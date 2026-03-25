from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats.mstats import winsorize
from sklearn.preprocessing import MinMaxScaler, PowerTransformer, RobustScaler, StandardScaler
from sqlalchemy.orm import Session

from app.models import Dataset, DatasetVersion, TransformationRun, TransformationStep, VariableDefinition, VariableProfile
from app.services.data_utils import coerce_numeric_series
from app.services.dataframe_io import load_version_dataframe, persist_dataframe_as_version_rows


OUTLIER_THRESHOLD = 0.05
HIGH_SKEW_THRESHOLD = 1.5


def recommend_transformations(db: Session, dataset_version_id: str) -> list[dict[str, Any]]:
    profiles = db.query(VariableProfile, VariableDefinition).join(VariableDefinition, VariableProfile.variable_id == VariableDefinition.variable_id).filter(VariableProfile.dataset_version_id == dataset_version_id).all()
    recommendations: list[dict[str, Any]] = []
    for profile, var in profiles:
        if var.is_time_index:
            continue
        method = 'z_score'
        rationale = 'default for numeric series with moderate dispersion and no strong outlier or skew signal'
        alternatives = ['robust', 'min_max', 'winsor_zscore', 'yeo_johnson']
        token_summary = (profile.summary_json or {}).get('token_summary', {})
        if profile.outlier_fraction and profile.outlier_fraction > OUTLIER_THRESHOLD:
            method = 'robust'
            rationale = f'outlier fraction {profile.outlier_fraction:.3f} exceeds {OUTLIER_THRESHOLD:.2f}; robust scaling reduces median-centered outlier sensitivity'
        elif profile.skewness and abs(profile.skewness) > HIGH_SKEW_THRESHOLD:
            if profile.negative_values_flag or profile.zero_values_flag:
                method = 'yeo_johnson'
                rationale = f'absolute skewness {abs(profile.skewness):.3f} exceeds {HIGH_SKEW_THRESHOLD:.1f} and series includes zero or negative values'
            else:
                method = 'winsor_zscore'
                rationale = f'absolute skewness {abs(profile.skewness):.3f} exceeds {HIGH_SKEW_THRESHOLD:.1f} without zero/negative constraints'
        elif profile.bounded_flag:
            method = 'min_max'
            rationale = 'series is explicitly modeled as bounded in metadata'
        warnings: list[str] = []
        if token_summary.get('proxy_count', 0) > 0:
            warnings.append('series contains threshold or inequality tokens that were coerced to numeric proxies')
        if token_summary.get('placeholder_count', 0) > 0:
            warnings.append('series contains placeholder null tokens that were converted to missing values')
        recommendations.append({'variable_name': var.variable_name, 'recommended_method': method, 'rationale': rationale, 'alternatives': alternatives, 'warnings': warnings})
    return recommendations


def _apply_method(series: pd.Series, method: str, parameters: dict[str, Any]) -> pd.Series:
    numeric = coerce_numeric_series(series)
    arr = numeric.to_numpy(dtype=float).reshape(-1, 1)
    nan_mask = np.isnan(arr[:, 0])
    fit_arr = arr[~nan_mask].reshape(-1, 1)
    if fit_arr.size == 0:
        return numeric
    if method == 'z_score':
        if np.nanstd(fit_arr) == 0:
            return numeric
        transformed = StandardScaler().fit_transform(fit_arr).reshape(-1)
    elif method == 'robust':
        transformed = RobustScaler().fit_transform(fit_arr).reshape(-1)
    elif method == 'min_max':
        if np.nanmax(fit_arr) == np.nanmin(fit_arr):
            return pd.Series(np.where(nan_mask, np.nan, 0.0), index=series.index)
        transformed = MinMaxScaler().fit_transform(fit_arr).reshape(-1)
    elif method == 'winsor_zscore':
        limits = parameters.get('limits', [0.05, 0.05])
        cleaned = np.array(winsorize(fit_arr.reshape(-1), limits=limits))
        transformed = cleaned.astype(float) if np.nanstd(cleaned) == 0 else StandardScaler().fit_transform(cleaned.reshape(-1, 1)).reshape(-1)
    elif method == 'yeo_johnson':
        if np.nanstd(fit_arr) == 0:
            return numeric
        transformed = PowerTransformer(method='yeo-johnson', standardize=True).fit_transform(fit_arr).reshape(-1)
    else:
        raise ValueError(f'unsupported transformation method: {method}')
    result = arr.copy()
    result[~nan_mask, 0] = transformed
    return pd.Series(result[:, 0], index=series.index)


def apply_transformations(db: Session, dataset_id: str, dataset_version_id: str, version_label: str | None, rationale: str | None, steps: list[dict[str, Any]]) -> dict[str, Any]:
    dataset = db.get(Dataset, dataset_id)
    version = db.get(DatasetVersion, dataset_version_id)
    if not dataset or not version:
        raise ValueError('dataset or dataset version not found')
    source_df = load_version_dataframe(db, dataset_version_id)
    transformed_df = source_df.copy()
    variables = db.query(VariableDefinition).filter(VariableDefinition.dataset_version_id == dataset_version_id).all()
    var_by_name = {v.variable_name: v for v in variables}
    run = TransformationRun(input_dataset_version_id=dataset_version_id, rationale=rationale)
    db.add(run)
    db.flush()
    transformed_variables: list[str] = []
    step_by_input_var_id: dict[str, TransformationStep] = {}
    for step in steps:
        variable_name = step['variable_name']
        method_name = step['method_name']
        params = step.get('parameters') or {}
        var = var_by_name.get(variable_name)
        if not var:
            raise ValueError(f'variable not found in dataset version: {variable_name}')
        if var.is_time_index:
            continue
        transformed_df[variable_name] = _apply_method(transformed_df[variable_name], method_name, params)
        db_step = TransformationStep(
            transformation_run_id=run.transformation_run_id,
            input_variable_id=var.variable_id,
            method_name=method_name,
            parameters_json=params,
            selection_reason=step.get('rationale'),
            warnings_json=[],
        )
        db.add(db_step)
        step_by_input_var_id[var.variable_id] = db_step
        transformed_variables.append(variable_name)
    output_version = DatasetVersion(
        dataset_id=dataset_id,
        parent_version_id=dataset_version_id,
        version_label=version_label or f'{version.version_label}_transformed',
        version_type='transformed',
        status='ready',
        notes=rationale,
    )
    db.add(output_version)
    db.flush()
    for var in variables:
        new_var = VariableDefinition(
            dataset_version_id=output_version.dataset_version_id,
            variable_name=var.variable_name,
            dtype=var.dtype,
            role=var.role,
            is_numeric=var.is_numeric,
            is_time_index=var.is_time_index,
            ordinal_position=var.ordinal_position,
        )
        db.add(new_var)
        db.flush()
        matching_step = step_by_input_var_id.get(var.variable_id)
        if matching_step:
            matching_step.output_variable_id = new_var.variable_id
    persist_dataframe_as_version_rows(db, output_version, transformed_df, dataset.time_column)
    run.output_dataset_version_id = output_version.dataset_version_id
    db.commit()
    return {'transformation_run_id': run.transformation_run_id, 'output_dataset_version_id': output_version.dataset_version_id, 'version_label': output_version.version_label, 'transformed_variables': transformed_variables}
