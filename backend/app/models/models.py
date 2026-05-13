from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
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
