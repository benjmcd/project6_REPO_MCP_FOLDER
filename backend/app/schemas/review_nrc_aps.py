from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NrcApsReviewRunSummaryCountersOut(BaseModel):
    selected_count: int = 0
    downloaded_count: int = 0
    failed_count: int = 0


class NrcApsReviewRunSelectorItemOut(BaseModel):
    run_id: str
    display_label: str | None = None
    connector_key: str = "nrc_adams_aps"
    status: str = "unknown"
    submitted_at: str
    completed_at: str | None = None
    reviewable: bool
    disabled_reason_code: str | None = None
    summary_counters: NrcApsReviewRunSummaryCountersOut = Field(default_factory=NrcApsReviewRunSummaryCountersOut)


class NrcApsReviewRunSelectorOut(BaseModel):
    default_run_id: str | None = None
    runs: list[NrcApsReviewRunSelectorItemOut] = Field(default_factory=list)


class NrcApsReviewCanonicalNodeOut(BaseModel):
    node_id: str
    label: str
    stage_family: str
    description: str | None = None
    expected_artifact_classes: list[str] = Field(default_factory=list)


class NrcApsReviewCanonicalEdgeOut(BaseModel):
    source_id: str
    target_id: str


class NrcApsReviewCanonicalGraphOut(BaseModel):
    pipeline_id: str = "nrc_aps_review_v1"
    version: str = "1"
    nodes: list[NrcApsReviewCanonicalNodeOut] = Field(default_factory=list)
    edges: list[NrcApsReviewCanonicalEdgeOut] = Field(default_factory=list)


class NrcApsReviewProjectionNodeOut(BaseModel):
    projection_id: str
    title: str
    detail_lines: list[str] = Field(default_factory=list)
    stage_family: str
    canonical_node_ids: list[str] = Field(default_factory=list)
    state: str = "unknown"
    warnings: list[str] = Field(default_factory=list)
    mapped_file_refs: list[str] = Field(default_factory=list)
    mapped_tree_ids: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    structured_summary: dict[str, Any] = Field(default_factory=dict)
    is_composite: bool = False


class NrcApsReviewProjectionEdgeOut(BaseModel):
    source_id: str
    target_id: str


class NrcApsReviewProjectionGraphOut(BaseModel):
    projection_id: str
    version: str = "1"
    nodes: list[NrcApsReviewProjectionNodeOut] = Field(default_factory=list)
    edges: list[NrcApsReviewProjectionEdgeOut] = Field(default_factory=list)


class NrcApsReviewPipelineLayoutEntryOut(BaseModel):
    label: str
    value: str
    path: str | None = None


class NrcApsReviewPipelineLayoutSectionOut(BaseModel):
    title: str
    entries: list[NrcApsReviewPipelineLayoutEntryOut] = Field(default_factory=list)


class NrcApsReviewPipelineLayoutOut(BaseModel):
    run_id: str
    sections: list[NrcApsReviewPipelineLayoutSectionOut] = Field(default_factory=list)


class NrcApsReviewPipelineDefinitionOut(BaseModel):
    canonical_graph: NrcApsReviewCanonicalGraphOut
    pipeline_projection: NrcApsReviewProjectionGraphOut


class NrcApsReviewTreeNodeOut(BaseModel):
    tree_id: str
    name: str
    path: str
    is_dir: bool
    children: list["NrcApsReviewTreeNodeOut"] | None = None
    mapped_node_ids: list[str] = Field(default_factory=list)


class NrcApsReviewTreeOut(BaseModel):
    run_id: str
    root: NrcApsReviewTreeNodeOut


class NrcApsReviewNodeDetailsOut(BaseModel):
    node_id: str
    label: str
    stage_family: str
    run_id: str
    state: str
    warnings: list[str] = Field(default_factory=list)
    mapped_file_refs: list[str] = Field(default_factory=list)
    structured_summary: dict[str, Any] = Field(default_factory=dict)


class NrcApsReviewFileDetailsOut(BaseModel):
    tree_id: str
    path: str
    name: str
    is_dir: bool
    mapped_node_ids: list[str] = Field(default_factory=list)
    run_id: str
    size_bytes: int | None = None
    modified_time: str | None = None
    preview_available: bool = False
    preview_kind: str | None = None
    structured_summary: dict[str, Any] = Field(default_factory=dict)


class NrcApsReviewFilePreviewOut(BaseModel):
    tree_id: str
    path: str
    name: str
    run_id: str
    preview_kind: str
    language: str
    content: str
    truncated: bool = False
    max_chars: int


class NrcApsReviewOverviewOut(BaseModel):
    run_id: str
    run_summary: dict[str, Any] = Field(default_factory=dict)
    run_projection: NrcApsReviewProjectionGraphOut
    pipeline_layout: NrcApsReviewPipelineLayoutOut
    tree: NrcApsReviewTreeOut


class NrcApsReviewTraceStateOut(BaseModel):
    has_source_blob: bool = False
    has_diagnostics: bool = False
    has_normalized_text: bool = False
    has_indexed_chunks: bool = False
    has_downstream_usage: bool = False


class NrcApsReviewDocumentSelectorRowOut(BaseModel):
    target_id: str
    accession_number: str | None = None
    document_title: str | None = None
    document_type: str | None = None
    media_type: str | None = None
    content_id: str | None = None
    trace_state: NrcApsReviewTraceStateOut


class NrcApsReviewDocumentSelectorOut(BaseModel):
    run_id: str
    default_target_id: str | None = None
    documents: list[NrcApsReviewDocumentSelectorRowOut] = Field(default_factory=list)


class NrcApsReviewTraceIdentityOut(BaseModel):
    accession_number: str | None = None
    document_title: str | None = None
    document_type: str | None = None
    media_type: str | None = None
    source_file_name: str | None = None
    content_id: str | None = None
    content_contract_id: str | None = None
    chunking_contract_id: str | None = None
    normalization_contract_id: str | None = None


class NrcApsReviewTraceSourceOut(BaseModel):
    viewer_kind: str = "unsupported"
    blob_ref_present: bool = False
    source_endpoint: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None


class NrcApsReviewTraceSummaryOut(BaseModel):
    document_class: str | None = None
    quality_status: str | None = None
    page_count: int = 0
    ordered_unit_count: int = 0
    indexed_chunk_count: int = 0
    visual_page_ref_count: int = 0
    visual_derivative_unit_count: int = 0


class NrcApsReviewTraceCompletenessOut(BaseModel):
    has_linkage_row: bool = False
    has_document_row: bool = False
    has_source_blob: bool = False
    has_diagnostics: bool = False
    has_normalized_text: bool = False
    has_indexed_chunks: bool = False
    has_visual_derivatives: bool = False
    has_downstream_usage: bool = False
    retrieval_available: bool = False


class NrcApsReviewTraceSyncCapabilitiesOut(BaseModel):
    source_to_units: str = "none"
    units_to_source: str = "none"
    normalized_text_to_source: str = "none"
    chunk_to_source: str = "none"


class NrcApsReviewTraceTabOut(BaseModel):
    tab_id: str
    label: str
    available: bool = False
    endpoint: str | None = None


class NrcApsReviewTraceManifestOut(BaseModel):
    run_id: str
    target_id: str
    identity: NrcApsReviewTraceIdentityOut
    source: NrcApsReviewTraceSourceOut
    summary: NrcApsReviewTraceSummaryOut
    trace_completeness: NrcApsReviewTraceCompletenessOut
    sync_capabilities: NrcApsReviewTraceSyncCapabilitiesOut
    tabs: list[NrcApsReviewTraceTabOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class NrcApsReviewDiagnosticsOut(BaseModel):
    run_id: str
    target_id: str
    available: bool = False
    quality_status: str | None = None
    document_class: str | None = None
    page_count: int = 0
    ordered_unit_count: int = 0
    visual_page_ref_count: int = 0
    visual_derivative_unit_count: int = 0
    unit_kind_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    degradation_codes: list[str] = Field(default_factory=list)
    extractor_metadata: dict[str, Any] | None = None


class NrcApsReviewNormalizedTextOut(BaseModel):
    run_id: str
    target_id: str
    available: bool = False
    char_count: int = 0
    mapping_precision: str | None = None
    text: str | None = None


class NrcApsReviewIndexedChunkItemOut(BaseModel):
    chunk_id: str
    chunk_ordinal: int
    page_start: int | None = None
    page_end: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    unit_kind: str | None = None
    quality_status: str | None = None
    chunk_text: str
    mapping_precision: str | None = None


class NrcApsReviewIndexedChunksOut(BaseModel):
    run_id: str
    target_id: str
    available: bool = False
    chunk_count: int = 0
    chunks: list[NrcApsReviewIndexedChunkItemOut] = Field(default_factory=list)


class NrcApsReviewExtractedUnitItemOut(BaseModel):
    unit_id: str
    page_number: int | None = None
    unit_kind: str | None = None
    text: str | None = None
    bbox: list[float] | None = None
    start_char: int | None = None
    end_char: int | None = None
    mapping_precision: str = "unit"


class NrcApsReviewVisualArtifactItemOut(BaseModel):
    artifact_id: str
    page_number: int | None = None
    status: str | None = None
    visual_page_class: str | None = None
    artifact_semantics: str | None = None
    format: str | None = None
    media_type: str | None = None
    width: float | None = None
    height: float | None = None
    dpi: int | None = None
    sha256: str | None = None
    endpoint: str | None = None


class NrcApsReviewExtractedUnitsOut(BaseModel):
    run_id: str
    target_id: str
    available: bool = False
    reason_code: str | None = None
    source_precision: str = "none"
    source_layer: str = "diagnostics_ordered_units"
    page_number: int | None = None
    total_unit_count: int = 0
    visual_artifacts: list[NrcApsReviewVisualArtifactItemOut] = Field(default_factory=list)
    units: list[NrcApsReviewExtractedUnitItemOut] = Field(default_factory=list)


class NrcApsReviewDownstreamUsageItemOut(BaseModel):
    consumer_stage: str
    artifact_class: str
    display_ref: str
    attribution_precision: str


class NrcApsReviewDownstreamUsageOut(BaseModel):
    run_id: str
    target_id: str
    available: bool = False
    usage: list[NrcApsReviewDownstreamUsageItemOut] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

