"""B1b connector-promotion identity and digest primitives.

Pure, side-effect-free building blocks for the Option II promotion receipt
(owner-bound correction, Sections 3.1 / 4.1 / 4.2). Server-derived only:
no caller-supplied value is ever authoritative for any digest produced here.
The legacy Gate-B manifest hash (``layer3_gate_b_state.stable_hash``) is a
distinct, deliberately different serializer and is never replaced by these.

Everything here is inert while ``LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED``
is false; the module performs no I/O and mutates no state.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata

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
