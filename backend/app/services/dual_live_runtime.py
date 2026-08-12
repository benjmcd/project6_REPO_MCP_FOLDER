"""Default-off composition for the B0 dual-live capability boundary.

An authority envelope is an immutable binding input, never a grant of live
authority.  This module does not create, issue, persist, or infer envelopes.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Protocol

from . import dual_live_worker_bundle as worker_bundle_contract

from .connector_egress_contract import (
    AUTHORITY_SCHEMA_VERSION,
    AuthorityBindings,
    AuthorityEnvelope,
    ContractHold,
    RequestLimits,
    validate_authority_envelope,
)
from .dual_live_sciencebase_producer import ScienceBaseInput


_SHA256_REF = re.compile(r"sha256:[0-9a-f]{64}\Z")
_WRAPPER_TOKEN_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_GIT_REF = re.compile(r"refs/[A-Za-z0-9._/-]{1,512}\Z")
MAX_AUTHORITY_ENVELOPE_BYTES = 64 * 1024
SCIENCEBASE_MAX_RESPONSE_BYTES = 64 * 1024 * 1024
SCIENCEBASE_MAX_TOTAL_BYTES = 512 * 1024 * 1024
SCIENCEBASE_TIMEOUT_SECONDS = 30


class RuntimeHold(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class RuntimeStatus(str, Enum):
    DISABLED = "DISABLED"
    HOLD = "HOLD"
    PREPARED = "PREPARED"


class ExecutionAuthorityConsumer(Protocol):
    """Injected, non-CLI capability that atomically consumes one exact live GO."""

    def consume_exact(self, envelope_digest: str) -> bool: ...


@dataclass(frozen=True)
class RuntimeRequest:
    enabled: bool
    authority_envelope_path: Path
    authority_envelope_digest: str
    campaign_id: str
    canonical_root: Path
    connector_run_id: str
    reservation_database_path: Path
    source_root: Path
    worker_bundle: "RuntimeWorkerBundle | None" = None
    sciencebase_request: "RuntimeScienceBaseRequest | None" = None


@dataclass(frozen=True)
class RuntimeScienceBaseRequest:
    query: str
    expected_item_id: str
    expected_file_name: str


@dataclass(frozen=True)
class RuntimeWorkerBundle:
    root: Path
    provisioning_root: Path
    profile_moniker: str
    manifest_digest: str
    entrypoint: str
    interpreter: str
    python_version: str
    architecture: str
    package_sid: str
    owner_sid: str
    provisioner_sid: str
    broker_sid: str
    ambient_interpreter_root: Path
    campaign_root: Path
    appcontainer_profile_root: Path
    broker_profile_root: Path
    user_data_root: Path


@dataclass(frozen=True)
class ExpectedAuthority:
    schema_version: str
    campaign_id: str
    canonical_root: Path
    connector_run_id: str
    source_commit: str
    interpreter_identity: str


@dataclass(frozen=True)
class ValidatedAuthorityEnvelope:
    envelope: AuthorityEnvelope
    live_authority: bool = False
    persisted: bool = False
    issued_by_b0: bool = False


@dataclass(frozen=True)
class RuntimeDependencies:
    read_bytes: Callable[[Path, int], bytes]
    source_commit: Callable[[Path], str]
    interpreter_identity: Callable[[Path], str]
    reservation_store_factory: Callable[[Path, Path], Any]
    boundary_factory: Callable[..., Any]
    transport_factory: Callable[[Any], Any]
    broker_factory: Callable[[Any], Any]
    bundle_validator: Callable[..., Any] = worker_bundle_contract.validate_worker_bundle
    bundle_probe_factory: Callable[[worker_bundle_contract.BundleBinding], Any] = (
        worker_bundle_contract.WindowsBundleProbe
    )


@dataclass(frozen=True)
class PreparedRuntime:
    envelope: ValidatedAuthorityEnvelope
    reservation_store: Any
    boundary: Any
    transport: Any
    broker: Any
    producer_request: ScienceBaseInput
    worker_manifest_digest: str = ""
    source_root: Path | None = None
    source_commit: str = ""
    source_commit_reader: Callable[[Path], str] | None = None


@dataclass(frozen=True)
class RuntimeResult:
    status: RuntimeStatus
    code: str
    prepared: PreparedRuntime | None = None


def _opaque_envelope_fields(raw: bytes) -> tuple[str, str, str]:
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "", "", ""
    if not isinstance(document, dict):
        return "", "", ""
    return (
        document.get("authorization_digest", ""),
        document.get("grant_digest", ""),
        document.get("wrapper_start_token_ref", ""),
    )


def _require_opaque_references(
    authorization_digest: object,
    grant_digest: object,
    wrapper_start_token_ref: object,
) -> None:
    if (
        not isinstance(authorization_digest, str)
        or _SHA256_REF.fullmatch(authorization_digest) is None
    ):
        raise RuntimeHold("authority_digest_invalid")
    if not isinstance(grant_digest, str) or _SHA256_REF.fullmatch(grant_digest) is None:
        raise RuntimeHold("grant_digest_invalid")
    if (
        not isinstance(wrapper_start_token_ref, str)
        or _WRAPPER_TOKEN_REF.fullmatch(wrapper_start_token_ref) is None
    ):
        raise RuntimeHold("wrapper_start_token_ref_invalid")


def load_authority_envelope_once(
    path: Path,
    expected_content_digest: str,
    expected: ExpectedAuthority,
    *,
    read_bytes: Callable[[Path, int], bytes] | None = None,
) -> ValidatedAuthorityEnvelope:
    """Read and validate an external envelope without retaining or issuing it."""

    try:
        reader = read_bytes or _read_bounded
        raw = reader(path, MAX_AUTHORITY_ENVELOPE_BYTES + 1)
    except OSError as exc:
        raise RuntimeHold("authority_envelope_unreadable") from exc
    if not isinstance(raw, bytes):
        raise RuntimeHold("authority_envelope_unreadable")
    if len(raw) > MAX_AUTHORITY_ENVELOPE_BYTES:
        raise RuntimeHold("authority_envelope_too_large")

    authorization_digest, grant_digest, wrapper_start_token_ref = (
        _opaque_envelope_fields(raw)
    )
    bindings = AuthorityBindings(
        schema_version=expected.schema_version,
        campaign_id=expected.campaign_id,
        canonical_root=str(expected.canonical_root),
        connector_run_id=expected.connector_run_id,
        source_commit=expected.source_commit,
        interpreter_identity=expected.interpreter_identity,
        authorization_digest=authorization_digest,
        grant_digest=grant_digest,
        wrapper_start_token_ref=wrapper_start_token_ref,
    )
    try:
        envelope = validate_authority_envelope(raw, expected_content_digest, bindings)
    except ContractHold as exc:
        raise RuntimeHold(str(exc)) from exc
    _require_opaque_references(
        envelope.authorization_digest,
        envelope.grant_digest,
        envelope.wrapper_start_token_ref,
    )
    return ValidatedAuthorityEnvelope(envelope=envelope)


def _read_bounded(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        return stream.read(limit)


def _bounded_ascii(path: Path, limit: int = 4096) -> str:
    raw = _read_bounded(path, limit + 1)
    if len(raw) > limit:
        raise RuntimeHold("runtime_identity_unavailable")
    try:
        return raw.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeHold("runtime_identity_unavailable") from exc


def _source_commit(
    source_root: Path,
    *,
    process_runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> str:
    try:
        root = Path(source_root).resolve(strict=True)
    except OSError:
        raise RuntimeHold("runtime_identity_unavailable") from None
    if root != source_root or not root.is_dir():
        raise RuntimeHold("runtime_identity_unavailable")
    git_executable = shutil.which("git")
    if not git_executable:
        raise RuntimeHold("runtime_identity_unavailable")
    git_environment = {
        "SystemRoot": r"C:\Windows",
        "WINDIR": r"C:\Windows",
        "GIT_CONFIG_GLOBAL": "NUL",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
    }

    def git(*arguments: str) -> bytes:
        try:
            result = process_runner(
                [git_executable, "-C", str(root), *arguments],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                shell=False,
                env=git_environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except BaseException:
            raise RuntimeHold("runtime_identity_unavailable") from None
        if (
            type(result.returncode) is not int
            or result.returncode != 0
            or not isinstance(result.stdout, bytes)
            or len(result.stdout) > 64 * 1024
            or result.stderr not in {b"", None}
        ):
            raise RuntimeHold("runtime_identity_unavailable")
        return result.stdout

    try:
        with tempfile.TemporaryDirectory(prefix="project6-git-identity-") as home:
            git_environment["HOME"] = home
            git_environment["XDG_CONFIG_HOME"] = home
            top = git("rev-parse", "--show-toplevel").decode("utf-8", "strict").strip()
            try:
                observed_root = Path(top).resolve(strict=True)
            except OSError:
                raise RuntimeHold("runtime_identity_unavailable") from None
            if observed_root != root:
                raise RuntimeHold("runtime_identity_unavailable")
            commit = git("rev-parse", "HEAD").decode("ascii", "strict").strip()
            if _COMMIT.fullmatch(commit) is None:
                raise RuntimeHold("runtime_identity_unavailable")
            if git("status", "--porcelain=v1", "--untracked-files=all") != b"":
                raise RuntimeHold("runtime_source_not_clean")
            return commit
    except OSError:
        raise RuntimeHold("runtime_identity_unavailable") from None


def _interpreter_identity(interpreter: Path | None = None) -> str:
    path = (interpreter or Path(sys.executable)).resolve(strict=True)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise RuntimeHold("runtime_identity_unavailable")
    return "sha256:" + digest.hexdigest()


def _validated_sciencebase_input(
    request: RuntimeScienceBaseRequest | None,
    envelope: AuthorityEnvelope,
) -> ScienceBaseInput:
    if request is None:
        raise RuntimeHold("sciencebase_request_missing")
    for value, maximum in (
        (request.query, 4096),
        (request.expected_item_id, 512),
        (request.expected_file_name, 512),
    ):
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value.encode("utf-8")) > maximum
            or any(
                ord(character) < 0x20 or ord(character) == 0x7F for character in value
            )
        ):
            raise RuntimeHold("sciencebase_request_invalid")
    return ScienceBaseInput(
        query=request.query,
        expected_item_id=request.expected_item_id,
        expected_file_name=request.expected_file_name,
        envelope_digest=envelope.content_digest,
        campaign_id=envelope.campaign_id,
        canonical_root=envelope.canonical_root,
        connector_run_id=envelope.connector_run_id,
        authorization_digest=envelope.authorization_digest,
        grant_digest=envelope.grant_digest,
        max_total_bytes=SCIENCEBASE_MAX_TOTAL_BYTES,
        limits=RequestLimits(
            timeout_seconds=SCIENCEBASE_TIMEOUT_SECONDS,
            max_response_bytes=SCIENCEBASE_MAX_RESPONSE_BYTES,
            max_redirects=0,
        ),
        max_redirect_hops=0,
        connector_run_target_id=None,
    )


def prepare_dual_live_runtime(
    request: RuntimeRequest,
    dependencies: RuntimeDependencies,
) -> RuntimeResult:
    if not request.enabled:
        return RuntimeResult(
            status=RuntimeStatus.DISABLED,
            code="dual_live_runtime_disabled",
        )

    try:
        canonical_root = request.canonical_root.resolve(strict=True)
    except OSError:
        return RuntimeResult(RuntimeStatus.HOLD, "canonical_root_unavailable")
    if canonical_root != request.canonical_root or not canonical_root.is_dir():
        return RuntimeResult(RuntimeStatus.HOLD, "canonical_root_not_canonical")

    try:
        source_root = request.source_root.resolve(strict=True)
    except OSError:
        return RuntimeResult(RuntimeStatus.HOLD, "source_root_unavailable")
    if (
        source_root != request.source_root
        or not source_root.is_dir()
        or source_root == canonical_root
        or source_root in canonical_root.parents
        or canonical_root in source_root.parents
    ):
        return RuntimeResult(RuntimeStatus.HOLD, "source_root_not_isolated")

    try:
        source_commit = dependencies.source_commit(source_root)
    except RuntimeHold as exc:
        return RuntimeResult(RuntimeStatus.HOLD, exc.code)
    except (OSError, ValueError, RuntimeError):
        return RuntimeResult(RuntimeStatus.HOLD, "runtime_identity_unavailable")

    bundle_values = request.worker_bundle
    if bundle_values is None:
        return RuntimeResult(RuntimeStatus.HOLD, "worker_bundle_binding_missing")
    if bundle_values.entrypoint != "tools/dual_live_run.py":
        return RuntimeResult(RuntimeStatus.HOLD, "worker_bundle_entrypoint_invalid")
    try:
        bundle_campaign_root = bundle_values.campaign_root.resolve(strict=True)
    except OSError:
        return RuntimeResult(RuntimeStatus.HOLD, "worker_bundle_campaign_root_invalid")
    if bundle_campaign_root != canonical_root:
        return RuntimeResult(RuntimeStatus.HOLD, "worker_bundle_campaign_root_mismatch")
    try:
        binding = worker_bundle_contract.BundleBinding(
            root=bundle_values.root,
            provisioning_root=bundle_values.provisioning_root,
            profile_moniker=bundle_values.profile_moniker,
            manifest_digest=bundle_values.manifest_digest,
            source_commit=source_commit,
            entrypoint=bundle_values.entrypoint,
            interpreter=bundle_values.interpreter,
            python_version=bundle_values.python_version,
            architecture=bundle_values.architecture,
            package_sid=bundle_values.package_sid,
            owner_sid=bundle_values.owner_sid,
            provisioner_sid=bundle_values.provisioner_sid,
            broker_sid=bundle_values.broker_sid,
            ambient_interpreter_root=bundle_values.ambient_interpreter_root,
            repository_root=source_root,
            campaign_root=canonical_root,
            appcontainer_profile_root=bundle_values.appcontainer_profile_root,
            broker_profile_root=bundle_values.broker_profile_root,
            user_data_root=bundle_values.user_data_root,
        )
        bundle_probe = dependencies.bundle_probe_factory(binding)
        validated_bundle = dependencies.bundle_validator(binding, bundle_probe)
        validated_interpreter = validated_bundle.interpreter
        if (
            not isinstance(validated_interpreter, Path)
            or not validated_interpreter.is_absolute()
        ):
            raise RuntimeHold("worker_bundle_interpreter_invalid")
        interpreter_identity = dependencies.interpreter_identity(validated_interpreter)
    except worker_bundle_contract.BundleHold as exc:
        return RuntimeResult(RuntimeStatus.HOLD, exc.code)
    except RuntimeHold as exc:
        return RuntimeResult(RuntimeStatus.HOLD, exc.code)
    except (AttributeError, OSError, TypeError, ValueError, RuntimeError):
        return RuntimeResult(RuntimeStatus.HOLD, "worker_bundle_validation_failed")

    expected = ExpectedAuthority(
        schema_version=AUTHORITY_SCHEMA_VERSION,
        campaign_id=request.campaign_id,
        canonical_root=canonical_root,
        connector_run_id=request.connector_run_id,
        source_commit=source_commit,
        interpreter_identity=interpreter_identity,
    )
    try:
        validated = load_authority_envelope_once(
            request.authority_envelope_path,
            request.authority_envelope_digest,
            expected,
            read_bytes=dependencies.read_bytes,
        )
    except RuntimeHold as exc:
        return RuntimeResult(RuntimeStatus.HOLD, exc.code)
    try:
        producer_request = _validated_sciencebase_input(
            request.sciencebase_request, validated.envelope
        )
    except (ContractHold, RuntimeHold) as exc:
        code = exc.code if isinstance(exc, RuntimeHold) else str(exc)
        return RuntimeResult(RuntimeStatus.HOLD, code)

    if request.reservation_database_path != canonical_root / "reservation.db":
        return RuntimeResult(RuntimeStatus.HOLD, "reservation_database_path_mismatch")
    try:
        reservation_store = dependencies.reservation_store_factory(
            canonical_root,
            request.reservation_database_path,
        )
    except (OSError, TypeError, ValueError, RuntimeError):
        return RuntimeResult(RuntimeStatus.HOLD, "reservation_store_unavailable")

    census = getattr(reservation_store, "assert_no_reservations", None)
    if not callable(census):
        return _hold_after_store(reservation_store, "reservation_census_unavailable")
    try:
        census_result = census(request.connector_run_id)
    except Exception:
        return _hold_after_store(reservation_store, "reservation_census_ambiguous")
    if census_result is not None:
        return _hold_after_store(reservation_store, "reservation_census_not_empty")

    try:
        boundary = dependencies.boundary_factory(
            str(canonical_root),
            request.campaign_id,
            bundle_binding=binding,
            bundle_probe=bundle_probe,
        )
        transport = dependencies.transport_factory(reservation_store)
        broker = dependencies.broker_factory(transport)
    except Exception:
        return _hold_after_store(
            reservation_store, "runtime_component_construction_failed"
        )

    prepared = PreparedRuntime(
        envelope=validated,
        reservation_store=reservation_store,
        boundary=boundary,
        transport=transport,
        broker=broker,
        producer_request=producer_request,
        worker_manifest_digest=binding.manifest_digest,
        source_root=source_root,
        source_commit=source_commit,
        source_commit_reader=dependencies.source_commit,
    )
    return RuntimeResult(
        status=RuntimeStatus.PREPARED,
        code="dual_live_runtime_prepared_non_live",
        prepared=prepared,
    )


def default_runtime_dependencies() -> RuntimeDependencies:
    """Construct broker-only defaults after launcher worker dispatch."""

    from .connector_egress_transport import ConnectorEgressTransport, ReservationStore
    from .dual_live_effect_guard import BrokerEffectGuard
    from .dual_live_windows_boundary import WindowsEffectBoundary

    return RuntimeDependencies(
        read_bytes=_read_bounded,
        source_commit=_source_commit,
        interpreter_identity=_interpreter_identity,
        reservation_store_factory=ReservationStore,
        boundary_factory=WindowsEffectBoundary,
        transport_factory=lambda store: ConnectorEgressTransport(
            store, session_factory=_requests_session
        ),
        broker_factory=BrokerEffectGuard,
    )


def _requests_session() -> Any:
    import requests

    session = requests.Session()
    session.trust_env = False
    session.headers.clear()
    session.cookies.clear()
    session.auth = None
    return session


def run_prepared_runtime(
    prepared: PreparedRuntime,
    *,
    execution_authority: ExecutionAuthorityConsumer | None = None,
    open_writer: Callable[[int], Any] | None = None,
    release_worker: Callable[[Any], None] | None = None,
) -> Any:
    """Run one bounded worker session; the boundary owns all process lifetime."""

    if not isinstance(prepared, PreparedRuntime):
        raise RuntimeHold("runtime_prepared_invalid")
    raw_handles = [0, 0, 0, 0]
    try:
        digest = prepared.envelope.envelope.content_digest
        if (
            prepared.source_root is None
            or not isinstance(prepared.source_commit, str)
            or _COMMIT.fullmatch(prepared.source_commit) is None
            or not callable(prepared.source_commit_reader)
        ):
            raise RuntimeHold("runtime_source_identity_invalid")
        try:
            observed_source_commit = prepared.source_commit_reader(prepared.source_root)
        except BaseException:
            raise RuntimeHold("runtime_source_identity_drift") from None
        if observed_source_commit != prepared.source_commit:
            raise RuntimeHold("runtime_source_identity_drift")
        if open_writer is None:
            from .dual_live_windows_boundary import open_pipe_writer

            open_writer = open_pipe_writer
        if release_worker is None:
            from .dual_live_effect_guard import release_sciencebase_worker

            release_worker = release_sciencebase_worker
        consume = getattr(execution_authority, "consume_exact", None)
        if (
            not isinstance(digest, str)
            or _SHA256_REF.fullmatch(digest) is None
            or not callable(consume)
        ):
            raise RuntimeHold("live_go_required")

        def consume_authority() -> bool:
            try:
                consumed = consume(digest)
            except BaseException:
                raise RuntimeHold("live_go_required") from None
            if consumed is not True:
                raise RuntimeHold("live_go_required")
            return True

        with prepared.boundary.acquire():
            try:
                allocated = prepared.boundary.create_worker_pipes()
                if isinstance(allocated, tuple) and len(allocated) == 4:
                    raw_handles[:] = [
                        value
                        if not isinstance(value, bool)
                        and isinstance(value, int)
                        and value > 0
                        else 0
                        for value in allocated
                    ]
                if (
                    not isinstance(allocated, tuple)
                    or len(allocated) != 4
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, int)
                        or value <= 0
                        for value in allocated
                    )
                    or len(set(allocated)) != 4
                ):
                    raise RuntimeHold("worker_pipe_identity_invalid")
                prepared.boundary.launch_worker(
                    tuple(raw_handles[2:]), mode="sciencebase"
                )
                child_close_failed = False
                for index in (2, 3):
                    handle = raw_handles[index]
                    try:
                        prepared.boundary.close_pipe_handle(handle)
                    except BaseException:
                        child_close_failed = True
                    else:
                        raw_handles[index] = 0
                if child_close_failed:
                    raise RuntimeHold("worker_pipe_close_failed")
                with contextlib.ExitStack() as streams:
                    writer = streams.enter_context(open_writer(raw_handles[1]))
                    raw_handles[1] = 0
                    with prepared.boundary.broker_session_deadline(15_000):
                        output = prepared.broker.serve_sciencebase(
                            prepared.producer_request,
                            None,
                            writer,
                            read_next=lambda: prepared.boundary.read_worker_frame(
                                raw_handles[0], 15_000
                            ),
                            consume_authority=consume_authority,
                        )
                        prepared.boundary.census()
                        release_worker(writer)
                        prepared.boundary.wait_worker(15_000)
                return output
            finally:
                _close_raw_handles(prepared.boundary, raw_handles)
    except RuntimeHold:
        raise
    except BaseException:
        raise RuntimeHold("runtime_execution_failed") from None
    finally:
        _close_reservation_store(prepared.reservation_store)


def _close_raw_handles(boundary: Any, handles: list[int]) -> None:
    cleanup_failed = False
    closed: set[int] = set()
    for index, handle in enumerate(handles):
        if not handle or handle in closed:
            continue
        closed.add(handle)
        try:
            boundary.close_pipe_handle(handle)
        except BaseException:
            cleanup_failed = True
        finally:
            handles[index] = 0
    if cleanup_failed:
        raise RuntimeHold("worker_pipe_cleanup_failed") from None


def _close_reservation_store(store: Any) -> None:
    close = getattr(store, "close", None)
    if not callable(close):
        raise RuntimeHold("reservation_store_close_failed")
    try:
        close()
    except BaseException:
        raise RuntimeHold("reservation_store_close_failed") from None


def _hold_after_store(store: Any, code: str) -> RuntimeResult:
    try:
        _close_reservation_store(store)
    except RuntimeHold as exc:
        return RuntimeResult(RuntimeStatus.HOLD, exc.code)
    return RuntimeResult(RuntimeStatus.HOLD, code)


def close_prepared_runtime(prepared: Any) -> None:
    """Release prepared reservation identity handles without executing effects."""

    _close_reservation_store(getattr(prepared, "reservation_store", None))
