from __future__ import annotations

from app.services import layer3_workbench
from app.services.layer3_readiness_contract import (
    EXECUTION_READINESS_SCHEMA_ID,
    READINESS_DEFERRED_GATES,
    READINESS_IMPLEMENTED_GATES,
    READINESS_REQUIRED_GATES,
    build_readiness_contract,
)


def test_layer3_readiness_contract_is_shared_without_behavior_change() -> None:
    state_model = layer3_workbench._workbench_state_model()
    state_action_contract = layer3_workbench._workbench_state_action_contract()

    direct = build_readiness_contract(
        api_root=layer3_workbench.API_ROOT,
        state_model=state_model,
        state_action_contract=state_action_contract,
    )
    workbench = layer3_workbench.readiness_contract()

    for response in (direct, workbench):
        assert response["request_id"]
        assert response["server_time"].endswith("Z")
    direct_body = {key: value for key, value in direct.items() if key not in {"request_id", "server_time"}}
    workbench_body = {key: value for key, value in workbench.items() if key not in {"request_id", "server_time"}}

    assert direct_body == workbench_body
    assert direct["schema_id"] == EXECUTION_READINESS_SCHEMA_ID
    assert direct["required_gates"] == list(READINESS_REQUIRED_GATES)
    assert direct["implemented_gates"] == list(READINESS_IMPLEMENTED_GATES)
    assert direct["deferred_gates"] == list(READINESS_DEFERRED_GATES)
    assert direct["state_model"] == state_model
    assert direct["state_action_contract"] == state_action_contract
    assert direct["execution_enabled"] is False
    assert direct["dispatch_admitted"] is False
    assert direct["deferred_decisions"]["source_breadth"] == (
        "requires later freeze before RAG/vector/upload/local-directory expansion"
    )
