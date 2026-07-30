from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base  # noqa: E402
from app.models import ConnectorRun  # noqa: E402
from app.services import connector_egress_transport as transport  # noqa: E402


def test_crash_after_reservation_derives_spent_unknown_and_blocks_later_ordinal(
    monkeypatch,
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    monkeypatch.setattr(transport, "SESSION_FACTORY", factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)
    envelope = {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": "nrc_adams_aps",
        "campaign_id": "7fe33e0a-c0e7-4f8e-9d55-8ba77a01ce23",
        "campaign_fingerprint": "a" * 64,
        "campaign_definition_sha256": "b" * 64,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": "c" * 64,
        "arming_fingerprint": "d" * 64,
        "grant_sha256": "e" * 64,
        "canonical_grant_fingerprint": "f" * 64,
        "code_revision": "test",
        "max_physical_requests": 2,
        "max_run_bytes": 10_000,
        "max_single_send_detection_allowance_bytes": (
            transport.SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
        ),
        "campaign_not_before": transport.utc_six_z(now - timedelta(minutes=1)),
        "campaign_expires_at": transport.utc_six_z(expires),
        "grant_issued_at": transport.utc_six_z(now - timedelta(minutes=1)),
        "grant_expires_at": transport.utc_six_z(expires),
        "request_rules": [
            {
                "ordinal": 1,
                "stage": "exact_accession_api",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ["adams-api.nrc.gov"],
                "port": 443,
                "path_rule_id": "nrc_get_document_exact_v1",
                "query_rule_id": "none_v1",
                "credential_audience": "nrc_aps_api_key",
                "max_response_bytes": 5 * 1024 * 1024,
            },
            {
                "ordinal": 2,
                "stage": "artifact",
                "method": "GET",
                "scheme": "https",
                "allowed_hosts": ["www.nrc.gov"],
                "port": 443,
                "path_rule_id": "nrc_public_pdf_exact_v1",
                "query_rule_id": "none_v1",
                "credential_audience": "none",
                "max_response_bytes": 64 * 1024 * 1024,
            },
        ],
    }
    with factory() as db:
        db.add(
            ConnectorRun(
                connector_run_id="crash-run",
                connector_key="nrc_adams_aps",
                source_system="nrc_adams_aps",
                source_mode="strict_live_egress",
                status="running",
                request_config_json={"connector_egress_arming": envelope},
                request_fingerprint="d" * 64,
                execution_lease_owner="test",
                execution_lease_token="lease-token",
                execution_lease_expires_at=expires.replace(tzinfo=None),
            )
        )
        db.commit()

    transport.reserve_physical_request(
        connector_run_id="crash-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        ordinal=1,
        stage="exact_accession_api",
        request=transport.FrozenPhysicalRequest(
            method="GET",
            url="https://adams-api.nrc.gov/aps/api/search/ML17123A319",
            headers={"Ocp-Apim-Subscription-Key": "unit-test-key"},
            credential_audience="nrc_aps_api_key",
        ),
        expected_derived_arming_hash=None,
        now=now,
    )

    with factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="crash-run",
        )
    assert ledger.entries[0]["outcome_class"] == "spent_unknown"
    assert not ledger.eligible

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="crash-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=2,
            stage="artifact",
            request=transport.FrozenPhysicalRequest(
                method="GET",
                url="https://www.nrc.gov/docs/ML1712/ML17123A319.pdf",
            ),
            expected_derived_arming_hash="2" * 64,
            now=now,
        )
    assert exc.value.code == "connector_egress_prior_reservation_unresolved"
    engine.dispose()
