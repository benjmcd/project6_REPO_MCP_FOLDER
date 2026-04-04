# Analyst Insight Status Handoff

## 1. Purpose and truth model

This document is the canonical live-repo status surface for the analyst-insight layer. It records the current state of the analyst-insight page, API routes, and deferred tech debt as of April 4, 2026.

The analyst-insight layer is the product-facing deterministic integration, validation, and insight surface. It is not the retired document-storage bridge lane and is not part of the `handoff/` package.

Repo truth precedence for analyst-insight decisions:

1. live code, tests, and repo-contained proof artifacts in the current worktree
2. this live status doc and other current root docs
3. active planning docs under `next_milestone_plans/`
4. historical bridge planning docs only as non-authoritative guardrails

## 2. Current status summary

| Surface | Current state | Proof |
| --- | --- | --- |
| Analyst-insight page | Live at `/review/analyst-insight` | `backend/main.py` route `analyst_insight_page`; `backend/tests/test_analyst_insight_page.py` |
| Analyst-insight alias routes | Live | `backend/app/api/market_data_integration.py` (`alias_router`), `market_data_validation.py` (`alias_router`), `market_insight_ai.py` (`alias_router`); `backend/tests/test_analyst_insight_alias_parity.py` |
| Legacy market-pipeline routes | Still supported | `backend/app/api/market_data_integration.py` (`router`), `market_data_validation.py` (`router`), `market_insight_ai.py` (`router`) |
| `/review/market-pipeline` page route | Absent (returns 404) | `backend/tests/test_analyst_insight_page.py::test_market_pipeline_page_remains_absent` |
| Deterministic/no-LLM semantics | True | All three stage services use deterministic heuristic logic with no LLM dependency |
| Static asset serving | Shared mount at `/review/nrc-aps/static/` | `backend/main.py` static mount; `backend/app/review_ui/static/analyst_insight.html` references `/review/nrc-aps/static/review.css`, `/review/nrc-aps/static/analyst_insight.css`, `/review/nrc-aps/static/analyst_insight.js` |
| Shared styling | Inherits `review.css` from the NRC APS review UI | `backend/app/review_ui/static/analyst_insight.html`; `backend/tests/test_analyst_insight_page.py` |
| Root discoverability | Home page links to analyst-insight | `backend/main.py` index route; `backend/tests/test_analyst_insight_page.py::test_root_exposes_analyst_insight_link` |
| Review-shell discoverability | `/review/nrc-aps` and `/review/nrc-aps/document-trace` link to analyst-insight | `backend/app/review_ui/static/index.html`; `backend/app/review_ui/static/document_trace.html`; `backend/tests/test_review_nrc_aps_page.py`; `backend/tests/test_review_nrc_aps_document_trace_page.py` |

## 3. Current contract summary

### Page route

| Route | Method | Handler |
| --- | --- | --- |
| `/review/analyst-insight` | GET | `backend/main.py::analyst_insight_page` |

### Analyst-insight alias routes (product-facing)

| Route | Method | Module | OpenAPI tag |
| --- | --- | --- | --- |
| `/api/v1/analyst-insight/integration/cross-reference` | POST | `market_data_integration.py` | `analyst-insight` |
| `/api/v1/analyst-insight/validation/run` | POST | `market_data_validation.py` | `analyst-insight` |
| `/api/v1/analyst-insight/insights/process` | POST | `market_insight_ai.py` | `analyst-insight` |

### Legacy compatibility routes

| Route | Method | Module | OpenAPI tag |
| --- | --- | --- | --- |
| `/api/v1/market-pipeline/integration/cross-reference` | POST | `market_data_integration.py` | `market-pipeline` |
| `/api/v1/market-pipeline/validation/run` | POST | `market_data_validation.py` | `market_data_validation` |
| `/api/v1/market-pipeline/insights/process` | POST | `market_insight_ai.py` | `market-pipeline` |

### Current OpenAPI/tag surface

OpenAPI exposes all six routes above. The tag surface is mixed:

- Alias routes use the `analyst-insight` tag consistently
- Legacy routes use `market-pipeline` (integration and insights) and `market_data_validation` (validation) tags as originally implemented
- No tag normalization or deprecation annotations have been applied

### Current proof basis

- `backend/tests/test_analyst_insight_page.py`: page route serving, root link, market-pipeline absence, JS alias usage, HTML alias references
- `backend/tests/test_analyst_insight_alias_parity.py`: response parity between legacy and alias routes for all three stages (success and error paths)
- `backend/tests/test_market_data_integration.py`: integration stage service logic
- `backend/tests/test_market_data_validation.py`: validation stage service logic
- `backend/tests/test_market_insight_ai.py`: insight stage service logic

## 4. Intentional deferred tech debt

The following are deferred by design and are not missing work:

- **Legacy `market-pipeline` naming**: Internal module filenames (`market_data_integration.py`, `market_data_validation.py`, `market_insight_ai.py`) and their service counterparts still use `market_*` naming. No rename decision has been made.
- **Shared static mount**: Analyst-insight assets (`analyst_insight.html`, `analyst_insight.js`, `analyst_insight.css`) are served through the NRC APS review UI static mount at `/review/nrc-aps/static/`. No decision to decouple this mount has been made.
- **Shared styling**: The analyst-insight page inherits `review.css` from the NRC APS review UI. This is intentional shared styling, not a missing analyst-insight-specific stylesheet.
- **Mixed OpenAPI tags**: Legacy routes retain their original tags (`market-pipeline`, `market_data_validation`). Alias routes use the `analyst-insight` tag. No tag normalization or OpenAPI deprecation annotations have been applied.
- **No deprecation decision**: Legacy `market-pipeline` routes remain fully supported. No timeline or mechanism for deprecation has been established.
- **Cross-shell discoverability**: The NRC APS review shell pages (`/review/nrc-aps` and `/review/nrc-aps/document-trace`) now link to `/review/analyst-insight`. No broader navigation redesign or additional cross-shell coupling has been introduced.

## 5. What is not authoritative

These are not the ongoing live authority for analyst-insight state:

- Historical bridge planning docs (e.g., `tier1_downstream_bridge_lane_plan.md` and related files in other worktrees)
- Archived bridge code
- Session logs
- Dirty local worktrees and unmerged side branches
- `handoff/` package control surfaces -- the analyst-insight layer is not a handoff-managed lane

## 6. Broad-signpost treatment

### README.md assessment

`README.md` acts as a broad capability and signpost surface. Its "Key docs" section already references `nrc_aps_status_handoff.md` and `postgres_status_handoff.md`. A minimal one-line signpost reference to this analyst-insight status handoff was added to that section to avoid orphaning this doc from the repo's primary navigational surface.

### REPO_INDEX.md assessment

`REPO_INDEX.md` acts as a broad repo map with status notes at the top pointing to authoritative status surfaces. A minimal one-line status note was added to the existing status note block to provide a navigational signpost to this doc. No other sections were modified.

## 7. Recommended next possible lanes

If analyst-insight work continues, the next reasonable lanes are:

1. **Discoverability refinement**: Review-shell discoverability links are now live (Slice 4). Further discoverability work (e.g., broader navigation redesign or additional cross-shell affordances) should be separately justified if needed.
2. **Deprecation / rename strategy**: Establish a timeline and mechanism for retiring the legacy `market-pipeline` route prefix, normalizing internal module naming, and cleaning up the mixed OpenAPI tag surface. This has high blast radius and should be a distinct slice.

Until one of those lanes is intentionally opened, the current analyst-insight state should be treated as stable and complete for its current scope.
