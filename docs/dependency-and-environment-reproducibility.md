# Dependency & Environment Reproducibility

How the backend's Python dependencies are pinned, why, and how to set up a
reproducible local environment that matches CI. This reflects the state after the
dependency-authority pin and release-lock reproducibility lanes landed.

## Release install authority

`backend/requirements.txt` remains the human-maintained input file with bounded
ranges where the app intentionally permits them. The deterministic release install
authority is `backend/requirements.lock.txt`.

The lock is generated with Python 3.12 using:

```
pip-compile --allow-unsafe --generate-hashes --output-file=backend/requirements.lock.txt --strip-extras backend/requirements.txt
```

The checked-in lock declares `--require-hashes`, pins every resolved Python package
with `==`, and carries SHA-256 hashes for the resolved artifacts. Do not update
versions as part of a reproducibility check; regenerating or changing pins is a
separate owner decision.

CI and the production image both consume the lock in hash-checking mode:

- `.github/workflows/playwright.yml` job `release-lock-install` runs on Python 3.12
  and executes `pip install --require-hashes -r ./backend/requirements.lock.txt`.
- `Dockerfile.app` uses a digest-pinned `python:3.12-slim` base image, copies
  `backend/requirements.lock.txt`, and runs
  `pip install --no-cache-dir --require-hashes -r requirements.lock.txt` before
  copying application code.
- `backend/tests/test_release_identity.py` guards the lock header, hash mode,
  Dockerfile install order, source SHA build argument, and CI job wiring.

For release/prod reproducibility, validate the lock path, not the range input:

```
python -m pytest backend/tests/test_release_identity.py backend/tests/test_release_readiness.py -q
python ./scripts/release_readiness_check.py
```

The full wheel-install proof is the Python 3.12 Linux CI/prod path above. On
Windows, use the static lock/Dockerfile tests locally or build `Dockerfile.app`;
do not treat a Windows wheel-selection mismatch as release drift unless the Linux
CI/prod lock install also fails.

## FastAPI is pinned to a single authority

The repository pins **`fastapi==0.137.2`** as the one supported version. The pin
lives in:

- `backend/requirements.txt` (base app runtime)
- `backend/tests/requirements-layer3-api.txt` (Layer 3 API test stack — what CI installs)
- `handoff/backend/requirements.txt` (tracked handoff mirror)

`backend/tests/requirements-browser.txt` and `backend/tests/requirements-layer3-arelle.txt`
**inherit** that authority — they must not carry a second FastAPI constraint.

### Why a single pin (history)

For most of development the repo declared `fastapi>=0.115`, which a clean resolver
selects as `0.137.2` / `starlette 1.3.1`. CI therefore ran on `0.137.2`. A local
global environment could still show `fastapi 0.111` — but that came from an
**out-of-repo** tool (`session-workbench`, which requires 0.111), not from any
tracked repo manifest. The floating range plus that out-of-repo 0.111 produced a
local-vs-CI drift that cost several debugging cycles. Pinning to the version CI
already used removes the drift without changing behavior (the full backend suite is
identical before and after the pin: 3634 passed, 13 skipped).

## The FastAPI `include_router` version gotcha

FastAPI changed `include_router` around 0.115: it inserts a lazy `_IncludedRouter`
node instead of flattening a sub-router's routes into `app.router.routes`. So naive
introspection like `for r in app.router.routes: ...` finds **0** included routes
under >=0.115, even though the app serves them all. Production is unaffected (the app
uses a static pre-body registry and never iterates routes; `app.openapi()` is fine).

Test-time route introspection must use the version-robust helper at
`backend/tests/_route_enum.py` (`iter_api_routes` / `post_routes`), which resolves an
`_IncludedRouter` via its `effective_route_contexts()` and otherwise iterates flatly
and descends `Mount`s. It matches `app.openapi()` on both 0.111 and 0.137.

## Reproducible setup

Pick the requirements file for the task:

| Purpose | Install |
| --- | --- |
| Release/prod app runtime | `pip install --require-hashes -r backend/requirements.lock.txt` |
| Editable local app development | `pip install -r backend/requirements.txt` |
| Layer 3 API tests (what CI runs) | `pip install -r backend/tests/requirements-layer3-api.txt` |
| Browser/Playwright harness | `pip install -r backend/tests/requirements-browser.txt` |
| SEC/Arelle (optional, default-off) | `pip install -r backend/tests/requirements-layer3-arelle.txt` |

Python runtime: **3.12** (matches CI). Use a per-project virtual environment — do not
install repo requirements into a global environment that also hosts unrelated tools
(e.g. `session-workbench`, which pins an older FastAPI), or they will conflict.

### Reproducing CI's FastAPI locally

If your global interpreter has a different FastAPI, create a temp venv that layers the
CI pin over the system packages, **outside** the repo tree so it is never committed:

```
python -m venv --system-site-packages <TEMP>/.venv-ci
<TEMP>/.venv-ci/Scripts/python.exe -m pip install -r backend/tests/requirements-layer3-api.txt
<TEMP>/.venv-ci/Scripts/python.exe -m pytest backend/tests -q
```

Run the same tests under the global interpreter too; both must pass.

## Optional heavyweight stacks stay optional

Tesseract OCR (a system binary, not a pip package) and the SEC/Arelle stack are
**not** required for a base install and are **default-off**: they are provisioned
only in their own dedicated paths/jobs, with pinned versions and (for Arelle)
versioned taxonomy artifacts. Keep those out of the base app install so a clean
environment installs reproducibly without them.

Note: the **PaddleOCR advanced-table stack** (`paddlepaddle`, `paddleocr`) is, by
contrast, currently declared in `backend/requirements.txt` under the
`# Advanced Table and OCR` comment, so a clean `pip install -r backend/requirements.txt`
**does** pull it (it additionally needs OS-level Ghostscript/Poppler to function).
Only Tesseract and SEC/Arelle are the out-of-base optional stacks described here.

## POSIX executable-bit gotcha in tests

`os.access(path, os.X_OK)` is always `True` on Windows but honors the execute bit on
Linux CI. A test that creates a mock executable file must `chmod(0o755)` it, or the
"is this binary runnable" check passes locally and fails in CI.
