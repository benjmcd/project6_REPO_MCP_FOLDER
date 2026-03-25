from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Dataset, DatasetVersion
from app.services.data_utils import parse_time_series


def _version_storage_path(version_id: str) -> Path:
    return Path(settings.dataset_storage_dir) / f"{version_id}.parquet"


def persist_dataframe_as_version_rows(db: Session, version: DatasetVersion, df: pd.DataFrame, time_column: str | None) -> None:
    frame = df.copy()
    if time_column and time_column in frame.columns:
        frame[time_column] = parse_time_series(frame[time_column], time_column)
    storage_path = _version_storage_path(version.dataset_version_id)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(storage_path, index=False)
    version.storage_ref = str(storage_path)
    version.row_count = int(len(frame))
    db.flush()


def load_version_dataframe(db: Session, dataset_version_id: str) -> pd.DataFrame:
    version = db.get(DatasetVersion, dataset_version_id)
    if not version:
        raise ValueError("dataset version not found")
    dataset = db.get(Dataset, version.dataset_id)
    storage_ref = version.storage_ref
    if not storage_ref:
        raise ValueError("dataset version has no storage_ref")
    path = Path(storage_ref)
    if not path.exists():
        raise ValueError(f"dataset storage file does not exist: {storage_ref}")
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(path)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"unsupported storage format: {suffix}")
    if dataset and dataset.time_column and dataset.time_column in df.columns:
        df[dataset.time_column] = parse_time_series(df[dataset.time_column], dataset.time_column)
    return df
