# P21 Mixed-Source Rendered Delivery Controls Runtime Closeout

Status: branch-local runtime implementation proof for the rendered
`/review/layer3` mixed-source delivery control. This is not current-main
authority until the implementation PR merges and a current-main sync records the
merge commit.

## Scope

This pass implements the P21 freeze by making the existing rendered external
export/download delivery form usable for the already-live P20 mixed-source
same-origin delivery route:

- `POST /api/v1/layer3/handoff/export/download/deliver`
- `layer3.mixed_source_external_export_download_delivery.v1`
- `delivery_mode: same_origin_artifact_stream`
- `operator_decision: deliver_mixed_source_external_export_download`

The rendered control derives its submit packet from server-owned
`State.sessionSummary.external_export_download_readiness` and the current
mixed-source package authority carried by that state. It selects only the
`review_facing` mixed package, preserves the existing browser-managed
same-origin form-post delivery behavior, and records only UI-local submitted
state or server-returned delivered state.

## Authority Boundary

The rendered packet must fail closed unless P19/P20 material authority is
complete and internally consistent:

- mixed package family is `mixed_dataset_document`;
- package review is approved;
- P17 handoff/export prepare is recorded with
  `handoff_target: mixed_source_review_package` and
  `export_mode: reference_envelope_only`;
- P18 APS handoff dispatch is recorded with
  `aps_handoff_target: mixed_source_aps_evidence_bundle` and
  `dispatch_mode: server_side_mixed_source_aps_handoff`;
- P19 readiness is recorded with
  `external_export_download_readiness_state:
  mixed_source_external_export_download_ready`;
- package ids, kinds, and payload hashes are complete, exact, and current;
- the selected package kind is exactly `review_facing`.

The frontend must not synthesize authority from selected-pass result-review
state, source-directory qualitative state, browser-authored package refs,
local file paths, package bytes, download URLs, signed references, provider
URLs, connector refs, destinations, credentials, or local outbox fields.

## Runtime Effects

The rendered UI now:

- shows a mixed-source delivery panel sourced from
  `State.sessionSummary.external_export_download_readiness`;
- enables the existing external export/download delivery submit only when the
  mixed-source P19/P20 authority packet is complete and no mixed delivery is
  already recorded;
- submits only the fields admitted by the P20 backend delivery contract;
- treats browser-managed form timeout as
  `mixed_source_external_export_download_delivery_submitted`;
- records server-returned `mixed_source_external_export_download_delivered`
  state when available;
- explicitly keeps signed-reference controls blocked while mixed-source
  readiness is the active delivery authority.

## Non-Goals Preserved

- No backend runtime route change.
- No API schema, DTO, model, migration, parser, or source-shape change.
- No package payload rewrite, mutation, reconstruction, replacement, or
  supersession.
- No download URL, signed-reference, public/provider URL, connector,
  destination, credential, local outbox, or provider dispatch behavior.
- No source acquisition, Arelle, SEC XBRL, excluded-tool behavior, value reveal,
  default-on behavior, or production-readiness claim.

## Branch-Local Proof

The implementation proof for this branch includes:

- `node --check ./backend/app/review_ui/static/layer3.js`;
- `python -B -m pytest ./backend/tests/test_layer3_page.py -q`;
- `python -B -m pytest ./backend/tests/test_layer3_api.py -q -k
  "mixed_source_external_export_download_readiness or
  mixed_source_external_export_download_deliver"`;
- `python -B -m pytest
  ./backend/tests/test_layer3_external_export_response.py::test_mixed_external_export_delivery_response_helper_is_shared_with_workbench
  -q`;
- `npm run test:e2e -- --grep "P21 mixed-source"`;
- `npm run test:e2e:headed -- --grep "P21 mixed-source"`;
- manifest JSON syntax;
- Layer 3 authority-index validation;
- frozen target-selection validation;
- Layer 3 progress check;
- `git diff --check`.

## Next Posture

After this implementation merges and current-main sync records the actual PR
and merge commit, the next downstream surface must again be frozen before
implementation. Candidate surfaces remain signed-reference governance,
provider/public URL governance, connector/destination dispatch, durable audit
or revocation behavior, product-flow usability proof, or a stop-for-product
authority checkpoint. None is admitted by this closeout.
