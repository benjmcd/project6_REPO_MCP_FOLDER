"""Tests for the SEC/XBRL Layer 3 operator lifecycle CLI.

Uses a TestClient-backed transport adapter so the CLI exercises the real
FastAPI routes against an in-memory SQLite database (StaticPool).
Live network calls are monkeypatched.

Test matrix:
1. open --ticker AAPL --confirm  -> exit 0, prints workflow_id, no raw CIK (320193)
2. open WITHOUT --confirm        -> refuses, exit nonzero, route NOT called
3. open --ticker ZZZZ --confirm  -> unknown ticker error, exit nonzero, route not called
4. reveal without --confirm      -> refuses, exit nonzero, value-reveal/submit NOT called
5. decide without required flags -> argparse error, exit nonzero
6. status happy path             -> prints status (workflow stubbed via transport spy)
7. open->decide->prepare-authority chain (happy path with stubbed corpus)
   + reveal request-assembly assertion (operator_reveal_confirmation=True only with --confirm)
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.api.deps import get_db
from app.db.session import Base
from main import app

from app.services import (
    layer3_sec_xbrl_full_pipeline_orchestrator as orchestrator,
    layer3_sec_edgar_real_company_corpus_validation as corpus_svc,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    classification_receipt_hash_basis,
    STATEMENT_CLASSIFICATION_MODE,
)
from app.services import layer3_sec_xbrl_offline_evidence_loader as loader

from app.cli.sec_xbrl_operator_cli import (
    ROUTE_OPEN,
    ROUTE_REVEAL_SUBMIT,
    ROUTE_STATUS,
    run,
)


# ---------------------------------------------------------------------------
# Shared hash helpers (same patterns as orchestrator test)
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash(char: str) -> str:
    return char * 64


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Evidence storage writer (replicated from orchestrator test)
# ---------------------------------------------------------------------------

def _stage_full_evidence_storage(storage: Path, *, connector_receipt_hash: str) -> dict[str, str]:
    sidecar_hash = _hash("b")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    bridge_hash = _hash("e")
    bridge_id = "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "e" * 24

    records = [
        {
            "resolved_fact_id": "rf-assets",
            "concept": {"namespace": "fasb.org/us-gaap/test", "local_name": "Assets", "standard": True},
            "unit": {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
            "period": {"type": "instant", "instant": "2023-12-31"},
            "dimensions": {"explicit": [], "typed": []},
        },
        {
            "resolved_fact_id": "rf-revenue",
            "concept": {"namespace": "fasb.org/us-gaap/test", "local_name": "Revenues", "standard": True},
            "unit": {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
            "period": {"type": "duration", "start": "2023-01-01", "end": "2023-12-31"},
            "dimensions": {"explicit": [], "typed": []},
        },
    ]
    value_records = [
        {"resolved_fact_id": "rf-assets", "effective_value": "200"},
        {"resolved_fact_id": "rf-revenue", "effective_value": "100"},
    ]
    projection = [{**r, "value_redacted": True} for r in records]
    inventory_hash = stable_hash(projection)
    value_store_hash = stable_hash(value_records)
    statement_roles = [
        {"fact_id_or_order_key": "rf-assets", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-revenue", "statement_candidate_role": "income_statement"},
    ]
    cls_inv_hash = stable_hash(statement_roles)
    sem_hash = stable_hash([])
    cls_order_hash = stable_hash([r["fact_id_or_order_key"] for r in statement_roles])
    group_hash = stable_hash([])
    unclass_hash = stable_hash([])
    diag_hash = stable_hash({})

    sidecar = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_records": records,
        "resolved_fact_projection": projection,
        "resolved_fact_inventory_hash": inventory_hash,
        "connector_receipt_hash": connector_receipt_hash,
        "internal_value_store": {
            "store_state": "persisted",
            "value_store_hash": value_store_hash,
            "value_record_count": len(value_records),
        },
        "authority_hashes": {
            "sidecar_receipt_hash": sidecar_hash,
            "internal_value_store_hash": value_store_hash,
        },
    }
    value_store_payload = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_record_count": len(value_records),
        "value_records": value_records,
    }
    classification = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1",
        "classification_mode": STATEMENT_CLASSIFICATION_MODE,
        "fact_authority_receipt_hash": sidecar_hash,
        "fact_inventory_hash": inventory_hash,
        "fact_material_bridge_receipt_hash": bridge_hash,
        "classification_inventory_hash": cls_inv_hash,
        "semantic_profile_inventory_hash": sem_hash,
        "classification_order_hash": cls_order_hash,
        "statement_group_inventory_hash": group_hash,
        "unclassified_fact_inventory_hash": unclass_hash,
        "classification_diagnostics_hash": diag_hash,
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "fact_inventory_hash": inventory_hash,
            "fact_material_bridge_receipt_hash": bridge_hash,
        },
        "classification_inventory": statement_roles,
    }
    cls_hash = stable_hash(
        classification_receipt_hash_basis(
            classification_mode=classification["classification_mode"],
            fact_authority_receipt_hash=classification["fact_authority_receipt_hash"],
            fact_material_bridge_receipt_hash=classification["fact_material_bridge_receipt_hash"],
            fact_inventory_hash=classification["fact_inventory_hash"],
            classification_inventory_hash=classification["classification_inventory_hash"],
            semantic_profile_inventory_hash=classification["semantic_profile_inventory_hash"],
            classification_order_hash=classification["classification_order_hash"],
            statement_group_inventory_hash=classification["statement_group_inventory_hash"],
            unclassified_fact_inventory_hash=classification["unclassified_fact_inventory_hash"],
            classification_diagnostics_hash=classification["classification_diagnostics_hash"],
        )
    )
    cls_id = f"sec-edgar-html-inline-xbrl-fact-statement-classification-{cls_hash[:24]}"
    classification["statement_classification_receipt_id"] = cls_id
    classification["statement_classification_receipt_hash"] = cls_hash

    bridge = {
        "fact_material_bridge_receipt_hash": bridge_hash,
        "fact_material_bridge_receipt_id": bridge_id,
        "response": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "dataset_version_id": "dv-cli-test",
        },
    }

    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / loader.VALUE_STORE_SUBDIR / f"{sidecar_id}.json", value_store_payload)
    _write_json(storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts" / f"{cls_id}.json", classification)
    _write_json(storage / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge" / "receipts" / f"{bridge_id}.json", bridge)

    return {
        "sidecar_hash": sidecar_hash,
        "classification_hash": cls_hash,
        "connector_receipt_hash": connector_receipt_hash,
    }


def _make_corpus_response(
    *,
    cik: str,
    connector_receipt_hash: str,
    sidecar_hash: str,
    classification_hash: str,
    form_type: str = "10-K",
    supported: bool = True,
) -> dict[str, Any]:
    cik_hash = _sha256(cik)
    record: dict[str, Any] = {
        "cik_hash": cik_hash,
        "form_type": form_type,
        "supported_degraded_blocked": "supported" if supported else "blocked",
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "statement_classification_receipt_hash": classification_hash,
            "arelle_sidecar_receipt_hash": sidecar_hash,
        },
    }
    return {
        "connector_receipt_hash": connector_receipt_hash,
        "validation_receipt_id": f"sec-edgar-real-company-corpus-validation-{connector_receipt_hash[:24]}",
        "validation_receipt_hash": _sha256(connector_receipt_hash + sidecar_hash),
        "filing_validation_records": [record],
        "status": "sec_edgar_real_company_corpus_validation_ready",
    }


# ---------------------------------------------------------------------------
# TestClient factory (identical pattern to orchestrator test)
# ---------------------------------------------------------------------------

def _make_test_client(tmp_path: Path, monkeypatch: Any) -> tuple[TestClient, Path]:
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
    bootstrap_storage_tree(storage_dir)

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

    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    client = TestClient(app)
    return client, storage_dir


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
# Spy-only transport (no real HTTP; returns canned responses)
# ---------------------------------------------------------------------------

class SpyTransport:
    """Transport that records calls and returns canned responses without hitting any server."""

    def __init__(self, responses: dict[str, tuple[int, dict]] | None = None) -> None:
        self._responses = responses or {}
        self.post_calls: list[dict] = []
        self.get_calls: list[dict] = []

    def _response_for(self, path: str) -> tuple[int, dict]:
        for key, val in self._responses.items():
            if key in path:
                return val
        return 200, {}

    def post(self, path: str, json_body: dict, headers: dict) -> tuple[int, dict]:
        self.post_calls.append({"path": path, "body": json_body, "headers": headers})
        return self._response_for(path)

    def get(self, path: str, headers: dict) -> tuple[int, dict]:
        self.get_calls.append({"path": path, "headers": headers})
        return self._response_for(path)


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
# Auth + corpus monkeypatching helpers
# ---------------------------------------------------------------------------

def _stub_auth(monkeypatch: Any) -> None:
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc

    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )
    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_evidence_ownership_marker",
        lambda *args, **kwargs: None,
    )


def _stub_corpus(monkeypatch: Any, fake_corpus: dict[str, Any]) -> None:
    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )


# ---------------------------------------------------------------------------
# Test 1: open --ticker AAPL --confirm -> exit 0, prints workflow_id, no raw CIK
# ---------------------------------------------------------------------------

def test_open_aapl_confirm_exit_0_no_cik_leak(tmp_path, monkeypatch) -> None:
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    hashes = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)

    fake_corpus = _make_corpus_response(
        cik=cik,
        connector_receipt_hash=connector_hash,
        sidecar_hash=hashes["sidecar_hash"],
        classification_hash=hashes["classification_hash"],
    )
    _stub_corpus(monkeypatch, fake_corpus)
    _stub_auth(monkeypatch)

    transport = ClientTransport(client)
    exit_code, stdout, stderr = _run_cli(
        ["open", "--ticker", "AAPL", "--confirm"],
        transport,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    # Route was called exactly once
    open_calls = [c for c in transport.post_calls if "open-full-pipeline" in c["path"]]
    assert len(open_calls) == 1, "Expected exactly one POST to open-full-pipeline"

    # Workflow id appears in output
    assert "workflow_id" in stdout.lower() or "sec_xbrl_operator_review_workflow" in stdout

    # Raw CIK must NOT appear in stdout (it's hash-only by design)
    assert "320193" not in stdout, f"Raw CIK '320193' leaked into stdout: {stdout!r}"


# ---------------------------------------------------------------------------
# Test 2: open WITHOUT --confirm -> refuses, exit nonzero, route NOT called
# ---------------------------------------------------------------------------

def test_open_without_confirm_refuses(tmp_path, monkeypatch) -> None:
    client, _ = _make_test_client(tmp_path, monkeypatch)
    transport = ClientTransport(client)

    exit_code, stdout, stderr = _run_cli(
        ["open", "--ticker", "AAPL"],
        transport,
    )

    assert exit_code != 0, "Expected nonzero exit when --confirm is absent"

    # Route must NOT have been called
    open_calls = [c for c in transport.post_calls if "open-full-pipeline" in c["path"]]
    assert len(open_calls) == 0, "Route must not be called without --confirm"

    combined = stdout + stderr
    assert "confirm" in combined.lower(), "Error message should mention --confirm"


# ---------------------------------------------------------------------------
# Test 3: open --ticker ZZZZ --confirm -> unknown ticker, exit nonzero, route not called
# ---------------------------------------------------------------------------

def test_open_unknown_ticker_exit_nonzero(tmp_path, monkeypatch) -> None:
    client, _ = _make_test_client(tmp_path, monkeypatch)
    transport = ClientTransport(client)

    exit_code, stdout, stderr = _run_cli(
        ["open", "--ticker", "ZZZZ", "--confirm"],
        transport,
    )

    assert exit_code != 0, "Expected nonzero exit for unknown ticker"

    open_calls = [c for c in transport.post_calls if "open-full-pipeline" in c["path"]]
    assert len(open_calls) == 0, "Route must not be called for unknown ticker"

    combined = stdout + stderr
    assert "ZZZZ" in combined or "known" in combined.lower(), \
        "Error should mention the unknown ticker"


# ---------------------------------------------------------------------------
# Test 4: reveal without --confirm -> refuses, exit nonzero, submit NOT called
# ---------------------------------------------------------------------------

def test_reveal_without_confirm_refuses() -> None:
    spy = SpyTransport()

    exit_code, stdout, stderr = _run_cli(
        [
            "reveal",
            "--authority-receipt-id", "some-receipt-id",
            "--authority-basis-hash", "a" * 64,
            # NOTE: --confirm deliberately omitted
        ],
        spy,
    )

    assert exit_code != 0, "Expected nonzero exit when --confirm is absent from reveal"

    reveal_calls = [c for c in spy.post_calls if "value-reveal/submit" in c["path"]]
    assert len(reveal_calls) == 0, "value-reveal/submit must not be called without --confirm"

    combined = stdout + stderr
    assert "confirm" in combined.lower(), "Error message should mention --confirm"


# ---------------------------------------------------------------------------
# Test 5: decide without required flags -> argparse error, exit nonzero
# ---------------------------------------------------------------------------

def test_decide_missing_required_flags() -> None:
    spy = SpyTransport()

    # Missing both --review-decision and --reason-code (but also missing --workflow-id)
    exit_code, stdout, stderr = _run_cli(
        ["decide"],
        spy,
    )
    assert exit_code != 0, "Expected nonzero exit when required flags are absent"


def test_decide_missing_reason_code() -> None:
    spy = SpyTransport()

    exit_code, stdout, stderr = _run_cli(
        [
            "decide",
            "--workflow-id", "wf-001",
            "--workflow-basis-hash", "a" * 64,
            "--review-decision", "approved",
            # --reason-code deliberately omitted
        ],
        spy,
    )
    assert exit_code != 0, "Expected nonzero exit when --reason-code is absent"


# ---------------------------------------------------------------------------
# Test 6: status happy path via SpyTransport with canned response
# ---------------------------------------------------------------------------

def test_status_happy_path() -> None:
    workflow_id = "wf-status-test-001"
    canned = {
        "status": "sec_xbrl_operator_review_workflow_open",
        "sec_xbrl_operator_review_workflow_id": workflow_id,
        "workflow_basis_hash": "b" * 64,
    }
    spy = SpyTransport(responses={"operator-review/workflow/status": (200, canned)})

    exit_code, stdout, stderr = _run_cli(
        [
            "status",
            "--workflow-id", workflow_id,
            "--workflow-basis-hash", "b" * 64,
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"
    assert workflow_id in stdout or "workflow" in stdout.lower()

    # Exactly one POST was made
    status_calls = [c for c in spy.post_calls if "workflow/status" in c["path"]]
    assert len(status_calls) == 1

    # Verify the literal/mode values are sent verbatim
    body = status_calls[0]["body"]
    assert body["status_mode"] == "sec_xbrl_operator_review_workflow_status_v1"
    assert body["operator_decision"] == "inspect_sec_xbrl_operator_review_workflow_status"
    assert body["sec_xbrl_operator_review_workflow_id"] == workflow_id


# ---------------------------------------------------------------------------
# Test 7: open -> decide -> prepare-authority chain (happy path) +
#          reveal request-assembly assertion (operator_reveal_confirmation=True only with --confirm)
# ---------------------------------------------------------------------------

def test_open_decide_chain_and_reveal_assembly(tmp_path, monkeypatch) -> None:
    """Happy path through open -> decide (approved) via real TestClient.

    prepare-authority and reveal are exercised via SpyTransport for request-assembly
    assertions only. The prepare-authority real route requires materialized packets and
    zero review exceptions (full packet staging beyond what the open route provides),
    so that step is covered at the transport/request-assembly level here.

    Key safety assertion: operator_reveal_confirmation=True is ONLY sent when --confirm
    is explicitly given; the CLI refuses and exits nonzero without it.
    """
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    hashes = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)

    fake_corpus = _make_corpus_response(
        cik=cik,
        connector_receipt_hash=connector_hash,
        sidecar_hash=hashes["sidecar_hash"],
        classification_hash=hashes["classification_hash"],
    )
    _stub_corpus(monkeypatch, fake_corpus)
    _stub_auth(monkeypatch)

    transport = ClientTransport(client)

    # Step 1: open (real route via TestClient)
    exit_code, stdout, _ = _run_cli(
        ["open", "--ticker", "AAPL", "--confirm"],
        transport,
    )
    assert exit_code == 0, f"open step failed; stdout={stdout}"

    # Extract workflow_id from the CLI output
    workflow_id = None
    workflow_basis_hash = None
    for line in stdout.splitlines():
        if "workflow_id" in line and ":" in line:
            val = line.split(":", 1)[1].strip()
            if val and val != "None":
                workflow_id = val
        if "workflow_basis_hash" in line and ":" in line:
            val = line.split(":", 1)[1].strip()
            if val and val != "None":
                workflow_basis_hash = val

    assert workflow_id is not None, f"Could not extract workflow_id from output:\n{stdout}"
    if not workflow_basis_hash:
        workflow_basis_hash = "0" * 64  # decide route accepts None hash; use placeholder

    # Step 2: decide (approved) — real route via TestClient
    decide_argv = [
        "decide",
        "--workflow-id", workflow_id,
        "--workflow-basis-hash", workflow_basis_hash,
        "--review-decision", "approved",
        "--reason-code", "ready_for_next_freeze",
    ]
    exit_code, stdout_decide, stderr_decide = _run_cli(decide_argv, transport)
    assert exit_code == 0, f"decide step failed; stderr={stderr_decide!r}; stdout={stdout_decide!r}"

    # Extract decision_id and decision_basis_hash from output
    decision_id = None
    decision_basis_hash = None
    for line in stdout_decide.splitlines():
        if "decision_id" in line and ":" in line:
            val = line.split(":", 1)[1].strip()
            if val and val != "None":
                decision_id = val
        if "decision_basis_hash" in line and ":" in line:
            val = line.split(":", 1)[1].strip()
            if val and val != "None":
                decision_basis_hash = val

    assert decision_id is not None, f"Could not extract decision_id from output:\n{stdout_decide}"
    assert decision_basis_hash is not None, f"Could not extract decision_basis_hash:\n{stdout_decide}"

    # Verify exact literal values sent to the decide route
    decide_calls = [c for c in transport.post_calls if "decision/submit" in c["path"]]
    assert len(decide_calls) == 1
    decide_body = decide_calls[0]["body"]
    assert decide_body["submit_mode"] == "sec_xbrl_operator_review_decision_submit_v1"
    assert decide_body["operator_decision"] == "submit_sec_xbrl_operator_review_decision"
    assert decide_body["review_decision"] == "approved"
    assert decide_body["decision_reason_code"] == "ready_for_next_freeze"

    # Step 3: prepare-authority (SpyTransport — request-assembly check only).
    # The real route requires materialized packets + zero review exceptions which needs
    # additional staging (statement packet materialization) beyond what open provides.
    # That gap is documented: the CLI sends the correct literals; server-side preconditions
    # are verified in the operator-review workflow service tests.
    fake_authority_receipt_id = "vr-authority-spy-001"
    fake_authority_basis_hash = "d" * 64
    prep_spy = SpyTransport(responses={"value-reveal/authority/prepare": (200, {
        "sec_xbrl_value_reveal_authority_receipt_id": fake_authority_receipt_id,
        "authority_basis_hash": fake_authority_basis_hash,
        "status": "sec_xbrl_value_reveal_authority_ready",
        "value_reveal_performed": False,
        "production_readiness_claimed": False,
    })})

    exit_code, stdout_prep, stderr_prep = _run_cli(
        [
            "prepare-authority",
            "--decision-id", decision_id,
            "--decision-basis-hash", decision_basis_hash,
        ],
        prep_spy,
    )
    assert exit_code == 0, f"prepare-authority failed; stderr={stderr_prep!r}; stdout={stdout_prep!r}"

    prep_calls = [c for c in prep_spy.post_calls if "value-reveal/authority/prepare" in c["path"]]
    assert len(prep_calls) == 1
    prep_body = prep_calls[0]["body"]
    assert prep_body["authority_mode"] == "sec_xbrl_value_reveal_authority_receipt_v1"
    assert prep_body["operator_decision"] == "prepare_sec_xbrl_value_reveal_authority"
    assert prep_body["sec_xbrl_operator_review_decision_id"] == decision_id
    assert prep_body["decision_basis_hash"] == decision_basis_hash

    # Step 4: reveal request-assembly — SpyTransport.
    # With --confirm: operator_reveal_confirmation=True must be in the body.
    reveal_spy = SpyTransport(responses={"value-reveal/submit": (200, {
        "sec_xbrl_controlled_value_reveal_submit_receipt_id": "reveal-spy-001",
        "status": "sec_xbrl_controlled_value_reveal_submit_ready",
        "production_readiness_claimed": False,
    })})

    exit_code, _, _ = _run_cli(
        [
            "reveal",
            "--authority-receipt-id", fake_authority_receipt_id,
            "--authority-basis-hash", fake_authority_basis_hash,
            "--confirm",
        ],
        reveal_spy,
    )
    assert exit_code == 0, "reveal --confirm should exit 0 with canned spy response"

    reveal_calls = [c for c in reveal_spy.post_calls if "value-reveal/submit" in c["path"]]
    assert len(reveal_calls) == 1, "reveal --confirm should POST to value-reveal/submit"
    reveal_body = reveal_calls[0]["body"]
    assert reveal_body.get("operator_reveal_confirmation") is True, \
        "operator_reveal_confirmation must be True when --confirm is given"
    assert reveal_body["submit_mode"] == "sec_xbrl_controlled_value_reveal_submit_v1"
    assert reveal_body["operator_decision"] == "submit_explicit_sec_xbrl_value_reveal_from_authority_receipt"

    # Without --confirm: route must NOT be called (safety invariant)
    reveal_spy2 = SpyTransport()
    exit_code2, _, _ = _run_cli(
        [
            "reveal",
            "--authority-receipt-id", fake_authority_receipt_id,
            "--authority-basis-hash", fake_authority_basis_hash,
            # --confirm deliberately omitted
        ],
        reveal_spy2,
    )
    assert exit_code2 != 0, "reveal without --confirm must exit nonzero"
    reveal_calls2 = [c for c in reveal_spy2.post_calls if "value-reveal/submit" in c["path"]]
    assert len(reveal_calls2) == 0, \
        "value-reveal/submit must NOT be called when --confirm is absent"


# ---------------------------------------------------------------------------
# Test: run-pipeline request assembly (all 4 steps, SpyTransport)
# ---------------------------------------------------------------------------

def test_run_pipeline_request_assembly() -> None:
    """run-pipeline --confirm orchestrates all 4 route calls in sequence,
    threading IDs and hashes from each response into the next request."""
    _OPEN_HASH = "a" * 64
    _DECIDE_HASH = "b" * 64
    _AUTH_HASH = "c" * 64

    spy = SpyTransport(responses={
        "open-full-pipeline": (200, {
            "status": "ready",
            "operator_review": {
                "sec_xbrl_operator_review_workflow_id": "wf-pipeline-001",
                "workflow_basis_hash": _OPEN_HASH,
                "status": "open",
            },
            "corpus_validation": {},
            "companyfacts_stage": {},
            "production_readiness_claimed": False,
        }),
        "decision/submit": (200, {
            "sec_xbrl_operator_review_decision_id": "dec-pipeline-001",
            "decision_basis_hash": _DECIDE_HASH,
            "review_decision": "approved",
            "decision_reason_code": "ready_for_next_freeze",
            "status": "approved",
        }),
        "value-reveal/authority/prepare": (200, {
            "sec_xbrl_value_reveal_authority_receipt_id": "auth-pipeline-001",
            "authority_basis_hash": _AUTH_HASH,
            "status": "ready",
            "value_reveal_performed": False,
            "production_readiness_claimed": False,
        }),
        "value-reveal/submit": (200, {
            "sec_xbrl_controlled_value_reveal_submit_receipt_id": "reveal-pipeline-001",
            "status": "ready",
            "production_readiness_claimed": False,
            "revealed_facts": [],
        }),
    })

    exit_code, stdout, stderr = _run_cli(
        [
            "run-pipeline",
            "--ticker", "AAPL",
            "--decision", "approved",
            "--reason-code", "ready_for_next_freeze",
            "--confirm",
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}; stdout={stdout!r}"

    # Step 1: open-full-pipeline called once with operator_confirmation=True
    open_calls = [c for c in spy.post_calls if "open-full-pipeline" in c["path"]]
    assert len(open_calls) == 1, "Expected exactly one POST to open-full-pipeline"
    assert open_calls[0]["body"]["operator_confirmation"] is True

    # Step 2: decision/submit called once with correct decision fields and hash from open response
    decide_calls = [c for c in spy.post_calls if "decision/submit" in c["path"]]
    assert len(decide_calls) == 1, "Expected exactly one POST to decision/submit"
    decide_body = decide_calls[0]["body"]
    assert decide_body["review_decision"] == "approved"
    assert decide_body["decision_reason_code"] == "ready_for_next_freeze"
    assert decide_body["workflow_basis_hash"] == _OPEN_HASH

    # Step 3: value-reveal/authority/prepare called once with hash from decide response
    prep_calls = [c for c in spy.post_calls if "value-reveal/authority/prepare" in c["path"]]
    assert len(prep_calls) == 1, "Expected exactly one POST to value-reveal/authority/prepare"
    prep_body = prep_calls[0]["body"]
    assert prep_body["decision_basis_hash"] == _DECIDE_HASH

    # Step 4: value-reveal/submit called once with operator_reveal_confirmation=True and hash from prep response
    reveal_calls = [c for c in spy.post_calls if "value-reveal/submit" in c["path"]]
    assert len(reveal_calls) == 1, "Expected exactly one POST to value-reveal/submit"
    reveal_body = reveal_calls[0]["body"]
    assert reveal_body["operator_reveal_confirmation"] is True
    assert reveal_body["authority_basis_hash"] == _AUTH_HASH

    # Output must include pipeline completion marker
    assert "run-pipeline" in stdout or "COMPLETE" in stdout, \
        f"Expected 'run-pipeline' or 'COMPLETE' in stdout:\n{stdout}"


# ---------------------------------------------------------------------------
# Test: run-pipeline refuses without --confirm
# ---------------------------------------------------------------------------

def test_run_pipeline_refuses_without_confirm() -> None:
    """run-pipeline without --confirm must exit nonzero and make no route calls."""
    spy = SpyTransport()

    exit_code, stdout, stderr = _run_cli(
        [
            "run-pipeline",
            "--ticker", "AAPL",
            "--decision", "approved",
            "--reason-code", "ready_for_next_freeze",
            # --confirm deliberately omitted
        ],
        spy,
    )

    assert exit_code != 0, "Expected nonzero exit when --confirm is absent from run-pipeline"
    assert len(spy.post_calls) == 0, "No route must be called when --confirm is absent"

    combined = stdout + stderr
    assert "confirm" in combined.lower(), "Error message should mention --confirm"


def test_run_pipeline_refuses_non_approval_decision() -> None:
    """run-pipeline with a non-approved decision must exit nonzero before any route call."""
    spy = SpyTransport()

    # argparse 'choices' restricts to _PIPELINE_VALID_DECISIONS, so non-approved
    # triggers argparse error (exit 2) without reaching cmd_run_pipeline at all.
    exit_code, stdout, stderr = _run_cli(
        [
            "run-pipeline",
            "--ticker", "AAPL",
            "--decision", "changes_requested",
            "--reason-code", "needs_packet_revision",
            "--confirm",
        ],
        spy,
    )

    assert exit_code != 0, "Expected nonzero exit for non-approved decision"
    assert len(spy.post_calls) == 0, "No route must be called for non-approved decision"


def test_run_pipeline_refuses_invalid_max_records() -> None:
    """run-pipeline with --max-records 0 must fail before any network call."""
    spy = SpyTransport()

    exit_code, stdout, stderr = _run_cli(
        [
            "run-pipeline",
            "--ticker", "AAPL",
            "--decision", "approved",
            "--reason-code", "ready_for_next_freeze",
            "--max-records", "0",
            "--confirm",
        ],
        spy,
    )

    assert exit_code != 0, "Expected nonzero exit when --max-records < 1"
    assert len(spy.post_calls) == 0, "No route must be called when max_records is invalid"
    combined = stdout + stderr
    assert "max-records" in combined.lower() or "max_records" in combined.lower(), \
        "Error message should mention max-records"


def test_run_pipeline_stable_open_request_id() -> None:
    """Caller-supplied --open-request-id must be used verbatim in the open step."""
    _OPEN_HASH = "a" * 64
    _DECIDE_HASH = "b" * 64
    _AUTH_HASH = "c" * 64
    STABLE_ID = "stable-retry-id-001"

    spy = SpyTransport(responses={
        "open-full-pipeline": (200, {
            "status": "ready",
            "operator_review": {
                "sec_xbrl_operator_review_workflow_id": "wf-stable-001",
                "workflow_basis_hash": _OPEN_HASH,
                "status": "open",
            },
            "corpus_validation": {},
            "companyfacts_stage": {},
            "production_readiness_claimed": False,
        }),
        "decision/submit": (200, {
            "sec_xbrl_operator_review_decision_id": "dec-stable-001",
            "decision_basis_hash": _DECIDE_HASH,
            "review_decision": "approved",
            "decision_reason_code": "ready_for_next_freeze",
            "status": "approved",
        }),
        "value-reveal/authority/prepare": (200, {
            "sec_xbrl_value_reveal_authority_receipt_id": "auth-stable-001",
            "authority_basis_hash": _AUTH_HASH,
            "status": "ready",
            "value_reveal_performed": False,
            "production_readiness_claimed": False,
        }),
        "value-reveal/submit": (200, {
            "sec_xbrl_controlled_value_reveal_submit_receipt_id": "reveal-stable-001",
            "status": "ready",
            "production_readiness_claimed": False,
            "revealed_facts": [],
        }),
    })

    exit_code, stdout, stderr = _run_cli(
        [
            "run-pipeline",
            "--ticker", "AAPL",
            "--decision", "approved",
            "--reason-code", "ready_for_next_freeze",
            "--open-request-id", STABLE_ID,
            "--confirm",
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    open_calls = [c for c in spy.post_calls if "open-full-pipeline" in c["path"]]
    assert len(open_calls) == 1
    assert open_calls[0]["body"]["client_request_id"] == STABLE_ID, \
        "Caller-supplied --open-request-id must be used verbatim"

    # ID must also appear in stdout (printed before step 1)
    assert STABLE_ID in stdout, "open_request_id must be printed for operator to record"


def test_check_posture_reveal_enabled_exit_0() -> None:
    """check-posture exits 0 when controlled_value_reveal_submit_enabled is True."""
    from app.cli.sec_xbrl_operator_cli import ROUTE_POSTURE

    spy = SpyTransport(responses={
        "sec-xbrl/runtime/posture": (200, {
            "sec_xbrl_runtime_posture": {
                "posture_state": "sec_xbrl_controlled_value_reveal_available_with_runtime_gates",
                "runtime_flags": {
                    "live_sec_edgar_network_enabled": True,
                    "arelle_internal_value_store_enabled": True,
                    "arelle_corpus_validation_enabled": True,
                    "arelle_governed_sibling_value_reveal_enabled": True,
                    "controlled_value_reveal_submit_enabled": True,
                },
                "operator_next_actions": [],
                "activation_surfaces": [],
            },
        }),
    })

    exit_code, stdout, stderr = _run_cli(["check-posture"], spy)

    assert exit_code == 0, f"Expected exit 0 when reveal is enabled; stderr={stderr!r}"
    assert "controlled_value_reveal_available" in stdout or "posture_state" in stdout
    get_calls = [c for c in spy.get_calls if "runtime/posture" in c["path"]]
    assert len(get_calls) == 1, "Expected exactly one GET to runtime/posture"


def test_check_posture_reveal_disabled_exit_1() -> None:
    """check-posture exits 1 and warns when controlled_value_reveal_submit_enabled is False."""
    spy = SpyTransport(responses={
        "sec-xbrl/runtime/posture": (200, {
            "sec_xbrl_runtime_posture": {
                "posture_state": "sec_xbrl_controlled_value_reveal_submit_blocked_by_feature_flag",
                "runtime_flags": {
                    "live_sec_edgar_network_enabled": False,
                    "arelle_internal_value_store_enabled": False,
                    "arelle_corpus_validation_enabled": False,
                    "arelle_governed_sibling_value_reveal_enabled": False,
                    "controlled_value_reveal_submit_enabled": False,
                },
                "operator_next_actions": [
                    "Set LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED=true to enable value-reveal."
                ],
                "activation_surfaces": [],
            },
        }),
    })

    exit_code, stdout, stderr = _run_cli(["check-posture"], spy)

    assert exit_code != 0, "Expected nonzero exit when reveal is disabled"
    combined = stdout + stderr
    assert "OFF" in combined or "blocked" in combined or "disabled" in combined.lower(), \
        "Output should indicate flags are off or path is blocked"
    assert "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED" in combined, \
        "Output should name the blocking flag"


def test_cli_cik_map_matches_connector() -> None:
    """Drift guard: the CLI's embedded ticker->CIK map must stay identical to the
    connector's authoritative map. Fails loudly if the connector adds/changes a ticker."""
    from app.cli import sec_xbrl_operator_cli as cli
    from app.services import layer3_sec_edgar_real_filing_acquisition_connector as connector

    assert cli.REAL_COMPANY_CIK_REFS == connector.REAL_COMPANY_CIK_REFS, (
        "CLI ticker->CIK map drifted from the connector's map; update "
        "app/cli/sec_xbrl_operator_cli.py REAL_COMPANY_CIK_REFS to match."
    )


# ---------------------------------------------------------------------------
# Test 8: admission-status happy path via SpyTransport with canned response
# ---------------------------------------------------------------------------

def test_admission_status_happy_path() -> None:
    """CLI posts to ROUTE_ADMISSION_STATUS with the correct body and prints
    the verdict fields (production_admission_ready, admission_flag_enabled,
    blocked_reason, criteria breakdown).
    """
    from app.cli.sec_xbrl_operator_cli import (
        ROUTE_ADMISSION_STATUS,
        ADMISSION_STATUS_MODE,
        ADMISSION_STATUS_OPERATOR_DECISION,
    )

    workflow_id = "wf-admission-cli-test-001"
    basis_hash = "d" * 64
    canned = {
        "production_admission_ready": False,
        "admission_flag_enabled": False,
        "production_admission_blocked_reason": "production_admission_flag_disabled",
        "production_readiness_claimed": False,
        "criteria": {
            "workflow_approved": {"passed": False, "reason": "flag_disabled"},
        },
        "schema_id": "layer3.sec_xbrl_admission_status.v1",
    }
    spy = SpyTransport(
        responses={"workflow/admission-status": (200, canned)}
    )

    exit_code, stdout, stderr = _run_cli(
        [
            "admission-status",
            "--workflow-id", workflow_id,
            "--workflow-basis-hash", basis_hash,
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    # Exactly one POST to the admission-status route
    admission_calls = [c for c in spy.post_calls if "workflow/admission-status" in c["path"]]
    assert len(admission_calls) == 1, f"Expected 1 POST to admission-status, got: {spy.post_calls}"

    # Verify posted to the right route constant
    assert admission_calls[0]["path"] == ROUTE_ADMISSION_STATUS

    # Verify request body contains the correct literals
    body = admission_calls[0]["body"]
    assert body["admission_status_mode"] == ADMISSION_STATUS_MODE
    assert body["operator_decision"] == ADMISSION_STATUS_OPERATOR_DECISION
    assert body["sec_xbrl_operator_review_workflow_id"] == workflow_id
    assert body["workflow_basis_hash"] == basis_hash

    # Verify output contains the real verdict token printed by cmd_admission_status.
    # The handler prints "  production_admission_ready : ..." as the first verdict line.
    combined = stdout + stderr
    assert "production_admission_ready" in combined, (
        f"Expected 'production_admission_ready' verdict token in output; stdout={stdout!r}"
    )


# ---------------------------------------------------------------------------
# Test: --role auditor forwarded in POST body
# ---------------------------------------------------------------------------

def test_admission_status_role_auditor_forwarded() -> None:
    """CLI admission-status with --role auditor includes operator_role='auditor' in the POST body."""
    from app.cli.sec_xbrl_operator_cli import ROUTE_ADMISSION_STATUS

    workflow_id = "wf-cli-role-auditor-test"
    canned = {
        "production_admission_ready": False,
        "admission_flag_enabled": False,
        "production_admission_blocked_reason": "production_admission_flag_disabled",
    }
    spy = SpyTransport(responses={"workflow/admission-status": (200, canned)})

    exit_code, stdout, stderr = _run_cli(
        [
            "admission-status",
            "--workflow-id", workflow_id,
            "--role", "auditor",
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    admission_calls = [c for c in spy.post_calls if "workflow/admission-status" in c["path"]]
    assert len(admission_calls) == 1, f"Expected 1 POST to admission-status, got: {spy.post_calls}"

    body = admission_calls[0]["body"]
    assert body.get("operator_role") == "auditor", (
        f"Expected operator_role='auditor' in body when --role auditor given; body={body}"
    )


# ---------------------------------------------------------------------------
# Test: --role omitted → operator_role NOT in POST body (default-owner unchanged)
# ---------------------------------------------------------------------------

def test_admission_status_role_default_owner_omitted() -> None:
    """CLI admission-status without --role does NOT include operator_role in the POST body."""
    from app.cli.sec_xbrl_operator_cli import ROUTE_ADMISSION_STATUS

    workflow_id = "wf-cli-role-default-test"
    canned = {
        "production_admission_ready": False,
        "admission_flag_enabled": False,
    }
    spy = SpyTransport(responses={"workflow/admission-status": (200, canned)})

    exit_code, stdout, stderr = _run_cli(
        [
            "admission-status",
            "--workflow-id", workflow_id,
            # --role deliberately omitted
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    admission_calls = [c for c in spy.post_calls if "workflow/admission-status" in c["path"]]
    assert len(admission_calls) == 1, f"Expected 1 POST to admission-status, got: {spy.post_calls}"

    body = admission_calls[0]["body"]
    assert "operator_role" not in body, (
        f"operator_role must NOT be in body when --role is omitted; body={body}"
    )


# ---------------------------------------------------------------------------
# Test: auditor-attach CLI forwards to ROUTE_AUDITOR_ATTACH with operator_role='auditor'
# ---------------------------------------------------------------------------

def test_auditor_attach_forwarded() -> None:
    """CLI auditor-attach posts to ROUTE_AUDITOR_ATTACH with operator_role='auditor'
    and the correct mode/decision literals.  SpyTransport canned-200.
    """
    from app.cli.sec_xbrl_operator_cli import (
        ROUTE_AUDITOR_ATTACH,
        AUDITOR_ATTACH_MODE,
        AUDITOR_ATTACH_OPERATOR_DECISION,
    )

    workflow_id = "wf-cli-auditor-attach-test"
    basis_hash = "f" * 64
    canned = {
        "sec_xbrl_operator_review_workflow_id": workflow_id,
        "workflow_basis_hash": basis_hash,
        "auth_binding_ref": "sec-xbrl-auth-binding:cli-test-ref",
        "auth_binding_role": "auditor",
        "auth_binding_basis_hash": "a" * 64,
        "auth_binding_route_family": "sec_xbrl_operator_review_workflow_status_read",
        "auth_binding_policy_hash": "b" * 64,
        "auth_binding_required": True,
    }
    spy = SpyTransport(responses={"auditor-attach": (200, canned)})

    exit_code, stdout, stderr = _run_cli(
        [
            "auditor-attach",
            "--workflow-id", workflow_id,
            "--workflow-basis-hash", basis_hash,
        ],
        spy,
    )

    assert exit_code == 0, f"Expected exit 0; stderr={stderr!r}"

    attach_calls = [c for c in spy.post_calls if "auditor-attach" in c["path"]]
    assert len(attach_calls) == 1, f"Expected 1 POST to auditor-attach, got: {spy.post_calls}"

    # Verify route constant
    assert attach_calls[0]["path"] == ROUTE_AUDITOR_ATTACH

    # Verify body literals
    body = attach_calls[0]["body"]
    assert body["auditor_attach_mode"] == AUDITOR_ATTACH_MODE
    assert body["operator_decision"] == AUDITOR_ATTACH_OPERATOR_DECISION
    assert body["operator_role"] == "auditor", (
        f"operator_role must always be 'auditor' for auditor-attach; body={body}"
    )
    assert body["sec_xbrl_operator_review_workflow_id"] == workflow_id
    assert body["workflow_basis_hash"] == basis_hash

    # Verify output contains binding ref/role
    combined = stdout + stderr
    assert "auditor-attach" in combined.lower() or "binding" in combined.lower(), (
        f"Expected audit/binding output; stdout={stdout!r}"
    )
