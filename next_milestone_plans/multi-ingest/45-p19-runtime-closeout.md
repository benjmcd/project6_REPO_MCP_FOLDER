# P19 Mixed-Source External Export/Download Readiness Runtime Closeout

Status: current-main runtime implementation verified after PR #2220. Current
main sync is recorded by `46-p19-current-main-sync.md` at live
`project6-origin/main` `9e4451cb710c0185a64f1788b9e0d848be7dbc8b`.

## Scope

This pass admits exactly one mixed-source external export/download readiness
state over the already recorded P18 reference-only mixed-source APS handoff
dispatch state selected by `44-p19-mixed-export-download-readiness-freeze.md`.

The admitted response schema is:

- `layer3.mixed_source_external_export_download_readiness.v1`

The admitted package family, handoff target, export mode, APS target, dispatch
mode, readiness state, and operator decision are:

- `mixed_dataset_document`
- `mixed_source_review_package`
- `reference_envelope_only`
- `mixed_source_aps_evidence_bundle`
- `server_side_mixed_source_aps_handoff`
- `mixed_source_external_export_download_ready`
- `record_mixed_source_external_export_download_readiness`

The runtime records readiness identity only. It does not deliver an export,
stream or expose a download, generate a signed reference, produce a public or
provider URL, dispatch a connector, write a local outbox record, create new
package rows, rewrite package payloads, or widen parser/source-shape/schema
behavior.

## Runtime Behavior

The mixed readiness request admits only:

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
- `aps_handoff_record_ref`
- `aps_handoff_state`
- `operator_decision`
- optional `decision_notes`
- optional `expected_package_kinds`

Server-side validation recomputes the P14 mixed-source package-review preview,
requires committed Gate B material authority, loads the P15 reconciliation and
exactly three package rows, verifies P15 construction, verifies the P16
approved package-review submit state, verifies the P17 handoff/export prepare
state and reference envelope, and verifies the P18 APS handoff dispatch state
on the same reconciliation before recording readiness.

On success, the runtime records exactly one readiness state in:

- `L3ReconciliationRecord.summary_json.external_export_download_readiness`
- `L3Session.summary_json.external_export_download_readiness`

The session summary projects that state through the existing
`external_export_download` status surface with schema
`layer3.mixed_source_external_export_download_readiness_state.v1`.

The recorded state emits only public `layer3://mixed-source-package/...` package
refs and a public `layer3://mixed-source-external-export/...` readiness ref. It
keeps `external_export_enabled`, `download_enabled`, `download_url_enabled`,
`signed_reference_enabled`, `provider_public_url_enabled`,
`provider_private_signed_url_enabled`, `connector_dispatch_enabled`,
`delivery_enabled`, and `external_export_download_enabled` false.

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
- missing or mismatched P18 APS handoff dispatch state
- non-dispatched APS handoff state
- stale or mismatched APS handoff record ref
- unsupported handoff target, export mode, APS target, dispatch mode, or
  operator decision
- selected-pass lifecycle fields on a mixed-source readiness request
- request-supplied payload refs, package payloads, download URLs, signed URLs,
  public/provider URLs, connector/destination fields, local outbox fields, or
  dispatch fields
- source expansion, parser, schema, migration, local upload, or local directory
  fields
- excluded-tool fields
- existing conflicting external export/download readiness state

## Non-Goals

- No rendered UI/static behavior change.
- No external export/download delivery.
- No browser download or download URL.
- No signed-reference, public URL, provider URL, or provider dispatch behavior.
- No connector, destination, local outbox, credential, network, or file delivery
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

Branch-local verification passed before PR #2220:

- `python -B -m py_compile .\backend\app\api\layer3.py .\backend\app\services\layer3_workbench.py .\backend\app\services\layer3_handoff_contract.py .\backend\app\services\layer3_workbench_package_state.py .\backend\app\services\layer3_external_export_response.py .\backend\tests\test_layer3_api.py`
- `python -B -m pytest .\backend\tests\test_layer3_api.py -k "mixed_source_external_export_download_readiness or layer3_handoff_openapi_contracts or workbench_error_responses or json_or_error_call_sites_return_workbench_error_envelope" -q`
  (`28 passed, 267 deselected, 3 warnings`)
- `python -B -m pytest .\backend\tests\test_layer3_api.py -q`
  (`295 passed, 4 warnings`)
- `python -B -m pytest .\backend\tests\test_layer3_external_export_response.py -q`
  (`6 passed, 2 warnings`)

Branch-local governance validation also passed before PR #2220:

- `python -B -m json.tool .\next_milestone_plans\authority-index.json`
- `python -B -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`
- `python -B -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`
- `python -B .\tools\l3-authority-index-validate.py`
- `python -B .\tools\l3-target-selection-validate.py --expect frozen`
- `python -B .\tools\l3-progress-check.py`
- `git diff --check`

Detached post-merge proof from current main
`9e4451cb710c0185a64f1788b9e0d848be7dbc8b` passed:

- touched-file `py_compile`
- focused P19/API contract and error-envelope slice
  (`28 passed, 267 deselected, 3 warnings`)
- full `backend/tests/test_layer3_api.py`
  (`295 passed, 4 warnings`)
- affected external export response helper tests
  (`6 passed, 2 warnings`)
- manifest JSON syntax
- authority-index validation
- frozen target-selection validation
- progress check
- `git diff --check`

## Next Posture

After current main is synced by `46-p19-current-main-sync.md`, the next safe
mixed-source downstream step is a separate external export/download delivery
freeze. That later freeze must decide the exact delivery surface and must
continue to keep download URLs, signed references, public/provider URLs,
connector/provider dispatch, schema/model/migration changes, parser/source-shape
expansion, package payload rewrite, excluded-tool behavior, and production
readiness blocked unless explicitly selected and proved.
