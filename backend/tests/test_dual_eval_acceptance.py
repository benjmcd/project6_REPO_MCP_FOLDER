from __future__ import annotations

__test__ = False

from collections.abc import Callable, Mapping
import copy
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
import queue
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO, cast
from uuid import UUID, uuid4

import fitz
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import Settings, settings
from app.db.session import Base
from app.models.models import (
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3AnalysisPlan,
    L3ConnectorSourceIntakeRecord,
    L3OutputPackage,
    L3PassRun,
    L3Session,
)
from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    COMMON_GRANT_NON_AUTHORITIES,
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorCampaignEvidenceIndexV1,
    ConnectorCampaignLogCaptureRefV1,
    ConnectorEgressArmingIn,
    ConnectorEgressGrantV1,
    ConnectorGrantConsumptionMarkerV1,
    DualLiveCampaignDefinitionV1,
    NrcApsFreshTargetV1,
    ScienceBaseFreshTargetV1,
    expected_grant_rule_payloads,
)
from app.services import (
    connector_egress_evidence,
    connector_egress_arming,
    connector_egress_transport,
    connectors_nrc_adams,
    connectors_sciencebase,
    dual_live_evaluator,
    dual_live_runtime,
    layer3_connector_source_intake,
    layer3_origin_continuity,
    layer3_workbench,
    nrc_aps_artifact_ingestion,
    nrc_aps_phase_b_linkage,
)
from app.services.connector_campaign_log_capture import (
    begin_connector_campaign_log_capture,
    seal_connector_campaign_log_capture,
)
from app.services.connector_egress_authorization import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    canonical_json_bytes,
    resolve_current_connector_egress_grant,
    resolve_current_dual_live_campaign_definition,
)
from app.services.dual_live_runtime import (
    PIPE_STREAM_CLASSES,
    WINDOWS_MIB_TCP_STATES,
    RuntimeIdentity,
    encode_child_control_frame,
    encode_child_status_frame,
    encode_pipe_frame,
)
from app.services.raw_storage_handles import persist_locked_raw_file


CODE_REVISION = "a" * 40
ITEM_ID = "63d1a3c6d34e06fef15006be"
FILE_NAME = "mcs2023-germa_salient.csv"
ACCESSION = "ML17123A319"
NRC_DETAIL_URL = f"https://adams-api.nrc.gov/aps/api/search/{ACCESSION}"
NRC_ARTIFACT_URL = f"https://www.nrc.gov/docs/ML1712/{ACCESSION}.pdf"
SCIENCEBASE_DETAIL_URL = (
    f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}?format=json"
)
SCIENCEBASE_ARTIFACT_URL = (
    f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}"
)
NRC_BYTES = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "nrc_aps_docs"
    / "v1"
    / "born_digital.pdf"
).read_bytes()
SCIENCEBASE_BYTES = b"county,value\n001,1\n"
COUNTER_BOOT_ID = "b" * 64
# Strict Phase B correctly installs a process-lifetime spawn guard. Preserve the
# pre-construction launcher only for the separate isolated-gate acceptance process.
_ACCEPTANCE_GATE_POPEN = subprocess.Popen


@dataclass
class _Campaign:
    db: Session
    engine: Any
    settings: Settings
    campaign_id: UUID
    campaign_fingerprint: str
    code_revision: str
    evidence_root: Path
    db_path: Path


@dataclass(frozen=True)
class _CampaignTemplate:
    live_root: Path
    backup_root: Path
    settings: Settings
    campaign_id: UUID
    campaign_fingerprint: str
    code_revision: str
    evidence_root: Path
    db_path: Path
    file_snapshot: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True)
class _Authority:
    campaign_id: UUID
    campaign_fingerprint: str
    definition_sha256: str
    grants: Mapping[str, Any]
    grant_sha256s: Mapping[str, str]
    evidence_root: Path
    index_path: Path
    index_sha256: str
    proof_settings: Settings


@dataclass(frozen=True, slots=True)
class _NegativeCase:
    check_id: str
    status: str
    code: str
    seam: str


NEGATIVE_CASES = (
    _NegativeCase("A01_INPUT_IDENTITY", "FAIL", "a01_input_identity_invalid", "input"),
    _NegativeCase(
        "A02_INDEX_LINEAR_HEAD",
        "FAIL",
        "a02_index_linear_head_invalid",
        "authority-model",
    ),
    _NegativeCase(
        "A03_ARCHIVE_EXACT", "FAIL", "a03_archive_binding_invalid", "authority-model"
    ),
    _NegativeCase(
        "A04_SLICE_CARDINALITY",
        "FAIL",
        "a04_slice_cardinality_invalid",
        "authority-model",
    ),
    _NegativeCase(
        "A05_SELECTED_UNION",
        "FAIL",
        "a05_selected_union_partial_slice",
        "authority-model",
    ),
    _NegativeCase(
        "A06_INTRODUCTION_PARITY",
        "FAIL",
        "a06_introduction_binding_invalid",
        "authority-model",
    ),
    _NegativeCase(
        "A07_MARKER_ONE_USE", "FAIL", "a07_marker_binding_invalid", "authority-model"
    ),
    _NegativeCase(
        "A08_ORIGINAL_WINDOWS", "FAIL", "a08_original_window_violation", "ledger-record"
    ),
    _NegativeCase(
        "A09_CODE_CAMPAIGN_FINGERPRINTS",
        "FAIL",
        "a09_cross_domain_fingerprint_invalid",
        "authority-model",
    ),
    _NegativeCase(
        "A10_PROOF_CLASS", "FAIL", "a10_rederived_proof_class_invalid", "origin-record"
    ),
    _NegativeCase(
        "R01_CAPTURE_MEMBERSHIP",
        "FAIL",
        "r01_capture_membership_invalid",
        "capture-record",
    ),
    _NegativeCase(
        "R02_MANIFEST_FILE_HASHES",
        "FAIL",
        "r02_manifest_file_hash_invalid",
        "capture-record",
    ),
    _NegativeCase(
        "R03_SEAL_PARITY", "FAIL", "r03_seal_parity_invalid", "capture-record"
    ),
    _NegativeCase(
        "R04_SEAL_EVENT_PARITY",
        "FAIL",
        "r04_seal_event_parity_invalid",
        "capture-record",
    ),
    _NegativeCase(
        "R05_RUNTIME_CHAIN", "FAIL", "r05_runtime_chain_invalid", "runtime-record"
    ),
    _NegativeCase(
        "R06_STARTUP_LOGGER_CENSUS",
        "FAIL",
        "r06_startup_logger_census_invalid",
        "runtime-record",
    ),
    _NegativeCase(
        "R07_EXIT_LOGGER_CENSUS",
        "FAIL",
        "r07_exit_logger_census_changed",
        "runtime-record",
    ),
    _NegativeCase(
        "R08_PHASE_A_IDENTITY", "FAIL", "r08_phase_a_identity_invalid", "runtime-record"
    ),
    _NegativeCase(
        "R09_PHASE_A_JOB_ZERO", "FAIL", "r09_phase_a_job_not_zero", "runtime-record"
    ),
    _NegativeCase(
        "R10_PHASE_A_SOCKET_QUIESCENCE",
        "FAIL",
        "r10_phase_a_socket_not_quiescent",
        "runtime-record",
    ),
    _NegativeCase(
        "R11_AUTHORITY_CLEARED", "FAIL", "r11_authority_not_cleared", "runtime-record"
    ),
    _NegativeCase(
        "R12_PHASE_B_GUARDS", "FAIL", "r12_phase_b_guards_unproven", "runtime-record"
    ),
    _NegativeCase(
        "R13_PHASE_B_JOB_ZERO", "FAIL", "r13_phase_b_not_quiescent", "runtime-record"
    ),
    _NegativeCase(
        "R14_RUNTIME_TERMINAL", "FAIL", "r14_runtime_terminal_invalid", "runtime-record"
    ),
    _NegativeCase(
        "R15_WRAPPER_NETWORK_INERT",
        "FAIL",
        "r15_wrapper_network_role_invalid",
        "runtime-record",
    ),
    _NegativeCase(
        "R16_PHASE_A_RAW_ONLY",
        "FAIL",
        "r16_phase_a_downstream_action",
        "runtime-record",
    ),
    _NegativeCase(
        "R17_PHASE_B_STRICT_FLOW",
        "INDETERMINATE",
        "r17_phase_b_flow_missing",
        "boundary-record",
    ),
    _NegativeCase(
        "R18_PHASE_A_TERMINAL_ONCE",
        "FAIL",
        "r18_phase_a_terminalization_invalid",
        "ledger-record",
    ),
    _NegativeCase(
        "R19_A_TO_B_ORDER", "FAIL", "r19_a_to_b_order_invalid", "runtime-record"
    ),
    _NegativeCase(
        "R20_FOUR_STREAM_CLOSEOUT",
        "FAIL",
        "r20_four_stream_closeout_invalid",
        "capture-record",
    ),
    _NegativeCase(
        "R21_EXTANT_RUN_SEAL_EVENTS",
        "FAIL",
        "r21_extant_run_seal_events_invalid",
        "durable-row",
    ),
    _NegativeCase(
        "R22_CAPTURE_START_CONTRACT",
        "FAIL",
        "r22_capture_start_contract_invalid",
        "authority-model",
    ),
    _NegativeCase(
        "L01_RUN_CARDINALITY",
        "FAIL",
        "l01_fixture_or_noncampaign_run",
        "row-projection",
    ),
    _NegativeCase(
        "L02_TERMINAL_EVENT", "FAIL", "l02_terminal_event_invalid", "row-projection"
    ),
    _NegativeCase(
        "L03_POST_TERMINAL_EXTINCTION",
        "FAIL",
        "l03_post_terminal_contradiction",
        "durable-row",
    ),
    _NegativeCase(
        "L04_LEDGER_RECONSTRUCTION",
        "INDETERMINATE",
        "l04_ledger_reconstruction_invalid",
        "ledger-record",
    ),
    _NegativeCase(
        "L05_COUNTER_BIJECTION",
        "INDETERMINATE",
        "l05_counter_ledger_bijection_invalid",
        "counter-record",
    ),
    _NegativeCase(
        "L06_COUNTER_BOOT",
        "INDETERMINATE",
        "l06_counter_boot_ambiguous",
        "counter-record",
    ),
    _NegativeCase(
        "L07_BYTE_ALLOWANCE",
        "INDETERMINATE",
        "l07_detection_allowance_exceeded",
        "counter-record",
    ),
    _NegativeCase(
        "L08_REQUEST_CADENCE", "FAIL", "l08_request_cadence_short", "counter-record"
    ),
    _NegativeCase(
        "L09_TRANSPORT_POLICY",
        "FAIL",
        "l09_transport_policy_violation",
        "ledger-record",
    ),
    _NegativeCase(
        "L10_FRESH_200_BYTES", "FAIL", "l10_fresh_200_bytes_invalid", "origin-record"
    ),
    _NegativeCase(
        "L11_NRC_FIRST_BINDING", "FAIL", "l11_nrc_first_binding_invalid", "run-envelope"
    ),
    _NegativeCase(
        "L12_RESERVATION_RESOLUTION",
        "FAIL",
        "l12_reservation_unresolved",
        "ledger-record",
    ),
    _NegativeCase(
        "D01_ORIGIN_RECEIPT", "FAIL", "d01_origin_receipt_invalid", "origin-record"
    ),
    _NegativeCase(
        "D02_RAW_PROVENANCE_LINKAGE",
        "FAIL",
        "d02_raw_provenance_linkage_invalid",
        "origin-record",
    ),
    _NegativeCase(
        "D03_LAYER3_EXECUTION", "FAIL", "d03_layer3_execution_invalid", "row-projection"
    ),
    _NegativeCase(
        "D04_REVIEW_RESULT", "FAIL", "d04_review_result_invalid", "boundary-record"
    ),
    _NegativeCase(
        "D05_PACKAGE_SET", "FAIL", "d05_package_set_invalid", "boundary-record"
    ),
    _NegativeCase(
        "D06_PACKAGE_PAYLOAD", "FAIL", "d06_package_payload_invalid", "package-payload"
    ),
    _NegativeCase(
        "D07_SUBMIT_RECEIPT", "FAIL", "d07_submit_receipt_invalid", "boundary-record"
    ),
    _NegativeCase(
        "D08_HANDOFF_RECEIPT", "FAIL", "d08_handoff_receipt_invalid", "boundary-record"
    ),
    _NegativeCase(
        "C01_STRICT_NULLS", "FAIL", "c01_strict_url_scalar_nonnull", "durable-row"
    ),
    _NegativeCase(
        "C02_DB_SCALAR_JSON_SCAN",
        "FAIL",
        "c02_forbidden_database_material",
        "db-scan-record",
    ),
    _NegativeCase(
        "C03_NON_SOURCE_FILE_SCAN",
        "FAIL",
        "c03_forbidden_file_material",
        "file-scan-record",
    ),
    _NegativeCase(
        "C04_SERIALIZATION_EVENT_SCAN",
        "FAIL",
        "c04_forbidden_serialized_material",
        "package-payload",
    ),
    _NegativeCase(
        "C05_RUNTIME_LOG_SCAN",
        "FAIL",
        "c05_forbidden_runtime_material",
        "capture-record",
    ),
    _NegativeCase(
        "C06_BOUNDED_DECODERS",
        "INDETERMINATE",
        "c06_bounded_decoder_invalid",
        "db-scan-record",
    ),
    _NegativeCase(
        "C07_SOURCE_EXEMPTION", "FAIL", "c07_source_blob_hash_mismatch", "source-record"
    ),
    _NegativeCase(
        "C08_SECRET_SCAN", "FAIL", "c08_forbidden_secret_material", "file-scan-record"
    ),
    _NegativeCase(
        "F01_EVIDENCE_STABILITY",
        "INDETERMINATE",
        "f01_evidence_stability_mismatch",
        "snapshot",
    ),
    _NegativeCase(
        "F02_DATABASE_STABILITY",
        "INDETERMINATE",
        "f02_database_stability_mismatch",
        "snapshot",
    ),
    _NegativeCase(
        "F03_NONCLAIMS_REPORT",
        "FAIL",
        "f03_nonclaims_contract_invalid",
        "module-contract",
    ),
    _NegativeCase(
        "F04_READ_ONLY_EVALUATION",
        "FAIL",
        "f04_session_has_pending_writes",
        "session-state",
    ),
    _NegativeCase(
        "F05_PROJECTION_REDERIVATION",
        "FAIL",
        "f05_package_projection_changed",
        "package-payload",
    ),
    _NegativeCase(
        "F06_NO_EGRESS_DEPENDENCY",
        "FAIL",
        "f06_egress_import_present",
        "module-contract",
    ),
    _NegativeCase(
        "F07_PUBLIC_API_CONTRACT",
        "FAIL",
        "f07_public_api_contract_invalid",
        "module-contract",
    ),
    _NegativeCase(
        "F08_RESULT_AGGREGATION",
        "FAIL",
        "f08_check_registry_invalid",
        "module-contract",
    ),
    _NegativeCase(
        "F09_CONNECTOR_AND_COMBINED_REPORTS",
        "FAIL",
        "f09_result_domains_invalid",
        "boundary-record",
    ),
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _patch_setting(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: object,
) -> None:
    monkeypatch.setattr(settings, name, value)


def _build_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_path: Path,
    storage: Path,
    started_at: datetime,
) -> _Authority:
    campaign_id = uuid4()
    evidence_root = tmp_path / "evidence"
    campaigns_dir = evidence_root / "campaigns"
    grants_dir = evidence_root / "grants"
    indexes_dir = evidence_root / "indexes"
    for path in (
        campaigns_dir,
        grants_dir,
        indexes_dir,
        evidence_root / "consumed",
        evidence_root / "logs",
        evidence_root / "log-seals",
    ):
        path.mkdir(parents=True, exist_ok=True)

    definition = DualLiveCampaignDefinitionV1(
        schema_id="project6.dual_live_campaign_definition.v1",
        campaign_id=campaign_id,
        code_revision=CODE_REVISION,
        connector_keys=("sciencebase_mcs", "nrc_adams_aps"),
        sciencebase_target=ScienceBaseFreshTargetV1(
            connector_key="sciencebase_mcs",
            item_id=ITEM_ID,
            exact_file_name=FILE_NAME,
            locator_key="downloadUri",
        ),
        nrc_target=NrcApsFreshTargetV1(
            connector_key="nrc_adams_aps",
            accession_number=ACCESSION,
        ),
        acceptance_profile="dual_live_to_internal_handoff_v1",
        evidence_profile="dual_live_evidence_v1",
        review_policy="security_egress_and_layer3_integrity_v1",
        required_review_roles=("security_egress", "layer3_integrity"),
        execution_order="nrc_then_sciencebase",
        package_kinds=("canonical_internal", "user_facing", "review_facing"),
        not_before=started_at - timedelta(hours=1),
        expires_at=started_at + timedelta(hours=1),
        non_authorities=CAMPAIGN_NON_AUTHORITIES,
    )
    definition_bytes = canonical_json_bytes(definition)
    definition_sha256 = _sha256(definition_bytes)
    campaign_fingerprint = _sha256(canonical_json_bytes(definition))
    definition_path = campaigns_dir / f"{definition_sha256}.json"
    definition_path.write_bytes(definition_bytes)

    grant_models: dict[str, ConnectorEgressGrantV1] = {}
    grant_paths: dict[str, Path] = {}
    grant_sha256s: dict[str, str] = {}
    entries: list[dict[str, Any]] = []
    for connector_key in ("nrc_adams_aps", "sciencebase_mcs"):
        sciencebase = connector_key == "sciencebase_mcs"
        grant = ConnectorEgressGrantV1(
            schema_id="project6.connector_egress_grant.v1",
            grant_id=f"grant-{connector_key}",
            connector_key=connector_key,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
            campaign_definition_sha256=definition_sha256,
            code_revision=CODE_REVISION,
            arming_nonce=uuid4(),
            max_armings=1,
            supersedes_grant_sha256=None,
            issued_at=started_at - timedelta(minutes=30),
            expires_at=started_at + timedelta(minutes=30),
            operator_mode="local_loopback",
            target=(
                ScienceBaseFreshTargetV1(
                    connector_key="sciencebase_mcs",
                    item_id=ITEM_ID,
                    exact_file_name=FILE_NAME,
                    locator_key="downloadUri",
                )
                if sciencebase
                else NrcApsFreshTargetV1(
                    connector_key="nrc_adams_aps",
                    accession_number=ACCESSION,
                )
            ),
            request_rules=expected_grant_rule_payloads(connector_key),
            max_physical_requests=3 if sciencebase else 2,
            max_run_bytes=70 * 1024 * 1024,
            max_single_send_detection_allowance_bytes=(
                SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
            ),
            request_timeout_seconds=30,
            min_request_interval_ms=250,
            non_authorities=(
                COMMON_GRANT_NON_AUTHORITIES
                if sciencebase
                else NRC_GRANT_NON_AUTHORITIES
            ),
        )
        grant_bytes = canonical_json_bytes(grant)
        grant_sha256 = _sha256(grant_bytes)
        grant_path = grants_dir / f"{grant_sha256}.json"
        grant_path.write_bytes(grant_bytes)
        run_id = connector_egress_arming.compute_parent_arming_id(
            connector_key=connector_key,
            campaign_id=str(campaign_id),
            grant_sha256=grant_sha256,
            arming_nonce=grant.arming_nonce,
        )
        marker = ConnectorGrantConsumptionMarkerV1(
            schema_id="project6.connector_grant_consumption.v1",
            connector_key=connector_key,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
            campaign_definition_sha256=definition_sha256,
            raw_grant_sha256=grant_sha256,
            canonical_grant_fingerprint=_sha256(canonical_json_bytes(grant)),
            arming_nonce=grant.arming_nonce,
            connector_run_id=run_id,
            max_armings=1,
        )
        marker_bytes = canonical_json_bytes(marker)
        entries.append(
            {
                "campaign_id": str(campaign_id),
                "campaign_fingerprint": campaign_fingerprint,
                "campaign_definition_sha256": definition_sha256,
                "connector_key": connector_key,
                "code_revision": CODE_REVISION,
                "raw_grant_sha256": grant_sha256,
                "canonical_grant_fingerprint": _sha256(canonical_json_bytes(grant)),
                "grant_relative_path": f"grants/{grant_sha256}.json",
                "consumption_marker_sha256": _sha256(marker_bytes),
                "consumption_marker_relative_path": (f"consumed/{grant_sha256}.json"),
            }
        )
        grant_models[connector_key] = grant
        grant_paths[connector_key] = grant_path
        grant_sha256s[connector_key] = grant_sha256

    capture_ref = ConnectorCampaignLogCaptureRefV1(
        campaign_id=str(campaign_id),
        campaign_fingerprint=campaign_fingerprint,
        campaign_definition_sha256=definition_sha256,
        code_revision=CODE_REVISION,
        log_dir_relative_path=f"logs/{campaign_fingerprint}",
        manifest_relative_path=f"logs/{campaign_fingerprint}/manifest.json",
        seal_relative_path=f"log-seals/{campaign_fingerprint}.json",
        expected_stream_files=(
            "app.jsonl",
            "http.jsonl",
            "stdout.log",
            "stderr.log",
        ),
    )
    index = ConnectorCampaignEvidenceIndexV1.model_validate(
        {
            "schema_id": "project6.connector_campaign_evidence_index.v1",
            "revision": 1,
            "predecessor_index_sha256": None,
            "predecessor_index_relative_path": None,
            "campaigns": (
                {
                    "campaign_id": str(campaign_id),
                    "campaign_fingerprint": campaign_fingerprint,
                    "code_revision": CODE_REVISION,
                    "raw_definition_sha256": definition_sha256,
                    "definition_relative_path": (f"campaigns/{definition_sha256}.json"),
                },
            ),
            "entries": tuple(entries),
            "log_captures": (capture_ref.model_dump(mode="json"),),
        }
    )
    index_bytes = canonical_json_bytes(index)
    index_sha256 = _sha256(index_bytes)
    index_path = indexes_dir / f"{index_sha256}.json"
    index_path.write_bytes(index_bytes)

    configured = {
        "storage_dir": str(storage),
        "database_url": f"sqlite:///{db_path.as_posix()}",
        "connector_campaign_definition_path": definition_path,
        "connector_campaign_definition_sha256": definition_sha256,
        "connector_sciencebase_grant_path": grant_paths["sciencebase_mcs"],
        "connector_sciencebase_grant_sha256": grant_sha256s["sciencebase_mcs"],
        "connector_nrc_aps_grant_path": grant_paths["nrc_adams_aps"],
        "connector_nrc_aps_grant_sha256": grant_sha256s["nrc_adams_aps"],
        "connector_campaign_evidence_root": evidence_root,
        "connector_campaign_evidence_index_path": index_path,
        "connector_campaign_evidence_index_sha256": index_sha256,
        "connector_live_egress_enabled": True,
        "connector_live_egress_exclusive_proof_mode": True,
        "connector_egress_arming_max_ttl_seconds": 3_600,
        "connector_lease_ttl_seconds": 3_600,
        "nrc_adams_subscription_key": "acceptance-secret-never-persisted",
    }
    for name, value in configured.items():
        _patch_setting(monkeypatch, name, value)
    proof_settings = Settings(
        DATABASE_URL=configured["database_url"],
        STORAGE_DIR=configured["storage_dir"],
        CONNECTOR_CAMPAIGN_DEFINITION_PATH=str(definition_path),
        CONNECTOR_CAMPAIGN_DEFINITION_SHA256=definition_sha256,
        CONNECTOR_SCIENCEBASE_GRANT_PATH=str(grant_paths["sciencebase_mcs"]),
        CONNECTOR_SCIENCEBASE_GRANT_SHA256=grant_sha256s["sciencebase_mcs"],
        CONNECTOR_NRC_APS_GRANT_PATH=str(grant_paths["nrc_adams_aps"]),
        CONNECTOR_NRC_APS_GRANT_SHA256=grant_sha256s["nrc_adams_aps"],
        CONNECTOR_CAMPAIGN_EVIDENCE_ROOT=str(evidence_root),
        CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH=str(index_path),
        CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256=index_sha256,
        CONNECTOR_LIVE_EGRESS_ENABLED=True,
        CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE=True,
        NRC_ADAMS_APS_SUBSCRIPTION_KEY="acceptance-secret-never-persisted",
    )
    return _Authority(
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        definition_sha256=definition_sha256,
        grants=grant_models,
        grant_sha256s=grant_sha256s,
        evidence_root=evidence_root,
        index_path=index_path,
        index_sha256=index_sha256,
        proof_settings=proof_settings,
    )


def _operator_receipt(grant: Any) -> dict[str, Any]:
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
        "auth_owner_mode": "identity_presence",
        "authorization_mode": "identity_presence",
        "role": None,
        "access": "write",
    }


def _resolve_current_grants(
    authority: _Authority,
    *,
    now: datetime,
) -> dict[str, Any]:
    campaign = resolve_current_dual_live_campaign_definition(
        expected_campaign_id=str(authority.campaign_id),
        expected_campaign_fingerprint=authority.campaign_fingerprint,
        code_revision=CODE_REVISION,
        now=now,
    )
    return {
        connector_key: resolve_current_connector_egress_grant(
            verified_campaign=campaign,
            connector_key=connector_key,
            expected_grant_sha256=authority.grant_sha256s[connector_key],
            campaign_id=str(authority.campaign_id),
            campaign_fingerprint=authority.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=now,
        )
        for connector_key in ("nrc_adams_aps", "sciencebase_mcs")
    }


def _create_and_lease_run(
    db: Session,
    *,
    grant: Any,
    now: datetime,
) -> tuple[ConnectorRun, str]:
    connector_key = str(grant.model.connector_key)
    run, created = connector_egress_arming.create_connector_egress_arming(
        db,
        payload=ConnectorEgressArmingIn(
            schema_id="project6.connector_egress_arming.v1",
            client_request_id=f"accept-{connector_key}",
            connector_key=connector_key,
            campaign_id=grant.model.campaign_id,
            campaign_fingerprint=grant.model.campaign_fingerprint,
            grant_sha256=grant.raw_sha256,
        ),
        verified_grant=grant,
        operator_receipt=_operator_receipt(grant),
        code_revision=CODE_REVISION,
    )
    assert created is True
    run, claimed = connector_egress_arming.claim_connector_egress_arming(
        db,
        connector_run_id=run.connector_run_id,
        execution_idempotency_key=f"execute-{connector_key}",
        expected_arming_fingerprint=str(run.request_fingerprint),
        now=datetime.now(UTC),
    )
    assert claimed is True
    if connector_key == "nrc_adams_aps":
        lease_token = connectors_nrc_adams._acquire_strict_run_lease(
            db,
            run=run,
        )
    else:
        lease_token = connectors_sciencebase._acquire_strict_sciencebase_run_lease(
            db,
            run=run,
        )
    assert isinstance(lease_token, str) and lease_token
    assert run.status == "running"
    return run, lease_token


def _counter_record(
    *,
    reservation: Any,
    body: bytes,
    started_at: datetime,
    completed_at: datetime,
    monotonic_started_at: float,
    runtime_instance_id: str,
) -> dict[str, Any]:
    digest = _sha256(body)
    return {
        "schema_id": "project6.connector_http_counter.v2",
        "ordinal": reservation.ordinal,
        "stage": reservation.stage,
        "request_fingerprint": reservation.request_fingerprint,
        "canonical_status_header_bytes": 17,
        "delivered_body_bytes": len(body),
        "decoded_body_bytes": len(body),
        "decoded_body_sha256": digest,
        "response_status": 200,
        "error_class": None,
        "monotonic_started_at": monotonic_started_at,
        "monotonic_stopped_at": monotonic_started_at + 0.1,
        "evidence_started_at": connector_egress_transport.utc_six_z(started_at),
        "evidence_stopped_at": connector_egress_transport.utc_six_z(completed_at),
        "runtime_instance_id": runtime_instance_id,
        "process_boot_id": COUNTER_BOOT_ID,
    }


def _complete_request(
    *,
    run: ConnectorRun,
    lease_token: str,
    ordinal: int,
    stage: str,
    request: connector_egress_transport.FrozenPhysicalRequest,
    body: bytes,
    now: datetime,
    prior_records: list[dict[str, Any]],
    runtime_instance_id: str,
    monotonic_started_at: float,
    expected_derived_arming_hash: str | None = None,
) -> dict[str, Any]:
    reservation = connector_egress_transport.reserve_physical_request(
        connector_run_id=run.connector_run_id,
        lease_token=lease_token,
        arming_fingerprint=str(run.request_fingerprint),
        ordinal=ordinal,
        stage=stage,
        request=request,
        expected_derived_arming_hash=expected_derived_arming_hash,
        now=now,
        counter_records=prior_records,
    )
    started_at = now
    completed_at = now
    digest = _sha256(body)
    connector_egress_transport.complete_physical_request(
        reservation=reservation,
        outcome=connector_egress_transport.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=len(body),
            body_sha256=digest,
            counted_status_header_bytes=17,
            delivered_body_bytes=len(body),
            decoded_body_bytes=len(body),
            decoded_body_sha256=digest,
            send_started_at=started_at,
            completed_at=completed_at,
        ),
    )
    return _counter_record(
        reservation=reservation,
        body=body,
        started_at=started_at,
        completed_at=completed_at,
        monotonic_started_at=monotonic_started_at,
        runtime_instance_id=runtime_instance_id,
    )


def _write_counters(writer: Any, records: list[dict[str, Any]]) -> None:
    for record in records:
        encoded = canonical_json_bytes(record) + b"\n"
        assert writer.write(encoded) == len(encoded)
    writer.flush()


def _nrc_target(
    db: Session,
    *,
    run: ConnectorRun,
    raw_path: Path,
    detail_hash: str,
    completed_at: datetime,
) -> ConnectorRunTarget:
    digest = _sha256(NRC_BYTES)
    target = ConnectorRunTarget(
        connector_run_target_id=f"target-{run.connector_run_id}",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        stable_release_key=ACCESSION,
        stable_release_identifier=f"adams_accession:{ACCESSION}",
        identifiers_json=[{"type": "AccessionNumber", "value": ACCESSION}],
        sciencebase_file_name=f"{ACCESSION}.pdf",
        artifact_surface="files",
        selection_source="strict_exact_accession",
        selection_scope="dual_live_proof_v1",
        selection_match_basis="exact_accession",
        artifact_locator_type=connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS,
        source_artifact_key=f"nrc_adams_aps::{ACCESSION}",
        canonical_artifact_key=f"nrc_adams_aps::{ACCESSION}",
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path.resolve()),
        fetch_policy_mode="strict_live_egress",
        redirect_count=0,
        aliases_json=[],
        source_reference_json={
            "schema_id": "project6.nrc_raw_admission.v1",
            "accession_number": ACCESSION,
            "artifact_file_name": f"{ACCESSION}.pdf",
            "detail_response_sha256": detail_hash,
            "artifact_url_sha256": _sha256(NRC_ARTIFACT_URL.encode("ascii")),
            "artifact_path_class": (connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS),
            "raw_content_sha256": digest,
            "raw_content_size_bytes": len(NRC_BYTES),
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
    run.discovered_count = 1
    run.selected_count = 1
    run.downloaded_count = 1
    run.consumed_bytes = len(NRC_BYTES)
    run.failed_count = 0
    run.terminal_target_count = 1
    run.nonterminal_target_count = 0
    db.add(target)
    db.commit()
    return target


def _sciencebase_target(
    db: Session,
    *,
    run: ConnectorRun,
    raw_path: Path,
    completed_at: datetime,
) -> tuple[ConnectorRunTarget, L3ConnectorSourceIntakeRecord]:
    digest = _sha256(SCIENCEBASE_BYTES)
    target = ConnectorRunTarget(
        connector_run_target_id=f"target-{run.connector_run_id}",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id=ITEM_ID,
        sciencebase_item_url=None,
        sciencebase_file_name=FILE_NAME,
        sciencebase_download_uri=None,
        artifact_surface="files",
        artifact_locator_type="downloadUri_hash_only",
        source_artifact_key=f"sciencebase:{ITEM_ID}:{FILE_NAME}",
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path.resolve()),
        public_read_confirmed=True,
        status="downloaded",
        retry_eligible=False,
        attempt_count=1,
        downloaded_at=completed_at,
        last_attempt_at=completed_at,
        last_stage_transition_at=completed_at,
    )
    run.discovered_count = 1
    run.selected_count = 1
    run.downloaded_count = 1
    run.consumed_bytes = len(SCIENCEBASE_BYTES)
    run.failed_count = 0
    run.terminal_target_count = 1
    run.nonterminal_target_count = 0
    db.add(target)
    db.commit()
    intake = layer3_connector_source_intake._stage_strict_sciencebase_source_intake(
        db,
        run=run,
        target=target,
    )
    dataset = Dataset(
        dataset_id=f"dataset-{run.connector_run_id}",
        name="MCS Germanium acceptance fixture",
    )
    version = DatasetVersion(
        dataset_version_id=f"version-{run.connector_run_id}",
        dataset_id=dataset.dataset_id,
        version_label="fresh",
        version_type="source",
        storage_ref=str(raw_path.resolve()),
        content_hash=digest,
    )
    provenance = DatasetSourceProvenance(
        dataset_source_provenance_id=f"provenance-{run.connector_run_id}",
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
            "item_id": ITEM_ID,
            "exact_file_name": FILE_NAME,
            "artifact_surface": "files",
            "source_mode": "strict_live_egress",
            "raw_sha256": digest,
            "storage_class": "connector_raw_sha256",
        },
    )
    target.dataset_id = dataset.dataset_id
    target.dataset_version_id = version.dataset_version_id
    db.add_all([dataset, version, provenance])
    db.commit()
    return target, intake


def _mint_origin(
    db: Session,
    *,
    target: ConnectorRunTarget,
) -> dict[str, str]:
    db.rollback()
    with db.begin():
        projection = layer3_origin_continuity.mint_connector_origin_receipt(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    db.refresh(target)
    return cast(dict[str, str], projection)


def _produce_real_runs(
    db: Session,
    *,
    grants: Mapping[str, Any],
    capture: Any,
    started_at: datetime,
    runtime_instance_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    dict[str, ConnectorRunTarget],
    dict[str, dict[str, str]],
    tuple[dict[str, Any], ...],
]:
    factory = sessionmaker(
        bind=db.get_bind(),
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    monkeypatch.setattr(connector_egress_transport, "SESSION_FACTORY", factory)
    raw_root = Path(settings.connector_raw_dir)
    raw_root.mkdir(parents=True, exist_ok=True)
    counter_writer = next(
        writer for writer in capture.writers if writer.stream_class == "http"
    )
    counters: list[dict[str, Any]] = []

    nrc_run, nrc_lease = _create_and_lease_run(
        db,
        grant=grants["nrc_adams_aps"],
        now=started_at,
    )
    nrc_detail = b"{}"
    counters.append(
        _complete_request(
            run=nrc_run,
            lease_token=nrc_lease,
            ordinal=1,
            stage="exact_accession_api",
            request=connector_egress_transport.FrozenPhysicalRequest(
                method="GET",
                url=NRC_DETAIL_URL,
                headers={
                    "Accept-Encoding": "identity",
                    "Ocp-Apim-Subscription-Key": ("acceptance-secret-never-persisted"),
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
        normalized_url=NRC_ARTIFACT_URL,
        verified_grant=grants["nrc_adams_aps"],
    )
    counters.append(
        _complete_request(
            run=nrc_run,
            lease_token=nrc_lease,
            ordinal=2,
            stage="artifact",
            request=connector_egress_transport.FrozenPhysicalRequest(
                method="GET",
                url=NRC_ARTIFACT_URL,
                headers={"Accept-Encoding": "identity"},
                credential_audience="none",
            ),
            body=NRC_BYTES,
            now=datetime.now(UTC),
            prior_records=counters,
            runtime_instance_id=runtime_instance_id,
            monotonic_started_at=2.0,
            expected_derived_arming_hash=nrc_derived.url_sha256,
        )
    )
    nrc_digest = _sha256(NRC_BYTES)
    nrc_raw_path = raw_root / nrc_aps_artifact_ingestion.blob_relative_path(
        sha256=nrc_digest
    )
    persist_locked_raw_file(raw_root, nrc_raw_path, NRC_BYTES)
    nrc_terminal_at = datetime.now(UTC)
    nrc_target = _nrc_target(
        db,
        run=nrc_run,
        raw_path=nrc_raw_path,
        detail_hash=_sha256(nrc_detail),
        completed_at=nrc_terminal_at,
    )
    connector_egress_arming.finalize_strict_run(
        db,
        run=nrc_run,
        lease_token=nrc_lease,
        terminal_status="completed",
        outcome_class="nrc_raw_admission_completed",
        now=nrc_terminal_at,
    )
    _write_counters(counter_writer, counters)

    nrc_target_id = nrc_target.connector_run_target_id
    db.rollback()
    nrc_aps_phase_b_linkage.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=nrc_target_id,
    )

    sciencebase_run, sciencebase_lease = _create_and_lease_run(
        db,
        grant=grants["sciencebase_mcs"],
        now=started_at + timedelta(seconds=4),
    )
    metadata = b'{"title":"MCS acceptance fixture"}'
    counters.append(
        _complete_request(
            run=sciencebase_run,
            lease_token=sciencebase_lease,
            ordinal=1,
            stage="item_hydration",
            request=connector_egress_transport.FrozenPhysicalRequest(
                method="GET",
                url=SCIENCEBASE_DETAIL_URL,
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
    _write_counters(counter_writer, counters[-1:])
    sciencebase_derived = connector_egress_arming.commit_derived_url_arming(
        db,
        run=sciencebase_run,
        lease_token=sciencebase_lease,
        ordinal=2,
        stage="artifact",
        normalized_url=SCIENCEBASE_ARTIFACT_URL,
        verified_grant=grants["sciencebase_mcs"],
    )
    counters.append(
        _complete_request(
            run=sciencebase_run,
            lease_token=sciencebase_lease,
            ordinal=2,
            stage="artifact",
            request=connector_egress_transport.FrozenPhysicalRequest(
                method="GET",
                url=SCIENCEBASE_ARTIFACT_URL,
                headers={"Accept-Encoding": "identity"},
                credential_audience="none",
            ),
            body=SCIENCEBASE_BYTES,
            now=datetime.now(UTC),
            prior_records=counters,
            runtime_instance_id=runtime_instance_id,
            monotonic_started_at=4.0,
            expected_derived_arming_hash=sciencebase_derived.url_sha256,
        )
    )
    sciencebase_digest = _sha256(SCIENCEBASE_BYTES)
    sciencebase_raw_path = raw_root / "sha256" / f"{sciencebase_digest}.csv"
    persist_locked_raw_file(raw_root, sciencebase_raw_path, SCIENCEBASE_BYTES)
    sciencebase_terminal_at = datetime.now(UTC)
    sciencebase_target, _ = _sciencebase_target(
        db,
        run=sciencebase_run,
        raw_path=sciencebase_raw_path,
        completed_at=sciencebase_terminal_at,
    )
    connector_egress_arming.finalize_strict_run(
        db,
        run=sciencebase_run,
        lease_token=sciencebase_lease,
        terminal_status="completed",
        outcome_class="sciencebase_raw_admitted",
        now=sciencebase_terminal_at,
    )
    _write_counters(counter_writer, counters[-1:])

    targets = {
        "nrc_adams_aps": nrc_target,
        "sciencebase_mcs": sciencebase_target,
    }
    projections = {
        connector_key: _mint_origin(db, target=target)
        for connector_key, target in targets.items()
    }
    return targets, projections, tuple(counters)


def _sciencebase_decision(
    db: Session,
    *,
    target: ConnectorRunTarget,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    intake = db.scalar(
        select(L3ConnectorSourceIntakeRecord).where(
            L3ConnectorSourceIntakeRecord.connector_run_target_id
            == target.connector_run_target_id
        )
    )
    assert intake is not None
    preview = layer3_connector_source_intake.connector_source_intake_material_preview(
        db,
        connector_source_intake_record_id=(intake.connector_source_intake_record_id),
    )
    candidate = cast(dict[str, Any], preview["material_candidate"])
    basis = {
        key: copy.deepcopy(candidate[key])
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
    decision = {
        "candidate_id": candidate["candidate_id"],
        "source_class": candidate["source_class"],
        "decision": "approved",
        "decision_basis": basis,
        "source_identity": copy.deepcopy(candidate["source_identity"]),
        "source_provenance": copy.deepcopy(candidate["source_provenance"]),
        "payload": copy.deepcopy(candidate["payload"]),
        "load_summary": copy.deepcopy(candidate["load_summary"]),
    }
    return (
        decision,
        cast(dict[str, Any], candidate["source_identity"]),
        cast(dict[str, Any], candidate["source_provenance"]),
        cast(dict[str, Any], candidate["payload"]),
    )


def _record_downstream_action(
    receipts: list[dict[str, str]],
    *,
    action: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    copied = cast(dict[str, Any], json.loads(canonical_json_bytes(result)))
    receipts.append(
        {
            "action": action,
            "result_sha256": _sha256(canonical_json_bytes(copied)),
        }
    )
    return copied


def _nrc_decision(
    db: Session,
    *,
    target: ConnectorRunTarget,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    linkage = db.scalar(
        select(ApsContentLinkage).where(
            ApsContentLinkage.target_id == target.connector_run_target_id
        )
    )
    assert linkage is not None
    document = db.scalar(
        select(ApsContentDocument).where(
            ApsContentDocument.content_id == linkage.content_id
        )
    )
    assert document is not None
    identity = {
        "schema_id": "layer3.aps_content_document_source_identity.v1",
        "source_class": "aps_content_document",
        "content_id": document.content_id,
        "content_contract_id": document.content_contract_id,
        "chunking_contract_id": document.chunking_contract_id,
        "normalization_contract_id": document.normalization_contract_id,
        "content_status": document.content_status,
        "media_type": document.media_type,
        "document_class": document.document_class,
        "quality_status": document.quality_status,
    }
    provenance = {
        "schema_id": "layer3.aps_content_document_source_provenance.v1",
        "content_id": document.content_id,
        "query_basis": "dual-live-proof",
        "aps_content_linkages": [
            {
                "aps_content_linkage_id": linkage.aps_content_linkage_id,
                "content_id": linkage.content_id,
                "run_id": linkage.run_id,
                "target_id": linkage.target_id,
                "accession_number": linkage.accession_number,
                "content_contract_id": linkage.content_contract_id,
                "chunking_contract_id": linkage.chunking_contract_id,
                "content_units_ref": linkage.content_units_ref,
                "normalized_text_ref": linkage.normalized_text_ref,
                "normalized_text_sha256": linkage.normalized_text_sha256,
                "blob_ref": linkage.blob_ref,
                "blob_sha256": linkage.blob_sha256,
                "download_exchange_ref": linkage.download_exchange_ref,
                "discovery_ref": linkage.discovery_ref,
                "selection_ref": linkage.selection_ref,
                "diagnostics_ref": linkage.diagnostics_ref,
            }
        ],
        "source_trace": {
            "document_identity": {"content_id": document.content_id},
            "aps_trace_refs": {
                "run_id": target.connector_run_id,
                "target_id": target.connector_run_target_id,
            },
        },
    }
    payload = {"content_id": document.content_id}
    load_summary = {"loaded_records": 1, "failed_records": 0}
    basis = {
        "source_ref": f"aps_content_document:{document.content_id}",
        "query_basis": "dual-live-proof",
        "provenance_ref": f"aps_content_document:{document.content_id}",
        "source_identity": copy.deepcopy(identity),
        "source_provenance": copy.deepcopy(provenance),
        "payload": copy.deepcopy(payload),
        "load_summary": copy.deepcopy(load_summary),
    }
    decision = {
        "candidate_id": f"mat-aps_content_document-{document.content_id[:12]}",
        "source_class": "aps_content_document",
        "decision": "approved",
        "decision_basis": basis,
        "source_identity": copy.deepcopy(identity),
        "source_provenance": copy.deepcopy(provenance),
        "payload": copy.deepcopy(payload),
        "load_summary": load_summary,
    }
    return decision, identity, provenance, payload


def _public_sciencebase_downstream(
    db: Session,
    *,
    target: ConnectorRunTarget,
    receipts: list[dict[str, str]],
) -> tuple[L3Session, dict[str, Any]]:
    intake = db.scalar(
        select(L3ConnectorSourceIntakeRecord).where(
            L3ConnectorSourceIntakeRecord.connector_run_target_id
            == target.connector_run_target_id
        )
    )
    assert intake is not None
    material = _record_downstream_action(
        receipts,
        action="sciencebase_material_preview",
        result=(
            layer3_connector_source_intake.connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=(
                    intake.connector_source_intake_record_id
                ),
            )
        ),
    )
    candidate = cast(dict[str, Any], material["material_candidate"])
    assert candidate["source_class"] == (
        layer3_connector_source_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )
    decision_basis = {
        key: copy.deepcopy(candidate[key])
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
    gate_b = _record_downstream_action(
        receipts,
        action="sciencebase_gate_b_decision",
        result=layer3_workbench.gate_b_decision(
            db,
            {
                "client_request_id": "l3-sb-acceptance-gate-b",
                "preflight_id": "l3-sb-acceptance-preflight",
                "source_set_id": "l3-sb-acceptance-source-set",
                "material_preview_id": material["material_preview_id"],
                "material_preview_hash": material["material_preview_hash"],
                "candidate_decisions": [
                    {
                        "candidate_id": candidate["candidate_id"],
                        "decision": "approved",
                        "decision_basis": decision_basis,
                    }
                ],
                "commit_reason": "dual_live_acceptance_sciencebase",
                "actor": "pytest",
            },
        ),
    )
    assert gate_b["next_state"] == "gate_c_preview_ready"
    gate_c = _record_downstream_action(
        receipts,
        action="sciencebase_gate_c_typing",
        result=layer3_workbench.gate_c_preview(
            db,
            {
                "client_request_id": "l3-sb-acceptance-gate-c",
                "session_id": gate_b["session_id"],
                "commit_typing": True,
            },
        ),
    )
    assert gate_c["next_state"] == "plan_preview_ready"
    preview = _record_downstream_action(
        receipts,
        action="sciencebase_plan_preview",
        result=layer3_workbench.plan_preview(
            db,
            {
                "client_request_id": "l3-sb-acceptance-plan-preview",
                "session_id": gate_b["session_id"],
            },
        ),
    )
    approval = _record_downstream_action(
        receipts,
        action="sciencebase_plan_approval",
        result=layer3_workbench.plan_approval(
            db,
            {
                "client_request_id": "l3-sb-acceptance-plan-approval",
                "session_id": gate_b["session_id"],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "operator_confirmation": True,
            },
        ),
    )
    selection = _record_downstream_action(
        receipts,
        action="sciencebase_execution_selection",
        result=layer3_workbench.execution_selection(
            db,
            {
                "client_request_id": "l3-sb-acceptance-selection",
                "session_id": gate_b["session_id"],
                "analysis_plan_id": approval["analysis_plan_id"],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
            },
        ),
    )
    pass_run = db.get(L3PassRun, selection["pass_run_ids"][0])
    assert pass_run is not None
    planned = pass_run.summary_json["planned_pass"]
    receipt = target.source_reference_json[
        layer3_origin_continuity.ORIGIN_RECEIPT_STORAGE_KEY
    ]
    assert planned["source_intake_source_shape"] == (
        layer3_connector_source_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )
    assert planned["connector_source_intake_record_id"] == (
        intake.connector_source_intake_record_id
    )
    assert planned["connector_run_id"] == target.connector_run_id
    assert planned["connector_run_target_id"] == target.connector_run_target_id
    assert planned["connector_origin_receipt_hash"] == receipt["receipt_hash"]
    finish = _public_finish_selected_pass(
        db,
        flow={
            "session_id": gate_b["session_id"],
            "analysis_plan_id": approval["analysis_plan_id"],
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
        action_prefix="sciencebase",
        receipts=receipts,
    )
    session = db.get(L3Session, gate_b["session_id"])
    assert session is not None
    package_commit = finish["package_commit"]
    handoff = finish["handoff"]
    return session, {
        "analysis_plan_id": approval["analysis_plan_id"],
        "analysis_run_id": finish["start"].get("analysis_run_id"),
        "candidate_id": candidate["candidate_id"],
        "connector_key": "sciencebase_mcs",
        "connector_origin_receipt_hash": receipt["receipt_hash"],
        "connector_run_id": target.connector_run_id,
        "connector_run_target_id": target.connector_run_target_id,
        "construction_basis_hash": package_commit["construction_basis_hash"],
        "handoff_export_envelope_ref": handoff[
            "handoff_export_envelope_ref"
        ],
        "output_package_ids": package_commit["output_package_ids"],
        "package_kinds": package_commit["package_kinds"],
        "package_review_preview_hash": finish["package_preview"][
            "package_review_preview_hash"
        ],
        "package_review_submit_record_ref": finish["submit"][
            "submit_record_ref"
        ],
        "pass_run_id": pass_run.pass_run_id,
        "payload_hashes": package_commit["payload_hashes"],
        "prepare_record_ref": handoff["prepare_record_ref"],
        "reconciliation_record_id": package_commit["reconciliation_record_id"],
        "result_review_record_ref": finish["review"]["review_record_ref"],
        "session_id": session.session_id,
        "source_shape": handoff["source_shape"],
        "source_record_id": intake.connector_source_intake_record_id,
    }


def _public_finish_reviewable_pass(
    db: Session,
    *,
    flow: Mapping[str, str],
    analysis_run_id: str | None,
    action_prefix: str,
    receipts: list[dict[str, str]],
) -> dict[str, Any]:
    common = {
        "session_id": flow["session_id"],
        "analysis_plan_id": flow["analysis_plan_id"],
        "pass_run_id": flow["pass_run_id"],
        "preview_id": flow["preview_id"],
        "preview_hash": flow["preview_hash"],
    }
    review = _record_downstream_action(
        receipts,
        action=f"{action_prefix}_execution_result_review",
        result=layer3_workbench.execution_result_review(
            db,
            {
                "client_request_id": f"{flow['session_id']}-review",
                **common,
                "analysis_run_id": analysis_run_id,
                "operator_decision": "approved",
                "reviewed_output_items": [],
            },
        ),
    )
    package_preview = _record_downstream_action(
        receipts,
        action=f"{action_prefix}_package_review_preview",
        result=layer3_workbench.package_review_preview(
            db,
            {
                "client_request_id": f"{flow['session_id']}-package-preview",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review["review_record_ref"],
            },
        ),
    )
    package_commit = _record_downstream_action(
        receipts,
        action=f"{action_prefix}_package_construction_commit",
        result=layer3_workbench.package_construction_commit(
            db,
            {
                "client_request_id": f"{flow['session_id']}-package-commit",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": package_preview[
                    "package_review_preview_hash"
                ],
                "expected_package_kinds": [
                    "canonical_internal",
                    "user_facing",
                    "review_facing",
                ],
            },
        ),
    )
    submit = _record_downstream_action(
        receipts,
        action=f"{action_prefix}_package_review_submit",
        result=layer3_workbench.package_review_submit(
            db,
            {
                "client_request_id": f"{flow['session_id']}-package-submit",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": package_preview[
                    "package_review_preview_hash"
                ],
                "construction_basis_hash": package_commit[
                    "construction_basis_hash"
                ],
                "reconciliation_record_id": package_commit[
                    "reconciliation_record_id"
                ],
                "output_package_ids": package_commit["output_package_ids"],
                "payload_refs": package_commit["payload_refs"],
                "payload_hashes": package_commit["payload_hashes"],
                "expected_package_kinds": [
                    "canonical_internal",
                    "user_facing",
                    "review_facing",
                ],
                "operator_decision": "approved",
            },
        ),
    )
    handoff = _record_downstream_action(
        receipts,
        action=f"{action_prefix}_handoff_export_prepare",
        result=layer3_workbench.handoff_export_prepare(
            db,
            {
                "client_request_id": f"{flow['session_id']}-handoff",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": package_preview[
                    "package_review_preview_hash"
                ],
                "construction_basis_hash": package_commit[
                    "construction_basis_hash"
                ],
                "reconciliation_record_id": package_commit[
                    "reconciliation_record_id"
                ],
                "package_review_submit_record_ref": submit["submit_record_ref"],
                "package_review_state": submit["package_review_state"],
                "package_review_submit_schema_id": submit["schema_id"],
                "handoff_target": "internal_export_envelope",
                "export_mode": "prepare_only",
                "operator_decision": "authorize_prepare",
                "output_package_ids": package_commit["output_package_ids"],
                "payload_refs": package_commit["payload_refs"],
                "payload_hashes": package_commit["payload_hashes"],
                "expected_package_kinds": [
                    "canonical_internal",
                    "user_facing",
                    "review_facing",
                ],
            },
        ),
    )
    assert review["review_state"] == "execution_result_review_approved"
    assert submit["package_review_state"] == "package_review_approved"
    assert handoff["handoff_export_state"] == "handoff_export_prepared"
    package_ids = tuple(package_commit["output_package_ids"])
    rows = tuple(
        db.scalars(
            select(L3OutputPackage).where(
                L3OutputPackage.output_package_id.in_(package_ids)
            )
        ).all()
    )
    assert len(rows) == 3
    return {
        "review": review,
        "package_preview": package_preview,
        "package_commit": package_commit,
        "submit": submit,
        "handoff": handoff,
    }


def _public_finish_selected_pass(
    db: Session,
    *,
    flow: Mapping[str, str],
    action_prefix: str,
    receipts: list[dict[str, str]],
) -> dict[str, Any]:
    common = {
        "session_id": flow["session_id"],
        "analysis_plan_id": flow["analysis_plan_id"],
        "pass_run_id": flow["pass_run_id"],
        "preview_id": flow["preview_id"],
        "preview_hash": flow["preview_hash"],
    }
    start = _record_downstream_action(
        receipts,
        action=f"{action_prefix}_analysis_execution_start",
        result=layer3_workbench.analysis_execution_start(
            db,
            {
                "client_request_id": f"{flow['session_id']}-start",
                **common,
            },
        ),
    )
    result = _public_finish_reviewable_pass(
        db,
        flow=flow,
        analysis_run_id=start.get("analysis_run_id"),
        action_prefix=action_prefix,
        receipts=receipts,
    )
    result["start"] = start
    return result


def _public_nrc_downstream(
    db: Session,
    *,
    target: ConnectorRunTarget,
    completed_at: datetime,
    receipts: list[dict[str, str]],
) -> tuple[L3Session, dict[str, Any]]:
    del completed_at
    linkage = db.scalar(
        select(ApsContentLinkage).where(
            ApsContentLinkage.target_id == target.connector_run_target_id
        )
    )
    assert linkage is not None
    preflight = _record_downstream_action(
        receipts,
        action="nrc_preflight",
        result=layer3_workbench.preflight(
            {
                "client_request_id": "l3-nrc-acceptance-preflight",
                "natural_language_intent": (
                    "Review the freshly acquired NRC APS document."
                ),
                "manual_constraints": {
                    "source_classes": ["aps_content_document"]
                },
            }
        ),
    )
    source = _record_downstream_action(
        receipts,
        action="nrc_source_preview",
        result=layer3_workbench.source_preview(
            {
                "client_request_id": "l3-nrc-acceptance-source",
                "preflight_id": preflight["preflight_id"],
                "selected_source_classes": ["aps_content_document"],
            }
        ),
    )
    source_candidate = next(
        candidate
        for candidate in source["source_candidates"]
        if candidate["source_class"] == "aps_content_document"
    )
    material = _record_downstream_action(
        receipts,
        action="nrc_material_preview",
        result=layer3_workbench.material_preview(
            {
                "client_request_id": "l3-nrc-acceptance-material",
                "preflight_id": preflight["preflight_id"],
                "source_set_id": source["source_set_id"],
                "source_candidate_ids": [
                    source_candidate["source_candidate_id"]
                ],
                "aps_content_document_ids": [linkage.content_id],
                "query_basis": {"terms": ["dual-live-proof"]},
            },
            db,
        ),
    )
    candidate = material["material_candidates"][0]
    gate_b = _record_downstream_action(
        receipts,
        action="nrc_gate_b_decision",
        result=layer3_workbench.gate_b_decision(
            db,
            {
                "client_request_id": "l3-nrc-acceptance-gate-b",
                "preflight_id": preflight["preflight_id"],
                "source_set_id": source["source_set_id"],
                "material_preview_id": material["material_preview_id"],
                "candidate_decisions": [
                    {
                        "candidate_id": candidate["candidate_id"],
                        "decision": "approved",
                        "operator_reason": "",
                        "decision_basis": {
                            key: copy.deepcopy(candidate[key])
                            for key in (
                                "source_ref",
                                "query_basis",
                                "provenance_ref",
                                "source_identity",
                                "source_provenance",
                                "payload",
                                "load_summary",
                            )
                        },
                    }
                ],
                "commit_reason": "dual_live_acceptance_nrc",
                "actor": "pytest",
            },
        ),
    )
    session = db.get(L3Session, gate_b["session_id"])
    assert session is not None
    _record_downstream_action(
        receipts,
        action="nrc_gate_c_typing",
        result=layer3_workbench.gate_c_preview(
            db,
            {
                "client_request_id": "l3-nrc-acceptance-gate-c",
                "session_id": session.session_id,
                "commit_typing": True,
            },
        ),
    )
    preview = _record_downstream_action(
        receipts,
        action="nrc_plan_preview",
        result=layer3_workbench.plan_preview(
            db,
            {
                "client_request_id": "l3-nrc-acceptance-plan-preview",
                "session_id": session.session_id,
            },
        ),
    )
    approval = _record_downstream_action(
        receipts,
        action="nrc_plan_approval",
        result=layer3_workbench.plan_approval(
            db,
            {
                "client_request_id": "l3-nrc-acceptance-plan-approval",
                "session_id": session.session_id,
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "operator_confirmation": True,
            },
        ),
    )
    selection = _record_downstream_action(
        receipts,
        action="nrc_execution_selection",
        result=layer3_workbench.execution_selection(
            db,
            {
                "client_request_id": "l3-nrc-acceptance-selection",
                "session_id": session.session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
            },
        ),
    )
    pass_run_id = selection["pass_run_ids"][0]
    finish = _public_finish_selected_pass(
        db,
        flow={
            "session_id": session.session_id,
            "analysis_plan_id": approval["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
        action_prefix="nrc",
        receipts=receipts,
    )
    refreshed = db.get(L3Session, session.session_id)
    assert refreshed is not None
    receipt = target.source_reference_json[
        layer3_origin_continuity.ORIGIN_RECEIPT_STORAGE_KEY
    ]
    package_commit = finish["package_commit"]
    handoff = finish["handoff"]
    return refreshed, {
        "analysis_plan_id": approval["analysis_plan_id"],
        "analysis_run_id": finish["start"].get("analysis_run_id"),
        "candidate_id": candidate["candidate_id"],
        "connector_key": "nrc_adams_aps",
        "connector_origin_receipt_hash": receipt["receipt_hash"],
        "connector_run_id": target.connector_run_id,
        "connector_run_target_id": target.connector_run_target_id,
        "construction_basis_hash": package_commit["construction_basis_hash"],
        "handoff_export_envelope_ref": handoff[
            "handoff_export_envelope_ref"
        ],
        "output_package_ids": package_commit["output_package_ids"],
        "package_kinds": package_commit["package_kinds"],
        "package_review_preview_hash": finish["package_preview"][
            "package_review_preview_hash"
        ],
        "package_review_submit_record_ref": finish["submit"][
            "submit_record_ref"
        ],
        "pass_run_id": pass_run_id,
        "payload_hashes": package_commit["payload_hashes"],
        "prepare_record_ref": handoff["prepare_record_ref"],
        "reconciliation_record_id": package_commit["reconciliation_record_id"],
        "result_review_record_ref": finish["review"]["review_record_ref"],
        "session_id": refreshed.session_id,
        "source_shape": handoff["source_shape"],
        "source_record_id": linkage.content_id,
    }


def _build_downstream(
    db: Session,
    *,
    targets: Mapping[str, ConnectorRunTarget],
    completed_at: datetime,
    receipts: list[dict[str, str]],
) -> tuple[dict[str, L3Session], tuple[dict[str, Any], ...]]:
    nrc_session, nrc_binding = _public_nrc_downstream(
        db,
        target=targets["nrc_adams_aps"],
        completed_at=completed_at,
        receipts=receipts,
    )
    sciencebase_session, sciencebase_binding = _public_sciencebase_downstream(
        db,
        target=targets["sciencebase_mcs"],
        receipts=receipts,
    )
    return (
        {
            "nrc_adams_aps": nrc_session,
            "sciencebase_mcs": sciencebase_session,
        },
        (nrc_binding, sciencebase_binding),
    )


class _ControllerReader:
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


def _controller_child(
    phase: str,
    *,
    proof_projection: Mapping[str, Any],
) -> dual_live_runtime._ControllerChild:
    process_boot_id = COUNTER_BOOT_ID if phase == "A" else "c" * 64
    status_nonce_sha256 = ("d" if phase == "A" else "e") * 64
    control_nonce = ("f" if phase == "A" else "1") * 64
    readers = {stream: _ControllerReader() for stream in PIPE_STREAM_CLASSES}
    boot_payload = canonical_json_bytes(
        {
            "control_nonce": control_nonce,
            "phase": phase,
            "process_boot_id": process_boot_id,
            "schema_id": dual_live_runtime.CHILD_BOOT_SCHEMA_ID,
            "status_nonce_sha256": status_nonce_sha256,
        }
    )
    boot_frame = encode_pipe_frame(boot_payload)
    pre_status_frame = encode_child_status_frame(
        phase=phase,
        event="logger_census",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce_sha256,
        ordinal=1,
        payload={
            "census_point": "pre_activity",
            "handler_count": 1,
            "topology_sha256": "2" * 64,
        },
    )
    readers["app"].feed(boot_frame)
    readers["app"].feed(pre_status_frame)
    proof_common = {
        "boot_frame_sha256": _sha256(boot_frame),
        "control_nonce_sha256": _sha256(control_nonce.encode("ascii")),
        "pre_activity_status_frame_sha256": _sha256(pre_status_frame),
        "proof_scope": "production",
    }
    previous_proof_sha256: str | None = None
    if phase == "B":
        preproof = dual_live_runtime.encode_child_proof_frame(
            phase="B",
            event="guard",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce_sha256,
            ordinal=1,
            previous_record_sha256=None,
            payload={
                **proof_common,
                "denied_routes": [
                    "dns",
                    "http",
                    "socket",
                    "subprocess",
                    "connector_transport",
                ],
                "network_enable_attempt_count": 0,
                "original_implementation_call_count": 0,
                "proof_point": "pre_go",
            },
        )
        previous_proof_sha256 = str(
            json.loads(preproof[4:].decode("utf-8"))["record_sha256"]
        )
        readers["stdout"].feed(preproof)

    def send_control(frame: bytes) -> None:
        assert frame == encode_child_control_frame(
            phase=phase,
            command="GO",
            control_nonce=control_nonce,
        )
        readers["app"].feed(
            encode_pipe_frame(
                canonical_json_bytes(
                    {
                        "schema_id": "project6.acceptance_fixture_activity.v1",
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
                "topology_sha256": "2" * 64,
            },
        )
        readers["app"].feed(exit_status_frame)
        terminal_common = {
            **proof_common,
            "control_frame_sha256": _sha256(frame),
            "exit_status_frame_sha256": _sha256(exit_status_frame),
        }
        if phase == "A":
            readers["stdout"].feed(
                dual_live_runtime.encode_child_proof_frame(
                    phase="A",
                    event="acquisition_boundary",
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=1,
                    previous_record_sha256=None,
                    payload={
                        **terminal_common,
                        "connector_acquisitions": proof_projection[
                            "connector_acquisitions"
                        ],
                        "downstream_action_count": 0,
                    },
                )
            )
        else:
            assert previous_proof_sha256 is not None
            downstream = dual_live_runtime.encode_child_proof_frame(
                phase="B",
                event="downstream_chain",
                process_boot_id=process_boot_id,
                status_nonce_sha256=status_nonce_sha256,
                ordinal=2,
                previous_record_sha256=previous_proof_sha256,
                payload={
                    **terminal_common,
                    "action_receipts": proof_projection["action_receipts"],
                    "downstream_actions": list(
                        dual_live_runtime._PHASE_B_DOWNSTREAM_ACTIONS
                    ),
                    "source_bindings": proof_projection["source_bindings"],
                    "terminal_boundary": "handoff_prepared",
                },
            )
            downstream_sha256 = str(
                json.loads(downstream[4:].decode("utf-8"))["record_sha256"]
            )
            readers["stdout"].feed(downstream)
            readers["stdout"].feed(
                dual_live_runtime.encode_child_proof_frame(
                    phase="B",
                    event="guard",
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=3,
                    previous_record_sha256=downstream_sha256,
                    payload={
                        **terminal_common,
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

    return dual_live_runtime._ControllerChild(
        process_boot_id=process_boot_id,
        process_creation_identity_sha256="3" * 64,
        executable_sha256="4" * 64,
        job_policy_sha256="5" * 64,
        status_nonce_sha256=status_nonce_sha256,
        control_nonce=control_nonce,
        readers=cast(Mapping[str, BinaryIO], readers),
        send_control=send_control,
        wait=lambda _timeout: 0,
        stop=lambda: None,
    )


def _run_runtime_and_seal(
    db: Session,
    *,
    capture: Any,
    runtime_instance_id: str,
    started_at: datetime,
    proof_projection: Mapping[str, Any],
) -> Any:
    identity = RuntimeIdentity(
        runtime_instance_id=runtime_instance_id,
        wrapper_nonce_sha256="6" * 64,
        code_revision=CODE_REVISION,
        wrapper_image_sha256="7" * 64,
        interpreter_image_sha256="8" * 64,
        dependency_set_sha256="0" * 64,
        root_mutex_identity_sha256="9" * 64,
        campaign_mutex_identity_sha256="a" * 64,
    )

    def quiesce(
        _phase: str,
        _child: object,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        zero_states = {state: 0 for state in WINDOWS_MIB_TCP_STATES}
        return (
            {
                "tcp4_state_counts": zero_states,
                "tcp6_state_counts": dict(zero_states),
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "b" * 64,
                "stable": True,
            },
            {"active_process_count": 0, "process_list_sha256": "c" * 64},
        )

    def clear_authority(
        _phase: str,
        _child: object,
    ) -> dict[str, Any]:
        return {
            "authority_posture_sha256": (
                "59629217f25b985366b9b16a9f6bd7b9a45d5544375dc04f847f1b7bc1e07cd2"
            ),
            "all_required_absent": True,
        }

    def seal() -> Any:
        runtime_stopped_at = datetime.now(UTC)
        chronology: list[tuple[str, str, str, str]] = []
        for run in db.scalars(select(ConnectorRun)).all():
            submitted = run.submitted_at
            completed = run.completed_at
            for event in db.scalars(
                select(ConnectorRunEvent).where(
                    ConnectorRunEvent.connector_run_id == run.connector_run_id
                )
            ).all():
                if (
                    submitted is None
                    or completed is None
                    or event.created_at is None
                    or not (submitted <= event.created_at <= completed)
                ):
                    chronology.append(
                        (
                            run.connector_key,
                            event.event_type,
                            str(event.created_at),
                            f"{submitted}..{completed}",
                        )
                    )
        assert chronology == []
        db.rollback()
        return seal_connector_campaign_log_capture(
            db,
            capture=capture,
            runtime_stopped_at=runtime_stopped_at,
            now=runtime_stopped_at,
        )

    return dual_live_runtime._run_two_phase_controller(
        identity=identity,
        runtime_start_payload={
            "code_revision": CODE_REVISION,
            "wrapper_image_sha256": identity.wrapper_image_sha256,
            "interpreter_image_sha256": identity.interpreter_image_sha256,
            "dependency_set_sha256": identity.dependency_set_sha256,
            "phase_timeout_contract": {
                "schema_id": "project6.dual_live_phase_timeout.v1",
                "phase_a_timeout_ms": 205_750,
                "phase_b_timeout_ms": 30_000,
                "fixed_non_egress_overhead_ms": 30_000,
                "counter_ack_timeout_ms": 5_000,
                "connector_grants": [
                    {
                        "connector_key": "nrc_adams_aps",
                        "max_physical_requests": 2,
                        "request_timeout_seconds": 30,
                        "min_request_interval_ms": 250,
                    },
                    {
                        "connector_key": "sciencebase_mcs",
                        "max_physical_requests": 3,
                        "request_timeout_seconds": 30,
                        "min_request_interval_ms": 250,
                    },
                ],
            },
            "mutex_identity_sha256": "e" * 64,
        },
        writers={writer.stream_class: writer for writer in capture.writers},
        create_phase_a=lambda: _controller_child(
            "A",
            proof_projection=proof_projection,
        ),
        create_phase_b=lambda: _controller_child(
            "B",
            proof_projection=proof_projection,
        ),
        quiesce_phase=quiesce,
        clear_authority=clear_authority,
        http_frame_validator=lambda _payload: None,
        seal=seal,
        timeout_seconds=2,
        _proof_scope="production",
    )


def _file_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _row_snapshot(engine: Any) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    rows: list[tuple[str, tuple[Any, ...]]] = []
    with engine.connect() as connection:
        for table in sorted(Base.metadata.sorted_tables, key=lambda item: item.name):
            result = connection.execute(select(table)).mappings()
            for row in result:
                normalized = tuple(
                    sorted(
                        (
                            key,
                            json.dumps(
                                value,
                                sort_keys=True,
                                separators=(",", ":"),
                                ensure_ascii=False,
                                default=str,
                            ),
                        )
                        for key, value in row.items()
                    )
                )
                rows.append((table.name, normalized))
    return tuple(sorted(rows))


def _build_real_constructor_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> _Campaign:
    started_at = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=2)
    with fitz.open(stream=NRC_BYTES, filetype="pdf") as document:
        assert document.page_count > 0
    storage = tmp_path / "storage"
    storage.mkdir()
    db_path = tmp_path / "campaign.db"
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
    authority = _build_authority(
        tmp_path,
        monkeypatch,
        db_path=db_path,
        storage=storage,
        started_at=started_at,
    )
    grants = _resolve_current_grants(authority, now=started_at)
    capture = begin_connector_campaign_log_capture(
        campaign_id=authority.campaign_id,
        expected_campaign_fingerprint=authority.campaign_fingerprint,
        expected_code_revision=CODE_REVISION,
        now=started_at,
    )
    runtime_instance_id = str(uuid4())
    targets, origin_projections, counter_records = _produce_real_runs(
        db,
        grants=grants,
        capture=capture,
        started_at=started_at,
        runtime_instance_id=runtime_instance_id,
        monkeypatch=monkeypatch,
    )
    nrc_linkage = db.scalar(
        select(ApsContentLinkage).where(
            ApsContentLinkage.target_id
            == targets["nrc_adams_aps"].connector_run_target_id
        )
    )
    assert nrc_linkage is not None
    action_receipts: list[dict[str, str]] = []
    _record_downstream_action(
        action_receipts,
        action="nrc_strict_parse",
        result={
            "connector_run_id": targets["nrc_adams_aps"].connector_run_id,
            "connector_run_target_id": (
                targets["nrc_adams_aps"].connector_run_target_id
            ),
            "content_id": nrc_linkage.content_id,
        },
    )
    for action, connector_key in (
        ("nrc_origin_receipt", "nrc_adams_aps"),
        ("sciencebase_origin_receipt", "sciencebase_mcs"),
    ):
        _record_downstream_action(
            action_receipts,
            action=action,
            result=origin_projections[connector_key],
        )
    _downstream_sessions, source_bindings = _build_downstream(
        db,
        targets=targets,
        completed_at=started_at + timedelta(seconds=10),
        receipts=action_receipts,
    )
    assert tuple(item["action"] for item in action_receipts) == (
        dual_live_runtime._PHASE_B_DOWNSTREAM_ACTIONS
    )
    ledgers = {
        connector_key: connector_egress_evidence.derive_terminal_request_ledger(
            db,
            connector_run_id=target.connector_run_id,
            counter_records=counter_records,
        )
        for connector_key, target in targets.items()
    }
    proof_projection = {
        "connector_acquisitions": [
            {
                "action_codes": [
                    "derived_arming",
                    "raw_acquisition",
                    "terminal_transition",
                ],
                "connector_key": connector_key,
                "connector_run_id": target.connector_run_id,
                "connector_run_target_id": target.connector_run_target_id,
                "ledger_terminal_hash": (
                    ledgers[connector_key].ledger_terminal_hash
                ),
                "raw_content_sha256": target.downloaded_sha256,
                "terminal_transition_count": 1,
            }
            for connector_key, target in targets.items()
        ],
        "action_receipts": action_receipts,
        "source_bindings": list(source_bindings),
    }
    db.rollback()
    _run_runtime_and_seal(
        db,
        capture=capture,
        runtime_instance_id=runtime_instance_id,
        started_at=started_at,
        proof_projection=proof_projection,
    )
    db.rollback()
    return _Campaign(
        db=db,
        engine=engine,
        settings=authority.proof_settings,
        campaign_id=authority.campaign_id,
        campaign_fingerprint=authority.campaign_fingerprint,
        code_revision=CODE_REVISION,
        evidence_root=authority.evidence_root,
        db_path=db_path,
    )


@pytest.fixture(scope="module")
def sealed_campaign_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> _CampaignTemplate:
    live_root = tmp_path_factory.mktemp("dual-live-live")
    backup_parent = tmp_path_factory.mktemp("dual-live-backup")
    backup_root = backup_parent / "root"
    local_monkeypatch = pytest.MonkeyPatch()
    campaign = _build_real_constructor_campaign(
        live_root,
        local_monkeypatch,
    )
    campaign.db.close()
    campaign.engine.dispose()
    snapshot = _file_snapshot(live_root)
    shutil.copytree(live_root, backup_root)
    assert _file_snapshot(backup_root) == snapshot
    local_monkeypatch.undo()
    return _CampaignTemplate(
        live_root=live_root,
        backup_root=backup_root,
        settings=campaign.settings,
        campaign_id=campaign.campaign_id,
        campaign_fingerprint=campaign.campaign_fingerprint,
        code_revision=campaign.code_revision,
        evidence_root=campaign.evidence_root,
        db_path=campaign.db_path,
        file_snapshot=snapshot,
    )


@pytest.fixture
def matrix_campaign(
    sealed_campaign_template: _CampaignTemplate,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    template = sealed_campaign_template
    backup_files = {
        path.relative_to(template.backup_root): path
        for path in template.backup_root.rglob("*")
        if path.is_file()
    }
    live_files = {
        path.relative_to(template.live_root): path
        for path in template.live_root.rglob("*")
        if path.is_file()
    }
    extras = sorted(set(live_files) - set(backup_files))
    if extras:
        archive_root = tmp_path / "archive" / uuid4().hex
        for relative_path in extras:
            destination = archive_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(live_files[relative_path], destination)
    for relative_path, source in backup_files.items():
        destination = template.live_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    assert _file_snapshot(template.live_root) == template.file_snapshot

    for field in (
        "database_url",
        "storage_dir",
        "connector_campaign_definition_path",
        "connector_campaign_definition_sha256",
        "connector_sciencebase_grant_path",
        "connector_sciencebase_grant_sha256",
        "connector_nrc_aps_grant_path",
        "connector_nrc_aps_grant_sha256",
        "connector_campaign_evidence_root",
        "connector_campaign_evidence_index_path",
        "connector_campaign_evidence_index_sha256",
        "connector_live_egress_enabled",
        "connector_live_egress_exclusive_proof_mode",
        "nrc_adams_subscription_key",
    ):
        _patch_setting(monkeypatch, field, getattr(template.settings, field))

    engine = create_engine(
        f"sqlite:///{template.db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    db = Session(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    campaign = _Campaign(
        db=db,
        engine=engine,
        settings=template.settings,
        campaign_id=template.campaign_id,
        campaign_fingerprint=template.campaign_fingerprint,
        code_revision=template.code_revision,
        evidence_root=template.evidence_root,
        db_path=template.db_path,
    )
    try:
        yield campaign
    finally:
        if db.in_transaction():
            db.rollback()
        db.close()
        engine.dispose()


def _capture_paths(campaign: _Campaign) -> tuple[Path, Path, Path]:
    log_root = campaign.evidence_root / "logs" / campaign.campaign_fingerprint
    return (
        log_root / "app.jsonl",
        log_root / "manifest.json",
        campaign.evidence_root / "log-seals" / f"{campaign.campaign_fingerprint}.json",
    )


def _rewrite_log_and_manifest(campaign: _Campaign) -> tuple[str, str]:
    _app_path, manifest_path, _ = _capture_paths(campaign)
    stream_path = manifest_path.parent / "stdout.log"
    original_stream = stream_path.read_bytes()
    assert original_stream
    rewritten_stream = bytearray(original_stream)
    rewritten_stream[0] ^= 0x01
    assert len(rewritten_stream) == len(original_stream)
    assert (
        sum(
            left != right
            for left, right in zip(original_stream, rewritten_stream, strict=True)
        )
        == 1
    )
    stream_path.write_bytes(rewritten_stream)
    manifest = json.loads(manifest_path.read_bytes())
    files = manifest["files"]
    stream_entries = [
        item for item in files if Path(item["relative_path"]).name == "stdout.log"
    ]
    assert len(stream_entries) == 1
    stream_entries[0]["byte_count"] = len(rewritten_stream)
    stream_entries[0]["sha256"] = _sha256(rewritten_stream)
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    file_set_hash = _sha256(
        canonical_json_bytes(
            {
                "schema_id": "project6.connector_campaign_log_file_set.v1",
                "files": files,
            }
        )
    )
    return _sha256(manifest_bytes), file_set_hash


def _rewrite_seal_to_match_manifest(
    campaign: _Campaign,
    *,
    manifest_sha256: str,
    file_set_hash: str,
) -> None:
    _, _, seal_path = _capture_paths(campaign)
    seal = json.loads(seal_path.read_bytes())
    seal["manifest_sha256"] = manifest_sha256
    seal["file_set_hash"] = file_set_hash
    seal_path.write_bytes(canonical_json_bytes(seal))


def _evaluate_preserving_protected_state(campaign: _Campaign) -> dict[str, Any]:
    campaign.db.rollback()
    db_bytes_before = campaign.db_path.read_bytes()
    rows_before = _row_snapshot(campaign.engine)
    files_before = _file_snapshot(campaign.db_path.parent)
    report = _query_only_report(campaign)
    campaign.db.rollback()
    assert campaign.db_path.read_bytes() == db_bytes_before
    assert _row_snapshot(campaign.engine) == rows_before
    assert _file_snapshot(campaign.db_path.parent) == files_before
    return report


def _open_query_only_session(
    campaign: _Campaign,
) -> tuple[Any, Any, Session]:
    database_uri = f"file:{campaign.db_path.as_posix()}?mode=ro&cache=private"

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(
            database_uri,
            uri=True,
            check_same_thread=False,
        )
        connection.execute("PRAGMA query_only=ON")
        assert connection.execute("PRAGMA query_only").fetchone() == (1,)
        return connection

    engine = create_engine(
        f"sqlite+pysqlite:///{campaign.db_path.as_posix()}",
        creator=connect,
        future=True,
        poolclass=NullPool,
    )
    connection = engine.connect()
    assert connection.exec_driver_sql("PRAGMA query_only").scalar_one() == 1
    connection.rollback()
    assert not connection.in_transaction()
    db = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    return engine, connection, db


def _query_only_report(campaign: _Campaign) -> dict[str, Any]:
    engine, connection, db = _open_query_only_session(campaign)
    try:
        return dual_live_evaluator.evaluate_dual_live_proof(
            db,
            campaign_id=str(campaign.campaign_id),
            expected_campaign_fingerprint=campaign.campaign_fingerprint,
            settings=campaign.settings,
        )
    finally:
        if db.in_transaction():
            db.rollback()
        db.close()
        connection.close()
        engine.dispose()


def _query_only_context(campaign: _Campaign) -> Any:
    engine, connection, db = _open_query_only_session(campaign)
    try:
        context = dual_live_evaluator._collect_evidence(
            db,
            campaign_id=str(campaign.campaign_id),
            campaign_fingerprint=campaign.campaign_fingerprint,
            settings=campaign.settings,
        )
        assert dict(context.domain_errors) == {}
        db.expunge_all()
        if db.in_transaction():
            db.rollback()
        return replace(context, db=campaign.db)
    finally:
        if db.in_transaction():
            db.rollback()
        db.close()
        connection.close()
        engine.dispose()


def _assert_named_nonpass(report: Mapping[str, Any], check_id: str) -> None:
    assert report["status"] != "PASS", report
    assert report["fresh_live"] is False
    assert [item["check_id"] for item in report["checks"]] == list(
        dual_live_evaluator.EVALUATOR_CHECK_ORDER
    )
    assert len(report["checks"]) == 69
    matches = [item for item in report["checks"] if item["check_id"] == check_id]
    assert len(matches) == 1
    assert matches[0]["status"] != "PASS", matches[0]


def _report_check(
    report: Mapping[str, Any],
    check_id: str,
) -> Mapping[str, Any]:
    matches = [item for item in report["checks"] if item["check_id"] == check_id]
    assert len(matches) == 1
    return matches[0]


def _raise_internal_evaluation_cause(campaign: _Campaign) -> None:
    engine, connection, db = _open_query_only_session(campaign)
    try:
        context = dual_live_evaluator._collect_evidence(
            db,
            campaign_id=str(campaign.campaign_id),
            campaign_fingerprint=campaign.campaign_fingerprint,
            settings=campaign.settings,
        )
        for check_id, check in zip(
            dual_live_evaluator.EVALUATOR_CHECK_ORDER,
            dual_live_evaluator.CHECKS,
            strict=True,
        ):
            try:
                check(context)
            except BaseException as exc:
                raise AssertionError(
                    f"internal evaluator cause at {check_id}: {type(exc).__name__}"
                ) from exc
        raise AssertionError("internal evaluator cause occurred outside named checks")
    finally:
        if db.in_transaction():
            db.rollback()
        db.close()
        connection.close()
        engine.dispose()


def _map_entry(
    mapping: Mapping[str, Any],
    key: str,
    value: Any,
) -> dict[str, Any]:
    updated = dict(mapping)
    updated[key] = value
    return updated


def _model_update(model: Any, **updates: Any) -> Any:
    return model.model_copy(update=updates)


def _row_shadow(row: Any, **updates: Any) -> SimpleNamespace:
    values = {column.key: getattr(row, column.key) for column in row.__table__.columns}
    values.update(updates)
    return SimpleNamespace(**values)


def _runtime_update(
    context: Any,
    *,
    phase: str,
    event: str,
    occurrence: int = 0,
    record_updates: Mapping[str, Any] | None = None,
    payload_updates: Mapping[str, Any] | None = None,
) -> Any:
    records = [
        copy.deepcopy(dual_live_evaluator._thaw(record))
        for record in context.runtime_records
    ]
    matches = [
        index
        for index, record in enumerate(records)
        if record.get("phase") == phase and record.get("event") == event
    ]
    assert matches
    index = matches[occurrence]
    records[index].update(record_updates or {})
    if payload_updates:
        payload = dict(records[index].get("payload") or {})
        payload.update(payload_updates)
        records[index]["payload"] = payload
    return replace(context, runtime_records=tuple(records))


def _ledger_entry_update(
    context: Any,
    *,
    connector_key: str = "nrc_adams_aps",
    entry_index: int = 0,
    **updates: Any,
) -> Any:
    ledger = context.ledgers[connector_key]
    entries = [copy.deepcopy(entry) for entry in ledger.entries]
    entries[entry_index].update(updates)
    changed = replace(ledger, entries=tuple(entries))
    return replace(
        context,
        ledgers=_map_entry(context.ledgers, connector_key, changed),
    )


def _origin_update(
    context: Any,
    connector_key: str,
    **updates: Any,
) -> Any:
    receipt = dict(context.origins[connector_key])
    receipt.update(updates)
    return replace(
        context,
        origins=_map_entry(context.origins, connector_key, receipt),
    )


def _mutate_authority(context: Any, check_id: str) -> Any:
    if check_id == "A01_INPUT_IDENTITY":
        return replace(context, campaign_id="not-a-canonical-uuid")
    if check_id == "A02_INDEX_LINEAR_HEAD":
        head = _model_update(context.chain.head, revision=2)
        return replace(context, chain=replace(context.chain, head=head))
    if check_id == "A03_ARCHIVE_EXACT":
        key = "nrc_adams_aps"
        evidence = replace(context.historical[key], raw_sha256="0" * 64)
        return replace(
            context,
            historical=_map_entry(context.historical, key, evidence),
        )
    if check_id == "A04_SLICE_CARDINALITY":
        return replace(context, entry_refs=context.entry_refs[:1])
    if check_id == "A05_SELECTED_UNION":
        revision = context.chain.revisions[0]
        model = _model_update(revision.model, entries=revision.model.entries[:1])
        changed = replace(revision, model=model)
        return replace(
            context,
            chain=replace(context.chain, revisions=(changed,)),
        )
    if check_id == "A06_INTRODUCTION_PARITY":
        seal = _model_update(
            context.seal,
            campaign_introduction_index_revision=(
                context.seal.campaign_introduction_index_revision + 1
            ),
        )
        return replace(context, seal=seal)
    if check_id == "A07_MARKER_ONE_USE":
        key = "nrc_adams_aps"
        evidence = context.historical[key]
        marker = _model_update(evidence.marker_model, max_armings=2)
        return replace(
            context,
            historical=_map_entry(
                context.historical,
                key,
                replace(evidence, marker_model=marker),
            ),
        )
    if check_id == "A08_ORIGINAL_WINDOWS":
        campaign = next(iter(context.historical.values())).definition_model
        return _ledger_entry_update(
            context,
            reserved_at=(campaign.not_before - timedelta(seconds=1)).isoformat(),
        )
    if check_id == "A09_CODE_CAMPAIGN_FINGERPRINTS":
        return replace(
            context,
            manifest=_model_update(
                context.manifest,
                campaign_fingerprint="0" * 64,
            ),
        )
    if check_id == "A10_PROOF_CLASS":
        return _origin_update(context, "nrc_adams_aps", proof_class="fixture")
    raise AssertionError(f"unmapped authority check: {check_id}")


def _mutate_runtime_domain(
    context: Any,
    campaign: _Campaign,
    check_id: str,
) -> tuple[Any, Callable[[], None]]:
    if check_id == "R01_CAPTURE_MEMBERSHIP":
        changed = replace(
            context.capture,
            stable_snapshot=context.capture.stable_snapshot[:-1],
        )
        return replace(context, capture=changed), lambda: None
    if check_id == "R02_MANIFEST_FILE_HASHES":
        files = list(context.manifest.files)
        files[0] = _model_update(files[0], sha256="0" * 64)
        manifest = _model_update(context.manifest, files=tuple(files))
        return replace(context, manifest=manifest), lambda: None
    if check_id == "R03_SEAL_PARITY":
        capture = replace(context.capture, manifest_sha256="0" * 64)
        return replace(context, capture=capture), lambda: None
    if check_id == "R04_SEAL_EVENT_PARITY":
        event_id = context.capture.seal_event_ids[0]
        capture = replace(context.capture, seal_event_ids=(event_id, event_id))
        return replace(context, capture=capture), lambda: None
    if check_id == "R05_RUNTIME_CHAIN":
        records = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in context.runtime_records
        ]
        records[0]["ordinal"] = 2
        return replace(context, runtime_records=tuple(records)), lambda: None
    if check_id == "R06_STARTUP_LOGGER_CENSUS":
        return (
            _runtime_update(
                context,
                phase="A",
                event="logger_census",
                payload_updates={"topology_matches_initial": False},
            ),
            lambda: None,
        )
    if check_id == "R07_EXIT_LOGGER_CENSUS":
        changed = _runtime_update(
            context,
            phase="A",
            event="logger_census",
            occurrence=-1,
            payload_updates={"topology_sha256": "0" * 64},
        )
        exit_census = next(
            record
            for record in reversed(changed.runtime_records)
            if record.get("phase") == "A"
            and record.get("event") == "logger_census"
        )
        child_proofs = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in changed.child_proofs
        ]
        phase_a_proof = child_proofs[0]
        phase_a_proof["payload"]["exit_status_frame_sha256"] = (
            dual_live_evaluator._status_frame_sha256_from_runtime(
                phase="A",
                process_boot_id=phase_a_proof["process_boot_id"],
                status_nonce_sha256=phase_a_proof["status_nonce_sha256"],
                ordinal=2,
                runtime_record=exit_census,
            )
        )
        return replace(changed, child_proofs=tuple(child_proofs)), lambda: None
    if check_id == "R08_PHASE_A_IDENTITY":
        return (
            _runtime_update(
                context,
                phase="A",
                event="phase_child_start",
                record_updates={"process_boot_id": None},
            ),
            lambda: None,
        )
    if check_id == "R09_PHASE_A_JOB_ZERO":
        return (
            _runtime_update(
                context,
                phase="A",
                event="job_zero",
                payload_updates={"active_process_count": 1},
            ),
            lambda: None,
        )
    if check_id == "R10_PHASE_A_SOCKET_QUIESCENCE":
        return (
            _runtime_update(
                context,
                phase="A",
                event="socket_census",
                payload_updates={"udp4_count": 1},
            ),
            lambda: None,
        )
    if check_id == "R11_AUTHORITY_CLEARED":
        return (
            _runtime_update(
                context,
                phase="A",
                event="authority_cleared",
                payload_updates={"all_required_absent": False},
            ),
            lambda: None,
        )
    if check_id == "R12_PHASE_B_GUARDS":
        return (
            _runtime_update(
                context,
                phase="B",
                event="logger_census",
                payload_updates={"guard_state": "NOT_GUARDED"},
            ),
            lambda: None,
        )
    if check_id == "R13_PHASE_B_JOB_ZERO":
        return (
            _runtime_update(
                context,
                phase="B",
                event="job_zero",
                payload_updates={"active_process_count": 1},
            ),
            lambda: None,
        )
    if check_id == "R14_RUNTIME_TERMINAL":
        return (
            _runtime_update(
                context,
                phase="wrapper",
                event="runtime_complete",
                payload_updates={"terminal_state": "failed"},
            ),
            lambda: None,
        )
    if check_id == "R15_WRAPPER_NETWORK_INERT":
        return (
            _runtime_update(
                context,
                phase="wrapper",
                event="runtime_start",
                record_updates={"event": "network_send"},
            ),
            lambda: None,
        )
    if check_id == "R16_PHASE_A_RAW_ONLY":
        child_proofs = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in context.child_proofs
        ]
        child_proofs[0]["payload"]["downstream_action_count"] = 1
        return replace(context, child_proofs=tuple(child_proofs)), lambda: None
    if check_id == "R17_PHASE_B_STRICT_FLOW":
        states = dict(context.review_states)
        states.pop("nrc_adams_aps")
        return replace(context, review_states=states), lambda: None
    if check_id == "R18_PHASE_A_TERMINAL_ONCE":
        ledger = replace(context.ledgers["nrc_adams_aps"], eligible=False)
        return (
            replace(
                context,
                ledgers=_map_entry(context.ledgers, "nrc_adams_aps", ledger),
            ),
            lambda: None,
        )
    if check_id == "R19_A_TO_B_ORDER":
        return (
            _runtime_update(
                context,
                phase="B",
                event="phase_child_start",
                record_updates={"ordinal": 1},
            ),
            lambda: None,
        )
    if check_id == "R20_FOUR_STREAM_CLOSEOUT":
        manifest = _model_update(
            context.manifest,
            runtime_stopped_at=(
                context.manifest.runtime_started_at - timedelta(seconds=1)
            ),
        )
        return replace(context, manifest=manifest), lambda: None
    if check_id == "R21_EXTANT_RUN_SEAL_EVENTS":
        campaign.db.rollback()
        event = campaign.db.scalar(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_event_id
                == context.capture.seal_event_ids[0]
            )
        )
        assert event is not None
        original = event.reason_code
        event.reason_code = "forged_seal_reason"
        campaign.db.commit()

        def restore_event() -> None:
            row = campaign.db.get(
                ConnectorRunEvent,
                context.capture.seal_event_ids[0],
            )
            assert row is not None
            row.reason_code = original
            campaign.db.commit()

        return replace(context, db=campaign.db), restore_event
    if check_id == "R22_CAPTURE_START_CONTRACT":
        capture_ref = _model_update(
            context.capture_ref,
            expected_stream_files=context.capture_ref.expected_stream_files[:-1],
        )
        return replace(context, capture_ref=capture_ref), lambda: None
    raise AssertionError(f"unmapped runtime check: {check_id}")


def _mutate_ledger_domain(
    context: Any,
    campaign: _Campaign,
    check_id: str,
) -> tuple[Any, Callable[[], None]]:
    if check_id == "L01_RUN_CARDINALITY":
        run = _row_shadow(context.runs[0], source_mode="fixture")
        return replace(context, runs=(run, *context.runs[1:])), lambda: None
    if check_id == "L02_TERMINAL_EVENT":
        run = _row_shadow(context.runs[0], status="failed")
        return replace(context, runs=(run, *context.runs[1:])), lambda: None
    if check_id == "L03_POST_TERMINAL_EXTINCTION":
        campaign.db.rollback()
        event = campaign.db.scalar(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_event_id
                == context.capture.seal_event_ids[0]
            )
        )
        assert event is not None
        original = event.event_type
        event.event_type = "lease_reacquired"
        campaign.db.commit()

        def restore_event() -> None:
            row = campaign.db.get(
                ConnectorRunEvent,
                context.capture.seal_event_ids[0],
            )
            assert row is not None
            row.event_type = original
            campaign.db.commit()

        return replace(context, db=campaign.db), restore_event
    if check_id == "L04_LEDGER_RECONSTRUCTION":
        ledger = replace(context.ledgers["nrc_adams_aps"], eligible=False)
        return (
            replace(
                context,
                ledgers=_map_entry(context.ledgers, "nrc_adams_aps", ledger),
            ),
            lambda: None,
        )
    if check_id == "L05_COUNTER_BIJECTION":
        records = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in context.counter_records
        ]
        records[0]["request_fingerprint"] = "0" * 64
        return replace(context, counter_records=tuple(records)), lambda: None
    if check_id == "L06_COUNTER_BOOT":
        records = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in context.counter_records
        ]
        records[0]["process_boot_id"] = "0" * 64
        return replace(context, counter_records=tuple(records)), lambda: None
    if check_id == "L07_BYTE_ALLOWANCE":
        records = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in context.counter_records
        ]
        records[0]["canonical_status_header_bytes"] = 100 * 1024 * 1024
        return replace(context, counter_records=tuple(records)), lambda: None
    if check_id == "L08_REQUEST_CADENCE":
        records = [
            copy.deepcopy(dual_live_evaluator._thaw(record))
            for record in context.counter_records
        ]
        for record in records:
            record["monotonic_started_at"] = 1.0
        return replace(context, counter_records=tuple(records)), lambda: None
    if check_id == "L09_TRANSPORT_POLICY":
        return _ledger_entry_update(context, method="POST"), lambda: None
    if check_id == "L10_FRESH_200_BYTES":
        receipt = context.origins["nrc_adams_aps"]
        return (
            _origin_update(
                context,
                "nrc_adams_aps",
                raw_content_size_bytes=int(receipt["raw_content_size_bytes"]) + 1,
            ),
            lambda: None,
        )
    if check_id == "L11_NRC_FIRST_BINDING":
        envelope = dict(context.envelopes["sciencebase_mcs"])
        envelope["predecessor_nrc_ledger_terminal_hash"] = "0" * 64
        return (
            replace(
                context,
                envelopes=_map_entry(
                    context.envelopes,
                    "sciencebase_mcs",
                    envelope,
                ),
            ),
            lambda: None,
        )
    if check_id == "L12_RESERVATION_RESOLUTION":
        return _ledger_entry_update(context, completion_event_id=None), lambda: None
    raise AssertionError(f"unmapped ledger check: {check_id}")


def _package_payload_update(
    context: Any,
    *,
    connector_key: str = "nrc_adams_aps",
    payload_index: int = 0,
    top_level: Mapping[str, Any] | None = None,
    origin_updates: Mapping[str, Any] | None = None,
) -> Any:
    payloads = [
        copy.deepcopy(dual_live_evaluator._thaw(payload))
        for payload in context.package_payloads[connector_key]
    ]
    payloads[payload_index].update(top_level or {})
    if origin_updates:
        origin = dict(payloads[payload_index]["connector_origin_integrity_v1"])
        origin.update(origin_updates)
        payloads[payload_index]["connector_origin_integrity_v1"] = origin
    return replace(
        context,
        package_payloads=_map_entry(
            context.package_payloads,
            connector_key,
            tuple(payloads),
        ),
    )


def _boundary_update(
    context: Any,
    field_name: str,
    connector_key: str,
    **updates: Any,
) -> Any:
    mapping = getattr(context, field_name)
    state = copy.deepcopy(dual_live_evaluator._thaw(mapping[connector_key]))
    state.update(updates)
    return replace(
        context,
        **{field_name: _map_entry(mapping, connector_key, state)},
    )


def _mutate_downstream_domain(context: Any, check_id: str) -> Any:
    key = "nrc_adams_aps"
    if check_id == "D01_ORIGIN_RECEIPT":
        return _origin_update(context, key, schema_id="invalid.origin.v1")
    if check_id == "D02_RAW_PROVENANCE_LINKAGE":
        return _origin_update(context, key, source_artifact_key="forged")
    if check_id == "D03_LAYER3_EXECUTION":
        pass_run = _row_shadow(context.pass_runs[key], status="failed")
        return replace(
            context,
            pass_runs=_map_entry(context.pass_runs, key, pass_run),
        )
    if check_id == "D04_REVIEW_RESULT":
        return _boundary_update(
            context,
            "review_states",
            key,
            operator_decision="rejected",
        )
    if check_id == "D05_PACKAGE_SET":
        return _boundary_update(
            context,
            "package_commits",
            key,
            construction_basis_hash="0" * 64,
        )
    if check_id == "D06_PACKAGE_PAYLOAD":
        return _package_payload_update(
            context,
            connector_key=key,
            origin_updates={"proof_class": "fixture"},
        )
    if check_id == "D07_SUBMIT_RECEIPT":
        return _boundary_update(
            context,
            "submit_states",
            key,
            handoff_enabled=True,
        )
    if check_id == "D08_HANDOFF_RECEIPT":
        return _boundary_update(
            context,
            "handoff_states",
            key,
            external_handoff_enabled=True,
        )
    raise AssertionError(f"unmapped downstream check: {check_id}")


def _mutate_scan_domain(
    context: Any,
    campaign: _Campaign,
    check_id: str,
) -> tuple[Any, Callable[[], None]]:
    forbidden = NRC_DETAIL_URL.encode("utf-8")
    if check_id == "C01_STRICT_NULLS":
        campaign.db.rollback()
        target_id = context.targets["nrc_adams_aps"].connector_run_target_id
        target = campaign.db.get(ConnectorRunTarget, target_id)
        assert target is not None
        original = target.sciencebase_item_url
        target.sciencebase_item_url = "redacted://strict-null-negative"
        campaign.db.commit()

        def restore_target() -> None:
            row = campaign.db.get(ConnectorRunTarget, target_id)
            assert row is not None
            row.sciencebase_item_url = original
            campaign.db.commit()

        return (
            replace(
                context,
                db=campaign.db,
                targets=_map_entry(context.targets, "nrc_adams_aps", target),
            ),
            restore_target,
        )
    if check_id == "C02_DB_SCALAR_JSON_SCAN":
        return (
            replace(
                context,
                db_values=(*context.db_values, ("matrix:scalar", NRC_DETAIL_URL)),
            ),
            lambda: None,
        )
    if check_id == "C03_NON_SOURCE_FILE_SCAN":
        return (
            replace(
                context,
                non_source_files=(
                    *context.non_source_files,
                    ("matrix:file", forbidden),
                ),
            ),
            lambda: None,
        )
    if check_id == "C04_SERIALIZATION_EVENT_SCAN":
        return (
            _package_payload_update(
                context,
                top_level={"forbidden_locator": NRC_DETAIL_URL},
            ),
            lambda: None,
        )
    if check_id == "C05_RUNTIME_LOG_SCAN":
        streams = dict(context.capture.stream_bytes)
        app_path = next(path for path in streams if Path(str(path)).name == "app.jsonl")
        streams[app_path] = streams[app_path] + forbidden
        return (
            replace(context, capture=replace(context.capture, stream_bytes=streams)),
            lambda: None,
        )
    if check_id == "C06_BOUNDED_DECODERS":
        return (
            replace(
                context,
                db_values=(*context.db_values, ("matrix:decoder", "%FF")),
            ),
            lambda: None,
        )
    if check_id == "C07_SOURCE_EXEMPTION":
        key = "nrc_adams_aps"
        receipt = dict(context.origins[key])
        receipt["raw_content_sha256"] = "0" * 64
        origins = _map_entry(context.origins, key, receipt)
        exemptions = tuple(
            sorted(
                (
                    str(origins[current]["raw_storage_ref"]),
                    str(origins[current]["raw_content_sha256"]),
                )
                for current in ("nrc_adams_aps", "sciencebase_mcs")
            )
        )
        return (
            replace(context, origins=origins, source_exemptions=exemptions),
            lambda: None,
        )
    if check_id == "C08_SECRET_SCAN":
        secret = context.settings.nrc_adams_subscription_key.encode("utf-8")
        return (
            replace(
                context,
                non_source_files=(
                    *context.non_source_files,
                    ("matrix:secret", secret),
                ),
            ),
            lambda: None,
        )
    raise AssertionError(f"unmapped scan check: {check_id}")


def _mutate_final_domain(
    context: Any,
    campaign: _Campaign,
    monkeypatch: pytest.MonkeyPatch,
    check_id: str,
) -> tuple[Any, Callable[[], None]]:
    if check_id == "F01_EVIDENCE_STABILITY":
        return replace(context, final_snapshot_sha256="0" * 64), lambda: None
    if check_id == "F02_DATABASE_STABILITY":
        return (
            replace(context, final_database_snapshot_sha256="0" * 64),
            lambda: None,
        )
    if check_id == "F03_NONCLAIMS_REPORT":
        monkeypatch.setattr(
            dual_live_evaluator,
            "EVALUATOR_NONCLAIMS",
            dual_live_evaluator.EVALUATOR_NONCLAIMS[:-1],
        )
        return context, lambda: None
    if check_id == "F04_READ_ONLY_EVALUATION":
        campaign.db.rollback()
        run = campaign.db.get(
            ConnectorRun,
            context.runs[0].connector_run_id,
        )
        assert run is not None
        run.error_summary = "pending matrix mutation"
        assert run in campaign.db.dirty
        return replace(context, db=campaign.db), campaign.db.rollback
    if check_id == "F05_PROJECTION_REDERIVATION":
        return (
            _package_payload_update(
                context,
                origin_updates={"connector_origin_receipt_hash": "0" * 64},
            ),
            lambda: None,
        )
    if check_id == "F06_NO_EGRESS_DEPENDENCY":
        original_read = dual_live_evaluator._stable_bounded_read
        evaluator_path = Path(dual_live_evaluator.__file__).resolve()

        def source_read(path: Path, *args: Any, **kwargs: Any) -> bytes:
            if Path(path).resolve() == evaluator_path:
                return b"import socket\n"
            return original_read(path, *args, **kwargs)

        monkeypatch.setattr(
            dual_live_evaluator,
            "_stable_bounded_read",
            source_read,
        )
        return context, lambda: None
    if check_id == "F07_PUBLIC_API_CONTRACT":
        monkeypatch.setattr(
            dual_live_evaluator,
            "evaluate_dual_live_proof",
            lambda: {},
        )
        return context, lambda: None
    if check_id == "F08_RESULT_AGGREGATION":
        monkeypatch.setattr(
            dual_live_evaluator,
            "CHECKS",
            dual_live_evaluator.CHECKS[:-1],
        )
        return context, lambda: None
    if check_id == "F09_CONNECTOR_AND_COMBINED_REPORTS":
        payloads = dict(context.package_payloads)
        payloads.pop("nrc_adams_aps")
        return replace(context, package_payloads=payloads), lambda: None
    raise AssertionError(f"unmapped final check: {check_id}")


def _mutate_case(
    context: Any,
    campaign: _Campaign,
    monkeypatch: pytest.MonkeyPatch,
    case: _NegativeCase,
) -> tuple[Any, Callable[[], None]]:
    prefix = case.check_id[0]
    if prefix == "A":
        return _mutate_authority(context, case.check_id), lambda: None
    if prefix == "R":
        return _mutate_runtime_domain(context, campaign, case.check_id)
    if prefix == "L":
        return _mutate_ledger_domain(context, campaign, case.check_id)
    if prefix == "D":
        return _mutate_downstream_domain(context, case.check_id), lambda: None
    if prefix == "C":
        return _mutate_scan_domain(context, campaign, case.check_id)
    if prefix == "F":
        return _mutate_final_domain(
            context,
            campaign,
            monkeypatch,
            case.check_id,
        )
    raise AssertionError(f"unmapped check group: {case.check_id}")


def _patch_ledger_reader(
    monkeypatch: pytest.MonkeyPatch,
    context: Any,
    ledgers: Mapping[str, Any],
) -> None:
    connector_by_run_id = {
        run.connector_run_id: connector_key
        for connector_key, run in context.run_by_connector.items()
    }

    def derive(
        _db: Session,
        *,
        connector_run_id: str,
        counter_path: Path | None = None,
        counter_records: object = None,
    ) -> Any:
        del counter_path, counter_records
        return ledgers[connector_by_run_id[connector_run_id]]

    monkeypatch.setattr(
        connector_egress_evidence,
        "derive_terminal_request_ledger",
        derive,
    )


def _patch_origin_reader(
    monkeypatch: pytest.MonkeyPatch,
    context: Any,
    origins: Mapping[str, Mapping[str, Any]],
) -> None:
    def derive(
        *,
        settings: Settings,
        run: ConnectorRun,
        target: ConnectorRunTarget,
        ledger: object,
        historical: object,
        envelope: Mapping[str, Any],
    ) -> dict[str, Any]:
        del settings, target, ledger, historical, envelope
        return copy.deepcopy(
            dual_live_evaluator._thaw(
                origins[str(run.connector_key)]
            )
        )

    monkeypatch.setattr(
        dual_live_evaluator,
        "_derive_origin_receipt_read_only",
        derive,
    )


def _install_public_negative(
    campaign: _Campaign,
    context: Any,
    monkeypatch: pytest.MonkeyPatch,
    case: _NegativeCase,
) -> None:
    check_id = case.check_id
    if check_id == "A01_INPUT_IDENTITY":
        original = dual_live_evaluator._require_campaign_id
        calls = 0

        def validate(value: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                original(value)
                return
            original("not-a-canonical-uuid")

        monkeypatch.setattr(dual_live_evaluator, "_require_campaign_id", validate)
        return
    if check_id == "F04_READ_ONLY_EVALUATION":
        original = dual_live_evaluator._rows_for_selected_authority
        calls = 0

        def rows(db: Session, **kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            result = original(db, **kwargs)
            if calls == 1:
                db.add(
                    ConnectorRun(
                        connector_run_id=str(uuid4()),
                        connector_key="nrc_adams_aps",
                        source_system="nrc_adams",
                        source_mode="strict_live_egress",
                        status="queued",
                    )
                )
            return result

        monkeypatch.setattr(
            dual_live_evaluator,
            "_rows_for_selected_authority",
            rows,
        )
        return
    if check_id == "F07_PUBLIC_API_CONTRACT":
        original_signature = dual_live_evaluator.inspect.signature

        def signature(value: object, *args: Any, **kwargs: Any) -> Any:
            result = original_signature(value, *args, **kwargs)
            if value is dual_live_evaluator.evaluate_dual_live_proof:
                return result.replace(parameters=())
            return result

        monkeypatch.setattr(dual_live_evaluator.inspect, "signature", signature)
        return
    if check_id == "F08_RESULT_AGGREGATION":
        checks = list(dual_live_evaluator.CHECKS)
        original_check = checks[0]

        def misnamed_registry_entry(value: Any) -> Any:
            return original_check(value)

        checks[0] = misnamed_registry_entry
        monkeypatch.setattr(dual_live_evaluator, "CHECKS", tuple(checks))
        return

    mutated, _restore = _mutate_case(
        context,
        campaign,
        monkeypatch,
        case,
    )

    if check_id in {"L01_RUN_CARDINALITY", "L02_TERMINAL_EVENT"}:
        campaign.db.rollback()
        run = campaign.db.get(ConnectorRun, context.runs[0].connector_run_id)
        assert run is not None
        if check_id == "L01_RUN_CARDINALITY":
            run.source_mode = "fixture"
        else:
            run.status = "failed"
        campaign.db.commit()
        monkeypatch.setattr(
            connector_egress_evidence,
            "verify_connector_campaign_log_capture_read_only",
            lambda *_args, **_kwargs: context.capture,
        )
        _patch_ledger_reader(monkeypatch, context, context.ledgers)
        _patch_origin_reader(monkeypatch, context, context.origins)
        return

    if check_id in {"A02_INDEX_LINEAR_HEAD", "A05_SELECTED_UNION"}:
        monkeypatch.setattr(
            connector_egress_evidence,
            "load_evidence_index_chain_read_only",
            lambda _settings: mutated.chain,
        )
    elif check_id in {"A04_SLICE_CARDINALITY", "R22_CAPTURE_START_CONTRACT"}:
        monkeypatch.setattr(
            dual_live_evaluator,
            "_select_campaign_slice",
            lambda *_args, **_kwargs: (
                mutated.campaign_ref,
                mutated.entry_refs,
                mutated.capture_ref,
            ),
        )
        if check_id == "R22_CAPTURE_START_CONTRACT":
            monkeypatch.setattr(
                connector_egress_evidence,
                "verify_connector_campaign_log_capture_read_only",
                lambda *_args, **_kwargs: context.capture,
            )
    elif check_id in {"A03_ARCHIVE_EXACT", "A07_MARKER_ONE_USE"}:
        monkeypatch.setattr(
            connector_egress_evidence,
            "resolve_historical_connector_grant_evidence_read_only",
            lambda _settings, *, connector_key, **_kwargs: mutated.historical[
                connector_key
            ],
        )
    elif check_id in {
        "A06_INTRODUCTION_PARITY",
        "A09_CODE_CAMPAIGN_FINGERPRINTS",
        "R02_MANIFEST_FILE_HASHES",
        "R20_FOUR_STREAM_CLOSEOUT",
    }:
        monkeypatch.setattr(
            dual_live_evaluator,
            "_parse_capture_models",
            lambda _capture: (mutated.manifest, mutated.seal),
        )
    elif check_id in {"A08_ORIGINAL_WINDOWS", "R18_PHASE_A_TERMINAL_ONCE"}:
        _patch_ledger_reader(monkeypatch, context, mutated.ledgers)
        if check_id == "R18_PHASE_A_TERMINAL_ONCE":
            _patch_origin_reader(monkeypatch, context, context.origins)
    elif check_id in {
        "A10_PROOF_CLASS",
        "L10_FRESH_200_BYTES",
        "D01_ORIGIN_RECEIPT",
        "D02_RAW_PROVENANCE_LINKAGE",
        "C07_SOURCE_EXEMPTION",
    }:
        _patch_origin_reader(monkeypatch, context, mutated.origins)
    elif check_id in {
        "R01_CAPTURE_MEMBERSHIP",
        "R03_SEAL_PARITY",
        "R04_SEAL_EVENT_PARITY",
        "C05_RUNTIME_LOG_SCAN",
    }:
        monkeypatch.setattr(
            connector_egress_evidence,
            "verify_connector_campaign_log_capture_read_only",
            lambda *_args, **_kwargs: mutated.capture,
        )
    elif check_id in {
        "R05_RUNTIME_CHAIN",
        "R06_STARTUP_LOGGER_CENSUS",
        "R07_EXIT_LOGGER_CENSUS",
        "R08_PHASE_A_IDENTITY",
        "R09_PHASE_A_JOB_ZERO",
        "R10_PHASE_A_SOCKET_QUIESCENCE",
        "R11_AUTHORITY_CLEARED",
        "R12_PHASE_B_GUARDS",
        "R13_PHASE_B_JOB_ZERO",
        "R14_RUNTIME_TERMINAL",
        "R15_WRAPPER_NETWORK_INERT",
        "R16_PHASE_A_RAW_ONLY",
        "R19_A_TO_B_ORDER",
    }:
        monkeypatch.setattr(
            connector_egress_evidence,
            "read_runtime_records",
            lambda _payload: mutated.runtime_records,
        )
        if check_id in {
            "R07_EXIT_LOGGER_CENSUS",
            "R16_PHASE_A_RAW_ONLY",
        }:
            monkeypatch.setattr(
                dual_live_evaluator,
                "_parse_child_proof_records",
                lambda _payload: mutated.child_proofs,
            )
        if check_id == "R08_PHASE_A_IDENTITY":
            monkeypatch.setattr(
                dual_live_evaluator,
                "_validate_child_proof_runtime_bindings",
                lambda **_kwargs: None,
            )
    elif check_id == "R17_PHASE_B_STRICT_FLOW":
        monkeypatch.setattr(
            dual_live_evaluator,
            "_load_review_states",
            lambda _pass_runs: dict(mutated.review_states),
        )
    elif check_id in {
        "L04_LEDGER_RECONSTRUCTION",
        "L09_TRANSPORT_POLICY",
        "L12_RESERVATION_RESOLUTION",
    }:
        _patch_ledger_reader(monkeypatch, context, mutated.ledgers)
    elif check_id in {
        "L05_COUNTER_BIJECTION",
        "L06_COUNTER_BOOT",
        "L07_BYTE_ALLOWANCE",
        "L08_REQUEST_CADENCE",
    }:
        monkeypatch.setattr(
            connector_egress_evidence,
            "parse_connector_counter_records",
            lambda _payload, **_kwargs: mutated.counter_records,
        )
        _patch_ledger_reader(monkeypatch, context, context.ledgers)
    elif check_id == "L11_NRC_FIRST_BINDING":
        original = dual_live_evaluator._run_envelope

        def envelope(run: Any) -> Mapping[str, Any]:
            key = str(run.connector_key)
            return mutated.envelopes[key] if key == "sciencebase_mcs" else original(run)

        monkeypatch.setattr(dual_live_evaluator, "_run_envelope", envelope)
    elif check_id == "D03_LAYER3_EXECUTION":
        monkeypatch.setattr(
            dual_live_evaluator,
            "_load_execution_evidence",
            lambda *_args, **_kwargs: (
                dict(mutated.pass_runs),
                dict(mutated.output_integrity),
            ),
        )
    elif check_id == "D04_REVIEW_RESULT":
        monkeypatch.setattr(
            dual_live_evaluator,
            "_load_review_states",
            lambda _pass_runs: dict(mutated.review_states),
        )
    elif check_id in {"D05_PACKAGE_SET", "D07_SUBMIT_RECEIPT", "D08_HANDOFF_RECEIPT"}:
        original = dual_live_evaluator._reconciliation_states

        def states(
            reconciliations: Mapping[str, Any],
            *,
            state_key: str,
            missing_code: str,
        ) -> dict[str, Mapping[str, Any]]:
            projected = {
                "workbench_package_commit": mutated.package_commits,
                "package_review_submit": mutated.submit_states,
                "handoff_export_prepare": mutated.handoff_states,
            }
            if state_key in projected:
                return dict(projected[state_key])
            return original(
                reconciliations,
                state_key=state_key,
                missing_code=missing_code,
            )

        monkeypatch.setattr(dual_live_evaluator, "_reconciliation_states", states)
    elif check_id in {
        "D06_PACKAGE_PAYLOAD",
        "C04_SERIALIZATION_EVENT_SCAN",
        "F05_PROJECTION_REDERIVATION",
        "F09_CONNECTOR_AND_COMBINED_REPORTS",
    }:
        monkeypatch.setattr(
            dual_live_evaluator,
            "_load_package_payloads",
            lambda **_kwargs: dict(mutated.package_payloads),
        )
    elif check_id in {"C02_DB_SCALAR_JSON_SCAN", "C06_BOUNDED_DECODERS"}:
        monkeypatch.setattr(
            dual_live_evaluator,
            "_rows_for_selected_authority",
            lambda *_args, **_kwargs: mutated.db_values,
        )
    elif check_id in {"C03_NON_SOURCE_FILE_SCAN", "C08_SECRET_SCAN"}:
        monkeypatch.setattr(
            dual_live_evaluator,
            "_collect_non_source_files",
            lambda *_args, **_kwargs: mutated.non_source_files,
        )
    elif check_id == "F01_EVIDENCE_STABILITY":
        monkeypatch.setattr(
            dual_live_evaluator,
            "_fresh_observation",
            lambda *_args, **_kwargs: (
                "0" * 64,
                context.initial_database_snapshot_sha256,
            ),
        )
    elif check_id == "F02_DATABASE_STABILITY":
        monkeypatch.setattr(
            dual_live_evaluator,
            "_fresh_observation",
            lambda *_args, **_kwargs: (
                context.initial_snapshot_sha256,
                "0" * 64,
            ),
        )
    elif check_id in {"F03_NONCLAIMS_REPORT", "F06_NO_EGRESS_DEPENDENCY"}:
        return
    elif check_id == "R21_EXTANT_RUN_SEAL_EVENTS":
        monkeypatch.setattr(
            connector_egress_evidence,
            "verify_connector_campaign_log_capture_read_only",
            lambda *_args, **_kwargs: context.capture,
        )
    elif check_id == "L03_POST_TERMINAL_EXTINCTION":
        monkeypatch.setattr(
            connector_egress_evidence,
            "verify_connector_campaign_log_capture_read_only",
            lambda *_args, **_kwargs: context.capture,
        )
        _patch_ledger_reader(monkeypatch, context, context.ledgers)
        _patch_origin_reader(monkeypatch, context, context.origins)
    elif check_id == "C01_STRICT_NULLS":
        _patch_origin_reader(monkeypatch, context, context.origins)
        monkeypatch.setattr(
            dual_live_evaluator,
            "_find_sessions_and_downstream",
            lambda *_args, **_kwargs: (
                tuple(
                    context.downstream_sessions[key]
                    for key in dual_live_evaluator._EXPECTED_CONNECTORS
                ),
                dict(context.downstream),
            ),
        )
    elif check_id not in {
        "L01_RUN_CARDINALITY",
        "L02_TERMINAL_EVENT",
    }:
        raise AssertionError(f"public mutation adapter missing: {check_id}")


@pytest.mark.parametrize(
    "case",
    NEGATIVE_CASES,
    ids=[case.check_id for case in NEGATIVE_CASES],
)
def test_all_69_checks_have_positive_and_named_negative_evidence(
    matrix_campaign: _Campaign,
    monkeypatch: pytest.MonkeyPatch,
    case: _NegativeCase,
) -> None:
    campaign = matrix_campaign
    assert tuple(case.check_id for case in NEGATIVE_CASES) == (
        dual_live_evaluator.EVALUATOR_CHECK_ORDER
    )
    assert len(NEGATIVE_CASES) == len(dual_live_evaluator.CHECKS) == 69

    positive_report = _evaluate_preserving_protected_state(campaign)
    positive = _report_check(positive_report, case.check_id)
    assert (
        positive["check_id"],
        positive["status"],
        positive["code"],
    ) == (
        case.check_id,
        "PASS",
        f"{case.check_id.lower()}_pass",
    ), {"case": case, "positive": positive}

    context = _query_only_context(campaign)
    with monkeypatch.context() as local_monkeypatch:
        _install_public_negative(
            campaign,
            context,
            local_monkeypatch,
            case,
        )
        negative_report = _evaluate_preserving_protected_state(campaign)
        if negative_report["code"] == "dual_live_evaluation_internal_error":
            _raise_internal_evaluation_cause(campaign)
        negative = _report_check(negative_report, case.check_id)
        assert (
            negative["check_id"],
            negative["status"],
            negative["code"],
        ) == (
            case.check_id,
            case.status,
            case.code,
        ), {
            "case": case,
            "negative": negative,
            "seam": case.seam,
        }


def test_real_constructor_campaign_evaluates_all_69_checks_pass_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    campaign.db.rollback()
    db_bytes_before = campaign.db_path.read_bytes()
    rows_before = _row_snapshot(campaign.engine)
    files_before = _file_snapshot(tmp_path)

    report = _query_only_report(campaign)
    campaign.db.rollback()

    nonpassing = [
        (item["check_id"], item["status"], item["code"])
        for item in report["checks"]
        if item["status"] != "PASS"
    ]
    assert report["status"] == "PASS", {
        "nonpassing": nonpassing,
    }
    assert report["fresh_live"] is True
    assert report["evaluation_complete"] is True
    assert report["code"] == "all_checks_pass"
    assert [item["check_id"] for item in report["checks"]] == list(
        dual_live_evaluator.EVALUATOR_CHECK_ORDER
    )
    assert len(report["checks"]) == 69
    assert {item["status"] for item in report["checks"]} == {"PASS"}
    assert len({item["check_id"] for item in report["checks"]}) == 69
    assert campaign.db_path.read_bytes() == db_bytes_before
    assert _row_snapshot(campaign.engine) == rows_before
    assert _file_snapshot(tmp_path) == files_before

    campaign.db.close()
    campaign.engine.dispose()


def test_public_nrc_path_proves_integrity_through_handoff_and_reporting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    report = _evaluate_preserving_protected_state(campaign)
    assert report["status"] == "PASS"
    for check_id in (
        "D03_LAYER3_EXECUTION",
        "D04_REVIEW_RESULT",
        "D05_PACKAGE_SET",
        "D06_PACKAGE_PAYLOAD",
        "D07_SUBMIT_RECEIPT",
        "D08_HANDOFF_RECEIPT",
        "F09_CONNECTOR_AND_COMBINED_REPORTS",
    ):
        assert _report_check(report, check_id)["status"] == "PASS"
    context = _query_only_context(campaign)
    state = context.handoff_states["nrc_adams_aps"]
    envelope = state["handoff_export_envelope"]
    assert (
        state["connector_origin_integrity_v1"]
        == envelope["connector_origin_integrity_v1"]
    )
    assert (
        state["connector_output_integrity_v1"]
        == envelope["connector_output_integrity_v1"]
    )

    campaign.db.close()
    campaign.engine.dispose()


def test_public_sciencebase_path_proves_strict_origin_through_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    report = _evaluate_preserving_protected_state(campaign)
    assert report["status"] == "PASS"
    for check_id in (
        "D03_LAYER3_EXECUTION",
        "D04_REVIEW_RESULT",
        "D05_PACKAGE_SET",
        "D06_PACKAGE_PAYLOAD",
        "D07_SUBMIT_RECEIPT",
        "D08_HANDOFF_RECEIPT",
        "F09_CONNECTOR_AND_COMBINED_REPORTS",
    ):
        assert _report_check(report, check_id)["status"] == "PASS"
    context = _query_only_context(campaign)
    session = context.downstream_sessions["sciencebase_mcs"]
    plan = campaign.db.scalar(
        select(L3AnalysisPlan).where(L3AnalysisPlan.session_id == session.session_id)
    )
    assert plan is not None
    pass_run = campaign.db.scalar(
        select(L3PassRun).where(L3PassRun.session_id == session.session_id)
    )
    assert pass_run is not None
    assert pass_run.summary_json["planned_pass"]["source_intake_source_shape"] == (
        layer3_connector_source_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )
    assert context.review_states["sciencebase_mcs"]["review_state"] == (
        "execution_result_review_approved"
    )
    assert context.submit_states["sciencebase_mcs"]["package_review_state"] == (
        "package_review_approved"
    )
    handoff = context.handoff_states["sciencebase_mcs"]
    assert handoff["handoff_export_state"] == "handoff_export_prepared"
    assert handoff["handoff_export_envelope"]["external_handoff_enabled"] is False
    assert handoff["handoff_export_envelope"]["source_shape"] == (
        layer3_connector_source_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    )

    campaign.db.close()
    campaign.engine.dispose()


def test_real_gate_process_runs_g01_g02_then_all_69_checks_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    gate_path = Path(__file__).resolve().parents[2] / "tools" / "dual_live_gate.py"
    campaign.db.rollback()
    db_bytes_before = campaign.db_path.read_bytes()
    rows_before = _row_snapshot(campaign.engine)
    files_before = _file_snapshot(tmp_path)
    campaign.db.close()
    campaign.engine.dispose()
    environment = dict(os.environ)
    for name in (
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{campaign.db_path.resolve().as_posix()}",
            "STORAGE_DIR": str(Path(campaign.settings.storage_dir).resolve()),
            "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(campaign.evidence_root.resolve()),
            "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(
                Path(campaign.settings.connector_campaign_evidence_index_path).resolve()
            ),
            "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256": str(
                campaign.settings.connector_campaign_evidence_index_sha256
            ),
            "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
            "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
            "NRC_ADAMS_APS_SUBSCRIPTION_KEY": ("acceptance-secret-never-persisted"),
        }
    )
    assert subprocess.Popen is not _ACCEPTANCE_GATE_POPEN
    process = _ACCEPTANCE_GATE_POPEN(
        [
            sys.executable,
            "-I",
            "-B",
            str(gate_path),
            "--campaign-id",
            str(campaign.campaign_id),
            "--campaign-fingerprint",
            campaign.campaign_fingerprint,
        ],
        cwd=gate_path.parent.parent,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    completed = SimpleNamespace(
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )
    assert subprocess.Popen is not _ACCEPTANCE_GATE_POPEN
    assert completed.stderr == ""
    assert completed.returncode == 0, completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "PASS"
    assert report["fresh_live"] is True
    assert report["evaluation_complete"] is True
    assert report["code"] == "all_checks_pass"
    assert [item["check_id"] for item in report["checks"]] == list(
        dual_live_evaluator.EVALUATOR_CHECK_ORDER
    )
    assert len(report["checks"]) == 69
    assert {item["status"] for item in report["checks"]} == {"PASS"}
    assert campaign.db_path.read_bytes() == db_bytes_before
    post_engine = create_engine(
        f"sqlite:///{campaign.db_path.as_posix()}",
        future=True,
    )
    assert _row_snapshot(post_engine) == rows_before
    post_engine.dispose()
    assert _file_snapshot(tmp_path) == files_before


def test_writable_caller_session_fails_closed_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    campaign.db.rollback()
    db_bytes_before = campaign.db_path.read_bytes()
    rows_before = _row_snapshot(campaign.engine)
    files_before = _file_snapshot(tmp_path)

    report = dual_live_evaluator.evaluate_dual_live_proof(
        campaign.db,
        campaign_id=str(campaign.campaign_id),
        expected_campaign_fingerprint=campaign.campaign_fingerprint,
        settings=campaign.settings,
    )
    campaign.db.rollback()

    assert report["code"] != "dual_live_evaluation_internal_error"
    assert _report_check(report, "F01_EVIDENCE_STABILITY") == {
        "check_id": "F01_EVIDENCE_STABILITY",
        "status": "INDETERMINATE",
        "code": "f01_evidence_stability_evidence_unavailable",
        "evidence": {
            "domain": "stability",
            "reason_code": "dual_live_database_query_only_refused",
        },
    }
    assert _report_check(report, "F02_DATABASE_STABILITY") == {
        "check_id": "F02_DATABASE_STABILITY",
        "status": "INDETERMINATE",
        "code": "f02_database_stability_evidence_unavailable",
        "evidence": {
            "domain": "stability",
            "reason_code": "dual_live_database_query_only_refused",
        },
    }
    assert campaign.db_path.read_bytes() == db_bytes_before
    assert _row_snapshot(campaign.engine) == rows_before
    assert _file_snapshot(tmp_path) == files_before

    campaign.db.close()
    campaign.engine.dispose()


def test_one_log_byte_and_rebuilt_manifest_preserve_exact_seal_taxonomy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    _rewrite_log_and_manifest(campaign)

    report = _evaluate_preserving_protected_state(campaign)

    assert (
        _report_check(report, "R02_MANIFEST_FILE_HASHES")["status"],
        _report_check(report, "R02_MANIFEST_FILE_HASHES")["code"],
        _report_check(report, "R03_SEAL_PARITY")["status"],
        _report_check(report, "R03_SEAL_PARITY")["code"],
        _report_check(report, "R04_SEAL_EVENT_PARITY")["status"],
        _report_check(report, "R04_SEAL_EVENT_PARITY")["code"],
    ) == (
        "PASS",
        "r02_manifest_file_hashes_pass",
        "FAIL",
        "r03_seal_parity_invalid",
        "PASS",
        "r04_seal_event_parity_pass",
    )
    campaign.db.close()
    campaign.engine.dispose()


def test_one_log_byte_rebuilt_manifest_and_seal_exposes_database_witness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    manifest_sha256, file_set_hash = _rewrite_log_and_manifest(campaign)
    _rewrite_seal_to_match_manifest(
        campaign,
        manifest_sha256=manifest_sha256,
        file_set_hash=file_set_hash,
    )

    report = _evaluate_preserving_protected_state(campaign)

    assert (
        _report_check(report, "R02_MANIFEST_FILE_HASHES")["status"],
        _report_check(report, "R02_MANIFEST_FILE_HASHES")["code"],
        _report_check(report, "R03_SEAL_PARITY")["status"],
        _report_check(report, "R03_SEAL_PARITY")["code"],
        _report_check(report, "R04_SEAL_EVENT_PARITY")["status"],
        _report_check(report, "R04_SEAL_EVENT_PARITY")["code"],
    ) == (
        "PASS",
        "r02_manifest_file_hashes_pass",
        "PASS",
        "r03_seal_parity_pass",
        "FAIL",
        "r04_seal_event_parity_invalid",
    )
    campaign.db.close()
    campaign.engine.dispose()


@pytest.mark.parametrize("mutation", ("delete", "duplicate", "rewrite"))
def test_database_seal_event_rewrite_cannot_rewrite_original_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    campaign = _build_real_constructor_campaign(tmp_path, monkeypatch)
    events = tuple(
        campaign.db.scalars(
            select(ConnectorRunEvent)
            .where(ConnectorRunEvent.event_type == "campaign_log_capture_sealed")
            .order_by(ConnectorRunEvent.connector_run_event_id.asc())
        )
    )
    assert len(events) == 2
    event = events[0]
    if mutation == "delete":
        # Deliberate mutation of temporary adversarial test data, never repo data.
        campaign.db.delete(event)
    elif mutation == "duplicate":
        campaign.db.add(
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
                metrics_json=copy.deepcopy(event.metrics_json),
                created_at=event.created_at,
            )
        )
    else:
        event.metrics_json = {
            **copy.deepcopy(event.metrics_json),
            "manifest_sha256": "f" * 64,
        }
    campaign.db.commit()

    report = _evaluate_preserving_protected_state(campaign)

    _assert_named_nonpass(report, "R04_SEAL_EVENT_PARITY")
    campaign.db.close()
    campaign.engine.dispose()
