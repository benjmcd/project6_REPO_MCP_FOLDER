from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


L3_SESSION_STATUS_ACTIVE_LOADING = "active_loading"
L3_SESSION_STATUS_ACTIVE_PLANNING = "active_planning"
L3_SESSION_STATUS_ACTIVE_EXECUTION = "active_execution"
L3_SESSION_STATUS_COMPLETED = "completed"
L3_SESSION_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
L3_SESSION_STATUS_FAILED = "failed"
L3_SESSION_STATUS_VALUES = (
    L3_SESSION_STATUS_ACTIVE_LOADING,
    L3_SESSION_STATUS_ACTIVE_PLANNING,
    L3_SESSION_STATUS_ACTIVE_EXECUTION,
    L3_SESSION_STATUS_COMPLETED,
    L3_SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    L3_SESSION_STATUS_FAILED,
)
L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED = "claimed"
L3_GATE_B_IDEMPOTENCY_STATUS_COMMITTED = "committed"
L3_GATE_B_IDEMPOTENCY_STATUS_VALUES = (
    L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED,
    L3_GATE_B_IDEMPOTENCY_STATUS_COMMITTED,
)
L3_ANALYSIS_PLAN_STATUS_FORMED = "formed"
L3_ANALYSIS_PLAN_STATUS_APPROVED = "approved"
L3_ANALYSIS_PLAN_STATUS_CANCELLED = "cancelled"
L3_ANALYSIS_PLAN_STATUS_VALUES = (
    L3_ANALYSIS_PLAN_STATUS_FORMED,
    L3_ANALYSIS_PLAN_STATUS_APPROVED,
    L3_ANALYSIS_PLAN_STATUS_CANCELLED,
)
L3_PASS_RUN_STATUS_PLANNED = "planned"
L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED = "selected_not_started"
L3_PASS_RUN_STATUS_RUNNING = "running"
L3_PASS_RUN_STATUS_COMPLETED = "completed"
L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
L3_PASS_RUN_STATUS_FAILED = "failed"
L3_PASS_RUN_STATUS_VALUES = (
    L3_PASS_RUN_STATUS_PLANNED,
    L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED,
    L3_PASS_RUN_STATUS_RUNNING,
    L3_PASS_RUN_STATUS_COMPLETED,
    L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS,
    L3_PASS_RUN_STATUS_FAILED,
)
L3_SEC_XBRL_PROJECTION_REDACTION_POLICY = "redacted_no_values"
L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED = "materialized"
L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY = "redacted_no_values"
L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED = "materialized"
L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY = "redacted_no_values"
L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE = "redacted_statement_packet_review_only"
L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY = "review_ready"
L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_REDACTION_POLICY = "redacted_no_values"
L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_MODE = "redacted_statement_packet_operator_review_decision"
L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED = "decision_recorded"
L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_VALUES = (
    "approved",
    "changes_requested",
    "rejected",
    "blocked",
)
L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_REASON_CODES = (
    "ready_for_next_freeze",
    "needs_packet_revision",
    "authority_gap",
    "redaction_gap",
    "operator_blocked",
)
L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY = "ready_for_explicit_value_reveal"
L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID = "sec_xbrl_approved_decision_bound_value_reveal_authority_v1"
L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY = "sec_xbrl_value_reveal_authority_hashes_only_v1"
L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY = "controlled_values_revealed_transiently"
L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_POLICY_ID = (
    "sec_xbrl_authority_receipt_bound_controlled_value_reveal_submit_v1"
)
L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_REDACTION_POLICY = (
    "sec_xbrl_controlled_value_reveal_submit_hash_count_receipt_v1"
)
L3_SEC_XBRL_AUTH_BINDING_POLICY_ID = "sec_xbrl_repo_owned_in_app_auth_owner_binding_v1"
L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND = "owner_bound"
L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY = "hash_only_actor_workspace_policy_refs_v1"

L3_ANALYSIS_PRODUCT_KIND_VALUES = (
    "analyst_note",
    "fact",
    "metric",
    "finding",
    "insight",
    "diagnostic",
    "summary",
    "hypothesis",
    "recommendation",
)
L3_ANALYSIS_PRODUCT_EXECUTOR_TYPE_VALUES = (
    "human",
    "deterministic",
    "agent",
    "external_api",
)
L3_ANALYSIS_PRODUCT_LIFECYCLE_VALUES = (
    "draft",
    "proposed",
    "validated",
    "accepted",
    "rejected",
    "package_eligible",
    "packaged",
    "superseded",
)
L3_ANALYSIS_PRODUCT_REVIEW_DECISION_VALUES = (
    "promote",
    "accept",
    "mark_package_eligible",
    "reject",
    "revise",
    "supersede",
)
L3_ANALYSIS_PRODUCT_REVIEW_REASON_CODES = (
    "proposed_ready",
    "validation_passed",
    "grounded_accept",
    "package_ready",
    "insufficient_grounding",
    "evidence_gap",
    "operator_rejected",
    "revision_requested",
    "superseded_by_successor",
    "stale_basis",
)
L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED = "decision_recorded"
L3_ANALYSIS_PRODUCT_EVIDENCE_ROLE_VALUES = (
    "observation",
    "measurement",
    "claim",
    "interpretation",
    "context",
    "counterpoint",
)
L3_WORKING_SET_MEMBER_REF_KIND_VALUES = (
    "material_snapshot",
    "pass_run",
    "output_package",
    "analysis_set",
    "prior_product",
)
L3_ANALYSIS_PRODUCT_EVIDENCE_REF_KIND_VALUES = (
    "material_snapshot",
    "pass_run",
    "output_package",
    "analysis_set",
    "prior_product",
    "working_set",
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SourceConnector(Base, TimestampMixin):
    __tablename__ = "source_connector"

    source_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_category: Mapped[str] = mapped_column(String(100), nullable=False)
    automation_tier: Mapped[str | None] = mapped_column(String(50))
    api_available_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    update_cadence: Mapped[str | None] = mapped_column(String(100))
    cleanup_burden: Mapped[str | None] = mapped_column(String(100))
    domain_pack: Mapped[str | None] = mapped_column(String(100))

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="source")


class Dataset(Base, TimestampMixin):
    __tablename__ = "dataset"

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("source_connector.source_id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    domain_pack: Mapped[str | None] = mapped_column(String(100))
    frequency_hint: Mapped[str | None] = mapped_column(String(50))
    time_column: Mapped[str | None] = mapped_column(String(255))

    source: Mapped[SourceConnector | None] = relationship(back_populates="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    saved_queries: Mapped[list["SavedQuery"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    external_identities: Mapped[list["DatasetExternalIdentity"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base, TimestampMixin):
    __tablename__ = "dataset_version"

    dataset_version_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.dataset_id"), nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_version.dataset_version_id"))
    version_label: Mapped[str] = mapped_column(String(255), nullable=False)
    version_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ready")
    storage_ref: Mapped[str | None] = mapped_column(String(512))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    source_row_count: Mapped[int | None] = mapped_column(Integer)
    dropped_row_count: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    dataset: Mapped[Dataset] = relationship(back_populates="versions", foreign_keys=[dataset_id])
    parent_version: Mapped[DatasetVersion | None] = relationship(remote_side=[dataset_version_id])
    variables: Mapped[list["VariableDefinition"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    rows: Mapped[list["DatasetRow"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    profiles: Mapped[list["VariableProfile"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    transformations: Mapped[list["TransformationRun"]] = relationship(back_populates="input_dataset_version", cascade="all, delete-orphan", foreign_keys="TransformationRun.input_dataset_version_id")
    annotations: Mapped[list["AnnotationWindow"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")
    source_provenance: Mapped[list["DatasetSourceProvenance"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")


class VariableDefinition(Base, TimestampMixin):
    __tablename__ = "variable_definition"
    __table_args__ = (UniqueConstraint("dataset_version_id", "variable_name", name="uq_version_variable_name"),)

    variable_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    variable_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dtype: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="measure")
    is_numeric: Mapped[bool] = mapped_column(Boolean, default=False)
    is_time_index: Mapped[bool] = mapped_column(Boolean, default=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False)

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="variables")
    profiles: Mapped[list["VariableProfile"]] = relationship(back_populates="variable")


class VariableProfile(Base, TimestampMixin):
    __tablename__ = "variable_profile"

    variable_profile_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    variable_id: Mapped[str] = mapped_column(ForeignKey("variable_definition.variable_id"), nullable=False)
    missingness_rate: Mapped[float | None] = mapped_column(Float)
    mean_value: Mapped[float | None] = mapped_column(Float)
    median_value: Mapped[float | None] = mapped_column(Float)
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    std_dev: Mapped[float | None] = mapped_column(Float)
    skewness: Mapped[float | None] = mapped_column(Float)
    outlier_fraction: Mapped[float | None] = mapped_column(Float)
    negative_values_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    zero_values_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    bounded_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    seasonality_flag: Mapped[bool | None] = mapped_column(Boolean)
    stationarity_hint: Mapped[str | None] = mapped_column(String(100))
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="profiles")
    variable: Mapped[VariableDefinition] = relationship(back_populates="profiles")


class TransformationRun(Base, TimestampMixin):
    __tablename__ = "transformation_run"

    transformation_run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    input_dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    output_dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_version.dataset_version_id"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    rationale: Mapped[str | None] = mapped_column(Text)

    input_dataset_version: Mapped[DatasetVersion] = relationship(foreign_keys=[input_dataset_version_id], back_populates="transformations")
    output_dataset_version: Mapped[DatasetVersion | None] = relationship(foreign_keys=[output_dataset_version_id])
    steps: Mapped[list["TransformationStep"]] = relationship(back_populates="transformation_run", cascade="all, delete-orphan")


class TransformationStep(Base):
    __tablename__ = "transformation_step"

    transformation_step_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    transformation_run_id: Mapped[str] = mapped_column(ForeignKey("transformation_run.transformation_run_id"), nullable=False)
    input_variable_id: Mapped[str] = mapped_column(ForeignKey("variable_definition.variable_id"), nullable=False)
    output_variable_id: Mapped[str | None] = mapped_column(ForeignKey("variable_definition.variable_id"))
    method_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    selection_reason: Mapped[str | None] = mapped_column(Text)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list)

    transformation_run: Mapped[TransformationRun] = relationship(back_populates="steps")


class AnnotationWindow(Base, TimestampMixin):
    __tablename__ = "annotation_window"

    annotation_window_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    annotation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="annotations")


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_run"

    analysis_run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    method_name: Mapped[str] = mapped_column(String(100), nullable=False)
    goal_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    route_reason: Mapped[str | None] = mapped_column(Text)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    window_scope_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="analysis_runs")
    assumptions: Mapped[list["AssumptionCheck"]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")
    caveats: Mapped[list["CaveatNote"]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")
    artifacts: Mapped[list["AnalysisArtifact"]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")


class AssumptionCheck(Base):
    __tablename__ = "assumption_check"

    assumption_check_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    assumption_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_method: Mapped[str | None] = mapped_column(String(255))
    check_result: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="assumptions")


class CaveatNote(Base, TimestampMixin):
    __tablename__ = "caveat_note"

    caveat_note_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    caveat_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="caveats")


class AnalysisArtifact(Base, TimestampMixin):
    __tablename__ = "analysis_artifact"

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="artifacts")


class SavedQuery(Base, TimestampMixin):
    __tablename__ = "saved_query"

    saved_query_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.dataset_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str] = mapped_column(String(50), default="sql")

    dataset: Mapped[Dataset] = relationship(back_populates="saved_queries")


class QueryRun(Base, TimestampMixin):
    __tablename__ = "query_run"

    query_run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    saved_query_id: Mapped[str | None] = mapped_column(ForeignKey("saved_query.saved_query_id"))
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    runtime_ms: Mapped[int | None] = mapped_column(Integer)


class ConnectorRun(Base, TimestampMixin):
    __tablename__ = "connector_run"

    connector_run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False, default="sciencebase")
    source_mode: Mapped[str] = mapped_column(String(100), nullable=False, default="public_api")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    request_config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    query_plan_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_query_fingerprint: Mapped[str | None] = mapped_column(String(128))
    request_fingerprint: Mapped[str | None] = mapped_column(String(128))
    effective_search_params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_filters_json: Mapped[list] = mapped_column(JSON, default=list)
    effective_sort: Mapped[str | None] = mapped_column(String(100))
    effective_order: Mapped[str | None] = mapped_column(String(20))
    effective_page_size: Mapped[int | None] = mapped_column(Integer)
    search_exhaustion_reason: Mapped[str | None] = mapped_column(String(100))
    page_count_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    partition_count_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_page_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_offset_committed: Mapped[int | None] = mapped_column(Integer)
    submission_idempotency_key: Mapped[str | None] = mapped_column(String(255))
    discovery_snapshot_ref: Mapped[str | None] = mapped_column(String(512))
    selection_manifest_ref: Mapped[str | None] = mapped_column(String(512))
    report_ref: Mapped[str | None] = mapped_column(String(512))
    adapter_dialect: Mapped[str | None] = mapped_column(String(100))
    api_generation: Mapped[str | None] = mapped_column(String(100))
    sciencebase_normalization_version: Mapped[str | None] = mapped_column(String(100))
    execution_lease_owner: Mapped[str | None] = mapped_column(String(255))
    execution_lease_token: Mapped[str | None] = mapped_column(String(64))
    execution_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resume_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ignored_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    collapsed_duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduped_within_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_by_fetch_policy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_modified_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reconciliation_only_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget_blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_skipped_count_by_reason_json: Mapped[dict] = mapped_column(JSON, default=dict)
    consumed_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    downloaded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingested_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    profiled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommended_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retryable_target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terminal_target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nonterminal_target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)

    targets: Mapped[list["ConnectorRunTarget"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")
    submissions: Mapped[list["ConnectorRunSubmission"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")
    source_provenance: Mapped[list["DatasetSourceProvenance"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")
    checkpoints: Mapped[list["ConnectorRunCheckpoint"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")
    partition_cursors: Mapped[list["ConnectorRunPartitionCursor"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")
    policy_snapshots: Mapped[list["ConnectorPolicySnapshot"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")
    events: Mapped[list["ConnectorRunEvent"]] = relationship(back_populates="connector_run", cascade="all, delete-orphan")


class ConnectorRunSubmission(Base, TimestampMixin):
    __tablename__ = "connector_run_submission"
    __table_args__ = (UniqueConstraint("connector_key", "submission_idempotency_key", name="uq_connector_submission_key"),)

    connector_run_submission_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False)
    submission_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    connector_run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    connector_run: Mapped[ConnectorRun] = relationship(back_populates="submissions")


class ConnectorRunTarget(Base, TimestampMixin):
    __tablename__ = "connector_run_target"

    connector_run_target_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stable_release_key: Mapped[str | None] = mapped_column(String(255))
    sciencebase_item_id: Mapped[str | None] = mapped_column(String(255))
    sciencebase_item_url: Mapped[str | None] = mapped_column(String(512))
    sciencebase_file_name: Mapped[str | None] = mapped_column(String(512))
    sciencebase_download_uri: Mapped[str | None] = mapped_column(String(1024))
    artifact_surface: Mapped[str] = mapped_column(String(50), nullable=False, default="files")
    selection_source: Mapped[str | None] = mapped_column(String(50))
    selection_scope: Mapped[str | None] = mapped_column(String(50))
    selection_match_basis: Mapped[str | None] = mapped_column(String(100))
    artifact_locator_type: Mapped[str | None] = mapped_column(String(100))
    source_artifact_key: Mapped[str | None] = mapped_column(String(1024))
    canonical_artifact_key: Mapped[str | None] = mapped_column(String(1024))
    remote_checksum_type: Mapped[str | None] = mapped_column(String(100))
    remote_checksum_value: Mapped[str | None] = mapped_column(String(255))
    downloaded_sha256: Mapped[str | None] = mapped_column(String(64))
    raw_storage_ref: Mapped[str | None] = mapped_column(String(512))
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    fetch_policy_mode: Mapped[str | None] = mapped_column(String(100))
    resolved_ip: Mapped[str | None] = mapped_column(String(64))
    redirect_count: Mapped[int | None] = mapped_column(Integer)
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    aliases_json: Mapped[list] = mapped_column(JSON, default=list)
    source_reference_json: Mapped[dict] = mapped_column(JSON, default=dict)
    permission_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    access_level_summary: Mapped[str | None] = mapped_column(String(100))
    public_read_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="discovered")
    error_stage: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    last_error_class: Mapped[str | None] = mapped_column(String(100))
    retry_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("dataset.dataset_id"))
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_version.dataset_version_id"))
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    profiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recommended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_stage_transition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    operator_reason_code: Mapped[str | None] = mapped_column(String(255))
    selection_reason_code: Mapped[str | None] = mapped_column(String(255))
    ignore_reason_code: Mapped[str | None] = mapped_column(String(255))
    dedup_reason_code: Mapped[str | None] = mapped_column(String(255))
    versioning_reason_code: Mapped[str | None] = mapped_column(String(255))
    reconciliation_reason_code: Mapped[str | None] = mapped_column(String(255))
    stable_release_identifier: Mapped[str | None] = mapped_column(String(512))
    identifiers_json: Mapped[list] = mapped_column(JSON, default=list)

    connector_run: Mapped[ConnectorRun] = relationship(back_populates="targets")
    stage_attempts: Mapped[list["ConnectorTargetStageAttempt"]] = relationship(back_populates="connector_run_target", cascade="all, delete-orphan")
    aliases: Mapped[list["ConnectorArtifactAlias"]] = relationship(back_populates="connector_run_target", cascade="all, delete-orphan")


class ConnectorRunCheckpoint(Base):
    __tablename__ = "connector_run_checkpoint"

    connector_run_checkpoint_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    phase: Mapped[str] = mapped_column(String(100), nullable=False)
    partition_cursor: Mapped[str | None] = mapped_column(String(255))
    page_offset: Mapped[int | None] = mapped_column(Integer)
    last_item_id: Mapped[str | None] = mapped_column(String(255))
    last_target_id: Mapped[str | None] = mapped_column(String(36))
    last_successful_stage: Mapped[str | None] = mapped_column(String(100))
    checkpoint_written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)

    connector_run: Mapped[ConnectorRun] = relationship(back_populates="checkpoints")


class ConnectorRunPartitionCursor(Base):
    __tablename__ = "connector_run_partition_cursor"
    __table_args__ = (UniqueConstraint("connector_run_id", "partition_id", name="uq_run_partition_cursor"),)

    connector_run_partition_cursor_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    partition_id: Mapped[str] = mapped_column(String(255), nullable=False)
    partition_type: Mapped[str] = mapped_column(String(100), nullable=False, default="query_partition")
    partition_bounds_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_offset: Mapped[int | None] = mapped_column(Integer)
    last_item_sort_key: Mapped[str | None] = mapped_column(String(255))
    last_page_link: Mapped[str | None] = mapped_column(String(1024))
    partition_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    connector_run: Mapped[ConnectorRun] = relationship(back_populates="partition_cursors")


class ConnectorRunEvent(Base):
    __tablename__ = "connector_run_event"

    connector_run_event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    connector_run_target_id: Mapped[str | None] = mapped_column(ForeignKey("connector_run_target.connector_run_target_id"))
    phase: Mapped[str | None] = mapped_column(String(100))
    stage: Mapped[str | None] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status_before: Mapped[str | None] = mapped_column(String(50))
    status_after: Mapped[str | None] = mapped_column(String(50))
    reason_code: Mapped[str | None] = mapped_column(String(255))
    error_class: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    connector_run: Mapped[ConnectorRun] = relationship(back_populates="events")
    connector_run_target: Mapped[ConnectorRunTarget | None] = relationship()


class ConnectorTargetStageAttempt(Base):
    __tablename__ = "connector_target_stage_attempt"

    connector_target_stage_attempt_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_target_id: Mapped[str] = mapped_column(ForeignKey("connector_run_target.connector_run_target_id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_class: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)

    connector_run_target: Mapped[ConnectorRunTarget] = relationship(back_populates="stage_attempts")


class ConnectorPolicySnapshot(Base, TimestampMixin):
    __tablename__ = "connector_policy_snapshot"

    connector_policy_snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    retry_matrix_json: Mapped[dict] = mapped_column(JSON, default=dict)

    connector_run: Mapped[ConnectorRun] = relationship(back_populates="policy_snapshots")


class ApsDialectCapability(Base, TimestampMixin):
    __tablename__ = "aps_dialect_capability"
    __table_args__ = (UniqueConstraint("subscription_key_hash", "api_host", "dialect", name="uq_aps_capability_key_host_dialect"),)

    aps_dialect_capability_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    subscription_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    api_host: Mapped[str] = mapped_column(String(255), nullable=False)
    dialect: Mapped[str] = mapped_column(String(64), nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_status: Mapped[int | None] = mapped_column(Integer)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_envelope_keys_json: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_count_keys_json: Mapped[list] = mapped_column(JSON, default=list)
    observed_page_cap: Mapped[int | None] = mapped_column(Integer)
    evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    notes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApsSyncCursor(Base, TimestampMixin):
    __tablename__ = "aps_sync_cursor"
    __table_args__ = (UniqueConstraint("source_system", "logical_query_fingerprint", name="uq_aps_sync_cursor_query"),)

    aps_sync_cursor_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False, default="nrc_adams_aps")
    logical_query_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    watermark_field: Mapped[str] = mapped_column(String(100), nullable=False, default="DateAddedTimestamp")
    last_watermark_iso: Mapped[str | None] = mapped_column(String(64))
    overlap_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=259200)
    last_run_connector_id: Mapped[str | None] = mapped_column(ForeignKey("connector_run.connector_run_id"))
    last_run_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reconciliation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciliation_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApsContentDocument(Base, TimestampMixin):
    __tablename__ = "aps_content_document"
    __table_args__ = (
        UniqueConstraint(
            "content_id",
            "content_contract_id",
            "chunking_contract_id",
            name="uq_aps_content_document_contract",
        ),
    )

    aps_content_document_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunking_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_contract_id: Mapped[str | None] = mapped_column(String(64))
    normalized_text_sha256: Mapped[str | None] = mapped_column(String(64))
    normalized_char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_status: Mapped[str] = mapped_column(String(64), nullable=False, default="indexed")
    media_type: Mapped[str | None] = mapped_column(String(128))
    document_class: Mapped[str | None] = mapped_column(String(64))
    quality_status: Mapped[str | None] = mapped_column(String(32))
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diagnostics_ref: Mapped[str | None] = mapped_column(String(1024))
    visual_page_refs_json: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApsContentChunk(Base, TimestampMixin):
    __tablename__ = "aps_content_chunk"
    __table_args__ = (
        UniqueConstraint(
            "content_id",
            "chunk_id",
            "content_contract_id",
            "chunking_contract_id",
            name="uq_aps_content_chunk_key",
        ),
    )

    aps_content_chunk_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunking_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chunk_text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    unit_kind: Mapped[str | None] = mapped_column(String(64))
    quality_status: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApsContentLinkage(Base, TimestampMixin):
    __tablename__ = "aps_content_linkage"
    __table_args__ = (
        UniqueConstraint(
            "content_id",
            "run_id",
            "target_id",
            "content_contract_id",
            "chunking_contract_id",
            name="uq_aps_content_linkage",
        ),
    )

    aps_content_linkage_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    target_id: Mapped[str] = mapped_column(ForeignKey("connector_run_target.connector_run_target_id"), nullable=False)
    accession_number: Mapped[str | None] = mapped_column(String(255))
    content_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunking_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_units_ref: Mapped[str | None] = mapped_column(String(1024))
    normalized_text_ref: Mapped[str | None] = mapped_column(String(1024))
    normalized_text_sha256: Mapped[str | None] = mapped_column(String(64))
    blob_ref: Mapped[str | None] = mapped_column(String(1024))
    blob_sha256: Mapped[str | None] = mapped_column(String(64))
    download_exchange_ref: Mapped[str | None] = mapped_column(String(1024))
    discovery_ref: Mapped[str | None] = mapped_column(String(1024))
    selection_ref: Mapped[str | None] = mapped_column(String(1024))
    diagnostics_ref: Mapped[str | None] = mapped_column(String(1024))

    connector_run: Mapped[ConnectorRun] = relationship()
    connector_run_target: Mapped[ConnectorRunTarget] = relationship()


class ApsRetrievalChunk(Base, TimestampMixin):
    __tablename__ = "aps_retrieval_chunk_v1"
    __table_args__ = (
        UniqueConstraint(
            "retrieval_contract_id",
            "run_id",
            "target_id",
            "content_id",
            "chunk_id",
            name="uq_aps_retrieval_chunk_v1_lookup",
        ),
    )

    aps_retrieval_chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("connector_run.connector_run_id"), nullable=False)
    target_id: Mapped[str] = mapped_column(ForeignKey("connector_run_target.connector_run_target_id"), nullable=False)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunking_contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_contract_id: Mapped[str | None] = mapped_column(String(64))
    accession_number: Mapped[str | None] = mapped_column(String(255))
    chunk_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chunk_text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_status: Mapped[str] = mapped_column(String(64), nullable=False, default="indexed")
    quality_status: Mapped[str | None] = mapped_column(String(32))
    document_class: Mapped[str | None] = mapped_column(String(64))
    media_type: Mapped[str | None] = mapped_column(String(128))
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_units_ref: Mapped[str | None] = mapped_column(String(1024))
    normalized_text_ref: Mapped[str | None] = mapped_column(String(1024))
    blob_ref: Mapped[str | None] = mapped_column(String(1024))
    download_exchange_ref: Mapped[str | None] = mapped_column(String(1024))
    discovery_ref: Mapped[str | None] = mapped_column(String(1024))
    selection_ref: Mapped[str | None] = mapped_column(String(1024))
    diagnostics_ref: Mapped[str | None] = mapped_column(String(1024))
    visual_page_refs_json: Mapped[str | None] = mapped_column(Text)
    source_signature_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rebuilt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    connector_run: Mapped[ConnectorRun] = relationship()
    connector_run_target: Mapped[ConnectorRunTarget] = relationship()


class ConnectorArtifactAlias(Base, TimestampMixin):
    __tablename__ = "connector_artifact_alias"

    connector_artifact_alias_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connector_run_target_id: Mapped[str] = mapped_column(ForeignKey("connector_run_target.connector_run_target_id"), nullable=False)
    alias_surface: Mapped[str] = mapped_column(String(50), nullable=False)
    alias_name: Mapped[str | None] = mapped_column(String(512))
    alias_url: Mapped[str | None] = mapped_column(String(1024))
    alias_checksum_type: Mapped[str | None] = mapped_column(String(100))
    alias_checksum_value: Mapped[str | None] = mapped_column(String(255))
    alias_json: Mapped[dict] = mapped_column(JSON, default=dict)

    connector_run_target: Mapped[ConnectorRunTarget] = relationship(back_populates="aliases")


class DatasetExternalIdentity(Base, TimestampMixin):
    __tablename__ = "dataset_external_identity"
    __table_args__ = (UniqueConstraint("source_system", "logical_dataset_key", name="uq_dataset_external_identity_key"),)

    dataset_external_identity_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.dataset_id"), nullable=False)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    logical_dataset_key: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    dataset: Mapped[Dataset] = relationship(back_populates="external_identities")


class DatasetSourceProvenance(Base, TimestampMixin):
    __tablename__ = "dataset_source_provenance"

    dataset_source_provenance_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    connector_run_id: Mapped[str | None] = mapped_column(ForeignKey("connector_run.connector_run_id"))
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(100), nullable=False)
    source_artifact_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    sciencebase_item_id: Mapped[str | None] = mapped_column(String(255))
    sciencebase_item_url: Mapped[str | None] = mapped_column(String(512))
    sciencebase_file_name: Mapped[str | None] = mapped_column(String(512))
    sciencebase_download_uri: Mapped[str | None] = mapped_column(String(1024))
    artifact_surface: Mapped[str | None] = mapped_column(String(50))
    artifact_locator_type: Mapped[str | None] = mapped_column(String(100))
    remote_checksum_type: Mapped[str | None] = mapped_column(String(100))
    remote_checksum_value: Mapped[str | None] = mapped_column(String(255))
    downloaded_sha256: Mapped[str | None] = mapped_column(String(64))
    raw_storage_ref: Mapped[str | None] = mapped_column(String(512))
    source_query_fingerprint: Mapped[str | None] = mapped_column(String(128))
    source_reference_json: Mapped[dict] = mapped_column(JSON, default=dict)
    fetch_policy_mode: Mapped[str | None] = mapped_column(String(100))
    resolved_ip: Mapped[str | None] = mapped_column(String(64))
    redirect_count: Mapped[int | None] = mapped_column(Integer)
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    retrieved_http_json: Mapped[dict] = mapped_column(JSON, default=dict)
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="source_provenance")
    connector_run: Mapped[ConnectorRun | None] = relationship(back_populates="source_provenance")


class DatasetRow(Base):
    __tablename__ = "dataset_row"
    __table_args__ = (UniqueConstraint("dataset_version_id", "row_number", name="uq_version_row_number"),)

    dataset_row_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    values_json: Mapped[dict] = mapped_column(JSON, default=dict)

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="rows")


class L3Session(Base):
    __tablename__ = "l3_session"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(status) for status in L3_SESSION_STATUS_VALUES)})",
            name="ck_l3_session_status",
        ),
    )

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, default=L3_SESSION_STATUS_ACTIVE_LOADING)
    selection_manifest_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entry_route_context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    manifests: Mapped[list["L3SelectionManifest"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    descriptors: Mapped[list["L3Descriptor"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    retrieval_events: Mapped[list["L3RetrievalEvent"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    material_snapshots: Mapped[list["L3MaterialSnapshot"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class L3SelectionManifest(Base):
    __tablename__ = "l3_selection_manifest"
    __table_args__ = (UniqueConstraint("session_id", name="uq_l3_selection_manifest_session"),)

    selection_manifest_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_plane_hints_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    selection_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    commit_reason: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[L3Session] = relationship(back_populates="manifests")
    descriptors: Mapped[list["L3Descriptor"]] = relationship(back_populates="selection_manifest", cascade="all, delete-orphan")


class L3GateBIdempotencyKey(Base):
    __tablename__ = "l3_gate_b_idempotency_key"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_gate_b_idempotency_client_request"),
        CheckConstraint(
            f"status IN ({', '.join(repr(status) for status in L3_GATE_B_IDEMPOTENCY_STATUS_VALUES)})",
            name="ck_l3_gate_b_idempotency_status",
        ),
        Index("ix_l3_gate_b_idempotency_session", "session_id"),
        Index("ix_l3_gate_b_idempotency_status", "status"),
    )

    gate_b_idempotency_key_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preflight_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_set_id: Mapped[str] = mapped_column(String(64), nullable=False)
    material_preview_id: Mapped[str] = mapped_column(String(64), nullable=False)
    material_preview_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_b_decision_manifest_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("l3_session.session_id"))
    selection_manifest_id: Mapped[str | None] = mapped_column(ForeignKey("l3_selection_manifest.selection_manifest_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session | None] = relationship()
    selection_manifest: Mapped[L3SelectionManifest | None] = relationship()


class L3Descriptor(Base):
    __tablename__ = "l3_descriptor"
    __table_args__ = (UniqueConstraint("session_id", "descriptor_hash", name="uq_l3_descriptor_session_hash"),)

    descriptor_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    selection_manifest_id: Mapped[str] = mapped_column(ForeignKey("l3_selection_manifest.selection_manifest_id"), nullable=False)
    source_plane: Mapped[str] = mapped_column(String(64), nullable=False)
    descriptor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    selector_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    selection_basis_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expansion_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="expanded")
    descriptor_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    session: Mapped[L3Session] = relationship(back_populates="descriptors")
    selection_manifest: Mapped[L3SelectionManifest] = relationship(back_populates="descriptors")
    retrieval_events: Mapped[list["L3RetrievalEvent"]] = relationship(back_populates="descriptor", cascade="all, delete-orphan")
    material_snapshots: Mapped[list["L3MaterialSnapshot"]] = relationship(back_populates="descriptor", cascade="all, delete-orphan")


class L3RetrievalEvent(Base):
    __tablename__ = "l3_retrieval_event"

    retrieval_event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    descriptor_id: Mapped[str] = mapped_column(ForeignKey("l3_descriptor.descriptor_id"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    material_snapshot_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship(back_populates="retrieval_events")
    descriptor: Mapped[L3Descriptor] = relationship(back_populates="retrieval_events")


class L3MaterialSnapshot(Base):
    __tablename__ = "l3_material_snapshot"

    material_snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    descriptor_id: Mapped[str] = mapped_column(ForeignKey("l3_descriptor.descriptor_id"), nullable=False)
    source_plane: Mapped[str] = mapped_column(String(64), nullable=False)
    source_shape: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_identity_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_provenance_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    co_retrieval_group_id: Mapped[str | None] = mapped_column(String(64))
    load_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship(back_populates="material_snapshots")
    descriptor: Mapped[L3Descriptor] = relationship(back_populates="material_snapshots")


class L3SecXbrlProjectionSet(Base):
    __tablename__ = "l3_sec_xbrl_projection_set"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_projection_set_client_request"),
        UniqueConstraint("projection_basis_hash", name="uq_l3_sec_xbrl_projection_set_basis_hash"),
        CheckConstraint(
            f"redaction_policy = '{L3_SEC_XBRL_PROJECTION_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_projection_set_redaction_policy",
        ),
        CheckConstraint(
            f"status = '{L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED}'",
            name="ck_l3_sec_xbrl_projection_set_status",
        ),
        Index("ix_l3_sec_xbrl_projection_set_dataset_version", "dataset_version_id"),
        Index("ix_l3_sec_xbrl_projection_set_source_report", "source_report_hash"),
    )

    sec_xbrl_projection_set_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    projection_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    projection_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_report_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_report_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version_id: Mapped[str | None] = mapped_column(String(36))
    sidecar_receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    value_store_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sector_family_presence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    period_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    projection_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    redaction_policy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    facts: Mapped[list["L3SecXbrlProjectionFact"]] = relationship(
        back_populates="projection_set",
        cascade="all, delete-orphan",
    )
    statement_packets: Mapped[list["L3SecXbrlStatementPacketSet"]] = relationship(back_populates="projection_set")


class L3SecXbrlProjectionFact(Base):
    __tablename__ = "l3_sec_xbrl_projection_fact"
    __table_args__ = (
        UniqueConstraint(
            "sec_xbrl_projection_set_id",
            "period_ref",
            "statement",
            "statement_row_index",
            name="uq_l3_sec_xbrl_projection_fact_statement_row",
        ),
        Index("ix_l3_sec_xbrl_projection_fact_set", "sec_xbrl_projection_set_id"),
        Index("ix_l3_sec_xbrl_projection_fact_canonical", "canonical_id"),
        Index("ix_l3_sec_xbrl_projection_fact_statement", "statement"),
        CheckConstraint(
            "value_redacted = true",
            name="ck_l3_sec_xbrl_projection_fact_value_redacted",
        ),
    )

    sec_xbrl_projection_fact_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    sec_xbrl_projection_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"),
        nullable=False,
    )
    period_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    period_index: Mapped[int] = mapped_column(Integer, nullable=False)
    statement: Mapped[str] = mapped_column(String(32), nullable=False)
    statement_row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(128), nullable=False)
    basis: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_qname: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    oracle_confirmed: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_method: Mapped[str | None] = mapped_column(String(128))
    mapping_confidence: Mapped[str | None] = mapped_column(String(128))
    unit_class: Mapped[str | None] = mapped_column(String(64))
    provenance_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    value_redacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    resolved_fact_provenance_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sidecar_receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    value_store_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    derived_from_concepts_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    projection_set: Mapped[L3SecXbrlProjectionSet] = relationship(back_populates="facts")
    statement_packet_rows: Mapped[list["L3SecXbrlStatementPacketRow"]] = relationship(back_populates="projection_fact")


class L3SecXbrlStatementPacketSet(Base):
    __tablename__ = "l3_sec_xbrl_statement_packet_set"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_statement_packet_set_client_request"),
        UniqueConstraint("packet_basis_hash", name="uq_l3_sec_xbrl_statement_packet_set_basis_hash"),
        CheckConstraint(
            f"value_policy = '{L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_statement_packet_set_value_policy",
        ),
        CheckConstraint(
            f"status = '{L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED}'",
            name="ck_l3_sec_xbrl_statement_packet_set_status",
        ),
        Index("ix_l3_sec_xbrl_statement_packet_set_projection", "sec_xbrl_projection_set_id"),
        Index("ix_l3_sec_xbrl_statement_packet_set_projection_basis", "source_projection_basis_hash"),
    )

    sec_xbrl_statement_packet_set_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    sec_xbrl_projection_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    packet_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    packet_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_projection_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_projection_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    statement_organization_authority: Mapped[str] = mapped_column(String(128), nullable=False)
    value_policy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
    )
    statement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_review_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    provenance_complete_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_exception_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    identity_rollup_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    organization_contract_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    packet_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    projection_set: Mapped[L3SecXbrlProjectionSet] = relationship(back_populates="statement_packets")
    statements: Mapped[list["L3SecXbrlStatementPacketStatement"]] = relationship(
        back_populates="packet_set",
        cascade="all, delete-orphan",
    )
    operator_review_workflows: Mapped[list["L3SecXbrlOperatorReviewWorkflow"]] = relationship(
        back_populates="statement_packet_set",
    )


class L3SecXbrlStatementPacketStatement(Base):
    __tablename__ = "l3_sec_xbrl_statement_packet_statement"
    __table_args__ = (
        UniqueConstraint(
            "sec_xbrl_statement_packet_set_id",
            "statement",
            name="uq_l3_sec_xbrl_statement_packet_statement_name",
        ),
        UniqueConstraint(
            "sec_xbrl_statement_packet_set_id",
            "statement_index",
            name="uq_l3_sec_xbrl_statement_packet_statement_index",
        ),
        Index("ix_l3_sec_xbrl_statement_packet_statement_set", "sec_xbrl_statement_packet_set_id"),
    )

    sec_xbrl_statement_packet_statement_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    sec_xbrl_statement_packet_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(String(32), nullable=False)
    statement_index: Mapped[int] = mapped_column(Integer, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    projected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    derived_count: Mapped[int] = mapped_column(Integer, nullable=False)
    provenance_complete_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_exception_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status_counts_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    family_counts_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    packet_set: Mapped[L3SecXbrlStatementPacketSet] = relationship(back_populates="statements")
    rows: Mapped[list["L3SecXbrlStatementPacketRow"]] = relationship(
        back_populates="packet_statement",
        cascade="all, delete-orphan",
    )


class L3SecXbrlStatementPacketRow(Base):
    __tablename__ = "l3_sec_xbrl_statement_packet_row"
    __table_args__ = (
        UniqueConstraint(
            "sec_xbrl_statement_packet_statement_id",
            "period_ref",
            "period_index",
            "statement_row_index",
            name="uq_l3_sec_xbrl_statement_packet_row_statement_period_index",
        ),
        Index("ix_l3_sec_xbrl_statement_packet_row_statement", "sec_xbrl_statement_packet_statement_id"),
        Index("ix_l3_sec_xbrl_statement_packet_row_projection_fact", "sec_xbrl_projection_fact_id"),
        Index("ix_l3_sec_xbrl_statement_packet_row_canonical", "canonical_id"),
        CheckConstraint(
            "value_redacted = true",
            name="ck_l3_sec_xbrl_statement_packet_row_value_redacted",
        ),
    )

    sec_xbrl_statement_packet_row_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    sec_xbrl_statement_packet_statement_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_statement_packet_statement.sec_xbrl_statement_packet_statement_id"),
        nullable=False,
    )
    sec_xbrl_projection_fact_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_projection_fact.sec_xbrl_projection_fact_id"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(String(32), nullable=False)
    statement_row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_index: Mapped[int] = mapped_column(Integer, nullable=False)
    period_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    period_index: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(128), nullable=False)
    basis: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_qname: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    oracle_confirmed: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_method: Mapped[str | None] = mapped_column(String(128))
    mapping_confidence: Mapped[str | None] = mapped_column(String(128))
    unit_class: Mapped[str | None] = mapped_column(String(64))
    provenance_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    value_redacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_exception: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    derived_from_concepts_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    packet_statement: Mapped[L3SecXbrlStatementPacketStatement] = relationship(back_populates="rows")
    projection_fact: Mapped[L3SecXbrlProjectionFact] = relationship(back_populates="statement_packet_rows")


class L3SecXbrlOperatorReviewWorkflow(Base):
    __tablename__ = "l3_sec_xbrl_operator_review_workflow"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_operator_review_workflow_client_request"),
        UniqueConstraint("workflow_basis_hash", name="uq_l3_sec_xbrl_operator_review_workflow_basis_hash"),
        CheckConstraint(
            f"redaction_policy = '{L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_operator_review_workflow_redaction_policy",
        ),
        CheckConstraint(
            f"control_mode = '{L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE}'",
            name="ck_l3_sec_xbrl_operator_review_workflow_control_mode",
        ),
        CheckConstraint(
            f"review_status = '{L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY}'",
            name="ck_l3_sec_xbrl_operator_review_workflow_status",
        ),
        Index("ix_l3_sec_xbrl_operator_review_workflow_packet", "sec_xbrl_statement_packet_set_id"),
        Index("ix_l3_sec_xbrl_operator_review_workflow_packet_basis", "statement_packet_basis_hash"),
    )

    sec_xbrl_operator_review_workflow_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    sec_xbrl_statement_packet_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    statement_packet_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_projection_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    control_mode: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
    )
    review_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
    )
    redaction_policy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
    )
    statement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_exception_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permitted_controls_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    blocked_controls_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authority_refs_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    review_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    statement_packet_set: Mapped[L3SecXbrlStatementPacketSet] = relationship(
        back_populates="operator_review_workflows",
    )
    operator_review_decisions: Mapped[list["L3SecXbrlOperatorReviewDecision"]] = relationship(
        back_populates="operator_review_workflow",
    )


class L3SecXbrlOperatorReviewDecision(Base):
    __tablename__ = "l3_sec_xbrl_operator_review_decision"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_operator_review_decision_client_request"),
        UniqueConstraint("decision_basis_hash", name="uq_l3_sec_xbrl_operator_review_decision_basis_hash"),
        UniqueConstraint(
            "sec_xbrl_operator_review_workflow_id",
            name="uq_l3_sec_xbrl_operator_review_decision_workflow",
        ),
        CheckConstraint(
            f"redaction_policy = '{L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_operator_review_decision_redaction_policy",
        ),
        CheckConstraint(
            f"decision_mode = '{L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_MODE}'",
            name="ck_l3_sec_xbrl_operator_review_decision_mode",
        ),
        CheckConstraint(
            f"decision_status = '{L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED}'",
            name="ck_l3_sec_xbrl_operator_review_decision_status",
        ),
        CheckConstraint(
            "review_decision IN ('approved', 'changes_requested', 'rejected', 'blocked')",
            name="ck_l3_sec_xbrl_operator_review_decision_value",
        ),
        CheckConstraint(
            "decision_reason_code IN ('ready_for_next_freeze', 'needs_packet_revision', 'authority_gap', 'redaction_gap', 'operator_blocked')",
            name="ck_l3_sec_xbrl_operator_review_decision_reason",
        ),
        Index("ix_l3_sec_xbrl_operator_review_decision_workflow", "sec_xbrl_operator_review_workflow_id"),
        Index("ix_l3_sec_xbrl_operator_review_decision_workflow_basis", "workflow_basis_hash"),
    )

    sec_xbrl_operator_review_decision_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    sec_xbrl_operator_review_workflow_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_operator_review_workflow.sec_xbrl_operator_review_workflow_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    statement_packet_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_projection_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_mode: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_MODE,
    )
    review_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED,
    )
    redaction_policy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_REDACTION_POLICY,
    )
    decision_reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_notes_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decision_notes_hash: Mapped[str | None] = mapped_column(String(64))
    decision_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    authority_refs_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    permitted_controls_after_decision_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    blocked_controls_after_decision_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    operator_review_workflow: Mapped[L3SecXbrlOperatorReviewWorkflow] = relationship(
        back_populates="operator_review_decisions",
    )
    value_reveal_authority_receipts: Mapped[list["L3SecXbrlValueRevealAuthorityReceipt"]] = relationship(
        back_populates="operator_review_decision",
    )


class L3SecXbrlValueRevealAuthorityReceipt(Base):
    __tablename__ = "l3_sec_xbrl_value_reveal_authority_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_value_reveal_authority_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_sec_xbrl_value_reveal_authority_basis_hash"),
        UniqueConstraint(
            "sec_xbrl_operator_review_decision_id",
            name="uq_l3_sec_xbrl_value_reveal_authority_decision",
        ),
        CheckConstraint(
            f"authority_state = '{L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY}'",
            name="ck_l3_sec_xbrl_value_reveal_authority_state",
        ),
        CheckConstraint(
            f"authority_policy_id = '{L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID}'",
            name="ck_l3_sec_xbrl_value_reveal_authority_policy",
        ),
        CheckConstraint(
            f"redaction_policy = '{L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_value_reveal_authority_redaction",
        ),
        Index("ix_l3_sec_xbrl_value_reveal_authority_decision", "sec_xbrl_operator_review_decision_id"),
        Index("ix_l3_sec_xbrl_value_reveal_authority_basis", "authority_basis_hash"),
        Index("ix_l3_sec_xbrl_value_reveal_authority_dataset", "dataset_version_id"),
        Index("ix_l3_sec_xbrl_value_reveal_authority_sidecar", "sidecar_receipt_hash"),
        Index("ix_l3_sec_xbrl_value_reveal_authority_projection_basis", "projection_basis_hash"),
    )

    sec_xbrl_value_reveal_authority_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sec_xbrl_operator_review_decision_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_operator_review_decision.sec_xbrl_operator_review_decision_id"),
        nullable=False,
    )
    decision_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_operator_review_workflow_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_operator_review_workflow.sec_xbrl_operator_review_workflow_id"),
        nullable=False,
    )
    workflow_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_statement_packet_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"),
        nullable=False,
    )
    statement_packet_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_projection_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"),
        nullable=False,
    )
    projection_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    dataset_version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sidecar_receipt_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sidecar_receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    value_store_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
    )
    authority_policy_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
    )
    redaction_policy: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
    )
    operator_actor_hash: Mapped[str | None] = mapped_column(String(64))
    authority_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    negative_invariants_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    operator_review_decision: Mapped[L3SecXbrlOperatorReviewDecision] = relationship(
        back_populates="value_reveal_authority_receipts",
    )
    controlled_value_reveal_submit_receipts: Mapped[list["L3SecXbrlControlledValueRevealSubmitReceipt"]] = relationship(
        back_populates="value_reveal_authority_receipt",
    )


class L3SecXbrlControlledValueRevealSubmitReceipt(Base):
    __tablename__ = "l3_sec_xbrl_controlled_value_reveal_submit_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id_hash", name="uq_l3_sec_xbrl_controlled_value_reveal_client_request"),
        UniqueConstraint("submit_basis_hash", name="uq_l3_sec_xbrl_controlled_value_reveal_basis_hash"),
        CheckConstraint(
            f"submit_state = '{L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY}'",
            name="ck_l3_sec_xbrl_controlled_value_reveal_state",
        ),
        CheckConstraint(
            f"submit_policy_id = '{L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_POLICY_ID}'",
            name="ck_l3_sec_xbrl_controlled_value_reveal_policy",
        ),
        CheckConstraint(
            f"redaction_policy = '{L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_controlled_value_reveal_redaction",
        ),
        Index(
            "ix_l3_sec_xbrl_controlled_value_reveal_authority",
            "sec_xbrl_value_reveal_authority_receipt_id",
        ),
        Index("ix_l3_sec_xbrl_controlled_value_reveal_basis", "submit_basis_hash"),
        Index("ix_l3_sec_xbrl_controlled_value_reveal_projection", "projection_basis_hash"),
        Index("ix_l3_sec_xbrl_controlled_value_reveal_dataset", "dataset_version_id"),
    )

    sec_xbrl_controlled_value_reveal_submit_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_request_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    submit_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    submit_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sec_xbrl_value_reveal_authority_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_value_reveal_authority_receipt.sec_xbrl_value_reveal_authority_receipt_id"),
        nullable=False,
    )
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_operator_review_decision_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_operator_review_decision.sec_xbrl_operator_review_decision_id"),
        nullable=False,
    )
    decision_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_operator_review_workflow_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_operator_review_workflow.sec_xbrl_operator_review_workflow_id"),
        nullable=False,
    )
    workflow_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_statement_packet_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"),
        nullable=False,
    )
    statement_packet_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sec_xbrl_projection_set_id: Mapped[str] = mapped_column(
        ForeignKey("l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"),
        nullable=False,
    )
    projection_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_version.dataset_version_id"), nullable=False)
    dataset_version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sidecar_receipt_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sidecar_receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    value_store_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    submit_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
    )
    submit_policy_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_POLICY_ID,
    )
    redaction_policy: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_REDACTION_POLICY,
    )
    revealed_fact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    value_redacted_fact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fact_inventory_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    value_inventory_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_inventory_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    submit_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    negative_invariants_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    value_reveal_authority_receipt: Mapped[L3SecXbrlValueRevealAuthorityReceipt] = relationship(
        back_populates="controlled_value_reveal_submit_receipts",
    )
    operator_review_decision: Mapped[L3SecXbrlOperatorReviewDecision] = relationship()


class L3SecXbrlAuthBindingReceipt(Base):
    __tablename__ = "l3_sec_xbrl_auth_binding_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_auth_binding_client_request"),
        UniqueConstraint("binding_basis_hash", name="uq_l3_sec_xbrl_auth_binding_basis_hash"),
        UniqueConstraint(
            "source_receipt_kind",
            "source_receipt_id",
            "route_family",
            "actor_ref_hash",
            "workspace_ref_hash",
            "role",
            name="uq_l3_sec_xbrl_auth_binding_source_route_actor_role",
        ),
        CheckConstraint(
            f"binding_policy_id = '{L3_SEC_XBRL_AUTH_BINDING_POLICY_ID}'",
            name="ck_l3_sec_xbrl_auth_binding_policy",
        ),
        CheckConstraint(
            f"binding_state = '{L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND}'",
            name="ck_l3_sec_xbrl_auth_binding_state",
        ),
        CheckConstraint(
            f"redaction_policy = '{L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY}'",
            name="ck_l3_sec_xbrl_auth_binding_redaction",
        ),
        CheckConstraint(
            "source_receipt_kind IN ('operator_review_workflow', 'operator_review_decision', 'value_reveal_authority', 'controlled_value_reveal_submit')",
            name="ck_l3_sec_xbrl_auth_binding_source_kind",
        ),
        CheckConstraint(
            "route_family IN ('sec_xbrl_operator_review_workflow_open_write', 'sec_xbrl_operator_review_workflow_status_read', 'sec_xbrl_operator_review_decision_submit_write', 'sec_xbrl_operator_review_decision_status_read', 'sec_xbrl_value_reveal_authority_prepare_write', 'sec_xbrl_controlled_value_reveal_submit_write', 'sec_xbrl_controlled_value_reveal_submit_status_read')",
            name="ck_l3_sec_xbrl_auth_binding_route_family",
        ),
        CheckConstraint("role IN ('owner', 'auditor')", name="ck_l3_sec_xbrl_auth_binding_role"),
        Index("ix_l3_sec_xbrl_auth_binding_source_basis", "source_receipt_kind", "source_receipt_basis_hash"),
        Index("ix_l3_sec_xbrl_auth_binding_actor_workspace", "actor_ref_hash", "workspace_ref_hash"),
        Index("ix_l3_sec_xbrl_auth_binding_policy", "policy_hash"),
        Index("ix_l3_sec_xbrl_auth_binding_route_family", "route_family"),
    )

    sec_xbrl_auth_binding_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    binding_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    binding_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    binding_policy_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=L3_SEC_XBRL_AUTH_BINDING_POLICY_ID,
    )
    binding_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND,
    )
    source_receipt_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_receipt_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_receipt_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    route_family: Mapped[str] = mapped_column(String(96), nullable=False)
    actor_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    redaction_policy: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY,
    )
    binding_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    negative_invariants_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3TypingRecord(Base, TimestampMixin):
    __tablename__ = "l3_typing_record"
    __table_args__ = (UniqueConstraint("material_snapshot_id", name="uq_l3_typing_record_material_snapshot"),)

    typing_record_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    material_snapshot_id: Mapped[str] = mapped_column(ForeignKey("l3_material_snapshot.material_snapshot_id"), nullable=False)
    candidate_modalities_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    chosen_modality: Mapped[str] = mapped_column(String(64), nullable=False)
    typing_basis_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    overridden_by_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text)

    session: Mapped[L3Session] = relationship()
    material_snapshot: Mapped[L3MaterialSnapshot] = relationship()


class L3AnalysisUnit(Base, TimestampMixin):
    __tablename__ = "l3_analysis_unit"
    __table_args__ = (UniqueConstraint("session_id", "unit_hash", name="uq_l3_analysis_unit_session_hash"),)

    analysis_unit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    unit_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_modality: Mapped[str] = mapped_column(String(64), nullable=False)
    member_snapshot_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    member_ranges_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    must_remain_intact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    typing_record_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    derived_view_ref: Mapped[str | None] = mapped_column(String(1024))
    unit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship()


class L3AnalysisGroup(Base):
    __tablename__ = "l3_analysis_group"

    analysis_group_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_modality: Mapped[str] = mapped_column(String(64), nullable=False)
    typing_basis_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analysis_unit_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(64), nullable=False)

    session: Mapped[L3Session] = relationship()


class L3AnalysisSet(Base, TimestampMixin):
    __tablename__ = "l3_analysis_set"

    analysis_set_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_group_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    analysis_unit_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    set_type: Mapped[str] = mapped_column(String(64), nullable=False)
    formation_basis_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship()


class L3AnalysisPlan(Base, TimestampMixin):
    __tablename__ = "l3_analysis_plan"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(status) for status in L3_ANALYSIS_PLAN_STATUS_VALUES)})",
            name="ck_l3_analysis_plan_status",
        ),
    )

    analysis_plan_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_set_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default=L3_ANALYSIS_PLAN_STATUS_FORMED)
    approved_by_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship()


class L3PassRun(Base, TimestampMixin):
    __tablename__ = "l3_pass_run"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(status) for status in L3_PASS_RUN_STATUS_VALUES)})",
            name="ck_l3_pass_run_status",
        ),
    )

    pass_run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_plan_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_plan.analysis_plan_id"), nullable=False)
    analysis_set_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_set.analysis_set_id"), nullable=False)
    pass_type: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_family: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_payload_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    output_payload_ref: Mapped[str | None] = mapped_column(String(1024))
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship()
    analysis_plan: Mapped[L3AnalysisPlan] = relationship()
    analysis_set: Mapped[L3AnalysisSet] = relationship()


class L3ReconciliationRecord(Base, TimestampMixin):
    __tablename__ = "l3_reconciliation_record"
    __table_args__ = (UniqueConstraint("session_id", name="uq_l3_reconciliation_record_session"),)

    reconciliation_record_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship()


class L3OutputPackage(Base, TimestampMixin):
    __tablename__ = "l3_output_package"
    __table_args__ = (UniqueConstraint("session_id", "package_kind", name="uq_l3_output_package_session_kind"),)

    output_package_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    package_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[L3Session] = relationship()
    reconciliation_record: Mapped[L3ReconciliationRecord] = relationship()


class L3ReplacementPackageSetAuthority(Base):
    __tablename__ = "l3_replacement_package_set_authority"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_replacement_package_set_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_replacement_package_set_basis_hash"),
        CheckConstraint(
            "operator_decision = 'record_replacement_package_set_authority'",
            name="ck_l3_replacement_package_set_operator_decision",
        ),
        Index("ix_l3_replacement_package_set_session", "session_id"),
        Index("ix_l3_replacement_package_set_reconciliation", "reconciliation_record_id"),
    )

    replacement_package_set_authority_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_plan_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_plan.analysis_plan_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    source_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_package_set_id: Mapped[str] = mapped_column(String(128), nullable=False)
    replacement_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    analysis_plan: Mapped[L3AnalysisPlan] = relationship()
    pass_run: Mapped[L3PassRun] = relationship()
    reconciliation_record: Mapped[L3ReconciliationRecord] = relationship()


class L3PackageSupersessionCommit(Base):
    __tablename__ = "l3_package_supersession_commit"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_package_supersession_commit_client_request"),
        UniqueConstraint("commit_basis_hash", name="uq_l3_package_supersession_commit_basis_hash"),
        CheckConstraint(
            "operator_decision = 'commit_package_supersession'",
            name="ck_l3_package_supersession_commit_operator_decision",
        ),
        CheckConstraint("status = 'committed'", name="ck_l3_package_supersession_commit_status"),
        Index("ix_l3_package_supersession_commit_session", "session_id"),
        Index("ix_l3_package_supersession_commit_reconciliation", "reconciliation_record_id"),
        Index(
            "ix_l3_package_supersession_commit_replacement_authority",
            "replacement_package_set_authority_id",
        ),
    )

    package_supersession_commit_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_plan_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_plan.analysis_plan_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    replacement_package_set_authority_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_set_authority.replacement_package_set_authority_id"),
        nullable=False,
    )
    package_supersession_preview_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_package_set_id: Mapped[str] = mapped_column(String(128), nullable=False)
    replacement_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    downstream_dependency_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="committed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    analysis_plan: Mapped[L3AnalysisPlan] = relationship()
    pass_run: Mapped[L3PassRun] = relationship()
    reconciliation_record: Mapped[L3ReconciliationRecord] = relationship()
    replacement_package_set_authority: Mapped[L3ReplacementPackageSetAuthority] = relationship()


class L3ReplacementPackageArtifactMaterialization(Base):
    __tablename__ = "l3_replacement_package_artifact_materialization"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_replacement_artifact_materialization_client_request"),
        UniqueConstraint("materialization_basis_hash", name="uq_l3_replacement_artifact_materialization_basis_hash"),
        CheckConstraint(
            "operator_decision = 'materialize_replacement_package_artifacts_from_supersession_preview'",
            name="ck_l3_replacement_artifact_materialization_operator_decision",
        ),
        CheckConstraint("status = 'materialized'", name="ck_l3_replacement_artifact_materialization_status"),
        Index("ix_l3_replacement_artifact_materialization_session", "session_id"),
        Index("ix_l3_replacement_artifact_materialization_reconciliation", "reconciliation_record_id"),
        Index("ix_l3_replacement_artifact_materialization_preview", "package_supersession_preview_hash"),
    )

    replacement_artifact_materialization_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_plan_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_plan.analysis_plan_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    package_supersession_preview_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_package_set_id: Mapped[str] = mapped_column(String(128), nullable=False)
    replacement_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    materialization_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    materialization_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_decision: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="materialized")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    analysis_plan: Mapped[L3AnalysisPlan] = relationship()
    pass_run: Mapped[L3PassRun] = relationship()
    reconciliation_record: Mapped[L3ReconciliationRecord] = relationship()


class L3ReplacementPackageArtifactManifest(Base):
    __tablename__ = "l3_replacement_package_artifact_manifest"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_replacement_artifact_manifest_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_replacement_artifact_manifest_basis_hash"),
        CheckConstraint(
            "operator_decision = 'record_replacement_package_artifact_manifest'",
            name="ck_l3_replacement_artifact_manifest_operator_decision",
        ),
        CheckConstraint("status = 'verified'", name="ck_l3_replacement_artifact_manifest_status"),
        Index("ix_l3_replacement_artifact_manifest_session", "session_id"),
        Index("ix_l3_replacement_artifact_manifest_reconciliation", "reconciliation_record_id"),
        Index(
            "ix_l3_replacement_artifact_manifest_replacement_authority",
            "replacement_package_set_authority_id",
        ),
        Index("ix_l3_replacement_artifact_manifest_supersession_commit", "package_supersession_commit_id"),
    )

    replacement_package_artifact_manifest_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_plan_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_plan.analysis_plan_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    replacement_package_set_authority_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_set_authority.replacement_package_set_authority_id"),
        nullable=False,
    )
    package_supersession_commit_id: Mapped[str] = mapped_column(
        ForeignKey("l3_package_supersession_commit.package_supersession_commit_id"),
        nullable=False,
    )
    replacement_authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    package_supersession_commit_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_package_set_id: Mapped[str] = mapped_column(String(128), nullable=False)
    replacement_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    verified_artifact_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    verified_artifact_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    verified_artifact_byte_sizes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    hash_algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_namespace: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="verified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    analysis_plan: Mapped[L3AnalysisPlan] = relationship()
    pass_run: Mapped[L3PassRun] = relationship()
    reconciliation_record: Mapped[L3ReconciliationRecord] = relationship()
    replacement_package_set_authority: Mapped[L3ReplacementPackageSetAuthority] = relationship()
    package_supersession_commit: Mapped[L3PackageSupersessionCommit] = relationship()


class L3CorrectedPackageArtifactSet(Base):
    __tablename__ = "l3_corrected_package_artifact_set"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_corrected_artifact_set_client_request"),
        UniqueConstraint("corrected_artifact_basis_hash", name="uq_l3_corrected_artifact_set_basis_hash"),
        CheckConstraint(
            "operator_decision = 'record_corrected_package_artifact_set_from_review_corrections'",
            name="ck_l3_corrected_artifact_set_operator_decision",
        ),
        CheckConstraint("status = 'recorded'", name="ck_l3_corrected_artifact_set_status"),
        Index("ix_l3_corrected_artifact_set_session", "session_id"),
        Index("ix_l3_corrected_artifact_set_reconciliation", "reconciliation_record_id"),
        Index("ix_l3_corrected_artifact_set_materialization", "replacement_artifact_materialization_id"),
    )

    corrected_package_artifact_set_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    analysis_plan_id: Mapped[str] = mapped_column(ForeignKey("l3_analysis_plan.analysis_plan_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    replacement_artifact_materialization_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_artifact_materialization.replacement_artifact_materialization_id"),
        nullable=False,
    )
    materialization_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    result_review_record_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    reviewed_output_items_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    package_review_preview_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    corrected_package_set_id: Mapped[str] = mapped_column(String(128), nullable=False)
    corrected_package_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    corrected_package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    corrected_artifact_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    corrected_artifact_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    corrected_artifact_byte_sizes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    artifact_namespace: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    corrected_artifact_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_history_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_decision: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    analysis_plan: Mapped[L3AnalysisPlan] = relationship()
    pass_run: Mapped[L3PassRun] = relationship()
    reconciliation_record: Mapped[L3ReconciliationRecord] = relationship()
    replacement_artifact_materialization: Mapped[L3ReplacementPackageArtifactMaterialization] = relationship()


class L3ReplacementOutputPackage(Base):
    __tablename__ = "l3_replacement_output_package"
    __table_args__ = (
        UniqueConstraint(
            "replacement_artifact_manifest_id",
            "package_kind",
            name="uq_l3_replacement_output_package_manifest_kind",
        ),
        UniqueConstraint("client_request_id", name="uq_l3_replacement_output_package_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_replacement_output_package_basis_hash"),
        CheckConstraint(
            "operator_decision = 'record_replacement_package_namespace'",
            name="ck_l3_replacement_output_package_operator_decision",
        ),
        CheckConstraint("status = 'recorded'", name="ck_l3_replacement_output_package_status"),
        Index("ix_l3_replacement_output_package_session", "session_id"),
        Index("ix_l3_replacement_output_package_source", "source_output_package_id"),
        Index("ix_l3_replacement_output_package_manifest", "replacement_artifact_manifest_id"),
        Index("ix_l3_replacement_output_package_replacement_set", "replacement_package_set_authority_id"),
        Index("ix_l3_replacement_output_package_supersession_commit", "package_supersession_commit_id"),
        Index("ix_l3_replacement_output_package_kind", "package_kind"),
    )

    replacement_output_package_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    source_output_package_id: Mapped[str] = mapped_column(
        ForeignKey("l3_output_package.output_package_id"),
        nullable=False,
    )
    replacement_artifact_manifest_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_artifact_manifest.replacement_package_artifact_manifest_id"),
        nullable=False,
    )
    replacement_package_set_authority_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_set_authority.replacement_package_set_authority_id"),
        nullable=False,
    )
    package_supersession_commit_id: Mapped[str] = mapped_column(
        ForeignKey("l3_package_supersession_commit.package_supersession_commit_id"),
        nullable=False,
    )
    package_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    package_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operator_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="recorded")
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    source_output_package: Mapped[L3OutputPackage] = relationship()
    replacement_artifact_manifest: Mapped[L3ReplacementPackageArtifactManifest] = relationship()
    replacement_package_set_authority: Mapped[L3ReplacementPackageSetAuthority] = relationship()
    package_supersession_commit: Mapped[L3PackageSupersessionCommit] = relationship()


class L3PackageReplacementActivation(Base):
    __tablename__ = "l3_package_replacement_activation"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_package_replacement_activation_client_request"),
        UniqueConstraint(
            "replacement_activation_basis_hash",
            name="uq_l3_package_replacement_activation_basis_hash",
        ),
        UniqueConstraint("session_id", name="uq_l3_package_replacement_activation_session"),
        CheckConstraint(
            "operator_decision = 'activate_replacement_output_package_namespace'",
            name="ck_l3_package_replacement_activation_operator_decision",
        ),
        CheckConstraint("status = 'activated'", name="ck_l3_package_replacement_activation_status"),
        Index("ix_l3_package_replacement_activation_manifest", "replacement_artifact_manifest_id"),
        Index("ix_l3_package_replacement_activation_replacement_set", "replacement_package_set_authority_id"),
        Index("ix_l3_package_replacement_activation_supersession_commit", "package_supersession_commit_id"),
    )

    package_replacement_activation_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    replacement_artifact_manifest_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_artifact_manifest.replacement_package_artifact_manifest_id"),
        nullable=False,
    )
    replacement_package_set_authority_id: Mapped[str] = mapped_column(
        ForeignKey("l3_replacement_package_set_authority.replacement_package_set_authority_id"),
        nullable=False,
    )
    package_supersession_commit_id: Mapped[str] = mapped_column(
        ForeignKey("l3_package_supersession_commit.package_supersession_commit_id"),
        nullable=False,
    )
    replacement_output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    active_artifact_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    active_artifact_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    replacement_activation_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    activation_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    operator_decision: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="activated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped[L3Session] = relationship()
    replacement_artifact_manifest: Mapped[L3ReplacementPackageArtifactManifest] = relationship()
    replacement_package_set_authority: Mapped[L3ReplacementPackageSetAuthority] = relationship()
    package_supersession_commit: Mapped[L3PackageSupersessionCommit] = relationship()


class L3SourceIntakeRecord(Base):
    __tablename__ = "l3_source_intake_record"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_source_intake_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_source_intake_authority_basis"),
        CheckConstraint(
            "operator_decision = 'record_operator_uploaded_source'",
            name="ck_l3_source_intake_operator_decision",
        ),
        CheckConstraint("status IN ('recorded', 'already_recorded')", name="ck_l3_source_intake_status"),
        Index("ix_l3_source_intake_content_sha256", "content_sha256"),
        Index("ix_l3_source_intake_source_family", "source_family"),
        Index("ix_l3_source_intake_status", "status"),
    )

    source_intake_record_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operator_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_description: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(128))
    content_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    freshness_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provenance_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    downstream_eligibility_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ConnectorSourceIntakeRecord(Base):
    __tablename__ = "l3_connector_source_intake_record"
    __table_args__ = (
        UniqueConstraint(
            "client_request_id",
            name="uq_l3_connector_source_intake_client_request",
        ),
        UniqueConstraint(
            "authority_basis_hash",
            name="uq_l3_connector_source_intake_authority_basis",
        ),
        CheckConstraint(
            "operator_decision = 'record_connector_produced_source'",
            name="ck_l3_connector_source_intake_operator_decision",
        ),
        CheckConstraint(
            "status IN ('recorded', 'already_recorded')",
            name="ck_l3_connector_source_intake_status",
        ),
        CheckConstraint(
            "(identity_metadata_hash_version IS NULL AND identity_metadata_hash IS NULL)"
            " OR (identity_metadata_hash_version IS NOT NULL AND identity_metadata_hash IS NOT NULL)",
            name="ck_l3_connector_source_intake_identity_metadata_joint_null",
        ),
        Index("ix_l3_connector_source_intake_content_sha256", "content_sha256"),
        Index(
            "ix_l3_connector_intake_material_identity",
            "identity_metadata_hash_version",
            "source_family",
            "content_sha256",
            "identity_metadata_hash",
        ),
        Index("ix_l3_connector_source_intake_source_family", "source_family"),
        Index("ix_l3_connector_source_intake_status", "status"),
        Index("ix_l3_connector_source_intake_run_target", "connector_run_target_id"),
    )

    connector_source_intake_record_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operator_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_description: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(128))
    content_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_metadata_hash_version: Mapped[str | None] = mapped_column(String(64))
    identity_metadata_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    freshness_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provenance_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    downstream_eligibility_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False)
    connector_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    connector_run_target_id: Mapped[str] = mapped_column(String(36), nullable=False)


class L3ConnectorPromotionReceipt(Base):
    __tablename__ = "l3_connector_promotion_receipt"
    __table_args__ = (
        UniqueConstraint(
            "identity_metadata_hash_version",
            "source_family",
            "content_sha256",
            "identity_metadata_hash",
            name="uq_l3_connector_promotion_identity_tuple",
        ),
        UniqueConstraint(
            "canonical_identity_key_hash",
            name="uq_l3_connector_promotion_canonical_identity",
        ),
        CheckConstraint(
            "receipt_schema_version = 'layer3.connector_promotion_receipt.v1'",
            name="ck_l3_connector_promotion_receipt_schema",
        ),
        Index("ix_l3_connector_promotion_intake", "connector_source_intake_record_id"),
        Index("ix_l3_connector_promotion_gate_b_session", "gate_b_session_id"),
        Index("ix_l3_connector_promotion_selection_manifest", "gate_b_selection_manifest_id"),
        Index("ix_l3_connector_promotion_material_snapshot", "gate_b_material_snapshot_id"),
    )

    connector_promotion_receipt_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    receipt_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_metadata_hash_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_family: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_metadata_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_identity_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_source_intake_record_id: Mapped[str] = mapped_column(
        ForeignKey(
            "l3_connector_source_intake_record.connector_source_intake_record_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    gate_b_session_id: Mapped[str] = mapped_column(
        ForeignKey("l3_session.session_id", ondelete="RESTRICT"), nullable=False
    )
    gate_b_selection_manifest_id: Mapped[str] = mapped_column(
        ForeignKey("l3_selection_manifest.selection_manifest_id", ondelete="RESTRICT"), nullable=False
    )
    gate_b_material_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("l3_material_snapshot.material_snapshot_id", ondelete="RESTRICT"), nullable=False
    )
    gate_b_decision_manifest_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_b_decision_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    material_preview_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    promotion_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class L3SourceDirectoryIngestionBatch(Base):
    __tablename__ = "l3_source_directory_ingestion_batch"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_source_directory_batch_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_source_directory_batch_authority_basis"),
        UniqueConstraint("directory_fingerprint_hash", name="uq_l3_source_directory_batch_fingerprint"),
        CheckConstraint(
            "source_family = 'server_configured_operator_directory_text_table_source_family'",
            name="ck_l3_source_directory_batch_source_family",
        ),
        CheckConstraint(
            "ingestion_mode = 'server_configured_operator_directory_text_table_ingestion'",
            name="ck_l3_source_directory_batch_ingestion_mode",
        ),
        CheckConstraint("status IN ('recorded', 'already_recorded')", name="ck_l3_source_directory_batch_status"),
        Index("ix_l3_source_directory_batch_source_family", "source_family"),
        Index("ix_l3_source_directory_batch_status", "status"),
    )

    source_ingestion_batch_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_family: Mapped[str] = mapped_column(String(96), nullable=False)
    ingestion_mode: Mapped[str] = mapped_column(String(96), nullable=False)
    config_authority: Mapped[str] = mapped_column(String(96), nullable=False)
    directory_fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    eligible_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3SourceDirectoryIngestionFile(Base):
    __tablename__ = "l3_source_directory_ingestion_file"
    __table_args__ = (
        UniqueConstraint(
            "source_ingestion_batch_id",
            "relative_name",
            name="uq_l3_source_directory_file_batch_relative_name",
        ),
        UniqueConstraint("authority_basis_hash", name="uq_l3_source_directory_file_authority_basis"),
        CheckConstraint("status = 'recorded'", name="ck_l3_source_directory_file_status"),
        Index("ix_l3_source_directory_file_batch", "source_ingestion_batch_id"),
        Index("ix_l3_source_directory_file_extension", "extension"),
        Index("ix_l3_source_directory_file_sha256", "content_sha256"),
    )

    source_ingestion_file_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_ingestion_batch_id: Mapped[str] = mapped_column(
        ForeignKey("l3_source_directory_ingestion_batch.source_ingestion_batch_id"),
        nullable=False,
    )
    relative_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    content_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mtime_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    batch: Mapped[L3SourceDirectoryIngestionBatch] = relationship()


class L3SignedReferenceToken(Base):
    __tablename__ = "l3_signed_reference_token"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_l3_signed_reference_token_hash"),
        UniqueConstraint("request_basis_hash", name="uq_l3_signed_reference_request_basis"),
        Index("ix_l3_signed_reference_token_session", "session_id"),
        Index("ix_l3_signed_reference_token_reconciliation", "reconciliation_record_id"),
        Index("ix_l3_signed_reference_token_state_expiry", "state", "expires_at"),
    )

    signed_reference_token_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    replay_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="single_use")
    max_use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authority_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class L3SignedReferenceReceipt(Base):
    __tablename__ = "l3_signed_reference_receipt"
    __table_args__ = (Index("ix_l3_signed_reference_receipt_token", "signed_reference_token_id"),)

    signed_reference_receipt_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    signed_reference_token_id: Mapped[str] = mapped_column(
        ForeignKey("l3_signed_reference_token.signed_reference_token_id"),
        nullable=False,
    )
    receipt_type: Mapped[str] = mapped_column(String(32), nullable=False)
    receipt_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(String(1024))
    artifact_hash: Mapped[str | None] = mapped_column(String(64))
    artifact_size_bytes: Mapped[int | None] = mapped_column(Integer)
    receipt_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3SignedReferenceRevocation(Base):
    __tablename__ = "l3_signed_reference_revocation"
    __table_args__ = (
        UniqueConstraint("signed_reference_token_id", "idempotency_key", name="uq_l3_signed_reference_revoke_token_key"),
        Index("ix_l3_signed_reference_revocation_token", "signed_reference_token_id"),
    )

    signed_reference_revocation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    signed_reference_token_id: Mapped[str] = mapped_column(
        ForeignKey("l3_signed_reference_token.signed_reference_token_id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_by: Mapped[str] = mapped_column(String(255), nullable=False)
    revocation_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    revocation_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3SignedReferenceAuditEvent(Base):
    __tablename__ = "l3_signed_reference_audit_event"
    __table_args__ = (
        Index("ix_l3_signed_reference_audit_token", "signed_reference_token_id"),
        Index("ix_l3_signed_reference_audit_type_created", "event_type", "created_at"),
    )

    signed_reference_audit_event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    signed_reference_token_id: Mapped[str | None] = mapped_column(
        ForeignKey("l3_signed_reference_token.signed_reference_token_id"),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPrivateSignedUrlObjectAuthority(Base):
    __tablename__ = "l3_provider_private_signed_url_object_authority"
    __table_args__ = (
        UniqueConstraint("authority_hash", name="uq_l3_provider_private_signed_url_authority_hash"),
        Index("ix_l3_provider_private_signed_url_authority_session", "session_id"),
        Index("ix_l3_provider_private_signed_url_authority_reconciliation", "reconciliation_record_id"),
    )

    provider_private_signed_url_object_authority_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    export_download_descriptor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    source_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provider_object_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPrivateSignedUrlReceipt(Base):
    __tablename__ = "l3_provider_private_signed_url_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_provider_private_signed_url_receipt_client_request"),
        UniqueConstraint("request_basis_hash", name="uq_l3_provider_private_signed_url_receipt_request_basis"),
        UniqueConstraint("provider_private_signed_url_token_hash", name="uq_l3_provider_private_signed_url_token_hash"),
        Index("ix_l3_provider_private_signed_url_receipt_authority", "provider_private_signed_url_object_authority_id"),
        Index("ix_l3_provider_private_signed_url_receipt_state_expiry", "provider_private_signed_url_state", "provider_private_signed_url_expires_at"),
    )

    provider_private_signed_url_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_private_signed_url_object_authority_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_private_signed_url_object_authority.provider_private_signed_url_object_authority_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_private_signed_url_state: Mapped[str] = mapped_column(String(64), nullable=False, default="provider_private_signed_url_prepared")
    provider_private_signed_url_replay_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="single_use")
    provider_private_signed_url_max_use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    provider_private_signed_url_use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_private_signed_url_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_private_signed_url_token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_private_signed_url_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authority_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class L3ProviderPrivateSignedUrlRevocation(Base):
    __tablename__ = "l3_provider_private_signed_url_revocation"
    __table_args__ = (
        UniqueConstraint(
            "provider_private_signed_url_receipt_id",
            "idempotency_key",
            name="uq_l3_provider_private_signed_url_revoke_receipt_key",
        ),
        Index("ix_l3_provider_private_signed_url_revoke_receipt", "provider_private_signed_url_receipt_id"),
    )

    provider_private_signed_url_revocation_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_private_signed_url_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_private_signed_url_receipt.provider_private_signed_url_receipt_id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_by: Mapped[str] = mapped_column(String(255), nullable=False)
    revocation_reason_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revocation_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPrivateSignedUrlAuditEvent(Base):
    __tablename__ = "l3_provider_private_signed_url_audit_event"
    __table_args__ = (
        Index("ix_l3_provider_private_signed_url_audit_receipt", "provider_private_signed_url_receipt_id"),
        Index("ix_l3_provider_private_signed_url_audit_type_created", "event_type", "created_at"),
    )

    provider_private_signed_url_audit_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_private_signed_url_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_private_signed_url_receipt.provider_private_signed_url_receipt_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ConnectorLocalDestinationReceipt(Base):
    __tablename__ = "l3_connector_local_destination_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_connector_local_destination_receipt_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_connector_local_destination_receipt_authority_basis"),
        Index("ix_l3_connector_local_destination_receipt_session", "session_id"),
        Index("ix_l3_connector_local_destination_receipt_reconciliation", "reconciliation_record_id"),
        Index("ix_l3_connector_local_destination_receipt_state", "receipt_state"),
    )

    connector_local_destination_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_dispatch_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_target: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    receipt_state: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ServerOwnedLocalOutboxTargetReceipt(Base):
    __tablename__ = "l3_server_owned_local_outbox_target_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_local_outbox_target_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_local_outbox_target_authority_basis"),
        Index("ix_l3_local_outbox_target_session", "session_id"),
        Index("ix_l3_local_outbox_target_reconciliation", "reconciliation_record_id"),
        Index("ix_l3_local_outbox_target_state", "target_state"),
    )

    server_owned_local_outbox_target_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    connector_local_destination_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_dispatch_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    target_state: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ServerOwnedLocalOutboxWriteReceipt(Base):
    __tablename__ = "l3_server_owned_local_outbox_write_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_local_outbox_write_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_local_outbox_write_authority_basis"),
        Index("ix_l3_local_outbox_write_session", "session_id"),
        Index("ix_l3_local_outbox_write_target_receipt", "server_owned_local_outbox_target_receipt_id"),
        Index("ix_l3_local_outbox_write_state", "write_state"),
    )

    server_owned_local_outbox_write_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    server_owned_local_outbox_target_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_target_receipt.server_owned_local_outbox_target_receipt_id"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    connector_local_destination_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_dispatch_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    write_state: Mapped[str] = mapped_column(String(64), nullable=False)
    outbox_artifact_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    outbox_manifest_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    outbox_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outbox_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3LocalOutboxProviderPrivateHandoffReceipt(Base):
    __tablename__ = "l3_local_outbox_provider_private_handoff_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_local_outbox_provider_private_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_local_outbox_provider_private_authority_basis"),
        UniqueConstraint("request_basis_hash", name="uq_l3_local_outbox_provider_private_request_basis"),
        Index("ix_l3_local_outbox_provider_private_session", "session_id"),
        Index(
            "ix_l3_local_outbox_provider_private_write_receipt",
            "server_owned_local_outbox_write_receipt_id",
        ),
        Index("ix_l3_local_outbox_provider_private_state", "handoff_state"),
    )

    provider_private_handoff_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    server_owned_local_outbox_write_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_write_receipt.server_owned_local_outbox_write_receipt_id"),
        nullable=False,
    )
    server_owned_local_outbox_target_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_target_receipt.server_owned_local_outbox_target_receipt_id"),
        nullable=False,
    )
    connector_local_destination_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_dispatch_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    handoff_state: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_private_marker: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_private_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_private_replay_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    fake_provider_object_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    fake_provider_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    outbox_artifact_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    outbox_manifest_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    outbox_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outbox_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3LocalOutboxProviderPrivateHandoffAuditEvent(Base):
    __tablename__ = "l3_local_outbox_provider_private_handoff_audit_event"
    __table_args__ = (
        Index(
            "ix_l3_local_outbox_provider_private_audit_receipt",
            "provider_private_handoff_receipt_id",
        ),
        Index("ix_l3_local_outbox_provider_private_audit_type_created", "event_type", "created_at"),
    )

    provider_private_handoff_audit_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_private_handoff_receipt_id: Mapped[str] = mapped_column(
        ForeignKey(
            "l3_local_outbox_provider_private_handoff_receipt.provider_private_handoff_receipt_id"
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_basis_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ExternalLocalExportReceipt(Base):
    __tablename__ = "l3_external_local_export_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_external_local_export_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_external_local_export_authority_basis"),
        UniqueConstraint("external_artifact_ref", name="uq_l3_external_local_export_artifact_ref"),
        Index("ix_l3_external_local_export_session", "session_id"),
        Index("ix_l3_external_local_export_write_receipt", "server_owned_local_outbox_write_receipt_id"),
        Index("ix_l3_external_local_export_state", "export_state"),
    )

    external_local_export_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    server_owned_local_outbox_write_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_write_receipt.server_owned_local_outbox_write_receipt_id"),
        nullable=False,
    )
    server_owned_local_outbox_target_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_target_receipt.server_owned_local_outbox_target_receipt_id"),
        nullable=False,
    )
    connector_local_destination_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
        nullable=False,
    )
    provider_private_handoff_receipt_id: Mapped[str | None] = mapped_column(
        ForeignKey("l3_local_outbox_provider_private_handoff_receipt.provider_private_handoff_receipt_id")
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_dispatch_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    target_class: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    export_state: Mapped[str] = mapped_column(String(64), nullable=False)
    redacted_destination_label: Mapped[str] = mapped_column(String(128), nullable=False)
    external_artifact_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_manifest_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    external_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    external_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    external_manifest_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    source_outbox_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_outbox_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    redacted_failure_code: Mapped[str | None] = mapped_column(String(128))
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ExternalLocalExportAuditEvent(Base):
    __tablename__ = "l3_external_local_export_audit_event"
    __table_args__ = (
        Index("ix_l3_external_local_export_audit_receipt", "external_local_export_receipt_id"),
        Index("ix_l3_external_local_export_audit_type_created", "event_type", "created_at"),
    )

    external_local_export_audit_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    external_local_export_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_external_local_export_receipt.external_local_export_receipt_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_basis_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3InternalWebhookDispatchReceipt(Base):
    __tablename__ = "l3_internal_webhook_dispatch_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_internal_webhook_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_internal_webhook_authority_basis"),
        UniqueConstraint("request_basis_hash", name="uq_l3_internal_webhook_request_basis"),
        Index("ix_l3_internal_webhook_session", "session_id"),
        Index("ix_l3_internal_webhook_write_receipt", "server_owned_local_outbox_write_receipt_id"),
        Index("ix_l3_internal_webhook_status", "dispatch_status"),
    )

    internal_webhook_dispatch_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    server_owned_local_outbox_write_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_write_receipt.server_owned_local_outbox_write_receipt_id"),
        nullable=False,
    )
    server_owned_local_outbox_target_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_server_owned_local_outbox_target_receipt.server_owned_local_outbox_target_receipt_id"),
        nullable=False,
    )
    connector_local_destination_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    pass_run_id: Mapped[str] = mapped_column(ForeignKey("l3_pass_run.pass_run_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_dispatch_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    package_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    package_artifact_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    package_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    package_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    handoff_export_prepare_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    target_class: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    redacted_destination_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dispatch_status: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer)
    redacted_response_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3InternalWebhookDispatchAuditEvent(Base):
    __tablename__ = "l3_internal_webhook_dispatch_audit_event"
    __table_args__ = (
        Index("ix_l3_internal_webhook_audit_receipt", "internal_webhook_dispatch_receipt_id"),
        Index("ix_l3_internal_webhook_audit_type_created", "event_type", "created_at"),
    )

    internal_webhook_dispatch_audit_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    internal_webhook_dispatch_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_internal_webhook_dispatch_receipt.internal_webhook_dispatch_receipt_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_basis_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3SourceDirectoryInternalWebhookDispatchReceipt(Base):
    __tablename__ = "l3_source_directory_internal_webhook_dispatch_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_srcdir_internal_webhook_client_request"),
        UniqueConstraint("authority_basis_hash", name="uq_l3_srcdir_internal_webhook_authority_basis"),
        UniqueConstraint("request_basis_hash", name="uq_l3_srcdir_internal_webhook_request_basis"),
        Index("ix_l3_srcdir_internal_webhook_session", "session_id"),
        Index("ix_l3_srcdir_internal_webhook_reconciliation", "reconciliation_record_id"),
        Index("ix_l3_srcdir_internal_webhook_status", "dispatch_status"),
    )

    source_directory_internal_webhook_dispatch_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    reconciliation_record_id: Mapped[str] = mapped_column(
        ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
        nullable=False,
    )
    material_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("l3_material_snapshot.material_snapshot_id"),
        nullable=False,
    )
    source_ingestion_batch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_ingestion_file_id: Mapped[str] = mapped_column(String(128), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    export_download_descriptor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    package_review_submit_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    handoff_export_prepare_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    handoff_export_envelope_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    target_class: Mapped[str] = mapped_column(String(128), nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    redacted_destination_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dispatch_status: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer)
    redacted_response_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    output_package_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    package_kinds_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    payload_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3SourceDirectoryInternalWebhookDispatchAuditEvent(Base):
    __tablename__ = "l3_source_directory_internal_webhook_dispatch_audit_event"
    __table_args__ = (
        Index(
            "ix_l3_srcdir_internal_webhook_audit_receipt",
            "source_directory_internal_webhook_dispatch_receipt_id",
        ),
        Index("ix_l3_srcdir_internal_webhook_audit_type_created", "event_type", "created_at"),
    )

    source_directory_internal_webhook_dispatch_audit_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    source_directory_internal_webhook_dispatch_receipt_id: Mapped[str] = mapped_column(
        ForeignKey(
            "l3_source_directory_internal_webhook_dispatch_receipt."
            "source_directory_internal_webhook_dispatch_receipt_id"
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_basis_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPublicUrlObjectAuthority(Base):
    __tablename__ = "l3_provider_public_url_object_authority"
    __table_args__ = (
        UniqueConstraint("authority_hash", name="uq_l3_provider_public_url_authority_hash"),
        Index("ix_l3_provider_public_url_authority_session", "session_id"),
        Index("ix_l3_provider_public_url_authority_private_receipt", "provider_private_signed_url_receipt_id"),
    )

    provider_public_url_object_authority_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    provider_private_signed_url_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_private_signed_url_receipt.provider_private_signed_url_receipt_id"),
        nullable=False,
    )
    external_export_download_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    export_download_descriptor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    source_artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provider_public_object_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPublicUrlReceipt(Base):
    __tablename__ = "l3_provider_public_url_receipt"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_l3_provider_public_url_receipt_client_request"),
        UniqueConstraint("request_basis_hash", name="uq_l3_provider_public_url_receipt_request_basis"),
        UniqueConstraint("provider_public_url_hash", name="uq_l3_provider_public_url_hash"),
        Index("ix_l3_provider_public_url_receipt_authority", "provider_public_url_object_authority_id"),
        Index("ix_l3_provider_public_url_receipt_state_expiry", "provider_public_url_state", "provider_public_url_expires_at"),
    )

    provider_public_url_receipt_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_public_url_object_authority_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_public_url_object_authority.provider_public_url_object_authority_id"),
        nullable=False,
    )
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_public_url_state: Mapped[str] = mapped_column(String(64), nullable=False, default="provider_public_url_prepared")
    provider_public_url_replay_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="status_only")
    provider_public_url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_public_url_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_public_url_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authority_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPublicUrlRevocation(Base):
    __tablename__ = "l3_provider_public_url_revocation"
    __table_args__ = (
        UniqueConstraint(
            "provider_public_url_receipt_id",
            "idempotency_key",
            name="uq_l3_provider_public_url_revoke_receipt_key",
        ),
        Index("ix_l3_provider_public_url_revoke_receipt", "provider_public_url_receipt_id"),
    )

    provider_public_url_revocation_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_public_url_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_public_url_receipt.provider_public_url_receipt_id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_by: Mapped[str] = mapped_column(String(255), nullable=False)
    revocation_reason_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revocation_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3ProviderPublicUrlAuditEvent(Base):
    __tablename__ = "l3_provider_public_url_audit_event"
    __table_args__ = (
        Index("ix_l3_provider_public_url_audit_receipt", "provider_public_url_receipt_id"),
        Index("ix_l3_provider_public_url_audit_type_created", "event_type", "created_at"),
    )

    provider_public_url_audit_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str,
    )
    provider_public_url_receipt_id: Mapped[str] = mapped_column(
        ForeignKey("l3_provider_public_url_receipt.provider_public_url_receipt_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255))
    authority_hash: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class L3AnalysisProduct(Base, TimestampMixin):
    __tablename__ = "l3_analysis_product"
    __table_args__ = (
        UniqueConstraint("session_id", "client_request_id", name="uq_l3_analysis_product_session_request"),
        CheckConstraint(
            f"product_kind IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_KIND_VALUES)})",
            name="ck_l3_analysis_product_kind",
        ),
        CheckConstraint(
            f"executor_type IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_EXECUTOR_TYPE_VALUES)})",
            name="ck_l3_analysis_product_executor_type",
        ),
        CheckConstraint(
            f"lifecycle_status IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_LIFECYCLE_VALUES)})",
            name="ck_l3_analysis_product_lifecycle",
        ),
        Index("ix_l3_analysis_product_session", "session_id"),
    )

    analysis_product_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    product_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    executor_type: Mapped[str] = mapped_column(String(64), nullable=False, default="human")
    lifecycle_status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_non_evidentiary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    executor_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_schema_validation_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    spec_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    authoring_provenance_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped["L3Session"] = relationship()
    evidence_links: Mapped[list["L3AnalysisProductEvidenceLink"]] = relationship(
        back_populates="analysis_product", cascade="all, delete-orphan"
    )
    review_decisions: Mapped[list["L3AnalysisProductReviewDecision"]] = relationship(
        back_populates="analysis_product"
    )


class L3AnalysisProductEvidenceLink(Base, TimestampMixin):
    __tablename__ = "l3_analysis_product_evidence_link"
    __table_args__ = (
        CheckConstraint(
            f"ref_kind IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_EVIDENCE_REF_KIND_VALUES)})",
            name="ck_l3_aprod_evlink_ref_kind",
        ),
        CheckConstraint(
            f"evidence_role IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_EVIDENCE_ROLE_VALUES)})",
            name="ck_l3_aprod_evlink_role",
        ),
        Index("ix_l3_aprod_evlink_product", "analysis_product_id"),
    )

    evidence_link_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    analysis_product_id: Mapped[str] = mapped_column(
        ForeignKey("l3_analysis_product.analysis_product_id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    ref_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(64), nullable=False)
    locator_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    analysis_product: Mapped["L3AnalysisProduct"] = relationship(back_populates="evidence_links")
    session: Mapped["L3Session"] = relationship()


class L3AnalysisProductReviewDecision(Base, TimestampMixin):
    __tablename__ = "l3_analysis_product_review_decision"
    __table_args__ = (
        # Idempotency is keyed on client_request_id only. decision_basis_hash is NOT
        # unique: an append-only trail legitimately repeats identical transitions (e.g.
        # the revise->re-promote loop draft->proposed->draft->proposed produces a
        # byte-identical basis tuple), so a global UNIQUE would 500 a valid DAG path.
        UniqueConstraint("client_request_id", name="uq_l3_aprod_review_decision_client_request"),
        CheckConstraint(
            f"from_status IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_LIFECYCLE_VALUES)})",
            name="ck_l3_aprod_review_decision_from_status",
        ),
        CheckConstraint(
            f"to_status IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_LIFECYCLE_VALUES)})",
            name="ck_l3_aprod_review_decision_to_status",
        ),
        CheckConstraint(
            f"review_decision IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_REVIEW_DECISION_VALUES)})",
            name="ck_l3_aprod_review_decision_value",
        ),
        CheckConstraint(
            f"decision_reason_code IN ({', '.join(repr(v) for v in L3_ANALYSIS_PRODUCT_REVIEW_REASON_CODES)})",
            name="ck_l3_aprod_review_decision_reason",
        ),
        CheckConstraint(
            f"decision_status = '{L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED}'",
            name="ck_l3_aprod_review_decision_status",
        ),
        Index("ix_l3_aprod_review_decision_product", "analysis_product_id"),
        Index("ix_l3_aprod_review_decision_session", "session_id"),
    )

    analysis_product_review_decision_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uuid_str
    )
    analysis_product_id: Mapped[str] = mapped_column(
        ForeignKey("l3_analysis_product.analysis_product_id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("l3_session.session_id"), nullable=False
    )
    from_status: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    review_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED,
    )
    decision_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    grounding_asserted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    operator_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_notes_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decision_notes_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_provenance_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    decision_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    analysis_product: Mapped["L3AnalysisProduct"] = relationship(back_populates="review_decisions")
    session: Mapped["L3Session"] = relationship()


class L3WorkingSet(Base, TimestampMixin):
    __tablename__ = "l3_working_set"
    __table_args__ = (
        UniqueConstraint("session_id", "client_request_id", name="uq_l3_working_set_session_request"),
        Index("ix_l3_working_set_session", "session_id"),
    )

    working_set_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("l3_session.session_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    member_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    basis_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped["L3Session"] = relationship()
