import hashlib
import json
from types import SimpleNamespace

from app.services.layer3_workbench_package_state import (
    COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
    PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_PREVIEW_READY_STATE,
    PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID,
    PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_SUBMIT_LEGACY_AUTHORITY_FIELDS,
    APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
    HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
    PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
    active_downstream_unavailable,
    aps_handoff_dispatch_from_reconciliation,
    canonical_payload_hashes,
    canonical_payload_refs,
    canonical_payload_values,
    cohort_package_construction_source,
    dispatched_package_id,
    external_export_download_prepare_from_reconciliation,
    handoff_export_prepare_from_reconciliation,
    legacy_package_review_submit_record_ref,
    package_owner_compatibility,
    package_review_candidate_projection,
    package_review_preview_hash,
    package_review_preview_summary,
    package_review_submit_downstream_unavailable,
    package_review_submit_from_reconciliation,
    package_source_dataset_version_ids,
    package_source_shape,
    packages_in_review_order,
    packages_in_kind_order,
    packages_with_kinds,
    reconciliation_state,
    review_source_packages,
    review_state_is_admitted_associated_cohort,
    state_downstream_unavailable,
    unexpected_package_kinds,
)
from app.services.layer3_pass_entry import (
    COHORT_REQUESTED_METHOD_SOURCE,
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    SOURCE_GATE_COHORT_DESC_FREEZE,
)


def _package(package_kind: str, output_package_id: str, *, payload_ref: str, payload_hash: str):
    return SimpleNamespace(
        package_kind=package_kind,
        output_package_id=output_package_id,
        payload_ref=payload_ref,
        payload_hash=payload_hash,
    )


def _approved_review_state() -> dict[str, object]:
    return {
        "review_state": "execution_result_review_approved",
        "operator_decision": "approved",
        "unresolved_trace_count": 0,
        "review_record_ref": "review-ref",
        "pass_type": "single_pass",
        "pass_scope": "quant_single_dataset",
        "selected_method_name": "summary_stats",
        "source_gate": "gate_d",
        "source_dataset_version_ids": ["dataset-v1"],
        "cohort_shape": "single_dataset",
    }


def _reconciliation(summary_json: dict[str, object] | None):
    return SimpleNamespace(summary_json=summary_json)


def test_state_downstream_unavailable_prefers_explicit_non_empty_state() -> None:
    assert state_downstream_unavailable(
        {"downstream_unavailable": ["next", 7]},
        fallback=("fallback",),
    ) == ("next", "7")


def test_state_downstream_unavailable_uses_fallback_for_missing_or_empty_state() -> None:
    assert state_downstream_unavailable({}, fallback=("fallback",)) == ("fallback",)
    assert state_downstream_unavailable(None, fallback=("fallback",)) == ("fallback",)
    assert state_downstream_unavailable({"downstream_unavailable": []}, fallback=("fallback",)) == ("fallback",)


def test_active_downstream_unavailable_returns_first_completed_stage_next_state() -> None:
    assert active_downstream_unavailable(
        transitions=(
            ({"state": "later_done"}, "later_done", {"downstream_unavailable": ["later_next"]}, ("later",)),
            ({"state": "earlier_done"}, "earlier_done", {"downstream_unavailable": ["earlier_next"]}, ("earlier",)),
        ),
        default_state={"downstream_unavailable": ["default_next"]},
        default_fallback=("default",),
    ) == ("later_next",)


def test_active_downstream_unavailable_falls_back_to_default_stage() -> None:
    assert active_downstream_unavailable(
        transitions=(
            (None, "done", {"downstream_unavailable": ["bad"]}, ("bad",)),
            ({"state": "pending"}, "done", {"downstream_unavailable": ["next"]}, ("next_fallback",)),
        ),
        default_state={},
        default_fallback=("default",),
    ) == ("default",)


def test_reconciliation_state_requires_dict_and_matching_schema() -> None:
    state = {"schema_id": "expected.schema", "value": "kept"}

    assert reconciliation_state(
        _reconciliation({"state_key": state}),
        state_key="state_key",
        schema_id="expected.schema",
    ) == state
    assert (
        reconciliation_state(
            _reconciliation({"state_key": {**state, "schema_id": "wrong.schema"}}),
            state_key="state_key",
            schema_id="expected.schema",
        )
        is None
    )
    assert (
        reconciliation_state(
            _reconciliation({"state_key": "not-a-dict"}),
            state_key="state_key",
            schema_id="expected.schema",
        )
        is None
    )
    assert reconciliation_state(None, state_key="state_key", schema_id="expected.schema") is None


def test_package_reconciliation_state_readers_preserve_matching_states() -> None:
    submit_state = {"schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID, "submit_record_ref": "submit-ref"}
    prepare_state = {"schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID, "prepare_record_ref": "prepare-ref"}
    dispatch_state = {"schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID, "aps_bundle_ref": "aps-ref"}
    readiness_state = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "external_export_download_descriptor": {"ref": "download-ref"},
    }
    reconciliation = _reconciliation(
        {
            "package_review_submit": submit_state,
            "handoff_export_prepare": prepare_state,
            "aps_handoff_dispatch": dispatch_state,
            "external_export_download_prepare": readiness_state,
        }
    )

    assert package_review_submit_from_reconciliation(reconciliation) is submit_state
    assert handoff_export_prepare_from_reconciliation(reconciliation) is prepare_state
    assert aps_handoff_dispatch_from_reconciliation(reconciliation) is dispatch_state
    assert external_export_download_prepare_from_reconciliation(reconciliation) is readiness_state


def test_package_reconciliation_state_readers_reject_wrong_schema() -> None:
    reconciliation = _reconciliation(
        {
            "package_review_submit": {"schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID},
            "handoff_export_prepare": {"schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID},
            "aps_handoff_dispatch": {"schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID},
            "external_export_download_prepare": {"schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID},
        }
    )

    assert package_review_submit_from_reconciliation(reconciliation) is None
    assert handoff_export_prepare_from_reconciliation(reconciliation) is None
    assert aps_handoff_dispatch_from_reconciliation(reconciliation) is None
    assert external_export_download_prepare_from_reconciliation(reconciliation) is None


def test_package_review_candidate_projection_preserves_candidate_contract() -> None:
    enabled_projection = package_review_candidate_projection(package_commit_enabled=True)
    disabled_projection = package_review_candidate_projection(package_commit_enabled=False)

    assert [candidate["package_kind"] for candidate in enabled_projection] == list(
        PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS
    )
    assert all(candidate["preview_only"] is True for candidate in enabled_projection)
    assert all(candidate["package_commit_enabled"] is True for candidate in enabled_projection)
    assert all(candidate["package_review_submit_enabled"] is False for candidate in enabled_projection)
    assert all(candidate["handoff_enabled"] is False for candidate in enabled_projection)
    assert all(candidate["package_commit_enabled"] is False for candidate in disabled_projection)
    assert {
        candidate["readiness_reason"]
        for candidate in enabled_projection
    } == {"candidate family is eligible for bounded package construction commit"}
    assert {
        candidate["readiness_reason"]
        for candidate in disabled_projection
    } == {"candidate family is preview-only for associated-cohort review; package construction is deferred"}


def test_package_review_preview_summary_reports_unavailable_without_review_state() -> None:
    summary = package_review_preview_summary(
        None,
        approved_review_state="execution_result_review_approved",
    )

    assert summary["schema_id"] == PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID
    assert summary["available"] is False
    assert summary["state"] is None
    assert summary["package_review_preview_enabled"] is False
    assert summary["package_commit_enabled"] is False
    assert summary["candidate_package_kinds"] == []
    assert summary["source_dataset_version_ids"] == []
    assert summary["downstream_unavailable"] == list(PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE)


def test_package_review_preview_summary_preserves_approved_projection_and_clones_source_ids() -> None:
    review_state = _approved_review_state()
    source_ids = review_state["source_dataset_version_ids"]

    summary = package_review_preview_summary(
        review_state,
        approved_review_state="execution_result_review_approved",
    )

    assert summary["available"] is True
    assert summary["state"] == PACKAGE_REVIEW_PREVIEW_READY_STATE
    assert summary["result_review_state"] == "execution_result_review_approved"
    assert summary["result_review_record_ref"] == "review-ref"
    assert summary["candidate_package_kinds"] == package_review_candidate_projection(package_commit_enabled=True)
    assert summary["downstream_unavailable"] == list(PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE)
    assert summary["source_dataset_version_ids"] == ["dataset-v1"]
    assert summary["source_dataset_version_ids"] is not source_ids


def test_package_review_preview_summary_uses_cohort_downstream_for_admitted_associated_cohort() -> None:
    review_state = {
        **_approved_review_state(),
        "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
        "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
        "selected_method_name": "descriptive_summary",
        "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
        "source_dataset_version_ids": ["dataset-v1", "dataset-v2"],
        "cohort_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
        "requested_method_name": "descriptive_summary",
        "requested_method_source": COHORT_REQUESTED_METHOD_SOURCE,
    }

    summary = package_review_preview_summary(
        review_state,
        approved_review_state="execution_result_review_approved",
    )

    assert review_state_is_admitted_associated_cohort(review_state) is True
    assert summary["available"] is True
    assert summary["downstream_unavailable"] == list(COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE)


def test_review_state_is_admitted_associated_cohort_requires_exact_source_authority() -> None:
    review_state = {
        **_approved_review_state(),
        "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
        "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
        "selected_method_name": "descriptive_summary",
        "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
        "source_dataset_version_ids": ["dataset-v1"],
        "cohort_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
        "requested_method_name": "descriptive_summary",
    }

    assert review_state_is_admitted_associated_cohort(review_state) is False


def test_package_source_shape_prefers_cohort_shape_then_dataset_version() -> None:
    assert (
        package_source_shape(
            output_metadata_summary={"cohort_shape": "aligned_wide_table", "dataset_version_id": "ignored"},
            pass_summary={"cohort_shape": "pass_shape", "dataset_version_id": "pass-dataset"},
        )
        == "aligned_wide_table"
    )
    assert (
        package_source_shape(
            output_metadata_summary={},
            pass_summary={"cohort_shape": "pass_shape", "dataset_version_id": "pass-dataset"},
        )
        == "pass_shape"
    )
    assert (
        package_source_shape(
            output_metadata_summary={"dataset_version_id": "dataset-v1"},
            pass_summary={},
        )
        == "dataset_version"
    )
    assert package_source_shape(output_metadata_summary={}, pass_summary={}) is None


def test_package_source_dataset_version_ids_prefers_list_then_dataset_version() -> None:
    assert package_source_dataset_version_ids(
        output_metadata_summary={"source_dataset_version_ids": ["dataset-v2", "", None, 7]},
        pass_summary={"source_dataset_version_ids_json": ["ignored"]},
    ) == ["dataset-v2", "7"]
    assert package_source_dataset_version_ids(
        output_metadata_summary={},
        pass_summary={"source_dataset_version_ids_json": ["pass-v1", "pass-v2"]},
    ) == ["pass-v1", "pass-v2"]
    assert package_source_dataset_version_ids(
        output_metadata_summary={"dataset_version_id": "dataset-v1"},
        pass_summary={"dataset_version_id": "pass-dataset"},
    ) == ["dataset-v1"]
    assert package_source_dataset_version_ids(
        output_metadata_summary={},
        pass_summary={"dataset_version_id": "pass-dataset"},
    ) == ["pass-dataset"]
    assert package_source_dataset_version_ids(output_metadata_summary={}, pass_summary={}) == []


def test_package_review_preview_hash_uses_stable_identity_basis() -> None:
    output_metadata_summary = {
        "output_payload_ref": "payload-ref",
        "artifact_refs": ["artifact-b", "artifact-a"],
        "artifact_types": ["csv", "json"],
    }
    expected_basis = {
        "schema_id": "layer3.package_review_preview_hash.v1",
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "preview_id": "preview-1",
        "preview_hash": "preview-hash",
        "analysis_run_id": "analysis-1",
        "result_review_record_ref": "review-ref",
        "output_payload_ref": "payload-ref",
        "artifact_refs": ["artifact-b", "artifact-a"],
        "artifact_types": ["csv", "json"],
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
    }
    expected_digest = hashlib.sha256(
        json.dumps(expected_basis, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]

    assert (
        package_review_preview_hash(
            session_id="session-1",
            analysis_plan_id="plan-1",
            pass_run_id="pass-1",
            preview_id="preview-1",
            preview_hash="preview-hash",
            analysis_run_id="analysis-1",
            result_review_record_ref="review-ref",
            output_metadata_summary=output_metadata_summary,
        )
        == f"l3-package-preview-{expected_digest}"
    )


def test_package_owner_compatibility_reports_missing_gate_d_inputs_for_default_preview() -> None:
    compatibility = package_owner_compatibility(
        session=SimpleNamespace(summary_json={}),
        pass_run=SimpleNamespace(
            summary_json={"pass_scope": "pass-scope", "source_gate": "pass-source-gate"},
            status="completed",
            pass_type="single_pass",
        ),
        output_metadata_summary={"readable": True},
        review_state={"review_state": "execution_result_review_approved"},
        approved_review_state="execution_result_review_approved",
    )

    assert compatibility["schema_id"] == "layer3.package_owner_compatibility.v1"
    assert compatibility["materialize_package_entry_callable"] is False
    assert compatibility["workbench_package_commit_callable"] is False
    assert compatibility["construction_compatible_with_current_workbench_state"] is False
    assert compatibility["missing_owner_service_inputs"] == ["pass_entry", "phase1a_loading_closure"]
    assert compatibility["pass_scope"] == "pass-scope"
    assert compatibility["source_gate"] == "pass-source-gate"
    assert compatibility["status"] == "construction_preconditions_missing"


def test_package_owner_compatibility_reports_ready_default_preview_without_calling_owner_service() -> None:
    compatibility = package_owner_compatibility(
        session=SimpleNamespace(
            summary_json={
                "phase1a_loading_closure": {"closed": True},
                "pass_entry": {"pass_entry_id": "entry-1"},
            }
        ),
        pass_run=SimpleNamespace(
            summary_json={
                "pass_scope": "pass-scope",
                "source_gate": "pass-source-gate",
                "source_preview_id": "preview-1",
                "source_preview_hash": "hash-1",
            },
            status="completed",
            pass_type="single_pass",
        ),
        output_metadata_summary={
            "readable": True,
            "pass_scope": "metadata-scope",
            "source_gate": "metadata-source-gate",
        },
        review_state={"review_state": "execution_result_review_approved"},
        approved_review_state="execution_result_review_approved",
    )

    assert compatibility["workbench_package_commit_callable"] is True
    assert compatibility["construction_compatible_with_current_workbench_state"] is True
    assert compatibility["missing_owner_service_inputs"] == []
    assert compatibility["pass_scope"] == "metadata-scope"
    assert compatibility["source_gate"] == "metadata-source-gate"
    assert compatibility["source_preview_id"] == "preview-1"
    assert compatibility["source_preview_hash"] == "hash-1"
    assert compatibility["status"] == "construction_preconditions_satisfied_but_call_deferred"
    assert compatibility["reason"] == (
        "Current state can be assessed against the owner service, but this endpoint remains read-only."
    )


def test_package_owner_compatibility_associated_cohort_preview_skips_gate_d_inputs() -> None:
    compatibility = package_owner_compatibility(
        session=SimpleNamespace(summary_json={}),
        pass_run=SimpleNamespace(summary_json={}, status="completed", pass_type=PASS_TYPE_ASSOCIATED_COHORT),
        output_metadata_summary={"readable": True},
        review_state={"review_state": "execution_result_review_approved"},
        approved_review_state="execution_result_review_approved",
        associated_cohort_preview=True,
    )

    assert compatibility["workbench_package_commit_callable"] is True
    assert compatibility["missing_owner_service_inputs"] == []
    assert compatibility["status"] == "associated_cohort_construction_preconditions_satisfied"
    assert compatibility["reason"] == (
        "Associated-cohort package construction is admitted for this exact approved descriptive cohort review."
    )


def test_legacy_package_review_submit_record_ref_preserves_legacy_identity_basis() -> None:
    submit_basis = {
        "schema_id": "layer3.package_review_submit.v1",
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "preview_id": "preview-1",
        "preview_hash": "preview-hash",
        "analysis_run_id": "analysis-1",
        "result_review_record_ref": "review-ref",
        "package_review_preview_hash": "package-preview-hash",
        "reconciliation_record_id": "reconciliation-1",
        "output_package_ids": ["pkg-1", "pkg-2"],
        "package_kinds": ["canonical_internal", "user_facing"],
        "payload_hashes": ["hash-1", "hash-2"],
        "operator_decision": "approved",
        "decision_notes": "ready",
        "pass_type": "single_pass",
        "source_gate": "new-provenance-field",
    }
    legacy_basis = {
        field: submit_basis[field]
        for field in PACKAGE_REVIEW_SUBMIT_LEGACY_AUTHORITY_FIELDS
    }
    expected_digest = hashlib.sha256(
        json.dumps(legacy_basis, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]

    assert legacy_package_review_submit_record_ref(
        submit_basis=submit_basis,
        existing_submit={"authority_basis": {"schema_id": "legacy"}},
    ) == f"l3-package-review-submit-{expected_digest}"


def test_legacy_package_review_submit_record_ref_rejects_missing_or_provenance_authority() -> None:
    submit_basis = {field: field for field in PACKAGE_REVIEW_SUBMIT_LEGACY_AUTHORITY_FIELDS}

    assert legacy_package_review_submit_record_ref(
        submit_basis=submit_basis,
        existing_submit={},
    ) is None
    assert legacy_package_review_submit_record_ref(
        submit_basis=submit_basis,
        existing_submit={"authority_basis": {"source_gate": "cohort"}},
    ) is None


def test_cohort_package_construction_source_requires_exact_source_gate() -> None:
    assert cohort_package_construction_source("88_COHORT_PACKAGE_CONSTRUCTION_FREEZE") is True
    assert cohort_package_construction_source("workbench_package_construction_freeze") is False
    assert cohort_package_construction_source(None) is False


def test_package_review_submit_downstream_unavailable_preserves_state_priority() -> None:
    assert package_review_submit_downstream_unavailable(
        "package_review_approved",
        associated_cohort_submit=True,
    ) == COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    assert package_review_submit_downstream_unavailable(
        "package_review_approved",
    ) == HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE
    assert package_review_submit_downstream_unavailable(
        "package_review_rejected",
    ) == PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE


def test_packages_in_kind_order_returns_canonical_order() -> None:
    packages = [
        _package("user", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
    ]

    ordered = packages_in_kind_order(packages, package_kinds=("internal", "review", "user"))

    assert [package.output_package_id for package in ordered] == ["pkg-internal", "pkg-review", "pkg-user"]


def test_packages_with_kinds_filters_without_mutating_order() -> None:
    packages = [
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("debug", "pkg-debug", payload_ref="ref-debug", payload_hash="hash-debug"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
    ]

    filtered = packages_with_kinds(packages, package_kinds=("review", "internal"))

    assert [package.output_package_id for package in filtered] == ["pkg-internal", "pkg-review"]


def test_review_source_packages_filters_to_package_review_candidate_kinds() -> None:
    packages = [
        _package("canonical_internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("debug", "pkg-debug", payload_ref="ref-debug", payload_hash="hash-debug"),
        _package("review_facing", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("user_facing", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
    ]

    filtered = review_source_packages(packages)

    assert [package.output_package_id for package in filtered] == ["pkg-internal", "pkg-review", "pkg-user"]


def test_packages_in_review_order_uses_package_review_candidate_order() -> None:
    packages = [
        _package("user_facing", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
        _package("review_facing", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("canonical_internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
    ]

    ordered = packages_in_review_order(packages)

    assert [package.package_kind for package in ordered] == list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    assert [package.output_package_id for package in ordered] == ["pkg-internal", "pkg-user", "pkg-review"]


def test_dispatched_package_id_requires_dispatched_state_and_expected_kind() -> None:
    dispatch_state = {
        "aps_handoff_state": "aps_handoff_dispatched",
        "aps_output_package_kind": "aps_bundle",
        "aps_output_package_id": "pkg-aps",
    }

    assert (
        dispatched_package_id(
            dispatch_state,
            dispatched_state="aps_handoff_dispatched",
            expected_package_kind="aps_bundle",
        )
        == "pkg-aps"
    )
    assert (
        dispatched_package_id(
            {**dispatch_state, "aps_handoff_state": "aps_handoff_ready"},
            dispatched_state="aps_handoff_dispatched",
            expected_package_kind="aps_bundle",
        )
        is None
    )
    assert (
        dispatched_package_id(
            {**dispatch_state, "aps_output_package_kind": "unexpected"},
            dispatched_state="aps_handoff_dispatched",
            expected_package_kind="aps_bundle",
        )
        is None
    )


def test_unexpected_package_kinds_allows_source_kinds_and_exact_dispatched_aps_package() -> None:
    packages = [
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("aps_bundle", "pkg-aps-good", payload_ref="ref-aps", payload_hash="hash-aps"),
        _package("aps_bundle", "pkg-aps-extra", payload_ref="ref-aps-extra", payload_hash="hash-aps-extra"),
        _package("debug", "pkg-debug", payload_ref="ref-debug", payload_hash="hash-debug"),
    ]

    unexpected = unexpected_package_kinds(
        packages,
        source_kinds=("internal", "review"),
        aps_handoff_dispatch_state={
            "aps_handoff_state": "aps_handoff_dispatched",
            "aps_output_package_kind": "aps_bundle",
            "aps_output_package_id": "pkg-aps-good",
        },
        aps_dispatched_state="aps_handoff_dispatched",
        aps_package_kind="aps_bundle",
    )

    assert unexpected == ["aps_bundle", "debug"]


def test_canonical_payload_values_accepts_list_and_dict_identity_forms() -> None:
    packages = [
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("user", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
    ]
    package_kinds = ("internal", "review", "user")

    assert canonical_payload_values(
        values=["ref-user", "ref-internal", "ref-review"],
        packages=packages,
        package_kinds=package_kinds,
        package_attr="payload_ref",
    ) == ["ref-internal", "ref-review", "ref-user"]
    assert canonical_payload_values(
        values={"internal": "hash-internal", "review": "hash-review", "user": "hash-user"},
        packages=packages,
        package_kinds=package_kinds,
        package_attr="payload_hash",
    ) == ["hash-internal", "hash-review", "hash-user"]
    assert canonical_payload_values(
        values={"pkg-internal": "hash-internal", "pkg-review": "hash-review", "pkg-user": "hash-user"},
        packages=packages,
        package_kinds=package_kinds,
        package_attr="payload_hash",
    ) == ["hash-internal", "hash-review", "hash-user"]
    assert (
        canonical_payload_values(
            values={"internal": "hash-internal", "review": "wrong", "user": "hash-user"},
            packages=packages,
            package_kinds=package_kinds,
            package_attr="payload_hash",
        )
        is None
    )


def test_canonical_payload_hashes_and_refs_use_review_package_identity_forms() -> None:
    packages = [
        _package("canonical_internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review_facing", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("user_facing", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
    ]

    assert canonical_payload_hashes(
        payload_hashes={
            "canonical_internal": "hash-internal",
            "user_facing": "hash-user",
            "review_facing": "hash-review",
        },
        packages=packages,
    ) == ["hash-internal", "hash-user", "hash-review"]
    assert canonical_payload_refs(
        payload_refs={
            "pkg-internal": "ref-internal",
            "pkg-user": "ref-user",
            "pkg-review": "ref-review",
        },
        packages=packages,
    ) == ["ref-internal", "ref-user", "ref-review"]
    assert (
        canonical_payload_hashes(
            payload_hashes={
                "canonical_internal": "hash-internal",
                "user_facing": "wrong",
                "review_facing": "hash-review",
            },
            packages=packages,
        )
        is None
    )
