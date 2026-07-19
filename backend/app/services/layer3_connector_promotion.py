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

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import unicodedata
from typing import Any, Mapping
import uuid

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm.exc import MultipleResultsFound

from app.core.config import settings
from app.models.models import (
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3Descriptor,
    L3GateBIdempotencyKey,
    L3MaterialSnapshot,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
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


def _closed_b1b_error(error_code: str) -> ConnectorPromotionError:
    http_status, message, retryable = b1b_error_spec(error_code)
    return _promotion_error(
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
    if not root_input.exists() or not root_input.is_dir() or _is_reparse(root_input):
        raise PromotionIdentityError("storage root is invalid")
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
        or promoted.summary_json
        != {
            "descriptor_status_counts": {"resolved_loaded": 1},
            "retrieval_outcome_counts": {"loaded": 1},
            "loaded_snapshot_count": 1,
            "source_planes": ["dataset"],
            "warning_reasons": ["synthetic_non_official_fixture"],
            "retrieved_descriptor_count": 1,
            "unresolved_descriptor_count": 0,
            "descriptor_coverage_status": "complete",
        }
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
