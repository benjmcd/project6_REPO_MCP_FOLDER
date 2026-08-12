from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
from typing import Sequence, TextIO


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one non-live dual-live preparation artifact."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    reservation = commands.add_parser("reservation-store")
    reservation.add_argument("--canonical-root", required=True, type=Path)
    reservation.add_argument("--connector-run-id", required=True)
    envelope = commands.add_parser("authority-envelope")
    envelope.add_argument("--output", required=True, type=Path)
    envelope.add_argument("--campaign-id", required=True)
    envelope.add_argument("--canonical-root", required=True, type=Path)
    envelope.add_argument("--connector-run-id", required=True)
    envelope.add_argument("--source-commit", required=True)
    envelope.add_argument("--interpreter-identity", required=True)
    envelope.add_argument("--authorization-digest", required=True)
    envelope.add_argument("--grant-digest", required=True)
    return parser


def _write_create_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "reservation-store":
        from app.services.sciencebase_live_readiness import (
            LiveReadinessHold,
            initialize_reservation_database,
        )

        try:
            database = initialize_reservation_database(
                args.canonical_root, args.connector_run_id
            )
        except LiveReadinessHold as exc:
            print(f"HOLD: {exc.code}", file=stderr)
            return 2
        print(f"INITIALIZED: {database}", file=stdout)
        return 0

    from app.services.connector_egress_contract import (
        AUTHORITY_SCHEMA_VERSION,
        RETIRED_WRAPPER_START_TOKEN_REF,
        ContractHold,
        emit_authority_envelope,
    )

    try:
        raw = emit_authority_envelope(
            {
                "schema_version": AUTHORITY_SCHEMA_VERSION,
                "campaign_id": args.campaign_id,
                "canonical_root": str(args.canonical_root),
                "connector_run_id": args.connector_run_id,
                "source_commit": args.source_commit,
                "interpreter_identity": args.interpreter_identity,
                "authorization_digest": args.authorization_digest,
                "grant_digest": args.grant_digest,
                "wrapper_start_token_ref": RETIRED_WRAPPER_START_TOKEN_REF,
            }
        )
        _write_create_once(args.output, raw)
    except FileExistsError:
        print("HOLD: authority_envelope_exists", file=stderr)
        return 2
    except (ContractHold, OSError, TypeError, ValueError):
        print("HOLD: authority_envelope_initialize_failed", file=stderr)
        return 2
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    print(f"INITIALIZED: {args.output}", file=stdout)
    print(f"AUTHORITY_ENVELOPE_SHA256: {digest}", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
