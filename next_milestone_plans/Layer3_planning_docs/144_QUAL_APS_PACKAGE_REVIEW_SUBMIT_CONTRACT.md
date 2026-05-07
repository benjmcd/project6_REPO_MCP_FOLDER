# Layer 3 Qualitative APS Package Review Submit Contract

Status: planning/control API and state contract paired with `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md`.

This contract defines the future API/state/proof shape for `qual_aps_package_review_submit_entry`. It does not make package-review submit live. Current main still blocks qualitative APS package-review submit with `qualitative_aps_package_review_submit_not_admitted`.

## Authority Order

Qualitative APS package-review submit must resolve authority in this order:

1. live source and tests on `project6-origin/main`;
2. `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md`;
3. `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`;
4. `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`;
5. qualitative execution governance in `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`;
6. qualitative hybrid/RAG boundary in `124_QUAL_HYBRID_RAG_FREEZE.md`;
7. package submit pattern docs `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md` as pattern sources only;
8. associated-cohort submit docs `90_COHORT_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `91_COHORT_PACKAGE_REVIEW_SUBMIT_CONTRACT.md` as pattern sources only;
9. `backend/app/services/layer3_workbench.py` and package state/submit helpers for current route behavior;
10. `backend/tests/test_layer3_bounded_e2e.py` and `backend/tests/test_layer3_qual_aps_execution.py`;
11. request payload as operator decision intent only;
12. browser state as non-authoritative display/cache only.

Planning prose, browser state, raw document text, mockup state, PR titles, branch names, and client-provided package bytes are never sufficient package-review submit authority.

## Route Contract

Selected route:

- `POST /api/v1/layer3/package/review/submit`

Selected response schema:

- `layer3.qual_aps_package_review_submit.v1`

Route reuse is preferred because the existing package route family already separates preview, commit, and submit. A new route is allowed only if implementation audit proves route reuse would make qualitative APS, quantitative single-item, or associated-cohort submit authority ambiguous.

## Request Contract

Required fields:

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
- `operator_decision`.

Conditionally allowed:

- `decision_notes`, required for `changes_requested`, `rejected`, and `blocked`;
- `analysis_run_id`, but it must be absent or null for qualitative APS execution because qualitative APS execution does not create `AnalysisRun`.

`expected_package_kinds` must equal:

- `canonical_internal`;
- `user_facing`;
- `review_facing`.

`operator_decision` must equal one of:

- `approved`;
- `changes_requested`;
- `rejected`;
- `blocked`.

Forbidden request fields include:

- `dataset_version_id`;
- `content_id`, `material_snapshot_id`, `analysis_unit_id`, or `analysis_set_id` as client authority;
- raw document text, raw chunk text, or qualitative output payload bytes;
- local paths, provider paths, URLs, buckets, ACLs, signed URL fields, public URL fields, connector ids, destination ids, or credentials;
- package bytes, replacement package fields, supersession fields, mutation fields, reconstruction fields, editable variant fields, or package payload overrides;
- handoff/export, APS dispatch, external export/download, connector, destination, provider, source expansion, upload, directory, web connector, RAG/vector, adapter registry, runtime DB expansion, prompt, model, LLM, retry, recovery, rerun, cancel, auth, UI, theme, or mockup fields.

The server must derive source, document, unit, set, chunk, output, package, payload, and review authority from persisted state and server-owned artifacts.

## Admission Contract

An available qualitative APS package-review submit requires:

- current session exists and matches the request;
- approved analysis plan exists and matches `preview_id` and `preview_hash`;
- selected pass run exists for the same session and approved plan;
- pass run engine family is `qualitative_aps_document`;
- pass scope is `single_aps_doc_qualitative_pass`;
- selected pass is terminal with readable qualitative output metadata;
- result-review state exists, is approved, and matches the same session, plan, preview id/hash, pass run, output payload, and source document;
- package-review preview state is available and `package_review_preview_hash` matches server-derived preview authority;
- qualitative package construction state exists and has source gate `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE`;
- `construction_basis_hash` matches persisted construction authority;
- exactly one reconciliation record exists for the constructed package set;
- exactly three output package rows exist for `canonical_internal`, `user_facing`, and `review_facing`;
- package ids, payload refs, and payload hashes match the persisted package rows;
- APS content document, chunks, material snapshot, analysis unit, analysis set, output payload hash, package candidate kinds, and construction basis still match preview and construction authority;
- no existing package-review submit state conflicts with the request.

Any missing, stale, malformed, mismatched, non-approved, duplicate-conflicting, or cross-session authority must fail closed before mutation.

## State Contract

Allowed state effects on successful submit:

- record exactly one qualitative APS package-review decision object in `L3ReconciliationRecord.summary_json`;
- optionally record session/operator summary pointer fields in `L3Session.summary_json`.

Forbidden state effects:

- create or mutate package rows or package payload files;
- create additional reconciliation rows;
- create handoff/export, APS dispatch, external export/download, connector, provider, delivery, signed-reference, auth, source-ingestion, RAG/vector, runtime snapshot, mockup, destination, plan, pass, run, or artifact state;
- create `AnalysisRun`;
- create or mutate source authority rows;
- alter qualitative execution output, result-review state, package-review preview state, package construction state, construction basis hash, output package ids, payload refs, or payload hashes;
- create replacement package-set, supersession, mutation, reconstruction, replacement artifact, or namespace state.

## Response Contract

Minimum response fields:

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
- `operator_decision`;
- `package_review_state`;
- `package_review_submit_enabled`;
- `handoff_enabled`;
- `aps_handoff_enabled`;
- `external_export_download_enabled`;
- `connector_dispatch_enabled`;
- `provider_public_url_enabled`;
- `downstream_unavailable`;
- `next_allowed_actions`.

`handoff_enabled`, `aps_handoff_enabled`, `external_export_download_enabled`, `connector_dispatch_enabled`, and `provider_public_url_enabled` must remain false in this tranche. `next_allowed_actions` must not include handoff/export or downstream delivery actions until a separate freeze admits them.

## Idempotency And Concurrency Contract

`client_request_id` is required.

Rules:

- duplicate `client_request_id` with the same submit basis returns the same decision state or an explicit already-submitted response;
- duplicate `client_request_id` with a different submit basis fails closed;
- a second request with a different `client_request_id` after a decision exists must fail closed unless the stored decision proves the same authority basis and same decision;
- concurrent duplicate submit attempts cannot create duplicate or divergent decision state;
- partial package-review decision state must fail closed.

The submit basis hash must include:

- request identity fields;
- package-review preview hash;
- construction basis hash;
- source document/material/unit/set authority;
- output payload ref/hash;
- result-review record ref;
- reconciliation record id;
- package ids;
- package kinds;
- payload refs and hashes;
- operator decision and decision notes.

## Failure Contract

The runtime must fail closed when:

- session, plan, preview hash, pass run, output metadata, result-review state, package-review preview state, construction state, reconciliation record, package rows, content document, chunks, material snapshot, analysis unit, or analysis set is missing;
- pass run is not qualitative APS document execution;
- result review is not approved;
- package-review preview hash or construction basis hash does not match server-derived authority;
- output payload hash/ref does not match result-review and package construction state;
- package ids, kinds, payload refs, or payload hashes differ from the frozen set;
- decision is invalid or required decision notes are missing;
- client provides document/source/package/downstream authority fields;
- existing package-review submit or downstream state conflicts with first submit semantics;
- request attempts source expansion, RAG/vector retrieval, local upload/directory ingestion, connector/destination dispatch, provider/public URL, handoff/export, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration changes, rendered UI changes, theme behavior, or auth/security behavior.

## Test Contract

Minimum implementation tests:

- one successful API submit after standalone APS qualitative package construction;
- bounded E2E reaches submit and stops before handoff/export;
- missing construction state fails closed;
- partial package set fails closed;
- non-approved result review fails closed;
- missing or stale package-review preview hash fails closed;
- stale construction basis hash fails closed;
- stale preview id/hash fails closed;
- stale output payload ref/hash fails closed;
- mismatched reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed;
- invalid decision and missing notes for `changes_requested`, `rejected`, or `blocked` fail closed;
- wrong engine family and wrong source shape fail closed;
- forbidden request fields fail closed before mutation;
- duplicate `client_request_id` same basis is deterministic;
- duplicate `client_request_id` different basis fails closed;
- concurrent duplicate requests do not create divergent decision state;
- no rows or files are created on success;
- payload refs, payload hashes, and package files remain unchanged;
- existing quantitative single-item and associated-cohort package submit behavior remains unchanged;
- no handoff/export, APS dispatch, external export/download, connector, provider/public URL, source, RAG/vector, model/migration, hidden LLM, full mockup, rendered UI, theme, or auth/security side effects;
- progress checker guard if needed;
- headed and headless Chrome proof only if rendered UI changes.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- handoff/export, APS dispatch, external export/download, connector/destination dispatch, or provider/public URL behavior;
- source expansion, ingestion, RAG/vector retrieval, or adapter registry behavior;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- package mutation/reconstruction, supersession, replacement artifact generation, or replacement namespace behavior;
- schema/model/migration changes;
- `L3OutputPackage.status` mutation;
- rendered UI controls or theme-visible behavior without a UI freeze and browser proof;
- auth/security behavior.
