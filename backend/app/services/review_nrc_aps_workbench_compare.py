from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import and_

from app.models.models import ApsContentLinkage, ConnectorRunTarget
from app.schemas.review_nrc_aps import (
    NrcApsWorkbenchCompareBadgeOut,
    NrcApsWorkbenchCompareBundleBindingOut,
    NrcApsWorkbenchCompareBundleSourceItemOut,
    NrcApsWorkbenchCompareColumnOut,
    NrcApsWorkbenchCompareDeepLinksOut,
    NrcApsWorkbenchCompareManifestOut,
    NrcApsWorkbenchCompareRunBindingOut,
    NrcApsWorkbenchCompareRunSourceItemOut,
    NrcApsWorkbenchCompareSourceIdentityOut,
    NrcApsWorkbenchCompareSourcesOut,
    NrcApsWorkbenchCompareTabDefOut,
    NrcApsWorkbenchCompareTabOut,
    NrcApsWorkbenchCompareTargetItemOut,
    NrcApsWorkbenchCompareTargetsOut,
    NrcApsWorkbenchCompareVariantBindingsOut,
)
from app.services.review_nrc_aps_catalog import discover_candidate_runs
from app.services.review_nrc_aps_document_trace import (
    _resolve_document_title,
    _resolve_document_type,
    compose_diagnostics_payload,
    compose_extracted_units_payload,
    compose_normalized_text_payload,
    compose_trace_manifest,
)
from app.services.review_nrc_aps_runtime import (
    ReviewRuntimeBinding,
    classify_runtime_binding_variant,
    discover_runtime_bindings,
)
from app.services.review_nrc_aps_runtime_db import runtime_db_session_for_binding


_TAB_LABELS: dict[str, str] = {
    "summary": "Summary",
    "normalized_text": "Normalized Text",
    "diagnostics": "Diagnostics",
    "structure": "Structure",
}
_COMPARABILITY_LEGEND: dict[str, str] = {
    "direct": "Directly comparable against the owner-path variants.",
    "derived_only": "Derived overlay only; useful for interpretation but not a replacement.",
    "non_equivalent": "Present for contrast, but not semantically equivalent to the owner path.",
    "missing": "Unavailable for this variant in the selected source set.",
}
_REQUIRED_BUNDLE_FILES: tuple[str, ...] = (
    "baseline-summary.json",
    "compare.json",
    "proof.json",
    "retain.json",
)


@dataclass(frozen=True)
class _RuntimeCompareTarget:
    fixture_id: str
    run_id: str
    target_id: str
    content_id: str | None
    accession_number: str | None
    source_file_name: str | None
    document_title: str | None
    document_type: str | None


@dataclass(frozen=True)
class _BundleArtifacts:
    bundle_id: str
    bundle_root: Path
    baseline_summary: dict[str, Any]
    compare: dict[str, Any]
    proof: dict[str, Any]
    retain: dict[str, Any]


def _checkout_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_json_object:{path.name}")
    return payload


def _corpus_manifest_path(checkout_root: Path) -> Path:
    return checkout_root / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"


def _load_manifest_entries(checkout_root: Path) -> list[dict[str, Any]]:
    payload = _read_json(_corpus_manifest_path(checkout_root))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_corpus_manifest_entries")
    out: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            out.append(entry)
    return out


def _manifest_entries_by_basename(checkout_root: Path) -> dict[str, dict[str, Any] | None]:
    by_basename: dict[str, dict[str, Any] | None] = {}
    for entry in _load_manifest_entries(checkout_root):
        basename = Path(str(entry.get("path") or "")).name.strip().lower()
        if not basename:
            continue
        if basename in by_basename:
            by_basename[basename] = None
            continue
        by_basename[basename] = entry
    return by_basename


def _canonical_bundle_id(root: Path, checkout_root: Path) -> str:
    return root.resolve().relative_to(checkout_root.resolve()).as_posix()


def _parse_public_bundle_id(bundle_id: str) -> PurePosixPath:
    normalized = str(bundle_id or "").strip().replace("\\", "/")
    if not normalized:
        raise ValueError("candidate_b_bundle_id_missing")
    pure = PurePosixPath(normalized)
    if pure.is_absolute():
        raise ValueError("candidate_b_bundle_id_invalid")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("candidate_b_bundle_id_invalid")
    return pure


def discover_candidate_b_bundle_roots(checkout_root: Path | None = None) -> list[Path]:
    root = (checkout_root or _checkout_root()).resolve()
    candidates: list[Path] = []

    archive_root = root / "archive"
    if archive_root.exists():
        for stamp_dir in sorted((entry for entry in archive_root.iterdir() if entry.is_dir()), key=lambda item: item.name):
            for bundle_dir in sorted((entry for entry in stamp_dir.iterdir() if entry.is_dir() and entry.name.startswith("cb-proof-")), key=lambda item: item.name):
                candidates.append(bundle_dir.resolve())

    reports_root = root / "tests" / "reports"
    if reports_root.exists():
        for bundle_dir in sorted((entry for entry in reports_root.iterdir() if entry.is_dir() and entry.name.startswith("cb-compare-")), key=lambda item: item.name):
            candidates.append(bundle_dir.resolve())

    discovered: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if str(candidate) in seen:
            continue
        seen.add(str(candidate))
        if all((candidate / name).is_file() for name in _REQUIRED_BUNDLE_FILES):
            discovered.append(candidate)
    return discovered


def resolve_candidate_b_bundle_root(bundle_id: str, checkout_root: Path | None = None) -> Path:
    root = (checkout_root or _checkout_root()).resolve()
    requested_rel = _parse_public_bundle_id(bundle_id)
    requested_root = (root / Path(*requested_rel.parts)).resolve()
    discovered = {candidate.resolve() for candidate in discover_candidate_b_bundle_roots(root)}
    if requested_root not in discovered:
        raise ValueError("candidate_b_bundle_unavailable")
    return requested_root


def _load_bundle_artifacts(bundle_id: str, checkout_root: Path | None = None) -> _BundleArtifacts:
    root = (checkout_root or _checkout_root()).resolve()
    bundle_root = resolve_candidate_b_bundle_root(bundle_id, root)
    return _BundleArtifacts(
        bundle_id=_canonical_bundle_id(bundle_root, root),
        bundle_root=bundle_root,
        baseline_summary=_read_json(bundle_root / "baseline-summary.json"),
        compare=_read_json(bundle_root / "compare.json"),
        proof=_read_json(bundle_root / "proof.json"),
        retain=_read_json(bundle_root / "retain.json"),
    )


def _bundle_documents_by_fixture(compare_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = compare_payload.get("documents")
    if not isinstance(documents, list):
        raise ValueError("candidate_b_compare_documents_missing")
    out: dict[str, dict[str, Any]] = {}
    for entry in documents:
        if not isinstance(entry, dict):
            continue
        fixture_id = str(entry.get("fixture_id") or "").strip()
        if fixture_id:
            out[fixture_id] = entry
    return out


def _variant_sort_key(item: NrcApsWorkbenchCompareRunSourceItemOut) -> tuple[str, str]:
    return (item.completed_at or "", item.run_id)


def _selector_by_run_id() -> dict[str, Any]:
    return {item.run_id: item for item in discover_candidate_runs().runs}


def discover_workbench_compare_sources(checkout_root: Path | None = None) -> NrcApsWorkbenchCompareSourcesOut:
    root = (checkout_root or _checkout_root()).resolve()
    selector_by_run_id = _selector_by_run_id()

    baseline_runs: list[NrcApsWorkbenchCompareRunSourceItemOut] = []
    candidate_a_runs: list[NrcApsWorkbenchCompareRunSourceItemOut] = []

    for binding in discover_runtime_bindings():
        selector_item = selector_by_run_id.get(binding.run_id)
        if selector_item is None or not selector_item.reviewable:
            continue
        variant_kind = classify_runtime_binding_variant(binding)
        if variant_kind not in {"baseline", "candidate_a_page_evidence_v1"}:
            continue
        item = NrcApsWorkbenchCompareRunSourceItemOut(
            run_id=binding.run_id,
            display_label=str(selector_item.display_label or binding.run_id),
            completed_at=selector_item.completed_at,
            variant_kind=variant_kind,
        )
        if variant_kind == "baseline":
            baseline_runs.append(item)
        else:
            candidate_a_runs.append(item)

    baseline_runs.sort(key=_variant_sort_key, reverse=True)
    candidate_a_runs.sort(key=_variant_sort_key, reverse=True)

    candidate_b_bundles: list[NrcApsWorkbenchCompareBundleSourceItemOut] = []
    for bundle_root in discover_candidate_b_bundle_roots(root):
        bundle_id = _canonical_bundle_id(bundle_root, root)
        compare_payload = _read_json(bundle_root / "compare.json")
        generated_at_utc = str(compare_payload.get("generated_at_utc") or "").strip() or None
        decision_recommendation = str(compare_payload.get("decision_recommendation") or "").strip() or None
        display_label = f"{bundle_root.name} | {decision_recommendation or 'unknown'}"
        candidate_b_bundles.append(
            NrcApsWorkbenchCompareBundleSourceItemOut(
                bundle_id=bundle_id,
                display_label=display_label,
                generated_at_utc=generated_at_utc,
                decision_recommendation=decision_recommendation,
                local_only=True,
            )
        )

    candidate_b_bundles.sort(key=lambda item: ((item.generated_at_utc or ""), item.bundle_id), reverse=True)

    return NrcApsWorkbenchCompareSourcesOut(
        default_baseline_run_id=baseline_runs[0].run_id if len(baseline_runs) == 1 else None,
        default_candidate_a_run_id=candidate_a_runs[0].run_id if len(candidate_a_runs) == 1 else None,
        default_candidate_b_bundle_id=candidate_b_bundles[0].bundle_id if len(candidate_b_bundles) == 1 else None,
        baseline_runs=baseline_runs,
        candidate_a_runs=candidate_a_runs,
        candidate_b_bundles=candidate_b_bundles,
    )


def _require_binding(run_id: str, *, expected_variant: str) -> ReviewRuntimeBinding:
    selector_item = _selector_by_run_id().get(run_id)
    if selector_item is None or not selector_item.reviewable:
        raise ValueError(f"invalid_{expected_variant}_run")
    for binding in discover_runtime_bindings():
        if binding.run_id != run_id:
            continue
        actual_variant = classify_runtime_binding_variant(binding)
        if actual_variant != expected_variant:
            raise ValueError(f"invalid_{expected_variant}_run")
        return binding
    raise ValueError(f"{expected_variant}_run_not_found")


def _load_runtime_targets(binding: ReviewRuntimeBinding, manifest_by_basename: dict[str, dict[str, Any] | None]) -> dict[str, _RuntimeCompareTarget]:
    with runtime_db_session_for_binding(binding) as session:
        rows = (
            session.query(ConnectorRunTarget, ApsContentLinkage)
            .outerjoin(
                ApsContentLinkage,
                and_(
                    ApsContentLinkage.run_id == ConnectorRunTarget.connector_run_id,
                    ApsContentLinkage.target_id == ConnectorRunTarget.connector_run_target_id,
                ),
            )
            .filter(ConnectorRunTarget.connector_run_id == binding.run_id)
            .order_by(ConnectorRunTarget.sciencebase_file_name.asc(), ConnectorRunTarget.connector_run_target_id.asc())
            .all()
        )

    targets: dict[str, _RuntimeCompareTarget] = {}
    for target, linkage in rows:
        if linkage is None:
            continue
        source_file_name = str(target.sciencebase_file_name or "").strip()
        basename = Path(source_file_name).name.strip().lower()
        manifest_entry = manifest_by_basename.get(basename)
        if manifest_entry is None:
            continue
        fixture_id = str(manifest_entry.get("fixture_id") or "").strip()
        if not fixture_id or fixture_id in targets:
            continue
        targets[fixture_id] = _RuntimeCompareTarget(
            fixture_id=fixture_id,
            run_id=binding.run_id,
            target_id=target.connector_run_target_id,
            content_id=linkage.content_id,
            accession_number=linkage.accession_number,
            source_file_name=source_file_name or None,
            document_title=_resolve_document_title(target),
            document_type=_resolve_document_type(target),
        )
    return targets


def _compare_targets_context(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    checkout_root: Path | None = None,
) -> tuple[ReviewRuntimeBinding, ReviewRuntimeBinding, _BundleArtifacts, dict[str, _RuntimeCompareTarget], dict[str, _RuntimeCompareTarget], dict[str, dict[str, Any]]]:
    root = (checkout_root or _checkout_root()).resolve()
    manifest_by_basename = _manifest_entries_by_basename(root)
    baseline_binding = _require_binding(baseline_run_id, expected_variant="baseline")
    candidate_a_binding = _require_binding(candidate_a_run_id, expected_variant="candidate_a_page_evidence_v1")
    bundle = _load_bundle_artifacts(candidate_b_bundle_id, root)
    bundle_docs = _bundle_documents_by_fixture(bundle.compare)
    baseline_targets = _load_runtime_targets(baseline_binding, manifest_by_basename)
    candidate_a_targets = _load_runtime_targets(candidate_a_binding, manifest_by_basename)
    return baseline_binding, candidate_a_binding, bundle, baseline_targets, candidate_a_targets, bundle_docs


def compose_workbench_compare_targets(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    checkout_root: Path | None = None,
) -> NrcApsWorkbenchCompareTargetsOut:
    _, _, _, baseline_targets, candidate_a_targets, bundle_docs = _compare_targets_context(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        checkout_root=checkout_root,
    )

    shared_fixture_ids = sorted(set(baseline_targets) & set(candidate_a_targets) & set(bundle_docs))
    targets: list[NrcApsWorkbenchCompareTargetItemOut] = []
    for fixture_id in shared_fixture_ids:
        baseline_target = baseline_targets[fixture_id]
        candidate_a_target = candidate_a_targets[fixture_id]
        display_label = baseline_target.document_title or baseline_target.source_file_name or fixture_id
        targets.append(
            NrcApsWorkbenchCompareTargetItemOut(
                fixture_id=fixture_id,
                display_label=display_label,
                source_file_name=baseline_target.source_file_name,
                baseline_target_id=baseline_target.target_id,
                candidate_a_target_id=candidate_a_target.target_id,
                candidate_b_available=True,
                comparability_state="aligned",
            )
        )

    return NrcApsWorkbenchCompareTargetsOut(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        default_fixture_id=targets[0].fixture_id if len(targets) == 1 else None,
        targets=targets,
    )


def _resolve_selected_target(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> tuple[ReviewRuntimeBinding, ReviewRuntimeBinding, _BundleArtifacts, _RuntimeCompareTarget, _RuntimeCompareTarget, dict[str, Any]]:
    baseline_binding, candidate_a_binding, bundle, baseline_targets, candidate_a_targets, bundle_docs = _compare_targets_context(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        checkout_root=checkout_root,
    )
    if fixture_id not in baseline_targets or fixture_id not in candidate_a_targets or fixture_id not in bundle_docs:
        raise ValueError("fixture_id_not_comparable")
    return (
        baseline_binding,
        candidate_a_binding,
        bundle,
        baseline_targets[fixture_id],
        candidate_a_targets[fixture_id],
        bundle_docs[fixture_id],
    )


def _trace_link(run_id: str, target_id: str, *, tab: str | None = None) -> str:
    params = {"run_id": run_id, "target_id": target_id}
    if tab:
        params["tab"] = tab
    return f"/review/nrc-aps/document-trace?{urlencode(params)}"


def _summary_badges(bundle: _BundleArtifacts, compare_doc: dict[str, Any]) -> list[NrcApsWorkbenchCompareBadgeOut]:
    interference_ok = bool(bundle.compare.get("interference_check_passed"))
    decision = str(bundle.compare.get("decision_recommendation") or "unknown").strip() or "unknown"
    limitation_count = len(compare_doc.get("expected_non_equivalences") or []) + len((compare_doc.get("candidate_b") or {}).get("limitation_flags") or [])
    return [
        NrcApsWorkbenchCompareBadgeOut(
            key="candidate_b_decision",
            label="Candidate B",
            value=decision,
            severity="warning" if "limitation" in decision else "info",
        ),
        NrcApsWorkbenchCompareBadgeOut(
            key="interference_check",
            label="Interference",
            value="passed" if interference_ok else "failed",
            severity="success" if interference_ok else "danger",
        ),
        NrcApsWorkbenchCompareBadgeOut(
            key="candidate_b_scope",
            label="Bundle posture",
            value="local operator evidence",
            severity="info",
        ),
        NrcApsWorkbenchCompareBadgeOut(
            key="candidate_b_limitations",
            label="Limitations",
            value=str(limitation_count),
            severity="warning" if limitation_count else "success",
        ),
    ]


def _proof_warning_matches_fixture(raw_warning: Any, fixture_id: str) -> bool:
    if isinstance(raw_warning, list):
        if not raw_warning:
            return False
        saw_fixture_scope = False
        for item in raw_warning:
            if isinstance(item, str):
                value = item.strip()
                if not value:
                    continue
                saw_fixture_scope = True
                if value == fixture_id:
                    return True
            elif isinstance(item, dict):
                fixture_value = str(item.get("fixture_id") or "").strip()
                if fixture_value:
                    saw_fixture_scope = True
                    if fixture_value == fixture_id:
                        return True
                fixture_ids = item.get("fixture_ids")
                if isinstance(fixture_ids, list):
                    normalized = [str(value).strip() for value in fixture_ids if str(value).strip()]
                    if normalized:
                        saw_fixture_scope = True
                        if fixture_id in normalized:
                            return True
        return not saw_fixture_scope
    if isinstance(raw_warning, dict):
        status = str(raw_warning.get("status") or "").strip().lower()
        if status in {"matched", "ok", "passed", "none"}:
            return False
        return bool(raw_warning)
    if isinstance(raw_warning, str):
        return bool(raw_warning.strip())
    return bool(raw_warning)


def _candidate_b_manifest_warnings(bundle: _BundleArtifacts, compare_doc: dict[str, Any], fixture_id: str) -> list[str]:
    candidate_b_data = compare_doc.get("candidate_b") or {}
    warnings: set[str] = {
        str(item).strip()
        for item in (candidate_b_data.get("warning_flags") or [])
        if str(item).strip()
    }
    proof_warnings = bundle.proof.get("warnings")
    if isinstance(proof_warnings, list):
        warnings.update(str(item).strip() for item in proof_warnings if str(item).strip())
    elif isinstance(proof_warnings, dict):
        for key, raw_warning in proof_warnings.items():
            label = str(key).strip()
            if label and _proof_warning_matches_fixture(raw_warning, fixture_id):
                warnings.add(label)
    return sorted(warnings)


def compose_workbench_compare_manifest(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> NrcApsWorkbenchCompareManifestOut:
    baseline_binding, candidate_a_binding, bundle, baseline_target, candidate_a_target, compare_doc = _resolve_selected_target(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )

    with runtime_db_session_for_binding(baseline_binding) as baseline_session:
        baseline_manifest = compose_trace_manifest(
            baseline_session,
            baseline_binding.run_id,
            baseline_target.target_id,
            baseline_binding.review_root,
        )
    with runtime_db_session_for_binding(candidate_a_binding) as candidate_a_session:
        candidate_a_manifest = compose_trace_manifest(
            candidate_a_session,
            candidate_a_binding.run_id,
            candidate_a_target.target_id,
            candidate_a_binding.review_root,
        )

    candidate_b_data = compare_doc.get("candidate_b") or {}
    warnings = _candidate_b_manifest_warnings(bundle, compare_doc, fixture_id)
    limitations = sorted(
        set(
            (candidate_b_data.get("limitation_flags") or [])
            + (compare_doc.get("expected_non_equivalences") or [])
            + (bundle.compare.get("non_equivalent_repo_fields") or [])
        )
    )

    tabs = [
        NrcApsWorkbenchCompareTabDefOut(tab_id=tab_id, label=label, available=True)
        for tab_id, label in _TAB_LABELS.items()
    ]

    return NrcApsWorkbenchCompareManifestOut(
        fixture_id=fixture_id,
        source_identity=NrcApsWorkbenchCompareSourceIdentityOut(
            fixture_id=fixture_id,
            document_title=baseline_manifest.identity.document_title or baseline_target.document_title,
            document_type=baseline_manifest.identity.document_type or baseline_target.document_type,
            source_file_name=baseline_manifest.identity.source_file_name or baseline_target.source_file_name,
            accession_number=baseline_manifest.identity.accession_number or baseline_target.accession_number,
            document_ref=str(compare_doc.get("document_ref") or "").strip() or None,
            document_sha256=str(compare_doc.get("document_sha256") or "").strip() or None,
        ),
        variant_bindings=NrcApsWorkbenchCompareVariantBindingsOut(
            baseline=NrcApsWorkbenchCompareRunBindingOut(
                run_id=baseline_binding.run_id,
                target_id=baseline_target.target_id,
                content_id=baseline_target.content_id,
            ),
            candidate_a=NrcApsWorkbenchCompareRunBindingOut(
                run_id=candidate_a_binding.run_id,
                target_id=candidate_a_target.target_id,
                content_id=candidate_a_target.content_id,
            ),
            candidate_b=NrcApsWorkbenchCompareBundleBindingOut(
                bundle_id=bundle.bundle_id,
                candidate_b_run_id=str(bundle.compare.get("run_id") or "").strip() or None,
            ),
        ),
        summary_badges=_summary_badges(bundle, compare_doc),
        tabs=tabs,
        warnings=warnings,
        limitations=limitations,
        deep_links=NrcApsWorkbenchCompareDeepLinksOut(
            baseline_trace=_trace_link(baseline_binding.run_id, baseline_target.target_id),
            candidate_a_trace=_trace_link(candidate_a_binding.run_id, candidate_a_target.target_id),
        ),
    )


def _missing_column(variant_id: str, label: str, message: str, *, deep_link: str | None = None) -> NrcApsWorkbenchCompareColumnOut:
    return NrcApsWorkbenchCompareColumnOut(
        variant_id=variant_id,
        available=False,
        comparability_class="missing",
        label=label,
        warnings=[message],
        deep_link=deep_link,
    )


def _structure_data_from_extracted(payload: Any, diagnostics_payload: Any) -> dict[str, Any]:
    page_numbers = sorted(
        {
            int(unit.page_number)
            for unit in getattr(payload, "units", [])
            if getattr(unit, "page_number", None) is not None
        }
        | {
            int(item.page_number)
            for item in getattr(payload, "visual_artifacts", [])
            if getattr(item, "page_number", None) is not None
        }
    )
    return {
        "total_unit_count": int(getattr(payload, "total_unit_count", 0) or 0),
        "visual_artifact_count": len(getattr(payload, "visual_artifacts", [])),
        "unit_kind_counts": dict(getattr(diagnostics_payload, "unit_kind_counts", {}) or {}),
        "visual_derivative_unit_count": int(getattr(diagnostics_payload, "visual_derivative_unit_count", 0) or 0),
        "page_numbers": page_numbers,
    }


def _candidate_b_summary_data(bundle: _BundleArtifacts, compare_doc: dict[str, Any]) -> dict[str, Any]:
    candidate_b = compare_doc.get("candidate_b") or {}
    return {
        "page_count": candidate_b.get("odl_page_count"),
        "normalized_char_count": candidate_b.get("candidate_b_normalized_char_count"),
        "struct_tree_state": candidate_b.get("struct_tree_state"),
        "decision_recommendation": bundle.compare.get("decision_recommendation"),
        "limitation_flags": list(candidate_b.get("limitation_flags") or []),
        "warning_flags": list(candidate_b.get("warning_flags") or []),
    }


def _candidate_b_diagnostics_data(bundle: _BundleArtifacts, compare_doc: dict[str, Any]) -> dict[str, Any]:
    candidate_b = compare_doc.get("candidate_b") or {}
    return {
        "limitation_flags": list(candidate_b.get("limitation_flags") or []),
        "warning_flags": list(candidate_b.get("warning_flags") or []),
        "expected_non_equivalences": list(compare_doc.get("expected_non_equivalences") or []),
        "expected_gain_claims": list(compare_doc.get("expected_gain_claims") or []),
        "derived_comparison_only": list(bundle.compare.get("derived_comparison_only") or []),
        "non_equivalent_repo_fields": list(bundle.compare.get("non_equivalent_repo_fields") or []),
        "decision_recommendation": bundle.compare.get("decision_recommendation"),
    }


def _candidate_b_structure_data(compare_doc: dict[str, Any]) -> dict[str, Any]:
    candidate_b = compare_doc.get("candidate_b") or {}
    page_summaries = candidate_b.get("page_summaries")
    return {
        "element_counts_by_type": dict(candidate_b.get("element_counts_by_type") or {}),
        "heading_count": candidate_b.get("heading_count"),
        "list_count": candidate_b.get("list_count"),
        "image_count": candidate_b.get("image_count"),
        "table_count": candidate_b.get("table_count"),
        "hidden_text_present": candidate_b.get("hidden_text_present"),
        "hidden_text_node_count": candidate_b.get("hidden_text_node_count"),
        "footer_page_numbers": list(candidate_b.get("footer_page_numbers") or []),
        "image_sources": list(candidate_b.get("image_sources") or []),
        "page_summaries": page_summaries if isinstance(page_summaries, list) else [],
    }


def compose_workbench_compare_tab(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    fixture_id: str,
    tab_id: str,
    checkout_root: Path | None = None,
) -> NrcApsWorkbenchCompareTabOut:
    if tab_id not in _TAB_LABELS:
        raise ValueError("unsupported_tab")

    baseline_binding, candidate_a_binding, bundle, baseline_target, candidate_a_target, compare_doc = _resolve_selected_target(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )

    baseline_link = _trace_link(baseline_binding.run_id, baseline_target.target_id, tab=tab_id)
    candidate_a_link = _trace_link(candidate_a_binding.run_id, candidate_a_target.target_id, tab=tab_id)

    with runtime_db_session_for_binding(baseline_binding) as baseline_session:
        baseline_manifest = compose_trace_manifest(
            baseline_session,
            baseline_binding.run_id,
            baseline_target.target_id,
            baseline_binding.review_root,
        )
        baseline_diagnostics = compose_diagnostics_payload(
            baseline_session,
            baseline_binding.run_id,
            baseline_target.target_id,
            baseline_binding.review_root,
        )
        baseline_normalized = compose_normalized_text_payload(
            baseline_session,
            baseline_binding.run_id,
            baseline_target.target_id,
            baseline_binding.review_root,
        )
        baseline_structure = compose_extracted_units_payload(
            baseline_session,
            baseline_binding.run_id,
            baseline_target.target_id,
            baseline_binding.review_root,
            storage_root=baseline_binding.storage_dir,
        )

    with runtime_db_session_for_binding(candidate_a_binding) as candidate_a_session:
        candidate_a_manifest = compose_trace_manifest(
            candidate_a_session,
            candidate_a_binding.run_id,
            candidate_a_target.target_id,
            candidate_a_binding.review_root,
        )
        candidate_a_diagnostics = compose_diagnostics_payload(
            candidate_a_session,
            candidate_a_binding.run_id,
            candidate_a_target.target_id,
            candidate_a_binding.review_root,
        )
        candidate_a_normalized = compose_normalized_text_payload(
            candidate_a_session,
            candidate_a_binding.run_id,
            candidate_a_target.target_id,
            candidate_a_binding.review_root,
        )
        candidate_a_structure = compose_extracted_units_payload(
            candidate_a_session,
            candidate_a_binding.run_id,
            candidate_a_target.target_id,
            candidate_a_binding.review_root,
            storage_root=candidate_a_binding.storage_dir,
        )

    columns: dict[str, NrcApsWorkbenchCompareColumnOut] = {}

    if tab_id == "summary":
        columns["baseline"] = NrcApsWorkbenchCompareColumnOut(
            variant_id="baseline",
            available=True,
            comparability_class="direct",
            label="Baseline",
            data={
                "page_count": baseline_manifest.summary.page_count,
                "normalized_char_count": baseline_normalized.char_count if baseline_normalized.available else 0,
                "document_class": baseline_manifest.summary.document_class,
                "quality_status": baseline_manifest.summary.quality_status,
                "degradation_codes": list(baseline_diagnostics.degradation_codes or []),
                "ordered_unit_count": baseline_manifest.summary.ordered_unit_count,
                "indexed_chunk_count": baseline_manifest.summary.indexed_chunk_count,
                "visual_derivative_unit_count": baseline_manifest.summary.visual_derivative_unit_count,
            },
            deep_link=baseline_link,
        )
        columns["candidate_a"] = NrcApsWorkbenchCompareColumnOut(
            variant_id="candidate_a",
            available=True,
            comparability_class="direct",
            label="Candidate A",
            data={
                "page_count": candidate_a_manifest.summary.page_count,
                "normalized_char_count": candidate_a_normalized.char_count if candidate_a_normalized.available else 0,
                "document_class": candidate_a_manifest.summary.document_class,
                "quality_status": candidate_a_manifest.summary.quality_status,
                "degradation_codes": list(candidate_a_diagnostics.degradation_codes or []),
                "ordered_unit_count": candidate_a_manifest.summary.ordered_unit_count,
                "indexed_chunk_count": candidate_a_manifest.summary.indexed_chunk_count,
                "visual_derivative_unit_count": candidate_a_manifest.summary.visual_derivative_unit_count,
            },
            deep_link=candidate_a_link,
        )
        columns["candidate_b"] = NrcApsWorkbenchCompareColumnOut(
            variant_id="candidate_b",
            available=True,
            comparability_class="direct",
            label="Candidate B",
            data=_candidate_b_summary_data(bundle, compare_doc),
            warnings=list((compare_doc.get("candidate_b") or {}).get("warning_flags") or []),
            limitations=list((compare_doc.get("candidate_b") or {}).get("limitation_flags") or []),
        )
    elif tab_id == "normalized_text":
        columns["baseline"] = (
            NrcApsWorkbenchCompareColumnOut(
                variant_id="baseline",
                available=True,
                comparability_class="direct",
                label="Baseline",
                data={
                    "char_count": baseline_normalized.char_count,
                    "mapping_precision": baseline_normalized.mapping_precision,
                    "text": baseline_normalized.text or "",
                },
                deep_link=baseline_link,
            )
            if baseline_normalized.available
            else _missing_column("baseline", "Baseline", "Normalized text is unavailable for the selected baseline target.", deep_link=baseline_link)
        )
        columns["candidate_a"] = (
            NrcApsWorkbenchCompareColumnOut(
                variant_id="candidate_a",
                available=True,
                comparability_class="direct",
                label="Candidate A",
                data={
                    "char_count": candidate_a_normalized.char_count,
                    "mapping_precision": candidate_a_normalized.mapping_precision,
                    "text": candidate_a_normalized.text or "",
                },
                deep_link=candidate_a_link,
            )
            if candidate_a_normalized.available
            else _missing_column("candidate_a", "Candidate A", "Normalized text is unavailable for the selected Candidate A target.", deep_link=candidate_a_link)
        )
        columns["candidate_b"] = NrcApsWorkbenchCompareColumnOut(
            variant_id="candidate_b",
            available=True,
            comparability_class="derived_only",
            label="Candidate B",
            data={
                "char_count": (compare_doc.get("candidate_b") or {}).get("candidate_b_normalized_char_count"),
                "mapping_precision": "document",
                "text": (compare_doc.get("candidate_b") or {}).get("candidate_b_normalized_text") or "",
            },
            warnings=["Candidate B normalized text is workbench-only and not a replacement for owner-path normalized text."],
            limitations=list((compare_doc.get("candidate_b") or {}).get("limitation_flags") or []),
        )
    elif tab_id == "diagnostics":
        columns["baseline"] = (
            NrcApsWorkbenchCompareColumnOut(
                variant_id="baseline",
                available=True,
                comparability_class="direct",
                label="Baseline",
                data={
                    "quality_status": baseline_diagnostics.quality_status,
                    "document_class": baseline_diagnostics.document_class,
                    "page_count": baseline_diagnostics.page_count,
                    "ordered_unit_count": baseline_diagnostics.ordered_unit_count,
                    "unit_kind_counts": dict(baseline_diagnostics.unit_kind_counts or {}),
                    "degradation_codes": list(baseline_diagnostics.degradation_codes or []),
                },
                warnings=list(baseline_diagnostics.warnings or []),
                deep_link=baseline_link,
            )
            if baseline_diagnostics.available
            else _missing_column("baseline", "Baseline", "Diagnostics are unavailable for the selected baseline target.", deep_link=baseline_link)
        )
        columns["candidate_a"] = (
            NrcApsWorkbenchCompareColumnOut(
                variant_id="candidate_a",
                available=True,
                comparability_class="direct",
                label="Candidate A",
                data={
                    "quality_status": candidate_a_diagnostics.quality_status,
                    "document_class": candidate_a_diagnostics.document_class,
                    "page_count": candidate_a_diagnostics.page_count,
                    "ordered_unit_count": candidate_a_diagnostics.ordered_unit_count,
                    "unit_kind_counts": dict(candidate_a_diagnostics.unit_kind_counts or {}),
                    "degradation_codes": list(candidate_a_diagnostics.degradation_codes or []),
                },
                warnings=list(candidate_a_diagnostics.warnings or []),
                deep_link=candidate_a_link,
            )
            if candidate_a_diagnostics.available
            else _missing_column("candidate_a", "Candidate A", "Diagnostics are unavailable for the selected Candidate A target.", deep_link=candidate_a_link)
        )
        columns["candidate_b"] = NrcApsWorkbenchCompareColumnOut(
            variant_id="candidate_b",
            available=True,
            comparability_class="non_equivalent",
            label="Candidate B",
            data=_candidate_b_diagnostics_data(bundle, compare_doc),
            warnings=list((compare_doc.get("candidate_b") or {}).get("warning_flags") or []),
            limitations=list((compare_doc.get("candidate_b") or {}).get("limitation_flags") or []),
        )
    else:
        columns["baseline"] = (
            NrcApsWorkbenchCompareColumnOut(
                variant_id="baseline",
                available=True,
                comparability_class="direct",
                label="Baseline",
                data=_structure_data_from_extracted(baseline_structure, baseline_diagnostics),
                deep_link=baseline_link,
            )
            if baseline_structure.available
            else _missing_column("baseline", "Baseline", "Structure data are unavailable for the selected baseline target.", deep_link=baseline_link)
        )
        columns["candidate_a"] = (
            NrcApsWorkbenchCompareColumnOut(
                variant_id="candidate_a",
                available=True,
                comparability_class="direct",
                label="Candidate A",
                data=_structure_data_from_extracted(candidate_a_structure, candidate_a_diagnostics),
                deep_link=candidate_a_link,
            )
            if candidate_a_structure.available
            else _missing_column("candidate_a", "Candidate A", "Structure data are unavailable for the selected Candidate A target.", deep_link=candidate_a_link)
        )
        columns["candidate_b"] = NrcApsWorkbenchCompareColumnOut(
            variant_id="candidate_b",
            available=True,
            comparability_class="derived_only",
            label="Candidate B",
            data=_candidate_b_structure_data(compare_doc),
            warnings=list((compare_doc.get("candidate_b") or {}).get("warning_flags") or []),
            limitations=list((compare_doc.get("candidate_b") or {}).get("limitation_flags") or []),
        )

    warnings = sorted(
        set(
            columns["baseline"].warnings
            + columns["candidate_a"].warnings
            + columns["candidate_b"].warnings
        )
    )
    limitations = sorted(
        set(
            columns["baseline"].limitations
            + columns["candidate_a"].limitations
            + columns["candidate_b"].limitations
        )
    )

    return NrcApsWorkbenchCompareTabOut(
        fixture_id=fixture_id,
        tab_id=tab_id,
        columns=columns,
        comparability_legend=dict(_COMPARABILITY_LEGEND),
        warnings=warnings,
        limitations=limitations,
    )
