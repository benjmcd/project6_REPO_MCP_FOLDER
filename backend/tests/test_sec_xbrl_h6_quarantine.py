from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools" / "sec-h6-quarantine.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("sec_h6_quarantine", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _seed_sidecar_run(storage_root: Path, run_id: str) -> dict[str, Path]:
    tool = _load_tool()
    run_hash = tool.sha256_text(run_id)
    sidecar_root = storage_root / "layer3-sec-edgar-arelle-resolved-fact-authority"
    sidecar_id = "sec-edgar-arelle-resolved-fact-authority-" + "a" * 24
    receipt = sidecar_root / "receipts" / f"{sidecar_id}.json"
    value_store = sidecar_root / "internal-value-stores" / f"{sidecar_id}.json"
    binding = sidecar_root / "request-bindings" / f"{run_hash}.json"
    _write_json(
        binding,
        {
            "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar_request_binding.v1",
            "client_request_id_hash": run_hash,
            "sidecar_receipt_id": sidecar_id,
        },
    )
    _write_json(
        receipt,
        {
            "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
            "sidecar_receipt_id": sidecar_id,
            "sidecar_receipt_hash": "b" * 64,
            "run_marker": run_hash,
            "internal_value_store": {"value_store_hash": "c" * 64},
        },
    )
    _write_json(
        value_store,
        {
            "schema_id": "layer3.sec_edgar_arelle_internal_value_store.v1",
            "sidecar_receipt_id": sidecar_id,
            "value_store_hash": "c" * 64,
            "value_records": [{"effective_value": "123.45"}],
        },
    )
    return {"binding": binding, "receipt": receipt, "value_store": value_store}


def test_sec_h6_dry_run_inventory_is_zero_mutation_and_links_sidecar_value_store(tmp_path) -> None:
    tool = _load_tool()
    run_id = "h6-dry-run"
    paths = _seed_sidecar_run(tmp_path, run_id)

    report = tool.build_inventory(run_id=run_id, storage_root=tmp_path)

    assert report["mode"] == "dry_run"
    assert report["zero_mutation"] is True
    assert report["mutation_performed"] is False
    assert report["source_acquisition_performed"] is False
    assert report["sec_egress_performed"] is False
    assert report["arelle_invoked"] is False
    assert report["value_reveal_performed"] is False
    assert report["file_candidate_count"] == 3
    kinds = {item["kind"] for item in report["files"]}
    assert kinds == {"sidecar_request_bindings", "sidecar_receipts", "sidecar_internal_value_stores"}
    assert all(path.exists() for path in paths.values())


def test_sec_h6_execute_requires_double_confirmation_and_path_ack(tmp_path) -> None:
    tool = _load_tool()
    run_id = "h6-refuse"
    paths = _seed_sidecar_run(tmp_path, run_id)
    report = tool.build_inventory(run_id=run_id, storage_root=tmp_path)

    refused = tool.quarantine_files(
        report,
        run_id=run_id,
        storage_root=tmp_path,
        repo_root=tmp_path / "repo",
        confirm_run_id=run_id,
        confirm_quarantine=True,
        ack_outside_repo_onedrive=False,
    )

    assert refused["status"] == "refused"
    assert refused["mutation_performed"] is False
    assert {item["code"] for item in refused["refusals"]} == {"candidate_outside_repo_or_onedrive_without_ack"}
    assert all(path.exists() for path in paths.values())


def test_sec_h6_execute_moves_files_to_flat_archive_only_with_ack(tmp_path) -> None:
    tool = _load_tool()
    run_id = "h6-quarantine"
    paths = _seed_sidecar_run(tmp_path / "storage", run_id)
    repo_root = tmp_path / "repo"
    report = tool.build_inventory(run_id=run_id, storage_root=tmp_path / "storage")

    quarantined = tool.quarantine_files(
        report,
        run_id=run_id,
        storage_root=tmp_path / "storage",
        repo_root=repo_root,
        confirm_run_id=run_id,
        confirm_quarantine=True,
        ack_outside_repo_onedrive=True,
    )

    assert quarantined["status"] == "quarantined"
    assert quarantined["mutation_performed"] is True
    assert quarantined["db_mutation_performed"] is False
    assert all(not path.exists() for path in paths.values())
    moved = [Path(item["archive_path"]) for item in quarantined["moved_files"]]
    assert len(moved) == 3
    assert all(path.exists() for path in moved)
    assert all(path.parent == repo_root / "archive" / "sec-h6" for path in moved)
    manifest = Path(quarantined["archive_manifest"])
    assert manifest.exists()
    assert manifest.parent == repo_root / "archive" / "sec-h6"


def test_sec_h6_sqlite_inventory_reports_controlled_submit_row_without_db_mutation(tmp_path) -> None:
    tool = _load_tool()
    run_id = "h6-db-row"
    run_hash = tool.sha256_text(run_id)
    db_path = tmp_path / "h6.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE l3_sec_xbrl_controlled_value_reveal_submit_receipt ("
            "sec_xbrl_controlled_value_reveal_submit_receipt_id TEXT, "
            "client_request_id_hash TEXT, submit_basis_hash TEXT)"
        )
        conn.execute("CREATE TABLE connector_run (connector_run_id TEXT, request_config_json TEXT)")
        conn.execute(
            "CREATE TABLE dataset_source_provenance ("
            "dataset_source_provenance_id TEXT, connector_run_id TEXT, source_artifact_key TEXT)"
        )
        conn.execute(
            "INSERT INTO l3_sec_xbrl_controlled_value_reveal_submit_receipt VALUES (?, ?, ?)",
            ("submit-row-1", run_hash, "a" * 64),
        )
        conn.execute(
            "INSERT INTO connector_run VALUES (?, ?)",
            ("connector-run-1", json.dumps({"run_id_hash": run_hash})),
        )
        conn.execute(
            "INSERT INTO dataset_source_provenance VALUES (?, ?, ?)",
            ("provenance-1", "connector-run-1", f"sec-xbrl/{run_hash}/artifact.json"),
        )
        conn.commit()
    finally:
        conn.close()

    report = tool.build_inventory(run_id=run_id, storage_root=tmp_path / "storage", sqlite_db=db_path)

    assert report["db_row_candidate_count"] == 3
    rows_by_table = {row["table"]: row for row in report["db_rows"]}
    assert set(rows_by_table) == {
        "connector_run",
        "dataset_source_provenance",
        "l3_sec_xbrl_controlled_value_reveal_submit_receipt",
    }
    assert (
        rows_by_table["l3_sec_xbrl_controlled_value_reveal_submit_receipt"]["row_ref"]
        == "sec_xbrl_controlled_value_reveal_submit_receipt_id:submit-row-1"
    )
    assert rows_by_table["connector_run"]["row_ref"] == "connector_run_id:connector-run-1"
    assert all(row["row_sha256"] for row in report["db_rows"])
    assert all(row["db_mutation_performed"] is False for row in report["db_rows"])


def test_sec_h6_cli_defaults_to_dry_run_no_archive_creation(tmp_path, capsys) -> None:
    tool = _load_tool()
    run_id = "h6-cli"
    paths = _seed_sidecar_run(tmp_path, run_id)

    exit_code = tool.main(["--run-id", run_id, "--storage-root", str(tmp_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["mode"] == "dry_run"
    assert output["mutation_performed"] is False
    assert all(path.exists() for path in paths.values())
