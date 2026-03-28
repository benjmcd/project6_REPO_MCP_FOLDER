# Agent Bake-Off Brief: APS Tier1 Retrieval Plane Phase1C

## 1. Goal

Build the next bounded retrieval-plane slice on top of the accepted Phase1B operator read path:

- add a validate-only proof gate for the exact public `content-units` and `content-search` surfaces
- keep every current HTTP route unchanged
- produce explicit parity evidence for or against a later default-cutover proposal

## 2. Slice Name

`Phase1C: Validate-Only Public Cutover Proof Gate`

## 3. Core Outcome

At the end of this round, the repo should have:

- one validate-only service that compares canonical public read behavior to retrieval-plane read behavior for run-scoped requests
- one thin gate wrapper under `tools\`
- one `project6.ps1` validate action for that gate
- focused isolated tests that prove match, mismatch, empty-runtime, and retrieval-not-materialized behavior

## 4. Non-Negotiable Invariants

- canonical APS truth remains `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- `ApsRetrievalChunk` remains fully derived
- current public routes remain unchanged
- this slice does not authorize a default cutover
- this slice does not authorize hidden flags or alternate behavior on the existing public routes
- validate-only behavior remains validate-only and fails closed on empty runtime
- run-scoped proof is the required proof target; omitted-`run_id` search remains outside this round's proof obligation

## 5. Exact Strategy

This round should validate readiness for a later cutover decision without changing live behavior.

The validate-only proof gate must compare:

- canonical run-scoped `content-units`
- retrieval run-scoped `content-units`
- canonical run-scoped `content-search`
- retrieval run-scoped `content-search`

It must report explicit mismatch classes instead of inferring readiness from passing route smoke alone.

## 6. Tech-Debt Target

Phase1C exists to control cutover debt.

Good outcomes:

- explicit proof surface
- explicit mismatch categories
- shorter path to a future cutover decision

Bad outcomes that are forbidden:

- another live route family
- hidden behavior switches on the public routes
- silent broadening into feature-flag or auth-system work

## 7. Carry-Forward QA Guardrail

The validated review UI baseline remains in force.

This round should not touch review UI code. If a shared edit could plausibly affect the review UI baseline, the submission must disclose that risk and run the focused review UI regression suite.
