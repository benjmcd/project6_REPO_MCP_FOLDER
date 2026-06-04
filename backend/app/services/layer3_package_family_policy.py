from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)


PACKAGE_FAMILY_DATASET_VERSION = "dataset_version"
PACKAGE_FAMILY_ASSOCIATED_COHORT = "associated_cohort"
PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT = "qualitative_aps_document"
PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE = "source_intake_qualitative"
PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT = "mixed_dataset_document"

PACKAGE_FAMILY_ACTION_PREVIEW = "preview"
PACKAGE_FAMILY_ACTION_COMMIT = "commit"
PACKAGE_FAMILY_ACTION_SUBMIT = "submit"
PACKAGE_FAMILY_ACTION_HANDOFF = "handoff"

PACKAGE_FAMILY_STAGE_PREVIEW = "preview"
PACKAGE_FAMILY_STAGE_CONSTRUCTION = "construction"
PACKAGE_FAMILY_STAGE_SUBMIT = "submit"
PACKAGE_FAMILY_STAGE_HANDOFF = "handoff"

PACKAGE_REVIEW_CANDIDATE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

DEFAULT_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
)
COHORT_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector",
)
EXTENDED_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
DEFAULT_SUBMIT_DOWNSTREAM_UNAVAILABLE = ("handoff", "export")
COHORT_SUBMIT_DOWNSTREAM_UNAVAILABLE = (
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector",
)
EXTENDED_SUBMIT_DOWNSTREAM_UNAVAILABLE = (
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE = (
    "aps_handoff",
    "external_export",
    "downstream_dispatch",
)
MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM = (
    "package_review_preview",
    "package_construction",
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
MIXED_DATASET_DOCUMENT_PREVIEW_DOWNSTREAM = (
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
MIXED_DATASET_DOCUMENT_SUBMIT_DOWNSTREAM = (
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
MIXED_DATASET_DOCUMENT_HANDOFF_DOWNSTREAM = (
    "aps_handoff",
    "external_export",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)


@dataclass(frozen=True)
class PackageFamilyPolicy:
    package_family: str
    known_family: bool
    contract_schema_id: str | None
    preview_admitted: bool
    commit_admitted: bool
    submit_admitted: bool
    handoff_admitted: bool
    candidate_package_kinds: tuple[str, ...]
    preview_downstream_unavailable: tuple[str, ...]
    construction_downstream_unavailable: tuple[str, ...]
    submit_downstream_unavailable: tuple[str, ...]
    handoff_downstream_unavailable: tuple[str, ...]
    admission_boundary: str
    reason: str

    def action_admitted(self, action: str) -> bool:
        admissions = {
            PACKAGE_FAMILY_ACTION_PREVIEW: self.preview_admitted,
            PACKAGE_FAMILY_ACTION_COMMIT: self.commit_admitted,
            PACKAGE_FAMILY_ACTION_SUBMIT: self.submit_admitted,
            PACKAGE_FAMILY_ACTION_HANDOFF: self.handoff_admitted,
        }
        return bool(admissions.get(str(action or "").strip(), False))

    def downstream_unavailable(self, stage: str) -> tuple[str, ...]:
        stages = {
            PACKAGE_FAMILY_STAGE_PREVIEW: self.preview_downstream_unavailable,
            PACKAGE_FAMILY_STAGE_CONSTRUCTION: self.construction_downstream_unavailable,
            PACKAGE_FAMILY_STAGE_SUBMIT: self.submit_downstream_unavailable,
            PACKAGE_FAMILY_STAGE_HANDOFF: self.handoff_downstream_unavailable,
        }
        return stages.get(str(stage or "").strip(), MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM)

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "layer3.package_family_policy.v1",
            "package_family": self.package_family,
            "known_family": self.known_family,
            "contract_schema_id": self.contract_schema_id,
            "admitted_actions": {
                PACKAGE_FAMILY_ACTION_PREVIEW: self.preview_admitted,
                PACKAGE_FAMILY_ACTION_COMMIT: self.commit_admitted,
                PACKAGE_FAMILY_ACTION_SUBMIT: self.submit_admitted,
                PACKAGE_FAMILY_ACTION_HANDOFF: self.handoff_admitted,
            },
            "candidate_package_kinds": list(self.candidate_package_kinds),
            "downstream_unavailable": {
                PACKAGE_FAMILY_STAGE_PREVIEW: list(self.preview_downstream_unavailable),
                PACKAGE_FAMILY_STAGE_CONSTRUCTION: list(self.construction_downstream_unavailable),
                PACKAGE_FAMILY_STAGE_SUBMIT: list(self.submit_downstream_unavailable),
                PACKAGE_FAMILY_STAGE_HANDOFF: list(self.handoff_downstream_unavailable),
            },
            "admission_boundary": self.admission_boundary,
            "reason": self.reason,
        }


def _policy(
    package_family: str,
    *,
    contract_schema_id: str | None,
    preview_admitted: bool,
    commit_admitted: bool,
    submit_admitted: bool,
    handoff_admitted: bool,
    candidate_package_kinds: tuple[str, ...],
    preview_downstream_unavailable: tuple[str, ...],
    construction_downstream_unavailable: tuple[str, ...],
    submit_downstream_unavailable: tuple[str, ...],
    handoff_downstream_unavailable: tuple[str, ...],
    admission_boundary: str,
    reason: str,
) -> PackageFamilyPolicy:
    return PackageFamilyPolicy(
        package_family=package_family,
        known_family=True,
        contract_schema_id=contract_schema_id,
        preview_admitted=preview_admitted,
        commit_admitted=commit_admitted,
        submit_admitted=submit_admitted,
        handoff_admitted=handoff_admitted,
        candidate_package_kinds=candidate_package_kinds,
        preview_downstream_unavailable=preview_downstream_unavailable,
        construction_downstream_unavailable=construction_downstream_unavailable,
        submit_downstream_unavailable=submit_downstream_unavailable,
        handoff_downstream_unavailable=handoff_downstream_unavailable,
        admission_boundary=admission_boundary,
        reason=reason,
    )


PACKAGE_FAMILY_POLICIES: dict[str, PackageFamilyPolicy] = {
    PACKAGE_FAMILY_DATASET_VERSION: _policy(
        PACKAGE_FAMILY_DATASET_VERSION,
        contract_schema_id=None,
        preview_admitted=True,
        commit_admitted=True,
        submit_admitted=True,
        handoff_admitted=True,
        candidate_package_kinds=PACKAGE_REVIEW_CANDIDATE_KINDS,
        preview_downstream_unavailable=DEFAULT_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        construction_downstream_unavailable=DEFAULT_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        submit_downstream_unavailable=DEFAULT_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        handoff_downstream_unavailable=HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
        admission_boundary="existing_dataset_version_package_flow",
        reason="Existing dataset-version package behavior remains governed by the current workbench package path.",
    ),
    PACKAGE_FAMILY_ASSOCIATED_COHORT: _policy(
        PACKAGE_FAMILY_ASSOCIATED_COHORT,
        contract_schema_id=None,
        preview_admitted=True,
        commit_admitted=True,
        submit_admitted=True,
        handoff_admitted=True,
        candidate_package_kinds=PACKAGE_REVIEW_CANDIDATE_KINDS,
        preview_downstream_unavailable=COHORT_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        construction_downstream_unavailable=COHORT_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        submit_downstream_unavailable=COHORT_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        handoff_downstream_unavailable=HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
        admission_boundary="existing_associated_cohort_package_flow",
        reason="Associated-cohort package behavior keeps its current downstream guardrails.",
    ),
    PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT: _policy(
        PACKAGE_FAMILY_QUALITATIVE_APS_DOCUMENT,
        contract_schema_id=None,
        preview_admitted=True,
        commit_admitted=True,
        submit_admitted=True,
        handoff_admitted=True,
        candidate_package_kinds=PACKAGE_REVIEW_CANDIDATE_KINDS,
        preview_downstream_unavailable=EXTENDED_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        construction_downstream_unavailable=EXTENDED_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        submit_downstream_unavailable=EXTENDED_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        handoff_downstream_unavailable=HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
        admission_boundary="existing_qualitative_aps_document_package_flow",
        reason="Qualitative APS document package behavior keeps provider and connector downstream blocks.",
    ),
    PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE: _policy(
        PACKAGE_FAMILY_SOURCE_INTAKE_QUALITATIVE,
        contract_schema_id=None,
        preview_admitted=True,
        commit_admitted=True,
        submit_admitted=True,
        handoff_admitted=True,
        candidate_package_kinds=PACKAGE_REVIEW_CANDIDATE_KINDS,
        preview_downstream_unavailable=EXTENDED_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        construction_downstream_unavailable=EXTENDED_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        submit_downstream_unavailable=EXTENDED_SUBMIT_DOWNSTREAM_UNAVAILABLE,
        handoff_downstream_unavailable=HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
        admission_boundary="existing_source_intake_qualitative_package_flow",
        reason="Source-intake package behavior keeps its existing construction-stage downstream blocks.",
    ),
    PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT: _policy(
        PACKAGE_FAMILY_MIXED_DATASET_DOCUMENT,
        contract_schema_id="layer3.mixed_source_package_contract.v1",
        preview_admitted=True,
        commit_admitted=True,
        submit_admitted=True,
        handoff_admitted=True,
        candidate_package_kinds=PACKAGE_REVIEW_CANDIDATE_KINDS,
        preview_downstream_unavailable=MIXED_DATASET_DOCUMENT_PREVIEW_DOWNSTREAM,
        construction_downstream_unavailable=MIXED_DATASET_DOCUMENT_SUBMIT_DOWNSTREAM,
        submit_downstream_unavailable=MIXED_DATASET_DOCUMENT_SUBMIT_DOWNSTREAM,
        handoff_downstream_unavailable=MIXED_DATASET_DOCUMENT_HANDOFF_DOWNSTREAM,
        admission_boundary="mixed_handoff_export_prepare_runtime_admitted",
        reason=(
            "Mixed-source material authority admits package-review preview and "
            "construction commit, package-review submit, and reference-only handoff/export prepare; "
            "APS handoff, external export/download, connector dispatch, and provider URL behavior remain blocked."
        ),
    ),
}


def blocked_package_family_policy(package_family: str) -> PackageFamilyPolicy:
    normalized = str(package_family or "").strip() or "unknown"
    return PackageFamilyPolicy(
        package_family=normalized,
        known_family=False,
        contract_schema_id=None,
        preview_admitted=False,
        commit_admitted=False,
        submit_admitted=False,
        handoff_admitted=False,
        candidate_package_kinds=(),
        preview_downstream_unavailable=MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM,
        construction_downstream_unavailable=MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM,
        submit_downstream_unavailable=MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM,
        handoff_downstream_unavailable=MIXED_DATASET_DOCUMENT_BLOCKED_DOWNSTREAM,
        admission_boundary="unknown_package_family_fail_closed",
        reason="Unknown package families are not admitted by the Layer 3 package-family policy registry.",
    )


def package_family_policy(package_family: str) -> PackageFamilyPolicy:
    normalized = str(package_family or "").strip()
    return PACKAGE_FAMILY_POLICIES.get(normalized, blocked_package_family_policy(normalized))


def package_family_action_admitted(package_family: str, action: str) -> bool:
    return package_family_policy(package_family).action_admitted(action)


def known_package_families() -> tuple[str, ...]:
    return tuple(PACKAGE_FAMILY_POLICIES)
