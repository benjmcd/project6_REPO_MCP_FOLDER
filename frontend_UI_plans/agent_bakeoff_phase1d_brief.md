# Agent Bake-Off Brief: APS Tier1 Retrieval Plane Phase1D

## 1. Goal

Build the next bounded retrieval-plane slice on top of the accepted Phase1C cutover proof gate:

- repoint the already-proven run-scoped public `content-units` surface to the retrieval plane
- repoint the already-proven run-scoped public `content-search` behavior to the retrieval plane when `run_id` is explicitly supplied
- keep omitted-`run_id` search unchanged

## 2. Slice Name

`Phase1D: Public Run-Scoped Retrieval Cutover`

## 3. Core Outcome

At the end of this round, the repo should have:

- the public run-scoped `content-units` route delegating to the retrieval read path by default
- the public `content-search` route delegating to the retrieval read path when `payload.run_id` is explicitly non-empty
- explicit fail-closed `409` behavior when required retrieval rows are absent or partial
- focused isolated tests proving schema and order preservation and no-fallback semantics

## 4. Non-Negotiable Invariants

- canonical APS truth remains `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- `ApsRetrievalChunk` remains fully derived
- public response schemas remain unchanged
- run-scoped public cutover must not silently fall back to canonical reads
- omitted-`run_id` search remains outside this cutover and must stay explicitly unchanged
- operator retrieval routes remain available and unchanged in this round
- validate-only actions remain validate-only and must not seed or generate artifacts

## 5. Exact Strategy

This round should cut over only the public surfaces that Phase1C already proved:

- `GET /api/v1/connectors/runs/{connector_run_id}/content-units`
- `POST /api/v1/connectors/nrc-adams-aps/content-search` when `run_id` is explicitly supplied

The implementation must preserve:

- current public schema
- deterministic ordering
- fail-closed retrieval-not-materialized behavior

It must not:

- touch omitted-`run_id` search behavior
- add route switches, flags, or alternate headers
- add another route family

## 6. Tech-Debt Target

Phase1D exists to reduce dual-read debt without creating hidden compatibility debt.

Good outcomes:

- one explicit public cutover for the proven run-scoped surfaces
- no silent fallback
- narrower gap between operator comparison and public default behavior

Bad outcomes that are forbidden:

- public routes with hidden dual behavior
- broad omitted-`run_id` redesign
- a new long-lived compatibility layer that duplicates canonical and retrieval semantics

## 7. Carry-Forward QA Guardrail

The validated review UI baseline remains in force.

This round should not touch review UI code. Because `router.py` is expected to change, the submission must rerun the focused review UI regression suite and disclose the result explicitly.
