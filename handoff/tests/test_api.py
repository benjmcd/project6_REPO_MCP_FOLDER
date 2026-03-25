import io
import importlib
import json
import os
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
import requests
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

DEFAULT_TEST_DB_PATH = ROOT / 'test_method_aware.db'
DEFAULT_DATABASE_URL = 'sqlite:///./test_method_aware.db'
TEST_DATABASE_URL = os.environ.get('DATABASE_URL') or DEFAULT_DATABASE_URL


def _sqlite_file_path(database_url: str) -> Path | None:
    if not str(database_url).startswith('sqlite:///'):
        return None
    raw = str(database_url)[10:]
    if raw == ':memory:':
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


TEST_DB_PATH = _sqlite_file_path(TEST_DATABASE_URL) or DEFAULT_TEST_DB_PATH
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
TEST_STORAGE_DIR = Path(os.environ.get('STORAGE_DIR') or str(BACKEND / 'app' / 'storage_test_runtime'))
NRC_FIXTURE_DIR = ROOT / 'tests' / 'fixtures' / 'nrc_aps_docs' / 'v1'
if TEST_STORAGE_DIR.exists():
    shutil.rmtree(TEST_STORAGE_DIR)

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
from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402

SQLALCHEMY_DATABASE_URL = TEST_DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})
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


def _read_nrc_fixture_bytes(name: str) -> bytes:
    return (NRC_FIXTURE_DIR / name).read_bytes()


def _nrc_manifest_entry(fixture_id: str) -> dict[str, object]:
    payload = json.loads((NRC_FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in payload.get("entries") or []:
        if str(entry.get("fixture_id") or "") == fixture_id:
            return dict(entry)
    raise KeyError(fixture_id)


def test_vertical_slice_csv_upload_profile_transform_analyze():
    csv_bytes = (
        b"date,revenue,traffic,temperature\n"
        b"2024-01-01,100,200,50\n"
        b"2024-01-02,102,210,51\n"
        b"2024-01-03,300,230,49\n"
        b"2024-01-04,110,220,52\n"
        b"2024-01-05,108,218,48\n"
        b"2024-01-06,112,225,47\n"
    )
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
    assert analysis['artifacts']
    assert analysis['caveats']


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
    assert payload['time_column'] == 'Year'
    assert payload['row_count'] == 3


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
    def search_page(self, *, q, filters, offset, page_size, sort, order):
        if offset > 0:
            items = []
        else:
            items = [{"id": "item-1"}]
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
            "title": "Item",
            "identifiers": [{"type": "DOI", "value": "10.1234/example"}],
            "files": [
                {"name": "good.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/good.csv"},
                {"name": "bad.csv", "downloadUri": "http://www.sciencebase.gov/catalog/file/bad.csv"},
            ],
            "webLinks": [
                {"title": "external", "uri": "https://example.com/external.csv"},
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
                "sha256": "fake_sha_surface",
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

    monkeypatch.setattr(sb, "get_sciencebase_adapter", lambda config: _FakeSurfaceAdapter())

    response = client.post(
        "/api/v1/connectors/sciencebase-public/runs",
        json={
            "q": "MCS",
            "run_mode": "one_shot_import",
            "surface_policy": "files_only",
            "allowed_extensions": [".csv"],
        },
        headers={"Idempotency-Key": "surface-policy-run"},
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
        headers={"Idempotency-Key": "dedupe-run"},
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
        winner_row = (
            db.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id, ConnectorRunTarget.status != "collapsed_duplicate")
            .first()
        )
        assert winner_row is not None
        alias_count = db.query(ConnectorArtifactAlias).filter(ConnectorArtifactAlias.connector_run_target_id == winner_row.connector_run_target_id).count()
        assert alias_count >= 1
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


def test_nrc_real_born_digital_content_search_and_evidence_bundle(monkeypatch):
    from app.services import connectors_nrc_adams as nrc

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
    assert assembled_payload["schema_id"] == "aps.evidence_bundle.v1"
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
    assert assembled_payload["schema_id"] == "aps.evidence_bundle.v1"
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
    assert bundle_payload["schema_id"] == "aps.evidence_bundle.v1"

    packed = client.post(
        "/api/v1/connectors/nrc-adams-aps/citation-packs",
        json={"bundle_id": bundle_payload["bundle_id"], "persist_pack": True, "limit": 1, "offset": 0},
    )
    assert packed.status_code == 200, packed.text
    packed_payload = packed.json()
    assert packed_payload["schema_id"] == "aps.evidence_citation_pack.v1"
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
    assert packed_payload["schema_id"] == "aps.evidence_citation_pack.v1"

    reported = client.post(
        "/api/v1/connectors/nrc-adams-aps/evidence-reports",
        json={"citation_pack_id": packed_payload["citation_pack_id"], "persist_report": True, "limit": 1, "offset": 0},
    )
    assert reported.status_code == 200, reported.text
    report_payload = reported.json()
    assert report_payload["schema_id"] == "aps.evidence_report.v1"
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


def test_senate_lda_connector_happy_path_reports_and_detail_hydration(monkeypatch):
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

