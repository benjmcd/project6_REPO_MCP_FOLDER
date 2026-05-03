from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import (
    Dataset,
    DatasetExternalIdentity,
    DatasetRow,
    DatasetSourceProvenance,
    DatasetVersion,
    SourceConnector,
    VariableDefinition,
    VariableProfile,
)
from app.services.data_utils import infer_frequency, normalize_scalar, parse_time_series
from app.services.dataframe_io import persist_dataframe_as_version_rows


APS_DATASET_BRIDGE_CONTRACT_ID = "aps_csv_dataset_bridge_v1"
APS_DATASET_BRIDGE_VERSION = "1.0.0"
APS_DATASET_BRIDGE_SOURCE_SYSTEM = "nrc_adams_aps"

_UUID_NAMESPACE = uuid.UUID("6fb6e746-3de8-4bd4-9b2b-c97df1f14f13")
_TABLE_PARSER_CONTRACTS = {
    "csv_table": {
        "typed_content_contract_id": "aps_csv_table_units_v1",
        "logical_prefix": "csv-table",
        "dataset_label": "CSV table",
        "description": "Materialized from NRC APS CSV parser diagnostics.",
        "version_label": "aps_csv_table_v1",
        "source_mode": "artifact_csv_parser",
    },
    "xlsx_workbook": {
        "typed_content_contract_id": "aps_xlsx_table_units_v1",
        "logical_prefix": "xlsx-table",
        "dataset_label": "XLSX workbook table",
        "description": "Materialized from NRC APS XLSX workbook parser diagnostics.",
        "version_label": "aps_xlsx_table_v1",
        "source_mode": "artifact_xlsx_parser",
    },
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _stable_uuid(value: str) -> str:
    return str(uuid.uuid5(_UUID_NAMESPACE, value))


def _table_units(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item or {}) for item in (extraction.get("table_units") or []) if isinstance(item, dict)]


def _rows_from_table_unit(table_unit: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item or {}) for item in (table_unit.get("rows") or []) if isinstance(item, dict)]


def _columns_from_table_unit(table_unit: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item or {}) for item in (table_unit.get("columns") or []) if isinstance(item, dict)]


def _dataframe_from_table_unit(table_unit: dict[str, Any]) -> pd.DataFrame:
    rows = _rows_from_table_unit(table_unit)
    if not rows:
        raise ValueError("dataset_bridge_table_rows_missing")
    values = [dict(row.get("values") or {}) for row in rows]
    frame = pd.DataFrame(values)
    columns = [str(column.get("name") or "").strip() for column in _columns_from_table_unit(table_unit)]
    ordered_columns = [name for name in columns if name and name in frame.columns]
    if ordered_columns:
        frame = frame[ordered_columns]
    if frame.empty:
        raise ValueError("dataset_bridge_dataframe_empty")
    return frame


def _time_column_from_extraction(extraction: dict[str, Any]) -> str | None:
    diagnostics = dict(extraction.get("table_diagnostics") or {})
    candidates = [str(item or "").strip() for item in (diagnostics.get("time_column_candidates") or [])]
    return next((item for item in candidates if item), None)


def _source_artifact_key(target_artifact_payload: dict[str, Any], *, table_index: int, table_hash: str) -> str:
    run_id = str(target_artifact_payload.get("run_id") or "").strip()
    target_id = str(target_artifact_payload.get("target_id") or "").strip()
    extraction = dict(target_artifact_payload.get("extraction") or {})
    parser_contract_id = str(extraction.get("parser_contract_id") or "").strip()
    blob_sha = str((target_artifact_payload.get("download") or {}).get("blob_sha256") or "").strip()
    return ":".join(
        [
            "nrc_adams_aps",
            run_id or "unknown-run",
            target_id or "unknown-target",
            blob_sha or "unknown-blob",
            parser_contract_id or "unknown-parser",
            f"table-{table_index}",
            table_hash,
        ]
    )


def _source_connector(db: Session) -> SourceConnector:
    existing = (
        db.query(SourceConnector)
        .filter(
            and_(
                SourceConnector.source_name == "nrc_adams_aps",
                SourceConnector.source_category == "connector_artifact",
            )
        )
        .first()
    )
    if existing:
        return existing
    connector = SourceConnector(
        source_name="nrc_adams_aps",
        source_category="connector_artifact",
        automation_tier="tier_1",
        api_available_flag=True,
        domain_pack="nrc_aps",
    )
    db.add(connector)
    db.flush()
    return connector


def _column_dtype(column: dict[str, Any], *, is_time: bool) -> str:
    if is_time:
        return "datetime64[ns]"
    kind = str(column.get("kind") or "").strip()
    if kind == "integer":
        return "int64"
    if kind == "number":
        return "float64"
    if kind == "boolean":
        return "bool"
    return "object"


def _coerce_frame(frame: pd.DataFrame, columns: list[dict[str, Any]], time_column: str | None) -> pd.DataFrame:
    coerced = frame.copy()
    for column in columns:
        name = str(column.get("name") or "").strip()
        if not name or name not in coerced.columns:
            continue
        kind = str(column.get("kind") or "").strip()
        if name == time_column:
            coerced[name] = parse_time_series(coerced[name], name)
        elif kind in {"integer", "number"}:
            coerced[name] = pd.to_numeric(coerced[name], errors="coerce")
        elif kind == "boolean":
            coerced[name] = coerced[name].map(lambda value: str(value).strip().lower() in {"true", "yes"})
    return coerced


def _write_dataset_rows(db: Session, *, version: DatasetVersion, frame: pd.DataFrame, time_column: str | None) -> None:
    db.query(DatasetRow).filter(DatasetRow.dataset_version_id == version.dataset_version_id).delete()
    for index, row in enumerate(frame.to_dict(orient="records"), start=1):
        observed_at = None
        if time_column and time_column in row and pd.notna(row[time_column]):
            observed_at = pd.Timestamp(row[time_column]).to_pydatetime()
        db.add(
            DatasetRow(
                dataset_version_id=version.dataset_version_id,
                row_number=index,
                observed_at=observed_at,
                values_json={key: normalize_scalar(value) for key, value in row.items()},
            )
        )


def _write_variable_profiles(db: Session, *, version: DatasetVersion, frame: pd.DataFrame) -> None:
    variables = (
        db.query(VariableDefinition)
        .filter(VariableDefinition.dataset_version_id == version.dataset_version_id)
        .order_by(VariableDefinition.ordinal_position.asc())
        .all()
    )
    db.query(VariableProfile).filter(VariableProfile.dataset_version_id == version.dataset_version_id).delete()
    for variable in variables:
        if not variable.is_numeric or variable.is_time_index or variable.variable_name not in frame.columns:
            continue
        series = pd.to_numeric(frame[variable.variable_name], errors="coerce")
        clean = series.dropna()
        if clean.empty:
            continue
        db.add(
            VariableProfile(
                dataset_version_id=version.dataset_version_id,
                variable_id=variable.variable_id,
                missingness_rate=float(series.isna().mean()),
                mean_value=float(clean.mean()),
                median_value=float(clean.median()),
                min_value=float(clean.min()),
                max_value=float(clean.max()),
                std_dev=float(clean.std()) if len(clean) > 1 else 0.0,
                negative_values_flag=bool((clean < 0).any()),
                zero_values_flag=bool((clean == 0).any()),
                bounded_flag=False,
                seasonality_flag=False,
                summary_json={
                    "dataset_bridge_contract_id": APS_DATASET_BRIDGE_CONTRACT_ID,
                    "n": int(len(clean)),
                    "unique_n": int(clean.nunique(dropna=True)),
                },
            )
        )


def _persist_bridge_frame(
    db: Session,
    *,
    version: DatasetVersion,
    frame: pd.DataFrame,
    time_column: str | None,
    artifact_storage_dir: str | Path | None,
) -> None:
    if artifact_storage_dir:
        output_dir = Path(artifact_storage_dir) / "datasets"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{version.dataset_version_id}.parquet"
        stored = frame.copy()
        if time_column and time_column in stored.columns:
            stored[time_column] = parse_time_series(stored[time_column], time_column)
        stored.to_parquet(output_path, index=False)
        version.storage_ref = str(output_path)
        version.row_count = int(len(stored))
        db.flush()
        return
    persist_dataframe_as_version_rows(db, version, frame, time_column)


def materialize_table_unit_dataset(
    db: Session,
    *,
    target_artifact_payload: dict[str, Any],
    artifact_storage_dir: str | Path | None = None,
    connector_run_id: str | None = None,
    table_index: int = 1,
    commit: bool = True,
) -> dict[str, Any]:
    extraction = dict(target_artifact_payload.get("extraction") or {})
    parser_family = str(extraction.get("parser_family") or "").strip()
    parser_contract = _TABLE_PARSER_CONTRACTS.get(parser_family)
    if parser_contract is None:
        raise ValueError("dataset_bridge_requires_csv_table_parser")
    if str(extraction.get("typed_content_contract_id") or "").strip() != parser_contract["typed_content_contract_id"]:
        raise ValueError("dataset_bridge_requires_csv_table_contract")

    units = _table_units(extraction)
    table_unit = next((unit for unit in units if int(unit.get("table_index") or 0) == int(table_index)), None)
    if table_unit is None:
        raise ValueError("dataset_bridge_table_unit_missing")

    rows = _rows_from_table_unit(table_unit)
    columns = _columns_from_table_unit(table_unit)
    table_hash = _stable_hash({"columns": columns, "rows": rows})
    source_artifact_key = _source_artifact_key(
        target_artifact_payload,
        table_index=int(table_index),
        table_hash=table_hash,
    )
    dataset_id = _stable_uuid(f"dataset:{source_artifact_key}")
    version_id = _stable_uuid(f"dataset-version:{source_artifact_key}")
    logical_dataset_key = f"{parser_contract['logical_prefix']}:{source_artifact_key}"

    existing_version = db.get(DatasetVersion, version_id)
    if existing_version is not None:
        return {
            "dataset_bridge_contract_id": APS_DATASET_BRIDGE_CONTRACT_ID,
            "dataset_bridge_version": APS_DATASET_BRIDGE_VERSION,
            "created": False,
            "dataset_id": existing_version.dataset_id,
            "dataset_version_id": existing_version.dataset_version_id,
            "source_artifact_key": source_artifact_key,
            "row_count": existing_version.row_count,
        }

    frame = _dataframe_from_table_unit(table_unit)
    time_column = _time_column_from_extraction(extraction)
    frame = _coerce_frame(frame, columns, time_column)
    frequency_hint = infer_frequency(frame[time_column]) if time_column and time_column in frame.columns else None

    connector = _source_connector(db)
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        dataset = Dataset(
            dataset_id=dataset_id,
            source_id=connector.source_id,
            name=f"APS {parser_contract['dataset_label']} {target_artifact_payload.get('target_id') or table_index}",
            description=parser_contract["description"],
            domain_pack="nrc_aps",
            frequency_hint=frequency_hint,
            time_column=time_column,
        )
        db.add(dataset)
        db.flush()

    version = DatasetVersion(
        dataset_version_id=version_id,
        dataset_id=dataset.dataset_id,
        version_label=parser_contract["version_label"],
        version_type="raw",
        status="ready",
        notes=(
            f"{APS_DATASET_BRIDGE_CONTRACT_ID}; parser_contract_id={extraction.get('parser_contract_id')}; "
            f"source_artifact_key={source_artifact_key}"
        ),
    )
    db.add(version)
    db.flush()

    for index, column in enumerate(columns):
        name = str(column.get("name") or "").strip()
        if not name:
            continue
        is_time = name == time_column
        kind = str(column.get("kind") or "").strip()
        is_numeric = kind in {"integer", "number"} and not is_time
        db.add(
            VariableDefinition(
                dataset_version_id=version.dataset_version_id,
                variable_name=name,
                dtype=_column_dtype(column, is_time=is_time),
                role="time_index" if is_time else "measure",
                is_numeric=is_numeric,
                is_time_index=is_time,
                ordinal_position=index,
            )
        )

    _persist_bridge_frame(
        db,
        version=version,
        frame=frame,
        time_column=time_column,
        artifact_storage_dir=artifact_storage_dir,
    )
    _write_dataset_rows(db, version=version, frame=frame, time_column=time_column)
    _write_variable_profiles(db, version=version, frame=frame)

    existing_identity = (
        db.query(DatasetExternalIdentity)
        .filter(
            and_(
                DatasetExternalIdentity.source_system == APS_DATASET_BRIDGE_SOURCE_SYSTEM,
                DatasetExternalIdentity.logical_dataset_key == logical_dataset_key,
            )
        )
        .first()
    )
    if existing_identity is None:
        db.add(
            DatasetExternalIdentity(
                dataset_id=dataset.dataset_id,
                source_system=APS_DATASET_BRIDGE_SOURCE_SYSTEM,
                logical_dataset_key=logical_dataset_key,
                metadata_json={
                    "dataset_bridge_contract_id": APS_DATASET_BRIDGE_CONTRACT_ID,
                    "dataset_bridge_version": APS_DATASET_BRIDGE_VERSION,
                    "table_hash": table_hash,
                    "parser_family": extraction.get("parser_family"),
                    "parser_contract_id": extraction.get("parser_contract_id"),
                    "typed_content_contract_id": extraction.get("typed_content_contract_id"),
                },
            )
        )

    download = dict(target_artifact_payload.get("download") or {})
    source_reference = dict(target_artifact_payload.get("source_reference_json") or {})
    db.add(
        DatasetSourceProvenance(
            dataset_version_id=version.dataset_version_id,
            connector_run_id=str(connector_run_id or "").strip() or None,
            source_system=APS_DATASET_BRIDGE_SOURCE_SYSTEM,
            source_mode=parser_contract["source_mode"],
            source_artifact_key=source_artifact_key,
            sciencebase_file_name=str(extraction.get("source_filename") or "").strip() or None,
            downloaded_sha256=str(download.get("blob_sha256") or "").strip() or None,
            raw_storage_ref=str(download.get("blob_ref") or "").strip() or None,
            source_reference_json={
                **source_reference,
                "target_id": target_artifact_payload.get("target_id"),
                "accession_number": target_artifact_payload.get("accession_number"),
                "table_index": int(table_index),
                "table_hash": table_hash,
                "parser_family": extraction.get("parser_family"),
                "parser_contract_id": extraction.get("parser_contract_id"),
                "typed_content_contract_id": extraction.get("typed_content_contract_id"),
                "diagnostics_ref": extraction.get("diagnostics_ref"),
            },
            retrieved_http_json={"content_type": (download.get("content_type") or extraction.get("effective_content_type"))},
            downloaded_at=datetime.now().astimezone(),
        )
    )

    if commit:
        db.commit()
        db.refresh(version)
    else:
        db.flush()

    return {
        "dataset_bridge_contract_id": APS_DATASET_BRIDGE_CONTRACT_ID,
        "dataset_bridge_version": APS_DATASET_BRIDGE_VERSION,
        "created": True,
        "dataset_id": dataset.dataset_id,
        "dataset_version_id": version.dataset_version_id,
        "source_artifact_key": source_artifact_key,
        "row_count": int(version.row_count or 0),
        "time_column": time_column,
        "numeric_columns": [
            str(column.get("name") or "")
            for column in columns
            if str(column.get("kind") or "") in {"integer", "number"} and str(column.get("name") or "") != time_column
        ],
        "storage_ref": version.storage_ref,
    }


def materialize_csv_table_dataset(
    db: Session,
    *,
    target_artifact_payload: dict[str, Any],
    artifact_storage_dir: str | Path | None = None,
    connector_run_id: str | None = None,
    table_index: int = 1,
    commit: bool = True,
) -> dict[str, Any]:
    return materialize_table_unit_dataset(
        db,
        target_artifact_payload=target_artifact_payload,
        artifact_storage_dir=artifact_storage_dir,
        connector_run_id=connector_run_id,
        table_index=table_index,
        commit=commit,
    )
