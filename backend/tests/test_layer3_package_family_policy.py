from app.services.layer3_package_family_policy import (
    MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM,
    MIXED_DATASET_DOCUMENT_PREVIEW_DOWNSTREAM,
    PACKAGE_FAMILY_ACTION_COMMIT,
    PACKAGE_FAMILY_ACTION_HANDOFF,
    PACKAGE_FAMILY_ACTION_PREVIEW,
    PACKAGE_FAMILY_ACTION_SUBMIT,
    PACKAGE_FAMILY_ASSOCIATED_COHORT,
    PACKAGE_FAMILY_DATASET_VERSION,
    PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT,
    PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT,
    PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE,
    PACKAGE_REVIEW_CANDIDATE_KINDS,
    known_package_families,
    package_family_action_admitted,
    package_family_policy,
)
from app.services.layer3_workbench_package_state import (
    COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
    PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    QUAL_APS_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    SOURCE_INTAKE_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    SOURCE_INTAKE_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    package_family_for_review_state,
    package_review_candidate_projection,
    package_review_preview_summary,
)


def _approved_review_state(**extra: object) -> dict[str, object]:
    return {
        "review_state": "execution_result_review_approved",
        "operator_decision": "approved",
        "unresolved_trace_count": 0,
        "review_record_ref": "review-ref",
        **extra,
    }


def test_package_family_registry_preserves_current_family_constants() -> None:
    dataset_policy = package_family_policy(PACKAGE_FAMILY_DATASET_VERSION)
    cohort_policy = package_family_policy(PACKAGE_FAMILY_ASSOCIATED_COHORT)
    qual_aps_policy = package_family_policy(PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT)
    source_intake_policy = package_family_policy(PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE)

    assert dataset_policy.candidate_package_kinds == PACKAGE_REVIEW_CANDIDATE_KINDS
    assert PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS == PACKAGE_REVIEW_CANDIDATE_KINDS
    assert dataset_policy.preview_downstream_unavailable == PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
    assert cohort_policy.preview_downstream_unavailable == COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
    assert qual_aps_policy.preview_downstream_unavailable == QUAL_APS_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
    assert (
        source_intake_policy.preview_downstream_unavailable
        == SOURCE_INTAKE_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
    )
    assert dataset_policy.submit_downstream_unavailable == PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    assert cohort_policy.submit_downstream_unavailable == COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    assert qual_aps_policy.submit_downstream_unavailable == QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    assert (
        source_intake_policy.submit_downstream_unavailable
        == SOURCE_INTAKE_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    )


def test_existing_package_families_keep_current_action_admissions() -> None:
    current_families = {
        PACKAGE_FAMILY_DATASET_VERSION,
        PACKAGE_FAMILY_ASSOCIATED_COHORT,
        PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT,
        PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE,
    }

    assert current_families.issubset(set(known_package_families()))
    for package_family in current_families:
        policy = package_family_policy(package_family)
        assert policy.known_family is True
        assert policy.preview_admitted is True
        assert policy.commit_admitted is True
        assert policy.submit_admitted is True
        assert policy.handoff_admitted is True
        assert policy.candidate_package_kinds == PACKAGE_REVIEW_CANDIDATE_KINDS


def test_mixed_dataset_document_policy_admits_read_only_preview_only() -> None:
    policy = package_family_policy(PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT)

    assert policy.known_family is True
    assert policy.contract_schema_id == "layer3.mixed_source_package_contract.v1"
    assert policy.preview_admitted is True
    assert policy.commit_admitted is False
    assert policy.submit_admitted is False
    assert policy.handoff_admitted is False
    assert policy.candidate_package_kinds == ()
    assert policy.preview_downstream_unavailable == MIXED_DATASET_DOCUMENT_PREVIEW_DOWNSTREAM
    assert policy.construction_downstream_unavailable == MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM
    assert policy.submit_downstream_unavailable == MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM
    assert policy.handoff_downstream_unavailable == MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM
    assert package_family_action_admitted(PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT, PACKAGE_FAMILY_ACTION_PREVIEW) is True
    assert package_family_action_admitted(PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT, PACKAGE_FAMILY_ACTION_COMMIT) is False
    assert package_family_action_admitted(PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT, PACKAGE_FAMILY_ACTION_SUBMIT) is False
    assert package_family_action_admitted(PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT, PACKAGE_FAMILY_ACTION_HANDOFF) is False


def test_unknown_package_family_fails_closed() -> None:
    policy = package_family_policy("future_unregistered_family")

    assert policy.known_family is False
    assert policy.action_admitted(PACKAGE_FAMILY_ACTION_PREVIEW) is False
    assert policy.action_admitted("unknown_action") is False
    assert policy.downstream_unavailable("unknown_stage") == MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM
    assert policy.public_dict()["admitted_actions"] == {
        PACKAGE_FAMILY_ACTION_PREVIEW: False,
        PACKAGE_FAMILY_ACTION_COMMIT: False,
        PACKAGE_FAMILY_ACTION_SUBMIT: False,
        PACKAGE_FAMILY_ACTION_HANDOFF: False,
    }


def test_review_state_family_classification_matches_current_authority_markers() -> None:
    assert package_family_for_review_state(None) == PACKAGE_FAMILY_DATASET_VERSION
    assert (
        package_family_for_review_state(
            _approved_review_state(engine_family="qualitative_aps_document")
        )
        == PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT
    )
    assert (
        package_family_for_review_state(
            _approved_review_state(engine_family="source_intake_qualitative_preview")
        )
        == PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE
    )
    assert (
        package_family_for_review_state(
            _approved_review_state(package_family=PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT)
        )
        == PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT
    )


def test_mixed_family_selected_pass_preview_summary_requires_material_authority() -> None:
    summary = package_review_preview_summary(
        _approved_review_state(package_family=PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT),
        approved_review_state="execution_result_review_approved",
    )

    assert summary["available"] is False
    assert summary["state"] is None
    assert summary["package_review_preview_enabled"] is False
    assert summary["package_commit_enabled"] is False
    assert summary["candidate_package_kinds"] == []
    assert summary["downstream_unavailable"] == list(MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM)
    assert package_review_candidate_projection(
        package_commit_enabled=True,
        package_family=PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT,
    ) == []
