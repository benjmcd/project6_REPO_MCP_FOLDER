from __future__ import annotations

from app.services.layer3_response_contract import LAYER3_SCHEMA_VERSION
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response


def test_layer3_workbench_error_contract_is_shared_without_behavior_change() -> None:
    exc = Layer3WorkbenchError(
        "test_error",
        "Test message.",
        status="blocked",
        http_status=409,
        recoverable=False,
        blocked_fields=["field_a"],
        next_allowed_actions=["fix_field_a"],
    )

    response = workbench_error_response(exc, request_id="fixed-request")

    assert response == {
        "schema_id": "layer3.workbench_error.v1",
        "schema_version": LAYER3_SCHEMA_VERSION,
        "request_id": "fixed-request",
        "server_time": response["server_time"],
        "status": "blocked",
        "error_code": "test_error",
        "message": "Test message.",
        "recoverable": False,
        "blocked_fields": ["field_a"],
        "next_allowed_actions": ["fix_field_a"],
    }
    assert response["server_time"].endswith("Z")
    assert exc.http_status == 409
