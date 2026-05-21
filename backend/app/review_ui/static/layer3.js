const API_ROOT = '/api/v1/layer3';
const THEME_STORAGE_KEY = 'nrc_aps_review_theme';
const LAYER3_THEME_STORAGE_KEY = 'layer3_workbench_theme';
const LAYER3_MOCKUP_WORKBENCH_THEME = 'layer3_mockup_workbench_theme';
const LAYER3_MOCKUP_THEME_FIRST_SLICE = 'mockup_theme_shell_and_fixture_projection';
const LAYER3_MOCKUP_THEME_FIXTURE = Object.freeze({
    scenario: 'semiconductor_infrastructure_auto_supply_chain',
    frames: Object.freeze([
        'userflow/layer3_user-flow-overview1.png',
        'userflow/layer3_user-flow-overview2.png',
        'clear-screenshots/userflow_slide1.png',
        'clear-screenshots/userflow_slide1_general-example.png',
        'clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png',
        'example-use-case-location-in-pdf.png',
        'focus_on_these/sublayer3A_and_sublayer3B.png',
        'focus_on_these/sublayer3C.png',
    ]),
});
const LAYER3_SESSION_RECOVERY_STORAGE_KEY = 'layer3_workbench_session_recovery_v1';
const LAYER3_GATE_B_DRAFT_STORAGE_KEY = 'layer3_workbench_gate_b_draft_v1';
const LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY = 'layer3_provider_private_receipt_v1';
const LAYER3_SESSION_RECOVERY_SCHEMA_ID = 'layer3.browser_session_recovery.v1';
const LAYER3_GATE_B_DRAFT_SCHEMA_ID = 'layer3.gate_b_draft_snapshot.v1';
const LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID = 'layer3.provider_private_receipt_recovery.v1';
const PROVIDER_PRIVATE_SIGNED_URL_REPLACEABLE_STATES = new Set([
    'provider_private_signed_url_expired',
    'provider_private_signed_url_revoked',
]);
const PROVIDER_PUBLIC_URL_REPLACEABLE_STATES = new Set([
    'provider_public_url_expired',
    'provider_public_url_revoked',
]);
const GATE_B_DRAFT_TTL_MS = 12 * 60 * 60 * 1000;
const QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE = '140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE';
const QUAL_APS_PASS_SCOPE = 'single_aps_doc_qualitative_pass';
const QUAL_APS_SOURCE_GATE = '119_L3_QUAL_APS_EXEC_ENTRY_FREEZE';
const QUAL_APS_SOURCE_SHAPE = 'aps_content_document';
const SOURCE_INTAKE_PASS_SCOPE = 'qualitative_single_item_operator_uploaded_source';
const SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = 'layer3.source_intake_external_export_download_prepare.v1';
const SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = 'layer3.source_intake_external_export_download_delivery.v1';
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = 'layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare.v1';
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID = 'layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status.v1';
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = 'layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery.v1';
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET = 'source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference';
const SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_RENDERED_MODE = 'rendered_source_directory_hybrid_middle_lifecycle_control';
const SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_USE_CASE = 'operator_prepares_source_directory_hybrid_context_packet_package_and_handoff_from_rendered_control';
const SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_RESPONSE_AUTHORITY = 'State.sourceDirectoryHybridMiddleLifecycle';
const SOURCE_DIRECTORY_HYBRID_VECTOR_RETRIEVAL_PATH = '/source/ingestion/server-configured-directory/vector-retrieval';
const SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet';
const SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis';
const SOURCE_DIRECTORY_HYBRID_ANALYSIS_STATUS_PATH = `${SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH}/status`;
const SOURCE_DIRECTORY_HYBRID_PACKAGE_COMMIT_PATH = `${SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH}/package/commit`;
const SOURCE_DIRECTORY_HYBRID_PACKAGE_REVIEW_SUBMIT_PATH = `${SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH}/package/review/submit`;
const SOURCE_DIRECTORY_HYBRID_HANDOFF_EXPORT_PREPARE_PATH = `${SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH}/handoff/export/prepare`;
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH = `${SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH}/handoff/export/download/prepare`;
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status';
const SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_RENDERED_MODE = 'rendered_source_directory_hybrid_internal_webhook_dispatch_control';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_USE_CASE = 'operator_dispatches_source_directory_hybrid_internal_webhook_from_server_configured_destination';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_RESPONSE_AUTHORITY = 'State.sourceDirectoryHybridInternalWebhookDispatch + State.sessionSummary.internal_webhook_dispatch';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_DISPATCH_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_STATUS_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/status';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID = 'layer3.source_directory_internal_webhook.dispatch.v1';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_STATUS_SCHEMA_ID = 'layer3.source_directory_internal_webhook.status.v1';
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_OPERATOR_DECISION = 'dispatch_source_directory_hybrid_internal_webhook';
const SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_REQUIRED_FIELDS = Object.freeze([
    'material_snapshot_id',
    'source_ingestion_batch_id',
    'source_ingestion_file_id',
    'content_sha256',
    'file_identity_hash',
    'authority_basis_hash',
    'payload_hash',
    'index_authority_hash',
    'embedding_index_authority_hash',
    'query_text',
    'top_k',
    'limit',
    'offset',
    'analysis_question',
    'analysis_focus',
]);
const SOURCE_DIRECTORY_HYBRID_DELIVERY_PAYLOAD_FIELDS = Object.freeze([
    'material_snapshot_id',
    'source_ingestion_batch_id',
    'source_ingestion_file_id',
    'content_sha256',
    'file_identity_hash',
    'authority_basis_hash',
    'payload_hash',
    'index_authority_hash',
    'embedding_index_authority_hash',
    'query_text',
    'top_k',
    'limit',
    'offset',
    'analysis_question',
    'analysis_focus',
    'qualitative_analysis_hash',
    'source_directory_hybrid_package_review_preview_hash',
    'construction_basis_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'package_kinds',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'handoff_target',
    'export_mode',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'external_export_download_record_ref',
    'export_download_descriptor_ref',
    'output_package_id',
    'package_kind',
    'package_payload_hash',
]);
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_EXCLUDED_DELIVERY_FIELDS = new Set([
    'output_package_id',
    'package_kind',
    'package_payload_hash',
]);
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_PAYLOAD_FIELDS = Object.freeze(
    SOURCE_DIRECTORY_HYBRID_DELIVERY_PAYLOAD_FIELDS.filter(
        (field) => !SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_EXCLUDED_DELIVERY_FIELDS.has(field),
    ),
);
const SOURCE_DIRECTORY_HYBRID_DELIVERY_REQUIRED_FIELDS = Object.freeze([
    'material_snapshot_id',
    'source_ingestion_batch_id',
    'source_ingestion_file_id',
    'content_sha256',
    'file_identity_hash',
    'authority_basis_hash',
    'payload_hash',
    'index_authority_hash',
    'embedding_index_authority_hash',
    'query_text',
    'analysis_question',
    'analysis_focus',
    'qualitative_analysis_hash',
    'source_directory_hybrid_package_review_preview_hash',
    'construction_basis_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'package_kinds',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'external_export_download_record_ref',
    'export_download_descriptor_ref',
    'output_package_id',
    'package_kind',
    'package_payload_hash',
]);
const SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_REQUIRED_FIELDS = Object.freeze(
    SOURCE_DIRECTORY_HYBRID_DELIVERY_REQUIRED_FIELDS.filter(
        (field) => !SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_EXCLUDED_DELIVERY_FIELDS.has(field),
    ),
);
const RAW_MIXED_MATERIALIZE_REQUEST_SCHEMA_ID = 'layer3.raw_mixed_corpus_materialize_request.v1';
const RAW_MIXED_MATERIALIZE_MODE = 'raw_mixed_existing_source_materialization_entry';
const RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES = new Set(['dataset_version', 'aps_content_document']);
const PACKAGE_LIFECYCLE_DASHBOARD_MODE = 'rendered_package_lifecycle_read_only_dashboard';
const PACKAGE_LIFECYCLE_USE_CASE = 'operator_inspects_package_lifecycle_without_mutation';
const PACKAGE_LIFECYCLE_RESPONSE_AUTHORITY = 'existing_server_response_authority';
const PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE = 'rendered_package_supersession_preview_control';
const PACKAGE_SUPERSESSION_PREVIEW_USE_CASE = 'operator_previews_package_supersession_without_package_row_or_payload_mutation';
const PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY = 'State.packageSupersessionPreview';
const PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = 'preview_package_supersession';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE = 'rendered_source_directory_package_supersession_preview_control';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_USE_CASE = 'operator_previews_source_directory_package_supersession_without_package_row_or_payload_mutation';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY = 'State.sourceDirectoryPackageSupersessionPreview';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = 'preview_source_directory_package_supersession';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID = 'layer3.source_directory_qualitative_analysis_package_supersession_preview.v1';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_MODE = 'source_directory_qualitative_analysis_package_supersession_preview_authority';
const SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE = 'rendered_source_directory_replacement_package_set_authority_control';
const SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE = 'operator_records_replacement_package_set_authority_from_source_directory_supersession_preview';
const SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_AUTHORITY = 'State.sourceDirectoryPackageSupersessionPreview';
const SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/replacement-set/record-from-supersession-preview';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE = 'rendered_source_directory_package_supersession_commit_control';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_USE_CASE = 'operator_commits_source_directory_package_supersession_lineage_after_replacement_package_set_authority';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_SOURCE_AUTHORITY = 'State.sourceDirectoryPackageSupersessionPreview + State.replacementPackageSetAuthority';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/commit';
const SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_RENDERED_MODE = 'rendered_source_directory_qualitative_handoff_export_prepare_control';
const SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_SOURCE_AUTHORITY = 'State.sourceDirectoryPackageSupersessionPreview + sourceDirectoryPackageSupersessionPreviewPayload';
const SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/prepare';
const SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_SCHEMA_ID = 'layer3.source_directory_qualitative_analysis_handoff_export_prepare.v1';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RENDERED_MODE = 'rendered_source_directory_qualitative_external_export_download_prepare_control';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_AUTHORITY = 'State.handoffExportPrepare + sourceDirectoryPackageSupersessionPreviewPayload';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/prepare';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = 'layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_TARGET = 'source_directory_qualitative_analysis_package_download_reference';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RENDERED_MODE = 'rendered_source_directory_qualitative_external_export_download_delivery_control';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver/status';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID = 'layer3.source_directory_qualitative_analysis_external_export_download_delivery_status.v1';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver';
const SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = 'layer3.source_directory_qualitative_analysis_external_export_download_delivery.v1';
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PAYLOAD_FIELDS = Object.freeze([
    'analysis_question',
    'analysis_focus',
    'material_snapshot_id',
    'source_ingestion_batch_id',
    'source_ingestion_file_id',
    'content_sha256',
    'file_identity_hash',
    'authority_basis_hash',
    'payload_hash',
    'index_authority_hash',
    'query_text',
    'limit',
    'offset',
    'qualitative_analysis_hash',
    'source_directory_package_review_preview_hash',
    'construction_basis_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'package_kinds',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
]);
const SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS = Object.freeze([
    'analysis_question',
    'analysis_focus',
    'material_snapshot_id',
    'source_ingestion_batch_id',
    'source_ingestion_file_id',
    'content_sha256',
    'file_identity_hash',
    'authority_basis_hash',
    'payload_hash',
    'index_authority_hash',
    'query_text',
    'qualitative_analysis_hash',
    'source_directory_package_review_preview_hash',
    'construction_basis_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'package_kinds',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
]);
const REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE = 'rendered_replacement_package_set_authority_control';
const REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE = 'operator_records_replacement_package_set_authority_from_server_owned_materialization';
const REPLACEMENT_PACKAGE_SET_AUTHORITY_RESPONSE_AUTHORITY = 'State.replacementPackageSetAuthority';
const REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION = 'materialize_replacement_package_artifacts_from_supersession_preview';
const REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION = 'record_replacement_package_set_authority';
const PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE = 'rendered_package_supersession_commit_control';
const PACKAGE_SUPERSESSION_COMMIT_USE_CASE = 'operator_commits_package_supersession_lineage_after_replacement_package_set_authority';
const PACKAGE_SUPERSESSION_COMMIT_RESPONSE_AUTHORITY = 'State.packageSupersessionCommit';
const PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION = 'commit_package_supersession';
const REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RENDERED_MODE = 'rendered_replacement_package_artifact_manifest_control';
const REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_USE_CASE = 'operator_records_replacement_package_artifact_manifest_from_server_computed_authority';
const REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RESPONSE_AUTHORITY = 'State.replacementPackageArtifactManifest';
const REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION = 'record_replacement_package_artifact_manifest_from_authority';
const REPLACEMENT_PACKAGE_NAMESPACE_RENDERED_MODE = 'rendered_replacement_package_namespace_control';
const REPLACEMENT_PACKAGE_NAMESPACE_USE_CASE = 'operator_records_replacement_package_namespace_row_from_manifest_authority';
const REPLACEMENT_PACKAGE_NAMESPACE_RESPONSE_AUTHORITY = 'State.replacementPackageNamespace';
const REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION = 'record_replacement_package_namespace';
const CONNECTOR_LOCAL_RECEIPT_STATUS_SURFACE_MODE = 'rendered_connector_local_destination_receipt_read_only_status_surface';
const CONNECTOR_LOCAL_RECEIPT_STATUS_USE_CASE = 'operator_reviews_connector_local_destination_receipt_status_without_real_connector_invocation_or_destination_write';
const CONNECTOR_LOCAL_RECEIPT_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.connector_local_destination_receipt';
const SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_SURFACE_MODE = 'rendered_server_owned_local_outbox_fake_target_read_only_status_surface';
const SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_USE_CASE = 'operator_reviews_server_owned_local_outbox_fake_target_status_without_real_destination_write';
const SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.server_owned_local_outbox_target';
const SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_SURFACE_MODE = 'rendered_server_owned_local_outbox_write_read_only_status_surface';
const SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_USE_CASE = 'operator_reviews_server_owned_local_outbox_write_status_without_real_connector_invocation_or_external_destination_write';
const SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.server_owned_local_outbox_write';
const LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_SURFACE_MODE = 'rendered_local_outbox_provider_private_handoff_read_only_status_surface';
const LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_USE_CASE = 'operator_reviews_local_outbox_provider_private_handoff_status_without_raw_token_use_or_external_write';
const LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.local_outbox_provider_private_handoff';
const EXTERNAL_LOCAL_EXPORT_STATUS_SURFACE_MODE = 'rendered_external_local_export_read_only_status_surface';
const EXTERNAL_LOCAL_EXPORT_STATUS_USE_CASE = 'operator_reviews_server_configured_external_local_export_status_without_path_editing_or_generic_dispatch';
const EXTERNAL_LOCAL_EXPORT_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.external_local_export';
const INTERNAL_WEBHOOK_DISPATCH_STATUS_SURFACE_MODE = 'rendered_internal_webhook_dispatch_read_only_status_surface';
const INTERNAL_WEBHOOK_DISPATCH_STATUS_USE_CASE = 'operator_reviews_internal_webhook_dispatch_status_without_dispatch_rerun_or_destination_selection';
const INTERNAL_WEBHOOK_DISPATCH_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.internal_webhook_dispatch';
const DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE = 'rendered_downstream_access_lifecycle_read_only_dashboard';
const DOWNSTREAM_ACCESS_LIFECYCLE_USE_CASE = 'operator_inspects_downstream_access_lifecycle_without_dispatch_or_raw_url_use';
const DOWNSTREAM_ACCESS_LIFECYCLE_RESPONSE_AUTHORITY = 'existing_server_response_authority';
const LAYER3_E2E_GOVERNANCE_LIFECYCLE_DASHBOARD_MODE = 'rendered_layer3_end_to_end_governance_lifecycle_read_only_dashboard';
const LAYER3_E2E_GOVERNANCE_LIFECYCLE_USE_CASE = 'operator_inspects_layer3_end_to_end_governance_lifecycle_without_mutation_or_dispatch';
const LAYER3_E2E_GOVERNANCE_LIFECYCLE_RESPONSE_AUTHORITY = 'existing_server_response_authority';
const AUTHORITY_MATRIX_REVIEW_RENDERED_MODE = 'rendered_authority_matrix_read_only_review_surface';
const AUTHORITY_MATRIX_REVIEW_USE_CASE = 'operator_reviews_exposed_layer3_authority_matrix_in_rendered_review_surface_without_mutation_or_dispatch';
const AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY = 'State.bootstrap.authority_matrix_contract';

const State = {
    bootstrap: null,
    datasetVersionCandidates: null,
    datasetVersionCandidateError: null,
    apsContentDocumentCandidates: null,
    apsContentDocumentCandidateError: null,
    rawMixedMaterialization: null,
    rawMixedMaterializationError: null,
    rawMixedMaterializationPending: false,
    preflight: null,
    sourcePreview: null,
    materialPreview: null,
    gateB: null,
    gateC: null,
    planPreview: null,
    planApproval: null,
    planRevision: null,
    planRevisionPending: false,
    sessionSummary: null,
    executionSelection: null,
    executionSelectionError: null,
    executionSelectionPending: false,
    executionStart: null,
    executionStartError: null,
    executionStartPending: false,
    resultStatus: null,
    resultStatusError: null,
    resultReview: null,
    resultReviewError: null,
    resultReviewPending: false,
    packageReviewPreview: null,
    packageReviewPreviewError: null,
    packageReviewPreviewPending: false,
    packageConstruction: null,
    packageConstructionError: null,
    packageConstructionPending: false,
    packageReviewSubmit: null,
    packageReviewSubmitError: null,
    packageReviewSubmitPending: false,
    packageSupersessionPreview: null,
    packageSupersessionPreviewError: null,
    packageSupersessionPreviewPending: false,
    sourceDirectoryPackageSupersessionPreview: null,
    sourceDirectoryPackageSupersessionPreviewError: null,
    sourceDirectoryPackageSupersessionPreviewPending: false,
    sourceDirectoryPackageSupersessionPreviewRequestToken: 0,
    replacementPackageArtifactMaterialization: null,
    replacementPackageArtifactMaterializationError: null,
    replacementPackageArtifactMaterializationPending: false,
    replacementPackageSetAuthority: null,
    replacementPackageSetAuthorityError: null,
    replacementPackageSetAuthorityPending: false,
    packageSupersessionCommit: null,
    packageSupersessionCommitError: null,
    packageSupersessionCommitPending: false,
    replacementPackageArtifactManifest: null,
    replacementPackageArtifactManifestError: null,
    replacementPackageArtifactManifestPending: false,
    replacementPackageNamespace: null,
    replacementPackageNamespaceHistory: [],
    replacementPackageNamespaceError: null,
    replacementPackageNamespacePending: false,
    handoffExportPrepare: null,
    handoffExportPrepareError: null,
    handoffExportPreparePending: false,
    apsHandoffDispatch: null,
    apsHandoffDispatchError: null,
    apsHandoffDispatchPending: false,
    externalExportDownloadPrepare: null,
    externalExportDownloadPrepareError: null,
    externalExportDownloadPreparePending: false,
    externalExportDownloadDelivery: null,
    externalExportDownloadDeliveryError: null,
    externalExportDownloadDeliveryPending: false,
    sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus: null,
    sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusError: null,
    sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusPending: false,
    sourceDirectoryHybridMiddleLifecycle: null,
    sourceDirectoryHybridMiddleLifecycleError: null,
    sourceDirectoryHybridMiddleLifecyclePending: false,
    sourceDirectoryHybridExternalExportDownloadDeliveryStatus: null,
    sourceDirectoryHybridExternalExportDownloadDeliveryStatusError: null,
    sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending: false,
    sourceDirectoryHybridExternalExportDownloadDelivery: null,
    sourceDirectoryHybridExternalExportDownloadDeliveryError: null,
    sourceDirectoryHybridExternalExportDownloadDeliveryPending: false,
    sourceDirectoryHybridInternalWebhookDispatch: null,
    sourceDirectoryHybridInternalWebhookDispatchError: null,
    sourceDirectoryHybridInternalWebhookDispatchPending: false,
    sourceDirectoryHybridInternalWebhookStatus: null,
    sourceDirectoryHybridInternalWebhookStatusError: null,
    sourceDirectoryHybridInternalWebhookStatusPending: false,
    externalExportDownloadSignedReference: null,
    externalExportDownloadSignedReferenceError: null,
    externalExportDownloadSignedReferencePending: false,
    externalExportDownloadSignedReferenceUse: null,
    externalExportDownloadSignedReferenceUsePending: false,
    providerPrivateSignedUrlPrepare: null,
    providerPrivateSignedUrlStatus: null,
    providerPrivateSignedUrlRevoke: null,
    providerPrivateSignedUrlReceiptRecovery: null,
    providerPrivateSignedUrlPrepareClientRequestId: null,
    providerPrivateSignedUrlError: null,
    providerPrivateSignedUrlPending: false,
    providerPublicUrlPrepare: null,
    providerPublicUrlStatus: null,
    providerPublicUrlUse: null,
    providerPublicUrlRevoke: null,
    providerPublicUrlPrepareClientRequestId: null,
    providerPublicUrlError: null,
    providerPublicUrlPending: false,
    gateBDecisions: {},
    gateBClientRequestId: null,
    materialFilter: '',
    events: [],
    themePreference: document.documentElement.dataset.themePreference || 'system',
    activeOperationId: 'intent-band',
    operationDockManual: false,
};

const elements = {
    themeSelector: document.getElementById('theme-selector'),
    authorityRail: document.getElementById('authority-rail'),
    authorityMatrixReviewPanel: document.getElementById('authority-matrix-review-panel'),
    layer3E2EGovernanceLifecycleDashboardPanel: document.getElementById('layer3-e2e-governance-lifecycle-dashboard-panel'),
    sublayerMapPanel: document.getElementById('sublayer-map-panel'),
    intentForm: document.getElementById('intent-form'),
    intentInput: document.getElementById('layer3-intent'),
    sourceFieldset: document.getElementById('source-fieldset'),
    rawMixedCorpusBatchId: document.getElementById('raw-mixed-corpus-batch-id'),
    rawMixedManifestRef: document.getElementById('raw-mixed-manifest-ref'),
    rawMixedManifestHash: document.getElementById('raw-mixed-manifest-hash'),
    rawMixedOperatorConfirmation: document.getElementById('raw-mixed-operator-confirmation'),
    rawMixedMaterialize: document.getElementById('raw-mixed-materialize'),
    rawMixedMaterializationState: document.getElementById('raw-mixed-materialization-state'),
    rawMixedMaterializationStatus: document.getElementById('raw-mixed-materialization-status'),
    datasetVersionCandidates: document.getElementById('dataset-version-candidates'),
    datasetVersionIds: document.getElementById('dataset-version-ids'),
    apsContentDocumentCandidates: document.getElementById('aps-content-document-candidates'),
    apsContentDocumentIds: document.getElementById('aps-content-document-ids'),
    runPreflight: document.getElementById('run-preflight'),
    materialLedgerBody: document.getElementById('material-ledger-body'),
    materialFilter: document.getElementById('material-filter'),
    gateBSubmit: document.getElementById('gate-b-submit'),
    gateCPreview: document.getElementById('gate-c-preview'),
    gateCCommit: document.getElementById('gate-c-commit'),
    gateCPanel: document.getElementById('gate-c-panel'),
    planStep: document.getElementById('plan-step-chip'),
    executionStep: document.getElementById('execution-step-chip'),
    resultsStep: document.getElementById('results-step-chip'),
    packageStep: document.getElementById('package-step-chip'),
    handoffStep: document.getElementById('handoff-step-chip'),
    planPreview: document.getElementById('plan-preview'),
    planReject: document.getElementById('plan-reject'),
    planRequestRevision: document.getElementById('plan-request-revision'),
    planApprove: document.getElementById('plan-approve'),
    planPanel: document.getElementById('plan-panel'),
    executionSelect: document.getElementById('execution-select'),
    executionStart: document.getElementById('execution-start'),
    executionSelectionStartPanel: document.getElementById('execution-selection-start-panel'),
    resultReviewRefresh: document.getElementById('result-review-refresh'),
    resultStatusInspect: document.getElementById('result-status-inspect'),
    resultReviewForm: document.getElementById('result-review-form'),
    resultReviewPanel: document.getElementById('result-review-panel'),
    resultReviewDecision: document.getElementById('result-review-decision'),
    resultReviewNotes: document.getElementById('result-review-notes'),
    resultReviewSubmit: document.getElementById('result-review-submit'),
    packageReviewPreviewInspect: document.getElementById('package-review-preview-inspect'),
    packageConstructionCommit: document.getElementById('package-construction-commit'),
    packageReviewSubmitForm: document.getElementById('package-review-submit-form'),
    packageReviewSubmitDecision: document.getElementById('package-review-submit-decision'),
    packageReviewSubmitNotes: document.getElementById('package-review-submit-notes'),
    packageReviewSubmit: document.getElementById('package-review-submit'),
    packageReviewPreviewPanel: document.getElementById('package-review-preview-panel'),
    packageLifecycleDashboardPanel: document.getElementById('package-lifecycle-dashboard-panel'),
    packageSupersessionPreviewPanel: document.getElementById('package-supersession-preview-panel'),
    packageSupersessionPreviewSubmit: document.getElementById('package-supersession-preview-submit'),
    sourceDirectoryPackageSupersessionPreviewPanel: document.getElementById('source-directory-package-supersession-preview-panel'),
    sourceDirectoryPackageSupersessionPreviewSubmit: document.getElementById('source-directory-package-supersession-preview-submit'),
    sourceDirectoryPackageSupersessionPreviewAuthority: document.getElementById('source-directory-package-supersession-preview-authority'),
    replacementPackageSetAuthorityPanel: document.getElementById('replacement-package-set-authority-panel'),
    replacementPackageSetAuthoritySubmit: document.getElementById('replacement-package-set-authority-submit'),
    packageSupersessionCommitPanel: document.getElementById('package-supersession-commit-panel'),
    packageSupersessionCommitSubmit: document.getElementById('package-supersession-commit-submit'),
    replacementPackageArtifactManifestPanel: document.getElementById('replacement-package-artifact-manifest-panel'),
    replacementPackageArtifactManifestSubmit: document.getElementById('replacement-package-artifact-manifest-submit'),
    replacementPackageNamespacePanel: document.getElementById('replacement-package-namespace-panel'),
    replacementPackageNamespaceSubmit: document.getElementById('replacement-package-namespace-submit'),
    handoffExportPrepareForm: document.getElementById('handoff-export-prepare-form'),
    handoffExportPreparePanel: document.getElementById('handoff-export-prepare-panel'),
    handoffExportPrepareDecision: document.getElementById('handoff-export-prepare-decision'),
    handoffExportPrepareNotes: document.getElementById('handoff-export-prepare-notes'),
    handoffExportPrepareSubmit: document.getElementById('handoff-export-prepare-submit'),
    apsHandoffDispatchForm: document.getElementById('aps-handoff-dispatch-form'),
    apsHandoffDispatchPanel: document.getElementById('aps-handoff-dispatch-panel'),
    apsHandoffDispatchSubmit: document.getElementById('aps-handoff-dispatch-submit'),
    externalExportDownloadPrepareForm: document.getElementById('external-export-download-prepare-form'),
    downstreamAccessLifecycleDashboardPanel: document.getElementById('downstream-access-lifecycle-dashboard-panel'),
    externalExportDownloadPreparePanel: document.getElementById('external-export-download-prepare-panel'),
    externalExportDownloadPrepareSubmit: document.getElementById('external-export-download-prepare-submit'),
    externalExportDownloadDeliveryForm: document.getElementById('external-export-download-delivery-form'),
    externalExportDownloadDeliveryPanel: document.getElementById('external-export-download-delivery-panel'),
    externalExportDownloadDeliverySubmit: document.getElementById('external-export-download-delivery-submit'),
    sourceDirectoryHybridMiddleLifecycleForm: document.getElementById('source-directory-hybrid-middle-lifecycle-form'),
    sourceDirectoryHybridMiddleLifecyclePanel: document.getElementById('source-directory-hybrid-middle-lifecycle-panel'),
    sourceDirectoryHybridMiddleLifecycleAuthority: document.getElementById('source-directory-hybrid-middle-lifecycle-authority'),
    sourceDirectoryHybridMiddleLifecycleSubmit: document.getElementById('source-directory-hybrid-middle-lifecycle-submit'),
    sourceDirectoryHybridExternalExportDownloadDeliveryForm: document.getElementById('source-directory-hybrid-external-export-download-delivery-form'),
    sourceDirectoryHybridRenderedStatusExtension: document.getElementById('source-directory-hybrid-rendered-status-extension'),
    sourceDirectoryHybridExternalExportDownloadDeliveryPanel: document.getElementById('source-directory-hybrid-external-export-download-delivery-panel'),
    sourceDirectoryHybridExternalExportDownloadDeliveryAuthority: document.getElementById('source-directory-hybrid-external-export-download-delivery-authority'),
    sourceDirectoryHybridExternalExportDownloadDeliveryStatus: document.getElementById('source-directory-hybrid-external-export-download-delivery-status'),
    sourceDirectoryHybridExternalExportDownloadDeliverySubmit: document.getElementById('source-directory-hybrid-external-export-download-delivery-submit'),
    sourceDirectoryHybridInternalWebhookForm: document.getElementById('source-directory-hybrid-internal-webhook-form'),
    sourceDirectoryHybridInternalWebhookPanel: document.getElementById('source-directory-hybrid-internal-webhook-panel'),
    sourceDirectoryHybridInternalWebhookAuthority: document.getElementById('source-directory-hybrid-internal-webhook-authority'),
    sourceDirectoryHybridInternalWebhookStatus: document.getElementById('source-directory-hybrid-internal-webhook-status'),
    sourceDirectoryHybridInternalWebhookSubmit: document.getElementById('source-directory-hybrid-internal-webhook-submit'),
    externalExportDownloadSignedReferenceForm: document.getElementById('external-export-download-signed-reference-form'),
    externalExportDownloadSignedReferencePanel: document.getElementById('external-export-download-signed-reference-panel'),
    externalExportDownloadSignedReferenceGenerate: document.getElementById('external-export-download-signed-reference-generate'),
    externalExportDownloadSignedReferenceUse: document.getElementById('external-export-download-signed-reference-use'),
    connectorLocalDestinationReceiptPanel: document.getElementById('connector-local-destination-receipt-panel'),
    serverOwnedLocalOutboxTargetPanel: document.getElementById('server-owned-local-outbox-target-panel'),
    serverOwnedLocalOutboxWritePanel: document.getElementById('server-owned-local-outbox-write-panel'),
    localOutboxProviderPrivateHandoffPanel: document.getElementById('local-outbox-provider-private-handoff-panel'),
    externalLocalExportPanel: document.getElementById('external-local-export-panel'),
    internalWebhookDispatchPanel: document.getElementById('internal-webhook-dispatch-panel'),
    providerPrivateSignedUrlForm: document.getElementById('provider-private-signed-url-form'),
    providerPrivateSignedUrlPanel: document.getElementById('provider-private-signed-url-panel'),
    providerPrivateSignedUrlPrepare: document.getElementById('provider-private-signed-url-prepare'),
    providerPrivateSignedUrlStatus: document.getElementById('provider-private-signed-url-status'),
    providerPrivateSignedUrlRevoke: document.getElementById('provider-private-signed-url-revoke'),
    providerPublicUrlForm: document.getElementById('provider-public-url-form'),
    providerPublicUrlPanel: document.getElementById('provider-public-url-panel'),
    providerPublicUrlPrepare: document.getElementById('provider-public-url-prepare'),
    providerPublicUrlStatus: document.getElementById('provider-public-url-status'),
    providerPublicUrlUse: document.getElementById('provider-public-url-use'),
    providerPublicUrlRevoke: document.getElementById('provider-public-url-revoke'),
    contextList: document.getElementById('context-list'),
    eventList: document.getElementById('event-list'),
    unavailableList: document.getElementById('unavailable-list'),
    stepChips: Array.from(document.querySelectorAll('.step-chip[data-step-target]')),
    operationsDock: document.querySelector('.operations-dock'),
    operationsDockNav: document.getElementById('operations-dock-nav'),
    operationsDockSummary: document.getElementById('operations-dock-summary'),
    mockupThemeShell: document.getElementById('mockup-theme-shell'),
    mockupThemeFrameList: document.getElementById('mockup-frame-list'),
    mockupFixtureScenario: document.getElementById('mockup-fixture-scenario'),
    mockupQuerySourceSetupProjection: document.getElementById('mockup-query-source-setup-projection'),
    mockupExecutionLanes: document.getElementById('mockup-execution-lanes'),
    mockupExecutionLanesProjection: document.getElementById('mockup-execution-lanes-projection'),
    mockupOutputReviewPackageHandoffProjection: document.getElementById('mockup-output-review-package-handoff-projection'),
    mockupSublayersAbBoard: document.getElementById('mockup-sublayers-ab-board'),
    mockupSublayersAbProjection: document.getElementById('mockup-sublayers-ab-projection'),
    mockupPdfLocationProjection: document.getElementById('mockup-pdf-location-projection'),
};

const systemThemeQuery = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : null;
const TERMINAL_PASS_STATUSES = new Set(['completed', 'completed_with_warnings', 'failed']);
const RESULT_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);
const PACKAGE_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);
const HANDOFF_EXPORT_PREPARE_DECISIONS_REQUIRING_NOTES = new Set(['hold', 'decline', 'blocked']);
const ASSOCIATED_COHORT_PASS_TYPE = 'associated_cohort';
const ASSOCIATED_COHORT_PASS_SCOPE = 'quantitative_associated_cohort_dataset_version';
const ASSOCIATED_COHORT_METHOD = 'descriptive_summary';
const ASSOCIATED_COHORT_METHOD_SOURCE = 'analysis_set.formation_basis_json.requested_method_name';
const ASSOCIATED_COHORT_SOURCE_GATE = '78_COHORT_FREEZE';
const ASSOCIATED_COHORT_SHAPE = 'aligned_wide_table';
const HANDOFF_EXPORT_PREPARE_RECORDED_STATES = new Set([
    'handoff_export_prepared',
    'handoff_export_held',
    'handoff_export_declined',
    'handoff_export_blocked',
]);
const APS_HANDOFF_DISPATCH_RECORDED_STATES = new Set(['aps_handoff_dispatched']);
const EXTERNAL_EXPORT_DOWNLOAD_RECORDED_STATES = new Set(['external_export_download_prepared']);
const EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RECORDED_STATES = new Set(['external_export_download_delivered']);
const PACKAGE_REVIEW_PACKAGE_KINDS = ['canonical_internal', 'user_facing', 'review_facing'];
const PACKAGE_REVIEW_PACKAGE_SCHEMA_IDS = Object.freeze({
    canonical_internal: 'layer3.canonical_internal_package.v1',
    user_facing: 'layer3.user_facing_package.v1',
    review_facing: 'layer3.review_facing_package.v1',
});
const SUBLAYER_MODALITIES = ['quantitative', 'qualitative', 'hybrid', 'unclassified'];
const SUBLAYER_MODALITY_META = {
    quantitative: {
        label: 'Quantitative Data',
        plane: 'Quantitative / Deterministic Environment',
        accent: 'green',
        empty: 'No quantitative objects are live in the current session state.',
    },
    qualitative: {
        label: 'Qualitative Data',
        plane: 'Qualitative Data Analysis Environment',
        accent: 'purple',
        empty: 'No qualitative objects are live in the current session state.',
    },
    hybrid: {
        label: 'Hybrid / Mixed Data',
        plane: 'Hybrid / Mixed Environment',
        accent: 'amber',
        empty: 'No hybrid or mixed objects are live in the current session state.',
    },
    unclassified: {
        label: 'Unclassified / Unsupported',
        plane: 'Unclassified Holding Area',
        accent: 'cyan',
        empty: 'No unclassified objects are currently reported.',
    },
};
const OPERATION_DOCK_STEPS = [
    { id: 'intent-band', key: 'intent', label: 'Intent', shortLabel: 'Intent', canvasLink: '3A intake setup', canvasTarget: '3a', canvasRole: 'Sublayer 3A intake/specification field' },
    { id: 'source-intake-rendered-controls', key: 'source_intake', label: 'Source Intake Controls', shortLabel: 'Source Intake', canvasLink: '3A source intake', canvasTarget: '3a', canvasRole: 'Sublayer 3A source intake upload/inventory/preview controls' },
    { id: 'gate-b-band', key: 'gate_b', label: 'Gate B Material Ledger', shortLabel: 'Gate B', canvasLink: '3A material ledger', canvasTarget: '3a', canvasRole: 'Sublayer 3A session-scoped material ledger' },
    { id: 'gate-c-band', key: 'gate_c', label: 'Gate C Typing Review', shortLabel: 'Gate C', canvasLink: '3B modality grouping', canvasTarget: '3b', canvasRole: 'Sublayer 3B modality object banks' },
    { id: 'plan-band', key: 'plan', label: 'Plan Preview And Approval', shortLabel: 'Plan', canvasLink: '3C process planning', canvasTarget: '3c-process', canvasRole: 'Sublayer 3C process/status planes' },
    { id: 'result-review-band', key: 'results', label: 'Result Review', shortLabel: 'Results', canvasLink: '3C output authority', canvasTarget: '3c-output', canvasRole: 'Sublayer 3C output/result fields' },
    { id: 'package-review-band', key: 'package', label: 'Package Review', shortLabel: 'Package', canvasLink: 'post-3C package controls', canvasTarget: 'post-3c', canvasRole: 'Post-3C package review control plane' },
    { id: 'handoff-export-band', key: 'handoff', label: 'Handoff / Export Preparation', shortLabel: 'Handoff', canvasLink: 'post-3C handoff controls', canvasTarget: 'post-3c', canvasRole: 'Post-3C handoff/export control plane' },
    { id: 'aps-handoff-band', key: 'aps', label: 'APS Handoff Dispatch', shortLabel: 'APS', canvasLink: 'post-3C APS bridge', canvasTarget: 'post-3c', canvasRole: 'Post-3C APS dispatch bridge' },
    { id: 'external-export-download-band', key: 'external', label: 'External Export / Download', shortLabel: 'External', canvasLink: 'post-3C delivery controls', canvasTarget: 'post-3c', canvasRole: 'Post-3C delivery readiness controls' },
];

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function isSharedThemePreference(value) {
    return value === 'system' || value === 'light' || value === 'dark';
}

function isLayer3ThemePreference(value) {
    return value === 'workbench' || value === LAYER3_MOCKUP_WORKBENCH_THEME;
}

function isClaudePrototypePreference(value) {
    return value === 'claude';
}

function isValidThemePreference(value) {
    return isSharedThemePreference(value) || isLayer3ThemePreference(value) || isClaudePrototypePreference(value);
}

function resolveTheme(preference) {
    if (preference === LAYER3_MOCKUP_WORKBENCH_THEME) return 'workbench';
    if (preference === 'light' || preference === 'dark' || preference === 'workbench') return preference;
    return systemThemeQuery?.matches ? 'dark' : 'light';
}

function applyThemePreference(preference, { persist = true } = {}) {
    const normalized = isValidThemePreference(preference) ? preference : 'system';
    if (isClaudePrototypePreference(normalized)) {
        if (persist) {
            window.location.assign('/review/layer3/static/claude.html');
        }
        return;
    }
    document.documentElement.dataset.themePreference = normalized;
    document.documentElement.dataset.theme = resolveTheme(normalized);
    if (normalized === LAYER3_MOCKUP_WORKBENCH_THEME) {
        document.documentElement.dataset.themeVariant = LAYER3_MOCKUP_WORKBENCH_THEME;
    } else {
        delete document.documentElement.dataset.themeVariant;
    }
    State.themePreference = normalized;
    if (elements.themeSelector) {
        elements.themeSelector.value = normalized;
    }
    renderMockupThemeShell();
    if (persist) {
        try {
            if (isSharedThemePreference(normalized)) {
                localStorage.removeItem(LAYER3_THEME_STORAGE_KEY);
                localStorage.setItem(THEME_STORAGE_KEY, normalized);
            } else {
                localStorage.setItem(LAYER3_THEME_STORAGE_KEY, normalized);
                if (localStorage.getItem(THEME_STORAGE_KEY) === normalized) {
                    localStorage.removeItem(THEME_STORAGE_KEY);
                }
            }
        } catch (error) {
            addEvent('Theme preference kept in browser memory only.');
        }
    }
}

function renderMockupThemeShell() {
    if (!elements.mockupThemeShell) return;
    const active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME;
    elements.mockupThemeShell.dataset.active = active ? 'true' : 'false';
    elements.mockupThemeShell.setAttribute('aria-hidden', active ? 'false' : 'true');
    elements.mockupThemeShell.dataset.firstSlice = LAYER3_MOCKUP_THEME_FIRST_SLICE;
    if (elements.mockupFixtureScenario) {
        elements.mockupFixtureScenario.dataset.fixtureScenario = LAYER3_MOCKUP_THEME_FIXTURE.scenario;
    }
    if (elements.mockupThemeFrameList && elements.mockupThemeFrameList.childElementCount === 0) {
        LAYER3_MOCKUP_THEME_FIXTURE.frames.forEach((frame) => {
            const item = document.createElement('li');
            item.textContent = frame;
            elements.mockupThemeFrameList.appendChild(item);
        });
    }
    renderMockupPdfLocationProjection(active);
    renderMockupQuerySourceSetupProjection(active);
    renderMockupSublayersAbLiveProjection(active);
    renderMockupExecutionLanesLiveProjection(active);
    renderMockupOutputReviewPackageHandoffProjection(active);
}

function mockupPdfLocationHighlightSpanCount(item) {
    const spans = Array.isArray(item?.highlight_spans) ? item.highlight_spans : [];
    if (spans.length > 0) return spans.length;
    const count = Number(item?.highlight_span_count);
    return Number.isFinite(count) && count > 0 ? count : 0;
}

function renderMockupPdfLocationProjection(active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME) {
    const panel = elements.mockupPdfLocationProjection;
    if (!panel) return;
    if (!active) {
        panel.dataset.projectionState = 'inactive';
        panel.innerHTML = '';
        return;
    }

    const projection = State.sessionSummary?.pdf_location_projection || null;
    const locationItems = Array.isArray(projection?.location_items) ? projection.location_items : [];
    const available = projection?.available === true;
    const blockedReason = projection?.blocked_reason || projection?.reason || 'session summary not loaded';
    const status = available
        ? `${locationItems.length} server-authoritative PDF location item${locationItems.length === 1 ? '' : 's'} available.`
        : `Server PDF-location projection unavailable: ${blockedReason}.`;
    const body = locationItems.length
        ? locationItems.map((item) => {
            const highlightSpanCount = mockupPdfLocationHighlightSpanCount(item);
            const highlightSpanLabel = `${highlightSpanCount} citation highlight span${highlightSpanCount === 1 ? '' : 's'}`;
            return `
            <article class="mockup-pdf-location-item">
                <strong>${escapeHtml(item.page_label || item.page || 'Located page')}</strong>
                <span>${escapeHtml(item.chunk_id || item.content_id || 'chunk unavailable')}</span>
                <span class="mockup-pdf-location-highlight">${escapeHtml(highlightSpanLabel)}</span>
                <p>${escapeHtml(item.bounded_text_preview || item.preview || 'No bounded preview supplied.')}</p>
            </article>
        `;
        }).join('')
        : '<span class="mockup-disabled-control" aria-disabled="true">Read-only server projection pending</span>';

    panel.dataset.projectionState = available ? 'available' : 'unavailable';
    panel.innerHTML = `
        <span class="mockup-frame-label">Server PDF-location projection</span>
        <p class="mockup-pdf-location-status">${escapeHtml(status)}</p>
        <div class="mockup-pdf-location-items" aria-label="Server-authoritative PDF location items">
            ${body}
        </div>
    `;
}

function mockupQuerySourceArrayCount(value) {
    return Array.isArray(value) ? value.length : 0;
}

function mockupQuerySourceStatusState(id) {
    const element = document.getElementById(id);
    return element?.dataset?.state || 'not loaded';
}

function mockupQuerySourceRenderedCounts() {
    return {
        sourceIntakeInventoryCount: document.querySelectorAll('#source-intake-inventory-list .source-intake-inventory-item').length,
        sourceIntakePreviewReady: Boolean(document.querySelector('#source-intake-preview-panel .source-intake-gate-b-admission')),
        sourceDirectoryAuthorityCount: document.querySelectorAll('#source-directory-ingestion-panel .source-intake-proof-list li').length,
    };
}

function mockupQuerySourceSetupServerSources(counts) {
    const sources = [];
    const add = (condition, label) => {
        if (condition && !sources.includes(label)) sources.push(label);
    };

    add(mockupProjectionObjectLoaded(State.preflight), 'State.preflight');
    add(mockupProjectionObjectLoaded(State.sourcePreview), 'State.sourcePreview');
    add(mockupProjectionObjectLoaded(State.materialPreview), 'State.materialPreview');
    add(counts.sourceIntakeInventoryCount > 0 || counts.sourceIntakePreviewReady, 'source-intake rendered control state');
    add(counts.sourceDirectoryAuthorityCount > 0, 'source-directory rendered control state');
    add(mockupProjectionObjectLoaded(State.sessionSummary), 'State.sessionSummary');
    return sources;
}

function mockupQuerySourceSetupState() {
    const counts = mockupQuerySourceRenderedCounts();
    const selectedClasses = selectedSourceClasses();
    const sourceCandidates = State.sourcePreview?.source_candidates || [];
    const materialCandidates = State.materialPreview?.material_candidates || [];
    const sources = mockupQuerySourceSetupServerSources(counts);
    return {
        sources,
        selectedSourceClassCount: selectedClasses.length,
        selectedSourceClassLabel: selectedClasses.length
            ? selectedClasses.map((sourceClass) => humanizeToken(sourceClass)).join(', ')
            : 'no source classes selected',
        preflightState: State.preflight?.schema_id ? 'loaded' : 'not loaded',
        preflightLoaded: mockupProjectionObjectLoaded(State.preflight),
        sourceCandidateCount: mockupQuerySourceArrayCount(sourceCandidates),
        materialCandidateCount: mockupQuerySourceArrayCount(materialCandidates),
        sourceIntakeInventoryCount: counts.sourceIntakeInventoryCount,
        sourceIntakeStatus: mockupQuerySourceStatusState('source-intake-status'),
        sourceIntakePreviewReady: counts.sourceIntakePreviewReady,
        sourceDirectoryAuthorityCount: counts.sourceDirectoryAuthorityCount,
        sourceDirectoryStatus: mockupQuerySourceStatusState('source-directory-ingestion-message'),
        sessionSummaryLoaded: mockupProjectionObjectLoaded(State.sessionSummary),
    };
}

function mockupQuerySourceSetupStatus(model) {
    if (!model.sources.length) {
        return 'Server query/source setup projection unavailable: preflight, source-preview, material-preview, source-intake, source-directory, and session-summary state are not loaded.';
    }
    return [
        mockupCountLabel(model.sourceCandidateCount, 'source candidate'),
        mockupCountLabel(model.materialCandidateCount, 'material candidate'),
        `${mockupCountLabel(model.sourceIntakeInventoryCount, 'source-intake inventory row')} and ${mockupCountLabel(model.sourceDirectoryAuthorityCount, 'source-directory authority label')} available from read-only server state.`,
    ].join(', ');
}

function renderMockupQuerySourceSetupProjection(active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME) {
    const fixture = elements.mockupFixtureScenario;
    const panel = elements.mockupQuerySourceSetupProjection;
    if (!fixture || !panel) return;
    if (!active) {
        fixture.dataset.querySourceProjectionState = 'inactive';
        panel.dataset.projectionState = 'inactive';
        panel.innerHTML = '';
        return;
    }

    const model = mockupQuerySourceSetupState();
    const available = model.sources.length > 0
        && (
            model.preflightLoaded
            || model.sourceCandidateCount > 0
            || model.materialCandidateCount > 0
            || model.sourceIntakeInventoryCount > 0
            || model.sourceIntakePreviewReady
            || model.sourceDirectoryAuthorityCount > 0
            || model.sessionSummaryLoaded
        );
    const sourceList = model.sources.length
        ? model.sources.map((source) => `<span>${escapeHtml(source)}</span>`).join('')
        : '<span>server query/source setup state unavailable</span>';

    fixture.dataset.querySourceProjectionState = available ? 'available' : 'unavailable';
    fixture.dataset.querySourceProjectionReadOnly = 'true';
    panel.dataset.projectionState = available ? 'available' : 'unavailable';
    panel.dataset.readOnly = 'true';
    panel.innerHTML = `
        <div class="mockup-query-source-projection-head">
            <span class="mockup-frame-label">Server-owned query/source setup projection</span>
            <strong>${escapeHtml(available ? 'Live read-only' : 'Read-only unavailable')}</strong>
            <p>${escapeHtml(mockupQuerySourceSetupStatus(model))}</p>
        </div>
        <div class="mockup-query-source-live-grid" aria-label="Read-only query and source setup state counts">
            <article>
                <span>Preflight</span>
                <strong>${escapeHtml(model.preflightState)}</strong>
                <p>${escapeHtml(model.selectedSourceClassLabel)}</p>
            </article>
            <article>
                <span>Source classes</span>
                <strong>${escapeHtml(model.selectedSourceClassCount)}</strong>
                <p>operator-selected existing controls</p>
            </article>
            <article>
                <span>Source preview</span>
                <strong>${escapeHtml(model.sourceCandidateCount)}</strong>
                <p>response-safe candidates</p>
            </article>
            <article>
                <span>Material preview</span>
                <strong>${escapeHtml(model.materialCandidateCount)}</strong>
                <p>response-safe candidates</p>
            </article>
            <article>
                <span>Source intake</span>
                <strong>${escapeHtml(model.sourceIntakeInventoryCount)}</strong>
                <p>${escapeHtml(model.sourceIntakePreviewReady ? 'preview ready' : model.sourceIntakeStatus)}</p>
            </article>
            <article>
                <span>Source directory</span>
                <strong>${escapeHtml(model.sourceDirectoryAuthorityCount)}</strong>
                <p>${escapeHtml(model.sourceDirectoryStatus)}</p>
            </article>
        </div>
        <div class="mockup-query-source-source-list" aria-label="Server state sources used by this read-only query/source projection">
            ${sourceList}
        </div>
        ${available ? '' : '<span class="mockup-disabled-control" aria-disabled="true">Read-only query/source setup projection pending</span>'}
    `;
}

function mockupSublayersAbServerSources() {
    const sources = [];
    if (State.sessionSummary?.sublayer_visualization) {
        sources.push('State.sessionSummary.sublayer_visualization');
    }
    if (State.materialPreview?.schema_id || (State.materialPreview?.material_candidates || []).length) {
        sources.push('State.materialPreview');
    }
    if (State.gateB?.schema_id || State.gateB?.session_id) {
        sources.push('State.gateB');
    }
    if (State.gateC?.schema_id || State.gateC?.session_id) {
        sources.push('State.gateC');
    }
    if (State.sessionSummary?.authority_rail) {
        sources.push('State.sessionSummary.authority_rail');
    }
    return sources;
}

function mockupSublayersAbGateLabel(value) {
    if (value === 'gate_b') return 'Gate B';
    if (value === 'gate_c') return 'Gate C';
    return humanizeToken(value || 'unavailable');
}

function renderMockupSublayersAbLiveProjection(active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME) {
    const board = elements.mockupSublayersAbBoard;
    const panel = elements.mockupSublayersAbProjection;
    if (!board || !panel) return;
    if (!active) {
        board.dataset.liveProjectionState = 'inactive';
        panel.dataset.projectionState = 'inactive';
        panel.innerHTML = '';
        return;
    }

    const model = currentSublayerVisualizationModel();
    const rail = model.rail || {};
    const materialCount = model.threeA.objects.length;
    const modalityCounts = model.threeB.buckets.map((bucket) => ({
        modality: bucket.modality,
        label: bucket.meta.label,
        count: bucket.objects.length,
    }));
    const typingCount = modalityCounts.reduce((total, bucket) => total + bucket.count, 0);
    const serverSources = mockupSublayersAbServerSources();
    const hasSessionScope = Boolean(rail.session_id && rail.session_id !== 'none');
    const available = serverSources.length > 0 && (materialCount > 0 || typingCount > 0 || hasSessionScope);
    const gateRailLabel = mockupSublayersAbGateLabel(rail.current_gate);
    const status = available
        ? `${materialCount} read-only 3A material object${materialCount === 1 ? '' : 's'} and ${typingCount} read-only 3B typing object${typingCount === 1 ? '' : 's'} available from server-owned state.`
        : 'Server Sublayers 3A/3B projection unavailable: material, Gate B, Gate C, and session-summary state are not loaded.';
    const modalityRows = modalityCounts
        .filter((bucket) => bucket.modality !== 'unclassified' || bucket.count > 0)
        .map((bucket) => `
            <li data-modality="${escapeHtml(bucket.modality)}">
                <span>${escapeHtml(bucket.label)}</span>
                <strong>${escapeHtml(bucket.count)}</strong>
            </li>
        `).join('');
    const sourceList = serverSources.length
        ? serverSources.map((source) => `<span>${escapeHtml(source)}</span>`).join('')
        : '<span>server state unavailable</span>';

    board.dataset.liveProjectionState = available ? 'available' : 'unavailable';
    board.dataset.liveProjectionReadOnly = 'true';
    panel.dataset.projectionState = available ? 'available' : 'unavailable';
    panel.dataset.readOnly = 'true';
    panel.innerHTML = `
        <div class="mockup-sublayers-ab-projection-head">
            <span class="mockup-frame-label">Server-owned Sublayers 3A/3B projection</span>
            <strong>${escapeHtml(available ? 'Live read-only' : 'Read-only unavailable')}</strong>
            <p>${escapeHtml(status)}</p>
        </div>
        <div class="mockup-sublayers-ab-live-grid" aria-label="Read-only Sublayers 3A and 3B state counts">
            <article>
                <span>Sublayer 3A material ledger</span>
                <strong>${escapeHtml(materialCount)}</strong>
                <p>${escapeHtml(model.threeA.stateLabel)}</p>
            </article>
            <article>
                <span>Sublayer 3B typing banks</span>
                <strong>${escapeHtml(typingCount)}</strong>
                <p>${escapeHtml(model.threeB.stateLabel)}</p>
            </article>
            <article>
                <span>Gate rail posture</span>
                <strong>${escapeHtml(gateRailLabel)}</strong>
                <p>${escapeHtml(`typing ${rail.typing_status || 'not_started'}`)}</p>
            </article>
        </div>
        <ul class="mockup-sublayers-ab-modality-counts" aria-label="Read-only Gate C modality counts">
            ${modalityRows || '<li data-modality="empty"><span>No Gate C modality objects</span><strong>0</strong></li>'}
        </ul>
        <div class="mockup-sublayers-ab-source-list" aria-label="Server state sources used by this read-only projection">
            ${sourceList}
        </div>
        ${available ? '' : '<span class="mockup-disabled-control" aria-disabled="true">Read-only server state projection pending</span>'}
    `;
}

function mockupProjectionObjectLoaded(value) {
    return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function mockupExecutionLanesServerSources() {
    const sources = [];
    const summary = State.sessionSummary || {};
    const add = (condition, label) => {
        if (condition && !sources.includes(label)) sources.push(label);
    };

    add(mockupProjectionObjectLoaded(summary.sublayer_visualization), 'State.sessionSummary.sublayer_visualization');
    add(mockupProjectionObjectLoaded(summary.analysis_environment_projection), 'State.sessionSummary.analysis_environment_projection');
    add(mockupProjectionObjectLoaded(summary.plan_preview), 'State.sessionSummary.plan_preview');
    add(mockupProjectionObjectLoaded(summary.plan_approval), 'State.sessionSummary.plan_approval');
    add(mockupProjectionObjectLoaded(summary.execution_selection), 'State.sessionSummary.execution_selection');
    add(mockupProjectionObjectLoaded(summary.analysis_execution_start), 'State.sessionSummary.analysis_execution_start');
    add(mockupProjectionObjectLoaded(summary.execution_result_review), 'State.sessionSummary.execution_result_review');
    add(mockupProjectionObjectLoaded(State.planPreview), 'State.planPreview');
    add(mockupProjectionObjectLoaded(State.planApproval), 'State.planApproval');
    add(mockupProjectionObjectLoaded(State.executionSelection), 'State.executionSelection');
    add(mockupProjectionObjectLoaded(State.executionStart), 'State.executionStart');
    add(mockupProjectionObjectLoaded(State.resultStatus), 'State.resultStatus');
    add(mockupProjectionObjectLoaded(State.resultReview), 'State.resultReview');
    return sources;
}

function mockupCountLabel(count, singular, plural = `${singular}s`) {
    return `${count} ${count === 1 ? singular : plural}`;
}

function mockupExecutionLanesStatus(model, counts, sources) {
    if (!sources.length) {
        return 'Server Sublayer 3C execution-lanes projection unavailable: session, plan, execution, result, and analysis-environment state are not loaded.';
    }
    if (!counts.inputCount && !counts.passCount && !counts.processCount && !counts.outputCount && !counts.analysisProjectionLoaded) {
        return 'Server Sublayer 3C execution-lanes projection unavailable: loaded state contains no 3C input, plan, process, output, or analysis-environment readiness.';
    }
    return [
        mockupCountLabel(counts.inputCount, 'live input object'),
        mockupCountLabel(counts.passCount, 'plan/pass shell'),
        mockupCountLabel(counts.processCount, 'process state'),
        `${mockupCountLabel(counts.outputCount, 'output/result field')} available from server-owned 3C state.`,
    ].join(', ');
}

function mockupExecutionLanesSafeState(model) {
    const plan = currentPlanBody() || {};
    const resultReview = recordedResultReview() || State.resultReview || {};
    const selection = State.executionSelection || State.sessionSummary?.execution_selection || {};
    const start = State.executionStart || State.sessionSummary?.analysis_execution_start || {};
    const status = State.resultStatus || {};
    return {
        planStatus: humanizeToken(
            State.sessionSummary?.plan_approval?.plan_status
            || State.sessionSummary?.plan_approval?.state
            || State.sessionSummary?.plan_preview?.state
            || plan.plan_status
            || plan.status
            || model.threeC.state
        ),
        executionStatus: humanizeToken(
            selection.state
            || start.state
            || start.pass_run_status
            || status.pass_run_status
            || model.threeC.executionPipeline.state
        ),
        resultStatus: humanizeToken(
            resultReview.review_state
            || resultReview.operator_decision
            || status.pass_run_status
            || status.status
            || 'not reported'
        ),
    };
}

function renderMockupExecutionLanesLiveProjection(active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME) {
    const lanes = elements.mockupExecutionLanes;
    const panel = elements.mockupExecutionLanesProjection;
    if (!lanes || !panel) return;
    if (!active) {
        lanes.dataset.liveProjectionState = 'inactive';
        panel.dataset.projectionState = 'inactive';
        panel.innerHTML = '';
        return;
    }

    const model = currentSublayerVisualizationModel();
    const planeStats = model.threeC.planes.map((plane) => ({
        modality: plane.modality,
        label: plane.meta.plane,
        inputCount: plane.inputs.length,
        passCount: plane.passes.length,
        processCount: plane.processCards.length,
        outputCount: plane.outputs.length,
        readinessState: plane.analysisEnvironmentPlaneReadiness?.state || 'not reported',
    }));
    const counts = {
        inputCount: planeStats.reduce((total, plane) => total + plane.inputCount, 0),
        passCount: planeStats.reduce((total, plane) => total + plane.passCount, 0),
        processCount: model.threeC.executionPipeline.cards.length,
        outputCount: model.threeC.executionPipeline.outputs.length,
        analysisProjectionLoaded: mockupProjectionObjectLoaded(State.sessionSummary?.analysis_environment_projection),
    };
    const sources = mockupExecutionLanesServerSources();
    const safeState = mockupExecutionLanesSafeState(model);
    const available = sources.length > 0
        && (counts.inputCount > 0 || counts.passCount > 0 || counts.processCount > 0 || counts.outputCount > 0 || counts.analysisProjectionLoaded);
    const sourceList = sources.length
        ? sources.map((source) => `<span>${escapeHtml(source)}</span>`).join('')
        : '<span>server 3C state unavailable</span>';
    const planeRows = planeStats.map((plane) => `
        <li data-modality="${escapeHtml(plane.modality)}">
            <span>${escapeHtml(plane.label)}</span>
            <strong>${escapeHtml(`${plane.inputCount} inputs / ${plane.passCount} plans / ${plane.processCount} process / ${plane.outputCount} outputs`)}</strong>
            <em>${escapeHtml(humanizeToken(plane.readinessState))}</em>
        </li>
    `).join('');

    lanes.dataset.liveProjectionState = available ? 'available' : 'unavailable';
    lanes.dataset.liveProjectionReadOnly = 'true';
    panel.dataset.projectionState = available ? 'available' : 'unavailable';
    panel.dataset.readOnly = 'true';
    panel.innerHTML = `
        <div class="mockup-execution-lanes-projection-head">
            <span class="mockup-frame-label">Server-owned Sublayer 3C execution-lanes projection</span>
            <strong>${escapeHtml(available ? 'Live read-only' : 'Read-only unavailable')}</strong>
            <p>${escapeHtml(mockupExecutionLanesStatus(model, counts, sources))}</p>
        </div>
        <div class="mockup-execution-lanes-live-grid" aria-label="Read-only Sublayer 3C execution-lane state counts">
            <article>
                <span>Input object banks</span>
                <strong>${escapeHtml(counts.inputCount)}</strong>
                <p>${escapeHtml(model.threeC.stateLabel)}</p>
            </article>
            <article>
                <span>Plan/pass shells</span>
                <strong>${escapeHtml(counts.passCount)}</strong>
                <p>${escapeHtml(safeState.planStatus)}</p>
            </article>
            <article>
                <span>Process state</span>
                <strong>${escapeHtml(counts.processCount)}</strong>
                <p>${escapeHtml(safeState.executionStatus)}</p>
            </article>
            <article>
                <span>Output/result fields</span>
                <strong>${escapeHtml(counts.outputCount)}</strong>
                <p>${escapeHtml(safeState.resultStatus)}</p>
            </article>
        </div>
        <ul class="mockup-execution-lane-plane-counts" aria-label="Read-only per-plane 3C state counts">
            ${planeRows}
        </ul>
        <div class="mockup-execution-lanes-source-list" aria-label="Server state sources used by this read-only 3C projection">
            ${sourceList}
        </div>
        ${available ? '' : '<span class="mockup-disabled-control" aria-disabled="true">Read-only 3C server state projection pending</span>'}
    `;
}

function mockupOutputReviewPackageHandoffServerSources() {
    const sources = [];
    const summary = State.sessionSummary || {};
    const add = (condition, label) => {
        if (condition && !sources.includes(label)) sources.push(label);
    };

    add(mockupProjectionObjectLoaded(State.resultStatus), 'State.resultStatus');
    add(mockupProjectionObjectLoaded(State.resultReview), 'State.resultReview');
    add(mockupProjectionObjectLoaded(summary.execution_result_review), 'State.sessionSummary.execution_result_review');
    add(mockupProjectionObjectLoaded(State.packageReviewPreview), 'State.packageReviewPreview');
    add(mockupProjectionObjectLoaded(summary.package_review_preview), 'State.sessionSummary.package_review_preview');
    add(mockupProjectionObjectLoaded(packageConstructionState()), 'State.packageConstruction');
    add(mockupProjectionObjectLoaded(summary.package_construction), 'State.sessionSummary.package_construction');
    add(mockupProjectionObjectLoaded(packageReviewSubmitState()), 'State.packageReviewSubmit');
    add(mockupProjectionObjectLoaded(summary.package_review_submit), 'State.sessionSummary.package_review_submit');
    add(mockupProjectionObjectLoaded(State.packageSupersessionPreview), 'State.packageSupersessionPreview');
    add(mockupProjectionObjectLoaded(State.replacementPackageSetAuthority), 'State.replacementPackageSetAuthority');
    add(mockupProjectionObjectLoaded(State.packageSupersessionCommit), 'State.packageSupersessionCommit');
    add(mockupProjectionObjectLoaded(State.replacementPackageArtifactManifest), 'State.replacementPackageArtifactManifest');
    add(mockupProjectionObjectLoaded(State.replacementPackageNamespace), 'State.replacementPackageNamespace');
    add(mockupProjectionObjectLoaded(handoffExportPrepareState()), 'State.handoffExportPrepare');
    add(mockupProjectionObjectLoaded(summary.handoff_export_prepare), 'State.sessionSummary.handoff_export_prepare');
    add(mockupProjectionObjectLoaded(apsHandoffDispatchState()), 'State.apsHandoffDispatch');
    add(mockupProjectionObjectLoaded(summary.aps_handoff_dispatch), 'State.sessionSummary.aps_handoff_dispatch');
    add(mockupProjectionObjectLoaded(externalExportDownloadPrepareState()), 'State.externalExportDownloadPrepare');
    add(mockupProjectionObjectLoaded(summary.external_export_download), 'State.sessionSummary.external_export_download');
    add(mockupProjectionObjectLoaded(State.externalExportDownloadDelivery), 'State.externalExportDownloadDelivery');
    add(mockupProjectionObjectLoaded(State.externalExportDownloadSignedReference), 'State.externalExportDownloadSignedReference');
    add(sources.some((source) => source.startsWith('State.sessionSummary.')), 'State.sessionSummary');
    return sources;
}

function mockupOutputReviewStateLabel(value, fallback = 'not loaded') {
    const text = String(value ?? '').trim();
    if (!text) return fallback;
    if (/([a-z][a-z0-9+.-]*:\/\/|[A-Za-z]:\\|\\\\)/i.test(text)) {
        return 'redacted unsafe label';
    }
    return humanizeToken(text.slice(0, 80));
}

function mockupOutputReviewPackageHandoffState() {
    const status = State.resultStatus || {};
    const review = recordedResultReview() || {};
    const preview = State.packageReviewPreview || State.sessionSummary?.package_review_preview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const external = externalExportDownloadPrepareState() || {};
    const signed = State.externalExportDownloadSignedReference || {};
    const packageKinds = packageKindsFromState().filter(Boolean);
    const packageRows = packageLifecycleOutputRows();
    const downstream = new Set([
        ...arrayFromServer(review.downstream_unavailable),
        ...arrayFromServer(preview.downstream_unavailable),
        ...arrayFromServer(construction.downstream_unavailable),
        ...arrayFromServer(submit.downstream_unavailable),
        ...arrayFromServer(handoff.downstream_unavailable),
        ...arrayFromServer(aps.downstream_unavailable),
        ...arrayFromServer(external.downstream_unavailable),
        ...currentDownstreamUnavailable(),
    ]);

    return {
        resultStatusLabel: mockupOutputReviewStateLabel(status.pass_run_status || status.status),
        resultReviewLabel: mockupOutputReviewStateLabel(review.review_state || review.state || review.operator_decision),
        packagePreviewLabel: mockupOutputReviewStateLabel(
            preview.next_state
            || preview.state
            || (preview.package_review_preview_enabled === true ? 'package_review_preview_available' : null),
        ),
        packageConstructionLabel: mockupOutputReviewStateLabel(
            construction.next_state
            || construction.state
            || (construction.package_commit_enabled === true ? 'package_construction_ready' : null),
        ),
        packageSubmitLabel: mockupOutputReviewStateLabel(
            submit.package_review_state
            || submit.next_state
            || submit.state
            || (submit.package_review_submit_enabled === true ? 'package_review_submit_ready' : null),
        ),
        handoffPrepareLabel: mockupOutputReviewStateLabel(
            handoff.handoff_export_state
            || handoff.next_state
            || handoff.state
            || (handoff.handoff_export_prepare_enabled === true ? 'handoff_export_prepare_ready' : null),
        ),
        apsHandoffLabel: mockupOutputReviewStateLabel(apsHandoffStateName(aps)),
        externalDownloadLabel: mockupOutputReviewStateLabel(externalExportDownloadStateName(external)),
        signedReferenceLabel: mockupOutputReviewStateLabel(signed.signed_reference_state),
        candidateKindCount: Array.isArray(preview.candidate_package_kinds) ? preview.candidate_package_kinds.length : 0,
        packageKindCount: packageKinds.length,
        outputPackageCount: Math.max(packageRows.length, packageOutputPackageIds().length),
        payloadHashCount: packagePayloadHashes().length,
        downstreamBlockedCount: downstream.size,
    };
}

function mockupOutputReviewPackageHandoffStatus(model, sources) {
    if (!sources.length) {
        return 'Server output review package handoff projection unavailable: result, package, handoff, external export, and session-summary state are not loaded.';
    }
    return [
        `${mockupCountLabel(model.packageKindCount, 'package kind')} and ${mockupCountLabel(model.outputPackageCount, 'output package')} visible as response-safe counts.`,
        `${mockupCountLabel(model.payloadHashCount, 'payload hash', 'payload hashes')} and ${mockupCountLabel(model.downstreamBlockedCount, 'blocked downstream state')} available from existing server-owned state.`,
    ].join(' ');
}

function renderMockupOutputReviewPackageHandoffProjection(active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME) {
    const lanes = elements.mockupExecutionLanes;
    const panel = elements.mockupOutputReviewPackageHandoffProjection;
    const outputCard = document.querySelector('.mockup-flow-card.mockup-3c');
    if (!panel) return;
    if (!active) {
        if (lanes) lanes.dataset.outputReviewPackageHandoffProjectionState = 'inactive';
        if (outputCard) outputCard.dataset.outputReviewPackageHandoffProjectionState = 'inactive';
        panel.dataset.projectionState = 'inactive';
        panel.innerHTML = '';
        return;
    }

    const sources = mockupOutputReviewPackageHandoffServerSources();
    const model = mockupOutputReviewPackageHandoffState();
    const available = sources.length > 0
        && (
            model.resultStatusLabel !== 'not loaded'
            || model.resultReviewLabel !== 'not loaded'
            || model.packagePreviewLabel !== 'not loaded'
            || model.packageConstructionLabel !== 'not loaded'
            || model.packageSubmitLabel !== 'not loaded'
            || model.handoffPrepareLabel !== 'not loaded'
            || model.apsHandoffLabel !== 'not loaded'
            || model.externalDownloadLabel !== 'not loaded'
            || model.signedReferenceLabel !== 'not loaded'
            || model.packageKindCount > 0
            || model.outputPackageCount > 0
        );
    const sourceList = sources.length
        ? sources.map((source) => `<span>${escapeHtml(source)}</span>`).join('')
        : '<span>server output review package handoff state unavailable</span>';

    if (lanes) {
        lanes.dataset.outputReviewPackageHandoffProjectionState = available ? 'available' : 'unavailable';
        lanes.dataset.outputReviewPackageHandoffProjectionReadOnly = 'true';
    }
    if (outputCard) {
        outputCard.dataset.outputReviewPackageHandoffProjectionState = available ? 'available' : 'unavailable';
        outputCard.dataset.outputReviewPackageHandoffProjectionReadOnly = 'true';
    }
    panel.dataset.projectionState = available ? 'available' : 'unavailable';
    panel.dataset.readOnly = 'true';
    panel.innerHTML = `
        <div class="mockup-output-review-projection-head">
            <span class="mockup-frame-label">Server-owned output review package handoff projection</span>
            <strong>${escapeHtml(available ? 'Live read-only' : 'Read-only unavailable')}</strong>
            <p>${escapeHtml(mockupOutputReviewPackageHandoffStatus(model, sources))}</p>
        </div>
        <div class="mockup-output-review-live-grid" aria-label="Read-only output review package handoff state counts">
            <article>
                <span>Result review</span>
                <strong>${escapeHtml(model.resultReviewLabel)}</strong>
                <p>${escapeHtml(model.resultStatusLabel)}</p>
            </article>
            <article>
                <span>Package preview</span>
                <strong>${escapeHtml(model.packagePreviewLabel)}</strong>
                <p>${escapeHtml(mockupCountLabel(model.candidateKindCount, 'candidate kind'))}</p>
            </article>
            <article>
                <span>Package lifecycle</span>
                <strong>${escapeHtml(model.packageConstructionLabel)}</strong>
                <p>${escapeHtml(`${mockupCountLabel(model.outputPackageCount, 'package row')} / ${mockupCountLabel(model.payloadHashCount, 'payload hash', 'payload hashes')}`)}</p>
            </article>
            <article>
                <span>Package review</span>
                <strong>${escapeHtml(model.packageSubmitLabel)}</strong>
                <p>${escapeHtml(mockupCountLabel(model.downstreamBlockedCount, 'blocked downstream state'))}</p>
            </article>
            <article>
                <span>Handoff/export</span>
                <strong>${escapeHtml(model.handoffPrepareLabel)}</strong>
                <p>${escapeHtml(`${model.apsHandoffLabel} / ${model.externalDownloadLabel} / ${model.signedReferenceLabel}`)}</p>
            </article>
        </div>
        <div class="mockup-output-review-source-list" aria-label="Server state sources used by this read-only output review package handoff projection">
            ${sourceList}
        </div>
        ${available ? '' : '<span class="mockup-disabled-control" aria-disabled="true">Read-only output review package handoff projection pending</span>'}
    `;
}

async function parseResponse(res) {
    const text = await res.text();
    let data = null;
    try {
        data = text ? JSON.parse(text) : null;
    } catch (error) {
        data = { message: text };
    }
    if (!res.ok) {
        const err = new Error(data?.message || `HTTP ${res.status}`);
        err.status = res.status;
        err.payload = data;
        throw err;
    }
    return data;
}

async function getJson(path) {
    const res = await fetch(`${API_ROOT}${path}`);
    return parseResponse(res);
}

async function postJson(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return parseResponse(res);
}

function submitAttachmentForm(path, body) {
    return new Promise((resolve, reject) => {
        const frameName = `layer3-download-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const frame = document.createElement('iframe');
        frame.name = frameName;
        frame.hidden = true;

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `${API_ROOT}${path}`;
        form.enctype = 'application/x-www-form-urlencoded';
        form.target = frameName;
        form.hidden = true;

        Object.entries(body).forEach(([key, value]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = JSON.stringify(value);
            form.appendChild(input);
        });

        let submitted = false;
        let settled = false;
        const cleanup = () => {
            window.setTimeout(() => {
                form.remove();
                frame.remove();
            }, 15000);
        };
        const settle = (handler, value) => {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            cleanup();
            handler(value);
        };
        const submittedResult = {
            state: 'external_export_download_delivery_submitted',
            schemaId: 'layer3.external_export_download_delivery.v1',
            filename: 'browser-managed attachment',
            sourceArtifactHash: body.source_artifact_hash || null,
            externalExportDownloadRecordRef: body.external_export_download_record_ref || null,
        };
        const timer = window.setTimeout(() => {
            settle(resolve, submittedResult);
        }, 5000);

        frame.addEventListener('load', () => {
            if (!submitted || settled) return;
            const text = frame.contentDocument?.body?.textContent?.trim();
            if (!text) {
                settle(resolve, submittedResult);
                return;
            }
            try {
                const payload = JSON.parse(text);
                settle(reject, Object.assign(new Error(payload.message || 'External delivery request failed.'), { payload }));
            } catch (_error) {
                settle(reject, new Error(text));
            }
        });

        document.body.appendChild(frame);
        document.body.appendChild(form);
        submitted = true;
        form.submit();
    });
}

function addEvent(message) {
    State.events.unshift({
        at: new Date().toLocaleTimeString(),
        message,
    });
    State.events = State.events.slice(0, 10);
    renderEvents();
}

function renderEvents() {
    elements.eventList.innerHTML = State.events
        .map((event) => `<li><strong>${escapeHtml(event.at)}</strong> ${escapeHtml(event.message)}</li>`)
        .join('');
}

function renderUnavailable(labels) {
    const values = labels?.length ? labels : ['plan', 'execution', 'results', 'package'];
    elements.unavailableList.innerHTML = values
        .map((label) => `<li>${escapeHtml(label.replace(/_/g, ' '))}</li>`)
        .join('');
}

function currentAuthorityRail() {
    return State.externalExportDownloadPrepare?.authority_rail || State.apsHandoffDispatch?.authority_rail || State.handoffExportPrepare?.authority_rail || State.replacementPackageNamespace?.authority_rail || State.replacementPackageArtifactManifest?.authority_rail || State.packageSupersessionCommit?.authority_rail || State.replacementPackageSetAuthority?.authority_rail || State.replacementPackageArtifactMaterialization?.authority_rail || State.sourceDirectoryPackageSupersessionPreview?.authority_rail || State.packageSupersessionPreview?.authority_rail || State.packageReviewSubmit?.authority_rail || State.packageConstruction?.authority_rail || State.packageReviewPreview?.authority_rail
        || State.sessionSummary?.authority_rail || State.resultReview?.authority_rail || State.resultStatus?.authority_rail
        || State.executionStart?.authority_rail || State.executionSelection?.authority_rail
        || State.planApproval?.authority_rail || State.planRevision?.authority_rail || State.planPreview?.authority_rail || State.gateC?.authority_rail || State.gateB?.authority_rail
        || State.materialPreview?.authority_rail || State.sourcePreview?.authority_rail || State.preflight?.authority_rail
        || State.bootstrap?.authority_rail;
}

function currentDownstreamUnavailable() {
    const external = externalExportDownloadPrepareState();
    if (
        external?.downstream_unavailable
        && (
            State.externalExportDownloadPrepare
            || external.available === true
            || externalExportDownloadStateName(external) === 'external_export_download_ready'
            || recordedExternalExportDownloadPrepare()
        )
    ) {
        return external.downstream_unavailable;
    }
    return State.apsHandoffDispatch?.downstream_unavailable
        || State.sessionSummary?.server_owned_local_outbox_write?.downstream_unavailable
        || State.sessionSummary?.server_owned_local_outbox_target?.downstream_unavailable
        || State.sessionSummary?.connector_local_destination_receipt?.downstream_unavailable
        || State.sessionSummary?.aps_handoff_dispatch?.downstream_unavailable
        || State.handoffExportPrepare?.downstream_unavailable
        || State.replacementPackageNamespace?.downstream_unavailable
        || State.replacementPackageArtifactManifest?.downstream_unavailable
        || State.packageSupersessionCommit?.downstream_unavailable
        || State.replacementPackageSetAuthority?.downstream_unavailable
        || State.replacementPackageArtifactMaterialization?.downstream_unavailable
        || State.sourceDirectoryPackageSupersessionPreview?.downstream_unavailable
        || State.packageSupersessionPreview?.downstream_unavailable
        || State.packageReviewSubmit?.downstream_unavailable
        || State.packageConstruction?.downstream_unavailable
        || State.packageReviewPreview?.downstream_unavailable
        || State.resultReview?.downstream_unavailable
        || State.resultStatus?.downstream_unavailable
        || State.executionStart?.downstream_unavailable
        || State.executionSelection?.downstream_unavailable
        || State.sessionSummary?.downstream_unavailable
        || State.sessionSummary?.handoff_export_prepare?.downstream_unavailable
        || State.sessionSummary?.package_review_submit?.downstream_unavailable
        || State.sessionSummary?.package_construction?.downstream_unavailable
        || State.sessionSummary?.package_review_preview?.downstream_unavailable
        || State.sessionSummary?.execution_result_review?.downstream_unavailable
        || State.sessionSummary?.analysis_execution_start?.downstream_unavailable
        || currentAuthorityRail()?.downstream_unavailable
        || State.bootstrap?.unavailable_gate_labels;
}

function renderContext() {
    const context = {
        route: State.bootstrap?.route || '/review/layer3',
        api_root: State.bootstrap?.api_root || API_ROOT,
        preflight_id: State.preflight?.preflight_id || 'none',
        source_set_id: State.sourcePreview?.source_set_id || 'none',
        material_preview_id: State.materialPreview?.material_preview_id || 'none',
        session_id: currentSessionId() || 'none',
        plan_preview_id: State.sessionSummary?.execution_selection?.source_preview_id || State.planPreview?.preview_id || 'none',
        analysis_plan_id: State.sessionSummary?.execution_selection?.analysis_plan_id || State.planApproval?.analysis_plan_id || 'none',
        plan_revision: State.planRevision?.next_state || 'none',
        pass_run_id: selectedResultAuthority()?.passRunId || State.resultStatus?.pass_run_id || 'none',
        result_status: State.resultStatus?.status || State.resultStatusError?.error_code || 'none',
        result_review: recordedResultReview()?.review_state || State.resultReview?.review_state || State.resultReviewError?.error_code || 'none',
        package_preview: State.packageReviewPreview?.next_state || State.packageReviewPreviewError?.error_code || State.sessionSummary?.package_review_preview?.state || 'none',
        package_construction: State.packageConstruction?.next_state || State.packageConstructionError?.error_code || State.sessionSummary?.package_construction?.state || 'none',
        package_review_submit: State.packageReviewSubmit?.next_state || State.packageReviewSubmitError?.error_code || State.sessionSummary?.package_review_submit?.state || 'none',
        package_supersession_preview: State.packageSupersessionPreview?.next_state || State.packageSupersessionPreviewError?.error_code || 'none',
        source_directory_package_supersession_preview: State.sourceDirectoryPackageSupersessionPreview?.next_state || State.sourceDirectoryPackageSupersessionPreviewError?.error_code || 'none',
        replacement_package_set_authority: State.replacementPackageSetAuthority?.next_state || State.replacementPackageSetAuthorityError?.error_code || State.replacementPackageArtifactMaterialization?.next_state || State.replacementPackageArtifactMaterializationError?.error_code || 'none',
        package_supersession_commit: State.packageSupersessionCommit?.next_state || State.packageSupersessionCommitError?.error_code || 'none',
        replacement_package_artifact_manifest: State.replacementPackageArtifactManifest?.next_state || State.replacementPackageArtifactManifestError?.error_code || 'none',
        replacement_package_namespace: State.replacementPackageNamespace?.next_state || State.replacementPackageNamespaceError?.error_code || 'none',
        handoff_export_prepare: State.handoffExportPrepare?.next_state || State.handoffExportPrepareError?.error_code || State.sessionSummary?.handoff_export_prepare?.state || 'none',
        aps_handoff_dispatch: State.apsHandoffDispatch?.next_state || State.apsHandoffDispatchError?.error_code || State.sessionSummary?.aps_handoff_dispatch?.state || 'none',
        external_export_download: State.externalExportDownloadPrepare?.next_state || State.externalExportDownloadPrepareError?.error_code || State.sessionSummary?.external_export_download?.state || 'none',
        external_export_download_delivery: State.externalExportDownloadDelivery?.state || State.externalExportDownloadDeliveryError?.error_code || 'none',
        signed_reference: State.externalExportDownloadSignedReferenceUse?.state || State.externalExportDownloadSignedReference?.signed_reference_state || State.externalExportDownloadSignedReferenceError?.error_code || 'none',
        connector_local_destination_receipt: State.sessionSummary?.connector_local_destination_receipt?.state || 'none',
        server_owned_local_outbox_target: State.sessionSummary?.server_owned_local_outbox_target?.state || 'none',
        local_outbox_provider_private_handoff: State.sessionSummary?.local_outbox_provider_private_handoff?.state || 'none',
        provider_private_signed_url: State.providerPrivateSignedUrlRevoke?.provider_signed_url_state || State.providerPrivateSignedUrlStatus?.provider_signed_url_state || State.providerPrivateSignedUrlPrepare?.provider_signed_url_state || State.providerPrivateSignedUrlError?.error_code || 'none',
    };
    elements.contextList.innerHTML = Object.entries(context)
        .map(([key, value]) => `
            <div>
                <dt>${escapeHtml(key.replace(/_/g, ' '))}</dt>
                <dd>${escapeHtml(value)}</dd>
            </div>
        `)
        .join('');
}

function renderAuthority(rail) {
    const current = rail || currentAuthorityRail();
    if (!current) return;

    const items = {
        gate: current.current_gate,
        persistence: current.persistence_mode,
        session: current.session_id,
        sources: (current.source_authority?.source_classes || []).join(', ') || 'none',
        approved: current.approved_material_count,
        denied: current.denied_material_count,
        isolated: current.isolated_material_count,
        flagged: current.flagged_material_count,
        typing: current.typing_status,
    };
    elements.authorityRail.innerHTML = Object.entries(items)
        .map(([label, value]) => `
            <div class="rail-item">
                <span class="rail-label">${escapeHtml(label)}</span>
                <span class="rail-value">${escapeHtml(value)}</span>
            </div>
        `)
        .join('');
}

function selectedSourceClasses() {
    return Array.from(document.querySelectorAll('input[name="source-class"]:checked'))
        .map((input) => input.value);
}

function parseDatasetVersionIds(value) {
    const result = [];
    String(value || '')
        .split(/[\s,;]+/)
        .map((item) => item.trim())
        .filter(Boolean)
        .forEach((item) => {
            if (!result.includes(item)) result.push(item);
        });
    return result;
}

function parseApsContentDocumentIds(value) {
    return parseDatasetVersionIds(value);
}

function checkedDatasetVersionCandidateIds() {
    return Array.from(document.querySelectorAll('input[name="dataset-version-candidate"]:checked'))
        .map((input) => input.value)
        .filter(Boolean);
}

function checkedApsContentDocumentCandidateIds() {
    return Array.from(document.querySelectorAll('input[name="aps-content-document-candidate"]:checked'))
        .map((input) => input.value)
        .filter(Boolean);
}

function selectedDatasetVersionIds() {
    const result = [];
    [...checkedDatasetVersionCandidateIds(), ...parseDatasetVersionIds(elements.datasetVersionIds?.value)]
        .forEach((item) => {
            if (!result.includes(item)) result.push(item);
        });
    return result;
}

function selectedApsContentDocumentIds() {
    const result = [];
    [...checkedApsContentDocumentCandidateIds(), ...parseApsContentDocumentIds(elements.apsContentDocumentIds?.value)]
        .forEach((item) => {
            if (!result.includes(item)) result.push(item);
        });
    return result;
}

function selectedRawMixedSourceClasses() {
    return selectedSourceClasses()
        .filter((sourceClass) => RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES.has(sourceClass));
}

function rawMixedMaterializationFormState() {
    return {
        corpusBatchId: elements.rawMixedCorpusBatchId?.value?.trim() || '',
        manifestRef: elements.rawMixedManifestRef?.value?.trim() || '',
        manifestHash: elements.rawMixedManifestHash?.value?.trim() || '',
        operatorConfirmed: Boolean(elements.rawMixedOperatorConfirmation?.checked),
        requestedSourceClasses: selectedRawMixedSourceClasses(),
    };
}

function canMaterializeRawMixed() {
    const form = rawMixedMaterializationFormState();
    return Boolean(
        form.corpusBatchId
        && form.manifestRef
        && form.manifestHash
        && form.operatorConfirmed
        && form.requestedSourceClasses.length === RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES.size
        && !State.rawMixedMaterializationPending
    );
}

function rawMixedMaterializationPayload() {
    const form = rawMixedMaterializationFormState();
    return {
        schema_id: RAW_MIXED_MATERIALIZE_REQUEST_SCHEMA_ID,
        schema_version: 1,
        client_request_id: requestId(),
        materialization_mode: RAW_MIXED_MATERIALIZE_MODE,
        corpus_batch_id: form.corpusBatchId,
        artifact_manifest_ref: form.manifestRef,
        artifact_manifest_hash: form.manifestHash,
        requested_source_classes: form.requestedSourceClasses,
        operator_confirmation: true,
    };
}

function candidateIdsForMaterialization(kind) {
    if (kind === 'dataset_version') {
        return new Set((State.datasetVersionCandidates?.dataset_version_candidates || [])
            .map((candidate) => String(candidate.dataset_version_id || ''))
            .filter(Boolean));
    }
    return new Set((State.apsContentDocumentCandidates?.aps_content_document_candidates || [])
        .map((candidate) => String(candidate.content_id || ''))
        .filter(Boolean));
}

function materializedSourceIdsVisible(materialization) {
    const datasetIds = materialization?.dataset_version_ids || [];
    const contentIds = materialization?.aps_content_document_ids || [];
    const datasetCandidates = candidateIdsForMaterialization('dataset_version');
    const contentCandidates = candidateIdsForMaterialization('aps_content_document');
    return datasetIds.every((id) => datasetCandidates.has(String(id)))
        && contentIds.every((id) => contentCandidates.has(String(id)));
}

function applyMaterializedSourceIds(materialization) {
    const datasetIds = materialization?.dataset_version_ids || [];
    const contentIds = materialization?.aps_content_document_ids || [];
    clearMaterializedSourceSelection();
    if (elements.datasetVersionIds) {
        elements.datasetVersionIds.value = datasetIds.join('\n');
    }
    if (elements.apsContentDocumentIds) {
        elements.apsContentDocumentIds.value = contentIds.join('\n');
    }
}

function clearMaterializedSourceSelection() {
    document.querySelectorAll('input[name="dataset-version-candidate"]:checked')
        .forEach((input) => { input.checked = false; });
    document.querySelectorAll('input[name="aps-content-document-candidate"]:checked')
        .forEach((input) => { input.checked = false; });
    if (elements.datasetVersionIds) {
        elements.datasetVersionIds.value = '';
    }
    if (elements.apsContentDocumentIds) {
        elements.apsContentDocumentIds.value = '';
    }
}

function clearRawMixedMaterializationState({ clearAppliedSources = false } = {}) {
    const hadMaterialization = Boolean(State.rawMixedMaterialization);
    State.rawMixedMaterialization = null;
    State.rawMixedMaterializationError = null;
    if (clearAppliedSources && hadMaterialization) {
        clearMaterializedSourceSelection();
        clearLayer3FlowStateForSourceChange();
    }
}

function handleRawMixedMaterializationInputChange() {
    clearRawMixedMaterializationState({ clearAppliedSources: true });
    renderAll();
}

function preventRawMixedManifestEnterSubmit(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
    }
}

function clearLayer3FlowStateForSourceChange() {
    State.preflight = null;
    State.sourcePreview = null;
    State.materialPreview = null;
    State.gateB = null;
    State.gateC = null;
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    clearGateBDraftSnapshot();
    clearResultReviewState();
    clearSessionRecoveryAnchor();
}

function selectedSourceClassLabels() {
    const labels = Array.from(document.querySelectorAll('input[name="source-class"]'))
        .filter((input) => input.checked)
        .map((input) => input.closest('label')?.textContent || input.value)
        .map((label) => label.replace(/\s+/g, ' ').trim())
        .filter(Boolean);
    const datasetVersionIds = selectedDatasetVersionIds();
    if (datasetVersionIds.length) {
        labels.push(`${datasetVersionIds.length} APS-derived DatasetVersion ID${datasetVersionIds.length === 1 ? '' : 's'}`);
    }
    const apsContentDocumentIds = selectedApsContentDocumentIds();
    if (apsContentDocumentIds.length) {
        labels.push(`${apsContentDocumentIds.length} APS content document ID${apsContentDocumentIds.length === 1 ? '' : 's'}`);
    }
    return labels;
}

function currentIntentText() {
    const intent = elements.intentInput?.value?.trim();
    return intent || 'No operator intent has been entered yet.';
}

function requestId() {
    if (window.crypto?.randomUUID) {
        return window.crypto.randomUUID();
    }
    return `browser-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function currentSessionId() {
    return State.sessionSummary?.session_id
        || State.gateB?.session_id
        || State.planApproval?.session_id
        || State.planPreview?.session_id
        || State.gateC?.session_id
        || null;
}

function storageGet(storage, key) {
    try {
        const raw = storage?.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch (_error) {
        return null;
    }
}

function storageSet(storage, key, value) {
    try {
        storage?.setItem(key, JSON.stringify(value));
        return true;
    } catch (_error) {
        return false;
    }
}

function storageRemove(storage, key) {
    try {
        storage?.removeItem(key);
    } catch (_error) {
        // Browser storage can be unavailable in private or locked-down contexts.
    }
}

function stateActionContractSchemaId(source = null) {
    return source?.state_action_contract?.schema_id || State.bootstrap?.state_action_contract?.schema_id || null;
}

function sortedStringList(values) {
    return Array.isArray(values) ? values.map(String).sort() : [];
}

function stableStringify(value) {
    if (Array.isArray(value)) {
        return `[${value.map((item) => stableStringify(item)).join(',')}]`;
    }
    if (value && typeof value === 'object') {
        return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
    }
    return JSON.stringify(value ?? null);
}

function stableHashAvailable() {
    return Boolean(window.crypto?.subtle && window.TextEncoder);
}

async function stableHash(value) {
    if (!stableHashAvailable()) {
        throw new Error('browser_sha256_unavailable');
    }
    const data = new TextEncoder().encode(stableStringify(value));
    const digest = await window.crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(digest))
        .map((byte) => byte.toString(16).padStart(2, '0'))
        .join('');
}

function capabilitySignatureItems(values) {
    return (Array.isArray(values) ? values : [])
        .map((item) => ({
            admitted: item?.admitted ?? null,
            blocked_downstream: sortedStringList(item?.blocked_downstream),
            capability: item?.capability || null,
            owner_service: item?.owner_service || null,
            reason: item?.reason || null,
            source_gate: item?.source_gate || null,
        }))
        .sort((left, right) => String(left.capability).localeCompare(String(right.capability)));
}

function stateActionMatrixSignatureItems(values) {
    return (Array.isArray(values) ? values : [])
        .map((item) => ({
            allowed_next_actions: sortedStringList(item?.allowed_next_actions),
            authority_source: item?.authority_source || null,
            forbidden_downstream_actions: sortedStringList(item?.forbidden_downstream_actions),
            state: item?.state || null,
        }))
        .sort((left, right) => String(left.state).localeCompare(String(right.state)));
}

function decisionSetSignatureItems(value) {
    const decisions = value && typeof value === 'object' ? value : {};
    return Object.fromEntries(
        Object.keys(decisions).sort().map((key) => [key, sortedStringList(decisions[key])]),
    );
}

function stateActionContractSignature(source = null) {
    const contract = source?.state_action_contract || State.bootstrap?.state_action_contract || null;
    if (!contract?.schema_id) return null;
    return stableStringify({
        action_ids: sortedStringList(contract.action_ids),
        admitted_capabilities: capabilitySignatureItems(contract.admitted_capabilities),
        decision_sets: decisionSetSignatureItems(contract.decision_sets),
        deferred_capabilities: capabilitySignatureItems(contract.deferred_capabilities),
        schema_id: contract.schema_id,
        schema_version: contract.schema_version ?? null,
        state_action_matrix: stateActionMatrixSignatureItems(contract.state_action_matrix),
        state_count: contract.state_count ?? null,
        state_model_schema_id: contract.state_model_schema_id || null,
        states: sortedStringList(contract.states),
    });
}

function authorityMatrixContract() {
    const contract = State.bootstrap?.authority_matrix_contract;
    if (!contract || typeof contract !== 'object') return null;
    if (contract.schema_id !== 'layer3.authority_matrix_contract.v1') return null;
    if (!Array.isArray(contract.authority_matrix)) return null;
    return contract;
}

function authorityMatrixReviewState(contract) {
    if (!State.bootstrap) return { label: 'authority_matrix_bootstrap_pending', pill: 'preview' };
    if (!contract) return { label: 'authority_matrix_bootstrap_contract_unavailable', pill: 'blocked' };
    if (contract.fail_closed_result === 'blocked_no_runtime_authority') {
        return { label: 'authority_matrix_fail_closed_read_only', pill: 'ok' };
    }
    return { label: 'authority_matrix_read_only_contract_loaded', pill: 'preview' };
}

function authorityMatrixRowCards(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.row || 'unknown_authority_row')}</code>
                ${row.admission_result ? `<span>${escapeHtml(row.admission_result)}</span>` : ''}
                ${row.next_allowed_action ? `<span>${escapeHtml(row.next_allowed_action)}</span>` : ''}
                ${Array.isArray(row.blocked_scope) && row.blocked_scope.length ? `<span>${escapeHtml(row.blocked_scope.join(', '))}</span>` : ''}
            </li>
        `).join('')
        : '<li>No authority matrix rows are exposed by bootstrap.</li>';
}

function sameStringList(left, right) {
    const leftValues = [...(left || [])].map(String).sort();
    const rightValues = [...(right || [])].map(String).sort();
    return leftValues.length === rightValues.length && leftValues.every((value, index) => value === rightValues[index]);
}

function materialPreviewCandidateIds(preview = State.materialPreview) {
    return (preview?.material_candidates || [])
        .map((candidate) => candidate.candidate_id)
        .filter(Boolean)
        .sort();
}

function isTypingCommitted() {
    return Boolean(
        State.gateC?.authority_rail?.typing_status === 'committed'
        || State.sessionSummary?.gate_c_summary?.typing_committed === true
    );
}

function persistSessionRecoveryAnchor(source) {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    const anchor = {
        schema_id: LAYER3_SESSION_RECOVERY_SCHEMA_ID,
        schema_version: 1,
        session_id: sessionId,
        selection_manifest_id: State.sessionSummary?.selection_manifest_id || State.gateB?.selection_manifest_id || null,
        current_gate: State.sessionSummary?.current_gate || currentAuthorityRail()?.current_gate || null,
        state_action_contract_schema_id: stateActionContractSchemaId(State.sessionSummary),
        state_action_contract_signature: stateActionContractSignature(State.sessionSummary),
        source,
        updated_at: new Date().toISOString(),
    };
    storageSet(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY, anchor);
}

function clearSessionRecoveryAnchor() {
    storageRemove(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
}

function loadSessionRecoveryAnchor() {
    const anchor = storageGet(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
    if (!anchor || anchor.schema_id !== LAYER3_SESSION_RECOVERY_SCHEMA_ID || !anchor.session_id) {
        storageRemove(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
        return null;
    }
    const currentContract = stateActionContractSignature();
    if (
        currentContract
        && anchor.state_action_contract_signature !== currentContract
    ) {
        storageRemove(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
        addEvent('Stored session recovery anchor skipped after contract change.');
        return null;
    }
    return anchor;
}

async function recoverSessionFromStorage() {
    const anchor = loadSessionRecoveryAnchor();
    if (!anchor) return false;
    try {
        const summary = await getJson(`/session/${encodeURIComponent(anchor.session_id)}`);
        const currentContract = stateActionContractSignature();
        const summaryContract = stateActionContractSignature(summary);
        if (currentContract && summaryContract && currentContract !== summaryContract) {
            clearSessionRecoveryAnchor();
            addEvent('Stored session recovery anchor no longer matches the server contract.');
            return false;
        }
        State.sessionSummary = summary;
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.replacementPackageArtifactMaterializationError = null;
        State.replacementPackageSetAuthorityError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        State.externalExportDownloadSignedReferenceError = null;
        clearGateBDraftSnapshot();
        persistSessionRecoveryAnchor('session_recovery');
        addEvent(`Session ${summary.session_id} restored from server state.`);
        return true;
    } catch (error) {
        clearSessionRecoveryAnchor();
        addEvent(`Stored session recovery anchor cleared: ${error.message}`);
        return false;
    }
}

function gateBDraftExpiresAt() {
    return new Date(Date.now() + GATE_B_DRAFT_TTL_MS).toISOString();
}

function gateBDraftExpired(draft) {
    const expiresAt = Date.parse(draft?.expires_at || '');
    return Number.isFinite(expiresAt) && expiresAt <= Date.now();
}

function currentGateBDraftIdentity() {
    return {
        preflight_id: State.preflight?.preflight_id || null,
        source_set_id: State.sourcePreview?.source_set_id || null,
        material_preview_id: State.materialPreview?.material_preview_id || null,
        material_preview_hash: State.materialPreview?.material_preview_hash || null,
        candidate_ids: materialPreviewCandidateIds(),
    };
}

function gateBDraftMatchesCurrentPreview(draft) {
    const current = currentGateBDraftIdentity();
    return Boolean(
        draft?.material_preview_id
        && current.material_preview_id
        && draft.material_preview_id === current.material_preview_id
        && draft.material_preview_hash === current.material_preview_hash
        && sameStringList(draft.candidate_ids, current.candidate_ids)
    );
}

function buildGateBDraftSnapshot() {
    if (!(State.materialPreview?.material_candidates || []).length) return null;
    const clientRequestId = State.gateBClientRequestId || requestId();
    State.gateBClientRequestId = clientRequestId;
    return {
        schema_id: LAYER3_GATE_B_DRAFT_SCHEMA_ID,
        schema_version: 1,
        draft_authority: 'browser_restore_only_server_revalidated_on_commit',
        client_request_id: clientRequestId,
        state_action_contract_schema_id: stateActionContractSchemaId(),
        state_action_contract_signature: stateActionContractSignature(),
        expires_at: gateBDraftExpiresAt(),
        ...currentGateBDraftIdentity(),
        preflight: State.preflight,
        source_preview: State.sourcePreview,
        material_preview: State.materialPreview,
        gate_b_decisions: State.gateBDecisions,
    };
}

function persistGateBDraftSnapshot() {
    const snapshot = buildGateBDraftSnapshot();
    if (!snapshot) return;
    storageSet(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY, snapshot);
}

function clearGateBDraftSnapshot() {
    State.gateBClientRequestId = null;
    storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
}

function restoreGateBDraftSnapshot() {
    if (currentSessionId()) return false;
    const draft = storageGet(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
    if (!draft || draft.schema_id !== LAYER3_GATE_B_DRAFT_SCHEMA_ID || gateBDraftExpired(draft)) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        return false;
    }
    const currentContract = stateActionContractSignature();
    if (
        currentContract
        && draft.state_action_contract_signature !== currentContract
    ) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        addEvent('Gate B draft skipped after contract change.');
        return false;
    }
    if (!draft.material_preview?.material_preview_id || !draft.material_preview?.material_preview_hash) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        return false;
    }
    if (State.materialPreview?.material_preview_id && !gateBDraftMatchesCurrentPreview(draft)) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        addEvent('Gate B draft skipped after material preview mismatch.');
        return false;
    }
    State.preflight = draft.preflight || null;
    State.sourcePreview = draft.source_preview || null;
    State.materialPreview = draft.material_preview;
    State.gateBDecisions = draft.gate_b_decisions || {};
    State.gateBClientRequestId = draft.client_request_id || requestId();
    addEvent('Gate B draft restored for server revalidation.');
    return true;
}

function gateBRequestId() {
    if (!State.gateBClientRequestId) {
        State.gateBClientRequestId = requestId();
        persistGateBDraftSnapshot();
    }
    return State.gateBClientRequestId;
}

function providerPrivateReceiptSnapshot(provider) {
    if (!provider?.provider_signed_url_receipt_id) return null;
    return {
        schema_id: LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID,
        schema_version: 1,
        recovery_authority: 'browser_receipt_handle_only_server_revalidated_on_status_or_revoke',
        provider_signed_url_receipt_id: provider.provider_signed_url_receipt_id,
        provider_signed_url_state: provider.provider_signed_url_state || null,
        source_artifact_hash: provider.source_artifact_hash || null,
        source_artifact_size_bytes: provider.source_artifact_size_bytes ?? null,
        updated_at: new Date().toISOString(),
    };
}

function persistProviderPrivateReceiptSnapshot(provider) {
    const snapshot = providerPrivateReceiptSnapshot(provider);
    if (!snapshot) return;
    State.providerPrivateSignedUrlReceiptRecovery = snapshot;
    storageSet(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY, snapshot);
}

function restoreProviderPrivateReceiptSnapshot() {
    const snapshot = storageGet(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY);
    if (!snapshot || snapshot.schema_id !== LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID || !snapshot.provider_signed_url_receipt_id) {
        storageRemove(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY);
        return false;
    }
    State.providerPrivateSignedUrlReceiptRecovery = snapshot;
    addEvent('Provider-private signed URL receipt handle restored for server revalidation.');
    return true;
}

function providerPrivateSignedUrlPrepareRequestId() {
    if (!State.providerPrivateSignedUrlPrepareClientRequestId) {
        State.providerPrivateSignedUrlPrepareClientRequestId = requestId();
    }
    return State.providerPrivateSignedUrlPrepareClientRequestId;
}

function clearExternalExportDownloadPrepareState() {
    State.externalExportDownloadPrepare = null;
    State.externalExportDownloadPrepareError = null;
    State.externalExportDownloadPreparePending = false;
    clearExternalExportDownloadDeliveryState();
}

function clearExternalExportDownloadDeliveryState() {
    State.externalExportDownloadDelivery = null;
    State.externalExportDownloadDeliveryError = null;
    State.externalExportDownloadDeliveryPending = false;
    State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus = null;
    State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusError = null;
    State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusPending = false;
    clearExternalExportDownloadSignedReferenceState();
}

function clearExternalExportDownloadSignedReferenceState() {
    State.externalExportDownloadSignedReference = null;
    State.externalExportDownloadSignedReferenceError = null;
    State.externalExportDownloadSignedReferencePending = false;
    State.externalExportDownloadSignedReferenceUse = null;
    State.externalExportDownloadSignedReferenceUsePending = false;
    clearProviderPrivateSignedUrlState();
}

function clearProviderPrivateSignedUrlState() {
    State.providerPrivateSignedUrlPrepare = null;
    State.providerPrivateSignedUrlStatus = null;
    State.providerPrivateSignedUrlRevoke = null;
    State.providerPrivateSignedUrlReceiptRecovery = null;
    State.providerPrivateSignedUrlPrepareClientRequestId = null;
    State.providerPrivateSignedUrlError = null;
    State.providerPrivateSignedUrlPending = false;
    clearProviderPublicUrlState();
    storageRemove(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY);
}

function clearProviderPublicUrlState() {
    State.providerPublicUrlPrepare = null;
    State.providerPublicUrlStatus = null;
    State.providerPublicUrlUse = null;
    State.providerPublicUrlRevoke = null;
    State.providerPublicUrlPrepareClientRequestId = null;
    State.providerPublicUrlError = null;
    State.providerPublicUrlPending = false;
}

function clearResultReviewState({ keepSummary = false } = {}) {
    if (!keepSummary) {
        State.sessionSummary = null;
    }
    State.executionSelection = null;
    State.executionSelectionError = null;
    State.executionSelectionPending = false;
    State.executionStart = null;
    State.executionStartError = null;
    State.executionStartPending = false;
    State.resultStatus = null;
    State.resultStatusError = null;
    State.resultReview = null;
    State.resultReviewError = null;
    State.resultReviewPending = false;
    State.packageReviewPreview = null;
    State.packageReviewPreviewError = null;
    State.packageReviewPreviewPending = false;
    State.packageConstruction = null;
    State.packageConstructionError = null;
    State.packageConstructionPending = false;
    State.packageReviewSubmit = null;
    State.packageReviewSubmitError = null;
    State.packageReviewSubmitPending = false;
    State.packageSupersessionPreview = null;
    State.packageSupersessionPreviewError = null;
    State.packageSupersessionPreviewPending = false;
    clearSourceDirectoryPackageSupersessionPreviewState();
    clearReplacementPackageSetAuthorityState();
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.handoffExportPreparePending = false;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    State.apsHandoffDispatchPending = false;
    clearExternalExportDownloadPrepareState();
}

function selectedResultAuthority() {
    const summary = State.sessionSummary || {};
    const selection = State.executionSelection || summary.execution_selection || {};
    const startState = State.executionStart || summary.analysis_execution_start || {};
    const statusBody = State.resultStatus || {};
    const reviewBody = State.resultReview || {};
    const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
    const firstPassRunId = passRunIds[0] || startState.pass_run_id || statusBody.pass_run_id || reviewBody.pass_run_id || null;
    const passRunStatuses = selection.pass_run_statuses || {};
    const passStatus = statusBody.pass_run_status || startState.pass_run_status || passRunStatuses[firstPassRunId] || null;
    const analysisRunIds = Array.isArray(selection.analysis_run_ids) ? selection.analysis_run_ids : [];
    const analysisRunId = statusBody.analysis_run_id || startState.analysis_run_id || analysisRunIds[0] || reviewBody.analysis_run_id || null;
    const previewIdentity = statusBody.preview_identity || startState.preview_identity || selection.preview_identity || reviewBody.preview_identity || {};
    const previewId = selection.source_preview_id || startState.source_preview_id || previewIdentity.preview_id || State.planPreview?.preview_id || null;
    const previewHash = selection.source_preview_hash || startState.source_preview_hash || previewIdentity.preview_hash || State.planPreview?.preview_hash || null;
    const analysisPlanId = selection.analysis_plan_id || startState.analysis_plan_id || statusBody.analysis_plan_id || reviewBody.analysis_plan_id || State.planApproval?.analysis_plan_id || null;
    return {
        sessionId: summary.session_id || currentSessionId(),
        analysisPlanId,
        passRunId: firstPassRunId,
        previewId,
        previewHash,
        analysisRunId,
        passStatus,
        selected: Boolean((selection.selected === true || State.executionSelection?.schema_id) && firstPassRunId),
        terminal: TERMINAL_PASS_STATUSES.has(passStatus),
        executionStarted: Boolean(selection.execution_started || startState.execution_started || startState.pass_run_id || statusBody.execution_started),
    };
}

function executionSelectionState() {
    return State.executionSelection || State.sessionSummary?.execution_selection || {};
}

function executionStartState() {
    return State.executionStart || State.sessionSummary?.analysis_execution_start || {};
}

function executionPlanAuthority() {
    const selection = executionSelectionState();
    const previewIdentity = selection.preview_identity || State.executionStart?.preview_identity || {};
    return {
        analysisPlanId: State.planApproval?.analysis_plan_id
            || selection.analysis_plan_id
            || State.sessionSummary?.plan_approval?.analysis_plan_id
            || null,
        previewId: State.planPreview?.preview_id
            || selection.source_preview_id
            || previewIdentity.preview_id
            || null,
        previewHash: State.planPreview?.preview_hash
            || selection.source_preview_hash
            || previewIdentity.preview_hash
            || null,
    };
}

function hasResultAuthorityIdentity(authority = selectedResultAuthority()) {
    return Boolean(
        authority.sessionId
        && authority.analysisPlanId
        && authority.passRunId
        && authority.previewId
        && authority.previewHash
    );
}

function recordedResultReview() {
    if (State.resultReview?.review_record_ref || State.resultReview?.review_state) {
        return State.resultReview;
    }
    const sessionReview = State.sessionSummary?.execution_result_review;
    if (sessionReview?.review_record_ref || sessionReview?.state) {
        return sessionReview;
    }
    return null;
}

function recordedApprovedResultReview() {
    const review = recordedResultReview();
    return review && review.review_state === 'execution_result_review_approved' && review.operator_decision === 'approved'
        ? review
        : null;
}

function arrayFromServer(value) {
    return Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && String(item).trim()) : [];
}

function nullIfBlank(value) {
    const normalized = String(value ?? '').trim();
    return normalized || null;
}

function selectedPassRunSummary(authority = selectedResultAuthority()) {
    const passRuns = Array.isArray(State.sessionSummary?.sublayer_visualization?.pass_runs)
        ? State.sessionSummary.sublayer_visualization.pass_runs
        : [];
    return passRuns.find((passRun) => passRun?.pass_run_id === authority.passRunId) || {};
}

function associatedCohortProjection(authority = selectedResultAuthority()) {
    const statusBody = State.resultStatus || {};
    const metadata = statusBody.output_metadata_summary || {};
    const reviewState = recordedResultReview() || {};
    const passRun = selectedPassRunSummary(authority);
    const traceSummary = State.resultReview?.trace_summary || reviewState.trace_summary || {};
    const sourceDatasetVersionIds = arrayFromServer(
        metadata.source_dataset_version_ids
        || traceSummary.source_dataset_version_ids
        || passRun.source_dataset_version_ids
        || passRun.source_dataset_version_ids_json
    );
    const passType = nullIfBlank(statusBody.pass_type || passRun.pass_type || metadata.pass_type || traceSummary.pass_type);
    const passScope = nullIfBlank(statusBody.pass_scope || passRun.pass_scope || metadata.pass_scope || traceSummary.pass_scope);
    const selectedMethod = nullIfBlank(
        statusBody.selected_method_name || passRun.selected_method_name || metadata.selected_method_name || traceSummary.selected_method_name
    );
    const requestedMethod = nullIfBlank(metadata.requested_method_name || traceSummary.requested_method_name || passRun.requested_method_name);
    const requestedMethodSource = nullIfBlank(
        metadata.requested_method_source || traceSummary.requested_method_source || passRun.requested_method_source
    );
    const sourceGate = nullIfBlank(metadata.source_gate || traceSummary.source_gate || passRun.source_gate);
    const cohortShape = nullIfBlank(metadata.cohort_shape || traceSummary.cohort_shape || passRun.cohort_shape);
    const outputPayloadRef = nullIfBlank(
        statusBody.output_payload_ref || metadata.output_payload_ref || traceSummary.output_payload_ref
    );
    const unresolvedTraceCount = Number(
        State.resultReview?.unresolved_trace_count
        ?? reviewState.unresolved_trace_count
        ?? statusBody.unresolved_trace_count
        ?? 0
    );
    const isAssociated = passType === ASSOCIATED_COHORT_PASS_TYPE
        || (
            passScope === ASSOCIATED_COHORT_PASS_SCOPE
            && sourceGate === ASSOCIATED_COHORT_SOURCE_GATE
            && cohortShape === ASSOCIATED_COHORT_SHAPE
        );
    const ready = Boolean(
        isAssociated
        && hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && statusBody.result_status_available === true
        && metadata.readable === true
        && passType === ASSOCIATED_COHORT_PASS_TYPE
        && passScope === ASSOCIATED_COHORT_PASS_SCOPE
        && selectedMethod === ASSOCIATED_COHORT_METHOD
        && requestedMethod === ASSOCIATED_COHORT_METHOD
        && requestedMethodSource === ASSOCIATED_COHORT_METHOD_SOURCE
        && sourceGate === ASSOCIATED_COHORT_SOURCE_GATE
        && cohortShape === ASSOCIATED_COHORT_SHAPE
        && sourceDatasetVersionIds.length > 0
        && outputPayloadRef
        && unresolvedTraceCount === 0
    );
    return {
        isAssociated,
        ready,
        passType,
        passScope,
        selectedMethod,
        requestedMethod,
        requestedMethodSource,
        sourceGate,
        cohortShape,
        sourceDatasetVersionIds,
        outputPayloadRef,
        unresolvedTraceCount,
    };
}

function associatedCohortReviewedOutputItems(authority = selectedResultAuthority()) {
    const projection = associatedCohortProjection(authority);
    if (!projection.ready) return [];
    const trace = {
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        output_payload_ref: projection.outputPayloadRef,
    };
    if (authority.analysisRunId) {
        trace.analysis_run_id = authority.analysisRunId;
    }
    return [
        {
            item_ref: projection.outputPayloadRef,
            item_type: 'finding',
            trace,
        },
    ];
}

function associatedCohortReviewContext() {
    return associatedCohortProjection().isAssociated;
}

function canRefreshSessionSummary() {
    return Boolean(
        currentSessionId()
        && !State.executionSelectionPending
        && !State.executionStartPending
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canInspectResultStatus() {
    const authority = selectedResultAuthority();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && !State.executionSelectionPending
        && !State.executionStartPending
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function reviewDecisionNeedsNotes() {
    return RESULT_REVIEW_DECISIONS_REQUIRING_NOTES.has(elements.resultReviewDecision.value);
}

function canSubmitResultReview() {
    const authority = selectedResultAuthority();
    const notes = elements.resultReviewNotes.value.trim();
    const cohort = associatedCohortProjection(authority);
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.resultStatus?.result_status_available === true
        && !recordedResultReview()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && (!reviewDecisionNeedsNotes() || notes)
        && (!cohort.isAssociated || cohort.ready)
    );
}

function canInspectPackageReviewPreview() {
    const authority = selectedResultAuthority();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && recordedApprovedResultReview()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function packageConstructionState() {
    return State.packageConstruction || State.sessionSummary?.package_construction || null;
}

function packageReviewSubmitState() {
    if (State.packageReviewSubmit) {
        return State.packageReviewSubmit;
    }
    const summarySubmit = State.sessionSummary?.package_review_submit;
    if (summarySubmit?.package_review_state || summarySubmit?.submit_record_ref) {
        return summarySubmit;
    }
    const construction = State.packageConstruction;
    if (construction?.package_review_submit_enabled === true) {
        const outputPackageIds = Array.isArray(construction.output_package_ids)
            ? construction.output_package_ids
            : (Array.isArray(construction.output_packages)
                ? construction.output_packages.map((item) => item.output_package_id).filter(Boolean)
                : []);
        return {
            schema_id: 'layer3.package_review_submit_state.v1',
            available: true,
            state: 'package_review_submit_ready',
            reconciliation_record_id: construction.reconciliation_record_id,
            output_package_ids: outputPackageIds,
            package_kinds: construction.package_kinds,
            payload_refs: construction.payload_refs,
            payload_hashes: construction.payload_hashes,
            construction_basis_hash: construction.construction_basis_hash,
            package_review_preview_hash: construction.package_review_preview_hash,
            result_review_record_ref: construction.result_review_record_ref,
            package_construction_source_gate: construction.package_construction_source_gate,
            pass_type: construction.pass_type,
            pass_scope: construction.pass_scope,
            method: construction.method,
            source_gate: construction.source_gate,
            source_shape: construction.source_shape,
            package_review_submit_enabled: true,
            handoff_enabled: false,
            export_enabled: false,
            downstream_unavailable: construction.downstream_unavailable,
        };
    }
    if (summarySubmit) {
        return summarySubmit;
    }
    return null;
}

function packageReviewPreviewHash() {
    const preview = State.packageReviewPreview || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return preview.package_review_preview_hash
        || submit.package_review_preview_hash
        || construction.package_review_preview_hash
        || null;
}

function packageConstructionBasisHash() {
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return submit.construction_basis_hash || construction.construction_basis_hash || null;
}

function isQualitativeApsPackageSubmitState(
    submit = packageReviewSubmitState() || {},
    construction = packageConstructionState() || {},
) {
    return Boolean(
        submit.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE
        || construction.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE
        || submit.pass_scope === QUAL_APS_PASS_SCOPE
        || construction.pass_scope === QUAL_APS_PASS_SCOPE
        || submit.source_shape === QUAL_APS_SOURCE_SHAPE
        || construction.source_shape === QUAL_APS_SOURCE_SHAPE
    );
}

function packageOutputPackageIds() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.output_package_ids) && handoff.output_package_ids.length) {
        return handoff.output_package_ids;
    }
    if (Array.isArray(submit.output_package_ids) && submit.output_package_ids.length) {
        return submit.output_package_ids;
    }
    if (Array.isArray(construction.output_package_ids) && construction.output_package_ids.length) {
        return construction.output_package_ids;
    }
    if (Array.isArray(construction.output_packages)) {
        return construction.output_packages.map((item) => item.output_package_id).filter(Boolean);
    }
    return [];
}

function packagePayloadHashes() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.payload_hashes) && handoff.payload_hashes.length) {
        return handoff.payload_hashes;
    }
    if (Array.isArray(submit.payload_hashes) && submit.payload_hashes.length) {
        return submit.payload_hashes;
    }
    if (Array.isArray(construction.payload_hashes) && construction.payload_hashes.length) {
        return construction.payload_hashes;
    }
    if (Array.isArray(construction.output_packages)) {
        return construction.output_packages.map((item) => item.payload_hash).filter(Boolean);
    }
    return [];
}

function packagePayloadRefs() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.payload_refs) && handoff.payload_refs.length) {
        return handoff.payload_refs;
    }
    if (Array.isArray(submit.payload_refs) && submit.payload_refs.length) {
        return submit.payload_refs;
    }
    if (Array.isArray(construction.payload_refs) && construction.payload_refs.length) {
        return construction.payload_refs;
    }
    if (Array.isArray(construction.output_packages)) {
        return construction.output_packages.map((item) => item.payload_ref).filter(Boolean);
    }
    return [];
}

function packageKindsFromState() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.package_kinds) && handoff.package_kinds.length) {
        return handoff.package_kinds;
    }
    if (Array.isArray(submit.package_kinds) && submit.package_kinds.length) {
        return submit.package_kinds;
    }
    if (Array.isArray(construction.package_kinds) && construction.package_kinds.length) {
        return construction.package_kinds;
    }
    const previewKinds = Array.isArray(State.packageReviewPreview?.candidate_package_kinds)
        ? State.packageReviewPreview.candidate_package_kinds.map((item) => item.package_kind).filter(Boolean)
        : [];
    return previewKinds.length ? previewKinds : PACKAGE_REVIEW_PACKAGE_KINDS;
}

function packageLifecycleOutputRows() {
    const construction = packageConstructionState() || {};
    const outputPackages = Array.isArray(construction.output_packages) ? construction.output_packages : [];
    const packageIds = packageOutputPackageIds();
    const payloadRefs = packagePayloadRefs();
    const payloadHashes = packagePayloadHashes();
    const previewKinds = Array.isArray(State.packageReviewPreview?.candidate_package_kinds)
        ? State.packageReviewPreview.candidate_package_kinds.map((item) => item.package_kind).filter(Boolean)
        : [];
    const constructionKinds = Array.isArray(construction.package_kinds) ? construction.package_kinds : [];
    const submit = packageReviewSubmitState() || {};
    const submitKinds = Array.isArray(submit.package_kinds) ? submit.package_kinds : [];
    const packageKinds = outputPackages.length || packageIds.length || payloadRefs.length || payloadHashes.length
        ? packageKindsFromState()
        : (previewKinds.length ? previewKinds : (constructionKinds.length ? constructionKinds : submitKinds));
    const rowCount = Math.max(
        outputPackages.length,
        packageIds.length,
        packageKinds.length,
        payloadRefs.length,
        payloadHashes.length,
    );
    return Array.from({ length: rowCount }, (_value, index) => ({
        package_kind: outputPackages[index]?.package_kind || packageKinds[index],
        output_package_id: outputPackages[index]?.output_package_id || packageIds[index],
        payload_ref: outputPackages[index]?.payload_ref || payloadRefs[index],
        payload_hash: outputPackages[index]?.payload_hash || payloadHashes[index],
    })).filter((row) => row.package_kind || row.output_package_id || row.payload_ref || row.payload_hash);
}

function packageSupersessionPreviewState() {
    return State.packageSupersessionPreview || null;
}

function sourceDirectoryPackageSupersessionPreviewState() {
    return State.sourceDirectoryPackageSupersessionPreview || null;
}

function nextSourceDirectoryPackageSupersessionPreviewRequestToken() {
    State.sourceDirectoryPackageSupersessionPreviewRequestToken += 1;
    return State.sourceDirectoryPackageSupersessionPreviewRequestToken;
}

function isCurrentSourceDirectoryPackageSupersessionPreviewRequest(requestToken) {
    return State.sourceDirectoryPackageSupersessionPreviewRequestToken === requestToken;
}

function replacementPackageSetAuthorityPreviewState() {
    return sourceDirectoryPackageSupersessionPreviewState() || packageSupersessionPreviewState() || null;
}

function isSourceDirectoryPackageSupersessionPreviewSelected(preview = replacementPackageSetAuthorityPreviewState()) {
    return Boolean(preview && preview === sourceDirectoryPackageSupersessionPreviewState());
}

function replacementPackageSetAuthorityPreviewSourceMode(preview = replacementPackageSetAuthorityPreviewState()) {
    return isSourceDirectoryPackageSupersessionPreviewSelected(preview)
        ? 'source_directory_package_supersession_preview'
        : 'package_supersession_preview';
}

function replacementPackageSetAuthorityPreviewSourceAuthority(preview = replacementPackageSetAuthorityPreviewState()) {
    return replacementPackageSetAuthorityPreviewSourceMode(preview) === 'source_directory_package_supersession_preview'
        ? SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_AUTHORITY
        : PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY;
}

function replacementPackageSetAuthoritySourcePackageSetHash(preview = replacementPackageSetAuthorityPreviewState()) {
    return preview?.source_package_set_hash || preview?.package_set_hash || null;
}

function packageSupersessionCommitPreviewState() {
    return replacementPackageSetAuthorityPreviewState();
}

function packageSupersessionCommitPreviewSourceMode(preview = packageSupersessionCommitPreviewState()) {
    return replacementPackageSetAuthorityPreviewSourceMode(preview);
}

function packageSupersessionCommitPreviewSourceAuthority(preview = packageSupersessionCommitPreviewState()) {
    return packageSupersessionCommitPreviewSourceMode(preview) === 'source_directory_package_supersession_preview'
        ? SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_SOURCE_AUTHORITY
        : PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY;
}

function replacementPackageArtifactMaterializationState() {
    return State.replacementPackageArtifactMaterialization || null;
}

function sourceDirectoryQualitativePackageAuthorityPayloadOrNull() {
    try {
        return sourceDirectoryPackageSupersessionPreviewPayload();
    } catch (_error) {
        return null;
    }
}

function isSourceDirectoryQualitativePackageAuthoritySelected() {
    const preview = sourceDirectoryPackageSupersessionPreviewState();
    const payload = sourceDirectoryQualitativePackageAuthorityPayloadOrNull();
    return Boolean(
        preview
        && payload
        && preview.schema_id === SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID
        && preview.package_review_submit_record_ref
        && payload.package_review_submit_record_ref === preview.package_review_submit_record_ref
        && payload.package_review_state === 'package_review_approved'
        && Array.isArray(payload.output_package_ids)
        && payload.output_package_ids.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && Array.isArray(payload.package_kinds)
        && payload.package_kinds.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && Array.isArray(payload.payload_hashes)
        && payload.payload_hashes.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
    );
}

function isSourceDirectoryQualitativeHandoffExportPrepareState(handoff = handoffExportPrepareState() || {}) {
    return handoff.schema_id === SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_SCHEMA_ID
        || handoff.handoff_export_prepare_schema_id === SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_SCHEMA_ID
        || handoff.source_gate === '808_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE';
}

function isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external = externalExportDownloadPrepareState() || {}) {
    return external.schema_id === SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        || external.external_export_download_prepare_schema_id === SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        || external.external_export_download_target === SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_TARGET
        || external.source_gate === '812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE';
}

function sourceDirectoryQualitativeExternalExportDownloadSelectedPackage(external = externalExportDownloadPrepareState() || {}) {
    const packages = Array.isArray(external.output_packages) ? external.output_packages : [];
    const selected = packages.find((row) => row.package_kind === 'user_facing') || packages[0] || {};
    const packageKinds = Array.isArray(external.package_kinds) ? external.package_kinds : [];
    const outputPackageIds = Array.isArray(external.output_package_ids) ? external.output_package_ids : [];
    const payloadHashes = Array.isArray(external.payload_hashes) ? external.payload_hashes : [];
    const selectedIndex = packageKinds.includes('user_facing') ? packageKinds.indexOf('user_facing') : 0;
    return {
        output_package_id: selected.output_package_id || outputPackageIds[selectedIndex],
        package_kind: selected.package_kind || packageKinds[selectedIndex],
        package_payload_hash: selected.package_payload_hash || selected.payload_hash || payloadHashes[selectedIndex],
    };
}

function sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusMatches(payload) {
    const status = State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus || {};
    return Boolean(
        status.delivery_available === true
        && status.schema_id === SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID
        && status.external_export_download_record_ref === payload.external_export_download_record_ref
        && status.export_download_descriptor_ref === payload.export_download_descriptor_ref
        && status.output_package_id === payload.output_package_id
        && status.package_kind === payload.package_kind
        && status.package_payload_hash === payload.package_payload_hash
        && status.same_origin_delivery_enabled === true
        && status.browser_managed_same_origin_attachment_enabled === true
        && status.provider_public_delivery_enabled === false
        && status.provider_private_signed_url_enabled === false
        && status.connector_dispatch_enabled === false
        && status.network_egress_enabled === false
        && status.frontend_durable_authority_enabled === false
        && status.package_payload_rewrite_enabled === false
        && status.source_package_row_mutation_enabled === false
        && status.raw_local_path_exposed === false
    );
}

function replacementPackageSetAuthorityState() {
    return State.replacementPackageSetAuthority || null;
}

function packageSupersessionCommitState() {
    return State.packageSupersessionCommit || null;
}

function replacementPackageArtifactManifestState() {
    return State.replacementPackageArtifactManifest || null;
}

function replacementPackageNamespaceState() {
    return State.replacementPackageNamespace || null;
}

function replacementPackageSetAuthorityBusy() {
    return Boolean(
        State.replacementPackageArtifactMaterializationPending
        || State.replacementPackageSetAuthorityPending
    );
}

function packageSupersessionCommitBusy() {
    return Boolean(State.packageSupersessionCommitPending);
}

function replacementPackageArtifactManifestBusy() {
    return Boolean(State.replacementPackageArtifactManifestPending);
}

function replacementPackageNamespaceBusy() {
    return Boolean(State.replacementPackageNamespacePending);
}

function clearReplacementPackageNamespaceState() {
    State.replacementPackageNamespace = null;
    State.replacementPackageNamespaceHistory = [];
    State.replacementPackageNamespaceError = null;
    State.replacementPackageNamespacePending = false;
}

function clearReplacementPackageArtifactManifestState() {
    State.replacementPackageArtifactManifest = null;
    State.replacementPackageArtifactManifestError = null;
    State.replacementPackageArtifactManifestPending = false;
    clearReplacementPackageNamespaceState();
}

function clearPackageSupersessionCommitState() {
    State.packageSupersessionCommit = null;
    State.packageSupersessionCommitError = null;
    State.packageSupersessionCommitPending = false;
    clearReplacementPackageArtifactManifestState();
}

function clearReplacementPackageSetAuthorityState() {
    State.replacementPackageArtifactMaterialization = null;
    State.replacementPackageArtifactMaterializationError = null;
    State.replacementPackageArtifactMaterializationPending = false;
    State.replacementPackageSetAuthority = null;
    State.replacementPackageSetAuthorityError = null;
    State.replacementPackageSetAuthorityPending = false;
    clearPackageSupersessionCommitState();
}

function clearSourceDirectoryPackageSupersessionPreviewState() {
    nextSourceDirectoryPackageSupersessionPreviewRequestToken();
    State.sourceDirectoryPackageSupersessionPreview = null;
    State.sourceDirectoryPackageSupersessionPreviewError = null;
    State.sourceDirectoryPackageSupersessionPreviewPending = false;
}

function safePackagePayloadRefForDisplay(value) {
    const text = String(value || '').trim();
    if (!text) return null;
    if (/^[A-Za-z]:[\\/]/.test(text) || text.startsWith('\\\\') || text.startsWith('/') || text.includes('\\')) {
        return 'redacted_local_payload_ref';
    }
    return text;
}

function renderPackageSupersessionPreviewRows(rows) {
    return rows.length
        ? rows.map((row) => {
            const payloadRef = safePackagePayloadRefForDisplay(row.payload_ref);
            return `
                <li>
                    <code>${escapeHtml(row.package_kind || 'unknown_package_kind')}</code>
                    ${row.output_package_id ? `<code>${escapeHtml(row.output_package_id)}</code>` : ''}
                    ${payloadRef ? `<code>${escapeHtml(payloadRef)}</code>` : ''}
                    ${row.payload_hash ? `<code>${escapeHtml(row.payload_hash)}</code>` : ''}
                </li>
            `;
        }).join('')
        : '<li>No immutable package rows are available.</li>';
}

function replacementPackageSourceArrays(preview = packageSupersessionPreviewState() || {}) {
    const previewRows = Array.isArray(preview.package_rows) ? preview.package_rows : [];
    const outputPackageIds = Array.isArray(preview.output_package_ids) && preview.output_package_ids.length
        ? preview.output_package_ids
        : (previewRows.length
            ? previewRows.map((row) => row.output_package_id).filter(Boolean)
            : packageOutputPackageIds());
    const packageKinds = Array.isArray(preview.package_kinds) && preview.package_kinds.length
        ? preview.package_kinds
        : (previewRows.length
            ? previewRows.map((row) => row.package_kind).filter(Boolean)
            : packageKindsFromState());
    const payloadRefs = Array.isArray(preview.payload_refs) && preview.payload_refs.length
        ? preview.payload_refs
        : (previewRows.length
            ? previewRows.map((row) => row.payload_ref).filter(Boolean)
            : packagePayloadRefs());
    const payloadHashes = Array.isArray(preview.payload_hashes) && preview.payload_hashes.length
        ? preview.payload_hashes
        : (previewRows.length
            ? previewRows.map((row) => row.payload_hash).filter(Boolean)
            : packagePayloadHashes());
    return {
        outputPackageIds,
        packageKinds,
        payloadRefs,
        payloadHashes,
    };
}

function replacementPackageRows({ packageIds = [], packageKinds = [], payloadRefs = [], payloadHashes = [] } = {}) {
    const rowCount = Math.max(packageIds.length, packageKinds.length, payloadRefs.length, payloadHashes.length);
    return Array.from({ length: rowCount }, (_value, index) => ({
        package_kind: packageKinds[index],
        output_package_id: packageIds[index],
        payload_ref: payloadRefs[index],
        payload_hash: payloadHashes[index],
    })).filter((row) => row.package_kind || row.output_package_id || row.payload_ref || row.payload_hash);
}

function packageSchemaIdForKind(packageKind) {
    return PACKAGE_REVIEW_PACKAGE_SCHEMA_IDS[packageKind] || null;
}

function replacementPackageNamespaceCandidateRows() {
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const commit = packageSupersessionCommitState() || {};
    const manifest = replacementPackageArtifactManifestState() || {};
    const sourcePackageKinds = replacementAuthority.source_package_kinds || commit.source_package_kinds || [];
    const sourcePackageIds = replacementAuthority.source_output_package_ids || commit.source_output_package_ids || [];
    const sourcePayloadRefs = replacementAuthority.source_payload_refs || commit.source_payload_refs || [];
    const sourcePayloadHashes = replacementAuthority.source_payload_hashes || commit.source_payload_hashes || [];
    const replacementPackageKinds = manifest.replacement_package_kinds || replacementAuthority.replacement_package_kinds || [];
    const verifiedRefs = manifest.verified_artifact_refs || manifest.replacement_payload_refs || [];
    const verifiedHashes = manifest.verified_artifact_hashes || manifest.replacement_payload_hashes || [];
    const rowCount = Math.max(
        replacementPackageKinds.length,
        sourcePackageKinds.length,
        sourcePackageIds.length,
        verifiedRefs.length,
        verifiedHashes.length,
    );
    return Array.from({ length: rowCount }, (_value, index) => {
        const packageKind = replacementPackageKinds[index] || sourcePackageKinds[index];
        return {
            package_kind: packageKind,
            package_schema_id: packageSchemaIdForKind(packageKind),
            source_package_kind: sourcePackageKinds[index],
            source_output_package_id: sourcePackageIds[index],
            source_payload_ref: sourcePayloadRefs[index],
            source_payload_hash: sourcePayloadHashes[index],
            artifact_ref: verifiedRefs[index],
            artifact_hash: verifiedHashes[index],
            replacement_artifact_manifest_id: manifest.replacement_package_artifact_manifest_id,
            replacement_artifact_manifest_authority_basis_hash: manifest.authority_basis_hash,
            replacement_package_set_authority_id: replacementAuthority.replacement_package_set_authority_id,
            replacement_package_set_authority_basis_hash: replacementAuthority.authority_basis_hash,
            package_supersession_commit_id: commit.package_supersession_commit_id,
            package_supersession_commit_basis_hash: commit.commit_basis_hash,
            session_id: manifest.session_id || replacementAuthority.session_id || commit.session_id || currentSessionId(),
        };
    }).filter((row) => (
        row.package_kind
        || row.source_output_package_id
        || row.artifact_ref
        || row.artifact_hash
    ));
}

function selectedReplacementPackageNamespaceRow() {
    const rows = replacementPackageNamespaceCandidateRows();
    if (!rows.length) return null;
    const recordedKinds = new Set(
        [
            ...State.replacementPackageNamespaceHistory,
            State.replacementPackageNamespace,
        ]
            .filter(Boolean)
            .map((row) => row.package_kind)
            .filter(Boolean),
    );
    return rows.find((row) => row.package_kind && !recordedKinds.has(row.package_kind)) || rows[0];
}

function renderReplacementPackageRows(rows) {
    return rows.length
        ? rows.map((row) => {
            const payloadRef = safePackagePayloadRefForDisplay(row.payload_ref);
            return `
                <li>
                    <code>${escapeHtml(row.package_kind || 'unknown_package_kind')}</code>
                    ${row.output_package_id ? `<code>${escapeHtml(row.output_package_id)}</code>` : ''}
                    ${payloadRef ? `<code>${escapeHtml(payloadRef)}</code>` : ''}
                    ${row.payload_hash ? `<code>${escapeHtml(row.payload_hash)}</code>` : ''}
                </li>
            `;
        }).join('')
        : '<li>No replacement package rows are available.</li>';
}

function renderPackageSupersessionDependencyRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.state_key || 'downstream_state')}</code>
                ${row.record_ref ? `<code>${escapeHtml(row.record_ref)}</code>` : ''}
                ${row.state ? `<span class="status-pill preview">${escapeHtml(row.state)}</span>` : ''}
            </li>
        `).join('')
        : '<li>No downstream dependency refs are present.</li>';
}

function packageLifecycleDashboardState(preview, construction, submit) {
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const supersessionCommit = packageSupersessionCommitState() || {};
    if (packageSupersessionCommitBusy()) return { label: 'package_supersession_commit_recording', pill: 'preview' };
    if (supersessionCommit.package_supersession_commit_id) {
        return { label: supersessionCommit.next_state || 'package_supersession_commit_recorded', pill: 'ok' };
    }
    if (replacementPackageSetAuthorityBusy()) return { label: 'replacement_package_set_authority_recording', pill: 'preview' };
    if (replacementAuthority.replacement_package_set_authority_id) {
        return { label: replacementAuthority.next_state || 'replacement_package_set_authority_recorded', pill: 'ok' };
    }
    if (State.packageReviewSubmitPending) return { label: 'package_lifecycle_submit_recording', pill: 'preview' };
    if (State.packageConstructionPending) return { label: 'package_lifecycle_construction_committing', pill: 'preview' };
    if (State.packageReviewPreviewPending) return { label: 'package_lifecycle_preview_inspecting', pill: 'preview' };
    const submitState = submit.package_review_state || submit.state;
    const submitRecorded = Boolean(
        submit.package_review_state
        || submit.submit_record_ref
    );
    if (submitRecorded) {
        return {
            label: submitState || 'package_review_recorded',
            pill: submitState === 'package_review_approved' ? 'ok' : 'blocked',
        };
    }
    if (
        State.replacementPackageSetAuthorityError
        || State.replacementPackageArtifactMaterializationError
        || State.packageSupersessionCommitError
        || State.packageReviewSubmitError
        || State.packageConstructionError
        || State.packageReviewPreviewError
    ) {
        return { label: 'package_lifecycle_blocked', pill: 'blocked' };
    }
    if (submit.package_review_submit_enabled === true) {
        return { label: submit.state || 'package_review_submit_ready', pill: 'ok' };
    }
    if (construction.state === 'package_constructed' || construction.next_state === 'package_constructed') {
        return { label: 'package_lifecycle_constructed', pill: 'ok' };
    }
    if (preview.package_review_preview_enabled === true) {
        return { label: preview.next_state || 'package_lifecycle_preview_ready', pill: 'preview' };
    }
    return { label: 'package_lifecycle_waiting_for_server_state', pill: 'blocked' };
}

function renderPackageLifecycleRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.package_kind || 'unknown_package_kind')}</code>
                ${row.output_package_id ? `<code>${escapeHtml(row.output_package_id)}</code>` : ''}
                ${row.payload_ref ? `<code>${escapeHtml(row.payload_ref)}</code>` : ''}
                ${row.payload_hash ? `<code>${escapeHtml(row.payload_hash)}</code>` : ''}
            </li>
        `).join('')
        : '<li>No package lifecycle rows are available.</li>';
}

function packageReviewSubmitDecisionNeedsNotes() {
    return PACKAGE_REVIEW_DECISIONS_REQUIRING_NOTES.has(elements.packageReviewSubmitDecision.value);
}

function handoffExportPrepareDecisionNeedsNotes() {
    return HANDOFF_EXPORT_PREPARE_DECISIONS_REQUIRING_NOTES.has(elements.handoffExportPrepareDecision.value);
}

function handoffExportPrepareState() {
    return State.handoffExportPrepare || State.sessionSummary?.handoff_export_prepare || null;
}

function recordedHandoffExportPrepare() {
    const state = handoffExportPrepareState();
    if (!state) return null;
    const recordedState = state.handoff_export_state || state.next_state || state.state;
    return state.prepare_record_ref || HANDOFF_EXPORT_PREPARE_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function apsHandoffDispatchState() {
    if (State.apsHandoffDispatch) {
        return State.apsHandoffDispatch;
    }
    const handoff = State.handoffExportPrepare;
    const handoffState = handoff?.handoff_export_state || handoff?.next_state || handoff?.state;
    const qualitativeAps = handoff?.schema_id === 'layer3.qual_aps_handoff_export_prepare.v1'
        || isQualitativeApsPackageSubmitState(packageReviewSubmitState() || {}, packageConstructionState() || {});
    if (
        qualitativeAps
        && handoffState === 'handoff_export_prepared'
        && handoff?.prepare_record_ref
        && handoffExportEnvelopeRef(handoff)
        && handoff?.package_review_submit_record_ref
    ) {
        return {
            schema_id: 'layer3.aps_handoff_dispatch_state.v1',
            available: true,
            state: 'aps_handoff_ready',
            blocked_reason: null,
            reconciliation_record_id: handoff.reconciliation_record_id,
            prepare_record_ref: handoff.prepare_record_ref,
            handoff_export_envelope_ref: handoffExportEnvelopeRef(handoff),
            aps_handoff_target: 'aps_evidence_bundle',
            dispatch_mode: 'server_side_aps_handoff',
            operator_decision: 'dispatch_aps_handoff',
            downstream_unavailable: handoff.downstream_unavailable,
        };
    }
    return State.sessionSummary?.aps_handoff_dispatch || null;
}

function apsHandoffStateName(state = apsHandoffDispatchState()) {
    return state?.aps_handoff_state || state?.next_state || state?.state || null;
}

function recordedApsHandoffDispatch() {
    const state = apsHandoffDispatchState();
    if (!state) return null;
    const recordedState = apsHandoffStateName(state);
    return state.aps_handoff_record_ref || APS_HANDOFF_DISPATCH_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function externalExportDownloadPrepareState() {
    return State.externalExportDownloadPrepare || State.sessionSummary?.external_export_download || null;
}

function externalExportDownloadStateName(state = externalExportDownloadPrepareState()) {
    return state?.external_export_download_state || state?.next_state || state?.state || null;
}

function recordedExternalExportDownloadPrepare() {
    const state = externalExportDownloadPrepareState();
    if (!state) return null;
    const recordedState = externalExportDownloadStateName(state);
    return state.external_export_download_record_ref || EXTERNAL_EXPORT_DOWNLOAD_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function connectorLocalDestinationReceiptStatusState() {
    return State.sessionSummary?.connector_local_destination_receipt || null;
}

function connectorLocalDestinationReceiptStateName(state = connectorLocalDestinationReceiptStatusState()) {
    return state?.connector_local_destination_receipt_state || state?.next_state || state?.state || null;
}

function isAssociatedCohortExternalExportDownloadState(external = externalExportDownloadPrepareState() || {}) {
    return external.pass_type === ASSOCIATED_COHORT_PASS_TYPE
        || (
            external.pass_scope === ASSOCIATED_COHORT_PASS_SCOPE
            && external.method === ASSOCIATED_COHORT_METHOD
            && external.source_gate === ASSOCIATED_COHORT_SOURCE_GATE
            && external.source_shape === ASSOCIATED_COHORT_SHAPE
        );
}

function isQualitativeApsExternalExportDownloadState(external = externalExportDownloadPrepareState() || {}) {
    if (isAssociatedCohortExternalExportDownloadState(external)) return false;
    if (isSourceIntakeExternalExportDownloadState(external)) return false;
    const summary = State.sessionSummary?.external_export_download || {};
    return external.pass_scope === QUAL_APS_PASS_SCOPE
        || summary.pass_scope === QUAL_APS_PASS_SCOPE
        || external.source_gate === QUAL_APS_SOURCE_GATE
        || summary.source_gate === QUAL_APS_SOURCE_GATE
        || external.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE
        || summary.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE;
}

function associatedCohortDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    return null;
}

function qualitativeApsDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    if (!isQualitativeApsExternalExportDownloadState(external)) return null;
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    return null;
}

function serverExternalExportDownloadDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    return null;
}

function isSourceIntakeExternalExportDownloadState(external = externalExportDownloadPrepareState() || {}) {
    const summary = State.sessionSummary?.external_export_download || {};
    return external.schema_id === SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        || summary.schema_id === SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        || external.pass_scope === SOURCE_INTAKE_PASS_SCOPE
        || summary.pass_scope === SOURCE_INTAKE_PASS_SCOPE
        || Boolean(external.source_intake_record_id || summary.source_intake_record_id);
}

function sourceIntakeDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    if (!isSourceIntakeExternalExportDownloadState(external)) return null;
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    const readiness = { ...summary, ...external };
    const readinessState = externalExportDownloadStateName(readiness);
    const available = Boolean(
        readiness.schema_id === SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        && readinessState === 'external_export_download_prepared'
        && readiness.external_export_download_record_ref
        && readiness.export_download_descriptor_ref
        && readiness.source_intake_record_id
        && readiness.candidate_id
        && readiness.aps_bundle_ref
        && readiness.source_artifact_hash
    );
    return {
        available,
        state: available
            ? 'source_intake_external_export_download_delivery_ui_ready'
            : 'source_intake_external_export_download_delivery_ui_blocked',
        operator_decision: 'deliver_external_export_download',
        delivery_mode: 'same_origin_artifact_stream',
        browser_managed_same_origin_attachment_enabled: available,
        public_url_enabled: false,
        signed_url_enabled: false,
        connector_dispatch_enabled: false,
        destination_selection_enabled: false,
        generic_downstream_dispatch_enabled: false,
        package_mutation_enabled: false,
        schema_runtime_source_widening_enabled: false,
        server_authority: SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
    };
}

function sourceDirectoryQualitativeExternalExportDownloadDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    if (!isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external)) return null;
    const selectedPackage = sourceDirectoryQualitativeExternalExportDownloadSelectedPackage(external);
    const readinessState = externalExportDownloadStateName(external);
    const available = Boolean(
        readinessState === 'external_export_download_prepared'
        && external.external_export_download_record_ref
        && external.export_download_descriptor_ref
        && external.prepare_record_ref
        && external.handoff_export_envelope_ref
        && selectedPackage.output_package_id
        && selectedPackage.package_kind
        && selectedPackage.package_payload_hash
    );
    return {
        available,
        state: available
            ? 'source_directory_external_export_download_delivery_ui_ready'
            : 'source_directory_external_export_download_delivery_ui_blocked',
        operator_decision: 'deliver_external_export_download',
        delivery_mode: 'same_origin_artifact_stream',
        browser_managed_same_origin_attachment_enabled: available,
        public_url_enabled: false,
        signed_url_enabled: false,
        connector_dispatch_enabled: false,
        destination_selection_enabled: false,
        generic_downstream_dispatch_enabled: false,
        package_mutation_enabled: false,
        schema_runtime_source_widening_enabled: false,
        server_authority: SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
    };
}

function deliveryUiStateAdmitted(deliveryUi, states) {
    return Boolean(
        deliveryUi
        && deliveryUi.available === true
        && states.includes(deliveryUi.state)
        && deliveryUi.operator_decision === 'deliver_external_export_download'
        && deliveryUi.delivery_mode === 'same_origin_artifact_stream'
        && deliveryUi.browser_managed_same_origin_attachment_enabled === true
        && deliveryUi.public_url_enabled === false
        && deliveryUi.signed_url_enabled === false
        && deliveryUi.connector_dispatch_enabled === false
        && deliveryUi.destination_selection_enabled === false
        && deliveryUi.generic_downstream_dispatch_enabled === false
        && deliveryUi.package_mutation_enabled === false
        && deliveryUi.schema_runtime_source_widening_enabled === false
    );
}

function externalExportDownloadDeliveryUiAdmitted(external = externalExportDownloadPrepareState() || {}) {
    const sourceDirectoryDeliveryUi = sourceDirectoryQualitativeExternalExportDownloadDeliveryUiState(external);
    if (sourceDirectoryDeliveryUi) {
        return deliveryUiStateAdmitted(sourceDirectoryDeliveryUi, [
            'source_directory_external_export_download_delivery_ui_ready',
        ]);
    }
    const sourceIntakeDeliveryUi = sourceIntakeDeliveryUiState(external);
    if (sourceIntakeDeliveryUi) {
        return deliveryUiStateAdmitted(sourceIntakeDeliveryUi, [
            'source_intake_external_export_download_delivery_ui_ready',
        ]);
    }
    if (isQualitativeApsExternalExportDownloadState(external)) {
        return deliveryUiStateAdmitted(qualitativeApsDeliveryUiState(external), [
            'external_export_download_delivery_ui_ready',
        ]);
    }
    if (isAssociatedCohortExternalExportDownloadState(external)) {
        const deliveryUi = associatedCohortDeliveryUiState(external);
        return deliveryUiStateAdmitted(deliveryUi, [
            'associated_cohort_external_export_download_delivery_ui_ready',
            'external_export_download_delivery_ui_ready',
        ]);
    }
    return deliveryUiStateAdmitted(serverExternalExportDownloadDeliveryUiState(external), [
        'external_export_download_delivery_ui_ready',
    ]);
}

function externalExportDownloadDeliveryStateName(state = State.externalExportDownloadDelivery) {
    return state?.external_export_download_delivery_state || state?.deliveryState || state?.state || null;
}

function recordedExternalExportDownloadDelivery() {
    const state = State.externalExportDownloadDelivery;
    if (!state) return null;
    const recordedState = externalExportDownloadDeliveryStateName(state);
    return EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function canGenerateExternalExportDownloadSignedReference() {
    const external = externalExportDownloadPrepareState() || {};
    return Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted(external)
        && !State.externalExportDownloadSignedReference?.signed_reference_token
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
    );
}

function canUseExternalExportDownloadSignedReference() {
    return Boolean(
        State.externalExportDownloadSignedReference?.signed_reference_token
        && State.externalExportDownloadSignedReference?.signed_reference_state === 'external_export_download_signed_reference_ready'
        && !State.externalExportDownloadSignedReferenceUse
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
    );
}

function providerPrivateSignedUrlReceiptId() {
    return State.providerPrivateSignedUrlRevoke?.provider_signed_url_receipt_id
        || State.providerPrivateSignedUrlStatus?.provider_signed_url_receipt_id
        || State.providerPrivateSignedUrlPrepare?.provider_signed_url_receipt_id
        || State.providerPrivateSignedUrlReceiptRecovery?.provider_signed_url_receipt_id
        || null;
}

function providerPrivateSignedUrlLatestState() {
    return State.providerPrivateSignedUrlRevoke?.provider_signed_url_state
        || State.providerPrivateSignedUrlStatus?.provider_signed_url_state
        || State.providerPrivateSignedUrlPrepare?.provider_signed_url_state
        || State.providerPrivateSignedUrlReceiptRecovery?.provider_signed_url_state
        || null;
}

function providerPrivateSignedUrlBlocksPrepare() {
    const receiptId = providerPrivateSignedUrlReceiptId();
    if (!receiptId) return false;
    return !PROVIDER_PRIVATE_SIGNED_URL_REPLACEABLE_STATES.has(providerPrivateSignedUrlLatestState());
}

function canPrepareProviderPrivateSignedUrl() {
    const external = externalExportDownloadPrepareState() || {};
    return Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted(external)
        && (!isSourceIntakeExternalExportDownloadState(external) || State.externalExportDownloadSignedReferenceUse)
        && !providerPrivateSignedUrlBlocksPrepare()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
        && !State.providerPrivateSignedUrlPending
    );
}

function canInspectProviderPrivateSignedUrl() {
    return Boolean(
        providerPrivateSignedUrlReceiptId()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.providerPrivateSignedUrlPending
    );
}

function canRevokeProviderPrivateSignedUrl() {
    return Boolean(
        providerPrivateSignedUrlReceiptId()
        && providerPrivateSignedUrlLatestState() !== 'provider_private_signed_url_revoked'
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.providerPrivateSignedUrlPending
    );
}

function providerPublicUrlReceiptId() {
    return State.providerPublicUrlRevoke?.provider_public_url_receipt_id
        || State.providerPublicUrlStatus?.provider_public_url_receipt_id
        || State.providerPublicUrlUse?.provider_public_url_receipt_id
        || State.providerPublicUrlPrepare?.provider_public_url_receipt_id
        || null;
}

function providerPublicUrlLatestState() {
    return State.providerPublicUrlRevoke?.provider_public_url_state
        || State.providerPublicUrlStatus?.provider_public_url_state
        || State.providerPublicUrlUse?.provider_public_url_state
        || State.providerPublicUrlPrepare?.provider_public_url_state
        || null;
}

function providerPublicUrlLatestSnapshot() {
    return State.providerPublicUrlRevoke
        || State.providerPublicUrlStatus
        || State.providerPublicUrlUse
        || State.providerPublicUrlPrepare
        || {};
}

function providerPublicUrlAuthorityState() {
    return State.providerPublicUrlStatus
        || State.providerPublicUrlPrepare
        || State.providerPublicUrlUse
        || State.providerPublicUrlRevoke
        || {};
}

function providerPublicUrlBlocksPrepare() {
    const receiptId = providerPublicUrlReceiptId();
    if (!receiptId) return false;
    return !PROVIDER_PUBLIC_URL_REPLACEABLE_STATES.has(providerPublicUrlLatestState());
}

function canPrepareProviderPublicUrl() {
    return Boolean(
        providerPrivateSignedUrlReceiptId()
        && providerPrivateSignedUrlLatestState() === 'provider_private_signed_url_prepared'
        && !providerPublicUrlBlocksPrepare()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.providerPrivateSignedUrlPending
        && !State.providerPublicUrlPending
    );
}

function canInspectProviderPublicUrl() {
    return Boolean(
        providerPublicUrlReceiptId()
        && !State.providerPublicUrlPending
    );
}

function canRevokeProviderPublicUrl() {
    return Boolean(
        providerPublicUrlReceiptId()
        && providerPublicUrlLatestState() !== 'provider_public_url_revoked'
        && !State.providerPublicUrlPending
    );
}

function canUseProviderPublicUrl() {
    return Boolean(
        providerPublicUrlReceiptId()
        && providerPublicUrlLatestState() === 'provider_public_url_prepared'
        && !State.providerPublicUrlUse
        && !State.providerPublicUrlPending
    );
}

function downstreamAccessLifecycleRows() {
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const external = externalExportDownloadPrepareState() || {};
    const delivery = State.externalExportDownloadDelivery || {};
    const signedReference = State.externalExportDownloadSignedReferenceUse || State.externalExportDownloadSignedReference || {};
    const providerPrivate = State.providerPrivateSignedUrlRevoke || State.providerPrivateSignedUrlStatus || State.providerPrivateSignedUrlPrepare || State.providerPrivateSignedUrlReceiptRecovery || {};
    const providerPublic = providerPublicUrlLatestSnapshot();
    const rows = [
        {
            stage: 'handoff/export prepare',
            state: handoff.handoff_export_state || handoff.next_state || handoff.state,
            record_ref: handoff.prepare_record_ref || handoffExportEnvelopeRef(handoff),
            authority: handoff.schema_id || 'handoff_export_prepare_response',
            access_mode: handoff.export_mode || handoff.handoff_target,
        },
        {
            stage: 'APS handoff dispatch',
            state: aps.aps_handoff_state || aps.next_state || aps.state,
            record_ref: aps.aps_handoff_record_ref,
            authority: aps.schema_id || 'aps_handoff_dispatch_response',
            access_mode: aps.dispatch_mode || aps.aps_handoff_target,
        },
        {
            stage: 'external export/download readiness',
            state: externalExportDownloadStateName(external),
            record_ref: external.external_export_download_record_ref || external.export_download_descriptor_ref,
            authority: external.schema_id || 'external_export_download_prepare_response',
            access_mode: external.delivery_mode || external.download_mode || external.export_download_target,
        },
        {
            stage: 'same-origin delivery',
            state: externalExportDownloadDeliveryStateName(delivery),
            record_ref: delivery.externalExportDownloadRecordRef || delivery.external_export_download_record_ref,
            authority: delivery.schemaId || delivery.schema_id || 'external_export_download_delivery_response',
            access_mode: externalExportDownloadDeliveryStateName(delivery) || delivery.externalExportDownloadRecordRef || delivery.external_export_download_record_ref
                ? (delivery.deliveryMode || delivery.delivery_mode || 'same_origin_artifact_stream')
                : null,
        },
        {
            stage: 'signed reference',
            state: signedReference.state || signedReference.signed_reference_state,
            record_ref: signedReference.signedReferenceReceiptId || signedReference.signed_reference_receipt_id,
            authority: signedReference.schemaId || signedReference.schema_id || 'external_export_download_signed_reference_response',
            access_mode: signedReference.state || signedReference.signed_reference_state || signedReference.signedReferenceReceiptId || signedReference.signed_reference_receipt_id
                ? (signedReference.replayPolicy || signedReference.signed_reference_replay_policy || 'same_origin_signed_delivery_reference')
                : null,
        },
        {
            stage: 'provider-private receipt',
            state: providerPrivate.provider_signed_url_state,
            record_ref: providerPrivate.provider_signed_url_receipt_id,
            authority: providerPrivate.schema_id || 'provider_private_signed_url_response',
            access_mode: providerPrivate.delivery_mode || providerPrivate.provider_url_replay_policy,
        },
        {
            stage: 'provider-public receipt',
            state: providerPublic.provider_public_url_state,
            record_ref: providerPublic.provider_public_url_receipt_id,
            authority: providerPublic.schema_id || 'provider_public_url_response',
            access_mode: providerPublic.provider_public_url_redacted ? 'redacted_receipt_only' : providerPublic.delivery_mode,
        },
    ];
    return rows.filter((row) => row.state || row.record_ref || row.access_mode);
}

function downstreamAccessLifecycleDashboardState(rows) {
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const external = externalExportDownloadPrepareState() || {};
    const apsState = apsHandoffStateName(aps);
    const externalState = externalExportDownloadStateName(external);
    if (
        State.handoffExportPreparePending
        || State.apsHandoffDispatchPending
        || State.externalExportDownloadPreparePending
        || State.externalExportDownloadDeliveryPending
        || State.externalExportDownloadSignedReferencePending
        || State.externalExportDownloadSignedReferenceUsePending
        || State.providerPrivateSignedUrlPending
        || State.providerPublicUrlPending
    ) {
        return { label: 'downstream_access_lifecycle_refreshing', pill: 'preview' };
    }
    const error = State.handoffExportPrepareError
        || State.apsHandoffDispatchError
        || State.externalExportDownloadPrepareError
        || State.externalExportDownloadDeliveryError
        || State.externalExportDownloadSignedReferenceError
        || State.providerPrivateSignedUrlError
        || State.providerPublicUrlError;
    if (error) {
        return { label: error.error_code || 'downstream_access_lifecycle_blocked', pill: 'blocked' };
    }
    if (providerPublicUrlLatestState()) {
        return { label: providerPublicUrlLatestState(), pill: 'ready' };
    }
    if (providerPrivateSignedUrlLatestState()) {
        return { label: providerPrivateSignedUrlLatestState(), pill: 'ready' };
    }
    if (State.externalExportDownloadSignedReferenceUse?.state || State.externalExportDownloadSignedReference?.signed_reference_state) {
        return { label: State.externalExportDownloadSignedReferenceUse?.state || State.externalExportDownloadSignedReference?.signed_reference_state, pill: 'ready' };
    }
    if (externalExportDownloadDeliveryStateName()) {
        return { label: externalExportDownloadDeliveryStateName(), pill: 'ready' };
    }
    if (
        externalState
        && (
            State.externalExportDownloadPrepare
            || external.available === true
            || externalState === 'external_export_download_ready'
            || recordedExternalExportDownloadPrepare()
        )
    ) {
        return { label: externalState, pill: recordedExternalExportDownloadPrepare() ? 'ready' : 'preview' };
    }
    if (
        apsState
        && (
            State.apsHandoffDispatch
            || aps.available === true
            || apsState === 'aps_handoff_ready'
            || recordedApsHandoffDispatch()
        )
    ) {
        return { label: apsState, pill: recordedApsHandoffDispatch() ? 'ready' : 'preview' };
    }
    if (handoff.handoff_export_state || handoff.next_state || handoff.state) {
        return { label: handoff.handoff_export_state || handoff.next_state || handoff.state, pill: recordedHandoffExportPrepare() ? 'ready' : 'preview' };
    }
    return {
        label: rows.length ? 'downstream_access_lifecycle_partial_server_state' : 'downstream_access_lifecycle_waiting_for_server_state',
        pill: rows.length ? 'preview' : 'blocked',
    };
}

function renderDownstreamAccessLifecycleRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.stage)}</code>
                ${row.state ? `<span>${escapeHtml(row.state)}</span>` : ''}
                ${row.record_ref ? `<code>${escapeHtml(row.record_ref)}</code>` : ''}
                ${row.access_mode ? `<span>${escapeHtml(row.access_mode)}</span>` : ''}
            </li>
        `).join('')
        : '<li>No downstream access lifecycle rows are available.</li>';
}

function layer3E2EGovernanceLifecycleRows() {
    const gateB = State.gateB || {};
    const gateC = State.gateC || State.sessionSummary?.gate_c || {};
    const planPreview = State.planPreview || State.sessionSummary?.plan_preview || {};
    const planApproval = State.planApproval || State.sessionSummary?.plan_approval || {};
    const selection = executionSelectionState();
    const start = executionStartState();
    const resultReview = recordedResultReview() || {};
    const packageRows = packageLifecycleOutputRows();
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageState = packageLifecycleDashboardState(preview, construction, submit);
    const materialization = replacementPackageArtifactMaterializationState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const handoff = handoffExportPrepareState() || {};
    const downstreamRows = downstreamAccessLifecycleRows();
    const downstreamState = downstreamAccessLifecycleDashboardState(downstreamRows);
    const latestDownstreamRow = [...downstreamRows].reverse().find((row) => row.state || row.record_ref || row.access_mode) || {};
    const providerPrivate = State.providerPrivateSignedUrlRevoke || State.providerPrivateSignedUrlStatus || State.providerPrivateSignedUrlPrepare || State.providerPrivateSignedUrlReceiptRecovery || {};
    const providerPublic = providerPublicUrlLatestSnapshot();
    return [
        {
            key: 'source_intake_gate_b',
            stage: 'source intake / Gate B',
            state: gateB.state || gateB.material_state || gateB.next_state,
            ref: gateB.source_intake_record_id || gateB.material_preview_id || gateB.session_id,
            authority: gateB.schema_id || 'gate_b_response_state',
        },
        {
            key: 'gate_c_typing',
            stage: 'Gate C typing',
            state: gateC.state || gateC.gate_c_state || gateC.next_state,
            ref: gateC.typing_record_ref || gateC.session_id || gateC.analysis_set_id,
            authority: gateC.schema_id || 'gate_c_response_state',
        },
        {
            key: 'plan_preview_approval',
            stage: 'plan preview / approval',
            state: planApproval.plan_approval_state || planApproval.state || planPreview.plan_preview_state || planPreview.state,
            ref: planApproval.analysis_plan_id || planPreview.preview_id,
            authority: planApproval.schema_id || planPreview.schema_id || 'plan_flow_response_state',
        },
        {
            key: 'execution_result_review',
            stage: 'execution / result review',
            state: resultReview.review_state || start.pass_run_status || start.state || selection.state,
            ref: selectedResultAuthority().passRunId || resultReview.review_record_ref || selection.analysis_plan_id,
            authority: resultReview.schema_id || start.schema_id || selection.schema_id || 'execution_response_state',
        },
        {
            key: 'package_lifecycle',
            stage: 'package lifecycle',
            state: packageState.label,
            ref: submit.submit_record_ref || construction.reconciliation_record_id || packageRows[0]?.output_package_id,
            authority: PACKAGE_LIFECYCLE_DASHBOARD_MODE,
        },
        {
            key: 'replacement_package_set_authority',
            stage: 'replacement package-set authority',
            state: replacementAuthority.next_state || materialization.next_state,
            ref: replacementAuthority.replacement_package_set_authority_id
                || materialization.replacement_artifact_materialization_id,
            authority: replacementAuthority.replacement_package_set_authority_mode
                || materialization.replacement_package_artifact_materialization_mode,
        },
        {
            key: 'handoff_export',
            stage: 'handoff/export',
            state: handoff.handoff_export_state || handoff.next_state || handoff.state,
            ref: handoff.prepare_record_ref || handoffExportEnvelopeRef(handoff),
            authority: handoff.schema_id || 'handoff_export_response_state',
        },
        {
            key: 'downstream_access',
            stage: latestDownstreamRow.stage ? `downstream access / ${latestDownstreamRow.stage}` : 'downstream access',
            state: downstreamState.label,
            ref: latestDownstreamRow.record_ref,
            authority: DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE,
            access_mode: latestDownstreamRow.access_mode,
        },
        {
            key: 'provider_connector_boundaries',
            stage: 'provider / connector boundaries',
            state: providerPublic.provider_public_url_state || providerPrivate.provider_signed_url_state,
            ref: providerPublic.provider_public_url_receipt_id || providerPrivate.provider_signed_url_receipt_id,
            authority: 'provider_receipt_and_connector_record_only_state',
        },
    ].filter((row) => row.state || row.ref);
}

function layer3E2EGovernanceLifecycleDashboardState(rows) {
    if (
        State.executionSelectionPending
        || State.executionStartPending
        || State.resultReviewPending
        || State.packageReviewPreviewPending
        || State.packageConstructionPending
        || State.packageReviewSubmitPending
        || State.replacementPackageArtifactMaterializationPending
        || State.replacementPackageSetAuthorityPending
        || State.handoffExportPreparePending
        || State.apsHandoffDispatchPending
        || State.externalExportDownloadPreparePending
        || State.externalExportDownloadDeliveryPending
        || State.externalExportDownloadSignedReferencePending
        || State.externalExportDownloadSignedReferenceUsePending
        || State.providerPrivateSignedUrlPending
        || State.providerPublicUrlPending
    ) {
        return { label: 'layer3_e2e_governance_lifecycle_refreshing', pill: 'preview' };
    }
    const error = State.executionSelectionError
        || State.executionStartError
        || State.resultReviewError
        || State.packageReviewPreviewError
        || State.packageConstructionError
        || State.packageReviewSubmitError
        || State.replacementPackageArtifactMaterializationError
        || State.replacementPackageSetAuthorityError
        || State.handoffExportPrepareError
        || State.apsHandoffDispatchError
        || State.externalExportDownloadPrepareError
        || State.externalExportDownloadDeliveryError
        || State.externalExportDownloadSignedReferenceError
        || State.providerPrivateSignedUrlError
        || State.providerPublicUrlError;
    if (error) {
        return { label: error.error_code || 'layer3_e2e_governance_lifecycle_blocked', pill: 'blocked' };
    }
    const furthest = [...rows].reverse().find((row) => row.state || row.ref);
    if (furthest) {
        const stateKey = furthest.key || furthest.stage.replace(/[^a-z0-9]+/gi, '_').toLowerCase();
        return { label: `layer3_e2e_latest_${stateKey}`, pill: 'ready' };
    }
    return { label: 'layer3_e2e_governance_lifecycle_waiting_for_server_state', pill: 'blocked' };
}

function renderLayer3E2EGovernanceLifecycleRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.stage)}</code>
                ${row.state ? `<span>${escapeHtml(row.state)}</span>` : ''}
                ${row.ref ? `<code>${escapeHtml(row.ref)}</code>` : ''}
                ${row.authority ? `<span>${escapeHtml(row.authority)}</span>` : ''}
                ${row.access_mode ? `<span>${escapeHtml(row.access_mode)}</span>` : ''}
            </li>
        `).join('')
        : '<li>No Layer 3 governance lifecycle rows are available.</li>';
}

function handoffExportEnvelopeRef(handoff = handoffExportPrepareState() || State.sessionSummary?.handoff_export_prepare || {}) {
    return handoff.handoff_export_envelope_ref || handoff.handoff_export_envelope?.envelope_ref || null;
}

function canCommitPackageConstruction() {
    const authority = selectedResultAuthority();
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && recordedApprovedResultReview()
        && preview.package_review_preview_enabled === true
        && preview.package_commit_enabled === true
        && preview.package_review_preview_hash
        && construction.state !== 'package_constructed'
        && construction.next_state !== 'package_constructed'
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitPackageReview() {
    const authority = selectedResultAuthority();
    const review = recordedApprovedResultReview();
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const cohort = associatedCohortProjection(authority);
    const notes = elements.packageReviewSubmitNotes.value.trim();
    const qualitativeAps = isQualitativeApsPackageSubmitState(submit, construction);
    const previewHash = packageReviewPreviewHash();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && review?.review_record_ref
        && (!cohort.isAssociated || cohort.ready)
        && previewHash
        && submit.package_review_submit_enabled === true
        && submit.reconciliation_record_id
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && (!qualitativeAps || submit.construction_basis_hash || construction.construction_basis_hash)
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && (!packageReviewSubmitDecisionNeedsNotes() || notes)
    );
}

function canSubmitPackageSupersessionPreview() {
    const authority = selectedResultAuthority();
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const packageReviewState = submit.package_review_state || submit.next_state || submit.state;
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && packageReviewState === 'package_review_approved'
        && submit.submit_record_ref
        && (submit.reconciliation_record_id || construction.reconciliation_record_id)
        && packageReviewPreviewHash()
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.packageSupersessionPreviewPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitReplacementPackageSetAuthority() {
    const authority = selectedResultAuthority();
    const preview = replacementPackageSetAuthorityPreviewState() || {};
    const source = replacementPackageSourceArrays(preview);
    const sourceMode = replacementPackageSetAuthorityPreviewSourceMode(preview);
    const sourcePackageSetHash = replacementPackageSetAuthoritySourcePackageSetHash(preview);
    const noPendingLifecycleWork = Boolean(
        !replacementPackageSetAuthorityState()
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.packageSupersessionPreviewPending
        && !State.sourceDirectoryPackageSupersessionPreviewPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    if (sourceMode === 'source_directory_package_supersession_preview') {
        return Boolean(
            preview.session_id
            && preview.reconciliation_record_id
            && preview.package_supersession_preview_hash
            && sourcePackageSetHash
            && noPendingLifecycleWork
        );
    }
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && preview.package_supersession_preview_hash
        && sourcePackageSetHash
        && (preview.reconciliation_record_id || packageReviewSubmitState()?.reconciliation_record_id || packageConstructionState()?.reconciliation_record_id)
        && source.outputPackageIds.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && source.packageKinds.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && source.payloadRefs.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && source.payloadHashes.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && noPendingLifecycleWork
    );
}

function canSubmitPackageSupersessionCommit() {
    const authority = selectedResultAuthority();
    const preview = packageSupersessionCommitPreviewState() || {};
    const sourceMode = packageSupersessionCommitPreviewSourceMode(preview);
    const sourcePackageSetHash = replacementPackageSetAuthoritySourcePackageSetHash(preview);
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const source = replacementPackageSourceArrays(preview);
    const noPendingLifecycleWork = Boolean(
        !packageSupersessionCommitState()
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.packageSupersessionPreviewPending
        && !State.sourceDirectoryPackageSupersessionPreviewPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    if (sourceMode === 'source_directory_package_supersession_preview') {
        return Boolean(
            preview.session_id
            && preview.reconciliation_record_id
            && preview.package_supersession_preview_hash
            && sourcePackageSetHash
            && replacementAuthority.replacement_package_set_authority_id
            && replacementAuthority.authority_basis_hash
            && noPendingLifecycleWork
        );
    }
    return Boolean(
        stableHashAvailable()
        && hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && preview.package_supersession_preview_hash
        && preview.package_set_hash
        && Array.isArray(preview.downstream_dependencies)
        && replacementAuthority.replacement_package_set_authority_id
        && replacementAuthority.replacement_package_set_id
        && replacementAuthority.replacement_package_set_hash
        && replacementAuthority.authority_basis_hash
        && source.outputPackageIds.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && source.packageKinds.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && source.payloadRefs.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && source.payloadHashes.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && Array.isArray(replacementAuthority.replacement_package_kinds)
        && replacementAuthority.replacement_package_kinds.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && Array.isArray(replacementAuthority.replacement_payload_refs)
        && replacementAuthority.replacement_payload_refs.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && Array.isArray(replacementAuthority.replacement_payload_hashes)
        && replacementAuthority.replacement_payload_hashes.length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && noPendingLifecycleWork
    );
}

function canSubmitReplacementPackageArtifactManifest() {
    const authority = selectedResultAuthority();
    const materialization = replacementPackageArtifactMaterializationState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const commit = packageSupersessionCommitState() || {};
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && materialization.replacement_artifact_materialization_id
        && materialization.materialization_basis_hash
        && replacementAuthority.replacement_package_set_authority_id
        && replacementAuthority.authority_basis_hash
        && commit.package_supersession_commit_id
        && commit.commit_basis_hash
        && (materialization.session_id || replacementAuthority.session_id || commit.session_id || authority.sessionId)
        && (materialization.analysis_plan_id || replacementAuthority.analysis_plan_id || commit.analysis_plan_id || authority.analysisPlanId)
        && (materialization.pass_run_id || replacementAuthority.pass_run_id || commit.pass_run_id || authority.passRunId)
        && (materialization.reconciliation_record_id || replacementAuthority.reconciliation_record_id || commit.reconciliation_record_id)
        && !replacementPackageArtifactManifestState()
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.packageSupersessionPreviewPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitReplacementPackageNamespace() {
    const manifest = replacementPackageArtifactManifestState() || {};
    const row = selectedReplacementPackageNamespaceRow();
    return Boolean(
        stableHashAvailable()
        && manifest.replacement_package_artifact_manifest_id
        && manifest.authority_basis_hash
        && row
        && row.session_id
        && row.replacement_artifact_manifest_id
        && row.replacement_artifact_manifest_authority_basis_hash
        && row.replacement_package_set_authority_id
        && row.replacement_package_set_authority_basis_hash
        && row.package_supersession_commit_id
        && row.package_supersession_commit_basis_hash
        && row.source_output_package_id
        && row.source_package_kind === row.package_kind
        && row.package_schema_id
        && row.source_payload_ref
        && row.source_payload_hash
        && row.artifact_ref
        && row.artifact_hash
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.packageSupersessionPreviewPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitHandoffExportPrepare() {
    const authority = selectedResultAuthority();
    const handoff = State.sessionSummary?.handoff_export_prepare || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const notes = elements.handoffExportPrepareNotes.value.trim();
    if (isSourceDirectoryQualitativePackageAuthoritySelected()) {
        const sourcePayload = sourceDirectoryQualitativeHandoffExportPreparePayloadOrNull();
        return Boolean(
            sourcePayload
            && sourcePayload.package_review_state === 'package_review_approved'
            && sourcePayload.package_review_submit_record_ref
            && !recordedHandoffExportPrepare()
            && !State.resultReviewPending
            && !State.packageReviewPreviewPending
            && !State.packageConstructionPending
            && !State.packageReviewSubmitPending
            && !replacementPackageSetAuthorityBusy()
            && !packageSupersessionCommitBusy()
            && !replacementPackageArtifactManifestBusy()
            && !replacementPackageNamespaceBusy()
            && !State.handoffExportPreparePending
            && !State.apsHandoffDispatchPending
            && !State.externalExportDownloadPreparePending
            && !State.externalExportDownloadDeliveryPending
            && (!handoffExportPrepareDecisionNeedsNotes() || notes)
        );
    }
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && handoff.available === true
        && handoff.handoff_export_prepare_enabled === true
        && packageReviewState === 'package_review_approved'
        && handoff.result_review_record_ref
        && handoff.package_review_preview_hash
        && handoff.reconciliation_record_id
        && handoff.package_review_submit_record_ref
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !recordedHandoffExportPrepare()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && (!handoffExportPrepareDecisionNeedsNotes() || notes)
    );
}

function canSubmitApsHandoffDispatch() {
    const authority = selectedResultAuthority();
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = handoff.handoff_export_state || handoff.next_state || handoff.state;
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && packageReviewState === 'package_review_approved'
        && prepareState === 'handoff_export_prepared'
        && aps.available === true
        && aps.state === 'aps_handoff_ready'
        && aps.prepare_record_ref
        && aps.handoff_export_envelope_ref
        && handoff.prepare_record_ref
        && handoffExportEnvelopeRef(handoff)
        && handoff.result_review_record_ref
        && handoff.package_review_preview_hash
        && handoff.reconciliation_record_id
        && handoff.package_review_submit_record_ref
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !recordedApsHandoffDispatch()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitExternalExportDownloadPrepare() {
    const authority = selectedResultAuthority();
    const external = State.sessionSummary?.external_export_download || {};
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state;
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    if (isSourceDirectoryQualitativeHandoffExportPrepareState(handoff)) {
        const sourcePayload = sourceDirectoryQualitativeExternalExportDownloadPreparePayloadOrNull();
        return Boolean(
            sourcePayload
            && sourcePayload.package_review_state === 'package_review_approved'
            && sourcePayload.prepare_record_ref
            && sourcePayload.handoff_export_envelope_ref
            && !recordedExternalExportDownloadPrepare()
            && !State.resultReviewPending
            && !State.packageReviewPreviewPending
            && !State.packageConstructionPending
            && !State.packageReviewSubmitPending
            && !replacementPackageSetAuthorityBusy()
            && !packageSupersessionCommitBusy()
            && !replacementPackageNamespaceBusy()
            && !State.handoffExportPreparePending
            && !State.apsHandoffDispatchPending
            && !State.externalExportDownloadPreparePending
            && !State.externalExportDownloadDeliveryPending
        );
    }
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && packageReviewState === 'package_review_approved'
        && prepareState === 'handoff_export_prepared'
        && apsState === 'aps_handoff_dispatched'
        && external.available === true
        && external.state === 'external_export_download_ready'
        && external.external_export_download_prepare_enabled === true
        && external.result_review_record_ref
        && external.package_review_preview_hash
        && external.reconciliation_record_id
        && external.package_review_submit_record_ref
        && external.prepare_record_ref
        && external.handoff_export_envelope_ref
        && external.aps_handoff_record_ref
        && external.aps_output_package_id
        && external.aps_output_package_kind
        && external.aps_bundle_ref
        && external.aps_bundle_id
        && external.aps_schema_id
        && external.source_artifact_hash
        && external.source_artifact_size_bytes != null
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !recordedExternalExportDownloadPrepare()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitExternalExportDownloadDelivery() {
    const authority = selectedResultAuthority();
    const external = externalExportDownloadPrepareState() || {};
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state;
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    const readinessState = externalExportDownloadStateName(external);
    if (isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external)) {
        const sourcePayload = sourceDirectoryQualitativeExternalExportDownloadDeliveryPayloadOrNull();
        return Boolean(
            sourcePayload
            && sourcePayload.external_export_download_state === 'external_export_download_prepared'
            && sourcePayload.external_export_download_record_ref
            && sourcePayload.export_download_descriptor_ref
            && sourcePayload.output_package_id
            && sourcePayload.package_kind
            && sourcePayload.package_payload_hash
            && externalExportDownloadDeliveryUiAdmitted(external)
            && !State.resultReviewPending
            && !State.packageReviewPreviewPending
            && !State.packageConstructionPending
            && !State.packageReviewSubmitPending
            && !replacementPackageSetAuthorityBusy()
            && !packageSupersessionCommitBusy()
            && !replacementPackageNamespaceBusy()
            && !State.handoffExportPreparePending
            && !State.apsHandoffDispatchPending
            && !State.externalExportDownloadPreparePending
            && !State.externalExportDownloadDeliveryPending
        );
    }
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && packageReviewState === 'package_review_approved'
        && prepareState === 'handoff_export_prepared'
        && apsState === 'aps_handoff_dispatched'
        && readinessState === 'external_export_download_prepared'
        && externalExportDownloadDeliveryUiAdmitted(external)
        && external.external_export_download_record_ref
        && external.export_download_descriptor_ref
        && external.result_review_record_ref
        && external.package_review_preview_hash
        && external.reconciliation_record_id
        && external.package_review_submit_record_ref
        && external.prepare_record_ref
        && external.handoff_export_envelope_ref
        && external.aps_handoff_record_ref
        && external.aps_output_package_id
        && external.aps_output_package_kind
        && external.aps_bundle_ref
        && external.aps_bundle_id
        && external.aps_schema_id
        && external.source_artifact_hash
        && external.source_artifact_size_bytes != null
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function isPackageActive() {
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return Boolean(
        (recordedApprovedResultReview() && !associatedCohortReviewContext())
        || State.packageReviewPreview?.package_review_preview_enabled === true
        || construction.state === 'package_constructed'
        || construction.next_state === 'package_constructed'
        || submit.package_review_submit_enabled === true
        || submit.submit_record_ref
    );
}

function isHandoffActive() {
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const submit = packageReviewSubmitState() || {};
    return Boolean(
        submit.package_review_state === 'package_review_approved'
        || submit.state === 'package_review_approved'
        || handoff.available === true
        || handoff.state === 'handoff_export_ready'
        || recordedHandoffExportPrepare()
        || aps.available === true
        || recordedApsHandoffDispatch()
        || (externalExportDownloadPrepareState() || {}).available === true
        || recordedExternalExportDownloadPrepare()
    );
}

function decisionState(candidateId) {
    return State.gateBDecisions[candidateId] || { decision: 'approved', operator_reason: '' };
}

function syncDecisionStateFromRow(row) {
    const candidateId = row.dataset.candidateId;
    if (!candidateId) return;
    State.gateBDecisions[candidateId] = {
        decision: row.querySelector('.decision-select')?.value || 'approved',
        operator_reason: row.querySelector('.reason-input')?.value || '',
    };
    persistGateBDraftSnapshot();
}

function termsFromIntent(intent) {
    return Array.from(new Set(
        intent.toLowerCase()
            .split(/[^a-z0-9_]+/)
            .map((term) => term.trim())
            .filter((term) => term.length > 3)
    )).slice(0, 6);
}

function candidateSearchText(candidate) {
    const trace = candidate.source_trace || {};
    const traceRefs = trace.aps_trace_refs || {};
    return [
        candidate.candidate_id,
        candidate.source_label,
        candidate.source_class,
        candidate.owner_service_source_shape,
        candidate.planning_shape_family,
        candidate.source_family,
        candidate.source_family_label,
        candidate.source_admission_state,
        trace.trace_readiness,
        traceRefs.parser_family,
        traceRefs.parser_contract_id,
        traceRefs.typed_content_contract_id,
        traceRefs.target_id,
        traceRefs.accession_number,
        traceRefs.diagnostics_ref,
        traceRefs.content_units_ref,
        traceRefs.normalized_text_ref,
        traceRefs.blob_ref,
        trace.document_identity?.content_id,
        trace.document_identity?.content_contract_id,
        trace.document_identity?.chunking_contract_id,
        candidate.validation_status,
        candidate.duplicate_status,
    ].join(' ').toLowerCase();
}

function humanizeToken(value) {
    const text = String(value ?? '').trim();
    if (!text) return 'none';
    return text.replace(/[_-]+/g, ' ');
}

function shortText(value, maxLength = 36) {
    const text = String(value ?? '').trim();
    if (!text) return 'none';
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(8, maxLength - 12))}...${text.slice(-8)}`;
}

function normalizeModality(value) {
    const text = String(value ?? '').toLowerCase();
    if (!text) return 'unclassified';
    if (text.includes('hybrid') || text.includes('mixed')) return 'hybrid';
    if (text.includes('qual')) return 'qualitative';
    if (
        text.includes('quant')
        || text.includes('deterministic')
        || text.includes('dataset')
        || text.includes('numeric')
        || text.includes('time_series')
    ) {
        return 'quantitative';
    }
    return 'unclassified';
}

function modalityMeta(modality) {
    return SUBLAYER_MODALITY_META[modality] || SUBLAYER_MODALITY_META.unclassified;
}

function groupedByModality(items) {
    return SUBLAYER_MODALITIES.reduce((groups, modality) => {
        groups[modality] = items.filter((item) => item.modality === modality);
        return groups;
    }, {});
}

function sessionSublayerState() {
    const state = State.sessionSummary?.sublayer_visualization;
    return state && typeof state === 'object' ? state : {};
}

function sourceIdentityLabel(identity = {}) {
    const candidates = [
        identity.candidate_id,
        identity.dataset_version_id,
        identity.content_id,
        identity.run_id,
        identity.target_id,
        identity.source_ref,
    ];
    return candidates.find((candidate) => candidate) || null;
}

function currentMaterialObjects() {
    const candidates = State.materialPreview?.material_candidates || [];
    if (candidates.length) {
        return candidates.map((candidate, index) => {
            const decision = decisionState(candidate.candidate_id).decision;
            return {
                id: candidate.candidate_id || `candidate-${index + 1}`,
                label: candidate.source_label || `Material candidate ${index + 1}`,
                kind: candidate.source_class || 'material candidate',
                primary: candidate.owner_service_source_shape || candidate.planning_shape_family || 'source shape unavailable',
                secondary: candidate.query_basis || candidate.duplicate_status || 'preview candidate',
                badge: decision,
                modality: normalizeModality(candidate.owner_service_source_shape || candidate.planning_shape_family || candidate.source_class),
                live: true,
            };
        });
    }

    const persistedObjects = sessionSublayerState().material_objects || [];
    if (persistedObjects.length) {
        return persistedObjects.map((item, index) => {
            const identity = item.source_identity || {};
            const identityLabel = sourceIdentityLabel(identity);
            const loadedRecords = item.load_summary?.loaded_records;
            return {
                id: item.material_snapshot_id || `material-snapshot-${index + 1}`,
                label: humanizeToken(identityLabel || item.source_shape || `Material snapshot ${index + 1}`),
                kind: item.source_shape || 'material snapshot',
                primary: identityLabel || item.source_plane || 'persisted material snapshot',
                secondary: loadedRecords !== undefined
                    ? `${loadedRecords} loaded record${loadedRecords === 1 ? '' : 's'}`
                    : (item.source_plane || 'session material ledger'),
                badge: item.state || 'loaded',
                modality: normalizeModality(item.source_shape || item.source_plane),
                live: true,
            };
        });
    }

    const gateB = State.gateB || {};
    const gateBIds = [
        ...(gateB.approved_candidate_ids || []).map((id) => ({ id, decision: 'approved' })),
        ...(gateB.denied_candidate_ids || []).map((id) => ({ id, decision: 'denied' })),
        ...(gateB.isolated_candidate_ids || []).map((id) => ({ id, decision: 'isolated' })),
        ...(gateB.flagged_candidate_ids || []).map((id) => ({ id, decision: 'flagged' })),
    ];
    if (gateBIds.length) {
        return gateBIds.map((item, index) => ({
            id: item.id || `gate-b-${index + 1}`,
            label: `Gate B ${humanizeToken(item.decision)} material`,
            kind: 'session-scoped material',
            primary: 'Gate B decision record',
            secondary: currentSessionId() ? `session ${shortText(currentSessionId(), 24)}` : 'session not reported',
            badge: item.decision,
            modality: 'unclassified',
            live: true,
        }));
    }

    const rail = currentAuthorityRail();
    const railSessionId = rail?.session_id && rail.session_id !== 'none' ? rail.session_id : null;
    const sessionId = State.gateB?.session_id || railSessionId;
    if (sessionId) {
        return [{
            id: sessionId,
            label: 'Session-scoped material posture',
            kind: 'authority rail',
            primary: `${rail?.approved_material_count ?? 0} approved / ${rail?.denied_material_count ?? 0} denied`,
            secondary: `typing ${rail?.typing_status || 'not_started'}`,
            badge: rail?.current_gate || 'session',
            modality: 'unclassified',
            live: true,
        }];
    }
    return [];
}

function currentTypingObjects() {
    const records = State.gateC?.typing_records || [];
    const persistedRecords = sessionSublayerState().typing_records || [];
    const sourceRecords = records.length ? records : persistedRecords;
    const typed = sourceRecords.map((record, index) => ({
        id: record.material_snapshot_id || `typing-${index + 1}`,
        label: record.planning_shape_family || 'Typed material',
        kind: record.owner_service_source_shape || 'source shape',
        primary: `modality ${humanizeToken(record.chosen_modality)}`,
        secondary: `confidence ${record.confidence ?? 'none'}`,
        badge: record.authoritative ? 'authoritative' : 'preview',
        modality: normalizeModality(record.chosen_modality || record.analysis_modality || record.planning_shape_family),
        live: true,
    }));
    const unsupported = (State.gateC?.unsupported_material || []).map((item, index) => ({
        id: item.material_snapshot_id || `unsupported-${index + 1}`,
        label: 'Unsupported material',
        kind: item.owner_service_source_shape || 'source shape',
        primary: item.reason || 'unsupported typing shape',
        secondary: 'held outside typed modality lanes',
        badge: 'unsupported',
        modality: 'unclassified',
        live: true,
    }));
    return [...typed, ...unsupported];
}

function currentPlanBody() {
    if (State.planApproval?.approved_plan) return State.planApproval.approved_plan;
    if (State.planPreview?.schema_id === 'layer3.plan_preview_result.v1') {
        return State.planPreview.plan_preview || State.planPreview;
    }
    if (sessionSublayerState().latest_plan) return sessionSublayerState().latest_plan;
    return null;
}

function currentPlanSetObjects() {
    const plan = currentPlanBody();
    const sets = (plan?.approved_sets || []).length
        ? (plan.approved_sets || [])
        : (plan?.admitted_sets || []);
    return sets.map((item, index) => ({
        id: item.analysis_set_id || `analysis-set-${index + 1}`,
        label: item.analysis_set_label || item.analysis_set_id || `Analysis set ${index + 1}`,
        kind: 'analysis set',
        primary: `modality ${humanizeToken(item.analysis_modality)}`,
        secondary: item.status || item.set_status || 'admitted',
        badge: plan?.approved || State.planApproval ? 'approved' : 'admitted',
        modality: normalizeModality(item.analysis_modality),
        live: true,
    }));
}

function currentPersistedAnalysisSetObjects() {
    return (sessionSublayerState().analysis_sets || []).map((item, index) => ({
        id: item.analysis_set_id || `persisted-analysis-set-${index + 1}`,
        label: item.analysis_set_id || `Analysis set ${index + 1}`,
        kind: item.set_type || 'analysis set',
        primary: `modality ${humanizeToken(item.analysis_modality)}`,
        secondary: item.unit_count !== undefined
            ? `${item.unit_count} unit${item.unit_count === 1 ? '' : 's'}`
            : 'formed Gate C set',
        badge: item.state || 'formed',
        modality: normalizeModality(item.analysis_modality),
        live: true,
    }));
}

function currentPlannedPasses() {
    const plan = currentPlanBody();
    return plan?.planned_passes || [];
}

function modalityFromPlanPass(pass) {
    const candidates = [
        pass?.analysis_modality,
        pass?.pass_scope,
        pass?.engine_family,
        pass?.method_family,
        pass?.pass_type,
        pass?.set_type,
    ];
    for (const candidate of candidates) {
        const modality = normalizeModality(candidate);
        if (modality && modality !== 'unclassified') return modality;
    }
    return 'unclassified';
}

function planPassesForModality(modality) {
    return currentPlannedPasses().filter((item) => modalityFromPlanPass(item) === modality);
}

function modalityFromEngineFamily(value) {
    const text = String(value || '').toLowerCase();
    if (text.includes('quant') || text.includes('deterministic')) return 'quantitative';
    if (text.includes('qual')) return 'qualitative';
    if (text.includes('hybrid') || text.includes('mixed')) return 'hybrid';
    return null;
}

function currentResultModality() {
    const fromStatus = modalityFromEngineFamily(State.resultStatus?.engine_family);
    if (fromStatus) return fromStatus;
    const passRunModalities = new Set(
        (sessionSublayerState().pass_runs || [])
            .map((passRun) => modalityFromEngineFamily(passRun.engine_family))
            .filter(Boolean)
    );
    if (passRunModalities.size === 1) return [...passRunModalities][0];
    const plannedModalities = new Set(
        currentPlannedPasses()
            .map((pass) => modalityFromPlanPass(pass))
            .filter((modality) => modality && modality !== 'unclassified')
    );
    return plannedModalities.size === 1 ? [...plannedModalities][0] : null;
}

function currentExecutionPipeline() {
    const summary = State.sessionSummary || {};
    const selection = summary.execution_selection || {};
    const start = summary.analysis_execution_start || {};
    const status = State.resultStatus || {};
    const review = recordedResultReview() || State.resultReview || {};
    const persistedPassRuns = sessionSublayerState().pass_runs || [];
    const cards = [];
    const outputs = [];

    if (selection.selected || selection.pass_run_count || (Array.isArray(selection.pass_run_ids) && selection.pass_run_ids.length)) {
        const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
        cards.push({
            label: 'Execution selection',
            primary: selection.state || (selection.selected ? 'selected' : 'available'),
            secondary: passRunIds.length ? `${passRunIds.length} pass run shell${passRunIds.length === 1 ? '' : 's'}` : 'no pass run shell reported',
            badge: selection.execution_started ? 'started' : 'selected',
            live: true,
        });
    }

    persistedPassRuns.slice(0, 4).forEach((passRun) => {
        cards.push({
            label: 'Pass run',
            primary: passRun.status || 'pass run shell',
            secondary: passRun.selected_method_name || passRun.pass_scope || passRun.pass_run_id || 'method not reported',
            badge: passRun.output_payload_available ? 'output ref' : (passRun.input_payload_available ? 'input ref' : 'run'),
            live: true,
        });
    });

    if (start.state || start.pass_run_id || status.execution_started) {
        cards.push({
            label: 'Execution start',
            primary: start.pass_run_status || status.pass_run_status || start.state || 'started',
            secondary: start.analysis_run_id || status.analysis_run_id || start.pass_run_id || 'analysis run not reported',
            badge: start.output_payload_ref || status.output_payload_ref ? 'output ref' : 'started',
            live: true,
        });
    }

    if (status.pass_run_status || status.result_status_available || status.next_state) {
        cards.push({
            label: 'Result status',
            primary: status.pass_run_status || status.status || status.next_state || 'available',
            secondary: status.next_state || status.pass_run_id || 'status loaded',
            badge: status.result_status_available ? 'available' : 'status',
            live: true,
        });
    }

    if (review.review_state || review.operator_decision || review.review_record_ref) {
        cards.push({
            label: 'Result review',
            primary: review.operator_decision || review.review_state || 'review recorded',
            secondary: review.review_record_ref || 'review ref not reported',
            badge: 'review',
            live: true,
        });
    }

    const outputRef = status.output_payload_ref || start.output_payload_ref;
    if (outputRef) {
        outputs.push({
            label: 'Output payload',
            primary: status.output_metadata_summary?.readable ? 'metadata readable' : 'payload reference reported',
            secondary: outputRef,
            badge: 'payload',
        });
    }
    if (status.output_metadata_summary?.artifact_count !== undefined) {
        outputs.push({
            label: 'Output artifacts',
            primary: `${status.output_metadata_summary.artifact_count} artifact${status.output_metadata_summary.artifact_count === 1 ? '' : 's'}`,
            secondary: status.output_metadata_summary.analysis_set_id || status.output_metadata_summary.source_gate || 'metadata summary',
            badge: 'metadata',
        });
    }
    const reviewedItems = Array.isArray(review.reviewed_output_items) ? review.reviewed_output_items : [];
    reviewedItems.slice(0, 6).forEach((item, index) => {
        outputs.push({
            label: item.item_type || `Reviewed item ${index + 1}`,
            primary: item.status || item.review_status || item.title || 'reviewed output item',
            secondary: item.item_ref || item.output_ref || item.trace_ref || review.review_record_ref || 'review item',
            badge: 'reviewed',
        });
    });

    const modality = currentResultModality();
    return {
        cards,
        outputs,
        modality,
        modalityLabel: modality ? modalityMeta(modality).label : 'modality not reported',
        state: outputs.length ? 'outputs' : (cards.length ? 'active' : 'empty'),
    };
}

function outputCardsForModality(modality) {
    const cards = [];
    const resultModality = currentResultModality();
    if (!resultModality || resultModality !== modality) {
        return cards;
    }
    const status = State.resultStatus;
    const start = State.sessionSummary?.analysis_execution_start || {};
    const outputRef = status?.output_payload_ref || start.output_payload_ref;
    if (outputRef) {
        cards.push({
            label: 'Output payload',
            primary: status?.output_metadata_summary?.readable ? 'metadata readable' : 'payload reference reported',
            secondary: outputRef,
            badge: 'payload',
        });
    }
    if (status?.result_status_available || TERMINAL_PASS_STATUSES.has(status?.pass_run_status)) {
        cards.push({
            label: 'Result status',
            primary: status.pass_run_status || status.status || 'available',
            secondary: status.pass_run_id || 'pass run id not reported',
            badge: 'status',
        });
    }
    const review = recordedResultReview() || State.resultReview;
    if (review?.review_state || review?.status) {
        cards.push({
            label: 'Result review',
            primary: review.operator_decision || review.review_state || review.status,
            secondary: review.review_record_ref || 'review ref not reported',
            badge: 'review',
        });
    }
    const reviewedItems = Array.isArray(review?.reviewed_output_items) ? review.reviewed_output_items : [];
    reviewedItems.slice(0, 6).forEach((item, index) => {
        cards.push({
            label: item.item_type || `Reviewed item ${index + 1}`,
            primary: item.status || item.review_status || item.title || 'reviewed output item',
            secondary: item.item_ref || item.output_ref || item.trace_ref || review.review_record_ref || 'review item',
            badge: 'reviewed',
        });
    });
    return modality === 'unclassified' ? [] : cards;
}

function sublayerStateLabel(state) {
    const labels = {
        empty: 'Awaiting live state',
        preview: 'Preview loaded',
        session: 'Session scoped',
        typed: 'Typing previewed',
        structural: 'Structural only',
        planned: 'Plan inputs loaded',
        inputs: 'Inputs routed',
        active: 'Execution state loaded',
        outputs: 'Outputs reported',
    };
    return labels[state] || humanizeToken(state);
}

function isRoutableAnalysisObject(item) {
    const modality = normalizeModality(item?.modality);
    return Boolean(modality && modality !== 'unclassified');
}

function currentAnalysisEnvironmentProjection() {
    const projection = State.sessionSummary?.analysis_environment_projection;
    return projection && typeof projection === 'object' && !Array.isArray(projection) ? projection : null;
}

function analysisEnvironmentProjectionStatus(projection = currentAnalysisEnvironmentProjection()) {
    const schemaValid = projection?.schema_id === 'layer3.analysis_environment_projection.v1';
    const readOnly = projection?.no_side_effects === true;
    const blockedReasons = Array.isArray(projection?.blocked_reasons)
        ? projection.blocked_reasons
        : [];
    const state = schemaValid && readOnly
        ? (projection.projection_state || 'blocked')
        : 'blocked';
    const missingReasons = [];
    if (!projection) missingReasons.push('analysis_environment_projection_missing');
    if (projection && !schemaValid) missingReasons.push('analysis_environment_projection_schema_invalid');
    if (projection && !readOnly) missingReasons.push('analysis_environment_projection_not_read_only');
    return {
        available: Boolean(schemaValid && readOnly && projection?.available_for_downstream_analysis === true),
        state,
        schemaValid,
        readOnly,
        authoritySource: projection?.authority_source || 'not reported',
        blockedReasons: missingReasons.length ? missingReasons : blockedReasons,
        downstreamUnavailable: Array.isArray(projection?.downstream_unavailable)
            ? projection.downstream_unavailable
            : [],
        forbiddenRuntimeAuthority: projection?.forbidden_runtime_authority
            && typeof projection.forbidden_runtime_authority === 'object'
            && !Array.isArray(projection.forbidden_runtime_authority)
            ? projection.forbidden_runtime_authority
            : {},
    };
}

function analysisEnvironmentPlaneReadiness(modality, projection = currentAnalysisEnvironmentProjection()) {
    const readiness = Array.isArray(projection?.plane_readiness) ? projection.plane_readiness : [];
    return readiness.find((item) => item?.plane === modality) || null;
}

function currentSublayerVisualizationModel() {
    const rail = currentAuthorityRail() || {};
    const analysisEnvironmentProjection = currentAnalysisEnvironmentProjection();
    const analysisProjectionStatus = analysisEnvironmentProjectionStatus(analysisEnvironmentProjection);
    const materialObjects = currentMaterialObjects();
    const typingObjects = currentTypingObjects();
    const planObjects = currentPlanSetObjects();
    const persistedAnalysisSetObjects = currentPersistedAnalysisSetObjects();
    const typedGroups = groupedByModality(typingObjects);
    const planGroups = groupedByModality(planObjects);
    const analysisSetGroups = groupedByModality(persistedAnalysisSetObjects);
    const plannedPasses = currentPlannedPasses();
    const executionPipeline = currentExecutionPipeline();
    const hasSessionScope = Boolean(State.gateB?.session_id || (rail.session_id && rail.session_id !== 'none'));
    const hasOutputs = SUBLAYER_MODALITIES.some((modality) => outputCardsForModality(modality).length > 0);
    const hasExecutionState = executionPipeline.cards.length > 0 || executionPipeline.outputs.length > 0;
    const hasRoutedInputs = typingObjects.some(isRoutableAnalysisObject)
        || persistedAnalysisSetObjects.some(isRoutableAnalysisObject);
    const threeAState = materialObjects.length ? (hasSessionScope ? 'session' : 'preview') : 'empty';
    const threeBState = typingObjects.length ? 'typed' : 'empty';
    const threeCState = hasOutputs ? 'outputs' : (planObjects.length || plannedPasses.length ? 'planned' : (hasExecutionState ? 'active' : (hasRoutedInputs ? 'inputs' : 'structural')));

    const gateBMessage = materialObjects.length
        ? (
            hasSessionScope
                ? 'Session-scoped material objects are represented from the current material preview, Gate B response, or authority rail.'
                : 'Source-plane material preview candidates are loaded; Gate B has not committed them into session state yet.'
        )
        : 'No source-plane material is loaded yet. Run Preflight to request material preview.';
    const gateCMessage = typingObjects.length
        ? 'Gate C typing objects are grouped by repo-reported modality.'
        : 'No Gate C typing state is loaded yet. Commit Gate B and preview Gate C to classify material.';
    const planeIntro = hasExecutionState
        ? '3C reflects the currently selected execution/result authority where the session summary or status endpoint reports it.'
        : (planObjects.length || plannedPasses.length
        ? '3C planes are populated from plan preview or approved-plan state where available.'
        : (hasRoutedInputs
            ? '3C planes show Gate C input objects where persisted typing or analysis-set state is available; process/output zones remain neutral until plan or execution state exists.'
            : '3C planes are structural and neutral until plan preview, approval, execution, or result status reports live data.'));

    const modalityBuckets = SUBLAYER_MODALITIES.map((modality) => {
        const objects = typedGroups[modality] || [];
        return {
            modality,
            meta: modalityMeta(modality),
            objects,
            state: objects.length ? 'loaded' : 'empty',
        };
    });

    const analysisPlanes = SUBLAYER_MODALITIES
        .filter((modality) => modality !== 'unclassified')
        .map((modality) => {
            const inputs = (planGroups[modality] || []).length
                ? planGroups[modality]
                : ((analysisSetGroups[modality] || []).length ? analysisSetGroups[modality] : (typedGroups[modality] || []));
            const passes = planPassesForModality(modality);
            const outputs = outputCardsForModality(modality);
            const processCards = executionPipeline.modality === modality ? executionPipeline.cards : [];
            return {
                modality,
                meta: modalityMeta(modality),
                inputs,
                passes,
                processCards,
                outputs,
                analysisEnvironmentProjectionStatus: analysisProjectionStatus,
                analysisEnvironmentPlaneReadiness: analysisEnvironmentPlaneReadiness(
                    modality,
                    analysisEnvironmentProjection
                ),
                state: outputs.length ? 'outputs' : (passes.length || inputs.length ? 'inputs' : 'empty'),
            };
        });

    return {
        rail,
        intentText: currentIntentText(),
        sourceLabels: selectedSourceClassLabels(),
        threeA: {
            state: threeAState,
            stateLabel: sublayerStateLabel(threeAState),
            objects: materialObjects,
            message: gateBMessage,
        },
        threeB: {
            state: threeBState,
            stateLabel: sublayerStateLabel(threeBState),
            buckets: modalityBuckets,
            message: gateCMessage,
        },
        threeC: {
            state: threeCState,
            stateLabel: sublayerStateLabel(threeCState),
            planes: analysisPlanes,
            executionPipeline,
            message: planeIntro,
            analysisEnvironmentProjectionStatus: analysisProjectionStatus,
        },
    };
}

function renderFlowObjects(items, emptyMessage, options = {}) {
    const fieldLabel = options.fieldLabel || 'Object field';
    const slotCount = options.slotCount || 4;
    const ghostSlotCount = Math.max(0, slotCount - items.length);
    if (!items.length) {
        return `
            <div class="flow-empty diagram-empty" data-field-label="${escapeHtml(fieldLabel)}">
                <div class="empty-slot-field" aria-hidden="true">
                    ${Array.from({ length: slotCount }).map(() => '<span class="empty-slot"></span>').join('')}
                </div>
                <p>${escapeHtml(emptyMessage)}</p>
            </div>
        `;
    }
    return `
        <div class="flow-object-list diagram-chip-grid" data-field-label="${escapeHtml(fieldLabel)}" data-object-count="${items.length}" data-slot-count="${escapeHtml(slotCount)}">
            ${items.map((item) => {
                const modality = item.modality || 'unclassified';
                const meta = modalityMeta(modality);
                const label = shortText(item.label || item.id, 32);
                const primary = shortText(item.primary || 'No detail reported', 34);
                const ref = shortText(item.id, 22);
                const chipTitle = [
                    item.label || item.id,
                    item.primary,
                    item.id,
                ].filter(Boolean).join(' / ');
                return `
                    <article class="flow-object diagram-chip modality-${escapeHtml(modality)}" data-live-backed="${item.live ? 'true' : 'false'}" title="${escapeHtml(chipTitle)}">
                        <div class="flow-object-head">
                            <span>${escapeHtml(humanizeToken(item.kind || meta.label))}</span>
                            <span class="flow-object-badge">${escapeHtml(humanizeToken(item.badge || 'reported'))}</span>
                        </div>
                        <strong>${escapeHtml(label)}</strong>
                        <span>${escapeHtml(primary)}</span>
                        <code>${escapeHtml(ref)}</code>
                    </article>
                `;
            }).join('')}
            ${Array.from({ length: ghostSlotCount }).map(() => '<span class="flow-slot-ghost" aria-hidden="true"></span>').join('')}
        </div>
    `;
}

function renderModalityBucket(bucket) {
    const { modality, meta, objects, state } = bucket;
    const transferState = modality === 'unclassified' ? 'held' : (objects.length ? 'ready' : 'empty');
    const transferLabel = modality === 'unclassified'
        ? 'Held in 3B'
        : (objects.length ? 'Feeds 3C plane' : 'Awaiting objects');
    return `
        <section class="modality-bucket modality-${escapeHtml(modality)} viz-state-${escapeHtml(state)}" aria-label="${escapeHtml(meta.label)}" data-modality="${escapeHtml(modality)}" data-object-count="${objects.length}">
            <div class="modality-heading">
                <span class="modality-dot" aria-hidden="true"></span>
                <h4>${escapeHtml(meta.label)}</h4>
                <span>${objects.length} objects</span>
            </div>
            <div class="modality-route-label" aria-hidden="true">Object bank / grouping field</div>
            <span class="modality-transfer-rail" data-transfer-state="${escapeHtml(transferState)}">${escapeHtml(transferLabel)}</span>
            <div class="modality-bank-shell" data-diagram-role="modality-object-bank">
                <span class="modality-bank-bracket" aria-hidden="true"></span>
                ${renderFlowObjects(objects, meta.empty, { fieldLabel: `${meta.label} object bank`, slotCount: 3 })}
            </div>
        </section>
    `;
}

function renderExecutionPipeline(pipeline) {
    const processRows = pipeline.cards.length
        ? pipeline.cards.map((card) => `
            <li>
                <strong>${escapeHtml(card.label)}</strong>
                <span>${escapeHtml(shortText(card.primary, 54))}</span>
                <code>${escapeHtml(shortText(card.secondary, 42))}</code>
                <em>${escapeHtml(humanizeToken(card.badge || 'live'))}</em>
            </li>
        `).join('')
        : `
            <li>
                <strong>No selected execution state</strong>
                <span>Execution selection, start, result status, and review state are not loaded into this session view.</span>
            </li>
        `;
    const outputObjects = pipeline.outputs.map((item) => ({
        id: item.secondary,
        label: item.label,
        kind: 'execution output',
        primary: item.primary,
        badge: item.badge,
        modality: pipeline.modality || 'unclassified',
        live: true,
    }));
    return `
        <section class="execution-state-field viz-state-${escapeHtml(pipeline.state)}" data-execution-modality="${escapeHtml(pipeline.modality || 'unreported')}">
            <div class="execution-state-heading">
                <span>Selected execution / result authority</span>
                <strong>${escapeHtml(pipeline.modalityLabel)}</strong>
            </div>
            <div class="execution-state-flow">
                <section class="execution-state-process">
                    <h5>Process state</h5>
                    <ul>${processRows}</ul>
                </section>
                <span class="plane-arrow plane-arrow-output" aria-hidden="true"></span>
                <section class="execution-state-outputs">
                    <h5>Live output refs</h5>
                    ${renderFlowObjects(outputObjects, 'No execution output reference or reviewed output item is loaded.', { fieldLabel: 'selected execution output field', slotCount: 5 })}
                </section>
            </div>
        </section>
    `;
}

function renderAnalysisEnvironmentProjectionStatus(status, readiness, modality) {
    const blockedReasons = status.blockedReasons.length
        ? status.blockedReasons
        : ['no projection blockers reported'];
    const downstreamUnavailable = status.downstreamUnavailable.length
        ? status.downstreamUnavailable
        : ['none reported'];
    const forbiddenAuthority = status.forbiddenRuntimeAuthority || {};
    const forbiddenLabels = Object.entries(forbiddenAuthority)
        .filter(([, value]) => value === false)
        .map(([key]) => humanizeToken(key));
    const readinessState = readiness?.state || 'not reported';
    const counts = [
        ['typing', readiness?.typing_record_count],
        ['sets', readiness?.analysis_set_count],
        ['runs', readiness?.pass_run_count],
        ['outputs', readiness?.output_payload_count],
    ]
        .filter(([, value]) => Number.isFinite(Number(value)))
        .map(([label, value]) => `${label} ${value}`)
        .join(' / ');
    return `
        <section class="analysis-environment-projection" data-projection-state="${escapeHtml(status.state)}" data-projection-available="${status.available ? 'true' : 'false'}" data-schema-valid="${status.schemaValid ? 'true' : 'false'}" data-read-only="${status.readOnly ? 'true' : 'false'}" aria-label="${escapeHtml(modalityMeta(modality).label)} downstream Analysis Environment projection">
            <div class="analysis-environment-projection-head">
                <span>Server projection</span>
                <strong>${escapeHtml(humanizeToken(status.state))}</strong>
                <em>${escapeHtml(status.available ? 'downstream ready' : 'read-only blocked')}</em>
            </div>
            <dl>
                <div>
                    <dt>Plane readiness</dt>
                    <dd>${escapeHtml(humanizeToken(readinessState))}${counts ? ` / ${escapeHtml(counts)}` : ''}</dd>
                </div>
                <div>
                    <dt>Authority</dt>
                    <dd>${escapeHtml(shortText(status.authoritySource, 54))}</dd>
                </div>
                <div>
                    <dt>Blocked reasons</dt>
                    <dd>${escapeHtml(shortText(blockedReasons.join(', '), 72))}</dd>
                </div>
                <div>
                    <dt>Downstream unavailable</dt>
                    <dd>${escapeHtml(shortText(downstreamUnavailable.join(', '), 72))}</dd>
                </div>
                <div>
                    <dt>Forbidden runtime</dt>
                    <dd>${escapeHtml(shortText(forbiddenLabels.length ? forbiddenLabels.join(', ') : 'not reported', 72))}</dd>
                </div>
            </dl>
        </section>
    `;
}

function renderAnalysisPlane(plane) {
    const {
        modality,
        meta,
        inputs,
        passes,
        processCards,
        outputs,
        state,
        analysisEnvironmentProjectionStatus,
        analysisEnvironmentPlaneReadiness,
    } = plane;
    const passRows = passes.map((pass) => `
            <li>
                <strong>${escapeHtml(humanizeToken(pass.pass_type || pass.method_family || 'planned pass'))}</strong>
                <span>${escapeHtml(shortText(pass.selected_method_name || pass.method_family || pass.pass_scope || 'method not reported', 52))}</span>
                <em>${escapeHtml(pass.approval_only ? 'approval only' : (pass.execution_mode || pass.status || 'planned'))}</em>
            </li>
        `).join('');
    const liveRows = (processCards || []).map((card) => `
                <li>
                    <strong>${escapeHtml(card.label)}</strong>
                    <span>${escapeHtml(shortText(card.primary, 52))}</span>
                    <em>${escapeHtml(humanizeToken(card.badge || 'live'))}</em>
                </li>
            `).join('');
    const processBody = passRows || liveRows
        ? `${passRows}${liveRows}`
        : '<li><strong>No live process yet</strong><span>Plan preview or approval has not reported a pass for this plane.</span></li>';
    return `
        <article class="analysis-plane modality-${escapeHtml(modality)} viz-state-${escapeHtml(state)}" data-modality="${escapeHtml(modality)}">
            <div class="analysis-plane-title">
                <span class="modality-dot" aria-hidden="true"></span>
                <h4>${escapeHtml(meta.plane)}</h4>
                <span class="plane-state-label">${escapeHtml(sublayerStateLabel(state))}</span>
            </div>
            ${renderAnalysisEnvironmentProjectionStatus(
                analysisEnvironmentProjectionStatus,
                analysisEnvironmentPlaneReadiness,
                modality
            )}
            <div class="plane-flow-frame" data-plane-role="analysis-environment-lane">
                <span class="plane-lane-spine" aria-hidden="true"></span>
                <span class="plane-lane-bracket" aria-hidden="true"></span>
                <div class="plane-flow">
                    <section class="plane-column plane-inputs plane-field-node plane-input-bank" data-plane-role="input-bank">
                        <h5>Input Object Bank</h5>
                        <div class="plane-input-group">
                            <span class="plane-bracket" aria-hidden="true"></span>
                            ${renderFlowObjects(inputs, 'No live input object is available for this plane.', { fieldLabel: `${meta.label} input objects`, slotCount: 3 })}
                        </div>
                    </section>
                    <span class="plane-arrow plane-arrow-process" aria-hidden="true"></span>
                    <section class="plane-process plane-field-node plane-process-node" data-plane-role="process-status" aria-label="${escapeHtml(meta.plane)} process status">
                        <h5>Process / Status</h5>
                        <ul>${processBody}</ul>
                    </section>
                    <span class="plane-arrow plane-arrow-output" aria-hidden="true"></span>
                    <section class="plane-column plane-outputs plane-field-node plane-output-field" data-plane-role="output-field">
                        <h5>Output / Result Field</h5>
                        ${renderFlowObjects(outputs.map((card) => ({
                            id: card.secondary,
                            label: card.label,
                            kind: 'output field',
                            primary: card.primary,
                            secondary: card.secondary,
                            badge: card.badge,
                            modality,
                            live: true,
                        })), 'No live output, insight, fact, or data item has been produced for this plane.', { fieldLabel: `${meta.label} generated output field`, slotCount: 6 })}
                    </section>
                </div>
            </div>
        </article>
    `;
}

function renderSourceFamilySummary(summary) {
    if (!summary) return '';
    const admitted = Array.isArray(summary.admitted_materialized_families)
        ? summary.admitted_materialized_families
        : [];
    const deferred = Array.isArray(summary.not_admitted_or_deferred_families)
        ? summary.not_admitted_or_deferred_families
        : [];
    const observed = summary.observed_candidate_counts || {};
    const admittedRows = admitted.map((family) => {
        const parserFamily = family.parser_family || family.source_family || 'unknown';
        const observedCount = observed[parserFamily] || 0;
        return `
            <li>
                <strong>${escapeHtml(family.source_family_label || parserFamily)}</strong>
                <span>${escapeHtml(family.scope || family.admission_state || 'server-backed dataset_version selection')}</span>
                <em>${escapeHtml(observedCount ? `${observedCount} candidate${observedCount === 1 ? '' : 's'}` : 'no candidates loaded')}</em>
            </li>
        `;
    }).join('');
    const deferredRows = deferred.map((family) => `
            <li>
                <strong>${escapeHtml(family.source_family_label || family.source_family || 'Deferred source family')}</strong>
                <span>${escapeHtml(family.scope || family.admission_state || 'not admitted')}</span>
                <em>${escapeHtml(humanizeToken(family.admission_state || 'deferred'))}</em>
            </li>
        `).join('');
    return `
        <section class="source-family-summary" aria-label="APS typed and refused source family boundary">
            <div>
                <span class="source-family-kicker">Server-backed typed families</span>
                <ul>${admittedRows || '<li><strong>No admitted table families reported</strong><span>Candidate endpoint did not report admitted families.</span></li>'}</ul>
            </div>
            <div>
                <span class="source-family-kicker">Deferred / refused guardrails</span>
                <ul>${deferredRows || '<li><strong>No deferred families reported</strong><span>Candidate endpoint did not report refusal guardrails.</span></li>'}</ul>
            </div>
            <p>${escapeHtml(summary.ui_scope || 'Only materialized APS-derived DatasetVersion records are selectable here.')}</p>
        </section>
    `;
}

function renderRawMixedMaterializationPanel() {
    if (!elements.rawMixedMaterializationStatus || !elements.rawMixedMaterializationState) return;
    const materialization = State.rawMixedMaterialization;
    if (State.rawMixedMaterializationPending) {
        elements.rawMixedMaterializationState.textContent = 'Materializing';
        elements.rawMixedMaterializationState.className = 'status-pill preview';
        elements.rawMixedMaterializationStatus.textContent = 'Materialization request is in flight.';
        return;
    }
    if (State.rawMixedMaterializationError) {
        elements.rawMixedMaterializationState.textContent = 'Blocked';
        elements.rawMixedMaterializationState.className = 'status-pill blocked';
        elements.rawMixedMaterializationStatus.textContent = State.rawMixedMaterializationError.message
            || State.rawMixedMaterializationError.error_code
            || 'Materialization failed closed.';
        return;
    }
    if (materialization) {
        const datasetCount = (materialization.dataset_version_ids || []).length;
        const contentCount = (materialization.aps_content_document_ids || []).length;
        elements.rawMixedMaterializationState.textContent = 'Materialized';
        elements.rawMixedMaterializationState.className = 'status-pill ok';
        elements.rawMixedMaterializationStatus.textContent = `${datasetCount} DatasetVersion ID${datasetCount === 1 ? '' : 's'} and ${contentCount} APS content document ID${contentCount === 1 ? '' : 's'} selected after candidate refresh.`;
        return;
    }
    const form = rawMixedMaterializationFormState();
    const ready = canMaterializeRawMixed();
    elements.rawMixedMaterializationState.textContent = ready ? 'Ready' : 'Not materialized';
    elements.rawMixedMaterializationState.className = ready ? 'status-pill ok' : 'status-pill preview';
    if (form.requestedSourceClasses.length !== RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES.size) {
        elements.rawMixedMaterializationStatus.textContent = 'Select both Dataset version and APS content document source classes.';
    } else if (!form.corpusBatchId || !form.manifestRef || !form.manifestHash || !form.operatorConfirmed) {
        elements.rawMixedMaterializationStatus.textContent = 'Awaiting server-owned manifest authority.';
    } else {
        elements.rawMixedMaterializationStatus.textContent = 'Ready to call the server-owned materialization route.';
    }
}

function renderDatasetVersionCandidates() {
    if (!elements.datasetVersionCandidates) return;
    const summaryMarkup = renderSourceFamilySummary(State.datasetVersionCandidates?.source_family_summary);
    if (State.datasetVersionCandidateError) {
        elements.datasetVersionCandidates.innerHTML = `
            ${summaryMarkup}
            <span class="dataset-version-empty">DatasetVersion candidate lookup failed: ${escapeHtml(State.datasetVersionCandidateError)}</span>
        `;
        return;
    }
    const candidates = State.datasetVersionCandidates?.dataset_version_candidates || [];
    const selectedIds = new Set(selectedDatasetVersionIds());
    if (!candidates.length) {
        elements.datasetVersionCandidates.innerHTML = `
            ${summaryMarkup}
            <span class="dataset-version-empty">No server-backed materialized dataset versions were found in the active runtime. Paste explicit IDs if you have them from a materialization report.</span>
        `;
        return;
    }
    const candidateMarkup = candidates.map((candidate) => {
        const datasetVersionId = String(candidate.dataset_version_id || '');
        const title = candidate.dataset_name || candidate.version_label || datasetVersionId;
        const detail = [
            candidate.source_family_label,
            candidate.source_admission_state ? humanizeToken(candidate.source_admission_state) : null,
            candidate.version_type,
            candidate.parser_family,
            candidate.typed_content_contract_id,
            candidate.row_count != null ? `${candidate.row_count} rows` : null,
            candidate.variable_count != null ? `${candidate.variable_count} variables` : null,
        ].filter(Boolean).join(' / ');
        return `
            <label class="dataset-version-candidate">
                <input type="checkbox" name="dataset-version-candidate" value="${escapeHtml(datasetVersionId)}" ${selectedIds.has(datasetVersionId) ? 'checked' : ''}>
                <span>
                    <strong>${escapeHtml(title)}</strong>
                    <code>${escapeHtml(datasetVersionId)}</code>
                    <span>${escapeHtml(detail || 'APS-derived dataset version')}</span>
                    ${candidate.source_family_scope ? `<small>${escapeHtml(candidate.source_family_scope)}</small>` : ''}
                </span>
            </label>
        `;
    }).join('');
    elements.datasetVersionCandidates.innerHTML = `${summaryMarkup}${candidateMarkup}`;
}

function renderApsContentDocumentCandidates() {
    if (!elements.apsContentDocumentCandidates) return;
    if (State.apsContentDocumentCandidateError) {
        elements.apsContentDocumentCandidates.innerHTML = `
            <span class="aps-content-document-empty">APS content document lookup failed: ${escapeHtml(State.apsContentDocumentCandidateError)}</span>
        `;
        return;
    }
    const candidates = State.apsContentDocumentCandidates?.aps_content_document_candidates || [];
    const selectedIds = new Set(selectedApsContentDocumentIds());
    if (!candidates.length) {
        elements.apsContentDocumentCandidates.innerHTML = `
            <span class="aps-content-document-empty">No indexed APS content documents were found in the active runtime. Paste explicit content IDs if you have them from an APS content report.</span>
        `;
        return;
    }
    elements.apsContentDocumentCandidates.innerHTML = candidates.map((candidate) => {
        const contentId = String(candidate.content_id || '');
        const title = candidate.accession_number || candidate.document_class || contentId;
        const detail = [
            candidate.source_family_label,
            candidate.source_admission_state ? humanizeToken(candidate.source_admission_state) : null,
            candidate.media_type,
            candidate.document_class,
            candidate.content_contract_id,
            candidate.chunk_count != null ? `${candidate.chunk_count} chunks` : null,
            candidate.page_count != null ? `${candidate.page_count} pages` : null,
        ].filter(Boolean).join(' / ');
        return `
            <label class="aps-content-document-candidate">
                <input type="checkbox" name="aps-content-document-candidate" value="${escapeHtml(contentId)}" ${selectedIds.has(contentId) ? 'checked' : ''}>
                <span>
                    <strong>${escapeHtml(title)}</strong>
                    <code>${escapeHtml(contentId)}</code>
                    <span>${escapeHtml(detail || 'Indexed APS content document')}</span>
                    ${candidate.source_family_scope ? `<small>${escapeHtml(candidate.source_family_scope)}</small>` : ''}
                </span>
            </label>
        `;
    }).join('');
}

function renderSublayerMap() {
    if (!elements.sublayerMapPanel) return;
    const model = currentSublayerVisualizationModel();
    const rail = model.rail;
    const sourceLabels = model.sourceLabels;
    const activeOperation = OPERATION_DOCK_STEPS.find((step) => step.id === State.activeOperationId);

    elements.sublayerMapPanel.dataset.vizState = `${model.threeA.state}|${model.threeB.state}|${model.threeC.state}`;
    elements.sublayerMapPanel.dataset.activeOperationCanvas = activeOperation?.canvasTarget || '3a';
    elements.sublayerMapPanel.dataset.activeOperationKey = activeOperation?.key || 'intent';
    elements.sublayerMapPanel.innerHTML = `
        <section class="canvas-intake-spec" aria-label="Layer 3 intake specification">
            <div class="intake-spec-frame">
                <article class="query-spec-block">
                    <span>User Natural Language Query Input</span>
                    <p>${escapeHtml(shortText(model.intentText, 170))}</p>
                </article>
                <article class="manual-source-spec">
                    <span>User Manual / Custom Source Specification</span>
                    <div class="source-spec-chip-grid">
                        ${sourceLabels.length
                            ? sourceLabels.map((label) => `<span class="source-spec-chip">${escapeHtml(label)}</span>`).join('')
                            : '<span class="source-spec-chip muted">No source classes selected</span>'}
                    </div>
                </article>
            </div>
        </section>
        <section class="workflow-canvas-field" aria-label="Layer 3 3A to 3B to 3C workflow canvas">
            <nav class="canvas-state-flow" aria-label="Layer 3 visualization state">
                <span class="state-node state-3a viz-state-${escapeHtml(model.threeA.state)}">
                    <strong>3A</strong>
                    <span>${escapeHtml(model.threeA.stateLabel)}</span>
                </span>
                <span class="state-flow-link" aria-hidden="true"></span>
                <span class="state-node state-3b viz-state-${escapeHtml(model.threeB.state)}">
                    <strong>3B</strong>
                    <span>${escapeHtml(model.threeB.stateLabel)}</span>
                </span>
                <span class="state-flow-link" aria-hidden="true"></span>
                <span class="state-node state-3c viz-state-${escapeHtml(model.threeC.state)}">
                    <strong>3C</strong>
                    <span>${escapeHtml(model.threeC.stateLabel)}</span>
                </span>
            </nav>
            <section class="sublayer-region sublayer-3a viz-state-${escapeHtml(model.threeA.state)}" aria-label="Sublayer 3A material intake and session scoping">
                <div class="sublayer-title">
                    <span>Sublayer 3A</span>
                    <strong>Material Intake &amp; Session Scoping</strong>
                    <em>${escapeHtml(model.threeA.stateLabel)}</em>
                </div>
                <div class="gate-panel diagram-gate">
                    <h3>Gate B / Session Entry / Material Ledger</h3>
                    <p>${escapeHtml(model.threeA.message)}</p>
                    <div class="mini-rail">
                        <span>Session ${escapeHtml(shortText(rail.session_id || 'none', 24))}</span>
                        <span>Approved ${escapeHtml(rail.approved_material_count ?? 0)}</span>
                        <span>Denied ${escapeHtml(rail.denied_material_count ?? 0)}</span>
                        <span>Typing ${escapeHtml(rail.typing_status || 'not_started')}</span>
                    </div>
                </div>
                <div class="ledger-chip-field">
                    <div class="ledger-bracket"><span>Session-scoped Materials / Material Snapshots</span></div>
                    <div class="material-bank-shell" data-diagram-role="source-plane-material-field">
                        <span class="material-bank-bracket" aria-hidden="true"></span>
                        ${renderFlowObjects(model.threeA.objects, 'No material preview, session entry, or material ledger object is currently loaded.', { fieldLabel: '3A material ledger object field', slotCount: 6 })}
                    </div>
                </div>
            </section>
            <div class="sublayer-connector sublayer-connector-3ab" aria-hidden="true"><span>3A to 3B</span></div>
            <section class="analysis-routing-plane" aria-label="Sublayer 3B to 3C analysis routing">
                <section class="sublayer-region sublayer-3b viz-state-${escapeHtml(model.threeB.state)}" aria-label="Sublayer 3B typing and set formation">
                    <div class="sublayer-title">
                        <span>Sublayer 3B</span>
                        <strong>Typing, Unit/Group/Set Formation</strong>
                        <em>${escapeHtml(model.threeB.stateLabel)}</em>
                    </div>
                    <div class="gate-panel diagram-gate">
                        <h3>Gate C Typing</h3>
                        <p>${escapeHtml(model.threeB.message)}</p>
                    </div>
                    <div class="modality-bank-field">
                        <div class="field-bracket modality-field-bracket"><span>Modality Object Banks / Ingress Containers</span></div>
                        <div class="modality-buckets">
                            ${model.threeB.buckets.map((bucket) => renderModalityBucket(bucket)).join('')}
                        </div>
                    </div>
                </section>
                <div class="sublayer-connector sublayer-connector-3bc" aria-hidden="true"><span>3B to 3C</span></div>
                <section class="sublayer-region sublayer-3c viz-state-${escapeHtml(model.threeC.state)}" aria-label="Sublayer 3C analysis execution environments">
                    <div class="sublayer-title">
                        <span>Sublayer 3C</span>
                        <strong>Analysis Execution Environments / Planes</strong>
                        <em>${escapeHtml(model.threeC.stateLabel)}</em>
                    </div>
                    <div class="gate-panel diagram-gate">
                        <h3>Input To Process To Output</h3>
                        <p>${escapeHtml(model.threeC.message)}</p>
                    </div>
                    ${renderExecutionPipeline(model.threeC.executionPipeline)}
                    <div class="analysis-plane-field">
                        <div class="field-bracket analysis-field-bracket"><span>Analysis Environment Planes / Input To Output Fields</span></div>
                        <div class="analysis-lane-legend" aria-hidden="true">
                            <span class="analysis-lane-label lane-label-input">Input object bank</span>
                            <span class="analysis-lane-arrow">route</span>
                            <span class="analysis-lane-label lane-label-process">Process / status</span>
                            <span class="analysis-lane-arrow">produce</span>
                            <span class="analysis-lane-label lane-label-output">Output field</span>
                        </div>
                        <div class="analysis-planes">
                            ${model.threeC.planes.map((plane) => renderAnalysisPlane(plane)).join('')}
                        </div>
                    </div>
                </section>
            </section>
        </section>
    `;
}

function renderMaterialTrace(candidate) {
    const trace = candidate.source_trace || candidate.source_provenance?.source_trace;
    if (!trace) {
        return '<div class="material-trace-card material-trace-empty">No server trace detail.</div>';
    }
    const refs = trace.aps_trace_refs || {};
    const variables = trace.variable_summary || {};
    const storage = trace.storage_summary || {};
    const documentIdentity = trace.document_identity || {};
    const chunks = trace.chunk_summary || {};
    const numericVariables = Array.isArray(variables.numeric_variables)
        ? variables.numeric_variables
        : [];
    const timeVariables = Array.isArray(variables.time_variables)
        ? variables.time_variables
        : [];
    const detailRows = [
        ['family', trace.source_family_label || trace.source_family],
        ['readiness', trace.trace_readiness],
        ['parser', refs.parser_family],
        ['contract', refs.typed_content_contract_id || refs.parser_contract_id || documentIdentity.content_contract_id],
        ['content', documentIdentity.content_id],
        ['chunking', documentIdentity.chunking_contract_id],
        ['target', refs.target_id],
        ['accession', refs.accession_number],
        ['rows', storage.row_count],
        ['chunks', chunks.loaded_chunk_count ?? chunks.chunk_count],
        ['pages', chunks.page_count],
        ['media', documentIdentity.media_type],
        ['class', documentIdentity.document_class],
        ['variables', variables.variable_count],
        ['numeric', numericVariables.join(', ')],
        ['time', variables.time_column || timeVariables.join(', ')],
        ['units', refs.content_units_ref],
        ['blob', refs.blob_ref],
        ['diagnostics', refs.diagnostics_ref],
    ].filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '');
    return `
        <div class="material-trace-card" data-trace-readiness="${escapeHtml(trace.trace_readiness || 'unknown')}">
            <strong>${escapeHtml(trace.source_family_label || 'DatasetVersion trace')}</strong>
            <span>${escapeHtml(trace.ui_summary || trace.source_family_scope || 'Server trace detail available.')}</span>
            <dl>
                ${detailRows.map(([label, value]) => `
                    <div>
                        <dt>${escapeHtml(label)}</dt>
                        <dd>${escapeHtml(shortText(value, 48))}</dd>
                    </div>
                `).join('')}
            </dl>
        </div>
    `;
}

function renderMaterialLedger() {
    const candidates = State.materialPreview?.material_candidates || [];
    const filter = State.materialFilter.trim().toLowerCase();
    const visible = filter
        ? candidates.filter((candidate) => candidateSearchText(candidate).includes(filter))
        : candidates;
    if (!visible.length) {
        const message = candidates.length ? 'No material candidates match the filter.' : 'No material preview loaded.';
        elements.materialLedgerBody.innerHTML = `<tr><td colspan="7" class="empty-cell">${escapeHtml(message)}</td></tr>`;
        return;
    }
    elements.materialLedgerBody.innerHTML = visible.map((candidate) => {
        const currentDecision = decisionState(candidate.candidate_id);
        const traceMarkup = renderMaterialTrace(candidate);
        return `
        <tr data-candidate-id="${escapeHtml(candidate.candidate_id)}">
            <td>
                <div class="candidate-id">${escapeHtml(candidate.candidate_id)}</div>
                <span class="source-badge">${escapeHtml(candidate.validation_status)}</span>
            </td>
            <td>${escapeHtml(candidate.source_label)}</td>
            <td>
                <div>${escapeHtml(candidate.owner_service_source_shape)}</div>
                <div class="rail-label">${escapeHtml(candidate.planning_shape_family)}</div>
            </td>
            <td>${traceMarkup}</td>
            <td>
                <div>${escapeHtml(candidate.duplicate_status)}</div>
                <div class="rail-label">${escapeHtml(candidate.query_basis)}</div>
            </td>
            <td>
                <select class="decision-select" aria-label="Decision for ${escapeHtml(candidate.candidate_id)}">
                    <option value="approved" ${currentDecision.decision === 'approved' ? 'selected' : ''}>Approved</option>
                    <option value="denied" ${currentDecision.decision === 'denied' ? 'selected' : ''}>Denied</option>
                    <option value="isolated" ${currentDecision.decision === 'isolated' ? 'selected' : ''}>Isolated</option>
                    <option value="flagged" ${currentDecision.decision === 'flagged' ? 'selected' : ''}>Flagged</option>
                </select>
            </td>
            <td>
                <input class="reason-input" type="text" value="${escapeHtml(currentDecision.operator_reason)}" placeholder="Required for denied, isolated, or flagged">
            </td>
        </tr>
    `;
    }).join('');
}

function materialCandidateById(candidateId) {
    return (State.materialPreview?.material_candidates || [])
        .find((candidate) => candidate.candidate_id === candidateId);
}

function initializeGateBDecisions() {
    State.gateBDecisions = {};
    State.gateBClientRequestId = null;
    for (const candidate of State.materialPreview?.material_candidates || []) {
        State.gateBDecisions[candidate.candidate_id] = {
            decision: 'approved',
            operator_reason: '',
        };
    }
    if (!restoreGateBDraftSnapshot()) {
        persistGateBDraftSnapshot();
    }
}

function collectGateBDecisions() {
    return (State.materialPreview?.material_candidates || []).map((candidate) => {
        const currentDecision = decisionState(candidate.candidate_id);
        return {
            candidate_id: candidate.candidate_id,
            decision: currentDecision.decision,
            operator_reason: currentDecision.operator_reason,
            decision_basis: {
                source_ref: candidate.source_ref,
                query_basis: candidate.query_basis,
                provenance_ref: candidate.provenance_ref,
                source_identity: candidate.source_identity || {},
                source_provenance: candidate.source_provenance || {},
                payload: candidate.payload || {},
                load_summary: candidate.load_summary || {},
                owner_service_source_shape: candidate.owner_service_source_shape,
                planning_shape_family: candidate.planning_shape_family,
            },
        };
    });
}

function renderGateCPanel() {
    const records = State.gateC?.typing_records || [];
    const unsupported = State.gateC?.unsupported_material || [];
    if (!records.length && !unsupported.length) {
        elements.gateCPanel.innerHTML = '<div class="empty-panel">No committed Gate B session yet.</div>';
        return;
    }
    const cards = records.map((record) => `
        <article class="typing-card">
            <h3>${escapeHtml(record.planning_shape_family)}</h3>
            <div class="typing-meta">
                <span>Snapshot: ${escapeHtml(record.material_snapshot_id)}</span>
                <span>Shape: ${escapeHtml(record.owner_service_source_shape)}</span>
                <span>Modality: ${escapeHtml(record.chosen_modality)}</span>
                <span>Confidence: ${escapeHtml(record.confidence)}</span>
                <span>Authoritative: ${record.authoritative ? 'yes' : 'no'}</span>
            </div>
        </article>
    `);
    const unsupportedRows = unsupported.map((item) => `
        <article class="typing-card">
            <h3>Unsupported Material</h3>
            <div class="typing-meta">
                <span>Snapshot: ${escapeHtml(item.material_snapshot_id)}</span>
                <span>Shape: ${escapeHtml(item.owner_service_source_shape)}</span>
                <span>Reason: ${escapeHtml(item.reason)}</span>
            </div>
        </article>
    `);
    elements.gateCPanel.innerHTML = [...cards, ...unsupportedRows].join('');
}

function canPlanPreview() {
    return Boolean(currentSessionId() && isTypingCommitted());
}

function canPlanApprove() {
    return Boolean(
        currentSessionId()
        && State.planPreview?.schema_id === 'layer3.plan_preview_result.v1'
        && State.planPreview?.preview_id
        && State.planPreview?.preview_hash
        && !State.planApproval
        && !State.planRevision
        && !State.planRevisionPending
    );
}

function canPlanRevise() {
    return Boolean(
        currentSessionId()
        && State.planPreview?.schema_id === 'layer3.plan_preview_result.v1'
        && State.planPreview?.preview_id
        && State.planPreview?.preview_hash
        && !State.planApproval
        && !State.planRevision
        && !State.planRevisionPending
    );
}

function canSelectExecution() {
    const authority = executionPlanAuthority();
    const selection = executionSelectionState();
    return Boolean(
        currentSessionId()
        && authority.analysisPlanId
        && authority.previewId
        && authority.previewHash
        && (
            State.planApproval?.analysis_plan_id
            || State.sessionSummary?.execution_selection?.available === true
        )
        && !State.planRevision
        && !State.planRevisionPending
        && !State.executionSelection
        && selection.selected !== true
        && !State.executionSelectionPending
        && !State.executionStartPending
    );
}

function canStartExecution() {
    const selection = executionSelectionState();
    const start = executionStartState();
    const authority = executionPlanAuthority();
    const passRunIds = Array.isArray(selection.pass_run_ids)
        ? selection.pass_run_ids
        : [];
    return Boolean(
        currentSessionId()
        && authority.analysisPlanId
        && authority.previewId
        && authority.previewHash
        && passRunIds[0]
        && start.execution_started !== true
        && !State.executionSelectionPending
        && !State.executionStartPending
    );
}

function renderPlanPanel() {
    if (State.planRevision) {
        const label = State.planRevision.next_state === 'plan_rejected' ? 'rejected' : 'revision requested';
        elements.planPanel.innerHTML = `
            <div class="plan-summary-grid">
                <div class="plan-summary-card"><strong>Revision Control</strong>${escapeHtml(label)}</div>
                <div class="plan-summary-card"><strong>Preview</strong><code>${escapeHtml(State.planRevision.source_preview_id)}</code></div>
                <div class="plan-summary-card"><strong>Execution</strong>${escapeHtml(State.planRevision.execution_started ? 'started' : 'not started')}</div>
            </div>
            <div class="plan-preview-grid">
                <section class="plan-list"><h3>Decision</h3><ul>
                    <li>${escapeHtml(State.planRevision.operator_decision)}</li>
                    <li>Note recorded: ${escapeHtml(State.planRevision.operator_note_recorded ? 'yes' : 'no')}</li>
                    <li>Approval blocked for this preview.</li>
                </ul></section>
                <section class="plan-list"><h3>Boundary</h3><ul>
                    <li>No execution started.</li>
                    <li>No pass runs created.</li>
                    <li>Results, package review, and handoff remain unavailable.</li>
                </ul></section>
            </div>
        `;
        return;
    }
    if (State.planApproval) {
        const approved = State.planApproval.approved_plan || {};
        const approvedSets = approved.approved_sets || [];
        const excluded = approved.excluded_sets || [];
        const planned = approved.planned_passes || [];
        const warningRows = (approved.warnings || []).length
            ? approved.warnings.map((item) => `<li>${escapeHtml(item.reason_code)}: ${escapeHtml(item.message)}</li>`).join('')
            : '<li>No warnings.</li>';
        const plannedRows = planned.length
            ? planned.map((item) => `
                <li>
                    <code>${escapeHtml(item.analysis_set_id)}</code>
                    ${escapeHtml(item.pass_type)} / ${escapeHtml(item.pass_scope)}
                    (${escapeHtml(item.selected_method_name || item.method_family)})
                </li>
            `).join('')
            : '<li>No planned passes.</li>';
        elements.planPanel.innerHTML = `
            <div class="plan-summary-grid">
                <div class="plan-summary-card"><strong>Approval</strong>approved</div>
                <div class="plan-summary-card"><strong>Plan ID</strong><code>${escapeHtml(State.planApproval.analysis_plan_id)}</code></div>
                <div class="plan-summary-card"><strong>Approved Sets</strong>${approvedSets.length}</div>
                <div class="plan-summary-card"><strong>Excluded</strong>${excluded.length}</div>
                <div class="plan-summary-card"><strong>Execution</strong>${escapeHtml(State.planApproval.execution_started ? 'started' : 'not started')}</div>
            </div>
            <div class="plan-preview-grid">
                <section class="plan-list"><h3>Approved Passes</h3><ul>${plannedRows}</ul></section>
                <section class="plan-list"><h3>Approval Basis</h3><ul>
                    <li>Approved at: ${escapeHtml(State.planApproval.approved_at)}</li>
                    <li>Preview: <code>${escapeHtml(approved.source_preview_id)}</code></li>
                    <li>Owner mode: ${escapeHtml(approved.owner_service_basis?.mode)}</li>
                </ul></section>
                <section class="plan-list"><h3>Warnings</h3><ul class="warning-list">${warningRows}</ul></section>
            </div>
        `;
        return;
    }
    const body = State.planPreview;
    if (!body) {
        elements.planPanel.innerHTML = canPlanPreview()
            ? '<div class="empty-panel">Plan preview is ready to request.</div>'
            : '<div class="empty-panel">Commit Gate C typing before plan preview.</div>';
        return;
    }
    if (body.schema_id === 'layer3.workbench_error.v1') {
        elements.planPanel.innerHTML = `
            <div class="plan-list">
                <h3>Plan Preview Blocked</h3>
                <ul>
                    <li><strong>${escapeHtml(body.error_code)}</strong>: ${escapeHtml(body.message)}</li>
                    ${(body.next_allowed_actions || []).map((action) => `<li>${escapeHtml(action)}</li>`).join('')}
                </ul>
            </div>
        `;
        return;
    }
    const preview = body.plan_preview || {};
    const admitted = preview.admitted_sets || [];
    const excluded = preview.excluded_sets || [];
    const planned = preview.planned_passes || [];
    const warnings = preview.warnings || [];
    const plannedRows = planned.length
        ? planned.map((item) => `
            <li>
                <code>${escapeHtml(item.analysis_set_id)}</code>
                ${escapeHtml(item.pass_type)} / ${escapeHtml(item.pass_scope)}
                (${escapeHtml(item.selected_method_name || item.method_family)})
            </li>
        `).join('')
        : '<li>No planned passes.</li>';
    const admittedRows = admitted.length
        ? admitted.map((item) => `<li><code>${escapeHtml(item.analysis_set_id)}</code> ${escapeHtml(item.readiness)} ${escapeHtml(item.analysis_modality)}</li>`).join('')
        : '<li>No admitted sets.</li>';
    const excludedRows = excluded.length
        ? excluded.map((item) => `<li><code>${escapeHtml(item.analysis_set_id)}</code> ${escapeHtml(item.reason_code)}</li>`).join('')
        : '<li>No excluded sets.</li>';
    const warningRows = warnings.length
        ? warnings.map((item) => `<li>${escapeHtml(item.reason_code)}: ${escapeHtml(item.message)}</li>`).join('')
        : '<li>No warnings.</li>';
    elements.planPanel.innerHTML = `
        <div class="plan-summary-grid">
            <div class="plan-summary-card"><strong>Preview</strong>${escapeHtml(body.preview_only ? 'preview only' : 'unknown')}</div>
            <div class="plan-summary-card"><strong>Admitted</strong>${admitted.length}</div>
            <div class="plan-summary-card"><strong>Excluded</strong>${excluded.length}</div>
            <div class="plan-summary-card"><strong>Passes</strong>${planned.length}</div>
        </div>
        <div class="plan-preview-grid">
            <section class="plan-list"><h3>Planned Passes</h3><ul>${plannedRows}</ul></section>
            <section class="plan-list"><h3>Admitted Sets</h3><ul>${admittedRows}</ul></section>
            <section class="plan-list"><h3>Exclusions</h3><ul>${excludedRows}</ul></section>
            <section class="plan-list"><h3>Warnings</h3><ul class="warning-list">${warningRows}</ul></section>
        </div>
    `;
}

function displayValue(value) {
    if (value === true) return 'true';
    if (value === false) return 'false';
    if (value === 0) return '0';
    return value || 'unknown';
}

function fieldItem(label, value, { code = false } = {}) {
    const escaped = escapeHtml(displayValue(value));
    const body = code ? `<code>${escaped}</code>` : escaped;
    return `<li>${escapeHtml(label)}: ${body}</li>`;
}

function summarizeTrace(value) {
    if (!value || typeof value !== 'object') return 'none';
    return Object.entries(value)
        .map(([key, item]) => `${key}=${displayValue(item)}`)
        .join(', ');
}

function resultReviewPanelState(authority) {
    const cohort = associatedCohortProjection(authority);
    if (State.resultReviewPending) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_recording' : 'result_review_ui_recording',
            pill: 'preview',
            message: 'Recording one bounded operator decision.',
        };
    }
    if (recordedResultReview()) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_recorded' : 'result_review_ui_recorded',
            pill: 'ok',
            message: 'Server state already contains a result-review record.',
        };
    }
    if (State.resultReviewError || State.resultStatusError) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_blocked' : 'result_review_ui_blocked',
            pill: 'blocked',
            message: 'Server authority rejected or blocked the latest result-review action.',
        };
    }
    if (!authority.sessionId) {
        return { label: 'result_review_ui_unavailable', pill: 'blocked', message: 'No Layer 3 session id is available.' };
    }
    if (!State.sessionSummary && !State.executionSelection && !State.executionStart) {
        return { label: 'result_review_ui_unavailable', pill: 'blocked', message: 'Refresh session state before inspecting result status.' };
    }
    if (!hasResultAuthorityIdentity(authority) || !authority.selected) {
        return { label: 'result_review_ui_waiting_for_selection', pill: 'blocked', message: 'Server summary has no selected pass authority.' };
    }
    if (!authority.terminal) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_waiting_for_execution' : 'result_review_ui_waiting_for_execution_start',
            pill: 'blocked',
            message: 'Selected pass is not terminal.',
        };
    }
    if (State.resultStatus?.result_status_available === true) {
        if (cohort.isAssociated && !cohort.ready) {
            return {
                label: 'cohort_result_review_ui_blocked',
                pill: 'blocked',
                message: 'Associated-cohort status is available, but exact method, provenance, or trace readiness is incomplete.',
            };
        }
        if (cohort.ready) {
            return {
                label: 'cohort_result_review_ui_review_ready',
                pill: 'ok',
                message: 'Exact selected-pass associated-cohort descriptive result/status authority is ready for one review.',
            };
        }
        return { label: 'result_review_ui_review_ready', pill: 'ok', message: 'Result/status authority is available for one selected terminal pass.' };
    }
    if (State.resultStatus) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_blocked' : 'result_review_ui_blocked',
            pill: 'blocked',
            message: 'Result/status authority is not available for review.',
        };
    }
    return { label: 'result_review_ui_unavailable', pill: 'preview', message: 'Selected terminal pass can be inspected for result/status availability.' };
}

function renderErrorCard(error) {
    if (!error) return '';
    const actions = Array.isArray(error.next_allowed_actions) ? error.next_allowed_actions : [];
    return `
        <section class="result-review-card">
            <strong>Block Reason</strong>
            <ul>
                ${fieldItem('code', error.error_code || error.status)}
                ${fieldItem('message', error.message)}
                ${actions.map((action) => `<li>next action: ${escapeHtml(action)}</li>`).join('')}
            </ul>
        </section>
    `;
}

function renderDownstreamLocks(labels) {
    const locks = labels?.length ? labels : ['package', 'handoff', 'package_review'];
    return locks.map((label) => `<span class="status-pill blocked">${escapeHtml(label.replace(/_/g, ' '))}</span>`).join('');
}

function executionSelectionPanelState() {
    const authority = executionPlanAuthority();
    const selection = executionSelectionState();
    if (State.executionStartPending) {
        return { label: 'execution_starting', pill: 'preview', message: 'Starting the selected pass through server authority.' };
    }
    if (State.executionSelectionPending) {
        return { label: 'execution_selecting', pill: 'preview', message: 'Selecting pass runs for the approved plan.' };
    }
    if (State.executionStart?.execution_started === true) {
        return { label: 'execution_started', pill: 'ok', message: 'Execution started for the server-selected pass.' };
    }
    if (State.executionStartError || State.executionSelectionError) {
        return { label: 'execution_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest execution action.' };
    }
    if (selection.pass_run_count) {
        return { label: 'execution_selected', pill: 'ok', message: 'Server-selected pass run is ready to start.' };
    }
    if (authority.analysisPlanId && authority.previewId && authority.previewHash) {
        return { label: 'execution_selection_ready', pill: 'preview', message: 'Approved plan is ready for execution selection.' };
    }
    return { label: 'execution_not_ready', pill: 'blocked', message: 'Approve a plan before execution selection.' };
}

function renderExecutionSelectionStartPanel() {
    const panelState = executionSelectionPanelState();
    const selection = executionSelectionState();
    const start = executionStartState();
    const error = State.executionStartError || State.executionSelectionError;
    const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
    const analysisRunIds = Array.isArray(selection.analysis_run_ids) ? selection.analysis_run_ids : [];
    const previewIdentity = start.preview_identity || selection.preview_identity || {};
    elements.executionSelectionStartPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Execution Selection</strong>
                <ul>
                    ${fieldItem('session', selection.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('analysis plan', selection.analysis_plan_id || State.planApproval?.analysis_plan_id || State.sessionSummary?.plan_approval?.analysis_plan_id, { code: true })}
                    ${fieldItem('preview', previewIdentity.preview_id || selection.source_preview_id || State.planPreview?.preview_id, { code: true })}
                    ${fieldItem('preview hash', previewIdentity.preview_hash || selection.source_preview_hash || State.planPreview?.preview_hash, { code: true })}
                    ${fieldItem('pass run count', selection.pass_run_count)}
                    ${fieldItem('first pass run', passRunIds[0], { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Execution Start</strong>
                <ul>
                    ${fieldItem('started', start.execution_started)}
                    ${fieldItem('pass run', start.pass_run_id || passRunIds[0], { code: true })}
                    ${fieldItem('pass status', start.pass_run_status)}
                    ${fieldItem('analysis run', start.analysis_run_id || analysisRunIds[0], { code: true })}
                    ${fieldItem('output ref', start.output_payload_ref, { code: true })}
                    ${fieldItem('next state', start.next_state || selection.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(start.downstream_unavailable || selection.downstream_unavailable || currentDownstreamUnavailable())}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderResultReviewPanel() {
    const authority = selectedResultAuthority();
    const statusBody = State.resultStatus || {};
    const reviewState = recordedResultReview();
    const panelState = resultReviewPanelState(authority);
    const metadata = statusBody.output_metadata_summary || {};
    const cohort = associatedCohortProjection(authority);
    const traceSummary = State.resultReview?.trace_summary || reviewState?.trace_summary;
    const error = State.resultReviewError || State.resultStatusError;
    const downstream = State.resultReview?.downstream_unavailable
        || statusBody.downstream_unavailable
        || reviewState?.downstream_unavailable
        || currentDownstreamUnavailable();

    elements.resultReviewPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Selected Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('pass status', authority.passStatus)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Result Status</strong>
                <ul>
                    ${fieldItem('status', statusBody.status)}
                    ${fieldItem('available', statusBody.result_status_available)}
                    ${fieldItem('analysis run', authority.analysisRunId, { code: true })}
                    ${fieldItem('output ref', statusBody.output_payload_ref, { code: true })}
                    ${fieldItem('metadata readable', metadata.readable)}
                    ${fieldItem('artifact count', metadata.artifact_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Associated Cohort Authority</strong>
                <ul>
                    ${fieldItem('pass type', cohort.passType)}
                    ${fieldItem('pass scope', cohort.passScope)}
                    ${fieldItem('selected method', cohort.selectedMethod)}
                    ${fieldItem('requested method', cohort.requestedMethod)}
                    ${fieldItem('requested method source', cohort.requestedMethodSource)}
                    ${fieldItem('source gate', cohort.sourceGate)}
                    ${fieldItem('cohort shape', cohort.cohortShape)}
                    ${fieldItem('source dataset versions', cohort.sourceDatasetVersionIds.join(', '))}
                    ${fieldItem('output ref', cohort.outputPayloadRef, { code: true })}
                    ${fieldItem('unresolved trace', cohort.unresolvedTraceCount)}
                    ${fieldItem('cohort review ready', cohort.ready)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Review State</strong>
                <ul>
                    ${fieldItem('state', reviewState?.review_state || reviewState?.state)}
                    ${fieldItem('decision', reviewState?.operator_decision)}
                    ${fieldItem('record', reviewState?.review_record_ref, { code: true })}
                    ${fieldItem('unresolved trace', reviewState?.unresolved_trace_count)}
                    ${fieldItem('trace', summarizeTrace(traceSummary))}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function packageReviewPanelState() {
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    if (State.packageReviewSubmitPending) {
        return { label: 'package_review_submit_recording', pill: 'preview', message: 'Recording one bounded package-review decision.' };
    }
    if (State.packageConstructionPending) {
        return { label: 'package_construction_committing', pill: 'preview', message: 'Committing the three package families before package-review submit.' };
    }
    if (State.packageReviewPreviewPending) {
        return { label: 'package_review_preview_inspecting', pill: 'preview', message: 'Inspecting read-only package-review readiness.' };
    }
    if (State.packageReviewSubmit?.package_review_state || submit.submit_record_ref) {
        return { label: State.packageReviewSubmit?.package_review_state || submit.state || 'package_review_recorded', pill: 'ok', message: 'Server state already contains a package-review submit record.' };
    }
    if (State.packageReviewSubmitError || State.packageConstructionError || State.packageReviewPreviewError) {
        return { label: 'package_review_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest package action.' };
    }
    if (submit.package_review_submit_enabled === true) {
        return { label: submit.state || 'package_review_submit_ready', pill: 'ok', message: 'Constructed packages are ready for one bounded package-review decision.' };
    }
    if (construction.state === 'package_constructed') {
        return { label: 'package_constructed', pill: 'ok', message: 'Package set is constructed; inspect preview if a current preview hash is needed before submit.' };
    }
    if (State.packageReviewPreview?.package_review_preview_enabled === true) {
        if (State.packageReviewPreview?.package_commit_enabled === false) {
            return { label: State.packageReviewPreview.next_state || 'package_review_preview_ready', pill: 'preview', message: 'Associated-cohort package-review preview is available as read-only; package construction remains deferred.' };
        }
        return { label: State.packageReviewPreview.next_state || 'package_review_preview_ready', pill: 'ok', message: 'Package-review preview is available and can be committed as a package set.' };
    }
    if (recordedApprovedResultReview() && associatedCohortReviewContext()) {
        return { label: 'package_review_preview_available', pill: 'preview', message: 'Approved associated-cohort result review can be inspected for read-only package-preview readiness.' };
    }
    if (recordedApprovedResultReview()) {
        return { label: 'package_review_preview_unavailable', pill: 'preview', message: 'Approved result review can be inspected for package-preview readiness.' };
    }
    return { label: 'package_review_preview_unavailable', pill: 'blocked', message: 'Package preview requires an approved selected-pass result review.' };
}

function renderPackageReviewPreviewPanel() {
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const panelState = packageReviewPanelState();
    const review = recordedApprovedResultReview() || {};
    const compatibility = preview.package_owner_compatibility || {};
    const candidateKinds = Array.isArray(preview.candidate_package_kinds) ? preview.candidate_package_kinds : [];
    const packageIds = packageOutputPackageIds();
    const payloadHashes = packagePayloadHashes();
    const packageKinds = packageKindsFromState();
    const candidateRows = candidateKinds.length
        ? candidateKinds.map((candidate) => `
            <li>
                <code>${escapeHtml(candidate.package_kind)}</code>
                ${candidate.preview_only ? '<span class="status-pill preview">preview</span>' : ''}
                ${candidate.package_commit_enabled ? '<span class="status-pill ok">commit ready</span>' : ''}
                ${candidate.package_commit_enabled === false ? '<span class="status-pill blocked">commit deferred</span>' : ''}
            </li>
        `).join('')
        : '<li>No package candidates loaded.</li>';
    const packageRows = packageKinds.length
        ? packageKinds.map((packageKind, index) => `
            <li>
                <code>${escapeHtml(packageKind)}</code>
                ${packageIds[index] ? `<code>${escapeHtml(packageIds[index])}</code>` : ''}
            </li>
        `).join('')
        : '<li>No package set is constructed.</li>';
    const payloadRows = payloadHashes.length
        ? payloadHashes.map((payloadHash) => `<li><code>${escapeHtml(payloadHash)}</code></li>`).join('')
        : '<li>No package payload hashes are available.</li>';
    const error = State.packageReviewSubmitError || State.packageConstructionError || State.packageReviewPreviewError;
    elements.packageReviewPreviewPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Preview Authority</strong>
                <ul>
                    ${fieldItem('session', preview.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('analysis plan', preview.analysis_plan_id || selectedResultAuthority().analysisPlanId, { code: true })}
                    ${fieldItem('pass run', preview.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('result review', preview.result_review_record_ref || review.review_record_ref, { code: true })}
                    ${fieldItem('review state', preview.result_review_state || review.review_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Candidate Families</strong>
                <ul>${candidateRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Package Construction</strong>
                <ul>
                    ${fieldItem('state', construction.next_state || construction.state)}
                    ${fieldItem('reconciliation', construction.reconciliation_record_id, { code: true })}
                    ${fieldItem('commit enabled', construction.package_commit_enabled)}
                    ${fieldItem('submit enabled', construction.package_review_submit_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Constructed Packages</strong>
                <ul>${packageRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${payloadRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Package Review Submit</strong>
                <ul>
                    ${fieldItem('state', submit.next_state || submit.package_review_state || submit.state)}
                    ${fieldItem('submit ref', submit.submit_record_ref, { code: true })}
                    ${fieldItem('operator decision', submit.operator_decision)}
                    ${fieldItem('submit enabled', submit.package_review_submit_enabled)}
                    ${fieldItem('handoff enabled', submit.handoff_enabled)}
                    ${fieldItem('export enabled', submit.export_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Owner Compatibility</strong>
                <ul>
                    ${fieldItem('status', compatibility.status)}
                    ${fieldItem('preview projection', compatibility.preview_candidate_projection_compatible)}
                    ${fieldItem('construction compatible', compatibility.construction_compatible_with_current_workbench_state)}
                    ${fieldItem('materialize callable', compatibility.materialize_package_entry_callable)}
                    ${fieldItem('missing inputs', Array.isArray(compatibility.missing_owner_service_inputs) ? compatibility.missing_owner_service_inputs.join(', ') : null)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(submit.downstream_unavailable || construction.downstream_unavailable || preview.downstream_unavailable || ['package_commit', 'package_review_submit', 'handoff', 'export'])}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderPackageLifecycleDashboardPanel() {
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const rows = packageLifecycleOutputRows();
    const dashboardState = packageLifecycleDashboardState(preview, construction, submit);
    const sourceGate = (
        submit.source_gate
        || construction.source_gate
        || preview.source_gate
        || submit.package_construction_source_gate
        || construction.package_construction_source_gate
    );
    const downstream = [
        'package_mutation_controls_blocked',
        'package_payload_rewrite_blocked',
        'connector_dispatch_blocked',
        'provider_public_delivery_use_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.packageLifecycleDashboardPanel.dataset.lifecycleState = dashboardState.label;
    elements.packageLifecycleDashboardPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(dashboardState.pill)}">${escapeHtml(dashboardState.label)}</span>
            <span class="rail-label">${escapeHtml(PACKAGE_LIFECYCLE_DASHBOARD_MODE)}</span>
        </div>
        <div class="result-review-grid package-lifecycle-grid">
            <section class="result-review-card">
                <strong>Lifecycle Authority</strong>
                <ul>
                    ${fieldItem('use case', PACKAGE_LIFECYCLE_USE_CASE, { code: true })}
                    ${fieldItem('response authority', PACKAGE_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('source gate', sourceGate, { code: true })}
                    ${fieldItem('session', preview.session_id || construction.session_id || submit.session_id || currentSessionId(), { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Preview Identity</strong>
                <ul>
                    ${fieldItem('preview hash', packageReviewPreviewHash(), { code: true })}
                    ${fieldItem('result review', preview.result_review_record_ref || construction.result_review_record_ref || submit.result_review_record_ref, { code: true })}
                    ${fieldItem('preview enabled', preview.package_review_preview_enabled)}
                    ${fieldItem('commit enabled', preview.package_commit_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Package Set</strong>
                <ul>
                    ${fieldItem('construction state', construction.next_state || construction.state)}
                    ${fieldItem('reconciliation', construction.reconciliation_record_id, { code: true })}
                    ${fieldItem('basis hash', packageConstructionBasisHash(), { code: true })}
                    ${fieldItem('package count', rows.length)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Review Decision</strong>
                <ul>
                    ${fieldItem('review state', submit.package_review_state || submit.next_state || submit.state)}
                    ${fieldItem('submit ref', submit.submit_record_ref, { code: true })}
                    ${fieldItem('decision', submit.operator_decision)}
                    ${fieldItem('handoff enabled', submit.handoff_enabled)}
                    ${fieldItem('export enabled', submit.export_enabled)}
                </ul>
            </section>
            <section class="result-review-card package-lifecycle-rows">
                <strong>Package Lifecycle Rows</strong>
                <ul>${renderPackageLifecycleRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function renderPackageSupersessionPreviewPanel() {
    const preview = packageSupersessionPreviewState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const rows = Array.isArray(preview.package_rows) && preview.package_rows.length
        ? preview.package_rows
        : packageLifecycleOutputRows();
    const dependencies = Array.isArray(preview.downstream_dependencies)
        ? preview.downstream_dependencies
        : [];
    const error = State.packageSupersessionPreviewError;
    const stateLabel = State.packageSupersessionPreviewPending
        ? 'package_supersession_preview_submitting'
        : (error?.error_code || preview.next_state || (canSubmitPackageSupersessionPreview() ? 'package_supersession_preview_ready' : 'package_supersession_preview_unavailable'));
    const statePill = error ? 'blocked' : (preview.next_state ? 'ok' : 'preview');
    elements.packageSupersessionPreviewPanel.dataset.previewState = stateLabel;
    elements.packageSupersessionPreviewPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(statePill)}">${escapeHtml(stateLabel)}</span>
            <span class="rail-label">${escapeHtml(PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE)}</span>
        </div>
        <div class="result-review-grid package-supersession-preview-grid">
            <section class="result-review-card">
                <strong>Rendered Control</strong>
                <ul>
                    ${fieldItem('use case', PACKAGE_SUPERSESSION_PREVIEW_USE_CASE, { code: true })}
                    ${fieldItem('response authority', PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('operator decision', PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION, { code: true })}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Request Basis</strong>
                <ul>
                    ${fieldItem('session', preview.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('reconciliation', preview.reconciliation_record_id || submit.reconciliation_record_id || construction.reconciliation_record_id, { code: true })}
                    ${fieldItem('package preview hash', preview.package_review_preview_hash || packageReviewPreviewHash(), { code: true })}
                    ${fieldItem('package submit ref', submit.submit_record_ref, { code: true })}
                    ${fieldItem('package count', rows.length)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Preview Result</strong>
                <ul>
                    ${fieldItem('status', preview.status)}
                    ${fieldItem('mode', preview.package_supersession_preview_mode, { code: true })}
                    ${fieldItem('preview hash', preview.package_supersession_preview_hash, { code: true })}
                    ${fieldItem('package set hash', preview.package_set_hash, { code: true })}
                    ${fieldItem('next state', preview.next_state)}
                    ${fieldItem('downstream dependency detected', preview.downstream_dependency_detected)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Capability Flags</strong>
                <ul>
                    ${fieldItem('database write', preview.database_write_enabled)}
                    ${fieldItem('filesystem write', preview.filesystem_write_enabled)}
                    ${fieldItem('package row mutation', preview.package_row_mutation_enabled)}
                    ${fieldItem('payload rewrite', preview.package_payload_rewrite_enabled)}
                    ${fieldItem('supersession commit', preview.package_supersession_commit_enabled)}
                    ${fieldItem('broad mutation', preview.broad_package_mutation_enabled)}
                    ${fieldItem('connector dispatch', preview.connector_dispatch_enabled)}
                    ${fieldItem('provider public URL', preview.provider_public_url_enabled)}
                    ${fieldItem('source widening', preview.source_widening_enabled)}
                    ${fieldItem('qualitative/RAG execution', preview.qualitative_hybrid_rag_execution_enabled)}
                </ul>
            </section>
            <section class="result-review-card package-supersession-preview-rows">
                <strong>Immutable Package Rows</strong>
                <ul>${renderPackageSupersessionPreviewRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Downstream Dependencies</strong>
                <ul>${renderPackageSupersessionDependencyRows(dependencies)}</ul>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderSourceDirectoryPackageSupersessionPreviewPanel() {
    const preview = sourceDirectoryPackageSupersessionPreviewState() || {};
    const payload = sourceDirectoryPackageSupersessionPreviewPayloadOrNull() || {};
    const rows = Array.isArray(preview.package_rows) && preview.package_rows.length
        ? preview.package_rows
        : replacementPackageRows({
            packageIds: preview.output_package_ids || payload.output_package_ids || [],
            packageKinds: preview.package_kinds || payload.package_kinds || [],
            payloadHashes: preview.payload_hashes || payload.payload_hashes || [],
        });
    const dependencies = Array.isArray(preview.downstream_dependencies)
        ? preview.downstream_dependencies
        : [];
    const error = State.sourceDirectoryPackageSupersessionPreviewError;
    const stateLabel = State.sourceDirectoryPackageSupersessionPreviewPending
        ? 'source_directory_package_supersession_preview_submitting'
        : (error?.error_code || preview.next_state || (canSubmitSourceDirectoryPackageSupersessionPreview() ? 'source_directory_package_supersession_preview_ready' : 'source_directory_package_supersession_preview_unavailable'));
    const statePill = error ? 'blocked' : (preview.next_state ? 'ok' : 'preview');
    elements.sourceDirectoryPackageSupersessionPreviewPanel.dataset.previewState = stateLabel;
    elements.sourceDirectoryPackageSupersessionPreviewPanel.dataset.readOnly = 'true';
    elements.sourceDirectoryPackageSupersessionPreviewPanel.dataset.frontendDurableAuthority = 'false';
    elements.sourceDirectoryPackageSupersessionPreviewPanel.dataset.serverRoute = SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH;
    elements.sourceDirectoryPackageSupersessionPreviewPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(statePill)}">${escapeHtml(stateLabel)}</span>
            <span class="rail-label">${escapeHtml(SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE)}</span>
        </div>
        <div class="result-review-grid package-supersession-preview-grid">
            <section class="result-review-card">
                <strong>Rendered Control</strong>
                <ul>
                    ${fieldItem('use case', SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_USE_CASE, { code: true })}
                    ${fieldItem('response authority', SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('server route', `POST ${API_ROOT}${SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH}`, { code: true })}
                    ${fieldItem('operator decision', SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION, { code: true })}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Server Authority Basis</strong>
                <ul>
                    ${fieldItem('payload source', 'sourceDirectoryPackageSupersessionPreviewPayload', { code: true })}
                    ${fieldItem('session', preview.session_id || payload.session_id, { code: true })}
                    ${fieldItem('material snapshot', preview.material_snapshot_id || payload.material_snapshot_id, { code: true })}
                    ${fieldItem('source file', preview.source_ingestion_file_id || payload.source_ingestion_file_id, { code: true })}
                    ${fieldItem('reconciliation', preview.reconciliation_record_id || payload.reconciliation_record_id, { code: true })}
                    ${fieldItem('package review submit ref', preview.package_review_submit_record_ref || payload.package_review_submit_record_ref, { code: true })}
                    ${fieldItem('package count', rows.length)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Preview Result</strong>
                <ul>
                    ${fieldItem('schema', preview.schema_id || SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID, { code: true })}
                    ${fieldItem('mode', preview.mode || SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_MODE, { code: true })}
                    ${fieldItem('status', preview.status)}
                    ${fieldItem('source gate', preview.source_gate, { code: true })}
                    ${fieldItem('preview hash', preview.package_supersession_preview_hash, { code: true })}
                    ${fieldItem('source package set hash', preview.source_package_set_hash, { code: true })}
                    ${fieldItem('downstream dependency hash', preview.downstream_dependency_hash, { code: true })}
                    ${fieldItem('next state', preview.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Capability Flags</strong>
                <ul>
                    ${fieldItem('replacement package-set authority', preview.replacement_package_set_authority_enabled)}
                    ${fieldItem('package supersession commit', preview.package_supersession_commit_enabled)}
                    ${fieldItem('package row mutation', preview.package_row_mutation_enabled)}
                    ${fieldItem('payload rewrite', preview.package_payload_rewrite_enabled)}
                    ${fieldItem('source package row mutation', preview.source_package_row_mutation_enabled)}
                    ${fieldItem('connector dispatch', preview.connector_dispatch_enabled)}
                    ${fieldItem('provider public delivery', preview.provider_public_delivery_enabled)}
                    ${fieldItem('network egress', preview.network_egress_enabled)}
                    ${fieldItem('frontend durable authority', preview.frontend_durable_authority_enabled)}
                </ul>
            </section>
            <section class="result-review-card package-supersession-preview-rows">
                <strong>Source Package Rows</strong>
                <ul>${renderPackageSupersessionPreviewRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Downstream Dependencies</strong>
                <ul>${renderPackageSupersessionDependencyRows(dependencies)}</ul>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderReplacementPackageSetAuthorityPanel() {
    const preview = replacementPackageSetAuthorityPreviewState() || {};
    const materialization = replacementPackageArtifactMaterializationState() || {};
    const authority = replacementPackageSetAuthorityState() || {};
    const source = replacementPackageSourceArrays(preview);
    const sourceMode = replacementPackageSetAuthorityPreviewSourceMode(preview);
    const sourceAuthority = replacementPackageSetAuthorityPreviewSourceAuthority(preview);
    const sourceDirectoryMode = sourceMode === 'source_directory_package_supersession_preview';
    const renderedMode = sourceDirectoryMode
        ? SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE
        : REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE;
    const useCase = sourceDirectoryMode
        ? SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE
        : REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE;
    const recordRoute = sourceDirectoryMode
        ? SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_PATH
        : '/package/replacement-set/record';
    const materializationDecision = sourceDirectoryMode
        ? 'not_applicable_source_directory_logical_replacement_refs'
        : REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION;
    const sourceRows = replacementPackageRows({
        packageIds: source.outputPackageIds,
        packageKinds: source.packageKinds,
        payloadRefs: source.payloadRefs,
        payloadHashes: source.payloadHashes,
    });
    const replacementRows = replacementPackageRows({
        packageKinds: authority.replacement_package_kinds || materialization.replacement_package_kinds || [],
        payloadRefs: authority.replacement_payload_refs || materialization.replacement_payload_refs || [],
        payloadHashes: authority.replacement_payload_hashes || materialization.replacement_payload_hashes || [],
    });
    const error = State.replacementPackageSetAuthorityError || State.replacementPackageArtifactMaterializationError;
    const stateLabel = replacementPackageSetAuthorityBusy()
        ? 'replacement_package_set_authority_recording'
        : (
            error?.error_code
            || authority.next_state
            || materialization.next_state
            || (canSubmitReplacementPackageSetAuthority()
                ? 'replacement_package_set_authority_ready'
                : 'replacement_package_set_authority_unavailable')
        );
    const statePill = error ? 'blocked' : (authority.replacement_package_set_authority_id ? 'ok' : 'preview');
    const downstream = authority.downstream_unavailable || materialization.downstream_unavailable || [];
    elements.replacementPackageSetAuthorityPanel.dataset.renderedMode = renderedMode;
    elements.replacementPackageSetAuthorityPanel.dataset.authorityState = stateLabel;
    elements.replacementPackageSetAuthorityPanel.dataset.sourceAuthority = sourceAuthority;
    elements.replacementPackageSetAuthorityPanel.dataset.sourceMode = sourceMode;
    elements.replacementPackageSetAuthorityPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(statePill)}">${escapeHtml(stateLabel)}</span>
            <span class="rail-label">${escapeHtml(renderedMode)}</span>
        </div>
        <div class="result-review-grid replacement-package-set-authority-grid">
            <section class="result-review-card">
                <strong>Rendered Control</strong>
                <ul>
                    ${fieldItem('use case', useCase, { code: true })}
                    ${fieldItem('response authority', REPLACEMENT_PACKAGE_SET_AUTHORITY_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('source-directory mode', SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE, { code: true })}
                    ${fieldItem('source-directory use case', SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE, { code: true })}
                    ${fieldItem('selected source authority', sourceAuthority, { code: true })}
                    ${fieldItem('selected source mode', sourceMode, { code: true })}
                    ${fieldItem('record route', recordRoute, { code: true })}
                    ${fieldItem('materialization decision', materializationDecision, { code: true })}
                    ${fieldItem('authority decision', REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION, { code: true })}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Materialization Request Source</strong>
                <ul>
                    ${fieldItem('status', materialization.status)}
                    ${fieldItem('materialization id', materialization.replacement_artifact_materialization_id, { code: true })}
                    ${fieldItem('mode', materialization.replacement_package_artifact_materialization_mode, { code: true })}
                    ${fieldItem('namespace', materialization.artifact_namespace, { code: true })}
                    ${fieldItem('preview hash', preview.package_supersession_preview_hash || materialization.package_supersession_preview_hash, { code: true })}
                    ${fieldItem('materialization basis', materialization.materialization_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Replacement Authority Result</strong>
                <ul>
                    ${fieldItem('status', authority.status)}
                    ${fieldItem('authority id', authority.replacement_package_set_authority_id, { code: true })}
                    ${fieldItem('replacement set id', authority.replacement_package_set_id || materialization.replacement_package_set_id, { code: true })}
                    ${fieldItem('replacement set hash', authority.replacement_package_set_hash || materialization.replacement_package_set_hash, { code: true })}
                    ${fieldItem('authority basis', authority.authority_basis_hash || materialization.authority_basis_hash, { code: true })}
                    ${fieldItem('next state', authority.next_state || materialization.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Capability Flags</strong>
                <ul>
                    ${fieldItem('source package row mutation', materialization.source_l3_output_package_mutation_enabled)}
                    ${fieldItem('source payload rewrite', materialization.source_package_payload_rewrite_enabled)}
                    ${fieldItem('package row mutation', authority.package_row_mutation_enabled)}
                    ${fieldItem('package payload write', authority.package_payload_write_enabled)}
                    ${fieldItem('package supersession commit', authority.package_supersession_commit_enabled || materialization.package_supersession_commit_enabled)}
                    ${fieldItem('provider public URL', authority.provider_public_url_enabled || materialization.provider_public_url_enabled)}
                    ${fieldItem('source widening', authority.source_widening_enabled || materialization.source_widening_enabled)}
                    ${fieldItem('qualitative/RAG execution', authority.qualitative_hybrid_rag_execution_enabled || materialization.qualitative_hybrid_rag_execution_enabled)}
                    ${fieldItem('frontend durable authority', authority.frontend_only_durable_state_enabled || materialization.frontend_only_durable_state_enabled)}
                </ul>
            </section>
            <section class="result-review-card replacement-package-set-authority-rows">
                <strong>Source Package Rows</strong>
                <ul>${renderReplacementPackageRows(sourceRows)}</ul>
            </section>
            <section class="result-review-card replacement-package-set-authority-rows">
                <strong>Replacement Payload Rows</strong>
                <ul>${renderReplacementPackageRows(replacementRows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderPackageSupersessionCommitPanel() {
    const preview = packageSupersessionCommitPreviewState() || {};
    const sourceMode = packageSupersessionCommitPreviewSourceMode(preview);
    const sourceAuthority = packageSupersessionCommitPreviewSourceAuthority(preview);
    const sourceDirectoryMode = sourceMode === 'source_directory_package_supersession_preview';
    const renderedMode = sourceDirectoryMode
        ? SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE
        : PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE;
    const useCase = sourceDirectoryMode
        ? SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_USE_CASE
        : PACKAGE_SUPERSESSION_COMMIT_USE_CASE;
    const commitRoute = sourceDirectoryMode
        ? SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH
        : '/package/supersession/commit';
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const commit = packageSupersessionCommitState() || {};
    const source = replacementPackageSourceArrays(preview);
    const sourceRows = replacementPackageRows({
        packageIds: commit.source_output_package_ids || source.outputPackageIds,
        packageKinds: commit.source_package_kinds || source.packageKinds,
        payloadRefs: commit.source_payload_refs || source.payloadRefs,
        payloadHashes: commit.source_payload_hashes || source.payloadHashes,
    });
    const replacementRows = replacementPackageRows({
        packageKinds: commit.replacement_package_kinds || replacementAuthority.replacement_package_kinds || [],
        payloadRefs: commit.replacement_payload_refs || replacementAuthority.replacement_payload_refs || [],
        payloadHashes: commit.replacement_payload_hashes || replacementAuthority.replacement_payload_hashes || [],
    });
    const error = State.packageSupersessionCommitError;
    const stateLabel = State.packageSupersessionCommitPending
        ? 'package_supersession_commit_recording'
        : (
            error?.error_code
            || commit.next_state
            || (canSubmitPackageSupersessionCommit()
                ? 'package_supersession_commit_ready'
                : (sourceDirectoryMode || stableHashAvailable()
                    ? 'package_supersession_commit_unavailable'
                    : 'package_supersession_commit_hashing_unavailable'))
        );
    const statePill = error ? 'blocked' : (commit.package_supersession_commit_id ? 'ok' : 'preview');
    const downstream = commit.downstream_unavailable || replacementAuthority.downstream_unavailable || [];
    elements.packageSupersessionCommitPanel.dataset.renderedMode = renderedMode;
    elements.packageSupersessionCommitPanel.dataset.commitState = stateLabel;
    elements.packageSupersessionCommitPanel.dataset.sourceAuthority = sourceAuthority;
    elements.packageSupersessionCommitPanel.dataset.sourceMode = sourceMode;
    elements.packageSupersessionCommitPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(statePill)}">${escapeHtml(stateLabel)}</span>
            <span class="rail-label">${escapeHtml(renderedMode)}</span>
        </div>
        <div class="result-review-grid package-supersession-commit-grid">
            <section class="result-review-card">
                <strong>Rendered Control</strong>
                <ul>
                    ${fieldItem('use case', useCase, { code: true })}
                    ${fieldItem('response authority', PACKAGE_SUPERSESSION_COMMIT_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('selected source authority', sourceAuthority, { code: true })}
                    ${fieldItem('selected source mode', sourceMode, { code: true })}
                    ${fieldItem('commit route', commitRoute, { code: true })}
                    ${fieldItem('operator decision', PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION, { code: true })}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Authority</strong>
                <ul>
                    ${fieldItem('preview hash', preview.package_supersession_preview_hash || commit.package_supersession_preview_hash, { code: true })}
                    ${fieldItem('source package set hash', replacementPackageSetAuthoritySourcePackageSetHash(preview) || commit.source_package_set_hash, { code: true })}
                    ${fieldItem('downstream dependency count', Array.isArray(preview.downstream_dependencies) ? preview.downstream_dependencies.length : null)}
                    ${fieldItem('source gate', commit.source_gate, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Replacement Authority</strong>
                <ul>
                    ${fieldItem('authority id', replacementAuthority.replacement_package_set_authority_id || commit.replacement_package_set_authority_id, { code: true })}
                    ${fieldItem('replacement set id', replacementAuthority.replacement_package_set_id || commit.replacement_package_set_id, { code: true })}
                    ${fieldItem('replacement set hash', replacementAuthority.replacement_package_set_hash || commit.replacement_package_set_hash, { code: true })}
                    ${fieldItem('basis hash', replacementAuthority.authority_basis_hash || commit.replacement_authority_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Commit Result</strong>
                <ul>
                    ${fieldItem('status', commit.status)}
                    ${fieldItem('commit id', commit.package_supersession_commit_id, { code: true })}
                    ${fieldItem('mode', commit.package_supersession_commit_mode, { code: true })}
                    ${fieldItem('commit basis', commit.commit_basis_hash, { code: true })}
                    ${fieldItem('downstream dependency hash', commit.downstream_dependency_hash, { code: true })}
                    ${fieldItem('next state', commit.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Capability Flags</strong>
                <ul>
                    ${fieldItem('package row mutation', commit.package_row_mutation_enabled)}
                    ${fieldItem('package payload write', commit.package_payload_write_enabled)}
                    ${fieldItem('L3 output package write', commit.l3_output_package_write_enabled)}
                    ${fieldItem('broad package mutation', commit.broad_package_mutation_enabled)}
                    ${fieldItem('connector dispatch', commit.connector_dispatch_enabled)}
                    ${fieldItem('provider public URL', commit.provider_public_url_enabled)}
                    ${fieldItem('source widening', commit.source_widening_enabled)}
                    ${fieldItem('qualitative/RAG execution', commit.qualitative_hybrid_rag_execution_enabled)}
                    ${fieldItem('frontend durable authority', commit.frontend_only_durable_state_enabled)}
                </ul>
            </section>
            <section class="result-review-card package-supersession-commit-rows">
                <strong>Source Package Rows</strong>
                <ul>${renderReplacementPackageRows(sourceRows)}</ul>
            </section>
            <section class="result-review-card package-supersession-commit-rows">
                <strong>Replacement Package Rows</strong>
                <ul>${renderReplacementPackageRows(replacementRows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderReplacementPackageArtifactManifestPanel() {
    const materialization = replacementPackageArtifactMaterializationState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const commit = packageSupersessionCommitState() || {};
    const manifest = replacementPackageArtifactManifestState() || {};
    const payloadRows = replacementPackageRows({
        packageKinds: manifest.replacement_package_kinds || replacementAuthority.replacement_package_kinds || [],
        payloadRefs: manifest.replacement_payload_refs || [],
        payloadHashes: manifest.replacement_payload_hashes || [],
    });
    const verifiedRows = replacementPackageRows({
        packageKinds: manifest.replacement_package_kinds || replacementAuthority.replacement_package_kinds || [],
        payloadRefs: manifest.verified_artifact_refs || manifest.replacement_payload_refs || [],
        payloadHashes: manifest.verified_artifact_hashes || manifest.replacement_payload_hashes || [],
    });
    const byteSizes = Array.isArray(manifest.verified_artifact_byte_sizes)
        ? manifest.verified_artifact_byte_sizes
        : [];
    const byteSizeRows = byteSizes.length
        ? byteSizes.map((size, index) => `<li><code>${escapeHtml(manifest.replacement_package_kinds?.[index] || `artifact_${index + 1}`)}</code> ${escapeHtml(size)}</li>`).join('')
        : '<li>No verified artifact byte sizes are available.</li>';
    const error = State.replacementPackageArtifactManifestError;
    const stateLabel = State.replacementPackageArtifactManifestPending
        ? 'replacement_package_artifact_manifest_recording'
        : (
            error?.error_code
            || manifest.next_state
            || (canSubmitReplacementPackageArtifactManifest()
                ? 'replacement_package_artifact_manifest_ready'
                : 'replacement_package_artifact_manifest_unavailable')
        );
    const statePill = error ? 'blocked' : (manifest.replacement_package_artifact_manifest_id ? 'ok' : 'preview');
    const downstream = manifest.downstream_unavailable || commit.downstream_unavailable || [];
    elements.replacementPackageArtifactManifestPanel.dataset.manifestState = stateLabel;
    elements.replacementPackageArtifactManifestPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(statePill)}">${escapeHtml(stateLabel)}</span>
            <span class="rail-label">${escapeHtml(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RENDERED_MODE)}</span>
        </div>
        <div class="result-review-grid replacement-package-artifact-manifest-grid">
            <section class="result-review-card">
                <strong>Rendered Control</strong>
                <ul>
                    ${fieldItem('use case', REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_USE_CASE, { code: true })}
                    ${fieldItem('response authority', REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('operator decision', REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION, { code: true })}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Basis</strong>
                <ul>
                    ${fieldItem('materialization id', materialization.replacement_artifact_materialization_id || manifest.replacement_artifact_materialization_id, { code: true })}
                    ${fieldItem('materialization basis', materialization.materialization_basis_hash || manifest.materialization_basis_hash, { code: true })}
                    ${fieldItem('replacement authority id', replacementAuthority.replacement_package_set_authority_id || manifest.replacement_package_set_authority_id, { code: true })}
                    ${fieldItem('replacement authority basis', replacementAuthority.authority_basis_hash || manifest.replacement_authority_basis_hash, { code: true })}
                    ${fieldItem('supersession commit id', commit.package_supersession_commit_id || manifest.package_supersession_commit_id, { code: true })}
                    ${fieldItem('supersession commit basis', commit.commit_basis_hash || manifest.package_supersession_commit_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Manifest Result</strong>
                <ul>
                    ${fieldItem('schema id', manifest.schema_id, { code: true })}
                    ${fieldItem('status', manifest.status)}
                    ${fieldItem('manifest id', manifest.replacement_package_artifact_manifest_id, { code: true })}
                    ${fieldItem('mode', manifest.replacement_package_artifact_manifest_mode, { code: true })}
                    ${fieldItem('source gate', manifest.source_gate, { code: true })}
                    ${fieldItem('record-from-authority decision', manifest.record_from_authority_operator_decision, { code: true })}
                    ${fieldItem('manifest hash', manifest.artifact_manifest_hash, { code: true })}
                    ${fieldItem('authority basis hash', manifest.authority_basis_hash, { code: true })}
                    ${fieldItem('next state', manifest.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Capability Flags</strong>
                <ul>
                    ${fieldItem('manifest record persisted', manifest.manifest_record_persisted)}
                    ${fieldItem('artifact generation', manifest.artifact_generation_enabled)}
                    ${fieldItem('package row mutation', manifest.package_row_mutation_enabled)}
                    ${fieldItem('package payload write', manifest.package_payload_write_enabled)}
                    ${fieldItem('L3 output package write', manifest.l3_output_package_write_enabled)}
                    ${fieldItem('broad package mutation', manifest.broad_package_mutation_enabled)}
                    ${fieldItem('connector dispatch', manifest.connector_dispatch_enabled)}
                    ${fieldItem('provider public URL', manifest.provider_public_url_enabled)}
                    ${fieldItem('source widening', manifest.source_widening_enabled)}
                    ${fieldItem('qualitative/RAG execution', manifest.qualitative_hybrid_rag_execution_enabled)}
                    ${fieldItem('frontend durable authority', manifest.frontend_only_durable_state_enabled)}
                </ul>
            </section>
            <section class="result-review-card replacement-package-artifact-manifest-rows">
                <strong>Replacement Payload Refs</strong>
                <ul>${renderReplacementPackageRows(payloadRows)}</ul>
            </section>
            <section class="result-review-card replacement-package-artifact-manifest-rows">
                <strong>Verified Artifact Refs</strong>
                <ul>${renderReplacementPackageRows(verifiedRows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Verified Artifact Sizes</strong>
                <ul>${byteSizeRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderReplacementPackageNamespaceRows(rows) {
    return rows.length
        ? rows.map((row) => {
            const sourceRef = safePackagePayloadRefForDisplay(row.source_payload_ref);
            const artifactRef = safePackagePayloadRefForDisplay(row.artifact_ref);
            return `
                <li>
                    <code>${escapeHtml(row.package_kind || 'unknown_package_kind')}</code>
                    ${row.source_output_package_id ? `<code>${escapeHtml(row.source_output_package_id)}</code>` : ''}
                    ${row.package_schema_id ? `<code>${escapeHtml(row.package_schema_id)}</code>` : ''}
                    ${sourceRef ? `<code>${escapeHtml(sourceRef)}</code>` : ''}
                    ${row.source_payload_hash ? `<code>${escapeHtml(row.source_payload_hash)}</code>` : ''}
                    ${artifactRef ? `<code>${escapeHtml(artifactRef)}</code>` : ''}
                    ${row.artifact_hash ? `<code>${escapeHtml(row.artifact_hash)}</code>` : ''}
                </li>
            `;
        }).join('')
        : '<li>No namespace candidate rows are available.</li>';
}

function renderReplacementPackageNamespaceHistoryRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.package_kind || 'unknown_package_kind')}</code>
                <span>status: ${escapeHtml(displayValue(row.status))}</span>
                <code>${escapeHtml(row.replacement_output_package_id || 'no_replacement_output_package_id')}</code>
                <code>${escapeHtml(row.authority_basis_hash || 'no_authority_basis_hash')}</code>
            </li>
        `).join('')
        : '<li>No namespace receipt history has been recorded in this rendered session.</li>';
}

function renderReplacementPackageNamespacePanel() {
    const namespace = replacementPackageNamespaceState() || {};
    const manifest = replacementPackageArtifactManifestState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const commit = packageSupersessionCommitState() || {};
    const candidates = replacementPackageNamespaceCandidateRows();
    const selectedRow = selectedReplacementPackageNamespaceRow() || {};
    const error = State.replacementPackageNamespaceError;
    const stateLabel = State.replacementPackageNamespacePending
        ? 'replacement_package_namespace_recording'
        : (
            error?.error_code
            || namespace.next_state
            || (canSubmitReplacementPackageNamespace()
                ? 'replacement_package_namespace_ready'
                : (stableHashAvailable()
                    ? 'replacement_package_namespace_unavailable'
                    : 'replacement_package_namespace_hashing_unavailable'))
        );
    const statePill = error ? 'blocked' : (namespace.replacement_output_package_id ? 'ok' : 'preview');
    const downstream = namespace.downstream_unavailable || manifest.downstream_unavailable || [];
    elements.replacementPackageNamespacePanel.dataset.namespaceState = stateLabel;
    elements.replacementPackageNamespacePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(statePill)}">${escapeHtml(stateLabel)}</span>
            <span class="rail-label">${escapeHtml(REPLACEMENT_PACKAGE_NAMESPACE_RENDERED_MODE)}</span>
        </div>
        <div class="result-review-grid replacement-package-namespace-grid">
            <section class="result-review-card">
                <strong>Rendered Control</strong>
                <ul>
                    ${fieldItem('use case', REPLACEMENT_PACKAGE_NAMESPACE_USE_CASE, { code: true })}
                    ${fieldItem('response authority', REPLACEMENT_PACKAGE_NAMESPACE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('operator decision', REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION, { code: true })}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Basis</strong>
                <ul>
                    ${fieldItem('manifest id', manifest.replacement_package_artifact_manifest_id || selectedRow.replacement_artifact_manifest_id, { code: true })}
                    ${fieldItem('manifest basis', manifest.authority_basis_hash || selectedRow.replacement_artifact_manifest_authority_basis_hash, { code: true })}
                    ${fieldItem('replacement authority id', replacementAuthority.replacement_package_set_authority_id || selectedRow.replacement_package_set_authority_id, { code: true })}
                    ${fieldItem('replacement authority basis', replacementAuthority.authority_basis_hash || selectedRow.replacement_package_set_authority_basis_hash, { code: true })}
                    ${fieldItem('supersession commit id', commit.package_supersession_commit_id || selectedRow.package_supersession_commit_id, { code: true })}
                    ${fieldItem('supersession commit basis', commit.commit_basis_hash || selectedRow.package_supersession_commit_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Selected Namespace Row</strong>
                <ul>
                    ${fieldItem('package kind', selectedRow.package_kind, { code: true })}
                    ${fieldItem('package schema id', selectedRow.package_schema_id, { code: true })}
                    ${fieldItem('source output package id', selectedRow.source_output_package_id, { code: true })}
                    ${fieldItem('source payload ref', safePackagePayloadRefForDisplay(selectedRow.source_payload_ref), { code: true })}
                    ${fieldItem('source payload hash', selectedRow.source_payload_hash, { code: true })}
                    ${fieldItem('artifact ref', safePackagePayloadRefForDisplay(selectedRow.artifact_ref), { code: true })}
                    ${fieldItem('artifact hash', selectedRow.artifact_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Namespace Result</strong>
                <ul>
                    ${fieldItem('schema id', namespace.schema_id, { code: true })}
                    ${fieldItem('status', namespace.status)}
                    ${fieldItem('replacement output package id', namespace.replacement_output_package_id, { code: true })}
                    ${fieldItem('mode', namespace.replacement_package_namespace_mode, { code: true })}
                    ${fieldItem('source gate', namespace.source_gate, { code: true })}
                    ${fieldItem('authority basis hash', namespace.authority_basis_hash, { code: true })}
                    ${fieldItem('next state', namespace.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Capability Flags</strong>
                <ul>
                    ${fieldItem('namespace row persisted', namespace.namespace_row_persisted)}
                    ${fieldItem('package row mutation', namespace.package_row_mutation_enabled)}
                    ${fieldItem('package payload write', namespace.package_payload_write_enabled)}
                    ${fieldItem('L3 output package write', namespace.l3_output_package_write_enabled)}
                    ${fieldItem('broad package mutation', namespace.broad_package_mutation_enabled)}
                    ${fieldItem('connector dispatch', namespace.connector_dispatch_enabled)}
                    ${fieldItem('provider public URL', namespace.provider_public_url_enabled)}
                    ${fieldItem('source widening', namespace.source_widening_enabled)}
                    ${fieldItem('qualitative/RAG execution', namespace.qualitative_hybrid_rag_execution_enabled)}
                    ${fieldItem('frontend durable authority', namespace.frontend_only_durable_state_enabled)}
                </ul>
            </section>
            <section class="result-review-card replacement-package-namespace-rows">
                <strong>Candidate Namespace Rows</strong>
                <ul>${renderReplacementPackageNamespaceRows(candidates)}</ul>
            </section>
            <section class="result-review-card replacement-package-namespace-rows">
                <strong>Rendered Session History</strong>
                <ul>${renderReplacementPackageNamespaceHistoryRows(State.replacementPackageNamespaceHistory)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderAuthorityMatrixReviewPanel() {
    const contract = authorityMatrixContract();
    const panelState = authorityMatrixReviewState(contract);
    const rows = contract?.authority_matrix || [];
    const blockedScope = [
        'runtime_behavior_blocked',
        'backend_route_behavior_blocked',
        'mutation_dispatch_blocked',
        'provider_public_delivery_use_blocked',
        'raw_public_url_display_use_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.authorityMatrixReviewPanel.dataset.reviewState = panelState.label;

    if (!contract) {
        elements.authorityMatrixReviewPanel.innerHTML = `
            <div class="result-review-status">
                <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
                <span class="rail-label">${escapeHtml(AUTHORITY_MATRIX_REVIEW_RENDERED_MODE)}</span>
            </div>
            <div class="result-review-grid authority-matrix-review-grid">
                <section class="result-review-card">
                    <strong>Bootstrap Contract</strong>
                    <ul>
                        ${fieldItem('response authority', AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY, { code: true })}
                        ${fieldItem('schema id', State.bootstrap?.authority_matrix_contract?.schema_id, { code: true })}
                        ${fieldItem('fail closed', 'blocked_no_runtime_authority', { code: true })}
                    </ul>
                </section>
                <section class="result-review-card">
                    <strong>Unavailable Boundary</strong>
                    <div class="downstream-locks">${renderDownstreamLocks(blockedScope)}</div>
                </section>
            </div>
        `;
        return;
    }

    elements.authorityMatrixReviewPanel.innerHTML = `
        <div class="section-heading">
            <div>
                <p class="eyebrow">Authority matrix</p>
                <h2>Rendered read-only authority review</h2>
            </div>
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
        </div>
        <div class="result-review-grid authority-matrix-review-grid">
            <section class="result-review-card">
                <strong>Review Authority</strong>
                <ul>
                    ${fieldItem('use case', AUTHORITY_MATRIX_REVIEW_USE_CASE, { code: true })}
                    ${fieldItem('rendered mode', AUTHORITY_MATRIX_REVIEW_RENDERED_MODE, { code: true })}
                    ${fieldItem('response authority', AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('exposure context', contract.exposure_context, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Contract Identity</strong>
                <ul>
                    ${fieldItem('schema id', contract.schema_id, { code: true })}
                    ${fieldItem('definition id', contract.contract_definition_id, { code: true })}
                    ${fieldItem('scope', contract.scope, { code: true })}
                    ${fieldItem('fail closed', contract.fail_closed_result, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Boundaries</strong>
                <ul>
                    ${fieldItem('mutation or dispatch', false)}
                    ${fieldItem('additional matrix route', false)}
                    ${fieldItem('provider-public delivery/use', false)}
                    ${fieldItem('raw public URL display/use', false)}
                    ${fieldItem('frontend durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card authority-matrix-review-rows">
                <strong>Authority Matrix Rows</strong>
                <ul>${authorityMatrixRowCards(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(blockedScope)}</div>
            </section>
        </div>
    `;
}

function renderDownstreamAccessLifecycleDashboardPanel() {
    const rows = downstreamAccessLifecycleRows();
    const dashboardState = downstreamAccessLifecycleDashboardState(rows);
    const external = externalExportDownloadPrepareState() || {};
    const downstream = currentDownstreamUnavailable() || [
        'external_connector_invocation_blocked',
        'destination_write_blocked',
        'provider_public_delivery_use_blocked',
        'raw_public_url_display_use_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.downstreamAccessLifecycleDashboardPanel.dataset.lifecycleState = dashboardState.label;
    elements.downstreamAccessLifecycleDashboardPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(dashboardState.pill)}">${escapeHtml(dashboardState.label)}</span>
            <span class="rail-label">${escapeHtml(DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE)}</span>
        </div>
        <div class="result-review-grid downstream-access-lifecycle-grid">
            <section class="result-review-card">
                <strong>Lifecycle Authority</strong>
                <ul>
                    ${fieldItem('use case', DOWNSTREAM_ACCESS_LIFECYCLE_USE_CASE, { code: true })}
                    ${fieldItem('response authority', DOWNSTREAM_ACCESS_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('session', currentSessionId(), { code: true })}
                    ${fieldItem('source gate', external.source_gate || external.package_construction_source_gate, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Access Boundaries</strong>
                <ul>
                    ${fieldItem('connector invocation', false)}
                    ${fieldItem('destination write', false)}
                    ${fieldItem('provider public delivery/use', false)}
                    ${fieldItem('raw public URL display/use', false)}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card downstream-access-lifecycle-rows">
                <strong>Downstream Lifecycle Rows</strong>
                <ul>${renderDownstreamAccessLifecycleRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function renderLayer3E2EGovernanceLifecycleDashboardPanel() {
    const rows = layer3E2EGovernanceLifecycleRows();
    const dashboardState = layer3E2EGovernanceLifecycleDashboardState(rows);
    const downstream = [
        'package_mutation_blocked',
        'external_connector_invocation_blocked',
        'destination_write_blocked',
        'provider_public_delivery_use_blocked',
        'raw_public_url_display_use_blocked',
        'source_expansion_blocked',
        'rag_vector_behavior_blocked',
        'auth_security_behavior_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.layer3E2EGovernanceLifecycleDashboardPanel.dataset.lifecycleState = dashboardState.label;
    elements.layer3E2EGovernanceLifecycleDashboardPanel.innerHTML = `
        <div class="section-heading">
            <div>
                <p class="eyebrow">End-to-end governance lifecycle</p>
                <h2>Layer 3 server-authoritative lifecycle</h2>
            </div>
            <span class="status-pill ${escapeHtml(dashboardState.pill)}">${escapeHtml(dashboardState.label)}</span>
        </div>
        <div class="result-review-grid layer3-e2e-governance-lifecycle-grid">
            <section class="result-review-card">
                <strong>Lifecycle Authority</strong>
                <ul>
                    ${fieldItem('use case', LAYER3_E2E_GOVERNANCE_LIFECYCLE_USE_CASE, { code: true })}
                    ${fieldItem('rendered mode', LAYER3_E2E_GOVERNANCE_LIFECYCLE_DASHBOARD_MODE, { code: true })}
                    ${fieldItem('response authority', LAYER3_E2E_GOVERNANCE_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('session', currentSessionId(), { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Boundaries</strong>
                <ul>
                    ${fieldItem('package mutation', false)}
                    ${fieldItem('connector/destination dispatch', false)}
                    ${fieldItem('provider-public delivery/use', false)}
                    ${fieldItem('raw public URL display/use', false)}
                    ${fieldItem('frontend durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card layer3-e2e-governance-lifecycle-rows">
                <strong>Lifecycle Rows</strong>
                <ul>${renderLayer3E2EGovernanceLifecycleRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function handoffExportPanelState() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    if (State.handoffExportPreparePending) {
        return { label: 'handoff_export_prepare_recording', pill: 'preview', message: 'Recording one prepare-only handoff/export decision.' };
    }
    if (recordedHandoffExportPrepare()) {
        return { label: handoff.handoff_export_state || handoff.next_state || handoff.state, pill: 'ok', message: 'Server state already contains a handoff/export preparation decision.' };
    }
    if (State.handoffExportPrepareError) {
        return { label: 'handoff_export_prepare_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest preparation action.' };
    }
    if (isSourceDirectoryQualitativePackageAuthoritySelected()) {
        return { label: 'source_directory_handoff_export_ready', pill: 'ok', message: 'Source-directory package review authority is ready for prepare-only handoff/export recording.' };
    }
    if (handoff.available === true && packageReviewState === 'package_review_approved') {
        return { label: handoff.state || 'handoff_export_ready', pill: 'ok', message: 'Approved package-review submit state is ready for prepare-only recording.' };
    }
    if (packageReviewState === 'package_review_approved') {
        return { label: handoff.state || 'handoff_export_unavailable', pill: 'blocked', message: handoff.blocked_reason || 'Preparation readiness is not available from the server summary.' };
    }
    return { label: handoff.state || 'handoff_export_unavailable', pill: 'blocked', message: 'Handoff/export preparation requires approved package-review submit state.' };
}

function renderCodeList(values, emptyText) {
    return values?.length
        ? values.map((value) => `<li><code>${escapeHtml(value)}</code></li>`).join('')
        : `<li>${escapeHtml(emptyText)}</li>`;
}

function renderHandoffExportPreparePanel() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const authority = selectedResultAuthority();
    const panelState = handoffExportPanelState();
    const sourceDirectoryMode = isSourceDirectoryQualitativePackageAuthoritySelected()
        || isSourceDirectoryQualitativeHandoffExportPrepareState(handoff);
    const sourceDirectoryPayload = sourceDirectoryMode
        ? sourceDirectoryQualitativePackageAuthorityPayloadOrNull() || {}
        : {};
    const packageReviewState = sourceDirectoryMode
        ? sourceDirectoryPayload.package_review_state || handoff.package_review_state || submit.package_review_state || submit.state
        : submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = handoff.handoff_export_state || handoff.next_state || handoff.state;
    const packageIds = sourceDirectoryMode && Array.isArray(sourceDirectoryPayload.output_package_ids)
        ? sourceDirectoryPayload.output_package_ids
        : packageOutputPackageIds();
    const packageKinds = sourceDirectoryMode && Array.isArray(sourceDirectoryPayload.package_kinds)
        ? sourceDirectoryPayload.package_kinds
        : packageKindsFromState();
    const payloadRefs = sourceDirectoryMode ? [] : packagePayloadRefs();
    const payloadHashes = sourceDirectoryMode && Array.isArray(sourceDirectoryPayload.payload_hashes)
        ? sourceDirectoryPayload.payload_hashes
        : packagePayloadHashes();
    const downstream = handoff.downstream_unavailable || submit.downstream_unavailable || ['aps_handoff', 'external_export', 'downstream_dispatch'];
    const envelope = handoff.handoff_export_envelope;
    const envelopeRows = envelope && typeof envelope === 'object'
        ? [
            fieldItem('schema', envelope.schema_id),
            fieldItem('package review submit ref', envelope.package_review_submit_record_ref, { code: true }),
            fieldItem('reconciliation', envelope.reconciliation_record_id, { code: true }),
            fieldItem('package count', Array.isArray(envelope.output_package_ids) ? envelope.output_package_ids.length : null),
        ].join('')
        : '<li>No preparation envelope has been recorded.</li>';

    elements.handoffExportPreparePanel.dataset.renderedMode = sourceDirectoryMode
        ? SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_RENDERED_MODE
        : 'rendered_handoff_export_prepare_control';
    elements.handoffExportPreparePanel.dataset.sourceAuthority = sourceDirectoryMode
        ? SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_SOURCE_AUTHORITY
        : 'selectedResultAuthority + State.sessionSummary.handoff_export_prepare';
    elements.handoffExportPreparePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Prepare Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('analysis run', handoff.analysis_run_id || authority.analysisRunId, { code: true })}
                    ${fieldItem('pass type', handoff.pass_type || submit.pass_type || authority.passType)}
                    ${fieldItem('pass scope', handoff.pass_scope || submit.pass_scope || authority.passScope)}
                    ${fieldItem('method', handoff.method || submit.method || authority.selectedMethod)}
                    ${fieldItem('source gate', handoff.source_gate || submit.source_gate || authority.sourceGate)}
                    ${sourceDirectoryMode ? fieldItem('source batch', sourceDirectoryPayload.source_ingestion_batch_id, { code: true }) : ''}
                    ${sourceDirectoryMode ? fieldItem('source file', sourceDirectoryPayload.source_ingestion_file_id, { code: true }) : ''}
                    ${fieldItem('package source gate', handoff.package_construction_source_gate || submit.package_construction_source_gate)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Package Review Submit</strong>
                <ul>
                    ${fieldItem('state', packageReviewState)}
                    ${fieldItem('submit ref', handoff.package_review_submit_record_ref || sourceDirectoryPayload.package_review_submit_record_ref || submit.submit_record_ref, { code: true })}
                    ${fieldItem('operator decision', submit.operator_decision)}
                    ${fieldItem('result review', handoff.result_review_record_ref || submit.result_review_record_ref, { code: true })}
                    ${fieldItem('package preview hash', handoff.package_review_preview_hash || submit.package_review_preview_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Handoff Contract</strong>
                <ul>
                    ${fieldItem('target', handoff.handoff_target || 'internal_export_envelope')}
                    ${fieldItem('mode', handoff.export_mode || 'prepare_only')}
                    ${fieldItem('route', sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_PATH : '/handoff/export/prepare', { code: true })}
                    ${fieldItem('source authority', sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_SOURCE_AUTHORITY : 'selected_result_authority', { code: true })}
                    ${fieldItem('state', prepareState)}
                    ${fieldItem('prepare enabled', handoff.handoff_export_prepare_enabled)}
                    ${fieldItem('prepare ref', handoff.prepare_record_ref, { code: true })}
                    ${fieldItem('operator decision', handoff.operator_decision)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Reviewed Packages</strong>
                <ul>${renderCodeList(packageKinds.map((kind, index) => `${kind}${packageIds[index] ? ` / ${packageIds[index]}` : ''}`), 'No reviewed package identities are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Refs</strong>
                <ul>${renderCodeList(payloadRefs, 'No package payload refs are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${renderCodeList(payloadHashes, 'No package payload hashes are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Reference Envelope</strong>
                <ul>${envelopeRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.handoffExportPrepareError)}
        </div>
    `;
}

function apsHandoffPanelState() {
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const prepareState = handoff.handoff_export_state || handoff.next_state || handoff.state;
    const stateName = apsHandoffStateName(aps);
    if (State.apsHandoffDispatchPending) {
        return { label: 'aps_handoff_ui_dispatching', pill: 'preview', message: 'Submitting one server-side APS handoff dispatch request.' };
    }
    if (recordedApsHandoffDispatch()) {
        return { label: stateName || 'aps_handoff_dispatched', pill: 'ok', message: 'Server state already contains a recorded APS handoff dispatch.' };
    }
    if (State.apsHandoffDispatchError) {
        return { label: State.apsHandoffDispatchError.error_code || 'aps_handoff_ui_error', pill: 'blocked', message: 'Server authority rejected or blocked the latest APS dispatch action.' };
    }
    if (stateName === 'aps_handoff_conflict') {
        return { label: stateName, pill: 'blocked', message: aps.blocked_reason || 'Existing APS handoff state conflicts with this workbench session.' };
    }
    if (stateName === 'aps_handoff_blocked') {
        return { label: stateName, pill: 'blocked', message: aps.blocked_reason || 'APS owner-service compatibility is blocked.' };
    }
    if (aps.available === true && stateName === 'aps_handoff_ready') {
        return { label: stateName, pill: 'ok', message: 'Prepared envelope authority is ready for server-side APS handoff dispatch.' };
    }
    if (prepareState === 'handoff_export_prepared') {
        return { label: stateName || 'aps_handoff_unavailable', pill: 'blocked', message: aps.blocked_reason || 'APS dispatch readiness is not available from the server summary.' };
    }
    return { label: stateName || 'aps_handoff_unavailable', pill: 'blocked', message: 'APS dispatch requires a recorded handoff_export_prepared envelope.' };
}

function renderApsHandoffDispatchPanel() {
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const authority = selectedResultAuthority();
    const panelState = apsHandoffPanelState();
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const packageKinds = packageKindsFromState();
    const packageIds = packageOutputPackageIds();
    const payloadRefs = packagePayloadRefs();
    const payloadHashes = packagePayloadHashes();
    const downstream = aps.downstream_unavailable || ['external_export', 'download', 'connector_dispatch', 'non_aps_dispatch'];

    elements.apsHandoffDispatchPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Dispatch Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('analysis run', handoff.analysis_run_id || authority.analysisRunId, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Prepared Envelope</strong>
                <ul>
                    ${fieldItem('package review state', packageReviewState)}
                    ${fieldItem('submit ref', handoff.package_review_submit_record_ref || submit.submit_record_ref, { code: true })}
                    ${fieldItem('prepare state', handoff.handoff_export_state || handoff.next_state || handoff.state)}
                    ${fieldItem('prepare ref', aps.prepare_record_ref || handoff.prepare_record_ref, { code: true })}
                    ${fieldItem('envelope ref', aps.handoff_export_envelope_ref || handoffExportEnvelopeRef(handoff), { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>APS Dispatch Contract</strong>
                <ul>
                    ${fieldItem('target', aps.aps_handoff_target || 'aps_evidence_bundle')}
                    ${fieldItem('mode', aps.dispatch_mode || 'server_side_aps_handoff')}
                    ${fieldItem('decision', aps.operator_decision || 'dispatch_aps_handoff')}
                    ${fieldItem('state', apsHandoffStateName(aps))}
                    ${fieldItem('record ref', aps.aps_handoff_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Packages</strong>
                <ul>${renderCodeList(packageKinds.map((kind, index) => `${kind}${packageIds[index] ? ` / ${packageIds[index]}` : ''}`), 'No reviewed package identities are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Refs</strong>
                <ul>${renderCodeList(payloadRefs, 'No source payload refs are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${renderCodeList(payloadHashes, 'No source payload hashes are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>APS Output</strong>
                <ul>
                    ${fieldItem('package id', aps.aps_output_package_id, { code: true })}
                    ${fieldItem('package kind', aps.aps_output_package_kind)}
                    ${fieldItem('bundle ref', aps.aps_bundle_ref, { code: true })}
                    ${fieldItem('bundle id', aps.aps_bundle_id, { code: true })}
                    ${fieldItem('schema', aps.aps_schema_id)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.apsHandoffDispatchError)}
        </div>
    `;
}

function externalExportDownloadPanelState() {
    const external = externalExportDownloadPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const stateName = externalExportDownloadStateName(external);
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    if (State.externalExportDownloadPreparePending) {
        return { label: 'external_export_download_ui_preparing', pill: 'preview', message: 'Submitting one reference-only readiness request.' };
    }
    if (recordedExternalExportDownloadPrepare()) {
        return { label: stateName || 'external_export_download_prepared', pill: 'ok', message: 'Server state already contains recorded external export/download readiness.' };
    }
    if (State.externalExportDownloadPrepareError) {
        return { label: State.externalExportDownloadPrepareError.error_code || 'external_export_download_ui_error', pill: 'blocked', message: 'Server authority rejected or blocked the latest readiness action.' };
    }
    if (stateName === 'external_export_download_conflict') {
        return { label: stateName, pill: 'blocked', message: external.blocked_reason || 'Existing external export/download readiness conflicts with this workbench session.' };
    }
    if (stateName === 'external_export_download_blocked') {
        return { label: stateName, pill: 'blocked', message: external.blocked_reason || 'External export/download readiness is blocked by server authority.' };
    }
    if (isSourceDirectoryQualitativeHandoffExportPrepareState(handoffExportPrepareState() || {})) {
        return { label: 'source_directory_external_export_download_ready', pill: 'ok', message: 'Prepared source-directory handoff envelope is ready for reference-only external export/download readiness.' };
    }
    if (external.available === true && stateName === 'external_export_download_ready') {
        return { label: stateName, pill: 'ok', message: 'Recorded APS handoff dispatch is ready for reference-only external export/download readiness.' };
    }
    if (apsState === 'aps_handoff_dispatched') {
        return { label: stateName || 'external_export_download_unavailable', pill: 'blocked', message: external.blocked_reason || 'External export/download readiness is not available from the server summary.' };
    }
    return { label: stateName || 'external_export_download_unavailable', pill: 'blocked', message: 'External export/download readiness requires recorded APS handoff dispatch.' };
}

function renderExternalExportDownloadPreparePanel() {
    const external = externalExportDownloadPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const authority = selectedResultAuthority();
    const panelState = externalExportDownloadPanelState();
    const sourceDirectoryMode = isSourceDirectoryQualitativeHandoffExportPrepareState(handoff)
        || isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external);
    const sourceDirectoryPayload = sourceDirectoryMode
        ? sourceDirectoryQualitativePackageAuthorityPayloadOrNull() || {}
        : {};
    const packageReviewState = external.package_review_state
        || handoff.package_review_state
        || sourceDirectoryPayload.package_review_state
        || submit.package_review_state
        || submit.state;
    const prepareState = external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state;
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    const packageKinds = Array.isArray(external.package_kinds) && external.package_kinds.length
        ? external.package_kinds
        : (sourceDirectoryMode && Array.isArray(sourceDirectoryPayload.package_kinds)
            ? sourceDirectoryPayload.package_kinds
            : packageKindsFromState());
    const packageIds = Array.isArray(external.output_package_ids) && external.output_package_ids.length
        ? external.output_package_ids
        : (sourceDirectoryMode && Array.isArray(sourceDirectoryPayload.output_package_ids)
            ? sourceDirectoryPayload.output_package_ids
            : packageOutputPackageIds());
    const payloadRefs = sourceDirectoryMode
        ? []
        : (Array.isArray(external.payload_refs) && external.payload_refs.length ? external.payload_refs : packagePayloadRefs());
    const payloadHashes = Array.isArray(external.payload_hashes) && external.payload_hashes.length
        ? external.payload_hashes
        : (sourceDirectoryMode && Array.isArray(sourceDirectoryPayload.payload_hashes)
            ? sourceDirectoryPayload.payload_hashes
            : packagePayloadHashes());
    const downstream = external.downstream_unavailable || [
        'browser_download',
        'download_url',
        'connector_dispatch',
        'destination_selection',
        'generic_downstream_dispatch',
    ];
    const descriptor = external.external_export_download_descriptor;
    const descriptorRows = descriptor && typeof descriptor === 'object'
        ? [
            fieldItem('descriptor ref', descriptor.descriptor_ref, { code: true }),
            fieldItem('source artifact', descriptor.source_artifact_ref, { code: true }),
            fieldItem('target', descriptor.export_download_target),
            fieldItem('mode', descriptor.download_mode),
            fieldItem('browser download enabled', descriptor.browser_download_enabled),
            fieldItem('download URL enabled', descriptor.download_url_enabled),
        ].join('')
        : '<li>No readiness descriptor has been recorded.</li>';

    elements.externalExportDownloadPreparePanel.dataset.renderedMode = sourceDirectoryMode
        ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RENDERED_MODE
        : 'rendered_external_export_download_prepare_control';
    elements.externalExportDownloadPreparePanel.dataset.sourceAuthority = sourceDirectoryMode
        ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_AUTHORITY
        : 'State.sessionSummary.external_export_download';
    elements.externalExportDownloadPreparePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Readiness Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('result review', external.result_review_record_ref || handoff.result_review_record_ref || submit.result_review_record_ref, { code: true })}
                    ${sourceDirectoryMode ? fieldItem('source batch', sourceDirectoryPayload.source_ingestion_batch_id, { code: true }) : ''}
                    ${sourceDirectoryMode ? fieldItem('source file', sourceDirectoryPayload.source_ingestion_file_id, { code: true }) : ''}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Upstream State</strong>
                <ul>
                    ${fieldItem('package review state', packageReviewState)}
                    ${fieldItem('submit ref', external.package_review_submit_record_ref || handoff.package_review_submit_record_ref || sourceDirectoryPayload.package_review_submit_record_ref || submit.submit_record_ref, { code: true })}
                    ${fieldItem('prepare state', prepareState)}
                    ${fieldItem('prepare ref', external.prepare_record_ref || handoff.prepare_record_ref, { code: true })}
                    ${fieldItem('APS state', apsState)}
                    ${fieldItem('APS record ref', external.aps_handoff_record_ref || aps.aps_handoff_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Readiness Contract</strong>
                <ul>
                    ${fieldItem('target', external.export_download_target || (sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_TARGET : 'aps_evidence_bundle_download_reference'))}
                    ${fieldItem('mode', external.download_mode || 'reference_only_prepare')}
                    ${fieldItem('route', sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH : '/handoff/export/download/prepare', { code: true })}
                    ${fieldItem('source authority', sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_AUTHORITY : 'State.sessionSummary.external_export_download', { code: true })}
                    ${fieldItem('decision', external.operator_decision || (sourceDirectoryMode ? 'prepare_source_directory_external_export_download' : 'prepare_external_export_download'))}
                    ${fieldItem('state', externalExportDownloadStateName(external))}
                    ${fieldItem('prepare enabled', external.external_export_download_prepare_enabled)}
                    ${fieldItem('readiness ref', external.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', external.export_download_descriptor_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source APS Bundle</strong>
                <ul>
                    ${fieldItem('package id', external.aps_output_package_id || aps.aps_output_package_id, { code: true })}
                    ${fieldItem('package kind', external.aps_output_package_kind || aps.aps_output_package_kind)}
                    ${fieldItem('bundle ref', external.aps_bundle_ref || aps.aps_bundle_ref, { code: true })}
                    ${fieldItem('bundle id', external.aps_bundle_id || aps.aps_bundle_id, { code: true })}
                    ${fieldItem('schema', external.aps_schema_id || aps.aps_schema_id)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Artifact</strong>
                <ul>
                    ${fieldItem('artifact ref', external.source_artifact_ref || external.aps_bundle_ref || aps.aps_bundle_ref, { code: true })}
                    ${fieldItem('artifact schema', external.source_artifact_schema_id)}
                    ${fieldItem('artifact hash', external.source_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', external.source_artifact_size_bytes)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Reviewed Packages</strong>
                <ul>${renderCodeList(packageKinds.map((kind, index) => `${kind}${packageIds[index] ? ` / ${packageIds[index]}` : ''}`), 'No reviewed package identities are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Refs</strong>
                <ul>${renderCodeList(payloadRefs, 'No source payload refs are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${renderCodeList(payloadHashes, 'No source payload hashes are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Readiness Descriptor</strong>
                <ul>${descriptorRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.externalExportDownloadPrepareError)}
        </div>
    `;
}

function externalExportDownloadDeliveryPanelState() {
    const external = externalExportDownloadPrepareState() || {};
    const stateName = externalExportDownloadStateName(external);
    const sourceDirectory = isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external);
    const associatedCohort = isAssociatedCohortExternalExportDownloadState(external);
    const sourceIntake = isSourceIntakeExternalExportDownloadState(external);
    const deliveryUi = sourceDirectoryQualitativeExternalExportDownloadDeliveryUiState(external)
        || sourceIntakeDeliveryUiState(external)
        || qualitativeApsDeliveryUiState(external)
        || associatedCohortDeliveryUiState(external)
        || serverExternalExportDownloadDeliveryUiState(external);
    if (State.externalExportDownloadDeliveryPending) {
        return { label: 'external_export_download_delivery_ui_downloading', pill: 'preview', message: 'Submitting one same-origin attachment request for browser-managed download.' };
    }
    if (externalExportDownloadDeliveryStateName() === 'external_export_download_delivery_submitted') {
        return { label: 'external_export_download_delivery_submitted', pill: 'preview', message: 'The same-origin delivery request was submitted; final download handling is browser-managed.' };
    }
    if (recordedExternalExportDownloadDelivery()) {
        return { label: State.externalExportDownloadDelivery.state || 'external_export_download_delivered', pill: 'ok', message: 'The browser received the same-origin delivery request; download handling is browser-managed.' };
    }
    if (State.externalExportDownloadDeliveryError) {
        const errorCode = State.externalExportDownloadDeliveryError.error_code || 'external_export_download_delivery_ui_error';
        const isConflict = State.externalExportDownloadDeliveryError.status === 'conflict' || errorCode.includes('conflict') || errorCode.includes('mismatch');
        return { label: errorCode, pill: 'blocked', message: isConflict ? 'Server authority rejected the delivery request as stale or conflicting.' : 'Server authority rejected or blocked the delivery request.' };
    }
    if (stateName === 'external_export_download_prepared' && canSubmitExternalExportDownloadDelivery()) {
        return { label: 'external_export_download_delivery_ui_ready', pill: 'ok', message: 'Recorded readiness can be delivered as a same-origin attachment.' };
    }
    if (stateName === 'external_export_download_prepared' && sourceDirectory && deliveryUi?.available !== true) {
        return { label: deliveryUi?.state || 'source_directory_external_export_download_delivery_ui_blocked', pill: 'blocked', message: 'Source-directory delivery requires complete server readiness authority before the rendered control can submit.' };
    }
    if (stateName === 'external_export_download_prepared' && sourceIntake && deliveryUi?.available !== true) {
        return { label: deliveryUi?.state || 'source_intake_external_export_download_delivery_ui_blocked', pill: 'blocked', message: 'Source-intake delivery requires complete server prepare authority before the rendered control can submit.' };
    }
    if (stateName === 'external_export_download_prepared' && associatedCohort && deliveryUi?.available !== true) {
        return { label: deliveryUi?.state || 'associated_cohort_external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Associated-cohort delivery requires explicit server UI authority before the rendered control can submit.' };
    }
    if (stateName === 'external_export_download_prepared') {
        return { label: 'external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Recorded readiness is present, but the server summary is missing required delivery basis.' };
    }
    return { label: 'external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before delivery.' };
}

function renderExternalExportDownloadDeliveryPanel() {
    const external = externalExportDownloadPrepareState() || {};
    const panelState = externalExportDownloadDeliveryPanelState();
    const sourceDirectoryMode = isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external);
    const deliveryUi = sourceDirectoryQualitativeExternalExportDownloadDeliveryUiState(external)
        || sourceIntakeDeliveryUiState(external)
        || qualitativeApsDeliveryUiState(external)
        || associatedCohortDeliveryUiState(external)
        || serverExternalExportDownloadDeliveryUiState(external)
        || {};
    const downstream = [
        'public_url',
        'signed_url',
        'connector_dispatch',
        'destination_selection',
        'generic_downstream_dispatch',
    ];
    const delivery = State.externalExportDownloadDelivery || {};
    const sourceDirectoryStatus = State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus || {};
    const descriptor = external.external_export_download_descriptor || {};
    elements.externalExportDownloadDeliveryPanel.dataset.renderedMode = sourceDirectoryMode
        ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RENDERED_MODE
        : 'rendered_external_export_download_delivery_control';
    elements.externalExportDownloadDeliveryPanel.dataset.sourceAuthority = sourceDirectoryMode
        ? 'State.externalExportDownloadPrepare + sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus'
        : 'State.sessionSummary.external_export_download';
    elements.externalExportDownloadDeliveryPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Delivery Gate</strong>
                <ul>
                    ${fieldItem('readiness state', externalExportDownloadStateName(external))}
                    ${fieldItem('readiness ref', external.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', external.export_download_descriptor_ref || descriptor.descriptor_ref, { code: true })}
                    ${fieldItem('target', external.export_download_target || descriptor.export_download_target || (sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_TARGET : 'aps_evidence_bundle_download_reference'))}
                    ${fieldItem('download mode', external.download_mode || descriptor.download_mode || 'reference_only_prepare')}
                    ${fieldItem('delivery mode', 'same_origin_artifact_stream')}
                    ${fieldItem('decision', sourceDirectoryMode ? 'deliver_source_directory_external_export_download' : 'deliver_external_export_download')}
                    ${fieldItem('delivery route', sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH : '/handoff/export/download/deliver', { code: true })}
                    ${fieldItem('status route', sourceDirectoryMode ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH : 'not_required_for_generic_delivery', { code: true })}
                    ${fieldItem('server UI state', deliveryUi.state)}
                    ${fieldItem('server UI available', deliveryUi.available)}
                    ${fieldItem('server UI basis', deliveryUi.server_authority)}
                    ${fieldItem('source-intake record', external.source_intake_record_id, { code: true })}
                    ${fieldItem('source-intake candidate', external.candidate_id, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Basis</strong>
                <ul>
                    ${fieldItem('package review state', external.package_review_state)}
                    ${fieldItem('handoff state', external.handoff_export_state)}
                    ${fieldItem('APS state', external.aps_handoff_state)}
                    ${fieldItem('submit ref', external.package_review_submit_record_ref, { code: true })}
                    ${fieldItem('prepare ref', external.prepare_record_ref, { code: true })}
                    ${fieldItem('APS record ref', external.aps_handoff_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Artifact</strong>
                <ul>
                    ${fieldItem('artifact ref', external.source_artifact_ref || external.aps_bundle_ref, { code: true })}
                    ${fieldItem('artifact schema', external.source_artifact_schema_id || external.aps_schema_id)}
                    ${fieldItem('artifact hash', external.source_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', external.source_artifact_size_bytes)}
                    ${fieldItem('safe filename', delivery.filename)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Completed Attempt</strong>
                <ul>
                    ${fieldItem('state', delivery.state)}
                    ${fieldItem('schema', delivery.schemaId)}
                    ${fieldItem('status schema', sourceDirectoryStatus.schema_id)}
                    ${fieldItem('status available', sourceDirectoryStatus.delivery_available)}
                    ${fieldItem('record ref', delivery.externalExportDownloadRecordRef, { code: true })}
                    ${fieldItem('source hash', delivery.sourceArtifactHash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusError)}
            ${renderErrorCard(State.externalExportDownloadDeliveryError)}
        </div>
    `;
}

function externalExportDownloadSignedReferencePanelState() {
    const external = externalExportDownloadPrepareState() || {};
    const stateName = externalExportDownloadStateName(external);
    if (State.externalExportDownloadSignedReferenceUsePending) {
        return { label: 'external_export_download_signed_reference_using', pill: 'preview', message: 'Using one server-generated same-origin signed reference.' };
    }
    if (State.externalExportDownloadSignedReferenceUse) {
        return { label: State.externalExportDownloadSignedReferenceUse.state || 'external_export_download_signed_reference_delivered', pill: 'ok', message: 'The signed reference was accepted and used through the same-origin endpoint.' };
    }
    if (State.externalExportDownloadSignedReferencePending) {
        return { label: 'external_export_download_signed_reference_generating', pill: 'preview', message: 'Requesting one short-lived server-owned signed reference.' };
    }
    if (State.externalExportDownloadSignedReferenceError) {
        return {
            label: State.externalExportDownloadSignedReferenceError.error_code || 'external_export_download_signed_reference_ui_error',
            pill: 'blocked',
            message: 'Server authority rejected or blocked the signed-reference request.',
        };
    }
    if (State.externalExportDownloadSignedReference?.signed_reference_state === 'external_export_download_signed_reference_ready') {
        return { label: 'external_export_download_signed_reference_ready', pill: 'ok', message: 'A short-lived same-origin signed reference is ready for use.' };
    }
    if (stateName === 'external_export_download_prepared' && externalExportDownloadDeliveryUiAdmitted()) {
        return { label: 'external_export_download_signed_reference_ui_ready', pill: 'ok', message: 'Recorded readiness and explicit delivery UI authority can generate a same-origin signed reference.' };
    }
    if (stateName === 'external_export_download_prepared') {
        return { label: 'external_export_download_signed_reference_ui_blocked', pill: 'blocked', message: 'Signed-reference controls require the same server delivery UI authority used by same-origin delivery.' };
    }
    return { label: 'external_export_download_signed_reference_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before signed-reference generation.' };
}

function renderExternalExportDownloadSignedReferencePanel() {
    const external = externalExportDownloadPrepareState() || {};
    const signed = State.externalExportDownloadSignedReference || {};
    const used = State.externalExportDownloadSignedReferenceUse || {};
    const panelState = externalExportDownloadSignedReferencePanelState();
    const downstream = [
        'public_url',
        'provider_signed_url',
        'connector_dispatch',
        'destination_selection',
        'durable_token_state',
        'receipt_audit_revocation_state',
    ];
    elements.externalExportDownloadSignedReferencePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Signed Reference Gate</strong>
                <ul>
                    ${fieldItem('readiness state', externalExportDownloadStateName(external))}
                    ${fieldItem('readiness ref', external.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', external.export_download_descriptor_ref, { code: true })}
                    ${fieldItem('delivery UI admitted', externalExportDownloadDeliveryUiAdmitted(external))}
                    ${fieldItem('delivery mode', 'same_origin_signed_delivery_reference')}
                    ${fieldItem('server authority', signed.server_authority || 'associated_cohort_external_export_download_signed_reference_gate')}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Generated Reference</strong>
                <ul>
                    ${fieldItem('state', signed.signed_reference_state)}
                    ${fieldItem('expires at', signed.signed_reference_expires_at)}
                    ${fieldItem('expires in seconds', signed.signed_reference_expires_in_seconds)}
                    ${fieldItem('use endpoint', signed.signed_reference_use_endpoint, { code: true })}
                    ${fieldItem('token prefix', signed.signed_reference_token ? `${String(signed.signed_reference_token).slice(0, 18)}...` : 'none', { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Artifact Basis</strong>
                <ul>
                    ${fieldItem('artifact ref', signed.source_artifact_ref || external.source_artifact_ref || external.aps_bundle_ref, { code: true })}
                    ${fieldItem('artifact hash', signed.source_artifact_hash || external.source_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', signed.source_artifact_size_bytes || external.source_artifact_size_bytes)}
                    ${fieldItem('pass type', signed.pass_type || external.pass_type)}
                    ${fieldItem('method', signed.method || external.method)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Use Result</strong>
                <ul>
                    ${fieldItem('state', used.state)}
                    ${fieldItem('schema', used.schemaId)}
                    ${fieldItem('source hash', used.sourceArtifactHash, { code: true })}
                    ${fieldItem('expires at', used.expiresAt)}
                    ${fieldItem('content type', used.contentType)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.externalExportDownloadSignedReferenceError)}
        </div>
    `;
}

function connectorLocalDestinationReceiptPanelState() {
    const status = connectorLocalDestinationReceiptStatusState() || {};
    const stateName = connectorLocalDestinationReceiptStateName(status);
    if (stateName === 'connector_local_destination_receipt_recorded') {
        return {
            label: 'connector_local_destination_receipt_recorded',
            pill: 'ok',
            message: 'The server has recorded an internal fake/local destination receipt for this connector authority.',
        };
    }
    if (status.available === true && stateName === 'connector_local_destination_receipt_ready') {
        return {
            label: 'connector_local_destination_receipt_ready',
            pill: 'ok',
            message: 'Existing connector dispatch and external export/download readiness can support a local receipt.',
        };
    }
    return {
        label: status.blocked_reason || 'connector_local_destination_receipt_unavailable',
        pill: 'blocked',
        message: 'The read-only status surface is waiting on server-owned connector dispatch and readiness state.',
    };
}

function connectorLocalDestinationReceiptLifecycle(status) {
    return status?.lifecycle_status_surface || {};
}

function connectorLocalDestinationReceiptHistoryRows(status) {
    const lifecycle = connectorLocalDestinationReceiptLifecycle(status);
    if (Array.isArray(lifecycle.receipt_history)) return lifecycle.receipt_history;
    if (Array.isArray(status?.receipt_history)) return status.receipt_history;
    return [];
}

function connectorLocalDestinationReceiptFailureRows(status) {
    const lifecycle = connectorLocalDestinationReceiptLifecycle(status);
    if (Array.isArray(lifecycle.failure_state_projection)) return lifecycle.failure_state_projection;
    if (Array.isArray(status?.failure_state_projection)) return status.failure_state_projection;
    return [];
}

function renderConnectorLocalDestinationReceiptHistory(status) {
    const history = connectorLocalDestinationReceiptHistoryRows(status);
    if (!history.length) {
        return '<li>history: none</li>';
    }
    return history.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.connector_local_destination_receipt_id || 'pending')}</code>: ${escapeHtml(row.connector_local_destination_receipt_state || 'unknown')} / <code>${escapeHtml(row.authority_basis_hash || 'no-authority-hash')}</code></li>`
    )).join('');
}

function renderConnectorLocalDestinationReceiptFailureProjection(status) {
    const rows = connectorLocalDestinationReceiptFailureRows(status);
    if (!rows.length) {
        return '<li>guardrails: unavailable</li>';
    }
    return rows.slice(0, 8).map((row) => (
        `<li>${escapeHtml(row.case)}: ${escapeHtml(row.projected_error_code || row.operator_status || 'status-only')}</li>`
    )).join('');
}

function renderConnectorLocalDestinationReceiptStatusPanel() {
    const status = connectorLocalDestinationReceiptStatusState() || {};
    const panelState = connectorLocalDestinationReceiptPanelState();
    const lifecycle = connectorLocalDestinationReceiptLifecycle(status);
    const idempotency = status.idempotency_policy || lifecycle.idempotency_policy || {};
    const retry = status.retry_policy || lifecycle.retry_policy || {};
    const downstream = status.downstream_unavailable || [
        'external_connector_invocation',
        'destination_write',
        'connector_run_creation',
        'real_destination_integration',
        'network_write',
        'provider_public_url',
        'package_mutation_reconstruction',
        'source_upload_expansion',
        'broad_qualitative_hybrid_rag_execution',
        'full_mockup_activation',
    ];
    elements.connectorLocalDestinationReceiptPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Local Receipt Status</strong>
                <ul>
                    ${fieldItem('rendered mode', CONNECTOR_LOCAL_RECEIPT_STATUS_SURFACE_MODE)}
                    ${fieldItem('use case', CONNECTOR_LOCAL_RECEIPT_STATUS_USE_CASE)}
                    ${fieldItem('response authority', CONNECTOR_LOCAL_RECEIPT_STATUS_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('state', connectorLocalDestinationReceiptStateName(status))}
                    ${fieldItem('available', status.available)}
                    ${fieldItem('blocked reason', status.blocked_reason)}
                    ${fieldItem('lifecycle surface', lifecycle.surface_mode)}
                    ${fieldItem('history count', status.receipt_history_count ?? lifecycle.history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Chain</strong>
                <ul>
                    ${fieldItem('session', status.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('pass run', status.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('reconciliation', status.reconciliation_record_id, { code: true })}
                    ${fieldItem('connector record', status.connector_dispatch_record_ref, { code: true })}
                    ${fieldItem('external readiness', status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('authority hash', status.authority_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Receipt Target</strong>
                <ul>
                    ${fieldItem('receipt id', status.connector_local_destination_receipt_id, { code: true })}
                    ${fieldItem('target', status.destination_target || 'layer3_internal_fake_local_destination_receipt')}
                    ${fieldItem('mode', status.dispatch_mode || 'internal_fake_local_destination_receipt_only')}
                    ${fieldItem('decision', status.operator_decision || 'record_internal_fake_local_destination_receipt')}
                    ${fieldItem('redacted artifact', status.accepted_artifact_ref, { code: true })}
                    ${fieldItem('artifact hash', status.accepted_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', status.accepted_artifact_size_bytes)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Lifecycle Policy</strong>
                <ul>
                    ${fieldItem('history authority', lifecycle.history_listing_authority)}
                    ${fieldItem('audit authority', lifecycle.audit_trail_authority)}
                    ${fieldItem('same key replay', idempotency.same_key_same_payload_replay)}
                    ${fieldItem('same key conflict', idempotency.same_key_different_payload_conflict)}
                    ${fieldItem('same basis conflict', idempotency.same_basis_different_client_request_id)}
                    ${fieldItem('retry fields', retry.retry_fields_admitted === false ? 'blocked' : retry.retry_fields_admitted)}
                    ${fieldItem('replay semantics', retry.replay_semantics)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Receipt History</strong>
                <ul>
                    ${renderConnectorLocalDestinationReceiptHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Guardrail Projection</strong>
                <ul>
                    ${renderConnectorLocalDestinationReceiptFailureProjection(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <ul>
                    ${fieldItem('external connector invocation', status.external_connector_invocation_enabled === false ? 'blocked' : status.external_connector_invocation_enabled)}
                    ${fieldItem('destination write', status.destination_write_enabled === false ? 'blocked' : status.destination_write_enabled)}
                    ${fieldItem('connector run created', status.connector_run_created === false ? 'blocked' : status.connector_run_created)}
                    ${fieldItem('network write', status.network_write_enabled === false ? 'blocked' : status.network_write_enabled)}
                    ${fieldItem('real destination integration', status.real_destination_integration_enabled === false ? 'blocked' : status.real_destination_integration_enabled)}
                    ${fieldItem('provider public URL', status.provider_public_url_enabled === false ? 'blocked' : status.provider_public_url_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function serverOwnedLocalOutboxTargetStatusState() {
    return State.sessionSummary?.server_owned_local_outbox_target || null;
}

function serverOwnedLocalOutboxTargetStateName(status = serverOwnedLocalOutboxTargetStatusState()) {
    return status?.server_owned_local_outbox_target_state || status?.next_state || status?.state || null;
}

function serverOwnedLocalOutboxTargetPanelState() {
    const status = serverOwnedLocalOutboxTargetStatusState() || {};
    const stateName = serverOwnedLocalOutboxTargetStateName(status);
    if (stateName === 'server_owned_local_outbox_fake_target_recorded') {
        return {
            label: 'server_owned_local_outbox_fake_target_recorded',
            pill: 'ok',
            message: 'The server has recorded a fake-target receipt for the named local outbox target.',
        };
    }
    if (status.available === true && stateName === 'server_owned_local_outbox_fake_target_ready') {
        return {
            label: 'server_owned_local_outbox_fake_target_ready',
            pill: 'ok',
            message: 'Connector-local receipt authority can support the named fake target.',
        };
    }
    return {
        label: status.blocked_reason || 'server_owned_local_outbox_target_not_ready',
        pill: 'blocked',
        message: 'The read-only status surface is waiting on server-owned connector-local receipt authority.',
    };
}

function serverOwnedLocalOutboxTargetLifecycle(status) {
    return status?.lifecycle_status_surface || {};
}

function serverOwnedLocalOutboxTargetHistoryRows(status) {
    const lifecycle = serverOwnedLocalOutboxTargetLifecycle(status);
    if (Array.isArray(lifecycle.target_receipt_history)) return lifecycle.target_receipt_history;
    if (Array.isArray(status?.target_receipt_history)) return status.target_receipt_history;
    return [];
}

function serverOwnedLocalOutboxTargetFailureRows(status) {
    const lifecycle = serverOwnedLocalOutboxTargetLifecycle(status);
    if (Array.isArray(lifecycle.failure_state_projection)) return lifecycle.failure_state_projection;
    if (Array.isArray(status?.failure_state_projection)) return status.failure_state_projection;
    return [];
}

function renderServerOwnedLocalOutboxTargetHistory(status) {
    const history = serverOwnedLocalOutboxTargetHistoryRows(status);
    if (!history.length) {
        return '<li>history: none</li>';
    }
    return history.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.server_owned_local_outbox_target_receipt_id || 'pending')}</code>: ${escapeHtml(row.server_owned_local_outbox_target_state || 'unknown')} / <code>${escapeHtml(row.authority_basis_hash || 'no-authority-hash')}</code></li>`
    )).join('');
}

function renderServerOwnedLocalOutboxTargetFailureProjection(status) {
    const rows = serverOwnedLocalOutboxTargetFailureRows(status);
    if (!rows.length) {
        return '<li>guardrails: unavailable</li>';
    }
    return rows.slice(0, 8).map((row) => (
        `<li>${escapeHtml(row.case)}: ${escapeHtml(row.projected_error_code || row.operator_status || 'status-only')}</li>`
    )).join('');
}

function renderServerOwnedLocalOutboxTargetStatusPanel() {
    const status = serverOwnedLocalOutboxTargetStatusState() || {};
    const panelState = serverOwnedLocalOutboxTargetPanelState();
    const lifecycle = serverOwnedLocalOutboxTargetLifecycle(status);
    const idempotency = status.idempotency_policy || lifecycle.idempotency_policy || {};
    const retry = status.retry_policy || lifecycle.retry_policy || {};
    const downstream = status.downstream_unavailable || [
        'real_connector_invocation',
        'production_destination_write',
        'connector_run_creation',
        'credentials',
        'provider_public_delivery_use',
        'package_mutation_reconstruction',
        'source_expansion',
        'rag_vector',
        'auth_security_implementation',
        'full_mockup_activation',
        'frontend_durable_authority',
        'generic_downstream_dispatch',
    ];
    elements.serverOwnedLocalOutboxTargetPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Local Outbox Target</strong>
                <ul>
                    ${fieldItem('rendered mode', SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_SURFACE_MODE)}
                    ${fieldItem('use case', SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_USE_CASE)}
                    ${fieldItem('response authority', SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('state', serverOwnedLocalOutboxTargetStateName(status))}
                    ${fieldItem('available', status.available)}
                    ${fieldItem('blocked reason', status.blocked_reason)}
                    ${fieldItem('history count', status.target_receipt_history_count ?? lifecycle.history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Chain</strong>
                <ul>
                    ${fieldItem('session', status.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('pass run', status.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('reconciliation', status.reconciliation_record_id, { code: true })}
                    ${fieldItem('connector record', status.connector_dispatch_record_ref, { code: true })}
                    ${fieldItem('local receipt', status.connector_local_destination_receipt_id, { code: true })}
                    ${fieldItem('external readiness', status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('authority hash', status.authority_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Fake Target Contract</strong>
                <ul>
                    ${fieldItem('receipt id', status.server_owned_local_outbox_target_receipt_id, { code: true })}
                    ${fieldItem('target', status.target_identity || 'server_owned_local_delivery_outbox_destination')}
                    ${fieldItem('mode', status.dispatch_mode || 'single_named_destination_dispatch_fake_target_first')}
                    ${fieldItem('decision', status.operator_decision || 'record_server_owned_local_outbox_fake_target')}
                    ${fieldItem('redacted artifact', status.accepted_artifact_ref, { code: true })}
                    ${fieldItem('artifact hash', status.accepted_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', status.accepted_artifact_size_bytes)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Lifecycle Policy</strong>
                <ul>
                    ${fieldItem('history authority', lifecycle.history_listing_authority)}
                    ${fieldItem('audit authority', lifecycle.audit_trail_authority)}
                    ${fieldItem('same key replay', idempotency.same_key_same_payload_replay)}
                    ${fieldItem('same key conflict', idempotency.same_key_different_payload_conflict)}
                    ${fieldItem('same basis conflict', idempotency.same_basis_different_client_request_id)}
                    ${fieldItem('retry fields', retry.retry_fields_admitted === false ? 'blocked' : retry.retry_fields_admitted)}
                    ${fieldItem('replay semantics', retry.replay_semantics)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Target History</strong>
                <ul>
                    ${renderServerOwnedLocalOutboxTargetHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Guardrail Projection</strong>
                <ul>
                    ${renderServerOwnedLocalOutboxTargetFailureProjection(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <ul>
                    ${fieldItem('real connector invocation', status.real_connector_invocation_enabled === false ? 'blocked' : status.real_connector_invocation_enabled)}
                    ${fieldItem('destination write', status.destination_write_enabled === false ? 'blocked' : status.destination_write_enabled)}
                    ${fieldItem('connector run created', status.connector_run_created === false ? 'blocked' : status.connector_run_created)}
                    ${fieldItem('connector target created', status.connector_run_target_created === false ? 'blocked' : status.connector_run_target_created)}
                    ${fieldItem('credentials', status.credentials_enabled === false ? 'blocked' : status.credentials_enabled)}
                    ${fieldItem('provider public delivery', status.provider_public_delivery_enabled === false ? 'blocked' : status.provider_public_delivery_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function serverOwnedLocalOutboxWriteStatusState() {
    return State.sessionSummary?.server_owned_local_outbox_write || null;
}

function serverOwnedLocalOutboxWriteStateName(status = serverOwnedLocalOutboxWriteStatusState()) {
    return status?.server_owned_local_outbox_write_state || status?.next_state || status?.state || null;
}

function serverOwnedLocalOutboxWritePanelState() {
    const status = serverOwnedLocalOutboxWriteStatusState() || {};
    const stateName = serverOwnedLocalOutboxWriteStateName(status);
    if (stateName === 'server_owned_local_outbox_write_recorded') {
        return {
            label: 'server_owned_local_outbox_write_recorded',
            pill: 'ok',
            message: 'The server has written the validated artifact into the derived local outbox root.',
        };
    }
    if (status.available === true && stateName === 'server_owned_local_outbox_write_ready') {
        return {
            label: 'server_owned_local_outbox_write_ready',
            pill: 'ok',
            message: 'Fake-target authority can support the first server-owned local outbox write.',
        };
    }
    return {
        label: status.blocked_reason || 'server_owned_local_outbox_write_not_ready',
        pill: 'blocked',
        message: 'The read-only status surface is waiting on server-owned fake-target authority.',
    };
}

function serverOwnedLocalOutboxWriteLifecycle(status) {
    return status?.lifecycle_status_surface || {};
}

function serverOwnedLocalOutboxWriteHistoryRows(status) {
    const lifecycle = serverOwnedLocalOutboxWriteLifecycle(status);
    if (Array.isArray(lifecycle.write_receipt_history)) return lifecycle.write_receipt_history;
    if (Array.isArray(status?.write_receipt_history)) return status.write_receipt_history;
    return [];
}

function serverOwnedLocalOutboxWriteFailureRows(status) {
    const lifecycle = serverOwnedLocalOutboxWriteLifecycle(status);
    if (Array.isArray(lifecycle.failure_state_projection)) return lifecycle.failure_state_projection;
    if (Array.isArray(status?.failure_state_projection)) return status.failure_state_projection;
    return [];
}

function renderServerOwnedLocalOutboxWriteHistory(status) {
    const history = serverOwnedLocalOutboxWriteHistoryRows(status);
    if (!history.length) {
        return '<li>history: none</li>';
    }
    return history.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.server_owned_local_outbox_write_receipt_id || 'pending')}</code>: ${escapeHtml(row.server_owned_local_outbox_write_state || 'unknown')} / <code>${escapeHtml(row.authority_basis_hash || 'no-authority-hash')}</code></li>`
    )).join('');
}

function renderServerOwnedLocalOutboxWriteFailureProjection(status) {
    const rows = serverOwnedLocalOutboxWriteFailureRows(status);
    if (!rows.length) {
        return '<li>guardrails: unavailable</li>';
    }
    return rows.slice(0, 8).map((row) => (
        `<li>${escapeHtml(row.case)}: ${escapeHtml(row.projected_error_code || row.operator_status || 'status-only')}</li>`
    )).join('');
}

function renderServerOwnedLocalOutboxWriteStatusPanel() {
    const status = serverOwnedLocalOutboxWriteStatusState() || {};
    const panelState = serverOwnedLocalOutboxWritePanelState();
    const lifecycle = serverOwnedLocalOutboxWriteLifecycle(status);
    const idempotency = status.idempotency_policy || lifecycle.idempotency_policy || {};
    const retry = status.retry_policy || lifecycle.retry_policy || {};
    const downstream = status.downstream_unavailable || [
        'real_connector_invocation',
        'external_destination_write',
        'connector_run_creation',
        'credentials',
        'provider_public_delivery_use',
        'package_mutation_reconstruction',
        'source_expansion',
        'rag_vector',
        'auth_security_implementation',
        'full_mockup_activation',
        'frontend_durable_authority',
        'generic_downstream_dispatch',
    ];
    elements.serverOwnedLocalOutboxWritePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Local Outbox Write</strong>
                <ul>
                    ${fieldItem('rendered mode', SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_SURFACE_MODE)}
                    ${fieldItem('use case', SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_USE_CASE)}
                    ${fieldItem('response authority', SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('state', serverOwnedLocalOutboxWriteStateName(status))}
                    ${fieldItem('available', status.available)}
                    ${fieldItem('blocked reason', status.blocked_reason)}
                    ${fieldItem('history count', status.write_receipt_history_count ?? lifecycle.history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Chain</strong>
                <ul>
                    ${fieldItem('session', status.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('pass run', status.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('reconciliation', status.reconciliation_record_id, { code: true })}
                    ${fieldItem('connector record', status.connector_dispatch_record_ref, { code: true })}
                    ${fieldItem('local receipt', status.connector_local_destination_receipt_id, { code: true })}
                    ${fieldItem('fake target receipt', status.server_owned_local_outbox_target_receipt_id, { code: true })}
                    ${fieldItem('external readiness', status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('authority hash', status.authority_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Outbox Receipt</strong>
                <ul>
                    ${fieldItem('write receipt id', status.server_owned_local_outbox_write_receipt_id, { code: true })}
                    ${fieldItem('target', status.target_identity || 'server_owned_local_delivery_outbox_destination')}
                    ${fieldItem('mode', status.dispatch_mode || 'server_owned_local_outbox_write_via_storage_dir')}
                    ${fieldItem('decision', status.operator_decision || 'write_server_owned_local_outbox')}
                    ${fieldItem('outbox artifact', status.outbox_artifact_ref, { code: true })}
                    ${fieldItem('outbox manifest', status.outbox_manifest_ref, { code: true })}
                    ${fieldItem('artifact hash', status.outbox_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', status.outbox_artifact_size_bytes)}
                    ${fieldItem('redacted source', status.accepted_artifact_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Lifecycle Policy</strong>
                <ul>
                    ${fieldItem('history authority', lifecycle.history_listing_authority)}
                    ${fieldItem('audit authority', lifecycle.audit_trail_authority)}
                    ${fieldItem('same key replay', idempotency.same_key_same_payload_replay)}
                    ${fieldItem('same key conflict', idempotency.same_key_different_payload_conflict)}
                    ${fieldItem('same basis conflict', idempotency.same_basis_different_client_request_id)}
                    ${fieldItem('retry fields', retry.retry_fields_admitted === false ? 'blocked' : retry.retry_fields_admitted)}
                    ${fieldItem('replay semantics', retry.replay_semantics)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Write History</strong>
                <ul>
                    ${renderServerOwnedLocalOutboxWriteHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Guardrail Projection</strong>
                <ul>
                    ${renderServerOwnedLocalOutboxWriteFailureProjection(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <ul>
                    ${fieldItem('real connector invocation', status.real_connector_invocation_enabled === false ? 'blocked' : status.real_connector_invocation_enabled)}
                    ${fieldItem('external destination write', status.external_destination_write_enabled === false ? 'blocked' : status.external_destination_write_enabled)}
                    ${fieldItem('operator path authority', status.operator_destination_path_enabled === false ? 'blocked' : status.operator_destination_path_enabled)}
                    ${fieldItem('connector run created', status.connector_run_created === false ? 'blocked' : status.connector_run_created)}
                    ${fieldItem('connector target created', status.connector_run_target_created === false ? 'blocked' : status.connector_run_target_created)}
                    ${fieldItem('credentials', status.credentials_enabled === false ? 'blocked' : status.credentials_enabled)}
                    ${fieldItem('network write', status.network_write_enabled === false ? 'blocked' : status.network_write_enabled)}
                    ${fieldItem('provider public URL', status.provider_public_url_enabled === false ? 'blocked' : status.provider_public_url_enabled)}
                    ${fieldItem('package mutation', status.package_mutation_enabled === false ? 'blocked' : status.package_mutation_enabled)}
                    ${fieldItem('source expansion', status.source_expansion_enabled === false ? 'blocked' : status.source_expansion_enabled)}
                    ${fieldItem('RAG/vector', status.rag_vector_enabled === false ? 'blocked' : status.rag_vector_enabled)}
                    ${fieldItem('frontend durable authority', status.frontend_durable_authority_enabled === false ? 'blocked' : status.frontend_durable_authority_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function localOutboxProviderPrivateHandoffStatusState() {
    return State.sessionSummary?.local_outbox_provider_private_handoff || null;
}

function localOutboxProviderPrivateHandoffStateName(status = localOutboxProviderPrivateHandoffStatusState()) {
    return status?.provider_private_handoff_state || status?.next_state || status?.state || null;
}

function localOutboxProviderPrivateHandoffPanelState() {
    const status = localOutboxProviderPrivateHandoffStatusState() || {};
    const stateName = localOutboxProviderPrivateHandoffStateName(status);
    if (stateName === 'local_outbox_provider_private_handoff_prepared') {
        return {
            label: 'local_outbox_provider_private_handoff_prepared',
            pill: 'ok',
            message: 'The server has prepared a redacted provider-private handoff receipt from local outbox authority.',
        };
    }
    if (stateName === 'local_outbox_provider_private_handoff_expired') {
        return {
            label: 'local_outbox_provider_private_handoff_expired',
            pill: 'ready',
            message: 'The provider-private handoff receipt is expired; status remains read-only.',
        };
    }
    if (status.available === true && stateName === 'local_outbox_provider_private_handoff_ready') {
        return {
            label: 'local_outbox_provider_private_handoff_ready',
            pill: 'ok',
            message: 'Server-owned local outbox write authority can support provider-private handoff prepare.',
        };
    }
    return {
        label: status.blocked_reason || 'local_outbox_provider_private_handoff_not_ready',
        pill: 'blocked',
        message: 'The read-only status surface is waiting on server-owned local outbox write authority.',
    };
}

function localOutboxProviderPrivateHandoffLifecycle(status) {
    return status?.lifecycle_status_surface || {};
}

function localOutboxProviderPrivateHandoffHistoryRows(status) {
    const lifecycle = localOutboxProviderPrivateHandoffLifecycle(status);
    if (Array.isArray(lifecycle.provider_private_handoff_history)) return lifecycle.provider_private_handoff_history;
    if (Array.isArray(status?.provider_private_handoff_history)) return status.provider_private_handoff_history;
    return [];
}

function localOutboxProviderPrivateHandoffAuditRows(status) {
    const lifecycle = localOutboxProviderPrivateHandoffLifecycle(status);
    if (Array.isArray(lifecycle.audit_event_history)) return lifecycle.audit_event_history;
    if (Array.isArray(status?.audit_event_history)) return status.audit_event_history;
    return [];
}

function localOutboxProviderPrivateHandoffFailureRows(status) {
    const lifecycle = localOutboxProviderPrivateHandoffLifecycle(status);
    if (Array.isArray(lifecycle.failure_state_projection)) return lifecycle.failure_state_projection;
    if (Array.isArray(status?.failure_state_projection)) return status.failure_state_projection;
    return [];
}

function renderLocalOutboxProviderPrivateHandoffHistory(status) {
    const history = localOutboxProviderPrivateHandoffHistoryRows(status);
    if (!history.length) {
        return '<li>history: none</li>';
    }
    return history.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.provider_private_handoff_receipt_id || 'pending')}</code>: ${escapeHtml(row.provider_private_handoff_state || 'unknown')} / <code>${escapeHtml(row.authority_basis_hash || 'no-authority-hash')}</code></li>`
    )).join('');
}

function renderLocalOutboxProviderPrivateHandoffAuditHistory(status) {
    const audit = localOutboxProviderPrivateHandoffAuditRows(status);
    if (!audit.length) {
        return '<li>audit: none</li>';
    }
    return audit.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.provider_private_handoff_audit_event_id || 'pending')}</code>: ${escapeHtml(row.event_type || 'event')} / ${escapeHtml(row.reason_code || row.event_status || 'status-only')}</li>`
    )).join('');
}

function renderLocalOutboxProviderPrivateHandoffFailureProjection(status) {
    const rows = localOutboxProviderPrivateHandoffFailureRows(status);
    if (!rows.length) {
        return '<li>guardrails: unavailable</li>';
    }
    return rows.slice(0, 10).map((row) => (
        `<li>${escapeHtml(row.case)}: ${escapeHtml(row.projected_error_code || row.operator_status || 'status-only')}</li>`
    )).join('');
}

function renderLocalOutboxProviderPrivateHandoffStatusPanel() {
    const status = localOutboxProviderPrivateHandoffStatusState() || {};
    const panelState = localOutboxProviderPrivateHandoffPanelState();
    const lifecycle = localOutboxProviderPrivateHandoffLifecycle(status);
    const idempotency = status.idempotency_policy || lifecycle.idempotency_policy || {};
    const retry = status.retry_policy || lifecycle.retry_policy || {};
    const downstream = status.downstream_unavailable || [
        'real_connector_invocation',
        'external_destination_write',
        'connector_run_creation',
        'connector_run_target_creation',
        'credentials',
        'provider_public_delivery_use',
        'raw_token_use',
        'package_mutation_reconstruction',
        'source_expansion',
        'rag_vector',
        'auth_security_implementation',
        'full_mockup_activation',
        'frontend_durable_authority',
        'generic_downstream_dispatch',
    ];
    elements.localOutboxProviderPrivateHandoffPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Provider-Private Handoff</strong>
                <ul>
                    ${fieldItem('rendered mode', LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_SURFACE_MODE)}
                    ${fieldItem('use case', LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_USE_CASE)}
                    ${fieldItem('response authority', LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('state', localOutboxProviderPrivateHandoffStateName(status))}
                    ${fieldItem('available', status.available)}
                    ${fieldItem('blocked reason', status.blocked_reason)}
                    ${fieldItem('lifecycle surface', lifecycle.surface_mode)}
                    ${fieldItem('history count', status.provider_private_handoff_history_count ?? lifecycle.history_count)}
                    ${fieldItem('audit event count', status.audit_event_history_count ?? lifecycle.audit_event_history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Chain</strong>
                <ul>
                    ${fieldItem('session', status.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('pass run', status.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('reconciliation', status.reconciliation_record_id, { code: true })}
                    ${fieldItem('connector record', status.connector_dispatch_record_ref, { code: true })}
                    ${fieldItem('local receipt', status.connector_local_destination_receipt_id, { code: true })}
                    ${fieldItem('fake target receipt', status.server_owned_local_outbox_target_receipt_id, { code: true })}
                    ${fieldItem('outbox write receipt', status.server_owned_local_outbox_write_receipt_id, { code: true })}
                    ${fieldItem('external readiness', status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('authority hash', status.authority_basis_hash, { code: true })}
                    ${fieldItem('request hash', status.request_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Redacted Receipt</strong>
                <ul>
                    ${fieldItem('handoff receipt id', status.provider_private_handoff_receipt_id, { code: true })}
                    ${fieldItem('target', status.target_identity || 'server_owned_local_outbox_provider_private_handoff_destination')}
                    ${fieldItem('mode', status.dispatch_mode || 'provider_private_fake_provider_prepare_status_from_local_outbox_receipt')}
                    ${fieldItem('decision', status.operator_decision || 'prepare_provider_private_handoff_from_local_outbox')}
                    ${fieldItem('recipient scope', status.recipient_scope)}
                    ${fieldItem('marker', status.provider_private_marker)}
                    ${fieldItem('expires at', status.provider_private_expires_at)}
                    ${fieldItem('requested ttl seconds', status.requested_ttl_seconds)}
                    ${fieldItem('replay policy', status.provider_private_replay_policy)}
                    ${fieldItem('outbox artifact', status.outbox_artifact_ref, { code: true })}
                    ${fieldItem('outbox manifest', status.outbox_manifest_ref, { code: true })}
                    ${fieldItem('outbox artifact hash', status.outbox_artifact_hash, { code: true })}
                    ${fieldItem('outbox size bytes', status.outbox_artifact_size_bytes)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Lifecycle Policy</strong>
                <ul>
                    ${fieldItem('history authority', lifecycle.history_listing_authority)}
                    ${fieldItem('audit authority', lifecycle.audit_trail_authority)}
                    ${fieldItem('same key replay', idempotency.same_key_same_payload_replay)}
                    ${fieldItem('same key conflict', idempotency.same_key_different_payload_conflict)}
                    ${fieldItem('same basis conflict', idempotency.same_basis_different_client_request_id)}
                    ${fieldItem('request basis unique', idempotency.request_basis_hash_unique)}
                    ${fieldItem('retry fields', retry.retry_fields_admitted === false ? 'blocked' : retry.retry_fields_admitted)}
                    ${fieldItem('raw token replay', retry.raw_token_replay_admitted === false ? 'blocked' : retry.raw_token_replay_admitted)}
                    ${fieldItem('replay semantics', retry.replay_semantics)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Handoff History</strong>
                <ul>
                    ${renderLocalOutboxProviderPrivateHandoffHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Audit History</strong>
                <ul>
                    ${renderLocalOutboxProviderPrivateHandoffAuditHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Guardrail Projection</strong>
                <ul>
                    ${renderLocalOutboxProviderPrivateHandoffFailureProjection(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <ul>
                    ${fieldItem('real connector invocation', status.real_connector_invocation_enabled === false ? 'blocked' : status.real_connector_invocation_enabled)}
                    ${fieldItem('external provider network write', status.external_provider_network_write_enabled === false ? 'blocked' : status.external_provider_network_write_enabled)}
                    ${fieldItem('external object store write', status.external_object_store_write_enabled === false ? 'blocked' : status.external_object_store_write_enabled)}
                    ${fieldItem('external destination write', status.external_destination_write_enabled === false ? 'blocked' : status.external_destination_write_enabled)}
                    ${fieldItem('operator path authority', status.operator_destination_path_enabled === false ? 'blocked' : status.operator_destination_path_enabled)}
                    ${fieldItem('connector run created', status.connector_run_created === false ? 'blocked' : status.connector_run_created)}
                    ${fieldItem('connector target created', status.connector_run_target_created === false ? 'blocked' : status.connector_run_target_created)}
                    ${fieldItem('credentials', status.credentials_enabled === false ? 'blocked' : status.credentials_enabled)}
                    ${fieldItem('provider public delivery', status.provider_public_delivery_enabled === false ? 'blocked' : status.provider_public_delivery_enabled)}
                    ${fieldItem('provider private use route', status.provider_private_use_route_enabled === false ? 'blocked' : status.provider_private_use_route_enabled)}
                    ${fieldItem('provider private revocation', status.provider_private_revocation_supported === false ? 'blocked' : status.provider_private_revocation_supported)}
                    ${fieldItem('raw token exposed', status.raw_token_exposed === false ? 'blocked' : status.raw_token_exposed)}
                    ${fieldItem('package mutation', status.package_mutation_enabled === false ? 'blocked' : status.package_mutation_enabled)}
                    ${fieldItem('source expansion', status.source_expansion_enabled === false ? 'blocked' : status.source_expansion_enabled)}
                    ${fieldItem('RAG/vector', status.rag_vector_enabled === false ? 'blocked' : status.rag_vector_enabled)}
                    ${fieldItem('auth/security implementation', status.auth_security_implementation_enabled === false ? 'blocked' : status.auth_security_implementation_enabled)}
                    ${fieldItem('frontend durable authority', status.frontend_durable_authority_enabled === false ? 'blocked' : status.frontend_durable_authority_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function externalLocalExportStatusState() {
    return State.sessionSummary?.external_local_export || null;
}

function externalLocalExportStateName(status = externalLocalExportStatusState()) {
    return status?.external_local_export_state || status?.next_state || status?.state || null;
}

function externalLocalExportPanelState() {
    const status = externalLocalExportStatusState() || {};
    const stateName = externalLocalExportStateName(status);
    if (stateName === 'external_local_export_written') {
        return {
            label: 'external_local_export_written',
            pill: 'ok',
            message: 'The server has written the approved outbox artifact and manifest to the configured local export directory.',
        };
    }
    if (status.available === true && stateName === 'external_local_export_ready') {
        return {
            label: 'external_local_export_ready',
            pill: 'ok',
            message: 'Server-owned local outbox authority can support the configured external local export write.',
        };
    }
    return {
        label: status.blocked_reason || 'external_local_export_not_ready',
        pill: 'blocked',
        message: 'The read-only status surface is waiting on server-owned local outbox authority.',
    };
}

function externalLocalExportLifecycle(status) {
    return status?.lifecycle_status_surface || {};
}

function externalLocalExportHistoryRows(status) {
    const lifecycle = externalLocalExportLifecycle(status);
    if (Array.isArray(lifecycle.external_local_export_history)) return lifecycle.external_local_export_history;
    if (Array.isArray(status?.external_local_export_history)) return status.external_local_export_history;
    return [];
}

function externalLocalExportAuditRows(status) {
    const lifecycle = externalLocalExportLifecycle(status);
    if (Array.isArray(lifecycle.audit_event_history)) return lifecycle.audit_event_history;
    if (Array.isArray(status?.audit_event_history)) return status.audit_event_history;
    return [];
}

function externalLocalExportFailureRows(status) {
    const lifecycle = externalLocalExportLifecycle(status);
    if (Array.isArray(lifecycle.failure_state_projection)) return lifecycle.failure_state_projection;
    if (Array.isArray(status?.failure_state_projection)) return status.failure_state_projection;
    return [];
}

function renderExternalLocalExportHistory(status) {
    const history = externalLocalExportHistoryRows(status);
    if (!history.length) {
        return '<li>history: none</li>';
    }
    return history.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.external_local_export_receipt_id || 'pending')}</code>: ${escapeHtml(row.external_local_export_state || 'unknown')} / <code>${escapeHtml(row.authority_basis_hash || 'no-authority-hash')}</code></li>`
    )).join('');
}

function renderExternalLocalExportAuditHistory(status) {
    const audit = externalLocalExportAuditRows(status);
    if (!audit.length) {
        return '<li>audit: none</li>';
    }
    return audit.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.external_local_export_audit_event_id || 'pending')}</code>: ${escapeHtml(row.event_type || 'event')} / ${escapeHtml(row.reason_code || row.event_status || 'status-only')}</li>`
    )).join('');
}

function renderExternalLocalExportFailureProjection(status) {
    const rows = externalLocalExportFailureRows(status);
    if (!rows.length) {
        return '<li>guardrails: unavailable</li>';
    }
    return rows.slice(0, 10).map((row) => (
        `<li>${escapeHtml(row.case)}: ${escapeHtml(row.projected_error_code || row.operator_status || 'status-only')}</li>`
    )).join('');
}

function renderExternalLocalExportStatusPanel() {
    const status = externalLocalExportStatusState() || {};
    const panelState = externalLocalExportPanelState();
    const lifecycle = externalLocalExportLifecycle(status);
    const idempotency = status.idempotency_policy || lifecycle.idempotency_policy || {};
    const retry = status.retry_policy || lifecycle.retry_policy || {};
    const downstream = status.downstream_unavailable || [
        'real_connector_invocation',
        'connector_run_creation',
        'connector_run_target_creation',
        'credentials',
        'network_egress',
        'provider_public_delivery_use',
        'raw_public_url_exposure',
        'raw_token_exposure',
        'caller_supplied_destination_path_or_url',
        'package_mutation_reconstruction',
        'source_expansion_ingestion',
        'rag_vector_behavior',
        'qualitative_hybrid_analysis_runtime',
        'auth_security_broadening',
        'full_mockup_activation',
        'frontend_durable_authority',
        'generic_downstream_dispatch',
    ];
    elements.externalLocalExportPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>External Local Export</strong>
                <ul>
                    ${fieldItem('rendered mode', EXTERNAL_LOCAL_EXPORT_STATUS_SURFACE_MODE)}
                    ${fieldItem('use case', EXTERNAL_LOCAL_EXPORT_STATUS_USE_CASE)}
                    ${fieldItem('response authority', EXTERNAL_LOCAL_EXPORT_STATUS_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('state', externalLocalExportStateName(status))}
                    ${fieldItem('available', status.available)}
                    ${fieldItem('blocked reason', status.blocked_reason)}
                    ${fieldItem('history count', status.external_local_export_history_count ?? lifecycle.history_count)}
                    ${fieldItem('audit count', status.audit_event_history_count ?? lifecycle.audit_event_history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Chain</strong>
                <ul>
                    ${fieldItem('session', status.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('pass run', status.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('reconciliation', status.reconciliation_record_id, { code: true })}
                    ${fieldItem('connector record', status.connector_dispatch_record_ref, { code: true })}
                    ${fieldItem('local receipt', status.connector_local_destination_receipt_id, { code: true })}
                    ${fieldItem('outbox target receipt', status.server_owned_local_outbox_target_receipt_id, { code: true })}
                    ${fieldItem('outbox write receipt', status.server_owned_local_outbox_write_receipt_id, { code: true })}
                    ${fieldItem('provider-private receipt', status.provider_private_handoff_receipt_id, { code: true })}
                    ${fieldItem('external readiness', status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('authority hash', status.authority_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Export Receipt</strong>
                <ul>
                    ${fieldItem('receipt id', status.external_local_export_receipt_id, { code: true })}
                    ${fieldItem('target', status.target_identity || 'server_configured_external_local_export_directory')}
                    ${fieldItem('target class', status.target_class || 'server_configured_external_destination_write')}
                    ${fieldItem('mode', status.dispatch_mode || 'server_configured_external_local_export_directory_write')}
                    ${fieldItem('decision', status.operator_decision || 'write_server_configured_external_local_export_directory')}
                    ${fieldItem('destination label', status.redacted_destination_label)}
                    ${fieldItem('artifact ref', status.external_artifact_ref, { code: true })}
                    ${fieldItem('manifest ref', status.external_manifest_ref, { code: true })}
                    ${fieldItem('artifact hash', status.external_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', status.external_artifact_size_bytes)}
                    ${fieldItem('redacted source', status.source_outbox_artifact_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Lifecycle Policy</strong>
                <ul>
                    ${fieldItem('history authority', lifecycle.history_listing_authority)}
                    ${fieldItem('audit authority', lifecycle.audit_trail_authority)}
                    ${fieldItem('same key replay', idempotency.same_key_same_payload_replay)}
                    ${fieldItem('same key conflict', idempotency.same_key_different_payload_conflict)}
                    ${fieldItem('same basis new key', idempotency.same_basis_different_client_request_id)}
                    ${fieldItem('duplicate target conflict', idempotency.duplicate_target_conflicting_output)}
                    ${fieldItem('retry fields', retry.retry_fields_admitted === false ? 'blocked' : retry.retry_fields_admitted)}
                    ${fieldItem('replay semantics', retry.replay_semantics)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Export History</strong>
                <ul>
                    ${renderExternalLocalExportHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Audit History</strong>
                <ul>
                    ${renderExternalLocalExportAuditHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Guardrail Projection</strong>
                <ul>
                    ${renderExternalLocalExportFailureProjection(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Boundary Status</strong>
                <ul>
                    ${fieldItem('selected external local export write', status.server_configured_external_local_export_write_performed === true ? 'performed' : status.server_configured_external_local_export_write_enabled === true ? 'ready' : 'blocked')}
                    ${fieldItem('operator path authority', status.operator_destination_path_enabled === false ? 'blocked' : status.operator_destination_path_enabled)}
                    ${fieldItem('real connector invocation', status.real_connector_invocation_enabled === false ? 'blocked' : status.real_connector_invocation_enabled)}
                    ${fieldItem('connector run created', status.connector_run_created === false ? 'blocked' : status.connector_run_created)}
                    ${fieldItem('connector target created', status.connector_run_target_created === false ? 'blocked' : status.connector_run_target_created)}
                    ${fieldItem('credentials', status.credentials_enabled === false ? 'blocked' : status.credentials_enabled)}
                    ${fieldItem('network egress', status.network_egress_enabled === false ? 'blocked' : status.network_egress_enabled)}
                    ${fieldItem('provider public delivery/use', status.provider_public_delivery_enabled === false ? 'blocked' : status.provider_public_delivery_enabled)}
                    ${fieldItem('raw public URL', status.raw_public_url_exposed === false ? 'blocked' : status.raw_public_url_exposed)}
                    ${fieldItem('raw token', status.raw_token_exposed === false ? 'blocked' : status.raw_token_exposed)}
                    ${fieldItem('package mutation', status.package_mutation_enabled === false ? 'blocked' : status.package_mutation_enabled)}
                    ${fieldItem('source expansion', status.source_expansion_enabled === false ? 'blocked' : status.source_expansion_enabled)}
                    ${fieldItem('RAG/vector', status.rag_vector_enabled === false ? 'blocked' : status.rag_vector_enabled)}
                    ${fieldItem('frontend durable authority', status.frontend_durable_authority_enabled === false ? 'blocked' : status.frontend_durable_authority_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function internalWebhookDispatchStatusState() {
    return State.sessionSummary?.internal_webhook_dispatch || null;
}

function internalWebhookDispatchStateName(status = internalWebhookDispatchStatusState()) {
    return status?.internal_webhook_dispatch_state || status?.next_state || status?.state || null;
}

function internalWebhookDispatchPanelState() {
    const status = internalWebhookDispatchStatusState() || {};
    const stateName = internalWebhookDispatchStateName(status);
    if (stateName === 'internal_webhook_dispatched' || stateName === 'source_directory_internal_webhook_dispatched') {
        return {
            label: stateName,
            pill: 'ok',
            message: stateName === 'source_directory_internal_webhook_dispatched'
                ? 'The server recorded a source-directory configured internal webhook dispatch receipt.'
                : 'The server recorded a configured internal webhook dispatch receipt.',
        };
    }
    if (status.available === true && stateName === 'internal_webhook_dispatch_ready') {
        return {
            label: 'internal_webhook_dispatch_ready',
            pill: 'ok',
            message: 'Server-owned local outbox authority can support configured internal webhook dispatch.',
        };
    }
    if (stateName === 'internal_webhook_failed' || stateName === 'source_directory_internal_webhook_failed') {
        return {
            label: stateName,
            pill: 'warn',
            message: 'The read-only status surface is showing a recorded internal webhook failure.',
        };
    }
    return {
        label: status.blocked_reason || 'internal_webhook_dispatch_not_ready',
        pill: 'blocked',
        message: 'The read-only status surface is waiting on server-owned local outbox authority.',
    };
}

function internalWebhookDispatchLifecycle(status) {
    return status?.lifecycle_status_surface || {};
}

function internalWebhookDispatchHistoryRows(status) {
    const lifecycle = internalWebhookDispatchLifecycle(status);
    if (Array.isArray(lifecycle.source_directory_internal_webhook_dispatch_history)) return lifecycle.source_directory_internal_webhook_dispatch_history;
    if (Array.isArray(status?.source_directory_internal_webhook_dispatch_history)) return status.source_directory_internal_webhook_dispatch_history;
    if (Array.isArray(lifecycle.internal_webhook_dispatch_history)) return lifecycle.internal_webhook_dispatch_history;
    if (Array.isArray(status?.internal_webhook_dispatch_history)) return status.internal_webhook_dispatch_history;
    return [];
}

function internalWebhookDispatchAuditRows(status) {
    const lifecycle = internalWebhookDispatchLifecycle(status);
    if (Array.isArray(lifecycle.audit_event_history)) return lifecycle.audit_event_history;
    if (Array.isArray(status?.audit_event_history)) return status.audit_event_history;
    return [];
}

function internalWebhookDispatchFailureRows(status) {
    const lifecycle = internalWebhookDispatchLifecycle(status);
    if (Array.isArray(lifecycle.failure_state_projection)) return lifecycle.failure_state_projection;
    if (Array.isArray(status?.failure_state_projection)) return status.failure_state_projection;
    return [];
}

function renderInternalWebhookDispatchHistory(status) {
    const history = internalWebhookDispatchHistoryRows(status);
    if (!history.length) {
        return '<li>history: none</li>';
    }
    return history.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.internal_webhook_dispatch_receipt_id || row.source_directory_internal_webhook_dispatch_receipt_id || 'pending')}</code>: ${escapeHtml(row.internal_webhook_dispatch_state || row.source_directory_internal_webhook_dispatch_state || 'unknown')} / <code>${escapeHtml(row.authority_basis_hash || 'no-authority-hash')}</code></li>`
    )).join('');
}

function renderInternalWebhookDispatchAuditHistory(status) {
    const audit = internalWebhookDispatchAuditRows(status);
    if (!audit.length) {
        return '<li>audit: none</li>';
    }
    return audit.slice(0, 4).map((row) => (
        `<li><code>${escapeHtml(row.internal_webhook_dispatch_audit_event_id || row.source_directory_internal_webhook_dispatch_audit_event_id || 'pending')}</code>: ${escapeHtml(row.event_type || 'event')} / ${escapeHtml(row.reason_code || row.event_status || 'status-only')}</li>`
    )).join('');
}

function renderInternalWebhookDispatchFailureProjection(status) {
    const rows = internalWebhookDispatchFailureRows(status);
    if (!rows.length) {
        return '<li>guardrails: unavailable</li>';
    }
    return rows.slice(0, 10).map((row) => (
        `<li>${escapeHtml(row.case)}: ${escapeHtml(row.projected_error_code || row.operator_status || 'status-only')}</li>`
    )).join('');
}

function renderInternalWebhookDispatchStatusPanel() {
    const status = internalWebhookDispatchStatusState() || {};
    const panelState = internalWebhookDispatchPanelState();
    const lifecycle = internalWebhookDispatchLifecycle(status);
    const idempotency = status.idempotency_policy || lifecycle.idempotency_policy || {};
    const retry = status.retry_policy || lifecycle.retry_policy || {};
    const downstream = status.downstream_unavailable || [
        'operator_destination_url',
        'raw_target_url_exposure',
        'raw_token_exposure',
        'raw_headers_exposure',
        'raw_local_path_exposure',
        'raw_package_payload_exposure',
        'raw_package_bytes_exposure',
        'connector_run_creation',
        'connector_run_target_creation',
        'credentials',
        'provider_public_url',
        'provider_private_signed_url',
        'cloud_object_store_write',
        'package_mutation_reconstruction',
        'source_expansion',
        'rag_vector',
        'optional_tool_runtime',
        'auth_security_implementation',
        'rendered_write_submit_control',
    ];
    elements.internalWebhookDispatchPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Internal Webhook Dispatch</strong>
                <ul>
                    ${fieldItem('rendered mode', INTERNAL_WEBHOOK_DISPATCH_STATUS_SURFACE_MODE)}
                    ${fieldItem('use case', INTERNAL_WEBHOOK_DISPATCH_STATUS_USE_CASE)}
                    ${fieldItem('response authority', INTERNAL_WEBHOOK_DISPATCH_STATUS_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('state', internalWebhookDispatchStateName(status))}
                    ${fieldItem('available', status.available)}
                    ${fieldItem('blocked reason', status.blocked_reason)}
                    ${fieldItem('history count', status.internal_webhook_dispatch_history_count ?? status.source_directory_internal_webhook_dispatch_history_count ?? lifecycle.history_count)}
                    ${fieldItem('audit count', status.audit_event_history_count ?? lifecycle.audit_event_history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Chain</strong>
                <ul>
                    ${fieldItem('session', status.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('pass run', status.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('source ingestion batch', status.source_ingestion_batch_id, { code: true })}
                    ${fieldItem('source ingestion file', status.source_ingestion_file_id, { code: true })}
                    ${fieldItem('reconciliation', status.reconciliation_record_id, { code: true })}
                    ${fieldItem('connector record', status.connector_dispatch_record_ref, { code: true })}
                    ${fieldItem('local receipt', status.connector_local_destination_receipt_id, { code: true })}
                    ${fieldItem('outbox target receipt', status.server_owned_local_outbox_target_receipt_id, { code: true })}
                    ${fieldItem('outbox write receipt', status.server_owned_local_outbox_write_receipt_id, { code: true })}
                    ${fieldItem('external readiness', status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('authority hash', status.authority_basis_hash, { code: true })}
                    ${fieldItem('request hash', status.request_basis_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Dispatch Receipt</strong>
                <ul>
                    ${fieldItem('receipt id', status.internal_webhook_dispatch_receipt_id || status.source_directory_internal_webhook_dispatch_receipt_id, { code: true })}
                    ${fieldItem('target', status.target_identity || 'server_configured_internal_webhook_destination')}
                    ${fieldItem('target class', status.target_class || 'real_connector_invocation')}
                    ${fieldItem('mode', status.dispatch_mode || 'server_configured_allowlisted_internal_webhook_post')}
                    ${fieldItem('destination', status.redacted_destination_display_name)}
                    ${fieldItem('package kind', status.package_kind)}
                    ${fieldItem('package set hash', status.package_set_hash, { code: true })}
                    ${fieldItem('package ref', status.package_artifact_ref, { code: true })}
                    ${fieldItem('package hash', status.package_artifact_hash, { code: true })}
                    ${fieldItem('package size bytes', status.package_artifact_size_bytes)}
                    ${fieldItem('response status', status.response_status_code)}
                    ${fieldItem('failure code', status.failure_code)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Lifecycle Policy</strong>
                <ul>
                    ${fieldItem('history authority', lifecycle.history_listing_authority)}
                    ${fieldItem('audit authority', lifecycle.audit_trail_authority)}
                    ${fieldItem('same key replay', idempotency.same_key_same_payload_replay)}
                    ${fieldItem('same key conflict', idempotency.same_key_different_payload_conflict)}
                    ${fieldItem('same basis new key', idempotency.same_basis_different_client_request_id)}
                    ${fieldItem('retry fields', retry.retry_fields_admitted === false ? 'blocked' : retry.retry_fields_admitted)}
                    ${fieldItem('replay semantics', retry.replay_semantics)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Dispatch History</strong>
                <ul>
                    ${renderInternalWebhookDispatchHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Audit History</strong>
                <ul>
                    ${renderInternalWebhookDispatchAuditHistory(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Guardrail Projection</strong>
                <ul>
                    ${renderInternalWebhookDispatchFailureProjection(status)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Boundary Status</strong>
                <ul>
                    ${fieldItem('internal webhook post', status.internal_webhook_post_performed === true ? 'performed' : status.server_configured_internal_webhook_enabled === true ? 'ready' : 'blocked')}
                    ${fieldItem('allowlisted URL authority', status.server_configured_allowlisted_url_enabled === true ? 'server configured' : 'blocked')}
                    ${fieldItem('operator URL authority', status.operator_destination_url_enabled === false ? 'blocked' : status.operator_destination_url_enabled)}
                    ${fieldItem('raw target URL', status.raw_target_url_exposed === false ? 'blocked' : status.raw_target_url_exposed)}
                    ${fieldItem('raw headers', status.raw_headers_exposed === false ? 'blocked' : status.raw_headers_exposed)}
                    ${fieldItem('raw package payload', status.raw_package_payload_exposed === false ? 'blocked' : status.raw_package_payload_exposed)}
                    ${fieldItem('raw package bytes', status.raw_package_bytes_exposed === false ? 'blocked' : status.raw_package_bytes_exposed)}
                    ${fieldItem('connector run created', status.connector_run_created === false ? 'blocked' : status.connector_run_created)}
                    ${fieldItem('connector target created', status.connector_run_target_created === false ? 'blocked' : status.connector_run_target_created)}
                    ${fieldItem('provider public URL', status.provider_public_url_enabled === false ? 'blocked' : status.provider_public_url_enabled)}
                    ${fieldItem('provider-private signed URL', status.provider_private_signed_url_enabled === false ? 'blocked' : status.provider_private_signed_url_enabled)}
                    ${fieldItem('cloud object store write', status.cloud_object_store_write_enabled === false ? 'blocked' : status.cloud_object_store_write_enabled)}
                    ${fieldItem('rendered write submit control', status.rendered_write_submit_control_enabled === false ? 'blocked' : status.rendered_write_submit_control_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function setBusy(button, busy, label) {
    button.disabled = busy;
    if (label) {
        button.textContent = busy ? 'Working...' : label;
    }
}

function setCurrentStepChip(selectedChip) {
    elements.stepChips.forEach((chip) => {
        const selected = chip === selectedChip;
        chip.classList.toggle('current', selected);
        if (selected) {
            chip.setAttribute('aria-current', 'step');
        } else {
            chip.removeAttribute('aria-current');
        }
    });
}

function navigateToStep(chip) {
    const targetId = chip.dataset.stepTarget;
    const target = targetId ? document.getElementById(targetId) : null;
    if (!target) return;
    setCurrentStepChip(chip);
    if (target.closest('.operations-dock')) {
        const operationPanel = target.closest('.workband');
        const operationId = OPERATION_DOCK_STEPS.some((step) => step.id === operationPanel?.id)
            ? operationPanel.id
            : targetId;
        setActiveOperation(operationId, { manual: true });
    }
    target.scrollIntoView({ block: 'start', behavior: 'auto' });
    if (typeof target.focus === 'function') {
        target.focus({ preventScroll: true });
    }
}

function setStepChip(element, active) {
    if (!element) return;
    element.disabled = false;
    element.classList.toggle('active', active);
    element.classList.toggle('unavailable', !active);
    element.dataset.available = active ? 'true' : 'false';
}

function operationDockStatus(step) {
    const sessionReady = Boolean(State.gateB?.session_id || currentSessionId());
    const gateCReady = Boolean(State.gateC?.typing_records?.length || sessionSublayerState().typing_records?.length);
    const authority = selectedResultAuthority();
    switch (step.key) {
    case 'intent':
        return State.preflight
            ? { state: 'live', label: 'preflight passed', detail: 'Intent and source posture are loaded.' }
            : { state: 'ready', label: 'ready', detail: 'Run preflight to load source and material previews.' };
    case 'source_intake':
        return { state: 'ready', label: 'ready', detail: 'Upload, inventory, and preview use existing server-authoritative source-intake APIs.' };
    case 'gate_b':
        if (sessionReady) return { state: 'live', label: 'session scoped', detail: 'Gate B has a session-scoped material boundary.' };
        if ((State.materialPreview?.material_candidates || []).length) return { state: 'ready', label: 'review ready', detail: 'Material preview is loaded and ready for Gate B decisions.' };
        return { state: 'blocked', label: 'waiting', detail: 'Run preflight before Gate B review.' };
    case 'gate_c':
        if (gateCReady) return { state: 'live', label: 'typing loaded', detail: 'Gate C typing is available for modality grouping.' };
        if (sessionReady) return { state: 'ready', label: 'preview ready', detail: 'Gate B is committed; Gate C preview can classify material.' };
        return { state: 'blocked', label: 'blocked', detail: 'Commit Gate B before Gate C typing.' };
    case 'plan':
        if (State.planApproval) return { state: 'live', label: 'approved', detail: 'Plan approval state is recorded.' };
        if (State.planPreview) return { state: 'live', label: 'preview loaded', detail: 'Plan preview state is loaded.' };
        if (canPlanPreview()) return { state: 'ready', label: 'preview ready', detail: 'Gate C typing allows plan preview.' };
        return { state: 'blocked', label: 'blocked', detail: 'Commit Gate C typing before plan preview.' };
    case 'results':
        if (recordedResultReview()) return { state: 'live', label: 'review recorded', detail: 'Selected-pass result review is recorded.' };
        if (State.resultStatus?.result_status_available === true) return { state: 'ready', label: 'status ready', detail: 'Selected-pass result status can be reviewed.' };
        if (authority.selected) return { state: 'ready', label: 'selected pass', detail: 'A selected pass exists; inspect terminal result status when available.' };
        return { state: 'blocked', label: 'blocked', detail: 'Execution/result authority is not available in the current session.' };
    case 'package':
        if (packageReviewSubmitState()?.package_review_state || packageReviewSubmitState()?.state) return { state: 'live', label: 'package state', detail: 'Package review state is recorded.' };
        if (canInspectPackageReviewPreview() || canCommitPackageConstruction() || canSubmitPackageReview()) return { state: 'ready', label: 'package ready', detail: 'Package preview, construction, or review controls are available.' };
        return { state: 'blocked', label: 'blocked', detail: 'Approve selected-pass result review before package review.' };
    case 'handoff':
        if (recordedHandoffExportPrepare()) return { state: 'live', label: 'prepared', detail: 'Internal handoff/export preparation is recorded.' };
        if (State.sessionSummary?.handoff_export_prepare?.available === true) return { state: 'ready', label: 'prepare ready', detail: 'Package review approval can be prepared for handoff/export.' };
        return { state: 'blocked', label: 'blocked', detail: 'Approve package review before handoff/export preparation.' };
    case 'aps':
        if (recordedApsHandoffDispatch()) return { state: 'live', label: 'dispatched', detail: 'APS handoff dispatch is recorded.' };
        if (apsHandoffDispatchState()?.available === true) return { state: 'ready', label: 'dispatch ready', detail: 'Prepared handoff/export can dispatch the APS evidence bundle.' };
        return { state: 'blocked', label: 'blocked', detail: 'Prepare handoff/export before APS dispatch.' };
    case 'external':
        if (recordedExternalExportDownloadDelivery()) return { state: 'live', label: 'delivered', detail: 'Same-origin delivery has been requested.' };
        if (recordedExternalExportDownloadPrepare()) return { state: 'ready', label: 'delivery ready', detail: 'External export/download readiness can be delivered.' };
        if (canSubmitExternalExportDownloadPrepare()) return { state: 'ready', label: 'prepare ready', detail: 'Prepared source-directory handoff can prepare external export/download readiness.' };
        if (State.sessionSummary?.external_export_download?.available === true) return { state: 'ready', label: 'prepare ready', detail: 'APS dispatch can prepare external export/download readiness.' };
        return { state: 'blocked', label: 'blocked', detail: 'Dispatch APS handoff before external export/download readiness.' };
    default:
        return { state: 'blocked', label: 'unknown', detail: 'Operation state is not reported.' };
    }
}

function renderOperationDockSummary(activeStep, status) {
    if (!elements.operationsDockSummary || !activeStep || !status) return;
    const activeIndex = OPERATION_DOCK_STEPS.findIndex((step) => step.id === activeStep.id);
    const positionLabel = activeIndex >= 0
        ? `${activeIndex + 1} of ${OPERATION_DOCK_STEPS.length}`
        : 'operation';
    const stateLabel = status.state === 'live'
        ? 'Live-backed'
        : status.state === 'ready'
            ? 'Action-ready'
            : 'Unavailable';
    elements.operationsDockSummary.dataset.operationState = status.state;
    elements.operationsDockSummary.dataset.canvasTarget = activeStep.canvasTarget || '';
    elements.operationsDockSummary.innerHTML = `
        <div class="operation-summary-eyebrow">
            <span>${escapeHtml(positionLabel)}</span>
            <span>${escapeHtml(activeStep.canvasLink || 'Layer 3 operation')}</span>
        </div>
        <div class="operation-summary-main">
            <h3>${escapeHtml(activeStep.label)}</h3>
            <span class="operation-summary-state">${escapeHtml(stateLabel)}: ${escapeHtml(status.label)}</span>
        </div>
        <div class="operation-summary-canvas-role">
            <span>Canvas role</span>
            <strong>${escapeHtml(activeStep.canvasRole || activeStep.canvasLink || 'Layer 3 canvas')}</strong>
        </div>
        <p>${escapeHtml(status.detail)}</p>
    `;
}

function renderOperationsDock() {
    if (!elements.operationsDock || !elements.operationsDockNav) return;
    const availableSteps = OPERATION_DOCK_STEPS.filter((step) => document.getElementById(step.id));
    if (!availableSteps.some((step) => step.id === State.activeOperationId)) {
        State.activeOperationId = availableSteps[0]?.id || '';
        State.operationDockManual = false;
    }
    if (!State.operationDockManual) {
        const suggestedStep = [...availableSteps]
            .reverse()
            .find((step) => step.key !== 'source_intake' && operationDockStatus(step).state !== 'blocked');
        if (suggestedStep) State.activeOperationId = suggestedStep.id;
    }
    elements.operationsDock.dataset.activeOperation = State.activeOperationId;
    const activeStep = availableSteps.find((step) => step.id === State.activeOperationId);
    const activeStatus = activeStep ? operationDockStatus(activeStep) : null;
    if (elements.sublayerMapPanel) {
        elements.sublayerMapPanel.dataset.activeOperationCanvas = activeStep?.canvasTarget || '3a';
        elements.sublayerMapPanel.dataset.activeOperationKey = activeStep?.key || 'intent';
    }
    renderOperationDockSummary(activeStep, activeStatus);
    elements.operationsDockNav.innerHTML = availableSteps.map((step, index) => {
        const status = operationDockStatus(step);
        const selected = step.id === State.activeOperationId;
        return `
            <button class="operation-dock-tab ${selected ? 'active' : ''}" type="button" role="tab"
                id="operation-tab-${escapeHtml(step.key)}"
                aria-controls="${escapeHtml(step.id)}"
                aria-selected="${selected ? 'true' : 'false'}"
                tabindex="${selected ? '0' : '-1'}"
                data-operation-target="${escapeHtml(step.id)}"
                data-operation-state="${escapeHtml(status.state)}"
                data-operation-index="${index}">
                <span class="operation-dock-tab-label">${escapeHtml(step.shortLabel)}</span>
                <span class="operation-dock-tab-state">${escapeHtml(status.label)}</span>
                <span class="operation-dock-tab-detail">${escapeHtml(status.detail)}</span>
            </button>
        `;
    }).join('');
    availableSteps.forEach((step) => {
        const panel = document.getElementById(step.id);
        const status = operationDockStatus(step);
        const selected = step.id === State.activeOperationId;
        panel.classList.toggle('operation-panel-active', selected);
        panel.classList.toggle('operation-panel-inactive', !selected);
        panel.dataset.operationState = status.state;
        panel.dataset.operationActive = selected ? 'true' : 'false';
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', `operation-tab-${step.key}`);
    });
    Array.from(elements.operationsDockNav.querySelectorAll('.operation-dock-tab')).forEach((button) => {
        button.addEventListener('click', () => setActiveOperation(button.dataset.operationTarget, { focusPanel: true, manual: true }));
        button.addEventListener('keydown', handleOperationDockKeydown);
    });
}

function setActiveOperation(operationId, { focusPanel = false, focusButton = false, manual = false } = {}) {
    if (manual) State.operationDockManual = true;
    if (!operationId || State.activeOperationId === operationId) {
        if (focusPanel) document.getElementById(operationId)?.focus({ preventScroll: true });
        return;
    }
    State.activeOperationId = operationId;
    renderOperationsDock();
    const panel = document.getElementById(operationId);
    const button = elements.operationsDockNav?.querySelector(`[data-operation-target="${CSS.escape(operationId)}"]`);
    if (focusButton && button) button.focus();
    if (focusPanel && panel) {
        panel.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'auto' });
        panel.focus({ preventScroll: true });
    }
}

function handleOperationDockKeydown(event) {
    const keys = ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'];
    if (!keys.includes(event.key)) return;
    const buttons = Array.from(elements.operationsDockNav?.querySelectorAll('.operation-dock-tab') || []);
    const currentIndex = buttons.indexOf(event.currentTarget);
    if (currentIndex < 0) return;
    event.preventDefault();
    let nextIndex = currentIndex;
    if (event.key === 'Home') {
        nextIndex = 0;
    } else if (event.key === 'End') {
        nextIndex = buttons.length - 1;
    } else {
        const delta = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : -1;
        nextIndex = (currentIndex + delta + buttons.length) % buttons.length;
    }
    setActiveOperation(buttons[nextIndex].dataset.operationTarget, { focusButton: true, manual: true });
}

function providerPrivateSignedUrlPanelState() {
    if (State.providerPrivateSignedUrlError) {
        return { label: State.providerPrivateSignedUrlError.error_code || 'provider_private_signed_url_blocked', pill: 'blocked', message: State.providerPrivateSignedUrlError.message || 'Provider-private signed URL control is blocked.' };
    }
    const stateName = providerPrivateSignedUrlLatestState();
    if (stateName === 'provider_private_signed_url_revoked') {
        return { label: stateName, pill: 'ready', message: 'Provider-private signed URL receipt has been revoked; a replacement can be prepared.' };
    }
    if (stateName === 'provider_private_signed_url_expired') {
        return { label: stateName, pill: 'ready', message: 'Provider-private signed URL receipt has expired; a replacement can be prepared.' };
    }
    if (stateName === 'provider_private_signed_url_prepared') {
        return { label: stateName, pill: 'ready', message: 'Provider-private signed URL receipt is prepared; use remains closed for this lane.' };
    }
    if (recordedExternalExportDownloadPrepare() && externalExportDownloadDeliveryUiAdmitted()) {
        return { label: 'provider_private_signed_url_ui_ready', pill: 'ready', message: 'Ready to prepare a redacted provider-private signed URL receipt.' };
    }
    return { label: 'provider_private_signed_url_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before provider-private signed URL controls.' };
}

function providerPrivateSignedUrlDisplayValue(value) {
    if (Array.isArray(value)) return value.length ? value.join(', ') : 'none';
    if (value === true) return 'true';
    if (value === false) return 'false';
    return value ?? 'none';
}

function renderProviderPrivateSignedUrlPanel() {
    const provider = State.providerPrivateSignedUrlRevoke || State.providerPrivateSignedUrlStatus || State.providerPrivateSignedUrlPrepare || {};
    const panelState = providerPrivateSignedUrlPanelState();
    const audit = provider.audit_receipt || {};
    const rows = {
        receipt_id: provider.provider_signed_url_receipt_id,
        provider_private_state: provider.provider_signed_url_state,
        delivery_mode: provider.delivery_mode,
        provider_url_redacted: provider.provider_url_redacted,
        expires_at: provider.provider_url_expires_at,
        replay_policy: provider.provider_url_replay_policy,
        use_count: provider.provider_url_use_count,
        max_use_count: provider.provider_url_max_use_count,
        revoked: provider.provider_url_revoked,
        source_artifact_hash: provider.source_artifact_hash,
        source_artifact_size_bytes: provider.source_artifact_size_bytes,
        audit_receipt_id: audit.audit_event_id || audit.provider_private_signed_url_audit_event_id,
        audit_reason_code: audit.reason_code,
        next_allowed_actions: provider.next_allowed_actions,
        use_route: 'closed_not_implemented',
    };
    elements.providerPrivateSignedUrlPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            ${Object.entries(rows).map(([label, value]) => `
                <section class="result-review-card">
                    <strong>${escapeHtml(label.replace(/_/g, ' '))}</strong>
                    <p>${escapeHtml(providerPrivateSignedUrlDisplayValue(value))}</p>
                </section>
            `).join('')}
        </div>
    `;
    elements.providerPrivateSignedUrlPrepare.disabled = !canPrepareProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlStatus.disabled = !canInspectProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlRevoke.disabled = !canRevokeProviderPrivateSignedUrl();
}

function providerPublicUrlPanelState() {
    if (State.providerPublicUrlError) {
        return { label: State.providerPublicUrlError.error_code || 'provider_public_url_blocked', pill: 'blocked', message: State.providerPublicUrlError.message || 'Provider-public URL control is blocked.' };
    }
    const stateName = providerPublicUrlLatestState();
    if (stateName === 'provider_public_url_revoked') {
        return { label: stateName, pill: 'ready', message: 'Provider-public URL receipt has been revoked; a replacement can be prepared from provider-private authority.' };
    }
    if (stateName === 'provider_public_url_expired') {
        return { label: stateName, pill: 'ready', message: 'Provider-public URL receipt has expired; a replacement can be prepared from provider-private authority.' };
    }
    if (State.providerPublicUrlUse?.delivery_use_decision === 'allowed') {
        return { label: 'provider_public_url_use_allowed', pill: 'ready', message: 'Server allowed the redacted provider-public use decision; raw URL delivery remains blocked.' };
    }
    if (State.providerPublicUrlUse?.delivery_use_decision === 'denied') {
        const reason = State.providerPublicUrlUse.delivery_use_denied_reason || 'provider_public_url_use_denied';
        return { label: 'provider_public_url_use_denied', pill: 'blocked', message: `Server denied the redacted provider-public use decision: ${reason}.` };
    }
    if (stateName === 'provider_public_url_prepared') {
        return { label: stateName, pill: 'ready', message: 'Provider-public URL receipt is prepared; the redacted use-decision control is available while raw public URL exposure remains closed.' };
    }
    if (providerPrivateSignedUrlReceiptId() && providerPrivateSignedUrlLatestState() === 'provider_private_signed_url_prepared') {
        return { label: 'provider_public_url_ui_ready', pill: 'ready', message: 'Ready to prepare a server-redacted provider-public URL receipt.' };
    }
    return { label: 'provider_public_url_ui_unavailable', pill: 'blocked', message: 'Prepare a provider-private receipt before provider-public URL controls.' };
}

function providerPublicUrlDisplayValue(value) {
    if (Array.isArray(value)) return value.length ? value.join(', ') : 'none';
    if (value === true) return 'true';
    if (value === false) return 'false';
    return value ?? 'none';
}

function renderProviderPublicUrlPanel() {
    const provider = providerPublicUrlLatestSnapshot();
    const panelState = providerPublicUrlPanelState();
    const audit = provider.audit_receipt || {};
    const rows = {
        receipt_id: provider.provider_public_url_receipt_id,
        provider_public_state: provider.provider_public_url_state,
        provider_private_receipt_id: provider.provider_private_signed_url_receipt_id || providerPrivateSignedUrlReceiptId(),
        delivery_mode: provider.delivery_mode || 'provider_public_url',
        delivery_use_mode: provider.delivery_use_mode,
        delivery_use_decision: provider.delivery_use_decision,
        delivery_use_denied_reason: provider.delivery_use_denied_reason,
        provider_public_url_redacted: provider.provider_public_url_redacted,
        expires_at: provider.provider_public_url_expires_at,
        replay_policy: provider.provider_public_url_replay_policy,
        revocation_supported: provider.provider_public_url_revocation_supported,
        revoked: provider.provider_public_url_revoked,
        raw_public_url_exposed: provider.raw_public_url_exposed === true ? true : false,
        public_url_enabled: provider.public_url_enabled === true ? true : false,
        provider_network_enabled: provider.provider_network_enabled === true ? true : false,
        provider_object_write_enabled: provider.provider_object_write_enabled === true ? true : false,
        public_redirect_enabled: provider.public_redirect_enabled === true ? true : false,
        byte_streaming_enabled: provider.byte_streaming_enabled === true ? true : false,
        durable_use_row_created: provider.durable_use_row_created === true ? true : false,
        audit_row_created: provider.audit_row_created === true ? true : false,
        provider_credentials_enabled: provider.provider_credentials_enabled === true ? true : false,
        connector_dispatch_enabled: provider.connector_dispatch_enabled === true ? true : false,
        package_mutation_enabled: provider.package_mutation_enabled === true ? true : false,
        source_expansion_enabled: provider.source_expansion_enabled === true ? true : false,
        rag_vector_indexing_enabled: provider.rag_vector_indexing_enabled === true ? true : false,
        frontend_durable_authority_enabled: provider.frontend_durable_authority_enabled === true ? true : false,
        source_artifact_hash: provider.source_artifact_hash,
        source_artifact_size_bytes: provider.source_artifact_size_bytes,
        audit_receipt_id: audit.audit_event_id || audit.provider_public_url_audit_event_id,
        audit_reason_code: audit.reason_code,
        next_allowed_actions: provider.next_allowed_actions,
        delivery_route: 'closed_not_implemented',
        use_route: '/handoff/export/download/provider-public-url/use redacted_decision_only',
        raw_public_url_display: 'blocked_not_rendered',
        browser_durable_authority: 'blocked_not_persisted',
    };
    elements.providerPublicUrlPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            ${Object.entries(rows).map(([label, value]) => `
                <section class="result-review-card">
                    <strong>${escapeHtml(label.replace(/_/g, ' '))}</strong>
                    <p>${escapeHtml(providerPublicUrlDisplayValue(value))}</p>
                </section>
            `).join('')}
        </div>
    `;
    elements.providerPublicUrlPrepare.disabled = !canPrepareProviderPublicUrl();
    elements.providerPublicUrlStatus.disabled = !canInspectProviderPublicUrl();
    elements.providerPublicUrlUse.disabled = !canUseProviderPublicUrl();
    elements.providerPublicUrlRevoke.disabled = !canRevokeProviderPublicUrl();
}

function setGateControls() {
    const gateCCommitted = isTypingCommitted();
    const sessionId = currentSessionId();
    const authority = selectedResultAuthority();
    const reviewRecorded = Boolean(recordedResultReview());
    const resultReviewControlsEnabled = Boolean(
        State.resultStatus?.result_status_available === true
        && !reviewRecorded
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const packageReviewControlsEnabled = Boolean(
        (packageReviewSubmitState() || {}).package_review_submit_enabled === true
        && !State.packageReviewSubmitPending
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const sourceDirectoryHandoffExportControlsEnabled = isSourceDirectoryQualitativePackageAuthoritySelected();
    const handoffExportControlsEnabled = Boolean(
        (
            (
                State.sessionSummary?.handoff_export_prepare?.available === true
                && (packageReviewSubmitState()?.package_review_state || packageReviewSubmitState()?.state) === 'package_review_approved'
            )
            || sourceDirectoryHandoffExportControlsEnabled
        )
        && !recordedHandoffExportPrepare()
        && !replacementPackageSetAuthorityBusy()
        && !packageSupersessionCommitBusy()
        && !replacementPackageArtifactManifestBusy()
        && !replacementPackageNamespaceBusy()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const apsHandoffControlsEnabled = Boolean(
        apsHandoffDispatchState()?.available === true
        && !recordedApsHandoffDispatch()
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const externalExportDownloadControlsEnabled = Boolean(
        (State.sessionSummary?.external_export_download?.available === true
            || isSourceDirectoryQualitativeHandoffExportPrepareState(handoffExportPrepareState() || {}))
        && !recordedExternalExportDownloadPrepare()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const externalExportDownloadDeliveryControlsEnabled = Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const externalExportDownloadSignedReferenceControlsEnabled = Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
    );
    elements.gateBSubmit.disabled = !(State.materialPreview?.material_candidates || []).length;
    if (elements.rawMixedMaterialize) {
        elements.rawMixedMaterialize.disabled = !canMaterializeRawMixed();
    }
    elements.gateCPreview.disabled = !sessionId || gateCCommitted;
    elements.gateCCommit.disabled = !sessionId || gateCCommitted;
    elements.planPreview.disabled = !canPlanPreview() || Boolean(State.planApproval) || Boolean(State.planRevision) || State.planRevisionPending;
    elements.planReject.disabled = !canPlanRevise();
    elements.planRequestRevision.disabled = !canPlanRevise();
    elements.planApprove.disabled = !canPlanApprove();
    elements.executionSelect.disabled = !canSelectExecution();
    elements.executionStart.disabled = !canStartExecution();
    elements.resultReviewRefresh.disabled = !canRefreshSessionSummary();
    elements.resultStatusInspect.disabled = !canInspectResultStatus();
    elements.resultReviewDecision.disabled = !resultReviewControlsEnabled;
    elements.resultReviewNotes.disabled = !resultReviewControlsEnabled;
    elements.resultReviewSubmit.disabled = !canSubmitResultReview();
    elements.packageReviewPreviewInspect.disabled = !canInspectPackageReviewPreview();
    elements.packageConstructionCommit.disabled = !canCommitPackageConstruction();
    elements.packageSupersessionPreviewSubmit.disabled = !canSubmitPackageSupersessionPreview();
    elements.sourceDirectoryPackageSupersessionPreviewSubmit.disabled = !canSubmitSourceDirectoryPackageSupersessionPreview();
    elements.replacementPackageSetAuthoritySubmit.disabled = !canSubmitReplacementPackageSetAuthority();
    elements.packageSupersessionCommitSubmit.disabled = !canSubmitPackageSupersessionCommit();
    elements.replacementPackageArtifactManifestSubmit.disabled = !canSubmitReplacementPackageArtifactManifest();
    elements.replacementPackageNamespaceSubmit.disabled = !canSubmitReplacementPackageNamespace();
    elements.packageReviewSubmitDecision.disabled = !packageReviewControlsEnabled;
    elements.packageReviewSubmitNotes.disabled = !packageReviewControlsEnabled;
    elements.packageReviewSubmit.disabled = !canSubmitPackageReview();
    elements.handoffExportPrepareDecision.disabled = !handoffExportControlsEnabled;
    elements.handoffExportPrepareNotes.disabled = !handoffExportControlsEnabled;
    elements.handoffExportPrepareSubmit.disabled = !canSubmitHandoffExportPrepare();
    elements.apsHandoffDispatchSubmit.disabled = !apsHandoffControlsEnabled || !canSubmitApsHandoffDispatch();
    elements.externalExportDownloadPrepareSubmit.disabled = !externalExportDownloadControlsEnabled || !canSubmitExternalExportDownloadPrepare();
    elements.externalExportDownloadDeliverySubmit.disabled = !externalExportDownloadDeliveryControlsEnabled || !canSubmitExternalExportDownloadDelivery();
    elements.sourceDirectoryHybridMiddleLifecycleSubmit.disabled = !canSubmitSourceDirectoryHybridMiddleLifecycle();
    elements.sourceDirectoryHybridExternalExportDownloadDeliveryStatus.disabled = !canInspectSourceDirectoryHybridExternalExportDownloadDelivery();
    elements.sourceDirectoryHybridExternalExportDownloadDeliverySubmit.disabled = !canSubmitSourceDirectoryHybridExternalExportDownloadDelivery();
    elements.sourceDirectoryHybridInternalWebhookStatus.disabled = !canInspectSourceDirectoryHybridInternalWebhookStatus();
    elements.sourceDirectoryHybridInternalWebhookSubmit.disabled = !canSubmitSourceDirectoryHybridInternalWebhook();
    elements.externalExportDownloadSignedReferenceGenerate.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canGenerateExternalExportDownloadSignedReference();
    elements.externalExportDownloadSignedReferenceUse.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canUseExternalExportDownloadSignedReference();
    elements.providerPrivateSignedUrlPrepare.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canPrepareProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlStatus.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canInspectProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlRevoke.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canRevokeProviderPrivateSignedUrl();
    elements.providerPublicUrlPrepare.disabled = !canPrepareProviderPublicUrl();
    elements.providerPublicUrlStatus.disabled = !canInspectProviderPublicUrl();
    elements.providerPublicUrlUse.disabled = !canUseProviderPublicUrl();
    elements.providerPublicUrlRevoke.disabled = !canRevokeProviderPublicUrl();
    setStepChip(elements.planStep, canPlanPreview());
    setStepChip(elements.executionStep, Boolean(State.executionSelection || State.sessionSummary?.execution_selection?.selected));
    setStepChip(elements.resultsStep, Boolean(authority.selected && authority.terminal));
    setStepChip(elements.packageStep, isPackageActive());
    setStepChip(elements.handoffStep, isHandoffActive());
}

function renderAll() {
    renderMockupThemeShell();
    renderAuthority();
    renderRawMixedMaterializationPanel();
    renderDatasetVersionCandidates();
    renderApsContentDocumentCandidates();
    renderSublayerMap();
    renderUnavailable(currentDownstreamUnavailable());
    renderContext();
    renderMaterialLedger();
    renderAuthorityMatrixReviewPanel();
    renderLayer3E2EGovernanceLifecycleDashboardPanel();
    renderGateCPanel();
    renderPlanPanel();
    renderExecutionSelectionStartPanel();
    renderResultReviewPanel();
    renderPackageReviewPreviewPanel();
    renderPackageLifecycleDashboardPanel();
    renderPackageSupersessionPreviewPanel();
    renderSourceDirectoryPackageSupersessionPreviewPanel();
    renderReplacementPackageSetAuthorityPanel();
    renderPackageSupersessionCommitPanel();
    renderReplacementPackageArtifactManifestPanel();
    renderReplacementPackageNamespacePanel();
    renderDownstreamAccessLifecycleDashboardPanel();
    renderHandoffExportPreparePanel();
    renderApsHandoffDispatchPanel();
    renderExternalExportDownloadPreparePanel();
    renderExternalExportDownloadDeliveryPanel();
    renderSourceDirectoryHybridMiddleLifecyclePanel();
    renderSourceDirectoryHybridRenderedStatusExtension();
    renderSourceDirectoryHybridExternalExportDownloadDeliveryPanel();
    renderSourceDirectoryHybridInternalWebhookPanel();
    renderExternalExportDownloadSignedReferencePanel();
    renderConnectorLocalDestinationReceiptStatusPanel();
    renderServerOwnedLocalOutboxTargetStatusPanel();
    renderServerOwnedLocalOutboxWriteStatusPanel();
    renderLocalOutboxProviderPrivateHandoffStatusPanel();
    renderExternalLocalExportStatusPanel();
    renderInternalWebhookDispatchStatusPanel();
    renderProviderPrivateSignedUrlPanel();
    renderProviderPublicUrlPanel();
    setGateControls();
    renderOperationsDock();
}

function executionSelectionPayload() {
    const authority = executionPlanAuthority();
    return {
        client_request_id: requestId(),
        session_id: currentSessionId(),
        analysis_plan_id: authority.analysisPlanId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
    };
}

function executionStartPayload() {
    const selection = executionSelectionState();
    const authority = executionPlanAuthority();
    const passRunIds = Array.isArray(selection.pass_run_ids)
        ? selection.pass_run_ids
        : [];
    return {
        client_request_id: requestId(),
        session_id: currentSessionId(),
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: passRunIds[0],
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        execution_mode: 'synchronous_single_pass',
    };
}

function resultStatusPayload(authority = selectedResultAuthority()) {
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        operator_view_mode: 'status_only',
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function resultReviewPayload(authority = selectedResultAuthority()) {
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        operator_decision: elements.resultReviewDecision.value,
        review_notes: elements.resultReviewNotes.value.trim(),
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    const reviewedOutputItems = associatedCohortReviewedOutputItems(authority);
    if (reviewedOutputItems.length) {
        payload.reviewed_output_items = reviewedOutputItems;
    }
    return payload;
}

function packageReviewPreviewPayload(authority = selectedResultAuthority()) {
    const review = recordedApprovedResultReview();
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    if (review?.review_record_ref) {
        payload.result_review_record_ref = review.review_record_ref;
    }
    return payload;
}

function packageConstructionPayload(authority = selectedResultAuthority()) {
    const review = recordedApprovedResultReview();
    const preview = State.packageReviewPreview || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: preview.result_review_record_ref || review?.review_record_ref,
        package_review_preview_hash: preview.package_review_preview_hash,
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function packageReviewSubmitPayload(authority = selectedResultAuthority()) {
    const review = recordedApprovedResultReview();
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const qualitativeAps = isQualitativeApsPackageSubmitState(submit, construction);
    const constructionBasisHash = packageConstructionBasisHash();
    const previewHash = packageReviewPreviewHash();
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: submit.result_review_record_ref || construction.result_review_record_ref || review?.review_record_ref,
        package_review_preview_hash: previewHash,
        reconciliation_record_id: submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        operator_decision: elements.packageReviewSubmitDecision.value,
        decision_notes: elements.packageReviewSubmitNotes.value.trim(),
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (constructionBasisHash) {
        payload.construction_basis_hash = constructionBasisHash;
    }
    if (authority.analysisRunId && !qualitativeAps) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function packageSupersessionPreviewPayload(authority = selectedResultAuthority()) {
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const external = externalExportDownloadPrepareState() || {};
    const connector = State.sessionSummary?.connector_dispatch_record || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        reconciliation_record_id: submit.reconciliation_record_id || construction.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        package_kinds: packageKindsFromState(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        package_review_preview_hash: packageReviewPreviewHash(),
        operator_decision: PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION,
    };
    if (submit.submit_record_ref) {
        payload.package_review_submit_record_ref = submit.submit_record_ref;
    }
    if (handoff.prepare_record_ref) {
        payload.handoff_export_record_ref = handoff.prepare_record_ref;
    }
    if (aps.aps_handoff_record_ref) {
        payload.aps_handoff_record_ref = aps.aps_handoff_record_ref;
    }
    if (external.external_export_download_record_ref) {
        payload.external_export_download_record_ref = external.external_export_download_record_ref;
    }
    if (connector.connector_dispatch_record_ref) {
        payload.connector_dispatch_record_ref = connector.connector_dispatch_record_ref;
    }
    return payload;
}

function sourceDirectoryPackageSupersessionPreviewAuthorityPacket() {
    const raw = elements.sourceDirectoryPackageSupersessionPreviewAuthority?.value?.trim();
    if (!raw) {
        throw new Error('Source-directory package supersession preview requires server package authority JSON.');
    }
    const packet = JSON.parse(raw);
    if (!packet || typeof packet !== 'object' || Array.isArray(packet)) {
        throw new Error('Source-directory package authority JSON must be an object.');
    }
    return packet;
}

function sourceDirectoryPackageSupersessionPreviewPayload() {
    const packet = sourceDirectoryPackageSupersessionPreviewAuthorityPacket();
    const payload = {
        client_request_id: packet.client_request_id || requestId(),
        operator_decision: SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION,
    };
    SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PAYLOAD_FIELDS.forEach((field) => {
        if (packet[field] != null) {
            payload[field] = packet[field];
        }
    });
    if (!payload.package_review_submit_record_ref && packet.submit_record_ref) {
        payload.package_review_submit_record_ref = packet.submit_record_ref;
    }
    if (!payload.package_review_state && (packet.next_state || packet.state)) {
        payload.package_review_state = packet.next_state || packet.state;
    }
    const missing = SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS.filter((field) => {
        const value = payload[field];
        return value == null || value === '' || (Array.isArray(value) && !value.length);
    });
    if (missing.length) {
        throw new Error(`Source-directory package supersession preview authority is missing: ${missing.join(', ')}`);
    }
    for (const field of ['output_package_ids', 'package_kinds', 'payload_hashes']) {
        if (!Array.isArray(payload[field]) || payload[field].length !== 3) {
            throw new Error(`Source-directory package supersession preview authority requires exactly three ${field}.`);
        }
    }
    if (payload.package_review_state !== 'package_review_approved') {
        throw new Error('Source-directory package supersession preview requires package_review_approved authority.');
    }
    return payload;
}

function sourceDirectoryPackageSupersessionPreviewPayloadOrNull() {
    try {
        return sourceDirectoryPackageSupersessionPreviewPayload();
    } catch (_error) {
        return null;
    }
}

function sourceDirectoryQualitativePackageReviewBasePayload() {
    const payload = sourceDirectoryPackageSupersessionPreviewPayload();
    return {
        ...payload,
        client_request_id: requestId(),
    };
}

function sourceDirectoryQualitativeHandoffExportPreparePayload() {
    const payload = {
        ...sourceDirectoryQualitativePackageReviewBasePayload(),
        operator_decision: elements.handoffExportPrepareDecision.value,
        handoff_target: 'internal_export_envelope',
        export_mode: 'prepare_only',
    };
    const notes = elements.handoffExportPrepareNotes.value.trim();
    if (notes) {
        payload.decision_notes = notes;
    }
    return payload;
}

function sourceDirectoryQualitativeHandoffExportPreparePayloadOrNull() {
    try {
        return sourceDirectoryQualitativeHandoffExportPreparePayload();
    } catch (_error) {
        return null;
    }
}

function sourceDirectoryQualitativeExternalExportDownloadPreparePayload() {
    const handoff = handoffExportPrepareState() || {};
    return {
        ...sourceDirectoryQualitativePackageReviewBasePayload(),
        package_review_submit_record_ref: handoff.package_review_submit_record_ref,
        package_review_state: handoff.package_review_state,
        operator_decision: 'prepare_source_directory_external_export_download',
        handoff_target: handoff.handoff_target || 'internal_export_envelope',
        export_mode: handoff.export_mode || 'prepare_only',
        prepare_record_ref: handoff.prepare_record_ref,
        handoff_export_state: handoff.handoff_export_state || handoff.next_state || handoff.state,
        handoff_export_envelope_ref: handoffExportEnvelopeRef(handoff),
        external_export_download_target: SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        download_mode: 'reference_only_prepare',
    };
}

function sourceDirectoryQualitativeExternalExportDownloadPreparePayloadOrNull() {
    try {
        return sourceDirectoryQualitativeExternalExportDownloadPreparePayload();
    } catch (_error) {
        return null;
    }
}

function sourceDirectoryQualitativeExternalExportDownloadDeliveryPayload() {
    const external = externalExportDownloadPrepareState() || {};
    const selectedPackage = sourceDirectoryQualitativeExternalExportDownloadSelectedPackage(external);
    return {
        ...sourceDirectoryQualitativeExternalExportDownloadPreparePayload(),
        package_review_submit_record_ref: external.package_review_submit_record_ref,
        package_review_state: external.package_review_state,
        operator_decision: 'deliver_source_directory_external_export_download',
        prepare_record_ref: external.prepare_record_ref,
        handoff_export_state: external.handoff_export_state,
        handoff_export_envelope_ref: external.handoff_export_envelope_ref,
        external_export_download_record_ref: external.external_export_download_record_ref,
        export_download_descriptor_ref: external.export_download_descriptor_ref,
        external_export_download_state: externalExportDownloadStateName(external),
        delivery_mode: 'same_origin_artifact_stream',
        output_package_id: selectedPackage.output_package_id,
        package_kind: selectedPackage.package_kind,
        package_payload_hash: selectedPackage.package_payload_hash,
    };
}

function sourceDirectoryQualitativeExternalExportDownloadDeliveryPayloadOrNull() {
    try {
        return sourceDirectoryQualitativeExternalExportDownloadDeliveryPayload();
    } catch (_error) {
        return null;
    }
}

function replacementPackageArtifactMaterializationPayload(authority = selectedResultAuthority()) {
    const preview = replacementPackageSetAuthorityPreviewState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const source = replacementPackageSourceArrays(preview);
    const sourcePackageSetHash = replacementPackageSetAuthoritySourcePackageSetHash(preview);
    return {
        client_request_id: requestId(),
        session_id: preview.session_id || authority.sessionId,
        analysis_plan_id: preview.analysis_plan_id || authority.analysisPlanId,
        pass_run_id: preview.pass_run_id || authority.passRunId,
        reconciliation_record_id: preview.reconciliation_record_id || submit.reconciliation_record_id || construction.reconciliation_record_id,
        package_supersession_preview_hash: preview.package_supersession_preview_hash,
        source_package_set_hash: sourcePackageSetHash,
        source_output_package_ids: source.outputPackageIds,
        source_package_kinds: source.packageKinds,
        source_payload_refs: source.payloadRefs,
        source_payload_hashes: source.payloadHashes,
        operator_decision: REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION,
    };
}

function replacementPackageSetAuthorityPayload(materialization, authority = selectedResultAuthority()) {
    return {
        client_request_id: requestId(),
        session_id: materialization.session_id || authority.sessionId,
        analysis_plan_id: materialization.analysis_plan_id || authority.analysisPlanId,
        pass_run_id: materialization.pass_run_id || authority.passRunId,
        reconciliation_record_id: materialization.reconciliation_record_id,
        source_package_set_hash: materialization.source_package_set_hash,
        source_output_package_ids: materialization.source_output_package_ids,
        source_package_kinds: materialization.source_package_kinds,
        source_payload_refs: materialization.source_payload_refs,
        source_payload_hashes: materialization.source_payload_hashes,
        replacement_package_set_id: materialization.replacement_package_set_id,
        replacement_package_set_hash: materialization.replacement_package_set_hash,
        replacement_package_kinds: materialization.replacement_package_kinds,
        replacement_payload_refs: materialization.replacement_payload_refs,
        replacement_payload_hashes: materialization.replacement_payload_hashes,
        authority_basis_hash: materialization.authority_basis_hash,
        operator_decision: REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION,
    };
}

function sourceDirectoryReplacementPackageSetAuthorityPayload() {
    const preview = sourceDirectoryPackageSupersessionPreviewState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return {
        client_request_id: requestId(),
        session_id: preview.session_id,
        analysis_plan_id: preview.analysis_plan_id,
        pass_run_id: preview.pass_run_id,
        reconciliation_record_id: (
            preview.reconciliation_record_id
            || submit.reconciliation_record_id
            || construction.reconciliation_record_id
        ),
        package_supersession_preview_hash: preview.package_supersession_preview_hash,
        source_package_set_hash: preview.source_package_set_hash,
        operator_decision: REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION,
    };
}

async function packageSupersessionCommitPayload(authority = selectedResultAuthority()) {
    const preview = packageSupersessionPreviewState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const source = replacementPackageSourceArrays(preview);
    const downstreamDependencies = Array.isArray(preview.downstream_dependencies)
        ? preview.downstream_dependencies
        : [];
    const downstreamDependencyHash = await stableHash({
        schema_id: 'layer3.package_supersession_downstream_dependencies.v1',
        downstream_dependencies: downstreamDependencies,
    });
    const payload = {
        client_request_id: requestId(),
        session_id: preview.session_id || replacementAuthority.session_id || authority.sessionId,
        analysis_plan_id: preview.analysis_plan_id || replacementAuthority.analysis_plan_id || authority.analysisPlanId,
        pass_run_id: preview.pass_run_id || replacementAuthority.pass_run_id || authority.passRunId,
        reconciliation_record_id: (
            preview.reconciliation_record_id
            || replacementAuthority.reconciliation_record_id
            || submit.reconciliation_record_id
            || construction.reconciliation_record_id
        ),
        package_supersession_preview_hash: preview.package_supersession_preview_hash,
        source_package_set_hash: preview.package_set_hash,
        source_output_package_ids: source.outputPackageIds,
        source_package_kinds: source.packageKinds,
        source_payload_refs: source.payloadRefs,
        source_payload_hashes: source.payloadHashes,
        replacement_package_set_authority_id: replacementAuthority.replacement_package_set_authority_id,
        replacement_package_set_id: replacementAuthority.replacement_package_set_id,
        replacement_package_set_hash: replacementAuthority.replacement_package_set_hash,
        replacement_package_kinds: replacementAuthority.replacement_package_kinds,
        replacement_payload_refs: replacementAuthority.replacement_payload_refs,
        replacement_payload_hashes: replacementAuthority.replacement_payload_hashes,
        replacement_authority_basis_hash: replacementAuthority.authority_basis_hash,
        downstream_dependency_hash: downstreamDependencyHash,
        operator_decision: PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
    };
    payload.commit_basis_hash = await stableHash({
        schema_id: 'layer3.package_supersession_commit_basis.v1',
        mode: 'package_supersession_commit_entry',
        operator_decision: PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
        session_id: payload.session_id,
        analysis_plan_id: payload.analysis_plan_id,
        pass_run_id: payload.pass_run_id,
        reconciliation_record_id: payload.reconciliation_record_id,
        package_supersession_preview_hash: payload.package_supersession_preview_hash,
        source_package_set_hash: payload.source_package_set_hash,
        source_output_package_ids: payload.source_output_package_ids,
        source_package_kinds: payload.source_package_kinds,
        source_payload_refs: payload.source_payload_refs,
        source_payload_hashes: payload.source_payload_hashes,
        replacement_package_set_authority_id: payload.replacement_package_set_authority_id,
        replacement_authority_basis_hash: payload.replacement_authority_basis_hash,
        replacement_package_set_id: payload.replacement_package_set_id,
        replacement_package_set_hash: payload.replacement_package_set_hash,
        replacement_package_kinds: payload.replacement_package_kinds,
        replacement_payload_refs: payload.replacement_payload_refs,
        replacement_payload_hashes: payload.replacement_payload_hashes,
        downstream_dependency_hash: payload.downstream_dependency_hash,
    });
    return payload;
}

function sourceDirectoryPackageSupersessionCommitPayload() {
    const preview = sourceDirectoryPackageSupersessionPreviewState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return {
        client_request_id: requestId(),
        session_id: replacementAuthority.session_id || preview.session_id,
        analysis_plan_id: replacementAuthority.analysis_plan_id || preview.analysis_plan_id,
        pass_run_id: replacementAuthority.pass_run_id || preview.pass_run_id,
        reconciliation_record_id: (
            replacementAuthority.reconciliation_record_id
            || preview.reconciliation_record_id
            || submit.reconciliation_record_id
            || construction.reconciliation_record_id
        ),
        package_supersession_preview_hash: preview.package_supersession_preview_hash,
        source_package_set_hash: preview.source_package_set_hash,
        replacement_package_set_authority_id: replacementAuthority.replacement_package_set_authority_id,
        replacement_authority_basis_hash: replacementAuthority.authority_basis_hash,
        operator_decision: PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
    };
}

function replacementPackageArtifactManifestPayload(authority = selectedResultAuthority()) {
    const materialization = replacementPackageArtifactMaterializationState() || {};
    const replacementAuthority = replacementPackageSetAuthorityState() || {};
    const commit = packageSupersessionCommitState() || {};
    return {
        client_request_id: requestId(),
        session_id: materialization.session_id || replacementAuthority.session_id || commit.session_id || authority.sessionId,
        analysis_plan_id: materialization.analysis_plan_id || replacementAuthority.analysis_plan_id || commit.analysis_plan_id || authority.analysisPlanId,
        pass_run_id: materialization.pass_run_id || replacementAuthority.pass_run_id || commit.pass_run_id || authority.passRunId,
        reconciliation_record_id: (
            materialization.reconciliation_record_id
            || replacementAuthority.reconciliation_record_id
            || commit.reconciliation_record_id
        ),
        replacement_artifact_materialization_id: materialization.replacement_artifact_materialization_id,
        materialization_basis_hash: materialization.materialization_basis_hash,
        replacement_package_set_authority_id: replacementAuthority.replacement_package_set_authority_id,
        replacement_authority_basis_hash: replacementAuthority.authority_basis_hash || commit.replacement_authority_basis_hash,
        package_supersession_commit_id: commit.package_supersession_commit_id,
        package_supersession_commit_basis_hash: commit.commit_basis_hash,
        operator_decision: REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION,
    };
}

async function replacementPackageNamespacePayload() {
    const row = selectedReplacementPackageNamespaceRow();
    if (!row) {
        throw new Error('replacement_package_namespace_row_unavailable');
    }
    const clientRequestId = requestId();
    const authorityBasisHash = await stableHash({
        schema_id: 'layer3.replacement_package_namespace_authority.v1',
        mode: 'replacement_package_namespace_rows',
        session_id: row.session_id,
        source: {
            output_package_id: row.source_output_package_id,
            package_kind: row.source_package_kind,
            package_schema_id: row.package_schema_id,
            payload_ref: row.source_payload_ref,
            payload_hash: row.source_payload_hash,
        },
        replacement_artifact_manifest: {
            replacement_artifact_manifest_id: row.replacement_artifact_manifest_id,
            authority_basis_hash: row.replacement_artifact_manifest_authority_basis_hash,
            artifact_ref: row.artifact_ref,
            artifact_hash: row.artifact_hash,
        },
        replacement_package_set_authority: {
            replacement_package_set_authority_id: row.replacement_package_set_authority_id,
            authority_basis_hash: row.replacement_package_set_authority_basis_hash,
        },
        package_supersession_commit: {
            package_supersession_commit_id: row.package_supersession_commit_id,
            commit_basis_hash: row.package_supersession_commit_basis_hash,
        },
        replacement: {
            package_kind: row.package_kind,
            package_schema_id: row.package_schema_id,
        },
        operator_decision: REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION,
        client_request_id: clientRequestId,
    });
    return {
        client_request_id: clientRequestId,
        session_id: row.session_id,
        replacement_artifact_manifest_id: row.replacement_artifact_manifest_id,
        replacement_package_set_authority_id: row.replacement_package_set_authority_id,
        package_supersession_commit_id: row.package_supersession_commit_id,
        source_output_package_id: row.source_output_package_id,
        package_kind: row.package_kind,
        package_schema_id: row.package_schema_id,
        artifact_ref: row.artifact_ref,
        artifact_hash: row.artifact_hash,
        authority_basis_hash: authorityBasisHash,
        operator_decision: REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION,
    };
}

function handoffExportPreparePayload(authority = selectedResultAuthority()) {
    const handoff = State.sessionSummary?.handoff_export_prepare || {};
    const submit = packageReviewSubmitState() || {};
    const qualitativeAps = isQualitativeApsPackageSubmitState(submit, packageConstructionState() || {});
    const constructionBasisHash = qualitativeAps ? handoff.construction_basis_hash || packageConstructionBasisHash() : null;
    const notes = elements.handoffExportPrepareNotes.value.trim();
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: handoff.result_review_record_ref || submit.result_review_record_ref,
        package_review_preview_hash: handoff.package_review_preview_hash || submit.package_review_preview_hash,
        reconciliation_record_id: handoff.reconciliation_record_id || submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        package_review_submit_record_ref: handoff.package_review_submit_record_ref || submit.submit_record_ref,
        package_review_state: submit.package_review_state || submit.state || handoff.package_review_state,
        package_review_submit_schema_id: handoff.package_review_submit_schema_id || submit.package_review_submit_schema_id || submit.schema_id,
        handoff_target: 'internal_export_envelope',
        export_mode: 'prepare_only',
        operator_decision: elements.handoffExportPrepareDecision.value,
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (notes) {
        payload.decision_notes = notes;
    }
    if (constructionBasisHash) {
        payload.construction_basis_hash = constructionBasisHash;
    }
    if (handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = handoff.analysis_run_id || authority.analysisRunId;
    }
    return payload;
}

function apsHandoffDispatchPayload(authority = selectedResultAuthority()) {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: handoff.result_review_record_ref || submit.result_review_record_ref,
        package_review_preview_hash: handoff.package_review_preview_hash || submit.package_review_preview_hash,
        reconciliation_record_id: handoff.reconciliation_record_id || submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        package_kinds: packageKindsFromState(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        package_review_submit_record_ref: handoff.package_review_submit_record_ref || submit.submit_record_ref,
        package_review_state: submit.package_review_state || submit.state || handoff.package_review_state,
        prepare_record_ref: handoff.prepare_record_ref,
        handoff_export_state: handoff.handoff_export_state || handoff.next_state || handoff.state,
        handoff_export_envelope_ref: handoffExportEnvelopeRef(handoff),
        handoff_target: 'internal_export_envelope',
        export_mode: 'prepare_only',
        aps_handoff_target: 'aps_evidence_bundle',
        dispatch_mode: 'server_side_aps_handoff',
        operator_decision: 'dispatch_aps_handoff',
    };
    if (handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = handoff.analysis_run_id || authority.analysisRunId;
    }
    return payload;
}

function externalExportDownloadPreparePayload(authority = selectedResultAuthority()) {
    const external = State.sessionSummary?.external_export_download || {};
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: external.result_review_record_ref || handoff.result_review_record_ref || submit.result_review_record_ref,
        package_review_preview_hash: external.package_review_preview_hash || handoff.package_review_preview_hash || submit.package_review_preview_hash,
        reconciliation_record_id: external.reconciliation_record_id || handoff.reconciliation_record_id || submit.reconciliation_record_id,
        output_package_ids: Array.isArray(external.output_package_ids) && external.output_package_ids.length ? external.output_package_ids : packageOutputPackageIds(),
        package_kinds: Array.isArray(external.package_kinds) && external.package_kinds.length ? external.package_kinds : packageKindsFromState(),
        payload_refs: Array.isArray(external.payload_refs) && external.payload_refs.length ? external.payload_refs : packagePayloadRefs(),
        payload_hashes: Array.isArray(external.payload_hashes) && external.payload_hashes.length ? external.payload_hashes : packagePayloadHashes(),
        package_review_submit_record_ref: external.package_review_submit_record_ref || handoff.package_review_submit_record_ref || submit.submit_record_ref,
        package_review_state: external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state,
        prepare_record_ref: external.prepare_record_ref || handoff.prepare_record_ref,
        handoff_export_state: external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state,
        handoff_export_envelope_ref: external.handoff_export_envelope_ref || handoffExportEnvelopeRef(handoff),
        handoff_target: external.handoff_target || 'internal_export_envelope',
        export_mode: external.export_mode || 'prepare_only',
        aps_handoff_record_ref: external.aps_handoff_record_ref || aps.aps_handoff_record_ref,
        aps_handoff_state: external.aps_handoff_state || apsHandoffStateName(aps),
        aps_handoff_target: external.aps_handoff_target || aps.aps_handoff_target || 'aps_evidence_bundle',
        dispatch_mode: external.dispatch_mode || aps.dispatch_mode || 'server_side_aps_handoff',
        aps_output_package_id: external.aps_output_package_id || aps.aps_output_package_id,
        aps_output_package_kind: external.aps_output_package_kind || aps.aps_output_package_kind,
        aps_bundle_ref: external.aps_bundle_ref || aps.aps_bundle_ref,
        aps_bundle_id: external.aps_bundle_id || aps.aps_bundle_id,
        aps_schema_id: external.aps_schema_id || aps.aps_schema_id,
        export_download_target: external.export_download_target || 'aps_evidence_bundle_download_reference',
        download_mode: external.download_mode || 'reference_only_prepare',
        operator_decision: 'prepare_external_export_download',
    };
    if (external.analysis_run_id || handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = external.analysis_run_id || handoff.analysis_run_id || authority.analysisRunId;
    }
    if (external.source_artifact_hash) {
        payload.aps_bundle_hash = external.source_artifact_hash;
    }
    if (external.source_artifact_size_bytes != null) {
        payload.aps_bundle_size_bytes = external.source_artifact_size_bytes;
    }
    return payload;
}

function externalExportDownloadDeliveryPayload(authority = selectedResultAuthority()) {
    const external = externalExportDownloadPrepareState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: external.result_review_record_ref,
        package_review_preview_hash: external.package_review_preview_hash,
        reconciliation_record_id: external.reconciliation_record_id,
        output_package_ids: Array.isArray(external.output_package_ids) && external.output_package_ids.length ? external.output_package_ids : packageOutputPackageIds(),
        package_kinds: Array.isArray(external.package_kinds) && external.package_kinds.length ? external.package_kinds : packageKindsFromState(),
        payload_refs: Array.isArray(external.payload_refs) && external.payload_refs.length ? external.payload_refs : packagePayloadRefs(),
        payload_hashes: Array.isArray(external.payload_hashes) && external.payload_hashes.length ? external.payload_hashes : packagePayloadHashes(),
        package_review_submit_record_ref: external.package_review_submit_record_ref,
        package_review_state: external.package_review_state,
        prepare_record_ref: external.prepare_record_ref,
        handoff_export_state: external.handoff_export_state,
        handoff_export_envelope_ref: external.handoff_export_envelope_ref,
        handoff_target: external.handoff_target || 'internal_export_envelope',
        export_mode: external.export_mode || 'prepare_only',
        aps_handoff_record_ref: external.aps_handoff_record_ref,
        aps_handoff_state: external.aps_handoff_state,
        aps_handoff_target: external.aps_handoff_target || 'aps_evidence_bundle',
        dispatch_mode: external.dispatch_mode || 'server_side_aps_handoff',
        aps_output_package_id: external.aps_output_package_id,
        aps_output_package_kind: external.aps_output_package_kind,
        aps_bundle_ref: external.aps_bundle_ref,
        aps_bundle_id: external.aps_bundle_id,
        aps_schema_id: external.aps_schema_id,
        export_download_target: external.export_download_target || 'aps_evidence_bundle_download_reference',
        download_mode: external.download_mode || 'reference_only_prepare',
        operator_decision: 'deliver_external_export_download',
        external_export_download_record_ref: external.external_export_download_record_ref,
        export_download_descriptor_ref: external.export_download_descriptor_ref,
        external_export_download_state: externalExportDownloadStateName(external),
        delivery_mode: 'same_origin_artifact_stream',
    };
    if (external.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = external.analysis_run_id || authority.analysisRunId;
    }
    if (external.source_artifact_hash) {
        payload.aps_bundle_hash = external.source_artifact_hash;
    }
    if (external.source_artifact_size_bytes != null) {
        payload.aps_bundle_size_bytes = external.source_artifact_size_bytes;
    }
    return payload;
}

function externalExportDownloadSignedReferencePayload(authority = selectedResultAuthority()) {
    return externalExportDownloadDeliveryPayload(authority);
}

function providerPrivateSignedUrlPreparePayload(authority = selectedResultAuthority()) {
    const external = externalExportDownloadPrepareState() || {};
    const externalPayload = externalExportDownloadDeliveryPayload(authority);
    return {
        client_request_id: providerPrivateSignedUrlPrepareRequestId(),
        session_id: externalPayload.session_id,
        analysis_plan_id: externalPayload.analysis_plan_id,
        pass_run_id: externalPayload.pass_run_id,
        reconciliation_record_id: externalPayload.reconciliation_record_id,
        external_export_download_record_ref: externalPayload.external_export_download_record_ref,
        export_download_descriptor_ref: externalPayload.export_download_descriptor_ref,
        external_export_download_state: externalPayload.external_export_download_state,
        export_download_target: externalPayload.export_download_target,
        download_mode: externalPayload.download_mode,
        delivery_mode: 'provider_private_signed_url',
        operator_decision: 'prepare_provider_private_signed_url',
        source_artifact_hash: external.source_artifact_hash,
        source_artifact_size_bytes: external.source_artifact_size_bytes,
        recipient_scope: 'external_downstream_recipient_private_artifact_delivery',
        requested_ttl_seconds: 300,
        signed_reference_receipt_id: State.externalExportDownloadSignedReferenceUse?.signedReferenceReceiptId
            || State.externalExportDownloadSignedReference?.signed_reference_receipt_id,
        decision_notes: 'Rendered workbench prepare/status/revoke lane; provider-private use remains closed.',
    };
}

function providerPrivateSignedUrlRevokePayload() {
    const receiptId = providerPrivateSignedUrlReceiptId();
    return {
        client_request_id: requestId(),
        provider_signed_url_receipt_id: receiptId,
        idempotency_key: `provider-private-revoke:${receiptId}`,
        revoked_by: 'layer3-rendered-workbench',
        revocation_reason: 'operator revoked provider-private signed URL from rendered workbench',
        operator_decision: 'revoke_provider_private_signed_url',
        decision_notes: 'Rendered workbench revoke lane; provider-private use remains closed.',
    };
}

function providerPublicUrlPrepareRequestId() {
    if (!State.providerPublicUrlPrepareClientRequestId) {
        State.providerPublicUrlPrepareClientRequestId = requestId();
    }
    return State.providerPublicUrlPrepareClientRequestId;
}

function providerPublicUrlPreparePayload() {
    return {
        client_request_id: providerPublicUrlPrepareRequestId(),
        provider_private_signed_url_receipt_id: providerPrivateSignedUrlReceiptId(),
        recipient_scope: 'external_downstream_recipient_provider_public_url_access',
        requested_ttl_seconds: 300,
        delivery_mode: 'provider_public_url',
        operator_decision: 'prepare_provider_public_url',
        decision_notes: 'Rendered workbench prepare/status/revoke lane; provider-public raw URL exposure remains closed.',
    };
}

function providerPublicUrlUsePayload() {
    const provider = providerPublicUrlAuthorityState();
    const authorityHash = provider.authority_hash || provider.audit_receipt?.authority_hash;
    const payload = {
        client_request_id: requestId(),
        provider_public_url_receipt_id: providerPublicUrlReceiptId(),
        delivery_use_mode: 'fake_provider_redacted_use_decision',
        operator_decision: 'use_provider_public_url_redacted_fake_provider',
    };
    if (authorityHash) {
        payload.expected_authority_hash = authorityHash;
    }
    if (provider.source_artifact_hash) {
        payload.expected_source_artifact_hash = provider.source_artifact_hash;
    }
    if (provider.source_artifact_size_bytes !== undefined && provider.source_artifact_size_bytes !== null) {
        payload.expected_source_artifact_size_bytes = provider.source_artifact_size_bytes;
    }
    return payload;
}

function providerPublicUrlRevokePayload() {
    const receiptId = providerPublicUrlReceiptId();
    return {
        client_request_id: requestId(),
        provider_public_url_receipt_id: receiptId,
        idempotency_key: `provider-public-revoke:${receiptId}`,
        revoked_by: 'layer3-rendered-workbench',
        revocation_reason: 'operator revoked provider-public URL from rendered workbench',
        operator_decision: 'revoke_provider_public_url',
        decision_notes: 'Rendered workbench revoke lane; provider-public raw URL exposure remains closed.',
    };
}

async function useExternalExportDownloadSignedReferenceToken(token) {
    const res = await fetch(`${API_ROOT}/handoff/export/download/signed-reference/use`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signed_reference_token: token }),
    });
    if (!res.ok) {
        const data = await res.json().catch(() => null);
        const err = new Error(data?.message || `HTTP ${res.status}`);
        err.status = res.status;
        err.payload = data;
        throw err;
    }
    await res.arrayBuffer();
    return {
        state: res.headers.get('x-layer3-signed-reference-state') || res.headers.get('x-layer3-delivery-state') || 'external_export_download_signed_reference_delivered',
        schemaId: res.headers.get('x-layer3-schema-id') || 'layer3.external_export_download_signed_reference_use.v1',
        sourceArtifactHash: res.headers.get('x-layer3-source-artifact-hash'),
        expiresAt: res.headers.get('x-layer3-signed-reference-expires-at'),
        signedReferenceReceiptId: res.headers.get('x-layer3-signed-reference-receipt-id'),
        contentType: res.headers.get('content-type'),
    };
}

async function selectExecution() {
    if (!canSelectExecution()) return;
    State.executionSelectionPending = true;
    State.executionSelectionError = null;
    setBusy(elements.executionSelect, true, 'Select Execution');
    try {
        State.executionSelection = await postJson('/execution/select', executionSelectionPayload());
        State.executionStart = null;
        State.executionStartError = null;
        State.resultStatus = null;
        State.resultStatusError = null;
        State.resultReview = null;
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.packageSupersessionPreview = null;
        State.packageSupersessionPreviewError = null;
        clearSourceDirectoryPackageSupersessionPreviewState();
        clearReplacementPackageSetAuthorityState();
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Execution selected for approved plan.');
        renderAll();
    } catch (error) {
        State.executionSelectionError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'execution_selection_request_failed',
            message: error.message,
        };
        addEvent(`Execution selection blocked: ${error.message}`);
        renderAll();
    } finally {
        State.executionSelectionPending = false;
        setBusy(elements.executionSelect, false, 'Select Execution');
        setGateControls();
        renderAll();
    }
}

async function startExecution() {
    if (!canStartExecution()) return;
    State.executionStartPending = true;
    State.executionStartError = null;
    setBusy(elements.executionStart, true, 'Start Execution');
    try {
        State.executionStart = await postJson('/execution/start', executionStartPayload());
        State.resultStatus = null;
        State.resultStatusError = null;
        State.resultReview = null;
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.packageSupersessionPreview = null;
        State.packageSupersessionPreviewError = null;
        clearSourceDirectoryPackageSupersessionPreviewState();
        clearReplacementPackageSetAuthorityState();
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Execution started for selected pass.');
        renderAll();
    } catch (error) {
        State.executionStartError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'analysis_execution_start_request_failed',
            message: error.message,
        };
        addEvent(`Execution start blocked: ${error.message}`);
        renderAll();
    } finally {
        State.executionStartPending = false;
        setBusy(elements.executionStart, false, 'Start Execution');
        setGateControls();
        renderAll();
    }
}

async function refreshSessionSummary() {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    setBusy(elements.resultReviewRefresh, true, 'Refresh Session State');
    try {
        const previousSessionId = State.sessionSummary?.session_id;
        State.sessionSummary = await getJson(`/session/${encodeURIComponent(sessionId)}`);
        if (previousSessionId && previousSessionId !== State.sessionSummary.session_id) {
            clearResultReviewState({ keepSummary: true });
        }
        persistSessionRecoveryAnchor('manual_refresh');
        State.executionSelectionError = null;
        State.executionStartError = null;
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        State.externalExportDownloadSignedReferenceError = null;
        State.sourceDirectoryHybridMiddleLifecycleError = null;
        State.sourceDirectoryHybridInternalWebhookDispatchError = null;
        State.sourceDirectoryHybridInternalWebhookStatusError = null;
        addEvent('Session state refreshed.');
        renderAll();
    } catch (error) {
        State.resultStatusError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'session_summary_request_failed',
            message: error.message,
        };
        addEvent(`Session refresh blocked: ${error.message}`);
        renderAll();
    } finally {
        setBusy(elements.resultReviewRefresh, false, 'Refresh Session State');
        setGateControls();
    }
}

function sourceDirectoryHybridExternalExportDownloadAuthorityPacket() {
    const text = elements.sourceDirectoryHybridExternalExportDownloadDeliveryAuthority.value.trim();
    if (!text) {
        throw new Error('Source-directory hybrid delivery authority JSON is required.');
    }
    const packet = JSON.parse(text);
    if (!packet || typeof packet !== 'object' || Array.isArray(packet)) {
        throw new Error('Source-directory hybrid delivery authority must be a JSON object.');
    }
    return packet.delivery_payload && typeof packet.delivery_payload === 'object'
        ? packet.delivery_payload
        : packet;
}

function sourceDirectoryHybridMiddleLifecycleAuthorityPacket() {
    const text = elements.sourceDirectoryHybridMiddleLifecycleAuthority.value.trim();
    if (!text) {
        throw new Error('Source-directory hybrid middle lifecycle authority JSON is required.');
    }
    const packet = JSON.parse(text);
    if (!packet || typeof packet !== 'object' || Array.isArray(packet)) {
        throw new Error('Source-directory hybrid middle lifecycle authority must be a JSON object.');
    }
    return packet.authority_payload && typeof packet.authority_payload === 'object'
        ? packet.authority_payload
        : packet;
}

function sourceDirectoryHybridMiddleLifecycleBasePayload(packet = sourceDirectoryHybridMiddleLifecycleAuthorityPacket()) {
    const payload = {};
    SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_REQUIRED_FIELDS.forEach((field) => {
        if (packet[field] != null) {
            payload[field] = packet[field];
        }
    });
    const missing = SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_REQUIRED_FIELDS.filter((field) => {
        const value = payload[field];
        return value == null || value === '' || (Array.isArray(value) && !value.length);
    });
    if (missing.length) {
        throw new Error(`Source-directory hybrid middle lifecycle authority is missing: ${missing.join(', ')}`);
    }
    return payload;
}

function sourceDirectoryHybridMiddleLifecycleAuthorityPacketOrNull() {
    try {
        return sourceDirectoryHybridMiddleLifecycleAuthorityPacket();
    } catch (_error) {
        return null;
    }
}

function sourceDirectoryHybridMiddleLifecyclePayload(fields, packet, clientRequestLabel) {
    const base = sourceDirectoryHybridMiddleLifecycleBasePayload(packet);
    const payload = { client_request_id: requestId(clientRequestLabel) };
    fields.forEach((field) => {
        if (base[field] != null) {
            payload[field] = base[field];
        }
    });
    return payload;
}

function sourceDirectoryHybridMiddleLifecycleSelectedPackage(externalPrepare) {
    const packages = Array.isArray(externalPrepare.output_packages) ? externalPrepare.output_packages : [];
    const selected = packages.find((row) => row.package_kind === 'user_facing') || packages[0] || {};
    return {
        output_package_id: selected.output_package_id,
        package_kind: selected.package_kind,
        package_payload_hash: selected.package_payload_hash || selected.payload_hash,
    };
}

function sourceDirectoryHybridMiddleLifecycleDeliveryAuthority(
    externalPreparePayload,
    commit,
    submit,
    handoff,
    externalPrepare,
) {
    const selectedPackage = sourceDirectoryHybridMiddleLifecycleSelectedPackage(externalPrepare);
    return {
        ...externalPreparePayload,
        package_review_submit_record_ref: submit.submit_record_ref,
        package_review_state: submit.package_review_state,
        prepare_record_ref: handoff.prepare_record_ref,
        handoff_export_state: handoff.handoff_export_state,
        handoff_export_envelope_ref: handoff.handoff_export_envelope?.envelope_ref,
        external_export_download_record_ref: externalPrepare.external_export_download_record_ref,
        export_download_descriptor_ref: externalPrepare.export_download_descriptor_ref,
        external_export_download_state: externalPrepare.external_export_download_state,
        output_package_ids: commit.output_package_ids,
        package_kinds: commit.package_kinds,
        payload_hashes: commit.payload_hashes,
        output_packages: externalPrepare.output_packages,
        output_package_id: selectedPackage.output_package_id,
        package_kind: selectedPackage.package_kind,
        package_payload_hash: selectedPackage.package_payload_hash,
    };
}

function canSubmitSourceDirectoryHybridMiddleLifecycle() {
    return Boolean(
        sourceDirectoryHybridMiddleLifecycleAuthorityPacketOrNull()
        && !State.sourceDirectoryHybridMiddleLifecyclePending
        && !State.sourceDirectoryHybridMiddleLifecycle
    );
}

function sourceDirectoryHybridExternalExportDownloadSelectedPackage(packet) {
    if (packet.output_package_id && packet.package_kind && packet.package_payload_hash) {
        return {
            output_package_id: packet.output_package_id,
            package_kind: packet.package_kind,
            package_payload_hash: packet.package_payload_hash,
        };
    }
    const packages = Array.isArray(packet.output_packages) ? packet.output_packages : [];
    const selected = packages.find((row) => row.package_kind === 'user_facing') || packages[0] || {};
    return {
        output_package_id: selected.output_package_id,
        package_kind: selected.package_kind,
        package_payload_hash: selected.package_payload_hash || selected.payload_hash,
    };
}

function sourceDirectoryHybridExternalExportDownloadDeliveryPayload() {
    const packet = sourceDirectoryHybridExternalExportDownloadAuthorityPacket();
    const selectedPackage = sourceDirectoryHybridExternalExportDownloadSelectedPackage(packet);
    const payload = {
        client_request_id: requestId(),
        operator_decision: 'deliver_source_directory_hybrid_external_export_download',
        external_export_download_target: SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        download_mode: 'reference_only_prepare',
        external_export_download_state: 'external_export_download_prepared',
        delivery_mode: 'same_origin_artifact_stream',
        output_package_id: selectedPackage.output_package_id,
        package_kind: selectedPackage.package_kind,
        package_payload_hash: selectedPackage.package_payload_hash,
    };
    SOURCE_DIRECTORY_HYBRID_DELIVERY_PAYLOAD_FIELDS.forEach((field) => {
        if (packet[field] != null && payload[field] == null) {
            payload[field] = packet[field];
        }
    });
    if (!payload.prepare_record_ref && packet.handoff_export_prepare_record_ref) {
        payload.prepare_record_ref = packet.handoff_export_prepare_record_ref;
    }
    payload.handoff_target = payload.handoff_target || 'internal_export_envelope';
    payload.export_mode = payload.export_mode || 'prepare_only';
    const missing = SOURCE_DIRECTORY_HYBRID_DELIVERY_REQUIRED_FIELDS.filter((field) => {
        const value = payload[field];
        return value == null || value === '' || (Array.isArray(value) && !value.length);
    });
    if (missing.length) {
        throw new Error(`Source-directory hybrid delivery authority is missing: ${missing.join(', ')}`);
    }
    return payload;
}

function sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull() {
    try {
        return sourceDirectoryHybridExternalExportDownloadDeliveryPayload();
    } catch (_error) {
        return null;
    }
}

function sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches(payload) {
    const status = State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus || {};
    return Boolean(
        status.delivery_available === true
        && status.schema_id === SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID
        && status.external_export_download_record_ref === payload.external_export_download_record_ref
        && status.export_download_descriptor_ref === payload.export_download_descriptor_ref
        && status.output_package_id === payload.output_package_id
        && status.package_kind === payload.package_kind
        && status.package_payload_hash === payload.package_payload_hash
        && status.same_origin_delivery_enabled === true
        && status.browser_managed_same_origin_attachment_enabled === true
        && status.provider_public_delivery_enabled === false
        && status.provider_private_signed_url_enabled === false
        && status.connector_dispatch_enabled === false
        && status.network_egress_enabled === false
        && status.frontend_durable_authority_enabled === false
        && status.package_payload_rewrite_enabled === false
        && status.source_package_row_mutation_enabled === false
        && status.raw_local_path_exposed === false
    );
}

function canInspectSourceDirectoryHybridExternalExportDownloadDelivery() {
    return Boolean(
        sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull()
        && !State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending
        && !State.sourceDirectoryHybridExternalExportDownloadDeliveryPending
    );
}

function canSubmitSourceDirectoryHybridExternalExportDownloadDelivery() {
    const payload = sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull();
    return Boolean(
        payload
        && sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches(payload)
        && !State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending
        && !State.sourceDirectoryHybridExternalExportDownloadDeliveryPending
        && !State.sourceDirectoryHybridExternalExportDownloadDelivery
    );
}

function sourceDirectoryHybridInternalWebhookAuthorityPacket() {
    const text = elements.sourceDirectoryHybridInternalWebhookAuthority.value.trim();
    if (!text) {
        throw new Error('Source-directory hybrid internal webhook authority JSON is required.');
    }
    const packet = JSON.parse(text);
    if (!packet || typeof packet !== 'object' || Array.isArray(packet)) {
        throw new Error('Source-directory hybrid internal webhook authority must be a JSON object.');
    }
    return packet.dispatch_payload && typeof packet.dispatch_payload === 'object'
        ? packet.dispatch_payload
        : packet;
}

function sourceDirectoryHybridInternalWebhookPayload() {
    const packet = sourceDirectoryHybridInternalWebhookAuthorityPacket();
    const payload = {
        client_request_id: requestId(),
        operator_decision: SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_OPERATOR_DECISION,
        external_export_download_target: SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        download_mode: 'reference_only_prepare',
        external_export_download_state: 'external_export_download_prepared',
        target_identity: 'server_configured_internal_webhook_destination',
        target_class: 'real_connector_invocation',
        dispatch_mode: 'server_configured_allowlisted_internal_webhook_post',
    };
    SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_PAYLOAD_FIELDS.forEach((field) => {
        if (packet[field] != null && payload[field] == null) {
            payload[field] = packet[field];
        }
    });
    if (!payload.prepare_record_ref && packet.handoff_export_prepare_record_ref) {
        payload.prepare_record_ref = packet.handoff_export_prepare_record_ref;
    }
    payload.handoff_target = payload.handoff_target || 'internal_export_envelope';
    payload.export_mode = payload.export_mode || 'prepare_only';
    const missing = SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_REQUIRED_FIELDS.filter((field) => {
        const value = payload[field];
        return value == null || value === '' || (Array.isArray(value) && !value.length);
    });
    if (missing.length) {
        throw new Error(`Source-directory hybrid internal webhook authority is missing: ${missing.join(', ')}`);
    }
    return payload;
}

function sourceDirectoryHybridInternalWebhookPayloadOrNull() {
    try {
        return sourceDirectoryHybridInternalWebhookPayload();
    } catch (_error) {
        return null;
    }
}

function sourceDirectoryHybridInternalWebhookReceiptId() {
    return State.sourceDirectoryHybridInternalWebhookDispatch?.source_directory_internal_webhook_dispatch_receipt_id
        || State.sourceDirectoryHybridInternalWebhookStatus?.source_directory_internal_webhook_dispatch_receipt_id
        || State.sessionSummary?.internal_webhook_dispatch?.source_directory_internal_webhook_dispatch_receipt_id
        || State.sessionSummary?.internal_webhook_dispatch?.latest_source_directory_internal_webhook_dispatch_receipt?.source_directory_internal_webhook_dispatch_receipt_id
        || null;
}

function sourceDirectoryHybridInternalWebhookStatusMatches(payload) {
    const status = State.sourceDirectoryHybridInternalWebhookStatus
        || State.sourceDirectoryHybridInternalWebhookDispatch
        || State.sessionSummary?.internal_webhook_dispatch
        || {};
    return Boolean(
        payload
        && status.source_directory_internal_webhook_dispatch_state === 'source_directory_internal_webhook_dispatched'
        && status.external_export_download_record_ref === payload.external_export_download_record_ref
        && status.export_download_descriptor_ref === payload.export_download_descriptor_ref
        && status.target_identity === 'server_configured_internal_webhook_destination'
        && status.target_class === 'real_connector_invocation'
        && status.dispatch_mode === 'server_configured_allowlisted_internal_webhook_post'
        && status.source_directory_internal_webhook_post_performed === true
        && status.connector_dispatch_enabled === false
        && status.provider_public_url_enabled === false
        && status.provider_private_signed_url_enabled === false
        && status.raw_target_url_exposed === false
        && status.raw_package_payload_exposed === false
        && status.raw_package_bytes_exposed === false
    );
}

function canSubmitSourceDirectoryHybridInternalWebhook() {
    return Boolean(
        sourceDirectoryHybridInternalWebhookPayloadOrNull()
        && !State.sourceDirectoryHybridInternalWebhookDispatchPending
        && !State.sourceDirectoryHybridInternalWebhookStatusPending
        && !sourceDirectoryHybridInternalWebhookReceiptId()
    );
}

function canInspectSourceDirectoryHybridInternalWebhookStatus() {
    return Boolean(
        sourceDirectoryHybridInternalWebhookReceiptId()
        && !State.sourceDirectoryHybridInternalWebhookStatusPending
        && !State.sourceDirectoryHybridInternalWebhookDispatchPending
    );
}

function sourceDirectoryHybridMiddleLifecyclePanelState() {
    if (State.sourceDirectoryHybridMiddleLifecyclePending) {
        return { state: 'preparing', label: 'source_directory_hybrid_middle_lifecycle_preparing', pill: 'preview', message: 'Preparing the source-directory hybrid retrieval, analysis, package, review, and handoff path.' };
    }
    if (State.sourceDirectoryHybridMiddleLifecycleError) {
        return { state: 'blocked', label: State.sourceDirectoryHybridMiddleLifecycleError.error_code || 'source_directory_hybrid_middle_lifecycle_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the source-directory hybrid middle lifecycle.' };
    }
    if (State.sourceDirectoryHybridMiddleLifecycle) {
        return { state: 'prepared', label: 'source_directory_hybrid_middle_lifecycle_prepared', pill: 'ok', message: 'Rendered control prepared source-directory hybrid package handoff authority.' };
    }
    if (sourceDirectoryHybridMiddleLifecycleAuthorityPacketOrNull()) {
        return { state: 'ready', label: 'source_directory_hybrid_middle_lifecycle_ready', pill: 'ok', message: 'Server-derived source-directory hybrid authority can prepare package handoff.' };
    }
    return { state: 'authority_missing', label: 'source_directory_hybrid_middle_lifecycle_authority_missing', pill: 'blocked', message: 'Provide server-derived source-directory hybrid authority before preparing handoff.' };
}

function renderSourceDirectoryHybridMiddleLifecyclePanel() {
    if (!elements.sourceDirectoryHybridMiddleLifecyclePanel) return;
    const payload = sourceDirectoryHybridMiddleLifecycleAuthorityPacketOrNull() || {};
    const lifecycle = State.sourceDirectoryHybridMiddleLifecycle || {};
    const analysis = lifecycle.analysis || {};
    const commit = lifecycle.packageCommit || {};
    const submit = lifecycle.packageReviewSubmit || {};
    const handoff = lifecycle.handoffExportPrepare || {};
    const externalPrepare = lifecycle.externalExportDownloadPrepare || {};
    const panelState = sourceDirectoryHybridMiddleLifecyclePanelState();
    const downstream = [
        'frontend_durable_authority',
        'full_mockup_activation',
        'provider_public_delivery',
        'provider_private_signed_url',
        'connector_dispatch',
        'operator_supplied_destination',
    ];
    elements.sourceDirectoryHybridMiddleLifecyclePanel.dataset.renderedMode = SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_RENDERED_MODE;
    elements.sourceDirectoryHybridMiddleLifecyclePanel.dataset.lifecycleState = panelState.state;
    elements.sourceDirectoryHybridMiddleLifecyclePanel.dataset.frontendDurableAuthority = 'false';
    elements.sourceDirectoryHybridMiddleLifecyclePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Middle Lifecycle</strong>
                <ul>
                    ${fieldItem('rendered mode', SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_RENDERED_MODE)}
                    ${fieldItem('use case', SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_USE_CASE)}
                    ${fieldItem('response authority', SOURCE_DIRECTORY_HYBRID_MIDDLE_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('state', lifecycle.state || panelState.state)}
                    ${fieldItem('frontend durable authority', 'blocked')}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Route Sequence</strong>
                <ul>
                    ${fieldItem('retrieval', SOURCE_DIRECTORY_HYBRID_VECTOR_RETRIEVAL_PATH, { code: true })}
                    ${fieldItem('context packet', SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_PATH, { code: true })}
                    ${fieldItem('analysis', SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH, { code: true })}
                    ${fieldItem('package commit', SOURCE_DIRECTORY_HYBRID_PACKAGE_COMMIT_PATH, { code: true })}
                    ${fieldItem('external prepare', SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Authority</strong>
                <ul>
                    ${fieldItem('material snapshot', payload.material_snapshot_id, { code: true })}
                    ${fieldItem('source batch', payload.source_ingestion_batch_id, { code: true })}
                    ${fieldItem('source file', payload.source_ingestion_file_id, { code: true })}
                    ${fieldItem('query present', Boolean(payload.query_text))}
                    ${fieldItem('analysis focus present', Boolean(payload.analysis_focus))}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Prepared Output</strong>
                <ul>
                    ${fieldItem('analysis status', analysis.status)}
                    ${fieldItem('package status', commit.status)}
                    ${fieldItem('review state', submit.package_review_state)}
                    ${fieldItem('handoff state', handoff.handoff_export_state)}
                    ${fieldItem('external state', externalPrepare.external_export_download_state)}
                    ${fieldItem('package count', Array.isArray(commit.output_package_ids) ? commit.output_package_ids.length : null)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.sourceDirectoryHybridMiddleLifecycleError)}
        </div>
    `;
}

function sourceDirectoryHybridInternalWebhookPanelState() {
    const payload = sourceDirectoryHybridInternalWebhookPayloadOrNull();
    if (State.sourceDirectoryHybridInternalWebhookDispatchPending) {
        return { label: 'source_directory_internal_webhook_dispatching', pill: 'preview', message: 'Submitting one server-configured source-directory internal webhook dispatch.' };
    }
    if (State.sourceDirectoryHybridInternalWebhookStatusPending) {
        return { label: 'source_directory_internal_webhook_status_inspecting', pill: 'preview', message: 'Inspecting durable source-directory internal webhook receipt status.' };
    }
    if (State.sourceDirectoryHybridInternalWebhookDispatchError) {
        return { label: State.sourceDirectoryHybridInternalWebhookDispatchError.error_code || 'source_directory_internal_webhook_dispatch_blocked', pill: 'blocked', message: 'Server authority rejected or blocked source-directory internal webhook dispatch.' };
    }
    if (State.sourceDirectoryHybridInternalWebhookStatusError) {
        return { label: State.sourceDirectoryHybridInternalWebhookStatusError.error_code || 'source_directory_internal_webhook_status_blocked', pill: 'blocked', message: 'Durable source-directory internal webhook status is blocked or unavailable.' };
    }
    if (sourceDirectoryHybridInternalWebhookStatusMatches(payload)) {
        return { label: 'source_directory_internal_webhook_dispatched', pill: 'ok', message: 'The server recorded source-directory internal webhook dispatch and exposes read-only status.' };
    }
    if (sourceDirectoryHybridInternalWebhookReceiptId()) {
        return { label: 'source_directory_internal_webhook_status_available', pill: 'ok', message: 'A durable source-directory internal webhook receipt is available for inspection.' };
    }
    if (payload) {
        return { label: 'source_directory_internal_webhook_ready', pill: 'ok', message: 'Server-derived source-directory authority can submit a configured internal webhook dispatch.' };
    }
    return { label: 'source_directory_internal_webhook_authority_missing', pill: 'blocked', message: 'Provide a server-derived source-directory hybrid external export/download authority payload.' };
}

function renderSourceDirectoryHybridInternalWebhookPanel() {
    if (!elements.sourceDirectoryHybridInternalWebhookPanel) return;
    const payload = sourceDirectoryHybridInternalWebhookPayloadOrNull() || {};
    const dispatch = State.sourceDirectoryHybridInternalWebhookDispatch || {};
    const status = State.sourceDirectoryHybridInternalWebhookStatus
        || State.sessionSummary?.internal_webhook_dispatch
        || {};
    const panelState = sourceDirectoryHybridInternalWebhookPanelState();
    const downstream = [
        'operator_supplied_url',
        'raw_target_url',
        'raw_token',
        'raw_headers',
        'raw_package_payload',
        'raw_package_bytes',
        'provider_public_delivery',
        'provider_private_signed_url',
        'frontend_durable_authority',
        'full_mockup_activation',
    ];
    elements.sourceDirectoryHybridInternalWebhookPanel.dataset.renderedMode = SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_RENDERED_MODE;
    elements.sourceDirectoryHybridInternalWebhookPanel.dataset.frontendDurableAuthority = 'false';
    elements.sourceDirectoryHybridInternalWebhookPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Source-Directory Internal Webhook</strong>
                <ul>
                    ${fieldItem('rendered mode', SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_RENDERED_MODE)}
                    ${fieldItem('use case', SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_USE_CASE)}
                    ${fieldItem('response authority', SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('dispatch schema', dispatch.schema_id || SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID)}
                    ${fieldItem('status schema', status.schema_id)}
                    ${fieldItem('decision', payload.operator_decision || SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_OPERATOR_DECISION)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Basis</strong>
                <ul>
                    ${fieldItem('session', payload.session_id || status.session_id, { code: true })}
                    ${fieldItem('reconciliation', payload.reconciliation_record_id || status.reconciliation_record_id, { code: true })}
                    ${fieldItem('material snapshot', payload.material_snapshot_id || status.material_snapshot_id, { code: true })}
                    ${fieldItem('external readiness', payload.external_export_download_record_ref || status.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor', payload.export_download_descriptor_ref || status.export_download_descriptor_ref, { code: true })}
                    ${fieldItem('package count', Array.isArray(payload.output_package_ids) ? payload.output_package_ids.length : null)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Dispatch Receipt</strong>
                <ul>
                    ${fieldItem('receipt id', sourceDirectoryHybridInternalWebhookReceiptId(), { code: true })}
                    ${fieldItem('state', status.source_directory_internal_webhook_dispatch_state || dispatch.source_directory_internal_webhook_dispatch_state)}
                    ${fieldItem('destination', status.redacted_destination_display_name || dispatch.redacted_destination_display_name)}
                    ${fieldItem('response status', status.response_status_code || dispatch.response_status_code)}
                    ${fieldItem('post performed', status.source_directory_internal_webhook_post_performed || dispatch.source_directory_internal_webhook_post_performed)}
                    ${fieldItem('history count', status.source_directory_internal_webhook_dispatch_history_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Fail-Closed Guards</strong>
                <ul>
                    ${fieldItem('target identity', payload.target_identity || 'server_configured_internal_webhook_destination')}
                    ${fieldItem('dispatch mode', payload.dispatch_mode || 'server_configured_allowlisted_internal_webhook_post')}
                    ${fieldItem('operator destination URL', status.operator_destination_url_enabled === true ? 'unexpected-enabled' : 'blocked')}
                    ${fieldItem('raw target URL', status.raw_target_url_exposed === true ? 'unexpected-exposed' : 'blocked')}
                    ${fieldItem('raw package payload', status.raw_package_payload_exposed === true ? 'unexpected-exposed' : 'blocked')}
                    ${fieldItem('raw package bytes', status.raw_package_bytes_exposed === true ? 'unexpected-exposed' : 'blocked')}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.sourceDirectoryHybridInternalWebhookDispatchError)}
            ${renderErrorCard(State.sourceDirectoryHybridInternalWebhookStatusError)}
        </div>
    `;
}

function sourceDirectoryHybridExternalExportDownloadDeliveryPanelState() {
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryPending) {
        return { label: 'source_directory_hybrid_delivery_submitting', pill: 'preview', message: 'Submitting one source-directory hybrid same-origin attachment request.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDelivery) {
        return { label: State.sourceDirectoryHybridExternalExportDownloadDelivery.state, pill: 'ok', message: 'The browser submitted the source-directory hybrid same-origin delivery request.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryError) {
        return { label: State.sourceDirectoryHybridExternalExportDownloadDeliveryError.error_code || 'source_directory_hybrid_delivery_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the source-directory hybrid delivery request.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending) {
        return { label: 'source_directory_hybrid_delivery_status_inspecting', pill: 'preview', message: 'Validating source-directory hybrid delivery authority with the server.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError) {
        return { label: State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError.error_code || 'source_directory_hybrid_delivery_status_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the source-directory hybrid delivery status request.' };
    }
    const payload = sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull();
    if (payload && sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches(payload)) {
        return { label: 'source_directory_hybrid_delivery_ui_ready', pill: 'ok', message: 'Server status admits one same-origin source-directory hybrid package delivery.' };
    }
    if (payload) {
        return { label: 'source_directory_hybrid_delivery_status_required', pill: 'preview', message: 'Inspect source-directory hybrid delivery status before submitting the attachment request.' };
    }
    return { label: 'source_directory_hybrid_delivery_authority_missing', pill: 'blocked', message: 'Provide a server-derived source-directory hybrid delivery authority payload.' };
}

function sourceDirectoryHybridRenderedStatusExtensionState(payload) {
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryPending) {
        return { state: 'delivery_submitting', label: 'source_directory_hybrid_delivery_submitting', pill: 'preview', message: 'Delivery submission is in progress; rendered status remains a transient server-authority projection.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDelivery) {
        return { state: 'delivery_submitted', label: 'source_directory_hybrid_delivery_submitted', pill: 'ok', message: 'A browser-managed same-origin attachment request was submitted from server authority.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryError) {
        return { state: 'delivery_blocked', label: State.sourceDirectoryHybridExternalExportDownloadDeliveryError.error_code || 'source_directory_hybrid_delivery_blocked', pill: 'blocked', message: 'Delivery remains blocked by server authority.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending) {
        return { state: 'status_inspecting', label: 'source_directory_hybrid_status_inspecting', pill: 'preview', message: 'The status extension is waiting for server-side delivery status authority.' };
    }
    if (State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError) {
        return { state: 'status_blocked', label: State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError.error_code || 'source_directory_hybrid_status_blocked', pill: 'blocked', message: 'Status authority was rejected or blocked by the server.' };
    }
    if (payload && sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches(payload)) {
        return { state: 'status_ready', label: 'source_directory_hybrid_status_ready', pill: 'ok', message: 'Server status admits one same-origin source-directory hybrid delivery path.' };
    }
    if (payload) {
        return { state: 'status_required', label: 'source_directory_hybrid_status_required', pill: 'preview', message: 'A server-derived authority payload is present; delivery status inspection is still required.' };
    }
    return { state: 'unavailable', label: 'source_directory_hybrid_status_unavailable', pill: 'blocked', message: 'Fail-closed until a server-derived source-directory hybrid authority payload is provided.' };
}

function renderSourceDirectoryHybridRenderedStatusExtension() {
    if (!elements.sourceDirectoryHybridRenderedStatusExtension) return;
    const payload = sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull();
    const status = State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus || {};
    const delivery = State.sourceDirectoryHybridExternalExportDownloadDelivery || {};
    const extensionState = sourceDirectoryHybridRenderedStatusExtensionState(payload);
    const statusMatches = Boolean(payload && sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches(payload));
    elements.sourceDirectoryHybridRenderedStatusExtension.dataset.extensionState = extensionState.state;
    elements.sourceDirectoryHybridRenderedStatusExtension.dataset.readOnly = 'true';
    elements.sourceDirectoryHybridRenderedStatusExtension.dataset.frontendDurableAuthority = 'false';
    elements.sourceDirectoryHybridRenderedStatusExtension.dataset.serverAuthority = 'source_directory_hybrid_external_export_download_delivery_status_route';
    elements.sourceDirectoryHybridRenderedStatusExtension.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(extensionState.pill)}">${escapeHtml(extensionState.label)}</span>
            <span class="rail-label">${escapeHtml(extensionState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Rendered Status Extension</strong>
                <ul>
                    ${fieldItem('extension state', extensionState.state)}
                    ${fieldItem('read only', 'true')}
                    ${fieldItem('frontend durable authority', 'blocked')}
                    ${fieldItem('route authority', `POST /api/v1/layer3${SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH}`)}
                    ${fieldItem('delivery route', `POST /api/v1/layer3${SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH}`)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>State Sources</strong>
                <ul>
                    ${fieldItem('status source', 'State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus')}
                    ${fieldItem('delivery source', 'State.sourceDirectoryHybridExternalExportDownloadDelivery')}
                    ${fieldItem('payload source', 'sourceDirectoryHybridExternalExportDownloadDeliveryPayload')}
                    ${fieldItem('status matcher', 'sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches')}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Server Status</strong>
                <ul>
                    ${fieldItem('schema', status.schema_id)}
                    ${fieldItem('available', status.delivery_available)}
                    ${fieldItem('status matches payload', statusMatches)}
                    ${fieldItem('same-origin delivery', status.same_origin_delivery_enabled)}
                    ${fieldItem('attachment managed by browser', status.browser_managed_same_origin_attachment_enabled)}
                    ${fieldItem('delivery state', delivery.state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Fail-Closed Guards</strong>
                <ul>
                    ${fieldItem('provider public delivery', status.provider_public_delivery_enabled === false ? 'blocked' : status.provider_public_delivery_enabled)}
                    ${fieldItem('provider private signed URL', status.provider_private_signed_url_enabled === false ? 'blocked' : status.provider_private_signed_url_enabled)}
                    ${fieldItem('connector dispatch', status.connector_dispatch_enabled === false ? 'blocked' : status.connector_dispatch_enabled)}
                    ${fieldItem('network egress', status.network_egress_enabled === false ? 'blocked' : status.network_egress_enabled)}
                    ${fieldItem('browser storage authority', 'blocked')}
                    ${fieldItem('full mockup activation', 'blocked')}
                </ul>
            </section>
        </div>
    `;
}

function renderSourceDirectoryHybridExternalExportDownloadDeliveryPanel() {
    const status = State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus || {};
    const delivery = State.sourceDirectoryHybridExternalExportDownloadDelivery || {};
    const payload = sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull() || {};
    const panelState = sourceDirectoryHybridExternalExportDownloadDeliveryPanelState();
    const downstream = [
        'provider_public_delivery',
        'provider_private_signed_url',
        'connector_dispatch',
        'destination_write',
        'network_egress',
        'frontend_durable_authority',
        'package_payload_rewrite',
        'source_package_row_mutation',
    ];
    elements.sourceDirectoryHybridExternalExportDownloadDeliveryPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Hybrid Delivery Gate</strong>
                <ul>
                    ${fieldItem('prepare schema', SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID)}
                    ${fieldItem('status schema', status.schema_id)}
                    ${fieldItem('readiness state', payload.external_export_download_state)}
                    ${fieldItem('readiness ref', payload.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', payload.export_download_descriptor_ref, { code: true })}
                    ${fieldItem('target', payload.external_export_download_target || SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET)}
                    ${fieldItem('delivery mode', payload.delivery_mode || 'same_origin_artifact_stream')}
                    ${fieldItem('decision', payload.operator_decision || 'deliver_source_directory_hybrid_external_export_download')}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Selected Package</strong>
                <ul>
                    ${fieldItem('package id', payload.output_package_id || status.output_package_id, { code: true })}
                    ${fieldItem('package kind', payload.package_kind || status.package_kind)}
                    ${fieldItem('payload hash', payload.package_payload_hash || status.package_payload_hash, { code: true })}
                    ${fieldItem('raw path exposed', status.raw_local_path_exposed === false ? 'blocked' : status.raw_local_path_exposed)}
                    ${fieldItem('payload ref redacted', status.payload_ref_redacted)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Status Authority</strong>
                <ul>
                    ${fieldItem('available', status.delivery_available)}
                    ${fieldItem('delivery status', status.delivery_status)}
                    ${fieldItem('streaming performed', status.delivery_streaming_performed)}
                    ${fieldItem('source gate', status.source_gate)}
                    ${fieldItem('validated source gate', status.validated_delivery_source_gate)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Submitted Attempt</strong>
                <ul>
                    ${fieldItem('state', delivery.state)}
                    ${fieldItem('schema', delivery.schemaId)}
                    ${fieldItem('record ref', delivery.externalExportDownloadRecordRef, { code: true })}
                    ${fieldItem('package id', delivery.outputPackageId, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Runtime</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError)}
            ${renderErrorCard(State.sourceDirectoryHybridExternalExportDownloadDeliveryError)}
        </div>
    `;
}

async function inspectResultStatus() {
    if (!canInspectResultStatus()) return;
    setBusy(elements.resultStatusInspect, true, 'Inspect Result Status');
    try {
        State.resultStatus = await postJson('/execution/result/status', resultStatusPayload());
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.packageSupersessionPreview = null;
        State.packageSupersessionPreviewError = null;
        clearSourceDirectoryPackageSupersessionPreviewState();
        clearReplacementPackageSetAuthorityState();
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Result/status authority loaded.');
        renderAll();
    } catch (error) {
        State.resultStatusError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'execution_result_status_request_failed',
            message: error.message,
        };
        addEvent(`Result/status blocked: ${error.message}`);
        renderAll();
    } finally {
        setBusy(elements.resultStatusInspect, false, 'Inspect Result Status');
        setGateControls();
    }
}

async function inspectPackageReviewPreview() {
    if (!canInspectPackageReviewPreview()) return;
    State.packageReviewPreviewPending = true;
    State.packageReviewPreviewError = null;
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    State.packageSupersessionPreview = null;
    State.packageSupersessionPreviewError = null;
    clearSourceDirectoryPackageSupersessionPreviewState();
    clearReplacementPackageSetAuthorityState();
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.packageReviewPreviewInspect, true, 'Inspect Package Preview');
    try {
        State.packageReviewPreview = await postJson('/package/review/preview', packageReviewPreviewPayload());
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Package review preview loaded.');
        renderAll();
    } catch (error) {
        State.packageReviewPreviewError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_review_preview_request_failed',
            message: error.message,
        };
        addEvent(`Package preview blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageReviewPreviewPending = false;
        setBusy(elements.packageReviewPreviewInspect, false, 'Inspect Package Preview');
        renderAll();
    }
}

async function commitPackageConstruction() {
    if (!canCommitPackageConstruction()) return;
    State.packageConstructionPending = true;
    State.packageConstructionError = null;
    State.packageReviewSubmitError = null;
    State.packageSupersessionPreview = null;
    State.packageSupersessionPreviewError = null;
    clearSourceDirectoryPackageSupersessionPreviewState();
    clearReplacementPackageSetAuthorityState();
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.packageConstructionCommit, true, 'Commit Package Set');
    try {
        State.packageConstruction = await postJson('/package/review/commit', packageConstructionPayload());
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Package set committed.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.packageConstruction.session_id)}`);
            persistSessionRecoveryAnchor('package_construction_refresh');
        } catch (refreshError) {
            addEvent(`Package committed; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.packageConstructionError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_construction_commit_request_failed',
            message: error.message,
        };
        addEvent(`Package commit blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageConstructionPending = false;
        setBusy(elements.packageConstructionCommit, false, 'Commit Package Set');
        renderAll();
    }
}

async function submitPackageReview(event) {
    event.preventDefault();
    if (!canSubmitPackageReview()) return;
    State.packageReviewSubmitPending = true;
    State.packageReviewSubmitError = null;
    State.packageSupersessionPreview = null;
    State.packageSupersessionPreviewError = null;
    clearSourceDirectoryPackageSupersessionPreviewState();
    clearReplacementPackageSetAuthorityState();
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.packageReviewSubmit, true, 'Submit Package Review');
    try {
        State.packageReviewSubmit = await postJson('/package/review/submit', packageReviewSubmitPayload());
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Package review submitted.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.packageReviewSubmit.session_id)}`);
            persistSessionRecoveryAnchor('package_review_submit_refresh');
        } catch (refreshError) {
            addEvent(`Package review submitted; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.packageReviewSubmitError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_review_submit_request_failed',
            message: error.message,
        };
        addEvent(`Package review submit blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageReviewSubmitPending = false;
        setBusy(elements.packageReviewSubmit, false, 'Submit Package Review');
        renderAll();
    }
}

function canSubmitSourceDirectoryPackageSupersessionPreview() {
    return Boolean(
        sourceDirectoryPackageSupersessionPreviewPayloadOrNull()
        && !State.sourceDirectoryPackageSupersessionPreviewPending
    );
}

async function submitPackageSupersessionPreview() {
    if (!canSubmitPackageSupersessionPreview()) return;
    State.packageSupersessionPreviewPending = true;
    State.packageSupersessionPreviewError = null;
    clearSourceDirectoryPackageSupersessionPreviewState();
    clearReplacementPackageSetAuthorityState();
    renderAll();
    setBusy(elements.packageSupersessionPreviewSubmit, true, 'Preview Supersession');
    try {
        State.packageSupersessionPreview = await postJson('/package/mutation/preview', packageSupersessionPreviewPayload());
        State.packageSupersessionPreviewError = null;
        addEvent('Package supersession preview recorded as read-only response state.');
        renderAll();
    } catch (error) {
        State.packageSupersessionPreviewError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_supersession_preview_request_failed',
            message: error.message,
        };
        addEvent(`Package supersession preview blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageSupersessionPreviewPending = false;
        setBusy(elements.packageSupersessionPreviewSubmit, false, 'Preview Supersession');
        renderAll();
    }
}

async function submitSourceDirectoryPackageSupersessionPreview() {
    if (!canSubmitSourceDirectoryPackageSupersessionPreview()) return;
    const requestToken = nextSourceDirectoryPackageSupersessionPreviewRequestToken();
    State.sourceDirectoryPackageSupersessionPreviewPending = true;
    State.sourceDirectoryPackageSupersessionPreviewError = null;
    State.sourceDirectoryPackageSupersessionPreview = null;
    clearReplacementPackageSetAuthorityState();
    renderAll();
    setBusy(elements.sourceDirectoryPackageSupersessionPreviewSubmit, true, 'Preview Source-Directory Supersession');
    try {
        const preview = await postJson(
            SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH,
            sourceDirectoryPackageSupersessionPreviewPayload(),
        );
        if (!isCurrentSourceDirectoryPackageSupersessionPreviewRequest(requestToken)) return;
        State.sourceDirectoryPackageSupersessionPreview = preview;
        State.sourceDirectoryPackageSupersessionPreviewError = null;
        addEvent('Source-directory package supersession preview returned as read-only response state.');
        renderAll();
    } catch (error) {
        if (!isCurrentSourceDirectoryPackageSupersessionPreviewRequest(requestToken)) return;
        State.sourceDirectoryPackageSupersessionPreviewError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'source_directory_package_supersession_preview_request_failed',
            message: error.message,
        };
        addEvent(`Source-directory package supersession preview blocked: ${error.message}`);
        renderAll();
    } finally {
        if (isCurrentSourceDirectoryPackageSupersessionPreviewRequest(requestToken)) {
            State.sourceDirectoryPackageSupersessionPreviewPending = false;
        }
        setBusy(elements.sourceDirectoryPackageSupersessionPreviewSubmit, false, 'Preview Source-Directory Supersession');
        renderAll();
    }
}

async function submitReplacementPackageSetAuthority() {
    if (!canSubmitReplacementPackageSetAuthority()) return;
    const sourceDirectoryMode = (
        replacementPackageSetAuthorityPreviewSourceMode() === 'source_directory_package_supersession_preview'
    );
    State.replacementPackageArtifactMaterializationPending = !sourceDirectoryMode;
    State.replacementPackageArtifactMaterializationError = null;
    State.replacementPackageSetAuthority = null;
    State.replacementPackageSetAuthorityPending = false;
    State.replacementPackageSetAuthorityError = null;
    clearPackageSupersessionCommitState();
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.replacementPackageSetAuthoritySubmit, true, 'Record Replacement Set');
    try {
        let materialization = null;
        if (!sourceDirectoryMode) {
            materialization = await postJson(
                '/package/replacement-artifact/materialize',
                replacementPackageArtifactMaterializationPayload(),
            );
            State.replacementPackageArtifactMaterialization = materialization;
            State.replacementPackageArtifactMaterializationError = null;
            State.replacementPackageArtifactMaterializationPending = false;
            addEvent('Replacement package artifacts materialized from server-owned source.');
        }
        State.replacementPackageSetAuthorityPending = true;
        renderAll();

        State.replacementPackageSetAuthority = await postJson(
            sourceDirectoryMode
                ? SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_PATH
                : '/package/replacement-set/record',
            sourceDirectoryMode
                ? sourceDirectoryReplacementPackageSetAuthorityPayload()
                : replacementPackageSetAuthorityPayload(materialization),
        );
        State.replacementPackageSetAuthorityError = null;
        addEvent(sourceDirectoryMode
            ? 'Source-directory replacement package-set authority recorded from server-owned preview.'
            : 'Replacement package-set authority recorded from server-owned materialization.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.replacementPackageSetAuthority.session_id)}`);
            persistSessionRecoveryAnchor('replacement_package_set_authority_refresh');
        } catch (refreshError) {
            addEvent(`Replacement package-set authority recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        const payload = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: State.replacementPackageArtifactMaterializationPending
                ? 'replacement_package_artifact_materialization_request_failed'
                : 'replacement_package_set_authority_request_failed',
            message: error.message,
        };
        if (State.replacementPackageArtifactMaterializationPending) {
            State.replacementPackageArtifactMaterializationError = payload;
            addEvent(`Replacement package artifact materialization blocked: ${error.message}`);
        } else {
            State.replacementPackageSetAuthorityError = payload;
            addEvent(`Replacement package-set authority blocked: ${error.message}`);
        }
        renderAll();
    } finally {
        State.replacementPackageArtifactMaterializationPending = false;
        State.replacementPackageSetAuthorityPending = false;
        setBusy(elements.replacementPackageSetAuthoritySubmit, false, 'Record Replacement Set');
        renderAll();
    }
}

async function submitPackageSupersessionCommit() {
    if (!canSubmitPackageSupersessionCommit()) return;
    const sourceDirectoryMode = (
        packageSupersessionCommitPreviewSourceMode() === 'source_directory_package_supersession_preview'
    );
    State.packageSupersessionCommitPending = true;
    State.packageSupersessionCommitError = null;
    renderAll();
    setBusy(elements.packageSupersessionCommitSubmit, true, 'Commit Supersession');
    try {
        State.packageSupersessionCommit = await postJson(
            sourceDirectoryMode
                ? SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH
                : '/package/supersession/commit',
            sourceDirectoryMode
                ? sourceDirectoryPackageSupersessionCommitPayload()
                : await packageSupersessionCommitPayload(),
        );
        State.packageSupersessionCommitError = null;
        addEvent(sourceDirectoryMode
            ? 'Source-directory package supersession commit lineage recorded.'
            : 'Package supersession commit lineage recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.packageSupersessionCommit.session_id)}`);
            persistSessionRecoveryAnchor('package_supersession_commit_refresh');
        } catch (refreshError) {
            addEvent(`Package supersession commit recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.packageSupersessionCommitError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: error.message === 'browser_sha256_unavailable'
                ? 'package_supersession_commit_hashing_unavailable'
                : 'package_supersession_commit_request_failed',
            message: error.message,
        };
        addEvent(`Package supersession commit blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageSupersessionCommitPending = false;
        setBusy(elements.packageSupersessionCommitSubmit, false, 'Commit Supersession');
        renderAll();
    }
}

async function submitReplacementPackageArtifactManifest() {
    if (!canSubmitReplacementPackageArtifactManifest()) return;
    State.replacementPackageArtifactManifestPending = true;
    State.replacementPackageArtifactManifestError = null;
    renderAll();
    setBusy(elements.replacementPackageArtifactManifestSubmit, true, 'Record Manifest');
    try {
        State.replacementPackageArtifactManifest = await postJson(
            '/package/replacement-artifact/manifest/record-from-authority',
            replacementPackageArtifactManifestPayload(),
        );
        State.replacementPackageArtifactManifestError = null;
        addEvent('Replacement package artifact manifest recorded from server-computed authority.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.replacementPackageArtifactManifest.session_id)}`);
            persistSessionRecoveryAnchor('replacement_package_artifact_manifest_refresh');
        } catch (refreshError) {
            addEvent(`Replacement package artifact manifest recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.replacementPackageArtifactManifestError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'replacement_package_artifact_manifest_request_failed',
            message: error.message,
        };
        addEvent(`Replacement package artifact manifest blocked: ${error.message}`);
        renderAll();
    } finally {
        State.replacementPackageArtifactManifestPending = false;
        setBusy(elements.replacementPackageArtifactManifestSubmit, false, 'Record Manifest');
        renderAll();
    }
}

async function submitReplacementPackageNamespace() {
    if (!canSubmitReplacementPackageNamespace()) return;
    State.replacementPackageNamespacePending = true;
    State.replacementPackageNamespaceError = null;
    renderAll();
    setBusy(elements.replacementPackageNamespaceSubmit, true, 'Record Namespace');
    try {
        State.replacementPackageNamespace = await postJson(
            '/package/replacement-namespace/record',
            await replacementPackageNamespacePayload(),
        );
        State.replacementPackageNamespaceError = null;
        State.replacementPackageNamespaceHistory = [
            ...State.replacementPackageNamespaceHistory,
            State.replacementPackageNamespace,
        ];
        addEvent('Replacement package namespace row recorded from manifest authority.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.replacementPackageNamespace.session_id)}`);
            persistSessionRecoveryAnchor('replacement_package_namespace_refresh');
        } catch (refreshError) {
            addEvent(`Namespace refresh skipped: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.replacementPackageNamespaceError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'replacement_package_namespace_request_failed',
            message: error.message,
        };
        renderAll();
    } finally {
        State.replacementPackageNamespacePending = false;
        setBusy(elements.replacementPackageNamespaceSubmit, false, 'Record Namespace');
        renderAll();
    }
}

async function submitHandoffExportPrepare(event) {
    event.preventDefault();
    if (!canSubmitHandoffExportPrepare()) return;
    const sourceDirectoryMode = isSourceDirectoryQualitativePackageAuthoritySelected();
    State.handoffExportPreparePending = true;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.handoffExportPrepareSubmit, true, 'Submit Preparation');
    try {
        State.handoffExportPrepare = await postJson(
            sourceDirectoryMode
                ? SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_PATH
                : '/handoff/export/prepare',
            sourceDirectoryMode
                ? sourceDirectoryQualitativeHandoffExportPreparePayload()
                : handoffExportPreparePayload(),
        );
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent(sourceDirectoryMode
            ? 'Source-directory handoff/export preparation recorded.'
            : 'Handoff/export preparation recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.handoffExportPrepare.session_id)}`);
            persistSessionRecoveryAnchor('handoff_export_prepare_refresh');
        } catch (refreshError) {
            addEvent(`Handoff/export preparation recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.handoffExportPrepareError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'handoff_export_prepare_request_failed',
            message: error.message,
        };
        addEvent(`Handoff/export preparation blocked: ${error.message}`);
        renderAll();
    } finally {
        State.handoffExportPreparePending = false;
        setBusy(elements.handoffExportPrepareSubmit, false, 'Submit Preparation');
        renderAll();
    }
}

async function submitApsHandoffDispatch(event) {
    event.preventDefault();
    if (!canSubmitApsHandoffDispatch()) return;
    State.apsHandoffDispatchPending = true;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.apsHandoffDispatchSubmit, true, 'Dispatch APS Handoff');
    try {
        State.apsHandoffDispatch = await postJson('/handoff/aps/dispatch', apsHandoffDispatchPayload());
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('APS handoff dispatch recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.apsHandoffDispatch.session_id)}`);
            persistSessionRecoveryAnchor('aps_handoff_dispatch_refresh');
        } catch (refreshError) {
            addEvent(`APS handoff dispatch recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.apsHandoffDispatchError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'aps_handoff_dispatch_request_failed',
            message: error.message,
        };
        addEvent(`APS handoff dispatch blocked: ${error.message}`);
        renderAll();
    } finally {
        State.apsHandoffDispatchPending = false;
        setBusy(elements.apsHandoffDispatchSubmit, false, 'Dispatch APS Handoff');
        renderAll();
    }
}

async function submitExternalExportDownloadPrepare(event) {
    event.preventDefault();
    if (!canSubmitExternalExportDownloadPrepare()) return;
    const sourceDirectoryMode = isSourceDirectoryQualitativeHandoffExportPrepareState(
        handoffExportPrepareState() || {},
    );
    State.externalExportDownloadPreparePending = true;
    State.externalExportDownloadPrepareError = null;
    State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus = null;
    State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusError = null;
    renderAll();
    setBusy(elements.externalExportDownloadPrepareSubmit, true, 'Prepare External Readiness');
    try {
        State.externalExportDownloadPrepare = await postJson(
            sourceDirectoryMode
                ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH
                : '/handoff/export/download/prepare',
            sourceDirectoryMode
                ? sourceDirectoryQualitativeExternalExportDownloadPreparePayload()
                : externalExportDownloadPreparePayload(),
        );
        State.externalExportDownloadPrepareError = null;
        addEvent(sourceDirectoryMode
            ? 'Source-directory external export/download readiness recorded.'
            : 'External export/download readiness recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.externalExportDownloadPrepare.session_id)}`);
            persistSessionRecoveryAnchor('external_export_download_prepare_refresh');
        } catch (refreshError) {
            addEvent(`External readiness recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.externalExportDownloadPrepareError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_prepare_request_failed',
            message: error.message,
        };
        addEvent(`External export/download readiness blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadPreparePending = false;
        setBusy(elements.externalExportDownloadPrepareSubmit, false, 'Prepare External Readiness');
        renderAll();
    }
}

async function submitExternalExportDownloadDelivery(event) {
    event.preventDefault();
    if (!canSubmitExternalExportDownloadDelivery()) return;
    const sourceDirectoryMode = isSourceDirectoryQualitativeExternalExportDownloadPrepareState(
        externalExportDownloadPrepareState() || {},
    );
    const payload = sourceDirectoryMode
        ? sourceDirectoryQualitativeExternalExportDownloadDeliveryPayload()
        : externalExportDownloadDeliveryPayload();
    State.externalExportDownloadDeliveryPending = true;
    State.externalExportDownloadDeliveryError = null;
    State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusError = null;
    let sourceDirectoryStatusValidated = false;
    renderAll();
    setBusy(elements.externalExportDownloadDeliverySubmit, true, 'Deliver External Bundle');
    try {
        if (sourceDirectoryMode) {
            State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusPending = true;
            State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatus = await postJson(
                SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH,
                payload,
            );
            State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusPending = false;
            if (!sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusMatches(payload)) {
                throw new Error('source_directory_external_export_download_delivery_status_mismatch');
            }
            sourceDirectoryStatusValidated = true;
        }
        const delivery = await submitAttachmentForm(
            sourceDirectoryMode
                ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH
                : '/handoff/export/download/deliver',
            payload,
        );
        State.externalExportDownloadDelivery = {
            state: delivery.state || 'external_export_download_delivered',
            schemaId: sourceDirectoryMode
                ? SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID
                : delivery.schemaId,
            filename: delivery.filename,
            sourceArtifactHash: delivery.sourceArtifactHash || payload.package_payload_hash,
            externalExportDownloadRecordRef: delivery.externalExportDownloadRecordRef,
        };
        State.externalExportDownloadDeliveryError = null;
        addEvent(sourceDirectoryMode
            ? 'Source-directory external export/download package submitted as browser-managed same-origin attachment.'
            : 'External export/download bundle submitted as browser-managed same-origin attachment.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(currentSessionId())}`);
            persistSessionRecoveryAnchor('external_export_download_delivery_refresh');
        } catch (refreshError) {
            addEvent(`External delivery completed; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusPending = false;
        if (sourceDirectoryMode && !sourceDirectoryStatusValidated) {
            State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusError = error.payload || {
                schema_id: 'layer3.workbench_error.v1',
                error_code: error.message === 'source_directory_external_export_download_delivery_status_mismatch'
                    ? error.message
                    : 'source_directory_external_export_download_delivery_status_request_failed',
                message: error.message,
            };
        }
        State.externalExportDownloadDelivery = null;
        State.externalExportDownloadDeliveryError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: sourceDirectoryMode
                ? 'source_directory_external_export_download_delivery_request_failed'
                : 'external_export_download_delivery_request_failed',
            message: error.message,
        };
        addEvent(`External export/download delivery blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadDeliveryPending = false;
        State.sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusPending = false;
        setBusy(elements.externalExportDownloadDeliverySubmit, false, 'Deliver External Bundle');
        renderAll();
    }
}

async function submitSourceDirectoryHybridMiddleLifecycle(event) {
    event.preventDefault();
    if (!canSubmitSourceDirectoryHybridMiddleLifecycle()) return;
    const packet = sourceDirectoryHybridMiddleLifecycleAuthorityPacket();
    const retrievalFields = [
        'material_snapshot_id',
        'source_ingestion_batch_id',
        'source_ingestion_file_id',
        'content_sha256',
        'file_identity_hash',
        'authority_basis_hash',
        'payload_hash',
        'index_authority_hash',
        'embedding_index_authority_hash',
        'query_text',
        'top_k',
    ];
    const contextFields = [...retrievalFields, 'limit', 'offset'];
    const analysisFields = [...contextFields, 'analysis_question', 'analysis_focus'];
    State.sourceDirectoryHybridMiddleLifecyclePending = true;
    State.sourceDirectoryHybridMiddleLifecycleError = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError = null;
    State.sourceDirectoryHybridExternalExportDownloadDelivery = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryError = null;
    State.sourceDirectoryHybridInternalWebhookDispatch = null;
    State.sourceDirectoryHybridInternalWebhookDispatchError = null;
    State.sourceDirectoryHybridInternalWebhookStatus = null;
    State.sourceDirectoryHybridInternalWebhookStatusError = null;
    elements.sourceDirectoryHybridExternalExportDownloadDeliveryAuthority.value = '';
    elements.sourceDirectoryHybridInternalWebhookAuthority.value = '';
    renderAll();
    setBusy(elements.sourceDirectoryHybridMiddleLifecycleSubmit, true, 'Prepare Hybrid Handoff');
    try {
        const retrievalPayload = sourceDirectoryHybridMiddleLifecyclePayload(
            retrievalFields,
            packet,
            'source-directory-hybrid-middle-lifecycle-retrieval',
        );
        const retrieval = await postJson(SOURCE_DIRECTORY_HYBRID_VECTOR_RETRIEVAL_PATH, retrievalPayload);
        const contextPayload = sourceDirectoryHybridMiddleLifecyclePayload(
            contextFields,
            packet,
            'source-directory-hybrid-middle-lifecycle-context',
        );
        const contextPacket = await postJson(SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_PATH, contextPayload);
        const analysisPayload = sourceDirectoryHybridMiddleLifecyclePayload(
            analysisFields,
            packet,
            'source-directory-hybrid-middle-lifecycle-analysis',
        );
        const analysis = await postJson(SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH, analysisPayload);
        const analysisStatusPayload = {
            ...analysisPayload,
            client_request_id: requestId('source-directory-hybrid-middle-lifecycle-analysis-status'),
        };
        const analysisStatus = await postJson(SOURCE_DIRECTORY_HYBRID_ANALYSIS_STATUS_PATH, analysisStatusPayload);
        const packageCommitPayload = {
            ...analysisPayload,
            client_request_id: requestId('source-directory-hybrid-middle-lifecycle-package-commit'),
            qualitative_analysis_hash: analysis.qualitative_analysis_hash,
            source_directory_hybrid_package_review_preview_hash: analysis.source_directory_hybrid_package_review_preview_hash,
            operator_decision: 'commit_source_directory_hybrid_context_packet_qualitative_analysis_package',
        };
        const packageCommit = await postJson(SOURCE_DIRECTORY_HYBRID_PACKAGE_COMMIT_PATH, packageCommitPayload);
        const packageReviewSubmitPayload = {
            ...analysisPayload,
            client_request_id: requestId('source-directory-hybrid-middle-lifecycle-package-review-submit'),
            qualitative_analysis_hash: analysis.qualitative_analysis_hash,
            source_directory_hybrid_package_review_preview_hash: analysis.source_directory_hybrid_package_review_preview_hash,
            construction_basis_hash: packageCommit.construction_basis_hash,
            reconciliation_record_id: packageCommit.reconciliation_record_id,
            output_package_ids: packageCommit.output_package_ids,
            package_kinds: packageCommit.package_kinds,
            payload_hashes: packageCommit.payload_hashes,
            operator_decision: 'approved',
        };
        const packageReviewSubmit = await postJson(
            SOURCE_DIRECTORY_HYBRID_PACKAGE_REVIEW_SUBMIT_PATH,
            packageReviewSubmitPayload,
        );
        const handoffExportPreparePayload = {
            ...packageReviewSubmitPayload,
            client_request_id: requestId('source-directory-hybrid-middle-lifecycle-handoff-prepare'),
            operator_decision: 'authorize_prepare',
            package_review_submit_record_ref: packageReviewSubmit.submit_record_ref,
            package_review_state: packageReviewSubmit.package_review_state,
            handoff_target: 'internal_export_envelope',
            export_mode: 'prepare_only',
        };
        const handoffExportPrepare = await postJson(
            SOURCE_DIRECTORY_HYBRID_HANDOFF_EXPORT_PREPARE_PATH,
            handoffExportPreparePayload,
        );
        const externalExportDownloadPreparePayload = {
            ...handoffExportPreparePayload,
            client_request_id: requestId('source-directory-hybrid-middle-lifecycle-external-prepare'),
            operator_decision: 'prepare_source_directory_hybrid_external_export_download',
            prepare_record_ref: handoffExportPrepare.prepare_record_ref,
            handoff_export_state: handoffExportPrepare.handoff_export_state,
            handoff_export_envelope_ref: handoffExportPrepare.handoff_export_envelope?.envelope_ref,
            external_export_download_target: SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET,
            download_mode: 'reference_only_prepare',
        };
        const externalExportDownloadPrepare = await postJson(
            SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH,
            externalExportDownloadPreparePayload,
        );
        const deliveryAuthority = sourceDirectoryHybridMiddleLifecycleDeliveryAuthority(
            externalExportDownloadPreparePayload,
            packageCommit,
            packageReviewSubmit,
            handoffExportPrepare,
            externalExportDownloadPrepare,
        );
        const deliveryAuthorityText = JSON.stringify(deliveryAuthority, null, 2);
        elements.sourceDirectoryHybridExternalExportDownloadDeliveryAuthority.value = deliveryAuthorityText;
        elements.sourceDirectoryHybridInternalWebhookAuthority.value = deliveryAuthorityText;
        State.sourceDirectoryHybridMiddleLifecycle = {
            state: 'source_directory_hybrid_middle_lifecycle_prepared',
            retrieval,
            contextPacket,
            analysis,
            analysisStatus,
            packageCommit,
            packageReviewSubmit,
            handoffExportPrepare,
            externalExportDownloadPrepare,
            deliveryAuthority,
        };
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(currentSessionId())}`);
        } catch (refreshError) {
            addEvent(`Source-directory hybrid handoff prepared; session refresh blocked: ${refreshError.message}`);
        }
        State.sourceDirectoryHybridMiddleLifecycleError = null;
        addEvent('Source-directory hybrid middle lifecycle prepared delivery and webhook authority.');
        renderAll();
    } catch (error) {
        State.sourceDirectoryHybridMiddleLifecycle = null;
        State.sourceDirectoryHybridMiddleLifecycleError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'source_directory_hybrid_middle_lifecycle_request_failed',
            message: error.message,
        };
        addEvent(`Source-directory hybrid middle lifecycle blocked: ${error.message}`);
        renderAll();
    } finally {
        State.sourceDirectoryHybridMiddleLifecyclePending = false;
        setBusy(elements.sourceDirectoryHybridMiddleLifecycleSubmit, false, 'Prepare Hybrid Handoff');
        renderAll();
    }
}

async function inspectSourceDirectoryHybridExternalExportDownloadDelivery(event) {
    event.preventDefault();
    if (!canInspectSourceDirectoryHybridExternalExportDownloadDelivery()) return;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending = true;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError = null;
    State.sourceDirectoryHybridExternalExportDownloadDelivery = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryError = null;
    renderAll();
    setBusy(elements.sourceDirectoryHybridExternalExportDownloadDeliveryStatus, true, 'Inspect Hybrid Delivery');
    try {
        State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus = await postJson(
            SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH,
            sourceDirectoryHybridExternalExportDownloadDeliveryPayload(),
        );
        State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError = null;
        addEvent('Source-directory hybrid external export/download delivery status admitted.');
        renderAll();
    } catch (error) {
        State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus = null;
        State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'source_directory_hybrid_external_export_download_delivery_status_request_failed',
            message: error.message,
        };
        addEvent(`Source-directory hybrid delivery status blocked: ${error.message}`);
        renderAll();
    } finally {
        State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending = false;
        setBusy(elements.sourceDirectoryHybridExternalExportDownloadDeliveryStatus, false, 'Inspect Hybrid Delivery');
        renderAll();
    }
}

async function submitSourceDirectoryHybridExternalExportDownloadDelivery(event) {
    event.preventDefault();
    if (!canSubmitSourceDirectoryHybridExternalExportDownloadDelivery()) return;
    const payload = sourceDirectoryHybridExternalExportDownloadDeliveryPayload();
    State.sourceDirectoryHybridExternalExportDownloadDeliveryPending = true;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryError = null;
    renderAll();
    setBusy(elements.sourceDirectoryHybridExternalExportDownloadDeliverySubmit, true, 'Deliver Hybrid Package');
    try {
        const delivery = await submitAttachmentForm(
            SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH,
            payload,
        );
        State.sourceDirectoryHybridExternalExportDownloadDelivery = {
            state: delivery.state || 'external_export_download_delivery_submitted',
            schemaId: SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
            externalExportDownloadRecordRef: payload.external_export_download_record_ref,
            outputPackageId: payload.output_package_id,
            packagePayloadHash: payload.package_payload_hash,
        };
        State.sourceDirectoryHybridExternalExportDownloadDeliveryError = null;
        addEvent('Source-directory hybrid package submitted as browser-managed same-origin attachment.');
        renderAll();
    } catch (error) {
        State.sourceDirectoryHybridExternalExportDownloadDelivery = null;
        State.sourceDirectoryHybridExternalExportDownloadDeliveryError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'source_directory_hybrid_external_export_download_delivery_request_failed',
            message: error.message,
        };
        addEvent(`Source-directory hybrid delivery blocked: ${error.message}`);
        renderAll();
    } finally {
        State.sourceDirectoryHybridExternalExportDownloadDeliveryPending = false;
        setBusy(elements.sourceDirectoryHybridExternalExportDownloadDeliverySubmit, false, 'Deliver Hybrid Package');
        renderAll();
    }
}

async function submitSourceDirectoryHybridInternalWebhook(event) {
    event.preventDefault();
    if (!canSubmitSourceDirectoryHybridInternalWebhook()) return;
    const payload = sourceDirectoryHybridInternalWebhookPayload();
    State.sourceDirectoryHybridInternalWebhookDispatchPending = true;
    State.sourceDirectoryHybridInternalWebhookDispatchError = null;
    State.sourceDirectoryHybridInternalWebhookStatusError = null;
    renderAll();
    setBusy(elements.sourceDirectoryHybridInternalWebhookSubmit, true, 'Dispatch Internal Webhook');
    try {
        State.sourceDirectoryHybridInternalWebhookDispatch = await postJson(
            SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_DISPATCH_PATH,
            payload,
        );
        State.sourceDirectoryHybridInternalWebhookStatus = State.sourceDirectoryHybridInternalWebhookDispatch;
        State.sourceDirectoryHybridInternalWebhookDispatchError = null;
        addEvent('Source-directory hybrid internal webhook dispatch recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(currentSessionId())}`);
            persistSessionRecoveryAnchor('source_directory_hybrid_internal_webhook_dispatch');
        } catch (refreshError) {
            addEvent(`Internal webhook dispatch recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.sourceDirectoryHybridInternalWebhookDispatch = null;
        State.sourceDirectoryHybridInternalWebhookDispatchError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'source_directory_internal_webhook_dispatch_request_failed',
            message: error.message,
        };
        addEvent(`Source-directory internal webhook dispatch blocked: ${error.message}`);
        renderAll();
    } finally {
        State.sourceDirectoryHybridInternalWebhookDispatchPending = false;
        setBusy(elements.sourceDirectoryHybridInternalWebhookSubmit, false, 'Dispatch Internal Webhook');
        renderAll();
    }
}

async function inspectSourceDirectoryHybridInternalWebhookStatus() {
    if (!canInspectSourceDirectoryHybridInternalWebhookStatus()) return;
    const receiptId = sourceDirectoryHybridInternalWebhookReceiptId();
    State.sourceDirectoryHybridInternalWebhookStatusPending = true;
    State.sourceDirectoryHybridInternalWebhookStatusError = null;
    renderAll();
    setBusy(elements.sourceDirectoryHybridInternalWebhookStatus, true, 'Inspect Webhook Status');
    try {
        State.sourceDirectoryHybridInternalWebhookStatus = await getJson(
            `${SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_STATUS_PATH}/${encodeURIComponent(receiptId)}`,
        );
        State.sourceDirectoryHybridInternalWebhookStatusError = null;
        addEvent('Source-directory hybrid internal webhook status inspected.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(currentSessionId())}`);
            persistSessionRecoveryAnchor('source_directory_hybrid_internal_webhook_status');
        } catch (refreshError) {
            addEvent(`Internal webhook status inspected; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.sourceDirectoryHybridInternalWebhookStatus = null;
        State.sourceDirectoryHybridInternalWebhookStatusError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'source_directory_internal_webhook_status_request_failed',
            message: error.message,
        };
        addEvent(`Source-directory internal webhook status blocked: ${error.message}`);
        renderAll();
    } finally {
        State.sourceDirectoryHybridInternalWebhookStatusPending = false;
        setBusy(elements.sourceDirectoryHybridInternalWebhookStatus, false, 'Inspect Webhook Status');
        renderAll();
    }
}

async function submitExternalExportDownloadSignedReference(event) {
    event.preventDefault();
    if (!canGenerateExternalExportDownloadSignedReference()) return;
    State.externalExportDownloadSignedReferencePending = true;
    State.externalExportDownloadSignedReferenceError = null;
    State.externalExportDownloadSignedReferenceUse = null;
    renderAll();
    setBusy(elements.externalExportDownloadSignedReferenceGenerate, true, 'Generate Signed Reference');
    try {
        State.externalExportDownloadSignedReference = await postJson(
            '/handoff/export/download/signed-reference/generate',
            externalExportDownloadSignedReferencePayload(),
        );
        State.externalExportDownloadSignedReferenceError = null;
        addEvent('External export/download signed reference generated.');
        renderAll();
    } catch (error) {
        State.externalExportDownloadSignedReference = null;
        State.externalExportDownloadSignedReferenceError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_signed_reference_request_failed',
            message: error.message,
        };
        addEvent(`External export/download signed reference blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadSignedReferencePending = false;
        setBusy(elements.externalExportDownloadSignedReferenceGenerate, false, 'Generate Signed Reference');
        renderAll();
    }
}

async function useExternalExportDownloadSignedReference() {
    if (!canUseExternalExportDownloadSignedReference()) return;
    State.externalExportDownloadSignedReferenceUsePending = true;
    State.externalExportDownloadSignedReferenceError = null;
    renderAll();
    setBusy(elements.externalExportDownloadSignedReferenceUse, true, 'Use Signed Reference');
    try {
        State.externalExportDownloadSignedReferenceUse = await useExternalExportDownloadSignedReferenceToken(
            State.externalExportDownloadSignedReference.signed_reference_token,
        );
        addEvent('External export/download signed reference used through same-origin endpoint.');
        renderAll();
    } catch (error) {
        State.externalExportDownloadSignedReferenceUse = null;
        State.externalExportDownloadSignedReferenceError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_signed_reference_use_failed',
            message: error.message,
        };
        addEvent(`External export/download signed reference use blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadSignedReferenceUsePending = false;
        setBusy(elements.externalExportDownloadSignedReferenceUse, false, 'Use Signed Reference');
        renderAll();
    }
}

async function submitResultReview(event) {
    event.preventDefault();
    if (!canSubmitResultReview()) return;
    State.resultReviewPending = true;
    State.resultReviewError = null;
    renderAll();
    setBusy(elements.resultReviewSubmit, true, 'Submit Result Review');
    try {
        State.resultReview = await postJson('/execution/result/review', resultReviewPayload());
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.packageSupersessionPreview = null;
        State.packageSupersessionPreviewError = null;
        clearSourceDirectoryPackageSupersessionPreviewState();
        clearReplacementPackageSetAuthorityState();
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Result review recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.resultReview.session_id)}`);
            persistSessionRecoveryAnchor('result_review_refresh');
        } catch (refreshError) {
            addEvent(`Review recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.resultReviewError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'execution_result_review_request_failed',
            message: error.message,
        };
        addEvent(`Result review blocked: ${error.message}`);
        renderAll();
    } finally {
        State.resultReviewPending = false;
        setBusy(elements.resultReviewSubmit, false, 'Submit Result Review');
        renderAll();
    }
}

async function materializeRawMixedSources() {
    if (!canMaterializeRawMixed()) return;
    State.rawMixedMaterializationPending = true;
    State.rawMixedMaterializationError = null;
    State.rawMixedMaterialization = null;
    renderAll();
    setBusy(elements.rawMixedMaterialize, true, 'Materialize Source IDs');
    try {
        const materialization = await postJson('/source/mixed-corpus/materialize', rawMixedMaterializationPayload());
        const datasetCandidatesRefreshed = await loadDatasetVersionCandidates();
        const apsContentCandidatesRefreshed = await loadApsContentDocumentCandidates();
        if (!datasetCandidatesRefreshed || !apsContentCandidatesRefreshed) {
            State.rawMixedMaterializationError = {
                schema_id: 'layer3.workbench_error.v1',
                error_code: 'raw_mixed_materialized_source_candidate_refresh_failed',
                message: 'Materialized source IDs were not applied because candidate refresh failed.',
            };
            addEvent('Raw mixed materialization blocked after candidate refresh failure.');
            return;
        }
        if (!materializedSourceIdsVisible(materialization)) {
            State.rawMixedMaterializationError = {
                schema_id: 'layer3.workbench_error.v1',
                error_code: 'raw_mixed_materialized_source_candidate_refresh_mismatch',
                message: 'Materialized source IDs were not present after candidate refresh.',
            };
            addEvent('Raw mixed materialization blocked after candidate refresh mismatch.');
            return;
        }
        clearLayer3FlowStateForSourceChange();
        State.rawMixedMaterialization = materialization;
        applyMaterializedSourceIds(materialization);
        addEvent('Raw mixed materialized source IDs selected.');
    } catch (error) {
        State.rawMixedMaterializationError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'raw_mixed_materialization_request_failed',
            message: error.message,
        };
        addEvent(`Raw mixed materialization blocked: ${error.message}`);
    } finally {
        State.rawMixedMaterializationPending = false;
        setBusy(elements.rawMixedMaterialize, false, 'Materialize Source IDs');
        renderAll();
    }
}

async function runPreflightFlow(event) {
    event.preventDefault();
    const intent = elements.intentInput.value.trim();
    const sourceClasses = selectedSourceClasses();
    const datasetVersionIds = selectedDatasetVersionIds();
    const apsContentDocumentIds = selectedApsContentDocumentIds();
    if (datasetVersionIds.length && !sourceClasses.includes('dataset_version')) {
        addEvent('DatasetVersion IDs require the Dataset version source class.');
        renderAll();
        return;
    }
    if (apsContentDocumentIds.length && !sourceClasses.includes('aps_content_document')) {
        addEvent('APS content document IDs require the APS content document source class.');
        renderAll();
        return;
    }
    setBusy(elements.runPreflight, true, 'Run Preflight');
    try {
        State.preflight = await postJson('/preflight', {
            schema_id: 'layer3.preflight_request.v1',
            client_request_id: requestId(),
            natural_language_intent: intent,
            manual_constraints: {
                source_classes: sourceClasses,
            },
            actor: 'operator',
        });
        addEvent('Preflight passed.');
        State.sourcePreview = await postJson('/source-preview', {
            schema_id: 'layer3.source_preview_request.v1',
            client_request_id: requestId(),
            preflight_id: State.preflight.preflight_id,
            selected_source_classes: sourceClasses,
        });
        addEvent('Source preview loaded.');
        State.materialPreview = await postJson('/material-preview', {
            schema_id: 'layer3.material_preview_request.v1',
            client_request_id: requestId(),
            preflight_id: State.preflight.preflight_id,
            source_set_id: State.sourcePreview.source_set_id,
            source_candidate_ids: State.sourcePreview.source_candidates.map((candidate) => candidate.source_candidate_id),
            dataset_version_ids: datasetVersionIds,
            aps_content_document_ids: apsContentDocumentIds,
            query_basis: {
                terms: termsFromIntent(intent),
            },
        });
        initializeGateBDecisions();
        State.gateB = null;
        State.gateC = null;
        State.sessionSummary = null;
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearSessionRecoveryAnchor();
        clearResultReviewState();
        addEvent('Material preview loaded.');
        renderAll();
    } catch (error) {
        addEvent(`Blocked: ${error.message}`);
        if (error.payload?.authority_rail) {
            renderAuthority(error.payload.authority_rail);
        }
    } finally {
        setBusy(elements.runPreflight, false, 'Run Preflight');
        setGateControls();
    }
}

async function commitGateB() {
    const decisions = collectGateBDecisions();
    setBusy(elements.gateBSubmit, true, 'Commit Gate B');
    try {
        State.gateB = await postJson('/gate-b/decision', {
            schema_id: 'layer3.gate_b_decision_request.v1',
            client_request_id: gateBRequestId(),
            preflight_id: State.preflight?.preflight_id,
            source_set_id: State.sourcePreview?.source_set_id,
            material_preview_id: State.materialPreview?.material_preview_id,
            material_preview_hash: State.materialPreview?.material_preview_hash,
            candidate_decisions: decisions,
            commit_reason: 'operator_gate_b_decision',
            actor: 'operator',
        });
        State.gateC = null;
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        clearGateBDraftSnapshot();
        persistSessionRecoveryAnchor('gate_b_commit');
        addEvent(`Gate B committed session ${State.gateB.session_id}.`);
        renderAll();
    } catch (error) {
        addEvent(`Gate B blocked: ${error.message}`);
    } finally {
        setBusy(elements.gateBSubmit, false, 'Commit Gate B');
        setGateControls();
    }
}

async function previewGateC() {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    if (isTypingCommitted()) return;
    setBusy(elements.gateCPreview, true, 'Preview Gate C');
    try {
        State.gateC = await postJson('/gate-c/preview', {
            schema_id: 'layer3.gate_c_preview_request.v1',
            client_request_id: requestId(),
            session_id: sessionId,
            commit_typing: false,
        });
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        persistSessionRecoveryAnchor('gate_c_preview');
        addEvent('Gate C typing preview loaded.');
        renderAll();
    } catch (error) {
        addEvent(`Gate C blocked: ${error.message}`);
    } finally {
        setBusy(elements.gateCPreview, false, 'Preview Gate C');
        setGateControls();
    }
}

async function commitGateC() {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    setBusy(elements.gateCCommit, true, 'Commit Gate C Typing');
    try {
        State.gateC = await postJson('/gate-c/preview', {
            schema_id: 'layer3.gate_c_preview_request.v1',
            client_request_id: requestId(),
            session_id: sessionId,
            commit_typing: true,
        });
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        persistSessionRecoveryAnchor('gate_c_commit');
        addEvent('Gate C typing committed.');
        renderAll();
    } catch (error) {
        addEvent(`Gate C commit blocked: ${error.message}`);
    } finally {
        setBusy(elements.gateCCommit, false, 'Commit Gate C Typing');
        setGateControls();
    }
}

async function previewPlan() {
    if (!canPlanPreview()) return;
    setBusy(elements.planPreview, true, 'Preview Plan');
    try {
        State.planPreview = await postJson('/plan/preview', {
            schema_id: 'layer3.plan_preview_request.v1',
            client_request_id: requestId(),
            session_id: currentSessionId(),
            include_exclusions: true,
            preview_scope: 'owner_service_default',
        });
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        persistSessionRecoveryAnchor('plan_preview');
        addEvent('Plan preview loaded.');
        renderAll();
    } catch (error) {
        State.planPreview = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'plan_preview_request_failed',
            message: error.message,
            next_allowed_actions: [],
        };
        addEvent(`Plan preview blocked: ${error.message}`);
        renderAll();
    } finally {
        setBusy(elements.planPreview, false, 'Preview Plan');
        setGateControls();
    }
}

async function approvePlan() {
    if (!canPlanApprove()) return;
    setBusy(elements.planApprove, true, 'Approve Plan');
    try {
        State.planApproval = await postJson('/plan/approve', {
            schema_id: 'layer3.plan_approval_request.v1',
            client_request_id: requestId(),
            session_id: currentSessionId(),
            preview_id: State.planPreview.preview_id,
            preview_hash: State.planPreview.preview_hash,
            operator_confirmation: true,
            approval_scope: 'owner_service_default',
        });
        clearResultReviewState();
        persistSessionRecoveryAnchor('plan_approval');
        addEvent('Plan approved. Execution has not started.');
        renderAll();
    } catch (error) {
        addEvent(`Plan approval blocked: ${error.message}`);
    } finally {
        setBusy(elements.planApprove, false, 'Approve Plan');
        setGateControls();
    }
}

async function revisePlan(operatorDecision) {
    if (!canPlanRevise()) return;
    const button = operatorDecision === 'reject_current_preview' ? elements.planReject : elements.planRequestRevision;
    const label = operatorDecision === 'reject_current_preview' ? 'Reject Plan' : 'Request Revision';
    State.planRevisionPending = true;
    setBusy(button, true, label);
    setGateControls();
    try {
        State.planRevision = await postJson('/plan/revise', {
            schema_id: 'layer3.plan_revision_request.v1',
            client_request_id: requestId(),
            session_id: currentSessionId(),
            preview_id: State.planPreview.preview_id,
            preview_hash: State.planPreview.preview_hash,
            operator_decision: operatorDecision,
        });
        clearResultReviewState();
        persistSessionRecoveryAnchor('plan_revision');
        addEvent(operatorDecision === 'reject_current_preview' ? 'Plan rejected. Execution has not started.' : 'Plan revision requested. Execution has not started.');
        renderAll();
    } catch (error) {
        addEvent(`Plan revision blocked: ${error.message}`);
    } finally {
        State.planRevisionPending = false;
        setBusy(button, false, label);
        setGateControls();
    }
}

async function submitProviderPrivateSignedUrlPrepare(event) {
    event.preventDefault();
    if (!canPrepareProviderPrivateSignedUrl()) return;
    State.providerPrivateSignedUrlPending = true;
    State.providerPrivateSignedUrlError = null;
    State.providerPrivateSignedUrlStatus = null;
    State.providerPrivateSignedUrlRevoke = null;
    renderAll();
    setBusy(elements.providerPrivateSignedUrlPrepare, true, 'Prepare Provider-Private Receipt');
    try {
        State.providerPrivateSignedUrlPrepare = await postJson(
            '/handoff/export/download/provider-private-signed-url/prepare',
            providerPrivateSignedUrlPreparePayload(),
        );
        persistProviderPrivateReceiptSnapshot(State.providerPrivateSignedUrlPrepare);
        State.providerPrivateSignedUrlPrepareClientRequestId = null;
        addEvent('Provider-private signed URL receipt prepared with redacted state.');
        renderAll();
    } catch (error) {
        State.providerPrivateSignedUrlError = error.payload || { error_code: 'provider_private_signed_url_prepare_failed', message: error.message };
        addEvent(`Provider-private signed URL prepare blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPrivateSignedUrlPending = false;
        setBusy(elements.providerPrivateSignedUrlPrepare, false, 'Prepare Provider-Private Receipt');
        setGateControls();
    }
}

async function inspectProviderPrivateSignedUrlStatus() {
    if (!canInspectProviderPrivateSignedUrl()) return;
    const receiptId = providerPrivateSignedUrlReceiptId();
    State.providerPrivateSignedUrlPending = true;
    State.providerPrivateSignedUrlError = null;
    renderAll();
    setBusy(elements.providerPrivateSignedUrlStatus, true, 'Inspect Provider-Private Status');
    try {
        State.providerPrivateSignedUrlStatus = await getJson(
            `/handoff/export/download/provider-private-signed-url/status/${encodeURIComponent(receiptId)}`,
        );
        persistProviderPrivateReceiptSnapshot(State.providerPrivateSignedUrlStatus);
        addEvent('Provider-private signed URL status inspected with redacted state.');
        renderAll();
    } catch (error) {
        State.providerPrivateSignedUrlError = error.payload || { error_code: 'provider_private_signed_url_status_failed', message: error.message };
        addEvent(`Provider-private signed URL status blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPrivateSignedUrlPending = false;
        setBusy(elements.providerPrivateSignedUrlStatus, false, 'Inspect Provider-Private Status');
        setGateControls();
    }
}

async function revokeProviderPrivateSignedUrl() {
    if (!canRevokeProviderPrivateSignedUrl()) return;
    State.providerPrivateSignedUrlPending = true;
    State.providerPrivateSignedUrlError = null;
    renderAll();
    setBusy(elements.providerPrivateSignedUrlRevoke, true, 'Revoke Provider-Private Receipt');
    try {
        State.providerPrivateSignedUrlRevoke = await postJson(
            '/handoff/export/download/provider-private-signed-url/revoke',
            providerPrivateSignedUrlRevokePayload(),
        );
        persistProviderPrivateReceiptSnapshot(State.providerPrivateSignedUrlRevoke);
        addEvent('Provider-private signed URL receipt revoked.');
        renderAll();
    } catch (error) {
        State.providerPrivateSignedUrlError = error.payload || { error_code: 'provider_private_signed_url_revoke_failed', message: error.message };
        addEvent(`Provider-private signed URL revoke blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPrivateSignedUrlPending = false;
        setBusy(elements.providerPrivateSignedUrlRevoke, false, 'Revoke Provider-Private Receipt');
        setGateControls();
    }
}

async function submitProviderPublicUrlPrepare(event) {
    event.preventDefault();
    if (!canPrepareProviderPublicUrl()) return;
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    State.providerPublicUrlStatus = null;
    State.providerPublicUrlUse = null;
    State.providerPublicUrlRevoke = null;
    renderAll();
    setBusy(elements.providerPublicUrlPrepare, true, 'Prepare Provider-Public Receipt');
    try {
        State.providerPublicUrlPrepare = await postJson(
            '/handoff/export/download/provider-public-url/prepare',
            providerPublicUrlPreparePayload(),
        );
        State.providerPublicUrlPrepareClientRequestId = null;
        addEvent('Provider-public URL receipt prepared with redacted state only.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_prepare_failed', message: error.message };
        addEvent(`Provider-public URL prepare blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlPrepare, false, 'Prepare Provider-Public Receipt');
        setGateControls();
    }
}

async function inspectProviderPublicUrlStatus() {
    if (!canInspectProviderPublicUrl()) return;
    const receiptId = providerPublicUrlReceiptId();
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    renderAll();
    setBusy(elements.providerPublicUrlStatus, true, 'Inspect Provider-Public Status');
    try {
        State.providerPublicUrlStatus = await getJson(
            `/handoff/export/download/provider-public-url/status/${encodeURIComponent(receiptId)}`,
        );
        addEvent('Provider-public URL status inspected with redacted state only.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_status_failed', message: error.message };
        addEvent(`Provider-public URL status blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlStatus, false, 'Inspect Provider-Public Status');
        setGateControls();
    }
}

async function useProviderPublicUrlDecision() {
    if (!canUseProviderPublicUrl()) return;
    const payload = providerPublicUrlUsePayload();
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    State.providerPublicUrlStatus = null;
    renderAll();
    setBusy(elements.providerPublicUrlUse, true, 'Use Redacted Decision');
    try {
        State.providerPublicUrlUse = await postJson(
            '/handoff/export/download/provider-public-url/use',
            payload,
        );
        addEvent('Provider-public URL redacted use decision recorded without raw URL exposure.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_use_failed', message: error.message };
        addEvent(`Provider-public URL use decision blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlUse, false, 'Use Redacted Decision');
        setGateControls();
    }
}

async function revokeProviderPublicUrl() {
    if (!canRevokeProviderPublicUrl()) return;
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    renderAll();
    setBusy(elements.providerPublicUrlRevoke, true, 'Revoke Provider-Public Receipt');
    try {
        State.providerPublicUrlRevoke = await postJson(
            '/handoff/export/download/provider-public-url/revoke',
            providerPublicUrlRevokePayload(),
        );
        addEvent('Provider-public URL receipt revoked.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_revoke_failed', message: error.message };
        addEvent(`Provider-public URL revoke blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlRevoke, false, 'Revoke Provider-Public Receipt');
        setGateControls();
    }
}

async function loadDatasetVersionCandidates() {
    try {
        State.datasetVersionCandidates = await getJson('/dataset-version-candidates');
        State.datasetVersionCandidateError = null;
        addEvent(`Loaded ${State.datasetVersionCandidates.candidate_count || 0} APS-derived DatasetVersion candidate(s).`);
        return true;
    } catch (error) {
        State.datasetVersionCandidateError = error.message;
        addEvent(`DatasetVersion candidate lookup blocked: ${error.message}`);
        return false;
    }
}

async function loadApsContentDocumentCandidates() {
    try {
        State.apsContentDocumentCandidates = await getJson('/aps-content-document-candidates');
        State.apsContentDocumentCandidateError = null;
        addEvent(`Loaded ${State.apsContentDocumentCandidates.candidate_count || 0} APS content document candidate(s).`);
        return true;
    } catch (error) {
        State.apsContentDocumentCandidateError = error.message;
        addEvent(`APS content document lookup blocked: ${error.message}`);
        return false;
    }
}

async function init() {
    try {
        State.bootstrap = await getJson('/bootstrap');
        await loadDatasetVersionCandidates();
        await loadApsContentDocumentCandidates();
        const sessionRecovered = await recoverSessionFromStorage();
        if (!sessionRecovered) {
            restoreGateBDraftSnapshot();
        }
        restoreProviderPrivateReceiptSnapshot();
        renderUnavailable(State.bootstrap.unavailable_gate_labels);
        renderAuthority(State.bootstrap.authority_rail);
        renderContext();
        addEvent('Workbench bootstrap loaded.');
    } catch (error) {
        addEvent(`Bootstrap failed: ${error.message}`);
        renderUnavailable();
    }
    renderAll();
}

if (elements.themeSelector) {
    applyThemePreference(State.themePreference, { persist: false });
    elements.themeSelector.addEventListener('change', (event) => applyThemePreference(event.target.value));
}

if (systemThemeQuery) {
    systemThemeQuery.addEventListener('change', () => {
        if (State.themePreference === 'system') {
            applyThemePreference('system', { persist: false });
        }
    });
}

elements.stepChips.forEach((chip) => {
    chip.addEventListener('click', () => navigateToStep(chip));
});
elements.intentForm.addEventListener('submit', runPreflightFlow);
elements.intentInput.addEventListener('input', renderSublayerMap);
elements.sourceFieldset.addEventListener('change', (event) => {
    if (event.target?.name === 'source-class') {
        clearRawMixedMaterializationState({ clearAppliedSources: true });
    }
    renderSublayerMap();
    renderAll();
});
[
    elements.rawMixedCorpusBatchId,
    elements.rawMixedManifestRef,
    elements.rawMixedManifestHash,
].forEach((input) => {
    input.addEventListener('input', handleRawMixedMaterializationInputChange);
    input.addEventListener('keydown', preventRawMixedManifestEnterSubmit);
});
elements.rawMixedOperatorConfirmation.addEventListener('change', handleRawMixedMaterializationInputChange);
elements.rawMixedMaterialize.addEventListener('click', materializeRawMixedSources);
elements.datasetVersionIds.addEventListener('input', renderAll);
elements.datasetVersionCandidates.addEventListener('change', renderAll);
elements.apsContentDocumentIds.addEventListener('input', renderAll);
elements.apsContentDocumentCandidates.addEventListener('change', renderAll);
elements.gateBSubmit.addEventListener('click', commitGateB);
elements.gateCPreview.addEventListener('click', previewGateC);
elements.gateCCommit.addEventListener('click', commitGateC);
elements.planPreview.addEventListener('click', previewPlan);
elements.planReject.addEventListener('click', () => revisePlan('reject_current_preview'));
elements.planRequestRevision.addEventListener('click', () => revisePlan('request_revision'));
elements.planApprove.addEventListener('click', approvePlan);
elements.executionSelect.addEventListener('click', selectExecution);
elements.executionStart.addEventListener('click', startExecution);
elements.resultReviewRefresh.addEventListener('click', refreshSessionSummary);
elements.resultStatusInspect.addEventListener('click', inspectResultStatus);
elements.resultReviewForm.addEventListener('submit', submitResultReview);
elements.packageReviewPreviewInspect.addEventListener('click', inspectPackageReviewPreview);
elements.packageConstructionCommit.addEventListener('click', commitPackageConstruction);
elements.packageReviewSubmitForm.addEventListener('submit', submitPackageReview);
elements.packageSupersessionPreviewSubmit.addEventListener('click', submitPackageSupersessionPreview);
elements.sourceDirectoryPackageSupersessionPreviewSubmit.addEventListener('click', submitSourceDirectoryPackageSupersessionPreview);
elements.sourceDirectoryPackageSupersessionPreviewAuthority.addEventListener('input', () => {
    clearSourceDirectoryPackageSupersessionPreviewState();
    clearReplacementPackageSetAuthorityState();
    renderAll();
});
elements.replacementPackageSetAuthoritySubmit.addEventListener('click', submitReplacementPackageSetAuthority);
elements.packageSupersessionCommitSubmit.addEventListener('click', submitPackageSupersessionCommit);
elements.replacementPackageArtifactManifestSubmit.addEventListener('click', submitReplacementPackageArtifactManifest);
elements.replacementPackageNamespaceSubmit.addEventListener('click', submitReplacementPackageNamespace);
elements.handoffExportPrepareForm.addEventListener('submit', submitHandoffExportPrepare);
elements.apsHandoffDispatchForm.addEventListener('submit', submitApsHandoffDispatch);
elements.externalExportDownloadPrepareForm.addEventListener('submit', submitExternalExportDownloadPrepare);
elements.externalExportDownloadDeliveryForm.addEventListener('submit', submitExternalExportDownloadDelivery);
elements.sourceDirectoryHybridMiddleLifecycleForm.addEventListener('submit', submitSourceDirectoryHybridMiddleLifecycle);
elements.sourceDirectoryHybridMiddleLifecycleAuthority.addEventListener('input', () => {
    State.sourceDirectoryHybridMiddleLifecycle = null;
    State.sourceDirectoryHybridMiddleLifecycleError = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError = null;
    State.sourceDirectoryHybridExternalExportDownloadDelivery = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryError = null;
    State.sourceDirectoryHybridInternalWebhookDispatch = null;
    State.sourceDirectoryHybridInternalWebhookDispatchError = null;
    State.sourceDirectoryHybridInternalWebhookStatus = null;
    State.sourceDirectoryHybridInternalWebhookStatusError = null;
    elements.sourceDirectoryHybridExternalExportDownloadDeliveryAuthority.value = '';
    elements.sourceDirectoryHybridInternalWebhookAuthority.value = '';
    renderAll();
});
elements.sourceDirectoryHybridExternalExportDownloadDeliveryStatus.addEventListener('click', inspectSourceDirectoryHybridExternalExportDownloadDelivery);
elements.sourceDirectoryHybridExternalExportDownloadDeliveryForm.addEventListener('submit', submitSourceDirectoryHybridExternalExportDownloadDelivery);
elements.sourceDirectoryHybridExternalExportDownloadDeliveryAuthority.addEventListener('input', () => {
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError = null;
    State.sourceDirectoryHybridExternalExportDownloadDelivery = null;
    State.sourceDirectoryHybridExternalExportDownloadDeliveryError = null;
    renderAll();
});
elements.sourceDirectoryHybridInternalWebhookStatus.addEventListener('click', inspectSourceDirectoryHybridInternalWebhookStatus);
elements.sourceDirectoryHybridInternalWebhookForm.addEventListener('submit', submitSourceDirectoryHybridInternalWebhook);
elements.sourceDirectoryHybridInternalWebhookAuthority.addEventListener('input', () => {
    State.sourceDirectoryHybridInternalWebhookDispatch = null;
    State.sourceDirectoryHybridInternalWebhookDispatchError = null;
    State.sourceDirectoryHybridInternalWebhookStatus = null;
    State.sourceDirectoryHybridInternalWebhookStatusError = null;
    renderAll();
});
elements.externalExportDownloadSignedReferenceForm.addEventListener('submit', submitExternalExportDownloadSignedReference);
elements.externalExportDownloadSignedReferenceUse.addEventListener('click', useExternalExportDownloadSignedReference);
elements.providerPrivateSignedUrlForm.addEventListener('submit', submitProviderPrivateSignedUrlPrepare);
elements.providerPrivateSignedUrlStatus.addEventListener('click', inspectProviderPrivateSignedUrlStatus);
elements.providerPrivateSignedUrlRevoke.addEventListener('click', revokeProviderPrivateSignedUrl);
elements.providerPublicUrlForm.addEventListener('submit', submitProviderPublicUrlPrepare);
elements.providerPublicUrlStatus.addEventListener('click', inspectProviderPublicUrlStatus);
elements.providerPublicUrlUse.addEventListener('click', useProviderPublicUrlDecision);
elements.providerPublicUrlRevoke.addEventListener('click', revokeProviderPublicUrl);
elements.resultReviewDecision.addEventListener('change', setGateControls);
elements.resultReviewNotes.addEventListener('input', setGateControls);
elements.packageReviewSubmitDecision.addEventListener('change', setGateControls);
elements.packageReviewSubmitNotes.addEventListener('input', setGateControls);
elements.handoffExportPrepareDecision.addEventListener('change', setGateControls);
elements.handoffExportPrepareNotes.addEventListener('input', setGateControls);
elements.materialFilter.addEventListener('input', (event) => {
    State.materialFilter = event.target.value;
    renderMaterialLedger();
});
elements.materialLedgerBody.addEventListener('change', (event) => {
    const row = event.target.closest('tr[data-candidate-id]');
    if (row) {
        syncDecisionStateFromRow(row);
        renderSublayerMap();
    }
});
elements.materialLedgerBody.addEventListener('input', (event) => {
    const row = event.target.closest('tr[data-candidate-id]');
    if (row) {
        syncDecisionStateFromRow(row);
        renderSublayerMap();
    }
});

init();

(function sourceIntakeRenderedControls() {
    const sourceIntakeApiRoot = '/api/v1/layer3';
    const sourceIntakeState = {
        latestRecordId: null,
        pendingUpload: false,
        pendingGateB: false,
        latestPreview: null,
        gateBClientRequestId: null,
        committedPreviewId: null,
    };
    const byId = (id) => document.getElementById(id);
    const escapeSourceIntakeText = (value) => String(value ?? '').replace(/[&<>"]/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
    }[char]));

    function setSourceIntakeStatus(message, state = 'idle') {
        const status = byId('source-intake-status');
        if (!status) return;
        status.textContent = message;
        status.dataset.state = state;
        renderMockupQuerySourceSetupProjection();
    }

    function setSourceIntakeGateBStatus(message, state = 'idle') {
        const status = byId('source-intake-gate-b-status');
        if (!status) return;
        status.textContent = message;
        status.dataset.state = state;
        renderMockupQuerySourceSetupProjection();
    }

    async function sourceIntakeJson(response) {
        const text = await response.text();
        let body = null;
        if (text) {
            try {
                body = JSON.parse(text);
            } catch (error) {
                throw new Error(`Source intake API returned non-JSON response (${response.status}).`);
            }
        }
        if (!response.ok) {
            const message = body?.detail || body?.message || `Source intake API failed (${response.status}).`;
            throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
        }
        return body;
    }

    function sourceIntakeFreshnessIso(rawValue) {
        if (!rawValue) return '';
        const parsed = new Date(rawValue);
        return Number.isNaN(parsed.getTime()) ? rawValue : parsed.toISOString();
    }

    function sourceIntakeGateBDecisionBasis(candidate) {
        return {
            source_ref: candidate.source_ref,
            query_basis: candidate.query_basis,
            provenance_ref: candidate.provenance_ref,
            source_identity: candidate.source_identity,
            source_provenance: candidate.source_provenance,
            payload: candidate.payload,
            load_summary: candidate.load_summary,
        };
    }

    function sourceIntakeGateBPayload(preview) {
        const candidate = preview?.material_candidate;
        if (!candidate?.candidate_id || !preview?.material_preview_id || !preview?.material_preview_hash) {
            throw new Error('Source intake Gate B admission requires a complete server preview candidate.');
        }
        if (!sourceIntakeState.gateBClientRequestId) {
            sourceIntakeState.gateBClientRequestId = requestId();
        }
        return {
            schema_id: 'layer3.gate_b_decision_request.v1',
            client_request_id: sourceIntakeState.gateBClientRequestId,
            material_preview_id: preview.material_preview_id,
            material_preview_hash: preview.material_preview_hash,
            candidate_decisions: [
                {
                    candidate_id: candidate.candidate_id,
                    decision: 'approved',
                    operator_reason: 'Rendered source-intake Gate B admission from server preview.',
                    decision_basis: sourceIntakeGateBDecisionBasis(candidate),
                },
            ],
            commit_reason: 'source_intake_gate_b_rendered_admission',
            actor: 'operator',
        };
    }

    function renderSourceIntakeGateBAdmission(payload) {
        const candidate = payload.material_candidate || {};
        return `
            <div class="source-intake-gate-b-admission">
                <div>
                    <h4>Gate B admission candidate</h4>
                    <p>This control commits exactly the server-previewed source-intake material candidate through the existing Gate B API.</p>
                </div>
                <ul class="source-intake-proof-list">
                    <li><strong>candidate:</strong> ${escapeSourceIntakeText(candidate.candidate_id || 'missing')}</li>
                    <li><strong>preview:</strong> ${escapeSourceIntakeText(payload.material_preview_id || 'missing')}</li>
                    <li><strong>hash:</strong> ${escapeSourceIntakeText(payload.material_preview_hash || 'missing')}</li>
                </ul>
                <button class="primary-btn" id="source-intake-gate-b-submit" type="button">Commit Preview To Gate B</button>
            </div>`;
    }

    function renderSourceIntakeInventory(payload) {
        const list = byId('source-intake-inventory-list');
        if (!list) return;
        const records = Array.isArray(payload?.records) ? payload.records : [];
        if (!records.length) {
            list.textContent = 'No durable source-intake records returned.';
            renderMockupQuerySourceSetupProjection();
            return;
        }
        list.innerHTML = records.map((record) => {
            const recordId = record.source_intake_record_id || record.record_id || '';
            const label = record.source_label || record.original_filename || 'Unlabeled source';
            const mediaType = record.media_type || record.declared_media_type || record.detected_media_type || 'media type unavailable';
            const byteSize = record.content_size_bytes ?? record.byte_size ?? record.content_length ?? 'unknown';
            const createdAt = record.created_at || record.freshness_timestamp || 'timestamp unavailable';
            return `
                <article class="source-intake-inventory-item">
                    <div>
                        <strong>${escapeSourceIntakeText(label)}</strong>
                        <div class="source-intake-meta">
                            <span>${escapeSourceIntakeText(recordId)}</span>
                            <span>${escapeSourceIntakeText(mediaType)}</span>
                            <span>${escapeSourceIntakeText(byteSize)} bytes</span>
                            <span>${escapeSourceIntakeText(createdAt)}</span>
                        </div>
                    </div>
                    <button class="secondary-btn source-intake-preview-button" type="button" data-source-intake-record-id="${escapeSourceIntakeText(recordId)}">Preview</button>
                </article>
            `;
        }).join('');
        renderMockupQuerySourceSetupProjection();
    }

    async function refreshSourceIntakeInventory() {
        setSourceIntakeStatus('Refreshing durable source-intake inventory...', 'busy');
        const payload = await sourceIntakeJson(await fetch(`${sourceIntakeApiRoot}/source/intake/inventory?limit=10`));
        renderSourceIntakeInventory(payload);
        setSourceIntakeStatus('Inventory refreshed from server-authoritative records.', 'ok');
        return payload;
    }

    async function uploadSourceIntake(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const fileInput = byId('source-intake-file');
        if (!fileInput?.files?.length) {
            setSourceIntakeStatus('Select a file before upload.', 'error');
            return;
        }
        if (sourceIntakeState.pendingUpload) {
            setSourceIntakeStatus('Upload already in progress; wait for the current source-intake request to finish.', 'busy');
            return;
        }
        const submitButton = byId('source-intake-upload-submit');
        sourceIntakeState.pendingUpload = true;
        if (submitButton) submitButton.disabled = true;
        const formData = new FormData(form);
        try {
            if (!String(formData.get('client_request_id') || '').trim()) {
                formData.set('client_request_id', `source-intake-ui-${Date.now()}`);
            }
            const freshness = sourceIntakeFreshnessIso(formData.get('freshness_timestamp'));
            if (freshness) {
                formData.set('freshness_timestamp', freshness);
            } else {
                formData.delete('freshness_timestamp');
            }
            setSourceIntakeStatus('Uploading source intake through existing durable API...', 'busy');
            const payload = await sourceIntakeJson(await fetch(`${sourceIntakeApiRoot}/source/intake/upload`, {
                method: 'POST',
                body: formData,
            }));
            sourceIntakeState.latestRecordId = payload?.source_intake_record_id || null;
            setSourceIntakeStatus(`Source intake recorded: ${sourceIntakeState.latestRecordId || 'record id unavailable'}.`, 'ok');
            try {
                await refreshSourceIntakeInventory();
                setSourceIntakeStatus(`Source intake recorded: ${sourceIntakeState.latestRecordId || 'record id unavailable'}. Inventory refreshed.`, 'ok');
            } catch (refreshError) {
                setSourceIntakeStatus(`Source intake recorded: ${sourceIntakeState.latestRecordId || 'record id unavailable'}. Inventory refresh failed: ${refreshError.message}`, 'error');
            }
        } finally {
            sourceIntakeState.pendingUpload = false;
            if (submitButton) submitButton.disabled = false;
        }
    }

    async function previewSourceIntake(recordId) {
        const panel = byId('source-intake-preview-panel');
        if (!recordId || !panel) return;
        setSourceIntakeStatus('Requesting bounded server preview...', 'busy');
        const payload = await sourceIntakeJson(await fetch(`${sourceIntakeApiRoot}/source/intake/${encodeURIComponent(recordId)}/preview?max_chars=1000`));
        sourceIntakeState.latestPreview = payload;
        sourceIntakeState.gateBClientRequestId = null;
        const candidate = payload?.material_candidate || {};
        const previewText = candidate.preview_text || payload?.preview_text || payload?.text_preview || payload?.content_preview || '';
        panel.innerHTML = `
            <h3>Bounded text preview</h3>
            <div class="source-intake-meta">
                <span>${escapeSourceIntakeText(recordId)}</span>
                <span>${escapeSourceIntakeText(candidate.media_type || payload?.declared_media_type || payload?.detected_media_type || 'media type unavailable')}</span>
                <span>${escapeSourceIntakeText(candidate.preview_truncated || payload?.partial_retrieval ? 'truncated' : 'not truncated')}</span>
            </div>
            <pre class="source-intake-preview-text">${escapeSourceIntakeText(previewText || 'No preview text returned.')}</pre>
            ${renderSourceIntakeGateBAdmission(payload)}
        `;
        setSourceIntakeStatus('Bounded preview returned by existing source-intake API.', 'ok');
        setSourceIntakeGateBStatus('Gate B admission is ready for the server-previewed material candidate.', 'idle');
        renderMockupQuerySourceSetupProjection();
    }

    async function submitSourceIntakeGateB() {
        const preview = sourceIntakeState.latestPreview;
        if (!preview) {
            setSourceIntakeGateBStatus('Gate B admission requires an active source-intake preview.', 'error');
            return;
        }
        if (sourceIntakeState.pendingGateB) {
            setSourceIntakeGateBStatus('Gate B admission is already in progress.', 'busy');
            return;
        }
        if (State.gateB?.session_id && sourceIntakeState.committedPreviewId === preview.material_preview_id) {
            setSourceIntakeGateBStatus(`Gate B already committed session ${State.gateB.session_id} for this preview.`, 'ok');
            return;
        }
        const button = byId('source-intake-gate-b-submit');
        try {
            sourceIntakeState.pendingGateB = true;
            if (button) setBusy(button, true, 'Commit Preview To Gate B');
            setSourceIntakeGateBStatus('Committing server-previewed source-intake candidate to Gate B...', 'busy');
            State.gateB = await postJson('/gate-b/decision', sourceIntakeGateBPayload(preview));
            State.materialPreview = {
                schema_id: preview.schema_id,
                material_preview_id: preview.material_preview_id,
                material_preview_hash: preview.material_preview_hash,
                source_intake_record_id: preview.source_intake_record_id,
                material_candidates: [preview.material_candidate],
                partial_retrieval: preview.partial_retrieval || false,
            };
            State.gateC = null;
            State.planPreview = null;
            State.planApproval = null;
            State.planRevision = null;
            clearResultReviewState();
            persistSessionRecoveryAnchor('source_intake_gate_b_commit');
            sourceIntakeState.committedPreviewId = preview.material_preview_id;
            addEvent(`Source intake Gate B committed session ${State.gateB.session_id}.`);
            setSourceIntakeGateBStatus(`Gate B committed session ${State.gateB.session_id} from source-intake preview.`, 'ok');
            renderAll();
            setGateControls();
        } catch (error) {
            const detail = error.payload?.detail;
            const errorMessage = typeof detail === 'string' ? detail : detail?.message || error.message;
            const errorCodeValue = error.payload?.error_code || detail?.error_code || detail?.code;
            const errorCode = errorCodeValue ? ` (${errorCodeValue})` : '';
            setSourceIntakeGateBStatus(`Gate B admission blocked: ${errorMessage}${errorCode}`, 'error');
            addEvent(`Source intake Gate B blocked: ${errorMessage}${errorCode}`);
        } finally {
            sourceIntakeState.pendingGateB = false;
            if (button) setBusy(button, false, 'Commit Preview To Gate B');
        }
    }

    function bindSourceIntakeControls() {
        const panel = byId('source-intake-rendered-controls');
        if (!panel) return;
        const form = byId('source-intake-upload-form');
        const refresh = byId('source-intake-refresh');
        form?.addEventListener('submit', (event) => {
            uploadSourceIntake(event).catch((error) => setSourceIntakeStatus(error.message, 'error'));
        });
        refresh?.addEventListener('click', () => {
            refreshSourceIntakeInventory().catch((error) => setSourceIntakeStatus(error.message, 'error'));
        });
        panel.addEventListener('click', (event) => {
            const target = event.target instanceof Element ? event.target : null;
            const button = target?.closest('.source-intake-preview-button');
            const recordId = button?.getAttribute('data-source-intake-record-id');
            if (recordId) {
                previewSourceIntake(recordId).catch((error) => setSourceIntakeStatus(error.message, 'error'));
            }
            if (target?.closest('#source-intake-gate-b-submit')) {
                submitSourceIntakeGateB();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindSourceIntakeControls);
    } else {
        bindSourceIntakeControls();
    }
}());

(function sourceDirectoryIngestionRenderedControls() {
    const SOURCE_DIRECTORY_INGESTION_SCAN_PATH = '/source/ingestion/server-configured-directory/scan';
    const SOURCE_DIRECTORY_INGESTION_STATUS_PATH_PREFIX = '/source/ingestion/server-configured-directory/status/';
    const SOURCE_DIRECTORY_MATERIAL_PREVIEW_PATH = '/source/ingestion/server-configured-directory/material-preview';
    const SOURCE_DIRECTORY_INGESTION_SCHEMA_ID = 'layer3.source_directory_ingestion_batch.v1';
    const SOURCE_DIRECTORY_INGESTION_STATUS_SCHEMA_ID = 'layer3.source_directory_ingestion_status.v1';
    const SOURCE_DIRECTORY_MATERIAL_PREVIEW_SCHEMA_ID = 'layer3.source_directory_material_preview.v1';
    const SOURCE_DIRECTORY_MATERIAL_PREVIEW_MODE = 'source_directory_ingestion_gate_b_material_admission';
    const SOURCE_DIRECTORY_INGESTION_MODE = 'server_configured_operator_directory_text_table_ingestion';
    const SOURCE_DIRECTORY_INGESTION_SOURCE_FAMILY = 'server_configured_operator_directory_text_table_source_family';
    const SOURCE_DIRECTORY_INGESTION_CONFIG_AUTHORITY = 'LAYER3_SOURCE_INGESTION_DIR';
    const SOURCE_DIRECTORY_INGESTION_OPERATOR_DECISION = 'scan_server_configured_operator_directory';
    const state = {
        latestBatch: null,
        latestPreview: null,
        latestError: null,
        gateBClientRequestId: null,
        committedPreviewId: null,
        pending: false,
        pendingPreview: false,
        pendingGateB: false,
    };
    const byId = (id) => document.getElementById(id);
    const escapeDirectoryText = (value) => String(value ?? '').replace(/[&<>"]/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
    }[char]));

    function setDirectoryMessage(message, status = 'idle') {
        const element = byId('source-directory-ingestion-message');
        if (!element) return;
        element.textContent = message;
        element.dataset.state = status;
        renderMockupQuerySourceSetupProjection();
    }

    function directoryBatchId() {
        return byId('source-directory-ingestion-batch-id')?.value.trim() || state.latestBatch?.source_ingestion_batch_id || '';
    }

    function setDirectoryControls() {
        const scan = byId('source-directory-ingestion-scan-submit');
        const status = byId('source-directory-ingestion-status');
        const busy = state.pending || state.pendingPreview || state.pendingGateB;
        if (scan) scan.disabled = busy;
        if (status) status.disabled = busy || !directoryBatchId();
        document.querySelectorAll('.source-directory-material-preview-button').forEach((button) => {
            button.disabled = busy;
        });
        const gateB = byId('source-directory-gate-b-submit');
        if (gateB) gateB.disabled = busy || !state.latestPreview;
    }

    function sourceDirectoryIngestionPayload() {
        const input = byId('source-directory-ingestion-client-request-id');
        const clientRequestId = input?.value.trim() || `source-directory-ui-${requestId()}`;
        if (input && !input.value.trim()) {
            input.value = clientRequestId;
        }
        return {
            client_request_id: clientRequestId,
            operator_decision: SOURCE_DIRECTORY_INGESTION_OPERATOR_DECISION,
            source_family: SOURCE_DIRECTORY_INGESTION_SOURCE_FAMILY,
            ingestion_mode: SOURCE_DIRECTORY_INGESTION_MODE,
        };
    }

    function sourceDirectoryIngestionForbiddenPayloadTerms() {
        return [
            'path',
            'paths',
            'directory',
            'local_path',
            'url',
            'urls',
            'glob',
            'recursive',
            'file',
            'files',
            'file_bytes',
            'rag_vector_index',
            'web_connector',
            'package_payload',
            'provider_url',
            'public_url',
        ];
    }

    function renderDirectoryError(error) {
        if (!error) return '';
        const details = error.error || error.detail || error;
        const code = details.code || details.error_code || error.error_code || 'source_directory_ingestion_blocked';
        const message = details.message || error.message || 'Server blocked source-directory ingestion.';
        return `
            <section class="source-intake-card">
                <strong>Blocked</strong>
                <ul class="source-intake-proof-list">
                    <li><strong>code:</strong> ${escapeDirectoryText(code)}</li>
                    <li><strong>message:</strong> ${escapeDirectoryText(message)}</li>
                </ul>
            </section>`;
    }

    function renderDirectoryFiles(files) {
        if (!Array.isArray(files) || !files.length) {
            return '<li>No admitted server-configured files returned.</li>';
        }
        return files.map((file) => `
            <li>
                <strong>${escapeDirectoryText(file.relative_name || 'unnamed')}</strong>
                <span>${escapeDirectoryText(file.extension || '')}</span>
                <span>${escapeDirectoryText(file.media_type || '')}</span>
                <span>${escapeDirectoryText(file.content_size_bytes ?? 'unknown')} bytes</span>
                <code>${escapeDirectoryText(file.file_identity_hash || '')}</code>
                <button
                    class="secondary-btn source-directory-material-preview-button"
                    type="button"
                    data-source-ingestion-batch-id="${escapeDirectoryText(file.source_ingestion_batch_id || state.latestBatch?.source_ingestion_batch_id || '')}"
                    data-source-ingestion-file-id="${escapeDirectoryText(file.source_ingestion_file_id || '')}"
                    data-file-identity-hash="${escapeDirectoryText(file.file_identity_hash || '')}"
                    data-authority-basis-hash="${escapeDirectoryText(file.authority_basis_hash || '')}"
                >Preview For Gate B</button>
            </li>
        `).join('');
    }

    function sourceDirectoryMaterialPreviewPayload(file) {
        const batchId = file.source_ingestion_batch_id || state.latestBatch?.source_ingestion_batch_id || directoryBatchId();
        const fileId = file.source_ingestion_file_id;
        const fileIdentityHash = file.file_identity_hash;
        const authorityBasisHash = file.authority_basis_hash;
        if (!batchId || !fileId || !fileIdentityHash || !authorityBasisHash) {
            throw new Error('Source-directory material preview requires persisted file id and authority hashes.');
        }
        return {
            client_request_id: `source-directory-material-ui-${requestId()}`,
            source_ingestion_batch_id: batchId,
            source_ingestion_file_id: fileId,
            file_identity_hash: fileIdentityHash,
            authority_basis_hash: authorityBasisHash,
            max_chars: 1000,
        };
    }

    function sourceDirectoryGateBDecisionBasis(candidate) {
        return {
            source_ref: candidate.source_ref,
            query_basis: candidate.query_basis,
            provenance_ref: candidate.provenance_ref,
            source_identity: candidate.source_identity,
            source_provenance: candidate.source_provenance,
            payload: candidate.payload,
            load_summary: candidate.load_summary,
        };
    }

    function sourceDirectoryGateBPayload(preview) {
        const candidate = preview?.material_candidate;
        if (!candidate?.candidate_id || !preview?.material_preview_id || !preview?.material_preview_hash) {
            throw new Error('Source-directory Gate B admission requires a complete server material preview.');
        }
        if (!state.gateBClientRequestId) {
            state.gateBClientRequestId = `source-directory-gate-b-ui-${requestId()}`;
        }
        return {
            schema_id: 'layer3.gate_b_decision_request.v1',
            client_request_id: state.gateBClientRequestId,
            preflight_id: `source-directory-rendered-${preview.source_ingestion_batch_id || 'batch'}`,
            source_set_id: preview.source_ingestion_batch_id,
            material_preview_id: preview.material_preview_id,
            material_preview_hash: preview.material_preview_hash,
            actor: 'operator',
            candidate_decisions: [
                {
                    candidate_id: candidate.candidate_id,
                    decision: 'approved',
                    operator_reason: 'Rendered source-directory Gate B admission from server material preview.',
                    decision_basis: sourceDirectoryGateBDecisionBasis(candidate),
                },
            ],
            commit_reason: 'source_directory_gate_b_rendered_admission',
        };
    }

    function renderDirectoryMaterialPreview(preview = state.latestPreview) {
        if (!preview) return '';
        const candidate = preview.material_candidate || {};
        return `
            <section class="source-intake-card source-directory-material-preview">
                <h4>Gate B Material Preview</h4>
                <div class="source-intake-meta">
                    <span>${escapeDirectoryText(preview.schema_id || SOURCE_DIRECTORY_MATERIAL_PREVIEW_SCHEMA_ID)}</span>
                    <span>${escapeDirectoryText(preview.mode || SOURCE_DIRECTORY_MATERIAL_PREVIEW_MODE)}</span>
                    <span>${escapeDirectoryText(preview.status || 'status unavailable')}</span>
                </div>
                <pre class="source-intake-preview-text">${escapeDirectoryText(candidate.preview_text || 'No preview text returned.')}</pre>
                <ul class="source-intake-proof-list">
                    <li><strong>candidate:</strong> ${escapeDirectoryText(candidate.candidate_id || 'missing')}</li>
                    <li><strong>preview:</strong> ${escapeDirectoryText(preview.material_preview_id || 'missing')}</li>
                    <li><strong>hash:</strong> ${escapeDirectoryText(preview.material_preview_hash || 'missing')}</li>
                    <li><strong>source class:</strong> ${escapeDirectoryText(candidate.source_class || 'missing')}</li>
                    <li><strong>raw path exposed:</strong> ${escapeDirectoryText(preview.source_gate?.absolute_path_exposed === false ? 'blocked' : preview.source_gate?.absolute_path_exposed)}</li>
                    <li><strong>RAG/vector:</strong> ${escapeDirectoryText(preview.source_gate?.rag_vector_index_enabled === false ? 'blocked' : preview.source_gate?.rag_vector_index_enabled)}</li>
                    <li><strong>package construction:</strong> ${escapeDirectoryText(preview.source_gate?.package_construction_enabled === false ? 'blocked' : preview.source_gate?.package_construction_enabled)}</li>
                </ul>
                <button class="primary-btn" id="source-directory-gate-b-submit" type="button">Commit Directory File To Gate B</button>
            </section>
        `;
    }

    function directoryAuthorityStatus(payload) {
        const status = payload.status || 'status unavailable';
        if (status === 'already_recorded') {
            return 'already_recorded: idempotent replay of existing server authority';
        }
        if (status === 'recorded') {
            return 'recorded: server authority captured';
        }
        return status;
    }

    function renderDirectoryPanel(payload = state.latestBatch) {
        const panel = byId('source-directory-ingestion-panel');
        if (!panel) return;
        if (state.latestError) {
            panel.innerHTML = renderDirectoryError(state.latestError);
            renderMockupQuerySourceSetupProjection();
            return;
        }
        if (!payload) {
            panel.innerHTML = `
                <h3>Directory authority</h3>
                <p class="muted">No server-configured directory batch has been inspected.</p>
            `;
            renderMockupQuerySourceSetupProjection();
            return;
        }
        const invariants = payload.negative_invariants || {};
        const schemaId = payload.schema_id
            || (payload.mode === `${SOURCE_DIRECTORY_INGESTION_MODE}_status`
                ? SOURCE_DIRECTORY_INGESTION_STATUS_SCHEMA_ID
                : SOURCE_DIRECTORY_INGESTION_SCHEMA_ID);
        panel.innerHTML = `
            <h3>Directory authority</h3>
            <div class="source-intake-meta">
                <span>${escapeDirectoryText(schemaId)}</span>
                <span>${escapeDirectoryText(directoryAuthorityStatus(payload))}</span>
                <span>${escapeDirectoryText(payload.source_ingestion_batch_id || 'batch unavailable')}</span>
            </div>
            <ul class="source-intake-proof-list">
                <li><strong>response schema:</strong> ${escapeDirectoryText(schemaId)}</li>
                <li><strong>response status:</strong> ${escapeDirectoryText(payload.status || 'status unavailable')}</li>
                <li><strong>idempotency:</strong> ${escapeDirectoryText(payload.status === 'already_recorded' ? 'server replay accepted' : 'server authority basis recorded')}</li>
                <li><strong>source family:</strong> ${escapeDirectoryText(payload.source_family || SOURCE_DIRECTORY_INGESTION_SOURCE_FAMILY)}</li>
                <li><strong>mode:</strong> ${escapeDirectoryText(payload.ingestion_mode || SOURCE_DIRECTORY_INGESTION_MODE)}</li>
                <li><strong>runtime policy:</strong> ${escapeDirectoryText(payload.runtime_policy_id || 'policy unavailable')}</li>
                <li><strong>config authority:</strong> ${escapeDirectoryText(payload.config_authority || SOURCE_DIRECTORY_INGESTION_CONFIG_AUTHORITY)}</li>
                <li><strong>root ref:</strong> ${escapeDirectoryText(payload.source_root_ref || 'redacted')}</li>
                <li><strong>raw path exposed:</strong> ${escapeDirectoryText(payload.source_root_absolute_path_exposed === false ? 'blocked' : payload.source_root_absolute_path_exposed)}</li>
                <li><strong>direct child only:</strong> ${escapeDirectoryText(payload.direct_child_only)}</li>
                <li><strong>recursive traversal admitted:</strong> ${escapeDirectoryText(payload.recursive_traversal_admitted)}</li>
                <li><strong>max recursion depth:</strong> ${escapeDirectoryText(payload.max_recursion_depth ?? 'unavailable')}</li>
                <li><strong>max relative path segments:</strong> ${escapeDirectoryText(payload.max_relative_path_segments ?? 'unavailable')}</li>
                <li><strong>caller recursive flag:</strong> ${escapeDirectoryText(payload.caller_selected_recursive_flag_allowed === false ? 'blocked' : payload.caller_selected_recursive_flag_allowed)}</li>
                <li><strong>allowed extensions:</strong> ${escapeDirectoryText((payload.allowed_extensions || []).join(', '))}</li>
                <li><strong>eligible files:</strong> ${escapeDirectoryText(payload.eligible_file_count ?? 0)}</li>
            </ul>
            <h4>Admitted Files</h4>
            <ul class="source-intake-proof-list">${renderDirectoryFiles(payload.files)}</ul>
            ${renderDirectoryMaterialPreview()}
            <h4>Blocked Runtime</h4>
            <div class="downstream-locks">${renderDownstreamLocks([
                'caller_supplied_path',
                'caller_selected_recursive_flag',
                'browser_file_bytes',
                'web_connector',
                'rag_vector_index',
                'package_construction',
                'connector_dispatch',
                'provider_public_delivery',
                'frontend_durable_authority',
            ])}</div>
            <ul class="source-intake-proof-list">
                <li><strong>recursive traversal:</strong> ${escapeDirectoryText(invariants.recursive_traversal_enabled === false ? 'blocked' : invariants.recursive_traversal_enabled)}</li>
                <li><strong>caller recursive flag:</strong> ${escapeDirectoryText(invariants.caller_selected_recursive_flag_enabled === false ? 'blocked' : invariants.caller_selected_recursive_flag_enabled)}</li>
                <li><strong>RAG/vector index:</strong> ${escapeDirectoryText(invariants.rag_vector_index_enabled === false ? 'blocked' : invariants.rag_vector_index_enabled)}</li>
                <li><strong>package construction:</strong> ${escapeDirectoryText(invariants.package_construction_enabled === false ? 'blocked' : invariants.package_construction_enabled)}</li>
                <li><strong>connector dispatch:</strong> ${escapeDirectoryText(invariants.connector_dispatch_enabled === false ? 'blocked' : invariants.connector_dispatch_enabled)}</li>
            </ul>
        `;
        renderMockupQuerySourceSetupProjection();
        setDirectoryControls();
    }

    async function previewSourceDirectoryFile(file) {
        if (state.pendingPreview || state.pendingGateB) return;
        state.pendingPreview = true;
        state.latestError = null;
        state.latestPreview = null;
        state.gateBClientRequestId = null;
        setDirectoryControls();
        setDirectoryMessage('Requesting bounded source-directory material preview...', 'busy');
        try {
            const payload = await postJson(SOURCE_DIRECTORY_MATERIAL_PREVIEW_PATH, sourceDirectoryMaterialPreviewPayload(file));
            state.latestPreview = payload;
            renderDirectoryPanel();
            setDirectoryMessage('Source-directory material preview returned by server authority.', 'ok');
            addEvent('Source-directory material preview loaded for Gate B admission.');
        } catch (error) {
            state.latestError = error.payload || {
                error_code: 'source_directory_material_preview_request_failed',
                message: error.message,
            };
            renderDirectoryPanel();
            setDirectoryMessage(`Directory material preview blocked: ${error.message}`, 'error');
            addEvent(`Source-directory material preview blocked: ${error.message}`);
        } finally {
            state.pendingPreview = false;
            setDirectoryControls();
        }
    }

    async function submitSourceDirectoryGateB() {
        const preview = state.latestPreview;
        if (!preview || state.pendingGateB) return;
        if (State.gateB?.session_id && state.committedPreviewId === preview.material_preview_id) {
            setDirectoryMessage(`Gate B already committed session ${State.gateB.session_id} for this source-directory preview.`, 'ok');
            return;
        }
        const button = byId('source-directory-gate-b-submit');
        try {
            state.pendingGateB = true;
            if (button) setBusy(button, true, 'Commit Directory File To Gate B');
            setDirectoryControls();
            setDirectoryMessage('Committing source-directory material preview to Gate B...', 'busy');
            State.gateB = await postJson('/gate-b/decision', sourceDirectoryGateBPayload(preview));
            State.materialPreview = {
                schema_id: preview.schema_id,
                material_preview_id: preview.material_preview_id,
                material_preview_hash: preview.material_preview_hash,
                source_ingestion_batch_id: preview.source_ingestion_batch_id,
                source_ingestion_file_id: preview.source_ingestion_file_id,
                material_candidates: [preview.material_candidate],
                partial_retrieval: preview.partial_retrieval || false,
            };
            State.gateC = null;
            State.planPreview = null;
            State.planApproval = null;
            State.planRevision = null;
            clearResultReviewState();
            persistSessionRecoveryAnchor('source_directory_gate_b_commit');
            state.committedPreviewId = preview.material_preview_id;
            addEvent(`Source-directory Gate B committed session ${State.gateB.session_id}.`);
            setDirectoryMessage(`Gate B committed session ${State.gateB.session_id} from source-directory material preview.`, 'ok');
            renderAll();
            setGateControls();
        } catch (error) {
            const detail = error.payload?.detail;
            const errorMessage = typeof detail === 'string' ? detail : detail?.message || error.message;
            const errorCodeValue = error.payload?.error_code || detail?.error_code || detail?.code;
            const errorCode = errorCodeValue ? ` (${errorCodeValue})` : '';
            setDirectoryMessage(`Directory Gate B admission blocked: ${errorMessage}${errorCode}`, 'error');
            addEvent(`Source-directory Gate B blocked: ${errorMessage}${errorCode}`);
        } finally {
            state.pendingGateB = false;
            if (button) setBusy(button, false, 'Commit Directory File To Gate B');
            setDirectoryControls();
        }
    }

    async function scanSourceDirectory(event) {
        event.preventDefault();
        if (state.pending) return;
        state.pending = true;
        state.latestError = null;
        state.latestPreview = null;
        state.gateBClientRequestId = null;
        setDirectoryControls();
        setDirectoryMessage('Scanning server-configured source directory...', 'busy');
        try {
            const payload = await postJson(SOURCE_DIRECTORY_INGESTION_SCAN_PATH, sourceDirectoryIngestionPayload());
            state.latestBatch = payload;
            const batchInput = byId('source-directory-ingestion-batch-id');
            if (batchInput && payload.source_ingestion_batch_id) {
                batchInput.value = payload.source_ingestion_batch_id;
            }
            renderDirectoryPanel(payload);
            setDirectoryMessage(`Directory batch recorded: ${payload.source_ingestion_batch_id || 'batch id unavailable'}.`, 'ok');
            addEvent('Source-directory ingestion scan recorded from server-configured authority.');
        } catch (error) {
            state.latestBatch = null;
            state.latestError = error.payload || {
                error_code: 'source_directory_ingestion_scan_request_failed',
                message: error.message,
            };
            renderDirectoryPanel();
            setDirectoryMessage(`Directory scan blocked: ${error.message}`, 'error');
            addEvent(`Source-directory ingestion scan blocked: ${error.message}`);
        } finally {
            state.pending = false;
            setDirectoryControls();
        }
    }

    async function inspectSourceDirectoryBatch() {
        const batchId = directoryBatchId();
        if (!batchId || state.pending) return;
        state.pending = true;
        state.latestError = null;
        state.latestPreview = null;
        state.gateBClientRequestId = null;
        setDirectoryControls();
        setDirectoryMessage('Inspecting server-recorded source-directory batch...', 'busy');
        try {
            const payload = await getJson(`${SOURCE_DIRECTORY_INGESTION_STATUS_PATH_PREFIX}${encodeURIComponent(batchId)}`);
            state.latestBatch = payload;
            renderDirectoryPanel(payload);
            setDirectoryMessage(`Directory batch status loaded: ${payload.source_ingestion_batch_id || batchId}.`, 'ok');
            addEvent('Source-directory ingestion status loaded from server authority.');
        } catch (error) {
            state.latestError = error.payload || {
                error_code: 'source_directory_ingestion_status_request_failed',
                message: error.message,
            };
            renderDirectoryPanel();
            setDirectoryMessage(`Directory status blocked: ${error.message}`, 'error');
            addEvent(`Source-directory ingestion status blocked: ${error.message}`);
        } finally {
            state.pending = false;
            setDirectoryControls();
        }
    }

    function bindSourceDirectoryIngestionControls() {
        const form = byId('source-directory-ingestion-scan-form');
        const status = byId('source-directory-ingestion-status');
        const batchId = byId('source-directory-ingestion-batch-id');
        const panel = byId('source-directory-ingestion-panel');
        if (!form) return;
        form.addEventListener('submit', (event) => {
            scanSourceDirectory(event);
        });
        status?.addEventListener('click', () => {
            inspectSourceDirectoryBatch();
        });
        batchId?.addEventListener('input', setDirectoryControls);
        panel?.addEventListener('click', (event) => {
            const target = event.target instanceof Element ? event.target : null;
            const previewButton = target?.closest('.source-directory-material-preview-button');
            if (previewButton) {
                previewSourceDirectoryFile({
                    source_ingestion_batch_id: previewButton.getAttribute('data-source-ingestion-batch-id'),
                    source_ingestion_file_id: previewButton.getAttribute('data-source-ingestion-file-id'),
                    file_identity_hash: previewButton.getAttribute('data-file-identity-hash'),
                    authority_basis_hash: previewButton.getAttribute('data-authority-basis-hash'),
                });
            }
            if (target?.closest('#source-directory-gate-b-submit')) {
                submitSourceDirectoryGateB();
            }
        });
        setDirectoryControls();
        sourceDirectoryIngestionForbiddenPayloadTerms();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindSourceDirectoryIngestionControls);
    } else {
        bindSourceDirectoryIngestionControls();
    }
}());
