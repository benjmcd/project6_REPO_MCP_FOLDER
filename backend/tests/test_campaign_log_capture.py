from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from sqlalchemy import create_engine, event as sqlalchemy_event, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models import ConnectorRun, ConnectorRunEvent
from app.schemas.api import ConnectorCampaignLogCaptureRefV1
from app.services import raw_storage_handles as raw_handles
from app.services.connector_campaign_log_capture import (
    ConnectorCampaignLogCaptureCommitAmbiguous,
    ConnectorCampaignLogCaptureError,
    begin_connector_campaign_log_capture,
    seal_connector_campaign_log_capture,
)
from app.services.dual_live_runtime import (
    RuntimeIdentity,
    RuntimeRecordWriter,
    read_runtime_records,
)
from app.services.connector_egress_arming import (
    canonical_arming_payload,
    compute_arming_fingerprint,
    compute_parent_arming_id,
)
from app.services.connector_egress_authorization import canonical_json_bytes


START = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64
DEFINITION_SHA256 = "b" * 64
CODE_REVISION = "c" * 40
INDEX_SHA256 = "d" * 64
NRC_GRANT_SHA256 = "e" * 64
SCIENCEBASE_GRANT_SHA256 = "f" * 64
CAMPAIGN_ID = UUID("123e4567-e89b-42d3-a456-426614174000")
ARMING_NONCES = {
    "nrc_adams_aps": UUID("123e4567-e89b-42d3-a456-426614174001"),
    "sciencebase_mcs": UUID("123e4567-e89b-42d3-a456-426614174002"),
}
GOLDEN_MANIFEST_SHA256 = (
    "74c2d3ef0fb232cdf5d7f1eeaf91e842b4415c6a0feac84e1faaf0be438217ec"
)
GOLDEN_FILE_SET_HASH = (
    "64a929d72bf738a2d3c0aa6ad1a287cbd0d5cc7f679139b1f94da1d5371a59bd"
)
GOLDEN_SEAL_SHA256 = (
    "ce44dd9eff7c6a33fe0ec5419fd37b4ee9e9dc0679d000ea59e726c287428fbe"
)


@dataclass(frozen=True)
class _AuthorityFixture:
    campaign_id: UUID
    evidence_root: Path
    verified_campaign: Any
    current_grants: dict[str, Any]
    historical_grants: dict[str, Any]
    run_ids: dict[str, str]


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    local = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    session = local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _grant_model(
    *,
    campaign_id: UUID,
    connector_key: str,
) -> Any:
    return SimpleNamespace(
        connector_key=connector_key,
        campaign_id=campaign_id,
        campaign_fingerprint=FINGERPRINT,
        code_revision=CODE_REVISION,
        grant_id=f"{connector_key}-grant",
        arming_nonce=ARMING_NONCES[connector_key],
        max_armings=1,
        supersedes_grant_sha256=None,
        operator_mode="local_loopback",
        non_authorities=("no-seeding", "no-retry"),
        target={"host": "example.invalid"},
        request_rules=({"method": "GET"},),
        max_physical_requests=1,
        max_run_bytes=1024,
        max_single_send_detection_allowance_bytes=64,
        request_timeout_seconds=5,
        min_request_interval_ms=0,
        issued_at=START - timedelta(hours=1),
        expires_at=START + timedelta(hours=1),
    )


def _authority_fixture(tmp_path: Path) -> _AuthorityFixture:
    campaign_id = CAMPAIGN_ID
    evidence_root = tmp_path / "evidence"
    (evidence_root / "logs").mkdir(parents=True)
    (evidence_root / "log-seals").mkdir()
    capture_ref = ConnectorCampaignLogCaptureRefV1(
        campaign_id=str(campaign_id),
        campaign_fingerprint=FINGERPRINT,
        campaign_definition_sha256=DEFINITION_SHA256,
        code_revision=CODE_REVISION,
        log_dir_relative_path=f"logs/{FINGERPRINT}",
        manifest_relative_path=f"logs/{FINGERPRINT}/manifest.json",
        seal_relative_path=f"log-seals/{FINGERPRINT}.json",
        expected_stream_files=(
            "app.jsonl",
            "http.jsonl",
            "stdout.log",
            "stderr.log",
        ),
    )
    definition_model = SimpleNamespace(
        campaign_id=campaign_id,
        code_revision=CODE_REVISION,
        not_before=START - timedelta(hours=2),
        expires_at=START + timedelta(hours=2),
    )
    entries = (
        SimpleNamespace(
            connector_key="nrc_adams_aps",
            campaign_id=str(campaign_id),
            campaign_fingerprint=FINGERPRINT,
            raw_grant_sha256=NRC_GRANT_SHA256,
        ),
        SimpleNamespace(
            connector_key="sciencebase_mcs",
            campaign_id=str(campaign_id),
            campaign_fingerprint=FINGERPRINT,
            raw_grant_sha256=SCIENCEBASE_GRANT_SHA256,
        ),
    )
    definition_ref = SimpleNamespace(
        campaign_id=str(campaign_id),
        campaign_fingerprint=FINGERPRINT,
    )
    head = SimpleNamespace(
        revision=1,
        campaigns=(definition_ref,),
        entries=entries,
        log_captures=(capture_ref,),
    )
    chain = SimpleNamespace(
        evidence_root=evidence_root,
        head=head,
        head_raw_sha256=INDEX_SHA256,
        head_path=evidence_root / "indexes" / f"{INDEX_SHA256}.json",
        revisions=(),
    )
    verified_campaign = SimpleNamespace(
        model=definition_model,
        raw_sha256=DEFINITION_SHA256,
        canonical_fingerprint=FINGERPRINT,
        introduction_index_revision=1,
        introduction_index_sha256=INDEX_SHA256,
        evidence_root=evidence_root,
        index_chain=chain,
    )
    grant_models = {
        connector_key: _grant_model(
            campaign_id=campaign_id,
            connector_key=connector_key,
        )
        for connector_key in ("nrc_adams_aps", "sciencebase_mcs")
    }
    grant_hashes = {
        "nrc_adams_aps": NRC_GRANT_SHA256,
        "sciencebase_mcs": SCIENCEBASE_GRANT_SHA256,
    }
    current_grants: dict[str, Any] = {}
    historical_grants: dict[str, Any] = {}
    run_ids: dict[str, str] = {}
    for connector_key, model in grant_models.items():
        grant_sha256 = grant_hashes[connector_key]
        run_id = compute_parent_arming_id(
            connector_key=connector_key,
            campaign_id=str(campaign_id),
            grant_sha256=grant_sha256,
            arming_nonce=model.arming_nonce,
        )
        run_ids[connector_key] = run_id
        current_grants[connector_key] = SimpleNamespace(
            model=model,
            raw_sha256=grant_sha256,
            canonical_fingerprint=hashlib.sha256(
                connector_key.encode()
            ).hexdigest(),
            verified_campaign=verified_campaign,
        )
        historical_grants[connector_key] = SimpleNamespace(
            definition_model=definition_model,
            model=model,
            raw_definition_sha256=DEFINITION_SHA256,
            canonical_campaign_fingerprint=FINGERPRINT,
            raw_sha256=grant_sha256,
            canonical_fingerprint=current_grants[
                connector_key
            ].canonical_fingerprint,
            introduction_index_revision=1,
            introduction_index_sha256=INDEX_SHA256,
            marker_model=SimpleNamespace(connector_run_id=run_id),
            index_chain=chain,
        )
    return _AuthorityFixture(
        campaign_id=campaign_id,
        evidence_root=evidence_root,
        verified_campaign=verified_campaign,
        current_grants=current_grants,
        historical_grants=historical_grants,
        run_ids=run_ids,
    )


def _install_authority(
    monkeypatch: pytest.MonkeyPatch,
    authority: _AuthorityFixture,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    def current_campaign(**kwargs: Any) -> Any:
        assert kwargs == {
            "expected_campaign_id": str(authority.campaign_id),
            "expected_campaign_fingerprint": FINGERPRINT,
            "code_revision": CODE_REVISION,
            "now": START,
        }
        return authority.verified_campaign

    def current_grant(**kwargs: Any) -> Any:
        connector_key = kwargs.pop("connector_key")
        grant = authority.current_grants[connector_key]
        assert kwargs == {
            "verified_campaign": authority.verified_campaign,
            "expected_grant_sha256": grant.raw_sha256,
            "campaign_id": str(authority.campaign_id),
            "campaign_fingerprint": FINGERPRINT,
            "code_revision": CODE_REVISION,
            "now": START,
        }
        return grant

    def historical_grant(**kwargs: Any) -> Any:
        connector_key = kwargs.pop("connector_key")
        grant = authority.historical_grants[connector_key]
        assert kwargs == {
            "campaign_id": str(authority.campaign_id),
            "expected_campaign_fingerprint": FINGERPRINT,
            "expected_grant_sha256": grant.raw_sha256,
        }
        return grant

    monkeypatch.setattr(
        capture_service,
        "resolve_current_dual_live_campaign_definition",
        current_campaign,
    )
    monkeypatch.setattr(
        capture_service,
        "resolve_current_connector_egress_grant",
        current_grant,
    )
    monkeypatch.setattr(
        capture_service,
        "_load_evidence_index_chain",
        lambda: authority.verified_campaign.index_chain,
    )
    monkeypatch.setattr(
        capture_service,
        "resolve_historical_connector_grant_evidence",
        historical_grant,
    )


def _arming_envelope(
    authority: _AuthorityFixture,
    connector_key: str,
) -> dict[str, Any]:
    grant = authority.current_grants[connector_key]
    model = grant.model
    receipt = {
        "schema_id": "project6.connector_egress_authorization_receipt.v1",
        "connector_key": connector_key,
        "campaign_id": str(authority.campaign_id),
        "campaign_fingerprint": FINGERPRINT,
        "campaign_definition_sha256": DEFINITION_SHA256,
        "grant_sha256": grant.raw_sha256,
        "canonical_grant_fingerprint": grant.canonical_fingerprint,
        "introduction_index_revision": 1,
        "introduction_index_sha256": INDEX_SHA256,
        "operator_ref_hash": "1" * 64,
        "workspace_ref_hash": "2" * 64,
        "auth_owner_mode": "none",
        "authorization_mode": "identity_presence",
        "role": None,
        "access": "write",
    }
    envelope: dict[str, Any] = {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": connector_key,
        "campaign_id": str(authority.campaign_id),
        "campaign_definition_sha256": DEFINITION_SHA256,
        "campaign_fingerprint": FINGERPRINT,
        "grant_sha256": grant.raw_sha256,
        "canonical_grant_fingerprint": grant.canonical_fingerprint,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": INDEX_SHA256,
        "code_revision": CODE_REVISION,
        "grant_id": model.grant_id,
        "arming_nonce": model.arming_nonce,
        "max_armings": model.max_armings,
        "supersedes_grant_sha256": model.supersedes_grant_sha256,
        "operator_mode": model.operator_mode,
        "non_authorities": model.non_authorities,
        "target": model.target,
        "request_rules": model.request_rules,
        "max_physical_requests": model.max_physical_requests,
        "max_run_bytes": model.max_run_bytes,
        "max_single_send_detection_allowance_bytes": (
            model.max_single_send_detection_allowance_bytes
        ),
        "request_timeout_seconds": model.request_timeout_seconds,
        "min_request_interval_ms": model.min_request_interval_ms,
        "grant_issued_at": model.issued_at,
        "grant_expires_at": model.expires_at,
        "campaign_not_before": (
            authority.verified_campaign.model.not_before
        ),
        "campaign_expires_at": (
            authority.verified_campaign.model.expires_at
        ),
        "authorization_receipt": receipt,
    }
    if connector_key == "sciencebase_mcs":
        envelope.update(
            predecessor_nrc_connector_run_id=authority.run_ids[
                "nrc_adams_aps"
            ],
            predecessor_nrc_ledger_terminal_hash="3" * 64,
        )
    canonical = canonical_arming_payload(envelope)
    return {
        **canonical,
        "arming_fingerprint": compute_arming_fingerprint(canonical),
    }


def _insert_terminal_runs(
    db: Session,
    authority: _AuthorityFixture,
    *,
    connector_keys: tuple[str, ...],
) -> None:
    for offset, connector_key in enumerate(connector_keys):
        envelope = _arming_envelope(authority, connector_key)
        run_id = authority.run_ids[connector_key]
        submitted_at = START + timedelta(seconds=1 + offset)
        started_at = START + timedelta(seconds=3 + offset)
        completed_at = START + timedelta(seconds=5 + offset)
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key=connector_key,
            source_system=(
                "nrc_adams"
                if connector_key == "nrc_adams_aps"
                else "sciencebase"
            ),
            source_mode="strict_live_egress",
            status="completed",
            request_config_json={"connector_egress_arming": envelope},
            query_plan_json={},
            request_fingerprint=envelope["arming_fingerprint"],
            submission_idempotency_key=f"egress-arm:{connector_key}",
            submitted_at=submitted_at,
            started_at=started_at,
            completed_at=completed_at,
            execution_lease_owner=None,
            execution_lease_token=None,
        )
        terminal_event_id = str(
            uuid5(
                NAMESPACE_URL,
                (
                    f"project6:connector-egress:{run_id}:"
                    "egress_run_terminal:0"
                ),
            )
        )
        terminal = ConnectorRunEvent(
            connector_run_event_id=terminal_event_id,
            connector_run_id=run_id,
            phase="execution",
            stage="terminal",
            event_type="egress_run_terminal",
            status_before="running",
            status_after="completed",
            reason_code="fixture_completed",
            error_class=None,
            message=None,
            metrics_json={
                "outcome_class": "fixture_completed",
                "arming_fingerprint": envelope["arming_fingerprint"],
                "campaign_introduction_index_revision": 1,
                "campaign_introduction_index_sha256": INDEX_SHA256,
            },
            created_at=completed_at,
        )
        db.add_all([run, terminal])
    db.commit()


def _begin_and_close(
    authority: _AuthorityFixture,
) -> Any:
    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=FINGERPRINT,
        expected_code_revision=CODE_REVISION,
        now=START,
    )
    payloads = (b'{"app":1}\n', b'{"http":1}\n', b"stdout\n", b"stderr\n")
    assert tuple(writer.stream_class for writer in capture.writers) == (
        "app",
        "http",
        "stdout",
        "stderr",
    )
    for writer, payload in zip(capture.writers, payloads, strict=True):
        assert writer.write(payload) == len(payload)
        writer.flush()
        writer.close()
    return capture


def _seal_event_id(run_id: str) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            (
                f"project6:connector-egress:{run_id}:"
                "campaign_log_capture_sealed:0"
            ),
        )
    )


def _artifact_paths(
    authority: _AuthorityFixture,
) -> tuple[Path, Path]:
    return (
        authority.evidence_root
        / "logs"
        / FINGERPRINT
        / "manifest.json",
        authority.evidence_root
        / "log-seals"
        / f"{FINGERPRINT}.json",
    )


def _assert_unpublished(authority: _AuthorityFixture) -> None:
    manifest, seal = _artifact_paths(authority)
    assert not manifest.exists()
    assert not manifest.with_name(".manifest.json.stage").exists()
    assert not seal.exists()
    assert not seal.with_name(f".{seal.name}.stage").exists()


def _connector_run_rows(db: Session) -> tuple[tuple[Any, ...], ...]:
    columns = tuple(ConnectorRun.__table__.columns)
    with db.get_bind().connect() as connection:
        rows = connection.execute(
            select(ConnectorRun.__table__).order_by(
                ConnectorRun.connector_run_id
            )
        ).mappings()
        return tuple(
            tuple(row[column.key] for column in columns) for row in rows
        )


def test_dual_capture_seals_exact_bytes_and_two_events_once(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps", "sciencebase_mcs"),
    )
    run_rows_before = _connector_run_rows(db)
    commit_calls = 0
    flush_calls = 0
    real_commit = db.commit
    real_flush = db.flush

    def counted_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        real_commit()

    def counted_flush(*args: Any, **kwargs: Any) -> None:
        nonlocal flush_calls
        flush_calls += 1
        real_flush(*args, **kwargs)

    monkeypatch.setattr(db, "commit", counted_commit)
    monkeypatch.setattr(db, "flush", counted_flush)
    result = seal_connector_campaign_log_capture(
        db,
        capture=capture,
        runtime_stopped_at=START + timedelta(seconds=10),
        now=START + timedelta(seconds=11),
    )

    expected_run_ids = tuple(sorted(authority.run_ids.values()))
    expected_event_ids = tuple(
        sorted(_seal_event_id(run_id) for run_id in expected_run_ids)
    )
    assert result.seal.connector_run_ids == expected_run_ids
    assert result.event_ids == expected_event_ids
    assert commit_calls == 1
    assert flush_calls == 1
    assert _connector_run_rows(db) == run_rows_before
    manifest_path, seal_path = _artifact_paths(authority)
    payloads = (b'{"app":1}\n', b'{"http":1}\n', b"stdout\n", b"stderr\n")
    file_names = ("app.jsonl", "http.jsonl", "stdout.log", "stderr.log")
    stream_classes = ("app", "http", "stdout", "stderr")
    expected_files = [
        {
            "relative_path": f"logs/{FINGERPRINT}/{file_name}",
            "stream_class": stream_class,
            "byte_count": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for file_name, stream_class, payload in zip(
            file_names,
            stream_classes,
            payloads,
            strict=True,
        )
    ]
    expected_manifest = {
        "schema_id": "project6.connector_campaign_log_manifest.v1",
        "campaign_id": str(authority.campaign_id),
        "campaign_fingerprint": FINGERPRINT,
        "campaign_definition_sha256": DEFINITION_SHA256,
        "code_revision": CODE_REVISION,
        "runtime_started_at": START,
        "runtime_stopped_at": START + timedelta(seconds=10),
        "files": expected_files,
    }
    manifest_bytes = canonical_json_bytes(expected_manifest)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    file_set_preimage = {
        "schema_id": "project6.connector_campaign_log_file_set.v1",
        "files": expected_files,
    }
    file_set_hash = hashlib.sha256(
        canonical_json_bytes(file_set_preimage)
    ).hexdigest()
    expected_seal = {
        "schema_id": "project6.connector_campaign_log_seal.v1",
        "campaign_id": str(authority.campaign_id),
        "campaign_fingerprint": FINGERPRINT,
        "campaign_definition_sha256": DEFINITION_SHA256,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": INDEX_SHA256,
        "code_revision": CODE_REVISION,
        "manifest_relative_path": f"logs/{FINGERPRINT}/manifest.json",
        "manifest_sha256": manifest_sha256,
        "file_set_hash": file_set_hash,
        "connector_run_ids": expected_run_ids,
        "sealed_at": START + timedelta(seconds=11),
    }
    seal_bytes = canonical_json_bytes(expected_seal)
    assert manifest_sha256 == GOLDEN_MANIFEST_SHA256
    assert file_set_hash == GOLDEN_FILE_SET_HASH
    assert hashlib.sha256(seal_bytes).hexdigest() == GOLDEN_SEAL_SHA256
    assert manifest_path.read_bytes() == manifest_bytes
    assert seal_path.read_bytes() == seal_bytes
    assert result.manifest_sha256 == manifest_sha256
    assert result.seal_sha256 == hashlib.sha256(seal_bytes).hexdigest()
    assert result.file_set_hash == file_set_hash
    with sessionmaker(
        bind=db.get_bind(),
        expire_on_commit=False,
        future=True,
    )() as check:
        runs = check.scalars(
            select(ConnectorRun).order_by(ConnectorRun.connector_run_id)
        ).all()
        assert [run.status for run in runs] == ["completed", "completed"]
        events = check.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.event_type
                == "campaign_log_capture_sealed"
            )
        ).all()
        assert sorted(event.connector_run_event_id for event in events) == list(
            expected_event_ids
        )
        expected_metrics = {
            "schema_id": (
                "project6.connector_campaign_log_seal_event_metrics.v1"
            ),
            "campaign_id": str(authority.campaign_id),
            "campaign_fingerprint": FINGERPRINT,
            "campaign_definition_sha256": DEFINITION_SHA256,
            "code_revision": CODE_REVISION,
            "campaign_introduction_index_revision": 1,
            "campaign_introduction_index_sha256": INDEX_SHA256,
            "manifest_relative_path": (
                f"logs/{FINGERPRINT}/manifest.json"
            ),
            "manifest_sha256": manifest_sha256,
            "file_set_hash": file_set_hash,
            "seal_relative_path": f"log-seals/{FINGERPRINT}.json",
            "seal_sha256": hashlib.sha256(seal_bytes).hexdigest(),
            "connector_run_ids": list(expected_run_ids),
            "sealed_at": "2026-07-30T12:00:11.000000Z",
        }
        assert all(
            event.metrics_json == expected_metrics for event in events
        )
        for event in events:
            created_at = event.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            assert {
                column.key: (
                    created_at
                    if column.key == "created_at"
                    else getattr(event, column.key)
                )
                for column in ConnectorRunEvent.__table__.columns
            } == {
                "connector_run_event_id": _seal_event_id(
                    event.connector_run_id
                ),
                "connector_run_id": event.connector_run_id,
                "connector_run_target_id": None,
                "phase": "evidence",
                "stage": "campaign_log_capture",
                "event_type": "campaign_log_capture_sealed",
                "status_before": "completed",
                "status_after": "completed",
                "reason_code": "protected_log_capture_sealed",
                "error_class": None,
                "message": None,
                "metrics_json": expected_metrics,
                "created_at": START + timedelta(seconds=11),
            }


@pytest.mark.parametrize(
    "connector_keys",
    (
        ("nrc_adams_aps",),
        ("nrc_adams_aps", "sciencebase_mcs"),
    ),
    ids=("nrc-only", "two-run"),
)
def test_task5_controller_closeout_seals_existing_runtime_records_once(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    connector_keys: tuple[str, ...],
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    index_path = authority.verified_campaign.index_chain.head_path
    index_path.parent.mkdir()
    index_bytes = canonical_json_bytes(
        {
            "revision": 1,
            "sha256": INDEX_SHA256,
        }
    )
    index_path.write_bytes(index_bytes)

    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=FINGERPRINT,
        expected_code_revision=CODE_REVISION,
        now=START,
    )
    assert tuple(writer.stream_class for writer in capture.writers) == (
        "app",
        "http",
        "stdout",
        "stderr",
    )

    identity = RuntimeIdentity(
        runtime_instance_id=str(CAMPAIGN_ID),
        wrapper_nonce_sha256="1" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="2" * 64,
        interpreter_image_sha256="3" * 64,
        root_mutex_identity_sha256="4" * 64,
        campaign_mutex_identity_sha256="5" * 64,
    )
    runtime_writer = RuntimeRecordWriter(
        capture.writers[0].write,
        identity=identity,
    )
    runtime_records = (
        runtime_writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload={
                "code_revision": CODE_REVISION,
                "wrapper_image_sha256": identity.wrapper_image_sha256,
                "interpreter_image_sha256": (
                    identity.interpreter_image_sha256
                ),
                "mutex_identity_sha256": "6" * 64,
            },
        ),
        runtime_writer.append(
            phase="wrapper",
            event="runtime_complete",
            process_boot_id=None,
            payload={
                "phase_a_result_sha256": "7" * 64,
                "phase_b_result_sha256": "8" * 64,
                "terminal_state": "completed",
            },
        ),
    )
    app_bytes = b"".join(
        canonical_json_bytes(record) + b"\n" for record in runtime_records
    )
    payload_by_stream = {
        "http": b"",
        "stdout": b"phase output\n",
        "stderr": b"",
    }
    for writer in capture.writers[1:]:
        payload = payload_by_stream[writer.stream_class]
        if payload:
            assert writer.write(payload) == len(payload)
    for writer in capture.writers:
        writer.flush()
    for writer in capture.writers:
        writer.close()
    assert all(writer.closed for writer in capture.writers)

    _insert_terminal_runs(
        db,
        authority,
        connector_keys=connector_keys,
    )
    run_rows_before = _connector_run_rows(db)
    result = seal_connector_campaign_log_capture(
        db,
        capture=capture,
        runtime_stopped_at=START + timedelta(seconds=10),
        now=START + timedelta(seconds=11),
    )

    expected_run_ids = tuple(
        sorted(authority.run_ids[key] for key in connector_keys)
    )
    expected_event_ids = tuple(
        sorted(_seal_event_id(run_id) for run_id in expected_run_ids)
    )
    assert result.seal.connector_run_ids == expected_run_ids
    assert result.event_ids == expected_event_ids
    assert _connector_run_rows(db) == run_rows_before
    manifest_path, seal_path = _artifact_paths(authority)
    app_path = manifest_path.parent / "app.jsonl"
    assert app_path.read_bytes() == app_bytes
    assert read_runtime_records(app_path.read_bytes()) == runtime_records
    app_manifest = next(
        item for item in result.manifest.files if item.stream_class == "app"
    )
    assert app_manifest.byte_count == len(app_bytes)
    assert app_manifest.sha256 == hashlib.sha256(app_bytes).hexdigest()
    assert tuple(item.stream_class for item in result.manifest.files) == (
        "app",
        "http",
        "stdout",
        "stderr",
    )
    assert sorted(path.name for path in manifest_path.parent.iterdir()) == [
        "app.jsonl",
        "http.jsonl",
        "manifest.json",
        "stderr.log",
        "stdout.log",
    ]
    sealed_events = db.scalars(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.event_type == "campaign_log_capture_sealed"
        )
    ).all()
    assert tuple(
        sorted(event.connector_run_event_id for event in sealed_events)
    ) == expected_event_ids
    assert tuple(
        sorted(event.connector_run_id for event in sealed_events)
    ) == expected_run_ids
    if connector_keys == ("nrc_adams_aps",):
        assert db.get(
            ConnectorRun,
            authority.run_ids["sciencebase_mcs"],
        ) is None

    manifest_bytes = manifest_path.read_bytes()
    seal_bytes = seal_path.read_bytes()
    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        begin_connector_campaign_log_capture(
            campaign_id=authority.campaign_id,
            expected_campaign_fingerprint=FINGERPRINT,
            expected_code_revision=CODE_REVISION,
            now=START,
        )
    assert excinfo.value.code == "connector_campaign_log_path_conflict"
    assert manifest_path.read_bytes() == manifest_bytes
    assert seal_path.read_bytes() == seal_bytes
    assert index_path.read_bytes() == index_bytes
    assert tuple(index_path.parent.iterdir()) == (index_path,)


def test_nrc_only_capture_does_not_fabricate_sciencebase(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service
    from app.services import (
        connector_egress_arming,
        connectors_sciencebase,
    )

    def forbidden(*_: Any, **__: Any) -> None:
        raise AssertionError("capture called a forbidden evaluator/resolver")

    monkeypatch.setattr(
        connector_egress_arming,
        "evaluate_nrc_acquisition_success",
        forbidden,
    )
    monkeypatch.setattr(
        connector_egress_arming,
        "_load_nrc_counter_records",
        forbidden,
    )
    monkeypatch.setattr(
        connector_egress_arming,
        "resolve_current_egress_authority",
        forbidden,
    )
    monkeypatch.setattr(
        connectors_sciencebase,
        "_resolve_current_sciencebase_egress_authority",
        forbidden,
    )
    for name in (
        "resolve_current_egress_authority",
        "evaluate_nrc_acquisition_success",
        "_load_nrc_counter_records",
        "_validated_nrc_ledger_entries",
        "_reconcile_nrc_counter_records",
        "derive_terminal_request_ledger",
        "_strict_http_counter_path",
        "_sciencebase_http_counter_path",
        "_resolve_current_sciencebase_egress_authority",
    ):
        monkeypatch.setattr(
            capture_service,
            name,
            forbidden,
            raising=False,
        )
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )

    result = seal_connector_campaign_log_capture(
        db,
        capture=capture,
        runtime_stopped_at=START + timedelta(seconds=10),
        now=START + timedelta(seconds=11),
    )

    nrc_run_id = authority.run_ids["nrc_adams_aps"]
    assert result.seal.connector_run_ids == (nrc_run_id,)
    assert result.event_ids == (_seal_event_id(nrc_run_id),)
    db.expire_all()
    assert db.get(
        ConnectorRun,
        authority.run_ids["sciencebase_mcs"],
    ) is None
    assert db.scalar(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.connector_run_id
            == authority.run_ids["sciencebase_mcs"]
        )
    ) is None
    db.rollback()


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        ("zero", "connector_campaign_log_run_cardinality_invalid"),
        ("sciencebase_only", "connector_campaign_log_run_cardinality_invalid"),
        ("same_campaign_extra", "connector_campaign_log_run_cardinality_invalid"),
        ("nonterminal", "connector_campaign_log_run_not_terminal"),
        ("live_lease", "connector_campaign_log_run_not_terminal"),
        ("missing_terminal", "connector_campaign_log_terminal_event_invalid"),
        ("duplicate_terminal", "connector_campaign_log_terminal_event_invalid"),
        ("terminal_mismatch", "connector_campaign_log_terminal_event_mismatch"),
        ("malformed_receipt", "connector_campaign_log_run_receipt_invalid"),
        ("chronology", "connector_campaign_log_run_not_terminal"),
        ("event_cap", "connector_campaign_log_event_cap_exhausted"),
        ("deterministic_event", "connector_campaign_log_event_conflict"),
    ),
)
def test_database_adversaries_reject_before_publication(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    if case == "sciencebase_only":
        keys = ("sciencebase_mcs",)
    elif case == "zero":
        keys = ()
    else:
        keys = ("nrc_adams_aps",)
    if keys:
        _insert_terminal_runs(db, authority, connector_keys=keys)
    nrc_id = authority.run_ids["nrc_adams_aps"]
    run = db.get(ConnectorRun, nrc_id) if keys else None
    if case == "same_campaign_extra":
        assert run is not None
        extra = ConnectorRun(
            connector_run_id=str(uuid4()),
            connector_key="nrc_adams_aps",
            source_system="nrc_adams",
            source_mode="strict_live_egress",
            status="completed",
            request_config_json=run.request_config_json,
            request_fingerprint=run.request_fingerprint,
            submission_idempotency_key="egress-arm:extra",
            submitted_at=START + timedelta(seconds=1),
            started_at=START + timedelta(seconds=2),
            completed_at=START + timedelta(seconds=4),
        )
        db.add(extra)
    elif case == "nonterminal":
        assert run is not None
        run.status = "running"
    elif case == "live_lease":
        assert run is not None
        run.execution_lease_owner = "worker"
        run.execution_lease_token = "1" * 64
    elif case == "missing_terminal":
        terminal = db.scalar(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == nrc_id
            )
        )
        assert terminal is not None
        db.delete(terminal)
    elif case == "duplicate_terminal":
        terminal = db.scalar(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == nrc_id
            )
        )
        assert terminal is not None
        db.add(
            ConnectorRunEvent(
                connector_run_event_id=str(uuid4()),
                connector_run_id=nrc_id,
                phase=terminal.phase,
                stage=terminal.stage,
                event_type=terminal.event_type,
                status_before=terminal.status_before,
                status_after=terminal.status_after,
                reason_code=terminal.reason_code,
                metrics_json=terminal.metrics_json,
                created_at=terminal.created_at,
            )
        )
    elif case == "terminal_mismatch":
        terminal = db.scalar(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == nrc_id
            )
        )
        assert terminal is not None
        terminal.reason_code = "different"
    elif case == "malformed_receipt":
        assert run is not None
        envelope = dict(
            run.request_config_json["connector_egress_arming"]
        )
        receipt = dict(envelope["authorization_receipt"])
        receipt["operator_ref_hash"] = "INVALID"
        envelope["authorization_receipt"] = receipt
        envelope.pop("arming_fingerprint")
        canonical = canonical_arming_payload(envelope)
        fingerprint = compute_arming_fingerprint(canonical)
        run.request_config_json = {
            "connector_egress_arming": {
                **canonical,
                "arming_fingerprint": fingerprint,
            }
        }
        run.request_fingerprint = fingerprint
        terminal = db.scalar(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == nrc_id
            )
        )
        assert terminal is not None
        terminal.metrics_json = {
            **terminal.metrics_json,
            "arming_fingerprint": fingerprint,
        }
    elif case == "chronology":
        assert run is not None
        run.submitted_at = START - timedelta(microseconds=1)
    elif case == "event_cap":
        for ordinal in range(7):
            db.add(
                ConnectorRunEvent(
                    connector_run_event_id=str(uuid4()),
                    connector_run_id=nrc_id,
                    phase="execution",
                    stage="progress",
                    event_type=f"fixture_progress_{ordinal}",
                    status_before="running",
                    status_after="running",
                    reason_code="fixture_progress",
                    metrics_json={"ordinal": ordinal},
                    created_at=START + timedelta(seconds=4),
                )
            )
    elif case == "deterministic_event":
        db.add(
            ConnectorRunEvent(
                connector_run_event_id=_seal_event_id(nrc_id),
                connector_run_id=nrc_id,
                phase="evidence",
                stage="campaign_log_capture",
                event_type="campaign_log_capture_sealed",
                status_before="completed",
                status_after="completed",
                reason_code="protected_log_capture_sealed",
                metrics_json={},
                created_at=START + timedelta(seconds=6),
            )
        )
    db.commit()

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == expected_code
    _assert_unpublished(authority)


def test_foreign_run_cannot_squat_deterministic_seal_event(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    foreign_id = str(uuid4())
    db.add_all(
        [
            ConnectorRun(
                connector_run_id=foreign_id,
                connector_key="fixture",
                source_system="fixture",
                source_mode="public_api",
                status="completed",
                submitted_at=START,
                completed_at=START,
            ),
            ConnectorRunEvent(
                connector_run_event_id=_seal_event_id(
                    authority.run_ids["nrc_adams_aps"]
                ),
                connector_run_id=foreign_id,
                event_type="unrelated",
                metrics_json={},
                created_at=START,
            ),
        ]
    )
    db.commit()

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == "connector_campaign_log_event_conflict"
    _assert_unpublished(authority)


def test_public_session_projection_replacement_is_rejected(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    forged = replace(capture, campaign_id=str(uuid4()))

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=forged,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert (
        excinfo.value.code
        == "connector_campaign_log_session_binding_mismatch"
    )
    _assert_unpublished(authority)


def test_public_writer_substitution_cannot_bypass_owned_writer_finality(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=FINGERPRINT,
        expected_code_revision=CODE_REVISION,
        now=START,
    )
    decoys = []
    for stream_class in ("app", "http", "stdout", "stderr"):
        decoy = capture_service.ConnectorCampaignLogWriter(
            SimpleNamespace(closed=True),
            stream_class,
        )
        decoy._closed_clean = True
        decoys.append(decoy)
    forged = replace(capture, writers=tuple(decoys))

    try:
        with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
            seal_connector_campaign_log_capture(
                db,
                capture=forged,
                runtime_stopped_at=START + timedelta(seconds=10),
                now=START + timedelta(seconds=11),
            )
        assert (
            excinfo.value.code
            == "connector_campaign_log_writer_binding_invalid"
        )
        assert all(not writer.closed for writer in capture.writers)
        assert all(
            writer._flushed_state is None for writer in capture.writers
        )
        _assert_unpublished(authority)
    finally:
        for writer in capture.writers:
            writer.close()


def test_self_attested_writer_substitution_is_rejected(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=FINGERPRINT,
        expected_code_revision=CODE_REVISION,
        now=START,
    )
    decoys = []
    for stream_class in ("app", "http", "stdout", "stderr"):
        decoy = capture_service.ConnectorCampaignLogWriter(
            SimpleNamespace(closed=True),
            stream_class,
        )
        decoy._closed_clean = True
        decoys.append(decoy)
    decoy_tuple = tuple(decoys)
    forged = replace(
        capture,
        writers=decoy_tuple,
        _binding_token=capture._binding_token,
    )
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )

    try:
        with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
            seal_connector_campaign_log_capture(
                db,
                capture=forged,
                runtime_stopped_at=START + timedelta(seconds=10),
                now=START + timedelta(seconds=11),
            )
        assert (
            excinfo.value.code
            == "connector_campaign_log_writer_binding_invalid"
        )
        assert all(not writer.closed for writer in capture.writers)
        _assert_unpublished(authority)
    finally:
        for writer in capture.writers:
            writer.close()


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        (
            "fingerprint",
            "connector_campaign_log_historical_authority_mismatch",
        ),
        ("code", "connector_campaign_log_historical_authority_mismatch"),
        ("index", "connector_campaign_log_historical_authority_mismatch"),
        ("marker", "connector_campaign_log_marker_run_mismatch"),
        ("start_window", "connector_campaign_log_start_outside_authority"),
    ),
)
def test_historical_authority_drift_rejects_before_publication(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    history = authority.historical_grants["nrc_adams_aps"]
    if case == "fingerprint":
        history.canonical_campaign_fingerprint = "7" * 64
    elif case == "code":
        history.model.code_revision = "7" * 40
    elif case == "index":
        history.introduction_index_sha256 = "7" * 64
    elif case == "marker":
        history.marker_model.connector_run_id = str(uuid4())
    else:
        history.definition_model.not_before = START + timedelta(seconds=1)

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == expected_code
    _assert_unpublished(authority)


@pytest.mark.parametrize("target_kind", ("final", "stage"))
def test_preexisting_seal_before_begin_creates_no_campaign_streams(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    target_kind: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    _, seal_path = _artifact_paths(authority)
    target = (
        seal_path
        if target_kind == "final"
        else seal_path.with_name(f".{seal_path.name}.stage")
    )
    target.write_bytes(b"preexisting")

    with pytest.raises(ConnectorCampaignLogCaptureError):
        begin_connector_campaign_log_capture(
            campaign_id=authority.campaign_id,
            expected_campaign_fingerprint=FINGERPRINT,
            expected_code_revision=CODE_REVISION,
            now=START,
        )

    assert target.read_bytes() == b"preexisting"
    assert not (
        authority.evidence_root / "logs" / FINGERPRINT
    ).exists()


def test_preexisting_campaign_directory_rejects_before_stream_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    campaign_dir = authority.evidence_root / "logs" / FINGERPRINT
    campaign_dir.mkdir()

    with pytest.raises(ConnectorCampaignLogCaptureError):
        begin_connector_campaign_log_capture(
            campaign_id=authority.campaign_id,
            expected_campaign_fingerprint=FINGERPRINT,
            expected_code_revision=CODE_REVISION,
            now=START,
        )

    assert list(campaign_dir.iterdir()) == []
    _assert_unpublished(authority)


def test_partial_begin_own_error_closes_all_writers_and_preserves_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    real_open = capture_service.open_new_locked_raw_file_writer
    real_writer_type = capture_service.ConnectorCampaignLogWriter
    raw_writers = []
    wrappers = []

    def tracked_open(*args: Any, **kwargs: Any) -> Any:
        writer = real_open(*args, **kwargs)
        raw_writers.append(writer)
        return writer

    def tracked_wrapper(*args: Any, **kwargs: Any) -> Any:
        writer = real_writer_type(*args, **kwargs)
        wrappers.append(writer)
        return writer

    def fail_membership(*_: Any, **__: Any) -> None:
        raise ConnectorCampaignLogCaptureError(
            "injected_partial_begin",
            "injected after all stream writers opened",
        )

    monkeypatch.setattr(
        capture_service,
        "open_new_locked_raw_file_writer",
        tracked_open,
    )
    monkeypatch.setattr(
        capture_service,
        "ConnectorCampaignLogWriter",
        tracked_wrapper,
    )
    monkeypatch.setattr(
        capture_service,
        "_exact_stream_membership",
        fail_membership,
    )

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        begin_connector_campaign_log_capture(
            campaign_id=authority.campaign_id,
            expected_campaign_fingerprint=FINGERPRINT,
            expected_code_revision=CODE_REVISION,
            now=START,
        )

    assert excinfo.value.code == "injected_partial_begin"
    assert len(raw_writers) == len(wrappers) == 4
    assert all(writer.closed for writer in raw_writers)
    assert all(writer.closed for writer in wrappers)
    campaign_dir = authority.evidence_root / "logs" / FINGERPRINT
    expected_names = {
        "app.jsonl",
        "http.jsonl",
        "stdout.log",
        "stderr.log",
    }
    assert {child.name for child in campaign_dir.iterdir()} == expected_names
    assert all(
        (campaign_dir / name).read_bytes() == b""
        for name in expected_names
    )

    with pytest.raises(ConnectorCampaignLogCaptureError):
        begin_connector_campaign_log_capture(
            campaign_id=authority.campaign_id,
            expected_campaign_fingerprint=FINGERPRINT,
            expected_code_revision=CODE_REVISION,
            now=START,
        )
    assert len(raw_writers) == len(wrappers) == 4
    assert {child.name for child in campaign_dir.iterdir()} == expected_names


@pytest.mark.parametrize("target_kind", ("final", "stage"))
def test_preexisting_manifest_at_seal_time_creates_no_seal(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    target_kind: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    manifest_path, seal_path = _artifact_paths(authority)
    target = (
        manifest_path
        if target_kind == "final"
        else manifest_path.with_name(".manifest.json.stage")
    )
    target.write_bytes(b"preexisting")

    with pytest.raises(ConnectorCampaignLogCaptureError):
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert target.read_bytes() == b"preexisting"
    assert not seal_path.exists()
    assert not seal_path.with_name(f".{seal_path.name}.stage").exists()


@pytest.mark.parametrize("target_kind", ("final", "stage"))
def test_preexisting_seal_at_seal_time_creates_no_new_artifact(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    target_kind: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    manifest_path, seal_path = _artifact_paths(authority)
    target = (
        seal_path
        if target_kind == "final"
        else seal_path.with_name(f".{seal_path.name}.stage")
    )
    target.write_bytes(b"preexisting")

    with pytest.raises(ConnectorCampaignLogCaptureError):
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert target.read_bytes() == b"preexisting"
    assert not manifest_path.exists()
    assert not manifest_path.with_name(".manifest.json.stage").exists()


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        ("unflushed", "connector_campaign_log_writer_not_final"),
        ("missing", "connector_campaign_log_stream_membership_invalid"),
        ("extra", "connector_campaign_log_stream_membership_invalid"),
        ("case_alias", "connector_campaign_log_stream_membership_invalid"),
        ("nonregular", "connector_campaign_log_stream_unsafe"),
        ("replaced", "connector_campaign_log_stream_invalid"),
        ("swapped", "connector_campaign_log_stream_invalid"),
        ("hardlink", "connector_campaign_log_stream_invalid"),
        ("directory_replaced", "connector_campaign_log_stream_invalid"),
    ),
)
def test_stream_identity_and_membership_adversaries_fail_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=FINGERPRINT,
        expected_code_revision=CODE_REVISION,
        now=START,
    )
    for index, writer in enumerate(capture.writers):
        writer.write(f"stream-{index}\n".encode())
        if case != "unflushed" or index != 0:
            writer.flush()
        writer.close()
    campaign_dir = authority.evidence_root / "logs" / FINGERPRINT
    app_path = campaign_dir / "app.jsonl"
    http_path = campaign_dir / "http.jsonl"
    if case == "missing":
        os.replace(app_path, authority.evidence_root / "moved-app")
    elif case == "extra":
        (campaign_dir / "extra.log").write_bytes(b"extra")
    elif case == "case_alias":
        real_iterdir = Path.iterdir

        def enumerate_case_alias(path: Path) -> Any:
            children = list(real_iterdir(path))
            if path == campaign_dir:
                children.append(path / "APP.JSONL")
            return iter(children)

        monkeypatch.setattr(Path, "iterdir", enumerate_case_alias)
    elif case == "nonregular":
        os.replace(app_path, authority.evidence_root / "moved-app")
        app_path.mkdir()
    elif case == "replaced":
        original = app_path.read_bytes()
        os.replace(app_path, authority.evidence_root / "old-app")
        app_path.write_bytes(original)
    elif case == "swapped":
        temporary = authority.evidence_root / "swap"
        os.replace(app_path, temporary)
        os.replace(http_path, app_path)
        os.replace(temporary, http_path)
    elif case == "hardlink":
        os.link(app_path, authority.evidence_root / "app-alias")
    elif case == "directory_replaced":
        old_dir = authority.evidence_root / "old-campaign"
        os.replace(campaign_dir, old_dir)
        campaign_dir.mkdir()
        for child in old_dir.iterdir():
            os.replace(child, campaign_dir / child.name)

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == expected_code
    _assert_unpublished(authority)


def test_bounded_snapshot_rejects_max_plus_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    output = raw_root / "oversized.bin"
    output.write_bytes(b"12345")

    with raw_handles.locked_raw_file_snapshot(
        raw_root,
        output,
        max_bytes=5,
    ) as exact:
        assert exact.size == 5
    read_calls = 0

    def unexpected_read(*_: Any, **__: Any) -> bytes:
        nonlocal read_calls
        read_calls += 1
        raise AssertionError("oversized file must be rejected before read")

    monkeypatch.setattr(raw_handles.os, "read", unexpected_read)
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        with raw_handles.locked_raw_file_snapshot(
            raw_root,
            output,
            max_bytes=4,
        ):
            pass

    assert excinfo.value.reason == "oversized"
    assert read_calls == 0


@pytest.mark.parametrize(
    ("case", "sizes"),
    (
        ("exact_per_file", (16 << 20, 0, 0, 0)),
        ("exact_aggregate", (8 << 20, 8 << 20, 8 << 20, 8 << 20)),
        ("per_file_plus_one", ((16 << 20) + 1, 0, 0, 0)),
        ("aggregate_plus_one", ((8 << 20) + 1, 8 << 20, 8 << 20, 8 << 20)),
    ),
)
def test_service_stream_bounds_are_exact_and_fail_at_plus_one(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    sizes: tuple[int, int, int, int],
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=FINGERPRINT,
        expected_code_revision=CODE_REVISION,
        now=START,
    )
    for writer, size in zip(capture.writers, sizes, strict=True):
        os.ftruncate(writer.fileno(), size)
        writer.flush()
        writer.close()
    if case.startswith("exact_"):
        _insert_terminal_runs(
            db,
            authority,
            connector_keys=("nrc_adams_aps",),
        )
        result = seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )
        assert tuple(
            item.byte_count for item in result.manifest.files
        ) == sizes
        assert sum(
            item.byte_count for item in result.manifest.files
        ) == sum(sizes)
    else:
        with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
            seal_connector_campaign_log_capture(
                db,
                capture=capture,
                runtime_stopped_at=START + timedelta(seconds=10),
                now=START + timedelta(seconds=11),
            )
        assert excinfo.value.code == "connector_campaign_log_stream_invalid"
        _assert_unpublished(authority)


def test_strict_new_rejects_existing_identical_bytes(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    output = raw_root / "same.bin"
    raw_handles.persist_locked_raw_file(raw_root, output, b"same")

    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        raw_handles.persist_locked_raw_file(
            raw_root,
            output,
            b"same",
            strict_new=True,
        )

    assert excinfo.value.reason == "conflict"
    assert output.read_bytes() == b"same"


def test_owned_writer_binds_identity_and_same_handle_snapshot(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    output = raw_root / "owned.bin"

    writer = raw_handles.open_new_locked_raw_file_writer(
        raw_root,
        output,
    )
    try:
        assert writer.write(b"owned") == 5
        writer.flush()
        snapshot = raw_handles.snapshot_open_locked_raw_file(
            writer,
            max_bytes=5,
            expected_identity=writer.identity,
            required_link_count=1,
        )
    finally:
        writer.close()

    assert snapshot.size == 5
    assert snapshot.sha256 == (
        "f5e6d024c05c9cc2746a3e127408b91a"
        "8b7a7f2a30da0c259bc54265502ddef4"
    )
    assert snapshot.identity == writer.identity
    assert snapshot.link_count == 1


def test_first_writer_exclusively_creates_and_binds_parent(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "evidence"
    logs = raw_root / "logs"
    logs.mkdir(parents=True)
    output = logs / ("a" * 64) / "app.jsonl"

    writer = raw_handles.open_new_locked_raw_file_writer(
        raw_root,
        output,
        create_immediate_parent_exclusive=True,
    )
    parent_identity = writer.parent_identity
    writer.close()

    second = raw_handles.open_new_locked_raw_file_writer(
        raw_root,
        output.parent / "http.jsonl",
        expected_parent_identity=parent_identity,
    )
    second.close()
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        raw_handles.open_new_locked_raw_file_writer(
            raw_root,
            output.parent / "retry.jsonl",
            create_immediate_parent_exclusive=True,
        )
    assert excinfo.value.reason == "conflict"
    assert output.exists()


def test_atomic_strict_publication_never_replays_existing_target(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "evidence"
    parent = raw_root / "logs"
    parent.mkdir(parents=True)
    output = parent / "manifest.json"
    content = b'{"sealed":true}'

    snapshot = raw_handles.publish_atomic_strict_new_locked_raw_file(
        raw_root,
        output,
        content,
        max_bytes=len(content),
    )

    assert snapshot.size == len(content)
    assert output.read_bytes() == content
    assert not output.with_name(f".{output.name}.stage").exists()
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )
    assert excinfo.value.reason == "conflict"
    assert output.read_bytes() == content


def test_snapshot_detects_file_growth_during_hash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    output = raw_root / "growing.bin"
    output.write_bytes(b"stable")
    real_hash = raw_handles._hash_fd
    mutated = False

    def growing_hash(fd: int, *, max_bytes: int | None) -> Any:
        nonlocal mutated
        result = real_hash(fd, max_bytes=max_bytes)
        if not mutated:
            mutated = True
            with output.open("ab") as stream:
                stream.write(b"+")
                stream.flush()
                os.fsync(stream.fileno())
        return result

    monkeypatch.setattr(raw_handles, "_hash_fd", growing_hash)
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        with raw_handles.locked_raw_file_snapshot(
            raw_root,
            output,
            max_bytes=7,
        ):
            pass

    assert mutated
    assert excinfo.value.reason == "changed"


def test_prepublish_failure_preserves_stage_and_retry_rejects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "evidence"
    parent = raw_root / "logs"
    parent.mkdir(parents=True)
    output = parent / "manifest.json"
    stage = output.with_name(".manifest.json.stage")
    content = b'{"manifest":true}'
    real_fsync = raw_handles.os.fsync

    def failed_fsync(_: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(raw_handles.os, "fsync", failed_fsync)
    with pytest.raises(OSError, match="injected fsync"):
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )
    monkeypatch.setattr(raw_handles.os, "fsync", real_fsync)

    assert not output.exists()
    assert stage.read_bytes() == content
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )
    assert excinfo.value.reason == "conflict"
    assert stage.read_bytes() == content


def test_zero_write_preserves_empty_stage_and_never_creates_final(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "evidence"
    parent = raw_root / "logs"
    parent.mkdir(parents=True)
    output = parent / "manifest.json"
    stage = output.with_name(".manifest.json.stage")
    content = b'{"manifest":true}'

    monkeypatch.setattr(
        raw_handles.OwnedLockedRawFileWriter,
        "write",
        lambda *_: 0,
    )
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )

    assert excinfo.value.reason == "io"
    assert stage.read_bytes() == b""
    assert not output.exists()
    with pytest.raises(raw_handles.StableRawStorageError) as retry:
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )
    assert retry.value.reason == "conflict"
    assert stage.read_bytes() == b""
    assert not output.exists()


@pytest.mark.parametrize("case", ("atomic_move", "final_rehash", "stage_race"))
def test_publication_partial_failure_is_never_repaired_or_replayed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    raw_root = tmp_path / "evidence"
    parent = raw_root / "logs"
    parent.mkdir(parents=True)
    output = parent / "manifest.json"
    stage = output.with_name(".manifest.json.stage")
    content = b'{"manifest":true}'
    if case == "atomic_move":
        mover_name = (
            "_atomic_no_replace_windows"
            if raw_handles._windows_backend_available()
            else "_atomic_no_replace_posix"
        )

        def failed_move(*_: Any, **__: Any) -> None:
            raise raw_handles.StableRawStorageError("io")

        monkeypatch.setattr(raw_handles, mover_name, failed_move)
    elif case == "final_rehash":

        @contextmanager
        def failed_snapshot(*_: Any, **__: Any) -> Any:
            raise raw_handles.StableRawStorageError("changed")
            yield

        monkeypatch.setattr(
            raw_handles,
            "locked_raw_file_snapshot",
            failed_snapshot,
        )
    else:
        real_stage_check = raw_handles._assert_publication_stage_absent

        def recreate_stage(*args: Any, **kwargs: Any) -> None:
            stage.write_bytes(b"raced")
            real_stage_check(*args, **kwargs)

        monkeypatch.setattr(
            raw_handles,
            "_assert_publication_stage_absent",
            recreate_stage,
        )

    with pytest.raises(raw_handles.StableRawStorageError):
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )

    if case == "atomic_move":
        assert not output.exists()
        assert stage.read_bytes() == content
    else:
        assert output.read_bytes() == content
        if case == "stage_race":
            assert stage.read_bytes() == b"raced"
    with pytest.raises(raw_handles.StableRawStorageError) as retry:
        raw_handles.publish_atomic_strict_new_locked_raw_file(
            raw_root,
            output,
            content,
            max_bytes=len(content),
        )
    assert retry.value.reason == "conflict"


def test_full_run_row_mutation_between_preflight_and_lock_is_rejected(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    real_publish = capture_service.publish_atomic_strict_new_locked_raw_file
    publish_calls = 0

    def publish_then_mutate(*args: Any, **kwargs: Any) -> Any:
        nonlocal publish_calls
        snapshot = real_publish(*args, **kwargs)
        publish_calls += 1
        if publish_calls == 1:
            with Session(
                bind=db.get_bind(),
                autoflush=False,
                expire_on_commit=False,
            ) as concurrent:
                run = concurrent.get(
                    ConnectorRun,
                    authority.run_ids["nrc_adams_aps"],
                )
                assert run is not None
                run.query_plan_json = {"concurrent": "mutation"}
                concurrent.commit()
        return snapshot

    monkeypatch.setattr(
        capture_service,
        "publish_atomic_strict_new_locked_raw_file",
        publish_then_mutate,
    )
    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == "connector_campaign_log_database_changed"
    assert publish_calls == 2
    manifest_path, seal_path = _artifact_paths(authority)
    assert manifest_path.exists()
    assert seal_path.exists()
    assert db.scalar(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.event_type
            == "campaign_log_capture_sealed"
        )
    ) is None
    db.rollback()


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        ("flush", "connector_campaign_log_database_write_failed"),
        ("cleanup", "precommit_cleanup_unconfirmed"),
        ("postflush", "connector_campaign_log_postflush_invalid"),
        ("commit_ack", "commit_outcome_ambiguous"),
    ),
)
def test_final_transaction_failures_preserve_artifacts_and_classify(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    real_flush = db.flush
    real_rollback = db.rollback
    real_commit = db.commit
    real_invalidate = db.invalidate
    rollback_calls = 0
    commit_calls = 0

    def counted_rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1
        real_rollback()

    def failed_flush(*_: Any, **__: Any) -> None:
        raise RuntimeError("injected flush failure")

    def failed_cleanup() -> None:
        nonlocal rollback_calls
        rollback_calls += 1
        raise RuntimeError("injected rollback failure")

    def injected_postflush(*args: Any, **kwargs: Any) -> None:
        real_flush(*args, **kwargs)
        db.execute(
            ConnectorRunEvent.__table__.insert().values(
                connector_run_event_id=str(uuid4()),
                connector_run_id=authority.run_ids["nrc_adams_aps"],
                connector_run_target_id=None,
                phase="execution",
                stage="injected",
                event_type="injected_postflush",
                status_before="completed",
                status_after="completed",
                reason_code="injected",
                error_class=None,
                message=None,
                metrics_json={},
                created_at=START + timedelta(seconds=6),
            )
        )

    def ambiguous_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        real_commit()
        raise RuntimeError("injected acknowledgement failure")

    monkeypatch.setattr(db, "rollback", counted_rollback)
    if case == "flush":
        monkeypatch.setattr(db, "flush", failed_flush)
    elif case == "cleanup":
        monkeypatch.setattr(db, "flush", failed_flush)
        monkeypatch.setattr(db, "rollback", failed_cleanup)
        monkeypatch.setattr(db, "invalidate", lambda: None)
    elif case == "postflush":
        monkeypatch.setattr(db, "flush", injected_postflush)
    else:
        monkeypatch.setattr(db, "commit", ambiguous_commit)
        monkeypatch.setattr(db, "invalidate", lambda: None)

    exception_type = (
        ConnectorCampaignLogCaptureCommitAmbiguous
        if case == "commit_ack"
        else ConnectorCampaignLogCaptureError
    )
    with pytest.raises(exception_type) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == expected_code
    manifest_path, seal_path = _artifact_paths(authority)
    manifest_bytes = manifest_path.read_bytes()
    seal_bytes = seal_path.read_bytes()
    if case == "commit_ack":
        assert rollback_calls == 0
        assert commit_calls == 1
    else:
        assert rollback_calls == 1
        assert commit_calls == 0
    if case != "cleanup":
        monkeypatch.setattr(db, "flush", real_flush)
        monkeypatch.setattr(db, "rollback", real_rollback)
        monkeypatch.setattr(db, "commit", real_commit)
        monkeypatch.setattr(db, "invalidate", real_invalidate)
        expected_events = 1 if case == "commit_ack" else 0
        assert len(
            db.scalars(
                select(ConnectorRunEvent).where(
                    ConnectorRunEvent.event_type
                    == "campaign_log_capture_sealed"
                )
            ).all()
        ) == expected_events
        db.rollback()
        with pytest.raises(ConnectorCampaignLogCaptureError) as retry:
            seal_connector_campaign_log_capture(
                db,
                capture=capture,
                runtime_stopped_at=START + timedelta(seconds=10),
                now=START + timedelta(seconds=11),
            )
        assert (
            retry.value.code
            == "connector_campaign_log_session_binding_mismatch"
        )
        assert manifest_path.read_bytes() == manifest_bytes
        assert seal_path.read_bytes() == seal_bytes


def test_sqlite_uses_begin_immediate_and_no_postcommit_derivation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    statements: list[str] = []
    committed = False
    real_event_id = capture_service._event_id
    real_commit = db.commit

    def record_statement(
        _: Any,
        __: Any,
        statement: str,
        *___: Any,
    ) -> None:
        statements.append(statement)

    def guarded_event_id(run_id: str, kind: str) -> str:
        if committed:
            raise AssertionError("event identity derived after commit")
        return real_event_id(run_id, kind)

    def commit_once() -> None:
        nonlocal committed
        real_commit()
        committed = True

    sqlalchemy_event.listen(
        db.get_bind(),
        "before_cursor_execute",
        record_statement,
    )
    monkeypatch.setattr(capture_service, "_event_id", guarded_event_id)
    monkeypatch.setattr(db, "commit", commit_once)
    try:
        result = seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )
    finally:
        sqlalchemy_event.remove(
            db.get_bind(),
            "before_cursor_execute",
            record_statement,
        )

    assert committed
    assert result.event_ids == (
        _seal_event_id(authority.run_ids["nrc_adams_aps"]),
    )
    assert [item for item in statements if item == "BEGIN IMMEDIATE"] == [
        "BEGIN IMMEDIATE"
    ]


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        ("new", "connector_campaign_log_session_not_clean"),
        ("transaction", "connector_campaign_log_session_not_clean"),
    ),
)
def test_dirty_or_active_supplied_session_is_rejected_before_artifacts(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    if case == "new":
        db.add(
            ConnectorRun(
                connector_run_id=str(uuid4()),
                connector_key="fixture",
                source_system="fixture",
                source_mode="public_api",
                status="pending",
            )
        )
    else:
        db.begin()

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == expected_code
    _assert_unpublished(authority)
    db.rollback()


@pytest.mark.parametrize("dialect_name", ("postgresql", "mysql"))
def test_final_transaction_dialect_locking_and_fail_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dialect_name: str,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    engine = db.get_bind()
    real_publish = capture_service.publish_atomic_strict_new_locked_raw_file
    real_execute = db.execute
    real_scalars = db.scalars
    publish_calls = 0
    locks: list[str] = []
    pg_locked_selects: list[str] = []

    def switch_dialect_after_publication(
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal publish_calls
        snapshot = real_publish(*args, **kwargs)
        publish_calls += 1
        if publish_calls == 2:
            engine.dialect.name = dialect_name
        return snapshot

    def capture_locks(statement: Any, *args: Any, **kwargs: Any) -> Any:
        rendered = str(statement)
        if rendered.startswith("LOCK TABLE "):
            locks.append(rendered)
            return SimpleNamespace()
        return real_execute(statement, *args, **kwargs)

    def capture_row_locks(
        statement: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if engine.dialect.name == "postgresql":
            rendered = " ".join(
                str(
                    statement.compile(
                        dialect=postgresql.dialect(),
                    )
                ).split()
            )
            if "FOR UPDATE" in rendered:
                pg_locked_selects.append(rendered)
        return real_scalars(statement, *args, **kwargs)

    monkeypatch.setattr(
        capture_service,
        "publish_atomic_strict_new_locked_raw_file",
        switch_dialect_after_publication,
    )
    monkeypatch.setattr(db, "execute", capture_locks)
    monkeypatch.setattr(db, "scalars", capture_row_locks)
    try:
        if dialect_name == "postgresql":
            result = seal_connector_campaign_log_capture(
                db,
                capture=capture,
                runtime_stopped_at=START + timedelta(seconds=10),
                now=START + timedelta(seconds=11),
            )
            assert result.event_ids == (
                _seal_event_id(authority.run_ids["nrc_adams_aps"]),
            )
        else:
            with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
                seal_connector_campaign_log_capture(
                    db,
                    capture=capture,
                    runtime_stopped_at=START + timedelta(seconds=10),
                    now=START + timedelta(seconds=11),
                )
            assert (
                excinfo.value.code
                == "connector_campaign_log_dialect_unsupported"
            )
    finally:
        engine.dialect.name = "sqlite"

    if dialect_name == "postgresql":
        assert locks == [
            "LOCK TABLE connector_run IN EXCLUSIVE MODE",
            "LOCK TABLE connector_run_event IN EXCLUSIVE MODE",
        ]
        assert len(pg_locked_selects) == 2
        assert sum(
            "FROM connector_run " in statement
            for statement in pg_locked_selects
        ) == 1
        assert sum(
            "FROM connector_run_event " in statement
            for statement in pg_locked_selects
        ) == 1
    else:
        assert locks == []
        assert pg_locked_selects == []


def test_connection_with_external_transaction_is_rejected(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    with db.get_bind().connect() as connection:
        transaction = connection.begin()
        supplied = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
        )
        try:
            with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
                seal_connector_campaign_log_capture(
                    supplied,
                    capture=capture,
                    runtime_stopped_at=START + timedelta(seconds=10),
                    now=START + timedelta(seconds=11),
                )
            assert (
                excinfo.value.code
                == "connector_campaign_log_connection_not_clean"
            )
        finally:
            supplied.close()
            transaction.rollback()
    _assert_unpublished(authority)


def test_session_dirtied_after_publication_fails_final_recheck(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=("nrc_adams_aps",),
    )
    real_publish = capture_service.publish_atomic_strict_new_locked_raw_file
    publish_calls = 0

    def publish_then_dirty(*args: Any, **kwargs: Any) -> Any:
        nonlocal publish_calls
        snapshot = real_publish(*args, **kwargs)
        publish_calls += 1
        if publish_calls == 2:
            db.add(
                ConnectorRun(
                    connector_run_id=str(uuid4()),
                    connector_key="fixture",
                    source_system="fixture",
                    source_mode="public_api",
                    status="pending",
                )
            )
        return snapshot

    monkeypatch.setattr(
        capture_service,
        "publish_atomic_strict_new_locked_raw_file",
        publish_then_dirty,
    )
    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    assert excinfo.value.code == "connector_campaign_log_session_not_clean"
    assert publish_calls == 2
    manifest_path, seal_path = _artifact_paths(authority)
    assert manifest_path.exists()
    assert seal_path.exists()
    db.rollback()
    assert db.scalar(
        select(ConnectorRunEvent).where(
            ConnectorRunEvent.event_type
            == "campaign_log_capture_sealed"
        )
    ) is None
    db.rollback()
