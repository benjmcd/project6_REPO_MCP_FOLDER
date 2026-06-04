# P17A Mixed-Source Rendered Handoff Status Freeze

Status: branch-local planning/control freeze only. No rendered UI behavior,
runtime endpoint behavior, downstream dispatch, export, schema, parser,
source-shape, payload rewrite, or production-readiness behavior is admitted in
this pass.

## Scope

This freeze selects the next implementation boundary after P17: a rendered
operator status and prepare-control path for the already-live P17
material-authority mixed-source handoff/export prepare API.

The future implementation may make the `/review/layer3` handoff/export prepare
control usable for `mixed_dataset_document` only when the session summary
contains server-owned P17 material authority from an approved P16 submit state.
It must not infer readiness from selected-pass result-review authority, browser
state, local package paths, or client-restated package payload data.

The future implementation may change only the rendered operator path and its
focused tests. It must consume the existing P17 API contract. It must not add a
new backend endpoint, model, migration, parser/source-family behavior,
package-construction behavior, package-review submit behavior, handoff/export
prepare runtime behavior, APS handoff, external export/download, connector
dispatch, provider URL behavior, local outbox behavior, or production-readiness
claim.

## Current Authority Facts

Current main after PR `#2206` has these facts:

- the direct P17 API path admits material-authority mixed-source prepare through
  `POST /api/v1/layer3/handoff/export/prepare`;
- the unprepared mixed-source session summary carries material-authority fields
  but reports `available: false`, `handoff_export_prepare_enabled: false`, and
  `blocked_reason: mixed_source_handoff_export_prepare_rendered_control_not_admitted`;
- the recorded prepared state is reported after direct API prepare;
- the existing rendered handoff/export prepare control still builds a
  selected-pass payload with `result_review_record_ref`,
  `handoff_target: internal_export_envelope`, and `export_mode: prepare_only`;
- mixed-source prepare requires `handoff_target: mixed_source_review_package`,
  `export_mode: reference_envelope_only`, and material-authority fields.

Therefore the future rendered path must be a material-authority path, not a
selected-pass fallback or browser-authored bridge.

## Future Rendered Contract

The future rendered implementation may submit exactly one P17 material-authority
prepare request when all required fields are present in server state:

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

The rendered control must use:

- `handoff_target: mixed_source_review_package`
- `export_mode: reference_envelope_only`

The rendered control must require `package_review_state:
package_review_approved`. It must require `decision_notes` for `hold`,
`decline`, and `blocked`, matching the P17 API contract.

The rendered control must preserve existing selected-pass and
source-directory qualitative handoff/export flows. Mixed-source material
authority must be selected by package family and field presence, not by
truthiness of optional selected-pass fields.

## Status Surface Requirements

Before direct or rendered prepare, the UI may show a mixed-source status panel
or message explaining that a material-authority prepare path is required. It
must not show selected-pass handoff/export prepare readiness for mixed-source
packages.

After prepare, the UI may render the recorded P17 prepared state, public
`layer3://mixed-source-package/...` refs, reference-envelope ref, package
kinds, hashes, and negative authority flags already provided by the session
summary. It must not reveal local storage paths or request raw package payload
bytes.

## Fail-Closed Cases

Future rendered implementation must fail closed or keep controls disabled for:

- missing `session_id`;
- missing material preview authority;
- missing `package_review_preview_hash`;
- missing `contract_hash`;
- missing `construction_basis_hash`;
- missing `reconciliation_record_id`;
- missing `package_review_submit_record_ref`;
- non-approved package-review state;
- missing, partial, or extra package IDs;
- missing, partial, or extra payload hashes;
- missing or unexpected package kinds;
- selected-pass `result_review_record_ref`-only authority;
- selected-pass `handoff_target` or `export_mode` defaults;
- local path, payload ref override, provider URL, public URL, connector,
  destination, APS handoff, external export/download, local outbox, parser,
  source-shape, schema, migration, payload rewrite, or excluded-tool fields.

## Non-Goals

- No runtime code change in this freeze.
- No backend API route change in this freeze.
- No rendered UI behavior change in this freeze.
- No P17 API contract change.
- No package-family policy change.
- No package construction, package-review submit, or handoff/export prepare
  backend behavior change.
- No APS handoff.
- No external export/download.
- No connector dispatch.
- No provider-public URL, provider-private signed URL, public URL, local
  outbox, network egress, or destination behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction or mutation.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Implementation Entry Gate

Implementation may begin only after this freeze is merged and current-main
synced. The implementation pass must keep the change narrow to the rendered
material-authority operator path and its tests. If implementation discovers that
a backend DTO, schema, migration, parser, source-shape, package payload,
downstream dispatch, or provider/connector change is required, stop and create a
new freeze instead of widening this one.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
