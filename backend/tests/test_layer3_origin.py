from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base
from app.models.models import (
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
    ConnectorPolicySnapshot,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3ConnectorSourceIntakeRecord,
)
from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    COMMON_GRANT_NON_AUTHORITIES,
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    ConnectorEgressGrantV1,
    DualLiveCampaignDefinitionV1,
    expected_grant_rule_payloads,
)
from app.services import layer3_origin_continuity as origin
from app.services import connector_egress_arming, connector_egress_transport
from app.services.connector_egress_authorization import (
    VerifiedHistoricalGrantEvidence,
)


CAMPAIGN_ID = "7fe33e0a-c0e7-4f8e-9d55-8ba77a01ce23"
CAMPAIGN_FINGERPRINT = "a" * 64
DEFINITION_SHA256 = "b" * 64
INDEX_SHA256 = "c" * 64
ARMING_FINGERPRINT = "d" * 64
GRANT_SHA256 = "e" * 64
GRANT_FINGERPRINT = "f" * 64
MARKER_SHA256 = "9" * 64
GRANT_ID = "grant-origin-test"
ARMING_NONCE = "11111111-1111-4111-8111-111111111111"
PREDECESSOR_RUN_ID = "run-nrc-predecessor"
PREDECESSOR_LEDGER_HASH = "6" * 64
MAX_RUN_BYTES = 524_288
MAX_SINGLE_SEND_ALLOWANCE = 4_096
REQUEST_TIMEOUT_SECONDS = 30
MIN_REQUEST_INTERVAL_MS = 1_000
NON_AUTHORITIES = ["external_delivery", "recurring_operation"]
WINDOW_START = datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage))
    Path(settings.connector_raw_dir).mkdir(parents=True)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _request_rules(connector_key: str) -> list[dict]:
    if connector_key == "sciencebase_mcs":
        return [
            {
                "ordinal": 1,
                "stage": "item_hydration",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ["www.sciencebase.gov"],
                "port": 443,
                "path_rule_id": "sciencebase_item_exact_v1",
                "query_rule_id": "format_json_exact_v1",
                "credential_audience": "none",
                "max_response_bytes": 5 * 1024 * 1024,
            },
            {
                "ordinal": 2,
                "stage": "artifact",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ["sciencebase.gov", "www.sciencebase.gov"],
                "port": 443,
                "path_rule_id": "sciencebase_file_exact_v1",
                "query_rule_id": "sciencebase_exact_file_selector_v1",
                "credential_audience": "none",
                "max_response_bytes": 64 * 1024 * 1024,
            },
            {
                "ordinal": 3,
                "stage": "artifact_redirect",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ["sciencebase.gov", "www.sciencebase.gov"],
                "port": 443,
                "path_rule_id": "sciencebase_file_exact_v1",
                "query_rule_id": "sciencebase_exact_file_selector_v1",
                "credential_audience": "none",
                "max_response_bytes": 64 * 1024 * 1024,
            },
        ]
    return [
        {
            "ordinal": 1,
            "stage": "exact_accession_api",
            "method": "GET",
            "scheme": "https",
            "allowed_hosts": ["adams-api.nrc.gov"],
            "port": 443,
            "path_rule_id": "nrc_get_document_exact_v1",
            "query_rule_id": "none_v1",
            "credential_audience": "nrc_aps_api_key",
            "max_response_bytes": 5 * 1024 * 1024,
        },
        {
            "ordinal": 2,
            "stage": "artifact",
            "method": "GET",
            "scheme": "https",
            "allowed_hosts": ["www.nrc.gov"],
            "port": 443,
            "path_rule_id": "nrc_public_pdf_exact_v1",
            "query_rule_id": "none_v1",
            "credential_audience": "none",
            "max_response_bytes": 64 * 1024 * 1024,
        },
    ]


def _arming(connector_key: str) -> dict:
    envelope = {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": connector_key,
        "campaign_id": CAMPAIGN_ID,
        "campaign_fingerprint": CAMPAIGN_FINGERPRINT,
        "campaign_definition_sha256": DEFINITION_SHA256,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": INDEX_SHA256,
        "arming_fingerprint": ARMING_FINGERPRINT,
        "grant_sha256": GRANT_SHA256,
        "canonical_grant_fingerprint": GRANT_FINGERPRINT,
        "code_revision": "test-revision",
        "grant_id": GRANT_ID,
        "arming_nonce": ARMING_NONCE,
        "max_armings": 1,
        "supersedes_grant_sha256": None,
        "operator_mode": "single_manual_proof",
        "non_authorities": NON_AUTHORITIES,
        "max_physical_requests": 3 if connector_key == "sciencebase_mcs" else 2,
        "max_run_bytes": MAX_RUN_BYTES,
        "max_single_send_detection_allowance_bytes": (
            MAX_SINGLE_SEND_ALLOWANCE
        ),
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "min_request_interval_ms": MIN_REQUEST_INTERVAL_MS,
        "target": (
            {
                "connector_key": "sciencebase_mcs",
                "item_id": "63d1a3c6d34e06fef15006be",
                "exact_file_name": "mcs2023-germa_salient.csv",
                "locator_key": "downloadUri",
            }
            if connector_key == "sciencebase_mcs"
            else {
                "connector_key": "nrc_adams_aps",
                "accession_number": "ML17123A319",
            }
        ),
        "request_rules": _request_rules(connector_key),
        "grant_issued_at": WINDOW_START.isoformat().replace("+00:00", ".000000Z"),
        "grant_expires_at": WINDOW_END.isoformat().replace("+00:00", ".000000Z"),
        "campaign_not_before": WINDOW_START.isoformat().replace(
            "+00:00", ".000000Z"
        ),
        "campaign_expires_at": WINDOW_END.isoformat().replace(
            "+00:00", ".000000Z"
        ),
        "authorization_receipt": {
            "schema_id": "project6.connector_egress_authorization_receipt.v1",
            "connector_key": connector_key,
            "campaign_id": CAMPAIGN_ID,
            "campaign_fingerprint": CAMPAIGN_FINGERPRINT,
            "campaign_definition_sha256": DEFINITION_SHA256,
            "grant_sha256": GRANT_SHA256,
            "canonical_grant_fingerprint": GRANT_FINGERPRINT,
            "introduction_index_revision": 1,
            "introduction_index_sha256": INDEX_SHA256,
            "operator_ref_hash": "7" * 64,
            "workspace_ref_hash": "8" * 64,
            "auth_owner_mode": "identity_presence",
            "authorization_mode": "identity_presence",
            "role": None,
            "access": "write",
        },
    }
    if connector_key == "sciencebase_mcs":
        envelope["predecessor_nrc_connector_run_id"] = PREDECESSOR_RUN_ID
        envelope["predecessor_nrc_ledger_terminal_hash"] = (
            PREDECESSOR_LEDGER_HASH
        )
    return envelope


def _entry(
    ordinal: int,
    stage: str,
    *,
    connector_key: str = "sciencebase_mcs",
    body_sha256: str | None = None,
    byte_count: int | None = None,
    response_status: int = 200,
) -> dict:
    stamp = f"2026-07-29T{ordinal + 8:02d}:00:00.000000Z"
    identities = {
        "item_hydration": (
            "www.sciencebase.gov",
            "sciencebase_item_exact",
            "format_json_exact",
            "none",
        ),
        "artifact_redirect": (
            "www.sciencebase.gov",
            "sciencebase_file_exact",
            "exact_single_f_expected_filename",
            "none",
        ),
        "exact_accession_api": (
            "adams-api.nrc.gov",
            "nrc_accession_exact",
            "none",
            "nrc_aps_api_key",
        ),
    }
    if stage == "artifact":
        identity = (
            (
                "www.nrc.gov",
                "nrc_public_pdf_exact",
                "none",
                "none",
            )
            if connector_key == "nrc_adams_aps"
            else (
                "www.sciencebase.gov",
                "sciencebase_file_exact",
                "exact_single_f_expected_filename",
                "none",
            )
        )
    else:
        identity = identities[stage]
    return {
        "ordinal": ordinal,
        "stage": stage,
        "reservation_event_id": f"reserve-{ordinal}",
        "completion_event_id": f"complete-{ordinal}",
        "reserved_at": stamp,
        "send_started_at": stamp,
        "completed_at": stamp,
        "request_fingerprint": str(ordinal) * 64,
        "method": "GET",
        "host": identity[0],
        "path_class": identity[1],
        "query_class": identity[2],
        "credential_audience": identity[3],
        "outcome_class": "completed",
        "response_status": response_status,
        "byte_count": (
            byte_count
            if byte_count is not None
            else (12 if body_sha256 else 4)
        ),
        "body_sha256": body_sha256 or str(ordinal + 3) * 64,
    }


def _ledger(
    run_id: str,
    connector_key: str,
    entries: list[dict],
    *,
    eligible: bool = True,
) -> SimpleNamespace:
    projection = {
        "schema_id": "project6.connector_egress_terminal_ledger.v1",
        "connector_run_id": run_id,
        "connector_key": connector_key,
        "campaign_fingerprint": CAMPAIGN_FINGERPRINT,
        "arming_fingerprint": ARMING_FINGERPRINT,
        "grant_sha256": GRANT_SHA256,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": INDEX_SHA256,
        "frozen_max_physical_requests": 3 if connector_key == "sciencebase_mcs" else 2,
        "entries": entries,
    }
    return SimpleNamespace(
        connector_run_id=run_id,
        entries=tuple(entries),
        ledger_terminal_hash=_canonical_hash(projection),
        eligible=eligible,
        validation_errors=() if eligible else ("spent_unknown",),
        canonical_projection=projection,
    )


def _capture_root(
    *,
    log_dir_relative_path: str | None = None,
) -> tuple[Path, Path, SimpleNamespace]:
    root = (Path(settings.storage_dir) / "campaign-evidence").resolve()
    relative_log_dir = log_dir_relative_path or f"logs/{CAMPAIGN_FINGERPRINT}"
    counter_path = root / relative_log_dir / "http.jsonl"
    counter_path.parent.mkdir(parents=True, exist_ok=True)
    counter_path.touch(exist_ok=True)
    capture = SimpleNamespace(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=DEFINITION_SHA256,
        code_revision="test-revision",
        log_dir_relative_path=relative_log_dir,
        manifest_relative_path=f"logs/{CAMPAIGN_FINGERPRINT}/manifest.json",
        seal_relative_path=f"log-seals/{CAMPAIGN_FINGERPRINT}.json",
        expected_stream_files=(
            "app.jsonl",
            "http.jsonl",
            "stdout.log",
            "stderr.log",
        ),
    )
    return root, counter_path, capture


def _evidence(
    connector_key: str,
    run_id: str,
    *,
    capture: SimpleNamespace | None = None,
) -> SimpleNamespace:
    root, _, default_capture = _capture_root()
    target = (
        {
            "connector_key": "sciencebase_mcs",
            "item_id": "63d1a3c6d34e06fef15006be",
            "exact_file_name": "mcs2023-germa_salient.csv",
            "locator_key": "downloadUri",
        }
        if connector_key == "sciencebase_mcs"
        else {
            "connector_key": "nrc_adams_aps",
            "accession_number": "ML17123A319",
        }
    )
    return SimpleNamespace(
        definition_model=SimpleNamespace(
            campaign_id=CAMPAIGN_ID,
            code_revision="test-revision",
            not_before=WINDOW_START,
            expires_at=WINDOW_END,
        ),
        model=SimpleNamespace(
            connector_key=connector_key,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            code_revision="test-revision",
            grant_id=GRANT_ID,
            arming_nonce=ARMING_NONCE,
            max_armings=1,
            supersedes_grant_sha256=None,
            operator_mode="single_manual_proof",
            non_authorities=NON_AUTHORITIES,
            max_physical_requests=(
                3 if connector_key == "sciencebase_mcs" else 2
            ),
            max_run_bytes=MAX_RUN_BYTES,
            max_single_send_detection_allowance_bytes=(
                MAX_SINGLE_SEND_ALLOWANCE
            ),
            request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            min_request_interval_ms=MIN_REQUEST_INTERVAL_MS,
            issued_at=WINDOW_START,
            expires_at=WINDOW_END,
            target=target,
            request_rules=_request_rules(connector_key),
        ),
        raw_definition_sha256=DEFINITION_SHA256,
        canonical_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        raw_sha256=GRANT_SHA256,
        canonical_fingerprint=GRANT_FINGERPRINT,
        introduction_index_revision=1,
        introduction_index_sha256=INDEX_SHA256,
        marker_model=SimpleNamespace(
            connector_key=connector_key,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            campaign_definition_sha256=DEFINITION_SHA256,
            raw_grant_sha256=GRANT_SHA256,
            canonical_grant_fingerprint=GRANT_FINGERPRINT,
            connector_run_id=run_id,
        ),
        consumption_marker_sha256=MARKER_SHA256,
        index_chain=SimpleNamespace(
            evidence_root=root,
            head=SimpleNamespace(
                log_captures=(capture or default_capture,),
            ),
        ),
    )


def _write_raw(run_id: str, name: str, content: bytes) -> str:
    storage_ref = Path(run_id) / name
    path = Path(settings.connector_raw_dir) / storage_ref
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    return storage_ref.as_posix()


def _stored_path(storage_ref: str) -> Path:
    path = Path(storage_ref)
    return path if path.is_absolute() else Path(settings.connector_raw_dir) / path


def _seed_sciencebase(db, content: bytes = b"commodity,value\nGermanium,42\n"):
    digest = hashlib.sha256(content).hexdigest()
    run_id = "run-sciencebase-origin"
    target_id = "target-sciencebase-origin"
    storage_ref = _write_raw(run_id, "mcs2023-germa_salient.csv", content)
    dataset = Dataset(dataset_id="dataset-sciencebase-origin", name="MCS Germanium")
    version = DatasetVersion(
        dataset_version_id="version-sciencebase-origin",
        dataset_id=dataset.dataset_id,
        version_label="fresh",
        version_type="source",
        storage_ref=storage_ref,
        content_hash=digest,
    )
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_proof",
        status="completed",
        request_config_json={"connector_egress_arming": _arming("sciencebase_mcs")},
        request_fingerprint=ARMING_FINGERPRINT,
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        sciencebase_item_id="63d1a3c6d34e06fef15006be",
        sciencebase_file_name="mcs2023-germa_salient.csv",
        source_artifact_key="sciencebase:63d1a3c6d34e06fef15006be:mcs2023-germa_salient.csv",
        downloaded_sha256=digest,
        raw_storage_ref=storage_ref,
        dataset_id=dataset.dataset_id,
        dataset_version_id=version.dataset_version_id,
        status="downloaded",
    )
    provenance = DatasetSourceProvenance(
        dataset_source_provenance_id="provenance-sciencebase-origin",
        dataset_version_id=version.dataset_version_id,
        connector_run_id=run_id,
        source_system="sciencebase",
        source_mode="strict_live_proof",
        source_artifact_key=target.source_artifact_key,
        sciencebase_item_id=target.sciencebase_item_id,
        sciencebase_file_name=target.sciencebase_file_name,
        downloaded_sha256=digest,
        raw_storage_ref=storage_ref,
    )
    intake = L3ConnectorSourceIntakeRecord(
        connector_source_intake_record_id="intake-sciencebase-origin",
        client_request_id="intake-sciencebase-origin",
        operator_decision="record_connector_produced_source",
        source_family="connector_produced_single_source",
        source_label="MCS Germanium",
        original_filename=target.sciencebase_file_name,
        media_type="text/csv",
        content_size_bytes=len(content),
        content_sha256=digest,
        metadata_hash="1" * 64,
        authority_basis_hash="2" * 64,
        storage_ref=storage_ref,
        status="recorded",
        connector_key=run.connector_key,
        connector_run_id=run_id,
        connector_run_target_id=target_id,
    )
    db.add_all([dataset, version, run, target, provenance, intake])
    db.commit()
    return run, target, digest, storage_ref


def _seed_nrc(
    db,
    *,
    content: bytes = b"%PDF-1.7\nfixture\n",
    source_mode: str = "strict_live_proof",
    storage_ref: str | None = None,
):
    digest = hashlib.sha256(content).hexdigest()
    run_id = "run-nrc-origin"
    target_id = "target-nrc-origin"
    effective_ref = storage_ref or _write_raw(
        run_id,
        "ML17123A319.pdf",
        content,
    )
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode=source_mode,
        status="completed",
        request_config_json=(
            {"connector_egress_arming": _arming("nrc_adams_aps")}
            if source_mode == "strict_live_proof"
            else {}
        ),
        request_fingerprint=(
            ARMING_FINGERPRINT if source_mode == "strict_live_proof" else None
        ),
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        stable_release_key="ML17123A319",
        source_artifact_key="nrc-aps:ML17123A319",
        downloaded_sha256=digest,
        raw_storage_ref=effective_ref,
        status="downloaded",
    )
    linkage = ApsContentLinkage(
        aps_content_linkage_id="linkage-nrc-origin",
        content_id=digest,
        run_id=run_id,
        target_id=target_id,
        accession_number="ML17123A319",
        content_contract_id="content-contract",
        chunking_contract_id="chunking-contract",
        blob_ref=effective_ref,
        blob_sha256=digest,
    )
    db.add_all([run, target, linkage])
    db.commit()
    return run, target, linkage, digest


def _install_live_proof(
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_id: str,
    connector_key: str,
    entries: list[dict],
) -> list[dict]:
    calls: list[dict] = []

    def resolve(**kwargs):
        calls.append(kwargs)
        return _evidence(connector_key, run_id)

    monkeypatch.setattr(origin, "_resolve_historical_evidence", resolve)
    monkeypatch.setattr(
        origin,
        "_derive_terminal_ledger",
        lambda db, connector_run_id, *, counter_path: _ledger(
            connector_run_id,
            connector_key,
            entries,
        ),
    )
    monkeypatch.setattr(
        origin,
        "_compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )
    return calls


def _seed_real_nrc_terminal_evidence(
    db,
    *,
    run: ConnectorRun,
    raw_body: bytes,
    counter_path: Path,
) -> None:
    requests = (
        connector_egress_transport.FrozenPhysicalRequest(
            method="GET",
            url="https://adams-api.nrc.gov/aps/api/search/ML17123A319",
            headers={
                "Accept-Encoding": "identity",
                "Ocp-Apim-Subscription-Key": "<credential>",
            },
            credential_audience="nrc_aps_api_key",
        ),
        connector_egress_transport.FrozenPhysicalRequest(
            method="GET",
            url="https://www.nrc.gov/docs/ML1712/ML17123A319.pdf",
            headers={"Accept-Encoding": "identity"},
            credential_audience="none",
        ),
    )
    stages = ("exact_accession_api", "artifact")
    path_classes = ("nrc_accession_exact", "nrc_public_pdf_exact")
    bodies = (b"{}", raw_body)
    counted = 0
    counter_records: list[dict] = []
    for ordinal, (request, stage, path_class, body) in enumerate(
        zip(requests, stages, path_classes, bodies, strict=True),
        start=1,
    ):
        reserved_at = WINDOW_START + timedelta(hours=ordinal)
        completed_at = reserved_at + timedelta(seconds=1)
        request_fingerprint = (
            connector_egress_transport.secret_free_request_fingerprint(
                request,
                arming_fingerprint=ARMING_FINGERPRINT,
                grant_sha256=GRANT_SHA256,
                ordinal=ordinal,
                stage=stage,
            )
        )
        derived_hash = (
            None
            if ordinal == 1
            else hashlib.sha256(request.url.encode("ascii")).hexdigest()
        )
        reservation_id = connector_egress_transport._event_id(
            run.connector_run_id,
            ARMING_FINGERPRINT,
            ordinal,
            connector_egress_transport.RESERVATION_EVENT_TYPE,
        )
        completion_id = connector_egress_transport._event_id(
            run.connector_run_id,
            ARMING_FINGERPRINT,
            ordinal,
            connector_egress_transport.COMPLETION_EVENT_TYPE,
        )
        body_hash = hashlib.sha256(body).hexdigest()
        status_header_bytes = 10
        remaining = MAX_RUN_BYTES - counted
        db.add(
            ConnectorRunEvent(
                connector_run_event_id=reservation_id,
                connector_run_id=run.connector_run_id,
                phase="egress",
                stage=stage,
                event_type=connector_egress_transport.RESERVATION_EVENT_TYPE,
                status_before="running",
                status_after="running",
                reason_code="physical_request_reserved",
                error_class=None,
                metrics_json={
                    "ordinal": ordinal,
                    "stage": stage,
                    "method": "GET",
                    "host": request.url.split("/", 3)[2],
                    "path_class": path_class,
                    "query_class": "none",
                    "credential_audience": request.credential_audience,
                    "request_fingerprint": request_fingerprint,
                    "grant_sha256": GRANT_SHA256,
                    "derived_arming_hash": derived_hash,
                    "effective_streaming_cap": remaining,
                    "remaining_aggregate_counted_byte_budget": remaining,
                    "single_send_detection_allowance_bytes": (
                        connector_egress_transport.SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
                    ),
                    "reserved_at": connector_egress_transport.utc_six_z(
                        reserved_at
                    ),
                },
                created_at=reserved_at,
            )
        )
        db.add(
            ConnectorRunEvent(
                connector_run_event_id=completion_id,
                connector_run_id=run.connector_run_id,
                phase="egress",
                stage=stage,
                event_type=connector_egress_transport.COMPLETION_EVENT_TYPE,
                status_before="running",
                status_after="running",
                reason_code="completed",
                error_class=None,
                metrics_json={
                    "ordinal": ordinal,
                    "stage": stage,
                    "reservation_event_id": reservation_id,
                    "request_fingerprint": request_fingerprint,
                    "outcome_class": "completed",
                    "response_status": 200,
                    "byte_count": len(body),
                    "body_sha256": body_hash,
                    "counted_status_header_bytes": status_header_bytes,
                    "delivered_body_bytes": len(body),
                    "decoded_body_bytes": len(body),
                    "decoded_body_sha256": body_hash,
                    "send_started_at": (
                        connector_egress_transport.utc_six_z(reserved_at)
                    ),
                    "completed_at": (
                        connector_egress_transport.utc_six_z(completed_at)
                    ),
                },
                created_at=completed_at,
            )
        )
        if derived_hash is not None:
            derived_payload = {
                "kind": "derived_egress_arming",
                "ordinal": ordinal,
                "stage": stage,
                "url_sha256": derived_hash,
                "scheme": "https",
                "host": "www.nrc.gov",
                "port": 443,
                "path_rule_id": "nrc_public_pdf_exact_v1",
                "query_class": "none",
            }
            db.add_all(
                [
                    ConnectorRunEvent(
                        connector_run_event_id=str(
                            uuid5(
                                NAMESPACE_URL,
                                (
                                    "project6:connector-egress:"
                                    f"{run.connector_run_id}:"
                                    "derived_egress_arming_created:2"
                                ),
                            )
                        ),
                        connector_run_id=run.connector_run_id,
                        phase="execution",
                        stage=stage,
                        event_type="derived_egress_arming_created",
                        status_before="running",
                        status_after="running",
                        reason_code="derived_url_grant_intersection",
                        error_class=None,
                        metrics_json=derived_payload,
                        created_at=reserved_at - timedelta(seconds=1),
                    ),
                    ConnectorPolicySnapshot(
                        connector_policy_snapshot_id=str(
                            uuid5(
                                NAMESPACE_URL,
                                (
                                    "project6:connector-egress:"
                                    f"{run.connector_run_id}:derived-policy:2"
                                ),
                            )
                        ),
                        connector_run_id=run.connector_run_id,
                        policy_json=derived_payload,
                        retry_matrix_json={
                            "automatic_retry_authorized": False
                        },
                    ),
                ]
            )
        counter_records.append(
            {
                "schema_id": "project6.connector_http_counter.v1",
                "ordinal": ordinal,
                "stage": stage,
                "request_fingerprint": request_fingerprint,
                "canonical_status_header_bytes": status_header_bytes,
                "delivered_body_bytes": len(body),
                "decoded_body_bytes": len(body),
                "decoded_body_sha256": body_hash,
                "response_status": 200,
                "error_class": None,
                "monotonic_started_at": float(ordinal),
                "monotonic_stopped_at": float(ordinal) + 0.5,
                "evidence_started_at": (
                    connector_egress_transport.utc_six_z(reserved_at)
                ),
                "evidence_stopped_at": (
                    connector_egress_transport.utc_six_z(completed_at)
                ),
            }
        )
        counted += status_header_bytes + len(body)
    db.commit()
    counter_path.write_bytes(
        b"".join(
            json.dumps(
                record,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
            for record in counter_records
        )
    )


def test_authority_canonicalization_accepts_real_frozen_schema_models() -> None:
    code_revision = "1" * 40
    definition = DualLiveCampaignDefinitionV1.model_validate(
        dict(
            schema_id="project6.dual_live_campaign_definition.v1",
            campaign_id=CAMPAIGN_ID,
            code_revision=code_revision,
            connector_keys=("sciencebase_mcs", "nrc_adams_aps"),
            sciencebase_target={
                "connector_key": "sciencebase_mcs",
                "item_id": "63d1a3c6d34e06fef15006be",
                "exact_file_name": "mcs2023-germa_salient.csv",
                "locator_key": "downloadUri",
            },
            nrc_target={
                "connector_key": "nrc_adams_aps",
                "accession_number": "ML17123A319",
            },
            acceptance_profile="dual_live_to_internal_handoff_v1",
            evidence_profile="dual_live_evidence_v1",
            review_policy="security_egress_and_layer3_integrity_v1",
            required_review_roles=("security_egress", "layer3_integrity"),
            execution_order="nrc_then_sciencebase",
            package_kinds=(
                "canonical_internal",
                "user_facing",
                "review_facing",
            ),
            not_before=WINDOW_START,
            expires_at=WINDOW_END,
            non_authorities=CAMPAIGN_NON_AUTHORITIES,
        )
    )
    grant = ConnectorEgressGrantV1.model_validate(
        dict(
            schema_id="project6.connector_egress_grant.v1",
            grant_id=GRANT_ID,
            connector_key="sciencebase_mcs",
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            campaign_definition_sha256=DEFINITION_SHA256,
            code_revision=code_revision,
            arming_nonce=ARMING_NONCE,
            max_armings=1,
            issued_at=WINDOW_START,
            expires_at=WINDOW_END,
            operator_mode="local_loopback",
            target=definition.sciencebase_target,
            request_rules=expected_grant_rule_payloads("sciencebase_mcs"),
            max_physical_requests=3,
            max_run_bytes=70 * 1024 * 1024,
            max_single_send_detection_allowance_bytes=(
                SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
            ),
            request_timeout_seconds=30,
            min_request_interval_ms=1_000,
            non_authorities=COMMON_GRANT_NON_AUTHORITIES,
        )
    )
    evidence = SimpleNamespace(
        model=grant,
        definition_model=definition,
        raw_definition_sha256=DEFINITION_SHA256,
        canonical_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        raw_sha256=GRANT_SHA256,
        canonical_fingerprint=GRANT_FINGERPRINT,
        introduction_index_revision=1,
        introduction_index_sha256=INDEX_SHA256,
    )

    canonical = origin._canonical_authority_fields(
        cast(VerifiedHistoricalGrantEvidence, evidence)
    )

    assert canonical["arming_nonce"] == ARMING_NONCE
    assert canonical["grant_issued_at"] == "2026-07-29T08:00:00.000000Z"
    assert canonical["target"]["locator_key"] == "downloadUri"
    assert isinstance(canonical["request_rules"], list)
    assert canonical["request_rules"][0]["allowed_hosts"] == [
        "www.sciencebase.gov"
    ]


def test_live_receipt_passes_only_index_derived_http_counter_path(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, linkage, digest = _seed_nrc(db)
    root, expected_counter_path, _ = _capture_root()
    seen: list[Path] = []
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: _evidence(run.connector_key, run.connector_run_id),
    )

    def derive_ledger(db, connector_run_id, *, counter_path):
        seen.append(counter_path)
        return _ledger(
            connector_run_id,
            run.connector_key,
            [
                _entry(1, "exact_accession_api"),
                _entry(
                    2,
                    "artifact",
                    connector_key=run.connector_key,
                    body_sha256=digest,
                    byte_count=_stored_path(linkage.blob_ref).stat().st_size,
                ),
            ],
        )

    monkeypatch.setattr(
        origin,
        "_derive_terminal_ledger",
        derive_ledger,
    )
    monkeypatch.setattr(
        origin,
        "_compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )

    origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert seen == [expected_counter_path.resolve()]
    assert expected_counter_path.is_relative_to(root)
    assert "counter_path" not in inspect.signature(
        origin.derive_connector_origin_receipt
    ).parameters
    with pytest.raises(TypeError):
        origin.derive_connector_origin_receipt(
            db,
            **{
                "connector_run_target_id": target.connector_run_target_id,
                "counter_path": expected_counter_path.parent / "attacker.jsonl",
            },
        )


def test_live_receipt_uses_real_manifest_bound_counter_reconciliation(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"%PDF-real-counter-evidence"
    run, target, _, digest = _seed_nrc(db, content=content)
    run.source_mode = "strict_live_egress"
    db.commit()
    _, counter_path, capture = _capture_root()
    _seed_real_nrc_terminal_evidence(
        db,
        run=run,
        raw_body=content,
        counter_path=counter_path,
    )
    evidence = _evidence(
        run.connector_key,
        run.connector_run_id,
        capture=capture,
    )
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: evidence,
    )
    monkeypatch.setattr(
        origin,
        "_compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )
    monkeypatch.setattr(
        connector_egress_arming,
        "compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )

    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert receipt["proof_class"] == "fresh_live"
    assert receipt["raw_content_sha256"] == digest
    assert receipt["ledger_terminal_hash"]

    counter_path.write_bytes(counter_path.read_bytes().splitlines()[0] + b"\n")
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_terminal_ledger_ineligible"


@pytest.mark.parametrize(
    "capture_field",
    [
        "campaign_id",
        "campaign_definition_sha256",
        "code_revision",
        "log_dir_relative_path",
        "manifest_relative_path",
        "seal_relative_path",
        "expected_stream_files",
    ],
)
def test_live_receipt_rejects_mismatched_counter_capture_authority(
    db,
    monkeypatch: pytest.MonkeyPatch,
    capture_field: str,
) -> None:
    run, target, _, _ = _seed_nrc(db)
    _, _, capture = _capture_root()
    setattr(
        capture,
        capture_field,
        (
            ("http.jsonl",)
            if capture_field == "expected_stream_files"
            else "attacker"
        ),
    )
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: _evidence(
            run.connector_key,
            run.connector_run_id,
            capture=capture,
        ),
    )
    monkeypatch.setattr(
        origin,
        "_compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_counter_authority_mismatch"


def test_live_receipt_rejects_symlinked_http_counter(
    db,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run, target, _, _ = _seed_nrc(db)
    root, counter_path, capture = _capture_root()
    outside = tmp_path / "outside-http.jsonl"
    outside.write_text("{}\n", encoding="utf-8")
    counter_path.unlink()
    try:
        counter_path.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: _evidence(
            run.connector_key,
            run.connector_run_id,
            capture=capture,
        ),
    )
    monkeypatch.setattr(
        origin,
        "_compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_counter_path_reparse"
    assert counter_path.is_relative_to(root)


def test_sciencebase_receipt_is_stable_target_derived_and_rehashes_raw_bytes(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, digest, storage_ref = _seed_sciencebase(db)
    calls = _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=[
            _entry(1, "item_hydration"),
            _entry(
                2,
                "artifact",
                body_sha256=digest,
                byte_count=_stored_path(storage_ref).stat().st_size,
            ),
        ],
    )

    first = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    second = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert first == second
    assert first["proof_class"] == "fresh_live"
    assert first["raw_content_sha256"] == digest
    assert first["dataset_version_id"] == "version-sciencebase-origin"
    assert first["dataset_source_provenance_id"] == "provenance-sciencebase-origin"
    assert first["connector_source_intake_record_id"] == "intake-sciencebase-origin"
    assert first["raw_storage_ref"] == storage_ref
    assert first["receipt_hash"] == _canonical_hash(
        {key: value for key, value in first.items() if key != "receipt_hash"}
    )
    assert first["receipt_hash"] == (
        "814b6b83a2bc1c3c21e4b3838c462fba"
        "8fd98ae8b681743a04a4c47a069d6139"
    )
    assert calls[0] == {
        "connector_key": "sciencebase_mcs",
        "campaign_id": CAMPAIGN_ID,
        "expected_campaign_fingerprint": CAMPAIGN_FINGERPRINT,
        "expected_grant_sha256": GRANT_SHA256,
    }

    _stored_path(storage_ref).write_bytes(b"changed")
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_raw_hash_mismatch"


@pytest.mark.parametrize(
    "tamper_field",
    ["max_run_bytes", "request_rules", "authorization_receipt"],
)
def test_mutable_arming_must_equal_protected_historical_authority(
    db,
    monkeypatch: pytest.MonkeyPatch,
    tamper_field: str,
) -> None:
    run, target, digest, storage_ref = _seed_sciencebase(db)
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=[
            _entry(1, "item_hydration"),
            _entry(
                2,
                "artifact",
                body_sha256=digest,
                byte_count=_stored_path(storage_ref).stat().st_size,
            ),
        ],
    )
    envelope = dict(run.request_config_json["connector_egress_arming"])
    if tamper_field == "max_run_bytes":
        envelope[tamper_field] = MAX_RUN_BYTES + 1
    elif tamper_field == "request_rules":
        envelope[tamper_field] = {"method": "POST"}
    else:
        receipt = dict(envelope["authorization_receipt"])
        receipt["grant_sha256"] = "0" * 64
        envelope[tamper_field] = receipt
    run.request_config_json = {"connector_egress_arming": envelope}
    db.commit()

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_authority_binding_mismatch"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("method", "POST"),
        ("host", "attacker.invalid"),
        ("path_class", "wrong_path"),
        ("query_class", "wrong_query"),
        ("credential_audience", "none"),
    ],
)
def test_terminal_request_identity_must_equal_protected_grant_rule(
    db,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    run, target, linkage, digest = _seed_nrc(db)
    entries = [
        _entry(1, "exact_accession_api"),
        _entry(
            2,
            "artifact",
            connector_key="nrc_adams_aps",
            body_sha256=digest,
            byte_count=_stored_path(linkage.blob_ref).stat().st_size,
        ),
    ]
    entries[0][field] = value
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=entries,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_terminal_request_identity_mismatch"


def test_stored_receipt_tampering_and_ineligible_ledger_fail_closed(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, digest, storage_ref = _seed_sciencebase(db)
    entries = [
        _entry(1, "item_hydration"),
        _entry(
            2,
            "artifact",
            body_sha256=digest,
            byte_count=_stored_path(storage_ref).stat().st_size,
        ),
    ]
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=entries,
    )
    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    target.source_reference_json = {
        "connector_origin_receipt_v1": dict(receipt),
    }
    db.commit()

    origin.assert_connector_origin_continuity(
        db,
        connector_run_target_id=target.connector_run_target_id,
        expected_receipt_hash=receipt["receipt_hash"],
        expected_bindings={
            "connector_run_id": run.connector_run_id,
            "raw_content_sha256": digest,
        },
    )

    tampered = dict(receipt)
    tampered["proof_class"] = "offline_fixture"
    target.source_reference_json = {"connector_origin_receipt_v1": tampered}
    db.commit()
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.assert_connector_origin_continuity(
            db,
            connector_run_target_id=target.connector_run_target_id,
            expected_receipt_hash=receipt["receipt_hash"],
            expected_bindings={},
        )
    assert exc.value.code == "layer3_origin_stored_receipt_hash_mismatch"

    monkeypatch.setattr(
        origin,
        "_derive_terminal_ledger",
        lambda db, connector_run_target_id, *, counter_path: _ledger(
            run.connector_run_id,
            run.connector_key,
            entries,
            eligible=False,
        ),
    )
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_terminal_ledger_ineligible"


def test_nrc_receipt_binds_linkage_content_and_exact_request_sequence(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, linkage, digest = _seed_nrc(db)
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=[
            _entry(1, "exact_accession_api"),
            _entry(
                2,
                "artifact",
                connector_key="nrc_adams_aps",
                body_sha256=digest,
                byte_count=_stored_path(linkage.blob_ref).stat().st_size,
            ),
        ],
    )

    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert receipt["proof_class"] == "fresh_live"
    assert receipt["target_identity"] == {
        "accession_number": "ML17123A319",
    }
    assert receipt["aps_content_linkage_id"] == linkage.aps_content_linkage_id
    assert receipt["content_id"] == digest
    assert receipt["raw_content_sha256"] == linkage.blob_sha256
    assert receipt["dataset_version_id"] is None

    linkage.blob_sha256 = "0" * 64
    db.commit()
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_aps_linkage_mismatch"


@pytest.mark.parametrize(
    "entries",
    [
        [
            _entry(
                2,
                "artifact",
                connector_key="nrc_adams_aps",
                body_sha256="7" * 64,
            ),
            _entry(1, "exact_accession_api"),
        ],
        [
            _entry(1, "exact_accession_api"),
            _entry(1, "exact_accession_api"),
            _entry(
                2,
                "artifact",
                connector_key="nrc_adams_aps",
                body_sha256="7" * 64,
            ),
        ],
    ],
)
def test_reordered_or_duplicated_terminal_ledger_fails_closed(
    db,
    monkeypatch: pytest.MonkeyPatch,
    entries: list[dict],
) -> None:
    run, target, _, digest = _seed_nrc(db, content=b"%PDF-ledger-order")
    entries[-1]["body_sha256"] = digest
    for entry in entries:
        if entry["stage"] == "artifact":
            entry["byte_count"] = _stored_path(
                target.raw_storage_ref
            ).stat().st_size
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=entries,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_request_sequence_mismatch"


def test_send_timestamp_at_expiry_is_outside_half_open_authority_window(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, linkage, digest = _seed_nrc(db, content=b"%PDF-window")
    entries = [
        _entry(1, "exact_accession_api"),
        _entry(
            2,
            "artifact",
            connector_key="nrc_adams_aps",
            body_sha256=digest,
            byte_count=_stored_path(linkage.blob_ref).stat().st_size,
        ),
    ]
    entries[1]["send_started_at"] = "2026-07-30T08:00:00.000000Z"
    entries[1]["completed_at"] = "2026-07-30T08:00:00.000000Z"
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=entries,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_send_outside_authority_window"


def test_sciencebase_redirect_send_requires_redirect_artifact_response(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, digest, storage_ref = _seed_sciencebase(
        db,
        content=b"commodity,value\nGermanium,43\n",
    )
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=[
            _entry(1, "item_hydration"),
            _entry(2, "artifact", response_status=200),
            _entry(
                3,
                "artifact_redirect",
                body_sha256=digest,
                byte_count=_stored_path(storage_ref).stat().st_size,
            ),
        ],
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_redirect_sequence_mismatch"


def test_artifact_byte_count_must_equal_rehashed_raw_size(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, linkage, digest = _seed_nrc(db, content=b"%PDF-byte-count")
    raw_size = _stored_path(linkage.blob_ref).stat().st_size
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=[
            _entry(1, "exact_accession_api"),
            _entry(
                2,
                "artifact",
                connector_key="nrc_adams_aps",
                body_sha256=digest,
                byte_count=raw_size - 1,
            ),
        ],
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_artifact_completion_mismatch"


def test_terminal_ledger_frozen_ceiling_must_equal_arming(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, linkage, digest = _seed_nrc(db, content=b"%PDF-ceiling")
    entries = [
        _entry(1, "exact_accession_api"),
        _entry(
            2,
            "artifact",
            connector_key="nrc_adams_aps",
            body_sha256=digest,
            byte_count=_stored_path(linkage.blob_ref).stat().st_size,
        ),
    ]
    ledger = _ledger(run.connector_run_id, run.connector_key, entries)
    projection = dict(ledger.canonical_projection)
    projection["frozen_max_physical_requests"] = 3
    ledger.canonical_projection = projection
    ledger.ledger_terminal_hash = _canonical_hash(projection)
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: _evidence(run.connector_key, run.connector_run_id),
    )
    monkeypatch.setattr(
        origin,
        "_derive_terminal_ledger",
        lambda db, connector_run_id, *, counter_path: ledger,
    )
    monkeypatch.setattr(
        origin,
        "_compute_arming_fingerprint",
        lambda envelope: ARMING_FINGERPRINT,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_terminal_ledger_binding_mismatch"


def test_fixed_manifest_source_derives_offline_fixture_without_live_resolvers(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_root = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "nrc_aps_docs"
        / "v1"
    )
    fixture_path = fixture_root / "ML17123A319.pdf"
    content = fixture_path.read_bytes()
    run, target, _, digest = _seed_nrc(
        db,
        content=content,
        source_mode="offline_fixture",
        storage_ref=str(fixture_path),
    )
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: pytest.fail("offline fixture resolved live authority"),
    )
    monkeypatch.setattr(
        origin,
        "_derive_terminal_ledger",
        lambda *args, **kwargs: pytest.fail("offline fixture derived live ledger"),
    )

    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert receipt["proof_class"] == "offline_fixture"
    assert receipt["raw_content_sha256"] == digest
    assert receipt["fixture_id"] == "ml17123a319"
    assert receipt["fixture_manifest_ref"] == (
        "tests/fixtures/nrc_aps_docs/v1/manifest.json"
    )
    assert receipt["fixture_manifest_sha256"] == hashlib.sha256(
        (fixture_root / "manifest.json").read_bytes()
    ).hexdigest()
    assert "proof_class" not in inspect.signature(
        origin.derive_connector_origin_receipt
    ).parameters

    run.request_config_json = ["not", "an", "object"]
    db.commit()
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_request_config_invalid"
