from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.models import (
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    VariableDefinition,
    uuid_str,
)
from app.services.layer3_pass_entry import (
    COHORT_REQUESTED_METHOD_SOURCE,
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
    PASS_STATUS_RUNNING,
    PASS_STATUS_SELECTED_NOT_STARTED,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    PASS_TYPE_SINGLE_ITEM,
    PLAN_STATUS_APPROVED,
    SOURCE_GATE_COHORT_DESC_FREEZE,
    Layer3PassEntryError,
    approve_pass_entry_plan,
    execute_selected_pass_run,
    preview_pass_entry,
)
from app.services.layer3_execution_state import (
    ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
    EXECUTION_PASS_COMPLETED_STATE,
    EXECUTION_PASS_FAILED_STATE,
    EXECUTION_PASS_RUNNING_STATE,
    EXECUTION_SELECTION_STATE,
    EXECUTION_SELECTION_STATE_SCHEMA_ID,
    analysis_execution_start_from_pass_run as _analysis_execution_start_from_pass_run,
    execution_selection_from_session as _execution_selection_from_session,
    execution_selection_pass_runs as _execution_selection_pass_runs,
    execution_state_for_pass_runs as _execution_state_for_pass_runs,
    pass_run_analysis_run_id as _pass_run_analysis_run_id,
    pass_run_execution_started as _pass_run_execution_started,
)
from app.services.layer3_execution_errors import analysis_execution_start_workbench_error
from app.services.layer3_execution_output import output_metadata_summary as _output_metadata_summary
from app.services.layer3_pdf_location import (
    pdf_location_projection_for_session as _pdf_location_projection_for_session,
)
from app.services.layer3_execution_review import (
    EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE,
    EXECUTION_RESULT_REVIEW_SCHEMA_ID,
    EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
    execution_result_review_response as _execution_result_review_response,
    execution_result_review_from_pass_run as _execution_result_review_from_pass_run,
    normalize_result_review_items as _normalize_result_review_items,
    result_review_trace_summary as _result_review_trace_summary,
)
from app.services.layer3_execution_selection import (
    EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE,
    EXECUTION_SELECTION_SCHEMA_ID,
    execution_selection_response as _execution_selection_response,
    execution_selection_summary as _execution_selection_summary,
)
from app.services.layer3_execution_start import (
    ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE,
    ANALYSIS_EXECUTION_START_SCHEMA_ID,
    analysis_execution_start_response as _analysis_execution_start_response,
)
from app.services.layer3_execution_status import (
    EXECUTION_RESULT_STATUS_AVAILABLE_STATE,
    EXECUTION_RESULT_STATUS_BLOCKED_STATE,
    EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE,
    EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE,
    EXECUTION_RESULT_STATUS_SCHEMA_ID,
    execution_result_status_response as _execution_result_status_response,
)
from app.services.layer3_plan_errors import plan_approval_workbench_error, plan_preview_workbench_error
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
    SOURCE_WORKBENCH_PACKAGE_CONSTRUCTION_FREEZE,
    SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
    Layer3PackageEntryError,
    materialize_workbench_package_commit,
)
from app.services.layer3_package_submit_response import (
    COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
    PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
    QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
    package_review_submit_response as _package_review_submit_response,
)
from app.services.layer3_handoff_export_response import (
    COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
    HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
    handoff_export_prepare_response as _handoff_export_prepare_response,
)
from app.services.layer3_external_export_response import (
    EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
    EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE,
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
    associated_cohort_delivery_ui_state as _associated_cohort_delivery_ui_state,
    associated_cohort_external_export_download as _is_associated_cohort_external_export_download,
    aps_bundle_identity_for_external_export_download as _aps_bundle_identity_for_external_export_download,
    cohort_readiness_identity as _cohort_readiness_identity,
    external_export_download_delivery_response as _external_export_download_delivery_response,
    external_export_download_prepare_payload_for_delivery as _external_export_download_prepare_payload_for_delivery,
    external_export_download_prepare_response as _external_export_download_prepare_response,
    external_export_download_prepare_summary as _external_export_download_prepare_summary,
    qualitative_aps_external_export_download_admitted as _qualitative_aps_external_export_download_admitted,
    qualitative_aps_external_export_download_deferred as _qualitative_aps_external_export_download_deferred,
    safe_download_token as _safe_download_token,
)
from app.services.layer3_gate_b_state import (
    GATE_B_DECISIONS,
    GATE_B_IDEMPOTENCY_CONTEXT_KEY,
    GATE_B_IDEMPOTENCY_STATUS_COMMITTED,
    candidate_decision_manifest as build_candidate_decision_manifest,
    claim_gate_b_idempotency,
    complete_gate_b_idempotency_claim,
    find_gate_b_idempotency_claim,
    find_gate_b_idempotency_session,
    gate_b_counts,
    gate_b_decision_manifest_id as build_gate_b_decision_manifest_id,
    gate_b_idempotency_claim_matches,
    gate_b_idempotency_from_session,
    gate_b_idempotency_record,
    gate_b_summary_from_session,
    material_candidate_basis_from_decision as gate_b_material_candidate_basis_from_decision,
    material_candidate_basis_from_preview as gate_b_material_candidate_basis_from_preview,
    material_preview_hash as compute_material_preview_hash,
)
from app.services.layer3_plan_revision_state import (
    PLAN_REVISION_CONTROL_CONTEXT_KEY,
    PLAN_REVISION_DECISIONS,
    PLAN_REVISION_RECOVERY_DECISION,
    plan_revision_control_from_session as _plan_revision_control_from_session,
    plan_revision_recovery_from_session as _plan_revision_recovery_from_session,
    plan_revision_control_record,
)
from app.services.layer3_plan_revision_recovery import (
    plan_revision_recovery_preview_marker as _plan_revision_recovery_preview_marker,
    recover_plan_revision_for_preview_refresh as _recover_plan_revision_for_preview_refresh,
)
from app.services.layer3_approved_plan_correction import (
    APPROVED_PLAN_CANCEL_DECISION,
    APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE,
    APPROVED_PLAN_CANCEL_NEXT_STATE,
    APPROVED_PLAN_CANCELLED_STATUS,
    cancel_approved_plan_without_replacement as _cancel_approved_plan_without_replacement,
    approved_plan_cancel_from_session as _approved_plan_cancel_from_session,
)
from app.services.layer3_signed_reference_state import (
    SignedReferenceDurableState,
    SignedReferenceStateError,
    record_generated_signed_reference,
    record_used_signed_reference,
)
from app.services.layer3_aps_handoff import (
    APS_HANDOFF_SCHEMA_ID,
    PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
    Layer3ApsHandoffError,
    check_aps_handoff_compatibility,
    materialize_aps_handoff,
)
from app.services.layer3_aps_source_family import (
    source_family_for_parser as _source_family_for_parser,
    source_family_summary as _source_family_summary,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_source_boundary import (
    SUPPORTED_SOURCE_CLASSES,
    UNSUPPORTED_SOURCE_CLASSES,
    requested_source_classes as _requested_source_classes,
    source_class_from_material_candidate_id as _source_class_from_material_candidate_id,
    source_class_from_source_candidate_id as _source_class_from_source_candidate_id,
    unsupported_requested as _unsupported_requested,
)
from app.services.layer3_source_intake import (
    SOURCE_INTAKE_SOURCE_FAMILY,
    SourceIntakeError,
    validate_source_intake_gate_b_decision_basis,
)
from app.services.layer3_raw_mixed_contract import RAW_MIXED_SERVER_OWNED_SOURCE_SYSTEM
from app.services.layer3_preflight_request_contract import (
    manual_constraints_from_payload as _manual_constraints,
    preflight_manual_constraint_blocked_fields,
)
from app.services.layer3_typing_entry import (
    Layer3TypingEntryError,
    materialize_typing_entry,
)
from app.services.layer3_sublayer_state import (
    serialize_analysis_group as _serialize_analysis_group,
    serialize_analysis_set as _serialize_analysis_set,
    serialize_analysis_unit as _serialize_analysis_unit,
    serialize_typing_record as _serialize_typing_record,
    session_sublayer_visualization_state as _session_sublayer_visualization_state,
    snapshot_projection as _snapshot_projection,
)
from app.services.layer3_utils import (
    epoch_seconds_iso_z as _epoch_iso,
    json_clone as _json_clone,
    stable_hash as _stable_hash,
    stable_id as _stable_id,
    stable_json_bytes as _canonical_json_bytes,
    utcnow_iso_z as _utcnow_iso,
)
from app.services.layer3_workbench_package_state import (
    APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
    COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
    HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
    PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
    PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_PREVIEW_READY_STATE,
    PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID,
    QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
    active_downstream_unavailable as package_state_active_downstream_unavailable,
    aps_handoff_dispatch_from_reconciliation as _aps_handoff_dispatch_from_reconciliation,
    canonical_payload_hashes as _canonical_payload_hashes,
    canonical_payload_refs as _canonical_payload_refs,
    cohort_package_construction_source as _is_cohort_package_construction_source,
    dispatched_package_id,
    external_export_download_prepare_from_reconciliation as _external_export_download_prepare_from_reconciliation,
    handoff_export_prepare_from_reconciliation as _handoff_export_prepare_from_reconciliation,
    legacy_package_review_submit_record_ref as _legacy_package_review_submit_record_ref,
    package_owner_compatibility as _package_owner_compatibility,
    package_review_candidate_projection,
    package_review_preview_hash as _package_review_preview_hash,
    package_review_preview_summary,
    package_review_submit_downstream_unavailable as _package_review_submit_downstream_unavailable,
    package_review_submit_from_reconciliation as _package_review_submit_from_reconciliation,
    package_source_dataset_version_ids as _package_source_dataset_version_ids,
    package_source_shape as _package_source_shape,
    packages_in_review_order as _packages_in_review_order,
    qualitative_aps_package_construction_source as _is_qualitative_aps_package_construction_source,
    review_package_hash_map as _package_hash_map,
    review_package_ref_map as _package_ref_map,
    review_source_packages as _review_source_packages,
    review_state_is_admitted_associated_cohort,
    unexpected_package_kinds as package_state_unexpected_package_kinds,
)
from app.services.layer3_state_action_contract import build_state_action_contract
from app.services.layer3_state_model_contract import build_workbench_state_model
from app.services.layer3_plan_flow_contract import (
    APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS,
    EXECUTION_SELECTION_FORBIDDEN_FIELDS,
    PLAN_APPROVAL_FORBIDDEN_FIELDS,
    PLAN_REVISION_FORBIDDEN_FIELDS,
    approved_planned_pass_payload as _approved_planned_pass_payload,
    approved_set_payload as _approved_set_payload,
    approved_plan_cancel_blocked_fields,
    execution_selection_blocked_fields,
    plan_approval_blocked_fields,
    plan_revision_blocked_fields,
    source_classes_from_plan_preview as _source_classes_from_plan_preview,
)
from app.services.layer3_plan_flow_state import (
    latest_analysis_plan as _latest_analysis_plan,
    plan_revision_control_for_session as _plan_revision_control,
)
from app.services.layer3_plan_flow_readiness import (
    plan_approval_summary as _plan_approval_summary,
    plan_preview_readiness as _plan_preview_readiness,
    plan_revision_summary as _plan_revision_summary,
)
from app.services.layer3_execution_request_contract import (
    ANALYSIS_EXECUTION_START_ALLOWED_FIELDS,
    ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS,
    EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS,
    EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS,
    EXECUTION_RESULT_STATUS_ALLOWED_FIELDS,
    EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS,
    analysis_execution_start_blocked_fields,
    execution_result_review_blocked_fields,
    execution_result_status_blocked_fields,
)
from app.services.layer3_handoff_contract import (
    APS_HANDOFF_DISPATCH_ALLOWED_FIELDS,
    APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS,
    HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS,
    HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS,
    aps_handoff_dispatch_blocked_fields,
    handoff_export_prepare_blocked_fields,
)
from app.services.layer3_package_review_contract import (
    PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS,
    PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS,
    PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS,
    PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS,
    PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS,
    PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS,
    package_construction_commit_blocked_fields,
    package_review_preview_blocked_fields,
    package_review_submit_blocked_fields,
)
from app.services.layer3_external_export_contract import (
    EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS,
    EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS,
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS,
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS,
    ExternalExportDownloadDelivery,
    external_export_download_delivery_blocked_fields,
    external_export_download_delivery_readiness_mismatches,
    external_export_download_delivery_request_fields,
    external_export_download_prepare_blocked_fields,
)
from app.services.layer3_response_contract import (
    LAYER3_SCHEMA_VERSION as SCHEMA_VERSION,
    base_response as _base_response,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError
from app.services.layer3_authority_rail import authority_rail as _authority_rail
from app.services.layer3_bootstrap_contract import build_bootstrap_contract
from app.services.layer3_preview_contract import (
    plan_preview_hash_contract as _plan_preview_hash_contract,
    preview_identity as _preview_identity,
)
from app.services.layer3_readiness_contract import build_readiness_contract
from app.services.layer3_qual_aps_execution import (
    APS_HANDOFF_COMPANION_ANALYSIS_ROLE,
    ENGINE_FAMILY_QUAL_APS_DOCUMENT,
    Layer3QualApsExecutionError,
    PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
    QUAL_APS_METHOD_NAME,
    QUAL_APS_OUTPUT_SCHEMA_ID,
    QUAL_APS_SOURCE_GATE,
    SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
    execute_single_aps_doc_qualitative_pass,
    is_single_aps_doc_qualitative_planned_pass,
)

ROUTE = "/review/layer3"
API_ROOT = "/api/v1/layer3"
GATE_LABELS = ("intent", "sources", "gate_b", "gate_c", "plan", "execution", "results", "package")
ACTIVE_GATES = ("intent", "sources", "gate_b", "gate_c")
DOWNSTREAM_UNAVAILABLE = ("plan", "execution", "results", "package")
PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE = ("execution", "results", "package")
PLAN_PREVIEW_SCOPE = "owner_service_default"
PLAN_APPROVAL_SCOPE = "owner_service_default"
PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = "layer3.package_review_preview.v1"
QUAL_APS_PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = "layer3.qual_aps_package_review_preview.v1"
PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = "layer3.package_construction_commit.v1"
QUAL_APS_PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = "layer3.qual_aps_package_construction_commit.v1"
PACKAGE_CONSTRUCTION_COMMIT_STATE_SCHEMA_ID = "layer3.package_construction_commit_state.v1"
APS_HANDOFF_DISPATCH_SCHEMA_ID = "layer3.aps_handoff_dispatch.v1"
QUAL_APS_APS_HANDOFF_DISPATCH_SCHEMA_ID = "layer3.qual_aps_aps_handoff_dispatch.v1"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = "layer3.external_export_download_delivery.v1"
EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_SCHEMA_ID = "layer3.external_export_download_signed_reference.v1"
EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_SCHEMA_ID = "layer3.external_export_download_signed_reference_use.v1"
EXECUTION_RESULT_REVIEW_READY_STATE = "execution_result_review_ready"
EXECUTION_RESULT_REVIEW_APPROVED_STATE = "execution_result_review_approved"
EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE = "execution_result_review_changes_requested"
EXECUTION_RESULT_REVIEW_REJECTED_STATE = "execution_result_review_rejected"
EXECUTION_RESULT_REVIEW_BLOCKED_STATE = "execution_result_review_blocked"
PACKAGE_REVIEW_PREVIEW_UNAVAILABLE_STATE = "package_review_preview_unavailable"
PACKAGE_REVIEW_PREVIEW_BLOCKED_STATE = "package_review_preview_blocked"
PACKAGE_REVIEW_PREVIEW_INSPECTED_STATE = "package_review_preview_inspected"
PACKAGE_COMMIT_UNAVAILABLE_STATE = "package_commit_unavailable"
PACKAGE_COMMIT_BLOCKED_STATE = "package_commit_blocked"
PACKAGE_COMMIT_READY_STATE = "package_commit_ready"
PACKAGE_CONSTRUCTED_STATE = "package_constructed"
PACKAGE_REVIEW_SUBMIT_UNAVAILABLE_STATE = "package_review_submit_unavailable"
PACKAGE_REVIEW_SUBMIT_BLOCKED_STATE = "package_review_submit_blocked"
PACKAGE_REVIEW_SUBMIT_READY_STATE = "package_review_submit_ready"
PACKAGE_REVIEW_APPROVED_STATE = "package_review_approved"
PACKAGE_REVIEW_CHANGES_REQUESTED_STATE = "package_review_changes_requested"
PACKAGE_REVIEW_REJECTED_STATE = "package_review_rejected"
PACKAGE_REVIEW_BLOCKED_STATE = "package_review_blocked"
HANDOFF_EXPORT_UNAVAILABLE_STATE = "handoff_export_unavailable"
HANDOFF_EXPORT_READY_STATE = "handoff_export_ready"
HANDOFF_EXPORT_PREPARED_STATE = "handoff_export_prepared"
HANDOFF_EXPORT_HELD_STATE = "handoff_export_held"
HANDOFF_EXPORT_DECLINED_STATE = "handoff_export_declined"
HANDOFF_EXPORT_BLOCKED_STATE = "handoff_export_blocked"
APS_HANDOFF_UNAVAILABLE_STATE = "aps_handoff_unavailable"
APS_HANDOFF_READY_STATE = "aps_handoff_ready"
APS_HANDOFF_DISPATCHED_STATE = "aps_handoff_dispatched"
APS_HANDOFF_BLOCKED_STATE = "aps_handoff_blocked"
APS_HANDOFF_CONFLICT_STATE = "aps_handoff_conflict"
EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE = "external_export_download_unavailable"
EXTERNAL_EXPORT_DOWNLOAD_READY_STATE = "external_export_download_ready"
EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE = "external_export_download_prepared"
EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE = "external_export_download_blocked"
EXTERNAL_EXPORT_DOWNLOAD_CONFLICT_STATE = "external_export_download_conflict"
CONNECTOR_DISPATCH_RECORDED_STATE = "connector_dispatch_recorded"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UNAVAILABLE_STATE = "external_export_download_delivery_unavailable"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_READY_STATE = "external_export_download_delivery_ready"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE = "external_export_download_delivered"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BLOCKED_STATE = "external_export_download_delivery_blocked"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONFLICT_STATE = "external_export_download_delivery_conflict"
EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_READY_STATE = "external_export_download_signed_reference_ready"
EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_DELIVERED_STATE = "external_export_download_signed_reference_delivered"
EXECUTION_RESULT_REVIEW_DECISIONS = frozenset({"approved", "changes_requested", "rejected", "blocked"})
EXECUTION_RESULT_REVIEW_STATE_BY_DECISION = {
    "approved": EXECUTION_RESULT_REVIEW_APPROVED_STATE,
    "changes_requested": EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE,
    "rejected": EXECUTION_RESULT_REVIEW_REJECTED_STATE,
    "blocked": EXECUTION_RESULT_REVIEW_BLOCKED_STATE,
}
PACKAGE_REVIEW_SUBMIT_DECISIONS = frozenset({"approved", "changes_requested", "rejected", "blocked"})
PACKAGE_REVIEW_SUBMIT_STATE_BY_DECISION = {
    "approved": PACKAGE_REVIEW_APPROVED_STATE,
    "changes_requested": PACKAGE_REVIEW_CHANGES_REQUESTED_STATE,
    "rejected": PACKAGE_REVIEW_REJECTED_STATE,
    "blocked": PACKAGE_REVIEW_BLOCKED_STATE,
}
PACKAGE_REVIEW_SUBMIT_NOTE_REQUIRED_DECISIONS = frozenset({"changes_requested", "rejected", "blocked"})
HANDOFF_EXPORT_PREPARE_DECISIONS = frozenset({"authorize_prepare", "hold", "decline", "blocked"})
HANDOFF_EXPORT_PREPARE_STATE_BY_DECISION = {
    "authorize_prepare": HANDOFF_EXPORT_PREPARED_STATE,
    "hold": HANDOFF_EXPORT_HELD_STATE,
    "decline": HANDOFF_EXPORT_DECLINED_STATE,
    "blocked": HANDOFF_EXPORT_BLOCKED_STATE,
}
HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION = {
    "authorize_prepare": "prepared",
    "hold": "held",
    "decline": "declined",
    "blocked": "blocked",
}
HANDOFF_EXPORT_PREPARE_NOTE_REQUIRED_DECISIONS = frozenset({"hold", "decline", "blocked"})
APS_HANDOFF_DISPATCH_OPERATOR_DECISION = "dispatch_aps_handoff"
EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION = "prepare_external_export_download"
PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
)
COHORT_PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE = COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
QUAL_APS_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_construction",
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
QUAL_APS_PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_url",
)
PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE = ("handoff", "export")
COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE = (
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector",
)
HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE = ("aps_handoff", "external_export", "downstream_dispatch")
APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE = (
    "external_export",
    "download",
    "connector_dispatch",
    "non_aps_dispatch",
)
APS_HANDOFF_BLOCKED_DOWNSTREAM_UNAVAILABLE = (
    "aps_handoff",
    "external_export",
    "download",
    "connector_dispatch",
    "non_aps_dispatch",
)
EXECUTION_RESULT_STATUS_TERMINAL_PASS_STATUSES = frozenset(
    {PASS_STATUS_COMPLETED, PASS_STATUS_COMPLETED_WITH_WARNINGS, PASS_STATUS_FAILED}
)
WORKBENCH_STATE_MODEL_STATE_NAMES = {
    "EXECUTION_SELECTION_STATE": EXECUTION_SELECTION_STATE,
    "EXECUTION_PASS_RUNNING_STATE": EXECUTION_PASS_RUNNING_STATE,
    "EXECUTION_PASS_COMPLETED_STATE": EXECUTION_PASS_COMPLETED_STATE,
    "EXECUTION_PASS_FAILED_STATE": EXECUTION_PASS_FAILED_STATE,
    "EXECUTION_RESULT_STATUS_AVAILABLE_STATE": EXECUTION_RESULT_STATUS_AVAILABLE_STATE,
    "EXECUTION_RESULT_REVIEW_READY_STATE": EXECUTION_RESULT_REVIEW_READY_STATE,
    "EXECUTION_RESULT_REVIEW_APPROVED_STATE": EXECUTION_RESULT_REVIEW_APPROVED_STATE,
    "EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE": EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE,
    "EXECUTION_RESULT_REVIEW_REJECTED_STATE": EXECUTION_RESULT_REVIEW_REJECTED_STATE,
    "EXECUTION_RESULT_REVIEW_BLOCKED_STATE": EXECUTION_RESULT_REVIEW_BLOCKED_STATE,
    "PACKAGE_REVIEW_PREVIEW_UNAVAILABLE_STATE": PACKAGE_REVIEW_PREVIEW_UNAVAILABLE_STATE,
    "PACKAGE_REVIEW_PREVIEW_BLOCKED_STATE": PACKAGE_REVIEW_PREVIEW_BLOCKED_STATE,
    "PACKAGE_REVIEW_PREVIEW_READY_STATE": PACKAGE_REVIEW_PREVIEW_READY_STATE,
    "PACKAGE_REVIEW_PREVIEW_INSPECTED_STATE": PACKAGE_REVIEW_PREVIEW_INSPECTED_STATE,
    "PACKAGE_COMMIT_UNAVAILABLE_STATE": PACKAGE_COMMIT_UNAVAILABLE_STATE,
    "PACKAGE_COMMIT_BLOCKED_STATE": PACKAGE_COMMIT_BLOCKED_STATE,
    "PACKAGE_COMMIT_READY_STATE": PACKAGE_COMMIT_READY_STATE,
    "PACKAGE_CONSTRUCTED_STATE": PACKAGE_CONSTRUCTED_STATE,
    "PACKAGE_REVIEW_SUBMIT_UNAVAILABLE_STATE": PACKAGE_REVIEW_SUBMIT_UNAVAILABLE_STATE,
    "PACKAGE_REVIEW_SUBMIT_BLOCKED_STATE": PACKAGE_REVIEW_SUBMIT_BLOCKED_STATE,
    "PACKAGE_REVIEW_SUBMIT_READY_STATE": PACKAGE_REVIEW_SUBMIT_READY_STATE,
    "PACKAGE_REVIEW_APPROVED_STATE": PACKAGE_REVIEW_APPROVED_STATE,
    "PACKAGE_REVIEW_CHANGES_REQUESTED_STATE": PACKAGE_REVIEW_CHANGES_REQUESTED_STATE,
    "PACKAGE_REVIEW_REJECTED_STATE": PACKAGE_REVIEW_REJECTED_STATE,
    "PACKAGE_REVIEW_BLOCKED_STATE": PACKAGE_REVIEW_BLOCKED_STATE,
    "HANDOFF_EXPORT_UNAVAILABLE_STATE": HANDOFF_EXPORT_UNAVAILABLE_STATE,
    "HANDOFF_EXPORT_READY_STATE": HANDOFF_EXPORT_READY_STATE,
    "HANDOFF_EXPORT_PREPARED_STATE": HANDOFF_EXPORT_PREPARED_STATE,
    "HANDOFF_EXPORT_HELD_STATE": HANDOFF_EXPORT_HELD_STATE,
    "HANDOFF_EXPORT_DECLINED_STATE": HANDOFF_EXPORT_DECLINED_STATE,
    "HANDOFF_EXPORT_BLOCKED_STATE": HANDOFF_EXPORT_BLOCKED_STATE,
    "APS_HANDOFF_UNAVAILABLE_STATE": APS_HANDOFF_UNAVAILABLE_STATE,
    "APS_HANDOFF_READY_STATE": APS_HANDOFF_READY_STATE,
    "APS_HANDOFF_DISPATCHED_STATE": APS_HANDOFF_DISPATCHED_STATE,
    "APS_HANDOFF_BLOCKED_STATE": APS_HANDOFF_BLOCKED_STATE,
    "APS_HANDOFF_CONFLICT_STATE": APS_HANDOFF_CONFLICT_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE": EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_READY_STATE": EXTERNAL_EXPORT_DOWNLOAD_READY_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
    "CONNECTOR_DISPATCH_RECORDED_STATE": CONNECTOR_DISPATCH_RECORDED_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE": EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_CONFLICT_STATE": EXTERNAL_EXPORT_DOWNLOAD_CONFLICT_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UNAVAILABLE_STATE": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UNAVAILABLE_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_READY_STATE": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_READY_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE": EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BLOCKED_STATE": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BLOCKED_STATE,
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONFLICT_STATE": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONFLICT_STATE,
    "EXECUTION_RESULT_STATUS_BLOCKED_STATE": EXECUTION_RESULT_STATUS_BLOCKED_STATE,
    "EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE": EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE,
}
def _signed_reference_state_workbench_error(exc: SignedReferenceStateError) -> Layer3WorkbenchError:
    return Layer3WorkbenchError(
        exc.error_code,
        exc.message,
        status=exc.status,
        http_status=exc.http_status,
        blocked_fields=list(exc.blocked_fields),
        next_allowed_actions=list(exc.next_allowed_actions),
    )


EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_TTL_SECONDS = 300
SIGNED_REFERENCE_SECRET_ENV_VAR = "LAYER3_SIGNED_REFERENCE_SECRET"


def _signed_reference_configured_secret() -> bytes:
    return os.environ.get(SIGNED_REFERENCE_SECRET_ENV_VAR, "").strip().encode("utf-8")


def _signed_reference_signing_key() -> bytes:
    configured_secret = _signed_reference_configured_secret()
    if not configured_secret:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_secret_required",
            "LAYER3_SIGNED_REFERENCE_SECRET is required for signed external export/download delivery references.",
            status="blocked",
            http_status=409,
            blocked_fields=[SIGNED_REFERENCE_SECRET_ENV_VAR],
            next_allowed_actions=["configure_layer3_signed_reference_secret"],
        )
    return hashlib.sha256(configured_secret).digest()


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _workbench_state_model() -> dict[str, Any]:
    return build_workbench_state_model(state_names=WORKBENCH_STATE_MODEL_STATE_NAMES)


def _workbench_state_action_contract() -> dict[str, Any]:
    return build_state_action_contract(
        state_model=_workbench_state_model(),
        schema_version=SCHEMA_VERSION,
        gate_labels=GATE_LABELS,
        active_gate_labels=ACTIVE_GATES,
        unavailable_gate_labels=DOWNSTREAM_UNAVAILABLE,
        plan_preview_unavailable_gate_labels=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        gate_b_decisions=GATE_B_DECISIONS,
        plan_revision_decisions=PLAN_REVISION_DECISIONS,
        plan_revision_recovery_decisions=(PLAN_REVISION_RECOVERY_DECISION,),
        approved_plan_cancel_decisions=(APPROVED_PLAN_CANCEL_DECISION,),
        execution_result_review_decisions=EXECUTION_RESULT_REVIEW_DECISIONS,
        package_review_submit_decisions=PACKAGE_REVIEW_SUBMIT_DECISIONS,
        handoff_export_prepare_decisions=HANDOFF_EXPORT_PREPARE_DECISIONS,
        aps_handoff_dispatch_operator_decision=APS_HANDOFF_DISPATCH_OPERATOR_DECISION,
        external_export_download_operator_decision=EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        external_export_download_delivery_operator_decision=EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
        connector_dispatch_record_operator_decision="record_internal_connector_dispatch",
        package_supersession_preview_operator_decision="preview_package_supersession",
        replacement_package_set_authority_operator_decision="record_replacement_package_set_authority",
        package_supersession_commit_operator_decision="commit_package_supersession",
        replacement_package_artifact_manifest_operator_decision="record_replacement_package_artifact_manifest",
        replacement_package_namespace_operator_decision="record_replacement_package_namespace",
        terminal_pass_statuses=EXECUTION_RESULT_STATUS_TERMINAL_PASS_STATUSES,
    )


def readiness_contract() -> dict[str, Any]:
    return build_readiness_contract(
        api_root=API_ROOT,
        state_model=_workbench_state_model(),
        state_action_contract=_workbench_state_action_contract(),
    )


def bootstrap() -> dict[str, Any]:
    return build_bootstrap_contract(
        route=ROUTE,
        api_root=API_ROOT,
        supported_source_classes=SUPPORTED_SOURCE_CLASSES,
        unsupported_source_classes=UNSUPPORTED_SOURCE_CLASSES,
        gate_labels=GATE_LABELS,
        active_gate_labels=ACTIVE_GATES,
        unavailable_gate_labels=DOWNSTREAM_UNAVAILABLE,
        state_action_contract=_workbench_state_action_contract(),
        authority_rail=_authority_rail(
            current_gate="intent",
            browser_only_state=["expanded_rows", "hidden_uncommitted_candidates", "selected_tab"],
        ),
    )


def preflight(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    intent = str(payload.get("natural_language_intent") or "").strip()
    manual_constraints = _manual_constraints(payload)
    if not intent:
        raise Layer3WorkbenchError(
            "empty_intent",
            "Natural-language intent is required before source selection.",
            status="blocked",
            blocked_fields=["natural_language_intent"],
            next_allowed_actions=["edit_intent"],
        )
    blocked_manual_constraints = preflight_manual_constraint_blocked_fields(manual_constraints)
    if blocked_manual_constraints:
        raise Layer3WorkbenchError(
            "preflight_manual_constraint_scope_not_admitted",
            "Manual constraints include non-admitted Layer 3 capability sentinel fields.",
            status="blocked",
            blocked_fields=blocked_manual_constraints,
            next_allowed_actions=["remove_non_admitted_manual_constraints"],
        )
    if manual_constraints.get("conflict") is True or manual_constraints.get("conflicts"):
        raise Layer3WorkbenchError(
            "conflicting_constraints",
            "Manual constraints declare a conflict that must be resolved before source selection.",
            status="blocked",
            blocked_fields=["manual_constraints"],
            next_allowed_actions=["edit_constraints"],
        )
    source_classes = _requested_source_classes(manual_constraints)
    unsupported = _unsupported_requested(source_classes)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_source_class",
            f"Unsupported source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["manual_constraints.source_classes"],
            next_allowed_actions=["choose_supported_sources"],
        )
    normalized = {
        "intent_text": " ".join(intent.split()),
        "manual_constraints": _json_clone(manual_constraints),
    }
    preflight_id = _stable_id("preflight", normalized)
    return {
        **_base_response("layer3.preflight_result.v1", request_id=request_id),
        "preflight_id": preflight_id,
        "normalized_intent": normalized,
        "blockers": [],
        "warnings": [],
        "eligible_for_source_selection": True,
        "authority_rail": _authority_rail(
            preflight_id=preflight_id,
            current_gate="sources",
            persistence_mode="preview_only",
            source_classes=source_classes,
        ),
    }


def source_preview(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    preflight_id = str(payload.get("preflight_id") or "").strip()
    if not preflight_id:
        raise Layer3WorkbenchError("empty_intent", "preflight_id is required for source preview.", status="blocked")
    requested = [str(item) for item in payload.get("selected_source_classes") or SUPPORTED_SOURCE_CLASSES]
    unsupported = _unsupported_requested(requested)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_source_class",
            f"Unsupported source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["selected_source_classes"],
            next_allowed_actions=["choose_supported_sources"],
        )
    candidates = []
    for source_class in requested:
        short_id = _stable_id("src", {"preflight_id": preflight_id, "source_class": source_class}).split("-", 1)[1]
        candidates.append(
            {
                "source_candidate_id": f"src-{source_class}-{short_id}",
                "source_class": source_class,
                "source_label": source_class.replace("_", " ").title(),
                "source_ref": f"{source_class}:preview:{short_id}",
                "source_authority": "repo_supported",
                "eligible_for_material_preview": True,
                "unavailable_reason": None,
            }
        )
    source_set_id = _stable_id("source-set", [item["source_candidate_id"] for item in candidates])
    return {
        **_base_response("layer3.source_preview_result.v1", request_id=request_id),
        "source_set_id": source_set_id,
        "source_candidates": candidates,
        "unsupported_sources": [],
        "authority_rail": _authority_rail(
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            current_gate="gate_b",
            persistence_mode="preview_only",
            source_classes=requested,
        ),
    }


def _requested_dataset_version_ids(payload: dict[str, Any]) -> list[str]:
    query_basis = payload.get("query_basis") if isinstance(payload.get("query_basis"), dict) else {}
    filters = query_basis.get("filters") if isinstance(query_basis.get("filters"), dict) else {}
    raw_ids = payload.get("dataset_version_ids") or filters.get("dataset_version_ids") or []
    if isinstance(raw_ids, str):
        raw_ids = [raw_ids]
    if not isinstance(raw_ids, list):
        return []
    result: list[str] = []
    for raw_id in raw_ids:
        dataset_version_id = str(raw_id or "").strip()
        if dataset_version_id and dataset_version_id not in result:
            result.append(dataset_version_id)
    return result


def _requested_aps_content_document_ids(payload: dict[str, Any]) -> list[str]:
    query_basis = payload.get("query_basis") if isinstance(payload.get("query_basis"), dict) else {}
    filters = query_basis.get("filters") if isinstance(query_basis.get("filters"), dict) else {}
    raw_ids = payload.get("aps_content_document_ids") or filters.get("aps_content_document_ids") or []
    if isinstance(raw_ids, str):
        raw_ids = [raw_ids]
    if not isinstance(raw_ids, list):
        return []
    result: list[str] = []
    for raw_id in raw_ids:
        content_id = str(raw_id or "").strip()
        if content_id and content_id not in result:
            result.append(content_id)
    return result


def _dataset_version_variables(db: Session, *, dataset_version_id: str) -> list[VariableDefinition]:
    return (
        db.query(VariableDefinition)
        .filter(VariableDefinition.dataset_version_id == dataset_version_id)
        .order_by(VariableDefinition.ordinal_position.asc())
        .all()
    )


def _admitted_dataset_version_provenance_filter():
    return or_(
        and_(
            DatasetSourceProvenance.source_system == "nrc_adams_aps",
            or_(
                DatasetSourceProvenance.source_mode.is_(None),
                DatasetSourceProvenance.source_mode != "raw_mixed_materialized",
            ),
        ),
        and_(
            DatasetSourceProvenance.source_system == RAW_MIXED_SERVER_OWNED_SOURCE_SYSTEM,
            DatasetSourceProvenance.source_mode == "raw_mixed_materialized",
            DatasetSourceProvenance.artifact_locator_type == "server_owned_ref",
            DatasetSourceProvenance.fetch_policy_mode == "server_owned_manifest",
        ),
    )


def _is_admitted_dataset_version_provenance(row: DatasetSourceProvenance) -> bool:
    if row.source_mode == "raw_mixed_materialized":
        return (
            row.source_system == RAW_MIXED_SERVER_OWNED_SOURCE_SYSTEM
            and row.artifact_locator_type == "server_owned_ref"
            and row.fetch_policy_mode == "server_owned_manifest"
        )
    return row.source_system == "nrc_adams_aps"


def _dataset_version_provenance_rows(db: Session, *, dataset_version_id: str) -> list[DatasetSourceProvenance]:
    return (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .order_by(
            DatasetSourceProvenance.created_at.desc(),
            DatasetSourceProvenance.dataset_source_provenance_id.desc(),
        )
        .all()
    )


def _aps_dataset_provenance_rows(db: Session, *, dataset_version_id: str) -> list[DatasetSourceProvenance]:
    rows = _dataset_version_provenance_rows(db, dataset_version_id=dataset_version_id)
    if rows and not _is_admitted_dataset_version_provenance(rows[0]):
        raise Layer3WorkbenchError(
            "dataset_version_provenance_not_admitted",
            "DatasetVersion provenance is not admitted for Layer 3 material preview.",
            status="blocked",
            blocked_fields=["dataset_version_ids"],
            next_allowed_actions=["revise_dataset_version_selection"],
        )
    return [row for row in rows if _is_admitted_dataset_version_provenance(row)]


def _serialize_aps_dataset_provenance(row: DatasetSourceProvenance) -> dict[str, Any]:
    source_reference = row.source_reference_json or {}
    return {
        "dataset_source_provenance_id": row.dataset_source_provenance_id,
        "connector_run_id": row.connector_run_id,
        "source_system": row.source_system,
        "source_mode": row.source_mode,
        "source_artifact_key": row.source_artifact_key,
        "downloaded_sha256": row.downloaded_sha256,
        "raw_storage_ref": row.raw_storage_ref,
        "parser_family": source_reference.get("parser_family"),
        "parser_contract_id": source_reference.get("parser_contract_id"),
        "typed_content_contract_id": source_reference.get("typed_content_contract_id"),
        "target_id": source_reference.get("target_id"),
        "accession_number": source_reference.get("accession_number"),
        "table_index": source_reference.get("table_index"),
        "table_hash": source_reference.get("table_hash"),
        "diagnostics_ref": source_reference.get("diagnostics_ref"),
    }


def _dataset_version_source_trace(
    *,
    dataset: Dataset | None,
    version: DatasetVersion,
    variables: list[VariableDefinition],
    aps_provenance: list[dict[str, Any]],
    source_family: dict[str, Any],
    storage_available: bool,
) -> dict[str, Any]:
    numeric_variables = [variable.variable_name for variable in variables if variable.is_numeric]
    time_variables = [variable.variable_name for variable in variables if variable.is_time_index]
    primary_provenance = aps_provenance[0] if aps_provenance else {}
    trace_readiness = (
        "traceable_aps_dataset_version"
        if aps_provenance
        else "traceable_dataset_version_without_aps_provenance"
    )
    return {
        "schema_id": "layer3.dataset_version_source_trace.v1",
        "trace_scope": "selected_material_candidate",
        "selection_shape": "dataset_version",
        "trace_readiness": trace_readiness,
        "ui_summary": (
            "Selected material is traceable through DatasetVersion authority, "
            "DatasetSourceProvenance, parser contract metadata, and source artifact refs."
            if aps_provenance
            else "Selected material is traceable as an existing DatasetVersion; APS source provenance was not present."
        ),
        "source_family": source_family["source_family"],
        "source_family_label": source_family["source_family_label"],
        "source_admission_state": source_family["admission_state"],
        "source_family_scope": source_family["scope"],
        "dataset_identity": {
            "dataset_id": version.dataset_id,
            "dataset_version_id": version.dataset_version_id,
            "dataset_name": dataset.name if dataset is not None else None,
            "version_label": version.version_label,
            "version_type": version.version_type,
            "status": version.status,
        },
        "variable_summary": {
            "variable_count": len(variables),
            "time_column": dataset.time_column if dataset is not None else None,
            "frequency_hint": dataset.frequency_hint if dataset is not None else None,
            "numeric_variables": numeric_variables,
            "time_variables": time_variables,
        },
        "storage_summary": {
            "row_count": int(version.row_count or 0),
            "storage_available": storage_available,
        },
        "aps_trace_refs": {
            "source_artifact_key": primary_provenance.get("source_artifact_key"),
            "raw_storage_ref": primary_provenance.get("raw_storage_ref"),
            "diagnostics_ref": primary_provenance.get("diagnostics_ref"),
            "target_id": primary_provenance.get("target_id"),
            "accession_number": primary_provenance.get("accession_number"),
            "parser_family": primary_provenance.get("parser_family"),
            "parser_contract_id": primary_provenance.get("parser_contract_id"),
            "typed_content_contract_id": primary_provenance.get("typed_content_contract_id"),
            "table_index": primary_provenance.get("table_index"),
            "table_hash": primary_provenance.get("table_hash"),
        },
    }


def _aps_content_linkage_rows(db: Session, *, content_id: str) -> list[ApsContentLinkage]:
    return (
        db.query(ApsContentLinkage)
        .filter(ApsContentLinkage.content_id == content_id)
        .order_by(ApsContentLinkage.created_at.desc(), ApsContentLinkage.aps_content_linkage_id.desc())
        .all()
    )


def _aps_content_chunks(
    db: Session,
    *,
    content_id: str,
    content_contract_id: str | None = None,
    chunking_contract_id: str | None = None,
    limit: int = 200,
) -> list[ApsContentChunk]:
    query = db.query(ApsContentChunk).filter(ApsContentChunk.content_id == content_id)
    if content_contract_id is not None:
        query = query.filter(ApsContentChunk.content_contract_id == content_contract_id)
    if chunking_contract_id is not None:
        query = query.filter(ApsContentChunk.chunking_contract_id == chunking_contract_id)
    return (
        query.order_by(ApsContentChunk.chunk_ordinal.asc(), ApsContentChunk.chunk_id.asc())
        .limit(max(1, min(int(limit or 200), 1000)))
        .all()
    )


def _visual_page_ref_count(document: ApsContentDocument) -> int:
    if not document.visual_page_refs_json:
        return 0
    try:
        refs = json.loads(document.visual_page_refs_json)
    except (TypeError, ValueError):
        return 0
    return len(refs) if isinstance(refs, list) else 0


def _serialize_aps_content_linkage(linkage: ApsContentLinkage) -> dict[str, Any]:
    return {
        "aps_content_linkage_id": linkage.aps_content_linkage_id,
        "content_id": linkage.content_id,
        "run_id": linkage.run_id,
        "target_id": linkage.target_id,
        "accession_number": linkage.accession_number,
        "content_contract_id": linkage.content_contract_id,
        "chunking_contract_id": linkage.chunking_contract_id,
        "content_units_ref": linkage.content_units_ref,
        "normalized_text_ref": linkage.normalized_text_ref,
        "normalized_text_sha256": linkage.normalized_text_sha256,
        "blob_ref": linkage.blob_ref,
        "blob_sha256": linkage.blob_sha256,
        "download_exchange_ref": linkage.download_exchange_ref,
        "discovery_ref": linkage.discovery_ref,
        "selection_ref": linkage.selection_ref,
        "diagnostics_ref": linkage.diagnostics_ref,
    }


def _aps_content_document_source_trace(
    *,
    document: ApsContentDocument,
    linkages: list[ApsContentLinkage],
    chunks: list[ApsContentChunk],
) -> dict[str, Any]:
    primary_linkage = linkages[0] if linkages else None
    unit_kinds = sorted({str(chunk.unit_kind) for chunk in chunks if chunk.unit_kind})
    page_starts = [chunk.page_start for chunk in chunks if chunk.page_start is not None]
    page_ends = [chunk.page_end for chunk in chunks if chunk.page_end is not None]
    page_span = None
    if page_starts or page_ends:
        page_span = {
            "page_start": min(page_starts) if page_starts else None,
            "page_end": max(page_ends) if page_ends else None,
        }
    return {
        "schema_id": "layer3.aps_content_document_source_trace.v1",
        "trace_scope": "selected_material_candidate",
        "selection_shape": "aps_content_document",
        "trace_readiness": (
            "traceable_aps_content_document"
            if primary_linkage
            else "traceable_aps_content_document_without_linkage"
        ),
        "ui_summary": (
            "Selected APS content document is traceable through ApsContentDocument, chunks, and linkage refs."
            if primary_linkage
            else "Selected APS content document is indexed, but APS linkage refs were not present."
        ),
        "source_family": "aps_content_document",
        "source_family_label": "APS content document",
        "source_admission_state": "admitted_content_document",
        "source_family_scope": "indexed APS document content with chunk-level qualitative material",
        "document_identity": {
            "content_id": document.content_id,
            "content_contract_id": document.content_contract_id,
            "chunking_contract_id": document.chunking_contract_id,
            "normalization_contract_id": document.normalization_contract_id,
            "content_status": document.content_status,
            "media_type": document.media_type,
            "document_class": document.document_class,
            "quality_status": document.quality_status,
        },
        "chunk_summary": {
            "chunk_count": int(document.chunk_count or len(chunks)),
            "loaded_chunk_count": len(chunks),
            "normalized_char_count": int(document.normalized_char_count or 0),
            "page_count": int(document.page_count or 0),
            "visual_page_ref_count": _visual_page_ref_count(document),
            "page_span": page_span,
            "unit_kinds": unit_kinds,
        },
        "aps_trace_refs": {
            "run_id": primary_linkage.run_id if primary_linkage else None,
            "target_id": primary_linkage.target_id if primary_linkage else None,
            "accession_number": primary_linkage.accession_number if primary_linkage else None,
            "content_units_ref": primary_linkage.content_units_ref if primary_linkage else None,
            "normalized_text_ref": primary_linkage.normalized_text_ref if primary_linkage else None,
            "blob_ref": primary_linkage.blob_ref if primary_linkage else None,
            "blob_sha256": primary_linkage.blob_sha256 if primary_linkage else None,
            "download_exchange_ref": primary_linkage.download_exchange_ref if primary_linkage else None,
            "discovery_ref": primary_linkage.discovery_ref if primary_linkage else None,
            "selection_ref": primary_linkage.selection_ref if primary_linkage else None,
            "normalized_text_sha256": (
                (primary_linkage.normalized_text_sha256 if primary_linkage else None)
                or document.normalized_text_sha256
            ),
            "diagnostics_ref": (primary_linkage.diagnostics_ref if primary_linkage else None) or document.diagnostics_ref,
        },
    }


def aps_dataset_version_candidates(db: Session, *, limit: int = 50) -> dict[str, Any]:
    normalized_limit = max(1, min(int(limit or 50), 200))
    rows = (
        db.query(DatasetSourceProvenance)
        .order_by(
            DatasetSourceProvenance.created_at.desc(),
            DatasetSourceProvenance.dataset_source_provenance_id.desc(),
        )
        .limit(normalized_limit * 6)
        .all()
    )
    candidates: list[dict[str, Any]] = []
    seen_dataset_version_ids: set[str] = set()
    for row in rows:
        if row.dataset_version_id in seen_dataset_version_ids:
            continue
        seen_dataset_version_ids.add(row.dataset_version_id)
        if not _is_admitted_dataset_version_provenance(row):
            continue
        version = db.get(DatasetVersion, row.dataset_version_id)
        if version is None:
            continue
        dataset = db.get(Dataset, version.dataset_id)
        variables = _dataset_version_variables(db, dataset_version_id=version.dataset_version_id)
        provenance = _serialize_aps_dataset_provenance(row)
        source_family = _source_family_for_parser(provenance.get("parser_family"))
        candidates.append(
            {
                "schema_id": "layer3.aps_dataset_version_candidate.v1",
                "dataset_version_id": version.dataset_version_id,
                "dataset_id": version.dataset_id,
                "dataset_name": dataset.name if dataset is not None else None,
                "version_label": version.version_label,
                "version_type": version.version_type,
                "status": version.status,
                "row_count": int(version.row_count or 0),
                "variable_count": len(variables),
                "time_column": dataset.time_column if dataset is not None else None,
                "frequency_hint": dataset.frequency_hint if dataset is not None else None,
                "source_system": row.source_system,
                "source_mode": row.source_mode,
                "source_artifact_key": row.source_artifact_key,
                "parser_family": provenance.get("parser_family"),
                "typed_content_contract_id": provenance.get("typed_content_contract_id"),
                "source_family": source_family["source_family"],
                "source_family_label": source_family["source_family_label"],
                "source_admission_state": source_family["admission_state"],
                "source_family_scope": source_family["scope"],
                "target_id": provenance.get("target_id"),
                "accession_number": provenance.get("accession_number"),
                "diagnostics_ref": provenance.get("diagnostics_ref"),
                "aps_derived": True,
            }
        )
        if len(candidates) >= normalized_limit:
            break
    return {
        **_base_response("layer3.aps_dataset_version_candidates.v1"),
        "dataset_version_candidates": candidates,
        "candidate_count": len(candidates),
        "source_system": "nrc_adams_aps",
        "source_family_summary": _source_family_summary(candidates),
        "authority_rail": {
            "authority_source": "dataset_source_provenance",
            "selection_authority": "material_preview_dataset_version_ids",
            "read_only": True,
        },
    }


def aps_content_document_candidates(db: Session, *, limit: int = 50) -> dict[str, Any]:
    normalized_limit = max(1, min(int(limit or 50), 200))
    rows = (
        db.query(ApsContentDocument)
        .order_by(ApsContentDocument.updated_at.desc(), ApsContentDocument.aps_content_document_id.desc())
        .limit(normalized_limit * 3)
        .all()
    )
    candidates: list[dict[str, Any]] = []
    seen_content_ids: set[str] = set()
    for document in rows:
        if document.content_id in seen_content_ids:
            continue
        linkages = _aps_content_linkage_rows(db, content_id=document.content_id)
        primary_linkage = linkages[0] if linkages else None
        candidates.append(
            {
                "schema_id": "layer3.aps_content_document_candidate.v1",
                "content_id": document.content_id,
                "content_contract_id": document.content_contract_id,
                "chunking_contract_id": document.chunking_contract_id,
                "normalization_contract_id": document.normalization_contract_id,
                "content_status": document.content_status,
                "media_type": document.media_type,
                "document_class": document.document_class,
                "quality_status": document.quality_status,
                "page_count": int(document.page_count or 0),
                "chunk_count": int(document.chunk_count or 0),
                "normalized_char_count": int(document.normalized_char_count or 0),
                "visual_page_ref_count": _visual_page_ref_count(document),
                "diagnostics_ref": document.diagnostics_ref,
                "run_id": primary_linkage.run_id if primary_linkage else None,
                "target_id": primary_linkage.target_id if primary_linkage else None,
                "accession_number": primary_linkage.accession_number if primary_linkage else None,
                "content_units_ref": primary_linkage.content_units_ref if primary_linkage else None,
                "normalized_text_ref": primary_linkage.normalized_text_ref if primary_linkage else None,
                "blob_ref": primary_linkage.blob_ref if primary_linkage else None,
                "selection_ref": primary_linkage.selection_ref if primary_linkage else None,
                "discovery_ref": primary_linkage.discovery_ref if primary_linkage else None,
                "source_family": "aps_content_document",
                "source_family_label": "APS content document",
                "source_admission_state": "admitted_content_document",
                "source_family_scope": "indexed APS document content with chunk-level qualitative material",
                "aps_derived": bool(primary_linkage),
            }
        )
        seen_content_ids.add(document.content_id)
        if len(candidates) >= normalized_limit:
            break
    return {
        **_base_response("layer3.aps_content_document_candidates.v1"),
        "aps_content_document_candidates": candidates,
        "candidate_count": len(candidates),
        "source_system": "nrc_adams_aps",
        "authority_rail": {
            "authority_source": "aps_content_document_and_linkage",
            "selection_authority": "material_preview_aps_content_document_ids",
            "read_only": True,
        },
    }


def _dataset_version_material_candidates(
    db: Session,
    *,
    source_id: str,
    dataset_version_ids: list[str],
    query_label: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for dataset_version_id in dataset_version_ids:
        version = db.get(DatasetVersion, dataset_version_id)
        if version is None:
            raise Layer3WorkbenchError(
                "dataset_version_not_found",
                f"Dataset version '{dataset_version_id}' was not found for material preview.",
                status="blocked",
                blocked_fields=["dataset_version_ids"],
                next_allowed_actions=["revise_dataset_version_selection"],
            )
        dataset = db.get(Dataset, version.dataset_id)
        variables = _dataset_version_variables(db, dataset_version_id=dataset_version_id)
        aps_provenance = [
            _serialize_aps_dataset_provenance(row)
            for row in _aps_dataset_provenance_rows(db, dataset_version_id=dataset_version_id)
        ]
        source_family = (
            _source_family_for_parser(aps_provenance[0].get("parser_family"))
            if aps_provenance
            else {
                "source_family": "dataset_version",
                "source_family_label": "Dataset version",
                "admission_state": "admitted_dataset_version",
                "scope": "existing Layer 3 dataset_version source shape",
            }
        )
        storage_ref = str(version.storage_ref or "").strip()
        storage_available = bool(storage_ref and Path(storage_ref).exists())
        source_trace = _dataset_version_source_trace(
            dataset=dataset,
            version=version,
            variables=variables,
            aps_provenance=aps_provenance,
            source_family=source_family,
            storage_available=storage_available,
        )
        source_identity = {
            "schema_id": "layer3.dataset_version_source_identity.v1",
            "source_class": "dataset_version",
            "dataset_version_id": version.dataset_version_id,
            "dataset_id": version.dataset_id,
            "dataset_name": dataset.name if dataset is not None else None,
            "version_label": version.version_label,
            "version_type": version.version_type,
            "status": version.status,
        }
        source_provenance = {
            "schema_id": "layer3.dataset_version_source_provenance.v1",
            "dataset_id": version.dataset_id,
            "storage_ref": storage_ref or None,
            "row_count": int(version.row_count or 0),
            "variable_count": len(variables),
            "time_column": dataset.time_column if dataset is not None else None,
            "frequency_hint": dataset.frequency_hint if dataset is not None else None,
            "domain_pack": dataset.domain_pack if dataset is not None else None,
            "aps_source_provenance": aps_provenance,
            "aps_derived": bool(aps_provenance),
            "source_family": source_family["source_family"],
            "source_family_label": source_family["source_family_label"],
            "source_admission_state": source_family["admission_state"],
            "source_family_scope": source_family["scope"],
            "source_trace": source_trace,
        }
        load_summary = {
            "loaded_records": int(version.row_count or 0),
            "failed_records": 0,
            "preview_material": True,
            "storage_available": storage_available,
            "variable_count": len(variables),
            "aps_derived": bool(aps_provenance),
            "source_family": source_family["source_family"],
            "source_admission_state": source_family["admission_state"],
        }
        short_id = _stable_id(
            "mat",
            {
                "source_id": source_id,
                "dataset_version_id": dataset_version_id,
                "query_basis": query_label,
            },
        ).split("-", 1)[1]
        candidates.append(
            {
                "candidate_id": f"mat-dataset_version-{short_id}",
                "source_label": "Dataset Version",
                "source_class": "dataset_version",
                "source_ref": f"dataset_version:{dataset_version_id}",
                "owner_service_source_shape": "dataset_version",
                "planning_shape_family": "tabular_numeric",
                "source_family": source_family["source_family"],
                "source_family_label": source_family["source_family_label"],
                "source_admission_state": source_family["admission_state"],
                "source_family_scope": source_family["scope"],
                "source_trace": source_trace,
                "query_basis": query_label,
                "validation_status": "valid" if variables else "incomplete",
                "duplicate_status": "unique",
                "size_or_unit_count": int(version.row_count or 0),
                "preview_payload_ref": None,
                "provenance_ref": (
                    aps_provenance[0]["source_artifact_key"]
                    if aps_provenance
                    else f"dataset_version:{dataset_version_id}"
                ),
                "source_identity": source_identity,
                "source_provenance": source_provenance,
                "payload": {"dataset_version_id": dataset_version_id},
                "load_summary": load_summary,
                "current_decision_state": "candidate",
            }
        )
    return candidates


def _aps_content_document_material_candidates(
    db: Session,
    *,
    source_id: str,
    content_ids: list[str],
    query_label: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for content_id in content_ids:
        document = (
            db.query(ApsContentDocument)
            .filter(ApsContentDocument.content_id == content_id)
            .order_by(ApsContentDocument.updated_at.desc(), ApsContentDocument.aps_content_document_id.desc())
            .first()
        )
        if document is None:
            raise Layer3WorkbenchError(
                "aps_content_document_not_found",
                f"APS content document '{content_id}' was not found for material preview.",
                status="blocked",
                blocked_fields=["aps_content_document_ids"],
                next_allowed_actions=["revise_aps_content_document_selection"],
            )
        linkages = _aps_content_linkage_rows(db, content_id=content_id)
        chunks = _aps_content_chunks(db, content_id=content_id)
        source_trace = _aps_content_document_source_trace(document=document, linkages=linkages, chunks=chunks)
        serialized_linkages = [_serialize_aps_content_linkage(linkage) for linkage in linkages]
        primary_linkage = serialized_linkages[0] if serialized_linkages else {}
        source_identity = {
            "schema_id": "layer3.aps_content_document_source_identity.v1",
            "source_class": "aps_content_document",
            "content_id": document.content_id,
            "content_contract_id": document.content_contract_id,
            "chunking_contract_id": document.chunking_contract_id,
            "normalization_contract_id": document.normalization_contract_id,
            "content_status": document.content_status,
            "media_type": document.media_type,
            "document_class": document.document_class,
            "quality_status": document.quality_status,
        }
        source_provenance = {
            "schema_id": "layer3.aps_content_document_source_provenance.v1",
            "aps_derived": bool(serialized_linkages),
            "content_id": document.content_id,
            "linkage_count": len(serialized_linkages),
            "aps_content_linkages": serialized_linkages,
            "diagnostics_ref": document.diagnostics_ref,
            "source_family": "aps_content_document",
            "source_family_label": "APS content document",
            "source_admission_state": "admitted_content_document",
            "source_family_scope": "indexed APS document content with chunk-level qualitative material",
            "source_trace": source_trace,
        }
        load_summary = {
            "loaded_records": len(chunks),
            "failed_records": 0,
            "preview_material": True,
            "chunk_count": int(document.chunk_count or len(chunks)),
            "loaded_chunk_count": len(chunks),
            "page_count": int(document.page_count or 0),
            "source_family": "aps_content_document",
            "source_admission_state": "admitted_content_document",
        }
        short_id = _stable_id(
            "mat",
            {
                "source_id": source_id,
                "content_id": content_id,
                "query_basis": query_label,
            },
        ).split("-", 1)[1]
        candidates.append(
            {
                "candidate_id": f"mat-aps_content_document-{short_id}",
                "source_label": "APS Content Document",
                "source_class": "aps_content_document",
                "source_ref": f"aps_content_document:{content_id}",
                "owner_service_source_shape": "aps_content_document",
                "planning_shape_family": "document_chunks",
                "source_family": "aps_content_document",
                "source_family_label": "APS content document",
                "source_admission_state": "admitted_content_document",
                "source_family_scope": "indexed APS document content with chunk-level qualitative material",
                "source_trace": source_trace,
                "query_basis": query_label,
                "validation_status": "valid" if chunks else "incomplete",
                "duplicate_status": "unique",
                "size_or_unit_count": len(chunks) or int(document.chunk_count or 0),
                "preview_payload_ref": None,
                "provenance_ref": (
                    primary_linkage.get("content_units_ref")
                    or document.diagnostics_ref
                    or f"aps_content_document:{content_id}"
                ),
                "source_identity": source_identity,
                "source_provenance": source_provenance,
                "payload": {"content_id": content_id},
                "load_summary": load_summary,
                "current_decision_state": "candidate",
            }
        )
    return candidates


def material_preview(payload: dict[str, Any], db: Session | None = None) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    source_ids = [str(item) for item in payload.get("source_candidate_ids") or []]
    if not source_ids:
        raise Layer3WorkbenchError("no_source_candidates", "At least one source candidate is required.", status="blocked")
    terms = [str(item) for item in (payload.get("query_basis") or {}).get("terms") or []]
    query_label = ", ".join(terms) if terms else "operator_intent"
    dataset_version_ids = _requested_dataset_version_ids(payload)
    aps_content_document_ids = _requested_aps_content_document_ids(payload)
    if dataset_version_ids and db is None:
        raise Layer3WorkbenchError(
            "dataset_version_preview_requires_db",
            "Real dataset_version material preview requires a database session.",
            status="blocked",
            blocked_fields=["dataset_version_ids"],
        )
    if aps_content_document_ids and db is None:
        raise Layer3WorkbenchError(
            "aps_content_document_preview_requires_db",
            "Real APS content document material preview requires a database session.",
            status="blocked",
            blocked_fields=["aps_content_document_ids"],
        )
    candidates = []
    for source_id in source_ids:
        source_class = _source_class_from_source_candidate_id(source_id)
        if source_class is None:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unknown source candidate: {source_id}.")
        if source_class == "dataset_version" and dataset_version_ids:
            assert db is not None
            candidates.extend(
                _dataset_version_material_candidates(
                    db,
                    source_id=source_id,
                    dataset_version_ids=dataset_version_ids,
                    query_label=query_label,
                )
            )
            continue
        if source_class == "aps_content_document" and aps_content_document_ids:
            assert db is not None
            candidates.extend(
                _aps_content_document_material_candidates(
                    db,
                    source_id=source_id,
                    content_ids=aps_content_document_ids,
                    query_label=query_label,
                )
            )
            continue
        short_id = _stable_id("mat", {"source_id": source_id, "query_basis": query_label}).split("-", 1)[1]
        planning_shape = "tabular_numeric" if source_class == "dataset_version" else "document_chunks"
        candidates.append(
            {
                "candidate_id": f"mat-{source_class}-{short_id}",
                "source_label": source_class.replace("_", " ").title(),
                "source_class": source_class,
                "source_ref": f"{source_class}:preview:{short_id}",
                "owner_service_source_shape": source_class,
                "planning_shape_family": planning_shape,
                "query_basis": query_label,
                "validation_status": "valid",
                "duplicate_status": "unique",
                "size_or_unit_count": 1,
                "preview_payload_ref": None,
                "provenance_ref": f"layer3-preview:{short_id}",
                "source_identity": {"candidate_id": f"mat-{source_class}-{short_id}", "source_class": source_class},
                "source_provenance": {"provenance_ref": f"layer3-preview:{short_id}"},
                "payload": {"candidate_id": f"mat-{source_class}-{short_id}", "source_class": source_class},
                "load_summary": {"loaded_records": 1, "failed_records": 0, "preview_material": True},
                "current_decision_state": "candidate",
            }
        )
    preview_id = _stable_id("material-preview", [item["candidate_id"] for item in candidates])
    material_hash = compute_material_preview_hash(
        [gate_b_material_candidate_basis_from_preview(candidate) for candidate in candidates]
    )
    return {
        **_base_response("layer3.material_preview_result.v1", request_id=request_id),
        "material_preview_id": preview_id,
        "material_preview_hash": material_hash,
        "material_candidates": candidates,
        "partial_retrieval": False,
        "authority_rail": _authority_rail(
            preflight_id=str(payload.get("preflight_id") or "none"),
            source_set_id=str(payload.get("source_set_id") or "none"),
            current_gate="gate_b",
            persistence_mode="preview_only",
            source_classes=sorted({item["source_class"] for item in candidates}),
        ),
    }


def _gate_b_response_from_session(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    manifest: L3SelectionManifest,
    decision_manifest: dict[str, Any],
) -> dict[str, Any]:
    decisions = [item for item in decision_manifest.get("items") or [] if isinstance(item, dict)]
    counts = gate_b_counts(decisions)
    hints = manifest.source_plane_hints_json or {}
    material_hash = compute_material_preview_hash(
        [
            (
                item.get("material_preview_basis")
                if isinstance(item.get("material_preview_basis"), dict)
                else gate_b_material_candidate_basis_from_decision(
                    candidate_id=str(item.get("candidate_id") or "").strip(),
                    source_class=str(item.get("source_class") or "").strip(),
                    decision_basis=item.get("decision_basis") if isinstance(item.get("decision_basis"), dict) else {},
                )
            )
            for item in decisions
        ]
    )
    return {
        **_base_response("layer3.gate_b_decision_result.v1", request_id=request_id),
        "status": status,
        "session_id": session.session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "material_preview_hash": material_hash,
        "gate_b_decision_manifest_id": build_gate_b_decision_manifest_id(decision_manifest),
        "approved_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "approved"],
        "denied_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "denied"],
        "isolated_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "isolated"],
        "flagged_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "flagged"],
        "next_state": "gate_c_preview_ready",
        "authority_rail": _authority_rail(
            session_id=session.session_id,
            preflight_id=str(hints.get("preflight_id") or "none"),
            source_set_id=str(hints.get("source_set_id") or "none"),
            current_gate="gate_c",
            persistence_mode="durable_layer3_control",
            source_classes=sorted({item["source_class"] for item in decisions if item["decision"] == "approved"}),
            counts=counts,
        ),
    }


def gate_b_decision(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for Gate B idempotency.",
            status="blocked",
            blocked_fields=["client_request_id"],
        )
    preflight_id = str(payload.get("preflight_id") or "").strip()
    source_set_id = str(payload.get("source_set_id") or "").strip()
    material_preview_id = str(payload.get("material_preview_id") or "").strip()
    supplied_material_preview_hash = str(payload.get("material_preview_hash") or "").strip()
    raw_decisions = payload.get("candidate_decisions") or []
    if not isinstance(raw_decisions, list) or not raw_decisions:
        raise Layer3WorkbenchError("no_approved_material", "At least one Gate B decision is required.", status="blocked")

    decisions: list[dict[str, Any]] = []
    material_candidate_bases: list[dict[str, str]] = []
    seen_candidate_ids: set[str] = set()
    for raw in raw_decisions:
        if not isinstance(raw, dict):
            raise Layer3WorkbenchError("invalid_material_candidate", "Gate B decision entries must be objects.")
        candidate_id = str(raw.get("candidate_id") or "").strip()
        source_class = _source_class_from_material_candidate_id(candidate_id)
        decision = str(raw.get("decision") or "").strip()
        reason = str(raw.get("operator_reason") or "").strip()
        if source_class is None:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unknown material candidate: {candidate_id}.")
        if candidate_id in seen_candidate_ids:
            raise Layer3WorkbenchError(
                "duplicate_material_candidate_decision",
                f"Material candidate '{candidate_id}' was submitted more than once.",
                blocked_fields=["candidate_decisions.candidate_id"],
            )
        seen_candidate_ids.add(candidate_id)
        if decision not in GATE_B_DECISIONS:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unsupported Gate B decision: {decision}.")
        if decision in {"denied", "isolated", "flagged"} and not reason:
            raise Layer3WorkbenchError(
                "invalid_material_candidate",
                f"Decision '{decision}' requires an operator reason.",
                blocked_fields=["candidate_decisions.operator_reason"],
            )
        decision_basis = raw.get("decision_basis") if isinstance(raw.get("decision_basis"), dict) else {}
        if source_class == SOURCE_INTAKE_SOURCE_FAMILY:
            try:
                validate_source_intake_gate_b_decision_basis(
                    db,
                    candidate_id=candidate_id,
                    decision_basis=decision_basis,
                )
            except SourceIntakeError as exc:
                raise Layer3WorkbenchError(
                    exc.code,
                    exc.message,
                    status="conflict" if exc.http_status == 409 else "blocked",
                    http_status=exc.http_status,
                    blocked_fields=exc.details.get("blocked_fields")
                    or ["candidate_decisions.decision_basis"],
                    next_allowed_actions=["refresh_source_intake_material_preview"],
                ) from exc
        source_identity = decision_basis.get("source_identity") if isinstance(decision_basis.get("source_identity"), dict) else {}
        source_provenance = (
            decision_basis.get("source_provenance") if isinstance(decision_basis.get("source_provenance"), dict) else {}
        )
        payload_basis = decision_basis.get("payload") if isinstance(decision_basis.get("payload"), dict) else {}
        load_summary = decision_basis.get("load_summary") if isinstance(decision_basis.get("load_summary"), dict) else {}
        material_preview_basis = gate_b_material_candidate_basis_from_decision(
            candidate_id=candidate_id,
            source_class=source_class,
            decision_basis=decision_basis,
        )
        material_candidate_bases.append(material_preview_basis)
        decisions.append(
            {
                "candidate_id": candidate_id,
                "source_class": source_class,
                "decision": decision,
                "operator_reason": reason,
                "decision_basis": _json_clone(decision_basis),
                "material_preview_basis": _json_clone(material_preview_basis),
                "source_identity": _json_clone(source_identity),
                "source_provenance": _json_clone(source_provenance),
                "payload": _json_clone(payload_basis),
                "load_summary": _json_clone(load_summary),
            }
        )

    approved = [item for item in decisions if item["decision"] == "approved"]
    material_preview_hash = compute_material_preview_hash(material_candidate_bases)
    if supplied_material_preview_hash and supplied_material_preview_hash != material_preview_hash:
        raise Layer3WorkbenchError(
            "material_preview_mismatch",
            "material_preview_hash does not match the submitted Gate B candidate decisions.",
            status="conflict",
            http_status=409,
            blocked_fields=["material_preview_hash", "candidate_decisions"],
            next_allowed_actions=["refresh_material_preview"],
        )
    decision_manifest = build_candidate_decision_manifest(decisions)
    gate_b_decision_manifest_id = build_gate_b_decision_manifest_id(decision_manifest)

    def existing_gate_b_response(existing_session: L3Session, existing_record: dict[str, Any]) -> dict[str, Any]:
        existing_manifest = db.get(L3SelectionManifest, existing_session.selection_manifest_id)
        if existing_manifest is None:
            raise Layer3WorkbenchError(
                "gate_b_idempotency_state_inconsistent",
                f"Layer 3 session '{existing_session.session_id}' is missing its selection manifest.",
                status="conflict",
                http_status=409,
            )
        if existing_manifest.session_id != existing_session.session_id:
            raise Layer3WorkbenchError(
                "selection_manifest_mismatch",
                "A matching Gate B idempotency record points at a manifest owned by a different session.",
                status="conflict",
                http_status=409,
                blocked_fields=["selection_manifest_id"],
                next_allowed_actions=["inspect_session_manifest_state"],
            )
        existing_decision_manifest = (existing_session.operator_context_json or {}).get(
            "layer3_gate_b_decision_manifest_v1"
        )
        if (
            not isinstance(existing_decision_manifest, dict)
            or build_gate_b_decision_manifest_id(existing_decision_manifest) != gate_b_decision_manifest_id
            or str(existing_record.get("gate_b_decision_manifest_id") or "") != gate_b_decision_manifest_id
        ):
            raise Layer3WorkbenchError(
                "gate_b_idempotency_state_inconsistent",
                f"Layer 3 session '{existing_session.session_id}' has inconsistent Gate B idempotency state.",
                status="conflict",
                http_status=409,
            )
        return _gate_b_response_from_session(
            request_id=request_id,
            status="already_committed",
            session=existing_session,
            manifest=existing_manifest,
            decision_manifest=existing_decision_manifest,
        )

    existing_idempotency = find_gate_b_idempotency_session(db, client_request_id=request_id)
    if existing_idempotency is not None:
        existing_session, existing_record = existing_idempotency
        if (
            str(existing_record.get("preflight_id") or "") == preflight_id
            and str(existing_record.get("source_set_id") or "") == source_set_id
            and str(existing_record.get("material_preview_id") or "") == material_preview_id
            and str(existing_record.get("material_preview_hash") or material_preview_hash) == material_preview_hash
            and str(existing_record.get("gate_b_decision_manifest_id") or "") == gate_b_decision_manifest_id
        ):
            return existing_gate_b_response(existing_session, existing_record)
        raise Layer3WorkbenchError(
            "idempotency_conflict",
            "client_request_id already committed Gate B for different material decisions.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )

    def existing_claim_response(existing_claim) -> dict[str, Any]:
        if gate_b_idempotency_claim_matches(
            existing_claim,
            client_request_id=request_id,
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            material_preview_id=material_preview_id,
            material_preview_hash=material_preview_hash,
            gate_b_decision_manifest_id=gate_b_decision_manifest_id,
        ):
            if existing_claim.status != GATE_B_IDEMPOTENCY_STATUS_COMMITTED:
                raise Layer3WorkbenchError(
                    "gate_b_idempotency_in_progress",
                    "client_request_id is already claiming a Gate B decision.",
                    status="conflict",
                    http_status=409,
                    blocked_fields=["client_request_id"],
                    next_allowed_actions=["retry_gate_b_decision"],
                )
            if not existing_claim.session_id:
                raise Layer3WorkbenchError(
                    "gate_b_idempotency_state_inconsistent",
                    "Committed Gate B idempotency claim is missing its session.",
                    status="conflict",
                    http_status=409,
                )
            existing_session = db.get(L3Session, existing_claim.session_id)
            if existing_session is None:
                raise Layer3WorkbenchError(
                    "gate_b_idempotency_state_inconsistent",
                    "Committed Gate B idempotency claim points at a missing session.",
                    status="conflict",
                    http_status=409,
                )
            existing_record = gate_b_idempotency_from_session(existing_session)
            if existing_record is None:
                raise Layer3WorkbenchError(
                    "gate_b_idempotency_state_inconsistent",
                    "Committed Gate B idempotency claim points at a session missing its idempotency record.",
                    status="conflict",
                    http_status=409,
                )
            return existing_gate_b_response(existing_session, existing_record)
        raise Layer3WorkbenchError(
            "idempotency_conflict",
            "client_request_id already claimed Gate B for different material decisions.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )

    preexisting_claim = find_gate_b_idempotency_claim(db, client_request_id=request_id)
    if preexisting_claim is not None:
        return existing_claim_response(preexisting_claim)

    if not approved:
        raise Layer3WorkbenchError(
            "no_approved_material",
            "At least one material candidate must be approved before Gate C.",
            status="blocked",
            next_allowed_actions=["approve_material", "revise_sources"],
        )

    gate_b_claim, existing_claim = claim_gate_b_idempotency(
        db,
        client_request_id=request_id,
        preflight_id=preflight_id,
        source_set_id=source_set_id,
        material_preview_id=material_preview_id,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
    )
    if existing_claim is not None:
        return existing_claim_response(existing_claim)
    if gate_b_claim is None:
        raise Layer3WorkbenchError(
            "gate_b_idempotency_state_persist_failed",
            "Gate B idempotency claim could not be persisted.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
            next_allowed_actions=["retry_gate_b_decision"],
        )

    counts = gate_b_counts(decisions)
    approved_dataset_version_items = [
        item
        for item in approved
        if item["source_class"] == "dataset_version" and item["source_identity"].get("dataset_version_id")
    ]
    approved_dataset_version_ids = sorted(
        str(item["source_identity"]["dataset_version_id"]) for item in approved_dataset_version_items
    )
    dataset_version_co_retrieval_group_id = (
        _stable_id(
            "gate-b-dataset-version-cohort",
            {
                "approved_candidate_ids": sorted(item["candidate_id"] for item in approved_dataset_version_items),
                "dataset_version_ids": approved_dataset_version_ids,
                "material_preview_hash": material_preview_hash,
            },
        )
        if len(approved_dataset_version_ids) > 1
        else None
    )
    manifest_items = []
    for item in approved:
        short_id = hashlib.sha256(item["candidate_id"].encode("utf-8")).hexdigest()[:12]
        manifest_items.append(
            {
                "source_plane": f"plane_{item['source_class']}_{short_id}",
                "descriptor_type": item["source_class"],
                "selector_payload": {
                    "candidate_id": item["candidate_id"],
                    "source_ref": item["decision_basis"].get("source_ref", item["candidate_id"]),
                    **(
                        {"dataset_version_id": item["source_identity"]["dataset_version_id"]}
                        if item["source_identity"].get("dataset_version_id")
                        else {}
                    ),
                },
                "selection_basis": {
                    "candidate_id": item["candidate_id"],
                    "query_basis": item["decision_basis"].get("query_basis", "operator_intent"),
                    "provenance_ref": item["decision_basis"].get("provenance_ref", "layer3-preview"),
                    "gate_b_decision": "approved",
                },
                "expansion_reason": "gate_b_approved_material",
            }
        )

    session, manifest = commit_selection(
        db,
        SessionEntryRequest(
            manifest_items=manifest_items,
            source_plane_hints={
                "preflight_id": preflight_id,
                "source_set_id": source_set_id,
                "source_classes": sorted({item["source_class"] for item in approved}),
            },
            commit_reason=str(payload.get("commit_reason") or "operator_gate_b_decision"),
            entry_route_context={"route": ROUTE, "api_root": API_ROOT, "slice": "workbench_first_slice"},
            operator_context={
                "actor": payload.get("actor") or "operator",
                "layer3_gate_b_decision_manifest_v1": decision_manifest,
                GATE_B_IDEMPOTENCY_CONTEXT_KEY: gate_b_idempotency_record(
                    client_request_id=request_id,
                    preflight_id=preflight_id,
                    source_set_id=source_set_id,
                    material_preview_id=material_preview_id,
                    material_preview_hash=material_preview_hash,
                    gate_b_decision_manifest_id=gate_b_decision_manifest_id,
                ),
            },
            summary={"current_gate": "gate_c", "gate_b_summary_v1": counts},
        ),
    )
    complete_gate_b_idempotency_claim(gate_b_claim, session=session, manifest=manifest)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    for descriptor, item in zip(descriptors, approved, strict=True):
        co_retrieval_group_id = None
        if (
            dataset_version_co_retrieval_group_id is not None
            and item["source_class"] == "dataset_version"
            and item["source_identity"].get("dataset_version_id") in approved_dataset_version_ids
        ):
            co_retrieval_group_id = dataset_version_co_retrieval_group_id
        source_identity, source_provenance, load_summary = _gate_b_snapshot_material_basis(
            item,
            mark_aps_handoff_companion=dataset_version_co_retrieval_group_id is not None,
        )
        record_retrieval_event(
            db,
            session=session,
            descriptor=descriptor,
            outcome="loaded",
            reason_code="gate_b_approved_preview_material",
            loaded_materials=[
                SnapshotMaterial(
                    source_shape=item["source_class"],
                    source_identity={
                        "candidate_id": item["candidate_id"],
                        "source_class": item["source_class"],
                        **source_identity,
                    },
                    source_provenance=source_provenance,
                    payload=(
                        item["payload"]
                        or {"candidate_id": item["candidate_id"], "source_class": item["source_class"], "decision": "approved"}
                    ),
                    load_summary=load_summary,
                    co_retrieval_group_id=co_retrieval_group_id,
                )
            ],
        )
    finalize_session(db, session=session)
    db.commit()
    return _gate_b_response_from_session(
        request_id=request_id,
        status="ok",
        session=session,
        manifest=manifest,
        decision_manifest=decision_manifest,
    )


def _load_session(db: Session, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    return session


def _latest_selection_manifest_for_session(db: Session, *, session: L3Session) -> L3SelectionManifest:
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session.session_id)
        .order_by(L3SelectionManifest.committed_at.desc())
        .first()
    )
    if manifest is None:
        raise Layer3WorkbenchError(
            "selection_manifest_missing",
            f"Layer 3 session '{session.session_id}' has no selection manifest.",
            status="conflict",
            http_status=409,
            blocked_fields=["selection_manifest_id"],
            next_allowed_actions=["inspect_session_manifest_state"],
        )
    if str(session.selection_manifest_id or "") != str(manifest.selection_manifest_id or ""):
        raise Layer3WorkbenchError(
            "selection_manifest_mismatch",
            "Layer 3 session selection_manifest_id does not match the server-owned manifest row.",
            status="conflict",
            http_status=409,
            blocked_fields=["selection_manifest_id"],
            next_allowed_actions=["inspect_session_manifest_state"],
        )
    return manifest


def _source_classes_from_latest_manifest(db: Session, session_id: str) -> list[str]:
    session = _load_session(db, session_id)
    manifest = _latest_selection_manifest_for_session(db, session=session)
    hints = manifest.source_plane_hints_json or {}
    hinted_classes = hints.get("source_classes")
    if isinstance(hinted_classes, list):
        return sorted({str(item) for item in hinted_classes if item is not None and str(item).strip()})
    items = (manifest.manifest_json or {}).get("items") or []
    return sorted(
        {
            str(item.get("descriptor_type"))
            for item in items
            if isinstance(item, dict) and str(item.get("descriptor_type") or "").strip()
        }
    )


def _gate_b_snapshot_material_basis(
    item: dict[str, Any],
    *,
    mark_aps_handoff_companion: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_identity = _json_clone(item["source_identity"])
    source_provenance = _json_clone(item["source_provenance"] or item["decision_basis"])
    load_summary = _json_clone(
        item["load_summary"] or {"loaded_records": 1, "failed_records": 0, "preview_material": True}
    )
    if item["source_class"] != "aps_content_document":
        return source_identity, source_provenance, load_summary

    source_trace = (
        source_provenance.get("source_trace") if isinstance(source_provenance.get("source_trace"), dict) else {}
    )
    aps_trace_refs = (
        source_trace.get("aps_trace_refs") if isinstance(source_trace.get("aps_trace_refs"), dict) else {}
    )
    for field in ("run_id", "target_id"):
        if aps_trace_refs.get(field) and not source_identity.get(field):
            source_identity[field] = aps_trace_refs[field]
    if not mark_aps_handoff_companion:
        return source_identity, source_provenance, load_summary
    source_provenance["analysis_admission_role"] = APS_HANDOFF_COMPANION_ANALYSIS_ROLE
    source_provenance["analysis_admission_reason"] = "mixed_dataset_version_aps_handoff_provenance_bridge"
    load_summary["analysis_admission_role"] = APS_HANDOFF_COMPANION_ANALYSIS_ROLE
    return source_identity, source_provenance, load_summary


def _stamp_api_dataset_cohort_method_authority(
    db: Session,
    *,
    analysis_sets: list[L3AnalysisSet] | tuple[L3AnalysisSet, ...],
) -> None:
    for analysis_set in analysis_sets:
        formation_basis = analysis_set.formation_basis_json or {}
        if (
            analysis_set.set_type != PASS_TYPE_ASSOCIATED_COHORT
            or formation_basis.get("analysis_modality") != "quantitative"
            or formation_basis.get("group_basis") != "same_co_retrieval_group"
        ):
            continue
        group_ids = list(analysis_set.analysis_group_ids_json or [])
        if len(group_ids) != 1:
            continue
        group = db.get(L3AnalysisGroup, group_ids[0])
        group_basis = group.typing_basis_json if group is not None else {}
        co_retrieval_group_id = str(group_basis.get("co_retrieval_group_id") or "")
        if not co_retrieval_group_id.startswith("gate-b-dataset-version-cohort-"):
            continue

        units = [
            db.get(L3AnalysisUnit, analysis_unit_id)
            for analysis_unit_id in list(analysis_set.analysis_unit_ids_json or [])
        ]
        if len(units) < 2 or any(unit is None or unit.analysis_modality != "quantitative" for unit in units):
            continue
        snapshots = [
            db.get(L3MaterialSnapshot, unit.member_snapshot_ids_json[0])
            for unit in units
            if unit is not None and len(unit.member_snapshot_ids_json or []) == 1
        ]
        if len(snapshots) != len(units):
            continue
        if any(
            snapshot is None
            or snapshot.source_shape != "dataset_version"
            or not (snapshot.source_identity_json or {}).get("dataset_version_id")
            for snapshot in snapshots
        ):
            continue

        analysis_set.formation_basis_json = {
            **formation_basis,
            "requested_method_name": "descriptive_summary",
        }


def gate_c_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for Gate C preview.", http_status=404)
    session = _load_session(db, session_id)
    gate_b_counts = gate_b_summary_from_session(session)
    source_classes = _source_classes_from_latest_manifest(db, session_id)
    commit_typing = bool(payload.get("commit_typing"))
    try:
        if commit_typing:
            result = materialize_typing_entry(db, session_id=session_id)
            _stamp_api_dataset_cohort_method_authority(db, analysis_sets=result.analysis_sets)
            db.commit()
            typing_records = [_serialize_typing_record(record) for record in result.typing_records]
            analysis_units = [_serialize_analysis_unit(unit) for unit in result.analysis_units]
            analysis_groups = [_serialize_analysis_group(group) for group in result.analysis_groups]
            analysis_sets = [_serialize_analysis_set(analysis_set) for analysis_set in result.analysis_sets]
            typing_status = "committed"
        else:
            snapshots = (
                db.query(L3MaterialSnapshot)
                .filter(L3MaterialSnapshot.session_id == session_id)
                .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
                .all()
            )
            if not snapshots:
                raise Layer3WorkbenchError(
                    "typing_not_ready",
                    f"Layer 3 session '{session_id}' has no material snapshots to type.",
                    status="blocked",
                )
            typing_records = []
            unsupported_material = []
            for snapshot in snapshots:
                projection, unsupported = _snapshot_projection(snapshot)
                if projection is not None:
                    typing_records.append(projection)
                if unsupported is not None:
                    unsupported_material.append(unsupported)
            analysis_units = [
                {
                    "analysis_unit_id": None,
                    "unit_kind": "atomic",
                    "analysis_modality": record["chosen_modality"],
                    "member_snapshot_ids": [record["material_snapshot_id"]],
                    "typing_record_ids": [],
                    "must_remain_intact": False,
                    "authoritative": False,
                }
                for record in typing_records
            ]
            analysis_groups = []
            analysis_sets = []
            typing_status = "previewed" if typing_records else "unavailable"
            return {
                **_base_response("layer3.gate_c_preview_result.v1", request_id=request_id),
                "session_id": session_id,
                "typing_records": typing_records,
                "analysis_units": analysis_units,
                "analysis_groups": analysis_groups,
                "analysis_sets": analysis_sets,
                "unsupported_material": unsupported_material,
                "override_allowed": False,
                "next_state": "first_slice_complete" if typing_records and not unsupported_material else "blocked_typing_unavailable",
                "authority_rail": _authority_rail(
                    session_id=session_id,
                    current_gate="complete" if typing_records and not unsupported_material else "gate_c",
                    persistence_mode="durable_layer3_control",
                    source_classes=source_classes,
                    counts=gate_b_counts,
                    typing_status=typing_status,
                ),
            }
    except Layer3WorkbenchError:
        raise
    except Layer3TypingEntryError as exc:
        detail = str(exc)
        code = "typing_already_materialized" if "already has" in detail else "typing_not_ready"
        raise Layer3WorkbenchError(code, detail, status="blocked", http_status=409) from exc

    return {
        **_base_response("layer3.gate_c_preview_result.v1", request_id=request_id),
        "session_id": session_id,
        "typing_records": typing_records,
        "analysis_units": analysis_units,
        "analysis_groups": analysis_groups,
        "analysis_sets": analysis_sets,
        "unsupported_material": [],
        "override_allowed": False,
        "next_state": "plan_preview_ready",
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="durable_layer3_control",
            source_classes=source_classes,
            counts=gate_b_counts,
            typing_status=typing_status,
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
    }


def gate_c_override_unavailable(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_response(
            "layer3.typing_override_unavailable.v1",
            request_id=str(payload.get("client_request_id") or uuid_str()),
            status="unavailable",
        ),
        "error_code": "override_unavailable",
        "message": "Typing override is not enabled in this first slice.",
        "recoverable": False,
        "next_allowed_actions": ["review_typing", "finish_first_slice"],
    }


def plan_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan preview.", http_status=404)

    preview_scope = str(payload.get("preview_scope") or PLAN_PREVIEW_SCOPE).strip()
    if preview_scope != PLAN_PREVIEW_SCOPE:
        raise Layer3WorkbenchError(
            "unsupported_preview_scope",
            f"Unsupported plan preview scope: {preview_scope}.",
            status="invalid",
            blocked_fields=["preview_scope"],
            next_allowed_actions=["use_owner_service_default"],
        )

    session = _load_session(db, session_id)
    gate_b_counts = gate_b_summary_from_session(session)
    readiness = _plan_preview_readiness(db, session_id=session_id)
    if not readiness["available"]:
        raise Layer3WorkbenchError(
            readiness["blocked_reason"],
            f"Layer 3 session '{session_id}' is not ready for plan preview: {readiness['blocked_reason']}.",
            status="blocked" if readiness["blocked_reason"] != "plan_already_materialized" else "conflict",
            http_status=409,
            next_allowed_actions=["commit_gate_c_typing"] if readiness["blocked_reason"] == "gate_c_not_committed" else [],
        )

    try:
        owner_preview = preview_pass_entry(db, session_id=session_id)
    except Layer3PassEntryError as exc:
        raise plan_preview_workbench_error(exc) from exc

    plan_preview_payload = {
        "schema_id": "layer3.plan_preview_payload.v1",
        "plan_version": PLAN_PREVIEW_SCOPE,
        "owner_plan_version": owner_preview.owner_service_basis["owner_plan_version"],
        "preview_hash": owner_preview.preview_hash,
        "preview_hash_contract": _plan_preview_hash_contract(),
        "approval_ready": True,
        "would_create_analysis_plan": False,
        "would_create_pass_runs": False,
        "would_execute_passes": False,
        "admitted_sets": [dict(item) for item in owner_preview.admitted_sets],
        "excluded_sets": [dict(item) for item in owner_preview.excluded_sets],
        "planned_passes": [dict(item) for item in owner_preview.planned_passes],
        "warnings": [dict(item) for item in owner_preview.warnings],
        "owner_service_basis": dict(owner_preview.owner_service_basis),
    }
    recovery_marker = _plan_revision_recovery_preview_marker(_plan_revision_recovery_from_session(session))
    if recovery_marker is not None:
        plan_preview_payload["revision_recovery"] = recovery_marker
    preview_id = _stable_id("plan-preview", {"session_id": session_id, "plan_preview": plan_preview_payload})
    return {
        **_base_response("layer3.plan_preview_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": "plan_preview_ready",
        "preview_id": preview_id,
        "preview_hash": owner_preview.preview_hash,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=owner_preview.preview_hash),
        "preview_only": True,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="preview_only",
            source_classes=_source_classes_from_plan_preview(plan_preview_payload),
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "plan_preview": plan_preview_payload,
    }


def plan_approval(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan approval.", http_status=404)

    if not bool(payload.get("operator_confirmation")):
        raise Layer3WorkbenchError(
            "operator_confirmation_required",
            "operator_confirmation must be true before plan approval is persisted.",
            status="blocked",
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_plan_approval"],
        )
    approval_scope = str(payload.get("approval_scope") or PLAN_APPROVAL_SCOPE).strip()
    if approval_scope != PLAN_APPROVAL_SCOPE:
        raise Layer3WorkbenchError(
            "unsupported_approval_scope",
            f"Unsupported plan approval scope: {approval_scope}.",
            status="invalid",
            blocked_fields=["approval_scope"],
            next_allowed_actions=["use_owner_service_default"],
        )
    forbidden = plan_approval_blocked_fields(payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan approval request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_approval_only_request"],
        )
    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    existing_control = _plan_revision_control_from_session(session)
    if existing_control is not None:
        raise Layer3WorkbenchError(
            str(existing_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )
    existing_plan = _latest_analysis_plan(db, session_id=session_id)
    if existing_plan is not None:
        if existing_plan.status == APPROVED_PLAN_CANCELLED_STATUS:
            error_code = "approved_plan_cancelled"
            message = f"Layer 3 session '{session_id}' has a cancelled approved analysis plan."
        elif bool(existing_plan.approved_by_operator):
            error_code = "plan_already_approved"
            message = f"Layer 3 session '{session_id}' already has an approved analysis plan."
        else:
            error_code = "plan_already_materialized"
            message = f"Layer 3 session '{session_id}' already has a non-approved analysis plan."
        raise Layer3WorkbenchError(
            error_code,
            message,
            status="conflict",
            http_status=409,
        )
    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    expected_preview = plan_preview(
        db,
        {
            "client_request_id": request_id,
            "session_id": session_id,
            "preview_scope": PLAN_PREVIEW_SCOPE,
        },
    )
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    if preview_id != expected_preview["preview_id"] or preview_hash != expected_preview["preview_hash"]:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan approval must reference the current server-recomputed preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    try:
        approved = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview_hash,
            source_preview_id=preview_id,
            approved_by_operator=True,
        )
        db.commit()
    except Layer3PassEntryError as exc:
        db.rollback()
        raise plan_approval_workbench_error(exc) from exc

    session = _load_session(db, session_id)
    gate_b_counts = gate_b_summary_from_session(session)
    approved_sets = [_approved_set_payload(item) for item in approved.approved_sets]
    planned_passes = [_approved_planned_pass_payload(item) for item in approved.planned_passes]
    approved_plan = {
        "schema_id": "layer3.approved_plan_payload.v1",
        "plan_version": PLAN_APPROVAL_SCOPE,
        "source_preview_id": approved.source_preview_id,
        "source_preview_hash": approved.source_preview_hash,
        "would_create_pass_runs": False,
        "would_execute_passes": False,
        "approved_sets": approved_sets,
        "excluded_sets": [dict(item) for item in approved.excluded_sets],
        "planned_passes": planned_passes,
        "warnings": [dict(item) for item in approved.warnings],
        "owner_service_basis": dict(approved.owner_service_basis),
    }
    return {
        **_base_response("layer3.plan_approval_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": "plan_approved",
        "approval_only": True,
        "execution_started": False,
        "analysis_plan_id": approved.analysis_plan.analysis_plan_id,
        "plan_status": approved.analysis_plan.status,
        "approved_by_operator": bool(approved.analysis_plan.approved_by_operator),
        "approved_at": approved.analysis_plan.approved_at.isoformat() if approved.analysis_plan.approved_at else None,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="approved_plan",
            source_classes=_source_classes_from_plan_preview(
                {
                    "admitted_sets": approved_sets,
                    "excluded_sets": approved_plan["excluded_sets"],
                }
            ),
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "approved_plan": approved_plan,
    }


def plan_revision(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan revision.", http_status=404)

    operator_decision = str(payload.get("operator_decision") or "").strip()
    if operator_decision not in PLAN_REVISION_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_revision_decision",
            f"Unsupported plan revision decision: {operator_decision or 'missing'}.",
            status="invalid",
            blocked_fields=["operator_decision"],
            next_allowed_actions=["use_supported_revision_decision"],
        )

    forbidden = plan_revision_blocked_fields(payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan revision request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_revision_control_only_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    existing_control = _plan_revision_control_from_session(session)
    if existing_control is not None:
        raise Layer3WorkbenchError(
            str(existing_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    existing_plan = _latest_analysis_plan(db, session_id=session_id)
    if existing_plan is not None:
        if bool(existing_plan.approved_by_operator):
            error_code = "plan_already_approved"
            message = f"Layer 3 session '{session_id}' already has an approved analysis plan."
        else:
            error_code = "plan_already_materialized"
            message = f"Layer 3 session '{session_id}' already has a non-approved analysis plan."
        raise Layer3WorkbenchError(error_code, message, status="conflict", http_status=409)

    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    expected_preview = plan_preview(
        db,
        {
            "client_request_id": request_id,
            "session_id": session_id,
            "preview_scope": PLAN_PREVIEW_SCOPE,
        },
    )
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    if preview_id != expected_preview["preview_id"] or preview_hash != expected_preview["preview_hash"]:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan revision must reference the current server-recomputed preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    operator_note = str(payload.get("operator_note") or "").strip()
    gate_b_counts = gate_b_summary_from_session(session)
    source_classes = _source_classes_from_plan_preview(expected_preview.get("plan_preview") or {})
    control = plan_revision_control_record(
        source_preview_id=preview_id,
        source_preview_hash=preview_hash,
        operator_decision=operator_decision,
        operator_note=operator_note,
        created_at=_utcnow_iso(),
    )
    next_state = str(control["state"])
    session.summary_json = {
        **_json_clone(session.summary_json),
        PLAN_REVISION_CONTROL_CONTEXT_KEY: control,
    }
    db.commit()

    return {
        **_base_response("layer3.plan_revision_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": next_state,
        "revision_control_only": True,
        "execution_started": False,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="plan_revision_control",
            source_classes=source_classes,
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "downstream_unavailable": list(PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE),
        "plan_revision_control": control,
    }


def plan_revision_recovery(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return _recover_plan_revision_for_preview_refresh(db, payload)


def approved_plan_cancel(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return _cancel_approved_plan_without_replacement(db, payload)


def _planned_pass_admits_associated_cohort_descriptive(
    *, planned_pass: dict[str, Any], pass_run: L3PassRun
) -> bool:
    return (
        pass_run.pass_type == PASS_TYPE_ASSOCIATED_COHORT
        and planned_pass.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT
        and planned_pass.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and planned_pass.get("selected_method_name") == "descriptive_summary"
        and planned_pass.get("requested_method_name") == "descriptive_summary"
        and planned_pass.get("requested_method_source") == COHORT_REQUESTED_METHOD_SOURCE
        and planned_pass.get("cohort_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
        and planned_pass.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
    )


def _pass_run_has_admitted_associated_cohort_execution(pass_run: L3PassRun) -> bool:
    summary = pass_run.summary_json or {}
    return (
        pass_run.pass_type == PASS_TYPE_ASSOCIATED_COHORT
        and summary.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and summary.get("selected_method_name") == "descriptive_summary"
        and summary.get("requested_method_name") == "descriptive_summary"
        and summary.get("requested_method_source") == COHORT_REQUESTED_METHOD_SOURCE
        and summary.get("cohort_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
        and summary.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
        and isinstance(summary.get("source_dataset_version_ids_json"), list)
        and isinstance(summary.get("column_map_json"), list)
    )


def _ensure_result_status_downstream_source_admitted(
    status_body: dict[str, Any],
    *,
    error_code: str,
    action_label: str,
) -> None:
    if status_body.get("pass_type") != PASS_TYPE_ASSOCIATED_COHORT:
        return
    raise Layer3WorkbenchError(
        error_code,
        f"{action_label} is not admitted for selected-pass associated-cohort result/status in this tranche.",
        status="blocked",
        http_status=409,
        next_allowed_actions=["inspect_execution_result_status"],
    )


def _associated_cohort_result_source_admitted(
    *,
    status_body: dict[str, Any],
    pass_run: L3PassRun,
    output_metadata_summary: dict[str, Any],
) -> bool:
    if status_body.get("pass_type") != PASS_TYPE_ASSOCIATED_COHORT:
        return False
    summary = pass_run.summary_json or {}
    source_dataset_version_ids = summary.get("source_dataset_version_ids_json")
    return bool(
        status_body.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and status_body.get("selected_method_name") == "descriptive_summary"
        and output_metadata_summary.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and output_metadata_summary.get("selected_method_name") == "descriptive_summary"
        and output_metadata_summary.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
        and output_metadata_summary.get("dataset_version_id") == summary.get("dataset_version_id")
        and output_metadata_summary.get("source_dataset_version_ids") == source_dataset_version_ids
        and output_metadata_summary.get("cohort_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
        and output_metadata_summary.get("requested_method_name") == "descriptive_summary"
        and output_metadata_summary.get("requested_method_source") == COHORT_REQUESTED_METHOD_SOURCE
        and _pass_run_has_admitted_associated_cohort_execution(pass_run)
    )


def _ensure_result_review_source_admitted(
    *,
    status_body: dict[str, Any],
    pass_run: L3PassRun,
    output_metadata_summary: dict[str, Any],
) -> None:
    if status_body.get("pass_type") != PASS_TYPE_ASSOCIATED_COHORT:
        return
    if _associated_cohort_result_source_admitted(
        status_body=status_body,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
    ):
        return
    raise Layer3WorkbenchError(
        "associated_cohort_result_review_not_admitted",
        "Execution result-review is admitted only for exact selected-pass descriptive associated-cohort result/status output.",
        status="blocked",
        http_status=409,
        next_allowed_actions=["inspect_execution_result_status"],
    )


def _raise_if_qualitative_aps_downstream_not_admitted(
    *,
    status_body: dict[str, Any],
    action_label: str,
    error_code: str,
) -> None:
    if status_body.get("engine_family") != ENGINE_FAMILY_QUAL_APS_DOCUMENT:
        return
    raise Layer3WorkbenchError(
        error_code,
        f"{action_label} is not admitted for the single APS-document qualitative execution slice.",
        status="blocked",
        http_status=409,
        next_allowed_actions=["inspect_execution_result_status"],
    )


def _raise_qualitative_aps_package_review_preview_not_admitted(
    reason: str,
    *,
    blocked_fields: list[str] | None = None,
) -> None:
    raise Layer3WorkbenchError(
        "qualitative_aps_package_review_preview_not_admitted",
        f"Qualitative APS package-review preview is not admitted for this authority basis: {reason}.",
        status="blocked",
        http_status=409,
        blocked_fields=blocked_fields or [],
        next_allowed_actions=["inspect_execution_result_status", "record_approved_execution_result_review"],
    )


def _qualitative_aps_package_review_candidate_projection() -> list[dict[str, Any]]:
    return [
        {
            "package_kind": package_kind,
            "preview_only": True,
            "package_commit_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "readiness_reason": (
                "candidate descriptor is preview-only until qualitative APS package "
                "construction is separately frozen"
            ),
        }
        for package_kind in PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS
    ]


def _read_qualitative_aps_package_output_payload(output_ref: Any) -> dict[str, Any]:
    output_ref_text = str(output_ref or "").strip()
    if not output_ref_text:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload ref is missing",
            blocked_fields=["output_payload_ref"],
        )
    output_path = Path(output_ref_text)
    if not output_path.exists() or not output_path.is_file():
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload ref is not readable",
            blocked_fields=["output_payload_ref"],
        )
    try:
        output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload is malformed",
            blocked_fields=["output_payload_ref"],
        )
    if not isinstance(output_payload, dict):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload is not an object",
            blocked_fields=["output_payload_ref"],
        )
    return output_payload


def _qualitative_aps_package_preview_mismatches(
    *,
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[str]:
    return [
        field
        for field, expected_value in expected.items()
        if actual.get(field) != expected_value
    ]


def _qualitative_aps_output_hash(output_payload: dict[str, Any]) -> str | None:
    output_hash = str(output_payload.get("output_hash") or "").strip()
    if not output_hash:
        return None
    hash_basis = {key: value for key, value in output_payload.items() if key != "output_hash"}
    return output_hash if output_hash == _stable_hash(hash_basis) else None


def _qualitative_aps_package_review_preview_hash(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    preview_id: str,
    preview_hash: str,
    result_review_record_ref: str | None,
    output_payload_ref: Any,
    qualitative_basis: dict[str, Any],
) -> str:
    return _stable_id(
        "l3-qual-aps-package-preview",
        {
            "schema_id": "layer3.qual_aps_package_review_preview_hash.v1",
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "preview_id": preview_id,
            "preview_hash": preview_hash,
            "result_review_record_ref": result_review_record_ref,
            "output_payload_ref": output_payload_ref,
            "output_payload_hash": qualitative_basis["output_payload_hash"],
            "content_id": qualitative_basis["content_id"],
            "content_contract_id": qualitative_basis["content_contract_id"],
            "chunking_contract_id": qualitative_basis["chunking_contract_id"],
            "material_snapshot_id": qualitative_basis["material_snapshot_id"],
            "analysis_unit_id": qualitative_basis["analysis_unit_id"],
            "analysis_set_id": qualitative_basis["analysis_set_id"],
            "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        },
    )


def _qualitative_aps_negative_capability_flags() -> dict[str, bool]:
    return {
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_retrieval_enabled": False,
        "hidden_llm_planning_enabled": False,
        "full_mockup_enabled": False,
        "rendered_ui_authority_enabled": False,
        "auth_security_behavior_changed": False,
    }


def _qualitative_aps_package_payload_extras(
    *,
    qualitative_basis: dict[str, Any],
    output_metadata_summary: dict[str, Any],
    package_review_preview_hash: str,
    result_review_state: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    output_payload = _json_clone(qualitative_basis["output_payload"])
    chunk_summary = _json_clone(output_payload.get("chunk_summary") or {})
    document_identity = _json_clone(output_payload.get("document_identity") or {})
    source_authority = {
        "schema_id": "layer3.qual_aps_package_source_authority.v1",
        "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
        "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
        "method": QUAL_APS_METHOD_NAME,
        "source_gate": QUAL_APS_SOURCE_GATE,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        "content_id": qualitative_basis["content_id"],
        "content_contract_id": qualitative_basis["content_contract_id"],
        "chunking_contract_id": qualitative_basis["chunking_contract_id"],
        "material_snapshot_id": qualitative_basis["material_snapshot_id"],
        "analysis_unit_id": qualitative_basis["analysis_unit_id"],
        "analysis_set_id": qualitative_basis["analysis_set_id"],
        "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
        "output_payload_hash": qualitative_basis["output_payload_hash"],
        "package_review_preview_hash": package_review_preview_hash,
        "chunk_count": qualitative_basis["chunk_count"],
        "chunk_ids": _json_clone(chunk_summary.get("chunk_ids") or []),
        "chunk_hashes": _json_clone(chunk_summary.get("chunk_hashes") or []),
    }
    negative_capabilities = _qualitative_aps_negative_capability_flags()
    reviewed_items = _json_clone(result_review_state.get("reviewed_output_items") or [])
    return {
        PACKAGE_KIND_CANONICAL_INTERNAL: {
            "qualitative_output_payload": output_payload,
            "qualitative_source_authority": _json_clone(source_authority),
            "negative_capability_flags": _json_clone(negative_capabilities),
        },
        PACKAGE_KIND_USER_FACING: {
            "qualitative_summary": {
                "schema_id": "layer3.qual_aps_user_facing_package_summary.v1",
                "content_id": qualitative_basis["content_id"],
                "output_item_count": len(output_payload.get("output_items_json") or []),
                "reviewed_output_item_count": len(reviewed_items),
                "chunk_count": qualitative_basis["chunk_count"],
                "method": QUAL_APS_METHOD_NAME,
            },
            "negative_capability_flags": _json_clone(negative_capabilities),
        },
        PACKAGE_KIND_REVIEW_FACING: {
            "qualitative_source_authority": _json_clone(source_authority),
            "document_identity": document_identity,
            "chunk_trace": chunk_summary,
            "reviewed_output_items": reviewed_items,
            "negative_capability_flags": _json_clone(negative_capabilities),
        },
    }


def _require_qualitative_aps_package_review_authority(
    db: Session,
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    status_body: dict[str, Any],
    pass_run: L3PassRun,
    output_metadata_summary: dict[str, Any],
) -> dict[str, Any]:
    pass_summary = pass_run.summary_json or {}
    status_mismatches = _qualitative_aps_package_preview_mismatches(
        expected={
            "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
            "pass_type": PASS_TYPE_SINGLE_ITEM,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
            "selected_method_name": QUAL_APS_METHOD_NAME,
            "analysis_run_id": None,
        },
        actual=status_body,
    )
    if status_mismatches:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "result/status authority is not the frozen standalone APS qualitative pass",
            blocked_fields=status_mismatches,
        )

    output_mismatches = _qualitative_aps_package_preview_mismatches(
        expected={
            "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
            "pass_type": PASS_TYPE_SINGLE_ITEM,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
            "selected_method_name": QUAL_APS_METHOD_NAME,
            "source_gate": QUAL_APS_SOURCE_GATE,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
            "analysis_run_id": None,
            "dataset_version_id": None,
        },
        actual=output_metadata_summary,
    )
    if output_mismatches:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "output metadata is not the frozen standalone APS qualitative payload",
            blocked_fields=output_mismatches,
        )

    if pass_run.engine_family != ENGINE_FAMILY_QUAL_APS_DOCUMENT or pass_run.pass_type != PASS_TYPE_SINGLE_ITEM:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "selected pass run is not the frozen standalone APS qualitative pass",
            blocked_fields=["pass_run_id"],
        )

    output_payload = _read_qualitative_aps_package_output_payload(
        output_metadata_summary.get("output_payload_ref")
    )
    output_hash = _qualitative_aps_output_hash(output_payload)
    if not output_hash or output_hash != pass_summary.get("qualitative_output_hash"):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload hash does not match persisted pass-run authority",
            blocked_fields=["output_payload_ref", "output_hash"],
        )

    payload_mismatches = _qualitative_aps_package_preview_mismatches(
        expected={
            "schema_id": QUAL_APS_OUTPUT_SCHEMA_ID,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "analysis_run_id": None,
            "dataset_version_id": None,
            "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
            "pass_type": PASS_TYPE_SINGLE_ITEM,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
            "selected_method_name": QUAL_APS_METHOD_NAME,
            "source_gate": QUAL_APS_SOURCE_GATE,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        },
        actual=output_payload,
    )
    if payload_mismatches:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload identity does not match the package-preview request",
            blocked_fields=payload_mismatches,
        )

    document_identity = output_payload.get("document_identity")
    chunk_summary = output_payload.get("chunk_summary")
    if not isinstance(document_identity, dict) or not isinstance(chunk_summary, dict):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload lacks document or chunk authority",
            blocked_fields=["document_identity", "chunk_summary"],
        )
    content_id = str(document_identity.get("content_id") or "").strip()
    content_contract_id = str(document_identity.get("content_contract_id") or "").strip()
    chunking_contract_id = str(document_identity.get("chunking_contract_id") or "").strip()
    if not content_id or not content_contract_id or not chunking_contract_id:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "qualitative output payload lacks APS document contract identity",
            blocked_fields=["content_id", "content_contract_id", "chunking_contract_id"],
        )

    material_snapshot_id = str(output_payload.get("material_snapshot_id") or "").strip()
    analysis_unit_id = str(output_payload.get("analysis_unit_id") or "").strip()
    analysis_set_id = str(output_payload.get("analysis_set_id") or "").strip()
    expected_summary = {
        "material_snapshot_id": material_snapshot_id,
        "analysis_unit_id": analysis_unit_id,
        "content_id": content_id,
        "content_contract_id": content_contract_id,
        "chunking_contract_id": chunking_contract_id,
        "selected_method_name": QUAL_APS_METHOD_NAME,
        "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
        "source_gate": QUAL_APS_SOURCE_GATE,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
    }
    summary_mismatches = _qualitative_aps_package_preview_mismatches(
        expected=expected_summary,
        actual=pass_summary,
    )
    if summary_mismatches:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "pass-run qualitative summary does not match output payload authority",
            blocked_fields=summary_mismatches,
        )

    document = (
        db.query(ApsContentDocument)
        .filter(
            ApsContentDocument.content_id == content_id,
            ApsContentDocument.content_contract_id == content_contract_id,
            ApsContentDocument.chunking_contract_id == chunking_contract_id,
        )
        .first()
    )
    if document is None:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "APS content document authority row is missing",
            blocked_fields=["content_id"],
        )

    material_snapshot = db.get(L3MaterialSnapshot, material_snapshot_id)
    analysis_unit = db.get(L3AnalysisUnit, analysis_unit_id)
    analysis_set = db.get(L3AnalysisSet, analysis_set_id)
    if (
        material_snapshot is None
        or material_snapshot.session_id != session_id
        or material_snapshot.source_shape != SOURCE_SHAPE_APS_CONTENT_DOCUMENT
        or (material_snapshot.source_identity_json or {}).get("content_id") != content_id
    ):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "material snapshot authority does not match APS qualitative output",
            blocked_fields=["material_snapshot_id"],
        )
    if (
        analysis_unit is None
        or analysis_unit.session_id != session_id
        or analysis_unit.analysis_modality != "qualitative"
        or material_snapshot_id not in list(analysis_unit.member_snapshot_ids_json or [])
    ):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "analysis unit authority does not match APS qualitative output",
            blocked_fields=["analysis_unit_id"],
        )
    if (
        analysis_set is None
        or analysis_set.session_id != session_id
        or analysis_set.set_type != "single_item"
        or analysis_unit_id not in list(analysis_set.analysis_unit_ids_json or [])
    ):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "analysis set authority does not match APS qualitative output",
            blocked_fields=["analysis_set_id"],
        )

    chunk_ids = chunk_summary.get("chunk_ids")
    chunk_hashes = chunk_summary.get("chunk_hashes")
    if not isinstance(chunk_ids, list) or not isinstance(chunk_hashes, list) or len(chunk_ids) != len(chunk_hashes):
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "chunk authority is missing or malformed",
            blocked_fields=["chunk_summary"],
        )
    chunks = _aps_content_chunks(
        db,
        content_id=content_id,
        content_contract_id=content_contract_id,
        chunking_contract_id=chunking_contract_id,
    )
    if [chunk.chunk_id for chunk in chunks] != chunk_ids or [chunk.chunk_text_sha256 for chunk in chunks] != chunk_hashes:
        _raise_qualitative_aps_package_review_preview_not_admitted(
            "chunk authority rows do not match qualitative output payload",
            blocked_fields=["chunk_ids", "chunk_hashes"],
        )

    return {
        "output_payload": output_payload,
        "output_payload_hash": output_hash,
        "content_id": content_id,
        "content_contract_id": content_contract_id,
        "chunking_contract_id": chunking_contract_id,
        "material_snapshot_id": material_snapshot_id,
        "analysis_unit_id": analysis_unit_id,
        "analysis_set_id": analysis_set_id,
        "document": document,
        "chunk_count": len(chunks),
    }


def _associated_cohort_aps_dispatch_source_admitted(
    *,
    status_body: dict[str, Any],
    pass_run: L3PassRun,
    output_metadata_summary: dict[str, Any],
) -> bool:
    return _associated_cohort_result_source_admitted(
        status_body=status_body,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
    )


def _associated_cohort_aps_dispatch_prepare_state_admitted(
    prepare_state: dict[str, Any],
) -> bool:
    source_dataset_version_ids = prepare_state.get("source_dataset_version_ids")
    return bool(
        prepare_state.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT
        and prepare_state.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and prepare_state.get("method") == "descriptive_summary"
        and prepare_state.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
        and prepare_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE
        and prepare_state.get("source_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
        and isinstance(source_dataset_version_ids, list)
        and len(source_dataset_version_ids) > 0
        and prepare_state.get("package_review_submit_schema_id")
        == COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    )


def _qualitative_aps_aps_dispatch_source_admitted(
    *,
    status_body: dict[str, Any],
    pass_run: L3PassRun,
    output_metadata_summary: dict[str, Any],
) -> bool:
    return bool(
        status_body.get("engine_family") == ENGINE_FAMILY_QUAL_APS_DOCUMENT
        and status_body.get("pass_type") == PASS_TYPE_SINGLE_ITEM
        and status_body.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        and status_body.get("selected_method_name") == QUAL_APS_METHOD_NAME
        and output_metadata_summary.get("source_gate") == QUAL_APS_SOURCE_GATE
        and output_metadata_summary.get("source_shape") == SOURCE_SHAPE_APS_CONTENT_DOCUMENT
        and pass_run.engine_family == ENGINE_FAMILY_QUAL_APS_DOCUMENT
        and pass_run.pass_type == PASS_TYPE_SINGLE_ITEM
    )


def _qualitative_aps_aps_dispatch_prepare_state_admitted(
    prepare_state: dict[str, Any],
) -> bool:
    return bool(
        prepare_state.get("pass_type") == PASS_TYPE_SINGLE_ITEM
        and prepare_state.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        and prepare_state.get("method") == QUAL_APS_METHOD_NAME
        and prepare_state.get("source_gate") == QUAL_APS_SOURCE_GATE
        and prepare_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE
        and prepare_state.get("source_shape") == SOURCE_SHAPE_APS_CONTENT_DOCUMENT
        and list(prepare_state.get("source_dataset_version_ids") or []) == []
        and prepare_state.get("package_review_submit_schema_id")
        == QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        and bool(str(prepare_state.get("content_id") or "").strip())
        and bool(str(prepare_state.get("content_contract_id") or "").strip())
        and bool(str(prepare_state.get("chunking_contract_id") or "").strip())
        and bool(str(prepare_state.get("material_snapshot_id") or "").strip())
        and bool(str(prepare_state.get("analysis_unit_id") or "").strip())
        and bool(str(prepare_state.get("analysis_set_id") or "").strip())
        and bool(str(prepare_state.get("output_payload_ref") or "").strip())
        and bool(str(prepare_state.get("output_payload_hash") or "").strip())
    )


def _qualitative_aps_external_export_submit_state_admitted(
    submit_state: dict[str, Any],
    *,
    qualitative_basis: dict[str, Any] | None,
    payload_refs: list[str],
) -> bool:
    if qualitative_basis is None:
        return False
    authority_basis = submit_state.get("authority_basis")
    if not isinstance(authority_basis, dict):
        return False
    identity_matches = all(
        str(authority_basis.get(field) or "") == str(qualitative_basis.get(field) or "")
        for field in (
            "content_id",
            "content_contract_id",
            "chunking_contract_id",
            "material_snapshot_id",
            "analysis_unit_id",
            "analysis_set_id",
            "output_payload_hash",
        )
    )
    return bool(
        submit_state.get("pass_type") == PASS_TYPE_SINGLE_ITEM
        and submit_state.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        and submit_state.get("method") == QUAL_APS_METHOD_NAME
        and submit_state.get("source_gate") == QUAL_APS_SOURCE_GATE
        and submit_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE
        and submit_state.get("source_shape") == SOURCE_SHAPE_APS_CONTENT_DOCUMENT
        and list(submit_state.get("source_dataset_version_ids") or []) == []
        and submit_state.get("package_review_submit_schema_id")
        == QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        and list(submit_state.get("payload_refs") or []) == payload_refs
        and bool(str(authority_basis.get("output_payload_ref") or "").strip())
        and identity_matches
    )


def _associated_cohort_readiness_submit_state_admitted(
    submit_state: dict[str, Any],
    *,
    output_metadata_summary: dict[str, Any],
) -> bool:
    source_dataset_version_ids = submit_state.get("source_dataset_version_ids")
    return bool(
        submit_state.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT
        and submit_state.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and submit_state.get("method") == "descriptive_summary"
        and submit_state.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
        and submit_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE
        and submit_state.get("source_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
        and isinstance(source_dataset_version_ids, list)
        and len(source_dataset_version_ids) > 0
        and source_dataset_version_ids == list(output_metadata_summary.get("source_dataset_version_ids") or [])
    )


def execution_selection(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for execution selection.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_execution_selection"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_selection_fields",
            f"Execution selection is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_selection_request"],
        )

    forbidden = execution_selection_blocked_fields(payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "analysis_execution_not_admitted",
            f"Execution selection request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_selection_only_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)

    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == PLAN_STATUS_APPROVED,
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]

    existing_selection = _execution_selection_from_session(session)
    existing_pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    if existing_selection is not None:
        stored_pass_run_ids = list(existing_selection.get("pass_run_ids_json") or [])
        existing_pass_run_ids = [pass_run.pass_run_id for pass_run in existing_pass_runs]
        if stored_pass_run_ids != existing_pass_run_ids:
            raise Layer3WorkbenchError(
                "execution_selection_inconsistent",
                f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
                status="conflict",
                http_status=409,
            )
        if str(existing_selection.get("client_request_id") or "") == request_id:
            if (
                str(existing_selection.get("analysis_plan_id") or "") == analysis_plan_id
                and str(existing_selection.get("source_preview_id") or "") == preview_id
                and str(existing_selection.get("source_preview_hash") or "") == preview_hash
            ):
                return _execution_selection_response(
                    request_id=request_id,
                    status="already_selected",
                    session_id=session_id,
                    analysis_plan_id=analysis_plan_id,
                    preview_id=preview_id,
                    preview_hash=preview_hash,
                    pass_runs=existing_pass_runs,
                )
            raise Layer3WorkbenchError(
                "idempotency_conflict",
                "client_request_id already selected execution for a different approved plan or preview identity.",
                status="conflict",
                http_status=409,
                blocked_fields=["client_request_id"],
            )
        raise Layer3WorkbenchError(
            "execution_selection_already_exists",
            f"Layer 3 session '{session_id}' already has an execution selection.",
            status="conflict",
            http_status=409,
        )
    if existing_pass_runs:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Execution selection must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Execution selection must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    approved_set_ids = [str(item) for item in (approved_plan.analysis_set_ids_json or []) if str(item)]
    planned_passes = [item for item in (plan_json.get("planned_passes_json") or []) if isinstance(item, dict)]
    if not approved_set_ids or not planned_passes:
        raise Layer3WorkbenchError(
            "no_admissible_plan",
            f"Layer 3 session '{session_id}' has no approved analysis sets for execution selection.",
            status="blocked",
            http_status=409,
        )

    planned_by_set_id = {str(item.get("analysis_set_id") or ""): item for item in planned_passes}
    selected_planned_passes: list[dict[str, Any]] = []
    for analysis_set_id in approved_set_ids:
        planned_pass = planned_by_set_id.get(analysis_set_id)
        if planned_pass is None:
            raise Layer3WorkbenchError(
                "approved_plan_malformed",
                f"Approved plan '{analysis_plan_id}' is missing a planned pass for analysis set '{analysis_set_id}'.",
                status="conflict",
                http_status=409,
            )
        if not str(planned_pass.get("pass_type") or "").strip():
            raise Layer3WorkbenchError(
                "approved_plan_malformed",
                f"Approved plan '{analysis_plan_id}' has a planned pass without pass_type.",
                status="conflict",
                http_status=409,
            )
        selected_planned_passes.append(planned_pass)

    selected_at = _utcnow_iso()
    pass_runs: list[L3PassRun] = []
    for planned_pass in selected_planned_passes:
        pass_run_id = uuid_str()
        pass_run = L3PassRun(
            pass_run_id=pass_run_id,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            analysis_set_id=str(planned_pass.get("analysis_set_id")),
            pass_type=str(planned_pass.get("pass_type")),
            engine_family=str(planned_pass.get("engine_family") or "wrapped_quantitative_analysis"),
            status=PASS_STATUS_SELECTED_NOT_STARTED,
            started_at=None,
            completed_at=None,
            input_payload_ref=f"layer3://execution-selection/{pass_run_id}/input",
            output_payload_ref=None,
            summary_json={
                "schema_id": "layer3.pass_run_shell_summary.v1",
                "execution_selection_schema_id": EXECUTION_SELECTION_SCHEMA_ID,
                "selection_state": EXECUTION_SELECTION_STATE,
                "client_request_id": request_id,
                "analysis_plan_id": analysis_plan_id,
                "source_preview_id": preview_id,
                "source_preview_hash": preview_hash,
                "execution_started": False,
                "analysis_run_id": None,
                "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
                "planned_pass": _json_clone(planned_pass),
                "selected_at": selected_at,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        pass_runs.append(pass_run)

    db.flush()
    session.summary_json = {
        **_json_clone(session.summary_json),
        "execution_selection": {
            "schema_id": EXECUTION_SELECTION_STATE_SCHEMA_ID,
            "state": EXECUTION_SELECTION_STATE,
            "client_request_id": request_id,
            "analysis_plan_id": analysis_plan_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "pass_run_ids_json": [pass_run.pass_run_id for pass_run in pass_runs],
            "pass_run_count": len(pass_runs),
            "execution_started": False,
            "analysis_run_ids_json": [],
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
            "operator_reason_recorded": bool(str(payload.get("operator_reason") or "").strip()),
            "selected_at": selected_at,
        },
    }
    db.commit()

    return _execution_selection_response(
        request_id=request_id,
        status=PASS_STATUS_SELECTED_NOT_STARTED,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_runs=pass_runs,
    )


def analysis_execution_start(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for analysis execution start.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_analysis_execution_start"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_analysis_execution_start_fields",
            f"Analysis execution start is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_analysis_execution_start_request"],
        )

    blocked_payload_fields = analysis_execution_start_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "analysis_execution_start_scope_not_admitted",
            f"Analysis execution start request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_single_pass_execution_start_request"],
        )
    execution_mode = str(payload.get("execution_mode") or "synchronous_single_pass").strip()
    if execution_mode != "synchronous_single_pass":
        raise Layer3WorkbenchError(
            "unsupported_execution_mode",
            "This Layer 3 tranche admits only synchronous_single_pass execution start.",
            status="invalid",
            blocked_fields=["execution_mode"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == PLAN_STATUS_APPROVED,
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]
    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Analysis execution start must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Analysis execution start must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    selection = _execution_selection_from_session(session)
    if selection is None:
        raise Layer3WorkbenchError(
            "execution_selection_required",
            "Analysis execution start requires a prior execution selection.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["submit_execution_selection"],
        )
    if (
        str(selection.get("analysis_plan_id") or "") != analysis_plan_id
        or str(selection.get("source_preview_id") or "") != preview_id
        or str(selection.get("source_preview_hash") or "") != preview_hash
    ):
        raise Layer3WorkbenchError(
            "execution_selection_mismatch",
            "Execution selection does not match the supplied approved plan preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id", "preview_id", "preview_hash"],
        )

    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    stored_pass_run_ids = [str(item) for item in (selection.get("pass_run_ids_json") or [])]
    actual_pass_run_ids = [pass_run.pass_run_id for pass_run in pass_runs]
    if stored_pass_run_ids != actual_pass_run_ids:
        raise Layer3WorkbenchError(
            "execution_selection_inconsistent",
            f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
            status="conflict",
            http_status=409,
        )
    if pass_run_id not in stored_pass_run_ids:
        raise Layer3WorkbenchError(
            "pass_run_not_selected",
            "Analysis execution start may execute only a pass run from the current execution selection.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    if any(pass_run.status == PASS_STATUS_RUNNING and pass_run.pass_run_id != pass_run_id for pass_run in pass_runs):
        raise Layer3WorkbenchError(
            "analysis_execution_already_running",
            "Another selected pass run is already running for this session.",
            status="conflict",
            http_status=409,
        )

    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if pass_run is None:
        raise Layer3WorkbenchError("pass_run_not_found", f"Layer 3 pass run '{pass_run_id}' was not found.", http_status=404)
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "pass_run_mismatch",
            "Analysis execution start pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    pass_summary = pass_run.summary_json or {}
    if str(pass_summary.get("source_preview_id") or "") != preview_id or str(pass_summary.get("source_preview_hash") or "") != preview_hash:
        raise Layer3WorkbenchError(
            "pass_run_preview_mismatch",
            "Selected pass run does not match the supplied preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
        )
    planned_pass = pass_summary.get("planned_pass")
    if not isinstance(planned_pass, dict):
        raise Layer3WorkbenchError(
            "selected_pass_malformed",
            "Selected pass run is missing its approved planned-pass payload.",
            status="conflict",
            http_status=409,
        )
    qualitative_aps_pass = is_single_aps_doc_qualitative_planned_pass(
        pass_run=pass_run,
        planned_pass=planned_pass,
    )
    wrapped_quantitative_pass = (
        pass_run.engine_family == ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS
        and str(planned_pass.get("engine_family") or "") == ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS
    )
    if not wrapped_quantitative_pass and not qualitative_aps_pass:
        raise Layer3WorkbenchError(
            "unsupported_analysis_execution_engine",
            "This execution-start slice admits only wrapped quantitative pass runs or the frozen single APS-document qualitative pass.",
            status="conflict",
            http_status=409,
        )
    planned_pass_type = str(planned_pass.get("pass_type") or pass_run.pass_type)
    if qualitative_aps_pass:
        if planned_pass_type != PASS_TYPE_SINGLE_ITEM:
            raise Layer3WorkbenchError(
                "unsupported_analysis_execution_source_breadth",
                "Single APS-document qualitative execution admits only one selected single-item pass run.",
                status="conflict",
                http_status=409,
            )
    elif planned_pass_type not in {PASS_TYPE_SINGLE_ITEM, PASS_TYPE_ASSOCIATED_COHORT}:
        raise Layer3WorkbenchError(
            "unsupported_analysis_execution_source_breadth",
            "This execution-start slice admits only selected single-item pass runs or exact descriptive associated-cohort pass runs.",
            status="conflict",
            http_status=409,
        )

    existing_start = _analysis_execution_start_from_pass_run(pass_run)
    if existing_start is not None:
        if str(existing_start.get("client_request_id") or "") == request_id:
            status = "already_completed" if pass_run.status in {PASS_STATUS_COMPLETED, PASS_STATUS_COMPLETED_WITH_WARNINGS} else pass_run.status
            return _analysis_execution_start_response(
                request_id=request_id,
                status=status,
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                pass_run=pass_run,
            )
        raise Layer3WorkbenchError(
            "analysis_execution_already_started",
            "Selected pass run already has analysis execution-start state from a different request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    if pass_run.status != PASS_STATUS_SELECTED_NOT_STARTED or _pass_run_analysis_run_id(pass_run):
        raise Layer3WorkbenchError(
            "pass_run_not_selected_not_started",
            "Analysis execution start requires a selected_not_started pass run with no analysis_run_id.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    try:
        if qualitative_aps_pass:
            execute_single_aps_doc_qualitative_pass(
                db,
                pass_run=pass_run,
                planned_pass=planned_pass,
                client_request_id=request_id,
            )
        else:
            execute_selected_pass_run(
                db,
                pass_run=pass_run,
                planned_pass=planned_pass,
                client_request_id=request_id,
            )
    except (Layer3PassEntryError, Layer3QualApsExecutionError) as exc:
        raise analysis_execution_start_workbench_error(exc) from exc

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "analysis_execution_start_inconsistent",
            "Analysis execution start could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    analysis_run_ids = [value for item in pass_runs if (value := _pass_run_analysis_run_id(item))]
    execution_state = _execution_state_for_pass_runs(pass_runs)
    completed_at = pass_run.completed_at.isoformat() if pass_run.completed_at else None
    started_at = pass_run.started_at.isoformat() if pass_run.started_at else None
    session.summary_json = {
        **_json_clone(session.summary_json),
        "execution_selection": {
            **_json_clone(_execution_selection_from_session(session) or selection),
            "state": execution_state,
            "execution_started": any(_pass_run_execution_started(item) for item in pass_runs),
            "analysis_run_ids_json": analysis_run_ids,
            "pass_run_statuses_json": {item.pass_run_id: item.status for item in pass_runs},
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        },
        "analysis_execution_start": {
            "schema_id": ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
            "client_request_id": request_id,
            "state": execution_state,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": _pass_run_analysis_run_id(pass_run),
            "pass_run_status": pass_run.status,
            "output_payload_ref": pass_run.output_payload_ref,
            "downstream_unavailable": list(ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE),
            "operator_reason_recorded": bool(str(payload.get("operator_reason") or "").strip()),
            "started_at": started_at,
            "completed_at": completed_at,
        },
    }
    db.commit()

    return _analysis_execution_start_response(
        request_id=request_id,
        status=pass_run.status,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_run=pass_run,
    )


def execution_result_status(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    request_id = str(payload.get("client_request_id") or "").strip() or None
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    operator_view_mode = str(payload.get("operator_view_mode") or "status_only").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_result_status_fields",
            f"Execution result/status request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_result_status_request"],
        )

    blocked_payload_fields = execution_result_status_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "execution_result_status_scope_not_admitted",
            f"Execution result/status request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_status_only_execution_result_status_request"],
        )
    if operator_view_mode != "status_only":
        raise Layer3WorkbenchError(
            "unsupported_execution_result_status_view_mode",
            "This Layer 3 tranche admits only status_only result/status inspection.",
            status="invalid",
            blocked_fields=["operator_view_mode"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == PLAN_STATUS_APPROVED,
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]
    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Execution result/status must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Execution result/status must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    selection = _execution_selection_from_session(session)
    if selection is None:
        raise Layer3WorkbenchError(
            "execution_selection_required",
            "Execution result/status requires a prior execution selection.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["submit_execution_selection"],
        )
    if (
        str(selection.get("analysis_plan_id") or "") != analysis_plan_id
        or str(selection.get("source_preview_id") or "") != preview_id
        or str(selection.get("source_preview_hash") or "") != preview_hash
    ):
        raise Layer3WorkbenchError(
            "execution_selection_mismatch",
            "Execution selection does not match the supplied approved plan preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id", "preview_id", "preview_hash"],
        )

    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    stored_pass_run_ids = [str(item) for item in (selection.get("pass_run_ids_json") or [])]
    actual_pass_run_ids = [pass_run.pass_run_id for pass_run in pass_runs]
    if stored_pass_run_ids != actual_pass_run_ids:
        raise Layer3WorkbenchError(
            "execution_selection_inconsistent",
            f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
            status="conflict",
            http_status=409,
        )
    if pass_run_id not in stored_pass_run_ids:
        raise Layer3WorkbenchError(
            "pass_run_not_selected",
            "Execution result/status may inspect only a pass run from the current execution selection.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).first()
    if pass_run is None:
        raise Layer3WorkbenchError("pass_run_not_found", f"Layer 3 pass run '{pass_run_id}' was not found.", http_status=404)
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "pass_run_mismatch",
            "Execution result/status pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    pass_summary = pass_run.summary_json or {}
    if str(pass_summary.get("source_preview_id") or "") != preview_id or str(pass_summary.get("source_preview_hash") or "") != preview_hash:
        raise Layer3WorkbenchError(
            "pass_run_preview_mismatch",
            "Selected pass run does not match the supplied preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
        )
    planned_pass = pass_summary.get("planned_pass")
    if not isinstance(planned_pass, dict):
        raise Layer3WorkbenchError(
            "selected_pass_malformed",
            "Selected pass run is missing its approved planned-pass payload.",
            status="conflict",
            http_status=409,
        )
    qualitative_aps_pass = is_single_aps_doc_qualitative_planned_pass(
        pass_run=pass_run,
        planned_pass=planned_pass,
    )
    wrapped_quantitative_pass = (
        pass_run.engine_family == ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS
        and str(planned_pass.get("engine_family") or "") == ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS
    )
    if not wrapped_quantitative_pass and not qualitative_aps_pass:
        raise Layer3WorkbenchError(
            "unsupported_execution_result_status_engine",
            "This result/status slice admits only wrapped quantitative pass runs or the frozen single APS-document qualitative pass.",
            status="conflict",
            http_status=409,
        )
    planned_pass_type = str(planned_pass.get("pass_type") or pass_run.pass_type)
    associated_cohort_descriptive = _planned_pass_admits_associated_cohort_descriptive(
        planned_pass=planned_pass,
        pass_run=pass_run,
    )
    if qualitative_aps_pass:
        if planned_pass_type != PASS_TYPE_SINGLE_ITEM:
            raise Layer3WorkbenchError(
                "unsupported_execution_result_status_source_breadth",
                "Single APS-document qualitative result/status admits only one selected single-item pass run.",
                status="conflict",
                http_status=409,
            )
    elif planned_pass_type != PASS_TYPE_SINGLE_ITEM and not associated_cohort_descriptive:
        raise Layer3WorkbenchError(
            "unsupported_execution_result_status_source_breadth",
            "This result/status slice admits only selected single-item pass runs or exact descriptive associated-cohort pass runs.",
            status="conflict",
            http_status=409,
        )

    start_state = _analysis_execution_start_from_pass_run(pass_run)
    if start_state is None:
        raise Layer3WorkbenchError(
            "analysis_execution_start_required",
            "Execution result/status requires prior selected-pass analysis execution-start state.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["submit_analysis_execution_start"],
        )
    if associated_cohort_descriptive and not _pass_run_has_admitted_associated_cohort_execution(pass_run):
        raise Layer3WorkbenchError(
            "associated_cohort_execution_state_not_admitted",
            "Execution result/status may inspect associated cohorts only after admitted descriptive selected-pass execution-start state.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    if pass_run.status not in EXECUTION_RESULT_STATUS_TERMINAL_PASS_STATUSES:
        raise Layer3WorkbenchError(
            "pass_run_not_terminal",
            "Execution result/status requires a terminal selected pass run.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    analysis_run_id = _pass_run_analysis_run_id(pass_run)
    if supplied_analysis_run_id and supplied_analysis_run_id != str(analysis_run_id or ""):
        raise Layer3WorkbenchError(
            "analysis_run_mismatch",
            "Supplied analysis_run_id does not match the selected pass run.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_run_id"],
        )
    analysis_run = db.get(AnalysisRun, analysis_run_id) if analysis_run_id else None
    if analysis_run_id and analysis_run is None:
        raise Layer3WorkbenchError(
            "analysis_run_not_found",
            "Selected pass run references an analysis_run_id that is not present.",
            status="conflict",
            http_status=409,
        )

    output_summary, output_error = _output_metadata_summary(pass_run)
    if pass_run.status == PASS_STATUS_FAILED:
        response_status = "failed"
    elif output_summary is None:
        response_status = "missing_output_metadata"
    else:
        response_status = "available"

    return _execution_result_status_response(
        request_id=request_id,
        status=response_status,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_run=pass_run,
        analysis_run=analysis_run,
        output_metadata_summary=output_summary,
        output_metadata_error=output_error,
    )


def execution_result_review(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    operator_decision = str(payload.get("operator_decision") or "").strip()
    request_id = str(payload.get("client_request_id") or "").strip()
    review_notes = str(payload.get("review_notes") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("operator_decision", operator_decision),
            ("client_request_id", request_id),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_result_review_fields",
            f"Execution result-review request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_result_review_request"],
        )

    blocked_payload_fields = execution_result_review_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "execution_result_review_scope_not_admitted",
            f"Execution result-review request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_execution_result_review_request"],
        )
    if operator_decision not in EXECUTION_RESULT_REVIEW_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_execution_result_review_decision",
            "operator_decision must be approved, changes_requested, rejected, or blocked.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if operator_decision != "approved" and not review_notes:
        raise Layer3WorkbenchError(
            "review_notes_required",
            "review_notes are required for changes_requested, rejected, or blocked result-review decisions.",
            status="invalid",
            blocked_fields=["review_notes"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "execution_result_review_not_available",
            "Execution result-review requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )

    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "output_metadata_required",
            "Execution result-review requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "execution_result_review_inconsistent",
            "Execution result-review could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    _ensure_result_review_source_admitted(
        status_body=status_body,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
    )

    analysis_run_id = str(status_body.get("analysis_run_id") or "").strip() or None
    reviewed_items, unresolved_trace_count = _normalize_result_review_items(
        items=payload.get("reviewed_output_items"),
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id=analysis_run_id,
        output_metadata_summary=output_metadata_summary,
    )
    if operator_decision == "approved" and unresolved_trace_count:
        raise Layer3WorkbenchError(
            "execution_result_review_trace_unresolved",
            "Approved result-review decisions require resolved trace references for every reviewed output item.",
            status="blocked",
            http_status=409,
            blocked_fields=["reviewed_output_items"],
        )

    trace_summary = _result_review_trace_summary(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id=analysis_run_id,
        output_metadata_summary=output_metadata_summary,
        reviewed_items=reviewed_items,
        unresolved_trace_count=unresolved_trace_count,
    )
    pass_summary = pass_run.summary_json or {}
    source_dataset_version_ids = output_metadata_summary.get("source_dataset_version_ids")
    if not isinstance(source_dataset_version_ids, list):
        source_dataset_version_ids = pass_summary.get("source_dataset_version_ids_json")
    if not isinstance(source_dataset_version_ids, list):
        source_dataset_version_ids = []
    review_record_ref = _stable_id(
        "l3-result-review",
        {
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "preview_id": preview_id,
            "preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "operator_decision": operator_decision,
            "client_request_id": request_id,
            "review_notes": review_notes,
            "reviewed_output_items": reviewed_items,
        },
    )

    existing_review = _execution_result_review_from_pass_run(pass_run)
    if existing_review is not None:
        if (
            existing_review.get("client_request_id") == request_id
            and existing_review.get("review_record_ref") == review_record_ref
        ):
            return _execution_result_review_response(
                request_id=request_id,
                status="already_recorded",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                pass_run=pass_run,
                analysis_run_id=analysis_run_id,
                review_state=existing_review,
            )
        raise Layer3WorkbenchError(
            "execution_result_review_already_recorded",
            "Selected pass run already has a result-review decision.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )

    review_state = {
        "schema_id": EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
        "client_request_id": request_id,
        "review_record_ref": review_record_ref,
        "review_state": EXECUTION_RESULT_REVIEW_STATE_BY_DECISION[operator_decision],
        "operator_decision": operator_decision,
        "review_notes": review_notes or None,
        "reviewed_output_items": reviewed_items,
        "trace_summary": trace_summary,
        "unresolved_trace_count": unresolved_trace_count,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "pass_type": pass_run.pass_type,
        "engine_family": pass_run.engine_family,
        "dataset_version_id": output_metadata_summary.get("dataset_version_id") or pass_summary.get("dataset_version_id"),
        "selected_method_name": output_metadata_summary.get("selected_method_name") or pass_summary.get("selected_method_name"),
        "pass_scope": output_metadata_summary.get("pass_scope") or pass_summary.get("pass_scope"),
        "source_gate": output_metadata_summary.get("source_gate") or pass_summary.get("source_gate"),
        "source_dataset_version_ids": list(source_dataset_version_ids),
        "cohort_shape": output_metadata_summary.get("cohort_shape") or pass_summary.get("cohort_shape"),
        "requested_method_name": output_metadata_summary.get("requested_method_name") or pass_summary.get("requested_method_name"),
        "requested_method_source": output_metadata_summary.get("requested_method_source") or pass_summary.get("requested_method_source"),
        "recorded_at": _utcnow_iso(),
        "package_review_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
    }
    pass_run.summary_json = {
        **_json_clone(pass_run.summary_json or {}),
        "execution_result_review": review_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "execution_result_review": {
            "schema_id": EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
            "review_record_ref": review_record_ref,
            "review_state": review_state["review_state"],
            "operator_decision": operator_decision,
            "pass_run_id": pass_run_id,
            "analysis_plan_id": analysis_plan_id,
            "analysis_run_id": analysis_run_id,
            "pass_type": pass_run.pass_type,
            "engine_family": pass_run.engine_family,
            "dataset_version_id": review_state.get("dataset_version_id"),
            "selected_method_name": review_state.get("selected_method_name"),
            "pass_scope": review_state.get("pass_scope"),
            "source_gate": review_state.get("source_gate"),
            "source_dataset_version_ids": list(source_dataset_version_ids),
            "cohort_shape": review_state.get("cohort_shape"),
            "requested_method_name": review_state.get("requested_method_name"),
            "requested_method_source": review_state.get("requested_method_source"),
            "unresolved_trace_count": unresolved_trace_count,
            "package_review_enabled": False,
            "handoff_enabled": False,
            "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _execution_result_review_response(
        request_id=request_id,
        status="recorded",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_run=pass_run,
        analysis_run_id=analysis_run_id,
        review_state=review_state,
    )


def _dispatched_aps_handoff_package_id(dispatch_state: dict[str, Any] | None) -> str | None:
    return dispatched_package_id(
        dispatch_state,
        dispatched_state=APS_HANDOFF_DISPATCHED_STATE,
        expected_package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
    )


def _unexpected_package_kinds(
    packages: list[L3OutputPackage],
    *,
    aps_handoff_dispatch_state: dict[str, Any] | None = None,
) -> list[str]:
    return package_state_unexpected_package_kinds(
        packages,
        source_kinds=PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
        aps_handoff_dispatch_state=aps_handoff_dispatch_state,
        aps_dispatched_state=APS_HANDOFF_DISPATCHED_STATE,
        aps_package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
    )


def _active_package_downstream_unavailable(
    *,
    package_construction_state: dict[str, Any],
    package_review_submit_state: dict[str, Any],
    handoff_export_prepare_state: dict[str, Any],
    aps_handoff_dispatch_state: dict[str, Any],
    external_export_download_state: dict[str, Any],
) -> tuple[str, ...]:
    return package_state_active_downstream_unavailable(
        transitions=(
            (
                aps_handoff_dispatch_state,
                APS_HANDOFF_DISPATCHED_STATE,
                external_export_download_state,
                EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE,
            ),
            (
                handoff_export_prepare_state,
                HANDOFF_EXPORT_PREPARED_STATE,
                aps_handoff_dispatch_state,
                APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE,
            ),
            (
                package_review_submit_state,
                PACKAGE_REVIEW_APPROVED_STATE,
                handoff_export_prepare_state,
                HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
            ),
            (
                package_construction_state,
                PACKAGE_CONSTRUCTED_STATE,
                package_review_submit_state,
                PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
            ),
        ),
        default_state=package_construction_state,
        default_fallback=PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE,
    )


def _aps_handoff_package_for_session(db: Session, *, session_id: str) -> L3OutputPackage | None:
    return (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        )
        .one_or_none()
    )


def _aps_handoff_dispatch_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    preview_id: str,
    preview_hash: str,
    result_review_record_ref: str,
    package_review_preview_hash: str,
    reconciliation_record: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    dispatch_state: dict[str, Any],
) -> dict[str, Any]:
    ordered_packages = _packages_in_review_order(packages)
    qualitative_aps_dispatch = (
        dispatch_state.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        or dispatch_state.get("source_gate") == QUAL_APS_SOURCE_GATE
        or dispatch_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE
    )
    body = {
        **_base_response(
            QUAL_APS_APS_HANDOFF_DISPATCH_SCHEMA_ID
            if qualitative_aps_dispatch
            else APS_HANDOFF_DISPATCH_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": dispatch_state.get("analysis_run_id"),
        "result_review_record_ref": result_review_record_ref,
        "package_review_preview_hash": package_review_preview_hash,
        "reconciliation_record_id": reconciliation_record.reconciliation_record_id,
        "output_package_ids": [package.output_package_id for package in ordered_packages],
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": [package.payload_ref for package in ordered_packages],
        "payload_hashes": [package.payload_hash for package in ordered_packages],
        "pass_type": dispatch_state.get("pass_type"),
        "pass_scope": dispatch_state.get("pass_scope"),
        "method": dispatch_state.get("method"),
        "source_gate": dispatch_state.get("source_gate"),
        "package_construction_source_gate": dispatch_state.get("package_construction_source_gate"),
        "source_shape": dispatch_state.get("source_shape"),
        "source_dataset_version_ids": _json_clone(dispatch_state.get("source_dataset_version_ids") or []),
        "package_review_submit_schema_id": dispatch_state.get("package_review_submit_schema_id"),
        "package_review_submit_record_ref": dispatch_state["package_review_submit_record_ref"],
        "package_review_state": dispatch_state["package_review_state"],
        "prepare_record_ref": dispatch_state["prepare_record_ref"],
        "handoff_export_state": dispatch_state["handoff_export_state"],
        "handoff_export_envelope_ref": dispatch_state["handoff_export_envelope_ref"],
        "handoff_target": dispatch_state["handoff_target"],
        "export_mode": dispatch_state["export_mode"],
        "aps_handoff_target": dispatch_state["aps_handoff_target"],
        "dispatch_mode": dispatch_state["dispatch_mode"],
        "operator_decision": dispatch_state["operator_decision"],
        "decision_notes": dispatch_state.get("decision_notes"),
        "aps_handoff_state": dispatch_state["aps_handoff_state"],
        "aps_handoff_record_ref": dispatch_state["aps_handoff_record_ref"],
        "aps_output_package_id": dispatch_state["aps_output_package_id"],
        "aps_output_package_kind": dispatch_state["aps_output_package_kind"],
        "aps_bundle_ref": dispatch_state["aps_bundle_ref"],
        "aps_bundle_id": dispatch_state["aps_bundle_id"],
        "aps_schema_id": dispatch_state["aps_schema_id"],
        "source_package_refs": _json_clone(dispatch_state["source_package_refs"]),
        "source_package_hashes": _json_clone(dispatch_state["source_package_hashes"]),
        "external_export_enabled": False,
        "download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": [] if qualitative_aps_dispatch else ["prepare_external_export_download"],
        "next_state": dispatch_state["aps_handoff_state"],
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode="durable_aps_handoff_dispatch",
            downstream_unavailable=APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }
    if qualitative_aps_dispatch:
        for field in (
            "content_id",
            "content_contract_id",
            "chunking_contract_id",
            "material_snapshot_id",
            "analysis_unit_id",
            "analysis_set_id",
            "output_payload_ref",
            "output_payload_hash",
            "chunk_count",
        ):
            body[field] = _json_clone(dispatch_state.get(field))
    return body


def _package_construction_summary(
    db: Session,
    *,
    session_id: str,
    package_review_preview_state: dict[str, Any],
) -> dict[str, Any]:
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .one_or_none()
    )
    packages = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    review_packages = _review_source_packages(packages)
    aps_handoff_dispatch_state = _aps_handoff_dispatch_from_reconciliation(reconciliation)
    unexpected_package_kinds = _unexpected_package_kinds(
        packages,
        aps_handoff_dispatch_state=aps_handoff_dispatch_state,
    )
    if reconciliation is not None or packages:
        constructed = bool(
            reconciliation is not None
            and not unexpected_package_kinds
            and len(review_packages) == len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
            and {package.package_kind for package in review_packages} == set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        )
        package_review_submit = _package_review_submit_from_reconciliation(reconciliation)
        blocked_reason = None
        if not constructed:
            blocked_reason = "unexpected_package_state" if unexpected_package_kinds else "partial_package_state"
        reconciliation_summary = reconciliation.summary_json if reconciliation is not None else {}
        if not isinstance(reconciliation_summary, dict):
            reconciliation_summary = {}
        commit_summary = reconciliation_summary.get("workbench_package_commit")
        if not isinstance(commit_summary, dict):
            commit_summary = {}
        cohort_package_construction = _is_cohort_package_construction_source(reconciliation_summary.get("source_gate"))
        qualitative_package_construction = _is_qualitative_aps_package_construction_source(
            reconciliation_summary.get("source_gate")
        )
        package_review_submit_enabled = bool(
            constructed
            and package_review_submit is None
            and (
                commit_summary.get("package_review_submit_enabled", True) is True
                or cohort_package_construction
                or qualitative_package_construction
            )
        )
        if package_review_submit_enabled and cohort_package_construction:
            downstream_unavailable = list(COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE)
        elif package_review_submit_enabled and qualitative_package_construction:
            downstream_unavailable = list(QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE)
        else:
            downstream_unavailable = (
                commit_summary.get("downstream_unavailable")
                if constructed
                else list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE)
            )
        if not isinstance(downstream_unavailable, list):
            downstream_unavailable = (
                list(
                    COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
                    if cohort_package_construction
                    else QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
                    if qualitative_package_construction
                    else PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
                )
                if package_review_submit_enabled
                else list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE)
            )
        return {
            "schema_id": PACKAGE_CONSTRUCTION_COMMIT_STATE_SCHEMA_ID,
            "available": False,
            "state": PACKAGE_CONSTRUCTED_STATE if constructed else PACKAGE_COMMIT_BLOCKED_STATE,
            "blocked_reason": blocked_reason,
            "reconciliation_record_id": reconciliation.reconciliation_record_id if reconciliation is not None else None,
            "output_package_ids": [package.output_package_id for package in review_packages],
            "package_kinds": [package.package_kind for package in review_packages],
            "payload_refs": [package.payload_ref for package in review_packages],
            "unexpected_package_kinds": unexpected_package_kinds,
            "package_review_preview_hash": commit_summary.get("package_review_preview_hash"),
            "construction_basis_hash": commit_summary.get("construction_basis_hash")
            or commit_summary.get("authority_basis_hash"),
            "package_construction_source_gate": reconciliation_summary.get("source_gate"),
            "package_commit_enabled": False,
            "package_review_submit_enabled": package_review_submit_enabled,
            "handoff_enabled": False,
            "downstream_unavailable": list(downstream_unavailable),
        }
    preview_available = bool(package_review_preview_state.get("available"))
    package_commit_enabled = bool(package_review_preview_state.get("package_commit_enabled", preview_available))
    available = bool(preview_available and package_commit_enabled)
    blocked_reason = None
    if not available:
        blocked_reason = (
            "package_construction_deferred_for_associated_cohort"
            if preview_available and not package_commit_enabled
            else "package_review_preview_not_available"
        )
    return {
        "schema_id": PACKAGE_CONSTRUCTION_COMMIT_STATE_SCHEMA_ID,
        "available": available,
        "state": PACKAGE_COMMIT_READY_STATE if available else PACKAGE_COMMIT_UNAVAILABLE_STATE,
        "blocked_reason": blocked_reason,
        "reconciliation_record_id": None,
        "output_package_ids": [],
        "package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS) if available else [],
        "package_commit_enabled": available,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE),
    }


def package_review_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    request_id = str(payload.get("client_request_id") or "").strip() or None
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_package_review_preview_fields",
            f"Package-review preview request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_review_preview_request"],
        )

    blocked_payload_fields = package_review_preview_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "package_review_preview_scope_not_admitted",
            f"Package-review preview request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_read_only_package_review_preview_request"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
    }
    if request_id:
        status_payload["client_request_id"] = request_id
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "package_review_preview_result_status_unavailable",
            "Package-review preview requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "package_review_preview_output_metadata_required",
            "Package-review preview requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "package_review_preview_inconsistent",
            "Package-review preview could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    pass_summary = pass_run.summary_json or {}
    associated_cohort_preview = False
    if status_body.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT:
        associated_cohort_preview = _associated_cohort_result_source_admitted(
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        if not associated_cohort_preview:
            raise Layer3WorkbenchError(
                "associated_cohort_package_review_preview_not_admitted",
                (
                    "Package-review preview is admitted only for exact selected-pass descriptive "
                    "associated-cohort result/status output in this tranche."
                ),
                status="blocked",
                http_status=409,
                next_allowed_actions=["inspect_execution_result_status"],
            )

    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "package_review_preview_requires_approved_result_review",
            "Package-review preview requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref and supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "package_review_preview_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    review_identity = {
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
    }
    mismatched_review_fields = [
        field
        for field, expected in review_identity.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "package_review_preview_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "package_review_preview_trace_unresolved",
            "Package-review preview requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    reconciliation_count = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .count()
    )
    package_count = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .count()
    )
    if reconciliation_count or package_count:
        raise Layer3WorkbenchError(
            "package_review_preview_existing_package_state",
            (
                "Package-review preview is blocked because existing package or reconciliation rows "
                f"already exist for session '{session_id}'."
            ),
            status="conflict",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        )

    if status_body.get("engine_family") == ENGINE_FAMILY_QUAL_APS_DOCUMENT:
        qualitative_basis = _require_qualitative_aps_package_review_authority(
            db,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        package_review_preview_hash = _qualitative_aps_package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_record_ref=str(review_state.get("review_record_ref") or "") or None,
            output_payload_ref=output_metadata_summary.get("output_payload_ref"),
            qualitative_basis=qualitative_basis,
        )
        return {
            **_base_response(
                QUAL_APS_PACKAGE_REVIEW_PREVIEW_SCHEMA_ID,
                request_id=request_id,
                status="available",
            ),
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
            "package_review_preview_hash": package_review_preview_hash,
            "analysis_run_id": None,
            "result_status_available": True,
            "result_review_state": review_state.get("review_state"),
            "result_review_record_ref": review_state.get("review_record_ref"),
            "package_review_preview_enabled": True,
            "package_commit_enabled": True,
            "package_review_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "aps_handoff_enabled": False,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_url_enabled": False,
            "candidate_package_kinds": package_review_candidate_projection(
                package_commit_enabled=True,
                readiness_reason="candidate family is eligible for bounded qualitative APS package construction commit",
            ),
            "package_owner_compatibility": {
                "schema_id": "layer3.qual_aps_package_owner_compatibility.v1",
                "owner_service": "layer3_package_entry.materialize_workbench_package_commit",
                "assessment_basis": [
                    "approved_single_aps_doc_qualitative_result_review",
                    "read_only_qualitative_output_metadata",
                    "aps_document_chunk_authority",
                ],
                "materialize_package_entry_callable": False,
                "workbench_package_commit_callable": True,
                "preview_candidate_projection_compatible": True,
                "construction_compatible_with_current_workbench_state": True,
                "missing_owner_service_inputs": [],
                "selected_pass_status": pass_run.status,
                "pass_type": pass_run.pass_type,
                "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
                "source_gate": QUAL_APS_SOURCE_GATE,
                "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
                "status": "qualitative_aps_package_construction_preconditions_satisfied",
                "reason": (
                    "Standalone APS qualitative output is inspectable and eligible for the bounded "
                    "package-construction commit boundary."
                ),
            },
            "blocked_reasons": [],
            "downstream_unavailable": list(QUAL_APS_PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE),
            "next_state": PACKAGE_REVIEW_PREVIEW_READY_STATE,
            "output_metadata_summary": output_metadata_summary,
            "trace_summary": review_state.get("trace_summary"),
            "reviewed_output_item_summary": {
                "reviewed_item_count": len(review_state.get("reviewed_output_items") or []),
                "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
            },
            "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
            "pass_type": pass_run.pass_type,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
            "method": QUAL_APS_METHOD_NAME,
            "selected_method_name": QUAL_APS_METHOD_NAME,
            "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
            "source_gate": QUAL_APS_SOURCE_GATE,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
            "source_dataset_version_ids": [],
            "cohort_shape": None,
            "content_id": qualitative_basis["content_id"],
            "content_contract_id": qualitative_basis["content_contract_id"],
            "chunking_contract_id": qualitative_basis["chunking_contract_id"],
            "material_snapshot_id": qualitative_basis["material_snapshot_id"],
            "analysis_unit_id": qualitative_basis["analysis_unit_id"],
            "analysis_set_id": qualitative_basis["analysis_set_id"],
            "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
            "output_payload_hash": qualitative_basis["output_payload_hash"],
            "chunk_count": qualitative_basis["chunk_count"],
            "authority_rail": _authority_rail(
                session_id=session_id,
                current_gate="package",
                persistence_mode="read_only_qual_aps_package_review_preview",
                downstream_unavailable=QUAL_APS_PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE,
                execution_enabled=False,
                package_review_enabled=False,
            ),
        }

    compatibility = _package_owner_compatibility(
        session=session,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
        review_state=review_state,
        approved_review_state=EXECUTION_RESULT_REVIEW_APPROVED_STATE,
        associated_cohort_preview=associated_cohort_preview,
    )
    downstream_unavailable = (
        COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
        if associated_cohort_preview
        else PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
    )
    package_commit_enabled = True
    package_review_preview_hash = _package_review_preview_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        analysis_run_id=str(status_body.get("analysis_run_id") or "") or None,
        result_review_record_ref=str(review_state.get("review_record_ref") or "") or None,
        output_metadata_summary=output_metadata_summary,
    )
    return {
        **_base_response(PACKAGE_REVIEW_PREVIEW_SCHEMA_ID, request_id=request_id, status="available"),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "package_review_preview_hash": package_review_preview_hash,
        "analysis_run_id": str(status_body.get("analysis_run_id") or "") or None,
        "result_status_available": True,
        "result_review_state": review_state.get("review_state"),
        "result_review_record_ref": review_state.get("review_record_ref"),
        "package_review_preview_enabled": True,
        "package_commit_enabled": package_commit_enabled,
        "package_review_enabled": False,
        "candidate_package_kinds": package_review_candidate_projection(
            package_commit_enabled=package_commit_enabled,
        ),
        "package_owner_compatibility": compatibility,
        "blocked_reasons": [],
        "downstream_unavailable": list(downstream_unavailable),
        "next_state": PACKAGE_REVIEW_PREVIEW_READY_STATE,
        "output_metadata_summary": output_metadata_summary,
        "trace_summary": review_state.get("trace_summary"),
        "reviewed_output_item_summary": {
            "reviewed_item_count": len(review_state.get("reviewed_output_items") or []),
            "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
        },
        "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
        "pass_type": pass_run.pass_type,
        "pass_scope": output_metadata_summary.get("pass_scope"),
        "selected_method_name": output_metadata_summary.get("selected_method_name"),
        "source_gate": output_metadata_summary.get("source_gate"),
        "source_dataset_version_ids": _package_source_dataset_version_ids(
            output_metadata_summary=output_metadata_summary,
            pass_summary=pass_summary,
        ),
        "cohort_shape": output_metadata_summary.get("cohort_shape"),
        "source_shape": _package_source_shape(
            output_metadata_summary=output_metadata_summary,
            pass_summary=pass_summary,
        ),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode="read_only_package_review_preview",
            downstream_unavailable=downstream_unavailable,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def package_construction_commit(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for package construction commit.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_package_construction_commit"],
        )
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()
    supplied_package_preview_hash = str(payload.get("package_review_preview_hash") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("result_review_record_ref", supplied_review_ref),
            ("package_review_preview_hash", supplied_package_preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_package_construction_commit_fields",
            f"Package construction commit request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_construction_commit_request"],
        )

    blocked_payload_fields = package_construction_commit_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "package_construction_commit_scope_not_admitted",
            f"Package construction commit request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_package_construction_commit_request"],
        )

    expected_package_kinds = payload.get("expected_package_kinds")
    if expected_package_kinds is not None and expected_package_kinds != list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS):
        raise Layer3WorkbenchError(
            "package_construction_commit_kinds_mismatch",
            "Package construction commit admits exactly the canonical_internal, user_facing, and review_facing package kinds.",
            status="conflict",
            http_status=409,
            blocked_fields=["expected_package_kinds"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "package_construction_commit_result_status_unavailable",
            "Package construction commit requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "package_construction_commit_output_metadata_required",
            "Package construction commit requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    qualitative_aps_commit = status_body.get("engine_family") == ENGINE_FAMILY_QUAL_APS_DOCUMENT

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    analysis_plan = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.analysis_plan_id == analysis_plan_id,
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == PLAN_STATUS_APPROVED,
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .one_or_none()
    )
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    if analysis_plan is None:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Package construction commit must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )
    if pass_run is None or pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "pass_run_mismatch",
            "Package construction commit pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    associated_cohort_commit = False
    if status_body.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT:
        associated_cohort_commit = _associated_cohort_result_source_admitted(
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        if not associated_cohort_commit:
            raise Layer3WorkbenchError(
                "associated_cohort_package_construction_commit_not_admitted",
                (
                    "Package construction commit is admitted only for exact selected-pass descriptive "
                    "associated-cohort result/status output in this tranche."
                ),
                status="blocked",
                http_status=409,
                next_allowed_actions=["inspect_execution_result_status"],
            )
    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "package_construction_commit_requires_approved_result_review",
            "Package construction commit requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "package_construction_commit_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )
    mismatched_review_fields = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
        }.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "package_construction_commit_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "package_construction_commit_trace_unresolved",
            "Package construction commit requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    qualitative_basis: dict[str, Any] | None = None
    if qualitative_aps_commit:
        qualitative_basis = _require_qualitative_aps_package_review_authority(
            db,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        expected_package_preview_hash = _qualitative_aps_package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_record_ref=supplied_review_ref,
            output_payload_ref=output_metadata_summary.get("output_payload_ref"),
            qualitative_basis=qualitative_basis,
        )
    else:
        expected_package_preview_hash = _package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            analysis_run_id=str(status_body.get("analysis_run_id") or "") or None,
            result_review_record_ref=supplied_review_ref,
            output_metadata_summary=output_metadata_summary,
        )
    if supplied_package_preview_hash != expected_package_preview_hash:
        raise Layer3WorkbenchError(
            "package_review_preview_mismatch",
            "Package construction commit must reference the current server-recomputed package-review preview hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_preview_hash"],
            next_allowed_actions=["refresh_package_review_preview"],
        )

    if qualitative_aps_commit:
        source_gate = SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE
    else:
        source_gate = (
            SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE
            if associated_cohort_commit
            else SOURCE_WORKBENCH_PACKAGE_CONSTRUCTION_FREEZE
        )
    package_review_submit_enabled = True
    downstream_unavailable = (
        QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
        if qualitative_aps_commit
        else
        COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
        if associated_cohort_commit
        else PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    )
    authority_basis_extra: dict[str, Any] | None = None
    package_payload_extras_by_kind: dict[str, dict[str, Any]] | None = None
    authority_schema_id = "layer3.workbench_package_construction_authority.v1"
    if qualitative_aps_commit:
        assert qualitative_basis is not None
        output_payload = qualitative_basis["output_payload"]
        chunk_summary = output_payload.get("chunk_summary") if isinstance(output_payload, dict) else {}
        authority_schema_id = "layer3.qual_aps_package_construction_authority.v1"
        authority_basis_extra = {
            "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
            "method": QUAL_APS_METHOD_NAME,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
            "content_id": qualitative_basis["content_id"],
            "content_contract_id": qualitative_basis["content_contract_id"],
            "chunking_contract_id": qualitative_basis["chunking_contract_id"],
            "material_snapshot_id": qualitative_basis["material_snapshot_id"],
            "analysis_unit_id": qualitative_basis["analysis_unit_id"],
            "analysis_set_id": qualitative_basis["analysis_set_id"],
            "output_payload_hash": qualitative_basis["output_payload_hash"],
            "chunk_ids": _json_clone(chunk_summary.get("chunk_ids") if isinstance(chunk_summary, dict) else []),
            "chunk_hashes": _json_clone(chunk_summary.get("chunk_hashes") if isinstance(chunk_summary, dict) else []),
            "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        }
        package_payload_extras_by_kind = _qualitative_aps_package_payload_extras(
            qualitative_basis=qualitative_basis,
            output_metadata_summary=output_metadata_summary,
            package_review_preview_hash=supplied_package_preview_hash,
            result_review_state=review_state,
        )
    try:
        result = materialize_workbench_package_commit(
            db,
            session=session,
            analysis_plan=analysis_plan,
            pass_run=pass_run,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_state=review_state,
            package_review_preview_hash=supplied_package_preview_hash,
            output_metadata_summary=output_metadata_summary,
            client_request_id=request_id,
            source_gate=source_gate,
            package_review_submit_enabled=package_review_submit_enabled,
            downstream_unavailable=downstream_unavailable,
            authority_schema_id=authority_schema_id,
            authority_basis_extra=authority_basis_extra,
            package_payload_extras_by_kind=package_payload_extras_by_kind,
        )
    except Layer3PackageEntryError as exc:
        raise Layer3WorkbenchError(
            "package_construction_commit_blocked",
            str(exc),
            status="conflict",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        ) from exc
    db.commit()

    packages = list(result.output_packages)
    pass_summary = pass_run.summary_json or {}
    reconciliation_summary = result.reconciliation_record.summary_json or {}
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        commit_summary = {}
    package_source_shape = (
        SOURCE_SHAPE_APS_CONTENT_DOCUMENT
        if qualitative_aps_commit
        else _package_source_shape(
            output_metadata_summary=output_metadata_summary,
            pass_summary=pass_summary,
        )
    )
    source_dataset_version_ids = [] if qualitative_aps_commit else _package_source_dataset_version_ids(
        output_metadata_summary=output_metadata_summary,
        pass_summary=pass_summary,
    )
    return {
        **_base_response(
            QUAL_APS_PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID
            if qualitative_aps_commit
            else PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID,
            request_id=request_id,
            status="already_committed" if result.replayed else "committed",
        ),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": str(status_body.get("analysis_run_id") or "") or None,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "construction_basis_hash": commit_summary.get("construction_basis_hash")
        or commit_summary.get("authority_basis_hash"),
        "reconciliation_record_id": result.reconciliation_record.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_ref": package.payload_ref,
                "payload_hash": package.payload_hash,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_refs": [package.payload_ref for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "pass_scope": output_metadata_summary.get("pass_scope"),
        "method": output_metadata_summary.get("selected_method_name"),
        "source_gate": output_metadata_summary.get("source_gate"),
        "package_construction_source_gate": source_gate,
        "source_shape": package_source_shape,
        "source_dataset_version_ids": source_dataset_version_ids,
        "content_id": qualitative_basis["content_id"] if qualitative_basis else None,
        "content_contract_id": qualitative_basis["content_contract_id"] if qualitative_basis else None,
        "chunking_contract_id": qualitative_basis["chunking_contract_id"] if qualitative_basis else None,
        "material_snapshot_id": qualitative_basis["material_snapshot_id"] if qualitative_basis else None,
        "analysis_unit_id": qualitative_basis["analysis_unit_id"] if qualitative_basis else None,
        "analysis_set_id": qualitative_basis["analysis_set_id"] if qualitative_basis else None,
        "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
        "output_payload_hash": qualitative_basis["output_payload_hash"] if qualitative_basis else None,
        "reviewed_output_item_summary": {
            "reviewed_item_count": len(review_state.get("reviewed_output_items") or []),
            "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
        },
        "package_commit_enabled": False,
        "package_review_submit_enabled": package_review_submit_enabled,
        "handoff_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "downstream_unavailable": list(downstream_unavailable),
        "next_allowed_actions": [] if qualitative_aps_commit else ["submit_package_review"],
        "next_state": PACKAGE_CONSTRUCTED_STATE,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode=(
                "durable_qual_aps_package_construction"
                if qualitative_aps_commit
                else "durable_package_construction"
            ),
            downstream_unavailable=downstream_unavailable,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def package_review_submit(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for package-review submit.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_package_review_submit_request"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()
    supplied_package_preview_hash = str(payload.get("package_review_preview_hash") or "").strip()
    supplied_construction_basis_hash = str(payload.get("construction_basis_hash") or "").strip()
    reconciliation_record_id = str(payload.get("reconciliation_record_id") or "").strip()
    operator_decision = str(payload.get("operator_decision") or "").strip()
    decision_notes = str(payload.get("decision_notes") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    raw_output_package_ids = payload.get("output_package_ids")
    raw_payload_refs = payload.get("payload_refs")
    raw_payload_hashes = payload.get("payload_hashes")

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("result_review_record_ref", supplied_review_ref),
            ("package_review_preview_hash", supplied_package_preview_hash),
            ("reconciliation_record_id", reconciliation_record_id),
            ("operator_decision", operator_decision),
        )
        if not value
    ]
    if not raw_output_package_ids:
        missing.append("output_package_ids")
    if not raw_payload_hashes:
        missing.append("payload_hashes")
    if missing:
        raise Layer3WorkbenchError(
            "missing_package_review_submit_fields",
            f"Package-review submit request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_review_submit_request"],
        )

    blocked_payload_fields = package_review_submit_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "package_review_submit_scope_not_admitted",
            f"Package-review submit request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_package_review_submit_request"],
        )
    if operator_decision not in PACKAGE_REVIEW_SUBMIT_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_package_review_submit_decision",
            "operator_decision must be approved, changes_requested, rejected, or blocked.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if operator_decision in PACKAGE_REVIEW_SUBMIT_NOTE_REQUIRED_DECISIONS and not decision_notes:
        raise Layer3WorkbenchError(
            "package_review_submit_notes_required",
            "decision_notes are required for changes_requested, rejected, or blocked package-review decisions.",
            status="invalid",
            blocked_fields=["decision_notes"],
        )

    expected_package_kinds = payload.get("expected_package_kinds")
    if expected_package_kinds is not None:
        expected_kinds = [str(item or "").strip() for item in expected_package_kinds] if isinstance(expected_package_kinds, list) else []
        if (
            len(expected_kinds) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
            or set(expected_kinds) != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        ):
            raise Layer3WorkbenchError(
                "package_review_submit_kinds_mismatch",
                "Package-review submit admits exactly the canonical_internal, user_facing, and review_facing package kinds.",
                status="conflict",
                http_status=409,
                blocked_fields=["expected_package_kinds"],
            )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "package_review_submit_result_status_unavailable",
            "Package-review submit requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "package_review_submit_output_metadata_required",
            "Package-review submit requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "package_review_submit_inconsistent",
            "Package-review submit could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    qualitative_aps_submit = status_body.get("engine_family") == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    qualitative_basis: dict[str, Any] | None = None
    if qualitative_aps_submit:
        if supplied_analysis_run_id:
            raise Layer3WorkbenchError(
                "qualitative_aps_package_review_submit_analysis_run_not_admitted",
                "Qualitative APS package-review submit must not supply analysis_run_id.",
                status="invalid",
                blocked_fields=["analysis_run_id"],
            )
        qualitative_basis = _require_qualitative_aps_package_review_authority(
            db,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        qualitative_missing = []
        if not supplied_construction_basis_hash:
            qualitative_missing.append("construction_basis_hash")
        if not raw_payload_refs:
            qualitative_missing.append("payload_refs")
        if qualitative_missing:
            raise Layer3WorkbenchError(
                "missing_qualitative_aps_package_review_submit_fields",
                (
                    "Qualitative APS package-review submit request is missing required fields: "
                    f"{', '.join(qualitative_missing)}."
                ),
                status="invalid",
                blocked_fields=qualitative_missing,
                next_allowed_actions=["submit_complete_qualitative_aps_package_review_submit_request"],
            )
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    associated_cohort_submit = False
    if status_body.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT:
        associated_cohort_submit = _associated_cohort_result_source_admitted(
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        if not associated_cohort_submit:
            raise Layer3WorkbenchError(
                "associated_cohort_package_review_submit_not_admitted",
                (
                    "Package-review submit is admitted only for exact selected-pass descriptive "
                    "associated-cohort result/status output in this tranche."
                ),
                status="blocked",
                http_status=409,
                next_allowed_actions=["inspect_execution_result_status"],
            )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "package_review_submit_pass_run_mismatch",
            "Package-review submit pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    if reconciliation is None:
        raise Layer3WorkbenchError(
            "package_review_submit_requires_package_construction",
            "Package-review submit requires an existing reconciliation record from package construction commit.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["package_construction_commit"],
        )

    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "package_review_submit_requires_approved_result_review",
            "Package-review submit requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "package_review_submit_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )
    mismatched_review_fields = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
        }.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "package_review_submit_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "package_review_submit_trace_unresolved",
            "Package-review submit requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    if qualitative_aps_submit:
        expected_package_preview_hash = _qualitative_aps_package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_record_ref=supplied_review_ref,
            output_payload_ref=output_metadata_summary.get("output_payload_ref"),
            qualitative_basis=qualitative_basis or {},
        )
    else:
        expected_package_preview_hash = _package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            analysis_run_id=str(status_body.get("analysis_run_id") or "") or None,
            result_review_record_ref=supplied_review_ref,
            output_metadata_summary=output_metadata_summary,
        )
    if supplied_package_preview_hash != expected_package_preview_hash:
        raise Layer3WorkbenchError(
            "package_review_submit_preview_mismatch",
            "Package-review submit must reference the current server-recomputed package-review preview hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_preview_hash"],
            next_allowed_actions=["refresh_package_review_preview"],
        )

    existing_submit = _package_review_submit_from_reconciliation(reconciliation)
    aps_handoff_dispatch_state = (
        _aps_handoff_dispatch_from_reconciliation(reconciliation)
        if existing_submit is not None and existing_submit.get("package_review_state") == PACKAGE_REVIEW_APPROVED_STATE
        else None
    )
    all_packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .order_by(L3OutputPackage.package_kind.asc())
        .with_for_update()
        .all()
    )
    unexpected_package_kinds = _unexpected_package_kinds(
        all_packages,
        aps_handoff_dispatch_state=aps_handoff_dispatch_state,
    )
    if unexpected_package_kinds:
        raise Layer3WorkbenchError(
            "package_review_submit_unexpected_package_state",
            "Package-review submit cannot proceed with unexpected package kinds on the reconciliation.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    packages = _review_source_packages(all_packages)
    if (
        len(packages) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    ):
        raise Layer3WorkbenchError(
            "package_review_submit_requires_complete_package_set",
            "Package-review submit requires exactly the constructed canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["output_package_ids"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    ordered_packages = _packages_in_review_order(packages)
    if not isinstance(raw_output_package_ids, list):
        raise Layer3WorkbenchError(
            "package_review_submit_package_ids_invalid",
            "output_package_ids must be a list of the three constructed output package ids.",
            status="invalid",
            blocked_fields=["output_package_ids"],
        )
    supplied_package_ids = [str(item or "").strip() for item in raw_output_package_ids]
    expected_package_ids = [package.output_package_id for package in ordered_packages]
    if len(supplied_package_ids) != len(expected_package_ids) or set(supplied_package_ids) != set(expected_package_ids):
        raise Layer3WorkbenchError(
            "package_review_submit_package_ids_mismatch",
            "Supplied output_package_ids do not match the constructed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    if not isinstance(raw_payload_hashes, (list, dict)):
        raise Layer3WorkbenchError(
            "package_review_submit_payload_hashes_invalid",
            "payload_hashes must be either a list of package hashes or a mapping keyed by package kind or package id.",
            status="invalid",
            blocked_fields=["payload_hashes"],
        )
    canonical_payload_hashes = _canonical_payload_hashes(payload_hashes=raw_payload_hashes, packages=packages)
    if canonical_payload_hashes is None:
        raise Layer3WorkbenchError(
            "package_review_submit_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the constructed package payload hashes.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_hashes"],
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        raise Layer3WorkbenchError(
            "package_review_submit_non_workbench_package_state",
            "Package-review submit requires workbench package-construction commit provenance.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        )
    package_construction_source_gate = str(reconciliation_summary.get("source_gate") or "")
    if qualitative_aps_submit and package_construction_source_gate != SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "qualitative_aps_package_review_submit_construction_source_gate_mismatch",
            "Qualitative APS package-review submit requires qualitative APS package-construction authority from docs 140/141.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    if associated_cohort_submit and package_construction_source_gate != SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "package_review_submit_construction_source_gate_mismatch",
            "Associated-cohort package-review submit requires cohort package-construction authority from docs 88/89.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    if not associated_cohort_submit and package_construction_source_gate == SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "package_review_submit_construction_source_gate_mismatch",
            "Single-item package-review submit cannot use associated-cohort package-construction authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    if not qualitative_aps_submit and package_construction_source_gate == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "package_review_submit_construction_source_gate_mismatch",
            "Non-qualitative package-review submit cannot use qualitative APS package-construction authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    commit_mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": supplied_package_preview_hash,
            "result_review_record_ref": supplied_review_ref,
        }.items()
        if str(commit_summary.get(field) or "") != str(expected)
    ]
    if commit_mismatches:
        raise Layer3WorkbenchError(
            "package_review_submit_construction_mismatch",
            "Stored package-construction provenance does not match the supplied package-review submit authority.",
            status="conflict",
            http_status=409,
            blocked_fields=commit_mismatches,
        )
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash") or commit_summary.get("authority_basis_hash") or ""
    )
    if qualitative_aps_submit and supplied_construction_basis_hash != expected_construction_basis_hash:
        raise Layer3WorkbenchError(
            "qualitative_aps_package_review_submit_construction_basis_mismatch",
            "Supplied construction_basis_hash does not match the persisted qualitative APS package construction.",
            status="conflict",
            http_status=409,
            blocked_fields=["construction_basis_hash"],
        )

    canonical_payload_refs = None
    if qualitative_aps_submit:
        if not isinstance(raw_payload_refs, (list, dict)):
            raise Layer3WorkbenchError(
                "qualitative_aps_package_review_submit_payload_refs_invalid",
                "payload_refs must be either a list of package refs or a mapping keyed by package kind or package id.",
                status="invalid",
                blocked_fields=["payload_refs"],
            )
        canonical_payload_refs = _canonical_payload_refs(payload_refs=raw_payload_refs, packages=packages)
        if canonical_payload_refs is None:
            raise Layer3WorkbenchError(
                "qualitative_aps_package_review_submit_payload_refs_mismatch",
                "Supplied payload_refs do not match the constructed package payload refs.",
                status="conflict",
                http_status=409,
                blocked_fields=["payload_refs"],
            )

    analysis_run_id = str(status_body.get("analysis_run_id") or "") or None
    submit_basis = {
        "schema_id": "layer3.package_review_submit_authority.v1",
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_submit else None,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": canonical_payload_refs if qualitative_aps_submit else None,
        "payload_hashes": canonical_payload_hashes,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "pass_type": PASS_TYPE_ASSOCIATED_COHORT if associated_cohort_submit else pass_run.pass_type,
        "pass_scope": output_metadata_summary.get("pass_scope"),
        "method": output_metadata_summary.get("selected_method_name"),
        "source_gate": output_metadata_summary.get("source_gate"),
        "package_construction_source_gate": package_construction_source_gate,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT if qualitative_aps_submit else output_metadata_summary.get("cohort_shape"),
        "source_dataset_version_ids": [] if qualitative_aps_submit else _json_clone(output_metadata_summary.get("source_dataset_version_ids") or []),
    }
    if qualitative_basis is not None:
        submit_basis.update(
            {
                "content_id": qualitative_basis["content_id"],
                "content_contract_id": qualitative_basis["content_contract_id"],
                "chunking_contract_id": qualitative_basis["chunking_contract_id"],
                "material_snapshot_id": qualitative_basis["material_snapshot_id"],
                "analysis_unit_id": qualitative_basis["analysis_unit_id"],
                "analysis_set_id": qualitative_basis["analysis_set_id"],
                "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                "output_payload_hash": qualitative_basis["output_payload_hash"],
                "chunk_count": qualitative_basis["chunk_count"],
            }
        )
    submit_record_ref = _stable_id("l3-package-review-submit", submit_basis)
    if existing_submit is not None:
        existing_submit_ref = str(existing_submit.get("submit_record_ref") or "")
        legacy_submit_record_ref = _legacy_package_review_submit_record_ref(
            submit_basis=submit_basis,
            existing_submit=existing_submit,
        )
        if existing_submit_ref == submit_record_ref or existing_submit_ref == legacy_submit_record_ref:
            return _package_review_submit_response(
                request_id=request_id,
                status="already_submitted",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                pass_run_id=pass_run_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                analysis_run_id=analysis_run_id,
                result_review_record_ref=supplied_review_ref,
                package_review_preview_hash=supplied_package_preview_hash,
                reconciliation_record=reconciliation,
                packages=packages,
                review_state=existing_submit,
            )
        raise Layer3WorkbenchError(
            "package_review_submit_already_recorded",
            "This package set already has a package-review submit decision.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )

    package_review_state = PACKAGE_REVIEW_SUBMIT_STATE_BY_DECISION[operator_decision]
    downstream_unavailable = _package_review_submit_downstream_unavailable(
        package_review_state,
        associated_cohort_submit=associated_cohort_submit,
        qualitative_aps_submit=qualitative_aps_submit,
    )
    package_review_submit_schema_id = (
        QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        if qualitative_aps_submit
        else COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        if associated_cohort_submit
        else PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    )
    submit_state = {
        "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
        "package_review_submit_schema_id": package_review_submit_schema_id,
        "client_request_id": request_id,
        "submit_record_ref": submit_record_ref,
        "authority_basis": submit_basis,
        "package_review_state": package_review_state,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_submit else None,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": canonical_payload_refs if qualitative_aps_submit else None,
        "payload_hashes": canonical_payload_hashes,
        "pass_type": PASS_TYPE_ASSOCIATED_COHORT if associated_cohort_submit else pass_run.pass_type,
        "pass_scope": output_metadata_summary.get("pass_scope"),
        "method": output_metadata_summary.get("selected_method_name"),
        "source_gate": output_metadata_summary.get("source_gate"),
        "package_construction_source_gate": package_construction_source_gate,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT if qualitative_aps_submit else output_metadata_summary.get("cohort_shape"),
        "source_dataset_version_ids": [] if qualitative_aps_submit else _json_clone(output_metadata_summary.get("source_dataset_version_ids") or []),
        "recorded_at": _utcnow_iso(),
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "export_enabled": False,
        "downstream_unavailable": list(downstream_unavailable),
    }
    commit_summary = {**commit_summary, "package_review_submit_enabled": False}
    reconciliation.summary_json = {
        **reconciliation_summary,
        "workbench_package_commit": commit_summary,
        "package_review_submit": submit_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "package_review_submit": {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "package_review_submit_schema_id": package_review_submit_schema_id,
            "submit_record_ref": submit_record_ref,
            "package_review_state": package_review_state,
            "operator_decision": operator_decision,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "analysis_run_id": analysis_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": expected_package_ids,
            "package_kinds": [package.package_kind for package in ordered_packages],
            "payload_refs": canonical_payload_refs if qualitative_aps_submit else None,
            "pass_type": PASS_TYPE_ASSOCIATED_COHORT if associated_cohort_submit else pass_run.pass_type,
            "pass_scope": output_metadata_summary.get("pass_scope"),
            "method": output_metadata_summary.get("selected_method_name"),
            "source_gate": output_metadata_summary.get("source_gate"),
            "package_construction_source_gate": package_construction_source_gate,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT if qualitative_aps_submit else output_metadata_summary.get("cohort_shape"),
            "source_dataset_version_ids": [] if qualitative_aps_submit else _json_clone(output_metadata_summary.get("source_dataset_version_ids") or []),
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(downstream_unavailable),
        },
    }
    db.commit()

    return _package_review_submit_response(
        request_id=request_id,
        status="submitted",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        analysis_run_id=analysis_run_id,
        result_review_record_ref=supplied_review_ref,
        package_review_preview_hash=supplied_package_preview_hash,
        reconciliation_record=reconciliation,
        packages=packages,
        review_state=submit_state,
    )


def handoff_export_prepare(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for handoff/export preparation.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_handoff_export_prepare_request"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()
    supplied_package_preview_hash = str(payload.get("package_review_preview_hash") or "").strip()
    supplied_construction_basis_hash = str(payload.get("construction_basis_hash") or "").strip()
    reconciliation_record_id = str(payload.get("reconciliation_record_id") or "").strip()
    supplied_submit_ref = str(payload.get("package_review_submit_record_ref") or "").strip()
    supplied_package_review_state = str(payload.get("package_review_state") or "").strip()
    supplied_package_review_submit_schema_id = str(payload.get("package_review_submit_schema_id") or "").strip()
    handoff_target = str(payload.get("handoff_target") or "").strip()
    export_mode = str(payload.get("export_mode") or "").strip()
    operator_decision = str(payload.get("operator_decision") or "").strip()
    decision_notes = str(payload.get("decision_notes") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    raw_output_package_ids = payload.get("output_package_ids")
    raw_payload_refs = payload.get("payload_refs")
    raw_payload_hashes = payload.get("payload_hashes")

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("result_review_record_ref", supplied_review_ref),
            ("package_review_preview_hash", supplied_package_preview_hash),
            ("reconciliation_record_id", reconciliation_record_id),
            ("package_review_submit_record_ref", supplied_submit_ref),
            ("package_review_state", supplied_package_review_state),
            ("package_review_submit_schema_id", supplied_package_review_submit_schema_id),
            ("handoff_target", handoff_target),
            ("export_mode", export_mode),
            ("operator_decision", operator_decision),
        )
        if not value
    ]
    if not raw_output_package_ids:
        missing.append("output_package_ids")
    if not raw_payload_hashes:
        missing.append("payload_hashes")
    if missing:
        raise Layer3WorkbenchError(
            "missing_handoff_export_prepare_fields",
            f"Handoff/export preparation request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_handoff_export_prepare_request"],
        )

    blocked_payload_fields = handoff_export_prepare_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "handoff_export_prepare_scope_not_admitted",
            f"Handoff/export preparation request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_handoff_export_prepare_request"],
        )
    if handoff_target != "internal_export_envelope":
        raise Layer3WorkbenchError(
            "handoff_export_prepare_target_not_admitted",
            "handoff_target must be internal_export_envelope for this tranche.",
            status="invalid",
            blocked_fields=["handoff_target"],
        )
    if export_mode != "prepare_only":
        raise Layer3WorkbenchError(
            "handoff_export_prepare_mode_not_admitted",
            "export_mode must be prepare_only for this tranche.",
            status="invalid",
            blocked_fields=["export_mode"],
        )
    if operator_decision not in HANDOFF_EXPORT_PREPARE_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_handoff_export_prepare_decision",
            "operator_decision must be authorize_prepare, hold, decline, or blocked.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if operator_decision in HANDOFF_EXPORT_PREPARE_NOTE_REQUIRED_DECISIONS and not decision_notes:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_notes_required",
            "decision_notes are required for hold, decline, or blocked handoff/export decisions.",
            status="invalid",
            blocked_fields=["decision_notes"],
        )
    if supplied_package_review_state != PACKAGE_REVIEW_APPROVED_STATE:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_requires_approved_package_review",
            "Handoff/export preparation requires package_review_state to be package_review_approved.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_state"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )

    expected_package_kinds = payload.get("expected_package_kinds")
    if expected_package_kinds is not None:
        expected_kinds = [str(item or "").strip() for item in expected_package_kinds] if isinstance(expected_package_kinds, list) else []
        if (
            len(expected_kinds) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
            or set(expected_kinds) != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        ):
            raise Layer3WorkbenchError(
                "handoff_export_prepare_kinds_mismatch",
                "Handoff/export preparation admits exactly the canonical_internal, user_facing, and review_facing package kinds.",
                status="conflict",
                http_status=409,
                blocked_fields=["expected_package_kinds"],
            )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_result_status_unavailable",
            "Handoff/export preparation requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_output_metadata_required",
            "Handoff/export preparation requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    qualitative_aps_prepare = (
        status_body.get("engine_family") == ENGINE_FAMILY_QUAL_APS_DOCUMENT
        or status_body.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        or output_metadata_summary.get("source_gate") == QUAL_APS_SOURCE_GATE
    )
    if qualitative_aps_prepare and supplied_analysis_run_id:
        raise Layer3WorkbenchError(
            "qualitative_aps_handoff_export_prepare_analysis_run_not_admitted",
            "Qualitative APS handoff/export preparation must not provide analysis_run_id.",
            status="invalid",
            blocked_fields=["analysis_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_inconsistent",
            "Handoff/export preparation could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_pass_run_mismatch",
            "Handoff/export preparation pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    associated_cohort_prepare = False
    qualitative_basis = None
    if qualitative_aps_prepare:
        qualitative_basis = _require_qualitative_aps_package_review_authority(
            db,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
    if status_body.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT:
        associated_cohort_prepare = _associated_cohort_result_source_admitted(
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        if not associated_cohort_prepare:
            raise Layer3WorkbenchError(
                "associated_cohort_handoff_export_prepare_not_admitted",
                (
                    "Handoff/export preparation is admitted only for exact selected-pass descriptive "
                    "associated-cohort result/status output in this tranche."
                ),
                status="blocked",
                http_status=409,
                next_allowed_actions=["inspect_execution_result_status"],
            )
    if reconciliation is None:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_requires_package_construction",
            "Handoff/export preparation requires an existing reconciliation record from package construction commit.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_package_construction_state"],
        )

    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_requires_approved_result_review",
            "Handoff/export preparation requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )
    mismatched_review_fields = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
        }.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_trace_unresolved",
            "Handoff/export preparation requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    analysis_run_id = str(status_body.get("analysis_run_id") or "") or None
    if qualitative_basis is not None:
        expected_package_preview_hash = _qualitative_aps_package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_record_ref=supplied_review_ref,
            output_payload_ref=output_metadata_summary.get("output_payload_ref"),
            qualitative_basis=qualitative_basis,
        )
    else:
        expected_package_preview_hash = _package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            analysis_run_id=analysis_run_id,
            result_review_record_ref=supplied_review_ref,
            output_metadata_summary=output_metadata_summary,
        )
    if supplied_package_preview_hash != expected_package_preview_hash:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_preview_mismatch",
            "Handoff/export preparation must reference the current server-recomputed package-review preview hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_preview_hash"],
            next_allowed_actions=["refresh_package_review_preview"],
        )

    existing_prepare = _handoff_export_prepare_from_reconciliation(reconciliation)
    aps_handoff_dispatch_state = (
        _aps_handoff_dispatch_from_reconciliation(reconciliation)
        if existing_prepare is not None and existing_prepare.get("handoff_export_state") == HANDOFF_EXPORT_PREPARED_STATE
        else None
    )
    all_packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .order_by(L3OutputPackage.package_kind.asc())
        .with_for_update()
        .all()
    )
    unexpected_package_kinds = _unexpected_package_kinds(
        all_packages,
        aps_handoff_dispatch_state=aps_handoff_dispatch_state,
    )
    if unexpected_package_kinds:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_unexpected_package_state",
            "Handoff/export preparation cannot proceed with unexpected package kinds on the reconciliation.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    packages = _review_source_packages(all_packages)
    if (
        len(packages) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    ):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_requires_complete_package_set",
            "Handoff/export preparation requires exactly the reviewed canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["output_package_ids"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    ordered_packages = _packages_in_review_order(packages)
    if not isinstance(raw_output_package_ids, list):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_package_ids_invalid",
            "output_package_ids must be a list of the three reviewed output package ids.",
            status="invalid",
            blocked_fields=["output_package_ids"],
        )
    supplied_package_ids = [str(item or "").strip() for item in raw_output_package_ids]
    expected_package_ids = [package.output_package_id for package in ordered_packages]
    if len(supplied_package_ids) != len(expected_package_ids) or set(supplied_package_ids) != set(expected_package_ids):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_package_ids_mismatch",
            "Supplied output_package_ids do not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    if any(not str(package.payload_ref or "").strip() or not str(package.payload_hash or "").strip() for package in ordered_packages):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_package_payload_identity_missing",
            "Handoff/export preparation requires stored package payload refs and hashes.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_refs", "payload_hashes"],
        )
    if qualitative_aps_prepare and raw_payload_refs is None:
        raise Layer3WorkbenchError(
            "qualitative_aps_handoff_export_prepare_payload_refs_required",
            "Qualitative APS handoff/export preparation requires explicit payload_refs authority.",
            status="invalid",
            blocked_fields=["payload_refs"],
        )
    if raw_payload_refs is not None:
        canonical_payload_refs = _canonical_payload_refs(payload_refs=raw_payload_refs, packages=packages)
        if canonical_payload_refs is None:
            raise Layer3WorkbenchError(
                "handoff_export_prepare_payload_refs_mismatch",
                "Supplied payload_refs do not match the reviewed package payload refs.",
                status="conflict",
                http_status=409,
                blocked_fields=["payload_refs"],
            )
    else:
        canonical_payload_refs = [package.payload_ref for package in ordered_packages]
    if not isinstance(raw_payload_hashes, (list, dict)):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_payload_hashes_invalid",
            "payload_hashes must be either a list of package hashes or a mapping keyed by package kind or package id.",
            status="invalid",
            blocked_fields=["payload_hashes"],
        )
    canonical_payload_hashes = _canonical_payload_hashes(payload_hashes=raw_payload_hashes, packages=packages)
    if canonical_payload_hashes is None:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the reviewed package payload hashes.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_hashes"],
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_non_workbench_package_state",
            "Handoff/export preparation requires workbench package-construction commit provenance.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        )
    package_construction_source_gate = str(reconciliation_summary.get("source_gate") or "")
    if associated_cohort_prepare and package_construction_source_gate != SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_construction_source_gate_mismatch",
            "Associated-cohort handoff/export preparation requires cohort package-construction authority from docs 88/89.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    if qualitative_aps_prepare and package_construction_source_gate != SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "qualitative_aps_handoff_export_prepare_construction_source_gate_mismatch",
            "Qualitative APS handoff/export preparation requires qualitative APS package-construction authority from docs 140/141.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    if not associated_cohort_prepare and package_construction_source_gate == SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_construction_source_gate_mismatch",
            "Single-item handoff/export preparation cannot use associated-cohort package-construction authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    if not qualitative_aps_prepare and package_construction_source_gate == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_construction_source_gate_mismatch",
            "Non-qualitative handoff/export preparation cannot use qualitative APS package-construction authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
        )
    commit_mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": supplied_package_preview_hash,
            "result_review_record_ref": supplied_review_ref,
        }.items()
        if str(commit_summary.get(field) or "") != str(expected)
    ]
    if commit_mismatches:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_construction_mismatch",
            "Stored package-construction provenance does not match the supplied handoff/export authority.",
            status="conflict",
            http_status=409,
            blocked_fields=commit_mismatches,
        )
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash") or commit_summary.get("authority_basis_hash") or ""
    )
    if qualitative_aps_prepare:
        if not supplied_construction_basis_hash:
            raise Layer3WorkbenchError(
                "missing_qualitative_aps_handoff_export_prepare_fields",
                "Qualitative APS handoff/export preparation requires construction_basis_hash.",
                status="invalid",
                blocked_fields=["construction_basis_hash"],
            )
        if supplied_construction_basis_hash != expected_construction_basis_hash:
            raise Layer3WorkbenchError(
                "qualitative_aps_handoff_export_prepare_construction_basis_mismatch",
                "Supplied construction_basis_hash does not match the persisted qualitative APS package construction.",
                status="conflict",
                http_status=409,
                blocked_fields=["construction_basis_hash"],
            )

    package_review_submit = _package_review_submit_from_reconciliation(reconciliation)
    if package_review_submit is None:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_requires_approved_package_review",
            "Handoff/export preparation requires an existing package-review submit decision.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_submit_record_ref"],
            next_allowed_actions=["submit_package_review_approval"],
        )
    if package_review_submit.get("package_review_state") != PACKAGE_REVIEW_APPROVED_STATE:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_requires_approved_package_review",
            "Handoff/export preparation requires package-review submit state package_review_approved.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_state"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )
    if supplied_submit_ref != str(package_review_submit.get("submit_record_ref") or ""):
        raise Layer3WorkbenchError(
            "handoff_export_prepare_submit_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match the approved package-review submit state.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_submit_record_ref"],
        )
    expected_submit_schema_id = (
        QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        if qualitative_aps_prepare
        else COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        if associated_cohort_prepare
        else PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    )
    if supplied_package_review_submit_schema_id != expected_submit_schema_id:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_submit_schema_mismatch",
            "Supplied package_review_submit_schema_id does not match the admitted package-review submit authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_submit_schema_id"],
        )

    recorded_package_review_submit_schema_id = str(
        package_review_submit.get("package_review_submit_schema_id")
        or expected_submit_schema_id
    )
    submit_mismatches = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_prepare else None,
            "reconciliation_record_id": reconciliation_record_id,
            "package_construction_source_gate": package_construction_source_gate,
        }.items()
        if str(package_review_submit.get(field) or "") != str(expected or "")
    ]
    if recorded_package_review_submit_schema_id != expected_submit_schema_id:
        submit_mismatches.append("package_review_submit_schema_id")
    if list(package_review_submit.get("output_package_ids") or []) != expected_package_ids:
        submit_mismatches.append("output_package_ids")
    if list(package_review_submit.get("package_kinds") or []) != [package.package_kind for package in ordered_packages]:
        submit_mismatches.append("package_kinds")
    if list(package_review_submit.get("payload_hashes") or []) != canonical_payload_hashes:
        submit_mismatches.append("payload_hashes")
    if associated_cohort_prepare:
        cohort_submit_expectations = {
            "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
            "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
            "method": "descriptive_summary",
            "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
            "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
        }
        submit_mismatches.extend(
            field
            for field, expected in cohort_submit_expectations.items()
            if str(package_review_submit.get(field) or "") != expected
        )
        if list(package_review_submit.get("source_dataset_version_ids") or []) != list(
            output_metadata_summary.get("source_dataset_version_ids") or []
        ):
            submit_mismatches.append("source_dataset_version_ids")
    if qualitative_aps_prepare:
        qualitative_submit_expectations = {
            "pass_type": PASS_TYPE_SINGLE_ITEM,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
            "method": QUAL_APS_METHOD_NAME,
            "source_gate": QUAL_APS_SOURCE_GATE,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        }
        submit_mismatches.extend(
            field
            for field, expected in qualitative_submit_expectations.items()
            if str(package_review_submit.get(field) or "") != expected
        )
        if list(package_review_submit.get("source_dataset_version_ids") or []) != []:
            submit_mismatches.append("source_dataset_version_ids")
        if list(package_review_submit.get("payload_refs") or []) != canonical_payload_refs:
            submit_mismatches.append("payload_refs")
        authority_basis = package_review_submit.get("authority_basis")
        if not isinstance(authority_basis, dict):
            submit_mismatches.append("authority_basis")
        else:
            for field, expected in {
                "content_id": qualitative_basis["content_id"] if qualitative_basis is not None else "",
                "content_contract_id": qualitative_basis["content_contract_id"] if qualitative_basis is not None else "",
                "chunking_contract_id": qualitative_basis["chunking_contract_id"] if qualitative_basis is not None else "",
                "material_snapshot_id": qualitative_basis["material_snapshot_id"] if qualitative_basis is not None else "",
                "analysis_unit_id": qualitative_basis["analysis_unit_id"] if qualitative_basis is not None else "",
                "analysis_set_id": qualitative_basis["analysis_set_id"] if qualitative_basis is not None else "",
                "output_payload_hash": qualitative_basis["output_payload_hash"] if qualitative_basis is not None else "",
            }.items():
                if str(authority_basis.get(field) or "") != expected:
                    submit_mismatches.append(field)
    if submit_mismatches:
        raise Layer3WorkbenchError(
            "handoff_export_prepare_package_review_submit_mismatch",
            "Stored package-review submit authority does not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(submit_mismatches)),
        )

    source_shape = SOURCE_SHAPE_APS_CONTENT_DOCUMENT if qualitative_aps_prepare else output_metadata_summary.get("cohort_shape")
    source_dataset_version_ids = [] if qualitative_aps_prepare else _json_clone(
        output_metadata_summary.get("source_dataset_version_ids") or []
    )
    prepare_pass_type = PASS_TYPE_ASSOCIATED_COHORT if associated_cohort_prepare else pass_run.pass_type
    preparation_basis = {
        "schema_id": "layer3.handoff_export_prepare_authority.v1",
        "package_review_submit_schema_id": expected_submit_schema_id,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_prepare else None,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": canonical_payload_refs,
        "payload_hashes": canonical_payload_hashes,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "pass_type": prepare_pass_type,
        "pass_scope": output_metadata_summary.get("pass_scope"),
        "method": output_metadata_summary.get("selected_method_name"),
        "source_gate": output_metadata_summary.get("source_gate"),
        "package_construction_source_gate": package_construction_source_gate,
        "source_shape": source_shape,
        "source_dataset_version_ids": source_dataset_version_ids,
    }
    if qualitative_basis is not None:
        preparation_basis.update(
            {
                "content_id": qualitative_basis["content_id"],
                "content_contract_id": qualitative_basis["content_contract_id"],
                "chunking_contract_id": qualitative_basis["chunking_contract_id"],
                "material_snapshot_id": qualitative_basis["material_snapshot_id"],
                "analysis_unit_id": qualitative_basis["analysis_unit_id"],
                "analysis_set_id": qualitative_basis["analysis_set_id"],
                "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                "output_payload_hash": qualitative_basis["output_payload_hash"],
                "chunk_count": qualitative_basis["chunk_count"],
            }
        )
    prepare_record_ref = _stable_id("l3-handoff-export-prepare", preparation_basis)
    if existing_prepare is not None:
        if existing_prepare.get("prepare_record_ref") == prepare_record_ref:
            existing_decision = str(existing_prepare.get("operator_decision") or operator_decision)
            existing_status = HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION.get(existing_decision, "recorded")
            return _handoff_export_prepare_response(
                request_id=request_id,
                status=f"already_{existing_status}",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                pass_run_id=pass_run_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                analysis_run_id=analysis_run_id,
                result_review_record_ref=supplied_review_ref,
                package_review_preview_hash=supplied_package_preview_hash,
                reconciliation_record=reconciliation,
                packages=packages,
                prepare_state=existing_prepare,
            )
        raise Layer3WorkbenchError(
            "handoff_export_prepare_already_recorded",
            "This package set already has a handoff/export preparation decision.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )

    recorded_at = _utcnow_iso()
    handoff_export_state = HANDOFF_EXPORT_PREPARE_STATE_BY_DECISION[operator_decision]
    envelope = None
    if operator_decision == "authorize_prepare":
        envelope_basis = {
            **preparation_basis,
            "schema_id": "layer3.handoff_export_envelope_authority.v1",
        }
        envelope = {
            "schema_id": "layer3.handoff_export_envelope.v1",
            "envelope_ref": _stable_id("l3-handoff-export-envelope", envelope_basis),
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "package_review_submit_record_ref": supplied_submit_ref,
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": expected_package_ids,
            "package_kinds": [package.package_kind for package in ordered_packages],
            "payload_refs": canonical_payload_refs,
            "payload_hashes": canonical_payload_hashes,
            "package_review_submit_schema_id": expected_submit_schema_id,
            "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_prepare else None,
            "pass_type": prepare_pass_type,
            "pass_scope": output_metadata_summary.get("pass_scope"),
            "method": output_metadata_summary.get("selected_method_name"),
            "source_gate": output_metadata_summary.get("source_gate"),
            "package_construction_source_gate": package_construction_source_gate,
            "source_shape": source_shape,
            "source_dataset_version_ids": _json_clone(source_dataset_version_ids),
            "prepared_at": recorded_at,
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
            "aps_handoff_enabled": False,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_url_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        }
        if qualitative_basis is not None:
            envelope.update(
                {
                    "content_id": qualitative_basis["content_id"],
                    "content_contract_id": qualitative_basis["content_contract_id"],
                    "chunking_contract_id": qualitative_basis["chunking_contract_id"],
                    "material_snapshot_id": qualitative_basis["material_snapshot_id"],
                    "analysis_unit_id": qualitative_basis["analysis_unit_id"],
                    "analysis_set_id": qualitative_basis["analysis_set_id"],
                    "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                    "output_payload_hash": qualitative_basis["output_payload_hash"],
                    "chunk_count": qualitative_basis["chunk_count"],
                }
            )
    prepare_state = {
        "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
        "client_request_id": request_id,
        "prepare_record_ref": prepare_record_ref,
        "authority_basis": preparation_basis,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "handoff_export_state": handoff_export_state,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_prepare else None,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": canonical_payload_refs,
        "payload_hashes": canonical_payload_hashes,
        "package_review_submit_schema_id": expected_submit_schema_id,
        "pass_type": prepare_pass_type,
        "pass_scope": output_metadata_summary.get("pass_scope"),
        "method": output_metadata_summary.get("selected_method_name"),
        "source_gate": output_metadata_summary.get("source_gate"),
        "package_construction_source_gate": package_construction_source_gate,
        "source_shape": source_shape,
        "source_dataset_version_ids": _json_clone(source_dataset_version_ids),
        "recorded_at": recorded_at,
        "external_handoff_enabled": False,
        "external_export_enabled": False,
        "dispatch_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    if qualitative_basis is not None:
        prepare_state.update(
            {
                "content_id": qualitative_basis["content_id"],
                "content_contract_id": qualitative_basis["content_contract_id"],
                "chunking_contract_id": qualitative_basis["chunking_contract_id"],
                "material_snapshot_id": qualitative_basis["material_snapshot_id"],
                "analysis_unit_id": qualitative_basis["analysis_unit_id"],
                "analysis_set_id": qualitative_basis["analysis_set_id"],
                "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                "output_payload_hash": qualitative_basis["output_payload_hash"],
                "chunk_count": qualitative_basis["chunk_count"],
            }
        )
    if envelope is not None:
        prepare_state["handoff_export_envelope"] = envelope

    reconciliation.summary_json = {
        **reconciliation_summary,
        "handoff_export_prepare": prepare_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "handoff_export_prepare": {
            "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
            "prepare_record_ref": prepare_record_ref,
            "handoff_export_state": handoff_export_state,
            "operator_decision": operator_decision,
            "decision_notes": decision_notes or None,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "analysis_run_id": analysis_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": expected_package_ids,
            "package_kinds": [package.package_kind for package in ordered_packages],
            "package_review_submit_schema_id": expected_submit_schema_id,
            "construction_basis_hash": expected_construction_basis_hash if qualitative_aps_prepare else None,
            "pass_type": prepare_pass_type,
            "pass_scope": output_metadata_summary.get("pass_scope"),
            "method": output_metadata_summary.get("selected_method_name"),
            "source_gate": output_metadata_summary.get("source_gate"),
            "package_construction_source_gate": package_construction_source_gate,
            "source_shape": source_shape,
            "source_dataset_version_ids": _json_clone(source_dataset_version_ids),
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
            "aps_handoff_enabled": False,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_url_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        },
    }
    if qualitative_basis is not None:
        session.summary_json["handoff_export_prepare"].update(
            {
                "content_id": qualitative_basis["content_id"],
                "content_contract_id": qualitative_basis["content_contract_id"],
                "chunking_contract_id": qualitative_basis["chunking_contract_id"],
                "material_snapshot_id": qualitative_basis["material_snapshot_id"],
                "analysis_unit_id": qualitative_basis["analysis_unit_id"],
                "analysis_set_id": qualitative_basis["analysis_set_id"],
                "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                "output_payload_hash": qualitative_basis["output_payload_hash"],
                "chunk_count": qualitative_basis["chunk_count"],
            }
        )
    db.commit()

    return _handoff_export_prepare_response(
        request_id=request_id,
        status=HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION[operator_decision],
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        analysis_run_id=analysis_run_id,
        result_review_record_ref=supplied_review_ref,
        package_review_preview_hash=supplied_package_preview_hash,
        reconciliation_record=reconciliation,
        packages=packages,
        prepare_state=prepare_state,
    )


def aps_handoff_dispatch(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for APS handoff dispatch.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_aps_handoff_dispatch_request"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()
    supplied_package_preview_hash = str(payload.get("package_review_preview_hash") or "").strip()
    reconciliation_record_id = str(payload.get("reconciliation_record_id") or "").strip()
    supplied_submit_ref = str(payload.get("package_review_submit_record_ref") or "").strip()
    supplied_package_review_state = str(payload.get("package_review_state") or "").strip()
    supplied_prepare_ref = str(payload.get("prepare_record_ref") or "").strip()
    supplied_handoff_export_state = str(payload.get("handoff_export_state") or "").strip()
    supplied_envelope_ref = str(payload.get("handoff_export_envelope_ref") or "").strip()
    handoff_target = str(payload.get("handoff_target") or "").strip()
    export_mode = str(payload.get("export_mode") or "").strip()
    aps_handoff_target = str(payload.get("aps_handoff_target") or "").strip()
    dispatch_mode = str(payload.get("dispatch_mode") or "").strip()
    operator_decision = str(payload.get("operator_decision") or "").strip()
    decision_notes = str(payload.get("decision_notes") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    raw_output_package_ids = payload.get("output_package_ids")
    raw_package_kinds = payload.get("package_kinds")
    raw_payload_refs = payload.get("payload_refs")
    raw_payload_hashes = payload.get("payload_hashes")

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("result_review_record_ref", supplied_review_ref),
            ("package_review_preview_hash", supplied_package_preview_hash),
            ("reconciliation_record_id", reconciliation_record_id),
            ("package_review_submit_record_ref", supplied_submit_ref),
            ("package_review_state", supplied_package_review_state),
            ("prepare_record_ref", supplied_prepare_ref),
            ("handoff_export_state", supplied_handoff_export_state),
            ("handoff_export_envelope_ref", supplied_envelope_ref),
            ("handoff_target", handoff_target),
            ("export_mode", export_mode),
            ("aps_handoff_target", aps_handoff_target),
            ("dispatch_mode", dispatch_mode),
            ("operator_decision", operator_decision),
        )
        if not value
    ]
    if not raw_output_package_ids:
        missing.append("output_package_ids")
    if not raw_package_kinds:
        missing.append("package_kinds")
    if not raw_payload_refs:
        missing.append("payload_refs")
    if not raw_payload_hashes:
        missing.append("payload_hashes")
    if missing:
        raise Layer3WorkbenchError(
            "missing_aps_handoff_dispatch_fields",
            f"APS handoff dispatch request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_aps_handoff_dispatch_request"],
        )

    blocked_payload_fields = aps_handoff_dispatch_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_scope_not_admitted",
            f"APS handoff dispatch request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_aps_handoff_dispatch_request"],
        )
    if handoff_target != "internal_export_envelope":
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_target_not_admitted",
            "handoff_target must be internal_export_envelope for APS handoff dispatch.",
            status="invalid",
            blocked_fields=["handoff_target"],
        )
    if export_mode != "prepare_only":
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_export_mode_not_admitted",
            "export_mode must be prepare_only for APS handoff dispatch.",
            status="invalid",
            blocked_fields=["export_mode"],
        )
    if aps_handoff_target != "aps_evidence_bundle":
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_target_family_not_admitted",
            "aps_handoff_target must be aps_evidence_bundle.",
            status="invalid",
            blocked_fields=["aps_handoff_target"],
        )
    if dispatch_mode != "server_side_aps_handoff":
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_mode_not_admitted",
            "dispatch_mode must be server_side_aps_handoff.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if operator_decision != APS_HANDOFF_DISPATCH_OPERATOR_DECISION:
        raise Layer3WorkbenchError(
            "unsupported_aps_handoff_dispatch_decision",
            "operator_decision must be dispatch_aps_handoff.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if supplied_package_review_state != PACKAGE_REVIEW_APPROVED_STATE:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_approved_package_review",
            "APS handoff dispatch requires package_review_state to be package_review_approved.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_state"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )
    if supplied_handoff_export_state != HANDOFF_EXPORT_PREPARED_STATE:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_prepared_handoff_export",
            "APS handoff dispatch requires handoff_export_state to be handoff_export_prepared.",
            status="blocked",
            http_status=409,
            blocked_fields=["handoff_export_state"],
            next_allowed_actions=["inspect_handoff_export_prepare_state"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_result_status_unavailable",
            "APS handoff dispatch requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_output_metadata_required",
            "APS handoff dispatch requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_inconsistent",
            "APS handoff dispatch could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_pass_run_mismatch",
            "APS handoff dispatch pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    associated_cohort_dispatch = False
    qualitative_aps_dispatch = False
    qualitative_basis = None
    if status_body.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT:
        associated_cohort_dispatch = _associated_cohort_aps_dispatch_source_admitted(
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        if not associated_cohort_dispatch:
            raise Layer3WorkbenchError(
                "associated_cohort_aps_handoff_dispatch_not_admitted",
                "APS handoff dispatch is admitted only for exact selected-pass descriptive associated-cohort result/status output.",
                status="blocked",
                http_status=409,
                next_allowed_actions=["inspect_execution_result_status"],
            )
    elif _qualitative_aps_aps_dispatch_source_admitted(
        status_body=status_body,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
    ):
        qualitative_aps_dispatch = True
        qualitative_basis = _require_qualitative_aps_package_review_authority(
            db,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        if supplied_analysis_run_id:
            raise Layer3WorkbenchError(
                "qualitative_aps_aps_handoff_dispatch_analysis_run_not_admitted",
                "Qualitative APS handoff dispatch must not provide analysis_run_id.",
                status="invalid",
                blocked_fields=["analysis_run_id"],
            )
    else:
        _ensure_result_status_downstream_source_admitted(
            status_body,
            error_code="associated_cohort_aps_handoff_dispatch_not_admitted",
            action_label="APS handoff dispatch",
        )
    if reconciliation is None:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_package_construction",
            "APS handoff dispatch requires an existing reconciliation record from package construction commit.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_package_construction_state"],
        )

    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_approved_result_review",
            "APS handoff dispatch requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )
    mismatched_review_fields = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
        }.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_trace_unresolved",
            "APS handoff dispatch requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    analysis_run_id = str(status_body.get("analysis_run_id") or "") or None
    if qualitative_aps_dispatch:
        expected_package_preview_hash = _qualitative_aps_package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_record_ref=supplied_review_ref,
            output_payload_ref=output_metadata_summary.get("output_payload_ref"),
            qualitative_basis=qualitative_basis,
        )
    else:
        expected_package_preview_hash = _package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            analysis_run_id=analysis_run_id,
            result_review_record_ref=supplied_review_ref,
            output_metadata_summary=output_metadata_summary,
        )
    if supplied_package_preview_hash != expected_package_preview_hash:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_preview_mismatch",
            "APS handoff dispatch must reference the current server-recomputed package-review preview hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_preview_hash"],
            next_allowed_actions=["refresh_package_review_preview"],
        )

    existing_dispatch = _aps_handoff_dispatch_from_reconciliation(reconciliation)
    all_packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .order_by(L3OutputPackage.package_kind.asc())
        .with_for_update()
        .all()
    )
    unexpected_package_kinds = _unexpected_package_kinds(
        all_packages,
        aps_handoff_dispatch_state=existing_dispatch,
    )
    if unexpected_package_kinds:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_unexpected_package_state",
            "APS handoff dispatch cannot proceed with unexpected package kinds on the reconciliation.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    packages = _review_source_packages(all_packages)
    if (
        len(packages) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    ):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_complete_package_set",
            "APS handoff dispatch requires exactly the reviewed canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["output_package_ids"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    ordered_packages = _packages_in_review_order(packages)
    if not isinstance(raw_output_package_ids, list):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_package_ids_invalid",
            "output_package_ids must be a list of the three reviewed output package ids.",
            status="invalid",
            blocked_fields=["output_package_ids"],
        )
    supplied_package_ids = [str(item or "").strip() for item in raw_output_package_ids]
    expected_package_ids = [package.output_package_id for package in ordered_packages]
    if supplied_package_ids != expected_package_ids:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_package_ids_mismatch",
            "Supplied output_package_ids do not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    if not isinstance(raw_package_kinds, list):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_package_kinds_invalid",
            "package_kinds must be the reviewed package kinds in server order.",
            status="invalid",
            blocked_fields=["package_kinds"],
        )
    supplied_package_kinds = [str(item or "").strip() for item in raw_package_kinds]
    expected_package_kinds = [package.package_kind for package in ordered_packages]
    if supplied_package_kinds != expected_package_kinds:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_package_kinds_mismatch",
            "Supplied package_kinds do not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_kinds"],
        )
    if any(not str(package.payload_ref or "").strip() or not str(package.payload_hash or "").strip() for package in ordered_packages):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_package_payload_identity_missing",
            "APS handoff dispatch requires stored package payload refs and hashes.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_refs", "payload_hashes"],
        )
    canonical_payload_refs = _canonical_payload_refs(payload_refs=raw_payload_refs, packages=packages)
    if canonical_payload_refs is None:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_payload_refs_mismatch",
            "Supplied payload_refs do not match the reviewed package payload refs.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_refs"],
        )
    if not isinstance(raw_payload_hashes, (list, dict)):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_payload_hashes_invalid",
            "payload_hashes must be either a list of package hashes or a mapping keyed by package kind or package id.",
            status="invalid",
            blocked_fields=["payload_hashes"],
        )
    canonical_payload_hashes = _canonical_payload_hashes(payload_hashes=raw_payload_hashes, packages=packages)
    if canonical_payload_hashes is None:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the reviewed package payload hashes.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_hashes"],
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_non_workbench_package_state",
            "APS handoff dispatch requires workbench package-construction commit provenance.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        )
    commit_mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": supplied_package_preview_hash,
            "result_review_record_ref": supplied_review_ref,
        }.items()
        if str(commit_summary.get(field) or "") != str(expected)
    ]
    if commit_mismatches:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_construction_mismatch",
            "Stored package-construction provenance does not match the supplied APS handoff authority.",
            status="conflict",
            http_status=409,
            blocked_fields=commit_mismatches,
        )

    package_review_submit = _package_review_submit_from_reconciliation(reconciliation)
    if package_review_submit is None or package_review_submit.get("package_review_state") != PACKAGE_REVIEW_APPROVED_STATE:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_approved_package_review",
            "APS handoff dispatch requires approved package-review submit state.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_state"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )
    if supplied_submit_ref != str(package_review_submit.get("submit_record_ref") or ""):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_submit_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match the approved package-review submit state.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_submit_record_ref"],
        )
    submit_mismatches = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "reconciliation_record_id": reconciliation_record_id,
        }.items()
        if str(package_review_submit.get(field) or "") != str(expected or "")
    ]
    if list(package_review_submit.get("output_package_ids") or []) != expected_package_ids:
        submit_mismatches.append("output_package_ids")
    if list(package_review_submit.get("package_kinds") or []) != expected_package_kinds:
        submit_mismatches.append("package_kinds")
    if list(package_review_submit.get("payload_hashes") or []) != canonical_payload_hashes:
        submit_mismatches.append("payload_hashes")
    if submit_mismatches:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_package_review_submit_mismatch",
            "Stored package-review submit authority does not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(submit_mismatches)),
        )
    if associated_cohort_dispatch:
        cohort_submit_mismatches = [
            field
            for field, expected in {
                "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
                "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
                "method": "descriptive_summary",
                "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
                "package_construction_source_gate": SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
                "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
            }.items()
            if package_review_submit.get(field) != expected
        ]
        if list(package_review_submit.get("source_dataset_version_ids") or []) != list(
            output_metadata_summary.get("source_dataset_version_ids") or []
        ):
            cohort_submit_mismatches.append("source_dataset_version_ids")
        if cohort_submit_mismatches:
            raise Layer3WorkbenchError(
                "associated_cohort_aps_handoff_dispatch_not_admitted",
                "Associated-cohort APS handoff dispatch requires exact approved cohort package-review submit authority.",
                status="blocked",
                http_status=409,
                blocked_fields=sorted(set(cohort_submit_mismatches)),
                next_allowed_actions=["inspect_package_review_submit_state"],
            )
    if qualitative_aps_dispatch:
        qualitative_submit_mismatches = [
            field
            for field, expected in {
                "pass_type": PASS_TYPE_SINGLE_ITEM,
                "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
                "method": QUAL_APS_METHOD_NAME,
                "source_gate": QUAL_APS_SOURCE_GATE,
                "package_construction_source_gate": SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
                "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
                "package_review_submit_schema_id": QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            }.items()
            if package_review_submit.get(field) != expected
        ]
        if list(package_review_submit.get("source_dataset_version_ids") or []) != []:
            qualitative_submit_mismatches.append("source_dataset_version_ids")
        if list(package_review_submit.get("payload_refs") or []) != canonical_payload_refs:
            qualitative_submit_mismatches.append("payload_refs")
        authority_basis = package_review_submit.get("authority_basis")
        if not isinstance(authority_basis, dict):
            qualitative_submit_mismatches.append("authority_basis")
        else:
            for field, expected in {
                "content_id": qualitative_basis["content_id"] if qualitative_basis is not None else "",
                "content_contract_id": qualitative_basis["content_contract_id"] if qualitative_basis is not None else "",
                "chunking_contract_id": qualitative_basis["chunking_contract_id"] if qualitative_basis is not None else "",
                "material_snapshot_id": qualitative_basis["material_snapshot_id"] if qualitative_basis is not None else "",
                "analysis_unit_id": qualitative_basis["analysis_unit_id"] if qualitative_basis is not None else "",
                "analysis_set_id": qualitative_basis["analysis_set_id"] if qualitative_basis is not None else "",
                "output_payload_hash": qualitative_basis["output_payload_hash"] if qualitative_basis is not None else "",
            }.items():
                if str(authority_basis.get(field) or "") != expected:
                    qualitative_submit_mismatches.append(field)
        if qualitative_submit_mismatches:
            raise Layer3WorkbenchError(
                "qualitative_aps_aps_handoff_dispatch_not_admitted",
                "Qualitative APS handoff dispatch requires exact approved qualitative APS package-review submit authority.",
                status="blocked",
                http_status=409,
                blocked_fields=sorted(set(qualitative_submit_mismatches)),
                next_allowed_actions=["inspect_package_review_submit_state"],
            )

    prepare_state = _handoff_export_prepare_from_reconciliation(reconciliation)
    if prepare_state is None or prepare_state.get("handoff_export_state") != HANDOFF_EXPORT_PREPARED_STATE:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_requires_prepared_handoff_export",
            "APS handoff dispatch requires recorded handoff_export_prepared state.",
            status="blocked",
            http_status=409,
            blocked_fields=["handoff_export_state"],
            next_allowed_actions=["record_handoff_export_prepare"],
        )
    if supplied_prepare_ref != str(prepare_state.get("prepare_record_ref") or ""):
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_prepare_ref_mismatch",
            "Supplied prepare_record_ref does not match the recorded handoff/export prepare state.",
            status="conflict",
            http_status=409,
            blocked_fields=["prepare_record_ref"],
        )
    envelope = prepare_state.get("handoff_export_envelope")
    envelope_ref = str(envelope.get("envelope_ref") or "").strip() if isinstance(envelope, dict) else ""
    if not envelope_ref or supplied_envelope_ref != envelope_ref:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_envelope_ref_mismatch",
            "Supplied handoff_export_envelope_ref does not match the recorded internal prepare envelope.",
            status="conflict",
            http_status=409,
            blocked_fields=["handoff_export_envelope_ref"],
        )
    prepare_mismatches = [
        field
        for field, expected in {
            "package_review_submit_record_ref": supplied_submit_ref,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "reconciliation_record_id": reconciliation_record_id,
        }.items()
        if str(prepare_state.get(field) or "") != str(expected or "")
    ]
    if list(prepare_state.get("output_package_ids") or []) != expected_package_ids:
        prepare_mismatches.append("output_package_ids")
    if list(prepare_state.get("package_kinds") or []) != expected_package_kinds:
        prepare_mismatches.append("package_kinds")
    if list(prepare_state.get("payload_refs") or []) != canonical_payload_refs:
        prepare_mismatches.append("payload_refs")
    if list(prepare_state.get("payload_hashes") or []) != canonical_payload_hashes:
        prepare_mismatches.append("payload_hashes")
    if prepare_mismatches:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_prepare_mismatch",
            "Stored handoff/export prepare authority does not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(prepare_mismatches)),
        )
    cohort_prepare_mismatches: list[str] = []
    if associated_cohort_dispatch:
        if not _associated_cohort_aps_dispatch_prepare_state_admitted(prepare_state):
            cohort_prepare_mismatches.append("handoff_export_state")
        if list(prepare_state.get("source_dataset_version_ids") or []) != list(
            output_metadata_summary.get("source_dataset_version_ids") or []
        ):
            cohort_prepare_mismatches.append("source_dataset_version_ids")
    if cohort_prepare_mismatches:
        raise Layer3WorkbenchError(
            "associated_cohort_aps_handoff_dispatch_not_admitted",
            "Associated-cohort APS handoff dispatch requires exact prepared cohort handoff/export authority.",
            status="blocked",
            http_status=409,
            blocked_fields=sorted(set(cohort_prepare_mismatches)),
            next_allowed_actions=["inspect_handoff_export_prepare_state"],
        )
    qualitative_prepare_mismatches: list[str] = []
    if qualitative_aps_dispatch:
        if not _qualitative_aps_aps_dispatch_prepare_state_admitted(prepare_state):
            qualitative_prepare_mismatches.append("handoff_export_state")
        if list(prepare_state.get("source_dataset_version_ids") or []) != []:
            qualitative_prepare_mismatches.append("source_dataset_version_ids")
        if qualitative_basis is not None:
            for field, expected in {
                "content_id": qualitative_basis["content_id"],
                "content_contract_id": qualitative_basis["content_contract_id"],
                "chunking_contract_id": qualitative_basis["chunking_contract_id"],
                "material_snapshot_id": qualitative_basis["material_snapshot_id"],
                "analysis_unit_id": qualitative_basis["analysis_unit_id"],
                "analysis_set_id": qualitative_basis["analysis_set_id"],
                "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                "output_payload_hash": qualitative_basis["output_payload_hash"],
            }.items():
                if str(prepare_state.get(field) or "") != str(expected or ""):
                    qualitative_prepare_mismatches.append(field)
    if qualitative_prepare_mismatches:
        raise Layer3WorkbenchError(
            "qualitative_aps_aps_handoff_dispatch_not_admitted",
            "Qualitative APS handoff dispatch requires exact prepared qualitative APS handoff/export authority.",
            status="blocked",
            http_status=409,
            blocked_fields=sorted(set(qualitative_prepare_mismatches)),
            next_allowed_actions=["inspect_handoff_export_prepare_state"],
        )

    source_package_refs = _package_ref_map(ordered_packages)
    source_package_hashes = _package_hash_map(ordered_packages)
    dispatch_basis = {
        "schema_id": "layer3.aps_handoff_dispatch_authority.v1",
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_refs": canonical_payload_refs,
        "payload_hashes": canonical_payload_hashes,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_envelope_ref": envelope_ref,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "operator_decision": APS_HANDOFF_DISPATCH_OPERATOR_DECISION,
        "decision_notes": decision_notes or None,
    }
    if associated_cohort_dispatch:
        dispatch_basis.update(
            {
                "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
                "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
                "method": "descriptive_summary",
                "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
                "package_construction_source_gate": SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
                "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
                "source_dataset_version_ids": _json_clone(
                    prepare_state.get("source_dataset_version_ids") or []
                ),
                "package_review_submit_schema_id": COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            }
        )
    if qualitative_aps_dispatch:
        dispatch_basis.update(
            {
                "pass_type": PASS_TYPE_SINGLE_ITEM,
                "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
                "method": QUAL_APS_METHOD_NAME,
                "source_gate": QUAL_APS_SOURCE_GATE,
                "package_construction_source_gate": SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
                "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
                "source_dataset_version_ids": [],
                "package_review_submit_schema_id": QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
                "content_id": qualitative_basis["content_id"] if qualitative_basis is not None else "",
                "content_contract_id": (
                    qualitative_basis["content_contract_id"] if qualitative_basis is not None else ""
                ),
                "chunking_contract_id": (
                    qualitative_basis["chunking_contract_id"] if qualitative_basis is not None else ""
                ),
                "material_snapshot_id": (
                    qualitative_basis["material_snapshot_id"] if qualitative_basis is not None else ""
                ),
                "analysis_unit_id": qualitative_basis["analysis_unit_id"] if qualitative_basis is not None else "",
                "analysis_set_id": qualitative_basis["analysis_set_id"] if qualitative_basis is not None else "",
                "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
                "output_payload_hash": (
                    qualitative_basis["output_payload_hash"] if qualitative_basis is not None else ""
                ),
                "chunk_count": qualitative_basis["chunk_count"] if qualitative_basis is not None else 0,
            }
        )
    aps_handoff_record_ref = _stable_id("l3-aps-handoff-dispatch", dispatch_basis)
    existing_aps_package = _aps_handoff_package_for_session(db, session_id=session_id)
    if existing_dispatch is not None:
        if (
            existing_dispatch.get("aps_handoff_record_ref") == aps_handoff_record_ref
            and existing_dispatch.get("client_request_id") == request_id
        ):
            if existing_aps_package is None or existing_aps_package.output_package_id != existing_dispatch.get("aps_output_package_id"):
                raise Layer3WorkbenchError(
                    "aps_handoff_dispatch_state_inconsistent",
                    "Recorded APS handoff dispatch state does not match an existing APS handoff package row.",
                    status="conflict",
                    http_status=409,
                    blocked_fields=["aps_output_package_id"],
                )
            return _aps_handoff_dispatch_response(
                request_id=request_id,
                status="already_dispatched",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                pass_run_id=pass_run_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                result_review_record_ref=supplied_review_ref,
                package_review_preview_hash=supplied_package_preview_hash,
                reconciliation_record=reconciliation,
                packages=packages,
                dispatch_state=existing_dispatch,
            )
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_already_recorded",
            "This prepared package set already has an APS handoff dispatch decision.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )
    if existing_aps_package is not None:
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_already_exists",
            "This session already has an APS evidence-bundle handoff package outside the workbench dispatch state.",
            status="conflict",
            http_status=409,
            blocked_fields=["session_id"],
        )

    try:
        aps_result = materialize_aps_handoff(db, session_id=session_id)
    except Layer3ApsHandoffError as exc:
        db.rollback()
        raise Layer3WorkbenchError(
            "aps_handoff_dispatch_blocked",
            f"APS handoff dispatch could not satisfy the existing owner-service contract: {exc}",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_handoff_target"],
            next_allowed_actions=["inspect_aps_handoff_provenance"],
        ) from exc

    aps_package = aps_result.output_package
    aps_summary = aps_package.summary_json or {}
    recorded_at = _utcnow_iso()
    dispatch_state = {
        "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
        "client_request_id": request_id,
        "aps_handoff_record_ref": aps_handoff_record_ref,
        "authority_basis": dispatch_basis,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_envelope_ref": envelope_ref,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "operator_decision": APS_HANDOFF_DISPATCH_OPERATOR_DECISION,
        "decision_notes": decision_notes or None,
        "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
        "aps_output_package_id": aps_package.output_package_id,
        "aps_output_package_kind": aps_package.package_kind,
        "aps_bundle_ref": aps_package.payload_ref,
        "aps_bundle_id": str(aps_summary.get("bundle_id") or ""),
        "aps_schema_id": str(aps_summary.get("aps_schema_id") or APS_HANDOFF_SCHEMA_ID),
        "source_package_refs": source_package_refs,
        "source_package_hashes": source_package_hashes,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_refs": canonical_payload_refs,
        "payload_hashes": canonical_payload_hashes,
        "pass_type": prepare_state.get("pass_type"),
        "pass_scope": prepare_state.get("pass_scope"),
        "method": prepare_state.get("method"),
        "source_gate": prepare_state.get("source_gate"),
        "package_construction_source_gate": prepare_state.get("package_construction_source_gate"),
        "source_shape": prepare_state.get("source_shape"),
        "source_dataset_version_ids": _json_clone(prepare_state.get("source_dataset_version_ids") or []),
        "package_review_submit_schema_id": prepare_state.get("package_review_submit_schema_id"),
        "recorded_at": recorded_at,
        "external_export_enabled": False,
        "download_enabled": False,
        "connector_dispatch_enabled": False,
        "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
    }
    if qualitative_aps_dispatch:
        dispatch_state.update(
            {
                "content_id": prepare_state.get("content_id"),
                "content_contract_id": prepare_state.get("content_contract_id"),
                "chunking_contract_id": prepare_state.get("chunking_contract_id"),
                "material_snapshot_id": prepare_state.get("material_snapshot_id"),
                "analysis_unit_id": prepare_state.get("analysis_unit_id"),
                "analysis_set_id": prepare_state.get("analysis_set_id"),
                "output_payload_ref": prepare_state.get("output_payload_ref"),
                "output_payload_hash": prepare_state.get("output_payload_hash"),
                "chunk_count": prepare_state.get("chunk_count"),
                "provider_public_url_enabled": False,
            }
        )
    reconciliation.summary_json = {
        **reconciliation_summary,
        "aps_handoff_dispatch": dispatch_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "aps_handoff_dispatch": {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "aps_handoff_record_ref": aps_handoff_record_ref,
            "prepare_record_ref": supplied_prepare_ref,
            "handoff_export_envelope_ref": envelope_ref,
            "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
            "operator_decision": APS_HANDOFF_DISPATCH_OPERATOR_DECISION,
            "decision_notes": decision_notes or None,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "analysis_run_id": analysis_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "pass_type": prepare_state.get("pass_type"),
            "pass_scope": prepare_state.get("pass_scope"),
            "method": prepare_state.get("method"),
            "source_gate": prepare_state.get("source_gate"),
            "package_construction_source_gate": prepare_state.get("package_construction_source_gate"),
            "source_shape": prepare_state.get("source_shape"),
            "source_dataset_version_ids": _json_clone(prepare_state.get("source_dataset_version_ids") or []),
            "package_review_submit_schema_id": prepare_state.get("package_review_submit_schema_id"),
            "aps_output_package_id": aps_package.output_package_id,
            "aps_bundle_ref": aps_package.payload_ref,
            "aps_bundle_id": str(aps_summary.get("bundle_id") or ""),
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _aps_handoff_dispatch_response(
        request_id=request_id,
        status="dispatched",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        result_review_record_ref=supplied_review_ref,
        package_review_preview_hash=supplied_package_preview_hash,
        reconciliation_record=reconciliation,
        packages=packages,
        dispatch_state=dispatch_state,
    )


def external_export_download_prepare(
    db: Session,
    payload: dict[str, Any],
    *,
    validate_source_artifact: bool = True,
) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for external export/download readiness preparation.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_external_export_download_prepare_request"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()
    supplied_package_preview_hash = str(payload.get("package_review_preview_hash") or "").strip()
    reconciliation_record_id = str(payload.get("reconciliation_record_id") or "").strip()
    supplied_submit_ref = str(payload.get("package_review_submit_record_ref") or "").strip()
    supplied_package_review_state = str(payload.get("package_review_state") or "").strip()
    supplied_prepare_ref = str(payload.get("prepare_record_ref") or "").strip()
    supplied_handoff_export_state = str(payload.get("handoff_export_state") or "").strip()
    supplied_envelope_ref = str(payload.get("handoff_export_envelope_ref") or "").strip()
    handoff_target = str(payload.get("handoff_target") or "").strip()
    export_mode = str(payload.get("export_mode") or "").strip()
    supplied_aps_handoff_record_ref = str(payload.get("aps_handoff_record_ref") or "").strip()
    supplied_aps_handoff_state = str(payload.get("aps_handoff_state") or "").strip()
    aps_handoff_target = str(payload.get("aps_handoff_target") or "").strip()
    dispatch_mode = str(payload.get("dispatch_mode") or "").strip()
    supplied_aps_output_package_id = str(payload.get("aps_output_package_id") or "").strip()
    supplied_aps_output_package_kind = str(payload.get("aps_output_package_kind") or "").strip()
    supplied_aps_bundle_ref = str(payload.get("aps_bundle_ref") or "").strip()
    supplied_aps_bundle_id = str(payload.get("aps_bundle_id") or "").strip()
    supplied_aps_schema_id = str(payload.get("aps_schema_id") or "").strip()
    export_download_target = str(payload.get("export_download_target") or "").strip()
    download_mode = str(payload.get("download_mode") or "").strip()
    operator_decision = str(payload.get("operator_decision") or "").strip()
    decision_notes = str(payload.get("decision_notes") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    supplied_aps_bundle_hash = str(payload.get("aps_bundle_hash") or "").strip()
    raw_aps_bundle_size = payload.get("aps_bundle_size_bytes")
    raw_output_package_ids = payload.get("output_package_ids")
    raw_package_kinds = payload.get("package_kinds")
    raw_payload_refs = payload.get("payload_refs")
    raw_payload_hashes = payload.get("payload_hashes")

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("result_review_record_ref", supplied_review_ref),
            ("package_review_preview_hash", supplied_package_preview_hash),
            ("reconciliation_record_id", reconciliation_record_id),
            ("package_review_submit_record_ref", supplied_submit_ref),
            ("package_review_state", supplied_package_review_state),
            ("prepare_record_ref", supplied_prepare_ref),
            ("handoff_export_state", supplied_handoff_export_state),
            ("handoff_export_envelope_ref", supplied_envelope_ref),
            ("handoff_target", handoff_target),
            ("export_mode", export_mode),
            ("aps_handoff_record_ref", supplied_aps_handoff_record_ref),
            ("aps_handoff_state", supplied_aps_handoff_state),
            ("aps_handoff_target", aps_handoff_target),
            ("dispatch_mode", dispatch_mode),
            ("aps_output_package_id", supplied_aps_output_package_id),
            ("aps_output_package_kind", supplied_aps_output_package_kind),
            ("aps_bundle_ref", supplied_aps_bundle_ref),
            ("aps_bundle_id", supplied_aps_bundle_id),
            ("aps_schema_id", supplied_aps_schema_id),
            ("export_download_target", export_download_target),
            ("download_mode", download_mode),
            ("operator_decision", operator_decision),
        )
        if not value
    ]
    if not raw_output_package_ids:
        missing.append("output_package_ids")
    if not raw_package_kinds:
        missing.append("package_kinds")
    if not raw_payload_refs:
        missing.append("payload_refs")
    if not raw_payload_hashes:
        missing.append("payload_hashes")
    if missing:
        raise Layer3WorkbenchError(
            "missing_external_export_download_prepare_fields",
            f"External export/download readiness request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_external_export_download_prepare_request"],
        )

    blocked_payload_fields = external_export_download_prepare_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "external_export_download_prepare_scope_not_admitted",
            f"External export/download readiness request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_external_export_download_prepare_request"],
        )
    if handoff_target != "internal_export_envelope":
        raise Layer3WorkbenchError(
            "external_export_download_prepare_handoff_target_not_admitted",
            "handoff_target must be internal_export_envelope.",
            status="invalid",
            blocked_fields=["handoff_target"],
        )
    if export_mode != "prepare_only":
        raise Layer3WorkbenchError(
            "external_export_download_prepare_export_mode_not_admitted",
            "export_mode must be prepare_only.",
            status="invalid",
            blocked_fields=["export_mode"],
        )
    if aps_handoff_target != "aps_evidence_bundle":
        raise Layer3WorkbenchError(
            "external_export_download_prepare_aps_target_not_admitted",
            "aps_handoff_target must be aps_evidence_bundle.",
            status="invalid",
            blocked_fields=["aps_handoff_target"],
        )
    if dispatch_mode != "server_side_aps_handoff":
        raise Layer3WorkbenchError(
            "external_export_download_prepare_dispatch_mode_not_admitted",
            "dispatch_mode must be server_side_aps_handoff.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if export_download_target != "aps_evidence_bundle_download_reference":
        raise Layer3WorkbenchError(
            "external_export_download_prepare_target_not_admitted",
            "export_download_target must be aps_evidence_bundle_download_reference.",
            status="invalid",
            blocked_fields=["export_download_target"],
        )
    if download_mode != "reference_only_prepare":
        raise Layer3WorkbenchError(
            "external_export_download_prepare_download_mode_not_admitted",
            "download_mode must be reference_only_prepare.",
            status="invalid",
            blocked_fields=["download_mode"],
        )
    if operator_decision != EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION:
        raise Layer3WorkbenchError(
            "unsupported_external_export_download_prepare_decision",
            "operator_decision must be prepare_external_export_download.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if supplied_package_review_state != PACKAGE_REVIEW_APPROVED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_approved_package_review",
            "External export/download readiness requires package_review_state to be package_review_approved.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_state"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )
    if supplied_handoff_export_state != HANDOFF_EXPORT_PREPARED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_prepared_handoff_export",
            "External export/download readiness requires handoff_export_state to be handoff_export_prepared.",
            status="blocked",
            http_status=409,
            blocked_fields=["handoff_export_state"],
            next_allowed_actions=["inspect_handoff_export_prepare_state"],
        )
    if supplied_aps_handoff_state != APS_HANDOFF_DISPATCHED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_aps_handoff_dispatch",
            "External export/download readiness requires aps_handoff_state to be aps_handoff_dispatched.",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_handoff_state"],
            next_allowed_actions=["inspect_aps_handoff_dispatch_state"],
        )
    if supplied_aps_output_package_kind != PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_aps_package_kind_mismatch",
            "aps_output_package_kind must be aps_evidence_bundle_handoff.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_output_package_kind"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_result_status_unavailable",
            "External export/download readiness requires available selected-pass result/status.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_output_metadata_required",
            "External export/download readiness requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_inconsistent",
            "External export/download readiness could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    associated_cohort_readiness = status_body.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT
    qualitative_aps_readiness_candidate = _qualitative_aps_external_export_download_deferred(
        {
            "pass_scope": status_body.get("pass_scope"),
            "source_gate": output_metadata_summary.get("source_gate"),
            "source_shape": output_metadata_summary.get("source_shape"),
        }
    )
    qualitative_aps_readiness = _qualitative_aps_aps_dispatch_source_admitted(
        status_body=status_body,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
    )
    if qualitative_aps_readiness_candidate and supplied_analysis_run_id:
        raise Layer3WorkbenchError(
            "qualitative_aps_external_export_download_analysis_run_not_admitted",
            "Qualitative APS external export/download readiness must not provide analysis_run_id.",
            status="invalid",
            blocked_fields=["analysis_run_id"],
        )
    if qualitative_aps_readiness_candidate and not qualitative_aps_readiness:
        raise Layer3WorkbenchError(
            "qualitative_aps_external_export_download_not_admitted",
            "Qualitative APS external export/download readiness requires exact standalone APS document execution authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
            next_allowed_actions=["inspect_qualitative_aps_execution_authority"],
        )
    if associated_cohort_readiness and not _associated_cohort_result_source_admitted(
        status_body=status_body,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
    ):
        raise Layer3WorkbenchError(
            "associated_cohort_external_export_download_prepare_not_admitted",
            "Associated-cohort external export/download readiness requires exact selected-pass descriptive cohort result/status authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
            next_allowed_actions=["inspect_execution_result_status"],
        )
    if reconciliation is None:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_package_construction",
            "External export/download readiness requires an existing package construction reconciliation.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_package_construction_state"],
        )

    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_approved_result_review",
            "External export/download readiness requires approved selected-pass result review.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "external_export_download_prepare_result_review_mismatch",
            "Supplied result_review_record_ref does not match the approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )
    if associated_cohort_readiness and not review_state_is_admitted_associated_cohort(review_state):
        raise Layer3WorkbenchError(
            "associated_cohort_external_export_download_prepare_not_admitted",
            "Associated-cohort external export/download readiness requires exact approved cohort result-review authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
            next_allowed_actions=["inspect_execution_result_review_state"],
        )
    mismatched_review_fields = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
        }.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_result_review_mismatch",
            "Stored result-review state does not match the supplied authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )

    analysis_run_id = str(status_body.get("analysis_run_id") or "") or None
    qualitative_basis = None
    if qualitative_aps_readiness:
        qualitative_basis = _require_qualitative_aps_package_review_authority(
            db,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            status_body=status_body,
            pass_run=pass_run,
            output_metadata_summary=output_metadata_summary,
        )
        expected_package_preview_hash = _qualitative_aps_package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_record_ref=supplied_review_ref,
            output_payload_ref=output_metadata_summary.get("output_payload_ref"),
            qualitative_basis=qualitative_basis,
        )
    else:
        expected_package_preview_hash = _package_review_preview_hash(
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            preview_id=preview_id,
            preview_hash=preview_hash,
            analysis_run_id=analysis_run_id,
            result_review_record_ref=supplied_review_ref,
            output_metadata_summary=output_metadata_summary,
        )
    if supplied_package_preview_hash != expected_package_preview_hash:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_preview_mismatch",
            "External export/download readiness must reference the current package-review preview hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_preview_hash"],
            next_allowed_actions=["refresh_package_review_preview"],
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    existing_readiness = _external_export_download_prepare_from_reconciliation(reconciliation)
    recorded_dispatch = _aps_handoff_dispatch_from_reconciliation(reconciliation)
    all_packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .order_by(L3OutputPackage.package_kind.asc())
        .with_for_update()
        .all()
    )
    unexpected_package_kinds = _unexpected_package_kinds(all_packages, aps_handoff_dispatch_state=recorded_dispatch)
    if unexpected_package_kinds:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_unexpected_package_state",
            "External export/download readiness cannot proceed with unexpected package kinds on the reconciliation.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    packages = _review_source_packages(all_packages)
    if (
        len(packages) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    ):
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_complete_package_set",
            "External export/download readiness requires the reviewed package set.",
            status="blocked",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    ordered_packages = _packages_in_review_order(packages)
    expected_package_ids = [package.output_package_id for package in ordered_packages]
    expected_package_kinds = [package.package_kind for package in ordered_packages]
    supplied_package_ids = [str(item or "").strip() for item in raw_output_package_ids] if isinstance(raw_output_package_ids, list) else []
    if supplied_package_ids != expected_package_ids:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_package_ids_mismatch",
            "Supplied output_package_ids do not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    supplied_package_kinds = [str(item or "").strip() for item in raw_package_kinds] if isinstance(raw_package_kinds, list) else []
    if supplied_package_kinds != expected_package_kinds:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_package_kinds_mismatch",
            "Supplied package_kinds do not match the reviewed package set.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_kinds"],
        )
    canonical_payload_refs = _canonical_payload_refs(payload_refs=raw_payload_refs, packages=packages)
    if canonical_payload_refs is None:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_payload_refs_mismatch",
            "Supplied payload_refs do not match the reviewed package payload refs.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_refs"],
        )
    if not isinstance(raw_payload_hashes, (list, dict)):
        raise Layer3WorkbenchError(
            "external_export_download_prepare_payload_hashes_invalid",
            "payload_hashes must be either a list of package hashes or a mapping keyed by package kind or package id.",
            status="invalid",
            blocked_fields=["payload_hashes"],
        )
    canonical_payload_hashes = _canonical_payload_hashes(payload_hashes=raw_payload_hashes, packages=packages)
    if canonical_payload_hashes is None:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the reviewed package payload hashes.",
            status="conflict",
            http_status=409,
            blocked_fields=["payload_hashes"],
        )

    package_review_submit = _package_review_submit_from_reconciliation(reconciliation)
    if package_review_submit is None or package_review_submit.get("package_review_state") != PACKAGE_REVIEW_APPROVED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_approved_package_review",
            "External export/download readiness requires approved package-review submit state.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_state"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )
    if supplied_submit_ref != str(package_review_submit.get("submit_record_ref") or ""):
        raise Layer3WorkbenchError(
            "external_export_download_prepare_submit_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match the approved package-review submit state.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_submit_record_ref"],
        )
    submit_mismatches = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "reconciliation_record_id": reconciliation_record_id,
        }.items()
        if str(package_review_submit.get(field) or "") != str(expected or "")
    ]
    if list(package_review_submit.get("output_package_ids") or []) != expected_package_ids:
        submit_mismatches.append("output_package_ids")
    if list(package_review_submit.get("package_kinds") or []) != expected_package_kinds:
        submit_mismatches.append("package_kinds")
    if list(package_review_submit.get("payload_hashes") or []) != canonical_payload_hashes:
        submit_mismatches.append("payload_hashes")
    if submit_mismatches:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_package_review_submit_mismatch",
            "Stored package-review submit authority does not match the supplied readiness basis.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(submit_mismatches)),
        )
    if associated_cohort_readiness and not _associated_cohort_readiness_submit_state_admitted(
        package_review_submit,
        output_metadata_summary=output_metadata_summary,
    ):
        raise Layer3WorkbenchError(
            "associated_cohort_external_export_download_prepare_not_admitted",
            "Associated-cohort external export/download readiness requires exact approved cohort package-review submit authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_submit_record_ref"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )
    if qualitative_aps_readiness and not _qualitative_aps_external_export_submit_state_admitted(
        package_review_submit,
        qualitative_basis=qualitative_basis,
        payload_refs=canonical_payload_refs,
    ):
        raise Layer3WorkbenchError(
            "qualitative_aps_external_export_download_prepare_not_admitted",
            "Qualitative APS external export/download readiness requires exact approved qualitative package-review submit authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_review_submit_record_ref"],
            next_allowed_actions=["inspect_package_review_submit_state"],
        )

    prepare_state = _handoff_export_prepare_from_reconciliation(reconciliation)
    if prepare_state is None or prepare_state.get("handoff_export_state") != HANDOFF_EXPORT_PREPARED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_prepared_handoff_export",
            "External export/download readiness requires recorded handoff_export_prepared state.",
            status="blocked",
            http_status=409,
            blocked_fields=["handoff_export_state"],
            next_allowed_actions=["record_handoff_export_prepare"],
        )
    envelope = prepare_state.get("handoff_export_envelope")
    envelope_ref = str(envelope.get("envelope_ref") or "").strip() if isinstance(envelope, dict) else ""
    if supplied_prepare_ref != str(prepare_state.get("prepare_record_ref") or ""):
        raise Layer3WorkbenchError(
            "external_export_download_prepare_prepare_ref_mismatch",
            "Supplied prepare_record_ref does not match the recorded handoff/export prepare state.",
            status="conflict",
            http_status=409,
            blocked_fields=["prepare_record_ref"],
        )
    if not envelope_ref or supplied_envelope_ref != envelope_ref:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_envelope_ref_mismatch",
            "Supplied handoff_export_envelope_ref does not match the recorded internal prepare envelope.",
            status="conflict",
            http_status=409,
            blocked_fields=["handoff_export_envelope_ref"],
        )
    prepare_mismatches = [
        field
        for field, expected in {
            "package_review_submit_record_ref": supplied_submit_ref,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "reconciliation_record_id": reconciliation_record_id,
        }.items()
        if str(prepare_state.get(field) or "") != str(expected or "")
    ]
    if list(prepare_state.get("output_package_ids") or []) != expected_package_ids:
        prepare_mismatches.append("output_package_ids")
    if list(prepare_state.get("package_kinds") or []) != expected_package_kinds:
        prepare_mismatches.append("package_kinds")
    if list(prepare_state.get("payload_refs") or []) != canonical_payload_refs:
        prepare_mismatches.append("payload_refs")
    if list(prepare_state.get("payload_hashes") or []) != canonical_payload_hashes:
        prepare_mismatches.append("payload_hashes")
    if prepare_mismatches:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_prepare_mismatch",
            "Stored handoff/export prepare authority does not match the supplied readiness basis.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(prepare_mismatches)),
        )
    cohort_prepare_mismatches: list[str] = []
    if associated_cohort_readiness:
        if not _associated_cohort_aps_dispatch_prepare_state_admitted(prepare_state):
            cohort_prepare_mismatches.append("handoff_export_state")
        if list(prepare_state.get("source_dataset_version_ids") or []) != list(
            output_metadata_summary.get("source_dataset_version_ids") or []
        ):
            cohort_prepare_mismatches.append("source_dataset_version_ids")
    if cohort_prepare_mismatches:
        raise Layer3WorkbenchError(
            "associated_cohort_external_export_download_prepare_not_admitted",
            "Associated-cohort external export/download readiness requires exact prepared cohort handoff/export authority.",
            status="blocked",
            http_status=409,
            blocked_fields=sorted(set(cohort_prepare_mismatches)),
            next_allowed_actions=["inspect_handoff_export_prepare_state"],
        )
    if qualitative_aps_readiness and not _qualitative_aps_aps_dispatch_prepare_state_admitted(prepare_state):
        raise Layer3WorkbenchError(
            "qualitative_aps_external_export_download_prepare_not_admitted",
            "Qualitative APS external export/download readiness requires exact prepared qualitative handoff/export authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["prepare_record_ref"],
            next_allowed_actions=["inspect_handoff_export_prepare_state"],
        )
    recorded_dispatch = _aps_handoff_dispatch_from_reconciliation(reconciliation)
    if recorded_dispatch is None or recorded_dispatch.get("aps_handoff_state") != APS_HANDOFF_DISPATCHED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_requires_aps_handoff_dispatch",
            "External export/download readiness requires recorded APS handoff dispatch.",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_handoff_state"],
            next_allowed_actions=["record_aps_handoff_dispatch"],
        )
    bundle_identity = _aps_bundle_identity_for_external_export_download(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
        dispatch_state=recorded_dispatch,
        error_prefix="external_export_download_prepare",
        existing_readiness=existing_readiness,
        validate_source_artifact=validate_source_artifact,
    )
    dispatch_mismatches = [
        field
        for field, expected in {
            "aps_handoff_record_ref": supplied_aps_handoff_record_ref,
            "package_review_submit_record_ref": supplied_submit_ref,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "prepare_record_ref": supplied_prepare_ref,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "handoff_export_envelope_ref": envelope_ref,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": supplied_review_ref,
            "package_review_preview_hash": supplied_package_preview_hash,
            "reconciliation_record_id": reconciliation_record_id,
        }.items()
        if str(recorded_dispatch.get(field) or "") != str(expected or "")
    ]
    if list(recorded_dispatch.get("output_package_ids") or []) != expected_package_ids:
        dispatch_mismatches.append("output_package_ids")
    if list(recorded_dispatch.get("package_kinds") or []) != expected_package_kinds:
        dispatch_mismatches.append("package_kinds")
    if list(recorded_dispatch.get("payload_refs") or []) != canonical_payload_refs:
        dispatch_mismatches.append("payload_refs")
    if list(recorded_dispatch.get("payload_hashes") or []) != canonical_payload_hashes:
        dispatch_mismatches.append("payload_hashes")
    if dispatch_mismatches:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_aps_dispatch_mismatch",
            "Stored APS handoff dispatch authority does not match the supplied readiness basis.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(dispatch_mismatches)),
        )
    cohort_dispatch_mismatches: list[str] = []
    if associated_cohort_readiness:
        if not _associated_cohort_aps_dispatch_prepare_state_admitted(recorded_dispatch):
            cohort_dispatch_mismatches.append("aps_handoff_record_ref")
        if list(recorded_dispatch.get("source_dataset_version_ids") or []) != list(
            output_metadata_summary.get("source_dataset_version_ids") or []
        ):
            cohort_dispatch_mismatches.append("source_dataset_version_ids")
    if cohort_dispatch_mismatches:
        raise Layer3WorkbenchError(
            "associated_cohort_external_export_download_prepare_not_admitted",
            "Associated-cohort external export/download readiness requires exact cohort APS handoff dispatch authority.",
            status="blocked",
            http_status=409,
            blocked_fields=sorted(set(cohort_dispatch_mismatches)),
            next_allowed_actions=["inspect_aps_handoff_dispatch_state"],
        )
    if qualitative_aps_readiness and not _qualitative_aps_external_export_download_admitted(recorded_dispatch):
        raise Layer3WorkbenchError(
            "qualitative_aps_external_export_download_prepare_not_admitted",
            "Qualitative APS external export/download readiness requires exact qualitative APS handoff dispatch authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_handoff_record_ref"],
            next_allowed_actions=["inspect_aps_handoff_dispatch_state"],
        )
    for field, supplied, expected in (
        ("aps_output_package_id", supplied_aps_output_package_id, bundle_identity["aps_output_package_id"]),
        ("aps_output_package_kind", supplied_aps_output_package_kind, bundle_identity["aps_output_package_kind"]),
        ("aps_bundle_ref", supplied_aps_bundle_ref, bundle_identity["aps_bundle_ref"]),
        ("aps_bundle_id", supplied_aps_bundle_id, bundle_identity["aps_bundle_id"]),
        ("aps_schema_id", supplied_aps_schema_id, bundle_identity["aps_schema_id"]),
    ):
        if str(supplied or "") != str(expected or ""):
            raise Layer3WorkbenchError(
                f"external_export_download_prepare_{field}_mismatch",
                f"Supplied {field} does not match the recorded APS handoff artifact.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )
    if supplied_aps_bundle_hash and supplied_aps_bundle_hash != bundle_identity["source_artifact_hash"]:
        raise Layer3WorkbenchError(
            "external_export_download_prepare_aps_bundle_hash_mismatch",
            "Supplied aps_bundle_hash does not match the existing APS bundle artifact hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_hash"],
        )
    if raw_aps_bundle_size is not None:
        try:
            supplied_size = int(raw_aps_bundle_size)
        except (TypeError, ValueError):
            raise Layer3WorkbenchError(
                "external_export_download_prepare_aps_bundle_size_invalid",
                "aps_bundle_size_bytes must be an integer when supplied.",
                status="invalid",
                blocked_fields=["aps_bundle_size_bytes"],
            ) from None
        if supplied_size != bundle_identity["source_artifact_size_bytes"]:
            raise Layer3WorkbenchError(
                "external_export_download_prepare_aps_bundle_size_mismatch",
                "Supplied aps_bundle_size_bytes does not match the existing APS bundle artifact size.",
                status="conflict",
                http_status=409,
                blocked_fields=["aps_bundle_size_bytes"],
            )

    source_package_refs = _package_ref_map(ordered_packages)
    source_package_hashes = _package_hash_map(ordered_packages)
    readiness_basis = {
        "schema_id": "layer3.external_export_download_prepare_authority.v1",
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_refs": canonical_payload_refs,
        "payload_hashes": canonical_payload_hashes,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_envelope_ref": envelope_ref,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_record_ref": supplied_aps_handoff_record_ref,
        "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "aps_output_package_id": bundle_identity["aps_output_package_id"],
        "aps_output_package_kind": bundle_identity["aps_output_package_kind"],
        "aps_bundle_ref": bundle_identity["aps_bundle_ref"],
        "aps_bundle_id": bundle_identity["aps_bundle_id"],
        "aps_schema_id": bundle_identity["aps_schema_id"],
        "source_package_refs": source_package_refs,
        "source_package_hashes": source_package_hashes,
        "source_artifact_hash": bundle_identity["source_artifact_hash"],
        "source_artifact_size_bytes": bundle_identity["source_artifact_size_bytes"],
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "decision_notes": decision_notes or None,
    }
    if associated_cohort_readiness:
        readiness_basis.update(
            {
                "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
                "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
                "method": "descriptive_summary",
                "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
                "package_construction_source_gate": SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
                "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
                "source_dataset_version_ids": _json_clone(
                    recorded_dispatch.get("source_dataset_version_ids") or []
                ),
                "package_review_submit_schema_id": COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            }
        )
    elif qualitative_aps_readiness:
        readiness_basis.update(_cohort_readiness_identity(recorded_dispatch))
    external_export_download_record_ref = _stable_id("l3-external-export-download-prepare", readiness_basis)
    if existing_readiness is not None:
        if (
            existing_readiness.get("external_export_download_record_ref") == external_export_download_record_ref
            and existing_readiness.get("client_request_id") == request_id
        ):
            return _external_export_download_prepare_response(
                request_id=request_id,
                status="already_prepared",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                pass_run_id=pass_run_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                result_review_record_ref=supplied_review_ref,
                package_review_preview_hash=supplied_package_preview_hash,
                reconciliation_record=reconciliation,
                packages=packages,
                readiness_state=existing_readiness,
            )
        raise Layer3WorkbenchError(
            "external_export_download_prepare_already_recorded",
            "This APS handoff dispatch already has an external export/download readiness decision.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )

    recorded_at = _utcnow_iso()
    descriptor_basis = {
        **readiness_basis,
        "schema_id": "layer3.external_export_download_descriptor_authority.v1",
    }
    descriptor_ref = _stable_id("l3-external-export-download-descriptor", descriptor_basis)
    descriptor = {
        "schema_id": "layer3.external_export_download_descriptor.v1",
        "descriptor_ref": descriptor_ref,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "aps_handoff_record_ref": supplied_aps_handoff_record_ref,
        "aps_output_package_id": bundle_identity["aps_output_package_id"],
        "aps_output_package_kind": bundle_identity["aps_output_package_kind"],
        "aps_bundle_ref": bundle_identity["aps_bundle_ref"],
        "aps_bundle_id": bundle_identity["aps_bundle_id"],
        "aps_schema_id": bundle_identity["aps_schema_id"],
        "source_artifact_ref": bundle_identity["source_artifact_ref"],
        "source_artifact_schema_id": bundle_identity["source_artifact_schema_id"],
        "source_artifact_hash": bundle_identity["source_artifact_hash"],
        "source_artifact_size_bytes": bundle_identity["source_artifact_size_bytes"],
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "prepared_at": recorded_at,
        "browser_download_enabled": False,
        "download_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
    }
    readiness_state = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "client_request_id": request_id,
        "external_export_download_record_ref": external_export_download_record_ref,
        "export_download_descriptor_ref": descriptor_ref,
        "external_export_download_descriptor": descriptor,
        "authority_basis": readiness_basis,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_envelope_ref": envelope_ref,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_record_ref": supplied_aps_handoff_record_ref,
        "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "decision_notes": decision_notes or None,
        "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "aps_output_package_id": bundle_identity["aps_output_package_id"],
        "aps_output_package_kind": bundle_identity["aps_output_package_kind"],
        "aps_bundle_ref": bundle_identity["aps_bundle_ref"],
        "aps_bundle_id": bundle_identity["aps_bundle_id"],
        "aps_schema_id": bundle_identity["aps_schema_id"],
        "source_artifact_ref": bundle_identity["source_artifact_ref"],
        "source_artifact_schema_id": bundle_identity["source_artifact_schema_id"],
        "source_artifact_hash": bundle_identity["source_artifact_hash"],
        "source_artifact_size_bytes": bundle_identity["source_artifact_size_bytes"],
        "source_package_refs": source_package_refs,
        "source_package_hashes": source_package_hashes,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_refs": canonical_payload_refs,
        "payload_hashes": canonical_payload_hashes,
        "recorded_at": recorded_at,
        "browser_download_enabled": False,
        "download_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
    }
    if associated_cohort_readiness:
        readiness_state.update(
            {
                "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
                "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
                "method": "descriptive_summary",
                "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
                "package_construction_source_gate": SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
                "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
                "source_dataset_version_ids": _json_clone(
                    recorded_dispatch.get("source_dataset_version_ids") or []
                ),
                "package_review_submit_schema_id": COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            }
        )
        readiness_state["delivery_ui"] = _associated_cohort_delivery_ui_state(readiness_state)
    elif qualitative_aps_readiness:
        readiness_state.update(_cohort_readiness_identity(recorded_dispatch))
    reconciliation.summary_json = {
        **reconciliation_summary,
        "external_export_download_prepare": readiness_state,
    }
    external_export_download_session_state = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "external_export_download_record_ref": external_export_download_record_ref,
        "export_download_descriptor_ref": descriptor_ref,
        "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "decision_notes": decision_notes or None,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "analysis_run_id": analysis_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "aps_handoff_record_ref": supplied_aps_handoff_record_ref,
        "aps_output_package_id": bundle_identity["aps_output_package_id"],
        "aps_bundle_ref": bundle_identity["aps_bundle_ref"],
        "aps_bundle_id": bundle_identity["aps_bundle_id"],
        "source_artifact_hash": bundle_identity["source_artifact_hash"],
        "source_artifact_size_bytes": bundle_identity["source_artifact_size_bytes"],
        "browser_download_enabled": False,
        "download_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
    }
    external_export_download_session_state.update(_cohort_readiness_identity(readiness_state))
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "external_export_download_prepare": external_export_download_session_state,
    }
    db.commit()

    return _external_export_download_prepare_response(
        request_id=request_id,
        status="prepared",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        result_review_record_ref=supplied_review_ref,
        package_review_preview_hash=supplied_package_preview_hash,
        reconciliation_record=reconciliation,
        packages=packages,
        readiness_state=readiness_state,
    )


def external_export_download_deliver(db: Session, payload: dict[str, Any]) -> ExternalExportDownloadDelivery:
    delivery_request = external_export_download_delivery_request_fields(payload)
    request_id = delivery_request.request_id
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for external export/download delivery.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_external_export_download_delivery_request"],
        )

    session_id = delivery_request.session_id
    reconciliation_record_id = delivery_request.reconciliation_record_id
    supplied_readiness_ref = delivery_request.supplied_readiness_ref
    supplied_descriptor_ref = delivery_request.supplied_descriptor_ref
    supplied_readiness_state = delivery_request.supplied_readiness_state
    delivery_mode = delivery_request.delivery_mode
    operator_decision = delivery_request.operator_decision
    export_download_target = delivery_request.export_download_target
    download_mode = delivery_request.download_mode
    supplied_aps_bundle_ref = delivery_request.supplied_aps_bundle_ref
    supplied_aps_bundle_id = delivery_request.supplied_aps_bundle_id
    supplied_aps_schema_id = delivery_request.supplied_aps_schema_id
    missing = delivery_request.missing_fields
    if missing:
        raise Layer3WorkbenchError(
            "missing_external_export_download_delivery_fields",
            f"External export/download delivery request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_external_export_download_delivery_request"],
        )

    blocked_payload_fields = external_export_download_delivery_blocked_fields(payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "external_export_download_delivery_scope_not_admitted",
            f"External export/download delivery request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_external_export_download_delivery_request"],
        )
    if export_download_target != "aps_evidence_bundle_download_reference":
        raise Layer3WorkbenchError(
            "external_export_download_delivery_target_not_admitted",
            "export_download_target must be aps_evidence_bundle_download_reference.",
            status="invalid",
            blocked_fields=["export_download_target"],
        )
    if download_mode != "reference_only_prepare":
        raise Layer3WorkbenchError(
            "external_export_download_delivery_download_mode_not_admitted",
            "download_mode must be reference_only_prepare.",
            status="invalid",
            blocked_fields=["download_mode"],
        )
    if delivery_mode != "same_origin_artifact_stream":
        raise Layer3WorkbenchError(
            "external_export_download_delivery_mode_not_admitted",
            "delivery_mode must be same_origin_artifact_stream.",
            status="invalid",
            blocked_fields=["delivery_mode"],
        )
    if operator_decision != EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION:
        raise Layer3WorkbenchError(
            "unsupported_external_export_download_delivery_decision",
            "operator_decision must be deliver_external_export_download.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if supplied_readiness_state != EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_requires_prepared_readiness",
            "External export/download delivery requires external_export_download_state to be external_export_download_prepared.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_state"],
            next_allowed_actions=["record_external_export_download_prepare"],
        )

    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    readiness_state = _external_export_download_prepare_from_reconciliation(reconciliation)
    if readiness_state is None or readiness_state.get("external_export_download_state") != EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_requires_prepared_readiness",
            "External export/download delivery requires recorded external_export_download_prepared state.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_state"],
            next_allowed_actions=["record_external_export_download_prepare"],
        )
    if not str(readiness_state.get("client_request_id") or "").strip():
        raise Layer3WorkbenchError(
            "external_export_download_delivery_readiness_request_id_missing",
            "Recorded external export/download readiness is missing its idempotency basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )
    for field, supplied, expected in external_export_download_delivery_readiness_mismatches(
        delivery_request,
        readiness_state,
    ):
        raise Layer3WorkbenchError(
            f"external_export_download_delivery_{field}_mismatch",
            f"Supplied {field} does not match recorded external export/download readiness.",
            status="conflict",
            http_status=409,
            blocked_fields=[field],
        )

    validation_body = external_export_download_prepare(
        db,
        _external_export_download_prepare_payload_for_delivery(payload, readiness_state=readiness_state),
        validate_source_artifact=False,
    )
    if validation_body.get("external_export_download_record_ref") != supplied_readiness_ref:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_readiness_mismatch",
            "Validated readiness authority does not match the requested delivery record.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )

    descriptor = readiness_state.get("external_export_download_descriptor")
    if not isinstance(descriptor, dict) or descriptor.get("descriptor_ref") != supplied_descriptor_ref:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_descriptor_mismatch",
            "Recorded external export/download descriptor is missing or stale.",
            status="conflict",
            http_status=409,
            blocked_fields=["export_download_descriptor_ref"],
        )
    source_artifact_ref = str(descriptor.get("source_artifact_ref") or "").strip()
    if not source_artifact_ref or source_artifact_ref != supplied_aps_bundle_ref:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_source_artifact_mismatch",
            "Recorded source artifact does not match the supplied APS bundle ref.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
        )
    expected_artifact_hash = str(readiness_state.get("source_artifact_hash") or "")
    try:
        expected_artifact_size = int(readiness_state.get("source_artifact_size_bytes") or -1)
    except (TypeError, ValueError):
        expected_artifact_size = -1

    db.rollback()

    return _external_export_download_delivery_response(
        session_id=session_id,
        supplied_aps_bundle_id=supplied_aps_bundle_id,
        supplied_readiness_ref=supplied_readiness_ref,
        source_artifact_ref=source_artifact_ref,
        expected_artifact_hash=expected_artifact_hash,
        expected_artifact_size=expected_artifact_size,
        validation_body=validation_body,
    )


def _signed_reference_required_cohort_authority(authority: dict[str, Any]) -> list[str]:
    required = (
        ("pass_type", PASS_TYPE_ASSOCIATED_COHORT),
        ("pass_scope", PASS_SCOPE_QUANT_ASSOCIATED_COHORT),
        ("method", "descriptive_summary"),
        ("source_gate", SOURCE_GATE_COHORT_DESC_FREEZE),
        ("source_shape", COHORT_SHAPE_ALIGNED_WIDE_TABLE),
    )
    return [field for field, expected in required if authority.get(field) != expected]


def _signed_reference_authority_basis(
    *,
    payload: dict[str, Any],
    delivery: ExternalExportDownloadDelivery,
) -> dict[str, Any]:
    authority = delivery.authority
    return {
        "session_id": str(payload.get("session_id") or ""),
        "analysis_plan_id": str(payload.get("analysis_plan_id") or ""),
        "pass_run_id": str(payload.get("pass_run_id") or ""),
        "preview_id": str(payload.get("preview_id") or ""),
        "preview_hash": str(payload.get("preview_hash") or ""),
        "result_review_record_ref": str(payload.get("result_review_record_ref") or ""),
        "package_review_preview_hash": str(payload.get("package_review_preview_hash") or ""),
        "reconciliation_record_id": str(payload.get("reconciliation_record_id") or ""),
        "package_review_submit_record_ref": str(payload.get("package_review_submit_record_ref") or ""),
        "prepare_record_ref": str(payload.get("prepare_record_ref") or ""),
        "aps_handoff_record_ref": str(payload.get("aps_handoff_record_ref") or ""),
        "external_export_download_record_ref": str(payload.get("external_export_download_record_ref") or ""),
        "export_download_descriptor_ref": str(payload.get("export_download_descriptor_ref") or ""),
        "aps_bundle_ref": str(payload.get("aps_bundle_ref") or ""),
        "aps_bundle_id": str(payload.get("aps_bundle_id") or ""),
        "aps_schema_id": str(payload.get("aps_schema_id") or ""),
        "pass_type": authority.get("pass_type"),
        "pass_scope": authority.get("pass_scope"),
        "method": authority.get("method"),
        "source_gate": authority.get("source_gate"),
        "source_shape": authority.get("source_shape"),
        "source_dataset_version_ids": _json_clone(authority.get("source_dataset_version_ids") or []),
        "source_artifact_ref": authority.get("source_artifact_ref"),
        "source_artifact_hash": delivery.headers.get("X-Layer3-Source-Artifact-Hash"),
        "source_artifact_size_bytes": int(delivery.artifact_path.stat().st_size),
    }


def _signed_reference_token_body(
    *,
    payload: dict[str, Any],
    delivery: ExternalExportDownloadDelivery,
    now_epoch: int,
) -> dict[str, Any]:
    bucket_start = now_epoch - (now_epoch % EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_TTL_SECONDS)
    expires_at_epoch = bucket_start + EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_TTL_SECONDS
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "issued_at_epoch": bucket_start,
        "expires_at_epoch": expires_at_epoch,
        "delivery_payload": _json_clone(payload),
        "delivery_authority": _signed_reference_authority_basis(payload=payload, delivery=delivery),
    }


def _encode_signed_reference_token(body: dict[str, Any]) -> str:
    encoded_body = _canonical_json_bytes(body)
    signature = hmac.digest(_signed_reference_signing_key(), encoded_body, "sha256").hex()
    return f"{_urlsafe_b64encode(encoded_body)}.{signature}"


def _decode_signed_reference_token(token: str) -> dict[str, Any]:
    try:
        encoded_body, supplied_signature = token.split(".", 1)
        body_bytes = _urlsafe_b64decode(encoded_body)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_malformed",
            "Signed delivery reference token is malformed.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        ) from exc
    expected_signature = hmac.digest(_signed_reference_signing_key(), body_bytes, "sha256").hex()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_signature_mismatch",
            "Signed delivery reference token could not be verified by this server process.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        )
    try:
        body = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_malformed",
            "Signed delivery reference token body is malformed.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        ) from exc
    if not isinstance(body, dict):
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_malformed",
            "Signed delivery reference token body must be a JSON object.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        )
    return body


def _delivery_response_from_signed_reference(
    *,
    request_id: str,
    payload: dict[str, Any],
    delivery: ExternalExportDownloadDelivery,
    token_body: dict[str, Any],
    token: str,
    now_epoch: int,
    durable_state: SignedReferenceDurableState,
) -> dict[str, Any]:
    authority_basis = token_body["delivery_authority"]
    expires_at_epoch = int(token_body["expires_at_epoch"])
    return {
        **_base_response(
            EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_SCHEMA_ID,
            request_id=request_id,
            status="prepared",
        ),
        "session_id": payload["session_id"],
        "analysis_plan_id": payload["analysis_plan_id"],
        "pass_run_id": payload["pass_run_id"],
        "preview_identity": _preview_identity(preview_id=payload["preview_id"], preview_hash=payload["preview_hash"]),
        "reconciliation_record_id": payload["reconciliation_record_id"],
        "external_export_download_record_ref": payload["external_export_download_record_ref"],
        "export_download_descriptor_ref": payload["export_download_descriptor_ref"],
        "signed_reference_state": EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_READY_STATE,
        "signed_reference_token": token,
        **durable_state.response_fields(),
        "signed_reference_expires_at": _epoch_iso(expires_at_epoch),
        "signed_reference_expires_in_seconds": max(0, expires_at_epoch - now_epoch),
        "signed_reference_use_endpoint": f"{API_ROOT}/handoff/export/download/signed-reference/use",
        "delivery_mode": "same_origin_signed_delivery_reference",
        "server_authority": "associated_cohort_external_export_download_signed_reference_gate",
        "source_artifact_ref": authority_basis["source_artifact_ref"],
        "source_artifact_hash": authority_basis["source_artifact_hash"],
        "source_artifact_size_bytes": authority_basis["source_artifact_size_bytes"],
        "pass_type": authority_basis["pass_type"],
        "pass_scope": authority_basis["pass_scope"],
        "method": authority_basis["method"],
        "source_gate": authority_basis["source_gate"],
        "source_shape": authority_basis["source_shape"],
        "source_dataset_version_ids": authority_basis["source_dataset_version_ids"],
        "public_url_enabled": False,
        "external_object_store_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "schema_runtime_source_widening_enabled": False,
        "authority_rail": {
            "token_authority": "server_hmac_with_durable_state",
            "artifact_authority": "existing_external_export_download_delivery_validator",
            "expires_within_seconds": EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_TTL_SECONDS,
            "revalidated_at_generation": True,
            "revalidate_at_use_required": True,
            "durable_state_required": True,
            "replay_policy": durable_state.signed_reference_replay_policy,
            "configured_secret_present": True,
            "process_restart_invalidates_existing_tokens": False,
        },
        "next_state": EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_DELIVERED_STATE,
    }


def external_export_download_generate_signed_reference(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for signed external export/download delivery reference generation.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_external_export_download_signed_reference_request"],
        )
    _signed_reference_signing_key()
    delivery = external_export_download_deliver(db, payload)
    blocked = _signed_reference_required_cohort_authority(delivery.authority)
    if blocked:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_scope_not_admitted",
            "Signed delivery references are limited to the associated-cohort descriptive-summary download authority rail.",
            status="blocked",
            http_status=409,
            blocked_fields=blocked,
            next_allowed_actions=["use_same_origin_external_export_download_delivery"],
        )
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    token_body = _signed_reference_token_body(payload=payload, delivery=delivery, now_epoch=effective_now)
    token = _encode_signed_reference_token(token_body)
    try:
        durable_state = record_generated_signed_reference(
            db,
            raw_token=token,
            token_body=token_body,
            request_id=request_id,
            payload=payload,
            authority_basis=token_body["delivery_authority"],
        )
    except SignedReferenceStateError as exc:
        raise _signed_reference_state_workbench_error(exc) from exc
    return _delivery_response_from_signed_reference(
        request_id=request_id,
        payload=payload,
        delivery=delivery,
        token_body=token_body,
        token=token,
        now_epoch=effective_now,
        durable_state=durable_state,
    )


def external_export_download_use_signed_reference(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> ExternalExportDownloadDelivery:
    token = str(payload.get("signed_reference_token") or "").strip()
    if not token:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_token_required",
            "signed_reference_token is required for signed external export/download delivery reference use.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
            next_allowed_actions=["submit_signed_reference_token"],
        )
    extra_fields = sorted(key for key in payload if key != "signed_reference_token")
    if extra_fields:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_use_scope_not_admitted",
            "Signed delivery reference use accepts only the server-generated signed_reference_token.",
            status="invalid",
            blocked_fields=extra_fields,
            next_allowed_actions=["submit_signed_reference_token_only"],
        )
    _signed_reference_signing_key()
    token_body = _decode_signed_reference_token(token)
    if token_body.get("schema_id") != EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_SCHEMA_ID:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_schema_mismatch",
            "Signed delivery reference token schema is not admitted for this route.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        )
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    try:
        expires_at_epoch = int(token_body.get("expires_at_epoch"))
    except (TypeError, ValueError) as exc:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_malformed",
            "Signed delivery reference token expiration is malformed.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        ) from exc
    if effective_now >= expires_at_epoch:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_expired",
            "Signed delivery reference token has expired.",
            status="blocked",
            http_status=409,
            blocked_fields=["signed_reference_token"],
            next_allowed_actions=["regenerate_external_export_download_signed_reference"],
        )
    delivery_payload = token_body.get("delivery_payload")
    if not isinstance(delivery_payload, dict):
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_payload_missing",
            "Signed delivery reference token is missing its delivery authority payload.",
            status="invalid",
            blocked_fields=["signed_reference_token"],
        )
    delivery = external_export_download_deliver(db, delivery_payload)
    blocked = _signed_reference_required_cohort_authority(delivery.authority)
    if blocked:
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_scope_not_admitted",
            "Signed delivery references are limited to the associated-cohort descriptive-summary download authority rail.",
            status="blocked",
            http_status=409,
            blocked_fields=blocked,
            next_allowed_actions=["use_same_origin_external_export_download_delivery"],
        )
    current_basis = _signed_reference_authority_basis(payload=delivery_payload, delivery=delivery)
    if current_basis != token_body.get("delivery_authority"):
        raise Layer3WorkbenchError(
            "external_export_download_signed_reference_authority_mismatch",
            "Current delivery authority no longer matches the signed delivery reference token.",
            status="conflict",
            http_status=409,
            blocked_fields=["signed_reference_token"],
            next_allowed_actions=["regenerate_external_export_download_signed_reference"],
        )
    try:
        durable_state = record_used_signed_reference(
            db,
            raw_token=token,
            token_body=token_body,
            request_id=str(delivery_payload.get("client_request_id") or "").strip() or None,
            authority_basis=current_basis,
            now_epoch=effective_now,
        )
    except SignedReferenceStateError as exc:
        raise _signed_reference_state_workbench_error(exc) from exc
    return ExternalExportDownloadDelivery(
        artifact_path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        headers={
            **delivery.headers,
            "X-Layer3-Schema-Id": EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_SCHEMA_ID,
            "X-Layer3-Signed-Reference-State": EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_DELIVERED_STATE,
            "X-Layer3-Signed-Reference-Expires-At": _epoch_iso(expires_at_epoch),
            "X-Layer3-Signed-Reference-Token-Id": durable_state.signed_reference_token_id,
            "X-Layer3-Signed-Reference-Receipt-Id": durable_state.signed_reference_receipt_id,
            "X-Layer3-Signed-Reference-Replay-Policy": durable_state.signed_reference_replay_policy,
            "X-Layer3-Signed-Reference-Use-Count": str(durable_state.signed_reference_use_count),
        },
        authority=delivery.authority,
    )


def _package_review_submit_summary(
    db: Session,
    *,
    session_id: str,
    package_construction_state: dict[str, Any],
) -> dict[str, Any]:
    reconciliation_record_id = str(package_construction_state.get("reconciliation_record_id") or "").strip()
    if package_construction_state.get("state") != PACKAGE_CONSTRUCTED_STATE or not reconciliation_record_id:
        return {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "available": False,
            "state": PACKAGE_REVIEW_SUBMIT_UNAVAILABLE_STATE,
            "blocked_reason": "package_not_constructed",
            "reconciliation_record_id": None,
            "output_package_ids": [],
            "package_kinds": [],
            "payload_hashes": [],
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE),
        }

    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.session_id == session_id,
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .filter(L3OutputPackage.package_kind.in_(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS))
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    complete_package_set = bool(
        reconciliation is not None
        and len(packages) == len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        and {package.package_kind for package in packages} == set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    )
    if not complete_package_set:
        return {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "available": False,
            "state": PACKAGE_REVIEW_SUBMIT_BLOCKED_STATE,
            "blocked_reason": "partial_package_state",
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": [package.output_package_id for package in packages],
            "package_kinds": [package.package_kind for package in packages],
            "payload_refs": [package.payload_ref for package in packages],
            "payload_hashes": [package.payload_hash for package in packages],
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE),
        }

    ordered_packages = _packages_in_review_order(packages)
    reconciliation_summary = reconciliation.summary_json if reconciliation is not None else {}
    if not isinstance(reconciliation_summary, dict):
        reconciliation_summary = {}
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        commit_summary = {}
    cohort_package_construction = _is_cohort_package_construction_source(reconciliation_summary.get("source_gate"))
    qualitative_package_construction = _is_qualitative_aps_package_construction_source(
        reconciliation_summary.get("source_gate")
    )
    recorded_submit = _package_review_submit_from_reconciliation(reconciliation)
    if (
        recorded_submit is None
        and commit_summary.get("package_review_submit_enabled", True) is not True
        and not cohort_package_construction
        and not qualitative_package_construction
    ):
        downstream_unavailable = commit_summary.get("downstream_unavailable")
        if not isinstance(downstream_unavailable, list):
            downstream_unavailable = list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE)
        return {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "available": False,
            "state": PACKAGE_REVIEW_SUBMIT_UNAVAILABLE_STATE,
            "blocked_reason": "package_review_submit_deferred_for_associated_cohort",
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": [package.output_package_id for package in ordered_packages],
            "package_kinds": [package.package_kind for package in ordered_packages],
            "payload_refs": [package.payload_ref for package in ordered_packages],
            "payload_hashes": [package.payload_hash for package in ordered_packages],
            "package_review_preview_hash": commit_summary.get("package_review_preview_hash"),
            "construction_basis_hash": commit_summary.get("construction_basis_hash")
            or commit_summary.get("authority_basis_hash"),
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(downstream_unavailable),
        }
    if recorded_submit is not None:
        recorded_cohort_submit = _is_cohort_package_construction_source(
            recorded_submit.get("package_construction_source_gate")
            or reconciliation_summary.get("source_gate")
        )
        recorded_qualitative_submit = _is_qualitative_aps_package_construction_source(
            recorded_submit.get("package_construction_source_gate")
            or reconciliation_summary.get("source_gate")
        )
        downstream_unavailable = _package_review_submit_downstream_unavailable(
            str(recorded_submit.get("package_review_state") or ""),
            associated_cohort_submit=recorded_cohort_submit,
            qualitative_aps_submit=recorded_qualitative_submit,
        )
        recorded_submit_schema_id = (
            QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
            if recorded_qualitative_submit
            else COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
            if recorded_cohort_submit
            else PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        )
        return {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "package_review_submit_schema_id": recorded_submit.get("package_review_submit_schema_id")
            or recorded_submit_schema_id,
            "available": False,
            "state": recorded_submit.get("package_review_state"),
            "blocked_reason": None,
            "submit_record_ref": recorded_submit.get("submit_record_ref"),
            "operator_decision": recorded_submit.get("operator_decision"),
            "decision_notes": recorded_submit.get("decision_notes"),
            "analysis_run_id": recorded_submit.get("analysis_run_id"),
            "result_review_record_ref": recorded_submit.get("result_review_record_ref"),
            "package_review_preview_hash": recorded_submit.get("package_review_preview_hash"),
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": [package.output_package_id for package in ordered_packages],
            "package_kinds": [package.package_kind for package in ordered_packages],
            "payload_refs": recorded_submit.get("payload_refs")
            or [package.payload_ref for package in ordered_packages],
            "payload_hashes": [package.payload_hash for package in ordered_packages],
            "construction_basis_hash": recorded_submit.get("construction_basis_hash"),
            "pass_type": recorded_submit.get("pass_type"),
            "pass_scope": recorded_submit.get("pass_scope"),
            "method": recorded_submit.get("method"),
            "source_gate": recorded_submit.get("source_gate"),
            "package_construction_source_gate": (
                recorded_submit.get("package_construction_source_gate")
                or reconciliation_summary.get("source_gate")
            ),
            "source_shape": recorded_submit.get("source_shape"),
            "source_dataset_version_ids": _json_clone(recorded_submit.get("source_dataset_version_ids") or []),
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(downstream_unavailable),
        }
    ready_downstream_unavailable = (
        COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
        if cohort_package_construction
        else QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
        if qualitative_package_construction
        else PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    )
    return {
        "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
        "package_review_submit_schema_id": (
            QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
            if qualitative_package_construction
            else COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
            if cohort_package_construction
            else PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        ),
        "available": True,
        "state": PACKAGE_REVIEW_SUBMIT_READY_STATE,
        "blocked_reason": None,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": [package.output_package_id for package in ordered_packages],
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": [package.payload_ref for package in ordered_packages],
        "payload_hashes": [package.payload_hash for package in ordered_packages],
        "package_review_preview_hash": commit_summary.get("package_review_preview_hash"),
        "construction_basis_hash": commit_summary.get("construction_basis_hash")
        or commit_summary.get("authority_basis_hash"),
        "package_construction_source_gate": reconciliation_summary.get("source_gate"),
        "package_review_submit_enabled": True,
        "handoff_enabled": False,
        "export_enabled": False,
        "downstream_unavailable": list(ready_downstream_unavailable),
    }


def _handoff_export_prepare_summary(
    db: Session,
    *,
    session_id: str,
    package_review_submit_state: dict[str, Any],
) -> dict[str, Any]:
    reconciliation_record_id = str(package_review_submit_state.get("reconciliation_record_id") or "").strip()
    submit_record_ref = str(package_review_submit_state.get("submit_record_ref") or "").strip()
    if package_review_submit_state.get("state") != PACKAGE_REVIEW_APPROVED_STATE or not reconciliation_record_id or not submit_record_ref:
        return {
            "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": HANDOFF_EXPORT_UNAVAILABLE_STATE,
            "blocked_reason": "approved_package_review_submit_required",
            "reconciliation_record_id": reconciliation_record_id or None,
            "output_package_ids": [],
            "package_kinds": [],
            "payload_refs": [],
            "payload_hashes": [],
            "package_review_submit_record_ref": submit_record_ref or None,
            "handoff_export_prepare_enabled": False,
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        }

    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.session_id == session_id,
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .filter(L3OutputPackage.package_kind.in_(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS))
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    complete_package_set = bool(
        reconciliation is not None
        and len(packages) == len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        and {package.package_kind for package in packages} == set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    )
    if not complete_package_set:
        return {
            "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": HANDOFF_EXPORT_BLOCKED_STATE,
            "blocked_reason": "partial_package_state",
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": [package.output_package_id for package in packages],
            "package_kinds": [package.package_kind for package in packages],
            "payload_refs": [package.payload_ref for package in packages],
            "payload_hashes": [package.payload_hash for package in packages],
            "package_review_submit_record_ref": submit_record_ref,
            "handoff_export_prepare_enabled": False,
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        }

    ordered_packages = _packages_in_review_order(packages)
    reconciliation_summary = reconciliation.summary_json if reconciliation is not None else {}
    if not isinstance(reconciliation_summary, dict):
        reconciliation_summary = {}
    package_construction_source_gate = (
        package_review_submit_state.get("package_construction_source_gate")
        or reconciliation_summary.get("source_gate")
    )
    prepare_submit_schema_id = (
        QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        if _is_qualitative_aps_package_construction_source(package_construction_source_gate)
        else COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
        if _is_cohort_package_construction_source(package_construction_source_gate)
        else package_review_submit_state.get("package_review_submit_schema_id")
        or PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    )
    recorded_prepare = _handoff_export_prepare_from_reconciliation(reconciliation)
    if recorded_prepare is not None:
        recorded_envelope = recorded_prepare.get("handoff_export_envelope")
        recorded_envelope_ref = (
            str(recorded_envelope.get("envelope_ref") or "").strip()
            if isinstance(recorded_envelope, dict)
            else None
        )
        return {
            "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": recorded_prepare.get("handoff_export_state"),
            "blocked_reason": None,
            "prepare_record_ref": recorded_prepare.get("prepare_record_ref"),
            "handoff_export_envelope_ref": recorded_envelope_ref,
            "operator_decision": recorded_prepare.get("operator_decision"),
            "decision_notes": recorded_prepare.get("decision_notes"),
            "analysis_run_id": recorded_prepare.get("analysis_run_id") or package_review_submit_state.get("analysis_run_id"),
            "result_review_record_ref": (
                recorded_prepare.get("result_review_record_ref")
                or package_review_submit_state.get("result_review_record_ref")
            ),
            "package_review_preview_hash": (
                recorded_prepare.get("package_review_preview_hash")
                or package_review_submit_state.get("package_review_preview_hash")
            ),
            "construction_basis_hash": recorded_prepare.get("construction_basis_hash"),
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": [package.output_package_id for package in ordered_packages],
            "package_kinds": [package.package_kind for package in ordered_packages],
            "payload_refs": [package.payload_ref for package in ordered_packages],
            "payload_hashes": [package.payload_hash for package in ordered_packages],
            "package_review_submit_record_ref": submit_record_ref,
            "package_review_state": package_review_submit_state.get("state"),
            "pass_type": recorded_prepare.get("pass_type") or package_review_submit_state.get("pass_type"),
            "pass_scope": recorded_prepare.get("pass_scope") or package_review_submit_state.get("pass_scope"),
            "method": recorded_prepare.get("method") or package_review_submit_state.get("method"),
            "source_gate": recorded_prepare.get("source_gate") or package_review_submit_state.get("source_gate"),
            "package_construction_source_gate": (
                recorded_prepare.get("package_construction_source_gate") or package_construction_source_gate
            ),
            "source_shape": recorded_prepare.get("source_shape") or package_review_submit_state.get("source_shape"),
            "source_dataset_version_ids": _json_clone(
                recorded_prepare.get("source_dataset_version_ids")
                or package_review_submit_state.get("source_dataset_version_ids")
                or []
            ),
            "package_review_submit_schema_id": recorded_prepare.get("package_review_submit_schema_id")
            or prepare_submit_schema_id,
            "handoff_export_prepare_enabled": False,
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
            "aps_handoff_enabled": bool(recorded_prepare.get("aps_handoff_enabled")),
            "external_export_download_enabled": bool(recorded_prepare.get("external_export_download_enabled")),
            "connector_dispatch_enabled": bool(recorded_prepare.get("connector_dispatch_enabled")),
            "provider_public_url_enabled": bool(recorded_prepare.get("provider_public_url_enabled")),
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        }
    return {
        "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
        "available": True,
        "state": HANDOFF_EXPORT_READY_STATE,
        "blocked_reason": None,
        "analysis_run_id": package_review_submit_state.get("analysis_run_id"),
        "result_review_record_ref": package_review_submit_state.get("result_review_record_ref"),
        "package_review_preview_hash": package_review_submit_state.get("package_review_preview_hash"),
        "construction_basis_hash": package_review_submit_state.get("construction_basis_hash"),
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": [package.output_package_id for package in ordered_packages],
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": [package.payload_ref for package in ordered_packages],
        "payload_hashes": [package.payload_hash for package in ordered_packages],
        "package_review_submit_record_ref": submit_record_ref,
        "package_review_state": package_review_submit_state.get("state"),
        "pass_type": package_review_submit_state.get("pass_type"),
        "pass_scope": package_review_submit_state.get("pass_scope"),
        "method": package_review_submit_state.get("method"),
        "source_gate": package_review_submit_state.get("source_gate"),
        "package_construction_source_gate": package_construction_source_gate,
        "source_shape": package_review_submit_state.get("source_shape"),
        "source_dataset_version_ids": _json_clone(package_review_submit_state.get("source_dataset_version_ids") or []),
        "package_review_submit_schema_id": prepare_submit_schema_id,
        "handoff_export_prepare_enabled": True,
        "external_handoff_enabled": False,
        "external_export_enabled": False,
        "dispatch_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }


def _aps_handoff_dispatch_summary(
    db: Session,
    *,
    session_id: str,
    handoff_export_prepare_state: dict[str, Any],
) -> dict[str, Any]:
    reconciliation_record_id = str(handoff_export_prepare_state.get("reconciliation_record_id") or "").strip()
    prepare_record_ref = str(handoff_export_prepare_state.get("prepare_record_ref") or "").strip()
    envelope_ref = str(handoff_export_prepare_state.get("handoff_export_envelope_ref") or "").strip()
    if reconciliation_record_id:
        early_reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(
                L3ReconciliationRecord.session_id == session_id,
                L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            )
            .one_or_none()
        )
        early_recorded_dispatch = _aps_handoff_dispatch_from_reconciliation(early_reconciliation)
        if early_recorded_dispatch is not None:
            return {
                "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
                "available": False,
                "state": early_recorded_dispatch.get("aps_handoff_state"),
                "blocked_reason": None,
                "reconciliation_record_id": early_recorded_dispatch.get("reconciliation_record_id"),
                "aps_handoff_record_ref": early_recorded_dispatch.get("aps_handoff_record_ref"),
                "prepare_record_ref": early_recorded_dispatch.get("prepare_record_ref"),
                "handoff_export_envelope_ref": early_recorded_dispatch.get("handoff_export_envelope_ref"),
                "aps_handoff_target": early_recorded_dispatch.get("aps_handoff_target"),
                "dispatch_mode": early_recorded_dispatch.get("dispatch_mode"),
                "operator_decision": early_recorded_dispatch.get("operator_decision"),
                "decision_notes": early_recorded_dispatch.get("decision_notes"),
                "aps_output_package_id": early_recorded_dispatch.get("aps_output_package_id"),
                "aps_output_package_kind": early_recorded_dispatch.get("aps_output_package_kind"),
                "aps_bundle_ref": early_recorded_dispatch.get("aps_bundle_ref"),
                "aps_bundle_id": early_recorded_dispatch.get("aps_bundle_id"),
                "aps_schema_id": early_recorded_dispatch.get("aps_schema_id"),
                "external_export_enabled": False,
                "download_enabled": False,
                "connector_dispatch_enabled": False,
                "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
            }
    if handoff_export_prepare_state.get("state") != HANDOFF_EXPORT_PREPARED_STATE or not reconciliation_record_id or not prepare_record_ref or not envelope_ref:
        return {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "available": False,
            "state": APS_HANDOFF_UNAVAILABLE_STATE,
            "blocked_reason": "handoff_export_prepared_required",
            "reconciliation_record_id": reconciliation_record_id or None,
            "prepare_record_ref": prepare_record_ref or None,
            "handoff_export_envelope_ref": envelope_ref or None,
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": None,
            "aps_output_package_kind": None,
            "aps_bundle_ref": None,
            "aps_bundle_id": None,
            "aps_schema_id": None,
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
        }
    cohort_prepare_source = (
        handoff_export_prepare_state.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT
        or _is_cohort_package_construction_source(
            handoff_export_prepare_state.get("package_construction_source_gate")
        )
    )
    qualitative_prepare_source = (
        handoff_export_prepare_state.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        or _is_qualitative_aps_package_construction_source(
            handoff_export_prepare_state.get("package_construction_source_gate")
        )
    )
    if qualitative_prepare_source and not _qualitative_aps_aps_dispatch_prepare_state_admitted(
        handoff_export_prepare_state
    ):
        return {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "available": False,
            "state": APS_HANDOFF_UNAVAILABLE_STATE,
            "blocked_reason": "qualitative_aps_aps_handoff_dispatch_not_admitted",
            "reconciliation_record_id": reconciliation_record_id,
            "prepare_record_ref": prepare_record_ref,
            "handoff_export_envelope_ref": envelope_ref,
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": None,
            "aps_output_package_kind": None,
            "aps_bundle_ref": None,
            "aps_bundle_id": None,
            "aps_schema_id": None,
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        }
    if cohort_prepare_source and not _associated_cohort_aps_dispatch_prepare_state_admitted(
        handoff_export_prepare_state
    ):
        return {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "available": False,
            "state": APS_HANDOFF_UNAVAILABLE_STATE,
            "blocked_reason": "associated_cohort_aps_handoff_dispatch_not_admitted",
            "reconciliation_record_id": reconciliation_record_id,
            "prepare_record_ref": prepare_record_ref,
            "handoff_export_envelope_ref": envelope_ref,
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": None,
            "aps_output_package_kind": None,
            "aps_bundle_ref": None,
            "aps_bundle_id": None,
            "aps_schema_id": None,
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        }

    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.session_id == session_id,
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    recorded_dispatch = _aps_handoff_dispatch_from_reconciliation(reconciliation)
    if recorded_dispatch is not None:
        return {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "available": False,
            "state": recorded_dispatch.get("aps_handoff_state"),
            "blocked_reason": None,
            "reconciliation_record_id": reconciliation_record_id,
            "aps_handoff_record_ref": recorded_dispatch.get("aps_handoff_record_ref"),
            "prepare_record_ref": recorded_dispatch.get("prepare_record_ref"),
            "handoff_export_envelope_ref": recorded_dispatch.get("handoff_export_envelope_ref"),
            "aps_handoff_target": recorded_dispatch.get("aps_handoff_target"),
            "dispatch_mode": recorded_dispatch.get("dispatch_mode"),
            "operator_decision": recorded_dispatch.get("operator_decision"),
            "decision_notes": recorded_dispatch.get("decision_notes"),
            "aps_output_package_id": recorded_dispatch.get("aps_output_package_id"),
            "aps_output_package_kind": recorded_dispatch.get("aps_output_package_kind"),
            "aps_bundle_ref": recorded_dispatch.get("aps_bundle_ref"),
            "aps_bundle_id": recorded_dispatch.get("aps_bundle_id"),
            "aps_schema_id": recorded_dispatch.get("aps_schema_id"),
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
        }

    existing_aps_package = _aps_handoff_package_for_session(db, session_id=session_id)
    if existing_aps_package is not None:
        return {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "available": False,
            "state": APS_HANDOFF_CONFLICT_STATE,
            "blocked_reason": "aps_handoff_package_exists_without_workbench_dispatch_state",
            "reconciliation_record_id": reconciliation_record_id,
            "prepare_record_ref": prepare_record_ref,
            "handoff_export_envelope_ref": envelope_ref,
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": existing_aps_package.output_package_id,
            "aps_output_package_kind": existing_aps_package.package_kind,
            "aps_bundle_ref": existing_aps_package.payload_ref,
            "aps_bundle_id": (existing_aps_package.summary_json or {}).get("bundle_id"),
            "aps_schema_id": (existing_aps_package.summary_json or {}).get("aps_schema_id"),
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
        }

    compatibility = check_aps_handoff_compatibility(db, session_id=session_id)
    if not compatibility.compatible:
        return {
            "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
            "available": False,
            "state": APS_HANDOFF_BLOCKED_STATE,
            "blocked_reason": compatibility.blocked_reason or "aps_handoff_owner_service_not_compatible",
            "reconciliation_record_id": reconciliation_record_id,
            "prepare_record_ref": prepare_record_ref,
            "handoff_export_envelope_ref": envelope_ref,
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": None,
            "aps_output_package_kind": None,
            "aps_bundle_ref": None,
            "aps_bundle_id": None,
            "aps_schema_id": None,
            "external_export_enabled": False,
            "download_enabled": False,
            "connector_dispatch_enabled": False,
            "downstream_unavailable": list(APS_HANDOFF_BLOCKED_DOWNSTREAM_UNAVAILABLE),
        }

    return {
        "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
        "available": True,
        "state": APS_HANDOFF_READY_STATE,
        "blocked_reason": None,
        "reconciliation_record_id": reconciliation_record_id,
        "prepare_record_ref": prepare_record_ref,
        "handoff_export_envelope_ref": envelope_ref,
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "aps_output_package_id": None,
        "aps_output_package_kind": None,
        "aps_bundle_ref": None,
        "aps_bundle_id": None,
        "aps_schema_id": None,
        "external_export_enabled": False,
        "download_enabled": False,
        "connector_dispatch_enabled": False,
        "downstream_unavailable": list(APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE),
    }


def session_summary(db: Session, session_id: str) -> dict[str, Any]:
    session = _load_session(db, session_id)
    manifest = _latest_selection_manifest_for_session(db, session=session)

    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_unit_count = db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).count()
    analysis_group_count = db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    gate_b_counts = gate_b_summary_from_session(session)
    typing_committed = typing_record_count > 0
    plan_preview_readiness = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
    plan_approval_readiness = _plan_approval_summary(db, session_id=session_id)
    plan_revision_readiness = _plan_revision_summary(db, session_id=session_id)
    active_revision_control = _plan_revision_control_from_session(session)
    recorded_revision_recovery = _plan_revision_recovery_from_session(session)
    recorded_approved_plan_cancel = _approved_plan_cancel_from_session(session)
    if recorded_revision_recovery is not None:
        plan_revision_recovery_state = {
            "schema_id": "layer3.plan_revision_recovery_readiness.v1",
            "available": False,
            "state": recorded_revision_recovery.get("state"),
            "blocked_reason": "plan_preview_refresh_required",
            "source_revision_state": recorded_revision_recovery.get("source_revision_state"),
            "source_preview_id": recorded_revision_recovery.get("source_preview_id"),
            "source_preview_hash": recorded_revision_recovery.get("source_preview_hash"),
            "preview_refresh_required": True,
            "approval_available": False,
            "execution_started": False,
            "recovery_id": recorded_revision_recovery.get("recovery_id"),
        }
    elif active_revision_control is not None:
        plan_revision_recovery_state = {
            "schema_id": "layer3.plan_revision_recovery_readiness.v1",
            "available": True,
            "state": active_revision_control.get("state"),
            "blocked_reason": None,
            "source_revision_state": active_revision_control.get("state"),
            "source_preview_id": active_revision_control.get("source_preview_id"),
            "source_preview_hash": active_revision_control.get("source_preview_hash"),
            "preview_refresh_required": False,
            "approval_available": False,
            "execution_started": False,
        }
    else:
        plan_revision_recovery_state = {
            "schema_id": "layer3.plan_revision_recovery_readiness.v1",
            "available": False,
            "state": None,
            "blocked_reason": "plan_revision_recovery_not_available",
            "source_revision_state": None,
            "source_preview_id": None,
            "source_preview_hash": None,
            "preview_refresh_required": False,
            "approval_available": False,
            "execution_started": False,
        }
    if recorded_approved_plan_cancel is not None:
        approved_plan_cancel_state = {
            "schema_id": "layer3.approved_plan_cancel_readiness.v1",
            "available": False,
            "cancelled": True,
            "state": recorded_approved_plan_cancel.get("state"),
            "blocked_reason": "approved_plan_cancelled",
            "analysis_plan_id": recorded_approved_plan_cancel.get("analysis_plan_id"),
            "source_preview_id": recorded_approved_plan_cancel.get("source_preview_id"),
            "source_preview_hash": recorded_approved_plan_cancel.get("source_preview_hash"),
            "cancellation_id": recorded_approved_plan_cancel.get("cancellation_id"),
            "approval_available": False,
            "execution_started": False,
            "replacement_plan_created": False,
            "downstream_unavailable": list(APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE),
        }
    else:
        cancel_available = bool(
            plan_approval_readiness.get("approved")
            and plan_approval_readiness.get("plan_status") == PLAN_STATUS_APPROVED
            and plan_approval_readiness.get("pass_run_count") == 0
        )
        cancel_plan = _latest_analysis_plan(db, session_id=session_id) if cancel_available else None
        cancel_plan_json = cancel_plan.plan_json if cancel_plan is not None else {}
        approved_plan_cancel_state = {
            "schema_id": "layer3.approved_plan_cancel_readiness.v1",
            "available": cancel_available,
            "cancelled": False,
            "state": "plan_approved" if cancel_available else None,
            "blocked_reason": None if cancel_available else "approved_plan_cancel_not_available",
            "analysis_plan_id": plan_approval_readiness.get("analysis_plan_id") if cancel_available else None,
            "source_preview_id": cancel_plan_json.get("source_preview_id"),
            "source_preview_hash": cancel_plan_json.get("source_preview_hash"),
            "cancellation_id": None,
            "approval_available": False,
            "execution_started": False,
            "replacement_plan_created": False,
            "downstream_unavailable": list(APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE),
        }
    execution_selection_readiness = _execution_selection_summary(db, session_id=session_id)
    analysis_execution_start_state = (session.summary_json or {}).get("analysis_execution_start")
    execution_result_review_state = (session.summary_json or {}).get("execution_result_review")
    if not isinstance(analysis_execution_start_state, dict):
        analysis_execution_start_state = {
            "schema_id": ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
            "available": bool(
                execution_selection_readiness["selected"]
                and not execution_selection_readiness["execution_started"]
            ),
            "state": None,
            "downstream_unavailable": list(ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE),
        }
    if not isinstance(execution_result_review_state, dict):
        execution_result_review_state = {
            "schema_id": EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
            "available": bool(analysis_execution_start_state.get("state") == EXECUTION_PASS_COMPLETED_STATE),
            "state": None,
            "package_review_enabled": False,
            "handoff_enabled": False,
            "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
        }
    package_review_preview_state = package_review_preview_summary(
        execution_result_review_state,
        approved_review_state=EXECUTION_RESULT_REVIEW_APPROVED_STATE,
    )
    package_construction_state = _package_construction_summary(
        db,
        session_id=session_id,
        package_review_preview_state=package_review_preview_state,
    )
    package_review_submit_state = _package_review_submit_summary(
        db,
        session_id=session_id,
        package_construction_state=package_construction_state,
    )
    handoff_export_prepare_state = _handoff_export_prepare_summary(
        db,
        session_id=session_id,
        package_review_submit_state=package_review_submit_state,
    )
    aps_handoff_dispatch_state = _aps_handoff_dispatch_summary(
        db,
        session_id=session_id,
        handoff_export_prepare_state=handoff_export_prepare_state,
    )
    external_export_download_state = _external_export_download_prepare_summary(
        db,
        session_id=session_id,
        aps_handoff_dispatch_state=aps_handoff_dispatch_state,
    )
    selection_active = bool(execution_selection_readiness["selected"])
    package_active = bool(
        package_review_preview_state.get("available")
        or package_construction_state.get("state") == PACKAGE_CONSTRUCTED_STATE
    )
    current_gate = "package" if package_active else ("execution" if selection_active else ("plan" if typing_committed else "gate_c"))
    downstream_unavailable = (
        _active_package_downstream_unavailable(
            package_construction_state=package_construction_state,
            package_review_submit_state=package_review_submit_state,
            handoff_export_prepare_state=handoff_export_prepare_state,
            aps_handoff_dispatch_state=aps_handoff_dispatch_state,
            external_export_download_state=external_export_download_state,
        )
        if package_active
        else (
        EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE
        if selection_active
        else (
            APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE
            if recorded_approved_plan_cancel is not None
            else (PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE if typing_committed else DOWNSTREAM_UNAVAILABLE)
        )
        )
    )

    return {
        **_base_response("layer3.workbench_session_summary.v1"),
        "session_id": session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "current_gate": current_gate,
        "gate_b_summary": gate_b_counts,
        "gate_c_summary": {
            "typing_committed": typing_committed,
            "typing_record_count": typing_record_count,
            "analysis_unit_count": analysis_unit_count,
            "analysis_group_count": analysis_group_count,
            "analysis_set_count": analysis_set_count,
        },
        "plan_preview": plan_preview_readiness,
        "plan_approval": plan_approval_readiness,
        "plan_revision": plan_revision_readiness,
        "plan_revision_recovery": plan_revision_recovery_state,
        "approved_plan_cancel": approved_plan_cancel_state,
        "execution_selection": execution_selection_readiness,
        "analysis_execution_start": analysis_execution_start_state,
        "execution_result_review": execution_result_review_state,
        "package_review_preview": package_review_preview_state,
        "package_construction": package_construction_state,
        "package_review_submit": package_review_submit_state,
        "handoff_export_prepare": handoff_export_prepare_state,
        "aps_handoff_dispatch": aps_handoff_dispatch_state,
        "external_export_download": external_export_download_state,
        "pdf_location_projection": _pdf_location_projection_for_session(db, session_id=session_id),
        "sublayer_visualization": _session_sublayer_visualization_state(db, session_id=session_id),
        "state_action_contract": _workbench_state_action_contract(),
        "downstream_unavailable": list(downstream_unavailable),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate=current_gate,
            persistence_mode="durable_layer3_control",
            counts=gate_b_counts,
            typing_status="committed" if typing_committed else "previewed",
            downstream_unavailable=downstream_unavailable,
        ),
    }
