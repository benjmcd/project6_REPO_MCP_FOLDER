"""B1b connector-promotion identity, arbitration, and digest services.

Pure, side-effect-free building blocks for the Option II promotion receipt
(owner-bound correction, Sections 3.1 / 4.1 / 4.2). Server-derived only:
no caller-supplied value is ever authoritative for any digest produced here.
The legacy Gate-B manifest hash (``layer3_gate_b_state.stable_hash``) is a
distinct, deliberately different serializer and is never replaced by these.

The workbench calls arbitration only when its feature flag and exact-shape gate
pass. Importing this module performs no I/O and mutates no state.
"""

from __future__ import annotations

import base64
import csv
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import unicodedata
from typing import Any, Mapping
from urllib.parse import parse_qsl, quote, unquote, urlsplit
import uuid

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm.exc import MultipleResultsFound

from app.core.config import settings
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    AssumptionCheck,
    CaveatNote,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3Descriptor,
    L3GateBIdempotencyKey,
    L3AnalysisPlan,
    L3AnalysisGroup,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    SourceConnector,
    VariableDefinition,
)
from app.services.dataframe_io import write_dataframe_to_absent_parquet
from app.services.ingest import read_existing_csv_reference
from app.services.layer3_connector_source_intake import (
    CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX,
    ConnectorSourceIntakeError,
    _storage_path_from_ref,
    validate_connector_intake_gate_b_decision_basis,
)
from app.services.layer3_gate_b_state import (
    GATE_B_IDEMPOTENCY_CONTEXT_KEY,
    GATE_B_IDEMPOTENCY_SCHEMA_ID,
    GATE_B_IDEMPOTENCY_STATUS_COMMITTED,
    gate_b_idempotency_request_hash,
    gate_b_decision_manifest_id,
    material_candidate_basis_from_decision,
    material_preview_hash,
)
from app.services.layer3_utils import stable_hash as gate_b_stable_hash
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import materialize_typing_entry

# ---------------------------------------------------------------------------
# Schema identifiers and fixed contract constants (owner-bound literals)
# ---------------------------------------------------------------------------

IDENTITY_METADATA_HASH_VERSION = "layer3.connector_source_intake.identity_metadata.v1"
RECEIPT_SCHEMA_VERSION = "layer3.connector_promotion_receipt.v1"
IDENTITY_KEY_SCHEMA_ID = "layer3.connector_promotion_identity_key.v1"
DECISION_SEMANTICS_SCHEMA_ID = "layer3.connector_promotion_decision_semantics.v1"
ELIGIBILITY_POLICY_ID = "layer3.connector_promotion_eligibility.f07-c01.v1"
RECEIPT_BASIS_SCHEMA_ID = "layer3.connector_promotion_receipt_basis.v1"
MATERIALIZATION_BASIS_SCHEMA_ID = "layer3.connector_promotion_materialization_basis.v1"
MATERIALIZATION_METADATA_SCHEMA_ID = "layer3.connector_promotion_materialization_metadata.v1"
MATERIALIZATION_RECORD_SCHEMA_ID = "layer3.connector_promotion_materialization_record.v1"
TRANSFORM_SCHEMA_ID = "layer3.connector_promotion_transform.v1"
TRANSFORM_VERSION = "1"

# Frozen digests referenced by the materialization basis (preimages are owned
# by their defining passes; the literals below are binding constants here).
TRANSFORM_CONTRACT_SHA256 = "951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179"
METHOD_INPUT_SHA256 = "907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b"
METADATA_CONTRACT_SHA256 = "86d8ab86401f1a7fa84f42e63bc288da1fe05d670cde1ec98c9387f136deb644"
MATERIALIZATION_SEMANTIC_SHA256 = "4bf4b24ded8e29087d1a8503e92d6141f59beb1356f3c9e7fadce1a250fbe2b0"
B1B_METHOD_CONTRACT_SHA256 = "586745d83f62f60e32a94fb62cd5557341866e5319d48eece7d0ea741a5e89e5"
B1B_EXPECTED_FIRST_PATH_CONTRACT_SHA256 = "0390d6adf485487bb599008bdabb7c04e8bfdb421fc5b76a3e604e9752d45dea"
B1B_QUESTION_TEXT = "Within the two synthetic C01 rows (`SB-001=42` and `SB-002=43`), what per-column classification, missingness, top values, and `value` minimum, maximum, mean, median, and sample standard deviation does `descriptive_summary` report, subject to the fixture being synthetic, non-temporal, and too small for official, causal, or population-wide inference?"
B1B_LIMITATIONS = [
    "Synthetic C01 fixture; not acquired from ScienceBase or USGS.",
    "public_read_confirmed=true is synthetic test state only.",
    "official_public_read_evidence=false.",
    "F20 is NOT-ESTABLISHED.",
    "The two-row sample is degenerate and non-temporal.",
    "Only bounded deterministic repeatability of descriptive_summary on C01 is supported.",
    "No official-data, source-availability, public-read, production, utility, causal, temporal, representativeness, or population-wide claim is supported.",
]

# F07/C01 fixed identity (v1 eligibility policy is exactly this material).
F07_SOURCE_FAMILY = "connector_produced_single_source"
F07_CONTENT_SHA256 = "d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad"
F07_CONTENT_BYTES = 34
F07_CONNECTOR_KEY = "sciencebase_public"
F07_SCIENCEBASE_ITEM_ID = "synthetic-sb-item-001"
F07_MEDIA_TYPE = "text/csv"
F07_IDENTITY_METADATA_HASH = "6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7"
F07_CANONICAL_IDENTITY_KEY_HASH = "2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0"

# The complete 2,180-byte D33-canonical materialization-metadata contract.
# Kept as the canonical byte string so tests can prove byte-for-byte fidelity
# (canonicalize(parse(s)) == s, len == 2180, sha256 == METADATA_CONTRACT_SHA256).
METADATA_CONTRACT_CANONICAL_JSON = '{"dataset":{"description":"Two-row synthetic, non-temporal, non-official C01 fixture for local B1b proof only.","domain_pack":null,"frequency_hint":null,"name":"Synthetic F07 C01 connector material","time_column":null},"dataset_source_provenance":{"artifact_locator_type":"intake_storage_ref","artifact_surface":"synthetic_fixture","blocked_reason":null,"discovered_at":null,"downloaded_at":null,"downloaded_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","etag":null,"fetch_policy_mode":"synthetic_local_no_network","last_modified":null,"raw_storage_ref_policy":"reuse_exact_intake_storage_ref","redirect_count":null,"remote_checksum_type":null,"remote_checksum_value":null,"resolved_ip":null,"retrieved_http_json":{},"sciencebase_download_uri":null,"sciencebase_file_name":null,"sciencebase_item_id":"synthetic-sb-item-001","sciencebase_item_url":null,"source_artifact_key":"f07-c01-synthetic","source_mode":"synthetic_local_direct_intake","source_query_fingerprint":null,"source_reference_json_policy":"exact_materialization_wrapper_only","source_system":"sciencebase_public_synthetic_fixture"},"dataset_version":{"content_hash":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","dropped_row_count":0,"notes":"synthetic=true; official_public_read_evidence=false; f20_status=NOT-ESTABLISHED; encoding=utf-8; transform=layer3.connector_promotion_transform.v1","parent_version_id":null,"row_count":2,"source_row_count":2,"status":"ready","storage_ref_policy":"final_parquet_under_dataset_storage_root","version_label":"b1b_f07_c01_v1","version_type":"synthetic_connector_promotion"},"schema_id":"layer3.connector_promotion_materialization_metadata.v1","source_connector":{"api_available_flag":false,"automation_tier":"tier_0","cleanup_burden":null,"domain_pack":null,"source_category":"synthetic_local_proof","source_name":"synthetic_f07_c01_connector","update_cadence":null},"variables":[{"dtype":"object","is_numeric":false,"is_time_index":false,"ordinal_position":0,"role":"measure","variable_name":"site_id"},{"dtype":"float64","is_numeric":true,"is_time_index":false,"ordinal_position":1,"role":"measure","variable_name":"value"}]}'

_B1B_ERROR_SPECS: dict[str, tuple[int, str, bool]] = {
    "promotion_identity_decision_conflict": (409, "Promotion identity decision conflicts with the committed receipt.", False),
    "connector_promotion_bridge_unavailable": (503, "Connector promotion bridge is unavailable.", True),
    "b1b_handoff_full_body_required": (400, "Handoff requires a full-body request.", False),
    "connector_promotion_session_not_found": (404, "Connector promotion session was not found.", False),
    "connector_promotion_not_eligible": (409, "Connector promotion is not eligible.", False),
    "b1b_request_validation_failed": (422, "Request body failed validation.", False),
    "promotion_identity_lock_unavailable": (503, "Promotion identity lock is unavailable.", True),
    "connector_promotion_basis_conflict": (409, "Promotion basis conflicts with the committed receipt.", False),
    "connector_result_review_decision_conflict": (409, "Result review decision conflicts with the recorded review.", False),
    "connector_package_basis_conflict": (409, "Package basis conflicts with the committed package set.", False),
    "connector_package_review_decision_conflict": (409, "Package review decision conflicts with the recorded review.", False),
    "connector_materialization_basis_conflict": (409, "Materialization basis conflicts with the committed output.", False),
}


class PromotionIdentityError(ValueError):
    """Raised for any invalid, unhashable, or non-canonical identity input."""


class ConnectorPromotionError(Exception):
    """Closed Step-3 error mapped by the workbench without caller text."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable


class B1BClosedApiError(ConnectorPromotionError):
    """Distinct typed failure intercepted only by the closed B1b route branch."""


@dataclass(frozen=True, init=False)
class B1BClosedApiResponse:
    """Validated closed B1b transport; stores only canonical bytes and status."""

    body_bytes: bytes
    http_status: int

    def __init__(self, body: Mapping[str, Any], *, http_status: int) -> None:
        _validate_b1b_closed_api_body(body, http_status=http_status)
        _assert_b1b_package_no_leak(body, _b1b_runtime_sensitive_values())
        object.__setattr__(self, "body_bytes", d33_canonical_bytes(body))
        object.__setattr__(self, "http_status", http_status)


@dataclass(frozen=True)
class GateBPromotionCandidate:
    candidate_id: str
    connector_source_intake_record_id: str
    decision: str
    decision_basis: Mapping[str, Any]


@dataclass(frozen=True)
class GateBPromotionIdentity:
    record: L3ConnectorSourceIntakeRecord
    run: ConnectorRun
    target: ConnectorRunTarget
    identity_metadata_hash: str
    canonical_identity_key_hash: str


@dataclass(frozen=True)
class GateBPromotionArbitration:
    candidate: GateBPromotionCandidate
    identity: GateBPromotionIdentity
    receipt: L3ConnectorPromotionReceipt | None
    winning_origin: tuple[L3Session, L3SelectionManifest, dict[str, Any]] | None


# ---------------------------------------------------------------------------
# D33 canonical serializer
# ---------------------------------------------------------------------------


def _validate_json_primitives(obj: object, path: str = "$") -> None:
    if obj is None or isinstance(obj, bool) or isinstance(obj, str):
        return
    if isinstance(obj, int):
        return
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise PromotionIdentityError(f"non-finite number at {path}")
        return
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_json_primitives(item, f"{path}[{i}]")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise PromotionIdentityError(f"non-string key at {path}: {key!r}")
            _validate_json_primitives(value, f"{path}.{key}")
        return
    raise PromotionIdentityError(f"non-JSON-primitive value at {path}: {type(obj).__name__}")


def d33_canonical_bytes(obj: object) -> bytes:
    """Serialize per the ratified D33 canonical JSON rules.

    Validated JSON primitives only; sort_keys; ensure_ascii; compact
    separators; allow_nan=False; UTF-8; no BOM; no terminal newline.
    """
    _validate_json_primitives(obj)
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def d33_sha256(obj: object) -> str:
    return hashlib.sha256(d33_canonical_bytes(obj)).hexdigest()


# ---------------------------------------------------------------------------
# Identity-metadata preimage (Section 3.1)
# ---------------------------------------------------------------------------

_TOKEN_FORBIDDEN = set(' ()<>@,;:\\"/[]?=')


def _clean_required_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise PromotionIdentityError(f"{field} must be a string")
    cleaned = unicodedata.normalize("NFC", value.strip())
    if not cleaned:
        raise PromotionIdentityError(f"{field} is empty after trimming")
    return cleaned


def _is_http_token(value: str) -> bool:
    return bool(value) and all(33 <= ord(ch) <= 126 and ch not in _TOKEN_FORBIDDEN for ch in value)


def parse_media_type(raw: object) -> dict:
    """Parse a media type per the Section 3.1 normalization contract.

    Lowercase essence and parameter names; reject malformed syntax and
    post-lowercase duplicate names; unquote/trim/NFC parameter values with
    case preserved; move ``charset`` to an explicit nullable key with only
    its token lowercased. No alias guessing.
    """
    text = _clean_required_string(raw, "media_type")
    parts = text.split(";")
    essence_raw = parts[0].strip()
    if "/" not in essence_raw:
        raise PromotionIdentityError("media_type essence must be type/subtype")
    type_part, _, subtype_part = essence_raw.partition("/")
    type_part, subtype_part = type_part.strip(), subtype_part.strip()
    if not (_is_http_token(type_part) and _is_http_token(subtype_part)):
        raise PromotionIdentityError("malformed media_type essence")
    essence = f"{type_part.lower()}/{subtype_part.lower()}"

    charset: str | None = None
    parameters: dict[str, str] = {}
    for segment in parts[1:]:
        segment = segment.strip()
        if not segment:
            raise PromotionIdentityError("empty media_type parameter segment")
        name_raw, eq, value_raw = segment.partition("=")
        if not eq:
            raise PromotionIdentityError(f"parameter missing '=': {segment!r}")
        name = name_raw.strip().lower()
        if not _is_http_token(name):
            raise PromotionIdentityError(f"malformed parameter name: {name_raw!r}")
        value = value_raw.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        value = unicodedata.normalize("NFC", value.strip())
        if not value:
            raise PromotionIdentityError(f"empty parameter value for {name!r}")
        if name == "charset":
            if charset is not None:
                raise PromotionIdentityError("duplicate charset parameter")
            charset = value.lower()
            continue
        if name in parameters:
            raise PromotionIdentityError(f"duplicate parameter name: {name!r}")
        parameters[name] = value

    return {"charset": charset, "essence": essence, "parameters": parameters}


def build_identity_metadata_preimage(
    connector_key: object, sciencebase_item_id: object, media_type: object
) -> dict:
    return {
        "fields": {
            "connector_key": _clean_required_string(connector_key, "connector_key"),
            "media_type": parse_media_type(media_type),
            "sciencebase_item_id": _clean_required_string(sciencebase_item_id, "sciencebase_item_id"),
        },
        "schema_id": IDENTITY_METADATA_HASH_VERSION,
    }


def identity_metadata_hash(
    connector_key: object, sciencebase_item_id: object, media_type: object
) -> str:
    return d33_sha256(build_identity_metadata_preimage(connector_key, sciencebase_item_id, media_type))


# ---------------------------------------------------------------------------
# Canonical identity key, decision semantics, and receipt basis (Section 4.1)
# ---------------------------------------------------------------------------

_HEX64 = frozenset("0123456789abcdef")


def _require_lower_hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or not set(value) <= _HEX64:
        raise PromotionIdentityError(f"{field} must be lowercase 64-hex")
    return value


def _identity_fields(
    hash_version: str, source_family: str, content_sha256: str, identity_hash: str
) -> dict:
    return {
        "content_sha256": _require_lower_hex64(content_sha256, "content_sha256"),
        "identity_metadata_hash": _require_lower_hex64(identity_hash, "identity_metadata_hash"),
        "identity_metadata_hash_version": _clean_required_string(hash_version, "identity_metadata_hash_version"),
        "source_family": _clean_required_string(source_family, "source_family"),
    }


def canonical_identity_key_hash(
    hash_version: str, source_family: str, content_sha256: str, identity_hash: str
) -> str:
    preimage = {
        "fields": _identity_fields(hash_version, source_family, content_sha256, identity_hash),
        "schema_id": IDENTITY_KEY_SCHEMA_ID,
    }
    return d33_sha256(preimage)


_VALID_DECISIONS = frozenset({"approved", "denied", "isolated", "flagged"})


def decision_semantics_hash(
    decision: str,
    hash_version: str,
    source_family: str,
    content_sha256: str,
    identity_hash: str,
) -> str:
    if decision not in _VALID_DECISIONS:
        raise PromotionIdentityError(f"invalid decision: {decision!r}")
    preimage = {
        "decision": decision,
        "eligibility_policy_id": ELIGIBILITY_POLICY_ID,
        "identity": _identity_fields(hash_version, source_family, content_sha256, identity_hash),
        "schema_id": DECISION_SEMANTICS_SCHEMA_ID,
    }
    return d33_sha256(preimage)


def promotion_basis_hash(
    *,
    approval_hash: str,
    gate_b_session_id: str,
    gate_b_selection_manifest_id: str,
    gate_b_material_snapshot_id: str,
    gate_b_decision_manifest_id: str,
    gate_b_decision_manifest_hash: str,
    material_preview_hash: str,
    canonical_identity_key_hash: str,
    identity_metadata_hash_version: str,
    source_family: str,
    content_sha256: str,
    identity_metadata_hash: str,
    connector_source_intake_record_id: str,
) -> str:
    preimage = {
        "approval_hash": _require_lower_hex64(approval_hash, "approval_hash"),
        "gate_b": {
            "decision_manifest_hash": _require_lower_hex64(
                gate_b_decision_manifest_hash, "gate_b_decision_manifest_hash"
            ),
            "decision_manifest_id": _clean_required_string(
                gate_b_decision_manifest_id, "gate_b_decision_manifest_id"
            ),
            "material_preview_hash": _require_lower_hex64(material_preview_hash, "material_preview_hash"),
            "material_snapshot_id": _clean_required_string(gate_b_material_snapshot_id, "gate_b_material_snapshot_id"),
            "selection_manifest_id": _clean_required_string(
                gate_b_selection_manifest_id, "gate_b_selection_manifest_id"
            ),
            "session_id": _clean_required_string(gate_b_session_id, "gate_b_session_id"),
        },
        "identity": {
            "canonical_identity_key_hash": _require_lower_hex64(
                canonical_identity_key_hash, "canonical_identity_key_hash"
            ),
            **_identity_fields(
                identity_metadata_hash_version, source_family, content_sha256, identity_metadata_hash
            ),
        },
        "intake": {
            "connector_source_intake_record_id": _clean_required_string(
                connector_source_intake_record_id, "connector_source_intake_record_id"
            )
        },
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "schema_id": RECEIPT_BASIS_SCHEMA_ID,
    }
    return d33_sha256(preimage)


# ---------------------------------------------------------------------------
# Gate-B single-I1 arbitration (Section 4.1, steps 1-4)
# ---------------------------------------------------------------------------


def _promotion_error(
    code: str,
    message: str,
    *,
    http_status: int,
    retryable: bool,
) -> ConnectorPromotionError:
    return ConnectorPromotionError(
        code,
        message,
        http_status=http_status,
        retryable=retryable,
    )


def possible_gate_b_promotion_candidate(
    raw_decisions: object,
) -> GateBPromotionCandidate | None:
    """Pure request-visible screen; never establishes server eligibility."""
    if not isinstance(raw_decisions, list) or len(raw_decisions) != 1:
        return None
    raw = raw_decisions[0]
    if not isinstance(raw, dict):
        return None
    candidate_id = str(raw.get("candidate_id") or "").strip()
    if not candidate_id.startswith(CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX):
        return None
    record_id = candidate_id[len(CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX) :]
    decision = str(raw.get("decision") or "").strip()
    if decision not in _VALID_DECISIONS:
        return None
    decision_basis = raw.get("decision_basis")
    if not record_id:
        return None
    return GateBPromotionCandidate(
        candidate_id=candidate_id,
        connector_source_intake_record_id=record_id,
        decision=decision,
        decision_basis=decision_basis if isinstance(decision_basis, Mapping) else {},
    )


def _server_exact_shape(
    record: L3ConnectorSourceIntakeRecord | None,
    run: ConnectorRun | None,
    target: ConnectorRunTarget | None,
) -> bool:
    return bool(
        record is not None
        and run is not None
        and target is not None
        and record.status == "recorded"
        and record.source_family == F07_SOURCE_FAMILY
        and record.connector_key == F07_CONNECTOR_KEY
        and record.content_size_bytes == F07_CONTENT_BYTES
        and record.content_sha256 == F07_CONTENT_SHA256
        and str(record.media_type or "").strip() == F07_MEDIA_TYPE
        and record.connector_run_id == run.connector_run_id
        and record.connector_run_target_id == target.connector_run_target_id
        and run.connector_key == F07_CONNECTOR_KEY
        and run.source_system == "sciencebase"
        and run.source_mode == "synthetic_local_direct_intake"
        and run.status == "running"
        and target.connector_run_id == run.connector_run_id
        and target.ordinal == 1
        and target.sciencebase_item_id == F07_SCIENCEBASE_ITEM_ID
        and target.sciencebase_item_url is None
        and target.sciencebase_file_name == "water-quality.csv"
        and target.sciencebase_download_uri is None
        and target.artifact_surface == "synthetic_fixture"
        and target.artifact_locator_type == "intake_storage_ref"
        and target.source_artifact_key == "f07-c01-synthetic"
        and target.downloaded_sha256 == F07_CONTENT_SHA256
        and target.raw_storage_ref == record.storage_ref
        and target.public_read_confirmed is True
        and target.status == "downloaded"
    )


def side_effect_free_server_exact_candidate(
    bind,
    candidate: GateBPromotionCandidate,
) -> bool:
    """Read exact server shape on a short-lived Session, never the writer Session."""
    try:
        with OrmSession(bind=bind, future=True) as screen_db:
            record = screen_db.get(
                L3ConnectorSourceIntakeRecord,
                candidate.connector_source_intake_record_id,
            )
            if record is None:
                return False
            run = screen_db.get(ConnectorRun, record.connector_run_id)
            target = screen_db.get(ConnectorRunTarget, record.connector_run_target_id)
            return _server_exact_shape(record, run, target)
    except DBAPIError as exc:
        raise _promotion_error(
            "connector_promotion_bridge_unavailable",
            "Connector promotion bridge is unavailable.",
            http_status=503,
            retryable=True,
        ) from exc


def side_effect_free_b1b_result_review_scope(bind, session_id: object) -> bool:
    """Classify a committed receipt-bound session without touching the writer Session."""
    if not bridge_precondition_available() or not isinstance(session_id, str):
        return False
    selected_session_id = session_id.strip()
    if not selected_session_id:
        return False
    try:
        with OrmSession(bind=bind, future=True) as screen_db:
            return bool(
                screen_db.query(L3ConnectorPromotionReceipt)
                .filter(
                    L3ConnectorPromotionReceipt.promoted_session_id == selected_session_id
                )
                .limit(1)
                .first()
            )
    except DBAPIError as exc:
        raise _closed_b1b_error("connector_promotion_bridge_unavailable") from exc


def attestation_precondition_available(_candidate: GateBPromotionCandidate | None = None) -> bool:
    """Step-3 seam. Full Section-8 attestation wiring is separately gated."""
    return False


def bridge_precondition_available() -> bool:
    """Body/DB-free availability check after static operator authorization."""
    return bool(
        settings.layer3_connector_promotion_bridge_enabled
        and attestation_precondition_available(None)
    )


def b1b_error_spec(error_code: str) -> tuple[int, str, bool]:
    try:
        return _B1B_ERROR_SPECS[error_code]
    except KeyError as exc:
        raise PromotionIdentityError("unknown closed B1b error code") from exc


def b1b_error_body(error_code: str) -> dict[str, Any]:
    _status, message, retryable = b1b_error_spec(error_code)
    return {
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "schema_id": "layer3.b1b_error.v1",
        "status": "error",
    }


def b1b_closed_error_response(error_code: str) -> B1BClosedApiResponse:
    http_status, _message, _retryable = b1b_error_spec(error_code)
    return B1BClosedApiResponse(b1b_error_body(error_code), http_status=http_status)


def _signed_advisory_lock_key(canonical_key_hash: str) -> int:
    value = int(_require_lower_hex64(canonical_key_hash, "canonical_identity_key_hash")[:16], 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def acquire_promotion_identity_lock(
    db: OrmSession,
    canonical_key_hash: str = F07_CANONICAL_IDENTITY_KEY_HASH,
) -> None:
    """Acquire the transaction-scoped writer lock before the writer Session reads."""
    marker = db.info.get("b1b_promotion_identity_lock")
    if db.in_transaction():
        if marker == canonical_key_hash:
            return
        raise _promotion_error(
            "promotion_identity_lock_unavailable",
            "Promotion identity lock is unavailable.",
            http_status=503,
            retryable=True,
        )
    dialect = db.get_bind().dialect.name
    try:
        if dialect == "sqlite":
            db.execute(text("PRAGMA busy_timeout=5000"))
            db.execute(text("BEGIN IMMEDIATE"))
        elif dialect == "postgresql":
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _signed_advisory_lock_key(canonical_key_hash)},
            )
        else:
            raise _promotion_error(
                "promotion_identity_lock_unavailable",
                "Promotion identity lock is unavailable.",
                http_status=503,
                retryable=True,
            )
    except DBAPIError as exc:
        db.rollback()
        db.info.pop("b1b_promotion_identity_lock", None)
        raise _promotion_error(
            "promotion_identity_lock_unavailable",
            "Promotion identity lock is unavailable.",
            http_status=503,
            retryable=True,
        ) from exc
    db.info["b1b_promotion_identity_lock"] = canonical_key_hash


def _reproduce_f07_transform(raw_bytes: bytes) -> None:
    if (
        len(raw_bytes) != F07_CONTENT_BYTES
        or hashlib.sha256(raw_bytes).hexdigest() != F07_CONTENT_SHA256
        or raw_bytes.startswith(b"\xef\xbb\xbf")
        or b"\r" in raw_bytes
        or not raw_bytes.endswith(b"\n")
    ):
        raise PromotionIdentityError("raw object does not reproduce F07 bytes")
    try:
        decoded = raw_bytes.decode("utf-8", errors="strict")
        parsed = list(csv.reader(io.StringIO(decoded, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise PromotionIdentityError("raw object does not reproduce strict UTF-8 CSV") from exc
    if parsed != [["site_id", "value"], ["SB-001", "42"], ["SB-002", "43"]]:
        raise PromotionIdentityError("raw object does not reproduce F07 rows")
    columns = [
        {"logical_type": "categorical_string", "name": "site_id"},
        {"logical_type": "numeric_integer", "name": "value"},
    ]
    rows = [["SB-001", 42], ["SB-002", 43]]
    transform = {
        "input": {
            "bom": False,
            "bytes": F07_CONTENT_BYTES,
            "encoding": "utf-8-strict",
            "final_lf": True,
            "line_endings": "lf",
            "sha256": F07_CONTENT_SHA256,
        },
        "output": {
            "coercion_count": 0,
            "column_count": 2,
            "columns": columns,
            "drop_count": 0,
            "row_count": 2,
            "rows": rows,
        },
        "parse": {"fallbacks": [], "header": ["site_id", "value"], "row_order": "source"},
        "schema_id": TRANSFORM_SCHEMA_ID,
    }
    method_input = {
        "columns": columns,
        "rows": rows,
        "schema_id": "layer3.descriptive_summary.input.v1",
        "time_column": None,
    }
    if d33_sha256(transform) != TRANSFORM_CONTRACT_SHA256:
        raise PromotionIdentityError("transform receipt digest mismatch")
    if d33_sha256(method_input) != METHOD_INPUT_SHA256:
        raise PromotionIdentityError("method-input digest mismatch")


def _not_eligible(exc: Exception | None = None) -> ConnectorPromotionError:
    error = _promotion_error(
        "connector_promotion_not_eligible",
        "Connector promotion is not eligible.",
        http_status=409,
        retryable=False,
    )
    if exc is not None:
        error.__cause__ = exc
    return error


def _basis_conflict() -> ConnectorPromotionError:
    return _promotion_error(
        "connector_promotion_basis_conflict",
        "Promotion basis conflicts with the committed receipt.",
        http_status=409,
        retryable=False,
    )


def _reconstruct_locked_identity(
    db: OrmSession,
    candidate: GateBPromotionCandidate,
) -> GateBPromotionIdentity:
    record = db.get(
        L3ConnectorSourceIntakeRecord,
        candidate.connector_source_intake_record_id,
    )
    if record is None:
        raise _not_eligible()
    run = db.get(ConnectorRun, record.connector_run_id)
    target = db.get(ConnectorRunTarget, record.connector_run_target_id)
    if not _server_exact_shape(record, run, target):
        raise _not_eligible()
    assert run is not None and target is not None
    try:
        validate_connector_intake_gate_b_decision_basis(
            db,
            candidate_id=candidate.candidate_id,
            decision_basis=candidate.decision_basis,
        )
        raw_path = _storage_path_from_ref(record.storage_ref)
        if not raw_path.is_file() or raw_path.stat().st_size != F07_CONTENT_BYTES:
            raise PromotionIdentityError("raw object missing or wrong length")
        _reproduce_f07_transform(raw_path.read_bytes())
        identity_hash = identity_metadata_hash(
            record.connector_key,
            target.sciencebase_item_id,
            record.media_type,
        )
        canonical_key = canonical_identity_key_hash(
            IDENTITY_METADATA_HASH_VERSION,
            record.source_family,
            record.content_sha256,
            identity_hash,
        )
    except (ConnectorSourceIntakeError, OSError, PromotionIdentityError) as exc:
        raise _not_eligible(exc) from exc
    if identity_hash != F07_IDENTITY_METADATA_HASH or canonical_key != F07_CANONICAL_IDENTITY_KEY_HASH:
        raise _not_eligible()
    pair = (record.identity_metadata_hash_version, record.identity_metadata_hash)
    if pair not in {
        (None, None),
        (IDENTITY_METADATA_HASH_VERSION, F07_IDENTITY_METADATA_HASH),
    }:
        raise _not_eligible()
    collisions = (
        db.query(L3ConnectorPromotionReceipt)
        .filter(
            L3ConnectorPromotionReceipt.canonical_identity_key_hash
            == F07_CANONICAL_IDENTITY_KEY_HASH
        )
        .all()
    )
    for collision in collisions:
        if (
            collision.identity_metadata_hash_version,
            collision.source_family,
            collision.content_sha256,
            collision.identity_metadata_hash,
        ) != (
            IDENTITY_METADATA_HASH_VERSION,
            F07_SOURCE_FAMILY,
            F07_CONTENT_SHA256,
            F07_IDENTITY_METADATA_HASH,
        ):
            raise _not_eligible()
    return GateBPromotionIdentity(
        record=record,
        run=run,
        target=target,
        identity_metadata_hash=identity_hash,
        canonical_identity_key_hash=canonical_key,
    )


def _receipt_for_identity(db: OrmSession) -> L3ConnectorPromotionReceipt | None:
    try:
        return (
            db.query(L3ConnectorPromotionReceipt)
            .filter(
                L3ConnectorPromotionReceipt.identity_metadata_hash_version
                == IDENTITY_METADATA_HASH_VERSION,
                L3ConnectorPromotionReceipt.source_family == F07_SOURCE_FAMILY,
                L3ConnectorPromotionReceipt.content_sha256 == F07_CONTENT_SHA256,
                L3ConnectorPromotionReceipt.identity_metadata_hash == F07_IDENTITY_METADATA_HASH,
            )
            .one_or_none()
        )
    except MultipleResultsFound as exc:
        raise _basis_conflict() from exc


def _stored_decision_manifest(session: L3Session) -> dict[str, Any]:
    operator_context = session.operator_context_json
    if not isinstance(operator_context, Mapping):
        raise _basis_conflict()
    decision_manifest = operator_context.get("layer3_gate_b_decision_manifest_v1")
    if not isinstance(decision_manifest, dict):
        raise _basis_conflict()
    return decision_manifest


def _verify_receipt_gate_b_spine(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    session: L3Session,
    manifest: L3SelectionManifest,
    snapshot: L3MaterialSnapshot,
    decision_item: Mapping[str, Any],
    snapshot_payload: object,
) -> None:
    context = session.operator_context_json
    summary = session.summary_json
    manifest_json = manifest.manifest_json
    hints = manifest.source_plane_hints_json
    idempotency = (
        context.get(GATE_B_IDEMPOTENCY_CONTEXT_KEY)
        if isinstance(context, Mapping)
        else None
    )
    manifest_items = manifest_json.get("items") if isinstance(manifest_json, Mapping) else None
    if (
        not isinstance(context, Mapping)
        or not isinstance(summary, Mapping)
        or not isinstance(idempotency, Mapping)
        or not isinstance(manifest_json, Mapping)
        or not isinstance(hints, Mapping)
        or not isinstance(manifest_items, list)
        or len(manifest_items) != 1
        or not isinstance(manifest_items[0], Mapping)
    ):
        raise _basis_conflict()
    manifest_item = manifest_items[0]
    selector_payload = manifest_item.get("selector_payload")
    selection_basis = manifest_item.get("selection_basis")
    source_identity = decision_item.get("source_identity")
    source_provenance = decision_item.get("source_provenance")
    decision_basis = decision_item.get("decision_basis")
    load_summary = decision_item.get("load_summary")
    payload = decision_item.get("payload")
    if not all(
        isinstance(value, Mapping)
        for value in (
            selector_payload,
            selection_basis,
            source_identity,
            source_provenance,
            decision_basis,
            load_summary,
            payload,
        )
    ):
        raise _basis_conflict()

    claims = db.query(L3GateBIdempotencyKey).filter(
        L3GateBIdempotencyKey.session_id == session.session_id
    ).all()
    manifests = db.query(L3SelectionManifest).filter(
        L3SelectionManifest.session_id == session.session_id
    ).all()
    descriptors = db.query(L3Descriptor).filter(
        L3Descriptor.session_id == session.session_id
    ).all()
    events = db.query(L3RetrievalEvent).filter(
        L3RetrievalEvent.session_id == session.session_id
    ).all()
    snapshots = db.query(L3MaterialSnapshot).filter(
        L3MaterialSnapshot.session_id == session.session_id
    ).all()
    if not (
        len(claims)
        == len(manifests)
        == len(descriptors)
        == len(events)
        == len(snapshots)
        == 1
    ):
        raise _basis_conflict()
    claim, descriptor, event = claims[0], descriptors[0], events[0]
    if (
        manifests[0].selection_manifest_id != manifest.selection_manifest_id
        or snapshots[0].material_snapshot_id != snapshot.material_snapshot_id
    ):
        raise _basis_conflict()

    candidate_id = str(decision_item.get("candidate_id") or "")
    expected_snapshot_identity = {
        "candidate_id": candidate_id,
        "source_class": F07_SOURCE_FAMILY,
        **dict(source_identity),
    }
    expected_provenance = dict(source_provenance) or dict(decision_basis)
    expected_load_summary = dict(load_summary) or {
        "loaded_records": 1,
        "failed_records": 0,
        "preview_material": True,
    }
    event_payload = event.event_payload_json
    loaded_items = event_payload.get("loaded_items") if isinstance(event_payload, Mapping) else None
    expected_loaded_item = {
        "material_snapshot_id": snapshot.material_snapshot_id,
        "source_plane": snapshot.source_plane,
        "source_shape": snapshot.source_shape,
        "payload_ref": snapshot.payload_ref,
        "payload_hash": snapshot.payload_hash,
    }
    expected_request_hash = gate_b_idempotency_request_hash(
        client_request_id=str(idempotency.get("client_request_id") or ""),
        preflight_id=str(idempotency.get("preflight_id") or ""),
        source_set_id=str(idempotency.get("source_set_id") or ""),
        material_preview_id=str(idempotency.get("material_preview_id") or ""),
        material_preview_hash=receipt.material_preview_hash,
        gate_b_decision_manifest_id=receipt.gate_b_decision_manifest_id,
    )
    expected_manifest_hash = gate_b_stable_hash(
        {
            "manifest_json": manifest_json,
            "source_plane_hints_json": hints,
        }
    )
    expected_descriptor_hash = gate_b_stable_hash(
        {
            "session_id": session.session_id,
            "source_plane": descriptor.source_plane,
            "descriptor_type": descriptor.descriptor_type,
            "selector_payload_json": descriptor.selector_payload_json,
            "selection_basis_json": descriptor.selection_basis_json,
            "expansion_reason": descriptor.expansion_reason,
        }
    )
    if (
        claim.status != GATE_B_IDEMPOTENCY_STATUS_COMMITTED
        or idempotency.get("schema_id") != GATE_B_IDEMPOTENCY_SCHEMA_ID
        or claim.session_id != session.session_id
        or claim.selection_manifest_id != manifest.selection_manifest_id
        or claim.client_request_id != idempotency.get("client_request_id")
        or claim.preflight_id != idempotency.get("preflight_id")
        or claim.source_set_id != idempotency.get("source_set_id")
        or claim.material_preview_id != idempotency.get("material_preview_id")
        or claim.material_preview_hash != receipt.material_preview_hash
        or claim.gate_b_decision_manifest_id != receipt.gate_b_decision_manifest_id
        or idempotency.get("material_preview_hash") != receipt.material_preview_hash
        or idempotency.get("gate_b_decision_manifest_id")
        != receipt.gate_b_decision_manifest_id
        or claim.request_basis_hash != expected_request_hash
        or manifest.selection_hash != expected_manifest_hash
        or hints.get("preflight_id") != idempotency.get("preflight_id")
        or hints.get("source_set_id") != idempotency.get("source_set_id")
        or hints.get("source_classes") != [F07_SOURCE_FAMILY]
        or summary.get("current_gate") != "gate_b"
        or summary.get("gate_b_summary_v1")
        != {"approved": 1, "denied": 0, "isolated": 0, "flagged": 0}
        or manifest_item.get("source_plane") != descriptor.source_plane
        or manifest_item.get("descriptor_type") != descriptor.descriptor_type
        or selector_payload != descriptor.selector_payload_json
        or selection_basis != descriptor.selection_basis_json
        or manifest_item.get("expansion_reason") != descriptor.expansion_reason
        or selector_payload.get("candidate_id") != candidate_id
        or selector_payload.get("source_ref") != decision_basis.get("source_ref")
        or selection_basis.get("query_basis") != decision_basis.get("query_basis")
        or selection_basis.get("provenance_ref") != decision_basis.get("provenance_ref")
        or selection_basis.get("gate_b_decision") != "approved"
        or descriptor.session_id != session.session_id
        or descriptor.selection_manifest_id != manifest.selection_manifest_id
        or descriptor.descriptor_type != F07_SOURCE_FAMILY
        or descriptor.status != "resolved_loaded"
        or descriptor.descriptor_hash != expected_descriptor_hash
        or event.session_id != session.session_id
        or event.descriptor_id != descriptor.descriptor_id
        or event.outcome != "loaded"
        or event.reason_code != "gate_b_approved_preview_material"
        or event.material_snapshot_ids_json != [snapshot.material_snapshot_id]
        or not isinstance(loaded_items, list)
        or loaded_items != [expected_loaded_item]
        or event_payload.get("failed_items") != []
        or event_payload.get("why") != event.reason_code
        or snapshot.descriptor_id != descriptor.descriptor_id
        or snapshot.source_plane != descriptor.source_plane
        or snapshot.source_identity_json != expected_snapshot_identity
        or snapshot.source_provenance_json != expected_provenance
        or snapshot.load_summary_json != expected_load_summary
        or snapshot.co_retrieval_group_id != event.retrieval_event_id
        or snapshot_payload != dict(payload)
    ):
        raise _basis_conflict()


def verify_existing_receipt_basis(
    db: OrmSession,
    receipt: L3ConnectorPromotionReceipt,
) -> tuple[L3Session, L3SelectionManifest, dict[str, Any]]:
    """Verify the immutable winning origin before any reuse."""
    session = db.get(L3Session, receipt.gate_b_session_id)
    manifest = db.get(L3SelectionManifest, receipt.gate_b_selection_manifest_id)
    snapshot = db.get(L3MaterialSnapshot, receipt.gate_b_material_snapshot_id)
    winner_intake = db.get(
        L3ConnectorSourceIntakeRecord,
        receipt.connector_source_intake_record_id,
    )
    if session is None or manifest is None or snapshot is None or winner_intake is None:
        raise _basis_conflict()
    if (
        receipt.receipt_schema_version != RECEIPT_SCHEMA_VERSION
        or receipt.identity_metadata_hash_version != IDENTITY_METADATA_HASH_VERSION
        or receipt.source_family != F07_SOURCE_FAMILY
        or receipt.content_sha256 != F07_CONTENT_SHA256
        or receipt.identity_metadata_hash != F07_IDENTITY_METADATA_HASH
        or receipt.canonical_identity_key_hash != F07_CANONICAL_IDENTITY_KEY_HASH
        or session.selection_manifest_id != manifest.selection_manifest_id
        or manifest.session_id != session.session_id
        or snapshot.session_id != session.session_id
        or snapshot.source_shape != F07_SOURCE_FAMILY
        or (
            winner_intake.identity_metadata_hash_version,
            winner_intake.identity_metadata_hash,
        )
        != (IDENTITY_METADATA_HASH_VERSION, F07_IDENTITY_METADATA_HASH)
    ):
        raise _basis_conflict()
    decision_manifest = _stored_decision_manifest(session)
    items = decision_manifest.get("items")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise _basis_conflict()
    item = items[0]
    expected_candidate_id = (
        f"{CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX}"
        f"{winner_intake.connector_source_intake_record_id}"
    )
    decision_basis = item.get("decision_basis")
    if (
        item.get("candidate_id") != expected_candidate_id
        or item.get("source_class") != F07_SOURCE_FAMILY
        or item.get("decision") != "approved"
        or not isinstance(decision_basis, Mapping)
        or not isinstance(snapshot.source_identity_json, Mapping)
        or snapshot.source_identity_json.get("candidate_id") != expected_candidate_id
    ):
        raise _basis_conflict()
    winner_candidate = GateBPromotionCandidate(
        candidate_id=expected_candidate_id,
        connector_source_intake_record_id=winner_intake.connector_source_intake_record_id,
        decision="approved",
        decision_basis=decision_basis,
    )
    try:
        winner_identity = _reconstruct_locked_identity(db, winner_candidate)
    except ConnectorPromotionError as exc:
        raise _basis_conflict() from exc
    if winner_identity.canonical_identity_key_hash != receipt.canonical_identity_key_hash:
        raise _basis_conflict()
    try:
        snapshot_root = (Path(settings.artifact_storage_dir) / "layer3").resolve()
        snapshot_path = Path(snapshot.payload_ref).resolve()
        snapshot_bytes = snapshot_path.read_bytes()
    except (OSError, TypeError, ValueError) as exc:
        raise _basis_conflict() from exc
    if (
        snapshot_path != snapshot_root
        and snapshot_root not in snapshot_path.parents
    ) or hashlib.sha256(snapshot_bytes).hexdigest() != snapshot.payload_hash:
        raise _basis_conflict()
    try:
        snapshot_payload = json.loads(snapshot_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _basis_conflict() from exc
    _verify_receipt_gate_b_spine(
        db,
        receipt=receipt,
        session=session,
        manifest=manifest,
        snapshot=snapshot,
        decision_item=item,
        snapshot_payload=snapshot_payload,
    )
    expected_manifest_id = gate_b_decision_manifest_id(decision_manifest)
    expected_manifest_hash = gate_b_stable_hash(decision_manifest)
    preview_bases = [
        item.get("material_preview_basis")
        if isinstance(item.get("material_preview_basis"), dict)
        else material_candidate_basis_from_decision(
            candidate_id=str(item.get("candidate_id") or "").strip(),
            source_class=str(item.get("source_class") or "").strip(),
            decision_basis=decision_basis,
        )
    ]
    expected_preview_hash = material_preview_hash(preview_bases)
    expected_approval_hash = decision_semantics_hash(
        "approved",
        IDENTITY_METADATA_HASH_VERSION,
        F07_SOURCE_FAMILY,
        F07_CONTENT_SHA256,
        F07_IDENTITY_METADATA_HASH,
    )
    expected_basis_hash = promotion_basis_hash(
        approval_hash=expected_approval_hash,
        gate_b_session_id=session.session_id,
        gate_b_selection_manifest_id=manifest.selection_manifest_id,
        gate_b_material_snapshot_id=snapshot.material_snapshot_id,
        gate_b_decision_manifest_id=expected_manifest_id,
        gate_b_decision_manifest_hash=expected_manifest_hash,
        material_preview_hash=expected_preview_hash,
        canonical_identity_key_hash=F07_CANONICAL_IDENTITY_KEY_HASH,
        identity_metadata_hash_version=IDENTITY_METADATA_HASH_VERSION,
        source_family=F07_SOURCE_FAMILY,
        content_sha256=F07_CONTENT_SHA256,
        identity_metadata_hash=F07_IDENTITY_METADATA_HASH,
        connector_source_intake_record_id=winner_intake.connector_source_intake_record_id,
    )
    if (
        receipt.gate_b_decision_manifest_id != expected_manifest_id
        or receipt.gate_b_decision_manifest_hash != expected_manifest_hash
        or receipt.material_preview_hash != expected_preview_hash
        or receipt.approval_hash != expected_approval_hash
        or receipt.promotion_basis_hash != expected_basis_hash
    ):
        raise _basis_conflict()
    return session, manifest, decision_manifest


def begin_gate_b_arbitration(
    db: OrmSession,
    candidate: GateBPromotionCandidate,
) -> GateBPromotionArbitration:
    acquire_promotion_identity_lock(db, F07_CANONICAL_IDENTITY_KEY_HASH)
    identity = _reconstruct_locked_identity(db, candidate)
    receipt = _receipt_for_identity(db)
    winning_origin = None
    if receipt is not None:
        winning_origin = verify_existing_receipt_basis(db, receipt)
        incoming_pair = (
            identity.record.identity_metadata_hash_version,
            identity.record.identity_metadata_hash,
        )
        if (
            identity.record.connector_source_intake_record_id
            != receipt.connector_source_intake_record_id
            and incoming_pair != (None, None)
        ):
            raise _not_eligible()
        if candidate.decision != "approved":
            raise _promotion_error(
                "promotion_identity_decision_conflict",
                "Promotion identity decision conflicts with the committed receipt.",
                http_status=409,
                retryable=False,
            )
    elif (
        identity.record.identity_metadata_hash_version,
        identity.record.identity_metadata_hash,
    ) != (None, None):
        raise _basis_conflict()
    return GateBPromotionArbitration(
        candidate=candidate,
        identity=identity,
        receipt=receipt,
        winning_origin=winning_origin,
    )


def promotion_result(
    candidate: GateBPromotionCandidate,
    disposition: str,
    receipt_id: str | None,
) -> dict[str, Any]:
    if disposition not in {"created", "reused", "none"}:
        raise PromotionIdentityError("invalid receipt disposition")
    if (disposition == "none") != (receipt_id is None):
        raise PromotionIdentityError("receipt disposition/id joint state is invalid")
    return {
        "candidate_id": candidate.candidate_id,
        "decision": candidate.decision,
        "receipt_disposition": disposition,
        "connector_promotion_receipt_id": receipt_id,
    }


def consume_gate_b_promotion_result(result: Mapping[str, Any]) -> None:
    """Internal-only sink; deliberately adds nothing to the Gate-B response."""
    if list(result) != [
        "candidate_id",
        "decision",
        "receipt_disposition",
        "connector_promotion_receipt_id",
    ]:
        raise PromotionIdentityError("invalid internal promotion result shape")


def stage_gate_b_promotion_receipt(
    db: OrmSession,
    arbitration: GateBPromotionArbitration,
    *,
    session: L3Session,
    manifest: L3SelectionManifest,
    snapshot: L3MaterialSnapshot,
    decision_manifest: dict[str, Any],
    submitted_material_preview_hash: str,
) -> dict[str, Any]:
    candidate = arbitration.candidate
    if arbitration.receipt is not None:
        return promotion_result(
            candidate,
            "reused",
            arbitration.receipt.connector_promotion_receipt_id,
        )
    if candidate.decision != "approved":
        return promotion_result(candidate, "none", None)
    decision_manifest_id = gate_b_decision_manifest_id(decision_manifest)
    decision_manifest_hash = gate_b_stable_hash(decision_manifest)
    approval_hash = decision_semantics_hash(
        "approved",
        IDENTITY_METADATA_HASH_VERSION,
        F07_SOURCE_FAMILY,
        F07_CONTENT_SHA256,
        F07_IDENTITY_METADATA_HASH,
    )
    basis_hash = promotion_basis_hash(
        approval_hash=approval_hash,
        gate_b_session_id=session.session_id,
        gate_b_selection_manifest_id=manifest.selection_manifest_id,
        gate_b_material_snapshot_id=snapshot.material_snapshot_id,
        gate_b_decision_manifest_id=decision_manifest_id,
        gate_b_decision_manifest_hash=decision_manifest_hash,
        material_preview_hash=submitted_material_preview_hash,
        canonical_identity_key_hash=F07_CANONICAL_IDENTITY_KEY_HASH,
        identity_metadata_hash_version=IDENTITY_METADATA_HASH_VERSION,
        source_family=F07_SOURCE_FAMILY,
        content_sha256=F07_CONTENT_SHA256,
        identity_metadata_hash=F07_IDENTITY_METADATA_HASH,
        connector_source_intake_record_id=(
            arbitration.identity.record.connector_source_intake_record_id
        ),
    )
    receipt_id = str(uuid.uuid4())
    receipt = L3ConnectorPromotionReceipt(
        connector_promotion_receipt_id=receipt_id,
        receipt_schema_version=RECEIPT_SCHEMA_VERSION,
        identity_metadata_hash_version=IDENTITY_METADATA_HASH_VERSION,
        source_family=F07_SOURCE_FAMILY,
        content_sha256=F07_CONTENT_SHA256,
        identity_metadata_hash=F07_IDENTITY_METADATA_HASH,
        canonical_identity_key_hash=F07_CANONICAL_IDENTITY_KEY_HASH,
        connector_source_intake_record_id=(
            arbitration.identity.record.connector_source_intake_record_id
        ),
        gate_b_session_id=session.session_id,
        gate_b_selection_manifest_id=manifest.selection_manifest_id,
        gate_b_material_snapshot_id=snapshot.material_snapshot_id,
        gate_b_decision_manifest_id=decision_manifest_id,
        gate_b_decision_manifest_hash=decision_manifest_hash,
        material_preview_hash=submitted_material_preview_hash,
        approval_hash=approval_hash,
        promotion_basis_hash=basis_hash,
    )
    arbitration.identity.record.identity_metadata_hash_version = IDENTITY_METADATA_HASH_VERSION
    arbitration.identity.record.identity_metadata_hash = F07_IDENTITY_METADATA_HASH
    db.add(receipt)
    return promotion_result(candidate, "created", receipt_id)


# ---------------------------------------------------------------------------
# Storage-reference hash domains (Section 4.2)
# ---------------------------------------------------------------------------

_STORAGE_REF_DOMAIN = b"project6-storage-ref-v1"
_DATASET_STORAGE_REF_DOMAIN = b"project6-dataset-storage-ref-v1"


def normalize_relative_ref(relative_path: str) -> str:
    """Normalize an already root-relative reference per the Section 4.2 rules.

    Containment/regular-file/reparse resolution against the configured root is
    the resolver's job (it holds the filesystem handles); this function
    enforces the pure path grammar: '/' separators, NFC, case preserved, no
    empty segments, '.', '..', drive prefix, UNC syntax, NUL, or leading/
    trailing slash.
    """
    if not isinstance(relative_path, str) or not relative_path:
        raise PromotionIdentityError("relative reference must be a nonempty string")
    if "\x00" in relative_path:
        raise PromotionIdentityError("relative reference contains NUL")
    ref = unicodedata.normalize("NFC", relative_path.replace("\\", "/"))
    if ref.startswith("/") or ref.endswith("/"):
        raise PromotionIdentityError("leading/trailing slash forbidden")
    if ref.startswith("\\\\") or "//" in ref:
        raise PromotionIdentityError("UNC syntax or empty segment forbidden")
    if len(ref) >= 2 and ref[1] == ":":
        raise PromotionIdentityError("drive prefix forbidden")
    segments = ref.split("/")
    if any(seg in ("", ".", "..") for seg in segments):
        raise PromotionIdentityError("empty, '.', or '..' segment forbidden")
    return ref


def storage_ref_hash(relative_ref: str) -> str:
    ref = normalize_relative_ref(relative_ref)
    return hashlib.sha256(_STORAGE_REF_DOMAIN + b"\x00" + ref.encode("utf-8")).hexdigest()


def dataset_storage_ref_hash(relative_ref: str) -> str:
    ref = normalize_relative_ref(relative_ref)
    return hashlib.sha256(_DATASET_STORAGE_REF_DOMAIN + b"\x00" + ref.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Materialization basis and record (Section 4.2)
# ---------------------------------------------------------------------------

_EXPECTED_OUTPUT = {
    "column_count": 2,
    "columns": [
        {"logical_type": "categorical_string", "name": "site_id"},
        {"logical_type": "numeric_integer", "name": "value"},
    ],
    "dropped_row_count": 0,
    "row_count": 2,
    "source_row_count": 2,
}

_HEX40 = frozenset("0123456789abcdef")


def _require_lower_hex40(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or not set(value) <= _HEX40:
        raise PromotionIdentityError(f"{field} must be lowercase 40-hex")
    return value


def build_materialization_basis(
    *,
    dataframe_io_git_blob: str,
    implementation_commit: str,
    ingest_git_blob: str,
    promotion_git_blob: str,
    input_storage_ref_hash: str,
    connector_run_id: str,
    connector_run_target_id: str,
    connector_source_intake_record_id: str,
    gate_b_material_snapshot_id: str,
    gate_b_selection_manifest_id: str,
    gate_b_session_id: str,
    canonical_identity_key_hash: str,
    connector_promotion_receipt_id: str,
    promotion_basis_hash: str,
) -> dict:
    return {
        "code": {
            "dataframe_io_git_blob": _require_lower_hex40(dataframe_io_git_blob, "dataframe_io_git_blob"),
            "implementation_commit": _require_lower_hex40(implementation_commit, "implementation_commit"),
            "ingest_git_blob": _require_lower_hex40(ingest_git_blob, "ingest_git_blob"),
            "metadata_contract_sha256": METADATA_CONTRACT_SHA256,
            "promotion_git_blob": _require_lower_hex40(promotion_git_blob, "promotion_git_blob"),
        },
        "expected_output": json.loads(json.dumps(_EXPECTED_OUTPUT)),
        "input": {
            "bytes": F07_CONTENT_BYTES,
            "content_sha256": F07_CONTENT_SHA256,
            "storage_ref_hash": _require_lower_hex64(input_storage_ref_hash, "storage_ref_hash"),
        },
        "lineage": {
            "connector_run_id": _clean_required_string(connector_run_id, "connector_run_id"),
            "connector_run_target_id": _clean_required_string(connector_run_target_id, "connector_run_target_id"),
            "connector_source_intake_record_id": _clean_required_string(
                connector_source_intake_record_id, "connector_source_intake_record_id"
            ),
            "gate_b_material_snapshot_id": _clean_required_string(
                gate_b_material_snapshot_id, "gate_b_material_snapshot_id"
            ),
            "gate_b_selection_manifest_id": _clean_required_string(
                gate_b_selection_manifest_id, "gate_b_selection_manifest_id"
            ),
            "gate_b_session_id": _clean_required_string(gate_b_session_id, "gate_b_session_id"),
        },
        "receipt": {
            "canonical_identity_key_hash": _require_lower_hex64(
                canonical_identity_key_hash, "canonical_identity_key_hash"
            ),
            "connector_promotion_receipt_id": _clean_required_string(
                connector_promotion_receipt_id, "connector_promotion_receipt_id"
            ),
            "promotion_basis_hash": _require_lower_hex64(promotion_basis_hash, "promotion_basis_hash"),
        },
        "schema_id": MATERIALIZATION_BASIS_SCHEMA_ID,
        "transformation": {
            "contract_sha256": TRANSFORM_CONTRACT_SHA256,
            "method_input_sha256": METHOD_INPUT_SHA256,
            "parameters": {},
            "schema_id": TRANSFORM_SCHEMA_ID,
            "version": TRANSFORM_VERSION,
        },
    }


def materialization_basis_hash(basis: dict) -> str:
    if basis.get("schema_id") != MATERIALIZATION_BASIS_SCHEMA_ID:
        raise PromotionIdentityError("not a materialization basis object")
    return d33_sha256(basis)


def build_materialization_record(
    *,
    basis_hash: str,
    dataset_file_bytes: int,
    dataset_file_sha256: str,
    dataset_id: str,
    dataset_source_provenance_id: str,
    dataset_storage_ref_hash: str,
    dataset_version_content_sha256: str,
    dataset_version_id: str,
    promoted_session_id: str,
    source_connector_id: str,
) -> dict:
    if not isinstance(dataset_file_bytes, int) or isinstance(dataset_file_bytes, bool) or dataset_file_bytes <= 0:
        raise PromotionIdentityError("dataset_file_bytes must be a positive integer")
    return {
        "basis_hash": _require_lower_hex64(basis_hash, "basis_hash"),
        "output": {
            "dataset_file_bytes": dataset_file_bytes,
            "dataset_file_sha256": _require_lower_hex64(dataset_file_sha256, "dataset_file_sha256"),
            "dataset_id": _clean_required_string(dataset_id, "dataset_id"),
            "dataset_source_provenance_id": _clean_required_string(
                dataset_source_provenance_id, "dataset_source_provenance_id"
            ),
            "dataset_storage_ref_hash": _require_lower_hex64(dataset_storage_ref_hash, "dataset_storage_ref_hash"),
            "dataset_version_content_sha256": _require_lower_hex64(
                dataset_version_content_sha256, "dataset_version_content_sha256"
            ),
            "dataset_version_id": _clean_required_string(dataset_version_id, "dataset_version_id"),
            "dropped_row_count": 0,
            "promoted_session_id": _clean_required_string(promoted_session_id, "promoted_session_id"),
            "row_count": 2,
            "source_connector_id": _clean_required_string(source_connector_id, "source_connector_id"),
            "source_row_count": 2,
            "variable_count": 2,
        },
        "schema_id": MATERIALIZATION_RECORD_SCHEMA_ID,
    }


def materialization_record_hash(record: dict) -> str:
    if record.get("schema_id") != MATERIALIZATION_RECORD_SCHEMA_ID:
        raise PromotionIdentityError("not a materialization record object")
    return d33_sha256(record)


def build_materialization_wrapper(record: dict) -> dict:
    """The exact persisted wrapper: ``{"record": <record>, "record_hash": <hash>}``.

    ``record_hash`` is the D33-canonical SHA-256 of the inner record object
    only; the wrapper itself is never separately hashed.
    """
    return {"record": record, "record_hash": materialization_record_hash(record)}


MATERIALIZATION_CONTEXT_KEY = "layer3_connector_promotion_materialization_v1"
MATERIALIZATION_RESPONSE_SCHEMA_ID = "layer3.connector_promotion_resolve_response.v1"


def _closed_b1b_error(error_code: str) -> B1BClosedApiError:
    http_status, message, retryable = b1b_error_spec(error_code)
    return B1BClosedApiError(
        error_code,
        message,
        http_status=http_status,
        retryable=retryable,
    )


def _git_text(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PromotionIdentityError("unable to read audited Git code identity") from exc
    return result.stdout.strip()


def _read_clean_materialization_code_identity() -> dict[str, str]:
    """Re-read the tracked-clean HEAD and three bound blobs immediately pre-claim."""
    repo_root = Path(__file__).resolve().parents[3]
    if _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no"):
        raise PromotionIdentityError("tracked checkout is dirty")
    head_before = _git_text(repo_root, "rev-parse", "HEAD")
    values = {
        "implementation_commit": head_before,
        "promotion_git_blob": _git_text(
            repo_root,
            "rev-parse",
            f"{head_before}:backend/app/services/layer3_connector_promotion.py",
        ),
        "ingest_git_blob": _git_text(
            repo_root,
            "rev-parse",
            f"{head_before}:backend/app/services/ingest.py",
        ),
        "dataframe_io_git_blob": _git_text(
            repo_root,
            "rev-parse",
            f"{head_before}:backend/app/services/dataframe_io.py",
        ),
    }
    if (
        _git_text(repo_root, "rev-parse", "HEAD") != head_before
        or _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise PromotionIdentityError("audited Git code identity changed during re-read")
    return {key: _require_lower_hex40(value, key) for key, value in values.items()}


def _is_reparse(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise PromotionIdentityError("storage reference is unavailable") from exc
    return bool(path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400)


def _require_nonreparse_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    component = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        component /= part
        if not os.path.lexists(component):
            raise PromotionIdentityError("storage path component is unavailable")
        if _is_reparse(component):
            raise PromotionIdentityError("storage path contains a reparse component")


def _resolve_regular_reference(raw_ref: str, root_ref: str) -> tuple[Path, str]:
    if not isinstance(raw_ref, str) or not raw_ref or "\x00" in raw_ref:
        raise PromotionIdentityError("storage reference is invalid")
    root_input = Path(root_ref)
    if not root_input.exists() or not root_input.is_dir():
        raise PromotionIdentityError("storage root is invalid")
    if _is_reparse(root_input):
        raise PromotionIdentityError("storage root contains a reparse point")
    _require_nonreparse_components(root_input)
    root = root_input.resolve(strict=True)
    candidate = Path(raw_ref)
    candidate = candidate if candidate.is_absolute() else root / candidate
    try:
        lexical_relative = candidate.relative_to(root)
    except ValueError as exc:
        raise PromotionIdentityError("storage reference escapes its configured root") from exc
    if any(part in {"", ".", ".."} for part in lexical_relative.parts):
        raise PromotionIdentityError("storage reference has a forbidden path segment")
    component = root
    for part in lexical_relative.parts:
        component /= part
        if component.exists() and _is_reparse(component):
            raise PromotionIdentityError("storage reference contains a reparse component")
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root)
        mode = resolved.stat().st_mode
    except (OSError, ValueError) as exc:
        raise PromotionIdentityError("storage reference escapes its configured root") from exc
    if not stat.S_ISREG(mode):
        raise PromotionIdentityError("storage reference is not a regular file")
    normalized = normalize_relative_ref(relative.as_posix())
    return resolved, normalized


def _file_facts(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise PromotionIdentityError("unable to re-read materialization file") from exc
    return size, digest.hexdigest()


def _atomic_rename_no_overwrite(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"materialization destination exists: {destination}")
    if not destination.parent.is_dir() or _is_reparse(destination.parent):
        raise PromotionIdentityError("materialization destination parent is invalid")
    if _is_reparse(source) or not stat.S_ISREG(source.stat().st_mode):
        raise PromotionIdentityError("materialization source is not a regular non-reparse file")
    if source.stat().st_dev != destination.parent.stat().st_dev:
        raise PromotionIdentityError("materialization publish crosses volumes")
    if os.name == "nt":
        os.rename(source, destination)
        return
    try:
        import ctypes
        import errno

        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
        result = renameat2(
            -100,
            os.fsencode(source),
            -100,
            os.fsencode(destination),
            1,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number), str(destination))
    except AttributeError as exc:
        raise OSError("atomic no-overwrite rename is unavailable") from exc
    except OSError as exc:
        if getattr(exc, "errno", None) == errno.EEXIST:
            raise FileExistsError(str(destination)) from exc
        raise


_CONTAINMENT_RECORD_SUFFIX = ".containment.json"


def _containment_record_path(artifact: Path) -> Path:
    return artifact.with_name(artifact.name + _CONTAINMENT_RECORD_SUFFIX)


def _write_containment_record(record_path: Path, record: Mapping[str, Any]) -> None:
    record_bytes = d33_canonical_bytes(dict(record))
    if record_path.exists():
        if _is_reparse(record_path) or not stat.S_ISREG(record_path.stat().st_mode):
            raise PromotionIdentityError("containment record is not a regular file")
        existing = record_path.read_bytes()
        if existing == record_bytes:
            return
        if not record_bytes.startswith(existing):
            raise PromotionIdentityError("containment record conflicts with artifact facts")
        with record_path.open("ab") as handle:
            handle.write(record_bytes[len(existing) :])
            handle.flush()
            os.fsync(handle.fileno())
        if record_path.read_bytes() != record_bytes:
            raise PromotionIdentityError("containment record recovery did not converge")
        return
    with record_path.open("xb") as handle:
        handle.write(record_bytes)
        handle.flush()
        os.fsync(handle.fileno())


def _contained_artifact_record(artifact: Path, containment_root: Path) -> dict[str, Any]:
    try:
        relative = artifact.relative_to(containment_root)
    except ValueError as exc:
        raise PromotionIdentityError("contained artifact escapes containment root") from exc
    if len(relative.parts) != 3:
        raise PromotionIdentityError("contained artifact path shape is invalid")
    prefix, basis_hash, artifact_name = relative.parts
    _require_lower_hex64(basis_hash, "containment basis_hash")
    if prefix != basis_hash[:2] or not artifact.suffix:
        raise PromotionIdentityError("contained artifact basis namespace is invalid")
    stem = artifact_name[: -len(artifact.suffix)]
    name_parts = stem.split("-")
    if len(name_parts) not in {2, 3}:
        raise PromotionIdentityError("contained artifact name is invalid")
    namespace_hash = _require_lower_hex64(name_parts[0], "containment namespace_hash")
    name_digest = _require_lower_hex64(name_parts[1], "containment artifact_sha256")
    size, digest = _file_facts(artifact)
    if digest != name_digest:
        raise PromotionIdentityError("contained artifact hash conflicts with its name")
    return {
        "artifact_bytes": size,
        "artifact_sha256": digest,
        "basis_hash": basis_hash,
        "namespace_hash": namespace_hash,
        "status": "non_authoritative_non_reusable",
    }


def _reconcile_containment_records(containment_root: Path) -> None:
    files = _regular_lane_files(containment_root)
    artifacts = [path for path in files if not path.name.endswith(_CONTAINMENT_RECORD_SUFFIX)]
    for artifact in artifacts:
        record = _contained_artifact_record(artifact, containment_root)
        _write_containment_record(_containment_record_path(artifact), record)
    for record_path in files:
        if not record_path.name.endswith(_CONTAINMENT_RECORD_SUFFIX):
            continue
        artifact = record_path.with_name(record_path.name[: -len(_CONTAINMENT_RECORD_SUFFIX)])
        if not artifact.is_file() or _is_reparse(artifact):
            raise PromotionIdentityError("containment record has no regular artifact")


def _contain_file(
    source: Path,
    *,
    containment_root: Path,
    basis_hash: str,
    namespace: str,
) -> Path | None:
    if not source.exists():
        return None
    _require_lower_hex64(basis_hash, "containment basis_hash")
    _size, digest = _file_facts(source)
    namespace_hash = d33_sha256(
        {
            "basis_hash": basis_hash,
            "namespace": namespace,
            "source_name": unicodedata.normalize("NFC", source.name),
        }
    )
    destination_dir = containment_root / basis_hash[:2] / basis_hash
    _ensure_nonreparse_lane_directory(destination_dir, containment_root)
    destination = destination_dir / f"{namespace_hash}-{digest}{source.suffix}"
    record_path = _containment_record_path(destination)
    if destination.exists() or record_path.exists():
        destination = destination_dir / f"{namespace_hash}-{digest}-{uuid.uuid4().hex}{source.suffix}"
        record_path = _containment_record_path(destination)
    _atomic_rename_no_overwrite(source, destination)
    _write_containment_record(
        record_path,
        _contained_artifact_record(destination, containment_root),
    )
    return destination


def _lane_paths(basis_hash: str) -> dict[str, Path]:
    dataset_root = Path(settings.dataset_storage_dir)
    artifact_custody_root = Path(settings.artifact_storage_dir)
    artifact_root = artifact_custody_root / "layer3"
    return {
        "dataset_root": dataset_root,
        "stage_root": dataset_root / "b1b" / "staging",
        "dataset_final_root": dataset_root / "b1b" / "dataset-versions",
        "final": dataset_root / "b1b" / "dataset-versions" / basis_hash[:2] / f"{basis_hash}.parquet",
        "dataset_containment": dataset_root / "b1b" / "containment",
        "artifact_custody_root": artifact_custody_root,
        "artifact_root": artifact_root,
        "artifact_stage_root": artifact_root / "b1b-staging",
        "artifact_final_root": artifact_root / "b1b",
        "artifact_containment": artifact_root / "b1b-containment",
    }


def _ensure_nonreparse_directory_tree(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    component = Path(absolute.anchor)
    if _is_reparse(component) or not component.is_dir():
        raise PromotionIdentityError("materialization path anchor is invalid")
    for part in absolute.parts[1:]:
        component /= part
        if not os.path.lexists(component):
            try:
                component.mkdir()
            except FileExistsError:
                pass
        if _is_reparse(component) or not component.is_dir():
            raise PromotionIdentityError("materialization path contains a reparse component")
    return absolute


def _ensure_nonreparse_lane_directory(path: Path, custody_root: Path) -> None:
    root = _ensure_nonreparse_directory_tree(custody_root)
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise PromotionIdentityError("materialization directory escapes custody root") from exc
    component = root
    for part in relative.parts:
        component /= part
        if not os.path.lexists(component):
            try:
                component.mkdir()
            except FileExistsError:
                pass
        if _is_reparse(component) or not component.is_dir():
            raise PromotionIdentityError("materialization directory contains a reparse component")
    try:
        absolute.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise PromotionIdentityError("materialization directory escapes custody root") from exc


def _regular_lane_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if _is_reparse(path):
            raise PromotionIdentityError("materialization lane contains a reparse entry")
        if path.is_file():
            if not stat.S_ISREG(path.stat().st_mode):
                raise PromotionIdentityError("materialization lane contains a nonregular entry")
            files.append(path)
        elif not path.is_dir():
            raise PromotionIdentityError("materialization lane contains an unsupported entry")
    return files


def _lane_file_basis(path: Path, lane_root: Path, *, layout: str) -> str:
    try:
        relative = path.relative_to(lane_root)
    except ValueError as exc:
        raise PromotionIdentityError("lane artifact escapes its lane root") from exc
    if layout == "basis-dirs" and len(relative.parts) >= 3:
        prefix, basis_hash = relative.parts[:2]
        _require_lower_hex64(basis_hash, "lane artifact basis_hash")
        if prefix == basis_hash[:2]:
            return basis_hash
    elif layout == "basis-file" and len(relative.parts) == 2:
        prefix, artifact_name = relative.parts
        basis_hash = Path(artifact_name).stem
        _require_lower_hex64(basis_hash, "lane artifact basis_hash")
        if prefix == basis_hash[:2]:
            return basis_hash
    elif layout == "basis-prefix":
        basis_hash = relative.name.split("-", 1)[0]
        _require_lower_hex64(basis_hash, "lane artifact basis_hash")
        return basis_hash
    raise PromotionIdentityError("lane artifact has no derivable basis")


def _contain_unreferenced_lane_files(
    db: OrmSession,
    *,
    paths: Mapping[str, Path],
    authoritative_final: Path | None = None,
) -> None:
    _reconcile_containment_records(paths["dataset_containment"])
    _reconcile_containment_records(paths["artifact_containment"])
    committed_version_ids = {
        value
        for (value,) in db.query(L3ConnectorPromotionReceipt.dataset_version_id)
        .filter(L3ConnectorPromotionReceipt.materialization_status == "materialized")
        .all()
        if value
    }
    referenced_dataset_files = {
        Path(value).resolve()
        for (value,) in db.query(DatasetVersion.storage_ref)
        .filter(DatasetVersion.dataset_version_id.in_(committed_version_ids))
        .all()
        if value
    } if committed_version_ids else set()
    if authoritative_final is not None:
        referenced_dataset_files.add(authoritative_final.resolve())
    for path in _regular_lane_files(paths["dataset_final_root"]):
        if path.resolve() not in referenced_dataset_files:
            _contain_file(
                path,
                containment_root=paths["dataset_containment"],
                basis_hash=_lane_file_basis(
                    path,
                    paths["dataset_final_root"],
                    layout="basis-file",
                ),
                namespace="deterministic-final",
            )
    for path in _regular_lane_files(paths["stage_root"]):
        _contain_file(
            path,
            containment_root=paths["dataset_containment"],
            basis_hash=_lane_file_basis(path, paths["stage_root"], layout="basis-prefix"),
            namespace="parquet-staging",
        )
    for path in _regular_lane_files(paths["artifact_stage_root"]):
        _contain_file(
            path,
            containment_root=paths["artifact_containment"],
            basis_hash=_lane_file_basis(
                path,
                paths["artifact_stage_root"],
                layout="basis-dirs",
            ),
            namespace="snapshot-staging",
        )
    committed_session_ids = {
        value
        for (value,) in db.query(L3ConnectorPromotionReceipt.promoted_session_id)
        .filter(L3ConnectorPromotionReceipt.materialization_status == "materialized")
        .all()
        if value
    }
    referenced_snapshots = {
        Path(value).resolve()
        for (value,) in db.query(L3MaterialSnapshot.payload_ref)
        .filter(L3MaterialSnapshot.session_id.in_(committed_session_ids))
        .all()
    } if committed_session_ids else set()
    for path in _regular_lane_files(paths["artifact_final_root"]):
        if path.resolve() not in referenced_snapshots:
            _contain_file(
                path,
                containment_root=paths["artifact_containment"],
                basis_hash=_lane_file_basis(
                    path,
                    paths["artifact_final_root"],
                    layout="basis-dirs",
                ),
                namespace="snapshot-final",
            )


def _before_materialization_publish() -> None:
    """Fault-injection seam; production is a no-op."""


def _after_materialization_publish() -> None:
    """Crash/fault-injection seam immediately after the Parquet rename."""


def _validated_existing_f07_frame(raw_path: Path):
    raw_bytes = raw_path.read_bytes()
    _reproduce_f07_transform(raw_bytes)
    existing = read_existing_csv_reference(
        raw_path,
        expected_sha256=F07_CONTENT_SHA256,
        expected_size_bytes=F07_CONTENT_BYTES,
    )
    frame = existing.dataframe.copy()
    if (
        existing.encoding != "utf-8"
        or existing.source_row_count != 2
        or list(frame.columns) != ["site_id", "value"]
        or frame["site_id"].tolist() != ["SB-001", "SB-002"]
        or frame["value"].tolist() != [42, 43]
    ):
        raise PromotionIdentityError("existing CSV reference does not reproduce F07")
    frame["site_id"] = frame["site_id"].astype("object")
    frame["value"] = frame["value"].astype("float64")
    return frame


def _build_resolver_basis(
    *,
    receipt: L3ConnectorPromotionReceipt,
    intake: L3ConnectorSourceIntakeRecord,
    target: ConnectorRunTarget,
    input_relative_ref: str,
    code_identity: Mapping[str, str],
) -> tuple[dict[str, Any], str]:
    basis = build_materialization_basis(
        dataframe_io_git_blob=code_identity["dataframe_io_git_blob"],
        implementation_commit=code_identity["implementation_commit"],
        ingest_git_blob=code_identity["ingest_git_blob"],
        promotion_git_blob=code_identity["promotion_git_blob"],
        input_storage_ref_hash=storage_ref_hash(input_relative_ref),
        connector_run_id=intake.connector_run_id,
        connector_run_target_id=target.connector_run_target_id,
        connector_source_intake_record_id=intake.connector_source_intake_record_id,
        gate_b_material_snapshot_id=receipt.gate_b_material_snapshot_id,
        gate_b_selection_manifest_id=receipt.gate_b_selection_manifest_id,
        gate_b_session_id=receipt.gate_b_session_id,
        canonical_identity_key_hash=receipt.canonical_identity_key_hash,
        connector_promotion_receipt_id=receipt.connector_promotion_receipt_id,
        promotion_basis_hash=receipt.promotion_basis_hash,
    )
    return basis, materialization_basis_hash(basis)


def _materialization_response(
    receipt: L3ConnectorPromotionReceipt,
    *,
    disposition: str,
    record_hash: str,
) -> dict[str, Any]:
    if disposition not in {"materialized", "reused"}:
        raise PromotionIdentityError("invalid materialization disposition")
    return {
        "approval_hash": receipt.approval_hash,
        "canonical_identity_key_hash": receipt.canonical_identity_key_hash,
        "connector_promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "dataset_id": receipt.dataset_id,
        "dataset_version_id": receipt.dataset_version_id,
        "disposition": disposition,
        "gate_b_session_id": receipt.gate_b_session_id,
        "materialization_basis_hash": receipt.materialization_basis_hash,
        "materialization_record_hash": record_hash,
        "promoted_session_id": receipt.promoted_session_id,
        "promotion_basis_hash": receipt.promotion_basis_hash,
        "row_count": 2,
        "schema_id": MATERIALIZATION_RESPONSE_SCHEMA_ID,
        "source_row_count": 2,
        "variable_count": 2,
    }


def _materialization_manifest_item(
    *,
    dataset_version_id: str,
    receipt_id: str,
    basis_hash: str,
) -> dict[str, Any]:
    return {
        "source_plane": "dataset",
        "descriptor_type": "dataset_version",
        "selector_payload": {"dataset_version_id": dataset_version_id},
        "selection_basis": {
            "connector_promotion_receipt_id": receipt_id,
            "materialization_basis_hash": basis_hash,
        },
        "expansion_reason": "connector_promotion_materialization",
        "status": "expanded",
    }


def _model_matches_profile(
    row: Any,
    profile: Mapping[str, Any],
    *,
    excluded: frozenset[str] = frozenset(),
) -> bool:
    return all(getattr(row, key) == value for key, value in profile.items() if key not in excluded)


_MATERIALIZED_REPLAY_BASE = {
    "descriptor_status_counts": {"resolved_loaded": 1},
    "retrieval_outcome_counts": {"loaded": 1},
    "loaded_snapshot_count": 1,
    "source_planes": ["dataset"],
    "warning_reasons": ["synthetic_non_official_fixture"],
    "retrieved_descriptor_count": 1,
    "unresolved_descriptor_count": 0,
    "descriptor_coverage_status": "complete",
}
_PLAN_APPROVAL_KEYS = frozenset(
    {
        "analysis_plan_id",
        "approved_set_count",
        "excluded_set_count",
        "planned_pass_count",
        "source_preview_id",
        "source_preview_hash",
        "source_gate",
        "approval_only",
        "execution_started",
    }
)
_EXECUTION_SELECTION_KEYS = frozenset(
    {
        "schema_id",
        "state",
        "client_request_id",
        "analysis_plan_id",
        "source_preview_id",
        "source_preview_hash",
        "pass_run_ids_json",
        "pass_run_count",
        "execution_started",
        "analysis_run_ids_json",
        "downstream_unavailable",
        "operator_reason_recorded",
        "selected_at",
    }
)
_ANALYSIS_EXECUTION_START_KEYS = frozenset(
    {
        "schema_id",
        "client_request_id",
        "state",
        "analysis_plan_id",
        "pass_run_id",
        "source_preview_id",
        "source_preview_hash",
        "analysis_run_id",
        "pass_run_status",
        "output_payload_ref",
        "downstream_unavailable",
        "operator_reason_recorded",
        "started_at",
        "completed_at",
    }
)
_B1B_SESSION_STATE_KEYS = frozenset(
    {
        "schema_id",
        "review_record_ref",
        "review_state",
        "result_review_hash",
        "analysis_plan_id",
        "pass_run_id",
        "analysis_run_id",
        "package_review_state",
        "package_review_hash",
        "reconciliation_record_id",
        "packages",
        "connector_dataset_handoff_basis_hash",
    }
)
_RESULT_REVIEW_RECORD_KEYS = frozenset(
    {
        "schema_id",
        "promotion_receipt_id",
        "promoted_session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "result_payload_sha256",
        "analysis_artifact_id",
        "analysis_artifact_sha256",
        "assumption_check_ids",
        "caveat_note_id",
        "reviewed_output_items",
        "unresolved_trace_count",
        "operator_decision",
        "review_notes",
        "result_review_request_basis_hash",
    }
)
_PACKAGE_REVIEW_RECORD_KEYS = frozenset(
    {
        "schema_id",
        "review_request_basis_hash",
        "package_review_preview_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_hashes",
        "operator_decision",
        "decision_notes",
    }
)
_RESULT_REVIEW_STATES = {
    "approved": "execution_result_review_approved",
    "changes_requested": "execution_result_review_changes_requested",
    "rejected": "execution_result_review_rejected",
    "blocked": "execution_result_review_blocked",
}
_PACKAGE_REVIEW_STATES = {
    "approved": "package_review_approved",
    "changes_requested": "package_review_changes_requested",
    "rejected": "package_review_rejected",
    "blocked": "package_review_blocked",
}
_REPLAY_DOWNSTREAM_UNAVAILABLE = ["results", "package", "handoff"]
_B1B_PACKAGE_ORDER = ["canonical_internal", "user_facing", "review_facing"]
_B1B_MEMBER_PATHS = (
    "dataset-lineage.json",
    "canonical-3c.json",
    "analysis-plan-pass.json",
    "result-review.json",
    "package-manifest.json",
    "package-rehash.json",
    "same-origin-handoff.json",
    "downstream-replay.json",
    "b1b-verdict.json",
)
_B1B_RESULT_REVIEW_REQUEST_KEYS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "operator_decision",
        "review_notes",
    }
)
_B1B_PACKAGE_PREVIEW_REQUEST_KEYS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "result_review_record_ref",
    }
)
_B1B_PACKAGE_COMMIT_REQUEST_KEYS = _B1B_PACKAGE_PREVIEW_REQUEST_KEYS | {
    "client_request_id",
    "package_review_preview_hash",
    "expected_package_kinds",
}
_B1B_PACKAGE_SUBMIT_REQUEST_KEYS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "operator_decision",
        "decision_notes",
        "expected_package_kinds",
    }
)
_B1B_RECONCILIATION_SUMMARY_KEYS = frozenset(
    {
        "schema_id",
        "profile",
        "source_gate",
        "promotion_receipt_id",
        "promoted_session_id",
        "result_review_hash",
        "package_review_preview_hash",
        "package_set",
        "package_review_submit",
        "package_review_hash",
        "connector_dataset_handoff_basis",
        "connector_dataset_handoff_basis_hash",
    }
)
_B1B_PACKAGE_SET_KEYS = frozenset(
    {
        "construction_basis_hash",
        "member_count",
        "bundle_index_order_hash",
        "package_manifest_sha256",
        "package_rehash_sha256",
        "packages",
    }
)
_B1B_RESULT_REVIEW_RESPONSE_KEYS = frozenset(
    {
        "schema_id",
        "promotion_receipt_id",
        "promoted_session_id",
        "analysis_plan_id",
        "pass_run_id",
        "analysis_run_id",
        "operator_decision",
        "review_state",
        "result_review_hash",
        "review_notes_present",
        "review_notes_sha256",
        "package_review_preview_enabled",
    }
)
_B1B_ERROR_BODY_KEYS = frozenset(
    {"schema_id", "status", "error_code", "message", "retryable"}
)
_B1B_PACKAGE_PREVIEW_RESPONSE_KEYS = frozenset(
    {
        "schema_id",
        "promotion_receipt_id",
        "promoted_session_id",
        "analysis_plan_id",
        "pass_run_id",
        "analysis_run_id",
        "result_review_hash",
        "package_review_preview_hash",
        "candidate_package_kinds",
        "member_count",
        "package_contract_schema_id",
        "correction_full_sha256",
    }
)
_B1B_PACKAGE_COMMIT_RESPONSE_KEYS = frozenset(
    {
        "schema_id",
        "promotion_receipt_id",
        "promoted_session_id",
        "analysis_plan_id",
        "pass_run_id",
        "analysis_run_id",
        "result_review_hash",
        "package_review_preview_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "packages",
        "package_count",
        "member_count",
        "persistence_status",
    }
)
_B1B_PACKAGE_SUBMIT_RESPONSE_KEYS = frozenset(
    {
        "schema_id",
        "promotion_receipt_id",
        "promoted_session_id",
        "analysis_plan_id",
        "pass_run_id",
        "analysis_run_id",
        "result_review_hash",
        "package_review_preview_hash",
        "construction_basis_hash",
        "package_review_hash",
        "reconciliation_record_id",
        "packages",
        "operator_decision",
        "package_review_state",
        "decision_notes_present",
        "decision_notes_sha256",
        "handoff_eligibility_status",
    }
)
_B1B_PACKAGE_SUBMIT_APPROVED_RESPONSE_KEYS = _B1B_PACKAGE_SUBMIT_RESPONSE_KEYS | {
    "connector_dataset_handoff_basis_hash"
}
_B1B_ASSUMPTION_CHECK_CONTRACT = (
    ("data_availability", "dataframe_shape", "pass", "high", "rows=2; columns=2"),
    (
        "column_classification",
        "deterministic_dtype_scan",
        "pass",
        "medium",
        '{"categorical": 1, "numeric": 1}',
    ),
    (
        "missingness_scan",
        "cell_missingness",
        "pass",
        "medium",
        "missing_cells=0; missing_fraction=0.000000",
    ),
    (
        "time_column_coverage",
        "declared_time_column_scan",
        "warn",
        "medium",
        "time_column=; present=False",
    ),
)
_B1B_CAVEAT_CONTRACT = (
    "non_time_series_interpretation",
    "medium",
    "Dataset does not declare a usable time column; descriptive summary is non-time-series only.",
)
_B1B_BOUNDED_RESULT = {
    "row_count": 2,
    "column_count": 2,
    "class_counts": {"numeric": 1, "categorical": 1, "boolean": 0, "time": 0},
    "missing_cells": 0,
    "missing_fraction": 0.0,
    "columns": [
        {
            "name": "site_id",
            "inferred_class": "categorical",
            "non_null_count": 2,
            "missing_count": 0,
            "missing_fraction": 0.0,
            "unsupported_nested_values": False,
            "unique_count": 2,
            "top_values": [
                {"value": "SB-001", "count": 1},
                {"value": "SB-002", "count": 1},
            ],
        },
        {
            "name": "value",
            "inferred_class": "numeric",
            "non_null_count": 2,
            "missing_count": 0,
            "missing_fraction": 0.0,
            "unsupported_nested_values": False,
            "numeric_summary": {
                "non_null_count": 2,
                "min": 42.0,
                "max": 43.0,
                "mean": 42.5,
                "median": 42.5,
                "std_dev": 0.7071067811865476,
            },
            "top_values": [{"value": 42, "count": 1}, {"value": 43, "count": 1}],
        },
    ],
}


def _has_exact_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _is_lower_hex64(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_uuid_string(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def build_b1b_package_construction_basis(
    *,
    authority: Mapping[str, Any],
    bundle: Mapping[str, Any],
    packages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the closed B1b-05 construction identity in its frozen order."""
    authority_keys = frozenset(
        {
            "correction_full_sha256",
            "owner_bound_main_sha",
            "promotion_receipt_id",
            "promoted_session_id",
            "result_review_hash",
            "package_review_preview_hash",
        }
    )
    bundle_keys = frozenset(
        {
            "member_count",
            "bundle_index_order_hash",
            "package_manifest_sha256",
            "package_rehash_sha256",
        }
    )
    package_keys = frozenset(
        {"package_kind", "output_package_id", "payload_bytes", "payload_sha256"}
    )
    if (
        not _has_exact_keys(authority, authority_keys)
        or not _has_exact_keys(bundle, bundle_keys)
        or not isinstance(packages, list)
        or len(packages) != 3
    ):
        raise PromotionIdentityError("B1b package construction basis is malformed")
    if (
        not _is_lower_hex64(authority["correction_full_sha256"])
        or not isinstance(authority["owner_bound_main_sha"], str)
        or len(authority["owner_bound_main_sha"]) != 40
        or any(character not in _HEX40 for character in authority["owner_bound_main_sha"])
        or not _is_uuid_string(authority["promotion_receipt_id"])
        or not _is_uuid_string(authority["promoted_session_id"])
        or not _is_lower_hex64(authority["result_review_hash"])
        or not _is_lower_hex64(authority["package_review_preview_hash"])
        or bundle["member_count"] != 9
        or type(bundle["member_count"]) is not int
        or any(
            not _is_lower_hex64(bundle[field])
            for field in (
                "bundle_index_order_hash",
                "package_manifest_sha256",
                "package_rehash_sha256",
            )
        )
    ):
        raise PromotionIdentityError("B1b package construction authority is malformed")
    for index, package in enumerate(packages):
        if (
            not _has_exact_keys(package, package_keys)
            or package["package_kind"] != _B1B_PACKAGE_ORDER[index]
            or not _is_uuid_string(package["output_package_id"])
            or type(package["payload_bytes"]) is not int
            or package["payload_bytes"] <= 0
            or not _is_lower_hex64(package["payload_sha256"])
        ):
            raise PromotionIdentityError("B1b package construction projection is malformed")
    return {
        "schema_id": "layer3.b1b_package_construction_basis.v1",
        "authority": dict(authority),
        "bundle": dict(bundle),
        "packages": json.loads(json.dumps(packages)),
    }


_B1B04_FORBIDDEN_NORMALIZED_KEYS = frozenset(
    {
        "authorization",
        "proxy_authorization",
        "cookie",
        "set_cookie",
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "credential",
        "credentials",
        "storage_ref",
        "raw_storage_ref",
        "input_payload_ref",
        "output_payload_ref",
        "payload_ref",
        "source_reference",
        "storage_path",
        "file_path",
        "local_path",
    }
)


def _normalize_b1b04_no_leak_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


_B1B_REQUEST_SENSITIVE_VALUES: ContextVar[frozenset[str]] = ContextVar(
    "b1b_request_sensitive_values",
    default=frozenset(),
)


@contextmanager
def b1b_request_sensitive_scope(headers: Mapping[str, str]):
    sensitive_names = {
        "authorization",
        "proxy_authorization",
        "cookie",
        "set_cookie",
        *(
            _normalize_b1b04_no_leak_key(value)
            for value in (
                settings.proxy_identity_header,
                settings.proxy_email_header,
                settings.proxy_groups_header,
            )
            if isinstance(value, str) and value
        ),
    }
    values = frozenset(
        value
        for key, value in headers.items()
        if isinstance(value, str)
        and value
        and _normalize_b1b04_no_leak_key(key) in sensitive_names
    )
    token = _B1B_REQUEST_SENSITIVE_VALUES.set(values)
    try:
        yield
    finally:
        _B1B_REQUEST_SENSITIVE_VALUES.reset(token)


def _b1b04_forbidden_normalized_keys() -> frozenset[str]:
    proxy_headers = {
        _normalize_b1b04_no_leak_key(value)
        for value in (
            settings.proxy_identity_header,
            settings.proxy_email_header,
            settings.proxy_groups_header,
            settings.proxy_roles_header,
        )
        if isinstance(value, str) and value
    }
    return _B1B04_FORBIDDEN_NORMALIZED_KEYS | proxy_headers


def _assert_b1b04_no_leak_string(value: str, *, forbidden_keys: frozenset[str]) -> None:
    decoded_values = [unicodedata.normalize("NFKC", value)]
    for _pass in range(2):
        decoded = unquote(decoded_values[-1])
        if decoded == decoded_values[-1]:
            break
        decoded_values.append(decoded)
    for decoded in decoded_values:
        folded = unicodedata.normalize("NFKC", decoded).casefold().strip()
        slash_value = folded.replace("\\", "/")
        if (
            re.match(r"^[a-z]:/", slash_value)
            or slash_value.startswith("/")
            or folded.startswith("file:")
            or any(segment in {".", ".."} for segment in slash_value.split("/"))
            or re.match(r"^(?:basic|bearer)\s+\S", folded)
            or re.match(r"^(?:cookie|set-cookie)\s*:", folded)
        ):
            raise PromotionIdentityError("closed B1b body contains a forbidden string")
        try:
            parsed = urlsplit(decoded)
        except ValueError as exc:
            raise PromotionIdentityError("closed B1b body contains a malformed URL") from exc
        if parsed.username is not None or parsed.password is not None:
            raise PromotionIdentityError("closed B1b body contains URL credentials")
        if any(
            _normalize_b1b04_no_leak_key(key) in forbidden_keys
            for key, _query_value in parse_qsl(parsed.query, keep_blank_values=True)
        ):
            raise PromotionIdentityError("closed B1b body contains a sensitive URL query")


def _assert_b1b04_closed_body_no_leak(value: object) -> None:
    """B1B-04 response/error guard; later package registries remain separately gated."""
    forbidden_keys = _b1b04_forbidden_normalized_keys()

    def visit(item: object) -> None:
        if item is None or isinstance(item, bool) or isinstance(item, int):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                raise PromotionIdentityError("closed B1b body contains a non-finite number")
            return
        if isinstance(item, str):
            _assert_b1b04_no_leak_string(item, forbidden_keys=forbidden_keys)
            return
        if isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise PromotionIdentityError("closed B1b body contains a non-string key")
                normalized_key = _normalize_b1b04_no_leak_key(key)
                if normalized_key in forbidden_keys:
                    raise PromotionIdentityError("closed B1b body contains a forbidden key")
                for suffix in ("_hash", "_sha256"):
                    if normalized_key.endswith(suffix):
                        raw_key = normalized_key[: -len(suffix)]
                        if raw_key in forbidden_keys and not _is_lower_hex64(child):
                            raise PromotionIdentityError("closed B1b body contains a malformed reference hash")
                visit(child)
            return
        if isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
            return
        raise PromotionIdentityError("closed B1b body contains a non-JSON value")

    visit(value)


def _b1b_sensitive_encodings(value: str) -> set[str]:
    raw = value.encode("utf-8")
    variants = {value, quote(value, safe="")}
    if len(raw) >= 8:
        for encoded in (base64.b64encode(raw), base64.urlsafe_b64encode(raw)):
            text_value = encoded.decode("ascii")
            variants.update({text_value, text_value.rstrip("=")})
    return {item for item in variants if item}


def _b1b_reference_canonical(value: str) -> str:
    decoded = unicodedata.normalize("NFKC", value)
    for _pass in range(2):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    parts: list[str] = []
    for part in decoded.replace("\\", "/").casefold().split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def _assert_b1b_package_no_leak(value: object, sensitive_values: set[str]) -> None:
    _assert_b1b04_closed_body_no_leak(value)
    encodings = {
        encoded
        for sensitive in sensitive_values
        if isinstance(sensitive, str) and sensitive
        for encoded in _b1b_sensitive_encodings(sensitive)
    }
    canonical = {
        _b1b_reference_canonical(encoded)
        for encoded in encodings
        if _b1b_reference_canonical(encoded)
    }
    raw_fixture = "site_id,value\nSB-001,42\nSB-002,43"
    crlf_fixture = raw_fixture.replace("\n", "\r\n")
    fixture_encodings: set[str] = set()
    for fixture_text in (
        raw_fixture,
        f"{raw_fixture}\n",
        crlf_fixture,
        f"{crlf_fixture}\r\n",
    ):
        fixture_encodings.update(_b1b_sensitive_encodings(fixture_text))

    def visit(item: object, *, allow_embedded: bool) -> None:
        if isinstance(item, str):
            normalized = unicodedata.normalize("NFKC", item)
            decoded = normalized
            for _pass in range(2):
                decoded = unquote(decoded)
            item_canonical = _b1b_reference_canonical(decoded)
            encoded_match = any(
                (encoded in normalized or encoded in decoded)
                if allow_embedded
                else (encoded == normalized or encoded == decoded)
                for encoded in encodings
            )
            canonical_match = any(
                value and (
                    value in item_canonical
                    if allow_embedded
                    else value == item_canonical
                )
                for value in canonical
            )
            if (
                encoded_match
                or any(encoded in normalized or encoded in decoded for encoded in fixture_encodings)
                or canonical_match
            ):
                raise PromotionIdentityError("closed B1b package contains a registered value")
            return
        if isinstance(item, Mapping):
            for key, child in item.items():
                visit(key, allow_embedded=False)
                visit(child, allow_embedded=True)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child, allow_embedded=True)

    visit(value, allow_embedded=True)


def _add_b1b_sensitive_strings(registry: set[str], value: object) -> None:
    if isinstance(value, str):
        if value and value != F07_SCIENCEBASE_ITEM_ID:
            registry.add(value)
        return
    if isinstance(value, Mapping):
        for child in value.values():
            _add_b1b_sensitive_strings(registry, child)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _add_b1b_sensitive_strings(registry, child)


def _is_b1b_reference_key(key: object) -> bool:
    normalized = _normalize_b1b04_no_leak_key(key)
    return normalized in {
        "reference",
        "references",
        "storage",
        "storage_ref",
        "raw_storage_ref",
        "payload_ref",
        "input_payload_ref",
        "output_payload_ref",
        "path",
        "url",
        "uri",
        "download_url",
        "download_uri",
        "sciencebase_item_url",
        "sciencebase_download_uri",
    } or normalized.endswith(("_ref", "_path", "_url", "_uri"))


def _add_b1b_nested_reference_strings(registry: set[str], value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_b1b_reference_key(key):
                _add_b1b_sensitive_strings(registry, child)
            else:
                _add_b1b_nested_reference_strings(registry, child)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _add_b1b_nested_reference_strings(registry, child)


def _b1b_runtime_sensitive_values() -> set[str]:
    values = settings.model_dump() if hasattr(settings, "model_dump") else settings.dict()
    registry: set[str] = set()
    for key, value in values.items():
        if not isinstance(value, str) or not value:
            continue
        normalized_key = _normalize_b1b04_no_leak_key(key)
        credential_setting = any(
            marker in normalized_key
            for marker in ("password", "secret", "api_key", "subscription_key", "credential")
        )
        if normalized_key == "database_url" or credential_setting or Path(value).is_absolute():
            registry.add(value)
    attestation_path = os.environ.get("PROJECT6_B1B_ATTESTATION_PATH", "")
    if attestation_path:
        registry.add(attestation_path)
    registry.update(_B1B_REQUEST_SENSITIVE_VALUES.get())
    return registry


def _b1b_package_sensitive_values(
    *,
    target: ConnectorRunTarget,
    intake: L3ConnectorSourceIntakeRecord,
    gate_snapshot: L3MaterialSnapshot,
    promoted_snapshot: L3MaterialSnapshot,
    version: DatasetVersion,
    provenance: DatasetSourceProvenance,
    pass_run: L3PassRun,
    artifact: AnalysisArtifact,
) -> set[str]:
    registry = _b1b_runtime_sensitive_values()
    for value in (
        target.raw_storage_ref,
        target.sciencebase_item_url,
        target.sciencebase_download_uri,
        intake.storage_ref,
        gate_snapshot.payload_ref,
        promoted_snapshot.payload_ref,
        version.storage_ref,
        provenance.raw_storage_ref,
        pass_run.input_payload_ref,
        pass_run.output_payload_ref,
        artifact.storage_ref,
    ):
        _add_b1b_sensitive_strings(registry, value)
    for value in (
        target.source_reference_json,
        intake.provenance_json,
        gate_snapshot.source_identity_json,
        gate_snapshot.source_provenance_json,
        promoted_snapshot.source_identity_json,
        promoted_snapshot.source_provenance_json,
        provenance.source_reference_json,
        provenance.retrieved_http_json,
    ):
        _add_b1b_nested_reference_strings(registry, value)
    return registry


def _valid_b1b_response_packages(value: object) -> bool:
    if not isinstance(value, list) or len(value) != 3:
        return False
    keys = frozenset({"package_kind", "output_package_id", "byte_length", "payload_sha256"})
    return all(
        _has_exact_keys(item, keys)
        and item["package_kind"] == _B1B_PACKAGE_ORDER[index]
        and _is_uuid_string(item["output_package_id"])
        and type(item["byte_length"]) is int
        and item["byte_length"] > 0
        and _is_lower_hex64(item["payload_sha256"])
        for index, item in enumerate(value)
    )


def _validate_b1b_closed_api_body(body: Mapping[str, Any], *, http_status: int) -> None:
    if not isinstance(body, dict) or type(http_status) is not int:
        raise PromotionIdentityError("closed B1b response is malformed")
    _validate_json_primitives(body)
    if body.get("schema_id") == "layer3.b1b_error.v1":
        if not _has_exact_keys(body, _B1B_ERROR_BODY_KEYS):
            raise PromotionIdentityError("closed B1b error keys are malformed")
        error_code = body.get("error_code")
        if not isinstance(error_code, str):
            raise PromotionIdentityError("closed B1b error code is malformed")
        expected_status, message, retryable = b1b_error_spec(error_code)
        if (
            http_status != expected_status
            or body.get("status") != "error"
            or body.get("message") != message
            or body.get("retryable") is not retryable
        ):
            raise PromotionIdentityError("closed B1b error mapping is malformed")
        return
    if http_status != 200:
        raise PromotionIdentityError("closed B1b success status is malformed")
    identity_fields = (
        "promotion_receipt_id",
        "promoted_session_id",
        "analysis_plan_id",
        "pass_run_id",
        "analysis_run_id",
    )
    if not all(_is_uuid_string(body.get(field)) for field in identity_fields):
        raise PromotionIdentityError("closed B1b response identity is malformed")
    schema_id = body.get("schema_id")
    if schema_id == "layer3.b1b_result_review_response.v1":
        if not _has_exact_keys(body, _B1B_RESULT_REVIEW_RESPONSE_KEYS):
            raise PromotionIdentityError("closed B1b result-review response is malformed")
        decision = body.get("operator_decision")
        notes_present = body.get("review_notes_present")
        notes_sha256 = body.get("review_notes_sha256")
        package_enabled = body.get("package_review_preview_enabled")
        valid_notes = (
            notes_present is False and notes_sha256 is None and package_enabled is True
            if decision == "approved"
            else notes_present is True
            and _is_lower_hex64(notes_sha256)
            and package_enabled is False
        )
        if (
            _RESULT_REVIEW_STATES.get(decision) != body.get("review_state")
            or not _is_lower_hex64(body.get("result_review_hash"))
            or type(notes_present) is not bool
            or type(package_enabled) is not bool
            or not valid_notes
        ):
            raise PromotionIdentityError("closed B1b result-review outcome is malformed")
        return
    if schema_id == "layer3.b1b_package_review_preview_response.v1":
        if (
            not _has_exact_keys(body, _B1B_PACKAGE_PREVIEW_RESPONSE_KEYS)
            or not _is_lower_hex64(body.get("result_review_hash"))
            or not _is_lower_hex64(body.get("package_review_preview_hash"))
            or body.get("candidate_package_kinds") != _B1B_PACKAGE_ORDER
            or body.get("member_count") != 9
            or type(body.get("member_count")) is not int
            or body.get("package_contract_schema_id") != "layer3.b1b_package_contract.v1"
            or not _is_lower_hex64(body.get("correction_full_sha256"))
        ):
            raise PromotionIdentityError("closed B1b package preview response is malformed")
        return
    if schema_id == "layer3.b1b_package_construction_commit_response.v1":
        if (
            not _has_exact_keys(body, _B1B_PACKAGE_COMMIT_RESPONSE_KEYS)
            or any(
                not _is_lower_hex64(body.get(field))
                for field in (
                    "result_review_hash",
                    "package_review_preview_hash",
                    "construction_basis_hash",
                )
            )
            or not _is_uuid_string(body.get("reconciliation_record_id"))
            or not _valid_b1b_response_packages(body.get("packages"))
            or body.get("package_count") != 3
            or type(body.get("package_count")) is not int
            or body.get("member_count") != 9
            or type(body.get("member_count")) is not int
            or body.get("persistence_status") != "committed"
        ):
            raise PromotionIdentityError("closed B1b package commit response is malformed")
        return
    if schema_id == "layer3.b1b_package_review_submit_response.v1":
        decision = body.get("operator_decision")
        approved = decision == "approved"
        expected_keys = (
            _B1B_PACKAGE_SUBMIT_APPROVED_RESPONSE_KEYS
            if approved
            else _B1B_PACKAGE_SUBMIT_RESPONSE_KEYS
        )
        notes_present = body.get("decision_notes_present")
        notes_sha256 = body.get("decision_notes_sha256")
        if (
            not _has_exact_keys(body, frozenset(expected_keys))
            or _PACKAGE_REVIEW_STATES.get(decision) != body.get("package_review_state")
            or any(
                not _is_lower_hex64(body.get(field))
                for field in (
                    "result_review_hash",
                    "package_review_preview_hash",
                    "construction_basis_hash",
                    "package_review_hash",
                )
            )
            or not _is_uuid_string(body.get("reconciliation_record_id"))
            or not _valid_b1b_response_packages(body.get("packages"))
            or type(notes_present) is not bool
            or (approved and (notes_present or notes_sha256 is not None))
            or (not approved and (not notes_present or not _is_lower_hex64(notes_sha256)))
            or body.get("handoff_eligibility_status")
            != ("eligible" if approved else "ineligible")
            or (approved and not _is_lower_hex64(body.get("connector_dataset_handoff_basis_hash")))
        ):
            raise PromotionIdentityError("closed B1b package submit response is malformed")
        return
    raise PromotionIdentityError("closed B1b response schema is malformed")


def _timestamp_matches(value: object, row_value: datetime | None) -> bool:
    if not isinstance(value, str) or not value or row_value is None:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    expected = row_value
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc) == expected.astimezone(timezone.utc)


def _approved_replay_plan(
    db: OrmSession,
    *,
    promoted: L3Session,
    approval: object,
) -> L3AnalysisPlan | None:
    if not _has_exact_keys(approval, _PLAN_APPROVAL_KEYS):
        return None
    assert isinstance(approval, dict)
    if (
        type(approval["approved_set_count"]) is not int
        or approval["approved_set_count"] != 1
        or type(approval["excluded_set_count"]) is not int
        or approval["excluded_set_count"] != 0
        or type(approval["planned_pass_count"]) is not int
        or approval["planned_pass_count"] != 1
        or approval["source_gate"] != "06_GATEC_PASS_FREEZE"
        or approval["approval_only"] is not True
        or approval["execution_started"] is not False
        or not _is_nonempty_string(approval["analysis_plan_id"])
        or not _is_nonempty_string(approval["source_preview_id"])
        or not _is_nonempty_string(approval["source_preview_hash"])
    ):
        return None
    plans = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == promoted.session_id).all()
    if len(plans) != 1 or plans[0].analysis_plan_id != approval["analysis_plan_id"]:
        return None
    plan = plans[0]
    plan_json = plan.plan_json
    if not isinstance(plan_json, dict):
        return None
    return plan if (
        plan.status == "approved"
        and plan.approved_by_operator is True
        and plan.approved_at is not None
        and isinstance(plan.analysis_set_ids_json, list)
        and len(plan.analysis_set_ids_json) == 1
        and plan_json.get("source_preview_id") == approval["source_preview_id"]
        and plan_json.get("source_preview_hash") == approval["source_preview_hash"]
        and plan_json.get("source_gate") == approval["source_gate"]
        and plan_json.get("approval_only") is True
        and plan_json.get("execution_started") is False
        and isinstance(plan_json.get("approved_sets_json"), list)
        and len(plan_json["approved_sets_json"]) == 1
        and plan_json.get("excluded_sets_json") == []
        and isinstance(plan_json.get("planned_passes_json"), list)
        and len(plan_json["planned_passes_json"]) == 1
    ) else None


def _staged_execution_matches(
    db: OrmSession,
    *,
    promoted: L3Session,
    receipt: L3ConnectorPromotionReceipt,
    plan: L3AnalysisPlan,
    selection: object,
    start: object | None,
) -> bool:
    terminal = start is not None
    selection_keys = _EXECUTION_SELECTION_KEYS | ({"pass_run_statuses_json"} if terminal else set())
    if not _has_exact_keys(selection, frozenset(selection_keys)):
        return False
    assert isinstance(selection, dict)
    pass_run_ids = selection["pass_run_ids_json"]
    if (
        selection["schema_id"] != "layer3.execution_selection_state.v1"
        or not _is_nonempty_string(selection["client_request_id"])
        or selection["analysis_plan_id"] != plan.analysis_plan_id
        or selection["source_preview_id"] != plan.plan_json.get("source_preview_id")
        or selection["source_preview_hash"] != plan.plan_json.get("source_preview_hash")
        or not isinstance(pass_run_ids, list)
        or len(pass_run_ids) != 1
        or not _is_nonempty_string(pass_run_ids[0])
        or type(selection["pass_run_count"]) is not int
        or selection["pass_run_count"] != 1
        or selection["downstream_unavailable"] != _REPLAY_DOWNSTREAM_UNAVAILABLE
        or type(selection["operator_reason_recorded"]) is not bool
        or not _is_nonempty_string(selection["selected_at"])
    ):
        return False
    pass_runs = db.query(L3PassRun).filter(L3PassRun.session_id == promoted.session_id).all()
    if len(pass_runs) != 1 or pass_runs[0].pass_run_id != pass_run_ids[0]:
        return False
    pass_run = pass_runs[0]
    pass_summary = pass_run.summary_json
    if (
        pass_run.analysis_plan_id != plan.analysis_plan_id
        or not isinstance(pass_summary, dict)
        or pass_summary.get("client_request_id") != selection["client_request_id"]
        or pass_summary.get("analysis_plan_id") != selection["analysis_plan_id"]
        or pass_summary.get("source_preview_id") != selection["source_preview_id"]
        or pass_summary.get("source_preview_hash") != selection["source_preview_hash"]
        or pass_summary.get("downstream_unavailable") != selection["downstream_unavailable"]
        or pass_summary.get("selected_at") != selection["selected_at"]
        or pass_summary.get("selection_state") != "execution_selected_not_started"
    ):
        return False
    if not terminal:
        return (
            selection["state"] == "execution_selected_not_started"
            and selection["execution_started"] is False
            and selection["analysis_run_ids_json"] == []
            and pass_run.status == "selected_not_started"
            and pass_run.started_at is None
            and pass_run.completed_at is None
            and pass_run.output_payload_ref is None
            and pass_summary.get("execution_started") is False
            and pass_summary.get("analysis_run_id") is None
        )
    if not _has_exact_keys(start, _ANALYSIS_EXECUTION_START_KEYS):
        return False
    assert isinstance(start, dict)
    pass_start = pass_summary.get("analysis_execution_start")
    if (
        start["schema_id"] != "layer3.analysis_execution_start_state.v1"
        or not _is_nonempty_string(start["client_request_id"])
        or start["analysis_plan_id"] != plan.analysis_plan_id
        or start["pass_run_id"] != pass_run.pass_run_id
        or start["source_preview_id"] != selection["source_preview_id"]
        or start["source_preview_hash"] != selection["source_preview_hash"]
        or start["downstream_unavailable"] != _REPLAY_DOWNSTREAM_UNAVAILABLE
        or type(start["operator_reason_recorded"]) is not bool
        or selection["execution_started"] is not True
        or not isinstance(pass_start, dict)
        or pass_start.get("client_request_id") != start["client_request_id"]
        or pass_start.get("state") != start["state"]
        or not _timestamp_matches(start["started_at"], pass_run.started_at)
        or not _timestamp_matches(start["completed_at"], pass_run.completed_at)
        or not _timestamp_matches(pass_start.get("started_at"), pass_run.started_at)
        or not _timestamp_matches(pass_start.get("completed_at"), pass_run.completed_at)
    ):
        return False
    if start["state"] == "execution_pass_completed":
        analysis_run_id = start["analysis_run_id"]
        analysis_run = db.get(AnalysisRun, analysis_run_id) if _is_nonempty_string(analysis_run_id) else None
        return (
            selection["state"] == "execution_pass_completed"
            and selection["analysis_run_ids_json"] == [analysis_run_id]
            and selection["pass_run_statuses_json"] == {pass_run.pass_run_id: "completed_with_warnings"}
            and pass_run.status == "completed_with_warnings"
            and pass_summary.get("execution_started") is True
            and pass_summary.get("analysis_run_id") == analysis_run_id
            and analysis_run is not None
            and analysis_run.status == "completed"
            and analysis_run.dataset_version_id == receipt.dataset_version_id
            and start["pass_run_status"] == "completed_with_warnings"
            and _is_nonempty_string(start["output_payload_ref"])
            and start["output_payload_ref"] == pass_run.output_payload_ref
        )
    return (
        start["state"] == "execution_pass_failed"
        and selection["state"] == "execution_pass_failed"
        and selection["analysis_run_ids_json"] == []
        and selection["pass_run_statuses_json"] == {pass_run.pass_run_id: "failed"}
        and pass_run.status == "failed"
        and pass_summary.get("execution_started") is True
        and pass_summary.get("analysis_run_id") is None
        and start["analysis_run_id"] is None
        and start["pass_run_status"] == "failed"
        and start["output_payload_ref"] is None
        and pass_run.output_payload_ref is None
    )


def _staged_replay_summary_matches(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    summary: dict[str, Any],
) -> bool:
    base_keys = frozenset(_MATERIALIZED_REPLAY_BASE)
    descriptor_counts = summary.get("descriptor_status_counts")
    retrieval_counts = summary.get("retrieval_outcome_counts")
    source_planes = summary.get("source_planes")
    warning_reasons = summary.get("warning_reasons")
    base_types_are_exact = (
        type(descriptor_counts) is dict
        and type(descriptor_counts.get("resolved_loaded")) is int
        and type(retrieval_counts) is dict
        and type(retrieval_counts.get("loaded")) is int
        and type(summary.get("loaded_snapshot_count")) is int
        and type(summary.get("retrieved_descriptor_count")) is int
        and type(summary.get("unresolved_descriptor_count")) is int
        and type(source_planes) is list
        and all(type(value) is str for value in source_planes)
        and type(warning_reasons) is list
        and all(type(value) is str for value in warning_reasons)
        and type(summary.get("descriptor_coverage_status")) is str
    )
    progressions = (
        base_keys,
        base_keys | {"plan_approval"},
        base_keys | {"plan_approval", "execution_selection"},
        base_keys | {"plan_approval", "execution_selection", "analysis_execution_start"},
    )
    if frozenset(summary) not in progressions or not base_types_are_exact or any(
        summary.get(key) != value for key, value in _MATERIALIZED_REPLAY_BASE.items()
    ):
        return False
    if set(summary) == base_keys:
        return (
            db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == promoted.session_id).count() == 0
            and db.query(L3PassRun).filter(L3PassRun.session_id == promoted.session_id).count() == 0
        )
    plan = _approved_replay_plan(db, promoted=promoted, approval=summary["plan_approval"])
    if plan is None:
        return False
    if "execution_selection" not in summary:
        return db.query(L3PassRun).filter(L3PassRun.session_id == promoted.session_id).count() == 0
    return _staged_execution_matches(
        db,
        promoted=promoted,
        receipt=receipt,
        plan=plan,
        selection=summary["execution_selection"],
        start=summary.get("analysis_execution_start"),
    )


def _closed_result_review_matches(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    summary: dict[str, Any],
) -> str | None:
    plan_id = summary["analysis_plan_id"]
    pass_run_id = summary["pass_run_id"]
    analysis_run_id = summary["analysis_run_id"]
    if not all(_is_nonempty_string(value) for value in (plan_id, pass_run_id, analysis_run_id)):
        return None
    plans = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == promoted.session_id).all()
    pass_runs = db.query(L3PassRun).filter(L3PassRun.session_id == promoted.session_id).all()
    if (
        len(plans) != 1
        or plans[0].analysis_plan_id != plan_id
        or len(pass_runs) != 1
        or pass_runs[0].pass_run_id != pass_run_id
    ):
        return None
    plan = plans[0]
    pass_run = pass_runs[0]
    analysis_run = db.get(AnalysisRun, analysis_run_id)
    pass_summary = pass_run.summary_json
    if (
        plan.status != "approved"
        or plan.approved_by_operator is not True
        or pass_run.analysis_plan_id != plan.analysis_plan_id
        or pass_run.status != "completed_with_warnings"
        or not _is_nonempty_string(pass_run.output_payload_ref)
        or not isinstance(pass_summary, dict)
        or pass_summary.get("analysis_run_id") != analysis_run_id
        or analysis_run is None
        or analysis_run.status != "completed"
        or analysis_run.dataset_version_id != receipt.dataset_version_id
    ):
        return None
    review = pass_summary.get("execution_result_review")
    review_keys = _RESULT_REVIEW_RECORD_KEYS | {
        "review_record_ref",
        "review_state",
        "result_review_hash",
    }
    if not _has_exact_keys(review, frozenset(review_keys)):
        return None
    assert isinstance(review, dict)
    record = {key: review[key] for key in _RESULT_REVIEW_RECORD_KEYS}
    decision = record["operator_decision"]
    expected_state = _RESULT_REVIEW_STATES.get(decision)
    result_hash = review["result_review_hash"]
    expected_ref = f"b1b-result-review-{result_hash}"
    plan_json = plan.plan_json
    check_ids = record["assumption_check_ids"]
    reviewed_items = record["reviewed_output_items"]
    if (
        record["schema_id"] != "layer3.b1b_result_review_record.v1"
        or record["promotion_receipt_id"] != receipt.connector_promotion_receipt_id
        or record["promoted_session_id"] != promoted.session_id
        or record["analysis_plan_id"] != plan.analysis_plan_id
        or record["pass_run_id"] != pass_run.pass_run_id
        or not isinstance(plan_json, dict)
        or record["preview_id"] != plan_json.get("source_preview_id")
        or record["preview_hash"] != plan_json.get("source_preview_hash")
        or record["preview_id"] != pass_summary.get("source_preview_id")
        or record["preview_hash"] != pass_summary.get("source_preview_hash")
        or record["analysis_run_id"] != analysis_run.analysis_run_id
        or not _is_lower_hex64(record["result_payload_sha256"])
        or not _is_lower_hex64(record["analysis_artifact_sha256"])
        or not _is_lower_hex64(record["result_review_request_basis_hash"])
        or not isinstance(check_ids, list)
        or len(check_ids) != 4
        or len(set(check_ids)) != 4
        or not all(_is_nonempty_string(value) for value in check_ids)
        or type(record["unresolved_trace_count"]) is not int
        or record["unresolved_trace_count"] != 0
        or expected_state is None
        or not _is_lower_hex64(result_hash)
        or d33_sha256(record) != result_hash
        or review["review_record_ref"] != expected_ref
        or review["review_state"] != expected_state
        or summary["review_record_ref"] != expected_ref
        or summary["review_state"] != expected_state
        or summary["result_review_hash"] != result_hash
    ):
        return None
    notes = record["review_notes"]
    if decision == "approved":
        if notes is not None:
            return None
    elif not isinstance(notes, str) or not notes or notes != notes.strip():
        return None
    try:
        authoritative_evidence = _b1b_result_artifact_evidence(
            db,
            receipt=receipt,
            analysis_run=analysis_run,
        )
    except ConnectorPromotionError:
        return None
    evidence_keys = (
        "result_payload_sha256",
        "analysis_artifact_id",
        "analysis_artifact_sha256",
        "assumption_check_ids",
        "caveat_note_id",
        "reviewed_output_items",
    )
    return decision if all(record[key] == authoritative_evidence[key] for key in evidence_keys) else None


def _handoff_basis_matches(
    basis: object,
    *,
    basis_hash: object,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    result_review_hash: str,
    package_review_hash: str,
    reconciliation: L3ReconciliationRecord,
    packages: list[dict[str, Any]],
    package_set: dict[str, Any],
) -> bool:
    if not _has_exact_keys(
        basis,
        frozenset(
            {
                "approved_reviews",
                "canonical_internal",
                "package_set",
                "promoted_session_id",
                "promotion_receipt_id",
                "schema_id",
            }
        ),
    ):
        return False
    assert isinstance(basis, dict)
    approved_reviews = basis["approved_reviews"]
    canonical = basis["canonical_internal"]
    basis_package_set = basis["package_set"]
    if (
        not _has_exact_keys(approved_reviews, frozenset({"package_review_hash", "result_review_hash"}))
        or not _has_exact_keys(canonical, frozenset({"byte_length", "output_package_id", "payload_hash"}))
        or not _has_exact_keys(
            basis_package_set,
            frozenset(
                {
                    "reconciliation_record_id",
                    "review_facing_output_package_id",
                    "review_facing_payload_hash",
                    "user_facing_output_package_id",
                    "user_facing_payload_hash",
                }
            ),
        )
    ):
        return False
    assert isinstance(approved_reviews, dict)
    assert isinstance(canonical, dict)
    assert isinstance(basis_package_set, dict)
    return (
        basis["schema_id"] == "layer3.connector_dataset_handoff_basis.v1"
        and basis["promotion_receipt_id"] == receipt.connector_promotion_receipt_id
        and basis["promoted_session_id"] == promoted.session_id
        and approved_reviews
        == {
            "package_review_hash": package_review_hash,
            "result_review_hash": result_review_hash,
        }
        and type(canonical["byte_length"]) is int
        and canonical["byte_length"] > 0
        and canonical["byte_length"] == package_set["packages"][0]["payload_bytes"]
        and canonical["output_package_id"] == packages[0]["output_package_id"]
        and canonical["payload_hash"] == packages[0]["payload_sha256"]
        and basis_package_set
        == {
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "review_facing_output_package_id": packages[2]["output_package_id"],
            "review_facing_payload_hash": packages[2]["payload_sha256"],
            "user_facing_output_package_id": packages[1]["output_package_id"],
            "user_facing_payload_hash": packages[1]["payload_sha256"],
        }
        and _is_lower_hex64(basis_hash)
        and d33_sha256(basis) == basis_hash
    )


def _closed_package_review_matches(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    summary: dict[str, Any],
    result_decision: str,
) -> bool:
    if result_decision != "approved":
        return False
    if (
        not _is_nonempty_string(summary["package_review_state"])
        or not _is_lower_hex64(summary["package_review_hash"])
        or not _is_nonempty_string(summary["reconciliation_record_id"])
        or not isinstance(summary["packages"], list)
    ):
        return False
    reconciliation = db.get(L3ReconciliationRecord, summary["reconciliation_record_id"])
    if reconciliation is None or reconciliation.session_id != promoted.session_id:
        return False
    reconciliation_rows = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == promoted.session_id)
        .all()
    )
    rows = db.query(L3OutputPackage).filter(L3OutputPackage.session_id == promoted.session_id).all()
    if len(reconciliation_rows) != 1 or len(rows) != 3:
        return False
    rows_by_kind = {row.package_kind: row for row in rows}
    if set(rows_by_kind) != set(_B1B_PACKAGE_ORDER) or any(
        row.reconciliation_record_id != reconciliation.reconciliation_record_id
        or row.status != "package_complete"
        or not _is_lower_hex64(row.payload_hash)
        for row in rows
    ):
        return False
    packages = [
        {
            "package_kind": kind,
            "output_package_id": rows_by_kind[kind].output_package_id,
            "payload_sha256": rows_by_kind[kind].payload_hash,
        }
        for kind in _B1B_PACKAGE_ORDER
    ]
    if summary["packages"] != packages:
        return False
    reconciliation_summary = reconciliation.summary_json
    if not _has_exact_keys(reconciliation_summary, _B1B_RECONCILIATION_SUMMARY_KEYS):
        return False
    assert isinstance(reconciliation_summary, dict)
    package_set = reconciliation_summary["package_set"]
    if not _has_exact_keys(package_set, _B1B_PACKAGE_SET_KEYS):
        return False
    assert isinstance(package_set, dict)
    package_set_rows = package_set["packages"]
    if (
        type(package_set["member_count"]) is not int
        or package_set["member_count"] != 9
        or not all(
            _is_lower_hex64(package_set[key])
            for key in (
                "construction_basis_hash",
                "bundle_index_order_hash",
                "package_manifest_sha256",
                "package_rehash_sha256",
            )
        )
        or not isinstance(package_set_rows, list)
        or len(package_set_rows) != 3
    ):
        return False
    for index, (stored, projected) in enumerate(zip(package_set_rows, packages, strict=True)):
        if (
            not _has_exact_keys(
                stored,
                frozenset({"package_kind", "output_package_id", "payload_bytes", "payload_sha256"}),
            )
            or {key: stored[key] for key in projected} != projected
            or type(stored["payload_bytes"]) is not int
            or stored["payload_bytes"] <= 0
            or stored["package_kind"] != _B1B_PACKAGE_ORDER[index]
        ):
            return False
    record = reconciliation_summary["package_review_submit"]
    if not _has_exact_keys(record, _PACKAGE_REVIEW_RECORD_KEYS):
        return False
    assert isinstance(record, dict)
    decision = record["operator_decision"]
    expected_state = _PACKAGE_REVIEW_STATES.get(decision)
    package_review_hash = reconciliation_summary["package_review_hash"]
    if (
        reconciliation_summary["schema_id"] != "layer3.b1b_reconciliation_summary.v1"
        or reconciliation_summary["profile"] != "receipt_bound_b1b"
        or reconciliation_summary["source_gate"] != "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE"
        or reconciliation_summary["promotion_receipt_id"] != receipt.connector_promotion_receipt_id
        or reconciliation_summary["promoted_session_id"] != promoted.session_id
        or reconciliation_summary["result_review_hash"] != summary["result_review_hash"]
        or reconciliation_summary["package_review_preview_hash"]
        != record["package_review_preview_hash"]
        or record["schema_id"] != "layer3.b1b_package_review_record.v1"
        or not _is_lower_hex64(record["review_request_basis_hash"])
        or not _is_lower_hex64(record["package_review_preview_hash"])
        or record["construction_basis_hash"] != package_set["construction_basis_hash"]
        or record["reconciliation_record_id"] != reconciliation.reconciliation_record_id
        or record["output_package_ids"] != [item["output_package_id"] for item in packages]
        or record["package_kinds"] != _B1B_PACKAGE_ORDER
        or record["payload_hashes"] != [item["payload_sha256"] for item in packages]
        or expected_state is None
        or summary["package_review_state"] != expected_state
        or summary["package_review_hash"] != package_review_hash
        or not _is_lower_hex64(package_review_hash)
        or d33_sha256(record) != package_review_hash
    ):
        return False
    notes = record["decision_notes"]
    if decision == "approved":
        if notes is not None:
            return False
        return _handoff_basis_matches(
            reconciliation_summary["connector_dataset_handoff_basis"],
            basis_hash=reconciliation_summary["connector_dataset_handoff_basis_hash"],
            receipt=receipt,
            promoted=promoted,
            result_review_hash=summary["result_review_hash"],
            package_review_hash=package_review_hash,
            reconciliation=reconciliation,
            packages=packages,
            package_set=package_set,
        ) and summary["connector_dataset_handoff_basis_hash"] == reconciliation_summary[
            "connector_dataset_handoff_basis_hash"
        ]
    return (
        isinstance(notes, str)
        and bool(notes)
        and notes == notes.strip()
        and summary["connector_dataset_handoff_basis_hash"] is None
        and reconciliation_summary["connector_dataset_handoff_basis"] is None
        and reconciliation_summary["connector_dataset_handoff_basis_hash"] is None
    )


def _materialized_replay_summary_is_valid(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
) -> bool:
    summary = promoted.summary_json
    if not isinstance(summary, dict):
        return False
    if "schema_id" not in summary:
        return _staged_replay_summary_matches(
            db,
            receipt=receipt,
            promoted=promoted,
            summary=summary,
        )
    if (
        summary.get("schema_id") != "layer3.b1b_session_state.v1"
        or not _has_exact_keys(summary, _B1B_SESSION_STATE_KEYS)
    ):
        return False
    try:
        result_decision = _closed_result_review_matches(
            db,
            receipt=receipt,
            promoted=promoted,
            summary=summary,
        )
        if result_decision is None:
            return False
        package_fields = (
            "package_review_state",
            "package_review_hash",
            "reconciliation_record_id",
            "packages",
            "connector_dataset_handoff_basis_hash",
        )
        if all(summary[field] is None for field in package_fields):
            return True
        return _closed_package_review_matches(
            db,
            receipt=receipt,
            promoted=promoted,
            summary=summary,
            result_decision=result_decision,
        )
    except (PromotionIdentityError, TypeError, ValueError):
        return False


def _b1b_result_review_request(
    payload: dict[str, Any],
) -> tuple[dict[str, str], str, str, str | None]:
    if not _has_exact_keys(payload, _B1B_RESULT_REVIEW_REQUEST_KEYS):
        raise _closed_b1b_error("b1b_request_validation_failed")
    if not all(isinstance(payload[key], str) for key in _B1B_RESULT_REVIEW_REQUEST_KEYS):
        raise _closed_b1b_error("b1b_request_validation_failed")
    for field in ("session_id", "analysis_plan_id", "pass_run_id", "analysis_run_id"):
        value = payload[field]
        if value != value.strip() or not _is_uuid_string(value):
            raise _closed_b1b_error("b1b_request_validation_failed")
    preview_id = payload["preview_id"]
    if not preview_id or preview_id != preview_id.strip():
        raise _closed_b1b_error("b1b_request_validation_failed")
    if not _is_lower_hex64(payload["preview_hash"]):
        raise _closed_b1b_error("b1b_request_validation_failed")
    decision = payload["operator_decision"]
    if decision not in _RESULT_REVIEW_STATES:
        raise _closed_b1b_error("b1b_request_validation_failed")
    raw_notes = payload["review_notes"]
    if decision == "approved":
        if raw_notes != "":
            raise _closed_b1b_error("b1b_request_validation_failed")
        normalized_notes = None
    else:
        normalized_notes = raw_notes.strip()
        if not normalized_notes:
            raise _closed_b1b_error("b1b_request_validation_failed")
    request_basis = {
        "session_id": payload["session_id"],
        "analysis_plan_id": payload["analysis_plan_id"],
        "pass_run_id": payload["pass_run_id"],
        "preview_id": payload["preview_id"],
        "preview_hash": payload["preview_hash"],
        "analysis_run_id": payload["analysis_run_id"],
        "operator_decision": decision,
        "review_notes": raw_notes,
    }
    return request_basis, d33_sha256(request_basis), decision, normalized_notes


def _b1b_expected_result_payload(
    *,
    dataset_id: str,
    dataset_version_id: str,
) -> dict[str, Any]:
    site_summary = {
        key: value for key, value in _B1B_BOUNDED_RESULT["columns"][0].items() if key != "name"
    }
    value_summary = {
        key: value for key, value in _B1B_BOUNDED_RESULT["columns"][1].items() if key != "name"
    }
    value_summary["top_values"] = [{"value": 42.0, "count": 1}, {"value": 43.0, "count": 1}]
    return {
        "dataset_version_id": dataset_version_id,
        "dataset_id": dataset_id,
        "method_id": "descriptive_summary",
        "columns": {"site_id": site_summary, "value": value_summary},
        "summary_stats": {
            "row_count": 2,
            "column_count": 2,
            "numeric_column_count": 1,
            "categorical_column_count": 1,
            "boolean_column_count": 0,
            "time_column_count": 0,
            "missing_cell_count": 0,
            "missing_fraction": 0.0,
        },
    }


def _b1b_result_artifact_evidence(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    analysis_run: AnalysisRun,
) -> dict[str, Any]:
    artifacts = (
        db.query(AnalysisArtifact)
        .filter(AnalysisArtifact.analysis_run_id == analysis_run.analysis_run_id)
        .with_for_update()
        .all()
    )
    checks = (
        db.query(AssumptionCheck)
        .filter(AssumptionCheck.analysis_run_id == analysis_run.analysis_run_id)
        .with_for_update()
        .all()
    )
    caveats = (
        db.query(CaveatNote)
        .filter(CaveatNote.analysis_run_id == analysis_run.analysis_run_id)
        .with_for_update()
        .all()
    )
    if len(artifacts) != 1 or len(checks) != 4 or len(caveats) != 1:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    artifact = artifacts[0]
    caveat = caveats[0]
    if (
        artifact.artifact_type != "descriptive_summary_result"
        or artifact.title != "Descriptive summary results"
        or artifact.summary != "Descriptive summary for 2 rows and 2 columns."
        or not _is_uuid_string(artifact.artifact_id)
        or not _is_uuid_string(caveat.caveat_note_id)
        or (caveat.caveat_type, caveat.severity, caveat.message) != _B1B_CAVEAT_CONTRACT
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    storage_ref = artifact.storage_ref
    artifact_name = Path(storage_ref).name if isinstance(storage_ref, str) else ""
    if not artifact_name or storage_ref != f"/storage/artifacts/{artifact_name}":
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    try:
        artifact_path, _relative_ref = _resolve_regular_reference(
            artifact_name,
            settings.artifact_storage_dir,
        )
        artifact_bytes = artifact_path.read_bytes()
        result_payload = json.loads(artifact_bytes.decode("utf-8"))
        expected_payload = _b1b_expected_result_payload(
            dataset_id=str(receipt.dataset_id),
            dataset_version_id=str(receipt.dataset_version_id),
        )
        normalized_payload = json.loads(json.dumps(result_payload))
        standard_deviation = normalized_payload["columns"]["value"]["numeric_summary"]["std_dev"]
        if type(standard_deviation) is not float or not math.isclose(
            standard_deviation,
            0.7071067811865476,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise PromotionIdentityError("result standard deviation is outside the frozen tolerance")
        normalized_payload["columns"]["value"]["numeric_summary"]["std_dev"] = 0.7071067811865476
        if d33_canonical_bytes(normalized_payload) != d33_canonical_bytes(expected_payload):
            raise PromotionIdentityError("result payload differs from the frozen projection")
        if d33_canonical_bytes(artifact.metadata_json) != d33_canonical_bytes(expected_payload["summary_stats"]):
            raise PromotionIdentityError("artifact metadata differs from the frozen projection")
        result_payload_sha256 = d33_sha256(result_payload)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, PromotionIdentityError) as exc:
        raise _closed_b1b_error("connector_materialization_basis_conflict") from exc
    check_by_name = {row.assumption_name: row for row in checks}
    if len(check_by_name) != 4:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    ordered_check_ids: list[str] = []
    for name, method, result, severity, notes in _B1B_ASSUMPTION_CHECK_CONTRACT:
        row = check_by_name.get(name)
        if (
            row is None
            or not _is_uuid_string(row.assumption_check_id)
            or (row.check_method, row.check_result, row.severity, row.notes)
            != (method, result, severity, notes)
        ):
            raise _closed_b1b_error("connector_materialization_basis_conflict")
        ordered_check_ids.append(row.assumption_check_id)
    reviewed_items = [
        {
            "index": 0,
            "item_ref": f"analysis-artifact:{artifact.artifact_id}",
            "item_type": "fact",
            "trace_status": "resolved",
            "missing_trace_fields": [],
        },
        {
            "index": 1,
            "item_ref": f"caveat:{caveat.caveat_note_id}",
            "item_type": "caveat",
            "trace_status": "resolved",
            "missing_trace_fields": [],
        },
    ]
    return {
        "result_payload_sha256": result_payload_sha256,
        "analysis_artifact_id": artifact.artifact_id,
        "analysis_artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "assumption_check_ids": ordered_check_ids,
        "caveat_note_id": caveat.caveat_note_id,
        "reviewed_output_items": reviewed_items,
    }


def _locked_b1b_result_review_authority(
    db: OrmSession,
    *,
    request_basis: dict[str, str],
) -> tuple[L3ConnectorPromotionReceipt, L3Session, L3PassRun, dict[str, Any]]:
    receipts = (
        db.query(L3ConnectorPromotionReceipt)
        .filter(L3ConnectorPromotionReceipt.promoted_session_id == request_basis["session_id"])
        .with_for_update()
        .all()
    )
    if len(receipts) != 1:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    receipt = receipts[0]
    promoted = (
        db.query(L3Session)
        .filter(L3Session.session_id == request_basis["session_id"])
        .with_for_update()
        .first()
    )
    plans = (
        db.query(L3AnalysisPlan)
        .filter(L3AnalysisPlan.session_id == request_basis["session_id"])
        .with_for_update()
        .all()
    )
    pass_runs = (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == request_basis["session_id"])
        .with_for_update()
        .all()
    )
    if promoted is None or len(plans) != 1 or len(pass_runs) != 1:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    plan = plans[0]
    pass_run = pass_runs[0]
    pass_summary = pass_run.summary_json
    plan_json = plan.plan_json
    analysis_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.analysis_run_id == request_basis["analysis_run_id"])
        .with_for_update()
        .first()
    )
    if (
        receipt.canonical_identity_key_hash != F07_CANONICAL_IDENTITY_KEY_HASH
        or receipt.source_family != F07_SOURCE_FAMILY
        or receipt.content_sha256 != F07_CONTENT_SHA256
        or receipt.materialization_status != "materialized"
        or not receipt.dataset_id
        or not receipt.dataset_version_id
        or receipt.promoted_session_id != promoted.session_id
        or not _materialized_replay_summary_is_valid(db, receipt=receipt, promoted=promoted)
        or plan.analysis_plan_id != request_basis["analysis_plan_id"]
        or plan.status != "approved"
        or plan.approved_by_operator is not True
        or not isinstance(plan_json, dict)
        or plan_json.get("source_preview_id") != request_basis["preview_id"]
        or plan_json.get("source_preview_hash") != request_basis["preview_hash"]
        or pass_run.pass_run_id != request_basis["pass_run_id"]
        or pass_run.analysis_plan_id != plan.analysis_plan_id
        or pass_run.status != "completed_with_warnings"
        or not isinstance(pass_summary, dict)
        or pass_summary.get("source_preview_id") != request_basis["preview_id"]
        or pass_summary.get("source_preview_hash") != request_basis["preview_hash"]
        or pass_summary.get("analysis_run_id") != request_basis["analysis_run_id"]
        or analysis_run is None
        or analysis_run.status != "completed"
        or analysis_run.dataset_version_id != receipt.dataset_version_id
        or analysis_run.method_name != "descriptive_summary"
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    evidence = _b1b_result_artifact_evidence(db, receipt=receipt, analysis_run=analysis_run)
    evidence.update(
        {
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "promoted_session_id": promoted.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "analysis_run_id": analysis_run.analysis_run_id,
        }
    )
    return receipt, promoted, pass_run, evidence


def _b1b_result_review_response(
    *,
    record: dict[str, Any],
    result_review_hash: str,
) -> B1BClosedApiResponse:
    decision = record["operator_decision"]
    notes = record["review_notes"]
    body = {
        "schema_id": "layer3.b1b_result_review_response.v1",
        "promotion_receipt_id": record["promotion_receipt_id"],
        "promoted_session_id": record["promoted_session_id"],
        "analysis_plan_id": record["analysis_plan_id"],
        "pass_run_id": record["pass_run_id"],
        "analysis_run_id": record["analysis_run_id"],
        "operator_decision": decision,
        "review_state": _RESULT_REVIEW_STATES[decision],
        "result_review_hash": result_review_hash,
        "review_notes_present": notes is not None,
        "review_notes_sha256": (
            hashlib.sha256(notes.encode("utf-8")).hexdigest() if notes is not None else None
        ),
        "package_review_preview_enabled": decision == "approved",
    }
    return B1BClosedApiResponse(body, http_status=200)


def record_b1b_result_review(
    db: OrmSession,
    payload: dict[str, Any],
) -> B1BClosedApiResponse:
    request_basis, request_basis_hash, decision, normalized_notes = _b1b_result_review_request(payload)
    if not bridge_precondition_available():
        raise _closed_b1b_error("connector_promotion_bridge_unavailable")
    try:
        acquire_promotion_identity_lock(db, F07_CANONICAL_IDENTITY_KEY_HASH)
        receipt, promoted, pass_run, connector_b1_evidence = _locked_b1b_result_review_authority(
            db,
            request_basis=request_basis,
        )
        existing = (pass_run.summary_json or {}).get("execution_result_review")
        expected_client_request_id = f"b1b-result-review-{request_basis_hash}"
        if existing is not None:
            if (
                isinstance(existing, dict)
                and existing.get("result_review_request_basis_hash") == request_basis_hash
            ):
                if payload["client_request_id"] != expected_client_request_id:
                    raise _closed_b1b_error("b1b_request_validation_failed")
                record = {key: existing[key] for key in _RESULT_REVIEW_RECORD_KEYS}
                response = _b1b_result_review_response(
                    record=record,
                    result_review_hash=existing["result_review_hash"],
                )
                db.rollback()
                db.info.pop("b1b_promotion_identity_lock", None)
                return response
            raise _closed_b1b_error("connector_result_review_decision_conflict")
        if payload["client_request_id"] != expected_client_request_id:
            raise _closed_b1b_error("b1b_request_validation_failed")
        record = {
            "schema_id": "layer3.b1b_result_review_record.v1",
            "promotion_receipt_id": connector_b1_evidence["promotion_receipt_id"],
            "promoted_session_id": connector_b1_evidence["promoted_session_id"],
            "analysis_plan_id": connector_b1_evidence["analysis_plan_id"],
            "pass_run_id": connector_b1_evidence["pass_run_id"],
            "preview_id": request_basis["preview_id"],
            "preview_hash": request_basis["preview_hash"],
            "analysis_run_id": connector_b1_evidence["analysis_run_id"],
            "result_payload_sha256": connector_b1_evidence["result_payload_sha256"],
            "analysis_artifact_id": connector_b1_evidence["analysis_artifact_id"],
            "analysis_artifact_sha256": connector_b1_evidence["analysis_artifact_sha256"],
            "assumption_check_ids": connector_b1_evidence["assumption_check_ids"],
            "caveat_note_id": connector_b1_evidence["caveat_note_id"],
            "reviewed_output_items": connector_b1_evidence["reviewed_output_items"],
            "unresolved_trace_count": 0,
            "operator_decision": decision,
            "review_notes": normalized_notes,
            "result_review_request_basis_hash": request_basis_hash,
        }
        result_review_hash = d33_sha256(record)
        review_record_ref = f"b1b-result-review-{result_review_hash}"
        review_state = _RESULT_REVIEW_STATES[decision]
        pass_run.summary_json = {
            **json.loads(json.dumps(pass_run.summary_json)),
            "execution_result_review": {
                **record,
                "review_record_ref": review_record_ref,
                "review_state": review_state,
                "result_review_hash": result_review_hash,
            },
        }
        promoted.summary_json = {
            "schema_id": "layer3.b1b_session_state.v1",
            "review_record_ref": review_record_ref,
            "review_state": review_state,
            "result_review_hash": result_review_hash,
            "analysis_plan_id": connector_b1_evidence["analysis_plan_id"],
            "pass_run_id": connector_b1_evidence["pass_run_id"],
            "analysis_run_id": connector_b1_evidence["analysis_run_id"],
            "package_review_state": None,
            "package_review_hash": None,
            "reconciliation_record_id": None,
            "packages": None,
            "connector_dataset_handoff_basis_hash": None,
        }
        db.flush()
        if not _materialized_replay_summary_is_valid(db, receipt=receipt, promoted=promoted):
            raise _closed_b1b_error("connector_materialization_basis_conflict")
        response = _b1b_result_review_response(
            record=record,
            result_review_hash=result_review_hash,
        )
        db.commit()
        db.info.pop("b1b_promotion_identity_lock", None)
        return response
    except ConnectorPromotionError:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise
    except DBAPIError as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise _closed_b1b_error("connector_promotion_bridge_unavailable") from exc


def b1b_result_review_from_pass_run(
    db: OrmSession,
    pass_run: L3PassRun,
) -> dict[str, Any] | None:
    summary = pass_run.summary_json
    if not isinstance(summary, dict):
        return None
    review = summary.get("execution_result_review")
    review_keys = _RESULT_REVIEW_RECORD_KEYS | {
        "review_record_ref",
        "review_state",
        "result_review_hash",
    }
    if not _has_exact_keys(review, frozenset(review_keys)):
        return None
    assert isinstance(review, dict)
    try:
        record = {key: review[key] for key in _RESULT_REVIEW_RECORD_KEYS}
        decision = record["operator_decision"]
        result_hash = review["result_review_hash"]
        expected_items = [
            {
                "index": 0,
                "item_ref": f"analysis-artifact:{record['analysis_artifact_id']}",
                "item_type": "fact",
                "trace_status": "resolved",
                "missing_trace_fields": [],
            },
            {
                "index": 1,
                "item_ref": f"caveat:{record['caveat_note_id']}",
                "item_type": "caveat",
                "trace_status": "resolved",
                "missing_trace_fields": [],
            },
        ]
        check_ids = record["assumption_check_ids"]
        if (
            record["schema_id"] != "layer3.b1b_result_review_record.v1"
            or not all(
                _is_uuid_string(record[field])
                for field in (
                    "promotion_receipt_id",
                    "promoted_session_id",
                    "analysis_plan_id",
                    "pass_run_id",
                    "analysis_run_id",
                    "analysis_artifact_id",
                    "caveat_note_id",
                )
            )
            or record["promoted_session_id"] != pass_run.session_id
            or record["analysis_plan_id"] != pass_run.analysis_plan_id
            or record["pass_run_id"] != pass_run.pass_run_id
            or not _is_nonempty_string(record["preview_id"])
            or record["preview_id"] != record["preview_id"].strip()
            or record["preview_id"] != summary.get("source_preview_id")
            or not _is_lower_hex64(record["preview_hash"])
            or record["preview_hash"] != summary.get("source_preview_hash")
            or record["analysis_run_id"] != summary.get("analysis_run_id")
            or not _is_lower_hex64(record["result_payload_sha256"])
            or not _is_lower_hex64(record["analysis_artifact_sha256"])
            or not _is_lower_hex64(record["result_review_request_basis_hash"])
            or _RESULT_REVIEW_STATES.get(decision) != review["review_state"]
            or not _is_lower_hex64(result_hash)
            or d33_sha256(record) != result_hash
            or review["review_record_ref"] != f"b1b-result-review-{result_hash}"
            or not isinstance(check_ids, list)
            or len(check_ids) != 4
            or len(set(check_ids)) != 4
            or not all(_is_uuid_string(value) for value in check_ids)
            or record["reviewed_output_items"] != expected_items
            or type(record["unresolved_trace_count"]) is not int
            or record["unresolved_trace_count"] != 0
        ):
            return None
        notes = record["review_notes"]
        if decision == "approved":
            if notes is not None:
                return None
        elif not isinstance(notes, str) or not notes or notes != notes.strip():
            return None
        receipt = db.get(L3ConnectorPromotionReceipt, record["promotion_receipt_id"])
        promoted = db.get(L3Session, record["promoted_session_id"])
        if (
            receipt is None
            or promoted is None
            or not _materialized_replay_summary_is_valid(
                db,
                receipt=receipt,
                promoted=promoted,
            )
        ):
            return None
        return {
            **review,
            "source_preview_id": record["preview_id"],
            "source_preview_hash": record["preview_hash"],
        }
    except (DBAPIError, KeyError, PromotionIdentityError, TypeError, ValueError):
        return None


def _read_b1b_package_authority() -> dict[str, str]:
    """Reopen and validate the pass-to-launch authority without exposing its path."""
    path_value = os.environ.get("PROJECT6_B1B_ATTESTATION_PATH", "")
    expected_sha256 = os.environ.get("PROJECT6_B1B_ATTESTATION_SHA256", "")
    profile = os.environ.get("PROJECT6_B1B_DATABASE_PROFILE", "")
    if not path_value or not _is_lower_hex64(expected_sha256):
        raise PromotionIdentityError("B1b package attestation is unavailable")
    path = Path(path_value)
    _require_nonreparse_components(path)
    if _is_reparse(path) or not stat.S_ISREG(path.stat().st_mode):
        raise PromotionIdentityError("B1b package attestation is not a regular file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise PromotionIdentityError("B1b package attestation hash mismatch")
    document = json.loads(raw.decode("utf-8"))
    authority = document.get("authority") if isinstance(document, dict) else None
    if not isinstance(authority, dict):
        raise PromotionIdentityError("B1b package authority is malformed")

    def authority_object(name: str) -> dict[str, Any]:
        value = authority.get(name)
        if not isinstance(value, dict):
            raise PromotionIdentityError("B1b package authority is incomplete")
        return value

    packet = authority_object("packet")
    correction = authority_object("correction")
    owner_decision = authority_object("dispatch_owner_decision")
    result = {
        "packet_full_sha256": packet.get("full_sha256"),
        "packet_canonical_sha256": packet.get("canonical_sha256"),
        "correction_full_sha256": correction.get("full_sha256"),
        "owner_decision_full_sha256": owner_decision.get("full_sha256"),
        "owner_decision_canonical_sha256": owner_decision.get("canonical_sha256"),
        "owner_bound_main_sha": authority.get("owner_bound_main_sha"),
        "implementation_head_sha": authority.get("candidate_head_sha"),
        "pass_to_launch_sha256": expected_sha256,
        "profile": profile,
    }
    if (
        any(not _is_lower_hex64(result[key]) for key in result if key.endswith("sha256"))
        or any(
            not isinstance(result[key], str)
            or len(result[key]) != 40
            or any(character not in _HEX40 for character in result[key])
            for key in ("owner_bound_main_sha", "implementation_head_sha")
        )
        or correction.get("owner_bound_main_sha") != result["owner_bound_main_sha"]
        or profile not in {"sqlite_authorized", "postgresql_authorized"}
    ):
        raise PromotionIdentityError("B1b package authority binding is malformed")
    return result


def _b1b_package_preview_request(payload: dict[str, Any]) -> dict[str, str]:
    if not _has_exact_keys(payload, _B1B_PACKAGE_PREVIEW_REQUEST_KEYS):
        raise _closed_b1b_error("b1b_request_validation_failed")
    if not all(isinstance(payload[key], str) for key in _B1B_PACKAGE_PREVIEW_REQUEST_KEYS):
        raise _closed_b1b_error("b1b_request_validation_failed")
    for field in ("session_id", "analysis_plan_id", "pass_run_id", "analysis_run_id"):
        if payload[field] != payload[field].strip() or not _is_uuid_string(payload[field]):
            raise _closed_b1b_error("b1b_request_validation_failed")
    if (
        not payload["preview_id"]
        or payload["preview_id"] != payload["preview_id"].strip()
        or not _is_lower_hex64(payload["preview_hash"])
        or not re.fullmatch(r"b1b-result-review-[0-9a-f]{64}", payload["result_review_record_ref"])
    ):
        raise _closed_b1b_error("b1b_request_validation_failed")
    return dict(payload)


def _b1b_package_commit_request(payload: dict[str, Any]) -> tuple[dict[str, str], str]:
    if not _has_exact_keys(payload, _B1B_PACKAGE_COMMIT_REQUEST_KEYS):
        raise _closed_b1b_error("b1b_request_validation_failed")
    preview = _b1b_package_preview_request(
        {key: payload[key] for key in _B1B_PACKAGE_PREVIEW_REQUEST_KEYS}
    )
    package_preview_hash = payload["package_review_preview_hash"]
    client_request_id = payload["client_request_id"]
    if (
        not _is_lower_hex64(package_preview_hash)
        or client_request_id != f"b1b-package-construction-{package_preview_hash}"
        or payload["expected_package_kinds"] != _B1B_PACKAGE_ORDER
    ):
        raise _closed_b1b_error("b1b_request_validation_failed")
    return preview, package_preview_hash


def _locked_b1b_approved_review(
    db: OrmSession,
    *,
    request_basis: dict[str, str],
) -> tuple[
    L3ConnectorPromotionReceipt,
    L3Session,
    L3PassRun,
    dict[str, Any],
    dict[str, Any],
]:
    receipt, promoted, pass_run, evidence = _locked_b1b_result_review_authority(
        db,
        request_basis=request_basis,
    )
    review = b1b_result_review_from_pass_run(db, pass_run)
    if (
        review is None
        or review.get("operator_decision") != "approved"
        or review.get("review_state") != _RESULT_REVIEW_STATES["approved"]
        or review.get("review_record_ref") != request_basis["result_review_record_ref"]
        or review.get("result_review_hash")
        != request_basis["result_review_record_ref"].removeprefix("b1b-result-review-")
        or any(review.get(key) != value for key, value in evidence.items())
    ):
        raise _closed_b1b_error("connector_package_basis_conflict")
    return receipt, promoted, pass_run, evidence, review


def _b1b_package_preview_basis(
    *,
    request_basis: dict[str, str],
    receipt: L3ConnectorPromotionReceipt,
    review: dict[str, Any],
    correction_full_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.b1b_package_review_preview_basis.v1",
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session_id": request_basis["session_id"],
        "analysis_plan_id": request_basis["analysis_plan_id"],
        "pass_run_id": request_basis["pass_run_id"],
        "preview_id": request_basis["preview_id"],
        "preview_hash": request_basis["preview_hash"],
        "analysis_run_id": request_basis["analysis_run_id"],
        "result_review_hash": review["result_review_hash"],
        "candidate_package_kinds": list(_B1B_PACKAGE_ORDER),
        "package_contract_schema_id": "layer3.b1b_package_contract.v1",
        "correction_full_sha256": correction_full_sha256,
    }


def preview_b1b_package_review(
    db: OrmSession,
    payload: dict[str, Any],
) -> B1BClosedApiResponse:
    request_basis = _b1b_package_preview_request(payload)
    if not bridge_precondition_available():
        raise _closed_b1b_error("connector_promotion_bridge_unavailable")
    try:
        authority = _read_b1b_package_authority()
        acquire_promotion_identity_lock(db, F07_CANONICAL_IDENTITY_KEY_HASH)
        receipt, _promoted, _pass_run, _evidence, review = _locked_b1b_approved_review(
            db,
            request_basis=request_basis,
        )
        basis = _b1b_package_preview_basis(
            request_basis=request_basis,
            receipt=receipt,
            review=review,
            correction_full_sha256=authority["correction_full_sha256"],
        )
        body = {
            "schema_id": "layer3.b1b_package_review_preview_response.v1",
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "promoted_session_id": request_basis["session_id"],
            "analysis_plan_id": request_basis["analysis_plan_id"],
            "pass_run_id": request_basis["pass_run_id"],
            "analysis_run_id": request_basis["analysis_run_id"],
            "result_review_hash": review["result_review_hash"],
            "package_review_preview_hash": d33_sha256(basis),
            "candidate_package_kinds": list(_B1B_PACKAGE_ORDER),
            "member_count": 9,
            "package_contract_schema_id": "layer3.b1b_package_contract.v1",
            "correction_full_sha256": authority["correction_full_sha256"],
        }
        response = B1BClosedApiResponse(body, http_status=200)
        db.rollback()
        db.info.pop("b1b_promotion_identity_lock", None)
        return response
    except ConnectorPromotionError:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise
    except (DBAPIError, OSError, UnicodeError, ValueError, PromotionIdentityError) as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise _closed_b1b_error("connector_promotion_bridge_unavailable") from exc


def _single_locked_row(db: OrmSession, model, session_id: str):
    rows = db.query(model).filter(model.session_id == session_id).with_for_update().all()
    if len(rows) != 1:
        raise _closed_b1b_error("connector_package_basis_conflict")
    return rows[0]


def _b1b_fixture_disclosure() -> dict[str, Any]:
    return {
        "source_fixture_id": "F07",
        "proof_cell_id": "C01",
        "synthetic": True,
        "byte_length": 34,
        "content_sha256": F07_CONTENT_SHA256,
        "official_public_read_evidence": False,
        "f20_status": "NOT-ESTABLISHED",
    }


def _b1b_lineage_fixture() -> dict[str, Any]:
    return {**_b1b_fixture_disclosure(), "media_type": "text/csv"}


def _b1b_battery_expected_census(profile: str) -> dict[str, Any]:
    if profile not in {"sqlite_authorized", "postgresql_authorized"}:
        raise PromotionIdentityError("B1b package profile is not authorized")
    comparison_count = 3 if profile == "sqlite_authorized" else 0
    return {
        "analysis_artifact_count": 1,
        "analysis_run_count": 1,
        "assumption_check_count": 4,
        "authoritative_application_file_count_at_c2": 9,
        "authoritative_session_spine_count": 2,
        "caveat_count": 1,
        "dataset_count": 1,
        "dataset_version_count": 1,
        "materializer_comparison_run_count": comparison_count,
        "method_comparison_run_count": comparison_count,
        "output_package_count": 3,
        "profile": profile,
        "promotion_receipt_count": 1,
        "schema_id": "layer3.b1b_battery_expected_census.v1",
        "variable_definition_count": 2,
    }


def _b1b_replay_contract() -> dict[str, Any]:
    return {
        "authoritative_same_request": {
            "changed_columns": [],
            "http_status": 200,
            "new_files": 0,
            "new_rows": 0,
            "zero_mutation": True,
        },
        "cross_run_same_i1": {
            "changed_columns": ["dataset_id", "dataset_version_id", "updated_at"],
            "excluded_from_authoritative_c0_c3": True,
            "http_status": 200,
            "new_files": 0,
            "new_rows": 0,
        },
        "divergent_d34": {
            "changed_columns": [],
            "error_code": "promotion_identity_decision_conflict",
            "excluded_from_authoritative_c0_c3": True,
            "http_status": 409,
            "new_files": 0,
            "new_rows": 0,
        },
        "schema_id": "layer3.b1b_replay_contract.v1",
        "seam_order": [
            "same_request_exact_replay",
            "cross_run_same_i1_reuse",
            "divergent_d34_conflict",
        ],
    }


def _build_b1b_package_members(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    pass_run: L3PassRun,
    review: dict[str, Any],
    package_review_preview_hash: str,
    authority: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    snapshot = _single_locked_row(db, L3MaterialSnapshot, promoted.session_id)
    typing = _single_locked_row(db, L3TypingRecord, promoted.session_id)
    unit = _single_locked_row(db, L3AnalysisUnit, promoted.session_id)
    group = _single_locked_row(db, L3AnalysisGroup, promoted.session_id)
    analysis_set = _single_locked_row(db, L3AnalysisSet, promoted.session_id)
    plan = _single_locked_row(db, L3AnalysisPlan, promoted.session_id)
    analysis_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.analysis_run_id == review["analysis_run_id"])
        .with_for_update()
        .first()
    )
    intake = (
        db.query(L3ConnectorSourceIntakeRecord)
        .filter(
            L3ConnectorSourceIntakeRecord.connector_source_intake_record_id
            == receipt.connector_source_intake_record_id
        )
        .with_for_update()
        .first()
    )
    target = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_target_id == intake.connector_run_target_id)
        .with_for_update()
        .first()
        if intake is not None
        else None
    )
    gate_snapshot = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.material_snapshot_id == receipt.gate_b_material_snapshot_id)
        .with_for_update()
        .first()
    )
    dataset = (
        db.query(Dataset)
        .filter(Dataset.dataset_id == receipt.dataset_id)
        .with_for_update()
        .first()
    )
    version = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_version_id == receipt.dataset_version_id)
        .with_for_update()
        .first()
    )
    provenance_rows = (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == receipt.dataset_version_id)
        .with_for_update()
        .all()
    )
    variables = (
        db.query(VariableDefinition)
        .filter(VariableDefinition.dataset_version_id == receipt.dataset_version_id)
        .order_by(VariableDefinition.ordinal_position)
        .with_for_update()
        .all()
    )
    checks = (
        db.query(AssumptionCheck)
        .filter(AssumptionCheck.analysis_run_id == review["analysis_run_id"])
        .with_for_update()
        .all()
    )
    caveat_rows = (
        db.query(CaveatNote)
        .filter(CaveatNote.analysis_run_id == review["analysis_run_id"])
        .with_for_update()
        .all()
    )
    artifact = (
        db.query(AnalysisArtifact)
        .filter(AnalysisArtifact.artifact_id == review["analysis_artifact_id"])
        .with_for_update()
        .first()
    )
    wrapper = (promoted.operator_context_json or {}).get(MATERIALIZATION_CONTEXT_KEY)
    if (
        analysis_run is None
        or intake is None
        or target is None
        or gate_snapshot is None
        or dataset is None
        or version is None
        or len(provenance_rows) != 1
        or len(variables) != 2
        or [row.variable_name for row in variables] != ["site_id", "value"]
        or len(checks) != 4
        or len(caveat_rows) != 1
        or artifact is None
        or not isinstance(wrapper, dict)
        or set(wrapper) != {"record", "record_hash"}
        or not isinstance(wrapper["record"], dict)
        or d33_sha256(wrapper["record"]) != wrapper["record_hash"]
    ):
        raise _closed_b1b_error("connector_package_basis_conflict")
    provenance = provenance_rows[0]
    record = wrapper["record"]
    output = record.get("output") if isinstance(record, dict) else None
    if (
        not isinstance(output, dict)
        or promoted.status != "completed_with_warnings"
        or snapshot.source_shape != "dataset_version"
        or typing.material_snapshot_id != snapshot.material_snapshot_id
        or typing.candidate_modalities_json != ["quantitative"]
        or typing.chosen_modality != "quantitative"
        or typing.confidence != 1.0
        or typing.overridden_by_operator is not False
        or unit.unit_kind != "atomic"
        or unit.analysis_modality != "quantitative"
        or unit.member_snapshot_ids_json != [snapshot.material_snapshot_id]
        or unit.typing_record_ids_json != [typing.typing_record_id]
        or unit.must_remain_intact is not False
        or not _is_lower_hex64(unit.unit_hash)
        or group.analysis_modality != "quantitative"
        or not isinstance(group.typing_basis_json, dict)
        or group.typing_basis_json.get("group_basis") != "singleton"
        or group.analysis_unit_ids_json != [unit.analysis_unit_id]
        or group.status != "formed"
        or analysis_set.set_type != "single_item"
        or analysis_set.analysis_group_ids_json != [group.analysis_group_id]
        or analysis_set.analysis_unit_ids_json != [unit.analysis_unit_id]
        or plan.analysis_set_ids_json != [analysis_set.analysis_set_id]
        or plan.status != "approved"
        or plan.approved_by_operator is not True
        or pass_run.analysis_plan_id != plan.analysis_plan_id
        or pass_run.analysis_set_id != analysis_set.analysis_set_id
        or pass_run.pass_type != "single_item"
        or analysis_run.dataset_version_id != version.dataset_version_id
        or analysis_run.method_name != "descriptive_summary"
        or analysis_run.status != "completed"
        or artifact.artifact_type != "descriptive_summary_result"
        or target.connector_run_target_id != intake.connector_run_target_id
        or target.connector_run_id != intake.connector_run_id
        or gate_snapshot.session_id != receipt.gate_b_session_id
        or dataset.dataset_id != version.dataset_id
        or provenance.dataset_version_id != version.dataset_version_id
    ):
        raise _closed_b1b_error("connector_package_basis_conflict")

    fixture_disclosure = _b1b_fixture_disclosure()
    question = {
        "question_id": "CT4B-C01-DESC-001",
        "text": B1B_QUESTION_TEXT,
        "question_sha256": hashlib.sha256(B1B_QUESTION_TEXT.encode("utf-8")).hexdigest(),
    }
    check_by_id = {row.assumption_check_id: row for row in checks}
    assumption_checks: list[dict[str, Any]] = []
    for check_id in review["assumption_check_ids"]:
        row = check_by_id.get(check_id)
        if row is None:
            raise _closed_b1b_error("connector_package_basis_conflict")
        assumption_checks.append(
            {
                "assumption_check_id": row.assumption_check_id,
                "name": row.assumption_name,
                "method": row.check_method,
                "result": row.check_result,
                "severity": row.severity,
                "notes": row.notes,
            }
        )
    caveat_row = caveat_rows[0]
    caveat = {
        "caveat_note_id": caveat_row.caveat_note_id,
        "type": caveat_row.caveat_type,
        "severity": caveat_row.severity,
        "message": caveat_row.message,
    }
    result_record = {key: review[key] for key in _RESULT_REVIEW_RECORD_KEYS}
    result_review = {
        **result_record,
        "review_record_ref": review["review_record_ref"],
        "result_review_hash": review["result_review_hash"],
    }
    package_review = {
        "schema_id": "layer3.b1b_package_review_expected.v1",
        "review_state": "package_review_preview_ready",
        "package_review_preview_hash": package_review_preview_hash,
        "result_review_hash": review["result_review_hash"],
        "candidate_package_kinds": list(_B1B_PACKAGE_ORDER),
        "expected_member_count": 9,
        "package_contract_schema_id": "layer3.b1b_package_contract.v1",
        "correction_full_sha256": authority["correction_full_sha256"],
    }
    artifact_path, _ = _resolve_regular_reference(
        Path(artifact.storage_ref).name,
        settings.artifact_storage_dir,
    )
    artifact_bytes, artifact_sha256 = _file_facts(artifact_path)
    if artifact_sha256 != review["analysis_artifact_sha256"]:
        raise _closed_b1b_error("connector_package_basis_conflict")

    dataset_lineage = {
        "schema_id": "layer3.b1b_dataset_lineage.v1",
        "authority_bindings": {
            key: authority[key]
            for key in (
                "packet_full_sha256",
                "packet_canonical_sha256",
                "correction_full_sha256",
                "owner_decision_full_sha256",
                "owner_decision_canonical_sha256",
                "owner_bound_main_sha",
                "implementation_head_sha",
                "pass_to_launch_sha256",
            )
        },
        "fixture": _b1b_lineage_fixture(),
        "material_identity": {
            "source_family": receipt.source_family,
            "content_sha256": receipt.content_sha256,
            "identity_metadata_hash": receipt.identity_metadata_hash,
            "identity_metadata_hash_version": receipt.identity_metadata_hash_version,
            "canonical_identity_key_hash": receipt.canonical_identity_key_hash,
        },
        "capture_lineage": {
            "connector_run_id": intake.connector_run_id,
            "connector_run_target_id": intake.connector_run_target_id,
            "connector_source_intake_record_id": intake.connector_source_intake_record_id,
        },
        "gate_b_lineage": {
            "session_id": receipt.gate_b_session_id,
            "selection_manifest_id": receipt.gate_b_selection_manifest_id,
            "material_snapshot_id": receipt.gate_b_material_snapshot_id,
            "decision_manifest_id": receipt.gate_b_decision_manifest_id,
            "decision_manifest_hash": receipt.gate_b_decision_manifest_hash,
            "material_preview_hash": receipt.material_preview_hash,
        },
        "promotion_receipt": {
            "connector_promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "receipt_schema_version": receipt.receipt_schema_version,
            "approval_hash": receipt.approval_hash,
            "promotion_basis_hash": receipt.promotion_basis_hash,
            "materialization_status": receipt.materialization_status,
            "materialization_basis_hash": receipt.materialization_basis_hash,
        },
        "materialization": {
            "materialization_record_sha256": wrapper["record_hash"],
            "materialization_semantic_sha256": MATERIALIZATION_SEMANTIC_SHA256,
            "dataset_file_bytes": output["dataset_file_bytes"],
            "dataset_file_sha256": output["dataset_file_sha256"],
            "dataset_storage_ref_hash": output["dataset_storage_ref_hash"],
            "source_row_count": output["source_row_count"],
            "row_count": output["row_count"],
            "dropped_row_count": output["dropped_row_count"],
            "column_count": 2,
            "variable_count": output["variable_count"],
        },
        "dataset_lineage": {
            "source_connector_id": output["source_connector_id"],
            "dataset_id": dataset.dataset_id,
            "dataset_version_id": version.dataset_version_id,
            "dataset_version_content_sha256": version.content_hash,
            "dataset_source_provenance_id": provenance.dataset_source_provenance_id,
            "variable_definition_ids": [row.variable_id for row in variables],
        },
        "nonclaims": list(B1B_LIMITATIONS),
    }

    canonical_3c = {
        "schema_id": "layer3.b1b_canonical_3c.v1",
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session": {
            "session_id": promoted.session_id,
            "status": promoted.status,
            "snapshot_count": 1,
        },
        "material_snapshot": {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "source_shape": snapshot.source_shape,
            "dataset_version_id": version.dataset_version_id,
            "content_sha256": snapshot.payload_hash,
        },
        "typing_record": {
            "typing_record_id": typing.typing_record_id,
            "material_snapshot_id": typing.material_snapshot_id,
            "candidate_modalities": typing.candidate_modalities_json,
            "chosen_modality": typing.chosen_modality,
            "confidence": typing.confidence,
            "overridden_by_operator": typing.overridden_by_operator,
        },
        "analysis_unit": {
            "analysis_unit_id": unit.analysis_unit_id,
            "unit_kind": unit.unit_kind,
            "analysis_modality": unit.analysis_modality,
            "material_snapshot_ids": unit.member_snapshot_ids_json,
            "typing_record_ids": unit.typing_record_ids_json,
            "must_remain_intact": unit.must_remain_intact,
            "unit_hash": unit.unit_hash,
        },
        "analysis_group": {
            "analysis_group_id": group.analysis_group_id,
            "analysis_modality": group.analysis_modality,
            "group_basis": group.typing_basis_json.get("group_basis"),
            "analysis_unit_ids": group.analysis_unit_ids_json,
            "status": group.status,
        },
        "analysis_set": {
            "analysis_set_id": analysis_set.analysis_set_id,
            "set_type": analysis_set.set_type,
            "analysis_group_ids": analysis_set.analysis_group_ids_json,
            "analysis_unit_ids": analysis_set.analysis_unit_ids_json,
        },
        "census": {
            "promoted_sessions": 1,
            "material_snapshots": 1,
            "typing_records": 1,
            "analysis_units": 1,
            "analysis_groups": 1,
            "analysis_sets": 1,
        },
    }

    analysis_plan_pass = {
        "schema_id": "layer3.b1b_analysis_plan_pass.v1",
        "question": question,
        "method_contract": {
            "method": "descriptive_summary",
            "version": "1",
            "parameters": {},
            "contract_sha256": B1B_METHOD_CONTRACT_SHA256,
            "method_input_sha256": METHOD_INPUT_SHA256,
        },
        "analysis_plan": {
            "analysis_plan_id": plan.analysis_plan_id,
            "analysis_set_id": analysis_set.analysis_set_id,
            "status": plan.status,
            "approved_by_operator": plan.approved_by_operator,
            "preview_id": review["preview_id"],
            "preview_hash": review["preview_hash"],
        },
        "pass_run": {
            "pass_run_id": pass_run.pass_run_id,
            "analysis_plan_id": pass_run.analysis_plan_id,
            "analysis_set_id": pass_run.analysis_set_id,
            "pass_type": pass_run.pass_type,
            "selected_method_name": "descriptive_summary",
            "status": pass_run.status,
            "result_payload_sha256": review["result_payload_sha256"],
        },
        "analysis_run": {
            "analysis_run_id": analysis_run.analysis_run_id,
            "pass_run_id": pass_run.pass_run_id,
            "dataset_version_id": analysis_run.dataset_version_id,
            "method": analysis_run.method_name,
            "status": analysis_run.status,
            "result_payload_sha256": review["result_payload_sha256"],
        },
        "assumption_checks": assumption_checks,
        "caveat": caveat,
        "hash_links": {
            "question_sha256": question["question_sha256"],
            "method_contract_sha256": B1B_METHOD_CONTRACT_SHA256,
            "method_input_sha256": METHOD_INPUT_SHA256,
            "result_payload_sha256": review["result_payload_sha256"],
            "analysis_artifact_sha256": artifact_sha256,
            "materialization_semantic_sha256": MATERIALIZATION_SEMANTIC_SHA256,
        },
    }
    connector_b1_evidence = {
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session_id": promoted.session_id,
        "dataset_id": dataset.dataset_id,
        "dataset_version_id": version.dataset_version_id,
        "gate_b_session_id": receipt.gate_b_session_id,
        "connector_source_intake_record_id": intake.connector_source_intake_record_id,
        "canonical_identity_key_hash": receipt.canonical_identity_key_hash,
        "fixture_disclosure_sha256": d33_sha256(fixture_disclosure),
        "promotion_basis_hash": receipt.promotion_basis_hash,
        "materialization_basis_hash": receipt.materialization_basis_hash,
        "materialization_semantic_sha256": MATERIALIZATION_SEMANTIC_SHA256,
        "transformation_contract_sha256": TRANSFORM_CONTRACT_SHA256,
        "question_sha256": question["question_sha256"],
        "method_contract_sha256": B1B_METHOD_CONTRACT_SHA256,
        "method_input_sha256": METHOD_INPUT_SHA256,
        "analysis_run_id": analysis_run.analysis_run_id,
        "result_payload_sha256": review["result_payload_sha256"],
        "analysis_artifact_id": artifact.artifact_id,
        "analysis_artifact_sha256": artifact_sha256,
        "assumption_checks_sha256": d33_sha256(assumption_checks),
        "caveat_sha256": d33_sha256(caveat),
        "limitations_sha256": d33_sha256(B1B_LIMITATIONS),
        "battery_census_sha256": d33_sha256(
            _b1b_battery_expected_census(authority["profile"])
        ),
        "result_review_hash": review["result_review_hash"],
        "package_review_preview_hash": package_review_preview_hash,
        "assumption_check_count": 4,
        "caveat_count": 1,
        "expected_first_path_contract_sha256": B1B_EXPECTED_FIRST_PATH_CONTRACT_SHA256,
        "replay_contract_sha256": d33_sha256(_b1b_replay_contract()),
    }
    result_review_member = {
        "schema_id": "layer3.b1b_result_review.v1",
        "connector_b1_evidence": connector_b1_evidence,
        "bounded_result": json.loads(json.dumps(_B1B_BOUNDED_RESULT)),
        "result_artifact": {
            "analysis_artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "byte_length": artifact_bytes,
            "sha256": artifact_sha256,
            "result_payload_sha256": review["result_payload_sha256"],
        },
        "result_review": result_review,
        "package_review": package_review,
        "limitations": list(B1B_LIMITATIONS),
        "hash_links": {
            "dataset_lineage_sha256": d33_sha256(dataset_lineage),
            "canonical_3c_sha256": d33_sha256(canonical_3c),
            "analysis_plan_pass_sha256": d33_sha256(analysis_plan_pass),
            "result_review_hash": review["result_review_hash"],
            "package_review_preview_hash": package_review_preview_hash,
        },
    }
    same_origin_handoff = {
        "schema_id": "layer3.b1b_same_origin_handoff.v1",
        "eligibility_status": "pending_approved_package_review",
        "basis": {
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "promoted_session_id": promoted.session_id,
            "result_review_hash": review["result_review_hash"],
            "package_review_preview_hash": package_review_preview_hash,
            "required_handoff_basis_schema": "layer3.connector_dataset_handoff_basis.v1",
        },
        "expected_invariants": [
            "one_receipt",
            "one_three_package_set",
            "canonical_bytes_rehashed",
            "approved_reviews_required",
            "prepare_and_deliver_zero_mutation",
        ],
        "forbidden_substitutions": [
            "aps_package",
            "mixed_session",
            "caller_selected_package",
            "payload_reference",
            "predicted_review_outcome",
        ],
    }
    downstream_replay = {
        "schema_id": "layer3.b1b_downstream_replay.v1",
        "eligibility_status": "not_yet_executed",
        "basis_hashes": {
            "canonical_identity_key_hash": receipt.canonical_identity_key_hash,
            "approval_hash": receipt.approval_hash,
            "promotion_basis_hash": receipt.promotion_basis_hash,
            "materialization_basis_hash": receipt.materialization_basis_hash,
            "result_review_hash": review["result_review_hash"],
            "package_review_preview_hash": package_review_preview_hash,
        },
        "expected_seams": [
            "same_request_exact_replay",
            "cross_run_same_i1_reuse",
            "divergent_d34_conflict",
        ],
        "expected_zero_mutation": {
            "same_request": True,
            "cross_run_new_rows": 0,
            "cross_run_new_files": 0,
            "cross_run_changed_columns": ["dataset_id", "dataset_version_id", "updated_at"],
            "divergent": True,
        },
    }
    verdict = {
        "schema_id": "layer3.b1b_package_verdict.v1",
        "verdict": "PACKAGE-ELIGIBLE-NOT-FINAL",
        "pending_operations": [
            "package_persistence",
            "package_review_submit",
            "package_rehash",
            "handoff_prepare",
            "handoff_deliver",
            "downstream_replay",
            "final_census",
        ],
        "required_external_receipts": [
            "package-postclose-rehash.json",
            "handoff-delivery-receipt.json",
            "downstream-replay-receipt.json",
            "b1b-integrated-run-verdict.json",
        ],
        "nonclaims": list(B1B_LIMITATIONS),
    }
    members = {
        "dataset-lineage.json": dataset_lineage,
        "canonical-3c.json": canonical_3c,
        "analysis-plan-pass.json": analysis_plan_pass,
        "result-review.json": result_review_member,
        "same-origin-handoff.json": same_origin_handoff,
        "downstream-replay.json": downstream_replay,
        "b1b-verdict.json": verdict,
    }
    sensitive_values = _b1b_package_sensitive_values(
        target=target,
        intake=intake,
        gate_snapshot=gate_snapshot,
        promoted_snapshot=snapshot,
        version=version,
        provenance=provenance,
        pass_run=pass_run,
        artifact=artifact,
    )
    for member in members.values():
        _assert_b1b_package_no_leak(member, sensitive_values)
    return members, sensitive_values


def _b1b_index_entry(logical_path: str, content: Mapping[str, Any]) -> dict[str, Any]:
    content_bytes = d33_canonical_bytes(dict(content))
    return {
        "logical_path": logical_path,
        "ordinal": _B1B_MEMBER_PATHS.index(logical_path) + 1,
        "media_type": "application/json",
        "encoding": "utf-8",
        "bom": False,
        "terminal_newline": False,
        "byte_length": len(content_bytes),
        "sha256": hashlib.sha256(content_bytes).hexdigest(),
    }


def _build_b1b_bundle(
    first_members: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    first_order = [path for path in _B1B_MEMBER_PATHS if path in first_members]
    first_entries = {path: _b1b_index_entry(path, first_members[path]) for path in first_order}
    rehash_members = [
        {"logical_path": path, "sha256": first_entries[path]["sha256"]}
        for path in first_order
    ]
    rehash = {
        "schema_id": "layer3.b1b_package_rehash.v1",
        "member_count": 7,
        "members": rehash_members,
    }
    rehash_entry = _b1b_index_entry("package-rehash.json", rehash)
    manifest_entries = [
        first_entries[path] if path in first_entries else rehash_entry
        for path in _B1B_MEMBER_PATHS
        if path != "package-manifest.json"
    ]
    manifest = {
        "schema_id": "layer3.b1b_package_manifest.v1",
        "member_count": 8,
        "members": manifest_entries,
        "package_order_hash": d33_sha256(manifest_entries),
    }
    manifest_entry = _b1b_index_entry("package-manifest.json", manifest)
    complete = {**first_members, "package-manifest.json": manifest, "package-rehash.json": rehash}
    entries = [
        manifest_entry
        if path == "package-manifest.json"
        else rehash_entry
        if path == "package-rehash.json"
        else first_entries[path]
        for path in _B1B_MEMBER_PATHS
    ]
    bundle = {
        "schema_id": "layer3.b1b_evidence_bundle.v1",
        "member_count": 9,
        "members": [
            {"logical_path": path, "content": complete[path]}
            for path in _B1B_MEMBER_PATHS
        ],
    }
    index = {
        "schema_id": "layer3.b1b_evidence_bundle_index.v1",
        "member_count": 9,
        "members": entries,
        "package_order_hash": d33_sha256(entries),
    }
    aliases = {
        "bundle_index_order_hash": index["package_order_hash"],
        "package_manifest_sha256": manifest_entry["sha256"],
        "package_rehash_sha256": rehash_entry["sha256"],
    }
    return bundle, index, aliases


def _build_b1b_outer_packages(
    *,
    session_id: str,
    output_package_ids: Mapping[str, str],
    first_members: dict[str, dict[str, Any]],
    sensitive_values: set[str],
) -> tuple[dict[str, bytes], dict[str, str], list[dict[str, Any]]]:
    bundle, index, aliases = _build_b1b_bundle(first_members)
    canonical_key = f"l3:{session_id}:canonical_internal"
    canonical = {
        "package_header": {
            "schema_id": "layer3.canonical_internal_package.v1",
            "schema_version": 1,
            "package_key": canonical_key,
            "package_kind": "canonical_internal",
            "package_status": "package_complete",
            "session_id": session_id,
            "source_gate": "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE",
        },
        "b1_evidence_bundle": bundle,
        "b1_evidence_bundle_index": index,
    }
    canonical_bytes = d33_canonical_bytes(canonical)
    canonical_binding = {
        "schema_id": "layer3.b1b_canonical_package_binding.v1",
        "canonical_package_key": canonical_key,
        "canonical_payload_bytes": len(canonical_bytes),
        "canonical_payload_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
        "package_manifest_sha256": aliases["package_manifest_sha256"],
        "package_rehash_sha256": aliases["package_rehash_sha256"],
        "bundle_index_order_hash": aliases["bundle_index_order_hash"],
    }
    question = first_members["analysis-plan-pass.json"]["question"]
    user = {
        "package_header": {
            "schema_id": "layer3.user_facing_package.v1",
            "schema_version": 1,
            "package_key": f"l3:{session_id}:user_facing",
            "package_kind": "user_facing",
            "package_status": "package_complete",
            "session_id": session_id,
            "source_gate": "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE",
            "canonical_package_key": canonical_key,
        },
        "b1_public_disclosure": {
            "schema_id": "layer3.b1b_public_disclosure.v1",
            "fixture_disclosure": _b1b_fixture_disclosure(),
            "question": question,
            "bounded_result": json.loads(json.dumps(_B1B_BOUNDED_RESULT)),
            "limitations": list(B1B_LIMITATIONS),
        },
        "b1_evidence_bundle_index": index,
        "canonical_package_binding": canonical_binding,
    }
    review = {
        "package_header": {
            "schema_id": "layer3.review_facing_package.v1",
            "schema_version": 1,
            "package_key": f"l3:{session_id}:review_facing",
            "package_kind": "review_facing",
            "package_status": "package_complete",
            "session_id": session_id,
            "source_gate": "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE",
            "canonical_package_key": canonical_key,
        },
        "b1_evidence_bundle": bundle,
        "b1_evidence_bundle_index": index,
        "canonical_package_binding": canonical_binding,
    }
    objects = {
        "canonical_internal": canonical,
        "user_facing": user,
        "review_facing": review,
    }
    payloads: dict[str, bytes] = {}
    packages: list[dict[str, Any]] = []
    for kind in _B1B_PACKAGE_ORDER:
        _assert_b1b_package_no_leak(objects[kind], sensitive_values)
        payload = d33_canonical_bytes(objects[kind])
        payloads[kind] = payload
        packages.append(
            {
                "package_kind": kind,
                "output_package_id": output_package_ids[kind],
                "payload_bytes": len(payload),
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return payloads, aliases, packages


def _b1b_package_lane_paths() -> dict[str, Path]:
    custody_root = Path(settings.artifact_storage_dir)
    root = custody_root / "layer3"
    return {
        "custody_root": custody_root,
        "root": root,
        "stage": root / "b1b-packages-staging",
        "final": root / "b1b-packages",
        "containment": root / "b1b-packages-containment",
    }


def _ensure_b1b_package_lanes(paths: Mapping[str, Path]) -> None:
    for path in (paths["custody_root"], paths["root"], paths["stage"], paths["final"], paths["containment"]):
        _ensure_nonreparse_lane_directory(path, paths["custody_root"])


def _authoritative_b1b_package_files(
    db: OrmSession,
    *,
    authority: Mapping[str, str],
) -> dict[Path, tuple[int, str]]:
    session_ids: set[str] = set()
    for row in db.query(L3OutputPackage).all():
        if isinstance(row.summary_json, dict) and row.summary_json.get("profile") == "receipt_bound_b1b":
            session_ids.add(row.session_id)
    for row in db.query(L3ReconciliationRecord).all():
        if isinstance(row.summary_json, dict) and row.summary_json.get("profile") == "receipt_bound_b1b":
            session_ids.add(row.session_id)

    authoritative: dict[Path, tuple[int, str]] = {}
    for session_id in sorted(session_ids):
        pass_runs = (
            db.query(L3PassRun)
            .filter(L3PassRun.session_id == session_id)
            .with_for_update()
            .all()
        )
        if len(pass_runs) != 1:
            raise _closed_b1b_error("connector_package_basis_conflict")
        review = b1b_result_review_from_pass_run(db, pass_runs[0])
        if review is None or review.get("operator_decision") != "approved":
            raise _closed_b1b_error("connector_package_basis_conflict")
        request_basis = {
            "session_id": session_id,
            "analysis_plan_id": review["analysis_plan_id"],
            "pass_run_id": review["pass_run_id"],
            "preview_id": review["preview_id"],
            "preview_hash": review["preview_hash"],
            "analysis_run_id": review["analysis_run_id"],
            "result_review_record_ref": review["review_record_ref"],
        }
        receipt, promoted, pass_run, _evidence, locked_review = _locked_b1b_approved_review(
            db,
            request_basis=request_basis,
        )
        package_preview_hash = d33_sha256(
            _b1b_package_preview_basis(
                request_basis=request_basis,
                receipt=receipt,
                review=locked_review,
                correction_full_sha256=authority["correction_full_sha256"],
            )
        )
        state = _locked_b1b_package_set(
            db,
            receipt=receipt,
            promoted=promoted,
            pass_run=pass_run,
            request_basis=request_basis,
            review=locked_review,
            package_preview_hash=package_preview_hash,
            authority=authority,
        )
        if state is None:
            raise _closed_b1b_error("connector_package_basis_conflict")
        for package, row in zip(state["packages"], state["rows"], strict=True):
            path = Path(row.payload_ref).resolve()
            if path in authoritative:
                raise _closed_b1b_error("connector_package_basis_conflict")
            authoritative[path] = (package["payload_bytes"], package["payload_sha256"])
    return authoritative


def _contain_unreferenced_b1b_package_files(
    db: OrmSession,
    *,
    paths: Mapping[str, Path],
    authority: Mapping[str, str],
) -> None:
    authoritative = _authoritative_b1b_package_files(db, authority=authority)
    _reconcile_containment_records(paths["containment"])
    for stage in _regular_lane_files(paths["stage"]):
        basis_hash = _lane_file_basis(stage, paths["stage"], layout="basis-prefix")
        _contain_file(
            stage,
            containment_root=paths["containment"],
            basis_hash=basis_hash,
            namespace="package-stage-orphan",
        )
    for final in _regular_lane_files(paths["final"]):
        expected = authoritative.get(final.resolve())
        if expected is not None and _file_facts(final) == expected:
            continue
        basis_hash = _lane_file_basis(final, paths["final"], layout="basis-dirs")
        _contain_file(
            final,
            containment_root=paths["containment"],
            basis_hash=basis_hash,
            namespace="package-final-orphan",
        )


def _b1b_commit_response(
    *,
    receipt: L3ConnectorPromotionReceipt,
    request_basis: Mapping[str, str],
    review: Mapping[str, Any],
    package_preview_hash: str,
    construction_basis_hash: str,
    reconciliation_record_id: str,
    packages: list[dict[str, Any]],
) -> B1BClosedApiResponse:
    body = {
        "schema_id": "layer3.b1b_package_construction_commit_response.v1",
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session_id": request_basis["session_id"],
        "analysis_plan_id": request_basis["analysis_plan_id"],
        "pass_run_id": request_basis["pass_run_id"],
        "analysis_run_id": request_basis["analysis_run_id"],
        "result_review_hash": review["result_review_hash"],
        "package_review_preview_hash": package_preview_hash,
        "construction_basis_hash": construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "packages": [
            {
                "package_kind": item["package_kind"],
                "output_package_id": item["output_package_id"],
                "byte_length": item["payload_bytes"],
                "payload_sha256": item["payload_sha256"],
            }
            for item in packages
        ],
        "package_count": 3,
        "member_count": 9,
        "persistence_status": "committed",
    }
    return B1BClosedApiResponse(body, http_status=200)


def _locked_b1b_package_set(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    pass_run: L3PassRun,
    request_basis: Mapping[str, str],
    review: Mapping[str, Any],
    package_preview_hash: str,
    authority: Mapping[str, str],
) -> dict[str, Any] | None:
    reconciliation_rows = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == promoted.session_id)
        .with_for_update()
        .all()
    )
    rows = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == promoted.session_id)
        .with_for_update()
        .all()
    )
    if not reconciliation_rows and not rows:
        return None
    if len(reconciliation_rows) != 1 or len(rows) != 3:
        raise _closed_b1b_error("connector_package_basis_conflict")
    reconciliation = reconciliation_rows[0]
    summary = reconciliation.summary_json
    rows_by_kind = {row.package_kind: row for row in rows}
    if (
        set(rows_by_kind) != set(_B1B_PACKAGE_ORDER)
        or not _has_exact_keys(summary, _B1B_RECONCILIATION_SUMMARY_KEYS)
        or reconciliation.status != "reconciled"
    ):
        raise _closed_b1b_error("connector_package_basis_conflict")
    package_set = summary.get("package_set")
    if (
        not _has_exact_keys(package_set, _B1B_PACKAGE_SET_KEYS)
        or summary.get("schema_id") != "layer3.b1b_reconciliation_summary.v1"
        or summary.get("profile") != "receipt_bound_b1b"
        or summary.get("source_gate") != "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE"
        or summary.get("promotion_receipt_id") != receipt.connector_promotion_receipt_id
        or summary.get("promoted_session_id") != promoted.session_id
        or summary.get("result_review_hash") != review["result_review_hash"]
        or summary.get("package_review_preview_hash") != package_preview_hash
        or package_set.get("member_count") != 9
        or type(package_set.get("member_count")) is not int
        or any(
            not _is_lower_hex64(package_set.get(field))
            for field in (
                "construction_basis_hash",
                "bundle_index_order_hash",
                "package_manifest_sha256",
                "package_rehash_sha256",
            )
        )
    ):
        raise _closed_b1b_error("connector_package_basis_conflict")
    stored_packages = package_set.get("packages")
    if not isinstance(stored_packages, list) or len(stored_packages) != 3:
        raise _closed_b1b_error("connector_package_basis_conflict")
    paths = _b1b_package_lane_paths()
    sensitive_values = _b1b_runtime_sensitive_values() | {
        row.payload_ref for row in rows if isinstance(row.payload_ref, str) and row.payload_ref
    }
    try:
        first_members, derived_sensitive_values = _build_b1b_package_members(
            db,
            receipt=receipt,
            promoted=promoted,
            pass_run=pass_run,
            review=dict(review),
            package_review_preview_hash=package_preview_hash,
            authority=dict(authority),
        )
        sensitive_values.update(derived_sensitive_values)
        expected_payloads, aliases, packages = _build_b1b_outer_packages(
            session_id=promoted.session_id,
            output_package_ids={
                kind: rows_by_kind[kind].output_package_id for kind in _B1B_PACKAGE_ORDER
            },
            first_members=first_members,
            sensitive_values=sensitive_values,
        )
    except (OSError, KeyError, TypeError, ValueError, PromotionIdentityError) as exc:
        raise _closed_b1b_error("connector_package_basis_conflict") from exc
    package_paths: dict[str, Path] = {}
    for index, kind in enumerate(_B1B_PACKAGE_ORDER):
        row = rows_by_kind[kind]
        stored = stored_packages[index]
        try:
            if not isinstance(row.payload_ref, str) or not Path(row.payload_ref).is_absolute():
                raise PromotionIdentityError("B1b package reference is not absolute")
            resolved, _relative = _resolve_regular_reference(row.payload_ref, str(paths["final"]))
            payload = resolved.read_bytes()
            facts = (len(payload), hashlib.sha256(payload).hexdigest())
        except (OSError, UnicodeError, ValueError, TypeError, PromotionIdentityError) as exc:
            raise _closed_b1b_error("connector_package_basis_conflict") from exc
        expected = packages[index]
        expected_summary = {
            "schema_id": "layer3.b1b_output_package_summary.v1",
            "profile": "receipt_bound_b1b",
            "package_kind": kind,
            "member_count": 0 if kind == "user_facing" else 9,
            **aliases,
            "canonical_binding_present": index != 0,
        }
        if (
            row.reconciliation_record_id != reconciliation.reconciliation_record_id
            or row.status != "package_complete"
            or row.payload_hash != facts[1]
            or payload != expected_payloads[kind]
            or facts != (expected["payload_bytes"], expected["payload_sha256"])
            or stored != expected
            or row.summary_json != expected_summary
        ):
            raise _closed_b1b_error("connector_package_basis_conflict")
        package_paths[kind] = resolved
    construction_basis = build_b1b_package_construction_basis(
        authority={
            "correction_full_sha256": authority["correction_full_sha256"],
            "owner_bound_main_sha": authority["owner_bound_main_sha"],
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "promoted_session_id": promoted.session_id,
            "result_review_hash": review["result_review_hash"],
            "package_review_preview_hash": package_preview_hash,
        },
        bundle={"member_count": 9, **aliases},
        packages=packages,
    )
    construction_basis_hash = d33_sha256(construction_basis)
    if package_set != {
        "construction_basis_hash": construction_basis_hash,
        "member_count": 9,
        **aliases,
        "packages": packages,
    }:
        raise _closed_b1b_error("connector_package_basis_conflict")
    try:
        for kind, path in package_paths.items():
            expected_path = (
                paths["final"]
                / construction_basis_hash[:2]
                / construction_basis_hash
                / f"{kind}.json"
            ).resolve(strict=True)
            if path != expected_path:
                raise PromotionIdentityError("B1b package path does not match its basis")
    except (OSError, KeyError, TypeError, ValueError, PromotionIdentityError) as exc:
        raise _closed_b1b_error("connector_package_basis_conflict") from exc
    return {
        "reconciliation": reconciliation,
        "rows": [rows_by_kind[kind] for kind in _B1B_PACKAGE_ORDER],
        "package_set": package_set,
        "packages": packages,
        "construction_basis_hash": construction_basis_hash,
        "sensitive_values": sensitive_values,
        "response": _b1b_commit_response(
            receipt=receipt,
            request_basis=request_basis,
            review=review,
            package_preview_hash=package_preview_hash,
            construction_basis_hash=construction_basis_hash,
            reconciliation_record_id=reconciliation.reconciliation_record_id,
            packages=packages,
        ),
    }


def _after_b1b_package_publish(_ordinal: int) -> None:
    """Crash seam invoked after each no-clobber package publication."""


def _commit_b1b_packages(db: OrmSession) -> None:
    """Commit seam used to distinguish acknowledged and ambiguous outcomes."""
    db.commit()


def _reconcile_failed_b1b_packages(
    engine,
    *,
    request_basis: Mapping[str, str],
    paths: Mapping[str, Path],
    expectation: Mapping[str, Any] | None,
    authority: Mapping[str, str],
) -> str:
    with OrmSession(bind=engine, expire_on_commit=False) as verify_db:
        acquire_promotion_identity_lock(verify_db, F07_CANONICAL_IDENTITY_KEY_HASH)
        reconciliations = (
            verify_db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.session_id == request_basis["session_id"])
            .with_for_update()
            .all()
        )
        rows = (
            verify_db.query(L3OutputPackage)
            .filter(L3OutputPackage.session_id == request_basis["session_id"])
            .with_for_update()
            .all()
        )
        if expectation is not None and len(reconciliations) == 1 and len(rows) == 3:
            try:
                receipt, promoted, pass_run, _evidence, review = _locked_b1b_approved_review(
                    verify_db,
                    request_basis=dict(request_basis),
                )
                package_preview_hash = d33_sha256(
                    _b1b_package_preview_basis(
                        request_basis=dict(request_basis),
                        receipt=receipt,
                        review=review,
                        correction_full_sha256=authority["correction_full_sha256"],
                    )
                )
                state = _locked_b1b_package_set(
                    verify_db,
                    receipt=receipt,
                    promoted=promoted,
                    pass_run=pass_run,
                    request_basis=request_basis,
                    review=review,
                    package_preview_hash=package_preview_hash,
                    authority=authority,
                )
            except (
                ConnectorPromotionError,
                DBAPIError,
                KeyError,
                OSError,
                TypeError,
                ValueError,
                PromotionIdentityError,
            ):
                return "uncertain"
            if (
                state is not None
                and state["reconciliation"].reconciliation_record_id
                == expectation["reconciliation_record_id"]
                and state["construction_basis_hash"] == expectation["construction_basis_hash"]
                and state["packages"] == expectation["packages"]
            ):
                return "committed"
            return "uncertain"
        if not reconciliations and not rows:
            _contain_unreferenced_b1b_package_files(
                verify_db,
                paths=paths,
                authority=authority,
            )
            return "absent"
        return "uncertain"


def commit_b1b_packages(
    db: OrmSession,
    payload: dict[str, Any],
) -> B1BClosedApiResponse:
    request_basis, supplied_preview_hash = _b1b_package_commit_request(payload)
    if not bridge_precondition_available():
        raise _closed_b1b_error("connector_promotion_bridge_unavailable")
    paths = _b1b_package_lane_paths()
    bind = db.get_bind()
    engine = getattr(bind, "engine", bind)
    authority: dict[str, str] | None = None
    expectation: dict[str, Any] | None = None
    response: B1BClosedApiResponse | None = None
    try:
        authority = _read_b1b_package_authority()
        acquire_promotion_identity_lock(db, F07_CANONICAL_IDENTITY_KEY_HASH)
        receipt, promoted, pass_run, _evidence, review = _locked_b1b_approved_review(
            db,
            request_basis=request_basis,
        )
        preview_basis = _b1b_package_preview_basis(
            request_basis=request_basis,
            receipt=receipt,
            review=review,
            correction_full_sha256=authority["correction_full_sha256"],
        )
        package_preview_hash = d33_sha256(preview_basis)
        if supplied_preview_hash != package_preview_hash:
            raise _closed_b1b_error("connector_package_basis_conflict")
        existing = _locked_b1b_package_set(
            db,
            receipt=receipt,
            promoted=promoted,
            pass_run=pass_run,
            request_basis=request_basis,
            review=review,
            package_preview_hash=package_preview_hash,
            authority=authority,
        )
        _ensure_b1b_package_lanes(paths)
        _contain_unreferenced_b1b_package_files(db, paths=paths, authority=authority)
        if existing is not None:
            if not _materialized_replay_summary_is_valid(
                db,
                receipt=receipt,
                promoted=promoted,
            ):
                raise _closed_b1b_error("connector_package_basis_conflict")
            db.rollback()
            db.info.pop("b1b_promotion_identity_lock", None)
            return existing["response"]

        output_package_ids = {kind: str(uuid.uuid4()) for kind in _B1B_PACKAGE_ORDER}
        reconciliation_record_id = str(uuid.uuid4())
        first_members, sensitive_values = _build_b1b_package_members(
            db,
            receipt=receipt,
            promoted=promoted,
            pass_run=pass_run,
            review=review,
            package_review_preview_hash=package_preview_hash,
            authority=authority,
        )
        package_payloads, aliases, packages = _build_b1b_outer_packages(
            session_id=promoted.session_id,
            output_package_ids=output_package_ids,
            first_members=first_members,
            sensitive_values=sensitive_values,
        )
        construction_basis = build_b1b_package_construction_basis(
            authority={
                "correction_full_sha256": authority["correction_full_sha256"],
                "owner_bound_main_sha": authority["owner_bound_main_sha"],
                "promotion_receipt_id": receipt.connector_promotion_receipt_id,
                "promoted_session_id": promoted.session_id,
                "result_review_hash": review["result_review_hash"],
                "package_review_preview_hash": package_preview_hash,
            },
            bundle={"member_count": 9, **aliases},
            packages=packages,
        )
        construction_basis_hash = d33_sha256(construction_basis)
        expectation = {
            "reconciliation_record_id": reconciliation_record_id,
            "construction_basis_hash": construction_basis_hash,
            "packages": packages,
        }
        response = _b1b_commit_response(
            receipt=receipt,
            request_basis=request_basis,
            review=review,
            package_preview_hash=package_preview_hash,
            construction_basis_hash=construction_basis_hash,
            reconciliation_record_id=reconciliation_record_id,
            packages=packages,
        )
        final_dir = paths["final"] / construction_basis_hash[:2] / construction_basis_hash
        _ensure_nonreparse_lane_directory(final_dir, paths["custody_root"])
        stage_paths: dict[str, Path] = {}
        final_paths: dict[str, Path] = {}
        for kind in _B1B_PACKAGE_ORDER:
            stage_path = paths["stage"] / f"{construction_basis_hash}-{uuid.uuid4().hex}-{kind}.json"
            final_path = final_dir / f"{kind}.json"
            if stage_path.exists() or final_path.exists():
                raise _closed_b1b_error("connector_package_basis_conflict")
            with stage_path.open("xb") as handle:
                handle.write(package_payloads[kind])
                handle.flush()
                os.fsync(handle.fileno())
            if _file_facts(stage_path) != (
                len(package_payloads[kind]),
                hashlib.sha256(package_payloads[kind]).hexdigest(),
            ):
                raise PromotionIdentityError("staged B1b package failed close verification")
            stage_paths[kind] = stage_path
            final_paths[kind] = final_path
        sensitive_values.update(
            str(path.resolve()) for path in (*stage_paths.values(), *final_paths.values())
        )
        for payload_bytes in package_payloads.values():
            _assert_b1b_package_no_leak(json.loads(payload_bytes), sensitive_values)
        for ordinal, kind in enumerate(_B1B_PACKAGE_ORDER, start=1):
            _atomic_rename_no_overwrite(stage_paths[kind], final_paths[kind])
            _after_b1b_package_publish(ordinal)
        if any(
            _file_facts(final_paths[item["package_kind"]])
            != (item["payload_bytes"], item["payload_sha256"])
            for item in packages
        ):
            raise PromotionIdentityError("published B1b package failed reopen verification")

        package_set = {
            "construction_basis_hash": construction_basis_hash,
            "member_count": 9,
            **aliases,
            "packages": packages,
        }
        reconciliation_summary = {
            "schema_id": "layer3.b1b_reconciliation_summary.v1",
            "profile": "receipt_bound_b1b",
            "source_gate": "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE",
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "promoted_session_id": promoted.session_id,
            "result_review_hash": review["result_review_hash"],
            "package_review_preview_hash": package_preview_hash,
            "package_set": package_set,
            "package_review_submit": None,
            "package_review_hash": None,
            "connector_dataset_handoff_basis": None,
            "connector_dataset_handoff_basis_hash": None,
        }
        _assert_b1b_package_no_leak(reconciliation_summary, sensitive_values)
        reconciliation = L3ReconciliationRecord(
            reconciliation_record_id=reconciliation_record_id,
            session_id=promoted.session_id,
            status="reconciled",
            summary_json=reconciliation_summary,
        )
        db.add(reconciliation)
        for index, item in enumerate(packages):
            kind = item["package_kind"]
            output_summary = {
                "schema_id": "layer3.b1b_output_package_summary.v1",
                "profile": "receipt_bound_b1b",
                "package_kind": kind,
                "member_count": 0 if kind == "user_facing" else 9,
                **aliases,
                "canonical_binding_present": index != 0,
            }
            _assert_b1b_package_no_leak(output_summary, sensitive_values)
            db.add(
                L3OutputPackage(
                    output_package_id=item["output_package_id"],
                    session_id=promoted.session_id,
                    reconciliation_record_id=reconciliation_record_id,
                    package_kind=kind,
                    status="package_complete",
                    payload_ref=str(final_paths[kind].resolve()),
                    payload_hash=item["payload_sha256"],
                    summary_json=output_summary,
                )
            )
        db.flush()
        if not _materialized_replay_summary_is_valid(db, receipt=receipt, promoted=promoted):
            raise _closed_b1b_error("connector_package_basis_conflict")
        _commit_b1b_packages(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        return response
    except ConnectorPromotionError as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        if expectation is not None and paths["custody_root"].exists():
            assert authority is not None
            outcome = _reconcile_failed_b1b_packages(
                engine,
                request_basis=request_basis,
                paths=paths,
                expectation=expectation,
                authority=authority,
            )
            if outcome == "committed" and response is not None:
                return response
            if outcome == "uncertain" and expectation is not None:
                raise _closed_b1b_error("connector_promotion_bridge_unavailable") from exc
        raise
    except (DBAPIError, OSError, UnicodeError, PromotionIdentityError) as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        outcome = (
            _reconcile_failed_b1b_packages(
                engine,
                request_basis=request_basis,
                paths=paths,
                expectation=expectation,
                authority=authority,
            )
            if expectation is not None
            and authority is not None
            and paths["custody_root"].exists()
            else "uncertain"
        )
        if outcome == "committed" and response is not None:
            return response
        raise _closed_b1b_error("connector_promotion_bridge_unavailable") from exc
    except Exception:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        outcome = (
            _reconcile_failed_b1b_packages(
                engine,
                request_basis=request_basis,
                paths=paths,
                expectation=expectation,
                authority=authority,
            )
            if expectation is not None
            and authority is not None
            and paths["custody_root"].exists()
            else "uncertain"
        )
        if outcome == "committed" and response is not None:
            return response
        raise


def _b1b_package_submit_request(
    payload: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any], str, str | None]:
    if not _has_exact_keys(payload, _B1B_PACKAGE_SUBMIT_REQUEST_KEYS):
        raise _closed_b1b_error("b1b_request_validation_failed")
    preview = _b1b_package_preview_request(
        {key: payload[key] for key in _B1B_PACKAGE_PREVIEW_REQUEST_KEYS}
    )
    decision = payload.get("operator_decision")
    raw_notes = payload.get("decision_notes")
    if decision not in _PACKAGE_REVIEW_STATES or not isinstance(raw_notes, str):
        raise _closed_b1b_error("b1b_request_validation_failed")
    if decision == "approved":
        if raw_notes != "":
            raise _closed_b1b_error("b1b_request_validation_failed")
        normalized_notes = None
    else:
        normalized_notes = raw_notes.strip()
        if not normalized_notes:
            raise _closed_b1b_error("b1b_request_validation_failed")
    for field in (
        "package_review_preview_hash",
        "construction_basis_hash",
    ):
        if not _is_lower_hex64(payload.get(field)):
            raise _closed_b1b_error("b1b_request_validation_failed")
    if not _is_uuid_string(payload.get("reconciliation_record_id")):
        raise _closed_b1b_error("b1b_request_validation_failed")
    for field in ("output_package_ids", "payload_hashes", "expected_package_kinds"):
        value = payload.get(field)
        if not isinstance(value, list) or len(value) != 3:
            raise _closed_b1b_error("b1b_request_validation_failed")
    if (
        not all(_is_uuid_string(value) for value in payload["output_package_ids"])
        or not all(_is_lower_hex64(value) for value in payload["payload_hashes"])
        or payload["expected_package_kinds"] != _B1B_PACKAGE_ORDER
    ):
        raise _closed_b1b_error("b1b_request_validation_failed")
    request_basis = {key: payload[key] for key in payload if key != "client_request_id"}
    request_basis_hash = d33_sha256(request_basis)
    if payload.get("client_request_id") != f"b1b-package-review-{request_basis_hash}":
        raise _closed_b1b_error("b1b_request_validation_failed")
    return preview, request_basis, request_basis_hash, normalized_notes


def _b1b_handoff_basis(
    *,
    receipt: L3ConnectorPromotionReceipt,
    promoted: L3Session,
    result_review_hash: str,
    package_review_hash: str,
    reconciliation_record_id: str,
    packages: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "approved_reviews": {
            "package_review_hash": package_review_hash,
            "result_review_hash": result_review_hash,
        },
        "canonical_internal": {
            "byte_length": packages[0]["payload_bytes"],
            "output_package_id": packages[0]["output_package_id"],
            "payload_hash": packages[0]["payload_sha256"],
        },
        "package_set": {
            "reconciliation_record_id": reconciliation_record_id,
            "review_facing_output_package_id": packages[2]["output_package_id"],
            "review_facing_payload_hash": packages[2]["payload_sha256"],
            "user_facing_output_package_id": packages[1]["output_package_id"],
            "user_facing_payload_hash": packages[1]["payload_sha256"],
        },
        "promoted_session_id": promoted.session_id,
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "schema_id": "layer3.connector_dataset_handoff_basis.v1",
    }


def _b1b_submit_response(
    *,
    receipt: L3ConnectorPromotionReceipt,
    request_basis: Mapping[str, Any],
    review: Mapping[str, Any],
    package_review_hash: str,
    package_review_state: str,
    packages: list[dict[str, Any]],
    normalized_notes: str | None,
    handoff_basis_hash: str | None,
) -> B1BClosedApiResponse:
    body: dict[str, Any] = {
        "schema_id": "layer3.b1b_package_review_submit_response.v1",
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session_id": request_basis["session_id"],
        "analysis_plan_id": request_basis["analysis_plan_id"],
        "pass_run_id": request_basis["pass_run_id"],
        "analysis_run_id": request_basis["analysis_run_id"],
        "result_review_hash": review["result_review_hash"],
        "package_review_preview_hash": request_basis["package_review_preview_hash"],
        "construction_basis_hash": request_basis["construction_basis_hash"],
        "package_review_hash": package_review_hash,
        "reconciliation_record_id": request_basis["reconciliation_record_id"],
        "packages": [
            {
                "package_kind": item["package_kind"],
                "output_package_id": item["output_package_id"],
                "byte_length": item["payload_bytes"],
                "payload_sha256": item["payload_sha256"],
            }
            for item in packages
        ],
        "operator_decision": request_basis["operator_decision"],
        "package_review_state": package_review_state,
        "decision_notes_present": normalized_notes is not None,
        "decision_notes_sha256": (
            hashlib.sha256(normalized_notes.encode("utf-8")).hexdigest()
            if normalized_notes is not None
            else None
        ),
        "handoff_eligibility_status": "eligible" if handoff_basis_hash else "ineligible",
    }
    if handoff_basis_hash is not None:
        body["connector_dataset_handoff_basis_hash"] = handoff_basis_hash
    return B1BClosedApiResponse(body, http_status=200)


def submit_b1b_package_review(
    db: OrmSession,
    payload: dict[str, Any],
) -> B1BClosedApiResponse:
    preview_request, request_basis, request_basis_hash, normalized_notes = (
        _b1b_package_submit_request(payload)
    )
    if not bridge_precondition_available():
        raise _closed_b1b_error("connector_promotion_bridge_unavailable")
    try:
        authority = _read_b1b_package_authority()
        acquire_promotion_identity_lock(db, F07_CANONICAL_IDENTITY_KEY_HASH)
        receipt, promoted, pass_run, _evidence, review = _locked_b1b_approved_review(
            db,
            request_basis=preview_request,
        )
        preview_basis = _b1b_package_preview_basis(
            request_basis=preview_request,
            receipt=receipt,
            review=review,
            correction_full_sha256=authority["correction_full_sha256"],
        )
        package_preview_hash = d33_sha256(preview_basis)
        package_state = _locked_b1b_package_set(
            db,
            receipt=receipt,
            promoted=promoted,
            pass_run=pass_run,
            request_basis=preview_request,
            review=review,
            package_preview_hash=package_preview_hash,
            authority=authority,
        )
        if package_state is None:
            raise _closed_b1b_error("connector_package_basis_conflict")
        packages = package_state["packages"]
        reconciliation = package_state["reconciliation"]
        sensitive_values = set(package_state["sensitive_values"])
        projected_ids = [item["output_package_id"] for item in packages]
        projected_hashes = [item["payload_sha256"] for item in packages]
        if (
            request_basis["package_review_preview_hash"] != package_preview_hash
            or request_basis["construction_basis_hash"]
            != package_state["construction_basis_hash"]
            or request_basis["reconciliation_record_id"]
            != reconciliation.reconciliation_record_id
            or request_basis["output_package_ids"] != projected_ids
            or request_basis["payload_hashes"] != projected_hashes
            or request_basis["expected_package_kinds"] != _B1B_PACKAGE_ORDER
        ):
            raise _closed_b1b_error("connector_package_basis_conflict")
        summary = reconciliation.summary_json
        try:
            _assert_b1b_package_no_leak(summary, sensitive_values)
        except PromotionIdentityError as exc:
            raise _closed_b1b_error("connector_package_basis_conflict") from exc
        existing = summary.get("package_review_submit")
        if existing is not None:
            if (
                not isinstance(existing, dict)
                or existing.get("review_request_basis_hash") != request_basis_hash
                or summary.get("package_review_hash") != d33_sha256(existing)
                or not _materialized_replay_summary_is_valid(
                    db,
                    receipt=receipt,
                    promoted=promoted,
                )
            ):
                raise _closed_b1b_error("connector_package_review_decision_conflict")
            handoff_hash = summary.get("connector_dataset_handoff_basis_hash")
            response = _b1b_submit_response(
                receipt=receipt,
                request_basis=request_basis,
                review=review,
                package_review_hash=summary["package_review_hash"],
                package_review_state=_PACKAGE_REVIEW_STATES[existing["operator_decision"]],
                packages=packages,
                normalized_notes=existing["decision_notes"],
                handoff_basis_hash=handoff_hash,
            )
            for item, row in zip(packages, package_state["rows"], strict=True):
                if _file_facts(Path(row.payload_ref)) != (
                    item["payload_bytes"],
                    item["payload_sha256"],
                ):
                    raise _closed_b1b_error("connector_package_basis_conflict")
            db.rollback()
            db.info.pop("b1b_promotion_identity_lock", None)
            return response
        if any(
            promoted.summary_json[field] is not None
            for field in (
                "package_review_state",
                "package_review_hash",
                "reconciliation_record_id",
                "packages",
                "connector_dataset_handoff_basis_hash",
            )
        ):
            raise _closed_b1b_error("connector_package_review_decision_conflict")

        decision = request_basis["operator_decision"]
        record = {
            "schema_id": "layer3.b1b_package_review_record.v1",
            "review_request_basis_hash": request_basis_hash,
            "package_review_preview_hash": package_preview_hash,
            "construction_basis_hash": package_state["construction_basis_hash"],
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "output_package_ids": projected_ids,
            "package_kinds": list(_B1B_PACKAGE_ORDER),
            "payload_hashes": projected_hashes,
            "operator_decision": decision,
            "decision_notes": normalized_notes,
        }
        try:
            _assert_b1b_package_no_leak(record, sensitive_values)
        except PromotionIdentityError as exc:
            raise _closed_b1b_error("b1b_request_validation_failed") from exc
        package_review_hash = d33_sha256(record)
        handoff_basis = None
        handoff_hash = None
        if decision == "approved":
            handoff_basis = _b1b_handoff_basis(
                receipt=receipt,
                promoted=promoted,
                result_review_hash=review["result_review_hash"],
                package_review_hash=package_review_hash,
                reconciliation_record_id=reconciliation.reconciliation_record_id,
                packages=packages,
            )
            handoff_hash = d33_sha256(handoff_basis)
        reconciliation_summary = {
            **json.loads(json.dumps(summary)),
            "package_review_submit": record,
            "package_review_hash": package_review_hash,
            "connector_dataset_handoff_basis": handoff_basis,
            "connector_dataset_handoff_basis_hash": handoff_hash,
        }
        session_packages = [
            {
                "package_kind": item["package_kind"],
                "output_package_id": item["output_package_id"],
                "payload_sha256": item["payload_sha256"],
            }
            for item in packages
        ]
        session_summary = {
            **json.loads(json.dumps(promoted.summary_json)),
            "package_review_state": _PACKAGE_REVIEW_STATES[decision],
            "package_review_hash": package_review_hash,
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "packages": session_packages,
            "connector_dataset_handoff_basis_hash": handoff_hash,
        }
        _assert_b1b_package_no_leak(reconciliation_summary, sensitive_values)
        _assert_b1b_package_no_leak(session_summary, sensitive_values)
        reconciliation.summary_json = reconciliation_summary
        promoted.summary_json = session_summary
        db.flush()
        if not _materialized_replay_summary_is_valid(db, receipt=receipt, promoted=promoted):
            raise _closed_b1b_error("connector_package_basis_conflict")
        for item, row in zip(packages, package_state["rows"], strict=True):
            if _file_facts(Path(row.payload_ref)) != (
                item["payload_bytes"],
                item["payload_sha256"],
            ):
                raise _closed_b1b_error("connector_package_basis_conflict")
        response = _b1b_submit_response(
            receipt=receipt,
            request_basis=request_basis,
            review=review,
            package_review_hash=package_review_hash,
            package_review_state=_PACKAGE_REVIEW_STATES[decision],
            packages=packages,
            normalized_notes=normalized_notes,
            handoff_basis_hash=handoff_hash,
        )
        db.commit()
        db.info.pop("b1b_promotion_identity_lock", None)
        return response
    except ConnectorPromotionError:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise
    except (DBAPIError, OSError, UnicodeError, PromotionIdentityError) as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise _closed_b1b_error("connector_promotion_bridge_unavailable") from exc
    except Exception:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise


def _verify_materialized_replay(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    intake: L3ConnectorSourceIntakeRecord,
    target: ConnectorRunTarget,
    basis_hash: str,
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    if (
        receipt.materialization_status != "materialized"
        or receipt.materialization_basis_hash != basis_hash
        or not receipt.dataset_id
        or not receipt.dataset_version_id
        or not receipt.promoted_session_id
        or receipt.materialized_at is None
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    dataset = db.get(Dataset, receipt.dataset_id)
    version = db.get(DatasetVersion, receipt.dataset_version_id)
    promoted = db.get(L3Session, receipt.promoted_session_id)
    if dataset is None or version is None or promoted is None:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    if (
        (target.dataset_id, target.dataset_version_id)
        != (dataset.dataset_id, version.dataset_version_id)
        or version.dataset_id != dataset.dataset_id
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    source = db.get(SourceConnector, dataset.source_id) if dataset.source_id else None
    variables = (
        db.query(VariableDefinition)
        .filter(VariableDefinition.dataset_version_id == version.dataset_version_id)
        .order_by(VariableDefinition.ordinal_position)
        .all()
    )
    profile = json.loads(METADATA_CONTRACT_CANONICAL_JSON)
    if (
        source is None
        or not _model_matches_profile(source, profile["source_connector"])
        or not _model_matches_profile(dataset, profile["dataset"])
        or not _model_matches_profile(
            version,
            profile["dataset_version"],
            excluded=frozenset({"storage_ref_policy"}),
        )
        or len(variables) != len(profile["variables"])
        or any(
            not _model_matches_profile(variable, expected)
            for variable, expected in zip(variables, profile["variables"], strict=True)
        )
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    try:
        final_path, output_relative_ref = _resolve_regular_reference(
            str(version.storage_ref or ""),
            settings.dataset_storage_dir,
        )
    except PromotionIdentityError as exc:
        raise _closed_b1b_error("connector_materialization_basis_conflict") from exc
    if final_path != paths["final"].resolve() or version.content_hash != F07_CONTENT_SHA256:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    file_bytes, file_sha256 = _file_facts(final_path)
    provenance_rows = (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == version.dataset_version_id)
        .all()
    )
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == promoted.session_id)
        .all()
    )
    events = (
        db.query(L3RetrievalEvent)
        .filter(L3RetrievalEvent.session_id == promoted.session_id)
        .all()
    )
    descriptors = (
        db.query(L3Descriptor)
        .filter(L3Descriptor.session_id == promoted.session_id)
        .all()
    )
    manifest = db.get(L3SelectionManifest, promoted.selection_manifest_id)
    if (
        len(provenance_rows) != 1
        or len(snapshots) != 1
        or len(events) != 1
        or len(descriptors) != 1
        or manifest is None
        or promoted.status != "completed_with_warnings"
        or promoted.completed_at is None
        or promoted.entry_route_context_json != {}
        or not _materialized_replay_summary_is_valid(
            db,
            receipt=receipt,
            promoted=promoted,
        )
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    provenance = provenance_rows[0]
    snapshot = snapshots[0]
    event = events[0]
    descriptor = descriptors[0]
    expected_manifest_item = _materialization_manifest_item(
        dataset_version_id=version.dataset_version_id,
        receipt_id=receipt.connector_promotion_receipt_id,
        basis_hash=basis_hash,
    )
    try:
        snapshot_path, _snapshot_relative_ref = _resolve_regular_reference(
            snapshot.payload_ref,
            str(paths["artifact_final_root"]),
        )
        snapshot_bytes = snapshot_path.read_bytes()
    except (OSError, PromotionIdentityError) as exc:
        raise _closed_b1b_error("connector_materialization_basis_conflict") from exc
    expected_snapshot_path = (
        paths["artifact_final_root"]
        / basis_hash[:2]
        / basis_hash
        / promoted.session_id
        / f"{snapshot.payload_hash}.json"
    ).resolve()
    expected_event_payload = {
        "loaded_items": [
            {
                "material_snapshot_id": snapshot.material_snapshot_id,
                "source_plane": snapshot.source_plane,
                "source_shape": snapshot.source_shape,
                "payload_ref": snapshot.payload_ref,
                "payload_hash": snapshot.payload_hash,
            }
        ],
        "failed_items": [],
        "why": "connector_promotion_materialized_dataset_version",
    }
    if (
        snapshot_path != expected_snapshot_path
        or hashlib.sha256(snapshot_bytes).hexdigest() != snapshot.payload_hash
        or json.loads(snapshot_bytes) != {"dataset_version_id": version.dataset_version_id}
        or snapshot.descriptor_id != descriptor.descriptor_id
        or snapshot.source_plane != "dataset"
        or snapshot.source_shape != "dataset_version"
        or snapshot.load_summary_json
        != {"loaded_records": 2, "failed_records": 0, "variable_count": 2}
        or event.descriptor_id != descriptor.descriptor_id
        or event.outcome != "loaded"
        or event.reason_code != "connector_promotion_materialized_dataset_version"
        or event.material_snapshot_ids_json != [snapshot.material_snapshot_id]
        or event.event_payload_json != expected_event_payload
        or manifest.session_id != promoted.session_id
        or manifest.manifest_json != {"items": [expected_manifest_item]}
        or manifest.source_plane_hints_json != {"dataset": 1}
        or manifest.commit_reason != "connector_promotion_materialization"
        or descriptor.selection_manifest_id != manifest.selection_manifest_id
        or descriptor.source_plane != "dataset"
        or descriptor.descriptor_type != "dataset_version"
        or descriptor.selector_payload_json != expected_manifest_item["selector_payload"]
        or descriptor.selection_basis_json != expected_manifest_item["selection_basis"]
        or descriptor.expansion_reason != "connector_promotion_materialization"
        or descriptor.status != "resolved_loaded"
        or snapshot.source_identity_json
        != {
            "schema_id": "layer3.dataset_version_source_identity.v1",
            "source_class": "dataset_version",
            "dataset_version_id": version.dataset_version_id,
            "dataset_id": dataset.dataset_id,
            "dataset_name": dataset.name,
            "version_label": version.version_label,
            "version_type": version.version_type,
            "status": version.status,
        }
        or snapshot.source_provenance_json
        != {
            "schema_id": "layer3.connector_promotion_dataset_source_provenance.v1",
            "connector_promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "materialization_basis_hash": basis_hash,
        }
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    if (
        not _model_matches_profile(
            provenance,
            profile["dataset_source_provenance"],
            excluded=frozenset({"raw_storage_ref_policy", "source_reference_json_policy"}),
        )
        or provenance.connector_run_id != intake.connector_run_id
        or provenance.raw_storage_ref != intake.storage_ref
    ):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    if list(provenance.source_reference_json) != [MATERIALIZATION_CONTEXT_KEY]:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    wrapper = provenance.source_reference_json[MATERIALIZATION_CONTEXT_KEY]
    if promoted.operator_context_json != {MATERIALIZATION_CONTEXT_KEY: wrapper}:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    if not isinstance(wrapper, dict) or set(wrapper) != {"record", "record_hash"}:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    record = wrapper.get("record")
    if not isinstance(record, dict) or materialization_record_hash(record) != wrapper.get("record_hash"):
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    expected_output = {
        "dataset_file_bytes": file_bytes,
        "dataset_file_sha256": file_sha256,
        "dataset_id": dataset.dataset_id,
        "dataset_source_provenance_id": provenance.dataset_source_provenance_id,
        "dataset_storage_ref_hash": dataset_storage_ref_hash(output_relative_ref),
        "dataset_version_content_sha256": version.content_hash,
        "dataset_version_id": version.dataset_version_id,
        "dropped_row_count": 0,
        "promoted_session_id": promoted.session_id,
        "row_count": 2,
        "source_connector_id": source.source_id,
        "source_row_count": 2,
        "variable_count": 2,
    }
    if record != {
        "basis_hash": basis_hash,
        "output": expected_output,
        "schema_id": MATERIALIZATION_RECORD_SCHEMA_ID,
    }:
        raise _closed_b1b_error("connector_materialization_basis_conflict")
    response = _materialization_response(
        receipt,
        disposition="reused",
        record_hash=wrapper["record_hash"],
    )
    _contain_unreferenced_lane_files(
        db,
        paths=paths,
        authoritative_final=final_path,
    )
    db.rollback()
    db.info.pop("b1b_promotion_identity_lock", None)
    return response


def _stage_profile_rows(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    intake: L3ConnectorSourceIntakeRecord,
    target: ConnectorRunTarget,
    frame,
    basis_hash: str,
    final_path: Path,
    artifact_stage_root: Path,
) -> tuple[
    SourceConnector,
    Dataset,
    DatasetVersion,
    DatasetSourceProvenance,
    L3Session,
    L3RetrievalEvent,
    L3MaterialSnapshot,
]:
    profile = json.loads(METADATA_CONTRACT_CANONICAL_JSON)
    source_profile = profile["source_connector"]
    source = SourceConnector(**source_profile)
    db.add(source)
    db.flush()
    dataset = Dataset(source_id=source.source_id, **profile["dataset"])
    db.add(dataset)
    db.flush()
    version_profile = profile["dataset_version"]
    version = DatasetVersion(
        dataset_id=dataset.dataset_id,
        parent_version_id=version_profile["parent_version_id"],
        version_label=version_profile["version_label"],
        version_type=version_profile["version_type"],
        status=version_profile["status"],
        storage_ref=str(final_path.resolve()),
        row_count=version_profile["row_count"],
        content_hash=version_profile["content_hash"],
        source_row_count=version_profile["source_row_count"],
        dropped_row_count=version_profile["dropped_row_count"],
        notes=version_profile["notes"],
    )
    db.add(version)
    db.flush()
    for variable_profile in profile["variables"]:
        db.add(VariableDefinition(dataset_version_id=version.dataset_version_id, **variable_profile))
    provenance_profile = profile["dataset_source_provenance"]
    provenance = DatasetSourceProvenance(
        dataset_version_id=version.dataset_version_id,
        connector_run_id=intake.connector_run_id,
        source_system=provenance_profile["source_system"],
        source_mode=provenance_profile["source_mode"],
        source_artifact_key=provenance_profile["source_artifact_key"],
        sciencebase_item_id=provenance_profile["sciencebase_item_id"],
        sciencebase_item_url=provenance_profile["sciencebase_item_url"],
        sciencebase_file_name=provenance_profile["sciencebase_file_name"],
        sciencebase_download_uri=provenance_profile["sciencebase_download_uri"],
        artifact_surface=provenance_profile["artifact_surface"],
        artifact_locator_type=provenance_profile["artifact_locator_type"],
        remote_checksum_type=provenance_profile["remote_checksum_type"],
        remote_checksum_value=provenance_profile["remote_checksum_value"],
        downloaded_sha256=provenance_profile["downloaded_sha256"],
        raw_storage_ref=intake.storage_ref,
        source_query_fingerprint=provenance_profile["source_query_fingerprint"],
        source_reference_json={},
        fetch_policy_mode=provenance_profile["fetch_policy_mode"],
        resolved_ip=provenance_profile["resolved_ip"],
        redirect_count=provenance_profile["redirect_count"],
        blocked_reason=provenance_profile["blocked_reason"],
        etag=provenance_profile["etag"],
        last_modified=provenance_profile["last_modified"],
        retrieved_http_json=provenance_profile["retrieved_http_json"],
        discovered_at=provenance_profile["discovered_at"],
        downloaded_at=provenance_profile["downloaded_at"],
    )
    db.add(provenance)
    manifest_item = _materialization_manifest_item(
        dataset_version_id=version.dataset_version_id,
        receipt_id=receipt.connector_promotion_receipt_id,
        basis_hash=basis_hash,
    )
    promoted, manifest = commit_selection(
        db,
        SessionEntryRequest(
            manifest_items=[manifest_item],
            source_plane_hints={"dataset": 1},
            commit_reason="connector_promotion_materialization",
        ),
    )
    descriptors = expand_descriptors(db, session=promoted, manifest=manifest)
    source_identity = {
        "schema_id": "layer3.dataset_version_source_identity.v1",
        "source_class": "dataset_version",
        "dataset_version_id": version.dataset_version_id,
        "dataset_id": dataset.dataset_id,
        "dataset_name": dataset.name,
        "version_label": version.version_label,
        "version_type": version.version_type,
        "status": version.status,
    }
    event, snapshots = record_retrieval_event(
        db,
        session=promoted,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="connector_promotion_materialized_dataset_version",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity=source_identity,
                source_provenance={
                    "schema_id": "layer3.connector_promotion_dataset_source_provenance.v1",
                    "connector_promotion_receipt_id": receipt.connector_promotion_receipt_id,
                    "materialization_basis_hash": basis_hash,
                },
                payload={"dataset_version_id": version.dataset_version_id},
                load_summary={
                    "loaded_records": int(len(frame)),
                    "failed_records": 0,
                    "variable_count": 2,
                },
            )
        ],
        storage_root=artifact_stage_root,
    )
    finalize_session(db, session=promoted)
    promoted.status = "completed_with_warnings"
    promoted.summary_json = {
        **promoted.summary_json,
        "warning_reasons": ["synthetic_non_official_fixture"],
    }
    return source, dataset, version, provenance, promoted, event, snapshots[0]


def _commit_materialization(db: OrmSession) -> None:
    """Commit seam used only to test acknowledged and ambiguous outcomes."""
    db.commit()


def _best_effort_rollback(db: OrmSession) -> None:
    """Never let a broken original connection mask independent reconciliation."""
    try:
        db.rollback()
    except Exception:
        pass


def _before_failed_materialization_containment() -> None:
    """Fault/barrier seam entered only while the fresh I1 lock is held."""


def _reconcile_failed_materialization(
    engine,
    *,
    receipt_id: str,
    target_id: str,
    paths: Mapping[str, Path],
    expectation: Mapping[str, Any] | None,
) -> str:
    with OrmSession(bind=engine, expire_on_commit=False) as verify_db:
        acquire_promotion_identity_lock(verify_db, F07_CANONICAL_IDENTITY_KEY_HASH)
        receipt = verify_db.get(L3ConnectorPromotionReceipt, receipt_id)
        target = verify_db.get(ConnectorRunTarget, target_id)
        if receipt is None or target is None:
            return "uncertain"
        if expectation is not None:
            dataset_id = expectation["dataset_id"]
            dataset_version_id = expectation["dataset_version_id"]
            promoted_session_id = expectation["promoted_session_id"]
            final_path = expectation["final_path"]
            snapshot_path = expectation["snapshot_path"]
            committed = (
                receipt.materialization_status == "materialized"
                and receipt.materialization_basis_hash == expectation["basis_hash"]
                and receipt.dataset_id == dataset_id
                and receipt.dataset_version_id == dataset_version_id
                and receipt.promoted_session_id == promoted_session_id
                and receipt.materialized_at is not None
                and (target.dataset_id, target.dataset_version_id)
                == (dataset_id, dataset_version_id)
            )
        else:
            committed = False
        if committed and expectation is not None:
            _require_nonreparse_components(final_path)
            _require_nonreparse_components(snapshot_path)
            version = verify_db.get(DatasetVersion, dataset_version_id)
            snapshots = (
                verify_db.query(L3MaterialSnapshot)
                .filter(L3MaterialSnapshot.session_id == promoted_session_id)
                .all()
            )
            if (
                version is not None
                and Path(version.storage_ref).resolve() == final_path.resolve()
                and len(snapshots) == 1
                and Path(snapshots[0].payload_ref).resolve() == snapshot_path.resolve()
                and _file_facts(final_path)
                == (expectation["final_bytes"], expectation["final_sha256"])
                and _file_facts(snapshot_path)
                == (expectation["snapshot_bytes"], expectation["snapshot_sha256"])
                and not _is_reparse(final_path)
                and not _is_reparse(snapshot_path)
            ):
                return "committed"
            return "uncertain"
        absent = (
            receipt.materialization_status is None
            and receipt.materialization_basis_hash is None
            and receipt.dataset_id is None
            and receipt.dataset_version_id is None
            and receipt.promoted_session_id is None
            and receipt.materialized_at is None
            and target.dataset_id is None
            and target.dataset_version_id is None
        )
        if absent and expectation is not None:
            absent = (
                verify_db.get(Dataset, dataset_id) is None
                and verify_db.get(DatasetVersion, dataset_version_id) is None
                and verify_db.get(L3Session, promoted_session_id) is None
            )
        if absent:
            _before_failed_materialization_containment()
            _contain_unreferenced_lane_files(verify_db, paths=paths)
            return "absent"
        return "uncertain"


def _materialize_locked_receipt(
    db: OrmSession,
    *,
    receipt: L3ConnectorPromotionReceipt,
    intake: L3ConnectorSourceIntakeRecord,
    target: ConnectorRunTarget,
    frame,
    basis_hash: str,
    input_relative_ref: str,
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    bind = db.get_bind()
    reconciliation_engine = getattr(bind, "engine", bind)
    stage_path = paths["stage_root"] / f"{basis_hash}-{uuid.uuid4().hex}.parquet"
    snapshot_stage: Path | None = None
    snapshot_final: Path | None = None
    commit_expectation: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    try:
        directory_bindings = (
            (paths["dataset_root"], paths["dataset_root"]),
            (paths["stage_root"], paths["dataset_root"]),
            (paths["dataset_final_root"], paths["dataset_root"]),
            (paths["final"].parent, paths["dataset_root"]),
            (paths["dataset_containment"], paths["dataset_root"]),
            (paths["artifact_custody_root"], paths["artifact_custody_root"]),
            (paths["artifact_root"], paths["artifact_custody_root"]),
            (paths["artifact_stage_root"], paths["artifact_custody_root"]),
            (paths["artifact_final_root"], paths["artifact_custody_root"]),
            (paths["artifact_containment"], paths["artifact_custody_root"]),
        )
        for directory, custody_root in directory_bindings:
            _ensure_nonreparse_lane_directory(directory, custody_root)
        _contain_unreferenced_lane_files(db, paths=paths)
        if paths["final"].exists() or stage_path.exists():
            raise _closed_b1b_error("connector_materialization_basis_conflict")
        write_dataframe_to_absent_parquet(frame, stage_path)
        stage_bytes, stage_sha256 = _file_facts(stage_path)
        artifact_stage_basis_root = (
            paths["artifact_stage_root"] / basis_hash[:2] / basis_hash
        )
        _ensure_nonreparse_lane_directory(
            artifact_stage_basis_root,
            paths["artifact_custody_root"],
        )
        source, dataset, version, provenance, promoted, event, snapshot = _stage_profile_rows(
            db,
            receipt=receipt,
            intake=intake,
            target=target,
            frame=frame,
            basis_hash=basis_hash,
            final_path=paths["final"],
            artifact_stage_root=artifact_stage_basis_root,
        )
        snapshot_stage, _snapshot_stage_ref = _resolve_regular_reference(
            snapshot.payload_ref,
            str(paths["artifact_stage_root"]),
        )
        with snapshot_stage.open("rb+") as handle:
            os.fsync(handle.fileno())
        snapshot_stage_bytes, snapshot_stage_sha256 = _file_facts(snapshot_stage)
        if snapshot_stage_sha256 != snapshot.payload_hash:
            raise PromotionIdentityError("staged snapshot payload hash mismatch")
        snapshot_final = (
            paths["artifact_final_root"]
            / basis_hash[:2]
            / basis_hash
            / promoted.session_id
            / snapshot_stage.name
        )
        receipt.materialization_status = "materializing"
        receipt.materialization_basis_hash = basis_hash
        db.flush()
        _before_materialization_publish()
        if paths["final"].exists():
            raise _closed_b1b_error("connector_materialization_basis_conflict")
        _atomic_rename_no_overwrite(stage_path, paths["final"])
        _after_materialization_publish()
        _ensure_nonreparse_lane_directory(snapshot_final.parent, paths["artifact_custody_root"])
        _atomic_rename_no_overwrite(snapshot_stage, snapshot_final)
        snapshot_final, _snapshot_final_ref = _resolve_regular_reference(
            str(snapshot_final),
            str(paths["artifact_final_root"]),
        )
        snapshot_final_bytes, snapshot_final_sha256 = _file_facts(snapshot_final)
        if (snapshot_final_bytes, snapshot_final_sha256) != (
            snapshot_stage_bytes,
            snapshot_stage_sha256,
        ):
            raise PromotionIdentityError("published snapshot differs from verified stage")
        snapshot.payload_ref = str(snapshot_final)
        event_payload = json.loads(json.dumps(event.event_payload_json))
        loaded_items = event_payload.get("loaded_items")
        if (
            not isinstance(loaded_items, list)
            or len(loaded_items) != 1
            or loaded_items[0].get("material_snapshot_id") != snapshot.material_snapshot_id
            or loaded_items[0].get("payload_hash") != snapshot.payload_hash
        ):
            raise PromotionIdentityError("snapshot retrieval event linkage is invalid")
        loaded_items[0]["payload_ref"] = snapshot.payload_ref
        event.event_payload_json = event_payload

        input_path_check, input_relative_check = _resolve_regular_reference(
            intake.storage_ref,
            settings.storage_dir,
        )
        if input_relative_check != input_relative_ref:
            raise PromotionIdentityError("input storage reference changed during materialization")
        _validated_existing_f07_frame(input_path_check)
        final_path_check, output_relative_ref = _resolve_regular_reference(
            str(paths["final"]),
            settings.dataset_storage_dir,
        )
        final_bytes, final_sha256 = _file_facts(final_path_check)
        if (final_bytes, final_sha256) != (stage_bytes, stage_sha256):
            raise PromotionIdentityError("published Parquet differs from verified stage")
        record = build_materialization_record(
            basis_hash=basis_hash,
            dataset_file_bytes=final_bytes,
            dataset_file_sha256=final_sha256,
            dataset_id=dataset.dataset_id,
            dataset_source_provenance_id=provenance.dataset_source_provenance_id,
            dataset_storage_ref_hash=dataset_storage_ref_hash(output_relative_ref),
            dataset_version_content_sha256=version.content_hash,
            dataset_version_id=version.dataset_version_id,
            promoted_session_id=promoted.session_id,
            source_connector_id=source.source_id,
        )
        wrapper = build_materialization_wrapper(record)
        provenance.source_reference_json = {MATERIALIZATION_CONTEXT_KEY: wrapper}
        promoted.operator_context_json = {MATERIALIZATION_CONTEXT_KEY: wrapper}
        if (
            dataset.source_id != source.source_id
            or version.dataset_id != dataset.dataset_id
            or provenance.dataset_version_id != version.dataset_version_id
            or provenance.connector_run_id != intake.connector_run_id
            or target.connector_run_id != intake.connector_run_id
        ):
            raise PromotionIdentityError("materialization foreign-key equality check failed")
        target.dataset_id = dataset.dataset_id
        target.dataset_version_id = version.dataset_version_id
        receipt.dataset_id = dataset.dataset_id
        receipt.dataset_version_id = version.dataset_version_id
        receipt.promoted_session_id = promoted.session_id
        receipt.materialization_status = "materialized"
        receipt.materialized_at = datetime.now(timezone.utc)
        materialize_typing_entry(db, session_id=promoted.session_id)
        response = _materialization_response(
            receipt,
            disposition="materialized",
            record_hash=wrapper["record_hash"],
        )
        commit_expectation = {
            "basis_hash": basis_hash,
            "dataset_id": dataset.dataset_id,
            "dataset_version_id": version.dataset_version_id,
            "promoted_session_id": promoted.session_id,
            "final_path": paths["final"],
            "final_bytes": final_bytes,
            "final_sha256": final_sha256,
            "snapshot_path": snapshot_final,
            "snapshot_bytes": snapshot_final_bytes,
            "snapshot_sha256": snapshot_final_sha256,
        }
        _commit_materialization(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        return response
    except Exception as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        try:
            outcome = _reconcile_failed_materialization(
                reconciliation_engine,
                receipt_id=receipt.connector_promotion_receipt_id,
                target_id=target.connector_run_target_id,
                paths=paths,
                expectation=commit_expectation,
            )
        except Exception as reconciliation_error:
            raise _closed_b1b_error("connector_materialization_basis_conflict") from reconciliation_error
        if outcome == "committed" and response is not None:
            return response
        if outcome != "absent":
            raise _closed_b1b_error("connector_materialization_basis_conflict") from exc
        raise


def resolve_connector_promotion(
    db: OrmSession,
    *,
    gate_b_session_id: str,
) -> dict[str, Any]:
    """Materialize or exactly replay the receipt selected by one Gate-B session."""
    try:
        uuid.UUID(_clean_required_string(gate_b_session_id, "gate_b_session_id"))
    except (ValueError, AttributeError, PromotionIdentityError, TypeError) as exc:
        raise _closed_b1b_error("connector_promotion_session_not_found") from exc
    try:
        acquire_promotion_identity_lock(db, F07_CANONICAL_IDENTITY_KEY_HASH)
        session = db.get(L3Session, gate_b_session_id)
        if session is None:
            raise _closed_b1b_error("connector_promotion_session_not_found")
        try:
            receipt = (
                db.query(L3ConnectorPromotionReceipt)
                .filter(L3ConnectorPromotionReceipt.gate_b_session_id == gate_b_session_id)
                .one_or_none()
            )
        except MultipleResultsFound as exc:
            raise _basis_conflict() from exc
        if receipt is None:
            raise _not_eligible()
        verify_existing_receipt_basis(db, receipt)
        intake = db.get(L3ConnectorSourceIntakeRecord, receipt.connector_source_intake_record_id)
        if intake is None:
            raise _basis_conflict()
        run = db.get(ConnectorRun, intake.connector_run_id)
        target = db.get(ConnectorRunTarget, intake.connector_run_target_id)
        if not _server_exact_shape(intake, run, target) or target is None:
            raise _not_eligible()
        try:
            code_identity = _read_clean_materialization_code_identity()
            raw_path, input_relative_ref = _resolve_regular_reference(
                intake.storage_ref,
                settings.storage_dir,
            )
            frame = _validated_existing_f07_frame(raw_path)
            _basis, basis_hash = _build_resolver_basis(
                receipt=receipt,
                intake=intake,
                target=target,
                input_relative_ref=input_relative_ref,
                code_identity=code_identity,
            )
        except PromotionIdentityError as exc:
            raise _closed_b1b_error("connector_materialization_basis_conflict") from exc
        paths = _lane_paths(basis_hash)
        if receipt.materialization_status == "materialized":
            return _verify_materialized_replay(
                db,
                receipt=receipt,
                intake=intake,
                target=target,
                basis_hash=basis_hash,
                paths=paths,
            )
        if (
            receipt.materialization_status is not None
            or receipt.materialization_basis_hash is not None
            or receipt.dataset_id is not None
            or receipt.dataset_version_id is not None
            or receipt.promoted_session_id is not None
            or receipt.materialized_at is not None
            or target.dataset_id is not None
            or target.dataset_version_id is not None
        ):
            raise _closed_b1b_error("connector_materialization_basis_conflict")
        return _materialize_locked_receipt(
            db,
            receipt=receipt,
            intake=intake,
            target=target,
            frame=frame,
            basis_hash=basis_hash,
            input_relative_ref=input_relative_ref,
            paths=paths,
        )
    except ConnectorPromotionError:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise
    except Exception as exc:
        _best_effort_rollback(db)
        db.info.pop("b1b_promotion_identity_lock", None)
        raise _closed_b1b_error("connector_materialization_basis_conflict") from exc
