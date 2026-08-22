"""Behavioral proof for the B0 reservation-before-effect boundary."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import sqlite3
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.connector_egress_contract import (  # noqa: E402
    AuthorityBindings,
    ContractHold,
    EffectResult,
    PhysicalRequestPlan,
    RequestLimits,
    physical_request_plan_from_document,
    validate_authority_envelope,
)
from app.services.connector_egress_transport import (  # noqa: E402
    CommittedReservation,
    ConnectorEgressTransport,
    EgressHold,
    ReservationFileIdentity,
    ReservationHold,
    ReservationIdentityProbe,
    ReservationStore,
    ReservationVolumeIdentity,
)
from app.services.sciencebase_reservation_security import (  # noqa: E402
    ReservationSecurityHold,
)


def _canonical_bytes(value: dict[str, object]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _envelope_dict(root: Path) -> dict[str, object]:
    return {
        "schema_version": "project6.connector_authority.v1",
        "campaign_id": "campaign-17",
        "canonical_root": str(root.resolve()),
        "connector_run_id": "11111111-1111-4111-8111-111111111111",
        "source_commit": "a" * 40,
        "interpreter_identity": "python:cpython-3.11.9:sha256:" + "b" * 64,
        "authorization_digest": "sha256:" + "c" * 64,
        "grant_digest": "sha256:" + "d" * 64,
        "wrapper_start_token_ref": "retired:sciencebase-live-v2",
    }


def _bindings(envelope: dict[str, object]) -> AuthorityBindings:
    return AuthorityBindings(**envelope)


def _plan(tmp_path: Path, **changes: object) -> PhysicalRequestPlan:
    values: dict[str, object] = {
        "envelope_digest": "sha256:" + "e" * 64,
        "campaign_id": "campaign-17",
        "canonical_root": str(tmp_path.resolve()),
        "connector_run_id": "11111111-1111-4111-8111-111111111111",
        "target_id": "sciencebase-item-7",
        "request_ordinal": 3,
        "stage": "download",
        "method": "GET",
        "canonical_destination": "https://www.sciencebase.gov/catalog/item/7",
        "header_names": (),
        "header_value_sha256s": (),
        "body_sha256": "sha256:" + hashlib.sha256(b"").hexdigest(),
        "limits": RequestLimits(timeout_seconds=4.0),
        "authorization_digest": "sha256:" + "c" * 64,
        "grant_digest": "sha256:" + "d" * 64,
    }
    values.update(changes)
    return PhysicalRequestPlan(**values)


def _reservation_database(tmp_path: Path) -> Path:
    database_path = (tmp_path / "reservation.db").resolve()
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE connector_run (
                connector_run_id VARCHAR(36) PRIMARY KEY
            );
            CREATE TABLE connector_run_event (
                connector_run_event_id VARCHAR(36) PRIMARY KEY,
                connector_run_id VARCHAR(36) NOT NULL REFERENCES connector_run(connector_run_id),
                connector_run_target_id VARCHAR(36),
                phase VARCHAR(100),
                stage VARCHAR(100),
                event_type VARCHAR(100) NOT NULL,
                status_before VARCHAR(50),
                status_after VARCHAR(50),
                reason_code VARCHAR(255),
                error_class VARCHAR(100),
                message TEXT,
                metrics_json JSON,
                created_at DATETIME
            );
            INSERT INTO connector_run(connector_run_id)
            VALUES ('11111111-1111-4111-8111-111111111111');
            """
        )
    return database_path


def _store(
    database_path: Path,
    *,
    identity_probe: ReservationIdentityProbe | None = None,
    reservation_security=None,
) -> ReservationStore:
    kwargs: dict[str, object] = {
        "identity_probe": (
            identity_probe if identity_probe is not None else _TestIdentityProbe()
        ),
        "reservation_security": (
            reservation_security
            if reservation_security is not None
            else _RecordingReservationSecurity()
        ),
    }
    return ReservationStore(database_path.parent, database_path, **kwargs)


class _RecordingReservationSecurity:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.database_failure: str | None = None
        self.birth_failure: str | None = None
        self.restore_failure: str | None = None
        self.journal_failure: str | None = None
        self.cleanup_failure: str | None = None

    def verify_database(self, _database: Path) -> None:
        self.events.append("database")
        if self.database_failure is not None:
            raise ReservationSecurityHold(self.database_failure)

    @contextmanager
    def birth_scope(self):
        self.events.append("birth-enter")
        if self.birth_failure is not None:
            raise ReservationSecurityHold(self.birth_failure)
        try:
            yield
        finally:
            self.events.append("birth-exit")
            if self.restore_failure is not None:
                raise ReservationSecurityHold(self.restore_failure)

    def verify_transient_journal(self, _database: Path, journal: Path) -> None:
        self.events.append("journal")
        assert journal.is_file()
        if self.journal_failure is not None:
            raise ReservationSecurityHold(self.journal_failure)

    def verify_journal_absent(self, journal: Path) -> None:
        self.events.append("absent")
        assert not journal.exists()
        if self.cleanup_failure is not None:
            raise ReservationSecurityHold(self.cleanup_failure)


class _TestIdentityProbe:
    def __init__(self) -> None:
        self.replaced_path: Path | None = None
        self.replace_after_database_observations: int | None = None

    def canonicalize(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def pin(self, path: Path, *, directory: bool) -> None:
        assert path.is_dir() is directory

    def volume(self, path: Path) -> ReservationVolumeIdentity:
        return ReservationVolumeIdentity("test-volume", fixed=True, local=True)

    def identity(self, path: Path, *, directory: bool) -> ReservationFileIdentity:
        identity = f"file:{path.name}"
        if (
            path.name == ReservationStore.DATABASE_BASENAME
            and self.replace_after_database_observations is not None
        ):
            self.replace_after_database_observations -= 1
            if self.replace_after_database_observations == 0:
                self.replaced_path = path
        if self.replaced_path == path:
            identity += ":replacement"
        return ReservationFileIdentity(
            "test-volume",
            identity,
            1,
            reparse=False,
            directory=directory,
        )

    def close(self) -> None:
        pass


class _Response:
    def __init__(
        self,
        body: bytes = b'{"ok":true}',
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.body = body
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}
        self.closed = False

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [
            self.body[index : index + chunk_size]
            for index in range(0, len(self.body), chunk_size)
        ]

    def close(self) -> None:
        self.closed = True


class _Session:
    def __init__(self, events: list[str], response: _Response) -> None:
        self.events = events
        self.response = response
        self.closed = False

    def request(self, method: str, url: str, **kwargs: object) -> _Response:
        self.events.append(f"send:{method}:{url}")
        self.kwargs = kwargs
        return self.response

    def close(self) -> None:
        self.closed = True


def test_canonical_content_addressed_envelope_binds_every_authority_field(
    tmp_path: Path,
) -> None:
    document = _envelope_dict(tmp_path)
    raw = _canonical_bytes(document)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()

    envelope = validate_authority_envelope(raw, digest, _bindings(document))

    assert envelope.content_digest == digest
    assert envelope.campaign_id == "campaign-17"
    assert envelope.connector_run_id == "11111111-1111-4111-8111-111111111111"


def test_authority_envelope_emitter_is_exact_complete_and_non_authorizing(
    tmp_path: Path,
) -> None:
    from app.services import connector_egress_contract as contract

    document = _envelope_dict(tmp_path)

    raw = contract.emit_authority_envelope(document)

    assert raw == _canonical_bytes(document)
    assert set(json.loads(raw)) == {
        "schema_version",
        "campaign_id",
        "canonical_root",
        "connector_run_id",
        "source_commit",
        "interpreter_identity",
        "authorization_digest",
        "grant_digest",
        "wrapper_start_token_ref",
    }
    incomplete = dict(document)
    incomplete.pop("source_commit")
    with pytest.raises(ContractHold, match="authority_envelope_fields_invalid"):
        contract.emit_authority_envelope(incomplete)
    assert tuple(tmp_path.iterdir()) == ()


def test_authority_envelope_requires_retired_wrapper_token_sentinel(
    tmp_path: Path,
) -> None:
    from app.services import connector_egress_contract as contract

    document = _envelope_dict(tmp_path)
    document["wrapper_start_token_ref"] = "wrapper-token:item-484"

    with pytest.raises(
        ContractHold, match="authority_envelope_field_invalid:wrapper_start_token_ref"
    ):
        contract.emit_authority_envelope(document)


def test_envelope_rejects_structurally_invalid_authorization_digest(
    tmp_path: Path,
) -> None:
    document = _envelope_dict(tmp_path)
    document["authorization_digest"] = "caller-says-yes"
    raw = _canonical_bytes(document)

    with pytest.raises(
        ContractHold, match="authority_envelope_field_invalid:authorization_digest"
    ):
        validate_authority_envelope(
            raw,
            "sha256:" + hashlib.sha256(raw).hexdigest(),
            _bindings(document),
        )


def test_slot_uuid_is_global_ordinal_while_plan_digest_detects_request_drift(
    tmp_path: Path,
) -> None:
    original = _plan(tmp_path)
    changed = _plan(
        tmp_path,
        target_id="different-target",
        stage="redirect",
        canonical_destination="https://www.sciencebase.gov/catalog/item/8",
    )

    assert original.slot_uuid == changed.slot_uuid
    assert original.plan_digest != changed.plan_digest


def test_physical_request_plan_rejects_nonpositive_global_ordinal(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ContractHold, match="physical_request_plan_invalid:request_ordinal"
    ):
        _plan(tmp_path, request_ordinal=0)


@pytest.mark.parametrize(
    ("factory", "reason"),
    [
        (
            lambda root: _plan(root, request_ordinal=True),
            "physical_request_plan_invalid:request_ordinal",
        ),
        (
            lambda root: RequestLimits(timeout_seconds=True),
            "request_limits_invalid:timeout_seconds",
        ),
        (
            lambda root: RequestLimits(timeout_seconds=4.0, max_response_bytes=True),
            "request_limits_invalid:max_response_bytes",
        ),
        (
            lambda root: RequestLimits(timeout_seconds=4.0, max_redirects=False),
            "request_limits_invalid:max_redirects",
        ),
        (
            lambda root: EffectResult(
                "11111111-1111-4111-8111-111111111111",
                "sha256:" + "e" * 64,
                True,
                b"",
            ),
            "effect_result_invalid:status_code",
        ),
    ],
)
def test_integer_contract_fields_reject_bool(
    tmp_path: Path,
    factory: object,
    reason: str,
) -> None:
    with pytest.raises(ContractHold, match=reason):
        factory(tmp_path)  # type: ignore[operator]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"reservation_event_id": "not-a-uuid"}, "reservation_event_id"),
        ({"plan_digest": "not-a-digest"}, "plan_digest"),
        ({"body": bytearray()}, "body"),
        ({"response_header_names": ["content-type"]}, "response_header_names"),
        ({"response_header_names": (7,)}, "response_header_names"),
        ({"response_header_names": ("Content-Type",)}, "response_header_names"),
        ({"status_code": 302, "redirect_location": 7}, "redirect_location"),
        (
            {"status_code": 302, "redirect_location": "javascript:alert(1)"},
            "redirect_location",
        ),
        ({"status_code": 302, "redirect_location": None}, "redirect_location"),
        ({"status_code": 200, "redirect_location": "/unexpected"}, "redirect_location"),
    ],
)
def test_effect_result_strictly_rejects_malformed_fields(
    tmp_path: Path,
    changes: dict[str, object],
    reason: str,
) -> None:
    plan = _plan(tmp_path)
    values: dict[str, object] = {
        "reservation_event_id": plan.slot_uuid,
        "plan_digest": plan.plan_digest,
        "status_code": 200,
        "body": b"",
        "response_header_names": ("content-type",),
        "redirect_location": None,
    }
    values.update(changes)

    with pytest.raises(ContractHold, match=f"effect_result_invalid:{reason}"):
        EffectResult(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"header_names": (7,)}, "physical_request_plan_invalid:header_names"),
        (
            {"header_value_sha256s": (7,)},
            "physical_request_plan_invalid:header_value_sha256s",
        ),
    ],
)
def test_non_string_sequence_fields_raise_deterministic_contract_hold(
    tmp_path: Path,
    changes: dict[str, object],
    reason: str,
) -> None:
    with pytest.raises(ContractHold, match=reason):
        _plan(tmp_path, **changes)


def test_physical_request_plan_document_round_trip_preserves_digest(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)

    decoded = physical_request_plan_from_document(plan.to_document())

    assert decoded == plan
    assert decoded.plan_digest == plan.plan_digest


def test_reservation_is_committed_as_connector_run_event_and_independently_visible(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)

    result = _store(database_path).reserve(plan)

    assert isinstance(result, CommittedReservation)
    assert result.disposition == "RESERVED"
    with sqlite3.connect(database_path) as independent:
        row = independent.execute(
            "SELECT event_type, reason_code, metrics_json FROM connector_run_event WHERE connector_run_event_id = ?",
            (plan.slot_uuid,),
        ).fetchone()
    assert row is not None
    assert row[0:2] == ("physical_request_reserved", "physical_request_reserved")
    assert json.loads(row[2])["plan_digest"] == plan.plan_digest


def test_reservation_and_live_event_writes_share_birth_and_journal_scope(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    security = _RecordingReservationSecurity()
    store = _store(database_path, reservation_security=security)

    reservation = store.reserve(_plan(tmp_path))
    live_event = store.write_sciencebase_live_event(
        event_id="22222222-2222-4222-8222-222222222222",
        connector_run_id="11111111-1111-4111-8111-111111111111",
        phase="live_authority",
        stage="go",
        event_type="sciencebase_live_go_consumed",
        status_after="consumed",
        reason_code="owner_go_consumed",
        metrics={"schema": "project6.sciencebase_live_evidence.v1"},
    )

    assert isinstance(reservation, CommittedReservation)
    assert live_event.disposition == "RECORDED"
    lifecycle = [event for event in security.events if event != "database"]
    assert lifecycle == [
        "birth-enter",
        "journal",
        "absent",
        "birth-exit",
        "birth-enter",
        "journal",
        "absent",
        "birth-exit",
    ]


def test_runtime_write_restores_delete_journal_mode_before_transaction(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)
    security = _RecordingReservationSecurity()

    result = _store(database_path, reservation_security=security).reserve(
        _plan(tmp_path)
    )

    assert isinstance(result, CommittedReservation)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)
    assert security.events.count("journal") == 1


def test_existing_reservation_rolls_back_without_demanding_a_journal(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    security = _RecordingReservationSecurity()
    store = _store(database_path, reservation_security=security)
    plan = _plan(tmp_path)
    assert isinstance(store.reserve(plan), CommittedReservation)
    security.events.clear()

    result = store.reserve(plan)

    assert isinstance(result, ReservationHold)
    assert result.disposition == "SPENT"
    assert [event for event in security.events if event != "database"] == [
        "birth-enter",
        "absent",
        "birth-exit",
    ]


def test_durable_database_acl_failure_uses_stable_hold_code(tmp_path: Path) -> None:
    database_path = _reservation_database(tmp_path)
    security = _RecordingReservationSecurity()
    security.database_failure = "reservation_database_security_invalid"

    with pytest.raises(EgressHold, match="HOLD:reservation_database_security_invalid"):
        _store(database_path, reservation_security=security)


@pytest.mark.parametrize(
    ("failure_field", "code"),
    [
        ("birth_failure", "reservation_birth_token_invalid"),
        ("restore_failure", "reservation_birth_token_restore_failed"),
        ("journal_failure", "reservation_journal_missing"),
        ("journal_failure", "reservation_journal_binding_invalid"),
        ("journal_failure", "reservation_journal_security_invalid"),
        ("cleanup_failure", "reservation_journal_cleanup_indeterminate"),
    ],
)
def test_reservation_security_failures_return_stable_holds(
    tmp_path: Path, failure_field: str, code: str
) -> None:
    database_path = _reservation_database(tmp_path)
    security = _RecordingReservationSecurity()
    setattr(security, failure_field, code)
    store = _store(database_path, reservation_security=security)

    result = store.reserve(_plan(tmp_path))

    assert isinstance(result, ReservationHold)
    assert result.disposition == "HOLD"
    assert result.reason_code == code


@pytest.mark.parametrize(
    ("unsafe_form", "reason"),
    [
        ("alternate", "reservation_database_path_mismatch"),
        ("hardlink", "reservation_database_identity_drift"),
    ],
)
@pytest.mark.skipif(os.name != "nt", reason="requires Windows file identity APIs")
def test_unsafe_reservation_database_is_rejected_before_any_effect(
    tmp_path: Path,
    unsafe_form: str,
    reason: str,
) -> None:
    database_path = _reservation_database(tmp_path)
    asserted_path = database_path
    if unsafe_form == "alternate":
        asserted_path = tmp_path / "alternate.db"
        asserted_path.touch()
    else:
        os.link(database_path, tmp_path / "reservation-link.db")
    session_constructed = False

    def forbidden_session() -> _Session:
        nonlocal session_constructed
        session_constructed = True
        raise AssertionError("session constructed for alternate reservation database")

    with pytest.raises(EgressHold, match=f"HOLD:{reason}"):
        store = ReservationStore(
            tmp_path.resolve(),
            asserted_path.resolve(),
            reservation_security=_RecordingReservationSecurity(),
        )
        ConnectorEgressTransport(store, session_factory=forbidden_session).execute(
            _plan(tmp_path)
        )

    assert session_constructed is False


def test_database_replacement_at_commit_boundary_holds_before_session(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    probe = _TestIdentityProbe()
    store = _store(database_path, identity_probe=probe)
    probe.replace_after_database_observations = 6
    session_constructed = False

    def forbidden_session() -> _Session:
        nonlocal session_constructed
        session_constructed = True
        raise AssertionError("session constructed after database replacement")

    with pytest.raises(EgressHold, match="HOLD:reservation_database_identity_drift"):
        ConnectorEgressTransport(store, session_factory=forbidden_session).execute(
            _plan(tmp_path)
        )

    assert session_constructed is False
    with sqlite3.connect(database_path) as independent:
        assert (
            independent.execute("SELECT COUNT(*) FROM connector_run_event").fetchone()[
                0
            ]
            == 1
        )


def test_reservation_identity_failure_suppresses_path_bearing_cause(
    tmp_path: Path,
) -> None:
    sentinel = "SENTINEL-SECRET-RESERVATION-PATH"

    class FailingProbe(_TestIdentityProbe):
        def canonicalize(self, path: Path) -> Path:
            raise OSError(f"{sentinel}:{path}")

    with pytest.raises(
        EgressHold,
        match="HOLD:reservation_database_identity_invalid",
    ) as caught:
        ReservationStore(
            tmp_path.resolve(),
            identity_probe=FailingProbe(),
            reservation_security=_RecordingReservationSecurity(),
        )

    rendered = "".join(
        traceback.format_exception(
            type(caught.value),
            caught.value,
            caught.value.__traceback__,
        )
    )
    assert sentinel not in rendered
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_exact_existing_reservation_is_spent_and_never_reowned(tmp_path: Path) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)
    store = _store(database_path)
    first = store.reserve(plan)

    second = store.reserve(plan)

    assert isinstance(first, CommittedReservation)
    assert isinstance(second, ReservationHold)
    assert second.disposition == "SPENT"
    assert second.reason_code == "reservation_already_spent"


def test_reservation_write_failure_returns_terminal_hold_without_event(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "DELETE FROM connector_run WHERE connector_run_id = ?",
            (plan.connector_run_id,),
        )

    result = _store(database_path).reserve(plan)

    assert isinstance(result, ReservationHold)
    assert result.disposition == "HOLD"
    assert result.reason_code == "reservation_write_failed"
    with sqlite3.connect(database_path) as independent:
        assert (
            independent.execute("SELECT COUNT(*) FROM connector_run_event").fetchone()[
                0
            ]
            == 0
        )


def test_changed_plan_in_same_global_slot_is_terminal_hold(tmp_path: Path) -> None:
    database_path = _reservation_database(tmp_path)
    store = _store(database_path)
    original = _plan(tmp_path)
    changed = _plan(tmp_path, target_id="different-target", stage="redirect")
    store.reserve(original)

    result = store.reserve(changed)

    assert isinstance(result, ReservationHold)
    assert result.disposition == "HOLD"
    assert result.reason_code == "reservation_slot_conflict"


def test_concurrent_exact_plans_have_one_owner_and_all_others_spent(
    tmp_path: Path,
) -> None:
    store = _store(_reservation_database(tmp_path))
    plan = _plan(tmp_path)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.reserve(plan), range(8)))

    assert sum(isinstance(result, CommittedReservation) for result in results) == 1
    assert (
        sum(
            isinstance(result, ReservationHold) and result.disposition == "SPENT"
            for result in results
        )
        == 7
    )


def test_restart_probe_reports_spent_after_any_committed_reservation(
    tmp_path: Path,
) -> None:
    store = _store(_reservation_database(tmp_path))
    plan = _plan(tmp_path)
    assert store.assert_no_reservations(plan.connector_run_id) is None
    store.reserve(plan)

    result = store.assert_no_reservations(plan.connector_run_id)

    assert isinstance(result, ReservationHold)
    assert result.disposition == "SPENT"
    assert result.reason_code == "connector_run_has_reservation"


def test_transport_observes_commit_before_session_construction_or_send(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)
    events: list[str] = []
    response = _Response()

    def session_factory() -> _Session:
        with sqlite3.connect(database_path) as independent:
            event = independent.execute(
                "SELECT event_type FROM connector_run_event WHERE connector_run_event_id = ?",
                (plan.slot_uuid,),
            ).fetchone()
        assert event == ("physical_request_reserved",)
        events.append("session")
        return _Session(events, response)

    result = ConnectorEgressTransport(
        _store(database_path), session_factory=session_factory
    ).execute(plan)

    assert events == ["session", f"send:GET:{plan.canonical_destination}"]
    assert result.body == b'{"ok":true}'
    assert result.reservation_event_id == plan.slot_uuid
    assert response.closed is True


def test_spent_reservation_blocks_second_session_and_send(tmp_path: Path) -> None:
    database_path = _reservation_database(tmp_path)
    sessions: list[_Session] = []

    def session_factory() -> _Session:
        session = _Session([], _Response())
        sessions.append(session)
        return session

    transport = ConnectorEgressTransport(
        _store(database_path), session_factory=session_factory
    )
    plan = _plan(tmp_path)
    transport.execute(plan)

    with pytest.raises(EgressHold, match="SPENT:reservation_already_spent"):
        transport.execute(plan)

    assert len(sessions) == 1


def test_reservation_failure_blocks_session_construction(tmp_path: Path) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "DELETE FROM connector_run WHERE connector_run_id = ?",
            (plan.connector_run_id,),
        )
    session_constructed = False

    def forbidden_session() -> _Session:
        nonlocal session_constructed
        session_constructed = True
        raise AssertionError("session construction crossed HOLD")

    with pytest.raises(EgressHold, match="HOLD:reservation_write_failed"):
        ConnectorEgressTransport(
            _store(database_path), session_factory=forbidden_session
        ).execute(plan)

    assert session_constructed is False


def test_header_commitment_mismatch_holds_before_session_and_never_persists_value(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    secret = "sentinel-secret-value"
    plan = _plan(
        tmp_path,
        header_names=("accept",),
        header_value_sha256s=(
            "sha256:" + hashlib.sha256(b"application/json").hexdigest(),
        ),
    )
    session_constructed = False

    def forbidden_session() -> _Session:
        nonlocal session_constructed
        session_constructed = True
        raise AssertionError("session constructed with mismatched headers")

    transport = ConnectorEgressTransport(
        _store(database_path),
        session_factory=forbidden_session,
        request_headers={"accept": secret},
    )

    with pytest.raises(
        EgressHold, match="HOLD:request_header_commitment_mismatch"
    ) as caught:
        transport.execute(plan)

    assert session_constructed is False
    assert secret not in str(caught.value)
    assert secret.encode() not in database_path.read_bytes()


def test_redirect_is_returned_without_automation_for_a_new_reserved_ordinal(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    response = _Response(b"", status_code=302, headers={"Location": "/catalog/item/8"})
    session = _Session([], response)

    result = ConnectorEgressTransport(
        _store(database_path),
        session_factory=lambda: session,
    ).execute(_plan(tmp_path))

    assert result.status_code == 302
    assert result.redirect_location == "/catalog/item/8"
    assert session.kwargs["allow_redirects"] is False
    assert len(session.events) == 1


def test_ambiguous_redirect_location_is_terminal_hold_and_not_followed(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    response = _Response(
        b"", status_code=302, headers={"Location": "javascript:alert(1)"}
    )
    session = _Session([], response)

    with pytest.raises(EgressHold, match="HOLD:transport_redirect_invalid"):
        ConnectorEgressTransport(
            _store(database_path),
            session_factory=lambda: session,
        ).execute(_plan(tmp_path))

    assert len(session.events) == 1
    assert response.closed is True
    assert session.closed is True


def test_non_string_response_header_name_is_sanitized_hold(tmp_path: Path) -> None:
    database_path = _reservation_database(tmp_path)
    response = _Response(headers={7: "invalid"})  # type: ignore[dict-item]
    session = _Session([], response)

    with pytest.raises(EgressHold, match="HOLD:transport_response_headers_invalid"):
        ConnectorEgressTransport(
            _store(database_path),
            session_factory=lambda: session,
        ).execute(_plan(tmp_path))

    assert response.closed is True
    assert session.closed is True


def test_response_limit_holds_after_exact_ceiling_and_closes_resources(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    response = _Response(b"12345")
    session = _Session([], response)
    plan = _plan(
        tmp_path, limits=RequestLimits(timeout_seconds=4.0, max_response_bytes=4)
    )

    with pytest.raises(EgressHold, match="HOLD:transport_response_too_large"):
        ConnectorEgressTransport(
            _store(database_path),
            session_factory=lambda: session,
        ).execute(plan)

    assert response.closed is True
    assert session.closed is True
    assert _store(database_path).reserve(plan).disposition == "SPENT"


def test_cleanup_failures_attempt_both_closes_and_raise_sanitized_hold(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    closed: list[str] = []

    class FailingResponse(_Response):
        def close(self) -> None:
            closed.append("response")
            raise OSError("sentinel-response-close")

    class FailingSession(_Session):
        def close(self) -> None:
            closed.append("session")
            raise OSError("sentinel-session-close")

    session = FailingSession([], FailingResponse())

    with pytest.raises(EgressHold, match="HOLD:transport_cleanup_failed") as caught:
        ConnectorEgressTransport(
            _store(database_path),
            session_factory=lambda: session,
        ).execute(_plan(tmp_path))

    assert closed == ["response", "session"]
    assert "sentinel" not in str(caught.value)


def test_all_injected_external_capable_markers_observe_independent_commit(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)
    observed: list[str] = []

    def marker(name: str) -> None:
        with sqlite3.connect(database_path) as independent:
            row = independent.execute(
                "SELECT metrics_json FROM connector_run_event WHERE connector_run_event_id = ?",
                (plan.slot_uuid,),
            ).fetchone()
        assert row is not None
        assert json.loads(row[0])["plan_digest"] == plan.plan_digest
        observed.append(name)

    class BoundarySession(_Session):
        def __init__(self) -> None:
            marker("session")
            super().__init__(observed, _Response())

        def request(self, method: str, url: str, **kwargs: object) -> _Response:
            for effect in (
                "dns",
                "socket_create",
                "socket_connect",
                "tls_wrap",
                "send",
                "loopback_accept",
            ):
                marker(effect)
            self.kwargs = kwargs
            return self.response

    ConnectorEgressTransport(
        _store(database_path),
        session_factory=BoundarySession,
    ).execute(plan)

    assert observed == [
        "session",
        "dns",
        "socket_create",
        "socket_connect",
        "tls_wrap",
        "send",
        "loopback_accept",
    ]


def test_ordering_probe_kills_mutant_that_constructs_session_before_reserve(
    tmp_path: Path,
) -> None:
    database_path = _reservation_database(tmp_path)
    plan = _plan(tmp_path)

    def guarded_session_factory() -> _Session:
        with sqlite3.connect(database_path) as independent:
            count = independent.execute(
                "SELECT COUNT(*) FROM connector_run_event WHERE connector_run_event_id = ?",
                (plan.slot_uuid,),
            ).fetchone()[0]
        assert count == 1, "mutation detected: session before committed reservation"
        return _Session([], _Response())

    with pytest.raises(AssertionError, match="mutation detected"):
        guarded_session_factory()
