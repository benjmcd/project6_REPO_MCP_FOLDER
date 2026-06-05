# P20 Mixed-Source External Export/Download Delivery Freeze

Status: branch-local planning/control freeze only. No mixed-source external
export/download delivery runtime, browser download, download URL, signed
reference, public/provider URL, connector/provider/destination behavior,
schema/model/migration change, parser behavior, source-shape expansion, package
payload rewrite, excluded-tool behavior, or production-readiness behavior is
admitted in this pass.

## Selection

This freeze selects mixed-source external export/download delivery as the next
exact downstream surface after P19. The selected delivery class is same-origin
artifact-stream delivery over the recorded P19 mixed-source external
export/download readiness state.

This is not a provider/public URL, signed-reference, connector, destination,
local outbox, or production-readiness surface. It is also not a package payload
rewrite surface. The future runtime may return only a server-revalidated
same-origin artifact stream for one existing mixed-source package artifact whose
identity, package kind, package payload hash, readiness state, and upstream
material/package/handoff authority all match server-owned state.

The selection is based on current code and control authority:

- P19 records exactly one reference-only mixed-source external export/download
  readiness state in
  `L3ReconciliationRecord.summary_json.external_export_download_readiness` and
  `L3Session.summary_json.external_export_download_readiness`.
- That recorded readiness state keeps `delivery_enabled`,
  `download_enabled`, `download_url_enabled`, `signed_reference_enabled`,
  `provider_public_url_enabled`, `provider_private_signed_url_enabled`,
  `connector_dispatch_enabled`, and `external_export_download_enabled` false.
- Existing non-mixed Layer 3 delivery precedent uses same-origin
  artifact-stream delivery and the route family
  `POST /api/v1/layer3/handoff/export/download/deliver`.
- Current mixed-source authority now reaches P19 readiness but does not yet
  admit delivery from that readiness state.

Because the P19 readiness precondition is now satisfied for mixed sources,
same-origin artifact-stream delivery is the next selectable surface. Download
URLs, signed references, public/provider URLs, connector/provider/destination
dispatch, local outbox writes, and production-readiness claims remain separate
later surfaces.

## Scope

The future runtime pass may admit exactly one mixed-source same-origin
artifact-stream delivery action over an already recorded P19 readiness state.
It may reuse the existing
`POST /api/v1/layer3/handoff/export/download/deliver` route only if the
implementation proves exact compatibility with mixed-source readiness and
emits a mixed-source-specific delivery authority signal rather than silently
falling through to a generic or selected-pass delivery schema.

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
- `output_package_id`
- `package_kind`
- `package_payload_hash`
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
- `external_export_download_readiness_record_ref`
- `external_export_download_readiness_ref`
- `external_export_download_readiness_state`
- `delivery_mode`
- `operator_decision`
- optional `decision_notes`
- optional `expected_package_kinds`

The only admitted `package_review_state` value is:

- `package_review_approved`

The only admitted `handoff_export_state` value is:

- `handoff_export_prepared`

The only admitted `aps_handoff_state` value is:

- `aps_handoff_dispatched`

The only admitted P19 readiness state value is:

- `mixed_source_external_export_download_ready`

The only admitted mixed-source `handoff_target` value is:

- `mixed_source_review_package`

The only admitted mixed-source `export_mode` value is:

- `reference_envelope_only`

The only admitted `aps_handoff_target` value is:

- `mixed_source_aps_evidence_bundle`

The only admitted `dispatch_mode` value is:

- `server_side_mixed_source_aps_handoff`

The only admitted `delivery_mode` value is:

- `same_origin_artifact_stream`

The only admitted `operator_decision` value for the first runtime pass is:

- `deliver_mixed_source_external_export_download`

The future response schema id should be mixed-source specific:

- `layer3.mixed_source_external_export_download_delivery.v1`

## Canonical Authority

Mixed-source external export/download delivery authority must be recomputed from
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
9. Require `output_package_id`, `package_kind`, `package_payload_hash`, and
   optional `expected_package_kinds` to match one current server-loaded package
   row and the full package-row set.
10. Require the P16 package-review submit state for
    `package_review_submit_record_ref` to exist on the same reconciliation
    record, match the package rows and authority basis, and have
    `package_review_state` equal to `package_review_approved`.
11. Require the P17 mixed-source handoff/export prepare state to exist on the
    same reconciliation record, match the package rows and authority basis, and
    have `handoff_export_state` equal to `handoff_export_prepared`.
12. Require the P18 mixed-source APS handoff dispatch state for
    `aps_handoff_record_ref` to exist in
    `L3ReconciliationRecord.summary_json.aps_handoff_dispatch` and
    `L3Session.summary_json.aps_handoff_dispatch`, match the package rows and
    authority basis, and have `aps_handoff_state` equal to
    `aps_handoff_dispatched`.
13. Require the P19 mixed-source external export/download readiness state for
    `external_export_download_readiness_record_ref` to exist in
    `L3ReconciliationRecord.summary_json.external_export_download_readiness`
    and `L3Session.summary_json.external_export_download_readiness`, match the
    package rows and authority basis, and have
    `external_export_download_readiness_state` equal to
    `mixed_source_external_export_download_ready`.
14. Require the package-family policy registry or the new runtime gate to admit
    mixed-source same-origin delivery before any artifact stream is returned.
15. Require the artifact stream source to be an existing server-owned package
    artifact or package payload already proven by P15/P16/P17/P18/P19 authority.

No request-supplied source IDs, selected-pass IDs, package payload bytes,
payload refs, generated text, local paths, provider URLs, public URLs, signed
URLs, connector refs, destination refs, dispatch destinations, download URLs,
download tokens, edited findings, replacement package data, or browser-authored
authority may become mixed-source delivery authority.

## Future Runtime Contract

The first implementation pass should add or adapt a mixed-source external
export/download delivery response with schema id:

- `layer3.mixed_source_external_export_download_delivery.v1`

On success, the runtime may return a same-origin artifact stream for one
server-owned package artifact. Response headers or authority metadata should
identify the mixed-source schema id, delivered state, package family, package
kind, package payload hash, readiness record ref, and source package authority
without exposing local storage paths or raw authority payloads.

The future runtime may record a delivery attempt/status in existing
session/reconciliation JSON only if it remains reference-only and does not
require a schema/model/migration. Any durable delivery receipt table,
outbox/package-copy table, signed-reference table, public/provider URL table,
or connector/destination table requires a separate freeze before implementation.

The future runtime must keep download URL generation, signed-reference
generation/use, public/provider URL generation/use, connector/provider
dispatch, destination selection/write, local outbox writes, package mutation,
package reconstruction, source-shape expansion, parser behavior, excluded-tool
behavior, and production-readiness activation blocked.

## Idempotency

Mixed-source external export/download delivery idempotency key must include:

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
- `external_export_download_readiness_record_ref`
- `external_export_download_readiness_ref`
- `output_package_id`
- `package_kind`
- `package_payload_hash`
- expected package kinds
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- `external_export_download_readiness_state`
- `delivery_mode`
- `operator_decision`
- `decision_notes`

The same `client_request_id` with the same authority may return the same
delivery response. The same `client_request_id` with changed authority must
fail closed. A different `client_request_id` after an already recorded
conflicting delivery state must fail closed unless the future runtime explicitly
proves repeat-delivery semantics inside this same mixed-source same-origin
surface.

## Fail-Closed Cases

The future runtime must fail closed for:

- missing `client_request_id`
- missing or stale material preview authority
- missing or stale package-review preview hash
- missing or stale contract hash
- missing or stale construction basis hash
- missing or mismatched P15 reconciliation/package state
- partial, extra, or unexpected package rows
- stale or mismatched `output_package_id`
- stale or mismatched `package_kind`
- stale or mismatched `package_payload_hash`
- explicit empty or unexpected `expected_package_kinds`
- missing or mismatched P16 package-review submit state
- non-approved package-review state
- missing or mismatched P17 handoff/export prepare state
- non-prepared handoff/export state
- missing or mismatched P18 APS handoff dispatch state
- non-dispatched APS handoff state
- missing or mismatched P19 readiness state
- non-ready external export/download readiness state
- stale or mismatched readiness record/ref
- unsupported handoff target, export mode, APS target, dispatch mode, delivery
  mode, or operator decision
- selected-pass lifecycle fields on a mixed-source delivery request
- source-directory lifecycle fields on a mixed-source delivery request
- SEC XBRL lifecycle fields on a mixed-source delivery request
- request-supplied payload refs, package payloads, download URLs, signed URLs,
  public/provider URLs, connector/destination fields, local outbox fields, or
  dispatch fields
- missing server-owned package artifact or package payload required to stream
- package artifact hash/size mismatch
- source expansion, parser, schema, migration, local upload, or local directory
  fields
- excluded-tool fields
- existing conflicting external export/download delivery state

## Non-Goals

- No backend route or runtime behavior change in this freeze.
- No rendered UI/static behavior change.
- No browser download control.
- No download URL generation or exposure.
- No signed-reference generation, use, status, or revocation.
- No public URL, provider URL, or provider dispatch behavior.
- No connector, destination, local outbox, credential, network, or external file
  delivery behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction, mutation, copy, amendment, replacement, or
  supersession.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No SEC XBRL surface.
- No production-readiness activation.

## Implementation Entry Gate

Implementation may begin only after this freeze merges and current main is
synced. The implementation pass must stay limited to mixed-source same-origin
external export/download delivery over recorded P19 readiness unless a fresh
freeze selects a different downstream surface.

Required future proofs include:

- mixed-source P19 readiness can deliver same-origin artifact stream
- delivery revalidates P19 readiness state and ref
- delivery revalidates P18 APS handoff dispatch state
- delivery revalidates P17 handoff/export prepare state
- delivery revalidates P16 package-review submit state
- delivery revalidates P15 package row id, kind, ref, hash, and server-owned
  artifact/payload identity
- delivery recomputes P14/P12 authority server-side
- mixed-source delivery emits a mixed-source-specific schema id
- generic/selected-pass/source-directory/SEC cross-shape requests fail closed
- mismatched readiness ref, package id, package kind, or package hash fails
  closed
- connector/destination/provider/public/signed URL fields remain blocked
- package rows and package payloads are not mutated
- local paths remain redacted from status and error surfaces

Minimum validation for the future implementation pass:

- touched-file `py_compile`
- focused mixed-source delivery API tests
- affected `backend/tests/test_layer3_external_export_response.py` helper tests
- affected Layer 3 API/workbench tests
- full `backend/tests/test_layer3_api.py` if the generic delivery route or
  shared workbench service changes
- manifest JSON syntax
- `python -B .\tools\l3-authority-index-validate.py`
- `python -B .\tools\l3-target-selection-validate.py --expect frozen`
- `python -B .\tools\l3-progress-check.py`
- `git diff --check`

`node --check .\backend\app\review_ui\static\layer3.js` and browser tests are
required only if a later, separately frozen rendered UI/static pass touches the
Layer 3 UI.
