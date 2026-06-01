# 1314 - SEC XBRL Default-On Admission Restatement

Milestone: `sec_xbrl_default_on_admission_restatement_v1`

Base authority: `project6-origin/main` at `4b0a24966b8facf2e47d4fdac8f150a1451c14f1`

Prior milestone:

- `next_milestone_plans/Layer3_planning_docs/1313-default-on-admission-restatement-selection.md`

## Status

Branch-local Tier-1 validate-only diagnostic/report/test entry.

This pass implements the selected default-on admission evidence restatement. It
does not implement runtime default-on behavior, source acquisition, Arelle
execution, value reveal, export/delivery, persistence, schema, API, or UI
behavior.

## Implemented Boundary

Added:

- `diagnostics/assessment/sec-xbrl-default-on-admission-restatement.py`;
- `diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json`;
- `backend/tests/test_sec_xbrl_default_on_admission_restatement.py`.

The diagnostic reads committed JSON reports and current-main source files only.
It fails closed when required reports are missing, malformed, stale, or
contradictory. It emits one of:

- `default_on_admission_restatement_ready_for_runtime_design`;
- `default_on_admission_restatement_still_blocked`;
- `default_on_admission_restatement_conflicting_evidence`.

## Current Outcome

Repo-confirmed branch-local output:

- `decision: default_on_admission_restatement_still_blocked`;
- `ready_for_default_on_runtime_design: false`;
- `redaction.passed: true`;
- `conflicting_reasons: []`.

Primary blockers:

- required committed report
  `diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json` is
  missing;
- committed broader-corpus, default-posture, and operator-runbook reports still
  reference that missing runner report as source evidence;
- because that report is missing, companyfacts value correctness,
  completeness/DTS coverage, product-path readiness, sidecar selection, and
  non-admission/redaction preservation are not re-proven from the required
  committed authority.

This is an evidence-governance block, not a runtime defect. The broader-corpus
summary still records admitted real-product metrics, but the restatement gate
requires the referenced report artifact itself before it can promote the lane to
runtime design.

## Non-Goals

No `models.py`, Alembic migration, schema, durable persistence change, backend
API route, rendered UI control, operator workflow expansion, runtime default-on
behavior, config default change, live SEC network request, source acquisition,
Arelle subprocess invocation, new value reveal, export/delivery, provider or
connector dispatch, raw runtime artifact commitment, operator-authentication
claim, production-readiness claim, cross-company comparability claim, or final
financial-statement semantics claim is admitted by this pass.

## Verification Result

Branch-local verification:

- `python -m pytest ./backend/tests/test_sec_xbrl_default_on_admission_restatement.py -q`:
  PASS (`5 passed`).
- `python ./diagnostics/assessment/sec-xbrl-default-on-admission-restatement.py --output ./diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json`:
  PASS, emitted `default_on_admission_restatement_still_blocked`.
- `python -m pytest <26 backend/tests/test_sec_xbrl*.py files> -q`: PASS
  (`304 passed, 4 warnings`).
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `python -m py_compile ./diagnostics/assessment/sec-xbrl-default-on-admission-restatement.py ./backend/tests/test_sec_xbrl_default_on_admission_restatement.py`:
  PASS.
- UTF-8-SIG JSON parse for committed SEC XBRL reports plus progress/proof
  manifests: PASS.
- Committed SEC XBRL report redaction/residual scan: PASS (`54` reports, `0`
  redaction hits, `0` residual/magnitude hits).
- `git diff --check`: PASS.

## Next Posture

The next safe action is to resolve the missing/stale committed evidence
artifact question without running live acquisition in this lane: either restore
or regenerate the required real-corpus runner report under an explicitly
authorized offline/live evidence turn, then rerun this restatement diagnostic.
Runtime default-on design remains blocked until this report returns
`default_on_admission_restatement_ready_for_runtime_design`.
