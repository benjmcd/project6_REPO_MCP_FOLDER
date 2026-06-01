# 1315 - SEC XBRL Real-Corpus Evidence Reference Reconciliation

Milestone: `sec_xbrl_real_corpus_evidence_reference_reconciliation_v1`

Base authority: `project6-origin/main` at `fe374a2b037015501c609ad84ac7b7444f0f2336`

Prior milestone:

- `next_milestone_plans/Layer3_planning_docs/1314-default-on-admission-restatement.md`

## Status

Branch-local Tier-1 diagnostic/report/docs reconciliation.

This pass resolves an authority-reference inconsistency left visible by the
default-on admission restatement gate. Current committed reports referenced
`diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json`, but PR
#2020 intentionally moved that broad live-matrix report into the archive because
it was not reproducible offline from the available operator inputs.

## Implemented Boundary

Updated diagnostic defaults and regenerated reports so committed `source_reports`
references point at the committed archive artifact:

- `diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate.py`;
- `diagnostics/assessment/sec-xbrl-default-on-runtime.py`;
- `diagnostics/assessment/sec-xbrl-default-posture-decision.py`;
- `diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection.py`;
- `diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight.py`;
- `diagnostics/assessment/sec-xbrl-default-on-admission-restatement.py`.

Regenerated reports:

- `diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json`;
- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json`;
- `diagnostics/assessment/sec-xbrl-default-posture-decision-report.json`;
- `diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json`;
- `diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight-report.json`;
- `diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json`.

## Current Outcome

Repo-confirmed branch-local output:

- committed SEC XBRL report `source_reports` missing-reference count: `0`;
- `sec-xbrl-default-on-admission-restatement-report.json` still emits
  `default_on_admission_restatement_still_blocked`;
- the remaining blocker is
  `default_on_admission_restatement_broader_live_matrix_historical_not_current_runtime_design_authority`;
- `redaction.passed: true`.

This pass does not make the archived broad live-matrix report current runtime
authority. It only makes provenance explicit and resolvable. Runtime default-on
design remains blocked until a future evidence turn produces current broad
real-corpus product-path/default-on authority or selects a replacement report
that covers the same requirements.

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

- Regenerated the six affected reports using their diagnostic scripts.
- `python -m pytest ./backend/tests/test_sec_xbrl_default_on_admission_restatement.py ./backend/tests/test_sec_xbrl_default_posture_decision.py ./backend/tests/test_sec_xbrl_operator_runbook_matrix_selection.py ./backend/tests/test_sec_xbrl_stratified_real_filing_validation_matrix_preflight.py -q`:
  PASS (`24 passed`).
- `python -m pytest ./backend/tests/test_sec_xbrl_default_on_admission_restatement.py ./backend/tests/test_sec_xbrl_broader_corpus_reliability_gate.py ./backend/tests/test_sec_xbrl_default_posture_decision.py ./backend/tests/test_sec_xbrl_operator_runbook_matrix_selection.py ./backend/tests/test_sec_xbrl_stratified_real_filing_validation_matrix_preflight.py -q`:
  PASS (`27 passed`).
- `python -m pytest <backend/tests/test_sec_xbrl*.py files> -q`:
  PASS (`304 passed, 4 warnings`).
- `python -m py_compile` over touched SEC XBRL diagnostic/test Python files:
  PASS.
- JSON validation over manifests and committed SEC XBRL reports with
  `utf-8-sig`: PASS (`56` files).
- Source-report reference scan: PASS (`56` checked, `0` missing).
- Redaction/residual scan over committed SEC XBRL reports: PASS (`54`
  reports, `0` raw accession/CIK/SEC URL/local path/operator contact/decimal
  magnitude hits).
- `git diff --check`: PASS.

## Next Posture

The next safe action is
`sec_xbrl_broad_real_corpus_product_runner_current_authority_renewal_v1`: an
explicitly authorized evidence turn that either regenerates the broad
real-corpus product runner report from valid inputs or replaces it with a
current-authority report that covers companyfacts value correctness,
completeness/DTS coverage, product-path readiness, sidecar selection, and
redaction/non-admission preservation.
