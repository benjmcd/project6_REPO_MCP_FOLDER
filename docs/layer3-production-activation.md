# Layer 3 Production Activation Runbook

This document is the authoritative flag-matrix runbook for Layer 3 SEC/XBRL
production deployments.  It describes every configuration flag, its production
value, its rationale, and the hard constraints enforced by the server.

---

## 1. Nonlocal deployment validator requirements

The `DEPLOYMENT_MODE=nonlocal` master switch triggers a fail-closed profile
validator in `backend/app/core/config.py` (`_validate_deployment_profile`,
approximately lines 233-267).  The following conditions are all required and
enforced at server start; the server will refuse to boot if any are violated:

| Requirement | Required value | Validator message |
|---|---|---|
| `ALLOWED_ORIGINS` | Explicit HTTPS origins only — no wildcard | "must use explicit origins" / "must use HTTPS origins" |
| `AUTH_OWNER` | `proxy` | "AUTH_OWNER=proxy is required" |
| `TRUSTED_PROXY_MODE` | `true` | "TRUSTED_PROXY_MODE=true is required" |
| `PROXY_IDENTITY_HEADER` | Non-empty string | "PROXY_IDENTITY_HEADER is required" |
| `STORAGE_EXPOSURE` | `auto` or `disabled` | "must be auto or disabled" |
| `DATABASE_URL` | Non-SQLite | "must not use sqlite" |
| `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED` | `true` (when cutover enabled) | "NONLOCAL_AUTHORIZED=true is required" |
| `PROXY_ROLES_HEADER` | Non-empty (when `role_enforcing`) | "PROXY_ROLES_HEADER is required" |

Additionally, production deployments must set `DB_INIT_MODE=migrate` (never
`create_all`).  The `create_all` mode is unsuitable for production because it
bypasses Alembic migration history and cannot apply incremental schema changes
safely to an existing database.

---

## 2. Full flag matrix

### 2a. Core deployment flags

| Flag | Production value | Why |
|---|---|---|
| `DEPLOYMENT_MODE` | `nonlocal` | Master switch; enables multi-identity, fail-closed profile |
| `AUTH_OWNER` | `proxy` | Operator identity is asserted by the trusted reverse proxy |
| `TRUSTED_PROXY_MODE` | `true` | Instructs the server to accept proxy identity headers |
| `PROXY_IDENTITY_HEADER` | `X-Forwarded-User` | Header carrying operator identity from proxy |
| `PROXY_EMAIL_HEADER` | `X-Forwarded-Email` | Header carrying operator email from proxy |
| `PROXY_GROUPS_HEADER` | `X-Forwarded-Groups` | Header carrying operator groups from proxy |
| `LAYER3_ROUTE_AUTHORIZATION_MODE` | `role_enforcing` | Enforces role-based access control on all protected routes |
| `PROXY_ROLES_HEADER` | `X-Forwarded-Roles` | Required when `role_enforcing` |
| `LAYER3_OWNER_ROLE_TOKENS` | `owner` | Token that grants owner-level access |
| `LAYER3_AUDITOR_ROLE_TOKENS` | `auditor` | Token that grants auditor-level access |
| `DB_INIT_MODE` | `migrate` | Apply incremental Alembic migrations (never `create_all`) |
| `DATABASE_URL` | `postgresql+psycopg://...` | PostgreSQL required; SQLite forbidden in nonlocal mode |
| `ALLOWED_ORIGINS` | `https://<your-domain>` | Explicit HTTPS origin; wildcard forbidden |
| `CORS_ALLOW_CREDENTIALS` | `true` | Proxy-auth flows require credential forwarding |
| `STORAGE_EXPOSURE` | `auto` | Safe default; `enabled`/`proxy_protected` forbidden |
| `LAYER3_LOG_FORMAT` | `json` | Structured JSON logs for log aggregation pipelines |

### 2b. Activated production capability flags

| Flag | Production value | Why |
|---|---|---|
| `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED` | `true` | Production must reach SEC EDGAR for live filing data |
| `LAYER3_SEC_EDGAR_USER_AGENT` | `<Org> <contact@example.com>` | Required by SEC fair-access policy when live network on |
| `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED` | `true` | Production uses Arelle as downstream fact-authority preference |
| `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED` | `true` | Required by nonlocal validator when cutover enabled |
| `LAYER3_SEC_EDGAR_OFFICIAL_TICKER_RESOLUTION_ENABLED` | `true` | Resolves tickers beyond static allow-list via SEC company_tickers.json |
| `LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED` | `true` | Surfaces full package inventory to authorized operators |
| `SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED` | `true` | Activates six-criteria production-admission evaluator |

---

## 3. PERMANENTLY GATED — value-reveal conjunction flags

The five flags below form the **Arelle invocation + governed sibling
value-reveal conjunction** (see `backend/app/services/layer3_sec_xbrl_posture.py`,
function `_arelle_invocation_surface`, lines 281-286).

All five must be `true` simultaneously before Arelle invocation is enabled and
any SEC XBRL value reveal can occur:

```
arelle_fact_authority_cutover_enabled          # LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED
arelle_fact_authority_nonlocal_authorized      # LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED
arelle_internal_value_store_enabled            # LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED
arelle_corpus_validation_enabled               # LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED
arelle_governed_sibling_value_reveal_enabled   # LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED
```

The first two are set to `true` in the production profile above (cutover is a
preference flag; nonlocal-authorized is required by the validator).  The
**remaining three are PERMANENTLY GATED** and must remain `false` in this
template:

| Flag | Production value | Gate status |
|---|---|---|
| `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED` | `false` | PERMANENTLY GATED |
| `LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED` | `false` | PERMANENTLY GATED |
| `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED` | `false` | PERMANENTLY GATED |
| `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED` | `false` | PERMANENTLY GATED |

Additionally, the redaction enforcement path is governed by the same gate: no
value reveal can proceed without explicit operator confirmation, a value-reveal
authority receipt, an approved review decision, complete lineage, redaction
validation, and sidecar/value-store resolution (all absent by default).

These flags must **never** be set in CI and must **never** be set to `true`
without satisfying all gating prerequisites listed above.

---

## 4. Observability

### Request-ID

Every request receives an `X-Request-ID` response header.  If the caller
supplies `X-Request-ID` in the request, that value is honored and echoed back.
Otherwise a UUID4 is generated server-side.  The id is available on
`request.state.request_id` within any route handler.

### Structured logging

Set `LAYER3_LOG_FORMAT=json` to emit one JSON object per log line.  Each line
includes `level`, `logger`, `message`, and `request_id` (when available).
Plain/uvicorn-default formatting is used when the variable is absent or empty.

### /health and /ready probes

| Endpoint | Purpose | Success | Failure |
|---|---|---|---|
| `GET /health` | Liveness — server process alive | `200 {"status":"ok"}` | n/a (static) |
| `GET /ready` | Readiness — database reachable | `200 {"status":"ready"}` | `503 {"status":"unavailable"}` |

Configure your load balancer or orchestrator (e.g. Kubernetes) to use `/ready`
as the readiness probe and `/health` as the liveness probe.  Never replace
`/health` with the DB-backed check — liveness must remain static so it does not
cause restart loops during database outages.
