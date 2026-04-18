# Onlook UI Sandbox

This app is the isolated Onlook-editable sandbox for the NRC APS review lane.

It is not the live review UI.
Live authority remains under:

- `../backend/main.py`
- `../backend/app/api/review_nrc_aps.py`
- `../backend/app/review_ui/static/*`

## Purpose

This sandbox exists to let Onlook edit a separate React and Tailwind surface without changing the current shipped static review UI by default.

Its default import path is now same-origin and fixture-backed:

- the committed `data/fixture.json` index is generated from the existing review API and analyst aliases
- large binary artifacts are split into `data/review-src/*` and `data/candidate-pdf/*` so the Onlook import path stays under the current 10 MB per-file ceiling
- `app/api/[...slug]/route.ts` serves that committed snapshot inside the sandbox itself, so imported previews do not depend on reaching your localhost review API

Current implemented sandbox family:

- `/`
  - loads `GET /api/v1/review/nrc-aps/runs`
  - loads `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`
  - renders the review overview shell
- `/document-trace`
  - loads document selector, manifest, diagnostics, normalized-text, indexed-chunks, and extracted-units review endpoints
- `/workbench-compare`
  - renders the compare shell
  - degrades cleanly when same-checkout compare prep is absent
  - renders populated compare data when same-checkout compare prep is present
- `/candidate-b-trace`
  - reuses compare-family selection
  - renders Candidate-B artifact-backed tabs when same-checkout compare prep is present
- `/analyst-insight`
  - calls the existing aliased stage-1, stage-2, and stage-3 POST endpoints
  - supports the bounded full-flow execution path

## Local Setup

1. Start the frontend locally:

```powershell
npm run dev -- --hostname 127.0.0.1 --port 3000
```

2. For Onlook usage, point Onlook at this folder as the project root.

3. Only start the local review API when you are refreshing the committed fixture snapshot or checking live API parity:

```powershell
./tools/start-review-api.ps1
python ../tools/export-onlook-fixture.py
```

4. Use `./.env.local` only when you intentionally want a local override for direct localhost API development instead of the committed same-origin fixture default.

Lowest-risk default:

- prepare a duplicate first with `../tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy`
- the default scratch target `onlook-ui-copy/` is tracked in the repo `.gitignore`, so duplicate-target work does not depend on workstation-local excludes
- that prep helper now materializes an upload-safe `onlook-ui-copy/.env` containing only the public same-origin `NEXT_PUBLIC_REVIEW_API_BASE=/api/v1/review/nrc-aps`, because Onlook intentionally skips `.env.local` during project upload
- custom visible scratch targets now require `-AllowVisibleTarget` explicitly so duplicate work does not accidentally pollute repo status
- review that duplicate against canonical `onlook-ui/` with `../tools/diff-onlook-copy.ps1 -TargetDir onlook-ui-copy`
- import that duplicate into Onlook
- leave `onlook-ui/` untouched unless direct canonical write-back is intentional

Do not point Onlook at the repo root.

## Operating Rules

- Keep writes inside this app unless a separate repo-confirmed blocker requires more scope.
- Do not modify `../backend/app/review_ui/static/*` from this lane.
- Keep client-side, non-credentialed fetches only for this sandbox family.
- Treat `.env.local` as an optional local override only. The committed default is `.env.example`.
- Treat the duplicate-target `.env` created by `../tools/prep-onlook-copy.ps1` as upload-only public config, not as canonical sandbox source.
- Treat same-checkout compare prep as an opt-in local runtime/input layer for populated compare-family validation, not as an always-present product dependency.
- Treat `data/fixture.json`, `data/review-src/*`, and `data/candidate-pdf/*` as the canonical import-safe snapshot for the sandbox lane.

## Validation

Frontend checks:

```powershell
npm run lint
npm run build
```

Backend validate-only slice from the lane root:

```powershell
$runtimeRoot = (Resolve-Path ./backend/app/storage_test_runtime).Path
$env:STORAGE_DIR=$runtimeRoot
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest ./backend/tests/test_review_nrc_aps_catalog.py ./backend/tests/test_review_nrc_aps_api.py -p no:cacheprovider
```

Same-checkout compare prep validation when populated compare-family routes are needed:

```powershell
./../../.venvs/phase7a-py311/Scripts/python.exe ../tools/seed_wb_compare.py --runtime-root ../backend/app/storage_test_runtime/lc_e2e/wb-b0 --visual-lane-mode baseline
./../../.venvs/phase7a-py311/Scripts/python.exe ../tools/seed_wb_compare.py --runtime-root ../backend/app/storage_test_runtime/lc_e2e/wb-a0 --visual-lane-mode candidate_a_page_evidence_v1
./../../.venvs/phase7a-py311/Scripts/python.exe ../tools/run_nrc_aps_candidate_b_compare.py
python ../tools/validate_wb_prep.py
```

Tracked sandbox browser smoke before any duplicate-target Onlook proof:

```powershell
../tools/run-onlook-sandbox-smoke.ps1 -Profile core
../tools/run-onlook-sandbox-smoke.ps1 -Profile full
../tools/run-onlook-sandbox-smoke.ps1 -Profile full -AppDir onlook-ui-copy
```

Meaning:

- `core` starts an isolated sandbox dev server and proves the hydrated review, document-trace, and analyst-insight routes against the committed same-origin fixture snapshot
- `full` adds the same-checkout compare-family proof by consuming the recommended URLs emitted by `../tools/validate_wb_prep.py` and remapping those live review URLs into the sandbox fixture route table
- `-AppDir onlook-ui-copy` lets the same proof run against a prepared duplicate target before import
- both profiles stop after browser proof; they do not import a duplicate target into Onlook or exercise the Onlook editor/write-back path

Tracked duplicate-target Onlook operator proof:

```powershell
../tools/run-onlook-operator-proof.ps1
```

Meaning:

- the operator proof imports a prepared duplicate target into local Onlook, verifies that the duplicate still has the import-safe fixture API route and a sub-10 MB fixture index, restarts the expected local Onlook clone once if a reused browser session is stale, and proves trusted preview navigation across the full sandbox route family
- it also runs the analyst flow and proves duplicate-only write-back while restoring the duplicate proof file and leaving canonical `onlook-ui/` untouched
- use it after `../tools/run-onlook-sandbox-smoke.ps1 -Profile full -AppDir onlook-ui-copy` when you need editor-side proof rather than browser-only route proof

## Related Docs

- `../next_milestone_plans/onlook-plan/README.md`
- `../next_milestone_plans/onlook-plan/pilot-plan.md`
- `../next_milestone_plans/onlook-plan/impl-plan.md`
