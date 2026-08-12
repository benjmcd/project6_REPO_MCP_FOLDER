from __future__ import annotations

import io
import hashlib
import inspect
import json
import os
import struct
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import dual_live_effect_guard as effect_guard
from app.services.connector_egress_contract import (
    PhysicalRequestPlan,
    RequestLimits,
)
from app.services.connector_egress_transport import (
    CommittedReservation,
    ConnectorEgressTransport,
)
from app.services.dual_live_effect_guard import (
    MAX_FRAME_BYTES,
    EffectBoundaryHold,
    WorkerIdentity,
    decode_frame,
    encode_frame,
    read_frame,
    write_frame,
)
from app.services.dual_live_sciencebase_producer import (
    ScienceBaseInput,
    ScienceBaseProducer,
)
from app.services.dual_live_windows_boundary import (
    WindowsEffectBoundary,
    _mutex_name,
    _clear_inherited_pipe_handles,
    _validate_launch_handles,
    _validate_probe_denials,
    run_probe_worker,
)


SID = "S-1-15-2-123456789-42"
MONIKER = "Project6.B0.External.v1"


class FakeBackend:
    def __init__(self) -> None:
        self.mutex_collision = False
        self.mutex_handle = 101
        self.job_handle = 202
        self.worker_pid = 303
        self.worker_sid = SID
        self.worker_capability_count = 0
        self.process_handle = 405
        self.thread_handle = 404
        self.launched: tuple[object, ...] | None = None
        self.job_pids: tuple[int, ...] = (303,)
        self.tcp_sockets: tuple[str, ...] = ()
        self.udp_sockets: tuple[str, ...] = ()
        self.loopback_exempt = False
        self.closed: list[int] = []
        self.terminated: list[int] = []
        self.resume_result: int | BaseException = 1
        self.wait_result: int | BaseException = 0
        self.broker_thread_handle = 606
        self.cancelled_threads: list[int] = []
        self.cancel_event = threading.Event()

    def acquire_mutex(self, name: str) -> int:
        assert name.startswith("Local\\Project6DualLive-")
        if self.mutex_collision:
            raise EffectBoundaryHold("mutex_owned")
        return self.mutex_handle

    def create_job(self) -> int:
        return self.job_handle

    def launch_appcontainer_suspended(
        self,
        interpreter: str,
        args: tuple[str, ...],
        inherited_handles: tuple[int, ...],
        job_handle: int,
        *, profile_moniker: str, expected_package_sid: str, creation_flags: int,
    ) -> tuple[int, str, int, int]:
        assert creation_flags == 4
        self.launched = (
            interpreter, args, inherited_handles, job_handle,
            profile_moniker, expected_package_sid,
        )
        return self.worker_pid, self.worker_sid, self.worker_capability_count, self.process_handle, self.thread_handle

    def resume_thread(self, handle: int) -> int:
        assert handle == self.thread_handle
        if isinstance(self.resume_result, BaseException):
            raise self.resume_result
        return self.resume_result

    def query_job_pids(self, job_handle: int) -> tuple[int, ...]:
        assert job_handle == self.job_handle
        return self.job_pids

    def query_sockets(self, pids: tuple[int, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        assert pids == self.job_pids
        return self.tcp_sockets, self.udp_sockets

    def is_loopback_exempt(self, sid: str) -> bool:
        assert sid == SID
        return self.loopback_exempt

    def close_handle(self, handle: int) -> None:
        self.closed.append(handle)

    def terminate_job(self, handle: int) -> None:
        self.terminated.append(handle)

    def current_identity(self) -> WorkerIdentity:
        return identity()

    def probe_denials(self) -> tuple[int, int, int]:
        return 5, 10013, 1816

    def open_current_thread(self) -> int:
        return self.broker_thread_handle

    def cancel_synchronous_io(self, thread_handle: int) -> None:
        self.cancelled_threads.append(thread_handle)
        self.cancel_event.set()

    def wait_process(self, process_handle: int, timeout_ms: int) -> int:
        assert process_handle == self.process_handle
        assert timeout_ms == 15_000
        if isinstance(self.wait_result, BaseException):
            raise self.wait_result
        return self.wait_result


def identity(**changes: object) -> WorkerIdentity:
    values: dict[str, object] = {
        "pid": 303,
        "appcontainer_sid": SID,
        "is_appcontainer": True,
        "loopback_exempt": False,
        "job_pids": (303,),
        "tcp_sockets": (),
        "udp_sockets": (),
    }
    values.update(changes)
    return WorkerIdentity(**values)  # type: ignore[arg-type]


def make_boundary(backend: FakeBackend, validator: object | None = None) -> WindowsEffectBoundary:
    return WindowsEffectBoundary("C:/canonical/root", "campaign", backend=backend,
                                 bundle_binding=SimpleNamespace(
                                     profile_moniker=MONIKER, package_sid=SID,
                                 ), bundle_probe=object(),
                                 bundle_validator=validator or FakeBundleValidator(backend))


def test_hold_exposes_only_bounded_public_facts() -> None:
    hold = EffectBoundaryHold("socket_present", fact_digest="a" * 64)
    assert hold.code == "socket_present"
    assert hold.fact_digest == "a" * 64
    assert str(hold) == "socket_present:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert hold.args == (str(hold),)


@pytest.mark.parametrize(
    "code,digest",
    [
        ("UPPER", None),
        ("contains space", None),
        ("secret=value", None),
        ("ok", "short"),
        ("ok", "g" * 64),
    ],
)
def test_hold_rejects_unbounded_or_non_digest_facts(code: str, digest: str | None) -> None:
    with pytest.raises(ValueError):
        EffectBoundaryHold(code, fact_digest=digest)


def test_frame_is_length_prefixed_canonical_json() -> None:
    payload = {"type": "attestation", "pid": 7, "job_pids": [7], "ok": True}
    frame = encode_frame(payload)
    body = b'{"job_pids":[7],"ok":true,"pid":7,"type":"attestation"}'
    assert frame == struct.pack(">I", len(body)) + body
    assert decode_frame(frame) == payload


def test_frame_round_trip_stream_uses_one_exact_frame() -> None:
    stream = io.BytesIO()
    write_frame(stream, {"type": "hold", "code": "job_ambiguous"})
    stream.seek(0)
    assert read_frame(stream) == {"code": "job_ambiguous", "type": "hold"}
    assert stream.read() == b""


@pytest.mark.parametrize(
    "frame,code",
    [
        (b"", "frame_truncated"),
        (b"\x00\x00\x00\x05{}", "frame_truncated"),
        (b"\x00\x00\x00\x02{}x", "frame_trailing_bytes"),
        (b"\x00\x00\x00\x03bad", "frame_invalid_json"),
        (struct.pack(">I", MAX_FRAME_BYTES + 1), "frame_too_large"),
    ],
)
def test_frame_parser_fails_closed(frame: bytes, code: str) -> None:
    with pytest.raises(EffectBoundaryHold) as caught:
        decode_frame(frame)
    assert caught.value.code == code


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "hunter2"},
        {"credential": "abc"},
        {"token": "abc"},
        {"nested": {"api_key": "abc"}},
        {"raw_headers": {"authorization": "Bearer abc"}},
        {"bytes": b"abc"},
        ["not", "an", "object"],
    ],
)
def test_frame_rejects_secret_or_non_object_payloads(payload: object) -> None:
    with pytest.raises(EffectBoundaryHold) as caught:
        encode_frame(payload)  # type: ignore[arg-type]
    assert caught.value.code in {"frame_secret_field", "frame_invalid_value", "frame_not_object"}


def test_frame_allows_digest_and_opaque_reference_fields() -> None:
    payload = {
        "authorization_digest": "a" * 64,
        "grant_digest": "b" * 64,
        "wrapper_start_token_reference": "sha256:" + "c" * 64,
    }
    assert decode_frame(encode_frame(payload)) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {"credential_value": "raw"},
        {"authorization_header": "Bearer raw"},
        {"client_secret": "raw"},
        {"subscription_key": "raw"},
        {"authorization_digest": "raw secret"},
        {"wrapper_start_token_reference": "raw secret"},
        {"clientSecret": "raw"},
        {"apiKey": "raw"},
        {"accessKey": "raw"},
        {"bearer": "raw"},
    ],
)
def test_frame_rejects_sensitive_aliases_and_malformed_safe_suffixes(
    payload: dict[str, str],
) -> None:
    with pytest.raises(EffectBoundaryHold) as caught:
        encode_frame(payload)
    assert caught.value.code == "frame_secret_field"


@pytest.mark.parametrize(
    "body",
    [
        b'{"type":"hold","type":"attestation"}',
        b'{ "type":"hold"}',
        b'{"type": "hold"}',
        b'{"z":1,"a":2}',
    ],
)
def test_frame_rejects_duplicate_or_noncanonical_json(body: bytes) -> None:
    with pytest.raises(EffectBoundaryHold) as caught:
        decode_frame(struct.pack(">I", len(body)) + body)
    assert caught.value.code in {"frame_duplicate_key", "frame_noncanonical_json"}


def test_mutex_name_is_stable_and_does_not_disclose_root_or_campaign() -> None:
    root = str(Path("C:/Private/Root").resolve())
    first = _mutex_name(root, "campaign-private-name")
    second = _mutex_name(root.upper(), "campaign-private-name")
    assert first == second
    assert "Private" not in first
    assert "campaign" not in first
    assert len(first) < 90


@pytest.mark.parametrize(
    "handles",
    [(), (0,), (-1,), (4, 4), (4, 0), (4, True)],
)
def test_launch_requires_exact_distinct_positive_pipe_handles(handles: tuple[object, ...]) -> None:
    with pytest.raises(EffectBoundaryHold) as caught:
        _validate_launch_handles(handles)  # type: ignore[arg-type]
    assert caught.value.code == "pipe_handles_invalid"


def test_launch_accepts_exact_read_and_write_pipe_handles() -> None:
    assert _validate_launch_handles((40, 44)) == (40, 44)


def test_acquire_owns_mutex_and_kill_on_close_job_until_context_exit() -> None:
    backend = FakeBackend()
    boundary = make_boundary(backend)
    with boundary.acquire() as owned:
        assert owned is boundary
        assert backend.closed == []
        assert backend.terminated == []
    assert backend.terminated == [backend.job_handle]
    assert backend.closed == [backend.job_handle, backend.mutex_handle]


def test_mutex_collision_holds_without_creating_job() -> None:
    backend = FakeBackend()
    backend.mutex_collision = True
    boundary = make_boundary(backend)
    with pytest.raises(EffectBoundaryHold) as caught:
        with boundary.acquire():
            pass
    assert caught.value.code == "mutex_owned"
    assert backend.closed == []


def test_launch_is_once_and_passes_only_exact_handles_and_job() -> None:
    backend = FakeBackend()
    boundary = make_boundary(backend)
    with boundary.acquire():
        worker = boundary.launch_worker((40, 44))
        assert worker.pid == backend.worker_pid
        assert backend.launched == (
            str(Path("C:/Python/python.exe")),
            (
                "-I", "-S", str(Path("C:/bundle/worker.py")),
                "--worker-probe", "40", "44",
            ),
            (40, 44),
            backend.job_handle,
            MONIKER,
            SID,
        )
        assert backend.thread_handle in backend.closed
        assert backend.process_handle not in backend.closed
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.launch_worker((40, 44))
        assert caught.value.code == "worker_already_launched"
    assert backend.process_handle in backend.closed


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"is_appcontainer": False}, "worker_not_appcontainer"),
        ({"appcontainer_sid": "S-1-15-2-999"}, "worker_sid_mismatch"),
        ({"loopback_exempt": True}, "worker_loopback_exempt"),
        ({"pid": 999}, "worker_pid_mismatch"),
        ({"job_pids": ()}, "job_empty"),
        ({"job_pids": (303, 304)}, "job_descendant_present"),
        ({"tcp_sockets": ("127.0.0.1:80",)}, "worker_socket_present"),
        ({"udp_sockets": ("0.0.0.0:53",)}, "worker_socket_present"),
    ],
)
def test_attestation_fails_closed(changes: dict[str, object], code: str) -> None:
    backend = FakeBackend()
    boundary = make_boundary(backend)
    with boundary.acquire():
        boundary.launch_worker((40, 44))
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.attest(identity(**changes))
        assert caught.value.code == code


def test_attestation_accepts_exact_appcontainer_job_and_zero_sockets() -> None:
    backend = FakeBackend()
    boundary = make_boundary(backend)
    with boundary.acquire():
        boundary.launch_worker((40, 44))
        assert boundary.attest(identity()) == identity()


@pytest.mark.parametrize(
    "job_pids,tcp,udp,code",
    [
        ((), (), (), "job_empty"),
        ((303, 304), (), (), "job_descendant_present"),
        ((303,), ("10.0.0.1:443",), (), "worker_socket_present"),
        ((303,), (), ("0.0.0.0:68",), "worker_socket_present"),
    ],
)
def test_fresh_census_fails_closed(
    job_pids: tuple[int, ...],
    tcp: tuple[str, ...],
    udp: tuple[str, ...],
    code: str,
) -> None:
    backend = FakeBackend()
    backend.job_pids = job_pids
    backend.tcp_sockets = tcp
    backend.udp_sockets = udp
    boundary = make_boundary(backend)
    with boundary.acquire():
        backend.job_pids = (303,)
        backend.tcp_sockets = ()
        backend.udp_sockets = ()
        boundary.launch_worker((40, 44))
        backend.job_pids = job_pids
        backend.tcp_sockets = tcp
        backend.udp_sockets = udp
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.census()
        assert caught.value.code == code


def test_fresh_census_returns_secret_free_identity() -> None:
    backend = FakeBackend()
    boundary = make_boundary(backend)
    with boundary.acquire():
        boundary.launch_worker((40, 44))
        observed = boundary.census()
        assert observed == identity()
        json.dumps(observed.to_frame())


def test_production_has_no_profile_creation_or_ambient_probe_signature() -> None:
    from app.services import dual_live_windows_boundary as module

    source = inspect.getsource(module)
    assert "CreateAppContainerProfile" not in source
    assert "FreeSid" in source
    assert "_process_appcontainer_sid(process_handle)" in source
    assert not hasattr(WindowsEffectBoundary, "prove_python_worker")
    assert tuple(inspect.signature(WindowsEffectBoundary.prove_worker).parameters) == ("self",)


@pytest.mark.skipif(os.name != "nt", reason="real AppContainer proof requires Windows")
def test_real_worker_uses_externally_preprovisioned_bundle() -> None:
    from app.services.dual_live_worker_bundle import BundleBinding, WindowsBundleProbe

    binding_file = os.environ.get("PROJECT6_B0_BUNDLE_BINDING")
    if not binding_file:
        pytest.skip("externally pre-provisioned PROJECT6_B0_BUNDLE_BINDING required")
    document = json.loads(Path(binding_file).resolve(strict=True).read_text(encoding="utf-8"))
    path_fields = {
        "root", "provisioning_root", "ambient_interpreter_root", "repository_root",
        "campaign_root", "appcontainer_profile_root", "broker_profile_root", "user_data_root",
    }
    binding = BundleBinding(**{
        key: Path(value) if key in path_fields else value
        for key, value in document.items()
    })
    boundary = WindowsEffectBoundary(
        str(binding.root), "b0-windows-proof", bundle_binding=binding,
        bundle_probe=WindowsBundleProbe(binding),
    )
    with boundary.acquire():
        observed = boundary.prove_worker()
        assert observed.is_appcontainer is True
        assert observed.appcontainer_sid == binding.package_sid
        assert observed.loopback_exempt is False
        assert observed.job_pids == (observed.pid,)
        assert observed.tcp_sockets == ()
        assert observed.udp_sockets == ()


class SuspendedBackend(FakeBackend):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def launch_appcontainer_suspended(
        self, *args: object, creation_flags: int, **kwargs: object,
    ) -> tuple[int, str, int, int]:
        assert creation_flags & 0x4
        self.events.append("create_suspended")
        return self.worker_pid, self.worker_sid, self.worker_capability_count, self.process_handle, self.thread_handle

    def resume_thread(self, handle: int) -> int:
        assert handle == self.thread_handle
        self.events.append("resume")
        return super().resume_thread(handle)


class FakeBundleValidator:
    def __init__(self, backend: FakeBackend, *, drift: bool = False,
                 interpreter: Path = Path("C:/Python/python.exe"), entrypoint: Path = Path("C:/bundle/worker.py")) -> None:
        self.backend, self.drift = backend, drift
        self.bundle = SimpleNamespace(interpreter=interpreter, entrypoint=entrypoint,
                                      manifest_digest="a" * 64, snapshot_digest="b" * 64)

    def validate_worker_bundle(self, binding: object, probe: object) -> object:
        getattr(self.backend, "events", []).append("validate_prelaunch")
        return self.bundle

    def revalidate_worker_bundle(self, binding: object, probe: object, expected: object) -> object:
        assert expected is self.bundle
        getattr(self.backend, "events", []).append("rebind_suspended")
        if self.drift:
            raise EffectBoundaryHold("bundle_drift")
        return expected


@pytest.mark.parametrize("drift", [False, True])
def test_worker_resumes_only_after_exact_suspended_bundle_rebind(drift: bool) -> None:
    backend = SuspendedBackend()
    boundary = make_boundary(backend, FakeBundleValidator(backend, drift=drift))
    with boundary.acquire():
        if drift:
            with pytest.raises(EffectBoundaryHold, match="bundle_drift"):
                boundary.launch_worker((40, 44))
            assert backend.events == ["validate_prelaunch", "create_suspended", "rebind_suspended"]
            assert backend.terminated == [backend.job_handle]
            assert backend.thread_handle in backend.closed
            assert backend.process_handle in backend.closed
        else:
            boundary.launch_worker((40, 44))
            assert backend.events == ["validate_prelaunch", "create_suspended", "rebind_suspended", "resume"]


@pytest.mark.parametrize("result,code", [(0, "worker_suspend_count_invalid"),
                                         (2, "worker_suspend_count_invalid"),
                                         (0xFFFFFFFF, "worker_suspend_count_invalid"),
                                         (OSError("resume failed"), "worker_resume_failed")])
def test_resume_failure_closes_thread_terminates_job_and_holds(result: object, code: str) -> None:
    backend = SuspendedBackend()
    backend.resume_result = result  # type: ignore[assignment]
    with make_boundary(backend).acquire() as boundary:
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.launch_worker((40, 44))
        assert caught.value.code == code
        assert backend.terminated == [backend.job_handle]
        assert backend.thread_handle in backend.closed
        assert backend.process_handle in backend.closed


def test_package_sid_mismatch_holds_before_resume_and_closes_child_handles() -> None:
    backend = SuspendedBackend()
    backend.worker_sid = "S-1-15-2-999"
    with make_boundary(backend).acquire() as boundary:
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.launch_worker((40, 44))
        assert caught.value.code == "worker_sid_mismatch"
        assert backend.events == ["validate_prelaunch", "create_suspended"]
        assert backend.terminated == [backend.job_handle]
        assert backend.thread_handle in backend.closed
        assert backend.process_handle in backend.closed


def test_worker_capabilities_hold_before_resume() -> None:
    backend = SuspendedBackend()
    backend.worker_capability_count = 1
    with make_boundary(backend).acquire() as boundary:
        with pytest.raises(EffectBoundaryHold, match="worker_capabilities_present"):
            boundary.launch_worker((40, 44))
        assert "resume" not in backend.events


class ProbeBackend(FakeBackend):
    def __init__(self, stalled_frame: str) -> None:
        super().__init__()
        self.stalled_frame = stalled_frame
        self.read_request: tuple[int, int] | None = None

    def create_probe_pipes(self) -> tuple[int, int, int, int]:
        return 10, 12, 40, 44

    def read_probe_frame(self, handle: int, timeout_ms: int) -> dict[str, object]:
        assert self.stalled_frame in {"empty", "partial"}
        self.read_request = (handle, timeout_ms)
        raise EffectBoundaryHold("worker_attestation_timeout")

    def wait_process(self, process_handle: int, timeout_ms: int) -> int:
        raise AssertionError("timeout must occur during the bounded pipe read")


@pytest.mark.parametrize("stalled_frame", ["empty", "partial"])
def test_stalled_probe_frame_terminates_job_and_closes_process(
    monkeypatch: pytest.MonkeyPatch,
    stalled_frame: str,
) -> None:
    from app.services import dual_live_windows_boundary as module

    backend = ProbeBackend(stalled_frame)
    monkeypatch.setattr(module, "_CtypesBackend", ProbeBackend)
    with make_boundary(backend).acquire() as boundary:
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.prove_worker()
        assert caught.value.code == "worker_attestation_timeout"
        assert backend.read_request == (10, 15_000)
        assert backend.terminated == [backend.job_handle]
        assert backend.process_handle in backend.closed


def test_bounded_worker_frame_timeout_contains_job_and_process() -> None:
    backend = ProbeBackend("partial")
    with make_boundary(backend).acquire() as boundary:
        boundary.launch_worker((40, 44), mode="sciencebase")
        with pytest.raises(EffectBoundaryHold, match="worker_attestation_timeout"):
            boundary.read_worker_frame(10, 15_000)
        assert backend.terminated == [backend.job_handle]
        assert backend.process_handle in backend.closed


def _ipc_plan(root: Path, ordinal: int = 1) -> PhysicalRequestPlan:
    return PhysicalRequestPlan(
        envelope_digest="sha256:" + "a" * 64,
        campaign_id="campaign",
        canonical_root=str(root.resolve()),
        connector_run_id=str(uuid4()),
        target_id="item",
        request_ordinal=ordinal,
        stage="sciencebase_search",
        method="GET",
        canonical_destination="https://www.sciencebase.gov/catalog/items?q=sample&format=json",
        header_names=(),
        header_value_sha256s=(),
        body_sha256="sha256:" + hashlib.sha256(b"").hexdigest(),
        limits=RequestLimits(timeout_seconds=5, max_response_bytes=1024 * 1024),
        authorization_digest="sha256:" + "b" * 64,
        grant_digest="sha256:" + "c" * 64,
    )


class _ReservationRecorder:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def reserve(self, plan: PhysicalRequestPlan) -> CommittedReservation:
        self.events.append(f"reserve:{plan.request_ordinal}")
        return CommittedReservation("RESERVED", plan.slot_uuid, plan.plan_digest)


class _Response:
    status_code = 200
    headers: dict[str, str] = {}

    def __init__(self, body: bytes) -> None:
        self.body = body

    def iter_content(self, *, chunk_size: int) -> tuple[bytes, ...]:
        assert chunk_size > 0
        return (self.body,)

    def close(self) -> None:
        return None


class _Session:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def request(self, method: str, destination: str, **kwargs: object) -> _Response:
        ordinal = len([item for item in self.events if item.startswith("effect:")]) + 1
        self.events.append(f"effect:{ordinal}")
        assert method == "GET"
        assert kwargs["allow_redirects"] is False
        if "/items?" in destination:
            body = b'{"items":[{"id":"item"}]}'
        elif "/item/item?" in destination:
            body = b'{"id":"item","files":[{"name":"sample.bin","downloadUri":"https://www.sciencebase.gov/catalog/file.bin"}]}'
        else:
            body = b"artifact"
        return _Response(body)

    def close(self) -> None:
        return None


def test_sciencebase_producer_completes_through_broker_after_each_reservation(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    transport = ConnectorEgressTransport(
        _ReservationRecorder(events),  # type: ignore[arg-type]
        session_factory=lambda: _Session(events),
    )
    guard = effect_guard.BrokerEffectGuard(transport)
    broker_read_fd, worker_write_fd = os.pipe()
    worker_read_fd, broker_write_fd = os.pipe()
    with (
        os.fdopen(broker_read_fd, "rb", buffering=0) as broker_reader,
        os.fdopen(broker_write_fd, "wb", buffering=0) as broker_writer,
        os.fdopen(worker_read_fd, "rb", buffering=0) as worker_reader,
        os.fdopen(worker_write_fd, "wb", buffering=0) as worker_writer,
    ):
        request = ScienceBaseInput(
            query="sample",
            expected_item_id="item",
            expected_file_name="sample.bin",
            envelope_digest="sha256:" + "a" * 64,
            campaign_id="campaign",
            canonical_root=str(tmp_path.resolve()),
            connector_run_id=str(uuid4()),
            authorization_digest="sha256:" + "b" * 64,
            grant_digest="sha256:" + "c" * 64,
            max_total_bytes=1024 * 1024,
            limits=RequestLimits(timeout_seconds=5, max_response_bytes=1024 * 1024),
        )
        failures: list[BaseException] = []

        def run_worker() -> None:
            try:
                effect_guard.run_sciencebase_worker(worker_reader, worker_writer)
            except BaseException as exc:
                failures.append(exc)

        worker = threading.Thread(target=run_worker)
        worker.start()
        output = guard.serve_sciencebase(request, broker_reader, broker_writer)
        effect_guard.release_sciencebase_worker(broker_writer)
        worker.join(timeout=2)
        assert not worker.is_alive()
        assert failures == []
    assert output.content == b"artifact"
    assert events == [
        "reserve:1", "effect:1", "reserve:2", "effect:2", "reserve:3", "effect:3",
    ]


def test_broker_holds_malformed_request_without_transport_retry(tmp_path: Path) -> None:
    class NeverTransport:
        calls = 0

        def execute(self, plan: PhysicalRequestPlan) -> object:
            self.calls += 1
            raise AssertionError("malformed frames must not reach transport")

    transport = NeverTransport()
    body = b'{"credential_value":"raw","type":"effect_request"}'
    reader = io.BytesIO(struct.pack(">I", len(body)) + body)
    writer = io.BytesIO()
    effect_guard.BrokerEffectGuard(transport).serve_one(reader, writer)
    writer.seek(0)
    response = read_frame(writer)
    assert response == {"code": "frame_secret_field", "type": "effect_hold"}
    assert transport.calls == 0


def test_pipe_effect_port_rejects_secret_or_malformed_result(tmp_path: Path) -> None:
    body = b'{"credential_value":"raw","type":"effect_result"}'
    reader = io.BytesIO(struct.pack(">I", len(body)) + body)
    writer = io.BytesIO()
    with pytest.raises(EffectBoundaryHold, match="frame_secret_field"):
        effect_guard.PipeEffectPort(reader, writer).execute(_ipc_plan(tmp_path))
    writer.seek(0)
    assert read_frame(writer)["type"] == "effect_request"


def test_broker_converts_transport_failure_to_one_secret_free_hold(tmp_path: Path) -> None:
    class FailingTransport:
        calls = 0

        def execute(self, plan: PhysicalRequestPlan) -> object:
            self.calls += 1
            raise RuntimeError("credential=C:/private/secret")

    transport = FailingTransport()
    reader = io.BytesIO()
    write_frame(reader, {"type": "effect_request", "plan": _ipc_plan(tmp_path).to_document()})
    reader.seek(0)
    writer = io.BytesIO()
    effect_guard.BrokerEffectGuard(transport).serve_one(reader, writer)
    writer.seek(0)
    response = read_frame(writer)
    assert response == {"code": "broker_effect_failed", "type": "effect_hold"}
    assert transport.calls == 1
    assert "private" not in json.dumps(response)


@pytest.mark.parametrize(
    "change",
    [
        {"stage": "unrelated_admin"},
        {"canonical_destination": "https://www.sciencebase.gov/not-authorized"},
        {"limits": RequestLimits(timeout_seconds=6, max_response_bytes=1024 * 1024)},
    ],
)
def test_broker_rejects_worker_selected_sciencebase_scope(
    tmp_path: Path, change: dict[str, object],
) -> None:
    request = ScienceBaseInput(
        query="sample", expected_item_id="item", expected_file_name="sample.bin",
        envelope_digest="sha256:" + "a" * 64, campaign_id="campaign",
        canonical_root=str(tmp_path.resolve()), connector_run_id=str(uuid4()),
        authorization_digest="sha256:" + "b" * 64,
        grant_digest="sha256:" + "c" * 64, max_total_bytes=1024 * 1024,
        limits=RequestLimits(timeout_seconds=5, max_response_bytes=1024 * 1024),
    )
    plan = ScienceBaseProducer(SimpleNamespace())._plan(request, 1, "sciencebase_search", "https://www.sciencebase.gov/catalog/items?q=sample&format=json")
    with pytest.raises(EffectBoundaryHold, match="sciencebase_plan_binding_mismatch"):
        effect_guard._bind_sciencebase_plan(replace(plan, **change), request, 1, None)


def test_launch_sciencebase_worker_uses_only_bundle_entrypoint_and_pipe_handles() -> None:
    backend = FakeBackend()
    boundary = make_boundary(backend)
    with boundary.acquire():
        boundary.launch_worker((40, 44), mode="sciencebase")
    assert backend.launched is not None
    assert backend.launched[1] == (
        "-I", "-S", str(Path("C:/bundle/worker.py")),
        "--worker-sciencebase", "40", "44",
    )


def test_boundary_exposes_exact_worker_pipe_allocation_and_close() -> None:
    backend = ProbeBackend("empty")
    with make_boundary(backend).acquire() as boundary:
        assert boundary.create_worker_pipes() == (10, 12, 40, 44)
        boundary.close_pipe_handle(40)
        boundary.close_pipe_handle(44)
    assert 40 in backend.closed
    assert 44 in backend.closed


@pytest.mark.parametrize("result,code", [(7, "worker_exit_nonzero"), (OSError("timeout"), "worker_wait_failed")])
def test_wait_worker_closes_process_and_contains_failure(result: object, code: str) -> None:
    backend = FakeBackend()
    backend.wait_result = result  # type: ignore[assignment]
    with make_boundary(backend).acquire() as boundary:
        boundary.launch_worker((40, 44), mode="sciencebase")
        with pytest.raises(EffectBoundaryHold) as caught:
            boundary.wait_worker(15_000)
        assert caught.value.code == code
        assert backend.process_handle in backend.closed
        assert backend.terminated == [backend.job_handle]


def test_wait_worker_accepts_exact_zero_exit_once() -> None:
    backend = FakeBackend()
    with make_boundary(backend).acquire() as boundary:
        boundary.launch_worker((40, 44), mode="sciencebase")
        assert boundary.wait_worker(15_000) == 0
        assert backend.process_handle in backend.closed
        with pytest.raises(EffectBoundaryHold, match="worker_process_handle_missing"):
            boundary.wait_worker(15_000)


def test_probe_worker_emits_os_identity_and_requires_exact_release() -> None:
    reader = io.BytesIO()
    write_frame(reader, {"type": "probe_release"})
    reader.seek(0)
    writer = io.BytesIO()
    run_probe_worker(reader, writer, backend=FakeBackend())
    writer.seek(0)
    assert WorkerIdentity.from_frame(read_frame(writer)) == identity()

    malformed = io.BytesIO()
    write_frame(malformed, {"type": "wrong"})
    malformed.seek(0)
    with pytest.raises(EffectBoundaryHold, match="probe_release_malformed"):
        run_probe_worker(malformed, io.BytesIO(), backend=FakeBackend())


@pytest.mark.parametrize(
    "codes,accepted",
    [((5, 10013, 1816), True), ((0, 10013, 1816), False),
     ((5, 0, 1816), False), ((5, 10013, 0), False), ((5, 10061, 1816), False)],
)
def test_probe_requires_exact_os_denial_codes(
    codes: tuple[int, int, int], accepted: bool,
) -> None:
    if accepted:
        _validate_probe_denials(*codes)
    else:
        with pytest.raises(EffectBoundaryHold, match="worker_denial_proof_failed"):
            _validate_probe_denials(*codes)


def test_launch_fails_closed_when_inherited_handle_clear_fails() -> None:
    source = inspect.getsource(
        __import__(
            "app.services.dual_live_windows_boundary", fromlist=["_CtypesBackend"]
        )._CtypesBackend.launch_appcontainer_suspended
    )
    assert "_clear_inherited_pipe_handles" in source
    assert "inheritance_clear_error" in source


def test_inheritance_clear_failure_closes_both_pipes_and_terminates_job() -> None:
    class Kernel:
        closed: list[int] = []
        terminated: list[int] = []

        def SetHandleInformation(self, handle: int, mask: int, flags: int) -> bool:
            return handle != 40

        def CloseHandle(self, handle: int) -> bool:
            self.closed.append(handle)
            return True

        def TerminateJobObject(self, handle: int, code: int) -> bool:
            self.terminated.append(handle)
            return True

    kernel = Kernel()
    with pytest.raises(EffectBoundaryHold, match="pipe_inheritance_clear_failed"):
        _clear_inherited_pipe_handles(kernel, (40, 44), 202)
    assert kernel.closed == [40, 44]
    assert kernel.terminated == [202]


def test_broker_session_deadline_cancels_stalled_write_and_joins_watchdog() -> None:
    backend = FakeBackend()

    class FilledPipeWriter:
        def write(self, data: bytes) -> int:
            assert len(data) > 32 * 1024
            assert backend.cancel_event.wait(2), "watchdog did not cancel stalled write"
            raise OSError("cancelled synchronous write")

        def flush(self) -> None:
            return None

    with make_boundary(backend).acquire() as boundary:
        boundary.launch_worker((40, 44), mode="sciencebase")
        with pytest.raises(EffectBoundaryHold, match="broker_session_deadline"):
            with boundary.broker_session_deadline(25):
                write_frame(
                    FilledPipeWriter(),
                    {"type": "effect_body_chunk", "index": 0, "data_b64": "a" * 40_000},
                )
        assert backend.terminated == [backend.job_handle]
        assert backend.cancelled_threads == [backend.broker_thread_handle]
        assert backend.broker_thread_handle in backend.closed
        assert not any(
            thread.name.startswith("p6-b0-session-") and thread.is_alive()
            for thread in threading.enumerate()
        )


def test_broker_session_deadline_success_closes_thread_handle_without_containment() -> None:
    backend = FakeBackend()
    with make_boundary(backend).acquire() as boundary:
        with boundary.broker_session_deadline(2_000):
            time.sleep(0.001)
        assert backend.cancelled_threads == []
        assert backend.terminated == []
        assert backend.broker_thread_handle in backend.closed
