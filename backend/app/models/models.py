from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


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
