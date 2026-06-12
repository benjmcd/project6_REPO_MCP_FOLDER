from __future__ import annotations

from typing import Any

from app.services.layer3_utils import json_clone


ANALYSIS_PRODUCT_INVENTORY_PROJECTION_SCHEMA_ID = "layer3.analysis_product_inventory_projection.v1"
ANALYSIS_PRODUCT_INVENTORY_PROJECTION_AUTHORITY_SOURCE = "read_only_session_summary_projection"
SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID = "layer3.sublayer_visualization_state.v1"

# Pass-run statuses that represent a materialized analysis execution whose output
# is reviewable / packageable. Kept in sync with serialize_sublayer_pass_run status values.
_COMPLETED_PASS_STATES = {"completed", "completed_with_warnings"}
_FAILED_PASS_STATES = {"failed"}

# Each enumerated 3C product is a derived analysis execution output. We deliberately
# use the kind we can actually derive from persisted state (an analysis pass output),
# not the aspirational fact/metric/insight taxonomy, which is not present in the data.
_ANALYSIS_PASS_OUTPUT_KIND = "analysis_pass_output"
_OUTPUT_PACKAGE_KIND = "output_package"

# Mirror PACKAGE_STATUS_* in layer3_package_entry. A materialized output package is
# only handoff/delivery-eligible once it has terminally completed; review-only,
# handoff-blocked, and failed packages are surfaced with an explicit blocked reason.
_PACKAGE_DELIVERABLE_STATES = {"package_complete", "package_complete_with_warnings"}
_PACKAGE_BLOCKED_STATUS_REASONS = {
    "package_failed": "package_failed",
    "package_handoff_blocked": "package_handoff_blocked",
    "package_review_only": "package_review_only",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _payload_hash_by_snapshot(material_objects: list[Any]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for material_object in material_objects:
        record = _as_dict(material_object)
        snapshot_id = record.get("material_snapshot_id")
        if snapshot_id is None:
            continue
        mapping[str(snapshot_id)] = record.get("payload_hash")
    return mapping


def _analysis_set_by_id(analysis_sets: list[Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for analysis_set in analysis_sets:
        record = _as_dict(analysis_set)
        set_id = record.get("analysis_set_id")
        if set_id is None:
            continue
        mapping[str(set_id)] = record
    return mapping


def _product_scope(member_snapshot_ids: list[Any]) -> str:
    count = len(member_snapshot_ids)
    if count == 1:
        return "single"
    if count > 1:
        return "multi"
    return "unknown"


def _session_eligibility(package_authority: dict[str, Any]) -> dict[str, bool]:
    def recorded(step: str) -> bool:
        return bool(_as_dict(package_authority.get(step)).get("recorded"))

    return {
        "package_eligible": recorded("package_construction") or recorded("package_review_submit"),
        "handoff_eligible": recorded("handoff_export_prepare") or recorded("aps_handoff_dispatch"),
        "delivery_eligible": (
            recorded("external_local_export")
            or recorded("local_outbox_provider_private_handoff")
            or recorded("server_owned_local_outbox_write")
            or recorded("external_export_download")
        ),
    }


def _product_blocked_reasons(
    *,
    status: str | None,
    output_available: bool,
    analysis_set_resolved: bool,
    source_basis_present: bool,
) -> list[str]:
    reasons: list[str] = []
    if status in _FAILED_PASS_STATES:
        reasons.append("pass_failed")
    elif status not in _COMPLETED_PASS_STATES:
        reasons.append("pass_not_terminal")
    elif not output_available:
        reasons.append("output_payload_missing")
    if not analysis_set_resolved:
        reasons.append("analysis_set_unresolved")
    elif not source_basis_present:
        reasons.append("source_basis_unavailable")
    return reasons


def _enumerate_products(
    *,
    pass_runs: list[Any],
    analysis_set_by_id: dict[str, dict[str, Any]],
    payload_hash_by_snapshot: dict[str, Any],
    session_eligibility: dict[str, bool],
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for pass_run in pass_runs:
        record = _as_dict(pass_run)
        pass_run_id = record.get("pass_run_id")
        if pass_run_id is None:
            continue
        status = record.get("status")
        output_available = bool(record.get("output_payload_available"))
        set_id = record.get("analysis_set_id")
        analysis_set = analysis_set_by_id.get(str(set_id)) if set_id is not None else None
        analysis_set_resolved = analysis_set is not None
        member_snapshot_ids = [
            str(member)
            for member in _as_list(_as_dict(analysis_set).get("member_snapshot_ids"))
        ]
        source_basis_hashes = [
            payload_hash_by_snapshot[snapshot_id]
            for snapshot_id in member_snapshot_ids
            if snapshot_id in payload_hash_by_snapshot
            and payload_hash_by_snapshot[snapshot_id] is not None
        ]
        # A product is only downstream-eligible once its pass has terminally succeeded
        # and produced an output payload. Failed or in-flight passes are never advertised
        # as packageable/handoffable/deliverable even if a stale output ref exists.
        downstream_ready = output_available and status in _COMPLETED_PASS_STATES
        products.append(
            {
                "product_id": f"layer3_analysis_product:{pass_run_id}",
                "product_kind": _ANALYSIS_PASS_OUTPUT_KIND,
                "product_scope": _product_scope(member_snapshot_ids),
                "lifecycle_status": status,
                "output_payload_available": output_available,
                "engine_family": record.get("engine_family"),
                "pass_type": record.get("pass_type"),
                "source_refs": {
                    "pass_run_id": pass_run_id,
                    "analysis_run_id": record.get("analysis_run_id"),
                    "analysis_plan_id": record.get("analysis_plan_id"),
                    "analysis_set_id": set_id,
                },
                "provenance": {
                    "material_snapshot_ids": member_snapshot_ids,
                    "source_basis_hashes": source_basis_hashes,
                },
                "package_eligible": downstream_ready and session_eligibility["package_eligible"],
                "handoff_eligible": downstream_ready and session_eligibility["handoff_eligible"],
                "delivery_eligible": downstream_ready and session_eligibility["delivery_eligible"],
                "blocked_reasons": _product_blocked_reasons(
                    status=status,
                    output_available=output_available,
                    analysis_set_resolved=analysis_set_resolved,
                    source_basis_present=bool(source_basis_hashes),
                ),
            }
        )
    return products


def _rollup(products: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_lifecycle_status: dict[str, int] = {}
    by_scope: dict[str, int] = {}
    output_ready_count = 0
    package_eligible_count = 0
    for product in products:
        kind = str(product.get("product_kind"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
        raw_status = product.get("lifecycle_status")
        status = str(raw_status) if raw_status is not None else "unknown"
        by_lifecycle_status[status] = by_lifecycle_status.get(status, 0) + 1
        scope = str(product.get("product_scope"))
        by_scope[scope] = by_scope.get(scope, 0) + 1
        if product.get("output_payload_available"):
            output_ready_count += 1
        if product.get("package_eligible"):
            package_eligible_count += 1
    return {
        "by_kind": by_kind,
        "by_lifecycle_status": by_lifecycle_status,
        "by_scope": by_scope,
        "output_ready_count": output_ready_count,
        "package_eligible_count": package_eligible_count,
    }


def _enumerate_package_products(
    *,
    output_package_products: list[Any],
    session_eligibility: dict[str, bool],
    reconciliation: dict[str, Any],
) -> list[dict[str, Any]]:
    reconciliation_record_id = reconciliation.get("reconciliation_record_id")
    reconciliation_status = reconciliation.get("status")
    products: list[dict[str, Any]] = []
    for entry in output_package_products:
        record = _as_dict(entry)
        output_package_id = record.get("output_package_id")
        if output_package_id is None:
            continue
        status = record.get("status")
        deliverable = status in _PACKAGE_DELIVERABLE_STATES
        blocked_reasons: list[str] = []
        status_reason = _PACKAGE_BLOCKED_STATUS_REASONS.get(status)
        if status_reason is not None:
            blocked_reasons.append(status_reason)
        elif not deliverable:
            blocked_reasons.append("package_not_deliverable")
        package_reconciliation_id = record.get("reconciliation_record_id")
        # The session reconciliation record (unique per session) anchors every output
        # package; surface its authoritative status only when the package actually
        # references it, otherwise report None rather than implying a link.
        linked_reconciliation_status = (
            reconciliation_status
            if reconciliation_record_id is not None
            and package_reconciliation_id == reconciliation_record_id
            else None
        )
        products.append(
            {
                "product_id": f"layer3_output_package:{output_package_id}",
                "product_kind": _OUTPUT_PACKAGE_KIND,
                "package_kind": record.get("package_kind"),
                "lifecycle_status": status,
                "reconciliation_status": linked_reconciliation_status,
                "payload_hash": record.get("payload_hash"),
                "content": _as_dict(record.get("content")),
                "source_refs": {
                    "output_package_id": output_package_id,
                    "reconciliation_record_id": package_reconciliation_id,
                },
                # package_eligible is intentionally elided: a materialized output package
                # IS the package, so only downstream handoff/delivery eligibility applies.
                "handoff_eligible": deliverable and session_eligibility["handoff_eligible"],
                "delivery_eligible": deliverable and session_eligibility["delivery_eligible"],
                "blocked_reasons": blocked_reasons,
            }
        )
    return products


def _package_rollup(products: list[dict[str, Any]]) -> dict[str, Any]:
    by_package_kind: dict[str, int] = {}
    by_lifecycle_status: dict[str, int] = {}
    # Counts terminally-complete packages (empty blocked_reasons). This is a
    # package-intrinsic signal and deliberately does NOT fold in session handoff/
    # delivery authority, which is a session property surfaced in downstream_eligibility.
    terminally_complete_count = 0
    for product in products:
        kind = str(product.get("package_kind"))
        by_package_kind[kind] = by_package_kind.get(kind, 0) + 1
        raw_status = product.get("lifecycle_status")
        status = str(raw_status) if raw_status is not None else "unknown"
        by_lifecycle_status[status] = by_lifecycle_status.get(status, 0) + 1
        if not product.get("blocked_reasons"):
            terminally_complete_count += 1
    return {
        "by_package_kind": by_package_kind,
        "by_lifecycle_status": by_lifecycle_status,
        "terminally_complete_count": terminally_complete_count,
    }


_ANALYST_PROMOTABLE_STATUSES: frozenset[str] = frozenset({"draft", "proposed", "validated", "accepted"})


def _analyst_blocked_reasons(lifecycle_status: str) -> list[str]:
    """Return the blocked_reasons list for an analyst product based on lifecycle_status.

    Grounding is enforced authoritatively in the write-path promotion service (a draft
    cannot be accepted while ungrounded), so this read-only projection blocks purely on
    lifecycle state.
    """
    if lifecycle_status == "draft":
        return ["draft_not_promotable"]
    if lifecycle_status in ("proposed", "validated", "accepted"):
        return []
    if lifecycle_status == "rejected":
        return ["rejected"]
    if lifecycle_status == "superseded":
        return ["superseded"]
    if lifecycle_status == "package_eligible":
        return ["package_lane_not_wired"]
    return []


def _enumerate_analyst_products(analyst_products: list[Any]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for entry in _as_list(analyst_products):
        record = _as_dict(entry)
        analysis_product_id = record.get("analysis_product_id")
        if analysis_product_id is None:
            continue
        evidence_refs_raw = _as_list(record.get("evidence_refs"))
        bounded_refs = [
            {
                "ref_kind": ref.get("ref_kind"),
                "ref_id": ref.get("ref_id"),
                "evidence_role": ref.get("evidence_role"),
            }
            for ref in (_as_dict(r) for r in evidence_refs_raw)
        ]
        raw_status = record.get("lifecycle_status")
        lifecycle_status = str(raw_status) if raw_status is not None else "draft"
        promotable = lifecycle_status in _ANALYST_PROMOTABLE_STATUSES
        blocked_reasons = _analyst_blocked_reasons(lifecycle_status)
        # Pass through latest_review_decision from the serialized record (None if absent)
        latest_review_decision = record.get("latest_review_decision")
        # Pass through bounded generation_method {method_id, method_version} for
        # deterministic products; None for human-authored products.  The field is
        # produced by serialize_analysis_product and carries no payload_ref, URI,
        # or free-form provenance — only the two bounded identity keys.
        raw_generation_method = record.get("generation_method")
        generation_method = (
            {
                "method_id": _as_dict(raw_generation_method).get("method_id"),
                "method_version": _as_dict(raw_generation_method).get("method_version"),
            }
            if isinstance(raw_generation_method, dict)
            else None
        )
        products.append(
            {
                "product_id": f"layer3_analyst_product:{analysis_product_id}",
                "product_kind": record.get("product_kind"),
                "executor_type": record.get("executor_type"),
                "lifecycle_status": lifecycle_status,
                "grounded": record.get("grounded"),
                "is_non_evidentiary": bool(record.get("is_non_evidentiary")),
                "evidence_count": int(record.get("evidence_count") or 0),
                "by_evidence_role": _as_dict(record.get("by_evidence_role")),
                "evidence_refs": bounded_refs,
                "basis_hash": record.get("basis_hash"),
                "promotable": promotable,
                "blocked_reasons": blocked_reasons,
                "latest_review_decision": latest_review_decision,
                "generation_method": generation_method,
            }
        )
    return products


def _analyst_rollup(analyst_products: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_lifecycle_status: dict[str, int] = {}
    by_executor_type: dict[str, int] = {}
    grounded_count = 0
    non_evidentiary_count = 0
    package_eligible_count = 0
    for product in analyst_products:
        kind = str(product.get("product_kind") or "unknown")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        raw_status = product.get("lifecycle_status")
        status = str(raw_status) if raw_status is not None else "unknown"
        by_lifecycle_status[status] = by_lifecycle_status.get(status, 0) + 1
        raw_exec = product.get("executor_type")
        exec_type = str(raw_exec) if raw_exec is not None else "unknown"
        by_executor_type[exec_type] = by_executor_type.get(exec_type, 0) + 1
        if product.get("grounded"):
            grounded_count += 1
        if product.get("is_non_evidentiary"):
            non_evidentiary_count += 1
        if status == "package_eligible":
            package_eligible_count += 1
    return {
        "by_kind": by_kind,
        "by_lifecycle_status": by_lifecycle_status,
        "by_executor_type": by_executor_type,
        "grounded_count": grounded_count,
        "non_evidentiary_count": non_evidentiary_count,
        "package_eligible_count": package_eligible_count,
    }


def _analyst_by_working_set(analyst_products: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group analyst product_ids by working_set evidence ref, or under 'unscoped'."""
    result: dict[str, list[str]] = {}
    for product in analyst_products:
        product_id = product.get("product_id")
        if product_id is None:
            continue
        ws_ids: list[str] = [
            str(ref["ref_id"])
            for ref in _as_list(product.get("evidence_refs"))
            if _as_dict(ref).get("ref_kind") == "working_set"
            and _as_dict(ref).get("ref_id")
        ]
        if not ws_ids:
            result.setdefault("unscoped", []).append(str(product_id))
        else:
            for ws_id in ws_ids:
                result.setdefault(ws_id, []).append(str(product_id))
    return result


def analysis_product_inventory_projection(
    *,
    sublayer_visualization: dict[str, Any],
    analysis_environment_projection: dict[str, Any],
    execution_result_review: dict[str, Any],
    output_package_products: list[Any] | None = None,
    reconciliation: dict[str, Any] | None = None,
    analyst_products: list[Any] | None = None,
    working_sets: list[Any] | None = None,
    current_gate: str,
) -> dict[str, Any]:
    """Read-only unified inventory of derived Sublayer 3C analysis products for a session.

    This projection enumerates the derived analysis products a session has produced in
    two typed classes: pass-run analysis outputs (`products`) and materialized output
    packages (`package_products`). Each is linked to its source/basis/provenance refs
    and to downstream review/package/handoff/delivery eligibility where already
    derivable. It is a read-only derivation over already-built session-summary state
    plus read-only output-package rows: it mutates nothing and reuses
    analysis_environment_projection as the eligibility authority rather than re-deriving
    it. It complements (does not duplicate) analysis_environment_projection, which
    reports aggregate lifecycle/environment state rather than per-product identity.
    """
    sublayer = _as_dict(sublayer_visualization)
    environment = _as_dict(analysis_environment_projection)
    review = _as_dict(execution_result_review)
    package_product_inputs = output_package_products if isinstance(output_package_products, list) else []
    analyst_product_inputs = _as_list(analyst_products)
    working_set_inputs = working_sets if isinstance(working_sets, list) else None

    blocked_reasons: list[str] = []
    if sublayer.get("schema_id") != SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID:
        blocked_reasons.append("sublayer_visualization_missing_or_invalid")
    if sublayer.get("no_side_effects") is not True:
        blocked_reasons.append("sublayer_visualization_not_read_only")
    source_collection_counts_complete = not blocked_reasons

    material_objects = _as_list(sublayer.get("material_objects"))
    analysis_sets = _as_list(sublayer.get("analysis_sets"))
    pass_runs = _as_list(sublayer.get("pass_runs"))
    sublayer_collections_truncated = sublayer.get("sublayer_collections_truncated") is True
    source_collection_counts_complete = source_collection_counts_complete and not sublayer_collections_truncated

    package_authority = _as_dict(environment.get("package_authority"))
    session_eligibility = _session_eligibility(package_authority)
    reconciliation_input = _as_dict(reconciliation)
    # execution_result_review is persisted per-session (session.summary_json), not per
    # pass-run, so it is surfaced as a session-level signal rather than misattributed
    # onto each individual product.
    session_review_state = review.get("state") if isinstance(review.get("state"), str) else None

    if blocked_reasons:
        products: list[dict[str, Any]] = []
        package_products: list[dict[str, Any]] = []
        enumerated_analyst_products: list[dict[str, Any]] = []
        working_sets_out: list[dict[str, Any]] = []
    else:
        products = _enumerate_products(
            pass_runs=pass_runs,
            analysis_set_by_id=_analysis_set_by_id(analysis_sets),
            payload_hash_by_snapshot=_payload_hash_by_snapshot(material_objects),
            session_eligibility=session_eligibility,
        )
        package_products = _enumerate_package_products(
            output_package_products=package_product_inputs,
            session_eligibility=session_eligibility,
            reconciliation=reconciliation_input,
        )
        enumerated_analyst_products = _enumerate_analyst_products(analyst_product_inputs)
        # Bounded pass-through of serialized working sets (ids/name/member_count/basis_hash only)
        if working_set_inputs is not None:
            working_sets_out = [
                {
                    "working_set_id": _as_dict(ws).get("working_set_id"),
                    "name": _as_dict(ws).get("name"),
                    "member_count": _as_dict(ws).get("member_count"),
                    "basis_hash": _as_dict(ws).get("basis_hash"),
                }
                for ws in working_set_inputs
            ]
        else:
            working_sets_out = []

    if blocked_reasons:
        inventory_state = "blocked"
    elif products or package_products or enumerated_analyst_products:
        inventory_state = "products_present"
    else:
        inventory_state = "empty"

    analyst_by_working_set = _analyst_by_working_set(enumerated_analyst_products)

    return {
        "schema_id": ANALYSIS_PRODUCT_INVENTORY_PROJECTION_SCHEMA_ID,
        "authority_source": ANALYSIS_PRODUCT_INVENTORY_PROJECTION_AUTHORITY_SOURCE,
        "projection_mode": "read_only_session_summary_projection",
        "current_gate": current_gate,
        "inventory_state": inventory_state,
        "product_count": len(products),
        "products": products,
        "rollup": _rollup(products),
        "package_product_count": len(package_products),
        "package_products": package_products,
        "package_rollup": _package_rollup(package_products),
        "analyst_product_count": len(enumerated_analyst_products),
        "analyst_products": enumerated_analyst_products,
        "analyst_rollup": _analyst_rollup(enumerated_analyst_products),
        "working_set_count": len(working_sets_out),
        "working_sets": working_sets_out,
        "analyst_by_working_set": analyst_by_working_set,
        "reconciliation": {
            "present": bool(reconciliation_input),
            "reconciliation_record_id": reconciliation_input.get("reconciliation_record_id"),
            "status": reconciliation_input.get("status"),
            "package_status": reconciliation_input.get("package_status"),
        },
        "downstream_eligibility": {
            "package_eligible": session_eligibility["package_eligible"],
            "handoff_eligible": session_eligibility["handoff_eligible"],
            "delivery_eligible": session_eligibility["delivery_eligible"],
            "available_for_downstream_analysis": bool(
                environment.get("available_for_downstream_analysis")
            ),
            "environment_projection_state": environment.get("projection_state"),
            "session_review_state": session_review_state,
        },
        "blocked_reasons": blocked_reasons,
        "source_collection_counts_complete": source_collection_counts_complete,
        "sublayer_collections_truncated": sublayer_collections_truncated,
        # Scope: these flags describe the runtime authority of THIS read-only inventory
        # projection (it performs no writes and grants no package/promotion/dispatch
        # authority). They are NOT a global assertion that the system has no write routes
        # — analyst-draft authoring is a separate, inert, draft-only route.
        "forbidden_runtime_authority": {
            "write_route_enabled": False,
            "package_mutation_enabled": False,
            "source_promotion_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_url_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "no_side_effects": True,
        "sublayer_visualization_unchanged": json_clone(sublayer_visualization) == sublayer_visualization,
    }
