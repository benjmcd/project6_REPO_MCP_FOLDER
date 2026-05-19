from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.layer3_analysis_environment_projection import (
    ANALYSIS_ENVIRONMENT_PROJECTION_AUTHORITY_SOURCE,
    ANALYSIS_ENVIRONMENT_PROJECTION_SCHEMA_ID,
    analysis_environment_projection,
)


def _projection(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "sublayer_visualization": {
            "schema_id": "layer3.sublayer_visualization_state.v1",
            "authority_source": "read_only_persisted_layer3_rows",
            "material_objects": [],
            "typing_records": [],
            "analysis_units": [],
            "analysis_sets": [],
            "pass_runs": [],
            "latest_plan": None,
            "no_side_effects": True,
        },
        "package_construction": {},
        "package_review_submit": {},
        "handoff_export_prepare": {},
        "aps_handoff_dispatch": {},
        "external_export_download": {},
        "server_owned_local_outbox_write": {},
        "local_outbox_provider_private_handoff": {},
        "external_local_export": {},
        "current_gate": "gate_c",
        "downstream_unavailable": ["plan", "execution", "results", "package"],
        "authority_rail": {
            "persistence_mode": "durable_layer3_control",
            "execution_enabled": False,
            "package_review_enabled": False,
        },
    }
    values.update(overrides)
    return analysis_environment_projection(**values)


def test_analysis_environment_projection_fails_closed_for_missing_sublayer() -> None:
    projection = _projection(sublayer_visualization={})

    assert projection["schema_id"] == ANALYSIS_ENVIRONMENT_PROJECTION_SCHEMA_ID
    assert projection["authority_source"] == ANALYSIS_ENVIRONMENT_PROJECTION_AUTHORITY_SOURCE
    assert projection["projection_state"] == "blocked"
    assert projection["available_for_downstream_analysis"] is False
    assert projection["blocked_reasons"] == [
        "sublayer_visualization_missing_or_invalid",
        "sublayer_visualization_not_read_only",
    ]
    assert projection["no_side_effects"] is True
    assert projection["forbidden_runtime_authority"] == {
        "write_route_enabled": False,
        "package_mutation_enabled": False,
        "source_promotion_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_url_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def test_analysis_environment_projection_reports_structural_state_without_inputs() -> None:
    projection = _projection()

    assert projection["projection_state"] == "structural"
    assert projection["available_for_downstream_analysis"] is False
    assert projection["blocked_reasons"] == ["analysis_environment_inputs_not_ready"]
    assert projection["source_state"] == {
        "sublayer_schema_id": "layer3.sublayer_visualization_state.v1",
        "material_object_count": 0,
        "typing_record_count": 0,
        "analysis_set_count": 0,
        "pass_run_count": 0,
        "output_payload_count": 0,
        "latest_plan_status": None,
        "latest_plan_approved": False,
    }
    assert {item["plane"]: item["state"] for item in projection["plane_readiness"]} == {
        "quantitative": "absent",
        "qualitative": "absent",
        "hybrid": "absent",
    }


def test_analysis_environment_projection_derives_delivery_ready_state_without_mutating_inputs() -> None:
    sublayer = {
        "schema_id": "layer3.sublayer_visualization_state.v1",
        "authority_source": "read_only_persisted_layer3_rows",
        "material_objects": [{"material_snapshot_id": "snapshot-1", "source_shape": "dataset_version"}],
        "typing_records": [{"typing_record_id": "typing-1", "chosen_modality": "quantitative"}],
        "analysis_units": [{"analysis_unit_id": "unit-1", "analysis_modality": "quantitative"}],
        "analysis_sets": [{"analysis_set_id": "set-1", "analysis_modality": "quantitative"}],
        "pass_runs": [
            {
                "pass_run_id": "pass-1",
                "analysis_set_id": "set-1",
                "status": "completed",
                "output_payload_available": True,
            }
        ],
        "latest_plan": {
            "analysis_plan_id": "plan-1",
            "plan_status": "approved",
            "approved": True,
        },
        "no_side_effects": True,
    }
    external_local_export = {
        "external_local_export_state": "external_local_export_recorded",
        "external_local_export_receipt_id": "export-1",
    }
    before_sublayer = deepcopy(sublayer)
    before_export = deepcopy(external_local_export)

    projection = _projection(
        sublayer_visualization=sublayer,
        external_local_export=external_local_export,
        current_gate="package",
        downstream_unavailable=["real_connector_invocation", "provider_public_delivery_use"],
    )

    assert sublayer == before_sublayer
    assert external_local_export == before_export
    assert projection["projection_state"] == "delivery_ready"
    assert projection["available_for_downstream_analysis"] is True
    assert projection["source_state"]["output_payload_count"] == 1
    assert projection["source_state"]["latest_plan_approved"] is True
    assert projection["package_authority"]["external_local_export"]["recorded"] is True
    assert projection["downstream_unavailable"] == [
        "real_connector_invocation",
        "provider_public_delivery_use",
    ]
    assert {item["plane"]: item["state"] for item in projection["plane_readiness"]} == {
        "quantitative": "output_ready",
        "qualitative": "absent",
        "hybrid": "absent",
    }
    assert projection["sublayer_visualization_unchanged"] is True
