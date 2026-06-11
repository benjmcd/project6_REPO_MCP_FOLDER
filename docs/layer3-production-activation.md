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

---

## 5. Deployment Packaging

The production application image is defined in `Dockerfile.app` at the repo
root.  It is separate from `Dockerfile`, which is the development-environment image
and must not be used for production deployments.

### Build command

Run from the repo root (the build context must include `backend/`):

```sh
docker build -f Dockerfile.app -t method-aware-app .
```

### Run command

Supply the production env file.  Override `DATABASE_URL` as required for your
environment:

```sh
docker run --env-file backend/.env.production.example \
  -e DATABASE_URL=postgresql+psycopg://user:pass@db-host:5432/method_aware \
  -p 8000:8000 \
  method-aware-app
```

All required production flags (`DEPLOYMENT_MODE`, `AUTH_OWNER`,
`TRUSTED_PROXY_MODE`, `PROXY_IDENTITY_HEADER`, etc.) are set in
`backend/.env.production.example`.  Copy that file, fill in every `<REPLACE>`
placeholder, and pass it via `--env-file`.

### Migration-at-boot behavior

The container entrypoint runs:

```sh
python -m alembic -c alembic.ini upgrade head && \
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Alembic applies all pending migrations before uvicorn starts.  If alembic
fails (e.g. database unreachable or a migration error), the container exits
non-zero and does not start the API server.

`DB_INIT_MODE` in the env file controls how `main.py` itself initialises the
database on import.  For production set `DB_INIT_MODE=migrate` (the default),
which causes `main.py` to call `alembic upgrade head` a second time at import
— this is a no-op if the entrypoint already applied all migrations and is safe
for idempotency.  Alternatively set `DB_INIT_MODE=none` to suppress the
`main.py`-side migration call entirely and rely solely on the entrypoint run.

### Healthcheck endpoints

| Endpoint | Purpose | Used for |
|---|---|---|
| `GET /health` | Static liveness — process alive | Docker `HEALTHCHECK`, liveness probe |
| `GET /ready` | Readiness — `SELECT 1` against the DB | Readiness probe before load-balancer traffic |

The `HEALTHCHECK` in `Dockerfile.app` uses `/ready` with a 60-second
`start-period` to allow migrations to complete before probes fire.

### Reverse proxy requirement

**The image must run behind a trusted reverse proxy.**  When
`DEPLOYMENT_MODE=nonlocal` (required for production):

- `AUTH_OWNER=proxy` and `TRUSTED_PROXY_MODE=true` must be set.
- The proxy must inject `PROXY_IDENTITY_HEADER` (and optionally
  `PROXY_EMAIL_HEADER`, `PROXY_GROUPS_HEADER`, `PROXY_ROLES_HEADER`) on every
  request.
- The API server must not be directly internet-exposed; all operator identity
  assertions come exclusively from the proxy headers.
- Do not set `TRUSTED_PROXY_MODE=true` without an actual authenticating proxy
  in front — the server will accept whatever identity the proxy sends.

### Python dependency notes

`backend/requirements.txt` is the complete production dependency set; all
packages are reachable from `main.py`'s import graph.  Key inclusions and
rationale:

| Package | Why needed |
|---|---|
| `fastapi`, `uvicorn` | ASGI framework and server |
| `sqlalchemy`, `alembic` | ORM and database migrations |
| `pydantic-settings` | Typed settings from environment |
| `psycopg[binary]` | PostgreSQL driver (psycopg3) |
| `requests` | HTTP client used by NRC ADAMS / ScienceBase connectors |
| `pandas`, `numpy` | DataFrame I/O, profiling, analysis services |
| `scipy`, `statsmodels` | Statistical routines in `profiling.py` and `analysis.py` |
| `scikit-learn` | Scalers/transformers in `transforms.py` |
| `matplotlib` | Chart generation in `analysis.py` (Agg backend, no display) |
| `ruptures` | Changepoint detection in `analysis.py` |
| `PyMuPDF` (fitz) | PDF text extraction in `nrc_aps_document_processing.py` |
| `camelot-py[cv]` | Advanced PDF table extraction (requires Ghostscript + Poppler) |
| `paddlepaddle`, `paddleocr` | Advanced OCR path in `nrc_aps_advanced_ocr.py` |
| `pyarrow` | Parquet read/write used by `dataframe_io.py` via pandas |
| `statsmodels` | STL decomposition and ADF/KPSS stationarity tests |

`scikit-learn`, `pandas`, `scipy`, `matplotlib`, `ruptures`, and `statsmodels`
are all genuinely required — they are imported at module load time by services
that are part of the router import chain, not optional or lazy-loaded.

---

## 6. Role Enforcement Mode

By default, `LAYER3_ROUTE_AUTHORIZATION_MODE=identity_presence` — operator identity is required
but the role claim is not enforced. This is the safe-start posture.

To activate full role enforcement once the proxy is provisioning roles:

1. Confirm `X-Forwarded-Roles` is being sent by the proxy with value `owner` or `auditor`.
2. Set `LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing` in your env file.
3. Restart the application.

Under `role_enforcing`:
- Requests without `X-Forwarded-Roles` → 401 `missing_workspace_authority`.
- Role claims in the request body that exceed the server-derived role → 409 `sec_xbrl_in_app_auth_policy_role_claim_exceeds_server_authority`.
- `PROXY_ROLES_HEADER` (default `X-Forwarded-Roles`) can be overridden if your proxy uses a different header name.

Do NOT enable `role_enforcing` before the proxy is configured to send the roles header — it will block all authenticated requests.

---

## 7. Reference Compose Deployment

`deploy/docker-compose.production.yml` provides a reference three-service stack
(app + postgres + nginx auth proxy) that assembles the topology described in
sections 1–6.  It is a starting point for operator adoption, not a
production-hardened blueprint — TLS, secrets management, and log aggregation
remain deployment-owned.

### Topology

```
  [browser / client]
         |
         | HTTPS (operator-owned TLS — see TLS note below)
         v
  +--------------------+
  |  nginx proxy :80   |  ← HTTP Basic Auth + role mapping
  |  (host port 8080)  |    rewrites all X-Forwarded-* headers server-side
  +--------------------+
         |
         | HTTP (internal network only — no internet exposure)
         v
  +--------------------+
  |  app :8000         |  ← FastAPI/uvicorn, DEPLOYMENT_MODE=nonlocal
  |  (no host port)    |    LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing
  +--------------------+
         |
         | (internal network)
         v
  +--------------------+
  |  db :5432          |  ← postgres:16-alpine
  |  (no host port)    |    named volume: db_data
  +--------------------+
```

All three services share a single internal Docker bridge network.  Only the
proxy publishes a host port (`${PROXY_HTTP_PORT:-8080}`).  The app and db are
unreachable from the host.

### Operator Setup Steps

1. **Copy the example env file** and fill in every `<REPLACE>` value:

   ```sh
   cp deploy/.env.deploy.example deploy/.env
   # Edit deploy/.env:
   #   POSTGRES_PASSWORD=<strong-random-password>
   #   ALLOWED_ORIGINS=https://your-domain.example.com
   #   PROXY_HTTP_PORT=8080      (or 80 behind a TLS LB)
   #   LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false   (default; enable later)
   ```

2. **Generate the htpasswd file** (bcrypt hashes via httpd:2.4-alpine):

   ```sh
   # Create/overwrite the password file for an owner user:
   docker run --rm httpd:2.4-alpine htpasswd -nbB alice mysecretpassword \
     > deploy/proxy/htpasswd
   # Append an auditor user:
   docker run --rm httpd:2.4-alpine htpasswd -nbB bob auditorpass \
     >> deploy/proxy/htpasswd
   ```

   See `deploy/proxy/htpasswd.example` for the expected format.

   > **Windows note:** run these from `cmd.exe`, Git Bash, or WSL. In Windows
   > PowerShell, `>` / `>>` redirection writes UTF-16 with a BOM, which nginx
   > cannot parse as an htpasswd file. (`deploy/smoke.ps1` handles this
   > correctly for its own ephemeral credentials.)

3. **Create the roles map** assigning each username a role token:

   ```
   # deploy/proxy/roles.map
   "alice" "owner";
   "bob"   "auditor";
   ```

   See `deploy/proxy/roles.map.example` for format details.

4. **Start the stack** from the repo root:

   ```sh
   docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env \
     up -d --build
   ```

5. **Verify** that the app is healthy and the proxy is routing:

   ```sh
   # Wait for healthy
   docker compose -f deploy/docker-compose.production.yml ps

   # Probe via proxy (replace 8080 with your PROXY_HTTP_PORT)
   curl -u alice:mysecretpassword http://localhost:8080/api/v1/layer3/operator/identity
   ```

### How Role Mapping Works

The split of responsibilities is deliberate: the **proxy authenticates and
injects headers; the app authorizes**.

1. **HTTP Basic Auth** (via `auth_basic` + `auth_basic_user_file /etc/nginx/htpasswd`):
   unauthenticated requests → 401.

2. **Role lookup**: authenticated usernames are looked up in `/etc/nginx/roles.map`
   via an nginx `map` block.  Mapped users receive the configured role token;
   users absent from the map are forwarded with an **empty** `X-Forwarded-Roles`
   header, which the app rejects (401, missing role authority) on every
   protected route under `role_enforcing`.  There is intentionally no
   nginx-side role rejection: an `if`/`return` gate would run in nginx's
   rewrite phase, before Basic Auth, and would break the 401 challenge for
   unauthenticated clients.

On every forwarded request the proxy unconditionally **overwrites** all four
identity headers with server-derived values:

| Header | Value |
|---|---|
| `X-Forwarded-User` | `$remote_user` (nginx Basic-Auth username) |
| `X-Forwarded-Email` | `$remote_user` (same; email is not collected in Basic Auth) |
| `X-Forwarded-Groups` | `layer3-operators` (static group for all authenticated users) |
| `X-Forwarded-Roles` | `$layer3_roles` (from roles.map lookup) |

Because these are set unconditionally, any client-supplied `X-Forwarded-*`
headers are silently discarded — spoofing is not possible.

Under `LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing` the app then enforces:
- `owner` → full read + write access
- `auditor` → read-only access (write routes return 403)
- Missing or unrecognised role → 401

### Smoke Test

`deploy/smoke.ps1` (Windows PowerShell 5.1) automates end-to-end stack
verification without requiring pre-created credentials:

```powershell
# From the repo root:
.\deploy\smoke.ps1

# Leave the stack running after the test:
.\deploy\smoke.ps1 -KeepUp
```

The script generates ephemeral random credentials, builds the stack, waits for
app health, then asserts the full matrix:

| Check | Expected |
|---|---|
| No credentials | 401 |
| Auditor GET `/operator/identity` | 200 |
| Auditor POST write route | 403 |
| Owner POST write route | 400 (auth passed; workbench validation error) |
| Auditor + spoofed role header | 403 (spoof rejected) |
| GET `/ready` | 200 |
| Direct `localhost:8000` | connection refused |

### TLS Note

This stack handles HTTP only.  **TLS must terminate at or before the nginx
proxy in real deployments.**  Options:

- Put a TLS-terminating load balancer (AWS ALB, GCP HTTPS LB, Cloudflare, or
  an outer nginx with SSL certificates) in front of the proxy container.
- Add an HTTPS server block directly to `deploy/proxy/nginx.conf` with
  `ssl_certificate` / `ssl_certificate_key` and redirect port 80 → 443.

The `ALLOWED_ORIGINS` value in `deploy/.env` must match the actual HTTPS origin
your clients connect to — the nonlocal validator requires explicit HTTPS origins.

### Value-Reveal Flags and Admission Evaluator

This compose stack **deliberately omits** the following:

- The five permanently-gated value-reveal conjunction flags
  (`LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED`,
  `LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED`,
  `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED`,
  `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED`):
  these must remain `false` and are not set anywhere in `deploy/`.

- `SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED`: this flag must
  **never** be set in CI and is not present in the reference stack.

See section 3 for the full value-reveal gate rationale.

### CI Contract Test

`backend/tests/test_layer3_deploy_compose_contract.py` is collected by pytest
(via the `test_layer3_*.py` glob) and asserts the structural invariants of the
`deploy/` directory without running docker:

```sh
# From backend/ directory:
python -m pytest tests/test_layer3_deploy_compose_contract.py -q
```
