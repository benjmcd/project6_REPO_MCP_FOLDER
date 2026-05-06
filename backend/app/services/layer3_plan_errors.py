from __future__ import annotations

from app.services.layer3_pass_entry import Layer3PassEntryError
from app.services.layer3_workbench_error import Layer3WorkbenchError


def plan_preview_workbench_error(exc: Layer3PassEntryError) -> Layer3WorkbenchError:
    message = str(exc)
    if "was not found" in message:
        return Layer3WorkbenchError("session_not_found", message, http_status=404)
    if "must be finalized" in message:
        return Layer3WorkbenchError("gate_c_not_committed", message, status="blocked", http_status=409)
    if "already has analysis plans" in message or "already has pass runs" in message:
        return Layer3WorkbenchError("plan_already_materialized", message, status="conflict", http_status=409)
    if "has no analysis sets" in message:
        return Layer3WorkbenchError("no_analysis_sets", message, status="blocked", http_status=409)
    if "has no admissible analysis sets" in message:
        return Layer3WorkbenchError("no_admissible_plan", message, status="blocked", http_status=409)
    return Layer3WorkbenchError(
        "owner_service_error",
        message,
        status="failed",
        http_status=500,
        recoverable=False,
    )


def plan_approval_workbench_error(exc: Layer3PassEntryError) -> Layer3WorkbenchError:
    message = str(exc)
    if "preview hash mismatch" in message:
        return Layer3WorkbenchError("preview_mismatch", message, status="conflict", http_status=409)
    if "operator confirmation" in message:
        return Layer3WorkbenchError(
            "operator_confirmation_required",
            message,
            status="blocked",
            http_status=400,
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_plan_approval"],
        )
    if "already has analysis plans" in message:
        return Layer3WorkbenchError("plan_already_materialized", message, status="conflict", http_status=409)
    if "already has pass runs" in message:
        return Layer3WorkbenchError("pass_runs_already_exist", message, status="conflict", http_status=409)
    return plan_preview_workbench_error(exc)
