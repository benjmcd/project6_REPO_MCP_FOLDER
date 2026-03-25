from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Dataset, DatasetVersion, SourceConnector, VariableDefinition
from app.services.data_utils import clean_dataframe, infer_frequency, infer_time_column, is_semantically_numeric, parse_time_series
from app.services.dataframe_io import persist_dataframe_as_version_rows


CSV_READ_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin1")


def _safe_filename(name: str) -> str:
    base = Path(name or "uploaded.csv").name.strip() or "uploaded.csv"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    return safe or "uploaded.csv"


def _read_csv_with_fallback(raw_path: Path) -> tuple[pd.DataFrame, str]:
    decode_failures: list[str] = []
    for encoding in CSV_READ_ENCODINGS:
        try:
            return pd.read_csv(raw_path, encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            decode_failures.append(f"{encoding}: {exc}")
        except Exception as exc:
            raise ValueError(f"parse failed with encoding {encoding}: {exc}") from exc
    last_error = decode_failures[-1] if decode_failures else "unknown decoding error"
    tried = ", ".join(CSV_READ_ENCODINGS)
    raise ValueError(f"unable to decode CSV with tried encodings: {tried}; last_error={last_error}")


def _next_version_label(db: Session, dataset_id: str) -> str:
    count = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).count()
    return f"raw_v{count + 1}"


def ingest_csv_bytes_to_dataset(
    db: Session,
    *,
    filename: str,
    content: bytes,
    name: str,
    description: str | None,
    domain_pack: str | None,
    primary_time_column: str | None,
    dataset_id: str | None = None,
    source_name: str = "file_upload",
    source_category: str = "upload",
    source_notes: str | None = None,
    version_label: str | None = None,
) -> dict[str, object]:
    safe_name = _safe_filename(filename)
    if not safe_name.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="only CSV upload is supported in this starter")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="file exceeds configured upload limit")

    raw_dir = Path(settings.raw_storage_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_path = raw_dir / f"{stamp}_{safe_name}"
    raw_path.write_bytes(content)

    try:
        df, used_encoding = _read_csv_with_fallback(raw_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"unable to parse CSV: {exc}") from exc

    df = clean_dataframe(df)
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV contains no non-empty rows")

    dataset: Dataset | None = db.get(Dataset, dataset_id) if dataset_id else None
    if dataset is None:
        source = SourceConnector(
            source_name=source_name,
            source_category=source_category,
            automation_tier="tier_0",
            api_available_flag=False,
            domain_pack=domain_pack,
        )
        db.add(source)
        db.flush()
        time_column = infer_time_column(df, primary_time_column)
        frequency_hint = None
        if time_column:
            df[time_column] = parse_time_series(df[time_column], time_column)
            frequency_hint = infer_frequency(df[time_column])
        dataset = Dataset(
            source_id=source.source_id,
            name=name,
            description=description,
            domain_pack=domain_pack,
            frequency_hint=frequency_hint,
            time_column=time_column,
        )
        db.add(dataset)
        db.flush()
    else:
        time_column = dataset.time_column or infer_time_column(df, primary_time_column)
        if time_column:
            df[time_column] = parse_time_series(df[time_column], time_column)
        if not dataset.time_column:
            dataset.time_column = time_column
        if not dataset.frequency_hint and time_column:
            dataset.frequency_hint = infer_frequency(df[time_column])

    label = version_label or _next_version_label(db, dataset.dataset_id)
    note_parts = [
        f"raw uploaded dataset; source_csv={raw_path}",
        f"csv_encoding={used_encoding}",
    ]
    if source_notes:
        note_parts.append(source_notes)
    version = DatasetVersion(
        dataset_id=dataset.dataset_id,
        version_label=label,
        version_type="raw",
        status="ready",
        notes="; ".join(note_parts),
    )
    db.add(version)
    db.flush()

    numeric_variables: list[str] = []
    for idx, column in enumerate(df.columns):
        is_time = column == time_column
        is_numeric = False if is_time else is_semantically_numeric(df[column])
        if is_numeric:
            numeric_variables.append(str(column))
        dtype_name = "datetime64[ns]" if is_time else ("float64" if is_numeric else str(df[column].dtype))
        db.add(
            VariableDefinition(
                dataset_version_id=version.dataset_version_id,
                variable_name=str(column),
                dtype=dtype_name,
                role="time_index" if is_time else "measure",
                is_numeric=is_numeric,
                is_time_index=is_time,
                ordinal_position=idx,
            )
        )
    persist_dataframe_as_version_rows(db, version, df, time_column)
    db.commit()
    db.refresh(version)
    return {
        "dataset_id": dataset.dataset_id,
        "dataset_version_id": version.dataset_version_id,
        "dataset_name": dataset.name,
        "row_count": version.row_count,
        "time_column": time_column,
        "numeric_variables": numeric_variables,
        "csv_encoding": used_encoding,
        "storage_ref": version.storage_ref,
    }


def upload_csv_to_dataset(
    db: Session,
    file: UploadFile,
    name: str,
    description: str | None,
    domain_pack: str | None,
    primary_time_column: str | None,
) -> dict[str, object]:
    content = file.file.read()
    return ingest_csv_bytes_to_dataset(
        db,
        filename=file.filename or "uploaded.csv",
        content=content,
        name=name,
        description=description,
        domain_pack=domain_pack,
        primary_time_column=primary_time_column,
        source_name="file_upload",
        source_category="upload",
    )
