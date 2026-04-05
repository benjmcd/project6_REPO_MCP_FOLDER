# 06K Shell-Specific Canonical Acceptance Commands

## Purpose

Provide shell/platform-specific realizations of the already-frozen canonical acceptance convention:

- run from repo root
- use pytest-family execution
- ensure `backend` is on `sys.path`
- target both active trees:
  - `tests/`
  - `backend/tests/`

## Live evidence supporting minimal env assumptions

`tests/test_nrc_aps_document_processing.py` sets defaults with `os.environ.setdefault(...)` for:
- `DATABASE_URL`
- `STORAGE_DIR`
- `DB_INIT_MODE`
- NRC APS key/base-url placeholders

This means the command examples do not need to hardcode those values just to express the canonical convention.

## Canonical realizations

### PowerShell
From repo root:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest tests backend/tests
```

### Windows CMD
From repo root:

```cmd
set PYTHONPATH=backend && python -m pytest tests backend/tests
```

### POSIX shells
From repo root:

```bash
PYTHONPATH=backend python -m pytest tests backend/tests
```

## Why `python -m pytest` is used here

The pack previously closed:
- pytest-family is required
- repo root is the canonical working location
- backend must be on `sys.path`

Using `python -m pytest` is the most portable shell-level realization of that canonical convention.

## Acceptable equivalent forms

These remain acceptable if they preserve the same semantics:
- `pytest tests backend/tests` with an equivalent backend-path bootstrap already active
- virtual-environment-specific Python launcher variants that still execute from repo root and put `backend` on `sys.path`

## Not canonical

Do not treat these as canonical:
- repo-root execution with no backend-path bootstrap
- unittest-only discovery
- commands that target only one active tree
