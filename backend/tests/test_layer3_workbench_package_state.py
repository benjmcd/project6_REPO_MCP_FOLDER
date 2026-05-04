from app.services.layer3_workbench_package_state import (
    active_downstream_unavailable,
    state_downstream_unavailable,
)


def test_state_downstream_unavailable_prefers_explicit_non_empty_state() -> None:
    assert state_downstream_unavailable(
        {"downstream_unavailable": ["next", 7]},
        fallback=("fallback",),
    ) == ("next", "7")


def test_state_downstream_unavailable_uses_fallback_for_missing_or_empty_state() -> None:
    assert state_downstream_unavailable({}, fallback=("fallback",)) == ("fallback",)
    assert state_downstream_unavailable(None, fallback=("fallback",)) == ("fallback",)
    assert state_downstream_unavailable({"downstream_unavailable": []}, fallback=("fallback",)) == ("fallback",)


def test_active_downstream_unavailable_returns_first_completed_stage_next_state() -> None:
    assert active_downstream_unavailable(
        transitions=(
            ({"state": "later_done"}, "later_done", {"downstream_unavailable": ["later_next"]}, ("later",)),
            ({"state": "earlier_done"}, "earlier_done", {"downstream_unavailable": ["earlier_next"]}, ("earlier",)),
        ),
        default_state={"downstream_unavailable": ["default_next"]},
        default_fallback=("default",),
    ) == ("later_next",)


def test_active_downstream_unavailable_falls_back_to_default_stage() -> None:
    assert active_downstream_unavailable(
        transitions=(
            (None, "done", {"downstream_unavailable": ["bad"]}, ("bad",)),
            ({"state": "pending"}, "done", {"downstream_unavailable": ["next"]}, ("next_fallback",)),
        ),
        default_state={},
        default_fallback=("default",),
    ) == ("default",)
