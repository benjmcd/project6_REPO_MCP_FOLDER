from __future__ import annotations

from app.services.layer3_pass_entry import Layer3PassEntryError
from app.services.layer3_plan_errors import plan_approval_workbench_error, plan_preview_workbench_error


def _mapped_preview(message: str):
    return plan_preview_workbench_error(Layer3PassEntryError(message))


def _mapped_approval(message: str):
    return plan_approval_workbench_error(Layer3PassEntryError(message))


def test_plan_preview_workbench_error_mapping_is_preserved() -> None:
    cases = [
        ("session was not found", "session_not_found", "invalid", 404, True),
        ("session must be finalized before plan preview", "gate_c_not_committed", "blocked", 409, True),
        ("session already has analysis plans", "plan_already_materialized", "conflict", 409, True),
        ("session already has pass runs", "plan_already_materialized", "conflict", 409, True),
        ("session has no analysis sets", "no_analysis_sets", "blocked", 409, True),
        ("session has no admissible analysis sets", "no_admissible_plan", "blocked", 409, True),
        ("unexpected owner failure", "owner_service_error", "failed", 500, False),
    ]

    for message, error_code, status, http_status, recoverable in cases:
        mapped = _mapped_preview(message)

        assert mapped.error_code == error_code
        assert mapped.status == status
        assert mapped.http_status == http_status
        assert mapped.recoverable is recoverable
        assert str(mapped.message) == message


def test_plan_approval_workbench_error_mapping_is_preserved() -> None:
    preview_mismatch = _mapped_approval("preview hash mismatch for approved plan")
    assert preview_mismatch.error_code == "preview_mismatch"
    assert preview_mismatch.status == "conflict"
    assert preview_mismatch.http_status == 409

    confirmation = _mapped_approval("operator confirmation is required")
    assert confirmation.error_code == "operator_confirmation_required"
    assert confirmation.status == "blocked"
    assert confirmation.http_status == 400
    assert confirmation.blocked_fields == ["operator_confirmation"]
    assert confirmation.next_allowed_actions == ["confirm_plan_approval"]

    materialized = _mapped_approval("session already has analysis plans")
    assert materialized.error_code == "plan_already_materialized"
    assert materialized.status == "conflict"
    assert materialized.http_status == 409

    pass_runs = _mapped_approval("session already has pass runs")
    assert pass_runs.error_code == "pass_runs_already_exist"
    assert pass_runs.status == "conflict"
    assert pass_runs.http_status == 409

    fallback = _mapped_approval("session has no admissible analysis sets")
    assert fallback.error_code == "no_admissible_plan"
    assert fallback.status == "blocked"
    assert fallback.http_status == 409
