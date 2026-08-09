from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass, fields, replace
from datetime import UTC, datetime, timedelta
import hashlib
import io
import importlib.util
import inspect
import os
import py_compile
import queue
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, BinaryIO, Callable, Mapping, NoReturn, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from sqlalchemy import (
    create_engine,
    event as sqlalchemy_event,
    inspect as sqlalchemy_inspect,
    select,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models import ConnectorRun, ConnectorRunEvent
from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    COMMON_GRANT_NON_AUTHORITIES,
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorCampaignEvidenceIndexV1,
    ConnectorCampaignLogCaptureRefV1,
    ConnectorEgressGrantV1,
    DualLiveCampaignDefinitionV1,
    expected_grant_rule_payloads,
)
from app.services import raw_storage_handles as raw_handles
from app.services import dual_live_runtime as dual_live_runtime_module
from app.services.connector_campaign_log_capture import (
    ConnectorCampaignLogCaptureCommitAmbiguous,
    ConnectorCampaignLogCaptureError,
    VerifiedCampaignLogCapture,
    begin_connector_campaign_log_capture,
    seal_connector_campaign_log_capture,
    verify_connector_campaign_log_capture_read_only,
)
from app.services.dual_live_runtime import (
    PIPE_STREAM_CLASSES,
    WINDOWS_MIB_TCP_STATES,
    RuntimeIdentity,
    encode_child_control_frame,
    encode_child_status_frame,
    encode_pipe_frame,
    read_runtime_records,
)
from app.services.connector_egress_arming import (
    canonical_arming_payload,
    compute_arming_fingerprint,
    compute_parent_arming_id,
)
from app.services.connector_egress_authorization import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    VerifiedEvidenceIndexChain,
    VerifiedEvidenceIndexRevision,
    canonical_json_bytes,
)


START = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
CODE_REVISION = "c" * 40
DEPENDENCY_SET_SHA256 = "d" * 64
CAMPAIGN_ID = UUID("123e4567-e89b-42d3-a456-426614174000")
CAMPAIGN_MODEL = DualLiveCampaignDefinitionV1.model_validate(
    {
        "schema_id": "project6.dual_live_campaign_definition.v1",
        "campaign_id": str(CAMPAIGN_ID),
        "code_revision": CODE_REVISION,
        "connector_keys": ["sciencebase_mcs", "nrc_adams_aps"],
        "sciencebase_target": {
            "connector_key": "sciencebase_mcs",
            "item_id": "63d1a3c6d34e06fef15006be",
            "exact_file_name": "mcs2023-germa_salient.csv",
            "locator_key": "downloadUri",
        },
        "nrc_target": {
            "connector_key": "nrc_adams_aps",
            "accession_number": "ML17123A319",
        },
        "acceptance_profile": "dual_live_to_internal_handoff_v1",
        "evidence_profile": "dual_live_evidence_v1",
        "review_policy": "security_egress_and_layer3_integrity_v1",
        "required_review_roles": ["security_egress", "layer3_integrity"],
        "execution_order": "nrc_then_sciencebase",
        "package_kinds": [
            "canonical_internal",
            "user_facing",
            "review_facing",
        ],
        "not_before": START - timedelta(hours=2),
        "expires_at": START + timedelta(hours=2),
        "non_authorities": list(CAMPAIGN_NON_AUTHORITIES),
    }
)
DEFINITION_BYTES = canonical_json_bytes(CAMPAIGN_MODEL)
DEFINITION_SHA256 = hashlib.sha256(DEFINITION_BYTES).hexdigest()
FINGERPRINT = hashlib.sha256(canonical_json_bytes(CAMPAIGN_MODEL)).hexdigest()
INDEX_SHA256 = "d" * 64
NRC_GRANT_SHA256 = "e" * 64
SCIENCEBASE_GRANT_SHA256 = "f" * 64
ARMING_NONCES = {
    "nrc_adams_aps": UUID("123e4567-e89b-42d3-a456-426614174001"),
    "sciencebase_mcs": UUID("123e4567-e89b-42d3-a456-426614174002"),
}
GOLDEN_MANIFEST_SHA256 = (
    "1a00c5e12f774ca62522b6d71f1cc8e6757981ba6d09f3980fa28d348db503b6"
)
GOLDEN_FILE_SET_HASH = (
    "350f20bf9f7be30b7d7cce11089a3df88881dac133fcd66ef9e0a77cad7b1058"
)
GOLDEN_SEAL_SHA256 = (
    "31fd99485117e068263357cd5897e59e47cca117f9fff3adea37cb6f45f27ebf"
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
    definition_model = CAMPAIGN_MODEL.model_copy(deep=True)
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


def _bind_real_evidence_index(
    authority: _AuthorityFixture,
) -> VerifiedEvidenceIndexChain:
    capture_ref = authority.verified_campaign.index_chain.head.log_captures[0]
    entries = []
    campaigns_dir = authority.evidence_root / "campaigns"
    campaigns_dir.mkdir()
    (campaigns_dir / f"{DEFINITION_SHA256}.json").write_bytes(
        DEFINITION_BYTES
    )
    grants_dir = authority.evidence_root / "grants"
    grants_dir.mkdir()
    for connector_key in ("nrc_adams_aps", "sciencebase_mcs"):
        sciencebase = connector_key == "sciencebase_mcs"
        grant_model = ConnectorEgressGrantV1.model_validate(
            {
                "schema_id": "project6.connector_egress_grant.v1",
                "grant_id": f"{connector_key}-grant",
                "connector_key": connector_key,
                "campaign_id": str(authority.campaign_id),
                "campaign_fingerprint": FINGERPRINT,
                "campaign_definition_sha256": DEFINITION_SHA256,
                "code_revision": CODE_REVISION,
                "arming_nonce": ARMING_NONCES[connector_key],
                "max_armings": 1,
                "supersedes_grant_sha256": None,
                "issued_at": START - timedelta(hours=1),
                "expires_at": START + timedelta(hours=1),
                "operator_mode": "local_loopback",
                "target": (
                    {
                        "connector_key": "sciencebase_mcs",
                        "item_id": "63d1a3c6d34e06fef15006be",
                        "exact_file_name": "mcs2023-germa_salient.csv",
                        "locator_key": "downloadUri",
                    }
                    if sciencebase
                    else {
                        "connector_key": "nrc_adams_aps",
                        "accession_number": "ML17123A319",
                    }
                ),
                "request_rules": expected_grant_rule_payloads(
                    connector_key
                ),
                "max_physical_requests": 3 if sciencebase else 2,
                "max_run_bytes": 140 * 1024 * 1024,
                "max_single_send_detection_allowance_bytes": (
                    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
                ),
                "request_timeout_seconds": 30,
                "min_request_interval_ms": 250,
                "non_authorities": (
                    COMMON_GRANT_NON_AUTHORITIES
                    if sciencebase
                    else NRC_GRANT_NON_AUTHORITIES
                ),
            }
        )
        grant_bytes = canonical_json_bytes(grant_model)
        grant_sha256 = hashlib.sha256(grant_bytes).hexdigest()
        canonical_fingerprint = hashlib.sha256(
            canonical_json_bytes(grant_model)
        ).hexdigest()
        (grants_dir / f"{grant_sha256}.json").write_bytes(grant_bytes)
        run_id = compute_parent_arming_id(
            connector_key=connector_key,
            campaign_id=str(authority.campaign_id),
            grant_sha256=grant_sha256,
            arming_nonce=grant_model.arming_nonce,
        )
        authority.run_ids[connector_key] = run_id
        current = authority.current_grants[connector_key]
        current.model = grant_model
        current.raw_sha256 = grant_sha256
        current.canonical_fingerprint = canonical_fingerprint
        history = authority.historical_grants[connector_key]
        history.model = grant_model
        history.raw_sha256 = grant_sha256
        history.canonical_fingerprint = canonical_fingerprint
        history.marker_model = SimpleNamespace(connector_run_id=run_id)
        entries.append(
            {
                "campaign_id": str(authority.campaign_id),
                "campaign_fingerprint": FINGERPRINT,
                "campaign_definition_sha256": DEFINITION_SHA256,
                "connector_key": connector_key,
                "code_revision": CODE_REVISION,
                "raw_grant_sha256": grant_sha256,
                "canonical_grant_fingerprint": canonical_fingerprint,
                "grant_relative_path": (
                    f"grants/{grant_sha256}.json"
                ),
                "consumption_marker_sha256": hashlib.sha256(
                    f"marker:{connector_key}".encode("ascii")
                ).hexdigest(),
                "consumption_marker_relative_path": (
                    f"consumed/{grant_sha256}.json"
                ),
            }
        )
    index_model = ConnectorCampaignEvidenceIndexV1.model_validate(
        {
            "schema_id": "project6.connector_campaign_evidence_index.v1",
            "revision": 1,
            "predecessor_index_sha256": None,
            "predecessor_index_relative_path": None,
            "campaigns": (
                {
                    "campaign_id": str(authority.campaign_id),
                    "campaign_fingerprint": FINGERPRINT,
                    "code_revision": CODE_REVISION,
                    "raw_definition_sha256": DEFINITION_SHA256,
                    "definition_relative_path": (
                        f"campaigns/{DEFINITION_SHA256}.json"
                    ),
                },
            ),
            "entries": tuple(entries),
            "log_captures": (capture_ref.model_dump(mode="json"),),
        }
    )
    raw_bytes = canonical_json_bytes(index_model)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    index_dir = authority.evidence_root / "indexes"
    index_dir.mkdir()
    index_path = index_dir / f"{digest}.json"
    index_path.write_bytes(raw_bytes)
    revision = VerifiedEvidenceIndexRevision(
        model=index_model,
        raw_bytes=raw_bytes,
        raw_sha256=digest,
        path=index_path,
    )
    chain = VerifiedEvidenceIndexChain(
        evidence_root=authority.evidence_root,
        head=index_model,
        head_raw_sha256=digest,
        head_path=index_path,
        revisions=(revision,),
    )
    authority.verified_campaign.index_chain = chain
    authority.verified_campaign.introduction_index_sha256 = digest
    for history in authority.historical_grants.values():
        history.index_chain = chain
        history.introduction_index_sha256 = digest
    return chain


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
        "introduction_index_sha256": (
            authority.verified_campaign.introduction_index_sha256
        ),
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
        "campaign_introduction_index_sha256": (
            authority.verified_campaign.introduction_index_sha256
        ),
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
                "campaign_introduction_index_sha256": (
                    authority.verified_campaign.introduction_index_sha256
                ),
            },
            created_at=completed_at,
        )
        db.add_all([run, terminal])
    db.commit()


def _foreign_strict_run(
    authority: _AuthorityFixture,
    run_id: str,
    *,
    same_campaign: bool,
) -> ConnectorRun:
    envelope = _arming_envelope(authority, "nrc_adams_aps")
    if not same_campaign:
        envelope = {
            **envelope,
            "campaign_id": "123e4567-e89b-42d3-a456-426614174099",
            "campaign_fingerprint": "9" * 64,
        }
        envelope["arming_fingerprint"] = compute_arming_fingerprint(envelope)
    return ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="completed",
        request_config_json={"connector_egress_arming": envelope},
        query_plan_json={},
        request_fingerprint=envelope["arming_fingerprint"],
        submission_idempotency_key=f"egress-arm:{run_id}",
        submitted_at=START + timedelta(seconds=1),
        started_at=START + timedelta(seconds=2),
        completed_at=START + timedelta(seconds=4),
        execution_lease_owner=None,
        execution_lease_token=None,
    )


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


def _connector_event_rows(db: Session) -> tuple[tuple[Any, ...], ...]:
    columns = tuple(ConnectorRunEvent.__table__.columns)
    with db.get_bind().connect() as connection:
        rows = connection.execute(
            select(ConnectorRunEvent.__table__).order_by(
                ConnectorRunEvent.connector_run_event_id
            )
        ).mappings()
        return tuple(
            tuple(row[column.key] for column in columns) for row in rows
        )


def _evidence_bytes(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    )


def _sealed_read_only_fixture(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    connector_keys: tuple[str, ...] = (
        "nrc_adams_aps",
        "sciencebase_mcs",
    ),
) -> tuple[
    _AuthorityFixture,
    VerifiedEvidenceIndexChain,
    Any,
]:
    authority = _authority_fixture(tmp_path)
    chain = _bind_real_evidence_index(authority)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(db, authority, connector_keys=connector_keys)
    sealed = seal_connector_campaign_log_capture(
        db,
        capture=capture,
        runtime_stopped_at=START + timedelta(seconds=10),
        now=START + timedelta(seconds=11),
    )
    return authority, chain, sealed


def _close_read_transaction(db: Session) -> None:
    if db.in_transaction():
        db.rollback()
    assert not db.in_transaction()


def _assert_transitively_immutable(value: Any) -> None:
    if isinstance(value, (bytes, int, str)):
        return
    if isinstance(value, tuple):
        for item in value:
            _assert_transitively_immutable(item)
        return
    if isinstance(value, MappingProxyType):
        for key, item in value.items():
            _assert_transitively_immutable(key)
            _assert_transitively_immutable(item)
        return
    pytest.fail(f"mutable verified evidence escaped: {type(value)!r}")


def _rewrite_stream_and_manifest(
    authority: _AuthorityFixture,
    sealed: Any,
) -> tuple[Any, str, str]:
    manifest_path, _ = _artifact_paths(authority)
    stream_path = manifest_path.parent / "app.jsonl"
    stream_bytes = stream_path.read_bytes() + b"rewrite"
    stream_path.write_bytes(stream_bytes)
    first = type(sealed.manifest.files[0]).model_validate(
        {
            **sealed.manifest.files[0].model_dump(mode="python"),
            "byte_count": len(stream_bytes),
            "sha256": hashlib.sha256(stream_bytes).hexdigest(),
        }
    )
    manifest = type(sealed.manifest).model_validate(
        {
            **sealed.manifest.model_dump(mode="python"),
            "files": (first, *sealed.manifest.files[1:]),
        }
    )
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    file_set_hash = hashlib.sha256(
        canonical_json_bytes(
            {
                "schema_id": "project6.connector_campaign_log_file_set.v1",
                "files": [
                    item.model_dump(mode="python")
                    for item in manifest.files
                ],
            }
        )
    ).hexdigest()
    return manifest, hashlib.sha256(manifest_bytes).hexdigest(), file_set_hash


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


class _CaptureControllerReader:
    def __init__(self) -> None:
        self._chunks: queue.Queue[bytes | None] = queue.Queue()
        self._buffer = b""
        self.closed = False

    def feed(self, content: bytes) -> None:
        self._chunks.put(content)

    def finish(self) -> None:
        self._chunks.put(None)

    def read(self, size: int) -> bytes:
        while not self._buffer:
            chunk = self._chunks.get(timeout=2)
            if chunk is None:
                return b""
            self._buffer = chunk
        result, self._buffer = self._buffer[:size], self._buffer[size:]
        return result

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.finish()


def _capture_controller_child(
    phase: str,
    events: list[str],
    *,
    proof_scope: str = "mechanical",
) -> dual_live_runtime_module._ControllerChild:
    process_boot_id = ("a" if phase == "A" else "b") * 64
    status_nonce_sha256 = ("c" if phase == "A" else "d") * 64
    control_nonce = ("e" if phase == "A" else "f") * 64
    readers = {stream: _CaptureControllerReader() for stream in PIPE_STREAM_CLASSES}
    boot_frame = encode_pipe_frame(
        canonical_json_bytes(
            {
                "control_nonce": control_nonce,
                "phase": phase,
                "process_boot_id": process_boot_id,
                "schema_id": dual_live_runtime_module.CHILD_BOOT_SCHEMA_ID,
                "status_nonce_sha256": status_nonce_sha256,
            }
        )
    )
    pre_status_frame = encode_child_status_frame(
        phase=phase,
        event="logger_census",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce_sha256,
        ordinal=1,
        payload={
            "census_point": "pre_activity",
            "handler_count": 1,
            "topology_sha256": "1" * 64,
        },
    )
    boot_sha256 = hashlib.sha256(boot_frame).hexdigest()
    pre_status_sha256 = hashlib.sha256(pre_status_frame).hexdigest()
    control_nonce_sha256 = hashlib.sha256(control_nonce.encode("ascii")).hexdigest()
    readers["app"].feed(boot_frame)
    readers["app"].feed(pre_status_frame)
    previous_proof_sha256: str | None = None
    if phase == "B":
        preproof = dual_live_runtime_module.encode_child_proof_frame(
            phase="B",
            event="guard",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce_sha256,
            ordinal=1,
            previous_record_sha256=None,
            payload={
                "boot_frame_sha256": boot_sha256,
                "control_nonce_sha256": control_nonce_sha256,
                "denied_routes": [
                    "dns",
                    "http",
                    "socket",
                    "subprocess",
                    "connector_transport",
                ],
                "network_enable_attempt_count": 0,
                "original_implementation_call_count": 0,
                "pre_activity_status_frame_sha256": pre_status_sha256,
                "proof_point": "pre_go",
                "proof_scope": proof_scope,
            },
        )
        raw_preproof = dual_live_runtime_module._read_pipe_frame(
            io.BytesIO(preproof),
            allowed_reserved_schema_ids=frozenset(
                (dual_live_runtime_module.CHILD_PROOF_SCHEMA_ID,)
            ),
        )
        assert raw_preproof is not None
        previous_proof_sha256 = cast(
            dict[str, Any],
            dual_live_runtime_module.strict_json_loads(raw_preproof),
        )["record_sha256"]
        readers["stdout"].feed(preproof)

    def send_control(frame: bytes) -> None:
        assert frame == encode_child_control_frame(
            phase=phase,
            command="GO",
            control_nonce=control_nonce,
        )
        events.append(f"go-{phase}")
        readers["app"].feed(
            encode_pipe_frame(
                canonical_json_bytes(
                    {
                        "schema_id": "project6.test_capture_app.v1",
                        "phase": phase,
                    }
                )
            )
        )
        exit_status_frame = encode_child_status_frame(
            phase=phase,
            event="logger_census",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce_sha256,
            ordinal=2,
            payload={
                "census_point": "exit",
                "handler_count": 1,
                "topology_sha256": "1" * 64,
            },
        )
        readers["app"].feed(exit_status_frame)
        common = {
            "boot_frame_sha256": boot_sha256,
            "control_frame_sha256": hashlib.sha256(frame).hexdigest(),
            "control_nonce_sha256": control_nonce_sha256,
            "exit_status_frame_sha256": hashlib.sha256(
                exit_status_frame
            ).hexdigest(),
            "pre_activity_status_frame_sha256": pre_status_sha256,
            "proof_scope": proof_scope,
        }
        if phase == "A":
            acquisitions = (
                []
                if proof_scope == "mechanical"
                else [
                    {
                        "action_codes": [
                            "derived_arming",
                            "raw_acquisition",
                            "terminal_transition",
                        ],
                        "connector_key": connector_key,
                        "connector_run_id": f"run-{connector_key}",
                        "connector_run_target_id": f"target-{connector_key}",
                        "ledger_terminal_hash": "6" * 64,
                        "raw_content_sha256": "7" * 64,
                        "terminal_transition_count": 1,
                    }
                    for connector_key in (
                        "nrc_adams_aps",
                        "sciencebase_mcs",
                    )
                ]
            )
            readers["stdout"].feed(
                dual_live_runtime_module.encode_child_proof_frame(
                    phase="A",
                    event="acquisition_boundary",
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=1,
                    previous_record_sha256=None,
                    payload={
                        **common,
                        "connector_acquisitions": acquisitions,
                        "downstream_action_count": 0,
                    },
                )
            )
        else:
            assert previous_proof_sha256 is not None
            downstream_actions = (
                []
                if proof_scope == "mechanical"
                else list(dual_live_runtime_module._PHASE_B_DOWNSTREAM_ACTIONS)
            )
            action_receipts = [
                {"action": action, "result_sha256": "9" * 64}
                for action in downstream_actions
            ]
            source_bindings = (
                []
                if proof_scope == "mechanical"
                else [
                    {
                        "analysis_plan_id": f"plan-{connector_key}",
                        "analysis_run_id": None,
                        "candidate_id": f"candidate-{connector_key}",
                        "connector_key": connector_key,
                        "connector_origin_receipt_hash": "8" * 64,
                        "connector_run_id": f"run-{connector_key}",
                        "connector_run_target_id": f"target-{connector_key}",
                        "construction_basis_hash": "a" * 64,
                        "handoff_export_envelope_ref": f"envelope-{connector_key}",
                        "output_package_ids": [
                            f"package-{connector_key}-{ordinal}"
                            for ordinal in range(3)
                        ],
                        "package_kinds": list(
                            dual_live_runtime_module._PHASE_B_PACKAGE_KINDS
                        ),
                        "package_review_preview_hash": (
                            (
                                "l3-qual-aps-package-preview-"
                                if connector_key == "nrc_adams_aps"
                                else "l3-source-intake-package-preview-"
                            )
                            + "b" * 16
                        ),
                        "package_review_submit_record_ref": f"submit-{connector_key}",
                        "pass_run_id": f"pass-{connector_key}",
                        "payload_hashes": ["c" * 64, "d" * 64, "e" * 64],
                        "prepare_record_ref": f"prepare-{connector_key}",
                        "reconciliation_record_id": f"reconcile-{connector_key}",
                        "result_review_record_ref": f"review-{connector_key}",
                        "session_id": f"session-{connector_key}",
                        "source_shape": dual_live_runtime_module._PHASE_B_SOURCE_SHAPES[
                            connector_key
                        ],
                        "source_record_id": f"source-{connector_key}",
                    }
                    for connector_key in (
                        "nrc_adams_aps",
                        "sciencebase_mcs",
                    )
                ]
            )
            downstream = dual_live_runtime_module.encode_child_proof_frame(
                phase="B",
                event="downstream_chain",
                process_boot_id=process_boot_id,
                status_nonce_sha256=status_nonce_sha256,
                ordinal=2,
                previous_record_sha256=previous_proof_sha256,
                payload={
                    **common,
                    **(
                        {"action_receipts": action_receipts}
                        if proof_scope == "production"
                        else {}
                    ),
                    "downstream_actions": downstream_actions,
                    "source_bindings": source_bindings,
                    "terminal_boundary": (
                        "mechanical_complete"
                        if proof_scope == "mechanical"
                        else "handoff_prepared"
                    ),
                },
            )
            raw_downstream = dual_live_runtime_module._read_pipe_frame(
                io.BytesIO(downstream),
                allowed_reserved_schema_ids=frozenset(
                    (dual_live_runtime_module.CHILD_PROOF_SCHEMA_ID,)
                ),
            )
            assert raw_downstream is not None
            downstream_sha256 = cast(
                dict[str, Any],
                dual_live_runtime_module.strict_json_loads(raw_downstream),
            )["record_sha256"]
            readers["stdout"].feed(downstream)
            readers["stdout"].feed(
                dual_live_runtime_module.encode_child_proof_frame(
                    phase="B",
                    event="guard",
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=3,
                    previous_record_sha256=downstream_sha256,
                    payload={
                        **common,
                        "denied_routes": [
                            "dns",
                            "http",
                            "socket",
                            "subprocess",
                            "connector_transport",
                        ],
                        "network_enable_attempt_count": 0,
                        "original_implementation_call_count": 0,
                        "proof_point": "exit",
                    },
                )
            )
        for reader in readers.values():
            reader.finish()

    def wait(_timeout: float) -> int:
        events.append(f"wait-{phase}")
        return 0

    def stop() -> None:
        events.append(f"stop-{phase}")

    return dual_live_runtime_module._ControllerChild(
        process_boot_id=process_boot_id,
        process_creation_identity_sha256="2" * 64,
        executable_sha256="3" * 64,
        job_policy_sha256="4" * 64,
        status_nonce_sha256=status_nonce_sha256,
        control_nonce=control_nonce,
        readers=cast(Mapping[str, BinaryIO], readers),
        send_control=send_control,
        wait=wait,
        stop=stop,
    )


def test_child_status_decoder_rejects_bool_ordinal() -> None:
    process_boot_id = "a" * 64
    status_nonce = "b" * 64
    frame = encode_child_status_frame(
        phase="A",
        event="logger_census",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=1,
        payload={
            "census_point": "pre_activity",
            "handler_count": 1,
            "topology_sha256": "c" * 64,
        },
    )
    payload = dual_live_runtime_module._read_pipe_frame(
        io.BytesIO(frame),
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime_module.CHILD_STATUS_SCHEMA_ID,)
        ),
    )
    assert payload is not None
    value = cast(
        dict[str, Any],
        dual_live_runtime_module.strict_json_loads(payload),
    )
    value["ordinal"] = True

    with pytest.raises(
        dual_live_runtime_module.DualLiveRuntimeError,
        match="dual_live_child_status_invalid",
    ):
        dual_live_runtime_module.decode_child_status_frame(
            canonical_json_bytes(value),
            expected_phase="A",
            expected_process_boot_id=process_boot_id,
            expected_status_nonce_sha256=status_nonce,
            expected_ordinal=1,
        )


def test_child_proof_codec_binds_exact_chain_and_owned_identities() -> None:
    process_boot_id = "a" * 64
    status_nonce = "b" * 64
    control_nonce_sha256 = "c" * 64
    first_payload = {
        "boot_frame_sha256": "d" * 64,
        "control_nonce_sha256": control_nonce_sha256,
        "denied_routes": [
            "dns",
            "http",
            "socket",
            "subprocess",
            "connector_transport",
        ],
        "network_enable_attempt_count": 0,
        "original_implementation_call_count": 0,
        "pre_activity_status_frame_sha256": "e" * 64,
        "proof_point": "pre_go",
        "proof_scope": "mechanical",
    }
    first_frame = dual_live_runtime_module.encode_child_proof_frame(
        phase="B",
        event="guard",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=1,
        previous_record_sha256=None,
        payload=first_payload,
    )
    first_raw = dual_live_runtime_module._read_pipe_frame(
        io.BytesIO(first_frame),
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime_module.CHILD_PROOF_SCHEMA_ID,)
        ),
    )
    assert first_raw is not None
    first = dual_live_runtime_module.decode_child_proof_frame(
        first_raw,
        expected_phase="B",
        expected_process_boot_id=process_boot_id,
        expected_status_nonce_sha256=status_nonce,
        expected_ordinal=1,
        expected_previous_record_sha256=None,
        expected_proof_scope="mechanical",
    )
    for count_field in (
        "network_enable_attempt_count",
        "original_implementation_call_count",
    ):
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError,
            match="dual_live_child_proof_invalid",
        ):
            dual_live_runtime_module.encode_child_proof_frame(
                phase="B",
                event="guard",
                process_boot_id=process_boot_id,
                status_nonce_sha256=status_nonce,
                ordinal=1,
                previous_record_sha256=None,
                payload={**first_payload, count_field: False},
            )
    with pytest.raises(
        dual_live_runtime_module.DualLiveRuntimeError,
        match="dual_live_child_proof_invalid",
    ):
        dual_live_runtime_module.encode_child_proof_frame(
            phase="B",
            event="guard",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce,
            ordinal=1,
            previous_record_sha256=None,
            payload={
                **first_payload,
                "boot_frame_sha256": int("1" * 64),
            },
        )
    bool_ordinal = {**first, "ordinal": True}
    bool_ordinal["record_sha256"] = dual_live_runtime_module._record_hash(
        bool_ordinal
    )
    with pytest.raises(
        dual_live_runtime_module.DualLiveRuntimeError,
        match="dual_live_child_proof_invalid",
    ):
        dual_live_runtime_module.decode_child_proof_frame(
            canonical_json_bytes(bool_ordinal),
            expected_phase="B",
            expected_process_boot_id=process_boot_id,
            expected_status_nonce_sha256=status_nonce,
            expected_ordinal=1,
            expected_previous_record_sha256=None,
            expected_proof_scope="mechanical",
        )
    second_frame = dual_live_runtime_module.encode_child_proof_frame(
        phase="B",
        event="downstream_chain",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=2,
        previous_record_sha256=first["record_sha256"],
        payload={
            "boot_frame_sha256": "d" * 64,
            "control_frame_sha256": "f" * 64,
            "control_nonce_sha256": control_nonce_sha256,
            "downstream_actions": [],
            "exit_status_frame_sha256": "1" * 64,
            "pre_activity_status_frame_sha256": "e" * 64,
            "proof_scope": "mechanical",
            "source_bindings": [],
            "terminal_boundary": "mechanical_complete",
        },
    )
    second_raw = dual_live_runtime_module._read_pipe_frame(
        io.BytesIO(second_frame),
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime_module.CHILD_PROOF_SCHEMA_ID,)
        ),
    )
    assert second_raw is not None
    second = dual_live_runtime_module.decode_child_proof_frame(
        second_raw,
        expected_phase="B",
        expected_process_boot_id=process_boot_id,
        expected_status_nonce_sha256=status_nonce,
        expected_ordinal=2,
        expected_previous_record_sha256=first["record_sha256"],
        expected_proof_scope="mechanical",
    )
    assert second["previous_record_sha256"] == first["record_sha256"]
    tampered = {**second, "process_boot_id": "2" * 64}
    with pytest.raises(
        dual_live_runtime_module.DualLiveRuntimeError,
        match="dual_live_child_proof_invalid",
    ):
        dual_live_runtime_module.decode_child_proof_frame(
            canonical_json_bytes(tampered),
            expected_phase="B",
            expected_process_boot_id=process_boot_id,
            expected_status_nonce_sha256=status_nonce,
            expected_ordinal=2,
            expected_previous_record_sha256=first["record_sha256"],
            expected_proof_scope="mechanical",
        )


def test_phase_b_production_proof_requires_exact_two_connector_bindings() -> None:
    def binding(connector_key: str) -> dict[str, Any]:
        return {
            "analysis_plan_id": f"plan-{connector_key}",
            "analysis_run_id": None,
            "candidate_id": f"candidate-{connector_key}",
            "connector_key": connector_key,
            "connector_origin_receipt_hash": "1" * 64,
            "connector_run_id": f"run-{connector_key}",
            "connector_run_target_id": f"target-{connector_key}",
            "construction_basis_hash": "2" * 64,
            "handoff_export_envelope_ref": f"envelope-{connector_key}",
            "output_package_ids": [
                f"package-{connector_key}-{ordinal}" for ordinal in range(3)
            ],
            "package_kinds": list(
                dual_live_runtime_module._PHASE_B_PACKAGE_KINDS
            ),
            "package_review_preview_hash": (
                (
                    "l3-qual-aps-package-preview-"
                    if connector_key == "nrc_adams_aps"
                    else "l3-source-intake-package-preview-"
                )
                + "3" * 16
            ),
            "package_review_submit_record_ref": f"submit-{connector_key}",
            "pass_run_id": f"pass-{connector_key}",
            "payload_hashes": ["4" * 64, "5" * 64, "6" * 64],
            "prepare_record_ref": f"prepare-{connector_key}",
            "reconciliation_record_id": f"reconcile-{connector_key}",
            "result_review_record_ref": f"review-{connector_key}",
            "session_id": f"session-{connector_key}",
            "source_shape": dual_live_runtime_module._PHASE_B_SOURCE_SHAPES[
                connector_key
            ],
            "source_record_id": f"source-{connector_key}",
        }

    actions = list(dual_live_runtime_module._PHASE_B_DOWNSTREAM_ACTIONS)
    nrc = binding("nrc_adams_aps")
    sciencebase = binding("sciencebase_mcs")
    payload = {
        "action_receipts": [
            {"action": action, "result_sha256": "7" * 64}
            for action in actions
        ],
        "boot_frame_sha256": "8" * 64,
        "control_frame_sha256": "9" * 64,
        "control_nonce_sha256": "a" * 64,
        "downstream_actions": actions,
        "exit_status_frame_sha256": "b" * 64,
        "pre_activity_status_frame_sha256": "c" * 64,
        "proof_scope": "production",
        "source_bindings": [nrc, sciencebase],
        "terminal_boundary": "handoff_prepared",
    }

    assert dual_live_runtime_module._validate_child_proof_payload(
        phase="B",
        event="downstream_chain",
        ordinal=2,
        payload=payload,
        expected_proof_scope="production",
    ) == payload

    invalid_bindings = (
        [nrc],
        [nrc, nrc],
        [sciencebase, nrc],
        [nrc, sciencebase, deepcopy(sciencebase)],
    )
    for bindings in invalid_bindings:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError,
            match="dual_live_child_proof_invalid",
        ):
            dual_live_runtime_module._validate_child_proof_payload(
                phase="B",
                event="downstream_chain",
                ordinal=2,
                payload={**payload, "source_bindings": bindings},
                expected_proof_scope="production",
            )

@pytest.mark.parametrize("at_or_after_bound", (False, True))
def test_controller_accepts_before_bound_and_rejects_at_or_after_bound(
    at_or_after_bound: bool,
) -> None:
    events: list[str] = []
    writers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
    identity = RuntimeIdentity(
        runtime_instance_id=str(uuid4()),
        wrapper_nonce_sha256="1" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="2" * 64,
        interpreter_image_sha256="3" * 64,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
        root_mutex_identity_sha256="4" * 64,
        campaign_mutex_identity_sha256="5" * 64,
    )

    def create(phase: str) -> dual_live_runtime_module._ControllerChild:
        child = _capture_controller_child(phase, events)
        calls = 0

        def wait(timeout: float) -> int:
            nonlocal calls
            calls += 1
            events.append(f"wait-{phase}-{calls}")
            if phase == "A" and calls == 1:
                if at_or_after_bound:
                    time.sleep(0.202)
                else:
                    time.sleep(0.005)
            return 0

        return replace(child, wait=wait)

    zero_states = {state: 0 for state in WINDOWS_MIB_TCP_STATES}

    def quiesce(
        _phase: str,
        _child: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        return (
            {
                "tcp4_state_counts": zero_states,
                "tcp6_state_counts": dict(zero_states),
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "7" * 64,
                "stable": True,
            },
            {"active_process_count": 0, "process_list_sha256": "8" * 64},
        )

    def run() -> object:
        return dual_live_runtime_module._run_two_phase_controller(
            identity=identity,
            runtime_start_payload={
                "code_revision": identity.code_revision,
                "wrapper_image_sha256": identity.wrapper_image_sha256,
                "interpreter_image_sha256": identity.interpreter_image_sha256,
                "dependency_set_sha256": identity.dependency_set_sha256,
                "phase_timeout_contract": _phase_timeout_contract(),
                "mutex_identity_sha256": "6" * 64,
            },
            writers=writers,
            create_phase_a=lambda: create("A"),
            create_phase_b=lambda: create("B"),
            quiesce_phase=quiesce,
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "9" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: "sealed",
            timeout_seconds={"A": 0.2, "B": 0.2},
        )

    if at_or_after_bound:
        with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
            run()
        assert exc.value.code == "dual_live_phase_exit_timeout"
        assert "go-A" in events
        assert "go-B" not in events
    else:
        assert run() == "sealed"
        assert "go-A" in events
        assert "go-B" in events


@pytest.mark.parametrize(
    ("exit_phase", "exit_code", "expected_code"),
    (
        ("A", 24, "dual_live_phase_failed"),
        ("B", 25, "dual_live_phase_failed"),
        ("B", 24, "dual_live_phase_failed"),
    ),
)
def test_controller_projects_all_nonzero_child_exits_as_phase_failure(
    exit_phase: str,
    exit_code: int,
    expected_code: str,
) -> None:
    events: list[str] = []
    writers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
    identity = RuntimeIdentity(
        runtime_instance_id=str(uuid4()),
        wrapper_nonce_sha256="1" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="2" * 64,
        interpreter_image_sha256="3" * 64,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
        root_mutex_identity_sha256="4" * 64,
        campaign_mutex_identity_sha256="5" * 64,
    )

    def create(phase: str) -> dual_live_runtime_module._ControllerChild:
        child = _capture_controller_child(phase, events)
        return replace(
            child,
            wait=lambda _timeout: exit_code if phase == exit_phase else 0,
        )

    zero_states = {state: 0 for state in WINDOWS_MIB_TCP_STATES}

    def quiesce(
        phase: str,
        _child: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        events.append(f"quiesce-{phase}")
        return (
            {
                "tcp4_state_counts": zero_states,
                "tcp6_state_counts": dict(zero_states),
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "7" * 64,
                "stable": True,
            },
            {"active_process_count": 0, "process_list_sha256": "8" * 64},
        )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=identity,
            runtime_start_payload={
                "code_revision": identity.code_revision,
                "wrapper_image_sha256": identity.wrapper_image_sha256,
                "interpreter_image_sha256": identity.interpreter_image_sha256,
                "dependency_set_sha256": identity.dependency_set_sha256,
                "phase_timeout_contract": _phase_timeout_contract(),
                "mutex_identity_sha256": "6" * 64,
            },
            writers=writers,
            create_phase_a=lambda: create("A"),
            create_phase_b=lambda: create("B"),
            quiesce_phase=quiesce,
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "9" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: pytest.fail("owner boundary must not seal"),
            timeout_seconds={"A": 0.2, "B": 0.2},
        )

    assert exc.value.code == expected_code
    assert f"stop-{exit_phase}" in events
    assert f"quiesce-{exit_phase}" in events
    if exit_phase == "A":
        assert "go-B" not in events
    else:
        assert "go-B" in events


def test_controller_never_clears_or_creates_b_before_quiescence_proof() -> None:
    events: list[str] = []
    writers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
    identity = RuntimeIdentity(
        runtime_instance_id=str(uuid4()),
        wrapper_nonce_sha256="1" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="2" * 64,
        interpreter_image_sha256="3" * 64,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
        root_mutex_identity_sha256="4" * 64,
        campaign_mutex_identity_sha256="5" * 64,
    )

    def create(phase: str) -> dual_live_runtime_module._ControllerChild:
        events.append(f"create-{phase}")
        return _capture_controller_child(phase, events)

    def quiesce(phase: str, _child: object) -> NoReturn:
        events.append(f"quiesce-{phase}")
        raise RuntimeError("fixture quiescence failure")

    def clear_authority(
        phase: str,
        _child: object,
    ) -> dict[str, object]:
        events.append(f"authority-{phase}")
        return {
            "authority_posture_sha256": "9" * 64,
            "all_required_absent": True,
        }

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=identity,
            runtime_start_payload={
                "code_revision": identity.code_revision,
                "wrapper_image_sha256": identity.wrapper_image_sha256,
                "interpreter_image_sha256": identity.interpreter_image_sha256,
                "dependency_set_sha256": identity.dependency_set_sha256,
                "phase_timeout_contract": _phase_timeout_contract(),
                "mutex_identity_sha256": "6" * 64,
            },
            writers=writers,
            create_phase_a=lambda: create("A"),
            create_phase_b=lambda: create("B"),
            quiesce_phase=quiesce,
            clear_authority=clear_authority,
            http_frame_validator=lambda _payload: None,
            seal=lambda: pytest.fail("failed quiescence must not seal"),
            timeout_seconds=2,
        )

    assert exc.value.code == "dual_live_quiescence_failed"
    assert "quiesce-A" in events
    assert "authority-A" not in events
    assert "create-B" not in events


def test_controller_blocks_b_when_measured_authority_is_retained() -> None:
    events: list[str] = []
    writers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
    identity = RuntimeIdentity(
        runtime_instance_id=str(uuid4()),
        wrapper_nonce_sha256="1" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="2" * 64,
        interpreter_image_sha256="3" * 64,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
        root_mutex_identity_sha256="4" * 64,
        campaign_mutex_identity_sha256="5" * 64,
    )
    zero_states = {state: 0 for state in WINDOWS_MIB_TCP_STATES}

    def create(phase: str) -> dual_live_runtime_module._ControllerChild:
        events.append(f"create-{phase}")
        return _capture_controller_child(phase, events)

    def quiesce(
        phase: str,
        _child: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        events.append(f"quiesce-{phase}")
        return (
            {
                "tcp4_state_counts": zero_states,
                "tcp6_state_counts": dict(zero_states),
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "7" * 64,
                "stable": True,
            },
            {"active_process_count": 0, "process_list_sha256": "8" * 64},
        )

    def retained_authority(
        phase: str,
        _child: object,
    ) -> dict[str, object]:
        events.append(f"authority-{phase}")
        return {
            "authority_posture_sha256": "9" * 64,
            "all_required_absent": False,
        }

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=identity,
            runtime_start_payload={
                "code_revision": identity.code_revision,
                "wrapper_image_sha256": identity.wrapper_image_sha256,
                "interpreter_image_sha256": identity.interpreter_image_sha256,
                "dependency_set_sha256": identity.dependency_set_sha256,
                "phase_timeout_contract": _phase_timeout_contract(),
                "mutex_identity_sha256": "6" * 64,
            },
            writers=writers,
            create_phase_a=lambda: create("A"),
            create_phase_b=lambda: create("B"),
            quiesce_phase=quiesce,
            clear_authority=retained_authority,
            http_frame_validator=lambda _payload: None,
            seal=lambda: pytest.fail("retained authority must not seal"),
            timeout_seconds=2,
        )

    assert exc.value.code == "dual_live_authority_clear_failed"
    assert events.index("quiesce-A") < events.index("authority-A")
    assert "create-B" not in events


class _CaptureOwnedPhaseProcess:
    def __init__(self, phase: str, events: list[str]) -> None:
        self.phase = phase
        self.events = events
        self._child: dual_live_runtime_module._ControllerChild = (
            _capture_controller_child(phase, events, proof_scope="production")
        )
        self.process_boot_id = self._child.process_boot_id
        self.process_creation_identity_sha256 = (
            self._child.process_creation_identity_sha256
        )
        self.executable_sha256 = self._child.executable_sha256
        self.job_policy_sha256 = self._child.job_policy_sha256
        self.status_nonce_sha256 = self._child.status_nonce_sha256
        self.control_nonce = self._child.control_nonce
        self.readers = self._child.readers
        self._closed = False
        self._authority_environment_names = (
            frozenset(
                dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
            )
            if phase == "A"
            else frozenset()
        )
        self._authority_revoked = False
        self._stopped = False
        self._quiesced = False
        self._retain_authority_coordinates = False

    def send_control(self, frame: bytes) -> None:
        self._child.send_control(frame)

    def poll_exit(self, timeout: float) -> int | None:
        return self._child.wait(timeout)

    def revoke_before_stop(self, reason: str) -> None:
        self.events.append(f"revoke-{self.phase}-{reason}")
        if self.phase == "A":
            self._authority_revoked = True

    def stop(self) -> None:
        if self.phase == "A" and not self._authority_revoked:
            self.revoke_before_stop("owned_stop")
        self._child.stop()
        self._stopped = True

    def quiesce_and_close(
        self,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self.events.append(f"quiesce-{self.phase}")
        self._quiesced = True
        zero_states = {state: 0 for state in WINDOWS_MIB_TCP_STATES}
        return (
            {
                "tcp4_state_counts": zero_states,
                "tcp6_state_counts": dict(zero_states),
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "7" * 64,
                "stable": True,
            },
            {"active_process_count": 0, "process_list_sha256": "8" * 64},
        )

    def authority_cleared_payload(self) -> dict[str, object]:
        self.events.append(f"authority-{self.phase}")
        return {
            "authority_posture_sha256": "9" * 64,
            "all_required_absent": True,
        }

    def clear_authority_coordinates(self) -> None:
        if (
            self.phase != "A"
            or not self._authority_revoked
            or not self._stopped
            or not self._quiesced
        ):
            raise AssertionError("authority cleared before fake quiescence")
        self.events.append(f"authority-{self.phase}")
        if not self._retain_authority_coordinates:
            self._authority_environment_names = frozenset()

    def discard_authority_coordinates(self) -> None:
        self._authority_environment_names = frozenset()

    def authority_coordinate_posture(self) -> dict[str, object]:
        return {
            "retained_environment_names": tuple(
                sorted(self._authority_environment_names)
            ),
            "revoked": self._authority_revoked,
            "stopped": self._stopped and self._quiesced,
        }

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.events.append(f"close-{self.phase}")
        for reader in self.readers.values():
            reader.close()


def _measured_authority_context(
    process: _CaptureOwnedPhaseProcess,
) -> dual_live_runtime_module._ProductionOwnedControllerContext:
    context = object.__new__(
        dual_live_runtime_module._ProductionOwnedControllerContext
    )
    context._lock = dual_live_runtime_module.threading.Lock()
    context._active_process = None
    context._quiescing_process = None
    context._owned_processes = [("A", process)]
    context._quiesced_process_ids = {id(process)}
    context._closed_process_ids = {id(process)}
    context._phase_environments = {
        "A": MappingProxyType(
            {
                name: "retained-fixture"
                for name in (
                    dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
                )
            }
        ),
        "B": MappingProxyType(
            {
                "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
                "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
            }
        ),
    }
    context._retired_quiesced_phases = set()
    return context


def _quiesced_authority_process(
    events: list[str],
) -> _CaptureOwnedPhaseProcess:
    process = _CaptureOwnedPhaseProcess("A", events)
    process._authority_revoked = True
    process._stopped = True
    process._quiesced = True
    return process


def test_measured_authority_clearance_releases_all_parent_context_process_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config
    from app.services import dual_live_windows

    assert (
        dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
        == dual_live_windows.OWNED_PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
    )
    for name in dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "retained-fixture")
    settings = cast(Any, _producer_fake_settings(tmp_path))
    monkeypatch.setattr(config, "settings", settings)
    process = _quiesced_authority_process([])
    context = _measured_authority_context(process)

    payload = context._authority_payload("A", process._child)

    assert payload == {
        "authority_posture_sha256": (
            dual_live_runtime_module.AUTHORITY_CLEARED_POSTURE_SHA256
        ),
        "all_required_absent": True,
    }
    assert all(
        name.upper()
        not in dual_live_runtime_module._PHASE_A_AUTHORITY_ENVIRONMENT
        for name in os.environ
    )
    assert context._phase_environments is not None
    assert context._phase_environments["A"] is None
    assert context._phase_environments["B"] == {
        "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
    }
    assert context._owned_processes == []
    assert context._quiesced_process_ids == set()
    assert context._closed_process_ids == set()
    assert process.authority_coordinate_posture() == {
        "retained_environment_names": (),
        "revoked": True,
        "stopped": True,
    }
    assert settings.nrc_adams_subscription_key == ""
    assert settings.connector_campaign_definition_path is None
    assert settings.connector_campaign_definition_sha256 is None
    assert settings.connector_nrc_aps_grant_path is None
    assert settings.connector_nrc_aps_grant_sha256 is None
    assert settings.connector_sciencebase_grant_path is None
    assert settings.connector_sciencebase_grant_sha256 is None
    assert settings.connector_live_egress_enabled is False
    assert settings.connector_live_egress_exclusive_proof_mode is False


@pytest.mark.parametrize(
    "retained_name",
    dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES,
)
def test_each_retained_parent_authority_coordinate_fails_closed(
    retained_name: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config

    for name in dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "retained-fixture")
    monkeypatch.setattr(config, "settings", _producer_fake_settings(tmp_path))
    process = _quiesced_authority_process([])
    context = _measured_authority_context(process)
    canonical_clear = (
        dual_live_runtime_module._clear_parent_authority_environment
    )

    def retain_one() -> list[BaseException]:
        failures = canonical_clear()
        monkeypatch.setenv(retained_name, "still-retained")
        return failures

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_clear_parent_authority_environment",
        retain_one,
    )

    payload = context._authority_payload("A", process._child)

    assert payload["all_required_absent"] is False
    assert (
        payload["authority_posture_sha256"]
        != dual_live_runtime_module.AUTHORITY_CLEARED_POSTURE_SHA256
    )
    assert context._phase_environments is not None
    assert context._phase_environments["A"] is None
    assert context._owned_processes == []


def test_retained_process_authority_coordinate_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config

    for name in dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "retained-fixture")
    monkeypatch.setattr(config, "settings", _producer_fake_settings(tmp_path))
    process = _quiesced_authority_process([])
    context = _measured_authority_context(process)
    process._retain_authority_coordinates = True

    payload = context._authority_payload("A", process._child)

    assert payload["all_required_absent"] is False
    assert context._phase_environments is not None
    assert context._phase_environments["A"] is None
    assert context._owned_processes == []


def test_retained_shared_settings_key_blocks_authority_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    class _StickySettings:
        _sticky: bool
        nrc_adams_subscription_key: str

        def __init__(self) -> None:
            object.__setattr__(self, "_sticky", False)
            for attribute, cleared in (
                dual_live_runtime_module._PHASE_A_SETTINGS_AUTHORITY_COORDINATES
            ):
                object.__setattr__(
                    self,
                    attribute,
                    "retained-fixture"
                    if cleared is None or cleared == ""
                    else True,
                )
            object.__setattr__(self, "_sticky", True)

        def __setattr__(self, name: str, value: object) -> None:
            if self._sticky and name == "nrc_adams_subscription_key":
                raise RuntimeError("fixture retained key")
            object.__setattr__(self, name, value)

    for name in dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "retained-fixture")
    settings = _StickySettings()
    monkeypatch.setattr(config, "settings", settings)
    process = _quiesced_authority_process([])
    context = _measured_authority_context(process)

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        context._authority_payload("A", process._child)

    assert exc.value.code == "dual_live_owned_authority_invalid"
    assert settings.nrc_adams_subscription_key == "retained-fixture"
    assert context._phase_environments is not None
    assert context._phase_environments["A"] is None
    assert context._owned_processes == []


def test_failed_quiescence_cleanup_discards_authority_without_attestation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config

    for name in dual_live_runtime_module.PHASE_A_AUTHORITY_ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "retained-fixture")
    settings = cast(Any, _producer_fake_settings(tmp_path))
    monkeypatch.setattr(config, "settings", settings)
    events: list[str] = []
    process = _CaptureOwnedPhaseProcess("A", events)
    context = _measured_authority_context(process)
    context._active_process = process
    context._quiesced_process_ids = set()
    context._closed_process_ids = set()

    assert context._discard_phase_a_authority() is None
    assert context._close_all_processes() is None

    assert all(
        name.upper()
        not in dual_live_runtime_module._PHASE_A_AUTHORITY_ENVIRONMENT
        for name in os.environ
    )
    assert settings.nrc_adams_subscription_key == ""
    assert context._phase_environments is not None
    assert context._phase_environments["A"] is None
    assert context._owned_processes == []
    assert process.authority_coordinate_posture()[
        "retained_environment_names"
    ] == ()
    assert not any(event.startswith("authority-") for event in events)


@pytest.mark.parametrize(
    "connector_keys",
    (
        ("nrc_adams_aps",),
        ("nrc_adams_aps", "sciencebase_mcs"),
    ),
    ids=("nrc-only", "two-run"),
)
def test_read_only_capture_verifier_rehashes_without_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    connector_keys: tuple[str, ...],
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority, chain, sealed = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=connector_keys,
    )
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)
    _close_read_transaction(db)

    def forbidden_write(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("read-only verifier reached a write/current path")

    for name in (
        "begin_connector_campaign_log_capture",
        "seal_connector_campaign_log_capture",
        "publish_atomic_strict_new_locked_raw_file",
        "_current_authority",
        "_historical_authority",
        "_managed_paths",
        "_forbidden_path",
    ):
        monkeypatch.setattr(capture_service, name, forbidden_write)

    verified = verify_connector_campaign_log_capture_read_only(
        db,
        chain,
        str(authority.campaign_id),
        FINGERPRINT,
    )

    assert not db.in_transaction()
    assert isinstance(verified, VerifiedCampaignLogCapture)
    assert verified.manifest_bytes == canonical_json_bytes(sealed.manifest)
    assert verified.manifest_sha256 == sealed.manifest_sha256
    assert verified.file_set_hash == sealed.file_set_hash
    assert verified.seal_bytes == canonical_json_bytes(sealed.seal)
    assert verified.seal_sha256 == sealed.seal_sha256
    assert verified.seal_event_ids == sealed.event_ids
    expected_paths = tuple(
        item.relative_path for item in sealed.manifest.files
    ) + (
        f"logs/{FINGERPRINT}/manifest.json",
        f"log-seals/{FINGERPRINT}.json",
    )
    assert tuple(verified.stream_bytes) == expected_paths[:4]
    assert tuple(item[0] for item in verified.stable_snapshot) == expected_paths
    assert verified.stream_bytes[expected_paths[0]] == b'{"app":1}\n'
    with pytest.raises(TypeError):
        verified.stream_bytes[expected_paths[0]] = b"changed"  # type: ignore[index]
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before
    assert tuple(
        inspect.signature(
            verify_connector_campaign_log_capture_read_only
        ).parameters
    ) == (
        "db",
        "chain",
        "campaign_id",
        "expected_campaign_fingerprint",
    )


def test_read_only_capture_result_is_transitively_immutable(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority, chain, _ = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    _close_read_transaction(db)

    verified = verify_connector_campaign_log_capture_read_only(
        db,
        chain,
        str(authority.campaign_id),
        FINGERPRINT,
    )

    assert not hasattr(verified, "manifest")
    assert not hasattr(verified, "seal")
    for field in fields(verified):
        _assert_transitively_immutable(getattr(verified, field.name))
    with pytest.raises(FrozenInstanceError):
        verified.manifest_bytes = b"changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        verified.manifest_bytes[0] = 0  # type: ignore[index]
    first_path = next(iter(verified.stream_bytes))
    with pytest.raises(TypeError):
        verified.stream_bytes[first_path] = b"changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        verified.stream_bytes[first_path][0] = 0  # type: ignore[index]
    with pytest.raises(TypeError):
        verified.stable_snapshot[0][0] = "changed"  # type: ignore[index]


def test_read_only_capture_verifier_isolates_caller_identity_map(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority, chain, _ = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    run = db.get(ConnectorRun, authority.run_ids["nrc_adams_aps"])
    assert run is not None
    db.commit()
    assert not db.in_transaction()
    caller_state = sqlalchemy_inspect(run)
    caller_key = caller_state.key
    assert caller_key is not None
    before_keys = tuple(run.__dict__)
    before_values = deepcopy(
        {
            key: value
            for key, value in run.__dict__.items()
            if key != "_sa_instance_state"
        }
    )
    before_state_object = run.__dict__["_sa_instance_state"]
    before_identity = caller_state.identity
    before_expired = frozenset(caller_state.expired_attributes)
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)

    def forbidden_caller_query(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("verifier queried or transacted through caller session")

    monkeypatch.setattr(db, "begin", forbidden_caller_query)
    monkeypatch.setattr(db, "scalars", forbidden_caller_query)
    monkeypatch.setattr(db, "execute", forbidden_caller_query)

    verify_connector_campaign_log_capture_read_only(
        db,
        chain,
        str(authority.campaign_id),
        FINGERPRINT,
    )

    after_state = sqlalchemy_inspect(run)
    after_values = {
        key: value
        for key, value in run.__dict__.items()
        if key != "_sa_instance_state"
    }
    assert not db.in_transaction()
    assert db.identity_map[caller_key] is run
    assert after_state is caller_state
    assert run.__dict__["_sa_instance_state"] is before_state_object
    assert tuple(run.__dict__) == before_keys
    assert after_values == before_values
    assert after_state.identity == before_identity
    assert frozenset(after_state.expired_attributes) == before_expired
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before


@pytest.mark.parametrize(
    "case",
    (
        "deterministic-plus-one",
        "same-campaign-foreign",
        "other-campaign-foreign",
    ),
)
def test_read_only_capture_verifier_enforces_exact_same_campaign_run_set(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    authority, chain, sealed = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    if case == "deterministic-plus-one":
        _insert_terminal_runs(
            db,
            authority,
            connector_keys=("sciencebase_mcs",),
        )
    else:
        envelope = _arming_envelope(authority, "nrc_adams_aps")
        if case == "other-campaign-foreign":
            envelope = {
                **envelope,
                "campaign_id": "123e4567-e89b-42d3-a456-426614174099",
                "campaign_fingerprint": "9" * 64,
            }
            envelope["arming_fingerprint"] = compute_arming_fingerprint(
                envelope
            )
        db.add(
            ConnectorRun(
                connector_run_id="foreign-strict-run",
                connector_key="nrc_adams_aps",
                source_system="nrc_adams",
                source_mode="strict_live_egress",
                status="completed",
                request_config_json={
                    "connector_egress_arming": envelope,
                },
                query_plan_json={},
                request_fingerprint=envelope["arming_fingerprint"],
                submission_idempotency_key="egress-arm:foreign",
                submitted_at=START + timedelta(seconds=1),
                started_at=START + timedelta(seconds=2),
                completed_at=START + timedelta(seconds=3),
                execution_lease_owner=None,
                execution_lease_token=None,
            )
        )
        db.commit()
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)
    _close_read_transaction(db)
    run_queries: list[tuple[str, tuple[Any, ...]]] = []

    def capture_run_query(
        _connection: Any,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        normalized = " ".join(statement.lower().split())
        if " from connector_run " in normalized:
            run_queries.append((normalized, tuple(parameters)))

    bind = db.get_bind()
    sqlalchemy_event.listen(bind, "before_cursor_execute", capture_run_query)
    try:
        if case != "other-campaign-foreign":
            with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
                verify_connector_campaign_log_capture_read_only(
                    db,
                    chain,
                    str(authority.campaign_id),
                    FINGERPRINT,
                )
            assert (
                excinfo.value.code
                == "connector_campaign_log_read_run_set_invalid"
            )
        else:
            verified = verify_connector_campaign_log_capture_read_only(
                db,
                chain,
                str(authority.campaign_id),
                FINGERPRINT,
            )
            assert verified.seal_event_ids == sealed.event_ids
    finally:
        sqlalchemy_event.remove(bind, "before_cursor_execute", capture_run_query)
    assert len(run_queries) == (
        2 if case == "other-campaign-foreign" else 1
    )
    for statement, parameters in run_queries:
        assert "connector_run.source_mode =" in statement
        assert "connector_run.request_config_json" in statement
        assert " limit " in statement
        assert "strict_live_egress" in parameters
        assert str(authority.campaign_id) in parameters
        assert FINGERPRINT in parameters
        assert any("campaign_id" in str(value) for value in parameters)
        assert any("campaign_fingerprint" in str(value) for value in parameters)
        assert len(sealed.seal.connector_run_ids) + 1 in parameters
    assert not db.in_transaction()
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before


def test_exact_child_bounds_protected_directory_at_max_plus_one(
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    parent = tmp_path / "bounded-parent"
    target = parent / "target"
    target.mkdir(parents=True)
    ceiling = capture_service.MAX_PROTECTED_DIRECTORY_CHILDREN
    assert ceiling == 256
    for ordinal in range(ceiling - 1):
        (parent / f"member-{ordinal:03}.json").write_bytes(b"{}")

    assert capture_service._exact_child(
        parent,
        "target",
        must_exist=True,
        directory=True,
    ) == target

    (parent / "overflow.json").write_bytes(b"{}")
    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        capture_service._exact_child(
            parent,
            "target",
            must_exist=True,
            directory=True,
        )
    assert (
        excinfo.value.code
        == "connector_campaign_log_directory_limit_exceeded"
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("grant_sha256", "1" * 64),
        ("canonical_grant_fingerprint", "2" * 64),
        ("grant_id", "changed-grant-id"),
        ("arming_nonce", "123e4567-e89b-42d3-a456-426614174099"),
    ),
)
def test_read_only_capture_verifier_binds_run_envelope_to_indexed_grant(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    authority, chain, _ = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    run = db.get(ConnectorRun, authority.run_ids["nrc_adams_aps"])
    assert run is not None
    envelope = {
        **run.request_config_json["connector_egress_arming"],
        field: replacement,
    }
    envelope["arming_fingerprint"] = compute_arming_fingerprint(envelope)
    run.request_config_json = {"connector_egress_arming": envelope}
    run.request_fingerprint = envelope["arming_fingerprint"]
    db.commit()

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        verify_connector_campaign_log_capture_read_only(
            db,
            chain,
            str(authority.campaign_id),
            FINGERPRINT,
        )

    assert excinfo.value.code == "connector_campaign_log_read_run_identity_mismatch"
    assert not db.in_transaction()


def test_read_only_capture_verifier_bounds_exact_seal_event_query(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority, chain, sealed = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    sealed_event = db.get(ConnectorRunEvent, sealed.event_ids[0])
    assert sealed_event is not None
    for ordinal in range(8):
        db.add(
            ConnectorRunEvent(
                connector_run_event_id=str(uuid4()),
                connector_run_id=sealed_event.connector_run_id,
                connector_run_target_id=None,
                phase="test",
                stage="unrelated",
                event_type=f"unrelated_{ordinal}",
                status_before="completed",
                status_after="completed",
                reason_code="unrelated",
                error_class=None,
                message=None,
                metrics_json={},
                created_at=sealed_event.created_at,
            )
        )
    db.commit()
    statements: list[tuple[str, tuple[Any, ...]]] = []

    def capture_statement(
        _connection: Any,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if "connector_run_event" in statement.lower():
            statements.append((statement.lower(), tuple(parameters)))

    bind = db.get_bind()
    sqlalchemy_event.listen(bind, "before_cursor_execute", capture_statement)
    try:
        verified = verify_connector_campaign_log_capture_read_only(
            db,
            chain,
            str(authority.campaign_id),
            FINGERPRINT,
        )
    finally:
        sqlalchemy_event.remove(bind, "before_cursor_execute", capture_statement)

    assert verified.seal_event_ids == sealed.event_ids
    assert len(statements) == 2
    expected_run_ids = sealed.seal.connector_run_ids
    for statement, parameters in statements:
        assert "connector_run_event.event_type =" in statement
        assert "connector_run_event.connector_run_id in" in statement
        assert " limit " in statement
        assert parameters[0] == "campaign_log_capture_sealed"
        assert parameters[1 : 1 + len(expected_run_ids)] == expected_run_ids
        assert parameters[-2] == len(expected_run_ids) + 1
    assert not db.in_transaction()


def test_read_only_capture_verifier_refuses_caller_transaction(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authority, chain, _ = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    run = db.get(ConnectorRun, authority.run_ids["nrc_adams_aps"])
    assert run is not None
    run.status = "failed"
    assert db.in_transaction()
    assert run in db.dirty

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        verify_connector_campaign_log_capture_read_only(
            db,
            chain,
            str(authority.campaign_id),
            FINGERPRINT,
        )

    assert excinfo.value.code == "connector_campaign_log_read_transaction_active"
    assert db.in_transaction()
    assert run in db.dirty
    db.rollback()


_PRODUCER_REQUIRED_ENV = (
    "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
    "CONNECTOR_SCIENCEBASE_GRANT_PATH",
    "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    "CONNECTOR_NRC_APS_GRANT_PATH",
    "CONNECTOR_NRC_APS_GRANT_SHA256",
    "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
    "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
    "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
    "CONNECTOR_LIVE_EGRESS_ENABLED",
    "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
    "DATABASE_URL",
    "STORAGE_DIR",
    "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
)


def _producer_fake_settings(tmp_path: Path) -> object:
    evidence_root = tmp_path / "evidence"
    storage_root = tmp_path / "storage"
    database_path = tmp_path / "runtime.db"
    evidence_root.mkdir()
    storage_root.mkdir()
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE fixture (id INTEGER PRIMARY KEY)")

    class _Settings:
        connector_campaign_definition_path = tmp_path / "campaign.json"
        connector_campaign_definition_sha256 = DEFINITION_SHA256
        connector_sciencebase_grant_path = tmp_path / "sciencebase.json"
        connector_sciencebase_grant_sha256 = SCIENCEBASE_GRANT_SHA256
        connector_nrc_aps_grant_path = tmp_path / "nrc.json"
        connector_nrc_aps_grant_sha256 = NRC_GRANT_SHA256
        connector_campaign_evidence_root = evidence_root
        connector_campaign_evidence_index_path = tmp_path / "index.json"
        connector_campaign_evidence_index_sha256 = INDEX_SHA256
        connector_live_egress_enabled = True
        connector_live_egress_exclusive_proof_mode = True
        database_url = f"sqlite:///{database_path.as_posix()}"
        storage_dir = str(storage_root)
        nrc_adams_subscription_key = "fixture-secret"
        deployment_mode = "local"
        auth_owner = "none"
        trusted_proxy_mode = False

        def model_dump(self, **_kwargs: object) -> dict[str, object]:
            return {
                name: getattr(self, name)
                for name in dir(self)
                if not name.startswith("_")
                and name != "model_dump"
                and not callable(getattr(self, name))
            }

    return _Settings()


def _install_producer_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    required = frozenset(_PRODUCER_REQUIRED_ENV)
    for key in tuple(os.environ):
        if key.upper() in required:
            monkeypatch.delenv(key, raising=False)
    for key in _PRODUCER_REQUIRED_ENV:
        monkeypatch.setenv(key, "configured")


def _install_dependency_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import dual_live_dependencies

    monkeypatch.setattr(
        dual_live_dependencies,
        "verify_dual_live_dependencies",
        lambda: DEPENDENCY_SET_SHA256,
    )


def _phase_timeout_contract(
    *,
    nrc_timeout_seconds: int = 30,
    sciencebase_timeout_seconds: int = 30,
    nrc_interval_ms: int = 250,
    sciencebase_interval_ms: int = 250,
) -> dict[str, Any]:
    return _producer_preauthorization(
        nrc_timeout_seconds=nrc_timeout_seconds,
        sciencebase_timeout_seconds=sciencebase_timeout_seconds,
        nrc_interval_ms=nrc_interval_ms,
        sciencebase_interval_ms=sciencebase_interval_ms,
    ).timeout_contract()


def _producer_preauthorization(
    *,
    nrc_timeout_seconds: int = 30,
    sciencebase_timeout_seconds: int = 30,
    nrc_interval_ms: int = 250,
    sciencebase_interval_ms: int = 250,
) -> dual_live_runtime_module._ProducerPreauthorization:
    return dual_live_runtime_module._ProducerPreauthorization(
        code_revision=CODE_REVISION,
        grant_timeouts=(
            dual_live_runtime_module._ProducerGrantTimeoutInput(
                connector_key="nrc_adams_aps",
                max_physical_requests=2,
                request_timeout_seconds=nrc_timeout_seconds,
                min_request_interval_ms=nrc_interval_ms,
            ),
            dual_live_runtime_module._ProducerGrantTimeoutInput(
                connector_key="sciencebase_mcs",
                max_physical_requests=3,
                request_timeout_seconds=sciencebase_timeout_seconds,
                min_request_interval_ms=sciencebase_interval_ms,
            ),
        ),
    )


def test_public_dual_live_campaign_signature_has_no_injection_seams() -> None:
    run = dual_live_runtime_module.run_dual_live_campaign
    parameters = tuple(inspect.signature(run).parameters.values())
    assert tuple(parameter.name for parameter in parameters) == (
        "campaign_id",
        "expected_campaign_fingerprint",
    )
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for parameter in parameters
    )


def test_producer_timeout_contract_is_grant_derived_and_environment_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = _phase_timeout_contract()
    changed = _phase_timeout_contract(nrc_timeout_seconds=31)
    monkeypatch.setenv("DUAL_LIVE_PHASE_A_TIMEOUT_SECONDS", "1")
    monkeypatch.setenv("DUAL_LIVE_PHASE_B_TIMEOUT_SECONDS", "999")

    assert canonical == _phase_timeout_contract()
    assert canonical["phase_a_timeout_ms"] == 205_750
    assert canonical["phase_b_timeout_ms"] == 30_000
    assert changed["phase_a_timeout_ms"] == 207_750
    assert changed["connector_grants"][0]["request_timeout_seconds"] == 31
    assert _producer_preauthorization().phase_timeout_seconds() == {
        "A": 205.75,
        "B": 30.0,
    }


def test_producer_timeout_contract_rejects_overflow_and_nonfinite_values() -> None:
    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        _producer_preauthorization(nrc_timeout_seconds=4_294_968)
    assert exc.value.code == "dual_live_phase_timeout_contract_invalid"

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._validated_phase_timeout_seconds(
            {"A": float("nan"), "B": 30.0},
            "dual_live_phase_timeout_contract_invalid",
        )
    assert exc.value.code == "dual_live_phase_timeout_contract_invalid"


def test_producer_phase_environments_split_current_authority_from_history(
    tmp_path: Path,
) -> None:
    settings = _producer_fake_settings(tmp_path)

    phase_a, phase_b = dual_live_runtime_module._producer_phase_environments(
        settings,
        campaign_id=str(CAMPAIGN_ID),
        campaign_fingerprint=FINGERPRINT,
        code_revision=CODE_REVISION,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
    )

    assert phase_a["NRC_ADAMS_APS_SUBSCRIPTION_KEY"] == "fixture-secret"
    assert phase_a["CONNECTOR_NRC_APS_GRANT_PATH"] == str(
        settings.connector_nrc_aps_grant_path
    )
    assert phase_a["CONNECTOR_SCIENCEBASE_GRANT_PATH"] == str(
        settings.connector_sciencebase_grant_path
    )
    assert phase_a["CONNECTOR_LIVE_EGRESS_ENABLED"] == "true"
    assert phase_a["CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE"] == "true"
    assert phase_a["DUAL_LIVE_CAMPAIGN_ID"] == str(CAMPAIGN_ID)
    assert phase_a["DUAL_LIVE_CAMPAIGN_FINGERPRINT"] == FINGERPRINT
    assert phase_a["DUAL_LIVE_CODE_REVISION"] == CODE_REVISION
    assert (
        phase_a["DUAL_LIVE_DEPENDENCY_SET_SHA256"]
        == DEPENDENCY_SET_SHA256
    )

    forbidden_in_phase_b = {
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    }
    assert forbidden_in_phase_b.isdisjoint(phase_b)
    assert phase_b == {
        "AUTH_OWNER": "none",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(
            settings.connector_campaign_evidence_index_path
        ),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256": INDEX_SHA256,
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(
            settings.connector_campaign_evidence_root
        ),
        "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
        "DATABASE_URL": settings.database_url,
        "DEPLOYMENT_MODE": "local",
        "DUAL_LIVE_CAMPAIGN_FINGERPRINT": FINGERPRINT,
        "DUAL_LIVE_CAMPAIGN_ID": str(CAMPAIGN_ID),
        "DUAL_LIVE_CODE_REVISION": CODE_REVISION,
        "DUAL_LIVE_DEPENDENCY_SET_SHA256": DEPENDENCY_SET_SHA256,
        "STORAGE_DIR": settings.storage_dir,
        "TRUSTED_PROXY_MODE": "false",
    }


@pytest.mark.parametrize("phase", ("A", "B"))
def test_producer_phase_environment_matches_windows_child_allowlist(
    phase: str,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    settings = _producer_fake_settings(tmp_path)
    phase_a, phase_b = dual_live_runtime_module._producer_phase_environments(
        settings,
        campaign_id=str(CAMPAIGN_ID),
        campaign_fingerprint=FINGERPRINT,
        code_revision=CODE_REVISION,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
    )
    supplied = phase_a if phase == "A" else phase_b

    child_environment = dual_live_windows._owned_child_environment(
        phase,
        supplied,
    )

    assert {
        name: child_environment[name]
        for name in supplied
    } == dict(supplied)
    assert (
        child_environment["DUAL_LIVE_DEPENDENCY_SET_SHA256"]
        == DEPENDENCY_SET_SHA256
    )


@pytest.mark.parametrize("phase", ("A", "B"))
@pytest.mark.parametrize("mutation", ("missing-digest", "extra-name"))
def test_windows_child_environment_remains_exact_and_fail_closed(
    phase: str,
    mutation: str,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    settings = _producer_fake_settings(tmp_path)
    phase_a, phase_b = dual_live_runtime_module._producer_phase_environments(
        settings,
        campaign_id=str(CAMPAIGN_ID),
        campaign_fingerprint=FINGERPRINT,
        code_revision=CODE_REVISION,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
    )
    supplied = dict(phase_a if phase == "A" else phase_b)
    if mutation == "missing-digest":
        supplied.pop("DUAL_LIVE_DEPENDENCY_SET_SHA256")
    else:
        supplied["UNREVIEWED_NAME"] = "blocked"

    with pytest.raises(
        dual_live_windows.DualLiveWindowsError,
        match="dual_live_owned_environment_invalid",
    ):
        dual_live_windows._owned_child_environment(phase, supplied)


def test_public_dual_live_campaign_dependency_failure_precedes_all_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_dependencies, dual_live_windows

    def refuse() -> NoReturn:
        raise dual_live_dependencies.DualLiveDependencyError

    monkeypatch.setattr(
        dual_live_dependencies,
        "verify_dual_live_dependencies",
        refuse,
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_load_producer_settings",
        lambda: pytest.fail("settings/auth read preceded dependency refusal"),
    )
    monkeypatch.setattr(
        dual_live_windows,
        "acquire_proof_locks_staged",
        lambda *_args, **_kwargs: pytest.fail(
            "proof lock effect preceded dependency refusal"
        ),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_open_producer_database",
        lambda *_args, **_kwargs: pytest.fail(
            "database effect preceded dependency refusal"
        ),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_make_production_owned_controller_context",
        lambda **_kwargs: pytest.fail(
            "capture/process effect preceded dependency refusal"
        ),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module.run_dual_live_campaign(
            str(CAMPAIGN_ID),
            FINGERPRINT,
        )

    assert exc.value.code == "dual_live_dependency_provenance_invalid"


def test_public_dual_live_campaign_authorizes_both_local_writers_before_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config
    from app.services import dual_live_windows

    _install_dependency_verifier(monkeypatch)
    _install_producer_environment(monkeypatch)
    settings = _producer_fake_settings(tmp_path)
    monkeypatch.setattr(config, "Settings", lambda **_kwargs: settings)
    monkeypatch.setattr(config, "settings", settings)
    events: list[str] = []

    def refuse(**kwargs: object) -> NoReturn:
        assert kwargs == {
            "settings": settings,
            "campaign_id": str(CAMPAIGN_ID),
            "campaign_fingerprint": FINGERPRINT,
        }
        events.append("preauthorize")
        raise dual_live_runtime_module.DualLiveRuntimeError(
            "dual_live_local_runner_authorization_denied"
        )

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_preauthorize_producer_connectors",
        refuse,
        raising=False,
    )
    monkeypatch.setattr(
        dual_live_windows,
        "acquire_proof_locks_staged",
        lambda *_args, **_kwargs: pytest.fail(
            "proof lock effect preceded local-runner authorization"
        ),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_open_producer_database",
        lambda *_args, **_kwargs: pytest.fail(
            "database effect preceded local-runner authorization"
        ),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_make_production_owned_controller_context",
        lambda **_kwargs: pytest.fail(
            "capture effect preceded local-runner authorization"
        ),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module.run_dual_live_campaign(
            str(CAMPAIGN_ID),
            FINGERPRINT,
        )

    assert exc.value.code == "dual_live_local_runner_authorization_denied"
    assert events == ["preauthorize"]


def test_producer_result_requires_exact_seal_derived_event_ids() -> None:
    run_ids = tuple(
        sorted(
            (
                str(uuid5(NAMESPACE_URL, "producer-nrc-run")),
                str(uuid5(NAMESPACE_URL, "producer-sciencebase-run")),
            )
        )
    )
    event_ids = tuple(
        str(
            uuid5(
                NAMESPACE_URL,
                "project6:connector-egress:"
                f"{run_id}:campaign_log_capture_sealed:0",
            )
        )
        for run_id in run_ids
    )
    result = SimpleNamespace(
        manifest_sha256="6" * 64,
        file_set_hash="7" * 64,
        seal_sha256="8" * 64,
        event_ids=event_ids,
        seal=SimpleNamespace(connector_run_ids=run_ids),
    )

    report = dual_live_runtime_module._producer_result_projection(
        result,
        campaign_id=str(CAMPAIGN_ID),
        campaign_fingerprint=FINGERPRINT,
    )

    assert report["event_ids"] == list(event_ids)

    result.event_ids = tuple(reversed(event_ids))
    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._producer_result_projection(
            result,
            campaign_id=str(CAMPAIGN_ID),
            campaign_fingerprint=FINGERPRINT,
        )
    assert exc.value.code == "dual_live_producer_result_invalid"


def test_producer_result_refuses_unbounded_event_iterable_without_iteration() -> None:
    class _Unbounded:
        def __iter__(self) -> object:
            pytest.fail("event_ids iterable was materialized before bounding")

    result = SimpleNamespace(
        manifest_sha256="6" * 64,
        file_set_hash="7" * 64,
        seal_sha256="8" * 64,
        event_ids=_Unbounded(),
        seal=SimpleNamespace(connector_run_ids=(str(uuid4()), str(uuid4()))),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._producer_result_projection(
            result,
            campaign_id=str(CAMPAIGN_ID),
            campaign_fingerprint=FINGERPRINT,
        )

    assert exc.value.code == "dual_live_producer_result_invalid"


def test_http_counter_ack_runs_only_after_validated_frame_is_persisted() -> None:
    writers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
    readers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
    events: list[str] = []

    def validate(payload: bytes) -> None:
        assert payload == b"{}"
        assert writers["http"].getvalue() == b""
        events.append("validated")

    def committed() -> None:
        assert writers["http"].getvalue() == b"{}\n"
        events.append("persisted-ack")

    pumps = dual_live_runtime_module.FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        boot_callback=lambda _sha256: None,
        status_callback=lambda _status, _sha256: None,
        proof_callback=lambda _proof: None,
        http_frame_validator=validate,
        http_frame_committed=committed,
        stop_latch=dual_live_runtime_module.FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id="1" * 64,
        expected_status_nonce_sha256="2" * 64,
        expected_control_nonce="3" * 64,
        expected_proof_scope="mechanical",
    )

    pumps._write_frame("http", b"{}")

    assert events == ["validated", "persisted-ack"]


def test_owned_phase_a_workload_uses_real_constructor_order_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.db import session as db_session
    from app.services import (
        connector_egress_arming,
        connector_egress_authorization,
        connector_egress_transport,
        connectors_nrc_adams,
        connectors_sciencebase,
    )

    monkeypatch.setenv("DUAL_LIVE_CAMPAIGN_ID", str(CAMPAIGN_ID))
    monkeypatch.setenv("DUAL_LIVE_CAMPAIGN_FINGERPRINT", FINGERPRINT)
    monkeypatch.setenv("DUAL_LIVE_CODE_REVISION", CODE_REVISION)
    settings = SimpleNamespace(
        connector_nrc_aps_grant_sha256=NRC_GRANT_SHA256,
        connector_sciencebase_grant_sha256=SCIENCEBASE_GRANT_SHA256,
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_load_producer_settings",
        lambda: settings,
    )
    events: list[str] = []
    campaign = SimpleNamespace(model=SimpleNamespace(code_revision=CODE_REVISION))

    def resolve_campaign(**_kwargs: object) -> object:
        events.append("campaign")
        return campaign

    def resolve_grant(**kwargs: object) -> object:
        connector_key = cast(str, kwargs["connector_key"])
        events.append(f"grant-{connector_key}")
        return SimpleNamespace(
            model=SimpleNamespace(connector_key=connector_key),
            raw_sha256=cast(str, kwargs["expected_grant_sha256"]),
            verified_campaign=campaign,
        )

    def authorize(**kwargs: object) -> object:
        grant = kwargs["verified_grant"]
        assert kwargs["access"] == "write"
        events.append(f"authorize-{grant.model.connector_key}")
        return SimpleNamespace(
            model_dump=lambda **_kwargs: {
                "connector_key": grant.model.connector_key,
                "access": "write",
            }
        )

    monkeypatch.setattr(
        connector_egress_authorization,
        "resolve_current_dual_live_campaign_definition",
        resolve_campaign,
    )
    monkeypatch.setattr(
        connector_egress_authorization,
        "resolve_current_connector_egress_grant",
        resolve_grant,
    )
    monkeypatch.setattr(
        connector_egress_authorization,
        "authorize_connector_egress_local_runner",
        authorize,
    )

    class _Db:
        def close(self) -> None:
            events.append("db-close")

    monkeypatch.setattr(db_session, "SessionLocal", lambda: _Db())

    def create_arming(
        _db: object,
        *,
        payload: object,
        verified_grant: object,
        operator_receipt: object,
        code_revision: str,
    ) -> tuple[object, bool]:
        del payload, operator_receipt
        assert code_revision == CODE_REVISION
        connector_key = verified_grant.model.connector_key
        events.append(f"arm-{connector_key}")
        return (
            SimpleNamespace(
                connector_run_id=f"run-{connector_key}",
                request_fingerprint=(
                    NRC_GRANT_SHA256
                    if connector_key == "nrc_adams_aps"
                    else SCIENCEBASE_GRANT_SHA256
                ),
            ),
            True,
        )

    def claim_arming(
        _db: object,
        *,
        connector_run_id: str,
        **_kwargs: object,
    ) -> tuple[object, bool]:
        events.append(f"claim-{connector_run_id}")
        return SimpleNamespace(connector_run_id=connector_run_id), True

    monkeypatch.setattr(
        connector_egress_arming,
        "create_connector_egress_arming",
        create_arming,
    )
    monkeypatch.setattr(
        connector_egress_arming,
        "claim_connector_egress_arming",
        claim_arming,
    )
    monkeypatch.setattr(
        connector_egress_arming,
        "evaluate_nrc_acquisition_success",
        lambda *_args, **_kwargs: events.append("nrc-success") or object(),
    )
    monkeypatch.setattr(
        connectors_nrc_adams,
        "execute_nrc_adams_run",
        lambda run_id: events.append(f"execute-{run_id}"),
    )
    monkeypatch.setattr(
        connectors_sciencebase,
        "execute_connector_run",
        lambda run_id: events.append(f"execute-{run_id}"),
    )

    @contextmanager
    def counter_runtime(_context: object) -> object:
        events.append("counter-install")
        try:
            yield _context
        finally:
            events.append("counter-remove")

    monkeypatch.setattr(
        connector_egress_transport,
        "connector_counter_runtime",
        counter_runtime,
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_phase_a_acquisition_projection",
        lambda _db, **kwargs: {
            "action_codes": [
                "derived_arming",
                "raw_acquisition",
                "terminal_transition",
            ],
            "connector_key": kwargs["connector_key"],
            "connector_run_id": kwargs["connector_run_id"],
            "connector_run_target_id": f"target-{kwargs['connector_key']}",
            "ledger_terminal_hash": "3" * 64,
            "raw_content_sha256": "4" * 64,
            "terminal_transition_count": 1,
        },
    )

    projection = dual_live_runtime_module.run_owned_phase_a_workload(
        runtime_instance_id=str(uuid4()),
        process_boot_id="a" * 64,
        append_counter_frame=lambda _payload: None,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: None,
        release_send_idle=lambda: None,
    )

    assert events == [
        "campaign",
        "counter-install",
        "grant-nrc_adams_aps",
        "authorize-nrc_adams_aps",
        "arm-nrc_adams_aps",
        "claim-run-nrc_adams_aps",
        "db-close",
        "execute-run-nrc_adams_aps",
        "nrc-success",
        "db-close",
        "campaign",
        "grant-sciencebase_mcs",
        "authorize-sciencebase_mcs",
        "arm-sciencebase_mcs",
        "claim-run-sciencebase_mcs",
        "db-close",
        "execute-run-sciencebase_mcs",
        "counter-remove",
        "db-close",
    ]
    assert [
        item["connector_key"]
        for item in projection["connector_acquisitions"]
    ] == ["nrc_adams_aps", "sciencebase_mcs"]
    assert projection["downstream_action_count"] == 0


def test_owned_child_dispatches_phase_workloads_under_distinct_guards() -> None:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    spec = importlib.util.spec_from_file_location("dual_live_run_dispatch", tool_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    events: list[str] = []

    class _Guards:
        def assert_intact(self) -> None:
            events.append("guard-all")

        def enable_phase_a_transport(self) -> None:
            events.append("guard-a-network")

        def install(self) -> None:
            events.append("guard-reinstall")

    class _Kernel:
        def WaitForSingleObject(self, _handle: int, _timeout: int) -> int:
            return runner._WAIT_TIMEOUT

    class _Runtime:
        class DualLiveRuntimeError(ValueError):
            def __init__(self, code: str) -> None:
                super().__init__(code)
                self.code = code

        def encode_pipe_frame(self, payload: bytes) -> bytes:
            return payload

        def run_owned_phase_a_workload(self, **kwargs: object) -> object:
            assert kwargs["runtime_instance_id"] == str(CAMPAIGN_ID)
            assert kwargs["process_boot_id"] == "a" * 64
            assert all(
                callable(kwargs[name])
                for name in (
                    "append_counter_frame",
                    "revocation_is_set",
                    "acquire_send_idle",
                    "release_send_idle",
                )
            )
            events.append("workload-A")
            return {
                "connector_acquisitions": [],
                "downstream_action_count": 0,
            }

        def run_owned_phase_b_workload(self) -> object:
            events.append("workload-B")
            return {
                "downstream_actions": [],
                "source_bindings": [],
                "terminal_boundary": "handoff_prepared",
            }

    handles = {
        "child_counter_ack_event_handle": 1,
        "child_http_write_handle": 2,
        "child_revocation_event_handle": 3,
        "child_send_idle_event_handle": 4,
    }
    runtime = _Runtime()
    guards = _Guards()
    kernel = _Kernel()

    assert runner._dispatch_owned_workload(
        runtime,
        guards,
        kernel,
        phase="A",
        handles=handles,
        runtime_instance_id=str(CAMPAIGN_ID),
        process_boot_id="a" * 64,
    ) == (0, {"connector_acquisitions": [], "downstream_action_count": 0})
    assert runner._dispatch_owned_workload(
        runtime,
        guards,
        kernel,
        phase="B",
        handles={},
        runtime_instance_id=str(CAMPAIGN_ID),
        process_boot_id="b" * 64,
    ) == (
        0,
        {
            "downstream_actions": [],
            "source_bindings": [],
            "terminal_boundary": "handoff_prepared",
        },
    )
    assert events == [
        "guard-a-network",
        "workload-A",
        "guard-reinstall",
        "guard-all",
        "workload-B",
        "guard-all",
    ]


def test_owned_child_does_not_translate_wrong_code_or_message_spoof() -> None:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    spec = importlib.util.spec_from_file_location(
        "dual_live_run_dispatch_negative",
        tool_path,
    )
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    class _CodeError(ValueError):
        def __init__(self, code: str) -> None:
            super().__init__(code)
            self.code = code

    class _Guards:
        def assert_intact(self) -> None:
            return None

    for error in (
        _CodeError("dual_live_phase_failed"),
        RuntimeError("dual_live_phase_b_projection_invalid"),
    ):
        runtime = SimpleNamespace(
            run_owned_phase_b_workload=lambda error=error: (
                (_ for _ in ()).throw(error)
            )
        )
        with pytest.raises(type(error)) as exc:
            runner._dispatch_owned_workload(
                runtime,
                _Guards(),
                SimpleNamespace(),
                phase="B",
                handles={},
                runtime_instance_id=str(CAMPAIGN_ID),
                process_boot_id="b" * 64,
            )
        assert exc.value is error


def test_public_runner_projects_only_reviewed_boundary_codes_secret_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    spec = importlib.util.spec_from_file_location("dual_live_run_refusal", tool_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    writes: list[tuple[int, bytes]] = []
    monkeypatch.setattr(
        runner.os,
        "write",
        lambda descriptor, content: (
            writes.append((descriptor, content)) or len(content)
        ),
    )

    inspection = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_timeout_inspection_required"
    )
    message_spoof = RuntimeError(
        "dual_live_phase_timeout_inspection_required"
    )
    wrong_code = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_failed"
    )
    unknown = RuntimeError("fixture-secret must never be emitted")

    assert runner._refuse(runner._allowlisted_refusal_code(inspection)) == 2
    assert runner._refuse(runner._allowlisted_refusal_code(message_spoof)) == 2
    assert runner._refuse(runner._allowlisted_refusal_code(wrong_code)) == 2
    assert runner._refuse(runner._allowlisted_refusal_code(unknown)) == 2
    assert writes == [
        (2, b"dual_live_phase_timeout_inspection_required\n"),
        (2, b"dual_live_run_refused\n"),
        (2, b"dual_live_run_refused\n"),
        (2, b"dual_live_run_refused\n"),
    ]
    assert b"fixture-secret" not in b"".join(content for _fd, content in writes)


@pytest.mark.parametrize(
    ("ack_mode", "expected_error"),
    (
        ("success", None),
        ("revoked", PermissionError),
        ("timeout", TimeoutError),
    ),
)
def test_owned_child_counter_ack_wait_is_bounded_and_revocation_aware(
    ack_mode: str,
    expected_error: type[BaseException] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    spec = importlib.util.spec_from_file_location("dual_live_run_ack", tool_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "_COUNTER_ACK_TIMEOUT_SECONDS", 0.002)
    events: list[str] = []

    class _Writer:
        def __init__(self, _kernel: object, handle: int) -> None:
            assert handle == 2

        def write(self, content: bytes) -> int:
            events.append("counter-written")
            assert content == b"framed-counter"
            return len(content)

    class _Guards:
        def enable_phase_a_transport(self) -> None:
            events.append("guard-a-network")

        def install(self) -> None:
            events.append("guard-reinstall")

    class _Kernel:
        def __init__(self) -> None:
            self.ack_waits = 0

        def ResetEvent(self, handle: int) -> int:
            events.append(f"reset-{handle}")
            return 1

        def SetEvent(self, handle: int) -> int:
            events.append(f"set-{handle}")
            return 1

        def WaitForSingleObject(self, handle: int, _timeout: int) -> int:
            if handle == 3:
                if ack_mode == "revoked" and self.ack_waits:
                    events.append("revocation-observed")
                    return runner._WAIT_OBJECT_0
                return runner._WAIT_TIMEOUT
            assert handle == 1
            self.ack_waits += 1
            if self.ack_waits == 1:
                events.append("ack-waited")
            if ack_mode == "success":
                return runner._WAIT_OBJECT_0
            return runner._WAIT_TIMEOUT

    class _Runtime:
        def encode_pipe_frame(self, payload: bytes) -> bytes:
            assert payload == b"counter"
            return b"framed-counter"

        def run_owned_phase_a_workload(self, **kwargs: object) -> object:
            events.append("workload-A")
            append_counter_frame = cast(
                Callable[[bytes], None],
                kwargs["append_counter_frame"],
            )
            append_counter_frame(b"counter")
            events.append("workload-A-complete")
            return {
                "connector_acquisitions": [],
                "downstream_action_count": 0,
            }

    monkeypatch.setattr(runner, "_NativeWriter", _Writer)
    kernel = _Kernel()

    def call() -> tuple[int, Mapping[str, object]]:
        return runner._dispatch_owned_workload(
            _Runtime(),
            _Guards(),
            kernel,
            phase="A",
            handles={
                "child_counter_ack_event_handle": 1,
                "child_http_write_handle": 2,
                "child_revocation_event_handle": 3,
                "child_send_idle_event_handle": 4,
            },
            runtime_instance_id=str(CAMPAIGN_ID),
            process_boot_id="a" * 64,
        )

    if expected_error is None:
        assert call() == (
            0,
            {"connector_acquisitions": [], "downstream_action_count": 0},
        )
        assert "workload-A-complete" in events
    else:
        with pytest.raises(expected_error):
            call()
        assert "workload-A-complete" not in events
    assert events.index("counter-written") < events.index("ack-waited")
    assert events[-1] == "guard-reinstall"
    if ack_mode == "revoked":
        assert "revocation-observed" in events
    if ack_mode == "timeout":
        assert kernel.ack_waits >= 1


def test_owned_phase_b_workload_is_secret_free_and_returns_prepared_handoff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.db import session as db_session

    phase_b_environment = {
        "AUTH_OWNER": "none",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'phase-b.db'}",
        "DEPLOYMENT_MODE": "local",
        "DUAL_LIVE_CAMPAIGN_FINGERPRINT": FINGERPRINT,
        "DUAL_LIVE_CAMPAIGN_ID": str(CAMPAIGN_ID),
        "DUAL_LIVE_CODE_REVISION": CODE_REVISION,
        "DUAL_LIVE_DEPENDENCY_SET_SHA256": DEPENDENCY_SET_SHA256,
        "STORAGE_DIR": str(tmp_path / "storage"),
        "TRUSTED_PROXY_MODE": "false",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(tmp_path / "index.json"),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256": "1" * 64,
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(tmp_path / "evidence"),
        "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
    }
    forbidden = {
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
    }
    for name, value in phase_b_environment.items():
        monkeypatch.setenv(name, value)
    for name in forbidden:
        monkeypatch.delenv(name, raising=False)

    events: list[str] = []

    class _Db:
        def in_transaction(self) -> bool:
            return True

        def rollback(self) -> None:
            events.append("rollback")

        def close(self) -> None:
            events.append("close")

    db = _Db()
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_assert_phase_b_connector_guards",
        lambda: events.append("connector-guards"),
        raising=False,
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_prepare_owned_phase_b",
        lambda _db, **kwargs: (
            events.append(
                "prepare:"
                + ":".join(
                    (
                        kwargs["campaign_id"],
                        kwargs["campaign_fingerprint"],
                        kwargs["code_revision"],
                    )
                )
            )
            or {
                "downstream_actions": [],
                "source_bindings": [],
                "terminal_boundary": "handoff_prepared",
            }
        ),
        raising=False,
    )
    monkeypatch.setattr(
        db_session,
        "SessionLocal",
        lambda: events.append("session") or db,
    )

    projection = dual_live_runtime_module.run_owned_phase_b_workload()

    assert events == [
        "connector-guards",
        "session",
        f"prepare:{CAMPAIGN_ID}:{FINGERPRINT}:{CODE_REVISION}",
        "connector-guards",
        "rollback",
        "close",
    ]
    assert projection["terminal_boundary"] == "handoff_prepared"


def test_owned_phase_b_completes_both_public_chains_to_prepared_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import (
        layer3_connector_source_intake,
        layer3_origin_continuity,
        layer3_workbench,
        nrc_aps_phase_b_linkage,
    )

    events: list[str] = []

    class _Transaction:
        def __enter__(self) -> None:
            events.append("begin")

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: object,
        ) -> None:
            del exc_type, exc, traceback
            events.append("commit")

    class _Db:
        def rollback(self) -> None:
            events.append("rollback")

        def begin(self) -> _Transaction:
            return _Transaction()

    targets = SimpleNamespace(
        nrc_run_id="nrc-run",
        nrc_target_id="nrc-target",
        sciencebase_run_id="sciencebase-run",
        sciencebase_target_id="sciencebase-target",
        sciencebase_intake_record_id="sciencebase-intake",
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_resolve_owned_phase_b_targets",
        lambda *_args, **_kwargs: events.append("resolve") or targets,
        raising=False,
    )
    monkeypatch.setattr(
        nrc_aps_phase_b_linkage,
        "bind_strict_nrc_phase_b_linkage",
        lambda _db, **kwargs: events.append(
            f"bind:{kwargs['connector_run_target_id']}"
        )
        or SimpleNamespace(content_id="nrc-content"),
    )
    monkeypatch.setattr(
        layer3_origin_continuity,
        "mint_connector_origin_receipt",
        lambda _db, **kwargs: events.append(
            f"mint:{kwargs['connector_run_target_id']}"
        )
        or {
            "connector_run_target_id": kwargs["connector_run_target_id"],
            "connector_origin_receipt_hash": "2" * 64,
        },
    )
    monkeypatch.setattr(
        layer3_workbench,
        "preflight",
        lambda payload: events.append("nrc-preflight")
        or {"preflight_id": "preflight"},
    )
    monkeypatch.setattr(
        layer3_workbench,
        "source_preview",
        lambda payload: events.append("nrc-source-preview")
        or {
            "source_set_id": "source-set",
            "source_candidates": [
                {"source_candidate_id": "src-aps_content_document-test"}
            ],
        },
    )
    def material_preview(payload: dict[str, Any], db: object) -> dict[str, Any]:
        assert db is not None
        assert payload["query_basis"] == {"terms": ["dual-live-proof"]}
        events.append("nrc-material-preview")
        return {
            "material_preview_id": "nrc-material",
            "material_candidates": [
                {
                    "candidate_id": "nrc-candidate",
                    "source_ref": "nrc-source",
                    "query_basis": {},
                    "provenance_ref": "nrc-provenance",
                    "source_identity": {},
                    "source_provenance": {},
                    "payload": {},
                    "load_summary": {},
                }
            ],
        }

    monkeypatch.setattr(
        layer3_workbench,
        "material_preview",
        material_preview,
    )
    monkeypatch.setattr(
        layer3_connector_source_intake,
        "connector_source_intake_material_preview",
        lambda _db, **kwargs: events.append("sciencebase-material-preview")
        or {
            "material_preview_id": "sciencebase-material",
            "material_preview_hash": "3" * 64,
            "material_candidate": {
                "candidate_id": "sciencebase-candidate",
                "source_class": (
                    layer3_connector_source_intake
                    .STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
                ),
                "source_ref": "sciencebase-source",
                "query_basis": {},
                "provenance_ref": "sciencebase-provenance",
                "source_identity": {},
                "source_provenance": {},
                "payload": {},
                "load_summary": {},
            },
        },
    )

    def gate_b(_db: object, payload: dict[str, Any]) -> dict[str, Any]:
        candidate_id = payload["candidate_decisions"][0]["candidate_id"]
        connector = (
            "nrc" if candidate_id == "nrc-candidate" else "sciencebase"
        )
        events.append(f"{connector}-gate-b")
        assert payload["candidate_decisions"][0]["decision"] == "approved"
        return {"session_id": f"{connector}-session"}

    monkeypatch.setattr(
        layer3_workbench,
        "gate_b_decision",
        gate_b,
    )

    def complete_chain(
        _db: object,
        **kwargs: Any,
    ) -> dict[str, Any]:
        prefix = kwargs["action_prefix"]
        events.append(f"{prefix}-complete")
        assert kwargs["gate_b_result"] == {
            "session_id": f"{prefix}-session"
        }
        actions = (
            dual_live_runtime_module._PHASE_B_NRC_ACTIONS[3:]
            if prefix == "nrc"
            else dual_live_runtime_module._PHASE_B_SCIENCEBASE_ACTIONS[1:]
        )
        kwargs["action_receipts"].extend(
            {"action": action, "result_sha256": "4" * 64}
            for action in actions
        )
        return {
            **kwargs["source_binding"],
            "session_id": f"{prefix}-session",
        }

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_complete_owned_phase_b_chain",
        complete_chain,
    )

    projection = dual_live_runtime_module._prepare_owned_phase_b(
        _Db(),
        campaign_id=str(CAMPAIGN_ID),
        campaign_fingerprint=FINGERPRINT,
        code_revision=CODE_REVISION,
    )

    assert events == [
        "resolve",
        "rollback",
        "bind:nrc-target",
        "begin",
        "mint:nrc-target",
        "commit",
        "begin",
        "mint:sciencebase-target",
        "commit",
        "nrc-preflight",
        "nrc-source-preview",
        "nrc-material-preview",
        "nrc-gate-b",
        "nrc-complete",
        "sciencebase-material-preview",
        "sciencebase-gate-b",
        "sciencebase-complete",
    ]
    assert projection["terminal_boundary"] == "handoff_prepared"
    assert projection["downstream_actions"] == list(
        dual_live_runtime_module._PHASE_B_DOWNSTREAM_ACTIONS
    )
    assert [item["action"] for item in projection["action_receipts"]] == (
        projection["downstream_actions"]
    )
    assert [item["connector_key"] for item in projection["source_bindings"]] == [
        "nrc_adams_aps",
        "sciencebase_mcs",
    ]


def test_owned_phase_b_finisher_binds_internal_handoff_and_fails_closed() -> None:
    package_ids = ["package-0", "package-1", "package-2"]
    package_hashes = ["4" * 64, "5" * 64, "6" * 64]
    package_refs = ["canonical.json", "user.json", "review.json"]
    no_delivery = {
        flag: False
        for flag in dual_live_runtime_module._PHASE_B_NO_DELIVERY_FLAGS
    }
    baseline = {
        "gate_c_preview": {"next_state": "plan_preview_ready"},
        "plan_preview": {
            "preview_id": "preview-sciencebase",
            "preview_hash": "1" * 64,
        },
        "plan_approval": {"analysis_plan_id": "plan-sciencebase"},
        "execution_selection": {"pass_run_ids": ["pass-sciencebase"]},
        "analysis_execution_start": {"analysis_run_id": "run-analysis"},
        "execution_result_review": {
            "review_state": "execution_result_review_approved",
            "review_record_ref": "review-sciencebase",
        },
        "package_review_preview": {
            "package_review_preview_hash": (
                "l3-source-intake-package-preview-" + "2" * 16
            ),
        },
        "package_construction_commit": {
            "construction_basis_hash": "3" * 64,
            "output_package_ids": package_ids,
            "package_kinds": list(
                dual_live_runtime_module._PHASE_B_PACKAGE_KINDS
            ),
            "payload_hashes": package_hashes,
            "payload_refs": package_refs,
            "reconciliation_record_id": "reconcile-sciencebase",
        },
        "package_review_submit": {
            "package_review_state": "package_review_approved",
            "schema_id": "layer3.source_intake_package_review_submit.v1",
            "submit_record_ref": "submit-sciencebase",
        },
        "handoff_export_prepare": {
            **no_delivery,
            "export_mode": "prepare_only",
            "handoff_export_envelope": {
                **no_delivery,
                "source_shape": "strict_sciencebase_connector_single_source",
            },
            "handoff_export_envelope_ref": "envelope-sciencebase",
            "handoff_export_state": "handoff_export_prepared",
            "handoff_target": "internal_export_envelope",
            "prepare_record_ref": "prepare-sciencebase",
            "source_shape": "strict_sciencebase_connector_single_source",
        },
    }

    def run(
        responses: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], list[tuple[str, dict[str, Any]]], list[dict[str, str]]]:
        calls: list[tuple[str, dict[str, Any]]] = []

        def invoke(name: str, *_args: object) -> dict[str, Any]:
            payload = _args[-1]
            assert isinstance(payload, dict)
            calls.append((name, deepcopy(payload)))
            return deepcopy(responses[name])

        workbench = SimpleNamespace(
            **{
                name: (
                    lambda *_args, name=name: invoke(name, *_args)
                )
                for name in responses
            }
        )
        receipts: list[dict[str, str]] = []
        result = dual_live_runtime_module._complete_owned_phase_b_chain(
            object(),
            layer3_workbench=workbench,
            connector_key="sciencebase_mcs",
            action_prefix="sciencebase",
            request_prefix="dual-live-campaign-sciencebase",
            gate_b_result={"session_id": "session-sciencebase"},
            source_binding={
                "candidate_id": "candidate-sciencebase",
                "connector_key": "sciencebase_mcs",
                "connector_origin_receipt_hash": "7" * 64,
                "connector_run_id": "run-sciencebase",
                "connector_run_target_id": "target-sciencebase",
                "source_record_id": "intake-sciencebase",
            },
            action_receipts=receipts,
        )
        return result, calls, receipts

    result, calls, receipts = run(deepcopy(baseline))
    assert [name for name, _payload in calls] == list(baseline)
    assert [receipt["action"] for receipt in receipts] == list(
        dual_live_runtime_module._PHASE_B_SCIENCEBASE_ACTIONS[1:]
    )
    assert result["output_package_ids"] == package_ids
    assert result["payload_hashes"] == package_hashes
    assert result["prepare_record_ref"] == "prepare-sciencebase"
    assert calls[2][1]["operator_confirmation"] is True
    assert calls[5][1]["operator_decision"] == "approved"
    assert calls[8][1]["operator_decision"] == "approved"
    assert calls[9][1] == {
        **calls[9][1],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": "authorize_prepare",
    }

    invalids = []
    top_flag = deepcopy(baseline)
    top_flag["handoff_export_prepare"]["external_export_enabled"] = True
    invalids.append(top_flag)
    nested_flag = deepcopy(baseline)
    nested_flag["handoff_export_prepare"]["handoff_export_envelope"][
        "dispatch_enabled"
    ] = True
    invalids.append(nested_flag)
    wrong_shape = deepcopy(baseline)
    wrong_shape["handoff_export_prepare"]["source_shape"] = "wrong"
    invalids.append(wrong_shape)
    duplicate_packages = deepcopy(baseline)
    duplicate_packages["package_construction_commit"]["output_package_ids"] = [
        "package-0",
        "package-0",
        "package-2",
    ]
    invalids.append(duplicate_packages)
    blank_ref = deepcopy(baseline)
    blank_ref["package_construction_commit"]["payload_refs"][1] = ""
    invalids.append(blank_ref)
    bad_hash = deepcopy(baseline)
    bad_hash["package_construction_commit"]["construction_basis_hash"] = "bad"
    invalids.append(bad_hash)
    for invalid in invalids:
        with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError):
            run(invalid)


def test_public_dual_live_campaign_stages_locks_derives_source_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config
    from app.services import dual_live_windows
    import sqlalchemy
    import sqlalchemy.orm

    _install_dependency_verifier(monkeypatch)
    _install_producer_environment(monkeypatch)
    settings = _producer_fake_settings(tmp_path)
    monkeypatch.setattr(config, "Settings", lambda **_kwargs: settings)
    monkeypatch.setattr(config, "settings", settings)
    events: list[str] = []
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_preauthorize_producer_connectors",
        lambda **_kwargs: (
            events.append("preauthorize") or _producer_preauthorization()
        ),
    )

    class _Locks:
        root_identity_sha256 = "4" * 64
        campaign_identity_sha256 = "5" * 64

        def close(self) -> None:
            events.append("locks-close")

    locks = _Locks()

    def acquire(
        evidence_root: Path,
        campaign_id: str,
        campaign_fingerprint: str,
        resolver: Any,
        wait_ms: int = 0,
    ) -> object:
        assert evidence_root == settings.connector_campaign_evidence_root
        assert campaign_id == str(CAMPAIGN_ID)
        assert campaign_fingerprint == FINGERPRINT
        assert wait_ms == 0
        events.append("root-lock")
        assert resolver() == DEFINITION_SHA256
        events.append("campaign-lock")
        return locks

    monkeypatch.setattr(dual_live_windows, "acquire_proof_locks_staged", acquire)
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_resolve_staged_campaign_definition_sha256",
        lambda *_args, **_kwargs: DEFINITION_SHA256,
        raising=False,
    )

    class _Source:
        code_revision = CODE_REVISION
        wrapper_image_sha256 = "2" * 64
        interpreter_image_sha256 = "3" * 64

        def assert_stable(self) -> None:
            events.append("source-stable")

        def close(self) -> None:
            events.append("source-close")

    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        lambda: events.append("source-open") or _Source(),
    )

    class _Connection:
        def __init__(self) -> None:
            self.query_only = False

        def exec_driver_sql(self, statement: str) -> tuple[tuple[object, ...], ...]:
            if statement == "PRAGMA query_only = ON":
                self.query_only = True
                return ()
            if statement == "PRAGMA query_only = OFF":
                self.query_only = False
                return ()
            if statement == "PRAGMA query_only":
                return ((1 if self.query_only else 0,),)
            if statement == "PRAGMA database_list":
                database_path = config._sqlite_database_path(settings.database_url)
                assert database_path is not None
                return ((0, "main", str(database_path)),)
            if statement == "PRAGMA quick_check(1)":
                return (("ok",),)
            if statement.startswith("SELECT name FROM sqlite_master"):
                return tuple((name,) for name in Base.metadata.tables)
            pytest.fail(f"unexpected producer DB statement: {statement}")

        def rollback(self) -> None:
            events.append("connection-rollback")

        def in_transaction(self) -> bool:
            return False

        def close(self) -> None:
            events.append("connection-close")

    connection = _Connection()

    class _Engine:
        def connect(self) -> _Connection:
            events.append("connection-open")
            return connection

        def dispose(self) -> None:
            events.append("engine-dispose")

    engine = _Engine()
    monkeypatch.setattr(
        sqlalchemy,
        "create_engine",
        lambda *_args, **_kwargs: events.append("engine-open") or engine,
    )

    class _Session:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["bind"] is connection
            events.append("session-open")

        def close(self) -> None:
            events.append("session-close")

    monkeypatch.setattr(sqlalchemy.orm, "Session", _Session)
    context = object()
    captured: dict[str, object] = {}

    def make_context(**kwargs: object) -> object:
        captured.update(kwargs)
        events.append("context")
        return context

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_make_production_owned_controller_context",
        make_context,
    )
    run_ids = tuple(
        sorted(
            (
                str(uuid5(NAMESPACE_URL, "fixture-nrc-run")),
                str(uuid5(NAMESPACE_URL, "fixture-sciencebase-run")),
            )
        )
    )
    event_ids = tuple(
        str(
            uuid5(
                NAMESPACE_URL,
                "project6:connector-egress:"
                f"{run_id}:campaign_log_capture_sealed:0",
            )
        )
        for run_id in run_ids
    )
    result = SimpleNamespace(
        manifest_sha256="6" * 64,
        file_set_hash="7" * 64,
        seal_sha256="8" * 64,
        event_ids=event_ids,
        seal=SimpleNamespace(connector_run_ids=run_ids),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_production_owned_two_phase_controller",
        lambda supplied: (
            events.append("run") or result
            if supplied is context
            else pytest.fail("wrong context")
        ),
    )

    report = dual_live_runtime_module.run_dual_live_campaign(
        str(CAMPAIGN_ID),
        FINGERPRINT,
    )

    assert report == {
        "schema_id": "project6.dual_live_campaign_run.v1",
        "campaign_id": str(CAMPAIGN_ID),
        "campaign_fingerprint": FINGERPRINT,
        "status": "SEALED",
        "code": "dual_live_campaign_sealed",
        "manifest_sha256": "6" * 64,
        "file_set_hash": "7" * 64,
        "seal_sha256": "8" * 64,
        "event_ids": list(event_ids),
    }
    identity = cast(RuntimeIdentity, captured["identity"])
    assert identity.code_revision == CODE_REVISION
    assert identity.wrapper_image_sha256 == "2" * 64
    assert identity.interpreter_image_sha256 == "3" * 64
    assert identity.dependency_set_sha256 == DEPENDENCY_SET_SHA256
    assert identity.root_mutex_identity_sha256 == "4" * 64
    assert identity.campaign_mutex_identity_sha256 == "5" * 64
    assert captured["proof_locks"] is locks
    assert captured["timeout_seconds"] == {"A": 205.75, "B": 30.0}
    assert cast(dict[str, Any], captured["runtime_start_payload"])[
        "phase_timeout_contract"
    ] == _phase_timeout_contract()
    assert "phase_environments" not in captured
    assert events == [
        "preauthorize",
        "root-lock",
        "campaign-lock",
        "engine-open",
        "connection-open",
        "connection-rollback",
        "session-open",
        "source-open",
        "source-stable",
        "source-close",
        "context",
        "run",
        "session-close",
        "connection-close",
        "engine-dispose",
        "locks-close",
    ]


def test_public_dual_live_campaign_missing_environment_refuses_before_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    _install_dependency_verifier(monkeypatch)
    for key in tuple(os.environ):
        if key.upper() in frozenset(_PRODUCER_REQUIRED_ENV):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        dual_live_windows,
        "acquire_proof_locks_staged",
        lambda *_args, **_kwargs: pytest.fail("lock effect before refusal"),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module.run_dual_live_campaign(
            str(CAMPAIGN_ID),
            FINGERPRINT,
        )

    assert exc.value.code == "dual_live_producer_configuration_missing"


def test_public_dual_live_campaign_refuses_empty_database_before_source_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config
    from app.services import dual_live_windows

    _install_dependency_verifier(monkeypatch)
    _install_producer_environment(monkeypatch)
    settings = _producer_fake_settings(tmp_path)
    database_path = config._sqlite_database_path(settings.database_url)
    assert database_path is not None
    database_path.write_bytes(b"")
    monkeypatch.setattr(config, "Settings", lambda **_kwargs: settings)
    monkeypatch.setattr(config, "settings", settings)
    events: list[str] = []
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_preauthorize_producer_connectors",
        lambda **_kwargs: CODE_REVISION,
    )

    class _Locks:
        root_identity_sha256 = "4" * 64
        campaign_identity_sha256 = "5" * 64

        def close(self) -> None:
            events.append("locks-close")

    monkeypatch.setattr(
        dual_live_windows,
        "acquire_proof_locks_staged",
        lambda *_args, **_kwargs: events.append("locks-open") or _Locks(),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_derive_reviewed_runtime_source_identity",
        lambda: pytest.fail("source custody opened for invalid local state"),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module.run_dual_live_campaign(
            str(CAMPAIGN_ID),
            FINGERPRINT,
        )

    assert exc.value.code == "dual_live_producer_local_state_invalid"
    assert events == ["locks-open", "locks-close"]


def test_public_dual_live_campaign_refuses_garbage_database_before_source_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config
    from app.services import dual_live_windows

    _install_dependency_verifier(monkeypatch)
    _install_producer_environment(monkeypatch)
    settings = _producer_fake_settings(tmp_path)
    database_path = config._sqlite_database_path(settings.database_url)
    assert database_path is not None
    database_path.write_bytes(b"not-a-sqlite-database")
    monkeypatch.setattr(config, "Settings", lambda **_kwargs: settings)
    monkeypatch.setattr(config, "settings", settings)
    events: list[str] = []
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_preauthorize_producer_connectors",
        lambda **_kwargs: CODE_REVISION,
    )

    class _Locks:
        root_identity_sha256 = "4" * 64
        campaign_identity_sha256 = "5" * 64

        def close(self) -> None:
            events.append("locks-close")

    monkeypatch.setattr(
        dual_live_windows,
        "acquire_proof_locks_staged",
        lambda *_args, **_kwargs: events.append("locks-open") or _Locks(),
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_derive_reviewed_runtime_source_identity",
        lambda: pytest.fail("source custody opened for garbage database"),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module.run_dual_live_campaign(
            str(CAMPAIGN_ID),
            FINGERPRINT,
        )

    assert exc.value.code == "dual_live_producer_local_state_invalid"
    assert events == ["locks-open", "locks-close"]


def test_producer_database_refuses_empty_existing_database_before_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import sqlalchemy

    database_path = tmp_path / "empty.db"
    storage_path = tmp_path / "storage"
    database_path.write_bytes(b"")
    storage_path.mkdir()
    settings = SimpleNamespace(
        database_url=f"sqlite:///{database_path.as_posix()}",
        storage_dir=str(storage_path),
    )
    monkeypatch.setattr(
        sqlalchemy,
        "create_engine",
        lambda *_args, **_kwargs: pytest.fail("engine opened for empty database"),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._open_producer_database(settings)

    assert exc.value.code == "dual_live_producer_local_state_invalid"


def test_producer_database_refuses_missing_schema_or_replacement_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config
    import sqlalchemy
    import sqlalchemy.orm

    original_identity = dual_live_runtime_module._producer_database_file_identity
    for fault in ("schema", "replacement"):
        lane = tmp_path / fault
        lane.mkdir()
        settings = _producer_fake_settings(lane)
        database_path = config._sqlite_database_path(settings.database_url)
        assert database_path is not None
        events: list[str] = []
        identity_calls = 0

        def identity(path: Path) -> tuple[int, int, int, int]:
            nonlocal identity_calls
            identity_calls += 1
            value = original_identity(path)
            if fault == "replacement" and identity_calls == 4:
                return (*value[:3], value[3] + 1)
            return value

        class _Connection:
            def __init__(self) -> None:
                self.query_only = False

            def exec_driver_sql(
                self,
                statement: str,
            ) -> tuple[tuple[object, ...], ...]:
                if statement == "PRAGMA query_only = ON":
                    self.query_only = True
                    return ()
                if statement == "PRAGMA query_only = OFF":
                    self.query_only = False
                    return ()
                if statement == "PRAGMA query_only":
                    return ((1 if self.query_only else 0,),)
                if statement == "PRAGMA database_list":
                    return ((0, "main", str(database_path)),)
                if statement == "PRAGMA quick_check(1)":
                    return (("ok",),)
                if statement.startswith("SELECT name FROM sqlite_master"):
                    if fault == "schema":
                        return ()
                    return tuple((name,) for name in Base.metadata.tables)
                pytest.fail(f"unexpected producer DB statement: {statement}")

            def rollback(self) -> None:
                events.append("connection-rollback")

            def in_transaction(self) -> bool:
                return False

            def close(self) -> None:
                events.append("connection-close")

        connection = _Connection()

        class _Engine:
            def connect(self) -> _Connection:
                events.append("connection-open")
                return connection

            def dispose(self) -> None:
                events.append("engine-dispose")

        monkeypatch.setattr(
            dual_live_runtime_module,
            "_producer_database_file_identity",
            identity,
        )
        monkeypatch.setattr(
            sqlalchemy,
            "create_engine",
            lambda *_args, **_kwargs: events.append("engine-open") or _Engine(),
        )
        monkeypatch.setattr(
            sqlalchemy.orm,
            "Session",
            lambda **_kwargs: pytest.fail("Session created before DB proof"),
        )

        with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
            dual_live_runtime_module._open_producer_database(settings)

        assert exc.value.code == "dual_live_producer_local_state_invalid"
        if fault == "schema":
            assert events == [
                "engine-open",
                "connection-open",
                "connection-close",
                "engine-dispose",
            ]
        else:
            assert events == [
                "engine-open",
                "connection-open",
                "connection-rollback",
                "connection-close",
                "engine-dispose",
            ]
            assert identity_calls == 4


def test_producer_local_state_rejects_sqlite_uri_options_and_file_form(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime.db"
    storage_path = tmp_path / "storage"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE fixture (id INTEGER PRIMARY KEY)")
    storage_path.mkdir()
    canonical = f"sqlite:///{database_path.as_posix()}"
    unsafe_urls = (
        f"sqlite:///file:{database_path.as_posix()}?uri=true",
        f"sqlite:///file:{database_path.as_posix()}?mode=memory&uri=true",
        f"sqlite:///file:{database_path.as_posix()}?mode=ro&uri=true",
        f"sqlite:///file:{database_path.as_posix()}?immutable=1&uri=true",
        f"sqlite:///file:{database_path.as_posix()}?nolock=1&uri=true",
        f"{canonical}?uri=true",
        f"{canonical}#alternate",
    )

    for database_url in unsafe_urls:
        settings = SimpleNamespace(
            database_url=database_url,
            storage_dir=str(storage_path),
        )
        with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
            dual_live_runtime_module._validate_producer_local_state(settings)
        assert exc.value.code == "dual_live_producer_local_state_invalid"


def test_producer_local_state_rejects_unc_before_path_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.core import config

    storage_path = tmp_path / "storage"
    storage_path.mkdir()
    monkeypatch.setattr(
        config,
        "_sqlite_database_path",
        lambda _url: pytest.fail("UNC path reached filesystem resolution"),
    )
    settings = SimpleNamespace(
        database_url="sqlite://///server/share/runtime.db",
        storage_dir=str(storage_path),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._validate_producer_local_state(settings)

    assert exc.value.code == "dual_live_producer_local_state_invalid"


def test_producer_local_state_rejects_reparse_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reparse_root = tmp_path / "reparse"
    reparse_root.mkdir()
    database_path = reparse_root / "runtime.db"
    storage_path = tmp_path / "storage"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE fixture (id INTEGER PRIMARY KEY)")
    storage_path.mkdir()
    real_lstat = os.lstat
    reparse_mode = real_lstat(reparse_root).st_mode

    def lstat(path: str | os.PathLike[str]) -> os.stat_result | object:
        if Path(path) == reparse_root:
            return SimpleNamespace(
                st_file_attributes=0x400,
                st_mode=reparse_mode,
                st_size=0,
            )
        return real_lstat(path)

    monkeypatch.setattr(os, "lstat", lstat)
    settings = SimpleNamespace(
        database_url=f"sqlite:///{database_path.as_posix()}",
        storage_dir=str(storage_path),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._validate_producer_local_state(settings)

    assert exc.value.code == "dual_live_producer_local_state_invalid"


def test_staged_producer_resolver_rederives_full_current_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import (
        connector_campaign_log_capture as capture_service,
        connector_egress_authorization as egress_service,
    )

    settings = SimpleNamespace(
        connector_campaign_definition_path=Path("C:/protected/campaign.json"),
        connector_campaign_definition_sha256=DEFINITION_SHA256,
    )
    events: list[str] = []

    def read(*_args: object, **kwargs: object) -> tuple[Path, bytes, str]:
        assert kwargs["settings_override"] is settings
        events.append("definition-read")
        return (
            settings.connector_campaign_definition_path,
            DEFINITION_BYTES,
            DEFINITION_SHA256,
        )

    def current(**kwargs: object) -> object:
        assert kwargs["campaign_id"] == CAMPAIGN_ID
        assert kwargs["expected_campaign_fingerprint"] == FINGERPRINT
        assert kwargs["expected_code_revision"] == CODE_REVISION
        events.append("current-authority")
        return SimpleNamespace(
            campaign_id=str(CAMPAIGN_ID),
            campaign_fingerprint=FINGERPRINT,
            campaign_definition_sha256=DEFINITION_SHA256,
            code_revision=CODE_REVISION,
        )

    monkeypatch.setattr(egress_service, "_read_protected_bytes", read)
    monkeypatch.setattr(
        egress_service,
        "_parse_model",
        lambda *_args, **_kwargs: events.append("definition-parse")
        or CAMPAIGN_MODEL,
    )
    monkeypatch.setattr(capture_service, "_current_authority", current)

    assert dual_live_runtime_module._resolve_staged_campaign_definition_sha256(
        settings,
        str(CAMPAIGN_ID),
        FINGERPRINT,
    ) == DEFINITION_SHA256
    assert events == [
        "definition-read",
        "definition-parse",
        "current-authority",
    ]


def test_strict_runner_public_mode_reaches_runtime_and_emits_canonical_json(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    from app.services import dual_live_windows

    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    spec = importlib.util.spec_from_file_location("dual_live_run_test", tool_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    calls: list[tuple[str, str]] = []
    report = {
        "campaign_id": str(CAMPAIGN_ID),
        "campaign_fingerprint": FINGERPRINT,
        "code": "dual_live_campaign_sealed",
        "event_ids": [],
        "file_set_hash": "7" * 64,
        "manifest_sha256": "6" * 64,
        "schema_id": "project6.dual_live_campaign_run.v1",
        "seal_sha256": "8" * 64,
        "status": "SEALED",
    }
    monkeypatch.setattr(
        dual_live_runtime_module,
        "run_dual_live_campaign",
        lambda campaign_id, fingerprint: (
            calls.append((campaign_id, fingerprint)) or report
        ),
        raising=False,
    )

    class _NoopGuards:
        def __init__(self, phase: str) -> None:
            assert phase == "wrapper"
            self._guard = lambda *_args, **_kwargs: None

        def install_wrapper_network_denial(self) -> None:
            return None

        def install(self) -> None:
            return None

        def assert_intact(self) -> None:
            return None

    monkeypatch.setattr(runner, "_StandardLibraryGuards", _NoopGuards)
    monkeypatch.setattr(
        runner,
        "_assert_wrapper_backend_not_preloaded",
        lambda: None,
    )
    monkeypatch.setattr(
        dual_live_windows,
        "_register_subprocess_gate_baseline",
        lambda _guard: None,
    )
    monkeypatch.setattr(runner, "_preflight_public_paths", lambda _env: None)
    monkeypatch.setattr(
        runner,
        "_install_wrapper_connector_import_guard",
        lambda: None,
    )

    assert runner._run_public_mode(
        (
            "--campaign-id",
            str(CAMPAIGN_ID),
            "--campaign-fingerprint",
            FINGERPRINT,
        )
    ) == 0
    captured = capfd.readouterr()
    assert captured.out.encode("utf-8") == canonical_json_bytes(report) + b"\n"
    assert captured.err == ""
    assert calls == [(str(CAMPAIGN_ID), FINGERPRINT)]

    assert runner._run_public_mode(
        ("--campaign-id", str(CAMPAIGN_ID), "--unexpected", "value")
    ) == 2
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == "dual_live_run_refused\n"
    assert calls == [(str(CAMPAIGN_ID), FINGERPRINT)]


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume public-path proof only")
def test_strict_runner_public_mode_is_reachable_under_reviewed_posture(
    tmp_path: Path,
) -> None:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    report = {
        "campaign_id": str(CAMPAIGN_ID),
        "campaign_fingerprint": FINGERPRINT,
        "code": "dual_live_campaign_sealed",
        "event_ids": [],
        "file_set_hash": "7" * 64,
        "manifest_sha256": "6" * 64,
        "schema_id": "project6.dual_live_campaign_run.v1",
        "seal_sha256": "8" * 64,
        "status": "SEALED",
    }
    probe = "\n".join(
        (
            "import importlib.abc, importlib.util, sys, warnings",
            "warnings.filterwarnings('ignore')",
            "class RuntimeLoader(importlib.abc.Loader):",
            "    def create_module(self, spec):",
            "        return None",
            "    def exec_module(self, module):",
            "        def run(campaign_id, fingerprint):",
            "            from app.services import dual_live_windows as windows",
            "            windows._require_reviewed_controller_python_posture()",
            f"            return {report!r}",
            "        module.run_dual_live_campaign = run",
            "class RuntimeFinder(importlib.abc.MetaPathFinder):",
            "    def find_spec(self, fullname, path, target=None):",
            "        if fullname == 'app.services.dual_live_runtime':",
            "            return importlib.util.spec_from_loader(fullname, RuntimeLoader())",
            "        return None",
            "sys.meta_path.insert(0, RuntimeFinder())",
            f"spec = importlib.util.spec_from_file_location('dual_live_run_probe', {str(tool_path)!r})",
            "runner = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(runner)",
            f"sys.argv = ['dual_live_run.py', '--campaign-id', {str(CAMPAIGN_ID)!r}, '--campaign-fingerprint', {FINGERPRINT!r}]",
            "raise SystemExit(runner.main())",
        )
    )
    environment = {
        name: os.environ[name]
        for name in ("COMSPEC", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if name in os.environ
    }
    public_root = tmp_path / "public"
    evidence_root = public_root / "evidence"
    storage_root = public_root / "storage"
    evidence_root.mkdir(parents=True)
    storage_root.mkdir()
    definition_path = public_root / "definition.json"
    sciencebase_path = public_root / "sciencebase.json"
    nrc_path = public_root / "nrc.json"
    index_path = evidence_root / "index.json"
    database_path = public_root / "proof.db"
    for path in (
        definition_path,
        sciencebase_path,
        nrc_path,
        index_path,
        database_path,
    ):
        path.touch()
    environment.update(
        {
            "CONNECTOR_CAMPAIGN_DEFINITION_PATH": str(definition_path),
            "CONNECTOR_SCIENCEBASE_GRANT_PATH": str(sciencebase_path),
            "CONNECTOR_NRC_APS_GRANT_PATH": str(nrc_path),
            "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(evidence_root),
            "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(index_path),
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "STORAGE_DIR": str(storage_root),
        }
    )

    completed = subprocess.run(
        (sys.executable, "-I", "-B", "-c", probe),
        check=False,
        capture_output=True,
        env=environment,
        timeout=10,
    )

    assert completed.returncode == 0
    assert completed.stdout == canonical_json_bytes(report) + b"\n"
    assert completed.stderr == b""
    assert "spawnve" not in tool_path.read_text(encoding="utf-8")


def test_strict_runner_redirects_repo_bytecode_before_public_import(
    tmp_path: Path,
) -> None:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_run.py"
    module_root = tmp_path / "modules"
    module_root.mkdir()
    source_path = module_root / "posture_probe.py"
    source_path.write_text("VALUE = 'evil'\n", encoding="utf-8")
    source_stat = source_path.stat()
    py_compile.compile(str(source_path), doraise=True)
    source_path.write_text("VALUE = 'safe'\n", encoding="utf-8")
    os.utime(
        source_path,
        ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
    )
    environment = {
        name: os.environ[name]
        for name in ("COMSPEC", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if name in os.environ
    }
    baseline = subprocess.run(
        (
            sys.executable,
            "-I",
            "-B",
            "-c",
            f"import sys;sys.path.insert(0,{str(module_root)!r});"
            "import posture_probe;print(posture_probe.VALUE)",
        ),
        check=False,
        capture_output=True,
        env=environment,
        timeout=10,
    )
    assert baseline.returncode == 0
    assert baseline.stdout == b"evil" + os.linesep.encode("ascii")

    probe = "\n".join(
        (
            "import importlib.util, sys",
            f"spec = importlib.util.spec_from_file_location('dual_live_run_probe', {str(tool_path)!r})",
            "runner = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(runner)",
            "def public(arguments):",
            f"    sys.path.insert(0, {str(module_root)!r})",
            "    import posture_probe",
            "    print(posture_probe.VALUE)",
            "    return 0 if posture_probe.VALUE == 'safe' else 7",
            "runner._run_public_mode = public",
            "sys.argv = ['dual_live_run.py', '--campaign-id', 'x', "
            "'--campaign-fingerprint', 'y']",
            "raise SystemExit(runner.main())",
        )
    )
    completed = subprocess.run(
        (sys.executable, "-I", "-B", "-c", probe),
        check=False,
        capture_output=True,
        env=environment,
        timeout=10,
    )

    assert completed.returncode == 0
    assert completed.stdout == b"safe" + os.linesep.encode("ascii")
    assert completed.stderr == b""


def test_read_only_capture_verifier_refuses_external_bind_transaction(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority, chain, _ = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    _close_read_transaction(db)
    engine = db.get_bind()
    connection = engine.connect()  # type: ignore[union-attr]
    external_transaction = connection.begin()
    external_run_id = "external-uncommitted-run"
    connection.execute(
        ConnectorRun.__table__.insert().values(
            connector_run_id=external_run_id,
            connector_key="fixture",
            source_system="fixture",
            source_mode="public_api",
            status="pending",
        )
    )
    caller = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    before_row = connection.execute(
        select(ConnectorRun.__table__).where(
            ConnectorRun.connector_run_id == external_run_id
        )
    ).mappings().one()

    def forbidden_verification(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("verifier read through an externally transacted bind")

    monkeypatch.setattr(
        capture_service,
        "_verify_connector_campaign_log_capture_in_owned_transaction",
        forbidden_verification,
    )
    try:
        assert not caller.in_transaction()
        with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
            verify_connector_campaign_log_capture_read_only(
                caller,
                chain,
                str(authority.campaign_id),
                FINGERPRINT,
            )
        assert excinfo.value.code == "connector_campaign_log_read_transaction_active"
        assert not caller.in_transaction()
        assert external_transaction.is_active
        assert connection.in_transaction()
        after_row = connection.execute(
            select(ConnectorRun.__table__).where(
                ConnectorRun.connector_run_id == external_run_id
            )
        ).mappings().one()
        assert after_row == before_row
    finally:
        caller.close()
        if external_transaction.is_active:
            external_transaction.rollback()
        connection.close()


def test_read_only_capture_verifier_rechecks_final_campaign_membership(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture as capture_service

    authority, chain, _ = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
        connector_keys=("nrc_adams_aps",),
    )
    original = capture_service._verify_index_chain_snapshot
    calls = 0

    def inject_late_member(candidate: VerifiedEvidenceIndexChain) -> Path:
        nonlocal calls
        calls += 1
        result = original(candidate)
        if calls == 2:
            late = authority.evidence_root / "logs" / FINGERPRINT / "late.log"
            late.write_bytes(b"late")
        return result

    monkeypatch.setattr(
        capture_service,
        "_verify_index_chain_snapshot",
        inject_late_member,
    )
    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        verify_connector_campaign_log_capture_read_only(
            db,
            chain,
            str(authority.campaign_id),
            FINGERPRINT,
        )

    assert excinfo.value.code == "connector_campaign_log_stream_membership_invalid"
    assert not db.in_transaction()


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        ("manifest_only", "connector_campaign_log_read_seal_mismatch"),
        (
            "manifest_and_seal",
            "connector_campaign_log_read_seal_event_mismatch",
        ),
        (
            "extra_manifest_member",
            "connector_campaign_log_stream_membership_invalid",
        ),
        (
            "extra_index_object",
            "connector_campaign_log_index_membership_invalid",
        ),
        (
            "manifest_code_identity",
            "connector_campaign_log_read_identity_mismatch",
        ),
        (
            "seal_introduction_identity",
            "connector_campaign_log_read_identity_mismatch",
        ),
    ),
)
def test_read_only_capture_verifier_rejects_filesystem_rewrites_without_repair(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority, chain, sealed = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
    )
    manifest_path, seal_path = _artifact_paths(authority)
    if case in {"manifest_only", "manifest_and_seal"}:
        _, manifest_sha256, file_set_hash = _rewrite_stream_and_manifest(
            authority,
            sealed,
        )
        if case == "manifest_and_seal":
            rewritten_seal = type(sealed.seal).model_validate(
                {
                    **sealed.seal.model_dump(mode="python"),
                    "manifest_sha256": manifest_sha256,
                    "file_set_hash": file_set_hash,
                }
            )
            seal_path.write_bytes(canonical_json_bytes(rewritten_seal))
    elif case == "extra_manifest_member":
        (manifest_path.parent / "undeclared.log").write_bytes(b"extra")
    elif case == "extra_index_object":
        (authority.evidence_root / "indexes" / "undeclared.json").write_bytes(
            b"{}"
        )
    elif case == "manifest_code_identity":
        rewritten_manifest = type(sealed.manifest).model_validate(
            {
                **sealed.manifest.model_dump(mode="python"),
                "code_revision": "1" * 40,
            }
        )
        manifest_path.write_bytes(canonical_json_bytes(rewritten_manifest))
    else:
        rewritten_seal = type(sealed.seal).model_validate(
            {
                **sealed.seal.model_dump(mode="python"),
                "campaign_introduction_index_sha256": "1" * 64,
            }
        )
        seal_path.write_bytes(canonical_json_bytes(rewritten_seal))
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)
    _close_read_transaction(db)

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        verify_connector_campaign_log_capture_read_only(
            db,
            chain,
            str(authority.campaign_id),
            FINGERPRINT,
        )

    assert excinfo.value.code == expected_code
    assert not db.in_transaction()
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before


@pytest.mark.parametrize(
    ("case", "expected_code"),
    (
        ("delete", "connector_campaign_log_read_seal_event_set_invalid"),
        ("duplicate", "connector_campaign_log_read_seal_event_mismatch"),
        ("rewrite", "connector_campaign_log_read_seal_event_mismatch"),
    ),
)
def test_read_only_capture_verifier_rejects_seal_event_rewrites_without_repair(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    expected_code: str,
) -> None:
    authority, chain, sealed = _sealed_read_only_fixture(
        db,
        monkeypatch,
        tmp_path,
    )
    event = db.scalar(
        select(ConnectorRunEvent)
        .where(
            ConnectorRunEvent.connector_run_event_id
            == sealed.event_ids[0]
        )
    )
    assert event is not None
    if case == "delete":
        db.delete(event)
    elif case == "duplicate":
        db.add(
            ConnectorRunEvent(
                connector_run_event_id=str(uuid4()),
                connector_run_id=event.connector_run_id,
                connector_run_target_id=event.connector_run_target_id,
                phase=event.phase,
                stage=event.stage,
                event_type=event.event_type,
                status_before=event.status_before,
                status_after=event.status_after,
                reason_code=event.reason_code,
                error_class=event.error_class,
                message=event.message,
                metrics_json=dict(event.metrics_json),
                created_at=event.created_at,
            )
        )
    else:
        event.metrics_json = {
            **event.metrics_json,
            "file_set_hash": "1" * 64,
        }
    db.commit()
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)
    _close_read_transaction(db)

    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        verify_connector_campaign_log_capture_read_only(
            db,
            chain,
            str(authority.campaign_id),
            FINGERPRINT,
        )

    assert excinfo.value.code == expected_code
    assert not db.in_transaction()
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before


def test_production_owned_binding_signature_has_no_injection_seams() -> None:
    factory = getattr(
        dual_live_runtime_module,
        "_make_production_owned_controller_context",
    )
    runner = getattr(
        dual_live_runtime_module,
        "_run_production_owned_two_phase_controller",
    )

    signature = inspect.signature(factory)
    assert tuple(signature.parameters) == (
        "campaign_id",
        "expected_campaign_fingerprint",
        "db",
        "identity",
        "runtime_start_payload",
        "timeout_seconds",
        "proof_locks",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert not {
        "capture",
        "writers",
        "writer",
        "process_factory",
        "quiesce",
        "seal",
        "clock",
        "now",
        "path",
        "environment",
    }.intersection(signature.parameters)
    assert tuple(inspect.signature(runner).parameters) == ("context",)

def _production_identity_and_payload(
    locks: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[RuntimeIdentity, dict[str, Any]]:
    from app.services import dual_live_windows

    identity = RuntimeIdentity(
        runtime_instance_id=str(uuid4()),
        wrapper_nonce_sha256="1" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="2" * 64,
        interpreter_image_sha256="3" * 64,
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
        root_mutex_identity_sha256=locks.root_identity_sha256,
        campaign_mutex_identity_sha256=locks.campaign_identity_sha256,
    )
    source_custody = SimpleNamespace(
        code_revision=identity.code_revision,
        wrapper_image_sha256=identity.wrapper_image_sha256,
        interpreter_image_sha256=identity.interpreter_image_sha256,
        assert_stable=lambda: None,
        close=lambda: None,
    )
    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        lambda: source_custody,
    )
    return identity, {
        "code_revision": CODE_REVISION,
        "wrapper_image_sha256": identity.wrapper_image_sha256,
        "interpreter_image_sha256": identity.interpreter_image_sha256,
        "dependency_set_sha256": identity.dependency_set_sha256,
        "phase_timeout_contract": _phase_timeout_contract(),
        "mutex_identity_sha256": (
            dual_live_runtime_module._combined_mutex_identity_sha256(identity)
        ),
    }


def _production_capture_owner(
    context: dual_live_runtime_module._ProductionOwnedControllerContext,
) -> dual_live_runtime_module._OwnedCampaignCapture:
    capture = cast(
        dual_live_runtime_module._OwnedCampaignCapture,
        context._capture,
    )
    assert type(capture) is dual_live_runtime_module._OwnedCampaignCapture
    return capture


def _raw_production_context_for_failure(
    *,
    capture_close_error: BaseException | None = None,
    source_close_error: BaseException | None = None,
) -> dual_live_runtime_module._ProductionOwnedControllerContext:
    context = object.__new__(
        dual_live_runtime_module._ProductionOwnedControllerContext
    )

    class _Capture:
        sealed = False

        def _abort_close(self) -> BaseException | None:
            return capture_close_error

    class _Source:
        def close(self) -> None:
            if source_close_error is not None:
                raise source_close_error

    object.__setattr__(context, "_capture", _Capture())
    object.__setattr__(context, "_source_custody", _Source())
    object.__setattr__(context, "_source_custody_closed", False)
    return context


def test_production_post_go_timeout_requires_operator_inspection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_exit_timeout"
    )
    context = _raw_production_context_for_failure()
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        lambda _context: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert exc.value.code == "dual_live_phase_timeout_inspection_required"
    assert exc.value.__cause__ is primary
    assert context._capture.sealed is False


def test_production_pre_go_census_timeout_keeps_replay_safe_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_census_failed"
    )
    context = _raw_production_context_for_failure()
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        lambda _context: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert exc.value is primary


def test_production_earlier_primary_is_not_reclassified_by_cleanup_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_control_invalid"
    )
    primary.__context__ = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_exit_timeout"
    )
    context = _raw_production_context_for_failure()
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        lambda _context: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert exc.value is primary


def test_production_timeout_preserves_capture_cleanup_failure_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_exit_timeout"
    )
    capture_error = OSError("bounded fixture close failure")
    context = _raw_production_context_for_failure(
        capture_close_error=capture_error
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        lambda _context: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert exc.value.code == "dual_live_capture_close_failed"
    assert exc.value.__cause__ is capture_error
    assert capture_error.__context__ is primary


def test_production_phase_failure_preserves_cleanup_failure_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = dual_live_runtime_module.DualLiveRuntimeError(
        "dual_live_phase_failed"
    )
    capture_error = OSError("bounded fixture close failure")
    context = _raw_production_context_for_failure(
        capture_close_error=capture_error
    )
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        lambda _context: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(dual_live_runtime_module.DualLiveRuntimeError) as exc:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert exc.value.code == "dual_live_capture_close_failed"
    assert exc.value.__cause__ is capture_error
    assert capture_error.__context__ is primary


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_binding_derives_source_identity_before_capture(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture, dual_live_windows

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    events: list[str] = []

    class _SourceCustody:
        code_revision = identity.code_revision
        wrapper_image_sha256 = "4" * 64
        interpreter_image_sha256 = identity.interpreter_image_sha256

        def assert_stable(self) -> None:
            events.append("stable")

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        _SourceCustody,
        raising=False,
    )

    def forbidden_begin(**_kwargs: Any) -> Any:
        pytest.fail("forged source identity reached canonical capture begin")

    monkeypatch.setattr(
        connector_campaign_log_capture,
        "begin_connector_campaign_log_capture",
        forbidden_begin,
    )
    try:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError
        ) as excinfo:
            dual_live_runtime_module._make_production_owned_controller_context(
                campaign_id=str(authority.campaign_id),
                expected_campaign_fingerprint=FINGERPRINT,
                db=db,
                identity=identity,
                runtime_start_payload=start_payload,
                timeout_seconds=2,
                proof_locks=locks,
            )
        assert excinfo.value.code == "dual_live_runtime_identity_mismatch"
        assert events == ["stable", "close"]
        _assert_unpublished(authority)
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_binding_normalizes_source_cleanup_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)

    class SourceCloseProbe(RuntimeError):
        pass

    class _SourceCustody:
        code_revision = identity.code_revision
        wrapper_image_sha256 = "4" * 64
        interpreter_image_sha256 = identity.interpreter_image_sha256

        def assert_stable(self) -> None:
            return None

        def close(self) -> None:
            raise SourceCloseProbe("source close")

    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        _SourceCustody,
    )
    try:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError
        ) as excinfo:
            dual_live_runtime_module._make_production_owned_controller_context(
                campaign_id=str(authority.campaign_id),
                expected_campaign_fingerprint=FINGERPRINT,
                db=db,
                identity=identity,
                runtime_start_payload=start_payload,
                timeout_seconds=2,
                proof_locks=locks,
            )
        assert excinfo.value.code == "dual_live_source_identity_cleanup_failed"
        assert isinstance(excinfo.value.__cause__, SourceCloseProbe)
        assert isinstance(
            excinfo.value.__context__,
            dual_live_runtime_module.DualLiveRuntimeError,
        )
        assert excinfo.value.__context__.code == "dual_live_runtime_identity_mismatch"
        _assert_unpublished(authority)
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_binding_capture_cleanup_precedes_source_cleanup(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)

    class FactoryProbe(RuntimeError):
        pass

    class CaptureCloseProbe(RuntimeError):
        pass

    class SourceCloseProbe(RuntimeError):
        pass

    class _SourceCustody:
        code_revision = identity.code_revision
        wrapper_image_sha256 = identity.wrapper_image_sha256
        interpreter_image_sha256 = identity.interpreter_image_sha256

        def assert_stable(self) -> None:
            return None

        def close(self) -> None:
            raise SourceCloseProbe("source close")

    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        _SourceCustody,
    )

    def reject_owned_capture(**_kwargs: Any) -> Any:
        raise FactoryProbe("owned capture")

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_OwnedCampaignCapture",
        reject_owned_capture,
    )
    original_close = dual_live_runtime_module._close_incomplete_campaign_capture

    def close_then_fail(capture: Any) -> BaseException:
        assert original_close(capture) is None
        return CaptureCloseProbe("capture close")

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_close_incomplete_campaign_capture",
        close_then_fail,
    )
    try:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError
        ) as excinfo:
            dual_live_runtime_module._make_production_owned_controller_context(
                campaign_id=str(authority.campaign_id),
                expected_campaign_fingerprint=FINGERPRINT,
                db=db,
                identity=identity,
                runtime_start_payload=start_payload,
                timeout_seconds=2,
                proof_locks=locks,
            )
        assert excinfo.value.code == "dual_live_capture_close_failed"
        assert isinstance(excinfo.value.__cause__, CaptureCloseProbe)
        assert isinstance(excinfo.value.__cause__.__context__, SourceCloseProbe)
        assert isinstance(
            excinfo.value.__cause__.__context__.__context__,
            FactoryProbe,
        )
        _assert_unpublished(authority)
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_runner_retains_run_and_both_cleanup_failures(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    context = dual_live_runtime_module._make_production_owned_controller_context(
        campaign_id=str(authority.campaign_id),
        expected_campaign_fingerprint=FINGERPRINT,
        db=db,
        identity=identity,
        runtime_start_payload=start_payload,
        timeout_seconds=2,
        proof_locks=locks,
    )

    class RunProbe(RuntimeError):
        pass

    class CaptureCloseProbe(RuntimeError):
        pass

    class SourceCloseProbe(RuntimeError):
        pass

    def fail_run(_context: object) -> Any:
        raise RunProbe("run")

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        fail_run,
    )
    original_abort = dual_live_runtime_module._OwnedCampaignCapture._abort_close

    def abort_then_fail(self: Any) -> BaseException:
        assert original_abort(self) is None
        return CaptureCloseProbe("capture close")

    monkeypatch.setattr(
        dual_live_runtime_module._OwnedCampaignCapture,
        "_abort_close",
        abort_then_fail,
    )
    original_source_close = (
        dual_live_runtime_module._ProductionOwnedControllerContext._close_source_custody
    )

    def source_then_fail(self: Any) -> BaseException:
        assert original_source_close(self) is None
        return SourceCloseProbe("source close")

    monkeypatch.setattr(
        dual_live_runtime_module._ProductionOwnedControllerContext,
        "_close_source_custody",
        source_then_fail,
    )
    try:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError
        ) as excinfo:
            dual_live_runtime_module._run_production_owned_two_phase_controller(
                context
            )
        assert excinfo.value.code == "dual_live_capture_close_failed"
        assert isinstance(excinfo.value.__cause__, CaptureCloseProbe)
        assert isinstance(excinfo.value.__cause__.__context__, SourceCloseProbe)
        assert isinstance(
            excinfo.value.__cause__.__context__.__context__,
            RunProbe,
        )
        _assert_unpublished(authority)
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_binding_refuses_inactive_locks_before_capture(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture, dual_live_windows

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    source_calls: list[str] = []

    def forbidden_source_custody() -> Any:
        source_calls.append("acquire")
        pytest.fail("inactive locks reached source custody acquisition")

    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        forbidden_source_custody,
    )
    locks.close()
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)

    def forbidden_begin(**_kwargs: Any) -> Any:
        pytest.fail("inactive locks reached canonical capture begin")

    monkeypatch.setattr(
        connector_campaign_log_capture,
        "begin_connector_campaign_log_capture",
        forbidden_begin,
    )
    with pytest.raises(dual_live_windows.DualLiveWindowsError) as excinfo:
        dual_live_runtime_module._make_production_owned_controller_context(
            campaign_id=str(authority.campaign_id),
            expected_campaign_fingerprint=FINGERPRINT,
            db=db,
            identity=identity,
            runtime_start_payload=start_payload,
            timeout_seconds=2,
            proof_locks=locks,
        )

    assert excinfo.value.code == "dual_live_proof_locks_inactive"
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before
    assert source_calls == []
    _assert_unpublished(authority)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_binding_refuses_dirty_db_before_capture(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture, dual_live_windows

    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)

    def forbidden_begin(**_kwargs: Any) -> Any:
        pytest.fail("dirty DB session reached canonical capture begin")

    monkeypatch.setattr(
        connector_campaign_log_capture,
        "begin_connector_campaign_log_capture",
        forbidden_begin,
    )
    try:
        with db.begin():
            with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
                dual_live_runtime_module._make_production_owned_controller_context(
                    campaign_id=str(authority.campaign_id),
                    expected_campaign_fingerprint=FINGERPRINT,
                    db=db,
                    identity=identity,
                    runtime_start_payload=start_payload,
                    timeout_seconds=2,
                    proof_locks=locks,
                )
        assert excinfo.value.code == "connector_campaign_log_session_not_clean"
        _assert_unpublished(authority)
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_runner_refuses_lost_locks_before_child_and_seal(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _bind_real_evidence_index(authority)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)

    def forbidden_child(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("lost locks reached child creation")

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        forbidden_child,
    )
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    context = (
        dual_live_runtime_module._make_production_owned_controller_context(
            campaign_id=str(authority.campaign_id),
            expected_campaign_fingerprint=FINGERPRINT,
            db=db,
            identity=identity,
            runtime_start_payload=start_payload,
            timeout_seconds=2,
            proof_locks=locks,
        )
    )
    capture_owner = _production_capture_owner(context)
    capture = capture_owner._capture
    evidence_before = _evidence_bytes(authority.evidence_root)
    runs_before = _connector_run_rows(db)
    events_before = _connector_event_rows(db)
    locks.close()

    with pytest.raises(dual_live_windows.DualLiveWindowsError) as excinfo:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert excinfo.value.code == "dual_live_proof_locks_inactive"
    assert all(writer.closed for writer in capture.writers)
    assert context.sealed is False
    assert _evidence_bytes(authority.evidence_root) == evidence_before
    assert _connector_run_rows(db) == runs_before
    assert _connector_event_rows(db) == events_before
    assert (authority.evidence_root / "logs" / FINGERPRINT).is_dir()
    _assert_unpublished(authority)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_runner_preserves_writers_when_ownership_unproven(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _bind_real_evidence_index(authority)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    context = (
        dual_live_runtime_module._make_production_owned_controller_context(
            campaign_id=str(authority.campaign_id),
            expected_campaign_fingerprint=FINGERPRINT,
            db=db,
            identity=identity,
            runtime_start_payload=start_payload,
            timeout_seconds=2,
            proof_locks=locks,
        )
    )
    capture_owner = _production_capture_owner(context)
    capture = capture_owner._capture

    def ownership_unproven(_context: object) -> Any:
        raise dual_live_runtime_module.DualLiveRuntimeError(
            "dual_live_capture_ownership_unproven"
        )

    monkeypatch.setattr(
        dual_live_runtime_module,
        "_run_bound_owned_two_phase_controller",
        ownership_unproven,
    )
    try:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError
        ) as excinfo:
            dual_live_runtime_module._run_production_owned_two_phase_controller(
                context
            )

        assert excinfo.value.code == "dual_live_capture_ownership_unproven"
        assert all(not writer.closed for writer in capture.writers)
        assert context.sealed is False
        _assert_unpublished(authority)
    finally:
        locks.close()
        assert capture_owner._abort_close() is None


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_runner_closes_child_if_locks_lost_during_create(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _bind_real_evidence_index(authority)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    context = (
        dual_live_runtime_module._make_production_owned_controller_context(
            campaign_id=str(authority.campaign_id),
            expected_campaign_fingerprint=FINGERPRINT,
            db=db,
            identity=identity,
            runtime_start_payload=start_payload,
            timeout_seconds=2,
            proof_locks=locks,
        )
    )
    capture_owner = _production_capture_owner(context)
    capture = capture_owner._capture
    events: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        events.append(f"create-{phase}")
        locks.close()
        return _CaptureOwnedPhaseProcess(phase, events)

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
    )
    with pytest.raises(
        dual_live_runtime_module.DualLiveRuntimeError
    ) as excinfo:
        dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )

    assert excinfo.value.code == "dual_live_phase_failed"
    assert isinstance(
        excinfo.value.__cause__,
        dual_live_windows.DualLiveWindowsError,
    )
    assert excinfo.value.__cause__.code == "dual_live_proof_locks_inactive"
    assert events == [
        "create-A",
        "revoke-A-protocol_failure",
        "close-A",
    ]
    assert all(writer.closed for writer in capture.writers)
    assert context.sealed is False
    _assert_unpublished(authority)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_runner_refuses_child_interpreter_mismatch(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import dual_live_windows

    authority = _authority_fixture(tmp_path)
    _bind_real_evidence_index(authority)
    _install_authority(monkeypatch, authority)

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return START

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)
    context = dual_live_runtime_module._make_production_owned_controller_context(
        campaign_id=str(authority.campaign_id),
        expected_campaign_fingerprint=FINGERPRINT,
        db=db,
        identity=identity,
        runtime_start_payload=start_payload,
        timeout_seconds=2,
        proof_locks=locks,
    )
    capture_owner = _production_capture_owner(context)
    events: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        process = _CaptureOwnedPhaseProcess(phase, events)
        process.executable_sha256 = "9" * 64
        return process

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
    )
    try:
        with pytest.raises(
            dual_live_runtime_module.DualLiveRuntimeError
        ) as excinfo:
            dual_live_runtime_module._run_production_owned_two_phase_controller(
                context
            )
        assert excinfo.value.code == "dual_live_runtime_identity_mismatch"
        assert events == [
            "revoke-A-protocol_failure",
            "close-A",
        ]
        assert all(writer.closed for writer in capture_owner._capture.writers)
        assert context.sealed is False
        _assert_unpublished(authority)
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_production_owned_binding_begins_runs_and_seals_canonical_capture(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services import connector_campaign_log_capture, dual_live_windows

    authority = _authority_fixture(tmp_path)
    chain = _bind_real_evidence_index(authority)
    _install_authority(monkeypatch, authority)
    connector_keys = ("nrc_adams_aps", "sciencebase_mcs")
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=connector_keys,
    )

    clock_values = iter(
        (
            START,
            START + timedelta(seconds=10),
        )
    )

    class _Clock:
        @classmethod
        def now(cls, _tz: object = None) -> datetime:
            return next(clock_values)

    monkeypatch.setattr(dual_live_runtime_module, "datetime", _Clock)
    events: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        events.append(f"create-{phase}")
        return _CaptureOwnedPhaseProcess(phase, events)

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
    )

    locks = dual_live_windows.acquire_proof_locks(
        authority.evidence_root,
        str(authority.campaign_id),
        FINGERPRINT,
        DEFINITION_SHA256,
    )
    identity, start_payload = _production_identity_and_payload(locks, monkeypatch)

    class _SourceCustody:
        code_revision = identity.code_revision
        wrapper_image_sha256 = identity.wrapper_image_sha256
        interpreter_image_sha256 = identity.interpreter_image_sha256

        def assert_stable(self) -> None:
            events.append("source-stable")

        def close(self) -> None:
            events.append("source-close")

    monkeypatch.setattr(
        dual_live_windows,
        "_acquire_reviewed_source_custody",
        _SourceCustody,
    )
    canonical_seal = (
        connector_campaign_log_capture.seal_connector_campaign_log_capture
    )

    def seal(*args: Any, **kwargs: Any) -> Any:
        events.append("seal")
        return canonical_seal(*args, **kwargs)

    monkeypatch.setattr(
        connector_campaign_log_capture,
        "seal_connector_campaign_log_capture",
        seal,
    )
    try:
        context = (
            dual_live_runtime_module._make_production_owned_controller_context(
                campaign_id=str(authority.campaign_id),
                expected_campaign_fingerprint=FINGERPRINT,
                db=db,
                identity=identity,
                runtime_start_payload=start_payload,
                timeout_seconds=2,
                proof_locks=locks,
            )
        )
        assert context.nonproduction_mechanical_only is False
        result = dual_live_runtime_module._run_production_owned_two_phase_controller(
            context
        )
        assert context.sealed is True
    finally:
        locks.close()

    assert result.seal.connector_run_ids == tuple(
        sorted(authority.run_ids[key] for key in connector_keys)
    )
    assert events.index("quiesce-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("create-B")
    assert events.index("quiesce-B") < events.index("close-B")
    assert context._owned_processes == []
    final_stable = max(
        index
        for index, event in enumerate(events)
        if event == "source-stable"
    )
    assert events.index("close-B") < events.index("seal")
    assert events.index("seal") < final_stable
    assert final_stable < events.index("source-close")
    verified = verify_connector_campaign_log_capture_read_only(
        db,
        chain,
        str(authority.campaign_id),
        FINGERPRINT,
    )
    app_path = next(
        path for path in verified.stream_bytes if path.endswith("/app.jsonl")
    )
    records = read_runtime_records(verified.stream_bytes[app_path])
    assert [record["event"] for record in records] == [
        "runtime_start",
        "phase_child_start",
        "logger_census",
        "phase_go",
        "logger_census",
        "socket_census",
        "job_zero",
        "authority_cleared",
        "phase_complete",
        "phase_child_start",
        "logger_census",
        "phase_go",
        "logger_census",
        "socket_census",
        "job_zero",
        "phase_complete",
        "runtime_complete",
    ]
    assert verified.seal_event_ids == result.event_ids

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
        dependency_set_sha256=DEPENDENCY_SET_SHA256,
        root_mutex_identity_sha256="4" * 64,
        campaign_mutex_identity_sha256="5" * 64,
    )
    _insert_terminal_runs(
        db,
        authority,
        connector_keys=connector_keys,
    )
    run_rows_before = _connector_run_rows(db)
    events: list[str] = []
    seal_calls = 0

    def create(
        phase: str,
    ) -> dual_live_runtime_module._ControllerChild:
        events.append(f"create-{phase}")
        return _capture_controller_child(phase, events)

    def quiesce(
        phase: str,
        _child: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        events.append(f"quiesce-{phase}")
        zero_states = {state: 0 for state in WINDOWS_MIB_TCP_STATES}
        return (
            {
                "tcp4_state_counts": zero_states,
                "tcp6_state_counts": dict(zero_states),
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "7" * 64,
                "stable": True,
            },
            {"active_process_count": 0, "process_list_sha256": "8" * 64},
        )

    def clear_authority(phase: str, _child: object) -> dict[str, object]:
        events.append(f"authority-{phase}")
        return {
            "authority_posture_sha256": "9" * 64,
            "all_required_absent": True,
        }

    def strict_seal() -> object:
        nonlocal seal_calls
        seal_calls += 1
        events.append("seal")
        return seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )

    result = dual_live_runtime_module._run_two_phase_controller(
        identity=identity,
        runtime_start_payload={
            "code_revision": CODE_REVISION,
            "wrapper_image_sha256": identity.wrapper_image_sha256,
            "interpreter_image_sha256": identity.interpreter_image_sha256,
            "dependency_set_sha256": identity.dependency_set_sha256,
            "phase_timeout_contract": _phase_timeout_contract(),
            "mutex_identity_sha256": "6" * 64,
        },
        writers={writer.stream_class: writer for writer in capture.writers},
        create_phase_a=lambda: create("A"),
        create_phase_b=lambda: create("B"),
        quiesce_phase=quiesce,
        clear_authority=clear_authority,
        http_frame_validator=lambda _payload: None,
        seal=strict_seal,
        timeout_seconds=2,
    )
    assert seal_calls == 1
    assert events.index("quiesce-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("create-B")
    assert "authority-B" not in events
    assert events[-1] == "seal"
    assert all(writer.closed for writer in capture.writers)

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
    app_bytes = app_path.read_bytes()
    runtime_records = read_runtime_records(app_bytes)
    assert [record["event"] for record in runtime_records] == [
        "runtime_start",
        "phase_child_start",
        "logger_census",
        "phase_go",
        "logger_census",
        "socket_census",
        "job_zero",
        "authority_cleared",
        "phase_complete",
        "phase_child_start",
        "logger_census",
        "phase_go",
        "logger_census",
        "socket_census",
        "job_zero",
        "phase_complete",
        "runtime_complete",
    ]
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

    campaign_entry_names = tuple(
        sorted(path.name for path in manifest_path.parent.iterdir())
    )
    campaign_file_bytes = {
        path.name: path.read_bytes()
        for path in manifest_path.parent.iterdir()
        if path.is_file()
    }
    assert campaign_entry_names == (
        "app.jsonl",
        "http.jsonl",
        "manifest.json",
        "stderr.log",
        "stdout.log",
    )
    seal_bytes = seal_path.read_bytes()
    with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
        begin_connector_campaign_log_capture(
            campaign_id=authority.campaign_id,
            expected_campaign_fingerprint=FINGERPRINT,
            expected_code_revision=CODE_REVISION,
            now=START,
        )
    assert excinfo.value.code == "connector_campaign_log_path_conflict"
    assert {
        path.name: path.read_bytes()
        for path in manifest_path.parent.iterdir()
        if path.is_file()
    } == campaign_file_bytes
    assert tuple(
        sorted(path.name for path in manifest_path.parent.iterdir())
    ) == campaign_entry_names
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
        (
            "expected_campaign_mismatch",
            "connector_campaign_log_run_envelope_mismatch",
        ),
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
    elif case == "expected_campaign_mismatch":
        assert run is not None
        envelope = {
            **run.request_config_json["connector_egress_arming"],
            "campaign_id": "123e4567-e89b-42d3-a456-426614174099",
            "campaign_fingerprint": "9" * 64,
        }
        envelope["arming_fingerprint"] = compute_arming_fingerprint(envelope)
        run.request_config_json = {"connector_egress_arming": envelope}
        run.request_fingerprint = envelope["arming_fingerprint"]
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


@pytest.mark.parametrize(
    "connector_keys",
    (
        ("nrc_adams_aps",),
        ("nrc_adams_aps", "sciencebase_mcs"),
    ),
    ids=("nrc-only", "two-run"),
)
def test_seal_preflight_run_query_is_bounded_and_campaign_scoped(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    connector_keys: tuple[str, ...],
) -> None:
    authority = _authority_fixture(tmp_path)
    _install_authority(monkeypatch, authority)
    capture = _begin_and_close(authority)
    _insert_terminal_runs(db, authority, connector_keys=connector_keys)
    db.add_all(
        [
            _foreign_strict_run(
                authority,
                f"unrelated-strict-{ordinal:03}",
                same_campaign=False,
            )
            for ordinal in range(64)
        ]
    )
    db.commit()
    statements: list[tuple[str, tuple[Any, ...]]] = []

    def capture_preflight_query(
        _connection: Any,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        normalized = " ".join(statement.lower().split())
        if (
            " from connector_run " in normalized
            and "connector_run.request_config_json" in normalized
        ):
            statements.append((normalized, tuple(parameters)))

    bind = db.get_bind()
    sqlalchemy_event.listen(bind, "before_cursor_execute", capture_preflight_query)
    try:
        result = seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=START + timedelta(seconds=10),
            now=START + timedelta(seconds=11),
        )
    finally:
        sqlalchemy_event.remove(
            bind,
            "before_cursor_execute",
            capture_preflight_query,
        )

    assert result.seal.connector_run_ids == tuple(
        sorted(authority.run_ids[key] for key in connector_keys)
    )
    assert len(statements) == 2
    expected_ids = set(authority.run_ids.values())
    for statement, parameters in statements:
        assert "connector_run.connector_run_id in" in statement
        assert "connector_run.source_mode =" in statement
        assert "connector_run.request_config_json" in statement
        assert " or " in statement
        assert " limit " in statement
        assert expected_ids.issubset(set(parameters))
        assert "strict_live_egress" in parameters
        assert str(authority.campaign_id) in parameters
        assert FINGERPRINT in parameters
        assert len(expected_ids) + 1 in parameters
        assert not any(
            str(value).startswith("unrelated-strict-")
            for value in parameters
        )


def test_seal_preflight_run_query_rejects_same_campaign_at_max_plus_one(
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
    db.add_all(
        [
            _foreign_strict_run(
                authority,
                f"rogue-same-campaign-{ordinal}",
                same_campaign=True,
            )
            for ordinal in range(2)
        ]
    )
    db.commit()
    statements: list[tuple[str, tuple[Any, ...]]] = []

    def capture_preflight_query(
        _connection: Any,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        normalized = " ".join(statement.lower().split())
        if (
            " from connector_run " in normalized
            and "connector_run.request_config_json" in normalized
        ):
            statements.append((normalized, tuple(parameters)))

    bind = db.get_bind()
    sqlalchemy_event.listen(bind, "before_cursor_execute", capture_preflight_query)
    try:
        with pytest.raises(ConnectorCampaignLogCaptureError) as excinfo:
            seal_connector_campaign_log_capture(
                db,
                capture=capture,
                runtime_stopped_at=START + timedelta(seconds=10),
                now=START + timedelta(seconds=11),
            )
    finally:
        sqlalchemy_event.remove(
            bind,
            "before_cursor_execute",
            capture_preflight_query,
        )

    assert excinfo.value.code == "connector_campaign_log_run_cardinality_invalid"
    assert len(statements) == 1
    statement, parameters = statements[0]
    assert " limit " in statement
    assert len(authority.run_ids) + 1 in parameters
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
