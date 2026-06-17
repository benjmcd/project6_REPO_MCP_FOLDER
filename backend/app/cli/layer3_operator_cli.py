"""Headless operator CLI for the Sublayer 3C golden path.

A thin HTTP client over the Layer 3 analysis-product lifecycle routes.
Designed for testability: all HTTP calls go through an injectable
transport object so tests can inject a TestClient-backed transport.

Usage:
    python -m app.cli.layer3_operator_cli <subcommand> [options] [--base-url URL] [--json]
    python -m app.cli.layer3_operator_cli list-methods
    python -m app.cli.layer3_operator_cli create-working-set \\
        --session-id <sid> --name "My WS" --member material_snapshot:<id>
    python -m app.cli.layer3_operator_cli generate-product \\
        --session-id <sid> --working-set-id <wsid> \\
        --method-id working_set_composition_summary
    python -m app.cli.layer3_operator_cli promote-product \\
        --session-id <sid> --product-id <pid> \\
        --decision-intent promote --decision-reason-code proposed_ready
    python -m app.cli.layer3_operator_cli verify-replay \\
        --session-id <sid> --product-id <pid>
    python -m app.cli.layer3_operator_cli show-lineage \\
        --session-id <sid> --product-id <pid>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from typing import Protocol, Tuple
from urllib.parse import urlencode

# ---------------------------------------------------------------------------
# Route paths
# ---------------------------------------------------------------------------

_API_PREFIX = "/api/v1/layer3"

ROUTE_METHODS = f"{_API_PREFIX}/analysis-product/methods"
ROUTE_WORKING_SET = f"{_API_PREFIX}/working-set"
ROUTE_GENERATE = f"{_API_PREFIX}/analysis-product/generate"
ROUTE_TRANSITION_TEMPLATE = f"{_API_PREFIX}/analysis-product/{{analysis_product_id}}/transition"
ROUTE_REPLAY_VERIFY = f"{_API_PREFIX}/analysis-product/replay-verify"
ROUTE_LINEAGE_TEMPLATE = f"{_API_PREFIX}/analysis-product/{{analysis_product_id}}/lineage"

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
# Subcommand: list-methods
# ---------------------------------------------------------------------------


def cmd_list_methods(args: argparse.Namespace, transport: Transport) -> None:
    headers = _build_auth_headers(args)
    status_code, resp = transport.get(ROUTE_METHODS, headers)

    if status_code not in (200, 201):
        _print_error_and_exit(status_code, resp)

    if args.json:
        print(json.dumps(resp, indent=2, sort_keys=True))
        return

    methods = resp.get("methods") or []
    print("=== analysis-product/methods ===")
    for m in methods:
        print(
            f"  {m.get('method_id'):<42}  "
            f"label={m.get('label')!r}  "
            f"product_kind={m.get('product_kind')}"
        )


# ---------------------------------------------------------------------------
# Subcommand: create-working-set
# ---------------------------------------------------------------------------


def cmd_create_working_set(args: argparse.Namespace, transport: Transport) -> None:
    # Parse member tokens: each is "kind:id"
    members = []
    for token in (args.member or []):
        if ":" not in token:
            print(
                f"ERROR: --member value {token!r} must be in the form ref_kind:ref_id",
                file=sys.stderr,
            )
            sys.exit(1)
        ref_kind, ref_id = token.split(":", 1)
        if not ref_kind or not ref_id:
            print(
                f"ERROR: --member value {token!r}: both ref_kind and ref_id must be non-empty",
                file=sys.stderr,
            )
            sys.exit(1)
        members.append({"ref_kind": ref_kind, "ref_id": ref_id})

    if not members:
        print("ERROR: at least one --member ref_kind:ref_id is required", file=sys.stderr)
        sys.exit(1)

    client_request_id = (args.client_request_id or "").strip() or _new_client_request_id("ws")

    body: dict = {
        "session_id": args.session_id,
        "client_request_id": client_request_id,
        "name": args.name,
        "members": members,
    }

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_WORKING_SET, body, headers)

    if status_code not in (200, 201):
        _print_error_and_exit(status_code, resp)

    if args.json:
        print(json.dumps(resp, indent=2, sort_keys=True))
        return

    print("=== working-set: OK ===")
    print(f"  working_set_id : {resp.get('working_set_id')}")
    print(f"  member_count   : {resp.get('member_count')}")
    print(f"  basis_hash     : {resp.get('basis_hash')}")
    print(f"  replayed       : {resp.get('replayed')}")


# ---------------------------------------------------------------------------
# Subcommand: generate-product
# ---------------------------------------------------------------------------


def cmd_generate_product(args: argparse.Namespace, transport: Transport) -> None:
    client_request_id = (args.client_request_id or "").strip() or _new_client_request_id("gen")

    body: dict = {
        "session_id": args.session_id,
        "client_request_id": client_request_id,
        "working_set_id": args.working_set_id,
        "method_id": args.method_id,
    }

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_GENERATE, body, headers)

    if status_code not in (200, 201):
        _print_error_and_exit(status_code, resp)

    if args.json:
        print(json.dumps(resp, indent=2, sort_keys=True))
        return

    print("=== analysis-product/generate: OK ===")
    print(f"  analysis_product_id : {resp.get('analysis_product_id')}")
    print(f"  method_id           : {resp.get('method_id')}")
    print(f"  method_version      : {resp.get('method_version')}")
    print(f"  lifecycle_status    : {resp.get('lifecycle_status')}")
    print(f"  replayed            : {resp.get('replayed')}")


# ---------------------------------------------------------------------------
# Subcommand: promote-product
# ---------------------------------------------------------------------------


def cmd_promote_product(args: argparse.Namespace, transport: Transport) -> None:
    client_request_id = (args.client_request_id or "").strip() or _new_client_request_id("promote")

    body: dict = {
        "session_id": args.session_id,
        "client_request_id": client_request_id,
        "decision_intent": args.decision_intent,
        "decision_reason_code": args.decision_reason_code,
    }
    if args.decision_notes:
        body["decision_notes"] = args.decision_notes

    path = ROUTE_TRANSITION_TEMPLATE.format(analysis_product_id=args.product_id)
    headers = _build_auth_headers(args)
    status_code, resp = transport.post(path, body, headers)

    if status_code not in (200, 201):
        _print_error_and_exit(status_code, resp)

    if args.json:
        print(json.dumps(resp, indent=2, sort_keys=True))
        return

    print("=== analysis-product/transition: OK ===")
    print(f"  analysis_product_id : {resp.get('analysis_product_id')}")
    print(f"  lifecycle_status    : {resp.get('lifecycle_status')}")
    print(f"  review_decision     : {resp.get('review_decision')}")
    print(f"  decision_reason_code: {resp.get('decision_reason_code')}")
    print(f"  from_status         : {resp.get('from_status')}")


# ---------------------------------------------------------------------------
# Subcommand: verify-replay
# ---------------------------------------------------------------------------


def cmd_verify_replay(args: argparse.Namespace, transport: Transport) -> None:
    body: dict = {
        "session_id": args.session_id,
        "analysis_product_id": args.product_id,
    }

    headers = _build_auth_headers(args)
    status_code, resp = transport.post(ROUTE_REPLAY_VERIFY, body, headers)

    if status_code not in (200, 201):
        _print_error_and_exit(status_code, resp)

    if args.json:
        print(json.dumps(resp, indent=2, sort_keys=True))
        return

    print("=== analysis-product/replay-verify: OK ===")
    print(f"  analysis_product_id : {resp.get('analysis_product_id')}")
    print(f"  reproduced          : {resp.get('reproduced')}")
    print(f"  classification      : {resp.get('classification')}")
    print(f"  method_present      : {resp.get('method_present')}")
    print(f"  method_version_match: {resp.get('method_version_match')}")
    print(f"  input_basis_match   : {resp.get('input_basis_match')}")
    print(f"  result_match        : {resp.get('result_match')}")


# ---------------------------------------------------------------------------
# Subcommand: show-lineage
# ---------------------------------------------------------------------------


def cmd_show_lineage(args: argparse.Namespace, transport: Transport) -> None:
    path = (
        ROUTE_LINEAGE_TEMPLATE.format(analysis_product_id=args.product_id)
        + "?"
        + urlencode({"session_id": args.session_id})
    )
    headers = _build_auth_headers(args)
    status_code, resp = transport.get(path, headers)

    if status_code not in (200, 201):
        _print_error_and_exit(status_code, resp)

    if args.json:
        print(json.dumps(resp, indent=2, sort_keys=True))
        return

    review_trail = resp.get("review_trail") or []
    pkg = resp.get("package") or {}
    print("=== analysis-product/lineage: OK ===")
    print(f"  analysis_product_id     : {resp.get('analysis_product_id')}")
    print(f"  working_set_linked      : {resp.get('working_set_linked')}")
    product = resp.get("product") or {}
    print(f"  lifecycle_status        : {product.get('lifecycle_status')}")
    print(f"  review_trail length     : {len(review_trail)}")
    pkg_eligible = pkg.get("package_eligible") if pkg else None
    print(f"  package_eligible        : {pkg_eligible}")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Deferred: package-preview needs material_preview_id, analysis_plan_id, pass_run_id,
# preview_id, preview_hash, and package context; out of golden-path CLI v0 scope.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="layer3_operator_cli",
        description=(
            "Headless operator CLI for the Sublayer 3C golden path. "
            "Thin HTTP client over existing Layer 3 analysis-product routes."
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON response instead of human summary",
    )

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # -- list-methods --
    sub.add_parser(
        "list-methods",
        help="List available deterministic analysis-product methods.",
    )

    # -- create-working-set --
    p_ws = sub.add_parser(
        "create-working-set",
        help="Create a new working set for a session.",
    )
    p_ws.add_argument("--session-id", required=True, metavar="SID")
    p_ws.add_argument("--name", required=True, metavar="NAME")
    p_ws.add_argument(
        "--member",
        dest="member",
        action="append",
        metavar="REF_KIND:REF_ID",
        help=(
            "Working-set member in the form ref_kind:ref_id "
            "(e.g. material_snapshot:<id>). Repeatable; at least one required."
        ),
    )
    p_ws.add_argument(
        "--client-request-id",
        default="",
        metavar="ID",
        help="Idempotency key (auto-generated if omitted)",
    )

    # -- generate-product --
    p_gen = sub.add_parser(
        "generate-product",
        help="Generate a deterministic analysis product for a working set.",
    )
    p_gen.add_argument("--session-id", required=True, metavar="SID")
    p_gen.add_argument("--working-set-id", required=True, metavar="WSID")
    p_gen.add_argument("--method-id", required=True, metavar="METHOD")
    p_gen.add_argument(
        "--client-request-id",
        default="",
        metavar="ID",
        help="Idempotency key (auto-generated if omitted)",
    )

    # -- promote-product --
    p_promote = sub.add_parser(
        "promote-product",
        help="Transition an analysis product lifecycle status (promote / archive / etc.).",
    )
    p_promote.add_argument("--session-id", required=True, metavar="SID")
    p_promote.add_argument("--product-id", required=True, metavar="PID")
    p_promote.add_argument("--decision-intent", required=True, metavar="INTENT")
    p_promote.add_argument("--decision-reason-code", required=True, metavar="CODE")
    p_promote.add_argument(
        "--decision-notes",
        default="",
        metavar="TEXT",
        help="Optional free-text notes attached to the decision",
    )
    p_promote.add_argument(
        "--client-request-id",
        default="",
        metavar="ID",
        help="Idempotency key (auto-generated if omitted)",
    )

    # -- verify-replay --
    p_replay = sub.add_parser(
        "verify-replay",
        help="Verify that a deterministic analysis product is reproducible.",
    )
    p_replay.add_argument("--session-id", required=True, metavar="SID")
    p_replay.add_argument("--product-id", required=True, metavar="PID")

    # -- show-lineage --
    p_lineage = sub.add_parser(
        "show-lineage",
        help="Show the full lineage of an analysis product.",
    )
    p_lineage.add_argument("--session-id", required=True, metavar="SID")
    p_lineage.add_argument("--product-id", required=True, metavar="PID")

    return parser


# ---------------------------------------------------------------------------
# run() — entry point for tests and main()
# ---------------------------------------------------------------------------

_SUBCOMMAND_MAP = {
    "list-methods": cmd_list_methods,
    "create-working-set": cmd_create_working_set,
    "generate-product": cmd_generate_product,
    "promote-product": cmd_promote_product,
    "verify-replay": cmd_verify_replay,
    "show-lineage": cmd_show_lineage,
}


def run(argv: list[str] | None, transport: Transport) -> None:
    """Parse argv and dispatch to the appropriate subcommand handler."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _SUBCOMMAND_MAP[args.subcommand]
    handler(args, transport)


def main() -> None:
    # Resolve --base-url with a minimal pre-parser that has no required
    # subcommand, so a bare `--base-url ...` does not SystemExit here; run()
    # then does the authoritative parse (and reports a missing subcommand).
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument(
        "--base-url",
        default=os.environ.get("LAYER3_API_BASE_URL", "http://127.0.0.1:8000"),
    )
    known, _ = pre.parse_known_args()
    transport = RequestsTransport(known.base_url)
    run(sys.argv[1:], transport)


if __name__ == "__main__":
    main()
