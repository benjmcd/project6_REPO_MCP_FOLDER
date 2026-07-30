from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
)
from app.services import connector_egress_arming
from app.services import connectors_nrc_adams
from app.services import layer3_origin_continuity as origin
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_content_index
from app.services import nrc_aps_document_processing
from app.services import nrc_aps_strict_parse
from app.services.raw_storage_handles import persist_locked_raw_file


def _phase_b() -> Any:
    return importlib.import_module(
        "app.services.nrc_aps_phase_b_linkage"
    )


@pytest.fixture()
def db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    session = factory()
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _strict_output() -> dict[str, Any]:
    first = (
        "NRC admitted content remains bound to server-owned raw bytes "
        "and exact accession authority."
    )
    second = (
        "Phase B creates canonical chunks without changing Phase A "
        "acquisition state or URL posture."
    )
    normalized_text = f"{first}\n{second}"
    return {
        "declared_content_type": "application/pdf",
        "sniffed_content_type": "application/pdf",
        "effective_content_type": "application/pdf",
        "media_detection_status": "declared_and_sniffed_match",
        "document_processing_contract_id": (
            nrc_aps_document_processing.APS_DOCUMENT_EXTRACTION_CONTRACT_ID
        ),
        "extractor_id": nrc_aps_document_processing.APS_PDF_EXTRACTOR_ID,
        "normalization_contract_id": (
            nrc_aps_document_processing.APS_TEXT_NORMALIZATION_CONTRACT_ID
        ),
        "document_class": "layout_complex_pdf",
        "page_count": 2,
        "quality_status": nrc_aps_document_processing.APS_QUALITY_STATUS_STRONG,
        "degradation_codes": [],
        "ordered_units": [
            {
                "page_number": 1,
                "unit_kind": "pdf_text_block",
                "text": first,
                "bbox": [1.0, 2.0, 300.0, 40.0],
                "start_char": 0,
                "end_char": len(first),
            },
            {
                "page_number": 2,
                "unit_kind": "pdf_text_block",
                "text": second,
                "bbox": [1.0, 2.0, 320.0, 42.0],
                "start_char": len(first) + 1,
                "end_char": len(normalized_text),
            },
        ],
        "page_summaries": [
            {"page_number": 1, "unit_count": 1, "source": "native"},
            {"page_number": 2, "unit_count": 1, "source": "native"},
        ],
        "native_page_count": 2,
        "ocr_page_count": 0,
        "weak_page_count": 0,
        "visual_page_refs": [],
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(
            normalized_text.encode("utf-8")
        ).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }


def _make_strict_state(
    db: Session,
    *,
    raw_bytes: bytes = b"%PDF-1.7\nstrict phase B fixture\n%%EOF",
    run_id: str = "strict-nrc-phase-b",
    target_id: str = "strict-nrc-phase-b-target",
) -> tuple[ConnectorRun, ConnectorRunTarget, Path, str]:
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_root = Path(settings.connector_raw_dir)
    raw_path = raw_root / nrc_aps_artifact_ingestion.blob_relative_path(
        sha256=digest
    )
    persist_locked_raw_file(raw_root, raw_path, raw_bytes)
    completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    envelope = {
        "schema_id": "project6.connector_egress_arming.v1",
        "arming_fingerprint": "a" * 64,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": "b" * 64,
    }
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="strict_live_egress",
        status="completed",
        submission_idempotency_key=f"egress-arm:{run_id}",
        request_config_json={"connector_egress_arming": envelope},
        request_fingerprint="a" * 64,
        completed_at=completed_at,
        discovered_count=1,
        selected_count=1,
        downloaded_count=1,
        ingested_count=0,
        consumed_bytes=len(raw_bytes),
        failed_count=0,
        terminal_target_count=1,
        nonterminal_target_count=0,
        execution_lease_owner=None,
        execution_lease_token=None,
        execution_lease_expires_at=completed_at,
        error_summary=None,
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        stable_release_key="ML17123A319",
        stable_release_identifier="adams_accession:ML17123A319",
        identifiers_json=[
            {"type": "AccessionNumber", "value": "ML17123A319"}
        ],
        sciencebase_item_id=None,
        sciencebase_item_url=None,
        sciencebase_file_name="ML17123A319.pdf",
        sciencebase_download_uri=None,
        artifact_surface="files",
        selection_source="strict_exact_accession",
        selection_scope="dual_live_proof_v1",
        selection_match_basis="exact_accession",
        artifact_locator_type=connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS,
        source_artifact_key="nrc_adams_aps::ML17123A319",
        canonical_artifact_key="nrc_adams_aps::ML17123A319",
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path),
        fetch_policy_mode="strict_live_egress",
        redirect_count=0,
        aliases_json=[],
        source_reference_json={
            "schema_id": "project6.nrc_raw_admission.v1",
            "accession_number": "ML17123A319",
            "artifact_file_name": "ML17123A319.pdf",
            "detail_response_sha256": "c" * 64,
            "artifact_url_sha256": "d" * 64,
            "artifact_path_class": (
                connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
            ),
            "raw_content_sha256": digest,
            "raw_content_size_bytes": len(raw_bytes),
            "media_type": "application/pdf",
            "blob_storage_layout": "nrc_aps_blob_sha256_v1",
        },
        permission_snapshot_json={"direct_public_200": True},
        access_level_summary="public_direct_200",
        public_read_confirmed=True,
        status="downloaded",
        retry_eligible=False,
        attempt_count=1,
        downloaded_at=completed_at,
        last_attempt_at=completed_at,
        last_stage_transition_at=completed_at,
    )
    terminal = ConnectorRunEvent(
        connector_run_event_id=connector_egress_arming._deterministic_id(
            run_id,
            "egress_run_terminal",
        ),
        connector_run_id=run_id,
        connector_run_target_id=None,
        phase="execution",
        stage="terminal",
        event_type="egress_run_terminal",
        status_before="running",
        status_after="completed",
        reason_code="nrc_raw_admission_completed",
        error_class=None,
        message=None,
        metrics_json={
            "outcome_class": "nrc_raw_admission_completed",
            "arming_fingerprint": envelope["arming_fingerprint"],
            "campaign_introduction_index_revision": 1,
            "campaign_introduction_index_sha256": "b" * 64,
        },
        created_at=completed_at,
    )
    db.add_all([run, target, terminal])
    db.commit()
    return run, target, raw_path, digest


def _install_parser(
    monkeypatch: pytest.MonkeyPatch,
    *,
    output: dict[str, Any] | None = None,
    callback: Any | None = None,
) -> list[dict[str, Any]]:
    phase_b = _phase_b()
    calls: list[dict[str, Any]] = []

    def parse(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        if callback is not None:
            return callback(**kwargs)
        return deepcopy(output or _strict_output())

    monkeypatch.setattr(
        phase_b.nrc_aps_strict_parse,
        "parse_admitted_blob_strict",
        parse,
    )
    return calls


def _row_snapshot(db: Session) -> str:
    documents = [
        {
            key: getattr(row, key)
            for key in (
                "aps_content_document_id",
                "content_id",
                "content_contract_id",
                "chunking_contract_id",
                "normalization_contract_id",
                "normalized_text_sha256",
                "normalized_char_count",
                "chunk_count",
                "content_status",
                "media_type",
                "document_class",
                "quality_status",
                "page_count",
                "diagnostics_ref",
                "visual_page_refs_json",
                "created_at",
                "updated_at",
            )
        }
        for row in db.query(ApsContentDocument).all()
    ]
    chunks = [
        {
            key: getattr(row, key)
            for key in (
                "aps_content_chunk_id",
                "content_id",
                "chunk_id",
                "chunk_ordinal",
                "start_char",
                "end_char",
                "chunk_text",
                "chunk_text_sha256",
                "page_start",
                "page_end",
                "unit_kind",
                "quality_status",
                "created_at",
                "updated_at",
            )
        }
        for row in db.query(ApsContentChunk).all()
    ]
    linkages = [
        {
            key: getattr(row, key)
            for key in (
                "aps_content_linkage_id",
                "content_id",
                "run_id",
                "target_id",
                "accession_number",
                "content_contract_id",
                "chunking_contract_id",
                "content_units_ref",
                "normalized_text_ref",
                "normalized_text_sha256",
                "blob_ref",
                "blob_sha256",
                "download_exchange_ref",
                "discovery_ref",
                "selection_ref",
                "diagnostics_ref",
                "created_at",
            )
        }
        for row in db.query(ApsContentLinkage).all()
    ]
    return repr((documents, chunks, linkages))


def test_public_boundary_accepts_only_db_and_target_id() -> None:
    signature = inspect.signature(
        _phase_b().bind_strict_nrc_phase_b_linkage
    )
    assert list(signature.parameters) == [
        "db",
        "connector_run_target_id",
    ]
    assert signature.parameters["connector_run_target_id"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )


def test_completed_strict_target_creates_canonical_linkage(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    calls = _install_parser(monkeypatch)
    assert db.query(ApsContentLinkage).count() == 0

    linkage = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert calls == [
        {"blob_path": raw_path, "expected_sha256": digest}
    ]
    assert db.query(ApsContentDocument).count() == 1
    assert db.query(ApsContentChunk).count() == 1
    assert db.query(ApsContentLinkage).count() == 1
    assert linkage.run_id == run.connector_run_id
    assert linkage.target_id == target.connector_run_target_id
    assert linkage.accession_number == "ML17123A319"
    assert linkage.blob_ref == str(raw_path)
    assert linkage.blob_sha256 == digest
    assert linkage.content_id != digest
    assert linkage.content_contract_id == (
        nrc_aps_content_index.APS_CONTENT_CONTRACT_ID
    )
    assert linkage.chunking_contract_id == (
        nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID
    )
    assert linkage.download_exchange_ref is None
    assert linkage.discovery_ref is None
    assert linkage.selection_ref is None
    db.refresh(run)
    db.refresh(target)
    assert run.ingested_count == 0
    assert target.status == "downloaded"


def test_exact_rerun_returns_same_row_without_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    _install_parser(monkeypatch)
    first = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    before = _row_snapshot(db)

    second = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert second.aps_content_linkage_id == first.aps_content_linkage_id
    assert _row_snapshot(db) == before


def test_created_linkage_satisfies_existing_receipt_derivation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    _install_parser(monkeypatch)
    linkage = _phase_b().bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )
    monkeypatch.setattr(
        origin,
        "_validate_fresh_live_evidence",
        lambda *args, **kwargs: (
            {"campaign_id": "campaign"},
            {"accession_number": "ML17123A319"},
        ),
    )

    receipt = origin.derive_connector_origin_receipt(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert receipt["connector_run_id"] == run.connector_run_id
    assert receipt["aps_content_linkage_id"] == (
        linkage.aps_content_linkage_id
    )
    assert receipt["content_id"] == linkage.content_id


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("connector_key", "sciencebase_mcs"),
        ("source_system", "not_nrc"),
        ("source_mode", "public_api"),
        ("status", "running"),
    ],
)
def test_wrong_or_incomplete_run_fails_before_parse(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    setattr(run, field, value)
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_run_invalid"
    assert calls == []
    assert db.query(ApsContentLinkage).count() == 0


def test_missing_target_fails_closed(db: Session) -> None:
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id="missing",
        )
    assert excinfo.value.code == "nrc_phase_b_target_not_found"


def test_noncanonical_target_cardinality_fails_before_parse(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, _, _ = _make_strict_state(db)
    db.add(
        ConnectorRunTarget(
            connector_run_target_id="extra-target",
            connector_run_id=run.connector_run_id,
            ordinal=2,
            artifact_surface="files",
            status="downloaded",
        )
    )
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_target_cardinality"
    assert calls == []


def _replace_admission(
    target: ConnectorRunTarget,
    key: str,
    value: object,
) -> None:
    admission = dict(target.source_reference_json)
    admission[key] = value
    target.source_reference_json = admission


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (
            lambda target: setattr(target, "ordinal", 2),
            "nrc_phase_b_target_invalid",
        ),
        (
            lambda target: setattr(target, "status", "ingested"),
            "nrc_phase_b_target_invalid",
        ),
        (
            lambda target: setattr(
                target,
                "stable_release_key",
                "ML00000A000",
            ),
            "nrc_phase_b_target_invalid",
        ),
        (
            lambda target: setattr(
                target,
                "sciencebase_download_uri",
                "https://www.nrc.gov/forbidden.pdf",
            ),
            "nrc_phase_b_url_authority_refused",
        ),
        (
            lambda target: setattr(target, "source_reference_json", {}),
            "nrc_phase_b_admission_invalid",
        ),
        (
            lambda target: _replace_admission(
                target,
                "media_type",
                "text/plain",
            ),
            "nrc_phase_b_admission_invalid",
        ),
        (
            lambda target: _replace_admission(
                target,
                "raw_content_size_bytes",
                1,
            ),
            "nrc_phase_b_admission_invalid",
        ),
        (
            lambda target: _replace_admission(
                target,
                "raw_content_sha256",
                "0" * 64,
            ),
            "nrc_phase_b_admission_invalid",
        ),
    ],
)
def test_target_and_admission_mismatches_fail_before_parse(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
    expected_code: str,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    mutation(target)
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == expected_code
    assert calls == []


def test_outside_root_and_wrong_content_address_path_fail_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"%PDF-outside")
    target.raw_storage_ref = str(outside)
    db.commit()
    calls = _install_parser(monkeypatch)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as outside_error:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert outside_error.value.code == "nrc_phase_b_raw_path_invalid"
    assert calls == []

    _, target, _, digest = _make_strict_state(
        db,
        run_id="second-run",
        target_id="second-target",
    )
    raw_root = Path(settings.connector_raw_dir)
    wrong_path = raw_root / "nrc_adams_aps" / "blobs" / f"{digest}.bin"
    persist_locked_raw_file(
        raw_root,
        wrong_path,
        b"%PDF-1.7\nstrict phase B fixture\n%%EOF",
    )
    target.raw_storage_ref = str(wrong_path)
    db.commit()

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as shape_error:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert shape_error.value.code == "nrc_phase_b_raw_path_invalid"
    assert calls == []


def test_safe_handle_rejection_maps_to_raw_storage_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    phase_b = _phase_b()
    calls = _install_parser(monkeypatch)

    def reject(*args: Any, **kwargs: Any) -> Any:
        raise phase_b.StableRawStorageError("unsafe")

    monkeypatch.setattr(phase_b, "hash_locked_raw_file", reject)
    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_raw_storage_unsafe"
    assert calls == []


def test_post_parse_blob_drift_fails_before_db_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, raw_path, _ = _make_strict_state(db)

    def drift(**kwargs: Any) -> dict[str, Any]:
        raw_path.write_bytes(b"%PDF-drifted")
        return _strict_output()

    _install_parser(monkeypatch, callback=drift)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_raw_drift"
    assert db.query(ApsContentLinkage).count() == 0


def test_post_parse_target_row_drift_fails_before_db_mutation(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)

    def drift(**kwargs: Any) -> dict[str, Any]:
        db.query(ConnectorRunTarget).filter(
            ConnectorRunTarget.connector_run_target_id
            == target.connector_run_target_id
        ).update({"downloaded_sha256": "0" * 64})
        db.commit()
        return _strict_output()

    _install_parser(monkeypatch, callback=drift)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_row_drift"
    assert db.query(ApsContentLinkage).count() == 0


@pytest.mark.parametrize(
    ("mutate", "case_id"),
    [
        (
            lambda output: output.__setitem__(
                "normalized_text_sha256",
                "0" * 64,
            ),
            "claimed_hash",
        ),
        (
            lambda output: output["ordered_units"][1].__setitem__(
                "start_char",
                0,
            ),
            "offset",
        ),
        (
            lambda output: output.__setitem__(
                "visual_page_refs",
                [{"page_number": 1, "ref": "forbidden"}],
            ),
            "visual",
        ),
        (
            lambda output: output.__setitem__(
                "normalization_contract_id",
                "wrong_contract",
            ),
            "contract",
        ),
        (
            lambda output: output["ordered_units"][0].__setitem__(
                "bbox",
                [5.0, 4.0, 1.0, 2.0],
            ),
            "geometry",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_malformed_strict_parser_output_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
    case_id: str,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    output = _strict_output()
    mutate(output)
    _install_parser(monkeypatch, output=output)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert case_id
    assert excinfo.value.code == "nrc_phase_b_parse_projection_invalid"
    assert db.query(ApsContentLinkage).count() == 0


def test_strict_parser_hash_refusal_is_preserved_as_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)

    def refuse(**kwargs: Any) -> dict[str, Any]:
        raise nrc_aps_strict_parse.StrictParseViolation(
            "strict_blob_sha256_mismatch"
        )

    _install_parser(monkeypatch, callback=refuse)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_parse_failed"
    assert db.query(ApsContentLinkage).count() == 0


def test_strict_parser_value_error_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)

    def refuse(**kwargs: Any) -> dict[str, Any]:
        raise ValueError("pdf_open_failed")

    _install_parser(monkeypatch, callback=refuse)
    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )
    assert excinfo.value.code == "nrc_phase_b_parse_failed"
    assert db.query(ApsContentLinkage).count() == 0


def _strict_payload(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_path: Path,
    digest: str,
    output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return (
        nrc_aps_content_index
        .build_strict_content_units_payload_from_processed_output(
            run_id=run.connector_run_id,
            target_id=target.connector_run_target_id,
            accession_number="ML17123A319",
            blob_ref=str(raw_path),
            blob_sha256=digest,
            processed_output=deepcopy(output or _strict_output()),
        )
    )


def _seed_document_projection(
    db: Session,
    payload: dict[str, Any],
    *,
    normalized_char_delta: int = 0,
) -> ApsContentDocument:
    document = ApsContentDocument(
        content_id=payload["content_id"],
        content_contract_id=payload["content_contract_id"],
        chunking_contract_id=payload["chunking_contract_id"],
        normalization_contract_id=payload["normalization_contract_id"],
        normalized_text_sha256=payload["normalized_text_sha256"],
        normalized_char_count=(
            int(payload["normalized_char_count"])
            + normalized_char_delta
        ),
        chunk_count=payload["chunk_count"],
        content_status=payload["content_status"],
        media_type=payload["effective_content_type"],
        document_class=payload["document_class"],
        quality_status=payload["quality_status"],
        page_count=payload["page_count"],
        diagnostics_ref=payload["diagnostics_ref"],
        visual_page_refs_json=json.dumps(payload["visual_page_refs"]),
    )
    db.add(document)
    for chunk in payload["chunks"]:
        db.add(
            ApsContentChunk(
                content_id=payload["content_id"],
                chunk_id=chunk["chunk_id"],
                content_contract_id=payload["content_contract_id"],
                chunking_contract_id=payload["chunking_contract_id"],
                chunk_ordinal=chunk["chunk_ordinal"],
                start_char=chunk["start_char"],
                end_char=chunk["end_char"],
                chunk_text=chunk["chunk_text"],
                chunk_text_sha256=chunk["chunk_text_sha256"],
                page_start=chunk["page_start"],
                page_end=chunk["page_end"],
                unit_kind=chunk["unit_kind"],
                quality_status=payload["quality_status"],
            )
        )
    db.commit()
    return document


def _seed_linkage(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    content_id: str,
    blob_ref: str,
    blob_sha256: str,
) -> ApsContentLinkage:
    row = ApsContentLinkage(
        content_id=content_id,
        run_id=run.connector_run_id,
        target_id=target.connector_run_target_id,
        accession_number="ML17123A319",
        content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        normalized_text_sha256="e" * 64,
        blob_ref=blob_ref,
        blob_sha256=blob_sha256,
    )
    db.add(row)
    db.commit()
    return row


def test_stale_linkage_fails_without_overwrite(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    _install_parser(monkeypatch)
    stale = _seed_linkage(
        db,
        run=run,
        target=target,
        content_id="f" * 64,
        blob_ref=str(raw_path),
        blob_sha256=digest,
    )
    before = _row_snapshot(db)

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_linkage_mismatch"
    db.refresh(stale)
    assert stale.content_id == "f" * 64
    assert _row_snapshot(db) == before


def test_two_run_target_linkages_fail_without_repair(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    _install_parser(monkeypatch)
    _seed_linkage(
        db,
        run=run,
        target=target,
        content_id="e" * 64,
        blob_ref=str(raw_path),
        blob_sha256=digest,
    )
    _seed_linkage(
        db,
        run=run,
        target=target,
        content_id="f" * 64,
        blob_ref=str(raw_path),
        blob_sha256=digest,
    )

    with pytest.raises(
        _phase_b().NrcPhaseBLinkageError
    ) as excinfo:
        _phase_b().bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_linkage_cardinality"
    assert db.query(ApsContentLinkage).count() == 2


def test_mismatching_shared_content_fails_before_generic_upsert(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    output = _strict_output()
    _install_parser(monkeypatch, output=output)
    payload = _strict_payload(
        run=run,
        target=target,
        raw_path=raw_path,
        digest=digest,
        output=output,
    )
    _seed_document_projection(
        db,
        payload,
        normalized_char_delta=1,
    )
    phase_b = _phase_b()
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        lambda *args, **kwargs: pytest.fail(
            "mutable generic upsert reached for mismatching shared state"
        ),
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_shared_content_mismatch"
    assert db.query(ApsContentLinkage).count() == 0


def test_exact_shared_content_is_reused_with_linkage_only(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, target, raw_path, digest = _make_strict_state(db)
    output = _strict_output()
    _install_parser(monkeypatch, output=output)
    payload = _strict_payload(
        run=run,
        target=target,
        raw_path=raw_path,
        digest=digest,
        output=output,
    )
    document = _seed_document_projection(db, payload)
    document_id = document.aps_content_document_id
    chunk_ids = [
        row.aps_content_chunk_id
        for row in db.query(ApsContentChunk).all()
    ]
    document_updated_at = document.updated_at
    phase_b = _phase_b()
    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        lambda *args, **kwargs: pytest.fail(
            "generic upsert must not rewrite exact shared content"
        ),
    )

    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    db.refresh(document)
    assert document.aps_content_document_id == document_id
    assert document.updated_at == document_updated_at
    assert [
        row.aps_content_chunk_id
        for row in db.query(ApsContentChunk).all()
    ] == chunk_ids
    assert linkage.content_id == payload["content_id"]
    assert db.query(ApsContentLinkage).count() == 1


def test_absent_content_uses_canonical_upsert_once(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_upsert = phase_b.nrc_aps_content_index.upsert_content_units_payload
    calls = 0

    def record(*args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        real_upsert(*args, **kwargs)

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        record,
    )

    phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert calls == 1


def test_concurrent_exact_uniqueness_conflict_is_accepted(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_upsert = phase_b.nrc_aps_content_index.upsert_content_units_payload

    def race(*args: Any, **kwargs: Any) -> None:
        real_upsert(*args, **kwargs)
        db.commit()
        raise IntegrityError("insert", {}, RuntimeError("race"))

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        race,
    )

    linkage = phase_b.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=target.connector_run_target_id,
    )

    assert linkage.target_id == target.connector_run_target_id
    assert db.query(ApsContentLinkage).count() == 1


def test_concurrent_nonexact_conflict_fails_closed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, target, _, _ = _make_strict_state(db)
    _install_parser(monkeypatch)
    phase_b = _phase_b()
    real_upsert = phase_b.nrc_aps_content_index.upsert_content_units_payload

    def race(*args: Any, **kwargs: Any) -> None:
        payload = deepcopy(kwargs["payload"])
        payload["blob_sha256"] = "0" * 64
        real_upsert(args[0], payload=payload)
        db.commit()
        raise IntegrityError("insert", {}, RuntimeError("race"))

    monkeypatch.setattr(
        phase_b.nrc_aps_content_index,
        "upsert_content_units_payload",
        race,
    )

    with pytest.raises(phase_b.NrcPhaseBLinkageError) as excinfo:
        phase_b.bind_strict_nrc_phase_b_linkage(
            db,
            connector_run_target_id=target.connector_run_target_id,
        )

    assert excinfo.value.code == "nrc_phase_b_persistence_conflict"
    persisted = db.query(ApsContentLinkage).one()
    assert persisted.blob_sha256 == "0" * 64
