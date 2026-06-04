# P17 Mixed-Source Handoff Export Prepare Runtime Closeout

Status: branch-local runtime implementation verified against current
`project6-origin/main` at `83a16914ef57f6eba139e8cd097531cb3660e752`.

## Scope

This pass admits mixed-source handoff/export prepare-only runtime over the
approved P16 mixed-source package-review submit state. Runtime authority is
material-authority only and must derive from existing server-owned state:

- committed Gate B material authority
- server-recomputed P14 mixed-source package review preview
- P12 mixed-source package contract hash
- P15 construction basis and reconciliation record
- persisted P15 `canonical_internal`, `user_facing`, and `review_facing`
  package rows
- P16 approved package-review submit state on the same reconciliation record

The admitted prepare schema is:

- `layer3.mixed_source_handoff_export_prepare.v1`

The admitted handoff envelope schema is:

- `layer3.mixed_source_handoff_export_envelope.v1`

The admitted package family remains:

- `mixed_dataset_document`

The admitted handoff target and export mode are:

- `mixed_source_review_package`
- `reference_envelope_only`

The admitted operator decisions are:

- `authorize_prepare`
- `hold`
- `decline`
- `blocked`

`decision_notes` are required for `hold`, `decline`, and `blocked`.

## Runtime Behavior

The route accepts only the P17 material-authority request shape:

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
- optional `expected_package_kinds`

The runtime recomputes P14 server-side from `session_id`,
`material_preview_id`, and `material_preview_hash`; compares the recomputed
preview hash and contract hash with the request; loads the P15 reconciliation
record and package rows; requires the mixed-source construction source gate;
validates the P15 construction basis hash; verifies output package IDs, kinds,
and payload hashes; verifies the P16 submit record on the same reconciliation
record; and requires the package-family policy registry to admit mixed-source
handoff prepare.

On success, it records exactly one handoff/export prepare state in:

- `L3ReconciliationRecord.summary_json.handoff_export_prepare`
- `L3Session.summary_json.handoff_export_prepare`

The recorded envelope is reference-only. It may expose public
`layer3://mixed-source-package/...` package refs, package hashes, package kinds,
contract hashes, prepare refs, and server-owned authority hashes. It must not
expose local storage paths, provider object keys, provider URLs, connector
destinations, source row contents, document text, dataset rows, or rewritten
package payload bytes.

## Status Surfaces

Session summary and package status now report mixed-source handoff/export
prepare readiness after an approved P16 submit state. After prepare, they
report the recorded `handoff_export_prepared` state, public package refs, the
reference-envelope ref, mixed material authority, package family, and negative
authority flags.

Selected-pass handoff/export prepare remains distinct. A selected-pass request
whose server-owned package family is `mixed_dataset_document` fails closed and
must use the material-authority shape.

## Idempotency

Same `client_request_id` with the same authority basis replays the recorded
prepare result. Same `client_request_id` with changed authority, target, mode,
or decision fails closed. A different `client_request_id` after prepare fails
closed as already recorded.

## Fail-Closed Cases

The runtime fails closed for:

- missing `client_request_id`
- missing or stale `material_preview_id`
- missing or stale `material_preview_hash`
- missing or stale `package_review_preview_hash`
- missing or stale `contract_hash`
- missing or stale `construction_basis_hash`
- missing Gate B material authority
- malformed Gate B decision manifest
- missing or mismatched P15 reconciliation record
- P15 reconciliation source gate or package-family mismatch
- missing, partial, or extra package rows
- explicit empty or unexpected `expected_package_kinds`
- stale or mismatched `output_package_ids`
- stale or mismatched `payload_hashes`
- missing or mismatched P16 submit state
- stale or mismatched `package_review_submit_record_ref`
- non-approved `package_review_state`
- package-family policy handoff admission false
- unsupported `handoff_target`
- unsupported `export_mode`
- unsupported `operator_decision`
- missing `decision_notes` for non-authorization decisions
- selected-pass lifecycle fields on mixed handoff/export prepare request
- request-supplied `payload_refs`
- package payload rewrite fields on request
- APS handoff, external export/download, provider, connector, public URL,
  signed URL, destination, or dispatch fields on request
- source expansion, parser, schema, migration, local upload, or local directory
  fields on request
- excluded-tool fields on request
- existing conflicting prepare state

## Non-Goals

- No APS handoff behavior.
- No external export/download behavior.
- No connector dispatch, provider-public URL, provider-private signed URL,
  public URL, destination, local outbox, or network egress behavior.
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

- touched API/service/test compile passed
- focused mixed-source handoff/export prepare and affected API contract slice
  passed with `4 passed, 293 deselected, 4 warnings`
- focused Layer 3 API mixed-source/package submit/handoff slice passed with
  `31 passed, 260 deselected, 3 warnings`
- full Layer 3 API suite passed with `291 passed, 4 warnings`
- focused package-family/package-contract/workbench-state/submit-response/
  workbench suite passed with `71 passed, 2 warnings`

Final control-spine verification for this branch must include:

- manifest JSON syntax
- Layer 3 authority-index validation
- Layer 3 target-selection frozen validation
- Layer 3 progress check
- `git diff --check`

## Next Posture

After this runtime merges and current main is synced, the next safe tranche must
be a separate freeze before any mixed-source APS handoff, external
export/download, rendered control, connector dispatch, provider URL, parser,
schema, source-shape, package mutation, package payload rewrite, or production
readiness behavior is admitted.
