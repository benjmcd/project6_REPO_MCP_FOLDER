from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd

PLACEHOLDER_NULLS = {
    "",
    "na",
    "n/a",
    "nan",
    "none",
    "null",
    "--",
    "—",
    "w",
    "withheld",
    "withheld to avoid disclosing company proprietary data",
    "e",
    "est",
    "estimated",
}

LESS_THAN_HALF_RE = re.compile(r"less than\s+1/2\s+unit\.?", re.IGNORECASE)
YEAR_TEXT_RE = re.compile(r"^\s*(\d{4})(?:[_\-\s]?(?:estimated|est))?\s*$", re.IGNORECASE)
TIME_NAME_RE = re.compile(r"(?:^|_)(year|date|datetime|timestamp|time|period|month|quarter)(?:$|_)", re.IGNORECASE)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for col in cleaned.columns:
        if cleaned[col].dtype == object:
            cleaned[col] = cleaned[col].map(lambda x: x.strip() if isinstance(x, str) else x)
            cleaned[col] = cleaned[col].replace(r"^\s*$", np.nan, regex=True)
    unnamed_drop = [c for c in cleaned.columns if str(c).startswith("Unnamed:") and cleaned[c].isna().all()]
    if unnamed_drop:
        cleaned = cleaned.drop(columns=unnamed_drop)
    cleaned = cleaned.dropna(axis=0, how="all").reset_index(drop=True)
    return cleaned


def time_like_column_name(column_name: str) -> bool:
    return bool(TIME_NAME_RE.search(column_name.strip().lower()))


def parse_time_series(series: pd.Series, column_name: str | None = None) -> pd.Series:
    s = series.copy()
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce")
    if s.dtype == object:
        s = s.map(lambda x: x.strip() if isinstance(x, str) else x)

    non_null = s.dropna()
    if non_null.empty:
        return pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    name = (column_name or "").strip().lower()

    if pd.api.types.is_numeric_dtype(non_null):
        numeric = pd.to_numeric(non_null, errors="coerce")
        is_yearish = numeric.notna().mean() >= 0.95 and numeric.between(1500, 2500).mean() >= 0.95
        if name == "year" or "year" in name or is_yearish:
            years = numeric.round().astype("Int64")
            parsed_non_null = pd.to_datetime(years.astype(str), format="%Y", errors="coerce")
            out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
            out.loc[non_null.index] = parsed_non_null.to_numpy()
            return out
        return pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    text_values = non_null.astype(str)
    year_matches = text_values.str.extract(YEAR_TEXT_RE, expand=False)
    year_match_ratio = year_matches.notna().mean()
    if name == "year" or "year" in name or year_match_ratio >= 0.95:
        years = pd.to_numeric(year_matches, errors="coerce")
        parsed_non_null = pd.to_datetime(years.astype("Int64").astype(str), format="%Y", errors="coerce")
        out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        out.loc[non_null.index] = parsed_non_null.to_numpy()
        return out

    dateish_ratio = text_values.str.contains(r"[-/:]|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|q[1-4]", case=False, regex=True).mean()
    if dateish_ratio < 0.8 and not time_like_column_name(name):
        return pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    return pd.to_datetime(s, errors="coerce")


def infer_time_column(df: pd.DataFrame, explicit: str | None) -> str | None:
    if explicit and explicit in df.columns:
        return explicit
    named_candidates = [c for c in df.columns if time_like_column_name(str(c))]
    for col in named_candidates:
        parsed = parse_time_series(df[col], col)
        if parsed.notna().mean() >= 0.8:
            return col
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            continue
        parsed = parse_time_series(series, str(col))
        if parsed.notna().mean() >= 0.9:
            return col
    return None


def infer_frequency(parsed_time: pd.Series) -> str | None:
    clean = pd.Series(parsed_time).dropna().sort_values()
    if len(clean) < 3:
        return None
    diffs = clean.diff().dropna()
    if diffs.empty:
        return None
    if diffs.dt.days.nunique() == 1:
        days = int(diffs.dt.days.iloc[0])
        if 360 <= days <= 370:
            return "YS"
        if 27 <= days <= 31:
            return "MS"
        if days == 1:
            return "D"
        if 6 <= days <= 8:
            return "W"
    try:
        return pd.infer_freq(clean)
    except Exception:
        return None


def normalize_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def _parse_numeric_string_token(text: str) -> float | None:
    raw = text.strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in PLACEHOLDER_NULLS:
        return None
    if LESS_THAN_HALF_RE.fullmatch(lowered):
        return 0.5
    raw = raw.replace(",", "").replace("%", "").strip()
    if raw.startswith((">", "<", "~")):
        raw = raw[1:].strip()
    match = re.match(r"^[-+]?\d+(?:\.\d+)?$", raw)
    if match:
        return float(raw)
    return None


def classify_numeric_token(value: Any) -> dict[str, Any]:
    if value is None or pd.isna(value):
        return {"status": "null", "normalized_value": None, "token": None}
    if isinstance(value, (int, float, np.number)) and not isinstance(value, bool):
        numeric = float(value)
        return {"status": "numeric", "normalized_value": numeric, "token": None}
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if lowered in PLACEHOLDER_NULLS:
            return {"status": "placeholder_null", "normalized_value": None, "token": stripped}
        if LESS_THAN_HALF_RE.fullmatch(lowered):
            return {"status": "threshold_proxy", "normalized_value": 0.5, "token": stripped}
        raw = stripped.replace(",", "").replace("%", "").strip()
        if raw.startswith((">", "<", "~")):
            parsed = _parse_numeric_string_token(stripped)
            return {"status": "inequality_proxy", "normalized_value": parsed, "token": stripped}
        parsed = _parse_numeric_string_token(stripped)
        if parsed is not None:
            return {"status": "numeric_string", "normalized_value": parsed, "token": stripped}
        return {"status": "non_numeric", "normalized_value": None, "token": stripped}
    return {"status": "non_numeric", "normalized_value": None, "token": None}


def coerce_numeric_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    def convert(value: Any) -> float | None:
        info = classify_numeric_token(value)
        parsed = info["normalized_value"]
        return np.nan if parsed is None else parsed

    coerced = series.map(convert)
    return pd.to_numeric(coerced, errors="coerce")


def numeric_token_summary(series: pd.Series) -> dict[str, Any]:
    if pd.api.types.is_numeric_dtype(series):
        return {"placeholder_count": 0, "proxy_count": 0, "non_numeric_count": 0, "examples": []}
    statuses = []
    examples: list[str] = []
    for value in series.dropna().tolist():
        info = classify_numeric_token(value)
        statuses.append(info["status"])
        token = info.get("token")
        if info["status"] in {"placeholder_null", "threshold_proxy", "inequality_proxy", "non_numeric"} and token and token not in examples:
            examples.append(token)
        if len(examples) >= 5:
            break
    return {
        "placeholder_count": int(sum(1 for s in statuses if s == "placeholder_null")),
        "proxy_count": int(sum(1 for s in statuses if s in {"threshold_proxy", "inequality_proxy"})),
        "non_numeric_count": int(sum(1 for s in statuses if s == "non_numeric")),
        "examples": examples,
    }


def is_semantically_numeric(series: pd.Series, min_ratio: float = 0.65) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    non_null = series.dropna()
    if non_null.empty:
        return False
    coerced = coerce_numeric_series(series)
    ratio = coerced.notna().sum() / len(non_null)
    return ratio >= min_ratio
