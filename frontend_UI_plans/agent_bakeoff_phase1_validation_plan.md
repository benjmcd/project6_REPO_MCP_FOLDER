# Agent Bake-Off Validation Plan: APS Tier1 Retrieval Plane Phase1A

## 1. Purpose

This document defines the minimum validation bar for the first retrieval-plane bake-off slice.

The goal is to ensure the two outputs are judged on the same correctness obligations.

## 2. Validation Principles

- validate-only actions remain validate-only
- validation must fail closed on empty runtime/scope
- validation must not seed or generate business artifacts
- canonical APS truth remains the comparison authority
- later UI polish debt is not a blocker for this slice, but existing review UI behavior must not regress

## 3. Required Validation Areas

### 3.1 Retrieval Row Derivation

Must prove:

- one derived retrieval row is produced per intended APS chunk/run/target context
- identity fields are deterministic
- retrieval-visible metadata is copied/derived from canonical truth coherently

### 3.2 Source Signature

Must prove:

- the source signature is stable when source fields are unchanged
- the source signature changes when material source fields change

### 3.3 Diagnostics Authority

Must prove:

- `diagnostics_ref` follows linkage-authoritative semantics
- document-row fallback is not used as the retrieval-plane authority

### 3.4 Parity Validation

Must prove:

- parity validation passes when canonical and derived rows agree
- parity validation reports mismatches explicitly when they disagree
- parity validation fails closed on empty scope

### 3.5 Non-Regression Boundary

If any shared model/service touch could affect the existing review UI baseline, re-run the focused review UI suite.

The carried-forward baseline that must not regress:

- graph renders
- tree expands
- file click opens drawer
- default run selection resolves correctly

## 4. Required Test Files

Expected focused tests:

- `backend\tests\test_aps_retrieval_plane.py`
- `backend\tests\test_aps_retrieval_plane_validation.py`

Optional:

- `backend\tests\test_aps_retrieval_plane_contract.py`

## 5. Required Commands

At minimum, the submission should run the new focused retrieval-plane tests.

If shared code paths are touched in a way that could affect the review UI baseline, also run:

```powershell
python -m pytest tests\test_review_nrc_aps_api.py tests\test_review_nrc_aps_catalog.py tests\test_review_nrc_aps_details.py tests\test_review_nrc_aps_graph.py tests\test_review_nrc_aps_page.py tests\test_review_nrc_aps_tree.py
```

If that review-UI suite is not run, the submission must explicitly state why it was unnecessary.

## 6. Required Reporting

Each submission must report:

- exact test commands run
- pass/fail counts
- whether any migration/schema checks were performed
- whether the review UI regression suite was run
- any tests intentionally not run

## 7. Failure Conditions

The slice should be treated as inadequately validated if:

- it only proves migration import without row-derivation tests
- it passes on an empty scope that should fail closed
- it cannot explain the source-signature basis
- it silently ignores diagnostics-authority mismatches
- it causes review UI regressions and does not disclose them
