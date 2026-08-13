from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Generator
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models import (
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
)
from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorEgressArmingIn,
    ConnectorEgressGrantV1,
    DualLiveCampaignDefinitionV1,
    NrcApsFreshTargetV1,
    ScienceBaseFreshTargetV1,
    expected_grant_rule_payloads,
)
from app.services import connectors_nrc_adams as nrc
from app.services.connector_egress_transport import (
    BoundedConnectorResponse,
    BoundedConnectorTransport,
)


def _envelope() -> dict[str, Any]:
    return {
        "schema_id": "project6.connector_egress_arming.v1",
        "arming_fingerprint": "a" * 64,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": "b" * 64,
    }


def _create_real_nrc_arming(
    db: Session,
    tmp_path: Path,
) -> tuple[ConnectorRun, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    campaign_id = "27693345-6a47-45bb-97a7-44c2932ef76b"
    code_revision = "e" * 40
    campaign_fingerprint = "c" * 64
    campaign_raw_sha256 = "d" * 64
    grant_raw_sha256 = "a" * 64
    grant_fingerprint = "b" * 64
    arming_nonce = UUID("ba4613f4-d8e5-4bfd-9447-04d21dbf951b")
    campaign = DualLiveCampaignDefinitionV1(
        schema_id="project6.dual_live_campaign_definition.v1",
        campaign_id=campaign_id,
        code_revision=code_revision,
        connector_keys=("sciencebase_mcs", "nrc_adams_aps"),
        sciencebase_target=ScienceBaseFreshTargetV1(
            connector_key="sciencebase_mcs",
            item_id="63d1a3c6d34e06fef15006be",
            exact_file_name="mcs2023-germa_salient.csv",
            locator_key="downloadUri",
        ),
        nrc_target=NrcApsFreshTargetV1(
            connector_key="nrc_adams_aps",
            accession_number=nrc.NRC_FRESH_ACCESSION,
        ),
        acceptance_profile="dual_live_to_internal_handoff_v1",
        evidence_profile="dual_live_evidence_v1",
        review_policy="security_egress_and_layer3_integrity_v1",
        required_review_roles=("security_egress", "layer3_integrity"),
        execution_order="nrc_then_sciencebase",
        package_kinds=("canonical_internal", "user_facing", "review_facing"),
        not_before=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=1),
        non_authorities=CAMPAIGN_NON_AUTHORITIES,
    )
    grant = ConnectorEgressGrantV1(
        schema_id="project6.connector_egress_grant.v1",
        grant_id="grant-nrc-real-arming",
        connector_key="nrc_adams_aps",
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        campaign_definition_sha256=campaign_raw_sha256,
        code_revision=code_revision,
        arming_nonce=arming_nonce,
        max_armings=1,
        supersedes_grant_sha256=None,
        issued_at=now - timedelta(minutes=30),
        expires_at=now + timedelta(minutes=30),
        operator_mode="local_loopback",
        target=NrcApsFreshTargetV1(
            connector_key="nrc_adams_aps",
            accession_number=nrc.NRC_FRESH_ACCESSION,
        ),
        request_rules=expected_grant_rule_payloads("nrc_adams_aps"),
        max_physical_requests=2,
        max_run_bytes=70 * 1024 * 1024,
        max_single_send_detection_allowance_bytes=6_684_672,
        request_timeout_seconds=30,
        min_request_interval_ms=500,
        non_authorities=NRC_GRANT_NON_AUTHORITIES,
    )
    verified_campaign = SimpleNamespace(
        model=campaign,
        raw_bytes=b"campaign",
        raw_sha256=campaign_raw_sha256,
        canonical_bytes=b"canonical-campaign",
        canonical_fingerprint=campaign_fingerprint,
        introduction_index_revision=1,
        introduction_index_sha256="f" * 64,
        evidence_root=tmp_path,
        definition_archive_path=tmp_path / "definition.json",
        index_chain=(),
    )
    verified_grant = SimpleNamespace(
        model=grant,
        raw_bytes=b"grant",
        raw_sha256=grant_raw_sha256,
        canonical_bytes=b"canonical-grant",
        canonical_fingerprint=grant_fingerprint,
        verified_campaign=verified_campaign,
        grant_archive_path=tmp_path / "grant.json",
        consumption_marker_path=tmp_path / f"{grant_raw_sha256}.json",
        consumption_marker_sha256="",
        consumption_marker_present=False,
    )
    connector_run_id = nrc.connector_egress_arming.compute_parent_arming_id(
        connector_key=grant.connector_key,
        campaign_id=str(grant.campaign_id),
        grant_sha256=grant_raw_sha256,
        arming_nonce=grant.arming_nonce,
    )
    marker_bytes = nrc.connector_egress_arming._marker_bytes(
        verified_grant=verified_grant,
        connector_run_id=connector_run_id,
    )
    verified_grant.consumption_marker_sha256 = hashlib.sha256(
        marker_bytes
    ).hexdigest()
    payload = ConnectorEgressArmingIn(
        schema_id="project6.connector_egress_arming.v1",
        client_request_id="real-nrc-identity",
        connector_key="nrc_adams_aps",
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        grant_sha256=grant_raw_sha256,
    )
    receipt = {
        "schema_id": "project6.connector_egress_authorization_receipt.v1",
        "connector_key": "nrc_adams_aps",
        "campaign_id": campaign_id,
        "campaign_fingerprint": campaign_fingerprint,
        "campaign_definition_sha256": campaign_raw_sha256,
        "grant_sha256": grant_raw_sha256,
        "canonical_grant_fingerprint": grant_fingerprint,
        "introduction_index_revision": 1,
        "introduction_index_sha256": "f" * 64,
        "operator_ref_hash": "1" * 64,
        "workspace_ref_hash": "2" * 64,
        "auth_owner_mode": "header_presence",
        "authorization_mode": "identity_presence",
        "role": None,
        "access": "write",
    }
    run, created = nrc.connector_egress_arming.create_connector_egress_arming(
        db,
        payload=payload,
        verified_grant=verified_grant,
        operator_receipt=receipt,
        code_revision=code_revision,
    )
    assert created is True
    return run, verified_grant


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
    monkeypatch.setattr(nrc.settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(
        nrc.settings,
        "nrc_adams_subscription_key",
        "test-key",
    )
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _running_run(db: Session, *, run_id: str = "strict-nrc") -> ConnectorRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="running",
        submission_idempotency_key="egress-arm:test",
        request_config_json={"connector_egress_arming": _envelope()},
        request_fingerprint="a" * 64,
        execution_lease_owner="test",
        execution_lease_token="lease-token",
        execution_lease_expires_at=now + timedelta(minutes=5),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _response(
    body: bytes,
    *,
    status: int = 200,
    outcome: str = "completed",
    content_type: str | None = None,
    delivered_body_bytes: int | None = None,
) -> BoundedConnectorResponse:
    return BoundedConnectorResponse(
        outcome_class=outcome,
        response_status=status,
        safe_headers=(
            {} if content_type is None else {"content_type": content_type}
        ),
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        location_values=(),
        counted_status_header_bytes=0,
        delivered_body_bytes=(
            len(body)
            if delivered_body_bytes is None
            else delivered_body_bytes
        ),
    )


def _detail_body(url: str = nrc.NRC_FRESH_ARTIFACT_URL) -> bytes:
    return json.dumps(
        {
            "document": {
                "AccessionNumber": nrc.NRC_FRESH_ACCESSION,
                "Url": url,
            }
        },
        separators=(",", ":"),
    ).encode()


class RecordingTransport(BoundedConnectorTransport):
    def __init__(
        self,
        responses: list[BoundedConnectorResponse],
        events: list[str] | None = None,
    ) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.events = events

    def send_once(self, **kwargs: Any) -> BoundedConnectorResponse:
        self.calls.append(kwargs)
        if self.events is not None:
            self.events.append(f"send:{kwargs['ordinal']}")
        return self.responses.pop(0)


def _patch_authority(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str] | None = None,
) -> None:
    verified_grant = object()
    monkeypatch.setattr(
        nrc.connector_egress_arming,
        "resolve_current_egress_authority",
        lambda *args, **kwargs: verified_grant,
    )

    def commit(*args: Any, **kwargs: Any) -> SimpleNamespace:
        if events is not None:
            events.append(f"arm:{kwargs['ordinal']}")
        return SimpleNamespace(
            normalized_url=nrc.NRC_FRESH_ARTIFACT_URL,
            url_sha256=hashlib.sha256(
                nrc.NRC_FRESH_ARTIFACT_URL.encode("ascii")
            ).hexdigest(),
            path_rule_id=nrc.NRC_FRESH_ARTIFACT_PATH_CLASS,
        )

    monkeypatch.setattr(
        nrc.connector_egress_arming,
        "commit_derived_url_arming",
        commit,
    )


def _terminal_event(db: Session, run_id: str) -> ConnectorRunEvent:
    return (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.connector_run_id == run_id)
        .filter(ConnectorRunEvent.event_type == "egress_run_terminal")
        .one()
    )


def test_exact_raw_admission_is_two_sends_sanitized_and_parse_free(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _running_run(db)
    events: list[str] = []
    _patch_authority(monkeypatch, events)
    monkeypatch.setattr(
        nrc,
        "_run_target_artifact_pipeline",
        lambda *args, **kwargs: pytest.fail("generic artifact pipeline called"),
    )
    monkeypatch.setattr(
        nrc,
        "_generate_content_index_artifacts",
        lambda *args, **kwargs: pytest.fail("content index called"),
    )
    pdf = b"%PDF-1.7\nstrict raw source\n%%EOF"
    transport = RecordingTransport(
        [
            _response(_detail_body()),
            _response(pdf, content_type="application/pdf"),
        ],
        events,
    )

    nrc._execute_fresh_exact_nrc_aps_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted_run = db.get(ConnectorRun, run.connector_run_id)
    assert persisted_run is not None
    assert persisted_run.status == "completed"
    assert persisted_run.execution_lease_token is None
    assert events == ["send:1", "arm:2", "send:2"]
    assert len(transport.calls) == 2
    first = transport.calls[0]
    assert (first["ordinal"], first["stage"]) == (
        1,
        nrc.NRC_FRESH_DETAIL_STAGE,
    )
    assert first["request"].method == "GET"
    assert first["request"].url == nrc.NRC_FRESH_DETAIL_URL
    assert first["request"].credential_audience == "nrc_aps_api_key"
    assert first["request"].headers == {
        "Ocp-Apim-Subscription-Key": "test-key"
    }
    second = transport.calls[1]
    assert (second["ordinal"], second["stage"]) == (
        2,
        nrc.NRC_FRESH_ARTIFACT_STAGE,
    )
    assert second["request"].method == "GET"
    assert second["request"].url == nrc.NRC_FRESH_ARTIFACT_URL
    assert second["request"].credential_audience == "none"
    assert second["request"].headers == {}
    assert second["expected_derived_arming_hash"] == hashlib.sha256(
        nrc.NRC_FRESH_ARTIFACT_URL.encode("ascii")
    ).hexdigest()

    target = db.query(ConnectorRunTarget).one()
    assert target.downloaded_sha256 == hashlib.sha256(pdf).hexdigest()
    assert target.raw_storage_ref is not None
    assert Path(target.raw_storage_ref).read_bytes() == pdf
    assert target.sciencebase_item_url is None
    assert target.sciencebase_download_uri is None
    assert target.aliases_json == []
    serialized_safe_projection = json.dumps(
        target.source_reference_json,
        sort_keys=True,
    )
    assert nrc.NRC_FRESH_ARTIFACT_URL not in serialized_safe_projection
    assert "\\/" not in serialized_safe_projection
    assert db.query(ApsContentLinkage).count() == 0
    terminal = _terminal_event(db, run.connector_run_id)
    assert terminal.status_after == "completed"
    assert terminal.reason_code == "nrc_raw_admission_completed"


def test_lease_expiry_after_response_blocks_next_send_and_finalizes_failed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _running_run(db)
    _patch_authority(monkeypatch)
    transport = RecordingTransport([_response(_detail_body())])
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

    nrc._execute_fresh_exact_nrc_aps_run(
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
    assert db.query(ConnectorRunTarget).count() == 0
    terminal = _terminal_event(db, run.connector_run_id)
    assert terminal.status_after == "failed"
    assert terminal.reason_code == "connector_strict_lease_expired"


def test_expiry_before_success_finalizer_allows_completed_terminal(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _running_run(db)
    _patch_authority(monkeypatch)
    real_finalizer = nrc._finalize_strict_nrc_run
    expired_now = datetime.now(timezone.utc) + timedelta(hours=1)

    class ExpiredDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return expired_now.replace(tzinfo=None)
            return expired_now.astimezone(tz)

    def expire_before_success(*args: Any, **kwargs: Any) -> None:
        if kwargs["terminal_status"] == "completed":
            monkeypatch.setattr(
                nrc,
                "datetime",
                ExpiredDateTime,
            )
        real_finalizer(*args, **kwargs)

    monkeypatch.setattr(
        nrc,
        "_finalize_strict_nrc_run",
        expire_before_success,
    )
    pdf = b"%PDF-1.7\nstrict raw source\n%%EOF"
    transport = RecordingTransport(
        [
            _response(_detail_body()),
            _response(pdf, content_type="application/pdf"),
        ]
    )

    nrc._execute_fresh_exact_nrc_aps_run(
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
    assert db.query(ConnectorRunTarget).count() == 1
    terminal = _terminal_event(db, run.connector_run_id)
    assert terminal.status_after == "completed"
    assert terminal.reason_code == "nrc_raw_admission_completed"


@pytest.mark.parametrize(
    "body",
    [
        b"\xff",
        b"{",
        b"[]",
        b'{"document":{"AccessionNumber":"ML17123A319"}}',
        (
            b'{"document":{"AccessionNumber":"ML17123A319",'
            b'"Url":"https://www.nrc.gov/docs/ML1712/ML17123A319.pdf",'
            b'"Url":"https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"}}'
        ),
        (
            b'{"document":{"AccessionNumber":"ML17123A319",'
            b'"Url":"https://www.nrc.gov/docs/ML1712/ML17123A319.pdf",'
            b'"Url":"https://attacker.invalid/file.pdf"}}'
        ),
        (
            b'{"Url":"https://attacker.invalid/file.pdf","document":'
            b'{"AccessionNumber":"ML17123A319",'
            b'"Url":"https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"}}'
        ),
        (
            b'{"document":{"AccessionNumber":"ML00000A000",'
            b'"Url":"https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"}}'
        ),
    ],
)
def test_invalid_or_duplicate_detail_json_stops_before_derived_arming(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
) -> None:
    run = _running_run(db)
    _patch_authority(monkeypatch)
    commit_called = False

    def forbidden_commit(*args: Any, **kwargs: Any) -> None:
        nonlocal commit_called
        commit_called = True
        pytest.fail("derived arming committed for invalid detail JSON")

    monkeypatch.setattr(
        nrc.connector_egress_arming,
        "commit_derived_url_arming",
        forbidden_commit,
    )
    transport = RecordingTransport([_response(body)])
    nrc._execute_fresh_exact_nrc_aps_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert len(transport.calls) == 1
    assert commit_called is False
    assert db.query(ConnectorRunTarget).count() == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://www.nrc.gov/docs/ML1712/ML17123A319.pdf",
        "https://user@www.nrc.gov/docs/ML1712/ML17123A319.pdf",
        "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf?",
        "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf#",
        "https://www.nrc.gov/docs/ML1712/%4dL17123A319.pdf",
        "https://www.nrc.gov/docs/ML1712/../ML1712/ML17123A319.pdf",
        "https://www.nrc.gov\\docs\\ML1712\\ML17123A319.pdf",
        "https://127.0.0.1/docs/ML1712/ML17123A319.pdf",
        "https://www.nrc.gov:443/docs/ML1712/ML17123A319.pdf",
        "HTTPS://WWW.NRC.GOV/docs/ML1712/ML17123A319.pdf",
    ],
)
def test_nonexact_raw_artifact_url_never_reaches_artifact_send(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    run = _running_run(db)
    _patch_authority(monkeypatch)
    transport = RecordingTransport([_response(_detail_body(url))])
    nrc._execute_fresh_exact_nrc_aps_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )
    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert len(transport.calls) == 1
    assert db.query(ConnectorRunTarget).count() == 0


@pytest.mark.parametrize(
    "artifact_response",
    [
        _response(
            b"",
            status=302,
            content_type="application/pdf",
        ),
        _response(
            b"denied",
            status=401,
            content_type="application/pdf",
        ),
        _response(
            b"",
            outcome="oversized",
            content_type="application/pdf",
        ),
        _response(
            b"%PDF-1.7\nx",
            content_type="text/plain",
        ),
        _response(
            b"not-a-pdf",
            content_type="application/octet-stream",
        ),
        _response(
            b"",
            content_type="application/pdf",
        ),
        _response(
            b"%PDF-1.7\nx",
            content_type="application/pdf",
            delivered_body_bytes=1,
        ),
    ],
)
def test_artifact_stop_conditions_finalize_once_without_fallback(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    artifact_response: BoundedConnectorResponse,
) -> None:
    run = _running_run(db)
    events: list[str] = []
    _patch_authority(monkeypatch, events)
    transport = RecordingTransport(
        [_response(_detail_body()), artifact_response],
        events,
    )
    nrc._execute_fresh_exact_nrc_aps_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.execution_lease_token is None
    assert events == ["send:1", "arm:2", "send:2"]
    assert len(transport.calls) == 2
    assert db.query(ConnectorRunTarget).count() == 0
    assert (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.connector_run_id == run.connector_run_id)
        .filter(ConnectorRunEvent.event_type == "egress_run_terminal")
        .count()
        == 1
    )


@pytest.mark.parametrize("status", [401, 403])
def test_api_auth_rejection_stops_without_key_fallback(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    run = _running_run(db)
    _patch_authority(monkeypatch)
    transport = RecordingTransport([_response(b"denied", status=status)])
    nrc._execute_fresh_exact_nrc_aps_run(
        db,
        run=run,
        lease_token="lease-token",
        transport=transport,
    )

    db.expire_all()
    persisted = db.get(ConnectorRun, run.connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert len(transport.calls) == 1
    assert transport.calls[0]["request"].credential_audience == "nrc_aps_api_key"
    assert db.query(ConnectorRunTarget).count() == 0
    assert _terminal_event(db, run.connector_run_id).reason_code == (
        "nrc_strict_api_key_rejected"
    )


def test_pdf_cap_and_guarded_octet_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admitted = _response(
        b"%PDF-1.7\nx",
        content_type="application/octet-stream",
    )
    body, media_type = nrc._strict_pdf_body(admitted)
    assert body == b"%PDF-1.7\nx"
    assert media_type == "application/octet-stream"

    monkeypatch.setattr(nrc, "NRC_FRESH_MAX_PDF_BYTES", 8)
    with pytest.raises(nrc.NrcFreshAdmissionError) as exc:
        nrc._strict_pdf_body(admitted)
    assert exc.value.code == "nrc_strict_artifact_oversized"


class FakeExecutorSession:
    def __init__(self, run: ConnectorRun) -> None:
        self.run = run
        self.added: list[Any] = []
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    def get(self, model: type[Any], identity: str) -> ConnectorRun | None:
        assert model is ConnectorRun
        return self.run if identity == self.run.connector_run_id else None

    def add(self, value: Any) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.close_count += 1


@pytest.mark.parametrize(
    ("payload", "idempotency_key"),
    [
        ({"connector_egress_arming": None}, None),
        ({"source_mode": " STRICT_LIVE_EGRESS "}, None),
        ({}, " egress-arm:header "),
        ({"client_request_id": " egress-arm:client "}, None),
        ({"submission_idempotency_key": "egress-arm:payload"}, None),
    ],
)
def test_generic_submit_rejects_reserved_provenance_before_normalization(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
    idempotency_key: str | None,
) -> None:
    monkeypatch.setattr(
        nrc,
        "_normalize_request_config",
        lambda *args, **kwargs: pytest.fail("reserved payload normalized"),
    )

    with pytest.raises(nrc.SubmissionConflictError) as exc:
        nrc.submit_nrc_adams_run(
            db,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    assert str(exc.value) == (
        "reserved egress provenance requires the protected arming API"
    )
    assert db.query(ConnectorRun).count() == 0


def test_real_arming_identity_reaches_public_executor_with_fake_transport(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, verified_grant = _create_real_nrc_arming(db, tmp_path)
    assert run.source_system == "nrc_adams"
    monkeypatch.setattr(
        nrc.connector_egress_arming,
        "resolve_current_egress_authority",
        lambda *args, **kwargs: verified_grant,
    )
    run, claimed = nrc.connector_egress_arming.claim_connector_egress_arming(
        db,
        connector_run_id=run.connector_run_id,
        execution_idempotency_key="real-nrc-execution",
        expected_arming_fingerprint=str(run.request_fingerprint),
        now=datetime.now(timezone.utc),
    )
    assert claimed is True
    transport = RecordingTransport(
        [
            _response(_detail_body()),
            _response(
                b"%PDF-1.7\nreal arming identity\n%%EOF",
                content_type="application/pdf",
            ),
        ]
    )
    _patch_authority(monkeypatch)
    monkeypatch.setattr(nrc, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        nrc,
        "_build_strict_nrc_transport",
        lambda **kwargs: transport,
    )
    monkeypatch.setattr(
        nrc,
        "get_nrc_adams_client",
        lambda *args, **kwargs: pytest.fail("generic NRC client created"),
    )
    connector_run_id = run.connector_run_id

    nrc.execute_nrc_adams_run(connector_run_id)

    persisted = db.get(ConnectorRun, connector_run_id)
    assert persisted is not None
    assert persisted.source_system == "nrc_adams"
    assert persisted.status == "completed"
    assert [call["ordinal"] for call in transport.calls] == [1, 2]


def test_alternate_source_identity_is_quarantined_before_transport_send(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, verified_grant = _create_real_nrc_arming(db, tmp_path)
    monkeypatch.setattr(
        nrc.connector_egress_arming,
        "resolve_current_egress_authority",
        lambda *args, **kwargs: verified_grant,
    )
    run, claimed = nrc.connector_egress_arming.claim_connector_egress_arming(
        db,
        connector_run_id=run.connector_run_id,
        execution_idempotency_key="alternate-nrc-source",
        expected_arming_fingerprint=str(run.request_fingerprint),
        now=datetime.now(timezone.utc),
    )
    assert claimed is True
    run.source_system = "nrc_adams_aps"
    db.commit()
    connector_run_id = run.connector_run_id
    monkeypatch.setattr(nrc, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        nrc,
        "_build_strict_nrc_transport",
        lambda **kwargs: pytest.fail("transport created for alternate source"),
    )
    monkeypatch.setattr(
        nrc,
        "get_nrc_adams_client",
        lambda *args, **kwargs: pytest.fail("generic NRC client created"),
    )

    nrc.execute_nrc_adams_run(connector_run_id)

    persisted = db.get(ConnectorRun, connector_run_id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_summary == "reserved_egress_provenance_invalid"
    assert db.query(ConnectorRunTarget).count() == 0


def test_malformed_reserved_provenance_is_quarantined_before_generic_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease_expires_at = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ConnectorRun(
        connector_run_id="malformed-reserved",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="public_api",
        status="pending",
        request_config_json={"connector_egress_arming": {"schema_id": "wrong"}},
        execution_lease_owner="poisoned-owner",
        execution_lease_token="poisoned-token",
        execution_lease_expires_at=lease_expires_at,
    )
    fake_db = FakeExecutorSession(run)
    monkeypatch.setattr(nrc, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        nrc,
        "_acquire_lease",
        lambda *args, **kwargs: pytest.fail("generic lease mutated"),
    )
    monkeypatch.setattr(
        nrc,
        "get_nrc_adams_client",
        lambda *args, **kwargs: pytest.fail("generic NRC client created"),
    )

    nrc.execute_nrc_adams_run(run.connector_run_id)

    assert run.status == "failed"
    assert run.error_summary == "reserved_egress_provenance_invalid"
    assert run.completed_at is not None
    assert run.execution_lease_owner is None
    assert run.execution_lease_token is None
    assert run.execution_lease_expires_at == run.completed_at
    assert fake_db.commit_count == 1
    assert fake_db.rollback_count == 0
    assert fake_db.close_count == 1
    assert len(fake_db.added) == 1
    event = fake_db.added[0]
    assert isinstance(event, ConnectorRunEvent)
    assert event.event_type == "reserved_egress_provenance_rejected"
    assert event.stage == "pre_dispatch"
    assert event.status_before == "pending"
    assert event.status_after == "failed"
    assert event.reason_code == "reserved_egress_provenance_invalid"
    assert event.metrics_json == {"generic_execution_entered": False}


def test_valid_reserved_provenance_dispatches_before_generic_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = ConnectorRun(
        connector_run_id="valid-reserved",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="pending",
        submission_idempotency_key="egress-arm:valid",
        request_config_json={"connector_egress_arming": _envelope()},
        request_fingerprint="a" * 64,
    )
    fake_db = FakeExecutorSession(run)
    strict_transport = object()
    calls: list[str] = []
    monkeypatch.setattr(nrc, "SessionLocal", lambda: fake_db)

    def acquire(*args: Any, **kwargs: Any) -> str:
        calls.append("strict-lease")
        run.status = "running"
        return "lease-token"

    monkeypatch.setattr(nrc, "_acquire_strict_run_lease", acquire)

    def resolve_authority(*args: Any, **kwargs: Any) -> object:
        calls.append("authority")
        return object()

    monkeypatch.setattr(
        nrc.connector_egress_arming,
        "resolve_current_egress_authority",
        resolve_authority,
    )

    def build_transport(**kwargs: Any) -> object:
        calls.append("transport")
        return strict_transport

    monkeypatch.setattr(
        nrc,
        "_build_strict_nrc_transport",
        build_transport,
    )

    def execute(*args: Any, **kwargs: Any) -> None:
        assert kwargs["transport"] is strict_transport
        calls.append("strict-execute")

    monkeypatch.setattr(nrc, "_execute_fresh_exact_nrc_aps_run", execute)
    monkeypatch.setattr(
        nrc,
        "_acquire_lease",
        lambda *args, **kwargs: pytest.fail("generic lease mutated"),
    )
    monkeypatch.setattr(
        nrc,
        "get_nrc_adams_client",
        lambda *args, **kwargs: pytest.fail("generic NRC client created"),
    )

    nrc.execute_nrc_adams_run(run.connector_run_id)

    assert calls == [
        "strict-lease",
        "authority",
        "transport",
        "strict-execute",
    ]
    assert fake_db.rollback_count == 0
    assert fake_db.close_count == 1
