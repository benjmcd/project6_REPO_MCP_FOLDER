# 1316 - SEC XBRL Broad Real-Corpus Authority Renewal

Milestone: `sec_xbrl_broad_real_corpus_product_runner_current_authority_renewal_v1`

Base authority: `project6-origin/main` at `79b8ab2b70c461323aa905673c1cb0c26729fe3f`

Prior milestones:

- `next_milestone_plans/Layer3_planning_docs/1314-default-on-admission-restatement.md`
- `next_milestone_plans/Layer3_planning_docs/1315-real-corpus-evidence-reference-reconciliation.md`

## Status

Branch-local Tier-1 diagnostic/report/test/docs authority-renewal entry.

This pass renews the broad real-corpus product-runner authority by adding a
fail-closed offline import path for an already-acquired, redacted product-runner
report. The import path validates the supplied report against the supplied
storage marker and matrix plan, recomputes current-code summary and criteria
from the report rows, and records that the current run did not use live SEC
network access or invoke Arelle.

## Implemented Boundary

Updated:

- `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`;
- `backend/tests/test_sec_xbrl_real_corpus_product_runner.py`;
- the downstream validate-only diagnostics that consume the real-corpus runner
  report;
- the regenerated committed SEC XBRL reports.

The runner now accepts `--redacted-product-runner-report` only with
`--storage-dir` and never with `--live`. The import is rejected when the report
is missing, malformed, unredacted, generated from a fake SEC client, lacks live
evidence provenance, has a mismatched storage marker or matrix plan, applies a
runtime default, contains summary mismatches under current code, or fails any
candidate criteria.

## Current Outcome

Branch-local output:

- `diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json`
  emits `decision: real_corpus_default_on_validated`;
- `gate_verdict: PASS`;
- `storage_dir_marker: a26c56586d12f29eb1bc7708`;
- `offline_redacted_product_report_import.state: passed`;
- `live_sec_network_used: true` as inherited report evidence;
- `current_run_live_sec_network_used: false`;
- `current_run_arelle_subprocess_invoked: false`;
- `summary.real_filing_count: 32`;
- `summary.issuer_hash_count: 16`;
- `summary.supported_record_count: 30`;
- `summary.companyfacts_value_compared_count: 10187`;
- `summary.companyfacts_value_match_rate: 0.9897`;
- `summary.resolved_fact_count: 52558`;
- `summary.independent_inline_fact_count: 52558`.

After downstream report regeneration,
`sec-xbrl-default-on-admission-restatement-report.json` emits
`default_on_admission_restatement_ready_for_runtime_design`.

That decision is readiness for a later runtime-design pass only. It does not
turn on runtime defaults and does not authorize production readiness, value
reveal, export/delivery, source acquisition, or Arelle execution.

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

- Focused SEC XBRL authority-renewal suite: PASS (`72 passed`).
- Full `backend/tests/test_sec_xbrl*.py` suite: PASS (`313 passed, 4 warnings`).
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `python -m py_compile` over touched SEC XBRL diagnostic/test Python files:
  PASS.
- UTF-8-SIG JSON parse for manifests and committed SEC XBRL reports: PASS.
- `source_reports` reference scan: PASS (`56` checked, `0` missing).
- Redaction/residual scan over committed SEC XBRL JSON: PASS (`55` files,
  `0` raw accession/CIK/SEC URL/local path/operator contact/decimal magnitude
  hits).

## Next Posture

The next safe action is `sec_xbrl_default_on_runtime_design_v1`: a design and
pre-review pass only. It must map the authority renewed here into a bounded
runtime-default design, rollback/containment notes, operator-authentication
requirements, redaction invariants, and test obligations before any default-on
implementation is attempted.
