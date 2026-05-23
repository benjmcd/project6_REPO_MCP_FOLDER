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
