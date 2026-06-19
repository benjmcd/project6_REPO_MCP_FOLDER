from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
)
from app.services import layer3_sec_edgar_live_source_artifact as live_source
from app.services import layer3_sec_edgar_real_filing_acquisition_connector as connector_service
from app.services import layer3_sec_xbrl_controlled_value_reveal_submit as submit_service
from app.services import layer3_sec_xbrl_e2e_offline_orchestrator as offline_orchestrator
from app.services import layer3_sec_xbrl_full_pipeline_orchestrator as full_pipeline
from app.services import layer3_sec_xbrl_offline_evidence_loader as evidence_loader
from app.services import layer3_sec_xbrl_operator_review_workflow as workflow_service
from app.services import layer3_sec_xbrl_sidecar
from app.services import layer3_sec_xbrl_value_reveal_authority as authority_service


CIK = "320193"
ACCESSION = "0000320193-25-000079"
PRIMARY_DOCUMENT = "aapl-20250927.htm"
MULTI_PAGE_FACT_COUNT = submit_service.MAX_REVEAL_RECORDS + 105
SINGLE_PAGE_FACT_COUNT = 12


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize(
    ("fact_count", "expected_page_sizes", "request_slug"),
    [
        (MULTI_PAGE_FACT_COUNT, [submit_service.MAX_REVEAL_RECORDS, 105], "m17b-multi"),
        (SINGLE_PAGE_FACT_COUNT, [SINGLE_PAGE_FACT_COUNT], "m17b-single"),
    ],
)
def test_path2_offline_real_chain_paginates_and_completes_under_cap(
    db_session,
    monkeypatch,
    tmp_path,
    fact_count: int,
    expected_page_sizes: list[int],
    request_slug: str,
) -> None:
    result = _run_path2_chain(
        db_session,
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        fact_count=fact_count,
        request_slug=request_slug,
    )

    assert result["page_sizes"] == expected_page_sizes
    assert result["page_indexes"] == list(range(1, len(expected_page_sizes) + 1))
    assert len(result["seen_fact_hashes"]) == fact_count
    assert len(set(result["seen_fact_hashes"])) == fact_count


def _run_path2_chain(
    db_session,
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fact_count: int,
    request_slug: str,
) -> dict[str, Any]:
    storage = _install_offline_boundaries(monkeypatch, tmp_path, fact_count=fact_count)

    plan = full_pipeline.prepare_full_pipeline_open_plan(
        db_session,
        fields={
            "client_request_id": f"{request_slug}-pipeline",
            "cik": CIK,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
            "period_limit": 3,
            "require_companyfacts_oracle": True,
        },
        evidence_owner={
            "owner_ref_hash": _sha256(f"{request_slug}-owner"),
            "workspace_ref_hash": _sha256(f"{request_slug}-workspace"),
        },
    )
    open_payload = plan["open_payload"]

    bundle = evidence_loader.load_sec_xbrl_offline_evidence_bundle(
        storage,
        connector_receipt_hash=open_payload["connector_receipt_hash"],
        cik_hash=open_payload["cik_hash"],
        expected_sidecar_receipt_hash=open_payload["expected_sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=open_payload[
            "expected_statement_classification_receipt_hash"
        ],
    )
    assert bundle["status"] == "offline_evidence_bundle_ready"
    assert bundle["summary"]["resolved_fact_count"] == fact_count
    assert bundle["summary"]["value_record_count"] == fact_count

    sidecar = bundle["evidence"]["sidecar_receipt"]
    assert sidecar["sidecar_state"] == layer3_sec_xbrl_sidecar.READY_STATE
    value_store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(
        sidecar
    )
    assert value_store["value_record_count"] == fact_count

    workflow = offline_orchestrator.open_redacted_operator_review_from_offline_evidence(
        db_session,
        client_request_id=f"{request_slug}-workflow",
        evidence=bundle["evidence"],
        period_limit=open_payload["period_limit"],
        single_transaction=True,
    )
    assert workflow["status"] == "review_ready"

    decision = workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id=f"{request_slug}-decision",
        sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        workflow_basis_hash=workflow["workflow_basis_hash"],
        review_decision="approved",
        decision_reason_code="ready_for_next_freeze",
    )
    assert decision["status"] == "decision_recorded"

    authority = authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id=f"{request_slug}-authority",
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )
    assert authority["status"] == L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY
    assert authority["eligible_for_explicit_value_reveal"] is True
    assert authority["sidecar_receipt_hash"] == sidecar["sidecar_receipt_hash"]
    assert authority["value_store_hash"] == value_store["value_store_hash"]
    _assert_authority_negative_invariants(authority)

    submit_result = _submit_all_pages(
        db_session,
        authority=authority,
        fact_count=fact_count,
        request_slug=request_slug,
    )
    assert submit_result["last_next_page_cursor"] is None
    return submit_result


def _submit_all_pages(
    db_session,
    *,
    authority: dict[str, Any],
    fact_count: int,
    request_slug: str,
) -> dict[str, Any]:
    cursor: str | None = None
    page_index = 0
    seen_fact_hashes: list[str] = []
    page_sizes: list[int] = []
    page_indexes: list[int] = []
    last_next_page_cursor: str | None = None

    while True:
        page_index += 1
        page = submit_service.submit_controlled_value_reveal(
            db_session,
            client_request_id=f"{request_slug}-submit-{page_index}",
            sec_xbrl_value_reveal_authority_receipt_id=authority[
                "sec_xbrl_value_reveal_authority_receipt_id"
            ],
            authority_basis_hash=authority["authority_basis_hash"],
            operator_reveal_confirmation=True,
            page_cursor=cursor,
        )

        assert page["status"] == L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY
        assert page["transient_values_returned"] is True
        assert page["total_record_count"] == fact_count
        assert page["page_index"] == page_index
        assert page["page_record_count"] == len(page["revealed_facts"])
        assert page["revealed_fact_count"] == len(page["revealed_facts"])

        redacted = [fact for fact in page["revealed_facts"] if fact["value_redacted"] is True]
        assert redacted
        for fact in redacted:
            assert fact["effective_value"] == ""
            assert fact["lexical_value"] == ""
            assert fact["value_redaction_reason"]

        for fact in page["revealed_facts"]:
            seen_fact_hashes.append(fact["resolved_fact_id_hash"])

        status = submit_service.inspect_controlled_value_reveal_submit_status(
            db_session,
            sec_xbrl_controlled_value_reveal_submit_receipt_id=page[
                "sec_xbrl_controlled_value_reveal_submit_receipt_id"
            ],
        )
        _assert_hash_only_submit_status(status)

        page_sizes.append(page["page_record_count"])
        page_indexes.append(page["page_index"])
        last_next_page_cursor = page["next_page_cursor"]
        if last_next_page_cursor is None:
            break
        cursor = last_next_page_cursor

    return {
        "seen_fact_hashes": seen_fact_hashes,
        "page_sizes": page_sizes,
        "page_indexes": page_indexes,
        "last_next_page_cursor": last_next_page_cursor,
    }


def _install_offline_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    fact_count: int,
) -> Path:
    storage = tmp_path / f"storage-{fact_count}"
    bootstrap_storage_tree(storage)
    taxonomy = tmp_path / f"taxonomy-{fact_count}.zip"
    taxonomy.write_bytes(b"fake-taxonomy-package")
    cache = tmp_path / f"cache-{fact_count}"
    cache.mkdir()

    monkeypatch.delenv("CI", raising=False)
    for name, value, raising in (
        ("storage_dir", str(storage), True),
        ("layer3_external_local_export_dir", str(tmp_path / "exports"), False),
        ("layer3_sec_edgar_live_network_enabled", True, True),
        ("layer3_sec_edgar_user_agent", "M17BTestAgent/1.0 test-contact", True),
        ("layer3_sec_edgar_max_bytes", 5_000_000, False),
        ("layer3_sec_edgar_timeout_seconds", 20, False),
        ("layer3_sec_edgar_official_ticker_resolution_enabled", False, False),
        ("layer3_sec_edgar_arelle_fact_authority_cutover_enabled", True, True),
        ("layer3_sec_edgar_arelle_internal_value_store_enabled", True, True),
        ("layer3_sec_edgar_arelle_corpus_validation_enabled", True, True),
        ("layer3_sec_edgar_arelle_value_reveal_enabled", True, True),
        ("layer3_sec_xbrl_controlled_value_reveal_submit_enabled", True, True),
    ):
        monkeypatch.setattr(settings, name, value, raising=raising)

    monkeypatch.setattr(live_source, "_SEC_OPENER", _FakeSecOpener(_complete_submission_text()))
    monkeypatch.setattr(live_source, "SEC_EDGAR_SLEEP", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_source, "_enforce_rate_limit", lambda: None)
    monkeypatch.setattr(connector_service, "_sleep_for_rate_policy", lambda: None)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", _arelle_runner(fact_count))
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_package_files", lambda: [taxonomy])
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: cache)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")
    return storage


class _FakeSecOpener:
    def __init__(self, complete_submission_text: bytes) -> None:
        self._complete_submission_text = complete_submission_text

    def open(self, request: Any, timeout: int | None = None) -> "_FakeSecResponse":
        del timeout
        url = str(getattr(request, "full_url", request))
        if "api/xbrl/companyfacts/" in url:
            return _FakeSecResponse(url, _companyfacts_json())
        if "data.sec.gov/submissions/" in url:
            return _FakeSecResponse(url, _submissions_json())
        if "www.sec.gov/Archives/edgar/data/320193/" in url:
            return _FakeSecResponse(url, self._complete_submission_text)
        raise AssertionError(f"unexpected SEC URL: {url}")


class _FakeSecResponse:
    status = 200

    def __init__(self, url: str, body: bytes) -> None:
        self._url = url
        self._body = BytesIO(body)
        self.headers = {"content-type": "application/json"}

    def __enter__(self) -> "_FakeSecResponse":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self._body.close()

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)


def _submissions_json() -> bytes:
    payload = {
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "form": ["10-K"],
                "accessionNumber": [ACCESSION],
                "filingDate": ["2025-10-31"],
                "reportDate": ["2025-09-27"],
                "primaryDocument": [PRIMARY_DOCUMENT],
                "primaryDocDescription": ["10-K"],
            }
        },
    }
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _companyfacts_json() -> bytes:
    facts = {"us-gaap": {}}
    for local_name, value, instant in (
        ("RevenueFromContractWithCustomerExcludingAssessedTax", 391035000000, False),
        ("Assets", 352583000000, True),
        ("NetCashProvidedByUsedInOperatingActivities", 118254000000, False),
        ("Liabilities", 290437000000, True),
    ):
        observation = {"fp": "FY", "fy": 2025, "val": value, "end": "2025-09-27"}
        if not instant:
            observation["start"] = "2024-09-29"
        facts["us-gaap"][local_name] = {"units": {"USD": [observation]}}
    payload = {"cik": CIK, "entityName": "Apple Inc.", "facts": facts}
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _complete_submission_text() -> bytes:
    text = f"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<SEQUENCE>1
<FILENAME>{PRIMARY_DOCUMENT}
<DESCRIPTION>10-K
<TEXT>
<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
<body>
<ix:nonFraction name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    contextRef="ctx-duration-2025" unitRef="usd" decimals="-6">391035000000</ix:nonFraction>
</body>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""
    return text.encode("utf-8")


def _arelle_runner(fact_count: int):
    def run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        payload = {
            "schema_id": "tools.sec_xbrl_arelle_extract.v1",
            "arelle_version": layer3_sec_xbrl_sidecar.ARELLE_VERSION,
            "taxonomy_package_loaded": True,
            "taxonomy_package_count": 1,
            "taxonomy_package_hashes": [_sha256("taxonomy")],
            "taxonomy_package_invalid_count": 0,
            "taxonomy_package_invalid_hashes": [],
            "fact_count": fact_count,
            "diagnostics": {
                "model_error_count": 0,
                "concept_resolved_from_dts_count": fact_count,
                "concept_dts_unresolved_count": 0,
                "period_unresolved_with_context_ref_count": 0,
                "unit_unresolved_with_unit_ref_count": 0,
            },
            "document_set": {"loaded_document_count": 1, "entry_document_loaded": True},
            "facts": _arelle_facts(fact_count),
        }
        return subprocess.CompletedProcess(args=["fake-arelle"], returncode=0, stdout=json.dumps(payload), stderr="")

    return run


def _arelle_facts(fact_count: int) -> list[dict[str, Any]]:
    standard_specs = (
        (1, "us-gaap:DocumentPeriodEndDate", "DocumentPeriodEndDate", "2025-09-27", "instant", "none"),
        (2, "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerExcludingAssessedTax", "391035000000", "duration", "usd"),
        (3, "us-gaap:Assets", "Assets", "352583000000", "instant", "usd"),
        (4, "us-gaap:NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivities", "118254000000", "duration", "usd"),
        (5, "us-gaap:Liabilities", "Liabilities", "290437000000", "instant", "usd"),
    )
    facts = [
        _standard_fact(
            order,
            qname,
            local_name,
            value,
            period=_instant_period() if period_kind == "instant" else _duration_period(),
            unit=_no_unit() if unit_kind == "none" else _usd_unit(),
        )
        for order, qname, local_name, value, period_kind, unit_kind in standard_specs
    ]
    for source_order in range(6, fact_count + 1):
        value = f"{source_order * 17}"
        if source_order in {7, submit_service.MAX_REVEAL_RECORDS + 3}:
            value = f"operator{source_order}@example.test"
        facts.append(_extension_fact(source_order, value))
    return facts[:fact_count]


def _standard_fact(
    source_order: int,
    qname: str,
    local_name: str,
    value: str,
    *,
    period: dict[str, Any],
    unit: dict[str, Any],
) -> dict[str, Any]:
    return _fact(
        source_order,
        qname=qname,
        namespace="http://fasb.org/us-gaap/2024",
        local_name=local_name,
        standard=True,
        extension=False,
        value=value,
        period=period,
        unit=unit,
        unit_id="" if not unit["measures"] else "usd",
    )


def _extension_fact(source_order: int, value: str) -> dict[str, Any]:
    return _fact(
        source_order,
        qname=f"issuer:CustomMetric{source_order}",
        namespace="http://example.test/issuer/2025",
        local_name=f"CustomMetric{source_order}",
        standard=False,
        extension=True,
        value=value,
        period=_duration_period(),
        unit=_usd_unit(),
        unit_id="usd",
    )


def _fact(
    source_order: int,
    *,
    qname: str,
    namespace: str,
    local_name: str,
    standard: bool,
    extension: bool,
    value: str,
    period: dict[str, Any],
    unit: dict[str, Any],
    unit_id: str,
) -> dict[str, Any]:
    concept = {
        "qname": qname,
        "namespace": namespace,
        "local_name": local_name,
        "standard": standard,
        "extension": extension,
        "resolved_from_dts": True,
    }
    return {
        "source_order": source_order,
        "entry_document_index": 1,
        "concept": concept,
        "context_id": f"ctx-{source_order}",
        "unit_id": unit_id,
        "period": period,
        "unit": unit,
        "dimensions": {"explicit": [], "typed": [], "resolved": True},
        "decimals": "0",
        "precision": None,
        "scale": "0",
        "sign": None,
        "format": None,
        "hidden": False,
        "continued": False,
        "footnote_count": 0,
        "value": value,
        "effective_value": value,
        "lexical_value": value,
    }


def _duration_period() -> dict[str, Any]:
    return {"type": "duration", "start": "2024-09-29", "end": "2025-09-27", "instant": None, "forever": False, "resolved": True}


def _instant_period() -> dict[str, Any]:
    return {"type": "instant", "start": None, "end": None, "instant": "2025-09-27", "forever": False, "resolved": True}


def _usd_unit() -> dict[str, Any]:
    return {"resolved": True, "measures": ["iso4217:USD"], "currency": "iso4217:USD", "numerator": ["iso4217:USD"], "denominator": []}


def _no_unit() -> dict[str, Any]:
    return {"resolved": True, "measures": [], "currency": None, "numerator": [], "denominator": []}


def _assert_authority_negative_invariants(payload: dict[str, Any]) -> None:
    invariants = payload["negative_invariants"]
    for key in (
        "raw_values_returned",
        "raw_values_persisted",
        "raw_identity_exposed",
        "runtime_default_changed",
        "value_reveal_performed",
    ):
        assert invariants[key] is False


def _assert_submit_negative_invariants(payload: dict[str, Any]) -> None:
    invariants = payload["negative_invariants"]
    for key in (
        "raw_values_persisted",
        "raw_identity_persisted",
        "status_surface_replays_raw_values",
        "runtime_default_changed",
    ):
        assert invariants[key] is False


def _assert_hash_only_submit_status(status: dict[str, Any]) -> None:
    assert status["revealed_facts"] == []
    assert status["transient_values_returned"] is False
    assert status["status_surface_hash_count_only"] is True
    assert status["audit_receipt_raw_values_persisted"] is False
    assert status["raw_sidecar_receipt_id_persisted"] is False
    _assert_submit_negative_invariants(status)
    serialized = json.dumps(status, sort_keys=True)
    assert "@" not in serialized
    assert "391035000000" not in serialized
    assert "operator7@example.test" not in serialized
    assert f"operator{submit_service.MAX_REVEAL_RECORDS + 3}@example.test" not in serialized


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
