from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
import zipfile
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

DEFAULT_DATA_ROOT = ROOT / 'data_actual'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--method-name', default='cross_correlation')
    parser.add_argument('--max-lag', type=int, default=2)
    parser.add_argument('--sample-file', default='')
    parser.add_argument('--output-prefix', default='attached_dataset_eval')
    parser.add_argument('--break-model', default='l2')
    parser.add_argument('--data-root', default=str(DEFAULT_DATA_ROOT), help='Directory containing zip archives and default output location.')
    parser.add_argument('--archive-glob', default='mcs*.zip', help='Glob pattern under --data-root used when --sample-file is not provided.')
    parser.add_argument('--max-files', type=int, default=0, help='Optional cap on CSV files to evaluate. 0 means evaluate all targets.')
    parser.add_argument('--seed', type=int, default=0, help='Random seed used when --max-files is set.')
    parser.add_argument('--output-dir', default='', help='Optional output directory for json/csv/md reports. Defaults to --data-root.')
    return parser.parse_args()


ARGS = parse_args()
DATA_ROOT = Path(ARGS.data_root).resolve()
OUTPUT_DIR = Path(ARGS.output_dir).resolve() if ARGS.output_dir else DATA_ROOT

if not DATA_ROOT.exists():
    raise FileNotFoundError(f'data root not found: {DATA_ROOT}')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

os.environ['DATABASE_URL'] = 'sqlite:///./attached_eval.db'
os.environ['STORAGE_DIR'] = str(BACKEND / 'app' / 'storage_eval')

from main import app  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402

engine = create_engine('sqlite:///./attached_eval.db', connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
ZIPS = sorted(DATA_ROOT.glob(ARGS.archive_glob))
if not ZIPS:
    raise FileNotFoundError(f'no archives matched {ARGS.archive_glob!r} under {DATA_ROOT}')


def bucket_for(name: str) -> str:
    lower = name.lower()
    if 'salient' in lower:
        return 'salient'
    if 'world' in lower:
        return 'world'
    if 'fig' in lower or 'trend' in lower or 'trends' in lower:
        return 'trends_figures'
    return 'other'


def pick_transform_steps(recommendations: list[dict]) -> list[dict]:
    out = []
    for item in recommendations[: min(5, len(recommendations))]:
        out.append({'variable_name': item['variable_name'], 'method_name': item['recommended_method'], 'parameters': {}, 'rationale': item['rationale']})
    return out


def resolve_sample_archive(ref: str) -> Path:
    candidate = Path(str(ref))
    if candidate.is_absolute() and candidate.exists():
        return candidate
    direct = DATA_ROOT / candidate
    if direct.exists():
        return direct
    by_name = DATA_ROOT / candidate.name
    if by_name.exists():
        return by_name
    raise FileNotFoundError(f'sample archive not found: {ref}')


def iter_targets():
    if ARGS.sample_file:
        sample_path = Path(ARGS.sample_file)
        if not sample_path.is_absolute():
            sample_path = (ROOT / sample_path).resolve()
        sample_df = pd.read_csv(sample_path)
        for _, row in sample_df.iterrows():
            yield resolve_sample_archive(str(row['archive'])), str(row['file'])
        return

    for zpath in ZIPS:
        with zipfile.ZipFile(zpath) as zf:
            for name in zf.namelist():
                if name.lower().endswith('.csv'):
                    yield zpath, name


targets = list(iter_targets())
if ARGS.max_files > 0 and len(targets) > ARGS.max_files:
    rng = random.Random(ARGS.seed)
    targets = sorted(rng.sample(targets, ARGS.max_files), key=lambda item: (item[0].name, item[1]))

print(f'data_root={DATA_ROOT}')
print(f'archives={len(ZIPS)}')
print(f'csv_targets={len(targets)}')
print(f'output_dir={OUTPUT_DIR}')

results = []
for idx, (zpath, name) in enumerate(targets, start=1):
    if idx % 25 == 0:
        print(f'progress {idx}/{len(targets)}')
    with zipfile.ZipFile(zpath) as zf:
        data = zf.read(name)
    row = {'archive': zpath.name, 'bucket': bucket_for(name), 'file': name, 'method_name': ARGS.method_name}
    resp = client.post('/api/v1/sources/upload', files={'file': (Path(name).name, io.BytesIO(data), 'text/csv')}, data={'name': Path(name).stem, 'description': name, 'domain_pack': 'macro_energy_commodities'})
    row['upload_status'] = resp.status_code
    if resp.status_code != 200:
        row['error'] = resp.text
        results.append(row)
        continue
    payload = resp.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']
    row['row_count'] = payload['row_count']
    row['time_column'] = payload['time_column']
    row['numeric_count'] = len(payload['numeric_variables'])
    row['dataset_id'] = dataset_id
    row['version_id'] = version_id

    resp = client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile', json={'detect_seasonality': True, 'detect_stationarity': True})
    row['profile_status'] = resp.status_code
    if resp.status_code == 200:
        row['profile_count'] = len(resp.json())
    else:
        row['error'] = resp.text
        results.append(row)
        continue

    resp = client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/recommend')
    row['recommend_status'] = resp.status_code
    if resp.status_code == 200:
        recs = resp.json()
        row['recommend_count'] = len(recs)
    else:
        row['error'] = resp.text
        results.append(row)
        continue

    steps = pick_transform_steps(recs)
    if steps:
        resp = client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/apply', json={'version_label': 'scaled_v1', 'rationale': 'automated evaluation transformation', 'steps': steps})
        row['transform_status'] = resp.status_code
        if resp.status_code == 200:
            transformed = resp.json()
            row['transformed_vars'] = len(transformed['transformed_variables'])
            transformed_version_id = transformed['output_dataset_version_id']
        else:
            row['error'] = resp.text
            results.append(row)
            continue
    else:
        row['transform_status'] = 204
        transformed_version_id = version_id
        row['transformed_vars'] = 0

    rec = client.post(f'/api/v1/datasets/{dataset_id}/versions/{transformed_version_id}/analysis/recommend', json={'goal_type': 'exploratory'})
    row['analysis_recommend_status'] = rec.status_code
    if rec.status_code == 200:
        row['analysis_sequence'] = ','.join(rec.json()['recommended_sequence'])

    if ARGS.method_name == 'cross_correlation':
        parameters = {'max_lag': ARGS.max_lag}
    elif ARGS.method_name == 'structural_break':
        parameters = {'model': ARGS.break_model}
    else:
        parameters = {}
    resp = client.post('/api/v1/analysis-runs', json={'dataset_version_id': transformed_version_id, 'method_name': ARGS.method_name, 'goal_type': 'exploratory', 'parameters': parameters, 'annotation_window_id': None})
    row['analysis_status'] = resp.status_code
    if resp.status_code == 200:
        analysis = resp.json()
        row['artifact_count'] = len(analysis['artifacts'])
        row['caveat_count'] = len(analysis['caveats'])
        row['assumption_count'] = len(analysis['assumptions'])
        row['artifact_types'] = ','.join(sorted({item['artifact_type'] for item in analysis['artifacts']}))
    else:
        row['error'] = resp.text
    results.append(row)

out_json = OUTPUT_DIR / f'{ARGS.output_prefix}.json'
out_csv = OUTPUT_DIR / f'{ARGS.output_prefix}.csv'
out_md = OUTPUT_DIR / f'{ARGS.output_prefix}.md'
out_json.write_text(json.dumps(results, indent=2))
pd.DataFrame(results).to_csv(out_csv, index=False)
df = pd.DataFrame(results)
lines = [f'# Attached Dataset Evaluation - {ARGS.method_name}', '', f'Total CSV files evaluated: {len(df)}', '']
for col in ['upload_status', 'profile_status', 'recommend_status', 'transform_status', 'analysis_status']:
    if col in df.columns:
        counts = df[col].fillna(-1).astype(int).value_counts().sort_index().to_dict()
        lines.append(f'- {col}: {counts}')
lines.append('')
if 'bucket' in df.columns:
    lines.append('## By bucket')
    lines.append('')
    bucket_summary = df.groupby('bucket')[['upload_status', 'analysis_status']].agg(lambda s: int((s == 200).sum())).rename(columns={'upload_status': 'upload_200', 'analysis_status': 'analysis_200'})
    try:
        lines.append(bucket_summary.to_markdown())
    except Exception:
        lines.append(bucket_summary.to_string())
    lines.append('')
failures = df[df.get('analysis_status', pd.Series(dtype=float)) != 200]
if not failures.empty:
    lines.append('## Remaining non-200 analysis cases')
    lines.append('')
    cols = [c for c in ['archive', 'file', 'analysis_status', 'error'] if c in failures.columns]
    try:
        lines.append(failures[cols].head(25).to_markdown(index=False))
    except Exception:
        lines.append(failures[cols].head(25).to_string(index=False))
out_md.write_text('\n'.join(lines))
print(out_json)
print(out_csv)
print(out_md)

