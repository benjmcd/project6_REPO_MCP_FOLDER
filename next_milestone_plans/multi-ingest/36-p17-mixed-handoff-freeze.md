# P17 Mixed-Source Handoff Export Prepare Freeze

Status: branch-local planning/control freeze only. No mixed-source handoff/export prepare runtime is admitted in this pass.

## Scope

This freeze selects the next implementation boundary after P16: a future mixed-source handoff/export prepare-only state over an approved P16 mixed-source package-review submit decision.

The future runtime pass may proceed only from:

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

The only admitted `package_review_state` value is:

- `package_review_approved`

The only admitted `handoff_target` value for the first runtime pass is:

- `mixed_source_review_package`

The only admitted `export_mode` value for the first runtime pass is:

- `reference_envelope_only`

The only admitted `operator_decision` values are:

- `authorize_prepare`
- `hold`
- `decline`
- `blocked`

`decision_notes` must be required for `hold`, `decline`, and `blocked`. `authorize_prepare` may include notes, but notes must not become package payload rewrite, source rewrite, export target, or dispatch authority.

The future runtime must not accept selected-pass `analysis_plan_id`, `pass_run_id`, `preview_id`, `preview_hash`, `result_review_record_ref`, or `analysis_run_id` fields for mixed-source handoff/export prepare. Those remain selected-pass package lifecycle authority, not mixed material-authority lifecycle authority.

## Canonical Authority

Mixed-source handoff/export prepare authority must be recomputed from server-owned state:

1. Load the `L3Session` by `session_id`.
2. Require the committed Gate B material decision on that session.
3. Require `material_preview_id` and `material_preview_hash` to match the Gate B idempotency record.
4. Require the stored Gate B decision manifest hash to match the manifest in session operator context.
5. Recompute the P14 mixed-source package-review preview basis, including selected `dataset_version` and `aps_content_document` source IDs, source manifest, narrative-table links, `contract_hash`, and `package_review_preview_hash`.
6. Load the P15 reconciliation record by `session_id` and `reconciliation_record_id`.
7. Require the reconciliation source gate and package family to be the mixed-source construction runtime boundary from P15.
8. Require P15 construction authority to match the recomputed P14/P12 basis through `construction_basis_hash`, `contract_hash`, and `package_review_preview_hash`.
9. Require exactly the three P15 package rows for `canonical_internal`, `user_facing`, and `review_facing`.
10. Require supplied `output_package_ids`, `payload_hashes`, and optional `expected_package_kinds` to match the current server-loaded package rows.
11. Require the P16 package-review submit state for `package_review_submit_record_ref` to exist on the same reconciliation record, match the package rows and authority basis, and have `package_review_state` equal to `package_review_approved`.
12. Require the package-family policy registry to admit `mixed_dataset_document` handoff before any prepare state is recorded.

No request-supplied source IDs, package payload bytes, payload refs, generated text, local paths, provider URLs, public URLs, connector refs, destination refs, dispatch targets, download modes, edited findings, or replacement package data may become handoff/export prepare authority.

## Future Runtime Contract

The first implementation pass should add a mixed-source handoff/export prepare response with schema id:

- `layer3.mixed_source_handoff_export_prepare.v1`

The runtime should record exactly one prepare state over the existing P16 submit state and existing P15 reconciliation/package set. The state belongs with package lifecycle state, not with parser output, material preview output, source-family rows, provider state, connector state, or external delivery state.

The prepare state should include:

- `prepare_record_ref`
- `handoff_export_prepare_schema_id`
- `handoff_export_state`
- `operator_decision`
- `decision_notes`
- `material_preview_id`
- `material_preview_hash`
- `contract_hash`
- `package_review_preview_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `package_review_submit_record_ref`
- `output_package_ids`
- `package_kinds`
- `payload_hashes`
- `handoff_target`
- `export_mode`
- `handoff_export_envelope_ref`
- package family `mixed_dataset_document`
- negative authority flags

The handoff/export envelope must be reference-only and public-surface safe:

- It may contain public `layer3://mixed-source-package/...` package refs.
- It may contain package hashes, package kinds, contract ids, and server-owned authority hashes.
- It must not contain local storage paths, raw provider object keys, provider tokens, raw public URLs, connector destinations, arbitrary target paths, source row contents, raw document text, dataset rows, or rewritten package payload bytes.

`authorize_prepare` may create a handoff/export prepare state and a reference envelope. It must not enable APS handoff, external export/download, connector dispatch, provider-public URL behavior, provider-private signed URL behavior, local outbox writes, network egress, package mutation, source expansion, parser behavior, payload rewrite, or production readiness in the same tranche.

## Idempotency

Handoff/export prepare idempotency key must include:

- package family: `mixed_dataset_document`
- `client_request_id`
- `session_id`
- `material_preview_id`
- `material_preview_hash`
- `contract_hash`
- `package_review_preview_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `package_review_submit_record_ref`
- ordered `output_package_ids`
- ordered `payload_hashes`
- expected package kinds
- `handoff_target`
- `export_mode`
- `operator_decision`
- `decision_notes`

Same authority basis and same `client_request_id` should replay the existing prepare result. Same `client_request_id` with changed authority, changed target, changed mode, or changed decision must fail closed. Same approved submit state with a different `client_request_id` after prepare should fail as already prepared unless the implementation explicitly freezes and tests a replay-by-authority rule.

## Fail-Closed Cases

Future implementation must cover:

- missing `client_request_id`
- missing or stale `material_preview_id`
- missing or stale `material_preview_hash`
- missing or stale `package_review_preview_hash`
- missing or stale `contract_hash`
- missing or stale `construction_basis_hash`
- missing Gate B material authority
- malformed Gate B decision manifest
- missing P15 reconciliation record
- P15 reconciliation source gate or package-family mismatch
- missing, partial, or extra package rows
- unexpected package kind
- stale or mismatched `output_package_ids`
- stale or mismatched `payload_hashes`
- missing P16 package-review submit state
- stale or mismatched `package_review_submit_record_ref`
- non-approved `package_review_state`
- package-family policy handoff admission still false
- unsupported `handoff_target`
- unsupported `export_mode`
- unsupported `operator_decision`
- missing `decision_notes` for `hold`, `decline`, or `blocked`
- selected-pass lifecycle fields on mixed handoff/export prepare request
- package payload, payload rewrite, or package reconstruction fields on request
- APS handoff, external export/download, provider, connector, destination, public URL, signed URL, local outbox, or dispatch fields on request
- source expansion, parser, schema, migration, local upload, or local directory fields on request
- excluded-tool field on request
- existing conflicting prepare state

## Non-Goals

- No runtime code change in this freeze.
- No package-family policy change in this freeze.
- No mixed-source handoff/export prepare admission in this freeze.
- No APS handoff, external export/download, connector dispatch, provider-public URL, provider-private signed URL, public URL, local outbox, network egress, or destination behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction.
- No package mutation or replacement package set behavior.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Implementation Entry Gate

Implementation may begin only after this freeze is merged and current-main synced. The implementation pass must keep APS handoff, external export/download, connector dispatch, provider URL behavior, local outbox behavior, parser, schema, source-shape, payload rewrite, package mutation, legacy bridge, excluded-tool behavior, and production readiness blocked unless a later freeze admits exactly one of those surfaces.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
