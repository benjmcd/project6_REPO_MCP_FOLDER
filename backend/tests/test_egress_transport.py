from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import builtins
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import importlib
import io
import json
import os
from pathlib import Path
from queue import Queue
import sys
from threading import Barrier, Event, Lock, Thread
from types import SimpleNamespace
from typing import Any

import pytest
import requests
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base  # noqa: E402
from app.models import (  # noqa: E402
    ConnectorRun,
    ConnectorRunEvent,
)
from app.schemas.api import expected_grant_rule_payloads  # noqa: E402
from app.services import connector_egress_arming as arming  # noqa: E402
from app.services import connector_egress_evidence as evidence  # noqa: E402
from app.services import connector_egress_transport as transport  # noqa: E402


def test_transport_reexports_dependency_pure_evidence_identities() -> None:
    assert transport.ConnectorEgressTransportError is (
        evidence.ConnectorEgressTransportError
    )
    assert transport.CounterEvidenceError is evidence.CounterEvidenceError
    assert transport.FrozenPhysicalRequest is evidence.FrozenPhysicalRequest
    assert transport.VerifiedTerminalRequestLedger is (
        evidence.VerifiedTerminalRequestLedger
    )
    assert transport.parse_connector_counter_records is (
        evidence.parse_connector_counter_records
    )
    assert transport.secret_free_request_fingerprint is (
        evidence.secret_free_request_fingerprint
    )
    assert transport.derive_terminal_request_ledger is (
        evidence.derive_terminal_request_ledger
    )


def test_evidence_module_import_does_not_load_network_or_authority_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = {
        "http",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_services = {
        "app.services.connector_egress_arming",
        "app.services.connector_egress_authorization",
        "app.services.connector_egress_transport",
        "app.services.connectors_nrc_adams",
        "app.services.connectors_sciencebase",
    }
    real_import = builtins.__import__
    observed: list[str] = []

    def blocked_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        observed.append(name)
        if name.split(".", 1)[0] in forbidden or name in forbidden_services:
            raise AssertionError(f"forbidden evidence import: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.delitem(
        sys.modules,
        "app.services.connector_egress_evidence",
        raising=False,
    )
    monkeypatch.setattr(builtins, "__import__", blocked_import)
    imported = importlib.import_module("app.services.connector_egress_evidence")

    assert imported.__name__ == "app.services.connector_egress_evidence"
    assert not forbidden_services.intersection(observed)


@pytest.fixture()
def session_factory(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    monkeypatch.setattr(transport, "SESSION_FACTORY", factory)
    try:
        yield factory
    finally:
        engine.dispose()


def _strict_envelope() -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return {
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
        "code_revision": "test-revision",
        "max_physical_requests": 2,
        "max_run_bytes": 10_000,
        "max_single_send_detection_allowance_bytes": (
            transport.SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
        ),
        "request_timeout_seconds": 30,
        "min_request_interval_ms": 0,
        "campaign_not_before": "2026-01-01T00:00:00.000000Z",
        "campaign_expires_at": transport.utc_six_z(expires_at),
        "grant_issued_at": "2026-01-01T00:00:00.000000Z",
        "grant_expires_at": transport.utc_six_z(expires_at),
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


def _seed_running_run(
    factory,
    *,
    connector_run_id: str = "strict-nrc-run",
) -> ConnectorRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ConnectorRun(
        connector_run_id=connector_run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="strict_live_egress",
        status="running",
        request_config_json={"connector_egress_arming": _strict_envelope()},
        request_fingerprint="d" * 64,
        execution_lease_owner="test",
        execution_lease_token="lease-token",
        execution_lease_expires_at=now + timedelta(minutes=5),
    )
    with factory() as db:
        db.add(run)
        db.commit()
    return run


def _set_connector_authority(
    factory,
    *,
    connector_key: str,
    max_physical_requests: int,
) -> None:
    with factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["connector_key"] = connector_key
        envelope["max_physical_requests"] = max_physical_requests
        envelope["request_rules"] = [
            dict(rule) for rule in expected_grant_rule_payloads(connector_key)
        ]
        config["connector_egress_arming"] = envelope
        run.connector_key = connector_key
        run.source_system = connector_key
        run.request_config_json = config
        db.commit()


def _seed_ledger_cardinality_rows(factory, *, count: int) -> None:
    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    with factory() as db:
        for index in range(count):
            db.add(
                ConnectorRunEvent(
                    connector_run_event_id=(
                        f"00000000-0000-0000-0000-{index + 1:012d}"
                    ),
                    connector_run_id="strict-nrc-run",
                    phase="egress",
                    stage="synthetic",
                    event_type=(
                        transport.RESERVATION_EVENT_TYPE
                        if index % 2 == 0
                        else transport.COMPLETION_EVENT_TYPE
                    ),
                    metrics_json={"ordinal": index // 2 + 1},
                    created_at=created_at + timedelta(microseconds=index),
                )
            )
        db.commit()


def _set_first_request_limits(
    factory,
    *,
    max_run_bytes: int,
    stage_cap: int | None = None,
) -> None:
    with factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["max_run_bytes"] = max_run_bytes
        if stage_cap is not None:
            rules = [dict(rule) for rule in envelope["request_rules"]]
            rules[0]["max_response_bytes"] = stage_cap
            envelope["request_rules"] = rules
        config["connector_egress_arming"] = envelope
        run.request_config_json = config
        db.commit()


def _request() -> transport.FrozenPhysicalRequest:
    return transport.FrozenPhysicalRequest(
        method="GET",
        url="https://adams-api.nrc.gov/aps/api/search/ML17123A319",
        headers={"Accept-Encoding": "identity", "Ocp-Apim-Subscription-Key": "secret"},
        credential_audience="nrc_aps_api_key",
    )


def _counter_record(
    *,
    ordinal: int,
    stage: str,
    request_fingerprint: str,
    now: datetime,
) -> dict[str, object]:
    body_hash = hashlib.sha256(b"x").hexdigest()
    return {
        "schema_id": "project6.connector_http_counter.v1",
        "ordinal": ordinal,
        "stage": stage,
        "request_fingerprint": request_fingerprint,
        "canonical_status_header_bytes": 10,
        "delivered_body_bytes": 1,
        "decoded_body_bytes": 1,
        "decoded_body_sha256": body_hash,
        "response_status": 200,
        "error_class": None,
        "monotonic_started_at": float(ordinal),
        "monotonic_stopped_at": float(ordinal) + 0.5,
        "evidence_started_at": transport.utc_six_z(now),
        "evidence_stopped_at": transport.utc_six_z(now),
    }


COUNTER_RUNTIME_INSTANCE_ID = "223e4567-e89b-42d3-a456-426614174000"
COUNTER_PROCESS_BOOT_ID = "7" * 64


def _v2_counter_record(
    record: dict[str, object],
    *,
    runtime_instance_id: str = COUNTER_RUNTIME_INSTANCE_ID,
    process_boot_id: str = COUNTER_PROCESS_BOOT_ID,
) -> dict[str, object]:
    return {
        **record,
        "schema_id": "project6.connector_http_counter.v2",
        "runtime_instance_id": runtime_instance_id,
        "process_boot_id": process_boot_id,
    }


def _write_counter_records(
    path: Path,
    records: list[dict[str, object]],
) -> None:
    path.write_bytes(
        b"".join(
            transport._canonical_json_bytes(record) + b"\n" for record in records
        )
    )


def _counter_events(
    records: list[dict[str, object]],
) -> list[SimpleNamespace]:
    events: list[SimpleNamespace] = []
    for record in records:
        identity = {
            "ordinal": record["ordinal"],
            "stage": record["stage"],
            "request_fingerprint": record["request_fingerprint"],
        }
        events.append(
            SimpleNamespace(
                event_type=transport.RESERVATION_EVENT_TYPE,
                metrics_json=identity,
            )
        )
        events.append(
            SimpleNamespace(
                event_type=transport.COMPLETION_EVENT_TYPE,
                metrics_json={
                    **identity,
                    "outcome_class": "completed",
                    "response_status": record["response_status"],
                    "counted_status_header_bytes": record[
                        "canonical_status_header_bytes"
                    ],
                    "delivered_body_bytes": record["delivered_body_bytes"],
                    "decoded_body_bytes": record["decoded_body_bytes"],
                    "decoded_body_sha256": record["decoded_body_sha256"],
                    "send_started_at": record["evidence_started_at"],
                    "completed_at": record["evidence_stopped_at"],
                },
            )
        )
    return events


def test_counter_parser_accepts_exact_historical_v1_and_boot_bound_v2() -> None:
    now = datetime.now(timezone.utc)
    v1 = _counter_record(
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="1" * 64,
        now=now,
    )
    v2 = _v2_counter_record(v1)

    assert transport.COUNTER_V2_EXTRA_KEYS == frozenset(
        ("runtime_instance_id", "process_boot_id")
    )
    assert transport.COUNTER_V2_KEYS == (
        transport.COUNTER_V1_KEYS | transport.COUNTER_V2_EXTRA_KEYS
    )
    assert transport.parse_connector_counter_records(
        transport._canonical_json_bytes(v1) + b"\n"
    ) == (v1,)
    assert transport.parse_connector_counter_records(
        transport._canonical_json_bytes(v2) + b"\n"
    ) == (v2,)


@pytest.mark.parametrize(
    "case",
    [
        "mixed_schema",
        "mixed_runtime",
        "mixed_boot",
        "missing_key",
        "extra_key",
        "noncanonical_uuid4",
        "noncanonical_boot",
    ],
)
def test_counter_parser_rejects_mixed_or_nonexact_v2(case: str) -> None:
    now = datetime.now(timezone.utc)
    first_v1 = _counter_record(
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="1" * 64,
        now=now,
    )
    second_v1 = _counter_record(
        ordinal=2,
        stage="artifact",
        request_fingerprint="2" * 64,
        now=now,
    )
    first = _v2_counter_record(first_v1)
    second = _v2_counter_record(second_v1)
    if case == "mixed_schema":
        records = [first, second_v1]
    else:
        records = [first, second]
        if case == "mixed_runtime":
            records[1]["runtime_instance_id"] = (
                "323e4567-e89b-42d3-a456-426614174000"
            )
        elif case == "mixed_boot":
            records[1]["process_boot_id"] = "8" * 64
        elif case == "missing_key":
            records[1].pop("process_boot_id")
        elif case == "extra_key":
            records[1]["unexpected"] = True
        elif case == "noncanonical_uuid4":
            records[1]["runtime_instance_id"] = COUNTER_RUNTIME_INSTANCE_ID.upper()
        elif case == "noncanonical_boot":
            records[1]["process_boot_id"] = "A" * 64
    payload = b"".join(
        transport._canonical_json_bytes(record) + b"\n" for record in records
    )

    with pytest.raises(transport.CounterEvidenceError):
        transport.parse_connector_counter_records(payload)


def test_revalidation_delegates_coordinated_tamper_to_canonical_resolver(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        rules = [dict(rule) for rule in envelope["request_rules"]]
        rules[0]["allowed_hosts"] = ["attacker.invalid"]
        envelope["request_rules"] = rules
        tampered_fingerprint = arming.compute_arming_fingerprint(envelope)
        envelope["arming_fingerprint"] = tampered_fingerprint
        run.request_fingerprint = tampered_fingerprint
        config["connector_egress_arming"] = envelope
        run.request_config_json = config
        db.commit()

    monkeypatch.setattr(arming.settings, "connector_live_egress_enabled", True)
    monkeypatch.setattr(
        arming.settings,
        "connector_live_egress_exclusive_proof_mode",
        True,
    )

    def reject_tampered_envelope(db, *, connector_run_id, now):
        run = db.get(ConnectorRun, connector_run_id)
        envelope = transport._strict_envelope(run)
        assert envelope["request_rules"][0]["allowed_hosts"] == [
            "attacker.invalid"
        ]
        raise arming.ConnectorEgressArmingError(
            "connector_arming_authority_drift",
            "synthetic canonical-envelope mismatch",
        )

    monkeypatch.setattr(
        arming,
        "resolve_current_egress_authority",
        reject_tampered_envelope,
    )

    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        envelope = transport._strict_envelope(run)
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            transport._revalidate_run_authority(
                db=db,
                run=run,
                envelope=envelope,
                now=datetime.now(timezone.utc),
            )
    assert exc.value.code == "connector_egress_authority_revalidation_failed"


def test_reservation_commits_before_send_and_terminal_ledger_is_stable(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    seen: list[int] = []

    def observed_send() -> None:
        with session_factory() as check:
            seen.append(
                check.query(ConnectorRunEvent)
                .filter(
                    ConnectorRunEvent.event_type == transport.RESERVATION_EVENT_TYPE
                )
                .count()
            )

    reservation = transport.reserve_physical_request(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
        expected_derived_arming_hash=None,
        now=datetime.now(timezone.utc),
    )
    observed_send()
    transport.complete_physical_request(
        reservation=reservation,
        outcome=transport.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=8,
            body_sha256="1" * 64,
            counted_status_header_bytes=42,
            delivered_body_bytes=8,
            decoded_body_bytes=8,
            decoded_body_sha256="1" * 64,
            send_started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        ),
    )

    assert seen == [1]
    original_events_for_run = evidence._events_for_run
    snapshot_calls: list[object] = []

    def counted_snapshot(*args, **kwargs):
        snapshot_calls.append(object())
        return original_events_for_run(*args, **kwargs)

    monkeypatch.setattr(evidence, "_events_for_run", counted_snapshot)
    with session_factory() as db:
        first = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
        second = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert first.ledger_terminal_hash == second.ledger_terminal_hash
    assert first.entries[0]["ordinal"] == 1
    assert first.entries[0]["outcome_class"] == "completed"
    assert not first.eligible
    assert "counter_reconciliation_failed" in first.validation_errors
    assert len(snapshot_calls) == 2


@pytest.mark.parametrize(
    ("connector_key", "physical_request_ceiling", "event_count", "error_code"),
    [
        ("nrc_adams_aps", 2, 4, None),
        ("nrc_adams_aps", 2, 5, "connector_egress_ledger_event_limit_exceeded"),
        ("sciencebase_mcs", 3, 6, None),
        ("sciencebase_mcs", 3, 7, "connector_egress_ledger_event_limit_exceeded"),
    ],
)
def test_ledger_event_loader_enforces_connector_specific_bound(
    session_factory,
    connector_key: str,
    physical_request_ceiling: int,
    event_count: int,
    error_code: str | None,
) -> None:
    _seed_running_run(session_factory)
    _set_connector_authority(
        session_factory,
        connector_key=connector_key,
        max_physical_requests=physical_request_ceiling,
    )
    _seed_ledger_cardinality_rows(session_factory, count=event_count)

    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        envelope = transport._strict_envelope(run)
        if error_code is None:
            events = transport._events_for_run(db, run=run, envelope=envelope)
            assert isinstance(events, tuple)
            assert len(events) == event_count
        else:
            with pytest.raises(transport.ConnectorEgressTransportError) as exc:
                transport._events_for_run(db, run=run, envelope=envelope)
            assert exc.value.code == error_code


def test_ledger_event_loader_rejects_no_limit_caller_before_materialization(
    session_factory,
) -> None:
    _seed_running_run(session_factory)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        envelope = transport._strict_envelope(run)

    class UnboundedQuery:
        rows: tuple[ConnectorRunEvent, ...] = ()
        all_calls = 0

        def filter(self, *criteria):
            return self

        def order_by(self, *criteria):
            return self

        def all(self):
            self.all_calls += 1
            return list(self.rows)

    unbounded_query = UnboundedQuery()

    class UnboundedAuthority:
        def query(self, model):
            assert model is ConnectorRunEvent
            return unbounded_query

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._events_for_run(
            UnboundedAuthority(),
            run=run,
            envelope=envelope,
        )

    assert exc.value.code == "connector_egress_ledger_query_unbounded"
    assert unbounded_query.all_calls == 0


def test_untrusted_envelope_ceiling_fails_before_event_query(
    session_factory,
) -> None:
    _seed_running_run(session_factory)
    _set_connector_authority(
        session_factory,
        connector_key="nrc_adams_aps",
        max_physical_requests=99,
    )
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        envelope = transport._strict_envelope(run)

    class QueryForbidden:
        def query(self, _model):
            raise AssertionError("event query must not run")

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._events_for_run(QueryForbidden(), run=run, envelope=envelope)

    assert exc.value.code == "connector_egress_ledger_bound_invalid"


def test_reservation_rejects_over_cap_ledger_before_new_event(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    _seed_ledger_cardinality_rows(session_factory, count=5)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
            expected_derived_arming_hash=None,
            now=datetime.now(timezone.utc),
        )

    assert exc.value.code == "connector_egress_ledger_event_limit_exceeded"
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 5


def test_reservation_commit_failure_calls_transport_zero_times(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    sends: list[object] = []

    def reject_reservation_commit(db) -> None:
        if any(
            isinstance(value, ConnectorRunEvent)
            and value.event_type == transport.RESERVATION_EVENT_TYPE
            for value in db.new
        ):
            raise RuntimeError("synthetic reservation commit failure")

    event.listen(session_factory.class_, "before_commit", reject_reservation_commit)
    try:
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            counter_path=tmp_path / "http.jsonl",
            send_callable=lambda *args, **kwargs: sends.append(args),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        with pytest.raises(RuntimeError, match="reservation commit failure"):
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )
    finally:
        event.remove(session_factory.class_, "before_commit", reject_reservation_commit)
    assert sends == []
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_terminal_ledger_rejects_coordinated_reservation_identity_tamper(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    now = datetime.now(timezone.utc)
    reservation = transport.reserve_physical_request(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
        expected_derived_arming_hash=None,
        now=now,
    )
    transport.complete_physical_request(
        reservation=reservation,
        outcome=transport.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=1,
            body_sha256=hashlib.sha256(b"x").hexdigest(),
            counted_status_header_bytes=10,
            delivered_body_bytes=1,
            decoded_body_bytes=1,
            decoded_body_sha256=hashlib.sha256(b"x").hexdigest(),
            send_started_at=now,
            completed_at=now,
        ),
    )

    with session_factory() as db:
        reservation_event = (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.event_type == transport.RESERVATION_EVENT_TYPE)
            .one()
        )
        completion_event = (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.event_type == transport.COMPLETION_EVENT_TYPE)
            .one()
        )
        reservation_metrics = dict(reservation_event.metrics_json)
        completion_metrics = dict(completion_event.metrics_json)
        reservation_metrics["host"] = "attacker.invalid"
        reservation_metrics["request_fingerprint"] = "9" * 64
        completion_metrics["request_fingerprint"] = "9" * 64
        reservation_event.metrics_json = reservation_metrics
        completion_event.metrics_json = completion_metrics
        db.commit()

    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert not ledger.eligible
    assert "invalid_reservation_1" in ledger.validation_errors


def test_duplicate_reservation_is_returned_as_already_spent(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    kwargs = {
        "connector_run_id": "strict-nrc-run",
        "lease_token": "lease-token",
        "arming_fingerprint": "d" * 64,
        "ordinal": 1,
        "stage": "exact_accession_api",
        "request": _request(),
        "expected_derived_arming_hash": None,
        "now": datetime.now(timezone.utc),
    }
    first = transport.reserve_physical_request(**kwargs)
    second = transport.reserve_physical_request(**kwargs)
    assert first.reservation_event_id == second.reservation_event_id
    assert not first.already_reserved
    assert second.already_reserved


def test_two_workers_cannot_create_two_reservations_for_one_ordinal(
    monkeypatch,
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'race.db').as_posix()}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    monkeypatch.setattr(transport, "SESSION_FACTORY", factory)
    _seed_running_run(factory)
    barrier = Barrier(2)

    def revalidate(**kwargs):
        barrier.wait(timeout=10)
        return kwargs["envelope"]

    monkeypatch.setattr(transport, "_revalidate_run_authority", revalidate)
    kwargs = {
        "connector_run_id": "strict-nrc-run",
        "lease_token": "lease-token",
        "arming_fingerprint": "d" * 64,
        "ordinal": 1,
        "stage": "exact_accession_api",
        "request": _request(),
        "expected_derived_arming_hash": None,
        "now": datetime.now(timezone.utc),
    }
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: transport.reserve_physical_request(**kwargs),
                    range(2),
                )
            )
        assert sorted(result.already_reserved for result in results) == [False, True]
        assert len({result.reservation_event_id for result in results}) == 1
        with factory() as db:
            assert (
                db.query(ConnectorRunEvent)
                .filter(
                    ConnectorRunEvent.event_type == transport.RESERVATION_EVENT_TYPE
                )
                .count()
                == 1
            )
    finally:
        engine.dispose()


def test_artifact_reservation_requires_committed_derived_arming(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    now = datetime.now(timezone.utc)
    first = transport.reserve_physical_request(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
        expected_derived_arming_hash=None,
        now=now,
    )
    transport.complete_physical_request(
        reservation=first,
        outcome=transport.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=1,
            body_sha256=hashlib.sha256(b"x").hexdigest(),
            counted_status_header_bytes=10,
            delivered_body_bytes=1,
            decoded_body_bytes=1,
            decoded_body_sha256=hashlib.sha256(b"x").hexdigest(),
            send_started_at=now,
            completed_at=now,
        ),
    )
    artifact_url = "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"
    expected_hash = hashlib.sha256(artifact_url.encode("ascii")).hexdigest()
    counter_path = tmp_path / "http.jsonl"
    counter_path.write_text(
        json.dumps(
            {
                "schema_id": "project6.connector_http_counter.v1",
                "ordinal": 1,
                "stage": "exact_accession_api",
                "request_fingerprint": first.request_fingerprint,
                "canonical_status_header_bytes": 10,
                "delivered_body_bytes": 1,
                "decoded_body_bytes": 1,
                "decoded_body_sha256": hashlib.sha256(b"x").hexdigest(),
                "response_status": 200,
                "error_class": None,
                "monotonic_started_at": 1.0,
                "monotonic_stopped_at": 2.0,
                "evidence_started_at": transport.utc_six_z(now),
                "evidence_stopped_at": transport.utc_six_z(now),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=2,
            stage="artifact",
            request=transport.FrozenPhysicalRequest(
                method="GET",
                url=artifact_url,
            ),
            expected_derived_arming_hash=expected_hash,
            now=now,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_derived_arming_missing"
    with session_factory() as db:
        assert (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.event_type == transport.RESERVATION_EVENT_TYPE)
            .count()
            == 1
        )


@pytest.mark.parametrize("counter_mode", ["missing", "mismatched", "extra"])
def test_later_ordinal_requires_matching_independent_prior_counter(
    session_factory,
    monkeypatch,
    tmp_path,
    counter_mode: str,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    now = datetime.now(timezone.utc)
    first = transport.reserve_physical_request(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
        expected_derived_arming_hash=None,
        now=now,
    )
    body_hash = hashlib.sha256(b"x").hexdigest()
    transport.complete_physical_request(
        reservation=first,
        outcome=transport.PhysicalRequestOutcome(
            outcome_class="completed",
            response_status=200,
            byte_count=1,
            body_sha256=body_hash,
            counted_status_header_bytes=10,
            delivered_body_bytes=1,
            decoded_body_bytes=1,
            decoded_body_sha256=body_hash,
            send_started_at=now,
            completed_at=now,
        ),
    )
    counter_path = tmp_path / "http.jsonl"
    if counter_mode != "missing":
        record = {
            "schema_id": "project6.connector_http_counter.v1",
            "ordinal": 1,
            "stage": "exact_accession_api",
            "request_fingerprint": first.request_fingerprint,
            "canonical_status_header_bytes": (
                9 if counter_mode == "mismatched" else 10
            ),
            "delivered_body_bytes": 1,
            "decoded_body_bytes": 1,
            "decoded_body_sha256": body_hash,
            "response_status": 200,
            "error_class": None,
            "monotonic_started_at": 1.0,
            "monotonic_stopped_at": 2.0,
            "evidence_started_at": transport.utc_six_z(now),
            "evidence_stopped_at": transport.utc_six_z(now),
        }
        records = [record]
        if counter_mode == "extra":
            records.append(dict(record))
        counter_path.write_text(
            "".join(
                json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
                for item in records
            ),
            encoding="utf-8",
        )

    artifact_url = "https://www.nrc.gov/docs/ML1712/ML17123A319.pdf"
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=2,
            stage="artifact",
            request=transport.FrozenPhysicalRequest(
                method="GET",
                url=artifact_url,
            ),
            expected_derived_arming_hash=hashlib.sha256(
                artifact_url.encode("ascii")
            ).hexdigest(),
            now=now,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"
    with session_factory() as db:
        assert (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.event_type == transport.RESERVATION_EVENT_TYPE)
            .count()
            == 1
        )


def test_counter_reconciliation_rejects_reordered_records(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    events: list[Any] = []
    records: list[dict[str, object]] = []
    for ordinal in (1, 2):
        fingerprint = str(ordinal) * 64
        stage = f"stage-{ordinal}"
        events.append(
            SimpleNamespace(
                event_type=transport.RESERVATION_EVENT_TYPE,
                metrics_json={
                    "ordinal": ordinal,
                    "stage": stage,
                    "request_fingerprint": fingerprint,
                },
            )
        )
        events.append(
            SimpleNamespace(
                event_type=transport.COMPLETION_EVENT_TYPE,
                metrics_json={
                    "ordinal": ordinal,
                    "stage": stage,
                    "request_fingerprint": fingerprint,
                    "outcome_class": "completed",
                    "response_status": 200,
                    "counted_status_header_bytes": 10,
                    "delivered_body_bytes": 1,
                    "decoded_body_bytes": 1,
                    "decoded_body_sha256": hashlib.sha256(b"x").hexdigest(),
                    "send_started_at": transport.utc_six_z(now),
                    "completed_at": transport.utc_six_z(now),
                },
            )
        )
        records.append(
            {
                "schema_id": "project6.connector_http_counter.v1",
                "ordinal": ordinal,
                "stage": stage,
                "request_fingerprint": fingerprint,
                "canonical_status_header_bytes": 10,
                "delivered_body_bytes": 1,
                "decoded_body_bytes": 1,
                "decoded_body_sha256": hashlib.sha256(b"x").hexdigest(),
                "response_status": 200,
                "error_class": None,
                "monotonic_started_at": float(ordinal),
                "monotonic_stopped_at": float(ordinal) + 0.5,
                "evidence_started_at": transport.utc_six_z(now),
                "evidence_stopped_at": transport.utc_six_z(now),
            }
        )
    counter_path = tmp_path / "http.jsonl"
    counter_path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in reversed(records)
        ),
        encoding="utf-8",
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            events,
            before_ordinal=3,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


def test_counter_reconciliation_allows_foreign_prefix_and_suffix(
    tmp_path,
) -> None:
    now = datetime.now(timezone.utc)
    expected_record = _counter_record(
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="3" * 64,
        now=now,
    )
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(
        counter_path,
        [
            _counter_record(
                ordinal=1,
                stage="exact_accession_api",
                request_fingerprint="1" * 64,
                now=now,
            ),
            expected_record,
            _counter_record(
                ordinal=2,
                stage="artifact",
                request_fingerprint="2" * 64,
                now=now,
            ),
        ],
    )

    assert (
        transport._reconcile_prior_counter_stream(
            _counter_events([expected_record]),
            before_ordinal=2,
            counter_path=counter_path,
        )
        == 11
    )


def test_counter_reconciliation_rejects_true_interleaving(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    expected_records = [
        _counter_record(
            ordinal=1,
            stage="item_hydration",
            request_fingerprint="3" * 64,
            now=now,
        ),
        _counter_record(
            ordinal=2,
            stage="download",
            request_fingerprint="4" * 64,
            now=now,
        ),
    ]
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(
        counter_path,
        [
            expected_records[0],
            _counter_record(
                ordinal=1,
                stage="exact_accession_api",
                request_fingerprint="1" * 64,
                now=now,
            ),
            expected_records[1],
        ],
    )

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            _counter_events(expected_records),
            before_ordinal=3,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


@pytest.mark.parametrize("duplicate_position", ["prefix", "suffix"])
def test_counter_reconciliation_rejects_duplicate_expected_identity(
    tmp_path,
    duplicate_position: str,
) -> None:
    now = datetime.now(timezone.utc)
    expected_record = _counter_record(
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="3" * 64,
        now=now,
    )
    foreign_record = _counter_record(
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="1" * 64,
        now=now,
    )
    records = (
        [expected_record, dict(expected_record), foreign_record]
        if duplicate_position == "prefix"
        else [foreign_record, expected_record, dict(expected_record)]
    )
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(counter_path, records)

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            _counter_events([expected_record]),
            before_ordinal=2,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


@pytest.mark.parametrize(
    ("identity_field", "wrong_value"),
    [("ordinal", 2), ("stage", "wrong-stage")],
)
def test_counter_reconciliation_rejects_wrong_expected_fingerprint_identity(
    tmp_path,
    identity_field: str,
    wrong_value: object,
) -> None:
    now = datetime.now(timezone.utc)
    expected_record = _counter_record(
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="3" * 64,
        now=now,
    )
    wrong_identity = dict(expected_record)
    wrong_identity[identity_field] = wrong_value
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(counter_path, [expected_record, wrong_identity])

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            _counter_events([expected_record]),
            before_ordinal=2,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


def test_counter_reconciliation_rejects_malformed_foreign_suffix(
    tmp_path,
) -> None:
    now = datetime.now(timezone.utc)
    expected_record = _counter_record(
        ordinal=1,
        stage="item_hydration",
        request_fingerprint="3" * 64,
        now=now,
    )
    foreign_record = _counter_record(
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="1" * 64,
        now=now,
    )
    counter_path = tmp_path / "http.jsonl"
    counter_path.write_bytes(
        transport._canonical_json_bytes(expected_record)
        + b"\n"
        + transport._canonical_json_bytes(foreign_record)[:-1]
        + b"\n"
    )

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            _counter_events([expected_record]),
            before_ordinal=2,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


def test_counter_reconciliation_rejects_gapped_expected_ordinals(
    tmp_path,
) -> None:
    now = datetime.now(timezone.utc)
    expected_records = [
        _counter_record(
            ordinal=1,
            stage="item_hydration",
            request_fingerprint="3" * 64,
            now=now,
        ),
        _counter_record(
            ordinal=3,
            stage="download",
            request_fingerprint="4" * 64,
            now=now,
        ),
    ]
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(counter_path, expected_records)

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            _counter_events(expected_records),
            before_ordinal=4,
            counter_path=counter_path,
            expected_ordinals={1, 3},
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


def test_shared_nrc_prefix_allows_sciencebase_ordinal_one(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(
        counter_path,
        [
            _counter_record(
                ordinal=1,
                stage="exact_accession_api",
                request_fingerprint="1" * 64,
                now=now,
            ),
            _counter_record(
                ordinal=2,
                stage="artifact",
                request_fingerprint="2" * 64,
                now=now,
            ),
        ],
    )

    assert (
        transport._reconcile_prior_counter_stream(
            [],
            before_ordinal=1,
            counter_path=counter_path,
        )
        == 0
    )


@pytest.mark.parametrize("invalid_kind", ["malformed", "noncanonical"])
def test_sciencebase_ordinal_one_rejects_invalid_shared_prefix(
    tmp_path,
    invalid_kind: str,
) -> None:
    now = datetime.now(timezone.utc)
    record = _counter_record(
        ordinal=1,
        stage="exact_accession_api",
        request_fingerprint="1" * 64,
        now=now,
    )
    canonical = transport._canonical_json_bytes(record) + b"\n"
    invalid = (
        b"{not-json}\n"
        if invalid_kind == "malformed"
        else json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
    )
    counter_path = tmp_path / "http.jsonl"
    counter_path.write_bytes(canonical + invalid)

    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport._reconcile_prior_counter_stream(
            [],
            before_ordinal=1,
            counter_path=counter_path,
        )
    assert exc.value.code == "connector_egress_prior_counter_unresolved"


def test_shared_v2_nrc_prefix_and_sciencebase_one_allow_sciencebase_two_revalidation(
    tmp_path,
) -> None:
    now = datetime.now(timezone.utc)
    sciencebase_fingerprint = "3" * 64
    sciencebase_record = _v2_counter_record(
        _counter_record(
            ordinal=1,
            stage="item_hydration",
            request_fingerprint=sciencebase_fingerprint,
            now=now,
        )
    )
    events = [
        SimpleNamespace(
            event_type=transport.RESERVATION_EVENT_TYPE,
            metrics_json={
                "ordinal": 1,
                "stage": "item_hydration",
                "request_fingerprint": sciencebase_fingerprint,
            },
        ),
        SimpleNamespace(
            event_type=transport.COMPLETION_EVENT_TYPE,
            metrics_json={
                "ordinal": 1,
                "stage": "item_hydration",
                "request_fingerprint": sciencebase_fingerprint,
                "outcome_class": "completed",
                "response_status": 200,
                "counted_status_header_bytes": 10,
                "delivered_body_bytes": 1,
                "decoded_body_bytes": 1,
                "decoded_body_sha256": hashlib.sha256(b"x").hexdigest(),
                "send_started_at": transport.utc_six_z(now),
                "completed_at": transport.utc_six_z(now),
            },
        ),
    ]
    counter_path = tmp_path / "http.jsonl"
    _write_counter_records(
        counter_path,
        [
            _v2_counter_record(
                _counter_record(
                    ordinal=1,
                    stage="exact_accession_api",
                    request_fingerprint="1" * 64,
                    now=now,
                )
            ),
            _v2_counter_record(
                _counter_record(
                    ordinal=2,
                    stage="artifact",
                    request_fingerprint="2" * 64,
                    now=now,
                )
            ),
            sciencebase_record,
        ],
    )

    assert (
        transport._reconcile_prior_counter_stream(
            events,
            before_ordinal=2,
            counter_path=counter_path,
        )
        == 11
    )

    foreign_suffix = _v2_counter_record(
        _counter_record(
            ordinal=3,
            stage="foreign_after_current_segment",
            request_fingerprint="4" * 64,
            now=now,
        )
    )
    counter_path.write_bytes(
        counter_path.read_bytes()
        + transport._canonical_json_bytes(foreign_suffix)
        + b"\n"
    )
    assert (
        transport._reconcile_prior_counter_stream(
            events,
            before_ordinal=2,
            counter_path=counter_path,
        )
        == 11
    )


def test_runtime_parser_limit_drift_fails_closed() -> None:
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.assert_pinned_http_parser_limits(maxline=65_535, maxheaders=100)
    assert exc.value.code == "connector_egress_http_parser_limit_drift"


def test_pinned_http_parser_accepts_99_fields_and_rejects_a_100th() -> None:
    admitted = b"".join(
        f"X-{index:02d}: value\r\n".encode("ascii") for index in range(99)
    ) + b"\r\n"
    parsed = http.client.parse_headers(io.BytesIO(admitted))
    assert len(parsed.items()) == 99

    rejected = b"".join(
        f"X-{index:03d}: value\r\n".encode("ascii") for index in range(100)
    ) + b"\r\n"
    with pytest.raises(http.client.HTTPException, match="more than 100 headers"):
        http.client.parse_headers(io.BytesIO(rejected))


def test_detection_allowance_mismatch_stops_before_reservation_or_send(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["max_single_send_detection_allowance_bytes"] -= 1
        config["connector_egress_arming"] = envelope
        run.request_config_json = config
        db.commit()
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    sends: list[object] = []
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: sends.append(args),
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_detection_allowance_mismatch"
    assert sends == []
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


@pytest.mark.parametrize(
    ("header_bytes", "body_bytes", "remaining", "crossed"),
    [
        (101, 0, 100, True),
        (90, 20, 100, True),
        (90, 10, 100, False),
        (0, 101, 100, True),
    ],
)
def test_aggregate_crossing_is_strict_greater_than(
    header_bytes: int,
    body_bytes: int,
    remaining: int,
    crossed: bool,
) -> None:
    assert (
        transport.aggregate_budget_crossed(
            status_header_bytes=header_bytes,
            delivered_body_bytes=body_bytes,
            remaining_budget=remaining,
        )
        is crossed
    )


def test_wall_clock_rollback_or_jump_cannot_change_bound_monotonic_authority() -> None:
    wall = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    monotonic = [100.0]
    envelope = {
        "campaign_expires_at": transport.utc_six_z(wall[0] + timedelta(seconds=10)),
        "grant_expires_at": transport.utc_six_z(wall[0] + timedelta(seconds=10)),
    }
    client = transport.BoundedConnectorTransport(
        connector_run_id="unused",
        lease_token="unused",
        arming_fingerprint="d" * 64,
        counter_path=Path("unused-http.jsonl"),
        utc_clock=lambda: wall[0],
        monotonic_clock=lambda: monotonic[0],
    )
    assert client._bind_authority_deadline(envelope) == 110.0

    wall[0] -= timedelta(seconds=100)
    monotonic[0] = 102.0
    assert client._bind_authority_deadline(envelope) == 110.0

    wall[0] = datetime(2026, 1, 1, 0, 0, 9, tzinfo=timezone.utc)
    monotonic[0] = 103.0
    assert client._bind_authority_deadline(envelope) == 110.0


def test_authority_windows_are_half_open_at_exact_boundaries() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=10)
    envelope = {
        "campaign_not_before": transport.utc_six_z(start),
        "campaign_expires_at": transport.utc_six_z(end),
        "grant_issued_at": transport.utc_six_z(start),
        "grant_expires_at": transport.utc_six_z(end),
    }
    assert transport._window_contains(envelope, start)
    assert transport._window_contains(envelope, end - timedelta(microseconds=1))
    assert not transport._window_contains(envelope, end)


def test_reservation_at_authority_expiry_fails_before_event(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    expiry = datetime.now(timezone.utc)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["campaign_expires_at"] = transport.utc_six_z(expiry)
        envelope["grant_expires_at"] = transport.utc_six_z(expiry)
        config["connector_egress_arming"] = envelope
        run.request_config_json = config
        db.commit()
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
            expected_derived_arming_hash=None,
            now=expiry,
        )
    assert exc.value.code == "connector_egress_campaign_expired"
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_reserved_not_sent_rejects_any_response_or_counter_evidence(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    now = datetime.now(timezone.utc)
    reservation = transport.reserve_physical_request(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
        expected_derived_arming_hash=None,
        now=now,
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.complete_physical_request(
            reservation=reservation,
            outcome=transport.PhysicalRequestOutcome(
                outcome_class="reserved_not_sent",
                response_status=200,
                byte_count=0,
                body_sha256=hashlib.sha256(b"").hexdigest(),
                counted_status_header_bytes=12,
                delivered_body_bytes=0,
                decoded_body_bytes=0,
                decoded_body_sha256=hashlib.sha256(b"").hexdigest(),
                send_started_at=None,
                completed_at=now,
            ),
        )
    assert exc.value.code == "connector_egress_reserved_not_sent_counter_invalid"
    with session_factory() as db:
        assert (
            db.query(ConnectorRunEvent)
            .filter(ConnectorRunEvent.event_type == transport.COMPLETION_EVENT_TYPE)
            .count()
            == 0
        )


def test_terminal_ledger_rejects_non_strict_source_mode(session_factory) -> None:
    _seed_running_run(session_factory)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        run.source_mode = "legacy_live"
        db.commit()
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert not ledger.eligible
    assert "run_authority_identity_invalid" in ledger.validation_errors


class _HeaderPairs:
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self._pairs = list(pairs)

    def items(self):
        return iter(self._pairs)

    def get(self, name: str, default=None):
        values = [value for key, value in self._pairs if key.lower() == name.lower()]
        return values[-1] if values else default

    def getlist(self, name: str):
        return [value for key, value in self._pairs if key.lower() == name.lower()]


class _RawResponse:
    version = 11

    def __init__(
        self,
        body: bytes,
        *,
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        self._body = body
        self._offset = 0
        self.headers = _HeaderPairs(headers or [("Content-Type", "application/json")])
        self.read_calls = 0
        self.closed = False

    def read(self, amount: int, *, decode_content: bool = False) -> bytes:
        assert decode_content is False
        self.read_calls += 1
        chunk = self._body[self._offset : self._offset + amount]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


class _DeadlineSocket:
    def __init__(self) -> None:
        self.timeout = 0.0
        self.observed: list[float] = []

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout
        self.observed.append(timeout)


class _SlowDripRaw(_RawResponse):
    def __init__(self, clock: list[float]) -> None:
        super().__init__(b"xx")
        self._clock = clock
        self._socket = _DeadlineSocket()
        self._fp = SimpleNamespace(
            fp=SimpleNamespace(
                raw=SimpleNamespace(_sock=self._socket),
            )
        )

    def read(self, amount: int, *, decode_content: bool = False) -> bytes:
        assert decode_content is False
        duration = 0.6
        if duration > self._socket.timeout:
            self._clock[0] += self._socket.timeout
            raise requests.Timeout("synthetic absolute deadline")
        self._clock[0] += duration
        self.read_calls += 1
        chunk = self._body[self._offset : self._offset + 1]
        self._offset += len(chunk)
        return chunk


def _response(
    body: bytes,
    *,
    status: int = 200,
    reason: str = "OK",
    headers: list[tuple[str, str]] | None = None,
):
    response = requests.Response()
    response.status_code = status
    response.reason = reason
    response.raw = _RawResponse(body, headers=headers)
    response.headers.clear()
    for name, value in response.raw.headers.items():
        response.headers[name] = value
    return response


def _runtime_context(
    frames: list[bytes],
    *,
    revocation_is_set,
    lifecycle: list[str],
) -> transport.ConnectorCounterRuntimeContext:
    return transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
        process_boot_id=COUNTER_PROCESS_BOOT_ID,
        append_frame=frames.append,
        revocation_is_set=revocation_is_set,
        acquire_send_idle=lambda: lifecycle.append("acquire"),
        release_send_idle=lambda: lifecycle.append("release"),
    )


def test_counter_runtime_emits_only_canonical_v2_to_wrapper_sink(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    frames: list[bytes] = []
    lifecycle: list[str] = []
    context = _runtime_context(
        frames,
        revocation_is_set=lambda: False,
        lifecycle=lifecycle,
    )

    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: _response(b"payload"),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        result = client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )

    assert result.outcome_class == "completed"
    assert lifecycle == ["acquire", "release"]
    assert len(frames) == 1
    assert not frames[0].endswith(b"\n")
    records = transport.parse_connector_counter_records(frames[0] + b"\n")
    assert records[0]["schema_id"] == "project6.connector_http_counter.v2"
    assert records[0]["runtime_instance_id"] == COUNTER_RUNTIME_INSTANCE_ID
    assert records[0]["process_boot_id"] == COUNTER_PROCESS_BOOT_ID
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_records=records,
        )
    assert ledger.eligible is True


def test_revocation_before_reservation_creates_no_reservation(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    frames: list[bytes] = []
    lifecycle: list[str] = []
    sends: list[object] = []
    preflights: list[str] = []
    resolutions: list[tuple[str, int]] = []
    real_preflight = transport._preflight_exact_request

    def observed_preflight(**kwargs):
        preflights.append(kwargs["connector_run_id"])
        return real_preflight(**kwargs)

    monkeypatch.setattr(transport, "_preflight_exact_request", observed_preflight)
    context = _runtime_context(
        frames,
        revocation_is_set=lambda: True,
        lifecycle=lifecycle,
    )

    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: sends.append(args),
            dns_resolver=lambda host, port: (
                resolutions.append((host, port)) or ["8.8.8.8"]
            ),
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )

    assert exc.value.code == "connector_egress_revoked"
    assert lifecycle == []
    assert sends == []
    assert frames == []
    assert preflights == []
    assert resolutions == []
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_revocation_set_by_idle_acquire_stops_before_reservation(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    revoked = [False]
    frames: list[bytes] = []
    lifecycle: list[str] = []
    resolutions: list[tuple[str, int]] = []
    adapters: list[object] = []
    sends: list[object] = []

    def acquire() -> None:
        lifecycle.append("acquire")
        revoked[0] = True

    context = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
        process_boot_id=COUNTER_PROCESS_BOOT_ID,
        append_frame=frames.append,
        revocation_is_set=lambda: revoked[0],
        acquire_send_idle=acquire,
        release_send_idle=lambda: lifecycle.append("release"),
    )
    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: sends.append(args),
            dns_resolver=lambda host, port: (
                resolutions.append((host, port)) or ["8.8.8.8"]
            ),
            prepared_request_adapter=lambda prepared: (
                adapters.append(prepared) or prepared
            ),
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )

    assert exc.value.code == "connector_egress_revoked"
    assert lifecycle == ["acquire", "release"]
    assert len(resolutions) == 1
    assert adapters == []
    assert sends == []
    assert frames == []
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_revocation_after_reservation_records_reserved_not_sent_and_signals_idle(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    checks = iter((False, False, True))
    frames: list[bytes] = []
    lifecycle: list[str] = []
    sends: list[object] = []
    context = _runtime_context(
        frames,
        revocation_is_set=lambda: next(checks),
        lifecycle=lifecycle,
    )

    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: sends.append(args),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )

    assert exc.value.code == "connector_egress_revoked"
    assert lifecycle == ["acquire", "release"]
    assert sends == []
    assert frames == []
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert ledger.entries[0]["outcome_class"] == "reserved_not_sent"
    assert ledger.eligible is False


def test_in_flight_send_finishes_v2_counter_and_terminal_evidence_after_revocation(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    revoked = [False]
    frames: list[bytes] = []
    lifecycle: list[str] = []

    def send(*args, **kwargs):
        revoked[0] = True
        return _response(b"completed-in-flight")

    context = _runtime_context(
        frames,
        revocation_is_set=lambda: revoked[0],
        lifecycle=lifecycle,
    )
    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=send,
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        result = client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )

    records = transport.parse_connector_counter_records(frames[0] + b"\n")
    assert revoked == [True]
    assert result.outcome_class == "completed"
    assert records[0]["error_class"] is None
    assert lifecycle == ["acquire", "release"]
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_records=records,
        )
    assert ledger.entries[0]["outcome_class"] == "completed"
    assert ledger.eligible is True


def test_process_global_physical_send_lock_serializes_transport_instances(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory, connector_run_id="strict-nrc-run-a")
    _seed_running_run(session_factory, connector_run_id="strict-nrc-run-b")
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    frames: list[bytes] = []
    lifecycle: list[str] = []
    first_entered = Event()
    release_first = Event()
    second_entered = Event()
    call_lock = Lock()
    calls = [0]

    def send(*args, **kwargs):
        with call_lock:
            calls[0] += 1
            current = calls[0]
        if current == 1:
            first_entered.set()
            assert release_first.wait(5)
        else:
            second_entered.set()
        return _response(f"response-{current}".encode("ascii"))

    context = _runtime_context(
        frames,
        revocation_is_set=lambda: False,
        lifecycle=lifecycle,
    )
    with transport.connector_counter_runtime(context):
        clients = [
            transport.BoundedConnectorTransport(
                connector_run_id=connector_run_id,
                lease_token="lease-token",
                arming_fingerprint="d" * 64,
                send_callable=send,
                dns_resolver=lambda host, port: ["8.8.8.8"],
            )
            for connector_run_id in ("strict-nrc-run-a", "strict-nrc-run-b")
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                clients[0].send_once,
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )
            assert first_entered.wait(5)
            second = pool.submit(
                clients[1].send_once,
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )
            assert second_entered.wait(0.25) is False
            release_first.set()
            assert first.result(timeout=5).outcome_class == "completed"
            assert second.result(timeout=5).outcome_class == "completed"

    assert second_entered.is_set()
    assert lifecycle == ["acquire", "release", "acquire", "release"]
    assert len(frames) == 2


def test_transport_constructed_before_runtime_binds_context_in_another_thread(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    legacy_path = tmp_path / "legacy.jsonl"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=legacy_path,
        send_callable=lambda *args, **kwargs: _response(b"runtime-bound"),
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    frames: list[bytes] = []
    lifecycle: list[str] = []
    context = _runtime_context(
        frames,
        revocation_is_set=lambda: False,
        lifecycle=lifecycle,
    )

    with transport.connector_counter_runtime(context):
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(
                client.send_once,
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            ).result(timeout=5)

    assert result.outcome_class == "completed"
    assert lifecycle == ["acquire", "release"]
    assert not legacy_path.exists()
    records = transport.parse_connector_counter_records(frames[0] + b"\n")
    assert records[0]["schema_id"] == transport.COUNTER_V2_SCHEMA_ID
    assert records[0]["runtime_instance_id"] == COUNTER_RUNTIME_INSTANCE_ID


def test_transport_uses_current_runtime_not_stale_construction_context(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    first_frames: list[bytes] = []
    first_lifecycle: list[str] = []
    first = _runtime_context(
        first_frames,
        revocation_is_set=lambda: False,
        lifecycle=first_lifecycle,
    )
    with transport.connector_counter_runtime(first):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: _response(b"fresh-context"),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )

    second_frames: list[bytes] = []
    second_lifecycle: list[str] = []
    second = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id="323e4567-e89b-42d3-a456-426614174000",
        process_boot_id="8" * 64,
        append_frame=second_frames.append,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: second_lifecycle.append("acquire"),
        release_send_idle=lambda: second_lifecycle.append("release"),
    )
    with transport.connector_counter_runtime(second):
        result = client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )

    assert result.outcome_class == "completed"
    assert first_frames == []
    assert first_lifecycle == []
    assert second_lifecycle == ["acquire", "release"]
    record = transport.parse_connector_counter_records(second_frames[0] + b"\n")[0]
    assert record["runtime_instance_id"] == second.runtime_instance_id
    assert record["process_boot_id"] == second.process_boot_id


def test_append_frame_failure_still_closes_physical_request_terminally(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    lifecycle: list[str] = []
    sends: list[object] = []

    def append_frame(_frame: bytes) -> None:
        raise RuntimeError("synthetic counter sink failure")

    context = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
        process_boot_id=COUNTER_PROCESS_BOOT_ID,
        append_frame=append_frame,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: lifecycle.append("acquire"),
        release_send_idle=lambda: lifecycle.append("release"),
    )
    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: (
                sends.append(args) or _response(b"physically-sent")
            ),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )

    assert exc.value.code == "connector_egress_counter_write_failed"
    assert len(sends) == 1
    assert lifecycle == ["acquire", "release"]
    with session_factory() as db:
        events = db.query(ConnectorRunEvent).all()
    assert [event.event_type for event in events] == [
        transport.RESERVATION_EVENT_TYPE,
        transport.COMPLETION_EVENT_TYPE,
    ]
    assert events[-1].metrics_json["outcome_class"] == "counter_write_failed"


def test_release_failure_does_not_mask_primary_revocation_error(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    revoked = [False]
    lifecycle: list[str] = []

    def acquire() -> None:
        lifecycle.append("acquire")
        revoked[0] = True

    def release() -> None:
        lifecycle.append("release")
        raise RuntimeError("synthetic release failure")

    context = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
        process_boot_id=COUNTER_PROCESS_BOOT_ID,
        append_frame=lambda frame: None,
        revocation_is_set=lambda: revoked[0],
        acquire_send_idle=acquire,
        release_send_idle=release,
    )
    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: pytest.fail("must not send"),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )

    assert exc.value.code == "connector_egress_revoked"
    assert lifecycle == ["acquire", "release"]
    assert any(
        "connector_egress_send_idle_release_failed" in note
        for note in getattr(exc.value, "__notes__", ())
    )
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_release_failure_after_success_is_reported(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    frames: list[bytes] = []

    def release() -> None:
        raise RuntimeError("synthetic release failure")

    context = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
        process_boot_id=COUNTER_PROCESS_BOOT_ID,
        append_frame=frames.append,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: None,
        release_send_idle=release,
    )
    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: _response(b"completed"),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            client.send_once(
                ordinal=1,
                stage="exact_accession_api",
                request=_request(),
            )

    assert exc.value.code == "connector_egress_send_idle_release_failed"
    assert len(frames) == 1
    with session_factory() as db:
        events = db.query(ConnectorRunEvent).all()
    assert events[-1].event_type == transport.COMPLETION_EVENT_TYPE


def test_process_global_send_guard_rejects_same_thread_reentry() -> None:
    with transport._serialized_physical_send():
        with pytest.raises(transport.ConnectorEgressTransportError) as exc:
            with transport._serialized_physical_send():
                pytest.fail("reentrant physical-send body must not run")
    assert exc.value.code == "connector_egress_send_reentry"


def test_runtime_sink_ack_persists_validated_frame_before_return(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    counter_path = tmp_path / "http.jsonl"
    pending: Queue[tuple[bytes, Event, list[BaseException]]] = Queue()

    def pump() -> None:
        frame, acknowledged, failures = pending.get(timeout=5)
        try:
            records = transport.parse_connector_counter_records(frame + b"\n")
            assert records[0]["schema_id"] == transport.COUNTER_V2_SCHEMA_ID
            with counter_path.open("ab", buffering=0) as stream:
                stream.write(frame + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException as exc:
            failures.append(exc)
        finally:
            acknowledged.set()

    worker = Thread(target=pump, daemon=True)
    worker.start()

    def append_frame(frame: bytes) -> None:
        acknowledged = Event()
        failures: list[BaseException] = []
        pending.put((frame, acknowledged, failures))
        if not acknowledged.wait(5):
            raise RuntimeError("counter pump ACK timed out")
        if failures:
            raise failures[0]

    lifecycle: list[str] = []
    context = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=COUNTER_RUNTIME_INSTANCE_ID,
        process_boot_id=COUNTER_PROCESS_BOOT_ID,
        append_frame=append_frame,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: lifecycle.append("acquire"),
        release_send_idle=lambda: lifecycle.append("release"),
    )
    with transport.connector_counter_runtime(context):
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: _response(b"persisted"),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        result = client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
        immediate = arming._load_nrc_counter_records(counter_path)

    worker.join(timeout=5)
    assert not worker.is_alive()
    assert result.outcome_class == "completed"
    assert lifecycle == ["acquire", "release"]
    assert len(immediate) == 1
    assert immediate[0]["schema_id"] == transport.COUNTER_V2_SCHEMA_ID


def test_runtime_install_rejections_do_not_disturb_active_context(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    first_frames: list[bytes] = []
    first_lifecycle: list[str] = []
    first = _runtime_context(
        first_frames,
        revocation_is_set=lambda: False,
        lifecycle=first_lifecycle,
    )
    second = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id="323e4567-e89b-42d3-a456-426614174000",
        process_boot_id="8" * 64,
        append_frame=lambda frame: None,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: None,
        release_send_idle=lambda: None,
    )

    with transport.connector_counter_runtime(first):
        with pytest.raises(transport.ConnectorEgressTransportError) as nested:
            with transport.connector_counter_runtime(second):
                pytest.fail("nested runtime must not install")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_install_runtime_for_test, second)
            with pytest.raises(
                transport.ConnectorEgressTransportError
            ) as concurrent:
                future.result(timeout=5)
        client = transport.BoundedConnectorTransport(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            send_callable=lambda *args, **kwargs: _response(b"still-active"),
            dns_resolver=lambda host, port: ["8.8.8.8"],
        )
        result = client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )

    assert nested.value.code == "connector_counter_runtime_already_installed"
    assert concurrent.value.code == "connector_counter_runtime_already_installed"
    assert result.outcome_class == "completed"
    assert len(first_frames) == 1
    assert first_lifecycle == ["acquire", "release"]


def _install_runtime_for_test(
    context: transport.ConnectorCounterRuntimeContext,
) -> None:
    with transport.connector_counter_runtime(context):
        pytest.fail("concurrent runtime must not install")


def test_runtime_exception_clears_cache_and_next_install_is_isolated() -> None:
    first_frames: list[bytes] = []
    first_lifecycle: list[str] = []
    first = _runtime_context(
        first_frames,
        revocation_is_set=lambda: False,
        lifecycle=first_lifecycle,
    )
    marker = _v2_counter_record(
        _counter_record(
            ordinal=1,
            stage="exact_accession_api",
            request_fingerprint="1" * 64,
            now=datetime.now(timezone.utc),
        )
    )
    with pytest.raises(RuntimeError, match="synthetic runtime exit"):
        with transport.connector_counter_runtime(first):
            transport._COUNTER_RUNTIME_RECORDS.append(marker)
            raise RuntimeError("synthetic runtime exit")

    second = transport.ConnectorCounterRuntimeContext(
        runtime_instance_id="323e4567-e89b-42d3-a456-426614174000",
        process_boot_id="8" * 64,
        append_frame=lambda frame: None,
        revocation_is_set=lambda: False,
        acquire_send_idle=lambda: None,
        release_send_idle=lambda: None,
    )
    with transport.connector_counter_runtime(second):
        assert transport._COUNTER_RUNTIME_RECORDS == []
    assert transport._COUNTER_RUNTIME_RECORDS == []


def test_counter_runtime_context_is_frozen() -> None:
    context = _runtime_context(
        [],
        revocation_is_set=lambda: False,
        lifecycle=[],
    )
    with pytest.raises(FrozenInstanceError):
        context.runtime_instance_id = "323e4567-e89b-42d3-a456-426614174000"


def test_subscription_key_value_is_absent_from_fingerprint_and_repr() -> None:
    first = _request()
    second = transport.FrozenPhysicalRequest(
        method="GET",
        url=first.url,
        headers={
            "Accept-Encoding": "identity",
            "Ocp-Apim-Subscription-Key": "different-secret",
        },
        credential_audience="nrc_aps_api_key",
    )
    kwargs = {
        "arming_fingerprint": "d" * 64,
        "grant_sha256": "e" * 64,
        "ordinal": 1,
        "stage": "exact_accession_api",
    }
    assert transport.secret_free_request_fingerprint(first, **kwargs) == (
        transport.secret_free_request_fingerprint(second, **kwargs)
    )
    assert "secret" not in repr(first)
    assert first.url not in repr(first)


def test_frozen_request_snapshots_caller_owned_headers() -> None:
    headers = {
        "Accept-Encoding": "identity",
        "Ocp-Apim-Subscription-Key": "first-secret",
    }
    request = transport.FrozenPhysicalRequest(
        method="GET",
        url="https://adams-api.nrc.gov/aps/api/search/ML17123A319",
        headers=headers,
        credential_audience="nrc_aps_api_key",
    )
    before = transport.secret_free_request_fingerprint(
        request,
        arming_fingerprint="d" * 64,
        grant_sha256="e" * 64,
        ordinal=1,
        stage="exact_accession_api",
    )
    headers["Authorization"] = "Bearer attacker"
    headers["Ocp-Apim-Subscription-Key"] = "second-secret"
    after = transport.secret_free_request_fingerprint(
        request,
        arming_fingerprint="d" * 64,
        grant_sha256="e" * 64,
        ordinal=1,
        stage="exact_accession_api",
    )
    assert before == after
    assert "Authorization" not in request.headers


def test_nrc_request_without_subscription_key_is_rejected_before_reservation(
    session_factory,
    monkeypatch,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=1,
            stage="exact_accession_api",
            request=transport.FrozenPhysicalRequest(
                method="GET",
                url="https://adams-api.nrc.gov/aps/api/search/ML17123A319",
                credential_audience="nrc_aps_api_key",
            ),
            expected_derived_arming_hash=None,
            now=datetime.now(timezone.utc),
        )
    assert exc.value.code == "connector_egress_credential_header_missing"
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


@pytest.mark.parametrize(
    "forbidden_header",
    [
        "Authorization",
        "Host",
        "Cookie",
        "Proxy-Authorization",
        "Transfer-Encoding",
        "Connection",
    ],
)
def test_control_or_ambient_credential_header_is_rejected_before_reservation(
    session_factory,
    monkeypatch,
    forbidden_header: str,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    headers = {
        "Accept-Encoding": "identity",
        "Ocp-Apim-Subscription-Key": "secret",
        forbidden_header: "forbidden",
    }
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        transport.reserve_physical_request(
            connector_run_id="strict-nrc-run",
            lease_token="lease-token",
            arming_fingerprint="d" * 64,
            ordinal=1,
            stage="exact_accession_api",
            request=transport.FrozenPhysicalRequest(
                method="GET",
                url="https://adams-api.nrc.gov/aps/api/search/ML17123A319",
                headers=headers,
                credential_audience="nrc_aps_api_key",
            ),
            expected_derived_arming_hash=None,
            now=datetime.now(timezone.utc),
        )
    assert exc.value.code == "connector_egress_header_not_authorized"
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_non_public_dns_stops_before_reservation_or_send(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    sends: list[object] = []
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: sends.append(args),
        dns_resolver=lambda host, port: ["127.0.0.1"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_dns_non_public"
    assert sends == []
    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 0


def test_final_prepared_request_drift_spends_reservation_without_send(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    sends: list[object] = []

    def mutate(prepared):
        prepared.headers["X-Adapter-Drift"] = "changed"
        return prepared

    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: sends.append(args),
        dns_resolver=lambda host, port: ["8.8.8.8"],
        prepared_request_adapter=mutate,
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_prepared_request_mismatch"
    assert sends == []
    assert not (tmp_path / "http.jsonl").exists()
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_path=tmp_path / "http.jsonl",
        )
    assert ledger.entries[0]["outcome_class"] == "reserved_not_sent"
    assert not ledger.eligible
    assert "counter_reconciliation_failed" not in ledger.validation_errors


def test_rate_wait_failure_records_reserved_not_sent_and_calls_no_transport(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["min_request_interval_ms"] = 1_000
        config["connector_egress_arming"] = envelope
        run.request_config_json = config
        db.commit()
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    sends: list[object] = []

    def interrupted_wait(seconds: float) -> None:
        raise RuntimeError(f"synthetic wait failure after {seconds}")

    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: sends.append(args),
        dns_resolver=lambda host, port: ["8.8.8.8"],
        monotonic_clock=lambda: 0.0,
        sleeper=interrupted_wait,
        rate_state={"adams-api.nrc.gov": 0.0},
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_pre_send_failed"
    assert sends == []
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert ledger.entries[0]["outcome_class"] == "reserved_not_sent"
    assert not ledger.eligible


def test_post_reservation_authority_drift_records_reserved_not_sent(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    calls = [0]

    def revalidate(**kwargs):
        calls[0] += 1
        if calls[0] == 3:
            raise transport.ConnectorEgressTransportError(
                "connector_egress_authority_revalidation_failed"
            )
        return kwargs["envelope"]

    monkeypatch.setattr(transport, "_revalidate_run_authority", revalidate)
    sends: list[object] = []
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: sends.append(args),
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_authority_revalidation_failed"
    assert calls[0] == 3
    assert sends == []
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert ledger.entries[0]["outcome_class"] == "reserved_not_sent"
    assert not ledger.eligible


def test_one_send_is_identity_no_redirect_and_counter_precedes_completion(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    observed: dict[str, object] = {}

    def send(prepared, **kwargs):
        observed["prepared"] = prepared
        observed.update(kwargs)
        return _response(
            b"payload",
            headers=[
                ("Content-Type", "application/json"),
                ("Location", "/first"),
                ("Location", "/second"),
            ],
        )

    counter_path = tmp_path / "http.jsonl"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=counter_path,
        send_callable=send,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    result = client.send_once(
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
    )

    prepared = observed["prepared"]
    assert prepared.headers["Accept-Encoding"] == "identity"
    assert observed["allow_redirects"] is False
    assert observed["verify"] is True
    assert observed["session"].trust_env is False
    assert len(observed["session"].cookies) == 0
    assert result.body == b"payload"
    assert result.location_values == ("/first", "/second")
    records = [
        json.loads(line)
        for line in counter_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["response_status"] == 200
    assert records[0]["delivered_body_bytes"] == 7
    serialized = json.dumps(records[0], sort_keys=True)
    assert "secret" not in serialized
    assert "adams-api" not in serialized
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_path=counter_path,
        )
    assert ledger.entries[0]["outcome_class"] == "completed"
    assert ledger.eligible


def test_slow_drip_is_cut_off_at_absolute_monotonic_deadline(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    with session_factory() as db:
        run = db.get(ConnectorRun, "strict-nrc-run")
        config = dict(run.request_config_json)
        envelope = dict(config["connector_egress_arming"])
        envelope["request_timeout_seconds"] = 1
        config["connector_egress_arming"] = envelope
        run.request_config_json = config
        db.commit()
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    monotonic = [0.0]
    raw = _SlowDripRaw(monotonic)
    response = requests.Response()
    response.status_code = 200
    response.reason = "OK"
    response.raw = raw
    response.headers["Content-Type"] = "application/json"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: response,
        dns_resolver=lambda host, port: ["8.8.8.8"],
        monotonic_clock=lambda: monotonic[0],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_transport_timeout"
    assert monotonic[0] == pytest.approx(1.0)
    assert raw._socket.observed == pytest.approx([1.0, 0.4])
    records = [
        json.loads(line)
        for line in (tmp_path / "http.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["delivered_body_bytes"] == 1


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (206, b"partial"),
        (429, b""),
        (500, b"provider-error"),
    ],
)
def test_partial_throttle_and_server_error_each_remain_one_physical_send(
    session_factory,
    monkeypatch,
    tmp_path,
    status: int,
    body: bytes,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    sends = [0]

    def send(*args, **kwargs):
        sends[0] += 1
        return _response(body, status=status, reason="Synthetic")

    counter_path = tmp_path / "http.jsonl"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=counter_path,
        send_callable=send,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    result = client.send_once(
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
    )
    assert sends == [1]
    assert result.response_status == status
    assert result.body == body
    assert len(counter_path.read_text(encoding="utf-8").splitlines()) == 1


def test_header_only_aggregate_crossing_is_terminal_oversized(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    headers = [(f"X-{index:02d}", "x" * 512) for index in range(99)]
    response = _response(
        b"must-not-be-read",
        headers=headers,
    )
    header_bytes = len(
        transport._canonical_status_header_bytes(
            response,
            transport._header_pairs(response),
        )
    )
    assert header_bytes > 32_768
    _set_first_request_limits(
        session_factory,
        max_run_bytes=header_bytes - 1,
    )
    counter_path = tmp_path / "http.jsonl"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=counter_path,
        send_callable=lambda *args, **kwargs: response,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    result = client.send_once(
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
    )
    assert result.outcome_class == "oversized"
    assert len(headers) == 99
    assert response.raw.read_calls == 0
    record = json.loads(counter_path.read_text(encoding="utf-8"))
    assert record["canonical_status_header_bytes"] == header_bytes
    assert (
        record["canonical_status_header_bytes"] - (header_bytes - 1)
        <= transport.SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
    )
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_path=counter_path,
        )
    assert not ledger.eligible
    assert "aggregate_ceiling_crossed" in ledger.validation_errors


def test_body_chunk_crosses_aggregate_while_body_stays_within_streaming_cap(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    body = b"aggregate-crossing-body"
    response = _response(body)
    header_bytes = len(
        transport._canonical_status_header_bytes(
            response,
            transport._header_pairs(response),
        )
    )
    remaining = header_bytes + len(body) - 1
    assert len(body) <= remaining
    _set_first_request_limits(session_factory, max_run_bytes=remaining)
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "http.jsonl",
        send_callable=lambda *args, **kwargs: response,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    result = client.send_once(
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
    )
    assert result.outcome_class == "oversized"
    assert result.delivered_body_bytes == len(body)


def test_aggregate_exact_boundary_completes_without_crossing(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    body = b"exact-boundary"
    response = _response(body)
    header_bytes = len(
        transport._canonical_status_header_bytes(
            response,
            transport._header_pairs(response),
        )
    )
    _set_first_request_limits(
        session_factory,
        max_run_bytes=header_bytes + len(body),
    )
    counter_path = tmp_path / "http.jsonl"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=counter_path,
        send_callable=lambda *args, **kwargs: response,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    result = client.send_once(
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
    )
    assert result.outcome_class == "completed"
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_path=counter_path,
        )
    assert ledger.eligible


def test_body_stage_crossing_without_aggregate_crossing_is_oversized(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    body = b"12345"
    response = _response(body)
    header_bytes = len(
        transport._canonical_status_header_bytes(
            response,
            transport._header_pairs(response),
        )
    )
    max_run_bytes = header_bytes + len(body) + 100
    _set_first_request_limits(
        session_factory,
        max_run_bytes=max_run_bytes,
        stage_cap=len(body) - 1,
    )
    counter_path = tmp_path / "http.jsonl"
    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=counter_path,
        send_callable=lambda *args, **kwargs: response,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    result = client.send_once(
        ordinal=1,
        stage="exact_accession_api",
        request=_request(),
    )
    assert result.outcome_class == "oversized"
    assert result.counted_status_header_bytes + result.delivered_body_bytes < (
        max_run_bytes
    )
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_path=counter_path,
        )
    assert "aggregate_ceiling_crossed" not in ledger.validation_errors


def test_pre_status_transport_failure_has_one_null_status_counter(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    counter_path = tmp_path / "http.jsonl"

    def fail(*args, **kwargs):
        raise requests.ConnectionError("synthetic")

    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=counter_path,
        send_callable=fail,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_transport_failed"
    records = [
        json.loads(line)
        for line in counter_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["response_status"] is None
    assert records[0]["error_class"] == "transport_error"
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
            counter_path=counter_path,
        )
    assert ledger.entries[0]["outcome_class"] == "transport_error"
    assert not ledger.eligible


def test_counter_write_failure_after_send_closes_terminal_and_response(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    _seed_running_run(session_factory)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    response = _response(b"delivered")
    sends = [0]

    def send(*args, **kwargs):
        sends[0] += 1
        return response

    client = transport.BoundedConnectorTransport(
        connector_run_id="strict-nrc-run",
        lease_token="lease-token",
        arming_fingerprint="d" * 64,
        counter_path=tmp_path / "absent-parent" / "http.jsonl",
        send_callable=send,
        dns_resolver=lambda host, port: ["8.8.8.8"],
    )
    with pytest.raises(transport.ConnectorEgressTransportError) as exc:
        client.send_once(
            ordinal=1,
            stage="exact_accession_api",
            request=_request(),
        )
    assert exc.value.code == "connector_egress_counter_write_failed"
    assert sends == [1]
    assert response.raw.closed
    with session_factory() as db:
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id="strict-nrc-run",
        )
    assert ledger.entries[0]["outcome_class"] == "counter_write_failed"
    assert "non_successful_send" in ledger.validation_errors
    assert not ledger.eligible
