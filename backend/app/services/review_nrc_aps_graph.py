from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.review_nrc_aps import (
    NrcApsReviewCanonicalEdgeOut,
    NrcApsReviewCanonicalGraphOut,
    NrcApsReviewCanonicalNodeOut,
    NrcApsReviewProjectionEdgeOut,
    NrcApsReviewProjectionGraphOut,
    NrcApsReviewProjectionNodeOut,
)
from app.services.review_nrc_aps_runtime import generate_tree_id, load_summary, normalize_path


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

PIPELINE_PROJECTION_NODES = [
    ("source_corpus", "Source corpus", "source", ["source_corpus"], False),
    ("preflight", "Preflight", "preparation", ["preflight"], False),
    ("submission", "Run submitted", "run_lifecycle", ["submission"], False),
    ("artifact_ingestion", "Artifact ingestion", "core_pipeline", ["artifact_ingestion"], False),
    ("content_index", "Content index", "core_pipeline", ["content_index"], False),
    ("search_smoke", "Search smoke", "verification", ["search_smoke"], False),
    ("branch_a", "Branch A", "downstream_branch", ["branch_a_bundle", "branch_a_citation_pack", "branch_a_evidence_report", "branch_a_export"], True),
    ("branch_b", "Branch B", "downstream_branch", ["branch_b_bundle", "branch_b_citation_pack", "branch_b_evidence_report", "branch_b_export"], True),
    ("export_package", "Export package from A+B", "downstream_shared", ["export_package"], False),
    ("context_packet_package", "Context packet from package", "downstream_shared", ["context_packet_package"], False),
    ("context_packet_export_a", "Context packet from Export A", "downstream_shared", ["context_packet_export_a"], False),
    ("context_packet_export_b", "Context packet from Export B", "downstream_shared", ["context_packet_export_b"], False),
    ("context_dossier", "Context dossier from export-derived packets", "downstream_shared", ["context_dossier"], False),
    ("deterministic_insight_artifact", "Deterministic insight artifact", "deterministic", ["deterministic_insight_artifact"], False),
    ("deterministic_challenge_artifact", "Deterministic challenge artifact", "deterministic", ["deterministic_challenge_artifact"], False),
    ("deterministic_challenge_review_packet", "Deterministic challenge review packet", "deterministic", ["deterministic_challenge_review_packet"], False),
    ("validate_only_gates", "Validate-only gates", "verification", ["validate_only_gates"], False),
]

PIPELINE_PROJECTION_EDGES = [
    ("source_corpus", "preflight"),
    ("preflight", "submission"),
    ("submission", "artifact_ingestion"),
    ("artifact_ingestion", "content_index"),
    ("content_index", "search_smoke"),
    ("content_index", "branch_a"),
    ("content_index", "branch_b"),
    ("branch_a", "export_package"),
    ("branch_b", "export_package"),
    ("branch_a", "context_packet_export_a"),
    ("branch_b", "context_packet_export_b"),
    ("export_package", "context_packet_package"),
    ("context_packet_export_a", "context_dossier"),
    ("context_packet_export_b", "context_dossier"),
    ("context_dossier", "deterministic_insight_artifact"),
    ("deterministic_insight_artifact", "deterministic_challenge_artifact"),
    ("deterministic_challenge_artifact", "deterministic_challenge_review_packet"),
    ("deterministic_challenge_review_packet", "validate_only_gates"),
]

CANONICAL_NODE_INDEX = {
    node_id: {
        "label": label,
        "stage_family": stage_family,
        "description": description,
        "expected_artifact_classes": expected_artifact_classes,
    }
    for node_id, label, stage_family, description, expected_artifact_classes in CANONICAL_NODES
}


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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _relative_path(review_root: Path, absolute_or_relative: str | None) -> str | None:
    if not absolute_or_relative:
        return None
    try:
        return normalize_path(review_root, absolute_or_relative)
    except ValueError:
        return None


def _normalize_ref(path: str | None) -> str | None:
    if not path:
        return None
    return path.replace("\\", "/").lower()


def _same_ref(candidate: str | None, target: str | None) -> bool:
    candidate_ref = _normalize_ref(candidate)
    target_ref = _normalize_ref(target)
    if not candidate_ref or not target_ref:
        return False
    return (
        candidate_ref == target_ref
        or candidate_ref.endswith(target_ref)
        or target_ref.endswith(candidate_ref)
    )


def _artifact_refs(items: list[str]) -> list[str]:
    return sorted({Path(item).name for item in items})


def _set_projection_tree_ids(node: NrcApsReviewProjectionNodeOut) -> None:
    node.mapped_tree_ids = sorted({generate_tree_id(path) for path in node.mapped_file_refs})


def _line(*parts: Any) -> str | None:
    content = " | ".join(str(part) for part in parts if part not in (None, "", [], {}))
    return content or None


def _payload_summary(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys if key in payload}


def _build_node(
    projection_id: str,
    title: str,
    stage_family: str,
    canonical_node_ids: list[str],
    *,
    detail_lines: list[str] | None = None,
    state: str = "unknown",
    warnings: list[str] | None = None,
    mapped_file_refs: list[str] | None = None,
    artifact_refs: list[str] | None = None,
    structured_summary: dict[str, Any] | None = None,
    is_composite: bool = False,
) -> NrcApsReviewProjectionNodeOut:
    node = NrcApsReviewProjectionNodeOut(
        projection_id=projection_id,
        title=title,
        detail_lines=[line for line in (detail_lines or []) if line],
        stage_family=stage_family,
        canonical_node_ids=canonical_node_ids,
        state=state,
        warnings=warnings or [],
        mapped_file_refs=sorted(set(mapped_file_refs or [])),
        artifact_refs=sorted(set(artifact_refs or _artifact_refs(mapped_file_refs or []))),
        structured_summary=structured_summary or {},
        is_composite=is_composite,
    )
    _set_projection_tree_ids(node)
    return node


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


def _load_downstream_artifacts(review_root: Path, summary: dict[str, Any]) -> list[dict[str, Any]]:
    downstream = summary.get("downstream_artifacts") or {}
    artifacts: list[dict[str, Any]] = []
    for items in downstream.values():
        for item in items or []:
            ref = _relative_path(review_root, item.get("ref"))
            if not ref:
                continue
            artifacts.append({"path": ref, "name": Path(ref).name, "payload": _load_json(review_root / ref)})
    return artifacts


def _find_content_units_paths(review_root: Path, run_id: str) -> list[str]:
    reports_root = review_root / "storage" / "connectors" / "reports"
    if not reports_root.exists():
        return []
    return [
        normalize_path(review_root, candidate)
        for candidate in sorted(reports_root.iterdir())
        if candidate.is_file() and candidate.name.startswith(f"{run_id}_") and candidate.name.endswith("_aps_content_units_v2.json")
    ]


def _branch_anchors(summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    selected = summary.get("selected_branch_rows") or []
    branch_a = selected[0] if len(selected) > 0 and isinstance(selected[0], dict) else {}
    branch_b = selected[1] if len(selected) > 1 and isinstance(selected[1], dict) else {}
    return branch_a, branch_b


def _payload_ref(payload: dict[str, Any], *keys: str) -> str | None:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


def _source_target_ids(payload: dict[str, Any]) -> list[str]:
    filters = payload.get("normalized_request", {}).get("filters", {})
    target_ids = filters.get("target_ids")
    if isinstance(target_ids, list):
        return [value for value in target_ids if isinstance(value, str)]
    return []


def _find_first_matching_artifact(artifacts: list[dict[str, Any]], suffix: str, predicate) -> dict[str, Any] | None:
    for artifact in artifacts:
        if artifact["name"].endswith(suffix) and predicate(artifact["payload"]):
            return artifact
    return None


def _collect_run_projection_inputs(run_id: str, review_root: Path) -> dict[str, Any]:
    summary = load_summary(review_root)
    downstream = _load_downstream_artifacts(review_root, summary)
    branch_a, branch_b = _branch_anchors(summary)

    branch_data: dict[str, dict[str, Any]] = {}
    for branch_key, anchor in (("a", branch_a), ("b", branch_b)):
        target_id = anchor.get("target_id")
        content_id = anchor.get("content_id")
        accession = anchor.get("accession_number")
        bundle = _find_first_matching_artifact(
            downstream,
            "_aps_evidence_bundle_v2.json",
            lambda payload, target_id=target_id: target_id in _source_target_ids(payload),
        )
        citation = _find_first_matching_artifact(
            downstream,
            "_aps_evidence_citation_pack_v2.json",
            lambda payload, bundle=bundle: bool(bundle)
            and _same_ref(_payload_ref(payload, "source_bundle", "bundle_ref"), bundle["path"]),
        )
        report = _find_first_matching_artifact(
            downstream,
            "_aps_evidence_report_v1.json",
            lambda payload, citation=citation: bool(citation)
            and _same_ref(_payload_ref(payload, "source_citation_pack", "citation_pack_ref"), citation["path"]),
        )
        export = _find_first_matching_artifact(
            downstream,
            "_aps_evidence_report_export_v1.json",
            lambda payload, report=report: bool(report)
            and _same_ref(_payload_ref(payload, "source_evidence_report", "evidence_report_ref"), report["path"]),
        )
        context_packet = _find_first_matching_artifact(
            downstream,
            "_aps_context_packet_v1.json",
            lambda payload, export=export: (
                _payload_ref(payload, "source_descriptor", "source_family") == "evidence_report_export"
                and bool(export)
                and _same_ref(_payload_ref(payload, "source_descriptor", "source_ref"), export["path"])
            ),
        )

        branch_data[branch_key] = {
            "anchor": anchor,
            "accession": accession,
            "target_id": target_id,
            "content_id": content_id,
            "bundle": bundle,
            "citation": citation,
            "report": report,
            "export": export,
            "context_packet": context_packet,
        }

    export_package = _find_first_matching_artifact(
        downstream,
        "_aps_evidence_report_export_package_v1.json",
        lambda payload, branch_data=branch_data: any(
            _same_ref(export_ref, branch_data[branch_key]["export"]["path"])
            for export_ref in [
                entry.get("evidence_report_export_ref")
                for entry in payload.get("source_exports", [])
                if isinstance(entry, dict)
            ]
            for branch_key in ("a", "b")
            if branch_data[branch_key]["export"]
        ),
    )
    package_context_packet = _find_first_matching_artifact(
        downstream,
        "_aps_context_packet_v1.json",
        lambda payload, export_package=export_package: (
            _payload_ref(payload, "source_descriptor", "source_family") == "evidence_report_export_package"
            and bool(export_package)
            and _same_ref(_payload_ref(payload, "source_descriptor", "source_ref"), export_package["path"])
        ),
    )
    context_dossier = _find_first_matching_artifact(
        downstream,
        "_aps_context_dossier_v1.json",
        lambda payload, branch_data=branch_data: (
            len([branch_key for branch_key in ("a", "b") if branch_data[branch_key]["context_packet"]]) == len(payload.get("source_packets", []))
            and all(
                any(
                    _same_ref(entry.get("context_packet_ref"), branch_data[branch_key]["context_packet"]["path"])
                    for entry in payload.get("source_packets", [])
                    if isinstance(entry, dict)
                )
                for branch_key in ("a", "b")
                if branch_data[branch_key]["context_packet"]
            )
        ),
    )
    insight = _find_first_matching_artifact(
        downstream,
        "_aps_deterministic_insight_artifact_v1.json",
        lambda payload, context_dossier=context_dossier: bool(context_dossier)
        and _same_ref(_payload_ref(payload, "source_context_dossier", "context_dossier_ref"), context_dossier["path"]),
    )
    challenge = _find_first_matching_artifact(
        downstream,
        "_aps_deterministic_challenge_artifact_v1.json",
        lambda payload, insight=insight: bool(insight)
        and _same_ref(
            _payload_ref(payload, "source_deterministic_insight_artifact", "deterministic_insight_artifact_ref"),
            insight["path"],
        ),
    )
    review_packet = _find_first_matching_artifact(
        downstream,
        "_aps_deterministic_challenge_review_packet_v1.json",
        lambda payload, challenge=challenge: bool(challenge)
        and _same_ref(
            _payload_ref(payload, "source_deterministic_challenge_artifact", "deterministic_challenge_artifact_ref"),
            challenge["path"],
        ),
    )

    gate_reports_root = review_root / "gate_reports"
    gate_reports = [
        normalize_path(review_root, candidate)
        for candidate in sorted(gate_reports_root.glob("*.json"))
        if candidate.is_file()
    ]
    return {
        "summary": summary,
        "branch_data": branch_data,
        "export_package": export_package,
        "package_context_packet": package_context_packet,
        "context_dossier": context_dossier,
        "insight": insight,
        "challenge": challenge,
        "review_packet": review_packet,
        "gate_reports": gate_reports,
        "gate_results": summary.get("gate_results") or {},
        "search_smoke": summary.get("search_smoke") or {},
        "advanced_metrics": summary.get("advanced_metrics") or {},
        "run_detail": summary.get("run_detail") or {},
        "submission": summary.get("submission") or {},
        "preflight": summary.get("preflight") or {},
        "content_units_paths": _find_content_units_paths(review_root, run_id),
    }


def build_pipeline_projection(run_id: str, review_root: Path) -> NrcApsReviewProjectionGraphOut:
    inputs = _collect_run_projection_inputs(run_id, review_root)
    summary = inputs["summary"]
    branch_data = inputs["branch_data"]
    nodes: list[NrcApsReviewProjectionNodeOut] = []

    for projection_id, title, stage_family, canonical_node_ids, is_composite in PIPELINE_PROJECTION_NODES:
        detail_lines: list[str] = []
        mapped_file_refs: list[str] = []
        warnings: list[str] = []
        structured_summary: dict[str, Any] = {}

        if projection_id == "source_corpus":
            detail_lines.append(_line(f"{summary.get('corpus_pdf_count', 0)} PDFs"))
            structured_summary = {"corpus_pdf_count": summary.get("corpus_pdf_count", 0)}
            mapped_file_refs = ["local_corpus_e2e_summary.json"]
        elif projection_id == "preflight":
            detail_lines.append(_line(f"passed={inputs['preflight'].get('passed', False)}"))
            structured_summary = _payload_summary(inputs["preflight"], ["passed"])
            mapped_file_refs = ["local_corpus_e2e_summary.json"]
        elif projection_id == "submission":
            detail_lines.extend([
                _line(f"run={run_id}"),
                _line(
                    f"selected={inputs['submission'].get('selected_count', 0)}",
                    f"downloaded={inputs['submission'].get('downloaded_count', 0)}",
                    f"failed={inputs['submission'].get('failed_count', 0)}",
                ),
            ])
            structured_summary = _payload_summary(inputs["submission"], ["status", "selected_count", "downloaded_count", "failed_count"])
            mapped_file_refs = ["local_corpus_e2e_summary.json", f"storage/connectors/reports/{run_id}_run_summary.json"]
            warnings = _extract_missing_report_warnings(review_root, {"artifact_dedup_report": (inputs["run_detail"].get("report_refs") or {}).get("artifact_dedup_report")})
        elif projection_id == "artifact_ingestion":
            detail_lines.append(_line(f"processed_targets={inputs['run_detail'].get('processed_targets')}"))
            detail_lines.append(_line(f"outcome_counts={inputs['run_detail'].get('outcome_counts')}"))
            structured_summary = _payload_summary(inputs["run_detail"], ["processed_targets", "outcome_counts"])
            mapped_file_refs = [f"storage/connectors/reports/{run_id}_aps_artifact_ingestion_run_v1.json"]
        elif projection_id == "content_index":
            detail_lines.append(_line(f"indexed_content_units={inputs['run_detail'].get('indexed_content_units')}"))
            detail_lines.append(_line(f"indexing_failures_count={inputs['run_detail'].get('indexing_failures_count')}"))
            structured_summary = _payload_summary(inputs["run_detail"], ["indexed_content_units", "indexing_failures_count"])
            mapped_file_refs = [f"storage/connectors/reports/{run_id}_aps_content_index_run_v1.json", *inputs["content_units_paths"]]
        elif projection_id == "search_smoke":
            detail_lines.append(_line(f"token={inputs['search_smoke'].get('token')}"))
            detail_lines.append(_line(f"hit_count={inputs['search_smoke'].get('hit_count')}"))
            structured_summary = _payload_summary(inputs["search_smoke"], ["token", "hit_count"])
            mapped_file_refs = ["local_corpus_e2e_summary.json"]
        elif projection_id in ("branch_a", "branch_b"):
            branch = branch_data["a" if projection_id == "branch_a" else "b"]
            detail_lines.extend([
                _line(branch.get("anchor", {}).get("accession_number"), branch.get("target_id")),
                _line(branch.get("anchor", {}).get("content_id")),
                _line("bundle -> citation pack -> evidence report -> export"),
            ])
            structured_summary = {
                "accession_number": branch.get("accession"),
                "target_id": branch.get("target_id"),
                "content_id": branch.get("content_id"),
            }
            mapped_file_refs = [
                artifact["path"]
                for artifact in (branch.get("bundle"), branch.get("citation"), branch.get("report"), branch.get("export"))
                if artifact
            ]
        elif projection_id == "export_package":
            payload = (inputs["export_package"] or {}).get("payload", {})
            detail_lines.append(_line(f"source_export_count={payload.get('source_export_count')}"))
            structured_summary = _payload_summary(payload, ["source_export_count", "total_citations"])
            mapped_file_refs = [inputs["export_package"]["path"]] if inputs["export_package"] else []
        elif projection_id == "context_packet_package":
            payload = (inputs["package_context_packet"] or {}).get("payload", {})
            detail_lines.append(_line(f"source_family={payload.get('source_descriptor', {}).get('source_family')}"))
            structured_summary = {"source_family": payload.get("source_descriptor", {}).get("source_family")}
            mapped_file_refs = [inputs["package_context_packet"]["path"]] if inputs["package_context_packet"] else []
        elif projection_id == "context_packet_export_a":
            payload = (branch_data["a"].get("context_packet") or {}).get("payload", {})
            detail_lines.append(_line(f"source_family={payload.get('source_descriptor', {}).get('source_family')}"))
            structured_summary = {"source_family": payload.get("source_descriptor", {}).get("source_family")}
            mapped_file_refs = [branch_data["a"]["context_packet"]["path"]] if branch_data["a"].get("context_packet") else []
        elif projection_id == "context_packet_export_b":
            payload = (branch_data["b"].get("context_packet") or {}).get("payload", {})
            detail_lines.append(_line(f"source_family={payload.get('source_descriptor', {}).get('source_family')}"))
            structured_summary = {"source_family": payload.get("source_descriptor", {}).get("source_family")}
            mapped_file_refs = [branch_data["b"]["context_packet"]["path"]] if branch_data["b"].get("context_packet") else []
        elif projection_id == "context_dossier":
            payload = (inputs["context_dossier"] or {}).get("payload", {})
            detail_lines.append(_line(f"total_facts={payload.get('total_facts')}", f"total_constraints={payload.get('total_constraints')}"))
            structured_summary = _payload_summary(payload, ["total_facts", "total_constraints"])
            mapped_file_refs = [inputs["context_dossier"]["path"]] if inputs["context_dossier"] else []
        elif projection_id == "deterministic_insight_artifact":
            payload = (inputs["insight"] or {}).get("payload", {})
            detail_lines.append(_line(f"total_findings={payload.get('total_findings')}"))
            structured_summary = _payload_summary(payload, ["total_findings"])
            mapped_file_refs = [inputs["insight"]["path"]] if inputs["insight"] else []
        elif projection_id == "deterministic_challenge_artifact":
            payload = (inputs["challenge"] or {}).get("payload", {})
            detail_lines.append(_line(f"total_challenges={payload.get('total_challenges')}"))
            structured_summary = _payload_summary(payload, ["total_challenges"])
            mapped_file_refs = [inputs["challenge"]["path"]] if inputs["challenge"] else []
        elif projection_id == "deterministic_challenge_review_packet":
            payload = (inputs["review_packet"] or {}).get("payload", {})
            detail_lines.append(_line(f"review_item_count={payload.get('review_item_count')}"))
            structured_summary = _payload_summary(payload, ["review_item_count", "acknowledgement_count", "blocker_count"])
            mapped_file_refs = [inputs["review_packet"]["path"]] if inputs["review_packet"] else []
        elif projection_id == "validate_only_gates":
            passed = sum(1 for value in inputs["gate_results"].values() if isinstance(value, dict) and value.get("passed") is True)
            total = len(inputs["gate_results"])
            detail_lines.append(_line(f"{passed} passed of {total}"))
            structured_summary = {"gate_total": total, "gate_passed": passed}
            mapped_file_refs = inputs["gate_reports"]

        nodes.append(
            _build_node(
                projection_id,
                title,
                stage_family,
                canonical_node_ids,
                detail_lines=detail_lines,
                state="complete",
                warnings=warnings,
                mapped_file_refs=mapped_file_refs,
                structured_summary=structured_summary,
                is_composite=is_composite,
            )
        )

    return NrcApsReviewProjectionGraphOut(
        projection_id=f"nrc_aps_pipeline_projection::{run_id}",
        nodes=nodes,
        edges=[NrcApsReviewProjectionEdgeOut(source_id=source_id, target_id=target_id) for source_id, target_id in PIPELINE_PROJECTION_EDGES],
    )


def build_run_projection(run_id: str, review_root: Path) -> NrcApsReviewProjectionGraphOut:
    inputs = _collect_run_projection_inputs(run_id, review_root)
    summary = inputs["summary"]
    branch_data = inputs["branch_data"]
    nodes: list[NrcApsReviewProjectionNodeOut] = []

    run_detail_report = f"storage/connectors/reports/{run_id}_run_summary.json"
    ingestion_report = f"storage/connectors/reports/{run_id}_aps_artifact_ingestion_run_v1.json"
    index_report = f"storage/connectors/reports/{run_id}_aps_content_index_run_v1.json"

    branch_artifacts = {
        "branch_a_bundle": branch_data["a"].get("bundle"),
        "branch_a_citation_pack": branch_data["a"].get("citation"),
        "branch_a_evidence_report": branch_data["a"].get("report"),
        "branch_a_export": branch_data["a"].get("export"),
        "branch_b_bundle": branch_data["b"].get("bundle"),
        "branch_b_citation_pack": branch_data["b"].get("citation"),
        "branch_b_evidence_report": branch_data["b"].get("report"),
        "branch_b_export": branch_data["b"].get("export"),
    }

    for node_id, label, stage_family, _, _ in CANONICAL_NODES:
        warnings: list[str] = []
        detail_lines: list[str] = []
        mapped_file_refs: list[str] = []
        structured_summary: dict[str, Any] = {}

        if node_id == "source_corpus":
            detail_lines.extend([
                _line(Path(str(summary.get("source_root", ""))).name or "data_demo/nrc_adams_documents_for_testing"),
                _line(f"{summary.get('corpus_pdf_count', 0)} PDFs"),
            ])
            mapped_file_refs = ["local_corpus_e2e_summary.json"]
            structured_summary = {"corpus_pdf_count": summary.get("corpus_pdf_count", 0)}
        elif node_id == "preflight":
            detail_lines.extend([
                _line("local_corpus_e2e_summary.json"),
                _line(f"passed={inputs['preflight'].get('passed', False)}"),
                _line(f"ocr_file_count={inputs['advanced_metrics'].get('ocr_file_count', 0)}", f"visual_ref_total={summary.get('visual_ref_total', 0)}"),
            ])
            mapped_file_refs = ["local_corpus_e2e_summary.json"]
            structured_summary = {
                "passed": inputs["preflight"].get("passed", False),
                "ocr_file_count": inputs["advanced_metrics"].get("ocr_file_count", 0),
                "visual_ref_total": summary.get("visual_ref_total", 0),
            }
        elif node_id == "submission":
            detail_lines.extend([
                _line(f"{run_id}_run_summary.json"),
                _line(f"status={inputs['run_detail'].get('status')}"),
                _line(f"{inputs['submission'].get('discovered_count', 0)} discovered", f"{inputs['submission'].get('selected_count', 0)} selected/{summary.get('corpus_pdf_count', 0)}"),
                _line(f"downloaded={inputs['submission'].get('downloaded_count', 0)}", f"failed={inputs['submission'].get('failed_count', 0)}"),
            ])
            mapped_file_refs = ["local_corpus_e2e_summary.json", run_detail_report]
            warnings = _extract_missing_report_warnings(review_root, {"artifact_dedup_report": (inputs["run_detail"].get("report_refs") or {}).get("artifact_dedup_report")})
            structured_summary = {
                "status": inputs["run_detail"].get("status"),
                **_payload_summary(inputs["submission"], ["discovered_count", "selected_count", "downloaded_count", "failed_count"]),
            }
        elif node_id == "artifact_ingestion":
            detail_lines.extend([
                _line(f"{run_id}_aps_artifact_ingestion_run_v1.json"),
                _line(f"processed_targets={inputs['run_detail'].get('processed_targets')}"),
                _line(f"outcome_counts={inputs['run_detail'].get('outcome_counts')}"),
            ])
            mapped_file_refs = [ingestion_report]
            structured_summary = _payload_summary(inputs["run_detail"], ["processed_targets", "outcome_counts"])
        elif node_id == "content_index":
            detail_lines.extend([
                _line(f"{run_id}_aps_content_index_run_v1.json"),
                _line(f"indexed_content_units={inputs['run_detail'].get('indexed_content_units')}"),
                _line(f"indexing_failures_count={inputs['run_detail'].get('indexing_failures_count')}"),
            ])
            mapped_file_refs = [index_report, *inputs["content_units_paths"]]
            structured_summary = _payload_summary(inputs["run_detail"], ["indexed_content_units", "indexing_failures_count"])
        elif node_id == "search_smoke":
            detail_lines.extend([
                _line("local_corpus_e2e_summary.json::search_smoke"),
                _line(f"token={inputs['search_smoke'].get('token')}"),
                _line(f"hit_count={inputs['search_smoke'].get('hit_count')}"),
            ])
            mapped_file_refs = ["local_corpus_e2e_summary.json"]
            structured_summary = _payload_summary(inputs["search_smoke"], ["token", "hit_count"])
        elif node_id.startswith("branch_a_") or node_id.startswith("branch_b_"):
            branch_key = "a" if node_id.startswith("branch_a_") else "b"
            branch = branch_data[branch_key]
            artifact = branch_artifacts.get(node_id)
            payload = artifact.get("payload", {}) if artifact else {}
            detail_lines.extend([
                _line(branch.get("accession"), branch.get("target_id")),
                _line(branch.get("content_id")),
            ])
            if artifact:
                detail_lines.append(_line(artifact["name"]))
                if node_id.endswith("_bundle"):
                    detail_lines.append(_line(f"total_hits={payload.get('total_hits')}"))
                elif node_id.endswith("_citation_pack"):
                    detail_lines.append(_line(f"total_citations={payload.get('total_citations')}"))
                elif node_id.endswith("_evidence_report"):
                    detail_lines.append(_line(f"total_sections={payload.get('total_sections')}", f"total_citations={payload.get('total_citations')}"))
                elif node_id.endswith("_export"):
                    detail_lines.append(_line(f"format_id={payload.get('format_id')}"))
                mapped_file_refs = [artifact["path"]]
                structured_summary = _payload_summary(payload, ["total_hits", "total_citations", "total_sections", "format_id"])
            else:
                warnings.append("mismatch: expected branch artifact missing")
        elif node_id == "export_package":
            payload = (inputs["export_package"] or {}).get("payload", {})
            if inputs["export_package"]:
                detail_lines.extend([
                    _line(inputs["export_package"]["name"]),
                    _line(f"source_export_count={payload.get('source_export_count')}"),
                    _line(f"total_citations={payload.get('total_citations')}"),
                ])
                mapped_file_refs = [inputs["export_package"]["path"]]
                structured_summary = _payload_summary(payload, ["source_export_count", "total_citations"])
            else:
                warnings.append("mismatch: export package missing")
        elif node_id == "context_packet_package":
            payload = (inputs["package_context_packet"] or {}).get("payload", {})
            if inputs["package_context_packet"]:
                detail_lines.extend([
                    _line(inputs["package_context_packet"]["name"]),
                    _line(f"source_family={payload.get('source_descriptor', {}).get('source_family')}"),
                    _line(f"source_ref={Path(str(payload.get('source_descriptor', {}).get('source_ref', ''))).name}"),
                ])
                mapped_file_refs = [inputs["package_context_packet"]["path"]]
                structured_summary = {"source_family": payload.get("source_descriptor", {}).get("source_family")}
            else:
                warnings.append("mismatch: package context packet missing")
        elif node_id == "context_packet_export_a":
            artifact = branch_data["a"].get("context_packet")
            payload = artifact.get("payload", {}) if artifact else {}
            if artifact:
                detail_lines.extend([
                    _line(artifact["name"]),
                    _line(f"source_family={payload.get('source_descriptor', {}).get('source_family')}"),
                    _line(f"source_ref={Path(str(payload.get('source_descriptor', {}).get('source_ref', ''))).name}"),
                ])
                mapped_file_refs = [artifact["path"]]
                structured_summary = {"source_family": payload.get("source_descriptor", {}).get("source_family")}
            else:
                warnings.append("mismatch: branch A export packet missing")
        elif node_id == "context_packet_export_b":
            artifact = branch_data["b"].get("context_packet")
            payload = artifact.get("payload", {}) if artifact else {}
            if artifact:
                detail_lines.extend([
                    _line(artifact["name"]),
                    _line(f"source_family={payload.get('source_descriptor', {}).get('source_family')}"),
                    _line(f"source_ref={Path(str(payload.get('source_descriptor', {}).get('source_ref', ''))).name}"),
                ])
                mapped_file_refs = [artifact["path"]]
                structured_summary = {"source_family": payload.get("source_descriptor", {}).get("source_family")}
            else:
                warnings.append("mismatch: branch B export packet missing")
        elif node_id == "context_dossier":
            payload = (inputs["context_dossier"] or {}).get("payload", {})
            if inputs["context_dossier"]:
                detail_lines.extend([
                    _line(inputs["context_dossier"]["name"]),
                    _line(f"total_facts={payload.get('total_facts')}", f"total_constraints={payload.get('total_constraints')}"),
                ])
                mapped_file_refs = [inputs["context_dossier"]["path"]]
                structured_summary = _payload_summary(payload, ["total_facts", "total_constraints"])
            else:
                warnings.append("mismatch: context dossier missing")
        elif node_id == "deterministic_insight_artifact":
            payload = (inputs["insight"] or {}).get("payload", {})
            if inputs["insight"]:
                detail_lines.extend([
                    _line(inputs["insight"]["name"]),
                    _line(f"total_findings={payload.get('total_findings')}"),
                ])
                mapped_file_refs = [inputs["insight"]["path"]]
                structured_summary = _payload_summary(payload, ["total_findings"])
            else:
                warnings.append("mismatch: insight artifact missing")
        elif node_id == "deterministic_challenge_artifact":
            payload = (inputs["challenge"] or {}).get("payload", {})
            if inputs["challenge"]:
                detail_lines.extend([
                    _line(inputs["challenge"]["name"]),
                    _line(f"total_challenges={payload.get('total_challenges')}"),
                    _line(f"dispositions={payload.get('dispositions')}"),
                ])
                mapped_file_refs = [inputs["challenge"]["path"]]
                structured_summary = _payload_summary(payload, ["total_challenges", "dispositions"])
            else:
                warnings.append("mismatch: challenge artifact missing")
        elif node_id == "deterministic_challenge_review_packet":
            payload = (inputs["review_packet"] or {}).get("payload", {})
            if inputs["review_packet"]:
                detail_lines.extend([
                    _line(inputs["review_packet"]["name"]),
                    _line(f"review_item_count={payload.get('review_item_count')}"),
                    _line(f"acknowledgement_count={payload.get('acknowledgement_count')}", f"blocker_count={payload.get('blocker_count')}"),
                ])
                mapped_file_refs = [inputs["review_packet"]["path"]]
                structured_summary = _payload_summary(payload, ["review_item_count", "acknowledgement_count", "blocker_count"])
            else:
                warnings.append("mismatch: challenge review packet missing")
        elif node_id == "validate_only_gates":
            passed = sum(1 for value in inputs["gate_results"].values() if isinstance(value, dict) and value.get("passed") is True)
            total = len(inputs["gate_results"])
            detail_lines.extend([_line("gate_reports/*.json"), _line(f"{passed} passed", f"{total - passed} failed")])
            mapped_file_refs = inputs["gate_reports"]
            structured_summary = {"gate_total": total, "gate_passed": passed, "gate_results": inputs["gate_results"]}

        state = "complete" if mapped_file_refs or node_id in {"source_corpus", "preflight", "search_smoke"} else "missing"
        if warnings:
            state = "mismatch" if state == "complete" else "missing"

        nodes.append(
            _build_node(
                node_id,
                label,
                stage_family,
                [node_id],
                detail_lines=detail_lines,
                state=state,
                warnings=warnings,
                mapped_file_refs=mapped_file_refs,
                structured_summary=structured_summary,
            )
        )

    return NrcApsReviewProjectionGraphOut(
        projection_id=f"nrc_aps_run_projection::{run_id}",
        nodes=nodes,
        edges=[NrcApsReviewProjectionEdgeOut(source_id=source_id, target_id=target_id) for source_id, target_id in CANONICAL_EDGES],
    )


def build_file_to_node_map(projection: NrcApsReviewProjectionGraphOut) -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = {}
    for node in projection.nodes:
        for file_ref in node.mapped_file_refs:
            mapping.setdefault(file_ref, set()).add(node.projection_id)
    return {path: sorted(node_ids) for path, node_ids in mapping.items()}


def get_run_projection_node(run_projection: NrcApsReviewProjectionGraphOut, node_id: str) -> NrcApsReviewProjectionNodeOut | None:
    for node in run_projection.nodes:
        if node.projection_id == node_id:
            return node
    return None
