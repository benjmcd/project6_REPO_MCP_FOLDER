from __future__ import annotations

from app.services import layer3_workbench
from app.services.layer3_authority_rail import DEFAULT_DOWNSTREAM_UNAVAILABLE, authority_rail
from app.services.layer3_response_contract import LAYER3_SCHEMA_VERSION


def test_layer3_authority_rail_contract_is_shared_without_behavior_change() -> None:
    rail = authority_rail(
        session_id="session-1",
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        current_gate="gate_b",
        persistence_mode="preview_only",
        source_classes=["dataset_version"],
        counts={"approved": 2, "flagged": 1},
        typing_status="committed",
        browser_only_state=["selected_tab"],
        execution_enabled=True,
        package_review_enabled=True,
    )

    assert rail["schema_id"] == "layer3.authority_rail.v1"
    assert rail["schema_version"] == LAYER3_SCHEMA_VERSION
    assert rail["session_id"] == "session-1"
    assert rail["preflight_id"] == "preflight-1"
    assert rail["source_set_id"] == "source-set-1"
    assert rail["source_authority"]["source_classes"] == ["dataset_version"]
    assert rail["approved_material_count"] == 2
    assert rail["denied_material_count"] == 0
    assert rail["flagged_material_count"] == 1
    assert rail["typing_status"] == "committed"
    assert rail["execution_enabled"] is True
    assert rail["package_review_enabled"] is True
    assert rail["downstream_unavailable"] == list(DEFAULT_DOWNSTREAM_UNAVAILABLE)
    assert rail["browser_only_state"] == ["selected_tab"]

    bootstrap_rail = layer3_workbench.bootstrap()["authority_rail"]
    assert bootstrap_rail["schema_id"] == "layer3.authority_rail.v1"
    assert bootstrap_rail["schema_version"] == LAYER3_SCHEMA_VERSION
    assert bootstrap_rail["downstream_unavailable"] == list(DEFAULT_DOWNSTREAM_UNAVAILABLE)
