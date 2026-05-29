from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-value-reveal-operator-exercise-runner.py"


def _runner_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_value_reveal_operator_exercise_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeDb:
    def __init__(self, *, versions: Mapping[str, Any] | None = None, provenances: Mapping[str, Any] | None = None):
        self.versions = dict(versions or {})
        self.provenances = dict(provenances or {})

    def get_dataset_version_context(self, dataset_version_id: str) -> dict[str, Any]:
        return {
            "version": self.versions.get(dataset_version_id),
            "provenance": self.provenances.get(dataset_version_id),
        }


def _hex(char: str) -> str:
    return char * 64


def _lineage() -> dict[str, str]:
    return {
        "parser_receipt_hash": _hex("1"),
        "connector_receipt_hash": _hex("2"),
        "live_source_artifact_receipt_hash": _hex("3"),
        "source_artifact_receipt_hash": _hex("4"),
        "content_sha256": _hex("5"),
        "primary_document_hash": _hex("6"),
        "document_inventory_hash": _hex("7"),
        "content_order_hash": _hex("8"),
        "table_candidate_inventory_hash": _hex("9"),
        "inline_xbrl_marker_inventory_hash": _hex("a"),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sidecar_path(module: Any, storage: Path, sidecar_id: str) -> Path:
    return storage / module.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json"


def _value_store_path(module: Any, storage: Path, sidecar_id: str) -> Path:
    return storage / module.SIDECAR_RECEIPT_DIR / module.INTERNAL_VALUE_STORE_DIR / f"{sidecar_id}.json"


def _bridge_path(module: Any, storage: Path, bridge_id: str) -> Path:
    return storage / module.BRIDGE_RECEIPT_DIR / "receipts" / f"{bridge_id}.json"


def _authority_bundle(
    module: Any,
    storage: Path,
    *,
    sidecar_id: str = "sec-edgar-arelle-resolved-fact-authority-aaaaaaaaaaaaaaaaaaaaaaaa",
    sidecar_hash: str = _hex("b"),
    bridge_id: str = "sec-edgar-html-inline-xbrl-fact-material-bridge-cccccccccccccccccccccccc",
    bridge_hash: str | None = None,
    dataset_version_id: str = "dataset-version-alpha",
    dataset_version_hash: str = _hex("e"),
    write_value_store: bool = True,
    value_store_records: list[dict[str, Any]] | None = None,
    sidecar_overrides: Mapping[str, Any] | None = None,
    bridge_overrides: Mapping[str, Any] | None = None,
    basis_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    records = value_store_records if value_store_records is not None else [{"resolved_fact_id": "fact-alpha", "value_hash": _hex("f")}]
    value_store_hash = module._stable_hash(records)
    lineage = _lineage()
    sidecar = {
        "sidecar_state": module.READY_SIDECAR_STATE,
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "resolved_fact_count": len(records),
        "internal_value_store": {
            "store_state": "persisted",
            "value_store_hash": value_store_hash,
            "value_record_count": len(records),
        },
        **lineage,
    }
    sidecar.update(dict(sidecar_overrides or {}))
    _write_json(storage / module.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    if write_value_store:
        _write_json(
            storage / module.SIDECAR_RECEIPT_DIR / module.INTERNAL_VALUE_STORE_DIR / f"{sidecar_id}.json",
            {
                "sidecar_receipt_id": sidecar_id,
                "sidecar_receipt_hash": sidecar_hash,
                "value_store_hash": value_store_hash,
                "value_record_count": len(records),
                "value_records": records,
            },
        )
    bridge_response = {
        "fact_material_bridge_receipt_id": bridge_id,
        "fact_authority_input_mode": module.ARELLE_FACT_AUTHORITY_INPUT_MODE,
        "arelle_sidecar_receipt_id": sidecar_id,
        "arelle_sidecar_receipt_hash": sidecar_hash,
        "dataset_version_id": dataset_version_id,
        "dataset_version_hash": dataset_version_hash,
        "materialization_summary": {"fact_count": len(records)},
        **lineage,
    }
    bridge_response.update(dict(bridge_overrides or {}))
    receipt_hash_basis = {
        "hash_version": "sec_edgar_html_inline_xbrl_fact_material_bridge_hash_v1",
        "bridge_mode": "sec_edgar_html_inline_xbrl_fact_authority_to_layer3_fact_material_authority_v1",
        "fact_authority_receipt_hash": _hex("7"),
        "parser_receipt_hash": str(bridge_response.get("parser_receipt_hash") or ""),
        "dataset_version_hash": str(bridge_response.get("dataset_version_hash") or ""),
        "materialization_receipt_hash": _hex("8"),
        "material_preview_hash": _hex("9"),
        "gate_b_decision_manifest_id": "sec-edgar-html-inline-xbrl-fact-material-bridge-gate-b-decision-aaaaaaaa",
        "fact_authority_input_mode": str(bridge_response.get("fact_authority_input_mode") or ""),
        "arelle_sidecar_receipt_hash": str(bridge_response.get("arelle_sidecar_receipt_hash") or ""),
        "regex_fact_authority_receipt_hash": _hex("0"),
        "resolved_fact_inventory_hash": _hex("1"),
        "internal_value_store_hash": value_store_hash,
    }
    receipt_hash_basis.update(dict(basis_overrides or {}))
    bridge_response["fact_material_bridge_receipt_hash"] = (
        bridge_hash if bridge_hash is not None else module._stable_hash(receipt_hash_basis)
    )
    _write_json(
        storage / module.BRIDGE_RECEIPT_DIR / "receipts" / f"{bridge_id}.json",
        {"response": bridge_response, "receipt_hash_basis": receipt_hash_basis},
    )
    return {
        "dataset_version_id": dataset_version_id,
        "dataset_version_hash": dataset_version_hash,
        "sidecar_id": sidecar_id,
        "sidecar_hash": sidecar_hash,
    }


def _ready_db(dataset_version_id: str, dataset_version_hash: str) -> _FakeDb:
    return _FakeDb(
        versions={dataset_version_id: SimpleNamespace(status="ready")},
        provenances={dataset_version_id: SimpleNamespace(source_reference_json={"dataset_version_hash": dataset_version_hash})},
    )


def _blocked_reasons(report: Mapping[str, Any]) -> set[str]:
    return {str(item.get("blocked_reason")) for item in report["blocking_reasons"] if item.get("blocked_reason")}


def _assert_redacted(report: Mapping[str, Any]) -> None:
    blocked = ("http://", "https://", "C:\\", "\\Users\\", "accession", "ticker", " cik", "contact")
    values: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)
        elif isinstance(value, str):
            values.append(value.lower())

    walk(report)
    for value in values:
        assert all(item.lower() not in value for item in blocked)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_without_authority(tmp_path: Path) -> None:
    module = _runner_module()

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_FakeDb())

    assert report["decision"] == "value_reveal_operator_exercise_blocked_missing_authority"
    assert report["operator_exercise_performed"] is False
    assert report["ready_to_run_operator_exercise"] is False
    assert report["next_slice"] == "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1"
    assert "value_reveal_operator_exercise_ready_sidecar_authority_missing" in _blocked_reasons(report)
    assert "value_reveal_operator_exercise_no_coherent_authority_bundle" in _blocked_reasons(report)
    assert report["redacted_inventory"]["storage_exists"] is True
    assert report["redacted_inventory"]["storage_file_count"] == 0
    assert report["non_goals_preserved"]["raw_values_returned"] is False
    assert report["non_goals_preserved"]["arelle_subprocess_invoked"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_bridge_without_dataset_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, bridge_overrides={"dataset_version_hash": ""})

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert "value_reveal_operator_exercise_bridge_dataset_version_hash_missing" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_bridge_without_dataset_id(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, bridge_overrides={"dataset_version_id": ""})

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert "value_reveal_operator_exercise_bridge_dataset_version_id_missing" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_different_sidecar_lineage(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(
        module,
        tmp_path,
        bridge_overrides={
            "arelle_sidecar_receipt_id": "sec-edgar-arelle-resolved-fact-authority-111111111111111111111111",
            "arelle_sidecar_receipt_hash": _hex("c"),
        },
    )

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert "value_reveal_operator_exercise_sidecar_bridge_lineage_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_missing_internal_value_store(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, write_value_store=False)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert "value_reveal_operator_exercise_internal_value_store_missing" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_value_store_hash_mismatch(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, value_store_records=[{"resolved_fact_id": "fact-alpha", "value_hash": _hex("1")}])
    sidecar_store = tmp_path / module.SIDECAR_RECEIPT_DIR / module.INTERNAL_VALUE_STORE_DIR / f"{bundle['sidecar_id']}.json"
    payload = json.loads(sidecar_store.read_text(encoding="utf-8"))
    payload["value_records"] = [{"resolved_fact_id": "fact-alpha", "value_hash": _hex("2")}]
    _write_json(sidecar_store, payload)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert "value_reveal_operator_exercise_internal_value_store_hash_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_sidecar_value_count(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)
    sidecar_path = _sidecar_path(module, tmp_path, bundle["sidecar_id"])
    payload = _load_json(sidecar_path)
    payload["internal_value_store"]["value_record_count"] = "abc"
    _write_json(sidecar_path, payload)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert module.MALFORMED_AUTHORITY_COUNT_REASON in _blocked_reasons(report)
    assert report["redacted_inventory"]["sidecar_receipt_count"] == 1
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_value_store_count(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)
    value_store_path = _value_store_path(module, tmp_path, bundle["sidecar_id"])
    payload = _load_json(value_store_path)
    payload["value_record_count"] = "abc"
    _write_json(value_store_path, payload)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert module.MALFORMED_AUTHORITY_COUNT_REASON in _blocked_reasons(report)
    assert report["redacted_inventory"]["internal_value_store_file_count"] == 1
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_value_store_count_mismatch(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)
    value_store_path = _value_store_path(module, tmp_path, bundle["sidecar_id"])
    payload = _load_json(value_store_path)
    payload["value_record_count"] = 2
    _write_json(value_store_path, payload)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert "value_reveal_operator_exercise_internal_value_store_hash_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_bridge_fact_count(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)
    bridge_path = _bridge_path(module, tmp_path, "sec-edgar-html-inline-xbrl-fact-material-bridge-cccccccccccccccccccccccc")
    payload = _load_json(bridge_path)
    payload["response"]["materialization_summary"]["fact_count"] = "abc"
    _write_json(bridge_path, payload)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert module.MALFORMED_AUTHORITY_COUNT_REASON in _blocked_reasons(report)
    assert report["redacted_inventory"]["bridge_receipt_count"] == 1
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_sidecar_receipt_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, sidecar_hash="not-a-sha")

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert module.MALFORMED_AUTHORITY_HASH_REASON in _blocked_reasons(report)
    assert report["redacted_inventory"]["sidecar_receipt_count"] == 1
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_bridge_receipt_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, bridge_hash="not-a-sha")

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert module.MALFORMED_AUTHORITY_HASH_REASON in _blocked_reasons(report)
    assert report["redacted_inventory"]["bridge_receipt_count"] == 1
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_dataset_version_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path, dataset_version_hash="not-a-sha")

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], "not-a-sha"))

    assert module.MALFORMED_AUTHORITY_HASH_REASON in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_lineage_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(
        module,
        tmp_path,
        sidecar_overrides={"parser_receipt_hash": "not-a-sha"},
        bridge_overrides={"parser_receipt_hash": "not-a-sha"},
    )

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert module.MALFORMED_AUTHORITY_HASH_REASON in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_rejects_echoed_non_sha_authorities(tmp_path: Path) -> None:
    module = _runner_module()
    bad_hash = "g" * 64
    bad_lineage = {key: bad_hash for key in _lineage()}
    bundle = _authority_bundle(
        module,
        tmp_path,
        sidecar_hash=bad_hash,
        bridge_hash=bad_hash,
        dataset_version_hash=bad_hash,
        sidecar_overrides=bad_lineage,
        bridge_overrides=bad_lineage,
    )

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bad_hash))

    assert module.MALFORMED_AUTHORITY_HASH_REASON in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    assert report["selected_authority_bundle"] is None
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_validates_coherent_bridge_wrapper_hash_basis(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]),
    )

    assert report["decision"] == "value_reveal_operator_exercise_ready_to_run"
    assert report["ready_to_run_operator_exercise"] is True
    assert report["selected_authority_bundle"] is not None
    assert report["blocking_reasons"] == []
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_missing_bridge_wrapper_basis(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)
    bridge_path = _bridge_path(module, tmp_path, "sec-edgar-html-inline-xbrl-fact-material-bridge-cccccccccccccccccccccccc")
    payload = _load_json(bridge_path)
    payload.pop("receipt_hash_basis", None)
    _write_json(bridge_path, payload)

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]),
    )

    assert "value_reveal_operator_exercise_bridge_wrapper_basis_missing" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    assert report["selected_authority_bundle"] is None
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_tampered_bridge_wrapper_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)
    bridge_path = _bridge_path(module, tmp_path, "sec-edgar-html-inline-xbrl-fact-material-bridge-cccccccccccccccccccccccc")
    payload = _load_json(bridge_path)
    # Tamper the stored receipt hash to a different valid sha; the persisted basis no longer
    # recomputes to it, so the wrapper receipt hash must be rejected.
    payload["response"]["fact_material_bridge_receipt_hash"] = _hex("0")
    _write_json(bridge_path, payload)

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]),
    )

    assert "value_reveal_operator_exercise_bridge_wrapper_hash_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    assert report["selected_authority_bundle"] is None
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_bridge_wrapper_value_store_binding_mismatch(tmp_path: Path) -> None:
    module = _runner_module()
    # The basis recomputes to the stored receipt hash (internally coherent wrapper), but its
    # committed internal_value_store_hash does not match the independently recomputed value store,
    # so a coherently re-hashed but tampered wrapper still fails.
    bundle = _authority_bundle(module, tmp_path, basis_overrides={"internal_value_store_hash": _hex("9")})

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]),
    )

    assert "value_reveal_operator_exercise_bridge_wrapper_value_store_binding_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    assert report["selected_authority_bundle"] is None
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_bridge_wrapper_sidecar_binding_mismatch(tmp_path: Path) -> None:
    module = _runner_module()
    # The basis recomputes to the stored receipt hash, but its committed arelle_sidecar_receipt_hash
    # does not match the independently read sidecar receipt hash.
    bundle = _authority_bundle(module, tmp_path, basis_overrides={"arelle_sidecar_receipt_hash": _hex("0")})

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]),
    )

    assert "value_reveal_operator_exercise_bridge_wrapper_sidecar_binding_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    assert report["selected_authority_bundle"] is None
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_missing_dataset_version(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_FakeDb(provenances={bundle["dataset_version_id"]: SimpleNamespace(source_reference_json={"dataset_version_hash": bundle["dataset_version_hash"]})}),
    )

    assert "value_reveal_operator_exercise_dataset_version_missing" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_missing_provenance(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_FakeDb(versions={bundle["dataset_version_id"]: SimpleNamespace(status="ready")}),
    )

    assert "value_reveal_operator_exercise_dataset_provenance_missing" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_mismatched_provenance_hash(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)

    report = module.build_report(
        source_root=ROOT,
        storage_dir=tmp_path,
        db=_ready_db(bundle["dataset_version_id"], _hex("0")),
    )

    assert "value_reveal_operator_exercise_dataset_version_hash_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_multiple_unrelated_partial_authorities(tmp_path: Path) -> None:
    module = _runner_module()
    first = _authority_bundle(
        module,
        tmp_path,
        sidecar_id="sec-edgar-arelle-resolved-fact-authority-aaaaaaaaaaaaaaaaaaaaaaaa",
        bridge_id="sec-edgar-html-inline-xbrl-fact-material-bridge-111111111111111111111111",
        bridge_overrides={"arelle_sidecar_receipt_hash": _hex("0")},
    )
    second = _authority_bundle(
        module,
        tmp_path,
        sidecar_id="sec-edgar-arelle-resolved-fact-authority-bbbbbbbbbbbbbbbbbbbbbbbb",
        sidecar_hash=_hex("c"),
        bridge_id="sec-edgar-html-inline-xbrl-fact-material-bridge-222222222222222222222222",
        dataset_version_id="dataset-version-beta",
        dataset_version_hash=_hex("4"),
        bridge_overrides={"arelle_sidecar_receipt_hash": _hex("5")},
    )
    db = _FakeDb(
        versions={
            first["dataset_version_id"]: SimpleNamespace(status="ready"),
            second["dataset_version_id"]: SimpleNamespace(status="ready"),
        },
        provenances={
            first["dataset_version_id"]: SimpleNamespace(source_reference_json={"dataset_version_hash": first["dataset_version_hash"]}),
            second["dataset_version_id"]: SimpleNamespace(source_reference_json={"dataset_version_hash": second["dataset_version_hash"]}),
        },
    )

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=db)

    assert "value_reveal_operator_exercise_sidecar_bridge_lineage_mismatch" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_multiple_coherent_candidates(tmp_path: Path) -> None:
    module = _runner_module()
    first = _authority_bundle(
        module,
        tmp_path,
        sidecar_id="sec-edgar-arelle-resolved-fact-authority-aaaaaaaaaaaaaaaaaaaaaaaa",
        sidecar_hash=_hex("b"),
        bridge_id="sec-edgar-html-inline-xbrl-fact-material-bridge-111111111111111111111111",
    )
    second = _authority_bundle(
        module,
        tmp_path,
        sidecar_id="sec-edgar-arelle-resolved-fact-authority-bbbbbbbbbbbbbbbbbbbbbbbb",
        sidecar_hash=_hex("c"),
        bridge_id="sec-edgar-html-inline-xbrl-fact-material-bridge-222222222222222222222222",
        dataset_version_id="dataset-version-beta",
        dataset_version_hash=_hex("4"),
    )
    db = _FakeDb(
        versions={
            first["dataset_version_id"]: SimpleNamespace(status="ready"),
            second["dataset_version_id"]: SimpleNamespace(status="ready"),
        },
        provenances={
            first["dataset_version_id"]: SimpleNamespace(source_reference_json={"dataset_version_hash": first["dataset_version_hash"]}),
            second["dataset_version_id"]: SimpleNamespace(source_reference_json={"dataset_version_hash": second["dataset_version_hash"]}),
        },
    )

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=db)

    assert "value_reveal_operator_exercise_ambiguous_authority_bundle" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_malformed_receipt_json(tmp_path: Path) -> None:
    module = _runner_module()
    receipt_dir = tmp_path / module.SIDECAR_RECEIPT_DIR / "receipts"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "bad.json").write_text("{", encoding="utf-8")

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_FakeDb())

    assert "value_reveal_operator_exercise_malformed_authority_receipt" in _blocked_reasons(report)
    assert report["ready_to_run_operator_exercise"] is False
    _assert_redacted(report)


def test_sec_xbrl_value_reveal_operator_exercise_runner_ready_only_for_coherent_bundle(tmp_path: Path) -> None:
    module = _runner_module()
    bundle = _authority_bundle(module, tmp_path)

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path, db=_ready_db(bundle["dataset_version_id"], bundle["dataset_version_hash"]))

    assert report["decision"] == "value_reveal_operator_exercise_ready_to_run"
    assert report["ready_to_run_operator_exercise"] is True
    assert report["selected_authority_bundle"]["sidecar_receipt_id"] == bundle["sidecar_id"]
    assert report["selected_authority_bundle"]["sidecar_receipt_hash"] == bundle["sidecar_hash"]
    assert report["selected_authority_bundle"]["dataset_version_hash"] == bundle["dataset_version_hash"]
    assert "dataset-version-alpha" not in json.dumps(report, sort_keys=True)
    assert report["selected_authority_bundle"]["dataset_version_id_marker"]
    _assert_redacted(report)
