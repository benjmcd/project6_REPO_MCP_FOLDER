from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import review_nrc_aps
from tests.review_browser_fixture import build_review_browser_fixture, install_review_browser_patches


def create_app() -> FastAPI:
    temp_dir = TemporaryDirectory(prefix="review-browser-", ignore_cleanup_errors=True)
    fixture = build_review_browser_fixture(Path(temp_dir.name))
    install_review_browser_patches(fixture)

    review_ui_static_dir = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static"

    app = FastAPI(title="NRC APS Review Browser Server")
    app.state.review_browser_temp_dir = temp_dir
    app.state.review_browser_fixture = fixture
    app.include_router(review_nrc_aps.router, prefix="/api/v1/review/nrc-aps")
    app.mount("/review/nrc-aps/static", StaticFiles(directory=review_ui_static_dir), name="review_ui_static")

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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
