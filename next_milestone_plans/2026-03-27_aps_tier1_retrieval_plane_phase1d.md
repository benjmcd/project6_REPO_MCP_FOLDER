# APS Tier1 Retrieval Plane Phase1D

## Status

Planning only. This document freezes the next bounded retrieval-plane milestone after the accepted Phase1C validate-only cutover proof gate. It does not authorize implementation changes by itself.

## Slice Name

`Phase1D: Public Run-Scoped Retrieval Cutover`

## Canonical Authority

Primary live authority for this slice:

- `next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1.md`
- `next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1c.md`
- `docs\postgres\postgres_status_handoff.md`
- `docs\nrc_adams\nrc_aps_reader_path.md`
- `docs\nrc_adams\nrc_aps_status_handoff.md`
- `project6.ps1`
- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\app\services\nrc_aps_content_index.py`
- `backend\app\services\aps_retrieval_plane_read.py`
- `backend\app\services\aps_retrieval_plane_cutover_validation.py`

## Why This Slice Exists

The Phase1 roadmap is now complete through:

- Phase1A shadow retrieval plane
- Phase1B operator retrieval read path
- Phase1C validate-only public cutover proof gate

The next bounded step is therefore the first live-behavior change:

- repoint the already-proven run-scoped public `content-units` surface to the retrieval plane
- repoint the already-proven run-scoped public `content-search` behavior to the retrieval plane when `run_id` is explicitly supplied

This slice is not a general search redesign, not a new route family, and not an auth or feature-flag project.

## In Scope

Phase1D may implement only the following:

1. public default cutover for:
   - `GET /api/v1/connectors/runs/{connector_run_id}/content-units`
   - `POST /api/v1/connectors/nrc-adams-aps/content-search` when `payload.run_id` is explicitly non-empty
2. explicit fail-closed `409` behavior for required run-scoped public requests when retrieval rows are absent or partially materialized
3. focused route or service tests proving the cutover preserves current public schema and deterministic ordering for the run-scoped proof target
4. rerun of the existing Phase1C cutover proof on isolated runtime state

## Out Of Scope

Phase1D must not:

- change omitted-`run_id` public search behavior beyond keeping it explicitly unchanged
- add new public routes, operator routes, or route families
- add hidden headers, query switches, or config flags
- widen request or response schemas
- modify Alembic or ORM models
- change review UI behavior
- add embeddings, vector work, or ranking redesign
- remove the existing operator retrieval routes
- generate or seed business artifacts
- rely on shared checked-in runtime state

## Non-Negotiable Invariants

- canonical APS truth remains `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- `ApsRetrievalChunk` remains fully derived
- public response schemas remain unchanged
- deterministic ordering for the proven run-scoped surfaces must remain unchanged
- run-scoped public requests must not silently fall back to canonical reads when retrieval is absent or partial
- fail-closed public cutover errors must use the existing retrieval-not-materialized semantics
- omitted-`run_id` search remains outside the cutover proof envelope for this slice
- validate-only actions remain validate-only and must not seed or generate artifacts

## Required Decision Outputs

The cutover implementation must make it possible to answer, for the run-scoped public surfaces:

- whether the public routes now default to the retrieval read path
- whether public output shape and ordering remain identical for proven run scopes
- whether absent or partial retrieval materialization yields explicit `409` failure instead of silent fallback
- whether omitted-`run_id` search was left unchanged
- whether the repo now has enough live evidence to discuss later retirement of the operator comparison path

## Tech-Debt Guardrails

This slice exists to reduce cutover debt without widening it.

Do not:

- turn the current public routes into hidden dual-behavior branches
- broaden the cutover into global omitted-`run_id` search redesign
- create a new compatibility shim layer that duplicates canonical and retrieval semantics
- remove the operator comparison routes before public cutover evidence is stable

Expected remaining debt after this slice:

- omitted-`run_id` search still follows the canonical path
- operator and public route duplication remains until a later retirement decision
- retrieval-plane ranking remains lexical-only

## Acceptance Criteria

Phase1D is adequate only if all of the following are true:

- the public run-scoped `content-units` route now defaults to the retrieval read path
- the public `content-search` route now defaults to the retrieval read path when `run_id` is explicitly supplied
- omitted-`run_id` search remains unchanged
- retrieval-not-materialized and partial materialization fail closed with explicit `409` detail
- public request and response schemas remain unchanged
- deterministic ordering is preserved for the proven run-scoped surfaces
- operator routes remain unchanged
- the existing Phase1C cutover proof still passes on isolated runtime state after the cutover
- no review UI regression is introduced
