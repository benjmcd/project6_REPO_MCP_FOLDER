"""Full-pipeline orchestrator for SEC/XBRL Layer 3 operator review.

Automates the three hand-threaded steps that previously required separate operator calls:
  1. Corpus-validation (live fetch -> Arelle sidecar -> classification -> ownership marker)
  2. CompanyFacts acquire-and-stage (optional, oracle)
  3. Build the open-plan payload so the route can call the staged-evidence open handler directly

All intermediate hashes are threaded internally; the operator never handles a hash.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from app.services import (
    layer3_sec_edgar_real_company_corpus_validation,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_xbrl_companyfacts_acquire_stage,
)

SCHEMA_ID = "layer3.sec_xbrl_full_pipeline_orchestrator.v1"

# Module-level constants pulled from the corpus-validation module so they always match.
VALIDATION_MODE = layer3_sec_edgar_real_company_corpus_validation.VALIDATION_MODE
OPERATOR_DECISION = layer3_sec_edgar_real_company_corpus_validation.OPERATOR_DECISION

DEFAULT_PERIOD_LIMIT = 3


class SecXbrlFullPipelineOrchestratorError(Exception):
    """Typed error raised by the full-pipeline orchestrator.

    Mirrors the shape of SecXbrlOfflineEvidenceLoaderError and SecXbrlE2EOfflineOrchestratorError:
    carries code, message, optional details, and an http_status (default 409).
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        http_status: int = 409,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = dict(details or {})
        self.http_status = http_status


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prepare_full_pipeline_open_plan(
    db: Any,
    *,
    fields: Mapping[str, Any],
    evidence_owner: dict[str, Any],
) -> dict[str, Any]:
    """Run steps 1-2 and return a plan dict ready for the staged-evidence open handler.

    Args:
        db: SQLAlchemy Session (passed through to corpus-validation).
        fields: Operator-supplied inputs (client_request_id, cik, company_matrix, etc.).
        evidence_owner: Server-derived owner stamp from the route's auth policy.

    Returns:
        dict with keys:
          "corpus_validation" — redacted summary of step 1
          "companyfacts_stage" — redacted acquire-and-stage summary or None
          "open_payload" — kwargs for Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceRequest

    Raises:
        SecXbrlFullPipelineOrchestratorError on validation / threading failures.
        Typed errors from corpus-validation or companyfacts services propagate unchanged.

    DB transaction note (intentional, idempotent-replay contract):
        Corpus-validation commits its bridge dataset to ``db`` independently (see
        layer3_sec_edgar_html_inline_xbrl_fact_material_bridge). If a LATER step here
        (cik-hash guard, no-supported-filing, CompanyFacts, or the open step) fails, the
        route's ``db.rollback()`` does NOT undo that already-committed corpus-validation
        work. This is by design: corpus-validation writes idempotent filesystem receipts and
        a same-basis retry short-circuits to the cached receipt without re-committing, so the
        retained rows are valid validated artifacts a retry reuses — not corruption.
    """
    # ------------------------------------------------------------------
    # Step 0: validate operator inputs
    # ------------------------------------------------------------------
    if fields.get("operator_confirmation") is not True:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_missing_operator_confirmation",
            "Full-pipeline orchestration requires operator_confirmation: true.",
            http_status=400,
        )

    client_request_id = str(fields.get("client_request_id") or "").strip()
    if not client_request_id:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_missing_client_request_id",
            "Full-pipeline orchestration requires a non-empty client_request_id.",
            http_status=400,
        )

    # SEC CIKs are at most 10 digits (canonical form is zero-padded to 10). Validate the RAW
    # stripped input BEFORE canonicalizing — checking length after lstrip("0") would let an
    # absurdly zero-padded value such as "00000000000320193" normalize to a valid CIK and
    # slip past the bound into live acquisition/staging side effects.
    raw_cik = str(fields.get("cik") or "").strip()
    if not raw_cik or not raw_cik.isdigit() or len(raw_cik) > 10:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_invalid_cik",
            "Full-pipeline orchestration requires a 1-10 digit cik.",
            http_status=400,
        )
    # Canonicalize to the connector's zero-stripped form: each record's cik_hash is derived
    # from the zero-stripped CIK and CompanyFacts fetch also zero-strips, so hashing/fetching
    # the verbatim padded string would produce a spurious mismatch and inconsistent fetch key.
    cik = raw_cik.lstrip("0")
    if not cik:  # all-zeros input
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_invalid_cik",
            "Full-pipeline orchestration requires a 1-10 digit cik.",
            http_status=400,
        )

    company_matrix = list(fields.get("company_matrix") or [])
    if not company_matrix:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_missing_company_matrix",
            "Full-pipeline orchestration requires a non-empty company_matrix.",
            http_status=400,
        )

    # Reject ticker/CIK pairing mismatches BEFORE corpus-validation so an invalid pair
    # (e.g. company_matrix=["MSFT"] with Apple's CIK) cannot trigger live SEC acquisition /
    # staging or leave orphan receipts for a workflow that can never open. The connector
    # matrix is a fixed ticker->CIK map (zero-stripped values); the supplied (normalized)
    # CIK must belong to at least one requested ticker. (Hashes only in error details.)
    cik_refs = layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_CIK_REFS
    matrix_ciks = {cik_refs.get(str(ticker)) for ticker in company_matrix}
    matrix_ciks.discard(None)
    if cik not in matrix_ciks:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_cik_not_in_company_matrix",
            "The supplied CIK is not represented by any ticker in the requested company_matrix.",
            details={
                "expected_cik_hash": _sha256_hex(cik),
                "matrix_cik_hashes": sorted(_sha256_hex(c) for c in matrix_ciks),
            },
            http_status=409,
        )

    # ------------------------------------------------------------------
    # Step 1: corpus-validation (live fetch -> Arelle -> classification -> marker)
    # ------------------------------------------------------------------
    corpus_fields: dict[str, Any] = {
        "client_request_id": f"{client_request_id}-corpus",
        "validation_mode": VALIDATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "company_matrix": company_matrix,
        "operator_confirmation": True,
    }
    corpus_response = layer3_sec_edgar_real_company_corpus_validation.validate_sec_edgar_real_company_corpus_product_path(
        corpus_fields,
        db,
        evidence_owner=evidence_owner,
    )

    # ------------------------------------------------------------------
    # Step 2: select the primary supported filing record
    # ------------------------------------------------------------------
    all_records: list[dict[str, Any]] = list(corpus_response.get("filing_validation_records") or [])
    supported = [
        r for r in all_records
        if r.get("supported_degraded_blocked") == "supported"
        and r.get("authority_hashes", {}).get("arelle_sidecar_receipt_hash")
    ]
    total_count = len(all_records)
    supported_count = len(supported)

    if not supported:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_no_supported_filing",
            "Corpus validation found no supported filings with Arelle sidecar coverage.",
            details={"total_records": total_count, "supported_count": supported_count},
            http_status=409,
        )

    # ------------------------------------------------------------------
    # Step 3: select the filing matching the supplied CIK, THEN prefer 10-K.
    # A multi-ticker company_matrix yields a record per company; filtering by the
    # caller's CIK first prevents another company's 10-K (appearing earlier in the
    # matrix) from triggering a spurious cik_hash mismatch. This also IS the
    # correctness guard that binds the oracle CIK to the validated filing.
    # ------------------------------------------------------------------
    expected_cik_hash = _sha256_hex(cik)
    cik_matched = [r for r in supported if str(r.get("cik_hash") or "") == expected_cik_hash]
    if not cik_matched:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_cik_hash_mismatch",
            "No supported filing matches the supplied CIK.",
            details={
                "expected_from_cik": expected_cik_hash,
                "supported_count": supported_count,
                "discovered_cik_hashes": sorted(
                    {str(r.get("cik_hash") or "") for r in supported}
                ),
            },
            http_status=409,
        )

    # Prefer an exact "10-K" over a "10-K/A" amendment (substring match alone would pick an
    # amendment listed first); then any 10-K family; then the first CIK-matched record.
    selected = (
        next((r for r in cik_matched if str(r.get("form_type") or "").strip() == "10-K"), None)
        or next((r for r in cik_matched if "10-K" in str(r.get("form_type") or "")), None)
        or cik_matched[0]
    )
    discovered_cik_hash = expected_cik_hash

    # ------------------------------------------------------------------
    # Step 4: extract hashes
    # ------------------------------------------------------------------
    authority_hashes = selected.get("authority_hashes") or {}
    connector_receipt_hash = str(corpus_response.get("connector_receipt_hash") or "")
    # The loader's `expected_sidecar_receipt_hash` parameter is satisfied by the record's
    # `fact_authority_receipt_hash` (NOT `arelle_sidecar_receipt_hash`, even though they hold the
    # same value today). The classification service keys the staged sidecar lookup on
    # fact_authority_receipt_hash; do NOT swap in arelle_sidecar_receipt_hash or the loader
    # resolution would break. Verified against the loader contract and live_oracle_chain.py.
    sidecar_param_hash = str(authority_hashes.get("fact_authority_receipt_hash") or "")
    classification_hash = str(authority_hashes.get("statement_classification_receipt_hash") or "")
    cik_hash = discovered_cik_hash

    # Defense-in-depth: the supported filter gates on arelle_sidecar_receipt_hash, but the open
    # step consumes these two hashes. If either is empty, building the open request model would
    # raise an UNcaught Pydantic ValidationError -> ungoverned 500. Fail closed with a governed
    # error instead. (Not reachable on the live path — a real supported record co-populates all
    # three — but the orchestrator must not trust an invariant it can cheaply assert.)
    if not sidecar_param_hash or not classification_hash:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_incomplete_authority_hashes",
            "Selected supported filing is missing required authority hashes for the open step.",
            details={
                "has_fact_authority_receipt_hash": bool(sidecar_param_hash),
                "has_statement_classification_receipt_hash": bool(classification_hash),
            },
            http_status=409,
        )

    # ------------------------------------------------------------------
    # Step 5: optional CompanyFacts oracle acquire-and-stage
    # ------------------------------------------------------------------
    companyfacts_summary: dict[str, Any] | None = None
    require_oracle = bool(fields.get("require_companyfacts_oracle"))
    if require_oracle:
        cf_result = layer3_sec_xbrl_companyfacts_acquire_stage.acquire_and_stage_companyfacts(
            client_request_id=f"{client_request_id}-cf",
            cik=cik,
            connector_receipt_hash=connector_receipt_hash,
            operator_confirmation=True,
        )
        companyfacts_summary = {
            "status": cf_result.get("status"),
            "acquire_cik_hash": (cf_result.get("acquire") or {}).get("cik_hash"),
            "acquire_observation_count": (cf_result.get("acquire") or {}).get("companyfacts_observation_count"),
            "stage_receipt_id": (cf_result.get("stage") or {}).get("companyfacts_receipt_id"),
        }

    # ------------------------------------------------------------------
    # Step 6: build redacted corpus_validation summary (no raw CIK, no raw values)
    # ------------------------------------------------------------------
    corpus_summary = {
        "validation_receipt_id": corpus_response.get("validation_receipt_id"),
        "validation_receipt_hash": corpus_response.get("validation_receipt_hash"),
        "supported_count": supported_count,
        "selected_form_type": str(selected.get("form_type") or ""),
        "selected_cik_hash": cik_hash,
        "connector_receipt_hash": connector_receipt_hash,
    }

    # ------------------------------------------------------------------
    # Step 7: return plan
    # ------------------------------------------------------------------
    # Validate explicitly (rather than `or`-coercing falsy to default) so direct service
    # callers get the SAME 1-10 bound the route's Pydantic model applies (ge=1, le=10), and
    # a non-numeric value yields a governed 400 instead of an uncaught ValueError.
    period_limit_raw = fields.get("period_limit")
    if period_limit_raw is None:
        period_limit = DEFAULT_PERIOD_LIMIT
    else:
        try:
            period_limit = int(period_limit_raw)
        except (TypeError, ValueError):
            raise SecXbrlFullPipelineOrchestratorError(
                "full_pipeline_invalid_period_limit",
                "period_limit must be an integer between 1 and 10.",
                http_status=400,
            )
    if period_limit < 1 or period_limit > 10:
        raise SecXbrlFullPipelineOrchestratorError(
            "full_pipeline_invalid_period_limit",
            "period_limit must be between 1 and 10.",
            http_status=400,
        )

    return {
        "corpus_validation": corpus_summary,
        "companyfacts_stage": companyfacts_summary,
        "open_payload": {
            "client_request_id": f"{client_request_id}-open",
            "expected_sidecar_receipt_hash": sidecar_param_hash,
            "expected_statement_classification_receipt_hash": classification_hash,
            "connector_receipt_hash": connector_receipt_hash,
            "cik_hash": cik_hash,
            "period_limit": period_limit,
            "require_companyfacts_oracle": require_oracle,
        },
    }
