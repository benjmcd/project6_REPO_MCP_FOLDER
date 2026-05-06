from types import SimpleNamespace

from app.services.layer3_workbench_package_state import (
    COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
    PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_PREVIEW_READY_STATE,
    PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID,
    active_downstream_unavailable,
    canonical_payload_hashes,
    canonical_payload_refs,
    canonical_payload_values,
    dispatched_package_id,
    package_review_candidate_projection,
    package_review_preview_summary,
    packages_in_review_order,
    packages_in_kind_order,
    packages_with_kinds,
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
