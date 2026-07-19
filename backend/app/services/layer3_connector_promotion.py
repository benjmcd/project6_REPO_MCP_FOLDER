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
import hashlib
import io
import json
import math
from pathlib import Path
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
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3Descriptor,
    L3GateBIdempotencyKey,
    L3MaterialSnapshot,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
)
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


def attestation_precondition_available(_candidate: GateBPromotionCandidate) -> bool:
    """Step-3 seam. Full Section-8 attestation wiring is separately gated."""
    return False


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
