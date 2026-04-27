from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

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
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetVersion,
    L3OutputPackage,
    L3ReconciliationRecord,
    VariableDefinition,
    VariableProfile,
    uuid_str,
)
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

APS_CONTENT_CONTRACT_ID = "aps_content_units_v2"
APS_CHUNKING_CONTRACT_ID = "aps_chunking_v2"
APS_NORMALIZATION_CONTRACT_ID = "aps_text_normalization_v2"
PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF = "aps_evidence_bundle_handoff"


def _install_layer3_browser_patches(temp_path: Path) -> None:
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

    from app.services import layer3_workbench as layer3_workbench_module

    def _check_aps_handoff_compatibility(db, *, session_id):
        return SimpleNamespace(compatible=True, blocked_reason=None)

    def _materialize_aps_handoff(db, *, session_id):
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.session_id == session_id)
            .one()
        )
        output_package_id = uuid_str()
        payload_path = temp_path / "aps-dispatch" / f"{output_package_id}.json"
        payload = {
            "schema_id": "layer3.browser_aps_handoff_fixture.v1",
            "bundle_id": f"browser-aps-bundle-{output_package_id}",
            "aps_schema_id": "nrc_aps_evidence_bundle.v1",
            "session_id": session_id,
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
        }
        payload_ref = _write_json(payload_path, payload)
        package = L3OutputPackage(
            output_package_id=output_package_id,
            session_id=session_id,
            reconciliation_record_id=reconciliation.reconciliation_record_id,
            package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            status="package_complete",
            payload_ref=payload_ref,
            payload_hash=hashlib.sha256(Path(payload_ref).read_bytes()).hexdigest(),
            summary_json={
                "bundle_id": payload["bundle_id"],
                "aps_schema_id": payload["aps_schema_id"],
            },
        )
        db.add(package)
        db.flush()
        return SimpleNamespace(output_package=package)

    layer3_workbench_module.check_aps_handoff_compatibility = _check_aps_handoff_compatibility
    layer3_workbench_module.materialize_aps_handoff = _materialize_aps_handoff


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return str(path)


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


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


def _seed_browser_aps_content_fixture(
    db,
    temp_path: Path,
    *,
    run_id: str,
    target_id: str,
    content_id: str,
) -> None:
    db.add(
        ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            status="completed",
        )
    )
    db.add(
        ConnectorRunTarget(
            connector_run_target_id=target_id,
            connector_run_id=run_id,
            status="completed",
            ordinal=0,
        )
    )

    artifact_root = temp_path / "aps"
    chunk_texts = [
        "Inspection findings confirm stable cooling performance.",
        "No safety-significant degradation was identified during the interval.",
    ]
    normalized_text = "\n".join(chunk_texts)
    content_units_ref = _write_json(
        artifact_root / f"{content_id}_content_units.json",
        {
            "content_id": content_id,
            "run_id": run_id,
            "target_id": target_id,
            "chunk_count": len(chunk_texts),
        },
    )
    normalized_text_ref = _write_text(artifact_root / f"{content_id}_normalized.txt", normalized_text)
    blob_ref = _write_text(artifact_root / f"{content_id}.pdf", "pdf-placeholder")
    selection_ref = _write_json(artifact_root / f"{content_id}_selection.json", {"run_id": run_id, "target_id": target_id})
    discovery_ref = _write_json(artifact_root / f"{content_id}_discovery.json", {"run_id": run_id, "target_id": target_id})
    diagnostics_ref = _write_json(artifact_root / f"{content_id}_diagnostics.json", {"quality_status": "strong"})

    db.add(
        ApsContentDocument(
            content_id=content_id,
            content_contract_id=APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            normalized_char_count=len(normalized_text),
            chunk_count=len(chunk_texts),
            content_status="indexed",
            media_type="application/pdf",
            document_class="inspection_report",
            quality_status="strong",
            page_count=2,
            diagnostics_ref=diagnostics_ref,
            visual_page_refs_json=json.dumps([]),
        )
    )
    for ordinal, chunk_text in enumerate(chunk_texts):
        db.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=f"{content_id}-chunk-{ordinal + 1}",
                content_contract_id=APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=ordinal,
                start_char=ordinal * 64,
                end_char=(ordinal * 64) + len(chunk_text),
                chunk_text=chunk_text,
                chunk_text_sha256=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                page_start=ordinal + 1,
                page_end=ordinal + 1,
                unit_kind="pdf_paragraph",
                quality_status="strong",
            )
        )
    db.add(
        ApsContentLinkage(
            content_id=content_id,
            run_id=run_id,
            target_id=target_id,
            accession_number="ML26001A001",
            content_contract_id=APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
            content_units_ref=content_units_ref,
            normalized_text_ref=normalized_text_ref,
            normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            blob_ref=blob_ref,
            blob_sha256=hashlib.sha256(Path(blob_ref).read_bytes()).hexdigest(),
            download_exchange_ref="aps/download_exchange.json",
            discovery_ref=discovery_ref,
            selection_ref=selection_ref,
            diagnostics_ref=diagnostics_ref,
        )
    )
    db.flush()


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


def _build_browser_aps_handoff_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    run_id = f"run-{seed_id}"
    target_id = f"target-{seed_id}"
    content_id = f"content-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    _seed_browser_aps_content_fixture(db, temp_path, run_id=run_id, target_id=target_id, content_id=content_id)
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}-aps-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="layer3-browser-aps-handoff-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "aps_handoff_dispatch"},
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
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": content_id, "run_id": run_id, "target_id": target_id},
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "browser APS handoff companion"},
                load_summary={"loaded_records": 1, "failed_records": 0},
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
    _install_layer3_browser_patches(temp_path)
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

    @app.post("/__test/layer3/seed-aps-handoff")
    def seed_layer3_aps_handoff() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_aps_handoff_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    return app
