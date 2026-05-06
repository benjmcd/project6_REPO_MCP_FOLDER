from app.services import layer3_workbench
from app.services.layer3_bootstrap_contract import (
    BOOTSTRAP_FEATURE_FLAGS,
    BOOTSTRAP_SCHEMA_ID,
    build_bootstrap_contract,
)


def test_layer3_bootstrap_contract_is_shared() -> None:
    workbench_body = layer3_workbench.bootstrap()

    direct_body = build_bootstrap_contract(
        route=layer3_workbench.ROUTE,
        api_root=layer3_workbench.API_ROOT,
        supported_source_classes=layer3_workbench.SUPPORTED_SOURCE_CLASSES,
        unsupported_source_classes=layer3_workbench.UNSUPPORTED_SOURCE_CLASSES,
        gate_labels=layer3_workbench.GATE_LABELS,
        active_gate_labels=layer3_workbench.ACTIVE_GATES,
        unavailable_gate_labels=layer3_workbench.DOWNSTREAM_UNAVAILABLE,
        state_action_contract=workbench_body["state_action_contract"],
        authority_rail=workbench_body["authority_rail"],
    )
    direct_body["request_id"] = workbench_body["request_id"]
    direct_body["server_time"] = workbench_body["server_time"]

    assert direct_body == workbench_body
    assert direct_body["schema_id"] == BOOTSTRAP_SCHEMA_ID
    assert direct_body["features"] == dict(BOOTSTRAP_FEATURE_FLAGS)
    assert direct_body["features"]["single_aps_doc_qualitative_execution"] is True
    assert direct_body["features"]["plan_revision_recovery"] is True
    assert direct_body["features"]["approved_plan_cancel"] is True
    assert direct_body["features"]["broad_qualitative_execution"] is False
    assert direct_body["features"]["rag_vector_retrieval"] is False
    assert direct_body["features"]["dispatch"] is False
    assert direct_body["execution_readiness"]["dispatch_admitted"] is False
    assert direct_body["execution_readiness"]["plan_revision_recovery_admitted"] is True
    assert direct_body["execution_readiness"]["approved_plan_cancel_admitted"] is True
    assert direct_body["execution_readiness"]["readiness_state"] == "execution_readiness_blocked"
