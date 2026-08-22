from __future__ import annotations

from pathlib import Path
import sys

import pytest

from app.services.sciencebase_reservation_security import (
    ReservationSecurityHold,
    WindowsReservationSecurity,
)
from app.services.sciencebase_spent_marker import (
    WindowsMarkerBackend,
    publish_new_initialized_file,
)


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows ACL proof")


def _secure_root(tmp_path: Path) -> Path:
    root = tmp_path / "Project6" / "Reservation"
    backend = WindowsMarkerBackend()
    handle = backend.open_directory(root)
    backend.close(handle)
    return root


def _secure_database(root: Path) -> Path:
    database = root / "reservation.db"
    publish_new_initialized_file(
        database,
        lambda staging: staging.write_bytes(b"reservation-security-test"),
        resecure_after_initialize=True,
    )
    return database


def test_windows_birth_scope_sets_exact_duplicate_dacl_and_restores_thread_token(
    tmp_path: Path,
) -> None:
    security = WindowsReservationSecurity(_secure_root(tmp_path))
    source = security._open_process_token()
    prior = security._open_thread_token(security.TOKEN_QUERY)
    source_before = security._token_snapshot(source)
    prior_id = security._token_id(prior) if prior is not None else None
    try:
        with security.birth_scope():
            active = security._open_thread_token(security.TOKEN_QUERY)
            assert active is not None
            try:
                assert security._token_snapshot(active) == (
                    security._owner_text,
                    security._owner_text,
                    security._exact_aces(),
                )
            finally:
                security.backend.kernel32.CloseHandle(active)

        restored = security._open_thread_token(security.TOKEN_QUERY)
        try:
            assert (
                security._token_id(restored) if restored is not None else None
            ) == prior_id
        finally:
            if restored is not None:
                security.backend.kernel32.CloseHandle(restored)
        assert security._token_snapshot(source) == source_before
    finally:
        if prior is not None:
            security.backend.kernel32.CloseHandle(prior)
        security.backend.kernel32.CloseHandle(source)


def test_windows_transient_journal_oracle_distinguishes_binding_missing_and_acl(
    tmp_path: Path,
) -> None:
    root = _secure_root(tmp_path)
    database = _secure_database(root)
    security = WindowsReservationSecurity(root)
    journal = database.with_name(database.name + "-journal")

    with pytest.raises(
        ReservationSecurityHold, match="reservation_journal_binding_invalid"
    ):
        security.verify_transient_journal(database, root / "wrong-journal")

    with pytest.raises(ReservationSecurityHold, match="reservation_journal_missing"):
        security.verify_transient_journal(database, journal)

    journal.write_bytes(b"ordinary-default-dacl")
    with pytest.raises(
        ReservationSecurityHold, match="reservation_journal_security_invalid"
    ):
        security.verify_transient_journal(database, journal)
    with pytest.raises(
        ReservationSecurityHold, match="reservation_journal_cleanup_indeterminate"
    ):
        security.verify_journal_absent(journal)


def test_windows_durable_oracle_rejects_ordinary_default_acl(tmp_path: Path) -> None:
    root = _secure_root(tmp_path)
    database = root / "reservation.db"
    database.write_bytes(b"ordinary-default-dacl")
    security = WindowsReservationSecurity(root)
    handle = security._open_no_delete_share(database)
    try:
        _owner_matches, protected, aces = security._security_posture(handle)
        assert not protected
        assert aces != security._exact_aces()
    finally:
        security.backend.close(handle)

    with pytest.raises(
        ReservationSecurityHold, match="reservation_database_security_invalid"
    ):
        security.verify_database(database)


def test_windows_journal_oracle_rejects_root_dacl_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _secure_root(tmp_path)
    database = _secure_database(root)
    security = WindowsReservationSecurity(root)
    journal = database.with_name(database.name + "-journal")
    with security.birth_scope():
        journal.write_bytes(b"birth-secured")
    security.verify_transient_journal(database, journal)

    secure = security.backend.secure

    def drifted(handle: object) -> tuple[bool, bool, bool]:
        if not isinstance(handle, int):
            return True, False, True
        return secure(handle)

    monkeypatch.setattr(security.backend, "secure", drifted)
    with pytest.raises(
        ReservationSecurityHold, match="reservation_journal_binding_invalid"
    ):
        security.verify_transient_journal(database, journal)
