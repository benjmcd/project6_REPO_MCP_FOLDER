from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.review_nrc_aps import (
    NrcApsReviewCanonicalEdgeOut,
    NrcApsReviewCanonicalGraphOut,
    NrcApsReviewCanonicalNodeOut,
    NrcApsReviewRunNodeStateOut,
)
from app.services.review_nrc_aps_runtime import load_summary, normalize_path


CANONICAL_NODES = [
    ("source_corpus", "Source corpus", "source", "The local PDF corpus and summary root.", ["summary"]),
    ("preflight", "Preflight", "preparation", "Preflight checks before submission.", ["summary"]),
    ("submission", "Run submitted", "run_lifecycle", "Run submission and run-level reporting.", ["summary", "run_report"]),
    ("artifact_ingestion", "Artifact ingestion", "core_pipeline", "Artifact ingestion run report.", ["run_report"]),
    ("content_index", "Content index", "core_pipeline", "Content indexing and per-target content units.", ["run_report", "content_units", "diagnostics"]),
    ("search_smoke", "Search smoke", "verification", "Run-specific search smoke verification.", ["summary"]),
    ("branch_a_bundle", "Bundle A", "downstream_branch", "Evidence bundle for the first selected branch.", ["run_report"]),
    ("branch_a_citation_pack", "Citation Pack A", "downstream_branch", "Citation pack for the first selected branch.", ["run_report"]),
    ("branch_a_evidence_report", "Evidence Report A", "downstream_branch", "Evidence report for the first selected branch.", ["run_report"]),
    ("branch_a_export", "Export A", "downstream_branch", "Evidence report export for the first selected branch.", ["run_report"]),
    ("branch_b_bundle", "Bundle B", "downstream_branch", "Evidence bundle for the second selected branch.", ["run_report"]),
    ("branch_b_citation_pack", "Citation Pack B", "downstream_branch", "Citation pack for the second selected branch.", ["run_report"]),
    ("branch_b_evidence_report", "Evidence Report B", "downstream_branch", "Evidence report for the second selected branch.", ["run_report"]),
    ("branch_b_export", "Export B", "downstream_branch", "Evidence report export for the second selected branch.", ["run_report"]),
    ("export_package", "Export package from A+B", "downstream_shared", "Combined export package.", ["run_report"]),
    ("context_packet_package", "Context packet from package", "downstream_shared", "Package-derived context packet.", ["run_report"]),
    ("context_packet_export_a", "Context packet from Export A", "downstream_shared", "Export-derived context packet for branch A.", ["run_report"]),
    ("context_packet_export_b", "Context packet from Export B", "downstream_shared", "Export-derived context packet for branch B.", ["run_report"]),
    ("context_dossier", "Context dossier from export-derived packets", "downstream_shared", "Merged dossier from export packets.", ["run_report"]),
    ("deterministic_insight_artifact", "Deterministic insight artifact", "deterministic", "Insight artifact from the dossier.", ["run_report"]),
    ("deterministic_challenge_artifact", "Deterministic challenge artifact", "deterministic", "Challenge artifact from the insight.", ["run_report"]),
    ("deterministic_challenge_review_packet", "Deterministic challenge review packet", "deterministic", "Final challenge review packet.", ["run_report"]),
    ("validate_only_gates", "Validate-only gates", "verification", "Validate-only gate reports.", ["gate_report"]),
]

CANONICAL_EDGES = [
    ("source_corpus", "preflight"),
    ("preflight", "submission"),
    ("submission", "artifact_ingestion"),
    ("artifact_ingestion", "content_index"),
    ("content_index", "search_smoke"),
    ("content_index", "branch_a_bundle"),
    ("branch_a_bundle", "branch_a_citation_pack"),
    ("branch_a_citation_pack", "branch_a_evidence_report"),
    ("branch_a_evidence_report", "branch_a_export"),
    ("content_index", "branch_b_bundle"),
    ("branch_b_bundle", "branch_b_citation_pack"),
    ("branch_b_citation_pack", "branch_b_evidence_report"),
    ("branch_b_evidence_report", "branch_b_export"),
    ("branch_a_export", "export_package"),
    ("branch_b_export", "export_package"),
    ("export_package", "context_packet_package"),
    ("branch_a_export", "context_packet_export_a"),
    ("branch_b_export", "context_packet_export_b"),
    ("context_packet_export_a", "context_dossier"),
    ("context_packet_export_b", "context_dossier"),
    ("context_dossier", "deterministic_insight_artifact"),
    ("deterministic_insight_artifact", "deterministic_challenge_artifact"),
    ("deterministic_challenge_artifact", "deterministic_challenge_review_packet"),
    ("deterministic_challenge_review_packet", "validate_only_gates"),
]


def build_canonical_graph() -> NrcApsReviewCanonicalGraphOut:
    return NrcApsReviewCanonicalGraphOut(
        nodes=[
            NrcApsReviewCanonicalNodeOut(
                node_id=node_id,
                label=label,
                stage_family=stage_family,
                description=description,
                expected_artifact_classes=expected_artifact_classes,
            )
            for node_id, label, stage_family, description, expected_artifact_classes in CANONICAL_NODES
        ],
        edges=[NrcApsReviewCanonicalEdgeOut(source_id=source_id, target_id=target_id) for source_id, target_id in CANONICAL_EDGES],
    )


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _relative_path(review_root: Path, absolute_or_relative: str | None) -> str | None:
    if not absolute_or_relative:
        return None
    try:
        return normalize_path(review_root, absolute_or_relative)
    except ValueError:
        return None


def _paths_from_artifact_list(review_root: Path, items: list[dict[str, Any]] | None) -> list[str]:
    relative_paths: list[str] = []
    for item in items or []:
        relative = _relative_path(review_root, item.get("ref"))
        if relative:
            relative_paths.append(relative)
    return relative_paths


def _node_state(mapped_file_refs: list[str], summary_metrics: dict[str, Any] | None = None, warnings: list[str] | None = None, fallback_state: str = "missing") -> NrcApsReviewRunNodeStateOut:
    state = "complete" if mapped_file_refs else fallback_state
    return NrcApsReviewRunNodeStateOut(
        node_id="",
        state=state,
        warnings=warnings or [],
        mapped_file_refs=mapped_file_refs,
        summary_metrics=summary_metrics or {},
    )


def _set_node(node_states: dict[str, NrcApsReviewRunNodeStateOut], node_id: str, *, mapped_file_refs: list[str], summary_metrics: dict[str, Any] | None = None, warnings: list[str] | None = None, fallback_state: str = "missing") -> None:
    node = _node_state(mapped_file_refs, summary_metrics, warnings, fallback_state)
    node.node_id = node_id
    node_states[node_id] = node


def _extract_missing_report_warnings(review_root: Path, report_refs: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for ref_key, ref_value in report_refs.items():
        if not ref_value:
            continue
        values = ref_value if isinstance(ref_value, list) else [ref_value]
        for candidate in values:
            relative = _relative_path(review_root, candidate)
            if relative is None:
                warnings.append(f"mismatch: {ref_key} outside review root")
                continue
            if not (review_root / relative).exists():
                warnings.append(f"mismatch: missing {Path(relative).name}")
    return warnings


def map_run_specific_graph(run_id: str, review_root: Path) -> dict[str, NrcApsReviewRunNodeStateOut]:
    summary = load_summary(review_root)
    run_detail = summary.get("run_detail") or {}
    report_refs = run_detail.get("report_refs") or {}
    downstream = summary.get("downstream_artifacts") or {}
    selected_branch_rows = summary.get("selected_branch_rows") or []
    gate_results = summary.get("gate_results") or {}
    node_states: dict[str, NrcApsReviewRunNodeStateOut] = {}

    summary_relative = "local_corpus_e2e_summary.json"
    run_summary_relative = _relative_path(review_root, report_refs.get("run_summary"))
    artifact_ingestion_relative = _relative_path(review_root, report_refs.get("aps_artifact_ingestion"))
    content_index_relative = _relative_path(review_root, report_refs.get("aps_content_index"))

    artifact_ingestion_payload = _load_json(review_root / artifact_ingestion_relative) if artifact_ingestion_relative else {}
    content_index_payload = _load_json(review_root / content_index_relative) if content_index_relative else {}

    _set_node(
        node_states,
        "source_corpus",
        mapped_file_refs=[summary_relative],
        summary_metrics={"corpus_pdf_count": summary.get("corpus_pdf_count", 0)},
        fallback_state="missing",
    )
    _set_node(
        node_states,
        "preflight",
        mapped_file_refs=[summary_relative],
        summary_metrics=summary.get("preflight") or {},
        fallback_state="missing" if not summary.get("preflight") else "complete",
    )
    submission_refs = [summary_relative]
    if run_summary_relative:
        submission_refs.append(run_summary_relative)
    _set_node(
        node_states,
        "submission",
        mapped_file_refs=submission_refs,
        summary_metrics={
            "run_id": summary.get("run_id"),
            "status": run_detail.get("status"),
            "submitted_at": (summary.get("submission") or {}).get("submitted_at"),
        },
        warnings=_extract_missing_report_warnings(review_root, report_refs),
        fallback_state="missing",
    )
    _set_node(
        node_states,
        "artifact_ingestion",
        mapped_file_refs=[artifact_ingestion_relative] if artifact_ingestion_relative else [],
        summary_metrics=artifact_ingestion_payload or {"ingested_count": run_detail.get("ingested_count", 0)},
        fallback_state="missing",
    )
    content_index_refs = [content_index_relative] if content_index_relative else []
    if content_index_relative:
        reports_dir = Path(content_index_relative).parent
        reports_root = review_root / reports_dir
        if reports_root.exists():
            for candidate in sorted(reports_root.iterdir()):
                name = candidate.name
                if name.startswith(f"{run_id}_") and name.endswith("_aps_content_units_v2.json"):
                    content_index_refs.append(normalize_path(review_root, candidate))
    _set_node(
        node_states,
        "content_index",
        mapped_file_refs=content_index_refs,
        summary_metrics=content_index_payload or {
            "indexed_content_units": len([ref for ref in content_index_refs if ref.endswith("_aps_content_units_v2.json")]),
            "indexing_failures_count": 0,
        },
        fallback_state="missing",
    )
    _set_node(
        node_states,
        "search_smoke",
        mapped_file_refs=[summary_relative],
        summary_metrics=summary.get("search_smoke") or {},
        fallback_state="missing" if not summary.get("search_smoke") else "complete",
    )

    branch_a = selected_branch_rows[0] if len(selected_branch_rows) > 0 else {}
    branch_b = selected_branch_rows[1] if len(selected_branch_rows) > 1 else {}

    def _downstream_paths(key: str) -> list[str]:
        return _paths_from_artifact_list(review_root, downstream.get(key))

    bundles = _downstream_paths("evidence_bundles")
    citation_packs = _downstream_paths("citation_packs")
    evidence_reports = _downstream_paths("evidence_reports")
    exports = _downstream_paths("evidence_report_exports")
    export_packages = _downstream_paths("evidence_report_export_packages")
    context_packets = _downstream_paths("context_packets")
    dossiers = _downstream_paths("context_dossiers")
    insights = _downstream_paths("deterministic_insight_artifacts")
    challenges = _downstream_paths("deterministic_challenge_artifacts")
    review_packets = _downstream_paths("deterministic_challenge_review_packets")

    _set_node(node_states, "branch_a_bundle", mapped_file_refs=bundles[:1], summary_metrics={"accession_number": branch_a.get("accession_number"), "target_id": branch_a.get("target_id")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_a_citation_pack", mapped_file_refs=citation_packs[:1], summary_metrics={"accession_number": branch_a.get("accession_number")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_a_evidence_report", mapped_file_refs=evidence_reports[:1], summary_metrics={"accession_number": branch_a.get("accession_number")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_a_export", mapped_file_refs=exports[:1], summary_metrics={"accession_number": branch_a.get("accession_number")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_b_bundle", mapped_file_refs=bundles[1:2], summary_metrics={"accession_number": branch_b.get("accession_number"), "target_id": branch_b.get("target_id")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_b_citation_pack", mapped_file_refs=citation_packs[1:2], summary_metrics={"accession_number": branch_b.get("accession_number")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_b_evidence_report", mapped_file_refs=evidence_reports[1:2], summary_metrics={"accession_number": branch_b.get("accession_number")}, fallback_state="not_exercised")
    _set_node(node_states, "branch_b_export", mapped_file_refs=exports[1:2], summary_metrics={"accession_number": branch_b.get("accession_number")}, fallback_state="not_exercised")
    _set_node(node_states, "export_package", mapped_file_refs=export_packages[:1], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "context_packet_package", mapped_file_refs=context_packets[:1], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "context_packet_export_a", mapped_file_refs=context_packets[1:2], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "context_packet_export_b", mapped_file_refs=context_packets[2:3], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "context_dossier", mapped_file_refs=dossiers[:1], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "deterministic_insight_artifact", mapped_file_refs=insights[:1], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "deterministic_challenge_artifact", mapped_file_refs=challenges[:1], summary_metrics={}, fallback_state="not_exercised")
    _set_node(node_states, "deterministic_challenge_review_packet", mapped_file_refs=review_packets[:1], summary_metrics={}, fallback_state="not_exercised")

    gate_refs = []
    gate_dir = review_root / "gate_reports"
    if gate_dir.exists():
        gate_refs = [normalize_path(review_root, path) for path in sorted(gate_dir.glob("*.json"))]
    _set_node(
        node_states,
        "validate_only_gates",
        mapped_file_refs=gate_refs,
        summary_metrics={
            "gate_count": len(gate_results),
            "passed_count": sum(1 for value in gate_results.values() if value.get("passed")),
            "failed_count": sum(1 for value in gate_results.values() if not value.get("passed")),
        },
        fallback_state="missing",
    )
    return node_states


def build_file_to_node_map(node_states: dict[str, NrcApsReviewRunNodeStateOut]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for node_id, node_state in node_states.items():
        for file_ref in node_state.mapped_file_refs:
            mapping.setdefault(file_ref, []).append(node_id)
    return mapping
