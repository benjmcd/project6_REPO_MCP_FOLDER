from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "tools" / "dual_live_recovery.py"
CAMPAIGN_ID = "123e4567-e89b-42d3-a456-426614174000"
FINGERPRINT = "a" * 64
OFFLINE_ENV = {"CONNECTOR_LIVE_EGRESS_ENABLED": "false"}


def _load_recovery() -> ModuleType:
    spec = importlib.util.spec_from_file_location("dual_live_recovery_probe", RECOVERY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _fixture(
    tmp_path: Path,
    *,
    poisoned: bool = True,
) -> tuple[Path, Path, Path, Path]:
    database = tmp_path / "campaign.db"
    storage = tmp_path / "storage"
    evidence = tmp_path / "evidence"
    archive = tmp_path / "archive"
    storage.mkdir()
    (storage / "payload.bin").write_bytes(b"preserve-storage\n")

    campaign_dir = evidence / "logs" / FINGERPRINT
    campaign_dir.mkdir(parents=True)
    (evidence / "log-seals").mkdir()
    (campaign_dir / "app.jsonl").write_bytes(b'{"partial":true}\n')
    marker_base = {
        "campaign_fingerprint": FINGERPRINT,
        "campaign_id": CAMPAIGN_ID,
        "reason_code": "phase_b_interrupted",
        "schema_id": "project6.dual_live_recovery_marker.v1",
    }
    if poisoned:
        (campaign_dir / "poison.json").write_bytes(
            _canonical({**marker_base, "marker_kind": "poison"})
        )
        (campaign_dir / "tombstone.json").write_bytes(
            _canonical({**marker_base, "marker_kind": "tombstone"})
        )

    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            CREATE TABLE l3_session (
                session_id TEXT PRIMARY KEY,
                client_request_id TEXT NOT NULL
            );
            CREATE TABLE l3_descriptor (
                descriptor_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES l3_session(session_id),
                source_binding_json TEXT NOT NULL
            );
            CREATE TABLE unrelated (value TEXT NOT NULL);
            """
        )
        connection.execute(
            "INSERT INTO l3_session VALUES (?, ?)",
            ("session-1", f"dual-live-{CAMPAIGN_ID}-nrc"),
        )
        connection.execute(
            "INSERT INTO l3_descriptor VALUES (?, ?, ?)",
            (
                "descriptor-orphan",
                "missing-session",
                json.dumps({"campaign_id": CAMPAIGN_ID}),
            ),
        )
        connection.execute("INSERT INTO unrelated VALUES ('leave-alone')")
        connection.commit()
    finally:
        connection.close()
    Path(f"{database}-journal").write_bytes(b"")
    return database, storage, evidence, archive


def _paths(database: Path, storage: Path, evidence: Path) -> dict[str, str]:
    return {
        "database_path": str(database.resolve()),
        "storage_root": str(storage.resolve()),
        "evidence_root": str(evidence.resolve()),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_operator_poison_cli_creates_canonical_marker_once(
    tmp_path: Path,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, _archive = _fixture(
        tmp_path,
        poisoned=False,
    )
    arguments = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_fingerprint": FINGERPRINT,
        **_paths(database, storage, evidence),
        "environ": OFFLINE_ENV,
    }

    child_environment = {
        name: value
        for name, value in os.environ.items()
        if name.upper()
        in {
            "COMSPEC",
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "WINDIR",
        }
    }
    child_environment["CONNECTOR_LIVE_EGRESS_ENABLED"] = "false"
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(RECOVERY),
            "poison",
            "--campaign-id",
            CAMPAIGN_ID,
            "--campaign-fingerprint",
            FINGERPRINT,
            "--database-path",
            arguments["database_path"],
            "--storage-root",
            arguments["storage_root"],
            "--evidence-root",
            arguments["evidence_root"],
            "--reason-code",
            "phase_b_interrupted",
        ],
        check=False,
        capture_output=True,
        env=child_environment,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    assert completed.stderr == b""
    result = json.loads(completed.stdout)
    assert completed.stdout == _canonical(result)

    marker = evidence / "logs" / FINGERPRINT / "poison.json"
    assert result["status"] == "POISONED_UNSEALED"
    assert result["marker_sha256"] == _sha256(marker)
    assert json.loads(marker.read_bytes()) == {
        "campaign_fingerprint": FINGERPRINT,
        "campaign_id": CAMPAIGN_ID,
        "marker_kind": "poison",
        "reason_code": "phase_b_interrupted",
        "schema_id": "project6.dual_live_recovery_marker.v1",
    }
    assert recovery.inspect_campaign(**arguments)["status"] == "POISONED_UNSEALED"
    with pytest.raises(recovery.RecoveryRefusal, match="poison_marker_exists"):
        recovery.poison_campaign(
            **arguments,
            reason_code="phase_b_interrupted",
        )

    long_reason_root = tmp_path / "long-reason"
    long_reason_root.mkdir()
    long_reason_db, long_reason_storage, long_reason_evidence, _ = _fixture(
        long_reason_root,
        poisoned=False,
    )
    with pytest.raises(recovery.RecoveryRefusal, match="poison_reason_invalid"):
        recovery.poison_campaign(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=FINGERPRINT,
            **_paths(long_reason_db, long_reason_storage, long_reason_evidence),
            environ=OFFLINE_ENV,
            reason_code="a" * 129,
        )


def test_inspect_then_archive_preserves_poisoned_campaign_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, archive = _fixture(tmp_path)
    originals = {
        path: _sha256(path)
        for root in (storage, evidence)
        for path in root.rglob("*")
        if path.is_file()
    }
    originals[database] = _sha256(database)
    originals[Path(f"{database}-journal")] = _sha256(Path(f"{database}-journal"))
    network_calls: list[str] = []

    def deny_network(*_args: object, **_kwargs: object) -> None:
        network_calls.append("attempted")
        raise AssertionError("network seam reached")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)

    inspected = recovery.inspect_campaign(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=FINGERPRINT,
        environ=OFFLINE_ENV,
        **_paths(database, storage, evidence),
    )
    assert inspected["status"] == "POISONED_UNSEALED"
    assert inspected["capture"]["manifest_present"] is False
    assert inspected["capture"]["seal_present"] is False
    assert inspected["capture"]["marker_kinds"] == ["poison", "tombstone"]
    assert inspected["database"]["integrity_check"] == "ok"
    assert [item["table"] for item in inspected["inventory"]["campaign_scoped"]] == [
        "l3_descriptor",
        "l3_session",
    ]
    assert inspected["inventory"]["orphans"] == [
        {
            "foreign_key_id": 0,
            "parent_table": "l3_session",
            "rowid": 1,
            "table": "l3_descriptor",
        }
    ]

    archived = recovery.archive_campaign(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=FINGERPRINT,
        archive_root=str(archive.resolve()),
        environ=OFFLINE_ENV,
        **_paths(database, storage, evidence),
    )
    archive_dir = Path(archived["archive_path"])
    manifest_path = archive_dir / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest_bytes == _canonical(manifest)
    assert archived["manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert manifest["classification"] == "POISONED_UNSEALED"
    assert manifest["inventory"] == inspected["inventory"]
    assert "nonempty_hot_rollback_journal_is_stop_unclassified" in manifest["nonclaims"]
    assert (
        "producer_quiescence_required_hashes_detect_drift_not_atomic_snapshot"
        in manifest["nonclaims"]
    )
    assert "database/raw/campaign.db-journal" in {
        item["archive_relative_path"] for item in manifest["files"]
    }
    assert [item["archive_relative_path"] for item in manifest["files"]] == sorted(
        item["archive_relative_path"] for item in manifest["files"]
    )
    for item in manifest["files"]:
        copied = archive_dir / item["archive_relative_path"]
        assert _sha256(copied) == item["sha256"]
        assert copied.stat().st_size == item["size"]
    assert {path: _sha256(path) for path in originals} == originals
    assert (evidence / "logs" / FINGERPRINT / "poison.json").is_file()
    assert (evidence / "logs" / FINGERPRINT / "tombstone.json").is_file()
    assert network_calls == []


@pytest.mark.parametrize(
    ("campaign_id", "fingerprint", "environ", "code"),
    [
        (CAMPAIGN_ID.upper(), FINGERPRINT, OFFLINE_ENV, "campaign_id_invalid"),
        (CAMPAIGN_ID, FINGERPRINT.upper(), OFFLINE_ENV, "fingerprint_invalid"),
        (
            CAMPAIGN_ID,
            FINGERPRINT,
            {"CONNECTOR_LIVE_EGRESS_ENABLED": "true"},
            "egress_enabled",
        ),
        (
            CAMPAIGN_ID,
            FINGERPRINT,
            {
                "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
                "CONNECTOR_NRC_APS_GRANT_PATH": "C:\\secret.json",
            },
            "credential_environment_present",
        ),
        (
            CAMPAIGN_ID,
            FINGERPRINT,
            {
                "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
                "GITHUB_TOKEN": "credential",
            },
            "credential_environment_present",
        ),
    ],
)
def test_inspect_refuses_invalid_identity_or_unsafe_environment(
    tmp_path: Path,
    campaign_id: str,
    fingerprint: str,
    environ: dict[str, str],
    code: str,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, _archive = _fixture(tmp_path)

    with pytest.raises(recovery.RecoveryRefusal, match=code):
        recovery.inspect_campaign(
            campaign_id=campaign_id,
            campaign_fingerprint=fingerprint,
            environ=environ,
            **_paths(database, storage, evidence),
        )


def test_inspect_fails_closed_when_layer3_state_is_empty(
    tmp_path: Path,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, _archive = _fixture(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("DELETE FROM l3_descriptor")
        connection.execute("DELETE FROM l3_session")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(recovery.RecoveryRefusal, match="state_unclassified"):
        recovery.inspect_campaign(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=FINGERPRINT,
            environ=OFFLINE_ENV,
            **_paths(database, storage, evidence),
        )


def test_inspect_refuses_uncheckpointed_wal_without_changing_sidecars(
    tmp_path: Path,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, _archive = _fixture(tmp_path)
    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)
        connection.execute(
            "INSERT INTO l3_session VALUES (?, ?)",
            ("session-wal", f"dual-live-{CAMPAIGN_ID}-sciencebase"),
        )
        connection.commit()
        sidecars_before = {
            path.name: _sha256(path)
            for suffix in ("-shm", "-wal")
            if (path := Path(f"{database}{suffix}")).is_file()
        }

        with pytest.raises(
            recovery.RecoveryRefusal,
            match="database_wal_uncheckpointed",
        ):
            recovery.inspect_campaign(
                campaign_id=CAMPAIGN_ID,
                campaign_fingerprint=FINGERPRINT,
                environ=OFFLINE_ENV,
                **_paths(database, storage, evidence),
            )
        assert {
            path.name: _sha256(path)
            for suffix in ("-shm", "-wal")
            if (path := Path(f"{database}{suffix}")).is_file()
        } == sidecars_before
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("suffix", "expected_code"),
    [
        ("-journal", "database_sidecar_requires_archive"),
        ("-shm", "database_sidecar_requires_archive"),
        ("-wal", "database_wal_uncheckpointed"),
    ],
)
def test_inspect_refuses_nonempty_sidecar_before_sqlite_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    expected_code: str,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, _archive = _fixture(tmp_path)
    sidecar = Path(f"{database}{suffix}")
    sidecar.write_bytes(f"preserve{suffix}".encode())
    before = _sha256(sidecar)

    def reject_open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("source sqlite was opened")

    monkeypatch.setattr(recovery.sqlite3, "connect", reject_open)
    with pytest.raises(
        recovery.RecoveryRefusal,
        match=expected_code,
    ):
        recovery.inspect_campaign(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=FINGERPRINT,
            environ=OFFLINE_ENV,
            **_paths(database, storage, evidence),
        )
    assert _sha256(sidecar) == before


def test_archive_preserves_raw_wal_then_inventories_only_an_analysis_clone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recovery = _load_recovery()
    database, storage, evidence, archive = _fixture(tmp_path)
    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)
        connection.execute(
            "INSERT INTO l3_session VALUES (?, ?)",
            ("session-wal", f"dual-live-{CAMPAIGN_ID}-sciencebase"),
        )
        connection.commit()
        source_family = {
            path: _sha256(path)
            for suffix in ("", "-journal", "-shm", "-wal")
            if (path := Path(f"{database}{suffix}")).is_file()
        }
        original_connect = recovery.sqlite3.connect
        opened_uris: list[str] = []

        def record_connect(
            database_uri: str, *args: object, **kwargs: object
        ) -> object:
            inspection_database = (
                archive / CAMPAIGN_ID / "database" / "inspect" / database.name
            )
            assert not Path(f"{inspection_database}-shm").exists()
            opened_uris.append(database_uri)
            return original_connect(database_uri, *args, **kwargs)

        monkeypatch.setattr(recovery.sqlite3, "connect", record_connect)
        archived = recovery.archive_campaign(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=FINGERPRINT,
            archive_root=str(archive.resolve()),
            environ=OFFLINE_ENV,
            **_paths(database, storage, evidence),
        )
        archive_dir = Path(archived["archive_path"])
        manifest = json.loads((archive_dir / "manifest.json").read_bytes())
        sessions = next(
            item
            for item in manifest["inventory"]["campaign_scoped"]
            if item["table"] == "l3_session"
        )
        assert sessions["matching_row_count"] == 2
        assert {path: _sha256(path) for path in source_family} == source_family
        for source, digest in source_family.items():
            assert _sha256(archive_dir / "database" / "raw" / source.name) == digest
        assert opened_uris
        assert all(database.as_uri() not in uri for uri in opened_uris)
        assert all("/database/inspect/" in uri for uri in opened_uris)
        assert any(item["scope"] == "derived_inspection" for item in manifest["files"])
    finally:
        connection.close()


def test_archive_never_overwrites_existing_campaign_archive(tmp_path: Path) -> None:
    recovery = _load_recovery()
    database, storage, evidence, archive = _fixture(tmp_path)
    archive.mkdir()
    occupied = archive / CAMPAIGN_ID
    occupied.mkdir()
    sentinel = occupied / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(recovery.RecoveryRefusal, match="archive_exists"):
        recovery.archive_campaign(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=FINGERPRINT,
            archive_root=str(archive.resolve()),
            environ=OFFLINE_ENV,
            **_paths(database, storage, evidence),
        )
    assert sentinel.read_text(encoding="utf-8") == "keep"
