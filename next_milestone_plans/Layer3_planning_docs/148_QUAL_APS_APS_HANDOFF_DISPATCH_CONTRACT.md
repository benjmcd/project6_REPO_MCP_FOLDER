# Layer 3 Qualitative APS APS Handoff Dispatch Contract

Status: current-main API and state contract paired with `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md`.

This contract defines the live API/state/proof shape for `qual_aps_aps_handoff_dispatch_entry`. Current main admits qualitative APS APS handoff dispatch for the exact qualitative APS prepare authority chain, then keeps qualitative APS external export/download blocked with `qualitative_aps_external_export_download_not_admitted`.

## Authority Order

Qualitative APS APS handoff dispatch must resolve authority in this order:

1. live source and tests on `project6-origin/main`;
2. `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md`;
3. `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md` and `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`;
4. `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`;
5. `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`;
6. `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`;
7. qualitative execution governance in `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`;
8. qualitative hybrid/RAG boundary in `124_QUAL_HYBRID_RAG_FREEZE.md`;
9. generic APS handoff docs `09_GATED_APS_HANDOFF_FREEZE.md`, `10_APS_HANDOFF_CONTRACT.md`, and current owner service `backend/app/services/layer3_aps_handoff.py` as owner-service pattern sources;
10. current workbench/API route behavior in `backend/app/services/layer3_workbench.py`, `backend/app/services/layer3_handoff_contract.py`, `backend/app/api/layer3.py`, and `backend/app/services/layer3_workbench_package_state.py`;
11. `backend/tests/test_layer3_bounded_e2e.py`, `backend/tests/test_layer3_qual_aps_execution.py`, `backend/tests/test_layer3_api.py`, and APS handoff tests;
12. request payload as operator dispatch intent only;
13. browser state as non-authoritative display/cache only.

Planning prose, browser state, raw document text, mockup state, PR titles, branch names, and client-provided package bytes are never sufficient APS handoff dispatch authority.

## Route Contract

Default route:

- `POST /api/v1/layer3/handoff/aps/dispatch`

Selected response schema:

- `layer3.qual_aps_aps_handoff_dispatch.v1`

Route reuse is preferred because the existing route already separates APS handoff dispatch from handoff/export prepare, external export/download readiness, connector record behavior, and delivery. A new route is allowed only if implementation audit proves route reuse would make qualitative APS, quantitative single-item, or associated-cohort dispatch authority ambiguous.

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
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `prepare_record_ref`;
- `handoff_export_state`;
- `handoff_export_envelope_ref`;
- `handoff_target`;
- `export_mode`;
- `aps_handoff_target`;
- `dispatch_mode`;
- `operator_decision`.

Conditionally allowed:

- `decision_notes`;
- `analysis_run_id`, but it must be absent or null for qualitative APS execution because qualitative APS execution does not create `AnalysisRun`.

`package_kinds` must equal:

- `canonical_internal`;
- `user_facing`;
- `review_facing`.

`package_review_state` must equal:

- `package_review_approved`.

`handoff_export_state` must equal:

- `qual_aps_handoff_export_prepared` for qualitative APS. If the shared route internally maps through the generic state constant, it must still prove qualitative prepare authority from the persisted prepare object.

`handoff_target` must equal:

- `internal_export_envelope`.

`export_mode` must equal:

- `prepare_only`.

`aps_handoff_target` must equal:

- `aps_evidence_bundle`.

`dispatch_mode` must equal:

- `server_side_aps_handoff`.

`operator_decision` must equal:

- `dispatch_aps_handoff`.

Forbidden request fields include:

- `dataset_version_id`;
- `content_id`, `material_snapshot_id`, `analysis_unit_id`, or `analysis_set_id` as client authority;
- raw document text, raw chunk text, qualitative output payload bytes, or package payload bytes;
- local paths, provider paths, URLs, buckets, ACLs, signed URL fields, public URL fields, connector ids, destination ids, or credentials;
- external export/download fields, connector fields, destination fields, provider/public URL fields, package mutation fields, package reconstruction fields, replacement package fields, package payload overrides, source expansion fields, upload fields, local-directory fields, web connector fields, RAG/vector fields, adapter registry fields, prompt/model/LLM fields, retry/recovery/rerun fields, cancel fields, auth fields, UI fields, theme fields, or mockup fields.

The server must derive source, document, unit, set, chunk, output, package, payload, review, construction, submit, prepare, envelope, and APS bundle authority from persisted state and server-owned artifacts.

## Admission Contract

An available qualitative APS APS handoff dispatch requires:

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
- exactly one reconciliation record exists for the constructed package set;
- exactly three output package rows exist for `canonical_internal`, `user_facing`, and `review_facing`;
- package ids, kinds, payload refs, and payload hashes match persisted package rows;
- package-review submit state exists, is approved, uses schema `layer3.qual_aps_package_review_submit.v1`, and matches the same package/construction/result-review authority;
- handoff/export prepare state exists, is prepared, uses the qualitative APS prepare authority chain, and has a matching `prepare_record_ref` and internal envelope ref;
- APS content document, chunks, material snapshot, analysis unit, analysis set, output payload hash, package candidate kinds, construction basis, submit basis, prepare basis, and envelope identity still match persisted authority;
- owner-service `layer3_aps_handoff.py` compatibility is satisfied for the exact qualitative APS source/package authority;
- no existing APS handoff package or dispatch state conflicts with the request.

Any missing, stale, malformed, mismatched, non-approved, duplicate-conflicting, or cross-session authority must fail closed before mutation.

Qualitative APS attempts that lack the exact persisted package-preview, construction, package-review submit, handoff/export prepare, envelope, payload, and source authority must fail closed before writing dispatch state or creating an APS handoff package.

## State Contract

Allowed state effects for successful dispatch:

- create exactly one APS evidence-bundle handoff package row through the existing APS handoff owner service;
- write exactly one server-owned APS bundle artifact file required by that owner service;
- record exactly one qualitative APS APS handoff dispatch object in `L3ReconciliationRecord.summary_json`;
- optionally record session/operator summary pointer fields in `L3Session.summary_json`.

Forbidden state effects:

- create additional reconciliation rows;
- create or mutate source authority rows;
- create external export/download, connector, provider, delivery, signed-reference, auth, source-ingestion, RAG/vector, runtime snapshot, mockup, destination, plan, pass, run, or artifact state;
- create `AnalysisRun`;
- create or mutate replacement package-set, supersession, mutation, reconstruction, replacement artifact, or namespace state;
- mutate existing package rows or package payload files;
- alter qualitative execution output, result-review state, package-review preview state, package construction state, package-review submit state, handoff/export prepare state, construction basis hash, output package ids, payload refs, or payload hashes.

## Response Contract

Minimum current response fields:

- `schema_id`;
- `status`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_identity`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_submit_record_ref`;
- `package_review_state`;
- `prepare_record_ref`;
- `handoff_export_state`;
- `handoff_export_envelope_ref`;
- `handoff_target`;
- `export_mode`;
- `aps_handoff_target`;
- `dispatch_mode`;
- `operator_decision`;
- `decision_notes`;
- `aps_handoff_state`;
- `aps_handoff_record_ref`;
- `aps_output_package_id`;
- `aps_output_package_kind`;
- `aps_bundle_ref`;
- `aps_bundle_id`;
- `aps_schema_id`;
- `external_export_enabled`;
- `download_enabled`;
- `connector_dispatch_enabled`;
- `provider_public_url_enabled`;
- `downstream_unavailable`;
- `next_allowed_actions`.

`external_export_enabled`, `download_enabled`, `connector_dispatch_enabled`, and `provider_public_url_enabled` must remain false in this tranche. `next_allowed_actions` must not include external export/download delivery, connector dispatch, destination send, or provider/public URL actions until separate freezes admit them.

The response must not include generated downstream download descriptors, download URLs, public URLs, signed URLs, connector run ids, destination ids, editable package payload bodies, rewritten package content, or any field implying external delivery has already happened.

## Idempotency And Concurrency Contract

`client_request_id` is required.

Rules:

- duplicate `client_request_id` with the same dispatch basis returns the same decision state or an explicit already-dispatched response;
- duplicate `client_request_id` with a different dispatch basis fails closed;
- a second request with a different `client_request_id` after dispatch exists must fail closed unless the stored decision proves the same authority basis and same decision;
- concurrent duplicate dispatch attempts cannot create duplicate or divergent dispatch state or duplicate APS handoff packages;
- partial dispatch state must fail closed.

The dispatch basis hash must include:

- request identity fields;
- package-review preview hash;
- package-review submit record ref and schema id;
- prepare record ref;
- handoff/export envelope ref;
- source document/material/unit/set authority;
- output payload ref/hash;
- result-review record ref;
- reconciliation record id;
- package ids;
- package kinds;
- payload refs and hashes;
- operator decision and decision notes.

## Failure Contract

The current runtime must fail closed when:

- session, plan, preview hash, pass run, output metadata, result-review state, package-review preview state, construction state, package-review submit state, handoff/export prepare state, envelope state, reconciliation record, package rows, content document, chunks, material snapshot, analysis unit, or analysis set is missing;
- pass run is not qualitative APS document execution;
- result review is not approved;
- package-review submit is not approved;
- handoff/export prepare is not prepared;
- package-review preview hash, submit record ref, prepare record ref, envelope ref, output payload hash/ref, package ids, package kinds, payload refs, or payload hashes do not match server-derived authority;
- client provides document/source/package/downstream authority fields;
- an APS handoff package already exists without matching workbench dispatch state;
- owner-service APS handoff compatibility fails;
- request attempts external export/download, source expansion, RAG/vector retrieval, local upload/directory ingestion, connector/destination dispatch, provider/public URL, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration changes, rendered UI changes, theme behavior, or auth/security behavior.

## Test Contract

Minimum current implementation tests:

- one successful API dispatch after standalone APS qualitative handoff/export prepare;
- bounded E2E reaches APS handoff dispatch and stops before external export/download;
- missing or non-prepared handoff/export prepare state fails closed;
- stale prepare record ref and stale envelope ref fail closed;
- missing submit state fails closed;
- missing construction state fails closed;
- partial package set fails closed;
- missing or stale package-review preview hash fails closed;
- stale package-review submit record ref fails closed;
- stale preview id/hash fails closed;
- stale output payload ref/hash fails closed;
- mismatched reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed;
- wrong engine family and wrong source shape fail closed;
- owner-service APS compatibility failure fails closed before mutation;
- forbidden request fields fail closed before mutation;
- duplicate `client_request_id` same basis is deterministic;
- duplicate `client_request_id` different basis fails closed;
- concurrent duplicate requests do not create divergent dispatch state;
- exactly one APS handoff package row and one APS bundle artifact are created on success;
- no rows or files are created on failure;
- existing package refs, hashes, rows, and files remain unchanged;
- existing quantitative single-item and associated-cohort APS dispatch behavior remains unchanged;
- no external export/download, connector, provider/public URL, source, RAG/vector, model/migration, hidden LLM, full mockup, rendered UI, theme, or auth/security side effects;
- progress checker guard if needed;
- headed and headless Chrome proof only if rendered UI changes.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- external export/download prepare/deliver, connector/destination dispatch, or provider/public URL behavior;
- source expansion, ingestion, RAG/vector retrieval, or adapter registry behavior;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- package mutation/reconstruction, supersession, replacement artifact generation, or replacement namespace behavior;
- schema/model/migration changes;
- existing package row mutation or existing package payload rewrite;
- rendered UI controls or theme-visible behavior without a UI freeze and browser proof;
- auth/security behavior.
