# 1317 - SEC XBRL Default-On Runtime Design

Milestone: `sec_xbrl_default_on_runtime_design_v1`

Base authority: `project6-origin/main` at `9fae22608b977bdf62298ab1120c3ce495ab03d0`

Prior milestones:

- `next_milestone_plans/Layer3_planning_docs/1263-sec-xbrl-default-on-runtime.md`
- `next_milestone_plans/Layer3_planning_docs/1314-default-on-admission-restatement.md`
- `next_milestone_plans/Layer3_planning_docs/1316-broad-real-corpus-authority-renewal.md`

## Status

Docs-only Tier-2 design/pre-review entry. This pass admits no runtime behavior,
schema, persistence, API, UI, source acquisition, Arelle invocation, value
reveal, default-on config change, raw runtime artifact, export/delivery, or
production-readiness claim.

The purpose of this design is to map the now-current broad real-corpus evidence
into the narrowest future default-on runtime implementation that can be reviewed
before any code changes touch the default-on surface.

## Current Authority

Repo-confirmed current main after PR #2063:

- `diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json`
  emits `decision: real_corpus_default_on_validated` and `gate_verdict: PASS`.
- The renewed runner report records `offline_redacted_product_report_import.state:
  passed`, `current_run_live_sec_network_used: false`, and inherited
  live-derived evidence from the imported redacted report.
- The runner summary records 32 filings, 16 issuer hashes, 30 supported records,
  10187 CompanyFacts value comparisons, 0.9897 match rate, 52558 resolved facts,
  and 52558 independent inline facts.
- `diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json`
  emits `decision: default_on_admission_restatement_ready_for_runtime_design`
  with no blocking reasons.
- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json` still emits
  `decision: default_on_runtime_disabled_by_governance_remediation` because
  `backend/app/core/config.py` keeps
  `layer3_sec_edgar_arelle_fact_authority_cutover_enabled` defaulted to `False`.
- `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py`
  already has the fail-closed Arelle-sidecar cutover behavior when the cutover
  flag is enabled: missing sidecar authority returns
  `arelle_sidecar_receipt_required`, records `synchronous_arelle_invocation_performed:
  false`, and records `regex_fallback_performed: false`.
- `backend/tests/test_layer3_api.py` already covers the flag-enabled sidecar
  classification path, missing-sidecar blocking, lineage mismatch blocking, and
  standing non-admissions for final statement semantics and cross-company
  comparability.

## Design Decision

The future runtime implementation should admit Arelle sidecar authority as the
default SEC XBRL fact-authority input only by changing runtime selection policy.
It must not perform source acquisition, invoke Arelle synchronously, persist raw
values, reveal values by default, or make the operator product surface a value
surface.

Default-on means:

1. The bridge selects persisted Arelle sidecar authority as the default fact
   authority path for the admitted SEC XBRL runtime profile.
2. A request without a ready persisted sidecar ID and hash fails closed with the
   existing `arelle_sidecar_receipt_required` posture.
3. Regex authority remains available only as an explicit rollback path, not as a
   silent fallback during default-on operation.
4. Value reveal remains separately gated by the authority-receipt and controlled
   submit chain; default-on Arelle authority does not imply default-on value
   reveal.
5. Existing projection persistence, statement-packet persistence, operator-review
   workflow, decision receipt, value-reveal authority receipt, and controlled
   value-reveal submit tables remain redacted, hash/count-only authority surfaces
   unless a later explicitly scoped implementation changes them.

## Operator-Authentication Decision

The first default-on runtime implementation should treat default-on selection as
a deployment-owned server policy, not as an operator-submitted runtime action.
There must be no public API route, rendered UI control, request field, browser
state, or operator-review decision field that toggles the default-on switch.

For local verification, the implementation can use test-time settings overrides
to prove both default-on and rollback behavior. For any nonlocal or production
enablement claim, the implementation must remain silent unless a separate
deployment/operator authorization record proves who owns the configuration
change. This design therefore explicitly rules out an in-app
operator-authenticated activation step for the first runtime switch, while
requiring the implementation to prove that clients cannot self-authorize or
override the server policy.

## Boundary Map

Future Tier-2 implementation surface:

- `backend/app/core/config.py`: runtime default selection policy for Arelle fact
  authority cutover.
- `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py`:
  only if a policy abstraction is needed to avoid hard-coded flag checks.
- `backend/tests/test_layer3_api.py`: behavior-level default-on, rollback, and
  non-admission tests.
- `diagnostics/assessment/sec-xbrl-default-on-runtime.py` and its committed
  report: gate must verify behavior-level admission, not just a brittle source
  string.
- Planning/proof manifests and the default-on runtime planning doc.

Surfaces that remain out of scope for the first implementation:

- `models.py`, Alembic migrations, new tables, or schema changes.
- Durable persistence changes beyond reading existing sidecar/projection/packet
  authority.
- Backend API contract changes, rendered UI controls, operator workflow
  expansion, source acquisition, Arelle subprocess invocation, export/delivery,
  provider/connector dispatch, raw runtime artifacts, value reveal default-on,
  production-readiness claims, final statement semantics claims, and
  cross-company comparability claims.

## Gate Hardening Required

The current default-on runtime diagnostic checks for the literal source text
`default=True` in `backend/app/core/config.py`. That is too brittle for the
actual risk boundary. The implementation PR should update the diagnostic to
prove the behavior instead:

- default-on profile selects Arelle sidecar authority by default;
- missing sidecar fails closed with no regex fallback;
- explicit rollback profile preserves regex behavior;
- no synchronous Arelle invocation is introduced;
- value reveal and controlled submit defaults remain off;
- source reports and runtime reports remain redacted and path-clean.

This gate-hardening change is part of the default-on implementation because it
prevents a misleading green outcome from a source-string-only flip.

## Rollback And Containment

Rollback must be one-step and non-destructive:

- restore the runtime default selection policy to regex/flag-off behavior;
- keep the Arelle sidecar path available behind explicit opt-in for diagnosis;
- preserve persisted sidecar, projection, statement-packet, operator-review,
  decision, and value-reveal receipt rows without mutation or deletion;
- keep value reveal disabled unless the separate value-reveal flags and receipts
  are explicitly present;
- keep default-on report blockers stable when the default selection policy is
  rolled back.

Any implementation that requires schema downgrade, table rewrite, data deletion,
raw value migration, or source reacquisition is outside this design and must stop
for a separate pre-review.

## Acceptance Criteria For Implementation

The first implementation PR is admissible only if all of the following are true:

- `sec-xbrl-default-on-runtime-report.json` emits `decision:
  default_on_runtime_enabled`.
- The report proves behavior-level default-on selection, sidecar-required
  fail-closed behavior, no regex fallback during default-on, explicit rollback,
  no synchronous Arelle, and value reveal default-off.
- The implementation proves the default-on switch is server/deployment policy
  only: no API/UI/request/browser/operator-review field can toggle it, and no
  production/nonlocal authorization claim is made without separate deployment
  authority.
- Focused runtime tests prove default-on sidecar selection, missing-sidecar
  blocking, lineage mismatch blocking, rollback to regex, and standing
  non-admissions.
- Focused persistence/operator-review/value-reveal tests prove existing
  redacted authority rows remain valid and no value reveal is performed by the
  default-on switch.
- Full `backend/tests/test_sec_xbrl*.py` passes.
- `python ./tools/l3-target-selection-validate.py --expect frozen` passes.
- `python ./tools/l3-progress-check.py` passes.
- Py-compile passes for every touched Python file.
- UTF-8-SIG JSON parse passes for changed reports/manifests.
- Source-report reference validation passes for committed SEC XBRL reports.
- Redaction and residual-magnitude scans pass over committed SEC XBRL reports.
- `git diff --check` passes.

## Branch-Local Verification

Docs-only validation on branch `codex/secxbrl-default-on-runtime-design`:

- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `python -m json.tool` over the progress and proof manifests: PASS.
- `next_milestone_plans/layer3_progress_board.md` includes the merged 1316
  authority-renewal state and this 1317 default-on runtime design posture.
- Added-line redaction/residual scan over this design diff: PASS (`0` hits).
- Committed SEC XBRL report redaction/residual scan: PASS (`43` reports,
  `0` hits).
- `git diff --check`: PASS.

No Python runtime file was touched by this design pass, so py-compile is not
applicable to the branch-local diff.

## Review Checklist

Independent review should focus on:

- whether the runtime policy change is truly default-on and not merely
  test-only opt-in;
- whether rollback is explicit and does not silently mix regex and sidecar
  authority in one default-on execution;
- whether missing or stale sidecar authority creates no partial downstream
  product, operator-review, or value-reveal state;
- whether value reveal remains a separate explicit operator action;
- whether the server/deployment-owned default-on decision is explicit and no
  client/operator runtime input can toggle the switch;
- whether any raw value, accession, CIK, SEC URL, local path, operator contact,
  sidecar payload, value-store payload, or residual magnitude can persist or be
  committed;
- whether diagnostics prove behavior rather than implementation-text shape;
- whether production-readiness, final-statement semantics, and cross-company
  comparability remain non-admitted.

## Next Posture

Next safe implementation lane:

`sec_xbrl_default_on_runtime_v1_tier2_risk_assessed_implementation`

That lane should be code plus report/test updates only for runtime default
selection and gate hardening. It should not add schema, migrations, new
persistence, API/UI, source acquisition, synchronous Arelle, value reveal
default-on, export/delivery, or production-readiness claims.
