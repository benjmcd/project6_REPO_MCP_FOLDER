from __future__ import annotations

from app.services import layer3_workbench
from app.services.layer3_response_contract import LAYER3_SCHEMA_VERSION, base_response


def test_layer3_base_response_contract_is_shared_without_behavior_change() -> None:
    response = base_response("layer3.test_response.v1", request_id="fixed-request", status="blocked")

    assert response["schema_id"] == "layer3.test_response.v1"
    assert response["schema_version"] == LAYER3_SCHEMA_VERSION
    assert response["request_id"] == "fixed-request"
    assert response["status"] == "blocked"
    assert response["server_time"].endswith("Z")

    bootstrap = layer3_workbench.bootstrap()
    assert bootstrap["schema_version"] == LAYER3_SCHEMA_VERSION
    assert bootstrap["schema_id"] == "layer3.workbench_bootstrap.v1"
