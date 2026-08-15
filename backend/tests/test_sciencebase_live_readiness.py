from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import gc
import json
import multiprocessing
from pathlib import Path
import subprocess
import sqlite3
import sys
from types import SimpleNamespace

import pytest

from app.services.connector_egress_contract import PhysicalRequestPlan, RequestLimits
from app.services.connector_egress_transport import (
    ReservationFileIdentity,
    ReservationStore,
    ReservationVolumeIdentity,
)
from app.services.dual_live_sciencebase_producer import ScienceBaseInput, ScienceBaseOutput


RUN_ID = "11111111-1111-4111-8111-111111111111"
DIGESTS = {
    name: "sha256:" + character * 64
    for name, character in {
        "envelope": "a",
        "authorization": "b",
        "grant": "c",
        "manifest": "d",
    }.items()
}
_RATIFIED_SCIENCEBASE_HEADER = (
    "DataSource,Commodity,Year,USprod_Primary_kg,USprod_Secondary_kg,"
    "Imports_Metal_kg,Imports_GeO2_kg,Exports_kg,Shipments_Gov_kg,"
    "Consump_kg,Price_Metal_dkg,Price_GeO2_dkg,NIR_pct"
)
_VALID_SCIENCEBASE_ROW = (
    "MCS2023,Germanium,2022,0,W,14000,15000,5800,0,30000,1300,840,>50"
)
_VALID_ONE_ROW_CSV = (
    _RATIFIED_SCIENCEBASE_HEADER + "\n" + _VALID_SCIENCEBASE_ROW + "\n"
).encode("utf-8")
_CHARACTERIZED_SCIENCEBASE_CSV = (
    b"\xef\xbb\xbf"
    + (
        _RATIFIED_SCIENCEBASE_HEADER
        + "\r\n"
        + "MCS2023,Germanium,2018,0,W,10000,12000,3600,0,30000,1543,1084,>50\r\n"
        + "MCS2023,Germanium,2019,0,W,14000,21000,4500,0,30000,1236,913,>50\r\n"
        + "MCS2023,Germanium,2020,0,W,14000,12000,4800,0,30000,1046,724,>50\r\n"
        + "MCS2023,Germanium,2021,0,W,13000,17000,7500,0,30000,1187,770,>50\r\n"
        + _VALID_SCIENCEBASE_ROW
        + "\r\n"
    ).encode("utf-8")
)


class _IdentityProbe:
    def canonicalize(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def pin(self, _path: Path, *, directory: bool) -> None:
        assert isinstance(directory, bool)

    def volume(self, _path: Path) -> ReservationVolumeIdentity:
        return ReservationVolumeIdentity("volume:1", True, True)

    def identity(self, path: Path, *, directory: bool) -> ReservationFileIdentity:
        return ReservationFileIdentity(
            "volume:1", f"file:{path.name}", 1, False, directory
        )

    def close(self) -> None:
        pass


def _database(root: Path) -> Path:
    path = root / ReservationStore.DATABASE_BASENAME
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE connector_run (
                connector_run_id VARCHAR(36) PRIMARY KEY
            );
            CREATE TABLE connector_run_event (
                connector_run_event_id VARCHAR(36) PRIMARY KEY,
                connector_run_id VARCHAR(36) NOT NULL REFERENCES connector_run(connector_run_id),
                connector_run_target_id VARCHAR(36),
                phase VARCHAR(100),
                stage VARCHAR(100),
                event_type VARCHAR(100) NOT NULL,
                status_before VARCHAR(50),
                status_after VARCHAR(50),
                reason_code VARCHAR(255),
                error_class VARCHAR(100),
                message TEXT,
                metrics_json JSON,
                created_at DATETIME
            );
            INSERT INTO connector_run(connector_run_id)
            VALUES ('11111111-1111-4111-8111-111111111111');
            """
        )
    return path


def _store(root: Path) -> ReservationStore:
    return ReservationStore(root, root / "reservation.db", identity_probe=_IdentityProbe())


def _producer_request(root: Path) -> ScienceBaseInput:
    return ScienceBaseInput(
        query="public geology",
        expected_item_id="item-1",
        expected_file_name="map.json",
        envelope_digest=DIGESTS["envelope"],
        campaign_id="campaign-test",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        authorization_digest=DIGESTS["authorization"],
        grant_digest=DIGESTS["grant"],
        max_total_bytes=512 * 1024 * 1024,
        limits=RequestLimits(timeout_seconds=30),
    )


def _plan(root: Path, ordinal: int, stage: str) -> PhysicalRequestPlan:
    return PhysicalRequestPlan(
        envelope_digest=DIGESTS["envelope"],
        campaign_id="campaign-test",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        target_id=stage,
        request_ordinal=ordinal,
        stage=stage,
        method="GET",
        canonical_destination=f"https://www.sciencebase.gov/catalog/{stage}",
        header_names=(),
        header_value_sha256s=(),
        body_sha256="sha256:" + hashlib.sha256(b"").hexdigest(),
        limits=RequestLimits(timeout_seconds=30),
        authorization_digest=DIGESTS["authorization"],
        grant_digest=DIGESTS["grant"],
    )


def _prepared(root: Path, store: ReservationStore):
    source_root = root.parent / f"{root.name}-source"
    source_root.mkdir(exist_ok=True)
    envelope = SimpleNamespace(
        content_digest=DIGESTS["envelope"],
        campaign_id="campaign-test",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        source_commit="1" * 40,
        interpreter_identity="sha256:" + "2" * 64,
        authorization_digest=DIGESTS["authorization"],
        grant_digest=DIGESTS["grant"],
        wrapper_start_token_ref="retired:sciencebase-live-v2",
    )
    return SimpleNamespace(
        envelope=SimpleNamespace(envelope=envelope),
        reservation_store=store,
        producer_request=_producer_request(root),
        worker_manifest_digest=DIGESTS["manifest"],
        source_root=source_root.resolve(),
    )


def _go_document(module, prepared) -> dict[str, object]:
    envelope = prepared.envelope.envelope
    return {
        "schema": module.LIVE_GO_SCHEMA,
        "go_id": "22222222-2222-4222-8222-222222222222",
        "envelope_digest": envelope.content_digest,
        "campaign_id": envelope.campaign_id,
        "canonical_root": envelope.canonical_root,
        "connector_run_id": envelope.connector_run_id,
        "source_commit": envelope.source_commit,
        "interpreter_identity": envelope.interpreter_identity,
        "worker_manifest_digest": prepared.worker_manifest_digest,
        "request_digest": module.sciencebase_request_digest(prepared.producer_request),
        "authorization_digest": envelope.authorization_digest,
        "grant_digest": envelope.grant_digest,
        "wrapper_start_token_ref": envelope.wrapper_start_token_ref,
        "credential_mode": "none_public",
        "egress_mode": "capability_scoped_default_off",
    }


def _canonical(document: dict[str, object]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def _load_module():
    from app.services import sciencebase_live_readiness

    return sciencebase_live_readiness


def _owner_authenticator():
    return SimpleNamespace(authenticate_exact=lambda _raw, _digest: True)


def _initialize_reservation_database_child(root: str, queue) -> None:
    module = _load_module()
    try:
        module.initialize_reservation_database(Path(root), RUN_ID)
        queue.put("INITIALIZED")
    except module.LiveReadinessHold as exc:
        queue.put(exc.code)


@pytest.fixture(autouse=True)
def _isolated_spent_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "LIVE_GO_SPENT_MARKER",
        tmp_path / "authority" / "spent.jsonl",
        raising=False,
    )


def test_initialize_reservation_database_create_once_and_store_opens_rw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = tmp_path.resolve()

    def publish(final: Path, initialize) -> Path:
        if final.exists():
            raise module.CustodyHold("custody_exists")
        stage = final.with_name(".reservation.db.test.tmp")
        stage.touch(exist_ok=False)
        try:
            initialize(stage)
            assert not final.exists()
            stage.rename(final)
            return final
        except BaseException:
            stage.unlink(missing_ok=True)
            raise

    monkeypatch.setattr(module, "publish_new_initialized_file", publish)

    database = module.initialize_reservation_database(root, RUN_ID)

    assert database == root / "reservation.db"
    store = _store(root)
    try:
        assert store.assert_no_reservations(RUN_ID) is None
    finally:
        store.close()
    with pytest.raises(module.LiveReadinessHold, match="reservation_database_exists"):
        module.initialize_reservation_database(root, RUN_ID)


def test_initialize_reservation_database_schema_failure_does_not_poison_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    root = tmp_path.resolve()
    final = root / "reservation.db"

    def publish(path: Path, initialize) -> Path:
        stage = path.with_name(".reservation.db.test.tmp")
        stage.touch(exist_ok=False)
        try:
            initialize(stage)
            stage.rename(path)
            return path
        except BaseException:
            stage.unlink(missing_ok=True)
            raise

    monkeypatch.setattr(module, "publish_new_initialized_file", publish)

    def fail_after_creation(*_args, **_kwargs):
        raise sqlite3.DatabaseError("schema failed")

    with pytest.raises(
        module.LiveReadinessHold, match="reservation_database_initialize_failed"
    ):
        module.initialize_reservation_database(root, RUN_ID, sqlite_connect=fail_after_creation)

    assert not final.exists()
    assert not list(root.glob(".reservation.db.*.tmp"))

    assert module.initialize_reservation_database(root, RUN_ID) == final
    with sqlite3.connect(final) as connection:
        assert connection.execute(
            "SELECT connector_run_id FROM connector_run"
        ).fetchone() == (RUN_ID,)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows custody proof")
def test_windows_initializer_publishes_complete_database_with_native_custody(
    tmp_path: Path,
) -> None:
    module = _load_module()
    from app.services.sciencebase_spent_marker import WindowsMarkerBackend

    backend = WindowsMarkerBackend()
    root = tmp_path / "Project6" / "Reservation"
    directory = backend.open_directory(root)
    backend.close(directory)

    assert module.initialize_reservation_database(root, RUN_ID) == root / "reservation.db"
    with sqlite3.connect((root / "reservation.db").as_uri() + "?mode=rw", uri=True) as connection:
        assert connection.execute(
            "SELECT connector_run_id FROM connector_run"
        ).fetchone() == (RUN_ID,)
        assert connection.execute("SELECT COUNT(*) FROM connector_run_event").fetchone() == (0,)
    native_store = ReservationStore(root)
    try:
        assert native_store.assert_no_reservations(RUN_ID) is None
    finally:
        native_store.close()
    assert not list(root.glob(".reservation.db.*.tmp"))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows custody proof")
def test_windows_initializer_schema_failure_leaves_no_canonical_and_retries(
    tmp_path: Path,
) -> None:
    module = _load_module()
    from app.services.sciencebase_spent_marker import WindowsMarkerBackend

    backend = WindowsMarkerBackend()
    root = tmp_path / "Project6" / "Reservation"
    directory = backend.open_directory(root)
    backend.close(directory)

    class FailingConnection:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = sqlite3.connect(*args, **kwargs)

        def execute(self, *args, **kwargs):
            return self.connection.execute(*args, **kwargs)

        def executescript(self, _script: str) -> None:
            self.connection.executescript(
                "BEGIN IMMEDIATE; CREATE TABLE partial_schema(value INTEGER);"
            )
            raise sqlite3.DatabaseError("injected schema failure")

        def close(self) -> None:
            self.connection.close()

    with pytest.raises(
        module.LiveReadinessHold, match="reservation_database_initialize_failed"
    ):
        module.initialize_reservation_database(root, RUN_ID, sqlite_connect=FailingConnection)
    assert not (root / "reservation.db").exists()
    assert not list(root.glob(".reservation.db.*.tmp"))

    assert module.initialize_reservation_database(root, RUN_ID) == root / "reservation.db"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows custody proof")
def test_windows_initializer_concurrent_publish_has_exactly_one_winner(
    tmp_path: Path,
) -> None:
    module = _load_module()
    from app.services.sciencebase_spent_marker import WindowsMarkerBackend

    backend = WindowsMarkerBackend()
    root = tmp_path / "Project6" / "Reservation"
    directory = backend.open_directory(root)
    backend.close(directory)

    def initialize() -> str:
        try:
            module.initialize_reservation_database(root, RUN_ID)
            return "INITIALIZED"
        except module.LiveReadinessHold as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _index: initialize(), range(8)))

    assert outcomes.count("INITIALIZED") == 1
    assert outcomes.count("reservation_database_exists") == 7
    with sqlite3.connect(root / "reservation.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM connector_run").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM connector_run_event").fetchone() == (0,)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows custody proof")
def test_windows_initializer_multiprocess_publish_has_exactly_one_winner(
    tmp_path: Path,
) -> None:
    from app.services.sciencebase_spent_marker import WindowsMarkerBackend

    backend = WindowsMarkerBackend()
    root = tmp_path / "Project6" / "Reservation"
    directory = backend.open_directory(root)
    backend.close(directory)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [
        context.Process(
            target=_initialize_reservation_database_child,
            args=(str(root), queue),
        )
        for _ in range(4)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=30)
        assert process.exitcode == 0
    outcomes = [queue.get(timeout=5) for _ in processes]

    assert outcomes.count("INITIALIZED") == 1
    assert outcomes.count("reservation_database_exists") == 3
    with sqlite3.connect(root / "reservation.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM connector_run").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM connector_run_event").fetchone() == (0,)


def test_write_owner_go_template_derives_canonical_bindings_create_once(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path.resolve())
    prepared = _prepared(tmp_path.resolve(), store)
    owner_root = tmp_path.parent / f"{tmp_path.name}-owner"
    owner_root.mkdir()
    path = owner_root / "owner-go.json"
    go_id = "22222222-2222-4222-8222-222222222222"

    try:
        result = module.write_owner_go_template(prepared, path=path, go_id=go_id)
        raw = path.read_bytes()
        expected = _canonical(_go_document(module, prepared))

        assert raw == expected
        assert result.path == path
        assert result.go_id == go_id
        assert result.content_digest == "sha256:" + hashlib.sha256(raw).hexdigest()
        with sqlite3.connect(tmp_path / "reservation.db") as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM connector_run_event"
            ).fetchone() == (0,)
        with pytest.raises(module.LiveReadinessHold, match="live_go_template_exists"):
            module.write_owner_go_template(prepared, path=path, go_id=go_id)
    finally:
        store.close()


def test_write_owner_go_template_rejects_canonical_root_custody(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path.resolve())
    prepared = _prepared(tmp_path.resolve(), store)

    try:
        with pytest.raises(
            module.LiveReadinessHold,
            match="live_go_template_inside_canonical_root",
        ):
            module.write_owner_go_template(
                prepared,
                path=tmp_path / "owner-go.json",
                go_id="22222222-2222-4222-8222-222222222222",
            )
        assert not (tmp_path / "owner-go.json").exists()
    finally:
        store.close()


def test_write_owner_go_template_rejects_source_root_custody(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path.resolve())
    prepared = _prepared(tmp_path.resolve(), store)
    path = prepared.source_root / "owner-go.json"

    try:
        with pytest.raises(
            module.LiveReadinessHold,
            match="live_go_template_inside_source_root",
        ):
            module.write_owner_go_template(
                prepared,
                path=path,
                go_id="22222222-2222-4222-8222-222222222222",
            )
        assert not path.exists()
    finally:
        store.close()


def _signature_bytes() -> bytes:
    return (
        b"-----BEGIN SSH SIGNATURE-----\n"
        b"U1NIU0lHAAAAAQAAADMAAAALc3NoLWVkMjU1MTkAAAAgdGVzdC1vbmx5\n"
        b"-----END SSH SIGNATURE-----\n"
    )


def test_openssh_owner_authenticator_pins_exact_identity_and_verifies_exact_bytes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    signature_path = tmp_path / "owner-go.json.sig"
    signature_path.write_bytes(_signature_bytes())
    raw = b'{"exact":"canonical-go-bytes"}'
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    observed: dict[str, object] = {}

    def runner(command, **kwargs):
        observed["command"] = command
        observed["input"] = kwargs["input"]
        observed["allowed_signers"] = Path(command[4]).read_text(encoding="ascii")
        observed["signature"] = Path(command[10]).read_bytes()
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(module.OWNER_GO_VERIFY_SUCCESS + "\n").encode("ascii"),
            stderr=b"",
        )

    authenticator = module.OpenSshOwnerGoAuthenticator(
        signature_path, process_runner=runner
    )

    assert authenticator.authenticate_exact(raw, digest) is True
    assert module.OWNER_GO_PUBLIC_KEY == (
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPDrs7xXzQ1c5a+1KJZYlvKHnpqrjb3NQPiKUFd4E0ZQ "
        "project6-sciencebase-owner-go-v1"
    )
    assert module.OWNER_GO_PUBLIC_KEY_FINGERPRINT == (
        "SHA256:wD25Cry/4ZcGWBZXolmIOUNEF96p/yMxQ+y0dZeFZVU"
    )
    assert observed["input"] == raw
    assert observed["signature"] == _signature_bytes()
    assert observed["allowed_signers"] == (
        "project6-sciencebase-owner-go-v1 "
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPDrs7xXzQ1c5a+1KJZYlvKHnpqrjb3NQPiKUFd4E0ZQ\n"
    )
    command = observed["command"]
    assert command[:4] == [
        r"C:\Windows\System32\OpenSSH\ssh-keygen.exe",
        "-Y",
        "verify",
        "-f",
    ]
    assert command[5:10] == [
        "-I",
        "project6-sciencebase-owner-go-v1",
        "-n",
        "project6-sciencebase-live-go-v1",
        "-s",
    ]
    assert observed["kwargs"]["shell"] is False
    assert observed["kwargs"]["timeout"] == 15
    assert observed["kwargs"]["cwd"] == r"C:\Windows\System32\OpenSSH"
    assert observed["kwargs"]["env"] == {
        "SystemRoot": r"C:\Windows",
        "WINDIR": r"C:\Windows",
    }


@pytest.mark.parametrize(
    ("signature", "result", "raises"),
    [
        (b"not-an-openssh-signature", None, False),
        (_signature_bytes(), None, True),
        (_signature_bytes(), (1, b"", b"Signature verification failed"), False),
        (_signature_bytes(), (0, b"Good but ambiguous\n", b""), False),
        (_signature_bytes(), (0, b"", b""), False),
        (
            _signature_bytes(),
            (0, b"Good but ambiguous\n", b"also output\n"),
            False,
        ),
    ],
)
def test_openssh_owner_authenticator_fails_closed_without_leaking_tool_output(
    tmp_path: Path,
    signature: bytes,
    result: tuple[int, bytes, bytes] | None,
    raises: bool,
) -> None:
    module = _load_module()
    path = tmp_path / "owner-go.json.sig"
    path.write_bytes(signature)

    def runner(command, **_kwargs):
        if raises:
            raise OSError("C:/sentinel-secret")
        return subprocess.CompletedProcess(command, *result)

    authenticator = module.OpenSshOwnerGoAuthenticator(path, process_runner=runner)
    raw = b"exact-canonical-go"
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert authenticator.authenticate_exact(raw, digest) is False


def test_openssh_owner_authenticator_rejects_missing_or_oversized_signature(
    tmp_path: Path,
) -> None:
    module = _load_module()
    called = False

    def runner(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("invalid signature reached OpenSSH")

    missing = module.OpenSshOwnerGoAuthenticator(
        tmp_path / "missing.sig", process_runner=runner
    )
    digest = "sha256:" + hashlib.sha256(b"go").hexdigest()
    assert missing.authenticate_exact(b"go", digest) is False
    oversized_path = tmp_path / "oversized.sig"
    oversized_path.write_bytes(b"x" * (module.MAX_OWNER_GO_SIGNATURE_BYTES + 1))
    oversized = module.OpenSshOwnerGoAuthenticator(
        oversized_path, process_runner=runner
    )
    assert oversized.authenticate_exact(b"go", digest) is False
    assert called is False


def test_openssh_owner_authenticator_rejects_changed_go_bytes_before_tool(
    tmp_path: Path,
) -> None:
    module = _load_module()
    path = tmp_path / "owner-go.json.sig"
    path.write_bytes(_signature_bytes())
    called = False

    def runner(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("changed bytes reached OpenSSH")

    authenticator = module.OpenSshOwnerGoAuthenticator(path, process_runner=runner)
    original_digest = "sha256:" + hashlib.sha256(b"original").hexdigest()
    assert authenticator.authenticate_exact(b"changed", original_digest) is False
    assert called is False


def test_go_requires_exact_external_owner_authentication(tmp_path: Path) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    path = tmp_path / "owner-go.json"
    path.write_bytes(raw)
    observed: list[tuple[bytes, str]] = []
    authenticator = SimpleNamespace(
        authenticate_exact=lambda actual, actual_digest: (
            observed.append((actual, actual_digest)) or True
        )
    )

    module.load_live_go_once(
        path, digest, prepared, owner_authenticator=authenticator
    )
    assert observed == [(raw, digest)]

    def fail_authentication(_raw, _digest):
        raise RuntimeError("owner-key-secret")

    for rejected in (
        None,
        SimpleNamespace(authenticate_exact=lambda _raw, _digest: False),
        SimpleNamespace(authenticate_exact=lambda _raw, _digest: 1),
        SimpleNamespace(authenticate_exact=fail_authentication),
    ):
        with pytest.raises(
            module.LiveReadinessHold,
            match="live_go_owner_authentication_required",
        ) as caught:
            module.load_live_go_once(
                path, digest, prepared, owner_authenticator=rejected
            )
        assert caught.value.__cause__ is None
    store.close()


def test_exact_go_is_credentialless_content_addressed_and_consumed_once(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    document = _go_document(module, prepared)
    raw = _canonical(document)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)

    authority = module.load_live_go_once(
        go_path, digest, prepared, owner_authenticator=_owner_authenticator()
    )
    consumer = module.OneUseLiveGoConsumer(store, authority)

    assert authority.credential_mode == "none_public"
    assert authority.egress_mode == "capability_scoped_default_off"
    assert consumer.consume_exact(DIGESTS["envelope"]) is True
    assert consumer.consume_exact(DIGESTS["envelope"]) is False
    assert consumer.last_code == "live_go_already_spent"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        rows = connection.execute(
            "SELECT event_type, status_after, metrics_json FROM connector_run_event"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0:2] == ("sciencebase_live_go_consumed", "consumed")
    assert "public geology" not in rows[0][2]
    store.close()


def test_spent_marker_prevents_rearm_after_consumption_row_deleted(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    document = _go_document(module, prepared)
    raw = _canonical(document)
    path = tmp_path / "owner-go.json"
    path.write_bytes(raw)
    authority = module.load_live_go_once(
        path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )

    assert module.OneUseLiveGoConsumer(store, authority).consume_exact(
        DIGESTS["envelope"]
    ) is True
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        connection.execute(
            "DELETE FROM connector_run_event WHERE event_type = 'sciencebase_live_go_consumed'"
        )
    replay = module.OneUseLiveGoConsumer(store, authority)
    assert replay.consume_exact(DIGESTS["envelope"]) is False
    assert replay.last_code == "live_go_already_spent"
    assert (tmp_path / "authority" / "spent.jsonl").read_bytes().endswith(b"\n")
    store.close()


def test_eight_thread_go_consumption_commits_once_and_spends_seven(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    document = _go_document(module, prepared)
    raw = _canonical(document)
    path = tmp_path / "owner-go.json"
    path.write_bytes(raw)
    authority = module.load_live_go_once(
        path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    consumers = [module.OneUseLiveGoConsumer(store, authority) for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda consumer: consumer.consume_exact(DIGESTS["envelope"]),
                consumers,
            )
        )

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert [consumer.last_code for consumer in consumers].count(
        "live_go_already_spent"
    ) == 7
    store.close()


def test_missing_reservation_database_holds_without_rearming_spent_go(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    document = _go_document(module, prepared)
    raw = _canonical(document)
    path = tmp_path / "owner-go.json"
    path.write_bytes(raw)
    authority = module.load_live_go_once(
        path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    assert module.OneUseLiveGoConsumer(store, authority).consume_exact(
        DIGESTS["envelope"]
    ) is True
    store.close()
    gc.collect()
    (tmp_path / "reservation.db").rename(tmp_path / "reservation.db.bak")

    replay = module.OneUseLiveGoConsumer(store, authority)
    assert replay.consume_exact(DIGESTS["envelope"]) is False
    assert replay.last_code == "reservation_store_unavailable"


def test_different_go_for_same_connector_run_cannot_rearm_after_consumption(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    first_document = _go_document(module, prepared)
    first_raw = _canonical(first_document)
    first_path = tmp_path / "owner-go-1.json"
    first_path.write_bytes(first_raw)
    first = module.load_live_go_once(
        first_path,
        "sha256:" + hashlib.sha256(first_raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    assert module.OneUseLiveGoConsumer(store, first).consume_exact(
        DIGESTS["envelope"]
    ) is True

    second_document = dict(first_document)
    second_document["go_id"] = "33333333-3333-4333-8333-333333333333"
    second_raw = _canonical(second_document)
    second_path = tmp_path / "owner-go-2.json"
    second_path.write_bytes(second_raw)
    second = module.load_live_go_once(
        second_path,
        "sha256:" + hashlib.sha256(second_raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    consumer = module.OneUseLiveGoConsumer(store, second)

    assert consumer.consume_exact(DIGESTS["envelope"]) is False
    assert consumer.last_code == "live_go_already_spent"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event WHERE event_type = 'sciencebase_live_go_consumed'"
        ).fetchone()[0] == 1
    store.close()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("credential_mode", "environment", "live_go_binding_mismatch"),
        ("egress_mode", "ambient", "live_go_binding_mismatch"),
        ("request_digest", "sha256:" + "9" * 64, "live_go_binding_mismatch"),
        ("worker_manifest_digest", "sha256:" + "8" * 64, "live_go_binding_mismatch"),
    ],
)
def test_go_drift_holds_before_consumption(
    tmp_path: Path, field: str, value: str, code: str
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    document = _go_document(module, prepared)
    document[field] = value
    raw = _canonical(document)
    path = tmp_path / "owner-go.json"
    path.write_bytes(raw)

    with pytest.raises(module.LiveReadinessHold, match=code):
        module.load_live_go_once(
            path,
            "sha256:" + hashlib.sha256(raw).hexdigest(),
            prepared,
            owner_authenticator=_owner_authenticator(),
        )
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM connector_run_event").fetchone()[0] == 0
    store.close()


def test_execution_maps_invalid_go_to_secret_free_hold_and_closes_store(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(b"not-json")

    result = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest="sha256:" + hashlib.sha256(b"not-json").hexdigest(),
        run=lambda *_args, **_kwargs: pytest.fail("invalid GO reached execution"),
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )

    assert result.status == "HOLD"
    assert result.code == "live_go_invalid"
    assert result.artifact_path is None


def test_success_records_artifact_and_terminal_only_after_containment(tmp_path: Path) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    events: list[str] = []

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        events.append("go_consumed")
        _prepared.reservation_store.close()
        events.append("contained")
        content = _VALID_ONE_ROW_CSV
        return ScienceBaseOutput(
            "item-1",
            "map.json",
            content,
            hashlib.sha256(content).hexdigest(),
            3,
            len(content),
        )

    result = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )

    assert result.status == "TERMINAL"
    assert result.code == "sciencebase_acquisition_succeeded"
    assert result.artifact_path.read_bytes() == _VALID_ONE_ROW_CSV
    assert result.artifact_path.name == (
        f"sciencebase-{go_digest[7:]}-"
        f"{hashlib.sha256(result.artifact_path.read_bytes()).hexdigest()}.bin"
    )
    assert events == ["go_consumed", "contained"]
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        rows = connection.execute(
            "SELECT event_type, status_after, metrics_json FROM connector_run_event ORDER BY created_at"
        ).fetchall()
    assert [row[0] for row in rows] == [
        "sciencebase_live_go_consumed",
        "sciencebase_acquisition_terminal",
    ]
    terminal = json.loads(rows[-1][2])
    assert terminal["containment_status"] == "contained"
    assert terminal["boundary_assurance"] == "owner_waived_unproven"
    assert terminal["credential_mode"] == "none_public"
    assert terminal["artifact_sha256"] == hashlib.sha256(result.artifact_path.read_bytes()).hexdigest()


def test_write_artifact_rejects_html_error_page_before_write(tmp_path: Path) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    authority = module.load_live_go_once(
        go_path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    content = b"<!DOCTYPE html><html>502 Bad Gateway</html>"
    output = ScienceBaseOutput(
        "item-1", "map.json", content, hashlib.sha256(content).hexdigest(), 3, len(content)
    )

    with pytest.raises(
        module.LiveReadinessHold, match="sciencebase_artifact_content_rejected"
    ):
        module._write_artifact(store, authority, output, prepared.producer_request)

    assert list(tmp_path.glob("sciencebase-*.bin")) == []
    store.close()


@pytest.mark.parametrize(
    ("bom", "encoding"),
    [
        pytest.param(b"\xef\xbb\xbf", "utf-8", id="utf8"),
        pytest.param(b"\xff\xfe", "utf-16-le", id="utf16le"),
        pytest.param(b"\xfe\xff", "utf-16-be", id="utf16be"),
        pytest.param(b"\xff\xfe\x00\x00", "utf-32-le", id="utf32le"),
        pytest.param(b"\x00\x00\xfe\xff", "utf-32-be", id="utf32be"),
    ],
)
def test_write_artifact_rejects_bom_encoded_html_before_write(
    tmp_path: Path, bom: bytes, encoding: str
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    authority = module.load_live_go_once(
        go_path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    content = bom + "<!DOCTYPE html><html>502 Bad Gateway</html>".encode(encoding)
    output = ScienceBaseOutput(
        "item-1", "map.json", content, hashlib.sha256(content).hexdigest(), 3, len(content)
    )

    with pytest.raises(
        module.LiveReadinessHold, match="sciencebase_artifact_content_rejected"
    ):
        module._write_artifact(store, authority, output, prepared.producer_request)

    assert list(tmp_path.glob("sciencebase-*.bin")) == []
    store.close()


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b" \t\r\n", id="whitespace"),
        pytest.param(b"\xef\xbb\xbf", id="utf8-bom-only"),
        pytest.param(b'{"error":"unavailable"}', id="json-object"),
        pytest.param(b'["unavailable"]', id="json-array"),
        pytest.param(
            b"\xff\xfe" + '{"error":"unavailable"}'.encode("utf-16-le"),
            id="utf16le-json",
        ),
        pytest.param(
            b"\x00\x00\xfe\xff" + '["unavailable"]'.encode("utf-32-be"),
            id="utf32be-json",
        ),
    ],
)
def test_write_artifact_rejects_empty_whitespace_and_json_before_write(
    tmp_path: Path, content: bytes
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    authority = module.load_live_go_once(
        go_path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    output = ScienceBaseOutput(
        "item-1",
        "map.json",
        content,
        hashlib.sha256(content).hexdigest(),
        3,
        len(content),
    )

    with pytest.raises(
        module.LiveReadinessHold, match="sciencebase_artifact_content_rejected"
    ):
        module._write_artifact(store, authority, output, prepared.producer_request)

    assert list(tmp_path.glob("sciencebase-*.bin")) == []
    store.close()


def test_failure_after_go_consumption_records_hold_without_retry(tmp_path: Path) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)

    def fail(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        _prepared.reservation_store.close()
        raise RuntimeError("sentinel-secret")

    result = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        run=fail,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )

    assert result.status == "HOLD"
    assert result.code == "sciencebase_execution_failed"
    assert result.artifact_path is None
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        rows = connection.execute("SELECT event_type, metrics_json FROM connector_run_event").fetchall()
    assert [row[0] for row in rows] == [
        "sciencebase_live_go_consumed",
        "sciencebase_acquisition_terminal",
    ]
    assert json.loads(rows[-1][1])["boundary_assurance"] == "owner_waived_unproven"
    assert "sentinel-secret" not in json.dumps(rows)


def test_post_containment_artifact_failure_still_records_terminal_hold(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    content = _VALID_ONE_ROW_CSV
    content_digest = hashlib.sha256(content).hexdigest()
    conflict = tmp_path / f"sciencebase-{go_digest[7:]}-{content_digest}.bin"
    conflict.write_bytes(b"foreign")

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1", "map.json", content, content_digest, 3, len(content)
        )

    result = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )

    assert result.status == "HOLD"
    assert result.code == "sciencebase_artifact_write_failed"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        terminal = connection.execute(
            "SELECT status_after, reason_code, metrics_json FROM connector_run_event "
            "WHERE event_type = 'sciencebase_acquisition_terminal'"
        ).fetchone()
    assert terminal[0:2] == ("hold", "sciencebase_artifact_write_failed")
    terminal_metrics = json.loads(terminal[2])
    assert terminal_metrics["containment_status"] == "contained"
    assert terminal_metrics["boundary_assurance"] == "owner_waived_unproven"


def test_post_containment_invalid_output_still_records_terminal_hold(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        _prepared.reservation_store.close()
        return object()

    result = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )

    assert result.status == "HOLD"
    assert result.code == "sciencebase_output_invalid"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        terminal = connection.execute(
            "SELECT status_after, reason_code FROM connector_run_event "
            "WHERE event_type = 'sciencebase_acquisition_terminal'"
        ).fetchone()
    assert terminal == ("hold", "sciencebase_output_invalid")


def test_utf16_csv_artifact_writes_and_independent_closeout_verifies_exact_three_reservations(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    csv_content = b"\xff\xfe" + (
        _RATIFIED_SCIENCEBASE_HEADER + "\n" + _VALID_SCIENCEBASE_ROW + "\n"
    ).encode("utf-16-le")

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1",
            "map.json",
            csv_content,
            hashlib.sha256(csv_content).hexdigest(),
            3,
            len(csv_content),
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    result = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )

    assert executed.status == "TERMINAL"
    assert executed.artifact_path.read_bytes() == csv_content
    assert result.status == "VERIFIED"
    assert result.code == "sciencebase_closeout_verified"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        closeout_row = connection.execute(
            "SELECT metrics_json FROM connector_run_event "
            "WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()
    assert closeout_row is not None
    assert json.loads(closeout_row[0])["boundary_assurance"] == "owner_waived_unproven"


def test_plain_utf8_no_bom_csv_writes_and_verifies(tmp_path: Path) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    csv_content = _VALID_ONE_ROW_CSV

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1",
            "map.json",
            csv_content,
            hashlib.sha256(csv_content).hexdigest(),
            3,
            len(csv_content),
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    result = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )

    assert executed.status == "TERMINAL"
    assert executed.artifact_path.read_bytes() == csv_content
    assert result.status == "VERIFIED"
    assert result.code == "sciencebase_closeout_verified"


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [
        pytest.param(b"", "sciencebase_closeout_evidence_malformed", id="empty"),
        pytest.param(
            b" \t\r\n", "sciencebase_artifact_content_rejected", id="whitespace"
        ),
        pytest.param(
            b'{"error":"unavailable"}',
            "sciencebase_artifact_content_rejected",
            id="json-object",
        ),
        pytest.param(
            b"\xff\xfe" + '["unavailable"]'.encode("utf-16-le"),
            "sciencebase_artifact_content_rejected",
            id="utf16le-json",
        ),
    ],
)
def test_closeout_rejects_empty_whitespace_and_json_without_verified_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
    expected_code: str,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()

    def bypass_write_gate(store, authority, output, _expected_request):
        digest = hashlib.sha256(output.content).hexdigest()
        path = Path(store.canonical_root) / (
            f"sciencebase-{authority.content_digest[7:]}-{digest}.bin"
        )
        path.write_bytes(output.content)
        return path

    monkeypatch.setattr(module, "_write_artifact", bypass_write_gate)

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1",
            "map.json",
            content,
            hashlib.sha256(content).hexdigest(),
            3,
            len(content),
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    result = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )

    assert executed.status == "TERMINAL"
    assert result.status == "HOLD"
    assert result.code == expected_code
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event "
            "WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()[0] == 0


def test_closeout_rejects_zero_artifact_bytes_even_when_content_predicates_bypassed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(module, "_artifact_content_rejected", lambda _content: False)
    monkeypatch.setattr(
        module, "_artifact_positive_contract_rejected", lambda _content: False
    )

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1", "map.json", b"", hashlib.sha256(b"").hexdigest(), 3, 0
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    result = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )

    assert executed.status == "TERMINAL"
    assert result.status == "HOLD"
    assert result.code == "sciencebase_closeout_evidence_malformed"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event "
            "WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()[0] == 0


def test_closeout_rejects_self_consistent_utf16le_html_without_verified_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    content = b"\xff\xfe" + "  <!DOCTYPE html><html>502 Bad Gateway</html>".encode(
        "utf-16-le"
    )

    def bypass_write_gate(store, authority, output, _expected_request):
        digest = hashlib.sha256(output.content).hexdigest()
        path = Path(store.canonical_root) / (
            f"sciencebase-{authority.content_digest[7:]}-{digest}.bin"
        )
        path.write_bytes(output.content)
        return path

    monkeypatch.setattr(module, "_write_artifact", bypass_write_gate)

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1", "map.json", content, hashlib.sha256(content).hexdigest(), 3, len(content)
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    result = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )

    assert executed.status == "TERMINAL"
    assert result.status == "HOLD"
    assert result.code == "sciencebase_artifact_content_rejected"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()[0] == 0


def test_closeout_holds_on_artifact_or_reservation_drift(tmp_path: Path) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        content = _VALID_ONE_ROW_CSV
        return ScienceBaseOutput(
            "item-1",
            "map.json",
            content,
            hashlib.sha256(content).hexdigest(),
            3,
            len(content),
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    executed.artifact_path.write_bytes(b"tampered")

    result = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )

    assert result.status == "HOLD"
    assert result.code == "sciencebase_artifact_verification_failed"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()[0] == 0


_PHASE_2_REJECTED_CSVS = [
    pytest.param(
        (
            _RATIFIED_SCIENCEBASE_HEADER.replace("DataSource", "WrongSource", 1)
            + "\n"
            + _VALID_SCIENCEBASE_ROW
            + "\n"
        ).encode("utf-8"),
        id="wrong-header",
    ),
    pytest.param(
        (_RATIFIED_SCIENCEBASE_HEADER + "\n").encode("utf-8"),
        id="zero-data-rows",
    ),
    pytest.param(
        (
            _RATIFIED_SCIENCEBASE_HEADER
            + "\n"
            + "MCS2023,Germanium,2022,0,W,14000,15000,5800,0,30000,1300,840\n"
        ).encode("utf-8"),
        id="ragged-width",
    ),
]


@pytest.mark.parametrize("content", _PHASE_2_REJECTED_CSVS)
def test_phase_2_write_gate_rejects_non_ratified_csv_contract(
    tmp_path: Path, content: bytes
) -> None:
    module = _load_module()
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    authority = module.load_live_go_once(
        go_path,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        prepared,
        owner_authenticator=_owner_authenticator(),
    )
    output = ScienceBaseOutput(
        "item-1",
        "map.json",
        content,
        hashlib.sha256(content).hexdigest(),
        3,
        len(content),
    )

    with pytest.raises(
        module.LiveReadinessHold, match="sciencebase_artifact_content_rejected"
    ):
        module._write_artifact(store, authority, output, prepared.producer_request)

    assert list(tmp_path.glob("sciencebase-*.bin")) == []
    store.close()


def _execute_and_verify_phase_2_artifact(
    module,
    tmp_path: Path,
    content: bytes,
    *,
    monkeypatch: pytest.MonkeyPatch | None = None,
):
    _database(tmp_path)
    store = _store(tmp_path)
    prepared = _prepared(tmp_path.resolve(), store)
    raw = _canonical(_go_document(module, prepared))
    go_path = tmp_path / "owner-go.json"
    go_path.write_bytes(raw)
    go_digest = "sha256:" + hashlib.sha256(raw).hexdigest()

    if monkeypatch is not None:

        def bypass_write_gate(store, authority, output, _expected_request):
            digest = hashlib.sha256(output.content).hexdigest()
            path = Path(store.canonical_root) / (
                f"sciencebase-{authority.content_digest[7:]}-{digest}.bin"
            )
            path.write_bytes(output.content)
            return path

        monkeypatch.setattr(module, "_write_artifact", bypass_write_gate)

    def run(_prepared, *, execution_authority):
        assert execution_authority.consume_exact(DIGESTS["envelope"]) is True
        for ordinal, stage in enumerate(
            ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download"),
            start=1,
        ):
            assert _prepared.reservation_store.reserve(
                _plan(tmp_path.resolve(), ordinal, stage)
            ).disposition == "RESERVED"
        _prepared.reservation_store.close()
        return ScienceBaseOutput(
            "item-1",
            "map.json",
            content,
            hashlib.sha256(content).hexdigest(),
            3,
            len(content),
        )

    executed = module.execute_sciencebase_live(
        prepared,
        go_path=go_path,
        go_digest=go_digest,
        run=run,
        store_factory=lambda root, path: _store(root),
        owner_authenticator=_owner_authenticator(),
    )
    verified = module.verify_sciencebase_closeout(
        canonical_root=tmp_path.resolve(),
        reservation_database_path=tmp_path / "reservation.db",
        connector_run_id=RUN_ID,
        go_digest=go_digest,
        store_factory=lambda root, path: _store(root),
    )
    return executed, verified


@pytest.mark.parametrize("content", _PHASE_2_REJECTED_CSVS)
def test_phase_2_verify_gate_holds_non_ratified_csv_without_verified_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    module = _load_module()

    executed, verified = _execute_and_verify_phase_2_artifact(
        module, tmp_path, content, monkeypatch=monkeypatch
    )

    assert executed.status == "TERMINAL"
    assert verified.status == "HOLD"
    assert verified.code == "sciencebase_artifact_content_rejected"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event "
            "WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()[0] == 0


def test_phase_2_characterized_artifact_passes_write_and_verify_gates(
    tmp_path: Path,
) -> None:
    module = _load_module()

    assert module.SCIENCEBASE_CSV_HEADER == _RATIFIED_SCIENCEBASE_HEADER
    assert hashlib.sha256(module.SCIENCEBASE_CSV_HEADER.encode("utf-8")).hexdigest() == (
        "048f103704744d4b39125ec28cb830ac94c0e18b9de93680f57844e5eec96394"
    )
    assert len(_CHARACTERIZED_SCIENCEBASE_CSV) == 510
    assert hashlib.sha256(_CHARACTERIZED_SCIENCEBASE_CSV).hexdigest() == (
        "c8eacb7b8df0aa12b45eeb383d79d5cf95d7e002dfed7c07736e5aad3dca930c"
    )
    executed, verified = _execute_and_verify_phase_2_artifact(
        module, tmp_path, _CHARACTERIZED_SCIENCEBASE_CSV
    )

    assert executed.status == "TERMINAL"
    assert executed.artifact_path.read_bytes() == _CHARACTERIZED_SCIENCEBASE_CSV
    assert verified.status == "VERIFIED"
    assert verified.code == "sciencebase_closeout_verified"
