# APS Tier1 Retrieval Plane Phase1C

## Status

Planning only. This document freezes the next bounded retrieval-plane milestone after the accepted Phase1B operator retrieval read path. It does not authorize implementation changes by itself.

## Slice Name

`Phase1C: Validate-Only Public Cutover Proof Gate`

## Canonical Authority

Primary live authority for this slice:

- `next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1.md`
- `docs\postgres\postgres_status_handoff.md`
- `docs\nrc_adams\nrc_aps_reader_path.md`
- `docs\nrc_adams\nrc_aps_status_handoff.md`
- `project6.ps1`
- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\app\services\nrc_aps_content_index.py`
- `backend\app\services\aps_retrieval_plane.py`
- `backend\app\services\aps_retrieval_plane_validation.py`
- `backend\app\services\aps_retrieval_plane_read.py`

## Why This Slice Exists

The Phase1 roadmap in `2026-03-27_aps_tier1_retrieval_plane_phase1.md` is explicit:

- Phase1A built the derived retrieval plane
- Phase1B added an operator-only retrieval read path
- default public cutover is a separate decision gate

The next bounded step is therefore not another live route variant and not a default behavior flip. It is a validate-only proof surface that answers a narrower question:

- is the repo ready to propose a default public cutover for the exact `content-search` and `content-units` surfaces?

## In Scope

Phase1C may implement only the following:

1. one validate-only cutover-proof service that compares:
   - the current canonical public `content-units` behavior for a run
   - the retrieval-plane behavior for that same run
   - the current canonical public `content-search` behavior for a run-scoped query
   - the retrieval-plane search behavior for that same run-scoped query
2. one thin tool wrapper under `tools\` for that validate-only gate
3. one `project6.ps1` validate action that invokes that gate
4. focused isolated tests for the proof service and gate entrypoint

## Out Of Scope

Phase1C must not:

- flip any public route to the retrieval plane
- add hidden headers, query switches, or dual-behavior flags on the current public routes
- add new HTTP routes
- widen request or response schemas
- modify Alembic or ORM models
- change review UI behavior
- add embeddings, vector work, or ranking redesign
- generate or seed business artifacts
- rely on shared checked-in runtime state

## Non-Negotiable Invariants

- canonical APS truth remains `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- `ApsRetrievalChunk` remains fully derived
- the current public `content-search` and `content-units` routes remain unchanged
- validate-only actions stay validate-only and fail closed on empty runtime
- the proof surface must fail closed when retrieval rows are absent or partially materialized for a required run scope
- omitted `run_id` search behavior is not the proof target for this slice; the proof gate is run-scoped
- no checked-in `tests\reports\*.json` refresh is required for this slice

## Required Decision Outputs

The cutover-proof surface must make it possible to answer, for an explicit run scope:

- whether canonical and retrieval results match in item count
- whether canonical and retrieval results preserve the same deterministic order
- whether canonical and retrieval results preserve the same field values for the current public schema
- whether retrieval materialization is missing or partial
- whether the repo has enough evidence to open a later default-cutover decision

## Tech-Debt Guardrails

This slice exists to reduce, not expand, cutover debt.

Do not:

- create a third live read path
- add another operator route family
- hide retrieval behavior behind the existing public routes
- broaden this into a general feature-flag system

This slice should shorten the dual-read window by producing explicit proof evidence rather than by adding another long-lived runtime branch.
