# P16 Mixed-Source Package Review Submit Runtime Closeout

Status: branch-local runtime implementation verified.

## Scope

This pass admits the first mixed-source package-review submit runtime over the
P15 manifest packages. Submit authority is material-authority only and must
derive from existing server-owned state:

- committed Gate B material authority
- server-recomputed P14 mixed-source package review preview
- P12 mixed-source package contract hash
- P15 construction basis and reconciliation record
- persisted P15 `canonical_internal`, `user_facing`, and `review_facing`
  package rows

The admitted submit schema is:

- `layer3.mixed_source_package_review_submit.v1`

The admitted package family remains:

- `mixed_dataset_document`

The admitted operator decisions are:

- `approved`
- `changes_requested`
- `rejected`
- `blocked`

`decision_notes` are required for `changes_requested`, `rejected`, and
`blocked`.

## Runtime Behavior

The submit route accepts only the P16 material-authority request shape:

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
- `operator_decision`
- optional `decision_notes`
- optional `expected_package_kinds`

The runtime recomputes P14 server-side from `session_id`,
`material_preview_id`, and `material_preview_hash`; compares the recomputed
preview hash and contract hash with the request; loads the P15 reconciliation
record; requires the P15 mixed-source construction source gate; validates the
construction basis hash; reloads package rows from the database; and compares
the supplied output package IDs, package kinds, and payload hashes with the
server-loaded package set.

On success, it records exactly one package-review submit decision state in:

- `L3ReconciliationRecord.summary_json.package_review_submit`
- `L3Session.summary_json.package_review_submit`

It does not create package rows, rewrite package payloads, reconstruct packages,
or seed/generate runtime artifacts from request data.

## Review-Debt Closure

This runtime also closes the P15/P16 code-family review concerns that remained
open after the P15 construction runtime:

- explicit `expected_package_kinds: []` fails closed instead of falling through
  to default package kinds
- material-authority routing is based on field presence, not truthiness, so
  empty strings cannot become selected-pass authority
- mixed-source package status/submit response payload refs are public
  `layer3://mixed-source-package/...` refs, not local storage paths
- mixed submit idempotency records `client_request_id`; same request replay
  returns the recorded submit result, while a different request after submit
  fails closed

## Fail-Closed Cases

The runtime fails closed for:

- missing `client_request_id`
- missing or stale `material_preview_id`
- missing or stale `material_preview_hash`
- missing or stale `package_review_preview_hash`
- missing or stale `contract_hash`
- missing or stale `construction_basis_hash`
- missing Gate B material authority
- missing or mismatched P15 reconciliation record
- P15 reconciliation source gate or package-family mismatch
- missing, partial, or extra package rows
- explicit empty or unexpected `expected_package_kinds`
- stale or mismatched `output_package_ids`
- stale or mismatched `payload_hashes`
- unsupported `operator_decision`
- missing `decision_notes` for non-approval decisions
- selected-pass lifecycle fields on mixed submit request
- request-supplied `payload_refs`
- package payload rewrite fields on request
- handoff/export/APS handoff/external export/provider/connector/public URL
  fields on request
- excluded-tool fields on request
- existing conflicting submit state

## Non-Goals

- No handoff/export, APS handoff, external export/download, connector dispatch,
  provider-public URL, or public URL behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Verification

Verification for this branch passed:

- touched API/service/test compile passed
- focused package-family/contract/workbench-state/submit-response/workbench
  suite passed with `71 passed, 2 warnings`
- focused Layer 3 API mixed-source/package submit/construction/preview slice
  passed with `33 passed, 254 deselected, 3 warnings`
- authority/progress/proof manifest JSON syntax passed
- Layer 3 authority-index validation passed
- Layer 3 target-selection frozen validation passed
- Layer 3 progress check passed

## Next Posture

After this runtime merges and current main is synced, the next safe tranche is a
separate P17 mixed-source handoff/export freeze. That future tranche must decide
handoff/export authority without widening parser behavior, schema, source shape,
payload rewrite, legacy bridge deprecation, excluded-tool behavior, or
production readiness.
