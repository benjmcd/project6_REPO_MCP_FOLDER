from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.db.session import Base
from app.models.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetVersion,
    L3OutputPackage,
    VariableDefinition,
    VariableProfile,
)
from app.services import nrc_aps_evidence_bundle as aps_bundle_module
from app.services import nrc_aps_evidence_bundle_contract as aps_contract
from app.services import nrc_aps_evidence_bundle_gate as aps_gate_module
from app.services.layer3_aps_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
    Layer3ApsHandoffError,
    materialize_aps_handoff,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    materialize_package_entry,
)
from app.services.layer3_pass_entry import materialize_pass_entry
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import materialize_typing_entry


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def _seed_timeseries_dataset_version(db, tmp_path: Path, *, dataset_version_id: str) -> None:
    dataset_id = f"ds-{dataset_version_id}"
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {dataset_id}",
        description="Gate D APS handoff proof dataset",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="gated-aps-handoff-proof",
    )
    observed_at = VariableDefinition(
        variable_id=f"var-time-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    value_profile = VariableProfile(
        variable_profile_id=f"profile-value-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
        variable_id=value.variable_id,
        seasonality_flag=False,
        stationarity_hint="likely_stationary",
        summary_json={},
    )
    db.add_all([dataset, version, observed_at, value, value_profile])
    db.flush()

    frame = pd.DataFrame(
        {
            "observed_at": pd.date_range("2021-01-01", periods=6, freq="MS", tz="UTC"),
            "value": [10.0, 11.5, 12.0, 12.5, 13.0, 13.5],
        }
    )
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    frame.to_csv(csv_path, index=False)
    version.storage_ref = str(csv_path)
    version.row_count = len(frame)
    db.flush()


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _seed_aps_content_fixture(
    db,
    tmp_path: Path,
    *,
    run_id: str,
    target_id: str,
    content_id: str,
    content_contract_id: str = aps_contract.APS_CONTENT_CONTRACT_ID,
    chunking_contract_id: str = aps_contract.APS_CHUNKING_CONTRACT_ID,
    normalization_contract_id: str = aps_contract.APS_NORMALIZATION_CONTRACT_ID,
    artifact_suffix: str = "",
) -> None:
    if db.get(ConnectorRun, run_id) is None:
        db.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                status="completed",
            )
        )
    if db.get(ConnectorRunTarget, target_id) is None:
        db.add(
            ConnectorRunTarget(
                connector_run_target_id=target_id,
                connector_run_id=run_id,
                status="completed",
                ordinal=0,
            )
        )

    artifact_root = tmp_path / "aps"
    chunk_texts = [
        "Inspection findings confirm stable cooling performance.",
        "No safety-significant degradation was identified during the interval.",
    ]
    suffix = f"_{artifact_suffix}" if artifact_suffix else ""
    content_units_ref = _write_json(
        artifact_root / f"{content_id}{suffix}_content_units.json",
        {
            "content_id": content_id,
            "run_id": run_id,
            "target_id": target_id,
            "chunk_count": len(chunk_texts),
        },
    )
    normalized_text = "\n".join(chunk_texts)
    normalized_text_ref = _write_text(
        artifact_root / f"{content_id}{suffix}_normalized.txt",
        normalized_text,
    )
    blob_ref = _write_text(
        artifact_root / f"{content_id}{suffix}.pdf",
        "pdf-placeholder",
    )
    selection_ref = _write_json(
        artifact_root / f"{content_id}{suffix}_selection.json",
        {"run_id": run_id, "target_id": target_id},
    )
    discovery_ref = _write_json(
        artifact_root / f"{content_id}{suffix}_discovery.json",
        {"run_id": run_id, "target_id": target_id},
    )
    diagnostics_ref = _write_json(
        artifact_root / f"{content_id}{suffix}_diagnostics.json",
        {"quality_status": "strong"},
    )

    db.add(
        ApsContentDocument(
            content_id=content_id,
            content_contract_id=content_contract_id,
            chunking_contract_id=chunking_contract_id,
            normalization_contract_id=normalization_contract_id,
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
                content_contract_id=content_contract_id,
                chunking_contract_id=chunking_contract_id,
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
            content_contract_id=content_contract_id,
            chunking_contract_id=chunking_contract_id,
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


def _build_packaged_session(
    db,
    tmp_path: Path,
    *,
    include_full_aps_identity: bool,
) -> tuple[str, str, str, str]:
    dataset_version_id = "dv-aps-handoff-001"
    run_id = "run-aps-handoff-001"
    target_id = "target-aps-handoff-001"
    content_id = "content-aps-handoff-001"

    _seed_timeseries_dataset_version(db, tmp_path, dataset_version_id=dataset_version_id)
    _seed_aps_content_fixture(db, tmp_path, run_id=run_id, target_id=target_id, content_id=content_id)

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-aps-handoff-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": "sel-aps-handoff-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="gated-aps-handoff-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "gate_d_aps_handoff"},
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
                source_provenance={
                    "dataset_id": f"ds-{dataset_version_id}",
                    "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv"),
                },
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    aps_identity = {"content_id": content_id}
    if include_full_aps_identity:
        aps_identity.update({"run_id": run_id, "target_id": target_id})
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity=aps_identity,
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "aps qualitative companion"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()

    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    materialize_pass_entry(db, session_id=session.session_id)
    db.commit()
    materialize_package_entry(db, session_id=session.session_id)
    db.commit()

    return session.session_id, run_id, target_id, content_id


def _rows_by_kind(db) -> dict[str, L3OutputPackage]:
    return {
        row.package_kind: row
        for row in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
    }


def test_materialize_aps_handoff_emits_bundle_and_handoff_row(tmp_path: Path) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, target_id, content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )

        result = materialize_aps_handoff(db, session_id=session_id)
        db.commit()

        rows = _rows_by_kind(db)
        canonical_row = rows[PACKAGE_KIND_CANONICAL_INTERNAL]
        handoff_row = rows[PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF]
        assert result.output_package.output_package_id == handoff_row.output_package_id
        assert handoff_row.status == canonical_row.status
        assert Path(handoff_row.payload_ref).parent == Path(settings.connector_reports_dir)
        assert hashlib.sha256(Path(handoff_row.payload_ref).read_bytes()).hexdigest() == handoff_row.payload_hash

        loaded_payload, bundle_path = aps_bundle_module.load_persisted_bundle_artifact(
            bundle_ref=handoff_row.payload_ref
        )
        assert bundle_path == Path(handoff_row.payload_ref)
        assert loaded_payload["schema_id"] == aps_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID
        assert loaded_payload["run_id"] == run_id
        assert loaded_payload["mode"] == aps_contract.APS_MODE_BROWSE
        assert loaded_payload["total_hits"] == 2
        assert {row["content_id"] for row in loaded_payload["results"]} == {content_id}
        assert {row["target_id"] for row in loaded_payload["results"]} == {target_id}

        reasons: list[str] = []
        aps_gate_module._validate_bundle_payload_schema(loaded_payload, reasons)
        aps_gate_module._validate_bundle_checksum(loaded_payload, reasons)
        aps_gate_module._validate_request_identity(loaded_payload, reasons)
        aps_gate_module._validate_provenance_and_snippets(loaded_payload, reasons)
        aps_gate_module._validate_artifact_db_parity(loaded_payload, db, reasons)
        assert reasons == []

        assert handoff_row.summary_json["aps_target_family"] == "evidence_bundle"
        assert handoff_row.summary_json["aps_schema_id"] == aps_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID
        assert handoff_row.summary_json["bundle_id"] == loaded_payload["bundle_id"]
        assert handoff_row.summary_json["bundle_ref"] == handoff_row.payload_ref
        assert handoff_row.summary_json["source_package_kinds_json"] == [
            "canonical_internal",
            "user_facing",
            "review_facing",
        ]
        assert set(handoff_row.summary_json["source_package_refs_json"]) == {
            "canonical_internal",
            "user_facing",
            "review_facing",
        }
        assert handoff_row.summary_json["handoff_status"]["aps_handoff_admitted"] is True
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_handoff_fails_closed_on_missing_packaged_run_target_identity(tmp_path: Path) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _, _ = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=False,
        )

        with pytest.raises(
            Layer3ApsHandoffError,
            match="content_id, run_id, and target_id",
        ):
            materialize_aps_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_handoff_ignores_non_current_contract_variants(tmp_path: Path) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, run_id, target_id, content_id = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_id,
            content_contract_id="aps_content_units_v1",
            chunking_contract_id="aps_chunking_v1",
            normalization_contract_id="aps_text_normalization_v1",
            artifact_suffix="legacy",
        )
        db.commit()

        result = materialize_aps_handoff(db, session_id=session_id)
        db.commit()

        assert result.bundle_payload["schema_id"] == aps_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID
        assert result.bundle_payload["total_hits"] == 2
        assert {
            row["content_contract_id"] for row in result.bundle_payload["results"]
        } == {aps_contract.APS_CONTENT_CONTRACT_ID}
        assert {
            row["chunking_contract_id"] for row in result.bundle_payload["results"]
        } == {aps_contract.APS_CHUNKING_CONTRACT_ID}
        assert {
            row["normalization_contract_id"] for row in result.bundle_payload["results"]
        } == {aps_contract.APS_NORMALIZATION_CONTRACT_ID}
    finally:
        settings.storage_dir = original_storage_dir


def test_materialize_aps_handoff_normalizes_bundle_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        db = _make_session()
        session_id, _, _, _ = _build_packaged_session(
            db,
            tmp_path,
            include_full_aps_identity=True,
        )

        def _raise_bundle_error(*, base_items, normalized_request):
            raise aps_bundle_module.EvidenceBundleError(
                aps_contract.APS_RUNTIME_FAILURE_PROVENANCE_MISSING,
                "missing required provenance fields: target_id",
                status_code=422,
            )

        monkeypatch.setattr(aps_bundle_module, "_validated_items_for_mode", _raise_bundle_error)

        with pytest.raises(
            Layer3ApsHandoffError,
            match="APS evidence bundle handoff failed",
        ):
            materialize_aps_handoff(db, session_id=session_id)

        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count()
            == 0
        )
    finally:
        settings.storage_dir = original_storage_dir
