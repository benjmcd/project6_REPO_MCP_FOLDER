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

- the historical broad real-corpus runner report is retained only at
  `archive/files_to_be_trashed/2026-05-31-secxbrl/sec-xbrl-real-corpus-product-runner-report.json`;
- current committed reports now reference that archive path instead of the
  removed diagnostics path, so committed `source_reports` are internally
  resolvable;
- that archived broad live-matrix report is not current runtime-design
  authority because PR #2020 recorded that it is not reproducible offline from
  available inputs;
- the active reproducible report is
  `diagnostics/assessment/sec-xbrl-sector-family-real-filer-validation-report.json`,
  which validates the scoped sector-family gate but explicitly keeps the broader
  live-matrix product gate out of scope.

This is an evidence-governance block, not a runtime defect. The broader-corpus
summary still records admitted historical real-product metrics, but the
restatement gate refuses to promote runtime design from archived, non-offline-
reproducible evidence.

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
- `python ./diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate.py`;
  `python ./diagnostics/assessment/sec-xbrl-default-on-runtime.py`;
  `python ./diagnostics/assessment/sec-xbrl-default-posture-decision.py`;
  `python ./diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection.py`;
  `python ./diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight.py`;
  `python ./diagnostics/assessment/sec-xbrl-default-on-admission-restatement.py`:
  PASS; all regenerated report `source_reports` references resolve.
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

The next safe action is an explicitly authorized broad real-corpus evidence
renewal turn: regenerate the broad real-corpus product runner report from valid
offline/live inputs, or select a replacement current-authority report that
actually covers the broad product-path/default-on evidence requirements. Runtime
default-on design remains blocked until this report returns
`default_on_admission_restatement_ready_for_runtime_design`.
