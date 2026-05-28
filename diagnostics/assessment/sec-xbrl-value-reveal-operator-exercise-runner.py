from __future__ import annotations

import argparse
import hashlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-run-report.json")
SIDECAR_RECEIPT_DIR = "layer3-sec-edgar-arelle-resolved-fact-authority"
BRIDGE_RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
VALUE_REVEAL_RECEIPT_DIR = "layer3-sec-edgar-arelle-value-reveal"
READY_SIDECAR_STATE = "sec_edgar_arelle_resolved_fact_authority_sidecar_ready"
ARELLE_FACT_AUTHORITY_INPUT_MODE = "arelle_resolved_fact_authority_sidecar_receipt"
INTERNAL_VALUE_STORE_DIR = "internal-value-stores"
LINEAGE_KEYS = (
    "parser_receipt_hash",
    "connector_receipt_hash",
    "live_source_artifact_receipt_hash",
    "source_artifact_receipt_hash",
    "content_sha256",
    "primary_document_hash",
    "document_inventory_hash",
    "content_order_hash",
    "table_candidate_inventory_hash",
    "inline_xbrl_marker_inventory_hash",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL value-reveal operator-exercise runner. This fail-closed preflight "
            "uses the configured storage authority and does not fabricate sidecars or datasets."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    report = build_report(source_root=ROOT)
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(*, source_root: Path, storage_dir: Path | None = None, db: Any | None = None) -> dict[str, Any]:
    storage = storage_dir if storage_dir is not None else _configured_storage_dir(source_root)
    inventory = _inventory_storage(storage)
    with _runtime_db(source_root, db) as runtime_db:
        selection = _select_authority_bundle(storage, runtime_db)
    criteria = [
        _criterion(
            "configured_storage_available",
            inventory["storage_exists"],
            {
                "storage_marker": inventory["storage_marker"],
                "storage_exists": inventory["storage_exists"],
                "storage_file_count": inventory["storage_file_count"],
            },
            "value_reveal_operator_exercise_storage_unavailable",
        ),
        _criterion(
            "coherent_value_reveal_authority_bundle_available",
            bool(selection["ready"]),
            {
                "sidecar_receipt_count": inventory["sidecar_receipt_count"],
                "ready_sidecar_count": inventory["ready_sidecar_count"],
                "internal_value_store_file_count": inventory["internal_value_store_file_count"],
                "bridge_receipt_count": inventory["bridge_receipt_count"],
                "bridge_receipt_with_dataset_hash_count": inventory["bridge_receipt_with_dataset_hash_count"],
                "bridge_receipt_with_dataset_id_count": inventory["bridge_receipt_with_dataset_id_count"],
                "coherent_bundle_count": selection["coherent_bundle_count"],
                "selected_bundle_present": selection["selected_bundle"] is not None,
                "blocked_reason_codes": [item["blocked_reason"] for item in selection["blocking_reasons"]],
            },
            "value_reveal_operator_exercise_coherent_authority_bundle_missing",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    ready = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_value_reveal_operator_exercise_run.v1",
        "target": "sec_edgar_arelle_value_reveal_operator_exercise_v1",
        "decision": (
            "value_reveal_operator_exercise_ready_to_run"
            if ready
            else "value_reveal_operator_exercise_blocked_missing_authority"
        ),
        "headline": (
            "Configured storage has the persisted sidecar and bridge dataset authority required for an isolated operator exercise."
            if ready
            else "Operator exercise cannot run from current configured storage because persisted sidecar/dataset authority is missing."
        ),
        "operator_exercise_performed": False,
        "ready_to_run_operator_exercise": ready,
        "criteria": criteria,
        "blocking_reasons": blockers + list(selection["blocking_reasons"]),
        "redacted_inventory": inventory,
        "selected_authority_bundle": selection["selected_bundle"],
        "required_next_action": (
            "run_isolated_value_reveal_operator_exercise_against_existing_authorities"
            if ready
            else "provision_or_point_to_existing_real_filing_sidecar_and_dataset_authorities_then_rerun"
        ),
        "non_goals_preserved": {
            "cutover_default_enabled": False,
            "value_reveal_default_enabled": False,
            "sec_network_fetch_performed": False,
            "arelle_subprocess_invoked": False,
            "sidecar_receipt_created": False,
            "dataset_version_created": False,
            "audit_receipt_created": False,
            "raw_values_returned": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "next_slice": (
            "sec_edgar_arelle_value_reveal_operator_exercise_v1"
            if ready
            else "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1"
        ),
    }


def _inventory_storage(storage: Path) -> dict[str, Any]:
    exists = storage.exists()
    sidecar_receipts = _json_files(storage / SIDECAR_RECEIPT_DIR / "receipts")
    bridge_receipts = _json_files(storage / BRIDGE_RECEIPT_DIR / "receipts")
    internal_value_stores = _json_files(storage / SIDECAR_RECEIPT_DIR / "internal-value-stores")
    ready_sidecars = []
    ready_sidecars_with_values = []
    for receipt_path in sidecar_receipts:
        receipt = _read_json_or_none(receipt_path)
        if not isinstance(receipt, Mapping):
            continue
        if receipt.get("sidecar_state") != READY_SIDECAR_STATE:
            continue
        ready_sidecars.append(receipt)
        metadata = receipt.get("internal_value_store") if isinstance(receipt.get("internal_value_store"), Mapping) else {}
        if (
            metadata.get("store_state") == "persisted"
            and isinstance(metadata.get("value_store_hash"), str)
        ):
            ready_sidecars_with_values.append(receipt)
    bridge_with_dataset_hash = 0
    bridge_with_dataset_id = 0
    for receipt_path in bridge_receipts:
        receipt = _read_json_or_none(receipt_path)
        if not isinstance(receipt, Mapping):
            continue
        response = receipt.get("response") if isinstance(receipt.get("response"), Mapping) else receipt
        if isinstance(response.get("dataset_version_hash"), str):
            bridge_with_dataset_hash += 1
        if isinstance(response.get("dataset_version_id"), str):
            bridge_with_dataset_id += 1
    return {
        "storage_marker": _redacted_marker(storage),
        "storage_exists": exists,
        "storage_file_count": _file_count(storage) if exists else 0,
        "sidecar_receipt_count": len(sidecar_receipts),
        "ready_sidecar_count": len(ready_sidecars),
        "ready_sidecar_with_internal_value_store_count": len(ready_sidecars_with_values),
        "internal_value_store_file_count": len(internal_value_stores),
        "bridge_receipt_count": len(bridge_receipts),
        "bridge_receipt_with_dataset_hash_count": bridge_with_dataset_hash,
        "bridge_receipt_with_dataset_id_count": bridge_with_dataset_id,
        "value_reveal_receipt_count": len(_json_files(storage / VALUE_REVEAL_RECEIPT_DIR / "receipts")),
    }


def _select_authority_bundle(storage: Path, db: Any | None) -> dict[str, Any]:
    sidecars, sidecar_blockers = _ready_sidecars(storage)
    bridges, bridge_blockers = _bridge_responses(storage)
    blockers = list(sidecar_blockers) + list(bridge_blockers)
    if not sidecars:
        blockers.append(_blocked("value_reveal_operator_exercise_ready_sidecar_authority_missing"))
    coherent_bundles: list[dict[str, Any]] = []
    for sidecar in sidecars:
        store_result = _verified_value_store(storage, sidecar)
        if store_result["blocked_reason"] is not None:
            blockers.append(store_result["blocked_reason"])
            continue
        candidate_matches = [bridge for bridge in bridges if _bridge_matches_sidecar(bridge, sidecar)]
        if not candidate_matches:
            blockers.append(_blocked("value_reveal_operator_exercise_sidecar_bridge_lineage_mismatch"))
            continue
        for bridge in candidate_matches:
            dataset_result = _dataset_context(db, bridge["response"])
            if dataset_result["blocked_reason"] is not None:
                blockers.append(dataset_result["blocked_reason"])
                continue
            coherent_bundles.append(
                _redacted_bundle(
                    sidecar=sidecar,
                    bridge=bridge,
                    value_store_hash=store_result["value_store_hash"],
                    provenance_hash=dataset_result["provenance_hash"],
                )
            )
    if len(coherent_bundles) > 1:
        blockers.append(_blocked("value_reveal_operator_exercise_ambiguous_authority_bundle"))
        return {
            "ready": False,
            "coherent_bundle_count": len(coherent_bundles),
            "selected_bundle": None,
            "blocking_reasons": _dedupe_blockers(blockers),
        }
    if len(coherent_bundles) == 1:
        return {
            "ready": True,
            "coherent_bundle_count": 1,
            "selected_bundle": coherent_bundles[0],
            "blocking_reasons": [],
        }
    blockers.append(_blocked("value_reveal_operator_exercise_no_coherent_authority_bundle"))
    return {
        "ready": False,
        "coherent_bundle_count": 0,
        "selected_bundle": None,
        "blocking_reasons": _dedupe_blockers(blockers),
    }


def _ready_sidecars(storage: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ready: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for path in _json_files(storage / SIDECAR_RECEIPT_DIR / "receipts"):
        payload, reason = _read_json(path)
        if reason is not None:
            blockers.append(_blocked("value_reveal_operator_exercise_malformed_authority_receipt"))
            continue
        if not isinstance(payload, Mapping):
            blockers.append(_blocked("value_reveal_operator_exercise_malformed_authority_receipt"))
            continue
        if payload.get("sidecar_state") != READY_SIDECAR_STATE:
            continue
        if not payload.get("sidecar_receipt_id") or not payload.get("sidecar_receipt_hash"):
            blockers.append(_blocked("value_reveal_operator_exercise_partial_authority_receipt"))
            continue
        ready.append(dict(payload))
    return ready, blockers


def _bridge_responses(storage: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bridges: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for path in _json_files(storage / BRIDGE_RECEIPT_DIR / "receipts"):
        payload, reason = _read_json(path)
        if reason is not None:
            blockers.append(_blocked("value_reveal_operator_exercise_malformed_authority_receipt"))
            continue
        if not isinstance(payload, Mapping):
            blockers.append(_blocked("value_reveal_operator_exercise_malformed_authority_receipt"))
            continue
        response = payload.get("response") if isinstance(payload.get("response"), Mapping) else payload
        if not isinstance(response, Mapping):
            blockers.append(_blocked("value_reveal_operator_exercise_partial_authority_receipt"))
            continue
        if not response.get("dataset_version_id"):
            blockers.append(_blocked("value_reveal_operator_exercise_bridge_dataset_version_id_missing"))
            continue
        if not response.get("dataset_version_hash"):
            blockers.append(_blocked("value_reveal_operator_exercise_bridge_dataset_version_hash_missing"))
            continue
        bridges.append(
            {
                "receipt_id": str(response.get("fact_material_bridge_receipt_id") or path.stem),
                "receipt_hash": str(response.get("fact_material_bridge_receipt_hash") or ""),
                "response": dict(response),
            }
        )
    return bridges, blockers


def _verified_value_store(storage: Path, sidecar: Mapping[str, Any]) -> dict[str, Any]:
    metadata = sidecar.get("internal_value_store") if isinstance(sidecar.get("internal_value_store"), Mapping) else {}
    if metadata.get("store_state") != "persisted" or not metadata.get("value_store_hash"):
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_internal_value_store_missing")}
    receipt_id = str(sidecar.get("sidecar_receipt_id") or "")
    receipt_hash = str(sidecar.get("sidecar_receipt_hash") or "")
    value_store_path = storage / SIDECAR_RECEIPT_DIR / INTERNAL_VALUE_STORE_DIR / f"{receipt_id}.json"
    payload, reason = _read_json(value_store_path)
    if reason == "missing":
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_internal_value_store_missing")}
    if reason is not None or not isinstance(payload, Mapping):
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_malformed_authority_receipt")}
    records = payload.get("value_records")
    if not isinstance(records, list):
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_malformed_authority_receipt")}
    expected_hash = str(metadata.get("value_store_hash") or "")
    value_store_hash = _stable_hash(records)
    if (
        str(payload.get("sidecar_receipt_id") or "") != receipt_id
        or str(payload.get("sidecar_receipt_hash") or "") != receipt_hash
        or value_store_hash != expected_hash
        or int(payload.get("value_record_count") or len(records)) != int(metadata.get("value_record_count") or -1)
    ):
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_internal_value_store_hash_mismatch")}
    return {"blocked_reason": None, "value_store_hash": value_store_hash}


def _bridge_matches_sidecar(bridge: Mapping[str, Any], sidecar: Mapping[str, Any]) -> bool:
    return not _lineage_mismatches(sidecar, bridge["response"])


def _lineage_mismatches(sidecar: Mapping[str, Any], response: Mapping[str, Any]) -> list[str]:
    mismatches: list[str] = []
    if str(response.get("fact_authority_input_mode") or "") != ARELLE_FACT_AUTHORITY_INPUT_MODE:
        mismatches.append("fact_authority_input_mode")
    if str(response.get("arelle_sidecar_receipt_id") or "") != str(sidecar.get("sidecar_receipt_id") or ""):
        mismatches.append("arelle_sidecar_receipt_id")
    if str(response.get("arelle_sidecar_receipt_hash") or "") != str(sidecar.get("sidecar_receipt_hash") or ""):
        mismatches.append("arelle_sidecar_receipt_hash")
    authority_hashes = response.get("authority_hashes") if isinstance(response.get("authority_hashes"), Mapping) else {}
    for key in LINEAGE_KEYS:
        bridge_value = str(response.get(key) or authority_hashes.get(key) or "")
        sidecar_value = str(sidecar.get(key) or "")
        if bridge_value != sidecar_value:
            mismatches.append(key)
    materialization = response.get("materialization_summary")
    if isinstance(materialization, Mapping):
        if int(materialization.get("fact_count") or -1) != int(sidecar.get("resolved_fact_count") or -2):
            mismatches.append("resolved_fact_count")
    return sorted(set(mismatches))


def _dataset_context(db: Any | None, response: Mapping[str, Any]) -> dict[str, Any]:
    dataset_version_id = str(response.get("dataset_version_id") or "")
    dataset_version_hash = str(response.get("dataset_version_hash") or "")
    if db is None:
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_runtime_db_unavailable")}
    try:
        if hasattr(db, "get_dataset_version_context"):
            context = db.get_dataset_version_context(dataset_version_id)
            version = context.get("version") if isinstance(context, Mapping) else None
            provenance = context.get("provenance") if isinstance(context, Mapping) else None
        else:
            _ensure_backend_path(ROOT)
            from app.models.models import DatasetSourceProvenance, DatasetVersion

            version = db.get(DatasetVersion, dataset_version_id)
            provenance = (
                db.query(DatasetSourceProvenance)
                .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
                .first()
            )
    except Exception:
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_runtime_db_unavailable")}
    if version is None:
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_dataset_version_missing")}
    if str(getattr(version, "status", "") or "") != "ready":
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_dataset_version_missing")}
    if provenance is None:
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_dataset_provenance_missing")}
    source_reference = getattr(provenance, "source_reference_json", None)
    if not isinstance(source_reference, Mapping):
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_dataset_provenance_missing")}
    if str(source_reference.get("dataset_version_hash") or "") != dataset_version_hash:
        return {"blocked_reason": _blocked("value_reveal_operator_exercise_dataset_version_hash_mismatch")}
    return {"blocked_reason": None, "provenance_hash": _stable_hash(source_reference)}


def _redacted_bundle(
    *,
    sidecar: Mapping[str, Any],
    bridge: Mapping[str, Any],
    value_store_hash: str,
    provenance_hash: str,
) -> dict[str, Any]:
    response = bridge["response"]
    return {
        "sidecar_receipt_id": str(sidecar.get("sidecar_receipt_id") or ""),
        "sidecar_receipt_hash": str(sidecar.get("sidecar_receipt_hash") or ""),
        "value_store_hash": value_store_hash,
        "bridge_receipt_id": str(bridge.get("receipt_id") or ""),
        "bridge_receipt_hash": str(bridge.get("receipt_hash") or ""),
        "dataset_version_id_marker": _sha256_text(str(response.get("dataset_version_id") or ""))[:16],
        "dataset_version_hash": str(response.get("dataset_version_hash") or ""),
        "dataset_source_provenance_hash": provenance_hash,
        "lineage_hashes": {key: str(sidecar.get(key) or "") for key in LINEAGE_KEYS},
    }


def _blocked(reason: str) -> dict[str, Any]:
    return {"state": "blocked", "blocked_reason": reason}


def _dedupe_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for blocker in blockers:
        reason = str(blocker.get("blocked_reason") or "")
        if not reason or reason in seen:
            continue
        seen.add(reason)
        output.append(blocker)
    return output


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _configured_storage_dir(source_root: Path) -> Path:
    _ensure_backend_path(source_root)
    from app.core.config import settings

    return Path(settings.storage_dir)


@contextmanager
def _runtime_db(source_root: Path, db: Any | None) -> Iterator[Any | None]:
    if db is not None:
        yield db
        return
    try:
        _ensure_backend_path(source_root)
        from app.db.session import SessionLocal

        session = SessionLocal()
    except Exception:
        yield None
        return
    try:
        yield session
    finally:
        session.close()


def _json_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _read_json_or_none(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except (OSError, json.JSONDecodeError):
        return None, "unreadable"


def _file_count(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())


def _redacted_marker(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_hash(value: Any) -> str:
    _ensure_backend_path(ROOT)
    from app.services.layer3_utils import stable_hash

    return stable_hash(value)


def _ensure_backend_path(source_root: Path) -> None:
    backend = str(source_root / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
