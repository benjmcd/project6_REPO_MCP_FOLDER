"""Loopback coverage for the bounded connector transport streaming read loop.

These tests drive ``BoundedConnectorTransport.send_once`` against a real
127.0.0.1 TCP listener with ``send_callable`` left at its ``None`` default, so
the certified adapter -> urllib3 -> http.client -> socket stack is exercised
unmodified.  That stack is the subject: once a ``Content-Length`` body has been
fully delivered, ``http.client`` clears ``HTTPResponse.fp`` and urllib3 releases
the pooled connection (``response.py`` ``release_conn``, reached from
``_error_catcher`` when ``_original_response.isclosed()``), after which the
transport has no socket left to re-arm before its next loop pass.  A fully
delivered body must still classify ``completed``.

The transport is constructed exactly as the production call sites construct it
-- ``connector_run_id`` / ``lease_token`` / ``arming_fingerprint`` /
``counter_path`` and nothing else (``connectors_nrc_adams.py``
``_build_strict_nrc_transport``, ``connectors_sciencebase.py``
``_build_sciencebase_strict_transport``); both shapes are covered.

Only four seams are stubbed, none of them below the send:

* ``SESSION_FACTORY`` -> in-memory SQLite (established fixture idiom).
* ``_revalidate_run_authority`` -> envelope passthrough (established idiom).
* ``_default_dns_resolver`` -> a public answer, patched at module level rather
  than passed to the constructor so the construction shape stays identical to
  the production call sites.  The stub records its calls and the transfers
  assert it was the resolver actually used, so a patch-order regression cannot
  silently emit a live lookup.
* ``_validate_exact_request`` -> permits the one loopback URL and delegates
  everything else.  The certified guard requires ``https`` on port 443, and the
  pinned runtime has no way to mint a trusted certificate, so the transfer runs
  in cleartext.  The release-then-re-arm mechanism under test is identical for
  both schemes: it depends on ``http.client`` clearing ``fp`` once the declared
  length is consumed, not on the socket implementation.  Reservation evidence
  therefore still records the canonical production host.  The candidate chain
  does differ under TLS (candidate 1 would be an ``ssl.SSLSocket``), so the
  transfers additionally assert *which* candidate armed, making the divergence
  from the live HTTPS run explicit rather than implicit.  One further
  consequence: the terminal ledger recomputes the reservation fingerprint from
  the canonical https authority URL, so ledger eligibility is structurally
  unreachable here and is asserted as the exact seam rather than as success.

The arming helper is wrapped by a pass-through spy (nothing below the send is
faked) so the post-release unarmed pass is asserted to have actually occurred:
without it the transfers would pass vacuously on any runtime that stopped
releasing the connection mid-loop.

Ordinal 1 is used for both connectors because later ordinals additionally
require committed derived arming plus a reconciled prior counter stream,
neither of which changes the read loop being covered.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import socket
import sys
import threading
from typing import Any, NamedTuple

import pytest
import urllib3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base  # noqa: E402
from app.models import ConnectorRun, ConnectorRunEvent  # noqa: E402
from app.schemas.api import expected_grant_rule_payloads  # noqa: E402
from app.services import connector_egress_transport as transport  # noqa: E402

PINNED_URLLIB3_VERSION = "2.7.0"

# Resolved tolerantly so this file still imports and collects against the
# unpatched revision, where the helper is named ``_set_raw_socket_timeout`` and
# returns a bool rather than the tri-state.
_TRI_STATE_AVAILABLE = hasattr(transport, "_arm_raw_socket_timeout")
_ARM_HELPER_NAME = (
    "_arm_raw_socket_timeout" if _TRI_STATE_AVAILABLE else "_set_raw_socket_timeout"
)

_ARMED = "armed"
_NO_SOCKET = "no_socket"
_FAILED = "failed"

_UNARMED_DATA_CODE = "connector_egress_transport_post_release_unarmed_data"

_ARMING_FINGERPRINT = "d" * 64
_LEASE_TOKEN = "loopback-lease-token"
_MAX_RUN_BYTES = 1024 * 1024

# Larger than one streaming read, mirroring the live artifact signature.
_MULTI_CHUNK_BODY_BYTES = 2 * transport.STREAM_READ_CHUNK_BYTES + 14_928
_SINGLE_CHUNK_BODY_BYTES = 11

# ``connection.sock``: the second entry of the arming candidate walk.
_CONNECTION_SOCK_CANDIDATE = 1

_RESPONSE_CONTENT_TYPE = "application/octet-stream"
_BODY_FILLER = b"loopback egress fixture octets\n"

_ACCEPT_TIMEOUT_SECONDS = 10.0
_IO_TIMEOUT_SECONDS = 10.0
_JOIN_TIMEOUT_SECONDS = 30.0


@pytest.fixture(autouse=True)
def _pinned_urllib3() -> None:
    """Bind the behavioural assumption to every transfer in this module."""
    assert urllib3.__version__ == PINNED_URLLIB3_VERSION


def _is_armed(outcome: Any) -> bool:
    """True for the armed result under either the bool or tri-state revision."""
    return outcome is True or outcome == _ARMED


def _is_failed(outcome: Any) -> bool:
    return outcome == _FAILED


def _armable_candidate_index(raw: Any) -> int | None:
    """Index of the first candidate exposing a callable ``settimeout``.

    Mirrors the production candidate walk so the transfers can state which
    candidate armed without the production helper having to report it.
    """
    target = raw._raw if isinstance(raw, transport._CountingRawReadPath) else raw
    candidates: list[Any] = [target]
    connection = getattr(target, "_connection", None)
    if connection is not None:
        candidates.append(getattr(connection, "sock", None))
    http_response = getattr(target, "_fp", None)
    buffered = getattr(http_response, "fp", None)
    socket_io = getattr(buffered, "raw", None)
    candidates.append(getattr(socket_io, "_sock", None))
    for index, candidate in enumerate(candidates):
        if callable(getattr(candidate, "settimeout", None)):
            return index
    return None


class _ArmingSpy(NamedTuple):
    outcomes: list[Any]
    armed_candidates: list[int | None]

    @property
    def call_count(self) -> int:
        return len(self.outcomes)


def _install_arming_spy(monkeypatch) -> _ArmingSpy:
    """Pass-through wrapper over the real arming helper (no faking below it)."""
    original = getattr(transport, _ARM_HELPER_NAME)
    spy = _ArmingSpy(outcomes=[], armed_candidates=[])

    def wrapper(raw: Any, timeout_seconds: float) -> Any:
        outcome = original(raw, timeout_seconds)
        spy.outcomes.append(outcome)
        if _is_armed(outcome):
            spy.armed_candidates.append(_armable_candidate_index(raw))
        return outcome

    monkeypatch.setattr(transport, _ARM_HELPER_NAME, wrapper)
    return spy


class _ConnectorShape(NamedTuple):
    """One production construction site, with its canonical ordinal-1 rule."""

    connector_key: str
    stage: str
    exact_path: str
    host: str
    path_class: str
    query_class: str
    credential_audience: str
    headers: tuple[tuple[str, str], ...]

    @property
    def run_id(self) -> str:
        return f"loopback-{self.connector_key}-run"


_NRC_SHAPE = _ConnectorShape(
    connector_key="nrc_adams_aps",
    stage="exact_accession_api",
    exact_path="/aps/api/search/ML17123A319",
    host="adams-api.nrc.gov",
    path_class="nrc_accession_exact",
    query_class="none",
    credential_audience="nrc_aps_api_key",
    headers=(
        ("Accept-Encoding", "identity"),
        ("Ocp-Apim-Subscription-Key", "secret"),
    ),
)
_SCIENCEBASE_SHAPE = _ConnectorShape(
    connector_key="sciencebase_mcs",
    stage="item_hydration",
    exact_path="/catalog/item/63d1a3c6d34e06fef15006be?format=json",
    host="www.sciencebase.gov",
    path_class="sciencebase_item_exact",
    query_class="format_json_exact",
    credential_audience="none",
    headers=(("Accept-Encoding", "identity"),),
)


def _fixture_body(size: int) -> bytes:
    if size <= 0:
        return b""
    repeats = size // len(_BODY_FILLER) + 1
    return (_BODY_FILLER * repeats)[:size]


class _LoopbackResponder:
    """Single-shot HTTP/1.1 responder on an ephemeral 127.0.0.1 port."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self._listener.settimeout(_ACCEPT_TIMEOUT_SECONDS)
        self.port = int(self._listener.getsockname()[1])
        self.request_head = b""
        self.failures: list[str] = []
        self._thread = threading.Thread(
            target=self._serve_once,
            name="connector-transport-loopback",
            daemon=True,
        )

    def __enter__(self) -> "_LoopbackResponder":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._thread.join(timeout=_JOIN_TIMEOUT_SECONDS)
        still_running = self._thread.is_alive()
        self._listener.close()
        if exc_type is None:
            assert not still_running, "loopback responder thread did not terminate"
            assert not self.failures, f"loopback responder failed: {self.failures}"

    def _serve_once(self) -> None:
        connection: socket.socket | None = None
        try:
            connection, _ = self._listener.accept()
            connection.settimeout(_IO_TIMEOUT_SECONDS)
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = connection.recv(65_536)
                if not chunk:
                    break
                head += chunk
            self.request_head = head
            status_and_headers = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {_RESPONSE_CONTENT_TYPE}\r\n"
                f"Content-Length: {len(self._body)}\r\n"
                "\r\n"
            ).encode("ascii")
            connection.sendall(status_and_headers + self._body)
            connection.shutdown(socket.SHUT_WR)
        except BaseException as exc:  # reported by __exit__
            self.failures.append(f"{type(exc).__name__}: {exc}")
        finally:
            if connection is not None:
                connection.close()


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


def _strict_envelope(shape: _ConnectorShape) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    canonical_rules = expected_grant_rule_payloads(shape.connector_key)
    return {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": shape.connector_key,
        "campaign_id": "7fe33e0a-c0e7-4f8e-9d55-8ba77a01ce23",
        "campaign_fingerprint": "a" * 64,
        "campaign_definition_sha256": "b" * 64,
        "campaign_introduction_index_revision": 1,
        "campaign_introduction_index_sha256": "c" * 64,
        "arming_fingerprint": _ARMING_FINGERPRINT,
        "grant_sha256": "e" * 64,
        "canonical_grant_fingerprint": "f" * 64,
        "code_revision": "test-revision",
        "max_physical_requests": len(canonical_rules),
        "max_run_bytes": _MAX_RUN_BYTES,
        "max_single_send_detection_allowance_bytes": (
            transport.SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
        ),
        "request_timeout_seconds": 30,
        "min_request_interval_ms": 0,
        "campaign_not_before": "2026-01-01T00:00:00.000000Z",
        "campaign_expires_at": transport.utc_six_z(expires_at),
        "grant_issued_at": "2026-01-01T00:00:00.000000Z",
        "grant_expires_at": transport.utc_six_z(expires_at),
        "request_rules": [dict(rule) for rule in canonical_rules],
    }


def _seed_running_run(factory, shape: _ConnectorShape) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ConnectorRun(
        connector_run_id=shape.run_id,
        connector_key=shape.connector_key,
        source_system=shape.connector_key,
        source_mode="strict_live_egress",
        status="running",
        request_config_json={"connector_egress_arming": _strict_envelope(shape)},
        request_fingerprint=_ARMING_FINGERPRINT,
        execution_lease_owner="test",
        execution_lease_token=_LEASE_TOKEN,
        execution_lease_expires_at=now + timedelta(minutes=5),
    )
    with factory() as db:
        db.add(run)
        db.commit()


def _loopback_request(
    shape: _ConnectorShape,
    port: int,
) -> transport.FrozenPhysicalRequest:
    return transport.FrozenPhysicalRequest(
        method="GET",
        url=f"http://127.0.0.1:{port}{shape.exact_path}",
        headers=dict(shape.headers),
        credential_audience=shape.credential_audience,
    )


def _permit_loopback_url(
    monkeypatch,
    *,
    shape: _ConnectorShape,
    url: str,
) -> None:
    original = transport._validate_exact_request

    def validate(request, *, rule):
        if request.url == url:
            return (shape.host, shape.path_class, shape.query_class)
        return original(request, rule=rule)

    monkeypatch.setattr(transport, "_validate_exact_request", validate)


def _install_recording_dns(monkeypatch) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []

    def resolver(host: str, port: int) -> list[str]:
        calls.append((host, port))
        return ["8.8.8.8"]

    monkeypatch.setattr(transport, "_default_dns_resolver", resolver)
    return calls


def test_pinned_urllib3_release_semantics() -> None:
    """The loopback expectations below are pinned to this urllib3 release."""
    assert urllib3.__version__ == PINNED_URLLIB3_VERSION


# ---------------------------------------------------------------------------
# Arming helper: pure-function tri-state coverage.
#
# The helper takes an arbitrary object and performs no I/O, so these stubs sit
# above the send rather than inside the transfer path.
# ---------------------------------------------------------------------------


class _StubSocket:
    def __init__(self, error: BaseException | None = None) -> None:
        self._error = error
        self.applied: list[float] = []

    def settimeout(self, value: float) -> None:
        if self._error is not None:
            raise self._error
        self.applied.append(value)


class _StubConnection:
    def __init__(self, sock: Any) -> None:
        self.sock = sock


class _StubRaw:
    """Mimics the urllib3 response shape the arming candidate walk inspects."""

    def __init__(
        self,
        *,
        own: _StubSocket | None = None,
        sock: _StubSocket | None = None,
    ) -> None:
        if own is not None:
            self.settimeout = own.settimeout
        self._connection = _StubConnection(sock) if sock is not None else None
        self._fp = None


tri_state = pytest.mark.skipif(
    not _TRI_STATE_AVAILABLE,
    reason="tri-state arming helper not present on this revision",
)


@tri_state
@pytest.mark.parametrize("error", [OSError("rejected"), ValueError("rejected")])
def test_rejecting_candidate_does_not_short_circuit_the_remaining_ones(
    error: BaseException,
) -> None:
    """Regression lock for the early-return defect."""
    refusing = _StubSocket(error)
    accepting = _StubSocket()
    raw = _StubRaw(own=refusing, sock=accepting)

    assert transport._arm_raw_socket_timeout(raw, 5.0) == transport._RAW_TIMEOUT_ARMED
    assert accepting.applied == [5.0]


@tri_state
def test_every_candidate_rejecting_classifies_failed() -> None:
    raw = _StubRaw(own=_StubSocket(OSError("no")), sock=_StubSocket(ValueError("no")))

    assert transport._arm_raw_socket_timeout(raw, 5.0) == transport._RAW_TIMEOUT_FAILED


@tri_state
def test_no_candidate_exposing_settimeout_classifies_no_socket() -> None:
    assert (
        transport._arm_raw_socket_timeout(_StubRaw(), 5.0)
        == transport._RAW_TIMEOUT_NO_SOCKET
    )


# ---------------------------------------------------------------------------
# Loopback transfers.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("shape", "body_size", "expect_unarmed_pass"),
    [
        (_NRC_SHAPE, _MULTI_CHUNK_BODY_BYTES, True),
        (_NRC_SHAPE, _SINGLE_CHUNK_BODY_BYTES, True),
        (_NRC_SHAPE, 0, False),
        (_SCIENCEBASE_SHAPE, _MULTI_CHUNK_BODY_BYTES, True),
    ],
    ids=[
        "nrc_multi_chunk",
        "nrc_single_chunk",
        "nrc_zero_length",
        "sciencebase_multi_chunk",
    ],
)
def test_fully_delivered_loopback_body_classifies_completed(
    session_factory,
    monkeypatch,
    tmp_path,
    shape: _ConnectorShape,
    body_size: int,
    expect_unarmed_pass: bool,
) -> None:
    _seed_running_run(session_factory, shape)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    dns_calls = _install_recording_dns(monkeypatch)
    arming = _install_arming_spy(monkeypatch)
    body = _fixture_body(body_size)
    counter_path = tmp_path / "http.jsonl"

    with _LoopbackResponder(body) as responder:
        request = _loopback_request(shape, responder.port)
        _permit_loopback_url(monkeypatch, shape=shape, url=request.url)
        client = transport.BoundedConnectorTransport(
            connector_run_id=shape.run_id,
            lease_token=_LEASE_TOKEN,
            arming_fingerprint=_ARMING_FINGERPRINT,
            counter_path=counter_path,
        )
        result = client.send_once(
            ordinal=1,
            stage=shape.stage,
            request=request,
        )

    # The stubbed resolver was the one actually consulted: no live lookup.
    assert dns_calls == [(shape.host, 443)]

    assert responder.request_head.startswith(
        f"GET {shape.exact_path} HTTP/1.1\r\n".encode("ascii")
    )
    assert result.outcome_class == "completed"
    assert result.response_status == 200
    assert result.body == body
    assert result.byte_count == body_size
    assert result.delivered_body_bytes == body_size
    assert result.body_sha256 == hashlib.sha256(body).hexdigest()
    assert result.safe_headers["content_type"] == _RESPONSE_CONTENT_TYPE

    # Non-vacuity: the post-release unarmed pass must actually have happened,
    # and no candidate may have refused arming outright.
    assert arming.outcomes, "arming helper was never consulted"
    assert not any(_is_failed(outcome) for outcome in arming.outcomes)
    unarmed = [outcome for outcome in arming.outcomes if not _is_armed(outcome)]
    if expect_unarmed_pass:
        assert unarmed, "expected a post-release unarmed pass; branch went untested"
    else:
        assert not unarmed
    # Cleartext loopback arms via ``connection.sock``; under TLS that candidate
    # is an ``ssl.SSLSocket``, which is the disclosed divergence from the live
    # HTTPS run.
    assert arming.armed_candidates
    assert set(arming.armed_candidates) == {_CONNECTION_SOCK_CANDIDATE}

    records = transport.parse_connector_counter_records(counter_path.read_bytes())
    assert len(records) == 1
    assert records[0]["error_class"] is None
    assert records[0]["response_status"] == 200
    assert records[0]["delivered_body_bytes"] == body_size
    assert records[0]["decoded_body_bytes"] == body_size

    with session_factory() as db:
        assert db.query(ConnectorRunEvent).count() == 2
        ledger = transport.derive_terminal_request_ledger(
            db,
            connector_run_id=shape.run_id,
            counter_path=counter_path,
        )
    # The terminal ledger independently recomputes the reservation fingerprint
    # from the canonical ``https://<authority-host><exact-path>`` URL
    # (``_validate_ledger_reservation`` in connector_egress_evidence.py), which
    # a cleartext 127.0.0.1 transfer can never match; the counter
    # reconciliation error then cascades from the dropped entry.  Ledger
    # eligibility is therefore structurally unreachable under the loopback seam
    # disclosed in the module docstring and is NOT what these transfers cover
    # -- the read-loop classification and the counter record above are.  The
    # exact seam is asserted so that any *other* derivation failure still fails
    # the test.
    assert ledger.eligible is False
    assert ledger.validation_errors == (
        "invalid_reservation_1",
        "counter_reconciliation_mismatch",
    )
    assert ledger.entries == ()


@tri_state
def test_data_on_an_unarmed_read_raises_the_distinct_code(
    session_factory,
    monkeypatch,
    tmp_path,
) -> None:
    """Bytes on a socket that could not be bounded are not a generic failure."""
    shape = _NRC_SHAPE
    _seed_running_run(session_factory, shape)
    monkeypatch.setattr(
        transport,
        "_revalidate_run_authority",
        lambda **kwargs: kwargs["envelope"],
    )
    _install_recording_dns(monkeypatch)

    calls: list[float] = []

    def never_arms(raw, timeout_seconds: float) -> str:
        calls.append(timeout_seconds)
        return transport._RAW_TIMEOUT_NO_SOCKET

    monkeypatch.setattr(transport, "_arm_raw_socket_timeout", never_arms)

    body = _fixture_body(_SINGLE_CHUNK_BODY_BYTES)
    counter_path = tmp_path / "http.jsonl"

    with _LoopbackResponder(body) as responder:
        request = _loopback_request(shape, responder.port)
        _permit_loopback_url(monkeypatch, shape=shape, url=request.url)
        client = transport.BoundedConnectorTransport(
            connector_run_id=shape.run_id,
            lease_token=_LEASE_TOKEN,
            arming_fingerprint=_ARMING_FINGERPRINT,
            counter_path=counter_path,
        )
        with pytest.raises(transport.ConnectorEgressTransportError) as excinfo:
            client.send_once(ordinal=1, stage=shape.stage, request=request)

    assert excinfo.value.code == _UNARMED_DATA_CODE
    # Single-shot: the unarmed branch is entered once and the loop is not
    # re-entered, so the helper is consulted exactly once.
    assert len(calls) == 1

    records = transport.parse_connector_counter_records(counter_path.read_bytes())
    assert len(records) == 1
    assert records[0]["error_class"] == "transport_error"
