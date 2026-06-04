# P17A Mixed-Source Rendered Handoff Prepare Runtime Closeout

Status: branch-local runtime implementation verified on current
`project6-origin/main` after SEC-only PR #2208.

## Scope

This pass implements only the rendered `/review/layer3`
material-authority handoff/export prepare path selected by the P17A freeze.
It does not change the P17 backend API contract, route, DTO, model, migration,
parser, source shape, package construction, package-review submit,
handoff/export prepare persistence, APS handoff, external export/download,
connector dispatch, provider URL behavior, local outbox behavior, package
payload rewrite, excluded-tool behavior, or production-readiness posture.

The rendered control now detects mixed-source handoff/export prepare authority
from server-owned session summary/package-review submit/package construction
state. It requires the mixed package family, exact package kinds, complete
package IDs and payload hashes, approved package-review state, material preview
authority, package-review preview hash, contract hash, construction basis hash,
reconciliation record, submit record ref, and P17 target/mode:

- `mixed_source_review_package`
- `reference_envelope_only`

The selected-pass handoff/export prepare path remains separate and still uses
`internal_export_envelope` plus `prepare_only`. Source-directory qualitative
handoff/export prepare remains separate and continues to use its dedicated
route.

## Runtime Behavior

The rendered mixed-source payload includes only the P17 material-authority
fields:

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
- `handoff_target`
- `export_mode`
- `operator_decision`
- optional `decision_notes`
- `expected_package_kinds`

It does not include selected-pass fields such as `analysis_plan_id`,
`pass_run_id`, `preview_id`, `preview_hash`, or `result_review_record_ref`. It
does not send request-supplied `payload_refs`, package payload bytes, local
paths, provider URL fields, connector fields, destination fields, export
download fields, APS handoff fields, schema/migration fields, source-expansion
fields, or browser durable-authority fields.

The rendered status panel now identifies the mixed-source source authority as
`State.sessionSummary.handoff_export_prepare material authority` and uses
`rendered_mixed_source_handoff_export_prepare_control` when the required
material-authority packet is complete. Before that packet is complete, the
panel remains fail-closed under the existing unavailable/blocked server
summary state.

## Fail-Closed Cases

The rendered control stays disabled for:

- missing `session_id`
- missing material preview authority
- missing `package_review_preview_hash`
- missing `contract_hash`
- missing `construction_basis_hash`
- missing `reconciliation_record_id`
- missing `package_review_submit_record_ref`
- non-approved package-review state
- missing, partial, or extra package IDs
- missing, partial, or extra payload hashes
- missing or unexpected package kinds
- selected-pass-only `result_review_record_ref` authority
- selected-pass target/mode defaults
- already recorded handoff/export prepare state
- pending lifecycle work
- missing notes when the selected decision requires notes

The backend P17 route still performs server-side recomputation and rejection
for stale, mismatched, missing, cross-shape, and disallowed fields.

## Non-Goals

- No backend API route change.
- No backend DTO, schema, model, or migration change.
- No handoff/export prepare persistence change.
- No package construction or package-review submit behavior change.
- No APS handoff behavior.
- No external export/download behavior.
- No connector dispatch.
- No provider-public URL, provider-private signed URL, public URL, local
  outbox, destination, or network egress behavior.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction or mutation.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Verification

Branch-local verification after rebasing to current `project6-origin/main`
`4bdbd0ebc18d2a0de0e5ddb1a77ef5f246a94d76` passed:

- `node --check ./backend/app/review_ui/static/layer3.js`
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`
  (`22 passed, 3 warnings`)
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "mixed_source_handoff_export_prepare or package_family_handoff_export_prepare"`
  (`1 passed, 290 deselected, 3 warnings`)

Final branch verification must also include:

- JSON syntax for changed manifests
- Layer 3 authority-index validation
- Layer 3 target-selection frozen validation
- Layer 3 progress check
- `git diff --check`

## Next Posture

After this rendered runtime lands and current main is synced, the next safe
mixed-source tranche must be a separate freeze before admitting any APS
handoff, external export/download readiness, connector/provider behavior,
schema/model/migration change, parser/source-shape expansion, package payload
rewrite, excluded-tool behavior, or production-readiness claim.
