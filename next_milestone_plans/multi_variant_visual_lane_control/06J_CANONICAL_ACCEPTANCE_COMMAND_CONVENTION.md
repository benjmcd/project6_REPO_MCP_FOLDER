# 06J Canonical Acceptance Command Convention

## Purpose

Freeze the command convention concept for acceptance validation.

## Canonical convention

Run the active test surface from the **repo root** using:

1. a **pytest-family** runner
2. both active test trees:
   - `tests/`
   - `backend/tests/`
3. a bootstrap mechanism that ensures **`backend` is on `sys.path`**

## Why this convention is the safest single choice

### Root tests
`tests/test_nrc_aps_document_processing.py`:
- uses pytest-native features
- computes fixture/storage paths relative to repo-root structure
- explicitly inserts `ROOT / "backend"` into `sys.path`

### Backend tests with no explicit bootstrap
`backend/tests/test_nrc_aps_run_config.py`:
- imports `from app.services ...`
- does not insert backend into `sys.path`

### Backend tests with explicit bootstrap
`backend/tests/test_review_nrc_aps_document_trace_page.py`:
- inserts backend-ish path into `sys.path`
- then imports `main`

## Resulting interpretation

A single safe acceptance convention should:

- execute from repo root so the two active trees are addressed naturally
- provide backend importability for backend tests that do not self-bootstrap
- use pytest-family discovery so pytest-native root tests run correctly

## Canonical command concept

Conceptually, the canonical acceptance command is:

`[backend on sys.path] + [pytest-family runner] + [tests backend/tests]`

## Examples of acceptable realizations

These are examples, not newly verified repo-native scripts:

- repo root + `PYTHONPATH=backend python -m pytest tests backend/tests`
- repo root + equivalent shell-specific env bootstrap + `pytest tests backend/tests`

## What is now ruled out

Do not freeze as canonical:
- plain unittest discovery
- repo-root pytest-family invocation with no backend-path bootstrap
- a convention that targets only one of the two active test trees

## Closure status by layer

### Layer 1 — Conceptual convention
**CLOSED.** The canonical acceptance convention is: repo root + pytest-family + `backend` on `sys.path` + both active trees.

### Layer 2 — Shell-specific realization
**CLOSED.** See `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md` for frozen realizations:
- PowerShell
- Windows CMD
- POSIX shell forms

### Layer 3 — Repo-native enforcement
**NOT YET IMPLEMENTED.** The convention is pack-specified and shell-realized but not visibly enforced via repo-native CI, hooks, or workflow mechanisms. This is a bounded residual tracked in `06L`, not a blocker for the convention itself.
