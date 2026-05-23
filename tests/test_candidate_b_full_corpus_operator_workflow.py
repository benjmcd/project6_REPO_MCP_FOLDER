from __future__ import annotations

import json
from pathlib import Path

from tools import run_candidate_b_full_corpus_operator_workflow as workflow


def test_parser_defaults_to_operator_safe_local_ack_mode() -> None:
    args = workflow.build_parser().parse_args([])

    assert args.internal_webhook_mode == "local-ack"
    assert args.material_relative_name == workflow.DEFAULT_MATERIAL_RELATIVE_NAME
    assert args.bridge_dir == str(workflow.DEFAULT_BRIDGE_DIR)
    assert args.receipt_dir == str(workflow.DEFAULT_RECEIPT_DIR)
    assert args.runtime_root_lifecycle_dir == str(workflow.DEFAULT_RUNTIME_ROOT_LIFECYCLE_DIR)


def test_coverage_evidence_binds_delivery_artifact_authority() -> None:
    retained_hash = "a" * 64

    evidence = workflow._coverage_evidence(retained_hash)

    assert set(evidence) == set(workflow.layer3_candidate_b_downstream_proof.REQUIRED_COVERAGE)
    for step, entry in evidence.items():
        assert entry["status"] == "proven"
        assert entry["raw_local_path_exposed"] is False
        assert entry["raw_url_exposed"] is False
        assert entry["provider_public_url_enabled"] is False
        assert entry["provider_object_writes_enabled"] is False
        assert entry["connector_dispatch_enabled"] is False
        assert entry["rag_vector_model_runtime_enabled"] is False
        assert entry["frontend_durable_authority_enabled"] is False
        if step in workflow.layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE:
            assert entry["candidate_b_retained_artifact_family_hash"] == retained_hash
            assert entry["candidate_b_delivery_artifact_roles_bound"] is True
        else:
            assert "candidate_b_delivery_artifact_roles_bound" not in entry


def test_operator_eligibility_summary_records_counts_and_rollback() -> None:
    summary = workflow._operator_eligibility_summary(
        corpus_pdf_count=69,
        source_directory_eligible_file_count=71,
        target_status_counts={
            "baseline": {"recommended": 69},
            "candidate_a": {"recommended": 69},
            "candidate_b": {"recommended": 69},
        },
    )

    assert summary == {
        "corpus_pdf_count": 69,
        "eligible_pdf_count": 69,
        "skipped_pdf_count": 0,
        "failed_pdf_count": 0,
        "source_directory_eligible_file_count": 71,
        "source_directory_extra_material_file_count": 2,
        "all_eligible_pdfs_processed": True,
        "candidate_b_target_status_counts": {"recommended": 69},
    }
    assert workflow._baseline_rollback_summary() == {
        "available": True,
        "selector": "baseline",
        "explicit_document_processing_engine": "baseline",
        "depends_on_candidate_b_artifacts": False,
        "candidate_a_visual_lane_preserved": True,
        "rollback_requires_selector_mutation": False,
    }


def test_path_ref_redacts_paths_outside_checkout(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    inside = checkout_root / "backend" / "receipt.json"
    outside = tmp_path / "outside" / "receipt.json"
    checkout_root.mkdir()
    outside.parent.mkdir()

    assert workflow._path_ref(checkout_root, inside) == "repo://backend/receipt.json"
    assert workflow._path_ref(checkout_root, outside).startswith("redacted://sha256/")


def test_runtime_discovery_storage_dir_uses_shared_explicit_parent(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    runtime_parent = tmp_path / "shared" / "storage_test_runtime" / "lc_e2e"
    baseline_root = runtime_parent / "baseline-run"
    candidate_a_root = runtime_parent / "candidate-a-run"
    candidate_b_root = runtime_parent / "candidate-b-run"
    for root in (checkout_root, baseline_root, candidate_a_root, candidate_b_root):
        root.mkdir(parents=True)

    storage_dir = workflow._runtime_discovery_storage_dir(
        checkout_root=checkout_root,
        runtime_roots=[str(baseline_root), str(candidate_a_root), str(candidate_b_root)],
    )

    assert storage_dir == runtime_parent.resolve()


def test_runtime_root_lifecycle_receipt_binds_roots_without_raw_path_leak(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    runtime_parent = tmp_path / "shared" / "storage_test_runtime" / "lc_e2e"
    roots = {
        "baseline": runtime_parent / "baseline-run",
        "candidate_a": runtime_parent / "candidate-a-run",
        "candidate_b": runtime_parent / "candidate-b-run",
    }
    checkout_root.mkdir()
    for label, root in roots.items():
        root.mkdir(parents=True)
        (root / "local_corpus_e2e_summary.json").write_text(f'{{"label":"{label}"}}', encoding="utf-8")
        (root / "lc.db").write_bytes(f"{label}-database".encode("utf-8"))

    receipt = workflow._runtime_root_lifecycle_receipt(
        checkout_root=checkout_root,
        runtime_parent=runtime_parent,
        triplet=_lifecycle_triplet(roots),
    )
    serialized = json.dumps(receipt, sort_keys=True)

    assert receipt["schema_id"] == workflow.RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID
    assert receipt["lifecycle_mode"] == workflow.RUNTIME_ROOT_LIFECYCLE_MODE
    assert receipt["lifecycle_receipt_id"].startswith("cb-full-corpus-runtime-roots-")
    assert receipt["status"] == "validated"
    assert receipt["root_count"] == 3
    assert receipt["validate_only_triplet"] is True
    assert receipt["artifacts_seeded_or_generated_by_triplet_validator"] is False
    assert receipt["negative_invariants"]["runtime_roots_moved_or_copied"] is False
    assert receipt["runtime_roots"]["candidate_b"]["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert receipt["runtime_roots"]["candidate_b"]["runtime_root_ref"].startswith("redacted://sha256/")
    assert str(runtime_parent) not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_runtime_root_lifecycle_receipt_rejects_mixed_runtime_parents(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()
    parent_a = tmp_path / "one" / "storage_test_runtime" / "lc_e2e"
    parent_b = tmp_path / "two" / "storage_test_runtime" / "lc_e2e"
    roots = {
        "baseline": parent_a / "baseline-run",
        "candidate_a": parent_a / "candidate-a-run",
        "candidate_b": parent_b / "candidate-b-run",
    }
    for root in roots.values():
        root.mkdir(parents=True)
        (root / "local_corpus_e2e_summary.json").write_text("{}", encoding="utf-8")
        (root / "lc.db").write_bytes(b"db")

    try:
        workflow._runtime_root_lifecycle_receipt(
            checkout_root=checkout_root,
            runtime_parent=None,
            triplet=_lifecycle_triplet(roots),
        )
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "runtime_root_lifecycle_parent_mismatch"
    else:
        raise AssertionError("mixed runtime parents were accepted")


def test_runtime_discovery_storage_dir_rejects_unadmitted_parent(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    runtime_root = tmp_path / "shared" / "not-runtime-parent" / "candidate-b"
    checkout_root.mkdir()
    runtime_root.mkdir(parents=True)

    try:
        workflow._runtime_discovery_storage_dir(checkout_root=checkout_root, runtime_roots=[str(runtime_root)])
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "explicit_runtime_root_parent_not_admitted"
    else:
        raise AssertionError("unadmitted explicit runtime parent was accepted")


def test_runtime_discovery_scope_restores_layer3_storage_dir(tmp_path: Path, monkeypatch) -> None:
    layer3_storage_dir = tmp_path / "layer3-storage"
    runtime_parent = tmp_path / "shared" / "storage_test_runtime" / "lc_e2e"
    monkeypatch.setattr(workflow.settings, "storage_dir", str(layer3_storage_dir))

    with workflow._runtime_discovery_scope(runtime_parent):
        assert workflow.settings.storage_dir == str(runtime_parent)

    assert workflow.settings.storage_dir == str(layer3_storage_dir)


def test_runtime_root_ref_redacts_external_paths_and_wraps_repo_relative(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    inside_relative = "backend/app/storage_test_runtime/lc_e2e/baseline-run"
    outside = tmp_path / "outside" / "storage_test_runtime" / "lc_e2e" / "candidate-b-run"
    checkout_root.mkdir()
    outside.mkdir(parents=True)

    assert workflow._runtime_root_ref(checkout_root, inside_relative) == f"repo://{inside_relative}"
    outside_ref = workflow._runtime_root_ref(checkout_root, str(outside))
    assert outside_ref.startswith("redacted://sha256/")
    assert str(outside) not in outside_ref


def test_blocked_receipt_redacts_raw_paths_and_urls(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()
    raw_inside = checkout_root / "backend" / "storage_test_runtime" / "secret.json"
    raw_outside = Path("D:/operator/private/source.pdf")
    file_url = f"file:///{raw_inside.as_posix()}"
    raw_url = "https://provider.example/private/raw-token"
    error = workflow.OperatorWorkflowError(
        "blocked_for_test",
        "Blocked without exposing artifact roots.",
        details={
            "inside": str(raw_inside),
            "outside": str(raw_outside),
            "body": f"failed at {raw_inside} using {raw_outside} via {file_url} and {raw_url}",
        },
    )

    receipt = workflow._blocked_receipt(error, checkout_root=checkout_root)
    serialized = json.dumps(receipt, sort_keys=True)

    assert receipt["status"] == "blocked"
    assert receipt["negative_invariants"]["raw_local_path_exposed"] is False
    assert str(checkout_root) not in serialized
    assert "D:/" not in serialized
    assert "D:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized
    assert "repo://" in serialized
    assert "redacted://" in serialized


def _lifecycle_triplet(roots: dict[str, Path]) -> dict[str, object]:
    return {
        "validate_only": True,
        "artifacts_seeded_or_generated": False,
        "corpus_pdf_count": 69,
        "compare_target_set": {"target_set_hash": "1" * 64},
        "target_status_counts": {
            "baseline": {"recommended": 69},
            "candidate_a": {"recommended": 69},
            "candidate_b": {"recommended": 69},
        },
        "selected_runs": {
            "baseline": {
                "run_id": "baseline-run",
                "runtime_root": str(roots["baseline"]),
                "document_processing_engine": "baseline",
                "visual_lane_mode": "baseline",
            },
            "candidate_a": {
                "run_id": "candidate-a-run",
                "runtime_root": str(roots["candidate_a"]),
                "document_processing_engine": "baseline",
                "visual_lane_mode": "candidate_a_page_evidence_v1",
            },
            "candidate_b": {
                "run_id": "candidate-b-run",
                "runtime_root": str(roots["candidate_b"]),
                "document_processing_engine": "candidate_b_opendataloader_pdf",
                "visual_lane_mode": "candidate_b_opendataloader_page_evidence_v1",
            },
        },
    }
