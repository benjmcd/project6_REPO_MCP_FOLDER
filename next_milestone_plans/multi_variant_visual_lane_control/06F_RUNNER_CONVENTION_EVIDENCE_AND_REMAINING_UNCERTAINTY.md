# 06F Runner Convention Evidence and Remaining Uncertainty

### Synchronization note
This document is a historical narrowing doc. Its earlier sections carry progressively narrower "still open" language that has since been **closed** by the canonical convention freeze (`06J`) and shell-specific realizations (`06K`). The final section ("Closure after this revision") reflects the current state. Earlier "remaining uncertainty" and "what it does not resolve" sections are retained as chronological evidence of the narrowing process, not as current-state claims.

---

## Verified live evidence

### Root packaging surface
`package.json` exists at repo root.

Observed:
- `scripts` is an empty object
- no Python test runner command is defined there
- description text warns that `tests/...` and `tools/...` paths should not be trusted unless on-disk presence is directly confirmed

### On-disk presence
The live repo does contain:
- `tests/`
- `backend/tests/`

### Search evidence
No live `pytest` string references were found in the scanned root/docs/backend/tests/tools surfaces during this pass.

## Interpretation

This narrows the runner-convention uncertainty:

- there is no obvious repo-advertised Python wrapper command at root via `package.json`
- bare `pytest ...` remains a plausible candidate command form
- but it is still not frozen as authoritative repo convention

## Historical policy at that stage

The control pack may continue to use `pytest ...` as a **candidate** command shape in the command matrix, but must not present it as fully frozen repo convention until one of the following is verified:

1. a live wrapper/script/config surface explicitly defines the runner, or
2. local execution evidence confirms the exact accepted invocation form.

## What this resolves

It reduces one kind of uncertainty:
- there is no visible root `package.json` script-based Python test wrapper to account for

## What it had not yet resolved at that stage

It does not yet freeze:
- working directory,
- environment requirements,
- whether the intended invocation is `pytest ...` vs `python -m pytest ...`,
- any local helper scripts outside the currently verified authority surfaces.


## Additional negative evidence from this pass

Direct file/search checks also found:
- no `pytest.ini`
- no `conftest.py`
- no `tox.ini`
- no `noxfile.py`
- no `Makefile`

This further narrows the uncertainty:
there is still no visible repo-advertised Python runner/config surface in the scanned authority areas.


## Additional direct framework evidence

### Root tests
`tests/test_nrc_aps_document_processing.py` directly uses:
- `import pytest`
- `@pytest.mark.parametrize`
- `pytest.raises`
- `monkeypatch` fixture

This proves the active root suite is pytest-native.

### Backend tests
`backend/tests/test_nrc_aps_run_config.py` directly uses:
- `import unittest`
- `unittest.TestCase`

This proves the backend suite includes unittest-style tests.

## Updated interpretation

The active suite is mixed-style but pytest-required:

- pytest is required because root tests use pytest-only features
- unittest alone is insufficient
- pytest-family invocation is therefore no longer speculative

## Historical uncertainty before canonical closure

At that stage of narrowing, what still was not frozen:
- exact shell entry form: `pytest ...` vs `python -m pytest ...`
- exact working directory
- exact env/bootstrap requirements


## Additional direct import-path implication

The active suite is not only pytest-required; it also has mixed import-path assumptions:

- some root/backend tests explicitly insert backend into `sys.path`
- at least one backend test (`test_nrc_aps_run_config.py`) imports `app...` without doing so

Updated implication:
the safe provisional convention is **pytest-family execution with backend on `sys.path`**.


## Canonical convention after this revision

The command-convention concept is now frozen as:

- repo-root execution
- pytest-family runner
- backend on `sys.path`
- both active trees included: `tests/` and `backend/tests/`

At that stage, only shell/platform-specific spelling still remained open.


The sections above are retained as narrowing history only. They are not the current-state canonical acceptance position.


## Closure after this revision

The shell/platform-specific spelling item is now closed by `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md`.
No runner-convention uncertainty remains for the canonical acceptance path.
