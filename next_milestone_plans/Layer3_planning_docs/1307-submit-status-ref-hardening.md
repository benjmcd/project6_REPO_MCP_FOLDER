# 1307 - SEC XBRL Controlled Submit Status Reference Hardening

Milestone: `sec_xbrl_controlled_value_reveal_submit_status_ref_hardening_v1`

Base authority: `project6-origin/main` at `89e8630068181e7b7484476134338ce470cf3490`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1306-submit-local-ref-review-fix.md`

## Status

Branch-local Tier-2 risk-assessed post-merge audit hardening entry, verified
for PR handoff.

This controlled-submit audit pass found that submit requests rejected raw or
local authority receipt ids before lookup, but status inspection only required
non-empty `sec_xbrl_controlled_value_reveal_submit_receipt_id` text before
looking up the submit receipt. That let accession-, file-URI-, or local-root-like
status ids fall through to the missing-receipt path instead of being rejected as
raw browser authority.

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

`inspect_controlled_value_reveal_submit_status` now applies the same raw/local
authority rejection predicate to the browser-supplied controlled-submit receipt
id before any receipt lookup. Direct service tests cover accession-like,
`file:///tmp/raw`, and `/workspace/raw` ids. The API status route test covers an
accession-like id and confirms the rejected raw id is not echoed in the error
response.

## Verification

Branch-local results:

- `python -m pytest .\backend\tests\test_sec_xbrl_operator_review_workflow.py -q`
  - `72 passed, 3 warnings`
- `python -m pytest <25 backend/tests/test_sec_xbrl*.py files> -q`
  - `299 passed, 4 warnings`
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

After this hardening lands and current-main verification remains clean, record
controlled-submit post-merge audit closure. Treat rendered value UI, default-on
behavior, export/delivery, and production readiness as separate admission gates.
