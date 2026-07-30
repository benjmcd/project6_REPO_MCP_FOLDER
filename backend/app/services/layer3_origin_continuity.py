from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import TYPE_CHECKING, Any, NoReturn

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    DatasetSourceProvenance,
    DatasetVersion,
    L3ConnectorSourceIntakeRecord,
)
from app.services.connector_egress_authorization import (
    VerifiedHistoricalGrantEvidence,
    resolve_historical_connector_grant_evidence,
    strict_json_loads,
)
from app.services.connector_egress_arming import (
    canonical_arming_payload,
    compute_arming_fingerprint,
)

if TYPE_CHECKING:
    from app.services.connector_egress_transport import (
        VerifiedTerminalRequestLedger,
    )


ORIGIN_RECEIPT_SCHEMA_ID = "layer3.connector_origin_continuity.v1"
ORIGIN_RECEIPT_STORAGE_KEY = "connector_origin_receipt_v1"
STRICT_ARMING_SCHEMA_ID = "project6.connector_egress_arming.v1"
TERMINAL_LEDGER_SCHEMA_ID = "project6.connector_egress_terminal_ledger.v1"
FRESH_LIVE_PROOF_CLASS = "fresh_live"
OFFLINE_FIXTURE_PROOF_CLASS = "offline_fixture"

_ALLOWED_CONNECTORS = frozenset({"sciencebase_mcs", "nrc_adams_aps"})
_HEX = frozenset("0123456789abcdef")
_FIXTURE_ID = "ml17123a319"
_FIXTURE_FILE_NAME = "ML17123A319.pdf"
_FIXTURE_ACCESSION = "ML17123A319"
_FIXTURE_MANIFEST_REF = "tests/fixtures/nrc_aps_docs/v1/manifest.json"


class Layer3OriginContinuityError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})


def _fail(
    code: str,
    message: str,
    *,
    details: Mapping[str, Any] | None = None,
) -> NoReturn:
    raise Layer3OriginContinuityError(code, message, details=details)


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_noncanonical_value",
            "Connector-origin evidence is not canonical JSON.",
        ) from exc


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _normalized_sha256(value: object, *, field: str) -> str:
    normalized = str(value or "").strip().lower()
    if len(normalized) != 64 or any(char not in _HEX for char in normalized):
        _fail(
            "layer3_origin_invalid_sha256",
            f"{field} must be a lowercase SHA-256.",
            details={"field": field},
        )
    return normalized


def _required_text(value: object, *, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        _fail(
            "layer3_origin_binding_missing",
            f"{field} is required for connector-origin continuity.",
            details={"field": field},
        )
    return normalized


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _fail(
            "layer3_origin_binding_invalid",
            f"{field} must be a positive integer.",
            details={"field": field},
        )
    return value


def _value(source: object, field: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(field)
    return getattr(source, field, None)


def _as_utc(value: object, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise Layer3OriginContinuityError(
                "layer3_origin_timestamp_invalid",
                f"{field} is not a valid UTC timestamp.",
                details={"field": field},
            ) from exc
    else:
        _fail(
            "layer3_origin_timestamp_invalid",
            f"{field} is not a valid UTC timestamp.",
            details={"field": field},
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(
            "layer3_origin_timestamp_invalid",
            f"{field} must be timezone-aware.",
            details={"field": field},
        )
    return parsed.astimezone(timezone.utc)


def _one(rows: list[Any], *, code: str, label: str) -> Any:
    if len(rows) != 1:
        _fail(
            code,
            f"Exactly one {label} must bind the connector target.",
            details={"count": len(rows)},
        )
    return rows[0]


def _same_storage_reference(left: object, right: object) -> bool:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if not left_text or not right_text:
        return False
    try:
        return Path(left_text).resolve() == Path(right_text).resolve()
    except OSError:
        return left_text == right_text


def _fixture_root() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "fixtures"
        / "nrc_aps_docs"
        / "v1"
    ).resolve()


def _raw_storage_path(
    storage_ref: object,
    *,
    allow_fixed_fixture: bool = False,
) -> Path:
    raw_ref = _required_text(storage_ref, field="raw_storage_ref")
    raw_root = Path(settings.connector_raw_dir).resolve()
    candidate = Path(raw_ref)
    if not candidate.is_absolute():
        candidate = raw_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_raw_blob_missing",
            "The connector-origin raw blob does not exist.",
        ) from exc
    admitted_fixture = (
        allow_fixed_fixture
        and resolved.parent == _fixture_root()
        and resolved.name == _FIXTURE_FILE_NAME
    )
    if (
        resolved != raw_root
        and raw_root not in resolved.parents
        and not admitted_fixture
    ):
        _fail(
            "layer3_origin_storage_ref_not_admitted",
            "The raw storage reference escapes connector raw storage.",
        )
    if not resolved.is_file():
        _fail(
            "layer3_origin_raw_blob_missing",
            "The connector-origin raw blob is not a regular file.",
        )
    return resolved


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        path_before = path.stat()
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if (
                opened_before.st_dev != path_before.st_dev
                or opened_before.st_ino != path_before.st_ino
            ):
                _fail(
                    "layer3_origin_raw_blob_changed",
                    "The raw blob changed while it was being opened.",
                )
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
            opened_after = os.fstat(handle.fileno())
        path_after = path.stat()
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_raw_blob_changed",
            "The raw blob changed while it was being hashed.",
        ) from exc
    stable_identity = (
        opened_before.st_dev,
        opened_before.st_ino,
        opened_before.st_size,
        opened_before.st_mtime_ns,
    )
    if stable_identity != (
        opened_after.st_dev,
        opened_after.st_ino,
        opened_after.st_size,
        opened_after.st_mtime_ns,
    ) or stable_identity != (
        path_after.st_dev,
        path_after.st_ino,
        path_after.st_size,
        path_after.st_mtime_ns,
    ):
        _fail(
            "layer3_origin_raw_blob_changed",
            "The raw blob changed while it was being hashed.",
        )
    if size != opened_after.st_size:
        _fail(
            "layer3_origin_raw_blob_changed",
            "The raw blob byte count changed while it was being hashed.",
        )
    if size <= 0:
        _fail(
            "layer3_origin_raw_blob_empty",
            "Connector-origin continuity rejects an empty raw blob.",
        )
    return size, digest.hexdigest()


def _compute_arming_fingerprint(envelope: Mapping[str, Any]) -> str:
    return str(compute_arming_fingerprint(envelope))


def _resolve_historical_evidence(
    **kwargs: str,
) -> VerifiedHistoricalGrantEvidence:
    return resolve_historical_connector_grant_evidence(**kwargs)


def _derive_terminal_ledger(
    db: Session,
    connector_run_id: str,
    *,
    counter_path: Path,
) -> VerifiedTerminalRequestLedger:
    from app.services.connector_egress_transport import (
        derive_terminal_request_ledger,
    )

    return derive_terminal_request_ledger(
        db,
        connector_run_id=connector_run_id,
        counter_path=counter_path,
    )


def _assert_counter_path_no_reparse(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise Layer3OriginContinuityError(
                "layer3_origin_counter_path_unavailable",
                "The protected HTTP counter path is unavailable.",
            ) from exc
        attrs = int(getattr(info, "st_file_attributes", 0))
        reparse_flag = int(
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        if stat.S_ISLNK(info.st_mode) or attrs & reparse_flag:
            _fail(
                "layer3_origin_counter_path_reparse",
                "The protected HTTP counter path cannot contain a reparse point.",
            )


def _resolve_historical_counter_path(
    evidence: VerifiedHistoricalGrantEvidence,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> Path:
    chain = _value(evidence, "index_chain")
    evidence_root = _value(chain, "evidence_root")
    head = _value(chain, "head")
    captures = _value(head, "log_captures")
    if (
        not isinstance(evidence_root, Path)
        or not evidence_root.is_absolute()
        or not isinstance(captures, Sequence)
        or isinstance(captures, (str, bytes))
    ):
        _fail(
            "layer3_origin_counter_authority_mismatch",
            "Historical evidence lacks one protected log-capture authority.",
        )
    matching = [
        capture
        for capture in captures
        if str(_value(capture, "campaign_id")) == campaign_id
        and _value(capture, "campaign_fingerprint")
        == campaign_fingerprint
    ]
    if len(matching) != 1:
        _fail(
            "layer3_origin_counter_authority_mismatch",
            "Historical evidence does not select one exact log capture.",
            details={"count": len(matching)},
        )
    capture = matching[0]
    expected_log_dir = f"logs/{campaign_fingerprint}"
    expected_manifest = f"{expected_log_dir}/manifest.json"
    expected_seal = f"log-seals/{campaign_fingerprint}.json"
    expected_streams = (
        "app.jsonl",
        "http.jsonl",
        "stdout.log",
        "stderr.log",
    )
    definition = _value(evidence, "definition_model")
    if (
        _value(capture, "campaign_definition_sha256")
        != _value(evidence, "raw_definition_sha256")
        or str(_value(capture, "code_revision"))
        != str(_value(definition, "code_revision"))
        or _value(capture, "log_dir_relative_path") != expected_log_dir
        or _value(capture, "manifest_relative_path") != expected_manifest
        or _value(capture, "seal_relative_path") != expected_seal
        or tuple(_value(capture, "expected_stream_files") or ())
        != expected_streams
    ):
        _fail(
            "layer3_origin_counter_authority_mismatch",
            "The historical log capture contradicts its campaign authority.",
        )

    root = evidence_root.absolute()
    candidate = root.joinpath(
        *PurePosixPath(expected_log_dir).parts,
        "http.jsonl",
    )
    _assert_counter_path_no_reparse(candidate)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        file_stat = os.stat(resolved, follow_symlinks=False)
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_counter_path_unavailable",
            "The protected HTTP counter path is unavailable.",
        ) from exc
    if (
        not resolved_root.is_dir()
        or resolved.parent != resolved_root / "logs" / campaign_fingerprint
        or not stat.S_ISREG(file_stat.st_mode)
    ):
        _fail(
            "layer3_origin_counter_path_mismatch",
            "The HTTP counter path does not equal the protected capture path.",
        )
    return resolved


def _load_sciencebase_bindings(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
    raw_size: int,
) -> dict[str, str | None]:
    version_id = _required_text(
        target.dataset_version_id,
        field="dataset_version_id",
    )
    version = db.get(DatasetVersion, version_id)
    if version is None or version.dataset_id != target.dataset_id:
        _fail(
            "layer3_origin_dataset_version_mismatch",
            "The target dataset version relationship is missing or contradictory.",
        )
    if _normalized_sha256(
        version.content_hash,
        field="DatasetVersion.content_hash",
    ) != raw_sha256:
        _fail(
            "layer3_origin_dataset_version_hash_mismatch",
            "DatasetVersion.content_hash does not equal the raw-byte hash.",
        )
    provenance = _one(
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.connector_run_id == run.connector_run_id)
        .filter(DatasetSourceProvenance.dataset_version_id == version_id)
        .all(),
        code="layer3_origin_provenance_cardinality",
        label="dataset source-provenance row",
    )
    if (
        _normalized_sha256(
            provenance.downloaded_sha256,
            field="DatasetSourceProvenance.downloaded_sha256",
        )
        != raw_sha256
        or provenance.source_artifact_key != target.source_artifact_key
        or provenance.sciencebase_item_id != target.sciencebase_item_id
        or provenance.sciencebase_file_name != target.sciencebase_file_name
        or not _same_storage_reference(
            provenance.raw_storage_ref,
            target.raw_storage_ref,
        )
    ):
        _fail(
            "layer3_origin_provenance_mismatch",
            "Dataset source provenance contradicts the connector target.",
        )

    intake = _one(
        db.query(L3ConnectorSourceIntakeRecord)
        .filter(
            L3ConnectorSourceIntakeRecord.connector_run_id
            == run.connector_run_id
        )
        .filter(
            L3ConnectorSourceIntakeRecord.connector_run_target_id
            == target.connector_run_target_id
        )
        .all(),
        code="layer3_origin_source_intake_cardinality",
        label="connector source-intake row",
    )
    if (
        intake.connector_key != run.connector_key
        or intake.content_sha256 != raw_sha256
        or intake.content_size_bytes != raw_size
        or intake.original_filename != target.sciencebase_file_name
        or not _same_storage_reference(intake.storage_ref, target.raw_storage_ref)
    ):
        _fail(
            "layer3_origin_source_intake_mismatch",
            "Connector source intake contradicts the connector target bytes.",
        )
    return {
        "dataset_id": str(version.dataset_id),
        "dataset_version_id": str(version.dataset_version_id),
        "dataset_source_provenance_id": str(
            provenance.dataset_source_provenance_id
        ),
        "connector_source_intake_record_id": str(
            intake.connector_source_intake_record_id
        ),
        "aps_content_linkage_id": None,
        "content_id": None,
    }


def _load_nrc_bindings(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
) -> dict[str, str | None]:
    linkage = _one(
        db.query(ApsContentLinkage)
        .filter(ApsContentLinkage.run_id == run.connector_run_id)
        .filter(
            ApsContentLinkage.target_id
            == target.connector_run_target_id
        )
        .all(),
        code="layer3_origin_aps_linkage_cardinality",
        label="APS content-linkage row",
    )
    accession = _required_text(
        linkage.accession_number,
        field="ApsContentLinkage.accession_number",
    )
    if (
        accession != _FIXTURE_ACCESSION
        or target.stable_release_key != accession
        or _normalized_sha256(
            linkage.blob_sha256,
            field="ApsContentLinkage.blob_sha256",
        )
        != raw_sha256
        or not _same_storage_reference(
            linkage.blob_ref,
            target.raw_storage_ref,
        )
    ):
        _fail(
            "layer3_origin_aps_linkage_mismatch",
            "APS content linkage contradicts the connector target bytes.",
        )
    return {
        "dataset_id": None,
        "dataset_version_id": None,
        "dataset_source_provenance_id": None,
        "connector_source_intake_record_id": None,
        "aps_content_linkage_id": str(linkage.aps_content_linkage_id),
        "content_id": _required_text(
            linkage.content_id,
            field="ApsContentLinkage.content_id",
        ),
    }


def _strict_json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = strict_json_loads(raw)
    except (TypeError, ValueError) as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_fixture_manifest_invalid",
            f"{label} is not strict canonical evidence.",
        ) from exc
    if not isinstance(parsed, dict):
        _fail(
            "layer3_origin_fixture_manifest_invalid",
            f"{label} root must be an object.",
        )
    return parsed


def _derive_offline_fixture_bindings(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_path: Path,
    raw_sha256: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    if (
        run.connector_key != "nrc_adams_aps"
        or run.source_mode != OFFLINE_FIXTURE_PROOF_CLASS
        or raw_path.resolve() != (_fixture_root() / _FIXTURE_FILE_NAME)
        or target.stable_release_key != _FIXTURE_ACCESSION
    ):
        _fail(
            "layer3_origin_fixture_source_not_admitted",
            "offline_fixture requires the one fixed manifest-bound NRC source.",
        )
    config = run.request_config_json
    if isinstance(config, Mapping) and config.get("connector_egress_arming") is not None:
        _fail(
            "layer3_origin_fixture_has_strict_arming",
            "A fixed offline fixture cannot carry a strict live arming.",
        )
    manifest_path = _fixture_root() / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_fixture_manifest_missing",
            "The fixed fixture manifest is unavailable.",
        ) from exc
    manifest = _strict_json_object(
        manifest_bytes,
        label="NRC fixture manifest",
    )
    entries = manifest.get("entries")
    if (
        manifest.get("schema_id") != "aps.document_corpus_manifest.v2"
        or not isinstance(entries, list)
    ):
        _fail(
            "layer3_origin_fixture_manifest_invalid",
            "The fixed fixture manifest schema is not admitted.",
        )
    matches = [
        entry
        for entry in entries
        if isinstance(entry, Mapping)
        and entry.get("fixture_id") == _FIXTURE_ID
        and entry.get("path") == _FIXTURE_FILE_NAME
        and entry.get("declared_content_type") == "application/pdf"
    ]
    if len(matches) != 1:
        _fail(
            "layer3_origin_fixture_manifest_invalid",
            "The fixed fixture must have exactly one manifest entry.",
            details={"count": len(matches)},
        )
    return (
        {
            "campaign_id": None,
            "campaign_fingerprint": None,
            "campaign_definition_sha256": None,
            "campaign_introduction_index_revision": None,
            "campaign_introduction_index_sha256": None,
            "arming_fingerprint": None,
            "grant_sha256": None,
            "canonical_grant_fingerprint": None,
            "grant_consumption_marker_sha256": None,
            "ledger_terminal_hash": None,
            "fixture_id": _FIXTURE_ID,
            "fixture_manifest_ref": _FIXTURE_MANIFEST_REF,
            "fixture_manifest_sha256": hashlib.sha256(
                manifest_bytes
            ).hexdigest(),
            "fixture_source_sha256": raw_sha256,
        },
        {"accession_number": _FIXTURE_ACCESSION},
    )


def _canonical_authority_fields(
    evidence: VerifiedHistoricalGrantEvidence,
) -> dict[str, Any]:
    grant = _value(evidence, "model")
    definition = _value(evidence, "definition_model")
    return canonical_arming_payload(
        {
            "schema_id": STRICT_ARMING_SCHEMA_ID,
            "connector_key": _value(grant, "connector_key"),
            "campaign_id": str(_value(grant, "campaign_id")),
            "campaign_definition_sha256": _value(
                evidence,
                "raw_definition_sha256",
            ),
            "campaign_fingerprint": _value(
                evidence,
                "canonical_campaign_fingerprint",
            ),
            "grant_sha256": _value(evidence, "raw_sha256"),
            "canonical_grant_fingerprint": _value(
                evidence,
                "canonical_fingerprint",
            ),
            "campaign_introduction_index_revision": _value(
                evidence,
                "introduction_index_revision",
            ),
            "campaign_introduction_index_sha256": _value(
                evidence,
                "introduction_index_sha256",
            ),
            "code_revision": _value(grant, "code_revision"),
            "grant_id": _value(grant, "grant_id"),
            "arming_nonce": _value(grant, "arming_nonce"),
            "max_armings": _value(grant, "max_armings"),
            "supersedes_grant_sha256": _value(
                grant,
                "supersedes_grant_sha256",
            ),
            "operator_mode": _value(grant, "operator_mode"),
            "non_authorities": _value(grant, "non_authorities"),
            "max_physical_requests": _value(
                grant,
                "max_physical_requests",
            ),
            "max_run_bytes": _value(grant, "max_run_bytes"),
            "max_single_send_detection_allowance_bytes": _value(
                grant,
                "max_single_send_detection_allowance_bytes",
            ),
            "request_timeout_seconds": _value(
                grant,
                "request_timeout_seconds",
            ),
            "min_request_interval_ms": _value(
                grant,
                "min_request_interval_ms",
            ),
            "target": _value(grant, "target"),
            "request_rules": _value(grant, "request_rules"),
            "grant_issued_at": _value(grant, "issued_at"),
            "grant_expires_at": _value(grant, "expires_at"),
            "campaign_not_before": _value(definition, "not_before"),
            "campaign_expires_at": _value(definition, "expires_at"),
        }
    )


def _validate_authorization_receipt_binding(
    envelope: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
) -> None:
    receipt = envelope.get("authorization_receipt")
    if not isinstance(receipt, Mapping):
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The strict arming lacks its server-derived authorization receipt.",
            details={"field": "authorization_receipt"},
        )
    binding_values = {
        "schema_id": "project6.connector_egress_authorization_receipt.v1",
        "connector_key": expected["connector_key"],
        "campaign_id": expected["campaign_id"],
        "campaign_fingerprint": expected["campaign_fingerprint"],
        "campaign_definition_sha256": expected[
            "campaign_definition_sha256"
        ],
        "grant_sha256": expected["grant_sha256"],
        "canonical_grant_fingerprint": expected[
            "canonical_grant_fingerprint"
        ],
        "introduction_index_revision": expected[
            "campaign_introduction_index_revision"
        ],
        "introduction_index_sha256": expected[
            "campaign_introduction_index_sha256"
        ],
        "access": "write",
    }
    variable_fields = {
        "operator_ref_hash",
        "workspace_ref_hash",
        "auth_owner_mode",
        "authorization_mode",
        "role",
    }
    if set(receipt) != set(binding_values) | variable_fields:
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The authorization receipt has missing or undeclared fields.",
            details={"field": "authorization_receipt"},
        )
    for field, expected_value in binding_values.items():
        if receipt.get(field) != expected_value:
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "The authorization receipt contradicts protected authority.",
                details={"field": f"authorization_receipt.{field}"},
            )
    for field in ("operator_ref_hash", "workspace_ref_hash"):
        normalized = _normalized_sha256(
            receipt.get(field),
            field=f"authorization_receipt.{field}",
        )
        if receipt.get(field) != normalized:
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "The authorization receipt hash is not canonical.",
                details={"field": f"authorization_receipt.{field}"},
            )
    _required_text(
        receipt.get("auth_owner_mode"),
        field="authorization_receipt.auth_owner_mode",
    )
    authorization_mode = receipt.get("authorization_mode")
    role = receipt.get("role")
    if (
        authorization_mode == "identity_presence"
        and role is not None
    ) or (
        authorization_mode == "role_enforcing"
        and role != "owner"
    ) or authorization_mode not in {"identity_presence", "role_enforcing"}:
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The authorization receipt owner posture is contradictory.",
            details={"field": "authorization_receipt.authorization_mode"},
        )


def _validate_full_authority_binding(
    *,
    connector_key: str,
    envelope: Mapping[str, Any],
    evidence: VerifiedHistoricalGrantEvidence,
) -> dict[str, str]:
    expected = _canonical_authority_fields(evidence)
    for field, expected_value in expected.items():
        if envelope.get(field) != expected_value:
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "Protected authority does not equal the immutable arming.",
                details={"field": field},
            )
    _validate_authorization_receipt_binding(
        envelope,
        expected=expected,
    )
    allowed_fields = set(expected) | {
        "arming_fingerprint",
        "authorization_receipt",
    }
    predecessor_bindings: dict[str, str] = {}
    predecessor_fields = {
        "predecessor_nrc_connector_run_id",
        "predecessor_nrc_ledger_terminal_hash",
    }
    if connector_key == "sciencebase_mcs":
        predecessor_bindings = {
            "predecessor_nrc_connector_run_id": _required_text(
                envelope.get("predecessor_nrc_connector_run_id"),
                field="predecessor_nrc_connector_run_id",
            ),
            "predecessor_nrc_ledger_terminal_hash": _normalized_sha256(
                envelope.get("predecessor_nrc_ledger_terminal_hash"),
                field="predecessor_nrc_ledger_terminal_hash",
            ),
        }
        allowed_fields |= predecessor_fields
    elif predecessor_fields & set(envelope):
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "NRC arming cannot claim an NRC predecessor.",
            details={"field": "predecessor_nrc_connector_run_id"},
        )
    if set(envelope) != allowed_fields:
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The strict arming has missing or undeclared fields.",
            details={"field": "connector_egress_arming"},
        )
    return predecessor_bindings


_PATH_CLASS_BY_RULE = {
    "sciencebase_item_exact_v1": "sciencebase_item_exact",
    "sciencebase_file_exact_v1": "sciencebase_file_exact",
    "nrc_get_document_exact_v1": "nrc_accession_exact",
    "nrc_public_pdf_exact_v1": "nrc_public_pdf_exact",
}
_QUERY_CLASS_BY_RULE = {
    "format_json_exact_v1": "format_json_exact",
    "sciencebase_exact_file_selector_v1": (
        "exact_single_f_expected_filename"
    ),
    "none_v1": "none",
}


def _validate_terminal_request_identities(
    entries: Sequence[Mapping[str, Any]],
    *,
    grant: object,
) -> None:
    canonical = canonical_arming_payload(
        {"request_rules": _value(grant, "request_rules")}
    )
    rules = canonical.get("request_rules")
    if not isinstance(rules, list):
        _fail(
            "layer3_origin_terminal_request_identity_mismatch",
            "Protected grant request rules are not canonical.",
        )
    for entry in entries:
        ordinal = entry.get("ordinal")
        stage = entry.get("stage")
        matches = [
            rule
            for rule in rules
            if isinstance(rule, Mapping)
            and rule.get("ordinal") == ordinal
            and rule.get("stage") == stage
        ]
        if len(matches) != 1:
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal request does not select one protected grant rule.",
                details={"ordinal": ordinal, "stage": stage},
            )
        rule = matches[0]
        allowed_hosts = rule.get("allowed_hosts")
        expected_identity = {
            "method": rule.get("method"),
            "path_class": _PATH_CLASS_BY_RULE.get(
                str(rule.get("path_rule_id"))
            ),
            "query_class": _QUERY_CLASS_BY_RULE.get(
                str(rule.get("query_rule_id"))
            ),
            "credential_audience": rule.get("credential_audience"),
        }
        if (
            not isinstance(allowed_hosts, list)
            or entry.get("host") not in allowed_hosts
            or any(
                entry.get(field) != expected_value
                for field, expected_value in expected_identity.items()
            )
        ):
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal request identity contradicts its protected grant rule.",
                details={"ordinal": ordinal, "stage": stage},
            )
        fingerprint = _normalized_sha256(
            entry.get("request_fingerprint"),
            field=f"ledger.request_fingerprint.{ordinal}",
        )
        if entry.get("request_fingerprint") != fingerprint:
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal request fingerprint is not canonical.",
                details={"ordinal": ordinal, "stage": stage},
            )
        byte_count = entry.get("byte_count")
        max_response_bytes = _positive_int(
            rule.get("max_response_bytes"),
            field=f"request_rule.max_response_bytes.{ordinal}",
        )
        if (
            isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count < 0
            or byte_count > max_response_bytes
        ):
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal response exceeds or contradicts its protected rule.",
                details={"ordinal": ordinal, "stage": stage},
            )


def _validate_target_against_grant(
    *,
    connector_key: str,
    target: ConnectorRunTarget,
    grant_target: object,
) -> dict[str, str]:
    if connector_key == "sciencebase_mcs":
        item_id = _required_text(
            target.sciencebase_item_id,
            field="sciencebase_item_id",
        )
        file_name = _required_text(
            target.sciencebase_file_name,
            field="sciencebase_file_name",
        )
        if (
            _value(grant_target, "connector_key") != connector_key
            or _value(grant_target, "item_id") != item_id
            or _value(grant_target, "exact_file_name") != file_name
        ):
            _fail(
                "layer3_origin_target_identity_mismatch",
                "The ScienceBase target does not equal the protected grant target.",
            )
        return {"item_id": item_id, "exact_file_name": file_name}
    if connector_key == "nrc_adams_aps":
        accession = _required_text(
            target.stable_release_key,
            field="target accession_number",
        )
        if (
            _value(grant_target, "connector_key") != connector_key
            or _value(grant_target, "accession_number") != accession
        ):
            _fail(
                "layer3_origin_target_identity_mismatch",
                "The NRC target does not equal the protected grant target.",
            )
        return {"accession_number": accession}
    _fail(
        "layer3_origin_connector_not_implemented",
        "This connector-origin branch is not implemented.",
    )


def _validate_fresh_live_evidence(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    envelope: Mapping[str, Any],
    raw_sha256: str,
    raw_size: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    if envelope.get("schema_id") != STRICT_ARMING_SCHEMA_ID:
        _fail(
            "layer3_origin_strict_arming_missing",
            "fresh_live requires the strict connector-egress arming schema.",
        )
    if envelope.get("connector_key") != run.connector_key:
        _fail(
            "layer3_origin_arming_connector_mismatch",
            "The strict arming connector does not match the run.",
        )
    stored_arming_hash = _normalized_sha256(
        envelope.get("arming_fingerprint"),
        field="arming_fingerprint",
    )
    if _compute_arming_fingerprint(envelope) != stored_arming_hash:
        _fail(
            "layer3_origin_arming_fingerprint_mismatch",
            "The strict arming fingerprint does not rederive.",
        )
    run_fingerprint = _normalized_sha256(
        run.request_fingerprint,
        field="ConnectorRun.request_fingerprint",
    )
    if run_fingerprint != stored_arming_hash:
        _fail(
            "layer3_origin_arming_fingerprint_mismatch",
            "The connector run fingerprint contradicts its strict arming.",
        )

    campaign_id = _required_text(
        envelope.get("campaign_id"),
        field="campaign_id",
    )
    campaign_fingerprint = _normalized_sha256(
        envelope.get("campaign_fingerprint"),
        field="campaign_fingerprint",
    )
    grant_sha256 = _normalized_sha256(
        envelope.get("grant_sha256"),
        field="grant_sha256",
    )
    evidence = _resolve_historical_evidence(
        connector_key=run.connector_key,
        campaign_id=campaign_id,
        expected_campaign_fingerprint=campaign_fingerprint,
        expected_grant_sha256=grant_sha256,
    )
    definition = _value(evidence, "definition_model")
    grant = _value(evidence, "model")
    marker = _value(evidence, "marker_model")
    predecessor_bindings = _validate_full_authority_binding(
        connector_key=run.connector_key,
        envelope=envelope,
        evidence=evidence,
    )
    expected_pairs = (
        ("campaign_definition_sha256", "raw_definition_sha256"),
        ("campaign_fingerprint", "canonical_campaign_fingerprint"),
        ("grant_sha256", "raw_sha256"),
        ("canonical_grant_fingerprint", "canonical_fingerprint"),
        (
            "campaign_introduction_index_revision",
            "introduction_index_revision",
        ),
        (
            "campaign_introduction_index_sha256",
            "introduction_index_sha256",
        ),
    )
    for envelope_field, evidence_field in expected_pairs:
        if str(envelope.get(envelope_field)) != str(
            _value(evidence, evidence_field)
        ):
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "Protected evidence does not equal the immutable arming binding.",
                details={"field": envelope_field},
            )
    if (
        str(_value(definition, "campaign_id")) != campaign_id
        or str(_value(grant, "campaign_id")) != campaign_id
        or _value(grant, "connector_key") != run.connector_key
        or str(_value(grant, "code_revision"))
        != str(envelope.get("code_revision"))
        or str(_value(definition, "code_revision"))
        != str(envelope.get("code_revision"))
    ):
        _fail(
            "layer3_origin_authority_document_mismatch",
            "Definition or grant identity contradicts the arming.",
        )
    if (
        str(_value(marker, "connector_run_id")) != run.connector_run_id
        or _value(marker, "connector_key") != run.connector_key
        or str(_value(marker, "campaign_id")) != campaign_id
        or str(_value(marker, "raw_grant_sha256")) != grant_sha256
    ):
        _fail(
            "layer3_origin_consumption_marker_mismatch",
            "The indexed one-use consumption marker contradicts the run.",
        )
    target_identity = _validate_target_against_grant(
        connector_key=run.connector_key,
        target=target,
        grant_target=_value(grant, "target"),
    )

    counter_path = _resolve_historical_counter_path(
        evidence,
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
    )
    ledger = _derive_terminal_ledger(
        db,
        run.connector_run_id,
        counter_path=counter_path,
    )
    if _value(ledger, "eligible") is not True:
        _fail(
            "layer3_origin_terminal_ledger_ineligible",
            "fresh_live requires a complete eligible terminal request ledger.",
        )
    projection = _value(ledger, "canonical_projection")
    if not isinstance(projection, Mapping):
        _fail(
            "layer3_origin_terminal_ledger_invalid",
            "The terminal ledger lacks a canonical projection.",
        )
    projection_dict = dict(projection)
    ledger_hash = _normalized_sha256(
        _value(ledger, "ledger_terminal_hash"),
        field="ledger_terminal_hash",
    )
    if _stable_hash(projection_dict) != ledger_hash:
        _fail(
            "layer3_origin_terminal_ledger_hash_mismatch",
            "The terminal-ledger hash does not rederive.",
        )
    for field, expected in (
        ("schema_id", TERMINAL_LEDGER_SCHEMA_ID),
        ("connector_run_id", run.connector_run_id),
        ("connector_key", run.connector_key),
        ("campaign_fingerprint", campaign_fingerprint),
        ("arming_fingerprint", stored_arming_hash),
        ("grant_sha256", grant_sha256),
        (
            "campaign_introduction_index_revision",
            envelope.get("campaign_introduction_index_revision"),
        ),
        (
            "campaign_introduction_index_sha256",
            envelope.get("campaign_introduction_index_sha256"),
        ),
        (
            "frozen_max_physical_requests",
            envelope.get("max_physical_requests"),
        ),
    ):
        if projection_dict.get(field) != expected:
            _fail(
                "layer3_origin_terminal_ledger_binding_mismatch",
                "The terminal ledger contradicts the strict arming.",
                details={"field": field},
            )
    entries = projection_dict.get("entries")
    if not isinstance(entries, list) or entries != list(
        _value(ledger, "entries") or ()
    ):
        _fail(
            "layer3_origin_terminal_ledger_invalid",
            "The terminal ledger entries are not canonical.",
        )
    if not all(isinstance(item, Mapping) for item in entries):
        _fail(
            "layer3_origin_terminal_ledger_invalid",
            "The terminal ledger contains a non-object entry.",
        )
    typed_entries = [dict(item) for item in entries]
    actual_sequence = [
        (item.get("ordinal"), item.get("stage"))
        for item in typed_entries
    ]
    admitted_sequences = (
        (
            ((1, "item_hydration"), (2, "artifact")),
            (
                (1, "item_hydration"),
                (2, "artifact"),
                (3, "artifact_redirect"),
            ),
        )
        if run.connector_key == "sciencebase_mcs"
        else (((1, "exact_accession_api"), (2, "artifact")),)
    )
    if tuple(actual_sequence) not in admitted_sequences:
        _fail(
            "layer3_origin_request_sequence_mismatch",
            "The terminal ledger has the wrong physical-send sequence.",
        )
    _validate_terminal_request_identities(
        typed_entries,
        grant=grant,
    )
    if (
        run.connector_key == "sciencebase_mcs"
        and len(typed_entries) == 3
        and typed_entries[1].get("response_status")
        not in {301, 302, 303, 307, 308}
    ):
        _fail(
            "layer3_origin_redirect_sequence_mismatch",
            "A ScienceBase redirect send requires an admitted redirect response.",
        )
    artifact = typed_entries[-1]
    if (
        artifact.get("outcome_class") != "completed"
        or artifact.get("response_status") != 200
        or artifact.get("byte_count") != raw_size
        or artifact.get("body_sha256") != raw_sha256
    ):
        _fail(
            "layer3_origin_artifact_completion_mismatch",
            "The terminal artifact completion does not equal admitted raw bytes.",
        )
    campaign_start = _as_utc(
        _value(definition, "not_before"),
        field="campaign.not_before",
    )
    campaign_end = _as_utc(
        _value(definition, "expires_at"),
        field="campaign.expires_at",
    )
    grant_start = _as_utc(_value(grant, "issued_at"), field="grant.issued_at")
    grant_end = _as_utc(_value(grant, "expires_at"), field="grant.expires_at")
    for entry in typed_entries:
        for field in ("reserved_at", "send_started_at"):
            timestamp = _as_utc(entry.get(field), field=f"ledger.{field}")
            if not (
                campaign_start <= timestamp < campaign_end
                and grant_start <= timestamp < grant_end
            ):
                _fail(
                    "layer3_origin_send_outside_authority_window",
                    "A physical-send timestamp is outside an original half-open window.",
                    details={"ordinal": entry.get("ordinal"), "field": field},
                )
    return (
        {
            "campaign_id": campaign_id,
            "campaign_fingerprint": campaign_fingerprint,
            "campaign_definition_sha256": str(
                envelope.get("campaign_definition_sha256")
            ),
            "campaign_introduction_index_revision": _positive_int(
                envelope.get("campaign_introduction_index_revision"),
                field="campaign_introduction_index_revision",
            ),
            "campaign_introduction_index_sha256": str(
                envelope.get("campaign_introduction_index_sha256")
            ),
            "arming_fingerprint": stored_arming_hash,
            "grant_sha256": grant_sha256,
            "canonical_grant_fingerprint": str(
                envelope.get("canonical_grant_fingerprint")
            ),
            "grant_consumption_marker_sha256": _normalized_sha256(
                _value(evidence, "consumption_marker_sha256"),
                field="grant_consumption_marker_sha256",
            ),
            "ledger_terminal_hash": ledger_hash,
            **predecessor_bindings,
        },
        target_identity,
    )


def derive_connector_origin_receipt(
    db: Session,
    *,
    connector_run_target_id: str,
) -> dict[str, Any]:
    """Reconstruct one connector target's origin receipt from server-owned state."""
    target_id = _required_text(
        connector_run_target_id,
        field="connector_run_target_id",
    )
    target = db.get(ConnectorRunTarget, target_id)
    if target is None:
        _fail(
            "layer3_origin_target_not_found",
            "The connector run target does not exist.",
        )
    run = db.get(ConnectorRun, target.connector_run_id)
    if run is None:
        _fail(
            "layer3_origin_run_not_found",
            "The connector run does not exist.",
        )
    if run.connector_key not in _ALLOWED_CONNECTORS:
        _fail(
            "layer3_origin_connector_not_admitted",
            "The connector is outside the dual-live origin contract.",
        )
    if run.status != "completed":
        _fail(
            "layer3_origin_run_not_completed",
            "fresh_live origin requires a completed strict connector run.",
            details={"status": run.status},
        )

    is_offline_fixture = (
        run.connector_key == "nrc_adams_aps"
        and run.source_mode == OFFLINE_FIXTURE_PROOF_CLASS
    )
    raw_path = _raw_storage_path(
        target.raw_storage_ref,
        allow_fixed_fixture=is_offline_fixture,
    )
    raw_size, raw_sha256 = _hash_file(raw_path)
    if (
        _normalized_sha256(
            target.downloaded_sha256,
            field="ConnectorRunTarget.downloaded_sha256",
        )
        != raw_sha256
    ):
        _fail(
            "layer3_origin_raw_hash_mismatch",
            "The raw bytes do not equal ConnectorRunTarget.downloaded_sha256.",
        )

    if run.connector_key == "sciencebase_mcs":
        content_bindings = _load_sciencebase_bindings(
            db,
            run=run,
            target=target,
            raw_sha256=raw_sha256,
            raw_size=raw_size,
        )
    else:
        content_bindings = _load_nrc_bindings(
            db,
            run=run,
            target=target,
            raw_sha256=raw_sha256,
        )

    if not isinstance(run.request_config_json, Mapping):
        _fail(
            "layer3_origin_request_config_invalid",
            "Connector origin requires an object request configuration.",
        )
    request_config = run.request_config_json
    envelope = request_config.get("connector_egress_arming")
    if is_offline_fixture:
        authority_bindings, target_identity = (
            _derive_offline_fixture_bindings(
                run=run,
                target=target,
                raw_path=raw_path,
                raw_sha256=raw_sha256,
            )
        )
        proof_class = OFFLINE_FIXTURE_PROOF_CLASS
    else:
        if not isinstance(envelope, Mapping):
            _fail(
                "layer3_origin_strict_arming_missing",
                "The run lacks a strict server-derived arming envelope.",
            )
        authority_bindings, target_identity = _validate_fresh_live_evidence(
            db,
            run=run,
            target=target,
            envelope=envelope,
            raw_sha256=raw_sha256,
            raw_size=raw_size,
        )
        proof_class = FRESH_LIVE_PROOF_CLASS

    receipt: dict[str, Any] = {
        "schema_id": ORIGIN_RECEIPT_SCHEMA_ID,
        "proof_class": proof_class,
        "connector_key": run.connector_key,
        "connector_run_id": run.connector_run_id,
        "connector_run_target_id": target.connector_run_target_id,
        "target_identity": target_identity,
        "source_artifact_key": _required_text(
            target.source_artifact_key,
            field="source_artifact_key",
        ),
        "raw_storage_ref": str(target.raw_storage_ref),
        "raw_content_sha256": raw_sha256,
        "raw_content_size_bytes": raw_size,
        **content_bindings,
        **authority_bindings,
    }
    receipt["receipt_hash"] = _stable_hash(receipt)
    return receipt


def assert_connector_origin_continuity(
    db: Session,
    *,
    connector_run_target_id: str,
    expected_receipt_hash: str,
    expected_bindings: Mapping[str, str],
) -> None:
    """Fail unless the stored target receipt equals a fresh reconstruction."""
    target_id = _required_text(
        connector_run_target_id,
        field="connector_run_target_id",
    )
    expected_hash = _normalized_sha256(
        expected_receipt_hash,
        field="expected_receipt_hash",
    )
    if not isinstance(expected_bindings, Mapping):
        _fail(
            "layer3_origin_expected_bindings_invalid",
            "expected_bindings must be a mapping of scalar receipt fields.",
        )
    target = db.get(ConnectorRunTarget, target_id)
    if target is None:
        _fail(
            "layer3_origin_target_not_found",
            "The connector run target does not exist.",
        )
    source_reference = (
        target.source_reference_json
        if isinstance(target.source_reference_json, Mapping)
        else {}
    )
    stored = source_reference.get(ORIGIN_RECEIPT_STORAGE_KEY)
    if not isinstance(stored, Mapping):
        _fail(
            "layer3_origin_stored_receipt_missing",
            "The target lacks its authoritative connector-origin receipt.",
        )
    for key, value in source_reference.items():
        if (
            key != ORIGIN_RECEIPT_STORAGE_KEY
            and isinstance(value, Mapping)
            and value.get("schema_id") == ORIGIN_RECEIPT_SCHEMA_ID
        ):
            _fail(
                "layer3_origin_duplicate_canonical_receipt",
                "The target carries more than one canonical origin receipt.",
            )
    stored_dict = dict(stored)
    stored_hash = _normalized_sha256(
        stored_dict.get("receipt_hash"),
        field="stored receipt_hash",
    )
    stored_preimage = {
        key: value
        for key, value in stored_dict.items()
        if key != "receipt_hash"
    }
    if _stable_hash(stored_preimage) != stored_hash:
        _fail(
            "layer3_origin_stored_receipt_hash_mismatch",
            "The stored connector-origin receipt hash does not rederive.",
        )

    derived = derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    if (
        derived["receipt_hash"] != expected_hash
        or stored_hash != expected_hash
        or stored_dict != derived
    ):
        _fail(
            "layer3_origin_stored_receipt_mismatch",
            "The stored receipt does not equal reconstructed origin evidence.",
        )
    for field, expected in expected_bindings.items():
        if not isinstance(field, str) or not isinstance(expected, str):
            _fail(
                "layer3_origin_expected_bindings_invalid",
                "Expected origin bindings must use string keys and values.",
            )
        actual = derived.get(field)
        if (
            actual is None
            or isinstance(actual, (Mapping, list))
            or str(actual) != expected
        ):
            _fail(
                "layer3_origin_expected_binding_mismatch",
                "A downstream origin binding does not equal the canonical receipt.",
                details={"field": field},
            )
