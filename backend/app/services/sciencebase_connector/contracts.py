from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RUN_TERMINAL_STATUSES = {"completed", "completed_with_errors", "failed", "cancelled"}
TARGET_TERMINAL_STATUSES = {
    "ignored_by_policy",
    "unsupported_artifact_surface",
    "collapsed_duplicate",
    "blocked_by_fetch_policy",
    "skipped_unchanged",
    "not_modified_remote",
    "budget_blocked",
    "dry_run_skipped",
    "missing_upstream",
    "removed_from_item",
    "superseded",
    "withdrawn",
    "out_of_scope",
    "recommended",
}
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
DEFAULT_ALLOWED_HOST_PATTERNS = ["sciencebase.gov", "www.sciencebase.gov", "*.usgs.gov"]
SURFACE_PRECEDENCE = {"files": 0, "distributionLinks": 1, "webLinks": 2}
SCOPE_MODES = {"keyword_search", "folder_children", "folder_descendants", "explicit_item_ids", "explicit_dois"}
RUN_MODES = {"one_shot_import", "recurring_sync", "dry_run"}
ARTIFACT_DEDUP_POLICIES = {"by_checksum", "by_resolved_url", "by_name_plus_surface"}
RECONCILIATION_STATUSES = {"missing_upstream", "removed_from_item", "superseded", "withdrawn", "out_of_scope"}
SEARCH_EXHAUSTION_REASONS = {"no_more_pages", "max_items_cap", "max_files_cap", "budget_exhausted", "cancelled", "error"}

ERROR_TAXONOMY = {
    "transport_timeout",
    "http_4xx",
    "http_5xx",
    "redirect_policy_violation",
    "host_policy_violation",
    "unsupported_artifact_surface",
    "unsupported_content_type",
    "conditional_fetch_miss",
    "checksum_mismatch",
    "raw_capture_failed",
    "parse_failed",
    "schema_validation_failed",
    "dataset_resolution_failed",
    "ingest_failed",
    "profile_failed",
    "recommend_failed",
    "lease_conflict",
    "cancelled_by_operator",
    "stale_checkpoint",
    "orchestrator_internal_error",
}

PHASES = {
    "planning",
    "discovery",
    "hydration",
    "target_creation",
    "downloading",
    "ingesting",
    "profiling",
    "recommending",
    "finalizing",
}


class SubmissionConflictError(Exception):
    pass


class RunNotFoundError(Exception):
    pass


class LeaseConflictError(Exception):
    pass


class FetchPolicyBlockedError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class SearchPageNormalized:
    items: list[dict[str, Any]]
    offset: int
    page_size: int
    total: int | None
    nextlink: str | None
    prevlink: str | None
    raw_query_metadata: dict[str, Any]


@dataclass
class ArtifactCandidate:
    stable_release_key: str
    stable_release_identifier: str
    identifiers_json: list[Any]
    sciencebase_item_id: str
    sciencebase_item_url: str
    artifact_surface: str
    artifact_locator_type: str
    sciencebase_file_name: str
    sciencebase_download_uri: str
    remote_checksum_type: str | None
    remote_checksum_value: str | None
    source_reference_json: dict[str, Any]
    canonical_artifact_key: str
    source_artifact_key: str
    dedup_hint: str
    permission_snapshot_json: dict[str, Any]
    access_level_summary: str
    public_read_confirmed: bool


@dataclass
class ResolvedTargetPlan:
    target_status: str
    operator_reason_code: str
    selection_reason_code: str | None
    ignore_reason_code: str | None
    dedup_reason_code: str | None
    blocked_reason: str | None


@dataclass
class ConditionalFetchMetadata:
    etag: str | None
    last_modified: str | None
    cache_validator_policy: str


@dataclass
class StageResult:
    status: str
    warnings: list[str]
    metrics: dict[str, Any]
    artifact_refs: dict[str, Any]
    error_class: str | None


@dataclass
class DownloadResult:
    content: bytes
    status_code: int
    final_url: str
    redirect_count: int
    etag: str | None
    last_modified: str | None
    content_type: str | None
    sha256: str
    headers: dict[str, Any]
    resolved_ip: str | None


def enum_value(value: Any, *, allowed: set[str], default: str) -> str:
    normalized = str(value or default).strip()
    return normalized if normalized in allowed else default
