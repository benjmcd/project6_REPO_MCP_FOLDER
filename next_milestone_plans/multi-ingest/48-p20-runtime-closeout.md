# P20 Mixed-Source External Export/Download Delivery Runtime Closeout

Status: branch-local runtime implementation proof. Current-main authority begins
only after this branch merges and detached post-merge proof passes.

## Scope

This pass implements exactly one mixed-source external export/download delivery
surface selected by `47-p20-mixed-export-download-delivery-freeze.md`:
same-origin artifact-stream delivery over an already recorded P19 mixed-source
external export/download readiness state.

The admitted response schema is:

- `layer3.mixed_source_external_export_download_delivery.v1`

The admitted package family, readiness state, delivery state, delivery mode, and
operator decision are:

- `mixed_dataset_document`
- `mixed_source_external_export_download_ready`
- `mixed_source_external_export_download_delivered`
- `same_origin_artifact_stream`
- `deliver_mixed_source_external_export_download`

The runtime streams one existing server-owned mixed-source package artifact when
the selected `output_package_id`, `package_kind`, `package_payload_hash`, P19
readiness refs, and full P14/P15/P16/P17/P18/P19 authority chain match current
server-owned state.

## Runtime Behavior

The delivery request admits only:

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

Server-side validation reloads the session and P15 reconciliation, requires the
recorded P19 readiness state on both reconciliation and session summary,
replays P19 readiness with the recorded P19 idempotency basis, reloads the
current package rows, validates the selected package identity/hash against the
current package artifact, and only then returns the artifact stream.

On success, the runtime records a reference-only delivery state in:

- `L3ReconciliationRecord.summary_json.external_export_download_delivery`
- `L3Session.summary_json.external_export_download_delivery`

The recorded delivery state contains only public refs, package identity, hashes,
negative authority flags, and delivery metadata. It does not store or expose
local package paths or package payload refs in status/control summaries.

Response headers identify the mixed-source delivery schema, delivery state,
package family, output package id, package kind, package payload hash, P19
readiness record ref, and P20 delivery record ref. Headers do not expose local
paths, download URLs, signed references, public/provider URLs, connector refs,
or destination refs.

## Fail-Closed Cases

The runtime fails closed for:

- missing `client_request_id`
- missing required delivery fields
- unsupported lifecycle values
- explicit empty or unexpected `expected_package_kinds`
- missing or mismatched P19 readiness state
- P19 readiness missing its idempotency basis
- session readiness state mismatched with reconciliation readiness state
- recomputed P19 readiness ref/state mismatch
- partial, extra, or unexpected package rows
- P19 package ids, kinds, public refs, or payload hashes mismatched with current
  package rows
- selected `output_package_id`, `package_kind`, or `package_payload_hash`
  mismatched with the selected current package row
- missing server-owned package artifact
- package artifact hash mismatch
- existing conflicting delivery state
- selected-pass, source-directory, SEC XBRL, URL, signed-reference, public/provider,
  connector, destination, local outbox, package rewrite, parser/source expansion,
  schema/migration, local upload/directory, excluded-tool, retry/recovery, or
  package mutation fields on the mixed-source delivery request

## Non-Goals

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

## Verification

Branch-local verification passed:

- `python -B -m py_compile .\backend\app\api\layer3.py .\backend\app\services\layer3_workbench.py .\backend\app\services\layer3_external_export_contract.py .\backend\app\services\layer3_external_export_response.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_external_export_response.py`
- `python -B -m pytest .\backend\tests\test_layer3_api.py -q -k "mixed_source_external_export_download or external_export_download_deliver or external_export_download_contracts or openapi"`
  (`23 passed, 273 deselected, 4 warnings`)
- `python -B -m pytest .\backend\tests\test_layer3_external_export_contract.py .\backend\tests\test_layer3_external_export_response.py -q`
  (`11 passed, 2 warnings`)
- `python -B -m pytest .\backend\tests\test_layer3_bounded_e2e.py -q -k "download_delivery or external_export_download"`
  (`1 passed, 3 deselected, 4 warnings`)

Additional final validation passed:

- `python -B -m pytest .\backend\tests\test_layer3_api.py -q`
  (`296 passed, 4 warnings`)
- manifest JSON syntax for authority/progress/proof manifests
- `python -B .\tools\l3-authority-index-validate.py`
- `python -B .\tools\l3-target-selection-validate.py --expect frozen`
- `python -B .\tools\l3-progress-check.py`
- `git diff --check`

Detached post-merge proof is required after merge before this branch-local
closeout can be treated as current-main implementation authority.

## Next Posture

After this runtime lands and current main is synced, the next safe mixed-source
downstream decision is not another backend delivery implementation. The next
surface should be selected by a separate freeze from one of:

- rendered delivery controls over the existing same-origin stream
- signed-reference governance for mixed-source packages
- provider/public URL governance
- connector/destination dispatch governance
- a stop-for-product-authority checkpoint if no downstream operator surface is
  selected

Download URLs, signed references, public/provider URLs, connector/provider/
destination behavior, schema/model/migration changes, parser/source-shape
expansion, package payload rewrite, excluded-tool behavior, and production
readiness remain blocked until a later freeze selects and proves them.
