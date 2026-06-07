"""Orchestration: acquire a live SEC CompanyFacts artifact then stage it for evidence use.

This module calls the live-fetch service (layer3_sec_edgar_live_source_artifact) and the
staging service (layer3_sec_xbrl_offline_companyfacts_stage) in sequence.  Raw values are
held in-memory only for the duration of the call and are NEVER returned, logged, or persisted
outside the gitignored raw store that the staging service manages.

Import topology (no cycle):
  this module  →  layer3_sec_edgar_live_source_artifact  (does NOT import this module)
  this module  →  layer3_sec_xbrl_offline_companyfacts_stage  (does NOT import this module)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.layer3_response_contract import base_response
from app.services.layer3_sec_edgar_live_source_artifact import (
    acquire_sec_edgar_companyfacts_live_artifact,
)
from app.services.layer3_sec_xbrl_offline_companyfacts_stage import (
    load_staged_companyfacts_raw,
    stage_sec_xbrl_companyfacts,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError

SCHEMA_ID = "layer3.sec_xbrl_companyfacts_acquire_stage.v1"


def acquire_and_stage_companyfacts(
    *,
    client_request_id: str,
    cik: str,
    connector_receipt_hash: str,
    operator_confirmation: bool,
    storage_dir: str | None = None,
    **_ignored: Any,
) -> dict[str, Any]:
    """Acquire a live SEC CompanyFacts JSON and stage it for offline evidence use.

    Steps:
    1. Call the live-fetch gate (acquire_sec_edgar_companyfacts_live_artifact) which writes
       the raw artifact to the gitignored store and returns a REDACTED receipt dict.
    2. Read the raw artifact in-memory via load_staged_companyfacts_raw using the receipt id
       from step 1.  The raw dict is NEVER returned or logged.
    3. Stage it (stage_sec_xbrl_companyfacts) bound to the supplied connector_receipt_hash.
    4. Return only redacted data — no raw CIK, no raw values, no facts object.

    Typed errors propagate to the caller for governed mapping:
    - Layer3WorkbenchError from the acquire step (operator_confirmation gate, CI gate, etc.)
    - SecXbrlCompanyfactsStageError from the stage step (cik_not_in_connector, conflict, etc.)
    """
    storage = Path(storage_dir or settings.storage_dir)

    # Step 1: live fetch — returns REDACTED dict only (no raw CIK/values)
    fetch = acquire_sec_edgar_companyfacts_live_artifact(
        {
            "client_request_id": client_request_id,
            "cik": cik,
            "operator_confirmation": operator_confirmation,
        }
    )

    # Step 1b: validate acquire contract — both keys must be present and non-empty
    _receipt_id = fetch.get("companyfacts_receipt_id") or ""
    _content_sha = fetch.get("content_sha256") or ""
    if not _receipt_id or not _content_sha:
        raise Layer3WorkbenchError(
            "sec_xbrl_companyfacts_acquire_stage_acquire_contract_violation",
            "acquire returned missing or empty companyfacts_receipt_id or content_sha256",
            http_status=409,
        )

    # Step 2: read raw artifact in-memory for staging — NEVER returned
    raw = load_staged_companyfacts_raw(
        storage,
        companyfacts_receipt_id=_receipt_id,
    )

    # Step 3: stage against the connector corpus — returns REDACTED stage receipt
    stage = stage_sec_xbrl_companyfacts(
        companyfacts=raw,
        cik=cik,
        connector_receipt_hash=connector_receipt_hash,
        content_sha256=_content_sha,
        storage_dir=storage,
    )

    # Step 4: return only redacted envelope via base_response (sets schema_version/request_id/server_time)
    return {
        **base_response(SCHEMA_ID, request_id=client_request_id, status="companyfacts_acquired_and_staged"),
        "acquire": fetch,
        "stage": stage,
    }
