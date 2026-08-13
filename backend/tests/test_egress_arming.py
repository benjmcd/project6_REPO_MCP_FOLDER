from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.orm import Mapper, Session, sessionmaker

from app.core.config import settings
from app.db.session import Base
from app.models import (
    ConnectorPolicySnapshot,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunSubmission,
    ConnectorRunTarget,
)
from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    COMMON_GRANT_NON_AUTHORITIES,
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorEgressArmingIn,
    ConnectorEgressGrantV1,
    ConnectorGrantConsumptionMarkerV1,
    DualLiveCampaignDefinitionV1,
    NrcApsFreshTargetV1,
    ScienceBaseFreshTargetV1,
    expected_grant_rule_payloads,
)
from app.services import connector_egress_arming as arming_module
from app.services import connector_egress_transport as transport_module
from app.services import layer3_origin_continuity as origin_module
from app.services import nrc_aps_artifact_ingestion as artifact_module
from app.services.connector_egress_arming import (
    ConnectorEgressArmingError,
    _assert_supersession_contract,
    _derive_arming_expiry,
    canonical_arming_payload,
    claim_connector_egress_arming,
    compute_arming_fingerprint,
    compute_parent_arming_id,
    commit_derived_url_arming,
    create_connector_egress_arming,
    evaluate_nrc_acquisition_success,
    finalize_strict_run,
    has_reserved_egress_provenance,
    is_strict_egress_run,
    refresh_strict_run_lease,
    resolve_current_egress_authority,
)
from app.services.connector_egress_authorization import canonical_json_bytes


COUNTER_RUNTIME_INSTANCE_ID = "223e4567-e89b-42d3-a456-426614174000"
COUNTER_PROCESS_BOOT_ID = "7" * 64


def _counter_record(
    *,
    schema_id: str,
    ordinal: int,
    stage: str,
    request_fingerprint: str,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_id": schema_id,
        "ordinal": ordinal,
        "stage": stage,
        "request_fingerprint": request_fingerprint,
        "canonical_status_header_bytes": 1,
        "delivered_body_bytes": 1,
        "decoded_body_bytes": 1,
        "decoded_body_sha256": "1" * 64,
        "response_status": 200,
        "error_class": None,
        "monotonic_started_at": float(ordinal),
        "monotonic_stopped_at": float(ordinal),
        "evidence_started_at": "2026-01-01T00:00:00.000000Z",
        "evidence_stopped_at": "2026-01-01T00:00:00.000000Z",
    }
    if schema_id == "project6.connector_http_counter.v2":
        record.update(
            runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
            process_boot_id=COUNTER_PROCESS_BOOT_ID,
        )
    return record


def test_canonical_arming_fingerprint_is_key_order_independent() -> None:
    left = {
        "campaign": {"id": "campaign-1", "revision": 7},
        "limits": {"bytes": 1024, "requests": 2},
    }
    right = {
        "limits": {"requests": 2, "bytes": 1024},
        "campaign": {"revision": 7, "id": "campaign-1"},
    }

    assert canonical_arming_payload(left) == canonical_arming_payload(right)
    assert compute_arming_fingerprint(left) == compute_arming_fingerprint(right)


def test_arming_fingerprint_excludes_only_itself() -> None:
    baseline = {
        "campaign_id": "campaign-1",
        "arming_fingerprint": "0" * 64,
        "grant_sha256": "1" * 64,
    }

    assert compute_arming_fingerprint(baseline) == compute_arming_fingerprint(
        {**baseline, "arming_fingerprint": "f" * 64}
    )
    assert compute_arming_fingerprint(baseline) != compute_arming_fingerprint(
        {**baseline, "grant_sha256": "2" * 64}
    )


def test_parent_arming_id_is_deterministic_uuid5() -> None:
    first = compute_parent_arming_id(
        connector_key="nrc_adams_aps",
        campaign_id="27693345-6a47-45bb-97a7-44c2932ef76b",
        grant_sha256="a" * 64,
        arming_nonce=UUID("ba4613f4-d8e5-4bfd-9447-04d21dbf951b"),
    )
    second = compute_parent_arming_id(
        connector_key="nrc_adams_aps",
        campaign_id="27693345-6a47-45bb-97a7-44c2932ef76b",
        grant_sha256="a" * 64,
        arming_nonce=UUID("ba4613f4-d8e5-4bfd-9447-04d21dbf951b"),
    )

    assert first == second
    assert UUID(first).version == 5


NOW = datetime.now(UTC).replace(microsecond=0)
CAMPAIGN_ID = "27693345-6a47-45bb-97a7-44c2932ef76b"
CAMPAIGN_FINGERPRINT = "c" * 64
CAMPAIGN_RAW_SHA256 = "d" * 64
CODE_REVISION = "e" * 40
GRANT_SHA256 = "a" * 64
GRANT_FINGERPRINT = "b" * 64
ARMING_NONCE = UUID("ba4613f4-d8e5-4bfd-9447-04d21dbf951b")


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    return factory()


def _campaign() -> DualLiveCampaignDefinitionV1:
    return DualLiveCampaignDefinitionV1(
        schema_id="project6.dual_live_campaign_definition.v1",
        campaign_id=CAMPAIGN_ID,
        code_revision=CODE_REVISION,
        connector_keys=("sciencebase_mcs", "nrc_adams_aps"),
        sciencebase_target=ScienceBaseFreshTargetV1(
            connector_key="sciencebase_mcs",
            item_id="63d1a3c6d34e06fef15006be",
            exact_file_name="mcs2023-germa_salient.csv",
            locator_key="downloadUri",
        ),
        nrc_target=NrcApsFreshTargetV1(
            connector_key="nrc_adams_aps",
            accession_number="ML17123A319",
        ),
        acceptance_profile="dual_live_to_internal_handoff_v1",
        evidence_profile="dual_live_evidence_v1",
        review_policy="security_egress_and_layer3_integrity_v1",
        required_review_roles=("security_egress", "layer3_integrity"),
        execution_order="nrc_then_sciencebase",
        package_kinds=("canonical_internal", "user_facing", "review_facing"),
        not_before=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=1),
        non_authorities=CAMPAIGN_NON_AUTHORITIES,
    )


def _grant(
    tmp_path,
    *,
    connector_key: str = "nrc_adams_aps",
    marker_exists: bool = False,
):
    target = (
        NrcApsFreshTargetV1(
            connector_key="nrc_adams_aps",
            accession_number="ML17123A319",
        )
        if connector_key == "nrc_adams_aps"
        else ScienceBaseFreshTargetV1(
            connector_key="sciencebase_mcs",
            item_id="63d1a3c6d34e06fef15006be",
            exact_file_name="mcs2023-germa_salient.csv",
            locator_key="downloadUri",
        )
    )
    model = ConnectorEgressGrantV1(
        schema_id="project6.connector_egress_grant.v1",
        grant_id=f"grant-{connector_key}",
        connector_key=connector_key,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=CAMPAIGN_RAW_SHA256,
        code_revision=CODE_REVISION,
        arming_nonce=ARMING_NONCE,
        max_armings=1,
        supersedes_grant_sha256=None,
        issued_at=NOW - timedelta(minutes=30),
        expires_at=NOW + timedelta(minutes=30),
        operator_mode="local_loopback",
        target=target,
        request_rules=expected_grant_rule_payloads(connector_key),
        max_physical_requests=2 if connector_key == "nrc_adams_aps" else 3,
        max_run_bytes=70 * 1024 * 1024,
        max_single_send_detection_allowance_bytes=6_684_672,
        request_timeout_seconds=30,
        min_request_interval_ms=500,
        non_authorities=(
            NRC_GRANT_NON_AUTHORITIES
            if connector_key == "nrc_adams_aps"
            else COMMON_GRANT_NON_AUTHORITIES
        ),
    )
    run_id = compute_parent_arming_id(
        connector_key=connector_key,
        campaign_id=CAMPAIGN_ID,
        grant_sha256=GRANT_SHA256,
        arming_nonce=ARMING_NONCE,
    )
    marker = ConnectorGrantConsumptionMarkerV1(
        schema_id="project6.connector_grant_consumption.v1",
        connector_key=connector_key,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=CAMPAIGN_RAW_SHA256,
        raw_grant_sha256=GRANT_SHA256,
        canonical_grant_fingerprint=GRANT_FINGERPRINT,
        arming_nonce=ARMING_NONCE,
        connector_run_id=run_id,
        max_armings=1,
    )
    marker_bytes = json.dumps(
        marker.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    marker_path = tmp_path / f"{GRANT_SHA256}.json"
    if marker_exists:
        marker_path.write_bytes(marker_bytes)
    verified_campaign = SimpleNamespace(
        model=_campaign(),
        raw_bytes=b"campaign",
        raw_sha256=CAMPAIGN_RAW_SHA256,
        canonical_bytes=b"canonical-campaign",
        canonical_fingerprint=CAMPAIGN_FINGERPRINT,
        introduction_index_revision=1,
        introduction_index_sha256="f" * 64,
        evidence_root=tmp_path,
        definition_archive_path=tmp_path / "definition.json",
        index_chain=(),
    )
    return SimpleNamespace(
        model=model,
        raw_bytes=b"grant",
        raw_sha256=GRANT_SHA256,
        canonical_bytes=b"canonical-grant",
        canonical_fingerprint=GRANT_FINGERPRINT,
        verified_campaign=verified_campaign,
        grant_archive_path=tmp_path / "grant.json",
        consumption_marker_path=marker_path,
        consumption_marker_sha256=hashlib.sha256(marker_bytes).hexdigest(),
        consumption_marker_present=marker_exists,
    )


def _operator_receipt(grant) -> dict[str, object]:
    campaign = grant.verified_campaign
    return {
        "schema_id": "project6.connector_egress_authorization_receipt.v1",
        "connector_key": grant.model.connector_key,
        "campaign_id": str(campaign.model.campaign_id),
        "campaign_fingerprint": campaign.canonical_fingerprint,
        "campaign_definition_sha256": campaign.raw_sha256,
        "grant_sha256": grant.raw_sha256,
        "canonical_grant_fingerprint": grant.canonical_fingerprint,
        "introduction_index_revision": campaign.introduction_index_revision,
        "introduction_index_sha256": campaign.introduction_index_sha256,
        "operator_ref_hash": "1" * 64,
        "workspace_ref_hash": "2" * 64,
        "auth_owner_mode": "header_presence",
        "authorization_mode": "identity_presence",
        "role": None,
        "access": "write",
    }


def _arming_payload(
    connector_key: str = "nrc_adams_aps",
    *,
    client_request_id: str = "arm-001",
) -> ConnectorEgressArmingIn:
    return ConnectorEgressArmingIn(
        schema_id="project6.connector_egress_arming.v1",
        client_request_id=client_request_id,
        connector_key=connector_key,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        grant_sha256=GRANT_SHA256,
    )


def test_arming_expiry_is_capped_by_server_ttl_and_authority_windows(
    tmp_path, monkeypatch
) -> None:
    grant = _grant(tmp_path)
    monkeypatch.setattr(
        settings,
        "connector_egress_arming_max_ttl_seconds",
        60,
    )
    assert _derive_arming_expiry(grant, now=NOW) == NOW + timedelta(seconds=60)

    grant.model = grant.model.model_copy(
        update={"expires_at": NOW + timedelta(seconds=30)}
    )
    assert _derive_arming_expiry(grant, now=NOW) == NOW + timedelta(seconds=30)

    grant.verified_campaign.model = (
        grant.verified_campaign.model.model_copy(
            update={"expires_at": NOW + timedelta(seconds=20)}
        )
    )
    assert _derive_arming_expiry(grant, now=NOW) == NOW + timedelta(seconds=20)


@pytest.mark.parametrize("ttl_seconds", [0, -1, 10**30])
def test_invalid_or_overflowing_arming_ttl_fails_closed(
    tmp_path, monkeypatch, ttl_seconds: int
) -> None:
    grant = _grant(tmp_path)
    monkeypatch.setattr(
        settings,
        "connector_egress_arming_max_ttl_seconds",
        ttl_seconds,
    )
    with pytest.raises(ConnectorEgressArmingError):
        _derive_arming_expiry(grant, now=NOW)


def test_arming_expiry_uses_half_open_boundary(tmp_path, monkeypatch) -> None:
    grant = _grant(tmp_path)
    grant.model = grant.model.model_copy(update={"expires_at": NOW})
    monkeypatch.setattr(
        settings,
        "connector_egress_arming_max_ttl_seconds",
        60,
    )
    with pytest.raises(ConnectorEgressArmingError) as exc:
        _derive_arming_expiry(grant, now=NOW)
    assert exc.value.code == "connector_arming_window_closed"


def test_create_arming_persists_one_immutable_envelope_and_marker(tmp_path) -> None:
    db = _session()
    grant = _grant(tmp_path)

    run, created = create_connector_egress_arming(
        db,
        payload=_arming_payload(),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )

    assert created is True
    assert run.status == "armed"
    assert run.request_fingerprint
    assert grant.consumption_marker_path.is_file()
    envelope = run.request_config_json["connector_egress_arming"]
    assert envelope["schema_id"] == "project6.connector_egress_arming.v1"
    assert envelope["campaign_definition_sha256"] == CAMPAIGN_RAW_SHA256
    assert envelope["campaign_fingerprint"] == CAMPAIGN_FINGERPRINT
    assert envelope["grant_sha256"] == GRANT_SHA256
    assert envelope["campaign_introduction_index_revision"] == 1
    assert envelope["campaign_introduction_index_sha256"] == "f" * 64
    assert envelope["max_armings"] == 1
    assert envelope["operator_mode"] == "local_loopback"
    assert envelope["non_authorities"] == list(NRC_GRANT_NON_AUTHORITIES)
    assert db.scalar(select(ConnectorRunSubmission)) is not None
    assert db.scalar(select(ConnectorPolicySnapshot)) is not None
    event = db.scalar(select(ConnectorRunEvent))
    assert event is not None
    assert event.event_type == "egress_arming_created"


def test_reserved_provenance_distinguishes_valid_malformed_and_ordinary(
    tmp_path,
) -> None:
    db = _session()
    strict, _ = _created_arming(db, tmp_path)
    generic = ConnectorRun(
        connector_run_id="generic-run",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="armed",
        request_config_json={},
    )
    lookalike = ConnectorRun(
        connector_run_id="lookalike-run",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="armed",
        request_config_json={
            "connector_egress_arming": {
                "schema_id": "project6.connector_egress_arming.v0"
            }
        },
    )
    ordinary = ConnectorRun(
        connector_run_id="ordinary-run",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="public_api",
        status="pending",
        request_config_json={},
    )

    assert is_strict_egress_run(strict) is True
    assert has_reserved_egress_provenance(strict) is True
    assert is_strict_egress_run(generic) is False
    assert has_reserved_egress_provenance(generic) is True
    assert is_strict_egress_run(lookalike) is False
    assert has_reserved_egress_provenance(lookalike) is True
    assert is_strict_egress_run(ordinary) is False
    assert has_reserved_egress_provenance(ordinary) is False


def test_create_arming_same_key_and_fingerprint_is_idempotent(tmp_path) -> None:
    db = _session()
    grant = _grant(tmp_path)
    first, created = create_connector_egress_arming(
        db,
        payload=_arming_payload(),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )

    replay, replay_created = create_connector_egress_arming(
        db,
        payload=_arming_payload(),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )

    assert created is True
    assert replay_created is False
    assert replay.connector_run_id == first.connector_run_id
    assert db.query(ConnectorRun).count() == 1


def test_consumed_grant_rejects_different_creation_key(tmp_path) -> None:
    db = _session()
    grant = _grant(tmp_path)
    create_connector_egress_arming(
        db,
        payload=_arming_payload(),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        create_connector_egress_arming(
            db,
            payload=_arming_payload(client_request_id="arm-002"),
            verified_grant=grant,
            operator_receipt=_operator_receipt(grant),
            code_revision=CODE_REVISION,
        )

    assert exc.value.code == "connector_grant_already_consumed"
    assert db.query(ConnectorRun).count() == 1


def test_marker_without_db_arming_fails_closed(tmp_path) -> None:
    db = _session()
    grant = _grant(tmp_path, marker_exists=True)

    with pytest.raises(ConnectorEgressArmingError) as exc:
        create_connector_egress_arming(
            db,
            payload=_arming_payload(),
            verified_grant=grant,
            operator_receipt=_operator_receipt(grant),
            code_revision=CODE_REVISION,
        )

    assert exc.value.code == "connector_grant_consumed_without_arming"
    assert db.query(ConnectorRun).count() == 0


def test_sciencebase_arming_accepts_matching_nrc_clause_5(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    sciencebase_root = tmp_path / "sciencebase"
    sciencebase_root.mkdir()
    grant = _grant(sciencebase_root, connector_key="sciencebase_mcs")
    grant.verified_campaign = state.grant.verified_campaign
    run, created = create_connector_egress_arming(
        db,
        payload=_arming_payload(connector_key="sciencebase_mcs"),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )

    assert created is True
    assert run.connector_key == "sciencebase_mcs"
    assert grant.consumption_marker_path.is_file()
    assert db.query(ConnectorRun).count() == 2


def _created_arming(db: Session, tmp_path):
    grant = _grant(tmp_path)
    run, _ = create_connector_egress_arming(
        db,
        payload=_arming_payload(),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )
    grant.consumption_marker_present = True
    return run, grant


def _nrc_evaluation_fixture(db, tmp_path, monkeypatch):
    run, grant = _created_arming(db, tmp_path)
    completed_at = datetime.now(UTC)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = completed_at + timedelta(minutes=5)
    db.commit()
    finalize_strict_run(
        db,
        run=run,
        lease_token="lease-token",
        terminal_status="completed",
        outcome_class="nrc_raw_admission_completed",
        now=completed_at,
    )
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    artifact_body = b"%PDF-1.7\nclause-5-proof\n"
    artifact_hash = hashlib.sha256(artifact_body).hexdigest()
    stored = artifact_module.write_blob_content_addressed(
        raw_root=settings.connector_raw_dir,
        content=artifact_body,
    )
    target = ConnectorRunTarget(
        connector_run_target_id="nrc-canonical-target",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        status="downloaded",
        downloaded_sha256=artifact_hash,
        raw_storage_ref=str(stored["blob_ref"]),
        sciencebase_download_uri=None,
        source_reference_json={
            "connector_origin_receipt_v1": {
                "schema_id": "must-not-be-read",
                "receipt_hash": "not-a-sha256",
            }
        },
    )
    db.add(target)
    db.commit()
    db.refresh(run)
    envelope = run.request_config_json["connector_egress_arming"]
    timestamp = completed_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    entries = (
        {
            "ordinal": 1,
            "stage": "exact_accession_api",
            "reservation_event_id": "reservation-1",
            "completion_event_id": "completion-1",
            "reserved_at": timestamp,
            "send_started_at": timestamp,
            "completed_at": timestamp,
            "request_fingerprint": "4" * 64,
            "method": "GET",
            "host": "adams-api.nrc.gov",
            "path_class": "nrc_accession_exact",
            "query_class": "none",
            "credential_audience": "nrc_aps_api_key",
            "outcome_class": "completed",
            "response_status": 200,
            "byte_count": 8,
            "body_sha256": "1" * 64,
        },
        {
            "ordinal": 2,
            "stage": "artifact",
            "reservation_event_id": "reservation-2",
            "completion_event_id": "completion-2",
            "reserved_at": timestamp,
            "send_started_at": timestamp,
            "completed_at": timestamp,
            "request_fingerprint": "5" * 64,
            "method": "GET",
            "host": "www.nrc.gov",
            "path_class": "nrc_public_pdf_exact",
            "query_class": "none",
            "credential_audience": "none",
            "outcome_class": "completed",
            "response_status": 200,
            "byte_count": len(artifact_body),
            "body_sha256": artifact_hash,
        },
    )
    projection = {
        "schema_id": "project6.connector_egress_terminal_ledger.v1",
        "connector_run_id": run.connector_run_id,
        "connector_key": "nrc_adams_aps",
        "campaign_fingerprint": envelope["campaign_fingerprint"],
        "arming_fingerprint": envelope["arming_fingerprint"],
        "grant_sha256": grant.raw_sha256,
        "campaign_introduction_index_revision": envelope[
            "campaign_introduction_index_revision"
        ],
        "campaign_introduction_index_sha256": envelope[
            "campaign_introduction_index_sha256"
        ],
        "frozen_max_physical_requests": 2,
        "entries": list(entries),
    }
    ledger = SimpleNamespace(
        connector_run_id=run.connector_run_id,
        entries=entries,
        ledger_terminal_hash=hashlib.sha256(
            canonical_json_bytes(projection)
        ).hexdigest(),
        eligible=True,
        validation_errors=(),
        canonical_projection=projection,
    )
    records = tuple(
        {
            "schema_id": "project6.connector_http_counter.v2",
            "ordinal": entry["ordinal"],
            "stage": entry["stage"],
            "request_fingerprint": entry["request_fingerprint"],
            "canonical_status_header_bytes": 1,
            "delivered_body_bytes": entry["byte_count"],
            "decoded_body_bytes": entry["byte_count"],
            "decoded_body_sha256": entry["body_sha256"],
            "response_status": entry["response_status"],
            "error_class": None,
            "monotonic_started_at": entry["ordinal"],
            "monotonic_stopped_at": entry["ordinal"],
            "evidence_started_at": timestamp,
            "evidence_stopped_at": timestamp,
            "runtime_instance_id": COUNTER_RUNTIME_INSTANCE_ID,
            "process_boot_id": COUNTER_PROCESS_BOOT_ID,
        }
        for entry in entries
    )
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    counter_path = log_dir / "http.jsonl"
    counter_path.write_bytes(
        b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    )
    capture = SimpleNamespace(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=CAMPAIGN_RAW_SHA256,
        code_revision=CODE_REVISION,
        expected_stream_files=(
            "app.jsonl",
            "http.jsonl",
            "stdout.log",
            "stderr.log",
        ),
        log_dir_relative_path="logs",
    )
    grant.verified_campaign.index_chain = SimpleNamespace(
        head=SimpleNamespace(log_captures=(capture,))
    )
    monkeypatch.setattr(
        settings,
        "connector_nrc_aps_grant_sha256",
        grant.raw_sha256,
    )
    monkeypatch.setattr(
        arming_module,
        "resolve_current_connector_egress_grant",
        lambda **_: grant,
    )
    monkeypatch.setattr(
        arming_module,
        "resolve_current_egress_authority",
        lambda *_args, **_kwargs: grant,
    )
    monkeypatch.setattr(
        transport_module,
        "derive_terminal_request_ledger",
        lambda *_args, **_kwargs: ledger,
    )
    monkeypatch.setattr(
        origin_module,
        "derive_connector_origin_receipt",
        lambda *_args, **_kwargs: pytest.fail(
            "derive_connector_origin_receipt must not be called"
        ),
    )
    monkeypatch.setattr(
        origin_module,
        "assert_connector_origin_continuity",
        lambda *_args, **_kwargs: pytest.fail(
            "assert_connector_origin_continuity must not be called"
        ),
    )
    return SimpleNamespace(
        run=run,
        grant=grant,
        ledger=ledger,
        records=records,
        counter_path=counter_path,
        target=target,
        artifact_body=artifact_body,
        artifact_hash=artifact_hash,
        blob_path=Path(str(stored["blob_ref"])),
    )


def _sciencebase_suffix_fixture(db, state, tmp_path):
    sciencebase_root = tmp_path / "sciencebase"
    sciencebase_root.mkdir()
    grant = _grant(sciencebase_root, connector_key="sciencebase_mcs")
    grant.verified_campaign = state.grant.verified_campaign
    run, _ = create_connector_egress_arming(
        db,
        payload=_arming_payload(connector_key="sciencebase_mcs"),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )
    run.status = "running"
    run.execution_lease_owner = "sciencebase-worker"
    run.execution_lease_token = "sciencebase-lease"
    run.execution_lease_expires_at = datetime.now(UTC) + timedelta(minutes=5)
    db.commit()
    record = _counter_record(
        schema_id="project6.connector_http_counter.v2",
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="6" * 64,
    )
    timestamp = "2026-01-01T00:00:00.000000Z"
    entry = {
        "ordinal": 1,
        "stage": "item_hydration",
        "reservation_event_id": "sciencebase-reservation-1",
        "completion_event_id": "sciencebase-completion-1",
        "reserved_at": timestamp,
        "send_started_at": timestamp,
        "completed_at": timestamp,
        "request_fingerprint": record["request_fingerprint"],
        "method": "GET",
        "host": "www.sciencebase.gov",
        "path_class": "sciencebase_item_exact",
        "query_class": "none",
        "credential_audience": "none",
        "outcome_class": "completed",
        "response_status": record["response_status"],
        "byte_count": record["decoded_body_bytes"],
        "body_sha256": record["decoded_body_sha256"],
    }
    envelope = run.request_config_json["connector_egress_arming"]
    projection = {
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
        "frozen_max_physical_requests": envelope["max_physical_requests"],
        "entries": [entry],
    }
    ledger = SimpleNamespace(
        connector_run_id=run.connector_run_id,
        entries=(entry,),
        ledger_terminal_hash=hashlib.sha256(
            canonical_json_bytes(projection)
        ).hexdigest(),
        eligible=True,
        validation_errors=(),
        canonical_projection=projection,
    )
    return SimpleNamespace(run=run, grant=grant, ledger=ledger, record=record)


def _bind_nrc_and_sciencebase_ledgers(monkeypatch, state, sciencebase):
    calls: list[str] = []

    def derive_ledger(_db, *, connector_run_id, **_kwargs):
        calls.append(connector_run_id)
        if connector_run_id == state.run.connector_run_id:
            return state.ledger
        if connector_run_id == sciencebase.run.connector_run_id:
            return sciencebase.ledger
        pytest.fail(f"unexpected ledger run: {connector_run_id}")

    monkeypatch.setattr(
        transport_module,
        "derive_terminal_request_ledger",
        derive_ledger,
    )
    return calls


@pytest.mark.parametrize(
    "schema_id",
    [
        "project6.connector_http_counter.v1",
        "project6.connector_http_counter.v2",
    ],
)
def test_nrc_counter_loader_accepts_exact_historical_v1_and_v2(
    tmp_path,
    schema_id: str,
) -> None:
    record = _counter_record(
        schema_id=schema_id,
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="4" * 64,
    )
    counter_path = tmp_path / "http.jsonl"
    counter_path.write_bytes(canonical_json_bytes(record) + b"\n")

    assert arming_module._load_nrc_counter_records(counter_path) == (record,)


@pytest.mark.parametrize("case", ["mixed_schema", "mixed_runtime", "mixed_boot"])
def test_nrc_counter_loader_rejects_mixed_schema_runtime_or_boot(
    tmp_path,
    case: str,
) -> None:
    first = _counter_record(
        schema_id="project6.connector_http_counter.v2",
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="4" * 64,
    )
    second = _counter_record(
        schema_id="project6.connector_http_counter.v2",
        ordinal=2,
        stage="artifact",
        request_fingerprint="5" * 64,
    )
    if case == "mixed_schema":
        second = _counter_record(
            schema_id="project6.connector_http_counter.v1",
            ordinal=2,
            stage="artifact",
            request_fingerprint="5" * 64,
        )
    elif case == "mixed_runtime":
        second["runtime_instance_id"] = "323e4567-e89b-42d3-a456-426614174000"
    else:
        second["process_boot_id"] = "8" * 64
    counter_path = tmp_path / "http.jsonl"
    counter_path.write_bytes(
        canonical_json_bytes(first) + b"\n" + canonical_json_bytes(second) + b"\n"
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        arming_module._load_nrc_counter_records(counter_path)
    assert exc.value.code == "nrc_acquisition_success_counter_invalid"


def test_nrc_dual_live_success_refuses_historical_v1_pass(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    historical = []
    for value in state.records:
        record = dict(value)
        record["schema_id"] = "project6.connector_http_counter.v1"
        record.pop("runtime_instance_id")
        record.pop("process_boot_id")
        historical.append(record)
    state.counter_path.write_bytes(
        b"".join(canonical_json_bytes(record) + b"\n" for record in historical)
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )
    assert exc.value.code == "nrc_acquisition_success_counter_v2_required"


def test_initial_sciencebase_arming_rejects_unledgered_foreign_suffix(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    sciencebase = _counter_record(
        schema_id="project6.connector_http_counter.v2",
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="6" * 64,
    )
    shared_records = (*state.records, sciencebase)
    state.counter_path.write_bytes(
        b"".join(
            canonical_json_bytes(record) + b"\n" for record in shared_records
        )
    )
    ledger_inputs: list[tuple[dict[str, object], ...]] = []

    def derive_ledger(_db, **kwargs):
        ledger_inputs.append(tuple(kwargs["counter_records"]))
        return state.ledger

    monkeypatch.setattr(
        transport_module,
        "derive_terminal_request_ledger",
        derive_ledger,
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )

    assert ledger_inputs == [shared_records]
    assert exc.value.code == "nrc_acquisition_success_counter_invalid"


def test_post_sciencebase_ordinal_one_revalidates_exact_ledger_suffix(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    sciencebase = _sciencebase_suffix_fixture(db, state, tmp_path)
    shared_records = (*state.records, sciencebase.record)
    state.counter_path.write_bytes(
        b"".join(
            canonical_json_bytes(record) + b"\n" for record in shared_records
        )
    )
    ledger_calls = _bind_nrc_and_sciencebase_ledgers(
        monkeypatch,
        state,
        sciencebase,
    )

    evidence = evaluate_nrc_acquisition_success(
        db,
        verified_definition=state.grant.verified_campaign,
    )

    assert ledger_calls == [
        state.run.connector_run_id,
        sciencebase.run.connector_run_id,
    ]
    assert evidence.counter_reconciliation == {
        "record_count": 2,
        "artifact_ordinal": 2,
        "artifact_stage": "artifact",
        "artifact_decoded_body_sha256": state.artifact_hash,
    }


@pytest.mark.parametrize("case", ["forged", "cross_campaign", "interleaved"])
def test_sciencebase_counter_suffix_rejects_non_authoritative_composition(
    tmp_path,
    monkeypatch,
    case: str,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    sciencebase = _sciencebase_suffix_fixture(db, state, tmp_path)
    _bind_nrc_and_sciencebase_ledgers(monkeypatch, state, sciencebase)
    if case == "cross_campaign":
        config = dict(sciencebase.run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["campaign_id"] = "37693345-6a47-45bb-97a7-44c2932ef76b"
        envelope["arming_fingerprint"] = compute_arming_fingerprint(envelope)
        config["connector_egress_arming"] = envelope
        sciencebase.run.request_config_json = config
        sciencebase.run.request_fingerprint = envelope["arming_fingerprint"]
        db.commit()
        records = [*state.records, sciencebase.record]
    elif case == "interleaved":
        records = [
            state.records[0],
            sciencebase.record,
            state.records[1],
        ]
    else:
        forged = _counter_record(
            schema_id="project6.connector_http_counter.v2",
            ordinal=2,
            stage="download",
            request_fingerprint="7" * 64,
        )
        records = [*state.records, sciencebase.record, forged]
    state.counter_path.write_bytes(
        b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )

    assert exc.value.code == "nrc_acquisition_success_counter_invalid"


@pytest.mark.parametrize(
    "case",
    ["missing", "duplicate", "reordered", "disagreeing"],
)
def test_nrc_substream_selection_rejects_invalid_ledger_bound_records(
    tmp_path,
    monkeypatch,
    case: str,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    first, second = (dict(record) for record in state.records)
    sciencebase = _counter_record(
        schema_id="project6.connector_http_counter.v2",
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="6" * 64,
    )
    if case == "missing":
        records = [first, sciencebase]
    elif case == "duplicate":
        records = [first, dict(first), second, sciencebase]
    elif case == "reordered":
        records = [second, first, sciencebase]
    else:
        second["response_status"] = 206
        records = [first, second, sciencebase]
    state.counter_path.write_bytes(
        b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )

    assert exc.value.code == "nrc_acquisition_success_counter_invalid"


def _db_state_snapshot(db: Session) -> dict[str, tuple[tuple[object, ...], ...]]:
    snapshot: dict[str, tuple[tuple[object, ...], ...]] = {}
    for model in (
        ConnectorRun,
        ConnectorRunSubmission,
        ConnectorPolicySnapshot,
        ConnectorRunEvent,
        ConnectorRunTarget,
    ):
        mapper = cast(Mapper[Any], inspect(model))
        column_keys = tuple(attribute.key for attribute in mapper.column_attrs)
        primary_keys = tuple(str(column.key) for column in mapper.primary_key)
        rows = sorted(
            db.scalars(select(model)).all(),
            key=lambda row: tuple(str(getattr(row, key)) for key in primary_keys),
        )
        snapshot[model.__name__] = tuple(
            tuple(deepcopy(getattr(row, key)) for key in column_keys)
            for row in rows
        )
    return snapshot


def _replace_ledger_artifact_hash(state, digest: str) -> None:
    entries = tuple(
        {**entry, "body_sha256": digest}
        if entry["stage"] == "artifact"
        else dict(entry)
        for entry in state.ledger.entries
    )
    projection = {
        **dict(state.ledger.canonical_projection),
        "entries": list(entries),
    }
    state.ledger.entries = entries
    state.ledger.canonical_projection = projection
    state.ledger.ledger_terminal_hash = hashlib.sha256(
        canonical_json_bytes(projection)
    ).hexdigest()


def _replace_counter_artifact_hash(state, digest: str) -> None:
    records = [dict(record) for record in state.records]
    records[-1]["decoded_body_sha256"] = digest
    state.counter_path.write_bytes(
        b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    )


def test_evaluate_nrc_acquisition_success_accepts_matching_blob_ledger_counter(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    target_selects: list[str] = []

    def capture_target_selects(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if "from connector_run_target" in statement.lower():
            target_selects.append(statement.lower())

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", capture_target_selects)
    try:
        evidence = evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )
    finally:
        event.remove(bind, "before_cursor_execute", capture_target_selects)

    assert evidence.connector_run_id == state.run.connector_run_id
    assert evidence.ledger_terminal_hash == state.ledger.ledger_terminal_hash
    assert evidence.blob_rehash_raw_sha256 == state.artifact_hash
    assert evidence.counter_reconciliation == {
        "record_count": 2,
        "artifact_ordinal": 2,
        "artifact_stage": "artifact",
        "artifact_decoded_body_sha256": state.artifact_hash,
    }
    assert len(target_selects) == 1
    assert "source_reference_json" not in target_selects[0]


@pytest.mark.parametrize(
    "tamper_blob",
    [False, True],
    ids=["agreement", "blob-ledger-mismatch"],
)
def test_evaluate_nrc_acquisition_success_uses_real_terminal_ledger(
    tmp_path,
    monkeypatch,
    tamper_blob: bool,
) -> None:
    db = _session()
    factory = sessionmaker(
        bind=db.get_bind(),
        autocommit=False,
        autoflush=False,
        future=True,
    )
    monkeypatch.setattr(transport_module, "SESSION_FACTORY", factory)
    monkeypatch.setattr(settings, "connector_live_egress_enabled", True)
    monkeypatch.setattr(
        settings,
        "connector_live_egress_exclusive_proof_mode",
        True,
    )
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))

    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        settings,
        "connector_nrc_aps_grant_sha256",
        grant.raw_sha256,
    )
    monkeypatch.setattr(
        arming_module,
        "resolve_current_connector_egress_grant",
        lambda **_: grant,
    )
    monkeypatch.setattr(
        arming_module,
        "resolve_current_egress_authority",
        lambda *_args, **_kwargs: grant,
    )

    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = datetime.now(UTC) + timedelta(minutes=5)
    db.commit()
    envelope = run.request_config_json["connector_egress_arming"]

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    counter_path = log_dir / "http.jsonl"
    timeline = datetime.now(UTC) - timedelta(seconds=12)

    first_body = b"{}"
    first_hash = hashlib.sha256(first_body).hexdigest()
    first_reserved_at = timeline
    first_send_at = timeline + timedelta(seconds=1)
    first_completed_at = timeline + timedelta(seconds=2)
    first_reservation = transport_module.reserve_physical_request(
        connector_run_id=run.connector_run_id,
        lease_token="lease-token",
        arming_fingerprint=envelope["arming_fingerprint"],
        ordinal=1,
        stage="exact_accession_api",
        request=transport_module.FrozenPhysicalRequest(
            method="GET",
            url=(
                "https://adams-api.nrc.gov/aps/api/search/"
                "ML17123A319"
            ),
            headers={
                "Accept-Encoding": "identity",
                "Ocp-Apim-Subscription-Key": "secret",
            },
            credential_audience="nrc_aps_api_key",
        ),
        expected_derived_arming_hash=None,
        now=first_reserved_at,
    )
    transport_module.complete_physical_request(
        reservation=first_reservation,
        outcome=transport_module.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=len(first_body),
            body_sha256=first_hash,
            counted_status_header_bytes=17,
            delivered_body_bytes=len(first_body),
            decoded_body_bytes=len(first_body),
            decoded_body_sha256=first_hash,
            send_started_at=first_send_at,
            completed_at=first_completed_at,
        ),
    )
    transport_module._append_counter_record(
        counter_path,
        {
            "schema_id": "project6.connector_http_counter.v2",
            "ordinal": 1,
            "stage": "exact_accession_api",
            "request_fingerprint": first_reservation.request_fingerprint,
            "canonical_status_header_bytes": 17,
            "delivered_body_bytes": len(first_body),
            "decoded_body_bytes": len(first_body),
            "decoded_body_sha256": first_hash,
            "response_status": 200,
            "error_class": None,
            "monotonic_started_at": 1.0,
            "monotonic_stopped_at": 1.5,
            "evidence_started_at": transport_module.utc_six_z(first_send_at),
            "evidence_stopped_at": transport_module.utc_six_z(
                first_completed_at
            ),
            "runtime_instance_id": COUNTER_RUNTIME_INSTANCE_ID,
            "process_boot_id": COUNTER_PROCESS_BOOT_ID,
        },
    )

    artifact_url = "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"
    derived = commit_derived_url_arming(
        db,
        run=run,
        lease_token="lease-token",
        ordinal=2,
        stage="artifact",
        normalized_url=artifact_url,
        verified_grant=grant,
    )
    artifact_body = b"%PDF-1.7\nclause-5-real-ledger\n"
    artifact_hash = hashlib.sha256(artifact_body).hexdigest()
    second_reserved_at = timeline + timedelta(seconds=3)
    second_send_at = timeline + timedelta(seconds=4)
    second_completed_at = timeline + timedelta(seconds=5)
    second_reservation = transport_module.reserve_physical_request(
        connector_run_id=run.connector_run_id,
        lease_token="lease-token",
        arming_fingerprint=envelope["arming_fingerprint"],
        ordinal=2,
        stage="artifact",
        request=transport_module.FrozenPhysicalRequest(
            method="GET",
            url=artifact_url,
            headers={"Accept-Encoding": "identity"},
            credential_audience="none",
        ),
        expected_derived_arming_hash=derived.url_sha256,
        now=second_reserved_at,
        counter_path=counter_path,
    )
    transport_module.complete_physical_request(
        reservation=second_reservation,
        outcome=transport_module.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=len(artifact_body),
            body_sha256=artifact_hash,
            counted_status_header_bytes=19,
            delivered_body_bytes=len(artifact_body),
            decoded_body_bytes=len(artifact_body),
            decoded_body_sha256=artifact_hash,
            send_started_at=second_send_at,
            completed_at=second_completed_at,
        ),
    )
    transport_module._append_counter_record(
        counter_path,
        {
            "schema_id": "project6.connector_http_counter.v2",
            "ordinal": 2,
            "stage": "artifact",
            "request_fingerprint": second_reservation.request_fingerprint,
            "canonical_status_header_bytes": 19,
            "delivered_body_bytes": len(artifact_body),
            "decoded_body_bytes": len(artifact_body),
            "decoded_body_sha256": artifact_hash,
            "response_status": 200,
            "error_class": None,
            "monotonic_started_at": 2.0,
            "monotonic_stopped_at": 2.5,
            "evidence_started_at": transport_module.utc_six_z(second_send_at),
            "evidence_stopped_at": transport_module.utc_six_z(
                second_completed_at
            ),
            "runtime_instance_id": COUNTER_RUNTIME_INSTANCE_ID,
            "process_boot_id": COUNTER_PROCESS_BOOT_ID,
        },
    )

    stored = artifact_module.write_blob_content_addressed(
        raw_root=settings.connector_raw_dir,
        content=artifact_body,
    )
    db.add(
        ConnectorRunTarget(
            connector_run_target_id="nrc-real-ledger-target",
            connector_run_id=run.connector_run_id,
            ordinal=1,
            status="downloaded",
            downloaded_sha256=artifact_hash,
            raw_storage_ref=str(stored["blob_ref"]),
            sciencebase_download_uri=None,
            source_reference_json={},
        )
    )
    db.commit()
    finalize_strict_run(
        db,
        run=run,
        lease_token="lease-token",
        terminal_status="completed",
        outcome_class="nrc_raw_admission_completed",
        now=timeline + timedelta(seconds=6),
    )
    capture = SimpleNamespace(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=CAMPAIGN_RAW_SHA256,
        code_revision=CODE_REVISION,
        expected_stream_files=(
            "app.jsonl",
            "http.jsonl",
            "stdout.log",
            "stderr.log",
        ),
        log_dir_relative_path="logs",
    )
    grant.verified_campaign.index_chain = SimpleNamespace(
        head=SimpleNamespace(log_captures=(capture,))
    )

    real_ledger = transport_module.derive_terminal_request_ledger(
        db,
        connector_run_id=run.connector_run_id,
        counter_path=counter_path,
    )
    assert real_ledger.eligible is True
    assert real_ledger.validation_errors == ()
    assert [(entry["ordinal"], entry["stage"]) for entry in real_ledger.entries] == [
        (1, "exact_accession_api"),
        (2, "artifact"),
    ]
    assert real_ledger.entries[-1]["body_sha256"] == artifact_hash
    assert (
        db.query(ConnectorRunEvent)
        .filter(
            ConnectorRunEvent.event_type.in_(
                [
                    transport_module.RESERVATION_EVENT_TYPE,
                    transport_module.COMPLETION_EVENT_TYPE,
                ]
            )
        )
        .count()
        == 4
    )

    blob_path = Path(str(stored["blob_ref"]))
    if tamper_blob:
        tampered_body = b"X" + artifact_body[1:]
        assert len(tampered_body) == len(artifact_body)
        blob_path.write_bytes(tampered_body)
    baseline = _db_state_snapshot(db)

    if tamper_blob:
        with pytest.raises(ConnectorEgressArmingError) as exc:
            evaluate_nrc_acquisition_success(
                db,
                verified_definition=grant.verified_campaign,
            )
        assert exc.value.code == "nrc_acquisition_success_blob_mismatch"
        assert exc.value.status_code == 409
    else:
        evidence = evaluate_nrc_acquisition_success(
            db,
            verified_definition=grant.verified_campaign,
        )
        assert evidence.connector_run_id == run.connector_run_id
        assert evidence.ledger_terminal_hash == real_ledger.ledger_terminal_hash
        assert evidence.blob_rehash_raw_sha256 == artifact_hash
        assert evidence.counter_reconciliation == {
            "record_count": 2,
            "artifact_ordinal": 2,
            "artifact_stage": "artifact",
            "artifact_decoded_body_sha256": artifact_hash,
        }
    assert _db_state_snapshot(db) == baseline


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("blob_vs_ledger", "nrc_acquisition_success_blob_mismatch"),
        ("blob_vs_counter", "nrc_acquisition_success_blob_mismatch"),
        ("changed_blob", "nrc_acquisition_success_blob_mismatch"),
        ("missing_blob", "nrc_acquisition_success_blob_unavailable"),
    ],
)
def test_sciencebase_clause_5_failures_leave_marker_db_and_events_untouched(
    tmp_path,
    monkeypatch,
    failure: str,
    expected_code: str,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    # Clause 4 normally rejects ledger/counter disagreement first. Bypass only
    # that redundant guard here to prove clause 5 independently compares both.
    if failure == "blob_vs_ledger":
        _replace_ledger_artifact_hash(state, "0" * 64)
        monkeypatch.setattr(
            arming_module,
            "_reconcile_nrc_counter_records",
            lambda *_args, **_kwargs: None,
        )
    elif failure == "blob_vs_counter":
        _replace_counter_artifact_hash(state, "0" * 64)
        monkeypatch.setattr(
            arming_module,
            "_reconcile_nrc_counter_records",
            lambda *_args, **_kwargs: None,
        )
    elif failure == "changed_blob":
        state.blob_path.write_bytes(b"X" + state.artifact_body[1:])
    else:
        state.blob_path.rename(state.blob_path.with_suffix(".missing"))

    sciencebase_root = tmp_path / "sciencebase"
    sciencebase_root.mkdir()
    grant = _grant(sciencebase_root, connector_key="sciencebase_mcs")
    grant.verified_campaign = state.grant.verified_campaign
    baseline = _db_state_snapshot(db)

    with pytest.raises(ConnectorEgressArmingError) as exc:
        create_connector_egress_arming(
            db,
            payload=_arming_payload(connector_key="sciencebase_mcs"),
            verified_grant=grant,
            operator_receipt=_operator_receipt(grant),
            code_revision=CODE_REVISION,
        )

    assert exc.value.code == expected_code
    assert exc.value.status_code == 409
    assert not grant.consumption_marker_path.exists()
    assert _db_state_snapshot(db) == baseline


def test_evaluate_nrc_acquisition_success_rejects_failure_like_terminal_outcome(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    terminal = db.scalar(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.connector_run_id == state.run.connector_run_id,
            ConnectorRunEvent.event_type == "egress_run_terminal",
        )
    )
    assert terminal is not None
    terminal.reason_code = "transport_failure"
    metrics = dict(terminal.metrics_json)
    metrics["outcome_class"] = "transport_failure"
    terminal.metrics_json = metrics
    db.commit()

    with pytest.raises(ConnectorEgressArmingError) as exc:
        evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )

    assert exc.value.code == "nrc_acquisition_success_terminal_invalid"


def _nrc_seal_event(run: ConnectorRun) -> ConnectorRunEvent:
    envelope = run.request_config_json["connector_egress_arming"]
    created_at = datetime.now(UTC)
    return ConnectorRunEvent(
        connector_run_event_id=arming_module._deterministic_id(
            run.connector_run_id,
            "campaign_log_capture_sealed",
        ),
        connector_run_id=run.connector_run_id,
        connector_run_target_id=None,
        phase="evidence",
        stage="campaign_log_capture",
        event_type="campaign_log_capture_sealed",
        status_before="completed",
        status_after="completed",
        reason_code="protected_log_capture_sealed",
        error_class=None,
        message=None,
        metrics_json={
            "schema_id": "project6.connector_campaign_log_seal_event_metrics.v1",
            "campaign_id": envelope["campaign_id"],
            "campaign_fingerprint": envelope["campaign_fingerprint"],
            "campaign_definition_sha256": envelope[
                "campaign_definition_sha256"
            ],
            "code_revision": envelope["code_revision"],
            "campaign_introduction_index_revision": envelope[
                "campaign_introduction_index_revision"
            ],
            "campaign_introduction_index_sha256": envelope[
                "campaign_introduction_index_sha256"
            ],
            "manifest_relative_path": "logs/manifest.json",
            "manifest_sha256": "1" * 64,
            "file_set_hash": "2" * 64,
            "seal_relative_path": "logs/seal.json",
            "seal_sha256": "3" * 64,
            "connector_run_ids": [run.connector_run_id, "sciencebase-run"],
            "sealed_at": created_at.isoformat().replace("+00:00", "Z"),
        },
        created_at=created_at,
    )


def test_nrc_terminal_transition_admits_one_exact_post_seal_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id
                == state.run.connector_run_id
            )
        )
    )

    arming_module._assert_nrc_terminal_transition(
        state.run,
        events=(*events, _nrc_seal_event(state.run)),
        now=datetime.now(UTC),
    )


@pytest.mark.parametrize("mutation", ["forged", "duplicate"])
def test_nrc_terminal_transition_rejects_invalid_post_seal_competitor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id
                == state.run.connector_run_id
            )
        )
    )
    seal = _nrc_seal_event(state.run)
    seals = [seal, deepcopy(seal)] if mutation == "duplicate" else [seal]
    if mutation == "forged":
        seals[0].reason_code = "forged_seal"

    with pytest.raises(ConnectorEgressArmingError) as exc:
        arming_module._assert_nrc_terminal_transition(
            state.run,
            events=(*events, *seals),
            now=datetime.now(UTC),
        )

    assert exc.value.code == "nrc_acquisition_success_terminal_invalid"


@pytest.mark.parametrize(
    ("clause", "expected_code"),
    [
        ("terminal", "nrc_acquisition_success_terminal_invalid"),
        ("lease", "nrc_acquisition_success_lease_active"),
        ("ledger", "nrc_acquisition_success_ledger_invalid"),
        ("counter", "nrc_acquisition_success_counter_invalid"),
    ],
)
def test_evaluate_nrc_acquisition_success_fails_each_clause_closed(
    tmp_path,
    monkeypatch,
    clause: str,
    expected_code: str,
) -> None:
    db = _session()
    state = _nrc_evaluation_fixture(db, tmp_path, monkeypatch)
    if clause == "terminal":
        db.add(
            ConnectorRunEvent(
                connector_run_event_id="competing-terminal",
                connector_run_id=state.run.connector_run_id,
                phase="execution",
                stage="terminal",
                event_type="egress_run_terminal",
                status_before="completed",
                status_after="failed",
                reason_code="later_failure",
                error_class="later_failure",
            )
        )
        db.commit()
    elif clause == "lease":
        state.run.execution_lease_expires_at = datetime.now(UTC) + timedelta(
            minutes=5
        )
        db.commit()
    elif clause == "ledger":
        state.ledger.eligible = False
        state.ledger.validation_errors = ("spent_unknown",)
    elif clause == "counter":
        state.counter_path.write_bytes(
            b"".join(
                canonical_json_bytes(record) + b"\n"
                for record in reversed(state.records)
            )
        )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        evaluate_nrc_acquisition_success(
            db,
            verified_definition=state.grant.verified_campaign,
        )

    assert exc.value.code == expected_code


def test_claim_uses_fingerprint_bound_sql_cas_and_replay_is_not_reclaimed(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        "app.services.connector_egress_arming._resolve_current_authority",
        lambda **_: grant,
    )

    claimed, claimed_now = claim_connector_egress_arming(
        db,
        connector_run_id=run.connector_run_id,
        execution_idempotency_key="execute-001",
        expected_arming_fingerprint=run.request_fingerprint,
        now=NOW,
    )
    replay, replay_claimed_now = claim_connector_egress_arming(
        db,
        connector_run_id=run.connector_run_id,
        execution_idempotency_key="execute-001",
        expected_arming_fingerprint=run.request_fingerprint,
        now=NOW,
    )

    assert claimed_now is True
    assert replay_claimed_now is False
    assert claimed.status == "pending"
    assert replay.connector_run_id == claimed.connector_run_id
    execute_submissions = db.scalars(
        select(ConnectorRunSubmission).where(
            ConnectorRunSubmission.submission_idempotency_key
            == "egress-execute:execute-001"
        )
    ).all()
    assert len(execute_submissions) == 1
    assert execute_submissions[0].connector_run_submission_id == str(
        uuid5(
            NAMESPACE_URL,
            "project6:connector-egress:execute-idempotency:execute-001",
        )
    )


def test_claim_cas_loser_returns_committed_same_key_replay(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        "app.services.connector_egress_arming._resolve_current_authority",
        lambda **_: grant,
    )
    original_execute = db.execute
    winner_committed = False

    def execute_with_concurrent_winner(statement, *args, **kwargs):
        nonlocal winner_committed
        if statement.__class__.__name__ == "Update" and not winner_committed:
            winner_committed = True
            winner_result = original_execute(statement, *args, **kwargs)
            assert winner_result.rowcount == 1
            db.add(
                ConnectorRunSubmission(
                    connector_run_submission_id="winner-execute-submission",
                    connector_key=run.connector_key,
                    submission_idempotency_key="egress-execute:execute-001",
                    request_fingerprint=run.request_fingerprint,
                    connector_run_id=run.connector_run_id,
                    expires_at=grant.model.expires_at,
                )
            )
            db.commit()
            return SimpleNamespace(rowcount=0)
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", execute_with_concurrent_winner)

    replay, claimed_now = claim_connector_egress_arming(
        db,
        connector_run_id=run.connector_run_id,
        execution_idempotency_key="execute-001",
        expected_arming_fingerprint=run.request_fingerprint,
        now=NOW,
    )

    assert winner_committed is True
    assert claimed_now is False
    assert replay.status == "pending"


def test_execute_idempotency_key_is_global_across_connectors(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        arming_module,
        "_resolve_current_authority",
        lambda **_: grant,
    )
    db.add(
        ConnectorRunSubmission(
            connector_run_submission_id="cross-connector-execute-submission",
            connector_key="sciencebase_mcs",
            submission_idempotency_key="egress-execute:cross-connector-key",
            request_fingerprint=run.request_fingerprint,
            connector_run_id=run.connector_run_id,
            expires_at=grant.model.expires_at,
        )
    )
    db.commit()

    with pytest.raises(ConnectorEgressArmingError) as exc:
        claim_connector_egress_arming(
            db,
            connector_run_id=run.connector_run_id,
            execution_idempotency_key="cross-connector-key",
            expected_arming_fingerprint=run.request_fingerprint,
            now=NOW,
        )

    db.refresh(run)
    assert exc.value.code == "connector_execution_idempotency_conflict"
    assert run.status == "armed"


def test_claim_rejects_stale_expected_fingerprint_without_mutation(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        "app.services.connector_egress_arming._resolve_current_authority",
        lambda **_: grant,
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        claim_connector_egress_arming(
            db,
            connector_run_id=run.connector_run_id,
            execution_idempotency_key="execute-001",
            expected_arming_fingerprint="0" * 64,
            now=NOW,
        )

    db.refresh(run)
    assert exc.value.code == "connector_arming_fingerprint_mismatch"
    assert run.status == "armed"
    assert (
        db.scalar(
            select(ConnectorRunSubmission).where(
                ConnectorRunSubmission.submission_idempotency_key
                == "egress-execute:execute-001"
            )
        )
        is None
    )


def test_claim_rejects_authority_drift_before_state_change(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    drifted = SimpleNamespace(**vars(grant))
    drifted.canonical_fingerprint = "9" * 64
    monkeypatch.setattr(
        "app.services.connector_egress_arming._resolve_current_authority",
        lambda **_: drifted,
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        claim_connector_egress_arming(
            db,
            connector_run_id=run.connector_run_id,
            execution_idempotency_key="execute-001",
            expected_arming_fingerprint=run.request_fingerprint,
            now=NOW,
        )

    db.refresh(run)
    assert exc.value.code == "connector_arming_authority_drift"
    assert run.status == "armed"


def test_claim_rejects_operator_mode_drift_before_state_change(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    drifted = SimpleNamespace(**vars(grant))
    drifted.model = grant.model.model_copy(
        update={"operator_mode": "proxy_owner"}
    )
    monkeypatch.setattr(
        "app.services.connector_egress_arming._resolve_current_authority",
        lambda **_: drifted,
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        claim_connector_egress_arming(
            db,
            connector_run_id=run.connector_run_id,
            execution_idempotency_key="execute-001",
            expected_arming_fingerprint=run.request_fingerprint,
            now=NOW,
        )

    db.refresh(run)
    assert exc.value.code == "connector_arming_authority_drift"
    assert run.status == "armed"


def test_public_authority_rejects_coordinated_envelope_rehash(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        arming_module,
        "_resolve_current_authority",
        lambda **_: grant,
    )
    envelope = dict(run.request_config_json["connector_egress_arming"])
    envelope["coordinated_extra"] = "attacker-controlled"
    fingerprint = compute_arming_fingerprint(envelope)
    envelope["arming_fingerprint"] = fingerprint
    run.request_config_json = {"connector_egress_arming": envelope}
    run.request_fingerprint = fingerprint
    creation = db.scalar(
        select(ConnectorRunSubmission).where(
            ConnectorRunSubmission.connector_run_id == run.connector_run_id
        )
    )
    assert creation is not None
    creation.request_fingerprint = fingerprint
    db.commit()

    with pytest.raises(ConnectorEgressArmingError) as exc:
        resolve_current_egress_authority(
            db,
            connector_run_id=run.connector_run_id,
            now=NOW,
        )

    assert exc.value.code == "connector_arming_envelope_drift"


def test_public_authority_rejects_reserved_source_mode_drift(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        arming_module,
        "_resolve_current_authority",
        lambda **_: grant,
    )
    run.source_mode = "public_api"
    db.commit()

    with pytest.raises(ConnectorEgressArmingError) as exc:
        resolve_current_egress_authority(
            db,
            connector_run_id=run.connector_run_id,
            now=NOW,
        )

    assert exc.value.code == "connector_strict_envelope_malformed"


def test_claim_rechecks_expiry_immediately_before_commit(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        arming_module,
        "_resolve_current_authority",
        lambda **_: grant,
    )
    original = arming_module._require_unexpired_creation_binding
    calls = 0

    def expire_on_precommit(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ConnectorEgressArmingError(
                "connector_arming_expired_or_unbound",
                "simulated precommit expiry",
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        arming_module,
        "_require_unexpired_creation_binding",
        expire_on_precommit,
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        claim_connector_egress_arming(
            db,
            connector_run_id=run.connector_run_id,
            execution_idempotency_key="execute-expiry-race",
            expected_arming_fingerprint=run.request_fingerprint,
            now=NOW,
        )

    db.refresh(run)
    assert calls == 2
    assert exc.value.code == "connector_arming_expired_or_unbound"
    assert run.status == "armed"
    assert (
        db.scalar(
            select(ConnectorRunSubmission).where(
                ConnectorRunSubmission.submission_idempotency_key
                == "egress-execute:execute-expiry-race"
            )
        )
        is None
    )


def test_claim_precommit_recheck_advances_injected_time_monotonically(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    monkeypatch.setattr(
        arming_module,
        "_resolve_current_authority",
        lambda **_: grant,
    )
    creation = db.scalar(
        select(ConnectorRunSubmission).where(
            ConnectorRunSubmission.connector_run_id == run.connector_run_id
        )
    )
    assert creation is not None
    creation.expires_at = NOW + timedelta(seconds=1)
    db.commit()
    monotonic_values = iter((100.0, 102.0))
    monkeypatch.setattr(
        arming_module.time,
        "monotonic",
        lambda: next(monotonic_values),
    )

    with pytest.raises(ConnectorEgressArmingError) as exc:
        claim_connector_egress_arming(
            db,
            connector_run_id=run.connector_run_id,
            execution_idempotency_key="execute-real-expiry-race",
            expected_arming_fingerprint=run.request_fingerprint,
            now=NOW,
        )

    db.refresh(run)
    assert exc.value.code == "connector_arming_expired_or_unbound"
    assert run.status == "armed"
    assert (
        db.scalar(
            select(ConnectorRunSubmission).where(
                ConnectorRunSubmission.submission_idempotency_key
                == "egress-execute:execute-real-expiry-race"
            )
        )
        is None
    )


def test_superseding_grant_requires_exact_prior_marker(
    tmp_path,
    monkeypatch,
) -> None:
    grant = _grant(tmp_path)
    prior_digest = "9" * 64
    prior_campaign_id = "e347d828-f475-4d7f-918f-4dc24a69efb7"
    prior_fingerprint = "8" * 64
    prior_definition_sha256 = "7" * 64
    prior_grant_fingerprint = "6" * 64
    prior_nonce = UUID("bf19ce7b-f91a-4607-8aae-e9092fef55da")
    grant.model = grant.model.model_copy(
        update={"supersedes_grant_sha256": prior_digest}
    )
    grant.verified_campaign.index_chain = SimpleNamespace(
        head=SimpleNamespace(
            entries=(
                SimpleNamespace(
                    connector_key="nrc_adams_aps",
                    raw_grant_sha256=prior_digest,
                    campaign_id=prior_campaign_id,
                    campaign_fingerprint=prior_fingerprint,
                ),
            )
        )
    )
    prior_model = grant.model.model_copy(
        update={
            "campaign_id": prior_campaign_id,
            "campaign_fingerprint": prior_fingerprint,
            "campaign_definition_sha256": prior_definition_sha256,
            "arming_nonce": prior_nonce,
            "supersedes_grant_sha256": None,
        }
    )
    prior_run_id = compute_parent_arming_id(
        connector_key="nrc_adams_aps",
        campaign_id=prior_campaign_id,
        grant_sha256=prior_digest,
        arming_nonce=prior_nonce,
    )
    marker = ConnectorGrantConsumptionMarkerV1(
        schema_id="project6.connector_grant_consumption.v1",
        connector_key="nrc_adams_aps",
        campaign_id=prior_campaign_id,
        campaign_fingerprint=prior_fingerprint,
        campaign_definition_sha256=prior_definition_sha256,
        raw_grant_sha256=prior_digest,
        canonical_grant_fingerprint=prior_grant_fingerprint,
        arming_nonce=prior_nonce,
        connector_run_id=prior_run_id,
        max_armings=1,
    )
    historical = SimpleNamespace(
        raw_sha256=prior_digest,
        canonical_fingerprint=prior_grant_fingerprint,
        raw_definition_sha256=prior_definition_sha256,
        canonical_campaign_fingerprint=prior_fingerprint,
        model=prior_model,
        marker_model=marker,
    )
    monkeypatch.setattr(
        arming_module,
        "resolve_historical_connector_grant_evidence",
        lambda **_: historical,
    )

    _assert_supersession_contract(grant)
    historical.marker_model = marker.model_copy(
        update={"connector_run_id": "wrong-prior-run"}
    )
    with pytest.raises(ConnectorEgressArmingError) as exc:
        _assert_supersession_contract(grant)
    assert exc.value.code == "connector_grant_supersession_unverified"


def test_finalize_strict_run_is_lease_gated_and_single_terminal_transition(
    tmp_path,
) -> None:
    db = _session()
    run, _ = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = NOW + timedelta(minutes=5)
    db.commit()

    finalize_strict_run(
        db,
        run=run,
        lease_token="lease-token",
        terminal_status="completed",
        outcome_class="fresh_live",
        now=NOW,
    )

    db.refresh(run)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.execution_lease_owner is None
    assert run.execution_lease_token is None
    terminals = db.scalars(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.event_type == "egress_run_terminal"
        )
    ).all()
    assert len(terminals) == 1
    assert terminals[0].status_after == "completed"

    with pytest.raises(ConnectorEgressArmingError) as exc:
        finalize_strict_run(
            db,
            run=run,
            lease_token="lease-token",
            terminal_status="failed",
            outcome_class="competing",
            now=NOW + timedelta(seconds=1),
        )
    assert exc.value.code == "connector_strict_finalize_conflict"
    assert (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.event_type == "egress_run_terminal")
        .count()
        == 1
    )


def test_finalize_wrong_lease_token_after_expiry_mutates_nothing(tmp_path) -> None:
    db = _session()
    run, _ = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = NOW - timedelta(seconds=1)
    db.commit()
    prior_expiry = run.execution_lease_expires_at

    with pytest.raises(ConnectorEgressArmingError) as exc:
        finalize_strict_run(
            db,
            run=run,
            lease_token="wrong-token",
            terminal_status="failed",
            outcome_class="transport_failure",
            now=NOW,
        )

    db.refresh(run)
    assert exc.value.code == "connector_strict_finalize_conflict"
    assert run.status == "running"
    assert run.execution_lease_owner == "strict-worker"
    assert run.execution_lease_token == "lease-token"
    assert run.execution_lease_expires_at == prior_expiry
    assert (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.event_type == "egress_run_terminal")
        .count()
        == 0
    )


def test_refresh_strict_run_lease_is_active_exact_token_cas(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, _ = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = NOW + timedelta(seconds=10)
    db.commit()
    monkeypatch.setattr(settings, "connector_lease_ttl_seconds", 90)

    refreshed = refresh_strict_run_lease(
        db,
        run=run,
        lease_token="lease-token",
        now=NOW,
    )

    db.refresh(run)
    assert refreshed == NOW + timedelta(seconds=90)
    assert run.execution_lease_expires_at is not None
    assert run.execution_lease_expires_at.replace(tzinfo=UTC) == refreshed
    assert run.heartbeat_at is not None
    assert run.heartbeat_at.replace(tzinfo=UTC) == NOW

    prior_expiry = run.execution_lease_expires_at
    with pytest.raises(ConnectorEgressArmingError) as wrong:
        refresh_strict_run_lease(
            db,
            run=run,
            lease_token="wrong-token",
            now=NOW + timedelta(seconds=1),
        )
    db.refresh(run)
    assert wrong.value.code == "connector_strict_lease_refresh_conflict"
    assert run.execution_lease_expires_at == prior_expiry


@pytest.mark.parametrize(
    "terminal_status",
    ["completed", "failed", "cancelled"],
)
def test_expired_strict_lease_rejects_refresh_but_allows_exact_token_finalization(
    tmp_path,
    terminal_status: str,
) -> None:
    db = _session()
    run, _ = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = NOW - timedelta(seconds=1)
    db.commit()

    with pytest.raises(ConnectorEgressArmingError) as refresh:
        refresh_strict_run_lease(
            db,
            run=run,
            lease_token="lease-token",
            now=NOW,
        )
    assert refresh.value.code == "connector_strict_lease_expired"

    finalize_strict_run(
        db,
        run=run,
        lease_token="lease-token",
        terminal_status=terminal_status,
        outcome_class=f"{terminal_status}_after_expiry",
        now=NOW,
    )

    db.refresh(run)
    assert run.status == terminal_status
    assert run.completed_at is not None
    assert run.execution_lease_owner is None
    assert run.execution_lease_token is None
    assert run.execution_lease_expires_at == run.completed_at
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.event_type == "egress_run_terminal"
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == terminal_status

    with pytest.raises(ConnectorEgressArmingError) as replay:
        finalize_strict_run(
            db,
            run=run,
            lease_token="lease-token",
            terminal_status=terminal_status,
            outcome_class=f"{terminal_status}_after_expiry",
            now=NOW + timedelta(seconds=1),
        )

    assert replay.value.code == "connector_strict_finalize_conflict"
    assert (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.event_type == "egress_run_terminal")
        .count()
        == 1
    )


def test_refresh_strict_run_lease_refuses_caller_pending_state(tmp_path) -> None:
    db = _session()
    run, _ = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = NOW + timedelta(minutes=5)
    db.commit()
    prior_expiry = run.execution_lease_expires_at
    run.error_summary = "must-not-commit"

    with pytest.raises(ConnectorEgressArmingError) as exc:
        refresh_strict_run_lease(
            db,
            run=run,
            lease_token="lease-token",
            now=NOW,
        )

    assert exc.value.code == "connector_strict_lease_refresh_dirty_session"
    assert run in db.dirty
    db.rollback()
    db.refresh(run)
    assert run.error_summary is None
    assert run.execution_lease_expires_at == prior_expiry


def test_commit_derived_url_arming_persists_hash_and_classes_only(tmp_path) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = datetime(2099, 1, 1, tzinfo=UTC)
    db.commit()
    exact_url = "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"

    derived = commit_derived_url_arming(
        db,
        run=run,
        lease_token="lease-token",
        ordinal=2,
        stage="artifact",
        normalized_url=exact_url,
        verified_grant=grant,
    )

    assert derived.normalized_url == exact_url
    snapshots = db.scalars(
        select(ConnectorPolicySnapshot).where(
            ConnectorPolicySnapshot.connector_run_id == run.connector_run_id
        )
    ).all()
    derived_snapshots = [
        item
        for item in snapshots
        if item.policy_json.get("kind") == "derived_egress_arming"
    ]
    assert len(derived_snapshots) == 1
    stored = json.dumps(derived_snapshots[0].policy_json, sort_keys=True)
    assert exact_url not in stored
    assert "/docs/ML1712/ML17123A319.pdf" not in stored
    assert derived.url_sha256 in stored
    event = db.scalar(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.event_type == "derived_egress_arming_created"
        )
    )
    assert event is not None
    assert exact_url not in json.dumps(event.metrics_json, sort_keys=True)


def test_commit_derived_url_arming_requires_active_lease_cas(
    tmp_path,
    monkeypatch,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = datetime(2099, 1, 1, tzinfo=UTC)
    db.commit()
    original_execute = db.execute

    def lose_lease_cas(statement, *args, **kwargs):
        if statement.__class__.__name__ == "Update":
            return SimpleNamespace(rowcount=0)
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", lose_lease_cas)

    with pytest.raises(ConnectorEgressArmingError) as exc:
        commit_derived_url_arming(
            db,
            run=run,
            lease_token="lease-token",
            ordinal=2,
            stage="artifact",
            normalized_url=(
                "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"
            ),
            verified_grant=grant,
        )

    assert exc.value.code == "connector_derived_url_lease_conflict"
    assert (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.event_type == "derived_egress_arming_created")
        .count()
        == 0
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://www.nrc.gov/docs/ML1712/OTHER.pdf",
        "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf?",
        "https://user@www.nrc.gov/docs/ML1712/ML17123A319.pdf",
        "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf#",
    ],
)
def test_commit_derived_url_arming_rejects_non_exact_nrc_url(
    tmp_path,
    url,
) -> None:
    db = _session()
    run, grant = _created_arming(db, tmp_path)
    run.status = "running"
    run.execution_lease_owner = "strict-worker"
    run.execution_lease_token = "lease-token"
    run.execution_lease_expires_at = datetime(2099, 1, 1, tzinfo=UTC)
    db.commit()

    with pytest.raises(ConnectorEgressArmingError) as exc:
        commit_derived_url_arming(
            db,
            run=run,
            lease_token="lease-token",
            ordinal=2,
            stage="artifact",
            normalized_url=url,
            verified_grant=grant,
        )

    assert exc.value.code == "connector_derived_url_not_authorized"
    assert (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.event_type == "derived_egress_arming_created")
        .count()
        == 0
    )
