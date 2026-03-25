from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ruptures as rpt
from sqlalchemy.orm import Session
from statsmodels.tsa.seasonal import STL

from app.core.config import settings
from app.models import AnalysisArtifact, AnalysisRun, AnnotationWindow, AssumptionCheck, CaveatNote, Dataset, DatasetVersion, VariableDefinition, VariableProfile
from app.services.data_utils import coerce_numeric_series
from app.services.dataframe_io import load_version_dataframe
from app.services.profiling import _detect_stationarity

NONSTATIONARY_HINTS = {'likely_nonstationary', 'trend_stationary_or_mixed'}
WARN_STATIONARITY_HINTS = {'mixed_or_borderline', 'inconclusive', 'insufficient_data'}


def _artifact_dir() -> Path:
    path = Path(settings.artifact_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_storage_path(storage_ref: str) -> Path:
    return _artifact_dir() / Path(storage_ref).name


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def _persist_artifact_json(run: AnalysisRun, artifact_type: str, title: str, payload: dict[str, Any], summary: str | None = None) -> AnalysisArtifact:
    artifact_path = _artifact_dir() / f'{artifact_type}_{run.analysis_run_id}_{uuid.uuid4().hex[:8]}.json'
    artifact_path.write_text(json.dumps(payload, indent=2, default=_json_default))
    artifact = AnalysisArtifact(
        analysis_run_id=run.analysis_run_id,
        artifact_type=artifact_type,
        title=title,
        storage_ref=f'/storage/artifacts/{artifact_path.name}',
        summary=summary,
        metadata_json=payload.get('summary_stats', {}),
    )
    return artifact


def _persist_artifact_png(run: AnalysisRun, artifact_type: str, title: str, fig: plt.Figure, metadata: dict[str, Any], summary: str | None = None) -> AnalysisArtifact:
    artifact_path = _artifact_dir() / f'{artifact_type}_{run.analysis_run_id}_{uuid.uuid4().hex[:8]}.png'
    fig.tight_layout()
    fig.savefig(artifact_path)
    plt.close(fig)
    artifact = AnalysisArtifact(
        analysis_run_id=run.analysis_run_id,
        artifact_type=artifact_type,
        title=title,
        storage_ref=f'/storage/artifacts/{artifact_path.name}',
        summary=summary,
        metadata_json=metadata,
    )
    return artifact


def _profile_maps(db: Session, dataset_version_id: str) -> tuple[dict[str, VariableProfile], list[VariableDefinition], list[str], bool]:
    variables = db.query(VariableDefinition).filter(VariableDefinition.dataset_version_id == dataset_version_id).order_by(VariableDefinition.ordinal_position.asc()).all()
    profile_rows = db.query(VariableProfile, VariableDefinition).join(VariableDefinition, VariableProfile.variable_id == VariableDefinition.variable_id).filter(VariableProfile.dataset_version_id == dataset_version_id).all()
    profile_map = {var.variable_name: profile for profile, var in profile_rows}
    numeric_cols = [v.variable_name for v in variables if v.is_numeric and not v.is_time_index]
    has_time = any(v.is_time_index for v in variables)
    return profile_map, variables, numeric_cols, has_time


def recommend_analysis(db: Session, dataset_version_id: str, goal_type: str | None = None) -> dict[str, Any]:
    version = db.get(DatasetVersion, dataset_version_id)
    if not version:
        raise ValueError('dataset version not found')
    profile_map, variables, numeric_cols, has_time = _profile_maps(db, dataset_version_id)
    stationary_like = [name for name in numeric_cols if name in profile_map and profile_map[name].stationarity_hint == 'likely_stationary']
    mixed_like = [name for name in numeric_cols if name in profile_map and profile_map[name].stationarity_hint in NONSTATIONARY_HINTS | WARN_STATIONARITY_HINTS]
    seasonal_like = [name for name in numeric_cols if name in profile_map and bool(profile_map[name].seasonality_flag)]

    if has_time and len(numeric_cols) >= 2:
        sequence = ['cross_correlation', 'decomposition', 'structural_break']
        if seasonal_like and mixed_like:
            rationale = 'time-indexed multivariate data supports lag inspection, decomposition, and break detection; seasonality is present and nonstationary variables require caution'
        elif seasonal_like:
            rationale = 'time-indexed multivariate data with seasonal structure supports lag inspection, decomposition, and break detection'
        elif mixed_like:
            rationale = 'time-indexed multivariate data supports lag inspection, decomposition, and break detection, but mixed or nonstationary profiles increase caveat severity'
        else:
            rationale = 'time-indexed multivariate data supports lag inspection, decomposition, and break detection on the starter spine'
    elif has_time and len(numeric_cols) == 1:
        sequence = ['decomposition', 'structural_break']
        rationale = 'single numeric time series should be decomposed first and then checked for structural breaks'
    else:
        sequence = ['descriptive_summary']
        rationale = 'dataset does not meet starter time-series assumptions for decomposition or break detection'
    return {
        'dataset_version_id': dataset_version_id,
        'recommended_sequence': sequence,
        'rationale': rationale,
        'profile_context': {
            'stationary_like_variables': stationary_like,
            'mixed_or_nonstationary_variables': mixed_like,
            'seasonal_like_variables': seasonal_like,
        },
    }


def _apply_window(df: pd.DataFrame, dataset: Dataset, window: AnnotationWindow | None) -> pd.DataFrame:
    if window is None or not dataset.time_column or dataset.time_column not in df.columns:
        return df
    time_values = pd.to_datetime(df[dataset.time_column], errors='coerce', utc=True)
    start = pd.Timestamp(window.start_time)
    end = pd.Timestamp(window.end_time)
    if start.tzinfo is None:
        start = start.tz_localize('UTC')
    else:
        start = start.tz_convert('UTC')
    if end.tzinfo is None:
        end = end.tz_localize('UTC')
    else:
        end = end.tz_convert('UTC')
    return df[(time_values >= start) & (time_values <= end)].copy()


def _pairwise_lag_correlation(series_a: pd.Series, series_b: pd.Series, max_lag: int) -> dict[int, float | None]:
    out: dict[int, float | None] = {}
    a = coerce_numeric_series(series_a).reset_index(drop=True)
    b = coerce_numeric_series(series_b).reset_index(drop=True)
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            left = a[:lag].reset_index(drop=True)
            right = b[-lag:].reset_index(drop=True)
        elif lag > 0:
            left = a[lag:].reset_index(drop=True)
            right = b[:-lag].reset_index(drop=True)
        else:
            left = a
            right = b
        pair = pd.concat([left, right], axis=1).dropna()
        if len(pair) < 2 or pair.iloc[:, 0].nunique() <= 1 or pair.iloc[:, 1].nunique() <= 1:
            out[lag] = None
            continue
        corr = pair.iloc[:, 0].corr(pair.iloc[:, 1])
        out[lag] = None if pd.isna(corr) else float(corr)
    return out


def _get_time_frame(df: pd.DataFrame, dataset: Dataset, variable_name: str) -> pd.DataFrame:
    if not dataset.time_column or dataset.time_column not in df.columns:
        return pd.DataFrame(columns=['time', 'value'])
    time_values = pd.to_datetime(df[dataset.time_column], errors='coerce', utc=True)
    values = coerce_numeric_series(df[variable_name])
    frame = pd.DataFrame({'time': time_values, 'value': values}).dropna().sort_values('time').reset_index(drop=True)
    return frame


def _time_regularity(time_values: pd.Series) -> tuple[str, dict[str, Any], str | None]:
    clean = pd.to_datetime(time_values, errors='coerce', utc=True).dropna().sort_values().reset_index(drop=True)
    if len(clean) < 3:
        return 'warn', {'note': 'fewer_than_3_timestamps'}, None
    if clean.duplicated().any():
        return 'fail', {'note': 'duplicate_timestamps_present'}, None
    inferred = pd.infer_freq(clean)
    if inferred:
        try:
            expected = pd.date_range(clean.iloc[0], clean.iloc[-1], freq=inferred)
            if len(expected) == len(clean):
                return 'pass', {'inferred_frequency': inferred, 'gap_count': 0}, inferred
            return 'fail', {'inferred_frequency': inferred, 'gap_count': int(len(expected) - len(clean))}, inferred
        except Exception:
            return 'pass', {'inferred_frequency': inferred, 'gap_count': None}, inferred
    diffs = clean.diff().dropna()
    if diffs.empty:
        return 'warn', {'note': 'no_valid_differences'}, None
    unique_diffs = diffs.nunique()
    if unique_diffs == 1:
        return 'pass', {'inferred_frequency': None, 'gap_count': 0, 'uniform_delta_days': float(diffs.iloc[0].total_seconds() / 86400.0)}, None
    return 'fail', {'note': 'irregular_spacing', 'unique_deltas': int(unique_diffs)}, None


def _choose_stl_period(profile: VariableProfile | None, freq_hint: str | None, n_obs: int) -> tuple[int | None, dict[str, Any]]:
    if n_obs < 4:
        return None, {'source': 'insufficient_observations'}
    freq = (freq_hint or '').upper()
    if freq.startswith('MS') or freq.startswith('M'):
        return 12, {'source': 'frequency_hint', 'frequency': freq}
    if freq.startswith('QS') or freq.startswith('Q'):
        return 4, {'source': 'frequency_hint', 'frequency': freq}
    if freq.startswith('W'):
        return (52 if n_obs >= 104 else 13), {'source': 'frequency_hint', 'frequency': freq}
    if freq.startswith('D'):
        return (7 if n_obs >= 28 else max(2, min(7, n_obs // 2))), {'source': 'frequency_hint', 'frequency': freq}
    if freq.startswith('YS') or freq.startswith('AS') or freq == 'A':
        return (2 if n_obs >= 24 else None), {'source': 'frequency_hint', 'frequency': freq}
    seasonality = (profile.summary_json or {}).get('seasonality', {}) if profile else {}
    best_lag = seasonality.get('best_lag') if isinstance(seasonality, dict) else None
    if isinstance(best_lag, int) and best_lag >= 2 and n_obs >= best_lag * 2:
        return best_lag, {'source': 'seasonality_profile_fallback', 'best_lag': best_lag}
    fallback = max(2, min(12, n_obs // 3))
    if n_obs >= fallback * 2:
        return fallback, {'source': 'fallback', 'fallback_period': fallback}
    return None, {'source': 'none'}


def _decomposition_payload(frame: pd.DataFrame, dataset: Dataset, variable_name: str, profile: VariableProfile | None) -> dict[str, Any]:
    n_obs = int(len(frame))
    regularity_result, regularity_info, inferred_freq = _time_regularity(frame['time'])
    period, period_info = _choose_stl_period(profile, dataset.frequency_hint or inferred_freq, n_obs)
    return {
        'n_obs': n_obs,
        'regularity_result': regularity_result,
        'regularity_info': regularity_info,
        'period': period,
        'period_info': period_info,
    }


def _run_stl(frame: pd.DataFrame, dataset: Dataset, variable_name: str, profile: VariableProfile | None) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    assumptions: list[dict[str, Any]] = []
    caveats: list[dict[str, Any]] = []
    prep = _decomposition_payload(frame, dataset, variable_name, profile)
    n_obs = prep['n_obs']
    assumptions.append({
        'assumption_name': 'sufficient_observations',
        'check_method': 'row_count_threshold',
        'check_result': 'pass' if n_obs >= 24 else 'fail',
        'severity': 'high',
        'notes': f'{variable_name}: n={n_obs}',
    })
    assumptions.append({
        'assumption_name': 'time_regularity',
        'check_method': 'frequency_and_gap_check',
        'check_result': prep['regularity_result'],
        'severity': 'high' if prep['regularity_result'] == 'fail' else 'medium',
        'notes': f'{variable_name}: {json.dumps(prep["regularity_info"], default=_json_default)}',
    })
    if n_obs < 24:
        caveats.append({'caveat_type': 'insufficient_observations', 'severity': 'high', 'message': f'{variable_name}: STL requires at least 24 observations for this workflow.'})
        assumptions.append({'assumption_name': 'stationarity_of_residual', 'check_method': 'adf_on_residual', 'check_result': 'warn', 'severity': 'medium', 'notes': f'{variable_name}: residual not tested because STL did not run'})
        return None, assumptions, caveats
    if prep['regularity_result'] == 'fail':
        caveats.append({'caveat_type': 'irregular_time_index', 'severity': 'high', 'message': f'{variable_name}: STL skipped because the time index is irregular or has gaps.'})
        assumptions.append({'assumption_name': 'stationarity_of_residual', 'check_method': 'adf_on_residual', 'check_result': 'warn', 'severity': 'medium', 'notes': f'{variable_name}: residual not tested because STL did not run'})
        return None, assumptions, caveats
    period = prep['period']
    if not period or period < 2:
        caveats.append({'caveat_type': 'missing_period', 'severity': 'medium', 'message': f'{variable_name}: STL skipped because no usable seasonal period could be determined.'})
        assumptions.append({'assumption_name': 'stationarity_of_residual', 'check_method': 'adf_on_residual', 'check_result': 'warn', 'severity': 'medium', 'notes': f'{variable_name}: residual not tested because STL did not run'})
        return None, assumptions, caveats
    if prep['period_info'].get('source') == 'seasonality_profile_fallback':
        caveats.append({'caveat_type': 'seasonal_period_inferred_from_autocorrelation', 'severity': 'medium', 'message': f'{variable_name}: STL period came from an autocorrelation lag fallback and may capture a harmonic rather than the fundamental seasonal cycle.'})

    series = pd.Series(frame['value'].to_numpy(dtype=float), index=pd.DatetimeIndex(frame['time']), name=variable_name)
    result = STL(series, period=period, robust=True).fit()
    residual = pd.Series(result.resid).dropna()
    residual_hint, residual_summary = _detect_stationarity(residual)
    residual_check = 'pass' if residual_hint == 'likely_stationary' else ('fail' if residual_hint in NONSTATIONARY_HINTS else 'warn')
    assumptions.append({
        'assumption_name': 'stationarity_of_residual',
        'check_method': 'adf_on_residual',
        'check_result': residual_check,
        'severity': 'high' if residual_check == 'fail' else 'medium',
        'notes': f'{variable_name}: {residual_hint}; {json.dumps(residual_summary, default=_json_default)}',
    })

    x = np.arange(len(series), dtype=float)
    trend = pd.Series(result.trend, index=series.index)
    valid_trend = trend.dropna()
    trend_slope = float(np.polyfit(np.arange(len(valid_trend), dtype=float), valid_trend.to_numpy(dtype=float), 1)[0]) if len(valid_trend) >= 2 else 0.0
    seasonal = pd.Series(result.seasonal, index=series.index)
    seasonal_amplitude = float(seasonal.max() - seasonal.min()) if len(seasonal.dropna()) else 0.0
    residual_std = float(residual.std(ddof=1)) if len(residual) > 1 else 0.0

    payload = {
        'variable_name': variable_name,
        'timestamps': [ts.isoformat() for ts in series.index],
        'observed': [None if pd.isna(v) else float(v) for v in series.to_numpy(dtype=float)],
        'trend': [None if pd.isna(v) else float(v) for v in result.trend],
        'seasonal': [None if pd.isna(v) else float(v) for v in result.seasonal],
        'residual': [None if pd.isna(v) else float(v) for v in result.resid],
        'summary_stats': {
            'trend_slope': trend_slope,
            'residual_std': residual_std,
            'seasonal_amplitude': seasonal_amplitude,
            'period': int(period),
            'period_source': prep['period_info'],
            'residual_stationarity_hint': residual_hint,
            'time_regularity': prep['regularity_info'],
        },
    }
    return payload, assumptions, caveats


def _run_cross_correlation(db: Session, run: AnalysisRun, dataset_version_id: str, dataset: Dataset, df: pd.DataFrame) -> None:
    numeric_cols = []
    for c in df.columns:
        if c == dataset.time_column:
            continue
        series = coerce_numeric_series(df[c])
        if series.notna().sum() >= 2:
            numeric_cols.append(c)
    max_lag = int(run.parameters_json.get('max_lag', 10))
    time_check_result = 'pass' if dataset.time_column else 'fail'
    db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='time_ordered_observations', check_method='time_column_present', check_result=time_check_result, severity='high', notes='cross-correlation requires ordered observations'))
    profile_map = {var.variable_name: profile for profile, var in db.query(VariableProfile, VariableDefinition).join(VariableDefinition, VariableProfile.variable_id == VariableDefinition.variable_id).filter(VariableProfile.dataset_version_id == dataset_version_id).all()}
    hints = [profile_map[n].stationarity_hint for n in numeric_cols if n in profile_map and profile_map[n].stationarity_hint]
    nonstationary = [h for h in hints if h in NONSTATIONARY_HINTS]
    check_result = 'fail' if nonstationary else ('pass' if hints else 'warn')
    stationarity_notes = []
    for name in numeric_cols:
        profile = profile_map.get(name)
        if profile:
            stationarity_notes.append(f"{name}:{profile.stationarity_hint or 'not_profiled'}")
    db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='series_stationarity', check_method='profile_lookup', check_result=check_result, severity='high' if check_result == 'fail' else 'medium', notes='; '.join(stationarity_notes) if stationarity_notes else 'no_profile_data'))
    db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='interpretation', severity='medium', message='Cross-correlation is not causal inference. Regime changes and nonstationarity can distort lag relationships.'))
    if len(numeric_cols) < 2:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='insufficient_variables', severity='high', message='Cross-correlation requires at least two numeric variables.'))
        return
    results: dict[str, Any] = {}
    best_pair = None
    best_abs_corr = -1.0
    best_pair_curve = None
    for i, left in enumerate(numeric_cols):
        for right in numeric_cols[i + 1:]:
            lag_curve = _pairwise_lag_correlation(df[left], df[right], max_lag)
            results[f'{left}__vs__{right}'] = lag_curve
            valid = [(abs(v), lag, v) for lag, v in lag_curve.items() if v is not None]
            if not valid:
                continue
            current_best = max(valid)
            if current_best[0] > best_abs_corr:
                best_abs_corr = current_best[0]
                best_pair = (left, right, current_best[1], current_best[2])
                best_pair_curve = lag_curve
    artifact_json = _persist_artifact_json(run, 'cross_correlation_result', 'Cross-correlation results', {'results': results, 'summary_stats': {'max_lag': max_lag, 'pair_count': len(results)}})
    db.add(artifact_json)
    if best_pair_curve is not None and best_pair is not None:
        fig = plt.figure(figsize=(8, 4.5))
        xs = list(best_pair_curve.keys())
        ys = [best_pair_curve[k] if best_pair_curve[k] is not None else 0.0 for k in xs]
        ax = fig.add_subplot(111)
        ax.plot(xs, ys)
        ax.axvline(best_pair[2], linestyle='--')
        ax.set_xlabel('Lag')
        ax.set_ylabel('Correlation')
        ax.set_title(f'Cross-correlation: {best_pair[0]} vs {best_pair[1]}')
        summary = f'Strongest pair: {best_pair[0]} vs {best_pair[1]} at lag {best_pair[2]} with correlation {best_pair[3]:.4f}.'
        metadata = {'max_lag': max_lag, 'pair_count': len(results), 'strongest_pair': {'left': best_pair[0], 'right': best_pair[1], 'lag': best_pair[2], 'correlation': best_pair[3]}}
        db.add(_persist_artifact_png(run, 'cross_correlation_plot', 'Cross-correlation plot', fig, metadata, summary=summary))
    else:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='degenerate_pairs', severity='medium', message='No variable pair produced a valid lag-correlation curve.'))


def _run_decomposition(db: Session, run: AnalysisRun, dataset_version_id: str, dataset: Dataset, df: pd.DataFrame) -> None:
    profile_map, _, numeric_cols, has_time = _profile_maps(db, dataset_version_id)
    if not has_time:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='missing_time_index', severity='high', message='Decomposition requires a time-indexed dataset.'))
        return
    artifact_count = 0
    for variable_name in numeric_cols:
        frame = _get_time_frame(df, dataset, variable_name)
        payload, assumptions, caveats = _run_stl(frame, dataset, variable_name, profile_map.get(variable_name))
        for assumption in assumptions:
            db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, **assumption))
        for caveat in caveats:
            db.add(CaveatNote(analysis_run_id=run.analysis_run_id, **caveat))
        if payload is None:
            continue
        artifact_count += 2
        json_artifact = _persist_artifact_json(run, 'decomposition_components', f'STL components: {variable_name}', payload, summary=f'{variable_name}: STL decomposition components and summary statistics')
        db.add(json_artifact)
        fig = plt.figure(figsize=(10, 8))
        observed_ax = fig.add_subplot(4, 1, 1)
        trend_ax = fig.add_subplot(4, 1, 2)
        seasonal_ax = fig.add_subplot(4, 1, 3)
        resid_ax = fig.add_subplot(4, 1, 4)
        timestamps = pd.to_datetime(payload['timestamps'], utc=True)
        observed_ax.plot(timestamps, payload['observed'])
        observed_ax.set_title(f'{variable_name} observed')
        trend_ax.plot(timestamps, payload['trend'])
        trend_ax.set_title('Trend')
        seasonal_ax.plot(timestamps, payload['seasonal'])
        seasonal_ax.set_title('Seasonal')
        resid_ax.plot(timestamps, payload['residual'])
        resid_ax.set_title('Residual')
        png_artifact = _persist_artifact_png(run, 'decomposition_plot', f'STL plot: {variable_name}', fig, payload['summary_stats'], summary=f'{variable_name}: STL observed, trend, seasonal, and residual views')
        db.add(png_artifact)
    if artifact_count == 0:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='no_decomposition_artifacts', severity='medium', message='No variables met STL decomposition prerequisites.'))


def _load_cached_decomposition_payload(db: Session, dataset_version_id: str, variable_name: str) -> dict[str, Any] | None:
    artifact = (
        db.query(AnalysisArtifact)
        .join(AnalysisRun, AnalysisArtifact.analysis_run_id == AnalysisRun.analysis_run_id)
        .filter(AnalysisRun.dataset_version_id == dataset_version_id)
        .filter(AnalysisRun.method_name == 'decomposition')
        .filter(AnalysisArtifact.artifact_type == 'decomposition_components')
        .filter(AnalysisArtifact.title == f'STL components: {variable_name}')
        .order_by(AnalysisRun.completed_at.desc(), AnalysisArtifact.created_at.desc())
        .first()
    )
    if not artifact:
        return None
    try:
        payload = json.loads(_artifact_storage_path(artifact.storage_ref).read_text())
    except Exception:
        return None
    if payload.get('variable_name') != variable_name:
        return None
    return payload


def _confidence_proxy(series: pd.Series, breakpoint: int, window: int = 5) -> float | None:
    if breakpoint <= 0 or breakpoint >= len(series):
        return None
    left = series.iloc[max(0, breakpoint - window):breakpoint].dropna()
    right = series.iloc[breakpoint:min(len(series), breakpoint + window)].dropna()
    if left.empty or right.empty:
        return None
    pooled = pd.concat([left, right])
    std = float(pooled.std(ddof=1)) if len(pooled) > 1 else 0.0
    delta = abs(float(right.mean() - left.mean()))
    if std == 0:
        return float(delta)
    return float(delta / std)


def _run_structural_break(db: Session, run: AnalysisRun, dataset_version_id: str, dataset: Dataset, df: pd.DataFrame) -> None:
    profile_map, _, numeric_cols, has_time = _profile_maps(db, dataset_version_id)
    if not has_time:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='missing_time_index', severity='high', message='Structural break detection requires a time-indexed dataset.'))
        return
    penalty = float(run.parameters_json.get('penalty', 8.0))
    min_segment_flag = int(run.parameters_json.get('minimum_segment_flag', 12))
    algo_min_size = int(run.parameters_json.get('min_size', 3))
    model_name = str(run.parameters_json.get('model', 'l2'))
    db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='penalty_sensitivity', severity='medium', message=f'Structural break detection is sensitive to the penalty parameter. penalty={penalty:g}.'))
    if model_name != 'l2':
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='break_model_choice', severity='medium', message=f'Structural break detection is using ruptures model={model_name}, which may detect distributional changes rather than simple mean shifts.'))
    artifact_count = 0
    for variable_name in numeric_cols:
        frame = _get_time_frame(df, dataset, variable_name)
        if len(frame) < 6:
            db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='insufficient_observations', severity='high', message=f'{variable_name}: too few observations for structural break detection.'))
            db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='minimum_segment_length', check_method='segment_length_threshold', check_result='fail', severity='high', notes=f'{variable_name}: n={len(frame)}'))
            db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='stationarity_required_for_break_test', check_method='profile_lookup', check_result='warn', severity='medium', notes=f'{variable_name}: insufficient observations'))
            continue

        stl_payload = None
        source_label = 'raw_difference'
        if not run.window_scope_json:
            stl_payload = _load_cached_decomposition_payload(db, dataset_version_id, variable_name)
            if stl_payload is not None:
                source_label = 'cached_stl_residual'

        if stl_payload is None:
            stl_payload, _, stl_caveats = _run_stl(frame, dataset, variable_name, profile_map.get(variable_name))
            if stl_payload is not None:
                source_label = 'stl_residual'
            else:
                series = pd.Series(frame['value'].to_numpy(dtype=float), index=pd.DatetimeIndex(frame['time'])).diff().dropna()
                source_label = 'raw_difference'
                for caveat in stl_caveats:
                    db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='break_preparation', severity='low', message=f"{variable_name}: {caveat['message']}"))
        if stl_payload is not None:
            series = pd.Series([np.nan if v is None else float(v) for v in stl_payload['residual']], index=pd.to_datetime(stl_payload['timestamps'], utc=True)).dropna()

        if len(series) < 6 or series.nunique(dropna=True) <= 1:
            db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='degenerate_series', severity='medium', message=f'{variable_name}: break detection skipped because the working series is degenerate.'))
            db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='minimum_segment_length', check_method='segment_length_threshold', check_result='fail', severity='high', notes=f'{variable_name}: degenerate working series'))
            hint = profile_map.get(variable_name).stationarity_hint if profile_map.get(variable_name) else None
            db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='stationarity_required_for_break_test', check_method='profile_lookup', check_result='warn', severity='medium', notes=f'{variable_name}: {hint or "not_profiled"}'))
            continue

        algo = rpt.Pelt(model=model_name, min_size=algo_min_size).fit(series.to_numpy(dtype=float))
        raw_breaks = algo.predict(pen=penalty)
        internal_breaks = [int(bp) for bp in raw_breaks if int(bp) < len(series)]
        segment_boundaries = [0] + [int(bp) for bp in raw_breaks]
        segment_lengths = [segment_boundaries[i + 1] - segment_boundaries[i] for i in range(len(segment_boundaries) - 1)]
        segment_check = 'fail' if any(length < min_segment_flag for length in segment_lengths) else 'pass'
        db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='minimum_segment_length', check_method='ruptures_segment_lengths', check_result=segment_check, severity='high' if segment_check == 'fail' else 'medium', notes=f'{variable_name}: segment_lengths={segment_lengths}'))
        hint = profile_map.get(variable_name).stationarity_hint if profile_map.get(variable_name) else None
        hint_result = 'fail' if hint in NONSTATIONARY_HINTS else ('pass' if hint == 'likely_stationary' else 'warn')
        db.add(AssumptionCheck(analysis_run_id=run.analysis_run_id, assumption_name='stationarity_required_for_break_test', check_method='profile_lookup', check_result=hint_result, severity='high' if hint_result == 'fail' else 'medium', notes=f'{variable_name}: {hint or "not_profiled"}'))
        severity = 'high' if hint in NONSTATIONARY_HINTS else 'medium'
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='nonstationary_break_interpretation', severity=severity, message=f'{variable_name}: breaks on non-stationary series may reflect trend rather than regime change. working_series={source_label}'))

        if not internal_breaks:
            db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='no_breakpoints_detected', severity='low', message=f'{variable_name}: no structural breakpoints were detected at penalty={penalty:g} using model={model_name}.'))
            continue

        breakpoints_payload = []
        for bp in internal_breaks:
            timestamp = series.index[min(bp - 1, len(series.index) - 1)]
            breakpoints_payload.append({'index': int(bp), 'timestamp': timestamp.isoformat(), 'confidence_proxy': _confidence_proxy(series, bp)})
        payload = {
            'variable_name': variable_name,
            'working_series_source': source_label,
            'penalty_used': penalty,
            'model_used': model_name,
            'breakpoints': breakpoints_payload,
            'summary_stats': {
                'break_count': len(breakpoints_payload),
                'penalty_used': penalty,
                'model_used': model_name,
                'segment_lengths': segment_lengths,
            },
        }
        db.add(_persist_artifact_json(run, 'structural_break_result', f'Structural breaks: {variable_name}', payload, summary=f'{variable_name}: structural break metadata and breakpoint locations'))
        fig = plt.figure(figsize=(9, 4.5))
        ax = fig.add_subplot(111)
        ax.plot(series.index, series.to_numpy(dtype=float))
        for bp in internal_breaks:
            ax.axvline(series.index[min(bp - 1, len(series.index) - 1)], linestyle='--')
        ax.set_title(f'Structural breaks: {variable_name}')
        ax.set_xlabel('Time')
        ax.set_ylabel('Working series')
        db.add(_persist_artifact_png(run, 'structural_break_plot', f'Structural break plot: {variable_name}', fig, payload['summary_stats'], summary=f'{variable_name}: working series with detected breakpoints'))
        artifact_count += 2
    if artifact_count == 0:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='no_structural_break_artifacts', severity='medium', message='No variables produced structural break artifacts.'))


def run_analysis(db: Session, dataset_version_id: str, method_name: str, goal_type: str | None, parameters: dict[str, Any], annotation_window_id: str | None) -> AnalysisRun:
    version = db.get(DatasetVersion, dataset_version_id)
    if not version:
        raise ValueError('dataset version not found')
    dataset = db.get(Dataset, version.dataset_id)
    if not dataset:
        raise ValueError('dataset not found')
    window = db.get(AnnotationWindow, annotation_window_id) if annotation_window_id else None
    df = load_version_dataframe(db, dataset_version_id)
    df = _apply_window(df, dataset, window)
    recommendation = recommend_analysis(db, dataset_version_id, goal_type)
    run = AnalysisRun(
        dataset_version_id=dataset_version_id,
        method_name=method_name,
        goal_type=goal_type,
        status='completed',
        route_reason=recommendation['rationale'],
        parameters_json=parameters,
        window_scope_json={'annotation_window_id': annotation_window_id} if annotation_window_id else {},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    if method_name == 'cross_correlation':
        _run_cross_correlation(db, run, dataset_version_id, dataset, df)
    elif method_name == 'decomposition':
        _run_decomposition(db, run, dataset_version_id, dataset, df)
    elif method_name == 'structural_break':
        _run_structural_break(db, run, dataset_version_id, dataset, df)
    else:
        db.add(CaveatNote(analysis_run_id=run.analysis_run_id, caveat_type='unsupported_method', severity='high', message='Only cross_correlation, decomposition, and structural_break are implemented in the starter repo.'))

    db.commit()
    db.refresh(run)
    return run
