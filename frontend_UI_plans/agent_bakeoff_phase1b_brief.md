# Agent Bake-Off Brief: APS Tier1 Retrieval Plane Phase1B

## 1. Goal

Build the next bounded retrieval-plane slice on top of the accepted Phase1A foundation:

- add an operator-only retrieval read path
- preserve the existing public APS read path unchanged by default
- prove the retrieval plane can serve the same list/search shapes as the current canonical read surface

## 2. Slice Name

`Phase1B: Operator Retrieval Read Path`

## 3. Core Outcome

At the end of this round, the repo should have:

- one retrieval-plane read service that reads from `aps_retrieval_chunk_v1`
- one operator-only run-scoped list endpoint over the retrieval plane
- one operator-only search endpoint over the retrieval plane
- focused parity-style tests that compare operator retrieval responses to the current canonical APS read path after retrieval rebuild

## 4. Non-Negotiable Invariants

- canonical APS truth remains `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- `aps_retrieval_chunk_v1` remains fully derived
- current public endpoints keep their existing default behavior
- response schemas for the operator-only endpoints must reuse the current public response contracts
- linkage-authoritative `diagnostics_ref` semantics remain intact
- validation and proof remain validate-only and fail closed on empty scope

## 5. Exact Operator-Only Strategy

This round uses explicit operator-only endpoints, not a hidden feature flag on the existing public endpoints.

Required endpoint shapes:

- `GET /api/v1/connectors/runs/{connector_run_id}/_operator/retrieval-content-units`
- `POST /api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search`

Reason:

- keeps default public behavior unchanged
- avoids dual-behavior debt on the same route
- makes operator comparison explicit
- allows schema reuse without public cutover

## 6. Reused Contracts

Required response schema reuse:

- `ConnectorRunContentUnitsPageOut`
- `NrcApsContentSearchOut`

Required request schema reuse:

- `NrcApsContentSearchIn`

No schema widening is allowed in this round unless a repo-confirmed blocker proves the reuse is impossible.

## 7. Carry-Forward QA Guardrail

The validated review UI baseline remains in force.

This round is backend/API-focused, but if a shared edit could affect the review UI baseline, the submission must disclose that risk and run the focused review UI regression suite.

The guardrail conditions remain:

- graph renders
- tree expands
- file click opens drawer
- default run selection remains correct
