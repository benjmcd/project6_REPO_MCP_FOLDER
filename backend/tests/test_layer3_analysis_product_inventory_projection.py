from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.layer3_analysis_product_inventory_projection import (
    ANALYSIS_PRODUCT_INVENTORY_PROJECTION_AUTHORITY_SOURCE,
    ANALYSIS_PRODUCT_INVENTORY_PROJECTION_SCHEMA_ID,
    analysis_product_inventory_projection,
)


def _sublayer(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_id": "layer3.sublayer_visualization_state.v1",
        "authority_source": "read_only_persisted_layer3_rows",
        "material_objects": [],
        "typing_records": [],
        "analysis_units": [],
        "analysis_sets": [],
        "pass_runs": [],
        "latest_plan": None,
        "no_side_effects": True,
    }
    base.update(overrides)
    return base


def _package_authority(**recorded: bool) -> dict[str, dict[str, Any]]:
    steps = (
        "package_construction",
        "package_review_submit",
        "handoff_export_prepare",
        "aps_handoff_dispatch",
        "external_export_download",
        "server_owned_local_outbox_write",
        "local_outbox_provider_private_handoff",
        "external_local_export",
    )
    return {step: {"recorded": bool(recorded.get(step, False))} for step in steps}


def _env(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_id": "layer3.analysis_environment_projection.v1",
        "projection_state": "structural",
        "available_for_downstream_analysis": False,
        "package_authority": _package_authority(),
    }
    base.update(overrides)
    return base


def _projection(
    *,
    sublayer: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    execution_result_review: dict[str, Any] | None = None,
    output_package_products: list[dict[str, Any]] | None = None,
    current_gate: str = "gate_c",
) -> dict[str, Any]:
    return analysis_product_inventory_projection(
        sublayer_visualization=sublayer if sublayer is not None else _sublayer(),
        analysis_environment_projection=environment if environment is not None else _env(),
        execution_result_review=execution_result_review if execution_result_review is not None else {},
        output_package_products=output_package_products,
        current_gate=current_gate,
    )


def test_inventory_fails_closed_for_missing_sublayer() -> None:
    projection = _projection(sublayer={})

    assert projection["schema_id"] == ANALYSIS_PRODUCT_INVENTORY_PROJECTION_SCHEMA_ID
    assert projection["authority_source"] == ANALYSIS_PRODUCT_INVENTORY_PROJECTION_AUTHORITY_SOURCE
    assert projection["inventory_state"] == "blocked"
    assert projection["product_count"] == 0
    assert projection["products"] == []
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


def test_inventory_empty_without_pass_runs() -> None:
    projection = _projection()

    assert projection["inventory_state"] == "empty"
    assert projection["product_count"] == 0
    assert projection["products"] == []
    assert projection["rollup"]["by_kind"] == {}
    assert projection["downstream_eligibility"] == {
        "package_eligible": False,
        "handoff_eligible": False,
        "delivery_eligible": False,
        "available_for_downstream_analysis": False,
        "environment_projection_state": "structural",
        "session_review_state": None,
    }
    assert projection["no_side_effects"] is True


def test_inventory_blocked_for_non_read_only_sublayer() -> None:
    projection = _projection(
        sublayer=_sublayer(no_side_effects=False),
    )

    assert projection["inventory_state"] == "blocked"
    assert projection["blocked_reasons"] == ["sublayer_visualization_not_read_only"]
    assert projection["products"] == []


def test_inventory_enumerates_products_with_provenance_without_mutating_inputs() -> None:
    sublayer = _sublayer(
        material_objects=[
            {"material_snapshot_id": "snap-1", "payload_hash": "hash-1"},
            {"material_snapshot_id": "snap-2", "payload_hash": "hash-2"},
        ],
        analysis_sets=[
            {"analysis_set_id": "set-1", "member_snapshot_ids": ["snap-1", "snap-2"]},
        ],
        pass_runs=[
            {
                "pass_run_id": "pass-1",
                "analysis_plan_id": "plan-1",
                "analysis_set_id": "set-1",
                "analysis_run_id": "run-1",
                "engine_family": "quantitative_engine",
                "pass_type": "summary_statistics",
                "status": "completed",
                "output_payload_available": True,
            }
        ],
    )
    environment = _env(
        projection_state="package_ready",
        available_for_downstream_analysis=True,
        package_authority=_package_authority(package_construction=True),
    )
    review = {"state": "execution_result_review_approved"}
    before_sublayer = deepcopy(sublayer)
    before_env = deepcopy(environment)

    projection = _projection(
        sublayer=sublayer,
        environment=environment,
        execution_result_review=review,
        current_gate="package",
    )

    assert sublayer == before_sublayer
    assert environment == before_env
    assert projection["inventory_state"] == "products_present"
    assert projection["product_count"] == 1

    product = projection["products"][0]
    assert product["product_id"] == "layer3_analysis_product:pass-1"
    assert product["product_kind"] == "analysis_pass_output"
    assert product["product_scope"] == "multi"
    assert product["lifecycle_status"] == "completed"
    assert product["output_payload_available"] is True
    assert product["engine_family"] == "quantitative_engine"
    assert product["pass_type"] == "summary_statistics"
    assert product["source_refs"] == {
        "pass_run_id": "pass-1",
        "analysis_run_id": "run-1",
        "analysis_plan_id": "plan-1",
        "analysis_set_id": "set-1",
    }
    assert product["provenance"] == {
        "material_snapshot_ids": ["snap-1", "snap-2"],
        "source_basis_hashes": ["hash-1", "hash-2"],
    }
    assert "review_state" not in product
    assert product["package_eligible"] is True
    assert product["handoff_eligible"] is False
    assert product["delivery_eligible"] is False
    assert product["blocked_reasons"] == []

    assert projection["rollup"]["output_ready_count"] == 1
    assert projection["rollup"]["package_eligible_count"] == 1
    assert projection["rollup"]["by_scope"] == {"multi": 1}
    assert projection["rollup"]["by_kind"] == {"analysis_pass_output": 1}
    assert projection["rollup"]["by_lifecycle_status"] == {"completed": 1}
    assert projection["downstream_eligibility"]["package_eligible"] is True
    assert projection["downstream_eligibility"]["available_for_downstream_analysis"] is True
    assert projection["downstream_eligibility"]["session_review_state"] == "execution_result_review_approved"
    assert projection["sublayer_visualization_unchanged"] is True


def test_inventory_handoff_and_delivery_eligible_true_paths() -> None:
    def _completed_pass(pass_run_id: str) -> dict[str, Any]:
        return {
            "pass_run_id": pass_run_id,
            "analysis_set_id": "set-1",
            "status": "completed",
            "output_payload_available": True,
        }

    sublayer = _sublayer(
        material_objects=[{"material_snapshot_id": "snap-1", "payload_hash": "hash-1"}],
        analysis_sets=[{"analysis_set_id": "set-1", "member_snapshot_ids": ["snap-1"]}],
        pass_runs=[_completed_pass("pass-1")],
    )

    handoff_env = _env(package_authority=_package_authority(handoff_export_prepare=True))
    handoff = _projection(sublayer=sublayer, environment=handoff_env)
    assert handoff["products"][0]["handoff_eligible"] is True
    assert handoff["products"][0]["package_eligible"] is False
    assert handoff["downstream_eligibility"]["handoff_eligible"] is True

    delivery_env = _env(package_authority=_package_authority(external_local_export=True))
    delivery = _projection(sublayer=sublayer, environment=delivery_env)
    assert delivery["products"][0]["delivery_eligible"] is True
    assert delivery["downstream_eligibility"]["delivery_eligible"] is True


def test_inventory_eligibility_requires_terminal_success() -> None:
    sublayer = _sublayer(
        material_objects=[{"material_snapshot_id": "snap-1", "payload_hash": "hash-1"}],
        analysis_sets=[{"analysis_set_id": "set-1", "member_snapshot_ids": ["snap-1"]}],
        pass_runs=[
            # failed pass carrying a stale output ref must never be advertised eligible
            {"pass_run_id": "pass-failed", "analysis_set_id": "set-1", "status": "failed", "output_payload_available": True},
            # in-flight pass with output present is likewise not yet eligible
            {"pass_run_id": "pass-running", "analysis_set_id": "set-1", "status": "running", "output_payload_available": True},
        ],
    )
    environment = _env(package_authority=_package_authority(package_construction=True))

    projection = _projection(sublayer=sublayer, environment=environment)
    by_id = {product["product_id"]: product for product in projection["products"]}

    failed = by_id["layer3_analysis_product:pass-failed"]
    assert failed["package_eligible"] is False
    assert failed["blocked_reasons"] == ["pass_failed"]

    running = by_id["layer3_analysis_product:pass-running"]
    assert running["package_eligible"] is False
    assert running["blocked_reasons"] == ["pass_not_terminal"]
    assert projection["rollup"]["package_eligible_count"] == 0


def test_inventory_flags_failed_incomplete_and_unbased_products() -> None:
    sublayer = _sublayer(
        material_objects=[{"material_snapshot_id": "snap-1", "payload_hash": "hash-1"}],
        analysis_sets=[
            {"analysis_set_id": "set-1", "member_snapshot_ids": ["snap-1"]},
            {"analysis_set_id": "set-nobasis", "member_snapshot_ids": ["snap-missing"]},
        ],
        pass_runs=[
            {
                "pass_run_id": "pass-failed",
                "analysis_set_id": "set-1",
                "status": "failed",
                "output_payload_available": False,
            },
            {
                "pass_run_id": "pass-incomplete",
                "analysis_set_id": "set-1",
                "status": "completed",
                "output_payload_available": False,
            },
            {
                "pass_run_id": "pass-unresolved",
                "analysis_set_id": "missing-set",
                "status": "completed",
                "output_payload_available": True,
            },
            {
                "pass_run_id": "pass-nobasis",
                "analysis_set_id": "set-nobasis",
                "status": "running",
                "output_payload_available": False,
            },
        ],
    )
    environment = _env(package_authority=_package_authority(package_construction=True))

    projection = _projection(sublayer=sublayer, environment=environment)
    by_id = {product["product_id"]: product for product in projection["products"]}

    failed = by_id["layer3_analysis_product:pass-failed"]
    assert failed["blocked_reasons"] == ["pass_failed"]
    assert failed["product_scope"] == "single"
    assert failed["package_eligible"] is False

    incomplete = by_id["layer3_analysis_product:pass-incomplete"]
    assert incomplete["blocked_reasons"] == ["output_payload_missing"]
    assert incomplete["package_eligible"] is False

    unresolved = by_id["layer3_analysis_product:pass-unresolved"]
    assert unresolved["product_scope"] == "unknown"
    assert unresolved["blocked_reasons"] == ["analysis_set_unresolved"]
    assert unresolved["package_eligible"] is True

    nobasis = by_id["layer3_analysis_product:pass-nobasis"]
    assert nobasis["blocked_reasons"] == ["pass_not_terminal", "source_basis_unavailable"]
    assert nobasis["provenance"]["source_basis_hashes"] == []

    assert projection["rollup"]["by_kind"] == {"analysis_pass_output": 4}
    assert projection["rollup"]["by_lifecycle_status"] == {
        "failed": 1,
        "completed": 2,
        "running": 1,
    }


def _package_input(
    output_package_id: str,
    *,
    package_kind: str,
    status: str,
    payload_hash: str = "phash",
    reconciliation_record_id: str = "recon-1",
) -> dict[str, Any]:
    return {
        "output_package_id": output_package_id,
        "reconciliation_record_id": reconciliation_record_id,
        "package_kind": package_kind,
        "status": status,
        "payload_hash": payload_hash,
    }


def test_inventory_enumerates_output_package_products_with_eligibility() -> None:
    environment = _env(
        package_authority=_package_authority(handoff_export_prepare=True, external_local_export=True),
    )
    packages = [
        _package_input("pkg-1", package_kind="canonical_internal", status="package_complete"),
        _package_input("pkg-2", package_kind="user_facing", status="package_complete_with_warnings"),
        _package_input("pkg-3", package_kind="review_facing", status="package_review_only"),
        _package_input("pkg-4", package_kind="user_facing", status="package_failed"),
        _package_input("pkg-5", package_kind="user_facing", status="package_handoff_blocked"),
        _package_input("pkg-6", package_kind="user_facing", status="package_unknown_state"),
    ]

    projection = _projection(environment=environment, output_package_products=packages)

    assert projection["inventory_state"] == "products_present"
    assert projection["package_product_count"] == 6
    by_id = {product["product_id"]: product for product in projection["package_products"]}

    complete = by_id["layer3_output_package:pkg-1"]
    assert complete["product_kind"] == "output_package"
    assert complete["package_kind"] == "canonical_internal"
    assert complete["payload_hash"] == "phash"
    assert "review_linked" not in complete
    assert complete["source_refs"] == {
        "output_package_id": "pkg-1",
        "reconciliation_record_id": "recon-1",
    }
    assert complete["handoff_eligible"] is True
    assert complete["delivery_eligible"] is True
    assert complete["blocked_reasons"] == []
    assert "payload_ref" not in complete

    warned = by_id["layer3_output_package:pkg-2"]
    assert warned["handoff_eligible"] is True
    assert warned["blocked_reasons"] == []

    review_only = by_id["layer3_output_package:pkg-3"]
    assert review_only["handoff_eligible"] is False
    assert review_only["delivery_eligible"] is False
    assert review_only["blocked_reasons"] == ["package_review_only"]

    failed = by_id["layer3_output_package:pkg-4"]
    assert failed["handoff_eligible"] is False
    assert failed["blocked_reasons"] == ["package_failed"]

    handoff_blocked = by_id["layer3_output_package:pkg-5"]
    assert handoff_blocked["handoff_eligible"] is False
    assert handoff_blocked["delivery_eligible"] is False
    assert handoff_blocked["blocked_reasons"] == ["package_handoff_blocked"]

    unknown = by_id["layer3_output_package:pkg-6"]
    assert unknown["blocked_reasons"] == ["package_not_deliverable"]

    assert projection["package_rollup"]["by_package_kind"] == {
        "canonical_internal": 1,
        "user_facing": 4,
        "review_facing": 1,
    }
    assert projection["package_rollup"]["by_lifecycle_status"] == {
        "package_complete": 1,
        "package_complete_with_warnings": 1,
        "package_review_only": 1,
        "package_failed": 1,
        "package_handoff_blocked": 1,
        "package_unknown_state": 1,
    }
    assert projection["package_rollup"]["terminally_complete_count"] == 2


def test_inventory_package_delivery_eligible_isolated_from_handoff() -> None:
    sublayer = _sublayer()
    packages = [_package_input("pkg-1", package_kind="user_facing", status="package_complete")]

    delivery_env = _env(package_authority=_package_authority(external_local_export=True))
    delivery = _projection(sublayer=sublayer, environment=delivery_env, output_package_products=packages)
    product = delivery["package_products"][0]
    assert product["delivery_eligible"] is True
    assert product["handoff_eligible"] is False


def test_inventory_package_products_only_marks_products_present() -> None:
    packages = [_package_input("pkg-1", package_kind="canonical_internal", status="package_complete")]

    projection = _projection(output_package_products=packages)

    assert projection["inventory_state"] == "products_present"
    assert projection["product_count"] == 0
    assert projection["package_product_count"] == 1


def test_inventory_blocked_sublayer_suppresses_package_products() -> None:
    packages = [_package_input("pkg-1", package_kind="canonical_internal", status="package_complete")]

    projection = _projection(sublayer={}, output_package_products=packages)

    assert projection["inventory_state"] == "blocked"
    assert projection["package_products"] == []
    assert projection["package_product_count"] == 0


def test_inventory_surfaces_review_state_at_session_level_not_per_product() -> None:
    sublayer = _sublayer(
        analysis_sets=[{"analysis_set_id": "set-1", "member_snapshot_ids": []}],
        pass_runs=[
            {"pass_run_id": "pass-running", "analysis_set_id": "set-1", "status": "running", "output_payload_available": False},
            {"pass_run_id": "pass-done", "analysis_set_id": "set-1", "status": "completed_with_warnings", "output_payload_available": True},
        ],
    )
    review = {"state": "execution_result_review_approved"}

    projection = _projection(sublayer=sublayer, execution_result_review=review)

    assert projection["downstream_eligibility"]["session_review_state"] == "execution_result_review_approved"
    assert all("review_state" not in product for product in projection["products"])
