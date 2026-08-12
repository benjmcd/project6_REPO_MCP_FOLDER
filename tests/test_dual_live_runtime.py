from __future__ import annotations

import importlib
import importlib.util
import ast
import contextlib
import hashlib
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "tools" / "dual_live_run.py"
PROJECT6_PS1 = REPO_ROOT / "project6.ps1"


def _runtime_module():
    module_name = "backend.app.services.dual_live_runtime"
    assert importlib.util.find_spec(module_name) is not None, (
        "dual-live runtime module is required"
    )
    return importlib.import_module(module_name)


def _launcher_module():
    spec = importlib.util.spec_from_file_location("project6_dual_live_run", LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _authority_document(tmp_path: Path, runtime=None) -> dict[str, str]:
    runtime = runtime or _runtime_module()
    return {
        "schema_version": runtime.AUTHORITY_SCHEMA_VERSION,
        "campaign_id": "campaign-test",
        "canonical_root": str(tmp_path.resolve()),
        "connector_run_id": "00000000-0000-4000-8000-000000000001",
        "source_commit": "1" * 40,
        "interpreter_identity": "sha256:" + "2" * 64,
        "authorization_digest": "sha256:" + "3" * 64,
        "grant_digest": "sha256:" + "4" * 64,
        "wrapper_start_token_ref": "wrapper-start:test-token-v1",
    }


def _canonical_bytes(document: dict[str, str]) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _expected_authority(runtime, tmp_path: Path):
    return runtime.ExpectedAuthority(
        schema_version=runtime.AUTHORITY_SCHEMA_VERSION,
        campaign_id="campaign-test",
        canonical_root=tmp_path.resolve(),
        connector_run_id="00000000-0000-4000-8000-000000000001",
        source_commit="1" * 40,
        interpreter_identity="sha256:" + "2" * 64,
    )


def _worker_bundle(runtime, root: Path):
    digest = "sha256:" + "5" * 64
    return runtime.RuntimeWorkerBundle(
        root=root / digest.replace(":", "-"),
        provisioning_root=root / "bundles",
        profile_moniker="Project6.B0.Test",
        manifest_digest=digest,
        entrypoint="tools/dual_live_run.py",
        interpreter="python.exe",
        python_version="3.11.9",
        architecture="amd64",
        package_sid="S-1-15-2-1",
        owner_sid="S-1-5-21-1",
        provisioner_sid="S-1-5-21-2",
        broker_sid="S-1-5-21-3",
        ambient_interpreter_root=root / "ambient-python",
        campaign_root=root / "campaign",
        appcontainer_profile_root=root / "app-profile",
        broker_profile_root=root / "broker-profile",
        user_data_root=root / "user-data",
    )


def _science_request(runtime):
    return runtime.RuntimeScienceBaseRequest(
        query="public geology", expected_item_id="item-1", expected_file_name="map.json"
    )


def test_launcher_help_states_non_authorizing_contract() -> None:
    completed = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "does not grant live authority" in completed.stdout
    assert "--reservation-database" in completed.stdout
    assert completed.stderr == ""


def test_launcher_defers_effect_capable_broker_imports_until_after_worker_dispatch() -> (
    None
):
    tree = ast.parse(LAUNCHER.read_text(encoding="utf-8"))
    top_imports = [
        node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    imported = {alias.name for node in top_imports for alias in node.names}
    assert not any(
        "dual_live_runtime" in name or "transport" in name for name in imported
    )


@pytest.mark.parametrize("values", [[], ["1"], ["1", "1"], ["0", "2"], ["x", "2"]])
def test_worker_dispatch_rejects_any_nonexact_inherited_handle_pair(values) -> None:
    launcher = _launcher_module()
    with pytest.raises(ValueError, match="worker handles invalid"):
        launcher._worker_handles(values)
    assert launcher._worker_handles(["11", "12"]) == (11, 12)


def test_disabled_returns_before_authority_or_component_callbacks(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module()
    calls: list[str] = []

    def forbidden(name: str):
        def invoke(*_args, **_kwargs):
            calls.append(name)
            raise AssertionError(f"disabled runtime invoked {name}")

        return invoke

    request = runtime.RuntimeRequest(
        enabled=False,
        authority_envelope_path=tmp_path / "unread.json",
        authority_envelope_digest="sha256:" + "0" * 64,
        campaign_id="campaign-test",
        canonical_root=tmp_path,
        connector_run_id="00000000-0000-4000-8000-000000000001",
        reservation_database_path=tmp_path / "reservation.db",
        worker_bundle=_worker_bundle(runtime, tmp_path.resolve()),
        sciencebase_request=_science_request(runtime),
    )
    dependencies = runtime.RuntimeDependencies(
        read_bytes=forbidden("read_bytes"),
        source_commit=forbidden("source_commit"),
        interpreter_identity=forbidden("interpreter_identity"),
        reservation_store_factory=forbidden("reservation_store_factory"),
        boundary_factory=forbidden("boundary_factory"),
        transport_factory=forbidden("transport_factory"),
        broker_factory=forbidden("broker_factory"),
    )

    result = runtime.prepare_dual_live_runtime(request, dependencies)

    assert result.status == runtime.RuntimeStatus.DISABLED
    assert result.code == "dual_live_runtime_disabled"
    assert result.prepared is None
    assert calls == []


def test_envelope_is_read_once_content_addressed_and_explicitly_non_live(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module()
    envelope_path = tmp_path / "authority.json"
    raw = _canonical_bytes(_authority_document(tmp_path))
    envelope_path.write_bytes(raw)
    reads: list[Path] = []

    def read_once(path: Path, _limit: int) -> bytes:
        reads.append(path)
        return path.read_bytes()

    validated = runtime.load_authority_envelope_once(
        envelope_path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        _expected_authority(runtime, tmp_path),
        read_bytes=read_once,
    )

    assert reads == [envelope_path]
    assert validated.envelope.campaign_id == "campaign-test"
    assert validated.envelope.authorization_digest == "sha256:" + "3" * 64
    assert validated.envelope.grant_digest == "sha256:" + "4" * 64
    assert validated.envelope.wrapper_start_token_ref == "wrapper-start:test-token-v1"
    assert validated.live_authority is False
    assert validated.persisted is False
    assert validated.issued_by_b0 is False


def test_authority_envelope_read_is_bounded(tmp_path: Path) -> None:
    runtime = _runtime_module()
    observed: list[int] = []

    def oversized(_path: Path, limit: int) -> bytes:
        observed.append(limit)
        return b"x" * limit

    with pytest.raises(runtime.RuntimeHold, match="authority_envelope_too_large"):
        runtime.load_authority_envelope_once(
            tmp_path / "authority.json",
            "sha256:" + "0" * 64,
            _expected_authority(runtime, tmp_path),
            read_bytes=oversized,
        )
    assert observed == [runtime.MAX_AUTHORITY_ENVELOPE_BYTES + 1]


def test_runtime_identity_reads_exact_worktree_ref_and_hashes_interpreter(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module()
    source_root = tmp_path / "source"
    git_dir = tmp_path / "git" / "worktrees" / "source"
    source_root.mkdir()
    git_dir.mkdir(parents=True)
    (source_root / ".git").write_text(f"gitdir: {git_dir}\n", encoding="ascii")
    (git_dir / "HEAD").write_text("ref: refs/heads/b0\n", encoding="ascii")
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "refs" / "heads" / "b0").write_text("a" * 40 + "\n", encoding="ascii")
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"exact-interpreter")

    assert runtime._source_commit(source_root) == "a" * 40
    assert runtime._interpreter_identity(interpreter) == (
        "sha256:" + hashlib.sha256(b"exact-interpreter").hexdigest()
    )


def test_valid_zero_reservation_path_composes_in_fail_closed_order(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module()
    raw = _canonical_bytes(_authority_document(tmp_path, runtime))
    calls: list[str] = []
    boundary = object()
    transport = object()
    broker = object()

    class EmptyStore:
        def assert_no_reservations(self, connector_run_id: str):
            calls.append(f"reservation_census:{connector_run_id}")
            return None

    def record(name: str, value):
        def invoke(*_args):
            calls.append(name)
            return value

        return invoke

    def reservation_factory(root: Path, asserted_path: Path):
        assert root == tmp_path.resolve()
        assert asserted_path == root / "reservation.db"
        calls.append("reservation_store")
        return EmptyStore()

    request = runtime.RuntimeRequest(
        enabled=True,
        authority_envelope_path=tmp_path / "authority.json",
        authority_envelope_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        campaign_id="campaign-test",
        canonical_root=tmp_path.resolve(),
        connector_run_id="00000000-0000-4000-8000-000000000001",
        reservation_database_path=tmp_path / "reservation.db",
        worker_bundle=_worker_bundle(runtime, tmp_path.resolve()),
        sciencebase_request=_science_request(runtime),
    )
    probe = object()
    validated_interpreter = tmp_path / "bundle" / "python.exe"

    def interpreter_identity(path: Path):
        assert path == validated_interpreter
        calls.append("interpreter_identity")
        return "sha256:" + "2" * 64

    def boundary_factory(root: str, campaign: str, **kwargs):
        assert root == str(tmp_path.resolve()) and campaign == "campaign-test"
        assert kwargs["bundle_binding"].source_commit == "1" * 40
        assert kwargs["bundle_probe"] is probe
        calls.append("boundary")
        return boundary

    dependencies = runtime.RuntimeDependencies(
        read_bytes=record("read_envelope", raw),
        source_commit=record("source_commit", "1" * 40),
        interpreter_identity=interpreter_identity,
        reservation_store_factory=reservation_factory,
        boundary_factory=boundary_factory,
        transport_factory=record("transport", transport),
        broker_factory=record("broker", broker),
        bundle_probe_factory=record("bundle_probe", probe),
        bundle_validator=record(
            "bundle_validate", SimpleNamespace(interpreter=validated_interpreter)
        ),
    )

    result = runtime.prepare_dual_live_runtime(request, dependencies)

    assert result.status == runtime.RuntimeStatus.PREPARED
    assert result.code == "dual_live_runtime_prepared_non_live"
    assert result.prepared is not None
    assert result.prepared.envelope.live_authority is False
    assert result.prepared.boundary is boundary
    assert result.prepared.transport is transport
    assert result.prepared.broker is broker
    producer_request = result.prepared.producer_request
    assert producer_request.max_total_bytes == 512 * 1024 * 1024
    assert producer_request.limits.max_response_bytes == 64 * 1024 * 1024
    assert producer_request.limits.timeout_seconds == 30
    assert producer_request.max_redirect_hops == 0
    assert producer_request.authorization_digest == "sha256:" + "3" * 64
    assert producer_request.campaign_id == "campaign-test"
    assert calls == [
        "source_commit",
        "bundle_probe",
        "bundle_validate",
        "interpreter_identity",
        "read_envelope",
        "reservation_store",
        "reservation_census:00000000-0000-4000-8000-000000000001",
        "boundary",
        "transport",
        "broker",
    ]


def test_run_prepared_runtime_owns_worker_pipes_job_and_exact_completion() -> None:
    runtime = _runtime_module()
    events: list[object] = []
    request = SimpleNamespace(query="public geology")
    output = object()

    class Store:
        def close(self):
            events.append("store_close")

    class Authority:
        def consume_exact(self, digest):
            events.append(("consume_go", digest))
            return True

    class Boundary:
        @contextlib.contextmanager
        def acquire(self):
            events.append("acquire")
            try:
                yield self
            finally:
                events.append("release")

        def create_worker_pipes(self):
            events.append("pipes")
            return 11, 12, 13, 14

        def launch_worker(self, handles, *, mode):
            events.append(("launch", handles, mode))

        def close_pipe_handle(self, handle):
            events.append(("close", handle))

        def wait_worker(self, timeout_ms):
            events.append(("wait", timeout_ms))
            return 0

        def census(self):
            events.append("census")

        def read_worker_frame(self, handle, timeout_ms):
            events.append(("read", handle, timeout_ms))
            return {"type": "test"}

        @contextlib.contextmanager
        def broker_session_deadline(self, timeout_ms):
            events.append(("deadline", timeout_ms))
            try:
                yield
            finally:
                events.append("deadline_end")

    class Stream(contextlib.AbstractContextManager):
        def __init__(self, handle):
            self.handle = handle

        def __exit__(self, *_args):
            events.append(("stream_close", self.handle))

    class Broker:
        def serve_sciencebase(self, received, reader, writer, *, read_next):
            events.append(("serve", received, reader, writer.handle, read_next()))
            return output

    prepared = runtime.PreparedRuntime(
        envelope=SimpleNamespace(
            envelope=SimpleNamespace(content_digest="sha256:" + "a" * 64)
        ),
        reservation_store=Store(),
        boundary=Boundary(),
        transport=object(),
        broker=Broker(),
        producer_request=request,
    )
    result = runtime.run_prepared_runtime(
        prepared,
        execution_authority=Authority(),
        open_writer=lambda handle: Stream(handle),
        release_worker=lambda writer: events.append(("release_worker", writer.handle)),
    )

    assert result is output
    assert events == [
        ("consume_go", "sha256:" + "a" * 64),
        "acquire",
        "pipes",
        ("launch", (13, 14), "sciencebase"),
        ("close", 13),
        ("close", 14),
        ("deadline", 15_000),
        ("read", 11, 15_000),
        ("serve", request, None, 12, {"type": "test"}),
        "census",
        ("release_worker", 12),
        ("wait", 15_000),
        "deadline_end",
        ("stream_close", 12),
        ("close", 11),
        "release",
        "store_close",
    ]


def test_runtime_rejects_nonstandard_external_worker_entrypoint(tmp_path: Path) -> None:
    runtime = _runtime_module()
    raw = _canonical_bytes(_authority_document(tmp_path, runtime))
    bundle = replace(
        _worker_bundle(runtime, tmp_path.resolve()), entrypoint="worker.py"
    )
    request = runtime.RuntimeRequest(
        enabled=True,
        authority_envelope_path=tmp_path / "authority.json",
        authority_envelope_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        campaign_id="campaign-test",
        canonical_root=tmp_path.resolve(),
        connector_run_id="00000000-0000-4000-8000-000000000001",
        reservation_database_path=tmp_path / "reservation.db",
        worker_bundle=bundle,
        sciencebase_request=_science_request(runtime),
    )

    class Store:
        def assert_no_reservations(self, _run_id):
            return None

    dependencies = runtime.RuntimeDependencies(
        read_bytes=lambda _path, _limit: raw,
        source_commit=lambda _root: "1" * 40,
        interpreter_identity=lambda _path: "sha256:" + "2" * 64,
        reservation_store_factory=lambda _root, _path: Store(),
        boundary_factory=lambda *_args, **_kwargs: pytest.fail("boundary constructed"),
        transport_factory=lambda _store: pytest.fail("transport constructed"),
        broker_factory=lambda _transport: pytest.fail("broker constructed"),
    )

    result = runtime.prepare_dual_live_runtime(request, dependencies)
    assert (result.status, result.code) == (
        runtime.RuntimeStatus.HOLD,
        "worker_bundle_entrypoint_invalid",
    )


@pytest.mark.parametrize("decision", [None, False, "true", 1, RuntimeError("consumed")])
def test_run_rejects_missing_or_nonlive_execution_authority_before_boundary(
    decision,
) -> None:
    runtime = _runtime_module()
    calls: list[object] = []

    class Store:
        def close(self):
            calls.append("store_close")

    class Boundary:
        def acquire(self):
            pytest.fail("boundary acquired without exact consumed live GO")

    class Authority:
        def consume_exact(self, digest):
            calls.append(("consume", digest))
            if isinstance(decision, BaseException):
                raise decision
            return decision

    prepared = runtime.PreparedRuntime(
        envelope=SimpleNamespace(
            envelope=SimpleNamespace(content_digest="sha256:" + "b" * 64)
        ),
        reservation_store=Store(),
        boundary=Boundary(),
        transport=object(),
        broker=object(),
        producer_request=object(),
    )
    authority = None if decision is None else Authority()
    with pytest.raises(runtime.RuntimeHold, match="live_go_required"):
        runtime.run_prepared_runtime(prepared, execution_authority=authority)
    expected = [] if authority is None else [("consume", "sha256:" + "b" * 64)]
    assert calls == [*expected, "store_close"]


def test_run_failure_closes_every_untransferred_pipe_inside_boundary() -> None:
    runtime = _runtime_module()
    events: list[object] = []

    class Boundary:
        @contextlib.contextmanager
        def acquire(self):
            events.append("acquire")
            try:
                yield self
            finally:
                events.append("release")

        def create_worker_pipes(self):
            return 21, 22, 23, 24

        def launch_worker(self, *_args, **_kwargs):
            raise OSError("sanitized by runtime")

        def close_pipe_handle(self, handle):
            events.append(("close", handle))

    prepared = runtime.PreparedRuntime(
        envelope=SimpleNamespace(
            envelope=SimpleNamespace(content_digest="sha256:" + "c" * 64)
        ),
        reservation_store=SimpleNamespace(close=lambda: events.append("store_close")),
        boundary=Boundary(),
        transport=object(),
        broker=object(),
        producer_request=object(),
    )
    with pytest.raises(runtime.RuntimeHold, match="runtime_execution_failed"):
        runtime.run_prepared_runtime(
            prepared,
            execution_authority=SimpleNamespace(consume_exact=lambda _digest: True),
            open_writer=lambda _h: None,
        )
    assert events == [
        "acquire",
        ("close", 21),
        ("close", 22),
        ("close", 23),
        ("close", 24),
        "release",
        "store_close",
    ]


@pytest.mark.parametrize(
    "census_result", [1, "ambiguous", object(), RuntimeError("census")]
)
def test_any_reservation_or_ambiguous_census_holds_before_boundary(
    tmp_path: Path,
    census_result: object,
) -> None:
    runtime = _runtime_module()
    raw = _canonical_bytes(_authority_document(tmp_path, runtime))
    component_calls: list[str] = []

    class NonEmptyStore:
        def assert_no_reservations(self, _connector_run_id: str):
            if isinstance(census_result, BaseException):
                raise census_result
            return census_result

        def close(self):
            component_calls.append("store_close")

    def forbidden(name: str):
        def invoke(*_args):
            component_calls.append(name)
            raise AssertionError(f"census HOLD invoked {name}")

        return invoke

    request = runtime.RuntimeRequest(
        enabled=True,
        authority_envelope_path=tmp_path / "authority.json",
        authority_envelope_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        campaign_id="campaign-test",
        canonical_root=tmp_path.resolve(),
        connector_run_id="00000000-0000-4000-8000-000000000001",
        reservation_database_path=tmp_path / "reservation.db",
        worker_bundle=_worker_bundle(runtime, tmp_path.resolve()),
        sciencebase_request=_science_request(runtime),
    )
    dependencies = runtime.RuntimeDependencies(
        read_bytes=lambda _path, _limit: raw,
        source_commit=lambda _root: "1" * 40,
        interpreter_identity=lambda _path: "sha256:" + "2" * 64,
        reservation_store_factory=lambda _root, _path: NonEmptyStore(),
        boundary_factory=forbidden("boundary"),
        transport_factory=forbidden("transport"),
        broker_factory=forbidden("broker"),
        bundle_probe_factory=lambda _binding: object(),
        bundle_validator=lambda _binding, _probe: SimpleNamespace(
            interpreter=(tmp_path / "python.exe").resolve()
        ),
    )

    result = runtime.prepare_dual_live_runtime(request, dependencies)

    assert result.status == runtime.RuntimeStatus.HOLD
    expected = (
        "reservation_census_ambiguous"
        if isinstance(census_result, BaseException)
        else "reservation_census_not_empty"
    )
    assert result.code == expected
    assert result.prepared is None
    assert component_calls == ["store_close"]


def test_envelope_drift_holds_before_store_or_boundary(tmp_path: Path) -> None:
    runtime = _runtime_module()
    document = _authority_document(tmp_path, runtime)
    document["source_commit"] = "9" * 40
    raw = _canonical_bytes(document)
    component_calls: list[str] = []

    def forbidden(name: str):
        def invoke(*_args):
            component_calls.append(name)
            raise AssertionError(f"drift HOLD invoked {name}")

        return invoke

    request = runtime.RuntimeRequest(
        enabled=True,
        authority_envelope_path=tmp_path / "authority.json",
        authority_envelope_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        campaign_id="campaign-test",
        canonical_root=tmp_path.resolve(),
        connector_run_id="00000000-0000-4000-8000-000000000001",
        reservation_database_path=tmp_path / "reservations.db",
        worker_bundle=_worker_bundle(runtime, tmp_path.resolve()),
        sciencebase_request=_science_request(runtime),
    )
    dependencies = runtime.RuntimeDependencies(
        read_bytes=lambda _path, _limit: raw,
        source_commit=lambda _root: "1" * 40,
        interpreter_identity=lambda _path: "sha256:" + "2" * 64,
        reservation_store_factory=forbidden("reservation_store"),
        boundary_factory=forbidden("boundary"),
        transport_factory=forbidden("transport"),
        broker_factory=forbidden("broker"),
        bundle_probe_factory=lambda _binding: object(),
        bundle_validator=lambda _binding, _probe: SimpleNamespace(
            interpreter=(tmp_path / "python.exe").resolve()
        ),
    )

    result = runtime.prepare_dual_live_runtime(request, dependencies)

    assert result.status == runtime.RuntimeStatus.HOLD
    assert result.code == "authority_envelope_binding_mismatch"
    assert component_calls == []


def test_settings_keep_dual_live_runtime_default_off() -> None:
    from backend.app.core.config import Settings

    field = Settings.model_fields["dual_live_runtime_enabled"]

    assert field.default is False
    assert field.alias == "DUAL_LIVE_RUNTIME_ENABLED"
    assert "does not grant live authority" in (field.description or "")


def test_launcher_reads_only_the_exact_noncredential_runtime_switch(
    monkeypatch,
) -> None:
    launcher = _launcher_module()
    monkeypatch.setenv("DUAL_LIVE_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "must-not-be-read")
    assert launcher._default_settings().dual_live_runtime_enabled is True
    source = __import__("inspect").getsource(launcher._default_settings)
    assert "backend.app.core.config" not in source


def test_project6_action_forwards_only_exact_dual_live_action_args() -> None:
    script = PROJECT6_PS1.read_text(encoding="utf-8-sig")

    assert '"run-dual-live"' in script.splitlines()[2]
    assert '$DualLiveRunPath = Join-Path $RepoRoot "tools\\dual_live_run.py"' in script
    expected_block = """    "run-dual-live" {
        if (-not (Test-Path $DualLiveRunPath)) {
            throw "Dual-live launcher not found: $DualLiveRunPath"
        }
        Push-Location $RepoRoot
        try {
            & py "-$PythonVersion" $DualLiveRunPath @ActionArgs
            exit $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
    }"""
    assert expected_block in script


def _launcher_args(tmp_path: Path) -> list[str]:
    bundle = _worker_bundle(_runtime_module(), tmp_path.resolve())
    return [
        "--authority-envelope",
        str(tmp_path / "authority.json"),
        "--authority-envelope-sha256",
        "sha256:" + "0" * 64,
        "--campaign-id",
        "campaign-test",
        "--canonical-root",
        str(tmp_path.resolve()),
        "--connector-run-id",
        "00000000-0000-4000-8000-000000000001",
        "--reservation-database",
        str(tmp_path / "reservation.db"),
        "--query",
        "public geology",
        "--expected-item-id",
        "item-1",
        "--expected-file-name",
        "map.json",
        "--worker-bundle-root",
        str(bundle.root),
        "--worker-provisioning-root",
        str(bundle.provisioning_root),
        "--worker-profile-moniker",
        bundle.profile_moniker,
        "--worker-manifest-sha256",
        bundle.manifest_digest,
        "--worker-entrypoint",
        bundle.entrypoint,
        "--worker-interpreter",
        bundle.interpreter,
        "--worker-python-version",
        bundle.python_version,
        "--worker-architecture",
        bundle.architecture,
        "--worker-package-sid",
        bundle.package_sid,
        "--worker-owner-sid",
        bundle.owner_sid,
        "--worker-provisioner-sid",
        bundle.provisioner_sid,
        "--worker-broker-sid",
        bundle.broker_sid,
        "--ambient-interpreter-root",
        str(bundle.ambient_interpreter_root),
        "--campaign-root",
        str(bundle.campaign_root),
        "--appcontainer-profile-root",
        str(bundle.appcontainer_profile_root),
        "--broker-profile-root",
        str(bundle.broker_profile_root),
        "--user-data-root",
        str(bundle.user_data_root),
    ]


def test_launcher_default_off_returns_before_dependencies_or_envelope(
    tmp_path: Path,
) -> None:
    launcher = _launcher_module()
    stdout = StringIO()
    stderr = StringIO()

    def forbidden():
        raise AssertionError("disabled launcher constructed dependencies")

    code = launcher.main(
        _launcher_args(tmp_path),
        settings_factory=lambda: SimpleNamespace(dual_live_runtime_enabled=False),
        dependencies_factory=forbidden,
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    assert stdout.getvalue() == "DISABLED: dual_live_runtime_disabled\n"
    assert stderr.getvalue() == ""


def test_standard_launcher_needs_no_authority_arguments_while_default_off() -> None:
    launcher = _launcher_module()
    stdout = StringIO()
    code = launcher.main(
        [],
        settings_factory=lambda: SimpleNamespace(dual_live_runtime_enabled=False),
        dependencies_factory=lambda: pytest.fail("dependencies constructed"),
        stdout=stdout,
    )
    assert code == 0
    assert stdout.getvalue() == "DISABLED: dual_live_runtime_disabled\n"


def test_launcher_forwards_exact_arguments_to_runtime_without_live_effect(
    tmp_path: Path,
) -> None:
    launcher = _launcher_module()
    runtime = _runtime_module()
    stdout = StringIO()
    stderr = StringIO()
    captured: list[tuple[object, object]] = []
    dependencies = object()

    def prepare(request, received_dependencies):
        captured.append((request, received_dependencies))
        return runtime.RuntimeResult(runtime.RuntimeStatus.HOLD, "test_hold")

    code = launcher.main(
        _launcher_args(tmp_path),
        settings_factory=lambda: SimpleNamespace(dual_live_runtime_enabled=True),
        dependencies_factory=lambda: dependencies,
        prepare=prepare,
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "HOLD: test_hold\n"
    assert len(captured) == 1
    request, received_dependencies = captured[0]
    assert request.enabled is True
    assert request.authority_envelope_path == tmp_path / "authority.json"
    assert request.authority_envelope_digest == "sha256:" + "0" * 64
    assert request.campaign_id == "campaign-test"
    assert request.canonical_root == tmp_path.resolve()
    assert request.connector_run_id == "00000000-0000-4000-8000-000000000001"
    assert request.reservation_database_path == tmp_path / "reservation.db"
    assert request.worker_bundle == _worker_bundle(runtime, tmp_path.resolve())
    assert request.sciencebase_request == _science_request(runtime)
    assert received_dependencies is dependencies


def test_standard_launcher_never_turns_prepared_envelope_into_live_go(
    tmp_path: Path,
) -> None:
    launcher = _launcher_module()
    runtime = _runtime_module()
    stderr = StringIO()
    closes: list[str] = []
    prepared = SimpleNamespace(
        reservation_store=SimpleNamespace(close=lambda: closes.append("store_close"))
    )

    code = launcher.main(
        _launcher_args(tmp_path),
        settings_factory=lambda: SimpleNamespace(dual_live_runtime_enabled=True),
        dependencies_factory=lambda: object(),
        prepare=lambda _request, _dependencies: runtime.RuntimeResult(
            runtime.RuntimeStatus.PREPARED,
            "dual_live_runtime_prepared_non_live",
            prepared,
        ),
        stderr=stderr,
    )

    assert code == 2
    assert stderr.getvalue() == "HOLD: live_go_required\n"
    assert closes == ["store_close"]
