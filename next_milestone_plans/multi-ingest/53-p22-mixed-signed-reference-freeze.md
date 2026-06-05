# P22 Mixed-Source Signed-Reference Governance Freeze

Status: branch-local planning/control freeze only. No backend runtime behavior,
API route behavior, rendered UI/static behavior, durable-state change,
schema/model/migration, parser, source-shape, package payload rewrite,
provider/connector/destination, download URL, SEC XBRL, excluded-tool,
value-reveal, default-on, or production-readiness behavior is admitted in this
pass.

## Scope

This freeze selects exactly one next mixed-source downstream surface after P21:
same-origin signed-reference governance for the current-main mixed-source
external export/download delivery chain.

The future implementation may admit short-lived, server-owned same-origin
signed-reference generation and use for `mixed_dataset_document` only after the
server revalidates the full mixed-source material-authority chain:

- P14 mixed-source package review preview authority;
- P15 mixed-source package construction commit state;
- P16 mixed-source package-review submit authority;
- P17 mixed-source handoff/export prepare authority;
- P18 mixed-source APS handoff dispatch authority;
- P19 mixed-source external export/download readiness authority;
- P20 same-origin mixed-source delivery authority;
- P21 rendered delivery state, when the request is initiated from
  `/review/layer3`;
- the current `review_facing` package row and its package ref, kind, id, hash,
  and artifact hash/size basis.

The future implementation may reuse the existing same-origin signed-reference
route family and durable-token service patterns, but it must add or dispatch a
mixed-source authority gate explicitly. It must not treat the existing
associated-cohort or source-intake signed-reference gates as mixed-source
authority.

## Selection Basis

Current main after P21 proves that mixed-source packages can be delivered only
as same-origin artifact streams through the existing P20 route and rendered P21
control. Current UI/static code explicitly blocks signed-reference controls
when mixed-source readiness is the active delivery authority.

Provider/public URL governance and connector/destination dispatch are not the
next implementation target. Current Layer 3 governance docs for those surfaces
require future activation evidence, provider or connector authority, security
posture, lifecycle, idempotency, and leakage contracts before implementation.

Therefore the narrowest downstream surface that improves operator usability
without provider credentials, public URLs, destination state, package mutation,
or source/schema widening is mixed-source same-origin signed-reference
governance.

## Future Runtime Contract

The future runtime may generate a mixed-source signed reference only when the
server can derive every required field from current durable/session authority.
The request must include or server-derive:

- `client_request_id`;
- `session_id`;
- `material_preview_id`;
- `material_preview_hash`;
- `package_review_preview_hash`;
- `contract_hash`;
- `construction_basis_hash`;
- `reconciliation_record_id`;
- `output_package_id`;
- `package_kind`;
- `package_payload_hash`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `prepare_record_ref`;
- `handoff_export_state`;
- `handoff_export_envelope_ref`;
- `handoff_target`;
- `export_mode`;
- `aps_handoff_target`;
- `dispatch_mode`;
- `aps_handoff_record_ref`;
- `aps_handoff_state`;
- `external_export_download_readiness_record_ref`;
- `external_export_download_readiness_ref`;
- `external_export_download_readiness_state`;
- `delivery_mode`;
- `operator_decision`;
- current package artifact ref/hash/size authority;
- optional `decision_notes`;
- optional `expected_package_kinds`.

The future runtime must use:

- `handoff_target: mixed_source_review_package`;
- `export_mode: reference_envelope_only`;
- `aps_handoff_target: mixed_source_aps_evidence_bundle`;
- `dispatch_mode: server_side_mixed_source_aps_handoff`;
- `external_export_download_readiness_state:
  mixed_source_external_export_download_ready`;
- `delivery_mode: same_origin_artifact_stream` as the prerequisite delivered
  artifact-stream mode;
- `signed_reference_delivery_mode: same_origin_signed_delivery_reference`;
- `operator_decision:
  generate_mixed_source_external_export_download_signed_reference`;
- `use_operator_decision:
  use_mixed_source_external_export_download_signed_reference`;
- `server_authority:
  mixed_source_external_export_download_signed_reference_gate`.

If the implementation keeps the existing generic response schema ids, it must
include mixed-source authority fields that distinguish the mixed gate from
associated-cohort and source-intake references. If it introduces
mixed-source-specific schema ids, they must remain bounded to the same-origin
reference and use surface only.

## Fail-Closed Cases

Future implementation must fail closed for:

- missing `client_request_id`;
- missing or stale material preview authority;
- missing `contract_hash` or `construction_basis_hash`;
- missing package-review preview or submit authority;
- missing or non-approved package-review state;
- missing P17 handoff/export prepare authority;
- missing P18 APS handoff dispatch authority;
- missing P19 external export/download readiness authority;
- missing P20 delivery authority;
- missing current `review_facing` package row;
- missing, partial, extra, stale, or mismatched package ids/kinds/hashes;
- stale package artifact ref/hash/size;
- selected-pass-only result-review authority;
- source-directory qualitative or source-intake authority;
- cross-shape signed-reference token use;
- client-supplied `download_url`, `download_token`, `public_url`,
  `provider_url`, `signed_url`, `signed_delivery_url`, local path, package
  bytes, package payload rewrite, provider, connector, destination, local
  outbox, retry/recovery/rerun, parser/source-shape, schema/migration, or
  excluded-tool fields;
- missing signed-reference secret or durable state when the implementation
  depends on current durable signed-reference tables;
- expired, malformed, revoked, reused beyond policy, wrong-session,
  wrong-artifact, or stale-authority references.

Failed signed-reference generation or use must not silently fall back to the
same-origin attachment endpoint.

## Status Surface Requirements

Future status surfaces may expose response-safe metadata only:

- mixed package family;
- selected output package id and kind;
- public `layer3://mixed-source-package/...` package refs;
- package payload hash and artifact hash/size;
- P17/P18/P19/P20 record refs and states;
- signed-reference token id/prefix, expiry, receipt id, replay policy, and use
  count when admitted by the existing durable signed-reference state family;
- negative authority flags for provider/public URL, connector/destination,
  package mutation, source-shape widening, and production readiness.

Status surfaces must not expose local storage paths, package payload bytes,
raw signed-reference tokens in durable state, download URLs, public/provider
URLs, connector targets, destination ids, credentials, local outbox targets, or
provider object keys.

## Non-Goals

- No runtime code change in this freeze.
- No backend API route change in this freeze.
- No rendered UI/static behavior change in this freeze.
- No signed-reference generation, use, status, revocation, or durable-state
  behavior in this freeze.
- No provider/public URL or provider dispatch behavior.
- No connector, destination, local outbox, credential, network, or external
  file delivery behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction, mutation, copy, amendment, replacement, or
  supersession.
- No download URL generation or exposure.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No SEC XBRL surface.
- No source acquisition or Arelle behavior.
- No value reveal, default-on behavior, or production-readiness activation.

## Implementation Entry Gate

Implementation may begin only after this freeze is merged and current-main
synced. The implementation pass must stay scoped to mixed-source same-origin
signed-reference generation/use over existing P19/P20/P21 authority and focused
tests. If implementation needs provider/public URLs, connector/destination
dispatch, durable-state schema changes beyond existing signed-reference tables,
rendered controls, package payload rewrite, parser/source-shape expansion,
local outbox, or external download URL behavior, stop and create a separate
freeze before editing.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
