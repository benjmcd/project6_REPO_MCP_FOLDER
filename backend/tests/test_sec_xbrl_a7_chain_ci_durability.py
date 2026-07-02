from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.db.session import Base
from app.models.models import DatasetSourceProvenance, DatasetVersion
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_xbrl_sidecar,
)
from app.services.layer3_utils import stable_hash


def test_a7_synthetic_chain_materializes_arelle_sidecar_bridge_offline(monkeypatch, tmp_path):
    _install_isolated_runtime(monkeypatch, tmp_path)
    chain = _seed_synthetic_connector_and_live_artifact()

    parser_response = layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
        {
            "client_request_id": "a7-ci-parser",
            "parser_mode": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_parser.OPERATOR_DECISION,
            "connector_receipt_id": chain["connector_receipt"]["connector_receipt_id"],
            "connector_receipt_hash": chain["connector_receipt"]["connector_receipt_hash"],
            "connector_example_id": chain["example_id"],
            "live_source_artifact_receipt_id": chain["live_receipt"]["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": chain["live_receipt"]["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": chain["live_receipt"]["source_artifact_receipt"][
                "source_artifact_receipt_hash"
            ],
            "operator_confirmation": True,
        }
    )
    assert parser_response["status"] == "ready"
    assert len(parser_response["inline_xbrl_marker_inventory"]) >= 3

    regex_fact_response = (
        layer3_sec_edgar_html_inline_xbrl_fact_authority.derive_sec_edgar_html_inline_xbrl_fact_authority(
            {
                "client_request_id": "a7-ci-regex-fact",
                "fact_authority_mode": layer3_sec_edgar_html_inline_xbrl_fact_authority.FACT_AUTHORITY_MODE,
                "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_authority.OPERATOR_DECISION,
                "parser_receipt_id": parser_response["parser_receipt_id"],
                "parser_receipt_hash": parser_response["parser_receipt_hash"],
                "operator_confirmation": True,
            }
        )
    )
    assert regex_fact_response["status"] == "ready"
    assert regex_fact_response["fact_count"] == 3

    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", _ready_arelle_runner)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_package_files", lambda: [tmp_path / "taxonomy.zip"])
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "arelle-cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")

    sidecar_response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        {
            "client_request_id": "a7-ci-sidecar",
            "sidecar_mode": layer3_sec_xbrl_sidecar.SIDECAR_MODE,
            "operator_decision": layer3_sec_xbrl_sidecar.OPERATOR_DECISION,
            "parser_receipt_id": parser_response["parser_receipt_id"],
            "parser_receipt_hash": parser_response["parser_receipt_hash"],
            "regex_fact_authority_receipt_id": regex_fact_response["fact_authority_receipt_id"],
            "regex_fact_authority_receipt_hash": regex_fact_response["fact_authority_receipt_hash"],
            "operator_confirmation": True,
        }
    )
    assert sidecar_response["status"] == "ready"
    assert sidecar_response["resolved_fact_count"] == 3
    assert sidecar_response["diagnostics"]["app_runtime_imported_arelle"] is False
    assert sidecar_response["diagnostics"]["taxonomy_network_resolution_enabled"] is False

    sidecar_receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        sidecar_response["sidecar_receipt_id"],
        expected_sidecar_receipt_hash=sidecar_response["sidecar_receipt_hash"],
    )
    assert sidecar_receipt["internal_value_store"]["store_state"] == "not_created_internal_value_store_flag_off"
    assert all(item["value_redacted"] is True for item in sidecar_receipt["resolved_fact_projection"])
    assert "A7 Synthetic Test Issuer" not in json.dumps(sidecar_receipt, sort_keys=True)

    session = _sqlite_session()
    try:
        bridge_response = (
            layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
                {
                    "client_request_id": "a7-ci-bridge",
                    "bridge_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE,
                    "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.OPERATOR_DECISION,
                    "fact_authority_receipt_id": regex_fact_response["fact_authority_receipt_id"],
                    "fact_authority_receipt_hash": regex_fact_response["fact_authority_receipt_hash"],
                    "arelle_sidecar_receipt_id": sidecar_response["sidecar_receipt_id"],
                    "arelle_sidecar_receipt_hash": sidecar_response["sidecar_receipt_hash"],
                    "parser_receipt_id": parser_response["parser_receipt_id"],
                    "parser_receipt_hash": parser_response["parser_receipt_hash"],
                    "rollback_confirmed": True,
                    "operator_confirmed": True,
                },
                session,
            )
        )

        assert bridge_response["status"] == "ready"
        assert (
            bridge_response["fact_authority_input_mode"]
            == layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.ARELLE_FACT_AUTHORITY_INPUT_MODE
        )
        assert bridge_response["materialization_summary"]["sidecar_resolved_fact_count"] == 3
        assert bridge_response["materialization_summary"]["raw_fact_values_materialized"] is False
        assert bridge_response["materialization_summary"]["operator_surface_values_exposed"] is False

        dataset_version = session.get(DatasetVersion, bridge_response["dataset_version_id"])
        assert dataset_version is not None
        assert dataset_version.version_type == "sec_edgar_html_inline_xbrl_fact_material_units"
        assert dataset_version.row_count == 3
        assert bridge_response["materialization_receipt_hash"] in str(dataset_version.notes)

        provenance = (
            session.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == bridge_response["dataset_version_id"])
            .one()
        )
        assert provenance.fetch_policy_mode == "server_owned_receipt"
        assert provenance.raw_storage_ref is None

        with Path(str(dataset_version.storage_ref)).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 3
        assert all(row["value_redacted"] == "True" for row in rows)
        assert all(row["value_text"] == "" for row in rows)
        assert all(row["effective_value_text"] == "" for row in rows)
        assert all(row["lexical_value_text"] == "" for row in rows)
        assert "A7 Synthetic Test Issuer" not in json.dumps(bridge_response, sort_keys=True)
        assert "A7 Synthetic Test Issuer" not in json.dumps(rows, sort_keys=True)
    finally:
        session.close()


def test_a7_bridge_cutover_fails_closed_without_sidecar_receipt(monkeypatch, tmp_path):
    _install_isolated_runtime(monkeypatch, tmp_path)
    chain = _seed_synthetic_connector_and_live_artifact()
    parser_response = layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
        {
            "client_request_id": "a7-ci-parser-no-sidecar",
            "parser_mode": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_parser.OPERATOR_DECISION,
            "connector_receipt_id": chain["connector_receipt"]["connector_receipt_id"],
            "connector_receipt_hash": chain["connector_receipt"]["connector_receipt_hash"],
            "connector_example_id": chain["example_id"],
            "live_source_artifact_receipt_id": chain["live_receipt"]["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": chain["live_receipt"]["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": chain["live_receipt"]["source_artifact_receipt"][
                "source_artifact_receipt_hash"
            ],
            "operator_confirmation": True,
        }
    )
    regex_fact_response = (
        layer3_sec_edgar_html_inline_xbrl_fact_authority.derive_sec_edgar_html_inline_xbrl_fact_authority(
            {
                "client_request_id": "a7-ci-regex-fact-no-sidecar",
                "fact_authority_mode": layer3_sec_edgar_html_inline_xbrl_fact_authority.FACT_AUTHORITY_MODE,
                "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_authority.OPERATOR_DECISION,
                "parser_receipt_id": parser_response["parser_receipt_id"],
                "parser_receipt_hash": parser_response["parser_receipt_hash"],
                "operator_confirmation": True,
            }
        )
    )

    session = _sqlite_session()
    try:
        bridge_response = (
            layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
                {
                    "client_request_id": "a7-ci-bridge-no-sidecar",
                    "bridge_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE,
                    "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.OPERATOR_DECISION,
                    "fact_authority_receipt_id": regex_fact_response["fact_authority_receipt_id"],
                    "fact_authority_receipt_hash": regex_fact_response["fact_authority_receipt_hash"],
                    "parser_receipt_id": parser_response["parser_receipt_id"],
                    "parser_receipt_hash": parser_response["parser_receipt_hash"],
                    "rollback_confirmed": True,
                    "operator_confirmed": True,
                },
                session,
            )
        )
        reason = bridge_response["status_projection"]["blocked_reasons"][0]
        assert bridge_response["status"] == "blocked"
        assert reason["reason"] == "arelle_sidecar_receipt_required"
        assert reason["persisted_sidecar_required"] is True
        assert reason["synchronous_arelle_invocation_performed"] is False
        assert reason["regex_fallback_performed"] is False
        assert session.query(DatasetVersion).count() == 0
    finally:
        session.close()


def _install_isolated_runtime(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", False)
    for flag_name in (
        "layer3_sec_edgar_live_network_enabled",
        "layer3_sec_edgar_official_ticker_resolution_enabled",
        "layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized",
        "layer3_sec_edgar_arelle_corpus_validation_enabled",
        "layer3_sec_edgar_arelle_value_reveal_enabled",
        "layer3_sec_xbrl_controlled_value_reveal_submit_enabled",
    ):
        monkeypatch.setattr(settings, flag_name, False)


def _seed_synthetic_connector_and_live_artifact() -> dict[str, object]:
    primary_document_name = "minimal_dei_ixbrl.htm"
    primary_document = Path("backend/tests/fixtures/sec_xbrl_a7/minimal_dei_ixbrl.htm").read_text(encoding="utf-8")
    complete_submission_text = f"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>8-K
<SEQUENCE>1
<FILENAME>{primary_document_name}
<DESCRIPTION>Synthetic A7 CI durability fixture
<TEXT>
{primary_document}
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
""".encode("utf-8")

    live_request = {
        "client_request_id": "a7-ci-live-artifact",
        "cik_or_filer_ref": "0000000000",
        "accession_or_submission_id": "0000000000-26-000001",
        "form_type": "8-K",
        "filing_date": "2026-01-01",
    }
    source_identity = layer3_sec_edgar_live_source_artifact._source_identity(live_request)
    source_identity_hash = stable_hash({"hash_version": "sec_edgar_live_source_identity_hash_v1", **source_identity})
    content_sha256 = hashlib.sha256(complete_submission_text).hexdigest()
    live_receipt = layer3_sec_edgar_live_source_artifact._build_available_receipt(
        request_id=live_request["client_request_id"],
        source_identity=source_identity,
        source_identity_hash=source_identity_hash,
        server_derived_url_hash=layer3_sec_edgar_live_source_artifact._sha256_text(
            layer3_sec_edgar_live_source_artifact._server_derived_complete_submission_text_url(live_request)
        ),
        user_agent_hash=layer3_sec_edgar_live_source_artifact._sha256_text("synthetic-offline-ci"),
        content_sha256=content_sha256,
        content_length=len(complete_submission_text),
    )
    layer3_sec_edgar_live_source_artifact._write_artifact(
        live_receipt["live_source_artifact_receipt_id"],
        complete_submission_text,
        content_sha256,
    )
    layer3_sec_edgar_live_source_artifact._write_receipt(live_receipt)

    live_response = layer3_sec_edgar_live_source_artifact._response_from_receipt(
        live_receipt,
        request_id=live_request["client_request_id"],
        cache_status="synthetic",
        idempotent_replay=False,
        network_request_made=False,
    )

    example_id = "sec-edgar-real-synthetic-a7"
    selected_example = {
        "example_id": example_id,
        "cik": "0000000000",
        "cik_hash": layer3_sec_edgar_real_filing_acquisition_connector._sha256_text("0000000000"),
        "ticker": "",
        "ticker_hash": None,
        "accession_or_submission_id": live_request["accession_or_submission_id"],
        "accession_or_submission_id_hash": layer3_sec_edgar_real_filing_acquisition_connector._sha256_text(
            live_request["accession_or_submission_id"]
        ),
        "form_type": live_request["form_type"],
        "filing_date": live_request["filing_date"],
        "report_period": None,
        "company_name_hash": None,
        "issuer_profile_tags": [],
        "primary_document_hash": layer3_sec_edgar_real_filing_acquisition_connector._sha256_text(
            primary_document_name
        ),
        "primary_document_family": layer3_sec_edgar_real_filing_acquisition_connector._classify_primary_document(
            primary_document_name
        ),
        "primary_document_description_hash": None,
        "source_family": "complete_submission_text",
        "source_family_roles": layer3_sec_edgar_real_filing_acquisition_connector._source_family_roles(
            primary_document_name
        ),
        "expected_support_status": "supported_complete_submission_text",
        "selection_policy": layer3_sec_edgar_real_filing_acquisition_connector.DEFAULT_FILING_SELECTION_POLICY,
        "parser_family": "sec_edgar_filing",
        "parser_contract_id": "aps_sec_edgar_filing_parser_v1",
        "artifact_role_set": [
            "source_evidence_artifact",
            "parser_input_artifact",
            "provenance_audit_artifact",
            "operator_inspection_artifact",
        ],
        "diagnostics": layer3_sec_edgar_real_filing_acquisition_connector._diagnostics_for_primary_document(
            primary_document_name
        ),
    }
    example_set = {
        "example_set_mode": layer3_sec_edgar_real_filing_acquisition_connector.EXAMPLE_SET_MODE,
        "cik_refs": ("0000000000",),
        "form_types": ("8-K",),
        "company_matrix": (),
        "filing_selection_policy": layer3_sec_edgar_real_filing_acquisition_connector.DEFAULT_FILING_SELECTION_POLICY,
    }
    example_set_hash = stable_hash({"hash_version": "sec_edgar_real_filing_example_set_hash_v1", **example_set})
    connector_receipt = layer3_sec_edgar_real_filing_acquisition_connector._build_receipt(
        request_id="a7-ci-connector",
        example_set=example_set,
        example_set_hash=example_set_hash,
        user_agent_hash=layer3_sec_edgar_real_filing_acquisition_connector._sha256_text("synthetic-offline-ci"),
        selected_examples=[selected_example],
        acquisition_receipts=[
            layer3_sec_edgar_real_filing_acquisition_connector._redacted_acquisition_receipt(
                live_response,
                example_id=example_id,
            )
        ],
    )
    layer3_sec_edgar_real_filing_acquisition_connector._write_receipt(connector_receipt)
    return {
        "connector_receipt": connector_receipt,
        "example_id": example_id,
        "live_receipt": live_receipt,
    }


def _sqlite_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    return session_factory()


def _ready_arelle_runner(*_args, **_kwargs):
    payload = {
        "schema_id": "tools.sec_xbrl_arelle_extract.v1",
        "arelle_version": layer3_sec_xbrl_sidecar.ARELLE_VERSION,
        "taxonomy_package_loaded": True,
        "taxonomy_package_count": 1,
        "taxonomy_package_hashes": [_hash("synthetic-taxonomy")],
        "taxonomy_package_invalid_count": 0,
        "taxonomy_package_invalid_hashes": [],
        "taxonomy_network_resolution_enabled": False,
        "fact_count": 3,
        "diagnostics": {
            "model_error_count": 0,
            "concept_resolved_from_dts_count": 3,
            "concept_dts_unresolved_count": 0,
            "period_unresolved_with_context_ref_count": 0,
            "unit_unresolved_with_unit_ref_count": 0,
        },
        "document_set": {"loaded_document_count": 1, "entry_document_loaded": True},
        "facts": [
            _arelle_fact(1, "dei:DocumentType", "DocumentType", "8-K"),
            _arelle_fact(2, "dei:EntityRegistrantName", "EntityRegistrantName", "A7 Synthetic Test Issuer"),
            _arelle_fact(3, "dei:AmendmentFlag", "AmendmentFlag", "false"),
        ],
    }
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=json.dumps(payload) + "\n", stderr="")


def _arelle_fact(source_order: int, qname: str, local_name: str, value: str) -> dict[str, object]:
    return {
        "source_order": source_order,
        "entry_document_index": 1,
        "concept": {
            "qname": qname,
            "namespace": "http://xbrl.sec.gov/dei/2025",
            "local_name": local_name,
            "standard": True,
            "extension": False,
            "resolved_from_dts": True,
        },
        "context_id": "c1",
        "unit_id": "",
        "period": {
            "type": "duration",
            "start": "2025-01-01",
            "end": "2025-12-31",
            "instant": None,
            "forever": False,
            "resolved": True,
        },
        "unit": {"resolved": True, "measures": [], "currency": None, "numerator": [], "denominator": []},
        "dimensions": {"explicit": [], "typed": [], "resolved": True},
        "decimals": None,
        "precision": None,
        "scale": None,
        "sign": None,
        "format": None,
        "hidden": False,
        "continued": False,
        "continued_at": None,
        "footnote_count": 0,
        "value": value,
        "effective_value": value,
        "lexical_value": value,
    }


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
