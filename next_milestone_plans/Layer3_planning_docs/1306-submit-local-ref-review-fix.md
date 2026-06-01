# 1306 - SEC XBRL Controlled Submit Local-Reference Review Fix

Milestone: `sec_xbrl_controlled_value_reveal_submit_local_ref_review_fix_v1`

Base authority: `project6-origin/main` at `4d54fd0b378748e87f877f67814eb346afc4b85b`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1305-submit-hardening.md`

## Status

Branch-local Tier-2 risk-assessed review-thread fix, verified for PR handoff.

This slice closes the late PR #2045 review thread that found the controlled
value-reveal submit raw-reference predicate rejected Windows paths but did not
catch `file://` or Unix local-root references such as `/workspace/raw`.

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

The controlled-submit predicate now reuses the same `file://`, UNC, and Unix
local-root pattern already used by adjacent SEC XBRL operator-review and
value-authority services. Direct service and API tests prove accession-like,
`file:///tmp/raw`, and `/workspace/raw` authority receipt ids fail closed with
`sec_xbrl_controlled_value_reveal_submit_raw_reference_not_admitted` and create
no partial controlled-submit receipt.

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
  files compared with `HEAD`
  - PASS: 0 new or increased numeric tokens
- `git diff --check`
  - PASS

## Next Posture

After this review-thread fix lands and current-main verification remains clean,
continue with controlled-submit post-merge audit closure. Treat rendered value
UI, default-on behavior, export/delivery, and production readiness as separate
admission gates.
