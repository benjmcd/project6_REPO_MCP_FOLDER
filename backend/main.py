from __future__ import annotations

import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect as sa_inspect, text

from app._version import BUILD_INFO
from app.api.router import api_router
from app.core.config import bootstrap_storage_tree, settings
from app.core.observability import RequestIdMiddleware, setup_logging, unhandled_exception_handler
from app.db.session import Base, engine, SessionLocal
from app.services import layer3_sec_xbrl_in_app_auth_policy
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response


def _run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    existing_tables = set(sa_inspect(engine).get_table_names())
    if "alembic_version" not in existing_tables and "connector_run" in existing_tables:
        command.stamp(cfg, "head")
        return
    command.upgrade(cfg, "head")


def _initialize_database() -> None:
    mode = settings.db_init_mode
    if mode == "none":
        return
    if mode == "create_all":
        Base.metadata.create_all(bind=engine)
        return
    _run_migrations()


_initialize_database()

setup_logging()

app = FastAPI(title=settings.app_name, version=BUILD_INFO["version"])

# Observability: request-id propagation (CORS, added after, wraps this middleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=settings.cors_allow_credentials_enabled,
    allow_methods=['*'],
    allow_headers=['*'],
)
# Global handler for unhandled exceptions — returns bounded 500, logs traceback
app.add_exception_handler(Exception, unhandled_exception_handler)


_REQUIRED_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES = {
    f"{settings.api_prefix.rstrip('/')}/analysis-runs": "write",
    f"{settings.api_prefix.rstrip('/')}/layer3/source/intake/upload": "write",
    f"{settings.api_prefix.rstrip('/')}/layer3/sec-xbrl/operator-review/workflow/status": "read",
}

# ---------------------------------------------------------------------------
# Static registry of protected POST routes for pre-body operator authorization.
#
# This dict is computed ONCE at import time from the known handler set — no
# runtime source inspection, no app.router.routes iteration, no import-order
# dependency.  Parametrized paths are stored in the companion PATTERNS tuple.
#
# To update: search the layer3 API handlers for _route_level_operator_identity
# or _sec_xbrl_policy_decision calls; derive access from the access= kwarg or
# the route_family name (_write -> "write", _read -> "read").  Layer3 routes
# carry the /layer3 sub-prefix; legacy API routes do not.
# ---------------------------------------------------------------------------

def _build_static_pre_body_routes(
    prefix: str,
) -> tuple[dict[str, str], tuple[tuple[re.Pattern[str], str, str], ...]]:
    """Return (exact_dict, patterns_tuple) from the hardcoded route registry."""
    p = prefix.rstrip("/")
    L = p + "/layer3"

    # Exact (non-parametrized) routes — (full_path, access)
    _exact: list[tuple[str, str]] = [
        # --- layer3/__init__.py ---
        (f"{L}/preflight", "read"),
        (f"{L}/source-preview", "read"),
        (f"{L}/material-preview", "read"),
        (f"{L}/gate-b/decision", "write"),
        (f"{L}/gate-c/preview", "write"),
        (f"{L}/gate-c/override", "read"),
        (f"{L}/plan/preview", "read"),
        (f"{L}/plan/approve", "write"),
        (f"{L}/plan/approved/cancel", "write"),
        (f"{L}/plan/revise", "write"),
        (f"{L}/plan/revision/recover", "write"),
        (f"{L}/execution/select", "write"),
        (f"{L}/execution/start", "write"),
        (f"{L}/execution/result/status", "read"),
        (f"{L}/execution/result/public-values", "read"),
        (f"{L}/execution/result/review", "write"),
        (f"{L}/analysis-product/draft", "write"),
        (f"{L}/working-set", "write"),
        (f"{L}/analysis-product/generate", "write"),
        (f"{L}/analysis-product/replay-verify", "read"),
        # --- layer3/handoff.py ---
        (f"{L}/handoff/export/prepare", "write"),
        (f"{L}/handoff/aps/dispatch", "write"),
        (f"{L}/handoff/export/download/readiness", "write"),
        (f"{L}/handoff/export/download/prepare", "write"),
        (f"{L}/handoff/connector/dataset", "write"),
        (f"{L}/handoff/connector/record", "write"),
        (f"{L}/handoff/connector/local-destination/receipt", "write"),
        (f"{L}/handoff/connector/local-outbox/fake-target", "write"),
        (f"{L}/handoff/connector/local-outbox/write", "write"),
        (f"{L}/handoff/connector/local-outbox/provider-private/prepare", "write"),
        (f"{L}/handoff/connector/local-outbox/external-local-export/write", "write"),
        (f"{L}/handoff/export/internal-webhook/dispatch", "write"),
        (f"{L}/handoff/export/download/signed-reference/generate", "write"),
        (f"{L}/handoff/export/download/provider-private-signed-url/prepare", "write"),
        (f"{L}/handoff/export/download/provider-private-signed-url/revoke", "write"),
        (f"{L}/handoff/export/download/provider-public-url/prepare", "write"),
        (f"{L}/handoff/export/download/provider-public-url/revoke", "write"),
        (f"{L}/handoff/export/download/provider-public-url/use", "read"),
        (f"{L}/handoff/export/download/deliver", "write"),
        (f"{L}/handoff/export/download/signed-reference/use", "write"),
        # --- layer3/package.py ---
        (f"{L}/package/review/preview", "write"),
        (f"{L}/package/review/commit", "write"),
        (f"{L}/package/review/submit", "write"),
        (f"{L}/package/mutation/preview", "write"),
        (f"{L}/package/replacement-artifact/materialize", "write"),
        (f"{L}/package/replacement-set/record", "write"),
        (f"{L}/package/replacement-set/record-from-corrected-artifact-set", "write"),
        (f"{L}/package/supersession/commit", "write"),
        (f"{L}/package/supersession/commit-from-corrected-artifact-set-authority", "write"),
        (f"{L}/package/replacement-artifact/manifest/record", "write"),
        (f"{L}/package/replacement-artifact/manifest/record-from-authority", "write"),
        (f"{L}/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority", "write"),
        (f"{L}/package/corrected-artifact-set/record", "write"),
        (f"{L}/package/replacement-namespace/record", "write"),
        (f"{L}/package/replacement-namespace/record-from-corrected-artifact-manifest-authority", "write"),
        (f"{L}/package/replacement-activation/commit", "write"),
        # --- layer3/source_ingestion.py ---
        (f"{L}/source/intake/upload", "write"),
        (f"{L}/source/ingestion/candidate-b/bundle/material-bridge", "write"),
        (f"{L}/source/ingestion/candidate-b/runtime/material-bridge", "write"),
        (f"{L}/source/ingestion/candidate-b/runtime/material-bridge/source-scan", "write"),
        (f"{L}/source/ingestion/candidate-b/artifact-family/status", "read"),
        (f"{L}/source/ingestion/candidate-b/visual-lane/status", "read"),
        (f"{L}/source/ingestion/candidate-b/runtime/downstream-proof", "write"),
        (f"{L}/source/ingestion/candidate-b/bundle/downstream-proof", "write"),
        (f"{L}/source/ingestion/candidate-b/default-promotion/operator-status", "read"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/run", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/status", "read"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout", "write"),
        (f"{L}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status", "read"),
        (f"{L}/source/ingestion/candidate-b/default-promotion/closure-evidence", "write"),
        (f"{L}/source/ingestion/candidate-b/default-promotion/readiness-audit", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use/status", "read"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-activation", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/activation-receipt/consume", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use/status", "read"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/operator-repeatability/trial", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/promotion-readiness", "write"),
        (f"{L}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/default-promotion", "write"),
        (f"{L}/source/ingestion/candidate-b/default-promotion/final-proof", "write"),
        (f"{L}/source/ingestion/candidate-b/default-promotion/final-proof/status", "read"),
        (f"{L}/source/ingestion/server-configured-directory/scan", "write"),
        (f"{L}/source/ingestion/server-configured-directory/material-preview", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-authority/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/vector-retrieval", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/status", "read"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/commit", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/status", "read"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/use", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/revoke", "write"),
        (f"{L}/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/status", "read"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/review/submit", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/replacement-set/record-from-supersession-preview", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/commit", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/status", "read"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/use", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/revoke", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/prepare", "write"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver/status", "read"),
        (f"{L}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver", "write"),
        (f"{L}/source/mixed-corpus/seed", "write"),
        (f"{L}/source/mixed-corpus/materialize", "write"),
        # --- layer3/source_sec_edgar.py ---
        (f"{L}/source/sec-edgar/text-table/authority-envelope/validate", "write"),
        (f"{L}/source/sec-edgar/text-table/material-authority/bridge", "write"),
        (f"{L}/source/sec-edgar/text-table/live-source-artifact/material-authority/bridge", "write"),
        (f"{L}/source/sec-edgar/text-table/source-acquisition/authority", "write"),
        (f"{L}/source/sec-edgar/text-table/live-source-artifact/acquire", "write"),
        (f"{L}/source/sec-edgar/companyfacts/acquire-and-stage", "write"),
        (f"{L}/source/sec-edgar/real-filing/acquisition/connector", "write"),
        (f"{L}/source/sec-edgar/real-filing/acquisition/connector/downstream-validation", "write"),
        (f"{L}/source/sec-edgar/real-company-corpus/validation", "write"),
        (f"{L}/source/sec-edgar/real-company-corpus/delivery-status/provenance", "read"),
        (f"{L}/source/sec-edgar/real-company-corpus/operator-inspection", "read"),
        (f"{L}/source/sec-edgar/real-company-corpus/operator-product-surface", "write"),
        (f"{L}/source/sec-edgar/real-company-corpus/operator-value-reveal", "write"),
        (f"{L}/source/sec-edgar/real-company-corpus/durable-delivery/archive", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/source-family/parser", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package-review/preview", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package/commit", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package-review/submit", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/handoff-export/prepare", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status", "read"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/operator-repeatability/trial", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/material-authority/bridge", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/downstream-proof", "write"),
        (f"{L}/source/sec-edgar/text-table/downstream-proof", "write"),
        (f"{L}/source/sec-edgar/text-table/live-source-artifact/downstream-proof", "write"),
        (f"{L}/source/sec-edgar/html-inline-xbrl/downstream-proof/status", "read"),
        (f"{L}/source/sec-edgar/text-table/live-source-artifact/downstream-proof/status", "read"),
        (f"{L}/source/sec-edgar/text-table/live-source-artifact/downstream/operator-repeatability/trial", "write"),
        (f"{L}/source/sec-edgar/text-table/downstream-proof/status", "read"),
        (f"{L}/source/sec-edgar/text-table/downstream/operator-repeatability/trial", "write"),
        # --- layer3/sec_xbrl.py ---
        # Routes using _sec_xbrl_policy_decision (authorize_sec_xbrl_route):
        #   route_family suffix determines access (_write -> "write", _read -> "read").
        (f"{L}/sec-xbrl/operator-review/workflow/open", "write"),
        (f"{L}/sec-xbrl/operator-review/workflow/open-from-staged-evidence", "write"),
        (f"{L}/sec-xbrl/operator-review/workflow/open-full-pipeline", "write"),
        (f"{L}/sec-xbrl/operator-review/workflow/status", "read"),
        (f"{L}/sec-xbrl/operator-review/workflow/admission-status", "read"),
        (f"{L}/sec-xbrl/operator-review/workflow/auditor-attach", "read"),
        (f"{L}/sec-xbrl/operator-review/workflow/decision/submit", "write"),
        (f"{L}/sec-xbrl/operator-review/workflow/decision/status", "read"),
        (f"{L}/sec-xbrl/value-reveal/authority/prepare", "write"),
        (f"{L}/sec-xbrl/value-reveal/submit", "write"),
        # --- app/api/router.py (legacy API — no /layer3 sub-prefix) ---
        (f"{p}/sources/upload", "write"),
        (f"{p}/analysis-runs", "write"),
        (f"{p}/connectors/sciencebase-public/runs", "write"),
        (f"{p}/connectors/sciencebase-mcs/runs", "write"),
        (f"{p}/connectors/nrc-adams-aps/runs", "write"),
        (f"{p}/connectors/senate-lda/runs", "write"),
        (f"{p}/connectors/worldbank/runs", "write"),
        (f"{p}/connectors/cftc-cot/runs", "write"),
        (f"{p}/connectors/bls/runs", "write"),
        (f"{p}/connectors/oecd-sdmx/runs", "write"),
        (f"{p}/connectors/nrc-adams-aps/content-search", "read"),
        (f"{p}/connectors/nrc-adams-aps/_operator/retrieval-content-search", "read"),
        (f"{p}/connectors/nrc-adams-aps/evidence-bundles", "write"),
        (f"{p}/connectors/nrc-adams-aps/citation-packs", "write"),
        (f"{p}/connectors/nrc-adams-aps/evidence-reports", "write"),
        (f"{p}/connectors/nrc-adams-aps/evidence-report-exports", "write"),
        (f"{p}/connectors/nrc-adams-aps/evidence-report-export-packages", "write"),
        (f"{p}/connectors/nrc-adams-aps/context-packets", "write"),
        (f"{p}/connectors/nrc-adams-aps/context-dossiers", "write"),
        (f"{p}/connectors/nrc-adams-aps/deterministic-insight-artifacts", "write"),
        (f"{p}/connectors/nrc-adams-aps/deterministic-challenge-artifacts", "write"),
        (f"{p}/connectors/nrc-adams-aps/deterministic-challenge-review-packets", "write"),
        # --- app/api/market_*.py (analyst-insight compute surface — no /layer3
        #     sub-prefix; each canonical route plus its /analyst-insight alias) ---
        (f"{p}/market-pipeline/integration/cross-reference", "write"),
        (f"{p}/analyst-insight/integration/cross-reference", "write"),
        (f"{p}/market-pipeline/validation/run", "write"),
        (f"{p}/analyst-insight/validation/run", "write"),
        (f"{p}/market-pipeline/insights/process", "write"),
        (f"{p}/analyst-insight/insights/process", "write"),
    ]

    # Parametrized routes — (path_template, access); regex compiled from template
    _param: list[tuple[str, str]] = [
        # layer3/__init__.py
        (f"{L}/analysis-product/{{analysis_product_id}}/transition", "write"),
        # app/api/router.py (legacy API)
        (f"{p}/datasets/{{dataset_id}}/versions/{{dataset_version_id}}/profile", "write"),
        (f"{p}/datasets/{{dataset_id}}/versions/{{dataset_version_id}}/transformations/recommend", "write"),
        (f"{p}/datasets/{{dataset_id}}/versions/{{dataset_version_id}}/transformations/apply", "write"),
        (f"{p}/datasets/{{dataset_id}}/versions/{{dataset_version_id}}/annotations", "write"),
        (f"{p}/datasets/{{dataset_id}}/versions/{{dataset_version_id}}/analysis/recommend", "write"),
        (f"{p}/connectors/runs/{{connector_run_id}}/resume", "write"),
        (f"{p}/connectors/runs/{{connector_run_id}}/cancel", "write"),
    ]

    # Parametrized templates go into both the exact dict (for the template-path
    # lookup done by test_pre_body_map_covers_registered_protected_post_routes)
    # and the patterns list (for runtime path matching against real request URLs).
    exact_dict: dict[str, str] = dict(_exact)
    patterns: list[tuple[re.Pattern[str], str, str]] = []
    for template, access in _param:
        exact_dict[template] = access
        # Build regex by escaping literal segments and replacing {param} placeholders.
        # re.escape is applied only to literal parts so the resulting character
        # class [^/]+ is not mangled.
        parts = re.split(r"(\{[^}]+\})", template)
        regex_str = "^" + "".join(
            "[^/]+" if part.startswith("{") else re.escape(part) for part in parts
        ) + "$"
        pattern = re.compile(regex_str)
        patterns.append((pattern, template, access))

    return exact_dict, tuple(patterns)


def _endpoint_source(endpoint: Any) -> str:
    try:
        return inspect.getsource(endpoint)
    except (OSError, TypeError):
        pass
    # Robust fallback: inspect.getsource can fail (OSError) in some runtime
    # environments when its linecache lookup misses (e.g. relative co_filename
    # under a changed cwd). Read the defining module's file by its absolute
    # __file__ and slice the function's source window directly.
    try:
        code = getattr(endpoint, "__code__", None)
        if code is None:
            return ""
        module = sys.modules.get(getattr(endpoint, "__module__", "") or "")
        path = getattr(module, "__file__", None) or code.co_filename
        if not path:
            return ""
        if not os.path.isabs(path) and module is not None and getattr(module, "__file__", None):
            path = module.__file__
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        start = max(0, code.co_firstlineno - 1)
        return "".join(lines[start:start + 400])
    except Exception:  # noqa: BLE001 - best-effort source recovery
        return ""


def _operator_authorization_access_from_endpoint(endpoint: Any) -> str | None:
    source = _endpoint_source(endpoint)
    if "_route_level_operator_identity" in source:
        match = re.search(
            r"_route_level_operator_identity\([\s\S]*?access\s*=\s*['\"](read|write)['\"]",
            source,
        )
        return match.group(1) if match else "write"
    if "_sec_xbrl_policy_decision" in source or "authorize_sec_xbrl_route" in source:
        route_family_access = set(
            re.findall(r"\bsec_xbrl_[A-Za-z0-9_]+_(read|write)\b", source)
        )
        if "write" in route_family_access:
            return "write"
        if "read" in route_family_access:
            return "read"
    return None


def _pre_body_operator_authorization_access_for_path(path: str) -> str | None:
    exact = _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES.get(path)
    if exact is not None:
        return exact
    for path_regex, _path_template, access in _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTE_PATTERNS:
        if path_regex.match(path):
            return access
    return None


def _require_pre_body_operator_authorization_routes(routes_by_path: dict[str, str]) -> None:
    missing = {
        path: expected_access
        for path, expected_access in _REQUIRED_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES.items()
        if routes_by_path.get(path) != expected_access
    }
    if missing:
        raise RuntimeError(
            "pre-body operator authorization route discovery failed: required protected POST routes "
            "are absent from the registry: "
            + ", ".join(f"{path}={access}" for path, access in sorted(missing.items()))
        )


def _auth_policy_error_response(
    exc: layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(field)
                    for field in exc.details.get(
                        "blocked_fields",
                        exc.details.get("mismatched_fields", []),
                    )
                ],
                next_allowed_actions=["inspect_existing_sec_xbrl_auth_binding_authority"],
            )
        ),
    )


@app.middleware("http")
async def _pre_body_operator_authorization_middleware(request: Request, call_next):
    access = _pre_body_operator_authorization_access_for_path(request.url.path)
    if request.method.upper() == "POST" and access is not None:
        try:
            layer3_sec_xbrl_in_app_auth_policy.route_level_operator_authorization_required(
                {str(key): str(value) for key, value in request.headers.items()},
                access=access,
            )
        except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
            return _auth_policy_error_response(exc)
    return await call_next(request)


app.include_router(api_router, prefix=settings.api_prefix)

# Build the static registry immediately after routes are registered.
# Pure dict/pattern lookup — no inspect.getsource, no app.router.routes iteration.
(
    _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES,
    _PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTE_PATTERNS,
) = _build_static_pre_body_routes(settings.api_prefix)
_require_pre_body_operator_authorization_routes(_PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES)
bootstrap_storage_tree()
if settings.storage_mount_enabled:
    app.mount('/storage', StaticFiles(directory=settings.storage_dir), name='storage')
review_ui_static_dir = Path(__file__).resolve().parent / "app" / "review_ui" / "static"
app.mount('/review/nrc-aps/static', StaticFiles(directory=review_ui_static_dir), name='review_ui_static')
app.mount('/review/layer3/static', StaticFiles(directory=review_ui_static_dir), name='layer3_ui_static')


@app.get('/review/nrc-aps', response_class=HTMLResponse)
def review_nrc_aps_page() -> HTMLResponse:
    index_file = review_ui_static_dir / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/document-trace', response_class=HTMLResponse)
def review_nrc_aps_document_trace_page() -> HTMLResponse:
    trace_file = review_ui_static_dir / "document_trace.html"
    return HTMLResponse(content=trace_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/workbench-compare', response_class=HTMLResponse)
def review_nrc_aps_workbench_compare_page() -> HTMLResponse:
    compare_file = review_ui_static_dir / "workbench_compare.html"
    return HTMLResponse(content=compare_file.read_text(encoding="utf-8"))


@app.get('/review/nrc-aps/candidate-b-trace', response_class=HTMLResponse)
def review_nrc_aps_candidate_b_trace_page() -> HTMLResponse:
    candidate_b_trace_file = review_ui_static_dir / "candidate_b_trace.html"
    return HTMLResponse(content=candidate_b_trace_file.read_text(encoding="utf-8"))


@app.get('/review/layer3', response_class=HTMLResponse)
def layer3_workbench_page() -> HTMLResponse:
    layer3_file = review_ui_static_dir / "layer3.html"
    return HTMLResponse(content=layer3_file.read_text(encoding="utf-8"))


@app.get('/review/analyst-insight', response_class=HTMLResponse)
def analyst_insight_page() -> HTMLResponse:
    page_file = review_ui_static_dir / "analyst_insight.html"
    return HTMLResponse(content=page_file.read_text(encoding="utf-8"))


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/ready', response_model=None)
def ready() -> JSONResponse:
    """Readiness probe: executes SELECT 1 against the configured database."""
    try:
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
        return JSONResponse(status_code=200, content={'status': 'ready', 'build': BUILD_INFO})
    except Exception:
        return JSONResponse(status_code=503, content={'status': 'unavailable', 'build': BUILD_INFO})


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return """
    <html>
      <head><title>Method-Aware Framework</title></head>
      <body style='font-family: sans-serif; max-width: 760px; margin: 40px auto;'>
        <h1>Method-Aware Data Utilization Framework</h1>
        <p>Starter backend is running.</p>
        <ul>
          <li><a href='/docs'>OpenAPI docs</a></li>
          <li><a href='/health'>Health</a></li>
          <li><a href='/review/analyst-insight'>Analyst insight layer</a> - deterministic integration, validation, and insight demo</li>
        </ul>
        <p>Use the upload endpoint first, then profile, transform, annotate, and analyze.</p>
      </body>
    </html>
    """
