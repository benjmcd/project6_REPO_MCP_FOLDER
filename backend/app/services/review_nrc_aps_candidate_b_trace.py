from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlencode

from app.schemas.review_nrc_aps import (
    NrcApsCandidateBTraceArtifactEndpointsOut,
    NrcApsCandidateBTraceIdentityOut,
    NrcApsCandidateBTraceManifestOut,
    NrcApsCandidateBTraceSummaryOut,
    NrcApsCandidateBTraceTabDefOut,
)
from app.services.review_nrc_aps_workbench_compare import resolve_candidate_b_bundle_root


_TAB_LABELS: dict[str, str] = {
    "annotated_pdf": "Annotated PDF",
    "summary": "Summary",
    "raw_json": "Raw JSON",
    "raw_markdown": "Raw Markdown",
}


@dataclass(frozen=True)
class _CandidateBTraceContext:
    checkout_root: Path
    bundle_id: str
    bundle_root: Path
    raw_root: Path
    compare: dict[str, Any]
    proof: dict[str, Any]
    retain: dict[str, Any]
    compare_doc: dict[str, Any]
    fixture_id: str
    retained_raw_paths: set[str]


def _checkout_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_bundle_id(bundle_root: Path, checkout_root: Path) -> str:
    return bundle_root.resolve().relative_to(checkout_root.resolve()).as_posix()


def _parse_repo_relative_ref(
    value: str | None,
    *,
    missing_code: str,
    invalid_code: str,
) -> PurePosixPath:
    normalized = str(value or "").strip().replace("\\", "/")
    if not normalized:
        raise ValueError(missing_code)
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(invalid_code)
    return pure


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


def _resolve_raw_root(compare_payload: dict[str, Any], *, bundle_root: Path, checkout_root: Path) -> Path:
    raw_root_rel = _parse_repo_relative_ref(
        str(compare_payload.get("raw_output_root") or ""),
        missing_code="candidate_b_raw_root_missing",
        invalid_code="candidate_b_raw_root_invalid",
    )
    raw_root = (checkout_root / Path(*raw_root_rel.parts)).resolve()
    try:
        relative = raw_root.relative_to(bundle_root.resolve())
    except ValueError as exc:
        raise ValueError("candidate_b_raw_root_invalid") from exc
    if not relative.parts or relative.parts[0] != "raw":
        raise ValueError("candidate_b_raw_root_invalid")
    return raw_root


def _retained_raw_paths(retain_payload: dict[str, Any]) -> set[str]:
    inventory = retain_payload.get("raw_file_inventory")
    if not isinstance(inventory, list):
        return set()
    out: set[str] = set()
    for entry in inventory:
        if not isinstance(entry, dict):
            continue
        path_value = str(entry.get("path") or "").strip().replace("\\", "/")
        if path_value:
            out.add(path_value)
    return out


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


def _candidate_b_trace_warnings(proof_payload: dict[str, Any], compare_doc: dict[str, Any], fixture_id: str) -> list[str]:
    candidate_b_data = compare_doc.get("candidate_b") or {}
    warnings: set[str] = {
        str(item).strip()
        for item in (candidate_b_data.get("warning_flags") or [])
        if str(item).strip()
    }
    proof_warnings = proof_payload.get("warnings")
    if isinstance(proof_warnings, list):
        warnings.update(str(item).strip() for item in proof_warnings if str(item).strip())
    elif isinstance(proof_warnings, dict):
        for key, raw_warning in proof_warnings.items():
            label = str(key).strip()
            if label and _proof_warning_matches_fixture(raw_warning, fixture_id):
                warnings.add(label)
    return sorted(warnings)


def _candidate_b_trace_limitations(compare_payload: dict[str, Any], compare_doc: dict[str, Any]) -> list[str]:
    candidate_b_data = compare_doc.get("candidate_b") or {}
    return sorted(
        set(
            list(candidate_b_data.get("limitation_flags") or [])
            + list(compare_doc.get("expected_non_equivalences") or [])
            + list(compare_payload.get("non_equivalent_repo_fields") or [])
        )
    )


def _candidate_b_trace_link(candidate_b_bundle_id: str, fixture_id: str, *, tab: str | None = None) -> str:
    params = {
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "fixture_id": fixture_id,
    }
    if tab:
        params["tab"] = tab
    return f"/review/nrc-aps/candidate-b-trace?{urlencode(params)}"


def _api_link(candidate_b_bundle_id: str, fixture_id: str, route_suffix: str) -> str:
    params = urlencode(
        {
            "candidate_b_bundle_id": candidate_b_bundle_id,
            "fixture_id": fixture_id,
        }
    )
    return f"/api/v1/review/nrc-aps/candidate-b-trace/{route_suffix}?{params}"


def _resolve_validated_artifact_path(
    context: _CandidateBTraceContext,
    ref_value: str | None,
    *,
    error_code: str,
    allow_missing: bool = False,
) -> Path | None:
    if not str(ref_value or "").strip():
        return None if allow_missing else (_ for _ in ()).throw(FileNotFoundError(error_code))
    pure = _parse_repo_relative_ref(
        ref_value,
        missing_code=error_code,
        invalid_code=error_code,
    )
    resolved = (context.checkout_root / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(context.raw_root.resolve())
    except ValueError as exc:
        raise ValueError(error_code) from exc
    normalized = resolved.relative_to(context.checkout_root.resolve()).as_posix()
    if normalized not in context.retained_raw_paths:
        raise ValueError(error_code)
    if not resolved.is_file():
        if allow_missing:
            return None
        raise FileNotFoundError(error_code)
    return resolved


def _artifact_available(context: _CandidateBTraceContext, ref_value: str | None, *, error_code: str) -> bool:
    return _resolve_validated_artifact_path(
        context,
        ref_value,
        error_code=error_code,
        allow_missing=True,
    ) is not None


def _resolve_trace_context(
    *,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> _CandidateBTraceContext:
    root = (checkout_root or _checkout_root()).resolve()
    bundle_root = resolve_candidate_b_bundle_root(candidate_b_bundle_id, root)
    compare_payload = _read_json(bundle_root / "compare.json")
    if not isinstance(compare_payload, dict):
        raise ValueError("candidate_b_compare_payload_invalid")
    proof_payload = _read_json(bundle_root / "proof.json")
    retain_payload = _read_json(bundle_root / "retain.json")
    if not isinstance(proof_payload, dict) or not isinstance(retain_payload, dict):
        raise ValueError("candidate_b_bundle_payload_invalid")
    documents_by_fixture = _bundle_documents_by_fixture(compare_payload)
    if fixture_id not in documents_by_fixture:
        raise ValueError("candidate_b_fixture_unavailable")
    return _CandidateBTraceContext(
        checkout_root=root,
        bundle_id=_canonical_bundle_id(bundle_root, root),
        bundle_root=bundle_root,
        raw_root=_resolve_raw_root(compare_payload, bundle_root=bundle_root, checkout_root=root),
        compare=compare_payload,
        proof=proof_payload,
        retain=retain_payload,
        compare_doc=documents_by_fixture[fixture_id],
        fixture_id=fixture_id,
        retained_raw_paths=_retained_raw_paths(retain_payload),
    )


def compose_candidate_b_trace_manifest(
    *,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> NrcApsCandidateBTraceManifestOut:
    context = _resolve_trace_context(
        candidate_b_bundle_id=candidate_b_bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )
    candidate_b = context.compare_doc.get("candidate_b") or {}
    annotated_available = (
        str(candidate_b.get("annotated_pdf_status") or "").strip() == "present"
        and _artifact_available(
            context,
            candidate_b.get("annotated_pdf_ref"),
            error_code="candidate_b_annotated_pdf_invalid",
        )
    )
    raw_json_available = _artifact_available(
        context,
        candidate_b.get("raw_json_ref"),
        error_code="candidate_b_raw_json_invalid",
    )
    raw_markdown_available = _artifact_available(
        context,
        candidate_b.get("raw_markdown_ref"),
        error_code="candidate_b_raw_markdown_invalid",
    )
    default_tab = "annotated_pdf" if annotated_available else "summary"
    tabs = [
        NrcApsCandidateBTraceTabDefOut(tab_id="annotated_pdf", label=_TAB_LABELS["annotated_pdf"], available=annotated_available),
        NrcApsCandidateBTraceTabDefOut(tab_id="summary", label=_TAB_LABELS["summary"], available=True),
        NrcApsCandidateBTraceTabDefOut(tab_id="raw_json", label=_TAB_LABELS["raw_json"], available=raw_json_available),
        NrcApsCandidateBTraceTabDefOut(tab_id="raw_markdown", label=_TAB_LABELS["raw_markdown"], available=raw_markdown_available),
    ]
    return NrcApsCandidateBTraceManifestOut(
        candidate_b_bundle_id=context.bundle_id,
        fixture_id=fixture_id,
        identity=NrcApsCandidateBTraceIdentityOut(
            fixture_id=fixture_id,
            bundle_id=context.bundle_id,
            candidate_b_run_id=str(context.compare.get("run_id") or "").strip() or None,
            document_title=str(candidate_b.get("file_name") or context.compare_doc.get("document_ref") or "").strip() or None,
            source_file_name=str(candidate_b.get("file_name") or "").strip() or None,
            document_ref=str(context.compare_doc.get("document_ref") or "").strip() or None,
            document_sha256=str(context.compare_doc.get("document_sha256") or "").strip() or None,
        ),
        summary=NrcApsCandidateBTraceSummaryOut(
            processing_status=str(candidate_b.get("processing_status") or "").strip() or None,
            decision_recommendation=str(context.compare.get("decision_recommendation") or "").strip() or None,
            page_count=int(candidate_b.get("odl_page_count")) if candidate_b.get("odl_page_count") is not None else None,
            normalized_char_count=int(candidate_b.get("candidate_b_normalized_char_count")) if candidate_b.get("candidate_b_normalized_char_count") is not None else None,
            struct_tree_state=str(candidate_b.get("struct_tree_state") or "").strip() or None,
            heading_count=int(candidate_b.get("heading_count")) if candidate_b.get("heading_count") is not None else None,
            list_count=int(candidate_b.get("list_count")) if candidate_b.get("list_count") is not None else None,
            image_count=int(candidate_b.get("image_count")) if candidate_b.get("image_count") is not None else None,
            table_count=int(candidate_b.get("table_count")) if candidate_b.get("table_count") is not None else None,
            hidden_text_present=bool(candidate_b.get("hidden_text_present")) if candidate_b.get("hidden_text_present") is not None else None,
            footer_page_numbers=[int(value) for value in (candidate_b.get("footer_page_numbers") or [])],
            image_sources=[str(value) for value in (candidate_b.get("image_sources") or []) if str(value)],
            annotated_pdf_status=str(candidate_b.get("annotated_pdf_status") or "").strip() or None,
            expected_gain_claims=[str(value) for value in (context.compare_doc.get("expected_gain_claims") or []) if str(value)],
            expected_non_equivalences=[str(value) for value in (context.compare_doc.get("expected_non_equivalences") or []) if str(value)],
            regime_labels=[str(value) for value in (context.compare_doc.get("regime_labels") or []) if str(value)],
            review_notes=str(context.compare_doc.get("review_notes") or "").strip() or None,
        ),
        tabs=tabs,
        default_tab=default_tab,
        warnings=_candidate_b_trace_warnings(context.proof, context.compare_doc, fixture_id),
        limitations=_candidate_b_trace_limitations(context.compare, context.compare_doc),
        artifacts=NrcApsCandidateBTraceArtifactEndpointsOut(
            annotated_pdf=_api_link(context.bundle_id, fixture_id, "annotated-pdf") if annotated_available else None,
            raw_json=_api_link(context.bundle_id, fixture_id, "raw-json") if raw_json_available else None,
            raw_markdown=_api_link(context.bundle_id, fixture_id, "raw-markdown") if raw_markdown_available else None,
        ),
    )


def candidate_b_trace_link(
    *,
    candidate_b_bundle_id: str,
    fixture_id: str,
    tab: str | None = None,
) -> str:
    return _candidate_b_trace_link(candidate_b_bundle_id, fixture_id, tab=tab)


def resolve_candidate_b_trace_annotated_pdf_info(
    *,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> tuple[Path, str, str]:
    context = _resolve_trace_context(
        candidate_b_bundle_id=candidate_b_bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )
    candidate_b = context.compare_doc.get("candidate_b") or {}
    if str(candidate_b.get("annotated_pdf_status") or "").strip() != "present":
        raise FileNotFoundError("annotated_pdf_unavailable")
    annotated_pdf_path = _resolve_validated_artifact_path(
        context,
        candidate_b.get("annotated_pdf_ref"),
        error_code="candidate_b_annotated_pdf_invalid",
        allow_missing=True,
    )
    if annotated_pdf_path is None:
        raise FileNotFoundError("annotated_pdf_unavailable")
    return annotated_pdf_path, "application/pdf", f"{fixture_id}.pdf"


def load_candidate_b_trace_raw_json(
    *,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> Any:
    context = _resolve_trace_context(
        candidate_b_bundle_id=candidate_b_bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )
    candidate_b = context.compare_doc.get("candidate_b") or {}
    raw_json_path = _resolve_validated_artifact_path(
        context,
        candidate_b.get("raw_json_ref"),
        error_code="candidate_b_raw_json_invalid",
    )
    return _read_json(raw_json_path)


def load_candidate_b_trace_raw_markdown(
    *,
    candidate_b_bundle_id: str,
    fixture_id: str,
    checkout_root: Path | None = None,
) -> str:
    context = _resolve_trace_context(
        candidate_b_bundle_id=candidate_b_bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )
    candidate_b = context.compare_doc.get("candidate_b") or {}
    raw_markdown_path = _resolve_validated_artifact_path(
        context,
        candidate_b.get("raw_markdown_ref"),
        error_code="candidate_b_raw_markdown_invalid",
    )
    return raw_markdown_path.read_text(encoding="utf-8")
