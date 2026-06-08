"""SEC/XBRL Layer 3 operator-review lifecycle CLI.

A thin HTTP client over the existing Layer 3 operator-review routes.
Designed for testability: all HTTP calls go through an injectable
transport object so tests can inject a TestClient-backed transport.

Usage:
    python -m app.cli.sec_xbrl_operator_cli --help
    python -m app.cli.sec_xbrl_operator_cli open --ticker AAPL --confirm
    python -m app.cli.sec_xbrl_operator_cli status --workflow-id <id>
    python -m app.cli.sec_xbrl_operator_cli decide --workflow-id <id> \\
        --workflow-basis-hash <hash> --review-decision approved \\
        --reason-code ready_for_next_freeze
    python -m app.cli.sec_xbrl_operator_cli prepare-authority \\
        --decision-id <id> --decision-basis-hash <hash>
    python -m app.cli.sec_xbrl_operator_cli reveal \\
        --authority-receipt-id <id> --authority-basis-hash <hash> --confirm
    python -m app.cli.sec_xbrl_operator_cli reveal-status --receipt-id <id>
    python -m app.cli.sec_xbrl_operator_cli run-pipeline --ticker AAPL \\
        --decision approved --reason-code ready_for_next_freeze --confirm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from typing import Protocol, Tuple

# ---------------------------------------------------------------------------
# CIK reference map (sourced verbatim from the acquisition connector)
# ---------------------------------------------------------------------------

REAL_COMPANY_CIK_REFS: dict[str, str] = {
    "MSFT": "789019",
    "STLD": "1022671",
    "SONY": "313838",
    "CCJ": "1009001",
    "JPM": "19617",
    "MET": "1099219",
    "PLD": "1045609",
    "FIZZ": "69891",
    "XOM": "34088",
    "PFE": "78003",
    "UAL": "100517",
    "T": "732717",
    "AAPL": "320193",
    "NVDA": "1045810",
    "AMZN": "1018724",
    "TSLA": "1318605",
}

# ---------------------------------------------------------------------------
# Route paths
# ---------------------------------------------------------------------------

_API_PREFIX = "/api/v1/layer3"

ROUTE_OPEN = f"{_API_PREFIX}/sec-xbrl/operator-review/workflow/open-full-pipeline"
ROUTE_STATUS = f"{_API_PREFIX}/sec-xbrl/operator-review/workflow/status"
ROUTE_DECIDE = f"{_API_PREFIX}/sec-xbrl/operator-review/workflow/decision/submit"
ROUTE_PREPARE_AUTHORITY = f"{_API_PREFIX}/sec-xbrl/value-reveal/authority/prepare"
ROUTE_REVEAL_SUBMIT = f"{_API_PREFIX}/sec-xbrl/value-reveal/submit"
ROUTE_REVEAL_STATUS_TEMPLATE = f"{_API_PREFIX}/sec-xbrl/value-reveal/submit/status/{{receipt_id}}"
ROUTE_POSTURE = f"{_API_PREFIX}/sec-xbrl/runtime/posture"

# ---------------------------------------------------------------------------
# Exact literal/mode values read from the request models
# ---------------------------------------------------------------------------

STATUS_MODE = "sec_xbrl_operator_review_workflow_status_v1"
STATUS_OPERATOR_DECISION = "inspect_sec_xbrl_operator_review_workflow_status"

DECISION_SUBMIT_MODE = "sec_xbrl_operator_review_decision_submit_v1"
DECISION_OPERATOR_DECISION = "submit_sec_xbrl_operator_review_decision"

AUTHORITY_MODE = "sec_xbrl_value_reveal_authority_receipt_v1"
AUTHORITY_OPERATOR_DECISION = "prepare_sec_xbrl_value_reveal_authority"

REVEAL_SUBMIT_MODE = "sec_xbrl_controlled_value_reveal_submit_v1"
REVEAL_OPERATOR_DECISION = "submit_explicit_sec_xbrl_value_reveal_from_authority_receipt"

VALID_REVIEW_DECISIONS = ("approved", "changes_requested", "rejected", "blocked")
# run-pipeline only supports decisions that can reach the reveal step
_PIPELINE_VALID_DECISIONS = ("approved",)
VALID_REASON_CODES = (
    "ready_for_next_freeze",
    "needs_packet_revision",
    "authority_gap",
    "redaction_gap",
    "operator_blocked",
)

# ---------------------------------------------------------------------------
# Transport protocol
# ---------------------------------------------------------------------------


class Transport(Protocol):
    """Injectable HTTP transport interface."""

    def post(self, path: str, json_body: dict, headers: dict) -> Tuple[int, dict]:
        ...

    def get(self, path: str, headers: dict) -> Tuple[int, dict]:
        ...


# ---------------------------------------------------------------------------
# Default transport using requests
# ---------------------------------------------------------------------------


class RequestsTransport:
    """Default transport backed by the requests library."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def post(self, path: str, json_body: dict, headers: dict) -> Tuple[int, dict]:
        import requests  # local import — available in requirements.txt

        url = self._base_url + path
        try:
            resp = requests.post(url, json=json_body, headers=headers, timeout=60)
        except requests.exceptions.RequestException as exc:
            # Network/connection failure → governed sentinel (status 0) so the handler
            # prints a clean error and exits nonzero rather than dumping a traceback.
            return 0, {"error_code": "transport_error", "message": f"request failed: {exc}"}
        try:
            body = resp.json()
        except Exception:
            body = {"_raw": resp.text}
        return resp.status_code, body

    def get(self, path: str, headers: dict) -> Tuple[int, dict]:
        import requests

        url = self._base_url + path
        try:
            resp = requests.get(url, headers=headers, timeout=60)
        except requests.exceptions.RequestException as exc:
            return 0, {"error_code": "transport_error", "message": f"request failed: {exc}"}
        try:
            body = resp.json()
        except Exception:
            body = {"_raw": resp.text}
        return resp.status_code, body


# ---------------------------------------------------------------------------
# Auth header helpers
# ---------------------------------------------------------------------------

# These header names match settings.proxy_identity_header / proxy_groups_header defaults.
# Override via --identity / --groups or env vars PROXY_IDENTITY_HEADER_NAME / PROXY_GROUPS_HEADER_NAME
# if non-default header names are in use.

_DEFAULT_IDENTITY_HEADER = "X-Forwarded-User"
_DEFAULT_GROUPS_HEADER = "X-Forwarded-Groups"


def _build_auth_headers(args: argparse.Namespace) -> dict:
    headers: dict = {}
    identity = getattr(args, "identity", None) or os.environ.get("LAYER3_OPERATOR_IDENTITY", "")
    groups = getattr(args, "groups", None) or os.environ.get("LAYER3_OPERATOR_GROUPS", "")
    identity_header = os.environ.get("PROXY_IDENTITY_HEADER_NAME", _DEFAULT_IDENTITY_HEADER)
    groups_header = os.environ.get("PROXY_GROUPS_HEADER_NAME", _DEFAULT_GROUPS_HEADER)
    if identity:
        headers[identity_header] = identity
    if groups:
        headers[groups_header] = groups
    return headers


def _new_client_request_id(prefix: str = "cli") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


# ---------------------------------------------------------------------------
# Response printing helpers
# ---------------------------------------------------------------------------


def _print_error_and_exit(status_code: int, body: dict) -> None:
    error_code = body.get("error_code") or body.get("error") or "(no error_code)"
    message = body.get("message") or body.get("detail") or json.dumps(body)
    print(f"ERROR {status_code}: {error_code}", file=sys.stderr)
    print(f"  {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommand: open
# ---------------------------------------------------------------------------


def cmd_open(args: argparse.Namespace, transport: Transport) -> None:
    # --confirm gate: REQUIRED before any live-acquisition call
    if not args.confirm:
        print(
            "ERROR: --confirm is required for 'open'. This subcommand triggers a live SEC "
            "acquisition and opens an operator-review workflow. Re-run with --confirm to proceed.",
            file=sys.stderr,
        )
        sys.exit(1)

    ticker = args.ticker.upper()

    # Resolve CIK. Zero-strip the operator-supplied --cik to the SEC canonical form the
    # server uses (so "0000320193" and "320193" are equivalent and the cross-check matches).
    if args.cik:
        resolved_cik = args.cik.strip().lstrip("0") or args.cik.strip()
        if ticker in REAL_COMPANY_CIK_REFS and REAL_COMPANY_CIK_REFS[ticker] != resolved_cik:
            print(
                f"WARNING: --cik {args.cik!r} does not match the known CIK for {ticker} "
                f"({REAL_COMPANY_CIK_REFS[ticker]}). Proceeding with supplied --cik; "
                "the server will cross-check.",
                file=sys.stderr,
            )
    else:
        if ticker not in REAL_COMPANY_CIK_REFS:
            known = ", ".join(sorted(REAL_COMPANY_CIK_REFS))
            print(
                f"ERROR: Ticker {ticker!r} is not in the known-company reference list. "
                f"Use --cik to supply a CIK directly, or choose a known ticker: {known}",
                file=sys.stderr,
            )
            sys.exit(1)
        resolved_cik = REAL_COMPANY_CIK_REFS[ticker]

    period_limit = args.period_limit
    if not (1 <= period_limit <= 10):
        print(
            f"ERROR: --period-limit must be between 1 and 10 (got {period_limit}).",
            file=sys.stderr,
        )
        sys.exit(1)

    client_request_id = args.client_request_id or _new_client_request_id("open")

    body = {
        "client_request_id": client_request_id,
        "company_matrix": [ticker],
        "cik": resolved_cik,
        "period_limit": period_limit,
        "require_companyfacts_oracle": args.require_oracle,
        "operator_confirmation": True,
    }

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_OPEN, body, headers)

    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    # Print redacted, human-readable summary — never print the raw resolved_cik
    cv = resp.get("corpus_validation") or {}
    cf = resp.get("companyfacts_stage") or {}
    op = resp.get("operator_review") or {}
    prod = resp.get("production_readiness_claimed", False)

    print("=== open-full-pipeline: OK ===")
    print(f"  status                : {resp.get('status')}")
    print(f"  production_readiness  : {prod}")
    print()
    print("  [corpus_validation]")
    print(f"    validation_receipt_id : {cv.get('validation_receipt_id')}")
    print(f"    connector_hash        : {cv.get('connector_receipt_hash')}")
    print(f"    selected_form_type    : {cv.get('selected_form_type')}")
    print(f"    selected_cik_hash     : {cv.get('selected_cik_hash')}")
    print()
    print("  [companyfacts_stage]")
    print(f"    stage_status          : {cf.get('stage_status') or cf.get('status')}")
    print()
    print("  [operator_review]")
    workflow_id = op.get("sec_xbrl_operator_review_workflow_id")
    workflow_hash = op.get("workflow_basis_hash")
    print(f"    workflow_id           : {workflow_id}")
    print(f"    workflow_basis_hash   : {workflow_hash}")
    print(f"    workflow_status       : {op.get('status')}")
    summary = op.get("summary", {})
    if summary:
        print(f"    summary               : {json.dumps(summary)}")
    print()
    print("  Feed these to 'status' / 'decide':")
    print(f"    --workflow-id {workflow_id}")
    if workflow_hash:
        print(f"    --workflow-basis-hash {workflow_hash}")


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------


def cmd_status(args: argparse.Namespace, transport: Transport) -> None:
    body: dict = {
        "client_request_id": _new_client_request_id("status"),
        "status_mode": STATUS_MODE,
        "operator_decision": STATUS_OPERATOR_DECISION,
    }
    if args.workflow_id:
        body["sec_xbrl_operator_review_workflow_id"] = args.workflow_id
    if args.workflow_basis_hash:
        body["workflow_basis_hash"] = args.workflow_basis_hash

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_STATUS, body, headers)

    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    print("=== workflow/status: OK ===")
    print(f"  workflow_id           : {resp.get('sec_xbrl_operator_review_workflow_id')}")
    print(f"  workflow_status       : {resp.get('status')}")
    print(f"  workflow_basis_hash   : {resp.get('workflow_basis_hash')}")
    decision_status = resp.get("decision_status") or resp.get("review_decision")
    if decision_status:
        print(f"  review_decision       : {decision_status}")


# ---------------------------------------------------------------------------
# Subcommand: decide
# ---------------------------------------------------------------------------


def cmd_decide(args: argparse.Namespace, transport: Transport) -> None:
    # review_decision and reason_code are NEVER defaulted — operator must supply them
    # (argparse 'required=True' enforces this at parse time; we also validate here)
    if not args.review_decision:
        print("ERROR: --review-decision is required for 'decide'.", file=sys.stderr)
        sys.exit(1)
    if not args.reason_code:
        print("ERROR: --reason-code is required for 'decide'.", file=sys.stderr)
        sys.exit(1)

    review_decision: str = args.review_decision
    reason_code: str = args.reason_code

    if review_decision not in VALID_REVIEW_DECISIONS:
        print(
            f"ERROR: --review-decision must be one of: {', '.join(VALID_REVIEW_DECISIONS)}",
            file=sys.stderr,
        )
        sys.exit(1)
    if reason_code not in VALID_REASON_CODES:
        print(
            f"ERROR: --reason-code must be one of: {', '.join(VALID_REASON_CODES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    notes = args.notes
    if review_decision != "approved" and not notes:
        print(
            f"ERROR: --notes is required when --review-decision is '{review_decision}' "
            "(only 'approved' decisions may omit notes).",
            file=sys.stderr,
        )
        sys.exit(1)

    body: dict = {
        "client_request_id": _new_client_request_id("decide"),
        "submit_mode": DECISION_SUBMIT_MODE,
        "operator_decision": DECISION_OPERATOR_DECISION,
        "review_decision": review_decision,
        "decision_reason_code": reason_code,
        "sec_xbrl_operator_review_workflow_id": args.workflow_id,
        "workflow_basis_hash": args.workflow_basis_hash,
    }
    if notes:
        body["decision_notes"] = notes

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_DECIDE, body, headers)

    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    decision_id = resp.get("sec_xbrl_operator_review_decision_id")
    decision_hash = resp.get("decision_basis_hash")

    print("=== decision/submit: OK ===")
    print(f"  decision_id           : {decision_id}")
    print(f"  decision_basis_hash   : {decision_hash}")
    print(f"  review_decision       : {resp.get('review_decision')}")
    print(f"  decision_reason_code  : {resp.get('decision_reason_code')}")
    print(f"  status                : {resp.get('status')}")
    print()
    print("  Feed these to 'prepare-authority':")
    print(f"    --decision-id {decision_id}")
    if decision_hash:
        print(f"    --decision-basis-hash {decision_hash}")


# ---------------------------------------------------------------------------
# Subcommand: prepare-authority
# ---------------------------------------------------------------------------


def cmd_prepare_authority(args: argparse.Namespace, transport: Transport) -> None:
    body: dict = {
        "client_request_id": _new_client_request_id("prepare-auth"),
        "authority_mode": AUTHORITY_MODE,
        "operator_decision": AUTHORITY_OPERATOR_DECISION,
        "sec_xbrl_operator_review_decision_id": args.decision_id,
        "decision_basis_hash": args.decision_basis_hash,
    }
    if args.attestation:
        body["operator_attestation"] = args.attestation

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_PREPARE_AUTHORITY, body, headers)

    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    receipt_id = resp.get("sec_xbrl_value_reveal_authority_receipt_id")
    authority_hash = resp.get("authority_basis_hash")

    print("=== value-reveal/authority/prepare: OK ===")
    print(f"  authority_receipt_id  : {receipt_id}")
    print(f"  authority_basis_hash  : {authority_hash}")
    print(f"  status                : {resp.get('status')}")
    print(f"  value_reveal_performed: {resp.get('value_reveal_performed')}")
    print(f"  production_readiness  : {resp.get('production_readiness_claimed')}")
    print()
    print("  Feed these to 'reveal':")
    print(f"    --authority-receipt-id {receipt_id}")
    if authority_hash:
        print(f"    --authority-basis-hash {authority_hash}")


# ---------------------------------------------------------------------------
# Subcommand: reveal
# ---------------------------------------------------------------------------


def cmd_reveal(args: argparse.Namespace, transport: Transport) -> None:
    # --confirm is REQUIRED — NEVER auto-supply operator_reveal_confirmation
    if not args.confirm:
        print(
            "ERROR: --confirm is required for 'reveal'. This subcommand discloses raw financial "
            "values to the authorized operator. Re-run with --confirm to proceed.",
            file=sys.stderr,
        )
        sys.exit(1)

    body: dict = {
        "client_request_id": _new_client_request_id("reveal"),
        "submit_mode": REVEAL_SUBMIT_MODE,
        "operator_decision": REVEAL_OPERATOR_DECISION,
        "sec_xbrl_value_reveal_authority_receipt_id": args.authority_receipt_id,
        "authority_basis_hash": args.authority_basis_hash,
        "operator_reveal_confirmation": True,
    }
    if args.max_records is not None:
        body["max_records"] = args.max_records

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_REVEAL_SUBMIT, body, headers)

    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    print(
        "WARNING: The following values are raw financial data. They are transient and "
        "sensitive — not persisted by this CLI.",
        file=sys.stderr,
    )
    print("=== value-reveal/submit: OK ===")
    print(f"  receipt_id            : {resp.get('sec_xbrl_controlled_value_reveal_submit_receipt_id')}")
    print(f"  status                : {resp.get('status')}")
    print(f"  production_readiness  : {resp.get('production_readiness_claimed')}")

    revealed_facts = resp.get("revealed_facts") or resp.get("value_records") or []
    if revealed_facts:
        print(f"\n  revealed_facts ({len(revealed_facts)} records):")
        for fact in revealed_facts:
            print(f"    {json.dumps(fact)}")
    else:
        print("\n  (no revealed_facts in response — check feature flag or receipt state)")


# ---------------------------------------------------------------------------
# Subcommand: run-pipeline
# ---------------------------------------------------------------------------


def cmd_run_pipeline(args: argparse.Namespace, transport: Transport) -> None:
    # --confirm gate: REQUIRED — covers both the live SEC acquisition AND value-reveal
    if not args.confirm:
        print(
            "ERROR: --confirm is required for 'run-pipeline'. This subcommand triggers a live "
            "SEC acquisition and discloses raw financial values. Re-run with --confirm to proceed.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Decision and reason-code are NEVER defaulted
    if not args.decision:
        print("ERROR: --decision is required for 'run-pipeline'.", file=sys.stderr)
        sys.exit(1)
    if not args.reason_code:
        print("ERROR: --reason-code is required for 'run-pipeline'.", file=sys.stderr)
        sys.exit(1)

    # Only decisions that can reach value-reveal are valid for run-pipeline.
    # Non-approved decisions (changes_requested, rejected, blocked) would create
    # irreversible open/decide receipts and then fail at prepare-authority.
    if args.decision not in _PIPELINE_VALID_DECISIONS:
        print(
            f"ERROR: --decision '{args.decision}' cannot reach the value-reveal step. "
            f"run-pipeline requires one of: {', '.join(_PIPELINE_VALID_DECISIONS)}. "
            "Use the 'decide' subcommand directly for non-approval decisions.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate max-records before any network call — the API rejects < 1 at the
    # reveal step, which would leave open/decide/authority receipts already committed.
    if args.max_records is not None and args.max_records < 1:
        print(
            f"ERROR: --max-records must be >= 1 (got {args.max_records}).",
            file=sys.stderr,
        )
        sys.exit(1)

    ticker = args.ticker.upper()

    # Resolve CIK — same logic as cmd_open
    if args.cik:
        resolved_cik = args.cik.strip().lstrip("0") or args.cik.strip()
        if ticker in REAL_COMPANY_CIK_REFS and REAL_COMPANY_CIK_REFS[ticker] != resolved_cik:
            print(
                f"WARNING: --cik {args.cik!r} does not match the known CIK for {ticker} "
                f"({REAL_COMPANY_CIK_REFS[ticker]}). Proceeding with supplied --cik; "
                "the server will cross-check.",
                file=sys.stderr,
            )
    else:
        if ticker not in REAL_COMPANY_CIK_REFS:
            known = ", ".join(sorted(REAL_COMPANY_CIK_REFS))
            print(
                f"ERROR: Ticker {ticker!r} is not in the known-company reference list. "
                f"Use --cik to supply a CIK directly, or choose a known ticker: {known}",
                file=sys.stderr,
            )
            sys.exit(1)
        resolved_cik = REAL_COMPANY_CIK_REFS[ticker]

    period_limit = args.period_limit
    if not (1 <= period_limit <= 10):
        print(
            f"ERROR: --period-limit must be between 1 and 10 (got {period_limit}).",
            file=sys.stderr,
        )
        sys.exit(1)

    headers = _build_auth_headers(args)

    # Stable open request-id: use caller-supplied value if present so the
    # operator can retry after a crash before receiving the open response.
    open_request_id = args.open_request_id or _new_client_request_id("run-open")
    print(f"  open_request_id       : {open_request_id}  (use --open-request-id to retry)")

    # ------------------------------------------------------------------
    # Step 1/4: open-full-pipeline
    # ------------------------------------------------------------------
    print("=== run-pipeline [step 1/4]: open-full-pipeline ===")
    open_body: dict = {
        "client_request_id": open_request_id,
        "company_matrix": [ticker],
        "cik": resolved_cik,
        "period_limit": period_limit,
        "require_companyfacts_oracle": args.require_oracle,
        "operator_confirmation": True,
    }
    status_code, open_resp = transport.post(ROUTE_OPEN, open_body, headers)
    if status_code != 200:
        _print_error_and_exit(status_code, open_resp)

    op = open_resp.get("operator_review") or {}
    workflow_id = op.get("sec_xbrl_operator_review_workflow_id")
    workflow_basis_hash = op.get("workflow_basis_hash")
    print(f"  workflow_id           : {workflow_id}")
    print(f"  workflow_basis_hash   : {workflow_basis_hash}")
    print(f"  workflow_status       : {op.get('status')}")

    # ------------------------------------------------------------------
    # Step 2/4: decision/submit
    # ------------------------------------------------------------------
    print("=== run-pipeline [step 2/4]: decision/submit ===")
    decide_body: dict = {
        "client_request_id": _new_client_request_id("run-decide"),
        "submit_mode": DECISION_SUBMIT_MODE,
        "operator_decision": DECISION_OPERATOR_DECISION,
        "review_decision": args.decision,
        "decision_reason_code": args.reason_code,
        "sec_xbrl_operator_review_workflow_id": workflow_id,
        "workflow_basis_hash": workflow_basis_hash,
    }
    if args.notes:
        decide_body["decision_notes"] = args.notes
    status_code, decide_resp = transport.post(ROUTE_DECIDE, decide_body, headers)
    if status_code != 200:
        _print_error_and_exit(status_code, decide_resp)

    decision_id = decide_resp.get("sec_xbrl_operator_review_decision_id")
    decision_basis_hash = decide_resp.get("decision_basis_hash")
    print(f"  decision_id           : {decision_id}")
    print(f"  decision_basis_hash   : {decision_basis_hash}")
    print(f"  review_decision       : {decide_resp.get('review_decision')}")

    # ------------------------------------------------------------------
    # Step 3/4: value-reveal/authority/prepare
    # ------------------------------------------------------------------
    print("=== run-pipeline [step 3/4]: value-reveal/authority/prepare ===")
    prep_body: dict = {
        "client_request_id": _new_client_request_id("run-prep"),
        "authority_mode": AUTHORITY_MODE,
        "operator_decision": AUTHORITY_OPERATOR_DECISION,
        "sec_xbrl_operator_review_decision_id": decision_id,
        "decision_basis_hash": decision_basis_hash,
    }
    if args.attestation:
        prep_body["operator_attestation"] = args.attestation
    status_code, prep_resp = transport.post(ROUTE_PREPARE_AUTHORITY, prep_body, headers)
    if status_code != 200:
        _print_error_and_exit(status_code, prep_resp)

    authority_receipt_id = prep_resp.get("sec_xbrl_value_reveal_authority_receipt_id")
    authority_basis_hash = prep_resp.get("authority_basis_hash")
    print(f"  authority_receipt_id  : {authority_receipt_id}")
    print(f"  authority_basis_hash  : {authority_basis_hash}")
    print(f"  status                : {prep_resp.get('status')}")

    # ------------------------------------------------------------------
    # Step 4/4: value-reveal/submit
    # ------------------------------------------------------------------
    print("=== run-pipeline [step 4/4]: value-reveal/submit ===")
    reveal_body: dict = {
        "client_request_id": _new_client_request_id("run-reveal"),
        "submit_mode": REVEAL_SUBMIT_MODE,
        "operator_decision": REVEAL_OPERATOR_DECISION,
        "sec_xbrl_value_reveal_authority_receipt_id": authority_receipt_id,
        "authority_basis_hash": authority_basis_hash,
        "operator_reveal_confirmation": True,
    }
    if args.max_records is not None:
        reveal_body["max_records"] = args.max_records
    status_code, reveal_resp = transport.post(ROUTE_REVEAL_SUBMIT, reveal_body, headers)
    if status_code != 200:
        _print_error_and_exit(status_code, reveal_resp)

    print(
        "WARNING: The following values are raw financial data. They are transient and "
        "sensitive — not persisted by this CLI.",
        file=sys.stderr,
    )
    revealed_facts = reveal_resp.get("revealed_facts") or reveal_resp.get("value_records") or []
    if revealed_facts:
        print(f"\n  revealed_facts ({len(revealed_facts)} records):")
        for fact in revealed_facts:
            print(f"    {json.dumps(fact)}")
    else:
        print("\n  (no revealed_facts in response — check feature flag or receipt state)")

    print("=== run-pipeline: COMPLETE ===")


# ---------------------------------------------------------------------------
# Subcommand: reveal-status
# ---------------------------------------------------------------------------


def cmd_reveal_status(args: argparse.Namespace, transport: Transport) -> None:
    path = ROUTE_REVEAL_STATUS_TEMPLATE.format(receipt_id=args.receipt_id)
    headers = _build_auth_headers(args)
    status_code, resp = transport.get(path, headers)

    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    print("=== value-reveal/submit/status: OK ===")
    print(f"  receipt_id            : {resp.get('sec_xbrl_controlled_value_reveal_submit_receipt_id')}")
    print(f"  status                : {resp.get('status')}")
    print(f"  submit_basis_hash     : {resp.get('submit_basis_hash')}")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sec_xbrl_operator_cli",
        description=(
            "SEC/XBRL Layer 3 operator-review lifecycle CLI. "
            "Thin HTTP client over existing Layer 3 routes."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LAYER3_API_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL (default: $LAYER3_API_BASE_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--identity",
        default="",
        metavar="USER",
        help="Proxy identity header value (AUTH_OWNER=proxy deployments)",
    )
    parser.add_argument(
        "--groups",
        default="",
        metavar="CSV",
        help="Proxy groups header value (comma-separated)",
    )

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # -- open --
    p_open = sub.add_parser(
        "open",
        help="Open a full-pipeline operator-review workflow (triggers live SEC acquisition).",
    )
    p_open.add_argument("--ticker", required=True, help="Company ticker (e.g. AAPL)")
    p_open.add_argument(
        "--cik",
        default="",
        help="Override CIK (zero-stripped). Required if ticker is not in the known list.",
    )
    p_open.add_argument(
        "--period-limit",
        type=int,
        default=3,
        metavar="N",
        help="Max filings per company (1-10, default 3)",
    )
    p_open.add_argument(
        "--require-oracle",
        action="store_true",
        help="Require CompanyFacts oracle acquisition",
    )
    p_open.add_argument(
        "--confirm",
        action="store_true",
        help="REQUIRED: confirm that this triggers a live SEC acquisition",
    )
    p_open.add_argument(
        "--client-request-id",
        default="",
        metavar="ID",
        help="Idempotency key (auto-generated if omitted)",
    )

    # -- status --
    p_status = sub.add_parser(
        "status",
        help="Inspect operator-review workflow status.",
    )
    p_status.add_argument("--workflow-id", default=None, metavar="ID")
    p_status.add_argument("--workflow-basis-hash", default=None, metavar="HASH")

    # -- decide --
    p_decide = sub.add_parser(
        "decide",
        help="Submit an operator review decision.",
    )
    p_decide.add_argument("--workflow-id", required=True, metavar="ID")
    p_decide.add_argument("--workflow-basis-hash", required=True, metavar="HASH")
    p_decide.add_argument(
        "--review-decision",
        required=True,
        choices=VALID_REVIEW_DECISIONS,
        metavar="DECISION",
        help=f"One of: {', '.join(VALID_REVIEW_DECISIONS)}",
    )
    p_decide.add_argument(
        "--reason-code",
        required=True,
        choices=VALID_REASON_CODES,
        metavar="CODE",
        help=f"One of: {', '.join(VALID_REASON_CODES)}",
    )
    p_decide.add_argument(
        "--notes",
        default="",
        metavar="TEXT",
        help="Decision notes (required when --review-decision != approved)",
    )

    # -- prepare-authority --
    p_prep = sub.add_parser(
        "prepare-authority",
        help="Prepare value-reveal authority receipt (mechanical step after approved decision).",
    )
    p_prep.add_argument("--decision-id", required=True, metavar="ID")
    p_prep.add_argument("--decision-basis-hash", required=True, metavar="HASH")
    p_prep.add_argument("--attestation", default="", metavar="TEXT")

    # -- reveal --
    p_reveal = sub.add_parser(
        "reveal",
        help="Submit controlled value reveal (discloses raw financial values to operator).",
    )
    p_reveal.add_argument("--authority-receipt-id", required=True, metavar="ID")
    p_reveal.add_argument("--authority-basis-hash", required=True, metavar="HASH")
    p_reveal.add_argument(
        "--confirm",
        action="store_true",
        help="REQUIRED: confirm that this discloses raw financial values",
    )
    p_reveal.add_argument(
        "--max-records",
        type=int,
        default=None,
        metavar="N",
        help="Max records to reveal (optional)",
    )

    # -- reveal-status --
    p_revst = sub.add_parser(
        "reveal-status",
        help="Get status of a value-reveal submit receipt.",
    )
    p_revst.add_argument("--receipt-id", required=True, metavar="ID")

    # -- check-posture --
    sub.add_parser(
        "check-posture",
        help=(
            "Print runtime activation state: feature flags, gated capabilities, "
            "and operator next actions. Exit 1 if value-reveal is not enabled."
        ),
    )

    # -- run-pipeline --
    p_pipe = sub.add_parser(
        "run-pipeline",
        help=(
            "Run the full 4-step operator pipeline in one command: "
            "open → decide → prepare-authority → reveal."
        ),
    )
    p_pipe.add_argument("--ticker", required=True, help="Company ticker (e.g. AAPL)")
    p_pipe.add_argument(
        "--cik",
        default="",
        help="Override CIK (zero-stripped). Required if ticker is not in the known list.",
    )
    p_pipe.add_argument(
        "--period-limit",
        type=int,
        default=3,
        metavar="N",
        help="Max filings per company (1-10, default 3)",
    )
    p_pipe.add_argument(
        "--require-oracle",
        action="store_true",
        help="Require CompanyFacts oracle acquisition",
    )
    p_pipe.add_argument(
        "--decision",
        required=True,
        choices=_PIPELINE_VALID_DECISIONS,
        metavar="DECISION",
        help=f"Review decision. Must be: {', '.join(_PIPELINE_VALID_DECISIONS)} (only decisions that can reach value-reveal)",
    )
    p_pipe.add_argument(
        "--reason-code",
        required=True,
        choices=VALID_REASON_CODES,
        metavar="CODE",
        help=f"Reason code. One of: {', '.join(VALID_REASON_CODES)}",
    )
    p_pipe.add_argument(
        "--notes",
        default="",
        metavar="TEXT",
        help="Decision notes (optional for approved; may be required for other decisions)",
    )
    p_pipe.add_argument(
        "--attestation",
        default="",
        metavar="TEXT",
        help="Operator attestation for prepare-authority step (optional)",
    )
    p_pipe.add_argument(
        "--confirm",
        action="store_true",
        help=(
            "REQUIRED: confirms both the live SEC acquisition gate "
            "and the value-reveal gate"
        ),
    )
    p_pipe.add_argument(
        "--max-records",
        type=int,
        default=None,
        metavar="N",
        help="Max records to reveal in the final step (optional, must be >= 1)",
    )
    p_pipe.add_argument(
        "--open-request-id",
        default="",
        metavar="ID",
        help=(
            "Idempotency key for the open step (auto-generated if omitted). "
            "Supply the printed value to retry after a crash before the open response was received."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# run() — entry point for tests and main()
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Subcommand: check-posture
# ---------------------------------------------------------------------------


def cmd_check_posture(args: argparse.Namespace, transport: Transport) -> None:
    """Print runtime activation state; exit 1 if value-reveal is not enabled."""
    headers = _build_auth_headers(args)
    status_code, resp = transport.get(ROUTE_POSTURE, headers)
    if status_code != 200:
        _print_error_and_exit(status_code, resp)

    posture = resp.get("sec_xbrl_runtime_posture") or resp
    posture_state = posture.get("posture_state", "unknown")
    flags = posture.get("runtime_flags") or {}
    next_actions = posture.get("operator_next_actions") or []
    activation_surfaces = posture.get("activation_surfaces") or []

    print(f"=== sec-xbrl runtime posture ===")
    print(f"  posture_state         : {posture_state}")

    print("\n  runtime_flags:")
    _FLAG_LABELS = {
        "live_sec_edgar_network_enabled": "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
        "arelle_internal_value_store_enabled": "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
        "arelle_corpus_validation_enabled": "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
        "arelle_governed_sibling_value_reveal_enabled": "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
        "controlled_value_reveal_submit_enabled": "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    }
    for key, env_var in _FLAG_LABELS.items():
        value = flags.get(key)
        mark = "ON " if value else "OFF"
        print(f"    [{mark}]  {env_var}")

    if activation_surfaces:
        print("\n  activation_surfaces:")
        for surf in activation_surfaces:
            name = surf.get("surface") or surf.get("capability") or str(surf)
            gated = surf.get("gated", False)
            required = surf.get("required_flags") or []
            status_str = "gated" if gated else "available"
            print(f"    {name}: {status_str}")
            for req in required:
                print(f"      requires: {req}")

    if next_actions:
        print("\n  operator_next_actions:")
        for action in next_actions:
            print(f"    - {action}")
    else:
        print("\n  operator_next_actions: (none — path is clear)")

    reveal_enabled = bool(flags.get("controlled_value_reveal_submit_enabled"))
    if not reveal_enabled:
        print(
            "\nWARNING: LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED is OFF. "
            "run-pipeline will be blocked at the reveal step.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------

_SUBCOMMAND_MAP = {
    "open": cmd_open,
    "status": cmd_status,
    "decide": cmd_decide,
    "prepare-authority": cmd_prepare_authority,
    "reveal": cmd_reveal,
    "reveal-status": cmd_reveal_status,
    "run-pipeline": cmd_run_pipeline,
    "check-posture": cmd_check_posture,
}


def run(argv: list[str] | None, transport: Transport) -> None:
    """Parse argv and dispatch to the appropriate subcommand handler."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _SUBCOMMAND_MAP[args.subcommand]
    handler(args, transport)


def main() -> None:
    # Parse known args once to resolve --base-url (handles both "--base-url X" and
    # "--base-url=X"); run() re-parses authoritatively for dispatch.
    parser = build_parser()
    known, _ = parser.parse_known_args()
    transport = RequestsTransport(known.base_url)
    run(sys.argv[1:], transport)


if __name__ == "__main__":
    main()
