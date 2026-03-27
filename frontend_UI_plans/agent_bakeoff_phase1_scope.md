# Agent Bake-Off Scope: APS Tier1 Retrieval Plane Phase1A

## 1. Purpose

This document freezes the first bounded implementation slice for the APS Tier1 retrieval-plane bake-off.

It is intentionally narrower than the full Phase 1 plan. The goal is to compare execution quality on a concrete foundational slice, not to let each tool define its own phase boundary.

## 2. Slice Name

`Phase1A: Shadow Retrieval Foundation`

## 3. In Scope

The implementation must include all of the following.

### 3.1 Additive Retrieval Persistence

Add one derived retrieval-plane persistence surface for APS chunk-level rows.

Required shape for this slice:

- one additive model/table representing one APS chunk in one run/target context
- stable identity from canonical APS keys
- explicit derived metadata fields needed for later lexical retrieval and parity checks
- no claim that this table is canonical evidence truth

### 3.2 Explicit Derivation Logic

Add a retrieval-plane materialization service that:

- derives rows only from canonical APS truth
- uses `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`
- preserves linkage-authoritative `diagnostics_ref` semantics
- builds a stable `source_signature_sha256`
- supports deterministic run-scoped rebuild behavior

### 3.3 Validate-Only Parity Logic

Add a validate-only parity service that can compare:

- canonical APS row expectations
- derived retrieval-plane rows

The validator must:

- fail closed on empty runtime/scope
- avoid seeding or generating business artifacts
- surface mismatches explicitly

### 3.4 Focused Tests

Add focused tests for:

- derived row creation
- source-signature stability/change behavior
- linkage-authoritative diagnostics semantics
- empty-scope fail-closed validation
- parity match/mismatch behavior

## 4. Required Fields For This Slice

The derived retrieval row must include, at minimum:

- run identity:
  - `run_id`
  - `target_id`
- canonical content identity:
  - `content_id`
  - `chunk_id`
  - `accession_number`
- chunk order/shape:
  - `chunk_ordinal`
  - `start_char`
  - `end_char`
  - `page_start`
  - `page_end`
- text/source fields:
  - `chunk_text`
  - `chunk_text_sha256`
  - `search_text`
- retrieval-visible metadata:
  - `content_status`
  - `quality_status`
  - `document_class`
  - `media_type`
  - `page_count`
- provenance refs:
  - `content_units_ref`
  - `normalized_text_ref`
  - `blob_ref`
  - `download_exchange_ref`
  - `discovery_ref`
  - `selection_ref`
  - `diagnostics_ref`
  - `visual_page_refs_json`
- derivation metadata:
  - `retrieval_contract_id`
  - `source_signature_sha256`
  - `source_updated_at`
  - `rebuilt_at`
  - `created_at`

## 5. Explicitly Deferred

The following are out of scope for Phase1A:

- live query endpoints over the retrieval plane
- read-path cutover or feature-flagged cutover
- embeddings or vector indexes
- semantic retrieval or ranking
- public API/schema changes
- review UI changes
- operator UI for the retrieval plane
- generalized rebuild scheduler/orchestrator work

## 6. Allowed Repo Surface

This slice should normally touch only:

- `backend/alembic/versions/`
- `backend/app/models/`
- `backend/app/services/`
- `backend/tests/`

Do not touch:

- `backend/app/api/`
- `backend/app/review_ui/`
- `backend/main.py`

unless a repo-confirmed blocker makes that unavoidable. If that happens, stop and explain it rather than broadening scope silently.

## 7. Required Behavioral Rules

### 7.1 Canonical Truth Rule

The retrieval plane is always derived. It is never a new source of evidence truth.

### 7.2 Rebuild Rule

The slice must support a deterministic rebuild for at least one explicit scope:

- per-run rebuild

Support for narrower scopes is allowed but not required in this round.

### 7.3 Source-Signature Rule

The source signature must be derived from canonical APS fields that materially affect retrieval-visible row content.

### 7.4 Fail-Closed Validation Rule

If the validation scope resolves to no APS content truth or no retrieval rows where rows are required, validation must fail closed rather than silently pass.

## 8. Acceptance Criteria

This slice is adequate only if all of the following are true:

- the retrieval plane remains clearly derived
- row identity is deterministic
- derivation uses linkage-authoritative diagnostics semantics
- source-signature hashing is explicit and tested
- parity validation is validate-only and fail-closed
- no public/API/UI read path is changed
- no review UI regression is introduced
- focused tests pass

## 9. Carry-Forward Regression Guardrail

Because the review UI baseline is already live-validated, this slice must not regress these pass conditions even though the slice is backend-focused:

- graph renders
- tree expands
- file click opens drawer
- default run selection remains correct

The remaining polish debt from the latest QA report is not a blocker and is not in scope unless explicitly requested in a later milestone.
