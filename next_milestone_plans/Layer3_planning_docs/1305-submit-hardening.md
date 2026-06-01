# 1305 - SEC XBRL Controlled Submit Hardening

Milestone: `sec_xbrl_controlled_value_reveal_submit_post_merge_audit_hardening_v1`

Base authority: `project6-origin/main` at `f8c50365dc89cec4055a2c8b78ab510841e17488`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1304-controlled-value-reveal-submit.md`

## Status

Branch-local Tier-2 risk-assessed hardening entry, verified for PR handoff.

This post-merge audit slice closes one authority-boundary gap in the controlled
value-reveal submit service. The service already rejected raw references in
`client_request_id`, but the browser-supplied
`sec_xbrl_value_reveal_authority_receipt_id` was only checked as non-empty text.
That meant accession-, URL-, or path-like text in the receipt-id field reached
the missing-authority path instead of being rejected as raw browser authority.

## Scope

This slice changes only:

- `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py`;
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`;
- progress/proof planning records.

It does not add schema, migration, durable persistence, rendered UI, default-on
behavior, source acquisition, live SEC network, Arelle subprocess invocation,
delivery/export, provider dispatch, raw runtime artifacts, production readiness,
or final financial-statement semantics.

## Hardening

The submit service now applies the existing raw-reference rejection predicate to
the supplied authority receipt id before attempting to load the authority row.

Focused regressions prove:

- direct service submit with accession-like authority receipt id fails closed;
- API submit with accession-like authority receipt id fails closed;
- no partial controlled submit receipt is created.

## Verification

Branch-local results:

- `python -m pytest .\backend\tests\test_sec_xbrl_operator_review_workflow.py -q`
  - `70 passed, 3 warnings`
- `python -m pytest <25 backend/tests/test_sec_xbrl*.py files> -q`
  - `297 passed, 4 warnings`
- `python -m py_compile .\backend\app\services\layer3_sec_xbrl_controlled_value_reveal_submit.py .\backend\tests\test_sec_xbrl_operator_review_workflow.py`
  - PASS
- `python .\tools\l3-target-selection-validate.py --expect frozen`
  - `Layer 3 target-selection validation: PASS (frozen)`
- `python .\tools\l3-progress-check.py`
  - `Layer 3 progress state check: PASS`
- JSON parse with `utf-8-sig`
  - PASS for `next_milestone_plans/layer3_progress_manifest.json` and
    `next_milestone_plans/layer3_workbench_proof_manifest.json`
- Redaction identity scan across 53 committed SEC XBRL report JSON files
  - PASS: 0 SEC URLs, accessions, Windows paths, file URIs, or operator emails
- Residual-magnitude regression scan across 53 committed SEC XBRL report JSON
  files compared with `project6-origin/main`
  - PASS: 0 new or increased numeric tokens
- `git diff --check`
  - PASS

## Next Posture

After this hardening lands and current-main verification remains clean, continue
with the read-only controlled-submit post-merge audit outcome and then a
separate rendered value UI or default-on design only if explicitly admitted.
