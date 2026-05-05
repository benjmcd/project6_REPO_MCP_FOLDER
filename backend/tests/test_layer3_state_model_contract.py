from app.services import layer3_workbench
from app.services.layer3_state_model_contract import (
    STATE_MODEL_SCHEMA_ID,
    build_workbench_state_model,
)


def test_layer3_state_model_contract_is_shared_without_behavior_change() -> None:
    direct_state_model = build_workbench_state_model(
        state_names=layer3_workbench.WORKBENCH_STATE_MODEL_STATE_NAMES
    )
    readiness_state_model = layer3_workbench.readiness_contract()["state_model"]

    assert direct_state_model == readiness_state_model
    assert readiness_state_model["schema_id"] == STATE_MODEL_SCHEMA_ID
    assert any(
        state["state"] == "execution_readiness_blocked"
        for state in readiness_state_model["states"]
    )
    assert any(
        state["state"] == "external_export_download_delivery_ready"
        for state in readiness_state_model["states"]
    )
