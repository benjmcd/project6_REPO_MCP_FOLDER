# P18 Current-Main Sync

Status: docs/control current-main sync only. Live `project6-origin/main` is
`a182a33e32eea7b235859fd23cbe40c06307ed09`.

## Scope

This sync records that P18 mixed-source APS handoff dispatch is current-main
runtime behavior after PR #2216 and review-debt follow-up PR #2217.

PR #2216 implemented only reference-only mixed-source APS handoff dispatch over
the already-live P17 handoff/export prepare state. PR #2217 fixed the APS
dispatch OpenAPI request contract so selected-pass and mixed-source request
shapes are explicit, and added regression proof that blank or null mixed
material-authority markers fail closed instead of falling through to selected
pass behavior.

## Authority

- P18 freeze: `41-p18-mixed-aps-handoff-freeze.md`
- P18 runtime closeout: `42-p18-runtime-closeout.md`
- Runtime merge: PR #2216 at
  `7c8c7fcd2cef4228b7fff17645920ea75ef53eeb`
- Review-debt merge: PR #2217 at
  `a182a33e32eea7b235859fd23cbe40c06307ed09`

## Non-Goals

- No runtime code change in this sync.
- No rendered UI/static behavior change.
- No backend route, DTO, schema, model, or migration change.
- No parser behavior or source-shape expansion.
- No package construction, package-review submit, or handoff/export prepare
  behavior change.
- No package payload rewrite, reconstruction, or mutation.
- No APS evidence-bundle package row creation.
- No local artifact, local path, local outbox, connector, provider,
  destination, credential, or network behavior.
- No external export/download readiness, delivery, download URL, signed
  reference, public URL, or provider URL behavior.
- No excluded-tool behavior.
- No production-readiness activation.

## Verification

Post-merge proof from detached current main passed:

- `python -B -m py_compile ./backend/app/api/layer3.py ./backend/app/services/layer3_handoff_contract.py ./backend/app/services/layer3_workbench.py ./backend/tests/test_layer3_api.py`
- `python -m pytest ./backend/tests/test_layer3_api.py -k "mixed_source_aps_handoff_dispatch_records_reference_state or layer3_handoff_openapi_contracts" --maxfail=1 -q`
  (`2 passed, 290 deselected, 3 warnings`)
- `python -m pytest ./backend/tests/test_layer3_api.py -k "mixed_source_package or mixed_source_handoff_export_prepare_records_reference_envelope or mixed_source_aps_handoff_dispatch_records_reference_state or aps_handoff_dispatch_materializes_owner_service_bundle_without_mutating_sources or aps_handoff_dispatch_prechecks_fail_closed or aps_handoff_dispatch_requires_prepared_state" --maxfail=1 -q`
  (`12 passed, 280 deselected, 3 warnings`)
- `python -m pytest ./backend/tests/test_layer3_api.py -q`
  (`292 passed, 4 warnings`)
- focused PR #2217 follow-up tests
  (`3 passed, 289 deselected, 3 warnings`)
- manifest JSON syntax
- `python -B ./tools/l3-authority-index-validate.py`
- `python -B ./tools/l3-target-selection-validate.py --expect frozen`
- `python -B ./tools/l3-progress-check.py`
- `git diff --check`

GitHub proof:

- PR #2216 merged, two review threads resolved.
- PR #2217 merged, zero review threads.

## Next Posture

The next mixed-source pass is to freeze external export/download readiness as
the exact downstream surface before implementation. The freeze may use the
current-main P18 reference-only mixed-source APS handoff identity as authority,
but must not create download, delivery, connector, provider, destination,
signed-reference, public URL, local outbox, schema, parser, source-shape,
payload-rewrite, excluded-tool, or production-readiness behavior by itself.
