from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
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
    envelope = SimpleNamespace(
        content_digest=DIGESTS["envelope"],
        campaign_id="campaign-test",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        source_commit="1" * 40,
        interpreter_identity="sha256:" + "2" * 64,
        authorization_digest=DIGESTS["authorization"],
        grant_digest=DIGESTS["grant"],
        wrapper_start_token_ref="wrapper-start:test-v1",
    )
    return SimpleNamespace(
        envelope=SimpleNamespace(envelope=envelope),
        reservation_store=store,
        producer_request=_producer_request(root),
        worker_manifest_digest=DIGESTS["manifest"],
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
    assert consumer.last_code == "live_go_consumption_indeterminate"
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
        content = b"public-sciencebase-artifact"
        return ScienceBaseOutput("item-1", "map.json", content, hashlib.sha256(content).hexdigest(), 3, 123)

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
    assert result.artifact_path.read_bytes() == b"public-sciencebase-artifact"
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
    assert terminal["credential_mode"] == "none_public"
    assert terminal["artifact_sha256"] == hashlib.sha256(result.artifact_path.read_bytes()).hexdigest()


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
    content = b"artifact-conflict"
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
    assert json.loads(terminal[2])["containment_status"] == "contained"


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


def test_independent_closeout_rehashes_artifact_and_exact_three_reservations(
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
        content = b"verified-public-artifact"
        return ScienceBaseOutput(
            "item-1", "map.json", content, hashlib.sha256(content).hexdigest(), 3, 321
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
    assert result.status == "VERIFIED"
    assert result.code == "sciencebase_closeout_verified"
    with sqlite3.connect(tmp_path / "reservation.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM connector_run_event WHERE event_type = 'sciencebase_closeout_verified'"
        ).fetchone()[0] == 1


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
        content = b"artifact-before-drift"
        return ScienceBaseOutput(
            "item-1", "map.json", content, hashlib.sha256(content).hexdigest(), 3, 222
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
