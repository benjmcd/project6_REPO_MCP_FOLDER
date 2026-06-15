from __future__ import annotations

import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect as sa_inspect, text

from app.api.router import api_router
from app.core.config import bootstrap_storage_tree, settings
from app.core.observability import RequestIdMiddleware, setup_logging, unhandled_exception_handler
from app.db.session import Base, engine, SessionLocal
from app.services import layer3_sec_xbrl_in_app_auth_policy
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response


def _run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    existing_tables = set(sa_inspect(engine).get_table_names())
    if "alembic_version" not in existing_tables and "connector_run" in existing_tables:
        command.stamp(cfg, "head")
        return
    command.upgrade(cfg, "head")


def _initialize_database() -> None:
    mode = settings.db_init_mode
    if mode == "none":
        return
    if mode == "create_all":
        Base.metadata.create_all(bind=engine)
        return
    _run_migrations()


_initialize_database()

setup_logging()

app = FastAPI(title=settings.app_name)

# Observability: request-id propagation (CORS, added after, wraps this middleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=settings.cors_allow_credentials_enabled,
    allow_methods=['*'],
    allow_headers=['*'],
)
# Global handler for unhandled exceptions — returns bounded 500, logs traceback
app.add_exception_handler(Exception, unhandled_exception_handler)


_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES: dict[str, str] = {}
_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTE_PATTERNS: tuple[
    tuple[re.Pattern[str], str, str],
    ...,
] = ()
_PRE_BODY_OPERATOR_AUTHORIZATION_BUILT = False
_REQUIRED_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES = {
    f"{settings.api_prefix.rstrip('/')}/analysis-runs": "write",
    f"{settings.api_prefix.rstrip('/')}/layer3/source/intake/upload": "write",
    f"{settings.api_prefix.rstrip('/')}/layer3/sec-xbrl/operator-review/workflow/status": "read",
}


def _endpoint_source(endpoint: Any) -> str:
    try:
        return inspect.getsource(endpoint)
    except (OSError, TypeError):
        pass
    # Robust fallback: inspect.getsource can fail (OSError) in some runtime
    # environments when its linecache lookup misses (e.g. relative co_filename
    # under a changed cwd). Read the defining module's file by its absolute
    # __file__ and slice the function's source window directly.
    try:
        code = getattr(endpoint, "__code__", None)
        if code is None:
            return ""
        module = sys.modules.get(getattr(endpoint, "__module__", "") or "")
        path = getattr(module, "__file__", None) or code.co_filename
        if not path:
            return ""
        if not os.path.isabs(path) and module is not None and getattr(module, "__file__", None):
            path = module.__file__
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        start = max(0, code.co_firstlineno - 1)
        return "".join(lines[start:start + 400])
    except Exception:  # noqa: BLE001 - best-effort source recovery
        return ""


def _operator_authorization_access_from_endpoint(endpoint: Any) -> str | None:
    source = _endpoint_source(endpoint)
    if "_route_level_operator_identity" in source:
        match = re.search(
            r"_route_level_operator_identity\([\s\S]*?access\s*=\s*['\"](read|write)['\"]",
            source,
        )
        return match.group(1) if match else "write"
    if "_sec_xbrl_policy_decision" in source or "authorize_sec_xbrl_route" in source:
        route_family_access = set(
            re.findall(r"\bsec_xbrl_[A-Za-z0-9_]+_(read|write)\b", source)
        )
        if "write" in route_family_access:
            return "write"
        if "read" in route_family_access:
            return "read"
    return None


def _build_pre_body_operator_authorization_post_routes(
    routes: list[Any],
) -> tuple[dict[str, str], tuple[tuple[re.Pattern[str], str, str], ...]]:
    routes_by_path: dict[str, str] = {}
    route_patterns: list[tuple[re.Pattern[str], str, str]] = []
    for route in routes:
        methods = getattr(route, "methods", set()) or set()
        if "POST" not in methods:
            continue
        access = _operator_authorization_access_from_endpoint(getattr(route, "endpoint", None))
        if access is None:
            continue
        path = str(getattr(route, "path", ""))
        path_regex = getattr(route, "path_regex", None)
        if not path or path_regex is None:
            continue
        routes_by_path[path] = access
        route_patterns.append((path_regex, path, access))
    return routes_by_path, tuple(route_patterns)


def _pre_body_operator_authorization_access_for_path(path: str) -> str | None:
    exact = _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES.get(path)
    if exact is not None:
        return exact
    for path_regex, _path_template, access in _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTE_PATTERNS:
        if path_regex.match(path):
            return access
    return None


def _require_pre_body_operator_authorization_routes(routes_by_path: dict[str, str]) -> None:
    missing = {
        path: expected_access
        for path, expected_access in _REQUIRED_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES.items()
        if routes_by_path.get(path) != expected_access
    }
    if missing:
        import logging

        logging.getLogger("app.pre_body_authorization").warning(
            "pre-body operator authorization discovery did not cover required protected POST routes "
            "(in-handler operator-identity enforcement still applies): %s",
            ", ".join(f"{path}={access}" for path, access in sorted(missing.items())),
        )


def _auth_policy_error_response(
    exc: layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(field)
                    for field in exc.details.get(
                        "blocked_fields",
                        exc.details.get("mismatched_fields", []),
                    )
                ],
                next_allowed_actions=["inspect_existing_sec_xbrl_auth_binding_authority"],
            )
        ),
    )


@app.middleware("http")
async def _pre_body_operator_authorization_middleware(request: Request, call_next):
    _ensure_pre_body_operator_authorization_routes()
    access = _pre_body_operator_authorization_access_for_path(request.url.path)
    if request.method.upper() == "POST" and access is not None:
        try:
            layer3_sec_xbrl_in_app_auth_policy.route_level_operator_authorization_required(
                {str(key): str(value) for key, value in request.headers.items()},
                access=access,
            )
        except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
            return _auth_policy_error_response(exc)
    return await call_next(request)


app.include_router(api_router, prefix=settings.api_prefix)


def _ensure_pre_body_operator_authorization_routes() -> None:
    """Build the protected-POST-route map on first request.

    Discovery is deferred out of import time on purpose: at import the route
    table can still be incomplete depending on import order, which previously
    made app construction raise. By the time the first request is served the
    app is fully constructed, so discovery is reliable.
    """
    global _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES
    global _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTE_PATTERNS
    global _PRE_BODY_OPERATOR_AUTHORIZATION_BUILT
    if _PRE_BODY_OPERATOR_AUTHORIZATION_BUILT:
        return
    (
        _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES,
        _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTE_PATTERNS,
    ) = _build_pre_body_operator_authorization_post_routes(app.router.routes)
    _require_pre_body_operator_authorization_routes(_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES)
    _PRE_BODY_OPERATOR_AUTHORIZATION_BUILT = True
bootstrap_storage_tree()
if settings.storage_mount_enabled:
    app.mount('/storage', StaticFiles(directory=settings.storage_dir), name='storage')
review_ui_static_dir = Path(__file__).resolve().parent / "app" / "review_ui" / "static"
app.mount('/review/nrc-aps/static', StaticFiles(directory=review_ui_static_dir), name='review_ui_static')
app.mount('/review/layer3/static', StaticFiles(directory=review_ui_static_dir), name='layer3_ui_static')


@app.get('/review/nrc-aps', response_class=HTMLResponse)
def review_nrc_aps_page() -> HTMLResponse:
    index_file = review_ui_static_dir / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/document-trace', response_class=HTMLResponse)
def review_nrc_aps_document_trace_page() -> HTMLResponse:
    trace_file = review_ui_static_dir / "document_trace.html"
    return HTMLResponse(content=trace_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/workbench-compare', response_class=HTMLResponse)
def review_nrc_aps_workbench_compare_page() -> HTMLResponse:
    compare_file = review_ui_static_dir / "workbench_compare.html"
    return HTMLResponse(content=compare_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/candidate-b-trace', response_class=HTMLResponse)
def review_nrc_aps_candidate_b_trace_page() -> HTMLResponse:
    candidate_b_trace_file = review_ui_static_dir / "candidate_b_trace.html"
    return HTMLResponse(content=candidate_b_trace_file.read_text(encoding="utf-8"))


@app.get('/review/layer3', response_class=HTMLResponse)
def layer3_workbench_page() -> HTMLResponse:
    layer3_file = review_ui_static_dir / "layer3.html"
    return HTMLResponse(content=layer3_file.read_text(encoding="utf-8"))


@app.get('/review/analyst-insight', response_class=HTMLResponse)
def analyst_insight_page() -> HTMLResponse:
    page_file = review_ui_static_dir / "analyst_insight.html"
    return HTMLResponse(content=page_file.read_text(encoding="utf-8"))


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/ready', response_model=None)
def ready() -> JSONResponse:
    """Readiness probe: executes SELECT 1 against the configured database."""
    try:
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
        return JSONResponse(status_code=200, content={'status': 'ready'})
    except Exception:
        return JSONResponse(status_code=503, content={'status': 'unavailable'})


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return """
    <html>
      <head><title>Method-Aware Framework</title></head>
      <body style='font-family: sans-serif; max-width: 760px; margin: 40px auto;'>
        <h1>Method-Aware Data Utilization Framework</h1>
        <p>Starter backend is running.</p>
        <ul>
          <li><a href='/docs'>OpenAPI docs</a></li>
          <li><a href='/health'>Health</a></li>
          <li><a href='/review/analyst-insight'>Analyst insight layer</a> - deterministic integration, validation, and insight demo</li>
        </ul>
        <p>Use the upload endpoint first, then profile, transform, annotate, and analyze.</p>
      </body>
    </html>
    """
