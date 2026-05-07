# Layer 3 Qualitative APS Handoff Export Prepare Contract

Status: current-main API and state contract paired with `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md`.

This contract defines the live API/state/proof shape for `qual_aps_handoff_export_prepare_entry`. Current main admits qualitative APS handoff/export prepare only through `POST /api/v1/layer3/handoff/export/prepare` after the approved qualitative APS package-review submit state, and the former blocker `qualitative_aps_handoff_export_prepare_not_admitted` has been removed for that exact authority chain.

## Authority Order

Qualitative APS handoff/export prepare must resolve authority in this order:

1. live source and tests on `project6-origin/main`;
2. `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md`;
3. `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`;
4. `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`;
5. `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`;
6. qualitative execution governance in `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`;
7. qualitative hybrid/RAG boundary in `124_QUAL_HYBRID_RAG_FREEZE.md`;
8. generic handoff/export docs `54_L3_WB_HANDOFF_EXPORT_FREEZE.md` and `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md` as pattern sources only;
9. associated-cohort handoff/export docs `92_COHORT_HANDOFF_EXPORT_FREEZE.md` and `93_COHORT_HANDOFF_EXPORT_CONTRACT.md` as pattern sources only;
10. `backend/app/services/layer3_workbench.py`, `backend/app/services/layer3_handoff_contract.py`, and `backend/app/services/layer3_handoff_export_response.py` for current route behavior;
11. `backend/tests/test_layer3_bounded_e2e.py`, `backend/tests/test_layer3_qual_aps_execution.py`, and `backend/tests/test_layer3_api.py`;
12. request payload as operator prepare intent only;
13. browser state as non-authoritative display/cache only.

Planning prose, browser state, raw document text, mockup state, PR titles, branch names, and client-provided package bytes are never sufficient handoff/export prepare authority.

## Route Contract

Default route:

- `POST /api/v1/layer3/handoff/export/prepare`

Selected response schema:

- `layer3.qual_aps_handoff_export_prepare.v1`

Route reuse is preferred because the existing handoff/export route family already separates prepare, APS dispatch, external export/download readiness, and delivery. A new route is allowed only if implementation audit proves route reuse would make qualitative APS, quantitative single-item, or associated-cohort prepare authority ambiguous.

## Request Contract

Expected required fields:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_id`;
- `preview_hash`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- `construction_basis_hash`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `payload_refs`;
- `payload_hashes`;
- `expected_package_kinds`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `package_review_submit_schema_id`;
- `handoff_target`;
- `export_mode`;
- `operator_decision`.

Conditionally allowed:

- `decision_notes`, required for `hold`, `decline`, and `blocked`;
- `analysis_run_id`, but it must be absent or null for qualitative APS execution because qualitative APS execution does not create `AnalysisRun`.

`expected_package_kinds` must equal:

- `canonical_internal`;
- `user_facing`;
- `review_facing`.

`package_review_state` must equal:

- `package_review_approved`.

`package_review_submit_schema_id` must equal:

- `layer3.qual_aps_package_review_submit.v1`.

`handoff_target` must equal:

- `internal_export_envelope`.

`export_mode` must equal:

- `prepare_only`.

`operator_decision` must equal one of:

- `authorize_prepare`;
- `hold`;
- `decline`;
- `blocked`.

Forbidden request fields include:

- `dataset_version_id`;
- `content_id`, `material_snapshot_id`, `analysis_unit_id`, or `analysis_set_id` as client authority;
- raw document text, raw chunk text, qualitative output payload bytes, or package payload bytes;
- local paths, provider paths, URLs, buckets, ACLs, signed URL fields, public URL fields, connector ids, destination ids, or credentials;
- APS dispatch fields, external export/download fields, connector fields, destination fields, provider/public URL fields, package mutation fields, package reconstruction fields, replacement package fields, package payload overrides, source expansion fields, upload fields, local-directory fields, web connector fields, RAG/vector fields, adapter registry fields, prompt/model/LLM fields, retry/recovery/rerun fields, cancel fields, auth fields, UI fields, theme fields, or mockup fields.

The server must derive source, document, unit, set, chunk, output, package, payload, review, construction, submit, and preparation authority from persisted state and server-owned artifacts.

## Admission Contract

An available qualitative APS handoff/export prepare requires:

- current session exists and matches the request;
- approved analysis plan exists and matches `preview_id` and `preview_hash`;
- selected pass run exists for the same session and approved plan;
- pass run engine family is `qualitative_aps_document`;
- pass scope is `single_aps_doc_qualitative_pass`;
- qualitative execution is terminal with readable qualitative output metadata;
- `analysis_run_id` is absent or null;
- result-review state exists, is approved, and matches the same session, plan, preview id/hash, pass run, output payload, and source document;
- package-review preview state exists and `package_review_preview_hash` matches qualitative server-derived preview authority;
- qualitative package construction state exists and has source gate `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE`;
- `construction_basis_hash` matches persisted construction authority;
- exactly one reconciliation record exists for the constructed package set;
- exactly three output package rows exist for `canonical_internal`, `user_facing`, and `review_facing`;
- package ids, payload refs, and payload hashes match the persisted package rows;
- package-review submit state exists, is approved, uses schema `layer3.qual_aps_package_review_submit.v1`, and matches the same package/construction/result-review authority;
- APS content document, chunks, material snapshot, analysis unit, analysis set, output payload hash, package candidate kinds, construction basis, and submit basis still match preview, construction, and submit authority;
- no existing handoff/export prepare state conflicts with the request.

Any missing, stale, malformed, mismatched, non-approved, duplicate-conflicting, or cross-session authority must fail closed before mutation.

Qualitative APS attempts that lack the exact persisted package-preview, construction, package-review submit, payload, and source authority must fail closed before writing handoff/export prepare state.

## State Contract

Allowed state effects for a successful prepare:

- record exactly one qualitative APS handoff/export prepare object in `L3ReconciliationRecord.summary_json`;
- optionally record session/operator summary pointer fields in `L3Session.summary_json`;
- include an internal handoff/export envelope identity only when `operator_decision == "authorize_prepare"`.

Forbidden state effects:

- create or mutate package rows or package payload files;
- create additional reconciliation rows;
- create APS dispatch, external export/download, connector, provider, delivery, signed-reference, auth, source-ingestion, RAG/vector, runtime snapshot, mockup, destination, plan, pass, run, or artifact state;
- create `AnalysisRun`;
- create or mutate source authority rows;
- alter qualitative execution output, result-review state, package-review preview state, package construction state, package-review submit state, construction basis hash, output package ids, payload refs, or payload hashes;
- create replacement package-set, supersession, mutation, reconstruction, replacement artifact, or namespace state.

## Response Contract

Minimum future response fields:

- `schema_id`;
- `status`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_identity`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- `construction_basis_hash`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `package_review_submit_schema_id`;
- `operator_decision`;
- `decision_notes`;
- `handoff_export_state`;
- `handoff_target`;
- `export_mode`;
- `external_handoff_enabled`;
- `external_export_enabled`;
- `aps_handoff_enabled`;
- `external_export_download_enabled`;
- `connector_dispatch_enabled`;
- `provider_public_url_enabled`;
- `downstream_unavailable`;
- `next_allowed_actions`.

`external_handoff_enabled`, `external_export_enabled`, `aps_handoff_enabled`, `external_export_download_enabled`, `connector_dispatch_enabled`, and `provider_public_url_enabled` must remain false in this tranche. `next_allowed_actions` must not include APS dispatch or external delivery actions until separate freezes admit them.

When `operator_decision == "authorize_prepare"`, the response may include `handoff_export_envelope` with only envelope identity, upstream authority refs, package ids/kinds, payload refs/hashes, prepared timestamp, and downstream disabled flags.

The response must not include APS handoff refs, connector dispatch refs, generated downstream artifacts, external export files, download URLs, public URLs, signed URLs, editable package payload bodies, rewritten package content, or any field implying downstream dispatch has already happened.

## Idempotency And Concurrency Contract

`client_request_id` is required.

Rules:

- duplicate `client_request_id` with the same prepare basis returns the same decision state or an explicit already-prepared response;
- duplicate `client_request_id` with a different prepare basis fails closed;
- a second request with a different `client_request_id` after a preparation decision exists must fail closed unless the stored decision proves the same authority basis and same decision;
- concurrent duplicate prepare attempts cannot create duplicate or divergent decision state;
- partial handoff/export prepare state must fail closed.

The prepare basis hash must include:

- request identity fields;
- package-review preview hash;
- construction basis hash;
- package-review submit record ref and schema id;
- source document/material/unit/set authority;
- output payload ref/hash;
- result-review record ref;
- reconciliation record id;
- package ids;
- package kinds;
- payload refs and hashes;
- operator decision and decision notes.

## Failure Contract

The future runtime must fail closed when:

- session, plan, preview hash, pass run, output metadata, result-review state, package-review preview state, construction state, package-review submit state, reconciliation record, package rows, content document, chunks, material snapshot, analysis unit, or analysis set is missing;
- pass run is not qualitative APS document execution;
- result review is not approved;
- package-review submit is not approved;
- package-review preview hash or construction basis hash does not match server-derived authority;
- package-review submit record ref or schema id does not match persisted submit authority;
- output payload hash/ref does not match result-review, construction, and submit state;
- package ids, kinds, payload refs, or payload hashes differ from the frozen set;
- decision is invalid or required decision notes are missing;
- client provides document/source/package/downstream authority fields;
- existing handoff/export prepare or downstream state conflicts with first prepare semantics;
- request attempts APS dispatch, external export/download, source expansion, RAG/vector retrieval, local upload/directory ingestion, connector/destination dispatch, provider/public URL, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration changes, rendered UI changes, theme behavior, or auth/security behavior.

## Test Contract

Minimum future implementation tests:

- one successful API prepare after standalone APS qualitative package-review submit;
- bounded E2E reaches handoff/export prepare and stops before APS dispatch;
- missing submit state fails closed;
- non-approved submit state fails closed;
- missing construction state fails closed;
- partial package set fails closed;
- missing or stale package-review preview hash fails closed;
- stale construction basis hash fails closed;
- stale package-review submit record ref fails closed;
- stale preview id/hash fails closed;
- stale output payload ref/hash fails closed;
- mismatched reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed;
- invalid decision and missing notes for `hold`, `decline`, or `blocked` fail closed;
- wrong engine family and wrong source shape fail closed;
- forbidden request fields fail closed before mutation;
- duplicate `client_request_id` same basis is deterministic;
- duplicate `client_request_id` different basis fails closed;
- concurrent duplicate requests do not create divergent decision state;
- no rows or files are created on success;
- payload refs, payload hashes, and package files remain unchanged;
- existing quantitative single-item and associated-cohort handoff/export behavior remains unchanged;
- no APS dispatch, external export/download, connector, provider/public URL, source, RAG/vector, model/migration, hidden LLM, full mockup, rendered UI, theme, or auth/security side effects;
- progress checker guard if needed;
- headed and headless Chrome proof only if rendered UI changes.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- APS dispatch, external export/download, connector/destination dispatch, or provider/public URL behavior;
- source expansion, ingestion, RAG/vector retrieval, or adapter registry behavior;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- package mutation/reconstruction, supersession, replacement artifact generation, or replacement namespace behavior;
- schema/model/migration changes;
- `L3OutputPackage.status` mutation;
- rendered UI controls or theme-visible behavior without a UI freeze and browser proof;
- auth/security behavior.
