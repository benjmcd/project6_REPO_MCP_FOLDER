from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import nrc_aps_sync_drift
from app.services import review_nrc_aps_gate_reports
from app.services import review_nrc_aps_runtime
from app.services import nrc_aps_validate_only_gates_contract as contract


class ValidateOnlyGatesError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = str(code or contract.APS_RUNTIME_FAILURE_INTERNAL)
        self.message = str(message or "")
        self.status_code = int(status_code)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_for_error_code(code: str) -> int:
    if code == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST:
        return 422
    if code in {
        contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_NOT_FOUND,
        contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND,
    }:
        return 404
    if code == contract.APS_RUNTIME_FAILURE_CONNECTOR_RUN_NOT_FOUND:
        return 409
    if code in {
        contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID,
        contract.APS_RUNTIME_FAILURE_GATE_RESULTS_MISSING,
        contract.APS_RUNTIME_FAILURE_GATE_RESULTS_INVALID,
        contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISSING,
        contract.APS_RUNTIME_FAILURE_GATE_REPORTS_INVALID,
        contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH,
    }:
        return 422
    if code == contract.APS_RUNTIME_FAILURE_CONFLICT:
        return 409
    return 500


def _safe_scope_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return "".join(ch for ch in raw if ch.isalnum() or ch in {"_", "-", "."}) or "unknown"


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _summary_path(binding: review_nrc_aps_runtime.ReviewRuntimeBinding) -> Path:
    return (binding.review_root / "local_corpus_e2e_summary.json").resolve()


def validate_only_gates_artifact_path(*, owner_run_id: str, review_root: str | Path) -> Path:
    reports_dir = Path(review_root).resolve() / "gate_reports"
    validate_only_gates_id = contract.derive_validate_only_gates_id(owner_run_id=str(owner_run_id or ""))
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return reports_dir / contract.expected_validate_only_gates_file_name(
        scope=scope,
        validate_only_gates_id=validate_only_gates_id,
    )


def validate_only_gates_failure_path(*, owner_run_id: str, error_code: str, review_root: str | Path) -> Path:
    reports_dir = Path(review_root).resolve() / "gate_reports"
    failure_id = contract.derive_failure_validate_only_gates_id(
        owner_run_id=str(owner_run_id or ""),
        error_code=str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
    )
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return reports_dir / contract.expected_failure_file_name(
        scope=scope,
        validate_only_gates_id=failure_id,
    )


def _expected_gate_report_map(binding: review_nrc_aps_runtime.ReviewRuntimeBinding) -> dict[str, str]:
    report_root = (binding.review_root / "gate_reports").resolve()
    refs: dict[str, str] = {}
    for spec in review_nrc_aps_gate_reports.GATE_REPORT_SPECS:
        candidate = (report_root / spec.report_name).resolve()
        if not candidate.exists() or not candidate.is_file():
            raise ValidateOnlyGatesError(
                contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISSING,
                f"missing generic gate report: {candidate.name}",
                status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISSING),
            )
        refs[spec.gate_name] = str(candidate)
    return refs


def _normalize_gate_report_refs(binding: review_nrc_aps_runtime.ReviewRuntimeBinding) -> list[str]:
    return list(_expected_gate_report_map(binding).values())


def _normalized_gate_results_from_summary(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gate_results = dict(summary.get("gate_results") or {})
    if not gate_results:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_GATE_RESULTS_MISSING,
            "review runtime summary is missing gate_results",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_GATE_RESULTS_MISSING),
        )
    normalized = contract.normalize_gate_results(gate_results)
    if not normalized:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_GATE_RESULTS_INVALID,
            "review runtime summary gate_results are invalid",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_GATE_RESULTS_INVALID),
        )
    return normalized


def _require_consistent_generic_boundary(
    *,
    binding: review_nrc_aps_runtime.ReviewRuntimeBinding,
    normalized_gate_results: dict[str, dict[str, Any]],
) -> None:
    expected = _expected_gate_report_map(binding)
    actual = {
        gate_name: str(Path(str(payload.get("report_path") or "")).resolve())
        for gate_name, payload in normalized_gate_results.items()
        if str(payload.get("report_path") or "").strip()
    }
    if actual != expected:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH,
            f"summary gate_results report_path map does not match generic gate report refs for run {binding.run_id}",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH),
        )


def _load_binding_or_raise(*, run_id: str, review_root: str | Path | None) -> review_nrc_aps_runtime.ReviewRuntimeBinding:
    try:
        return review_nrc_aps_runtime.resolve_runtime_binding_for_run(run_id=run_id, review_root=review_root)
    except FileNotFoundError as exc:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_NOT_FOUND,
            str(exc),
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_NOT_FOUND),
        ) from exc
    except ValueError as exc:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID,
            str(exc),
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID),
        ) from exc


def _collect_runtime_inputs(binding: review_nrc_aps_runtime.ReviewRuntimeBinding) -> tuple[Path, dict[str, Any], list[str], dict[str, dict[str, Any]]]:
    summary_path = _summary_path(binding)
    summary = dict(binding.summary or {})
    if str(summary.get("schema_id") or "").strip() != review_nrc_aps_gate_reports.SUMMARY_SCHEMA_ID:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID,
            f"review runtime summary is not {review_nrc_aps_gate_reports.SUMMARY_SCHEMA_ID}: {binding.review_root}",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID),
        )
    if str(summary.get("run_id") or "").strip() != binding.run_id:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID,
            f"review runtime summary run_id mismatch for {binding.review_root}",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID),
        )
    gate_report_refs = _normalize_gate_report_refs(binding)
    normalized_gate_results = _normalized_gate_results_from_summary(summary)
    _require_consistent_generic_boundary(
        binding=binding,
        normalized_gate_results=normalized_gate_results,
    )
    return summary_path, summary, gate_report_refs, normalized_gate_results


def _candidate_runtime_artifacts(binding: review_nrc_aps_runtime.ReviewRuntimeBinding) -> list[Path]:
    scope = contract.safe_path_token(f"run_{_safe_scope_token(binding.run_id)}")
    pattern = f"{scope}_*_aps_validate_only_gates_v1.json"
    return sorted((binding.review_root / "gate_reports").glob(pattern), key=lambda path: path.name)


def _validate_persisted_validate_only_gates_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_VALIDATE_ONLY_GATES_SCHEMA_ID:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema version mismatch", status_code=500)
    for field_name, expected_value in contract.projection_identity_payload().items():
        if payload.get(field_name) != expected_value:
            raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} mismatch", status_code=500)
    owner_run_id = str(payload.get("owner_run_id") or "").strip()
    if not owner_run_id:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "owner_run_id missing", status_code=500)
    expected_id = contract.derive_validate_only_gates_id(owner_run_id=owner_run_id)
    if str(payload.get("validate_only_gates_id") or "").strip() != expected_id:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "validate_only_gates_id mismatch", status_code=500)
    source_runtime = dict(payload.get("source_review_runtime") or {})
    if str(source_runtime.get("run_id") or "").strip() != owner_run_id:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source runtime run_id mismatch", status_code=500)
    if not str(source_runtime.get("summary_ref") or "").strip():
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source summary ref missing", status_code=500)
    gate_results = contract.normalize_gate_results(dict(payload.get("gate_results") or {}))
    if gate_results != dict(payload.get("gate_results") or {}):
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "gate_results mismatch", status_code=500)
    gate_total = int(payload.get("gate_total") or 0)
    gate_passed = int(payload.get("gate_passed") or 0)
    gate_failed = int(payload.get("gate_failed") or 0)
    if gate_total != len(gate_results) or gate_failed != gate_total - gate_passed:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "gate counts mismatch", status_code=500)
    checksum = str(payload.get("validate_only_gates_checksum") or "").strip()
    if not checksum or checksum != contract.compute_validate_only_gates_checksum(payload):
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact checksum mismatch", status_code=500)
    return payload


def load_persisted_validate_only_gates_artifact(
    *,
    run_id: str,
    review_root: str | Path,
) -> tuple[dict[str, Any], Path]:
    binding = _load_binding_or_raise(run_id=run_id, review_root=review_root)
    candidate_paths = _candidate_runtime_artifacts(binding)
    if not candidate_paths:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND,
            "validate-only gates artifact not found",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND),
        )
    if len(candidate_paths) > 1:
        raise ValidateOnlyGatesError(
            contract.APS_RUNTIME_FAILURE_CONFLICT,
            "validate-only gates artifact id is ambiguous across persisted runtime artifacts",
            status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_CONFLICT),
        )
    candidate_path = candidate_paths[0]
    payload = _read_json(candidate_path)
    if not payload:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "validate-only gates artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_validate_only_gates_payload(payload)
    validated_payload["_validate_only_gates_ref"] = str(candidate_path.resolve())
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path.resolve()


def _artifact_registry_update(database_path: Path, *, run_id: str, artifact_ref: str | None = None, failure_ref: str | None = None, summary_entry: dict[str, Any] | None = None) -> None:
    database_uri = f"file:{database_path.resolve().as_posix()}?mode=rw"
    try:
        connection = sqlite3.connect(database_uri, uri=True, check_same_thread=False)
    except sqlite3.DatabaseError as exc:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, str(exc), status_code=500) from exc
    try:
        row = connection.execute(
            """
            SELECT query_plan_json
            FROM connector_run
            WHERE connector_run_id = ?
              AND connector_key = ?
            LIMIT 1
            """,
            (run_id, "nrc_adams_aps"),
        ).fetchone()
        if row is None:
            raise ValidateOnlyGatesError(
                contract.APS_RUNTIME_FAILURE_CONNECTOR_RUN_NOT_FOUND,
                f"connector_run not found for run {run_id}",
                status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_CONNECTOR_RUN_NOT_FOUND),
            )
        raw_query_plan = row[0]
        if isinstance(raw_query_plan, dict):
            query_plan = dict(raw_query_plan)
        elif isinstance(raw_query_plan, str) and raw_query_plan.strip():
            query_plan = json.loads(raw_query_plan)
            query_plan = dict(query_plan) if isinstance(query_plan, dict) else {}
        else:
            query_plan = {}

        existing_refs = dict(query_plan.get("aps_validate_only_gates_report_refs") or {})
        artifact_refs = [str(item).strip() for item in list(existing_refs.get("aps_validate_only_gates_artifacts") or []) if str(item).strip()]
        failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_validate_only_gates_failures") or []) if str(item).strip()]
        if artifact_ref and artifact_ref not in artifact_refs:
            artifact_refs.append(artifact_ref)
        if failure_ref and failure_ref not in failure_refs:
            failure_refs.append(failure_ref)
        query_plan["aps_validate_only_gates_report_refs"] = {
            "aps_validate_only_gates_artifacts": artifact_refs,
            "aps_validate_only_gates_failures": failure_refs,
        }

        summaries = [dict(item or {}) for item in list(query_plan.get("aps_validate_only_gates_summaries") or []) if isinstance(item, dict)]
        if summary_entry is not None:
            target_id = str(summary_entry.get("validate_only_gates_id") or "").strip()
            target_ref = str(summary_entry.get("ref") or "").strip()
            kept: list[dict[str, Any]] = []
            replaced = False
            for item in summaries:
                same_id = str(item.get("validate_only_gates_id") or "").strip() == target_id
                same_ref = target_ref and str(item.get("ref") or "").strip() == target_ref
                if same_id or same_ref:
                    if not replaced:
                        kept.append(dict(summary_entry))
                        replaced = True
                    continue
                kept.append(item)
            if not replaced:
                kept.append(dict(summary_entry))
            kept.sort(key=lambda item: (str(item.get("validate_only_gates_id") or ""), str(item.get("ref") or "")))
            query_plan["aps_validate_only_gates_summaries"] = kept

        connection.execute(
            """
            UPDATE connector_run
            SET query_plan_json = ?
            WHERE connector_run_id = ?
              AND connector_key = ?
            """,
            (json.dumps(query_plan, sort_keys=True), run_id, "nrc_adams_aps"),
        )
        connection.commit()
    except ValidateOnlyGatesError:
        raise
    except (sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, str(exc), status_code=500) from exc
    finally:
        connection.close()


def _persist_failure_artifact(
    *,
    binding: review_nrc_aps_runtime.ReviewRuntimeBinding,
    normalized_request: dict[str, Any],
    error_code: str,
    error_message: str,
) -> str:
    failure_payload: dict[str, Any] = {
        "schema_id": contract.APS_VALIDATE_ONLY_GATES_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "validate_only_gates_id": contract.derive_failure_validate_only_gates_id(
            owner_run_id=binding.run_id,
            error_code=error_code,
        ),
        **contract.projection_identity_payload(),
        "owner_run_id": binding.run_id,
        "source_request": {
            "run_id": normalized_request.get("run_id"),
            "review_root": normalized_request.get("review_root"),
            "persist_validate_only_gates": bool(normalized_request.get("persist_validate_only_gates", False)),
        },
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["validate_only_gates_checksum"] = contract.compute_validate_only_gates_checksum(failure_payload)
    failure_path = validate_only_gates_failure_path(
        owner_run_id=binding.run_id,
        error_code=error_code,
        review_root=binding.review_root,
    )
    failure_ref = nrc_aps_sync_drift.write_json_deterministic(failure_path, failure_payload)
    if binding.database_path is not None and binding.database_path.exists():
        _artifact_registry_update(binding.database_path, run_id=binding.run_id, failure_ref=failure_ref)
    return failure_ref


def _persist_or_validate_validate_only_gates_artifact(
    *,
    artifact_path: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        existing_payload = _read_json(artifact_path)
        if not existing_payload:
            raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_CONFLICT, "existing validate-only gates artifact is unreadable", status_code=409)
        _validate_persisted_validate_only_gates_payload(existing_payload)
        if contract.logical_validate_only_gates_payload(existing_payload) != contract.logical_validate_only_gates_payload(payload):
            raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_CONFLICT, "existing validate-only gates artifact conflicts with derived artifact", status_code=409)
        existing_payload["_validate_only_gates_ref"] = str(artifact_path.resolve())
        existing_payload["_persisted"] = True
        return existing_payload, str(artifact_path.resolve())
    artifact_ref = nrc_aps_sync_drift.write_json_deterministic(artifact_path, payload)
    validated_payload = _read_json(artifact_path)
    _validate_persisted_validate_only_gates_payload(validated_payload)
    validated_payload["_validate_only_gates_ref"] = artifact_ref
    validated_payload["_persisted"] = True
    return validated_payload, artifact_ref


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "schema_id": str(payload.get("schema_id") or contract.APS_VALIDATE_ONLY_GATES_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION),
        "validate_only_gates_id": str(payload.get("validate_only_gates_id") or ""),
        "validate_only_gates_checksum": str(payload.get("validate_only_gates_checksum") or ""),
        "validate_only_gates_ref": str(payload.get("_validate_only_gates_ref") or "") or None,
        "owner_run_id": str(payload.get("owner_run_id") or ""),
        "source_review_runtime": dict(payload.get("source_review_runtime") or {}),
        "gate_results": dict(payload.get("gate_results") or {}),
        "gate_result_names": [str(item or "") for item in list(payload.get("gate_result_names") or [])],
        "gate_report_refs": [str(item or "") for item in list(payload.get("gate_report_refs") or [])],
        "gate_total": int(payload.get("gate_total") or 0),
        "gate_passed": int(payload.get("gate_passed") or 0),
        "gate_failed": int(payload.get("gate_failed") or 0),
        "persisted": bool(payload.get("_persisted", False)),
    }


def assemble_validate_only_gates(*, request_payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise ValidateOnlyGatesError(code, f"invalid request: {code}", status_code=_status_for_error_code(code)) from None

    binding = _load_binding_or_raise(
        run_id=str(normalized_request.get("run_id") or ""),
        review_root=normalized_request.get("review_root"),
    )
    persist_artifact = bool(normalized_request.get("persist_validate_only_gates", False))
    try:
        summary_path, summary, gate_report_refs, _normalized_gate_results = _collect_runtime_inputs(binding)
        payload = contract.build_validate_only_gates_payload(
            run_id=binding.run_id,
            summary_ref=str(summary_path),
            summary_payload=summary,
            gate_report_refs=gate_report_refs,
            generated_at_utc=_utc_iso(),
        )
        if persist_artifact:
            artifact_path = validate_only_gates_artifact_path(owner_run_id=binding.run_id, review_root=binding.review_root)
            payload, artifact_ref = _persist_or_validate_validate_only_gates_artifact(
                artifact_path=artifact_path,
                payload=payload,
            )
            if binding.database_path is None or not binding.database_path.exists():
                raise ValidateOnlyGatesError(
                    contract.APS_RUNTIME_FAILURE_CONNECTOR_RUN_NOT_FOUND,
                    f"connector_run database missing for run {binding.run_id}",
                    status_code=_status_for_error_code(contract.APS_RUNTIME_FAILURE_CONNECTOR_RUN_NOT_FOUND),
                )
            _artifact_registry_update(
                binding.database_path,
                run_id=binding.run_id,
                artifact_ref=artifact_ref,
                summary_entry={
                    "validate_only_gates_id": str(payload.get("validate_only_gates_id") or ""),
                    "validate_only_gates_checksum": str(payload.get("validate_only_gates_checksum") or ""),
                    "owner_run_id": binding.run_id,
                    "source_summary_ref": str(summary_path),
                    "gate_total": int(payload.get("gate_total") or 0),
                    "gate_passed": int(payload.get("gate_passed") or 0),
                    "gate_failed": int(payload.get("gate_failed") or 0),
                    "ref": artifact_ref,
                },
            )
            payload["_validate_only_gates_ref"] = artifact_ref
            payload["_persisted"] = True
        else:
            payload["_validate_only_gates_ref"] = None
            payload["_persisted"] = False
        return _response_payload(payload)
    except ValidateOnlyGatesError as exc:
        if persist_artifact:
            _persist_failure_artifact(
                binding=binding,
                normalized_request=normalized_request,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_artifact:
            _persist_failure_artifact(
                binding=binding,
                normalized_request=normalized_request,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise ValidateOnlyGatesError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def refresh_validate_only_gates(
    *,
    run_id: str,
    review_root: str | Path | None = None,
) -> dict[str, Any]:
    return assemble_validate_only_gates(
        request_payload={
            "run_id": str(run_id or "").strip(),
            "review_root": str(review_root or "").strip() or None,
            "persist_validate_only_gates": True,
        }
    )
