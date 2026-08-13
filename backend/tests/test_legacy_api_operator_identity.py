"""Operator-identity gating proof for legacy API (router.py) routes.

Proves, at the HTTP route layer, that:
1. proxy mode + trusted proxy + missing identity header → auth-gate error with error_code
2. proxy mode + trusted proxy + valid identity headers → not auth-gate rejected
3. local default mode (auth_owner=none) → behaviour unchanged (inert seam, no auth rejection)

All 48 routes are covered via parametrize.  Auth check fires before any service lookup,
so the auth-gate 401/409 proves gating independent of whether the resource exists.

POST routes with JSON bodies: the gate fires as the FIRST statement, before Pydantic
validation, so 401/409 with an auth error_code confirms gating even with an empty body.

Multipart upload routes: the pre-body middleware intercepts BEFORE the handler body is
parsed, so a multipart-less POST still returns the auth error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402
from main import app  # noqa: E402

_API = "/api/v1"
_IDENTITY_HEADER = "x-forwarded-user"
_GROUPS_HEADER = "x-forwarded-groups"
_ROLES_HEADER = "x-forwarded-roles"
_IDENTITY_CANARY = "legacy-api-test-operator@example.invalid"
_GROUPS_CANARY = "legacy-api-test-workspace@example.invalid"

# Plausible dummy values for path parameters.
_DS = "dummy-dataset-id"
_DSV = "dummy-dataset-version-id"
_RUN = "dummy-analysis-run-id"
_CRUN = "dummy-connector-run-id"
_BUNDLE = "dummy-bundle-id"
_CITATION = "dummy-citation-pack-id"
_REPORT = "dummy-evidence-report-id"
_EXPORT = "dummy-evidence-report-export-id"
_PKG = "dummy-evidence-report-export-package-id"
_CPKT = "dummy-context-packet-id"
_DOSS = "dummy-context-dossier-id"
_INSIGHT = "dummy-insight-artifact-id"
_CHALLENGE = "dummy-challenge-artifact-id"
_REVIEW_PKT = "dummy-challenge-review-packet-id"

# ---------------------------------------------------------------------------
# Route inventory
# ---------------------------------------------------------------------------

_GET_ROUTES = [
    f"{_API}/datasets",
    f"{_API}/datasets/{_DS}",
    f"{_API}/datasets/{_DS}/versions/{_DSV}/annotations",
    f"{_API}/analysis-runs/{_RUN}",
    f"{_API}/connectors/egress-armings/{_CRUN}",
    f"{_API}/connectors/runs/{_CRUN}",
    f"{_API}/connectors/runs/{_CRUN}/targets",
    f"{_API}/connectors/runs/{_CRUN}/events",
    f"{_API}/connectors/runs/{_CRUN}/reports",
    f"{_API}/connectors/runs/{_CRUN}/content-units",
    f"{_API}/connectors/runs/{_CRUN}/_operator/retrieval-content-units",
    f"{_API}/connectors/nrc-adams-aps/evidence-bundles/{_BUNDLE}",
    f"{_API}/connectors/nrc-adams-aps/citation-packs/{_CITATION}",
    f"{_API}/connectors/nrc-adams-aps/evidence-reports/{_REPORT}",
    f"{_API}/connectors/nrc-adams-aps/evidence-report-exports/{_EXPORT}",
    f"{_API}/connectors/nrc-adams-aps/evidence-report-export-packages/{_PKG}",
    f"{_API}/connectors/nrc-adams-aps/context-packets/{_CPKT}",
    f"{_API}/connectors/nrc-adams-aps/context-dossiers/{_DOSS}",
    f"{_API}/connectors/nrc-adams-aps/deterministic-insight-artifacts/{_INSIGHT}",
    f"{_API}/connectors/nrc-adams-aps/deterministic-challenge-artifacts/{_CHALLENGE}",
    f"{_API}/connectors/nrc-adams-aps/deterministic-challenge-review-packets/{_REVIEW_PKT}",
]

# POST routes: (path, minimal_valid_body).
# Minimal body satisfies required fields so FastAPI body-injection succeeds and the
# gate (first statement in handler) fires.  Routes with all-optional bodies use {}.
_POST_JSON_ROUTES: list[tuple[str, dict]] = [
    (f"{_API}/datasets/{_DS}/versions/{_DSV}/profile", {}),
    (f"{_API}/datasets/{_DS}/versions/{_DSV}/transformations/recommend", {}),
    (
        f"{_API}/datasets/{_DS}/versions/{_DSV}/transformations/apply",
        {"steps": []},
    ),
    (
        f"{_API}/datasets/{_DS}/versions/{_DSV}/annotations",
        {
            "label": "x",
            "annotation_type": "event",
            "start_time": "2020-01-01T00:00:00",
            "end_time": "2020-01-02T00:00:00",
        },
    ),
    (f"{_API}/datasets/{_DS}/versions/{_DSV}/analysis/recommend", {}),
    (
        f"{_API}/analysis-runs",
        {"dataset_version_id": _DSV, "method_name": "arima"},
    ),
    (
        f"{_API}/connectors/egress-armings",
        {
            "schema_id": "project6.connector_egress_arming.v1",
            "client_request_id": "auth-gate-probe",
            "connector_key": "nrc_adams_aps",
            "campaign_id": "7fe33e0a-c0e7-4f8e-9d55-8ba77a01ce23",
            "campaign_fingerprint": "a" * 64,
            "grant_sha256": "b" * 64,
        },
    ),
    (
        f"{_API}/connectors/egress-armings/{_CRUN}/execute",
        {
            "execution_idempotency_key": "auth-gate-probe",
            "arming_fingerprint": "c" * 64,
        },
    ),
    (f"{_API}/connectors/sciencebase-public/runs", {}),
    (f"{_API}/connectors/sciencebase-mcs/runs", {}),
    (f"{_API}/connectors/nrc-adams-aps/runs", {}),
    (f"{_API}/connectors/senate-lda/runs", {}),
    (f"{_API}/connectors/worldbank/runs", {}),
    (f"{_API}/connectors/cftc-cot/runs", {}),
    (f"{_API}/connectors/bls/runs", {}),
    (f"{_API}/connectors/oecd-sdmx/runs", {}),
    (f"{_API}/connectors/nrc-adams-aps/content-search", {"query": "test"}),
    (f"{_API}/connectors/nrc-adams-aps/_operator/retrieval-content-search", {"query": "test"}),
    (f"{_API}/connectors/nrc-adams-aps/evidence-bundles", {"run_id": _CRUN}),
    (f"{_API}/connectors/nrc-adams-aps/citation-packs", {}),
    (f"{_API}/connectors/nrc-adams-aps/evidence-reports", {}),
    (f"{_API}/connectors/nrc-adams-aps/evidence-report-exports", {}),
    (f"{_API}/connectors/nrc-adams-aps/evidence-report-export-packages", {}),
    (f"{_API}/connectors/nrc-adams-aps/context-packets", {}),
    (f"{_API}/connectors/nrc-adams-aps/context-dossiers", {}),
    (f"{_API}/connectors/nrc-adams-aps/deterministic-insight-artifacts", {}),
    (f"{_API}/connectors/nrc-adams-aps/deterministic-challenge-artifacts", {}),
    (f"{_API}/connectors/nrc-adams-aps/deterministic-challenge-review-packets", {}),
    (f"{_API}/connectors/runs/{_CRUN}/resume", {}),
    (f"{_API}/connectors/runs/{_CRUN}/cancel", {}),
]

# POST multipart route (pre-body middleware; no body needed for gate proof)
_POST_MULTIPART_ROUTES = [
    f"{_API}/sources/upload",
]

assert len(_GET_ROUTES) == 21, f"Expected 21 GET routes, got {len(_GET_ROUTES)}"
assert len(_POST_JSON_ROUTES) == 30, f"Expected 30 POST JSON routes, got {len(_POST_JSON_ROUTES)}"
assert len(_POST_MULTIPART_ROUTES) == 1, f"Expected 1 multipart POST route, got {len(_POST_MULTIPART_ROUTES)}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(tmp_path, monkeypatch, *, auth_owner: str, trusted: bool) -> TestClient:
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", auth_owner)
    monkeypatch.setattr(settings, "trusted_proxy_mode", trusted)
    if auth_owner == "proxy":
        monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
        monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def proxy_fail_closed_client(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def proxy_trusted_client(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def local_default_client(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, auth_owner="none", trusted=False)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _is_auth_error_code(body: dict) -> bool:
    ec = body.get("error_code", "")
    return "auth_policy" in ec or "proxy" in ec or "missing_identity" in ec


# ---------------------------------------------------------------------------
# Posture 1: proxy mode, no identity header → auth-gate error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _GET_ROUTES)
def test_get_route_rejected_without_identity_in_proxy_mode(
    proxy_fail_closed_client: TestClient,
    path: str,
) -> None:
    """Every GET route returns an auth-gate error when proxy mode is active but identity header is absent."""
    response = proxy_fail_closed_client.get(path)
    assert response.status_code == 401, (
        f"Expected 401 auth gate on GET {path}, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "error_code" in body, f"No error_code in response body for GET {path}: {body}"
    assert "missing_identity_authority" in body["error_code"], (
        f"Unexpected error_code for GET {path}: {body['error_code']}"
    )


@pytest.mark.parametrize("path,payload", _POST_JSON_ROUTES)
def test_post_json_route_rejected_without_identity_in_proxy_mode(
    proxy_fail_closed_client: TestClient,
    path: str,
    payload: dict,
) -> None:
    """Every POST (JSON) route returns an auth-gate error when proxy mode is active but identity header is absent.
    Minimal valid body supplied so FastAPI body-injection succeeds and the gate (first statement) fires."""
    response = proxy_fail_closed_client.post(path, json=payload)
    assert response.status_code in (401, 409), (
        f"Expected 401/409 auth gate on POST {path}, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "error_code" in body, f"No error_code in response body for POST {path}: {body}"
    assert _is_auth_error_code(body), (
        f"Unexpected error_code for POST {path}: {body['error_code']}"
    )


@pytest.mark.parametrize("path", _POST_MULTIPART_ROUTES)
def test_post_multipart_route_rejected_without_identity_in_proxy_mode(
    proxy_fail_closed_client: TestClient,
    path: str,
) -> None:
    """Multipart POST routes are intercepted by pre-body middleware: auth rejection happens
    without a body being required."""
    response = proxy_fail_closed_client.post(path)
    assert response.status_code in (401, 409), (
        f"Expected 401/409 auth gate on multipart POST {path}, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "error_code" in body, f"No error_code in response body for POST {path}: {body}"
    assert _is_auth_error_code(body), (
        f"Unexpected error_code for POST {path}: {body['error_code']}"
    )


# ---------------------------------------------------------------------------
# Posture 2: proxy mode, valid identity headers → not auth-gate rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _GET_ROUTES)
def test_get_route_not_auth_rejected_with_valid_identity(
    proxy_trusted_client: TestClient,
    path: str,
) -> None:
    """Every GET route is NOT auth-rejected when trusted proxy identity headers are present
    (may produce 404/400/500 from service layer — that is acceptable)."""
    response = proxy_trusted_client.get(
        path,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        assert not _is_auth_error_code(body), (
            f"Auth-gate error on GET {path} with valid headers: {body}"
        )


@pytest.mark.parametrize("path,payload", _POST_JSON_ROUTES)
def test_post_json_route_not_auth_rejected_with_valid_identity(
    proxy_trusted_client: TestClient,
    path: str,
    payload: dict,
) -> None:
    """Every POST (JSON) route is NOT auth-rejected when trusted proxy identity headers are present."""
    response = proxy_trusted_client.post(
        path,
        json=payload,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        assert not _is_auth_error_code(body), (
            f"Auth-gate error on POST {path} with valid headers: {body}"
        )


@pytest.mark.parametrize("path", _POST_MULTIPART_ROUTES)
def test_post_multipart_route_not_auth_rejected_with_valid_identity(
    proxy_trusted_client: TestClient,
    path: str,
) -> None:
    """Multipart POST routes are NOT auth-rejected when valid identity headers are present."""
    response = proxy_trusted_client.post(
        path,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        assert not _is_auth_error_code(body), (
            f"Auth-gate error on multipart POST {path} with valid headers: {body}"
        )


# ---------------------------------------------------------------------------
# Posture 3: local default mode (auth_owner=none) → inert seam
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _GET_ROUTES)
def test_get_route_local_default_mode_not_auth_rejected(
    local_default_client: TestClient,
    path: str,
) -> None:
    """In local default mode (auth_owner=none) GET routes proceed to service layer; no auth rejection."""
    response = local_default_client.get(path)
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        assert not _is_auth_error_code(body), (
            f"Auth-gate error in local default mode on GET {path}: {body}"
        )


@pytest.mark.parametrize("path,payload", _POST_JSON_ROUTES)
def test_post_json_route_local_default_mode_not_auth_rejected(
    local_default_client: TestClient,
    path: str,
    payload: dict,
) -> None:
    """In local default mode (auth_owner=none) POST routes proceed to service layer; no auth rejection."""
    response = local_default_client.post(path, json=payload)
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        assert not _is_auth_error_code(body), (
            f"Auth-gate error in local default mode on POST {path}: {body}"
        )


@pytest.mark.parametrize("path", _POST_MULTIPART_ROUTES)
def test_post_multipart_route_local_default_mode_not_auth_rejected(
    local_default_client: TestClient,
    path: str,
) -> None:
    """In local default mode multipart POST routes proceed without auth rejection."""
    response = local_default_client.post(path)
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        assert not _is_auth_error_code(body), (
            f"Auth-gate error in local default mode on multipart POST {path}: {body}"
        )


@pytest.mark.parametrize("path", _POST_MULTIPART_ROUTES)
def test_post_multipart_route_rejects_auditor_role_before_body_parsing(
    tmp_path,
    monkeypatch,
    path: str,
) -> None:
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
    monkeypatch.setattr(settings, "proxy_roles_header", _ROLES_HEADER)
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")

    try:
        response = client.post(
            path,
            headers={
                _IDENTITY_HEADER: _IDENTITY_CANARY,
                _GROUPS_HEADER: _GROUPS_CANARY,
                _ROLES_HEADER: "auditor",
            },
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403, response.text
    body = response.json()
    assert "role_access_forbidden" in body.get("error_code", ""), body
    assert _IDENTITY_CANARY not in response.text
    assert _GROUPS_CANARY not in response.text
