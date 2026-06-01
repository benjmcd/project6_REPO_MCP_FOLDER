# 1313 - SEC XBRL Default-On Admission Restatement Selection

Milestone: `sec_xbrl_default_on_admission_restatement_selection_v1`

Base authority: `project6-origin/main` at `d531bfa09dacf6202fb164df84f3e77657c1c553`

Prior milestones:

- `next_milestone_plans/Layer3_planning_docs/1311-rendered-value-ui-post-merge-audit-closure.md`
- `next_milestone_plans/Layer3_planning_docs/1312-rendered-value-ui-review-thread-remediation.md`

## Status

Branch-local Tier-1 design/admission-selection entry.

This pass selects the next downstream SEC XBRL gate: a validate-only default-on
admission evidence restatement. It does not implement runtime default-on
behavior.

## Evidence Basis

Repo-confirmed:

- `diagnostics/assessment/sec-xbrl-default-on-gate-report.json` currently records
  `decision: default_on_admitted_candidate` and `ready_for_default_on: true`.
- `diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json`
  currently records `decision: broader_corpus_reliability_admitted`.
- `diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json` currently
  records `decision: value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings`.
- `diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json`
  currently records `decision: admission_review_requires_post_1966_governance_followup`
  and `ready_for_default_on_runtime_slice: false`.
- The current admission-review blocker is
  `admission_review_post_1966_governance_followup_required`, with evidence that
  companyfacts, completeness, product-path readiness, and sidecar-selection
  default-on evidence must be restated after governance remediation.
- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json` currently
  records `decision: default_on_runtime_disabled_by_governance_remediation`.
- `diagnostics/assessment/sec-xbrl-default-posture-decision-report.json` currently
  selects `explicit_operator_only_default_off_selected`, with default-on Arelle
  cutover, default-on value reveal, and staged default-on experiment deferred.
- `diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json`
  currently records explicit-operator-only policy, default-off runtime posture,
  explicit live-network authorization, and explicit value-reveal confirmation.

## Selection

Select `sec_xbrl_default_on_admission_restatement_v1` as the next admissible
downstream gate.

The selected gate is a Tier-1 validate-only diagnostic/report/test pass that
re-evaluates whether the current default-on evidence still satisfies admission
after the post-governance-remediation body and the rendered controlled
value-reveal UI proof. It must decide whether the existing blocker remains,
is superseded by stronger current-main evidence, or has become a different
blocker.

Do not select runtime default-on enablement, automatic value reveal,
export/delivery, operator-authentication hardening, production readiness,
source acquisition, Arelle invocation, or final financial-statement semantics as
the next implementation boundary.

## Required Inputs

The later implementation must read only committed reports and current-main
source/tests:

- `diagnostics/assessment/sec-xbrl-default-on-gate-report.json`;
- `diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json`;
- `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py` and committed
  report/corpus outputs;
- `diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json`;
- `diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json`;
- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json`;
- `diagnostics/assessment/sec-xbrl-default-posture-decision-report.json`;
- `diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json`;
- current SEC XBRL service/config/test surfaces that prove default-off runtime,
  rollback support, sidecar requirement, redaction posture, and explicit
  value-reveal confirmation.

The implementation must not perform live SEC network access, source acquisition,
Arelle subprocess invocation, new value reveal, or default-on runtime execution.

## Acceptance Criteria

The later restatement gate is acceptable only if it:

1. Fails closed when any required committed source report is missing, malformed,
   stale, contradictory, or not UTF-8-SIG JSON parseable.
2. Explicitly restates companyfacts value correctness, completeness/DTS
   coverage, product-path readiness, and sidecar-selection evidence using
   current-main committed authority.
3. Separates evidence readiness from runtime enablement: `ready_for_default_on`
   may be true while runtime default-on remains false.
4. Preserves explicit operator-only controlled value reveal; default-on value
   reveal remains deferred unless a separate operator policy, authentication,
   retention, audit, and rollback gate is selected later.
5. Preserves rollback criteria: missing or stale sidecar, parser/source lineage
   mismatch, value-store mismatch, Arelle/taxonomy/cache unavailability, or
   redaction violation must block any future runtime cutover.
6. Preserves non-admissions: no production readiness, final financial-statement
   semantics, cross-company comparability, Candidate B SEC routing, RAG/model/
   provider behavior, export/delivery, source acquisition, Arelle execution, raw
   identity commitment, or raw value commitment.
7. Emits a committed report that uses only hashes, counts, forms, booleans,
   reason codes, and redacted summaries; no issuer names, raw CIKs, accessions,
   SEC URLs, local paths, operator contact text, or raw financial values.
8. Records one of three decisions:
   - `default_on_admission_restatement_ready_for_runtime_design`;
   - `default_on_admission_restatement_still_blocked`;
   - `default_on_admission_restatement_conflicting_evidence`.
9. Includes focused tests proving success, stale/missing report fail-closed
   behavior, default-off runtime preservation, redaction scan cleanliness, and
   explicit value-reveal default-off preservation.

## Non-Goals

No `models.py`, Alembic migration, schema, durable persistence change, backend
API route, rendered UI control, operator workflow expansion, runtime default-on
behavior, config default change, live SEC network request, source acquisition,
Arelle subprocess invocation, new value reveal, export/delivery, provider or
connector dispatch, raw runtime artifact commitment, operator-authentication
claim, production-readiness claim, cross-company comparability claim, or final
financial-statement semantics claim is admitted by this selection.

## Verification Result

Branch-local verification:

- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json`:
  PASS.
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json`:
  PASS.
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `git diff --check`: PASS.

## Next Posture

After this selection lands, the next safe implementation pass is
`sec_xbrl_default_on_admission_restatement_v1`: a validate-only diagnostic,
focused tests, committed report, and manifest/proof update. Runtime default-on
design remains a later gate and is admissible only if the restatement report
returns `default_on_admission_restatement_ready_for_runtime_design`.
