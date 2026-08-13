from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base  # noqa: E402
from app.models import (  # noqa: E402
    ConnectorArtifactAlias,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
    Dataset,
    DatasetExternalIdentity,
    DatasetRow,
    DatasetSourceProvenance,
    DatasetVersion,
    VariableDefinition,
    VariableProfile,
)
from app.models.models import L3ConnectorSourceIntakeRecord  # noqa: E402
from app.services import connectors_sciencebase as sciencebase  # noqa: E402
from app.services import layer3_origin_continuity as origin  # noqa: E402
from app.services import raw_storage_handles as raw_handles  # noqa: E402
from app.services.connector_egress_transport import (  # noqa: E402
    BoundedConnectorResponse,
)
from app.services.sciencebase_connector.contracts import (  # noqa: E402
    SubmissionConflictError,
)


ITEM_ID = "63d1a3c6d34e06fef15006be"
FILE_NAME = "mcs2023-germa_salient.csv"
HYDRATION_URL = (
    f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}?format=json"
)
ARTIFACT_URL = (
    f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}"
)
REDIRECT_URL = (
    f"https://sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}"
)
CSV_BYTES = b"county,value\n001,1\n"
UPSTREAM_SENTINEL = "upstream-object-must-not-persist"
FORBIDDEN_URL_KEYS = {
    "url",
    "uri",
    "downloadUri",
    "sciencebase_item_url",
    "sciencebase_download_uri",
    "alias_url",
    "provider_url",
    "public_url",
    "Location",
}


def _json_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested_key
            for nested_value in value.values()
            for nested_key in _json_keys(nested_value)
        }
    if isinstance(value, list):
        return {
            nested_key
            for nested_value in value
            for nested_key in _json_keys(nested_value)
        }
    return set()


def _envelope() -> dict[str, Any]:
    return {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": "sciencebase_mcs",
        "campaign_id": "7fe33e0a-c0e7-4f8e-9d55-8ba77a01ce23",
        "campaign_fingerprint": "a" * 64,
        "campaign_definition_sha256": "b" * 64,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": "c" * 64,
        "arming_fingerprint": "d" * 64,
        "grant_sha256": "e" * 64,
        "canonical_grant_fingerprint": "f" * 64,
        "code_revision": "1" * 40,
        "max_physical_requests": 3,
        "max_run_bytes": 70 * 1024 * 1024,
        "request_timeout_seconds": 30,
        "min_request_interval_ms": 0,
        "campaign_not_before": "2026-01-01T00:00:00.000000Z",
        "campaign_expires_at": "2027-01-01T00:00:00.000000Z",
        "grant_issued_at": "2026-01-01T00:00:00.000000Z",
        "grant_expires_at": "2027-01-01T00:00:00.000000Z",
    }


@pytest.fixture()
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    session = factory()
    monkeypatch.setattr(sciencebase.settings, "storage_dir", tmp_path)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _running_run(db: Session) -> ConnectorRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ConnectorRun(
        connector_run_id="sciencebase-fresh-run",
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status="running",
        request_config_json={"connector_egress_arming": _envelope()},
        request_fingerprint="d" * 64,
        submission_idempotency_key="egress-arm:sciencebase-test",
        execution_lease_owner="test",
        execution_lease_token="lease-token",
        execution_lease_expires_at=now + timedelta(minutes=5),
    )
    db.add(run)
    db.commit()
    return run


def _unleased_strict_run(
    db: Session,
    *,
    connector_run_id: str,
    status: str,
) -> ConnectorRun:
    run = ConnectorRun(
        connector_run_id=connector_run_id,
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status=status,
        request_config_json={"connector_egress_arming": _envelope()},
        request_fingerprint="d" * 64,
        submission_idempotency_key=f"egress-arm:{connector_run_id}",
    )
    db.add(run)
    db.commit()
    return run


def _response(
    status: int | None,
    body: bytes = b"",
    *,
    media: str = "application/octet-stream",
    locations: tuple[str, ...] = (),
    outcome: str = "completed",
) -> BoundedConnectorResponse:
    return BoundedConnectorResponse(
        outcome_class=outcome,
        response_status=status,
        safe_headers={"content_type": media},
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest() if body else None,
        byte_count=len(body),
        location_values=locations,
        counted_status_header_bytes=32,
        delivered_body_bytes=len(body),
    )


class FakeTransport:
    def __init__(
        self,
        responses: list[BoundedConnectorResponse],
        timeline: list[tuple[Any, ...]],
    ) -> None:
        self.responses = list(responses)
        self.timeline = timeline
        self.calls: list[dict[str, Any]] = []

    def send_once(self, **kwargs: Any) -> BoundedConnectorResponse:
        call = dict(kwargs)
        self.calls.append(call)
        request = call["request"]
        self.timeline.append(
            ("send", call["ordinal"], call["stage"], request.url)
        )
        if not self.responses:
            raise AssertionError("unexpected physical send")
        return self.responses.pop(0)


class _ChangedFileIdentity:
    def __init__(self, original: Any) -> None:
        self._original = original

    @property
    def st_ino(self) -> int:
        return int(self._original.st_ino) + 1

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def _install_seams(
    monkeypatch: pytest.MonkeyPatch,
    timeline: list[tuple[Any, ...]],
) -> None:
    verified_grant = SimpleNamespace(raw_sha256="e" * 64)
    monkeypatch.setattr(
        sciencebase,
        "_resolve_current_sciencebase_egress_authority",
        lambda **kwargs: verified_grant,
    )

    def commit(**kwargs: Any) -> SimpleNamespace:
        raw_url = kwargs["normalized_url"]
        ordinal = kwargs["ordinal"]
        stage = kwargs["stage"]
        timeline.append(("commit", ordinal, stage))
        host = raw_url.split("/", 3)[2].split(":", 1)[0]
        return SimpleNamespace(
            ordinal=ordinal,
            stage=stage,
            normalized_url=raw_url,
            url_sha256=hashlib.sha256(raw_url.encode("ascii")).hexdigest(),
            scheme="https",
            host=host,
            port=443,
            path_rule_id="sciencebase_file_exact_v1",
            query_class="exact_single_f_expected_filename",
        )

    def finalize(**kwargs: Any) -> None:
        run = kwargs["run"]
        timeline.append(
            ("finalize", kwargs["terminal_status"], kwargs["outcome_class"])
        )
        run.status = kwargs["terminal_status"]
        run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.execution_lease_owner = None
        run.execution_lease_token = None
        run.execution_lease_expires_at = run.completed_at
        kwargs["db"].commit()

    monkeypatch.setattr(
        sciencebase, "_commit_sciencebase_derived_arming", commit
    )
    monkeypatch.setattr(
        sciencebase, "_finalize_sciencebase_strict_run", finalize
    )
    for name in (
        "ingest_csv_bytes_to_dataset",
        "profile_dataset_version",
        "recommend_transformations",
    ):
        monkeypatch.setattr(
            sciencebase,
            name,
            lambda *args, _name=name, **kwargs: pytest.fail(
                f"strict raw admission called {_name}"
            ),
        )


def _hydration_body(
    *,
    name: Any = FILE_NAME,
    download_uri: Any = ARTIFACT_URL,
    extra: dict[str, Any] | None = None,
) -> bytes:
    selected: dict[str, Any] = {
        "name": name,
        "downloadUri": download_uri,
    }
    selected.update(extra or {})
    return json.dumps({"files": [selected]}).encode("utf-8")


@pytest.mark.parametrize(
    ("payload", "idempotency_key"),
    [
        ({"connector_egress_arming": _envelope()}, "ordinary"),
        ({"source_mode": " strict_live_egress "}, "ordinary"),
        ({"client_request_id": "egress-arm:client"}, None),
        ({"submission_idempotency_key": "egress-arm:submission"}, None),
        ({"idempotency_key": "egress-arm:payload"}, None),
        ({}, "egress-arm:header"),
    ],
)
def test_generic_submit_rejects_reserved_arming_marker(
    db: Session,
    payload: dict[str, Any],
    idempotency_key: str | None,
) -> None:
    with pytest.raises(SubmissionConflictError):
        sciencebase.submit_connector_run(
            db,
            connector_key="sciencebase_mcs",
            payload=payload,
            idempotency_key=idempotency_key,
        )
    assert db.scalar(select(ConnectorRun)) is None


def test_complete_200_atomically_persists_phase_a_graph(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    transport = FakeTransport(
        [
            _response(
                200,
                _hydration_body(extra={"note": UPSTREAM_SENTINEL}),
                media="application/json",
            ),
            _response(200, CSV_BYTES, media="text/csv"),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    assert timeline == [
        ("send", 1, "item_hydration", HYDRATION_URL),
        ("commit", 2, "artifact"),
        ("send", 2, "artifact", ARTIFACT_URL),
        ("finalize", "completed", "sciencebase_raw_admitted"),
    ]
    assert len(transport.calls) == 2
    for call in transport.calls:
        request = call["request"]
        assert request.method == "GET"
        assert dict(request.headers) == {}
        assert request.body is None
        assert request.credential_audience == "none"

    target = db.scalar(select(ConnectorRunTarget))
    assert target is not None
    digest = hashlib.sha256(CSV_BYTES).hexdigest()
    assert target.sciencebase_item_id == ITEM_ID
    assert target.sciencebase_file_name == FILE_NAME
    assert target.sciencebase_item_url is None
    assert target.sciencebase_download_uri is None
    assert target.downloaded_sha256 == digest
    assert target.status == "downloaded"
    assert target.ingested_at is None
    assert target.profiled_at is None
    assert target.recommended_at is None
    raw_path = Path(target.raw_storage_ref).resolve()
    assert raw_path == (
        Path(sciencebase.settings.connector_raw_dir).resolve()
        / "sha256"
        / f"{digest}.csv"
    )
    assert not (
        Path(sciencebase.settings.storage_dir)
        / "connector-raw"
        / "sha256"
        / f"{digest}.csv"
    ).exists()
    assert raw_path.read_bytes() == CSV_BYTES
    fresh_digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert fresh_digest == digest
    assert ARTIFACT_URL not in json.dumps(target.source_reference_json)
    assert f"f={FILE_NAME}" not in json.dumps(target.source_reference_json)
    assert UPSTREAM_SENTINEL not in json.dumps(target.source_reference_json)
    assert target.source_reference_json["artifact_url_sha256"] == hashlib.sha256(
        ARTIFACT_URL.encode("ascii")
    ).hexdigest()
    assert target.versioning_reason_code == "phase_a_raw_admission_only"

    datasets = list(db.scalars(select(Dataset)))
    versions = list(db.scalars(select(DatasetVersion)))
    provenance_rows = list(db.scalars(select(DatasetSourceProvenance)))
    intake_rows = list(db.scalars(select(L3ConnectorSourceIntakeRecord)))
    assert len(datasets) == len(versions) == len(provenance_rows) == len(intake_rows) == 1
    dataset = datasets[0]
    version = versions[0]
    provenance = provenance_rows[0]
    intake = intake_rows[0]
    assert target.dataset_id == dataset.dataset_id
    assert target.dataset_version_id == version.dataset_version_id
    assert version.dataset_id == dataset.dataset_id
    assert provenance.dataset_version_id == version.dataset_version_id
    assert dataset.source_id is None
    assert dataset.name == "ScienceBase MCS frozen raw artifact"
    assert dataset.description == "Strict Phase-A raw CSV artifact; no semantic ingestion."
    assert dataset.time_column is None
    assert version.parent_version_id is None
    assert version.version_label == "sciencebase_phase_a_raw_v1"
    assert version.version_type == "raw"
    assert version.status == "ready"
    assert version.row_count == 0
    assert version.source_row_count is None
    assert version.dropped_row_count is None
    assert version.notes == "Strict Phase-A raw artifact; no semantic ingestion."
    assert provenance.connector_run_id == run.connector_run_id
    assert provenance.source_mode == run.source_mode
    assert provenance.source_artifact_key == target.source_artifact_key
    assert provenance.sciencebase_item_id == ITEM_ID
    assert provenance.sciencebase_item_url is None
    assert provenance.sciencebase_download_uri is None
    assert provenance.sciencebase_file_name == FILE_NAME
    assert provenance.retrieved_http_json == {
        "response_status": 200,
        "content_size_bytes": len(CSV_BYTES),
        "admitted_media_type": "text/csv",
        "upstream_media_class": "declared_csv_shape",
    }
    assert intake.connector_key == run.connector_key
    assert intake.connector_run_id == run.connector_run_id
    assert intake.connector_run_target_id == target.connector_run_target_id
    assert intake.media_type == "text/csv"
    assert intake.original_filename == FILE_NAME
    assert intake.content_size_bytes == len(CSV_BYTES)
    assert {
        target.downloaded_sha256,
        version.content_hash,
        provenance.downloaded_sha256,
        intake.content_sha256,
        fresh_digest,
    } == {digest}
    assert {
        Path(target.raw_storage_ref).resolve(),
        Path(version.storage_ref).resolve(),
        Path(provenance.raw_storage_ref).resolve(),
        Path(intake.storage_ref).resolve(),
    } == {raw_path}

    stored_json = [
        target.source_reference_json,
        target.permission_snapshot_json,
        provenance.source_reference_json,
        provenance.retrieved_http_json,
        intake.provenance_json,
        intake.downstream_eligibility_json,
        intake.summary_json,
    ]
    assert not FORBIDDEN_URL_KEYS.intersection(
        set().union(*(_json_keys(value) for value in stored_json))
    )
    serialized_json = json.dumps(stored_json, sort_keys=True)
    assert ARTIFACT_URL not in serialized_json
    assert f"f={FILE_NAME}" not in serialized_json
    assert UPSTREAM_SENTINEL not in serialized_json

    loaded_path = origin._raw_storage_path(target.raw_storage_ref)
    loaded_size, loaded_hash = origin._hash_file(loaded_path)
    bindings = origin._load_sciencebase_bindings(
        db,
        run=run,
        target=target,
        raw_sha256=loaded_hash,
        raw_size=loaded_size,
    )
    assert bindings == {
        "dataset_id": dataset.dataset_id,
        "dataset_version_id": version.dataset_version_id,
        "dataset_source_provenance_id": provenance.dataset_source_provenance_id,
        "connector_source_intake_record_id": (
            intake.connector_source_intake_record_id
        ),
        "aps_content_linkage_id": None,
        "content_id": None,
    }

    assert db.scalar(select(ConnectorArtifactAlias)) is None
    assert db.scalar(select(DatasetExternalIdentity)) is None
    assert db.scalar(select(DatasetRow)) is None
    assert db.scalar(select(VariableDefinition)) is None
    assert db.scalar(select(VariableProfile)) is None


def test_lease_expiry_after_response_blocks_next_send_and_finalizes_failed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _running_run(db)
    monkeypatch.setattr(
        sciencebase,
        "_resolve_current_sciencebase_egress_authority",
        lambda **kwargs: object(),
    )
    timeline: list[tuple[Any, ...]] = []
    transport = FakeTransport(
        [
            _response(
                200,
                _hydration_body(),
                media="application/json",
            )
        ],
        timeline,
    )
    original_send = transport.send_once

    def send_and_expire(**kwargs: Any) -> BoundedConnectorResponse:
        response = original_send(**kwargs)
        run.execution_lease_expires_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(seconds=1)
        )
        db.commit()
        return response

    monkeypatch.setattr(transport, "send_once", send_and_expire)

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.execution_lease_owner is None
    assert persisted.execution_lease_token is None
    assert len(transport.calls) == 1
    assert db.scalar(select(ConnectorRunTarget)) is None
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id,
                ConnectorRunEvent.event_type == "egress_run_terminal",
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == "failed"
    assert terminal_events[0].reason_code == "connector_strict_lease_expired"


def test_lease_expiry_during_persistence_finalizes_failed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    real_finalizer = sciencebase._finalize_sciencebase_strict_run
    real_persist = sciencebase._persist_fresh_sciencebase_raw_blob
    _install_seams(monkeypatch, timeline)
    monkeypatch.setattr(
        sciencebase,
        "_finalize_sciencebase_strict_run",
        real_finalizer,
    )
    run = _running_run(db)

    def persist_and_expire(body: bytes, digest: str) -> str:
        raw_storage_ref = real_persist(body, digest)
        run.execution_lease_expires_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(seconds=1)
        )
        db.commit()
        return raw_storage_ref

    monkeypatch.setattr(
        sciencebase,
        "_persist_fresh_sciencebase_raw_blob",
        persist_and_expire,
    )
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            _response(200, CSV_BYTES, media="text/csv"),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.execution_lease_owner is None
    assert persisted.execution_lease_token is None
    assert len(transport.calls) == 2
    assert db.scalar(select(DatasetVersion)) is None
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id,
                ConnectorRunEvent.event_type == "egress_run_terminal",
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == "failed"
    assert terminal_events[0].reason_code == "connector_strict_lease_expired"


def test_expiry_before_success_finalizer_allows_completed_terminal(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    real_finalizer = sciencebase._finalize_sciencebase_strict_run
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    expired_now = datetime.now(timezone.utc) + timedelta(hours=1)

    class ExpiredDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return expired_now.replace(tzinfo=None)
            return expired_now.astimezone(tz)

    def expire_before_success(**kwargs: Any) -> None:
        if kwargs["terminal_status"] == "completed":
            monkeypatch.setattr(
                sciencebase,
                "datetime",
                ExpiredDateTime,
            )
        real_finalizer(**kwargs)

    monkeypatch.setattr(
        sciencebase,
        "_finalize_sciencebase_strict_run",
        expire_before_success,
    )
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            _response(200, CSV_BYTES, media="text/csv"),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "completed"
    assert persisted.execution_lease_owner is None
    assert persisted.execution_lease_token is None
    assert len(transport.calls) == 2
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id,
                ConnectorRunEvent.event_type == "egress_run_terminal",
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == "completed"
    assert terminal_events[0].reason_code == "sciencebase_raw_admitted"


def test_one_admitted_redirect_uses_ordinal_three_once(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            _response(302, locations=(REDIRECT_URL,)),
            _response(200, CSV_BYTES, media="application/octet-stream"),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    assert timeline == [
        ("send", 1, "item_hydration", HYDRATION_URL),
        ("commit", 2, "artifact"),
        ("send", 2, "artifact", ARTIFACT_URL),
        ("commit", 3, "artifact_redirect"),
        ("send", 3, "artifact_redirect", REDIRECT_URL),
        ("finalize", "completed", "sciencebase_raw_admitted"),
    ]
    target = db.scalar(select(ConnectorRunTarget))
    assert target is not None
    assert target.redirect_count == 1
    assert target.sciencebase_download_uri is None


@pytest.mark.parametrize(
    "body",
    [
        b'{"files":[]}',
        _hydration_body(name="MCS2023-germa_salient.csv"),
        _hydration_body(name="mcs2023-germa_salient.tsv"),
        _hydration_body(download_uri=""),
        _hydration_body(download_uri=" " + ARTIFACT_URL),
        _hydration_body(download_uri=7),
        _hydration_body(extra={"url": REDIRECT_URL}),
        b'{"files":[],"files":[]}',
        (
            b'{"files":[{"name":"'
            + FILE_NAME.encode("ascii")
            + b'","name":"'
            + FILE_NAME.encode("ascii")
            + b'","downloadUri":"'
            + ARTIFACT_URL.encode("ascii")
            + b'"}]}'
        ),
        (
            b'{"files":[{"name":"'
            + FILE_NAME.encode("ascii")
            + b'","downloadUri":"'
            + ARTIFACT_URL.encode("ascii")
            + b'","downloadUri":"'
            + ARTIFACT_URL.encode("ascii")
            + b'"}]}'
        ),
        b"\xff",
    ],
)
def test_hydration_ambiguity_fails_before_artifact_send(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    transport = FakeTransport(
        [_response(200, body, media="application/json")],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    assert [call["ordinal"] for call in transport.calls] == [1]
    assert not any(item[0] == "commit" for item in timeline)
    assert timeline[-1][0:2] == ("finalize", "failed")
    assert db.scalar(select(ConnectorRunTarget)) is None


@pytest.mark.parametrize(
    "raw_url",
    [
        "http://www.sciencebase.gov/catalog/file/get/"
        f"{ITEM_ID}?f={FILE_NAME}",
        f"https://evil.example/catalog/file/get/{ITEM_ID}?f={FILE_NAME}",
        f"https://WWW.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}",
        f"https://user@www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}",
        f"https://www.sciencebase.gov:444/catalog/file/get/{ITEM_ID}?f={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/%36{ITEM_ID[1:]}?f={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/../get/{ITEM_ID}?f={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}/?f={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?&f={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}&&",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME};",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f{FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}=x",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f=+{FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f=%6dcs2023-germa_salient.csv",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f=%256dcs2023-germa_salient.csv",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}&f={FILE_NAME}",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}&",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}&x=1",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}%20",
        f"https://www.sciencebase.gov/catalog/file/get/{ITEM_ID}?f={FILE_NAME}#",
        " " + ARTIFACT_URL,
        ARTIFACT_URL + "\t",
    ],
)
def test_exact_artifact_url_rejects_raw_ambiguity(raw_url: str) -> None:
    with pytest.raises(sciencebase.ScienceBaseFreshAcquisitionError):
        sciencebase._validate_fresh_sciencebase_url(raw_url)


@pytest.mark.parametrize("raw_url", [ARTIFACT_URL, REDIRECT_URL])
def test_exact_artifact_url_admits_only_two_exact_hosts(raw_url: str) -> None:
    projection = sciencebase._validate_fresh_sciencebase_url(raw_url)
    assert projection["host"] in {"sciencebase.gov", "www.sciencebase.gov"}
    assert projection["path_rule_id"] == "sciencebase_file_exact_v1"
    assert projection["query_class"] == "exact_single_f_expected_filename"


@pytest.mark.parametrize(
    ("status", "locations"),
    [
        (300, (REDIRECT_URL,)),
        (304, (REDIRECT_URL,)),
        (305, (REDIRECT_URL,)),
        (306, (REDIRECT_URL,)),
        (309, (REDIRECT_URL,)),
        (302, ()),
        (302, ("",)),
        (302, (" " + REDIRECT_URL,)),
        (302, (REDIRECT_URL, REDIRECT_URL)),
    ],
)
def test_redirect_guard_never_reserves_ordinal_three(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    locations: tuple[str, ...],
) -> None:
    timeline: list[tuple[Any, ...]] = []
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            _response(status, locations=locations),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    assert [call["ordinal"] for call in transport.calls] == [1, 2]
    assert not any(item[0:2] == ("commit", 3) for item in timeline)
    assert timeline[-1][0:2] == ("finalize", "failed")
    target = db.scalar(select(ConnectorRunTarget))
    assert target is not None
    assert target.status == "download_failed"
    assert target.raw_storage_ref is None
    assert target.sciencebase_download_uri is None


@pytest.mark.parametrize(
    "artifact_response",
    [
        _response(404, b"not found", media="text/plain"),
        _response(206, CSV_BYTES, media="text/csv"),
        _response(200, b"", media="text/csv"),
        _response(200, b"<html>bad</html>", media="text/html"),
        _response(200, b"PK\x03\x04archive", media="application/octet-stream"),
        _response(200, b"%PDF-1.7", media="application/octet-stream"),
        _response(200, b"a,b\n", media="application/octet-stream"),
        _response(
            200,
            b"",
            media="text/csv",
            outcome="oversized",
        ),
    ],
)
def test_artifact_admission_failure_never_persists_raw_target(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    artifact_response: BoundedConnectorResponse,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            artifact_response,
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    assert [call["ordinal"] for call in transport.calls] == [1, 2]
    assert timeline[-1][0:2] == ("finalize", "failed")
    target = db.scalar(select(ConnectorRunTarget))
    assert target is not None
    assert target.status == "download_failed"
    assert target.raw_storage_ref is None
    assert target.downloaded_sha256 is None
    assert target.dataset_id is None
    assert target.dataset_version_id is None
    assert db.scalar(select(Dataset)) is None
    assert db.scalar(select(DatasetVersion)) is None
    assert db.scalar(select(DatasetSourceProvenance)) is None
    assert db.scalar(select(L3ConnectorSourceIntakeRecord)) is None


def test_rehash_drift_rolls_back_entire_phase_a_graph(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)
    real_persist = sciencebase._persist_fresh_sciencebase_raw_blob

    def persist_then_drift(body: bytes, digest: str) -> str:
        raw_storage_ref = real_persist(body, digest)
        Path(raw_storage_ref).write_bytes(b"drifted-after-persist")
        return raw_storage_ref

    monkeypatch.setattr(
        sciencebase,
        "_persist_fresh_sciencebase_raw_blob",
        persist_then_drift,
    )
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            _response(200, CSV_BYTES, media="text/csv"),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted_run = db.get(ConnectorRun, run.connector_run_id)
    target = db.scalar(select(ConnectorRunTarget))
    assert persisted_run is not None
    assert persisted_run.status == "failed"
    assert target is not None
    assert target.status == "download_failed"
    assert target.raw_storage_ref is None
    assert target.downloaded_sha256 is None
    assert target.dataset_id is None
    assert target.dataset_version_id is None
    assert db.scalar(select(Dataset)) is None
    assert db.scalar(select(DatasetVersion)) is None
    assert db.scalar(select(DatasetSourceProvenance)) is None
    assert db.scalar(select(L3ConnectorSourceIntakeRecord)) is None


def test_raw_persist_rejects_parent_reparse_between_checks(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del db
    digest = hashlib.sha256(CSV_BYTES).hexdigest()
    content_dir = (
        Path(sciencebase.settings.connector_raw_dir).resolve()
        / "sha256"
    )
    real_check = sciencebase._path_is_reparse_or_symlink
    content_dir_checks = 0

    def reparse_after_first_check(path: Path) -> bool:
        nonlocal content_dir_checks
        if Path(path).resolve(strict=False) == content_dir:
            content_dir_checks += 1
            return content_dir_checks > 1
        return real_check(path)

    monkeypatch.setattr(
        sciencebase,
        "_path_is_reparse_or_symlink",
        reparse_after_first_check,
    )

    with pytest.raises(
        sciencebase.ScienceBaseFreshAcquisitionError
    ) as excinfo:
        sciencebase._persist_fresh_sciencebase_raw_blob(
            CSV_BYTES,
            digest,
        )

    assert excinfo.value.code == "sciencebase_raw_storage_unsafe"
    assert content_dir_checks >= 2


def test_raw_rehash_rejects_open_handle_identity_swap(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del db
    digest = hashlib.sha256(CSV_BYTES).hexdigest()
    raw_dir = Path(sciencebase.settings.connector_raw_dir) / "sha256"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{digest}.csv"
    raw_path.write_bytes(CSV_BYTES)
    real_fstat = sciencebase.os.fstat
    fstat_calls = 0

    def swapped_fstat(fd: int) -> Any:
        nonlocal fstat_calls
        current = real_fstat(fd)
        fstat_calls += 1
        if fstat_calls >= 2:
            return _ChangedFileIdentity(current)
        return current

    monkeypatch.setattr(sciencebase.os, "fstat", swapped_fstat)

    with pytest.raises(
        sciencebase.ScienceBaseFreshAcquisitionError
    ) as excinfo:
        sciencebase._rehash_fresh_sciencebase_raw_blob(
            str(raw_path),
            expected_digest=digest,
        )

    assert excinfo.value.code == "sciencebase_raw_storage_verification_failed"
    assert fstat_calls >= 2


def test_raw_persist_dispatches_to_capable_posix_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected = (7, "a" * 64, str(tmp_path / "raw" / "blob.csv"))
    calls: list[tuple[Path, Path, bytes]] = []

    def fake_persist(
        raw_root: Path,
        file_path: Path,
        content: bytes,
    ) -> tuple[int, str, str]:
        calls.append((raw_root, file_path, content))
        return expected

    monkeypatch.setattr(
        raw_handles,
        "_windows_backend_available",
        lambda: False,
        raising=False,
    )
    monkeypatch.setattr(
        raw_handles,
        "_supports_posix_anchored_io",
        lambda: True,
        raising=False,
    )
    monkeypatch.setattr(
        raw_handles,
        "_persist_posix_locked_raw_file",
        fake_persist,
        raising=False,
    )
    raw_root = tmp_path / "raw"
    output = raw_root / "blob.csv"

    result = raw_handles.persist_locked_raw_file(
        raw_root,
        output,
        b"content",
    )

    assert result == expected
    assert calls == [(raw_root, output, b"content")]


def test_raw_hash_dispatches_to_capable_posix_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected = (7, "b" * 64, str(tmp_path / "raw" / "blob.csv"))
    calls: list[tuple[Path, Path]] = []

    def fake_hash(
        raw_root: Path,
        file_path: Path,
    ) -> tuple[int, str, str]:
        calls.append((raw_root, file_path))
        return expected

    monkeypatch.setattr(
        raw_handles,
        "_windows_backend_available",
        lambda: False,
        raising=False,
    )
    monkeypatch.setattr(
        raw_handles,
        "_supports_posix_anchored_io",
        lambda: True,
        raising=False,
    )
    monkeypatch.setattr(
        raw_handles,
        "_hash_posix_locked_raw_file",
        fake_hash,
        raising=False,
    )
    raw_root = tmp_path / "raw"
    output = raw_root / "blob.csv"

    result = raw_handles.hash_locked_raw_file(raw_root, output)

    assert result == expected
    assert calls == [(raw_root, output)]


def test_locked_raw_file_round_trip_uses_available_backend(
    tmp_path: Path,
) -> None:
    content = b"posix-content\n"
    raw_root = tmp_path / "raw"
    output = raw_root / "sha256" / "blob.csv"

    persisted = raw_handles.persist_locked_raw_file(
        raw_root,
        output,
        content,
    )
    rehashed = raw_handles.hash_locked_raw_file(raw_root, output)

    assert persisted == rehashed
    assert persisted[0] == len(content)
    assert persisted[1] == hashlib.sha256(content).hexdigest()
    assert output.read_bytes() == content


def test_locked_raw_snapshot_retains_descriptor_through_caller_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    content = b"held-snapshot-content\n"
    raw_root = tmp_path / "raw"
    output = raw_root / "sha256" / "held.bin"
    raw_handles.persist_locked_raw_file(raw_root, output, content)
    captured_fds: list[int] = []
    real_hash_fd = raw_handles._hash_fd

    def capture_hash(fd: int, **kwargs: Any) -> tuple[int, str, bool]:
        captured_fds.append(fd)
        return real_hash_fd(fd, **kwargs)

    monkeypatch.setattr(raw_handles, "_hash_fd", capture_hash)
    with raw_handles.locked_raw_file_snapshot(
        raw_root,
        output,
    ) as snapshot:
        held_fd = captured_fds[0]
        assert os.fstat(held_fd).st_size == len(content)
        assert snapshot.canonical_ref == str(output.resolve(strict=True))
        assert snapshot.size == len(content)
        assert snapshot.sha256 == hashlib.sha256(content).hexdigest()

    with pytest.raises(OSError):
        os.fstat(held_fd)
    assert len(captured_fds) == 2


def test_locked_raw_snapshot_exit_rehash_detects_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    content = b"snapshot-drift-content\n"
    raw_root = tmp_path / "raw"
    output = raw_root / "sha256" / "drift.bin"
    raw_handles.persist_locked_raw_file(raw_root, output, content)
    real_hash_fd = raw_handles._hash_fd
    calls = 0

    def drift_hash(fd: int, **kwargs: Any) -> tuple[int, str, bool]:
        nonlocal calls
        calls += 1
        size, digest, matches = real_hash_fd(fd, **kwargs)
        if calls == 2:
            digest = "0" * 64
        return size, digest, matches

    monkeypatch.setattr(raw_handles, "_hash_fd", drift_hash)
    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        with raw_handles.locked_raw_file_snapshot(raw_root, output):
            pass

    assert excinfo.value.reason == "changed"
    assert calls == 2


@pytest.mark.parametrize(
    "secondary_failure",
    ["exit-validation", "close"],
)
def test_locked_raw_snapshot_preserves_body_error_during_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    secondary_failure: str,
) -> None:
    content = b"primary-error-content\n"
    raw_root = tmp_path / "raw"
    output = raw_root / "sha256" / "primary.bin"
    raw_handles.persist_locked_raw_file(raw_root, output, content)
    real_hash_fd = raw_handles._hash_fd
    real_close = raw_handles.os.close
    held_fd: int | None = None
    hash_calls = 0
    close_failures = 0

    def controlled_hash(
        fd: int,
        **kwargs: Any,
    ) -> tuple[int, str, bool]:
        nonlocal hash_calls, held_fd
        hash_calls += 1
        held_fd = fd
        size, digest, matches = real_hash_fd(fd, **kwargs)
        if secondary_failure == "exit-validation" and hash_calls == 2:
            digest = "0" * 64
        return size, digest, matches

    def controlled_close(fd: int) -> None:
        nonlocal close_failures
        if (
            secondary_failure == "close"
            and fd == held_fd
            and close_failures == 0
        ):
            close_failures += 1
            raise OSError("forced held-descriptor close failure")
        real_close(fd)

    monkeypatch.setattr(raw_handles, "_hash_fd", controlled_hash)
    monkeypatch.setattr(raw_handles.os, "close", controlled_close)
    try:
        with pytest.raises(RuntimeError) as excinfo:
            with raw_handles.locked_raw_file_snapshot(raw_root, output):
                raise RuntimeError("primary persistence failure")
    finally:
        if (
            secondary_failure == "close"
            and held_fd is not None
            and close_failures == 1
        ):
            real_close(held_fd)

    assert str(excinfo.value) == "primary persistence failure"
    assert isinstance(
        excinfo.value.__cause__,
        raw_handles.StableRawStorageError,
    )
    assert any(
        "secondary raw snapshot" in note.lower()
        for note in getattr(excinfo.value, "__notes__", [])
    )


def test_locked_raw_snapshot_preserves_body_error_during_parent_close_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    content = b"parent-close-content\n"
    raw_root = tmp_path / "raw"
    output = raw_root / "sha256" / "parent.bin"
    raw_handles.persist_locked_raw_file(raw_root, output, content)
    failed_parent: list[int] = []
    held_fd: int | None = None

    if raw_handles._windows_backend_available():
        real_parent_close = raw_handles._close_windows_handle

        def fail_parent_close(handle: int) -> None:
            if not failed_parent:
                failed_parent.append(handle)
                raise raw_handles.StableRawStorageError("io")
            real_parent_close(handle)

        monkeypatch.setattr(
            raw_handles,
            "_close_windows_handle",
            fail_parent_close,
        )
    else:
        real_hash_fd = raw_handles._hash_fd
        real_parent_close = raw_handles.os.close

        def capture_fd(
            fd: int,
            **kwargs: Any,
        ) -> tuple[int, str, bool]:
            nonlocal held_fd
            held_fd = fd
            return real_hash_fd(fd, **kwargs)

        def fail_parent_close(fd: int) -> None:
            if fd != held_fd and not failed_parent:
                failed_parent.append(fd)
                raise OSError("forced parent close failure")
            real_parent_close(fd)

        monkeypatch.setattr(raw_handles, "_hash_fd", capture_fd)
        monkeypatch.setattr(
            raw_handles.os,
            "close",
            fail_parent_close,
        )

    try:
        with pytest.raises(RuntimeError) as excinfo:
            with raw_handles.locked_raw_file_snapshot(raw_root, output):
                raise RuntimeError("primary persistence failure")
    finally:
        for parent in failed_parent:
            real_parent_close(parent)

    assert failed_parent
    assert str(excinfo.value) == "primary persistence failure"
    assert isinstance(
        excinfo.value.__cause__,
        raw_handles.StableRawStorageError,
    )
    assert any(
        "secondary raw snapshot" in note.lower()
        for note in getattr(excinfo.value, "__notes__", [])
    )


def test_posix_locked_raw_file_rejects_symlink_component(
    tmp_path: Path,
) -> None:
    if not raw_handles._supports_posix_anchored_io():
        assert raw_handles._windows_backend_available()
        return

    raw_root = tmp_path / "raw"
    outside = tmp_path / "outside"
    raw_root.mkdir()
    outside.mkdir()
    os.symlink(
        outside,
        raw_root / "sha256",
        target_is_directory=True,
    )

    with pytest.raises(raw_handles.StableRawStorageError) as excinfo:
        raw_handles.persist_locked_raw_file(
            raw_root,
            raw_root / "sha256" / "blob.csv",
            b"must-not-escape",
        )

    assert excinfo.value.reason == "unsafe"
    assert list(outside.iterdir()) == []


def test_raw_persist_parent_lock_prevents_redirect_swap(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    del db
    if not raw_handles._windows_backend_available():
        assert raw_handles._supports_posix_anchored_io()
        return

    digest = hashlib.sha256(CSV_BYTES).hexdigest()
    content_dir = (
        Path(sciencebase.settings.connector_raw_dir).resolve()
        / "sha256"
    )
    content_dir.mkdir(parents=True, exist_ok=True)
    displaced_dir = content_dir.with_name("sha256-held")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    real_open = raw_handles._open_windows_file_handle
    rename_errors: list[int | None] = []

    def attack_before_child_open(
        path: Path,
        *,
        create_new: bool,
    ) -> int:
        try:
            content_dir.rename(displaced_dir)
        except OSError as exc:
            rename_errors.append(exc.winerror)
        else:
            import _winapi

            _winapi.CreateJunction(str(outside_dir), str(content_dir))
        return real_open(path, create_new=create_new)

    monkeypatch.setattr(
        raw_handles,
        "_open_windows_file_handle",
        attack_before_child_open,
    )

    storage_ref = sciencebase._persist_fresh_sciencebase_raw_blob(
        CSV_BYTES,
        digest,
    )

    assert rename_errors == [32]
    assert Path(storage_ref).read_bytes() == CSV_BYTES
    assert not (outside_dir / f"{digest}.csv").exists()


def test_success_finalizer_failure_rolls_back_staged_graph_then_fails_run(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeline: list[tuple[Any, ...]] = []
    real_finalizer = sciencebase._finalize_sciencebase_strict_run
    _install_seams(monkeypatch, timeline)
    run = _running_run(db)

    def fail_success_finalizer(**kwargs: Any) -> None:
        if kwargs["terminal_status"] == "completed":
            assert kwargs["db"].query(Dataset).count() == 1
            assert kwargs["db"].query(DatasetVersion).count() == 1
            assert kwargs["db"].query(DatasetSourceProvenance).count() == 1
            assert (
                kwargs["db"].query(L3ConnectorSourceIntakeRecord).count() == 1
            )
            raise RuntimeError("forced_success_finalizer_failure")
        real_finalizer(**kwargs)

    monkeypatch.setattr(
        sciencebase,
        "_finalize_sciencebase_strict_run",
        fail_success_finalizer,
    )
    transport = FakeTransport(
        [
            _response(200, _hydration_body(), media="application/json"),
            _response(200, CSV_BYTES, media="text/csv"),
        ],
        timeline,
    )

    sciencebase._execute_fresh_exact_sciencebase_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted_run = db.get(ConnectorRun, run.connector_run_id)
    target = db.scalar(select(ConnectorRunTarget))
    assert persisted_run is not None
    assert persisted_run.status == "failed"
    assert target is not None
    assert target.status == "download_failed"
    assert target.raw_storage_ref is None
    assert target.downloaded_sha256 is None
    assert target.dataset_id is None
    assert target.dataset_version_id is None
    assert db.scalar(select(Dataset)) is None
    assert db.scalar(select(DatasetVersion)) is None
    assert db.scalar(select(DatasetSourceProvenance)) is None
    assert db.scalar(select(L3ConnectorSourceIntakeRecord)) is None
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id,
                ConnectorRunEvent.event_type == "egress_run_terminal",
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == "failed"


class _NonClosingSession:
    def __init__(self, session: Session) -> None:
        self._session = session

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    def close(self) -> None:
        pass


def test_armed_direct_executor_invocation_is_zero_mutation_and_zero_send(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _unleased_strict_run(
        db,
        connector_run_id="sciencebase-armed-direct",
        status="armed",
    )
    monkeypatch.setattr(
        sciencebase,
        "SessionLocal",
        lambda: _NonClosingSession(db),
    )
    monkeypatch.setattr(
        sciencebase,
        "_acquire_lease",
        lambda *args, **kwargs: pytest.fail(
            "armed strict run entered generic lease acquisition"
        ),
    )
    monkeypatch.setattr(
        sciencebase,
        "_build_sciencebase_strict_transport",
        lambda *args, **kwargs: pytest.fail(
            "armed strict run attempted transport construction"
        ),
    )

    sciencebase.execute_connector_run(run.connector_run_id)

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "armed"
    assert persisted.execution_lease_owner is None
    assert persisted.execution_lease_token is None
    assert persisted.execution_lease_expires_at is None
    assert persisted.attempt_number == 0
    assert persisted.started_at is None
    assert db.scalar(select(ConnectorRunEvent)) is None
    assert db.scalar(select(ConnectorRunTarget)) is None


def test_strict_pending_lease_cas_has_one_winner_and_loser_zero_send(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _unleased_strict_run(
        db,
        connector_run_id="sciencebase-pending-cas",
        status="pending",
    )
    stale_loser: Any = SimpleNamespace(
        connector_run_id=run.connector_run_id,
        status="pending",
        cancellation_requested_at=None,
        attempt_number=0,
    )

    winner_token = sciencebase._acquire_strict_sciencebase_run_lease(
        db,
        run=run,
    )
    assert isinstance(winner_token, str)
    assert sciencebase._acquire_strict_sciencebase_run_lease(
        db,
        run=stale_loser,
    ) is None

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "running"
    assert persisted.execution_lease_token == winner_token
    assert persisted.attempt_number == 1
    monkeypatch.setattr(
        sciencebase,
        "SessionLocal",
        lambda: _NonClosingSession(db),
    )
    monkeypatch.setattr(
        sciencebase,
        "_build_sciencebase_strict_transport",
        lambda *args, **kwargs: pytest.fail(
            "strict lease loser attempted transport construction"
        ),
    )

    sciencebase.execute_connector_run(run.connector_run_id)

    db.expire_all()
    after_loser = db.get(ConnectorRun, run.connector_run_id)
    assert after_loser is not None
    assert after_loser.status == "running"
    assert after_loser.execution_lease_token == winner_token
    assert after_loser.attempt_number == 1
    assert db.scalar(select(ConnectorRunEvent)) is None
    assert db.scalar(select(ConnectorRunTarget)) is None


def test_malformed_reserved_provenance_never_enters_generic_executor(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = ConnectorRun(
        connector_run_id="sciencebase-malformed-reserved",
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status="pending",
        request_config_json={
            "connector_egress_arming": {"schema_id": "malformed"}
        },
        request_fingerprint="0" * 64,
        submission_idempotency_key="egress-arm:malformed",
    )
    db.add(run)
    db.commit()
    monkeypatch.setattr(
        sciencebase,
        "SessionLocal",
        lambda: _NonClosingSession(db),
    )
    monkeypatch.setattr(
        sciencebase,
        "_acquire_lease",
        lambda *args, **kwargs: pytest.fail(
            "malformed reserved run attempted generic lease acquisition"
        ),
    )
    monkeypatch.setattr(
        sciencebase,
        "get_sciencebase_adapter",
        lambda *args, **kwargs: pytest.fail(
            "malformed reserved run entered generic adapter"
        ),
    )

    sciencebase.execute_connector_run(run.connector_run_id)

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_summary == "reserved_egress_provenance_invalid"
    assert db.scalar(select(ConnectorRunTarget)) is None
    events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id
            )
        )
    )
    assert [event.event_type for event in events] == [
        "reserved_egress_provenance_rejected"
    ]
    assert events[0].metrics_json == {"generic_execution_entered": False}


def test_reserved_run_rejects_generic_resume_and_cancel(db: Session) -> None:
    run = _running_run(db)
    with pytest.raises(SubmissionConflictError):
        sciencebase.request_resume_run(db, run.connector_run_id)
    with pytest.raises(SubmissionConflictError):
        sciencebase.request_cancel_run(db, run.connector_run_id)
    db.refresh(run)
    assert run.status == "running"
    assert run.resume_count == 0
    assert run.cancellation_requested_at is None
    assert db.scalar(select(ConnectorRunEvent)) is None


def test_public_strict_finalizer_is_single_use_and_releases_lease(
    db: Session,
) -> None:
    run = _running_run(db)
    sciencebase._finalize_sciencebase_strict_run(
        db=db,
        run=run,
        lease_token="lease-token",
        terminal_status="completed",
        outcome_class="sciencebase_raw_admitted",
    )
    db.refresh(run)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.execution_lease_owner is None
    assert run.execution_lease_token is None
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id,
                ConnectorRunEvent.event_type == "egress_run_terminal",
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == "completed"
    completed_at = run.completed_at

    with pytest.raises(
        sciencebase.connector_egress_arming.ConnectorEgressArmingError
    ):
        sciencebase._finalize_sciencebase_strict_run(
            db=db,
            run=run,
            lease_token="lease-token",
            terminal_status="completed",
            outcome_class="sciencebase_raw_admitted",
        )

    db.refresh(run)
    assert run.status == "completed"
    assert run.completed_at == completed_at
    assert (
        db.query(ConnectorRunEvent)
        .filter(
            ConnectorRunEvent.connector_run_id == run.connector_run_id,
            ConnectorRunEvent.event_type == "egress_run_terminal",
        )
        .count()
        == 1
    )


@pytest.mark.parametrize(
    ("terminal_status", "outcome_class"),
    [
        ("completed", "sciencebase_raw_admitted"),
        ("failed", "connector_strict_lease_expired"),
    ],
)
def test_public_strict_finalizer_accepts_matching_token_after_expiry(
    db: Session,
    terminal_status: str,
    outcome_class: str,
) -> None:
    run = _running_run(db)
    run.execution_lease_expires_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(seconds=1)
    )
    db.commit()

    sciencebase._finalize_sciencebase_strict_run(
        db=db,
        run=run,
        lease_token="lease-token",
        terminal_status=terminal_status,
        outcome_class=outcome_class,
    )

    db.refresh(run)
    assert run.status == terminal_status
    assert run.execution_lease_owner is None
    assert run.execution_lease_token is None
    terminal_events = list(
        db.scalars(
            select(ConnectorRunEvent).where(
                ConnectorRunEvent.connector_run_id == run.connector_run_id,
                ConnectorRunEvent.event_type == "egress_run_terminal",
            )
        )
    )
    assert len(terminal_events) == 1
    assert terminal_events[0].status_after == terminal_status
    assert terminal_events[0].reason_code == outcome_class


def test_hydration_cap_media_and_hash_guards_fail_closed() -> None:
    valid_body = _hydration_body()
    wrong_hash = BoundedConnectorResponse(
        outcome_class="completed",
        response_status=200,
        safe_headers={"content_type": "application/json"},
        body=valid_body,
        body_sha256="0" * 64,
        byte_count=len(valid_body),
        location_values=(),
        counted_status_header_bytes=32,
        delivered_body_bytes=len(valid_body),
    )
    oversized_body = b"{" + b" " * sciencebase.SCIENCEBASE_FRESH_HYDRATION_CAP + b"}"
    guarded = [
        _response(200, valid_body, media="text/plain"),
        wrong_hash,
        _response(200, oversized_body, media="application/json"),
    ]
    for response in guarded:
        with pytest.raises(sciencebase.ScienceBaseFreshAcquisitionError):
            sciencebase._parse_fresh_sciencebase_hydration(response)
