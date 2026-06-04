# P18 Mixed-Source APS Handoff Dispatch Runtime Closeout

Status: current-main runtime implementation verified after PR #2216 and
review-debt follow-up PR #2217.

## Scope

This pass admits one mixed-source APS handoff dispatch state over an already
prepared P17 mixed-source handoff/export state. It uses the existing
`/api/v1/layer3/handoff/aps/dispatch` route, but routes mixed-source requests
by material-authority field presence before selected-pass validation.

The admitted response schema is:

- `layer3.mixed_source_aps_handoff_dispatch.v1`

The admitted package family, handoff target, export mode, APS target, dispatch
mode, and operator decision are:

- `mixed_dataset_document`
- `mixed_source_review_package`
- `reference_envelope_only`
- `mixed_source_aps_evidence_bundle`
- `server_side_mixed_source_aps_handoff`
- `dispatch_mixed_source_aps_handoff`

The implementation records a reference-only APS handoff identity. It does not create an APS evidence-bundle package row, does not persist a local APS bundle artifact, and does not expose local paths.

## Runtime Behavior

The mixed dispatch request admits only:

- `client_request_id`
- `session_id`
- `material_preview_id`
- `material_preview_hash`
- `package_review_preview_hash`
- `contract_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_hashes`
- `package_review_submit_record_ref`
- `package_review_state`
- `prepare_record_ref`
- `handoff_export_state`
- `handoff_export_envelope_ref`
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- `operator_decision`
- optional `decision_notes`
- optional `expected_package_kinds`

Server-side validation recomputes the P14 mixed-source package-review preview,
requires the committed Gate B material authority, loads the P15 reconciliation
record and exactly three package rows, validates P15 construction authority,
validates the P16 approved package-review submit state, and validates the P17
handoff/export prepare record plus reference envelope on the same
reconciliation.

On success, the runtime records exactly one APS handoff dispatch state in:

- `L3ReconciliationRecord.summary_json.aps_handoff_dispatch`
- `L3Session.summary_json.aps_handoff_dispatch`

The recorded state uses public `layer3://mixed-source-package/...` package
refs and a public `layer3://mixed-source-aps-handoff/...` reference-only APS
bundle identity. The state keeps `external_export_enabled`, `download_enabled`,
`connector_dispatch_enabled`, `provider_public_url_enabled`, and
`external_export_download_enabled` false.

## Fail-Closed Cases

The runtime fails closed for:

- missing `client_request_id`
- missing or stale material preview authority
- missing or stale package-review preview hash
- missing or stale contract hash
- missing or stale construction basis hash
- missing or mismatched P15 reconciliation/package state
- partial, extra, or unexpected package rows
- stale or mismatched `output_package_ids`
- stale or mismatched `payload_hashes`
- explicit empty or unexpected `expected_package_kinds`
- missing or mismatched P16 package-review submit state
- non-approved package-review state
- missing or mismatched P17 handoff/export prepare state
- non-prepared handoff/export state
- stale or mismatched reference envelope
- unsupported handoff target, export mode, APS target, dispatch mode, or
  operator decision
- selected-pass lifecycle fields on a mixed-source dispatch request
- request-supplied `payload_refs`
- package payload rewrite or reconstruction fields
- external export/download, provider, connector, destination, signed URL,
  public URL, local outbox, or download fields
- source expansion, parser, schema, migration, local upload, or local directory
  fields
- excluded-tool fields
- existing conflicting APS handoff dispatch state
- selected-pass APS evidence-bundle package rows on the mixed-source path

## Non-Goals

- No rendered UI/static behavior change.
- No external export/download readiness, delivery, download URL, signed
  reference, connector, provider, destination, local outbox, or network egress
  behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction or mutation.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Verification

Branch-local verification passed:

- `python -B -m py_compile ./backend/app/api/layer3.py ./backend/app/services/layer3_handoff_contract.py ./backend/app/services/layer3_workbench.py ./backend/tests/test_layer3_api.py`
- `python -m pytest ./backend/tests/test_layer3_api.py -k "mixed_source_aps_handoff_dispatch_records_reference_state or layer3_handoff_openapi_contracts" --maxfail=1 -q`
  (`2 passed, 290 deselected, 3 warnings`)
- `python -m pytest ./backend/tests/test_layer3_api.py -k "mixed_source_package or mixed_source_handoff_export_prepare_records_reference_envelope or mixed_source_aps_handoff_dispatch_records_reference_state or aps_handoff_dispatch_materializes_owner_service_bundle_without_mutating_sources or aps_handoff_dispatch_prechecks_fail_closed or aps_handoff_dispatch_requires_prepared_state" --maxfail=1 -q`
  (`12 passed, 280 deselected, 3 warnings`)
- `python -m pytest ./backend/tests/test_layer3_api.py -q`
  (`292 passed, 4 warnings`)
- manifest JSON syntax
- Layer 3 authority-index validation
- Layer 3 target-selection frozen validation
- Layer 3 progress check
- `git diff --check`

Detached post-merge proof after PR #2216 passed:

- `python -B -m py_compile ./backend/app/api/layer3.py ./backend/app/services/layer3_handoff_contract.py ./backend/app/services/layer3_workbench.py ./backend/tests/test_layer3_api.py`
- `python -m pytest ./backend/tests/test_layer3_api.py -k "mixed_source_aps_handoff_dispatch_records_reference_state or layer3_handoff_openapi_contracts" --maxfail=1 -q`
  (`2 passed, 290 deselected, 3 warnings`)
- `python -m pytest ./backend/tests/test_layer3_api.py -k "mixed_source_package or mixed_source_handoff_export_prepare_records_reference_envelope or mixed_source_aps_handoff_dispatch_records_reference_state or aps_handoff_dispatch_materializes_owner_service_bundle_without_mutating_sources or aps_handoff_dispatch_prechecks_fail_closed or aps_handoff_dispatch_requires_prepared_state" --maxfail=1 -q`
  (`12 passed, 280 deselected, 3 warnings`)
- `python -m pytest ./backend/tests/test_layer3_api.py -q`
  (`292 passed, 4 warnings`)
- manifest JSON syntax
- Layer 3 authority-index validation
- Layer 3 target-selection frozen validation
- Layer 3 progress check
- `git diff --check`

Review-debt follow-up PR #2217 passed and is merged on current main:

- OpenAPI request schema splits selected-pass and mixed-source APS handoff
  dispatch requests with `oneOf`.
- selected-pass requests carrying blank or null mixed material-authority
  markers fail closed as cross-shape requests instead of silently routing to
  selected-pass behavior.
- focused follow-up tests passed with `3 passed, 289 deselected, 3 warnings`.
- full `backend/tests/test_layer3_api.py` passed with `292 passed, 4 warnings`.
- post-merge manifest JSON syntax, authority-index validation, frozen
  target-selection validation, progress check, and `git diff --check` passed.

PR #2216 review threads are resolved, and PR #2217 has zero review threads.

Current-main docs/control sync verification must include:

- manifest JSON syntax
- Layer 3 authority-index validation
- Layer 3 target-selection frozen validation
- Layer 3 progress check
- `git diff --check`

## Next Posture

After current main is synced, mixed-source external export/download readiness is
the next safe downstream surface to freeze before implementation. That later
pass must decide how reference-only mixed-source APS handoff identity is
converted into external export/download readiness without creating download,
provider, connector, public URL, signed-reference, schema, parser,
source-shape, payload-rewrite, or production-readiness behavior in the freeze
itself.
