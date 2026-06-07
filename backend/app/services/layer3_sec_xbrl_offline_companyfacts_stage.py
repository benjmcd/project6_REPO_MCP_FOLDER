from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_offline_companyfacts_stage.v1"
COMPANYFACTS_RECEIPT_PREFIX = "sec-edgar-companyfacts-live-artifact"
COMPANYFACTS_RECEIPT_DIR = "layer3-sec-xbrl-companyfacts"
CONNECTOR_RECEIPT_DIR = "layer3-sec-edgar-real-filing-acquisition-connector"

# Path-traversal guard: receipts ids are server-generated and must match this pattern exactly.
# Format: sec-edgar-companyfacts-live-artifact-<24 hex chars>-<24 hex chars>
_COMPANYFACTS_RECEIPT_ID_RE = re.compile(
    r"^sec-edgar-companyfacts-live-artifact-[a-f0-9]{24}-[a-f0-9]{24}$"
)


class SecXbrlCompanyfactsStageError(ValueError):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})


def stage_sec_xbrl_companyfacts(
    *,
    companyfacts: Mapping[str, Any],
    cik: str,
    connector_receipt_hash: str,
    content_sha256: str,
    storage_dir: Any,
) -> dict[str, Any]:
    """Write a CompanyFacts artifact to the gitignored raw store and a redacted receipt.

    The redacted receipt contains ONLY hashes + counts — never raw CIK, values, accession,
    or issuer name.  The raw JSON is written to the gitignored companyfacts-store path.

    Issuer binding: verifies sha256(cik) is present among the connector receipt's example
    cik_hash values so a wrong-issuer oracle cannot be staged against a connector.

    Idempotency: uses atomic open('x'); same content → replay (no error); different content
    for same cik_hash → conflict error.
    """
    storage = Path(storage_dir)

    # --- Validate inputs ---
    raw_cik = str(cik or "").strip().lstrip("0") or "0"
    cik_hash = hashlib.sha256(raw_cik.encode("utf-8")).hexdigest()

    connector_receipt_hash = str(connector_receipt_hash or "").strip()
    if not connector_receipt_hash or len(connector_receipt_hash) != 64:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_connector_receipt_hash_invalid",
            "connector_receipt_hash must be a 64-character hex string.",
        )

    content_sha256 = str(content_sha256 or "").strip()
    if not content_sha256 or len(content_sha256) != 64:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_content_sha256_invalid",
            "content_sha256 must be a 64-character hex string.",
        )

    if not isinstance(companyfacts, Mapping):
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_payload_invalid",
            "companyfacts must be a mapping (facts dict).",
        )

    # --- Issuer binding: assert cik_hash in connector receipt ---
    connector_receipt = _read_connector_receipt_by_hash(storage, connector_receipt_hash)
    if connector_receipt is None:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_connector_receipt_missing",
            "The connector receipt for the supplied connector_receipt_hash was not found in storage.",
            details={"connector_receipt_hash": connector_receipt_hash},
        )

    example_cik_hashes = _extract_connector_cik_hashes(connector_receipt)
    if cik_hash not in example_cik_hashes:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_cik_not_in_connector",
            "The CIK hash for this companyfacts is not present among the connector receipt's examples.",
            details={"cik_hash": cik_hash},
        )

    # --- Count observations for the receipt ---
    taxonomy_count, concept_count, observation_count = _count_companyfacts(companyfacts)

    # --- Compute receipt id ---
    source_identity_hash = stable_hash(
        {"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash}
    )
    companyfacts_payload_hash = stable_hash(dict(companyfacts))
    receipt_hash_basis = {
        "hash_version": "sec_xbrl_offline_companyfacts_stage_receipt_hash_v1",
        "schema_id": SCHEMA_ID,
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "connector_receipt_hash": connector_receipt_hash,
        "companyfacts_payload_hash": companyfacts_payload_hash,
        "content_sha256": content_sha256,
    }
    receipt_hash = stable_hash(receipt_hash_basis)
    companyfacts_receipt_id = f"{COMPANYFACTS_RECEIPT_PREFIX}-{source_identity_hash[:24]}-{receipt_hash[:24]}"

    # --- Raw store (gitignored) ---
    raw_store_path = storage / COMPANYFACTS_RECEIPT_DIR / "companyfacts-store" / f"{companyfacts_receipt_id}.json"
    receipt_path = storage / COMPANYFACTS_RECEIPT_DIR / "receipts" / f"{companyfacts_receipt_id}.json"

    # --- Idempotency / conflict check ---
    # Scan all existing receipts for this cik_hash to detect cross-content conflicts.
    # A different content_sha256 for the same cik_hash is a conflict regardless of receipt_id.
    receipts_dir = storage / COMPANYFACTS_RECEIPT_DIR / "receipts"
    if receipts_dir.exists():
        for existing_path in sorted(receipts_dir.glob(f"{COMPANYFACTS_RECEIPT_PREFIX}-*.json")):
            try:
                existing_receipt = _read_json_object(existing_path)
            except (OSError, SecXbrlCompanyfactsStageError):
                continue
            if existing_receipt.get("cik_hash") != cik_hash:
                continue
            if existing_receipt.get("content_sha256") != content_sha256:
                raise SecXbrlCompanyfactsStageError(
                    "sec_xbrl_companyfacts_stage_conflict",
                    "A different companyfacts payload already exists for this cik_hash; content_sha256 mismatch.",
                    details={"cik_hash": cik_hash},
                )
            # Same cik_hash + same content_sha256 → idempotent replay
            return _build_stage_response(existing_receipt, idempotent_replay=True)

    # --- Write raw store (gitignored) ---
    raw_store_path.parent.mkdir(parents=True, exist_ok=True)
    raw_payload = dict(companyfacts)
    try:
        with raw_store_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(raw_payload, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        pass  # concurrent write of same id — both carry same content by construction

    # --- Write redacted receipt (never contains raw CIK/values/accession/issuer) ---
    receipt = {
        "schema_id": SCHEMA_ID,
        "companyfacts_receipt_id": companyfacts_receipt_id,
        "companyfacts_receipt_hash": receipt_hash,
        "companyfacts_payload_hash": companyfacts_payload_hash,
        "cik_hash": cik_hash,
        "connector_receipt_hash": connector_receipt_hash,
        "companyfacts_observation_count": observation_count,
        "taxonomy_count": taxonomy_count,
        "concept_count": concept_count,
        "content_sha256": content_sha256,
        "recorded_at": _server_time(),
        "gitignored_local_storage": True,
        "operator_surface_exposure": False,
    }

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with receipt_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing_receipt = _read_json_object(receipt_path)
        if existing_receipt.get("content_sha256") != content_sha256:
            raise SecXbrlCompanyfactsStageError(
                "sec_xbrl_companyfacts_stage_conflict",
                "A different companyfacts payload already exists for this cik_hash; content_sha256 mismatch.",
                details={"cik_hash": cik_hash},
            )
        return _build_stage_response(existing_receipt, idempotent_replay=True)

    return _build_stage_response(receipt, idempotent_replay=False)


def find_staged_companyfacts_receipt(
    storage: Path,
    *,
    connector_receipt_hash: str,
    cik_hash: str,
) -> dict[str, Any] | None:
    """Locate a staged companyfacts receipt that matches connector_receipt_hash AND cik_hash."""
    receipts_dir = storage / COMPANYFACTS_RECEIPT_DIR / "receipts"
    if not receipts_dir.exists():
        return None
    for path in sorted(receipts_dir.glob(f"{COMPANYFACTS_RECEIPT_PREFIX}-*.json")):
        try:
            payload = _read_json_object(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if (
            payload.get("connector_receipt_hash") == connector_receipt_hash
            and payload.get("cik_hash") == cik_hash
        ):
            return payload
    return None


def load_staged_companyfacts_raw(
    storage: Path,
    *,
    companyfacts_receipt_id: str,
) -> dict[str, Any]:
    """Load the raw companyfacts JSON from the gitignored store by receipt id."""
    rid = str(companyfacts_receipt_id or "").strip()
    if not _COMPANYFACTS_RECEIPT_ID_RE.fullmatch(rid):
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_receipt_id_invalid",
            "companyfacts_receipt_id is not a valid server-issued receipt id.",
            details={"companyfacts_receipt_id": rid},
        )
    raw_path = storage / COMPANYFACTS_RECEIPT_DIR / "companyfacts-store" / f"{rid}.json"
    # Defense-in-depth: confirm the resolved path stays within the store.
    store_root = (storage / COMPANYFACTS_RECEIPT_DIR / "companyfacts-store").resolve()
    try:
        raw_path.resolve().relative_to(store_root)
    except ValueError:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_receipt_id_invalid",
            "companyfacts_receipt_id resolves outside the companyfacts store.",
            details={"companyfacts_receipt_id": rid},
        )
    return _read_json_object(raw_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_connector_receipt_by_hash(
    storage: Path,
    connector_receipt_hash: str,
) -> dict[str, Any] | None:
    receipts_dir = storage / CONNECTOR_RECEIPT_DIR / "receipts"
    if not receipts_dir.exists():
        return None
    for path in sorted(receipts_dir.glob("*.json")):
        try:
            payload = _read_json_object(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if payload.get("connector_receipt_hash") == connector_receipt_hash:
            return payload
    return None


def _extract_connector_cik_hashes(connector_receipt: Mapping[str, Any]) -> set[str]:
    """Extract all cik_hash values from the connector receipt's corpus manifest examples."""
    hashes: set[str] = set()
    corpus_manifest = connector_receipt.get("corpus_manifest")
    if not isinstance(corpus_manifest, Mapping):
        return hashes
    for example in corpus_manifest.get("example_records") or []:
        if isinstance(example, Mapping) and example.get("cik_hash"):
            hashes.add(str(example["cik_hash"]))
    return hashes


def _count_companyfacts(facts: Mapping[str, Any]) -> tuple[int, int, int]:
    """Return (taxonomy_count, concept_count, observation_count)."""
    taxonomy_count = concept_count = observation_count = 0
    for concepts in facts.values():
        if not isinstance(concepts, Mapping):
            continue
        taxonomy_count += 1
        for concept in concepts.values():
            if not isinstance(concept, Mapping):
                continue
            units = concept.get("units") if isinstance(concept.get("units"), Mapping) else {}
            concept_count += 1
            for observations in units.values():
                if isinstance(observations, list):
                    observation_count += len(observations)
    return taxonomy_count, concept_count, observation_count


def _build_stage_response(receipt: Mapping[str, Any], *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "staged",
        "companyfacts_receipt_id": receipt["companyfacts_receipt_id"],
        "companyfacts_receipt_hash": receipt["companyfacts_receipt_hash"],
        "companyfacts_payload_hash": receipt["companyfacts_payload_hash"],
        "cik_hash": receipt["cik_hash"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "companyfacts_observation_count": receipt["companyfacts_observation_count"],
        "taxonomy_count": receipt["taxonomy_count"],
        "concept_count": receipt["concept_count"],
        "content_sha256": receipt["content_sha256"],
        "gitignored_local_storage": True,
        "operator_surface_exposure": False,
        "idempotent_replay": idempotent_replay,
        "raw_cik_exposed": False,
        "raw_values_exposed": False,
        "raw_accession_exposed": False,
        "raw_issuer_name_exposed": False,
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_json_missing",
            f"Required JSON file is missing: {path.name}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_json_invalid",
            "Required JSON file is invalid.",
        ) from exc
    if not isinstance(payload, dict):
        raise SecXbrlCompanyfactsStageError(
            "sec_xbrl_companyfacts_stage_json_not_object",
            "Required JSON file must contain an object.",
        )
    return payload


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()
