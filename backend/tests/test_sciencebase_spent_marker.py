from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys

import pytest

from app.services.sciencebase_spent_marker import (
    CustodyHold,
    MarkerIdentity,
    SpentMarkerHold,
    SpentMarkerStore,
    WindowsMarkerBackend,
    publish_new_initialized_file,
)


MARKER = (
    b'{"envelope_digest":"sha256:'
    + b"a" * 64
    + b'","go_id":"22222222-2222-4222-8222-222222222222",'
    + b'"schema":"project6.sciencebase_live_go_spent.v1"}'
)


@dataclass
class _Handle:
    kind: str


class FakeBackend:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = MarkerIdentity("vol", "dir", 1, False, True)
        self.file = MarkerIdentity("vol", "file", 1, False, False)
        self.owner_matches = True
        self.dacl_protected = True
        self.dacl_owner_broker_only = True
        self.contents = b""
        self.locked = False
        self.operations: list[str] = []

    def open_directory(self, path: Path) -> _Handle:
        assert path == self.root
        self.operations.append("open_directory")
        return _Handle("directory")

    def open_file(self, path: Path) -> tuple[_Handle, bool]:
        assert path == self.root / "spent.jsonl"
        self.operations.append("open_file_create_new")
        return _Handle("file"), not self.contents

    def identity(self, handle: _Handle) -> MarkerIdentity:
        self.operations.append(f"identity_{handle.kind}")
        return self.directory if handle.kind == "directory" else self.file

    def secure(self, handle: _Handle) -> tuple[bool, bool, bool]:
        self.operations.append(f"secure_{handle.kind}")
        return (
            self.owner_matches,
            self.dacl_protected,
            self.dacl_owner_broker_only,
        )

    def lock(self, handle: _Handle) -> None:
        assert handle.kind == "file"
        self.operations.append("lock")
        self.locked = True

    def unlock(self, handle: _Handle) -> None:
        self.operations.append("unlock")
        self.locked = False

    def read(self, handle: _Handle, limit: int) -> bytes:
        assert self.locked
        self.operations.append("read")
        return self.contents[: limit + 1]

    def append(self, handle: _Handle, value: bytes) -> None:
        assert self.locked
        self.operations.append("append")
        self.contents += value

    def flush(self, handle: _Handle) -> None:
        assert self.locked
        self.operations.append("flush")

    def close(self, handle: _Handle) -> None:
        self.operations.append(f"close_{handle.kind}")


@dataclass
class _PublishHandle:
    kind: str
    path: Path


class FakePublishBackend:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = MarkerIdentity("vol", "dir", 1, False, True)
        self.file = MarkerIdentity("vol", "file", 1, False, False)
        self.security = {
            "directory": (True, True, True),
            "file": (True, True, True),
        }
        self.identity_reads = 0
        self.drift_after: int | None = None
        self.operations: list[str] = []
        self.before_publish = lambda _path: None
        self.substituted_identity: MarkerIdentity | None = None
        self.fixed_volume = True

    def open_existing_directory(self, path: Path) -> _PublishHandle:
        assert path == self.root
        self.operations.append("open_directory")
        return _PublishHandle("directory", path)

    def create_new_file(self, path: Path) -> _PublishHandle:
        assert path.parent == self.root
        path.open("xb").close()
        self.operations.append("create_new_file")
        return _PublishHandle("file", path)

    def open_existing_file(self, path: Path) -> _PublishHandle:
        assert path.exists()
        self.operations.append("open_existing_file")
        kind = "substituted" if self.substituted_identity is not None else "file"
        return _PublishHandle(kind, path)

    def fixed_local(self, handle: _PublishHandle) -> bool:
        assert handle.kind == "directory"
        self.operations.append("fixed_local")
        return self.fixed_volume

    def identity(self, handle: _PublishHandle) -> MarkerIdentity:
        self.identity_reads += 1
        identity = (
            self.directory
            if handle.kind == "directory"
            else self.substituted_identity
            if handle.kind == "substituted"
            else self.file
        )
        assert identity is not None
        if self.drift_after is not None and self.identity_reads > self.drift_after:
            identity = replace(identity, file_id=f"{identity.file_id}-changed")
        self.operations.append(f"identity_{handle.kind}")
        return identity

    def secure(self, handle: _PublishHandle) -> tuple[bool, bool, bool]:
        self.operations.append(f"secure_{handle.kind}")
        return self.security["directory" if handle.kind == "directory" else "file"]

    def flush(self, handle: _PublishHandle) -> None:
        assert handle.kind == "file"
        self.operations.append("flush")

    def publish_new(
        self,
        handle: _PublishHandle,
        directory_handle: _PublishHandle,
        final: Path,
    ) -> None:
        assert directory_handle.kind == "directory"
        assert final.parent == directory_handle.path
        self.before_publish(final)
        if final.exists():
            raise FileExistsError(final)
        handle.path.rename(final)
        handle.path = final
        self.operations.append("publish_new")

    def discard(self, handle: _PublishHandle) -> None:
        self.operations.append("discard")
        handle.path.unlink(missing_ok=True)

    def close(self, handle: _PublishHandle) -> None:
        self.operations.append(f"close_{handle.kind}")


def _store(tmp_path: Path, backend: FakeBackend) -> SpentMarkerStore:
    return SpentMarkerStore(
        tmp_path / "authority" / "spent.jsonl", backend=backend, max_bytes=65536
    )


def test_wrong_owner_fails_closed_before_marker_scan(tmp_path: Path) -> None:
    backend = FakeBackend(tmp_path / "authority")
    backend.owner_matches = False

    with pytest.raises(SpentMarkerHold):
        _store(tmp_path, backend).claim_exact(MARKER)

    assert "read" not in backend.operations
    assert "append" not in backend.operations


def test_reparse_marker_fails_closed_before_marker_scan(tmp_path: Path) -> None:
    backend = FakeBackend(tmp_path / "authority")
    backend.file = replace(backend.file, reparse=True)

    with pytest.raises(SpentMarkerHold):
        _store(tmp_path, backend).claim_exact(MARKER)

    assert "read" not in backend.operations
    assert "append" not in backend.operations


def test_malformed_preseed_fails_closed_without_append(tmp_path: Path) -> None:
    backend = FakeBackend(tmp_path / "authority")
    backend.contents = b'not-json\n'

    with pytest.raises(SpentMarkerHold):
        _store(tmp_path, backend).claim_exact(MARKER)

    assert backend.contents == b'not-json\n'
    assert backend.operations.index("lock") < backend.operations.index("read")
    assert "append" not in backend.operations
    assert backend.operations.index("unlock") < backend.operations.index("close_file")


def test_claim_is_locked_flushed_revalidated_and_one_use(tmp_path: Path) -> None:
    backend = FakeBackend(tmp_path / "authority")
    store = _store(tmp_path, backend)

    assert store.claim_exact(MARKER) == "RECORDED"
    assert store.claim_exact(MARKER) == "EXISTS"

    first_lock = backend.operations.index("lock")
    first_append = backend.operations.index("append")
    first_flush = backend.operations.index("flush")
    first_unlock = backend.operations.index("unlock")
    assert first_lock < first_append < first_flush < first_unlock
    assert backend.contents == MARKER + b"\n"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("directory_owner", "custody_security_invalid"),
        ("file_owner", "custody_security_invalid"),
        ("directory_reparse", "custody_directory_invalid"),
        ("file_reparse", "custody_file_invalid"),
        ("file_hardlink", "custody_file_invalid"),
        ("remote_volume", "custody_volume_invalid"),
    ],
)
def test_publish_initialized_file_rejects_unsafe_custody_without_canonical(
    tmp_path: Path, mutation: str, expected_code: str
) -> None:
    backend = FakePublishBackend(tmp_path)
    if mutation == "directory_owner":
        backend.security["directory"] = (False, True, True)
    elif mutation == "file_owner":
        backend.security["file"] = (False, True, True)
    elif mutation == "directory_reparse":
        backend.directory = replace(backend.directory, reparse=True)
    elif mutation == "file_reparse":
        backend.file = replace(backend.file, reparse=True)
    elif mutation == "remote_volume":
        backend.fixed_volume = False
    else:
        backend.file = replace(backend.file, link_count=2)

    with pytest.raises(CustodyHold, match=expected_code):
        publish_new_initialized_file(
            tmp_path / "reservation.db",
            lambda stage: stage.write_bytes(b"complete"),
            backend=backend,
        )

    assert not (tmp_path / "reservation.db").exists()
    assert "publish_new" not in backend.operations


def test_publish_initialized_file_rejects_identity_drift_before_publish(
    tmp_path: Path,
) -> None:
    backend = FakePublishBackend(tmp_path)
    backend.drift_after = 2

    with pytest.raises(CustodyHold, match="custody_identity_changed"):
        publish_new_initialized_file(
            tmp_path / "reservation.db",
            lambda stage: stage.write_bytes(b"complete"),
            backend=backend,
        )

    assert not (tmp_path / "reservation.db").exists()
    assert "publish_new" not in backend.operations


def test_publish_initialized_file_rejects_staging_path_substitution(
    tmp_path: Path,
) -> None:
    backend = FakePublishBackend(tmp_path)
    backend.substituted_identity = replace(backend.file, file_id="substituted")

    with pytest.raises(CustodyHold, match="custody_identity_changed"):
        publish_new_initialized_file(
            tmp_path / "reservation.db",
            lambda stage: stage.write_bytes(b"substituted"),
            backend=backend,
        )

    assert not (tmp_path / "reservation.db").exists()
    assert "publish_new" not in backend.operations


def test_publish_initialized_file_failure_leaves_canonical_absent_and_retry_succeeds(
    tmp_path: Path,
) -> None:
    final = tmp_path / "reservation.db"
    first = FakePublishBackend(tmp_path)

    with pytest.raises(RuntimeError, match="schema failed"):
        publish_new_initialized_file(
            final,
            lambda _stage: (_ for _ in ()).throw(RuntimeError("schema failed")),
            backend=first,
        )

    assert not final.exists()
    assert "discard" in first.operations

    second = FakePublishBackend(tmp_path)
    publish_new_initialized_file(
        final,
        lambda stage: stage.write_bytes(b"complete"),
        backend=second,
    )
    assert final.read_bytes() == b"complete"


def test_publish_initialized_file_never_exposes_incomplete_canonical(
    tmp_path: Path,
) -> None:
    final = tmp_path / "reservation.db"
    backend = FakePublishBackend(tmp_path)
    observations: list[bool] = []

    def initialize(stage: Path) -> None:
        observations.append(final.exists())
        stage.write_bytes(b"partial")
        observations.append(final.exists())
        stage.write_bytes(b"complete")
        observations.append(final.exists())

    backend.before_publish = lambda path: observations.append(path.exists())
    publish_new_initialized_file(final, initialize, backend=backend)

    assert observations == [False, False, False, False]
    assert final.read_bytes() == b"complete"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows handle proof")
def test_windows_backend_atomically_publishes_initialized_file(tmp_path: Path) -> None:
    backend = WindowsMarkerBackend()
    root = tmp_path / "Project6" / "Reservation"
    directory = backend.open_directory(root)
    backend.close(directory)
    final = root / "reservation.db"
    observations: list[bool] = []

    def initialize(stage: Path) -> None:
        observations.append(final.exists())
        stage.write_bytes(b"complete")
        observations.append(final.exists())

    assert publish_new_initialized_file(final, initialize, backend=backend) == final
    assert observations == [False, False]
    assert final.read_bytes() == b"complete"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows handle proof")
def test_windows_backend_rejects_hardlinked_staging_file(tmp_path: Path) -> None:
    backend = WindowsMarkerBackend()
    root = tmp_path / "Project6" / "Reservation"
    directory = backend.open_directory(root)
    backend.close(directory)
    final = root / "reservation.db"

    def initialize(stage: Path) -> None:
        stage.write_bytes(b"complete")
        (root / "staging-link.tmp").hardlink_to(stage)

    with pytest.raises(CustodyHold, match="custody_identity_changed"):
        publish_new_initialized_file(final, initialize, backend=backend)
    assert not final.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows handle proof")
def test_windows_backend_claims_only_temp_marker(tmp_path: Path) -> None:
    path = tmp_path / "Project6" / "Authority" / "spent.jsonl"
    store = SpentMarkerStore(path, max_bytes=65536)

    assert store.claim_exact(MARKER) == "RECORDED"
    assert store.claim_exact(MARKER) == "EXISTS"
    assert path.read_bytes() == MARKER + b"\n"
