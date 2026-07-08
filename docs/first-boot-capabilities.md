# First-Boot Capabilities

What an operator can actually do immediately after a default boot, versus what is gated behind an API key, a secret, or a feature flag. This is the concrete definition of "usable" for a fresh install; it is not target-state design.

Default boot (no environment configuration):

```powershell
cd backend
py -3.12 -m uvicorn main:app
```

This runs Alembic migrations automatically (`db_init_mode` default `migrate`, `backend/app/core/config.py:63`) against the default SQLite database, in `deployment_mode=local` (`config.py:62`) with `auth_owner=none` (`config.py:134`). In local mode the server-derived role is `OWNER` for any caller, so no auth headers are required.

Status legend: **[verified]** = exercised end-to-end against a running server in this workspace; **[code]** = asserted from source/config, not independently run here.

## Works out of the box — no config

| Capability | Surface | Status |
| --- | --- | --- |
| Health / readiness / OpenAPI | `GET /health`, `GET /ready`, `GET /docs`, `GET /openapi.json` (306 paths) | [verified] |
| Method-aware analytics vertical | `POST /api/v1/sources/upload` → `.../profile` → `.../analysis/recommend` → `POST /api/v1/analysis-runs` (`cross_correlation`, `decomposition`, `structural_break`) — runs complete with persisted artifacts | [verified] |
| Layer 3 workbench UI | `GET /review/layer3` (+ `/review/nrc-aps`, `/review/analyst-insight`, document-trace, workbench-compare, candidate-b-trace) | [verified: layer3 page serves] |
| ScienceBase public connector | `POST /api/v1/connectors/sciencebase-public/runs` (+ `sciencebase-mcs`) — no API key; public access | [code: `config.py:144`, `get_sciencebase_adapter`] |
| Senate LDA connector (anonymous) | `POST /api/v1/connectors/senate-lda/runs` — works with no key in anonymous mode | [code: `connectors_senate_lda.py:481`] |
| World Bank Indicators connector (anonymous) | `POST /api/v1/connectors/worldbank/runs` - works with no key in anonymous metadata mode | [code: `connectors_worldbank.py`] |
| BLS Public Data API v1 connector (anonymous) | `POST /api/v1/connectors/bls/runs` - works with no key in anonymous metadata mode; per-run caps are enforced locally | [code: `connectors_bls.py`] |
| OECD SDMX connector (anonymous) | `POST /api/v1/connectors/oecd-sdmx/runs` - works with no key in anonymous SDMX-CSV mode; per-run budget <=30 is enforced locally, while 60 downloads/hour and no-VPN/no-anonymized-traffic compliance remain operator residuals | [code: `connectors_oecd.py`] |
| CFTC COT connector (anonymous) | `POST /api/v1/connectors/cftc-cot/runs` - works with no key for current public COT report rows | [code: `connectors_cftc_cot.py`] |
| Connector run observability | `GET /api/v1/connectors/runs/{id}` + `/targets` `/events` `/reports` `/content-units` | [code] |

The analytics vertical and the ScienceBase/Senate/World Bank/BLS/OECD/CFTC anonymous connectors are the realistic "usable in full" core for a fresh boot.

## Needs an API key or secret (otherwise blocked)

| Variable | What it unlocks | Behavior when unset |
| --- | --- | --- |
| `NRC_ADAMS_APS_SUBSCRIPTION_KEY` | NRC ADAMS APS connector | Connector **non-functional** — raises `SubmissionConflictError` (`connectors_nrc_adams.py:1195-1196`) |
| `LAYER3_SIGNED_REFERENCE_SECRET` | External export/download signed-reference generation | `Layer3WorkbenchError` raised; signed-reference export blocked (`layer3_workbench.py:880-893`) |
| `SENATE_LDA_API_KEY` | Senate LDA authenticated (higher-rate) mode | Optional — anonymous mode still works (`connectors_senate_lda.py:302,481`) |

## Gated by feature flags (default OFF)

All default `false` in `config.py` unless noted. Each must be explicitly enabled.

| Flag (env alias) | Gates | config.py |
| --- | --- | --- |
| `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED` | Live network fetches to SEC EDGAR (otherwise offline/replay only) | 86-89 |
| `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED` | Arelle fact-authority internal value store | 100-103 |
| `LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED` | Arelle real-company corpus validation | 104-107 |
| `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED` | SEC EDGAR Arelle value-reveal | 112-115 |
| `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED` | SEC XBRL controlled value-reveal submit | 120-123 |
| `LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED` | 3C product package inventory feature | 124-127 |
| `SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED` | SEC XBRL production admission evaluator | 128-131 |
| `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED` (default **true**) | Arelle fact-authority cutover; in nonlocal mode also requires `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED=true` | 96-99 |

The SEC-EDGAR / Arelle value-reveal surface (the bulk of these flags) is off by default and not part of the default usable set.

## Optional analytical extras (lazy — absence is non-fatal)

- Advanced PDF table extraction requires `camelot-py[cv]` + Ghostscript. Imported lazily (`nrc_aps_advanced_table_parser.py`); only invoking advanced table extraction raises a clear error when absent. The app boots and all other features work without it.
- OCR requires the Tesseract CLI and/or `paddleocr`; lazy-loaded and degrades gracefully.
- `PyMuPDF` (core requirement) is needed for baseline PDF text extraction and is always installed.

## Production / nonlocal mode

`DEPLOYMENT_MODE=nonlocal` enforces (validated at startup, `config.py:269-309`): explicit HTTPS `ALLOWED_ORIGINS`; `AUTH_OWNER=proxy` + `TRUSTED_PROXY_MODE=true` + proxy identity headers; non-SQLite `DATABASE_URL`; `STORAGE_EXPOSURE` constrained (`auto`/`disabled`); no value-reveal flags armed. See [deploy/SETUP.md](../deploy/SETUP.md) for the operator first-run runbook and [deploy/.env.deploy.example](../deploy/.env.deploy.example) for the full environment-variable reference.
