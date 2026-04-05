# 06H Acceptance Command Convention Narrowing Report

### Synchronization note
This document is a historical narrowing doc. Its "What remains open" section has since been **closed** by the canonical convention freeze (`06J`) and shell-specific realizations (`06K`). The final section ("Update after this revision") reflects the terminal state. Earlier "still not frozen" items are retained as chronological evidence, not as current-state claims.

---

## Purpose

Narrow the remaining command-convention uncertainty using direct import-path behavior from representative active tests.

## Direct evidence

### Root test behavior
`tests/test_nrc_aps_document_processing.py`:
- imports `pytest`
- inserts `backend` into `sys.path` explicitly:
  - computes repo root from file location
  - inserts `ROOT / "backend"`

Implication:
- this root test can self-bootstrap backend imports.

### Backend test behavior with explicit path bootstrap
`backend/tests/test_review_nrc_aps_document_trace_page.py`:
- inserts `Path(__file__).resolve().parents[1]` into `sys.path`
- imports `main` and app schemas afterward

Implication:
- at least some backend tests are also self-bootstrapping.

### Backend test behavior without explicit path bootstrap
`backend/tests/test_nrc_aps_run_config.py`:
- imports `from app.services import connectors_nrc_adams`
- does **not** insert backend into `sys.path`

Implication:
- at least some backend tests assume `backend` is already on `sys.path`

## Narrowed conclusion

The suite is now known to require:

1. pytest-family execution
2. `backend` available on `sys.path`

This can be satisfied by a future frozen convention such as:
- running from the `backend` directory, or
- setting `PYTHONPATH=backend`, or
- an equivalent bootstrap method

## What is now ruled out

Do not freeze a command convention that assumes:
- repo-root pytest invocation
- with no backend path bootstrap
- and no working-directory adjustment

That is too weak for the current test surface.

## Historical open items before canonical closure

At that stage, still not frozen:
- exact shell form (`pytest ...` vs `python -m pytest ...`)
- exact working directory
- exact environment/bootstrap mechanism that places `backend` on `sys.path`


The earlier open-item section is retained as narrowing history only and should not be read as current-state command uncertainty.


## Update after this revision

The narrowing is now sufficient to freeze a canonical convention concept:
- repo root
- pytest-family
- backend on `sys.path`
- both active test trees

After this narrowing revision, the remaining uncertainty was no longer conceptual and had been reduced to shell-specific expression, which is now closed by `06K`.
