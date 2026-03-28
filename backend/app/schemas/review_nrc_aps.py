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
