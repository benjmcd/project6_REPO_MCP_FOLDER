from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any, Literal, Mapping
from uuid import UUID

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)


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
    source_row_count: int | None = None
    dropped_row_count: int | None = None
    content_hash: str | None = None
    time_column: str | None = None
    numeric_variables: list[str]


class DatasetVersionOut(BaseModel):
    dataset_version_id: str
    version_label: str
    version_type: str
    row_count: int
    source_row_count: int | None = None
    dropped_row_count: int | None = None
    content_hash: str | None = None


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


SINGLE_SEND_DETECTION_ALLOWANCE_BYTES = 6_684_672

COMMON_GRANT_NON_AUTHORITIES = (
    "other_connector_or_target_not_authorized",
    "search_not_authorized",
    "automatic_retry_not_authorized",
    "resume_or_recurrence_not_authorized",
    "alternate_selection_not_authorized",
    "credential_fallback_not_authorized",
    "post_expiry_send_not_authorized",
    "continuation_after_code_change_not_authorized",
    "external_delivery_not_authorized",
    "production_or_support_promotion_not_authorized",
    "additional_parent_arming_not_authorized",
    "unused_budget_transfer_not_authorized",
)
NRC_GRANT_NON_AUTHORITIES = (
    *COMMON_GRANT_NON_AUTHORITIES,
    "redirect_follow_not_authorized",
)
CAMPAIGN_NON_AUTHORITIES = COMMON_GRANT_NON_AUTHORITIES

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def _normalized_sha256(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError("value must be a lowercase 64-hex SHA-256")
    return normalized


def _normalized_code_revision(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if not _CODE_REVISION_RE.fullmatch(normalized):
        raise ValueError("code_revision must be a lowercase 40-hex Git revision")
    return normalized


def _validated_id(value: object) -> str:
    text = str(value or "")
    if text != text.strip() or not _ID_RE.fullmatch(text):
        raise ValueError("identifier must be 1-128 safe ASCII characters")
    return text


def _canonical_uuid4_text(value: object) -> str:
    try:
        parsed = UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("campaign_id must be a UUID4") from exc
    if parsed.version != 4:
        raise ValueError("campaign_id must be a UUID4")
    return str(parsed)


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _normalized_hosts(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("allowed_hosts must be an ordered array")
    normalized: list[str] = []
    for raw in value:
        host = str(raw or "").strip().lower()
        if host.endswith("."):
            host = host[:-1]
        if host.endswith("."):
            raise ValueError("hostname cannot contain repeated trailing dots")
        try:
            host.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("hostname must be ASCII") from exc
        if not _HOST_RE.fullmatch(host):
            raise ValueError("hostname is invalid")
        normalized.append(host)
    result = tuple(normalized)
    if not result or len(set(result)) != len(result):
        raise ValueError("allowed_hosts must be non-empty and duplicate-free")
    return result


def expected_grant_rule_payloads(connector_key: str) -> tuple[dict[str, object], ...]:
    if connector_key == "sciencebase_mcs":
        common: dict[str, object] = {
            "method": "GET",
            "scheme": "https",
            "port": 443,
            "credential_audience": "none",
        }
        return (
            {
                **common,
                "ordinal": 1,
                "stage": "item_hydration",
                "allowed_hosts": ("www.sciencebase.gov",),
                "path_rule_id": "sciencebase_item_exact_v1",
                "query_rule_id": "format_json_exact_v1",
                "max_response_bytes": 5 * 1024 * 1024,
            },
            {
                **common,
                "ordinal": 2,
                "stage": "artifact",
                "allowed_hosts": ("sciencebase.gov", "www.sciencebase.gov"),
                "path_rule_id": "sciencebase_file_exact_v1",
                "query_rule_id": "sciencebase_exact_file_selector_v1",
                "max_response_bytes": 64 * 1024 * 1024,
            },
            {
                **common,
                "ordinal": 3,
                "stage": "artifact_redirect",
                "allowed_hosts": ("sciencebase.gov", "www.sciencebase.gov"),
                "path_rule_id": "sciencebase_file_exact_v1",
                "query_rule_id": "sciencebase_exact_file_selector_v1",
                "max_response_bytes": 64 * 1024 * 1024,
            },
        )
    if connector_key == "nrc_adams_aps":
        return (
            {
                "ordinal": 1,
                "stage": "exact_accession_api",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ("adams-api.nrc.gov",),
                "port": 443,
                "path_rule_id": "nrc_get_document_exact_v1",
                "query_rule_id": "none_v1",
                "credential_audience": "nrc_aps_api_key",
                "max_response_bytes": 5 * 1024 * 1024,
            },
            {
                "ordinal": 2,
                "stage": "artifact",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ("www.nrc.gov",),
                "port": 443,
                "path_rule_id": "nrc_public_pdf_exact_v1",
                "query_rule_id": "none_v1",
                "credential_audience": "none",
                "max_response_bytes": 64 * 1024 * 1024,
            },
        )
    raise ValueError("connector_key is not admitted")


class ScienceBaseFreshTargetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_key: Literal["sciencebase_mcs"]
    item_id: Literal["63d1a3c6d34e06fef15006be"]
    exact_file_name: Literal["mcs2023-germa_salient.csv"]
    locator_key: Literal["downloadUri"]


class NrcApsFreshTargetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_key: Literal["nrc_adams_aps"]
    accession_number: Literal["ML17123A319"]


class DualLiveCampaignDefinitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.dual_live_campaign_definition.v1"]
    campaign_id: UUID4
    code_revision: str
    connector_keys: tuple[Literal["sciencebase_mcs"], Literal["nrc_adams_aps"]]
    sciencebase_target: ScienceBaseFreshTargetV1
    nrc_target: NrcApsFreshTargetV1
    acceptance_profile: Literal["dual_live_to_internal_handoff_v1"]
    evidence_profile: Literal["dual_live_evidence_v1"]
    review_policy: Literal["security_egress_and_layer3_integrity_v1"]
    required_review_roles: tuple[
        Literal["security_egress"], Literal["layer3_integrity"]
    ]
    execution_order: Literal["nrc_then_sciencebase"]
    package_kinds: tuple[
        Literal["canonical_internal"],
        Literal["user_facing"],
        Literal["review_facing"],
    ]
    not_before: datetime
    expires_at: datetime
    non_authorities: tuple[str, ...]

    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )
    _times = field_validator("not_before", "expires_at")(_utc_datetime)

    @model_validator(mode="after")
    def _validate_campaign(self) -> "DualLiveCampaignDefinitionV1":
        if self.connector_keys != ("sciencebase_mcs", "nrc_adams_aps"):
            raise ValueError("connector_keys must use exact campaign order")
        if self.required_review_roles != ("security_egress", "layer3_integrity"):
            raise ValueError("required_review_roles must use exact review order")
        if self.package_kinds != (
            "canonical_internal",
            "user_facing",
            "review_facing",
        ):
            raise ValueError("package_kinds must use exact package order")
        if self.not_before >= self.expires_at:
            raise ValueError("campaign authority window must be non-empty")
        if self.non_authorities != CAMPAIGN_NON_AUTHORITIES:
            raise ValueError("campaign non_authorities must equal canonical codes")
        return self


class ConnectorGrantRequestRuleV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordinal: int = Field(gt=0)
    stage: Literal[
        "item_hydration",
        "artifact",
        "artifact_redirect",
        "exact_accession_api",
    ]
    method: Literal["GET"]
    scheme: Literal["https"]
    allowed_hosts: tuple[str, ...]
    port: Literal[443]
    path_rule_id: Literal[
        "sciencebase_item_exact_v1",
        "sciencebase_file_exact_v1",
        "nrc_get_document_exact_v1",
        "nrc_public_pdf_exact_v1",
    ]
    query_rule_id: Literal[
        "format_json_exact_v1",
        "sciencebase_exact_file_selector_v1",
        "none_v1",
    ]
    credential_audience: Literal["none", "nrc_aps_api_key"]
    max_response_bytes: int = Field(gt=0)

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, value: object) -> str:
        return str(value or "").strip().upper()

    _hosts = field_validator("allowed_hosts", mode="before")(_normalized_hosts)

    @model_validator(mode="after")
    def _validate_credential_audience(self) -> "ConnectorGrantRequestRuleV1":
        if (
            self.credential_audience == "nrc_aps_api_key"
            and self.allowed_hosts != ("adams-api.nrc.gov",)
        ):
            raise ValueError(
                "nrc_aps_api_key audience is restricted to adams-api.nrc.gov"
            )
        return self


class ConnectorEgressGrantV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.connector_egress_grant.v1"]
    grant_id: str
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    arming_nonce: UUID4
    max_armings: Literal[1]
    supersedes_grant_sha256: str | None = None
    issued_at: datetime
    expires_at: datetime
    operator_mode: Literal["local_loopback", "proxy_owner"]
    target: ScienceBaseFreshTargetV1 | NrcApsFreshTargetV1
    request_rules: tuple[ConnectorGrantRequestRuleV1, ...]
    max_physical_requests: int = Field(gt=0)
    max_run_bytes: int = Field(gt=0)
    max_single_send_detection_allowance_bytes: int = Field(gt=0)
    request_timeout_seconds: int = Field(gt=0)
    min_request_interval_ms: int = Field(gt=0)
    non_authorities: tuple[str, ...]

    _grant_id = field_validator("grant_id", mode="before")(_validated_id)
    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "supersedes_grant_sha256",
        mode="before",
    )(
        lambda value: (
            None if value is None else _normalized_sha256(value)
        )
    )
    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )
    _times = field_validator("issued_at", "expires_at")(_utc_datetime)

    @model_validator(mode="after")
    def _validate_grant(self) -> "ConnectorEgressGrantV1":
        if self.issued_at >= self.expires_at:
            raise ValueError("grant authority window must be non-empty")
        expected_target_type = (
            ScienceBaseFreshTargetV1
            if self.connector_key == "sciencebase_mcs"
            else NrcApsFreshTargetV1
        )
        if not isinstance(self.target, expected_target_type):
            raise ValueError("target does not match connector discriminator")
        expected_rules = expected_grant_rule_payloads(self.connector_key)
        actual_rules = tuple(
            rule.model_dump(mode="python") for rule in self.request_rules
        )
        if actual_rules != expected_rules:
            raise ValueError("request_rules do not equal exact connector matrix")
        expected_ceiling = 3 if self.connector_key == "sciencebase_mcs" else 2
        if self.max_physical_requests != expected_ceiling:
            raise ValueError("max_physical_requests does not equal connector ceiling")
        if (
            self.max_single_send_detection_allowance_bytes
            != SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
        ):
            raise ValueError(
                "max_single_send_detection_allowance_bytes does not equal pinned allowance"
            )
        expected_non_authorities = (
            COMMON_GRANT_NON_AUTHORITIES
            if self.connector_key == "sciencebase_mcs"
            else NRC_GRANT_NON_AUTHORITIES
        )
        if self.non_authorities != expected_non_authorities:
            raise ValueError("grant non_authorities do not equal canonical codes")
        return self


class ConnectorEgressArmingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.connector_egress_arming.v1"]
    client_request_id: str
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    grant_sha256: str

    _client_request_id = field_validator("client_request_id", mode="before")(
        _validated_id
    )
    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint", "grant_sha256", mode="before"
    )(_normalized_sha256)


class ConnectorEgressExecuteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_idempotency_key: str
    arming_fingerprint: str

    _execution_idempotency_key = field_validator(
        "execution_idempotency_key", mode="before"
    )(_validated_id)
    _arming_fingerprint = field_validator("arming_fingerprint", mode="before")(
        _normalized_sha256
    )


class ConnectorGrantEvidenceRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    code_revision: str
    raw_grant_sha256: str
    canonical_grant_fingerprint: str
    grant_relative_path: str
    consumption_marker_sha256: str
    consumption_marker_relative_path: str

    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "raw_grant_sha256",
        "canonical_grant_fingerprint",
        "consumption_marker_sha256",
        mode="before",
    )(_normalized_sha256)
    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )


class ConnectorCampaignDefinitionRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    campaign_fingerprint: str
    code_revision: str
    raw_definition_sha256: str
    definition_relative_path: str

    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint", "raw_definition_sha256", mode="before"
    )(_normalized_sha256)
    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )


class ConnectorCampaignLogCaptureRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    log_dir_relative_path: str
    manifest_relative_path: str
    seal_relative_path: str
    expected_stream_files: tuple[
        Literal["app.jsonl", "http.jsonl", "stdout.log", "stderr.log"], ...
    ]

    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint", "campaign_definition_sha256", mode="before"
    )(_normalized_sha256)
    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )

    @model_validator(mode="after")
    def _validate_stream_set(self) -> "ConnectorCampaignLogCaptureRefV1":
        if self.expected_stream_files != (
            "app.jsonl",
            "http.jsonl",
            "stdout.log",
            "stderr.log",
        ):
            raise ValueError("expected_stream_files must equal exact four-stream set")
        return self


class ConnectorGrantConsumptionMarkerV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.connector_grant_consumption.v1"]
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    raw_grant_sha256: str
    canonical_grant_fingerprint: str
    arming_nonce: UUID4
    connector_run_id: str
    max_armings: Literal[1]

    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "raw_grant_sha256",
        "canonical_grant_fingerprint",
        mode="before",
    )(_normalized_sha256)
    _run_id = field_validator("connector_run_id", mode="before")(_validated_id)


class ConnectorCampaignEvidenceIndexV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.connector_campaign_evidence_index.v1"]
    revision: PositiveInt
    predecessor_index_sha256: str | None
    predecessor_index_relative_path: str | None
    campaigns: tuple[ConnectorCampaignDefinitionRefV1, ...]
    entries: tuple[ConnectorGrantEvidenceRefV1, ...]
    log_captures: tuple[ConnectorCampaignLogCaptureRefV1, ...]

    _predecessor_hash = field_validator(
        "predecessor_index_sha256", mode="before"
    )(lambda value: None if value is None else _normalized_sha256(value))

    @model_validator(mode="after")
    def _validate_predecessor_pair(self) -> "ConnectorCampaignEvidenceIndexV1":
        predecessor_present = self.predecessor_index_sha256 is not None
        path_present = self.predecessor_index_relative_path is not None
        if predecessor_present != path_present:
            raise ValueError("predecessor digest and path must be present together")
        if self.revision == 1 and predecessor_present:
            raise ValueError("revision 1 cannot name a predecessor")
        if self.revision > 1 and not predecessor_present:
            raise ValueError("successor revision must name a predecessor")
        return self


class ConnectorCampaignLogFileV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    stream_class: Literal["app", "http", "stdout", "stderr"]
    byte_count: int = Field(ge=0)
    sha256: str

    _sha256 = field_validator("sha256", mode="before")(_normalized_sha256)


class ConnectorCampaignLogManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.connector_campaign_log_manifest.v1"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    runtime_started_at: datetime
    runtime_stopped_at: datetime
    files: tuple[ConnectorCampaignLogFileV1, ...]

    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint", "campaign_definition_sha256", mode="before"
    )(_normalized_sha256)
    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )
    _times = field_validator("runtime_started_at", "runtime_stopped_at")(
        _utc_datetime
    )

    @model_validator(mode="after")
    def _validate_manifest(self) -> "ConnectorCampaignLogManifestV1":
        if self.runtime_stopped_at < self.runtime_started_at:
            raise ValueError("runtime_stopped_at cannot precede runtime_started_at")
        expected_files = (
            (f"logs/{self.campaign_fingerprint}/app.jsonl", "app"),
            (f"logs/{self.campaign_fingerprint}/http.jsonl", "http"),
            (f"logs/{self.campaign_fingerprint}/stdout.log", "stdout"),
            (f"logs/{self.campaign_fingerprint}/stderr.log", "stderr"),
        )
        actual_files = tuple(
            (item.relative_path, item.stream_class) for item in self.files
        )
        if actual_files != expected_files:
            raise ValueError(
                "manifest files must equal the exact campaign-bound four-stream paths"
            )
        return self


class ConnectorCampaignLogSealV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["project6.connector_campaign_log_seal.v1"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    campaign_introduction_index_revision: PositiveInt
    campaign_introduction_index_sha256: str
    code_revision: str
    manifest_relative_path: str
    manifest_sha256: str
    file_set_hash: str
    connector_run_ids: tuple[str, ...]
    sealed_at: datetime

    _campaign_id = field_validator("campaign_id", mode="before")(
        _canonical_uuid4_text
    )
    _hashes = field_validator(
        "campaign_fingerprint",
        "campaign_definition_sha256",
        "campaign_introduction_index_sha256",
        "manifest_sha256",
        "file_set_hash",
        mode="before",
    )(_normalized_sha256)
    _code_revision = field_validator("code_revision", mode="before")(
        _normalized_code_revision
    )
    _sealed_at = field_validator("sealed_at")(_utc_datetime)

    @model_validator(mode="after")
    def _validate_extant_runs(self) -> "ConnectorCampaignLogSealV1":
        expected_manifest = (
            f"logs/{self.campaign_fingerprint}/manifest.json"
        )
        if self.manifest_relative_path != expected_manifest:
            raise ValueError(
                "manifest_relative_path must equal the campaign-bound manifest path"
            )
        if len(self.connector_run_ids) not in {1, 2}:
            raise ValueError("connector_run_ids must contain one or two extant runs")
        if self.connector_run_ids != tuple(sorted(set(self.connector_run_ids))):
            raise ValueError("connector_run_ids must be sorted and duplicate-free")
        for run_id in self.connector_run_ids:
            _validated_id(run_id)
        return self


def _reject_reserved_sciencebase_egress_input(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    source_mode = value.get("source_mode")
    idempotency_values = (
        value.get("client_request_id"),
        value.get("submission_idempotency_key"),
        value.get("idempotency_key"),
    )
    if (
        "connector_egress_arming" in value
        or (
            isinstance(source_mode, str)
            and source_mode.strip().lower() == "strict_live_egress"
        )
        or any(
            isinstance(item, str)
            and item.strip().startswith("egress-arm:")
            for item in idempotency_values
        )
    ):
        raise ValueError(
            "reserved egress provenance requires the protected arming API"
        )
    return value


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

    @model_validator(mode="before")
    @classmethod
    def _reject_reserved_egress_input(cls, value: Any) -> Any:
        return _reject_reserved_sciencebase_egress_input(value)


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


class WorldBankConnectorRunIn(BaseModel):
    source_id: str = "2"
    indicators: list[str] = Field(default_factory=lambda: ["SP.POP.TOTL"])
    countries: list[str] = Field(default_factory=lambda: ["USA"])
    date_range: str | None = None
    per_page: int = 1000
    max_items: int = 0
    run_mode: Literal["metadata_only", "dry_run"] = "metadata_only"
    request_timeout_seconds: int = 30
    retry_max_attempts_per_request: int = 4
    retry_base_backoff_seconds: float = 0.4
    retry_max_backoff_seconds: float = 3.0
    retry_respect_retry_after: bool = True
    max_rps: float = Field(default=2.0, le=2.0)
    report_verbosity: Literal["summary", "standard", "debug"] = "standard"
    client_request_id: str | None = None


class CftcCotConnectorRunIn(BaseModel):
    report_variant: Literal["legacy_futures_only", "legacy_combined"] = "legacy_futures_only"
    market_name_contains: str | None = None
    exchange_name_contains: str | None = None
    max_rows: int = Field(default=1000, ge=1, le=5000)
    max_file_bytes: int = Field(default=8 * 1024 * 1024, ge=1, le=8 * 1024 * 1024)
    run_mode: Literal["metadata_only", "dry_run"] = "metadata_only"
    request_timeout_seconds: int = 30
    retry_max_attempts_per_request: int = 4
    retry_base_backoff_seconds: float = 0.4
    retry_max_backoff_seconds: float = 3.0
    retry_respect_retry_after: bool = True
    max_rps: float = Field(default=2.0, le=2.0)
    report_verbosity: Literal["summary", "standard", "debug"] = "standard"
    client_request_id: str | None = None


class BlsConnectorRunIn(BaseModel):
    series_ids: list[str] = Field(default_factory=lambda: ["LAUCN040010000000005"], min_length=1, max_length=25)
    start_year: int | None = Field(default=None, ge=1900, le=9999)
    end_year: int | None = Field(default=None, ge=1900, le=9999)
    max_requests: int = Field(default=10, ge=1, le=25)
    run_mode: Literal["metadata_only", "dry_run"] = "metadata_only"
    request_timeout_seconds: int = 30
    retry_max_attempts_per_request: int = 4
    retry_base_backoff_seconds: float = 0.4
    retry_max_backoff_seconds: float = 3.0
    retry_respect_retry_after: bool = True
    max_rps: float = Field(default=2.0, ge=0.1, le=2.0)
    report_verbosity: Literal["summary", "standard", "debug"] = "standard"
    client_request_id: str | None = None

    @field_validator("series_ids")
    @classmethod
    def _normalize_series_ids(cls, value: list[str]) -> list[str]:
        normalized = []
        for item in value:
            text = str(item or "").strip().upper()
            if text and (len(text) > 64 or not text.isalnum()):
                raise ValueError("BLS series ids must be alphanumeric")
            if text:
                normalized.append(text)
        deduped = list(dict.fromkeys(normalized))
        if not deduped:
            raise ValueError("at least one BLS series id is required")
        return deduped

    @model_validator(mode="after")
    def _validate_year_span(self) -> "BlsConnectorRunIn":
        if (self.start_year is None) != (self.end_year is None):
            raise ValueError("start_year and end_year must be supplied together")
        if self.start_year is not None and self.end_year is not None:
            if self.start_year > self.end_year:
                raise ValueError("start_year must be before or equal to end_year")
            if self.end_year - self.start_year > 9:
                raise ValueError("BLS API v1 year range must be 10 years or less")
        return self


class OecdSdmxConnectorRunIn(BaseModel):
    agency: str = "OECD.SDD.STES"
    dataflow: str = "DSD_STES@DF_CLI"
    dimension_key: str = ".M.LI...AA...H"
    start_period: str | None = None
    end_period: str | None = None
    lastNObservations: int | None = Field(default=None, ge=1)
    max_requests: int = Field(default=6, ge=1, le=30)
    max_rows: int = Field(default=5000, ge=1, le=10000)
    max_response_bytes: int = Field(default=2_000_000, ge=1, le=5_000_000)
    run_mode: Literal["metadata_only", "dry_run"] = "metadata_only"
    request_timeout_seconds: int = 30
    retry_max_attempts_per_request: int = 4
    retry_base_backoff_seconds: float = 0.4
    retry_max_backoff_seconds: float = 3.0
    retry_respect_retry_after: bool = True
    max_rps: float = Field(default=2.0, ge=0.1, le=2.0)
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


class NrcApsDeterministicChallengeReviewPacketCreateIn(BaseModel):
    deterministic_challenge_artifact_id: str | None = None
    deterministic_challenge_artifact_ref: str | None = None
    persist_review_packet: bool = False


class NrcApsDeterministicChallengeReviewPacketSourceInsightOut(BaseModel):
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


class NrcApsDeterministicChallengeReviewPacketSourceChallengeOut(BaseModel):
    schema_id: str
    schema_version: int
    deterministic_challenge_artifact_id: str
    deterministic_challenge_artifact_checksum: str
    deterministic_challenge_artifact_ref: str | None = None
    ruleset_contract_id: str
    ruleset_id: str
    ruleset_version: int
    challenge_mode: str
    total_challenges: int
    challenge_counts: dict[str, int] = Field(default_factory=dict)
    disposition_counts: dict[str, int] = Field(default_factory=dict)
    source_deterministic_insight_artifact: NrcApsDeterministicChallengeReviewPacketSourceInsightOut


class NrcApsDeterministicChallengeReviewPacketEvidencePointerOut(BaseModel):
    pointer: str
    source_finding_id: str | None = None
    source_rule_id: str | None = None


class NrcApsDeterministicChallengeReviewPacketChallengeRowOut(BaseModel):
    challenge_id: str
    check_id: str
    check_version: int
    category: str
    severity: str
    disposition: str
    matched_finding_count: int
    source_finding_ids: list[str] = Field(default_factory=list)
    message: str
    evidence_pointers: list[NrcApsDeterministicChallengeReviewPacketEvidencePointerOut] = Field(default_factory=list)


class NrcApsDeterministicChallengeReviewPacketOut(BaseModel):
    generated_at_utc: str
    schema_id: str
    schema_version: int
    deterministic_challenge_review_packet_id: str
    deterministic_challenge_review_packet_checksum: str
    deterministic_challenge_review_packet_ref: str | None = None
    projection_contract_id: str
    projection_mode: str
    source_deterministic_challenge_artifact: NrcApsDeterministicChallengeReviewPacketSourceChallengeOut
    total_challenges: int
    blocker_count: int
    review_item_count: int
    acknowledgement_count: int
    blockers: list[NrcApsDeterministicChallengeReviewPacketChallengeRowOut] = Field(default_factory=list)
    review_items: list[NrcApsDeterministicChallengeReviewPacketChallengeRowOut] = Field(default_factory=list)
    acknowledgements: list[NrcApsDeterministicChallengeReviewPacketChallengeRowOut] = Field(default_factory=list)
    persisted: bool = False
