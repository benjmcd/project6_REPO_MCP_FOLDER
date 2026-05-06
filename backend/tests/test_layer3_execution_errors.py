from __future__ import annotations

from app.services.layer3_execution_errors import analysis_execution_start_workbench_error
from app.services.layer3_pass_entry import Layer3PassEntryError
from app.services.layer3_qual_aps_execution import Layer3QualApsExecutionError


def test_analysis_execution_start_maps_pass_entry_error_without_behavior_change() -> None:
    mapped = analysis_execution_start_workbench_error(Layer3PassEntryError("pass entry blocked"))

    assert mapped.error_code == "analysis_execution_start_not_admitted"
    assert mapped.message == "pass entry blocked"
    assert mapped.status == "conflict"
    assert mapped.http_status == 409
    assert mapped.recoverable is True
    assert mapped.blocked_fields == []
    assert mapped.next_allowed_actions == []


def test_analysis_execution_start_maps_qual_aps_error_without_behavior_change() -> None:
    mapped = analysis_execution_start_workbench_error(Layer3QualApsExecutionError("qualitative pass blocked"))

    assert mapped.error_code == "analysis_execution_start_not_admitted"
    assert mapped.message == "qualitative pass blocked"
    assert mapped.status == "conflict"
    assert mapped.http_status == 409
    assert mapped.recoverable is True
    assert mapped.blocked_fields == []
    assert mapped.next_allowed_actions == []
