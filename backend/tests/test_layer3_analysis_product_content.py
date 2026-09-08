"""Selected authored-content read: exact text, bounded identities, existing readers."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import settings
from app.db.session import Base
from app.models.models import (
    L3AnalysisProductEvidenceLink,
    L3MaterialSnapshot,
    L3Session,
)
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    create_analysis_product_draft,
)
from app.services.layer3_sublayer_state import serialize_analysis_product
from main import app


SESSION_ID = "session-content"
BODY = "Observation: 42 units.\n\tCaveat: descriptive only. <script>literal</script>\nΔ is not causal."
PRODUCT_KEYS = {
    "analysis_product_id", "title", "body", "product_kind", "executor_type",
    "lifecycle_status", "is_non_evidentiary", "basis_hash", "spec_hash", "created_at",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # Autoflush is deliberately enabled: a reader must not persist pending work.
    db = sessionmaker(bind=engine, autoflush=True)()
    db.add(L3Session(
        session_id=SESSION_ID,
        selection_manifest_id="manifest-content",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    ))
    db.add(L3MaterialSnapshot(
        material_snapshot_id="snapshot-content",
        session_id=SESSION_ID,
        descriptor_id="descriptor-content",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="private://DO-NOT-READ",
        payload_hash="payload-hash",
        source_identity_json={"secret": "SOURCE-BLOB-CANARY"},
        source_provenance_json={},
        load_summary_json={},
    ))
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.product_db = db
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()


def _create(client, *, body=BODY, title="Stored interpretation", non_evidentiary=False,
            request_id="content-request"):
    evidence = () if non_evidentiary else (
        AnalysisProductEvidenceDraft(
            ref_kind="material_snapshot", ref_id="snapshot-content",
            evidence_role="observation", locator={"private": "LOCATOR-CANARY"},
        ),
    )
    result = create_analysis_product_draft(
        client.product_db, session_id=SESSION_ID, client_request_id=request_id,
        draft=AnalysisProductDraft(
            product_kind="analyst_note", title=title, body=body, evidence=evidence,
            is_non_evidentiary=non_evidentiary,
            authoring_provenance={"private": "AUTHORING-BLOB-CANARY"},
        ),
    )
    client.product_db.commit()
    return result.product


def _get(client, product_id, *, session_id=SESSION_ID, headers=None, suffix="content"):
    return client.get(
        f"/api/v1/layer3/analysis-product/{product_id}/{suffix}",
        params={"session_id": session_id}, headers=headers,
    )


def test_content_exact_stored_text_identity_and_unchanged_metadata_reads(client):
    product = _create(client)
    pid = product.analysis_product_id
    response = _get(client, pid)
    assert response.status_code == 200, response.text
    content = response.json()
    assert set(content) == {
        "schema_id", "schema_version", "request_id", "server_time", "status",
        "session_id", "analysis_product", "evidence_refs", "evidence_refs_total",
        "evidence_refs_truncated",
    }
    assert content["schema_id"] == "layer3.analysis_product_content.v1"
    assert content["session_id"] == SESSION_ID
    assert set(content["analysis_product"]) == PRODUCT_KEYS
    assert content["analysis_product"] == {
        key: (getattr(product, key).isoformat() if key == "created_at" else getattr(product, key))
        for key in PRODUCT_KEYS
    }
    assert content["analysis_product"]["body"] == BODY
    assert content["evidence_refs"] == [{
        "ref_kind": "material_snapshot", "ref_id": "snapshot-content",
        "evidence_role": "observation",
    }]
    assert content["evidence_refs_total"] == 1
    assert content["evidence_refs_truncated"] is False
    for canary in ("LOCATOR-CANARY", "AUTHORING-BLOB-CANARY", "SOURCE-BLOB-CANARY", "DO-NOT-READ"):
        assert canary not in response.text
    links = client.product_db.query(L3AnalysisProductEvidenceLink).all()
    inventory = serialize_analysis_product(product, links)
    lineage = _get(client, pid, suffix="lineage").json()
    assert "body" not in inventory
    assert "body" not in lineage["product"]
    assert BODY not in json.dumps([inventory, lineage])
    assert _get(client, pid).json()["analysis_product"] == content["analysis_product"]


@pytest.mark.parametrize("non_evidentiary", [False, True])
def test_content_preserves_authoring_text_limits_and_evidence_posture(client, non_evidentiary):
    product = _create(client, body="x" * 16384, title="t" * 256, non_evidentiary=non_evidentiary)
    response = _get(client, product.analysis_product_id)
    assert response.status_code == 200, response.text
    content = response.json()
    assert content["analysis_product"]["title"] == "t" * 256
    assert content["analysis_product"]["body"] == "x" * 16384
    assert content["analysis_product"]["is_non_evidentiary"] is non_evidentiary
    assert content["evidence_refs_total"] == (0 if non_evidentiary else 1)


@pytest.mark.parametrize("field,size", [("title", 257), ("body", 16385)])
def test_content_fails_closed_for_stored_text_outside_authoring_bounds(client, field, size):
    product = _create(client)
    setattr(product, field, "z" * size)
    client.product_db.commit()
    response = _get(client, product.analysis_product_id)
    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "analysis_product_content_exceeds_limit"
    assert "z" * 256 not in response.text


@pytest.mark.parametrize("case,status,code", [
    ("missing", 404, "analysis_product_not_found"),
    ("other-session", 409, "analysis_product_not_in_session"),
])
def test_content_uses_lineage_identity_error_contract(client, case, status, code):
    product = _create(client)
    pid = "no-such-product" if case == "missing" else product.analysis_product_id
    sid = SESSION_ID if case == "missing" else "other-session"
    response = _get(client, pid, session_id=sid)
    assert response.status_code == status, response.text
    assert response.json() == _get(client, pid, session_id=sid, suffix="lineage").json()
    assert response.json()["error_code"] == code
    assert BODY not in response.text


@pytest.mark.parametrize("params", [{}, {"session_id": ""}])
def test_content_requires_nonempty_session_id(client, params):
    product = _create(client)
    response = client.get(
        f"/api/v1/layer3/analysis-product/{product.analysis_product_id}/content", params=params,
    )
    assert response.status_code == 422


def test_content_caps_same_session_links_and_never_reads_blobs_or_writes(client):
    product = _create(client)
    pid = product.analysis_product_id
    db = client.product_db
    first_link = db.query(L3AnalysisProductEvidenceLink).one()
    first_link.evidence_link_id = "ref-000"
    first_link.evidence_role = "context"
    for index in range(1, 205):
        db.add(L3AnalysisProductEvidenceLink(
            evidence_link_id=f"ref-{index:03d}", analysis_product_id=pid,
            session_id=SESSION_ID, ref_kind="material_snapshot", ref_id="snapshot-content",
            evidence_role="context" if index < 200 else "counterpoint",
            locator_json={"secret": "LINK-BLOB-CANARY"},
        ))
    db.add(L3AnalysisProductEvidenceLink(
        evidence_link_id="foreign-first", analysis_product_id=pid, session_id="other-session",
        ref_kind="material_snapshot", ref_id="foreign-ref", evidence_role="context", locator_json={},
    ))
    db.commit()
    # A dirty unrelated row must remain pending even with autoflush enabled.
    pending = L3Session(session_id="pending", selection_manifest_id="pending", status="active_execution")
    db.add(pending)
    statements = []

    def record_sql(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.lower())

    event.listen(db.get_bind(), "before_cursor_execute", record_sql)
    try:
        response = _get(client, pid)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", record_sql)
    assert response.status_code == 200, response.text
    content = response.json()
    assert len(content["evidence_refs"]) == 200
    assert content["evidence_refs_total"] == 205
    assert content["evidence_refs_truncated"] is True
    assert all(ref["ref_id"] == "snapshot-content" for ref in content["evidence_refs"])
    assert all(ref["evidence_role"] == "context" for ref in content["evidence_refs"])
    assert pending in db.new
    assert statements and all(sql.lstrip().startswith("select ") for sql in statements)
    assert len(statements) <= 10
    selects = "\n".join(statements)
    assert "limit" in selects
    for forbidden_column in ("locator_json", "authoring_provenance_json", "summary_json", "payload_ref", "source_identity_json"):
        assert forbidden_column not in selects


@pytest.mark.parametrize("target", ["missing-ref", "other-session"])
def test_content_rejects_missing_or_cross_session_evidence_target(client, target):
    product = _create(client)
    db = client.product_db
    link = db.query(L3AnalysisProductEvidenceLink).one()
    if target == "missing-ref":
        link.ref_id = "missing-secret-ref"
    else:
        db.get(L3MaterialSnapshot, "snapshot-content").session_id = "other-session"
    db.commit()
    response = _get(client, product.analysis_product_id)
    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "evidence_ref_not_found_in_session"
    assert "missing-secret-ref" not in response.text
    assert BODY not in response.text


@pytest.mark.parametrize("mode,role,identity,trusted,status", [
    ("identity_presence", None, True, True, 200),
    ("identity_presence", None, False, True, 401),
    ("identity_presence", None, True, False, 409),
    ("role_enforcing", "owner", True, True, 200),
    ("role_enforcing", "auditor", True, True, 200),
    ("role_enforcing", None, True, True, 401),
    ("role_enforcing", "unknown", True, True, 401),
])
def test_content_preserves_existing_read_audience(client, monkeypatch, mode, role, identity, trusted, status):
    product = _create(client)
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", trusted)
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", mode)
    monkeypatch.setattr(settings, "proxy_identity_header", "X-Forwarded-User")
    monkeypatch.setattr(settings, "proxy_groups_header", "X-Forwarded-Groups")
    monkeypatch.setattr(settings, "proxy_roles_header", "X-Forwarded-Roles")
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
    monkeypatch.setattr(settings, "layer3_public_dataset_analysis_enabled", False)
    monkeypatch.setattr(settings, "layer3_public_connector_value_reveal_enabled", False)
    headers = {"X-Forwarded-Groups": "workspace"}
    if identity:
        headers["X-Forwarded-User"] = "reader-canary"
    if role:
        headers["X-Forwarded-Roles"] = role
    response = _get(client, product.analysis_product_id, headers=headers)
    lineage = _get(client, product.analysis_product_id, headers=headers, suffix="lineage")
    assert response.status_code == lineage.status_code == status, response.text
    if status == 200:
        assert response.json()["analysis_product"]["body"] == BODY
    else:
        per_request = {"request_id", "server_time"}
        assert {k: v for k, v in response.json().items() if k not in per_request} == {
            k: v for k, v in lineage.json().items() if k not in per_request
        }
        assert BODY not in response.text
        assert "reader-canary" not in response.text
    assert settings.layer3_public_dataset_analysis_enabled is False
    assert settings.layer3_public_connector_value_reveal_enabled is False
