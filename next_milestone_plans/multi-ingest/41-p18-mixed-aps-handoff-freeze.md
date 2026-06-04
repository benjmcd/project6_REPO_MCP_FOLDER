# P18 Mixed-Source APS Handoff Dispatch Freeze

Status: branch-local planning/control freeze only. No mixed-source APS handoff
runtime, external export/download readiness, connector/provider behavior,
schema, parser, source-shape, package payload rewrite, or production-readiness
behavior is admitted in this pass.

## Selection

This freeze selects mixed-source APS handoff dispatch as the next exact
downstream surface after P17/P17A. It is the prerequisite surface before
mixed-source external export/download readiness can be pursued.

The selection is based on current code and control authority:

- P17 records only a reference-only mixed-source handoff/export prepare state.
- P17A renders only the material-authority control for that prepare state.
- Current package-family policy still lists `aps_handoff` and
  `external_export_download` as blocked downstream mixed-source surfaces.
- Current external export/download readiness requires a recorded APS handoff
  dispatch before readiness can be prepared.
- Current APS handoff dispatch explicitly rejects mixed-source reconciliation
  state with `mixed_source_aps_handoff_dispatch_not_admitted`.

Therefore external export/download readiness must remain blocked until a later
runtime pass admits and proves mixed-source APS handoff dispatch. Freezing
external export/download readiness first would skip the recorded-dispatch
precondition already enforced by the existing lifecycle.

## Scope

The future runtime pass may admit one server-side mixed-source APS handoff
dispatch over an already prepared P17 mixed-source handoff/export state.

The future runtime may proceed only from material-authority lifecycle state
already owned by the server:

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

The only admitted `package_review_state` value is:

- `package_review_approved`

The only admitted `handoff_export_state` value is:

- `handoff_export_prepared`

The only admitted mixed-source `handoff_target` value is:

- `mixed_source_review_package`

The only admitted mixed-source `export_mode` value is:

- `reference_envelope_only`

The only admitted `aps_handoff_target` value for the first runtime pass is:

- `mixed_source_aps_evidence_bundle`

The only admitted `dispatch_mode` value for the first runtime pass is:

- `server_side_mixed_source_aps_handoff`

The only admitted `operator_decision` value for the first runtime pass is:

- `dispatch_mixed_source_aps_handoff`

## Canonical Authority

Mixed-source APS handoff dispatch authority must be recomputed from server-owned
state:

1. Load the `L3Session` by `session_id`.
2. Require the committed Gate B material decision on that session.
3. Require `material_preview_id` and `material_preview_hash` to match the Gate B
   idempotency record.
4. Recompute the P14 mixed-source package-review preview basis, including
   selected `dataset_version` and `aps_content_document` source IDs, source
   manifest, narrative-table links, `contract_hash`, and
   `package_review_preview_hash`.
5. Load the P15 reconciliation record by `session_id` and
   `reconciliation_record_id`.
6. Require the reconciliation source gate and package family to be the
   mixed-source construction runtime boundary from P15.
7. Require P15 construction authority to match the recomputed P14/P12 basis
   through `construction_basis_hash`, `contract_hash`, and
   `package_review_preview_hash`.
8. Require exactly the three P15 package rows for `canonical_internal`,
   `user_facing`, and `review_facing`.
9. Require supplied `output_package_ids`, `payload_hashes`, and optional
   `expected_package_kinds` to match the current server-loaded package rows.
10. Require the P16 package-review submit state for
   `package_review_submit_record_ref` to exist on the same reconciliation
   record, match the package rows and authority basis, and have
   `package_review_state` equal to `package_review_approved`.
11. Require the P17 mixed-source handoff/export prepare state to exist on the
   same reconciliation record, match the package rows and authority basis, and
   have `handoff_export_state` equal to `handoff_export_prepared`.
12. Require the P17 reference envelope to be present and to expose only public
   `layer3://mixed-source-package/...` package refs plus hashes and authority
   metadata.
13. Require the package-family policy registry or the new runtime gate to admit
   mixed-source APS handoff dispatch before any dispatch state is recorded.

No request-supplied source IDs, selected-pass IDs, package payload bytes,
payload refs, generated text, local paths, provider URLs, public URLs,
connector refs, destination refs, dispatch destinations, download modes, edited
findings, replacement package data, or browser-authored authority may become APS
handoff dispatch authority.

## Future Runtime Contract

The first implementation pass should add a mixed-source APS handoff dispatch
response with schema id:

- `layer3.mixed_source_aps_handoff_dispatch.v1`

The runtime should record exactly one APS handoff dispatch state over the
existing P17 prepare state and existing P15/P16 package lifecycle state. The
state belongs with package lifecycle state on the existing JSON-bearing
session/reconciliation records unless a future freeze explicitly admits a
schema/model/migration change.

The dispatch state should include:

- `aps_handoff_record_ref`
- `aps_handoff_dispatch_schema_id`
- `aps_handoff_state`
- `operator_decision`
- `decision_notes`
- `material_preview_id`
- `material_preview_hash`
- `contract_hash`
- `package_review_preview_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `package_review_submit_record_ref`
- `prepare_record_ref`
- `handoff_export_envelope_ref`
- `output_package_ids`
- `package_kinds`
- `payload_hashes`
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- package family `mixed_dataset_document`
- negative authority flags

The dispatch response may include a reference-only mixed-source APS evidence
bundle identity if the bundle is derived entirely from server-owned package and
handoff/export prepare authority. It must not include local storage paths, raw
dataset rows, raw document text, provider object keys, provider tokens, public
URLs, connector destinations, arbitrary target paths, rewritten package payload
bytes, or external download authority.

The future runtime may set mixed-source APS handoff dispatch state only. It must
not prepare external export/download readiness, deliver a download, generate or
use signed references, dispatch connectors, invoke providers, write local
outbox records, mutate packages, expand source shapes, run parsers, or claim
production readiness in the same tranche.

## Idempotency

Mixed-source APS handoff dispatch idempotency key must include:

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
- `prepare_record_ref`
- `handoff_export_envelope_ref`
- ordered `output_package_ids`
- ordered `payload_hashes`
- expected package kinds
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- `operator_decision`
- `decision_notes`

Same authority basis and same `client_request_id` should replay the existing
dispatch result. Same `client_request_id` with changed authority, changed
target, changed mode, or changed decision must fail closed. Same prepared state
with a different `client_request_id` after dispatch should fail as already
dispatched unless the implementation explicitly freezes and tests a
replay-by-authority rule.

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
- missing P17 handoff/export prepare state
- stale or mismatched `prepare_record_ref`
- stale or mismatched `handoff_export_envelope_ref`
- non-prepared `handoff_export_state`
- unsupported mixed-source `handoff_target`
- unsupported mixed-source `export_mode`
- unsupported `aps_handoff_target`
- unsupported `dispatch_mode`
- unsupported `operator_decision`
- selected-pass lifecycle fields on mixed APS handoff dispatch request
- package payload, payload ref override, payload rewrite, or package
  reconstruction fields on request
- external export/download, provider, connector, destination, public URL,
  signed URL, local outbox, or download fields on request
- source expansion, parser, schema, migration, local upload, or local directory
  fields on request
- excluded-tool field on request
- existing conflicting APS handoff dispatch state

## Non-Goals

- No runtime code change in this freeze.
- No package-family policy runtime change in this freeze.
- No mixed-source APS handoff dispatch admission in this freeze.
- No external export/download readiness, delivery, download, or signed-reference
  behavior.
- No connector dispatch, provider-public URL, provider-private signed URL,
  public URL, local outbox, network egress, or destination behavior.
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

Implementation may begin only after this freeze is merged and current-main
synced. The implementation pass must keep external export/download readiness
blocked. After the mixed-source APS handoff dispatch runtime lands and is synced
to current main, a later freeze may select mixed-source external export/download
readiness as the next downstream surface.

If implementation discovers that mixed-source APS handoff dispatch requires a
schema/model/migration, parser/source-shape expansion, package payload rewrite,
connector/provider dispatch, external export/download behavior, or broader
operator workflow change, stop and create a new freeze instead of widening this
one.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
