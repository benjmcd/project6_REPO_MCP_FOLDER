# P21 Mixed-Source Rendered Delivery Controls Freeze

Status: branch-local planning/control freeze only. No rendered UI behavior,
backend runtime behavior, API route behavior, schema/model/migration, parser,
source-shape, package payload rewrite, provider/connector/destination,
download URL, signed-reference, SEC XBRL, excluded-tool, or production
readiness behavior is admitted in this pass.

## Scope

This freeze selects exactly one next mixed-source downstream surface after P20:
rendered `/review/layer3` operator controls for the already-live P20
same-origin mixed-source external export/download delivery runtime.

The future implementation may make the existing rendered external
export/download delivery form usable for `mixed_dataset_document` only when
server-owned session summary and reconciliation state contain complete P20
delivery authority derived from recorded P19 readiness and current package
rows. It must not infer readiness from selected-pass result-review authority,
source-directory qualitative authority, browser state, local package paths,
client-restated package payload data, or ad hoc download references.

The future implementation may change only the rendered operator path and its
focused page/static tests. It must consume the existing P20 backend delivery
contract and route:

- `POST /api/v1/layer3/handoff/export/download/deliver`
- `layer3.mixed_source_external_export_download_delivery.v1`
- `delivery_mode: same_origin_artifact_stream`
- `operator_decision: deliver_mixed_source_external_export_download`

## Current Authority Facts

Current main after PR `#2224` has these facts:

- P20 same-origin mixed-source external export/download delivery is current-main
  runtime behavior after PR `#2223`;
- the P20 runtime streams one existing server-owned mixed-source package
  artifact only after revalidating P14/P15/P16/P17/P18/P19 authority, recorded
  P19 readiness, current package rows, selected package id/kind/hash, and
  artifact hash;
- P20 records reference-only delivery state in session and reconciliation JSON,
  with public package refs and record refs but no local path or `payload_ref`
  status exposure;
- `/review/layer3` already contains rendered selected-pass/source-directory
  external export/download controls and a P17A mixed-source rendered
  material-authority handoff/export prepare precedent;
- current P20 docs explicitly keep rendered browser download controls blocked
  until a later freeze selects and proves them.

Therefore the next high-ROI surface is not another backend delivery runtime,
not signed-reference/provider/connector behavior, and not package mutation. It
is a rendered material-authority delivery control over the already-admitted P20
same-origin stream.

## Future Rendered Contract

The future rendered implementation may submit exactly one P20
material-authority delivery request when all required fields are present in
server state:

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

The rendered control must use:

- `delivery_mode: same_origin_artifact_stream`
- `operator_decision: deliver_mixed_source_external_export_download`
- `handoff_target: mixed_source_review_package`
- `export_mode: reference_envelope_only`
- `aps_handoff_target: mixed_source_aps_evidence_bundle`
- `dispatch_mode: server_side_mixed_source_aps_handoff`
- `external_export_download_readiness_state:
  mixed_source_external_export_download_ready`

The rendered payload must be assembled from server-owned session summary and
delivery/readiness/package authority, not from client-authored package payload
bytes or local path fields.

## Status Surface Requirements

Before complete P20 authority is present, the UI may show mixed-source delivery
as unavailable or blocked. It must not enable the selected-pass delivery submit
path for mixed-source packages.

When complete P20 authority is present, the UI may show:

- mixed package family;
- selected output package id, package kind, and package payload hash;
- public `layer3://mixed-source-package/...` refs;
- P19 readiness record/ref/state;
- P20 delivery record/ref/state when present;
- negative authority flags already supplied by server state.

It must not reveal local storage paths, request raw package payload bytes,
download URLs, signed-reference tokens, public/provider URLs, connector refs,
destination refs, credentials, or local outbox targets.

## Fail-Closed Cases

Future rendered implementation must keep controls disabled or fail closed for:

- missing `session_id`;
- missing material preview authority;
- missing `package_review_preview_hash`;
- missing `contract_hash`;
- missing `construction_basis_hash`;
- missing `reconciliation_record_id`;
- missing or non-approved package-review submit authority;
- missing P17 handoff/export prepare authority;
- missing P18 APS handoff dispatch authority;
- missing P19 external export/download readiness authority;
- missing, partial, or extra package ids/kinds/hashes;
- missing selected `output_package_id`, `package_kind`, or
  `package_payload_hash`;
- selected-pass-only `result_review_record_ref` authority;
- source-directory qualitative delivery authority;
- stale, mismatched, or cross-shape server summary fields;
- browser-authored `payload_ref`, local path, package bytes, `download_url`,
  signed-reference, public/provider URL, connector, destination, local outbox,
  parser/source-shape, schema/migration, package rewrite, retry/recovery, or
  excluded-tool fields;
- already recorded conflicting delivery state;
- pending lifecycle work.

The backend P20 route remains the fail-closed authority for stale, mismatched,
missing, cross-shape, and disallowed fields.

## Non-Goals

- No runtime code change in this freeze.
- No backend API route change in this freeze.
- No rendered UI behavior change in this freeze.
- No P20 backend contract change.
- No browser download control behavior in this freeze.
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

Implementation may begin only after this freeze is merged and current-main
synced. The implementation pass must keep the change narrow to the rendered
material-authority delivery path and focused tests. If implementation discovers
that a backend DTO, schema, migration, parser, source-shape, package payload,
signed-reference, provider, connector, destination, local outbox, or external
download URL change is required, stop and create a new freeze instead of
widening this one.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
