# P15 Mixed-Source Package Construction Commit Freeze

Status: branch-local planning/control freeze only. No mixed-source package construction runtime is admitted in this pass.

## Scope

This freeze selects the next implementation boundary after P14: a future mixed-source package construction commit derived only from the P14 read-only preview hash and committed Gate B material authority.

The future runtime pass may proceed only from:

- `session_id`
- `client_request_id`
- `material_preview_id`
- `material_preview_hash`
- `package_review_preview_hash`
- `contract_hash`
- optional `expected_package_kinds`

The future runtime must not accept selected-pass `analysis_plan_id`, `pass_run_id`, `preview_id`, `preview_hash`, `result_review_record_ref`, or `analysis_run_id` fields for mixed-source construction. Those remain selected-pass package lifecycle authority, not mixed material-authority lifecycle authority.

## Canonical Authority

Construction authority must be recomputed from server-owned state:

1. Load the `L3Session` by `session_id`.
2. Require the committed Gate B material decision on that session.
3. Require `material_preview_id` and `material_preview_hash` to match the Gate B idempotency record.
4. Require the stored Gate B decision manifest hash to match the manifest in session operator context.
5. Recompute the P14 mixed preview basis, including selected `dataset_version` and `aps_content_document` source IDs, source manifest, narrative-table links, `contract_hash`, and `package_review_preview_hash`.
6. Require supplied `contract_hash` and `package_review_preview_hash` to match recomputed values.

No request-supplied source IDs, package payload bytes, payload refs, payload hashes, local paths, provider URLs, connector refs, or generated text may become construction authority.

## Future Runtime Contract

The first implementation pass should add a mixed-source construction commit response with schema id:

- `layer3.mixed_source_package_construction_commit.v1`

The commit should materialize exactly one reconciliation record plus exactly three package rows:

- `canonical_internal`
- `user_facing`
- `review_facing`

Each package payload must be a manifest over existing authority:

- P14 `source_manifest`
- P14 `narrative_table_links`
- P12 `layer3.mixed_source_package_contract.v1`
- selected `dataset_version` IDs
- selected `aps_content_document` IDs
- negative authority flags

Payloads must not inline raw documents, rewrite dataset rows, create new source rows, change parser output, mutate `DatasetVersion`, mutate `ApsContentDocument`, or expose local absolute paths.

## Idempotency

Construction idempotency key must include:

- package family: `mixed_dataset_document`
- `client_request_id`
- `session_id`
- `material_preview_id`
- `material_preview_hash`
- `contract_hash`
- `package_review_preview_hash`
- sorted selected `dataset_version` IDs
- sorted selected `aps_content_document` IDs
- sorted narrative-table link IDs
- expected package kinds

Same authority basis and same `client_request_id` should replay the existing construction result. Same `client_request_id` with changed authority must fail closed. Same authority with a different `client_request_id` may either replay by authority basis or fail as already constructed, but the implementation must choose one behavior explicitly and test it.

## Fail-Closed Cases

Future implementation must cover:

- missing `client_request_id`
- missing or stale `material_preview_id`
- missing or stale `material_preview_hash`
- missing or stale `package_review_preview_hash`
- missing or stale `contract_hash`
- missing Gate B material authority
- malformed Gate B decision manifest
- missing `dataset_version` or `aps_content_document` material class
- unexpected source class
- duplicate selected source identity
- selected-pass lifecycle fields on mixed construction request
- package payload fields on request
- handoff/export/APS handoff/external export/provider/connector/public URL fields on request
- Onlook field on request
- existing conflicting package/reconciliation state

## Non-Goals

- No runtime code change in this freeze.
- No package-family policy change in this freeze.
- No mixed-source construction admission in this freeze.
- No mixed-source package-review submit.
- No handoff/export, APS handoff, external export/download, connector dispatch, provider-public URL, or public URL behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No legacy CSV bridge deprecation.
- No Onlook behavior.

## Implementation Entry Gate

Implementation may begin only after this freeze is merged and current-main synced. The implementation pass must keep submit, handoff, export, parser, schema, source-shape, payload rewrite, legacy bridge, and Onlook behavior blocked unless a later freeze admits exactly one of those surfaces.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
