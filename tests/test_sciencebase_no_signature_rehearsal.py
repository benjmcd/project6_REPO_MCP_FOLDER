from __future__ import annotations

import hashlib
import importlib.util
from io import StringIO
import gc
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from uuid import uuid5

import pytest

from app.services.connector_egress_contract import (
    AUTHORITY_SCHEMA_VERSION,
    PhysicalRequestPlan,
    RequestLimits,
    emit_authority_envelope,
)
from app.services.connector_egress_transport import (
    ReservationFileIdentity,
    ReservationStore,
    ReservationVolumeIdentity,
)
from app.services import dual_live_runtime as runtime
from app.services import sciencebase_live_readiness as readiness


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "11111111-1111-4111-8111-111111111111"
GO_ID = "22222222-2222-4222-8222-222222222222"
GO_DIGEST = "sha256:" + "9" * 64
ENVELOPE_DIGEST = "sha256:" + "a" * 64
AUTHORIZATION_DIGEST = "sha256:" + "b" * 64
GRANT_DIGEST = "sha256:" + "c" * 64
MANIFEST_DIGEST = "sha256:" + "d" * 64


class _IdentityProbe:
    def canonicalize(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def pin(self, _path: Path, *, directory: bool) -> None:
        assert isinstance(directory, bool)

    def volume(self, _path: Path) -> ReservationVolumeIdentity:
        return ReservationVolumeIdentity("volume:rehearsal", True, True)

    def identity(self, path: Path, *, directory: bool) -> ReservationFileIdentity:
        return ReservationFileIdentity(
            "volume:rehearsal", f"file:{path.name}", 1, False, directory
        )

    def close(self) -> None:
        return None


def _load_tool(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _launcher_args(root: Path) -> list[str]:
    return [
        "--authority-envelope",
        str(root / "authority.json"),
        "--authority-envelope-sha256",
        ENVELOPE_DIGEST,
        "--campaign-id",
        "campaign-rehearsal",
        "--canonical-root",
        str(root),
        "--connector-run-id",
        RUN_ID,
        "--reservation-database",
        str(root / "reservation.db"),
        "--query",
        "synthetic public geology",
        "--expected-item-id",
        "synthetic-item",
        "--expected-file-name",
        "synthetic-map.json",
        "--worker-bundle-root",
        str(root / "bundle"),
        "--worker-provisioning-root",
        str(root / "bundles"),
        "--worker-profile-moniker",
        "Project6.B0.Rehearsal",
        "--worker-manifest-sha256",
        MANIFEST_DIGEST,
        "--worker-entrypoint",
        "tools/dual_live_run.py",
        "--worker-interpreter",
        "python.exe",
        "--worker-python-version",
        "3.12.0",
        "--worker-architecture",
        "amd64",
        "--worker-package-sid",
        "S-1-15-2-1",
        "--worker-owner-sid",
        "S-1-5-21-1",
        "--worker-provisioner-sid",
        "S-1-5-21-2",
        "--worker-broker-sid",
        "S-1-5-21-3",
        "--ambient-interpreter-root",
        str(root / "ambient-python"),
        "--campaign-root",
        str(root),
        "--appcontainer-profile-root",
        str(root / "app-profile"),
        "--broker-profile-root",
        str(root / "broker-profile"),
        "--user-data-root",
        str(root / "user-data"),
    ]


def _producer_request(root: Path):
    return SimpleNamespace(
        query="synthetic public geology",
        expected_item_id="synthetic-item",
        expected_file_name="synthetic-map.json",
        envelope_digest=ENVELOPE_DIGEST,
        campaign_id="campaign-rehearsal",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        authorization_digest=AUTHORIZATION_DIGEST,
        grant_digest=GRANT_DIGEST,
        max_total_bytes=512 * 1024 * 1024,
        limits=RequestLimits(timeout_seconds=30),
        max_redirect_hops=0,
        connector_run_target_id=None,
    )


def _prepared(root: Path, source_root: Path, close_calls: list[str]):
    envelope = SimpleNamespace(
        content_digest=ENVELOPE_DIGEST,
        campaign_id="campaign-rehearsal",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        source_commit="1" * 40,
        interpreter_identity="sha256:" + "2" * 64,
        authorization_digest=AUTHORIZATION_DIGEST,
        grant_digest=GRANT_DIGEST,
        wrapper_start_token_ref="retired:sciencebase-live-v2",
    )
    return SimpleNamespace(
        envelope=SimpleNamespace(envelope=envelope),
        reservation_store=SimpleNamespace(close=lambda: close_calls.append("store_close")),
        source_root=source_root,
        producer_request=_producer_request(root),
        worker_manifest_digest=MANIFEST_DIGEST,
    )


def _store(root: Path, database: Path | None = None) -> ReservationStore:
    return ReservationStore(
        root, database or root / "reservation.db", identity_probe=_IdentityProbe()
    )


def _reservation_plan(root: Path, ordinal: int, stage: str) -> PhysicalRequestPlan:
    return PhysicalRequestPlan(
        envelope_digest=ENVELOPE_DIGEST,
        campaign_id="campaign-rehearsal",
        canonical_root=str(root),
        connector_run_id=RUN_ID,
        target_id=f"synthetic-{ordinal}",
        request_ordinal=ordinal,
        stage=stage,
        method="GET",
        canonical_destination=f"https://example.invalid/{stage}",
        header_names=(),
        header_value_sha256s=(),
        body_sha256="sha256:" + hashlib.sha256(b"").hexdigest(),
        limits=RequestLimits(timeout_seconds=30),
        authorization_digest=AUTHORIZATION_DIGEST,
        grant_digest=GRANT_DIGEST,
    )


def _seed_closeout(root: Path, reservation_count: int) -> Path:
    readiness.initialize_reservation_database(root, RUN_ID)
    store = _store(root)
    artifact = b"synthetic-closeout-artifact"
    artifact_sha256 = hashlib.sha256(artifact).hexdigest()
    artifact_name = f"sciencebase-{GO_DIGEST[7:]}-{artifact_sha256}.bin"
    go_metrics = {
        "schema": readiness.LIVE_EVIDENCE_SCHEMA,
        "go_digest": GO_DIGEST,
        "envelope_digest": ENVELOPE_DIGEST,
        "request_digest": "sha256:" + "e" * 64,
        "authorization_digest": AUTHORIZATION_DIGEST,
        "grant_digest": GRANT_DIGEST,
        "credential_mode": "none_public",
        "egress_mode": "capability_scoped_default_off",
    }
    terminal_metrics = {
        **go_metrics,
        "artifact_name": artifact_name,
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": len(artifact),
        "request_count": 3,
        "total_response_bytes": len(artifact),
        "containment_status": "contained",
    }
    try:
        assert store.write_sciencebase_live_event(
            event_id=str(uuid5(readiness.LIVE_EVENT_NAMESPACE, f"go:{RUN_ID}")),
            connector_run_id=RUN_ID,
            phase="live_authority",
            stage="go",
            event_type="sciencebase_live_go_consumed",
            status_after="consumed",
            reason_code="owner_go_consumed",
            metrics=go_metrics,
        ).disposition == "RECORDED"
        stages = ("sciencebase_search", "sciencebase_hydrate", "sciencebase_download")
        for ordinal in range(1, reservation_count + 1):
            stage = stages[ordinal - 1] if ordinal <= 3 else "sciencebase_extra"
            assert store.reserve(_reservation_plan(root, ordinal, stage)).disposition == "RESERVED"
        assert store.write_sciencebase_live_event(
            event_id=str(uuid5(readiness.LIVE_EVENT_NAMESPACE, f"terminal:{RUN_ID}")),
            connector_run_id=RUN_ID,
            phase="terminal",
            stage="sciencebase",
            event_type="sciencebase_acquisition_terminal",
            status_after="succeeded",
            reason_code="sciencebase_acquisition_succeeded",
            metrics=terminal_metrics,
        ).disposition == "RECORDED"
    finally:
        store.close()
    artifact_path = root / artifact_name
    artifact_path.write_bytes(artifact)
    return artifact_path


def _run_closeout(launcher, root: Path) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    code = launcher.main(
        [
            "--verify-closeout",
            "--canonical-root",
            str(root),
            "--connector-run-id",
            RUN_ID,
            "--reservation-database",
            str(root / "reservation.db"),
            "--owner-go-sha256",
            GO_DIGEST,
        ],
        verify=lambda **kwargs: readiness.verify_sciencebase_closeout(
            store_factory=lambda actual_root, database: _store(actual_root, database),
            **kwargs,
        ),
        settings_factory=lambda: pytest.fail("closeout read runtime switch"),
        dependencies_factory=lambda: pytest.fail("closeout built runtime"),
        stdout=stdout,
        stderr=stderr,
    )
    return code, stdout.getvalue(), stderr.getvalue()


def test_sciencebase_no_signature_rehearsal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DUAL_LIVE_RUNTIME_ENABLED", raising=False)

    def publish(final: Path, initialize) -> Path:
        if final.exists():
            raise readiness.CustodyHold("custody_exists")
        stage = final.with_name(".reservation.db.rehearsal.tmp")
        stage.touch(exist_ok=False)
        try:
            initialize(stage)
            assert not final.exists()
            stage.rename(final)
            return final
        except BaseException:
            stage.unlink(missing_ok=True)
            raise

    monkeypatch.setattr(readiness, "publish_new_initialized_file", publish)
    spent_marker = tmp_path / "authority" / "spent.jsonl"
    monkeypatch.setattr(readiness, "LIVE_GO_SPENT_MARKER", spent_marker)
    launcher = _load_tool("sciencebase_rehearsal_launcher", REPO_ROOT / "tools" / "dual_live_run.py")
    initializer = _load_tool(
        "sciencebase_rehearsal_initializer", REPO_ROOT / "tools" / "dual_live_initialize.py"
    )

    # R1: real template writer through the launcher, with execution as a hard tripwire.
    r1_root = (tmp_path / "r1-root").resolve()
    source_root = (tmp_path / "r1-source").resolve()
    owner_root = (tmp_path / "r1-owner").resolve()
    for path in (r1_root, source_root, owner_root):
        path.mkdir()
    close_calls: list[str] = []
    prepared = _prepared(r1_root, source_root, close_calls)
    template = owner_root / "owner-go.json"

    def run_template(path: Path) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        code = launcher.main(
            [
                *_launcher_args(r1_root),
                "--emit-owner-go-template",
                str(path),
                "--owner-go-id",
                GO_ID,
            ],
            settings_factory=lambda: SimpleNamespace(dual_live_runtime_enabled=True),
            dependencies_factory=lambda: object(),
            prepare=lambda *_args: runtime.RuntimeResult(
                runtime.RuntimeStatus.PREPARED,
                "dual_live_runtime_prepared_non_live",
                prepared,
            ),
            execute=lambda *_args, **_kwargs: pytest.fail("template consumed GO or executed"),
            stdout=stdout,
            stderr=stderr,
        )
        return code, stdout.getvalue(), stderr.getvalue()

    code, stdout, stderr = run_template(template)
    assert code == 0 and stderr == ""
    document = json.loads(template.read_bytes())
    assert set(document) == readiness._GO_FIELDS
    assert len(document) == 15
    assert document["schema"] == "project6.sciencebase_live_go.v1"
    assert document["credential_mode"] == "none_public"
    assert document["egress_mode"] == "capability_scoped_default_off"
    assert document["wrapper_start_token_ref"] == "retired:sciencebase-live-v2"
    digest = "sha256:" + hashlib.sha256(template.read_bytes()).hexdigest()
    assert stdout == (
        "PREPARED: owner_go_template_written\n"
        f"OWNER_GO_PATH: {template}\n"
        f"OWNER_GO_SHA256: {digest}\n"
    )
    print("R1 create stdout:\n" + stdout, end="")

    original = template.read_bytes()
    code, stdout, stderr = run_template(template)
    assert (code, stdout, stderr) == (2, "", "HOLD: live_go_template_exists\n")
    assert template.read_bytes() == original
    print("R1 existing stderr:\n" + stderr, end="")

    inside = r1_root / "owner-go.json"
    code, stdout, stderr = run_template(inside)
    assert (code, stdout, stderr) == (
        2,
        "",
        "HOLD: live_go_template_inside_canonical_root\n",
    )
    assert not inside.exists()
    assert close_calls == ["store_close", "store_close", "store_close"]
    assert not (r1_root / "reservation.db").exists()
    assert not spent_marker.exists()
    print("R1 inside-root stderr:\n" + stderr, end="")

    # R4: synthetic durable records; the command reopens and rehashes each fixture.
    cases = {
        "valid": (3, None, 0, "VERIFIED: sciencebase_closeout_verified\n"),
        "two-reservations": (2, None, 2, "HOLD: sciencebase_closeout_evidence_malformed\n"),
        "four-reservations": (4, None, 2, "HOLD: sciencebase_closeout_evidence_malformed\n"),
        "artifact-mismatch": (3, "artifact", 2, "HOLD: sciencebase_artifact_verification_failed\n"),
        "database-renamed": (3, "database", 2, "HOLD: sciencebase_closeout_failed\n"),
        "consumption-row-deleted": (3, "consumption", 2, "HOLD: sciencebase_closeout_evidence_incomplete\n"),
    }
    for name, (count, mutation, expected_exit, expected_line) in cases.items():
        root = (tmp_path / f"r4-{name}").resolve()
        root.mkdir()
        artifact_path = _seed_closeout(root, count)
        query_database = root / "reservation.db"
        if mutation == "artifact":
            artifact_path.write_bytes(b"tampered-local-fixture")
        elif mutation == "database":
            gc.collect()
            query_database.rename(root / "reservation.db.bak")
            query_database = root / "reservation.db.bak"
        elif mutation == "consumption":
            with sqlite3.connect(query_database) as connection:
                connection.execute(
                    "DELETE FROM connector_run_event WHERE event_type = ?",
                    ("sciencebase_live_go_consumed",),
                )
        code, stdout, stderr = _run_closeout(launcher, root)
        observed = stdout if code == 0 else stderr
        assert code == expected_exit and observed == expected_line
        if query_database.exists():
            with sqlite3.connect(query_database) as connection:
                closeout_count = connection.execute(
                    "SELECT COUNT(*) FROM connector_run_event WHERE event_type = ?",
                    ("sciencebase_closeout_verified",),
                ).fetchone()[0]
            assert closeout_count == (1 if name == "valid" else 0)
        channel = "stdout" if code == 0 else "stderr"
        print(f"R4 {name} {channel}:\n{observed}", end="")

    # R0: initialize a fresh root, open it rw, and prepare through empty census only.
    r0_root = (tmp_path / "r0-root").resolve()
    r0_source = (tmp_path / "r0-source").resolve()
    r0_root.mkdir()
    r0_source.mkdir()
    stdout, stderr = StringIO(), StringIO()
    code = initializer.main(
        ["reservation-store", "--canonical-root", str(r0_root), "--connector-run-id", RUN_ID],
        stdout=stdout,
        stderr=stderr,
    )
    assert code == 0 and stderr.getvalue() == ""
    assert stdout.getvalue() == f"INITIALIZED: {r0_root / 'reservation.db'}\n"
    print("R0 initializer stdout:\n" + stdout.getvalue(), end="")

    authority_document = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "campaign_id": "campaign-rehearsal",
        "canonical_root": str(r0_root),
        "connector_run_id": RUN_ID,
        "source_commit": "1" * 40,
        "interpreter_identity": "sha256:" + "2" * 64,
        "authorization_digest": AUTHORIZATION_DIGEST,
        "grant_digest": GRANT_DIGEST,
        "wrapper_start_token_ref": "retired:sciencebase-live-v2",
    }
    raw = emit_authority_envelope(authority_document)
    validated_interpreter = (tmp_path / "synthetic-python.exe").resolve()
    boundary = SimpleNamespace(launch_worker=lambda *_args, **_kwargs: pytest.fail("worker launched"))
    worker_bundle = runtime.RuntimeWorkerBundle(
        root=r0_root / "bundle",
        provisioning_root=r0_root / "bundles",
        profile_moniker="Project6.B0.Rehearsal",
        manifest_digest=MANIFEST_DIGEST,
        entrypoint="tools/dual_live_run.py",
        interpreter="python.exe",
        python_version="3.12.0",
        architecture="amd64",
        package_sid="S-1-15-2-1",
        owner_sid="S-1-5-21-1",
        provisioner_sid="S-1-5-21-2",
        broker_sid="S-1-5-21-3",
        ambient_interpreter_root=r0_root / "ambient-python",
        campaign_root=r0_root,
        appcontainer_profile_root=r0_root / "app-profile",
        broker_profile_root=r0_root / "broker-profile",
        user_data_root=r0_root / "user-data",
    )
    request = runtime.RuntimeRequest(
        enabled=True,
        authority_envelope_path=r0_root / "authority.json",
        authority_envelope_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        campaign_id="campaign-rehearsal",
        canonical_root=r0_root,
        connector_run_id=RUN_ID,
        reservation_database_path=r0_root / "reservation.db",
        source_root=r0_source,
        worker_bundle=worker_bundle,
        sciencebase_request=runtime.RuntimeScienceBaseRequest(
            query="synthetic public geology",
            expected_item_id="synthetic-item",
            expected_file_name="synthetic-map.json",
        ),
    )
    dependencies = runtime.RuntimeDependencies(
        read_bytes=lambda *_args: raw,
        source_commit=lambda _path: "1" * 40,
        interpreter_identity=lambda path: (
            "sha256:" + "2" * 64
            if path == validated_interpreter
            else pytest.fail("unexpected interpreter")
        ),
        reservation_store_factory=lambda root, database: _store(root, database),
        boundary_factory=lambda *_args, **_kwargs: boundary,
        transport_factory=lambda _store_value: SimpleNamespace(
            execute=lambda *_args, **_kwargs: pytest.fail("external effect")
        ),
        broker_factory=lambda _transport: SimpleNamespace(
            serve_sciencebase=lambda *_args, **_kwargs: pytest.fail("broker served")
        ),
        bundle_probe_factory=lambda _binding: object(),
        bundle_validator=lambda *_args: SimpleNamespace(interpreter=validated_interpreter),
    )
    prepared_result = runtime.prepare_dual_live_runtime(request, dependencies)
    assert prepared_result.status is runtime.RuntimeStatus.PREPARED
    assert prepared_result.code == "dual_live_runtime_prepared_non_live"
    assert prepared_result.prepared is not None
    assert prepared_result.prepared.envelope.live_authority is False
    runtime.close_prepared_runtime(prepared_result.prepared)
    with sqlite3.connect(r0_root / "reservation.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM connector_run_event").fetchone()[0] == 0
    print("R0 prepare stdout:\nPREPARED: dual_live_runtime_prepared_non_live\n")

    initializer_source = (REPO_ROOT / "tools" / "dual_live_initialize.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "DUAL_LIVE_RUNTIME_ENABLED",
        "prepare_dual_live_runtime",
        "run_prepared_runtime",
        "requests",
        "launch_worker",
    ):
        assert forbidden not in initializer_source
