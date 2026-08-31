from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import importlib.util
import inspect as python_inspect
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db  # noqa: E402
from app.core.config import Settings, bootstrap_storage_tree, settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.models import (  # noqa: E402
    ConnectorRun,
    ConnectorRunTarget,
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3Descriptor,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
)
from app.services import layer3_connector_promotion_identity as promotion_identity  # noqa: E402
from app.services import layer3_connector_source_intake as intake_service  # noqa: E402
from app.services.layer3_connector_source_intake import (  # noqa: E402
    ConnectorSourceIntakeError,
    connector_source_intake_inventory,
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
    validate_connector_intake_gate_b_decision_basis,
)
from app.services.layer3_gate_b_state import (  # noqa: E402
    material_candidate_basis_from_decision,
    material_preview_hash,
)
from main import app  # noqa: E402


ALEMBIC_INI = BACKEND / "alembic.ini"
ADOPT_FLAG = "layer3_adopted_external_source_intake_enabled"
PROMOTION_FLAG = "layer3_connector_promotion_identity_enabled"
HANDOFF_FLAG = "layer3_connector_dataset_handoff_enabled"
HANDOFF_ROUTE = "/api/v1/layer3/handoff/connector/dataset"

ADOPT_SOURCE_FAMILY = "adopted_external_single_source"
ADOPT_OPERATOR_DECISION = "record_adopted_external_source"
ADOPT_CONNECTOR_KEY = "sciencebase_adopted_external"
ADOPT_SOURCE_MODE = "adopted_external_artifact"
ADOPT_CANDIDATE_PREFIX = "mat-adopted_source_intake_record-"
ADOPT_INTAKE_MODE = "adopted_external_source_intake"

ITEM_ID = "63d1a3c6d34e06fef15006be"
DOI = "10.5066/P9WCYUI6"
ORIGINAL_FILENAME = "mcs2023-germa_salient.csv"
DOWNLOAD_URI = (
    "https://www.sciencebase.gov/catalog/file/get/"
    "63d1a3c6d34e06fef15006be?f=__disk__7e%2F49%2Fe8%2F"
    "7e49e8a4a53eb2219837f97defb22a25a286cdbc"
)
ACQUIRED_AT = "2026-08-30T17:05:58.459Z"
ACQUISITION_GIT_REF = "codex/sb-instrument-acq@b8839048"
ACQUISITION_RECORD_PATH = "acquisitions/20260830T170556947Z/acquisition-record.json"
DECOY_ACQUISITION_RECORD_PATH = (
    "acquisitions/20990101T000000000Z/acquisition-record.json"
)
ACQUISITION_RECORD_SHA256 = (
    "d49762e1e588841d76583c9dfb59a60fc3634c8d8324ca1c535014db1fc06f1d"
)
ARTIFACT_SHA256 = "c8eacb7b8df0aa12b45eeb383d79d5cf95d7e002dfed7c07736e5aad3dca930c"

ADOPT_BYTES = (
    b"\xef\xbb\xbfDataSource,Commodity,Year,USprod_Primary_kg,USprod_Secondary_kg,"
    b"Imports_Metal_kg,Imports_GeO2_kg,Exports_kg,Shipments_Gov_kg,Consump_kg,"
    b"Price_Metal_dkg,Price_GeO2_dkg,NIR_pct\r\n"
    b"MCS2023,Germanium,2018,0,W,10000,12000,3600,0,30000,1543,1084,>50\r\n"
    b"MCS2023,Germanium,2019,0,W,14000,21000,4500,0,30000,1236,913,>50\r\n"
    b"MCS2023,Germanium,2020,0,W,14000,12000,4800,0,30000,1046,724,>50\r\n"
    b"MCS2023,Germanium,2021,0,W,13000,17000,7500,0,30000,1187,770,>50\r\n"
    b"MCS2023,Germanium,2022,0,W,14000,15000,5800,0,30000,1300,840,>50\r\n"
)

ADOPTION_PROVENANCE = {
    "instrument": "standalone-curl",
    "method": "single unauthenticated HTTPS GET",
    "doi": DOI,
    "acquisition_git_ref": ACQUISITION_GIT_REF,
    "acquisition_record_path": ACQUISITION_RECORD_PATH,
    "acquisition_record_sha256": ACQUISITION_RECORD_SHA256,
    "artifact_sha256": ARTIFACT_SHA256,
    "acquired_at": ACQUIRED_AT,
}

PERMISSION_SNAPSHOT = {
    "license": "CC0-1.0",
    "license_source": "asserted",
    "public_read_confirmed": True,
    "public_read_evidence_source": (
        "standalone-instrument acquisition record, not this run"
    ),
    "acquisition_record_path": ACQUISITION_RECORD_PATH,
    "acquisition_record_sha256": ACQUISITION_RECORD_SHA256,
}

BANNED_ADOPT_TOKENS = (
    "connector_produced_single_source",
    "record_connector_produced_source",
    "sciencebase_public",
)
ADOPT_ORIGIN_LEAKS = (
    "connector_produced_source_intake",
    "connector-produced",
)
EXPECTED_PACKAGE_KINDS = {
    "canonical_internal",
    "review_facing",
    "user_facing",
}
PACKAGE_FACT_FRAGMENTS = (
    "mcs2023 germanium 2018 0 w 10000 12000 3600",
    "mcs2023 germanium 2019 0 w 14000 21000 4500",
    "mcs2023 germanium 2020 0 w 14000 12000 4800",
    "mcs2023 germanium 2021 0 w 13000 17000 7500",
    "mcs2023 germanium 2022 0 w 14000 15000 5800",
    "1543 1084 >50",
    "1236 913 >50",
    "1046 724 >50",
    "1187 770 >50",
    "1300 840 >50",
)
PACKAGE_FACT_ATOMS = {
    "1543",
    "1084",
    "1236",
    "913",
    "1046",
    "724",
    "1187",
    "770",
    "1300",
    "840",
}


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = app_test_client = TestClient(app)
    app_test_client.layer3_session_factory = session_factory
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


@pytest.fixture(autouse=True)
def restore_feature_flags():
    prior = {
        name: (name in settings.__dict__, settings.__dict__.get(name))
        for name in (ADOPT_FLAG, PROMOTION_FLAG, HANDOFF_FLAG)
    }
    try:
        yield
    finally:
        for name, (existed, value) in prior.items():
            if existed:
                settings.__dict__[name] = value
            else:
                settings.__dict__.pop(name, None)


def _set_flag(monkeypatch: pytest.MonkeyPatch, name: str, value: bool) -> None:
    del monkeypatch
    settings.__dict__[name] = value


def _enable_all_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (ADOPT_FLAG, PROMOTION_FLAG, HANDOFF_FLAG):
        _set_flag(monkeypatch, name, True)


def _adopt_recorder():
    recorder = getattr(intake_service, "record_adopted_external_source_intake", None)
    if not callable(recorder):
        pytest.fail(
            "record_adopted_external_source_intake is not implemented; "
            "this is the expected RED feature gap"
        )
    return recorder


def _adoption_basis(provenance: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_family": ADOPT_SOURCE_FAMILY,
        "operator_decision": ADOPT_OPERATOR_DECISION,
        "connector_key": ADOPT_CONNECTOR_KEY,
        "source_mode": ADOPT_SOURCE_MODE,
        "artifact_surface": ADOPT_SOURCE_MODE,
        "sciencebase_item_id": ITEM_ID,
        "sciencebase_file_name": ORIGINAL_FILENAME,
        "sciencebase_download_uri": DOWNLOAD_URI,
        "adoption_provenance": copy.deepcopy(dict(provenance)),
    }


def _write_adopt_blob(stem: str) -> Path:
    assert len(ADOPT_BYTES) == 510
    assert hashlib.sha256(ADOPT_BYTES).hexdigest() == ARTIFACT_SHA256
    raw_path = (
        Path(settings.connector_raw_dir)
        / "adopted"
        / stem
        / ORIGINAL_FILENAME
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(ADOPT_BYTES)
    stored = raw_path.read_bytes()
    assert len(stored) == 510
    assert hashlib.sha256(stored).hexdigest() == ARTIFACT_SHA256
    return raw_path


def _seed_adopt_carrier(
    db: Session,
    *,
    stem: str,
    provenance: Mapping[str, Any] | None = None,
    run_overrides: Mapping[str, Any] | None = None,
    target_overrides: Mapping[str, Any] | None = None,
) -> tuple[ConnectorRun, ConnectorRunTarget, Path, dict[str, Any]]:
    effective_provenance = copy.deepcopy(dict(provenance or ADOPTION_PROVENANCE))
    raw_path = _write_adopt_blob(stem)
    run_values: dict[str, Any] = {
        "connector_run_id": f"{stem}-run",
        "connector_key": ADOPT_CONNECTOR_KEY,
        "source_system": "sciencebase",
        "source_mode": ADOPT_SOURCE_MODE,
        "status": "completed",
        "request_config_json": _adoption_basis(effective_provenance),
        "discovered_count": 1,
        "selected_count": 1,
        "downloaded_count": 1,
        "terminal_target_count": 1,
        "consumed_bytes": len(ADOPT_BYTES),
        "completed_at": datetime.fromisoformat(ACQUIRED_AT.replace("Z", "+00:00")),
    }
    run_values.update(dict(run_overrides or {}))
    run = ConnectorRun(**run_values)
    target_values: dict[str, Any] = {
        "connector_run_target_id": f"{stem}-target",
        "connector_run_id": run.connector_run_id,
        "ordinal": 1,
        "sciencebase_item_id": ITEM_ID,
        "sciencebase_item_url": f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}",
        "sciencebase_file_name": ORIGINAL_FILENAME,
        "sciencebase_download_uri": DOWNLOAD_URI,
        "artifact_surface": ADOPT_SOURCE_MODE,
        "artifact_locator_type": "adopted_storage_ref",
        "source_artifact_key": f"adopted-external://sciencebase/{ITEM_ID}/{ORIGINAL_FILENAME}",
        "downloaded_sha256": ARTIFACT_SHA256,
        "raw_storage_ref": str(raw_path),
        "source_reference_json": {
            "doi": DOI,
            "acquisition_git_ref": ACQUISITION_GIT_REF,
            "acquisition_record_path": ACQUISITION_RECORD_PATH,
            "acquisition_record_sha256": ACQUISITION_RECORD_SHA256,
        },
        "permission_snapshot_json": copy.deepcopy(PERMISSION_SNAPSHOT),
        "access_level_summary": "public-read evidenced by standalone acquisition record",
        "public_read_confirmed": True,
        "status": "downloaded",
        "downloaded_at": datetime.fromisoformat(ACQUIRED_AT.replace("Z", "+00:00")),
    }
    target_values.update(dict(target_overrides or {}))
    target = ConnectorRunTarget(**target_values)
    db.add_all([run, target])
    db.commit()
    return run, target, raw_path, effective_provenance


def _record_adopt(
    db: Session,
    *,
    stem: str,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    provenance: Any,
) -> dict[str, Any]:
    return _adopt_recorder()(
        db,
        client_request_id=f"{stem}-intake",
        connector_key=run.connector_key,
        connector_run_id=run.connector_run_id,
        connector_run_target_id=target.connector_run_target_id,
        source_label="MCS 2023 germanium salient values",
        source_description=(
            "Offline adoption of the owner-authorized standalone-instrument artifact."
        ),
        media_type="text/csv",
        freshness_timestamp=ACQUIRED_AT,
        adoption_provenance=copy.deepcopy(provenance),
    )


def _decision_basis(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(candidate[key])
        for key in (
            "source_ref",
            "query_basis",
            "provenance_ref",
            "source_identity",
            "source_provenance",
            "payload",
            "load_summary",
        )
    }


def _gate_b_payload(preview: Mapping[str, Any], *, stem: str) -> dict[str, Any]:
    candidate = preview["material_candidate"]
    return {
        "client_request_id": f"{stem}-gate-b",
        "preflight_id": f"{stem}-preflight",
        "source_set_id": f"{stem}-source-set",
        "material_preview_id": preview["material_preview_id"],
        "material_preview_hash": preview["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": _decision_basis(candidate),
            }
        ],
    }


def _rehash_gate_b_payload(payload: dict[str, Any]) -> None:
    decision = payload["candidate_decisions"][0]
    decision_basis = decision["decision_basis"]
    payload["material_preview_hash"] = material_preview_hash(
        [
            material_candidate_basis_from_decision(
                candidate_id=decision["candidate_id"],
                source_class=decision_basis["payload"]["source_class"],
                decision_basis=decision_basis,
            )
        ]
    )


def _read_packages(db: Session) -> tuple[list[L3OutputPackage], list[dict[str, Any]]]:
    rows = db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
    payloads = [json.loads(Path(row.payload_ref).read_text(encoding="utf-8")) for row in rows]
    return rows, payloads


def _admit_adopt(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    stem: str,
    perform_handoff: bool = True,
) -> dict[str, Any]:
    _enable_all_flags(monkeypatch)
    with client.layer3_session_factory() as db:
        run, target, raw_path, provenance = _seed_adopt_carrier(db, stem=stem)
        intake_response = _record_adopt(
            db,
            stem=stem,
            run=run,
            target=target,
            provenance=provenance,
        )
        record_id = intake_response["connector_source_intake_record_id"]
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record_id,
        )
        candidate = preview["material_candidate"]
        assert candidate["candidate_id"] == f"{ADOPT_CANDIDATE_PREFIX}{record_id}"
        assert candidate["source_class"] == ADOPT_SOURCE_FAMILY
        assert candidate["payload"]["source_class"] == ADOPT_SOURCE_FAMILY
        validate_connector_intake_gate_b_decision_basis(
            db,
            candidate_id=candidate["candidate_id"],
            decision_basis=_decision_basis(candidate),
        )
        gate_payload = _gate_b_payload(preview, stem=stem)

    gate_response = client.post("/api/v1/layer3/gate-b/decision", json=gate_payload)
    assert gate_response.status_code == 200, gate_response.text
    gate_b = gate_response.json()
    assert gate_b["next_state"] == "connector_source_intake_gate_b_admitted"
    assert gate_b["connector_promotion_receipt"]["receipt_disposition"] == "created"

    replay_response = client.post("/api/v1/layer3/gate-b/decision", json=gate_payload)
    assert replay_response.status_code == 200, replay_response.text
    replay = replay_response.json()
    assert replay["status"] == "already_committed"
    assert replay["connector_promotion_receipt"]["receipt_disposition"] == "reused"
    assert (
        replay["connector_promotion_receipt"]["connector_promotion_receipt_id"]
        == gate_b["connector_promotion_receipt"]["connector_promotion_receipt_id"]
    )

    with client.layer3_session_factory() as db:
        receipts = db.query(L3ConnectorPromotionReceipt).all()
        assert len(receipts) == 1
        receipt = receipts[0]
        assert receipt.source_family == ADOPT_SOURCE_FAMILY
        snapshot = db.get(L3MaterialSnapshot, receipt.gate_b_material_snapshot_id)
        assert snapshot is not None
        assert snapshot.source_shape == ADOPT_SOURCE_FAMILY
        receipt_id = receipt.connector_promotion_receipt_id
        snapshot_id = snapshot.material_snapshot_id

    handoff_body: dict[str, Any] | None = None
    package_payloads: list[dict[str, Any]] = []
    package_ids: list[str] = []
    if perform_handoff:
        handoff_response = client.post(
            HANDOFF_ROUTE,
            json={
                "session_id": gate_b["session_id"],
                "client_request_id": f"{stem}-handoff",
            },
        )
        assert handoff_response.status_code == 200, handoff_response.text
        handoff_body = handoff_response.json()
        assert handoff_body["next_state"] == "connector_dataset_handoff_ready"
        with client.layer3_session_factory() as db:
            assert db.query(L3ReconciliationRecord).count() == 1
            packages, package_payloads = _read_packages(db)
            assert len(packages) == 3
            assert {row.package_kind for row in packages} == EXPECTED_PACKAGE_KINDS
            assert {row.status for row in packages} == {"package_review_only"}
            package_ids = [row.output_package_id for row in packages]

    with client.layer3_session_factory() as db:
        inventory = connector_source_intake_inventory(
            db,
            source_family=ADOPT_SOURCE_FAMILY,
        )

    return {
        "gate_b": gate_b,
        "gate_payload": gate_payload,
        "handoff": handoff_body,
        "intake_response": intake_response,
        "inventory": inventory,
        "package_ids": package_ids,
        "package_payloads": package_payloads,
        "preview": preview,
        "raw_path": raw_path,
        "receipt_id": receipt_id,
        "record_id": record_id,
        "run_id": f"{stem}-run",
        "snapshot_id": snapshot_id,
        "target_id": f"{stem}-target",
    }


def _model_dict(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _recursive_scalar_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if isinstance(value, Mapping):
        scalar_texts: list[str] = []
        for key, child in value.items():
            scalar_texts.extend(_recursive_scalar_texts(key))
            scalar_texts.extend(_recursive_scalar_texts(child))
        return scalar_texts
    if isinstance(value, (list, tuple)):
        scalar_texts = []
        for child in value:
            scalar_texts.extend(_recursive_scalar_texts(child))
        return scalar_texts
    return []


def _normalise_fact_text(value: str) -> str:
    return " ".join(
        value.replace("\ufeff", " ").replace(",", " ").split()
    ).casefold()


def _assert_no_package_fact_leak(payload: Mapping[str, Any]) -> None:
    normalized_values = {
        _normalise_fact_text(value)
        for value in _recursive_scalar_texts(payload)
    }
    for fragment in PACKAGE_FACT_FRAGMENTS:
        assert all(fragment not in value for value in normalized_values), fragment
    assert PACKAGE_FACT_ATOMS.isdisjoint(normalized_values)


def _stable_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _run_alembic(url: str, operation: Any, revision: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    manager = logging.Logger.manager
    disabled_before = {
        name: logger.disabled
        for name, logger in manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    try:
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(BACKEND / "alembic"))
        config.set_main_option("sqlalchemy.url", url)
        operation(config, revision)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        for name, logger in manager.loggerDict.items():
            if isinstance(logger, logging.Logger):
                logger.disabled = disabled_before.get(name, False)


def _intake_insert_values(stem: str, **overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "record_id": f"migration-{stem}",
        "request_id": f"migration-{stem}",
        "operator_decision": ADOPT_OPERATOR_DECISION,
        "source_family": ADOPT_SOURCE_FAMILY,
        "source_label": "migration preservation proof",
        "original_filename": ORIGINAL_FILENAME,
        "media_type": "text/csv",
        "content_size_bytes": len(ADOPT_BYTES),
        "content_sha256": ARTIFACT_SHA256,
        "identity_metadata_hash_version": None,
        "identity_metadata_hash": None,
        "metadata_hash": hashlib.sha256(f"metadata-{stem}".encode()).hexdigest(),
        "authority_basis_hash": hashlib.sha256(f"authority-{stem}".encode()).hexdigest(),
        "storage_ref": f"migration/{stem}/{ORIGINAL_FILENAME}",
        "provenance_json": "{}",
        "downstream_eligibility_json": "{}",
        "summary_json": "{}",
        "status": "recorded",
        "created_at": "2026-08-30T17:05:58.459Z",
        "updated_at": "2026-08-30T17:05:58.459Z",
        "connector_key": ADOPT_CONNECTOR_KEY,
        "connector_run_id": f"migration-{stem}-run",
        "connector_run_target_id": f"migration-{stem}-target",
    }
    values.update(overrides)
    return values


INTAKE_INSERT_SQL = text(
    """
    INSERT INTO l3_connector_source_intake_record (
        connector_source_intake_record_id, client_request_id, operator_decision,
        source_family, source_label, original_filename, media_type,
        content_size_bytes, content_sha256, identity_metadata_hash_version,
        identity_metadata_hash, metadata_hash, authority_basis_hash, storage_ref,
        provenance_json, downstream_eligibility_json, summary_json, status,
        created_at, updated_at, connector_key, connector_run_id,
        connector_run_target_id
    ) VALUES (
        :record_id, :request_id, :operator_decision, :source_family, :source_label,
        :original_filename, :media_type, :content_size_bytes, :content_sha256,
        :identity_metadata_hash_version, :identity_metadata_hash, :metadata_hash,
        :authority_basis_hash, :storage_ref, :provenance_json,
        :downstream_eligibility_json, :summary_json, :status, :created_at,
        :updated_at, :connector_key, :connector_run_id, :connector_run_target_id
    )
    """
)


def _assert_insert_rejected(engine: Any, stem: str, **overrides: Any) -> None:
    connection = engine.connect()
    transaction = connection.begin()
    try:
        with pytest.raises(IntegrityError):
            connection.execute(INTAKE_INSERT_SQL, _intake_insert_values(stem, **overrides))
    finally:
        transaction.rollback()
        connection.close()


def _seed_fk_receipt(engine: Any, *, intake_record_id: str) -> None:
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    with factory() as db:
        db.execute(text("PRAGMA foreign_keys=ON"))
        session = L3Session(
            session_id="migration-fk-session",
            status="active_loading",
            selection_manifest_id="migration-fk-manifest",
            entry_route_context_json={},
            operator_context_json={},
            summary_json={},
        )
        db.add(session)
        db.flush()
        manifest = L3SelectionManifest(
            selection_manifest_id="migration-fk-manifest",
            session_id=session.session_id,
            manifest_json={},
            source_plane_hints_json={},
            selection_hash="2" * 64,
            commit_reason="migration FK preservation proof",
        )
        db.add(manifest)
        db.flush()
        descriptor = L3Descriptor(
            descriptor_id="migration-fk-descriptor",
            session_id=session.session_id,
            selection_manifest_id=manifest.selection_manifest_id,
            source_plane="connector",
            descriptor_type="material_candidate",
            selector_payload_json={},
            selection_basis_json={},
            expansion_reason="migration FK preservation proof",
            status="expanded",
            descriptor_hash="3" * 64,
        )
        db.add(descriptor)
        db.flush()
        snapshot = L3MaterialSnapshot(
            material_snapshot_id="migration-fk-snapshot",
            session_id=session.session_id,
            descriptor_id=descriptor.descriptor_id,
            source_plane="connector",
            source_shape=ADOPT_SOURCE_FAMILY,
            payload_ref="migration/fk/payload.json",
            payload_hash="4" * 64,
            source_identity_json={},
            source_provenance_json={},
            load_summary_json={"loaded_records": 1, "failed_records": 0},
        )
        db.add(snapshot)
        db.flush()
        db.add(
            L3ConnectorPromotionReceipt(
                connector_promotion_receipt_id="migration-fk-receipt",
                receipt_schema_version="layer3.connector_promotion_receipt.v1",
                identity_metadata_hash_version="v1",
                source_family=ADOPT_SOURCE_FAMILY,
                content_sha256=ARTIFACT_SHA256,
                identity_metadata_hash="5" * 64,
                canonical_identity_key_hash="6" * 64,
                connector_source_intake_record_id=intake_record_id,
                gate_b_session_id=session.session_id,
                gate_b_selection_manifest_id=manifest.selection_manifest_id,
                gate_b_material_snapshot_id=snapshot.material_snapshot_id,
                gate_b_decision_manifest_id="migration-fk-decision",
                gate_b_decision_manifest_hash="7" * 64,
                material_preview_hash="8" * 64,
                approval_hash="9" * 64,
                promotion_basis_hash="a" * 64,
            )
        )
        db.commit()


def _admit_connector(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    stem: str,
) -> dict[str, Any]:
    _set_flag(monkeypatch, ADOPT_FLAG, False)
    _set_flag(monkeypatch, PROMOTION_FLAG, True)
    _set_flag(monkeypatch, HANDOFF_FLAG, True)
    connector_bytes = b"site_id,value\nSB-001,42\nSB-002,43\n"
    connector_sha = hashlib.sha256(connector_bytes).hexdigest()
    raw_path = Path(settings.connector_raw_dir) / stem / "water-quality.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(connector_bytes)
    with client.layer3_session_factory() as db:
        run = ConnectorRun(
            connector_run_id=f"{stem}-run",
            connector_key="sciencebase_public",
            source_system="sciencebase",
            source_mode="synthetic_local_direct_intake",
            status="running",
        )
        target = ConnectorRunTarget(
            connector_run_target_id=f"{stem}-target",
            connector_run_id=run.connector_run_id,
            ordinal=1,
            sciencebase_item_id="synthetic-sb-item-001",
            sciencebase_file_name="water-quality.csv",
            artifact_surface="synthetic_fixture",
            artifact_locator_type="intake_storage_ref",
            source_artifact_key=f"{stem}-source-artifact",
            downloaded_sha256=connector_sha,
            raw_storage_ref=str(raw_path),
            public_read_confirmed=True,
            status="downloaded",
        )
        db.add_all([run, target])
        db.commit()
        intake_response = record_connector_produced_source_intake(
            db,
            client_request_id=f"{stem}-intake",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="Synthetic connector CSV",
            source_description="Offline connector nonregression fixture.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=intake_response[
                "connector_source_intake_record_id"
            ],
        )
        payload = _gate_b_payload(preview, stem=stem)

    created_response = client.post("/api/v1/layer3/gate-b/decision", json=payload)
    assert created_response.status_code == 200, created_response.text
    created = created_response.json()
    replay_response = client.post("/api/v1/layer3/gate-b/decision", json=payload)
    assert replay_response.status_code == 200, replay_response.text
    replay = replay_response.json()
    handoff_response = client.post(
        HANDOFF_ROUTE,
        json={
            "session_id": created["session_id"],
            "client_request_id": f"{stem}-handoff",
        },
    )
    assert handoff_response.status_code == 200, handoff_response.text
    with client.layer3_session_factory() as db:
        receipt = db.query(L3ConnectorPromotionReceipt).one()
        packages, payloads = _read_packages(db)
        record = db.get(
            L3ConnectorSourceIntakeRecord,
            intake_response["connector_source_intake_record_id"],
        )
        assert record is not None
        record_values = _model_dict(record)
    return {
        "created": created,
        "handoff": handoff_response.json(),
        "intake_response": intake_response,
        "package_payloads": payloads,
        "package_rows": len(packages),
        "preview": preview,
        "receipt_source_family": receipt.source_family,
        "record": record_values,
        "replay": replay,
    }


def _provenance_view(value: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = value.get("adoption_provenance")
    return nested if isinstance(nested, Mapping) else value


def _assert_required_provenance(value: Mapping[str, Any]) -> None:
    actual = _provenance_view(value)
    for key, expected in ADOPTION_PROVENANCE.items():
        assert actual.get(key) == expected, key


def _write_synthetic_custody(root: Path) -> tuple[Path, str]:
    record_path = root / ACQUISITION_RECORD_PATH
    artifact_name = (
        "mcs2023-germa_salient."
        f"{ARTIFACT_SHA256}.csv"
    )
    artifact_path = root / "acquisitions" / "artifact" / artifact_name
    record = {
        "schema": "project6.instrument-acquisition.v1",
        "doi": DOI,
        "doi_source": "asserted",
        "item_id": ITEM_ID,
        "filename": ORIGINAL_FILENAME,
        "observed_download_uri": DOWNLOAD_URI,
        "license": "CC0-1.0",
        "license_source": "asserted",
        "stages": {
            "download": {
                "url": DOWNLOAD_URI,
                "url_effective": DOWNLOAD_URI,
                "body_bytes": len(ADOPT_BYTES),
                "body_sha256": ARTIFACT_SHA256,
                "ended_at": ACQUIRED_AT,
            }
        },
        "artifact_finalized_name": artifact_name,
        "artifact_sha256": ARTIFACT_SHA256,
        "artifact_bytes": len(ADOPT_BYTES),
    }
    record_bytes = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    record_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)
    artifact_path.write_bytes(ADOPT_BYTES)

    decoy_path = root / DECOY_ACQUISITION_RECORD_PATH
    decoy_path.parent.mkdir(parents=True, exist_ok=True)
    decoy_path.write_text(
        json.dumps(
            {
                **record,
                "item_id": "decoy-item-that-must-not-be-selected",
                "filename": "decoy.csv",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return record_path, hashlib.sha256(record_bytes).hexdigest()


def _load_owner_script():
    script_path = BACKEND / "scripts" / "adopt_external_source_intake.py"
    assert script_path.is_file(), (
        "the offline owner adoption script is absent; this is an expected RED feature gap"
    )
    module_name = "project6_adopt_external_source_intake_contract"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _row_counts(db: Session) -> tuple[int, int, int]:
    return (
        db.query(ConnectorRun).count(),
        db.query(ConnectorRunTarget).count(),
        db.query(L3ConnectorSourceIntakeRecord).count(),
    )


def _mutate_bound_provenance(
    container: Mapping[str, Any],
    *,
    field: str,
    value: str,
) -> dict[str, Any]:
    mutated = copy.deepcopy(dict(container))
    nested = mutated.get("adoption_provenance")
    if isinstance(nested, dict):
        nested[field] = value
    else:
        mutated[field] = value
    return mutated


def test_intake_to_handoff(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(AssertionError):
        _assert_no_package_fact_leak(
            {
                "leaked_germanium_fact": {
                    "year": 2018,
                    "imports_metal_kg": 10000,
                    "price_metal_dkg": 1543,
                    "price_geo2_dkg": 1084,
                }
            }
        )

    admitted = _admit_adopt(client, monkeypatch, stem="adopt-flow")

    assert admitted["raw_path"].is_file()
    assert admitted["raw_path"].read_bytes() == ADOPT_BYTES
    assert admitted["intake_response"]["source_family"] == ADOPT_SOURCE_FAMILY
    assert admitted["intake_response"]["mode"] == ADOPT_INTAKE_MODE
    assert admitted["inventory"]["source_family"] == ADOPT_SOURCE_FAMILY
    assert admitted["inventory"]["inventory_count"] == 1
    assert admitted["handoff"] is not None
    assert admitted["handoff"]["handoff_enabled"] is False

    candidate = admitted["preview"]["material_candidate"]
    assert candidate["candidate_id"] == (
        f"{ADOPT_CANDIDATE_PREFIX}{admitted['record_id']}"
    )
    assert candidate["query_basis"] == ADOPT_INTAKE_MODE
    assert candidate["source_class"] == ADOPT_SOURCE_FAMILY

    with client.layer3_session_factory() as db:
        record = db.get(L3ConnectorSourceIntakeRecord, admitted["record_id"])
        receipt = db.get(L3ConnectorPromotionReceipt, admitted["receipt_id"])
        snapshot = db.get(L3MaterialSnapshot, admitted["snapshot_id"])
        assert record is not None
        assert receipt is not None
        assert snapshot is not None
        assert record.operator_decision == ADOPT_OPERATOR_DECISION
        assert record.source_family == ADOPT_SOURCE_FAMILY
        assert record.content_size_bytes == 510
        assert record.content_sha256 == ARTIFACT_SHA256
        assert receipt.source_family == ADOPT_SOURCE_FAMILY
        assert receipt.content_sha256 == ARTIFACT_SHA256
        assert snapshot.source_shape == ADOPT_SOURCE_FAMILY
        assert db.query(L3ConnectorPromotionReceipt).count() == 1
        assert db.query(L3ReconciliationRecord).count() == 1
        assert db.query(L3OutputPackage).count() == 3

    assert len(admitted["package_payloads"]) == 3
    for payload in admitted["package_payloads"]:
        assert payload["package_header"]["package_status"] == "package_review_only"
        source_summary = payload["connector_source_summary"]
        source_identity = source_summary["source_identity"]
        assert source_identity["candidate_id"] == (
            f"{ADOPT_CANDIDATE_PREFIX}{admitted['record_id']}"
        )
        assert source_identity["source_class"] == ADOPT_SOURCE_FAMILY
        assert source_identity["source_family"] == ADOPT_SOURCE_FAMILY
        _assert_required_provenance(source_summary["source_provenance"])
        _assert_no_package_fact_leak(payload)


def test_honesty_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    mutated_argument_provenance = copy.deepcopy(ADOPTION_PROVENANCE)
    mutated_argument_provenance["artifact_sha256"] = "0" * 64
    direct_argument_cases: list[tuple[str, Any]] = [
        ("missing", None),
        ("malformed", "not-a-provenance-mapping"),
        ("mutated", mutated_argument_provenance),
    ]
    _set_flag(monkeypatch, ADOPT_FLAG, True)
    with client.layer3_session_factory() as db:
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
        for case, argument_provenance in direct_argument_cases:
            run, target, _raw_path, _carrier_provenance = _seed_adopt_carrier(
                db,
                stem=f"direct-provenance-{case}",
            )
            with pytest.raises(
                (ConnectorSourceIntakeError, TypeError, ValueError)
            ):
                _record_adopt(
                    db,
                    stem=f"direct-provenance-{case}",
                    run=run,
                    target=target,
                    provenance=argument_provenance,
                )
            db.rollback()
            assert db.query(L3ConnectorSourceIntakeRecord).count() == 0

    admitted = _admit_adopt(client, monkeypatch, stem="adopt-honest")

    with client.layer3_session_factory() as db:
        run = db.get(ConnectorRun, admitted["run_id"])
        target = db.get(ConnectorRunTarget, admitted["target_id"])
        record = db.get(L3ConnectorSourceIntakeRecord, admitted["record_id"])
        receipt = db.get(L3ConnectorPromotionReceipt, admitted["receipt_id"])
        snapshot = db.get(L3MaterialSnapshot, admitted["snapshot_id"])
        assert run is not None
        assert target is not None
        assert record is not None
        assert receipt is not None
        assert snapshot is not None

        metadata = record.summary_json["metadata"]
        payload_set = {
            "carrier_run": _model_dict(run),
            "carrier_target": _model_dict(target),
            "intake_provenance": record.provenance_json,
            "intake_metadata": metadata,
            "intake_response": admitted["intake_response"],
            "promotion_receipt": _model_dict(receipt),
            "material_snapshot": {
                "source_shape": snapshot.source_shape,
                "source_identity": snapshot.source_identity_json,
                "source_provenance": snapshot.source_provenance_json,
            },
            "output_packages": admitted["package_payloads"],
            "inventory_response": admitted["inventory"],
            "material_preview_response": admitted["preview"],
        }
        serialized = json.dumps(
            payload_set,
            sort_keys=True,
            default=str,
        ).casefold()
        for token in BANNED_ADOPT_TOKENS:
            assert token.casefold() not in serialized

        origin_payloads = json.dumps(
            {
                "intake_response": admitted["intake_response"],
                "intake_provenance": record.provenance_json,
                "material_preview_response": admitted["preview"],
            },
            sort_keys=True,
            default=str,
        ).casefold()
        for leak in ADOPT_ORIGIN_LEAKS:
            assert leak.casefold() not in origin_payloads

        assert run.connector_key == ADOPT_CONNECTOR_KEY
        assert run.source_mode == ADOPT_SOURCE_MODE
        assert run.request_config_json == _adoption_basis(ADOPTION_PROVENANCE)
        assert target.artifact_surface == ADOPT_SOURCE_MODE
        assert target.sciencebase_item_id == ITEM_ID
        assert target.sciencebase_file_name == ORIGINAL_FILENAME
        assert target.sciencebase_download_uri == DOWNLOAD_URI
        assert target.permission_snapshot_json["license"] == "CC0-1.0"
        assert target.permission_snapshot_json["license_source"] == "asserted"
        assert (
            target.permission_snapshot_json["public_read_evidence_source"]
            == "standalone-instrument acquisition record, not this run"
        )
        _assert_required_provenance(record.provenance_json)
        _assert_required_provenance(metadata)
        for payload in admitted["package_payloads"]:
            _assert_required_provenance(
                payload["connector_source_summary"]["source_provenance"]
            )

        swapped_candidate_id = (
            "mat-connector_source_intake_record-"
            f"{record.connector_source_intake_record_id}"
        )
        decision_basis = _decision_basis(admitted["preview"]["material_candidate"])
        with pytest.raises(ConnectorSourceIntakeError):
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=swapped_candidate_id,
                decision_basis=decision_basis,
            )
        with pytest.raises(promotion_identity.ConnectorPromotionIdentityError):
            promotion_identity.derive_candidate_identity(
                db,
                {"candidate_id": swapped_candidate_id},
            )

    def basis_with(**overrides: Any) -> dict[str, Any]:
        basis = _adoption_basis(ADOPTION_PROVENANCE)
        basis.update(overrides)
        return basis

    basis_without_provenance = basis_with()
    basis_without_provenance.pop("adoption_provenance")
    basis_incomplete_provenance = basis_with()
    basis_incomplete_provenance["adoption_provenance"].pop("acquired_at")
    basis_inconsistent_provenance = basis_with()
    basis_inconsistent_provenance["adoption_provenance"]["doi"] = (
        "10.0000/NOT-AUTHORIZED-DOI"
    )
    permission_without_evidence = copy.deepcopy(PERMISSION_SNAPSHOT)
    permission_without_evidence.pop("public_read_evidence_source")

    dishonest_cases: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        ("bad-key", {"connector_key": "sciencebase_public"}, {}),
        ("bad-mode", {"source_mode": "public_api"}, {}),
        ("bad-surface", {}, {"artifact_surface": "files"}),
        ("bad-basis-empty", {"request_config_json": {}}, {}),
        (
            "bad-basis-family",
            {"request_config_json": basis_with(source_family="wrong-family")},
            {},
        ),
        (
            "bad-basis-decision",
            {"request_config_json": basis_with(operator_decision="wrong-decision")},
            {},
        ),
        (
            "bad-basis-key",
            {"request_config_json": basis_with(connector_key="sciencebase_public")},
            {},
        ),
        (
            "bad-basis-mode",
            {"request_config_json": basis_with(source_mode="public_api")},
            {},
        ),
        (
            "bad-basis-surface",
            {"request_config_json": basis_with(artifact_surface="files")},
            {},
        ),
        (
            "bad-basis-item",
            {"request_config_json": basis_with(sciencebase_item_id="wrong-item")},
            {},
        ),
        (
            "bad-basis-file",
            {"request_config_json": basis_with(sciencebase_file_name="wrong.csv")},
            {},
        ),
        (
            "bad-basis-uri",
            {
                "request_config_json": basis_with(
                    sciencebase_download_uri="https://example.invalid/not-authorized"
                )
            },
            {},
        ),
        (
            "bad-basis-provenance-missing",
            {"request_config_json": basis_without_provenance},
            {},
        ),
        (
            "bad-basis-provenance-malformed",
            {"request_config_json": basis_with(adoption_provenance="not-a-mapping")},
            {},
        ),
        (
            "bad-basis-provenance-incomplete",
            {"request_config_json": basis_incomplete_provenance},
            {},
        ),
        (
            "bad-basis-provenance-inconsistent",
            {"request_config_json": basis_inconsistent_provenance},
            {},
        ),
        (
            "bad-permission-license",
            {},
            {
                "permission_snapshot_json": {
                    **PERMISSION_SNAPSHOT,
                    "license": "proprietary",
                }
            },
        ),
        (
            "bad-permission-license-source",
            {},
            {
                "permission_snapshot_json": {
                    **PERMISSION_SNAPSHOT,
                    "license_source": "independently-verified",
                }
            },
        ),
        (
            "bad-permission-public-read",
            {},
            {
                "permission_snapshot_json": {
                    **PERMISSION_SNAPSHOT,
                    "public_read_confirmed": False,
                }
            },
        ),
        (
            "bad-permission-evidence-missing",
            {},
            {"permission_snapshot_json": permission_without_evidence},
        ),
        (
            "bad-permission-evidence-source",
            {},
            {
                "permission_snapshot_json": {
                    **PERMISSION_SNAPSHOT,
                    "public_read_evidence_source": "this Project6 run",
                }
            },
        ),
        ("bad-item", {}, {"sciencebase_item_id": "wrong-item"}),
        ("bad-file", {}, {"sciencebase_file_name": "wrong.csv"}),
        ("bad-target-public-read", {}, {"public_read_confirmed": False}),
        (
            "bad-uri",
            {},
            {"sciencebase_download_uri": "https://example.invalid/not-authorized"},
        ),
    ]
    with client.layer3_session_factory() as db:
        baseline_count = db.query(L3ConnectorSourceIntakeRecord).count()
        for stem, run_overrides, target_overrides in dishonest_cases:
            run, target, _raw_path, provenance = _seed_adopt_carrier(
                db,
                stem=stem,
                run_overrides=run_overrides,
                target_overrides=target_overrides,
            )
            with pytest.raises(ConnectorSourceIntakeError):
                _record_adopt(
                    db,
                    stem=stem,
                    run=run,
                    target=target,
                    provenance=provenance,
                )
            db.rollback()
            assert db.query(L3ConnectorSourceIntakeRecord).count() == baseline_count


def test_flag_off_inertness(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LAYER3_ADOPTED_EXTERNAL_SOURCE_INTAKE_ENABLED", raising=False)
    configured = getattr(
        Settings(_env_file=None),
        ADOPT_FLAG,
        None,
    )
    assert configured is False, "the adopted-external intake flag is absent or not default-off"

    _set_flag(monkeypatch, ADOPT_FLAG, False)
    with client.layer3_session_factory() as db:
        run, target, _raw_path, provenance = _seed_adopt_carrier(
            db,
            stem="adopt-off-mint",
        )
        with pytest.raises(ConnectorSourceIntakeError) as disabled:
            _record_adopt(
                db,
                stem="adopt-off-mint",
                run=run,
                target=target,
                provenance=provenance,
            )
        db.rollback()
        assert disabled.value.code == "adopted_external_source_intake_unavailable"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0

    seeded = _admit_adopt(
        client,
        monkeypatch,
        stem="adopt-preseed",
        perform_handoff=False,
    )
    _set_flag(monkeypatch, ADOPT_FLAG, False)
    _set_flag(monkeypatch, PROMOTION_FLAG, True)
    _set_flag(monkeypatch, HANDOFF_FLAG, True)

    with client.layer3_session_factory() as db:
        with pytest.raises(ConnectorSourceIntakeError) as preview_refusal:
            connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=seeded["record_id"],
            )
        assert "not_admitted" in preview_refusal.value.code

        with pytest.raises(ConnectorSourceIntakeError) as inventory_refusal:
            connector_source_intake_inventory(
                db,
                source_family=ADOPT_SOURCE_FAMILY,
            )
        assert "not_admitted" in inventory_refusal.value.code

        candidate_decision = seeded["gate_payload"]["candidate_decisions"][0]
        with pytest.raises(ConnectorSourceIntakeError) as basis_refusal:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate_decision["candidate_id"],
                decision_basis=candidate_decision["decision_basis"],
            )
        assert "not_admitted" in basis_refusal.value.code

        with pytest.raises(promotion_identity.ConnectorPromotionIdentityError):
            promotion_identity._server_rows(db, seeded["record_id"])

    gate_refusal = client.post(
        "/api/v1/layer3/gate-b/decision",
        json=seeded["gate_payload"],
    )
    assert gate_refusal.status_code == 409, gate_refusal.text

    handoff_refusal = client.post(
        HANDOFF_ROUTE,
        json={
            "session_id": seeded["gate_b"]["session_id"],
            "client_request_id": "adopt-preseed-handoff-off",
        },
    )
    assert handoff_refusal.status_code == 409, handoff_refusal.text
    with client.layer3_session_factory() as db:
        assert db.query(L3ConnectorPromotionReceipt).count() == 1
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_adoption_provenance_hash_bound(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_flag(monkeypatch, ADOPT_FLAG, True)
    _set_flag(monkeypatch, PROMOTION_FLAG, True)
    with client.layer3_session_factory() as db:
        run, target, _raw_path, provenance = _seed_adopt_carrier(
            db,
            stem="adopt-hash",
        )
        response = _record_adopt(
            db,
            stem="adopt-hash",
            run=run,
            target=target,
            provenance=provenance,
        )
        record = db.get(
            L3ConnectorSourceIntakeRecord,
            response["connector_source_intake_record_id"],
        )
        assert record is not None
        metadata = copy.deepcopy(record.summary_json["metadata"])
        authority_basis = copy.deepcopy(record.summary_json["authority_basis"])
        _assert_required_provenance(metadata)
        assert _stable_hash(metadata) == record.metadata_hash
        assert "metadata_hash" in authority_basis
        assert authority_basis["metadata_hash"] == record.metadata_hash
        assert _stable_hash(authority_basis) == record.authority_basis_hash

        mutations = {
            "instrument": "another-instrument",
            "method": "a different acquisition method",
            "doi": "10.0000/DIFFERENT",
            "acquisition_git_ref": "codex/sb-instrument-acq@00000000",
            "acquisition_record_path": "acquisitions/other/acquisition-record.json",
            "acquisition_record_sha256": "0" * 64,
            "artifact_sha256": "1" * 64,
            "acquired_at": "2026-08-30T17:05:59.000Z",
        }
        for field, changed_value in mutations.items():
            changed_metadata = _mutate_bound_provenance(
                metadata,
                field=field,
                value=changed_value,
            )
            changed_metadata_hash = _stable_hash(changed_metadata)
            assert changed_metadata_hash != record.metadata_hash, field
            changed_authority_basis = copy.deepcopy(authority_basis)
            assert changed_authority_basis["metadata_hash"] == record.metadata_hash
            changed_authority_basis["metadata_hash"] = changed_metadata_hash
            if "adoption_provenance" in changed_authority_basis:
                changed_authority_basis = _mutate_bound_provenance(
                    changed_authority_basis,
                    field=field,
                    value=changed_value,
                )
            assert _stable_hash(changed_authority_basis) != record.authority_basis_hash, field
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record.connector_source_intake_record_id,
        )
        clean_gate_payload = _gate_b_payload(preview, stem="adopt-hash-clean")

    tampering_cases = list(mutations.items()) + [
        ("banned_origin_assertion", "connector_produced_single_source")
    ]
    for index, (field, changed_value) in enumerate(tampering_cases):
        tampered = copy.deepcopy(clean_gate_payload)
        tampered["client_request_id"] = f"adopt-hash-tamper-{index}"
        tampered["preflight_id"] = f"adopt-hash-preflight-{index}"
        tampered["source_set_id"] = f"adopt-hash-source-set-{index}"
        source_provenance = tampered["candidate_decisions"][0]["decision_basis"][
            "source_provenance"
        ]
        if field == "banned_origin_assertion":
            source_provenance["origin_assertion"] = changed_value
        else:
            tampered["candidate_decisions"][0]["decision_basis"][
                "source_provenance"
            ] = _mutate_bound_provenance(
                source_provenance,
                field=field,
                value=changed_value,
            )
        _rehash_gate_b_payload(tampered)
        response = client.post("/api/v1/layer3/gate-b/decision", json=tampered)
        assert response.status_code == 409, (field, response.text)
        assert response.json()["error_code"] in {
            "connector_promotion_not_eligible",
            "connector_source_intake_gate_b_source_provenance_mismatch",
        }
        with client.layer3_session_factory() as verify_db:
            assert verify_db.query(L3ConnectorPromotionReceipt).count() == 0
            assert verify_db.query(L3MaterialSnapshot).count() == 0


def test_hash_mismatch_hard_fail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_flag(monkeypatch, ADOPT_FLAG, True)
    with client.layer3_session_factory() as db:
        run, target, raw_path, provenance = _seed_adopt_carrier(
            db,
            stem="adopt-drift",
        )
        assert raw_path.read_bytes() == ADOPT_BYTES
        raw_path.write_bytes(ADOPT_BYTES + b"\n")
        with pytest.raises(ConnectorSourceIntakeError) as mismatch:
            _record_adopt(
                db,
                stem="adopt-drift",
                run=run,
                target=target,
                provenance=provenance,
            )
        db.rollback()
        assert "hash_mismatch" in mismatch.value.code
        assert mismatch.value.http_status == 409
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
        assert db.query(L3ConnectorPromotionReceipt).count() == 0


def test_connector_lane_nonregression(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("LAYER3_ADOPTED_EXTERNAL_SOURCE_INTAKE_ENABLED", raising=False)
    configured = getattr(
        Settings(_env_file=None),
        ADOPT_FLAG,
        None,
    )
    assert configured is False, "the adopted-external feature flag contract is absent"

    result = _admit_connector(client, monkeypatch, stem="connector-legacy")
    assert settings.__dict__[ADOPT_FLAG] is False
    record = result["record"]
    candidate = result["preview"]["material_candidate"]
    assert result["package_rows"] == 3
    assert result["created"]["next_state"] == "connector_source_intake_gate_b_admitted"
    assert result["created"]["connector_promotion_receipt"]["receipt_disposition"] == "created"
    assert result["replay"]["status"] == "already_committed"
    assert result["replay"]["connector_promotion_receipt"]["receipt_disposition"] == "reused"
    assert result["handoff"]["next_state"] == "connector_dataset_handoff_ready"
    assert result["intake_response"]["mode"] == "connector_produced_source_intake"
    assert record["operator_decision"] == "record_connector_produced_source"
    assert record["source_family"] == "connector_produced_single_source"
    assert record["connector_key"] == "sciencebase_public"
    assert candidate["candidate_id"].startswith("mat-connector_source_intake_record-")
    assert candidate["query_basis"] == "connector_produced_source_intake"
    assert candidate["source_class"] == "connector_produced_single_source"
    assert result["receipt_source_family"] == "connector_produced_single_source"
    for payload in result["package_payloads"]:
        source_summary = payload["connector_source_summary"]
        assert source_summary["source_identity"]["candidate_id"].startswith(
            "mat-connector_source_intake_record-"
        )
        assert (
            source_summary["source_identity"]["source_family"]
            == "connector_produced_single_source"
        )
        assert source_summary["source_provenance"]["connector_key"] == "sciencebase_public"
        assert "adoption_provenance" not in source_summary["source_provenance"]

    _set_flag(monkeypatch, ADOPT_FLAG, True)
    swapped_candidate_id = (
        f"{ADOPT_CANDIDATE_PREFIX}{record['connector_source_intake_record_id']}"
    )
    with client.layer3_session_factory() as db:
        with pytest.raises(ConnectorSourceIntakeError):
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=swapped_candidate_id,
                decision_basis=_decision_basis(candidate),
            )
        with pytest.raises(promotion_identity.ConnectorPromotionIdentityError):
            promotion_identity.derive_candidate_identity(
                db,
                {"candidate_id": swapped_candidate_id},
            )


def test_owner_script_accepts_connection_bound_session(client: TestClient):
    owner_script = _load_owner_script()
    with client.layer3_session_factory() as outer_session:
        connection = outer_session.connection()
        with Session(bind=connection) as connection_session:
            raw_root = owner_script._assert_safe_runtime_storage(connection_session)
    assert raw_root == Path(settings.connector_raw_dir).resolve()


def test_owner_script_resolves_exact_mirror_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    owner_script = _load_owner_script()
    source_root = tmp_path / "source-custody"
    source_record, synthetic_record_sha = _write_synthetic_custody(source_root)
    for constant_name in (
        "ACQUISITION_RECORD_SHA256",
        "EXPECTED_ACQUISITION_RECORD_SHA256",
    ):
        monkeypatch.setattr(
            owner_script,
            constant_name,
            synthetic_record_sha,
            raising=False,
        )

    mirror_root = tmp_path / owner_script.EXACT_MIRROR_RUN
    mirror_root.mkdir(parents=True)
    mirror_record = mirror_root / "acquisition-record.json"
    mirror_record.write_bytes(source_record.read_bytes())
    source_artifact = next((source_root / "acquisitions" / "artifact").glob("*.csv"))
    mirror_artifact = mirror_root / source_artifact.name
    mirror_artifact.write_bytes(source_artifact.read_bytes())

    selected_record = owner_script._resolve_acquisition_record(
        mirror_root,
        ACQUISITION_RECORD_PATH,
    )
    parsed_record = owner_script._validated_record(selected_record)
    selected_artifact = owner_script._resolve_artifact(
        mirror_root,
        selected_record,
        parsed_record,
    )
    assert selected_record == mirror_record.resolve()
    assert selected_artifact == mirror_artifact.resolve()


def test_owner_script_core_is_explicit_inert_and_atomic(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    _set_flag(monkeypatch, ADOPT_FLAG, True)
    import_storage = Path(settings.storage_dir)
    import_files_before = {
        path.relative_to(import_storage)
        for path in import_storage.rglob("*")
        if path.is_file()
    }
    with client.layer3_session_factory() as db:
        rows_before = _row_counts(db)

    owner_script = _load_owner_script()
    assert callable(getattr(owner_script, "adopt_external_source_intake", None))
    assert callable(getattr(owner_script, "main", None))
    try:
        help_result = owner_script.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        assert help_result == 0
    with client.layer3_session_factory() as db:
        assert _row_counts(db) == rows_before
    assert {
        path.relative_to(import_storage)
        for path in import_storage.rglob("*")
        if path.is_file()
    } == import_files_before

    custody_root = tmp_path / "custody"
    _record_path, synthetic_record_sha = _write_synthetic_custody(custody_root)
    for constant_name in (
        "ACQUISITION_RECORD_SHA256",
        "EXPECTED_ACQUISITION_RECORD_SHA256",
    ):
        monkeypatch.setattr(
            owner_script,
            constant_name,
            synthetic_record_sha,
            raising=False,
        )
    for constant_name in ("ARTIFACT_SHA256", "EXPECTED_ARTIFACT_SHA256"):
        monkeypatch.setattr(
            owner_script,
            constant_name,
            ARTIFACT_SHA256,
            raising=False,
        )
    adopt = owner_script.adopt_external_source_intake
    adopt_parameters = python_inspect.signature(adopt).parameters
    accepts_record_path = (
        "acquisition_record_path" in adopt_parameters
        or any(
            parameter.kind == python_inspect.Parameter.VAR_KEYWORD
            for parameter in adopt_parameters.values()
        )
    )

    def call_adopt(
        db: Session,
        *,
        custody_root: Path,
        client_request_id: str,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "custody_root": custody_root,
            "client_request_id": client_request_id,
        }
        if accepts_record_path:
            kwargs["acquisition_record_path"] = ACQUISITION_RECORD_PATH
        return adopt(db, **kwargs)

    unsafe_repo_storage = Path(__file__).resolve()
    unsafe_repo_bytes = unsafe_repo_storage.read_bytes()
    unsafe_onedrive_storage = tmp_path / "OneDrive" / "unsafe-storage"
    for case, unsafe_storage in (
        ("repo", unsafe_repo_storage),
        ("onedrive", unsafe_onedrive_storage),
    ):
        monkeypatch.setattr(settings, "storage_dir", str(unsafe_storage))
        with client.layer3_session_factory() as db:
            with pytest.raises(
                (RuntimeError, ValueError),
                match="(?i)(unsafe|storage|repository|repo|onedrive)",
            ):
                call_adopt(
                    db,
                    custody_root=custody_root,
                    client_request_id=f"script-unsafe-{case}",
                )
            db.rollback()
            assert _row_counts(db) == rows_before
        if case == "repo":
            assert unsafe_repo_storage.read_bytes() == unsafe_repo_bytes
        else:
            assert not unsafe_onedrive_storage.exists()

    def set_case_storage(case: str) -> Path:
        storage = tmp_path / case / "storage"
        monkeypatch.setattr(settings, "storage_dir", str(storage))
        bootstrap_storage_tree(storage)
        return (
            Path(settings.connector_raw_dir)
            / "adopted"
            / ARTIFACT_SHA256[:8]
            / ORIGINAL_FILENAME
        )

    flag_off_destination = set_case_storage("flag-off")
    _set_flag(monkeypatch, ADOPT_FLAG, False)
    with client.layer3_session_factory() as db:
        with pytest.raises(ConnectorSourceIntakeError) as disabled:
            call_adopt(
                db,
                custody_root=custody_root,
                client_request_id="script-flag-off",
            )
        db.rollback()
        assert disabled.value.code == "adopted_external_source_intake_unavailable"
        assert _row_counts(db) == rows_before
    assert not flag_off_destination.exists()
    _set_flag(monkeypatch, ADOPT_FLAG, True)

    original_resolve = Path.resolve

    raw_root_destination = set_case_storage("raw-root-escape")
    configured_raw_root = Path(settings.connector_raw_dir)
    outside_raw_root = tmp_path / "outside-raw-root"

    def redirect_raw_root_resolve(path: Path, strict: bool = False) -> Path:
        if path == configured_raw_root:
            return original_resolve(outside_raw_root, strict=strict)
        return original_resolve(path, strict=strict)

    with monkeypatch.context() as raw_root_fault:
        raw_root_fault.setattr(Path, "resolve", redirect_raw_root_resolve)
        with client.layer3_session_factory() as db:
            with pytest.raises(RuntimeError, match="(?i)(outside|escape|storage)"):
                call_adopt(
                    db,
                    custody_root=custody_root,
                    client_request_id="script-raw-root-escape",
                )
            db.rollback()
            assert _row_counts(db) == rows_before
    assert not raw_root_destination.exists()
    assert not outside_raw_root.exists()

    escaped_destination = set_case_storage("resolved-escape")
    outside_destination = tmp_path / "outside-storage" / ORIGINAL_FILENAME

    def redirect_destination_resolve(path: Path, strict: bool = False) -> Path:
        if path == escaped_destination:
            return outside_destination
        return original_resolve(path, strict=strict)

    with monkeypatch.context() as escape_fault:
        escape_fault.setattr(Path, "resolve", redirect_destination_resolve)
        with client.layer3_session_factory() as db:
            with pytest.raises(RuntimeError, match="(?i)(outside|escape|storage)"):
                call_adopt(
                    db,
                    custody_root=custody_root,
                    client_request_id="script-resolved-escape",
                )
            db.rollback()
            assert _row_counts(db) == rows_before
    assert not escaped_destination.exists()
    assert not outside_destination.exists()

    corrupt_custody = tmp_path / "corrupt-custody"
    _write_synthetic_custody(corrupt_custody)
    corrupt_artifact = next((corrupt_custody / "acquisitions" / "artifact").glob("*.csv"))
    corrupt_artifact.write_bytes(ADOPT_BYTES + b"\n")
    pre_copy_destination = set_case_storage("pre-copy")
    with client.layer3_session_factory() as db:
        with pytest.raises(RuntimeError, match="hash|mismatch"):
            call_adopt(
                db,
                custody_root=corrupt_custody,
                client_request_id="script-pre-copy-mismatch",
            )
        db.rollback()
        assert _row_counts(db) == rows_before
    assert not pre_copy_destination.exists()

    mismatch_destination = set_case_storage("existing-mismatch")
    mismatch_destination.parent.mkdir(parents=True, exist_ok=True)
    mismatch_destination.write_bytes(b"do-not-overwrite")
    with client.layer3_session_factory() as db:
        with pytest.raises(RuntimeError, match="destination|hash|mismatch"):
            call_adopt(
                db,
                custody_root=custody_root,
                client_request_id="script-existing-mismatch",
            )
        db.rollback()
        assert _row_counts(db) == rows_before
    assert mismatch_destination.read_bytes() == b"do-not-overwrite"

    post_copy_destination = set_case_storage("post-copy")
    original_read_bytes = Path.read_bytes

    def corrupt_post_copy_read(path: Path) -> bytes:
        data = original_read_bytes(path)
        if path.resolve() == post_copy_destination.resolve():
            return data + b"\n"
        return data

    with monkeypatch.context() as fault:
        fault.setattr(Path, "read_bytes", corrupt_post_copy_read)
        with client.layer3_session_factory() as db:
            with pytest.raises(RuntimeError, match="hash|mismatch"):
                call_adopt(
                    db,
                    custody_root=custody_root,
                    client_request_id="script-post-copy-mismatch",
                )
            db.rollback()
            assert _row_counts(db) == rows_before

    mint_failure_destination = set_case_storage("mint-failure")
    mint_failure_destination.parent.mkdir(parents=True, exist_ok=True)
    mint_failure_destination.write_bytes(ADOPT_BYTES)

    def fail_mint(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("synthetic downstream mint failure")

    with monkeypatch.context() as mint_fault:
        mint_fault.setattr(
            owner_script,
            "record_adopted_external_source_intake",
            fail_mint,
            raising=False,
        )
        mint_fault.setattr(
            intake_service,
            "record_adopted_external_source_intake",
            fail_mint,
            raising=False,
        )
        with client.layer3_session_factory() as db:
            with pytest.raises(
                RuntimeError,
                match="synthetic downstream mint failure",
            ):
                call_adopt(
                    db,
                    custody_root=custody_root,
                    client_request_id="script-mint-failure",
                )
            db.rollback()
            assert _row_counts(db) == rows_before

    reused_destination = set_case_storage("reuse-exact")
    reused_destination.parent.mkdir(parents=True, exist_ok=True)
    reused_destination.write_bytes(ADOPT_BYTES)
    mtime_before = reused_destination.stat().st_mtime_ns
    with client.layer3_session_factory() as db:
        first = call_adopt(
            db,
            custody_root=custody_root,
            client_request_id="script-reuse-one",
        )
        assert first["copy_disposition"] == "reused_exact"
        assert first["acquisition_record_path"] == ACQUISITION_RECORD_PATH
        assert first["content_sha256"] == ARTIFACT_SHA256
        assert Path(first["raw_storage_ref"]) == reused_destination
        assert _row_counts(db) == (1, 1, 1)
        run = db.query(ConnectorRun).one()
        target = db.query(ConnectorRunTarget).one()
        assert target.sciencebase_item_id == ITEM_ID
        assert target.sciencebase_file_name == ORIGINAL_FILENAME
        assert target.sciencebase_download_uri == DOWNLOAD_URI
        assert (
            run.request_config_json["adoption_provenance"][
                "acquisition_record_path"
            ]
            == ACQUISITION_RECORD_PATH
        )
        assert target.source_reference_json["acquisition_record_path"] == (
            ACQUISITION_RECORD_PATH
        )
        selected_outcome = json.dumps(
            {
                "response": first,
                "run": _model_dict(run),
                "target": _model_dict(target),
            },
            sort_keys=True,
            default=str,
        )
        assert DECOY_ACQUISITION_RECORD_PATH not in selected_outcome
        assert "decoy-item-that-must-not-be-selected" not in selected_outcome
        assert "decoy.csv" not in selected_outcome
    assert reused_destination.stat().st_mtime_ns == mtime_before

    with client.layer3_session_factory() as db:
        second = call_adopt(
            db,
            custody_root=custody_root,
            client_request_id="script-reuse-two",
        )
        assert second["copy_disposition"] == "reused_exact"
        assert second["acquisition_record_path"] == ACQUISITION_RECORD_PATH
        assert _row_counts(db) == (2, 2, 2)
        rerun_outcome = json.dumps(
            {
                "response": second,
                "runs": [_model_dict(row) for row in db.query(ConnectorRun).all()],
                "targets": [
                    _model_dict(row) for row in db.query(ConnectorRunTarget).all()
                ],
            },
            sort_keys=True,
            default=str,
        )
        assert DECOY_ACQUISITION_RECORD_PATH not in rerun_outcome
        assert "decoy-item-that-must-not-be-selected" not in rerun_outcome
        assert "decoy.csv" not in rerun_outcome
    assert reused_destination.read_bytes() == ADOPT_BYTES
    assert reused_destination.stat().st_mtime_ns == mtime_before


def test_sqlite_migration_preserves_all_intake_constraints_and_incoming_fk(
    tmp_path: Path,
):
    db_path = tmp_path / "adopt-migration.db"
    url = f"sqlite:///{db_path.as_posix()}"
    _run_alembic(
        url,
        command.upgrade,
        "0057_layer3_b1b_connector_promotion",
    )
    _run_alembic(url, command.upgrade, "head")

    engine = create_engine(url, future=True)
    schema = inspect(engine)
    checks = {
        constraint["name"]: str(constraint["sqltext"])
        for constraint in schema.get_check_constraints(
            "l3_connector_source_intake_record"
        )
    }
    assert set(checks) == {
        "ck_l3_connector_source_intake_operator_decision",
        "ck_l3_connector_source_intake_status",
        "ck_l3_connector_source_intake_identity_metadata_joint_null",
    }
    operator_check = checks["ck_l3_connector_source_intake_operator_decision"]
    assert "record_connector_produced_source" in operator_check
    assert ADOPT_OPERATOR_DECISION in operator_check, (
        "the adopted-external constraint-widening migration is absent"
    )
    status_check = checks["ck_l3_connector_source_intake_status"]
    assert "recorded" in status_check
    assert "already_recorded" in status_check
    joint_null_check = checks[
        "ck_l3_connector_source_intake_identity_metadata_joint_null"
    ]
    assert "identity_metadata_hash_version IS NULL" in joint_null_check
    assert "identity_metadata_hash IS NULL" in joint_null_check
    assert "identity_metadata_hash_version IS NOT NULL" in joint_null_check
    assert "identity_metadata_hash IS NOT NULL" in joint_null_check

    uniques = {
        constraint["name"]
        for constraint in schema.get_unique_constraints(
            "l3_connector_source_intake_record"
        )
    }
    assert uniques == {
        "uq_l3_connector_source_intake_client_request",
        "uq_l3_connector_source_intake_authority_basis",
    }
    indexes = {
        index["name"]
        for index in schema.get_indexes("l3_connector_source_intake_record")
    }
    assert indexes == {
        "ix_l3_connector_intake_material_identity",
        "ix_l3_connector_source_intake_content_sha256",
        "ix_l3_connector_source_intake_run_target",
        "ix_l3_connector_source_intake_source_family",
        "ix_l3_connector_source_intake_status",
    }
    incoming_receipt_fks = {
        (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in schema.get_foreign_keys(
            "l3_connector_promotion_receipt"
        )
    }
    assert (
        ("connector_source_intake_record_id",),
        "l3_connector_source_intake_record",
        ("connector_source_intake_record_id",),
    ) in incoming_receipt_fks

    with engine.begin() as connection:
        connection.execute(
            INTAKE_INSERT_SQL,
            _intake_insert_values("valid-adopt"),
        )
    with engine.connect() as connection:
        stored_decision = connection.execute(
            text(
                "SELECT operator_decision FROM l3_connector_source_intake_record "
                "WHERE connector_source_intake_record_id = 'migration-valid-adopt'"
            )
        ).scalar_one()
    assert stored_decision == ADOPT_OPERATOR_DECISION

    _assert_insert_rejected(
        engine,
        "bad-operator",
        operator_decision="not_an_admitted_decision",
    )
    _assert_insert_rejected(
        engine,
        "bad-status",
        status="not_an_admitted_status",
    )
    _assert_insert_rejected(
        engine,
        "bad-joint-null",
        identity_metadata_hash_version="v1",
        identity_metadata_hash=None,
    )

    _seed_fk_receipt(engine, intake_record_id="migration-valid-adopt")
    connection = engine.connect()
    try:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "DELETE FROM l3_connector_source_intake_record "
                    "WHERE connector_source_intake_record_id = 'migration-valid-adopt'"
                )
            )
        connection.rollback()
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        connection.close()
    engine.dispose()

    with pytest.raises(RuntimeError):
        _run_alembic(
            url,
            command.downgrade,
            "0057_layer3_b1b_connector_promotion",
        )
    preserved = create_engine(url, future=True)
    preserved_checks = {
        constraint["name"]: str(constraint["sqltext"])
        for constraint in inspect(preserved).get_check_constraints(
            "l3_connector_source_intake_record"
        )
    }
    assert ADOPT_OPERATOR_DECISION in preserved_checks[
        "ck_l3_connector_source_intake_operator_decision"
    ]
    with preserved.connect() as connection:
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM l3_connector_source_intake_record "
                "WHERE operator_decision = :decision"
            ),
            {"decision": ADOPT_OPERATOR_DECISION},
        ).scalar_one() == 1
    with preserved.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.execute(
            text(
                "DELETE FROM l3_connector_promotion_receipt "
                "WHERE connector_promotion_receipt_id = 'migration-fk-receipt'"
            )
        )
        connection.execute(
            text(
                "DELETE FROM l3_material_snapshot "
                "WHERE material_snapshot_id = 'migration-fk-snapshot'"
            )
        )
        connection.execute(
            text(
                "DELETE FROM l3_descriptor "
                "WHERE descriptor_id = 'migration-fk-descriptor'"
            )
        )
        connection.execute(
            text(
                "DELETE FROM l3_selection_manifest "
                "WHERE selection_manifest_id = 'migration-fk-manifest'"
            )
        )
        connection.execute(
            text(
                "DELETE FROM l3_session "
                "WHERE session_id = 'migration-fk-session'"
            )
        )
        connection.execute(
            text(
                "DELETE FROM l3_connector_source_intake_record "
                "WHERE connector_source_intake_record_id = 'migration-valid-adopt'"
            )
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    preserved.dispose()

    _run_alembic(
        url,
        command.downgrade,
        "0057_layer3_b1b_connector_promotion",
    )
    downgraded = create_engine(url, future=True)
    downgraded_schema = inspect(downgraded)
    downgraded_checks = {
        constraint["name"]: str(constraint["sqltext"])
        for constraint in downgraded_schema.get_check_constraints(
            "l3_connector_source_intake_record"
        )
    }
    assert ADOPT_OPERATOR_DECISION not in downgraded_checks[
        "ck_l3_connector_source_intake_operator_decision"
    ]
    assert set(downgraded_checks) == set(checks)
    downgraded_operator_check = downgraded_checks[
        "ck_l3_connector_source_intake_operator_decision"
    ]
    assert "record_connector_produced_source" in downgraded_operator_check
    downgraded_status_check = downgraded_checks[
        "ck_l3_connector_source_intake_status"
    ]
    assert "recorded" in downgraded_status_check
    assert "already_recorded" in downgraded_status_check
    downgraded_joint_null_check = downgraded_checks[
        "ck_l3_connector_source_intake_identity_metadata_joint_null"
    ]
    assert "identity_metadata_hash_version IS NULL" in downgraded_joint_null_check
    assert "identity_metadata_hash IS NULL" in downgraded_joint_null_check
    assert "identity_metadata_hash_version IS NOT NULL" in downgraded_joint_null_check
    assert "identity_metadata_hash IS NOT NULL" in downgraded_joint_null_check
    assert {
        constraint["name"]
        for constraint in downgraded_schema.get_unique_constraints(
            "l3_connector_source_intake_record"
        )
    } == uniques
    assert {
        index["name"]
        for index in downgraded_schema.get_indexes(
            "l3_connector_source_intake_record"
        )
    } == indexes
    assert {
        (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in downgraded_schema.get_foreign_keys(
            "l3_connector_promotion_receipt"
        )
    } == incoming_receipt_fks
    _assert_insert_rejected(
        downgraded,
        "downgraded-bad-operator",
        operator_decision="not_an_admitted_decision",
    )
    _assert_insert_rejected(
        downgraded,
        "downgraded-bad-status",
        operator_decision="record_connector_produced_source",
        status="not_an_admitted_status",
    )
    _assert_insert_rejected(
        downgraded,
        "downgraded-bad-joint-null",
        operator_decision="record_connector_produced_source",
        identity_metadata_hash_version="v1",
        identity_metadata_hash=None,
    )
    with downgraded.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    downgraded.dispose()

    _run_alembic(url, command.upgrade, "head")
    round_tripped = create_engine(url, future=True)
    round_trip_schema = inspect(round_tripped)
    round_trip_checks = {
        constraint["name"]: str(constraint["sqltext"])
        for constraint in round_trip_schema.get_check_constraints(
            "l3_connector_source_intake_record"
        )
    }
    assert ADOPT_OPERATOR_DECISION in round_trip_checks[
        "ck_l3_connector_source_intake_operator_decision"
    ]
    assert {
        constraint["name"]
        for constraint in round_trip_schema.get_unique_constraints(
            "l3_connector_source_intake_record"
        )
    } == uniques
    assert {
        index["name"]
        for index in round_trip_schema.get_indexes(
            "l3_connector_source_intake_record"
        )
    } == indexes
    assert {
        (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in round_trip_schema.get_foreign_keys(
            "l3_connector_promotion_receipt"
        )
    } == incoming_receipt_fks
    with round_tripped.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    round_tripped.dispose()
