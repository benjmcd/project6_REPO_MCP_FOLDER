from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import skew
from sqlalchemy.orm import Session
from statsmodels.tsa.stattools import adfuller, kpss

from app.models import DatasetVersion, VariableDefinition, VariableProfile
from app.services.data_utils import coerce_numeric_series, numeric_token_summary
from app.services.dataframe_io import load_version_dataframe


def _detect_seasonality(series: pd.Series) -> tuple[bool, dict]:
    clean = series.dropna().reset_index(drop=True)
    if len(clean) < 24:
        return False, {"method": "autocorr_grid", "tested_lags": [], "best_lag": None, "best_autocorr": None, "note": "insufficient_observations"}
    max_lag = min(24, max(2, len(clean) // 3))
    candidate_lags = [lag for lag in range(2, max_lag + 1) if len(clean) > lag * 2]
    if not candidate_lags:
        return False, {"method": "autocorr_grid", "tested_lags": [], "best_lag": None, "best_autocorr": None, "note": "no_valid_lags"}
    scored: list[tuple[float, int]] = []
    for lag in candidate_lags:
        ac = clean.autocorr(lag=lag)
        if ac is None or pd.isna(ac):
            continue
        scored.append((abs(float(ac)), lag))
    if not scored:
        return False, {"method": "autocorr_grid", "tested_lags": candidate_lags, "best_lag": None, "best_autocorr": None, "note": "all_nan"}
    best_abs, best_lag = max(scored)
    best_ac = float(clean.autocorr(lag=best_lag))
    return bool(best_abs >= 0.45), {"method": "autocorr_grid", "tested_lags": candidate_lags, "best_lag": best_lag, "best_autocorr": best_ac}


def _detect_stationarity(series: pd.Series) -> tuple[str, dict]:
    clean = series.dropna().astype(float)
    if len(clean) < 12:
        return "insufficient_data", {"method": "adf_kpss", "note": "fewer_than_12_non_null_points"}
    if clean.nunique(dropna=True) <= 1:
        return "constant_series", {"method": "adf_kpss", "note": "constant_series"}
    summary: dict[str, object] = {"method": "adf_kpss"}
    adf_pass = None
    kpss_pass = None
    try:
        adf_stat, adf_pvalue, used_lag, nobs, _, _ = adfuller(clean, autolag="AIC")
        summary["adf"] = {"stat": float(adf_stat), "pvalue": float(adf_pvalue), "usedlag": int(used_lag), "nobs": int(nobs)}
        adf_pass = adf_pvalue < 0.05
    except Exception as exc:
        summary["adf"] = {"error": str(exc)}
    try:
        regression = "ct" if len(clean) >= 24 else "c"
        kpss_stat, kpss_pvalue, used_lag, _ = kpss(clean, regression=regression, nlags="auto")
        summary["kpss"] = {"stat": float(kpss_stat), "pvalue": float(kpss_pvalue), "usedlag": int(used_lag), "regression": regression}
        kpss_pass = kpss_pvalue > 0.05
    except Exception as exc:
        summary["kpss"] = {"error": str(exc)}
    if adf_pass is True and kpss_pass is True:
        return "likely_stationary", summary
    if adf_pass is False and kpss_pass is False:
        return "likely_nonstationary", summary
    if adf_pass is True and kpss_pass is False:
        return "trend_stationary_or_mixed", summary
    if adf_pass is False and kpss_pass is True:
        return "mixed_or_borderline", summary
    return "inconclusive", summary


def profile_dataset_version(db: Session, dataset_version_id: str, detect_seasonality: bool = True, detect_stationarity: bool = False) -> list[VariableProfile]:
    version = db.get(DatasetVersion, dataset_version_id)
    if not version:
        raise ValueError('dataset version not found')
    df = load_version_dataframe(db, dataset_version_id)
    variables = db.query(VariableDefinition).filter(VariableDefinition.dataset_version_id == dataset_version_id).order_by(VariableDefinition.ordinal_position.asc()).all()
    db.query(VariableProfile).filter(VariableProfile.dataset_version_id == dataset_version_id).delete()
    created: list[VariableProfile] = []
    for var in variables:
        if not var.is_numeric or var.is_time_index or var.variable_name not in df.columns:
            continue
        raw_series = df[var.variable_name]
        series = coerce_numeric_series(raw_series)
        clean = series.dropna()
        if clean.empty:
            continue
        q1 = clean.quantile(0.25)
        q3 = clean.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_fraction = float(((clean < lower) | (clean > upper)).mean()) if len(clean) else 0.0
        min_val = float(clean.min())
        max_val = float(clean.max())
        skewness = float(skew(clean, bias=False)) if len(clean) > 2 and float(clean.std(ddof=1)) > 0 else 0.0
        seasonal_flag = None
        seasonality_summary: dict | None = None
        if detect_seasonality:
            seasonal_flag, seasonality_summary = _detect_seasonality(clean)
        stationarity_hint = None
        stationarity_summary: dict | None = None
        if detect_stationarity:
            stationarity_hint, stationarity_summary = _detect_stationarity(clean)
        token_summary = numeric_token_summary(raw_series)
        bounded_flag = False
        profile = VariableProfile(
            dataset_version_id=dataset_version_id,
            variable_id=var.variable_id,
            missingness_rate=float(series.isna().mean()),
            mean_value=float(clean.mean()),
            median_value=float(clean.median()),
            min_value=min_val,
            max_value=max_val,
            std_dev=float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
            skewness=skewness,
            outlier_fraction=outlier_fraction,
            negative_values_flag=bool((clean < 0).any()),
            zero_values_flag=bool((clean == 0).any()),
            bounded_flag=bounded_flag,
            seasonality_flag=seasonal_flag,
            stationarity_hint=stationarity_hint,
            summary_json={
                'q1': float(q1),
                'q3': float(q3),
                'iqr': float(iqr),
                'n': int(len(clean)),
                'unique_n': int(clean.nunique(dropna=True)),
                'range_width': float(max_val - min_val),
                'seasonality': seasonality_summary,
                'stationarity': stationarity_summary,
                'token_summary': token_summary,
            },
        )
        db.add(profile)
        created.append(profile)
    db.commit()
    for item in created:
        db.refresh(item)
    return created
