from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect as sa_inspect

from app.api.router import api_router
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base, engine


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

app = FastAPI(title=settings.app_name)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(api_router, prefix=settings.api_prefix)
bootstrap_storage_tree()
app.mount('/storage', StaticFiles(directory=settings.storage_dir), name='storage')
review_ui_static_dir = Path(__file__).resolve().parent / "app" / "review_ui" / "static"
app.mount('/review/nrc-aps/static', StaticFiles(directory=review_ui_static_dir), name='review_ui_static')


@app.get('/review/nrc-aps', response_class=HTMLResponse)
def review_nrc_aps_page() -> HTMLResponse:
    index_file = review_ui_static_dir / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/document-trace', response_class=HTMLResponse)
def review_nrc_aps_document_trace_page() -> HTMLResponse:
    trace_file = review_ui_static_dir / "document_trace.html"
    return HTMLResponse(content=trace_file.read_text(encoding="utf-8"))


@app.get('/review/analyst-insight', response_class=HTMLResponse)
def analyst_insight_page() -> HTMLResponse:
    page_file = review_ui_static_dir / "analyst_insight.html"
    return HTMLResponse(content=page_file.read_text(encoding="utf-8"))


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


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
