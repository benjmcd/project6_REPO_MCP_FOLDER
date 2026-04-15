# Onlook UI Sandbox

This app is the isolated Onlook-editable sandbox for the NRC APS review lane.

It is not the live review UI.
Live authority remains under:

- `../backend/main.py`
- `../backend/app/api/review_nrc_aps.py`
- `../backend/app/review_ui/static/*`

## Purpose

This sandbox exists to let Onlook edit a separate React and Tailwind surface without changing the current shipped static review UI by default.

Current implemented slice:

- load `GET /api/v1/review/nrc-aps/runs`
- load `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`
- render:
  - run selector
  - pipeline pane
  - tree pane
  - details pane shell

## Local Setup

1. Start the backend review API from the lane root:

```powershell
./tools/start-review-api.ps1
```

2. Create `./.env.local` from `./.env.example`:

```dotenv
NEXT_PUBLIC_REVIEW_API_BASE=http://127.0.0.1:8000/api/v1/review/nrc-aps
```

3. Start the frontend locally:

```powershell
npm run dev -- --hostname 127.0.0.1 --port 3000
```

4. For Onlook usage, point Onlook at this folder as the project root:

- `worktrees/onlook-lane/onlook-ui`

Do not point Onlook at the repo root.

## Operating Rules

- Keep writes inside this app unless a separate repo-confirmed blocker requires more scope.
- Do not modify `../backend/app/review_ui/static/*` from this lane.
- Keep client-side, non-credentialed fetches only for this slice.
- Treat `.env.local` as local machine config only. The committed template is `.env.example`.

## Validation

Frontend checks:

```powershell
npm run lint
npm run build
```

Backend validate-only slice from the lane root:

```powershell
$env:STORAGE_DIR='../pr45-postmerge-audit/backend/app/storage_test_runtime'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest ./backend/tests/test_review_nrc_aps_catalog.py ./backend/tests/test_review_nrc_aps_api.py -p no:cacheprovider
```

## Related Docs

- `../next_milestone_plans/onlook-plan/README.md`
- `../next_milestone_plans/onlook-plan/pilot-plan.md`
- `../next_milestone_plans/onlook-plan/impl-plan.md`
