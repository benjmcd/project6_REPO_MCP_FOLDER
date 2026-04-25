from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
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
from app.models.models import AnalysisArtifact, AnalysisRun, Dataset, DatasetVersion, VariableDefinition, VariableProfile, uuid_str
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import materialize_typing_entry
from review_browser_fixture import build_review_browser_fixture, install_review_browser_patches


def _install_layer3_browser_patches() -> None:
    def _recommend_analysis(*args, **kwargs) -> dict[str, object]:
        dataset_version_id = str(kwargs.get("dataset_version_id") or (args[1] if len(args) > 1 else ""))
        return {
            "dataset_version_id": dataset_version_id,
            "recommended_sequence": ["decomposition", "structural_break"],
            "rationale": "browser harness deterministic quantitative recommendation",
            "profile_context": {
                "stationary_like_variables": ["value"],
                "mixed_or_nonstationary_variables": [],
                "seasonal_like_variables": ["value"],
            },
        }

    def _run_analysis(db, *, dataset_version_id, method_name, goal_type=None, parameters=None, annotation_window_id=None):
        now = datetime.now(timezone.utc)
        run = AnalysisRun(
            analysis_run_id=uuid_str(),
            dataset_version_id=dataset_version_id,
            method_name=method_name,
            goal_type=goal_type,
            status="completed",
            route_reason="browser harness deterministic quantitative run",
            parameters_json=parameters or {},
            window_scope_json={"annotation_window_id": annotation_window_id} if annotation_window_id else {},
            started_at=now,
            completed_at=now,
        )
        db.add(run)
        db.flush()
        db.add(
            AnalysisArtifact(
                artifact_id=uuid_str(),
                analysis_run_id=run.analysis_run_id,
                artifact_type="summary_json",
                title="Browser harness deterministic output",
                storage_ref=f"layer3-browser://artifact/{run.analysis_run_id}/summary.json",
                summary="Deterministic Layer 3 browser harness output.",
                metadata_json={"source": "review_browser_server", "method_name": method_name},
            )
        )
        db.flush()
        return run

    layer3_pass_entry_module.recommend_analysis = _recommend_analysis
    layer3_pass_entry_module.run_analysis = _run_analysis


def _seed_browser_dataset_version(db, temp_path: Path, *, seed_id: str, dataset_id: str, dataset_version_id: str) -> Path:
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {seed_id}",
        description="Layer 3 browser harness dataset",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="layer3-browser-harness",
    )
    observed_at = VariableDefinition(
        variable_id=f"var-time-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    value_profile = VariableProfile(
        variable_profile_id=f"profile-value-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_id=value.variable_id,
        seasonality_flag=True,
        stationarity_hint="likely_stationary",
        summary_json={},
    )
    db.add_all([dataset, version, observed_at, value, value_profile])
    db.flush()

    dataset_dir = temp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    rows = ["observed_at,value"]
    for index in range(24):
        year = 2020 + (index // 12)
        month = 1 + (index % 12)
        rows.append(f"{year:04d}-{month:02d}-01T00:00:00+00:00,{100 + index}")
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    version.storage_ref = str(csv_path)
    version.row_count = 24
    db.flush()
    return csv_path


def _build_browser_quant_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="layer3-browser-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "gate_c_pass"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": dataset_id, "storage_ref": str(csv_path)},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def create_app() -> FastAPI:
    temp_dir = TemporaryDirectory(prefix="review-browser-", ignore_cleanup_errors=True)
    temp_path = Path(temp_dir.name)
    fixture = build_review_browser_fixture(temp_path)
    install_review_browser_patches(fixture)
    _install_layer3_browser_patches()
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
            session_id = _build_browser_quant_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    return app
