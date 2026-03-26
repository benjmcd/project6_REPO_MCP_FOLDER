"""Add connector subsystem control-plane and provenance tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_connector_subsystem"
down_revision = "0003_core_schema_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_run",
        sa.Column("connector_run_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_key", sa.String(length=100), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("source_mode", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("request_config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("query_plan_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_query_fingerprint", sa.String(length=128)),
        sa.Column("request_fingerprint", sa.String(length=128)),
        sa.Column("submission_idempotency_key", sa.String(length=255)),
        sa.Column("discovery_snapshot_ref", sa.String(length=512)),
        sa.Column("selection_manifest_ref", sa.String(length=512)),
        sa.Column("report_ref", sa.String(length=512)),
        sa.Column("adapter_dialect", sa.String(length=100)),
        sa.Column("api_generation", sa.String(length=100)),
        sa.Column("sciencebase_normalization_version", sa.String(length=100)),
        sa.Column("execution_lease_owner", sa.String(length=255)),
        sa.Column("execution_lease_token", sa.String(length=64)),
        sa.Column("execution_lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resume_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ignored_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collapsed_duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_by_fetch_policy_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloaded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ingested_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profiled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommended_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connector_run_status_submitted", "connector_run", ["status", "submitted_at"])

    op.create_table(
        "connector_run_submission",
        sa.Column("connector_run_submission_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_key", sa.String(length=100), nullable=False),
        sa.Column("submission_idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_key", "submission_idempotency_key", name="uq_connector_submission_key"),
    )

    op.create_table(
        "connector_run_target",
        sa.Column("connector_run_target_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stable_release_key", sa.String(length=255)),
        sa.Column("stable_release_identifier", sa.String(length=512)),
        sa.Column("identifiers_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("sciencebase_item_id", sa.String(length=255)),
        sa.Column("sciencebase_item_url", sa.String(length=512)),
        sa.Column("sciencebase_file_name", sa.String(length=512)),
        sa.Column("sciencebase_download_uri", sa.String(length=1024)),
        sa.Column("artifact_surface", sa.String(length=50), nullable=False),
        sa.Column("artifact_locator_type", sa.String(length=100)),
        sa.Column("source_artifact_key", sa.String(length=1024)),
        sa.Column("canonical_artifact_key", sa.String(length=1024)),
        sa.Column("remote_checksum_type", sa.String(length=100)),
        sa.Column("remote_checksum_value", sa.String(length=255)),
        sa.Column("downloaded_sha256", sa.String(length=64)),
        sa.Column("raw_storage_ref", sa.String(length=512)),
        sa.Column("etag", sa.String(length=255)),
        sa.Column("last_modified", sa.String(length=255)),
        sa.Column("fetch_policy_mode", sa.String(length=100)),
        sa.Column("resolved_ip", sa.String(length=64)),
        sa.Column("redirect_count", sa.Integer()),
        sa.Column("blocked_reason", sa.Text()),
        sa.Column("aliases_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("source_reference_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_stage", sa.String(length=100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("last_error_class", sa.String(length=100)),
        sa.Column("retry_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("backoff_until", sa.DateTime(timezone=True)),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("dataset.dataset_id")),
        sa.Column("dataset_version_id", sa.String(length=36), sa.ForeignKey("dataset_version.dataset_version_id")),
        sa.Column("discovered_at", sa.DateTime(timezone=True)),
        sa.Column("selected_at", sa.DateTime(timezone=True)),
        sa.Column("downloaded_at", sa.DateTime(timezone=True)),
        sa.Column("ingested_at", sa.DateTime(timezone=True)),
        sa.Column("profiled_at", sa.DateTime(timezone=True)),
        sa.Column("recommended_at", sa.DateTime(timezone=True)),
        sa.Column("last_stage_transition_at", sa.DateTime(timezone=True)),
        sa.Column("operator_reason_code", sa.String(length=255)),
        sa.Column("selection_reason_code", sa.String(length=255)),
        sa.Column("ignore_reason_code", sa.String(length=255)),
        sa.Column("dedup_reason_code", sa.String(length=255)),
        sa.Column("versioning_reason_code", sa.String(length=255)),
        sa.Column("reconciliation_reason_code", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connector_run_target_run_ordinal", "connector_run_target", ["connector_run_id", "ordinal"])
    op.create_index("ix_connector_run_target_source_key", "connector_run_target", ["source_artifact_key"])
    op.create_index("ix_connector_run_target_status", "connector_run_target", ["status"])

    op.create_table(
        "connector_run_checkpoint",
        sa.Column("connector_run_checkpoint_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("phase", sa.String(length=100), nullable=False),
        sa.Column("partition_cursor", sa.String(length=255)),
        sa.Column("page_offset", sa.Integer()),
        sa.Column("last_item_id", sa.String(length=255)),
        sa.Column("last_target_id", sa.String(length=36)),
        sa.Column("last_successful_stage", sa.String(length=100)),
        sa.Column("checkpoint_written_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_connector_checkpoint_run_time", "connector_run_checkpoint", ["connector_run_id", "checkpoint_written_at"])

    op.create_table(
        "connector_target_stage_attempt",
        sa.Column("connector_target_stage_attempt_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_run_target_id", sa.String(length=36), sa.ForeignKey("connector_run_target.connector_run_target_id"), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_class", sa.String(length=100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metrics_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_stage_attempt_target_stage", "connector_target_stage_attempt", ["connector_run_target_id", "stage"])

    op.create_table(
        "connector_policy_snapshot",
        sa.Column("connector_policy_snapshot_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("retry_matrix_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "connector_artifact_alias",
        sa.Column("connector_artifact_alias_id", sa.String(length=36), primary_key=True),
        sa.Column("connector_run_target_id", sa.String(length=36), sa.ForeignKey("connector_run_target.connector_run_target_id"), nullable=False),
        sa.Column("alias_surface", sa.String(length=50), nullable=False),
        sa.Column("alias_name", sa.String(length=512)),
        sa.Column("alias_url", sa.String(length=1024)),
        sa.Column("alias_checksum_type", sa.String(length=100)),
        sa.Column("alias_checksum_value", sa.String(length=255)),
        sa.Column("alias_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "dataset_external_identity",
        sa.Column("dataset_external_identity_id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("dataset.dataset_id"), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("logical_dataset_key", sa.String(length=512), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_system", "logical_dataset_key", name="uq_dataset_external_identity_key"),
    )

    op.create_table(
        "dataset_source_provenance",
        sa.Column("dataset_source_provenance_id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_version_id", sa.String(length=36), sa.ForeignKey("dataset_version.dataset_version_id"), nullable=False),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id")),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("source_mode", sa.String(length=100), nullable=False),
        sa.Column("source_artifact_key", sa.String(length=1024), nullable=False),
        sa.Column("sciencebase_item_id", sa.String(length=255)),
        sa.Column("sciencebase_item_url", sa.String(length=512)),
        sa.Column("sciencebase_file_name", sa.String(length=512)),
        sa.Column("sciencebase_download_uri", sa.String(length=1024)),
        sa.Column("artifact_surface", sa.String(length=50)),
        sa.Column("artifact_locator_type", sa.String(length=100)),
        sa.Column("remote_checksum_type", sa.String(length=100)),
        sa.Column("remote_checksum_value", sa.String(length=255)),
        sa.Column("downloaded_sha256", sa.String(length=64)),
        sa.Column("raw_storage_ref", sa.String(length=512)),
        sa.Column("source_query_fingerprint", sa.String(length=128)),
        sa.Column("source_reference_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("fetch_policy_mode", sa.String(length=100)),
        sa.Column("resolved_ip", sa.String(length=64)),
        sa.Column("redirect_count", sa.Integer()),
        sa.Column("blocked_reason", sa.Text()),
        sa.Column("etag", sa.String(length=255)),
        sa.Column("last_modified", sa.String(length=255)),
        sa.Column("retrieved_http_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("discovered_at", sa.DateTime(timezone=True)),
        sa.Column("downloaded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dataset_source_prov_artifact_key", "dataset_source_provenance", ["source_artifact_key"])
    op.create_index("ix_dataset_source_prov_version", "dataset_source_provenance", ["dataset_version_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_source_prov_version", table_name="dataset_source_provenance")
    op.drop_index("ix_dataset_source_prov_artifact_key", table_name="dataset_source_provenance")
    op.drop_table("dataset_source_provenance")
    op.drop_table("dataset_external_identity")
    op.drop_table("connector_artifact_alias")
    op.drop_table("connector_policy_snapshot")
    op.drop_index("ix_stage_attempt_target_stage", table_name="connector_target_stage_attempt")
    op.drop_table("connector_target_stage_attempt")
    op.drop_index("ix_connector_checkpoint_run_time", table_name="connector_run_checkpoint")
    op.drop_table("connector_run_checkpoint")
    op.drop_index("ix_connector_run_target_status", table_name="connector_run_target")
    op.drop_index("ix_connector_run_target_source_key", table_name="connector_run_target")
    op.drop_index("ix_connector_run_target_run_ordinal", table_name="connector_run_target")
    op.drop_table("connector_run_target")
    op.drop_table("connector_run_submission")
    op.drop_index("ix_connector_run_status_submitted", table_name="connector_run")
    op.drop_table("connector_run")
