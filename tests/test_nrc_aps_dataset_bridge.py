import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base  # noqa: E402
from app.models import (  # noqa: E402
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetExternalIdentity,
    DatasetRow,
    DatasetSourceProvenance,
    DatasetVersion,
    VariableDefinition,
    VariableProfile,
)
from app.services import connectors_nrc_adams  # noqa: E402
from app.services import nrc_aps_dataset_bridge  # noqa: E402
from app.services import nrc_aps_document_processing  # noqa: E402
from support_nrc_aps_xlsx import build_xlsx_bytes  # noqa: E402


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def _csv_target_payload() -> dict:
    extraction = nrc_aps_document_processing.process_document(
        content=b"date,value,label\n2026-01-01,42,alpha\n2026-01-02,43,beta\n",
        declared_content_type="text/csv",
    )
    return {
        "run_id": "run-csv-1",
        "target_id": "target-csv-1",
        "accession_number": "MLCSV0001",
        "outcome_status": "processed",
        "download": {
            "content_type": "text/csv",
            "blob_sha256": "a" * 64,
            "blob_ref": "/tmp/raw.csv",
        },
        "extraction": extraction,
    }


def _xlsx_target_payload() -> dict:
    extraction = nrc_aps_document_processing.process_document(
        content=build_xlsx_bytes(
            {
                "Observations": [
                    ["date", "value", "label"],
                    ["2026-01-01", 42, "alpha"],
                    ["2026-01-02", 43, "beta"],
                ],
            }
        ),
        declared_content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return {
        "run_id": "run-xlsx-1",
        "target_id": "target-xlsx-1",
        "accession_number": "MLXLSX0001",
        "outcome_status": "processed",
        "download": {
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "blob_sha256": "b" * 64,
            "blob_ref": "/tmp/raw.xlsx",
        },
        "extraction": extraction,
    }


def _json_target_payload() -> dict:
    extraction = nrc_aps_document_processing.process_document(
        content=json.dumps(
            [
                {"date": "2026-01-01", "value": 42, "label": "alpha"},
                {"date": "2026-01-02", "value": 43, "label": "beta"},
            ]
        ).encode("utf-8"),
        declared_content_type="application/json",
    )
    return {
        "run_id": "run-json-1",
        "target_id": "target-json-1",
        "accession_number": "MLJSON0001",
        "outcome_status": "processed",
        "download": {
            "content_type": "application/json",
            "blob_sha256": "c" * 64,
            "blob_ref": "/tmp/raw.json",
        },
        "extraction": extraction,
    }


def test_materialize_csv_table_dataset_creates_dataset_authority(tmp_path: Path):
    db = _make_session()

    result = nrc_aps_dataset_bridge.materialize_csv_table_dataset(
        db,
        target_artifact_payload=_csv_target_payload(),
        artifact_storage_dir=tmp_path,
    )

    assert result["created"] is True
    assert result["dataset_bridge_contract_id"] == "aps_csv_dataset_bridge_v1"
    assert result["row_count"] == 2
    assert result["time_column"] == "date"
    assert result["numeric_columns"] == ["value"]
    assert Path(str(result["storage_ref"])).exists()

    dataset = db.get(Dataset, result["dataset_id"])
    version = db.get(DatasetVersion, result["dataset_version_id"])
    assert dataset is not None
    assert dataset.time_column == "date"
    assert version is not None
    assert version.row_count == 2

    variables = (
        db.query(VariableDefinition)
        .filter(VariableDefinition.dataset_version_id == result["dataset_version_id"])
        .order_by(VariableDefinition.ordinal_position.asc())
        .all()
    )
    assert [(item.variable_name, item.is_time_index, item.is_numeric) for item in variables] == [
        ("date", True, False),
        ("value", False, True),
        ("label", False, False),
    ]
    profile = db.query(VariableProfile).one()
    assert profile.variable_id == variables[1].variable_id
    assert profile.mean_value == 42.5

    rows = (
        db.query(DatasetRow)
        .filter(DatasetRow.dataset_version_id == result["dataset_version_id"])
        .order_by(DatasetRow.row_number.asc())
        .all()
    )
    assert len(rows) == 2
    assert rows[0].values_json["value"] == 42
    assert rows[0].observed_at is not None

    identity = db.query(DatasetExternalIdentity).one()
    assert identity.source_system == "nrc_adams_aps"
    assert identity.metadata_json["typed_content_contract_id"] == "aps_csv_table_units_v1"

    provenance = db.query(DatasetSourceProvenance).one()
    assert provenance.connector_run_id is None
    assert provenance.source_system == "nrc_adams_aps"
    assert provenance.source_mode == "artifact_csv_parser"
    assert provenance.downloaded_sha256 == "a" * 64
    assert provenance.source_reference_json["target_id"] == "target-csv-1"
    assert provenance.source_reference_json["parser_family"] == "csv_table"


def test_materialize_xlsx_table_dataset_preserves_sheet_provenance(tmp_path: Path):
    db = _make_session()

    result = nrc_aps_dataset_bridge.materialize_table_unit_dataset(
        db,
        target_artifact_payload=_xlsx_target_payload(),
        artifact_storage_dir=tmp_path,
    )

    assert result["created"] is True
    assert result["dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert result["row_count"] == 2
    assert result["time_column"] == "date"
    assert result["numeric_columns"] == ["value"]

    dataset = db.get(Dataset, result["dataset_id"])
    assert dataset is not None
    assert dataset.name.startswith("APS XLSX workbook table")

    identity = db.query(DatasetExternalIdentity).one()
    assert identity.logical_dataset_key.startswith("xlsx-table:")
    assert identity.metadata_json["dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert identity.metadata_json["typed_content_contract_id"] == "aps_xlsx_table_units_v1"
    assert identity.metadata_json["parser_family"] == "xlsx_workbook"

    provenance = db.query(DatasetSourceProvenance).one()
    assert provenance.source_mode == "artifact_xlsx_parser"
    assert provenance.sciencebase_file_name is None
    assert provenance.downloaded_sha256 == "b" * 64
    assert provenance.source_reference_json["parser_family"] == "xlsx_workbook"
    assert provenance.source_reference_json["typed_content_contract_id"] == "aps_xlsx_table_units_v1"


def test_materialize_json_recordset_table_dataset_preserves_recordset_provenance(tmp_path: Path):
    db = _make_session()

    result = nrc_aps_dataset_bridge.materialize_table_unit_dataset(
        db,
        target_artifact_payload=_json_target_payload(),
        artifact_storage_dir=tmp_path,
    )

    assert result["created"] is True
    assert result["dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert result["row_count"] == 2
    assert result["time_column"] == "date"
    assert result["numeric_columns"] == ["value"]

    dataset = db.get(Dataset, result["dataset_id"])
    assert dataset is not None
    assert dataset.name.startswith("APS JSON recordset table")

    identity = db.query(DatasetExternalIdentity).one()
    assert identity.logical_dataset_key.startswith("json-recordset:")
    assert identity.metadata_json["dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert identity.metadata_json["typed_content_contract_id"] == "aps_json_recordset_units_v1"
    assert identity.metadata_json["parser_family"] == "json_recordset"

    provenance = db.query(DatasetSourceProvenance).one()
    assert provenance.source_mode == "artifact_json_recordset_parser"
    assert provenance.downloaded_sha256 == "c" * 64
    assert provenance.source_reference_json["parser_family"] == "json_recordset"
    assert provenance.source_reference_json["typed_content_contract_id"] == "aps_json_recordset_units_v1"


def test_materialize_csv_table_dataset_is_idempotent(tmp_path: Path):
    db = _make_session()
    payload = _csv_target_payload()

    first = nrc_aps_dataset_bridge.materialize_csv_table_dataset(
        db,
        target_artifact_payload=payload,
        artifact_storage_dir=tmp_path,
    )
    second = nrc_aps_dataset_bridge.materialize_csv_table_dataset(
        db,
        target_artifact_payload=payload,
        artifact_storage_dir=tmp_path,
    )

    assert first["dataset_id"] == second["dataset_id"]
    assert first["dataset_version_id"] == second["dataset_version_id"]
    assert second["created"] is False
    assert db.query(Dataset).count() == 1
    assert db.query(DatasetVersion).count() == 1
    assert db.query(DatasetRow).count() == 2
    assert db.query(VariableProfile).count() == 1
    assert db.query(DatasetExternalIdentity).count() == 1
    assert db.query(DatasetSourceProvenance).count() == 1


def test_materialize_csv_table_dataset_requires_csv_parser_contract():
    db = _make_session()
    payload = _csv_target_payload()
    payload["extraction"] = {**payload["extraction"], "parser_family": "plain_text"}

    try:
        nrc_aps_dataset_bridge.materialize_csv_table_dataset(db, target_artifact_payload=payload)
    except ValueError as exc:
        assert str(exc) == "dataset_bridge_requires_csv_table_parser"
    else:
        raise AssertionError("expected bridge to reject non-CSV parser output")


def test_materialize_csv_table_dataset_rejects_xlsx_parser_output():
    db = _make_session()

    try:
        nrc_aps_dataset_bridge.materialize_csv_table_dataset(db, target_artifact_payload=_xlsx_target_payload())
    except ValueError as exc:
        assert str(exc) == "dataset_bridge_requires_csv_table_parser"
    else:
        raise AssertionError("expected CSV compatibility bridge to reject XLSX parser output")


def test_connector_csv_dataset_bridge_materializes_processed_csv_target(tmp_path: Path):
    db = _make_session()
    artifact_ref = tmp_path / "target-artifact.json"
    target_payload = {
        **_csv_target_payload(),
        "source_reference_json": {"metadata_ref": "metadata.json"},
    }
    artifact_ref.write_text(json.dumps(target_payload), encoding="utf-8")
    run = ConnectorRun(
        connector_run_id="run-csv-bridge-1",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
        selected_count=1,
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-csv-bridge-1",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        artifact_surface="documents",
        status="recommended",
        source_reference_json={"aps_artifact_ingestion_ref": str(artifact_ref)},
    )
    db.add(run)
    db.add(target)
    db.commit()

    summary = connectors_nrc_adams._generate_csv_dataset_bridge_artifacts(
        db,
        run=run,
        config={
            "csv_dataset_bridge_enabled": True,
            "artifact_storage_dir": str(tmp_path / "storage"),
            "connector_reports_dir": str(tmp_path / "reports"),
        },
    )

    assert summary["run_outcome"] == "datasets_materialized"
    assert summary["materialized_dataset_versions"] == 1
    assert summary["created_dataset_versions"] == 1
    assert summary["failures_count"] == 0
    assert Path(str(summary["run_ref"])).exists()

    refreshed_target = db.get(ConnectorRunTarget, "target-csv-bridge-1")
    assert refreshed_target is not None
    assert refreshed_target.dataset_id
    assert refreshed_target.dataset_version_id
    assert refreshed_target.source_reference_json["aps_csv_dataset_bridge_ref"] == summary["run_ref"]
    assert refreshed_target.source_reference_json["aps_csv_dataset_bridge_contract_id"] == "aps_csv_dataset_bridge_v1"
    assert db.get(DatasetVersion, refreshed_target.dataset_version_id) is not None
    provenance = db.query(DatasetSourceProvenance).one()
    assert provenance.connector_run_id == "run-csv-bridge-1"

    report = json.loads(Path(str(summary["run_ref"])).read_text(encoding="utf-8"))
    assert report["schema_id"] == "aps.csv_dataset_bridge_run.v1"
    assert report["enabled"] is True
    assert report["materialized"][0]["target_id"] == "target-csv-bridge-1"
    assert run.query_plan_json["aps_csv_dataset_bridge_report_refs"]["aps_csv_dataset_bridge"] == summary["run_ref"]


def test_connector_table_dataset_bridge_materializes_processed_xlsx_target(tmp_path: Path):
    db = _make_session()
    artifact_ref = tmp_path / "target-artifact.json"
    target_payload = {
        **_xlsx_target_payload(),
        "source_reference_json": {"metadata_ref": "metadata.json"},
    }
    artifact_ref.write_text(json.dumps(target_payload), encoding="utf-8")
    run = ConnectorRun(
        connector_run_id="run-table-bridge-xlsx",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
        selected_count=1,
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-table-bridge-xlsx",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        artifact_surface="documents",
        status="recommended",
        source_reference_json={"aps_artifact_ingestion_ref": str(artifact_ref)},
    )
    db.add(run)
    db.add(target)
    db.commit()

    summary = connectors_nrc_adams._generate_table_dataset_bridge_artifacts(
        db,
        run=run,
        config={
            "table_dataset_bridge_enabled": True,
            "artifact_storage_dir": str(tmp_path / "storage"),
            "connector_reports_dir": str(tmp_path / "reports"),
        },
    )

    assert summary["run_outcome"] == "datasets_materialized"
    assert summary["materialized_dataset_versions"] == 1
    assert summary["created_dataset_versions"] == 1
    assert summary["failures_count"] == 0
    assert Path(str(summary["run_ref"])).exists()

    refreshed_target = db.get(ConnectorRunTarget, "target-table-bridge-xlsx")
    assert refreshed_target is not None
    assert refreshed_target.dataset_id
    assert refreshed_target.dataset_version_id
    assert refreshed_target.source_reference_json["aps_table_dataset_bridge_ref"] == summary["run_ref"]
    assert refreshed_target.source_reference_json["aps_table_dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert refreshed_target.source_reference_json["aps_table_dataset_parser_family"] == "xlsx_workbook"
    assert "aps_csv_dataset_bridge_ref" not in refreshed_target.source_reference_json

    version = db.get(DatasetVersion, refreshed_target.dataset_version_id)
    assert version is not None
    assert version.row_count == 2
    assert version.notes.startswith("aps_table_dataset_bridge_v1;")
    provenance = db.query(DatasetSourceProvenance).one()
    assert provenance.connector_run_id == "run-table-bridge-xlsx"
    assert provenance.source_mode == "artifact_xlsx_parser"

    report = json.loads(Path(str(summary["run_ref"])).read_text(encoding="utf-8"))
    assert report["schema_id"] == "aps.table_dataset_bridge_run.v1"
    assert report["enabled"] is True
    assert report["dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert report["supported_parser_families"] == ["csv_table", "xlsx_workbook", "json_recordset"]
    assert report["materialized"][0]["parser_family"] == "xlsx_workbook"
    assert run.query_plan_json["aps_table_dataset_bridge_report_refs"]["aps_table_dataset_bridge"] == summary["run_ref"]


def test_connector_table_dataset_bridge_materializes_processed_json_target(tmp_path: Path):
    db = _make_session()
    artifact_ref = tmp_path / "target-artifact.json"
    target_payload = {
        **_json_target_payload(),
        "source_reference_json": {"metadata_ref": "metadata.json"},
    }
    artifact_ref.write_text(json.dumps(target_payload), encoding="utf-8")
    run = ConnectorRun(
        connector_run_id="run-table-bridge-json",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
        selected_count=1,
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-table-bridge-json",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        artifact_surface="documents",
        status="recommended",
        source_reference_json={"aps_artifact_ingestion_ref": str(artifact_ref)},
    )
    db.add(run)
    db.add(target)
    db.commit()

    summary = connectors_nrc_adams._generate_table_dataset_bridge_artifacts(
        db,
        run=run,
        config={
            "table_dataset_bridge_enabled": True,
            "artifact_storage_dir": str(tmp_path / "storage"),
            "connector_reports_dir": str(tmp_path / "reports"),
        },
    )

    assert summary["run_outcome"] == "datasets_materialized"
    assert summary["materialized_dataset_versions"] == 1
    assert summary["failures_count"] == 0

    refreshed_target = db.get(ConnectorRunTarget, "target-table-bridge-json")
    assert refreshed_target is not None
    assert refreshed_target.dataset_id
    assert refreshed_target.dataset_version_id
    assert refreshed_target.source_reference_json["aps_table_dataset_bridge_ref"] == summary["run_ref"]
    assert refreshed_target.source_reference_json["aps_table_dataset_parser_family"] == "json_recordset"
    assert refreshed_target.source_reference_json["aps_table_dataset_typed_content_contract_id"] == "aps_json_recordset_units_v1"

    provenance = db.query(DatasetSourceProvenance).one()
    assert provenance.connector_run_id == "run-table-bridge-json"
    assert provenance.source_mode == "artifact_json_recordset_parser"

    report = json.loads(Path(str(summary["run_ref"])).read_text(encoding="utf-8"))
    assert report["schema_id"] == "aps.table_dataset_bridge_run.v1"
    assert report["supported_parser_families"] == ["csv_table", "xlsx_workbook", "json_recordset"]
    assert report["materialized"][0]["parser_family"] == "json_recordset"


def test_connector_csv_dataset_bridge_skips_non_csv_targets_without_materializing(tmp_path: Path):
    db = _make_session()
    artifact_ref = tmp_path / "target-artifact.json"
    target_payload = _csv_target_payload()
    target_payload["extraction"] = {**target_payload["extraction"], "parser_family": "plain_text"}
    artifact_ref.write_text(json.dumps(target_payload), encoding="utf-8")
    run = ConnectorRun(
        connector_run_id="run-csv-bridge-skip",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
        selected_count=1,
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-csv-bridge-skip",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        artifact_surface="documents",
        status="recommended",
        source_reference_json={"aps_artifact_ingestion_ref": str(artifact_ref)},
    )
    db.add(run)
    db.add(target)
    db.commit()

    summary = connectors_nrc_adams._generate_csv_dataset_bridge_artifacts(
        db,
        run=run,
        config={
            "csv_dataset_bridge_enabled": True,
            "artifact_storage_dir": str(tmp_path / "storage"),
            "connector_reports_dir": str(tmp_path / "reports"),
        },
    )

    assert summary["run_outcome"] == "no_csv_table_targets"
    assert summary["materialized_dataset_versions"] == 0
    assert summary["failures_count"] == 0
    refreshed_target = db.get(ConnectorRunTarget, "target-csv-bridge-skip")
    assert refreshed_target is not None
    assert refreshed_target.dataset_id is None
    assert refreshed_target.dataset_version_id is None
    report = json.loads(Path(str(summary["run_ref"])).read_text(encoding="utf-8"))
    assert report["skipped"][0]["reason"] == "not_csv_table_parser"
