from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.core.config import settings
from app.services import nrc_aps_evidence_bundle as bundle_service
from app.services import nrc_aps_evidence_bundle_contract as bundle_contract
from app.services import nrc_aps_evidence_citation_pack as citation_service
from app.services import nrc_aps_evidence_citation_pack_contract as citation_contract
from app.services import nrc_aps_evidence_report as report_service
from app.services import nrc_aps_evidence_report_contract as report_contract


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router, prefix=settings.api_prefix)
    return TestClient(app, raise_server_exceptions=False)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _snapshot() -> dict[str, Any]:
    return {
        "snapshot_contract_id": bundle_contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID,
        "snapshot_started_at_utc": "2026-06-03T00:00:00Z",
        "snapshot_completed_at_utc": "2026-06-03T00:00:01Z",
        "index_state_hash": "index-state-hash",
        "index_row_count": 3,
        "index_max_updated_at_utc": None,
        "db_fingerprint": "db-fingerprint",
        "read_scope": {"fixture": "pagination-route"},
    }


def _bundle_item(index: int) -> dict[str, Any]:
    text = f"fixture evidence text {index}"
    item = {
        "content_id": f"content-{index:03d}",
        "chunk_id": f"chunk-{index:03d}",
        "content_contract_id": bundle_contract.APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": bundle_contract.APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
        "chunk_ordinal": index,
        "start_char": 0,
        "end_char": len(text),
        "chunk_text": text,
        "chunk_text_sha256": f"{index:064x}"[-64:],
        "snippet_text": text,
        "snippet_start_char": 0,
        "snippet_end_char": len(text),
        "highlight_spans": [],
        "matched_unique_query_terms": 0,
        "summed_term_frequency": 0,
        "run_id": "run-pagination-route",
        "target_id": "target-pagination-route",
        "accession_number": f"ML{index:010d}",
        "content_units_ref": f"content-units-{index}.json",
        "normalized_text_ref": f"normalized-{index}.txt",
        "blob_ref": f"blob-{index}.pdf",
        "download_exchange_ref": f"exchange-{index}.json",
        "discovery_ref": f"discovery-{index}.json",
        "selection_ref": None,
        "normalized_text_sha256": f"{index + 10:064x}"[-64:],
        "blob_sha256": f"{index + 20:064x}"[-64:],
        "page_start": index + 1,
        "page_end": index + 1,
        "unit_kind": "pdf_paragraph",
        "quality_status": "usable",
        "diagnostics_ref": f"diagnostics-{index}.json",
        "visual_page_refs": [],
        "document_class": "inspection_report",
        "media_type": "application/pdf",
        "page_count": 3,
    }
    item["group_id"] = bundle_contract.group_id_for_item(item)
    return item


def _persist_fixture_artifacts(reports_dir: Path) -> dict[str, str]:
    run_id = "run-pagination-route"
    bundle_id = "bundle-pagination-route"
    items = [_bundle_item(index) for index in range(1, 4)]
    bundle_payload = {
        "schema_id": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
        "schema_version": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "generated_at_utc": "2026-06-03T00:00:02Z",
        "bundle_id": bundle_id,
        "mode": bundle_contract.APS_MODE_BROWSE,
        "run_id": run_id,
        "query": None,
        "query_tokens": [],
        "request_identity_hash": "request-identity-hash",
        "snapshot": _snapshot(),
        "total_hits": len(items),
        "total_groups": bundle_contract.total_group_count(items),
        "results": bundle_contract.ordered_items(items, mode=bundle_contract.APS_MODE_BROWSE),
    }
    bundle_payload["bundle_checksum"] = bundle_contract.compute_bundle_checksum(bundle_payload)
    bundle_path = bundle_service.bundle_artifact_path(
        run_id=run_id,
        bundle_id=bundle_id,
        reports_dir=reports_dir,
    )
    _write_json(bundle_path, bundle_payload)

    source_bundle = citation_contract.source_bundle_summary_payload(bundle_payload)
    citation_pack_id = "citation-pack-pagination-route"
    citations = citation_contract.build_citations_from_bundle(bundle_payload)
    citation_payload = {
        "schema_id": citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
        "schema_version": citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
        "generated_at_utc": "2026-06-03T00:00:03Z",
        "citation_pack_id": citation_pack_id,
        "derivation_contract_id": citation_contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
        "source_bundle": source_bundle,
        "total_citations": len(citations),
        "total_groups": len({str(item.get("group_id") or "") for item in citations}),
        "citations": citations,
    }
    citation_payload["citation_pack_checksum"] = citation_contract.compute_citation_pack_checksum(citation_payload)
    citation_path = citation_service.citation_pack_artifact_path(
        run_id=run_id,
        citation_pack_id=citation_pack_id,
        reports_dir=reports_dir,
    )
    _write_json(citation_path, citation_payload)

    evidence_report_id = "evidence-report-pagination-route"
    sections = report_contract.build_sections_from_citation_pack(citation_payload)
    report_payload = {
        "schema_id": report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
        "schema_version": report_contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
        "generated_at_utc": "2026-06-03T00:00:04Z",
        "evidence_report_id": evidence_report_id,
        "assembly_contract_id": report_contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
        "sectioning_contract_id": report_contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
        "source_citation_pack": report_contract.source_citation_pack_summary_payload(citation_payload),
        "total_sections": len(sections),
        "total_citations": len(citations),
        "total_groups": len({str(item.get("group_id") or "") for item in sections}),
        "sections": sections,
    }
    report_payload["evidence_report_checksum"] = report_contract.compute_evidence_report_checksum(report_payload)
    report_path = report_service.evidence_report_artifact_path(
        run_id=run_id,
        evidence_report_id=evidence_report_id,
        reports_dir=reports_dir,
    )
    _write_json(report_path, report_payload)

    return {
        "bundle_id": bundle_id,
        "citation_pack_id": citation_pack_id,
        "evidence_report_id": evidence_report_id,
    }


def test_persisted_artifact_routes_page_existing_ids_and_reject_invalid_pagination(tmp_path: Path) -> None:
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path)
    try:
        reports_dir = Path(settings.connector_reports_dir)
        ids = _persist_fixture_artifacts(reports_dir)
        client = _client()

        valid_paths = {
            "bundle": f"{settings.api_prefix}/connectors/nrc-adams-aps/evidence-bundles/{ids['bundle_id']}",
            "citation": f"{settings.api_prefix}/connectors/nrc-adams-aps/citation-packs/{ids['citation_pack_id']}",
            "report": f"{settings.api_prefix}/connectors/nrc-adams-aps/evidence-reports/{ids['evidence_report_id']}",
        }
        collection_fields = {"bundle": "items", "citation": "citations", "report": "sections"}
        for artifact_name, path in valid_paths.items():
            response = client.get(path, params={"limit": 1, "offset": 1})
            assert response.status_code == 200
            body = response.json()
            assert body["limit"] == 1
            assert body["offset"] == 1
            assert len(body[collection_fields[artifact_name]]) == 1

        for artifact_name, path in valid_paths.items():
            response = client.get(path, params={"limit": 0})
            assert response.status_code == 422, artifact_name
            assert response.json()["detail"]["code"] == "invalid_limit"

            response = client.get(path, params={"offset": -1})
            assert response.status_code == 422, artifact_name
            assert response.json()["detail"]["code"] == "invalid_offset"
    finally:
        settings.storage_dir = original_storage_dir
