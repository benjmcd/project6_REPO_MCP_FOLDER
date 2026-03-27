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


class NrcApsReviewRunNodeStateOut(BaseModel):
    node_id: str
    state: str
    warnings: list[str] = Field(default_factory=list)
    mapped_file_refs: list[str] = Field(default_factory=list)
    summary_metrics: dict[str, Any] = Field(default_factory=dict)


class NrcApsReviewRunGraphOut(BaseModel):
    run_id: str
    canonical_graph: NrcApsReviewCanonicalGraphOut
    node_states: dict[str, NrcApsReviewRunNodeStateOut] = Field(default_factory=dict)


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
    structured_summary: dict[str, Any] = Field(default_factory=dict)


class NrcApsReviewOverviewOut(BaseModel):
    run_id: str
    graph: NrcApsReviewRunGraphOut
    tree: NrcApsReviewTreeOut
