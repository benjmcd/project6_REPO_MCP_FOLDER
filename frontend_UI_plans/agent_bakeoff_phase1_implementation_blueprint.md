# Agent Bake-Off Implementation Blueprint: APS Tier1 Retrieval Plane Phase1A

## 1. Purpose

This document freezes the repo-fit file/module ownership plan for the first retrieval-plane bake-off slice.

The goal is to reduce agent guesswork and keep the two implementations comparable.

## 2. Expected File Ownership

### 2.1 Migration Layer

Expected file:

- `backend\alembic\versions\0011_aps_retrieval_chunk_v1.py`

Responsibility:

- define the additive retrieval-plane table
- keep the migration self-contained
- do not alter older APS canonical tables except for normal foreign-key/index references if truly required

### 2.2 Model Layer

Expected modified file:

- `backend\app\models\models.py`

Responsibility:

- add the derived retrieval-plane ORM model
- keep canonical APS models unchanged except for additive relationships if truly necessary

Optional modified file if the repo requires it:

- `backend\app\models\__init__.py`

### 2.3 Service Layer

Expected new files:

- `backend\app\services\aps_retrieval_plane_contract.py`
- `backend\app\services\aps_retrieval_plane.py`
- `backend\app\services\aps_retrieval_plane_validation.py`

Responsibilities:

- `aps_retrieval_plane_contract.py`
  - retrieval contract identifiers
  - source-signature field projection rules
  - shared constants for the retrieval slice
- `aps_retrieval_plane.py`
  - canonical-to-derived row shaping
  - deterministic rebuild logic
  - explicit scope handling
- `aps_retrieval_plane_validation.py`
  - validate-only parity comparison logic
  - mismatch reporting structures
  - empty-scope fail-closed behavior

Do not bury derivation logic inside API handlers, ad hoc scripts, or test-only helpers.

### 2.4 Test Layer

Expected new files:

- `backend\tests\test_aps_retrieval_plane.py`
- `backend\tests\test_aps_retrieval_plane_validation.py`

Optional third focused test file if useful:

- `backend\tests\test_aps_retrieval_plane_contract.py`

Responsibilities:

- row derivation correctness
- source-signature behavior
- validation match/mismatch behavior
- fail-closed semantics

## 3. Explicitly Unwanted Touches

The following files should remain untouched in this slice unless a repo-confirmed blocker requires otherwise:

- `backend\app\api\router.py`
- `backend\main.py`
- `backend\app\review_ui\*`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_*`

If touching any of those becomes necessary, stop and explain the blocker first.

## 4. Data-Model Guardrails

### 4.1 Canonical vs Derived

Do not:

- rewrite canonical APS truth tables
- treat retrieval rows as canonical evidence truth
- move existing APS content-index truth into the retrieval plane

### 4.2 Diagnostics Authority

Use linkage-authoritative `diagnostics_ref` semantics only.

Do not reintroduce document-row fallback behavior.

### 4.3 Search Representation

For this Phase1A slice, the required backend-safe retrieval representation is:

- `search_text`

Do not make a Postgres-specific `search_vector` implementation the blocking center of the round.

If you choose to prepare for later lexical indexing, keep it additive and non-blocking. This bake-off slice is judged on retrieval-plane derivation and validation correctness, not on finishing the later ranking/index-tuning phases.

## 5. Validation Boundary

Validation for this slice should be service-level and test-level.

Do not:

- add public endpoints
- add operator endpoints
- add CLI entrypoints
- add background jobs

unless that is explicitly requested later.

## 6. QA Carry-Forward Rule

This blueprint inherits the latest UI QA findings:

- the review UI baseline is functionally passing
- known remaining issues are polish-level and partial tree-reveal behavior

Therefore:

- do not spend this milestone on review UI cleanup
- if a shared change unexpectedly affects the review UI, treat that as a regression risk and validate against the existing review UI tests
