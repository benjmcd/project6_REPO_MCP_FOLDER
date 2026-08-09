from __future__ import annotations

import hashlib
from decimal import Decimal
from itertools import count
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api import layer3, review_nrc_aps
from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3AnalysisSet,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    VariableDefinition,
    VariableProfile,
    uuid_str,
)
from app.services import (
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_default_readiness,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_final_proof,
    layer3_candidate_b_operator_status,
    layer3_candidate_b_promotion_closure,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_visual_lane_status,
    layer3_internal_webhook_connector,
    layer3_sec_edgar_authority_envelope,
    layer3_sec_edgar_downstream_proof,
    layer3_sec_edgar_downstream_status,
    layer3_sec_edgar_html_inline_xbrl_downstream_proof,
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof,
    layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status,
    layer3_sec_edgar_html_inline_xbrl_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_downstream_proof,
    layer3_sec_edgar_live_downstream_status,
    layer3_sec_edgar_live_material_bridge,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_material_bridge,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_edgar_source_acquisition,
    layer3_workbench,
)
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services import layer3_sec_xbrl_projection_persistence as xbrl_proj_persistence
from app.services import layer3_sec_xbrl_statement_assembly as xbrl_assembly
from app.services import layer3_sec_xbrl_statement_packet_persistence as xbrl_packet_persistence
from app.services.layer3_utils import stable_hash
from app.services.layer3_raw_mixed_bridge import (
    RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_SEED_MODE,
)
from app.services.layer3_raw_mixed_materialization import (
    RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_MATERIALIZE_MODE,
    RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_source_directory_text_index import source_directory_material_text_index
from app.services.layer3_source_directory_vector_index import (
    source_directory_material_embedding_vector_index,
)
from app.services.layer3_typing_entry import materialize_typing_entry
from app.services.dataframe_io import load_version_dataframe
from review_browser_fixture import ReviewBrowserFixture, build_review_browser_fixture, install_review_browser_patches
import test_layer3_candidate_b_default_readiness as candidate_b_readiness_helpers
from test_layer3_candidate_b_default_readiness import (
    READY_REGRESSION,
    READY_SCOPE,
    _bundle_downstream_proof_request,
    _closure_evidence_request,
    _coverage_evidence,
    _final_proof_request,
    _final_proof_status_request,
    _operator_status_request,
    _payload,
    _downstream_proof_request,
    _visual_lane_status_request,
    _write_bundle_receipt,
    _write_runtime_receipt,
)

APS_EVIDENCE_BUNDLE_SCHEMA_ID = "aps.evidence_bundle.v2"
APS_EVIDENCE_BUNDLE_SCHEMA_VERSION = 2
APS_MODE_BROWSE = "browse"
APS_CONTENT_CONTRACT_ID = "aps_content_units_v2"
APS_CHUNKING_CONTRACT_ID = "aps_chunking_v2"
APS_NORMALIZATION_CONTRACT_ID = "aps_text_normalization_v2"
PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF = "aps_evidence_bundle_handoff"
HARNESS_INFO_SCHEMA_ID = "project6.review_browser_harness_info.v1"
HARNESS_INFO_SCHEMA_VERSION = 1
HARNESS_FIXTURE_VERSION = "review-browser-fixture-v1"
HARNESS_PATCH_GROUPS = (
    "review-runtime-bindings",
    "workbench-compare",
    "candidate-b-trace",
    "layer3-deterministic-analysis",
    "layer3-aps-handoff",
    "layer3-sec-edgar-live-source-artifact",
)


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _compute_aps_bundle_checksum(payload: dict[str, object]) -> str:
    clean = dict(payload)
    clean.pop("bundle_checksum", None)
    clean.pop("_bundle_ref", None)
    clean.pop("_persisted", None)
    return hashlib.sha256(_canonical_json_bytes(clean)).hexdigest()


def _sync_candidate_b_readiness_helper_modules() -> None:
    candidate_b_readiness_helpers.settings = settings
    candidate_b_readiness_helpers.layer3_candidate_b_bundle_bridge = layer3_candidate_b_bundle_bridge
    candidate_b_readiness_helpers.layer3_candidate_b_runtime_bridge = layer3_candidate_b_runtime_bridge
    candidate_b_readiness_helpers.layer3_candidate_b_downstream_proof = layer3_candidate_b_downstream_proof
    candidate_b_readiness_helpers.layer3_candidate_b_final_proof = layer3_candidate_b_final_proof
    candidate_b_readiness_helpers.layer3_candidate_b_operator_status = layer3_candidate_b_operator_status


def _prepare_candidate_b_readiness_audit_fixture() -> dict[str, object]:
    _sync_candidate_b_readiness_helper_modules()
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    bundle_proof = layer3_candidate_b_bundle_downstream_proof.candidate_b_bundle_downstream_proof(
        _bundle_downstream_proof_request(bundle_receipt_id)
    )
    visual_status = layer3_candidate_b_visual_lane_status.candidate_b_visual_lane_status(
        _visual_lane_status_request(runtime_receipt_id)
    )
    runtime_proof = layer3_candidate_b_downstream_proof.candidate_b_runtime_downstream_proof(
        _downstream_proof_request(runtime_receipt_id, visual_status)
    )
    operator_status = layer3_candidate_b_operator_status.candidate_b_default_promotion_operator_status(
        _operator_status_request(bundle_receipt_id, runtime_receipt_id, visual_status, runtime_proof)
    )
    closure = layer3_candidate_b_promotion_closure.candidate_b_default_promotion_closure_evidence(
        _closure_evidence_request(
            bundle_receipt_id,
            runtime_receipt_id,
            bundle_proof,
            runtime_proof,
            operator_status,
        )
    )
    readiness_payload = _payload(bundle_receipt_id, runtime_receipt_id)
    readiness_payload["bundle_downstream_proof"] = bundle_proof
    readiness_payload["candidate_b_visual_lane_status_evidence"] = visual_status
    readiness_payload["runtime_downstream_proof"] = runtime_proof
    readiness_payload["operator_status_evidence"] = operator_status
    readiness_payload["closure_evidence"] = closure
    readiness = layer3_candidate_b_default_readiness.evaluate_candidate_b_default_promotion_readiness(
        readiness_payload
    )
    return {
        "schema_id": "project6.review_browser_candidate_b_readiness_audit_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "server_generated_receipts": True,
        "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
        "readiness_audit_id": readiness["readiness_audit_id"],
        "readiness_audit_hash": readiness["readiness_audit_hash"],
        "readiness_audit": readiness,
        "final_proof_request": _final_proof_request(readiness),
    }


def _bridge_role_counts(bridge_response: dict[str, Any]) -> dict[str, int]:
    artifact_family = bridge_response.get("governed_retained_artifact_family") or {}
    return dict(artifact_family.get("role_counts") or {})


def _prepare_candidate_b_realistic_bridges(
    fixture: ReviewBrowserFixture,
) -> dict[str, Any]:
    baseline_run_id = fixture.baseline_binding.run_id
    candidate_a_run_id = fixture.candidate_a_binding.run_id
    candidate_b_run_id = fixture.candidate_b_binding.run_id
    bundle_bridge = layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge(
        {
            "client_request_id": "candidate-b-realistic-bundle-bridge",
            "bridge_mode": layer3_candidate_b_bundle_bridge.BRIDGE_MODE,
            "candidate_b_bundle_id": fixture.bundle_id,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "operator_confirmation": True,
        },
        checkout_root=fixture.checkout_root,
    )
    runtime_bridge = layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge(
        {
            "client_request_id": "candidate-b-realistic-runtime-bridge",
            "bridge_mode": layer3_candidate_b_runtime_bridge.BRIDGE_MODE,
            "candidate_b_run_id": candidate_b_run_id,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "operator_confirmation": True,
        }
    )
    return {
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_run_id": candidate_b_run_id,
        "bundle_bridge": bundle_bridge,
        "runtime_bridge": runtime_bridge,
    }


def _prepare_candidate_b_realistic_readiness_audit_fixture(
    fixture: ReviewBrowserFixture,
) -> dict[str, object]:
    bridge_setup = _prepare_candidate_b_realistic_bridges(fixture)
    baseline_run_id = str(bridge_setup["baseline_run_id"])
    candidate_a_run_id = str(bridge_setup["candidate_a_run_id"])
    candidate_b_run_id = str(bridge_setup["candidate_b_run_id"])
    bundle_bridge = bridge_setup["bundle_bridge"]
    runtime_bridge = bridge_setup["runtime_bridge"]
    bundle_receipt_id = str(bundle_bridge["bridge_receipt_id"])
    runtime_receipt_id = str(runtime_bridge["bridge_receipt_id"])
    bundle_proof = layer3_candidate_b_bundle_downstream_proof.candidate_b_bundle_downstream_proof(
        {
            "client_request_id": "candidate-b-realistic-bundle-downstream-proof",
            "proof_mode": "candidate_b_bundle_downstream_e2e_proof_v1",
            "operator_decision": "record_candidate_b_bundle_downstream_e2e_proof",
            "candidate_b_bundle_id": fixture.bundle_id,
            "bridge_receipt_id": bundle_receipt_id,
            "coverage_evidence": _coverage_evidence(
                retained_artifact_family_hash=bundle_bridge["authority_hashes"][
                    "governed_retained_artifact_family_hash"
                ],
            ),
            "operator_confirmation": True,
        }
    )
    visual_status = layer3_candidate_b_visual_lane_status.candidate_b_visual_lane_status(
        {
            "client_request_id": "candidate-b-realistic-visual-lane-status",
            "status_mode": "candidate_b_visual_lane_status_v1",
            "operator_decision": "inspect_candidate_b_visual_lane_evidence_status",
            "candidate_b_run_id": candidate_b_run_id,
            "bridge_receipt_id": runtime_receipt_id,
        }
    )
    runtime_proof = layer3_candidate_b_downstream_proof.candidate_b_runtime_downstream_proof(
        {
            "client_request_id": "candidate-b-realistic-runtime-downstream-proof",
            "proof_mode": "candidate_b_visual_lane_runtime_downstream_e2e_proof_v1",
            "operator_decision": "record_candidate_b_visual_lane_runtime_downstream_e2e_proof",
            "candidate_b_run_id": candidate_b_run_id,
            "bridge_receipt_id": runtime_receipt_id,
            "candidate_b_visual_lane_status_evidence": visual_status,
            "coverage_evidence": _coverage_evidence(
                retained_artifact_family_hash=runtime_bridge["authority_hashes"][
                    "governed_retained_artifact_family_hash"
                ],
            ),
            "operator_confirmation": True,
        }
    )
    operator_status = layer3_candidate_b_operator_status.candidate_b_default_promotion_operator_status(
        {
            "client_request_id": "candidate-b-realistic-operator-status",
            "status_mode": "candidate_b_default_promotion_operator_status_v1",
            "operator_decision": "inspect_candidate_b_default_promotion_operator_status",
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": fixture.bundle_id,
            "candidate_b_run_id": candidate_b_run_id,
            "candidate_b_bundle_bridge_receipt_id": bundle_receipt_id,
            "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
            "candidate_b_visual_lane_status_evidence": visual_status,
            "runtime_downstream_proof": runtime_proof,
        }
    )
    closure = layer3_candidate_b_promotion_closure.candidate_b_default_promotion_closure_evidence(
        {
            "client_request_id": "candidate-b-realistic-closure-evidence",
            "closure_mode": "candidate_b_default_promotion_closure_evidence_v1",
            "operator_decision": "record_candidate_b_default_promotion_closure_evidence",
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": fixture.bundle_id,
            "candidate_b_run_id": candidate_b_run_id,
            "candidate_b_bundle_bridge_receipt_id": bundle_receipt_id,
            "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
            "eligible_corpus_scope": READY_SCOPE,
            "regression_disposition": READY_REGRESSION,
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
            "bundle_downstream_proof": bundle_proof,
            "runtime_downstream_proof": runtime_proof,
            "operator_status_evidence": operator_status,
        }
    )
    readiness = layer3_candidate_b_default_readiness.evaluate_candidate_b_default_promotion_readiness(
        {
            "client_request_id": "candidate-b-realistic-default-readiness",
            "readiness_mode": "candidate_b_default_promotion_readiness_audit_v1",
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": fixture.bundle_id,
            "candidate_b_run_id": candidate_b_run_id,
            "candidate_b_bundle_bridge_receipt_id": bundle_receipt_id,
            "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
            "eligible_corpus_scope": READY_SCOPE,
            "regression_disposition": READY_REGRESSION,
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
            "bundle_downstream_proof": bundle_proof,
            "candidate_b_visual_lane_status_evidence": visual_status,
            "runtime_downstream_proof": runtime_proof,
            "operator_status_evidence": operator_status,
            "closure_evidence": closure,
        }
    )
    return {
        "schema_id": "project6.review_browser_candidate_b_realistic_readiness_audit_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "server_generated_receipts": True,
        "bridge_receipts_from_fixture_sources": True,
        "candidate_b_bundle_id": fixture.bundle_id,
        "candidate_b_run_id": candidate_b_run_id,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_bundle_bridge_receipt_id": bundle_receipt_id,
        "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
        "visual_lane_mode": runtime_bridge["visual_lane_mode"],
        "bundle_artifact_role_counts": _bridge_role_counts(bundle_bridge),
        "runtime_artifact_role_counts": _bridge_role_counts(runtime_bridge),
        "bundle_authority_hashes": bundle_bridge["authority_hashes"],
        "runtime_authority_hashes": runtime_bridge["authority_hashes"],
        "readiness_audit_id": readiness["readiness_audit_id"],
        "readiness_audit_hash": readiness["readiness_audit_hash"],
        "readiness_audit": readiness,
        "final_proof_request": _final_proof_request(readiness),
    }


def _prepare_candidate_b_source_directory_authority_fixture(
    fixture: ReviewBrowserFixture,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = payload or {}
    candidate_b_source_kind = str(payload.get("candidate_b_source_kind") or "bundle").strip().lower()
    if candidate_b_source_kind not in {"bundle", "runtime"}:
        raise ValueError("candidate_b_source_kind must be bundle or runtime")
    bridge_setup = _prepare_candidate_b_realistic_bridges(fixture)
    bridge = bridge_setup[f"{candidate_b_source_kind}_bridge"]
    bridge_receipt_id = str(bridge["bridge_receipt_id"])
    bridge_base = (
        Path(str(settings.layer3_candidate_b_bundle_bridge_dir))
        if candidate_b_source_kind == "bundle"
        else Path(str(settings.layer3_candidate_b_runtime_bridge_dir))
    )
    curated_root = bridge_base / bridge_receipt_id / "curated"
    if not curated_root.is_dir():
        raise ValueError(f"Candidate B {candidate_b_source_kind} curated bridge root is unavailable")
    settings.layer3_source_ingestion_dir = str(curated_root)
    return {
        "schema_id": "project6.review_browser_candidate_b_source_directory_authority_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "server_generated_receipts": True,
        "source_ingestion_dir_configured_from_bridge": True,
        "candidate_b_source_kind": candidate_b_source_kind,
        "candidate_b_bundle_id": fixture.bundle_id,
        "candidate_b_run_id": bridge_setup["candidate_b_run_id"],
        "baseline_run_id": bridge_setup["baseline_run_id"],
        "candidate_a_run_id": bridge_setup["candidate_a_run_id"],
        "bridge_receipt_id": bridge_receipt_id,
        "bundle_bridge_receipt_id": bridge_setup["bundle_bridge"]["bridge_receipt_id"],
        "runtime_bridge_receipt_id": bridge_setup["runtime_bridge"]["bridge_receipt_id"],
        "source_ingestion_config_authority": "LAYER3_SOURCE_INGESTION_DIR",
        "source_ingestion_required_root_ref": bridge["source_ingestion_required_root_ref"],
        "curated_material_root_ref": bridge["curated_material_root_ref"],
        "curated_root_absolute_path_exposed": False,
        "expected_source_directory_file_count": bridge["admitted_artifact_subset"]["file_count"],
        "admitted_artifact_subset": bridge["admitted_artifact_subset"],
        "artifact_role_counts": _bridge_role_counts(bridge),
        "authority_hashes": bridge["authority_hashes"],
        "layer3_material_preview_compatible": bridge["layer3_material_preview_compatible"],
        "gate_b_material_authority_compatible": bridge["gate_b_material_authority_compatible"],
        "negative_invariants": bridge["negative_invariants"],
    }


def _prepare_candidate_b_final_proof_fixture() -> dict[str, object]:
    readiness_setup = _prepare_candidate_b_readiness_audit_fixture()
    readiness = readiness_setup["readiness_audit"]
    final_proof = layer3_candidate_b_final_proof.candidate_b_default_promotion_final_proof(
        _final_proof_request(readiness)
    )
    return {
        "schema_id": "project6.review_browser_candidate_b_final_proof_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "server_generated_receipts": True,
        "candidate_b_runtime_bridge_receipt_id": readiness_setup["candidate_b_runtime_bridge_receipt_id"],
        "proof_receipt_id": final_proof["proof_receipt_id"],
        "proof_hash": final_proof["proof_hash"],
        "readiness_audit_id": readiness["readiness_audit_id"],
        "readiness_audit_hash": readiness["readiness_audit_hash"],
        "status_request": _final_proof_status_request(
            readiness_setup["candidate_b_runtime_bridge_receipt_id"],
            final_proof["proof_receipt_id"],
        ),
    }


def _install_layer3_browser_patches(temp_path: Path) -> None:
    class _BrowserEvidenceBundleError(RuntimeError):
        def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
            super().__init__(message)
            self.code = code
            self.message = message
            self.status_code = status_code

    def _load_browser_persisted_bundle_artifact(*, bundle_ref: str | Path):
        bundle_path = Path(bundle_ref)
        if not bundle_path.exists():
            raise _BrowserEvidenceBundleError("invalid_request", "bundle not found", status_code=404)
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        if payload.get("schema_id") != APS_EVIDENCE_BUNDLE_SCHEMA_ID:
            raise _BrowserEvidenceBundleError("schema_mismatch", "bundle schema mismatch", status_code=409)
        expected_checksum = _compute_aps_bundle_checksum(payload)
        if payload.get("bundle_checksum") != expected_checksum:
            raise _BrowserEvidenceBundleError("checksum_mismatch", "bundle checksum mismatch", status_code=409)
        return payload, bundle_path

    aps_bundle_module = ModuleType("app.services.nrc_aps_evidence_bundle")
    aps_bundle_module.EvidenceBundleError = _BrowserEvidenceBundleError
    aps_bundle_module.load_persisted_bundle_artifact = _load_browser_persisted_bundle_artifact
    sys.modules["app.services.nrc_aps_evidence_bundle"] = aps_bundle_module

    def _recommend_analysis(*args, **kwargs) -> dict[str, object]:
        dataset_version_id = str(kwargs.get("dataset_version_id") or (args[1] if len(args) > 1 else ""))
        return {
            "dataset_version_id": dataset_version_id,
            "recommended_sequence": ["decomposition", "structural_break"],
            "rationale": "browser harness deterministic quantitative recommendation",
            "profile_context": {
                "stationary_like_variables": ["value"],
                "mixed_or_nonstationary_variables": [],
                "seasonal_like_variables": ["value"],
            },
        }

    def _run_analysis(
        db,
        *,
        dataset_version_id,
        method_name,
        goal_type=None,
        parameters=None,
        annotation_window_id=None,
        commit=True,
        connector_origin_integrity=None,
    ):
        # Faithfully mirror production run_analysis, which loads the dataset
        # dataframe first and raises if the storage is unreadable. The harness
        # output itself stays deterministic, but this preserves the real
        # execution-failure semantics so a seed with unreadable dataset storage
        # drives a genuine PASS_STATUS_FAILED instead of a stub that always
        # completes.
        load_version_dataframe(db, dataset_version_id)
        now = datetime.now(timezone.utc)
        run = AnalysisRun(
            analysis_run_id=uuid_str(),
            dataset_version_id=dataset_version_id,
            method_name=method_name,
            goal_type=goal_type,
            status="completed",
            route_reason="browser harness deterministic quantitative run",
            parameters_json=parameters or {},
            window_scope_json={"annotation_window_id": annotation_window_id} if annotation_window_id else {},
            started_at=now,
            completed_at=now,
        )
        db.add(run)
        db.flush()
        db.add(
            AnalysisArtifact(
                artifact_id=uuid_str(),
                analysis_run_id=run.analysis_run_id,
                artifact_type="summary_json",
                title="Browser harness deterministic output",
                storage_ref=f"layer3-browser://artifact/{run.analysis_run_id}/summary.json",
                summary="Deterministic Layer 3 browser harness output.",
                metadata_json={"source": "review_browser_server", "method_name": method_name},
            )
        )
        db.flush()
        return run

    layer3_pass_entry_module.recommend_analysis = _recommend_analysis
    layer3_pass_entry_module.run_analysis = _run_analysis

    from app.services import layer3_workbench as layer3_workbench_module

    def _check_aps_handoff_compatibility(db, *, session_id, active_package_authority=None):
        return SimpleNamespace(compatible=True, blocked_reason=None)

    def _materialize_aps_handoff(db, *, session_id, active_package_authority=None):
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.session_id == session_id)
            .one()
        )
        output_package_id = uuid_str()
        payload_path = temp_path / "aps-dispatch" / f"{output_package_id}.json"
        bundle_id = f"browser-aps-bundle-{output_package_id}"
        payload = {
            "schema_id": APS_EVIDENCE_BUNDLE_SCHEMA_ID,
            "schema_version": APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "bundle_id": bundle_id,
            "mode": APS_MODE_BROWSE,
            "session_id": session_id,
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "results": [],
        }
        payload["bundle_checksum"] = _compute_aps_bundle_checksum(payload)
        payload_ref = _write_json(payload_path, payload)
        package = L3OutputPackage(
            output_package_id=output_package_id,
            session_id=session_id,
            reconciliation_record_id=reconciliation.reconciliation_record_id,
            package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            status="package_complete",
            payload_ref=payload_ref,
            payload_hash=hashlib.sha256(Path(payload_ref).read_bytes()).hexdigest(),
            summary_json={
                "bundle_id": payload["bundle_id"],
                "aps_schema_id": payload["schema_id"],
            },
        )
        db.add(package)
        db.flush()
        return SimpleNamespace(output_package=package)

    layer3_workbench_module.check_aps_handoff_compatibility = _check_aps_handoff_compatibility
    layer3_workbench_module.materialize_aps_handoff = _materialize_aps_handoff


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return str(path)


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _write_layer3_source_directory_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    lines = ["alpha beta beta lead\n"]
    lines.extend(f"context filler line {index}\n" for index in range(1, 42))
    lines.append("alpha gamma tail\n")
    (root / "vector-retrieval.txt").write_text("".join(lines), encoding="utf-8")


def _seed_browser_dataset_version(db, temp_path: Path, *, seed_id: str, dataset_id: str, dataset_version_id: str) -> Path:
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {seed_id}",
        description="Layer 3 browser harness dataset",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="layer3-browser-harness",
    )
    observed_at = VariableDefinition(
        variable_id=f"var-time-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    value_profile = VariableProfile(
        variable_profile_id=f"profile-value-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_id=value.variable_id,
        seasonality_flag=True,
        stationarity_hint="likely_stationary",
        summary_json={},
    )
    db.add_all([dataset, version, observed_at, value, value_profile])
    db.flush()

    dataset_dir = temp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    rows = ["observed_at,value"]
    for index in range(24):
        year = 2020 + (index // 12)
        month = 1 + (index % 12)
        rows.append(f"{year:04d}-{month:02d}-01T00:00:00+00:00,{100 + index}")
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    version.storage_ref = str(csv_path)
    version.row_count = 24
    db.flush()
    return csv_path


def _seed_browser_aps_dataset_version_candidate(db, temp_path: Path) -> dict[str, str]:
    seed_id = uuid_str()
    dataset_id = f"ds-aps-{seed_id}"
    dataset_version_id = f"dv-aps-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=f"aps-{seed_id}",
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    db.add(
        DatasetSourceProvenance(
            dataset_version_id=dataset_version_id,
            connector_run_id=None,
            source_system="nrc_adams_aps",
            source_mode="artifact_csv_parser",
            source_artifact_key=f"aps-target-artifacts/run-{seed_id}/target-{seed_id}/extraction.json",
            sciencebase_file_name="browser-fixture.csv",
            downloaded_sha256="1" * 64,
            raw_storage_ref=f"aps-target-artifacts/run-{seed_id}/target-{seed_id}/blob.csv",
            source_reference_json={
                "target_id": f"target-{seed_id}",
                "accession_number": "ML26001A777",
                "table_index": 0,
                "table_hash": f"hash-table-{seed_id}",
                "parser_family": "csv_table",
                "parser_contract_id": "aps_csv_parser_v1",
                "typed_content_contract_id": "aps_csv_table_units_v1",
                "diagnostics_ref": f"aps-target-artifacts/run-{seed_id}/target-{seed_id}/diagnostics.json",
            },
        )
    )
    db.commit()
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "storage_ref": str(csv_path),
    }


def _seed_browser_raw_mixed_authority(db, temp_path: Path, *, seed_id: str) -> dict[str, object]:
    dataset_version_ids = (f"dv-{seed_id}-a", f"dv-{seed_id}-b")
    dataset_ids = (f"ds-{seed_id}-a", f"ds-{seed_id}-b")
    run_id = f"run-{seed_id}"
    target_id = f"target-{seed_id}"
    content_id = f"content-{seed_id}"
    corpus_batch_id = f"batch-{seed_id}"

    for index, dataset_version_id in enumerate(dataset_version_ids):
        _seed_browser_dataset_version(
            db,
            temp_path,
            seed_id=f"{seed_id}-{index + 1}",
            dataset_id=dataset_ids[index],
            dataset_version_id=dataset_version_id,
        )

    _seed_browser_aps_content_fixture(db, temp_path, run_id=run_id, target_id=target_id, content_id=content_id)

    for dataset_version_id in dataset_version_ids:
        db.add(
            DatasetSourceProvenance(
                dataset_version_id=dataset_version_id,
                connector_run_id=run_id,
                source_system="nrc_adams_aps",
                source_mode="raw_mixed_corpus_bridge_seed_fixture",
                source_artifact_key=f"aps://{run_id}/{target_id}/{dataset_version_id}",
                sciencebase_file_name="browser-raw-mixed-fixture.csv",
                downloaded_sha256=hashlib.sha256(dataset_version_id.encode("utf-8")).hexdigest(),
                raw_storage_ref=f"dataset_version:{dataset_version_id}",
                source_reference_json={
                    "target_id": target_id,
                    "content_id": content_id,
                    "accession_number": "ML26001A777",
                    "parser_family": "csv_table",
                    "parser_contract_id": "aps_csv_parser_v1",
                    "typed_content_contract_id": "aps_csv_table_units_v1",
                },
                fetch_policy_mode="seed_fixture",
            )
        )

    manifest_ref = f"raw-mixed/{seed_id}.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": corpus_batch_id,
        "aps_run_id": run_id,
        "target_ids": [target_id],
        "source_classes": ["dataset_version", "aps_content_document"],
        "dataset_version_ids": list(dataset_version_ids),
        "aps_content_document_ids": [content_id],
    }
    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    db.commit()

    return {
        "schema_id": "project6.review_browser_raw_mixed_seed_setup.v1",
        "schema_version": 1,
        "seed_request": {
            "schema_id": "layer3.raw_mixed_corpus_seed_request.v1",
            "schema_version": 1,
            "client_request_id": f"browser-raw-mixed-seed-{seed_id}",
            "seed_mode": RAW_MIXED_CORPUS_SEED_MODE,
            "corpus_batch_id": corpus_batch_id,
            "aps_run_id": run_id,
            "target_ids": [target_id],
            "artifact_manifest_ref": manifest_ref,
            "artifact_manifest_hash": manifest_hash,
            "requested_source_classes": ["dataset_version", "aps_content_document"],
            "operator_confirmation": True,
        },
    }


def _sec_edgar_browser_coverage(bridge: dict[str, Any], gate_b: dict[str, Any], snapshot: L3MaterialSnapshot) -> dict[str, dict[str, object]]:
    coverage: dict[str, dict[str, object]] = {}
    for step in layer3_sec_edgar_downstream_proof.REQUIRED_COVERAGE:
        item: dict[str, object] = {
            "status": "proven",
            "evidence_ref": f"sec-edgar-text-table-downstream-proof:{step}",
            "evidence_hash": stable_hash({"step": step, "session_id": gate_b["session_id"]}),
            "server_response_hash": stable_hash({"response": step, "session_id": gate_b["session_id"]}),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        }
        if step not in {"authority_envelope_validation", "material_authority_bridge"}:
            item["session_id"] = gate_b["session_id"]
        if step == "authority_envelope_validation":
            item["authority_envelope_hash"] = bridge["authority_envelope_hash"]
        if step == "material_authority_bridge":
            item["bridge_receipt_hash"] = bridge["bridge_receipt_hash"]
            item["material_preview_hash"] = bridge["material_preview_hash"]
            item["gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
        if step == "gate_b_commit":
            item["material_preview_hash"] = bridge["material_preview_hash"]
            item["gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
            item["selection_manifest_id"] = gate_b["selection_manifest_id"]
            item["material_snapshot_payload_hash"] = snapshot.payload_hash
        coverage[step] = item
    return coverage


def _sec_edgar_text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _ReviewBrowserSeededSecEdgarClient:
    def __init__(self) -> None:
        self._content_by_url: dict[str, bytes] = {}
        self.calls: list[dict[str, object]] = []

    def register_complete_submission_text(self, *, url: str, content: bytes) -> None:
        self._content_by_url[url] = content

    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ) -> layer3_sec_edgar_live_source_artifact.SecEdgarFetchResult:
        self.calls.append(
            {
                "url_hash": _sec_edgar_text_hash(url),
                "user_agent_hash": _sec_edgar_text_hash(user_agent),
                "timeout_seconds": timeout_seconds,
                "max_bytes": max_bytes,
            }
        )
        content = self._content_by_url.get(url)
        if content is None:
            return layer3_sec_edgar_live_source_artifact.SecEdgarFetchResult(
                status_code=404,
                final_url=url,
            )
        return layer3_sec_edgar_live_source_artifact.SecEdgarFetchResult(
            status_code=200,
            content=content,
            final_url=url,
        )


def _reset_sec_edgar_live_source_artifact_rate_marker() -> None:
    root = layer3_sec_edgar_live_source_artifact._root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "rate-limit-state.json").write_text(
        json.dumps(
            {
                "last_network_request_at": 0,
                "rate_policy_id": layer3_sec_edgar_live_source_artifact.RATE_POLICY_ID,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _sec_edgar_live_source_artifact_identity(seed_id: str) -> dict[str, str]:
    seed_hash = _sec_edgar_text_hash(seed_id)
    cik = f"{1000000000 + (int(seed_hash[:16], 16) % 9000000000):010d}"
    accession_year = int(seed_hash[16:20], 16) % 100
    accession_sequence = int(seed_hash[20:32], 16) % 1_000_000
    return {
        "cik_or_filer_ref": cik,
        "accession_or_submission_id": f"{cik}-{accession_year:02d}-{accession_sequence:06d}",
        "form_type": "10-K",
        "filing_date": "2024-11-01",
    }


def _prepare_sec_edgar_live_source_artifact_acquisition_fixture(
    *,
    fake_client: _ReviewBrowserSeededSecEdgarClient,
    seed_id: str,
) -> dict[str, object]:
    content = f"<SEC-DOCUMENT>review browser SEC EDGAR filing text {seed_id}</SEC-DOCUMENT>\n".encode("utf-8")
    _reset_sec_edgar_live_source_artifact_rate_marker()
    source_identity = _sec_edgar_live_source_artifact_identity(seed_id)
    acquisition_request = {
        **source_identity,
        "expected_content_sha256": hashlib.sha256(content).hexdigest(),
    }
    fake_client.register_complete_submission_text(
        url=layer3_sec_edgar_live_source_artifact._server_derived_complete_submission_text_url(acquisition_request),
        content=content,
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_live_source_artifact_acquisition_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "live_acquisition_request": acquisition_request,
        "expected_content_sha256": acquisition_request["expected_content_sha256"],
        "acquisition_endpoint": "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire",
        "status_endpoint_prefix": "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/status/",
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "server_user_agent_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _seed_sec_edgar_browser_dataset_version(
    db,
    temp_path: Path,
    *,
    dataset_version_id: str,
    parser_family: str,
    typed_content_contract_id: str,
    source_mode: str,
    parser_contract_id: str,
) -> str:
    dataset_id = f"ds-{dataset_version_id}"
    variable_suffix = stable_hash(
        {
            "dataset_version_id": dataset_version_id,
            "fixture": "sec_edgar_browser_dataset",
        }
    )[:16]
    dataset = Dataset(
        dataset_id=dataset_id,
        name="SEC EDGAR browser fixture dataset",
        description="SEC EDGAR dataset for Layer 3 browser proof",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="table-0",
        version_type="sec_edgar_browser_fixture",
        status="ready",
        notes="sec_edgar_browser_fixture=true",
        row_count=3,
    )
    observed_at = VariableDefinition(
        variable_id=f"var-time-{variable_suffix}",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{variable_suffix}",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    dataset_dir = temp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    csv_path.write_text(
        "observed_at,value\n2025-01-01,1.0\n2025-02-01,2.5\n2025-03-01,3.0\n",
        encoding="utf-8",
    )
    version.storage_ref = str(csv_path)
    provenance = DatasetSourceProvenance(
        dataset_version_id=dataset_version_id,
        connector_run_id=None,
        source_system="nrc_adams_aps",
        source_mode=source_mode,
        source_artifact_key="sec-edgar-browser-fixture/extraction.json",
        sciencebase_file_name="sec-edgar-fixture.csv",
        downloaded_sha256="0" * 64,
        raw_storage_ref="sec-edgar-browser-fixture/blob.csv",
        source_reference_json={
            "target_id": "sec-edgar-browser-fixture",
            "accession_number": "ML000000001",
            "table_index": 0,
            "table_hash": "hash-sec-edgar-browser-fixture",
            "parser_family": parser_family,
            "parser_contract_id": parser_contract_id,
            "typed_content_contract_id": typed_content_contract_id,
            "diagnostics_ref": "sec-edgar-browser-fixture/diagnostics.json",
        },
    )
    db.add_all([dataset, version, observed_at, value, provenance])
    db.flush()
    return dataset_version_id


def _bind_sec_edgar_browser_dataset_to_live_source_artifact(
    db,
    temp_path: Path,
    *,
    dataset_version_id: str,
    live_artifact: dict[str, Any],
    live_acquisition_request: dict[str, Any],
) -> str:
    _seed_sec_edgar_browser_dataset_version(
        db,
        temp_path,
        dataset_version_id=dataset_version_id,
        parser_family=layer3_sec_edgar_source_acquisition.PARSER_FAMILY,
        typed_content_contract_id=layer3_sec_edgar_source_acquisition.TYPED_CONTENT_CONTRACT_ID,
        source_mode=layer3_sec_edgar_source_acquisition.SOURCE_MODE,
        parser_contract_id=layer3_sec_edgar_source_acquisition.PARSER_CONTRACT_ID,
    )
    provenance = (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .one()
    )
    source_artifact = live_artifact["source_artifact_receipt"]
    provenance.downloaded_sha256 = source_artifact["content_sha256"]
    source_reference = dict(provenance.source_reference_json or {})
    source_reference.update(
        {
            "accession_or_submission_id": live_acquisition_request["accession_or_submission_id"],
            "cik": str(live_acquisition_request["cik_or_filer_ref"]).lstrip("0") or "0",
            "form_type": live_acquisition_request["form_type"],
            "filing_date": live_acquisition_request["filing_date"],
            "content_length": source_artifact["content_length"],
            "source_artifact_receipt_id": source_artifact["source_artifact_receipt_id"],
            "source_artifact_receipt_hash": source_artifact["source_artifact_receipt_hash"],
            "source_artifact_ref_hash": source_artifact["source_artifact_ref_hash"],
        }
    )
    provenance.source_reference_json = source_reference
    db.commit()
    return dataset_version_id


def _sec_edgar_source_acquisition_payload_from_live(
    *,
    dataset_version_id: str,
    envelope: dict[str, Any],
    live_artifact: dict[str, Any],
    client_request_id: str,
) -> dict[str, object]:
    source_artifact = live_artifact["source_artifact_receipt"]
    source_identity = live_artifact["source_identity"]
    return {
        "schema_id": layer3_sec_edgar_source_acquisition.REQUEST_SCHEMA_ID,
        "client_request_id": client_request_id,
        "acquisition_mode": layer3_sec_edgar_source_acquisition.ACQUISITION_MODE,
        "operator_decision": layer3_sec_edgar_source_acquisition.OPERATOR_DECISION,
        "dataset_version_id": dataset_version_id,
        "source_artifact_receipt_id": source_artifact["source_artifact_receipt_id"],
        "source_artifact_receipt_hash": source_artifact["source_artifact_receipt_hash"],
        "source_artifact_ref_hash": source_artifact["source_artifact_ref_hash"],
        "accession_or_submission_id_hash": source_identity["accession_or_submission_id_hash"],
        "cik_or_filer_ref_hash": source_identity["cik_or_filer_ref_hash"],
        "form_type": source_identity["form_type"],
        "filing_date": source_identity["filing_date"],
        "content_sha256": source_artifact["content_sha256"],
        "content_length": source_artifact["content_length"],
        "parser_family": layer3_sec_edgar_source_acquisition.PARSER_FAMILY,
        "parser_contract_id": layer3_sec_edgar_source_acquisition.PARSER_CONTRACT_ID,
        "typed_content_contract_id": layer3_sec_edgar_source_acquisition.TYPED_CONTENT_CONTRACT_ID,
        "materialization_receipt_hash": envelope["materialization_receipt_hash"],
        "dataset_version_hash": envelope["dataset_version_hash"],
        "authority_envelope_hash": envelope["authority_envelope_hash"],
        "operator_confirmation": True,
    }


def _prepare_sec_edgar_source_acquisition_authority_fixture(
    db,
    temp_path: Path,
    *,
    seed_id: str,
) -> dict[str, object]:
    dataset_version_id = _seed_sec_edgar_browser_dataset_version(
        db,
        temp_path,
        dataset_version_id=f"dv-sec-edgar-source-acq-{seed_id}",
        parser_family="sec_edgar_filing",
        typed_content_contract_id="aps_sec_edgar_filing_units_v1",
        source_mode="artifact_sec_edgar_filing_parser",
        parser_contract_id="aps_sec_edgar_filing_parser_v1",
    )
    provenance = (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .one()
    )
    source_reference = dict(provenance.source_reference_json or {})
    source_reference.update(
        {
            "accession_or_submission_id": "0000320193-24-000123",
            "cik": "0000320193",
            "form_type": "10-K",
            "filing_date": "2024-11-01",
            "content_length": 91337,
        }
    )
    provenance.source_reference_json = source_reference
    db.commit()
    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    source_artifact_ref_hash = _sec_edgar_text_hash(provenance.source_artifact_key)
    source_artifact_receipt_id = f"sec-edgar-text-table-source-artifact-{source_artifact_ref_hash[:24]}"
    accession_hash = _sec_edgar_text_hash("0000320193-24-000123")
    cik_hash = _sec_edgar_text_hash("0000320193")
    source_artifact_receipt_hash = stable_hash(
        {
            "schema_id": layer3_sec_edgar_source_acquisition.SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID,
            "schema_version": layer3_sec_edgar_source_acquisition.SCHEMA_VERSION,
            "source_artifact_receipt_id": source_artifact_receipt_id,
            "dataset_version_id": dataset_version_id,
            "source_artifact_ref_hash": source_artifact_ref_hash,
            "content_sha256": provenance.downloaded_sha256,
            "content_length": 91337,
            "accession_or_submission_id_hash": accession_hash,
            "cik_or_filer_ref_hash": cik_hash,
            "form_type": "10-K",
            "filing_date": "2024-11-01",
            "parser_family": layer3_sec_edgar_source_acquisition.PARSER_FAMILY,
            "parser_contract_id": layer3_sec_edgar_source_acquisition.PARSER_CONTRACT_ID,
            "typed_content_contract_id": layer3_sec_edgar_source_acquisition.TYPED_CONTENT_CONTRACT_ID,
            "source_mode": layer3_sec_edgar_source_acquisition.SOURCE_MODE,
            "dataset_version_hash": envelope["dataset_version_hash"],
            "materialization_receipt_hash": envelope["materialization_receipt_hash"],
            "authority_envelope_hash": envelope["authority_envelope_hash"],
        }
    )
    source_acquisition_request = {
        "schema_id": layer3_sec_edgar_source_acquisition.REQUEST_SCHEMA_ID,
        "client_request_id": f"browser-sec-edgar-source-acq-{seed_id}",
        "acquisition_mode": layer3_sec_edgar_source_acquisition.ACQUISITION_MODE,
        "operator_decision": layer3_sec_edgar_source_acquisition.OPERATOR_DECISION,
        "dataset_version_id": dataset_version_id,
        "source_artifact_receipt_id": source_artifact_receipt_id,
        "source_artifact_receipt_hash": source_artifact_receipt_hash,
        "source_artifact_ref_hash": source_artifact_ref_hash,
        "accession_or_submission_id_hash": accession_hash,
        "cik_or_filer_ref_hash": cik_hash,
        "form_type": "10-K",
        "filing_date": "2024-11-01",
        "content_sha256": provenance.downloaded_sha256,
        "content_length": 91337,
        "parser_family": layer3_sec_edgar_source_acquisition.PARSER_FAMILY,
        "parser_contract_id": layer3_sec_edgar_source_acquisition.PARSER_CONTRACT_ID,
        "typed_content_contract_id": layer3_sec_edgar_source_acquisition.TYPED_CONTENT_CONTRACT_ID,
        "materialization_receipt_hash": envelope["materialization_receipt_hash"],
        "dataset_version_hash": envelope["dataset_version_hash"],
        "authority_envelope_hash": envelope["authority_envelope_hash"],
        "operator_confirmation": True,
    }
    return {
        "schema_id": "project6.review_browser_sec_edgar_source_acquisition_authority_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": dataset_version_id,
        "source_acquisition_request": source_acquisition_request,
        "stale_source_acquisition_request": {
            **source_acquisition_request,
            "source_artifact_receipt_hash": "f" * 64,
        },
        "expected_source_acquisition_receipt_hash": stable_hash(
            {
                "hash_version": "sec_edgar_text_table_source_acquisition_authority_hash_v1",
                "schema_id": layer3_sec_edgar_source_acquisition.SCHEMA_ID,
                "acquisition_mode": layer3_sec_edgar_source_acquisition.ACQUISITION_MODE,
                "operator_decision": layer3_sec_edgar_source_acquisition.OPERATOR_DECISION,
                "dataset_version_id": dataset_version_id,
                "dataset_version_hash": envelope["dataset_version_hash"],
                "materialization_receipt_hash": envelope["materialization_receipt_hash"],
                "authority_envelope_hash": envelope["authority_envelope_hash"],
                "source_artifact_receipt_hash": source_artifact_receipt_hash,
                "source_artifact_ref_hash": source_artifact_ref_hash,
                "parser_family": layer3_sec_edgar_source_acquisition.PARSER_FAMILY,
                "parser_contract_id": layer3_sec_edgar_source_acquisition.PARSER_CONTRACT_ID,
                "typed_content_contract_id": layer3_sec_edgar_source_acquisition.TYPED_CONTENT_CONTRACT_ID,
                "source_mode": layer3_sec_edgar_source_acquisition.SOURCE_MODE,
                "redaction_policy_id": layer3_sec_edgar_source_acquisition.REDACTION_POLICY_ID,
            }
        ),
        "source_acquisition_endpoint": "/api/v1/layer3/source/sec-edgar/text-table/source-acquisition/authority",
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _prepare_sec_edgar_downstream_status_fixture(db, temp_path: Path, *, seed_id: str) -> dict[str, object]:
    dataset_version_id = _seed_sec_edgar_browser_dataset_version(
        db,
        temp_path,
        dataset_version_id=f"dv-sec-edgar-status-{seed_id}",
        parser_family="sec_edgar_filing",
        typed_content_contract_id="aps_sec_edgar_filing_units_v1",
        source_mode="artifact_sec_edgar_filing_parser",
        parser_contract_id="aps_sec_edgar_filing_parser_v1",
    )
    db.commit()
    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    bridge = layer3_sec_edgar_material_bridge.prepare_sec_edgar_text_table_material_authority_bridge(
        {
            "client_request_id": f"browser-sec-edgar-status-bridge-{seed_id}",
            "bridge_mode": "sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1",
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": envelope["authority_envelope_hash"],
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    gate_b = layer3_workbench.gate_b_decision(db, dict(bridge["gate_b_decision_payload"]))
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == gate_b["session_id"])
        .filter(L3MaterialSnapshot.source_shape == "dataset_version")
        .all()
    )
    matches = [
        snapshot
        for snapshot in snapshots
        if (snapshot.source_identity_json or {}).get("dataset_version_id") == dataset_version_id
    ]
    if len(matches) != 1:
        raise RuntimeError("SEC EDGAR material snapshot was not created for browser fixture")
    snapshot = matches[0]
    proof_request = {
        "client_request_id": f"browser-sec-edgar-status-proof-{seed_id}",
        "proof_mode": "sec_edgar_text_table_downstream_layer3_e2e_proof_v1",
        "operator_decision": "record_sec_edgar_text_table_downstream_layer3_e2e_proof",
        "dataset_version_id": dataset_version_id,
        "authority_envelope_hash": bridge["authority_envelope_hash"],
        "bridge_receipt_hash": bridge["bridge_receipt_hash"],
        "material_preview_hash": bridge["material_preview_hash"],
        "gate_b_decision_manifest_id": bridge["gate_b_decision_manifest_id"],
        "session_id": gate_b["session_id"],
        "selection_manifest_id": gate_b["selection_manifest_id"],
        "material_snapshot_payload_hash": snapshot.payload_hash,
        "coverage_evidence": _sec_edgar_browser_coverage(bridge, gate_b, snapshot),
        "operator_confirmation": True,
    }
    proof = layer3_sec_edgar_downstream_proof.record_sec_edgar_text_table_downstream_layer3_proof(
        proof_request,
        db,
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_downstream_status_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": dataset_version_id,
        "downstream_proof_request": proof_request,
        "expected_proof_hash": proof["proof_hash"],
        "proof_hash": proof["proof_hash"],
        "status_endpoint": "/api/v1/layer3/source/sec-edgar/text-table/downstream-proof/status",
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _prepare_sec_edgar_live_downstream_status_fixture(
    db,
    temp_path: Path,
    *,
    fake_client: _ReviewBrowserSeededSecEdgarClient,
    seed_id: str,
) -> dict[str, object]:
    setup = _prepare_sec_edgar_live_source_artifact_acquisition_fixture(
        fake_client=fake_client,
        seed_id=seed_id,
    )
    live_acquisition_request = dict(setup["live_acquisition_request"])
    live_artifact = layer3_sec_edgar_live_source_artifact.acquire_sec_edgar_text_table_live_source_artifact(
        {
            "client_request_id": f"browser-sec-edgar-live-status-acq-{seed_id}",
            "acquisition_mode": layer3_sec_edgar_live_source_artifact.ACQUISITION_MODE,
            "operator_decision": layer3_sec_edgar_live_source_artifact.OPERATOR_DECISION,
            **live_acquisition_request,
            "operator_confirmation": True,
        }
    )
    dataset_version_id = _bind_sec_edgar_browser_dataset_to_live_source_artifact(
        db,
        temp_path,
        dataset_version_id=f"dv-sec-edgar-live-status-{seed_id}",
        live_artifact=live_artifact,
        live_acquisition_request=live_acquisition_request,
    )
    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    source_acquisition = layer3_sec_edgar_source_acquisition.record_sec_edgar_text_table_source_acquisition_authority(
        _sec_edgar_source_acquisition_payload_from_live(
            dataset_version_id=dataset_version_id,
            envelope=envelope,
            live_artifact=live_artifact,
            client_request_id=f"browser-sec-edgar-live-status-source-acq-{seed_id}",
        ),
        db,
    )
    bridge = layer3_sec_edgar_live_material_bridge.prepare_sec_edgar_text_table_live_source_artifact_material_authority_bridge(
        {
            "client_request_id": f"browser-sec-edgar-live-status-bridge-{seed_id}",
            "bridge_mode": layer3_sec_edgar_live_material_bridge.BRIDGE_MODE,
            "live_source_artifact_receipt_id": live_artifact["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": live_artifact["live_source_artifact_receipt_hash"],
            "source_acquisition_receipt_id": source_acquisition["source_acquisition_receipt_id"],
            "source_acquisition_receipt_hash": source_acquisition["source_acquisition_receipt_hash"],
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": envelope["authority_envelope_hash"],
            "expected_materialization_receipt_hash": envelope["materialization_receipt_hash"],
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    gate_b = layer3_workbench.gate_b_decision(db, dict(bridge["gate_b_decision_payload"]))
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == gate_b["session_id"])
        .filter(L3MaterialSnapshot.source_shape == "dataset_version")
        .all()
    )
    matches = [
        snapshot
        for snapshot in snapshots
        if (snapshot.source_identity_json or {}).get("dataset_version_id") == dataset_version_id
    ]
    if len(matches) != 1:
        raise RuntimeError("SEC EDGAR live material snapshot was not created for browser fixture")
    snapshot = matches[0]
    material_bridge_receipt_hash = bridge["authority_hashes"]["material_bridge_receipt_hash"]
    coverage_bridge = {
        **bridge,
        "authority_envelope_hash": bridge["authority_hashes"]["authority_envelope_hash"],
        "bridge_receipt_hash": material_bridge_receipt_hash,
    }
    coverage = _sec_edgar_browser_coverage(coverage_bridge, gate_b, snapshot)
    for step, extra in {
        "live_source_artifact_acquisition": {
            "live_source_artifact_receipt_hash": live_artifact["live_source_artifact_receipt_hash"],
            "server_receipt_id": live_artifact["live_source_artifact_receipt_id"],
        },
        "source_acquisition_authority": {
            "source_acquisition_receipt_hash": source_acquisition["source_acquisition_receipt_hash"],
            "server_receipt_id": source_acquisition["source_acquisition_receipt_id"],
        },
        "live_material_authority_bridge": {
            "live_source_artifact_material_bridge_receipt_hash": bridge["bridge_receipt_hash"],
            "server_receipt_id": bridge["bridge_receipt_id"],
            "material_bridge_receipt_hash": material_bridge_receipt_hash,
            "material_preview_hash": bridge["material_preview_hash"],
            "gate_b_decision_manifest_id": bridge["gate_b_decision_manifest_id"],
        },
    }.items():
        coverage[step] = {
            "status": "proven",
            "evidence_ref": f"sec-edgar-live-source-artifact-downstream-proof:{step}",
            "evidence_hash": stable_hash({"step": step, "seed_id": seed_id}),
            "server_response_hash": stable_hash({"response": step, "seed_id": seed_id}),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
            **extra,
        }
    proof_request = {
        "client_request_id": f"browser-sec-edgar-live-status-proof-{seed_id}",
        "proof_mode": layer3_sec_edgar_live_downstream_proof.PROOF_MODE,
        "operator_decision": layer3_sec_edgar_live_downstream_proof.OPERATOR_DECISION,
        "live_source_artifact_receipt_id": live_artifact["live_source_artifact_receipt_id"],
        "live_source_artifact_receipt_hash": live_artifact["live_source_artifact_receipt_hash"],
        "source_acquisition_receipt_id": source_acquisition["source_acquisition_receipt_id"],
        "source_acquisition_receipt_hash": source_acquisition["source_acquisition_receipt_hash"],
        "dataset_version_id": dataset_version_id,
        "authority_envelope_hash": bridge["authority_hashes"]["authority_envelope_hash"],
        "live_source_artifact_material_bridge_receipt_id": bridge["bridge_receipt_id"],
        "live_source_artifact_material_bridge_receipt_hash": bridge["bridge_receipt_hash"],
        "material_bridge_receipt_hash": material_bridge_receipt_hash,
        "material_preview_hash": bridge["material_preview_hash"],
        "gate_b_decision_manifest_id": bridge["gate_b_decision_manifest_id"],
        "session_id": gate_b["session_id"],
        "selection_manifest_id": gate_b["selection_manifest_id"],
        "material_snapshot_payload_hash": snapshot.payload_hash,
        "coverage_evidence": coverage,
        "operator_confirmation": True,
    }
    proof = layer3_sec_edgar_live_downstream_proof.record_sec_edgar_text_table_live_source_artifact_downstream_layer3_proof(
        proof_request,
        db,
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_live_downstream_status_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": dataset_version_id,
        "live_source_artifact_receipt_hash": live_artifact["live_source_artifact_receipt_hash"],
        "source_acquisition_receipt_hash": source_acquisition["source_acquisition_receipt_hash"],
        "live_source_artifact_material_bridge_receipt_hash": bridge["bridge_receipt_hash"],
        "material_bridge_receipt_hash": material_bridge_receipt_hash,
        "live_downstream_proof_request": proof_request,
        "expected_proof_hash": proof["proof_hash"],
        "proof_hash": proof["proof_hash"],
        "status_endpoint": (
            "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/downstream-proof/status"
        ),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _sec_edgar_real_filing_submissions_payload() -> bytes:
    return json.dumps(
        {
            "name": "Apple Inc.",
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "8-K"],
                    "accessionNumber": [
                        "0000320193-24-000123",
                        "0000320193-24-000124",
                        "0000320193-24-000125",
                    ],
                    "filingDate": ["2024-11-01", "2024-08-02", "2024-05-02"],
                    "reportDate": ["2024-09-28", "2024-06-29", "2024-05-01"],
                    "primaryDocument": [
                        "aapl-20240928.htm",
                        "aapl-20240629.htm",
                        "aapl-20240502.htm",
                    ],
                    "primaryDocDescription": ["10-K", "10-Q", "8-K"],
                }
            },
        },
        sort_keys=True,
    ).encode("utf-8")


def _sec_edgar_html_inline_xbrl_submission_text() -> bytes:
    return b"""<SEC-DOCUMENT>
<SEC-HEADER>
<ACCESSION-NUMBER>0000320193-24-000123
<CONFORMED-SUBMISSION-TYPE>10-K
</SEC-HEADER>
<DOCUMENT>
<TYPE>10-K
<SEQUENCE>1
<FILENAME>aapl-20240928.htm
<DESCRIPTION>10-K
<TEXT>
<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
<body>
<h1>Item 1. Business</h1>
<p>Company narrative in source order.</p>
<ix:nonFraction name="us-gaap:Assets" contextRef="c1">123</ix:nonFraction>
<table><tr><td>Cash</td><td>123</td></tr></table>
</body>
</html>
</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-99
<SEQUENCE>2
<FILENAME>exhibit99.htm
<DESCRIPTION>EXHIBIT
<TEXT><html><body><p>Exhibit text</p></body></html></TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""


def _sec_edgar_html_inline_xbrl_coverage(
    parser: dict[str, object],
    bridge: dict[str, object],
    gate_b: dict[str, object],
    snapshot: L3MaterialSnapshot,
) -> dict[str, dict[str, object]]:
    authority_hashes = bridge["authority_hashes"]
    primary_document_hash = next(
        str(item["filename_hash"])
        for item in parser["document_inventory"]
        if item.get("primary_document_match") is True
    )
    required = set(layer3_sec_edgar_html_inline_xbrl_downstream_proof.REQUIRED_COVERAGE)
    coverage: dict[str, dict[str, object]] = {}
    for step in required:
        item: dict[str, object] = {
            "status": "proven",
            "evidence_ref": f"sec-edgar-html-inline-xbrl-downstream-proof:{step}",
            "evidence_hash": stable_hash({"step": step, "session_id": gate_b["session_id"]}),
            "server_response_hash": stable_hash({"response": step, "session_id": gate_b["session_id"]}),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        }
        if step not in {
            "real_filing_connector_acquisition",
            "live_source_artifact_acquisition",
            "html_inline_xbrl_source_family_parser",
            "html_inline_xbrl_material_authority_bridge",
        }:
            item["session_id"] = gate_b["session_id"]
        if step == "real_filing_connector_acquisition":
            item["connector_receipt_hash"] = parser["connector_receipt_hash"]
        if step == "live_source_artifact_acquisition":
            item["live_source_artifact_receipt_hash"] = parser["live_source_artifact_receipt_hash"]
            item["source_artifact_receipt_hash"] = parser["source_artifact_receipt_hash"]
        if step == "html_inline_xbrl_source_family_parser":
            item["parser_receipt_hash"] = parser["parser_receipt_hash"]
            item["content_sha256"] = authority_hashes["content_sha256"]
            item["primary_document_hash"] = primary_document_hash
            item["content_order_hash"] = parser["content_order_hash"]
        if step == "html_inline_xbrl_material_authority_bridge":
            item["material_bridge_receipt_hash"] = bridge["bridge_receipt_hash"]
            item["bridge_receipt_hash"] = bridge["bridge_receipt_hash"]
            item["material_preview_hash"] = bridge["material_preview_hash"]
            item["gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
        if step == "gate_b_commit":
            item["material_preview_hash"] = bridge["material_preview_hash"]
            item["gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
            item["selection_manifest_id"] = gate_b["selection_manifest_id"]
            item["material_snapshot_payload_hash"] = snapshot.payload_hash
        coverage[step] = item
    return coverage


def _prepare_sec_edgar_html_inline_xbrl_downstream_status_fixture(
    db,
    *,
    fake_client: _ReviewBrowserSeededSecEdgarClient,
    seed_id: str,
) -> dict[str, object]:
    _reset_sec_edgar_live_source_artifact_rate_marker()
    fake_client.register_complete_submission_text(
        url="https://data.sec.gov/submissions/CIK0000320193.json",
        content=_sec_edgar_real_filing_submissions_payload(),
    )
    fake_client.register_complete_submission_text(
        url=(
            "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/"
            "0000320193-24-000123.txt"
        ),
        content=_sec_edgar_html_inline_xbrl_submission_text(),
    )
    connector = layer3_sec_edgar_real_filing_acquisition_connector.acquire_sec_edgar_real_filing_validation_corpus(
        {
            "client_request_id": f"browser-sec-edgar-html-inline-xbrl-connector-{seed_id}",
            "connector_mode": layer3_sec_edgar_real_filing_acquisition_connector.CONNECTOR_MODE,
            "operator_decision": layer3_sec_edgar_real_filing_acquisition_connector.OPERATOR_DECISION,
            "example_set_mode": layer3_sec_edgar_real_filing_acquisition_connector.EXAMPLE_SET_MODE,
            "cik_refs": ["0000320193"],
            "form_types": ["10-K"],
            "operator_confirmation": True,
        }
    )
    acquisition = connector["acquisition_receipts"][0]
    parser = layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
        {
            "client_request_id": f"browser-sec-edgar-html-inline-xbrl-parser-{seed_id}",
            "parser_mode": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_parser.OPERATOR_DECISION,
            "connector_receipt_id": connector["connector_receipt_id"],
            "connector_receipt_hash": connector["connector_receipt_hash"],
            "connector_example_id": acquisition["example_id"],
            "live_source_artifact_receipt_id": acquisition["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": acquisition["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": acquisition["source_artifact_receipt"][
                "source_artifact_receipt_hash"
            ],
            "operator_confirmation": True,
        }
    )
    bridge = layer3_sec_edgar_html_inline_xbrl_material_bridge.prepare_sec_edgar_html_inline_xbrl_material_bridge(
        {
            "client_request_id": f"browser-sec-edgar-html-inline-xbrl-bridge-{seed_id}",
            "bridge_mode": layer3_sec_edgar_html_inline_xbrl_material_bridge.BRIDGE_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_material_bridge.OPERATOR_DECISION,
            "parser_receipt_id": parser["parser_receipt_id"],
            "parser_receipt_hash": parser["parser_receipt_hash"],
            "expected_connector_receipt_hash": parser["connector_receipt_hash"],
            "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    gate_b = layer3_workbench.gate_b_decision(db, dict(bridge["gate_b_decision_payload"]))
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == gate_b["session_id"])
        .filter(L3MaterialSnapshot.source_shape == "dataset_version")
        .all()
    )
    matches = [
        snapshot
        for snapshot in snapshots
        if (snapshot.source_identity_json or {}).get("dataset_version_id") == bridge["dataset_version_id"]
    ]
    if len(matches) != 1:
        raise RuntimeError("SEC EDGAR HTML/iXBRL material snapshot was not created for browser fixture")
    snapshot = matches[0]
    proof_request = {
        "client_request_id": f"browser-sec-edgar-html-inline-xbrl-proof-{seed_id}",
        "proof_mode": layer3_sec_edgar_html_inline_xbrl_downstream_proof.PROOF_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_downstream_proof.OPERATOR_DECISION,
        "parser_receipt_id": parser["parser_receipt_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "material_bridge_receipt_id": bridge["bridge_receipt_id"],
        "material_bridge_receipt_hash": bridge["bridge_receipt_hash"],
        "dataset_version_id": bridge["dataset_version_id"],
        "material_preview_hash": bridge["material_preview_hash"],
        "gate_b_decision_manifest_id": bridge["gate_b_decision_manifest_id"],
        "session_id": gate_b["session_id"],
        "selection_manifest_id": gate_b["selection_manifest_id"],
        "material_snapshot_payload_hash": snapshot.payload_hash,
        "coverage_evidence": _sec_edgar_html_inline_xbrl_coverage(parser, bridge, gate_b, snapshot),
        "operator_confirmation": True,
    }
    proof = layer3_sec_edgar_html_inline_xbrl_downstream_proof.record_sec_edgar_html_inline_xbrl_downstream_layer3_proof(
        proof_request,
        db,
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_html_inline_xbrl_downstream_status_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": bridge["dataset_version_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "connector_receipt_hash": parser["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "material_bridge_receipt_hash": bridge["bridge_receipt_hash"],
        "material_preview_hash": bridge["material_preview_hash"],
        "html_inline_xbrl_downstream_proof_request": proof_request,
        "expected_proof_hash": proof["proof_hash"],
        "proof_hash": proof["proof_hash"],
        "status_endpoint": "/api/v1/layer3/source/sec-edgar/html-inline-xbrl/downstream-proof/status",
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _sec_edgar_html_inline_xbrl_fact_material_coverage(
    parser: dict[str, object],
    fact_authority: dict[str, object],
    bridge: dict[str, object],
    gate_b: dict[str, object],
    snapshot: L3MaterialSnapshot,
) -> dict[str, dict[str, object]]:
    authority_hashes = bridge["authority_hashes"]
    primary_document_hash = next(
        str(item["filename_hash"])
        for item in parser["document_inventory"]
        if item.get("primary_document_match") is True
    )
    required = set(layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof.REQUIRED_COVERAGE)
    coverage: dict[str, dict[str, object]] = {}
    for step in required:
        item: dict[str, object] = {
            "status": "proven",
            "evidence_ref": f"sec-edgar-html-inline-xbrl-fact-material-downstream-proof:{step}",
            "evidence_hash": stable_hash({"fact-step": step, "session_id": gate_b["session_id"]}),
            "server_response_hash": stable_hash({"fact-response": step, "session_id": gate_b["session_id"]}),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
            "raw_fact_values_exposed_in_operator_projection": False,
            "fact_value_reconstruction_admitted_in_proof": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        }
        if step not in {
            "real_filing_connector_acquisition",
            "live_source_artifact_acquisition",
            "html_inline_xbrl_source_family_parser",
            "html_inline_xbrl_fact_authority",
            "html_inline_xbrl_fact_material_authority_bridge",
        }:
            item["session_id"] = gate_b["session_id"]
        if step == "real_filing_connector_acquisition":
            item["connector_receipt_hash"] = parser["connector_receipt_hash"]
        if step == "live_source_artifact_acquisition":
            item["live_source_artifact_receipt_hash"] = parser["live_source_artifact_receipt_hash"]
            item["source_artifact_receipt_hash"] = parser["source_artifact_receipt_hash"]
        if step == "html_inline_xbrl_source_family_parser":
            item["parser_receipt_hash"] = parser["parser_receipt_hash"]
            item["content_sha256"] = authority_hashes["content_sha256"]
            item["primary_document_hash"] = primary_document_hash
            item["content_order_hash"] = parser["content_order_hash"]
        if step == "html_inline_xbrl_fact_authority":
            item["fact_authority_receipt_hash"] = fact_authority["fact_authority_receipt_hash"]
            item["fact_inventory_hash"] = fact_authority["fact_inventory_hash"]
            item["diagnostics_hash"] = fact_authority["diagnostics_hash"]
        if step == "html_inline_xbrl_fact_material_authority_bridge":
            item["fact_material_bridge_receipt_hash"] = bridge["fact_material_bridge_receipt_hash"]
            item["bridge_receipt_hash"] = bridge["bridge_receipt_hash"]
            item["material_preview_hash"] = bridge["material_preview_hash"]
            item["gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
        if step == "gate_b_commit":
            item["material_preview_hash"] = bridge["material_preview_hash"]
            item["gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
            item["selection_manifest_id"] = gate_b["selection_manifest_id"]
            item["material_snapshot_payload_hash"] = snapshot.payload_hash
        coverage[step] = item
    return coverage


def _prepare_sec_edgar_html_inline_xbrl_fact_material_downstream_status_fixture(
    db,
    *,
    fake_client: _ReviewBrowserSeededSecEdgarClient,
    seed_id: str,
) -> dict[str, object]:
    _reset_sec_edgar_live_source_artifact_rate_marker()
    fake_client.register_complete_submission_text(
        url="https://data.sec.gov/submissions/CIK0000320193.json",
        content=_sec_edgar_real_filing_submissions_payload(),
    )
    fake_client.register_complete_submission_text(
        url=(
            "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/"
            "0000320193-24-000123.txt"
        ),
        content=_sec_edgar_html_inline_xbrl_submission_text(),
    )
    connector = layer3_sec_edgar_real_filing_acquisition_connector.acquire_sec_edgar_real_filing_validation_corpus(
        {
            "client_request_id": f"browser-sec-edgar-html-inline-xbrl-fact-material-connector-{seed_id}",
            "connector_mode": layer3_sec_edgar_real_filing_acquisition_connector.CONNECTOR_MODE,
            "operator_decision": layer3_sec_edgar_real_filing_acquisition_connector.OPERATOR_DECISION,
            "example_set_mode": layer3_sec_edgar_real_filing_acquisition_connector.EXAMPLE_SET_MODE,
            "cik_refs": ["0000320193"],
            "form_types": ["10-K"],
            "operator_confirmation": True,
        }
    )
    acquisition = connector["acquisition_receipts"][0]
    parser = layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
        {
            "client_request_id": f"browser-sec-edgar-html-inline-xbrl-fact-material-parser-{seed_id}",
            "parser_mode": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_parser.OPERATOR_DECISION,
            "connector_receipt_id": connector["connector_receipt_id"],
            "connector_receipt_hash": connector["connector_receipt_hash"],
            "connector_example_id": acquisition["example_id"],
            "live_source_artifact_receipt_id": acquisition["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": acquisition["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": acquisition["source_artifact_receipt"][
                "source_artifact_receipt_hash"
            ],
            "operator_confirmation": True,
        }
    )
    fact_authority = layer3_sec_edgar_html_inline_xbrl_fact_authority.derive_sec_edgar_html_inline_xbrl_fact_authority(
        {
            "client_request_id": f"browser-sec-edgar-html-inline-xbrl-fact-authority-{seed_id}",
            "fact_authority_mode": layer3_sec_edgar_html_inline_xbrl_fact_authority.FACT_AUTHORITY_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_authority.OPERATOR_DECISION,
            "parser_receipt_id": parser["parser_receipt_id"],
            "parser_receipt_hash": parser["parser_receipt_hash"],
            "expected_connector_receipt_hash": parser["connector_receipt_hash"],
            "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
            "expected_content_sha256": parser["identity_binding"]["content_sha256"],
            "expected_primary_document_hash": parser["identity_binding"]["primary_document_hash"],
            "expected_document_inventory_hash": parser["document_inventory_hash"],
            "expected_content_order_hash": parser["content_order_hash"],
            "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
            "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
            "operator_confirmation": True,
        }
    )
    original_cutover_enabled = settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled
    settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = False
    try:
        bridge = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
            {
                "client_request_id": f"browser-sec-edgar-html-inline-xbrl-fact-material-bridge-{seed_id}",
                "bridge_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE,
                "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.OPERATOR_DECISION,
                "fact_authority_receipt_id": fact_authority["fact_authority_receipt_id"],
                "fact_authority_receipt_hash": fact_authority["fact_authority_receipt_hash"],
                "parser_receipt_id": parser["parser_receipt_id"],
                "parser_receipt_hash": parser["parser_receipt_hash"],
                "expected_connector_receipt_hash": parser["connector_receipt_hash"],
                "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
                "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
                "expected_content_sha256": parser["identity_binding"]["content_sha256"],
                "expected_primary_document_hash": parser["identity_binding"]["primary_document_hash"],
                "expected_document_inventory_hash": parser["document_inventory_hash"],
                "expected_content_order_hash": parser["content_order_hash"],
                "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
                "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
                "expected_fact_inventory_hash": fact_authority["fact_inventory_hash"],
                "expected_diagnostics_hash": fact_authority["diagnostics_hash"],
                "rollback_confirmed": True,
                "operator_confirmed": True,
            },
            db,
        )
    finally:
        settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = original_cutover_enabled
    gate_b = layer3_workbench.gate_b_decision(db, dict(bridge["gate_b_decision_payload"]))
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == gate_b["session_id"])
        .filter(L3MaterialSnapshot.source_shape == "dataset_version")
        .all()
    )
    matches = [
        snapshot
        for snapshot in snapshots
        if (snapshot.source_identity_json or {}).get("dataset_version_id") == bridge["dataset_version_id"]
    ]
    if len(matches) != 1:
        raise RuntimeError("SEC EDGAR HTML/iXBRL fact-material snapshot was not created for browser fixture")
    snapshot = matches[0]
    proof_request = {
        "client_request_id": f"browser-sec-edgar-html-inline-xbrl-fact-material-proof-{seed_id}",
        "proof_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof.PROOF_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof.OPERATOR_DECISION,
        "parser_receipt_id": parser["parser_receipt_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "fact_authority_receipt_id": fact_authority["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": fact_authority["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_id": bridge["fact_material_bridge_receipt_id"],
        "fact_material_bridge_receipt_hash": bridge["fact_material_bridge_receipt_hash"],
        "dataset_version_id": bridge["dataset_version_id"],
        "material_preview_hash": bridge["material_preview_hash"],
        "gate_b_decision_manifest_id": bridge["gate_b_decision_manifest_id"],
        "session_id": gate_b["session_id"],
        "selection_manifest_id": gate_b["selection_manifest_id"],
        "material_snapshot_payload_hash": snapshot.payload_hash,
        "coverage_evidence": _sec_edgar_html_inline_xbrl_fact_material_coverage(
            parser,
            fact_authority,
            bridge,
            gate_b,
            snapshot,
        ),
        "operator_confirmation": True,
    }
    proof = (
        layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof
        .record_sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_proof(
            proof_request,
            db,
        )
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_html_inline_xbrl_fact_material_downstream_status_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": bridge["dataset_version_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "connector_receipt_hash": parser["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "fact_authority_receipt_hash": fact_authority["fact_authority_receipt_hash"],
        "fact_inventory_hash": fact_authority["fact_inventory_hash"],
        "diagnostics_hash": fact_authority["diagnostics_hash"],
        "fact_material_bridge_receipt_hash": bridge["fact_material_bridge_receipt_hash"],
        "material_bridge_receipt_hash": bridge["bridge_receipt_hash"],
        "material_preview_hash": bridge["material_preview_hash"],
        "fact_material_downstream_proof_request": proof_request,
        "expected_proof_hash": proof["proof_hash"],
        "proof_hash": proof["proof_hash"],
        "status_endpoint": (
            "/api/v1/layer3/source/sec-edgar/html-inline-xbrl/"
            "fact-authority/material-bridge/downstream-proof/status"
        ),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_rendered": False,
        "fact_value_reconstruction_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def _prepare_sec_edgar_html_inline_xbrl_fact_material_repeatability_trial_fixture(
    db,
    *,
    fake_client: _ReviewBrowserSeededSecEdgarClient,
    seed_id: str,
) -> dict[str, object]:
    status_fixture = _prepare_sec_edgar_html_inline_xbrl_fact_material_downstream_status_fixture(
        db,
        fake_client=fake_client,
        seed_id=seed_id,
    )
    original_status_request = {
        "client_request_id": f"review-browser-sec-edgar-html-inline-xbrl-fact-material-repeatability-original-{seed_id}",
        "status_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status.STATUS_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status.OPERATOR_DECISION,
        "fact_material_downstream_proof_request": status_fixture["fact_material_downstream_proof_request"],
        "expected_proof_hash": status_fixture["expected_proof_hash"],
    }
    repeat_status_request = {
        **original_status_request,
        "client_request_id": f"review-browser-sec-edgar-html-inline-xbrl-fact-material-repeatability-repeat-{seed_id}",
    }
    original_status = (
        layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status
        .inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status(
            original_status_request,
            db,
        )
    )
    repeat_status = (
        layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status
        .inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status(
            repeat_status_request,
            db,
        )
    )
    return {
        "schema_id": (
            "project6.review_browser_sec_edgar_html_inline_xbrl_fact_material_repeatability_trial_setup.v1"
        ),
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": status_fixture["dataset_version_id"],
        "parser_receipt_hash": status_fixture["parser_receipt_hash"],
        "connector_receipt_hash": status_fixture["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": status_fixture["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": status_fixture["source_artifact_receipt_hash"],
        "fact_authority_receipt_hash": status_fixture["fact_authority_receipt_hash"],
        "fact_inventory_hash": status_fixture["fact_inventory_hash"],
        "diagnostics_hash": status_fixture["diagnostics_hash"],
        "fact_material_bridge_receipt_hash": status_fixture["fact_material_bridge_receipt_hash"],
        "material_bridge_receipt_hash": status_fixture["material_bridge_receipt_hash"],
        "proof_hash": status_fixture["proof_hash"],
        "original_operator_status_request": original_status_request,
        "original_operator_status_hash": original_status["operator_status_hash"],
        "repeat_operator_status_request": repeat_status_request,
        "repeat_operator_status_hash": repeat_status["operator_status_hash"],
        "trial_endpoint": (
            "/api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/"
            "downstream-proof/operator-repeatability/trial"
        ),
        "status_endpoint": status_fixture["status_endpoint"],
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_rendered": False,
        "fact_value_reconstruction_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def _prepare_sec_edgar_live_repeatability_trial_fixture(
    db,
    temp_path: Path,
    *,
    fake_client: _ReviewBrowserSeededSecEdgarClient,
    seed_id: str,
) -> dict[str, object]:
    status_fixture = _prepare_sec_edgar_live_downstream_status_fixture(
        db,
        temp_path,
        fake_client=fake_client,
        seed_id=seed_id,
    )
    original_status_request = {
        "client_request_id": f"review-browser-sec-edgar-live-repeatability-original-{seed_id}",
        "status_mode": layer3_sec_edgar_live_downstream_status.STATUS_MODE,
        "operator_decision": layer3_sec_edgar_live_downstream_status.OPERATOR_DECISION,
        "live_downstream_proof_request": status_fixture["live_downstream_proof_request"],
        "expected_proof_hash": status_fixture["expected_proof_hash"],
    }
    repeat_status_request = {
        **original_status_request,
        "client_request_id": f"review-browser-sec-edgar-live-repeatability-repeat-{seed_id}",
    }
    original_status = (
        layer3_sec_edgar_live_downstream_status
        .inspect_sec_edgar_text_table_live_source_artifact_downstream_operator_status(
            original_status_request,
            db,
        )
    )
    repeat_status = (
        layer3_sec_edgar_live_downstream_status
        .inspect_sec_edgar_text_table_live_source_artifact_downstream_operator_status(
            repeat_status_request,
            db,
        )
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_live_repeatability_trial_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": status_fixture["dataset_version_id"],
        "live_source_artifact_receipt_hash": status_fixture["live_source_artifact_receipt_hash"],
        "source_acquisition_receipt_hash": status_fixture["source_acquisition_receipt_hash"],
        "live_source_artifact_material_bridge_receipt_hash": (
            status_fixture["live_source_artifact_material_bridge_receipt_hash"]
        ),
        "material_bridge_receipt_hash": status_fixture["material_bridge_receipt_hash"],
        "proof_hash": status_fixture["proof_hash"],
        "original_operator_status_request": original_status_request,
        "original_operator_status_hash": original_status["operator_status_hash"],
        "repeat_operator_status_request": repeat_status_request,
        "repeat_operator_status_hash": repeat_status["operator_status_hash"],
        "trial_endpoint": (
            "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/downstream/"
            "operator-repeatability/trial"
        ),
        "status_endpoint": status_fixture["status_endpoint"],
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _prepare_sec_edgar_repeatability_trial_fixture(db, temp_path: Path, *, seed_id: str) -> dict[str, object]:
    status_fixture = _prepare_sec_edgar_downstream_status_fixture(db, temp_path, seed_id=seed_id)
    original_status_request = {
        "client_request_id": f"review-browser-sec-edgar-repeatability-original-{seed_id}",
        "status_mode": "sec_edgar_text_table_downstream_layer3_operator_status_v1",
        "operator_decision": "inspect_sec_edgar_text_table_downstream_layer3_operator_status",
        "downstream_proof_request": status_fixture["downstream_proof_request"],
        "expected_proof_hash": status_fixture["expected_proof_hash"],
    }
    repeat_status_request = {
        **original_status_request,
        "client_request_id": f"review-browser-sec-edgar-repeatability-repeat-{seed_id}",
    }
    original_status = layer3_sec_edgar_downstream_status.inspect_sec_edgar_text_table_downstream_layer3_operator_status(
        original_status_request,
        db,
    )
    repeat_status = layer3_sec_edgar_downstream_status.inspect_sec_edgar_text_table_downstream_layer3_operator_status(
        repeat_status_request,
        db,
    )
    return {
        "schema_id": "project6.review_browser_sec_edgar_repeatability_trial_setup.v1",
        "schema_version": 1,
        "test_only": True,
        "dataset_version_id": status_fixture["dataset_version_id"],
        "original_operator_status_request": original_status_request,
        "original_operator_status_hash": original_status["operator_status_hash"],
        "repeat_operator_status_request": repeat_status_request,
        "repeat_operator_status_hash": repeat_status["operator_status_hash"],
        "trial_endpoint": "/api/v1/layer3/source/sec-edgar/text-table/downstream/operator-repeatability/trial",
        "status_endpoint": status_fixture["status_endpoint"],
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "frontend_durable_authority_enabled": False,
    }


def _write_browser_storage_ref(ref: str, content: str) -> tuple[str, str]:
    path = Path(settings.storage_dir) / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ref, hashlib.sha256(path.read_bytes()).hexdigest()


def _browser_materialized_dataset_entry(
    *,
    seed_id: str,
    corpus_batch_id: str,
    run_id: str,
    target_id: str,
    content_id: str,
    index: int,
) -> dict[str, object]:
    dataset_version_id = f"dv-materialized-{seed_id}-{index + 1}"
    dataset_id = f"ds-materialized-{seed_id}-{index + 1}"
    rows = [
        {
            "dataset_row_id": f"row-materialized-{seed_id}-{index + 1}-{row_index + 1}",
            "row_number": row_index + 1,
            "values_json": {
                "period": f"2026-{row_index + 1:02d}",
                "value": 10 + index + (row_index * 0.5),
            },
        }
        for row_index in range(24)
    ]
    csv_rows = "\n".join(f"{row['values_json']['period']},{row['values_json']['value']}" for row in rows)
    storage_ref, storage_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/dataset-{index + 1}.csv",
        f"period,value\n{csv_rows}\n",
    )
    value_variable_id = f"var-materialized-value-{seed_id}-{index + 1}"
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "name": f"Browser Raw Materialized Dataset {index + 1}",
        "description": "Deterministic browser harness materialized dataset.",
        "domain_pack": "nrc_aps",
        "frequency_hint": "monthly",
        "time_column": "period",
        "version_label": "v1",
        "version_type": "raw_mixed_materialized",
        "status": "ready",
        "storage_ref": storage_ref,
        "storage_sha256": storage_hash,
        "row_count": 24,
        "variables": [
            {
                "variable_id": f"var-materialized-period-{seed_id}-{index + 1}",
                "variable_name": "period",
                "dtype": "string",
                "role": "time",
                "is_numeric": False,
                "is_time_index": True,
                "ordinal_position": 0,
            },
            {
                "variable_id": value_variable_id,
                "variable_name": "value",
                "dtype": "float",
                "role": "measure",
                "is_numeric": True,
                "is_time_index": False,
                "ordinal_position": 1,
            },
        ],
        "rows": rows,
        "variable_profiles": [
            {
                "variable_profile_id": f"profile-materialized-value-{seed_id}-{index + 1}",
                "variable_id": value_variable_id,
                "seasonality_flag": False,
                "stationarity_hint": "not_evaluated",
                "summary_json": {"min": 10 + index, "max": 21.5 + index},
            }
        ],
        "source_provenance": {
            "dataset_source_provenance_id": f"prov-materialized-{seed_id}-{index + 1}",
            "source_system": "local_operator_staged_server_owned_manifest",
            "source_mode": "raw_mixed_materialized",
            "source_artifact_key": f"aps://{run_id}/{target_id}/{dataset_version_id}",
            "artifact_locator_type": "server_owned_ref",
            "fetch_policy_mode": "server_owned_manifest",
            "source_reference_json": {
                "content_id": content_id,
                "parser_family": "csv_table",
                "parser_contract_id": "aps_csv_parser_v1",
                "typed_content_contract_id": "aps_csv_table_units_v1",
            },
        },
    }


def _build_browser_raw_mixed_materialization_setup(*, seed_id: str) -> dict[str, object]:
    corpus_batch_id = f"batch-materialized-{seed_id}"
    run_id = f"run-materialized-{seed_id}"
    target_id = f"target-materialized-{seed_id}"
    content_id = f"content-materialized-{seed_id}"
    normalized_text = "Browser materialized APS content confirms inspection follow-up."
    normalized_ref, normalized_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-normalized.txt",
        normalized_text,
    )
    content_units_ref, _content_units_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-content-units.json",
        json.dumps(
            [
                {"unit_id": "unit-001", "text": "Browser materialized APS content confirms inspection."},
                {"unit_id": "unit-002", "text": "Follow-up is recorded for rendered selection proof."},
            ],
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    blob_ref, blob_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-source.txt",
        "browser raw materialization source bytes",
    )
    chunk_texts = [
        "Browser materialized APS content confirms inspection.",
        "Follow-up is recorded for rendered selection proof.",
    ]
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": corpus_batch_id,
        "source_classes": ["dataset_version", "aps_content_document"],
        "dataset_versions": [
            _browser_materialized_dataset_entry(
                seed_id=seed_id,
                corpus_batch_id=corpus_batch_id,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
                index=index,
            )
            for index in range(2)
        ],
        "aps_content_documents": [
            {
                "connector_run": {
                    "connector_run_id": run_id,
                    "source_system": "local_operator_staged_server_owned_manifest",
                    "source_mode": "server_owned_manifest",
                    "status": "completed",
                    "request_config_json": {"fixture": "browser_raw_mixed_materialization"},
                    "query_plan_json": {"corpus_batch_id": corpus_batch_id},
                },
                "target": {
                    "connector_run_target_id": target_id,
                    "connector_run_id": run_id,
                    "ordinal": 0,
                    "artifact_surface": "files",
                    "selection_source": "browser_materialization_manifest",
                    "selection_scope": "single_aps_document",
                    "artifact_locator_type": "server_owned_ref",
                    "source_artifact_key": f"aps://{run_id}/{target_id}/{content_id}",
                    "canonical_artifact_key": f"aps://{run_id}/{target_id}/canonical",
                    "downloaded_sha256": blob_hash,
                    "raw_storage_ref": blob_ref,
                    "fetch_policy_mode": "server_owned_manifest",
                    "status": "completed",
                },
                "document": {
                    "aps_content_document_id": f"aps-doc-materialized-{seed_id}",
                    "content_id": content_id,
                    "content_contract_id": APS_CONTENT_CONTRACT_ID,
                    "chunking_contract_id": APS_CHUNKING_CONTRACT_ID,
                    "normalization_contract_id": APS_NORMALIZATION_CONTRACT_ID,
                    "normalized_text_sha256": normalized_hash,
                    "normalized_char_count": len(normalized_text),
                    "chunk_count": len(chunk_texts),
                    "content_status": "indexed",
                    "media_type": "application/pdf",
                    "document_class": "inspection_report",
                    "quality_status": "strong",
                    "page_count": 2,
                    "diagnostics_ref": f"raw-materialized/{corpus_batch_id}/diagnostics.json",
                    "visual_page_refs_json": [],
                },
                "chunks": [
                    {
                        "aps_content_chunk_id": f"aps-chunk-materialized-{seed_id}-{index + 1}",
                        "chunk_id": f"{content_id}-chunk-{index + 1}",
                        "chunk_ordinal": index,
                        "chunk_text": chunk_text,
                        "chunk_text_sha256": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                        "start_char": index * 64,
                        "end_char": (index * 64) + len(chunk_text),
                        "page_start": index + 1,
                        "page_end": index + 1,
                        "unit_kind": "pdf_paragraph",
                        "quality_status": "strong",
                    }
                    for index, chunk_text in enumerate(chunk_texts)
                ],
                "linkage": {
                    "aps_content_linkage_id": f"aps-linkage-materialized-{seed_id}",
                    "accession_number": "MLRAWBROWSER001",
                    "content_units_ref": content_units_ref,
                    "normalized_text_ref": normalized_ref,
                    "normalized_text_sha256": normalized_hash,
                    "blob_ref": blob_ref,
                    "blob_sha256": blob_hash,
                    "download_exchange_ref": f"raw-materialized/{corpus_batch_id}/download-exchange.json",
                    "discovery_ref": f"raw-materialized/{corpus_batch_id}/discovery.json",
                    "selection_ref": f"raw-materialized/{corpus_batch_id}/selection.json",
                    "diagnostics_ref": f"raw-materialized/{corpus_batch_id}/diagnostics.json",
                },
            }
        ],
    }
    manifest_ref = f"raw-materialized/{corpus_batch_id}/manifest.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return {
        "schema_id": "project6.review_browser_raw_mixed_materialization_setup.v1",
        "schema_version": 1,
        "materialize_request": {
            "schema_id": RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID,
            "schema_version": 1,
            "client_request_id": f"browser-raw-mixed-materialize-{seed_id}",
            "materialization_mode": RAW_MIXED_CORPUS_MATERIALIZE_MODE,
            "corpus_batch_id": corpus_batch_id,
            "artifact_manifest_ref": manifest_ref,
            "artifact_manifest_hash": manifest_hash,
            "requested_source_classes": ["dataset_version", "aps_content_document"],
            "operator_confirmation": True,
        },
    }


def _seed_browser_aps_content_fixture(
    db,
    temp_path: Path,
    *,
    run_id: str,
    target_id: str,
    content_id: str,
) -> None:
    db.add(
        ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            status="completed",
        )
    )
    db.add(
        ConnectorRunTarget(
            connector_run_target_id=target_id,
            connector_run_id=run_id,
            status="completed",
            ordinal=0,
        )
    )

    artifact_root = temp_path / "aps"
    chunk_texts = [
        "Inspection findings confirm stable cooling performance.",
        "No safety-significant degradation was identified during the interval.",
    ]
    normalized_text = "\n".join(chunk_texts)
    content_units_ref = _write_json(
        artifact_root / f"{content_id}_content_units.json",
        {
            "content_id": content_id,
            "run_id": run_id,
            "target_id": target_id,
            "chunk_count": len(chunk_texts),
        },
    )
    normalized_text_ref = _write_text(artifact_root / f"{content_id}_normalized.txt", normalized_text)
    blob_ref = _write_text(artifact_root / f"{content_id}.pdf", "pdf-placeholder")
    selection_ref = _write_json(artifact_root / f"{content_id}_selection.json", {"run_id": run_id, "target_id": target_id})
    discovery_ref = _write_json(artifact_root / f"{content_id}_discovery.json", {"run_id": run_id, "target_id": target_id})
    diagnostics_ref = _write_json(artifact_root / f"{content_id}_diagnostics.json", {"quality_status": "strong"})

    db.add(
        ApsContentDocument(
            content_id=content_id,
            content_contract_id=APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            normalized_char_count=len(normalized_text),
            chunk_count=len(chunk_texts),
            content_status="indexed",
            media_type="application/pdf",
            document_class="inspection_report",
            quality_status="strong",
            page_count=2,
            diagnostics_ref=diagnostics_ref,
            visual_page_refs_json=json.dumps([]),
        )
    )
    for ordinal, chunk_text in enumerate(chunk_texts):
        db.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=f"{content_id}-chunk-{ordinal + 1}",
                content_contract_id=APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=ordinal,
                start_char=ordinal * 64,
                end_char=(ordinal * 64) + len(chunk_text),
                chunk_text=chunk_text,
                chunk_text_sha256=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                page_start=ordinal + 1,
                page_end=ordinal + 1,
                unit_kind="pdf_paragraph",
                quality_status="strong",
            )
        )
    db.add(
        ApsContentLinkage(
            content_id=content_id,
            run_id=run_id,
            target_id=target_id,
            accession_number="ML26001A001",
            content_contract_id=APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
            content_units_ref=content_units_ref,
            normalized_text_ref=normalized_text_ref,
            normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            blob_ref=blob_ref,
            blob_sha256=hashlib.sha256(Path(blob_ref).read_bytes()).hexdigest(),
            download_exchange_ref="aps/download_exchange.json",
            discovery_ref=discovery_ref,
            selection_ref=selection_ref,
            diagnostics_ref=diagnostics_ref,
        )
    )
    db.flush()


def _build_browser_quant_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="layer3-browser-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "gate_c_pass"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": dataset_id, "storage_ref": str(csv_path)},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def _build_browser_failed_pass_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="layer3-browser-harness-failed",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "gate_c_pass"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": dataset_id, "storage_ref": str(csv_path)},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    # Truncate the CSV to empty bytes. The file still exists, so Gate C pass
    # admission (which only checks storage existence) admits the analysis set,
    # but load_version_dataframe raises EmptyDataError ("No columns to parse from
    # file") at execution, so execute_selected_pass_run writes PASS_STATUS_FAILED.
    # This drives a genuine execution failure rather than a plan-time block.
    csv_path.write_bytes(b"")
    return session.session_id


def _build_browser_aps_handoff_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    run_id = f"run-{seed_id}"
    target_id = f"target-{seed_id}"
    content_id = f"content-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    _seed_browser_aps_content_fixture(db, temp_path, run_id=run_id, target_id=target_id, content_id=content_id)
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}-aps-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="layer3-browser-aps-handoff-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "aps_handoff_dispatch"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": dataset_id, "storage_ref": str(csv_path)},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": content_id, "run_id": run_id, "target_id": target_id},
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "browser APS handoff companion"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def _build_browser_cohort_aps_handoff_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    first_dataset_version_id = f"dv-cohort-aps-{seed_id}-001"
    second_dataset_version_id = f"dv-cohort-aps-{seed_id}-002"
    run_id = f"run-cohort-aps-{seed_id}"
    target_id = f"target-cohort-aps-{seed_id}"
    content_id = f"content-cohort-aps-{seed_id}"
    first_csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=f"cohort-aps-a-{seed_id}",
        dataset_id=f"ds-cohort-aps-{seed_id}-001",
        dataset_version_id=first_dataset_version_id,
    )
    second_csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=f"cohort-aps-b-{seed_id}",
        dataset_id=f"ds-cohort-aps-{seed_id}-002",
        dataset_version_id=second_dataset_version_id,
    )
    _seed_browser_aps_content_fixture(db, temp_path, run_id=run_id, target_id=target_id, content_id=content_id)
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"selection_group": f"sel-cohort-aps-{seed_id}-quant"},
                "selection_basis": {"selection_id": f"sel-cohort-aps-{seed_id}-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": f"sel-cohort-aps-{seed_id}-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="layer3-browser-cohort-aps-handoff-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "cohort_aps_handoff_dispatch"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    descriptors_by_type = {descriptor.descriptor_type: descriptor for descriptor in descriptors}
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors_by_type["dataset_version"],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": first_dataset_version_id},
                source_provenance={"dataset_id": f"ds-cohort-aps-{seed_id}-001", "storage_ref": str(first_csv_path)},
                payload={"dataset_version_id": first_dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": second_dataset_version_id},
                source_provenance={"dataset_id": f"ds-cohort-aps-{seed_id}-002", "storage_ref": str(second_csv_path)},
                payload={"dataset_version_id": second_dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            ),
        ],
        storage_root=temp_path,
    )
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors_by_type["aps_content_document"],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": content_id, "run_id": run_id, "target_id": target_id},
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "browser APS handoff companion for cohort local outbox proof"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    associated_set = (
        db.query(L3AnalysisSet)
        .filter(
            L3AnalysisSet.session_id == session.session_id,
            L3AnalysisSet.set_type == "associated_cohort",
        )
        .one()
    )
    associated_set.formation_basis_json = {
        **associated_set.formation_basis_json,
        "requested_method_name": "descriptive_summary",
    }
    db.commit()
    return session.session_id


def _seed_sec_xbrl_operator_review_packet(db, *, seed_id: str) -> dict[str, Any]:
    char_a = hashlib.sha256(seed_id.encode()).hexdigest()
    char_b = "b" * 64
    char_c = "c" * 64
    projection_rows = [
        {
            "canonical_id": concept,
            "basis": "total",
            "requested_basis": "total",
            "statement": stmt,
            "family": "universal",
            "status": "projected_oracle_confirmed",
            "source_qname": f"us-gaap:{concept}",
            "oracle_confirmed": True,
            "mapping_method": "fixture",
            "mapping_confidence": "fixture",
            "unit_class": "monetary",
            "provenance_complete": True,
            "value_redacted": True,
            "resolved_fact_provenance_present": True,
            "sidecar_receipt_hash": char_b,
            "value_store_hash": char_c,
        }
        for concept, stmt in [
            ("Revenue", "income"),
            ("TotalAssets", "balance"),
            ("OperatingCashFlow", "cashflow"),
        ]
    ]
    projection_response = xbrl_proj_persistence.materialize_redacted_projection_set(
        db,
        client_request_id=f"proj-{seed_id}",
        projection={
            "status": "canonical_multi_period_projection_ready",
            "sector_family_presence": {"activation_rule": "concept_presence_not_sic_gated"},
            "periods": [
                {
                    "period_ref": "fy-seed",
                    "period_index": 1,
                    "projection": {
                        "status": "canonical_projection_ready",
                        "sidecar_receipt_hash": char_b,
                        "value_store_hash": char_c,
                        "concepts": projection_rows,
                    },
                }
            ],
        },
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=char_a,
    )
    assembly_rows = [
        {
            "canonical_id": concept,
            "basis": "total",
            "requested_basis": "total",
            "statement": stmt,
            "family": "universal",
            "status": "projected_oracle_confirmed",
            "source_qname": f"us-gaap:{concept}",
            "oracle_confirmed": True,
            "mapping_method": "fixture",
            "mapping_confidence": "fixture",
            "unit_class": "monetary",
            "provenance_complete": True,
            "_value": Decimal(str(idx)),
        }
        for idx, (concept, stmt) in enumerate(
            [("Revenue", "income"), ("TotalAssets", "balance"), ("OperatingCashFlow", "cashflow")],
            start=1,
        )
    ]
    packet = xbrl_assembly.assemble_reviewable_statement_packet(
        projection_items=assembly_rows,
        organization_result={
            "contract_passed": True,
            "contract_b_authoritative_organization": True,
            "contract_every_fact_id_bound": True,
            "contract_derived_inputs_bound_and_corroborated": True,
            "normalized_fact_count": 3,
            "organized_count": 3,
            "unjoined_count": 0,
            "a_divergent_count": 0,
            "a_role_unknown_count": 0,
        },
    )
    packet["review_exception_count"] = 0
    packet_response = xbrl_packet_persistence.materialize_redacted_statement_packet(
        db,
        client_request_id=f"packet-{seed_id}",
        sec_xbrl_projection_set_id=projection_response["sec_xbrl_projection_set_id"],
        packet=packet,
    )
    return {
        "schema_id": "project6.review_browser_sec_xbrl_operator_review_seed.v1",
        "schema_version": 1,
        "test_only": True,
        "seed_id": seed_id,
        "sec_xbrl_projection_set_id": projection_response["sec_xbrl_projection_set_id"],
        "sec_xbrl_statement_packet_set_id": packet_response["sec_xbrl_statement_packet_set_id"],
    }


def create_app() -> FastAPI:
    temp_dir = TemporaryDirectory(prefix="review-browser-", ignore_cleanup_errors=True)
    temp_path = Path(temp_dir.name)
    raw_mixed_seed_counter = count(1)
    raw_mixed_materialization_counter = count(1)
    sec_edgar_live_source_artifact_counter = count(1)
    sec_edgar_source_acquisition_counter = count(1)
    sec_edgar_status_counter = count(1)
    sec_edgar_live_status_counter = count(1)
    sec_edgar_html_inline_xbrl_status_counter = count(1)
    sec_edgar_html_inline_xbrl_fact_material_status_counter = count(1)
    sec_edgar_html_inline_xbrl_fact_material_repeatability_counter = count(1)
    sec_edgar_live_repeatability_counter = count(1)
    sec_edgar_repeatability_counter = count(1)
    sec_xbrl_operator_review_counter = count(1)
    fixture = build_review_browser_fixture(temp_path)
    install_review_browser_patches(fixture)
    _install_layer3_browser_patches(temp_path)
    settings.storage_dir = str(temp_path / "storage")
    settings.layer3_external_local_export_dir = str(temp_path / "external-local-export")
    settings.layer3_internal_webhook_url = "http://127.0.0.1/source-directory-browser-webhook"
    settings.layer3_internal_webhook_display_name = "source-directory-browser-webhook"
    settings.layer3_candidate_b_bundle_bridge_dir = str(temp_path / "candidate-b-bundle-bridge")
    settings.layer3_candidate_b_runtime_bridge_dir = str(temp_path / "candidate-b-runtime-bridge")
    source_dir = temp_path / "source-dir"
    _write_layer3_source_directory_fixture(source_dir)
    settings.layer3_source_ingestion_dir = str(source_dir)
    bootstrap_storage_tree(settings.storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    review_ui_static_dir = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static"

    app = FastAPI(title="NRC APS Review Browser Server")
    app.state.review_browser_temp_dir = temp_dir
    app.state.review_browser_fixture = fixture
    app.state.layer3_internal_webhook_calls = []
    app.state.layer3_engine = engine
    app.state.sec_edgar_live_source_artifact_client = _ReviewBrowserSeededSecEdgarClient()
    settings.layer3_sec_edgar_user_agent = "Layer3 Review Browser contact@example.com"
    settings.layer3_sec_edgar_live_network_enabled = True
    settings.layer3_sec_edgar_rate_limit_per_second = 10
    layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT = app.state.sec_edgar_live_source_artifact_client
    layer3_sec_edgar_live_source_artifact.SEC_EDGAR_SLEEP = lambda _seconds: None
    layer3_sec_edgar_live_source_artifact._enforce_rate_limit = lambda: None
    app.include_router(review_nrc_aps.router, prefix="/api/v1/review/nrc-aps")
    app.include_router(layer3.router, prefix="/api/v1/layer3")
    app.mount("/review/nrc-aps/static", StaticFiles(directory=review_ui_static_dir), name="review_ui_static")
    app.mount("/review/layer3/static", StaticFiles(directory=review_ui_static_dir), name="layer3_ui_static")

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    def review_browser_internal_webhook_transport(
        destination_url: str,
        envelope: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, dict[str, object]]:
        app.state.layer3_internal_webhook_calls.append(
            {
                "destination_url": destination_url,
                "envelope_schema_id": envelope.get("schema_id"),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        return 202, {"accepted": True, "receipt": "source-directory-browser-webhook"}

    layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT = (
        review_browser_internal_webhook_transport
    )

    @app.get("/review/nrc-aps", response_class=HTMLResponse)
    def review_nrc_aps_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "index.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/document-trace", response_class=HTMLResponse)
    def review_nrc_aps_document_trace_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "document_trace.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/workbench-compare", response_class=HTMLResponse)
    def review_nrc_aps_workbench_compare_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "workbench_compare.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/candidate-b-trace", response_class=HTMLResponse)
    def review_nrc_aps_candidate_b_trace_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "candidate_b_trace.html").read_text(encoding="utf-8"))

    @app.get("/review/layer3", response_class=HTMLResponse)
    def layer3_workbench_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "layer3.html").read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/__test/harness-info")
    def harness_info() -> dict[str, object]:
        return {
            "schema_id": HARNESS_INFO_SCHEMA_ID,
            "schema_version": HARNESS_INFO_SCHEMA_VERSION,
            "harness_name": "review_browser_server",
            "fixture_version": HARNESS_FIXTURE_VERSION,
            "test_only": True,
            "storage_mode": "temporary-redacted",
            "patch_groups": list(HARNESS_PATCH_GROUPS),
            "runtime_binding_count": len(fixture.selector.runs),
            "seed_routes": [
                "/__test/layer3/seed-quant",
                "/__test/layer3/seed-aps-dataset",
                "/__test/layer3/seed-aps-document",
                "/__test/layer3/seed-aps-handoff",
                "/__test/layer3/seed-cohort-aps-handoff",
                "/__test/layer3/seed-raw-mixed",
                "/__test/layer3/materialize-raw-mixed",
                "/__test/layer3/sec-edgar-live-source-artifact-acquisition",
                "/__test/layer3/sec-edgar-source-acquisition-authority",
                "/__test/layer3/sec-edgar-downstream-status",
                "/__test/layer3/sec-edgar-live-downstream-status",
                "/__test/layer3/sec-edgar-html-inline-xbrl-downstream-status",
                "/__test/layer3/sec-edgar-html-inline-xbrl-fact-material-downstream-status",
                "/__test/layer3/sec-edgar-html-inline-xbrl-fact-material-repeatability-trial",
                "/__test/layer3/sec-edgar-live-repeatability-trial",
                "/__test/layer3/sec-edgar-repeatability-trial",
                "/__test/layer3/source-directory-hybrid-authority",
                "/__test/layer3/source-directory-fixture-reset",
                "/__test/layer3/candidate-b-readiness-audit",
                "/__test/layer3/candidate-b-realistic-readiness-audit",
                "/__test/layer3/candidate-b-source-directory-authority",
                "/__test/layer3/candidate-b-final-proof",
                "/__test/layer3/seed-sec-xbrl-operator-review",
            ],
        }

    @app.post("/__test/layer3/source-directory-fixture-reset")
    def source_directory_fixture_reset() -> dict[str, object]:
        settings.layer3_source_ingestion_dir = str(source_dir)
        return {
            "schema_id": "project6.review_browser_source_directory_fixture_reset.v1",
            "schema_version": 1,
            "test_only": True,
            "source_ingestion_dir_restored": True,
            "source_root_absolute_path_exposed": False,
            "expected_relative_names": ["vector-retrieval.txt"],
        }

    @app.post("/__test/layer3/source-directory-hybrid-authority")
    def source_directory_hybrid_authority(payload: dict[str, object]) -> dict[str, object]:
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        db = SessionLocal()
        try:
            snapshot = (
                db.query(L3MaterialSnapshot)
                .filter(
                    L3MaterialSnapshot.session_id == session_id,
                    L3MaterialSnapshot.source_shape == "server_configured_directory_file",
                )
                .one_or_none()
            )
            if snapshot is None:
                raise HTTPException(status_code=404, detail="source-directory material snapshot not found")
            identity = dict(snapshot.source_identity_json or {})
            snapshot_info = {
                "material_snapshot_id": snapshot.material_snapshot_id,
                "payload_hash": snapshot.payload_hash,
                "source_ingestion_batch_id": identity.get("source_ingestion_batch_id"),
                "source_ingestion_file_id": identity.get("source_ingestion_file_id"),
                "content_sha256": identity.get("content_sha256"),
                "file_identity_hash": identity.get("file_identity_hash"),
                "authority_basis_hash": identity.get("authority_basis_hash"),
            }
            missing = [field for field, value in snapshot_info.items() if not value]
            if missing:
                raise HTTPException(
                    status_code=409,
                    detail=f"source-directory material snapshot is missing authority fields: {', '.join(missing)}",
                )
            text_index = source_directory_material_text_index(
                db,
                {
                    "client_request_id": f"browser-source-directory-text-index-{snapshot.material_snapshot_id}",
                    **snapshot_info,
                },
            )
            vector_index = source_directory_material_embedding_vector_index(
                db,
                {
                    "client_request_id": f"browser-source-directory-vector-index-{snapshot.material_snapshot_id}",
                    **snapshot_info,
                    "index_authority_hash": text_index["index_authority_hash"],
                },
            )
            return {
                "schema_id": "project6.review_browser_source_directory_hybrid_authority.v1",
                "schema_version": 1,
                "test_only": True,
                "session_id": session_id,
                "authority_payload": {
                    **snapshot_info,
                    "index_authority_hash": text_index["index_authority_hash"],
                    "embedding_index_authority_hash": vector_index["embedding_index_authority_hash"],
                    "query_text": "BETA alpha alpha",
                    "analysis_question": "What does the alpha beta evidence support?",
                    "analysis_focus": "rendered source-directory scan to hybrid handoff delivery proof",
                    "limit": 2,
                    "offset": 0,
                    "top_k": 2,
                },
            }
        finally:
            db.close()

    @app.post("/__test/layer3/candidate-b-final-proof")
    def candidate_b_final_proof_setup() -> dict[str, object]:
        try:
            return _prepare_candidate_b_final_proof_fixture()
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"candidate-b final proof setup failed: {exc}",
            ) from exc

    @app.post("/__test/layer3/candidate-b-readiness-audit")
    def candidate_b_readiness_audit_setup() -> dict[str, object]:
        try:
            return _prepare_candidate_b_readiness_audit_fixture()
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"candidate-b readiness audit setup failed: {exc}",
            ) from exc

    @app.post("/__test/layer3/candidate-b-realistic-readiness-audit")
    def candidate_b_realistic_readiness_audit_setup() -> dict[str, object]:
        try:
            return _prepare_candidate_b_realistic_readiness_audit_fixture(fixture)
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"candidate-b realistic readiness audit setup failed: {exc}",
            ) from exc

    @app.post("/__test/layer3/candidate-b-source-directory-authority")
    def candidate_b_source_directory_authority_setup(payload: dict[str, object] | None = None) -> dict[str, object]:
        try:
            return _prepare_candidate_b_source_directory_authority_fixture(fixture, payload)
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"candidate-b source-directory authority setup failed: {exc}",
            ) from exc

    @app.post("/__test/layer3/seed-quant")
    def seed_layer3_quant() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_quant_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-failed-pass")
    def seed_layer3_failed_pass() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_failed_pass_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    @app.post("/__test/layer3/delete-pass-output-manifest")
    def delete_pass_output_manifest(body: dict[str, object]) -> dict[str, object]:
        pass_run_id = str(body.get("pass_run_id") or "").strip()
        if not pass_run_id:
            raise HTTPException(status_code=400, detail="pass_run_id is required")
        db = SessionLocal()
        try:
            pass_run = db.get(L3PassRun, pass_run_id)
            if pass_run is None:
                raise HTTPException(status_code=404, detail=f"PassRun '{pass_run_id}' not found")
            output_ref = str(pass_run.output_payload_ref or "").strip()
            if not output_ref:
                return {"deleted": False, "output_payload_ref": output_ref, "reason": "output_payload_ref_missing"}
            output_path = Path(output_ref)
            if output_path.exists():
                output_path.unlink()
                return {"deleted": True, "output_payload_ref": output_ref}
            return {"deleted": False, "output_payload_ref": output_ref, "reason": "file_already_absent"}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-aps-dataset")
    def seed_layer3_aps_dataset() -> dict[str, str]:
        db = SessionLocal()
        try:
            return _seed_browser_aps_dataset_version_candidate(db, temp_path)
        finally:
            db.close()

    @app.post("/__test/layer3/seed-aps-document")
    def seed_layer3_aps_document() -> dict[str, str]:
        db = SessionLocal()
        try:
            seed_id = uuid_str()
            run_id = f"run-{seed_id}"
            target_id = f"target-{seed_id}"
            content_id = f"content-{seed_id}"
            _seed_browser_aps_content_fixture(
                db,
                temp_path,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
            )
            db.commit()
            return {"run_id": run_id, "target_id": target_id, "content_id": content_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-aps-handoff")
    def seed_layer3_aps_handoff() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_aps_handoff_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-cohort-aps-handoff")
    def seed_layer3_cohort_aps_handoff() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_cohort_aps_handoff_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-raw-mixed")
    def seed_layer3_raw_mixed() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"raw-mixed-browser-{next(raw_mixed_seed_counter):03d}"
            return _seed_browser_raw_mixed_authority(db, temp_path, seed_id=seed_id)
        finally:
            db.close()

    @app.post("/__test/layer3/materialize-raw-mixed")
    def materialize_layer3_raw_mixed_setup() -> dict[str, object]:
        seed_id = f"raw-mixed-materialize-browser-{next(raw_mixed_materialization_counter):03d}"
        return _build_browser_raw_mixed_materialization_setup(seed_id=seed_id)

    @app.post("/__test/layer3/sec-edgar-live-source-artifact-acquisition")
    def sec_edgar_live_source_artifact_acquisition_setup() -> dict[str, object]:
        try:
            seed_id = f"browser-live-source-artifact-{next(sec_edgar_live_source_artifact_counter):03d}"
            return _prepare_sec_edgar_live_source_artifact_acquisition_fixture(
                fake_client=app.state.sec_edgar_live_source_artifact_client,
                seed_id=seed_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR live source-artifact acquisition setup failed: {exc}",
            ) from exc

    @app.post("/__test/layer3/sec-edgar-source-acquisition-authority")
    def sec_edgar_source_acquisition_authority_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"browser-source-acq-{next(sec_edgar_source_acquisition_counter):03d}"
            return _prepare_sec_edgar_source_acquisition_authority_fixture(db, temp_path, seed_id=seed_id)
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR source-acquisition authority setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-downstream-status")
    def sec_edgar_downstream_status_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"browser-{next(sec_edgar_status_counter):03d}"
            return _prepare_sec_edgar_downstream_status_fixture(db, temp_path, seed_id=seed_id)
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR downstream status setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-live-downstream-status")
    def sec_edgar_live_downstream_status_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"browser-live-{next(sec_edgar_live_status_counter):03d}"
            return _prepare_sec_edgar_live_downstream_status_fixture(
                db,
                temp_path,
                fake_client=app.state.sec_edgar_live_source_artifact_client,
                seed_id=seed_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR live downstream status setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-html-inline-xbrl-downstream-status")
    def sec_edgar_html_inline_xbrl_downstream_status_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"browser-html-ixbrl-{next(sec_edgar_html_inline_xbrl_status_counter):03d}"
            return _prepare_sec_edgar_html_inline_xbrl_downstream_status_fixture(
                db,
                fake_client=app.state.sec_edgar_live_source_artifact_client,
                seed_id=seed_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR HTML/iXBRL downstream status setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-html-inline-xbrl-fact-material-downstream-status")
    def sec_edgar_html_inline_xbrl_fact_material_downstream_status_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = (
                "browser-html-ixbrl-fact-material-"
                f"{next(sec_edgar_html_inline_xbrl_fact_material_status_counter):03d}"
            )
            return _prepare_sec_edgar_html_inline_xbrl_fact_material_downstream_status_fixture(
                db,
                fake_client=app.state.sec_edgar_live_source_artifact_client,
                seed_id=seed_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR HTML/iXBRL fact-material downstream status setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-html-inline-xbrl-fact-material-repeatability-trial")
    def sec_edgar_html_inline_xbrl_fact_material_repeatability_trial_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = (
                "browser-html-ixbrl-fact-material-repeatability-"
                f"{next(sec_edgar_html_inline_xbrl_fact_material_repeatability_counter):03d}"
            )
            return _prepare_sec_edgar_html_inline_xbrl_fact_material_repeatability_trial_fixture(
                db,
                fake_client=app.state.sec_edgar_live_source_artifact_client,
                seed_id=seed_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR HTML/iXBRL fact-material repeatability trial setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-live-repeatability-trial")
    def sec_edgar_live_repeatability_trial_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"browser-live-repeatability-{next(sec_edgar_live_repeatability_counter):03d}"
            return _prepare_sec_edgar_live_repeatability_trial_fixture(
                db,
                temp_path,
                fake_client=app.state.sec_edgar_live_source_artifact_client,
                seed_id=seed_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR live repeatability trial setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/sec-edgar-repeatability-trial")
    def sec_edgar_repeatability_trial_setup() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"browser-repeatability-{next(sec_edgar_repeatability_counter):03d}"
            return _prepare_sec_edgar_repeatability_trial_fixture(db, temp_path, seed_id=seed_id)
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC EDGAR repeatability trial setup failed: {exc}",
            ) from exc
        finally:
            db.close()

    @app.post("/__test/layer3/seed-sec-xbrl-operator-review")
    def seed_sec_xbrl_operator_review() -> dict[str, Any]:
        db = SessionLocal()
        try:
            seed_id = f"xbrl-op-rev-{next(sec_xbrl_operator_review_counter):03d}"
            return _seed_sec_xbrl_operator_review_packet(db, seed_id=seed_id)
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=f"SEC XBRL operator review seed failed: {exc}",
            ) from exc
        finally:
            db.close()

    return app
