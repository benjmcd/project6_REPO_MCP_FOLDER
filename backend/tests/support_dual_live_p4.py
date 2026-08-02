from __future__ import annotations

# Isolated child mode must add the backend and test roots before app/test imports.
# ruff: noqa: E402

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Any
from uuid import uuid4

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
_TEST_ROOT = Path(__file__).resolve().parent
if str(_TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(_TEST_ROOT))

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, settings
from app.db.session import Base
from app.models.models import (
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
    DatasetSourceProvenance,
    DatasetVersion,
    L3_ANALYSIS_PLAN_STATUS_APPROVED,
    L3AnalysisPlan,
    L3ConnectorSourceIntakeRecord,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3Session,
    L3TypingRecord,
)
from app.services import (
    connector_egress_arming,
    connector_egress_transport,
    dual_live_runtime,
    layer3_connector_source_intake,
    layer3_origin_continuity,
    layer3_workbench,
    nrc_aps_artifact_ingestion,
    nrc_aps_phase_b_linkage,
    nrc_phase_b_custody,
)
from app.services.layer3_execution_review import (
    execution_result_review_from_pass_run,
)
from app.services.layer3_execution_state import (
    analysis_execution_start_from_pass_run,
)
from app.services.connector_egress_authorization import canonical_json_bytes
from app.services.layer3_workbench_package_state import (
    handoff_export_prepare_from_reconciliation,
    package_review_submit_from_reconciliation,
)
from app.services.raw_storage_handles import persist_locked_raw_file

import test_dual_eval_acceptance as acceptance


@dataclass(frozen=True, slots=True)
class PhaseBCommitBoundary:
    ordinal: int
    connector_key: str
    name: str


@dataclass(frozen=True, slots=True)
class PhaseAFixture:
    root: Path
    campaign_id: str
    campaign_fingerprint: str
    code_revision: str
    definition_sha256: str
    index_sha256: str
    grant_sha256s: dict[str, str]


@dataclass(frozen=True, slots=True)
class KilledCampaignRecoveryInput:
    cell_root: Path
    campaign_id: str
    campaign_fingerprint: str
    database_path: Path
    storage_root: Path
    evidence_root: Path


@dataclass(frozen=True, slots=True)
class FaultCellResult:
    signal: str
    process_was_alive_at_kill: bool
    returncode: int
    durable_prefix: tuple[str, ...]
    phase_a_before: dict[str, object]
    phase_a_after: dict[str, object]
    evaluator_status: str
    recovery_input: KilledCampaignRecoveryInput


_WORKBENCH_COMMIT_NAMES = (
    "gate_b_decision",
    "gate_c_typing",
    "plan_approval",
    "execution_selection",
    "analysis_execution_start",
    "execution_result_review",
    "package_construction_commit",
    "package_review_submit",
    "handoff_export_prepare",
)
_WORKBENCH_FUNCTION_BY_COMMIT = {
    **{name: name for name in _WORKBENCH_COMMIT_NAMES},
    "gate_c_typing": "gate_c_preview",
}


def _boundaries() -> tuple[PhaseBCommitBoundary, ...]:
    # Runtime mints both origins before either workbench chain. Connector
    # counts are NRC=12 and ScienceBase=10, but their durable order interleaves.
    names = (
        ("nrc_adams_aps", "nrc", "linkage_persisted"),
        ("nrc_adams_aps", "nrc", "custody_finalized"),
        ("nrc_adams_aps", "nrc", "origin_receipt"),
        ("sciencebase_mcs", "sciencebase", "origin_receipt"),
        *(
            ("nrc_adams_aps", "nrc", name)
            for name in _WORKBENCH_COMMIT_NAMES
        ),
        *(
            ("sciencebase_mcs", "sciencebase", name)
            for name in _WORKBENCH_COMMIT_NAMES
        ),
    )
    return tuple(
        PhaseBCommitBoundary(ordinal, connector_key, f"{prefix}_{name}")
        for ordinal, (connector_key, prefix, name) in enumerate(names, start=1)
    )


PHASE_B_COMMIT_BOUNDARIES = _boundaries()
_P4_POPEN = subprocess.Popen
_ACQUISITION_TABLES = (
    "connector_artifact_alias",
    "connector_policy_snapshot",
    "connector_run",
    "connector_run_checkpoint",
    "connector_run_event",
    "connector_run_partition_cursor",
    "connector_run_submission",
    "connector_run_target",
    "connector_target_stage_attempt",
    "dataset",
    "dataset_external_identity",
    "dataset_row",
    "dataset_source_provenance",
    "dataset_version",
    "l3_connector_source_intake_record",
)
_CHILD_ENVIRONMENT_ALLOWLIST = frozenset(
    (
        "APPDATA",
        "COMSPEC",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    )
)


def phase_b_child_environment(
    source: dict[str, str] | None = None,
) -> dict[str, str]:
    inherited = os.environ if source is None else source
    child = {
        name.upper(): value
        for name, value in inherited.items()
        if name.upper() in _CHILD_ENVIRONMENT_ALLOWLIST
    }
    child.update(
        {
            "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
            "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
            "TRUSTED_PROXY_MODE": "false",
        }
    )
    return child


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_value(value: object) -> object:
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    )


def build_phase_a_fixture(root: Path) -> PhaseAFixture:
    root.mkdir(parents=True, exist_ok=True)
    assert not any(root.iterdir())
    storage = root / "storage"
    storage.mkdir()
    db_path = root / "campaign.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    db = factory()
    monkeypatch = pytest.MonkeyPatch()
    started_at = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=2)
    authority = acceptance._build_authority(
        root,
        monkeypatch,
        db_path=db_path,
        storage=storage,
        started_at=started_at,
    )
    grants = acceptance._resolve_current_grants(authority, now=started_at)
    capture = acceptance.begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=authority.campaign_fingerprint,
        expected_code_revision=acceptance.CODE_REVISION,
        now=started_at,
    )
    counter_writer = next(
        writer for writer in capture.writers if writer.stream_class == "http"
    )
    monkeypatch.setattr(connector_egress_transport, "SESSION_FACTORY", factory)
    raw_root = Path(settings.connector_raw_dir)
    raw_root.mkdir(parents=True, exist_ok=True)
    runtime_instance_id = str(uuid4())
    counters: list[dict[str, Any]] = []
    try:
        nrc_run, nrc_lease = acceptance._create_and_lease_run(
            db,
            grant=grants["nrc_adams_aps"],
            now=started_at,
        )
        nrc_detail = b"{}"
        counters.append(
            acceptance._complete_request(
                run=nrc_run,
                lease_token=nrc_lease,
                ordinal=1,
                stage="exact_accession_api",
                request=connector_egress_transport.FrozenPhysicalRequest(
                    method="GET",
                    url=acceptance.NRC_DETAIL_URL,
                    headers={
                        "Accept-Encoding": "identity",
                        "Ocp-Apim-Subscription-Key": "offline-fixture-only",
                    },
                    credential_audience="nrc_aps_api_key",
                ),
                body=nrc_detail,
                now=datetime.now(UTC),
                prior_records=counters,
                runtime_instance_id=runtime_instance_id,
                monotonic_started_at=1.0,
            )
        )
        nrc_derived = connector_egress_arming.commit_derived_url_arming(
            db,
            run=nrc_run,
            lease_token=nrc_lease,
            ordinal=2,
            stage="artifact",
            normalized_url=acceptance.NRC_ARTIFACT_URL,
            verified_grant=grants["nrc_adams_aps"],
        )
        counters.append(
            acceptance._complete_request(
                run=nrc_run,
                lease_token=nrc_lease,
                ordinal=2,
                stage="artifact",
                request=connector_egress_transport.FrozenPhysicalRequest(
                    method="GET",
                    url=acceptance.NRC_ARTIFACT_URL,
                    headers={"Accept-Encoding": "identity"},
                    credential_audience="none",
                ),
                body=acceptance.NRC_BYTES,
                now=datetime.now(UTC),
                prior_records=counters,
                runtime_instance_id=runtime_instance_id,
                monotonic_started_at=2.0,
                expected_derived_arming_hash=nrc_derived.url_sha256,
            )
        )
        nrc_digest = _sha256(acceptance.NRC_BYTES)
        nrc_raw_path = raw_root / nrc_aps_artifact_ingestion.blob_relative_path(
            sha256=nrc_digest
        )
        persist_locked_raw_file(raw_root, nrc_raw_path, acceptance.NRC_BYTES)
        nrc_completed_at = datetime.now(UTC)
        acceptance._nrc_target(
            db,
            run=nrc_run,
            raw_path=nrc_raw_path,
            detail_hash=_sha256(nrc_detail),
            completed_at=nrc_completed_at,
        )
        connector_egress_arming.finalize_strict_run(
            db,
            run=nrc_run,
            lease_token=nrc_lease,
            terminal_status="completed",
            outcome_class="nrc_raw_admission_completed",
            now=nrc_completed_at,
        )
        acceptance._write_counters(counter_writer, counters)

        sciencebase_run, sciencebase_lease = acceptance._create_and_lease_run(
            db,
            grant=grants["sciencebase_mcs"],
            now=started_at + timedelta(seconds=4),
        )
        metadata = b'{"title":"MCS offline fixture"}'
        counters.append(
            acceptance._complete_request(
                run=sciencebase_run,
                lease_token=sciencebase_lease,
                ordinal=1,
                stage="item_hydration",
                request=connector_egress_transport.FrozenPhysicalRequest(
                    method="GET",
                    url=acceptance.SCIENCEBASE_DETAIL_URL,
                    headers={"Accept-Encoding": "identity"},
                    credential_audience="none",
                ),
                body=metadata,
                now=datetime.now(UTC),
                prior_records=counters,
                runtime_instance_id=runtime_instance_id,
                monotonic_started_at=3.0,
            )
        )
        acceptance._write_counters(counter_writer, counters[-1:])
        sciencebase_derived = connector_egress_arming.commit_derived_url_arming(
            db,
            run=sciencebase_run,
            lease_token=sciencebase_lease,
            ordinal=2,
            stage="artifact",
            normalized_url=acceptance.SCIENCEBASE_ARTIFACT_URL,
            verified_grant=grants["sciencebase_mcs"],
        )
        counters.append(
            acceptance._complete_request(
                run=sciencebase_run,
                lease_token=sciencebase_lease,
                ordinal=2,
                stage="artifact",
                request=connector_egress_transport.FrozenPhysicalRequest(
                    method="GET",
                    url=acceptance.SCIENCEBASE_ARTIFACT_URL,
                    headers={"Accept-Encoding": "identity"},
                    credential_audience="none",
                ),
                body=acceptance.SCIENCEBASE_BYTES,
                now=datetime.now(UTC),
                prior_records=counters,
                runtime_instance_id=runtime_instance_id,
                monotonic_started_at=4.0,
                expected_derived_arming_hash=sciencebase_derived.url_sha256,
            )
        )
        sciencebase_digest = _sha256(acceptance.SCIENCEBASE_BYTES)
        sciencebase_raw_path = raw_root / "sha256" / f"{sciencebase_digest}.csv"
        persist_locked_raw_file(
            raw_root,
            sciencebase_raw_path,
            acceptance.SCIENCEBASE_BYTES,
        )
        sciencebase_completed_at = datetime.now(UTC)
        acceptance._sciencebase_target(
            db,
            run=sciencebase_run,
            raw_path=sciencebase_raw_path,
            completed_at=sciencebase_completed_at,
        )
        connector_egress_arming.finalize_strict_run(
            db,
            run=sciencebase_run,
            lease_token=sciencebase_lease,
            terminal_status="completed",
            outcome_class="sciencebase_raw_admitted",
            now=sciencebase_completed_at,
        )
        acceptance._write_counters(counter_writer, counters[-1:])
        # The Phase-B entry contract requires no retained lease coordinate.
        # Normalize the already-terminal offline fixture to that post-quiescence
        # state; this is fixture setup, not a production retry or failpoint.
        nrc_run.execution_lease_expires_at = None
        sciencebase_run.execution_lease_expires_at = None
        db.commit()
        db.rollback()
    finally:
        for writer in capture.writers:
            writer.close()
        db.close()
        engine.dispose()
        monkeypatch.undo()

    fixture = PhaseAFixture(
        root=root,
        campaign_id=str(authority.campaign_id),
        campaign_fingerprint=authority.campaign_fingerprint,
        code_revision=acceptance.CODE_REVISION,
        definition_sha256=authority.definition_sha256,
        index_sha256=authority.index_sha256,
        grant_sha256s=dict(authority.grant_sha256s),
    )
    (root / "p4-fixture.json").write_bytes(
        canonical_json_bytes(
            {
                "campaign_id": fixture.campaign_id,
                "campaign_fingerprint": fixture.campaign_fingerprint,
                "code_revision": fixture.code_revision,
                "definition_sha256": fixture.definition_sha256,
                "index_sha256": fixture.index_sha256,
                "grant_sha256s": fixture.grant_sha256s,
            }
        )
    )
    return fixture


def _acquisition_table_snapshot(db: Session, table_name: str) -> list[dict[str, object]]:
    table = Base.metadata.tables[table_name]
    rows = []
    ignored_source_keys = {
        layer3_origin_continuity.ORIGIN_RECEIPT_STORAGE_KEY,
        nrc_phase_b_custody.CUSTODY_STORAGE_KEY,
    }
    for row in db.execute(select(table)).mappings():
        item = {str(key): _json_value(value) for key, value in row.items()}
        if table_name == "connector_run_target":
            source_reference = dict(item.get("source_reference_json") or {})
            for key in ignored_source_keys:
                source_reference.pop(key, None)
            item["source_reference_json"] = _json_value(source_reference)
        elif table_name == "dataset_source_provenance":
            source_reference = dict(item.get("source_reference_json") or {})
            source_reference.pop("connector_origin_receipt_hash", None)
            item["source_reference_json"] = _json_value(source_reference)
        elif table_name == "l3_connector_source_intake_record":
            # Origin minting deliberately continuity-enriches the Phase-A intake
            # record. Compare its acquisition identity/bytes/storage plus every
            # non-derived field, excluding only the receipt-derived projection.
            item.pop("metadata_hash", None)
            item.pop("authority_basis_hash", None)
            provenance = dict(item.get("provenance_json") or {})
            provenance.pop("connector_origin_receipt_hash", None)
            provenance.pop("metadata_hash", None)
            item["provenance_json"] = _json_value(provenance)
            summary = dict(item.get("summary_json") or {})
            authority_basis = dict(summary.get("authority_basis") or {})
            for key in (
                "connector_origin_receipt_hash",
                "connector_run_target_id",
                "metadata_hash",
            ):
                authority_basis.pop(key, None)
            metadata = dict(summary.get("metadata") or {})
            metadata.pop("connector_origin_receipt_hash", None)
            summary["authority_basis"] = authority_basis
            summary["metadata"] = metadata
            item["summary_json"] = _json_value(summary)
        rows.append(item)
    return sorted(
        rows,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )


def _authority_file_snapshot(root: Path) -> list[dict[str, object]]:
    evidence_root = root / "evidence"
    return [
        {
            "path": path.relative_to(evidence_root).as_posix(),
            "sha256": _sha256(payload),
            "size": len(payload),
        }
        for path in sorted(item for item in evidence_root.rglob("*") if item.is_file())
        for payload in (path.read_bytes(),)
    ]


def snapshot_phase_a(root: Path, fixture: PhaseAFixture) -> dict[str, object]:
    engine = create_engine(
        f"sqlite:///{(root / 'campaign.db').as_posix()}",
        future=True,
    )
    with Session(engine, expire_on_commit=False) as db:
        runs = sorted(db.scalars(select(ConnectorRun)).all(), key=lambda item: item.connector_key)
        targets = sorted(
            db.scalars(select(ConnectorRunTarget)).all(),
            key=lambda item: item.connector_run_id,
        )
        connector_by_run = {
            item.connector_run_id: item.connector_key for item in runs
        }
        target_identities = []
        raw_artifacts = []
        ignored_source_keys = {
            layer3_origin_continuity.ORIGIN_RECEIPT_STORAGE_KEY,
            nrc_phase_b_custody.CUSTODY_STORAGE_KEY,
        }
        for target in targets:
            source_reference = dict(target.source_reference_json or {})
            for key in ignored_source_keys:
                source_reference.pop(key, None)
            target_identities.append(
                {
                    column.name: _json_value(getattr(target, column.name))
                    for column in ConnectorRunTarget.__table__.columns
                    if column.name != "source_reference_json"
                }
                | {"source_reference_json": _json_value(source_reference)}
            )
            raw_path = Path(str(target.raw_storage_ref))
            raw_bytes = raw_path.read_bytes()
            raw_artifacts.append(
                {
                    "connector_key": connector_by_run[target.connector_run_id],
                    "sha256": _sha256(raw_bytes),
                    "size": len(raw_bytes),
                }
            )
        events = [
            {
                column.name: _json_value(getattr(event, column.name))
                for column in ConnectorRunEvent.__table__.columns
            }
            for event in db.scalars(select(ConnectorRunEvent)).all()
        ]
        snapshot = {
            "campaign_id": fixture.campaign_id,
            "connector_keys": [item.connector_key for item in runs],
            "run_statuses": [item.status for item in runs],
            "runs": [
                {
                    column.name: _json_value(getattr(run, column.name))
                    for column in ConnectorRun.__table__.columns
                }
                for run in runs
            ],
            "events": sorted(events, key=lambda item: str(item["connector_run_event_id"])),
            "target_identities": target_identities,
            "raw_artifacts": sorted(raw_artifacts, key=lambda item: str(item["connector_key"])),
            "acquisition_tables": {
                table_name: _acquisition_table_snapshot(db, table_name)
                for table_name in _ACQUISITION_TABLES
            },
            "authority_files": _authority_file_snapshot(root),
            "phase_b_row_counts": {
                "aps_content_linkage": len(
                    db.scalars(select(ApsContentLinkage)).all()
                ),
                "l3_session": len(db.scalars(select(L3Session)).all()),
            },
        }
    engine.dispose()
    return snapshot


def _fixture_from_root(root: Path) -> PhaseAFixture:
    payload = json.loads((root / "p4-fixture.json").read_bytes())
    return PhaseAFixture(
        root=root,
        campaign_id=str(payload["campaign_id"]),
        campaign_fingerprint=str(payload["campaign_fingerprint"]),
        code_revision=str(payload["code_revision"]),
        definition_sha256=str(payload["definition_sha256"]),
        index_sha256=str(payload["index_sha256"]),
        grant_sha256s={
            str(key): str(value)
            for key, value in dict(payload["grant_sha256s"]).items()
        },
    )


def clone_phase_a_fixture(
    fixture: PhaseAFixture,
    cell_root: Path,
) -> PhaseAFixture:
    shutil.copytree(fixture.root, cell_root)
    cloned = _fixture_from_root(cell_root)
    old_root = str(fixture.root.resolve())
    new_root = str(cell_root.resolve())
    engine = create_engine(
        f"sqlite:///{(cell_root / 'campaign.db').as_posix()}",
        future=True,
    )
    with Session(engine, expire_on_commit=False) as db:
        for target in db.scalars(select(ConnectorRunTarget)).all():
            target.raw_storage_ref = str(target.raw_storage_ref).replace(
                old_root,
                new_root,
                1,
            )
        for version in db.scalars(select(DatasetVersion)).all():
            version.storage_ref = str(version.storage_ref).replace(
                old_root,
                new_root,
                1,
            )
        for provenance in db.scalars(select(DatasetSourceProvenance)).all():
            provenance.raw_storage_ref = str(provenance.raw_storage_ref).replace(
                old_root,
                new_root,
                1,
            )
        for intake in db.scalars(select(L3ConnectorSourceIntakeRecord)).all():
            intake.storage_ref = str(intake.storage_ref).replace(
                old_root,
                new_root,
                1,
            )
        db.commit()
    engine.dispose()
    return cloned


def _authority_paths(root: Path, fixture: PhaseAFixture) -> dict[str, object]:
    evidence = root / "evidence"
    grants = evidence / "grants"
    return {
        "database_url": f"sqlite:///{(root / 'campaign.db').as_posix()}",
        "storage_dir": str(root / "storage"),
        "connector_campaign_definition_path": (
            evidence / "campaigns" / f"{fixture.definition_sha256}.json"
        ),
        "connector_campaign_definition_sha256": fixture.definition_sha256,
        "connector_sciencebase_grant_path": (
            grants / f"{fixture.grant_sha256s['sciencebase_mcs']}.json"
        ),
        "connector_sciencebase_grant_sha256": fixture.grant_sha256s[
            "sciencebase_mcs"
        ],
        "connector_nrc_aps_grant_path": (
            grants / f"{fixture.grant_sha256s['nrc_adams_aps']}.json"
        ),
        "connector_nrc_aps_grant_sha256": fixture.grant_sha256s[
            "nrc_adams_aps"
        ],
        "connector_campaign_evidence_root": evidence,
        "connector_campaign_evidence_index_path": (
            evidence / "indexes" / f"{fixture.index_sha256}.json"
        ),
        "connector_campaign_evidence_index_sha256": fixture.index_sha256,
    }


def _configure_phase_b(root: Path, fixture: PhaseAFixture) -> None:
    coordinates = _authority_paths(root, fixture)
    for name in (
        "database_url",
        "storage_dir",
        "connector_campaign_evidence_root",
        "connector_campaign_evidence_index_path",
        "connector_campaign_evidence_index_sha256",
    ):
        setattr(settings, name, coordinates[name])
    settings.connector_live_egress_enabled = False
    settings.connector_live_egress_exclusive_proof_mode = False
    settings.connector_campaign_definition_path = None
    settings.connector_campaign_definition_sha256 = None
    settings.connector_sciencebase_grant_path = None
    settings.connector_sciencebase_grant_sha256 = None
    settings.connector_nrc_aps_grant_path = None
    settings.connector_nrc_aps_grant_sha256 = None
    settings.nrc_adams_subscription_key = None


def _proof_settings(root: Path, fixture: PhaseAFixture) -> Settings:
    coordinates = _authority_paths(root, fixture)
    return Settings(
        DATABASE_URL=coordinates["database_url"],
        STORAGE_DIR=coordinates["storage_dir"],
        CONNECTOR_CAMPAIGN_DEFINITION_PATH=str(
            coordinates["connector_campaign_definition_path"]
        ),
        CONNECTOR_CAMPAIGN_DEFINITION_SHA256=coordinates[
            "connector_campaign_definition_sha256"
        ],
        CONNECTOR_SCIENCEBASE_GRANT_PATH=str(
            coordinates["connector_sciencebase_grant_path"]
        ),
        CONNECTOR_SCIENCEBASE_GRANT_SHA256=coordinates[
            "connector_sciencebase_grant_sha256"
        ],
        CONNECTOR_NRC_APS_GRANT_PATH=str(
            coordinates["connector_nrc_aps_grant_path"]
        ),
        CONNECTOR_NRC_APS_GRANT_SHA256=coordinates[
            "connector_nrc_aps_grant_sha256"
        ],
        CONNECTOR_CAMPAIGN_EVIDENCE_ROOT=str(
            coordinates["connector_campaign_evidence_root"]
        ),
        CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH=str(
            coordinates["connector_campaign_evidence_index_path"]
        ),
        CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256=coordinates[
            "connector_campaign_evidence_index_sha256"
        ],
        CONNECTOR_LIVE_EGRESS_ENABLED=False,
        CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE=False,
    )


def _install_fault_wrappers(
    db: Session,
    *,
    target_name: str,
    signal_path: Path,
) -> None:
    def trip(name: str) -> None:
        if name != target_name:
            return
        descriptor = os.open(
            signal_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(descriptor, name.encode("ascii"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        threading.Event().wait()

    original_detach_commit = nrc_aps_phase_b_linkage._detach_then_commit

    def detach_commit(*args: object, **kwargs: object) -> object:
        result = original_detach_commit(*args, **kwargs)
        trip("nrc_linkage_persisted")
        return result

    nrc_aps_phase_b_linkage._detach_then_commit = detach_commit
    original_finalize = nrc_aps_phase_b_linkage._finalize_pending_custody

    def finalize(*args: object, **kwargs: object) -> object:
        result = original_finalize(*args, **kwargs)
        trip("nrc_custody_finalized")
        return result

    nrc_aps_phase_b_linkage._finalize_pending_custody = finalize

    pending_origin: list[str] = []
    original_origin = layer3_origin_continuity.mint_connector_origin_receipt

    def mint_origin(*args: object, **kwargs: object) -> object:
        target_id = str(kwargs["connector_run_target_id"])
        target = db.get(ConnectorRunTarget, target_id)
        assert target is not None
        run = db.get(ConnectorRun, target.connector_run_id)
        assert run is not None
        prefix = "nrc" if run.connector_key == "nrc_adams_aps" else "sciencebase"
        result = original_origin(*args, **kwargs)
        pending_origin.append(f"{prefix}_origin_receipt")
        return result

    layer3_origin_continuity.mint_connector_origin_receipt = mint_origin

    def after_transaction_end(_session: Session, transaction: object) -> None:
        if pending_origin and getattr(transaction, "parent", None) is None:
            trip(pending_origin.pop(0))

    event.listen(db, "after_transaction_end", after_transaction_end)

    for boundary_name, function_name in _WORKBENCH_FUNCTION_BY_COMMIT.items():
        original = getattr(layer3_workbench, function_name)

        def wrapped(
            *args: object,
            _original: object = original,
            _name: str = boundary_name,
            **kwargs: object,
        ) -> object:
            result = _original(*args, **kwargs)  # type: ignore[operator]
            payload = args[-1]
            assert isinstance(payload, dict)
            request_id = str(payload.get("client_request_id", ""))
            prefix = "sciencebase" if "-sciencebase-" in request_id else "nrc"
            trip(f"{prefix}_{_name}")
            return result

        setattr(layer3_workbench, function_name, wrapped)


def _fault_child(root: Path, target_name: str, signal_path: Path) -> None:
    fixture = _fixture_from_root(root)
    _configure_phase_b(root, fixture)
    dual_live_runtime._install_phase_b_connector_guards()
    dual_live_runtime.exercise_owned_phase_b_connector_guard()
    dual_live_runtime._assert_phase_b_connector_guards()
    engine = create_engine(
        f"sqlite:///{(root / 'campaign.db').as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        _install_fault_wrappers(
            db,
            target_name=target_name,
            signal_path=signal_path,
        )
        dual_live_runtime._prepare_owned_phase_b(
            db,
            campaign_id=fixture.campaign_id,
            campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=fixture.code_revision,
        )
    engine.dispose()
    raise RuntimeError("fault boundary was not reached")


def _acquisition_projection(snapshot: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in snapshot.items()
        if key != "phase_b_row_counts"
    }


def _classify_durable_prefix(root: Path) -> tuple[str, ...]:
    engine = create_engine(
        f"sqlite:///{(root / 'campaign.db').as_posix()}",
        future=True,
    )
    with Session(engine, expire_on_commit=False) as db:
        runs = db.scalars(select(ConnectorRun)).all()
        run_by_id = {run.connector_run_id: run for run in runs}
        targets = db.scalars(select(ConnectorRunTarget)).all()
        target_by_connector = {
            run_by_id[target.connector_run_id].connector_key: target
            for target in targets
        }
        assert set(target_by_connector) == {"nrc_adams_aps", "sciencebase_mcs"}

        state = {item.name: False for item in PHASE_B_COMMIT_BOUNDARIES}
        nrc_target = target_by_connector["nrc_adams_aps"]
        linkages = db.scalars(select(ApsContentLinkage)).all()
        assert len(linkages) <= 1
        custody = dict(nrc_target.source_reference_json or {}).get(
            nrc_phase_b_custody.CUSTODY_STORAGE_KEY
        )
        if linkages:
            assert len(linkages) == 1
            linkage = linkages[0]
            assert linkage.target_id == nrc_target.connector_run_target_id
            assert isinstance(custody, dict)
            assert custody.get("status") in {
                nrc_phase_b_custody.PENDING_SNAPSHOT_EXIT,
                nrc_phase_b_custody.VERIFIED,
            }
            state["nrc_linkage_persisted"] = True
            state["nrc_custody_finalized"] = (
                custody["status"] == nrc_phase_b_custody.VERIFIED
            )
        else:
            assert custody is None

        source_shape_by_connector = {
            "nrc_adams_aps": "aps_content_document",
            "sciencebase_mcs": (
                layer3_connector_source_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
            ),
        }
        snapshots = db.scalars(select(L3MaterialSnapshot)).all()
        session_ids_by_connector: dict[str, set[str]] = {
            connector_key: set() for connector_key in source_shape_by_connector
        }
        for snapshot in snapshots:
            matches = [
                connector_key
                for connector_key, source_shape in source_shape_by_connector.items()
                if snapshot.source_shape == source_shape
            ]
            assert len(matches) == 1
            session_ids_by_connector[matches[0]].add(snapshot.session_id)
        assert all(len(session_ids) <= 1 for session_ids in session_ids_by_connector.values())

        sessions = db.scalars(select(L3Session)).all()
        mapped_session_ids = {
            session_id
            for session_ids in session_ids_by_connector.values()
            for session_id in session_ids
        }
        assert {session.session_id for session in sessions} == mapped_session_ids
        typing_records = db.scalars(select(L3TypingRecord)).all()
        plans = db.scalars(select(L3AnalysisPlan)).all()
        pass_runs = db.scalars(select(L3PassRun)).all()
        reconciliations = db.scalars(select(L3ReconciliationRecord)).all()
        packages = db.scalars(select(L3OutputPackage)).all()
        for rows in (typing_records, plans, pass_runs, reconciliations, packages):
            assert {row.session_id for row in rows}.issubset(mapped_session_ids)

        for connector_key, prefix in (
            ("nrc_adams_aps", "nrc"),
            ("sciencebase_mcs", "sciencebase"),
        ):
            target = target_by_connector[connector_key]
            origin = layer3_origin_continuity._stored_origin_receipt(target)
            state[f"{prefix}_origin_receipt"] = origin is not None

            session_ids = session_ids_by_connector[connector_key]
            session_id = next(iter(session_ids), None)
            state[f"{prefix}_gate_b_decision"] = session_id is not None
            if session_id is None:
                continue

            session_typing = [
                item for item in typing_records if item.session_id == session_id
            ]
            assert len(session_typing) <= 1
            state[f"{prefix}_gate_c_typing"] = len(session_typing) == 1

            session_plans = [item for item in plans if item.session_id == session_id]
            assert len(session_plans) <= 1
            if session_plans:
                plan = session_plans[0]
                assert plan.status == L3_ANALYSIS_PLAN_STATUS_APPROVED
                assert plan.approved_by_operator is True
                state[f"{prefix}_plan_approval"] = True

            session_pass_runs = [
                item for item in pass_runs if item.session_id == session_id
            ]
            assert len(session_pass_runs) <= 1
            if session_pass_runs:
                pass_run = session_pass_runs[0]
                state[f"{prefix}_execution_selection"] = True
                state[f"{prefix}_analysis_execution_start"] = (
                    analysis_execution_start_from_pass_run(pass_run) is not None
                )
                state[f"{prefix}_execution_result_review"] = (
                    execution_result_review_from_pass_run(pass_run) is not None
                )

            session_reconciliations = [
                item for item in reconciliations if item.session_id == session_id
            ]
            assert len(session_reconciliations) <= 1
            session_packages = [
                item for item in packages if item.session_id == session_id
            ]
            assert len(session_packages) in {0, 3}
            assert len(session_reconciliations) == (1 if session_packages else 0)
            if session_reconciliations:
                reconciliation = session_reconciliations[0]
                assert {
                    item.package_kind for item in session_packages
                } == {"canonical_internal", "review_facing", "user_facing"}
                state[f"{prefix}_package_construction_commit"] = True
                state[f"{prefix}_package_review_submit"] = (
                    package_review_submit_from_reconciliation(reconciliation)
                    is not None
                )
                state[f"{prefix}_handoff_export_prepare"] = (
                    handoff_export_prepare_from_reconciliation(reconciliation)
                    is not None
                )

        ordered_state = [state[item.name] for item in PHASE_B_COMMIT_BOUNDARIES]
        first_absent = next(
            (index for index, present in enumerate(ordered_state) if not present),
            len(ordered_state),
        )
        assert not any(ordered_state[first_absent:])
    engine.dispose()
    return tuple(
        item.name
        for item, present in zip(PHASE_B_COMMIT_BOUNDARIES, ordered_state, strict=True)
        if present
    )


def _evaluate_partial(root: Path, fixture: PhaseAFixture) -> str:
    proof_settings = _proof_settings(root, fixture)
    db_path = root / "campaign.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    db = Session(engine, autoflush=False, expire_on_commit=False)
    campaign = acceptance._Campaign(
        db=db,
        engine=engine,
        settings=proof_settings,
        campaign_id=acceptance.UUID(fixture.campaign_id),
        campaign_fingerprint=fixture.campaign_fingerprint,
        code_revision=fixture.code_revision,
        evidence_root=root / "evidence",
        db_path=db_path,
    )
    try:
        report = acceptance._query_only_report(campaign)
        return str(report["status"])
    finally:
        db.close()
        engine.dispose()


def poison_killed_campaign(
    recovery_input: KilledCampaignRecoveryInput,
    *,
    reason_code: str = "phase_b_killed_after_commit",
) -> Path:
    if (
        not reason_code
        or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_"
            for character in reason_code
        )
    ):
        raise ValueError("reason_code must be a lowercase alphanumeric token")
    campaign_dir = (
        recovery_input.evidence_root
        / "logs"
        / recovery_input.campaign_fingerprint
    )
    assert campaign_dir.is_dir()
    assert not (campaign_dir / "manifest.json").exists()
    assert not (
        recovery_input.evidence_root
        / "log-seals"
        / f"{recovery_input.campaign_fingerprint}.json"
    ).exists()
    marker_path = campaign_dir / "poison.json"
    marker_bytes = (
        json.dumps(
            {
                "campaign_fingerprint": recovery_input.campaign_fingerprint,
                "campaign_id": recovery_input.campaign_id,
                "marker_kind": "poison",
                "reason_code": reason_code,
                "schema_id": "project6.dual_live_recovery_marker.v1",
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    with marker_path.open("xb") as stream:
        stream.write(marker_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    assert marker_path.read_bytes() == marker_bytes
    return marker_path


def run_fault_cell(
    fixture: PhaseAFixture,
    *,
    cell_root: Path,
    boundary: PhaseBCommitBoundary,
) -> FaultCellResult:
    cloned = clone_phase_a_fixture(fixture, cell_root)
    before = _acquisition_projection(snapshot_phase_a(cell_root, cloned))
    signal_path = cell_root / "fault.signal"
    process = _P4_POPEN(
        [
            sys.executable,
            "-I",
            "-B",
            str(Path(__file__).resolve()),
            "--child",
            str(cell_root),
            boundary.name,
            str(signal_path),
        ],
        cwd=_BACKEND_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=phase_b_child_environment(),
    )
    deadline = time.monotonic() + 90
    while not signal_path.exists() and process.poll() is None:
        if time.monotonic() >= deadline:
            process.kill()
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"fault child timeout: stdout={stdout!r} stderr={stderr!r}"
            )
        time.sleep(0.01)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise AssertionError(
            f"fault child exited early: rc={process.returncode} "
            f"stdout={stdout!r} stderr={stderr!r}"
        )
    signal = signal_path.read_text(encoding="ascii")
    alive = process.poll() is None
    process.kill()
    process.communicate(timeout=30)
    assert process.returncode is not None
    after = _acquisition_projection(snapshot_phase_a(cell_root, cloned))
    durable_prefix = _classify_durable_prefix(cell_root)
    evaluator_status = _evaluate_partial(cell_root, cloned)
    return FaultCellResult(
        signal=signal,
        process_was_alive_at_kill=alive,
        returncode=process.returncode,
        durable_prefix=durable_prefix,
        phase_a_before=before,
        phase_a_after=after,
        evaluator_status=evaluator_status,
        recovery_input=KilledCampaignRecoveryInput(
            cell_root=cell_root.resolve(),
            campaign_id=cloned.campaign_id,
            campaign_fingerprint=cloned.campaign_fingerprint,
            database_path=(cell_root / "campaign.db").resolve(),
            storage_root=(cell_root / "storage").resolve(),
            evidence_root=(cell_root / "evidence").resolve(),
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--child":
        _fault_child(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
    raise SystemExit(2)
