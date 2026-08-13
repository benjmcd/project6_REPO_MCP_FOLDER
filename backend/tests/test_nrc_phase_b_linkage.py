from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Generator
from uuid import UUID

import pytest
from sqlalchemy import (
    create_engine,
    event as sa_event,
    inspect as sa_inspect,
    select,
    update,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunSubmission,
    ConnectorRunTarget,
)
from app.schemas.api import (
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorEgressArmingIn,
    expected_grant_rule_payloads,
)
from app.services import connector_egress_arming
from app.services import connectors_nrc_adams
from app.services import layer3_origin_continuity as origin
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_content_index
from app.services import nrc_aps_document_processing
from app.services import nrc_aps_strict_parse
from app.services import raw_storage_handles as raw_handles
from app.services.raw_storage_handles import persist_locked_raw_file


_CUSTODY_KEY = "nrc_phase_b_custody_v1"
_CUSTODY_SCHEMA = "project6.nrc_phase_b_custody.v1"
_PENDING_CUSTODY = "pending_snapshot_exit"
_VERIFIED_CUSTODY = "verified"
_ATTEMPT_ID = "11111111-1111-4111-8111-111111111111"


def _phase_b() -> Any:
    return importlib.import_module(
        "app.services.nrc_aps_phase_b_linkage"
    )


def _create_real_nrc_arming(
    db: Session,
    tmp_path: Path,
) -> ConnectorRun:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    campaign_id = "27693345-6a47-45bb-97a7-44c2932ef76b"
    code_revision = "e" * 40
    campaign_fingerprint = "c" * 64
    campaign_raw_sha256 = "d" * 64
    grant_raw_sha256 = "a" * 64
    grant_fingerprint = "b" * 64
    grant = SimpleNamespace(
        connector_key="nrc_adams_aps",
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        code_revision=code_revision,
        max_armings=1,
        supersedes_grant_sha256=None,
        grant_id="grant-nrc-phase-b-real-arming",
        arming_nonce=UUID("ba4613f4-d8e5-4bfd-9447-04d21dbf951b"),
        operator_mode="local_loopback",
        non_authorities=NRC_GRANT_NON_AUTHORITIES,
        target={
            "connector_key": "nrc_adams_aps",
            "accession_number": connectors_nrc_adams.NRC_FRESH_ACCESSION,
        },
        request_rules=expected_grant_rule_payloads("nrc_adams_aps"),
        max_physical_requests=2,
        max_run_bytes=70 * 1024 * 1024,
        max_single_send_detection_allowance_bytes=6_684_672,
        request_timeout_seconds=30,
        min_request_interval_ms=500,
        issued_at=now - timedelta(minutes=30),
        expires_at=now + timedelta(minutes=30),
    )
    campaign = SimpleNamespace(
        model=SimpleNamespace(
            campaign_id=campaign_id,
            code_revision=code_revision,
            not_before=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=1),
        ),
        raw_sha256=campaign_raw_sha256,
        canonical_fingerprint=campaign_fingerprint,
        introduction_index_revision=1,
        introduction_index_sha256="f" * 64,
    )
    verified_grant = SimpleNamespace(
        model=grant,
        raw_sha256=grant_raw_sha256,
        canonical_fingerprint=grant_fingerprint,
        verified_campaign=campaign,
        consumption_marker_path=tmp_path / f"{grant_raw_sha256}.json",
        consumption_marker_sha256="",
    )
    connector_run_id = connector_egress_arming.compute_parent_arming_id(
        connector_key=grant.connector_key,
        campaign_id=grant.campaign_id,
        grant_sha256=grant_raw_sha256,
        arming_nonce=grant.arming_nonce,
    )
    marker_bytes = connector_egress_arming._marker_bytes(
        verified_grant=verified_grant,
        connector_run_id=connector_run_id,
    )
    verified_grant.consumption_marker_sha256 = hashlib.sha256(
        marker_bytes
    ).hexdigest()
    run, created = connector_egress_arming.create_connector_egress_arming(
        db,
        payload=ConnectorEgressArmingIn(
            schema_id="project6.connector_egress_arming.v1",
            client_request_id="real-nrc-phase-b-identity",
            connector_key="nrc_adams_aps",
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
            grant_sha256=grant_raw_sha256,
        ),
        verified_grant=verified_grant,
        operator_receipt={
            "schema_id": "project6.connector_egress_authorization_receipt.v1",
            "connector_key": "nrc_adams_aps",
            "campaign_id": campaign_id,
            "campaign_fingerprint": campaign_fingerprint,
            "campaign_definition_sha256": campaign_raw_sha256,
            "grant_sha256": grant_raw_sha256,
            "canonical_grant_fingerprint": grant_fingerprint,
            "introduction_index_revision": 1,
            "introduction_index_sha256": "f" * 64,
            "operator_ref_hash": "1" * 64,
            "workspace_ref_hash": "2" * 64,
            "auth_owner_mode": "header_presence",
            "authorization_mode": "identity_presence",
            "role": None,
            "access": "write",
        },
        code_revision=code_revision,
    )
    assert created is True
    return run


@pytest.fixture()
def db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    session = factory()
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def expiring_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    session = factory()
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def file_dbs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Session, Session], None, None]:
    db_path = tmp_path / "phase-b-race.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
        connection.commit()
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    first = factory()
    second = factory()
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    try:
        yield first, second
    finally:
        first.close()
        second.close()
        engine.dispose()


def _strict_output() -> dict[str, Any]:
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
        "extractor_id": nrc_aps_document_processing.APS_PDF_EXTRACTOR_ID,
        "normalization_contract_id": (
            nrc_aps_document_processing.APS_TEXT_NORMALIZATION_CONTRACT_ID
        ),
        "document_class": "layout_complex_pdf",
        "page_count": 2,
        "quality_status": nrc_aps_document_processing.APS_QUALITY_STATUS_STRONG,
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


def _make_strict_state(
    db: Session,
    *,
    raw_bytes: bytes = b"%PDF-1.7\nstrict phase B fixture\n%%EOF",
    run_id: str = "strict-nrc-phase-b",
    target_id: str = "strict-nrc-phase-b-target",
    existing_run: ConnectorRun | None = None,
) -> tuple[ConnectorRun, ConnectorRunTarget, Path, str]:
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_root = Path(settings.connector_raw_dir)
    raw_path = raw_root / nrc_aps_artifact_ingestion.blob_relative_path(
        sha256=digest
    )
    persist_locked_raw_file(raw_root, raw_path, raw_bytes)
    completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing_run is None:
        envelope = {
            "schema_id": "project6.connector_egress_arming.v1",
            "arming_fingerprint": "a" * 64,
            "campaign_id": "27693345-6a47-45bb-97a7-44c2932ef76b",
            "campaign_fingerprint": "c" * 64,
            "campaign_definition_sha256": "d" * 64,
            "code_revision": "e" * 40,
            "campaign_introduction_index_revision": 1,
            "campaign_introduction_index_sha256": "b" * 64,
        }
        run = ConnectorRun(
            connector_run_id=run_id,
            submission_idempotency_key=f"egress-arm:{run_id}",
            request_config_json={"connector_egress_arming": envelope},
            request_fingerprint="a" * 64,
        )
    else:
        run = existing_run
        run_id = run.connector_run_id
        envelope = dict(run.request_config_json["connector_egress_arming"])
    run.connector_key = "nrc_adams_aps"
    run.source_system = "nrc_adams"
    run.source_mode = "strict_live_egress"
    run.status = "completed"
    run.completed_at = completed_at
    run.discovered_count = 1
    run.selected_count = 1
    run.downloaded_count = 1
    run.ingested_count = 0
    run.consumed_bytes = len(raw_bytes)
    run.failed_count = 0
    run.terminal_target_count = 1
    run.nonterminal_target_count = 0
    run.execution_lease_owner = None
    run.execution_lease_token = None
    run.execution_lease_expires_at = completed_at
    run.error_summary = None
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        stable_release_key="ML17123A319",
        stable_release_identifier="adams_accession:ML17123A319",
        identifiers_json=[
            {"type": "AccessionNumber", "value": "ML17123A319"}
        ],
        sciencebase_item_id=None,
        sciencebase_item_url=None,
        sciencebase_file_name="ML17123A319.pdf",
        sciencebase_download_uri=None,
        artifact_surface="files",
        selection_source="strict_exact_accession",
        selection_scope="dual_live_proof_v1",
        selection_match_basis="exact_accession",
        artifact_locator_type=connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS,
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
            "detail_response_sha256": "c" * 64,
            "artifact_url_sha256": "d" * 64,
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
            run_id,
            "egress_run_terminal",
        ),
        connector_run_id=run_id,
        connector_run_target_id=None,
        phase="execution",
        stage="terminal",
        event_type="egress_run_terminal",
        status_before="running",
        status_after="completed",
        reason_code="nrc_raw_admission_completed",
        error_class=None,
        message=None,
        metrics_json={
            "outcome_class": "nrc_raw_admission_completed",
            "arming_fingerprint": envelope["arming_fingerprint"],
            "campaign_introduction_index_revision": envelope[
                "campaign_introduction_index_revision"
            ],
            "campaign_introduction_index_sha256": envelope[
                "campaign_introduction_index_sha256"
            ],
        },
        created_at=completed_at,
    )
    db.add_all([run, target, terminal])
    db.commit()
    return run, target, raw_path, digest


def _make_seal_event(run: ConnectorRun) -> ConnectorRunEvent:
    envelope = run.request_config_json["connector_egress_arming"]
    created_at = datetime.now(timezone.utc)
    return ConnectorRunEvent(
        connector_run_event_id=connector_egress_arming._deterministic_id(
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


def _add_benign_run_events(
    db: Session,
    run: ConnectorRun,
    *,
    count: int,
) -> None:
    db.add_all(
        ConnectorRunEvent(
            connector_run_event_id=f"benign-phase-b-{index}",
            connector_run_id=run.connector_run_id,
            connector_run_target_id=None,
            phase="execution",
            stage="progress",
            event_type="progress",
            status_before="running",
            status_after="running",
            reason_code="progress",
            error_class=None,
            message=None,
            metrics_json={"ordinal": index},
            created_at=datetime.now(timezone.utc),
        )
        for index in range(count)
    )


def _install_parser(
    monkeypatch: pytest.MonkeyPatch,
    *,
    output: dict[str, Any] | None = None,
    callback: Any | None = None,
) -> list[dict[str, Any]]:
    phase_b = _phase_b()
    calls: list[dict[str, Any]] = []

    def parse(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        if callback is not None:
            return callback(**kwargs)
        return deepcopy(output or _strict_output())

    monkeypatch.setattr(
        phase_b.nrc_aps_strict_parse,
        "parse_admitted_blob_strict",
        parse,
    )
    return calls


def _install_second_commit_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    error: BaseException,
    commit_first: bool = False,
    before_raise: Any | None = None,
) -> Any:
    real_commit = db.commit
    commit_calls = 0

    def injected_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 2:
            if commit_first:
                real_commit()
            if before_raise is not None:
                before_raise()
            raise error
        real_commit()

    monkeypatch.setattr(db, "commit", injected_commit)
    return real_commit


def _apply_commit_ack_drift(
    db: Session,
    *,
    drift_surface: str,
    run_id: str,
    target_id: str,
) -> None:
    if drift_surface == "event":
        db.add(
            ConnectorRunEvent(
                connector_run_event_id="commit-ack-drift-event",
                connector_run_id=run_id,
                connector_run_target_id=target_id,
                phase="execution",
                stage="progress",
                event_type="progress",
                status_before="running",
                status_after="running",
                reason_code="progress",
                metrics_json={},
                created_at=datetime.now(timezone.utc),
            )
        )
    else:
        drift_updates: dict[
            str,
            tuple[type[Any], dict[Any, Any]],
        ] = {
            "run": (ConnectorRun, {"status": "failed"}),
            "target": (ConnectorRunTarget, {"status": "failed"}),
            "document": (ApsContentDocument, {"quality_status": "weak"}),
            "chunk": (ApsContentChunk, {"chunk_text": "tampered chunk"}),
            "linkage": (
                ApsContentLinkage,
                {"content_contract_id": "tampered-contract"},
            ),
        }
        model, values = drift_updates[drift_surface]
        query = db.query(model)
        if drift_surface == "run":
            query = query.filter(ConnectorRun.connector_run_id == run_id)
        elif drift_surface == "target":
            query = query.filter(
                ConnectorRunTarget.connector_run_target_id == target_id
            )
        query.update(values, synchronize_session=False)
    db.commit()


def _snapshot_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return value


def _row_snapshot(db: Session) -> str:
    documents = [
        {
            key: _snapshot_value(getattr(row, key))
            for key in (
                "aps_content_document_id",
                "content_id",
                "content_contract_id",
                "chunking_contract_id",
                "normalization_contract_id",
                "normalized_text_sha256",
                "normalized_char_count",
                "chunk_count",
                "content_status",
                "media_type",
                "document_class",
                "quality_status",
                "page_count",
                "diagnostics_ref",
                "visual_page_refs_json",
                "created_at",
                "updated_at",
            )
        }
        for row in db.query(ApsContentDocument).all()
    ]
    chunks = [
        {
            key: _snapshot_value(getattr(row, key))
            for key in (
                "aps_content_chunk_id",
                "content_id",
                "chunk_id",
                "chunk_ordinal",
                "start_char",
                "end_char",
                "chunk_text",
                "chunk_text_sha256",
                "page_start",
                "page_end",
                "unit_kind",
                "quality_status",
                "created_at",
                "updated_at",
            )
        }
        for row in db.query(ApsContentChunk).all()
    ]
    linkages = [
        {
            key: _snapshot_value(getattr(row, key))
            for key in (
                "aps_content_linkage_id",
                "content_id",
                "run_id",
                "target_id",
                "accession_number",
                "content_contract_id",
                "chunking_contract_id",
                "content_units_ref",
                "normalized_text_ref",
                "normalized_text_sha256",
                "blob_ref",
                "blob_sha256",
                "download_exchange_ref",
                "discovery_ref",
                "selection_ref",
                "diagnostics_ref",
                "created_at",
            )
        }
        for row in db.query(ApsContentLinkage).all()
    ]
    return repr((documents, chunks, linkages))


def _fresh_source_reference(
    db: Session,
    target_id: str,
) -> dict[str, Any]:
    value = (
        db.query(ConnectorRunTarget.source_reference_json)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .scalar()
    )
    assert isinstance(value, dict)
    return deepcopy(value)


def _marker_for(
    linkage: ApsContentLinkage,
    *,
    raw_size: int,
    status: str = _VERIFIED_CUSTODY,
    attempt_id: str = _ATTEMPT_ID,
) -> dict[str, Any]:
    return {
        "schema_id": _CUSTODY_SCHEMA,
        "status": status,
        "attempt_id": attempt_id,
        "connector_run_id": linkage.run_id,
        "connector_run_target_id": linkage.target_id,
        "aps_content_linkage_id": linkage.aps_content_linkage_id,
        "content_id": linkage.content_id,
        "blob_ref": linkage.blob_ref,
        "blob_sha256": linkage.blob_sha256,
        "blob_size_bytes": raw_size,
    }


def _install_origin_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        origin,
        "_validate_fresh_live_evidence",
        lambda *args, **kwargs: (
            {"campaign_id": "campaign"},
            {"accession_number": "ML17123A319"},
        ),
    )


def _make_verified_state(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    ConnectorRun,
    ConnectorRunTarget,
    ApsContentLinkage,
    Path,
    str,
    list[dict[str, Any]],
]:
    run, target, raw_path, digest = _make_strict_state(db)
    parser_calls = _install_parser(monkeypatch)
    linkage = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    parser_calls.clear()
    return run, target, linkage, raw_path, digest, parser_calls


def _verified_error_code(
    db: Session,
    *,
    target_id: str,
) -> str:
    outer = db.begin()
    try:
        with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
            _phase_b().verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target_id,
            )
        return str(excinfo.value.code)
    finally:
        outer.rollback()


def test_real_arming_completed_run_reaches_public_phase_b_linkage(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    armed = _create_real_nrc_arming(db, tmp_path)
    assert armed.source_system == "nrc_adams"
    run, target, _, _ = _make_strict_state(
        db,
        target_id="real-arming-phase-b-target",
        existing_run=armed,
    )
    parser_calls = _install_parser(monkeypatch)

    linkage = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert linkage.run_id == run.connector_run_id
    assert linkage.target_id == target.connector_run_target_id
    assert len(parser_calls) == 1


def test_verifier_accepts_seven_phase_events_plus_exact_campaign_seal(
    db: Session,
) -> None:
    phase_b = _phase_b()
    run, target, _, _ = _make_strict_state(db)
    _add_benign_run_events(db, run, count=6)
    db.add(_make_seal_event(run))
    db.commit()

    authority = phase_b._read_verifier_authority(
        db.connection(),
        target_id=target.connector_run_target_id,
        expected_run_id=run.connector_run_id,
    )
    verified_run, verified_target, _, _ = (
        phase_b._validate_verifier_authority(
            authority,
            target_id=target.connector_run_target_id,
        )
    )

    assert len(authority.events) == 8
    assert verified_run.connector_run_id == run.connector_run_id
    assert (
        verified_target.connector_run_target_id
        == target.connector_run_target_id
    )


def test_verifier_rejects_eighth_non_seal_event_with_exact_campaign_seal(
    db: Session,
) -> None:
    phase_b = _phase_b()
    run, target, _, _ = _make_strict_state(db)
    _add_benign_run_events(db, run, count=7)
    db.add(_make_seal_event(run))
    db.commit()

    authority = phase_b._read_verifier_authority(
        db.connection(),
        target_id=target.connector_run_target_id,
        expected_run_id=run.connector_run_id,
    )
    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b._validate_verifier_authority(
            authority,
            target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_run_invalid"


def test_verifier_contract_success_is_frozen_and_read_only(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _ = file_dbs
    phase_b = _phase_b()
    run, target, linkage, raw_path, digest, parser_calls = (
        _make_verified_state(db, monkeypatch)
    )
    signature = inspect.signature(phase_b.verify_strict_nrc_phase_b_linkage)
    assert list(signature.parameters) == ["db", "connector_run_target_id"]
    assert signature.parameters["connector_run_target_id"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert [item.name for item in fields(phase_b.NrcPhaseBVerifiedState)] == (
        [
            "connector_run_id",
            "connector_run_target_id",
            "aps_content_linkage_id",
            "content_id",
            "raw_storage_ref",
            "raw_content_sha256",
            "raw_content_size_bytes",
        ]
    )
    assert phase_b.NrcPhaseBVerifiedState.__dataclass_params__.frozen
    assert "__slots__" in vars(phase_b.NrcPhaseBVerifiedState)
    statements: list[str] = []

    def capture(*args: Any) -> None:
        statements.append(str(args[2]))

    engine = db.get_bind()
    outer = db.begin()
    sa_event.listen(engine, "before_cursor_execute", capture)
    try:
        state = phase_b.verify_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
        assert outer.is_active and db.in_transaction()
    finally:
        sa_event.remove(engine, "before_cursor_execute", capture)
        outer.rollback()
    assert tuple(getattr(state, item.name) for item in fields(state)) == (
        run.connector_run_id,
        target.connector_run_target_id,
        linkage.aps_content_linkage_id,
        linkage.content_id,
        str(raw_path),
        digest,
        raw_path.stat().st_size,
    )
    assert parser_calls == [{"blob_path": raw_path, "expected_sha256": digest}]
    assert statements and all(
        item.lstrip().upper().startswith("SELECT")
        and "FOR UPDATE" not in item.upper()
        for item in statements
    )
    with pytest.raises(FrozenInstanceError):
        setattr(state, "content_id", "mutated")


def test_explicit_settings_verifier_ignores_global_and_matches_legacy(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _ = file_dbs
    phase_b = _phase_b()
    _, target, _, _, _, parser_calls = _make_verified_state(db, monkeypatch)
    target_id = target.connector_run_target_id
    explicit_settings = settings.model_copy(deep=True)
    expected_root = Path(explicit_settings.connector_raw_dir).resolve()
    signature = inspect.signature(
        phase_b.verify_strict_nrc_phase_b_linkage_read_only
    )
    assert list(signature.parameters) == [
        "db",
        "connector_run_target_id",
        "settings",
    ]

    monkeypatch.setattr(
        phase_b,
        "settings",
        SimpleNamespace(connector_raw_dir=str(expected_root)),
    )
    outer = db.begin()
    try:
        legacy = phase_b.verify_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )
    finally:
        outer.rollback()
    parser_calls.clear()

    locked_roots: list[tuple[str, Path]] = []
    real_hash = phase_b.hash_locked_raw_file
    real_snapshot = phase_b.locked_raw_file_snapshot

    def record_initial(raw_root: Path, file_path: Path) -> Any:
        locked_roots.append(("initial", Path(raw_root).resolve()))
        return real_hash(raw_root, file_path)

    @contextmanager
    def record_final(
        raw_root: Path,
        file_path: Path,
    ) -> Generator[Any, None, None]:
        locked_roots.append(("final", Path(raw_root).resolve()))
        with real_snapshot(raw_root, file_path) as snapshot:
            yield snapshot

    class NoAccess:
        @property
        def connector_raw_dir(self) -> str:
            raise AssertionError("module-global settings accessed")

    monkeypatch.setattr(phase_b, "hash_locked_raw_file", record_initial)
    monkeypatch.setattr(
        phase_b,
        "locked_raw_file_snapshot",
        record_final,
    )
    monkeypatch.setattr(phase_b, "settings", NoAccess())

    outer = db.begin()
    try:
        explicit = phase_b.verify_strict_nrc_phase_b_linkage_read_only(
            db,
            target_id,
            explicit_settings,
        )
        assert outer.is_active and db.in_transaction()
    finally:
        outer.rollback()

    assert explicit == legacy
    assert parser_calls
    assert locked_roots == [
        ("initial", expected_root),
        ("final", expected_root),
    ]


def test_explicit_settings_verifier_preserves_caller_session(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _ = file_dbs
    phase_b = _phase_b()
    run, target, _, _, _, _ = _make_verified_state(db, monkeypatch)
    explicit_settings = settings.model_copy(deep=True)
    pending = ConnectorRunSubmission(
        connector_run_submission_id="explicit-verifier-pending",
        connector_key="other",
        submission_idempotency_key="explicit-verifier-pending",
        request_fingerprint="f" * 64,
        connector_run_id=run.connector_run_id,
    )
    db.add(pending)
    statements: list[str] = []

    def capture(*args: Any) -> None:
        statements.append(str(args[2]))

    def forbidden(method_name: str) -> Any:
        def fail(*_args: Any, **_kwargs: Any) -> None:
            pytest.fail(f"adapter called Session.{method_name}")

        return fail

    engine = db.get_bind()
    outer = db.get_transaction()
    assert outer is not None and outer.is_active
    sa_event.listen(engine, "before_cursor_execute", capture)
    try:
        with monkeypatch.context() as method_guard:
            for method_name in ("flush", "commit", "rollback"):
                method_guard.setattr(db, method_name, forbidden(method_name))
            phase_b.verify_strict_nrc_phase_b_linkage_read_only(
                db,
                target.connector_run_target_id,
                explicit_settings,
            )
            assert outer.is_active and db.in_transaction()
            assert pending in db.new and sa_inspect(pending).pending
    finally:
        sa_event.remove(engine, "before_cursor_execute", capture)
        outer.rollback()
    assert statements and all(
        item.lstrip().upper().startswith("SELECT")
        and "FOR UPDATE" not in item.upper()
        for item in statements
    )


def test_explicit_settings_verifier_requires_active_transaction(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _ = file_dbs
    phase_b = _phase_b()
    _, target, _, _, _, parser_calls = _make_verified_state(db, monkeypatch)

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.verify_strict_nrc_phase_b_linkage_read_only(
            db,
            target.connector_run_target_id,
            settings.model_copy(deep=True),
        )

    assert excinfo.value.code == "nrc_phase_b_caller_transaction_required"
    assert parser_calls == []
    assert not db.in_transaction()


def test_explicit_settings_verifier_preserves_root_and_drift_rejections(
    file_dbs: tuple[Session, Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _ = file_dbs
    phase_b = _phase_b()
    _, target, _, _, _, _ = _make_verified_state(db, monkeypatch)
    target_id = target.connector_run_target_id
    explicit_settings = settings.model_copy(deep=True)
    outside = tmp_path / "outside-explicit-phase-b.pdf"
    outside.write_bytes(b"%PDF-outside-explicit-phase-b")
    target.raw_storage_ref = str(outside.resolve())
    db.commit()

    outer = db.begin()
    try:
        with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
            phase_b.verify_strict_nrc_phase_b_linkage_read_only(
                db,
                target_id,
                explicit_settings,
            )
        assert excinfo.value.code == "nrc_phase_b_raw_path_invalid"
        assert outer.is_active and db.in_transaction()
    finally:
        outer.rollback()

    stored_target = db.get(ConnectorRunTarget, target_id)
    assert stored_target is not None
    expected_path = (
        Path(explicit_settings.connector_raw_dir)
        / nrc_aps_artifact_ingestion.blob_relative_path(
            sha256=str(stored_target.downloaded_sha256)
        )
    ).resolve()
    stored_target.raw_storage_ref = str(expected_path)
    db.commit()
    real_snapshot = phase_b.locked_raw_file_snapshot

    @contextmanager
    def drift_after_snapshot(
        raw_root: Path,
        file_path: Path,
    ) -> Generator[Any, None, None]:
        with real_snapshot(raw_root, file_path) as snapshot:
            yield snapshot
            raise raw_handles.StableRawStorageError("explicit drift")

    monkeypatch.setattr(
        phase_b,
        "locked_raw_file_snapshot",
        drift_after_snapshot,
    )
    outer = db.begin()
    try:
        with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
            phase_b.verify_strict_nrc_phase_b_linkage_read_only(
                db,
                target_id,
                explicit_settings,
            )
        assert excinfo.value.code == "nrc_phase_b_raw_drift"
        assert outer.is_active and db.in_transaction()
    finally:
        outer.rollback()


@pytest.mark.parametrize(
    "mode",
    ["missing_tx", "outer", "nested", "unrelated", "new", "dirty", "deleted"],
)
def test_verifier_transaction_and_identity_map_contract(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    db, _ = file_dbs
    run, target, linkage, _, _, parser_calls = _make_verified_state(
        db,
        monkeypatch,
    )
    if mode == "missing_tx":
        with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
            _phase_b().verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target.connector_run_target_id,
            )
        assert excinfo.value.code == "nrc_phase_b_caller_transaction_required"
        assert parser_calls == []
        return
    outer = db.begin()
    nested = db.begin_nested() if mode == "nested" else None
    unrelated = None
    if mode == "unrelated":
        unrelated = ConnectorRunSubmission(
            connector_run_submission_id="pending-unrelated",
            connector_key="other",
            submission_idempotency_key="pending-unrelated",
            request_fingerprint="f" * 64,
            connector_run_id=run.connector_run_id,
        )
        db.add(unrelated)
    elif mode == "new":
        db.add(ApsContentChunk(chunk_text_sha256="0" * 64))
    elif mode == "dirty":
        target.status = "failed"
    elif mode == "deleted":
        db.delete(linkage)
    try:
        if mode in {"new", "dirty", "deleted"}:
            with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
                _phase_b().verify_strict_nrc_phase_b_linkage(
                    db,
                    connector_run_target_id=target.connector_run_target_id,
                )
            assert excinfo.value.code == "nrc_phase_b_identity_map_dirty"
            assert parser_calls == []
            if mode == "dirty":
                history = sa_inspect(target).attrs.status.history
                assert history.added == ["failed"]
                assert history.deleted == ["downloaded"]
        else:
            _phase_b().verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target.connector_run_target_id,
            )
            assert outer.is_active and db.in_transaction()
            assert db.in_nested_transaction() is (nested is not None)
            if unrelated is not None:
                assert unrelated in db.new and sa_inspect(unrelated).pending
    finally:
        if nested is not None and nested.is_active:
            nested.rollback()
        outer.rollback()


@pytest.mark.parametrize(
    ("surface", "expected_code"),
    [
        ("linkage_missing", "nrc_phase_b_linkage_cardinality"),
        ("linkage_extra", "nrc_phase_b_linkage_cardinality"),
        ("linkage_forbidden", "nrc_phase_b_linkage_mismatch"),
        ("linkage_cross_run", "nrc_phase_b_linkage_mismatch"),
        ("document_tamper", "nrc_phase_b_linkage_mismatch"),
        ("chunk_tamper", "nrc_phase_b_linkage_mismatch"),
        ("custody_absent", "nrc_phase_b_custody_ineligible"),
        ("custody_pending", "nrc_phase_b_custody_ineligible"),
        ("custody_contradictory", "nrc_phase_b_custody_ineligible"),
    ],
)
def test_verifier_rejects_projection_and_custody_mutations(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
    expected_code: str,
) -> None:
    db, _ = file_dbs
    run, target, _, _, _, _ = _make_verified_state(db, monkeypatch)
    linkage = db.query(ApsContentLinkage).one()
    document = db.query(ApsContentDocument).one()
    chunk = db.query(ApsContentChunk).first()
    assert chunk is not None
    if surface == "linkage_missing":
        db.delete(linkage)
    elif surface == "linkage_extra":
        db.add(
            ApsContentLinkage(
                content_id="extra",
                run_id=run.connector_run_id,
                target_id=target.connector_run_target_id,
                content_contract_id="extra",
                chunking_contract_id="extra",
            )
        )
    elif surface == "linkage_forbidden":
        linkage.diagnostics_ref = "forbidden"
    elif surface == "linkage_cross_run":
        linkage.run_id = "cross-run"
    elif surface == "document_tamper":
        document.normalized_char_count += 1
    elif surface == "chunk_tamper":
        chunk.chunk_text = "tampered"
    else:
        source = _fresh_source_reference(
            db,
            target.connector_run_target_id,
        )
        marker = deepcopy(source.get(_CUSTODY_KEY))
        assert isinstance(marker, dict)
        if surface == "custody_absent":
            source.pop(_CUSTODY_KEY)
        elif surface == "custody_pending":
            marker["status"] = _PENDING_CUSTODY
            source[_CUSTODY_KEY] = marker
        else:
            marker["content_id"] = "contradictory"
            source[_CUSTODY_KEY] = marker
        target.source_reference_json = source
    db.commit()
    assert (
        _verified_error_code(
            db,
            target_id=target.connector_run_target_id,
        )
        == expected_code
    )


@pytest.mark.parametrize(
    ("surface", "expected_code"),
    [
        ("raw_initial", "nrc_phase_b_raw_storage_unsafe"),
        ("raw_exit", "nrc_phase_b_raw_drift"),
    ],
)
def test_verifier_translates_raw_failures(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
    expected_code: str,
) -> None:
    db, _ = file_dbs
    _, target, _, _, _, _ = _make_verified_state(db, monkeypatch)
    phase_b = _phase_b()
    if surface == "raw_initial":
        def fail_rehash(*_args: Any, **_kwargs: Any) -> Any:
            raise raw_handles.StableRawStorageError("missing")

        monkeypatch.setattr(phase_b, "hash_locked_raw_file", fail_rehash)
    else:
        db.rollback()
        real_snapshot = phase_b.locked_raw_file_snapshot

        @contextmanager
        def changed_raw(
            raw_root: Path,
            file_path: Path,
        ) -> Generator[Any, None, None]:
            with real_snapshot(raw_root, file_path) as snapshot:
                yield snapshot
                raise raw_handles.StableRawStorageError("changed")

        monkeypatch.setattr(
            phase_b,
            "locked_raw_file_snapshot",
            changed_raw,
        )
    assert (
        _verified_error_code(
            db,
            target_id=target.connector_run_target_id,
        )
        == expected_code
    )


def test_verifier_refuses_shared_memory_pool_before_checkout(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _, _, parser_calls = _make_verified_state(db, monkeypatch)
    engine = db.get_bind()
    real_connect = engine.connect
    checkouts: list[None] = []

    def record_checkout() -> Any:
        checkouts.append(None)
        return real_connect()

    monkeypatch.setattr(engine, "connect", record_checkout)
    outer = db.begin()
    try:
        with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
            _phase_b().verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target.connector_run_target_id,
            )
        assert excinfo.value.code == (
            "nrc_phase_b_committed_visibility_unavailable"
        )
        assert checkouts == []
        assert parser_calls == []
        assert outer.is_active and db.in_transaction()
    finally:
        outer.rollback()


@pytest.mark.parametrize(
    "promotion",
    ["flushed_orm", "direct_core", "nested_rollback"],
)
def test_verifier_rejects_provisional_custody_promotion(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    promotion: str,
) -> None:
    db, observer = file_dbs
    run, target, _, _, _, _ = _make_verified_state(db, monkeypatch)
    target_id = target.connector_run_target_id
    pending_source = _fresh_source_reference(db, target_id)
    pending_marker = deepcopy(pending_source[_CUSTODY_KEY])
    pending_marker["status"] = _PENDING_CUSTODY
    pending_source[_CUSTODY_KEY] = pending_marker
    target.source_reference_json = pending_source
    db.commit()
    verified_source = deepcopy(pending_source)
    verified_marker = deepcopy(verified_source[_CUSTODY_KEY])
    verified_marker["status"] = _VERIFIED_CUSTODY
    verified_source[_CUSTODY_KEY] = verified_marker

    outer = db.begin()
    nested = db.begin_nested() if promotion == "nested_rollback" else None
    if promotion == "flushed_orm":
        target.source_reference_json = verified_source
        db.flush()
        assert target not in db.dirty
    else:
        db.connection().execute(
            update(ConnectorRunTarget)
            .where(
                ConnectorRunTarget.connector_run_target_id == target_id
            )
            .values(source_reference_json=verified_source)
        )
    unrelated = ConnectorRunSubmission(
        connector_run_submission_id=f"pending-{promotion}",
        connector_key="other",
        submission_idempotency_key=f"pending-{promotion}",
        request_fingerprint="f" * 64,
        connector_run_id=run.connector_run_id,
    )
    db.add(unrelated)
    try:
        with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
            _phase_b().verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target_id,
            )
        assert excinfo.value.code == "nrc_phase_b_custody_ineligible"
        assert outer.is_active and db.in_transaction()
        assert db.in_nested_transaction() is (nested is not None)
        assert unrelated in db.new and sa_inspect(unrelated).pending
        committed_source = _fresh_source_reference(observer, target_id)
        assert (
            committed_source[_CUSTODY_KEY]["status"] == _PENDING_CUSTODY
        )
        if nested is not None:
            nested.rollback()
            rolled_back_source = db.connection().execute(
                select(ConnectorRunTarget.source_reference_json).where(
                    ConnectorRunTarget.connector_run_target_id == target_id
                )
            ).scalar_one()
            assert (
                rolled_back_source[_CUSTODY_KEY]["status"]
                == _PENDING_CUSTODY
            )
    finally:
        observer.rollback()
        if nested is not None and nested.is_active:
            nested.rollback()
        outer.rollback()


@pytest.mark.parametrize(
    "failure",
    ["checkout", "isolation", "isolation_error", "read"],
)
def test_verifier_fails_closed_when_committed_visibility_fails(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    db, _ = file_dbs
    _, target, _, _, _, _ = _make_verified_state(db, monkeypatch)
    engine = db.get_bind()
    remove_listener = False
    read_listener: Any = None
    if failure == "checkout":
        def fail_checkout() -> Any:
            raise OperationalError(
                "independent checkout",
                {},
                RuntimeError("unavailable"),
            )

        monkeypatch.setattr(engine, "connect", fail_checkout)
    elif failure == "isolation":
        monkeypatch.setattr(
            engine.dialect,
            "get_isolation_level",
            lambda _connection: "READ-UNCOMMITTED",
        )
    elif failure == "isolation_error":
        def fail_isolation(_connection: Any) -> str:
            raise RuntimeError("unavailable")

        monkeypatch.setattr(
            engine.dialect,
            "get_isolation_level",
            fail_isolation,
        )
    else:
        def fail_read(*_args: Any) -> None:
            raise OperationalError(
                "independent read",
                {},
                RuntimeError("unavailable"),
            )

        read_listener = fail_read
        sa_event.listen(engine, "before_cursor_execute", read_listener)
        remove_listener = True

    outer = db.begin()
    try:
        with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
            _phase_b().verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target.connector_run_target_id,
            )
        assert excinfo.value.code == (
            "nrc_phase_b_committed_visibility_unavailable"
        )
        assert outer.is_active and db.in_transaction()
    finally:
        if remove_listener:
            sa_event.remove(engine, "before_cursor_execute", read_listener)
        outer.rollback()


def test_public_boundary_accepts_only_db_and_target_id() -> None:
    signature = inspect.signature(
        _phase_b().bind_strict_nrc_phase_b_linkage
    )
    assert list(signature.parameters) == [
        "db",
        "connector_run_target_id",
    ]
    assert signature.parameters["connector_run_target_id"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )


@pytest.mark.parametrize(
    "transaction_state",
    ["pending", "flushed", "active_read"],
)
def test_entry_refuses_caller_owned_transaction_state(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    transaction_state: str,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    unrelated = ApsContentDocument(
        content_id=f"{transaction_state}-caller-row",
        content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        normalized_char_count=0,
        chunk_count=0,
        content_status="indexed",
    )
    if transaction_state in {"pending", "flushed"}:
        db.add(unrelated)
    if transaction_state == "flushed":
        db.flush()
    elif transaction_state == "active_read":
        assert db.query(ConnectorRun).count() == 1

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_transaction_not_owned"
    assert db.in_transaction()


def test_entry_refuses_active_nested_transaction_before_owned_rollback(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    nested = db.begin_nested()

    with pytest.raises(_phase_b().NrcPhaseBLinkageError) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_transaction_not_owned"
    assert db.in_transaction()
    assert db.in_nested_transaction()
    assert nested.is_active
    nested.rollback()
    db.rollback()


@pytest.mark.parametrize(
    "failure_type",
    [RuntimeError, KeyboardInterrupt],
    ids=["runtime-error", "keyboard-interrupt"],
)
def test_sqlite_outer_transaction_rolls_back_real_immutable_insert(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[BaseException],
) -> None:
    db, observer = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_insert = (
        phase_b.nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    insert_returned = False

    def tracked_insert(*args: Any, **kwargs: Any) -> Any:
        nonlocal insert_returned
        result = real_insert(*args, **kwargs)
        insert_returned = True
        return result

    def fail_before_commit() -> None:
        raise failure_type("injected precommit failure")

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        tracked_insert,
    )
    monkeypatch.setattr(db, "commit", fail_before_commit)

    with pytest.raises(failure_type):
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert insert_returned
    assert not db.in_transaction()
    observer.expire_all()
    assert observer.query(ApsContentDocument).count() == 0
    assert observer.query(ApsContentChunk).count() == 0
    assert observer.query(ApsContentLinkage).count() == 0


def test_unrelated_sqlite_writer_can_commit_during_strict_parse(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    competing.connection().exec_driver_sql("PRAGMA busy_timeout=100")
    competing.commit()
    outcomes: list[str] = []

    def parse_with_unrelated_write(**kwargs: Any) -> dict[str, Any]:
        competing.add(
            ApsContentDocument(
                content_id="unrelated-parse-writer",
                content_contract_id="unrelated",
                chunking_contract_id="unrelated",
                normalized_char_count=0,
                chunk_count=0,
                content_status="indexed",
            )
        )
        competing.commit()
        outcomes.append("committed")
        return _strict_output()

    _install_parser(monkeypatch, callback=parse_with_unrelated_write)

    _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert outcomes == ["committed"]


def test_retained_terminal_event_drift_is_freshly_rejected(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    run, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    retained = (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.connector_run_id == run.connector_run_id)
        .one()
    )
    assert retained.status_after == "completed"
    db.commit()
    competing.query(ConnectorRunEvent).filter(
        ConnectorRunEvent.connector_run_event_id
        == retained.connector_run_event_id
    ).update({"status_after": "failed"}, synchronize_session=False)
    competing.commit()
    _install_parser(monkeypatch)

    with pytest.raises(_phase_b().NrcPhaseBLinkageError):
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert db.query(ApsContentLinkage).count() == 0


def test_default_expiring_session_returns_loaded_detached_linkage(
    expiring_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(expiring_db)
    target_id = target.connector_run_target_id
    expiring_db.rollback()
    assert expiring_db.expire_on_commit is True
    _install_parser(monkeypatch)

    first = _phase_b().bind_strict_nrc_phase_b_linkage(
        expiring_db,
        connector_run_target_id=target_id,
    )
    first_id = first.aps_content_linkage_id

    assert sa_inspect(first).detached
    assert not sa_inspect(first).expired_attributes
    assert expiring_db.expire_on_commit is True
    assert not expiring_db.in_transaction()
    assert {
        column.name: getattr(first, column.name)
        for column in ApsContentLinkage.__table__.columns
    }["target_id"] == target_id
    assert not expiring_db.in_transaction()

    second = _phase_b().bind_strict_nrc_phase_b_linkage(
        expiring_db,
        connector_run_target_id=target_id,
    )

    assert sa_inspect(second).detached
    assert not sa_inspect(second).expired_attributes
    assert expiring_db.expire_on_commit is True
    assert second.aps_content_linkage_id == first_id
    assert not expiring_db.in_transaction()


def test_exact_replay_allows_canonical_origin_receipt_without_using_it(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    first = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )
    first_id = first.aps_content_linkage_id
    first_source = _fresh_source_reference(db, target_id)
    first_marker = first_source[_CUSTODY_KEY]
    assert first_marker["status"] == _VERIFIED_CUSTODY
    db.rollback()

    stored_target = db.get(ConnectorRunTarget, target_id)
    assert stored_target is not None
    admission = dict(stored_target.source_reference_json)
    admission["connector_origin_receipt_v1"] = {
        "schema_id": origin.ORIGIN_RECEIPT_SCHEMA_ID,
        "connector_key": "nrc_adams_aps",
        "connector_run_id": run_id,
        "connector_run_target_id": target_id,
        "receipt_hash": "e" * 64,
        "ignored_non_authority_field": "receipt payload stays opaque",
    }
    stored_target.source_reference_json = admission
    db.commit()
    expected_source = deepcopy(admission)

    second = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert not db.in_transaction()
    assert second.aps_content_linkage_id == first_id
    replay_source = _fresh_source_reference(db, target_id)
    assert replay_source == expected_source
    assert replay_source[_CUSTODY_KEY] == first_marker
    assert db.query(ApsContentLinkage).count() == 1
    assert db.query(ApsContentDocument).count() == 1


def test_receipt_without_exact_existing_linkage_fails_before_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    admission = dict(target.source_reference_json)
    admission["connector_origin_receipt_v1"] = {
        "schema_id": origin.ORIGIN_RECEIPT_SCHEMA_ID,
        "connector_key": run.connector_key,
        "connector_run_id": run.connector_run_id,
        "connector_run_target_id": target_id,
        "receipt_hash": "e" * 64,
        "opaque_receipt_field": "not Phase-B authority",
    }
    target.source_reference_json = admission
    db.commit()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_insert = (
        phase_b.nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    mutation_calls = 0

    def record_mutation(*args: Any, **kwargs: Any) -> Any:
        nonlocal mutation_calls
        mutation_calls += 1
        return real_insert(*args, **kwargs)

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        record_mutation,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_receipt_without_linkage"
    assert mutation_calls == 0
    assert db.query(ApsContentDocument).count() == 0
    assert db.query(ApsContentChunk).count() == 0
    assert db.query(ApsContentLinkage).count() == 0


@pytest.mark.parametrize(
    "receipt",
    [
        None,
        {
            "schema_id": origin.ORIGIN_RECEIPT_SCHEMA_ID,
            "connector_key": "nrc_adams_aps",
            "connector_run_id": "wrong-run",
            "connector_run_target_id": "strict-nrc-phase-b-target",
            "receipt_hash": "e" * 64,
        },
        {
            "schema_id": origin.ORIGIN_RECEIPT_SCHEMA_ID,
            "connector_key": "nrc_adams_aps",
            "connector_run_id": "strict-nrc-phase-b",
            "connector_run_target_id": "strict-nrc-phase-b-target",
            "receipt_hash": "E" * 64,
        },
        {
            "schema_id": origin.ORIGIN_RECEIPT_SCHEMA_ID,
            "connector_key": "nrc_adams_aps",
            "connector_run_id": "strict-nrc-phase-b",
            "connector_run_target_id": "strict-nrc-phase-b-target",
            "receipt_hash": "e" * 64,
            "forbidden_url": "https://example.invalid/receipt",
        },
    ],
    ids=["null", "wrong-run", "uppercase-hash", "url-bearing"],
)
def test_malformed_origin_receipt_envelope_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    admission = dict(target.source_reference_json)
    admission["connector_origin_receipt_v1"] = receipt
    target.source_reference_json = admission
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_admission_invalid"
    assert calls == []


def test_completed_strict_target_creates_canonical_linkage(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    admission_before = deepcopy(target.source_reference_json)
    calls = _install_parser(monkeypatch)
    assert db.query(ApsContentLinkage).count() == 0
    db.rollback()

    linkage = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert calls == [
        {"blob_path": raw_path, "expected_sha256": digest}
    ]
    assert db.query(ApsContentDocument).count() == 1
    assert db.query(ApsContentChunk).count() == 1
    assert db.query(ApsContentLinkage).count() == 1
    assert linkage.run_id == run.connector_run_id
    assert linkage.target_id == target.connector_run_target_id
    assert linkage.accession_number == "ML17123A319"
    assert linkage.blob_ref == str(raw_path)
    assert linkage.blob_sha256 == digest
    assert linkage.content_id != digest
    assert linkage.content_contract_id == (
        nrc_aps_content_index.APS_CONTENT_CONTRACT_ID
    )
    assert linkage.chunking_contract_id == (
        nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID
    )
    assert linkage.download_exchange_ref is None
    assert linkage.discovery_ref is None
    assert linkage.selection_ref is None
    source_reference = _fresh_source_reference(db, target_id)
    marker = source_reference.pop(_CUSTODY_KEY)
    assert source_reference == admission_before
    assert str(UUID(marker["attempt_id"])) == marker["attempt_id"]
    assert marker == _marker_for(
        linkage,
        raw_size=raw_path.stat().st_size,
        attempt_id=marker["attempt_id"],
    )
    db.rollback()
    db.refresh(run)
    db.refresh(target)
    assert run.ingested_count == 0
    assert target.status == "downloaded"


def test_exact_rerun_returns_same_row_without_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    _install_parser(monkeypatch)
    first = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )
    before = _row_snapshot(db)
    db.rollback()

    second = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert second.aps_content_linkage_id == first.aps_content_linkage_id
    assert _row_snapshot(db) == before


@pytest.mark.parametrize(
    ("surface", "field", "value"),
    [
        ("linkage", "content_contract_id", "tampered-contract"),
        ("document", "quality_status", "weak"),
        ("chunk", "chunk_text", "tampered chunk"),
    ],
)
def test_retained_projection_drift_is_freshly_rejected(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
    field: str,
    value: str,
) -> None:
    db, competing = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )
    retained = {
        "linkage": db.query(ApsContentLinkage).one(),
        "document": db.query(ApsContentDocument).one(),
        "chunk": db.query(ApsContentChunk).first(),
    }
    assert retained["chunk"] is not None
    db.commit()
    model = {
        "linkage": ApsContentLinkage,
        "document": ApsContentDocument,
        "chunk": ApsContentChunk,
    }[surface]
    competing.query(model).update(
        {field: value},
        synchronize_session=False,
    )
    competing.commit()

    with pytest.raises(_phase_b().NrcPhaseBLinkageError):
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    competing.expire_all()
    assert getattr(competing.query(model).first(), field) == value


def test_created_linkage_satisfies_existing_receipt_derivation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    verification_calls: list[str] = []

    def verify_fresh_binding(
        verify_db: Session,
        *,
        connector_run_target_id: str,
    ) -> Any:
        # StaticPool memory DB cannot expose an independent committed reader.
        # This test isolates the origin bridge; verifier tests cover visibility.
        assert verify_db is db
        verification_calls.append(connector_run_target_id)
        return phase_b.NrcPhaseBVerifiedState(
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            aps_content_linkage_id=linkage.aps_content_linkage_id,
            content_id=linkage.content_id,
            raw_storage_ref=str(raw_path.resolve()),
            raw_content_sha256=digest,
            raw_content_size_bytes=raw_path.stat().st_size,
        )

    monkeypatch.setattr(
        phase_b,
        "verify_strict_nrc_phase_b_linkage",
        verify_fresh_binding,
    )
    monkeypatch.setattr(
        origin,
        "_validate_fresh_live_evidence",
        lambda *args, **kwargs: (
            {"campaign_id": "campaign"},
            {"accession_number": "ML17123A319"},
        ),
    )

    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert receipt["connector_run_id"] == run.connector_run_id
    assert receipt["aps_content_linkage_id"] == (
        linkage.aps_content_linkage_id
    )
    assert receipt["content_id"] == linkage.content_id
    assert verification_calls == [target.connector_run_target_id]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("connector_key", "sciencebase_mcs"),
        ("source_system", "not_nrc"),
        ("source_mode", "public_api"),
        ("status", "running"),
    ],
)
def test_wrong_or_incomplete_run_fails_before_parse(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    setattr(run, field, value)
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_run_invalid"
    assert calls == []
    assert db.query(ApsContentLinkage).count() == 0


def test_missing_target_fails_closed(db: Session) -> None:
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id="missing",
        )
    assert excinfo.value.code == "nrc_phase_b_target_not_found"


def test_noncanonical_target_cardinality_fails_before_parse(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    db.add(
        ConnectorRunTarget(
            connector_run_target_id="extra-target",
            connector_run_id=run.connector_run_id,
            ordinal=2,
            artifact_surface="files",
            status="downloaded",
        )
    )
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_target_cardinality"
    assert calls == []


def _replace_admission(
    target: ConnectorRunTarget,
    key: str,
    value: object,
) -> None:
    admission = dict(target.source_reference_json)
    admission[key] = value
    target.source_reference_json = admission


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (
            lambda target: setattr(target, "ordinal", 2),
            "nrc_phase_b_target_invalid",
        ),
        (
            lambda target: setattr(target, "status", "ingested"),
            "nrc_phase_b_target_invalid",
        ),
        (
            lambda target: setattr(
                target,
                "stable_release_key",
                "ML00000A000",
            ),
            "nrc_phase_b_target_invalid",
        ),
        (
            lambda target: setattr(
                target,
                "sciencebase_download_uri",
                "https://www.nrc.gov/forbidden.pdf",
            ),
            "nrc_phase_b_url_authority_refused",
        ),
        (
            lambda target: setattr(target, "source_reference_json", {}),
            "nrc_phase_b_admission_invalid",
        ),
        (
            lambda target: _replace_admission(
                target,
                "media_type",
                "text/plain",
            ),
            "nrc_phase_b_admission_invalid",
        ),
        (
            lambda target: _replace_admission(
                target,
                "raw_content_size_bytes",
                1,
            ),
            "nrc_phase_b_admission_invalid",
        ),
        (
            lambda target: _replace_admission(
                target,
                "raw_content_sha256",
                "0" * 64,
            ),
            "nrc_phase_b_admission_invalid",
        ),
    ],
)
def test_target_and_admission_mismatches_fail_before_parse(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
    expected_code: str,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    mutation(target)
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == expected_code
    assert calls == []


def test_outside_root_and_wrong_content_address_path_fail_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"%PDF-outside")
    target.raw_storage_ref = str(outside)
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as outside_error:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert outside_error.value.code == "nrc_phase_b_raw_path_invalid"
    assert calls == []

    _, target, _, digest = _make_strict_state(
        db,
        run_id="second-run",
        target_id="second-target",
    )
    raw_root = Path(settings.connector_raw_dir)
    wrong_path = raw_root / "nrc_adams_aps" / "blobs" / f"{digest}.bin"
    persist_locked_raw_file(
        raw_root,
        wrong_path,
        b"%PDF-1.7\nstrict phase B fixture\n%%EOF",
    )
    target.raw_storage_ref = str(wrong_path)
    db.commit()

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as shape_error:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert shape_error.value.code == "nrc_phase_b_raw_path_invalid"
    assert calls == []


def test_equivalent_but_noncanonical_raw_ref_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, raw_path, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    target.raw_storage_ref = str(
        raw_path.parent
        / ".."
        / raw_path.parent.name
        / raw_path.name
    )
    assert Path(target.raw_storage_ref).resolve() == raw_path.resolve()
    assert target.raw_storage_ref != str(raw_path.resolve())
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_raw_path_invalid"
    assert calls == []


def test_safe_handle_rejection_maps_to_raw_storage_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    phase_b = _phase_b()
    calls = _install_parser(monkeypatch)

    def reject(*args: Any, **kwargs: Any) -> Any:
        raise phase_b.StableRawStorageError("unsafe")

    monkeypatch.setattr(phase_b, "hash_locked_raw_file", reject)
    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_raw_storage_unsafe"
    assert calls == []


def test_post_parse_blob_drift_fails_before_db_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, raw_path, _ = _make_strict_state(db)

    def drift(**kwargs: Any) -> dict[str, Any]:
        raw_path.write_bytes(b"%PDF-drifted")
        return _strict_output()

    _install_parser(monkeypatch, callback=drift)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_raw_drift"
    assert db.query(ApsContentLinkage).count() == 0


def test_final_raw_snapshot_encloses_flush_requery_and_commit(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    timeline: list[str] = []
    real_snapshot = phase_b.locked_raw_file_snapshot
    real_insert = (
        phase_b.nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    real_commit = db.commit

    @contextmanager
    def tracked_snapshot(*args: Any, **kwargs: Any) -> Generator[Any, None, None]:
        timeline.append("lock-enter")
        with real_snapshot(*args, **kwargs) as snapshot:
            yield snapshot
        timeline.append("lock-exit")

    def tracked_insert(*args: Any, **kwargs: Any) -> Any:
        assert timeline[-1] == "lock-enter"
        timeline.append("immutable-insert")
        return real_insert(*args, **kwargs)

    def tracked_commit() -> None:
        assert "lock-enter" in timeline
        if "commit" not in timeline:
            assert "lock-exit" not in timeline
        else:
            assert timeline[-1] == "lock-exit"
        timeline.append("commit")
        real_commit()

    monkeypatch.setattr(
        phase_b,
        "locked_raw_file_snapshot",
        tracked_snapshot,
    )
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        tracked_insert,
    )
    monkeypatch.setattr(db, "commit", tracked_commit)

    phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert timeline == [
        "lock-enter",
        "immutable-insert",
        "commit",
        "lock-exit",
        "commit",
    ]


@pytest.mark.parametrize(
    ("failure_timing", "expected_code", "expected_rows"),
    [
        ("precommit", "nrc_phase_b_raw_drift", 0),
        ("postcommit", "nrc_phase_b_postcommit_raw_drift", 1),
    ],
)
def test_custody_failure_code_distinguishes_commit_state(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    failure_timing: str,
    expected_code: str,
    expected_rows: int,
) -> None:
    _, target, raw_path, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    raw_size = raw_path.stat().st_size
    db.rollback()
    _install_parser(monkeypatch)
    _install_origin_stub(monkeypatch)
    phase_b = _phase_b()

    @contextmanager
    def injected_snapshot(
        *args: Any,
        **kwargs: Any,
    ) -> Generator[raw_handles.LockedRawFileSnapshot, None, None]:
        if failure_timing == "precommit":
            raise raw_handles.StableRawStorageError("changed")
        yield raw_handles.LockedRawFileSnapshot(
            canonical_ref=str(raw_path.resolve(strict=True)),
            size=raw_size,
            sha256=digest,
        )
        raise raw_handles.StableRawStorageError("changed")

    monkeypatch.setattr(
        phase_b,
        "locked_raw_file_snapshot",
        injected_snapshot,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == expected_code
    if failure_timing == "postcommit":
        assert excinfo.value.message == (
            "Postcommit raw drift preserves exact rows but grants no "
            "receipt, retry, or repair authority."
        )
    assert db.query(ApsContentDocument).count() == expected_rows
    assert db.query(ApsContentChunk).count() == expected_rows
    assert db.query(ApsContentLinkage).count() == expected_rows
    source_reference = _fresh_source_reference(db, target_id)
    if failure_timing == "precommit":
        assert _CUSTODY_KEY not in source_reference
    else:
        assert source_reference[_CUSTODY_KEY]["status"] == _PENDING_CUSTODY
        db.rollback()
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as origin_error:
            origin.derive_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )
        assert (
            origin_error.value.code
            == "layer3_origin_nrc_custody_ineligible"
        )


def test_real_platform_postcommit_custody_outcome_is_fail_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, raw_path, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    _install_origin_stub(monkeypatch)
    phase_b = _phase_b()
    real_commit = db.commit
    replacement_outcomes: list[str] = []
    commit_calls = 0
    raw_bytes = raw_path.read_bytes()

    def commit_then_replace() -> None:
        nonlocal commit_calls
        real_commit()
        commit_calls += 1
        if commit_calls != 1:
            return
        replacement = raw_path.with_suffix(".swap")
        try:
            replacement.write_bytes(raw_bytes)
            os.replace(replacement, raw_path)
        except OSError:
            replacement_outcomes.append("denied")
        else:
            replacement_outcomes.append("replaced")

    monkeypatch.setattr(db, "commit", commit_then_replace)

    if raw_handles._windows_backend_available():
        linkage = phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )
        assert replacement_outcomes == ["denied"]
        assert linkage.blob_sha256 == digest
    else:
        with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
            phase_b.bind_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target_id,
        )
        assert excinfo.value.code == "nrc_phase_b_postcommit_raw_drift"
        assert replacement_outcomes == ["replaced"]

    assert db.query(ApsContentDocument).count() == 1
    assert db.query(ApsContentChunk).count() == 1
    assert db.query(ApsContentLinkage).count() == 1
    preserved_linkage = db.query(ApsContentLinkage).one()
    assert preserved_linkage.target_id == target_id
    assert preserved_linkage.blob_sha256 == digest
    source_reference = _fresh_source_reference(db, target_id)
    assert origin.ORIGIN_RECEIPT_STORAGE_KEY not in (
        source_reference
    )
    expected_status = (
        _VERIFIED_CUSTODY
        if raw_handles._windows_backend_available()
        else _PENDING_CUSTODY
    )
    assert source_reference[_CUSTODY_KEY]["status"] == expected_status

    if not raw_handles._windows_backend_available():
        db.rollback()
        with pytest.raises(
            origin.Layer3OriginContinuityError
        ) as origin_error:
            origin.derive_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )
        assert (
            origin_error.value.code
            == "layer3_origin_nrc_custody_ineligible"
        )


@pytest.mark.parametrize("ack_mode", ["raise-before", "commit-then-raise"])
def test_phase_two_commit_ack_is_classified_from_durable_marker(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    ack_mode: str,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_commit = db.commit
    commit_calls = 0

    def ambiguous_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 2:
            if ack_mode == "commit-then-raise":
                real_commit()
            raise RuntimeError(f"injected {ack_mode}")
        real_commit()

    monkeypatch.setattr(db, "commit", ambiguous_commit)

    if ack_mode == "raise-before":
        with pytest.raises(RuntimeError, match="raise-before"):
            phase_b.bind_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target_id,
            )
    else:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    source_reference = _fresh_source_reference(db, target_id)
    expected_status = (
        _PENDING_CUSTODY
        if ack_mode == "raise-before"
        else _VERIFIED_CUSTODY
    )
    assert source_reference[_CUSTODY_KEY]["status"] == expected_status
    db.rollback()
    if ack_mode == "raise-before":
        monkeypatch.setattr(db, "commit", real_commit)
        before = _fresh_source_reference(db, target_id)
        db.rollback()
        with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
            phase_b.bind_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target_id,
            )
        assert excinfo.value.code == "nrc_phase_b_custody_ineligible"
        assert _fresh_source_reference(db, target_id) == before


def test_phase_two_committed_base_exception_is_not_swallowed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_commit = db.commit
    commit_calls = 0

    def interrupt_after_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        real_commit()
        if commit_calls == 2:
            raise KeyboardInterrupt("injected phase-two interrupt")

    monkeypatch.setattr(db, "commit", interrupt_after_commit)

    with pytest.raises(
        KeyboardInterrupt,
        match="injected phase-two interrupt",
    ):
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert not db.in_transaction()
    source_reference = _fresh_source_reference(db, target_id)
    assert source_reference[_CUSTODY_KEY]["status"] == _VERIFIED_CUSTODY


def test_pending_custody_retry_rejects_before_raw_work(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, witness = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    injected = RuntimeError("injected phase-two failure")
    real_commit = _install_second_commit_failure(
        db,
        monkeypatch,
        error=injected,
    )
    with pytest.raises(RuntimeError, match="injected phase-two failure"):
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )
    monkeypatch.setattr(db, "commit", real_commit)

    before = _fresh_source_reference(witness, target_id)
    assert before[_CUSTODY_KEY]["status"] == _PENDING_CUSTODY
    witness.rollback()
    raw_calls: list[str] = []
    parse_calls: list[str] = []

    def reject_raw_work(*args: Any, **kwargs: Any) -> Any:
        raw_calls.append("rehash")
        pytest.fail("pending retry reached raw rehash")

    def reject_parse(*args: Any, **kwargs: Any) -> Any:
        parse_calls.append("parse")
        pytest.fail("pending retry reached strict parser")

    monkeypatch.setattr(phase_b, "_safe_rehash", reject_raw_work)
    monkeypatch.setattr(
        phase_b.nrc_aps_strict_parse,
        "parse_admitted_blob_strict",
        reject_parse,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_custody_ineligible"
    assert raw_calls == []
    assert parse_calls == []
    assert not db.in_transaction()
    assert _fresh_source_reference(witness, target_id) == before


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_phase_two_precommit_base_exception_preserves_pending(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[BaseException],
) -> None:
    db, witness = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    injected = error_type("injected precommit base exception")
    real_commit = _install_second_commit_failure(
        db,
        monkeypatch,
        error=injected,
    )
    with pytest.raises(error_type) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value is injected
    assert not db.in_transaction()
    before = _fresh_source_reference(witness, target_id)
    assert before[_CUSTODY_KEY]["status"] == _PENDING_CUSTODY
    witness.rollback()
    monkeypatch.setattr(db, "commit", real_commit)

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as retry_error:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert retry_error.value.code == "nrc_phase_b_custody_ineligible"
    assert not db.in_transaction()
    assert _fresh_source_reference(witness, target_id) == before


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("invalidate_fails", [False, True])
@pytest.mark.parametrize(
    "cleanup_error_type",
    [RuntimeError, KeyboardInterrupt, SystemExit],
)
def test_cleanup_rollback_failure_preserves_original_base_exception(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[BaseException],
    invalidate_fails: bool,
    cleanup_error_type: type[BaseException],
) -> None:
    db, witness = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_rollback = db.rollback
    real_invalidate = db.invalidate
    base_raised = False
    cleanup_failure_injected = False
    invalidations = 0
    injected = error_type("original base exception")

    def mark_base_raised() -> None:
        nonlocal base_raised
        base_raised = True

    def fail_first_cleanup_rollback() -> None:
        nonlocal cleanup_failure_injected
        if base_raised and not cleanup_failure_injected:
            cleanup_failure_injected = True
            raise cleanup_error_type("injected rollback failure")
        real_rollback()

    def record_invalidation() -> None:
        nonlocal invalidations
        invalidations += 1
        if invalidate_fails:
            raise cleanup_error_type("injected invalidation failure")
        real_invalidate()

    _install_second_commit_failure(
        db,
        monkeypatch,
        error=injected,
        before_raise=mark_base_raised,
    )
    monkeypatch.setattr(db, "rollback", fail_first_cleanup_rollback)
    monkeypatch.setattr(db, "invalidate", record_invalidation)

    with pytest.raises(error_type) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value is injected
    assert cleanup_failure_injected
    assert invalidations == 1
    if not invalidate_fails:
        assert not db.in_transaction()
    source_reference = _fresh_source_reference(witness, target_id)
    assert source_reference[_CUSTODY_KEY]["status"] == _PENDING_CUSTODY


@pytest.mark.parametrize(
    "drift_surface",
    ["run", "target", "event", "document", "chunk", "linkage"],
)
def test_commit_ack_drift_is_not_classified_as_success(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    drift_surface: str,
) -> None:
    db, competing = file_dbs
    run, target, _, _ = _make_strict_state(db)
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    injected = RuntimeError(f"injected {drift_surface} drift")

    _install_second_commit_failure(
        db,
        monkeypatch,
        error=injected,
        commit_first=True,
        before_raise=lambda: _apply_commit_ack_drift(
            competing,
            drift_surface=drift_surface,
            run_id=run_id,
            target_id=target_id,
        ),
    )

    with pytest.raises(RuntimeError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value is injected
    assert not db.in_transaction()
    source_reference = _fresh_source_reference(competing, target_id)
    assert source_reference[_CUSTODY_KEY]["status"] == _VERIFIED_CUSTODY


def test_phase_two_concurrent_target_json_change_is_not_overwritten(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_snapshot = phase_b.locked_raw_file_snapshot

    @contextmanager
    def mutate_after_phase_one(
        *args: Any,
        **kwargs: Any,
    ) -> Generator[raw_handles.LockedRawFileSnapshot, None, None]:
        with real_snapshot(*args, **kwargs) as snapshot:
            yield snapshot
            competing_target = competing.get(ConnectorRunTarget, target_id)
            assert competing_target is not None
            changed = dict(competing_target.source_reference_json)
            changed["detail_response_sha256"] = "e" * 64
            competing_target.source_reference_json = changed
            competing.commit()

    monkeypatch.setattr(
        phase_b,
        "locked_raw_file_snapshot",
        mutate_after_phase_one,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError):
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    source_reference = _fresh_source_reference(competing, target_id)
    assert source_reference["detail_response_sha256"] == "e" * 64
    assert source_reference[_CUSTODY_KEY]["status"] == _PENDING_CUSTODY
    competing.rollback()
    with pytest.raises(phase_b.NrcPhaseBLinkageError) as retry_error:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )
    assert retry_error.value.code == "nrc_phase_b_custody_ineligible"
    assert _fresh_source_reference(competing, target_id) == source_reference


@pytest.mark.parametrize(
    "marker_case",
    ["missing", "malformed", "contradictory"],
)
def test_existing_linkage_requires_exact_verified_custody_marker(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    marker_case: str,
) -> None:
    _, target, raw_path, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )
    source_reference = _fresh_source_reference(db, target_id)
    db.rollback()
    if marker_case == "missing":
        source_reference.pop(_CUSTODY_KEY, None)
    elif marker_case == "malformed":
        source_reference[_CUSTODY_KEY] = {
            "schema_id": _CUSTODY_SCHEMA,
            "status": _VERIFIED_CUSTODY,
        }
    else:
        marker = _marker_for(
            linkage,
            raw_size=raw_path.stat().st_size,
        )
        marker["content_id"] = "0" * 64
        source_reference[_CUSTODY_KEY] = marker
    stored_target = db.get(ConnectorRunTarget, target_id)
    assert stored_target is not None
    stored_target.source_reference_json = deepcopy(source_reference)
    db.commit()

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_custody_ineligible"
    assert _fresh_source_reference(db, target_id) == source_reference


def test_post_parse_target_row_drift_fails_before_db_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)

    def drift(**kwargs: Any) -> dict[str, Any]:
        db.query(ConnectorRunTarget).filter(
            ConnectorRunTarget.connector_run_target_id
            == target.connector_run_target_id
        ).update({"downloaded_sha256": "0" * 64})
        db.commit()
        return _strict_output()

    _install_parser(monkeypatch, callback=drift)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_row_drift"
    assert db.query(ApsContentLinkage).count() == 0


@pytest.mark.parametrize(
    ("mutate", "case_id"),
    [
        (
            lambda output: output.__setitem__(
                "normalized_text_sha256",
                "0" * 64,
            ),
            "claimed_hash",
        ),
        (
            lambda output: output["ordered_units"][1].__setitem__(
                "start_char",
                0,
            ),
            "offset",
        ),
        (
            lambda output: output.__setitem__(
                "visual_page_refs",
                [{"page_number": 1, "ref": "forbidden"}],
            ),
            "visual",
        ),
        (
            lambda output: output.__setitem__(
                "normalization_contract_id",
                "wrong_contract",
            ),
            "contract",
        ),
        (
            lambda output: output["ordered_units"][0].__setitem__(
                "bbox",
                [5.0, 4.0, 1.0, 2.0],
            ),
            "geometry",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_malformed_strict_parser_output_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
    case_id: str,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    output = _strict_output()
    mutate(output)
    _install_parser(monkeypatch, output=output)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert case_id
    assert excinfo.value.code == "nrc_phase_b_parse_projection_invalid"
    assert db.query(ApsContentLinkage).count() == 0


def test_strict_parser_hash_refusal_is_preserved_as_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)

    def refuse(**kwargs: Any) -> dict[str, Any]:
        raise nrc_aps_strict_parse.StrictParseViolation(
            "strict_blob_sha256_mismatch"
        )

    _install_parser(monkeypatch, callback=refuse)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_parse_failed"
    assert db.query(ApsContentLinkage).count() == 0


def test_strict_parser_value_error_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)

    def refuse(**kwargs: Any) -> dict[str, Any]:
        raise ValueError("pdf_open_failed")

    _install_parser(monkeypatch, callback=refuse)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_parse_failed"
    assert db.query(ApsContentLinkage).count() == 0


def _strict_payload(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_path: Path,
    digest: str,
    output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return (
        nrc_aps_content_index
        .build_strict_content_units_payload_from_processed_output(
            run_id=run.connector_run_id,
            target_id=target.connector_run_target_id,
            accession_number="ML17123A319",
            blob_ref=str(raw_path),
            blob_sha256=digest,
            processed_output=deepcopy(output or _strict_output()),
        )
    )


def _seed_document_projection(
    db: Session,
    payload: dict[str, Any],
    *,
    normalized_char_delta: int = 0,
) -> ApsContentDocument:
    document = ApsContentDocument(
        content_id=payload["content_id"],
        content_contract_id=payload["content_contract_id"],
        chunking_contract_id=payload["chunking_contract_id"],
        normalization_contract_id=payload["normalization_contract_id"],
        normalized_text_sha256=payload["normalized_text_sha256"],
        normalized_char_count=(
            int(payload["normalized_char_count"])
            + normalized_char_delta
        ),
        chunk_count=payload["chunk_count"],
        content_status=payload["content_status"],
        media_type=payload["effective_content_type"],
        document_class=payload["document_class"],
        quality_status=payload["quality_status"],
        page_count=payload["page_count"],
        diagnostics_ref=payload["diagnostics_ref"],
        visual_page_refs_json=json.dumps(payload["visual_page_refs"]),
    )
    db.add(document)
    for chunk in payload["chunks"]:
        db.add(
            ApsContentChunk(
                content_id=payload["content_id"],
                chunk_id=chunk["chunk_id"],
                content_contract_id=payload["content_contract_id"],
                chunking_contract_id=payload["chunking_contract_id"],
                chunk_ordinal=chunk["chunk_ordinal"],
                start_char=chunk["start_char"],
                end_char=chunk["end_char"],
                chunk_text=chunk["chunk_text"],
                chunk_text_sha256=chunk["chunk_text_sha256"],
                page_start=chunk["page_start"],
                page_end=chunk["page_end"],
                unit_kind=chunk["unit_kind"],
                quality_status=payload["quality_status"],
            )
        )
    db.commit()
    return document


def _seed_linkage(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    content_id: str,
    blob_ref: str,
    blob_sha256: str,
) -> ApsContentLinkage:
    row = ApsContentLinkage(
        content_id=content_id,
        run_id=run.connector_run_id,
        target_id=target.connector_run_target_id,
        accession_number="ML17123A319",
        content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        normalized_text_sha256="e" * 64,
        blob_ref=blob_ref,
        blob_sha256=blob_sha256,
    )
    db.add(row)
    db.commit()
    return row


def test_stale_linkage_fails_without_overwrite(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    _install_parser(monkeypatch)
    stale = _seed_linkage(
        db,
        run=run,
        target=target,
        content_id="f" * 64,
        blob_ref=str(raw_path),
        blob_sha256=digest,
    )
    before = _row_snapshot(db)
    db.rollback()

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_linkage_mismatch"
    db.refresh(stale)
    assert stale.content_id == "f" * 64
    assert _row_snapshot(db) == before


def test_two_run_target_linkages_fail_without_repair(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    _install_parser(monkeypatch)
    _seed_linkage(
        db,
        run=run,
        target=target,
        content_id="e" * 64,
        blob_ref=str(raw_path),
        blob_sha256=digest,
    )
    _seed_linkage(
        db,
        run=run,
        target=target,
        content_id="f" * 64,
        blob_ref=str(raw_path),
        blob_sha256=digest,
    )

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_linkage_cardinality"
    assert db.query(ApsContentLinkage).count() == 2


def test_mismatching_shared_content_fails_before_generic_upsert(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    output = _strict_output()
    _install_parser(monkeypatch, output=output)
    payload = _strict_payload(
        run=run,
        target=target,
        raw_path=raw_path,
        digest=digest,
        output=output,
    )
    _seed_document_projection(
        db,
        payload,
        normalized_char_delta=1,
    )
    phase_b = _phase_b()
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        lambda *args, **kwargs: pytest.fail(
            "mutable generic upsert reached for mismatching shared state"
        ),
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_shared_content_mismatch"
    assert db.query(ApsContentLinkage).count() == 0


def test_exact_shared_content_is_reused_with_linkage_only(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    output = _strict_output()
    _install_parser(monkeypatch, output=output)
    payload = _strict_payload(
        run=run,
        target=target,
        raw_path=raw_path,
        digest=digest,
        output=output,
    )
    document = _seed_document_projection(db, payload)
    document_id = document.aps_content_document_id
    chunk_ids = [
        row.aps_content_chunk_id
        for row in db.query(ApsContentChunk).all()
    ]
    document_updated_at = document.updated_at.replace(tzinfo=None)
    db.rollback()
    phase_b = _phase_b()
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        lambda *args, **kwargs: pytest.fail(
            "generic upsert must not rewrite exact shared content"
        ),
    )

    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    db.refresh(document)
    assert document.aps_content_document_id == document_id
    assert document.updated_at.replace(tzinfo=None) == document_updated_at
    assert [
        row.aps_content_chunk_id
        for row in db.query(ApsContentChunk).all()
    ] == chunk_ids
    assert linkage.content_id == payload["content_id"]
    assert db.query(ApsContentLinkage).count() == 1


def test_absent_content_uses_immutable_insert_once(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_insert = (
        phase_b.nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    calls = 0

    def record(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return real_insert(*args, **kwargs)

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        record,
    )
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        lambda *args, **kwargs: pytest.fail(
            "mutable generic upsert reached from Phase B"
        ),
    )

    phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert calls == 1


def test_sqlite_phase_one_writer_reservation_blocks_exact_competitor(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_insert = (
        phase_b.nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    calls = 0
    write_outcomes: list[str] = []
    competing.connection().exec_driver_sql("PRAGMA busy_timeout=100")

    def race(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        assert calls == 1
        payload = deepcopy(kwargs["payload"])
        try:
            nrc_aps_content_index.upsert_content_units_payload(
                competing,
                payload=payload,
            )
            competing.commit()
        except OperationalError:
            competing.rollback()
            write_outcomes.append("blocked")
        else:
            write_outcomes.append("committed")
        return real_insert(*args, **kwargs)

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        race,
    )

    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    competing.expire_all()
    persisted = competing.query(ApsContentLinkage).one()
    assert calls == 1
    assert write_outcomes == ["blocked"]
    assert linkage.aps_content_linkage_id == (
        persisted.aps_content_linkage_id
    )
    assert persisted.target_id == target_id
    assert competing.query(ApsContentDocument).count() == 1
    assert competing.query(ApsContentChunk).count() == 1


def test_exact_conflict_recovery_accepts_fresh_verified_winner(
    file_dbs: tuple[Session, Session],
) -> None:
    db, competing = file_dbs
    run, target, raw_path, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    phase_b = _phase_b()
    output = _strict_output()
    payload = _strict_payload(
        run=run,
        target=target,
        raw_path=raw_path,
        digest=digest,
        output=output,
    )
    event_snapshot = phase_b._validate_run(db, run)
    run_snapshot = phase_b._run_snapshot(run)
    target_snapshot = phase_b._target_snapshot(target)
    initial_source_reference = deepcopy(target.source_reference_json)
    raw_size = raw_path.stat().st_size
    db.rollback()

    winner = (
        nrc_aps_content_index
        .insert_content_units_payload_immutable(
            competing,
            payload=payload,
        )
    )
    competing.commit()
    winner_target = competing.get(
        ConnectorRunTarget,
        target_id,
    )
    assert winner_target is not None
    winner_source_reference = deepcopy(initial_source_reference)
    winner_source_reference[_CUSTODY_KEY] = _marker_for(
        winner,
        raw_size=raw_size,
    )
    winner_target.source_reference_json = winner_source_reference
    competing.commit()

    recovered = phase_b._recover_exact_conflict(
        db,
        payload=payload,
        run_snapshot=run_snapshot,
        target_snapshot=target_snapshot,
        event_snapshot=event_snapshot,
        initial_source_reference=initial_source_reference,
        raw_size=raw_size,
    )

    assert sa_inspect(recovered).detached
    assert recovered.aps_content_linkage_id == (
        winner.aps_content_linkage_id
    )
    assert not db.in_transaction()


@pytest.mark.parametrize(
    "winner_case",
    [
        "exact-verified",
        "pending",
        "missing",
        "nonexact",
        "run-drift",
        "target-drift",
        "event-drift",
    ],
)
def test_public_conflict_recovery_accepts_only_verified_exact_winner(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    winner_case: str,
) -> None:
    db, competing = file_dbs
    run, target, raw_path, _ = _make_strict_state(db)
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    raw_size = raw_path.stat().st_size
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_begin = phase_b._begin_authoritative_transaction
    real_insert = (
        nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    begin_calls = 0
    conflict_calls = 0
    winner_id: str | None = None

    def allow_injected_non_sqlite_interleaving(session: Session) -> None:
        nonlocal begin_calls
        begin_calls += 1
        if begin_calls > 1:
            real_begin(session)

    def insert_winner_then_conflict(
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal conflict_calls, winner_id
        conflict_calls += 1
        payload = deepcopy(kwargs["payload"])
        if winner_case == "nonexact":
            winner = ApsContentLinkage(
                aps_content_linkage_id="nonexact-conflict-linkage",
                content_id="f" * 64,
                run_id=payload["run_id"],
                target_id=payload["target_id"],
                accession_number=payload["accession_number"],
                content_contract_id=payload["content_contract_id"],
                chunking_contract_id=payload["chunking_contract_id"],
                normalized_text_sha256="0" * 64,
                blob_ref=payload["blob_ref"],
                blob_sha256="0" * 64,
            )
            competing.add(winner)
        else:
            winner = (
                real_insert(
                    competing,
                    payload=payload,
                )
            )
        winner_id = winner.aps_content_linkage_id
        competing_target = competing.get(
            ConnectorRunTarget,
            target_id,
        )
        assert competing_target is not None
        if winner_case != "missing":
            status = (
                _PENDING_CUSTODY
                if winner_case == "pending"
                else _VERIFIED_CUSTODY
            )
            source_reference = deepcopy(
                competing_target.source_reference_json
            )
            source_reference[_CUSTODY_KEY] = _marker_for(
                winner,
                raw_size=raw_size,
                status=status,
            )
            competing_target.source_reference_json = source_reference
        if winner_case == "run-drift":
            competing_run = competing.get(ConnectorRun, run_id)
            assert competing_run is not None
            competing_run.status = "failed"
        elif winner_case == "target-drift":
            competing_target.status = "failed"
        elif winner_case == "event-drift":
            competing.add(
                ConnectorRunEvent(
                    connector_run_event_id="public-recovery-drift-event",
                    connector_run_id=run_id,
                    connector_run_target_id=target_id,
                    phase="execution",
                    stage="progress",
                    event_type="progress",
                    status_before="running",
                    status_after="running",
                    reason_code="progress",
                    metrics_json={},
                    created_at=datetime.now(timezone.utc),
                )
            )
        competing.commit()
        raise nrc_aps_content_index.ImmutableContentInsertConflict(
            "injected public conflict"
        )

    monkeypatch.setattr(
        phase_b,
        "_begin_authoritative_transaction",
        allow_injected_non_sqlite_interleaving,
    )
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        insert_winner_then_conflict,
    )

    if winner_case == "exact-verified":
        linkage = phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )
        assert linkage.aps_content_linkage_id == winner_id
        assert sa_inspect(linkage).detached
    else:
        with pytest.raises(phase_b.NrcPhaseBLinkageError):
            phase_b.bind_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=target_id,
            )

    assert conflict_calls == 1
    assert begin_calls == 2
    assert not db.in_transaction()
    competing.expire_all()
    assert competing.query(ApsContentLinkage).count() == 1


def test_public_conflict_recovery_translates_sqlalchemy_error(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    db.rollback()
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_begin = phase_b._begin_authoritative_transaction
    begin_calls = 0

    def fail_recovery_begin(session: Session) -> None:
        nonlocal begin_calls
        begin_calls += 1
        if begin_calls == 2:
            raise OperationalError(
                "BEGIN",
                {},
                RuntimeError("injected recovery DB failure"),
            )
        real_begin(session)

    def conflict(*args: Any, **kwargs: Any) -> Any:
        raise nrc_aps_content_index.ImmutableContentInsertConflict(
            "injected public conflict"
        )

    monkeypatch.setattr(
        phase_b,
        "_begin_authoritative_transaction",
        fail_recovery_begin,
    )
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        conflict,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_persistence_conflict"
    assert begin_calls == 2
    assert not db.in_transaction()


@pytest.mark.parametrize(
    ("authority_surface", "field_name", "changed_value"),
    [
        ("run", "query_plan_json", {"unexpected": ["drift"]}),
        ("target", "blocked_reason", "unexpected drift"),
    ],
)
def test_all_column_snapshot_rejects_previously_omitted_field_drift(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    authority_surface: str,
    field_name: str,
    changed_value: Any,
) -> None:
    db, competing = file_dbs
    run, target, _, _ = _make_strict_state(db)
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    phase_b = _phase_b()

    def drift_during_parse(**kwargs: Any) -> dict[str, Any]:
        if authority_surface == "run":
            competing.query(ConnectorRun).filter(
                ConnectorRun.connector_run_id == run_id
            ).update(
                {field_name: changed_value},
                synchronize_session=False,
            )
        else:
            competing.query(ConnectorRunTarget).filter(
                ConnectorRunTarget.connector_run_target_id == target_id
            ).update(
                {field_name: changed_value},
                synchronize_session=False,
            )
        competing.commit()
        return _strict_output()

    _install_parser(monkeypatch, callback=drift_during_parse)

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_row_drift"
    assert competing.query(ApsContentLinkage).count() == 0


def test_all_column_snapshot_rejects_same_pk_target_replacement(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    _, target, _, _ = _make_strict_state(db)
    target_id = target.connector_run_target_id
    replacement_values = {
        column.key: deepcopy(getattr(target, column.key))
        for column in ConnectorRunTarget.__table__.columns
    }
    phase_b = _phase_b()

    def replace_during_parse(**kwargs: Any) -> dict[str, Any]:
        competing.query(ConnectorRunTarget).filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        ).delete(synchronize_session=False)
        competing.flush()
        replacement_values["blocked_reason"] = "replacement drift"
        competing.add(ConnectorRunTarget(**replacement_values))
        competing.commit()
        return _strict_output()

    _install_parser(monkeypatch, callback=replace_during_parse)

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_row_drift"
    competing.expire_all()
    replacement = competing.get(ConnectorRunTarget, target_id)
    assert replacement is not None
    assert replacement.blocked_reason == "replacement drift"
    assert competing.query(ApsContentLinkage).count() == 0


def _custody_marker_with_blob_ref(blob_ref: str) -> dict[str, Any]:
    return {
        "schema_id": _CUSTODY_SCHEMA,
        "status": _VERIFIED_CUSTODY,
        "attempt_id": _ATTEMPT_ID,
        "connector_run_id": "strict-run",
        "connector_run_target_id": "strict-target",
        "aps_content_linkage_id": "strict-linkage",
        "content_id": "a" * 64,
        "blob_ref": blob_ref,
        "blob_sha256": "b" * 64,
        "blob_size_bytes": 1,
    }


@pytest.mark.parametrize(
    "blob_ref",
    [
        "ftp://example.test/blob.pdf",
        "file:///var/raw/blob.pdf",
        "urn:project6:raw-blob",
        "\\\\server\\share\\blob.pdf",
        "//server/share/blob.pdf",
        "x://host/blob.pdf",
        r"x:\\host\blob.pdf",
        r"x:/\host/blob.pdf",
        r"x:\/host\blob.pdf",
        "x:////host/blob.pdf",
        r"x:\\\\host\blob.pdf",
    ],
)
def test_custody_marker_rejects_uri_and_network_blob_refs(
    blob_ref: str,
) -> None:
    custody = _phase_b().nrc_phase_b_custody
    with pytest.raises(custody.NrcPhaseBCustodyMarkerError):
        custody.parse_custody_marker(
            _custody_marker_with_blob_ref(blob_ref)
        )


@pytest.mark.parametrize(
    "blob_ref",
    [
        r"C:\path\blob.pdf",
        "C:/path/blob.pdf",
        "/var/lib/project6/raw/blob.pdf",
    ],
)
def test_custody_marker_allows_local_absolute_blob_refs(
    blob_ref: str,
) -> None:
    custody = _phase_b().nrc_phase_b_custody
    pending = custody.build_pending_custody_marker(
        connector_run_id="strict-run",
        connector_run_target_id="strict-target",
        aps_content_linkage_id="strict-linkage",
        content_id="a" * 64,
        blob_ref=blob_ref,
        blob_sha256="b" * 64,
        blob_size_bytes=1,
    )
    verified = custody.verified_custody_marker(pending)
    marker = custody.require_exact_custody_marker(
        verified,
        status=custody.VERIFIED,
        connector_run_id="strict-run",
        connector_run_target_id="strict-target",
        aps_content_linkage_id="strict-linkage",
        content_id="a" * 64,
        blob_ref=blob_ref,
        blob_sha256="b" * 64,
        blob_size_bytes=1,
        attempt_id=pending["attempt_id"],
    )
    assert marker["blob_ref"] == blob_ref


@pytest.mark.parametrize(
    "authority_surface",
    ["run", "target", "event-set"],
)
def test_post_parse_authority_drift_is_freshly_rejected(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
    authority_surface: str,
) -> None:
    db, competing = file_dbs
    run, target, _, _ = _make_strict_state(db)
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    phase_b = _phase_b()

    def drift_during_parse(**kwargs: Any) -> dict[str, Any]:
        if authority_surface == "run":
            competing.query(ConnectorRun).filter(
                ConnectorRun.connector_run_id == run_id
            ).update({"status": "failed"}, synchronize_session=False)
        elif authority_surface == "target":
            competing.query(ConnectorRunTarget).filter(
                ConnectorRunTarget.connector_run_target_id == target_id
            ).update({"status": "failed"}, synchronize_session=False)
        else:
            competing.add(
                ConnectorRunEvent(
                    connector_run_event_id="recovery-benign-event",
                    connector_run_id=run_id,
                    connector_run_target_id=target_id,
                    phase="execution",
                    stage="progress",
                    event_type="progress",
                    status_before="running",
                    status_after="running",
                    reason_code="progress",
                    metrics_json={},
                    created_at=datetime.now(timezone.utc),
                )
            )
        competing.commit()
        return _strict_output()

    _install_parser(
        monkeypatch,
        callback=drift_during_parse,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_row_drift"
    assert competing.query(ApsContentLinkage).count() == 0


def test_sqlite_phase_one_lock_blocks_post_read_mutation(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    _, target, _, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_require = phase_b._require_exact_persisted
    write_outcomes: list[str] = []
    competing.connection().exec_driver_sql("PRAGMA busy_timeout=100")

    def read_then_try_write(*args: Any, **kwargs: Any) -> Any:
        exact = real_require(*args, **kwargs)
        if write_outcomes:
            return exact
        try:
            competing.query(ConnectorRunTarget).filter(
                ConnectorRunTarget.connector_run_target_id == target_id
            ).update(
                {"downloaded_sha256": "0" * 64},
                synchronize_session=False,
            )
            competing.commit()
        except OperationalError:
            competing.rollback()
            write_outcomes.append("blocked")
        else:
            write_outcomes.append("committed")
        return exact

    monkeypatch.setattr(
        phase_b,
        "_require_exact_persisted",
        read_then_try_write,
    )

    phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    assert write_outcomes == ["blocked"]
    competing.expire_all()
    assert (
        competing.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .one()
        .downloaded_sha256
        == digest
    )
    assert competing.query(ApsContentLinkage).one().blob_sha256 == digest


def test_sqlite_phase_one_writer_reservation_blocks_nonexact_competitor(
    file_dbs: tuple[Session, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, competing = file_dbs
    _, target, _, digest = _make_strict_state(db)
    target_id = target.connector_run_target_id
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_insert = (
        phase_b.nrc_aps_content_index
        .insert_content_units_payload_immutable
    )
    calls = 0
    write_outcomes: list[str] = []
    competing.connection().exec_driver_sql("PRAGMA busy_timeout=100")

    def race(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        assert calls == 1
        payload = kwargs["payload"]
        competing.add(
            ApsContentLinkage(
                content_id="f" * 64,
                run_id=payload["run_id"],
                target_id=payload["target_id"],
                accession_number=payload["accession_number"],
                content_contract_id=payload["content_contract_id"],
                chunking_contract_id=payload["chunking_contract_id"],
                normalized_text_sha256="0" * 64,
                blob_ref=payload["blob_ref"],
                blob_sha256="0" * 64,
            )
        )
        try:
            competing.commit()
        except OperationalError:
            competing.rollback()
            write_outcomes.append("blocked")
        else:
            write_outcomes.append("committed")
        return real_insert(*args, **kwargs)

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "insert_content_units_payload_immutable",
        race,
    )

    phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target_id,
    )

    competing.expire_all()
    persisted = competing.query(ApsContentLinkage).one()
    assert calls == 1
    assert write_outcomes == ["blocked"]
    assert persisted.blob_sha256 == digest
    assert competing.query(ApsContentDocument).count() == 1
    assert competing.query(ApsContentChunk).count() == 1
