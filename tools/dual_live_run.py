from __future__ import annotations

import argparse
import contextlib
import os
import sys
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _worker_handles(values: Sequence[str]) -> tuple[int, int]:
    if len(values) != 2 or any(
        not isinstance(value, str) or not value.isascii() or not value.isdecimal()
        for value in values
    ):
        raise ValueError("worker handles invalid")
    handles = tuple(int(value, 10) for value in values)
    if any(value <= 0 for value in handles) or len(set(handles)) != 2:
        raise ValueError("worker handles invalid")
    return handles[0], handles[1]


def _worker_dispatch(mode: str, values: Sequence[str]) -> int:
    try:
        read_handle, write_handle = _worker_handles(values)
        from app.services.dual_live_windows_boundary import (
            open_pipe_reader,
            open_pipe_writer,
        )

        worker: Callable[[Any, Any], None]
        if mode == "probe":
            from app.services.dual_live_windows_boundary import run_probe_worker

            worker = run_probe_worker
        elif mode == "sciencebase":
            from app.services.dual_live_effect_guard import (
                run_sciencebase_worker,
            )

            worker = run_sciencebase_worker
        else:
            return 2
        with contextlib.ExitStack() as streams:
            reader = streams.enter_context(open_pipe_reader(read_handle))
            writer = streams.enter_context(open_pipe_writer(write_handle))
            worker(reader, writer)
        return 0
    except BaseException:
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and prepare the default-off dual-live capability broker after strict "
            "authority-envelope validation. This command does not grant live authority."
        )
    )
    parser.add_argument("--authority-envelope", required=True, type=Path)
    parser.add_argument("--authority-envelope-sha256", required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument("--connector-run-id", required=True)
    parser.add_argument("--reservation-database", required=True, type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--expected-item-id", required=True)
    parser.add_argument("--expected-file-name", required=True)
    parser.add_argument(
        "--owner-go",
        type=Path,
        help="Exact GO document; still requires an independently trusted owner authenticator.",
    )
    parser.add_argument(
        "--owner-go-sha256",
        help="Content digest only; never owner authority by itself.",
    )
    parser.add_argument(
        "--owner-go-signature",
        type=Path,
        help="Detached OpenSSH signature from the pinned Project6 owner identity.",
    )
    for name in (
        "worker-bundle-root",
        "worker-provisioning-root",
        "ambient-interpreter-root",
        "campaign-root",
        "appcontainer-profile-root",
        "broker-profile-root",
        "user-data-root",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    for name in (
        "worker-profile-moniker",
        "worker-manifest-sha256",
        "worker-entrypoint",
        "worker-interpreter",
        "worker-python-version",
        "worker-architecture",
        "worker-package-sid",
        "worker-owner-sid",
        "worker-provisioner-sid",
        "worker-broker-sid",
    ):
        parser.add_argument(f"--{name}", required=True)
    return parser


def _verification_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Independently verify one terminal ScienceBase closeout without live authority."
    )
    parser.add_argument("--verify-closeout", action="store_true", required=True)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument("--connector-run-id", required=True)
    parser.add_argument("--reservation-database", required=True, type=Path)
    parser.add_argument("--owner-go-sha256", required=True)
    return parser


class _RuntimeSettings:
    def __init__(self, enabled: bool) -> None:
        self.dual_live_runtime_enabled = enabled


def _default_settings() -> Any:
    value = os.environ.get("DUAL_LIVE_RUNTIME_ENABLED", "false").strip().lower()
    return _RuntimeSettings(value in {"1", "true", "yes", "on"})


def _default_dependencies() -> Any:
    from app.services.dual_live_runtime import default_runtime_dependencies

    return default_runtime_dependencies()


def _default_execute(
    prepared: Any,
    *,
    go_path: Path,
    go_digest: str,
    signature_path: Path,
) -> Any:
    from app.services.connector_egress_transport import ReservationStore
    from app.services.dual_live_runtime import run_prepared_runtime
    from app.services.sciencebase_live_readiness import (
        OpenSshOwnerGoAuthenticator,
        execute_sciencebase_live,
    )

    return execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run_prepared_runtime,
        store_factory=ReservationStore,
        owner_authenticator=OpenSshOwnerGoAuthenticator(signature_path),
    )


def _default_verify(**kwargs: Any) -> Any:
    from app.services.connector_egress_transport import ReservationStore
    from app.services.sciencebase_live_readiness import verify_sciencebase_closeout

    return verify_sciencebase_closeout(store_factory=ReservationStore, **kwargs)


def main(
    argv: Sequence[str] | None = None,
    *,
    settings_factory: Callable[[], Any] = _default_settings,
    dependencies_factory: Callable[[], Any] = _default_dependencies,
    prepare: Callable[[Any, Any], Any] | None = None,
    execute: Callable[..., Any] = _default_execute,
    verify: Callable[..., Any] = _default_verify,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments[:1] == ["--worker-probe"]:
        return _worker_dispatch("probe", arguments[1:])
    if arguments[:1] == ["--worker-sciencebase"]:
        return _worker_dispatch("sciencebase", arguments[1:])
    if arguments[:1] == ["--verify-closeout"]:
        verify_args = _verification_parser().parse_args(arguments)
        result = verify(
            canonical_root=verify_args.canonical_root,
            reservation_database_path=verify_args.reservation_database,
            connector_run_id=verify_args.connector_run_id,
            go_digest=verify_args.owner_go_sha256,
        )
        if getattr(result, "status", None) == "VERIFIED":
            print(f"VERIFIED: {result.code}", file=stdout)
            return 0
        print(f"HOLD: {getattr(result, 'code', 'sciencebase_closeout_failed')}", file=stderr)
        return 2
    if "-h" in arguments or "--help" in arguments:
        _parser().parse_args(arguments)
    settings = settings_factory()
    enabled = settings.dual_live_runtime_enabled is True
    if not enabled:
        print("DISABLED: dual_live_runtime_disabled", file=stdout)
        return 0

    from app.services.dual_live_runtime import (
        RuntimeRequest,
        RuntimeScienceBaseRequest,
        RuntimeStatus,
        RuntimeWorkerBundle,
        close_prepared_runtime,
        prepare_dual_live_runtime,
    )

    args = _parser().parse_args(arguments)
    go_bindings = (
        args.owner_go,
        args.owner_go_sha256,
        args.owner_go_signature,
    )
    if any(value is None for value in go_bindings) and any(
        value is not None for value in go_bindings
    ):
        print("HOLD: live_go_binding_incomplete", file=stderr)
        return 2

    request = RuntimeRequest(
        enabled=True,
        authority_envelope_path=args.authority_envelope,
        authority_envelope_digest=args.authority_envelope_sha256,
        campaign_id=args.campaign_id,
        canonical_root=args.canonical_root,
        connector_run_id=args.connector_run_id,
        reservation_database_path=args.reservation_database,
        sciencebase_request=RuntimeScienceBaseRequest(
            query=args.query,
            expected_item_id=args.expected_item_id,
            expected_file_name=args.expected_file_name,
        ),
        worker_bundle=RuntimeWorkerBundle(
            root=args.worker_bundle_root,
            provisioning_root=args.worker_provisioning_root,
            profile_moniker=args.worker_profile_moniker,
            manifest_digest=args.worker_manifest_sha256,
            entrypoint=args.worker_entrypoint,
            interpreter=args.worker_interpreter,
            python_version=args.worker_python_version,
            architecture=args.worker_architecture,
            package_sid=args.worker_package_sid,
            owner_sid=args.worker_owner_sid,
            provisioner_sid=args.worker_provisioner_sid,
            broker_sid=args.worker_broker_sid,
            ambient_interpreter_root=args.ambient_interpreter_root,
            campaign_root=args.campaign_root,
            appcontainer_profile_root=args.appcontainer_profile_root,
            broker_profile_root=args.broker_profile_root,
            user_data_root=args.user_data_root,
        ),
    )
    result = (prepare or prepare_dual_live_runtime)(request, dependencies_factory())
    if result.status is RuntimeStatus.DISABLED:
        print(f"DISABLED: {result.code}", file=stdout)
        return 0
    if result.status is RuntimeStatus.HOLD or result.prepared is None:
        print(f"HOLD: {result.code}", file=stderr)
        return 2

    if args.owner_go is None:
        try:
            close_prepared_runtime(result.prepared)
        except Exception:
            print("HOLD: runtime_cleanup_failed", file=stderr)
            return 2
        print("HOLD: live_go_required", file=stderr)
        return 2
    execution = execute(
        result.prepared,
        go_path=args.owner_go,
        go_digest=args.owner_go_sha256,
        signature_path=args.owner_go_signature,
    )
    if getattr(execution, "status", None) == "TERMINAL":
        print(f"TERMINAL: {execution.code}", file=stdout)
        return 0
    print(f"HOLD: {getattr(execution, 'code', 'sciencebase_execution_failed')}", file=stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
