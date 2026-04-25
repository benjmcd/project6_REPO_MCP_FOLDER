from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api import layer3, review_nrc_aps
from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from review_browser_fixture import build_review_browser_fixture, install_review_browser_patches
from test_layer3_pass_entry import _build_quant_ready_session


def create_app() -> FastAPI:
    temp_dir = TemporaryDirectory(prefix="review-browser-", ignore_cleanup_errors=True)
    temp_path = Path(temp_dir.name)
    fixture = build_review_browser_fixture(temp_path)
    install_review_browser_patches(fixture)
    settings.storage_dir = str(temp_path / "storage")
    bootstrap_storage_tree(settings.storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    review_ui_static_dir = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static"

    app = FastAPI(title="NRC APS Review Browser Server")
    app.state.review_browser_temp_dir = temp_dir
    app.state.review_browser_fixture = fixture
    app.state.layer3_engine = engine
    app.include_router(review_nrc_aps.router, prefix="/api/v1/review/nrc-aps")
    app.include_router(layer3.router, prefix="/api/v1/layer3")
    app.mount("/review/nrc-aps/static", StaticFiles(directory=review_ui_static_dir), name="review_ui_static")
    app.mount("/review/layer3/static", StaticFiles(directory=review_ui_static_dir), name="layer3_ui_static")

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/review/nrc-aps", response_class=HTMLResponse)
    def review_nrc_aps_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "index.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/document-trace", response_class=HTMLResponse)
    def review_nrc_aps_document_trace_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "document_trace.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/workbench-compare", response_class=HTMLResponse)
    def review_nrc_aps_workbench_compare_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "workbench_compare.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/candidate-b-trace", response_class=HTMLResponse)
    def review_nrc_aps_candidate_b_trace_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "candidate_b_trace.html").read_text(encoding="utf-8"))

    @app.get("/review/layer3", response_class=HTMLResponse)
    def layer3_workbench_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "layer3.html").read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/__test/layer3/seed-quant")
    def seed_layer3_quant() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id, _, _ = _build_quant_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    return app
