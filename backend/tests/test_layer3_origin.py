from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import create_engine, event, inspect as sa_inspect, select
from sqlalchemy.dialects import postgresql
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
    L3PassRun,
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
from app.services import (
    connector_egress_arming,
    connector_egress_transport,
    connectors_nrc_adams,
    layer3_connector_source_intake as connector_intake,
    layer3_workbench,
    nrc_aps_artifact_ingestion,
    nrc_aps_document_processing,
    nrc_aps_phase_b_linkage as phase_b,
)
from app.services.connector_egress_authorization import (
    VerifiedHistoricalGrantEvidence,
)
from app.services.raw_storage_handles import persist_locked_raw_file


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
_CUSTODY_KEY = "nrc_phase_b_custody_v1"
_CUSTODY_SCHEMA = "project6.nrc_phase_b_custody.v1"
_CUSTODY_ATTEMPT = "22222222-2222-4222-8222-222222222222"


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
    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage",
        _verify_synthetic_phase_b,
    )
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def origin_file_dbs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage))
    Path(settings.connector_raw_dir).mkdir(parents=True)
    db_path = tmp_path / "origin-dirty.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        future=True,
    )
    first = factory()
    second = factory()
    try:
        yield first, second
    finally:
        first.close()
        second.close()
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


def _seed_actual_sciencebase_phase_a(db):
    content = b"county,value\n001,1\n"
    digest = hashlib.sha256(content).hexdigest()
    raw_dir = Path(settings.connector_raw_dir) / "sha256"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{digest}.csv"
    raw_path.write_bytes(content)
    run = ConnectorRun(
        connector_run_id="run-sciencebase-phase-a-origin",
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-sciencebase-phase-a-origin",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id="63d1a3c6d34e06fef15006be",
        sciencebase_item_url=None,
        sciencebase_file_name="mcs2023-germa_salient.csv",
        sciencebase_download_uri=None,
        artifact_surface="files",
        artifact_locator_type="downloadUri_hash_only",
        source_artifact_key=(
            "sciencebase:63d1a3c6d34e06fef15006be:"
            "mcs2023-germa_salient.csv"
        ),
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path.resolve()),
        public_read_confirmed=True,
        status="downloaded",
    )
    db.add_all([run, target])
    db.commit()
    intake = connector_intake._stage_strict_sciencebase_source_intake(
        db,
        run=run,
        target=target,
    )
    dataset = Dataset(
        dataset_id="dataset-sciencebase-phase-a-origin",
        name="MCS Germanium Phase A",
    )
    version = DatasetVersion(
        dataset_version_id="version-sciencebase-phase-a-origin",
        dataset_id=dataset.dataset_id,
        version_label="fresh",
        version_type="source",
        storage_ref=str(raw_path.resolve()),
        content_hash=digest,
    )
    provenance = DatasetSourceProvenance(
        dataset_source_provenance_id=(
            "provenance-sciencebase-phase-a-origin"
        ),
        dataset_version_id=version.dataset_version_id,
        connector_run_id=run.connector_run_id,
        source_system="sciencebase",
        source_mode="strict_live_egress",
        source_artifact_key=target.source_artifact_key,
        sciencebase_item_id=target.sciencebase_item_id,
        sciencebase_file_name=target.sciencebase_file_name,
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path.resolve()),
        source_reference_json={
            "schema_id": "project6.sciencebase_phase_a_provenance.v1",
            "connector_key": "sciencebase_mcs",
            "connector_run_target_id": target.connector_run_target_id,
            "item_id": target.sciencebase_item_id,
            "exact_file_name": target.sciencebase_file_name,
            "artifact_surface": "files",
            "source_mode": "strict_live_egress",
            "raw_sha256": digest,
            "storage_class": "connector_raw_sha256",
        },
    )
    target.dataset_id = dataset.dataset_id
    target.dataset_version_id = version.dataset_version_id
    run.status = "completed"
    run.request_config_json = {
        "connector_egress_arming": _arming("sciencebase_mcs")
    }
    run.request_fingerprint = ARMING_FINGERPRINT
    db.add_all([dataset, version, provenance])
    db.commit()
    return run, target, provenance, intake, digest, raw_path


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
    if source_mode != "offline_fixture":
        target.source_reference_json = {
            _CUSTODY_KEY: {
                "schema_id": _CUSTODY_SCHEMA,
                "status": "verified",
                "attempt_id": _CUSTODY_ATTEMPT,
                "connector_run_id": run_id,
                "connector_run_target_id": target_id,
                "aps_content_linkage_id": linkage.aps_content_linkage_id,
                "content_id": linkage.content_id,
                "blob_ref": effective_ref,
                "blob_sha256": digest,
                "blob_size_bytes": _stored_path(effective_ref).stat().st_size,
            }
        }
    db.add_all([run, target, linkage])
    db.commit()
    return run, target, linkage, digest


def _strict_phase_b_output() -> dict:
    first = (
        "NRC admitted content remains bound to server-owned raw bytes "
        "and exact accession authority."
    )
    second = (
        "Phase B creates canonical chunks without changing Phase A "
        "acquisition state or URL posture."
    )
    normalized_text = f"{first}\n{second}"
    return {
        "declared_content_type": "application/pdf",
        "sniffed_content_type": "application/pdf",
        "effective_content_type": "application/pdf",
        "media_detection_status": "declared_and_sniffed_match",
        "document_processing_contract_id": (
            nrc_aps_document_processing.APS_DOCUMENT_EXTRACTION_CONTRACT_ID
        ),
        "extractor_id": (
            nrc_aps_document_processing.APS_PDF_EXTRACTOR_ID
        ),
        "normalization_contract_id": (
            nrc_aps_document_processing.APS_TEXT_NORMALIZATION_CONTRACT_ID
        ),
        "document_class": "layout_complex_pdf",
        "page_count": 2,
        "quality_status": (
            nrc_aps_document_processing.APS_QUALITY_STATUS_STRONG
        ),
        "degradation_codes": [],
        "ordered_units": [
            {
                "page_number": 1,
                "unit_kind": "pdf_text_block",
                "text": first,
                "bbox": [1.0, 2.0, 300.0, 40.0],
                "start_char": 0,
                "end_char": len(first),
            },
            {
                "page_number": 2,
                "unit_kind": "pdf_text_block",
                "text": second,
                "bbox": [1.0, 2.0, 320.0, 42.0],
                "start_char": len(first) + 1,
                "end_char": len(normalized_text),
            },
        ],
        "page_summaries": [
            {"page_number": 1, "unit_count": 1, "source": "native"},
            {"page_number": 2, "unit_count": 1, "source": "native"},
        ],
        "native_page_count": 2,
        "ocr_page_count": 0,
        "weak_page_count": 0,
        "visual_page_refs": [],
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(
            normalized_text.encode("utf-8")
        ).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }


def _seed_actual_nrc_phase_b(
    db,
    monkeypatch: pytest.MonkeyPatch,
):
    raw_bytes = b"%PDF-1.7\nstrict origin Phase B fixture\n%%EOF"
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_root = Path(settings.connector_raw_dir)
    raw_path = raw_root / nrc_aps_artifact_ingestion.blob_relative_path(
        sha256=digest
    )
    persist_locked_raw_file(raw_root, raw_path, raw_bytes)
    completed_at = WINDOW_START.replace(tzinfo=None)
    run = ConnectorRun(
        connector_run_id="run-nrc-phase-b-origin",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="completed",
        submission_idempotency_key="egress-arm:run-nrc-phase-b-origin",
        request_config_json={
            "connector_egress_arming": _arming("nrc_adams_aps")
        },
        request_fingerprint=ARMING_FINGERPRINT,
        completed_at=completed_at,
        discovered_count=1,
        selected_count=1,
        downloaded_count=1,
        ingested_count=0,
        consumed_bytes=len(raw_bytes),
        failed_count=0,
        terminal_target_count=1,
        nonterminal_target_count=0,
        execution_lease_owner=None,
        execution_lease_token=None,
        execution_lease_expires_at=completed_at,
        error_summary=None,
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-nrc-phase-b-origin",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        stable_release_key="ML17123A319",
        stable_release_identifier="adams_accession:ML17123A319",
        identifiers_json=[
            {"type": "AccessionNumber", "value": "ML17123A319"}
        ],
        sciencebase_file_name="ML17123A319.pdf",
        artifact_surface="files",
        selection_source="strict_exact_accession",
        selection_scope="dual_live_proof_v1",
        selection_match_basis="exact_accession",
        artifact_locator_type=(
            connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
        ),
        source_artifact_key="nrc_adams_aps::ML17123A319",
        canonical_artifact_key="nrc_adams_aps::ML17123A319",
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path),
        fetch_policy_mode="strict_live_egress",
        redirect_count=0,
        aliases_json=[],
        source_reference_json={
            "schema_id": "project6.nrc_raw_admission.v1",
            "accession_number": "ML17123A319",
            "artifact_file_name": "ML17123A319.pdf",
            "detail_response_sha256": "3" * 64,
            "artifact_url_sha256": "4" * 64,
            "artifact_path_class": (
                connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
            ),
            "raw_content_sha256": digest,
            "raw_content_size_bytes": len(raw_bytes),
            "media_type": "application/pdf",
            "blob_storage_layout": "nrc_aps_blob_sha256_v1",
        },
        permission_snapshot_json={"direct_public_200": True},
        access_level_summary="public_direct_200",
        public_read_confirmed=True,
        status="downloaded",
        retry_eligible=False,
        attempt_count=1,
        downloaded_at=completed_at,
        last_attempt_at=completed_at,
        last_stage_transition_at=completed_at,
    )
    terminal = ConnectorRunEvent(
        connector_run_event_id=connector_egress_arming._deterministic_id(
            run.connector_run_id,
            "egress_run_terminal",
        ),
        connector_run_id=run.connector_run_id,
        phase="execution",
        stage="terminal",
        event_type="egress_run_terminal",
        status_before="running",
        status_after="completed",
        reason_code="nrc_raw_admission_completed",
        metrics_json={
            "outcome_class": "nrc_raw_admission_completed",
            "arming_fingerprint": ARMING_FINGERPRINT,
            "campaign_introduction_index_revision": 1,
            "campaign_introduction_index_sha256": INDEX_SHA256,
        },
        created_at=completed_at,
    )
    db.add_all([run, target, terminal])
    db.commit()
    monkeypatch.setattr(
        phase_b.nrc_aps_strict_parse,
        "parse_admitted_blob_strict",
        lambda **kwargs: deepcopy(_strict_phase_b_output()),
    )
    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    return run, target, linkage, digest, raw_path


def _verify_synthetic_phase_b(
    db,
    *,
    connector_run_target_id: str,
):
    anchor = origin._read_origin_anchor(
        db,
        target_id=connector_run_target_id,
    )
    run = anchor.run.materialize(ConnectorRun)
    target = anchor.target.materialize(ConnectorRunTarget)
    linkage = anchor.linkages[0].materialize(ApsContentLinkage)
    raw_path = _stored_path(str(target.raw_storage_ref))
    return phase_b.NrcPhaseBVerifiedState(
        connector_run_id=run.connector_run_id,
        connector_run_target_id=target.connector_run_target_id,
        aps_content_linkage_id=linkage.aps_content_linkage_id,
        content_id=linkage.content_id,
        raw_storage_ref=str(raw_path.resolve()),
        raw_content_sha256=str(target.downloaded_sha256),
        raw_content_size_bytes=raw_path.stat().st_size,
    )


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
    if connector_key == "nrc_adams_aps":
        monkeypatch.setattr(
            phase_b,
            "verify_strict_nrc_phase_b_linkage",
            _verify_synthetic_phase_b,
        )
    return calls


def _seed_nrc_with_live_proof(
    db,
    monkeypatch: pytest.MonkeyPatch,
    *,
    content: bytes,
):
    run, target, linkage, digest = _seed_nrc(db, content=content)
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
    return run, target, linkage, digest


@contextmanager
def _record_dml(db, prefixes: tuple[str, ...]):
    statements: list[str] = []

    def record(
        connection,
        cursor,
        statement: str,
        parameters,
        context,
        executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith(prefixes):
            statements.append(statement)

    event.listen(db.get_bind(), "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", record)


@contextmanager
def _record_select_sql(db):
    statements: list[tuple[str, tuple[object, ...]]] = []

    def record(
        connection,
        cursor,
        statement: str,
        parameters,
        context,
        executemany: bool,
    ) -> None:
        normalized = " ".join(statement.lower().split())
        if normalized.startswith("select "):
            assert isinstance(parameters, tuple)
            statements.append((normalized, parameters))

    event.listen(db.get_bind(), "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", record)


def _anchor_events(
    *,
    run_id: str,
    count: int,
) -> list[ConnectorRunEvent]:
    return [
        ConnectorRunEvent(
            connector_run_event_id=f"fanout-event-{ordinal:02d}",
            connector_run_id=run_id,
            event_type="fanout_contract_test",
            metrics_json={"ordinal": ordinal},
            created_at=WINDOW_START + timedelta(seconds=ordinal),
        )
        for ordinal in range(count)
    ]


def _anchor_policies(
    *,
    run_id: str,
    count: int,
) -> list[ConnectorPolicySnapshot]:
    return [
        ConnectorPolicySnapshot(
            connector_policy_snapshot_id=f"fanout-policy-{ordinal:02d}",
            connector_run_id=run_id,
            policy_json={"ordinal": ordinal},
            retry_matrix_json={},
        )
        for ordinal in range(count)
    ]


def _overflow_linkage(
    *,
    run_id: str,
    target_id: str,
) -> ApsContentLinkage:
    return ApsContentLinkage(
        aps_content_linkage_id="fanout-linkage",
        content_id="8" * 64,
        run_id=run_id,
        target_id=target_id,
        accession_number="ML17123A319",
        content_contract_id="fanout-content-contract",
        chunking_contract_id="fanout-chunking-contract",
        blob_ref="fanout.pdf",
        blob_sha256="8" * 64,
    )


def _overflow_provenance(
    *,
    run_id: str,
    version_id: str,
) -> DatasetSourceProvenance:
    return DatasetSourceProvenance(
        dataset_source_provenance_id="fanout-provenance",
        dataset_version_id=version_id,
        connector_run_id=run_id,
        source_system="sciencebase",
        source_mode="strict_live_proof",
        source_artifact_key="sciencebase:fanout",
        downloaded_sha256="8" * 64,
        raw_storage_ref="fanout.csv",
    )


def _overflow_intake(
    *,
    connector_key: str,
    run_id: str,
    target_id: str,
) -> L3ConnectorSourceIntakeRecord:
    return L3ConnectorSourceIntakeRecord(
        connector_source_intake_record_id="fanout-intake",
        client_request_id="fanout-intake",
        operator_decision="record_connector_produced_source",
        source_family="connector_produced_single_source",
        source_label="Fanout",
        original_filename="fanout.csv",
        media_type="text/csv",
        content_size_bytes=1,
        content_sha256="8" * 64,
        metadata_hash="3" * 64,
        authority_basis_hash="4" * 64,
        storage_ref="fanout.csv",
        status="recorded",
        connector_key=connector_key,
        connector_run_id=run_id,
        connector_run_target_id=target_id,
    )


def _invoke_origin(
    operation: str,
    db,
    *,
    target_id: str,
    receipt: dict,
):
    if operation == "derive":
        return origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )
    return origin.assert_connector_origin_continuity(
        db,
        connector_run_target_id=target_id,
        expected_receipt_hash=receipt["receipt_hash"],
        expected_bindings={},
    )


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


def _seed_real_live_origin(
    db,
    monkeypatch: pytest.MonkeyPatch,
    *,
    content: bytes,
):
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
    return run, target, digest, counter_path


@pytest.mark.parametrize(
    ("connector_key", "expected_limits"),
    [
        (
            "nrc_adams_aps",
            {
                "connector_run_event": 9,
                "connector_policy_snapshot": 3,
                "aps_content_linkage": 2,
                "dataset_source_provenance": 2,
                "l3_connector_source_intake_record": 2,
            },
        ),
        (
            "sciencebase_mcs",
            {
                "connector_run_event": 13,
                "connector_policy_snapshot": 4,
                "aps_content_linkage": 2,
                "dataset_source_provenance": 2,
                "l3_connector_source_intake_record": 2,
            },
        ),
    ],
)
def test_origin_anchor_uses_six_non_cartesian_core_selects(
    db,
    connector_key: str,
    expected_limits: dict[str, int],
) -> None:
    if connector_key == "nrc_adams_aps":
        _, target, _, _ = _seed_nrc(db)
    else:
        _, target, _, _ = _seed_sciencebase(db)
    target_id = target.connector_run_target_id
    collection_tables = (
        "connector_run_event",
        "connector_policy_snapshot",
        "aps_content_linkage",
        "dataset_source_provenance",
        "l3_connector_source_intake_record",
    )

    with _record_select_sql(db) as statements:
        origin._read_origin_anchor(
            db,
            target_id=target_id,
        )

    assert len(statements) == 6
    sql_statements = [statement for statement, _ in statements]
    (base_statement, _), *collection_records = statements
    collection_statements = [
        statement for statement, _ in collection_records
    ]
    assert "connector_run_target" in base_statement
    assert "connector_run" in base_statement
    assert "dataset_version" in base_statement
    assert (
        "dataset_version.dataset_version_id = "
        "connector_run_target.dataset_version_id"
    ) in base_statement
    assert not any(table in base_statement for table in collection_tables)
    assert all(" order by " not in statement for statement in sql_statements)
    assert all(" limit " in statement for statement in collection_statements)
    assert sorted(
        table
        for statement in collection_statements
        for table in collection_tables
        if table in statement
    ) == sorted(collection_tables)
    assert all(
        sum(table in statement for table in collection_tables) <= 1
        for statement in sql_statements
    )
    for statement, parameters in collection_records:
        matched_tables = [
            table for table in collection_tables if table in statement
        ]
        assert len(matched_tables) == 1
        assert parameters[-2:] == (
            expected_limits[matched_tables[0]],
            0,
        )


@pytest.mark.parametrize(
    (
        "connector_key",
        "surface",
        "overflow_count",
        "expected_table",
        "max_rows",
    ),
    [
        (
            "nrc_adams_aps",
            "event",
            9,
            "connector_run_event",
            8,
        ),
        (
            "nrc_adams_aps",
            "policy",
            3,
            "connector_policy_snapshot",
            2,
        ),
        (
            "nrc_adams_aps",
            "linkage",
            1,
            "aps_content_linkage",
            1,
        ),
        (
            "sciencebase_mcs",
            "event",
            13,
            "connector_run_event",
            12,
        ),
        (
            "sciencebase_mcs",
            "policy",
            4,
            "connector_policy_snapshot",
            3,
        ),
        (
            "sciencebase_mcs",
            "provenance",
            1,
            "dataset_source_provenance",
            1,
        ),
        (
            "sciencebase_mcs",
            "intake",
            1,
            "l3_connector_source_intake_record",
            1,
        ),
    ],
)
def test_origin_anchor_rejects_collection_overflow(
    db,
    connector_key: str,
    surface: str,
    overflow_count: int,
    expected_table: str,
    max_rows: int,
) -> None:
    if connector_key == "nrc_adams_aps":
        run, target, _, _ = _seed_nrc(db)
    else:
        run, target, _, _ = _seed_sciencebase(db)

    if surface == "event":
        db.add_all(
            _anchor_events(
                run_id=run.connector_run_id,
                count=overflow_count,
            )
        )
    elif surface == "policy":
        db.add_all(
            _anchor_policies(
                run_id=run.connector_run_id,
                count=overflow_count,
            )
        )
    elif surface == "linkage":
        db.add(
            _overflow_linkage(
                run_id=run.connector_run_id,
                target_id=target.connector_run_target_id,
            )
        )
    elif surface == "provenance":
        assert isinstance(target.dataset_version_id, str)
        db.add(
            _overflow_provenance(
                run_id=run.connector_run_id,
                version_id=target.dataset_version_id,
            )
        )
    else:
        db.add(
            _overflow_intake(
                connector_key=run.connector_key,
                run_id=run.connector_run_id,
                target_id=target.connector_run_target_id,
            )
        )
    db.commit()

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._read_origin_anchor(
            db,
            target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == (
        "layer3_origin_anchor_cardinality_exceeded"
    )
    assert excinfo.value.details == {
        "table": expected_table,
        "max_rows": max_rows,
        "observed_at_least": max_rows + 1,
    }


@pytest.mark.parametrize(
    ("connector_key", "event_cap", "policy_cap"),
    [
        ("nrc_adams_aps", 8, 2),
        ("sciencebase_mcs", 12, 3),
    ],
)
def test_origin_anchor_accepts_frozen_collection_cap_boundaries(
    db,
    connector_key: str,
    event_cap: int,
    policy_cap: int,
) -> None:
    if connector_key == "nrc_adams_aps":
        run, target, _, _ = _seed_nrc(db)
    else:
        run, target, _, _ = _seed_sciencebase(db)
    db.add_all(
        [
            *_anchor_events(
                run_id=run.connector_run_id,
                count=event_cap,
            ),
            *_anchor_policies(
                run_id=run.connector_run_id,
                count=policy_cap,
            ),
        ]
    )
    db.commit()

    anchor = origin._read_origin_anchor(
        db,
        target_id=target.connector_run_target_id,
    )

    assert len(anchor.events) == event_cap
    assert len(anchor.policy_snapshots) == policy_cap
    assert len(anchor.linkages) == (
        1 if connector_key == "nrc_adams_aps" else 0
    )
    assert len(anchor.dataset_versions) == (
        1 if connector_key == "sciencebase_mcs" else 0
    )
    assert len(anchor.provenances) == (
        1 if connector_key == "sciencebase_mcs" else 0
    )
    assert len(anchor.intakes) == (
        1 if connector_key == "sciencebase_mcs" else 0
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


def test_explicit_settings_read_only_receipt_matches_legacy_and_ignores_globals(
    db,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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
    explicit_settings = settings.model_copy(deep=True)
    baseline = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    evidence = _evidence(run.connector_key, run.connector_run_id)
    explicit_calls: list[dict] = []

    def resolve_explicit(read_settings, **kwargs):
        assert read_settings is explicit_settings
        explicit_calls.append(kwargs)
        return evidence

    monkeypatch.setattr(
        origin,
        "resolve_historical_connector_grant_evidence_read_only",
        resolve_explicit,
    )
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: pytest.fail("legacy historical resolver was called"),
    )
    monkeypatch.setattr(
        origin,
        "_raw_storage_path",
        lambda *args, **kwargs: pytest.fail("legacy raw loader was called"),
    )
    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage",
        lambda *args, **kwargs: pytest.fail("legacy Phase-B verifier was called"),
    )
    monkeypatch.setattr(
        settings,
        "storage_dir",
        str(tmp_path / "poison-global-storage"),
    )

    derived = origin.derive_connector_origin_receipt_read_only(
        db,
        target.connector_run_target_id,
        explicit_settings,
    )

    assert derived == baseline
    assert explicit_calls == [
        {
            "connector_key": run.connector_key,
            "campaign_id": CAMPAIGN_ID,
            "expected_campaign_fingerprint": CAMPAIGN_FINGERPRINT,
            "expected_grant_sha256": GRANT_SHA256,
        }
    ]


def test_explicit_settings_read_only_nrc_receipt_has_no_global_access(
    origin_file_dbs,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db, _ = origin_file_dbs
    run, target, _, digest, raw_path = _seed_actual_nrc_phase_b(
        db,
        monkeypatch,
    )
    run_id = run.connector_run_id
    connector_key = run.connector_key
    target_id = target.connector_run_target_id
    _install_live_proof(
        monkeypatch,
        run_id=run_id,
        connector_key=connector_key,
        entries=[
            _entry(1, "exact_accession_api"),
            _entry(
                2,
                "artifact",
                connector_key="nrc_adams_aps",
                body_sha256=digest,
                byte_count=raw_path.stat().st_size,
            ),
        ],
    )
    explicit_settings = settings.model_copy(deep=True)
    baseline = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    evidence = _evidence(connector_key, run_id)
    resolver_calls: list[object] = []
    verifier_calls: list[tuple[object, str, object]] = []
    real_explicit_verifier = (
        phase_b.verify_strict_nrc_phase_b_linkage_read_only
    )

    def resolve_explicit(read_settings, **kwargs):
        resolver_calls.append(read_settings)
        return evidence

    def verify_explicit(read_db, read_target_id, read_settings):
        verifier_calls.append((read_db, read_target_id, read_settings))
        return real_explicit_verifier(
            read_db,
            read_target_id,
            read_settings,
        )

    monkeypatch.setattr(
        origin,
        "resolve_historical_connector_grant_evidence_read_only",
        resolve_explicit,
    )
    monkeypatch.setattr(
        origin,
        "_resolve_historical_evidence",
        lambda **kwargs: pytest.fail("legacy historical resolver was called"),
    )
    monkeypatch.setattr(
        origin,
        "_raw_storage_path",
        lambda *args, **kwargs: pytest.fail("legacy raw loader was called"),
    )
    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage",
        lambda *args, **kwargs: pytest.fail("legacy Phase-B verifier was called"),
    )
    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage_read_only",
        verify_explicit,
    )
    monkeypatch.setattr(
        settings,
        "storage_dir",
        str(tmp_path / "poison-global-storage"),
    )

    derived = origin.derive_connector_origin_receipt_read_only(
        db,
        target_id,
        explicit_settings,
    )

    assert derived == baseline
    assert resolver_calls == [explicit_settings]
    assert verifier_calls == [(db, target_id, explicit_settings)]


def test_explicit_settings_read_only_receipt_rejects_raw_root_escape(
    db,
    tmp_path: Path,
) -> None:
    outside_ref = str((tmp_path / "outside.pdf").resolve())
    Path(outside_ref).write_bytes(b"%PDF-outside-explicit-root")
    _, target, _, _ = _seed_nrc(
        db,
        content=Path(outside_ref).read_bytes(),
        storage_ref=outside_ref,
    )
    explicit_settings = settings.model_copy(
        update={"storage_dir": str(tmp_path / "explicit-storage")},
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin.derive_connector_origin_receipt_read_only(
            db,
            target.connector_run_target_id,
            explicit_settings,
        )

    assert excinfo.value.code == "layer3_origin_storage_ref_not_admitted"


def test_explicit_settings_read_only_receipt_rechecks_anchor(
    origin_file_dbs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = origin_file_dbs
    run, target, _, _ = _seed_nrc_with_live_proof(
        db,
        monkeypatch,
        content=b"%PDF-explicit-anchor-drift",
    )
    explicit_settings = settings.model_copy(deep=True)
    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage_read_only",
        lambda verify_db, verify_target_id, read_settings: (
            _verify_synthetic_phase_b(
                verify_db,
                connector_run_target_id=verify_target_id,
            )
        ),
    )
    monkeypatch.setattr(
        origin,
        "resolve_historical_connector_grant_evidence_read_only",
        lambda read_settings, **kwargs: _evidence(
            run.connector_key,
            run.connector_run_id,
        ),
    )
    real_validate = origin._validate_fresh_live_evidence_with_resolver
    mutations = 0

    def validate_then_mutate(*args, **kwargs):
        nonlocal mutations
        result = real_validate(*args, **kwargs)
        mutations += 1
        competing.query(ConnectorRunTarget).filter(
            ConnectorRunTarget.connector_run_target_id
            == target.connector_run_target_id
        ).update(
            {"blocked_reason": "explicit-settings-drift"},
            synchronize_session=False,
        )
        competing.commit()
        return result

    monkeypatch.setattr(
        origin,
        "_validate_fresh_live_evidence_with_resolver",
        validate_then_mutate,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin.derive_connector_origin_receipt_read_only(
            db,
            target.connector_run_target_id,
            explicit_settings,
        )

    assert excinfo.value.code == "layer3_origin_authority_drift"
    assert mutations == 1


def test_explicit_settings_read_only_receipt_preserves_caller_state(
    db,
    monkeypatch: pytest.MonkeyPatch,
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
    target_id = target.connector_run_target_id
    evidence = _evidence(run.connector_key, run.connector_run_id)
    explicit_settings = settings.model_copy(deep=True)
    monkeypatch.setattr(
        origin,
        "resolve_historical_connector_grant_evidence_read_only",
        lambda read_settings, **kwargs: evidence,
    )
    deleted = Dataset(
        dataset_id="explicit-read-deleted",
        name="Explicit read deleted",
    )
    db.add(deleted)
    db.commit()
    dirty = db.get(Dataset, "dataset-sciencebase-origin")
    assert dirty is not None
    dirty.name = "Caller-owned dirty dataset"
    pending = Dataset(
        dataset_id="explicit-read-pending",
        name="Explicit read pending",
    )
    db.add(pending)
    db.delete(deleted)
    expected_new = set(db.new)
    expected_dirty = set(db.dirty)
    expected_deleted = set(db.deleted)

    def forbidden(method_name: str):
        def fail(*args, **kwargs):
            pytest.fail(f"adapter called Session.{method_name}")

        return fail

    with _record_dml(db, ("INSERT ", "UPDATE ", "DELETE ")) as statements:
        with monkeypatch.context() as method_guard:
            for method_name in (
                "add",
                "add_all",
                "flush",
                "commit",
                "delete",
                "rollback",
            ):
                method_guard.setattr(db, method_name, forbidden(method_name))
            receipt = origin.derive_connector_origin_receipt_read_only(
                db,
                target_id,
                explicit_settings,
            )

    assert receipt["receipt_hash"]
    assert statements == []
    assert set(db.new) == expected_new
    assert set(db.dirty) == expected_dirty
    assert set(db.deleted) == expected_deleted
    assert db.in_transaction()
    db.rollback()


def test_live_receipt_uses_real_manifest_bound_counter_reconciliation(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"%PDF-real-counter-evidence"
    _, target, digest, counter_path = _seed_real_live_origin(
        db,
        monkeypatch,
        content=content,
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


@pytest.mark.parametrize("dirty_surface", ["run", "event", "policy"])
def test_dirty_terminal_ledger_authority_uses_frozen_durable_rows(
    db,
    monkeypatch: pytest.MonkeyPatch,
    dirty_surface: str,
) -> None:
    run, target, _, _ = _seed_real_live_origin(
        db,
        monkeypatch,
        content=b"%PDF-dirty-terminal-ledger",
    )
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    baseline = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    db.rollback()

    changed: object
    if dirty_surface == "run":
        authority = db.get(ConnectorRun, run_id)
        field = "request_fingerprint"
        changed = "0" * 64
    elif dirty_surface == "event":
        authority = (
            db.query(ConnectorRunEvent)
            .filter(
                ConnectorRunEvent.connector_run_id == run_id,
                ConnectorRunEvent.event_type == "egress_reserved",
            )
            .first()
        )
        assert authority is not None
        field = "metrics_json"
        event_metrics = deepcopy(authority.metrics_json)
        event_metrics["request_fingerprint"] = "0" * 64
        changed = event_metrics
    else:
        authority = (
            db.query(ConnectorPolicySnapshot)
            .filter(
                ConnectorPolicySnapshot.connector_run_id == run_id,
            )
            .first()
        )
        assert authority is not None
        field = "policy_json"
        changed = {"tampered": True}
    assert authority is not None
    setattr(authority, field, changed)
    state_before = sa_inspect(authority)
    history_before = state_before.attrs[field].history
    assert authority in db.dirty

    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as dml_statements:
        derived = origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )

    assert derived == baseline
    assert dml_statements == []
    assert sa_inspect(authority) is state_before
    assert state_before.attrs[field].history == history_before
    assert authority in db.dirty
    db.rollback()


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
    run, target, _, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    entries = [
        _entry(1, "item_hydration"),
        _entry(
            2,
            "artifact",
            body_sha256=digest,
            byte_count=intake.content_size_bytes,
        ),
    ]
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key=run.connector_key,
        entries=entries,
    )
    projection = origin.mint_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    receipt = deepcopy(
        target.source_reference_json[
            origin.ORIGIN_RECEIPT_STORAGE_KEY
        ]
    )
    assert projection["connector_origin_receipt_hash"] == (
        receipt["receipt_hash"]
    )
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
    "marker_case",
    ["missing", "pending", "malformed", "contradictory"],
)
def test_fresh_nrc_origin_requires_exact_verified_custody(
    db,
    monkeypatch: pytest.MonkeyPatch,
    marker_case: str,
) -> None:
    run, target, linkage, digest = _seed_nrc(
        db,
        content=b"%PDF-custody-gate",
    )
    source_reference = dict(target.source_reference_json)
    if marker_case == "missing":
        source_reference.pop(_CUSTODY_KEY)
    elif marker_case == "pending":
        marker = dict(source_reference[_CUSTODY_KEY])
        marker["status"] = "pending_snapshot_exit"
        source_reference[_CUSTODY_KEY] = marker
    elif marker_case == "malformed":
        source_reference[_CUSTODY_KEY] = {
            "schema_id": _CUSTODY_SCHEMA,
            "status": "verified",
        }
    else:
        marker = dict(source_reference[_CUSTODY_KEY])
        marker["content_id"] = "0" * 64
        source_reference[_CUSTODY_KEY] = marker
    target.source_reference_json = source_reference
    db.commit()
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

    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert exc.value.code == "layer3_origin_nrc_custody_ineligible"


def test_origin_assert_freshly_observes_competing_stored_receipt_change(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, linkage, digest = _seed_nrc(
        db,
        content=b"%PDF-fresh-stored-receipt",
    )
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
    source_reference = dict(target.source_reference_json)
    source_reference[origin.ORIGIN_RECEIPT_STORAGE_KEY] = deepcopy(receipt)
    target.source_reference_json = source_reference
    db.expire_on_commit = False
    db.commit()
    retained = db.get(ConnectorRunTarget, target.connector_run_target_id)
    assert retained is target
    competing = sessionmaker(
        bind=db.get_bind(),
        expire_on_commit=False,
        future=True,
    )()
    try:
        competing_target = competing.get(
            ConnectorRunTarget,
            target.connector_run_target_id,
        )
        assert competing_target is not None
        changed = dict(competing_target.source_reference_json)
        changed_receipt = dict(
            changed[origin.ORIGIN_RECEIPT_STORAGE_KEY]
        )
        changed_receipt["receipt_hash"] = "0" * 64
        changed[origin.ORIGIN_RECEIPT_STORAGE_KEY] = changed_receipt
        competing_target.source_reference_json = changed
        competing.commit()

        with pytest.raises(origin.Layer3OriginContinuityError) as exc:
            origin.assert_connector_origin_continuity(
                db,
                connector_run_target_id=target.connector_run_target_id,
                expected_receipt_hash=receipt["receipt_hash"],
                expected_bindings={},
            )
    finally:
        competing.close()

    assert exc.value.code == "layer3_origin_stored_receipt_hash_mismatch"


@pytest.mark.parametrize("operation", ["derive", "assert"])
def test_local_dirty_custody_cannot_be_autoflushed_or_attested(
    origin_file_dbs,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    db, witness = origin_file_dbs
    _, target, _, _ = _seed_nrc_with_live_proof(
        db,
        monkeypatch,
        content=b"%PDF-local-dirty-custody",
    )
    target_id = target.connector_run_target_id
    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    durable_source_reference = deepcopy(target.source_reference_json)
    durable_marker = dict(durable_source_reference[_CUSTODY_KEY])
    durable_marker["status"] = "pending_snapshot_exit"
    durable_source_reference[_CUSTODY_KEY] = durable_marker
    durable_source_reference[
        origin.ORIGIN_RECEIPT_STORAGE_KEY
    ] = deepcopy(receipt)
    target.source_reference_json = deepcopy(durable_source_reference)
    db.commit()

    local_source_reference = deepcopy(durable_source_reference)
    local_marker = dict(local_source_reference[_CUSTODY_KEY])
    local_marker["status"] = "verified"
    local_source_reference[_CUSTODY_KEY] = local_marker
    target.source_reference_json = deepcopy(local_source_reference)
    assert target in db.dirty
    state_before = sa_inspect(target)
    history_before = state_before.attrs.source_reference_json.history
    with _record_dml(db, ("UPDATE ",)) as update_statements:
        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            _invoke_origin(
                operation,
                db,
                target_id=target_id,
                receipt=receipt,
            )

    assert excinfo.value.code == (
        "layer3_origin_nrc_custody_ineligible"
        if operation == "derive"
        else "layer3_origin_identity_map_dirty"
    )
    assert update_statements == []
    assert sa_inspect(target) is state_before
    assert (
        state_before.attrs.source_reference_json.history
        == history_before
    )
    assert target.source_reference_json == local_source_reference
    assert target in db.dirty
    durable_value = (
        witness.query(ConnectorRunTarget.source_reference_json)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .scalar()
    )
    assert durable_value == durable_source_reference
    db.rollback()


def test_unrelated_pending_state_is_not_flushed_by_origin_derive(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _seed_nrc_with_live_proof(
        db,
        monkeypatch,
        content=b"%PDF-unrelated-pending",
    )
    target_id = target.connector_run_target_id
    unrelated = Dataset(
        dataset_id="unrelated-pending-dataset",
        name="Unrelated pending dataset",
    )
    db.add(unrelated)
    assert unrelated in db.new
    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as dml_statements:
        receipt = origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )

    assert receipt["receipt_hash"]
    assert dml_statements == []
    assert unrelated in db.new
    assert db.in_transaction()
    db.rollback()


@pytest.mark.parametrize("operation", ["derive", "assert"])
def test_origin_anchor_rejects_competing_durable_target_drift(
    origin_file_dbs,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    db, competing = origin_file_dbs
    _, target, _, _ = _seed_nrc_with_live_proof(
        db,
        monkeypatch,
        content=b"%PDF-origin-anchor-drift",
    )
    target_id = target.connector_run_target_id
    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    source_reference = deepcopy(target.source_reference_json)
    source_reference[origin.ORIGIN_RECEIPT_STORAGE_KEY] = deepcopy(
        receipt
    )
    target.source_reference_json = source_reference
    db.commit()
    real_validate = origin._validate_fresh_live_evidence
    mutations = 0

    def validate_then_mutate(*args, **kwargs):
        nonlocal mutations
        result = real_validate(*args, **kwargs)
        mutations += 1
        competing.query(ConnectorRunTarget).filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        ).update(
            {"blocked_reason": f"durable-drift-{operation}"},
            synchronize_session=False,
        )
        competing.commit()
        return result

    monkeypatch.setattr(
        origin,
        "_validate_fresh_live_evidence",
        validate_then_mutate,
    )

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        _invoke_origin(
            operation,
            db,
            target_id=target_id,
            receipt=receipt,
        )

    assert excinfo.value.code == "layer3_origin_authority_drift"
    assert mutations == 1
    competing.expire_all()
    changed = competing.get(ConnectorRunTarget, target_id)
    assert changed is not None
    assert changed.blocked_reason == f"durable-drift-{operation}"


def test_flushed_savepoint_receipt_is_visible_without_transaction_takeover(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _seed_nrc_with_live_proof(
        db,
        monkeypatch,
        content=b"%PDF-origin-savepoint",
    )
    target_id = target.connector_run_target_id
    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    db.rollback()

    outer = db.begin()
    nested = db.begin_nested()
    current = db.get(ConnectorRunTarget, target_id)
    assert current is not None
    source_reference = deepcopy(current.source_reference_json)
    source_reference[origin.ORIGIN_RECEIPT_STORAGE_KEY] = deepcopy(receipt)
    current.source_reference_json = source_reference
    db.flush()

    origin.assert_connector_origin_continuity(
        db,
        connector_run_target_id=target_id,
        expected_receipt_hash=receipt["receipt_hash"],
        expected_bindings={},
    )

    assert outer.is_active
    assert nested.is_active
    assert db.in_transaction()
    assert db.in_nested_transaction()
    nested.rollback()
    assert outer.is_active
    outer.rollback()


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
    assert _CUSTODY_KEY not in target.source_reference_json
    assert "proof_class" not in inspect.signature(
        origin.derive_connector_origin_receipt
    ).parameters
    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage",
        lambda *args, **kwargs: pytest.fail(
            "offline fixture invoked committed Phase-B verifier"
        ),
    )
    projection = origin.mint_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    assert projection == {
        "connector_run_target_id": target.connector_run_target_id,
        "connector_origin_receipt_hash": receipt["receipt_hash"],
    }
    assert (
        target.source_reference_json[
            origin.ORIGIN_RECEIPT_STORAGE_KEY
        ]
        == receipt
    )
    db.rollback()
    run.request_config_json = ["not", "an", "object"]
    db.commit()
    with pytest.raises(origin.Layer3OriginContinuityError) as exc:
        origin.derive_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert exc.value.code == "layer3_origin_request_config_invalid"


def test_origin_mint_public_contract_requires_caller_transaction(
    db,
) -> None:
    expected_parameters = ["db", "connector_run_target_id"]
    for function_name in (
        "mint_connector_origin_receipt",
        "verified_connector_origin_projection",
    ):
        function = getattr(origin, function_name)
        assert list(inspect.signature(function).parameters) == (
            expected_parameters
        )
        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            function(
                db,
                connector_run_target_id="target-without-transaction",
            )
        assert (
            excinfo.value.code
            == "layer3_origin_caller_transaction_required"
        )
    postgres_condition = origin._json_cas_condition(
        ConnectorRunTarget.__table__.c.source_reference_json,
        expected={"b": 2, "a": 1},
        dialect_name="postgresql",
    )
    compiled = str(
        postgres_condition.compile(
            dialect=postgresql.dialect(),
        )
    )
    assert " AS JSONB)" in compiled
    assert "source_reference_json AS JSONB" in compiled
    with pytest.raises(
        origin.Layer3OriginContinuityError
    ) as unsupported:
        origin._json_cas_condition(
            ConnectorRunTarget.__table__.c.source_reference_json,
            expected={},
            dialect_name="unsupported",
        )
    assert (
        unsupported.value.code
        == "layer3_origin_cas_dialect_unsupported"
    )


def test_actual_sciencebase_phase_a_mint_is_atomic_exact_and_replay_safe(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    intake_id = intake.connector_source_intake_record_id
    _install_live_proof(
        monkeypatch,
        run_id=run_id,
        connector_key="sciencebase_mcs",
        entries=[
            _entry(1, "item_hydration"),
            _entry(
                2,
                "artifact",
                body_sha256=digest,
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    with pytest.raises(
        connector_intake.ConnectorSourceIntakeError
    ) as pre_mint:
        connector_intake.connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=intake_id,
        )
    assert (
        pre_mint.value.code
        == "connector_source_intake_preview_origin_receipt_missing"
    )
    db.rollback()

    outer = db.begin()
    with _record_dml(
        db,
        ("SAVEPOINT", "INSERT ", "UPDATE ", "DELETE "),
    ) as first_statements:
        projection = origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )

    assert outer.is_active
    assert db.in_transaction()
    assert not db.in_nested_transaction()
    assert set(projection) == {
        "connector_run_target_id",
        "connector_origin_receipt_hash",
    }
    assert projection["connector_run_target_id"] == target_id
    assert len(
        projection["connector_origin_receipt_hash"]
    ) == 64
    assert sum(
        statement.lstrip().upper().startswith("SAVEPOINT")
        for statement in first_statements
    ) == 1
    assert sum(
        statement.lstrip().upper().startswith("UPDATE ")
        for statement in first_statements
    ) == 3

    current_target = db.get(ConnectorRunTarget, target_id)
    current_provenance = db.get(
        DatasetSourceProvenance,
        provenance.dataset_source_provenance_id,
    )
    current_intake = db.get(
        L3ConnectorSourceIntakeRecord,
        intake_id,
    )
    assert current_target is not None
    assert current_provenance is not None
    assert current_intake is not None
    stored_receipt = current_target.source_reference_json[
        origin.ORIGIN_RECEIPT_STORAGE_KEY
    ]
    assert stored_receipt["receipt_hash"] == (
        projection["connector_origin_receipt_hash"]
    )
    assert current_provenance.source_reference_json == {
        "schema_id": "project6.sciencebase_phase_a_provenance.v1",
        "connector_key": "sciencebase_mcs",
        "connector_run_target_id": target_id,
        "item_id": target.sciencebase_item_id,
        "exact_file_name": target.sciencebase_file_name,
        "artifact_surface": "files",
        "source_mode": "strict_live_egress",
        "raw_sha256": digest,
        "storage_class": "connector_raw_sha256",
        "connector_origin_receipt_hash": (
            projection["connector_origin_receipt_hash"]
        ),
    }
    for values in (
        current_intake.provenance_json,
        current_intake.summary_json["metadata"],
        current_intake.summary_json["authority_basis"],
    ):
        assert values["connector_run_target_id"] == target_id
        assert values["connector_origin_receipt_hash"] == (
            projection["connector_origin_receipt_hash"]
        )

    preview = (
        connector_intake.connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=intake_id,
        )
    )
    candidate = preview["material_candidate"]
    assert candidate["source_class"] == (
        connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )
    for surface in (
        candidate["source_identity"],
        candidate["source_provenance"],
        candidate["payload"],
    ):
        assert surface["connector_run_target_id"] == target_id
        assert surface["connector_origin_receipt_hash"] == (
            projection["connector_origin_receipt_hash"]
        )
    assert "connector_origin_receipt_hash" not in (
        candidate["load_summary"]
    )
    decision_basis = {
        key: candidate[key]
        for key in (
            "source_ref",
            "query_basis",
            "provenance_ref",
            "source_identity",
            "source_provenance",
            "payload",
            "load_summary",
        )
    }
    assert connector_intake.validate_connector_intake_gate_b_decision_basis(
        db,
        candidate_id=candidate["candidate_id"],
        decision_basis=decision_basis,
    ) == connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    downgraded_basis = deepcopy(decision_basis)
    downgraded_basis["payload"]["source_class"] = (
        connector_intake.CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
    )
    with pytest.raises(connector_intake.ConnectorSourceIntakeError) as downgraded:
        connector_intake.validate_connector_intake_gate_b_decision_basis(
            db,
            candidate_id=candidate["candidate_id"],
            decision_basis=downgraded_basis,
        )
    assert downgraded.value.code == "connector_source_intake_gate_b_payload_mismatch"

    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as verifier_dml:
        verified = origin.verified_connector_origin_projection(
            db,
            connector_run_target_id=target_id,
        )
    assert verified == projection
    assert verifier_dml == []

    with _record_dml(
        db,
        ("SAVEPOINT", "INSERT ", "UPDATE ", "DELETE "),
    ) as replay_statements:
        replay = origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )
    assert replay == projection
    assert sum(
        statement.lstrip().upper().startswith("SAVEPOINT")
        for statement in replay_statements
    ) == 1
    assert not any(
        statement.lstrip().upper().startswith(
            ("INSERT ", "UPDATE ", "DELETE ")
        )
        for statement in replay_statements
    )
    assert outer.is_active
    outer.rollback()

    durable_target = db.get(ConnectorRunTarget, target_id)
    assert durable_target is not None
    assert origin.ORIGIN_RECEIPT_STORAGE_KEY not in (
        durable_target.source_reference_json or {}
    )


def test_strict_sciencebase_public_chain_reaches_internal_prepared_handoff(
    origin_file_dbs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _ = origin_file_dbs
    run, target, _, intake, digest, raw_path = _seed_actual_sciencebase_phase_a(db)
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    with db.begin():
        origin_projection = origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    material = connector_intake.connector_source_intake_material_preview(
        db,
        connector_source_intake_record_id=intake.connector_source_intake_record_id,
    )
    candidate = material["material_candidate"]
    assert candidate["source_class"] == connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    decision_basis = {
        key: deepcopy(candidate[key])
        for key in (
            "source_ref",
            "query_basis",
            "provenance_ref",
            "source_identity",
            "source_provenance",
            "payload",
            "load_summary",
        )
    }
    gate_b = layer3_workbench.gate_b_decision(
        db,
        {
            "client_request_id": "strict-sciencebase-gate-b",
            "preflight_id": "strict-sciencebase-preflight",
            "source_set_id": "strict-sciencebase-source-set",
            "material_preview_id": material["material_preview_id"],
            "material_preview_hash": material["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": decision_basis,
                }
            ],
            "commit_reason": "strict_sciencebase_dual_live_phase_b",
            "actor": "dual_live_campaign",
        },
    )
    assert gate_b["next_state"] == "gate_c_preview_ready"
    gate_c = layer3_workbench.gate_c_preview(
        db,
        {
            "client_request_id": "strict-sciencebase-gate-c",
            "session_id": gate_b["session_id"],
            "commit_typing": True,
        },
    )
    assert gate_c["next_state"] == "plan_preview_ready"
    preview = layer3_workbench.plan_preview(
        db,
        {
            "client_request_id": "strict-sciencebase-plan-preview",
            "session_id": gate_b["session_id"],
        },
    )
    approval = layer3_workbench.plan_approval(
        db,
        {
            "client_request_id": "strict-sciencebase-plan-approval",
            "session_id": gate_b["session_id"],
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_confirmation": True,
        },
    )
    selection = layer3_workbench.execution_selection(
        db,
        {
            "client_request_id": "strict-sciencebase-selection",
            "session_id": gate_b["session_id"],
            "analysis_plan_id": approval["analysis_plan_id"],
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
    )
    pass_run = db.get(L3PassRun, selection["pass_run_ids"][0])
    assert pass_run is not None
    planned = pass_run.summary_json["planned_pass"]
    assert planned["source_intake_source_shape"] == (
        connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )
    assert planned["connector_source_intake_record_id"] == (
        intake.connector_source_intake_record_id
    )
    assert planned["connector_run_id"] == run.connector_run_id
    assert planned["connector_run_target_id"] == target.connector_run_target_id
    assert planned["connector_origin_receipt_hash"] == (
        origin_projection["connector_origin_receipt_hash"]
    )
    common = {
        "session_id": gate_b["session_id"],
        "analysis_plan_id": approval["analysis_plan_id"],
        "pass_run_id": pass_run.pass_run_id,
        "preview_id": preview["preview_id"],
        "preview_hash": preview["preview_hash"],
    }
    start = layer3_workbench.analysis_execution_start(
        db,
        {"client_request_id": "strict-sciencebase-start", **common},
    )
    db.refresh(pass_run)
    assert pass_run.output_payload_ref is not None
    assert not Path(pass_run.output_payload_ref).is_absolute()
    resolved_output_path = (
        Path(settings.artifact_storage_dir) / "layer3" / pass_run.output_payload_ref
    ).resolve()
    output_payload = json.loads(resolved_output_path.read_text(encoding="utf-8"))
    raw_path_text = str(raw_path.resolve())
    resolved_output_path_text = str(resolved_output_path)
    assert output_payload["storage_pointer"]["storage_ref"] == f"sha256:{digest}"
    assert raw_path_text not in json.dumps(output_payload, sort_keys=True)
    review = layer3_workbench.execution_result_review(
        db,
        {
            "client_request_id": "strict-sciencebase-review",
            **common,
            "analysis_run_id": start.get("analysis_run_id"),
            "operator_decision": "approved",
            "reviewed_output_items": [],
        },
    )
    package_preview = layer3_workbench.package_review_preview(
        db,
        {
            "client_request_id": "strict-sciencebase-package-preview",
            **common,
            "analysis_run_id": start.get("analysis_run_id"),
            "result_review_record_ref": review["review_record_ref"],
        },
    )
    package_preview_receipt = package_preview["package_review_preview_hash"]
    package_preview_prefix = "l3-source-intake-package-preview-"
    assert package_preview_receipt.startswith(package_preview_prefix)
    assert len(package_preview_receipt) == len(package_preview_prefix) + 16
    assert all(
        character in "0123456789abcdef"
        for character in package_preview_receipt[len(package_preview_prefix) :]
    )
    expected_kinds = ["canonical_internal", "user_facing", "review_facing"]
    package_commit = layer3_workbench.package_construction_commit(
        db,
        {
            "client_request_id": "strict-sciencebase-package-commit",
            **common,
            "analysis_run_id": start.get("analysis_run_id"),
            "result_review_record_ref": review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "expected_package_kinds": expected_kinds,
        },
    )
    submit = layer3_workbench.package_review_submit(
        db,
        {
            "client_request_id": "strict-sciencebase-package-submit",
            **common,
            "analysis_run_id": start.get("analysis_run_id"),
            "result_review_record_ref": review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "construction_basis_hash": package_commit["construction_basis_hash"],
            "reconciliation_record_id": package_commit["reconciliation_record_id"],
            "output_package_ids": package_commit["output_package_ids"],
            "payload_refs": package_commit["payload_refs"],
            "payload_hashes": package_commit["payload_hashes"],
            "expected_package_kinds": expected_kinds,
            "operator_decision": "approved",
        },
    )
    handoff = layer3_workbench.handoff_export_prepare(
        db,
        {
            "client_request_id": "strict-sciencebase-handoff",
            **common,
            "analysis_run_id": start.get("analysis_run_id"),
            "result_review_record_ref": review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "construction_basis_hash": package_commit["construction_basis_hash"],
            "reconciliation_record_id": package_commit["reconciliation_record_id"],
            "package_review_submit_record_ref": submit["submit_record_ref"],
            "package_review_state": submit["package_review_state"],
            "package_review_submit_schema_id": submit["schema_id"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "operator_decision": "authorize_prepare",
            "output_package_ids": package_commit["output_package_ids"],
            "payload_refs": package_commit["payload_refs"],
            "payload_hashes": package_commit["payload_hashes"],
            "expected_package_kinds": expected_kinds,
        },
    )
    assert review["review_state"] == "execution_result_review_approved"
    assert package_commit["package_kinds"] == expected_kinds
    assert len(package_commit["output_package_ids"]) == 3
    assert submit["package_review_state"] == "package_review_approved"
    assert handoff["handoff_export_state"] == "handoff_export_prepared"
    assert handoff["handoff_export_envelope"]["external_handoff_enabled"] is False
    assert handoff["handoff_export_envelope"]["source_shape"] == (
        connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )
    for payload_ref in package_commit["payload_refs"]:
        package_text = Path(payload_ref).read_text(encoding="utf-8")
        assert raw_path_text not in package_text
        assert resolved_output_path_text not in package_text
    for public_projection in (start, review, package_commit, submit, handoff):
        projection_text = json.dumps(public_projection, sort_keys=True)
        assert raw_path_text not in projection_text
        assert resolved_output_path_text not in projection_text


def test_mint_preserves_existing_nested_and_flushes_unrelated_work(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
    provenance_id = provenance.dataset_source_provenance_id
    intake_id = intake.connector_source_intake_record_id
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    outer = db.begin()
    caller_nested = db.begin_nested()
    unrelated = Dataset(
        dataset_id="unrelated-mint-pending",
        name="Unrelated mint pending",
    )
    unrelated_id = unrelated.dataset_id
    db.add(unrelated)
    real_begin_nested = db.begin_nested
    mint_nested_calls = 0

    def counted_begin_nested():
        nonlocal mint_nested_calls
        mint_nested_calls += 1
        return real_begin_nested()

    monkeypatch.setattr(
        db,
        "begin_nested",
        counted_begin_nested,
    )

    with _record_dml(
        db,
        ("SAVEPOINT", "INSERT ", "UPDATE ", "DELETE "),
    ) as statements:
        projection = origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )

    assert projection["connector_run_target_id"] == target_id
    assert outer.is_active
    assert caller_nested.is_active
    assert db.in_nested_transaction()
    assert unrelated not in db.new
    assert db.get(Dataset, unrelated_id) is unrelated
    assert mint_nested_calls == 1
    assert sum(
        statement.lstrip().upper().startswith("SAVEPOINT")
        for statement in statements
    ) == 2
    caller_nested.commit()
    assert outer.is_active
    outer.rollback()
    witness = sessionmaker(
        bind=db.get_bind(),
        future=True,
    )()
    try:
        reverted_target = witness.get(
            ConnectorRunTarget,
            target_id,
        )
        reverted_provenance = witness.get(
            DatasetSourceProvenance,
            provenance_id,
        )
        reverted_intake = witness.get(
            L3ConnectorSourceIntakeRecord,
            intake_id,
        )
        assert reverted_target is not None
        assert reverted_provenance is not None
        assert reverted_intake is not None
        assert origin.ORIGIN_RECEIPT_STORAGE_KEY not in (
            reverted_target.source_reference_json or {}
        )
        assert "connector_origin_receipt_hash" not in (
            reverted_provenance.source_reference_json or {}
        )
        assert "connector_origin_receipt_hash" not in (
            reverted_intake.provenance_json or {}
        )
        assert witness.get(Dataset, unrelated_id) is None
    finally:
        witness.close()


def test_mint_refuses_unverified_sqlite_nested_root_without_dml(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    prior_root = db.begin()
    origin._prepare_caller_root_transaction(db)
    prior_root.rollback()
    outer = db.begin()
    caller_nested = db.begin_nested()
    assert db.get(ConnectorRunTarget, target_id) is not None
    assert db.connection().get_nested_transaction() is not None
    unrelated = Dataset(
        dataset_id="unsafe-nested-unrelated",
        name="Unsafe nested unrelated",
    )
    db.add(unrelated)

    with _record_dml(
        db,
        ("SAVEPOINT", "INSERT ", "UPDATE ", "DELETE "),
    ) as statements:
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as excinfo:
            origin.mint_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )

    assert (
        excinfo.value.code
        == "layer3_origin_sqlite_nested_root_unverified"
    )
    assert statements == []
    assert unrelated in db.new
    assert caller_nested.is_active
    assert outer.is_active
    caller_nested.rollback()
    outer.rollback()


@pytest.mark.parametrize("pending_state", ["new", "deleted"])
def test_mint_rejects_relevant_new_or_deleted_without_dml(
    db,
    monkeypatch: pytest.MonkeyPatch,
    pending_state: str,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    outer = db.begin()
    if pending_state == "new":
        pending = ConnectorRunEvent(
            connector_run_event_id="pending-origin-event",
            connector_run_id=run.connector_run_id,
            event_type="pending_origin_event",
        )
        db.add(pending)
    else:
        pending = db.get(
            DatasetSourceProvenance,
            provenance.dataset_source_provenance_id,
        )
        assert pending is not None
        db.delete(pending)

    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as statements:
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as excinfo:
            origin.mint_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )

    assert excinfo.value.code == "layer3_origin_identity_map_dirty"
    assert statements == []
    assert outer.is_active
    assert pending in (
        db.new if pending_state == "new" else db.deleted
    )
    outer.rollback()


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        (ConnectorRunTarget, "blocked_reason", "pending-local-change"),
        (
            DatasetSourceProvenance,
            "source_mode",
            "pending-local-change",
        ),
        (
            L3ConnectorSourceIntakeRecord,
            "source_label",
            "pending-local-change",
        ),
    ],
)
def test_mint_rejects_dirty_relevant_authority_without_dml(
    db,
    monkeypatch: pytest.MonkeyPatch,
    model,
    field: str,
    value: str,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
    identities = {
        ConnectorRunTarget: target_id,
        DatasetSourceProvenance: provenance.dataset_source_provenance_id,
        L3ConnectorSourceIntakeRecord: (
            intake.connector_source_intake_record_id
        ),
    }
    _install_live_proof(
        monkeypatch,
        run_id=run.connector_run_id,
        connector_key="sciencebase_mcs",
        entries=[
            _entry(1, "item_hydration"),
            _entry(
                2,
                "artifact",
                body_sha256=digest,
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    outer = db.begin()
    authority = db.get(model, identities[model])
    assert authority is not None
    setattr(authority, field, value)
    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as dml_statements:
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as excinfo:
            origin.mint_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )

    assert excinfo.value.code == "layer3_origin_identity_map_dirty"
    assert dml_statements == []
    assert outer.is_active
    assert authority in db.dirty
    outer.rollback()


@pytest.mark.parametrize(
    ("drift_model", "drift_values"),
    [
        (
            ConnectorRunTarget,
            {"blocked_reason": "forced-cas-drift"},
        ),
        (
            DatasetSourceProvenance,
            {"blocked_reason": "forced-cas-drift"},
        ),
        (
            L3ConnectorSourceIntakeRecord,
            {"source_label": "forced-cas-drift"},
        ),
    ],
)
def test_sciencebase_cas_drift_rolls_back_only_receipt_child(
    db,
    monkeypatch: pytest.MonkeyPatch,
    drift_model,
    drift_values: dict,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    db.rollback()
    outer = db.begin()
    unrelated = Dataset(
        dataset_id=f"cas-unrelated-{drift_model.__name__}",
        name="CAS unrelated pending",
    )
    unrelated_id = unrelated.dataset_id
    db.add(unrelated)
    real_cas = origin._cas_update_anchor_row
    injected = False

    def drift_then_cas(
        session,
        *,
        row,
        model,
        values,
    ):
        nonlocal injected
        if model is drift_model and not injected:
            injected = True
            identity = origin._row_primary_identity(
                row,
                model,
            )
            primary_key = tuple(model.__table__.primary_key)
            assert len(primary_key) == len(identity) == 1
            session.execute(
                model.__table__.update()
                .where(primary_key[0] == identity[0])
                .values(**drift_values)
            )
        return real_cas(
            session,
            row=row,
            model=model,
            values=values,
        )

    monkeypatch.setattr(
        origin,
        "_cas_update_anchor_row",
        drift_then_cas,
    )
    with pytest.raises(
        origin.Layer3OriginContinuityError
    ) as excinfo:
        origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "layer3_origin_cas_conflict"
    assert injected
    assert outer.is_active
    assert db.get(Dataset, unrelated_id) is unrelated
    db.expire_all()
    current_target = db.get(ConnectorRunTarget, target_id)
    current_provenance = db.get(
        DatasetSourceProvenance,
        provenance.dataset_source_provenance_id,
    )
    current_intake = db.get(
        L3ConnectorSourceIntakeRecord,
        intake.connector_source_intake_record_id,
    )
    assert current_target is not None
    assert current_provenance is not None
    assert current_intake is not None
    assert origin.ORIGIN_RECEIPT_STORAGE_KEY not in (
        current_target.source_reference_json or {}
    )
    assert "connector_origin_receipt_hash" not in (
        current_provenance.source_reference_json or {}
    )
    assert "connector_origin_receipt_hash" not in (
        current_intake.provenance_json or {}
    )
    outer.rollback()
    assert db.get(Dataset, unrelated_id) is None


@pytest.mark.parametrize(
    ("stored_state", "expected_code"),
    [
        (
            "stale_receipt",
            "layer3_origin_stored_receipt_mismatch",
        ),
        (
            "partial_projection",
            "layer3_origin_provenance_projection_mismatch",
        ),
    ],
)
def test_stale_or_partial_stored_receipt_fails_without_repair_dml(
    db,
    monkeypatch: pytest.MonkeyPatch,
    stored_state: str,
    expected_code: str,
) -> None:
    run, target, _, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    stored = deepcopy(receipt)
    if stored_state == "stale_receipt":
        stored["source_artifact_key"] = "stale-source-artifact"
        stored["receipt_hash"] = origin._stable_hash(
            {
                key: value
                for key, value in stored.items()
                if key != "receipt_hash"
            }
        )
    target.source_reference_json = {
        **(target.source_reference_json or {}),
        origin.ORIGIN_RECEIPT_STORAGE_KEY: stored,
    }
    db.commit()
    outer = db.begin()

    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as statements:
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as excinfo:
            origin.mint_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )

    assert excinfo.value.code == expected_code
    assert statements == []
    assert outer.is_active
    current_target = db.get(ConnectorRunTarget, target_id)
    assert current_target is not None
    assert (
        current_target.source_reference_json[
            origin.ORIGIN_RECEIPT_STORAGE_KEY
        ]
        == stored
    )
    outer.rollback()


@pytest.mark.parametrize(
    ("history_state", "expected_code"),
    [
        (
            "exact_current_target",
            "layer3_origin_candidate_already_consumed",
        ),
        (
            "malformed_unattributed",
            "layer3_origin_history_claim_malformed",
        ),
        (
            "hidden_current_target",
            "layer3_origin_history_claim_malformed",
        ),
        (
            "hidden_current_provenance",
            "layer3_origin_history_claim_malformed",
        ),
        ("explicit_other_target", None),
    ],
)
def test_origin_history_claim_attribution_is_fail_closed(
    db,
    monkeypatch: pytest.MonkeyPatch,
    history_state: str,
    expected_code: str | None,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
    target_id = target.connector_run_target_id
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target_id,
    )
    receipt_hash = receipt["receipt_hash"]
    if history_state == "exact_current_target":
        claim = {
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": receipt_hash,
        }
    elif history_state == "malformed_unattributed":
        claim = {
            "connector_origin_receipt_hash": "not-a-hash",
        }
    else:
        claim = {
            "connector_run_target_id": "explicit-other-target",
            "connector_origin_receipt_hash": receipt_hash,
        }
    if history_state == "hidden_current_target":
        target.source_reference_json = {
            "hidden_claim": {
                "connector_run_target_id": target_id,
                "connector_origin_receipt_hash": receipt_hash,
            },
        }
    elif history_state == "hidden_current_provenance":
        provenance.source_reference_json = {
            "hidden_claim": {
                "connector_run_target_id": target_id,
                "connector_origin_receipt_hash": receipt_hash,
            },
        }
    history_dataset = Dataset(
        dataset_id=f"history-dataset-{history_state}",
        name="History claim dataset",
    )
    history_version = DatasetVersion(
        dataset_version_id=f"history-version-{history_state}",
        dataset_id=history_dataset.dataset_id,
        version_label="history",
        version_type="source",
    )
    history_provenance = DatasetSourceProvenance(
        dataset_source_provenance_id=(
            f"history-provenance-{history_state}"
        ),
        dataset_version_id=history_version.dataset_version_id,
        connector_run_id=None,
        source_system="history",
        source_mode="history",
        source_artifact_key=f"history:{history_state}",
        source_reference_json=claim,
    )
    db.add_all(
        [
            history_dataset,
            history_version,
            history_provenance,
        ]
    )
    db.commit()
    outer = db.begin()

    if expected_code is None:
        projection = origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )
        assert projection["connector_origin_receipt_hash"] == (
            receipt_hash
        )
    else:
        with _record_dml(
            db,
            ("INSERT ", "UPDATE ", "DELETE "),
        ) as statements:
            with pytest.raises(
                origin.Layer3OriginContinuityError
            ) as excinfo:
                origin.mint_connector_origin_receipt(
                    db,
                    connector_run_target_id=target_id,
                )
        assert excinfo.value.code == expected_code
        assert statements == []
    assert outer.is_active
    outer.rollback()


@pytest.mark.parametrize("target_state", ["missing", "wrong"])
def test_sciencebase_phase_a_target_projection_tamper_is_zero_dml(
    db,
    monkeypatch: pytest.MonkeyPatch,
    target_state: str,
) -> None:
    run, target, provenance, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    source_reference = dict(provenance.source_reference_json)
    if target_state == "missing":
        source_reference.pop("connector_run_target_id")
    else:
        source_reference["connector_run_target_id"] = "wrong-target"
    provenance.source_reference_json = source_reference
    db.commit()

    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as statements:
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as excinfo:
            origin.mint_connector_origin_receipt(
                db,
                connector_run_target_id=(
                    target.connector_run_target_id
                ),
            )
    assert (
        excinfo.value.code
        == "layer3_origin_provenance_projection_mismatch"
    )
    assert statements == []


def test_post_mint_seal_event_preserves_receipt_and_projection(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, intake, digest, _ = (
        _seed_actual_sciencebase_phase_a(db)
    )
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
                byte_count=intake.content_size_bytes,
            ),
        ],
    )
    before = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    projection = origin.mint_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    db.commit()
    db.add(
        ConnectorRunEvent(
            connector_run_event_id="sciencebase-log-capture-sealed",
            connector_run_id=run.connector_run_id,
            event_type="campaign_log_capture_sealed",
        )
    )
    db.commit()

    after = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    verified = origin.verified_connector_origin_projection(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    assert after == before
    assert verified == projection


def test_duplicate_seal_events_fail_closed(db) -> None:
    run, target, _, _ = _seed_nrc(db)
    db.add_all(
        [
            ConnectorRunEvent(
                connector_run_event_id=f"duplicate-seal-{index}",
                connector_run_id=run.connector_run_id,
                event_type="campaign_log_capture_sealed",
            )
            for index in range(2)
        ]
    )
    db.commit()

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._read_origin_anchor(
            db,
            target_id=target.connector_run_target_id,
        )
    assert (
        excinfo.value.code
        == "layer3_origin_seal_event_cardinality"
    )


@pytest.mark.parametrize("bound", ["depth", "nodes"])
def test_origin_claim_traversal_bounds_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    bound: str,
) -> None:
    if bound == "depth":
        monkeypatch.setattr(origin, "_ORIGIN_CLAIM_DEPTH_CAP", 2)
        value = {"a": {"b": {"c": {}}}}
    else:
        monkeypatch.setattr(origin, "_ORIGIN_CLAIM_NODE_CAP", 2)
        value = [1, 2, 3]
    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._origin_claims(value)
    assert (
        excinfo.value.code
        == "layer3_origin_history_claim_bounds_exceeded"
    )


def test_origin_history_query_cap_fails_closed(
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_nrc(db)
    monkeypatch.setattr(origin, "_ORIGIN_HISTORY_ROW_CAP", 0)
    table = origin._model_table(ConnectorRunTarget)
    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._bounded_history_rows(
            db,
            select(table.c.connector_run_target_id),
            table_name=str(table.name),
        )
    assert (
        excinfo.value.code
        == "layer3_origin_history_cardinality_exceeded"
    )


def test_actual_phase_b_mint_calls_committed_verifier_around_target_cas(
    origin_file_dbs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, witness = origin_file_dbs
    run, target, linkage, digest, raw_path = _seed_actual_nrc_phase_b(
        db,
        monkeypatch,
    )
    target_id = target.connector_run_target_id
    real_verifier = phase_b.verify_strict_nrc_phase_b_linkage
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
                byte_count=raw_path.stat().st_size,
            ),
        ],
    )
    operation_order: list[str] = []

    def verify_committed(db, *, connector_run_target_id: str):
        operation_order.append("verify")
        return real_verifier(
            db,
            connector_run_target_id=connector_run_target_id,
        )

    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage",
        verify_committed,
    )
    real_cas = origin._cas_update_anchor_row

    def record_cas(session, *, row, model, values):
        operation_order.append(f"cas:{model.__name__}")
        return real_cas(
            session,
            row=row,
            model=model,
            values=values,
        )

    monkeypatch.setattr(
        origin,
        "_cas_update_anchor_row",
        record_cas,
    )
    db.rollback()
    outer = db.begin()
    with _record_dml(
        db,
        ("INSERT ", "UPDATE ", "DELETE "),
    ) as dml_statements:
        projection = origin.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target_id,
        )

    assert projection == {
        "connector_run_target_id": target_id,
        "connector_origin_receipt_hash": (
            db.get(ConnectorRunTarget, target_id)
            .source_reference_json[origin.ORIGIN_RECEIPT_STORAGE_KEY][
                "receipt_hash"
            ]
        ),
    }
    assert operation_order == [
        "verify",
        "cas:ConnectorRunTarget",
        "verify",
    ]
    assert sum(
        statement.lstrip().upper().startswith("UPDATE ")
        for statement in dml_statements
    ) == 1
    assert outer.is_active
    assert linkage.aps_content_linkage_id
    witness_target = witness.get(ConnectorRunTarget, target_id)
    assert witness_target is not None
    assert origin.ORIGIN_RECEIPT_STORAGE_KEY not in (
        witness_target.source_reference_json or {}
    )
    outer.rollback()


def _downstream_snapshot_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, str], str, Path]:
    storage = tmp_path / "storage"
    root = storage / "artifacts"
    session_id = "session-content-stability"
    payload = b'{"source":"stable"}'
    payload_hash = hashlib.sha256(payload).hexdigest()
    payload_path = root / "layer3" / session_id / f"{payload_hash}.json"
    payload_path.parent.mkdir(parents=True)
    payload_path.write_bytes(payload)
    monkeypatch.setattr(settings, "storage_dir", str(storage))
    return (
        {
            "payload_hash": payload_hash,
            "payload_ref": str(payload_path),
        },
        session_id,
        payload_path,
    )


def test_downstream_snapshot_accepts_timestamp_only_churn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, session_id, payload_path = _downstream_snapshot_fixture(
        tmp_path,
        monkeypatch,
    )
    original_managed_file = origin._downstream_managed_regular_file
    preflight_count = 0

    def churn_after_initial_stat(root: Path, path: Path):
        nonlocal preflight_count
        info = original_managed_file(root, path)
        preflight_count += 1
        if preflight_count == 1:
            os.utime(
                payload_path,
                ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000),
            )
            assert payload_path.stat().st_mtime_ns != info.st_mtime_ns
        return info

    monkeypatch.setattr(
        origin,
        "_downstream_managed_regular_file",
        churn_after_initial_stat,
    )

    assert origin._read_downstream_snapshot_payload(
        snapshot,
        session_id=session_id,
    ) == {"source": "stable"}


def test_downstream_snapshot_rejects_same_size_change_between_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, session_id, payload_path = _downstream_snapshot_fixture(
        tmp_path,
        monkeypatch,
    )
    original_hash_stream = origin._downstream_hash_stream
    hash_count = 0

    def mutate_after_first_hash(*args, **kwargs):
        nonlocal hash_count
        result = original_hash_stream(*args, **kwargs)
        hash_count += 1
        if hash_count == 1:
            payload_path.write_bytes(b'{"source":"change"}')
        return result

    monkeypatch.setattr(origin, "_downstream_hash_stream", mutate_after_first_hash)

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._read_downstream_snapshot_payload(snapshot, session_id=session_id)

    assert excinfo.value.code == "layer3_downstream_origin_authority_invalid"
    assert hash_count == 3


def test_downstream_snapshot_rejects_same_size_change_after_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, session_id, payload_path = _downstream_snapshot_fixture(
        tmp_path,
        monkeypatch,
    )
    original_hash_stream = origin._downstream_hash_stream
    hash_count = 0

    def mutate_after_second_hash(*args, **kwargs):
        nonlocal hash_count
        result = original_hash_stream(*args, **kwargs)
        hash_count += 1
        if hash_count == 2:
            payload_path.write_bytes(b'{"source":"change"}')
        return result

    monkeypatch.setattr(origin, "_downstream_hash_stream", mutate_after_second_hash)

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._read_downstream_snapshot_payload(snapshot, session_id=session_id)

    assert excinfo.value.code == "layer3_downstream_origin_authority_invalid"
    assert hash_count == 3
