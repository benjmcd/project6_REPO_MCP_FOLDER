"""Tests for the Layer 3 Sublayer 3C headless operator CLI.

Uses a TestClient-backed transport adapter so the CLI exercises the real
FastAPI routes against an in-memory SQLite database (StaticPool).

Test matrix:
1. list-methods -> exit 0, output contains three method ids
2. Full golden path: create-working-set -> generate-product ->
   verify-replay -> show-lineage (all exit 0; reproduced + working_set_linked asserted)
3. promote-product: generate then promote draft->proposed; exit 0 + lifecycle proposed
4. Error path: generate-product with unknown method-id -> nonzero exit + error surfaced
5. --json output is valid JSON for one read command
6. Auth headers: --identity / --groups forwarded via ClientTransport recorded calls
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.api.deps import get_db
from app.db.session import Base
from main import app

from app.models.models import (
    L3MaterialSnapshot,
    L3Session,
)

from app.cli.layer3_operator_cli import run


# ---------------------------------------------------------------------------
# TestClient + DB factory (mirrors SEC CLI test pattern)
# ---------------------------------------------------------------------------


def _make_test_client(monkeypatch) -> tuple[TestClient, "sessionmaker"]:
    """Build an in-memory SQLite DB, wire it into FastAPI, return TestClient + factory."""
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, SessionLocal


# ---------------------------------------------------------------------------
# TestClient-backed transport adapter
# ---------------------------------------------------------------------------


class ClientTransport:
    """Transport adapter that delegates to a FastAPI TestClient.

    Records every call so tests can assert what was (or was not) called.
    """

    def __init__(self, client: TestClient) -> None:
        self._client = client
        self.post_calls: list[dict] = []
        self.get_calls: list[dict] = []

    def post(self, path: str, json_body: dict, headers: dict) -> tuple[int, dict]:
        self.post_calls.append({"path": path, "body": json_body, "headers": headers})
        resp = self._client.post(path, json=json_body, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = {"_raw": resp.text}
        return resp.status_code, body

    def get(self, path: str, headers: dict) -> tuple[int, dict]:
        self.get_calls.append({"path": path, "headers": headers})
        resp = self._client.get(path, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = {"_raw": resp.text}
        return resp.status_code, body


# ---------------------------------------------------------------------------
# Helpers for capturing CLI stdout/stderr and exit code
# ---------------------------------------------------------------------------


def _run_cli(argv: list[str], transport) -> tuple[int, str, str]:
    """Run the CLI, capturing stdout, stderr, and exit code."""
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    exit_code = 0
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf
    try:
        run(argv, transport)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


# ---------------------------------------------------------------------------
# DB seeding helper
# ---------------------------------------------------------------------------

_SESSION_ID = "session-cli-test-001"
_SNAPSHOT_ID = "snapshot-cli-test-001"


def _seed_db(SessionLocal) -> None:
    """Insert a session + material_snapshot so working-set creation succeeds."""
    db = SessionLocal()
    try:
        session_row = L3Session(
            session_id=_SESSION_ID,
            selection_manifest_id="manifest-cli-test",
            status="active_execution",
            operator_context_json={},
            summary_json={},
        )
        snapshot = L3MaterialSnapshot(
            material_snapshot_id=_SNAPSHOT_ID,
            session_id=_SESSION_ID,
            descriptor_id="descriptor-cli-test",
            source_plane="runtime",
            source_shape="dataset_version",
            payload_ref="payload://cli-test",
            payload_hash="hash-cli-test",
            source_identity_json={"dataset_version_id": "dv-cli-test"},
            source_provenance_json={},
            load_summary_json={},
        )
        db.add(session_row)
        db.add(snapshot)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test 1: list-methods -> exit 0, three method ids present
# ---------------------------------------------------------------------------


def test_list_methods_exit_0_three_methods(monkeypatch) -> None:
    client, SessionLocal = _make_test_client(monkeypatch)
    transport = ClientTransport(client)

    exit_code, stdout, stderr = _run_cli(["list-methods"], transport)

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    # Exactly one GET to the methods route
    methods_calls = [c for c in transport.get_calls if "analysis-product/methods" in c["path"]]
    assert len(methods_calls) == 1

    # Three known method ids must appear
    for method_id in (
        "working_set_composition_summary",
        "working_set_member_state_profile",
        "working_set_staleness_diagnostic",
    ):
        assert method_id in stdout, (
            f"Expected method_id {method_id!r} in stdout;\n{stdout}"
        )


# ---------------------------------------------------------------------------
# Test 2: Full golden path via --json to extract IDs between steps
# ---------------------------------------------------------------------------


def test_golden_path_create_generate_verify_lineage(monkeypatch) -> None:
    client, SessionLocal = _make_test_client(monkeypatch)
    _seed_db(SessionLocal)
    transport = ClientTransport(client)

    # Step 1: create-working-set
    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "create-working-set",
            "--session-id", _SESSION_ID,
            "--name", "CLI Golden Path WS",
            "--member", f"material_snapshot:{_SNAPSHOT_ID}",
            "--client-request-id", "cli-golden-ws-001",
        ],
        transport,
    )
    assert exit_code == 0, f"create-working-set failed; stderr={stderr!r}; stdout={stdout!r}"
    ws_resp = json.loads(stdout)
    working_set_id = ws_resp["working_set_id"]
    assert working_set_id, "working_set_id must be non-empty"
    assert ws_resp["member_count"] == 1

    # Step 2: generate-product
    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "generate-product",
            "--session-id", _SESSION_ID,
            "--working-set-id", working_set_id,
            "--method-id", "working_set_composition_summary",
            "--client-request-id", "cli-golden-gen-001",
        ],
        transport,
    )
    assert exit_code == 0, f"generate-product failed; stderr={stderr!r}; stdout={stdout!r}"
    gen_resp = json.loads(stdout)
    analysis_product_id = gen_resp["analysis_product_id"]
    assert analysis_product_id, "analysis_product_id must be non-empty"
    assert gen_resp["lifecycle_status"] == "draft"
    assert gen_resp["method_id"] == "working_set_composition_summary"

    # Step 3: verify-replay
    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "verify-replay",
            "--session-id", _SESSION_ID,
            "--product-id", analysis_product_id,
        ],
        transport,
    )
    assert exit_code == 0, f"verify-replay failed; stderr={stderr!r}; stdout={stdout!r}"
    replay_resp = json.loads(stdout)
    assert replay_resp["reproduced"] is True, (
        f"Expected reproduced=True; classification={replay_resp.get('classification')!r}"
    )

    # Step 4: show-lineage
    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "show-lineage",
            "--session-id", _SESSION_ID,
            "--product-id", analysis_product_id,
        ],
        transport,
    )
    assert exit_code == 0, f"show-lineage failed; stderr={stderr!r}; stdout={stdout!r}"
    lineage_resp = json.loads(stdout)
    assert lineage_resp["working_set_linked"] is True, (
        f"Expected working_set_linked=True; lineage={lineage_resp!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: promote-product draft->proposed
# ---------------------------------------------------------------------------


def test_promote_product_draft_to_proposed(monkeypatch) -> None:
    client, SessionLocal = _make_test_client(monkeypatch)
    _seed_db(SessionLocal)
    transport = ClientTransport(client)

    # create working set
    exit_code, stdout, _ = _run_cli(
        [
            "--json",
            "create-working-set",
            "--session-id", _SESSION_ID,
            "--name", "Promote WS",
            "--member", f"material_snapshot:{_SNAPSHOT_ID}",
            "--client-request-id", "cli-promote-ws-001",
        ],
        transport,
    )
    assert exit_code == 0
    working_set_id = json.loads(stdout)["working_set_id"]

    # generate
    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "generate-product",
            "--session-id", _SESSION_ID,
            "--working-set-id", working_set_id,
            "--method-id", "working_set_composition_summary",
            "--client-request-id", "cli-promote-gen-001",
        ],
        transport,
    )
    assert exit_code == 0, f"generate failed; stderr={stderr!r}"
    analysis_product_id = json.loads(stdout)["analysis_product_id"]

    # promote draft -> proposed
    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "promote-product",
            "--session-id", _SESSION_ID,
            "--product-id", analysis_product_id,
            "--decision-intent", "promote",
            "--decision-reason-code", "proposed_ready",
            "--client-request-id", "cli-promote-001",
        ],
        transport,
    )
    assert exit_code == 0, f"promote-product failed; stderr={stderr!r}; stdout={stdout!r}"
    promote_resp = json.loads(stdout)
    assert promote_resp["lifecycle_status"] == "proposed", (
        f"Expected lifecycle_status='proposed'; got {promote_resp.get('lifecycle_status')!r}"
    )
    assert promote_resp["review_decision"] == "promote"


# ---------------------------------------------------------------------------
# Test 4: generate-product with unknown method-id -> nonzero exit, error surfaced
# ---------------------------------------------------------------------------


def test_generate_unknown_method_id_nonzero_exit(monkeypatch) -> None:
    client, SessionLocal = _make_test_client(monkeypatch)
    _seed_db(SessionLocal)
    transport = ClientTransport(client)

    # create working set first
    exit_code, stdout, _ = _run_cli(
        [
            "--json",
            "create-working-set",
            "--session-id", _SESSION_ID,
            "--name", "Error WS",
            "--member", f"material_snapshot:{_SNAPSHOT_ID}",
            "--client-request-id", "cli-error-ws-001",
        ],
        transport,
    )
    assert exit_code == 0
    working_set_id = json.loads(stdout)["working_set_id"]

    # generate with a nonexistent method
    exit_code, stdout, stderr = _run_cli(
        [
            "generate-product",
            "--session-id", _SESSION_ID,
            "--working-set-id", working_set_id,
            "--method-id", "this_method_does_not_exist",
            "--client-request-id", "cli-error-gen-001",
        ],
        transport,
    )
    assert exit_code != 0, "Expected nonzero exit for unknown method-id"

    # No Python traceback must appear
    combined = stdout + stderr
    assert "Traceback" not in combined, (
        f"Traceback leaked into output:\n{combined}"
    )
    # Error must mention some signal (status code or error text)
    assert "ERROR" in combined or "error" in combined.lower() or "400" in combined or "422" in combined, (
        f"Expected error token in output:\n{combined}"
    )


# ---------------------------------------------------------------------------
# Test 5: --json output is valid JSON for list-methods
# ---------------------------------------------------------------------------


def test_json_flag_produces_valid_json(monkeypatch) -> None:
    client, SessionLocal = _make_test_client(monkeypatch)
    transport = ClientTransport(client)

    exit_code, stdout, stderr = _run_cli(
        ["--json", "list-methods"],
        transport,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"--json output is not valid JSON: {exc}\nstdout={stdout!r}")

    assert "methods" in parsed, f"Expected 'methods' key in JSON output; got: {list(parsed.keys())}"


# ---------------------------------------------------------------------------
# Test 6: auth headers forwarded via --identity / --groups
# ---------------------------------------------------------------------------


def test_auth_headers_forwarded(monkeypatch) -> None:
    """--identity and --groups must appear in X-Forwarded-User / X-Forwarded-Groups headers."""
    client, SessionLocal = _make_test_client(monkeypatch)
    transport = ClientTransport(client)

    exit_code, stdout, stderr = _run_cli(
        [
            "--identity", "operator-foo",
            "--groups", "ops,admin",
            "list-methods",
        ],
        transport,
    )

    # In local mode (AUTH_OWNER=none) the extra identity headers are accepted, so
    # the round-trip succeeds; the point of this test is that they are forwarded.
    assert exit_code == 0, f"stderr={stderr}"
    assert len(transport.get_calls) >= 1, "Expected at least one GET call"

    headers_sent = transport.get_calls[0]["headers"]
    assert headers_sent.get("X-Forwarded-User") == "operator-foo", (
        f"Expected X-Forwarded-User=operator-foo; headers={headers_sent}"
    )
    assert headers_sent.get("X-Forwarded-Groups") == "ops,admin", (
        f"Expected X-Forwarded-Groups=ops,admin; headers={headers_sent}"
    )
