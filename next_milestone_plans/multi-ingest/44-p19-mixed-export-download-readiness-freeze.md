# P19 Mixed-Source External Export/Download Readiness Freeze

Status: branch-local planning/control freeze only. No mixed-source external
export/download readiness runtime, delivery, download, signed reference, public
URL, connector/provider behavior, schema, parser, source-shape, package payload
rewrite, or production-readiness behavior is admitted in this pass.

## Selection

This freeze selects mixed-source external export/download readiness as the next
exact downstream surface after P18. It is the first external export/download
surface for mixed sources, and it records a reference-only readiness state only.
It does not deliver, download, generate, or expose any external artifact, URL,
or signed reference.

The selection is based on current code and control authority:

- P18 records exactly one reference-only mixed-source APS handoff dispatch state
  in `L3ReconciliationRecord.summary_json.aps_handoff_dispatch` and
  `L3Session.summary_json.aps_handoff_dispatch`.
- That recorded dispatch state keeps `external_export_enabled`,
  `download_enabled`, `connector_dispatch_enabled`,
  `provider_public_url_enabled`, and `external_export_download_enabled` false.
- Current package-family policy still lists `external_export_download` as a
  blocked downstream mixed-source surface after APS handoff dispatch.
- External export/download readiness already requires a recorded APS handoff
  dispatch state as its precondition, and mixed sources now satisfy that
  precondition on current main through the P18 dispatch runtime.

Because the recorded-dispatch precondition is now satisfied for mixed sources,
external export/download readiness is the next selectable surface. Actual
external export/download delivery, download, and signed/public reference output
remain a separate, later surface. Therefore external export/download delivery
must remain blocked until a later runtime pass admits and proves it; this freeze
admits readiness selection only and admits no delivery.

## Scope

The future runtime pass may record exactly one server-side mixed-source external
export/download readiness state over an already recorded P18 mixed-source APS
handoff dispatch state.

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
- `aps_handoff_record_ref`
- `aps_handoff_state`
- `operator_decision`
- optional `decision_notes`
- optional `expected_package_kinds`

The only admitted `package_review_state` value is:

- `package_review_approved`

The only admitted `handoff_export_state` value is:

- `handoff_export_prepared`

The only admitted `aps_handoff_state` value is:

- `aps_handoff_dispatched`

The only admitted mixed-source `handoff_target` value is:

- `mixed_source_review_package`

The only admitted mixed-source `export_mode` value is:

- `reference_envelope_only`

The only admitted `aps_handoff_target` value is:

- `mixed_source_aps_evidence_bundle`

The only admitted `dispatch_mode` value is:

- `server_side_mixed_source_aps_handoff`

The only admitted external export/download readiness response schema id for the
first runtime pass is:

- `layer3.mixed_source_external_export_download_readiness.v1`

The only admitted external export/download readiness state value for the first
runtime pass is:

- `mixed_source_external_export_download_ready`

The only admitted `operator_decision` value for the first runtime pass is:

- `record_mixed_source_external_export_download_readiness`

## Canonical Authority

Mixed-source external export/download readiness authority must be recomputed from
server-owned state and must not trust any request-supplied lifecycle, package,
delivery, or reference value:

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
13. Require the P18 mixed-source APS handoff dispatch state for
    `aps_handoff_record_ref` to exist in
    `L3ReconciliationRecord.summary_json.aps_handoff_dispatch` and
    `L3Session.summary_json.aps_handoff_dispatch`, match the package rows and
    authority basis, and have `aps_handoff_state` equal to
    `aps_handoff_dispatched`.
14. Require the P18 reference-only APS bundle identity to be present and to
    expose only the public `layer3://mixed-source-aps-handoff/...` reference.
15. Require the package-family policy registry or the new runtime gate to admit
    mixed-source external export/download readiness before any readiness state is
    recorded.

No request-supplied source IDs, selected-pass IDs, package payload bytes,
payload refs, generated text, local paths, provider URLs, public URLs, signed
URLs, connector refs, destination refs, dispatch destinations, download modes,
download URLs, edited findings, replacement package data, or browser-authored
authority may become external export/download readiness authority.

## Future Runtime Contract

The first implementation pass should add a mixed-source external export/download
readiness response with schema id:

- `layer3.mixed_source_external_export_download_readiness.v1`

The runtime should record exactly one external export/download readiness state
over the existing P18 dispatch state and existing P15/P16/P17 package lifecycle
state. The state belongs with package lifecycle state on the existing
JSON-bearing session/reconciliation records unless a future freeze explicitly
admits a schema/model/migration change.

The readiness state should be recorded in:

- `L3ReconciliationRecord.summary_json.external_export_download_readiness`
- `L3Session.summary_json.external_export_download_readiness`

The readiness state should include:

- `external_export_download_readiness_record_ref`
- `external_export_download_readiness_schema_id`
- `external_export_download_readiness_state`
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
- `aps_handoff_record_ref`
- `output_package_ids`
- `package_kinds`
- `payload_hashes`
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- package family `mixed_dataset_document`
- negative authority flags

The readiness response may include a reference-only mixed-source external
export/download readiness identity (for example a public
`layer3://mixed-source-external-export/...` reference) only if it is derived
entirely from server-owned package, handoff/export prepare, and APS handoff
dispatch authority. It must not include local storage paths, raw dataset rows,
raw document text, provider object keys, provider tokens, public URLs, signed
URLs, download URLs, connector destinations, arbitrary target paths, rewritten
package payload bytes, or any external download authority.

The recorded readiness state must keep `external_export_enabled`,
`download_enabled`, `connector_dispatch_enabled`, `provider_public_url_enabled`,
`provider_private_signed_url_enabled`, `signed_reference_enabled`,
`delivery_enabled`, and `external_export_download_enabled` false. Readiness means
the server has recorded that the mixed-source package lifecycle is ready for a
later, separately frozen external export/download delivery surface; it does not
mean any delivery, download, or external reference has been produced.

The future runtime may set mixed-source external export/download readiness state
only. It must not deliver an export, deliver a download, generate or use signed
references, generate or use public URLs, generate download URLs, dispatch
connectors, invoke providers, write local outbox records, mutate packages,
expand source shapes, run parsers, or claim production readiness in the same
tranche.

## Idempotency

Mixed-source external export/download readiness idempotency key must include:

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
- `aps_handoff_record_ref`
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
readiness result. Same `client_request_id` with changed authority, changed
target, changed mode, or changed decision must fail closed. Same dispatched
state with a different `client_request_id` after readiness is recorded should
fail as already ready unless the implementation explicitly freezes and tests a
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
- missing P18 APS handoff dispatch state
- stale or mismatched `aps_handoff_record_ref`
- non-dispatched `aps_handoff_state`
- stale or mismatched APS handoff reference identity
- unsupported mixed-source `handoff_target`
- unsupported mixed-source `export_mode`
- unsupported `aps_handoff_target`
- unsupported `dispatch_mode`
- unsupported `operator_decision`
- selected-pass lifecycle fields on a mixed external export/download readiness
  request
- package payload, payload ref override, payload rewrite, or package
  reconstruction fields on request
- delivery, download, download URL, download mode, signed URL, signed reference,
  public URL, provider, connector, destination, or local outbox fields on
  request
- source expansion, parser, schema, migration, local upload, or local directory
  fields on request
- excluded-tool field on request
- existing conflicting external export/download readiness state

## Non-Goals

- No runtime code change in this freeze.
- No package-family policy runtime change in this freeze.
- No mixed-source external export/download readiness admission in this freeze.
- No external export/download delivery, download, download URL, signed
  reference, signed URL, or public URL behavior.
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
synced. The implementation pass must keep external export/download delivery,
download, signed-reference, public-URL, connector, and provider behavior
blocked. After the mixed-source external export/download readiness runtime lands
and is synced to current main, a later freeze may select mixed-source external
export/download delivery as the next downstream surface.

If implementation discovers that mixed-source external export/download readiness
requires a schema/model/migration, parser/source-shape expansion, package
payload rewrite, connector/provider dispatch, external delivery/download
behavior, signed/public reference output, or broader operator workflow change,
stop and create a new freeze instead of widening this one.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
