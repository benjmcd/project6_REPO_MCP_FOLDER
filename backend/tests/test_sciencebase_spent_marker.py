from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys

import pytest

from app.services.sciencebase_spent_marker import (
    MarkerIdentity,
    SpentMarkerHold,
    SpentMarkerStore,
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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows handle proof")
def test_windows_backend_claims_only_temp_marker(tmp_path: Path) -> None:
    path = tmp_path / "Project6" / "Authority" / "spent.jsonl"
    store = SpentMarkerStore(path, max_bytes=65536)

    assert store.claim_exact(MARKER) == "RECORDED"
    assert store.claim_exact(MARKER) == "EXISTS"
    assert path.read_bytes() == MARKER + b"\n"
