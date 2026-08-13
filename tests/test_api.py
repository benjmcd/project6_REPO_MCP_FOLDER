import io
import importlib
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
import pandas as pd
import pytest
import requests
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

TEST_RUN_TOKEN = f"a{os.getpid()}{uuid.uuid4().hex[:4]}"
DEFAULT_TEST_RUNTIME_ROOT = ROOT / '.t' / TEST_RUN_TOKEN
DEFAULT_TEST_DB_PATH = DEFAULT_TEST_RUNTIME_ROOT / 'd.db'
SHARED_TEST_RUNTIME_ROOT = (BACKEND / 'app' / 'storage_test_runtime').resolve()
SHARED_TEST_DB_PATH = (BACKEND / 'test_method_aware.db').resolve()


def _sqlite_url_for_path(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


DEFAULT_DATABASE_URL = _sqlite_url_for_path(DEFAULT_TEST_DB_PATH)


def _sqlite_file_path(database_url: str) -> Path | None:
    if not str(database_url).startswith('sqlite:///'):
        return None
    raw = str(database_url)[10:].strip()
    if not raw or raw == '.' or raw == ':memory:' or raw.startswith('file:'):
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (BACKEND / path).resolve()
    return path.resolve()


def _normalize_test_database_url(database_url: str | None) -> tuple[str, Path | None]:
    raw = str(database_url or '').strip()
    if not raw:
        return DEFAULT_DATABASE_URL, DEFAULT_TEST_DB_PATH.resolve()
    if raw.startswith('sqlite:///'):
        raw_path = raw[10:].strip()
        if not raw_path or raw_path == '.':
            return DEFAULT_DATABASE_URL, DEFAULT_TEST_DB_PATH.resolve()
        if raw_path == ':memory:' or raw_path.startswith('file:'):
            return raw, None
    file_path = _sqlite_file_path(raw)
    if file_path is None:
        return raw, None
    if file_path.resolve() == SHARED_TEST_DB_PATH:
        return DEFAULT_DATABASE_URL, DEFAULT_TEST_DB_PATH.resolve()
    return _sqlite_url_for_path(file_path), file_path


def _normalize_test_storage_dir(storage_dir: str | None) -> Path:
    raw = str(storage_dir or '').strip()
    candidate = DEFAULT_TEST_RUNTIME_ROOT / 's' if not raw else Path(raw)
    if not candidate.is_absolute():
        candidate = BACKEND / candidate
    resolved = candidate.resolve()
    if resolved == SHARED_TEST_RUNTIME_ROOT:
        return (DEFAULT_TEST_RUNTIME_ROOT / 's').resolve()
    return resolved


TEST_DATABASE_URL, TEST_DB_PATH = _normalize_test_database_url(os.environ.get('DATABASE_URL'))
TEST_STORAGE_DIR = _normalize_test_storage_dir(os.environ.get('STORAGE_DIR'))
if TEST_DB_PATH is not None:
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
NRC_FIXTURE_DIR = ROOT / 'tests' / 'fixtures' / 'nrc_aps_docs' / 'v1'

os.environ['DATABASE_URL'] = TEST_DATABASE_URL
os.environ['STORAGE_DIR'] = str(TEST_STORAGE_DIR)
os.environ['DB_INIT_MODE'] = 'none'
os.environ['NRC_ADAMS_APS_SUBSCRIPTION_KEY'] = 'test-nrc-key'
os.environ['NRC_ADAMS_APS_API_BASE_URL'] = 'https://adams-api.nrc.gov'

for module_name in list(sys.modules):
    if module_name == "main" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)

main_module = importlib.import_module("main")
app = main_module.app
from app.core.config import bootstrap_storage_tree  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models import DatasetVersion  # noqa: E402
from app.services.analysis import (  # noqa: E402
    SUPPORTED_ANALYSIS_METHOD_IDS,
    _descriptive_column_summary,
    analysis_method_registry,
)
from support_nrc_aps_fake_opendataloader import install_fake_opendataloader_pdf  # noqa: E402

SQLALCHEMY_DATABASE_URL = TEST_DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

bootstrap_storage_tree(TEST_STORAGE_DIR)
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
API_APP_MODULES = {
    name: module
    for name, module in sys.modules.items()
    if name == "main" or name.startswith("app.")
}
API_APP_MODULE_ATTR_MISSING = object()


def _api_app_module_names():
    return {
        name
        for name in sys.modules
        if name == "main" or name.startswith("app.")
    } | set(API_APP_MODULES)


def _snapshot_api_app_modules():
    module_names = _api_app_module_names()
    parent_attrs = {}
    for module_name in module_names:
        parent_name, _, child_name = module_name.rpartition(".")
        if not parent_name:
            continue
        parent_module = sys.modules.get(parent_name)
        if parent_module is None:
            continue
        parent_attrs[(parent_name, child_name)] = vars(parent_module).get(
            child_name,
            API_APP_MODULE_ATTR_MISSING,
        )
    return {
        "modules": {
            name: sys.modules[name]
            for name in module_names
            if name in sys.modules
        },
        "parent_attrs": parent_attrs,
    }


def _restore_api_app_module_snapshot(snapshot):
    modules = snapshot["modules"]
    for module_name in list(sys.modules):
        if (module_name == "main" or module_name.startswith("app.")) and module_name not in modules:
            module = sys.modules.pop(module_name, None)
            parent_name, _, child_name = module_name.rpartition(".")
            parent_module = sys.modules.get(parent_name)
            if (
                module is not None
                and parent_module is not None
                and vars(parent_module).get(child_name) is module
            ):
                delattr(parent_module, child_name)
    for module_name, module in modules.items():
        sys.modules[module_name] = module
    for (parent_name, child_name), value in snapshot["parent_attrs"].items():
        parent_module = sys.modules.get(parent_name)
        if parent_module is None:
            continue
        if value is API_APP_MODULE_ATTR_MISSING:
            if hasattr(parent_module, child_name):
                delattr(parent_module, child_name)
        else:
            setattr(parent_module, child_name, value)


def _restore_api_app_module_baseline():
    for module_name in list(sys.modules):
        if module_name == "main" or module_name.startswith("app."):
            if module_name not in API_APP_MODULES:
                module = sys.modules.pop(module_name, None)
                parent_name, _, child_name = module_name.rpartition(".")
                parent_module = sys.modules.get(parent_name)
                if (
                    module is not None
                    and parent_module is not None
                    and vars(parent_module).get(child_name) is module
                ):
                    delattr(parent_module, child_name)
    for module_name, module in API_APP_MODULES.items():
        sys.modules[module_name] = module
    for module_name, module in API_APP_MODULES.items():
        parent_name, _, child_name = module_name.rpartition(".")
        parent_module = API_APP_MODULES.get(parent_name)
        if parent_module is not None:
            setattr(parent_module, child_name, module)


@pytest.fixture(autouse=True)
def _restore_api_app_modules():
    _restore_api_app_module_baseline()
    snapshot = _snapshot_api_app_modules()
    try:
        yield
    finally:
        _restore_api_app_module_snapshot(snapshot)


def test_analysis_method_registry_describes_current_methods_only() -> None:
    registry = analysis_method_registry()

    assert list(SUPPORTED_ANALYSIS_METHOD_IDS) == [
        "cross_correlation",
        "decomposition",
        "structural_break",
        "descriptive_summary",
    ]
    assert list(registry) == list(SUPPORTED_ANALYSIS_METHOD_IDS)
    assert registry["cross_correlation"]["parameters"]["max_lag"]["default"] == 10
    assert registry["decomposition"]["artifact_types"] == ("decomposition_components", "decomposition_plot")
    assert registry["structural_break"]["parameters"]["penalty"]["default"] == 8.0
    assert registry["structural_break"]["parameters"]["model"]["default"] == "l2"
    assert registry["descriptive_summary"]["artifact_types"] == ("descriptive_summary_result",)
    assert registry["descriptive_summary"]["parameters"] == {}


def test_descriptive_summary_runs_deterministic_json_without_widening_scope():
    csv_bytes = (
        b"category,amount,flag,notes\n"
        b"A,10,true,alpha\n"
        b"A,,false,beta\n"
        b"B,30,true,alpha\n"
        b"C,40,,gamma\n"
    )
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('summary.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Summary', 'description': 'Descriptive summary dataset', 'domain_pack': 'general'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']

    rec_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/analysis/recommend',
        json={'goal_type': 'exploratory'},
    )
    assert rec_response.status_code == 200, rec_response.text
    rec_payload = rec_response.json()
    assert rec_payload['recommended_sequence'] == ['descriptive_summary']
    assert 'does not meet starter time-series assumptions' in rec_payload['rationale']

    analysis_response = client.post(
        '/api/v1/analysis-runs',
        json={
            'dataset_version_id': version_id,
            'method_name': 'descriptive_summary',
            'goal_type': 'exploratory',
            'parameters': {},
            'annotation_window_id': None,
        },
    )
    assert analysis_response.status_code == 200, analysis_response.text
    analysis = analysis_response.json()
    artifact_types = [item['artifact_type'] for item in analysis['artifacts']]
    assert artifact_types == ['descriptive_summary_result']
    assert all(not item['artifact_type'].endswith('_plot') for item in analysis['artifacts'])
    assumption_names = {item['assumption_name'] for item in analysis['assumptions']}
    assert {'data_availability', 'column_classification', 'missingness_scan'}.issubset(assumption_names)
    caveat_types = {item['caveat_type'] for item in analysis['caveats']}
    assert {'non_time_series_interpretation', 'missing_values_present'}.issubset(caveat_types)

    artifact = analysis['artifacts'][0]
    artifact_path = Path(os.environ['STORAGE_DIR']) / 'artifacts' / Path(artifact['storage_ref']).name
    result_payload = json.loads(artifact_path.read_text())
    assert result_payload['summary_stats']['row_count'] == 4
    assert result_payload['summary_stats']['column_count'] == 4
    assert result_payload['summary_stats']['numeric_column_count'] == 1
    assert result_payload['summary_stats']['boolean_column_count'] == 1
    assert result_payload['columns']['amount']['inferred_class'] == 'numeric'
    assert result_payload['columns']['amount']['numeric_summary']['non_null_count'] == 3
    assert result_payload['columns']['amount']['numeric_summary']['mean'] == pytest.approx(26.6666666667)
    assert result_payload['columns']['category']['top_values'][0] == {'value': 'A', 'count': 2}
    assert result_payload['columns']['flag']['inferred_class'] == 'boolean'


def test_descriptive_summary_column_summary_handles_nested_values_deterministically():
    summary = _descriptive_column_summary(pd.Series([{'b': 2, 'a': 1}, {'a': 1, 'b': 2}, None]), is_time_column=False)

    assert summary['inferred_class'] == 'categorical'
    assert summary['unsupported_nested_values'] is True
    assert summary['missing_count'] == 1
    assert summary['unique_count'] == 1
    assert summary['top_values'] == [{'value': {'a': 1, 'b': 2}, 'count': 2}]


def _read_nrc_fixture_bytes(name: str) -> bytes:
    return (NRC_FIXTURE_DIR / name).read_bytes()


def _nrc_manifest_entry(fixture_id: str) -> dict[str, object]:
    payload = json.loads((NRC_FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in payload.get("entries") or []:
        if str(entry.get("fixture_id") or "") == fixture_id:
            return dict(entry)
    raise KeyError(fixture_id)


def test_canonical_local_expert_journey_recovers_state_with_fresh_client():
    csv_bytes = (
        b"date,revenue,traffic,temperature\n"
        b"2024-01-01,100,200,50\n"
        b"2024-01-02,102,210,51\n"
        b"2024-01-03,300,230,49\n"
        b"2024-01-04,110,220,52\n"
        b"2024-01-05,108,218,48\n"
        b"2024-01-06,112,225,47\n"
        b",,,\n"
    )
    expected_hash = hashlib.sha256(csv_bytes).hexdigest()
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('demo.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Demo', 'description': 'Test dataset', 'domain_pack': 'macro', 'primary_time_column': 'date'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']
    assert payload['row_count'] == 6
    assert payload['source_row_count'] == 7
    assert payload['dropped_row_count'] == 1
    assert payload['content_hash'] == expected_hash

    profile_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile',
        json={'detect_seasonality': False, 'detect_stationarity': False},
    )
    assert profile_response.status_code == 200, profile_response.text
    profiles = profile_response.json()
    assert len(profiles) == 3

    rec_response = client.post(f'/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/recommend')
    assert rec_response.status_code == 200, rec_response.text
    recommendations = rec_response.json()
    assert any(item['variable_name'] == 'revenue' for item in recommendations)

    apply_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/apply',
        json={
            'version_label': 'scaled_v1',
            'rationale': 'test transformation',
            'steps': [
                {'variable_name': 'revenue', 'method_name': 'robust', 'parameters': {}},
                {'variable_name': 'traffic', 'method_name': 'z_score', 'parameters': {}},
                {'variable_name': 'temperature', 'method_name': 'min_max', 'parameters': {}},
            ],
        },
    )
    assert apply_response.status_code == 200, apply_response.text
    transformed = apply_response.json()
    transformed_version_id = transformed['output_dataset_version_id']

    transformed_profile_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{transformed_version_id}/profile',
        json={'detect_seasonality': False, 'detect_stationarity': True},
    )
    assert transformed_profile_response.status_code == 200, transformed_profile_response.text
    assert len(transformed_profile_response.json()) == 3

    annotation_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{transformed_version_id}/annotations',
        json={
            'label': 'shock window',
            'annotation_type': 'event_window',
            'start_time': '2024-01-02T00:00:00',
            'end_time': '2024-01-05T00:00:00',
            'notes': 'focus on revenue spike',
        },
    )
    assert annotation_response.status_code == 200, annotation_response.text
    annotation_id = annotation_response.json()['annotation_window_id']

    analysis_response = client.post(
        '/api/v1/analysis-runs',
        json={
            'dataset_version_id': transformed_version_id,
            'method_name': 'cross_correlation',
            'goal_type': 'exploratory',
            'parameters': {'max_lag': 2},
            'annotation_window_id': annotation_id,
        },
    )
    assert analysis_response.status_code == 200, analysis_response.text
    analysis = analysis_response.json()
    analysis_id = analysis['analysis_run_id']
    assert analysis['artifacts']
    assert analysis['assumptions']
    assert analysis['caveats']
    stationarity_assumption = next(
        item for item in analysis['assumptions']
        if item['assumption_name'] == 'series_stationarity'
    )
    assert stationarity_assumption['notes'] != 'no_profile_data'
    assert 'revenue:' in stationarity_assumption['notes']
    assert 'traffic:' in stationarity_assumption['notes']

    recovery_client = TestClient(app)
    recovered_analysis = recovery_client.get(f'/api/v1/analysis-runs/{analysis_id}')
    assert recovered_analysis.status_code == 200, recovered_analysis.text
    recovered_payload = recovered_analysis.json()
    assert recovered_payload['analysis_run_id'] == analysis_id
    assert recovered_payload['artifacts'] == analysis['artifacts']
    assert recovered_payload['assumptions'] == analysis['assumptions']
    assert recovered_payload['caveats'] == analysis['caveats']

    recovered_dataset = recovery_client.get(f'/api/v1/datasets/{dataset_id}')
    assert recovered_dataset.status_code == 200, recovered_dataset.text
    recovered_raw_version = next(
        item for item in recovered_dataset.json()['versions']
        if item['dataset_version_id'] == version_id
    )
    assert recovered_raw_version['row_count'] == 6
    assert recovered_raw_version['source_row_count'] == 7
    assert recovered_raw_version['dropped_row_count'] == 1
    assert recovered_raw_version['content_hash'] == expected_hash

    unsupported_response = recovery_client.post(
        '/api/v1/analysis-runs',
        json={
            'dataset_version_id': transformed_version_id,
            'method_name': 'unsupported_operator_method',
            'goal_type': 'exploratory',
            'parameters': {},
            'annotation_window_id': annotation_id,
        },
    )
    assert unsupported_response.status_code == 200, unsupported_response.text
    unsupported_payload = unsupported_response.json()
    assert unsupported_payload['status'] == 'completed'
    assert unsupported_payload['artifacts'] == []
    assert any(
        item['caveat_type'] == 'unsupported_method'
        and item['severity'] == 'high'
        and all(method in item['message'] for method in SUPPORTED_ANALYSIS_METHOD_IDS)
        for item in unsupported_payload['caveats']
    )

    recovered_unsupported = recovery_client.get(
        f"/api/v1/analysis-runs/{unsupported_payload['analysis_run_id']}"
    )
    assert recovered_unsupported.status_code == 200, recovered_unsupported.text
    assert recovered_unsupported.json()['caveats'] == unsupported_payload['caveats']


def test_year_column_and_placeholders_are_handled():
    csv_bytes = (
        b"DataSource,Commodity,Year,Imports,Exports,NIR\n"
        b"MCS,Lead,2020,10,Less than 1/2 unit.,25\n"
        b"MCS,Lead,2021,11,1,36\n"
        b"MCS,Lead,2022,12,W,38\n"
        b",,,,,\n"
    )
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('lead.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Lead', 'description': 'Placeholder test', 'domain_pack': 'commodity'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']
    assert payload['time_column'] == 'Year'
    assert payload['row_count'] == 3
    assert payload['source_row_count'] == 4
    assert payload['dropped_row_count'] == 1
    assert payload['content_hash'] == hashlib.sha256(csv_bytes).hexdigest()

    db = TestingSessionLocal()
    try:
        version = db.get(DatasetVersion, version_id)
        assert version is not None
        assert version.row_count == 3
        assert version.source_row_count == 4
        assert version.dropped_row_count == 1
        assert version.content_hash == hashlib.sha256(csv_bytes).hexdigest()
    finally:
        db.close()

    detail_response = client.get(f'/api/v1/datasets/{dataset_id}')
    assert detail_response.status_code == 200, detail_response.text
    [version_detail] = [
        item for item in detail_response.json()['versions']
        if item['dataset_version_id'] == version_id
    ]
    assert version_detail['row_count'] == 3
    assert version_detail['source_row_count'] == 4
    assert version_detail['dropped_row_count'] == 1
    assert version_detail['content_hash'] == hashlib.sha256(csv_bytes).hexdigest()


def test_upload_content_hash_is_stable_for_identical_source_bytes():
    csv_bytes = (
        b"year,amount\n"
        b"2020,10\n"
        b",\n"
        b"2021,11\n"
    )
    expected_hash = hashlib.sha256(csv_bytes).hexdigest()

    responses = [
        client.post(
            '/api/v1/sources/upload',
            files={'file': ('stable-source.csv', io.BytesIO(csv_bytes), 'text/csv')},
            data={'name': f'Stable Source {idx}', 'description': 'Hash stability', 'domain_pack': 'macro'},
        )
        for idx in range(2)
    ]

    for response in responses:
        assert response.status_code == 200, response.text

    payloads = [response.json() for response in responses]
    assert payloads[0]['dataset_version_id'] != payloads[1]['dataset_version_id']
    assert [payload['content_hash'] for payload in payloads] == [expected_hash, expected_hash]
    assert [payload['source_row_count'] for payload in payloads] == [3, 3]
    assert [payload['row_count'] for payload in payloads] == [2, 2]
    assert [payload['dropped_row_count'] for payload in payloads] == [1, 1]


def test_upload_counts_blank_csv_lines_as_dropped_source_rows():
    csv_bytes = (
        b"year,amount\n"
        b"2020,10\n"
        b"\n"
        b"2021,11\n"
    )

    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('blank-line-source.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Blank Line Source', 'description': 'Blank line fidelity', 'domain_pack': 'macro'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['row_count'] == 2
    assert payload['source_row_count'] == 3
    assert payload['dropped_row_count'] == 1
    assert payload['content_hash'] == hashlib.sha256(csv_bytes).hexdigest()


def test_descriptive_summary_classifies_numeric_after_placeholder_nulls():
    summary = _descriptive_column_summary(pd.Series(["10", "W", "12"]), is_time_column=False)

    assert summary["inferred_class"] == "numeric"
    assert summary["missing_count"] == 1
    assert summary["non_null_count"] == 2
    assert summary["numeric_summary"]["non_null_count"] == 2


def test_storage_ref_uses_parquet_and_stationarity_is_returned():
    csv_bytes = (
        b"year,a,b\n"
        b"2018,10,20\n"
        b"2019,11,21\n"
        b"2020,12,22\n"
        b"2021,13,24\n"
        b"2022,14,26\n"
        b"2023,15,28\n"
        b"2024,16,30\n"
        b"2025,17,33\n"
        b"2026,18,35\n"
        b"2027,19,38\n"
        b"2028,20,40\n"
        b"2029,21,43\n"
    )
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('years.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Years', 'description': 'Stationarity test', 'domain_pack': 'macro'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']

    detail = client.get(f'/api/v1/datasets/{dataset_id}')
    assert detail.status_code == 200, detail.text

    from app.db.session import SessionLocal
    from app.models import DatasetVersion
    db = SessionLocal()
    try:
        version = db.get(DatasetVersion, version_id)
        assert version is not None
        assert version.storage_ref is not None
        assert version.storage_ref.endswith('.parquet')
    finally:
        db.close()

    profile_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile',
        json={'detect_seasonality': False, 'detect_stationarity': True},
    )
    assert profile_response.status_code == 200, profile_response.text
    profiles = profile_response.json()
    assert profiles
    assert all(profile['stationarity_hint'] is not None for profile in profiles)


def test_decomposition_and_break_detection_persist_artifacts():
    rows = ['date,value_a,value_b']
    dates = [
        '2021-01-01','2021-02-01','2021-03-01','2021-04-01','2021-05-01','2021-06-01','2021-07-01','2021-08-01','2021-09-01','2021-10-01','2021-11-01','2021-12-01',
        '2022-01-01','2022-02-01','2022-03-01','2022-04-01','2022-05-01','2022-06-01','2022-07-01','2022-08-01','2022-09-01','2022-10-01','2022-11-01','2022-12-01',
        '2023-01-01','2023-02-01','2023-03-01','2023-04-01','2023-05-01','2023-06-01','2023-07-01','2023-08-01','2023-09-01','2023-10-01','2023-11-01','2023-12-01',
    ]
    for i, date_value in enumerate(dates):
        base = 10 + i * 0.3
        seasonal = 3 if i % 12 < 6 else -3
        shift = 0 if i < 24 else 5
        rows.append(f'{date_value},{base + seasonal + shift:.2f},{20 + 0.5 * i + (-seasonal) + shift:.2f}')
    csv_bytes = ('\n'.join(rows) + '\n').encode()
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('seasonal.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Seasonal', 'description': 'Decomposition dataset', 'domain_pack': 'macro', 'primary_time_column': 'date'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']

    profile_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile',
        json={'detect_seasonality': True, 'detect_stationarity': True},
    )
    assert profile_response.status_code == 200, profile_response.text

    rec_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/analysis/recommend',
        json={'goal_type': 'exploratory'},
    )
    assert rec_response.status_code == 200, rec_response.text
    assert rec_response.json()['recommended_sequence'] == ['cross_correlation', 'decomposition', 'structural_break']

    decomp = client.post(
        '/api/v1/analysis-runs',
        json={'dataset_version_id': version_id, 'method_name': 'decomposition', 'goal_type': 'exploratory', 'parameters': {}, 'annotation_window_id': None},
    )
    assert decomp.status_code == 200, decomp.text
    decomp_payload = decomp.json()
    artifact_types = {item['artifact_type'] for item in decomp_payload['artifacts']}
    assert 'decomposition_components' in artifact_types
    assert 'decomposition_plot' in artifact_types
    assumption_names = {item['assumption_name'] for item in decomp_payload['assumptions']}
    assert {'sufficient_observations', 'time_regularity', 'stationarity_of_residual'}.issubset(assumption_names)

    breaks = client.post(
        '/api/v1/analysis-runs',
        json={'dataset_version_id': version_id, 'method_name': 'structural_break', 'goal_type': 'exploratory', 'parameters': {'penalty': 2.0}, 'annotation_window_id': None},
    )
    assert breaks.status_code == 200, breaks.text
    break_payload = breaks.json()
    break_artifacts = {item['artifact_type'] for item in break_payload['artifacts']}
    assert 'structural_break_result' in break_artifacts
    assert 'structural_break_plot' in break_artifacts

    result_artifact = next(item for item in break_payload['artifacts'] if item['artifact_type'] == 'structural_break_result')
    from pathlib import Path as _Path
    import json as _json
    result_payload = _json.loads((_Path(os.environ['STORAGE_DIR']) / 'artifacts' / _Path(result_artifact['storage_ref']).name).read_text())
    assert result_payload['working_series_source'] == 'cached_stl_residual'
    assert result_payload['model_used'] == 'l2'


def test_structural_break_zero_breakpoint_path_returns_caveat_not_blank_artifact():
    rows = ['date,value']
    dates = [
        '2021-01-01','2021-02-01','2021-03-01','2021-04-01','2021-05-01','2021-06-01','2021-07-01','2021-08-01','2021-09-01','2021-10-01','2021-11-01','2021-12-01',
        '2022-01-01','2022-02-01','2022-03-01','2022-04-01','2022-05-01','2022-06-01','2022-07-01','2022-08-01','2022-09-01','2022-10-01','2022-11-01','2022-12-01',
        '2023-01-01','2023-02-01','2023-03-01','2023-04-01','2023-05-01','2023-06-01','2023-07-01','2023-08-01','2023-09-01','2023-10-01','2023-11-01','2023-12-01',
    ]
    for i, date_value in enumerate(dates):
        base = 10 + i * 0.4
        seasonal = 2 if i % 12 < 6 else -2
        rows.append(f'{date_value},{base + seasonal:.2f}')
    csv_bytes = ('\n'.join(rows) + '\n').encode()
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('stable.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Stable', 'description': 'No structural break dataset', 'domain_pack': 'macro', 'primary_time_column': 'date'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']

    profile_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile',
        json={'detect_seasonality': True, 'detect_stationarity': True},
    )
    assert profile_response.status_code == 200, profile_response.text

    decomp = client.post(
        '/api/v1/analysis-runs',
        json={'dataset_version_id': version_id, 'method_name': 'decomposition', 'goal_type': 'exploratory', 'parameters': {}, 'annotation_window_id': None},
    )
    assert decomp.status_code == 200, decomp.text

    breaks = client.post(
        '/api/v1/analysis-runs',
        json={'dataset_version_id': version_id, 'method_name': 'structural_break', 'goal_type': 'exploratory', 'parameters': {'penalty': 8.0}, 'annotation_window_id': None},
    )
    assert breaks.status_code == 200, breaks.text
    break_payload = breaks.json()
    assert not break_payload['artifacts']
    caveat_types = {item['caveat_type'] for item in break_payload['caveats']}
    assert 'no_breakpoints_detected' in caveat_types


def test_decomposition_short_series_returns_caveat_not_exception():
    rows = ['date,value']
    for i in range(12):
        rows.append(f'2024-{i + 1:02d}-01,{10 + i}')
    csv_bytes = ('\n'.join(rows) + '\n').encode()
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('short.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'Short', 'description': 'Short series', 'domain_pack': 'macro', 'primary_time_column': 'date'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload['dataset_id']
    version_id = payload['dataset_version_id']

    profile_response = client.post(
        f'/api/v1/datasets/{dataset_id}/versions/{version_id}/profile',
        json={'detect_seasonality': True, 'detect_stationarity': True},
    )
    assert profile_response.status_code == 200, profile_response.text

    decomp = client.post(
        '/api/v1/analysis-runs',
        json={'dataset_version_id': version_id, 'method_name': 'decomposition', 'goal_type': 'exploratory', 'parameters': {}, 'annotation_window_id': None},
    )
    assert decomp.status_code == 200, decomp.text
    payload = decomp.json()
    assert any(item['caveat_type'] == 'insufficient_observations' for item in payload['caveats'])

def test_cp1252_csv_upload_fallback_is_supported():
    csv_text = (
        'Year,Commodity,Notes,Value\n'
        '2024,Nickel,Range \u2014 high,12\n'
        '2025,Nickel,Range \u2014 low,13\n'
    )
    csv_bytes = csv_text.encode('cp1252')
    response = client.post(
        '/api/v1/sources/upload',
        files={'file': ('cp1252.csv', io.BytesIO(csv_bytes), 'text/csv')},
        data={'name': 'CP1252', 'description': 'Encoding fallback test', 'domain_pack': 'commodity'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['row_count'] == 2
    assert payload['time_column'] == 'Year'

    from app.db.session import SessionLocal
    from app.models import DatasetVersion

    db = SessionLocal()
    try:
        version = db.get(DatasetVersion, payload['dataset_version_id'])
        assert version is not None
        assert 'csv_encoding=cp1252' in (version.notes or '')
    finally:
        db.close()


class _FakeSearchOnlyAdapter:
    def search_page(self, *, q, filters, offset, page_size, sort, order):
        return type(
            "SearchPage",
            (),
            {
                "items": [],
                "offset": offset,
                "page_size": page_size,
                "total": 0,
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {}

    def extract_artifacts(self, item):
        return []

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        raise RuntimeError("download should not be called")


class _FakeSurfaceAdapter:
    def __init__(self, namespace: str = ""):
        self.namespace = namespace

    def _name(self, stem: str) -> str:
        return f"{stem}-{self.namespace}" if self.namespace else stem

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        if offset > 0:
            items = []
        else:
            items = [{"id": self._name("item-1")}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": self._name("Item"),
            "identifiers": [
                {"type": "DOI", "value": self._name("10.1234/example")},
            ],
            "files": [
                {
                    "name": f"{self._name('good')}.csv",
                    "downloadUri": f"https://www.sciencebase.gov/catalog/file/{self._name('good')}.csv",
                },
                {
                    "name": f"{self._name('bad')}.csv",
                    "downloadUri": f"http://www.sciencebase.gov/catalog/file/{self._name('bad')}.csv",
                },
            ],
            "webLinks": [
                {
                    "title": self._name("external"),
                    "uri": f"https://example.com/{self._name('external')}.csv",
                },
            ],
            "distributionLinks": [],
        }

    def extract_artifacts(self, item):
        out = []
        for raw in item.get("files") or []:
            out.append(
                {
                    "surface": "files",
                    "name": raw["name"],
                    "url": raw.get("downloadUri") or raw.get("url"),
                    "locator_type": "downloadUri" if raw.get("downloadUri") else "url",
                    "checksum_type": None,
                    "checksum_value": None,
                    "source_reference": raw,
                }
            )
        for raw in item.get("webLinks") or []:
            out.append(
                {
                    "surface": "webLinks",
                    "name": raw["title"],
                    "url": raw["uri"],
                    "locator_type": "webLink",
                    "checksum_type": None,
                    "checksum_value": None,
                    "source_reference": raw,
                }
            )
        return out

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        csv = b"year,a,b\n2020,1,2\n2021,2,3\n2022,3,4\n2023,4,5\n2024,5,6\n2025,6,7\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url.replace("http://", "https://"),
                "redirect_count": 0,
                "etag": "etag-1",
                "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": self._name("fake_sha_surface"),
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _FakeScienceBaseSourceFidelityAdapter(_FakeSurfaceAdapter):
    csv_bytes = (
        b"year,value\n"
        b"2020,10\n"
        b"2021,20\n"
        b",\n"
        b"2022,30\n"
    )

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Item",
            "identifiers": [{"type": "DOI", "value": "10.1234/example"}],
            "files": [
                {"name": "good.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/good.csv"},
            ],
            "webLinks": [],
            "distributionLinks": [],
        }

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        return type(
            "DownloadResult",
            (),
            {
                "content": self.csv_bytes,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": "etag-source-fidelity",
                "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": hashlib.sha256(self.csv_bytes).hexdigest(),
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


MCS_2026_PARENT_ITEM_ID = "696a75d5d4be0228872d3bf8"
MCS_2026_COMMODITIES_ITEM_ID = "69837e43b66b01367d7ec7c7"
MCS_2026_TRENDS_ITEM_ID = "69837ec8b66b01367d7ec7d9"
MCS_2026_COMMODITIES_DOWNLOAD_URI = (
    f"https://www.sciencebase.gov/catalog/file/get/{MCS_2026_COMMODITIES_ITEM_ID}?f=MCS2026_Commodities_Data.csv"
)
MCS_2026_TRENDS_DOWNLOAD_URI = (
    f"https://www.sciencebase.gov/catalog/file/get/{MCS_2026_TRENDS_ITEM_ID}?f=MCS2026_T1_Mineral_Industry_Trends.csv"
)


class _FakeMcs2026ScienceBaseAdapter:
    # Phase 0 provenance: official ScienceBase metadata lists the 2026 MCS
    # release as a parent item with two child Data Release items and CSV files.
    commodity_csv_bytes = (
        b"year,commodity,us_production,apparent_consumption,net_import_reliance\n"
        b"2021,Aluminum,880,3900,44\n"
        b"2022,Aluminum,860,3800,45\n"
        b"2023,Aluminum,750,3700,46\n"
        b"2024,Aluminum,670,3600,47\n"
        b"2025,Aluminum,700,3650,48\n"
    )
    trends_csv_bytes = (
        b"year,table,value\n"
        b"2021,T1_Mineral_Industry_Trends,100\n"
        b"2022,T1_Mineral_Industry_Trends,105\n"
        b"2023,T1_Mineral_Industry_Trends,111\n"
        b"2024,T1_Mineral_Industry_Trends,116\n"
        b"2025,T1_Mineral_Industry_Trends,121\n"
    )

    def __init__(self, *, external_download_url: str | None = None):
        self.external_download_url = external_download_url
        self.search_calls = []
        self.hydrate_calls = []
        self.download_calls = []

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        self.search_calls.append(
            {
                "q": q,
                "filters": list(filters),
                "offset": offset,
                "page_size": page_size,
                "sort": sort,
                "order": order,
            }
        )
        return type(
            "SearchPage",
            (),
            {
                "items": [],
                "offset": offset,
                "page_size": page_size,
                "total": 0,
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        self.hydrate_calls.append(item_id)
        if item_id == MCS_2026_PARENT_ITEM_ID:
            return {
                "id": MCS_2026_PARENT_ITEM_ID,
                "title": "Mineral Commodity Summaries 2026 Data Release",
                "identifiers": [{"type": "DOI", "value": "10.5066/P1WKQ63T"}],
                "files": [],
                "webLinks": [],
                "distributionLinks": [],
            }
        if item_id == MCS_2026_COMMODITIES_ITEM_ID:
            return {
                "id": MCS_2026_COMMODITIES_ITEM_ID,
                "title": "Mineral Commodity Summaries 2026 Data Release - Commodity Salient U.S. and World Statistics",
                "identifiers": [{"type": "DOI", "value": "10.5066/P1WKQ63T"}],
                "files": [
                    {
                        "name": "MCS2026_Commodities_Data.csv",
                        "downloadUri": self.external_download_url or MCS_2026_COMMODITIES_DOWNLOAD_URI,
                    }
                ],
                "webLinks": [],
                "distributionLinks": [],
            }
        if item_id == MCS_2026_TRENDS_ITEM_ID:
            return {
                "id": MCS_2026_TRENDS_ITEM_ID,
                "title": "Mineral Commodity Summaries 2026 Data Release - Mineral Industry Trends and Salient Statistics",
                "identifiers": [{"type": "DOI", "value": "10.5066/P1WKQ63T"}],
                "files": [
                    {
                        "name": "MCS2026_T1_Mineral_Industry_Trends.csv",
                        "downloadUri": MCS_2026_TRENDS_DOWNLOAD_URI,
                    }
                ],
                "webLinks": [],
                "distributionLinks": [],
            }
        raise AssertionError(f"unexpected MCS 2026 item id: {item_id}")

    def extract_artifacts(self, item):
        return [
            {
                "surface": "files",
                "name": raw["name"],
                "url": raw["downloadUri"],
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": raw,
            }
            for raw in item.get("files") or []
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        self.download_calls.append(url)
        if url == MCS_2026_COMMODITIES_DOWNLOAD_URI:
            content = self.commodity_csv_bytes
            etag = "mcs-2026-commodities-etag"
        elif url == MCS_2026_TRENDS_DOWNLOAD_URI:
            content = self.trends_csv_bytes
            etag = "mcs-2026-trends-etag"
        else:
            raise AssertionError(f"unexpected MCS 2026 artifact URL: {url}")
        return type(
            "DownloadResult",
            (),
            {
                "content": content,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": etag,
                "last_modified": "Fri, 06 Feb 2026 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": hashlib.sha256(content).hexdigest(),
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _FakeDedupAdapter:
    def search_page(self, *, q, filters, offset, page_size, sort, order):
        if offset > 0:
            items = []
        else:
            items = [{"id": "item-dedup"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Dedup item",
            "identifiers": [{"type": "DOI", "value": "10.9999/dedup"}],
            "files": [{"name": "same.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/same.csv"}],
            "distributionLinks": [{"title": "same.csv", "uri": "https://www.sciencebase.gov/catalog/file/same.csv"}],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        return [
            {
                "surface": "files",
                "name": "same.csv",
                "url": "https://www.sciencebase.gov/catalog/file/same.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            },
            {
                "surface": "distributionLinks",
                "name": "same.csv",
                "url": "https://www.sciencebase.gov/catalog/file/same.csv",
                "locator_type": "distributionLink",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "distributionLinks"},
            },
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        csv = b"year,a,b\n2020,1,2\n2021,2,3\n2022,3,4\n2023,4,5\n2024,5,6\n2025,6,7\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": "etag-dedup",
                "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": "fake_sha_dedup",
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _FakePartitionAdapter:
    def __init__(self):
        self.search_calls = []

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        self.search_calls.append(
            {
                "q": q,
                "filters": list(filters),
                "offset": offset,
                "page_size": page_size,
                "sort": sort,
                "order": order,
            }
        )
        items = [] if offset > 0 else [{"id": f"{q}-{len(self.search_calls)}"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {"q": q, "filters": filters},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Partition item",
            "identifiers": [],
            "files": [{"name": "partition.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/partition.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        return [
            {
                "surface": "files",
                "name": "partition.csv",
                "url": "https://www.sciencebase.gov/catalog/file/partition.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        raise RuntimeError("download should not be called for ignored extensions")


class _FakeConditionalAdapter:
    def __init__(self):
        self.request_headers = []

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        items = [] if offset > 0 else [{"id": "item-conditional"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Conditional item",
            "identifiers": [],
            "files": [{"name": "conditional.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/conditional.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        return [
            {
                "surface": "files",
                "name": "conditional.csv",
                "url": "https://www.sciencebase.gov/catalog/file/conditional.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        sent_headers = dict(headers or {})
        self.request_headers.append(sent_headers)
        if sent_headers.get("If-None-Match") == "etag-conditional":
            return type(
                "DownloadResult",
                (),
                {
                    "content": b"",
                    "status_code": 304,
                    "final_url": url,
                    "redirect_count": 0,
                    "etag": "etag-conditional",
                    "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                    "content_type": "text/csv",
                    "sha256": "",
                    "headers": {"etag": "etag-conditional"},
                    "resolved_ip": "8.8.8.8",
                },
            )()

        csv = b"year,value\n2020,1\n2021,2\n2022,3\n2023,4\n2024,5\n2025,6\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": "etag-conditional",
                "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": "sha-conditional-v1",
                "headers": {"etag": "etag-conditional"},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _FakeConditionalRevalidate200Adapter:
    def __init__(self):
        self.request_headers = []

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        items = [] if offset > 0 else [{"id": "item-conditional-200"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Conditional 200 item",
            "identifiers": [],
            "files": [{"name": "conditional_200.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/conditional_200.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        return [
            {
                "surface": "files",
                "name": "conditional_200.csv",
                "url": "https://www.sciencebase.gov/catalog/file/conditional_200.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        self.request_headers.append(dict(headers or {}))
        csv = b"year,value\n2020,1\n2021,2\n2022,3\n2023,4\n2024,5\n2025,6\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": "etag-conditional-200",
                "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": "sha-conditional-200",
                "headers": {"etag": "etag-conditional-200"},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _FakeResumeDiscoveryAdapter:
    def __init__(self):
        self.search_calls = []
        self.fail_once = True

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        self.search_calls.append({"q": q, "offset": offset, "page_size": page_size})
        if q == "MCS 2026" and offset == 0 and self.fail_once:
            self.fail_once = False
            raise RuntimeError("transient discovery failure")
        if offset > 0:
            items = []
        elif q == "MCS 2025":
            items = [{"id": "item-2025"}]
        elif q == "MCS 2026":
            items = [{"id": "item-2026"}]
        else:
            items = []
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Resume discovery item",
            "identifiers": [],
            "files": [{"name": f"{item_id}.csv", "downloadUri": f"https://www.sciencebase.gov/catalog/file/{item_id}.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        item_id = item["id"]
        return [
            {
                "surface": "files",
                "name": f"{item_id}.csv",
                "url": f"https://www.sciencebase.gov/catalog/file/{item_id}.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        raise RuntimeError("download should not be called for ignored extensions")


class _FakeResumeTargetCursorAdapter:
    def __init__(self):
        self.download_attempts = {"first": 0, "second": 0}

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        if offset > 0:
            items = []
        else:
            items = [{"id": "item-first"}, {"id": "item-second"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        filename = "first.csv" if item_id == "item-first" else "second.csv"
        return {
            "id": item_id,
            "title": f"Resume target {item_id}",
            "identifiers": [],
            "files": [{"name": filename, "downloadUri": f"https://www.sciencebase.gov/catalog/file/{filename}"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        raw = item["files"][0]
        return [
            {
                "surface": "files",
                "name": raw["name"],
                "url": raw["downloadUri"],
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        if url.endswith("/first.csv"):
            self.download_attempts["first"] += 1
            if self.download_attempts["first"] == 1:
                raise requests.Timeout("simulated timeout")
        elif url.endswith("/second.csv"):
            self.download_attempts["second"] += 1
        csv = b"year,value\n2020,1\n2021,2\n2022,3\n2023,4\n2024,5\n2025,6\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": None,
                "last_modified": None,
                "content_type": "text/csv",
                "sha256": f"sha-{Path(url).name}",
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _UnexpectedScienceBaseAdapter:
    def search_page(self, *, q, filters, offset, page_size, sort, order):
        raise AssertionError("sciencebase adapter should not execute")


class _FakeCancelDuringDownloadAdapter:
    def __init__(self):
        self.run_id = None
        self.download_calls = 0

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        return type(
            "SearchPage",
            (),
            {
                "items": [] if offset > 0 else [{"id": "item-cancel"}],
                "offset": offset,
                "page_size": page_size,
                "total": 1,
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Cancel target item",
            "identifiers": [],
            "files": [{"name": "cancel.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/cancel.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        return [
            {
                "surface": "files",
                "name": "cancel.csv",
                "url": "https://www.sciencebase.gov/catalog/file/cancel.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        assert self.run_id is not None
        self.download_calls += 1
        from app.db.session import SessionLocal
        from app.services.connectors_sciencebase import request_cancel_run

        db = SessionLocal()
        try:
            request_cancel_run(db, self.run_id)
        finally:
            db.close()
        csv = b"year,value\n2020,1\n2021,2\n2022,3\n2023,4\n2024,5\n2025,6\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": None,
                "last_modified": None,
                "content_type": "text/csv",
                "sha256": "sha-cancel",
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _L17ScienceBaseAdapter:
    def __init__(self, *, download_case="timeout", empty_page_next=False, malformed_item=False, namespace=""):
        self.download_case = download_case
        self.empty_page_next = empty_page_next
        self.malformed_item = malformed_item
        self.namespace = namespace

    def _name(self, stem):
        return f"{stem}-{self.namespace}" if self.namespace else stem

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        if self.empty_page_next and offset == 0:
            items = []
            nextlink = "https://www.sciencebase.gov/catalog/items?page=2"
        elif offset == 0:
            items = [{"id": self._name("l17-item"), "unexpected_additive_field": "kept-for-schema-drift"}]
            nextlink = None
        else:
            items = []
            nextlink = None
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": nextlink,
                "prevlink": None,
                "raw_query_metadata": {"fixture": "l17"},
            },
        )()

    def hydrate_item(self, item_id):
        if self.malformed_item:
            return {"title": "Missing required ScienceBase item id", "files": []}
        return {
            "id": item_id,
            "title": "L17 ScienceBase item",
            "identifiers": [],
            "files": [
                {
                    "name": f"{self._name('l17')}.csv",
                    "downloadUri": f"https://www.sciencebase.gov/catalog/file/{self._name('l17')}.csv",
                }
            ],
            "distributionLinks": [],
            "webLinks": [],
            "unexpected_additive_field": "tolerated",
        }

    def extract_artifacts(self, item):
        if not item.get("id"):
            raise ValueError("missing_required_field:item_id")
        return [
            {
                "surface": "files",
                "name": f"{self._name('l17')}.csv",
                "url": f"https://www.sciencebase.gov/catalog/file/{self._name('l17')}.csv",
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files", "unexpected_additive_field": item.get("unexpected_additive_field")},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        if self.download_case == "timeout":
            raise requests.Timeout("simulated bounded timeout")
        if self.download_case == "http_403":
            response = requests.Response()
            response.status_code = 403
            response.url = url
            error = requests.HTTPError("403 Forbidden", response=response)
            raise error
        if self.download_case == "redirect_private":
            return type(
                "DownloadResult",
                (),
                {
                    "content": b"year,value\n2025,1\n",
                    "status_code": 200,
                    "final_url": "https://sciencebase.gov/private.csv",
                    "redirect_count": 1,
                    "etag": None,
                    "last_modified": None,
                    "content_type": "text/csv",
                    "sha256": "sha-redirect-private",
                    "headers": {},
                    "resolved_ip": "127.0.0.1",
                },
            )()
        return type(
            "DownloadResult",
            (),
            {
                "content": b"year,value\n2025,1\n",
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": None,
                "last_modified": None,
                "content_type": "text/csv",
                "sha256": self._name("sha-l17"),
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


def test_connector_submission_idempotency_key_behaviour(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeSearchOnlyAdapter())

    payload = {"q": "MCS", "run_mode": "dry_run"}
    first = client.post("/api/v1/connectors/sciencebase-public/runs", json=payload, headers={"Idempotency-Key": "run-key-1"})
    assert first.status_code == 202, first.text
    first_payload = first.json()
    assert first_payload["created"] is True

    second = client.post("/api/v1/connectors/sciencebase-public/runs", json=payload, headers={"Idempotency-Key": "run-key-1"})
    assert second.status_code == 202, second.text
    second_payload = second.json()
    assert second_payload["created"] is False
    assert second_payload["connector_run_id"] == first_payload["connector_run_id"]

    conflict = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS changed"},
        headers={"Idempotency-Key": "run-key-1"},
    )
    assert conflict.status_code == 409, conflict.text

    no_key_a = client.post("/api/v1/connectors/sciencebase-public/runs", json=payload)
    no_key_b = client.post("/api/v1/connectors/sciencebase-public/runs", json=payload)
    assert no_key_a.status_code == 202 and no_key_b.status_code == 202
    assert no_key_a.json()["connector_run_id"] != no_key_b.json()["connector_run_id"]


def test_connector_fetch_policy_blocks_http_and_non_enabled_surfaces(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(
        sb,
        "get_sciencebase_adapter",
        lambda config: _FakeSurfaceAdapter("fetch-policy"),
    )

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "surface_policy": "files_only",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": f"surface-policy-run-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    statuses = {item["status"] for item in targets.json()["targets"]}
    assert "recommended" in statuses
    assert "blocked_by_fetch_policy" in statuses
    assert "unsupported_artifact_surface" in statuses


def test_connector_cross_surface_dedupe_prefers_files(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorArtifactAlias, ConnectorRunTarget

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeDedupAdapter())

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "surface_policy": "all_supported",
            "allowed_extensions": [".csv"],
            "run_mode": "one_shot_import",
        },
        headers={"Idempotency-Key": f"dedupe-run-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    targets_resp = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets_resp.status_code == 200, targets_resp.text
    targets = targets_resp.json()["targets"]
    assert any(item["status"] == "collapsed_duplicate" for item in targets)
    winner = next(item for item in targets if item["status"] in {"recommended", "selected", "downloaded", "ingested", "profiled"})
    assert winner["artifact_surface"] == "files"

    db = SessionLocal()
    try:
        target_rows = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        assert [target.ordinal for target in target_rows] == [1, 2]
        assert [target.artifact_surface for target in target_rows] == ["files", "distributionLinks"]
        assert [target.status for target in target_rows].count("collapsed_duplicate") == 1
        winner_row = next(target for target in target_rows if target.status != "collapsed_duplicate")
        collapsed_row = next(target for target in target_rows if target.status == "collapsed_duplicate")
        assert winner_row is not None
        assert winner_row.source_reference_json["surface"] == "files"
        assert collapsed_row.source_reference_json["surface"] == "distributionLinks"
        aliases = (
            db.query(ConnectorArtifactAlias)
            .filter(ConnectorArtifactAlias.connector_run_target_id == winner_row.connector_run_target_id)
            .order_by(ConnectorArtifactAlias.alias_surface.asc())
            .all()
        )
        assert len(aliases) == 1
        assert aliases[0].alias_surface == "distributionLinks"
        assert aliases[0].alias_json["surface"] == "distributionLinks"
    finally:
        db.close()


def test_connector_partition_strategy_configured_slices_plans_queries(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRun

    adapter = _FakePartitionAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "partition_strategy": "configured_slices",
            "configured_slices": [
                {
                    "label": "y2025",
                    "q": "MCS 2025",
                    "filters": ["systemType=Data Release", "dateRange=2025-01-01,2025-12-31"],
                },
                {
                    "label": "y2026",
                    "q": "MCS 2026",
                    "filters": ["systemType=Data Release", "dateRange=2026-01-01,2026-12-31"],
                },
            ],
            "allowed_extensions": [".txt"],
        },
        headers={"Idempotency-Key": "partition-slices-run"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    offset_zero_calls = [call for call in adapter.search_calls if call["offset"] == 0]
    assert len(offset_zero_calls) == 2
    assert {call["q"] for call in offset_zero_calls} == {"MCS 2025", "MCS 2026"}

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.discovery_snapshot_ref
        snapshot = json.loads(Path(run.discovery_snapshot_ref).read_text(encoding="utf-8"))
        assert snapshot["partition_strategy"] == "configured_slices"
        assert [part["label"] for part in snapshot["partitions"]] == ["y2025", "y2026"]
        assert len(snapshot["pages"]) >= 2
    finally:
        db.close()


def test_connector_recurring_sync_uses_conditional_fetch_and_handles_304(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget, ConnectorTargetStageAttempt

    adapter = _FakeConditionalAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    first = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "conditional-seed-run"},
    )
    assert first.status_code == 202, first.text
    first_run_id = first.json()["connector_run_id"]

    first_targets = client.get(f"/api/v1/connectors/runs/{first_run_id}/targets")
    assert first_targets.status_code == 200, first_targets.text
    assert any(item["status"] == "recommended" for item in first_targets.json()["targets"])

    second = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "recurring_sync",
            "conditional_request_policy": "etag_then_last_modified",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "conditional-sync-run"},
    )
    assert second.status_code == 202, second.text
    second_run_id = second.json()["connector_run_id"]

    second_targets = client.get(f"/api/v1/connectors/runs/{second_run_id}/targets")
    assert second_targets.status_code == 200, second_targets.text
    statuses = {item["status"] for item in second_targets.json()["targets"]}
    assert "not_modified_remote" in statuses

    db = SessionLocal()
    try:
        run_row = db.get(ConnectorRun, second_run_id)
        assert run_row is not None
        assert int(run_row.not_modified_count or 0) >= 1
        assert int(run_row.terminal_target_count or 0) >= 1
        assert int(run_row.nonterminal_target_count or 0) == 0

        skipped_target = (
            db.query(ConnectorRunTarget)
            .filter(
                ConnectorRunTarget.connector_run_id == second_run_id,
                ConnectorRunTarget.status == "not_modified_remote",
            )
            .first()
        )
        assert skipped_target is not None
        assert skipped_target.versioning_reason_code == "not_modified_remote_conditional_304"

        stage_attempt = (
            db.query(ConnectorTargetStageAttempt)
            .filter(
                ConnectorTargetStageAttempt.connector_run_target_id == skipped_target.connector_run_target_id,
                ConnectorTargetStageAttempt.stage == "downloading",
            )
            .order_by(ConnectorTargetStageAttempt.completed_at.desc())
            .first()
        )
        assert stage_attempt is not None
        assert stage_attempt.error_class == "conditional_fetch_miss"

        event_row = (
            db.query(ConnectorRunEvent)
            .filter(
                ConnectorRunEvent.connector_run_id == second_run_id,
                ConnectorRunEvent.connector_run_target_id == skipped_target.connector_run_target_id,
                ConnectorRunEvent.event_type == "target_not_modified_remote",
            )
            .order_by(ConnectorRunEvent.created_at.desc())
            .first()
        )
        assert event_row is not None
    finally:
        db.close()

    assert {} in adapter.request_headers
    assert {"If-None-Match": "etag-conditional"} in adapter.request_headers


def test_connector_recurring_sync_revalidate_200_marks_conditional_skipped_unchanged(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget

    adapter = _FakeConditionalRevalidate200Adapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    seed = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "conditional-200-seed-run"},
    )
    assert seed.status_code == 202, seed.text

    recurring = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "recurring_sync",
            "conditional_request_policy": "etag_then_last_modified",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "conditional-200-sync-run"},
    )
    assert recurring.status_code == 202, recurring.text
    recurring_run_id = recurring.json()["connector_run_id"]

    targets = client.get(f"/api/v1/connectors/runs/{recurring_run_id}/targets")
    assert targets.status_code == 200, targets.text
    statuses = {item["status"] for item in targets.json()["targets"]}
    assert "skipped_unchanged" in statuses

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(
                ConnectorRunTarget.connector_run_id == recurring_run_id,
                ConnectorRunTarget.status == "skipped_unchanged",
            )
            .first()
        )
        assert target is not None
        assert target.operator_reason_code == "skipped_unchanged_after_conditional_revalidate"
        assert target.versioning_reason_code == "skipped_unchanged_after_conditional_revalidate"
    finally:
        db.close()

    assert {} in adapter.request_headers
    assert {"If-None-Match": "etag-conditional-200"} in adapter.request_headers


def test_connector_checkpoint_frequency_controls_checkpoint_granularity(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRunCheckpoint

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeSurfaceAdapter())

    per_page = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "checkpoint_frequency": "per_page",
            "allowed_extensions": [".txt"],
            "surface_policy": "files_only",
        },
        headers={"Idempotency-Key": "checkpoint-per-page"},
    )
    assert per_page.status_code == 202, per_page.text
    per_page_run_id = per_page.json()["connector_run_id"]

    per_target = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "checkpoint_frequency": "per_target",
            "allowed_extensions": [".txt"],
            "surface_policy": "files_only",
        },
        headers={"Idempotency-Key": "checkpoint-per-target"},
    )
    assert per_target.status_code == 202, per_target.text
    per_target_run_id = per_target.json()["connector_run_id"]

    per_stage = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "checkpoint_frequency": "per_stage",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
        },
        headers={"Idempotency-Key": "checkpoint-per-stage"},
    )
    assert per_stage.status_code == 202, per_stage.text
    per_stage_run_id = per_stage.json()["connector_run_id"]

    db = SessionLocal()
    try:
        page_checkpoints = (
            db.query(ConnectorRunCheckpoint)
            .filter(ConnectorRunCheckpoint.connector_run_id == per_page_run_id)
            .all()
        )
        target_checkpoints = (
            db.query(ConnectorRunCheckpoint)
            .filter(ConnectorRunCheckpoint.connector_run_id == per_target_run_id)
            .all()
        )
        stage_checkpoints = (
            db.query(ConnectorRunCheckpoint)
            .filter(ConnectorRunCheckpoint.connector_run_id == per_stage_run_id)
            .all()
        )

        assert all(checkpoint.last_target_id is None for checkpoint in page_checkpoints)
        assert any(checkpoint.last_target_id is not None for checkpoint in target_checkpoints)
        assert any((checkpoint.payload_json or {}).get("stage") in {"downloading", "ingesting", "profiling", "recommending"} for checkpoint in stage_checkpoints)
    finally:
        db.close()


def test_connector_run_observability_contract_fields_present(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeSurfaceAdapter())

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "checkpoint_frequency": "per_stage",
            "surface_policy": "files_only",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "observability-contract-run"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()

    for key in [
        "run_mode",
        "lease_state",
        "checkpoint_summary",
        "cancellation_state",
        "resume_eligibility",
        "retryable_target_count",
        "terminal_target_count",
        "nonterminal_target_count",
        "current_phase",
        "artifact_surface_counts",
        "partition_progress",
        "throughput_summary",
        "fetch_policy_summary",
        "dedupe_summary",
        "report_refs",
        "manifest_refs",
    ]:
        assert key in payload

    assert {"claimed", "lease_owner", "lease_expires_at", "lease_token_redacted_summary"}.issubset(payload["lease_state"].keys())
    assert {"current_partition", "current_page", "last_completed_target_ordinal", "last_committed_stage"}.issubset(payload["checkpoint_summary"].keys())
    assert {"requested", "requested_at", "cancelled_at"}.issubset(payload["cancellation_state"].keys())
    assert {"bytes_downloaded", "bytes_skipped_due_to_unchanged_detection", "targets_per_hour", "average_stage_latency_ms"}.issubset(payload["throughput_summary"].keys())
    assert {"mode", "surface_policy", "external_fetch_policy", "allowed_hosts"}.issubset(payload["fetch_policy_summary"].keys())
    assert "collapsed_duplicate_count" in payload["dedupe_summary"]
    assert {"discovery_snapshot_ref", "selection_manifest_ref"}.issubset(payload["manifest_refs"].keys())

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    first_target = targets.json()["targets"][0]
    for key in [
        "artifact_surface",
        "artifact_locator_type",
        "stable_release_key",
        "source_artifact_key",
        "attempt_count",
        "retry_eligible",
        "last_error_class",
        "last_stage_transition_at",
        "operator_reason_code",
    ]:
        assert key in first_target


def test_connector_run_detail_uses_precomputed_core_counters(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeBudgetAdapter())
    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "max_file_bytes": 2048,
            "max_run_bytes": 2500,
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "precomputed-core-counters-run"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    statements: list[str] = []

    def _capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        text = str(statement or "").lower()
        if "connector_run_target" in text:
            statements.append(text)

    event.listen(engine, "before_cursor_execute", _capture_sql)
    try:
        detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    finally:
        event.remove(engine, "before_cursor_execute", _capture_sql)

    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["retryable_target_count"] == 0
    assert payload["terminal_target_count"] >= 1
    assert payload["nonterminal_target_count"] == 0
    full_target_scan_statements = [
        sql
        for sql in statements
        if " from connector_run_target " in sql and "count(" not in sql
    ]
    assert full_target_scan_statements == []


def test_connector_events_and_reports_endpoints(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeSurfaceAdapter())
    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "report_verbosity": "debug",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
        },
        headers={"Idempotency-Key": "events-and-reports-run"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    events = client.get(f"/api/v1/connectors/runs/{run_id}/events?limit=200&offset=0")
    assert events.status_code == 200, events.text
    events_payload = events.json()
    assert events_payload["connector_run_id"] == run_id
    assert events_payload["total"] >= 1
    event_types = {row["event_type"] for row in events_payload["events"]}
    assert "run_submitted" in event_types
    assert "run_finalized" in event_types

    reports = client.get(f"/api/v1/connectors/runs/{run_id}/reports")
    assert reports.status_code == 200, reports.text
    reports_payload = reports.json()
    assert reports_payload["connector_run_id"] == run_id
    assert "run_summary" in reports_payload["reports"]
    assert reports_payload["report_status"].get("run_summary") is True


def test_connector_resume_reuses_discovery_checkpoint_cursor(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunCheckpoint, ConnectorRunTarget

    adapter = _FakeResumeDiscoveryAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "partition_strategy": "configured_slices",
            "configured_slices": [
                {"label": "y2025", "q": "MCS 2025", "filters": ["systemType=Data Release"]},
                {"label": "y2026", "q": "MCS 2026", "filters": ["systemType=Data Release"]},
            ],
            "page_size": 5,
            "allowed_extensions": [".txt"],
        },
        headers={"Idempotency-Key": "resume-discovery-run"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    first_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert first_detail.status_code == 200, first_detail.text
    assert first_detail.json()["status"] == "failed"

    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text

    second_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert second_detail.status_code == 200, second_detail.text
    assert second_detail.json()["status"] in {"completed", "completed_with_errors"}

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        checkpoints = (
            db.query(ConnectorRunCheckpoint)
            .filter(ConnectorRunCheckpoint.connector_run_id == run_id, ConnectorRunCheckpoint.phase == "discovery")
            .all()
        )
        assert any("page_item_ids" in (checkpoint.payload_json or {}) for checkpoint in checkpoints)
        targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
        assert len(targets) == 2
    finally:
        db.close()

    first_page_calls = [call for call in adapter.search_calls if call["q"] == "MCS 2025" and call["offset"] == 0]
    assert len(first_page_calls) == 1


def test_connector_resume_target_cursor_keeps_retryable_prior_targets(monkeypatch):
    from app.services import connectors_sciencebase as sb

    adapter = _FakeResumeTargetCursorAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "page_size": 5,
            "allowed_extensions": [".csv"],
            "checkpoint_frequency": "per_target",
        },
        headers={"Idempotency-Key": "resume-target-cursor-run"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    first_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert first_detail.status_code == 200, first_detail.text
    assert first_detail.json()["status"] == "completed_with_errors"

    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text

    second_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert second_detail.status_code == 200, second_detail.text
    assert second_detail.json()["status"] == "completed"

    assert adapter.download_attempts["first"] == 2
    assert adapter.download_attempts["second"] == 1


def test_sciencebase_csv_ingest_preserves_l11_source_fidelity(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_sciencebase as sb
    from app.services.dataframe_io import load_version_dataframe

    adapter = _FakeScienceBaseSourceFidelityAdapter()
    expected_hash = hashlib.sha256(adapter.csv_bytes).hexdigest()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
            "detect_seasonality": False,
            "detect_stationarity": False,
        },
        headers={"Idempotency-Key": f"sciencebase-l11-source-fidelity-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.status == "recommended"
        assert target.dataset_version_id
        version = db.get(DatasetVersion, target.dataset_version_id)
        assert version is not None
        assert version.content_hash == expected_hash
        assert version.source_row_count == 4
        assert version.dropped_row_count == 1
        assert version.row_count == 3

        frame = load_version_dataframe(db, target.dataset_version_id)
        assert frame["value"].astype(int).tolist() == [10, 20, 30]

        expected_summary = {
            "content_hash": expected_hash,
            "source_row_count": 4,
            "dropped_row_count": 1,
            "row_count": 3,
        }
        assert target.source_reference_json["ingest_fidelity"] == expected_summary

        provenance = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .one()
        )
        assert provenance.source_artifact_key == target.source_artifact_key
        assert provenance.downloaded_sha256 == expected_hash
        assert provenance.source_reference_json["ingest_fidelity"] == expected_summary
    finally:
        db.close()


def test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunTarget, DatasetVersion
    from app.services import connectors_sciencebase as sb

    journey_item_id = f"journey-{uuid.uuid4().hex}"

    class _JourneyAdapter(_FakeScienceBaseSourceFidelityAdapter):
        csv_bytes = (
            b"year,value,comparison\n"
            b"2020,10,12\n"
            b"2021,20,18\n"
            b",,\n"
            b"2022,30,27\n"
        )

        def search_page(self, *, q, filters, offset, page_size, sort, order):
            page = super().search_page(q=q, filters=filters, offset=offset, page_size=page_size, sort=sort, order=order)
            if offset == 0:
                page.items = [{"id": journey_item_id}]
            return page

        def hydrate_item(self, item_id):
            item = super().hydrate_item(item_id)
            item["id"] = journey_item_id
            item["files"][0]["name"] = f"{journey_item_id}.csv"
            item["files"][0]["downloadUri"] = f"https://www.sciencebase.gov/catalog/file/{journey_item_id}.csv"
            return item

    adapter = _JourneyAdapter()
    expected_hash = hashlib.sha256(adapter.csv_bytes).hexdigest()
    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
            "detect_seasonality": False,
            "detect_stationarity": False,
        },
        headers={"Idempotency-Key": f"sciencebase-operator-journey-bridge-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["connector_key"] == "sciencebase_public"
    assert detail_payload["source_system"] == "sciencebase"
    assert detail_payload["source_mode"] == "public_api"
    assert detail_payload["status"] == "completed"
    assert detail_payload["downloaded_count"] == 1
    assert detail_payload["ingested_count"] == 1
    assert detail_payload["profiled_count"] == 1
    assert detail_payload["recommended_count"] == 1
    assert detail_payload["fetch_policy_summary"]["mode"] == "strict_public_safe"
    assert detail_payload["fetch_policy_summary"]["external_fetch_policy"] == "sciencebase_only"
    assert {"sciencebase.gov", "www.sciencebase.gov"}.issubset(
        set(detail_payload["fetch_policy_summary"]["allowed_hosts"])
    )

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 1
    [target] = target_rows
    assert target["status"] == "recommended"
    assert target["artifact_surface"] == "files"
    assert target["public_read_confirmed"] is True
    assert target["dataset_id"]
    assert target["dataset_version_id"]

    recommendation = client.post(
        f"/api/v1/datasets/{target['dataset_id']}/versions/{target['dataset_version_id']}/analysis/recommend",
        json={"goal_type": "exploratory"},
    )
    assert recommendation.status_code == 200, recommendation.text
    recommended_sequence = recommendation.json()["recommended_sequence"]
    assert recommended_sequence[0] == "cross_correlation"
    recommended_method = "cross_correlation"

    analysis_response = client.post(
        "/api/v1/analysis-runs",
        json={
            "dataset_version_id": target["dataset_version_id"],
            "method_name": recommended_method,
            "goal_type": "exploratory",
            "parameters": {"max_lag": 2},
            "annotation_window_id": None,
        },
    )
    assert analysis_response.status_code == 200, analysis_response.text
    analysis = analysis_response.json()
    assert analysis["dataset_version_id"] == target["dataset_version_id"]
    assert analysis["method_name"] == recommended_method
    assert analysis["status"] == "completed"
    assert analysis["assumptions"] or analysis["artifacts"] or analysis["caveats"]

    recovery_client = TestClient(app)
    recovered_run = recovery_client.get(f"/api/v1/connectors/runs/{run_id}")
    assert recovered_run.status_code == 200, recovered_run.text
    assert recovered_run.json()["status"] == "completed"
    recovered_targets = recovery_client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert recovered_targets.status_code == 200, recovered_targets.text
    assert recovered_targets.json()["targets"][0]["dataset_version_id"] == target["dataset_version_id"]
    recovered_analysis = recovery_client.get(f"/api/v1/analysis-runs/{analysis['analysis_run_id']}")
    assert recovered_analysis.status_code == 200, recovered_analysis.text
    assert recovered_analysis.json()["artifacts"] == analysis["artifacts"]

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        request_config = run.request_config_json or {}
        assert "api_key" not in request_config
        assert "authorization" not in request_config
        assert "token" not in request_config
        target_row = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        version = db.get(DatasetVersion, target_row.dataset_version_id)
        assert version is not None
        expected_summary = {
            "content_hash": expected_hash,
            "source_row_count": 4,
            "dropped_row_count": 1,
            "row_count": 3,
        }
        assert version.content_hash == expected_hash
        assert version.source_row_count == expected_summary["source_row_count"]
        assert version.dropped_row_count == expected_summary["dropped_row_count"]
        assert version.row_count == expected_summary["row_count"]
        assert target_row.source_reference_json["ingest_fidelity"] == expected_summary
    finally:
        db.close()


def test_public_connector_journey_network_unreachable_is_degraded(monkeypatch):
    from app.services import connectors_sciencebase as sb

    class _NetworkUnreachableAdapter(_FakeScienceBaseSourceFidelityAdapter):
        def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
            raise requests.ConnectionError("simulated network unreachable")

    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _NetworkUnreachableAdapter())

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": f"sciencebase-network-unreachable-degraded-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["status"] == "completed_with_errors"
    assert detail_payload["discovered_count"] == 1
    assert detail_payload["downloaded_count"] == 0
    assert detail_payload["failed_count"] == 1
    assert detail_payload["retryable_target_count"] == 1
    assert detail_payload["terminal_target_count"] == 0

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    [target] = targets.json()["targets"]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "transport_timeout"
    assert target["retry_eligible"] is True
    assert target["dataset_version_id"] is None


def test_connector_l20_lease_token_assertion_rejects_mismatch_and_expiry():
    from datetime import timedelta

    from app.services.sciencebase_connector.contracts import LeaseConflictError
    from app.services.sciencebase_connector.executor import assert_lease_token, utcnow

    with pytest.raises(LeaseConflictError):
        assert_lease_token(current_token="current-token", expected_token="other-token", expires_at=utcnow() + timedelta(seconds=60))

    with pytest.raises(LeaseConflictError):
        assert_lease_token(current_token="current-token", expected_token="current-token", expires_at=utcnow() - timedelta(seconds=1))


def test_connector_l20_terminal_resume_is_noop_for_public_connectors(monkeypatch):
    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun
    from app.services.connectors_sciencebase import _utcnow

    cases = [
        (
            "/api/v1/connectors/sciencebase-public/runs",
            {"q": "MCS", "page_size": 1},
            "l20-terminal-resume-sciencebase",
        ),
        (
            "/api/v1/connectors/senate-lda/runs",
            {"client_name": "Meta", "filing_year": 2025},
            "l20-terminal-resume-senate-lda",
        ),
    ]

    def _noop_enqueue(*args, **kwargs):
        return None

    for endpoint, payload, idempotency_key in cases:
        monkeypatch.setattr(router, "_enqueue_connector_run", _noop_enqueue)
        submit = client.post(endpoint, json=payload, headers={"Idempotency-Key": idempotency_key})
        assert submit.status_code == 202, submit.text
        run_id = submit.json()["connector_run_id"]

        db = SessionLocal()
        try:
            run = db.get(ConnectorRun, run_id)
            assert run is not None
            run.status = "completed"
            run.completed_at = _utcnow()
            run.resume_count = 0
            db.commit()
        finally:
            db.close()

        enqueue_calls = []
        monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: enqueue_calls.append(args))
        resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
        assert resume.status_code == 202, resume.text
        resume_payload = resume.json()

        db = SessionLocal()
        try:
            run = db.get(ConnectorRun, run_id)
            assert run is not None
            observed_status = run.status
            observed_resume_count = run.resume_count
            run.status = "completed"
            run.resume_count = 0
            run.completed_at = run.completed_at or _utcnow()
            db.commit()
        finally:
            db.close()
        assert resume_payload["status"] == "completed"
        assert observed_status == "completed"
        assert observed_resume_count == 0
        assert enqueue_calls == []


def test_connector_l20_expired_running_lease_resume_requeues_public_connectors(monkeypatch):
    from datetime import timedelta

    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun
    from app.services.connectors_sciencebase import _utcnow

    cases = [
        (
            "/api/v1/connectors/sciencebase-public/runs",
            {"q": "MCS", "page_size": 1},
            "l20-expired-lease-resume-sciencebase",
            "sciencebase_public",
        ),
        (
            "/api/v1/connectors/senate-lda/runs",
            {"client_name": "Meta", "filing_year": 2025},
            "l20-expired-lease-resume-senate-lda",
            "senate_lda",
        ),
    ]

    for endpoint, payload, idempotency_key, connector_key in cases:
        monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: None)
        submit = client.post(endpoint, json=payload, headers={"Idempotency-Key": idempotency_key})
        assert submit.status_code == 202, submit.text
        run_id = submit.json()["connector_run_id"]

        db = SessionLocal()
        try:
            run = db.get(ConnectorRun, run_id)
            assert run is not None
            run.status = "running"
            run.execution_lease_owner = "pid:stale"
            run.execution_lease_token = "stale-token"
            run.execution_lease_expires_at = _utcnow() - timedelta(seconds=1)
            run.resume_count = 0
            db.commit()
        finally:
            db.close()

        enqueue_calls = []
        monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: enqueue_calls.append(args))
        resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
        assert resume.status_code == 202, resume.text
        assert resume.json()["status"] == "pending"
        assert len(enqueue_calls) == 1
        assert enqueue_calls[0][1:] == (connector_key, run_id)

        db = SessionLocal()
        try:
            run = db.get(ConnectorRun, run_id)
            assert run is not None
            observed_status = run.status
            observed_resume_count = run.resume_count
            run.status = "failed"
            db.commit()
        finally:
            db.close()
        assert observed_status == "pending"
        assert observed_resume_count == 1


def test_connector_l20_sciencebase_active_lease_records_conflict(monkeypatch):
    from datetime import timedelta

    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _UnexpectedScienceBaseAdapter())

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "page_size": 1},
        headers={"Idempotency-Key": "l20-sciencebase-lease-conflict"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        run.status = "running"
        run.execution_lease_owner = f"pid:{os.getpid()}"
        run.execution_lease_token = "held-token"
        run.execution_lease_expires_at = sb._utcnow() + timedelta(seconds=300)
        db.commit()
    finally:
        db.close()

    sb.execute_connector_run(run_id)

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        observed_error_summary = run.error_summary
        observed_lease_conflicts = (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.connector_run_id == run_id, ConnectorRunEvent.event_type == "lease_conflict")
            .count()
        )
        observed_target_count = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).count()
        run.status = "failed"
        db.commit()
    finally:
        db.close()
    assert observed_error_summary == "lease_conflict"
    assert observed_lease_conflicts == 1
    assert observed_target_count == 0


def test_connector_l20_sciencebase_cancel_mid_target_stops_before_partial_authority(monkeypatch):
    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget, DatasetSourceProvenance
    from app.services import connectors_sciencebase as sb

    adapter = _FakeCancelDuringDownloadAdapter()
    monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "page_size": 1, "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": "l20-sciencebase-cancel-mid-target"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]
    adapter.run_id = run_id

    sb.execute_connector_run(run_id)

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.status == "cancelled"
        assert run.cancelled_at is not None
        assert run.error_summary == "cancelled_by_operator"
        assert run.execution_lease_owner is None
        assert run.execution_lease_token is None
        assert run.execution_lease_expires_at is not None
        targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
        assert len(targets) == 1
        assert targets[0].status == "selected"
        assert targets[0].raw_storage_ref is None
        assert targets[0].dataset_version_id is None
        assert db.query(DatasetSourceProvenance).filter(DatasetSourceProvenance.connector_run_id == run_id).count() == 0
        event_types = {
            row.event_type
            for row in db.query(ConnectorRunEvent).filter(ConnectorRunEvent.connector_run_id == run_id).all()
        }
        assert "run_cancel_requested" in event_types
        assert "run_finalized" in event_types
    finally:
        db.close()


class _FakeExplicitScopeAdapter:
    def __init__(self):
        self.search_calls = 0
        self.hydrated_ids = []

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        self.search_calls += 1
        return type(
            "SearchPage",
            (),
            {
                "items": [],
                "offset": offset,
                "page_size": page_size,
                "total": 0,
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        self.hydrated_ids.append(item_id)
        return {
            "id": item_id,
            "title": f"Explicit {item_id}",
            "identifiers": [],
            "permissions": {"read": ["public"]},
            "files": [{"name": f"{item_id}.txt", "downloadUri": f"https://www.sciencebase.gov/catalog/file/{item_id}.txt"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        file = item["files"][0]
        return [
            {
                "surface": "files",
                "name": file["name"],
                "url": file["downloadUri"],
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": {"surface": "files"},
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        raise RuntimeError("download should not be called for .txt in this test")


class _FakeDryRunAdapter:
    def __init__(self):
        self.download_calls = 0

    def search_page(self, *, q, filters, offset, page_size, sort, order):
        items = [] if offset > 0 else [{"id": "dry-run-item"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": "Dry run item",
            "identifiers": [],
            "permissions": {"read": ["public"]},
            "files": [{"name": "dry.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/dry.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        raw = item["files"][0]
        return [
            {
                "surface": "files",
                "name": raw["name"],
                "url": raw["downloadUri"],
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": raw,
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        self.download_calls += 1
        raise RuntimeError("dry_run must not call download")


class _FakeBudgetAdapter:
    def search_page(self, *, q, filters, offset, page_size, sort, order):
        if offset > 0:
            items = []
        else:
            items = [{"id": "budget-1"}, {"id": "budget-2"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id):
        return {
            "id": item_id,
            "title": f"Budget {item_id}",
            "identifiers": [],
            "permissions": {"read": ["public"]},
            "files": [{"name": f"{item_id}.csv", "downloadUri": f"https://www.sciencebase.gov/catalog/file/{item_id}.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item):
        raw = item["files"][0]
        return [
            {
                "surface": "files",
                "name": raw["name"],
                "url": raw["downloadUri"],
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": raw,
            }
        ]

    def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
        rows = ["year,value"] + [f"{2000 + i},{100 + i}" for i in range(180)]
        csv = ("\n".join(rows) + "\n").encode("utf-8")
        return type(
            "DownloadResult",
            (),
            {
                "content": csv,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": None,
                "last_modified": None,
                "content_type": "text/csv",
                "sha256": f"sha-{Path(url).name}",
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


def test_connector_scope_mode_folder_children_and_explicit_item_ids(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRun

    # Contract validation: folder scopes require exactly one scope value.
    invalid = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"scope_mode": "folder_children", "scope_values": []},
        headers={"Idempotency-Key": "scope-folder-invalid"},
    )
    assert invalid.status_code == 409, invalid.text

    adapter = _FakeExplicitScopeAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "scope_mode": "explicit_item_ids",
            "scope_values": ["alpha-item", "beta-item"],
            "run_mode": "one_shot_import",
            "allowed_extensions": [".txt"],
        },
        headers={"Idempotency-Key": "scope-explicit-items"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    # explicit_item_ids bypasses search and hydrates explicit ids directly.
    assert adapter.search_calls == 0
    assert set(adapter.hydrated_ids) == {"alpha-item", "beta-item"}

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["effective_search_envelope"]["params"]["scope_mode"] == "explicit_item_ids"
    assert payload["manifest_refs"]["selection_manifest_ref"]

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.effective_search_params_json["scope_mode"] == "explicit_item_ids"
    finally:
        db.close()


def test_sciencebase_download_429_retryable_sets_backoff(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorPolicySnapshot, ConnectorRunTarget, ConnectorTargetStageAttempt
    from app.services import connectors_sciencebase as sb

    class _RateLimitedScienceBaseAdapter(_FakeSearchOnlyAdapter):
        def search_page(self, *, q, filters, offset, page_size, sort, order):
            return type(
                "SearchPage",
                (),
                {
                    "items": [{"id": "rate-limited-item"}] if offset == 0 else [],
                    "offset": offset,
                    "page_size": page_size,
                    "total": 1,
                    "nextlink": None,
                    "prevlink": None,
                    "raw_query_metadata": {},
                },
            )()

        def hydrate_item(self, item_id):
            return {
                "id": item_id,
                "title": "Rate Limited Item",
                "files": [
                    {
                        "name": "rate-limited.csv",
                        "downloadUri": "https://www.sciencebase.gov/catalog/file/rate-limited.csv",
                    }
                ],
                "distributionLinks": [],
                "webLinks": [],
            }

        def extract_artifacts(self, item):
            return [
                {
                    "surface": "files",
                    "name": "rate-limited.csv",
                    "url": "https://www.sciencebase.gov/catalog/file/rate-limited.csv",
                    "locator_type": "downloadUri",
                    "checksum_type": None,
                    "checksum_value": None,
                    "source_reference": {"name": "rate-limited.csv"},
                }
            ]

        def download_artifact(self, *, url, timeout_seconds, max_redirects, headers=None):
            response = requests.Response()
            response.status_code = 429
            response.url = url
            response.headers["Retry-After"] = "120"
            error = requests.HTTPError("429 Too Many Requests", response=response)
            raise error

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _RateLimitedScienceBaseAdapter())

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": "sciencebase-429-retry-after"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        target = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).one()
        assert target.status == "download_failed"
        assert target.last_error_class == "http_429"
        assert target.retry_eligible is True
        assert target.backoff_until is not None
        assert target.last_attempt_at is not None
        assert target.backoff_until > target.last_attempt_at
        stage_attempt = (
            db.query(ConnectorTargetStageAttempt)
            .filter(ConnectorTargetStageAttempt.connector_run_target_id == target.connector_run_target_id)
            .order_by(ConnectorTargetStageAttempt.completed_at.desc())
            .first()
        )
        assert stage_attempt is not None
        assert stage_attempt.retryable is True
        assert stage_attempt.metrics_json["retry_after_seconds"] == 120.0
        policy = db.query(ConnectorPolicySnapshot).filter(ConnectorPolicySnapshot.connector_run_id == run_id).one()
        assert "http_429" in policy.retry_matrix_json["retryable"]
    finally:
        db.close()


@pytest.mark.parametrize(
    ("detail_error_case", "expected_error_class", "expected_retryable"),
    [
        ("timeout", "transport_timeout", True),
        ("http_403", "http_403", False),
    ],
)
def test_l17_senate_lda_detail_errors_are_terminal_or_retryable(monkeypatch, detail_error_case, expected_error_class, expected_retryable):
    from app.services import connectors_senate_lda as senate_lda

    fake = _L17SenateLdaClient(detail_error_case=detail_error_case)
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={
            "client_name": "Meta",
            "filing_year": 2025,
            "include_filing_detail": True,
            "run_mode": "metadata_only",
            "retry_max_attempts_per_request": 1,
        },
        headers={"Idempotency-Key": f"l17-senate-detail-{detail_error_case}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed_with_errors"
    assert payload["retryable_target_count"] == (2 if expected_retryable else 0)

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    rows = targets.json()["targets"]
    assert {row["status"] for row in rows} == {"download_failed"}
    assert {row["last_error_class"] for row in rows} == {expected_error_class}
    assert {row["retry_eligible"] for row in rows} == {expected_retryable}


def test_l17_senate_lda_detail_missing_required_schema_is_rejected(monkeypatch):
    from app.services import connectors_senate_lda as senate_lda

    fake = _L17SenateLdaClient(detail_error_case="missing_schema")
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={
            "client_name": "Meta",
            "filing_year": 2025,
            "include_filing_detail": True,
            "run_mode": "metadata_only",
            "retry_max_attempts_per_request": 1,
        },
        headers={"Idempotency-Key": "l17-senate-detail-missing-schema"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed_with_errors"

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    rows = targets.json()["targets"]
    assert {row["status"] for row in rows} == {"download_failed"}
    assert {row["last_error_class"] for row in rows} == {"schema_validation_failed"}
    assert {row["retry_eligible"] for row in rows} == {False}


def test_l17_senate_lda_retry_after_records_retry_telemetry(monkeypatch):
    from app.services import connectors_senate_lda as senate_lda

    payload = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "filing_uuid": "retry-after-filing",
                "url": "https://lda.senate.gov/api/v1/filings/retry-after-filing/",
                "filing_type": "LD-2",
                "filing_year": 2025,
                "filing_period": "mid_year",
                "dt_posted": "2025-07-01",
                "filing_document_url": "https://lda.senate.gov/retry-after-filing.pdf",
                "filing_document_content_type": "application/pdf",
                "registrant": {"name": "Registrant Retry"},
                "client": {"name": "Client Retry"},
            }
        ],
    }
    session = _SequenceSession(
        [
            _SequenceJsonResponse(429, {"detail": "rate limited"}, headers={"Retry-After": "2"}),
            _SequenceJsonResponse(200, payload),
        ]
    )
    real_client = senate_lda.SenateLdaClient(base_url="https://lda.senate.gov/api/v1")
    real_client.session = session
    sleeps = []
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: real_client)
    monkeypatch.setattr(senate_lda._RateLimiter, "wait", lambda self: None)
    monkeypatch.setattr(senate_lda.time, "sleep", lambda seconds: sleeps.append(seconds))

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={
            "client_name": "Meta",
            "filing_year": 2025,
            "run_mode": "metadata_only",
            "retry_max_attempts_per_request": 2,
            "retry_base_backoff_seconds": 0.1,
            "retry_max_backoff_seconds": 5,
        },
        headers={"Idempotency-Key": "l17-senate-retry-after"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    assert len(session.calls) == 2
    assert sleeps == [2.0]
    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    summary_ref = detail.json()["report_refs"]["senate_lda_summary"]
    summary = json.loads(Path(summary_ref).read_text(encoding="utf-8"))
    assert summary["retry_summary"]["requests_total"] == 2
    assert summary["retry_summary"]["retries_total"] == 1
    assert summary["retry_summary"]["retry_sleep_seconds"] == 2.0


def test_l17_senate_lda_additive_schema_and_policy_snapshot_are_bounded(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorPolicySnapshot
    from app.services import connectors_senate_lda as senate_lda

    payload = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "filing_uuid": "additive-filing",
                "url": "https://lda.senate.gov/api/v1/filings/additive-filing/",
                "filing_type": "LD-2",
                "filing_year": 2025,
                "filing_period": "mid_year",
                "dt_posted": "2025-07-01",
                "filing_document_url": "https://lda.senate.gov/additive-filing.pdf",
                "filing_document_content_type": "application/pdf",
                "registrant": {"name": "Registrant Additive"},
                "client": {"name": "Client Additive"},
                "new_optional_field": {"schema_drift": "tolerated"},
            }
        ],
    }
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: _L17SenateLdaClient(list_payload=payload))

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025, "run_mode": "metadata_only"},
        headers={"Idempotency-Key": "l17-senate-additive-schema"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed"

    db = SessionLocal()
    try:
        policy = db.query(ConnectorPolicySnapshot).filter(ConnectorPolicySnapshot.connector_run_id == run_id).one()
        assert policy.policy_json["fetch_policy_summary"]["allowed_hosts"] == ["lda.senate.gov"]
        assert 429 in policy.retry_matrix_json["retryable_http_statuses"]
    finally:
        db.close()


def test_l17_senate_lda_missing_required_schema_is_rejected_explicitly(monkeypatch):
    from app.services import connectors_senate_lda as senate_lda

    payload = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "url": "https://lda.senate.gov/api/v1/filings/missing-uuid/",
                "filing_type": "LD-2",
                "filing_year": 2025,
                "filing_period": "mid_year",
                "dt_posted": "2025-07-01",
            }
        ],
    }
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: _L17SenateLdaClient(list_payload=payload))

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025, "run_mode": "metadata_only"},
        headers={"Idempotency-Key": "l17-senate-missing-schema"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "failed"
    assert payload["search_exhaustion_reason"] == "schema_validation_failed"
    assert "missing_required_field:filing_uuid" in payload["error_summary"]


def test_l17_senate_lda_partial_page_is_degraded_not_complete(monkeypatch):
    from app.services import connectors_senate_lda as senate_lda

    payload = {
        "count": 2,
        "next": "https://lda.senate.gov/api/v1/filings/?page=2",
        "previous": None,
        "results": [],
    }
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: _L17SenateLdaClient(list_payload=payload))

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025, "run_mode": "metadata_only"},
        headers={"Idempotency-Key": "l17-senate-partial-page"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed_with_errors"
    assert payload["next_page_available"] is True
    assert payload["search_exhaustion_reason"] == "partial_page_empty_with_next"
    assert payload["error_summary"] == "partial_page_empty_with_next"


@pytest.mark.parametrize(
    ("download_case", "expected_status", "expected_error_class", "expected_retryable"),
    [
        ("timeout", "download_failed", "transport_timeout", True),
        ("http_403", "download_failed", "http_4xx", False),
        ("redirect_private", "blocked_by_fetch_policy", "host_policy_violation", False),
    ],
)
def test_l17_sciencebase_download_negatives_are_bounded_and_observable(
    monkeypatch,
    download_case,
    expected_status,
    expected_error_class,
    expected_retryable,
):
    from app.db.session import SessionLocal
    from app.models import ConnectorPolicySnapshot, ConnectorRunTarget, ConnectorTargetStageAttempt
    from app.services import connectors_sciencebase as sb

    adapter = _L17ScienceBaseAdapter(download_case=download_case)
    if download_case == "redirect_private":
        resolved_ips = iter(["8.8.8.8", "127.0.0.1"])
        monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: next(resolved_ips))
    else:
        monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": f"l17-sciencebase-{download_case}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["status"] == "completed_with_errors"
    assert detail_payload["retryable_target_count"] == (1 if expected_retryable else 0)
    assert detail_payload["fetch_policy_summary"]["external_fetch_policy"] == "sciencebase_only"
    assert {"sciencebase.gov", "www.sciencebase.gov"}.issubset(detail_payload["fetch_policy_summary"]["allowed_hosts"])

    db = SessionLocal()
    try:
        target = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).one()
        assert target.status == expected_status
        assert target.last_error_class == expected_error_class
        assert target.retry_eligible is expected_retryable

        stage_attempt = (
            db.query(ConnectorTargetStageAttempt)
            .filter(ConnectorTargetStageAttempt.connector_run_target_id == target.connector_run_target_id)
            .order_by(ConnectorTargetStageAttempt.completed_at.desc())
            .first()
        )
        assert stage_attempt is not None
        assert stage_attempt.error_class == expected_error_class
        assert stage_attempt.retryable is expected_retryable
        assert "duration_ms" in stage_attempt.metrics_json

        policy = db.query(ConnectorPolicySnapshot).filter(ConnectorPolicySnapshot.connector_run_id == run_id).one()
        assert "transport_timeout" in policy.retry_matrix_json["retryable"]
        assert "http_4xx" in policy.retry_matrix_json["terminal"]
        assert "host_policy_violation" in policy.retry_matrix_json["terminal"]
    finally:
        db.close()


def test_l17_sciencebase_additive_schema_is_tolerated(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(
        sb,
        "get_sciencebase_adapter",
        lambda config: _L17ScienceBaseAdapter(download_case="success", namespace="additive-schema"),
    )

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": "l17-sciencebase-additive-schema"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed"

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    assert {row["status"] for row in targets.json()["targets"]} == {"recommended"}


def test_l17_sciencebase_malformed_schema_is_rejected_explicitly(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _L17ScienceBaseAdapter(malformed_item=True))

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": "l17-sciencebase-malformed-schema"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "failed"
    assert "missing_required_field:item_id" in payload["error_summary"]


def test_l17_sciencebase_partial_page_is_degraded_not_complete(monkeypatch):
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _L17ScienceBaseAdapter(empty_page_next=True))

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": "l17-sciencebase-partial-page"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed_with_errors"
    assert payload["next_page_available"] is True
    assert payload["search_exhaustion_reason"] == "partial_page_empty_with_next"
    assert payload["error_summary"] == "partial_page_empty_with_next"


def test_l17_finalize_ignores_stale_error_summary_after_current_success(monkeypatch):
    from app.db.session import SessionLocal
    from app.services import connectors_sciencebase as sb

    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(
        sb,
        "get_sciencebase_adapter",
        lambda config: _L17ScienceBaseAdapter(download_case="success", namespace="finalize-success"),
    )

    submit = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={"q": "MCS", "run_mode": "one_shot_import", "allowed_extensions": [".csv"]},
        headers={"Idempotency-Key": "l17-stale-error-finalize"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        run = db.get(sb.ConnectorRun, run_id)
        assert run is not None
        run.error_summary = "stale_prior_error"
        db.commit()

        sb._finalize_run(db, run)
        db.refresh(run)
        assert run.status == "completed"
        assert run.error_summary == "stale_prior_error"
    finally:
        db.close()


def test_connector_scope_mode_folder_children_applies_parent_filter(monkeypatch):
    from app.services import connectors_sciencebase as sb

    adapter = _FakePartitionAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "scope_mode": "folder_children",
            "scope_values": ["folder-xyz"],
            "allowed_extensions": [".txt"],
        },
        headers={"Idempotency-Key": "scope-folder-children"},
    )
    assert response.status_code == 202, response.text
    assert adapter.search_calls
    assert any("parentId=folder-xyz" in call["filters"] for call in adapter.search_calls)

    run_id = response.json()["connector_run_id"]
    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["effective_search_envelope"]["params"]["scope_mode"] == "folder_children"


def test_connector_mcs_release_mode_requires_commodity_keywords():
    invalid = client.post(
        "/api/v1/connectors/sciencebase-mcs/runs",
        json={"mcs_release_mode": "commodity_sheet_release", "commodity_keywords": []},
        headers={"Idempotency-Key": "mcs-commodity-invalid"},
    )
    assert invalid.status_code == 409, invalid.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/connectors/sciencebase-public/runs",
        "/api/v1/connectors/sciencebase-mcs/runs",
    ],
)
@pytest.mark.parametrize(
    ("payload", "headers"),
    [
        ({"connector_egress_arming": {"schema_id": "reserved"}}, {}),
        ({"source_mode": " strict_live_egress "}, {}),
        ({"client_request_id": "egress-arm:client"}, {}),
        ({"submission_idempotency_key": "egress-arm:submission"}, {}),
        ({"idempotency_key": "egress-arm:payload"}, {}),
        ({}, {"Idempotency-Key": "egress-arm:header"}),
    ],
)
def test_sciencebase_generic_api_rejects_all_reserved_egress_markers(
    monkeypatch,
    path,
    payload,
    headers,
):
    from app.api import router as api_router
    from app.models import ConnectorRun

    monkeypatch.setattr(
        api_router,
        "_enqueue_connector_run",
        lambda *_args, **_kwargs: pytest.fail(
            "reserved ScienceBase request must not enqueue"
        ),
    )
    with TestingSessionLocal() as db:
        before = db.query(ConnectorRun).count()

    response = client.post(path, json=payload, headers=headers)

    assert response.status_code in {409, 422}, response.text
    with TestingSessionLocal() as db:
        assert db.query(ConnectorRun).count() == before


def test_sciencebase_mcs_explicit_2026_item_ids_skip_search_and_dry_run(monkeypatch):
    from app.services import connectors_sciencebase as sb

    adapter = _FakeMcs2026ScienceBaseAdapter()
    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-mcs/runs",
        json={
            "q": "Mineral Commodity Summaries",
            "years": [2026],
            "scope_mode": "explicit_item_ids",
            "scope_values": [MCS_2026_COMMODITIES_ITEM_ID, MCS_2026_TRENDS_ITEM_ID],
            "run_mode": "dry_run",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
        },
        headers={"Idempotency-Key": f"sciencebase-mcs-2026-dry-run-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    assert adapter.search_calls == []
    assert adapter.hydrate_calls == [MCS_2026_COMMODITIES_ITEM_ID, MCS_2026_TRENDS_ITEM_ID]
    assert adapter.download_calls == []

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["connector_key"] == "sciencebase_mcs"
    assert detail_payload["run_mode"] == "dry_run"
    assert detail_payload["fetch_policy_summary"]["external_fetch_policy"] == "sciencebase_only"
    assert detail_payload["effective_search_envelope"]["params"]["scope_mode"] == "explicit_item_ids"
    assert detail_payload["effective_search_envelope"]["params"]["scope_values"] == [
        MCS_2026_COMMODITIES_ITEM_ID,
        MCS_2026_TRENDS_ITEM_ID,
    ]
    assert detail_payload["effective_search_envelope"]["filters"] == ["systemType=Data Release"]

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 2
    assert {target["sciencebase_item_id"] for target in target_rows} == {
        MCS_2026_COMMODITIES_ITEM_ID,
        MCS_2026_TRENDS_ITEM_ID,
    }
    assert {target["status"] for target in target_rows} == {"dry_run_skipped"}
    assert {target["artifact_surface"] for target in target_rows} == {"files"}
    assert {target["selection_scope"] for target in target_rows} == {"explicit_item"}
    assert {target["selection_match_basis"] for target in target_rows} == {"content_type"}


def test_sciencebase_mcs_2026_commodity_csv_ingests_offline(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_sciencebase as sb
    from app.services.dataframe_io import load_version_dataframe

    adapter = _FakeMcs2026ScienceBaseAdapter()
    expected_hash = hashlib.sha256(adapter.commodity_csv_bytes).hexdigest()
    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-mcs/runs",
        json={
            "years": [2026],
            "scope_mode": "explicit_item_ids",
            "scope_values": [MCS_2026_COMMODITIES_ITEM_ID],
            "run_mode": "one_shot_import",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
            "detect_seasonality": False,
            "detect_stationarity": False,
        },
        headers={"Idempotency-Key": f"sciencebase-mcs-2026-ingest-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["connector_key"] == "sciencebase_mcs"
    assert detail_payload["status"] == "completed"
    assert detail_payload["downloaded_count"] == 1
    assert detail_payload["ingested_count"] == 1
    assert detail_payload["profiled_count"] == 1
    assert adapter.search_calls == []
    assert adapter.download_calls == [MCS_2026_COMMODITIES_DOWNLOAD_URI]

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.sciencebase_item_id == MCS_2026_COMMODITIES_ITEM_ID
        assert target.sciencebase_file_name == "MCS2026_Commodities_Data.csv"
        assert target.sciencebase_download_uri == MCS_2026_COMMODITIES_DOWNLOAD_URI
        assert target.dataset_version_id
        assert target.source_artifact_key

        version = db.get(DatasetVersion, target.dataset_version_id)
        assert version is not None
        assert version.content_hash == expected_hash
        assert version.source_row_count == 5
        assert version.dropped_row_count == 0
        assert version.row_count == 5

        frame = load_version_dataframe(db, target.dataset_version_id)
        assert frame["commodity"].tolist() == ["Aluminum"] * 5
        assert frame["net_import_reliance"].astype(int).tolist() == [44, 45, 46, 47, 48]

        provenance = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .one()
        )
        assert provenance.sciencebase_item_id == MCS_2026_COMMODITIES_ITEM_ID
        assert provenance.sciencebase_file_name == "MCS2026_Commodities_Data.csv"
        assert provenance.downloaded_sha256 == expected_hash
    finally:
        db.close()


def test_sciencebase_mcs_default_policy_blocks_data_usgs_artifact_urls(monkeypatch):
    from app.services import connectors_sciencebase as sb

    adapter = _FakeMcs2026ScienceBaseAdapter(
        external_download_url="https://data.usgs.gov/datacatalog/file/MCS2026_Commodities_Data.csv"
    )
    monkeypatch.setattr(sb, "_resolve_host_ip", lambda _hostname: "8.8.8.8")
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-mcs/runs",
        json={
            "years": [2026],
            "scope_mode": "explicit_item_ids",
            "scope_values": [MCS_2026_COMMODITIES_ITEM_ID],
            "run_mode": "one_shot_import",
            "allowed_extensions": [".csv"],
            "surface_policy": "files_only",
            "external_fetch_policy": "sciencebase_only",
        },
        headers={"Idempotency-Key": f"sciencebase-mcs-2026-host-block-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    [target] = targets.json()["targets"]
    assert target["sciencebase_item_id"] == MCS_2026_COMMODITIES_ITEM_ID
    assert target["status"] == "blocked_by_fetch_policy"
    assert target["blocked_reason"] == "host_not_allowed"
    assert adapter.download_calls == []


def test_sciencebase_mcs_support_matrix_evidence_pins_current_data_release():
    matrix = json.loads((ROOT / "config" / "support_matrix.yaml").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    sciencebase = by_id["sciencebase_public_connector_slice"]

    assert len(matrix["capabilities"]) == 32
    assert sciencebase["status"] == "supported"
    assert "ScienceBase public/MCS" in matrix["boundary_note"]
    assert "sciencebase_mcs_2026_data_release_slice" not in by_id
    for test_name in [
        "test_sciencebase_mcs_explicit_2026_item_ids_skip_search_and_dry_run",
        "test_sciencebase_mcs_2026_commodity_csv_ingests_offline",
        "test_sciencebase_mcs_default_policy_blocks_data_usgs_artifact_urls",
    ]:
        assert f"tests/test_api.py::{test_name}" in sciencebase["evidence"]
    assert "tests/test_api.py::test_sciencebase_mcs_support_matrix_evidence_pins_current_data_release" not in sciencebase["evidence"]


def test_connector_dry_run_never_downloads(monkeypatch):
    from app.services import connectors_sciencebase as sb

    adapter = _FakeDryRunAdapter()
    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: adapter)

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "dry_run",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "dry-run-contract"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    statuses = {item["status"] for item in targets.json()["targets"]}
    assert statuses == {"dry_run_skipped"}
    assert adapter.download_calls == 0


def test_connector_budget_blocked_and_partition_cursor_persisted(monkeypatch):
    from app.services import connectors_sciencebase as sb
    from app.db.session import SessionLocal
    from app.models import ConnectorRunPartitionCursor

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeBudgetAdapter())
    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "max_file_bytes": 2048,
            "max_run_bytes": 2500,
            "allowed_extensions": [".csv"],
            "partition_strategy": "configured_slices",
            "configured_slices": [{"label": "slice-a", "q": "MCS", "filters": ["systemType=Data Release"]}],
        },
        headers={"Idempotency-Key": "budget-and-cursor-run"},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["budget_blocked_count"] >= 1
    assert payload["budget_summary"]["budget_exhausted"] is True
    assert payload["effective_search_envelope"]["params"]["page_size"] >= 5

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    assert any(item["status"] == "budget_blocked" for item in targets.json()["targets"])

    db = SessionLocal()
    try:
        cursor_count = (
            db.query(ConnectorRunPartitionCursor)
            .filter(ConnectorRunPartitionCursor.connector_run_id == run_id)
            .count()
        )
        assert cursor_count >= 1
    finally:
        db.close()


class _FakeRequest:
    def __init__(self, url):
        self.url = url


class _FakeJsonResponse:
    def __init__(self, *, url, status_code, payload, headers=None):
        self.request = _FakeRequest(url)
        self.url = url
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = headers or {"content-type": "application/json"}
        self.history = []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}", response=self)


class _FakeNrcClient:
    def __init__(self, *, fixture_name: str = "born_digital.pdf", content_type: str = "application/pdf"):
        self.search_payloads = []
        self.document_ids = []
        self.download_urls = []
        self.fixture_name = fixture_name
        self.content_type = content_type

    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "ML900000001",
                            "DocumentTitle": "Inspection Report",
                            "DocumentType": "Letter",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                            "Url": "https://adams.nrc.gov/wba/test1.pdf",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number):
        self.document_ids.append(accession_number)
        body = {
            "document": {
                "AccessionNumber": accession_number,
                "DocumentTitle": "Inspection Report (Detailed)",
                "DocumentType": "Letter",
                "DocumentDate": "2025-02-01",
                "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                "Url": "https://adams.nrc.gov/wba/test1.pdf",
                "content": "document body text",
            }
        }
        return _FakeJsonResponse(url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}", status_code=200, payload=body)

    def download_artifact(self, url, *, max_redirects, max_file_bytes=None):
        from app.services.connectors_nrc_adams import ApsDownloadResult
        import hashlib

        self.download_urls.append(url)
        content = _read_nrc_fixture_bytes(self.fixture_name)
        return ApsDownloadResult(
            content=content,
            status_code=200,
            final_url=url,
            redirect_count=0,
            etag="etag-1",
            last_modified="Mon, 01 Jan 2025 00:00:00 GMT",
            content_type=self.content_type,
            sha256=hashlib.sha256(content).hexdigest(),
            headers={"content-type": self.content_type},
            auth_required=True,
        )


class _FakeNrcCsvClient(_FakeNrcClient):
    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "MLCSV000001",
                            "DocumentTitle": "CSV Table",
                            "DocumentType": "Data",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                            "Url": "https://adams.nrc.gov/wba/table.csv",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number):
        self.document_ids.append(accession_number)
        body = {
            "document": {
                "AccessionNumber": accession_number,
                "DocumentTitle": "CSV Table (Detailed)",
                "DocumentType": "Data",
                "DocumentDate": "2025-02-01",
                "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                "Url": "https://adams.nrc.gov/wba/table.csv",
                "content": "date,value,label",
            }
        }
        return _FakeJsonResponse(url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}", status_code=200, payload=body)

    def download_artifact(self, url, *, max_redirects, max_file_bytes=None):
        from app.services.connectors_nrc_adams import ApsDownloadResult
        import hashlib

        self.download_urls.append(url)
        content = b"date,value,label\n2026-01-01,42,alpha\n2026-01-02,43,beta\n"
        return ApsDownloadResult(
            content=content,
            status_code=200,
            final_url=url,
            redirect_count=0,
            etag="etag-csv-1",
            last_modified="Mon, 01 Jan 2025 00:00:00 GMT",
            content_type="text/csv",
            sha256=hashlib.sha256(content).hexdigest(),
            headers={"content-type": "text/csv"},
            auth_required=True,
        )


class _FakeNrcXlsxClient(_FakeNrcClient):
    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "MLXLSX000001",
                            "DocumentTitle": "XLSX Table",
                            "DocumentType": "Data",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                            "Url": "https://adams.nrc.gov/wba/table.xlsx",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number):
        self.document_ids.append(accession_number)
        body = {
            "document": {
                "AccessionNumber": accession_number,
                "DocumentTitle": "XLSX Table (Detailed)",
                "DocumentType": "Data",
                "DocumentDate": "2025-02-01",
                "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                "Url": "https://adams.nrc.gov/wba/table.xlsx",
                "content": "",
            }
        }
        return _FakeJsonResponse(url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}", status_code=200, payload=body)

    def download_artifact(self, url, *, max_redirects, max_file_bytes=None):
        from app.services.connectors_nrc_adams import ApsDownloadResult
        from support_nrc_aps_xlsx import build_xlsx_bytes
        import hashlib

        self.download_urls.append(url)
        content = build_xlsx_bytes(
            {
                "Observations": [
                    ["date", "value", "label"],
                    ["2026-01-01", 42, "alpha"],
                    ["2026-01-02", 43, "beta"],
                ],
            }
        )
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return ApsDownloadResult(
            content=content,
            status_code=200,
            final_url=url,
            redirect_count=0,
            etag="etag-xlsx-1",
            last_modified="Mon, 01 Jan 2025 00:00:00 GMT",
            content_type=content_type,
            sha256=hashlib.sha256(content).hexdigest(),
            headers={"content-type": content_type},
            auth_required=True,
        )


class _FakeNrcJsonClient(_FakeNrcClient):
    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "MLJSON000001",
                            "DocumentTitle": "JSON Recordset",
                            "DocumentType": "Data",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                            "Url": "https://adams.nrc.gov/wba/table.json",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number):
        self.document_ids.append(accession_number)
        body = {
            "document": {
                "AccessionNumber": accession_number,
                "DocumentTitle": "JSON Recordset (Detailed)",
                "DocumentType": "Data",
                "DocumentDate": "2025-02-01",
                "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                "Url": "https://adams.nrc.gov/wba/table.json",
                "content": "",
            }
        }
        return _FakeJsonResponse(url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}", status_code=200, payload=body)

    def download_artifact(self, url, *, max_redirects, max_file_bytes=None):
        from app.services.connectors_nrc_adams import ApsDownloadResult
        import hashlib

        self.download_urls.append(url)
        content = json.dumps(
            [
                {"date": "2026-01-01", "value": 42, "label": "alpha"},
                {"date": "2026-01-02", "value": 43, "label": "beta"},
            ]
        ).encode("utf-8")
        return ApsDownloadResult(
            content=content,
            status_code=200,
            final_url=url,
            redirect_count=0,
            etag="etag-json-1",
            last_modified="Mon, 01 Jan 2025 00:00:00 GMT",
            content_type="application/json",
            sha256=hashlib.sha256(content).hexdigest(),
            headers={"content-type": "application/json"},
            auth_required=True,
        )


class _FakeNrcSecEdgarClient(_FakeNrcClient):
    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "MLSECEDGAR001",
                            "DocumentTitle": "SEC EDGAR Filing",
                            "DocumentType": "Filing",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                            "Url": "https://adams.nrc.gov/wba/sec-edgar.txt",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number):
        self.document_ids.append(accession_number)
        body = {
            "document": {
                "AccessionNumber": accession_number,
                "DocumentTitle": "SEC EDGAR Filing (Detailed)",
                "DocumentType": "Filing",
                "DocumentDate": "2025-02-01",
                "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                "Url": "https://adams.nrc.gov/wba/sec-edgar.txt",
                "content": "",
            }
        }
        return _FakeJsonResponse(url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}", status_code=200, payload=body)

    def download_artifact(self, url, *, max_redirects, max_file_bytes=None):
        from app.services.connectors_nrc_adams import ApsDownloadResult
        import hashlib

        self.download_urls.append(url)
        content = b"""<SEC-DOCUMENT>0000320193-24-000123.txt : 20241101
<SEC-HEADER>
<ACCESSION-NUMBER>0000320193-24-000123
<CONFORMED-SUBMISSION-TYPE>10-K
<FILED-AS-OF-DATE>20241101
<COMPANY-CONFORMED-NAME>EXAMPLE INDUSTRIES INC
<CENTRAL-INDEX-KEY>0000320193
</SEC-HEADER>
<DOCUMENT>
<TYPE>10-K
<SEQUENCE>1
<FILENAME>example-20241101.txt
<DESCRIPTION>Primary filing document
<TEXT>
ITEM 1. Business
Registrant manufactures industrial widgets.
<TABLE>
date|revenue|segment
2026-01-01|42|alpha
2026-01-02|43|beta
</TABLE>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""
        return ApsDownloadResult(
            content=content,
            status_code=200,
            final_url=url,
            redirect_count=0,
            etag="etag-sec-edgar-1",
            last_modified="Mon, 01 Jan 2025 00:00:00 GMT",
            content_type="text/plain",
            sha256=hashlib.sha256(content).hexdigest(),
            headers={"content-type": "text/plain"},
            auth_required=True,
        )


class _FakeNrcNoUrlClient(_FakeNrcClient):
    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "ML900000009",
                            "DocumentTitle": "No URL Record",
                            "DocumentType": "Letter",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number):
        self.document_ids.append(accession_number)
        body = {
            "document": {
                "AccessionNumber": accession_number,
                "DocumentTitle": "No URL Record (Detailed)",
                "DocumentType": "Letter",
                "DocumentDate": "2025-02-01",
                "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                "content": "document body text",
            }
        }
        return _FakeJsonResponse(url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}", status_code=200, payload=body)


class _FakeNrcMapperProbeClient:
    def __init__(self):
        self.search_payloads = []

    def search(self, payload):
        self.search_payloads.append(payload)
        return _FakeJsonResponse(
            url="https://adams-api.nrc.gov/aps/api/search",
            status_code=200,
            payload={"count": 0, "results": []},
        )

    def get_document(self, accession_number):
        raise RuntimeError("should not call get_document when no hits")

    def download_artifact(self, url, *, max_redirects, max_file_bytes=None):
        raise RuntimeError("should not call download when no hits")


class _FakeNrcWireFallbackClient(_FakeNrcClient):
    def search(self, payload):
        self.search_payloads.append(payload)
        skip = int(payload.get("skip", 0))
        if "q" in payload and "filters" in payload and "searchCriteria" not in payload:
            return _FakeJsonResponse(
                url="https://adams-api.nrc.gov/aps/api/search",
                status_code=500,
                payload={},
            )
        if skip > 0:
            body = {"count": 0, "results": []}
        else:
            body = {
                "count": 1,
                "results": [
                    {
                        "score": 0.9,
                        "document": {
                            "AccessionNumber": "ML900000001",
                            "DocumentTitle": "Inspection Report",
                            "DocumentType": "Letter",
                            "DocumentDate": "2025-02-01",
                            "DateAddedTimestamp": "2025-02-02T00:00:00Z",
                            "Url": "https://adams.nrc.gov/wba/test1.pdf",
                        },
                    }
                ],
            }
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)


def test_nrc_adams_metadata_indexing_route(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "page_size": 10,
            "max_items": 5,
            "run_mode": "metadata_only",
            "download_artifacts": True,
        },
        headers={"Idempotency-Key": "nrc-index-route"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    assert payload["connector_key"] == "nrc_adams_aps"
    assert payload["recommended_count"] >= 1
    assert payload["manifest_refs"]["selection_manifest_ref"]
    safeguard_ref = payload["report_refs"]["aps_safeguard"]
    assert safeguard_ref
    safeguard_payload = json.loads(Path(safeguard_ref).read_text(encoding="utf-8"))
    assert safeguard_payload["schema_id"] == "aps.safeguard_report.v1"
    assert int(safeguard_payload["schema_version"]) == 1
    assert fake.document_ids == ["ML900000001"]
    assert fake.download_urls == ["https://adams.nrc.gov/wba/test1.pdf"]
    assert fake.search_payloads
    assert "q" in fake.search_payloads[0]

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 1
    assert target_rows[0]["sciencebase_item_id"] == "ML900000001"
    assert target_rows[0]["status"] == "recommended"


def test_nrc_hydrate_process_emits_normalization_contract(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "page_size": 10,
            "max_items": 5,
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "artifact_required_for_target_success": True,
        },
        headers={"Idempotency-Key": "nrc-hydrate-process"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    assert payload["report_refs"]["aps_artifact_ingestion"]
    assert payload["report_refs"]["aps_artifact_ingestion_failure"] is None

    run_artifact = json.loads(Path(payload["report_refs"]["aps_artifact_ingestion"]).read_text(encoding="utf-8"))
    assert run_artifact["schema_id"] == "aps.artifact_ingestion_run.v1"
    assert int(run_artifact["schema_version"]) == 1
    assert run_artifact["pipeline_mode"] == "hydrate_process"
    assert int(run_artifact["selected_targets"]) >= 1
    assert int(run_artifact["processed_targets"]) >= 1
    assert run_artifact["target_artifacts"]

    target_ref = run_artifact["target_artifacts"][0]["ref"]
    target_artifact = json.loads(Path(target_ref).read_text(encoding="utf-8"))
    assert target_artifact["schema_id"] == "aps.artifact_ingestion_target.v1"
    assert target_artifact["outcome_status"] == "processed"
    assert target_artifact["normalization_contract_id"] == "aps_text_normalization_v2"
    extraction = target_artifact["extraction"]
    assert extraction["effective_content_type"] == "application/pdf"
    assert extraction["media_detection_contract_id"] == "aps_media_detection_v1"
    assert extraction["document_processing_contract_id"] == "aps_document_extraction_v1"
    assert extraction["diagnostics_ref"]
    assert extraction["quality_status"] in {"limited", "strong"}


def test_nrc_hydrate_process_supports_candidate_b_document_processing_engine(monkeypatch):
    from app.models import ConnectorRun
    from app.services import connectors_nrc_adams as nrc
    from app.services import nrc_aps_document_processing

    fake = _FakeNrcClient(fixture_name="layout.pdf")
    install_fake_opendataloader_pdf(monkeypatch, nrc_aps_document_processing)
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report candidate b",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "page_size": 10,
            "max_items": 5,
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "artifact_required_for_target_success": True,
            "document_processing_engine": "candidate_b_opendataloader_pdf",
        },
        headers={"Idempotency-Key": "nrc-hydrate-process-candidate-b"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = TestingSessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert (run.request_config_json or {}).get("document_processing_engine") == "candidate_b_opendataloader_pdf"
    finally:
        db.close()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    assert payload["report_refs"]["aps_artifact_ingestion"]

    run_artifact = json.loads(Path(payload["report_refs"]["aps_artifact_ingestion"]).read_text(encoding="utf-8"))
    target_ref = run_artifact["target_artifacts"][0]["ref"]
    target_artifact = json.loads(Path(target_ref).read_text(encoding="utf-8"))
    extraction = target_artifact["extraction"]

    assert extraction["effective_content_type"] == "application/pdf"
    assert extraction["extractor_family"] == "pdf_candidate_b_opendataloader"
    assert extraction["extractor_id"] == "aps_odl_pdf_extractor"
    assert extraction["extractor_version"] == "2.0.0"
    assert extraction["visual_page_refs"] == []


def test_nrc_download_only_missing_url_emits_artifact_not_available(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcNoUrlClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "download_only",
            "artifact_required_for_target_success": False,
        },
        headers={"Idempotency-Key": "nrc-download-only-no-url"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed"
    run_artifact = json.loads(Path(payload["report_refs"]["aps_artifact_ingestion"]).read_text(encoding="utf-8"))
    assert run_artifact["run_outcome"] == "targets_processed"
    assert int(run_artifact["failure_code_counts"].get("artifact_url_missing", 0)) == 0
    assert int(run_artifact["outcome_counts"].get("artifact_not_available", 0)) >= 1

    target_ref = run_artifact["target_artifacts"][0]["ref"]
    target_artifact = json.loads(Path(target_ref).read_text(encoding="utf-8"))
    assert target_artifact["outcome_status"] == "artifact_not_available"
    assert target_artifact.get("failure") is None


def test_nrc_hydrate_process_missing_url_required_for_success_fails_target(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcNoUrlClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "artifact_required_for_target_success": True,
        },
        headers={"Idempotency-Key": "nrc-hydrate-no-url-required"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed_with_errors"

    run_artifact = json.loads(Path(payload["report_refs"]["aps_artifact_ingestion"]).read_text(encoding="utf-8"))
    assert int(run_artifact["failure_code_counts"].get("artifact_url_missing", 0)) >= 1

    target_ref = run_artifact["target_artifacts"][0]["ref"]
    target_artifact = json.loads(Path(target_ref).read_text(encoding="utf-8"))
    assert target_artifact["outcome_status"] == "failed"
    assert target_artifact["failure"]["code"] == "artifact_url_missing"

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    assert targets.json()["targets"][0]["status"] == "download_failed"


def test_nrc_zero_selected_targets_emits_no_targets_selected_run_outcome(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcMapperProbeClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "empty query set",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "download_only",
        },
        headers={"Idempotency-Key": "nrc-zero-selected"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed"
    assert int(payload["selected_count"]) == 0

    run_artifact = json.loads(Path(payload["report_refs"]["aps_artifact_ingestion"]).read_text(encoding="utf-8"))
    assert run_artifact["run_outcome"] == "no_targets_selected"
    assert int(run_artifact["selected_targets"]) == 0
    assert int(run_artifact["processed_targets"]) == 0
    assert run_artifact["target_artifacts"] == []


def test_nrc_content_index_artifacts_and_search_route(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "download_only",
            "content_chunk_size_chars": 32,
            "content_chunk_overlap_chars": 8,
            "content_chunk_min_chars": 5,
        },
        headers={"Idempotency-Key": "nrc-content-index-search"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["report_refs"]["aps_content_index"]
    assert payload["report_refs"]["aps_content_index_failure"] is None

    run_artifact = json.loads(Path(payload["report_refs"]["aps_content_index"]).read_text(encoding="utf-8"))
    assert run_artifact["schema_id"] == "aps.content_index_run.v1"
    assert int(run_artifact["schema_version"]) == 1
    assert int(run_artifact["processed_targets"]) >= 1
    assert int(run_artifact["indexing_failures_count"]) == 0
    assert run_artifact["content_units_artifacts"]

    content_ref = run_artifact["content_units_artifacts"][0]["ref"]
    content_artifact = json.loads(Path(content_ref).read_text(encoding="utf-8"))
    assert content_artifact["schema_id"] == "aps.content_units.v2"
    assert content_artifact["content_contract_id"] == "aps_content_units_v2"
    assert content_artifact["chunking_contract_id"] == "aps_chunking_v2"
    assert int(content_artifact["chunk_count"]) >= 1
    assert content_artifact["effective_content_type"] == "application/pdf"
    assert "diagnostics_ref" in content_artifact

    listed = client.get(f"/api/v1/connectors/runs/{run_id}/content-units")
    assert listed.status_code == 200, listed.text
    listed_payload = listed.json()
    assert listed_payload["connector_run_id"] == run_id
    assert listed_payload["total"] >= 1
    first_row = listed_payload["items"][0]
    assert first_row["content_contract_id"] == "aps_content_units_v2"
    assert first_row["chunking_contract_id"] == "aps_chunking_v2"
    assert first_row["run_id"] == run_id
    assert first_row["target_id"]
    assert first_row["effective_content_type"] == "application/pdf"
    assert first_row["quality_status"] in {"limited", "strong"}
    assert first_row["page_start"] == 1

    searched = client.post(
        "/api/v1/connectors/nrc-adams-aps/content-search",
        json={"query": "reactor coolant", "run_id": run_id, "limit": 10, "offset": 0},
    )
    assert searched.status_code == 200, searched.text
    searched_payload = searched.json()
    assert sorted(searched_payload["query_tokens"]) == ["coolant", "reactor"]
    assert searched_payload["total"] >= 1
    assert searched_payload["items"][0]["matched_unique_query_terms"] == 2
    assert searched_payload["items"][0]["summed_term_frequency"] >= 2
    assert searched_payload["items"][0]["effective_content_type"] == "application/pdf"


def test_nrc_csv_dataset_bridge_materializes_dataset_from_runtime_run(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget, DatasetVersion
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcCsvClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "csv table",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "csv_dataset_bridge_enabled": True,
        },
        headers={"Idempotency-Key": "nrc-csv-dataset-bridge-runtime"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    bridge_ref = payload["report_refs"]["aps_csv_dataset_bridge"]
    assert bridge_ref

    bridge_report = json.loads(Path(bridge_ref).read_text(encoding="utf-8"))
    assert bridge_report["schema_id"] == "aps.csv_dataset_bridge_run.v1"
    assert bridge_report["enabled"] is True
    assert bridge_report["run_outcome"] == "datasets_materialized"
    assert bridge_report["materialized_dataset_versions"] == 1
    assert bridge_report["failures_count"] == 0

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.dataset_id
        assert target.dataset_version_id
        assert target.source_reference_json["aps_csv_dataset_bridge_ref"] == bridge_ref
        assert target.source_reference_json["aps_csv_dataset_bridge_contract_id"] == "aps_csv_dataset_bridge_v1"
        version = db.get(DatasetVersion, target.dataset_version_id)
        assert version is not None
        assert version.row_count == 2
    finally:
        db.close()


def test_nrc_table_dataset_bridge_materializes_xlsx_dataset_from_runtime_run(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcXlsxClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "xlsx table",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "table_dataset_bridge_enabled": True,
        },
        headers={"Idempotency-Key": "nrc-table-dataset-bridge-xlsx-runtime"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    bridge_ref = payload["report_refs"]["aps_table_dataset_bridge"]
    assert bridge_ref
    assert "aps_csv_dataset_bridge" not in payload["report_refs"]

    bridge_report = json.loads(Path(bridge_ref).read_text(encoding="utf-8"))
    assert bridge_report["schema_id"] == "aps.table_dataset_bridge_run.v1"
    assert bridge_report["enabled"] is True
    assert bridge_report["run_outcome"] == "datasets_materialized"
    assert bridge_report["dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
    assert bridge_report["materialized_dataset_versions"] == 1
    assert bridge_report["materialized"][0]["parser_family"] == "xlsx_workbook"
    assert bridge_report["failures_count"] == 0

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.dataset_id
        assert target.dataset_version_id
        assert target.source_reference_json["aps_table_dataset_bridge_ref"] == bridge_ref
        assert target.source_reference_json["aps_table_dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
        assert target.source_reference_json["aps_table_dataset_parser_family"] == "xlsx_workbook"
        assert "aps_csv_dataset_bridge_ref" not in target.source_reference_json
        version = db.get(DatasetVersion, target.dataset_version_id)
        assert version is not None
        assert version.row_count == 2
        provenance = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id)
            .one()
        )
        assert provenance.connector_run_id == run_id
        assert provenance.source_mode == "artifact_xlsx_parser"
    finally:
        db.close()


def test_nrc_table_dataset_bridge_materializes_json_dataset_from_runtime_run(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcJsonClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "json table",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "table_dataset_bridge_enabled": True,
        },
        headers={"Idempotency-Key": "nrc-table-dataset-bridge-json-runtime"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    bridge_ref = payload["report_refs"]["aps_table_dataset_bridge"]
    assert bridge_ref

    bridge_report = json.loads(Path(bridge_ref).read_text(encoding="utf-8"))
    assert bridge_report["schema_id"] == "aps.table_dataset_bridge_run.v1"
    assert bridge_report["enabled"] is True
    assert bridge_report["run_outcome"] == "datasets_materialized"
    assert bridge_report["materialized_dataset_versions"] == 1
    assert bridge_report["materialized"][0]["parser_family"] == "json_recordset"
    assert bridge_report["failures_count"] == 0

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.dataset_id
        assert target.dataset_version_id
        assert target.source_reference_json["aps_table_dataset_bridge_ref"] == bridge_ref
        assert target.source_reference_json["aps_table_dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
        assert target.source_reference_json["aps_table_dataset_parser_family"] == "json_recordset"
        version = db.get(DatasetVersion, target.dataset_version_id)
        assert version is not None
        assert version.row_count == 2
        provenance = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id)
            .one()
        )
        assert provenance.connector_run_id == run_id
        assert provenance.source_mode == "artifact_json_recordset_parser"
    finally:
        db.close()


def test_nrc_table_dataset_bridge_materializes_sec_edgar_dataset_from_runtime_run(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcSecEdgarClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "sec edgar filing",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "hydrate_process",
            "table_dataset_bridge_enabled": True,
            "sec_edgar_admitted_form_types": "10-K,10-Q,8-K",
        },
        headers={"Idempotency-Key": "nrc-table-dataset-bridge-sec-edgar-runtime"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    bridge_ref = payload["report_refs"]["aps_table_dataset_bridge"]
    assert bridge_ref

    bridge_report = json.loads(Path(bridge_ref).read_text(encoding="utf-8"))
    assert bridge_report["schema_id"] == "aps.table_dataset_bridge_run.v1"
    assert bridge_report["enabled"] is True
    assert bridge_report["run_outcome"] == "datasets_materialized"
    assert bridge_report["materialized_dataset_versions"] == 1
    assert bridge_report["materialized"][0]["parser_family"] == "sec_edgar_filing"
    assert bridge_report["failures_count"] == 0

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.dataset_id
        assert target.dataset_version_id
        assert target.source_reference_json["aps_table_dataset_bridge_ref"] == bridge_ref
        assert target.source_reference_json["aps_table_dataset_bridge_contract_id"] == "aps_table_dataset_bridge_v1"
        assert target.source_reference_json["aps_table_dataset_parser_family"] == "sec_edgar_filing"
        version = db.get(DatasetVersion, target.dataset_version_id)
        assert version is not None
        assert version.row_count == 2
        provenance = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == target.dataset_version_id)
            .one()
        )
        assert provenance.connector_run_id == run_id
        assert provenance.source_mode == "artifact_sec_edgar_filing_parser"
    finally:
        db.close()


def test_nrc_real_born_digital_content_search_and_evidence_bundle(monkeypatch):
    from app.services import connectors_nrc_adams as nrc
    from app.services import nrc_aps_evidence_bundle_contract as contract

    fixture = _nrc_manifest_entry("ml17123a319")
    (TEST_STORAGE_DIR / "connectors" / "reports").mkdir(parents=True, exist_ok=True)
    fake = _FakeNrcClient(fixture_name=str(fixture["path"]))
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "public comments",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "download_only",
            "content_chunk_size_chars": 600,
            "content_chunk_overlap_chars": 80,
            "content_chunk_min_chars": 120,
        },
        headers={"Idempotency-Key": "nrc-real-born-digital-bundle"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    search_query = str(fixture["downstream_usefulness_anchor"])
    searched = client.post(
        "/api/v1/connectors/nrc-adams-aps/content-search",
        json={"query": search_query, "run_id": run_id, "limit": 10, "offset": 0},
    )
    assert searched.status_code == 200, searched.text
    searched_payload = searched.json()
    assert searched_payload["total"] >= 1
    assert search_query.split()[0] in searched_payload["items"][0]["chunk_text"].lower()

    assembled = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": search_query, "persist_bundle": True, "limit": 10, "offset": 0},
    )
    assert assembled.status_code == 200, assembled.text
    assembled_payload = assembled.json()
    assert assembled_payload["schema_id"] == contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID
    assert assembled_payload["persisted"] is True
    assert assembled_payload["total_hits"] >= 1
    assert assembled_payload["items"]
    assert search_query.split()[0] in assembled_payload["items"][0]["snippet_text"].lower()
    assert Path(str(assembled_payload["bundle_ref"])).exists()


def test_nrc_scanned_content_search_and_evidence_bundle_with_ocr(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    from app.services import nrc_aps_ocr

    if not nrc_aps_ocr.tesseract_available():
        pytest.skip("tesseract unavailable")

    fixture = _nrc_manifest_entry("scanned")
    (TEST_STORAGE_DIR / "connectors" / "reports").mkdir(parents=True, exist_ok=True)
    fake = _FakeNrcClient(fixture_name=str(fixture["path"]))
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "turbine inspection",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "download_only",
        },
        headers={"Idempotency-Key": "nrc-scanned-bundle-ocr"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    search_query = str(fixture["downstream_usefulness_anchor"])
    searched = client.post(
        "/api/v1/connectors/nrc-adams-aps/content-search",
        json={"query": search_query, "run_id": run_id, "limit": 10, "offset": 0},
    )
    assert searched.status_code == 200, searched.text
    searched_payload = searched.json()
    assert searched_payload["total"] >= 1

    assembled = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": search_query, "persist_bundle": True, "limit": 10, "offset": 0},
    )
    assert assembled.status_code == 200, assembled.text
    assembled_payload = assembled.json()
    assert assembled_payload["persisted"] is True
    assert assembled_payload["items"]
    assert search_query.split()[0] in assembled_payload["items"][0]["snippet_text"].lower()


def test_nrc_evidence_bundle_routes_return_persisted_snapshot_page():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract

    refs_dir = TEST_STORAGE_DIR / "connectors" / "reports" / "evidence_api_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    content_units_ref = refs_dir / "content_units.json"
    normalized_text_ref = refs_dir / "normalized.txt"
    blob_ref = refs_dir / "blob.bin"
    download_exchange_ref = refs_dir / "download_exchange.json"
    discovery_ref = refs_dir / "discovery.json"
    selection_ref = refs_dir / "selection.json"
    for path, value in (
        (content_units_ref, "{}"),
        (normalized_text_ref, "alpha beta alpha gamma"),
        (blob_ref, "blob"),
        (download_exchange_ref, "{}"),
        (discovery_ref, "{}"),
        (selection_ref, "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    db = TestingSessionLocal()
    try:
        run_id = "run-evidence-api-1"
        db.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system="nrc_adams_aps",
                source_mode="public_api",
                status="completed",
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-evidence-api-1",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=0,
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-evidence-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-api-sha",
                normalized_char_count=22,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-evidence-api-1",
                chunk_id="chunk-evidence-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=10,
                chunk_text="alpha beta",
                chunk_text_sha256="chunk-api-sha-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-evidence-api-1",
                chunk_id="chunk-evidence-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=11,
                end_char=22,
                chunk_text="alpha gamma",
                chunk_text_sha256="chunk-api-sha-2",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-evidence-api-1",
                run_id=run_id,
                target_id="target-evidence-api-1",
                accession_number="ML-EVIDENCE-API",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(content_units_ref),
                normalized_text_ref=str(normalized_text_ref),
                normalized_text_sha256="norm-api-sha",
                blob_ref=str(blob_ref),
                blob_sha256="blob-api-sha",
                download_exchange_ref=str(download_exchange_ref),
                discovery_ref=str(discovery_ref),
                selection_ref=str(selection_ref),
            )
        )
        db.commit()
    finally:
        db.close()

    assembled = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True, "limit": 1, "offset": 0},
    )
    assert assembled.status_code == 200, assembled.text
    assembled_payload = assembled.json()
    assert assembled_payload["schema_id"] == contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID
    assert assembled_payload["persisted"] is True
    assert assembled_payload["mode"] == "query"
    assert assembled_payload["total_hits"] == 2
    assert assembled_payload["total_groups"] == 1
    assert assembled_payload["items"][0]["group_id"]
    assert assembled_payload["items"][0]["content_units_ref"] == str(content_units_ref)
    assert assembled_payload["items"][0]["normalized_text_ref"] == str(normalized_text_ref)
    assert assembled_payload["items"][0]["blob_ref"] == str(blob_ref)
    assert assembled_payload["items"][0]["download_exchange_ref"] == str(download_exchange_ref)
    assert assembled_payload["items"][0]["discovery_ref"] == str(discovery_ref)
    assert assembled_payload["items"][0]["selection_ref"] == str(selection_ref)
    assert assembled_payload["items"][0]["highlight_spans"]
    assert Path(assembled_payload["bundle_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_evidence_bundles"] == [assembled_payload["bundle_ref"]]
    assert detail_payload["report_refs"]["aps_evidence_bundle_failures"] == []

    persisted = client.get(
        f"/api/v1/connectors/nrc-adams-aps/evidence-bundles/{assembled_payload['bundle_id']}",
        params={"limit": 1, "offset": 1},
    )
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["bundle_id"] == assembled_payload["bundle_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["limit"] == 1
    assert persisted_payload["offset"] == 1
    assert len(persisted_payload["items"]) == 1
    assert persisted_payload["items"][0]["chunk_id"] == "chunk-evidence-api-2"
    assert persisted_payload["groups"][0]["chunk_count"] == 1


def test_nrc_evidence_citation_pack_routes_return_persisted_page():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract
    from app.services import nrc_aps_evidence_citation_pack_contract as citation_contract

    refs_dir = TEST_STORAGE_DIR / "connectors" / "reports" / "citation_api_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    content_units_ref = refs_dir / "content_units.json"
    normalized_text_ref = refs_dir / "normalized.txt"
    blob_ref = refs_dir / "blob.bin"
    download_exchange_ref = refs_dir / "download_exchange.json"
    discovery_ref = refs_dir / "discovery.json"
    selection_ref = refs_dir / "selection.json"
    for path, value in (
        (content_units_ref, "{}"),
        (normalized_text_ref, "alpha beta alpha gamma"),
        (blob_ref, "blob"),
        (download_exchange_ref, "{}"),
        (discovery_ref, "{}"),
        (selection_ref, "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    db = TestingSessionLocal()
    try:
        run_id = "run-citation-api-1"
        db.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system="nrc_adams_aps",
                source_mode="public_api",
                status="completed",
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-citation-api-1",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=0,
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-citation-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-citation-api-sha",
                normalized_char_count=22,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-citation-api-1",
                chunk_id="chunk-citation-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=10,
                chunk_text="alpha beta",
                chunk_text_sha256="chunk-citation-api-sha-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-citation-api-1",
                chunk_id="chunk-citation-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=11,
                end_char=22,
                chunk_text="alpha gamma",
                chunk_text_sha256="chunk-citation-api-sha-2",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-citation-api-1",
                run_id=run_id,
                target_id="target-citation-api-1",
                accession_number="ML-CITATION-API",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(content_units_ref),
                normalized_text_ref=str(normalized_text_ref),
                normalized_text_sha256="norm-citation-api-sha",
                blob_ref=str(blob_ref),
                blob_sha256="blob-citation-api-sha",
                download_exchange_ref=str(download_exchange_ref),
                discovery_ref=str(discovery_ref),
                selection_ref=str(selection_ref),
            )
        )
        db.commit()
    finally:
        db.close()

    bundle = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    assert bundle.status_code == 200, bundle.text
    bundle_payload = bundle.json()
    assert bundle_payload["schema_id"] == contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID

    packed = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_payload["bundle_id"], "persist_pack": True, "limit": 1, "offset": 0},
    )
    assert packed.status_code == 200, packed.text
    packed_payload = packed.json()
    assert packed_payload["schema_id"] == citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID
    assert packed_payload["persisted"] is True
    assert packed_payload["source_bundle"]["bundle_id"] == bundle_payload["bundle_id"]
    assert packed_payload["total_citations"] == 2
    assert packed_payload["citations"][0]["citation_label"] == "APS-CIT-00001"
    assert Path(packed_payload["citation_pack_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_evidence_citation_packs"] == [packed_payload["citation_pack_ref"]]
    assert detail_payload["report_refs"]["aps_evidence_citation_pack_failures"] == []

    persisted = client.get(
        f"/api/v1/connectors/nrc-adams-aps/citation-packs/{packed_payload['citation_pack_id']}",
        params={"limit": 1, "offset": 1},
    )
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["citation_pack_id"] == packed_payload["citation_pack_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["limit"] == 1
    assert persisted_payload["offset"] == 1
    assert len(persisted_payload["citations"]) == 1
    assert persisted_payload["citations"][0]["citation_label"] == "APS-CIT-00002"
    assert persisted_payload["citations"][0]["chunk_id"] == "chunk-citation-api-2"


def test_nrc_evidence_report_routes_return_persisted_section_page():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract
    from app.services import nrc_aps_evidence_citation_pack_contract as citation_contract
    from app.services import nrc_aps_evidence_report_contract as report_contract

    refs_dir_a = TEST_STORAGE_DIR / "connectors" / "reports" / "report_api_refs_a"
    refs_dir_b = TEST_STORAGE_DIR / "connectors" / "reports" / "report_api_refs_b"
    refs_dir_a.mkdir(parents=True, exist_ok=True)
    refs_dir_b.mkdir(parents=True, exist_ok=True)
    paths = {
        "a": {
            "content_units_ref": refs_dir_a / "content_units.json",
            "normalized_text_ref": refs_dir_a / "normalized.txt",
            "blob_ref": refs_dir_a / "blob.bin",
            "download_exchange_ref": refs_dir_a / "download_exchange.json",
            "discovery_ref": refs_dir_a / "discovery.json",
            "selection_ref": refs_dir_a / "selection.json",
        },
        "b": {
            "content_units_ref": refs_dir_b / "content_units.json",
            "normalized_text_ref": refs_dir_b / "normalized.txt",
            "blob_ref": refs_dir_b / "blob.bin",
            "download_exchange_ref": refs_dir_b / "download_exchange.json",
            "discovery_ref": refs_dir_b / "discovery.json",
            "selection_ref": refs_dir_b / "selection.json",
        },
    }
    for path, value in (
        (paths["a"]["content_units_ref"], "{}"),
        (paths["a"]["normalized_text_ref"], "alpha alpha beta alpha gamma"),
        (paths["a"]["blob_ref"], "blob"),
        (paths["a"]["download_exchange_ref"], "{}"),
        (paths["a"]["discovery_ref"], "{}"),
        (paths["a"]["selection_ref"], "{}"),
        (paths["b"]["content_units_ref"], "{}"),
        (paths["b"]["normalized_text_ref"], "alpha delta"),
        (paths["b"]["blob_ref"], "blob"),
        (paths["b"]["download_exchange_ref"], "{}"),
        (paths["b"]["discovery_ref"], "{}"),
        (paths["b"]["selection_ref"], "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    db = TestingSessionLocal()
    try:
        run_id = "run-report-api-1"
        db.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system="nrc_adams_aps",
                source_mode="public_api",
                status="completed",
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-report-api-1",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=0,
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-report-api-2",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=1,
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-report-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-report-api-sha-1",
                normalized_char_count=28,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-api-1",
                chunk_id="chunk-report-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=16,
                chunk_text="alpha alpha beta",
                chunk_text_sha256="chunk-report-api-sha-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-api-1",
                chunk_id="chunk-report-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=17,
                end_char=28,
                chunk_text="alpha gamma",
                chunk_text_sha256="chunk-report-api-sha-2",
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-report-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-report-api-sha-2",
                normalized_char_count=11,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-api-2",
                chunk_id="chunk-report-api-3",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=11,
                chunk_text="alpha delta",
                chunk_text_sha256="chunk-report-api-sha-3",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-report-api-1",
                run_id=run_id,
                target_id="target-report-api-1",
                accession_number="ML-REPORT-API",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["a"]["content_units_ref"]),
                normalized_text_ref=str(paths["a"]["normalized_text_ref"]),
                normalized_text_sha256="norm-report-api-sha-1",
                blob_ref=str(paths["a"]["blob_ref"]),
                blob_sha256="blob-report-api-sha-1",
                download_exchange_ref=str(paths["a"]["download_exchange_ref"]),
                discovery_ref=str(paths["a"]["discovery_ref"]),
                selection_ref=str(paths["a"]["selection_ref"]),
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-report-api-2",
                run_id=run_id,
                target_id="target-report-api-2",
                accession_number=None,
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["b"]["content_units_ref"]),
                normalized_text_ref=str(paths["b"]["normalized_text_ref"]),
                normalized_text_sha256="norm-report-api-sha-2",
                blob_ref=str(paths["b"]["blob_ref"]),
                blob_sha256="blob-report-api-sha-2",
                download_exchange_ref=str(paths["b"]["download_exchange_ref"]),
                discovery_ref=str(paths["b"]["discovery_ref"]),
                selection_ref=str(paths["b"]["selection_ref"]),
            )
        )
        db.commit()
    finally:
        db.close()

    bundle = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    assert bundle.status_code == 200, bundle.text
    bundle_payload = bundle.json()

    packed = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_payload["bundle_id"], "persist_pack": True},
    )
    assert packed.status_code == 200, packed.text
    packed_payload = packed.json()
    assert packed_payload["schema_id"] == citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID

    reported = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_payload["citation_pack_id"], "persist_report": True, "limit": 1, "offset": 0},
    )
    assert reported.status_code == 200, reported.text
    report_payload = reported.json()
    assert report_payload["schema_id"] == report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID
    assert report_payload["persisted"] is True
    assert report_payload["source_citation_pack"]["citation_pack_id"] == packed_payload["citation_pack_id"]
    assert report_payload["total_sections"] == 2
    assert report_payload["total_citations"] == 3
    assert len(report_payload["sections"]) == 1
    assert report_payload["sections"][0]["section_ordinal"] == 1
    assert report_payload["sections"][0]["title"] == "Accession ML-REPORT-API / Content content-report-api-1"
    assert Path(report_payload["evidence_report_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_evidence_reports"] == [report_payload["evidence_report_ref"]]
    assert detail_payload["report_refs"]["aps_evidence_report_failures"] == []

    persisted = client.get(
        f"/api/v1/connectors/nrc-adams-aps/evidence-reports/{report_payload['evidence_report_id']}",
        params={"limit": 1, "offset": 1},
    )
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["evidence_report_id"] == report_payload["evidence_report_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["limit"] == 1
    assert persisted_payload["offset"] == 1
    assert len(persisted_payload["sections"]) == 1
    assert persisted_payload["sections"][0]["section_ordinal"] == 2
    assert persisted_payload["sections"][0]["title"] == "Content content-report-api-2"


def test_nrc_evidence_report_export_routes_return_persisted_snapshot():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract

    refs_dir_a = TEST_STORAGE_DIR / "connectors" / "reports" / "report_export_api_refs_a"
    refs_dir_b = TEST_STORAGE_DIR / "connectors" / "reports" / "report_export_api_refs_b"
    refs_dir_a.mkdir(parents=True, exist_ok=True)
    refs_dir_b.mkdir(parents=True, exist_ok=True)
    paths = {
        "a": {
            "content_units_ref": refs_dir_a / "content_units.json",
            "normalized_text_ref": refs_dir_a / "normalized.txt",
            "blob_ref": refs_dir_a / "blob.bin",
            "download_exchange_ref": refs_dir_a / "download_exchange.json",
            "discovery_ref": refs_dir_a / "discovery.json",
            "selection_ref": refs_dir_a / "selection.json",
        },
        "b": {
            "content_units_ref": refs_dir_b / "content_units.json",
            "normalized_text_ref": refs_dir_b / "normalized.txt",
            "blob_ref": refs_dir_b / "blob.bin",
            "download_exchange_ref": refs_dir_b / "download_exchange.json",
            "discovery_ref": refs_dir_b / "discovery.json",
            "selection_ref": refs_dir_b / "selection.json",
        },
    }
    for path, value in (
        (paths["a"]["content_units_ref"], "{}"),
        (paths["a"]["normalized_text_ref"], "alpha alpha beta alpha gamma"),
        (paths["a"]["blob_ref"], "blob"),
        (paths["a"]["download_exchange_ref"], "{}"),
        (paths["a"]["discovery_ref"], "{}"),
        (paths["a"]["selection_ref"], "{}"),
        (paths["b"]["content_units_ref"], "{}"),
        (paths["b"]["normalized_text_ref"], "alpha delta"),
        (paths["b"]["blob_ref"], "blob"),
        (paths["b"]["download_exchange_ref"], "{}"),
        (paths["b"]["discovery_ref"], "{}"),
        (paths["b"]["selection_ref"], "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    db = TestingSessionLocal()
    try:
        run_id = "run-report-export-api-1"
        db.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system="nrc_adams_aps",
                source_mode="public_api",
                status="completed",
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-report-export-api-1",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=0,
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-report-export-api-2",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=1,
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-report-export-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-report-export-api-sha-1",
                normalized_char_count=28,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-export-api-1",
                chunk_id="chunk-report-export-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=16,
                chunk_text="alpha alpha beta",
                chunk_text_sha256="chunk-report-export-api-sha-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-export-api-1",
                chunk_id="chunk-report-export-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=17,
                end_char=28,
                chunk_text="alpha gamma",
                chunk_text_sha256="chunk-report-export-api-sha-2",
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-report-export-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-report-export-api-sha-2",
                normalized_char_count=11,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-export-api-2",
                chunk_id="chunk-report-export-api-3",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=11,
                chunk_text="alpha delta",
                chunk_text_sha256="chunk-report-export-api-sha-3",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-report-export-api-1",
                run_id=run_id,
                target_id="target-report-export-api-1",
                accession_number="ML-REPORT-EXPORT-API",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["a"]["content_units_ref"]),
                normalized_text_ref=str(paths["a"]["normalized_text_ref"]),
                normalized_text_sha256="norm-report-export-api-sha-1",
                blob_ref=str(paths["a"]["blob_ref"]),
                blob_sha256="blob-report-export-api-sha-1",
                download_exchange_ref=str(paths["a"]["download_exchange_ref"]),
                discovery_ref=str(paths["a"]["discovery_ref"]),
                selection_ref=str(paths["a"]["selection_ref"]),
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-report-export-api-2",
                run_id=run_id,
                target_id="target-report-export-api-2",
                accession_number=None,
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["b"]["content_units_ref"]),
                normalized_text_ref=str(paths["b"]["normalized_text_ref"]),
                normalized_text_sha256="norm-report-export-api-sha-2",
                blob_ref=str(paths["b"]["blob_ref"]),
                blob_sha256="blob-report-export-api-sha-2",
                download_exchange_ref=str(paths["b"]["download_exchange_ref"]),
                discovery_ref=str(paths["b"]["discovery_ref"]),
                selection_ref=str(paths["b"]["selection_ref"]),
            )
        )
        db.commit()
    finally:
        db.close()

    bundle = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    assert bundle.status_code == 200, bundle.text
    bundle_payload = bundle.json()

    packed = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_payload["bundle_id"], "persist_pack": True},
    )
    assert packed.status_code == 200, packed.text
    packed_payload = packed.json()

    reported = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_payload["citation_pack_id"], "persist_report": True},
    )
    assert reported.status_code == 200, reported.text
    report_payload = reported.json()

    exported = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_payload["evidence_report_id"], "persist_export": True},
    )
    assert exported.status_code == 200, exported.text
    export_payload = exported.json()
    assert export_payload["schema_id"] == "aps.evidence_report_export.v1"
    assert export_payload["persisted"] is True
    assert export_payload["format_id"] == "markdown"
    assert export_payload["source_evidence_report"]["evidence_report_id"] == report_payload["evidence_report_id"]
    assert export_payload["rendered_markdown"].startswith("# NRC ADAMS APS Evidence Report Export\n")
    assert "## Section 00001:" in export_payload["rendered_markdown"]
    assert Path(export_payload["evidence_report_export_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_evidence_report_exports"] == [export_payload["evidence_report_export_ref"]]
    assert detail_payload["report_refs"]["aps_evidence_report_export_failures"] == []

    persisted = client.get(
        f"/api/v1/connectors/nrc-adams-aps/evidence-report-exports/{export_payload['evidence_report_export_id']}",
    )
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["evidence_report_export_id"] == export_payload["evidence_report_export_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["rendered_markdown"] == export_payload["rendered_markdown"]


def test_nrc_evidence_report_export_package_routes_return_persisted_snapshot():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract

    refs_dir_a = TEST_STORAGE_DIR / "report_export_package_api_refs_a"
    refs_dir_b = TEST_STORAGE_DIR / "report_export_package_api_refs_b"
    refs_dir_a.mkdir(parents=True, exist_ok=True)
    refs_dir_b.mkdir(parents=True, exist_ok=True)
    paths = {
        "a": {
            "content_units_ref": refs_dir_a / "content_units.json",
            "normalized_text_ref": refs_dir_a / "normalized.txt",
            "blob_ref": refs_dir_a / "blob.bin",
            "download_exchange_ref": refs_dir_a / "download_exchange.json",
            "discovery_ref": refs_dir_a / "discovery.json",
            "selection_ref": refs_dir_a / "selection.json",
        },
        "b": {
            "content_units_ref": refs_dir_b / "content_units.json",
            "normalized_text_ref": refs_dir_b / "normalized.txt",
            "blob_ref": refs_dir_b / "blob.bin",
            "download_exchange_ref": refs_dir_b / "download_exchange.json",
            "discovery_ref": refs_dir_b / "discovery.json",
            "selection_ref": refs_dir_b / "selection.json",
        },
    }
    for path, value in (
        (paths["a"]["content_units_ref"], "{}"),
        (paths["a"]["normalized_text_ref"], "alpha alpha beta alpha gamma"),
        (paths["a"]["blob_ref"], "blob"),
        (paths["a"]["download_exchange_ref"], "{}"),
        (paths["a"]["discovery_ref"], "{}"),
        (paths["a"]["selection_ref"], "{}"),
        (paths["b"]["content_units_ref"], "{}"),
        (paths["b"]["normalized_text_ref"], "alpha delta"),
        (paths["b"]["blob_ref"], "blob"),
        (paths["b"]["download_exchange_ref"], "{}"),
        (paths["b"]["discovery_ref"], "{}"),
        (paths["b"]["selection_ref"], "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    run_id = "run-report-export-package-api-1"
    db = TestingSessionLocal()
    try:
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            source_system="nrc_adams_aps",
            source_mode="public_api",
            status="completed",
        )
        target_a = ConnectorRunTarget(
            connector_run_target_id="target-report-export-package-api-1",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=0,
        )
        target_b = ConnectorRunTarget(
            connector_run_target_id="target-report-export-package-api-2",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=1,
        )
        db.add(run)
        db.add(target_a)
        db.add(target_b)
        db.add(
            ApsContentDocument(
                content_id="content-report-export-package-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-report-export-package-api-1",
                normalized_char_count=28,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-export-package-api-1",
                chunk_id="chunk-report-export-package-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=16,
                chunk_text="alpha alpha beta",
                chunk_text_sha256="sha-report-export-package-api-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-export-package-api-1",
                chunk_id="chunk-report-export-package-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=17,
                end_char=28,
                chunk_text="alpha gamma",
                chunk_text_sha256="sha-report-export-package-api-2",
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-report-export-package-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-report-export-package-api-2",
                normalized_char_count=11,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-report-export-package-api-2",
                chunk_id="chunk-report-export-package-api-3",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=11,
                chunk_text="alpha delta",
                chunk_text_sha256="sha-report-export-package-api-3",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-report-export-package-api-1",
                run_id=run_id,
                target_id="target-report-export-package-api-1",
                accession_number="ML-REPORT-EXPORT-PACKAGE-API-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["a"]["content_units_ref"]),
                normalized_text_ref=str(paths["a"]["normalized_text_ref"]),
                normalized_text_sha256="norm-report-export-package-api-1",
                blob_ref=str(paths["a"]["blob_ref"]),
                blob_sha256="blob-report-export-package-api-1",
                download_exchange_ref=str(paths["a"]["download_exchange_ref"]),
                discovery_ref=str(paths["a"]["discovery_ref"]),
                selection_ref=str(paths["a"]["selection_ref"]),
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-report-export-package-api-2",
                run_id=run_id,
                target_id="target-report-export-package-api-2",
                accession_number=None,
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["b"]["content_units_ref"]),
                normalized_text_ref=str(paths["b"]["normalized_text_ref"]),
                normalized_text_sha256="norm-report-export-package-api-2",
                blob_ref=str(paths["b"]["blob_ref"]),
                blob_sha256="blob-report-export-package-api-2",
                download_exchange_ref=str(paths["b"]["download_exchange_ref"]),
                discovery_ref=str(paths["b"]["discovery_ref"]),
                selection_ref=str(paths["b"]["selection_ref"]),
            )
        )
        db.commit()
    finally:
        db.close()

    bundle_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    assert bundle_a.status_code == 200, bundle_a.text
    bundle_a_payload = bundle_a.json()

    packed_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_a_payload["bundle_id"], "persist_pack": True},
    )
    assert packed_a.status_code == 200, packed_a.text
    packed_a_payload = packed_a.json()

    report_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_a_payload["citation_pack_id"], "persist_report": True},
    )
    assert report_a.status_code == 200, report_a.text
    report_a_payload = report_a.json()

    export_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_a_payload["evidence_report_id"], "persist_export": True},
    )
    assert export_a.status_code == 200, export_a.text
    export_a_payload = export_a.json()

    bundle_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "delta", "persist_bundle": True},
    )
    assert bundle_b.status_code == 200, bundle_b.text
    bundle_b_payload = bundle_b.json()

    packed_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_b_payload["bundle_id"], "persist_pack": True},
    )
    assert packed_b.status_code == 200, packed_b.text
    packed_b_payload = packed_b.json()

    report_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_b_payload["citation_pack_id"], "persist_report": True},
    )
    assert report_b.status_code == 200, report_b.text
    report_b_payload = report_b.json()

    export_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_b_payload["evidence_report_id"], "persist_export": True},
    )
    assert export_b.status_code == 200, export_b.text
    export_b_payload = export_b.json()

    packaged = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-export-packages",
        json={
            "evidence_report_export_ids": [
                export_a_payload["evidence_report_export_id"],
                export_b_payload["evidence_report_export_id"],
            ],
            "persist_package": True,
        },
    )
    assert packaged.status_code == 200, packaged.text
    package_payload = packaged.json()
    assert package_payload["schema_id"] == "aps.evidence_report_export_package.v1"
    assert package_payload["persisted"] is True
    assert package_payload["owner_run_id"] == run_id
    assert package_payload["source_export_count"] == 2
    assert package_payload["source_exports"][0]["evidence_report_export_id"] == export_a_payload["evidence_report_export_id"]
    assert Path(package_payload["evidence_report_export_package_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_evidence_report_export_packages"] == [
        package_payload["evidence_report_export_package_ref"]
    ]
    assert detail_payload["report_refs"]["aps_evidence_report_export_package_failures"] == []

    persisted = client.get(
        f"/api/v1/connectors/nrc-adams-aps/evidence-report-export-packages/{package_payload['evidence_report_export_package_id']}",
    )
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["evidence_report_export_package_id"] == package_payload["evidence_report_export_package_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["ordered_source_exports_sha256"] == package_payload["ordered_source_exports_sha256"]


def test_nrc_context_packet_routes_return_persisted_snapshot():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract

    refs_dir_a = TEST_STORAGE_DIR / "connectors" / "reports" / "context_packet_api_refs_a"
    refs_dir_b = TEST_STORAGE_DIR / "connectors" / "reports" / "context_packet_api_refs_b"
    refs_dir_a.mkdir(parents=True, exist_ok=True)
    refs_dir_b.mkdir(parents=True, exist_ok=True)
    paths = {
        "a": {
            "content_units_ref": refs_dir_a / "content_units.json",
            "normalized_text_ref": refs_dir_a / "normalized.txt",
            "blob_ref": refs_dir_a / "blob.bin",
            "download_exchange_ref": refs_dir_a / "download_exchange.json",
            "discovery_ref": refs_dir_a / "discovery.json",
            "selection_ref": refs_dir_a / "selection.json",
        },
        "b": {
            "content_units_ref": refs_dir_b / "content_units.json",
            "normalized_text_ref": refs_dir_b / "normalized.txt",
            "blob_ref": refs_dir_b / "blob.bin",
            "download_exchange_ref": refs_dir_b / "download_exchange.json",
            "discovery_ref": refs_dir_b / "discovery.json",
            "selection_ref": refs_dir_b / "selection.json",
        },
    }
    for path, value in (
        (paths["a"]["content_units_ref"], "{}"),
        (paths["a"]["normalized_text_ref"], "alpha alpha beta alpha gamma"),
        (paths["a"]["blob_ref"], "blob"),
        (paths["a"]["download_exchange_ref"], "{}"),
        (paths["a"]["discovery_ref"], "{}"),
        (paths["a"]["selection_ref"], "{}"),
        (paths["b"]["content_units_ref"], "{}"),
        (paths["b"]["normalized_text_ref"], "alpha delta"),
        (paths["b"]["blob_ref"], "blob"),
        (paths["b"]["download_exchange_ref"], "{}"),
        (paths["b"]["discovery_ref"], "{}"),
        (paths["b"]["selection_ref"], "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    run_id = "run-context-packet-api-1"
    db = TestingSessionLocal()
    try:
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            source_system="nrc_adams_aps",
            source_mode="public_api",
            status="completed",
        )
        target_a = ConnectorRunTarget(
            connector_run_target_id="target-context-packet-api-1",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=0,
        )
        target_b = ConnectorRunTarget(
            connector_run_target_id="target-context-packet-api-2",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=1,
        )
        db.add(run)
        db.add(target_a)
        db.add(target_b)
        db.add(
            ApsContentDocument(
                content_id="content-context-packet-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-context-packet-api-1",
                normalized_char_count=28,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-context-packet-api-1",
                chunk_id="chunk-context-packet-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=16,
                chunk_text="alpha alpha beta",
                chunk_text_sha256="sha-context-packet-api-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-context-packet-api-1",
                chunk_id="chunk-context-packet-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=17,
                end_char=28,
                chunk_text="alpha gamma",
                chunk_text_sha256="sha-context-packet-api-2",
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-context-packet-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-context-packet-api-2",
                normalized_char_count=11,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-context-packet-api-2",
                chunk_id="chunk-context-packet-api-3",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=11,
                chunk_text="alpha delta",
                chunk_text_sha256="sha-context-packet-api-3",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-context-packet-api-1",
                run_id=run_id,
                target_id="target-context-packet-api-1",
                accession_number="ML-CONTEXT-PACKET-API-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["a"]["content_units_ref"]),
                normalized_text_ref=str(paths["a"]["normalized_text_ref"]),
                normalized_text_sha256="norm-context-packet-api-1",
                blob_ref=str(paths["a"]["blob_ref"]),
                blob_sha256="blob-context-packet-api-1",
                download_exchange_ref=str(paths["a"]["download_exchange_ref"]),
                discovery_ref=str(paths["a"]["discovery_ref"]),
                selection_ref=str(paths["a"]["selection_ref"]),
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-context-packet-api-2",
                run_id=run_id,
                target_id="target-context-packet-api-2",
                accession_number=None,
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["b"]["content_units_ref"]),
                normalized_text_ref=str(paths["b"]["normalized_text_ref"]),
                normalized_text_sha256="norm-context-packet-api-2",
                blob_ref=str(paths["b"]["blob_ref"]),
                blob_sha256="blob-context-packet-api-2",
                download_exchange_ref=str(paths["b"]["download_exchange_ref"]),
                discovery_ref=str(paths["b"]["discovery_ref"]),
                selection_ref=str(paths["b"]["selection_ref"]),
            )
        )
        db.commit()
    finally:
        db.close()

    bundle_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    assert bundle_a.status_code == 200, bundle_a.text
    bundle_a_payload = bundle_a.json()
    packed_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_a_payload["bundle_id"], "persist_pack": True},
    )
    assert packed_a.status_code == 200, packed_a.text
    packed_a_payload = packed_a.json()
    report_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_a_payload["citation_pack_id"], "persist_report": True},
    )
    assert report_a.status_code == 200, report_a.text
    report_a_payload = report_a.json()
    export_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_a_payload["evidence_report_id"], "persist_export": True},
    )
    assert export_a.status_code == 200, export_a.text
    export_a_payload = export_a.json()

    bundle_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "delta", "persist_bundle": True},
    )
    assert bundle_b.status_code == 200, bundle_b.text
    bundle_b_payload = bundle_b.json()
    packed_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_b_payload["bundle_id"], "persist_pack": True},
    )
    assert packed_b.status_code == 200, packed_b.text
    packed_b_payload = packed_b.json()
    report_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_b_payload["citation_pack_id"], "persist_report": True},
    )
    assert report_b.status_code == 200, report_b.text
    report_b_payload = report_b.json()
    export_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_b_payload["evidence_report_id"], "persist_export": True},
    )
    assert export_b.status_code == 200, export_b.text
    export_b_payload = export_b.json()

    packaged = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-export-packages",
        json={
            "evidence_report_export_ids": [
                export_a_payload["evidence_report_export_id"],
                export_b_payload["evidence_report_export_id"],
            ],
            "persist_package": True,
        },
    )
    assert packaged.status_code == 200, packaged.text
    package_payload = packaged.json()

    context_packet = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-packets",
        json={
            "evidence_report_export_package_id": package_payload["evidence_report_export_package_id"],
            "persist_context_packet": True,
        },
    )
    assert context_packet.status_code == 200, context_packet.text
    context_packet_payload = context_packet.json()
    assert context_packet_payload["schema_id"] == "aps.context_packet.v1"
    assert context_packet_payload["persisted"] is True
    assert context_packet_payload["source_family"] == "evidence_report_export_package"
    assert context_packet_payload["source_descriptor"]["owner_run_id"] == run_id
    assert context_packet_payload["total_facts"] >= 2
    assert Path(context_packet_payload["context_packet_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_context_packets"] == [context_packet_payload["context_packet_ref"]]
    assert detail_payload["report_refs"]["aps_context_packet_failures"] == []

    persisted = client.get(
        f"/api/v1/connectors/nrc-adams-aps/context-packets/{context_packet_payload['context_packet_id']}",
    )
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["context_packet_id"] == context_packet_payload["context_packet_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["context_packet_checksum"] == context_packet_payload["context_packet_checksum"]


def test_nrc_context_dossier_routes_return_persisted_snapshot_and_errors():
    from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
    from app.services import nrc_aps_evidence_bundle_contract as contract

    refs_dir_a = TEST_STORAGE_DIR / "connectors" / "reports" / "context_dossier_api_refs_a"
    refs_dir_b = TEST_STORAGE_DIR / "connectors" / "reports" / "context_dossier_api_refs_b"
    refs_dir_a.mkdir(parents=True, exist_ok=True)
    refs_dir_b.mkdir(parents=True, exist_ok=True)
    paths = {
        "a": {
            "content_units_ref": refs_dir_a / "content_units.json",
            "normalized_text_ref": refs_dir_a / "normalized.txt",
            "blob_ref": refs_dir_a / "blob.bin",
            "download_exchange_ref": refs_dir_a / "download_exchange.json",
            "discovery_ref": refs_dir_a / "discovery.json",
            "selection_ref": refs_dir_a / "selection.json",
        },
        "b": {
            "content_units_ref": refs_dir_b / "content_units.json",
            "normalized_text_ref": refs_dir_b / "normalized.txt",
            "blob_ref": refs_dir_b / "blob.bin",
            "download_exchange_ref": refs_dir_b / "download_exchange.json",
            "discovery_ref": refs_dir_b / "discovery.json",
            "selection_ref": refs_dir_b / "selection.json",
        },
    }
    for path, value in (
        (paths["a"]["content_units_ref"], "{}"),
        (paths["a"]["normalized_text_ref"], "alpha alpha beta alpha gamma"),
        (paths["a"]["blob_ref"], "blob"),
        (paths["a"]["download_exchange_ref"], "{}"),
        (paths["a"]["discovery_ref"], "{}"),
        (paths["a"]["selection_ref"], "{}"),
        (paths["b"]["content_units_ref"], "{}"),
        (paths["b"]["normalized_text_ref"], "alpha delta"),
        (paths["b"]["blob_ref"], "blob"),
        (paths["b"]["download_exchange_ref"], "{}"),
        (paths["b"]["discovery_ref"], "{}"),
        (paths["b"]["selection_ref"], "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    run_id = "run-context-dossier-api-1"
    db = TestingSessionLocal()
    try:
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            source_system="nrc_adams_aps",
            source_mode="public_api",
            status="completed",
        )
        db.add(run)
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-context-dossier-api-1",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=0,
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id="target-context-dossier-api-2",
                connector_run_id=run_id,
                artifact_surface="documents",
                status="recommended",
                ordinal=1,
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-context-dossier-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-context-dossier-api-1",
                normalized_char_count=28,
                chunk_count=2,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-context-dossier-api-1",
                chunk_id="chunk-context-dossier-api-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=16,
                chunk_text="alpha alpha beta",
                chunk_text_sha256="sha-context-dossier-api-1",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-context-dossier-api-1",
                chunk_id="chunk-context-dossier-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=17,
                end_char=28,
                chunk_text="alpha gamma",
                chunk_text_sha256="sha-context-dossier-api-2",
            )
        )
        db.add(
            ApsContentDocument(
                content_id="content-context-dossier-api-2",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-context-dossier-api-2",
                normalized_char_count=11,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-context-dossier-api-2",
                chunk_id="chunk-context-dossier-api-3",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=11,
                chunk_text="alpha delta",
                chunk_text_sha256="sha-context-dossier-api-3",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-context-dossier-api-1",
                run_id=run_id,
                target_id="target-context-dossier-api-1",
                accession_number="ML-CONTEXT-DOSSIER-API-1",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["a"]["content_units_ref"]),
                normalized_text_ref=str(paths["a"]["normalized_text_ref"]),
                normalized_text_sha256="norm-context-dossier-api-1",
                blob_ref=str(paths["a"]["blob_ref"]),
                blob_sha256="blob-context-dossier-api-1",
                download_exchange_ref=str(paths["a"]["download_exchange_ref"]),
                discovery_ref=str(paths["a"]["discovery_ref"]),
                selection_ref=str(paths["a"]["selection_ref"]),
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-context-dossier-api-2",
                run_id=run_id,
                target_id="target-context-dossier-api-2",
                accession_number=None,
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(paths["b"]["content_units_ref"]),
                normalized_text_ref=str(paths["b"]["normalized_text_ref"]),
                normalized_text_sha256="norm-context-dossier-api-2",
                blob_ref=str(paths["b"]["blob_ref"]),
                blob_sha256="blob-context-dossier-api-2",
                download_exchange_ref=str(paths["b"]["download_exchange_ref"]),
                discovery_ref=str(paths["b"]["discovery_ref"]),
                selection_ref=str(paths["b"]["selection_ref"]),
            )
        )
        db.commit()
    finally:
        db.close()

    bundle_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    assert bundle_a.status_code == 200, bundle_a.text
    packed_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_a.json()["bundle_id"], "persist_pack": True},
    )
    assert packed_a.status_code == 200, packed_a.text
    report_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_a.json()["citation_pack_id"], "persist_report": True},
    )
    assert report_a.status_code == 200, report_a.text
    export_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_a.json()["evidence_report_id"], "persist_export": True},
    )
    assert export_a.status_code == 200, export_a.text

    bundle_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-bundles",
        json={"run_id": run_id, "query": "delta", "persist_bundle": True},
    )
    assert bundle_b.status_code == 200, bundle_b.text
    packed_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_b.json()["bundle_id"], "persist_pack": True},
    )
    assert packed_b.status_code == 200, packed_b.text
    report_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_b.json()["citation_pack_id"], "persist_report": True},
    )
    assert report_b.status_code == 200, report_b.text
    export_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-report-exports",
        json={"evidence_report_id": report_b.json()["evidence_report_id"], "persist_export": True},
    )
    assert export_b.status_code == 200, export_b.text

    packet_a = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-packets",
        json={"evidence_report_export_id": export_a.json()["evidence_report_export_id"], "persist_context_packet": True},
    )
    packet_b = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-packets",
        json={"evidence_report_export_id": export_b.json()["evidence_report_export_id"], "persist_context_packet": True},
    )
    assert packet_a.status_code == 200, packet_a.text
    assert packet_b.status_code == 200, packet_b.text

    dossier = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-dossiers",
        json={
            "context_packet_ids": [
                packet_a.json()["context_packet_id"],
                packet_b.json()["context_packet_id"],
            ],
            "persist_dossier": True,
        },
    )
    assert dossier.status_code == 200, dossier.text
    dossier_payload = dossier.json()
    assert dossier_payload["schema_id"] == "aps.context_dossier.v1"
    assert dossier_payload["persisted"] is True
    assert dossier_payload["owner_run_id"] == run_id
    assert dossier_payload["source_packet_count"] == 2
    assert dossier_payload["source_packets"][0]["context_packet_ref"] == packet_a.json()["context_packet_ref"]
    assert Path(dossier_payload["context_dossier_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_context_dossiers"] == [dossier_payload["context_dossier_ref"]]
    assert detail_payload["report_refs"]["aps_context_dossier_failures"] == []

    persisted = client.get(f"/api/v1/connectors/nrc-adams-aps/context-dossiers/{dossier_payload['context_dossier_id']}")
    assert persisted.status_code == 200, persisted.text
    persisted_payload = persisted.json()
    assert persisted_payload["context_dossier_id"] == dossier_payload["context_dossier_id"]
    assert persisted_payload["persisted"] is True
    assert persisted_payload["context_dossier_checksum"] == dossier_payload["context_dossier_checksum"]

    insight = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts",
        json={
            "context_dossier_id": dossier_payload["context_dossier_id"],
            "persist_insight_artifact": True,
        },
    )
    assert insight.status_code == 200, insight.text
    insight_payload = insight.json()
    assert insight_payload["schema_id"] == "aps.deterministic_insight_artifact.v1"
    assert insight_payload["persisted"] is True
    assert insight_payload["source_context_dossier"]["context_dossier_id"] == dossier_payload["context_dossier_id"]
    assert Path(insight_payload["deterministic_insight_artifact_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_context_dossiers"] == [dossier_payload["context_dossier_ref"]]
    assert detail_payload["report_refs"]["aps_context_dossier_failures"] == []
    assert detail_payload["report_refs"]["aps_deterministic_insight_artifacts"] == [
        insight_payload["deterministic_insight_artifact_ref"]
    ]
    assert detail_payload["report_refs"]["aps_deterministic_insight_artifact_failures"] == []

    persisted_insight = client.get(
        "/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts/"
        f"{insight_payload['deterministic_insight_artifact_id']}"
    )
    assert persisted_insight.status_code == 200, persisted_insight.text
    persisted_insight_payload = persisted_insight.json()
    assert persisted_insight_payload["deterministic_insight_artifact_id"] == insight_payload["deterministic_insight_artifact_id"]
    assert persisted_insight_payload["persisted"] is True
    assert persisted_insight_payload["findings"] == insight_payload["findings"]

    challenge = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts",
        json={
            "deterministic_insight_artifact_id": insight_payload["deterministic_insight_artifact_id"],
            "persist_challenge_artifact": True,
        },
    )
    assert challenge.status_code == 200, challenge.text
    challenge_payload = challenge.json()
    assert challenge_payload["schema_id"] == "aps.deterministic_challenge_artifact.v1"
    assert challenge_payload["persisted"] is True
    assert challenge_payload["source_deterministic_insight_artifact"]["deterministic_insight_artifact_id"] == insight_payload["deterministic_insight_artifact_id"]
    assert Path(challenge_payload["deterministic_challenge_artifact_ref"]).exists()

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["report_refs"]["aps_deterministic_challenge_artifacts"] == [
        challenge_payload["deterministic_challenge_artifact_ref"]
    ]
    assert detail_payload["report_refs"]["aps_deterministic_challenge_artifact_failures"] == []

    persisted_challenge = client.get(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts/"
        f"{challenge_payload['deterministic_challenge_artifact_id']}"
    )
    assert persisted_challenge.status_code == 200, persisted_challenge.text
    persisted_challenge_payload = persisted_challenge.json()
    assert persisted_challenge_payload["deterministic_challenge_artifact_id"] == challenge_payload["deterministic_challenge_artifact_id"]
    assert persisted_challenge_payload["persisted"] is True
    assert persisted_challenge_payload["challenges"] == challenge_payload["challenges"]

    invalid_request = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-dossiers",
        json={
            "context_packet_ids": [packet_a.json()["context_packet_id"], packet_b.json()["context_packet_id"]],
            "context_packet_refs": [packet_a.json()["context_packet_ref"], packet_b.json()["context_packet_ref"]],
            "persist_dossier": False,
        },
    )
    assert invalid_request.status_code == 422, invalid_request.text
    assert invalid_request.json()["detail"]["code"] == "invalid_request"

    missing_source = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-dossiers",
        json={
            "context_packet_ids": ["missing-packet-a", "missing-packet-b"],
            "persist_dossier": False,
        },
    )
    assert missing_source.status_code == 404, missing_source.text
    assert missing_source.json()["detail"]["code"] == "source_packet_not_found"

    report_packet = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-packets",
        json={"evidence_report_id": report_a.json()["evidence_report_id"], "persist_context_packet": True},
    )
    assert report_packet.status_code == 200, report_packet.text
    incompat = client.post(
        "/api/v1/connectors/nrc-adams-aps/context-dossiers",
        json={
            "context_packet_refs": [report_packet.json()["context_packet_ref"], packet_a.json()["context_packet_ref"]],
            "persist_dossier": False,
        },
    )
    assert incompat.status_code == 409, incompat.text
    assert incompat.json()["detail"]["code"] == "source_packet_incompatible"


def test_nrc_context_dossier_get_fails_closed_on_ambiguous_id():
    from app.services import nrc_aps_context_dossier
    from app.services import nrc_aps_context_dossier_contract as dossier_contract

    reports_dir = Path(nrc_aps_context_dossier.settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    def _synthetic_context_packet(*, run_id: str, packet_id: str, packet_checksum: str, packet_ref: str) -> dict:
        return {
            "schema_id": "aps.context_packet.v1",
            "schema_version": 1,
            "generated_at_utc": "2026-03-12T00:00:00Z",
            "context_packet_id": packet_id,
            "context_packet_checksum": packet_checksum,
            "_context_packet_ref": packet_ref,
            "projection_contract_id": "aps_context_packet_projection_v1",
            "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
            "source_family": "evidence_report_export_package",
            "source_descriptor": {
                "source_id": f"source-{packet_id}",
                "source_checksum": f"source-sum-{packet_id}",
                "owner_run_id": run_id,
            },
            "objective": "normalize_persisted_source_for_downstream_consumption",
            "total_facts": 3,
            "total_caveats": 2,
            "total_constraints": 1,
            "total_unresolved_questions": 1,
        }

    run_a_payload = dossier_contract.build_context_dossier_payload(
        [
            _synthetic_context_packet(
                run_id="run-api-ambig-a",
                packet_id="packet-1",
                packet_checksum="sum-1",
                packet_ref="C:/tmp/run-a-packet-1.json",
            ),
            _synthetic_context_packet(
                run_id="run-api-ambig-a",
                packet_id="packet-2",
                packet_checksum="sum-2",
                packet_ref="C:/tmp/run-a-packet-2.json",
            ),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    run_b_payload = dossier_contract.build_context_dossier_payload(
        [
            _synthetic_context_packet(
                run_id="run-api-ambig-b",
                packet_id="packet-1",
                packet_checksum="sum-1",
                packet_ref="C:/tmp/run-b-packet-1.json",
            ),
            _synthetic_context_packet(
                run_id="run-api-ambig-b",
                packet_id="packet-2",
                packet_checksum="sum-2",
                packet_ref="C:/tmp/run-b-packet-2.json",
            ),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert run_a_payload["context_dossier_id"] == run_b_payload["context_dossier_id"]
    dossier_id = str(run_a_payload["context_dossier_id"])

    path_a = reports_dir / dossier_contract.expected_context_dossier_file_name(scope="run_aaa", context_dossier_id=dossier_id)
    path_b = reports_dir / dossier_contract.expected_context_dossier_file_name(scope="run_zzz", context_dossier_id=dossier_id)
    path_a.write_text(json.dumps(run_a_payload, indent=2, sort_keys=True), encoding="utf-8")
    path_b.write_text(json.dumps(run_b_payload, indent=2, sort_keys=True), encoding="utf-8")

    response = client.get(f"/api/v1/connectors/nrc-adams-aps/context-dossiers/{dossier_id}")
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "context_dossier_conflict"


def test_nrc_deterministic_insight_artifact_routes_return_errors(monkeypatch):
    from app.services import nrc_aps_context_dossier
    from app.services import nrc_aps_context_dossier_contract as dossier_contract
    from app.services import nrc_aps_deterministic_insight_artifact
    from app.services import nrc_aps_deterministic_insight_artifact_contract as insight_contract

    invalid_request = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts",
        json={
            "context_dossier_id": "dossier-1",
            "context_dossier_ref": "C:/tmp/dossier.json",
            "persist_insight_artifact": False,
        },
    )
    assert invalid_request.status_code == 422, invalid_request.text
    assert invalid_request.json()["detail"]["code"] == "invalid_request"

    missing_source = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts",
        json={
            "context_dossier_id": "missing-dossier",
            "persist_insight_artifact": False,
        },
    )
    assert missing_source.status_code == 404, missing_source.text
    assert missing_source.json()["detail"]["code"] == "source_dossier_not_found"

    def _raise_conflict(**kwargs):
        raise nrc_aps_context_dossier.ContextDossierError(
            dossier_contract.APS_RUNTIME_FAILURE_CONFLICT,
            "ambiguous across runs",
            status_code=409,
        )

    monkeypatch.setattr(
        nrc_aps_deterministic_insight_artifact.nrc_aps_context_dossier,
        "load_persisted_context_dossier_artifact",
        _raise_conflict,
    )
    ambiguous = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts",
        json={
            "context_dossier_id": "ambiguous-dossier",
            "persist_insight_artifact": False,
        },
    )
    assert ambiguous.status_code == 409, ambiguous.text
    assert ambiguous.json()["detail"]["code"] == insight_contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_CONFLICT


def test_nrc_deterministic_challenge_artifact_routes_return_errors(monkeypatch):
    from app.services import nrc_aps_deterministic_challenge_artifact
    from app.services import nrc_aps_deterministic_challenge_artifact_contract as challenge_contract
    from app.services import nrc_aps_deterministic_insight_artifact

    invalid_request = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts",
        json={
            "deterministic_insight_artifact_id": "insight-1",
            "deterministic_insight_artifact_ref": "C:/tmp/insight.json",
            "persist_challenge_artifact": False,
        },
    )
    assert invalid_request.status_code == 422, invalid_request.text
    assert invalid_request.json()["detail"]["code"] == "invalid_request"

    missing_source = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts",
        json={
            "deterministic_insight_artifact_id": "missing-insight",
            "persist_challenge_artifact": False,
        },
    )
    assert missing_source.status_code == 404, missing_source.text
    assert missing_source.json()["detail"]["code"] == "source_insight_artifact_not_found"

    def _raise_conflict(**kwargs):
        raise nrc_aps_deterministic_insight_artifact.DeterministicInsightArtifactError(
            challenge_contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_CONFLICT,
            "ambiguous across runs",
            status_code=409,
        )

    monkeypatch.setattr(
        nrc_aps_deterministic_challenge_artifact.nrc_aps_deterministic_insight_artifact,
        "load_persisted_deterministic_insight_artifact",
        _raise_conflict,
    )
    ambiguous = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts",
        json={
            "deterministic_insight_artifact_id": "ambiguous-insight",
            "persist_challenge_artifact": False,
        },
    )
    assert ambiguous.status_code == 409, ambiguous.text
    assert ambiguous.json()["detail"]["code"] == challenge_contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_CONFLICT


def test_nrc_deterministic_challenge_review_packet_routes_return_errors(monkeypatch):
    from app.services import nrc_aps_deterministic_challenge_review_packet
    from app.services import nrc_aps_deterministic_challenge_review_packet_contract as rp_contract
    from app.services import nrc_aps_deterministic_challenge_artifact

    invalid_request = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets",
        json={
            "deterministic_challenge_artifact_id": "id-1",
            "deterministic_challenge_artifact_ref": "C:/tmp/challenge.json",
            "persist_review_packet": False,
        },
    )
    assert invalid_request.status_code == 422, invalid_request.text
    assert invalid_request.json()["detail"]["code"] == "invalid_request"

    missing_source = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets",
        json={
            "deterministic_challenge_artifact_id": "missing-challenge",
            "persist_review_packet": False,
        },
    )
    assert missing_source.status_code == 404, missing_source.text
    assert missing_source.json()["detail"]["code"] == "source_challenge_artifact_not_found"

    def _raise_conflict(**kwargs):
        raise nrc_aps_deterministic_challenge_artifact.DeterministicChallengeArtifactError(
            rp_contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_CONFLICT,
            "ambiguous across runs",
            status_code=409,
        )

    monkeypatch.setattr(
        nrc_aps_deterministic_challenge_review_packet.nrc_aps_deterministic_challenge_artifact,
        "load_persisted_deterministic_challenge_artifact",
        _raise_conflict,
    )
    ambiguous = client.post(
        "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets",
        json={
            "deterministic_challenge_artifact_id": "ambiguous-challenge",
            "persist_review_packet": False,
        },
    )
    assert ambiguous.status_code == 409, ambiguous.text
    assert ambiguous.json()["detail"]["code"] == rp_contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_CONFLICT


def test_nrc_deterministic_challenge_review_packet_persist_and_report_refs(monkeypatch):
    from app.models import ConnectorRun

    reports_dir = TEST_STORAGE_DIR / "connectors" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    db = TestingSessionLocal()
    try:
        run_id = "run-review-packet-api-e2e"
        from test_nrc_aps_context_dossier import _patch_runtime_settings
        from test_nrc_aps_deterministic_insight_artifact import _persisted_context_dossier, _seed_report_index_rows
        _patch_runtime_settings(monkeypatch, reports_dir)
        _seed_report_index_rows(db, reports_dir=reports_dir, run_id=run_id)
        seeded = _persisted_context_dossier(db, run_id=run_id)

        insight_result = client.post(
            "/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts",
            json={
                "context_dossier_ref": seeded["dossier"]["context_dossier_ref"],
                "persist_insight_artifact": True,
            },
        )
        assert insight_result.status_code == 200, insight_result.text
        insight_data = insight_result.json()

        challenge_result = client.post(
            "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts",
            json={
                "deterministic_insight_artifact_ref": insight_data["deterministic_insight_artifact_ref"],
                "persist_challenge_artifact": True,
            },
        )
        assert challenge_result.status_code == 200, challenge_result.text
        challenge_data = challenge_result.json()

        review_packet_result = client.post(
            "/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets",
            json={
                "deterministic_challenge_artifact_ref": challenge_data["deterministic_challenge_artifact_ref"],
                "persist_review_packet": True,
            },
        )
        assert review_packet_result.status_code == 200, review_packet_result.text
        rp_data = review_packet_result.json()
        assert rp_data["persisted"] is True
        assert rp_data["deterministic_challenge_review_packet_ref"] is not None
        assert rp_data["total_challenges"] == rp_data["blocker_count"] + rp_data["review_item_count"] + rp_data["acknowledgement_count"]

        get_result = client.get(
            f"/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets/{rp_data['deterministic_challenge_review_packet_id']}",
        )
        assert get_result.status_code == 200, get_result.text
        get_data = get_result.json()
        assert get_data["deterministic_challenge_review_packet_id"] == rp_data["deterministic_challenge_review_packet_id"]
        assert get_data["persisted"] is True

        db.expire_all()
        run = db.get(ConnectorRun, run_id)
        report_refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_report_refs") or {})
        assert report_refs.get("aps_deterministic_challenge_review_packets") == [
            rp_data["deterministic_challenge_review_packet_ref"]
        ]
        assert report_refs.get("aps_deterministic_challenge_review_packet_failures") == []

        run_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
        assert run_detail.status_code == 200, run_detail.text
        detail_data = run_detail.json()
        rr = detail_data.get("report_refs") or {}
        assert rr["aps_deterministic_challenge_review_packets"] == [
            rp_data["deterministic_challenge_review_packet_ref"]
        ]
        assert rr["aps_deterministic_challenge_review_packet_failures"] == []
    finally:
        db.close()


def test_nrc_content_index_not_available_zero_chunk_artifact(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcNoUrlClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "run_mode": "metadata_only",
            "artifact_pipeline_mode": "download_only",
            "artifact_required_for_target_success": False,
        },
        headers={"Idempotency-Key": "nrc-content-index-not-available"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    run_artifact = json.loads(Path(payload["report_refs"]["aps_content_index"]).read_text(encoding="utf-8"))
    assert int(run_artifact["content_status_counts"].get("artifact_not_available", 0)) >= 1
    content_ref = run_artifact["content_units_artifacts"][0]["ref"]
    content_artifact = json.loads(Path(content_ref).read_text(encoding="utf-8"))
    assert content_artifact["content_status"] == "artifact_not_available"
    assert int(content_artifact["chunk_count"]) == 0
    assert content_artifact["chunks"] == []


def test_nrc_content_search_rejects_empty_query():
    response = client.post(
        "/api/v1/connectors/nrc-adams-aps/content-search",
        json={"query": "   "},
    )
    assert response.status_code == 422


def test_nrc_adams_shape_b_mapper(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcMapperProbeClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "lenient_pass_through",
            "queryString": "nuclear safety",
            "docketNumber": "05000275,05000323",
            "filters": [{"name": "DocumentType", "operator": "eq", "value": "Letter"}],
            "sort": "-DateAddedTimestamp",
            "skip": 0,
            "page_size": 25,
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-shape-b"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] in {"completed", "completed_with_errors"}

    assert fake.search_payloads
    outbound = fake.search_payloads[0]
    assert outbound["q"] == "nuclear safety"
    assert outbound["sort"] == "DateAddedTimestamp"
    assert outbound["sortDirection"] == 1

    props = outbound["filters"]
    doc_type = [item for item in props if item.get("field") == "DocumentType"]
    assert doc_type and doc_type[0].get("operator") == "equals"

    docket_props = [item for item in props if item.get("field") == "DocketNumber"]
    assert {item.get("value") for item in docket_props} == {"05000275", "05000323"}


def test_nrc_adams_wire_shape_fallback_from_shape_a_to_guide(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcWireFallbackClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "auto_probe",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
                "skip": 0,
            },
            "page_size": 10,
            "max_items": 1,
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-wire-shape-fallback"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] in {"completed", "completed_with_errors"}
    assert payload["recommended_count"] >= 1

    assert len(fake.search_payloads) >= 2
    assert "q" in fake.search_payloads[0]
    assert "filters" in fake.search_payloads[0]
    assert "searchCriteria" in fake.search_payloads[1]

    events = client.get(f"/api/v1/connectors/runs/{run_id}/events")
    assert events.status_code == 200, events.text
    event_types = {row["event_type"] for row in events.json()["events"]}
    assert "search_shape_fallback" in event_types


def test_nrc_document_types_json_is_canonical_source():
    from app.services.connectors_nrc_adams import _load_document_types_reference

    values = _load_document_types_reference()
    assert "Inspection Report" in values
    assert len(values) > 100


def test_nrc_forced_known_bad_dialect_blocked_without_override():
    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "guide_native",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
            },
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-forced-known-bad-block"},
    )
    assert submit.status_code == 409, submit.text
    assert "blocked by config lint" in submit.text


def test_nrc_capability_and_sync_cursor_persisted(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ApsDialectCapability, ApsSyncCursor, ConnectorRun
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "auto_probe",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
            },
            "sync_mode": "incremental",
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-capability-sync"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        source_query_fingerprint = str(run.source_query_fingerprint or "")
        assert source_query_fingerprint

        capability_rows = db.query(ApsDialectCapability).all()
        assert capability_rows
        assert any(str(row.dialect) == "shape_a" and int(row.success_count or 0) >= 1 for row in capability_rows)

        cursor = (
            db.query(ApsSyncCursor)
            .filter(ApsSyncCursor.logical_query_fingerprint == source_query_fingerprint)
            .first()
        )
        assert cursor is not None
        assert str(cursor.last_watermark_iso or "").startswith("2025-02-02")
    finally:
        db.close()


def test_nrc_auto_probe_prefers_persisted_capability(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ApsDialectCapability
    from app.services import connectors_nrc_adams as nrc

    db = SessionLocal()
    try:
        db.query(ApsDialectCapability).filter(
            ApsDialectCapability.subscription_key_hash == nrc._subscription_key_hash(),
            ApsDialectCapability.api_host == nrc._aps_api_host(),
        ).delete(synchronize_session=False)
        row = (
            db.query(ApsDialectCapability)
            .filter(
                ApsDialectCapability.subscription_key_hash == nrc._subscription_key_hash(),
                ApsDialectCapability.api_host == nrc._aps_api_host(),
                ApsDialectCapability.dialect == "guide_native",
            )
            .first()
        )
        if row is None:
            row = ApsDialectCapability(
                subscription_key_hash=nrc._subscription_key_hash(),
                api_host=nrc._aps_api_host(),
                dialect="guide_native",
                observed_envelope_keys_json={},
                observed_count_keys_json=[],
                evidence_refs_json=[],
                notes_json={},
            )
            db.add(row)
        row.success_count = 5
        row.failure_count = 0
        row.cooldown_until = None
        row.last_status = 200
        row.updated_at = nrc._utcnow()
        db.commit()
    finally:
        db.close()

    fake = _FakeNrcMapperProbeClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "auto_probe",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
            },
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-capability-preference"},
    )
    assert submit.status_code == 202, submit.text
    assert fake.search_payloads
    assert "searchCriteria" in fake.search_payloads[0]


def test_nrc_incremental_sync_drift_artifacts_baseline_resolution(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    first_submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "auto_probe",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report baseline",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
            },
            "sync_mode": "incremental",
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-sync-drift-baseline-first"},
    )
    assert first_submit.status_code == 202, first_submit.text
    first_run_id = first_submit.json()["connector_run_id"]

    second_submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "auto_probe",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report baseline",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
            },
            "sync_mode": "incremental",
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-sync-drift-baseline-second"},
    )
    assert second_submit.status_code == 202, second_submit.text
    second_run_id = second_submit.json()["connector_run_id"]

    first_detail = client.get(f"/api/v1/connectors/runs/{first_run_id}")
    assert first_detail.status_code == 200, first_detail.text
    first_payload = first_detail.json()
    first_drift_ref = first_payload["report_refs"]["aps_sync_drift"]
    assert first_drift_ref
    first_drift = json.loads(Path(first_drift_ref).read_text(encoding="utf-8"))
    assert first_drift["baseline_resolution"] == "no_baseline"
    assert first_drift["baseline_run_id"] is None

    second_detail = client.get(f"/api/v1/connectors/runs/{second_run_id}")
    assert second_detail.status_code == 200, second_detail.text
    second_payload = second_detail.json()
    second_drift_ref = second_payload["report_refs"]["aps_sync_drift"]
    assert second_drift_ref
    second_drift = json.loads(Path(second_drift_ref).read_text(encoding="utf-8"))
    assert second_drift["baseline_resolution"] == "incremental_prev_incremental"
    assert second_drift["baseline_run_id"] == first_run_id


def test_aps_sync_drift_artifact_generation_failure_forces_completed_with_errors(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

    fake = _FakeNrcClient()
    monkeypatch.setattr(nrc, "get_nrc_adams_client", lambda config: fake)

    def _raise_artifact_failure(**kwargs):
        raise RuntimeError("forced_sync_drift_failure")

    monkeypatch.setattr(nrc.nrc_aps_sync_drift, "build_delta_and_drift_artifacts", _raise_artifact_failure)

    submit = client.post(
        "/api/v1/connectors/nrc-adams-aps/runs",
        json={
            "mode": "strict_builder",
            "wire_shape_mode": "auto_probe",
            "query_payload": {
                "searchCriteria": {
                    "q": "inspection report artifact failure",
                    "mainLibFilter": True,
                    "legacyLibFilter": False,
                    "properties": [],
                },
                "sort": "DateAddedTimestamp",
                "sortDirection": 1,
            },
            "sync_mode": "incremental",
            "run_mode": "metadata_only",
            "download_artifacts": False,
        },
        headers={"Idempotency-Key": "nrc-sync-drift-failure"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed_with_errors"
    assert "aps_sync_drift_artifact_generation_failed" in str(payload["error_summary"] or "")
    assert payload["report_refs"]["aps_sync_delta"] is None
    assert payload["report_refs"]["aps_sync_drift"] is None
    failure_ref = payload["report_refs"]["aps_sync_drift_failure"]
    assert failure_ref and Path(failure_ref).exists()
    failure_payload = json.loads(Path(failure_ref).read_text(encoding="utf-8"))
    assert failure_payload["schema_id"] == "aps.sync_drift_failure.v1"

    events = client.get(f"/api/v1/connectors/runs/{run_id}/events")
    assert events.status_code == 200, events.text
    event_types = {row["event_type"] for row in events.json()["events"]}
    assert "aps_sync_drift_artifact_failed" in event_types


def test_nrc_safe_filename_truncates_long_names():
    from app.services.connectors_nrc_adams import _fit_filename_for_path, _safe_filename

    raw = ("ANNUAL_STATUS_REPORT_" * 40) + ".pdf"
    safe = _safe_filename(raw)
    assert len(safe) <= 120
    assert safe.endswith(".pdf")

    base_dir = Path("C:/very/long/path/segment/that/simulates/windows/max/path/pressure/connectors/raw/run-id")
    fitted = _fit_filename_for_path(base_dir, "01234567-89ab-cdef-0123-456789abcdef", safe, max_path_len=140)
    assert len(str(base_dir / f"01234567-89ab-cdef-0123-456789abcdef_{fitted}")) <= 140


class _FakeSenateLdaClient:
    def __init__(self):
        self.list_calls = []
        self.detail_calls = []

    def list_filings(
        self,
        *,
        params,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        self.list_calls.append(dict(params))
        page = int(params.get("page", 1))
        if page > 1:
            return {"count": 2, "next": None, "previous": None, "results": []}
        return {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "filing_uuid": "filing-1",
                    "url": "https://lda.senate.gov/api/v1/filings/filing-1/",
                    "filing_type": "LD-2",
                    "filing_year": 2025,
                    "filing_period": "mid_year",
                    "dt_posted": "2025-07-01",
                    "filing_document_url": "https://lda.senate.gov/filing-1.pdf",
                    "filing_document_content_type": "application/pdf",
                    "registrant": {"name": "Registrant One"},
                    "client": {"name": "Client One"},
                },
                {
                    "filing_uuid": "filing-2",
                    "url": "https://lda.senate.gov/api/v1/filings/filing-2/",
                    "filing_type": "LD-203",
                    "filing_year": 2025,
                    "filing_period": "year_end",
                    "dt_posted": "2025-12-31",
                    "filing_document_url": "https://lda.senate.gov/filing-2.pdf",
                    "filing_document_content_type": "application/pdf",
                    "registrant": {"name": "Registrant Two"},
                    "client": {"name": "Client Two"},
                },
            ],
        }

    def get_filing_detail(
        self,
        *,
        filing_uuid,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        self.detail_calls.append(filing_uuid)
        return {
            "filing_uuid": filing_uuid,
            "url": f"https://lda.senate.gov/api/v1/filings/{filing_uuid}/",
            "filing_type": "LD-2" if filing_uuid == "filing-1" else "LD-203",
            "filing_year": 2025,
            "filing_period": "mid_year" if filing_uuid == "filing-1" else "year_end",
            "dt_posted": "2025-07-01" if filing_uuid == "filing-1" else "2025-12-31",
            "filing_document_url": f"https://lda.senate.gov/{filing_uuid}.pdf",
            "filing_document_content_type": "application/pdf",
            "registrant": {"name": f"Registrant {filing_uuid}"},
            "client": {"name": f"Client {filing_uuid}"},
        }


class _UnexpectedSenateLdaClient:
    def list_filings(
        self,
        *,
        params,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        raise AssertionError("senate lda client should not execute")


class _CancellingSenateLdaClient(_FakeSenateLdaClient):
    def __init__(self):
        super().__init__()
        self.run_id = None

    def list_filings(
        self,
        *,
        params,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        assert self.run_id is not None
        from app.db.session import SessionLocal
        from app.services.connectors_sciencebase import request_cancel_run

        db = SessionLocal()
        try:
            request_cancel_run(db, self.run_id)
        finally:
            db.close()
        return super().list_filings(
            params=params,
            timeout_seconds=timeout_seconds,
            retry_max_attempts_per_request=retry_max_attempts_per_request,
            retry_base_backoff_seconds=retry_base_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_respect_retry_after=retry_respect_retry_after,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
        )


class _RetryingFakeSenateLdaClient(_FakeSenateLdaClient):
    def __init__(self):
        super().__init__()
        self.detail_attempts = {}

    def get_filing_detail(
        self,
        *,
        filing_uuid,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        self.detail_calls.append(filing_uuid)
        self.detail_attempts[filing_uuid] = int(self.detail_attempts.get(filing_uuid, 0)) + 1
        if self.detail_attempts[filing_uuid] == 1:
            response = requests.Response()
            response.status_code = 503
            error = requests.HTTPError("503 Server Error")
            error.response = response
            raise error
        return super().get_filing_detail(
            filing_uuid=filing_uuid,
            timeout_seconds=timeout_seconds,
            retry_max_attempts_per_request=retry_max_attempts_per_request,
            retry_base_backoff_seconds=retry_base_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_respect_retry_after=retry_respect_retry_after,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
        )


class _L17SenateLdaClient(_FakeSenateLdaClient):
    def __init__(self, *, list_payload=None, detail_error_case=None):
        super().__init__()
        self.list_payload = list_payload
        self.detail_error_case = detail_error_case

    def list_filings(
        self,
        *,
        params,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        self.list_calls.append(dict(params))
        if self.list_payload is not None:
            return self.list_payload
        return super().list_filings(
            params=params,
            timeout_seconds=timeout_seconds,
            retry_max_attempts_per_request=retry_max_attempts_per_request,
            retry_base_backoff_seconds=retry_base_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_respect_retry_after=retry_respect_retry_after,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
        )

    def get_filing_detail(
        self,
        *,
        filing_uuid,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        self.detail_calls.append(filing_uuid)
        if self.detail_error_case == "timeout":
            raise requests.Timeout("simulated senate detail timeout")
        if self.detail_error_case == "http_403":
            response = requests.Response()
            response.status_code = 403
            response.url = f"https://lda.senate.gov/api/v1/filings/{filing_uuid}/"
            error = requests.HTTPError("403 Forbidden", response=response)
            raise error
        if self.detail_error_case == "missing_schema":
            return {
                "url": f"https://lda.senate.gov/api/v1/filings/{filing_uuid}/",
                "filing_type": "LD-2",
                "filing_year": 2025,
                "filing_period": "mid_year",
                "dt_posted": "2025-07-01",
            }
        return super().get_filing_detail(
            filing_uuid=filing_uuid,
            timeout_seconds=timeout_seconds,
            retry_max_attempts_per_request=retry_max_attempts_per_request,
            retry_base_backoff_seconds=retry_base_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_respect_retry_after=retry_respect_retry_after,
            rate_limiter=rate_limiter,
            retry_counters=retry_counters,
        )


class _SequenceJsonResponse:
    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error

    def json(self):
        return self._payload


class _SequenceSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params, headers, timeout):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {}), "timeout": timeout})
        if not self.responses:
            raise AssertionError("unexpected Senate LDA request")
        return self.responses.pop(0)


def test_senate_lda_connector_happy_path_reports_and_detail_hydration(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import DatasetSourceProvenance
    from app.services import connectors_senate_lda as senate_lda

    fake = _FakeSenateLdaClient()
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={
            "client_name": "Meta",
            "filing_year": 2025,
            "page_size": 25,
            "max_items": 2,
            "include_filing_detail": True,
            "run_mode": "metadata_only",
        },
        headers={"Idempotency-Key": "senate-lda-happy-path"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["connector_key"] == "senate_lda"
    assert payload["status"] == "completed"
    assert payload["artifact_surface_counts"]["filings"] == 2
    assert Path(payload["report_refs"]["senate_lda_summary"]).exists()
    assert Path(payload["manifest_refs"]["discovery_snapshot_ref"]).exists()
    assert Path(payload["manifest_refs"]["selection_manifest_ref"]).exists()

    reports = client.get(f"/api/v1/connectors/runs/{run_id}/reports")
    assert reports.status_code == 200, reports.text
    reports_payload = reports.json()
    assert "senate_lda_summary" in reports_payload["reports"]
    assert reports_payload["report_status"]["senate_lda_summary"] is True

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_payload = targets.json()
    assert target_payload["total"] == 2
    assert {row["status"] for row in target_payload["targets"]} == {"recommended"}
    assert fake.detail_calls == ["filing-1", "filing-2"]

    db = SessionLocal()
    try:
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "senate_lda")
            .all()
        )
        assert len(provenance_rows) == 2
        assert all((row.source_reference_json or {}).get("detail_ref") for row in provenance_rows)
    finally:
        db.close()


def test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, DatasetSourceProvenance
    from app.services import connectors_senate_lda as senate_lda

    fake = _FakeSenateLdaClient()
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={
            "client_name": "Meta",
            "filing_year": 2025,
            "page_size": 25,
            "max_items": 2,
            "include_filing_detail": False,
            "run_mode": "metadata_only",
        },
        headers={"Idempotency-Key": f"senate-lda-anonymous-metadata-secondary-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["connector_key"] == "senate_lda"
    assert payload["source_system"] == "senate_lda"
    assert payload["status"] == "completed"
    assert payload["run_mode"] == "metadata_only"
    assert payload["fetch_policy_summary"] == {
        "mode": "official_api_only",
        "surface_policy": "metadata_only",
        "external_fetch_policy": "senate_lda_official_only",
        "allowed_hosts": ["lda.senate.gov"],
    }

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 2
    assert {row["status"] for row in target_rows} == {"recommended"}
    assert all(row["dataset_version_id"] for row in target_rows)
    assert fake.detail_calls == []

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.effective_search_params_json["auth_mode"] == "anonymous"
        request_config = run.request_config_json or {}
        assert "api_key" not in request_config
        assert "authorization" not in request_config
        assert "token" not in request_config
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "senate_lda")
            .all()
        )
        assert len(provenance_rows) == 2
        assert {row.source_mode for row in provenance_rows} == {"metadata_only"}
    finally:
        db.close()


def test_senate_lda_connector_submission_idempotency_reuse_and_conflict(monkeypatch):
    from app.services import connectors_senate_lda as senate_lda

    fake = _FakeSenateLdaClient()
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    first = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025},
        headers={"Idempotency-Key": "senate-lda-idempotency"},
    )
    assert first.status_code == 202, first.text
    first_payload = first.json()

    second = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025},
        headers={"Idempotency-Key": "senate-lda-idempotency"},
    )
    assert second.status_code == 202, second.text
    second_payload = second.json()
    assert second_payload["connector_run_id"] == first_payload["connector_run_id"]
    assert second_payload["created"] is False

    conflict = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Different Client", "filing_year": 2025},
        headers={"Idempotency-Key": "senate-lda-idempotency"},
    )
    assert conflict.status_code == 409, conflict.text


def test_senate_lda_connector_resume_uses_senate_executor(monkeypatch):
    from app.api import router
    from app.services import connectors_senate_lda as senate_lda

    fake = _RetryingFakeSenateLdaClient()
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    def _wrong_executor(*args, **kwargs):
        raise AssertionError("sciencebase executor should not run for senate_lda")

    monkeypatch.setattr(router, "execute_connector_run", _wrong_executor)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={
            "client_name": "Meta",
            "filing_year": 2025,
            "include_filing_detail": True,
            "retry_max_attempts_per_request": 1,
        },
        headers={"Idempotency-Key": "senate-lda-resume"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    first_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert first_detail.status_code == 200, first_detail.text
    assert first_detail.json()["status"] == "completed_with_errors"

    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text

    second_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert second_detail.status_code == 200, second_detail.text
    assert second_detail.json()["status"] == "completed"

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    assert {row["status"] for row in targets.json()["targets"]} == {"recommended"}
    assert len(fake.list_calls) == 1


def test_senate_lda_l20_active_lease_records_conflict(monkeypatch):
    from datetime import timedelta

    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget
    from app.services import connectors_senate_lda as senate_lda

    monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: _UnexpectedSenateLdaClient())

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025},
        headers={"Idempotency-Key": "l20-senate-lda-lease-conflict"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        run.status = "running"
        run.execution_lease_owner = f"pid:{os.getpid()}"
        run.execution_lease_token = "held-token"
        run.execution_lease_expires_at = senate_lda._utcnow() + timedelta(seconds=300)
        db.commit()
    finally:
        db.close()

    senate_lda.execute_senate_lda_run(run_id)

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        observed_error_summary = run.error_summary
        observed_lease_conflicts = (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.connector_run_id == run_id, ConnectorRunEvent.event_type == "lease_conflict")
            .count()
        )
        observed_target_count = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).count()
        run.status = "failed"
        db.commit()
    finally:
        db.close()
    assert observed_error_summary == "lease_conflict"
    assert observed_lease_conflicts == 1
    assert observed_target_count == 0


def test_senate_lda_l20_cancel_mid_page_stops_before_partial_authority(monkeypatch):
    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget, DatasetSourceProvenance
    from app.services import connectors_senate_lda as senate_lda

    fake = _CancellingSenateLdaClient()
    monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025, "include_filing_detail": False},
        headers={"Idempotency-Key": "l20-senate-lda-cancel-mid-page"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]
    fake.run_id = run_id

    senate_lda.execute_senate_lda_run(run_id)

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.status == "cancelled"
        assert run.cancelled_at is not None
        assert run.error_summary == "cancelled_by_operator"
        assert run.execution_lease_owner is None
        assert run.execution_lease_token is None
        assert run.execution_lease_expires_at is not None
        assert db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).count() == 0
        assert db.query(DatasetSourceProvenance).filter(DatasetSourceProvenance.connector_run_id == run_id).count() == 0
        event_types = {
            row.event_type
            for row in db.query(ConnectorRunEvent).filter(ConnectorRunEvent.connector_run_id == run_id).all()
        }
        assert "run_cancel_requested" in event_types
        assert "run_finalized" in event_types
    finally:
        db.close()


def test_senate_lda_l20_resume_after_target_creation_crash_does_not_duplicate_targets(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget
    from app.services import connectors_senate_lda as senate_lda

    fake = _FakeSenateLdaClient()
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)
    real_create_targets = senate_lda._create_targets_from_discovery
    crashed = {"done": False}

    def _crash_after_targets(*args, **kwargs):
        real_create_targets(*args, **kwargs)
        if not crashed["done"]:
            crashed["done"] = True
            raise RuntimeError("simulated crash after persisted senate lda targets")

    monkeypatch.setattr(senate_lda, "_create_targets_from_discovery", _crash_after_targets)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025, "include_filing_detail": False, "max_items": 2},
        headers={"Idempotency-Key": "l20-senate-lda-crash-resume"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    first_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert first_detail.status_code == 200, first_detail.text
    assert first_detail.json()["status"] == "failed"

    monkeypatch.setattr(senate_lda, "_create_targets_from_discovery", real_create_targets)
    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text

    second_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert second_detail.status_code == 200, second_detail.text
    assert second_detail.json()["status"] == "completed"

    db = SessionLocal()
    try:
        targets = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        assert [target.sciencebase_item_id for target in targets] == ["filing-1", "filing-2"]
        assert len(fake.list_calls) == 1
    finally:
        db.close()


def test_senate_lda_dedupes_duplicate_filings_and_records_provenance(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_senate_lda as senate_lda

    class _DuplicateFilingSenateLdaClient(_FakeSenateLdaClient):
        def list_filings(
            self,
            *,
            params,
            timeout_seconds,
            retry_max_attempts_per_request,
            retry_base_backoff_seconds,
            retry_max_backoff_seconds,
            retry_respect_retry_after,
            rate_limiter,
            retry_counters,
        ):
            self.list_calls.append(dict(params))
            page = int(params.get("page", 1))
            filing = {
                "filing_uuid": "filing-dup",
                "url": "https://lda.senate.gov/api/v1/filings/filing-dup/",
                "filing_type": "LD-2",
                "filing_year": 2025,
                "filing_period": "mid_year",
                "dt_posted": "2025-07-01",
                "filing_document_url": "https://lda.senate.gov/filing-dup.pdf",
                "filing_document_content_type": "application/pdf",
                "registrant": {"name": "Registrant Duplicate"},
                "client": {"name": "Client Duplicate"},
            }
            if page == 1:
                return {"count": 3, "next": "https://lda.senate.gov/api/v1/filings/?page=2", "previous": None, "results": [filing]}
            if page == 2:
                second = dict(filing)
                second["url"] = "https://lda.senate.gov/api/v1/filings/filing-dup/?page=2"
                distinct = {
                    "filing_uuid": "filing-2",
                    "url": "https://lda.senate.gov/api/v1/filings/filing-2/",
                    "filing_type": "LD-203",
                    "filing_year": 2025,
                    "filing_period": "year_end",
                    "dt_posted": "2025-12-31",
                    "filing_document_url": "https://lda.senate.gov/filing-2.pdf",
                    "filing_document_content_type": "application/pdf",
                    "registrant": {"name": "Registrant Two"},
                    "client": {"name": "Client Two"},
                }
                return {"count": 3, "next": None, "previous": None, "results": [second, distinct]}
            return {"count": 3, "next": None, "previous": None, "results": []}

    fake = _DuplicateFilingSenateLdaClient()
    monkeypatch.setattr(senate_lda, "get_senate_lda_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/senate-lda/runs",
        json={"client_name": "Meta", "filing_year": 2025, "include_filing_detail": False},
        headers={"Idempotency-Key": f"senate-lda-duplicate-provenance-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    targets_response = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets_response.status_code == 200, targets_response.text
    target_rows = targets_response.json()["targets"]
    assert targets_response.json()["total"] == 3
    assert [row["status"] for row in target_rows].count("recommended") == 2
    assert [row["status"] for row in target_rows].count("collapsed_duplicate") == 1

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.collapsed_duplicate_count == 1
        targets = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        assert [target.ordinal for target in targets] == [1, 2, 3]
        assert [target.sciencebase_item_id for target in targets] == ["filing-dup", "filing-dup", "filing-2"]
        recommended_targets = [target for target in targets if target.status == "recommended"]
        collapsed_targets = [target for target in targets if target.status == "collapsed_duplicate"]
        assert [target.sciencebase_item_id for target in recommended_targets] == ["filing-dup", "filing-2"]
        assert [target.ordinal for target in recommended_targets] == [1, 3]
        assert all(target.dataset_version_id for target in recommended_targets)
        assert len(collapsed_targets) == 1
        assert collapsed_targets[0].ordinal == 2
        assert collapsed_targets[0].source_reference_json["deduped_with_ordinal"] == 1
        assert collapsed_targets[0].dataset_version_id is None
        for target in recommended_targets:
            version = db.get(DatasetVersion, target.dataset_version_id)
            assert version is not None
            assert version.row_count == 1
            assert version.source_row_count == 1
            assert version.dropped_row_count == 0
            assert version.storage_ref == target.source_artifact_key
            expected_payload = {
                "source_system": "senate_lda",
                "filing_uuid": target.sciencebase_item_id,
                "source_artifact_key": target.source_artifact_key,
                "source_reference_json": target.source_reference_json or {},
            }
            assert version.content_hash == senate_lda._stable_json_hash(expected_payload)
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "senate_lda")
            .order_by(DatasetSourceProvenance.source_artifact_key.asc())
            .all()
        )
        assert len(provenance_rows) == 2
        assert {row.source_mode for row in provenance_rows} == {"metadata_only"}
        assert {row.sciencebase_item_id for row in provenance_rows} == {"filing-dup", "filing-2"}
        for row in provenance_rows:
            assert row.source_reference_json["source_system"] == "senate_lda"
            assert row.source_reference_json["list_ref"]
            assert row.source_reference_json["document_url"] == row.source_artifact_key
    finally:
        db.close()


class _FakeWorldBankClient:
    auth_mode = "anonymous"

    def __init__(self):
        self.source_calls = []
        self.indicator_calls = []
        self.country_calls = []
        self.observation_calls = []

    def list_sources(self, *, timeout_seconds, retry_max_attempts_per_request, retry_base_backoff_seconds, retry_max_backoff_seconds, retry_respect_retry_after, rate_limiter, retry_counters):
        self.source_calls.append({"timeout_seconds": timeout_seconds})
        return [
            {
                "id": "2",
                "name": "World Development Indicators",
                "description": "Official World Bank development indicator metadata.",
                "url": "https://api.worldbank.org/v2/source/2",
            }
        ]

    def list_indicators(self, *, source_id, timeout_seconds, retry_max_attempts_per_request, retry_base_backoff_seconds, retry_max_backoff_seconds, retry_respect_retry_after, rate_limiter, retry_counters):
        self.indicator_calls.append({"source_id": source_id})
        return [
            {
                "id": "SP.POP.TOTL",
                "name": "Population, total",
                "source": {"id": source_id, "value": "World Development Indicators"},
                "sourceNote": "Total population is based on the de facto definition of population.",
                "sourceOrganization": "The World Bank",
            }
        ]

    def list_countries(self, *, countries, timeout_seconds, retry_max_attempts_per_request, retry_base_backoff_seconds, retry_max_backoff_seconds, retry_respect_retry_after, rate_limiter, retry_counters):
        self.country_calls.append({"countries": list(countries)})
        return [
            {"id": "USA", "iso2Code": "US", "name": "United States", "region": {"value": "North America"}},
            {"id": "CAN", "iso2Code": "CA", "name": "Canada", "region": {"value": "North America"}},
        ]

    def list_indicator_observations(self, *, source_id, country, indicator, date_range, per_page, timeout_seconds, retry_max_attempts_per_request, retry_base_backoff_seconds, retry_max_backoff_seconds, retry_respect_retry_after, rate_limiter, retry_counters):
        self.observation_calls.append({"source_id": source_id, "country": country, "indicator": indicator, "date_range": date_range, "per_page": per_page})
        return [
            {
                "countryiso3code": country,
                "date": "2022",
                "value": 333287557 if country == "USA" else 38929902,
                "unit": "",
                "obs_status": "",
                "decimal": 0,
                "indicator": {"id": indicator, "value": "Population, total"},
                "country": {"id": country[:2], "value": "United States" if country == "USA" else "Canada"},
            }
        ]


class _PagingWorldBankClient(_FakeWorldBankClient):
    def __init__(self):
        super().__init__()
        self.pages = [
            [{"countryiso3code": "USA", "date": "2021", "value": 332031554, "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"}, "country": {"id": "US", "value": "United States"}}],
            [{"countryiso3code": "USA", "date": "2022", "value": 333287557, "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"}, "country": {"id": "US", "value": "United States"}}],
        ]

    def list_indicator_observations(self, **kwargs):
        self.observation_calls.append(dict(kwargs))
        return self.pages.pop(0) if self.pages else []


class _EmptyWorldBankClient(_FakeWorldBankClient):
    def list_indicator_observations(self, **kwargs):
        self.observation_calls.append(dict(kwargs))
        return []


class _MalformedWorldBankClient(_FakeWorldBankClient):
    def list_indicator_observations(self, **kwargs):
        self.observation_calls.append(dict(kwargs))
        return [{"countryiso3code": "USA", "value": 123}]


class _NullValueWorldBankClient(_FakeWorldBankClient):
    def __init__(self):
        super().__init__()
        self._served = False

    def list_indicator_observations(self, **kwargs):
        self.observation_calls.append(dict(kwargs))
        if self._served:
            return []
        self._served = True
        indicator = kwargs["indicator"]
        return [
            {
                "countryiso3code": "USA",
                "date": "2021",
                "value": None,
                "indicator": {"id": indicator, "value": "Population, total"},
                "country": {"id": "US", "value": "United States"},
            },
            {
                "countryiso3code": "USA",
                "date": "2022",
                "value": 333287557,
                "indicator": {"id": indicator, "value": "Population, total"},
                "country": {"id": "US", "value": "United States"},
            },
        ]


class _AllNullWorldBankClient(_FakeWorldBankClient):
    def list_indicator_observations(
        self,
        *,
        source_id,
        country,
        indicator,
        date_range,
        per_page,
        timeout_seconds,
        retry_max_attempts_per_request,
        retry_base_backoff_seconds,
        retry_max_backoff_seconds,
        retry_respect_retry_after,
        rate_limiter,
        retry_counters,
    ):
        self.observation_calls.append(
            {
                "source_id": source_id,
                "country": country,
                "indicator": indicator,
                "date_range": date_range,
                "per_page": per_page,
            }
        )
        return [
            {
                "countryiso3code": country,
                "date": "2022",
                "value": None,
                "indicator": {"id": indicator, "value": "Population, total"},
                "country": {"id": country[:2], "value": "United States"},
            }
        ]


class _TimeoutWorldBankClient(_FakeWorldBankClient):
    def list_indicator_observations(self, **kwargs):
        self.observation_calls.append(dict(kwargs))
        raise requests.Timeout("temporary World Bank timeout")


class _PolicyBlockedWorldBankClient(_FakeWorldBankClient):
    def list_indicator_observations(self, **kwargs):
        from app.services.sciencebase_connector.contracts import FetchPolicyBlockedError

        self.observation_calls.append(dict(kwargs))
        raise FetchPolicyBlockedError("redirect_policy_violation")


def test_worldbank_connector_happy_path_reports_and_attribution(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, DatasetSourceProvenance
    from app.services import connectors_worldbank as wb

    fake = _FakeWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={
            "source_id": "2",
            "indicators": ["SP.POP.TOTL"],
            "countries": ["USA", "CAN"],
            "date_range": "2022:2022",
            "max_items": 2,
        },
        headers={"Idempotency-Key": f"worldbank-happy-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["connector_key"] == "worldbank_indicators"
    assert payload["status"] == "completed"
    assert payload["run_mode"] == "metadata_only"
    assert payload["page_count_completed"] == 2
    assert payload["fetch_policy_summary"] == {
        "mode": "official_api_only",
        "surface_policy": "metadata_only",
        "external_fetch_policy": "worldbank_indicators_official_only",
        "allowed_hosts": ["api.worldbank.org"],
    }
    assert Path(payload["report_refs"]["worldbank_summary"]).exists()
    assert fake.source_calls and fake.indicator_calls and fake.country_calls
    assert len(fake.observation_calls) == 2
    assert {call["source_id"] for call in fake.observation_calls} == {"2"}

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 2
    assert {row["status"] for row in target_rows} == {"recommended"}

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.effective_search_params_json["auth_mode"] == "anonymous"
        assert run.effective_search_params_json["base_url"] == "https://api.worldbank.org/v2"
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "worldbank_indicators")
            .all()
        )
        assert len(provenance_rows) == 2
        for row in provenance_rows:
            assert row.source_mode == "metadata_only"
            assert row.source_reference_json["license"] == "CC BY 4.0"
            assert row.source_reference_json["attribution"] == "The World Bank: World Development Indicators: Data source"
            assert row.retrieved_http_json["terms_of_use_url"] == "https://data.worldbank.org/summary-terms-of-use"
    finally:
        db.close()


def test_worldbank_connector_source_id_flows_to_observations_and_keys(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget
    from app.services import connectors_worldbank as wb

    fake = _FakeWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"source_id": "57", "indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022"},
        headers={"Idempotency-Key": f"worldbank-source-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    assert fake.indicator_calls == [{"source_id": "57"}]
    assert fake.observation_calls and fake.observation_calls[0]["source_id"] == "57"

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.stable_release_key.startswith("worldbank:57:USA:SP.POP.TOTL:")
        assert target.source_reference_json["source_id"] == "57"
        assert target.dataset_id is not None
    finally:
        db.close()


def test_worldbank_connector_pagination_continues_until_max_items(monkeypatch):
    from app.services import connectors_worldbank as wb

    fake = _PagingWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2021:2022", "max_items": 2},
        headers={"Idempotency-Key": f"worldbank-paging-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed"
    assert len(fake.observation_calls) == 2
    assert [call["per_page"] for call in fake.observation_calls] == [1000, 1000]


def test_worldbank_connector_empty_observations_fail_closed(monkeypatch):
    from app.services import connectors_worldbank as wb

    fake = _EmptyWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022"},
        headers={"Idempotency-Key": f"worldbank-empty-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["status"] == "completed_with_errors"
    assert detail_payload["failed_count"] == 1
    assert detail_payload["page_count_completed"] == 0

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 1
    assert target_rows[0]["status"] == "download_failed"
    assert target_rows[0]["last_error_class"] == "empty_result"


def test_worldbank_connector_malformed_observations_fail_closed(monkeypatch):
    from app.services import connectors_worldbank as wb

    fake = _MalformedWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022"},
        headers={"Idempotency-Key": f"worldbank-malformed-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed_with_errors"
    assert detail.json()["failed_count"] == 1

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target_rows = targets.json()["targets"]
    assert len(target_rows) == 1
    assert target_rows[0]["status"] == "download_failed"
    assert target_rows[0]["last_error_class"] == "schema_validation_failed"


def test_worldbank_connector_null_values_are_skipped_not_failed(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget
    from app.services import connectors_worldbank as wb

    fake = _NullValueWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2021:2022"},
        headers={"Idempotency-Key": f"worldbank-null-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed"

    db = SessionLocal()
    try:
        target = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .one()
        )
        assert target.status == "recommended"
        assert target.source_reference_json["observations_count"] == 1
    finally:
        db.close()


def test_worldbank_connector_all_null_page_fails_empty_after_normalization(monkeypatch):
    from app.services import connectors_worldbank as wb

    fake = _AllNullWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022"},
        headers={"Idempotency-Key": f"worldbank-all-null-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["status"] == "completed_with_errors"
    assert detail_payload["failed_count"] == 1
    assert detail_payload["page_count_completed"] == 0

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    [target] = targets.json()["targets"]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "empty_after_normalization"


def test_worldbank_connector_resume_continues_unmanifested_partial_discovery(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget
    from app.services import connectors_worldbank as wb

    fake = _FakeWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    db = SessionLocal()
    try:
        run, _created = wb.submit_worldbank_run(
            db,
            payload={"indicators": ["SP.POP.TOTL"], "countries": ["USA", "CAN"], "date_range": "2022:2022", "max_items": 2},
            idempotency_key=f"worldbank-partial-{uuid.uuid4().hex}",
        )
        partial = wb._target_from_observations(
            run=run,
            ordinal=1,
            country="USA",
            indicator="SP.POP.TOTL",
            observations=[
                {
                    "countryiso3code": "USA",
                    "date": "2022",
                    "value": 333287557,
                    "indicator_id": "SP.POP.TOTL",
                    "indicator_name": "Population, total",
                }
            ],
            source_ref={
                "source_system": "worldbank_indicators",
                "source_id": "2",
                "country": "USA",
                "indicator": "SP.POP.TOTL",
                "date_range": "2022:2022",
                "observations_count": 1,
            },
            run_mode="metadata_only",
        )
        db.add(partial)
        db.commit()
        run_id = run.connector_run_id
    finally:
        db.close()

    wb.execute_worldbank_run(run_id)

    db = SessionLocal()
    try:
        rows = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        assert [row.sciencebase_item_id for row in rows] == ["USA:SP.POP.TOTL", "CAN:SP.POP.TOTL"]
        assert {row.status for row in rows} == {"recommended"}
    finally:
        db.close()
    assert [call["country"] for call in fake.observation_calls] == ["CAN"]


def test_worldbank_connector_resume_stops_when_existing_targets_reach_max_items(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget
    from app.services import connectors_worldbank as wb

    fake = _FakeWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    db = SessionLocal()
    try:
        run, _created = wb.submit_worldbank_run(
            db,
            payload={"indicators": ["SP.POP.TOTL"], "countries": ["USA", "CAN"], "date_range": "2021:2022", "max_items": 2},
            idempotency_key=f"worldbank-max-resume-{uuid.uuid4().hex}",
        )
        partial = wb._target_from_observations(
            run=run,
            ordinal=1,
            country="USA",
            indicator="SP.POP.TOTL",
            observations=[
                {"countryiso3code": "USA", "date": "2021", "value": 332031554, "indicator_id": "SP.POP.TOTL"},
                {"countryiso3code": "USA", "date": "2022", "value": 333287557, "indicator_id": "SP.POP.TOTL"},
            ],
            source_ref={
                "source_system": "worldbank_indicators",
                "source_id": "2",
                "country": "USA",
                "indicator": "SP.POP.TOTL",
                "date_range": "2021:2022",
                "observations_count": 2,
            },
            run_mode="metadata_only",
        )
        db.add(partial)
        db.commit()
        run_id = run.connector_run_id
    finally:
        db.close()

    wb.execute_worldbank_run(run_id)

    db = SessionLocal()
    try:
        rows = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        assert len(rows) == 1
        assert rows[0].sciencebase_item_id == "USA:SP.POP.TOTL"
        assert fake.observation_calls == []
    finally:
        db.close()


def test_worldbank_connector_retryable_failures_remain_retry_eligible(monkeypatch):
    from app.services import connectors_worldbank as wb

    fake = _TimeoutWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022"},
        headers={"Idempotency-Key": f"worldbank-timeout-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "completed_with_errors"

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    target = targets.json()["targets"][0]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "transport_timeout"
    assert target["retry_eligible"] is True


def test_worldbank_connector_redirect_policy_blocks_are_policy_visible(monkeypatch):
    from app.services import connectors_worldbank as wb

    fake = _PolicyBlockedWorldBankClient()
    monkeypatch.setattr(wb, "get_worldbank_client", lambda config: fake)

    submit = client.post(
        "/api/v1/connectors/worldbank/runs",
        json={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022"},
        headers={"Idempotency-Key": f"worldbank-policy-block-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["status"] == "completed_with_errors"
    assert detail_payload["blocked_by_fetch_policy_count"] == 1
    assert detail_payload["failed_count"] == 0

    targets = client.get(f"/api/v1/connectors/runs/{run_id}/targets")
    assert targets.status_code == 200, targets.text
    [target] = targets.json()["targets"]
    assert target["status"] == "blocked_by_fetch_policy"
    assert target["last_error_class"] == "redirect_policy_violation"


def test_worldbank_connector_rejects_non_worldbank_base_url():
    from app.services import connectors_worldbank as wb

    with pytest.raises(wb.WorldBankSchemaValidationError, match="inadmissible_worldbank_base_url"):
        wb.WorldBankIndicatorsClient(base_url="https://example.test/v2")


def test_worldbank_client_redirect_policy_rejects_redirect_over_cap_and_final_host():
    from app.services import connectors_worldbank as wb
    from app.services.sciencebase_connector.contracts import FetchPolicyBlockedError

    class _Response:
        def __init__(self, *, url: str, status_code: int = 200, headers: dict[str, str] | None = None):
            self.url = url
            self.status_code = status_code
            self.headers = headers or {}
            self.history = []

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"http {self.status_code}")
                error.response = self
                raise error

        def json(self):
            return [{}, []]

    class _Session:
        def __init__(self, responses):
            self.responses = list(responses)
            self.calls = []

        def get(self, url, params=None, timeout=None, allow_redirects=True):
            self.calls.append({"url": url, "allow_redirects": allow_redirects})
            return self.responses.pop(0)

    request_kwargs = {
        "path": "/source",
        "params": {"format": "json"},
        "timeout_seconds": 30,
        "retry_max_attempts_per_request": 1,
        "retry_base_backoff_seconds": 0.0,
        "retry_max_backoff_seconds": 0.0,
        "retry_respect_retry_after": False,
        "rate_limiter": wb._RateLimiter(0),
        "retry_counters": {},
    }

    real_client = wb.WorldBankIndicatorsClient(base_url="https://api.worldbank.org/v2")
    over_cap_responses = [
        _Response(
            url=f"https://api.worldbank.org/v2/redirect-{index}",
            status_code=302,
            headers={"Location": f"/v2/redirect-{index + 1}"},
        )
        for index in range(int(wb.settings.connector_max_redirects) + 1)
    ]
    real_client.session = _Session(over_cap_responses)
    with pytest.raises(FetchPolicyBlockedError, match="redirect_policy_violation"):
        real_client._request_json(**request_kwargs)

    cross_host_session = _Session(
        [
            _Response(
                url="https://api.worldbank.org/v2/source",
                status_code=302,
                headers={"Location": "https://example.test/v2/source"},
            )
        ]
    )
    real_client.session = cross_host_session
    with pytest.raises(FetchPolicyBlockedError, match="redirect_policy_violation"):
        real_client._request_json(**request_kwargs)
    assert [call["url"] for call in cross_host_session.calls] == ["https://api.worldbank.org/v2/source"]

    real_client.session = _Session(
        [_Response(url="http://api.worldbank.org/v2/source")]
    )
    with pytest.raises(FetchPolicyBlockedError, match="redirect_policy_violation"):
        real_client._request_json(**request_kwargs)

    success_session = _Session(
        [
            _Response(
                url="https://api.worldbank.org/v2/source",
                status_code=302,
                headers={"Location": "/v2/source?page=2"},
            ),
            _Response(url="https://api.worldbank.org/v2/source?page=2"),
        ]
    )
    real_client.session = success_session
    assert real_client._request_json(**request_kwargs) == [{}, []]
    assert [call["allow_redirects"] for call in success_session.calls] == [False, False]


def _bls_payload(series_ids: list[str], *, value: str | None = "123.4", data: list[dict] | None = None) -> dict:
    series = []
    for index, series_id in enumerate(series_ids):
        rows = data if data is not None else [
            {
                "year": "2024",
                "period": f"M0{index + 1}",
                "periodName": "January" if index == 0 else "February",
                "value": value,
                "footnotes": [{"code": "P", "text": "Preliminary."}],
            }
        ]
        series.append({"seriesID": series_id, "data": rows})
    return {"status": "REQUEST_SUCCEEDED", "responseTime": 5, "message": [], "Results": [{"series": series}]}


class _FakeBlsClient:
    auth_mode = "anonymous"

    def __init__(self, payload: dict | None = None, *, error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.calls: list[dict[str, object]] = []

    def fetch_series(self, *, series_ids, start_year, end_year, rate_limiter=None, retry_counters=None, **kwargs):
        method = "GET" if len(series_ids) == 1 and start_year is None and end_year is None else "POST"
        body = None
        if method == "POST":
            body = {"seriesid": list(series_ids)}
            if start_year is not None and end_year is not None:
                body.update({"startyear": str(start_year), "endyear": str(end_year)})
        url = "https://api.bls.gov/publicAPI/v1/timeseries/data"
        if method == "GET":
            url = f"{url}/{series_ids[0]}"
        self.calls.append({"method": method, "url": url, "body": body, "kwargs": dict(kwargs)})
        if rate_limiter is not None:
            rate_limiter.wait()
        if retry_counters is not None:
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
        if self.error is not None:
            raise self.error
        return self.payload or _bls_payload(list(series_ids))


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://api.bls.gov/publicAPI/v1/timeseries/data"
    error = requests.HTTPError(f"{status_code} error")
    error.response = response
    return error


def _install_fake_bls(monkeypatch, fake: _FakeBlsClient):
    from app.services import connectors_bls as bls

    monkeypatch.setattr(bls, "get_bls_client", lambda config: fake)
    monkeypatch.setattr(bls, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    return bls


def test_bls_connector_happy_single_get_reports_and_attribution(monkeypatch):
    from app.core.config import settings
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunTarget, DatasetSourceProvenance
    from app.services import connectors_bls as bls

    fake = _FakeBlsClient()
    _install_fake_bls(monkeypatch, fake)
    assert bls.ALLOWED_HOST == "api.bls.gov"
    assert settings.bls_api_base_url.startswith("https://api.bls.gov/")
    assert "www.bls.gov" not in {bls.ALLOWED_HOST, settings.bls_api_base_url}

    submit = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"]},
        headers={"Idempotency-Key": f"bls-happy-get-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["connector_key"] == "bls_v1"
    assert payload["status"] == "completed"
    assert payload["run_mode"] == "metadata_only"
    assert payload["fetch_policy_summary"] == {
        "mode": "official_api_only",
        "surface_policy": "metadata_only",
        "external_fetch_policy": "bls_v1_official_only",
        "allowed_hosts": ["api.bls.gov"],
    }
    assert fake.calls[0]["method"] == "GET"
    assert fake.calls[0]["url"].endswith("/LAUCN040010000000005")

    summary = json.loads(Path(payload["report_refs"]["bls_summary"]).read_text(encoding="utf-8"))
    assert summary["request"]["method"] == "GET"
    assert summary["rows"][0]["series_id"] == "LAUCN040010000000005"
    assert summary["terms_of_service_url"] == "https://www.bls.gov/developers/termsOfService.htm"
    assert "cannot vouch" in summary["no_vouch_disclaimer"]
    assert summary["api_access_date"] == "2026-07-08"

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run.effective_search_params_json["base_url"] == "https://api.bls.gov/publicAPI/v1/timeseries/data"
        assert run.effective_search_params_json["runtime_host"] == "api.bls.gov"
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "bls_v1")
            .all()
        )
        assert len(provenance_rows) == 1
        row = provenance_rows[0]
        assert row.source_mode == "metadata_only"
        assert row.source_reference_json["runtime_host"] == "api.bls.gov"
        assert row.retrieved_http_json["api_base_url"] == "https://api.bls.gov/publicAPI/v1/timeseries/data"
        assert row.retrieved_http_json["terms_of_service_url"] == "https://www.bls.gov/developers/termsOfService.htm"
        target = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).one()
        row_artifact_ref = target.source_reference_json["row_artifact_ref"]
        row_artifact = json.loads(Path(row_artifact_ref).read_text(encoding="utf-8"))
        assert row_artifact["rows"][0]["series_id"] == "LAUCN040010000000005"
        bls._write_selection_manifest(db, run=run, rows_by_target={})
        recovered_manifest = json.loads(Path(run.selection_manifest_ref).read_text(encoding="utf-8"))
        assert recovered_manifest["targets"][0]["rows"][0]["series_id"] == "LAUCN040010000000005"
    finally:
        db.close()


def test_bls_connector_happy_multi_post_with_years(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget

    fake = _FakeBlsClient()
    _install_fake_bls(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005", "LAUCN040010000000006"], "start_year": 2022, "end_year": 2022},
        headers={"Idempotency-Key": f"bls-happy-post-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    detail = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}").json()
    summary = json.loads(Path(detail["report_refs"]["bls_summary"]).read_text(encoding="utf-8"))

    assert fake.calls[0]["method"] == "POST"
    assert fake.calls[0]["url"] == "https://api.bls.gov/publicAPI/v1/timeseries/data"
    assert fake.calls[0]["body"] == {
        "seriesid": ["LAUCN040010000000005", "LAUCN040010000000006"],
        "startyear": "2022",
        "endyear": "2022",
    }
    assert summary["request"]["method"] == "POST"
    assert {row["series_id"] for row in summary["rows"]} == {"LAUCN040010000000005", "LAUCN040010000000006"}

    long_series_ids = [f"BLS{i:017d}" for i in range(25)]
    wide_fake = _FakeBlsClient()
    _install_fake_bls(monkeypatch, wide_fake)
    wide_submit = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": long_series_ids, "start_year": 2022, "end_year": 2022},
        headers={"Idempotency-Key": f"bls-wide-post-{uuid.uuid4().hex}"},
    )
    assert wide_submit.status_code == 202, wide_submit.text
    wide_run_id = wide_submit.json()["connector_run_id"]
    db = SessionLocal()
    try:
        target = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == wide_run_id).one()
        assert "25series-" in target.stable_release_key
        for value in (
            target.stable_release_key,
            target.stable_release_identifier,
            target.sciencebase_item_id,
            target.source_artifact_key,
            target.canonical_artifact_key,
        ):
            assert len(value) <= 255
        assert target.source_reference_json["series_ids"] == long_series_ids
    finally:
        db.close()


def test_bls_connector_rejects_26_series(monkeypatch):
    _install_fake_bls(monkeypatch, _FakeBlsClient())
    response = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": [f"SERIES{i:02d}" for i in range(26)]},
        headers={"Idempotency-Key": f"bls-too-many-series-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 422, response.text
    invalid = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005/../x"]},
        headers={"Idempotency-Key": f"bls-invalid-series-{uuid.uuid4().hex}"},
    )
    assert invalid.status_code == 422, invalid.text


def test_bls_connector_rejects_11_year_span(monkeypatch):
    _install_fake_bls(monkeypatch, _FakeBlsClient())
    response = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"], "start_year": 2010, "end_year": 2020},
        headers={"Idempotency-Key": f"bls-year-span-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 422, response.text


def test_bls_connector_rejects_budget_over_25(monkeypatch):
    _install_fake_bls(monkeypatch, _FakeBlsClient())
    response = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"], "max_requests": 26},
        headers={"Idempotency-Key": f"bls-budget-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 422, response.text


def test_bls_connector_429_fail_closed_after_budget(monkeypatch):
    fake = _FakeBlsClient(error=_http_error(429))
    _install_fake_bls(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"], "max_requests": 1, "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": f"bls-429-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "http_429"
    assert target["retry_eligible"] is True


def test_bls_connector_empty_all_null_and_malformed_fail_closed(monkeypatch):
    cases = [
        (_bls_payload(["LAUCN040010000000005"], data=[]), "empty_series"),
        (_bls_payload(["LAUCN040010000000005"], value=None), "empty_after_normalization"),
        ({"status": "REQUEST_SUCCEEDED", "Results": []}, "malformed_bls_results"),
    ]
    for payload, error_class in cases:
        fake = _FakeBlsClient(payload)
        _install_fake_bls(monkeypatch, fake)
        submit = client.post(
            "/api/v1/connectors/bls/runs",
            json={"series_ids": ["LAUCN040010000000005"]},
            headers={"Idempotency-Key": f"bls-fail-closed-{error_class}-{uuid.uuid4().hex}"},
        )
        assert submit.status_code == 202, submit.text
        target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
        assert target["status"] == "download_failed"
        assert target["last_error_class"] == error_class


def test_bls_connector_rate_limiter_and_backoff_use_monkeypatched_clock(monkeypatch):
    from app.services import connectors_bls as bls

    sleeps: list[float] = []
    clock = {"now": 10.0}
    monkeypatch.setattr(bls.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(bls.time, "sleep", lambda seconds: sleeps.append(seconds))

    limiter = bls._RateLimiter(2.0)
    limiter.wait()
    clock["now"] = 10.1
    limiter.wait()
    assert sleeps == [pytest.approx(0.4)]
    assert limiter.total_sleep_seconds == pytest.approx(0.4)

    class _Response:
        def __init__(self, status_code: int):
            self.status_code = status_code
            self.url = "https://api.bls.gov/publicAPI/v1/timeseries/data/LAUCN040010000000005"
            self.history = []
            self.headers = {}

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"http {self.status_code}")
                error.response = self
                raise error

        def json(self):
            return _bls_payload(["LAUCN040010000000005"])

    responses = [_Response(503), _Response(200)]
    real_client = bls.BlsV1Client(base_url="https://api.bls.gov/publicAPI/v1/timeseries/data")
    monkeypatch.setattr(bls, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    monkeypatch.setattr(real_client.session, "get", lambda *args, **kwargs: responses.pop(0))
    retry_counters: dict[str, object] = {}
    payload = real_client.fetch_series(
        series_ids=["LAUCN040010000000005"],
        start_year=None,
        end_year=None,
        timeout_seconds=30,
        max_redirects=3,
        max_requests_budget=2,
        retry_max_attempts_per_request=2,
        retry_base_backoff_seconds=0.25,
        retry_max_backoff_seconds=1.0,
        retry_respect_retry_after=True,
        rate_limiter=bls._RateLimiter(0),
        retry_counters=retry_counters,
    )
    assert payload["status"] == "REQUEST_SUCCEEDED"
    assert retry_counters["requests_total"] == 2
    assert retry_counters["retries_total"] == 1
    assert sleeps[-1] == pytest.approx(0.25)


def test_bls_connector_post_redirect_is_terminal(monkeypatch):
    from app.services import connectors_bls as bls
    from app.services.sciencebase_connector.contracts import FetchPolicyBlockedError

    class _RedirectResponse:
        status_code = 302
        url = "https://api.bls.gov/publicAPI/v1/timeseries/data"
        history: list[object] = []
        headers = {"Location": "https://api.bls.gov/redirected"}

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    real_client = bls.BlsV1Client(base_url="https://api.bls.gov/publicAPI/v1/timeseries/data")
    captured = {}
    monkeypatch.setattr(bls, "_resolve_host_ip", lambda hostname: "8.8.8.8")

    def _post(*args, **kwargs):
        captured["kwargs"] = kwargs
        return _RedirectResponse()

    monkeypatch.setattr(real_client.session, "post", _post)

    with pytest.raises(FetchPolicyBlockedError, match="redirect_policy_violation"):
        real_client.fetch_series(
            series_ids=["LAUCN040010000000005", "LAUCN040010000000006"],
            start_year=2022,
            end_year=2022,
            timeout_seconds=30,
            max_redirects=3,
            max_requests_budget=1,
            retry_max_attempts_per_request=1,
            retry_base_backoff_seconds=0.25,
            retry_max_backoff_seconds=1.0,
            retry_respect_retry_after=True,
            rate_limiter=bls._RateLimiter(0),
            retry_counters={},
        )
    assert captured["kwargs"]["allow_redirects"] is False


def test_bls_connector_no_key_negative_single_and_multi(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRun
    from app.services import connectors_bls as bls

    fake = _FakeBlsClient()
    _install_fake_bls(monkeypatch, fake)
    single = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"]},
        headers={"Idempotency-Key": f"bls-no-key-single-{uuid.uuid4().hex}"},
    )
    assert single.status_code == 202, single.text
    multi = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005", "LAUCN040010000000006"], "start_year": 2022, "end_year": 2022},
        headers={"Idempotency-Key": f"bls-no-key-multi-{uuid.uuid4().hex}"},
    )
    assert multi.status_code == 202, multi.text

    serialized_calls = json.dumps(fake.calls, sort_keys=True).lower()
    assert "registrationkey" not in serialized_calls
    assert fake.auth_mode == "anonymous"
    db = SessionLocal()
    try:
        for run_id in [single.json()["connector_run_id"], multi.json()["connector_run_id"]]:
            run = db.get(ConnectorRun, run_id)
            request_config = json.dumps(run.request_config_json, sort_keys=True).lower()
            assert "registrationkey" not in request_config
            assert "api_key" not in request_config
            assert "authorization" not in request_config
            assert "token" not in request_config
    finally:
        db.close()
    with pytest.raises(bls.BlsSchemaValidationError, match="inadmissible_bls_base_url"):
        bls.BlsV1Client(base_url="https://api.bls.gov/publicAPI/v1/timeseries/data?registrationkey=secret")


def test_bls_connector_unauthorized_terminal(monkeypatch):
    fake = _FakeBlsClient(error=_http_error(401))
    _install_fake_bls(monkeypatch, fake)
    submit = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"]},
        headers={"Idempotency-Key": f"bls-401-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "http_4xx"
    assert target["retry_eligible"] is False


def test_bls_connector_idempotency_conflict_and_resume(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunTarget

    class _RetryThenSuccessBlsClient(_FakeBlsClient):
        def fetch_series(self, **kwargs):
            self.attempts = int(getattr(self, "attempts", 0)) + 1
            if self.attempts == 1:
                raise requests.Timeout("temporary bls timeout")
            return super().fetch_series(**kwargs)

    fake = _RetryThenSuccessBlsClient()
    _install_fake_bls(monkeypatch, fake)
    key = f"bls-idempotency-{uuid.uuid4().hex}"
    first = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"], "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 202, first.text
    conflict = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000006"], "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409, conflict.text
    run_id = first.json()["connector_run_id"]
    first_target = client.get(f"/api/v1/connectors/runs/{run_id}/targets").json()["targets"][0]
    assert first_target["status"] == "download_failed"
    assert first_target["retry_eligible"] is True

    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text
    detail = client.get(f"/api/v1/connectors/runs/{run_id}").json()
    assert detail["status"] == "completed"
    summary = json.loads(Path(detail["report_refs"]["bls_summary"]).read_text(encoding="utf-8"))
    assert summary["rows"][0]["series_id"] == "LAUCN040010000000005"

    db = SessionLocal()
    try:
        targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
        assert len(targets) == 1
        assert targets[0].attempt_count == 2
        assert targets[0].retry_eligible is False
    finally:
        db.close()

    budget_fake = _FakeBlsClient(error=_http_error(429))
    _install_fake_bls(monkeypatch, budget_fake)
    budget_first = client.post(
        "/api/v1/connectors/bls/runs",
        json={"series_ids": ["LAUCN040010000000005"], "max_requests": 1, "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": f"bls-budget-resume-{uuid.uuid4().hex}"},
    )
    assert budget_first.status_code == 202, budget_first.text
    budget_run_id = budget_first.json()["connector_run_id"]
    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, budget_run_id)
        assert run.query_plan_json["bls_request_accounting"]["requests_total"] == 1
    finally:
        db.close()
    budget_fake.error = None
    budget_resume = client.post(f"/api/v1/connectors/runs/{budget_run_id}/resume")
    assert budget_resume.status_code == 202, budget_resume.text
    assert len(budget_fake.calls) == 1
    budget_target = client.get(f"/api/v1/connectors/runs/{budget_run_id}/targets").json()["targets"][0]
    assert budget_target["status"] == "download_failed"
    assert budget_target["last_error_class"] == "request_budget_exhausted"
    assert budget_target["retry_eligible"] is False


def test_bls_support_matrix_mirror_and_runtime_probe():
    import importlib.util

    matrix = json.loads((ROOT / "config" / "support_matrix.yaml").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    assert by_id["bls_v1_anonymous_connector_slice"]["status"] == "supported"
    assert "BLS Public Data API v1 anonymous metadata only" in matrix["boundary_note"]
    assert "operator-responsible BLS 25-queries/day compliance across runs" in matrix["boundary_note"]

    spec = importlib.util.spec_from_file_location(
        "support_matrix_runtime_contract_audit",
        ROOT / "scripts" / "support_matrix_runtime_contract_audit.py",
    )
    assert spec is not None
    assert spec.loader is not None
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    payload = audit.PROBES["bls_v1_anonymous_connector_slice"]()
    assert payload["status"] == "completed"
    assert payload["auth_mode"] == "anonymous"


# Phase 0 provenance: OECD API docs pre-commit SDMX-CSV via
# format=csvfilewithlabels and describe SDMX-CSV as a flattened table.
_OECD_SDMX_CSV = (
    "DATAFLOW,FREQ,MEASURE,ADJUSTMENT,REF_AREA,TIME_PERIOD,OBS_VALUE,UNIT_MEASURE,UNIT_MULT,OBS_STATUS,Reference area\n"
    "OECD.SDD.STES:DSD_STES@DF_CLI,M,LI,AA,USA,2023-02,100.1,IX,0,A,United States\n"
    "OECD.SDD.STES:DSD_STES@DF_CLI,M,LI,AA,USA,2023-03,,IX,0,A,United States\n"
)


class _FakeOecdSdmxClient:
    auth_mode = "anonymous"

    def __init__(self, csv_text: str = _OECD_SDMX_CSV, *, error: Exception | None = None):
        self.csv_text = csv_text
        self.error = error
        self.calls: list[dict[str, object]] = []

    def fetch_csv(
        self,
        *,
        agency: str,
        dataflow: str,
        dimension_key: str,
        start_period: str | None,
        end_period: str | None,
        last_n_observations: int | None,
        rate_limiter=None,
        retry_counters=None,
        **kwargs,
    ) -> str:
        url = f"https://sdmx.oecd.org/public/rest/data/{agency},{dataflow}/{dimension_key}"
        self.calls.append(
            {
                "agency": agency,
                "dataflow": dataflow,
                "dimension_key": dimension_key,
                "start_period": start_period,
                "end_period": end_period,
                "last_n_observations": last_n_observations,
                "url": url,
                "kwargs": dict(kwargs),
            }
        )
        if rate_limiter is not None:
            rate_limiter.wait()
        if retry_counters is not None:
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
        if self.error is not None:
            raise self.error
        return self.csv_text


def _oecd_http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H"
    error = requests.HTTPError(f"{status_code} error")
    error.response = response
    return error


def _install_fake_oecd(monkeypatch, fake: _FakeOecdSdmxClient):
    from app.services import connectors_oecd as oecd

    monkeypatch.setattr(oecd, "get_oecd_client", lambda config: fake)
    monkeypatch.setattr(oecd, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    return oecd


def test_oecd_sdmx_connector_happy_dataflow_query_reports_and_attribution(monkeypatch):
    from app.core.config import settings
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunTarget, DatasetSourceProvenance, DatasetVersion
    from app.services import connectors_oecd as oecd

    fake = _FakeOecdSdmxClient()
    _install_fake_oecd(monkeypatch, fake)
    assert oecd.ALLOWED_HOST == "sdmx.oecd.org"
    assert settings.oecd_sdmx_api_base_url == "https://sdmx.oecd.org/public/rest/data"
    assert "data-explorer.oecd.org" not in {oecd.ALLOWED_HOST, settings.oecd_sdmx_api_base_url}

    submit = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={
            "agency": "OECD.SDD.STES",
            "dataflow": "DSD_STES@DF_CLI",
            "dimension_key": ".M.LI...AA...H",
            "start_period": "2023-02",
        },
        headers={"Idempotency-Key": f"oecd-happy-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["connector_key"] == "oecd_sdmx"
    assert payload["status"] == "completed"
    assert payload["fetch_policy_summary"] == {
        "mode": "official_api_only",
        "surface_policy": "metadata_only",
        "external_fetch_policy": "oecd_sdmx_official_only",
        "allowed_hosts": ["sdmx.oecd.org"],
    }
    assert fake.calls[0]["url"].endswith("/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H")
    assert fake.calls[0]["kwargs"]["format"] == "csvfilewithlabels"
    assert "jsondata" not in json.dumps(fake.calls, sort_keys=True).lower()

    summary = json.loads(Path(payload["report_refs"]["oecd_sdmx_summary"]).read_text(encoding="utf-8"))
    assert summary["request"]["format"] == "csvfilewithlabels"
    assert summary["rows"][0]["dataflow"] == "OECD.SDD.STES:DSD_STES@DF_CLI"
    assert summary["rows"][0]["time_period"] == "2023-02"
    assert summary["rows"][0]["obs_value"] == 100.1
    assert summary["attribution"] == "Organisation for Economic Co-operation and Development SDMX API"
    assert summary["terms_url"] == "https://www.oecd.org/en/about/terms-conditions.html"
    assert "60 data downloads per hour" in summary["operator_residuals"]
    assert "VPNs or anonymized sources" in summary["operator_residuals"]
    assert "Registration in no way impacts the application of these Terms" in summary["anonymous_tier_basis"]

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run.effective_search_params_json["base_url"] == "https://sdmx.oecd.org/public/rest/data"
        assert run.effective_search_params_json["runtime_host"] == "sdmx.oecd.org"
        target = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).one()
        assert "startPeriod=2023-02" in target.sciencebase_item_url
        assert "dimensionAtObservation=AllDimensions" in target.sciencebase_item_url
        assert "format=csvfilewithlabels" in target.sciencebase_item_url
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "oecd_sdmx")
            .all()
        )
        assert len(provenance_rows) == 1
        row = provenance_rows[0]
        assert row.source_mode == "metadata_only"
        assert row.source_reference_json["runtime_host"] == "sdmx.oecd.org"
        assert row.retrieved_http_json["api_base_url"] == "https://sdmx.oecd.org/public/rest/data"
        assert row.retrieved_http_json["format"] == "csvfilewithlabels"
        assert "60 data downloads per hour" in row.retrieved_http_json["operator_residuals"]
        version = db.get(DatasetVersion, row.dataset_version_id)
        assert version.row_count == 1
        assert version.source_row_count == 2
        assert version.dropped_row_count == 1
        assert row.retrieved_http_json["source_row_count"] == 2
        assert row.retrieved_http_json["dropped_row_count"] == 1
    finally:
        db.close()


def test_oecd_sdmx_connector_rejects_budget_over_30(monkeypatch):
    _install_fake_oecd(monkeypatch, _FakeOecdSdmxClient())
    response = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"max_requests": 31},
        headers={"Idempotency-Key": f"oecd-budget-{uuid.uuid4().hex}"},
    )
    assert response.status_code == 422, response.text
    invalid_identifier = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"agency": "OECD/SDD"},
        headers={"Idempotency-Key": f"oecd-invalid-{uuid.uuid4().hex}"},
    )
    assert invalid_identifier.status_code == 422, invalid_identifier.text
    assert invalid_identifier.json()["detail"]["error_code"] == "invalid_agency"


def test_oecd_sdmx_connector_413_restricted_parameter_terminal_with_last_n(monkeypatch):
    fake = _FakeOecdSdmxClient(error=_oecd_http_error(413))
    _install_fake_oecd(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"lastNObservations": 1, "max_requests": 3, "retry_max_attempts_per_request": 4},
        headers={"Idempotency-Key": f"oecd-413-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    assert fake.calls[0]["last_n_observations"] == 1
    assert len(fake.calls) == 1
    target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "restricted_parameter_413"
    assert target["retry_eligible"] is False


def test_oecd_sdmx_connector_empty_all_null_and_malformed_fail_closed(monkeypatch):
    cases = [
        ("", "empty_dataset", {}),
        ("DATAFLOW,FREQ,TIME_PERIOD,OBS_VALUE\n", "empty_dataset", {}),
        ("DATAFLOW,FREQ,TIME_PERIOD,OBS_VALUE\nOECD.SDD.STES:DSD_STES@DF_CLI,M,2023-02,\n", "empty_after_normalization", {}),
        ("not_a_dataflow,not_time,not_value\nx,y,z\n", "schema_validation_failed", {}),
        (
            "DATAFLOW,FREQ,TIME_PERIOD,OBS_VALUE\n"
            "OECD.SDD.STES:DSD_STES@DF_CLI,M,2023-02,1\n"
            "OECD.SDD.STES:DSD_STES@DF_CLI,M,2023-03,2\n",
            "row_limit_exceeded",
            {"max_rows": 1},
        ),
    ]
    for csv_text, error_class, extra_payload in cases:
        fake = _FakeOecdSdmxClient(csv_text)
        _install_fake_oecd(monkeypatch, fake)
        submit = client.post(
            "/api/v1/connectors/oecd-sdmx/runs",
            json={"dimension_key": ".M.LI...AA...H", **extra_payload},
            headers={"Idempotency-Key": f"oecd-fail-closed-{error_class}-{uuid.uuid4().hex}"},
        )
        assert submit.status_code == 202, submit.text
        target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
        assert target["status"] == "download_failed"
        assert target["last_error_class"] == error_class


def test_oecd_sdmx_connector_rate_limiter_and_backoff_use_monkeypatched_clock(monkeypatch):
    from app.services import connectors_oecd as oecd

    sleeps: list[float] = []
    clock = {"now": 10.0}
    monkeypatch.setattr(oecd.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(oecd.time, "sleep", lambda seconds: sleeps.append(seconds))

    limiter = oecd._RateLimiter(2.0)
    limiter.wait()
    clock["now"] = 10.1
    limiter.wait()
    assert sleeps == [pytest.approx(0.4)]

    class _Response:
        def __init__(self, status_code: int, text: str = ""):
            self.status_code = status_code
            self.text = text
            self.content = text.encode("utf-8")
            self.url = "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H"
            self.history = []
            self.headers = {}

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"http {self.status_code}")
                error.response = self
                raise error

    responses = [_Response(503), _Response(200, _OECD_SDMX_CSV)]
    real_client = oecd.OecdSdmxClient(base_url="https://sdmx.oecd.org/public/rest/data")
    monkeypatch.setattr(oecd, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    monkeypatch.setattr(real_client.session, "get", lambda *args, **kwargs: responses.pop(0))
    retry_counters: dict[str, object] = {}
    payload = real_client.fetch_csv(
        agency="OECD.SDD.STES",
        dataflow="DSD_STES@DF_CLI",
        dimension_key=".M.LI...AA...H",
        start_period="2023-02",
        end_period=None,
        last_n_observations=None,
        timeout_seconds=30,
        max_redirects=3,
        max_requests_budget=2,
        retry_max_attempts_per_request=2,
        retry_base_backoff_seconds=0.25,
        retry_max_backoff_seconds=1.0,
        retry_respect_retry_after=True,
        rate_limiter=oecd._RateLimiter(0),
        retry_counters=retry_counters,
        format="csvfilewithlabels",
    )
    assert "OBS_VALUE" in payload
    assert retry_counters["requests_total"] == 2
    assert retry_counters["retries_total"] == 1
    assert sleeps[-1] == pytest.approx(0.25)


def test_oecd_sdmx_connector_get_redirect_cap_and_final_host(monkeypatch):
    from app.services import connectors_oecd as oecd
    from app.services.sciencebase_connector.contracts import FetchPolicyBlockedError

    class _ManualRedirectResponse:
        def __init__(self, status_code: int, *, url: str, text: str = "", headers: dict[str, str] | None = None, content: bytes | None = None):
            self.status_code = status_code
            self.url = url
            self.text = text
            self.content = content if content is not None else text.encode("utf-8")
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"http {self.status_code}")
                error.response = self
                raise error

    real_client = oecd.OecdSdmxClient(base_url="https://sdmx.oecd.org/public/rest/data")
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(oecd, "_resolve_host_ip", lambda hostname: "8.8.8.8")

    def _get(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return _ManualRedirectResponse(
            302,
            url="https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H",
            headers={"Location": "https://example.test/outside.csv"},
        )

    monkeypatch.setattr(real_client.session, "get", _get)
    with pytest.raises(FetchPolicyBlockedError, match="host_not_allowed"):
        real_client.fetch_csv(
            agency="OECD.SDD.STES",
            dataflow="DSD_STES@DF_CLI",
            dimension_key=".M.LI...AA...H",
            start_period=None,
            end_period=None,
            last_n_observations=None,
            timeout_seconds=30,
            max_redirects=3,
            max_requests_budget=1,
            retry_max_attempts_per_request=1,
            retry_base_backoff_seconds=0.25,
            retry_max_backoff_seconds=1.0,
            retry_respect_retry_after=True,
            rate_limiter=oecd._RateLimiter(0),
            retry_counters={},
            format="csvfilewithlabels",
        )
    assert len(calls) == 1
    assert calls[0]["kwargs"]["allow_redirects"] is False

    monkeypatch.setattr(
        real_client.session,
        "get",
        lambda *args, **kwargs: _ManualRedirectResponse(
            200,
            url="https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H",
            text="DATAFLOW,TIME_PERIOD,OBS_VALUE\nOECD.SDD.STES:DSD_STES@DF_CLI,2023-02,1\n",
            content=b"x" * 128,
        ),
    )
    with pytest.raises(oecd.OecdSdmxSchemaValidationError, match="response_too_large"):
        real_client.fetch_csv(
            agency="OECD.SDD.STES",
            dataflow="DSD_STES@DF_CLI",
            dimension_key=".M.LI...AA...H",
            start_period=None,
            end_period=None,
            last_n_observations=None,
            timeout_seconds=30,
            max_redirects=3,
            max_requests_budget=1,
            retry_max_attempts_per_request=1,
            retry_base_backoff_seconds=0.25,
            retry_max_backoff_seconds=1.0,
            retry_respect_retry_after=True,
            rate_limiter=oecd._RateLimiter(0),
            retry_counters={"max_response_bytes": 16},
            format="csvfilewithlabels",
        )

    monkeypatch.setattr(
        real_client.session,
        "get",
        lambda *args, **kwargs: _ManualRedirectResponse(
            302,
            url="https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H",
            headers={"Location": "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI/.M.LI...AA...H"},
        ),
    )
    with pytest.raises(FetchPolicyBlockedError, match="redirect_policy_violation"):
        real_client.fetch_csv(
            agency="OECD.SDD.STES",
            dataflow="DSD_STES@DF_CLI",
            dimension_key=".M.LI...AA...H",
            start_period=None,
            end_period=None,
            last_n_observations=None,
            timeout_seconds=30,
            max_redirects=0,
            max_requests_budget=1,
            retry_max_attempts_per_request=1,
            retry_base_backoff_seconds=0.25,
            retry_max_backoff_seconds=1.0,
            retry_respect_retry_after=True,
            rate_limiter=oecd._RateLimiter(0),
            retry_counters={},
            format="csvfilewithlabels",
        )


def test_oecd_sdmx_connector_unauthorized_terminal(monkeypatch):
    fake = _FakeOecdSdmxClient(error=_oecd_http_error(401))
    _install_fake_oecd(monkeypatch, fake)
    submit = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"dimension_key": ".M.LI...AA...H"},
        headers={"Idempotency-Key": f"oecd-401-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "http_4xx"
    assert target["retry_eligible"] is False


def test_oecd_sdmx_connector_idempotency_conflict_and_resume(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget

    class _RetryThenSuccessOecdClient(_FakeOecdSdmxClient):
        def fetch_csv(self, **kwargs):
            self.attempts = int(getattr(self, "attempts", 0)) + 1
            if self.attempts == 1:
                raise requests.Timeout("temporary oecd timeout")
            return super().fetch_csv(**kwargs)

    fake = _RetryThenSuccessOecdClient()
    _install_fake_oecd(monkeypatch, fake)
    key = f"oecd-idempotency-{uuid.uuid4().hex}"
    first = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"dimension_key": ".M.LI...AA...H", "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 202, first.text
    conflict = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"dimension_key": ".Q.LI...AA...H", "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409, conflict.text
    run_id = first.json()["connector_run_id"]
    first_target = client.get(f"/api/v1/connectors/runs/{run_id}/targets").json()["targets"][0]
    assert first_target["status"] == "download_failed"
    assert first_target["retry_eligible"] is True

    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text
    detail = client.get(f"/api/v1/connectors/runs/{run_id}").json()
    assert detail["status"] == "completed"
    summary = json.loads(Path(detail["report_refs"]["oecd_sdmx_summary"]).read_text(encoding="utf-8"))
    assert summary["rows"][0]["time_period"] == "2023-02"

    second = client.post(
        "/api/v1/connectors/oecd-sdmx/runs",
        json={"dimension_key": ".M.LI...AA...H", "max_requests": 2},
        headers={"Idempotency-Key": f"oecd-identity-budget-{uuid.uuid4().hex}"},
    )
    assert second.status_code == 202, second.text
    second_run_id = second.json()["connector_run_id"]
    second_detail = client.get(f"/api/v1/connectors/runs/{second_run_id}").json()
    assert second_detail["status"] == "completed"

    db = SessionLocal()
    try:
        targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
        assert len(targets) == 1
        assert targets[0].attempt_count == 2
        assert targets[0].retry_eligible is False
        second_targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == second_run_id).all()
        assert len(second_targets) == 1
        assert second_targets[0].stable_release_key == targets[0].stable_release_key
        assert second_targets[0].dataset_id == targets[0].dataset_id
    finally:
        db.close()


def test_oecd_sdmx_connector_rejects_non_oecd_base_url():
    from app.services import connectors_oecd as oecd

    with pytest.raises(oecd.OecdSdmxSchemaValidationError, match="inadmissible_oecd_sdmx_base_url"):
        oecd.OecdSdmxClient(base_url="https://example.test/public/rest/data")
    with pytest.raises(oecd.OecdSdmxSchemaValidationError, match="inadmissible_oecd_sdmx_base_url"):
        oecd.OecdSdmxClient(base_url="https://sdmx.oecd.org/public/rest/data?format=jsondata")


def test_oecd_sdmx_support_matrix_mirror_and_runtime_probe():
    import importlib.util

    matrix = json.loads((ROOT / "config" / "support_matrix.yaml").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    assert by_id["oecd_sdmx_anonymous_connector_slice"]["status"] == "supported"
    assert "OECD SDMX anonymous metadata only" in matrix["boundary_note"]
    assert "operator-responsible OECD 60 data downloads/hour compliance across runs" in matrix["boundary_note"]
    assert "VPNs or anonymized sources" in matrix["boundary_note"]

    spec = importlib.util.spec_from_file_location(
        "support_matrix_runtime_contract_audit",
        ROOT / "scripts" / "support_matrix_runtime_contract_audit.py",
    )
    assert spec is not None
    assert spec.loader is not None
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    payload = audit.PROBES["oecd_sdmx_anonymous_connector_slice"]()
    assert payload["status"] == "completed"
    assert payload["auth_mode"] == "anonymous"


# CFTC Phase 0 pinned the current legacy long-form comma-delimited variable order:
# Market_and_Exchange_Names, As_of_Date_In_Form_YYMMDD, As_of_Date_Form_YYYY-MM-DD,
# CFTC_Contract_Market_Code, CFTC_Market_Code, CFTC_Region_Code, CFTC_Commodity_Code.
_CFTC_COT_LEGACY_HEADER = ",".join(
    [
        "Market_and_Exchange_Names",
        "As_of_Date_In_Form_YYMMDD",
        "As_of_Date_Form_YYYY-MM-DD",
        "CFTC_Contract_Market_Code",
        "CFTC_Market_Code",
        "CFTC_Region_Code",
        "CFTC_Commodity_Code",
        "Open_Interest_All",
        "Noncommercial_Positions_Long_All",
        "Noncommercial_Positions_Short_All",
        "Noncommercial_Positions_Spreading_All",
        "Commercial_Positions_Long_All",
        "Commercial_Positions_Short_All",
        "Total_Reportable_Positions_Long_All",
        "Total_Reportable_Positions_Short_All",
        "Nonreportable_Positions_Long_All",
        "Nonreportable_Positions_Short_All",
    ]
)


def _cftc_cot_csv(rows: list[str], *, header: bool = True) -> bytes:
    lines = []
    if header:
        lines.append(_CFTC_COT_LEGACY_HEADER)
    lines.extend(rows)
    return ("\n".join(lines) + "\n").encode("utf-8")


_CFTC_COT_WHEAT_ROW = (
    "CHICAGO WHEAT SRW - CHICAGO BOARD OF TRADE,240625,2024-06-25,001602,001,0,001,"
    "400000,100000,50000,25000,150000,175000,275000,250000,125000,150000"
)
_CFTC_COT_CORN_ROW = (
    "CORN - CHICAGO BOARD OF TRADE,240625,2024-06-25,002602,002,0,002,"
    "500000,120000,70000,30000,180000,190000,330000,290000,170000,210000"
)


class _FakeCftcCotClient:
    auth_mode = "anonymous"

    def __init__(self, content: bytes | None = None, *, final_url: str | None = None):
        self.content = content if content is not None else _cftc_cot_csv([_CFTC_COT_WHEAT_ROW, _CFTC_COT_CORN_ROW])
        self.final_url = final_url
        self.calls: list[dict[str, object]] = []

    def download_artifact(
        self,
        *,
        url,
        timeout_seconds,
        max_redirects,
        headers=None,
        rate_limiter=None,
        retry_counters=None,
        **_kwargs,
    ):
        from app.services.sciencebase_connector.contracts import DownloadResult

        self.calls.append({"url": url, "timeout_seconds": timeout_seconds, "max_redirects": max_redirects})
        if rate_limiter is not None:
            rate_limiter.wait()
        if retry_counters is not None:
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
        return DownloadResult(
            content=self.content,
            status_code=200,
            final_url=self.final_url or url,
            redirect_count=0,
            etag="cftc-etag",
            last_modified="Mon, 01 Jul 2024 00:00:00 GMT",
            content_type="text/plain; charset=utf-8",
            sha256=hashlib.sha256(self.content).hexdigest(),
            headers={},
            resolved_ip="8.8.8.8",
        )


def _install_fake_cftc(monkeypatch, fake: _FakeCftcCotClient):
    from app.services import connectors_cftc_cot as cftc

    monkeypatch.setattr(cftc, "get_cftc_cot_client", lambda config: fake)
    monkeypatch.setattr(cftc, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    return cftc


def test_cftc_cot_connector_happy_path_reports_rows_and_attribution(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import DatasetSourceProvenance

    fake = _FakeCftcCotClient()
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only", "max_rows": 2},
        headers={"Idempotency-Key": f"cftc-cot-happy-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["connector_key"] == "cftc_cot"
    assert payload["status"] == "completed"
    assert payload["run_mode"] == "metadata_only"
    assert payload["fetch_policy_summary"] == {
        "mode": "official_file_only",
        "surface_policy": "public_report_rows",
        "external_fetch_policy": "cftc_cot_official_only",
        "allowed_hosts": ["www.cftc.gov"],
    }
    assert payload["report_refs"]["cftc_cot_summary"]
    assert fake.calls[0]["url"] == "https://www.cftc.gov/dea/newcot/deafut.txt"

    summary = json.loads(Path(payload["report_refs"]["cftc_cot_summary"]).read_text(encoding="utf-8"))
    assert summary["report_variant"] == "legacy_futures_only"
    assert [row["commodity_code"] for row in summary["rows"]] == ["001", "002"]
    assert summary["rows"][0]["market_and_exchange"] == "CHICAGO WHEAT SRW - CHICAGO BOARD OF TRADE"

    db = SessionLocal()
    try:
        provenance_rows = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run_id)
            .filter(DatasetSourceProvenance.source_system == "cftc_cot")
            .all()
        )
        assert len(provenance_rows) == 1
        assert provenance_rows[0].source_mode == "metadata_only"
        assert provenance_rows[0].source_reference_json["phase0_format_pin"] == "official_cftc_doc_pages"
        assert provenance_rows[0].retrieved_http_json["api_base_url"] == "https://www.cftc.gov/dea/newcot"
    finally:
        db.close()


def test_cftc_cot_connector_variant_selection_uses_combined_file(monkeypatch):
    fake = _FakeCftcCotClient()
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_combined", "max_rows": 1},
        headers={"Idempotency-Key": f"cftc-cot-combined-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    assert fake.calls[0]["url"] == "https://www.cftc.gov/dea/newcot/deacom.txt"


def test_cftc_cot_connector_accepts_headerless_current_report_rows(monkeypatch):
    headerless = _cftc_cot_csv([_CFTC_COT_WHEAT_ROW + ",ignored_extra_column"], header=False)
    fake = _FakeCftcCotClient(headerless)
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only", "max_rows": 1},
        headers={"Idempotency-Key": f"cftc-cot-headerless-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text

    detail = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "completed"
    summary = json.loads(Path(payload["report_refs"]["cftc_cot_summary"]).read_text(encoding="utf-8"))
    assert summary["rows"][0]["commodity_code"] == "001"
    assert summary["rows"][0]["open_interest_all"] == 400000


def test_cftc_cot_connector_unrecognized_format_fails_closed(monkeypatch):
    fake = _FakeCftcCotClient(b"Unexpected,Header\nx,y\n")
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only"},
        headers={"Idempotency-Key": f"cftc-cot-malformed-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text

    targets = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets")
    assert targets.status_code == 200, targets.text
    target = targets.json()["targets"][0]
    assert target["status"] == "download_failed"
    assert target["last_error_class"] == "unrecognized_cot_header"


def test_cftc_cot_connector_empty_and_all_null_reports_fail_closed(monkeypatch):
    fake_empty = _FakeCftcCotClient(_cftc_cot_csv([]))
    _install_fake_cftc(monkeypatch, fake_empty)
    empty = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only"},
        headers={"Idempotency-Key": f"cftc-cot-empty-{uuid.uuid4().hex}"},
    )
    assert empty.status_code == 202, empty.text
    empty_target = client.get(f"/api/v1/connectors/runs/{empty.json()['connector_run_id']}/targets").json()["targets"][0]
    assert empty_target["last_error_class"] == "empty_report"

    null_row = "EMPTY MARKET - TEST EXCHANGE,240625,2024-06-25,009999,009,0,009,,,,,,,,,,"
    fake_null = _FakeCftcCotClient(_cftc_cot_csv([null_row]))
    _install_fake_cftc(monkeypatch, fake_null)
    nulls = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only"},
        headers={"Idempotency-Key": f"cftc-cot-null-{uuid.uuid4().hex}"},
    )
    assert nulls.status_code == 202, nulls.text
    null_target = client.get(f"/api/v1/connectors/runs/{nulls.json()['connector_run_id']}/targets").json()["targets"][0]
    assert null_target["last_error_class"] == "empty_after_normalization"


def test_cftc_cot_connector_row_cap_and_byte_cap(monkeypatch):
    fake = _FakeCftcCotClient()
    _install_fake_cftc(monkeypatch, fake)

    capped = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only", "max_rows": 1},
        headers={"Idempotency-Key": f"cftc-cot-row-cap-{uuid.uuid4().hex}"},
    )
    assert capped.status_code == 202, capped.text
    detail = client.get(f"/api/v1/connectors/runs/{capped.json()['connector_run_id']}").json()
    summary = json.loads(Path(detail["report_refs"]["cftc_cot_summary"]).read_text(encoding="utf-8"))
    assert len(summary["rows"]) == 1

    too_small = _FakeCftcCotClient()
    _install_fake_cftc(monkeypatch, too_small)
    blocked = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only", "max_file_bytes": 10},
        headers={"Idempotency-Key": f"cftc-cot-byte-cap-{uuid.uuid4().hex}"},
    )
    assert blocked.status_code == 202, blocked.text
    target = client.get(f"/api/v1/connectors/runs/{blocked.json()['connector_run_id']}/targets").json()["targets"][0]
    assert target["status"] == "blocked_by_fetch_policy"
    assert target["last_error_class"] == "file_size_limit_exceeded"


def test_cftc_cot_client_enforces_byte_cap_while_streaming(monkeypatch):
    from app.services import connectors_cftc_cot as cftc
    from app.services.sciencebase_connector.contracts import FetchPolicyBlockedError

    class _StreamingResponse:
        status_code = 200
        url = "https://www.cftc.gov/dea/newcot/deafut.txt"
        history: list[object] = []
        headers: dict[str, str] = {}

        def __init__(self):
            self.yielded = 0

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            for chunk in [b"12345", b"67890", b"overflow"]:
                self.yielded += 1
                yield chunk

    response = _StreamingResponse()
    real_client = cftc.CftcCotClient(base_url="https://www.cftc.gov/dea/newcot")
    monkeypatch.setattr(real_client.session, "get", lambda *args, **kwargs: response)

    with pytest.raises(FetchPolicyBlockedError, match="file_size_limit_exceeded"):
        real_client.download_artifact(
            url="https://www.cftc.gov/dea/newcot/deafut.txt",
            timeout_seconds=30,
            max_redirects=3,
            max_file_bytes=9,
        )

    assert response.yielded == 2


def test_cftc_cot_connector_rate_limiter_and_backoff_use_monkeypatched_clock(monkeypatch):
    from app.services import connectors_cftc_cot as cftc

    sleeps: list[float] = []
    clock = {"now": 10.0}
    monkeypatch.setattr(cftc.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(cftc.time, "sleep", lambda seconds: sleeps.append(seconds))

    limiter = cftc._RateLimiter(2.0)
    limiter.wait()
    clock["now"] = 10.1
    limiter.wait()

    assert sleeps == [pytest.approx(0.4)]
    assert limiter.total_sleep_seconds == pytest.approx(0.4)

    class _Response:
        def __init__(self, status_code: int, content: bytes):
            self.status_code = status_code
            self._content = content
            self.url = "https://www.cftc.gov/dea/newcot/deafut.txt"
            self.history = []
            self.headers = {}

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.HTTPError(f"http {self.status_code}")
                error.response = self
                raise error

        def iter_content(self, chunk_size):
            yield self._content

    responses = [_Response(503, b""), _Response(200, _cftc_cot_csv([_CFTC_COT_WHEAT_ROW]))]
    real_client = cftc.CftcCotClient(base_url="https://www.cftc.gov/dea/newcot")
    monkeypatch.setattr(cftc, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    monkeypatch.setattr(real_client.session, "get", lambda *args, **kwargs: responses.pop(0))
    retry_counters: dict[str, object] = {}

    result = real_client.download_artifact(
        url="https://www.cftc.gov/dea/newcot/deafut.txt",
        timeout_seconds=30,
        max_redirects=3,
        retry_max_attempts_per_request=2,
        retry_base_backoff_seconds=0.25,
        retry_max_backoff_seconds=1.0,
        retry_counters=retry_counters,
    )

    assert result.status_code == 200
    assert retry_counters["requests_total"] == 2
    assert retry_counters["retries_total"] == 1
    assert sleeps[-1] == pytest.approx(0.25)


def test_cftc_cot_connector_idempotency_conflict_and_post_enum_cross_check(monkeypatch):
    fake = _FakeCftcCotClient()
    _install_fake_cftc(monkeypatch, fake)

    key = f"cftc-cot-idempotency-{uuid.uuid4().hex}"
    first = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only", "max_rows": 1},
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 202, first.text
    conflict = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_combined", "max_rows": 1},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409, conflict.text

    invalid = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "historical_legacy_zip"},
        headers={"Idempotency-Key": f"cftc-cot-invalid-{uuid.uuid4().hex}"},
    )
    assert invalid.status_code == 422, invalid.text


def test_cftc_cot_connector_resume_retries_existing_retryable_failed_target(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import ConnectorRunTarget

    class _RetryThenSuccessCftcCotClient(_FakeCftcCotClient):
        def download_artifact(self, **kwargs):
            self.attempts = int(getattr(self, "attempts", 0)) + 1
            if self.attempts == 1:
                self.calls.append({"url": kwargs["url"], "timeout_seconds": kwargs["timeout_seconds"], "max_redirects": kwargs["max_redirects"]})
                raise requests.Timeout("temporary cftc timeout")
            return super().download_artifact(**kwargs)

    fake = _RetryThenSuccessCftcCotClient(_cftc_cot_csv([_CFTC_COT_WHEAT_ROW]))
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only", "retry_max_attempts_per_request": 1},
        headers={"Idempotency-Key": f"cftc-cot-resume-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    first_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert first_detail.status_code == 200, first_detail.text
    assert first_detail.json()["status"] == "completed_with_errors"
    first_target = client.get(f"/api/v1/connectors/runs/{run_id}/targets").json()["targets"][0]
    assert first_target["status"] == "download_failed"
    assert first_target["retry_eligible"] is True

    resume = client.post(f"/api/v1/connectors/runs/{run_id}/resume")
    assert resume.status_code == 202, resume.text

    second_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
    assert second_detail.status_code == 200, second_detail.text
    second_payload = second_detail.json()
    assert second_payload["status"] == "completed"
    summary = json.loads(Path(second_payload["report_refs"]["cftc_cot_summary"]).read_text(encoding="utf-8"))
    assert summary["rows"][0]["commodity_code"] == "001"

    db = SessionLocal()
    try:
        targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
        assert len(targets) == 1
        assert targets[0].attempt_count == 2
        assert targets[0].retry_eligible is False
    finally:
        db.close()


def test_cftc_cot_connector_pre_target_cancel_finalizes_without_target(monkeypatch):
    from app.api import router
    from app.db.session import SessionLocal
    from app.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget
    from app.services import connectors_cftc_cot as cftc
    from app.services.connectors_sciencebase import request_cancel_run

    fake = _FakeCftcCotClient()
    monkeypatch.setattr(router, "_enqueue_connector_run", lambda *args, **kwargs: None)
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only"},
        headers={"Idempotency-Key": f"cftc-cot-cancel-before-target-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    run_id = submit.json()["connector_run_id"]

    db = SessionLocal()
    try:
        request_cancel_run(db, run_id)
    finally:
        db.close()

    cftc.execute_cftc_cot_run(run_id)

    db = SessionLocal()
    try:
        run = db.get(ConnectorRun, run_id)
        assert run is not None
        assert run.status == "cancelled"
        assert run.cancelled_at is not None
        assert run.error_summary == "cancelled_by_operator"
        assert run.execution_lease_owner is None
        assert run.execution_lease_token is None
        assert db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).count() == 0
        event_types = {
            row.event_type
            for row in db.query(ConnectorRunEvent).filter(ConnectorRunEvent.connector_run_id == run_id).all()
        }
        assert "run_cancel_requested" in event_types
        assert "run_cancelling" in event_types
        assert "run_finalized" in event_types
    finally:
        db.close()
    assert fake.calls == []


def test_cftc_cot_connector_precheck_rejects_non_cftc_and_blocked_ip(monkeypatch):
    from app.services import connectors_cftc_cot as cftc

    monkeypatch.setattr(cftc, "_resolve_host_ip", lambda hostname: "8.8.8.8")
    _ip, reason = cftc._precheck_cftc_download_url("https://example.test/deafut.txt", cftc._cftc_fetch_policy({}))
    assert reason == "host_not_allowed"

    monkeypatch.setattr(cftc, "_resolve_host_ip", lambda hostname: "127.0.0.1")
    ip, reason = cftc._precheck_cftc_download_url(
        "https://www.cftc.gov/dea/newcot/deafut.txt",
        cftc._cftc_fetch_policy({}),
    )
    assert ip == "127.0.0.1"
    assert reason == "resolved_private_or_blocked_ip"


def test_cftc_cot_connector_redirect_posture_rechecks_final_url(monkeypatch):
    fake = _FakeCftcCotClient(final_url="https://example.test/deafut.txt")
    _install_fake_cftc(monkeypatch, fake)

    submit = client.post(
        "/api/v1/connectors/cftc-cot/runs",
        json={"report_variant": "legacy_futures_only"},
        headers={"Idempotency-Key": f"cftc-cot-redirect-{uuid.uuid4().hex}"},
    )
    assert submit.status_code == 202, submit.text
    target = client.get(f"/api/v1/connectors/runs/{submit.json()['connector_run_id']}/targets").json()["targets"][0]
    assert target["status"] == "blocked_by_fetch_policy"
    assert target["last_error_class"] == "host_not_allowed"


def test_cftc_cot_connector_rejects_non_cftc_base_url():
    from app.services import connectors_cftc_cot as cftc

    with pytest.raises(cftc.CftcCotSchemaValidationError, match="inadmissible_cftc_cot_base_url"):
        cftc.CftcCotClient(base_url="https://example.test/dea/newcot")


def test_cftc_cot_support_matrix_mirror_and_runtime_probe():
    import importlib.util

    matrix = json.loads((ROOT / "config" / "support_matrix.yaml").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    assert by_id["cftc_cot_anonymous_connector_slice"]["status"] == "supported"
    assert "CFTC COT anonymous public report rows only" in matrix["boundary_note"]

    spec = importlib.util.spec_from_file_location(
        "support_matrix_runtime_contract_audit",
        ROOT / "scripts" / "support_matrix_runtime_contract_audit.py",
    )
    assert spec is not None
    assert spec.loader is not None
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    payload = audit.PROBES["cftc_cot_anonymous_connector_slice"]()
    assert payload["status"] == "completed"
    assert payload["auth_mode"] == "anonymous"
