# Lane B CI R7 remote closeout

Date: 2026-08-08

Status: `LANE_B_CI_DEBT_RESOLVED_REMOTE_CLOSURE_RECORDED`

## Authority boundary

This closes only the exact 16-file CI-debt correction and its attributable CI
regressions on draft PR #2485. It does not issue P8, a lease, credential access,
egress, launch, merge, ready-for-review, Lane A, or any owner-only act. The PR
remains draft.

## Qualifying code head

Commit `f6ce353336c05491bc5fa9c3da5667974fc83d68` contains the final executable,
workflow, dependency, and test bytes for this correction lane.

GitHub Actions run `31296855809` evaluated that exact head and passed every
required job:

- Windows root/strict proof: 358 passed in 258.47 seconds;
- separate Windows evaluator process: 404 passed in 604.24 seconds;
- all backend, root, and Playwright shards and aggregators;
- backend coverage, Postgres migrations/3C, release lock, NRC APS OCR, SEC XBRL
  Arelle provisioning, and `release-gate`.

## Consecutive code-equivalent confirmation

Commit `498ae8dfc772a563a1ced56ec497e4bf0ca625ae` is the direct docs-only child of
`f6ce353336c05491bc5fa9c3da5667974fc83d68`. Its sole changed path is
`docs/campaign-records/2026-08-08-ci-r6.md`; every executable, workflow,
dependency, and test byte is identical to the qualifying code head.

GitHub Actions run `31297646308` evaluated that code-equivalent child and also
passed every required job:

- Windows root/strict proof: 358 passed in 254.55 seconds;
- separate Windows evaluator process: 404 passed in 724.40 seconds;
- all backend, root, and Playwright shards and aggregators;
- backend coverage, Postgres migrations/3C, release lock, NRC APS OCR, SEC XBRL
  Arelle provisioning, and `release-gate`.

Neither qualifying run used a failed-job retry.

## Closure determination

The coverage inventory and workflow now exercise the previously disclosed
16-file debt, and two consecutive full code-equivalent workflows are green.
The CI-debt acceptance criteria are satisfied; this exact CI debt is no longer
a blocker to a later Lane B transition.

All non-CI gates remain independent. Packet readiness, trusted time, producer
quiescence freshness, owner presentation/acceptance, P8, credential, egress,
launch, clearance, merge, and Lane A must still follow their own controlling
records and may not be inferred from this closeout.

This append-only record does not change the qualifying code bytes. Any workflow
triggered by committing this record verifies the record-bearing head but is not
needed to create or redefine the two-run closure already established above.
