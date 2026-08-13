from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Literal, cast
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import exists, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ConnectorPolicySnapshot,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunSubmission,
    ConnectorRunTarget,
)
from app.schemas.api import (
    ConnectorEgressArmingIn,
    ConnectorGrantConsumptionMarkerV1,
)
from app.services.connector_egress_authorization import (
    ConnectorEgressAuthorizationError,
    ConnectorEgressAuthorizationReceipt,
    VerifiedConnectorGrant,
    VerifiedDualLiveCampaignDefinition,
    canonical_json_bytes as authority_canonical_json_bytes,
    resolve_current_connector_egress_grant,
    resolve_current_dual_live_campaign_definition,
    resolve_historical_connector_grant_evidence,
)
from app.services import nrc_aps_artifact_ingestion
from app.services.raw_storage_handles import (
    StableRawStorageError,
    hash_locked_raw_file,
)

try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - application dependency
    BaseModel = object  # type: ignore[assignment,misc]


class ConnectorEgressArmingError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class NrcAcquisitionSuccessEvidence:
    connector_run_id: str
    ledger_terminal_hash: str
    blob_rehash_raw_sha256: str
    counter_reconciliation: Mapping[str, Any]


@dataclass(frozen=True)
class DerivedEgressTarget:
    ordinal: int
    stage: str
    normalized_url: str
    url_sha256: str
    scheme: str
    host: str
    port: int
    path_rule_id: str
    query_class: str


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical timestamps must be timezone-aware")
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            normalized[key] = _canonical_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return [_canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise ValueError("floating-point fields are forbidden in arming payloads")
    raise TypeError(f"value is not canonical-JSON compatible: {type(value).__name__}")


def canonical_arming_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    materialized = {key: value for key, value in payload.items() if key != "arming_fingerprint"}
    canonical = _canonical_value(materialized)
    if not isinstance(canonical, dict):  # pragma: no cover - Mapping contract
        raise TypeError("arming payload must be an object")
    return canonical


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        canonical_arming_payload(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_arming_fingerprint(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def compute_parent_arming_id(
    *,
    connector_key: str,
    campaign_id: str,
    grant_sha256: str,
    arming_nonce: UUID,
) -> str:
    preimage = (
        "project6:parent-arming:"
        f"{connector_key}:{campaign_id}:{grant_sha256}:{arming_nonce}"
    )
    return str(uuid5(NAMESPACE_URL, preimage))


def _deterministic_id(
    connector_run_id: str,
    kind: str,
    ordinal: int = 0,
) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"project6:connector-egress:{connector_run_id}:{kind}:{ordinal}",
        )
    )


def _validate_creation_request(
    payload: ConnectorEgressArmingIn,
    verified_grant: VerifiedConnectorGrant,
    code_revision: str,
) -> None:
    grant = verified_grant.model
    campaign = verified_grant.verified_campaign
    expected = {
        "connector_key": grant.connector_key,
        "campaign_id": str(grant.campaign_id),
        "campaign_fingerprint": grant.campaign_fingerprint,
        "grant_sha256": verified_grant.raw_sha256,
    }
    actual = {
        "connector_key": payload.connector_key,
        "campaign_id": str(payload.campaign_id),
        "campaign_fingerprint": payload.campaign_fingerprint,
        "grant_sha256": payload.grant_sha256,
    }
    if actual != expected:
        raise ConnectorEgressArmingError(
            "connector_arming_authority_mismatch",
            "public arming fields do not match verified server authority",
        )
    if (
        code_revision != grant.code_revision
        or code_revision != campaign.model.code_revision
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_code_revision_mismatch",
            "code revision does not match verified campaign and grant",
        )
    if grant.max_armings != 1:
        raise ConnectorEgressArmingError(
            "connector_arming_ceiling_mismatch",
            "verified grant does not bind exactly one parent arming",
        )
    _assert_supersession_contract(verified_grant)


def _assert_supersession_contract(
    verified_grant: VerifiedConnectorGrant,
) -> None:
    grant = verified_grant.model
    prior_digest = grant.supersedes_grant_sha256
    if prior_digest is None:
        return
    if prior_digest == verified_grant.raw_sha256:
        raise ConnectorEgressArmingError(
            "connector_grant_supersession_invalid",
            "a grant cannot supersede its own raw digest",
        )
    matching_refs = [
        entry
        for entry in verified_grant.verified_campaign.index_chain.head.entries
        if entry.connector_key == grant.connector_key
        and entry.raw_grant_sha256 == prior_digest
    ]
    if len(matching_refs) != 1:
        raise ConnectorEgressArmingError(
            "connector_grant_supersession_unverified",
            "superseded grant digest does not select one protected index entry",
        )
    prior_ref = matching_refs[0]
    if (
        prior_ref.campaign_id == str(grant.campaign_id)
        or prior_ref.campaign_fingerprint == grant.campaign_fingerprint
    ):
        raise ConnectorEgressArmingError(
            "connector_grant_same_campaign_supersession_forbidden",
            "recovery requires a new campaign ID and fingerprint",
        )
    try:
        prior = resolve_historical_connector_grant_evidence(
            connector_key=grant.connector_key,
            campaign_id=prior_ref.campaign_id,
            expected_campaign_fingerprint=prior_ref.campaign_fingerprint,
            expected_grant_sha256=prior_digest,
        )
    except ConnectorEgressAuthorizationError as exc:
        raise ConnectorEgressArmingError(
            exc.code,
            exc.message,
            status_code=exc.http_status,
        ) from exc
    if (
        prior.raw_sha256 != prior_digest
        or prior.model.connector_key != grant.connector_key
        or prior.raw_definition_sha256
        == verified_grant.verified_campaign.raw_sha256
        or prior.model.arming_nonce == grant.arming_nonce
        or prior.marker_model.raw_grant_sha256 != prior_digest
        or prior.marker_model.connector_key != grant.connector_key
        or prior.marker_model.campaign_id
        != str(prior.model.campaign_id)
        or prior.marker_model.campaign_fingerprint
        != prior.canonical_campaign_fingerprint
        or prior.marker_model.campaign_definition_sha256
        != prior.raw_definition_sha256
        or prior.marker_model.canonical_grant_fingerprint
        != prior.canonical_fingerprint
        or prior.marker_model.arming_nonce != prior.model.arming_nonce
        or prior.marker_model.connector_run_id
        != compute_parent_arming_id(
            connector_key=prior.model.connector_key,
            campaign_id=str(prior.model.campaign_id),
            grant_sha256=prior.raw_sha256,
            arming_nonce=prior.model.arming_nonce,
        )
        or prior.marker_model.max_armings != 1
    ):
        raise ConnectorEgressArmingError(
            "connector_grant_supersession_unverified",
            "superseded grant or consumption marker does not prove fresh recovery authority",
        )


def _validated_authorization_receipt(
    value: Mapping[str, Any],
    *,
    verified_grant: VerifiedConnectorGrant,
) -> ConnectorEgressAuthorizationReceipt:
    try:
        receipt = ConnectorEgressAuthorizationReceipt.model_validate(value)
    except Exception as exc:
        raise ConnectorEgressArmingError(
            "connector_arming_authorization_receipt_invalid",
            "authorization receipt does not match the frozen schema",
        ) from exc
    campaign = verified_grant.verified_campaign
    expected = {
        "connector_key": verified_grant.model.connector_key,
        "campaign_id": str(campaign.model.campaign_id),
        "campaign_fingerprint": campaign.canonical_fingerprint,
        "campaign_definition_sha256": campaign.raw_sha256,
        "grant_sha256": verified_grant.raw_sha256,
        "canonical_grant_fingerprint": verified_grant.canonical_fingerprint,
        "introduction_index_revision": campaign.introduction_index_revision,
        "introduction_index_sha256": campaign.introduction_index_sha256,
        "access": "write",
    }
    actual = {
        key: getattr(receipt, key)
        for key in expected
    }
    if actual != expected:
        raise ConnectorEgressArmingError(
            "connector_arming_authorization_receipt_mismatch",
            "authorization receipt does not bind the verified campaign and grant",
        )
    for field_name in ("operator_ref_hash", "workspace_ref_hash"):
        field_value = getattr(receipt, field_name)
        if not re.fullmatch(r"[0-9a-f]{64}", field_value):
            raise ConnectorEgressArmingError(
                "connector_arming_authorization_receipt_invalid",
                "authorization receipt principal hashes must be lowercase SHA-256",
            )
    if not receipt.auth_owner_mode:
        raise ConnectorEgressArmingError(
            "connector_arming_authorization_receipt_invalid",
            "authorization receipt owner mode is empty",
        )
    return receipt


def _materialize_envelope(
    *,
    verified_grant: VerifiedConnectorGrant,
    operator_receipt: Mapping[str, Any],
    code_revision: str,
    predecessor: NrcAcquisitionSuccessEvidence | None,
) -> dict[str, Any]:
    grant = verified_grant.model
    campaign = verified_grant.verified_campaign
    receipt = _validated_authorization_receipt(
        operator_receipt,
        verified_grant=verified_grant,
    )
    envelope: dict[str, Any] = {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": grant.connector_key,
        "campaign_id": str(grant.campaign_id),
        "campaign_definition_sha256": campaign.raw_sha256,
        "campaign_fingerprint": campaign.canonical_fingerprint,
        "grant_sha256": verified_grant.raw_sha256,
        "canonical_grant_fingerprint": verified_grant.canonical_fingerprint,
        "campaign_introduction_index_revision": campaign.introduction_index_revision,
        "campaign_introduction_index_sha256": campaign.introduction_index_sha256,
        "code_revision": code_revision,
        "grant_id": grant.grant_id,
        "arming_nonce": grant.arming_nonce,
        "max_armings": grant.max_armings,
        "supersedes_grant_sha256": grant.supersedes_grant_sha256,
        "operator_mode": grant.operator_mode,
        "non_authorities": grant.non_authorities,
        "target": grant.target,
        "request_rules": grant.request_rules,
        "max_physical_requests": grant.max_physical_requests,
        "max_run_bytes": grant.max_run_bytes,
        "max_single_send_detection_allowance_bytes": (
            grant.max_single_send_detection_allowance_bytes
        ),
        "request_timeout_seconds": grant.request_timeout_seconds,
        "min_request_interval_ms": grant.min_request_interval_ms,
        "grant_issued_at": grant.issued_at,
        "grant_expires_at": grant.expires_at,
        "campaign_not_before": campaign.model.not_before,
        "campaign_expires_at": campaign.model.expires_at,
        "authorization_receipt": receipt.model_dump(mode="json"),
    }
    if predecessor is not None:
        envelope["predecessor_nrc_connector_run_id"] = (
            predecessor.connector_run_id
        )
        envelope["predecessor_nrc_ledger_terminal_hash"] = (
            predecessor.ledger_terminal_hash
        )
    fingerprint = compute_arming_fingerprint(envelope)
    return {**canonical_arming_payload(envelope), "arming_fingerprint": fingerprint}


def _marker_bytes(
    *,
    verified_grant: VerifiedConnectorGrant,
    connector_run_id: str,
) -> bytes:
    grant = verified_grant.model
    campaign = verified_grant.verified_campaign
    marker = ConnectorGrantConsumptionMarkerV1(
        schema_id="project6.connector_grant_consumption.v1",
        connector_key=grant.connector_key,
        campaign_id=str(grant.campaign_id),
        campaign_fingerprint=campaign.canonical_fingerprint,
        campaign_definition_sha256=campaign.raw_sha256,
        raw_grant_sha256=verified_grant.raw_sha256,
        canonical_grant_fingerprint=verified_grant.canonical_fingerprint,
        arming_nonce=grant.arming_nonce,
        connector_run_id=connector_run_id,
        max_armings=1,
    )
    return authority_canonical_json_bytes(marker)


def _assert_marker_bytes(
    path: Path,
    *,
    expected_bytes: bytes,
    expected_sha256: str,
) -> None:
    try:
        actual = path.read_bytes()
    except OSError as exc:
        raise ConnectorEgressArmingError(
            "connector_grant_consumption_marker_unreadable",
            "consumption marker could not be read",
        ) from exc
    if actual != expected_bytes or hashlib.sha256(actual).hexdigest() != expected_sha256:
        raise ConnectorEgressArmingError(
            "connector_grant_consumption_marker_mismatch",
            "consumption marker bytes do not match protected index",
        )


def _create_marker_once(path: Path, payload: bytes) -> bool:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        return False
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:  # pragma: no cover - OS contract
                raise OSError("short marker write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def _existing_creation(
    db: Session,
    *,
    connector_key: str,
    connector_run_id: str,
    submission_key: str,
    arming_fingerprint: str,
) -> ConnectorRun | None:
    submission = db.scalar(
        select(ConnectorRunSubmission).where(
            ConnectorRunSubmission.connector_key == connector_key,
            ConnectorRunSubmission.submission_idempotency_key == submission_key,
        )
    )
    run = db.get(ConnectorRun, connector_run_id)
    if run is None:
        return None
    if submission is None:
        raise ConnectorEgressArmingError(
            "connector_grant_already_consumed",
            "grant marker is already consumed by another creation key",
        )
    if (
        submission.connector_run_id != connector_run_id
        or submission.request_fingerprint != arming_fingerprint
        or run.request_fingerprint != arming_fingerprint
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_idempotency_conflict",
            "creation idempotency key was reused with different bytes",
        )
    return run


_NRC_TERMINAL_METRIC_KEYS = frozenset(
    {
        "outcome_class",
        "arming_fingerprint",
        "campaign_introduction_index_revision",
        "campaign_introduction_index_sha256",
    }
)
_NRC_SEAL_METRIC_KEYS = frozenset(
    {
        "schema_id",
        "campaign_id",
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "code_revision",
        "campaign_introduction_index_revision",
        "campaign_introduction_index_sha256",
        "manifest_relative_path",
        "manifest_sha256",
        "file_set_hash",
        "seal_relative_path",
        "seal_sha256",
        "connector_run_ids",
        "sealed_at",
    }
)


def _is_exact_nrc_campaign_seal_event(
    run: ConnectorRun,
    event: ConnectorRunEvent,
    *,
    envelope: Mapping[str, Any],
) -> bool:
    metrics = event.metrics_json
    run_ids = metrics.get("connector_run_ids") if isinstance(metrics, dict) else None
    sealed_at = metrics.get("sealed_at") if isinstance(metrics, dict) else None
    try:
        parsed_sealed_at = datetime.fromisoformat(
            str(sealed_at).replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return False
    bound_fields = (
        "campaign_id",
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "code_revision",
        "campaign_introduction_index_revision",
        "campaign_introduction_index_sha256",
    )
    digest_fields = (
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "campaign_introduction_index_sha256",
        "manifest_sha256",
        "file_set_hash",
        "seal_sha256",
    )
    return bool(
        isinstance(metrics, dict)
        and set(metrics) == _NRC_SEAL_METRIC_KEYS
        and event.connector_run_event_id
        == _deterministic_id(
            run.connector_run_id,
            "campaign_log_capture_sealed",
        )
        and event.connector_run_id == run.connector_run_id
        and event.connector_run_target_id is None
        and event.phase == "evidence"
        and event.stage == "campaign_log_capture"
        and event.event_type == "campaign_log_capture_sealed"
        and event.status_before == run.status == "completed"
        and event.status_after == run.status
        and event.reason_code == "protected_log_capture_sealed"
        and event.error_class is None
        and event.message is None
        and metrics.get("schema_id")
        == "project6.connector_campaign_log_seal_event_metrics.v1"
        and all(metrics.get(field) == envelope.get(field) for field in bound_fields)
        and all(
            isinstance(metrics.get(field), str)
            and re.fullmatch(r"[0-9a-f]{64}", str(metrics[field]))
            for field in digest_fields
        )
        and isinstance(metrics.get("code_revision"), str)
        and re.fullmatch(r"[0-9a-f]{40}", str(metrics["code_revision"]))
        and all(
            isinstance(metrics.get(field), str) and bool(str(metrics[field]))
            for field in ("manifest_relative_path", "seal_relative_path")
        )
        and isinstance(run_ids, list)
        and len(run_ids) == len(set(run_ids))
        and run.connector_run_id in run_ids
        and all(isinstance(run_id, str) and bool(run_id) for run_id in run_ids)
        and event.created_at is not None
        and _as_utc(parsed_sealed_at) == _as_utc(event.created_at)
    )


def _load_nrc_counter_records(path: Path) -> tuple[dict[str, Any], ...]:
    from app.services.connector_egress_transport import (
        CounterEvidenceError,
        parse_connector_counter_records,
    )

    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_unavailable",
            "manifest-bound NRC HTTP counter is unavailable",
        ) from exc
    try:
        return parse_connector_counter_records(payload)
    except CounterEvidenceError as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "NRC HTTP counter is not one exact homogeneous counter stream",
        ) from exc


def _assert_nrc_terminal_transition(
    run: ConnectorRun,
    *,
    events: Sequence[ConnectorRunEvent],
    now: datetime,
) -> None:
    envelope = _strict_envelope(run)
    terminal_id = _deterministic_id(
        run.connector_run_id,
        "egress_run_terminal",
    )
    terminals = [
        event
        for event in events
        if event.event_type == "egress_run_terminal"
        or event.connector_run_event_id == terminal_id
    ]
    terminal = terminals[0] if len(terminals) == 1 else None
    seal_id = _deterministic_id(
        run.connector_run_id,
        "campaign_log_capture_sealed",
    )
    seal_candidates = [
        event
        for event in events
        if event.event_type == "campaign_log_capture_sealed"
        or event.connector_run_event_id == seal_id
    ]
    exact_seals = [
        event
        for event in seal_candidates
        if _is_exact_nrc_campaign_seal_event(
            run,
            event,
            envelope=envelope,
        )
    ]
    seal_event = (
        exact_seals[0]
        if len(seal_candidates) == len(exact_seals) == 1
        else None
    )
    invalid_seal_evidence = bool(seal_candidates) and seal_event is None
    metrics = (
        terminal.metrics_json
        if terminal is not None and isinstance(terminal.metrics_json, dict)
        else {}
    )
    outcome_class = metrics.get("outcome_class")
    completed_at = run.completed_at
    terminal_shape_valid = bool(
        terminal is not None
        and terminal.connector_run_event_id == terminal_id
        and terminal.connector_run_id == run.connector_run_id
        and terminal.connector_run_target_id is None
        and terminal.phase == "execution"
        and terminal.stage == "terminal"
        and terminal.event_type == "egress_run_terminal"
        and terminal.status_before == "running"
        and terminal.status_after == "completed"
        and terminal.error_class is None
        and terminal.message is None
        and outcome_class == "nrc_raw_admission_completed"
        and terminal.reason_code == outcome_class
        and set(metrics) == _NRC_TERMINAL_METRIC_KEYS
        and metrics.get("arming_fingerprint")
        == envelope.get("arming_fingerprint")
        and metrics.get("campaign_introduction_index_revision")
        == envelope.get("campaign_introduction_index_revision")
        and metrics.get("campaign_introduction_index_sha256")
        == envelope.get("campaign_introduction_index_sha256")
        and completed_at is not None
        and _as_utc(terminal.created_at) == _as_utc(completed_at)
    )
    prohibited_statuses = {
        "cancelling",
        "cancelled",
        "completed",
        "completed_with_errors",
        "failed",
    }
    prohibited_tokens = ("cancel", "error", "fail", "terminal")
    competing_evidence = any(
        event is not terminal
        and event is not seal_event
        and (
            event.status_before in prohibited_statuses
            or event.status_after in prohibited_statuses
            or event.error_class is not None
            or any(
                token in str(value or "").lower()
                for token in prohibited_tokens
                for value in (event.event_type, event.reason_code)
            )
        )
        for event in events
    )
    if (
        run.status != "completed"
        or not terminal_shape_valid
        or invalid_seal_evidence
        or competing_evidence
        or run.cancellation_requested_at is not None
        or run.cancelled_at is not None
        or run.error_summary is not None
        or run.failed_count != 0
        or run.execution_lease_owner is not None
        or run.execution_lease_token is not None
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_terminal_invalid",
            "NRC predecessor lacks one unambiguous strict completed transition",
        )
    if (
        run.execution_lease_expires_at is not None
        and _as_utc(now) < _as_utc(run.execution_lease_expires_at)
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_lease_active",
            "NRC predecessor retains an unexpired execution lease",
        )


def _validated_nrc_ledger_entries(
    ledger: Any,
    *,
    run: ConnectorRun,
    verified_grant: VerifiedConnectorGrant,
) -> tuple[dict[str, Any], ...]:
    envelope = _strict_envelope(run)
    projection = ledger.canonical_projection
    entries = tuple(
        dict(entry)
        for entry in ledger.entries
        if isinstance(entry, Mapping)
    )
    expected_projection = {
        "schema_id": "project6.connector_egress_terminal_ledger.v1",
        "connector_run_id": run.connector_run_id,
        "connector_key": "nrc_adams_aps",
        "campaign_fingerprint": envelope["campaign_fingerprint"],
        "arming_fingerprint": envelope["arming_fingerprint"],
        "grant_sha256": verified_grant.raw_sha256,
        "campaign_introduction_index_revision": envelope[
            "campaign_introduction_index_revision"
        ],
        "campaign_introduction_index_sha256": envelope[
            "campaign_introduction_index_sha256"
        ],
        "frozen_max_physical_requests": (
            verified_grant.model.max_physical_requests
        ),
        "entries": list(entries),
    }
    expected_hash = hashlib.sha256(
        authority_canonical_json_bytes(expected_projection)
    ).hexdigest()
    if (
        ledger.connector_run_id != run.connector_run_id
        or ledger.eligible is not True
        or ledger.validation_errors
        or not isinstance(projection, Mapping)
        or dict(projection) != expected_projection
        or ledger.ledger_terminal_hash != expected_hash
        or len(entries) != verified_grant.model.max_physical_requests
        or [(entry.get("ordinal"), entry.get("stage")) for entry in entries]
        != [(1, "exact_accession_api"), (2, "artifact")]
        or any(
            entry.get("outcome_class") != "completed"
            for entry in entries
        )
        or any(
            entry.get("completion_event_id") is None
            for entry in entries
        )
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_ledger_invalid",
            "NRC terminal ledger is incomplete, ambiguous, or ineligible",
        )
    return entries


def _reconcile_counter_records(
    records: Sequence[Mapping[str, Any]],
    *,
    entries: Sequence[Mapping[str, Any]],
    source_name: str,
) -> None:
    if len(records) != len(entries):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            f"{source_name} HTTP counter cardinality does not equal terminal ledger",
        )
    for record, entry in zip(records, entries, strict=True):
        if (
            record.get("schema_id")
            not in (
                "project6.connector_http_counter.v1",
                "project6.connector_http_counter.v2",
            )
            or record.get("ordinal") != entry.get("ordinal")
            or record.get("stage") != entry.get("stage")
            or record.get("request_fingerprint")
            != entry.get("request_fingerprint")
            or record.get("response_status")
            != entry.get("response_status")
            or record.get("decoded_body_bytes")
            != entry.get("byte_count")
            or record.get("decoded_body_sha256")
            != entry.get("body_sha256")
            or record.get("error_class") is not None
        ):
            raise ConnectorEgressArmingError(
                "nrc_acquisition_success_counter_invalid",
                f"{source_name} HTTP counter disagrees with terminal ledger",
            )


def _reconcile_nrc_counter_records(
    records: Sequence[Mapping[str, Any]],
    *,
    entries: Sequence[Mapping[str, Any]],
) -> None:
    _reconcile_counter_records(records, entries=entries, source_name="NRC")


def _select_nrc_counter_records(
    records: Sequence[Mapping[str, Any]],
    *,
    entries: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    expected = [
        (
            entry.get("request_fingerprint"),
            entry.get("ordinal"),
            entry.get("stage"),
        )
        for entry in entries
    ]
    expected_set = set(expected)
    expected_fingerprints = {identity[0] for identity in expected}
    if (
        len(expected_set) != len(expected)
        or len(expected_fingerprints) != len(expected)
        or any(
            not isinstance(fingerprint, str)
            or not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or not isinstance(stage, str)
            for fingerprint, ordinal, stage in expected
        )
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "NRC terminal ledger does not select one exact counter substream",
        )

    selected: list[dict[str, Any]] = []
    found: set[tuple[object, object, object]] = set()
    for record in records:
        fingerprint = record.get("request_fingerprint")
        if fingerprint not in expected_fingerprints:
            continue
        identity = (
            fingerprint,
            record.get("ordinal"),
            record.get("stage"),
        )
        if identity not in expected_set or identity in found:
            raise ConnectorEgressArmingError(
                "nrc_acquisition_success_counter_invalid",
                "NRC HTTP counter substream is duplicate or disagrees with ledger",
            )
        found.add(identity)
        selected.append(dict(record))
    selected_identities = [
        (
            record.get("request_fingerprint"),
            record.get("ordinal"),
            record.get("stage"),
        )
        for record in selected
    ]
    if selected_identities != expected:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "NRC HTTP counter substream is missing or reordered",
        )
    return tuple(selected)


def _same_campaign_sciencebase_run(
    db: Session,
    *,
    verified_definition: VerifiedDualLiveCampaignDefinition,
    predecessor_run_id: str,
    predecessor_ledger_hash: str,
    now: datetime,
) -> ConnectorRun | None:
    expected_campaign = {
        "campaign_id": str(verified_definition.model.campaign_id),
        "campaign_definition_sha256": verified_definition.raw_sha256,
        "campaign_fingerprint": verified_definition.canonical_fingerprint,
        "campaign_introduction_index_revision": (
            verified_definition.introduction_index_revision
        ),
        "campaign_introduction_index_sha256": (
            verified_definition.introduction_index_sha256
        ),
        "code_revision": verified_definition.model.code_revision,
        "connector_key": "sciencebase_mcs",
        "predecessor_nrc_connector_run_id": predecessor_run_id,
        "predecessor_nrc_ledger_terminal_hash": predecessor_ledger_hash,
    }
    matches: list[ConnectorRun] = []
    runs = db.scalars(
        select(ConnectorRun)
        .where(ConnectorRun.connector_key == "sciencebase_mcs")
        .order_by(ConnectorRun.connector_run_id.asc())
    ).all()
    for run in runs:
        config = run.request_config_json
        envelope = (
            config.get("connector_egress_arming")
            if isinstance(config, Mapping)
            else None
        )
        if not isinstance(envelope, Mapping) or any(
            envelope.get(field) != value
            for field, value in expected_campaign.items()
        ):
            continue
        try:
            strict_envelope = _strict_envelope(run)
            fingerprint = _assert_envelope_fingerprint(run, strict_envelope)
            grant_sha256 = strict_envelope.get("grant_sha256")
            raw_arming_nonce = strict_envelope.get("arming_nonce")
            if (
                not isinstance(grant_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", grant_sha256)
                or not isinstance(raw_arming_nonce, str)
            ):
                raise ValueError("invalid ScienceBase authority identity")
            arming_nonce = UUID(raw_arming_nonce)
            if str(arming_nonce) != raw_arming_nonce:
                raise ValueError("noncanonical ScienceBase arming nonce")
            expected_run_id = compute_parent_arming_id(
                connector_key="sciencebase_mcs",
                campaign_id=expected_campaign["campaign_id"],
                grant_sha256=grant_sha256,
                arming_nonce=arming_nonce,
            )
            submission = db.scalar(
                select(ConnectorRunSubmission).where(
                    ConnectorRunSubmission.connector_key
                    == "sciencebase_mcs",
                    ConnectorRunSubmission.submission_idempotency_key
                    == run.submission_idempotency_key,
                    ConnectorRunSubmission.connector_run_id
                    == run.connector_run_id,
                )
            )
            if (
                run.connector_run_id != expected_run_id
                or run.source_system != "sciencebase"
                or run.source_mode != "strict_live_egress"
                or not isinstance(run.submission_idempotency_key, str)
                or not run.submission_idempotency_key.startswith("egress-arm:")
                or submission is None
                or submission.connector_run_submission_id
                != _deterministic_id(run.connector_run_id, "arming-submission")
                or submission.request_fingerprint != fingerprint
                or submission.expires_at is None
                or _as_utc(now) >= _as_utc(submission.expires_at)
            ):
                raise ValueError("invalid ScienceBase run binding")
        except (ConnectorEgressArmingError, TypeError, ValueError) as exc:
            raise ConnectorEgressArmingError(
                "nrc_acquisition_success_counter_invalid",
                "same-campaign ScienceBase run authority is invalid",
            ) from exc
        matches.append(run)
    if len(matches) > 1:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "same-campaign ScienceBase run is ambiguous",
        )
    return matches[0] if matches else None


def _validated_sciencebase_ledger_entries(
    ledger: Any,
    *,
    run: ConnectorRun,
    now: datetime,
) -> tuple[dict[str, Any], ...]:
    envelope = _strict_envelope(run)
    raw_entries = tuple(ledger.entries)
    if any(not isinstance(entry, Mapping) for entry in raw_entries):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "ScienceBase terminal ledger entries are malformed",
        )
    entries = tuple(dict(entry) for entry in raw_entries)
    ceiling = envelope.get("max_physical_requests")
    expected_projection = {
        "schema_id": "project6.connector_egress_terminal_ledger.v1",
        "connector_run_id": run.connector_run_id,
        "connector_key": "sciencebase_mcs",
        "campaign_fingerprint": envelope["campaign_fingerprint"],
        "arming_fingerprint": envelope["arming_fingerprint"],
        "grant_sha256": envelope["grant_sha256"],
        "campaign_introduction_index_revision": envelope[
            "campaign_introduction_index_revision"
        ],
        "campaign_introduction_index_sha256": envelope[
            "campaign_introduction_index_sha256"
        ],
        "frozen_max_physical_requests": ceiling,
        "entries": list(entries),
    }
    expected_hash = hashlib.sha256(
        authority_canonical_json_bytes(expected_projection)
    ).hexdigest()
    ordinals = [entry.get("ordinal") for entry in entries]
    completed = tuple(
        entry for entry in entries if entry.get("outcome_class") == "completed"
    )
    common_invalid = (
        ledger.connector_run_id != run.connector_run_id
        or not isinstance(ledger.canonical_projection, Mapping)
        or dict(ledger.canonical_projection) != expected_projection
        or ledger.ledger_terminal_hash != expected_hash
        or isinstance(ceiling, bool)
        or not isinstance(ceiling, int)
        or ceiling <= 0
        or len(entries) > ceiling
        or ordinals != list(range(1, len(entries) + 1))
        or any(
            not isinstance(entry.get("stage"), str)
            or not entry.get("stage")
            for entry in entries
        )
        or any(
            entry.get("completion_event_id") is None
            or entry.get("send_started_at") is None
            or entry.get("completed_at") is None
            for entry in completed
        )
    )
    if common_invalid:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "ScienceBase terminal ledger identity is invalid",
        )
    if len(completed) == len(entries):
        if ledger.eligible is not True or ledger.validation_errors:
            raise ConnectorEgressArmingError(
                "nrc_acquisition_success_counter_invalid",
                "ScienceBase terminal ledger is not eligible",
            )
        return completed

    trailing = entries[-1] if entries else None
    trailing_ordinal = len(entries)
    expected_errors = {
        f"missing_completion_{trailing_ordinal}",
        "spent_unknown",
        "non_successful_send",
    }
    if (
        not entries
        or completed != entries[:-1]
        or trailing is None
        or trailing.get("outcome_class") != "spent_unknown"
        or trailing.get("completion_event_id") is not None
        or trailing.get("send_started_at") is not None
        or trailing.get("completed_at") is not None
        or trailing.get("response_status") is not None
        or trailing.get("byte_count") is not None
        or trailing.get("body_sha256") is not None
        or ledger.eligible is not False
        or set(ledger.validation_errors) != expected_errors
        or len(tuple(ledger.validation_errors)) != len(expected_errors)
        or run.status != "running"
        or not isinstance(run.execution_lease_owner, str)
        or not run.execution_lease_owner
        or not isinstance(run.execution_lease_token, str)
        or not run.execution_lease_token
        or run.execution_lease_expires_at is None
        or _as_utc(now) >= _as_utc(run.execution_lease_expires_at)
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "ScienceBase terminal ledger is not an exact completed prefix",
        )
    return completed


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _same_lexical_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(
        os.path.normpath(str(right))
    )


def _rehash_nrc_artifact_blob(
    db: Session,
    *,
    connector_run_id: str,
    ledger_sha256: str,
    counter_sha256: object,
    expected_size: int,
    max_bytes: int,
) -> str:
    target_rows = db.execute(
        select(
            ConnectorRunTarget.downloaded_sha256,
            ConnectorRunTarget.raw_storage_ref,
        )
        .where(ConnectorRunTarget.connector_run_id == connector_run_id)
        .order_by(ConnectorRunTarget.connector_run_target_id.asc())
    ).all()
    if len(target_rows) != 1:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_blob_invalid",
            "NRC predecessor does not bind exactly one raw target blob",
        )
    target_sha256, raw_storage_ref = target_rows[0]
    if (
        not isinstance(target_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", target_sha256)
        or not isinstance(raw_storage_ref, str)
        or not raw_storage_ref
        or raw_storage_ref != raw_storage_ref.strip()
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_blob_invalid",
            "NRC predecessor raw target binding is incomplete or invalid",
        )

    raw_root = _lexical_absolute(Path(settings.connector_raw_dir))
    expected_path = _lexical_absolute(
        raw_root
        / nrc_aps_artifact_ingestion.blob_relative_path(
            sha256=target_sha256
        )
    )
    target_path = _lexical_absolute(Path(raw_storage_ref))
    if not _same_lexical_path(target_path, expected_path):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_blob_invalid",
            "NRC predecessor raw target is not the exact content-addressed blob",
        )

    try:
        actual_size, actual_sha256, canonical_ref = hash_locked_raw_file(
            raw_root,
            expected_path,
            max_bytes=max_bytes,
        )
    except StableRawStorageError as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_blob_unavailable",
            "NRC predecessor content-addressed blob is unavailable or unsafe",
        ) from exc
    if (
        not _same_lexical_path(Path(canonical_ref), expected_path)
        or actual_size != expected_size
        or actual_sha256 != target_sha256
        or actual_sha256 != ledger_sha256
        or actual_sha256 != counter_sha256
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_blob_mismatch",
            "NRC predecessor blob rehash disagrees with target, ledger, or counter authority",
        )
    return actual_sha256


def evaluate_nrc_acquisition_success(
    db: Session,
    *,
    verified_definition: VerifiedDualLiveCampaignDefinition,
) -> NrcAcquisitionSuccessEvidence:
    from app.services.connector_egress_transport import (
        derive_terminal_request_ledger,
    )

    now = datetime.now(UTC)
    configured_digest = settings.connector_nrc_aps_grant_sha256
    if not configured_digest:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_grant_unconfigured",
            "NRC predecessor grant digest is not configured",
        )
    try:
        configured_grant = resolve_current_connector_egress_grant(
            verified_campaign=verified_definition,
            connector_key="nrc_adams_aps",
            expected_grant_sha256=configured_digest,
            campaign_id=str(verified_definition.model.campaign_id),
            campaign_fingerprint=verified_definition.canonical_fingerprint,
            code_revision=verified_definition.model.code_revision,
            now=now,
        )
    except Exception as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_authority_invalid",
            "NRC predecessor authority could not be rederived",
        ) from exc
    run_id = compute_parent_arming_id(
        connector_key="nrc_adams_aps",
        campaign_id=str(verified_definition.model.campaign_id),
        grant_sha256=configured_grant.raw_sha256,
        arming_nonce=configured_grant.model.arming_nonce,
    )
    run = db.get(ConnectorRun, run_id)
    if run is None or run.connector_key != "nrc_adams_aps":
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_run_missing",
            "deterministic NRC predecessor run does not exist",
        )
    try:
        verified_grant = resolve_current_egress_authority(
            db,
            connector_run_id=run_id,
            now=now,
        )
    except Exception as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_authority_invalid",
            "NRC predecessor run authority could not be rederived",
        ) from exc
    if (
        verified_grant.raw_sha256 != configured_grant.raw_sha256
        or verified_grant.canonical_fingerprint
        != configured_grant.canonical_fingerprint
        or verified_grant.verified_campaign.raw_sha256
        != verified_definition.raw_sha256
        or verified_grant.verified_campaign.canonical_fingerprint
        != verified_definition.canonical_fingerprint
        or verified_grant.verified_campaign.introduction_index_revision
        != verified_definition.introduction_index_revision
        or verified_grant.verified_campaign.introduction_index_sha256
        != verified_definition.introduction_index_sha256
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_authority_invalid",
            "NRC predecessor authority differs across same-call derivations",
        )

    events = list(
        db.scalars(
            select(ConnectorRunEvent)
            .where(ConnectorRunEvent.connector_run_id == run_id)
            .order_by(
                ConnectorRunEvent.created_at.asc(),
                ConnectorRunEvent.connector_run_event_id.asc(),
            )
        ).all()
    )
    _assert_nrc_terminal_transition(run, events=events, now=now)

    captures = [
        capture
        for capture in verified_definition.index_chain.head.log_captures
        if capture.campaign_id == str(verified_definition.model.campaign_id)
        and capture.campaign_fingerprint
        == verified_definition.canonical_fingerprint
        and capture.campaign_definition_sha256
        == verified_definition.raw_sha256
        and capture.code_revision == verified_definition.model.code_revision
        and tuple(capture.expected_stream_files)
        == ("app.jsonl", "http.jsonl", "stdout.log", "stderr.log")
    ]
    if len(captures) != 1:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_unbound",
            "campaign evidence does not select one HTTP counter capture",
        )
    try:
        evidence_root = verified_definition.evidence_root.resolve(strict=True)
        counter_path = (
            evidence_root
            / captures[0].log_dir_relative_path
            / "http.jsonl"
        )
        resolved_counter = counter_path.resolve(strict=True)
    except OSError as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_unavailable",
            "manifest-bound NRC HTTP counter is unavailable",
        ) from exc
    if (
        not resolved_counter.is_relative_to(evidence_root)
        or resolved_counter != counter_path.absolute()
        or not resolved_counter.is_file()
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_unavailable",
            "manifest-bound NRC HTTP counter is not an exact regular file",
        )
    all_records = _load_nrc_counter_records(resolved_counter)
    if (
        not all_records
        or all_records[0].get("schema_id")
        != "project6.connector_http_counter.v2"
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_v2_required",
            "dual-live NRC success requires one boot-bound counter-v2 stream",
        )
    try:
        ledger = derive_terminal_request_ledger(
            db,
            connector_run_id=run_id,
            counter_records=all_records,
        )
    except Exception as exc:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_ledger_invalid",
            "NRC terminal ledger or counter stream could not be rederived",
        ) from exc
    entries = _validated_nrc_ledger_entries(
        ledger,
        run=run,
        verified_grant=verified_grant,
    )
    records = _select_nrc_counter_records(all_records, entries=entries)
    _reconcile_nrc_counter_records(records, entries=entries)
    nrc_prefix = tuple(
        dict(record) for record in all_records[: len(records)]
    )
    if nrc_prefix != records:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_counter_invalid",
            "NRC HTTP counter records are not the exact stream prefix",
        )
    sciencebase_records = tuple(all_records[len(records) :])
    sciencebase_run = _same_campaign_sciencebase_run(
        db,
        verified_definition=verified_definition,
        predecessor_run_id=run_id,
        predecessor_ledger_hash=ledger.ledger_terminal_hash,
        now=now,
    )
    if sciencebase_run is None:
        if sciencebase_records:
            raise ConnectorEgressArmingError(
                "nrc_acquisition_success_counter_invalid",
                "counter stream has records without a same-campaign ScienceBase run",
            )
    else:
        try:
            sciencebase_ledger = derive_terminal_request_ledger(
                db,
                connector_run_id=sciencebase_run.connector_run_id,
                counter_records=all_records,
            )
            sciencebase_entries = _validated_sciencebase_ledger_entries(
                sciencebase_ledger,
                run=sciencebase_run,
                now=now,
            )
            _reconcile_counter_records(
                sciencebase_records,
                entries=sciencebase_entries,
                source_name="ScienceBase",
            )
        except ConnectorEgressArmingError:
            raise
        except Exception as exc:
            raise ConnectorEgressArmingError(
                "nrc_acquisition_success_counter_invalid",
                "ScienceBase counter suffix could not be rederived",
            ) from exc

    artifact = entries[-1]
    artifact_hash = artifact.get("body_sha256")
    artifact_size = artifact.get("byte_count")
    artifact_rules = [
        rule
        for rule in verified_grant.model.request_rules
        if rule.ordinal == 2 and rule.stage == "artifact"
    ]
    if len(artifact_rules) != 1:
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_artifact_invalid",
            "NRC artifact rule is not unique",
        )
    artifact_limit = artifact_rules[0].max_response_bytes
    if (
        artifact.get("outcome_class") != "completed"
        or artifact.get("response_status") != 200
        or not isinstance(artifact_size, int)
        or isinstance(artifact_size, bool)
        or artifact_size <= 0
        or artifact_size > artifact_limit
        or not isinstance(artifact_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", artifact_hash)
    ):
        raise ConnectorEgressArmingError(
            "nrc_acquisition_success_artifact_invalid",
            "NRC artifact completion is not one complete bounded 200 response",
        )

    counter_artifact_hash = records[-1].get("decoded_body_sha256")
    blob_rehash_raw_sha256 = _rehash_nrc_artifact_blob(
        db,
        connector_run_id=run_id,
        ledger_sha256=artifact_hash,
        counter_sha256=counter_artifact_hash,
        expected_size=artifact_size,
        max_bytes=artifact_limit,
    )
    return NrcAcquisitionSuccessEvidence(
        connector_run_id=run_id,
        ledger_terminal_hash=ledger.ledger_terminal_hash,
        blob_rehash_raw_sha256=blob_rehash_raw_sha256,
        counter_reconciliation={
            "record_count": len(records),
            "artifact_ordinal": artifact.get("ordinal"),
            "artifact_stage": artifact.get("stage"),
            "artifact_decoded_body_sha256": counter_artifact_hash,
        },
    )


def _derive_arming_expiry(
    verified_grant: VerifiedConnectorGrant,
    *,
    now: datetime,
) -> datetime:
    ttl_seconds = settings.connector_egress_arming_max_ttl_seconds
    if (
        isinstance(ttl_seconds, bool)
        or not isinstance(ttl_seconds, int)
        or ttl_seconds <= 0
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_ttl_invalid",
            "configured arming TTL must be a positive integer",
        )
    current = _as_utc(now)
    try:
        configured_expiry = current + timedelta(seconds=ttl_seconds)
    except OverflowError as exc:
        raise ConnectorEgressArmingError(
            "connector_arming_ttl_invalid",
            "configured arming TTL exceeds the supported datetime range",
        ) from exc
    campaign_expiry = _as_utc(
        verified_grant.verified_campaign.model.expires_at
    )
    grant_expiry = _as_utc(verified_grant.model.expires_at)
    expires_at = min(configured_expiry, campaign_expiry, grant_expiry)
    if current >= expires_at:
        raise ConnectorEgressArmingError(
            "connector_arming_window_closed",
            "arming authority window is already closed",
        )
    return expires_at


def create_connector_egress_arming(
    db: Session,
    *,
    payload: ConnectorEgressArmingIn,
    verified_grant: VerifiedConnectorGrant,
    operator_receipt: Mapping[str, Any],
    code_revision: str,
) -> tuple[ConnectorRun, bool]:
    _validate_creation_request(payload, verified_grant, code_revision)
    arming_expires_at = _derive_arming_expiry(
        verified_grant,
        now=datetime.now(UTC),
    )
    predecessor = None
    if verified_grant.model.connector_key == "sciencebase_mcs":
        predecessor = evaluate_nrc_acquisition_success(
            db,
            verified_definition=verified_grant.verified_campaign,
        )
    envelope = _materialize_envelope(
        verified_grant=verified_grant,
        operator_receipt=operator_receipt,
        code_revision=code_revision,
        predecessor=predecessor,
    )
    arming_fingerprint = envelope["arming_fingerprint"]
    grant = verified_grant.model
    connector_run_id = compute_parent_arming_id(
        connector_key=grant.connector_key,
        campaign_id=str(grant.campaign_id),
        grant_sha256=verified_grant.raw_sha256,
        arming_nonce=grant.arming_nonce,
    )
    marker_path = Path(verified_grant.consumption_marker_path)
    marker_payload = _marker_bytes(
        verified_grant=verified_grant,
        connector_run_id=connector_run_id,
    )
    expected_marker_sha256 = verified_grant.consumption_marker_sha256
    if hashlib.sha256(marker_payload).hexdigest() != expected_marker_sha256:
        raise ConnectorEgressArmingError(
            "connector_grant_consumption_marker_contract_mismatch",
            "derived marker does not match protected index digest",
        )
    submission_key = f"egress-arm:{payload.client_request_id}"
    marker_created = _create_marker_once(marker_path, marker_payload)
    if not marker_created:
        _assert_marker_bytes(
            marker_path,
            expected_bytes=marker_payload,
            expected_sha256=expected_marker_sha256,
        )
        existing = _existing_creation(
            db,
            connector_key=grant.connector_key,
            connector_run_id=connector_run_id,
            submission_key=submission_key,
            arming_fingerprint=arming_fingerprint,
        )
        if existing is not None:
            return existing, False
        raise ConnectorEgressArmingError(
            "connector_grant_consumed_without_arming",
            "grant marker exists without matching DB arming",
        )

    source_system = (
        "sciencebase" if grant.connector_key == "sciencebase_mcs" else "nrc_adams"
    )
    run = ConnectorRun(
        connector_run_id=connector_run_id,
        connector_key=grant.connector_key,
        source_system=source_system,
        source_mode="strict_live_egress",
        status="armed",
        request_config_json={"connector_egress_arming": envelope},
        query_plan_json={},
        request_fingerprint=arming_fingerprint,
        submission_idempotency_key=submission_key,
    )
    submission = ConnectorRunSubmission(
        connector_run_submission_id=_deterministic_id(
            connector_run_id, "arming-submission"
        ),
        connector_key=grant.connector_key,
        submission_idempotency_key=submission_key,
        request_fingerprint=arming_fingerprint,
        connector_run_id=connector_run_id,
        expires_at=arming_expires_at,
    )
    policy = ConnectorPolicySnapshot(
        connector_policy_snapshot_id=_deterministic_id(
            connector_run_id, "parent-policy"
        ),
        connector_run_id=connector_run_id,
        policy_json={
            "connector_key": grant.connector_key,
            "request_rules": canonical_arming_payload(
                {"request_rules": grant.request_rules}
            )["request_rules"],
            "max_physical_requests": grant.max_physical_requests,
            "max_run_bytes": grant.max_run_bytes,
            "max_single_send_detection_allowance_bytes": (
                grant.max_single_send_detection_allowance_bytes
            ),
        },
        retry_matrix_json={"automatic_retry_authorized": False},
    )
    event = ConnectorRunEvent(
        connector_run_event_id=_deterministic_id(
            connector_run_id, "egress_arming_created"
        ),
        connector_run_id=connector_run_id,
        phase="arming",
        stage="parent",
        event_type="egress_arming_created",
        status_before=None,
        status_after="armed",
        reason_code="owner_grant_consumed",
        metrics_json={
            "arming_fingerprint": arming_fingerprint,
            "campaign_introduction_index_revision": (
                verified_grant.verified_campaign.introduction_index_revision
            ),
            "campaign_introduction_index_sha256": (
                verified_grant.verified_campaign.introduction_index_sha256
            ),
        },
    )
    try:
        db.add_all([run, submission, policy, event])
        db.commit()
        db.refresh(run)
    except IntegrityError as exc:
        db.rollback()
        raise ConnectorEgressArmingError(
            "connector_arming_persistence_conflict",
            "grant was consumed but DB arming transaction conflicted",
        ) from exc
    except Exception:
        db.rollback()
        raise
    return run, True


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def has_reserved_egress_provenance(run: ConnectorRun) -> bool:
    """Return true for any strict-lane marker, including malformed envelopes."""
    config = run.request_config_json
    return bool(
        run.source_mode == "strict_live_egress"
        or (
            isinstance(run.submission_idempotency_key, str)
            and run.submission_idempotency_key.startswith("egress-arm:")
        )
        or (
            isinstance(config, dict)
            and "connector_egress_arming" in config
        )
    )


def is_strict_egress_run(run: ConnectorRun) -> bool:
    """Return true only for a structurally valid reserved strict-lane run."""
    config = run.request_config_json
    envelope = (
        config.get("connector_egress_arming")
        if isinstance(config, dict)
        else None
    )
    return bool(
        run.source_mode == "strict_live_egress"
        and isinstance(run.submission_idempotency_key, str)
        and run.submission_idempotency_key.startswith("egress-arm:")
        and isinstance(envelope, dict)
        and envelope.get("schema_id")
        == "project6.connector_egress_arming.v1"
    )


def _strict_envelope(run: ConnectorRun) -> dict[str, Any]:
    if not is_strict_egress_run(run):
        code = (
            "connector_strict_envelope_malformed"
            if has_reserved_egress_provenance(run)
            else "connector_strict_envelope_required"
        )
        raise ConnectorEgressArmingError(
            code,
            "connector run does not carry one valid strict egress arming envelope",
        )
    return dict(run.request_config_json["connector_egress_arming"])


def _assert_envelope_fingerprint(
    run: ConnectorRun,
    envelope: Mapping[str, Any],
) -> str:
    stored = str(envelope.get("arming_fingerprint") or "")
    rederived = compute_arming_fingerprint(envelope)
    if (
        not re.fullmatch(r"[0-9a-f]{64}", stored)
        or stored != rederived
        or run.request_fingerprint != rederived
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_fingerprint_mismatch",
            "persisted arming bytes do not rederive the bound fingerprint",
        )
    return rederived


def _resolve_current_authority(
    *,
    envelope: Mapping[str, Any],
    now: datetime,
) -> VerifiedConnectorGrant:
    required = (
        "campaign_id",
        "campaign_fingerprint",
        "code_revision",
        "connector_key",
        "grant_sha256",
    )
    if any(
        not isinstance(envelope.get(field), str)
        or not str(envelope[field])
        for field in required
    ):
        raise ConnectorEgressArmingError(
            "connector_strict_envelope_malformed",
            "strict arming envelope lacks a required authority binding",
        )
    try:
        campaign = resolve_current_dual_live_campaign_definition(
            expected_campaign_id=str(envelope["campaign_id"]),
            expected_campaign_fingerprint=str(
                envelope["campaign_fingerprint"]
            ),
            code_revision=str(envelope["code_revision"]),
            now=now,
        )
        return resolve_current_connector_egress_grant(
            verified_campaign=campaign,
            connector_key=str(envelope["connector_key"]),
            expected_grant_sha256=str(envelope["grant_sha256"]),
            campaign_id=str(envelope["campaign_id"]),
            campaign_fingerprint=str(envelope["campaign_fingerprint"]),
            code_revision=str(envelope["code_revision"]),
            now=now,
        )
    except ConnectorEgressAuthorizationError as exc:
        raise ConnectorEgressArmingError(
            exc.code,
            exc.message,
            status_code=exc.http_status,
        ) from exc


def _assert_strict_run_identity(
    run: ConnectorRun,
    *,
    verified_grant: VerifiedConnectorGrant,
) -> None:
    grant = verified_grant.model
    expected_run_id = compute_parent_arming_id(
        connector_key=grant.connector_key,
        campaign_id=str(grant.campaign_id),
        grant_sha256=verified_grant.raw_sha256,
        arming_nonce=grant.arming_nonce,
    )
    expected_source_system = (
        "sciencebase"
        if grant.connector_key == "sciencebase_mcs"
        else "nrc_adams"
    )
    if (
        run.connector_run_id != expected_run_id
        or run.connector_key != grant.connector_key
        or run.source_system != expected_source_system
        or run.source_mode != "strict_live_egress"
        or not isinstance(run.submission_idempotency_key, str)
        or not run.submission_idempotency_key.startswith("egress-arm:")
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_run_identity_drift",
            "strict run identity no longer equals verified owner authority",
        )


def _assert_current_authority_matches_envelope(
    *,
    envelope: Mapping[str, Any],
    verified_grant: VerifiedConnectorGrant,
    now: datetime,
) -> None:
    grant = verified_grant.model
    campaign = verified_grant.verified_campaign
    comparisons = {
        "connector_key": grant.connector_key,
        "campaign_id": str(grant.campaign_id),
        "campaign_definition_sha256": campaign.raw_sha256,
        "campaign_fingerprint": campaign.canonical_fingerprint,
        "grant_sha256": verified_grant.raw_sha256,
        "canonical_grant_fingerprint": verified_grant.canonical_fingerprint,
        "campaign_introduction_index_revision": (
            campaign.introduction_index_revision
        ),
        "campaign_introduction_index_sha256": (
            campaign.introduction_index_sha256
        ),
        "code_revision": grant.code_revision,
        "grant_id": grant.grant_id,
        "arming_nonce": str(grant.arming_nonce),
        "max_armings": grant.max_armings,
        "supersedes_grant_sha256": grant.supersedes_grant_sha256,
        "operator_mode": grant.operator_mode,
        "non_authorities": list(grant.non_authorities),
        "max_physical_requests": grant.max_physical_requests,
        "max_run_bytes": grant.max_run_bytes,
        "max_single_send_detection_allowance_bytes": (
            grant.max_single_send_detection_allowance_bytes
        ),
        "request_timeout_seconds": grant.request_timeout_seconds,
        "min_request_interval_ms": grant.min_request_interval_ms,
        "target": canonical_arming_payload({"target": grant.target})["target"],
        "request_rules": canonical_arming_payload(
            {"request_rules": grant.request_rules}
        )["request_rules"],
        "grant_issued_at": _canonical_value(grant.issued_at),
        "grant_expires_at": _canonical_value(grant.expires_at),
        "campaign_not_before": _canonical_value(campaign.model.not_before),
        "campaign_expires_at": _canonical_value(campaign.model.expires_at),
    }
    if any(envelope.get(key) != value for key, value in comparisons.items()):
        raise ConnectorEgressArmingError(
            "connector_arming_authority_drift",
            "current campaign or grant differs from immutable arming envelope",
        )
    current = _as_utc(now)
    if not (
        _as_utc(campaign.model.not_before)
        <= current
        < _as_utc(campaign.model.expires_at)
    ):
        raise ConnectorEgressArmingError(
            "connector_campaign_authority_expired",
            "campaign authority window is not current",
        )
    if not (
        _as_utc(grant.issued_at) <= current < _as_utc(grant.expires_at)
    ):
        raise ConnectorEgressArmingError(
            "connector_grant_authority_expired",
            "grant authority window is not current",
        )


def resolve_current_egress_authority(
    db: Session,
    *,
    connector_run_id: str,
    now: datetime,
) -> VerifiedConnectorGrant:
    """Reload and rederive all parent-arming authority without mutation."""
    current = _as_utc(now)
    run = db.scalar(
        select(ConnectorRun)
        .where(ConnectorRun.connector_run_id == connector_run_id)
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "strict connector run does not exist",
            status_code=404,
        )
    envelope = _strict_envelope(run)
    fingerprint = _assert_envelope_fingerprint(run, envelope)
    verified_grant = _resolve_current_authority(
        envelope=envelope,
        now=current,
    )
    _assert_current_authority_matches_envelope(
        envelope=envelope,
        verified_grant=verified_grant,
        now=current,
    )
    receipt = _validated_authorization_receipt(
        cast(Mapping[str, Any], envelope.get("authorization_receipt")),
        verified_grant=verified_grant,
    )
    _assert_supersession_contract(verified_grant)

    predecessor = None
    if run.connector_key == "sciencebase_mcs":
        predecessor = evaluate_nrc_acquisition_success(
            db,
            verified_definition=verified_grant.verified_campaign,
        )
    expected_envelope = _materialize_envelope(
        verified_grant=verified_grant,
        operator_receipt=receipt.model_dump(mode="json"),
        code_revision=verified_grant.model.code_revision,
        predecessor=predecessor,
    )
    if envelope != expected_envelope or fingerprint != expected_envelope[
        "arming_fingerprint"
    ]:
        raise ConnectorEgressArmingError(
            "connector_arming_envelope_drift",
            "persisted strict envelope is not the exact canonical owner envelope",
        )

    _assert_strict_run_identity(run, verified_grant=verified_grant)
    creation = db.scalar(
        select(ConnectorRunSubmission).where(
            ConnectorRunSubmission.connector_key == run.connector_key,
            ConnectorRunSubmission.submission_idempotency_key
            == run.submission_idempotency_key,
            ConnectorRunSubmission.connector_run_id == run.connector_run_id,
        )
    )
    if (
        creation is None
        or creation.request_fingerprint != fingerprint
        or creation.expires_at is None
        or current >= _as_utc(creation.expires_at)
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_expired_or_unbound",
            "creation submission is missing, expired, or fingerprint-mismatched",
        )

    expected_marker = _marker_bytes(
        verified_grant=verified_grant,
        connector_run_id=run.connector_run_id,
    )
    if not verified_grant.consumption_marker_present:
        raise ConnectorEgressArmingError(
            "connector_grant_consumption_marker_missing",
            "strict arming no longer has its protected one-use marker",
        )
    _assert_marker_bytes(
        verified_grant.consumption_marker_path,
        expected_bytes=expected_marker,
        expected_sha256=verified_grant.consumption_marker_sha256,
    )
    return verified_grant


def _load_execute_replay(
    db: Session,
    *,
    connector_key: str,
    connector_run_id: str,
    submission_key: str,
    arming_fingerprint: str,
) -> ConnectorRun | None:
    existing = db.scalar(
        select(ConnectorRunSubmission).where(
            ConnectorRunSubmission.submission_idempotency_key == submission_key,
        )
    )
    if existing is None:
        return None
    if (
        existing.connector_key != connector_key
        or existing.connector_run_id != connector_run_id
        or existing.request_fingerprint != arming_fingerprint
    ):
        raise ConnectorEgressArmingError(
            "connector_execution_idempotency_conflict",
            "execution idempotency key is bound to another run or fingerprint",
        )
    db.expire_all()
    replay = db.get(ConnectorRun, connector_run_id)
    if replay is None:
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "execution submission refers to a missing arming",
            status_code=404,
        )
    return replay


def _execute_submission_id(execution_idempotency_key: str) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            (
                "project6:connector-egress:"
                f"execute-idempotency:{execution_idempotency_key}"
            ),
        )
    )


def _require_unexpired_creation_binding(
    db: Session,
    *,
    run: ConnectorRun,
    arming_fingerprint: str,
    verified_grant: VerifiedConnectorGrant,
    now: datetime,
) -> ConnectorRunSubmission:
    creation = db.scalar(
        select(ConnectorRunSubmission)
        .where(
            ConnectorRunSubmission.connector_key == run.connector_key,
            ConnectorRunSubmission.submission_idempotency_key
            == run.submission_idempotency_key,
            ConnectorRunSubmission.connector_run_id == run.connector_run_id,
        )
        .execution_options(populate_existing=True)
    )
    current = _as_utc(now)
    if (
        creation is None
        or creation.request_fingerprint != arming_fingerprint
        or creation.expires_at is None
        or current >= _as_utc(creation.expires_at)
        or current >= _as_utc(verified_grant.model.expires_at)
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_expired_or_unbound",
            "creation submission is missing, expired, or fingerprint-mismatched",
        )
    return creation


def claim_connector_egress_arming(
    db: Session,
    *,
    connector_run_id: str,
    execution_idempotency_key: str,
    expected_arming_fingerprint: str,
    now: datetime,
) -> tuple[ConnectorRun, bool]:
    monotonic_started = time.monotonic()
    if not _SAFE_ID_RE.fullmatch(execution_idempotency_key):
        raise ConnectorEgressArmingError(
            "connector_execution_idempotency_key_invalid",
            "execution idempotency key must be safe ASCII",
            status_code=422,
        )
    run = db.get(ConnectorRun, connector_run_id)
    if run is None:
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "connector arming does not exist",
            status_code=404,
        )
    envelope = _strict_envelope(run)
    persisted_fingerprint = _assert_envelope_fingerprint(run, envelope)
    if (
        expected_arming_fingerprint != persisted_fingerprint
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_fingerprint_mismatch",
            "expected fingerprint does not match immutable arming",
        )
    current = _as_utc(now)
    verified_grant = resolve_current_egress_authority(
        db,
        connector_run_id=connector_run_id,
        now=current,
    )
    creation = _require_unexpired_creation_binding(
        db,
        run=run,
        arming_fingerprint=persisted_fingerprint,
        verified_grant=verified_grant,
        now=current,
    )
    submission_key = f"egress-execute:{execution_idempotency_key}"
    replay = _load_execute_replay(
        db,
        connector_key=run.connector_key,
        connector_run_id=run.connector_run_id,
        submission_key=submission_key,
        arming_fingerprint=persisted_fingerprint,
    )
    if replay is not None:
        return replay, False
    if run.status != "armed":
        raise ConnectorEgressArmingError(
            "connector_arming_state_conflict",
            "only an armed strict run can be claimed",
        )
    result = cast(
        CursorResult[Any],
        db.execute(
            update(ConnectorRun)
            .where(
                ConnectorRun.connector_run_id == connector_run_id,
                ConnectorRun.status == "armed",
                ConnectorRun.request_fingerprint == expected_arming_fingerprint,
                exists(
                    select(ConnectorRunSubmission.connector_run_submission_id)
                    .where(
                        ConnectorRunSubmission.connector_key
                        == run.connector_key,
                        ConnectorRunSubmission.submission_idempotency_key
                        == run.submission_idempotency_key,
                        ConnectorRunSubmission.connector_run_id
                        == connector_run_id,
                        ConnectorRunSubmission.request_fingerprint
                        == expected_arming_fingerprint,
                        ConnectorRunSubmission.expires_at.is_not(None),
                        ConnectorRunSubmission.expires_at > current,
                    )
                ),
            )
            .values(status="pending", claimed_at=current)
        ),
    )
    if result.rowcount != 1:
        db.rollback()
        replay = _load_execute_replay(
            db,
            connector_key=run.connector_key,
            connector_run_id=connector_run_id,
            submission_key=submission_key,
            arming_fingerprint=persisted_fingerprint,
        )
        if replay is not None:
            return replay, False
        raise ConnectorEgressArmingError(
            "connector_arming_claim_conflict",
            "armed-to-pending compare-and-swap did not win",
        )
    db.add(
        ConnectorRunSubmission(
            connector_run_submission_id=_execute_submission_id(
                execution_idempotency_key
            ),
            connector_key=run.connector_key,
            submission_idempotency_key=submission_key,
            request_fingerprint=persisted_fingerprint,
            connector_run_id=connector_run_id,
            expires_at=creation.expires_at,
        )
    )
    try:
        db.flush()
        elapsed_seconds = max(0.0, time.monotonic() - monotonic_started)
        precommit_now = current + timedelta(seconds=elapsed_seconds)
        _require_unexpired_creation_binding(
            db,
            run=run,
            arming_fingerprint=persisted_fingerprint,
            verified_grant=verified_grant,
            now=precommit_now,
        )
        db.commit()
    except ConnectorEgressArmingError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = _load_execute_replay(
            db,
            connector_key=run.connector_key,
            connector_run_id=connector_run_id,
            submission_key=submission_key,
            arming_fingerprint=persisted_fingerprint,
        )
        if replay is not None:
            return replay, False
        raise ConnectorEgressArmingError(
            "connector_arming_claim_conflict",
            "execution claim transaction conflicted",
        ) from exc
    claimed = db.get(ConnectorRun, connector_run_id)
    if claimed is None:  # pragma: no cover - primary-key invariant
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "claimed arming disappeared",
            status_code=404,
        )
    return claimed, True


def refresh_strict_run_lease(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    now: datetime,
) -> datetime:
    current = _as_utc(now)
    if (
        db.new
        or db.deleted
        or any(
            db.is_modified(item, include_collections=True)
            for item in db.dirty
        )
    ):
        raise ConnectorEgressArmingError(
            "connector_strict_lease_refresh_dirty_session",
            "strict lease refresh refuses to commit caller-pending state",
        )
    persisted = db.scalar(
        select(ConnectorRun)
        .where(ConnectorRun.connector_run_id == run.connector_run_id)
        .execution_options(populate_existing=True)
    )
    if persisted is None:
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "strict connector run does not exist",
            status_code=404,
        )
    _strict_envelope(persisted)
    lease_expires_at = persisted.execution_lease_expires_at
    if (
        persisted.status != "running"
        or not persisted.execution_lease_owner
        or persisted.execution_lease_token != lease_token
        or lease_expires_at is None
    ):
        raise ConnectorEgressArmingError(
            "connector_strict_lease_refresh_conflict",
            "strict lease refresh requires running state and exact lease ownership",
        )
    if current >= _as_utc(lease_expires_at):
        raise ConnectorEgressArmingError(
            "connector_strict_lease_expired",
            "an expired strict lease cannot be refreshed",
        )
    ttl_seconds = int(settings.connector_lease_ttl_seconds)
    if ttl_seconds <= 0:
        raise ConnectorEgressArmingError(
            "connector_strict_lease_ttl_invalid",
            "strict lease TTL must be positive",
        )
    refreshed_expires_at = current + timedelta(seconds=ttl_seconds)
    result = cast(
        CursorResult[Any],
        db.execute(
            update(ConnectorRun)
            .where(
                ConnectorRun.connector_run_id == persisted.connector_run_id,
                ConnectorRun.status == "running",
                ConnectorRun.execution_lease_owner.is_not(None),
                ConnectorRun.execution_lease_token == lease_token,
                ConnectorRun.execution_lease_expires_at.is_not(None),
                ConnectorRun.execution_lease_expires_at > current,
            )
            .execution_options(synchronize_session=False)
            .values(
                execution_lease_expires_at=refreshed_expires_at,
                heartbeat_at=current,
            )
        ),
    )
    if result.rowcount != 1:
        db.rollback()
        raise ConnectorEgressArmingError(
            "connector_strict_lease_refresh_conflict",
            "strict lease refresh compare-and-swap did not win",
        )
    db.commit()
    db.refresh(run)
    return refreshed_expires_at


def finalize_strict_run(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    terminal_status: Literal["completed", "failed", "cancelled"],
    outcome_class: str,
    now: datetime,
) -> None:
    if terminal_status not in {"completed", "failed", "cancelled"}:
        raise ConnectorEgressArmingError(
            "connector_strict_terminal_status_invalid",
            "strict finalizer accepts only declared terminal statuses",
            status_code=422,
        )
    if not outcome_class or not _SAFE_ID_RE.fullmatch(outcome_class):
        raise ConnectorEgressArmingError(
            "connector_strict_outcome_class_invalid",
            "outcome class must be safe ASCII",
            status_code=422,
        )
    current = _as_utc(now)
    persisted = db.scalar(
        select(ConnectorRun)
        .where(ConnectorRun.connector_run_id == run.connector_run_id)
        .execution_options(populate_existing=True)
    )
    if persisted is None:
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "strict connector run does not exist",
            status_code=404,
        )
    envelope = _strict_envelope(persisted)
    if (
        persisted.status != "running"
        or not persisted.execution_lease_owner
        or persisted.execution_lease_token != lease_token
    ):
        raise ConnectorEgressArmingError(
            "connector_strict_finalize_conflict",
            "strict finalizer requires running state and exact lease ownership",
        )
    terminal_event_id = _deterministic_id(
        persisted.connector_run_id,
        "egress_run_terminal",
    )
    if db.get(ConnectorRunEvent, terminal_event_id) is not None:
        raise ConnectorEgressArmingError(
            "connector_strict_finalize_conflict",
            "strict terminal event already exists",
        )
    values: dict[str, Any] = {
        "status": terminal_status,
        "completed_at": current,
        "execution_lease_owner": None,
        "execution_lease_token": None,
        "execution_lease_expires_at": current,
    }
    if terminal_status == "cancelled":
        values["cancelled_at"] = current
    finalize_predicates = [
        ConnectorRun.connector_run_id == persisted.connector_run_id,
        ConnectorRun.status == "running",
        ConnectorRun.execution_lease_owner.is_not(None),
        ConnectorRun.execution_lease_token == lease_token,
    ]
    result = cast(
        CursorResult[Any],
        db.execute(
            update(ConnectorRun)
            .where(*finalize_predicates)
            .execution_options(synchronize_session=False)
            .values(**values)
        ),
    )
    if result.rowcount != 1:
        db.rollback()
        raise ConnectorEgressArmingError(
            "connector_strict_finalize_conflict",
            "running-to-terminal compare-and-swap did not win",
        )
    db.add(
        ConnectorRunEvent(
            connector_run_event_id=terminal_event_id,
            connector_run_id=persisted.connector_run_id,
            phase="execution",
            stage="terminal",
            event_type="egress_run_terminal",
            status_before="running",
            status_after=terminal_status,
            reason_code=outcome_class,
            metrics_json={
                "outcome_class": outcome_class,
                "arming_fingerprint": envelope["arming_fingerprint"],
                "campaign_introduction_index_revision": envelope[
                    "campaign_introduction_index_revision"
                ],
                "campaign_introduction_index_sha256": envelope[
                    "campaign_introduction_index_sha256"
                ],
            },
            created_at=current,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConnectorEgressArmingError(
            "connector_strict_finalize_conflict",
            "strict terminal event or state transition conflicted",
        ) from exc
    db.refresh(run)


_EXACT_PATHS = {
    "sciencebase_item_exact_v1": (
        "/catalog/item/63d1a3c6d34e06fef15006be"
    ),
    "sciencebase_file_exact_v1": (
        "/catalog/file/get/63d1a3c6d34e06fef15006be"
    ),
    "nrc_get_document_exact_v1": "/aps/api/search/ML17123A319",
    "nrc_public_pdf_exact_v1": "/docs/ML1712/ML17123A319.pdf",
}
_EXACT_QUERIES = {
    "format_json_exact_v1": ("format=json", "format_json_exact"),
    "sciencebase_exact_file_selector_v1": (
        "f=mcs2023-germa_salient.csv",
        "exact_single_f_expected_filename",
    ),
    "none_v1": ("", "none"),
}


def _validated_derived_url(
    *,
    raw_url: str,
    rule: Any,
) -> DerivedEgressTarget:
    try:
        raw_url.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL must be ASCII",
        ) from exc
    if (
        not raw_url
        or any(ord(character) < 0x20 for character in raw_url)
        or "\\" in raw_url
        or "#" in raw_url
    ):
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL contains a forbidden delimiter or character",
        )
    try:
        parsed = urlsplit(raw_url)
        parsed_port = parsed.port
    except ValueError as exc:
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL authority is invalid",
        ) from exc
    if (
        parsed.scheme.lower() != "https"
        or "@" in parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname is None
    ):
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL authority is not admitted",
        )
    host = parsed.hostname.lower()
    port = parsed_port or 443
    if host not in rule.allowed_hosts or port != rule.port:
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL host or port is not admitted",
        )
    expected_path = _EXACT_PATHS.get(rule.path_rule_id)
    if expected_path is None or parsed.path != expected_path:
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL raw path does not equal the frozen rule",
        )
    expected_query, query_class = _EXACT_QUERIES[rule.query_rule_id]
    if rule.query_rule_id == "none_v1":
        if "?" in raw_url or parsed.query:
            raise ConnectorEgressArmingError(
                "connector_derived_url_not_authorized",
                "query delimiter is forbidden for this rule",
            )
    elif parsed.query != expected_query or raw_url.count("?") != 1:
        raise ConnectorEgressArmingError(
            "connector_derived_url_not_authorized",
            "derived URL raw query does not equal the frozen rule",
        )
    normalized = f"https://{host}{expected_path}"
    if expected_query:
        normalized = f"{normalized}?{expected_query}"
    return DerivedEgressTarget(
        ordinal=rule.ordinal,
        stage=rule.stage,
        normalized_url=normalized,
        url_sha256=hashlib.sha256(normalized.encode("ascii")).hexdigest(),
        scheme="https",
        host=host,
        port=443,
        path_rule_id=rule.path_rule_id,
        query_class=query_class,
    )


def commit_derived_url_arming(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    ordinal: int,
    stage: str,
    normalized_url: str,
    verified_grant: VerifiedConnectorGrant,
) -> DerivedEgressTarget:
    persisted = db.scalar(
        select(ConnectorRun)
        .where(ConnectorRun.connector_run_id == run.connector_run_id)
        .execution_options(populate_existing=True)
    )
    if persisted is None:
        raise ConnectorEgressArmingError(
            "connector_arming_not_found",
            "strict connector run does not exist",
            status_code=404,
        )
    envelope = _strict_envelope(persisted)
    lease_expires_at = persisted.execution_lease_expires_at
    if (
        persisted.status != "running"
        or not persisted.execution_lease_owner
        or persisted.execution_lease_token != lease_token
        or lease_expires_at is None
        or datetime.now(UTC) >= _as_utc(lease_expires_at)
    ):
        raise ConnectorEgressArmingError(
            "connector_derived_url_lease_conflict",
            "derived URL arming requires running state and exact active lease",
        )
    if (
        envelope.get("connector_key") != verified_grant.model.connector_key
        or envelope.get("grant_sha256") != verified_grant.raw_sha256
        or envelope.get("canonical_grant_fingerprint")
        != verified_grant.canonical_fingerprint
    ):
        raise ConnectorEgressArmingError(
            "connector_arming_authority_drift",
            "verified grant does not match immutable parent arming",
        )
    matching_rules = [
        rule
        for rule in verified_grant.model.request_rules
        if rule.ordinal == ordinal and rule.stage == stage
    ]
    if len(matching_rules) != 1:
        raise ConnectorEgressArmingError(
            "connector_derived_url_rule_not_found",
            "ordinal and stage do not select one frozen request rule",
        )
    derived = _validated_derived_url(
        raw_url=normalized_url,
        rule=matching_rules[0],
    )
    current = datetime.now(UTC)
    lease_guard = cast(
        CursorResult[Any],
        db.execute(
            update(ConnectorRun)
            .where(
                ConnectorRun.connector_run_id == persisted.connector_run_id,
                ConnectorRun.status == "running",
                ConnectorRun.execution_lease_owner.is_not(None),
                ConnectorRun.execution_lease_token == lease_token,
                ConnectorRun.execution_lease_expires_at.is_not(None),
                ConnectorRun.execution_lease_expires_at > current,
            )
            .execution_options(synchronize_session=False)
            .values(execution_lease_token=lease_token)
        ),
    )
    if lease_guard.rowcount != 1:
        db.rollback()
        raise ConnectorEgressArmingError(
            "connector_derived_url_lease_conflict",
            "active-lease compare-and-swap did not win",
        )
    safe_payload = {
        "kind": "derived_egress_arming",
        "ordinal": ordinal,
        "stage": stage,
        "url_sha256": derived.url_sha256,
        "scheme": derived.scheme,
        "host": derived.host,
        "port": derived.port,
        "path_rule_id": derived.path_rule_id,
        "query_class": derived.query_class,
    }
    db.add_all(
        [
            ConnectorPolicySnapshot(
                connector_policy_snapshot_id=_deterministic_id(
                    persisted.connector_run_id,
                    "derived-policy",
                    ordinal,
                ),
                connector_run_id=persisted.connector_run_id,
                policy_json=safe_payload,
                retry_matrix_json={"automatic_retry_authorized": False},
            ),
            ConnectorRunEvent(
                connector_run_event_id=_deterministic_id(
                    persisted.connector_run_id,
                    "derived_egress_arming_created",
                    ordinal,
                ),
                connector_run_id=persisted.connector_run_id,
                phase="execution",
                stage=stage,
                event_type="derived_egress_arming_created",
                status_before="running",
                status_after="running",
                reason_code="derived_url_grant_intersection",
                metrics_json=safe_payload,
            ),
        ]
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConnectorEgressArmingError(
            "connector_derived_url_arming_conflict",
            "derived URL arming already exists or conflicted",
        ) from exc
    return derived
