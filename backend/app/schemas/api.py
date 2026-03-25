from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileRequest(BaseModel):
    detect_seasonality: bool = True
    detect_stationarity: bool = False


class TransformationStepIn(BaseModel):
    variable_name: str
    method_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class TransformationApplyRequest(BaseModel):
    version_label: str | None = None
    rationale: str | None = None
    steps: list[TransformationStepIn]


class AnnotationWindowIn(BaseModel):
    label: str
    annotation_type: str
    start_time: str
    end_time: str
    notes: str | None = None


class AnalysisRecommendationRequest(BaseModel):
    goal_type: str | None = None


class AnalysisRunIn(BaseModel):
    dataset_version_id: str
    method_name: str
    goal_type: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    annotation_window_id: str | None = None


class UploadResponse(BaseModel):
    dataset_id: str
    dataset_version_id: str
    dataset_name: str
    row_count: int
    time_column: str | None = None
    numeric_variables: list[str]


class DatasetVersionOut(BaseModel):
    dataset_version_id: str
    version_label: str
    version_type: str
    row_count: int


class DatasetOut(BaseModel):
    dataset_id: str
    name: str
    description: str | None = None
    time_column: str | None = None
    frequency_hint: str | None = None


class DatasetDetailOut(DatasetOut):
    versions: list[DatasetVersionOut]


class VariableProfileOut(BaseModel):
    variable_profile_id: str
    variable_id: str
    missingness_rate: float | None = None
    mean_value: float | None = None
    median_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    std_dev: float | None = None
    skewness: float | None = None
    outlier_fraction: float | None = None
    negative_values_flag: bool
    zero_values_flag: bool
    bounded_flag: bool
    seasonality_flag: bool | None = None
    stationarity_hint: str | None = None
    summary_json: dict[str, Any] = Field(default_factory=dict)


class TransformRecommendationOut(BaseModel):
    variable_name: str
    recommended_method: str
    rationale: str
    alternatives: list[str]
    warnings: list[str] = Field(default_factory=list)


class TransformationApplyOut(BaseModel):
    transformation_run_id: str
    output_dataset_version_id: str
    version_label: str
    transformed_variables: list[str]


class AnnotationWindowOut(BaseModel):
    annotation_window_id: str
    label: str
    annotation_type: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None


class AnalysisRecommendationOut(BaseModel):
    dataset_version_id: str
    recommended_sequence: list[str]
    rationale: str
    profile_context: dict[str, Any] = Field(default_factory=dict)


class AnalysisArtifactOut(BaseModel):
    artifact_id: str
    artifact_type: str
    title: str
    storage_ref: str
    summary: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AssumptionCheckOut(BaseModel):
    assumption_check_id: str
    assumption_name: str
    check_result: str
    severity: str
    notes: str | None = None


class CaveatOut(BaseModel):
    caveat_note_id: str
    caveat_type: str
    severity: str
    message: str


class AnalysisRunOut(BaseModel):
    analysis_run_id: str
    dataset_version_id: str
    method_name: str
    goal_type: str | None = None
    status: str
    route_reason: str | None = None
    parameters_json: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[AnalysisArtifactOut] = Field(default_factory=list)
    assumptions: list[AssumptionCheckOut] = Field(default_factory=list)
    caveats: list[CaveatOut] = Field(default_factory=list)


class ScienceBaseConnectorRunIn(BaseModel):
    q: str = "Mineral Commodity Summaries"
    filters: list[str] = Field(default_factory=list)
    sort: str = "title"
    order: str = "asc"
    scope_mode: Literal["keyword_search", "folder_children", "folder_descendants", "explicit_item_ids", "explicit_dois"] = "keyword_search"
    scope_values: list[str] = Field(default_factory=list)
    page_size: int = 100
    max_items: int = 0
    max_files: int = 0
    seed: int = 0
    selection_mode: str = "first_n"
    run_mode: Literal["one_shot_import", "recurring_sync", "dry_run"] = "one_shot_import"
    surface_policy: Literal["files_only", "files_and_distribution", "all_supported"] = "files_only"
    external_fetch_policy: Literal["sciencebase_only", "allowlisted_external", "all_https_denied_by_default"] = "sciencebase_only"
    reconciliation_enabled: bool = False
    resume_behavior: Literal["resume_if_exists", "fail_if_running", "force_new_run"] = "resume_if_exists"
    partition_strategy: Literal["none", "auto_date_split", "configured_slices"] = "none"
    configured_slices: list[dict[str, Any]] = Field(default_factory=list)
    ordering_strategy: Literal["item_id", "doi_then_item_id", "explicit_sort"] = "item_id"
    checkpoint_frequency: Literal["per_page", "per_target", "per_stage"] = "per_target"
    artifact_dedup_policy: Literal["by_checksum", "by_resolved_url", "by_name_plus_surface"] = "by_checksum"
    report_verbosity: Literal["summary", "standard", "debug"] = "standard"
    conditional_request_policy: Literal["etag_then_last_modified", "etag_only", "last_modified_only"] = "etag_then_last_modified"
    allowed_extensions: list[str] = Field(default_factory=lambda: [".csv"])
    allow_distribution_links: bool = False
    allow_web_links: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    fetch_policy_mode: str = "strict_public_safe"
    max_file_bytes: int = 64 * 1024 * 1024
    max_run_bytes: int = 512 * 1024 * 1024
    max_concurrent_downloads_per_run: int = 1
    per_host_fetch_limit: int = 2
    request_timeout_seconds: int = 30
    domain_pack: str = "macro_energy_commodities"
    primary_time_column: str | None = None
    client_request_id: str | None = None
    detect_seasonality: bool = True
    detect_stationarity: bool = True


class ScienceBaseMcsConnectorRunIn(ScienceBaseConnectorRunIn):
    years: list[int] = Field(default_factory=list)
    mcs_release_mode: Literal["annual_release", "commodity_sheet_release"] = "annual_release"
    commodity_keywords: list[str] = Field(default_factory=list)


class NrcAdamsApsConnectorRunIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: Literal["strict_builder", "lenient_pass_through"] = "strict_builder"
    wire_shape_mode: Literal["auto_probe", "guide_native", "shape_a", "shape_b", "draft_shape_a"] = "auto_probe"
    query_payload: dict[str, Any] = Field(default_factory=dict)
    q: str | None = None
    queryString: str | None = None
    filters: list[dict[str, Any]] = Field(default_factory=list)
    anyFilters: list[dict[str, Any]] = Field(default_factory=list)
    docketNumber: str | None = None
    run_mode: Literal["metadata_only", "dry_run"] = "metadata_only"
    page_size: int = 100
    max_items: int = 0
    include_document_details: bool = True
    artifact_pipeline_mode: Literal["off", "download_only", "hydrate_process"] = "download_only"
    artifact_required_for_target_success: bool | None = None
    download_artifacts: bool = True
    probe_artifact_auth: bool = True
    allowed_hosts: list[str] = Field(default_factory=list)
    fetch_policy_mode: str = "strict_public_safe"
    max_file_bytes: int = 64 * 1024 * 1024
    max_run_bytes: int = 512 * 1024 * 1024
    request_timeout_seconds: int = 30
    connect_timeout_seconds: int = 10
    read_timeout_seconds: int = 30
    overall_deadline_seconds: int = 120
    limiter_max_wait_seconds: float = 10.0
    limiter_queue_poll_seconds: float = 0.05
    runtime_process_count: int = 1
    unsafe_allow_multi_process_limiter: bool = False
    retry_max_attempts_per_request: int = 4
    retry_max_attempts_per_scope: int = 8
    retry_max_attempts_per_run: int = 300
    retry_max_cumulative_sleep_seconds: float = 20.0
    retry_base_backoff_seconds: float = 0.4
    retry_max_backoff_seconds: float = 3.0
    retry_jitter_mode: Literal["none", "full"] = "none"
    retry_respect_retry_after: bool = True
    max_redirects: int = 3
    content_sniff_bytes: int = 4096
    content_parse_max_pages: int = 500
    content_parse_timeout_seconds: int = 30
    ocr_enabled: bool = True
    ocr_max_pages: int = 50
    ocr_render_dpi: int = 300
    ocr_language: str = "eng"
    ocr_timeout_seconds: int = 120
    content_min_searchable_chars: int = 200
    content_min_searchable_tokens: int = 30
    content_chunk_size_chars: int = 1000
    content_chunk_overlap_chars: int = 200
    content_chunk_min_chars: int = 50
    sync_mode: Literal["full_scan", "incremental", "reconciliation"] = "full_scan"
    incremental_overlap_seconds: int = 259200
    reconciliation_lookback_days: int = 30
    max_rps: float = 5.0
    allow_known_bad_dialect: bool = False
    report_verbosity: Literal["summary", "standard", "debug"] = "standard"
    safeguard_policy: dict[str, Any] = Field(default_factory=dict)
    client_request_id: str | None = None


class SenateLdaConnectorRunIn(BaseModel):
    filing_uuid: str | None = None
    filing_year: int | None = None
    filing_period: str | None = None
    filing_type: str | None = None
    registrant_name: str | None = None
    client_name: str | None = None
    lobbyist_name: str | None = None
    filing_specific_lobbying_issues: str | None = None
    filing_dt_posted_after: str | None = None
    filing_dt_posted_before: str | None = None
    ordering: str = "-dt_posted"
    page_size: int = 25
    max_items: int = 0
    run_mode: Literal["metadata_only", "dry_run"] = "metadata_only"
    include_filing_detail: bool = False
    request_timeout_seconds: int = 30
    retry_max_attempts_per_request: int = 4
    retry_base_backoff_seconds: float = 0.4
    retry_max_backoff_seconds: float = 3.0
    retry_respect_retry_after: bool = True
    max_rps: float = 2.0
    report_verbosity: Literal["summary", "standard", "debug"] = "standard"
    client_request_id: str | None = None


class ConnectorRunSubmitOut(BaseModel):
    connector_run_id: str
    status: str
    created: bool
    submitted_at: datetime
    poll_url: str
    submission_idempotency_key: str | None = None
    request_fingerprint: str | None = None


class ConnectorRunTargetOut(BaseModel):
    connector_run_target_id: str
    ordinal: int
    sciencebase_item_id: str | None = None
    sciencebase_file_name: str | None = None
    artifact_surface: str
    selection_source: str | None = None
    selection_scope: str | None = None
    selection_match_basis: str | None = None
    artifact_locator_type: str | None = None
    stable_release_key: str | None = None
    status: str
    error_stage: str | None = None
    error_message: str | None = None
    last_error_class: str | None = None
    last_error_message: str | None = None
    retry_eligible: bool
    attempt_count: int
    operator_reason_code: str | None = None
    last_stage_transition_at: datetime | None = None
    dataset_id: str | None = None
    dataset_version_id: str | None = None
    source_artifact_key: str | None = None
    canonical_artifact_key: str | None = None
    blocked_reason: str | None = None
    redirect_count: int | None = None
    access_level_summary: str | None = None
    public_read_confirmed: bool = False


class ConnectorRunOut(BaseModel):
    connector_run_id: str
    connector_key: str
    source_system: str
    source_mode: str
    status: str
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    run_mode: str = "one_shot_import"
    search_exhaustion_reason: str | None = None
    submission_idempotency_key: str | None = None
    request_fingerprint: str | None = None
    source_query_fingerprint: str | None = None
    effective_search_envelope: dict[str, Any] = Field(default_factory=dict)
    page_count_completed: int = 0
    partition_count_completed: int = 0
    next_page_available: bool = False
    last_offset_committed: int | None = None
    collapsed_duplicate_count: int
    deduped_within_run_count: int = 0
    blocked_by_fetch_policy_count: int
    not_modified_count: int = 0
    reconciliation_only_count: int = 0
    budget_blocked_count: int = 0
    policy_skipped_count_by_reason_json: dict[str, int] = Field(default_factory=dict)
    discovered_count: int
    selected_count: int
    ignored_count: int
    skipped_unchanged_count: int
    downloaded_count: int
    ingested_count: int
    profiled_count: int
    recommended_count: int
    failed_count: int
    error_summary: str | None = None
    lease_state: dict[str, Any] = Field(default_factory=dict)
    checkpoint_summary: dict[str, Any] = Field(default_factory=dict)
    cancellation_state: dict[str, Any] = Field(default_factory=dict)
    resume_eligibility: bool = False
    retryable_target_count: int = 0
    terminal_target_count: int = 0
    nonterminal_target_count: int = 0
    current_phase: str = "planning"
    artifact_surface_counts: dict[str, int] = Field(default_factory=dict)
    partition_progress: dict[str, Any] = Field(default_factory=dict)
    throughput_summary: dict[str, Any] = Field(default_factory=dict)
    reconciliation_summary: dict[str, Any] = Field(default_factory=dict)
    budget_summary: dict[str, Any] = Field(default_factory=dict)
    fetch_policy_summary: dict[str, Any] = Field(default_factory=dict)
    dedupe_summary: dict[str, Any] = Field(default_factory=dict)
    report_refs: dict[str, Any] = Field(default_factory=dict)
    manifest_refs: dict[str, Any] = Field(default_factory=dict)


class ConnectorRunTargetsPageOut(BaseModel):
    connector_run_id: str
    total: int
    limit: int
    offset: int
    targets: list[ConnectorRunTargetOut] = Field(default_factory=list)


class ConnectorRunEventOut(BaseModel):
    connector_run_event_id: str
    connector_run_id: str
    connector_run_target_id: str | None = None
    phase: str | None = None
    stage: str | None = None
    event_type: str
    status_before: str | None = None
    status_after: str | None = None
    reason_code: str | None = None
    error_class: str | None = None
    message: str | None = None
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConnectorRunEventsPageOut(BaseModel):
    connector_run_id: str
    total: int
    limit: int
    offset: int
    events: list[ConnectorRunEventOut] = Field(default_factory=list)


class ConnectorRunReportsOut(BaseModel):
    connector_run_id: str
    reports: dict[str, str] = Field(default_factory=dict)
    report_status: dict[str, bool] = Field(default_factory=dict)


class ConnectorRunContentUnitOut(BaseModel):
    content_id: str
    chunk_id: str
    content_contract_id: str
    chunking_contract_id: str
    chunk_ordinal: int
    start_char: int
    end_char: int
    chunk_text: str
    chunk_text_sha256: str
    page_start: int | None = None
    page_end: int | None = None
    unit_kind: str | None = None
    quality_status: str | None = None
    run_id: str
    target_id: str
    accession_number: str | None = None
    content_units_ref: str | None = None
    normalized_text_ref: str | None = None
    diagnostics_ref: str | None = None
    blob_ref: str | None = None
    download_exchange_ref: str | None = None
    discovery_ref: str | None = None
    selection_ref: str | None = None
    normalized_text_sha256: str | None = None
    blob_sha256: str | None = None
    effective_content_type: str | None = None
    document_class: str | None = None
    page_count: int = 0
    visual_page_refs: list[dict[str, Any]] = Field(default_factory=list)


class ConnectorRunContentUnitsPageOut(BaseModel):
    connector_run_id: str
    total: int
    limit: int
    offset: int
    items: list[ConnectorRunContentUnitOut] = Field(default_factory=list)


class NrcApsContentSearchIn(BaseModel):
    query: str
    run_id: str | None = None
    limit: int = 20
    offset: int = 0


class NrcApsContentSearchResultOut(ConnectorRunContentUnitOut):
    matched_unique_query_terms: int
    summed_term_frequency: int


class NrcApsContentSearchOut(BaseModel):
    query: str
    query_tokens: list[str] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    items: list[NrcApsContentSearchResultOut] = Field(default_factory=list)


class NrcApsEvidenceBundleAssembleIn(BaseModel):
    run_id: str
    query: str | None = None
    accession_numbers: list[str] = Field(default_factory=list)
    content_ids: list[str] = Field(default_factory=list)
    target_ids: list[str] = Field(default_factory=list)
    content_contract_id: str | None = None
    chunking_contract_id: str | None = None
    normalization_contract_id: str | None = None
    limit: int | None = None
    offset: int = 0
    persist_bundle: bool = False


class NrcApsEvidenceHighlightOut(BaseModel):
    chunk_start: int
    chunk_end: int
    snippet_start: int
    snippet_end: int


class NrcApsEvidenceChunkOut(BaseModel):
    content_id: str
    chunk_id: str
    group_id: str
    content_contract_id: str
    chunking_contract_id: str
    normalization_contract_id: str
    chunk_ordinal: int
    start_char: int
    end_char: int
    chunk_text: str
    chunk_text_sha256: str
    snippet_text: str
    snippet_start_char: int
    snippet_end_char: int
    highlight_spans: list[NrcApsEvidenceHighlightOut] = Field(default_factory=list)
    matched_unique_query_terms: int = 0
    summed_term_frequency: int = 0
    run_id: str
    target_id: str
    accession_number: str | None = None
    content_units_ref: str | None = None
    normalized_text_ref: str | None = None
    blob_ref: str | None = None
    download_exchange_ref: str | None = None
    discovery_ref: str | None = None
    selection_ref: str | None = None
    normalized_text_sha256: str | None = None
    blob_sha256: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    unit_kind: str | None = None
    quality_status: str | None = None
    diagnostics_ref: str | None = None


class NrcApsEvidenceGroupOut(BaseModel):
    group_id: str
    content_id: str
    run_id: str
    target_id: str
    accession_number: str | None = None
    content_contract_id: str
    chunking_contract_id: str
    chunk_count: int
    visual_page_refs: list[dict[str, Any]] = Field(default_factory=list)
    quality_status: str | None = None
    document_class: str | None = None
    media_type: str | None = None
    page_count: int = 0
    diagnostics_ref: str | None = None
    blob_ref: str | None = None
    blob_sha256: str | None = None
    normalized_text_ref: str | None = None
    normalized_text_sha256: str | None = None
    chunks: list[NrcApsEvidenceChunkOut] = Field(default_factory=list)


class NrcApsEvidenceSnapshotOut(BaseModel):
    snapshot_contract_id: str
    snapshot_started_at_utc: str
    snapshot_completed_at_utc: str
    index_state_hash: str
    index_row_count: int
    index_max_updated_at_utc: str | None = None
    db_fingerprint: str
    read_scope: dict[str, Any] = Field(default_factory=dict)


class NrcApsEvidenceBundleOut(BaseModel):
    schema_id: str
    schema_version: int
    bundle_id: str
    bundle_checksum: str
    bundle_ref: str | None = None
    mode: str
    query: str | None = None
    query_tokens: list[str] = Field(default_factory=list)
    request_identity_hash: str
    snapshot: NrcApsEvidenceSnapshotOut
    total_hits: int
    total_groups: int
    limit: int
    offset: int
    persisted: bool = False
    items: list[NrcApsEvidenceChunkOut] = Field(default_factory=list)
    groups: list[NrcApsEvidenceGroupOut] = Field(default_factory=list)


class NrcApsEvidenceCitationPackCreateIn(BaseModel):
    bundle_id: str | None = None
    bundle_ref: str | None = None
    limit: int | None = None
    offset: int = 0
    persist_pack: bool = False


class NrcApsEvidenceCitationSourceBundleOut(BaseModel):
    schema_id: str
    schema_version: int
    bundle_id: str
    bundle_checksum: str
    bundle_ref: str | None = None
    request_identity_hash: str
    mode: str
    run_id: str
    query: str | None = None
    query_tokens: list[str] = Field(default_factory=list)
    snapshot: NrcApsEvidenceSnapshotOut
    total_hits: int
    total_groups: int


class NrcApsEvidenceCitationOut(BaseModel):
    citation_id: str
    citation_ordinal: int
    citation_label: str
    group_id: str
    chunk_id: str
    content_id: str
    run_id: str
    target_id: str
    accession_number: str | None = None
    content_contract_id: str
    chunking_contract_id: str
    normalization_contract_id: str
    chunk_ordinal: int
    start_char: int
    end_char: int
    snippet_text: str
    snippet_start_char: int
    snippet_end_char: int
    highlight_spans: list[NrcApsEvidenceHighlightOut] = Field(default_factory=list)
    matched_unique_query_terms: int = 0
    summed_term_frequency: int = 0
    chunk_text_sha256: str
    normalized_text_sha256: str | None = None
    blob_sha256: str | None = None
    content_units_ref: str | None = None
    normalized_text_ref: str | None = None
    blob_ref: str | None = None
    download_exchange_ref: str | None = None
    discovery_ref: str | None = None
    selection_ref: str | None = None


class NrcApsEvidenceCitationPackOut(BaseModel):
    schema_id: str
    schema_version: int
    citation_pack_id: str
    citation_pack_checksum: str
    citation_pack_ref: str | None = None
    derivation_contract_id: str
    source_bundle: NrcApsEvidenceCitationSourceBundleOut
    total_citations: int
    total_groups: int
    limit: int
    offset: int
    persisted: bool = False
    citations: list[NrcApsEvidenceCitationOut] = Field(default_factory=list)


class NrcApsEvidenceReportCreateIn(BaseModel):
    citation_pack_id: str | None = None
    citation_pack_ref: str | None = None
    limit: int | None = None
    offset: int = 0
    persist_report: bool = False


class NrcApsEvidenceReportSourceCitationPackOut(BaseModel):
    schema_id: str
    schema_version: int
    citation_pack_id: str
    citation_pack_checksum: str
    citation_pack_ref: str | None = None
    derivation_contract_id: str
    total_citations: int
    total_groups: int
    source_bundle: NrcApsEvidenceCitationSourceBundleOut


class NrcApsEvidenceReportCitationOut(BaseModel):
    citation_id: str
    citation_label: str
    citation_ordinal: int
    chunk_id: str
    chunk_ordinal: int
    start_char: int
    end_char: int
    snippet_text: str
    snippet_start_char: int
    snippet_end_char: int
    highlight_spans: list[NrcApsEvidenceHighlightOut] = Field(default_factory=list)


class NrcApsEvidenceReportSectionOut(BaseModel):
    section_id: str
    section_ordinal: int
    section_type: str
    group_id: str
    accession_number: str | None = None
    content_id: str | None = None
    run_id: str
    target_id: str
    content_contract_id: str
    chunking_contract_id: str
    title: str
    citation_count: int
    citations: list[NrcApsEvidenceReportCitationOut] = Field(default_factory=list)


class NrcApsEvidenceReportOut(BaseModel):
    schema_id: str
    schema_version: int
    evidence_report_id: str
    evidence_report_checksum: str
    evidence_report_ref: str | None = None
    assembly_contract_id: str
    sectioning_contract_id: str
    source_citation_pack: NrcApsEvidenceReportSourceCitationPackOut
    total_sections: int
    total_citations: int
    total_groups: int
    limit: int
    offset: int
    persisted: bool = False
    sections: list[NrcApsEvidenceReportSectionOut] = Field(default_factory=list)


class NrcApsEvidenceReportExportCreateIn(BaseModel):
    evidence_report_id: str | None = None
    evidence_report_ref: str | None = None
    persist_export: bool = False


class NrcApsEvidenceReportExportSourceEvidenceReportOut(BaseModel):
    schema_id: str
    schema_version: int
    evidence_report_id: str
    evidence_report_checksum: str
    evidence_report_ref: str | None = None
    assembly_contract_id: str
    sectioning_contract_id: str
    total_sections: int
    total_citations: int
    total_groups: int
    source_citation_pack: NrcApsEvidenceReportSourceCitationPackOut


class NrcApsEvidenceReportExportOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    evidence_report_export_id: str
    evidence_report_export_checksum: str
    evidence_report_export_ref: str | None = None
    render_contract_id: str
    template_contract_id: str
    format_id: str
    media_type: str
    file_extension: str
    source_evidence_report: NrcApsEvidenceReportExportSourceEvidenceReportOut
    total_sections: int
    total_citations: int
    total_groups: int
    rendered_markdown_sha256: str
    rendered_markdown: str
    persisted: bool = False


class NrcApsEvidenceReportExportPackageCreateIn(BaseModel):
    evidence_report_export_ids: list[str] = Field(default_factory=list)
    evidence_report_export_refs: list[str] = Field(default_factory=list)
    persist_package: bool = False


class NrcApsEvidenceReportExportPackageSourceExportOut(BaseModel):
    export_ordinal: int
    evidence_report_export_id: str
    evidence_report_export_checksum: str
    evidence_report_export_ref: str | None = None
    rendered_markdown_sha256: str
    source_evidence_report_id: str
    source_evidence_report_checksum: str
    source_evidence_report_ref: str | None = None
    total_sections: int
    total_citations: int
    total_groups: int


class NrcApsEvidenceReportExportPackageOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    evidence_report_export_package_id: str
    evidence_report_export_package_checksum: str
    evidence_report_export_package_ref: str | None = None
    composition_contract_id: str
    package_mode: str
    owner_run_id: str
    format_id: str
    media_type: str
    file_extension: str
    render_contract_id: str
    template_contract_id: str
    source_export_count: int
    total_sections: int
    total_citations: int
    total_groups: int
    ordered_source_exports_sha256: str
    persisted: bool = False
    source_exports: list[NrcApsEvidenceReportExportPackageSourceExportOut] = Field(default_factory=list)


class NrcApsContextPacketCreateIn(BaseModel):
    evidence_report_id: str | None = None
    evidence_report_ref: str | None = None
    evidence_report_export_id: str | None = None
    evidence_report_export_ref: str | None = None
    evidence_report_export_package_id: str | None = None
    evidence_report_export_package_ref: str | None = None
    persist_context_packet: bool = False


class NrcApsContextPacketFactOut(BaseModel):
    fact_ordinal: int
    fact_type: str
    source_pointer: str
    source_ref: str | None = None
    source_id: str
    source_checksum: str
    fields: dict[str, Any] = Field(default_factory=dict)


class NrcApsContextPacketCaveatOut(BaseModel):
    caveat_ordinal: int
    code: str
    context_key: str
    source_pointer: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class NrcApsContextPacketConstraintOut(BaseModel):
    constraint_ordinal: int
    code: str
    context_key: str
    source_pointer: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class NrcApsContextPacketUnresolvedQuestionOut(BaseModel):
    unresolved_question_ordinal: int
    code: str
    context_key: str
    source_pointer: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class NrcApsContextPacketOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    context_packet_id: str
    context_packet_checksum: str
    context_packet_ref: str | None = None
    projection_contract_id: str
    fact_grammar_contract_id: str
    source_family: str
    source_descriptor: dict[str, Any] = Field(default_factory=dict)
    objective: str
    scope: dict[str, Any] = Field(default_factory=dict)
    facts: list[NrcApsContextPacketFactOut] = Field(default_factory=list)
    caveats: list[NrcApsContextPacketCaveatOut] = Field(default_factory=list)
    constraints: list[NrcApsContextPacketConstraintOut] = Field(default_factory=list)
    unresolved_questions: list[NrcApsContextPacketUnresolvedQuestionOut] = Field(default_factory=list)
    total_facts: int
    total_caveats: int
    total_constraints: int
    total_unresolved_questions: int
    persisted: bool = False


class NrcApsContextDossierCreateIn(BaseModel):
    context_packet_ids: list[str] = Field(default_factory=list)
    context_packet_refs: list[str] = Field(default_factory=list)
    persist_dossier: bool = False


class NrcApsContextDossierSourcePacketOut(BaseModel):
    packet_ordinal: int
    context_packet_id: str
    context_packet_checksum: str
    context_packet_ref: str | None = None
    source_family: str
    source_id: str
    source_checksum: str
    owner_run_id: str
    projection_contract_id: str
    fact_grammar_contract_id: str
    objective: str
    total_facts: int
    total_caveats: int
    total_constraints: int
    total_unresolved_questions: int


class NrcApsContextDossierOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    context_dossier_id: str
    context_dossier_checksum: str
    context_dossier_ref: str | None = None
    composition_contract_id: str
    dossier_mode: str
    owner_run_id: str
    projection_contract_id: str
    fact_grammar_contract_id: str
    objective: str
    source_family: str
    source_packet_count: int
    ordered_source_packets_sha256: str
    total_facts: int
    total_caveats: int
    total_constraints: int
    total_unresolved_questions: int
    source_packets: list[NrcApsContextDossierSourcePacketOut] = Field(default_factory=list)
    persisted: bool = False


class NrcApsDeterministicInsightArtifactCreateIn(BaseModel):
    context_dossier_id: str | None = None
    context_dossier_ref: str | None = None
    persist_insight_artifact: bool = False


class NrcApsDeterministicInsightArtifactSourcePacketOut(BaseModel):
    packet_ordinal: int
    context_packet_id: str
    total_facts: int
    total_caveats: int
    total_constraints: int
    total_unresolved_questions: int


class NrcApsDeterministicInsightArtifactSourceContextDossierOut(BaseModel):
    schema_id: str
    schema_version: int
    context_dossier_id: str
    context_dossier_checksum: str
    context_dossier_ref: str | None = None
    composition_contract_id: str
    dossier_mode: str
    owner_run_id: str
    projection_contract_id: str
    fact_grammar_contract_id: str
    objective: str
    source_family: str
    source_packet_count: int
    ordered_source_packets_sha256: str
    total_facts: int
    total_caveats: int
    total_constraints: int
    total_unresolved_questions: int
    source_packets: list[NrcApsDeterministicInsightArtifactSourcePacketOut] = Field(default_factory=list)


class NrcApsDeterministicInsightArtifactEvidencePointerOut(BaseModel):
    pointer: str
    packet_ordinal: int | None = None
    context_packet_id: str | None = None


class NrcApsDeterministicInsightArtifactFindingOut(BaseModel):
    finding_id: str
    rule_id: str
    rule_version: int
    category: str
    severity: str
    matched_source_packet_count: int
    message: str
    evidence_pointers: list[NrcApsDeterministicInsightArtifactEvidencePointerOut] = Field(default_factory=list)


class NrcApsDeterministicInsightArtifactOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    deterministic_insight_artifact_id: str
    deterministic_insight_artifact_checksum: str
    deterministic_insight_artifact_ref: str | None = None
    ruleset_contract_id: str
    ruleset_id: str
    ruleset_version: int
    insight_mode: str
    source_context_dossier: NrcApsDeterministicInsightArtifactSourceContextDossierOut
    total_findings: int
    finding_counts: dict[str, int] = Field(default_factory=dict)
    findings: list[NrcApsDeterministicInsightArtifactFindingOut] = Field(default_factory=list)
    persisted: bool = False


class NrcApsDeterministicChallengeArtifactCreateIn(BaseModel):
    deterministic_insight_artifact_id: str | None = None
    deterministic_insight_artifact_ref: str | None = None
    persist_challenge_artifact: bool = False


class NrcApsDeterministicChallengeArtifactSourceInsightOut(BaseModel):
    schema_id: str
    schema_version: int
    deterministic_insight_artifact_id: str
    deterministic_insight_artifact_checksum: str
    deterministic_insight_artifact_ref: str | None = None
    ruleset_contract_id: str
    ruleset_id: str
    ruleset_version: int
    insight_mode: str
    owner_run_id: str
    source_context_dossier_id: str
    source_context_dossier_checksum: str
    source_context_dossier_ref: str | None = None
    total_findings: int
    finding_counts: dict[str, int] = Field(default_factory=dict)


class NrcApsDeterministicChallengeArtifactEvidencePointerOut(BaseModel):
    pointer: str
    source_finding_id: str | None = None
    source_rule_id: str | None = None


class NrcApsDeterministicChallengeArtifactChallengeOut(BaseModel):
    challenge_id: str
    check_id: str
    check_version: int
    category: str
    severity: str
    disposition: str
    matched_finding_count: int
    source_finding_ids: list[str] = Field(default_factory=list)
    message: str
    evidence_pointers: list[NrcApsDeterministicChallengeArtifactEvidencePointerOut] = Field(default_factory=list)


class NrcApsDeterministicChallengeArtifactOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    deterministic_challenge_artifact_id: str
    deterministic_challenge_artifact_checksum: str
    deterministic_challenge_artifact_ref: str | None = None
    ruleset_contract_id: str
    ruleset_id: str
    ruleset_version: int
    challenge_mode: str
    source_deterministic_insight_artifact: NrcApsDeterministicChallengeArtifactSourceInsightOut
    total_challenges: int
    challenge_counts: dict[str, int] = Field(default_factory=dict)
    disposition_counts: dict[str, int] = Field(default_factory=dict)
    challenges: list[NrcApsDeterministicChallengeArtifactChallengeOut] = Field(default_factory=list)
    persisted: bool = False
