from __future__ import annotations

import ast
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from main import app  # noqa: E402

_API_PREFIX = settings.api_prefix.rstrip("/")
_LAYER3_API = f"{_API_PREFIX}/layer3"
_NRC_APS_API = f"{_API_PREFIX}/review/nrc-aps"

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_ROLES_HEADER = "X-Forwarded-Roles"

_CODE_UNTRUSTED = "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
_CODE_MISSING_IDENTITY = "sec_xbrl_in_app_auth_policy_missing_identity_authority"
_CODE_MISSING_WORKSPACE = "sec_xbrl_in_app_auth_policy_missing_workspace_authority"
_CODE_MISSING_ROLE = "sec_xbrl_in_app_auth_policy_missing_role_authority"
_CODE_ROLE_FORBIDDEN = "sec_xbrl_in_app_auth_policy_role_access_forbidden"
_AUTH_ERROR_CODES = {
    _CODE_UNTRUSTED,
    _CODE_MISSING_IDENTITY,
    _CODE_MISSING_WORKSPACE,
    _CODE_MISSING_ROLE,
    _CODE_ROLE_FORBIDDEN,
}
_AUTH_STATUS_CODES = {401, 403, 409}

_NONSEC_ROUTE_FILES = [
    BACKEND / "app" / "api" / "layer3" / "__init__.py",
    BACKEND / "app" / "api" / "layer3" / "handoff.py",
    BACKEND / "app" / "api" / "layer3" / "package.py",
    BACKEND / "app" / "api" / "layer3" / "operator_identity.py",
    BACKEND / "app" / "api" / "layer3" / "source_ingestion.py",
    BACKEND / "app" / "api" / "review_nrc_aps.py",
]

_PUBLIC_METADATA_HANDLERS = {
    ("__init__.py", "get_bootstrap"),
    ("__init__.py", "get_readiness"),
    ("__init__.py", "get_authority_matrix"),
}

_EXPECTED_FILE_COUNTS = {
    "__init__.py": {"routes": 30, "gated": 27, "public": 3},
    "handoff.py": {"routes": 25, "gated": 25, "public": 0},
    "package.py": {"routes": 16, "gated": 16, "public": 0},
    "operator_identity.py": {"routes": 1, "gated": 1, "public": 0},
    "source_ingestion.py": {"routes": 88, "gated": 88, "public": 0},
    "review_nrc_aps.py": {"routes": 23, "gated": 23, "public": 0},
}


@dataclass(frozen=True)
class _RouteRecord:
    file_name: str
    function_name: str
    method: str
    path: str
    line: int
    access: str | None


def _route_decorator(decorator: ast.expr) -> tuple[str, str] | None:
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "router"
        and func.attr in {"get", "post", "put", "patch", "delete"}
    ):
        path = ""
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            if isinstance(decorator.args[0].value, str):
                path = decorator.args[0].value
        return func.attr.upper(), path
    return None


def _access_for_route(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "_route_level_operator_identity":
            continue
        for keyword in child.keywords:
            if (
                keyword.arg == "access"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                return keyword.value.value
        return None
    return None


def _collect_nonsec_routes() -> list[_RouteRecord]:
    records: list[_RouteRecord] = []
    for source_path in _NONSEC_ROUTE_FILES:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        prefix = _NRC_APS_API if source_path.name == "review_nrc_aps.py" else _LAYER3_API
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                route = _route_decorator(decorator)
                if route is None:
                    continue
                method, path = route
                records.append(
                    _RouteRecord(
                        file_name=source_path.name,
                        function_name=node.name,
                        method=method,
                        path=f"{prefix}{path}",
                        line=node.lineno,
                        access=_access_for_route(node),
                    )
                )
    return records


def _configure_proxy(monkeypatch, *, mode: str) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(settings, "proxy_roles_header", _ROLES_HEADER)
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", mode)
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")


def _client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _error_code(response) -> str | None:
    if not response.headers.get("content-type", "").startswith("application/json"):
        return None
    data = response.json()
    return data.get("error_code") if isinstance(data, dict) else None


def _assert_not_auth_blocked(response) -> None:
    assert _error_code(response) not in _AUTH_ERROR_CODES, response.text
    assert response.status_code not in _AUTH_STATUS_CODES, response.text


def test_nonsec_route_identity_audit_inventory_matches_current_authority() -> None:
    records = _collect_nonsec_routes()

    assert len(records) == 183
    by_file = Counter(record.file_name for record in records)
    gated_by_file = Counter(record.file_name for record in records if record.access is not None)
    public_by_file = Counter(record.file_name for record in records if record.access is None)
    for file_name, expected in _EXPECTED_FILE_COUNTS.items():
        assert by_file[file_name] == expected["routes"]
        assert gated_by_file[file_name] == expected["gated"]
        assert public_by_file[file_name] == expected["public"]

    public_handlers = {
        (record.file_name, record.function_name)
        for record in records
        if record.access is None
    }
    assert public_handlers == _PUBLIC_METADATA_HANDLERS

    access_counts = Counter(record.access for record in records if record.access is not None)
    assert access_counts == {"read": 62, "write": 118}

    nrc_aps = [record for record in records if record.file_name == "review_nrc_aps.py"]
    assert len(nrc_aps) == 23
    assert {record.method for record in nrc_aps} == {"GET"}
    assert {record.access for record in nrc_aps} == {"read"}


def test_public_layer3_metadata_routes_remain_auth_exempt_under_proxy_role_mode(monkeypatch) -> None:
    _configure_proxy(monkeypatch, mode="role_enforcing")

    with _client() as client:
        for route in ("/bootstrap", "/readiness", "/authority-matrix"):
            response = client.get(_LAYER3_API + route)
            assert response.status_code == 200, response.text
            _assert_not_auth_blocked(response)


def test_nrc_aps_runs_route_is_inert_under_auth_owner_none(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")

    with _client() as client:
        response = client.get(_NRC_APS_API + "/runs")

    _assert_not_auth_blocked(response)


def test_nrc_aps_runs_route_identity_presence_ignores_missing_roles(monkeypatch) -> None:
    _configure_proxy(monkeypatch, mode="identity_presence")

    with _client() as client:
        response = client.get(
            _NRC_APS_API + "/runs",
            headers={
                _IDENTITY_HEADER: "operator@example.com",
                _GROUPS_HEADER: "workspace",
            },
        )

    _assert_not_auth_blocked(response)


def test_nrc_aps_runs_route_proxy_missing_identity_fails_closed(monkeypatch) -> None:
    _configure_proxy(monkeypatch, mode="identity_presence")

    with _client() as client:
        response = client.get(
            _NRC_APS_API + "/runs",
            headers={_GROUPS_HEADER: "workspace"},
        )

    assert response.status_code == 401, response.text
    assert _error_code(response) == _CODE_MISSING_IDENTITY


def test_nrc_aps_runs_route_role_enforcing_missing_roles_fails_closed(monkeypatch) -> None:
    _configure_proxy(monkeypatch, mode="role_enforcing")

    with _client() as client:
        response = client.get(
            _NRC_APS_API + "/runs",
            headers={
                _IDENTITY_HEADER: "operator@example.com",
                _GROUPS_HEADER: "workspace",
            },
        )

    assert response.status_code == 401, response.text
    assert _error_code(response) == _CODE_MISSING_ROLE


def test_nrc_aps_runs_route_role_enforcing_auditor_read_allowed(monkeypatch) -> None:
    _configure_proxy(monkeypatch, mode="role_enforcing")

    with _client() as client:
        response = client.get(
            _NRC_APS_API + "/runs",
            headers={
                _IDENTITY_HEADER: "operator@example.com",
                _GROUPS_HEADER: "workspace",
                _ROLES_HEADER: "auditor",
            },
        )

    _assert_not_auth_blocked(response)
