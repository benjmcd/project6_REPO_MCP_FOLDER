from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

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
    reconciliation: dict[str, Any] | None = None,
    analyst_products: list[dict[str, Any]] | None = None,
    working_sets: list[dict[str, Any]] | None = None,
    current_gate: str = "gate_c",
) -> dict[str, Any]:
    return analysis_product_inventory_projection(
        sublayer_visualization=sublayer if sublayer is not None else _sublayer(),
        analysis_environment_projection=environment if environment is not None else _env(),
        execution_result_review=execution_result_review if execution_result_review is not None else {},
        output_package_products=output_package_products,
        reconciliation=reconciliation,
        analyst_products=analyst_products,
        working_sets=working_sets,
        current_gate=current_gate,
    )


def _analyst_input(
    analysis_product_id: str,
    *,
    product_kind: str = "finding",
    executor_type: str = "human",
    lifecycle_status: str = "draft",
    grounded: bool = True,
    is_non_evidentiary: bool = False,
    evidence_count: int = 1,
    by_evidence_role: dict[str, int] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    basis_hash: str = "bhash",
) -> dict[str, Any]:
    return {
        "analysis_product_id": analysis_product_id,
        "product_kind": product_kind,
        "executor_type": executor_type,
        "lifecycle_status": lifecycle_status,
        "grounded": grounded,
        "is_non_evidentiary": is_non_evidentiary,
        "evidence_count": evidence_count,
        "by_evidence_role": by_evidence_role if by_evidence_role is not None else {"observation": 1},
        "evidence_refs": evidence_refs
        if evidence_refs is not None
        else [{"ref_kind": "material_snapshot", "ref_id": "snap-1", "evidence_role": "observation"}],
        "basis_hash": basis_hash,
    }


def test_inventory_enumerates_analyst_products_never_promotable() -> None:
    analyst = [
        _analyst_input("ap-1", product_kind="finding", grounded=True),
        _analyst_input("ap-2", product_kind="analyst_note", grounded=False, is_non_evidentiary=True, evidence_count=0, evidence_refs=[]),
    ]

    projection = _projection(analyst_products=analyst)

    assert projection["inventory_state"] == "products_present"
    assert projection["analyst_product_count"] == 2
    by_id = {product["product_id"]: product for product in projection["analyst_products"]}

    finding = by_id["layer3_analyst_product:ap-1"]
    assert finding["product_kind"] == "finding"
    assert finding["grounded"] is True
    assert finding["blocked_reasons"] == ["draft_not_promotable"]
    # analyst drafts are NEVER downstream-eligible — these keys must not be present/true
    assert "package_eligible" not in finding
    assert "handoff_eligible" not in finding
    assert "delivery_eligible" not in finding
    assert finding["evidence_refs"] == [
        {"ref_kind": "material_snapshot", "ref_id": "snap-1", "evidence_role": "observation"}
    ]

    rollup = projection["analyst_rollup"]
    assert rollup["by_kind"] == {"finding": 1, "analyst_note": 1}
    assert rollup["by_executor_type"] == {"human": 2}
    assert rollup["grounded_count"] == 1
    assert rollup["non_evidentiary_count"] == 1

    # Read-only safety invariants unchanged by the third class.
    assert projection["no_side_effects"] is True
    assert projection["forbidden_runtime_authority"] == {
        "write_route_enabled": False,
        "package_mutation_enabled": False,
        "source_promotion_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_url_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def test_inventory_analyst_rollup_counts_deterministic_executor_type() -> None:
    analyst = [
        _analyst_input("ap-human", executor_type="human"),
        _analyst_input("ap-det", executor_type="deterministic"),
    ]
    projection = _projection(analyst_products=analyst)
    assert projection["analyst_rollup"]["by_executor_type"] == {"human": 1, "deterministic": 1}
    by_id = {p["product_id"]: p for p in projection["analyst_products"]}
    assert by_id["layer3_analyst_product:ap-det"]["executor_type"] == "deterministic"


def test_inventory_analyst_products_only_marks_products_present() -> None:
    projection = _projection(analyst_products=[_analyst_input("ap-1")])
    assert projection["inventory_state"] == "products_present"
    assert projection["product_count"] == 0
    assert projection["package_product_count"] == 0
    assert projection["analyst_product_count"] == 1


def test_inventory_blocked_sublayer_suppresses_analyst_products() -> None:
    projection = _projection(sublayer={}, analyst_products=[_analyst_input("ap-1")])
    assert projection["inventory_state"] == "blocked"
    assert projection["analyst_products"] == []
    assert projection["analyst_product_count"] == 0


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
    assert projection["source_collection_counts_complete"] is False
    assert projection["sublayer_collections_truncated"] is False
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
    assert projection["source_collection_counts_complete"] is True
    assert projection["sublayer_collections_truncated"] is False


def test_inventory_reports_truncated_sublayer_source() -> None:
    projection = _projection(sublayer=_sublayer(sublayer_collections_truncated=True))

    assert projection["source_collection_counts_complete"] is False
    assert projection["sublayer_collections_truncated"] is True


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
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "output_package_id": output_package_id,
        "reconciliation_record_id": reconciliation_record_id,
        "package_kind": package_kind,
        "status": status,
        "payload_hash": payload_hash,
        "content": content if content is not None else {},
    }


def test_inventory_package_products_carry_content_descriptors() -> None:
    packages = [
        _package_input(
            "pkg-1",
            package_kind="canonical_internal",
            status="package_complete",
            content={"finding_count": 4, "contradiction_count": 1, "caveat_count": 2},
        ),
    ]

    projection = _projection(output_package_products=packages)
    product = projection["package_products"][0]

    assert product["content"] == {"finding_count": 4, "contradiction_count": 1, "caveat_count": 2}


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


def test_inventory_reconciliation_block_absent_by_default() -> None:
    projection = _projection()

    assert projection["reconciliation"] == {
        "present": False,
        "reconciliation_record_id": None,
        "status": None,
        "package_status": None,
    }


def test_inventory_surfaces_reconciliation_status_for_linked_packages() -> None:
    reconciliation = {
        "reconciliation_record_id": "recon-1",
        "status": "reconciled_with_warnings",
        "package_status": "package_complete_with_warnings",
    }
    packages = [
        _package_input("pkg-1", package_kind="canonical_internal", status="package_complete", reconciliation_record_id="recon-1"),
        _package_input("pkg-2", package_kind="user_facing", status="package_complete", reconciliation_record_id="recon-other"),
    ]

    projection = _projection(output_package_products=packages, reconciliation=reconciliation)

    assert projection["reconciliation"] == {
        "present": True,
        "reconciliation_record_id": "recon-1",
        "status": "reconciled_with_warnings",
        "package_status": "package_complete_with_warnings",
    }
    by_id = {product["product_id"]: product for product in projection["package_products"]}
    assert by_id["layer3_output_package:pkg-1"]["reconciliation_status"] == "reconciled_with_warnings"
    assert by_id["layer3_output_package:pkg-2"]["reconciliation_status"] is None


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


# ---------------------------------------------------------------------------
# Analyst product lifecycle_status blocked_reasons + promotable + latest_review_decision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lifecycle_status,expected_blocked,expected_promotable", [
    ("draft", ["draft_not_promotable"], True),
    ("proposed", [], True),
    ("validated", [], True),
    ("accepted", [], True),
    ("rejected", ["rejected"], False),
    ("package_eligible", ["package_lane_not_wired"], False),
])
def test_analyst_product_blocked_reasons_by_status(lifecycle_status, expected_blocked, expected_promotable) -> None:
    analyst = [_analyst_input("ap-1", lifecycle_status=lifecycle_status)]
    projection = _projection(analyst_products=analyst)
    ap = projection["analyst_products"][0]
    assert ap["blocked_reasons"] == expected_blocked
    assert ap["promotable"] is expected_promotable


def test_analyst_product_package_eligible_has_no_truthy_eligible_keys() -> None:
    """package_eligible status must NOT surface any *_eligible=True key on analyst products."""
    analyst = [_analyst_input("ap-pe", lifecycle_status="package_eligible")]
    projection = _projection(analyst_products=analyst)
    ap = projection["analyst_products"][0]
    assert ap.get("package_eligible") is None or ap.get("package_eligible") is False
    assert ap.get("handoff_eligible") is None or ap.get("handoff_eligible") is False
    assert ap.get("delivery_eligible") is None or ap.get("delivery_eligible") is False
    assert ap["blocked_reasons"] == ["package_lane_not_wired"]


def test_analyst_product_latest_review_decision_surfaced() -> None:
    """latest_review_decision passes through from the serialized record."""
    lrd = {
        "review_decision": "promote",
        "decision_reason_code": "proposed_ready",
        "from_status": "draft",
        "to_status": "proposed",
        "created_at": "2026-06-08T00:00:00+00:00",
    }
    analyst = [{**_analyst_input("ap-lrd", lifecycle_status="proposed"), "latest_review_decision": lrd}]
    projection = _projection(analyst_products=analyst)
    ap = projection["analyst_products"][0]
    assert ap["latest_review_decision"] == lrd


def test_analyst_product_latest_review_decision_none_when_absent() -> None:
    """latest_review_decision is None when not present in the input record."""
    analyst = [_analyst_input("ap-no-lrd", lifecycle_status="draft")]
    projection = _projection(analyst_products=analyst)
    ap = projection["analyst_products"][0]
    assert ap["latest_review_decision"] is None


def test_analyst_rollup_package_eligible_count() -> None:
    """analyst_rollup includes package_eligible_count."""
    analyst = [
        _analyst_input("ap-1", lifecycle_status="proposed"),
        _analyst_input("ap-2", lifecycle_status="package_eligible"),
        _analyst_input("ap-3", lifecycle_status="package_eligible"),
    ]
    projection = _projection(analyst_products=analyst)
    rollup = projection["analyst_rollup"]
    assert rollup["package_eligible_count"] == 2


def test_analyst_rollup_package_eligible_count_zero_when_none() -> None:
    """package_eligible_count is 0 when no products are package_eligible."""
    analyst = [_analyst_input("ap-1", lifecycle_status="draft")]
    projection = _projection(analyst_products=analyst)
    assert projection["analyst_rollup"]["package_eligible_count"] == 0


def test_analyst_draft_still_yields_draft_not_promotable() -> None:
    """Backward-compat: draft status still yields blocked_reasons == ['draft_not_promotable']."""
    analyst = [_analyst_input("ap-draft", lifecycle_status="draft")]
    projection = _projection(analyst_products=analyst)
    ap = projection["analyst_products"][0]
    assert ap["blocked_reasons"] == ["draft_not_promotable"]
    # also check the never-promotable safety invariants remain intact
    assert "package_eligible" not in ap
    assert "handoff_eligible" not in ap
    assert "delivery_eligible" not in ap


# ---------------------------------------------------------------------------
# Working-set surface tests
# ---------------------------------------------------------------------------


def _ws_input(
    working_set_id: str,
    *,
    name: str = "Test WS",
    member_count: int = 1,
    basis_hash: str = "bh-test",
) -> dict[str, Any]:
    return {
        "working_set_id": working_set_id,
        "name": name,
        "member_count": member_count,
        "basis_hash": basis_hash,
    }


def test_inventory_working_sets_surfaces_when_passed() -> None:
    ws = [_ws_input("ws-1", name="Alpha set", member_count=2)]
    projection = _projection(working_sets=ws)
    assert projection["working_set_count"] == 1
    assert projection["working_sets"] == [
        {"working_set_id": "ws-1", "name": "Alpha set", "member_count": 2, "basis_hash": "bh-test"}
    ]


def test_inventory_state_empty_with_only_working_sets_no_products() -> None:
    # Working sets are SCOPES, not products: a session with working sets but no
    # pass-run/package/analyst products is still products-wise 'empty' by design.
    projection = _projection(working_sets=[_ws_input("ws-1", name="Scope", member_count=1)])
    assert projection["working_set_count"] == 1
    assert projection["inventory_state"] == "empty"


def test_inventory_working_sets_pass_through_is_bounded() -> None:
    # Extra / unsafe fields on a serialized working set are stripped to the bounded shape.
    raw = {
        "working_set_id": "ws-1",
        "name": "Alpha",
        "member_count": 2,
        "basis_hash": "bh",
        "member_refs": [{"ref_kind": "material_snapshot", "ref_id": "snap-1"}],
        "provenance_json": {"secret": "x"},
        "created_at": "2026-06-08T00:00:00Z",
    }
    projection = _projection(working_sets=[raw])
    out = projection["working_sets"][0]
    assert out == {"working_set_id": "ws-1", "name": "Alpha", "member_count": 2, "basis_hash": "bh"}
    assert "member_refs" not in out
    assert "provenance_json" not in out


def test_inventory_working_sets_empty_when_not_passed() -> None:
    projection = _projection()
    assert projection["working_set_count"] == 0
    assert projection["working_sets"] == []


def test_inventory_working_sets_empty_when_empty_list() -> None:
    projection = _projection(working_sets=[])
    assert projection["working_set_count"] == 0
    assert projection["working_sets"] == []


def test_inventory_blocked_sublayer_working_sets_empty() -> None:
    ws = [_ws_input("ws-1")]
    projection = _projection(sublayer={}, working_sets=ws)
    assert projection["inventory_state"] == "blocked"
    assert projection["working_sets"] == []
    assert projection["working_set_count"] == 0


def test_inventory_analyst_by_working_set_groups_products() -> None:
    analyst = [
        _analyst_input(
            "ap-1",
            evidence_refs=[{"ref_kind": "working_set", "ref_id": "ws-1", "evidence_role": "context"}],
        ),
        _analyst_input(
            "ap-2",
            evidence_refs=[{"ref_kind": "working_set", "ref_id": "ws-1", "evidence_role": "context"}],
        ),
        _analyst_input(
            "ap-3",
            evidence_refs=[{"ref_kind": "material_snapshot", "ref_id": "snap-1", "evidence_role": "observation"}],
        ),
    ]
    projection = _projection(analyst_products=analyst)
    abws = projection["analyst_by_working_set"]
    assert set(abws["ws-1"]) == {"layer3_analyst_product:ap-1", "layer3_analyst_product:ap-2"}
    assert abws["unscoped"] == ["layer3_analyst_product:ap-3"]


def test_inventory_analyst_by_working_set_unscoped_when_no_refs() -> None:
    analyst = [_analyst_input("ap-only", evidence_refs=[])]
    projection = _projection(analyst_products=analyst)
    abws = projection["analyst_by_working_set"]
    assert "unscoped" in abws
    assert "layer3_analyst_product:ap-only" in abws["unscoped"]


def test_inventory_analyst_by_working_set_empty_when_no_products() -> None:
    projection = _projection()
    assert projection["analyst_by_working_set"] == {}


def test_inventory_no_side_effects_and_forbidden_runtime_authority_unchanged_with_working_sets() -> None:
    ws = [_ws_input("ws-1"), _ws_input("ws-2")]
    analyst = [_analyst_input("ap-1", evidence_refs=[{"ref_kind": "working_set", "ref_id": "ws-1", "evidence_role": "context"}])]
    projection = _projection(working_sets=ws, analyst_products=analyst)
    assert projection["no_side_effects"] is True
    assert projection["forbidden_runtime_authority"] == {
        "write_route_enabled": False,
        "package_mutation_enabled": False,
        "source_promotion_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_url_enabled": False,
        "frontend_durable_authority_enabled": False,
    }
