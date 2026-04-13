from __future__ import annotations

import json
from pathlib import Path


def write_candidate_b_trace_bundle(
    tmp_path: Path,
    *,
    fixture_id: str = "fixture-001",
    include_annotated_pdf: bool = True,
    include_raw_json: bool = True,
    include_raw_markdown: bool = True,
    annotated_pdf_status: str | None = None,
    raw_json_ref_override: str | None = None,
    raw_markdown_ref_override: str | None = None,
) -> dict[str, object]:
    checkout_root = tmp_path / "checkout"
    bundle_rel = Path("archive") / "20260413-cb-proof" / "cb-proof-test"
    bundle_root = checkout_root / bundle_rel
    raw_root = bundle_root / "raw"
    annotated_path = raw_root / "annotated" / f"{fixture_id}.pdf"
    raw_json_path = raw_root / f"{fixture_id}.json"
    raw_markdown_path = raw_root / f"{fixture_id}.md"

    raw_root.mkdir(parents=True, exist_ok=True)
    if include_annotated_pdf:
        annotated_path.parent.mkdir(parents=True, exist_ok=True)
        annotated_path.write_bytes(b"%PDF-1.4\n% candidate b trace fixture\n")
    if include_raw_json:
        raw_json_path.write_text(json.dumps({"fixture_id": fixture_id, "kind": "candidate_b"}, indent=2), encoding="utf-8")
    if include_raw_markdown:
        raw_markdown_path.write_text(f"# Candidate B\n\nFixture: {fixture_id}\n", encoding="utf-8")

    bundle_root.mkdir(parents=True, exist_ok=True)
    raw_output_root = (bundle_rel / "raw").as_posix()
    annotated_ref = raw_json_ref = raw_markdown_ref = None
    raw_inventory: list[dict[str, object]] = []

    if include_annotated_pdf:
        annotated_ref = (bundle_rel / "raw" / "annotated" / f"{fixture_id}.pdf").as_posix()
        raw_inventory.append({"path": annotated_ref, "category": "candidate_b_annotated_pdf"})
    if include_raw_json:
        raw_json_ref = (bundle_rel / "raw" / f"{fixture_id}.json").as_posix()
        raw_inventory.append({"path": raw_json_ref, "category": "candidate_b_raw_json"})
    if include_raw_markdown:
        raw_markdown_ref = (bundle_rel / "raw" / f"{fixture_id}.md").as_posix()
        raw_inventory.append({"path": raw_markdown_ref, "category": "candidate_b_raw_markdown"})

    compare_payload = {
        "run_id": "cb-run-001",
        "decision_recommendation": "workbench_useful_with_explicit_footer_limitation",
        "raw_output_root": raw_output_root,
        "non_equivalent_repo_fields": ["element_counts_by_type"],
        "documents": [
            {
                "fixture_id": fixture_id,
                "document_ref": "doc-ref-001",
                "document_sha256": "sha256-fixture-001",
                "expected_gain_claims": ["heading_count"],
                "expected_non_equivalences": ["element_counts_by_type"],
                "regime_labels": ["table_dense"],
                "review_notes": "Fixture-specific operator note.",
                "candidate_b": {
                    "file_name": f"{fixture_id}.pdf",
                    "processing_status": "succeeded",
                    "candidate_b_normalized_char_count": 1188,
                    "odl_page_count": 4,
                    "heading_count": 2,
                    "list_count": 1,
                    "image_count": 0,
                    "table_count": 1,
                    "hidden_text_present": False,
                    "struct_tree_state": "struct_tree_absent",
                    "footer_page_numbers": [4],
                    "image_sources": [],
                    "warning_flags": ["footer_warning"],
                    "limitation_flags": ["footer_page_numbers_detected"],
                    "annotated_pdf_status": annotated_pdf_status or ("present" if include_annotated_pdf else "missing"),
                    "annotated_pdf_ref": annotated_ref,
                    "raw_json_ref": raw_json_ref_override if raw_json_ref_override is not None else raw_json_ref,
                    "raw_markdown_ref": raw_markdown_ref_override if raw_markdown_ref_override is not None else raw_markdown_ref,
                },
            }
        ],
    }
    proof_payload = {
        "warnings": {
            "header_footer_emitted_despite_config": [fixture_id],
            "image_source_collisions": [],
            "labels_sidecar_manifest_hash_status": {"status": "matched"},
        }
    }
    retain_payload = {
        "raw_file_inventory": raw_inventory,
        "outputs_outside_approved_roots": [],
    }

    (bundle_root / "compare.json").write_text(json.dumps(compare_payload, indent=2, sort_keys=True), encoding="utf-8")
    (bundle_root / "proof.json").write_text(json.dumps(proof_payload, indent=2, sort_keys=True), encoding="utf-8")
    (bundle_root / "retain.json").write_text(json.dumps(retain_payload, indent=2, sort_keys=True), encoding="utf-8")
    (bundle_root / "baseline-summary.json").write_text(
        json.dumps({"documents": [{"fixture_id": fixture_id, "baseline": {"char_count": 1200}}]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "checkout_root": checkout_root,
        "bundle_root": bundle_root,
        "bundle_id": bundle_rel.as_posix(),
        "fixture_id": fixture_id,
        "annotated_pdf_ref": annotated_ref,
        "raw_json_ref": raw_json_ref_override if raw_json_ref_override is not None else raw_json_ref,
        "raw_markdown_ref": raw_markdown_ref_override if raw_markdown_ref_override is not None else raw_markdown_ref,
    }
