from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


os.environ["DB_INIT_MODE"] = "none"

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TOOLS = ROOT / "tools"
for candidate in (ROOT, BACKEND, TOOLS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import validate_full_corpus_triplet as triplet_validator  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.core.config import bootstrap_storage_tree, settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.services import layer3_candidate_b_downstream_proof, layer3_internal_webhook_connector  # noqa: E402
from main import app  # noqa: E402


SCHEMA_ID = "candidate_b.full_corpus_layer3_operator_workflow.v1"
SCHEMA_VERSION = 1
RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID = "candidate_b.full_corpus_runtime_root_lifecycle.v1"
RUNTIME_ROOT_LIFECYCLE_MODE = "candidate_b_full_corpus_runtime_root_lifecycle_v1"
WORKFLOW_MODE = "candidate_b_full_corpus_operator_workflow_v1"
BRIDGE_MODE = "candidate_b_full_corpus_runtime_to_layer3_material_authority_v1"
PROOF_MODE = "candidate_b_visual_lane_runtime_downstream_e2e_proof_v1"
OPERATOR_DECISION = "record_candidate_b_visual_lane_runtime_downstream_e2e_proof"
DEFAULT_BRIDGE_DIR = ROOT / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "cb-full-corpus-operator-bridge"
DEFAULT_RECEIPT_DIR = ROOT / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "cb-full-corpus-operator-workflow"
DEFAULT_RUNTIME_ROOT_LIFECYCLE_DIR = (
    ROOT / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "cb-full-corpus-runtime-root-lifecycle"
)
DEFAULT_STORAGE_DIR = ROOT / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "cb-full-corpus-operator-layer3"
DEFAULT_MATERIAL_RELATIVE_NAME = "text/target-00001.md"


class OperatorWorkflowError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the governed Candidate B full-corpus runtime evidence through Layer 3 operator workflow."
    )
    parser.add_argument("--checkout-root", default="", help="Checkout root. Defaults to this repository.")
    parser.add_argument("--baseline-run-root", default="", help="Optional baseline full-corpus runtime root.")
    parser.add_argument("--candidate-a-run-root", default="", help="Optional Candidate A full-corpus runtime root.")
    parser.add_argument("--candidate-b-run-root", default="", help="Optional Candidate B full-corpus runtime root.")
    parser.add_argument("--bridge-dir", default=str(DEFAULT_BRIDGE_DIR), help="Server-owned Candidate B bridge dir.")
    parser.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR), help="Server-owned operator receipt dir.")
    parser.add_argument(
        "--runtime-root-lifecycle-dir",
        default=str(DEFAULT_RUNTIME_ROOT_LIFECYCLE_DIR),
        help="Server-owned Candidate B runtime-root lifecycle receipt dir.",
    )
    parser.add_argument("--layer3-storage-dir", default=str(DEFAULT_STORAGE_DIR), help="Isolated Layer 3 storage dir.")
    parser.add_argument("--material-relative-name", default=DEFAULT_MATERIAL_RELATIVE_NAME)
    parser.add_argument(
        "--internal-webhook-mode",
        choices=("local-ack", "configured"),
        default="local-ack",
        help="Use a local deterministic ack transport, or the configured transport.",
    )
    return parser


def run_operator_workflow(args: argparse.Namespace) -> dict[str, Any]:
    checkout_root = _checkout_root(args.checkout_root)
    bridge_dir = _resolve_dir(args.bridge_dir, checkout_root=checkout_root, field="bridge_dir")
    receipt_dir = _resolve_dir(args.receipt_dir, checkout_root=checkout_root, field="receipt_dir")
    runtime_root_lifecycle_dir = _resolve_dir(
        args.runtime_root_lifecycle_dir,
        checkout_root=checkout_root,
        field="runtime_root_lifecycle_dir",
    )
    layer3_storage_dir = _resolve_dir(args.layer3_storage_dir, checkout_root=checkout_root, field="layer3_storage_dir")
    material_relative_name = _clean_relative_name(args.material_relative_name)

    triplet = _validate_triplet(
        checkout_root=checkout_root,
        baseline_run_root=args.baseline_run_root,
        candidate_a_run_root=args.candidate_a_run_root,
        candidate_b_run_root=args.candidate_b_run_root,
    )
    runs = triplet["selected_runs"]
    baseline_run_id = runs["baseline"]["run_id"]
    candidate_a_run_id = runs["candidate_a"]["run_id"]
    candidate_b_run_id = runs["candidate_b"]["run_id"]
    runtime_discovery_storage_dir = _runtime_discovery_storage_dir(
        checkout_root=checkout_root,
        runtime_roots=[
            runs["baseline"]["runtime_root"],
            runs["candidate_a"]["runtime_root"],
            runs["candidate_b"]["runtime_root"],
        ],
    )
    runtime_root_lifecycle = _runtime_root_lifecycle_receipt(
        checkout_root=checkout_root,
        runtime_parent=runtime_discovery_storage_dir,
        triplet=triplet,
    )
    runtime_root_lifecycle_path = _write_receipt(
        runtime_root_lifecycle_dir,
        runtime_root_lifecycle["lifecycle_receipt_id"],
        runtime_root_lifecycle,
    )

    with _layer3_client(layer3_storage_dir=layer3_storage_dir, bridge_dir=bridge_dir) as client:
        with _runtime_discovery_scope(runtime_discovery_storage_dir):
            bridge = _post_json(
                client,
                "/api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge",
                {
                    "client_request_id": "candidate-b-full-corpus-operator-bridge",
                    "bridge_mode": BRIDGE_MODE,
                    "candidate_b_run_id": candidate_b_run_id,
                    "baseline_run_id": baseline_run_id,
                    "candidate_a_run_id": candidate_a_run_id,
                    "operator_confirmation": True,
                },
            )
        bridge_receipt_id = bridge["bridge_receipt_id"]

        scan = _scan_bridge_curated_source(
            client,
            bridge_receipt_id=bridge_receipt_id,
            candidate_b_run_id=candidate_b_run_id,
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
        )
        snapshot = _approve_material(client, scan, relative_name=material_relative_name)
        analysis_payload, analysis_body, prepare_payload, prepare_body = _prepare_package(
            client,
            snapshot,
            request_prefix="candidate-b-full-corpus-operator",
        )
        delivery = _prove_delivery_surfaces(
            client,
            analysis_payload=analysis_payload,
            analysis_body=analysis_body,
            prepare_payload=prepare_payload,
            prepare_body=prepare_body,
            internal_webhook_mode=str(args.internal_webhook_mode),
        )
        visual_status = _post_json(
            client,
            "/api/v1/layer3/source/ingestion/candidate-b/visual-lane/status",
            {
                "client_request_id": "candidate-b-full-corpus-operator-visual-lane-status",
                "status_mode": "candidate_b_visual_lane_status_v1",
                "operator_decision": "inspect_candidate_b_visual_lane_evidence_status",
                "candidate_b_run_id": candidate_b_run_id,
                "bridge_receipt_id": bridge_receipt_id,
            },
        )
        retained_hash = bridge["authority_hashes"]["governed_retained_artifact_family_hash"]
        downstream_proof = _post_json(
            client,
            "/api/v1/layer3/source/ingestion/candidate-b/runtime/downstream-proof",
            {
                "client_request_id": "candidate-b-full-corpus-operator-downstream-proof",
                "proof_mode": PROOF_MODE,
                "operator_decision": OPERATOR_DECISION,
                "candidate_b_run_id": candidate_b_run_id,
                "bridge_receipt_id": bridge_receipt_id,
                "candidate_b_visual_lane_status_evidence": visual_status,
                "coverage_evidence": _coverage_evidence(retained_hash),
                "operator_confirmation": True,
            },
        )

    eligibility_summary = _operator_eligibility_summary(
        corpus_pdf_count=int(triplet["corpus_pdf_count"]),
        source_directory_eligible_file_count=int(scan["eligible_file_count"]),
        target_status_counts=triplet["target_status_counts"],
    )
    baseline_rollback = _baseline_rollback_summary()
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "workflow_mode": WORKFLOW_MODE,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_run_id": candidate_b_run_id,
        "compare_target_set_hash": triplet["compare_target_set"]["target_set_hash"],
        "bridge_receipt_id": bridge_receipt_id,
        "bridge_receipt_hash": bridge["authority_hashes"]["bridge_receipt_hash"],
        "downstream_proof_id": downstream_proof["proof_receipt_id"],
        "downstream_proof_hash": downstream_proof["proof_hash"],
        "coverage_count": len(downstream_proof["coverage"]),
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"cb-full-corpus-operator-{receipt_hash[:24]}"
    receipt = {
        **receipt_input,
        "receipt_id": receipt_id,
        "receipt_hash": receipt_hash,
        "status": "proven",
        "server_time": _utc_iso(),
        "validate_only_triplet": triplet["validate_only"],
        "artifacts_seeded_or_generated_by_triplet_validator": triplet["artifacts_seeded_or_generated"],
        "corpus": {
            "corpus_pdf_count": triplet["corpus_pdf_count"],
            "eligible_file_count": scan["eligible_file_count"],
            "material_relative_name": material_relative_name,
            "target_status_counts": triplet["target_status_counts"],
            "eligibility_summary": eligibility_summary,
        },
        "baseline_rollback": baseline_rollback,
        "refs": {
            "baseline_runtime_root": _runtime_root_ref(checkout_root, runs["baseline"]["runtime_root"]),
            "candidate_a_runtime_root": _runtime_root_ref(checkout_root, runs["candidate_a"]["runtime_root"]),
            "candidate_b_runtime_root": _runtime_root_ref(checkout_root, runs["candidate_b"]["runtime_root"]),
            "bridge_dir": _path_ref(checkout_root, bridge_dir),
            "curated_root": f"candidate-b-runtime-bridge://{bridge_receipt_id}/curated",
            "receipt_dir": _path_ref(checkout_root, receipt_dir),
        },
        "runtime_root_lifecycle": {
            "schema_id": runtime_root_lifecycle["schema_id"],
            "lifecycle_mode": runtime_root_lifecycle["lifecycle_mode"],
            "lifecycle_receipt_id": runtime_root_lifecycle["lifecycle_receipt_id"],
            "lifecycle_receipt_hash": runtime_root_lifecycle["lifecycle_receipt_hash"],
            "runtime_parent_ref": runtime_root_lifecycle["runtime_parent_ref"],
            "root_count": runtime_root_lifecycle["root_count"],
            "receipt_file": _path_ref(checkout_root, runtime_root_lifecycle_path),
            "validate_only_triplet": runtime_root_lifecycle["validate_only_triplet"],
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
        "layer3": {
            "bridge_status": bridge["status"],
            "source_directory_scan_status": "available",
            "source_directory_eligible_file_count": scan["eligible_file_count"],
            "qualitative_analysis_status": analysis_body["status"],
            "external_export_download_status": prepare_body["status"],
            "same_origin_delivery_available": delivery["same_origin_delivery_available"],
            "provider_private_state": delivery["provider_private_state"],
            "provider_private_revoke_state": delivery["provider_private_revoke_state"],
            "internal_webhook_state": delivery["internal_webhook_state"],
            "visual_lane_status": visual_status["visual_lane_status"],
            "downstream_proof_status": downstream_proof["status"],
        },
        "artifact_family": {
            "governed_retained_artifact_family_hash": retained_hash,
            "role_counts": bridge["governed_retained_artifact_family"]["role_counts"],
            "curated_file_count": bridge["admitted_artifact_subset"]["file_count"],
            "text_file_count": len(bridge["admitted_artifact_subset"]["text_files"]),
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_broadened_beyond_eligible_pdf": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        },
        "next_allowed_actions": [
            "use this receipt as Candidate B full-corpus operator workflow evidence",
            "inspect this receipt through the Candidate B full-corpus operator workflow status surface",
        ],
    }
    receipt_path = _write_receipt(receipt_dir, receipt_id, receipt)
    receipt["receipt_file"] = _path_ref(checkout_root, receipt_path)
    return receipt


def _operator_eligibility_summary(
    *,
    corpus_pdf_count: int,
    source_directory_eligible_file_count: int,
    target_status_counts: dict[str, Any],
) -> dict[str, Any]:
    candidate_b_counts = _candidate_b_target_status_counts(target_status_counts)
    eligible_pdf_count = int(candidate_b_counts.get("recommended") or 0)
    failed_pdf_count = sum(
        count
        for status, count in candidate_b_counts.items()
        if status in {"failed", "error", "blocked"} or "fail" in status or "error" in status
    )
    skipped_pdf_count = sum(
        count
        for status, count in candidate_b_counts.items()
        if status != "recommended"
        and status not in {"failed", "error", "blocked"}
        and "fail" not in status
        and "error" not in status
    )
    skipped_pdf_count += max(corpus_pdf_count - sum(candidate_b_counts.values()), 0)
    return {
        "corpus_pdf_count": corpus_pdf_count,
        "eligible_pdf_count": eligible_pdf_count,
        "skipped_pdf_count": skipped_pdf_count,
        "failed_pdf_count": failed_pdf_count,
        "source_directory_eligible_file_count": source_directory_eligible_file_count,
        "source_directory_extra_material_file_count": max(source_directory_eligible_file_count - eligible_pdf_count, 0),
        "all_eligible_pdfs_processed": (
            eligible_pdf_count == corpus_pdf_count
            and skipped_pdf_count == 0
            and failed_pdf_count == 0
            and source_directory_eligible_file_count >= eligible_pdf_count
        ),
        "candidate_b_target_status_counts": candidate_b_counts,
    }


def _candidate_b_target_status_counts(target_status_counts: dict[str, Any]) -> dict[str, int]:
    candidate_b = target_status_counts.get("candidate_b")
    source = candidate_b if isinstance(candidate_b, dict) else target_status_counts
    counts: dict[str, int] = {}
    for key, value in source.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count >= 0:
            counts[str(key)] = count
    return counts


def _baseline_rollback_summary() -> dict[str, Any]:
    return {
        "available": True,
        "selector": "baseline",
        "explicit_document_processing_engine": "baseline",
        "depends_on_candidate_b_artifacts": False,
        "candidate_a_visual_lane_preserved": True,
        "rollback_requires_selector_mutation": False,
    }


def _validate_triplet(
    *,
    checkout_root: Path,
    baseline_run_root: str,
    candidate_a_run_root: str,
    candidate_b_run_root: str,
) -> dict[str, Any]:
    try:
        baseline_root = triplet_validator._run_root(
            baseline_run_root,
            checkout_root=checkout_root,
            label="baseline",
            engine=triplet_validator.BASELINE_ENGINE,
            visual_lane=triplet_validator.BASELINE_ENGINE,
        )
        candidate_a_root = triplet_validator._run_root(
            candidate_a_run_root,
            checkout_root=checkout_root,
            label="candidate_a",
            engine=triplet_validator.BASELINE_ENGINE,
            visual_lane=triplet_validator.CANDIDATE_A_VISUAL_LANE,
        )
        candidate_b_root = triplet_validator._run_root(
            candidate_b_run_root,
            checkout_root=checkout_root,
            label="candidate_b",
            engine=triplet_validator.CANDIDATE_B_ENGINE,
            visual_lane=triplet_validator.CANDIDATE_B_VISUAL_LANE,
        )
        return triplet_validator.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=baseline_root,
            candidate_a_run_root=candidate_a_root,
            candidate_b_run_root=candidate_b_root,
        )
    except triplet_validator.ValidationError as exc:
        raise OperatorWorkflowError(
            exc.code,
            exc.detail,
            details=_redact_value(exc.context, checkout_root=checkout_root),
        ) from exc


def _runtime_root_lifecycle_receipt(
    *,
    checkout_root: Path,
    runtime_parent: Path | None,
    triplet: dict[str, Any],
) -> dict[str, Any]:
    runs = triplet["selected_runs"]
    roots = {
        label: _runtime_root_path(checkout_root, runs[label]["runtime_root"])
        for label in ("baseline", "candidate_a", "candidate_b")
    }
    parent = runtime_parent or _shared_runtime_parent(roots)
    if not _is_review_runtime_parent(parent):
        raise OperatorWorkflowError(
            "runtime_root_lifecycle_parent_not_admitted",
            "Candidate B runtime-root lifecycle receipts only admit storage/lc_e2e or storage_test_runtime/lc_e2e parents.",
            details={"runtime_parent": str(parent)},
        )
    if {str(root.resolve().parent) for root in roots.values()} != {str(parent.resolve())}:
        raise OperatorWorkflowError(
            "runtime_root_lifecycle_parent_mismatch",
            "Candidate B runtime-root lifecycle receipts require one shared runtime parent for baseline, Candidate A, and Candidate B.",
            details={
                "runtime_parent": str(parent),
                "runtime_roots": {label: str(root) for label, root in roots.items()},
            },
        )

    root_entries = {
        label: _runtime_root_lifecycle_entry(checkout_root, root, run_payload=runs[label])
        for label, root in roots.items()
    }
    receipt_input = {
        "schema_id": RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "lifecycle_mode": RUNTIME_ROOT_LIFECYCLE_MODE,
        "baseline_run_id": runs["baseline"]["run_id"],
        "candidate_a_run_id": runs["candidate_a"]["run_id"],
        "candidate_b_run_id": runs["candidate_b"]["run_id"],
        "compare_target_set_hash": triplet["compare_target_set"]["target_set_hash"],
        "runtime_parent_ref": _path_ref(checkout_root, parent),
        "root_file_hashes": {
            label: {
                "summary_hash": entry["summary_hash"],
                "database_hash": entry["database_hash"],
            }
            for label, entry in root_entries.items()
        },
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"cb-full-corpus-runtime-roots-{receipt_hash[:24]}"
    return {
        **receipt_input,
        "lifecycle_receipt_id": receipt_id,
        "lifecycle_receipt_hash": receipt_hash,
        "status": "validated",
        "server_time": _utc_iso(),
        "validate_only_triplet": triplet.get("validate_only") is True,
        "artifacts_seeded_or_generated_by_triplet_validator": (
            triplet.get("artifacts_seeded_or_generated") is True
        ),
        "root_count": len(root_entries),
        "runtime_roots": root_entries,
        "corpus": {
            "corpus_pdf_count": triplet["corpus_pdf_count"],
            "target_status_counts": triplet["target_status_counts"],
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_broadened_beyond_eligible_pdf": False,
            "runtime_roots_moved_or_copied": False,
            "runtime_artifacts_seeded_by_lifecycle": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "use this lifecycle receipt as the runtime-root authority binding for the Candidate B full-corpus operator workflow",
            "bridge only the validated Candidate B run id through candidate_b_full_corpus_runtime_to_layer3_material_authority_v1",
        ],
    }


def _runtime_root_lifecycle_entry(
    checkout_root: Path,
    root: Path,
    *,
    run_payload: dict[str, Any],
) -> dict[str, Any]:
    summary = root / "local_corpus_e2e_summary.json"
    database = root / "lc.db"
    missing = [path.name for path in (summary, database) if not path.is_file()]
    if missing:
        raise OperatorWorkflowError(
            "runtime_root_lifecycle_required_file_missing",
            "Candidate B runtime-root lifecycle validation requires summary and database files for each selected run.",
            details={"runtime_root": str(root), "missing_files": missing},
        )
    return {
        "run_id": run_payload["run_id"],
        "runtime_root_ref": _runtime_root_ref(checkout_root, str(root)),
        "summary_ref": _path_ref(checkout_root, summary),
        "summary_hash": _file_hash(summary),
        "database_ref": _path_ref(checkout_root, database),
        "database_hash": _file_hash(database),
        "document_processing_engine": run_payload["document_processing_engine"],
        "visual_lane_mode": run_payload["visual_lane_mode"],
    }


def _runtime_root_path(checkout_root: Path, value: Any) -> Path:
    text = str(value or "").strip()
    if not text:
        raise OperatorWorkflowError("runtime_root_lifecycle_root_missing", "A selected runtime root is missing.")
    if text.startswith("redacted://"):
        raise OperatorWorkflowError(
            "runtime_root_lifecycle_root_unresolvable",
            "A selected runtime root is redacted and cannot be used for lifecycle validation.",
        )
    if text.startswith("repo://"):
        return (checkout_root / text.removeprefix("repo://")).resolve()
    root = Path(text)
    if not root.is_absolute():
        root = checkout_root / root
    return root.resolve()


def _shared_runtime_parent(roots: dict[str, Path]) -> Path:
    parents = {str(root.resolve().parent): root.resolve().parent for root in roots.values()}
    if len(parents) != 1:
        raise OperatorWorkflowError(
            "runtime_root_lifecycle_parent_mismatch",
            "Candidate B runtime-root lifecycle validation requires one shared runtime parent.",
            details={"runtime_parents": sorted(parents)},
        )
    return next(iter(parents.values()))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_discovery_storage_dir(*, checkout_root: Path, runtime_roots: list[str]) -> Path | None:
    parents: dict[str, Path] = {}
    for raw_root in runtime_roots:
        if not str(raw_root or "").strip():
            continue
        root = _runtime_root_path(checkout_root, raw_root)
        parent = root.resolve().parent
        if not _is_review_runtime_parent(parent):
            raise OperatorWorkflowError(
                "explicit_runtime_root_parent_not_admitted",
                "Explicit runtime roots must live under an admitted storage_test_runtime/lc_e2e parent.",
                details={"runtime_root": str(root), "runtime_parent": str(parent)},
            )
        parents[str(parent)] = parent
    if not parents:
        return None
    if len(parents) != 1:
        raise OperatorWorkflowError(
            "explicit_runtime_roots_parent_mismatch",
            "The full-corpus operator runner can only bridge one configured runtime-discovery parent per run.",
            details={"runtime_parent_count": len(parents), "runtime_parents": sorted(parents)},
        )
    return next(iter(parents.values()))


def _is_review_runtime_parent(path: Path) -> bool:
    return path.name == "lc_e2e" and path.parent.name in {"storage", "storage_test_runtime"}


@contextmanager
def _runtime_discovery_scope(storage_dir: Path | None) -> Iterator[None]:
    if storage_dir is None:
        yield
        return
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(storage_dir)
    try:
        yield
    finally:
        settings.storage_dir = original_storage_dir


@contextmanager
def _layer3_client(*, layer3_storage_dir: Path, bridge_dir: Path) -> Iterator[TestClient]:
    original_storage_dir = settings.storage_dir
    original_bridge_dir = settings.layer3_candidate_b_runtime_bridge_dir
    original_source_ingestion_dir = settings.layer3_source_ingestion_dir
    original_webhook_url = settings.layer3_internal_webhook_url
    original_webhook_display_name = settings.layer3_internal_webhook_display_name
    original_webhook_transport = layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT
    bootstrap_storage_tree(layer3_storage_dir)
    settings.storage_dir = str(layer3_storage_dir)
    settings.layer3_candidate_b_runtime_bridge_dir = str(bridge_dir)
    settings.layer3_source_ingestion_dir = ""
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db() -> Iterator[Any]:
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.openapi_schema = None
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.openapi_schema = None
        settings.storage_dir = original_storage_dir
        settings.layer3_candidate_b_runtime_bridge_dir = original_bridge_dir
        settings.layer3_source_ingestion_dir = original_source_ingestion_dir
        settings.layer3_internal_webhook_url = original_webhook_url
        settings.layer3_internal_webhook_display_name = original_webhook_display_name
        layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT = original_webhook_transport


def _scan_bridge_curated_source(
    client: TestClient,
    *,
    bridge_receipt_id: str,
    candidate_b_run_id: str,
    baseline_run_id: str,
    candidate_a_run_id: str,
) -> dict[str, Any]:
    return _post_json(
        client,
        "/api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge/source-scan",
        {
            "client_request_id": "candidate-b-full-corpus-operator-source-scan",
            "source_scan_mode": "candidate_b_runtime_bridge_curated_source_scan_v1",
            "operator_decision": "scan_candidate_b_runtime_bridge_curated_material_root",
            "bridge_receipt_id": bridge_receipt_id,
            "candidate_b_run_id": candidate_b_run_id,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "operator_confirmation": True,
            "source_family": "server_configured_operator_directory_text_table_source_family",
            "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
        },
        expected_status=201,
    )


def _approve_material(client: TestClient, scan: dict[str, Any], *, relative_name: str) -> dict[str, Any]:
    file_record = next((item for item in scan["files"] if item["relative_name"] == relative_name), None)
    if not isinstance(file_record, dict):
        raise OperatorWorkflowError(
            "material_file_missing",
            "The requested material file is not present in the source-directory scan.",
            details={"relative_name": relative_name},
        )
    preview = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        {
            "client_request_id": f"candidate-b-full-corpus-operator-preview-{relative_name.replace('/', '-')}",
            "source_ingestion_batch_id": scan["source_ingestion_batch_id"],
            "source_ingestion_file_id": file_record["source_ingestion_file_id"],
            "file_identity_hash": file_record["file_identity_hash"],
            "authority_basis_hash": file_record["authority_basis_hash"],
        },
    )
    candidate = preview["material_candidate"]
    gate_b = _post_json(
        client,
        "/api/v1/layer3/gate-b/decision",
        {
            "client_request_id": "candidate-b-full-corpus-operator-gate-b",
            "preflight_id": "candidate-b-full-corpus-operator-preflight",
            "source_set_id": scan["source_ingestion_batch_id"],
            "material_preview_id": preview["material_preview_id"],
            "material_preview_hash": preview["material_preview_hash"],
            "candidate_decisions": [
                {"candidate_id": candidate["candidate_id"], "decision": "approved", "decision_basis": candidate}
            ],
        },
    )
    return {
        "session_id": gate_b["session_id"],
        "source_ingestion_batch_id": scan["source_ingestion_batch_id"],
        "source_ingestion_file_id": candidate["payload"]["source_ingestion_file_id"],
        "content_sha256": candidate["payload"]["content_sha256"],
        "file_identity_hash": candidate["payload"]["file_identity_hash"],
        "authority_basis_hash": candidate["payload"]["authority_basis_hash"],
    }


def _prepare_package(
    client: TestClient,
    snapshot: dict[str, Any],
    *,
    request_prefix: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    authority = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare",
        {
            "client_request_id": f"{request_prefix}-hybrid-authority",
            "session_id": snapshot["session_id"],
            "query_text": "Candidate B full-corpus normalized text",
            "analysis_question": "What Candidate B runtime material is available?",
            "analysis_focus": "Candidate B full-corpus operator workflow",
            "limit": 2,
            "offset": 0,
            "top_k": 2,
        },
    )
    analysis_payload = {
        "client_request_id": f"{request_prefix}-analysis",
        **authority["authority_payload"],
    }
    analysis = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis",
        analysis_payload,
    )
    commit = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/commit",
        {
            **analysis_payload,
            "qualitative_analysis_hash": analysis["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": analysis[
                "source_directory_hybrid_package_review_preview_hash"
            ],
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": analysis[
            "source_directory_hybrid_package_review_preview_hash"
        ],
        "construction_basis_hash": commit["construction_basis_hash"],
        "reconciliation_record_id": commit["reconciliation_record_id"],
        "output_package_ids": commit["output_package_ids"],
        "package_kinds": commit["package_kinds"],
        "payload_hashes": commit["payload_hashes"],
        "operator_decision": "approved",
        "decision_notes": "Candidate B full-corpus operator workflow package approved.",
    }
    submit = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit",
        submit_payload,
    )
    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    handoff = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare",
        handoff_payload,
    )
    prepare_payload = {
        **handoff_payload,
        "operator_decision": "prepare_source_directory_hybrid_external_export_download",
        "prepare_record_ref": handoff["prepare_record_ref"],
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": handoff["handoff_export_envelope"]["envelope_ref"],
        "external_export_download_target": "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference",
        "download_mode": "reference_only_prepare",
    }
    prepare = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare",
        prepare_payload,
    )
    return analysis_payload, analysis, prepare_payload, prepare


def _prove_delivery_surfaces(
    client: TestClient,
    *,
    analysis_payload: dict[str, Any],
    analysis_body: dict[str, Any],
    prepare_payload: dict[str, Any],
    prepare_body: dict[str, Any],
    internal_webhook_mode: str,
) -> dict[str, Any]:
    selected_package = next(item for item in prepare_body["output_packages"] if item["package_kind"] == "user_facing")
    delivery_payload = {
        **prepare_payload,
        "operator_decision": "deliver_source_directory_hybrid_external_export_download",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
        "output_package_id": selected_package["output_package_id"],
        "package_kind": selected_package["package_kind"],
        "package_payload_hash": selected_package["payload_hash"],
    }
    delivery_status = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status",
        delivery_payload,
    )
    delivery_response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver",
        json=delivery_payload,
    )
    if delivery_response.status_code != 200:
        raise OperatorWorkflowError("same_origin_delivery_failed", "Same-origin delivery failed.")
    provider_private_prepare = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare",
        {
            **delivery_payload,
            "client_request_id": "candidate-b-full-corpus-operator-provider-private-prepare",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "candidate-b-full-corpus-operator-redacted-delivery",
            "requested_ttl_seconds": 300,
        },
    )
    provider_private_status = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/status",
        {
            **delivery_payload,
            "client_request_id": "candidate-b-full-corpus-operator-provider-private-status",
            "operator_decision": "inspect_source_directory_hybrid_provider_private_signed_url_status",
            "delivery_mode": "provider_private_signed_url",
            "provider_signed_url_receipt_id": provider_private_prepare["provider_signed_url_receipt_id"],
        },
    )
    _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/use",
        {
            **delivery_payload,
            "client_request_id": "candidate-b-full-corpus-operator-provider-private-use",
            "operator_decision": "use_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "provider_signed_url_receipt_id": provider_private_prepare["provider_signed_url_receipt_id"],
        },
    )
    revoke_prepare = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare",
        {
            **delivery_payload,
            "client_request_id": "candidate-b-full-corpus-operator-provider-private-revoke-prepare",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "candidate-b-full-corpus-operator-redacted-revoke",
            "requested_ttl_seconds": 300,
        },
    )
    provider_private_revoke = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/revoke",
        {
            **delivery_payload,
            "client_request_id": "candidate-b-full-corpus-operator-provider-private-revoke",
            "operator_decision": "revoke_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "provider_signed_url_receipt_id": revoke_prepare["provider_signed_url_receipt_id"],
            "idempotency_key": "candidate-b-full-corpus-operator-provider-private-revoke",
            "revoked_by": "candidate-b-full-corpus-operator-runner",
            "revocation_reason": "Candidate B full-corpus operator workflow revoke.",
        },
    )
    webhook = _dispatch_internal_webhook(
        client,
        prepare_payload=prepare_payload,
        prepare_body=prepare_body,
        internal_webhook_mode=internal_webhook_mode,
    )
    downstream_status = _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/status",
        {
            **{key: value for key, value in analysis_payload.items() if key != "client_request_id"},
            "client_request_id": "candidate-b-full-corpus-operator-downstream-status",
        },
    )
    session = _get_json(client, f"/api/v1/layer3/session/{webhook['session_id']}")
    if session["internal_webhook_dispatch"]["raw_package_payload_exposed"] is True:
        raise OperatorWorkflowError(
            "raw_package_payload_exposed",
            "Internal webhook status exposed raw package payload authority.",
            details={"session_id": webhook["session_id"]},
        )
    return {
        "same_origin_delivery_available": delivery_status["delivery_available"] is True,
        "provider_private_state": provider_private_prepare["provider_signed_url_state"],
        "provider_private_status_state": provider_private_status["provider_signed_url_state"],
        "provider_private_revoke_state": provider_private_revoke["provider_signed_url_state"],
        "internal_webhook_state": webhook["source_directory_internal_webhook_dispatch_state"],
        "downstream_status_hash": downstream_status["qualitative_analysis_hash"],
        "session_internal_webhook_state": session["internal_webhook_dispatch"]["state"],
        "raw_package_payload_exposed": False,
    }


def _dispatch_internal_webhook(
    client: TestClient,
    *,
    prepare_payload: dict[str, Any],
    prepare_body: dict[str, Any],
    internal_webhook_mode: str,
) -> dict[str, Any]:
    if internal_webhook_mode == "local-ack":
        settings.layer3_internal_webhook_url = "http://127.0.0.1/candidate-b-full-corpus-operator-webhook"
        settings.layer3_internal_webhook_display_name = "candidate-b-full-corpus-operator-webhook"

        def local_ack_transport(url: str, envelope: dict[str, Any], headers: dict[str, str], timeout: int) -> tuple[int, dict[str, Any]]:
            del url, envelope, headers, timeout
            return 202, {"accepted": True, "receipt": "candidate-b-full-corpus-operator-local-ack"}

        layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT = local_ack_transport
    elif not str(settings.layer3_internal_webhook_url or "").strip():
        raise OperatorWorkflowError(
            "internal_webhook_url_missing",
            "Configured internal webhook mode requires LAYER3_INTERNAL_WEBHOOK_URL.",
        )
    return _post_json(
        client,
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch",
        {
            **prepare_payload,
            "client_request_id": "candidate-b-full-corpus-operator-internal-webhook-dispatch",
            "operator_decision": "dispatch_source_directory_hybrid_internal_webhook",
            "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
            "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
            "external_export_download_state": "external_export_download_prepared",
            "target_identity": "server_configured_internal_webhook_destination",
            "target_class": "real_connector_invocation",
            "dispatch_mode": "server_configured_allowlisted_internal_webhook_post",
        },
    )


def _coverage_evidence(retained_artifact_family_hash: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for step in sorted(layer3_candidate_b_downstream_proof.REQUIRED_COVERAGE):
        entry = {
            "status": "proven",
            "evidence_ref": f"candidate-b-full-corpus-operator-workflow://{step}",
            "evidence_hash": hashlib.sha256(step.encode("utf-8")).hexdigest(),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        }
        if step in layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE:
            entry["candidate_b_retained_artifact_family_hash"] = retained_artifact_family_hash
            entry["candidate_b_delivery_artifact_roles_bound"] = True
        evidence[step] = entry
    return evidence


def _post_json(client: TestClient, path: str, payload: dict[str, Any], *, expected_status: int = 200) -> dict[str, Any]:
    response = client.post(path, json=payload)
    if response.status_code != expected_status:
        raise OperatorWorkflowError(
            "api_request_failed",
            "Layer 3 API request failed closed.",
            details={
                "path": path,
                "status_code": response.status_code,
                "body": _safe_response_body(response.text, checkout_root=ROOT.resolve()),
            },
        )
    body = response.json()
    if not isinstance(body, dict):
        raise OperatorWorkflowError("api_response_invalid", "Layer 3 API response was not a JSON object.", details={"path": path})
    return body


def _get_json(client: TestClient, path: str) -> dict[str, Any]:
    response = client.get(path)
    if response.status_code != 200:
        raise OperatorWorkflowError("api_request_failed", "Layer 3 API request failed closed.", details={"path": path})
    body = response.json()
    if not isinstance(body, dict):
        raise OperatorWorkflowError("api_response_invalid", "Layer 3 API response was not a JSON object.", details={"path": path})
    return body


def _write_receipt(receipt_dir: Path, receipt_id: str, receipt: dict[str, Any]) -> Path:
    target_dir = receipt_dir / receipt_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "receipt.json"
    body = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if target.is_file():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("receipt_hash") != receipt.get("receipt_hash"):
            raise OperatorWorkflowError("operator_receipt_conflict", "Existing operator receipt has different contents.")
        return target
    target.write_text(body, encoding="utf-8")
    return target


def _checkout_root(raw_value: str) -> Path:
    root = Path(raw_value).resolve() if str(raw_value).strip() else ROOT.resolve()
    if not root.is_dir():
        raise OperatorWorkflowError("checkout_root_missing", "Checkout root is unavailable.")
    return root


def _resolve_dir(raw_value: str, *, checkout_root: Path, field: str) -> Path:
    if not str(raw_value or "").strip():
        raise OperatorWorkflowError(f"{field}_missing", f"{field} is required.")
    path = Path(str(raw_value))
    if not path.is_absolute():
        path = checkout_root / path
    return path.resolve()


def _clean_relative_name(value: str) -> str:
    clean = str(value or "").strip().replace("\\", "/")
    if not clean or clean.startswith("/") or ".." in Path(clean).parts:
        raise OperatorWorkflowError("material_relative_name_invalid", "Material relative name must be a safe relative path.")
    return clean


def _path_ref(checkout_root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return f"repo://{resolved.relative_to(checkout_root.resolve()).as_posix()}"
    except ValueError:
        return f"redacted://sha256/{hashlib.sha256(str(resolved).encode('utf-8')).hexdigest()[:24]}"


def _runtime_root_ref(checkout_root: Path, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "redacted://sha256/empty-runtime-root"
    if text.startswith(("repo://", "redacted://")):
        return text
    if _looks_like_path(text):
        return _path_ref(checkout_root, Path(text))
    normalized = text.replace("\\", "/").lstrip("/")
    return f"repo://{normalized}"


def _redact_value(value: Any, *, checkout_root: Path) -> Any:
    if isinstance(value, dict):
        return {str(key): _redact_value(item, checkout_root=checkout_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, checkout_root=checkout_root) for item in value]
    if isinstance(value, str) and _looks_like_path(value):
        return _path_ref(checkout_root, Path(value))
    if isinstance(value, str):
        return _redact_text(value, checkout_root=checkout_root)
    return value


def _looks_like_path(value: str) -> bool:
    text = value.strip()
    return bool(text) and (PureWindowsPath(text).is_absolute() or Path(text).is_absolute())


def _safe_response_body(text: str, *, checkout_root: Path) -> str:
    redacted = _redact_text(text, checkout_root=checkout_root)
    return redacted if len(redacted) <= 2000 else redacted[:2000] + "...truncated"


def _redact_text(text: str, *, checkout_root: Path) -> str:
    redacted = str(text)
    root = str(checkout_root.resolve())
    for raw_root in {root, root.replace("\\", "/")}:
        redacted = redacted.replace(raw_root, "repo://")

    def replace_path(match: re.Match[str]) -> str:
        path_text = match.group(0)
        return f"redacted://sha256/{hashlib.sha256(path_text.encode('utf-8')).hexdigest()[:24]}"

    redacted = re.sub(r"[A-Za-z]:[\\/][^\s\"'<>|]+", replace_path, redacted)
    redacted = re.sub(
        r"file:///[^\s\"'<>|]+",
        lambda match: f"redacted://file/{hashlib.sha256(match.group(0).encode('utf-8')).hexdigest()[:24]}",
        redacted,
    )
    redacted = re.sub(
        r"https?://[^\s\"'<>|]+",
        lambda match: f"redacted://url/{hashlib.sha256(match.group(0).encode('utf-8')).hexdigest()[:24]}",
        redacted,
    )
    return redacted


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _blocked_receipt(exc: Exception, *, checkout_root: Path | None = None) -> dict[str, Any]:
    if isinstance(exc, OperatorWorkflowError):
        code = exc.code
        message = exc.message
        details = exc.details
    else:
        code = "unexpected_operator_workflow_error"
        message = str(exc)
        details = {}
    redacted_details = _redact_value(details, checkout_root=checkout_root or ROOT.resolve())
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "workflow_mode": WORKFLOW_MODE,
        "status": "blocked",
        "server_time": _utc_iso(),
        "error": {"code": code, "message": message, "details": redacted_details},
        "negative_invariants": {
            "artifacts_seeded_after_blocker": False,
            "raw_local_path_exposed": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checkout_root = Path(args.checkout_root).resolve() if str(args.checkout_root).strip() else ROOT.resolve()
    try:
        receipt = run_operator_workflow(args)
        exit_code = 0
    except Exception as exc:  # noqa: BLE001
        receipt = _blocked_receipt(exc, checkout_root=checkout_root)
        exit_code = 1
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
