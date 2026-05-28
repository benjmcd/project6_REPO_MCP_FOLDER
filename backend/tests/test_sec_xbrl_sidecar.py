from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_sec_xbrl_sidecar
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


def test_sec_xbrl_sidecar_emits_resolved_semantics_and_redacts_response(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "ready"
    assert response["resolved_fact_count"] == 2
    assert response["parity"]["regex_fact_authority_count"] == 1
    assert response["parity"]["recovered_vs_regex"] == 1
    assert response["coverage"]["period_resolved_count"] == 2
    assert response["coverage"]["unit_resolved_count"] == 2
    assert response["coverage"]["explicit_dimension_fact_count"] == 1
    assert response["coverage"]["typed_dimension_fact_count"] == 1
    assert response["coverage"]["hidden_fact_count"] == 1
    assert response["coverage"]["continued_fact_count"] == 1
    assert response["coverage"]["concept_resolved_from_dts_count"] == 2
    assert "987654321000000" not in json.dumps(response, sort_keys=True)

    receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        response["sidecar_receipt_id"],
        expected_sidecar_receipt_hash=response["sidecar_receipt_hash"],
    )
    assert "value" not in receipt["resolved_fact_records"][0]
    assert receipt["internal_value_store"]["store_state"] == "persisted"
    value_store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)
    assert value_store["value_records"][0]["effective_value"] == "987654321000000"
    assert value_store["value_records"][0]["lexical_value"] == "987654321"
    assert receipt["resolved_fact_projection"][0]["value_redacted"] is True
    assert "value" not in receipt["resolved_fact_projection"][0]
    assert receipt["diagnostics"]["app_runtime_imported_arelle"] is False
    assert receipt["diagnostics"]["taxonomy_package_count"] == 1
    assert receipt["diagnostics"]["taxonomy_package_invalid_count"] == 1
    assert receipt["diagnostics"]["taxonomy_package_invalid_hashes"] == [_hash("invalid-taxonomy")]
    assert receipt["negative_invariants"]["material_bridge_mutated"] is False


def test_sec_xbrl_sidecar_internal_value_store_missing_fails_closed(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )
    receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        response["sidecar_receipt_id"],
        expected_sidecar_receipt_hash=response["sidecar_receipt_hash"],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_value_store_path", lambda _receipt_id: tmp_path / "missing.json")

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_internal_value_store_missing"


def test_sec_xbrl_sidecar_fails_closed_when_arelle_is_absent(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _blocked_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=None)
    )

    assert response["status"] == "blocked"
    assert response["sidecar_receipt_id"] is None
    assert response["status_projection"]["ready"] is False
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "arelle_nonzero_exit"
    assert (
        response["status_projection"]["blocked_reasons"][0]["arelle_error_reason"]
        == "taxonomy_package_valid_package_missing"
    )
    assert response["negative_invariants"]["arelle_imported_into_app_runtime"] is False


def test_sec_xbrl_sidecar_rejects_silent_low_fact_cap(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
            {**_request(companyfacts_count=1), "max_facts": 10}
        )

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_max_facts_too_low"


def test_sec_xbrl_sidecar_fails_closed_on_independent_fact_undercount(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_independent_inline_fact_tally",
        lambda _documents: {
            "inline_fact_count": 3,
            "scanned_document_count": 1,
            "inline_document_count": 1,
            "document_tally": [{"document_index": 1, "inline_fact_count": 3}],
        },
    )

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "blocked"
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "arelle_independent_inline_fact_count_mismatch"
    assert response["status_projection"]["blocked_reasons"][0]["independent_inline_fact_count"] == 3
    assert response["status_projection"]["blocked_reasons"][0]["arelle_fact_count"] == 2


def test_sec_xbrl_sidecar_stages_submission_documents_for_dts_loading():
    primary = "<html><head></head><body>inline</body></html>"
    wrapped_schema = "\r\n<XBRL>\r\n<?xml version=\"1.0\" encoding=\"utf-8\"?>\r\n<schema />\r\n</XBRL>\r\n"
    inline = '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body><ix:nonFraction name="a" contextRef="c">1</ix:nonFraction></body></html>'
    inline_exhibit = '<html xmlns:ixt="http://www.xbrl.org/2013/inlineXBRL"><body><ixt:nonNumeric name="b" contextRef="c">x</ixt:nonNumeric></body></html>'
    content = f"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<FILENAME>primary.htm
<TEXT>{primary}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-101.SCH
<FILENAME>issuer.xsd
<TEXT>{wrapped_schema}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-101.INS
<FILENAME>instance.htm
<TEXT>{inline}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-99.2
<FILENAME>exhibit.htm
<TEXT>{inline_exhibit}</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
""".encode("utf-8")

    documents = layer3_sec_xbrl_sidecar._submission_documents(
        content,
        primary_document_hash=_hash(primary),
    )

    assert documents[0]["primary"] == "true"
    assert documents[1]["filename"] == "issuer.xsd"
    assert documents[1]["text"].startswith("<?xml")
    assert "<XBRL>" not in documents[1]["text"]
    tally = layer3_sec_xbrl_sidecar._independent_inline_fact_tally(documents)
    assert tally["inline_fact_count"] == 2
    assert tally["inline_document_count"] == 2
    assert tally["document_tally"][0]["document_type"] == "EX-101.INS"
    assert tally["document_tally"][1]["document_type"] == "EX-99.2"


def test_sec_xbrl_arelle_tool_prefers_context_dates_and_corrects_adjusted_end_datetimes():
    tool = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools" / "sec-xbrl-arelle.py"), run_name="sec_xbrl_arelle_test")
    period_payload = tool["_period_payload"]

    instant_context = SimpleNamespace(
        isForeverPeriod=False,
        isInstantPeriod=True,
        isStartEndPeriod=False,
        instantDate="2025-12-31",
        instantDatetime=datetime(2026, 1, 1),
    )
    duration_context = SimpleNamespace(
        isForeverPeriod=False,
        isInstantPeriod=False,
        isStartEndPeriod=True,
        startDate=None,
        startDatetime=datetime(2025, 1, 1),
        endDate=None,
        endDatetime=datetime(2026, 1, 1),
    )

    assert period_payload(instant_context)["instant"] == "2025-12-31"
    assert period_payload(duration_context) == {
        "type": "duration",
        "start": "2025-01-01",
        "end": "2025-12-31",
        "instant": None,
        "forever": False,
        "resolved": True,
    }


def _install_receipt_fakes(monkeypatch, tmp_path, runner):
    content = b"retained complete submission text"
    parsed = {
        "primary_document_hash": _hash("primary-doc"),
        "document_inventory": [{"document_index": 1}],
        "content_order": [{"segment_index": 1}],
        "table_candidate_inventory": [],
        "inline_xbrl_marker_inventory": [{"marker_index": 1}],
    }
    parser = {
        "parser_receipt_id": "sec-edgar-html-inline-xbrl-parser-" + "a" * 24,
        "parser_receipt_hash": _hash("parser"),
        "connector_receipt_id": "sec-edgar-real-filing-acquisition-connector-" + "b" * 24 + "-" + "c" * 24,
        "connector_receipt_hash": _hash("connector"),
        "connector_example_id": "example",
        "live_source_artifact_receipt_id": "sec-edgar-text-table-live-source-artifact-" + "d" * 24 + "-" + "e" * 24,
        "live_source_artifact_receipt_hash": _hash("live"),
        "source_artifact_receipt_hash": _hash("source-artifact"),
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "primary_document_hash": parsed["primary_document_hash"],
        "document_inventory_hash": stable_hash(parsed["document_inventory"]),
        "content_order_hash": stable_hash(parsed["content_order"]),
        "table_candidate_inventory_hash": stable_hash(parsed["table_candidate_inventory"]),
        "inline_xbrl_marker_inventory_hash": stable_hash(parsed["inline_xbrl_marker_inventory"]),
    }
    live_receipt = {
        "source_artifact_receipt": {
            "source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
            "content_sha256": parser["content_sha256"],
        }
    }
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", True)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_html_inline_xbrl_parser,
        "read_sec_edgar_html_inline_xbrl_source_family_parser_receipt",
        lambda *_args, **_kwargs: dict(parser),
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_real_filing_acquisition_connector,
        "read_sec_edgar_real_filing_acquisition_connector_receipt",
        lambda *_args, **_kwargs: {"connector_receipt_hash": parser["connector_receipt_hash"]},
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_live_source_artifact,
        "read_sec_edgar_text_table_live_source_artifact_bytes",
        lambda *_args, **_kwargs: (dict(live_receipt), content),
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_html_inline_xbrl_parser,
        "reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge",
        lambda *_args, **_kwargs: {"primary_document_text": "<html>primary</html>", "parsed": parsed},
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_html_inline_xbrl_fact_authority,
        "read_sec_edgar_html_inline_xbrl_fact_authority_receipt",
        lambda *_args, **_kwargs: {"fact_authority_receipt_hash": _hash("regex"), "fact_count": 1},
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", runner)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_package_files", lambda: [tmp_path / "taxonomy.zip"])
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")


def _request(*, companyfacts_count):
    payload = {
        "client_request_id": "sidecar-test",
        "sidecar_mode": layer3_sec_xbrl_sidecar.SIDECAR_MODE,
        "operator_decision": layer3_sec_xbrl_sidecar.OPERATOR_DECISION,
        "parser_receipt_id": "sec-edgar-html-inline-xbrl-parser-" + "a" * 24,
        "parser_receipt_hash": _hash("parser"),
        "regex_fact_authority_receipt_id": "sec-edgar-html-inline-xbrl-fact-authority-" + "f" * 24,
        "regex_fact_authority_receipt_hash": _hash("regex"),
        "operator_confirmation": True,
    }
    if companyfacts_count is not None:
        payload["companyfacts_standard_fact_count"] = companyfacts_count
        payload["companyfacts_oracle_confidence"] = "primary_companyfacts_us_gaap_dei_accession_scope"
    return payload


def _ready_arelle_runner(*_args, **_kwargs):
    payload = {
        "schema_id": "tools.sec_xbrl_arelle_extract.v1",
        "arelle_version": layer3_sec_xbrl_sidecar.ARELLE_VERSION,
        "taxonomy_package_loaded": True,
        "taxonomy_package_count": 1,
        "taxonomy_package_hashes": [_hash("taxonomy")],
        "taxonomy_package_invalid_count": 1,
        "taxonomy_package_invalid_hashes": [_hash("invalid-taxonomy")],
        "fact_count": 2,
        "diagnostics": {"model_error_count": 0, "concept_resolved_from_dts_count": 2, "concept_dts_unresolved_count": 0},
        "document_set": {"loaded_document_count": 5, "entry_document_loaded": True},
        "facts": [
            {
                "source_order": 1,
                "concept": {"qname": "us-gaap:Revenue", "namespace": "http://fasb.org/us-gaap/2024", "local_name": "Revenue", "standard": True, "extension": False, "resolved_from_dts": True},
                "context_id": "ctx-1",
                "unit_id": "usd",
                "period": {"type": "duration", "start": "2025-01-01", "end": "2025-12-31", "instant": None, "forever": False, "resolved": True},
                "unit": {"resolved": True, "measures": ["iso4217:USD"], "currency": "iso4217:USD", "numerator": ["iso4217:USD"], "denominator": []},
                "dimensions": {"explicit": [{"axis": {"qname": "us-gaap:SegmentAxis"}, "member": {"qname": "us-gaap:SoftwareMember"}}], "typed": [], "resolved": True},
                "decimals": "-6",
                "precision": None,
                "scale": "0",
                "sign": None,
                "format": None,
                "hidden": True,
                "continued": True,
                "continued_at": "cont-1",
                "footnote_count": 0,
                "value": "987654321000000",
                "effective_value": "987654321000000",
                "lexical_value": "987654321",
            },
            {
                "source_order": 2,
                "concept": {"qname": "issuer:CustomMetric", "namespace": "http://example.invalid/issuer", "local_name": "CustomMetric", "standard": False, "extension": True, "resolved_from_dts": True},
                "context_id": "ctx-2",
                "unit_id": "shares",
                "period": {"type": "instant", "start": None, "end": None, "instant": "2025-12-31", "forever": False, "resolved": True},
                "unit": {"resolved": True, "measures": ["xbrli:shares"], "currency": None, "numerator": ["xbrli:shares"], "denominator": []},
                "dimensions": {"explicit": [], "typed": [{"axis": {"qname": "issuer:TypedAxis"}, "member_qname": {"qname": "issuer:TypedMember"}, "value": "typed-code"}], "resolved": True},
                "hidden": False,
                "continued": False,
                "footnote_count": 0,
                "sign": "-",
                "scale": None,
                "decimals": "0",
                "format": None,
                "value": "-123456789",
                "effective_value": "-123456789",
                "lexical_value": "123456789",
            },
        ],
    }
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=json.dumps(payload) + "\n", stderr="")


def _blocked_arelle_runner(*_args, **_kwargs):
    return subprocess.CompletedProcess(
        args=["fake"],
        returncode=2,
        stdout='{"reason":"taxonomy_package_valid_package_missing","error_class":"RuntimeError"}\n',
        stderr="missing",
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
