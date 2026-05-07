# Layer 3 Qualitative APS Package Construction Contract

Status: implementation-entry contract paired with `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md`.

This contract defines the future API/state/proof shape for `qual_aps_package_construction_commit_entry`. It is not live runtime behavior. Current main still blocks qualitative APS package construction with `qualitative_aps_package_construction_commit_not_admitted` and package-review submit with `qualitative_aps_package_review_submit_not_admitted`.

## Authority Order

Qualitative APS package construction must resolve authority in this order:

1. live source and tests on `project6-origin/main`;
2. `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md`;
3. `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`;
4. qualitative execution governance in `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`;
5. qualitative hybrid/RAG boundary in `124_QUAL_HYBRID_RAG_FREEZE.md`;
6. `backend/app/services/layer3_qual_aps_execution.py` for qualitative output authority;
7. `backend/app/services/layer3_workbench.py` and `backend/app/services/layer3_workbench_package_state.py` for existing package state patterns;
8. `backend/tests/test_layer3_bounded_e2e.py` and `backend/tests/test_layer3_qual_aps_execution.py`;
9. request payload as operator intent only;
10. browser state as non-authoritative display/cache only.

Planning prose, browser state, raw document text, mockup state, PR titles, branch names, and client-provided package bytes are never sufficient package authority.

## Route Contract

Selected route:

- `POST /api/v1/layer3/package/review/commit`

Selected future response schema:

- `layer3.qual_aps_package_construction_commit.v1`

Route reuse is admitted because the existing package route family already separates preview, commit, and submit. The qualitative implementation must still distinguish its response schema and authority rail from quantitative package construction.

## Request Contract

Required fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- `package_review_preview_hash`
- `expected_package_kinds`

Conditionally allowed only if current-main result/status authority still exposes it:

- `analysis_run_id`, but it must be absent or null for qualitative APS execution because qualitative APS execution does not create `AnalysisRun`

`expected_package_kinds` must equal:

- `canonical_internal`
- `user_facing`
- `review_facing`

Forbidden request fields include:

- `dataset_version_id`;
- `content_id`, `material_snapshot_id`, `analysis_unit_id`, or `analysis_set_id` as client authority;
- raw document text or raw chunk text;
- local paths, provider paths, URLs, buckets, ACLs, signed URL fields, or public URL fields;
- package ids, reconciliation ids, package bytes, payload refs, payload hashes, replacement fields, supersession fields, mutation fields, or reconstruction fields;
- package-review submit decisions;
- handoff/export, APS dispatch, external export/download, connector, destination, provider, credential, source expansion, upload, directory, web connector, RAG/vector, adapter registry, runtime DB expansion, prompt, model, LLM, retry, recovery, rerun, cancel, auth, or mockup fields.

The server must derive source, document, unit, set, chunk, output, package, and payload authority from persisted state and server-owned artifacts.

## Admission Contract

An available qualitative APS package construction commit requires:

- current session exists and matches the request;
- approved analysis plan exists and matches `preview_id` and `preview_hash`;
- selected pass run exists for the same session and approved plan;
- pass run engine family is `qualitative_aps_document`;
- pass scope is `single_aps_doc_qualitative_pass`;
- selected pass is terminal with readable qualitative output metadata;
- output metadata binds to one APS content document and one server-owned qualitative output payload;
- result-review state exists, is approved, and matches the same session, plan, preview id/hash, pass run, output payload, and source document;
- package-review preview state is available and `package_review_preview_hash` matches the server-derived qualitative package preview basis;
- content document, chunks, material snapshot, analysis unit, analysis set, output payload hash, and package candidate kinds still match preview authority;
- no existing reconciliation/package/downstream state conflicts with first construction semantics.

Any missing, stale, malformed, mismatched, non-approved, duplicate-conflicting, or cross-session authority must fail closed before row or file mutation.

## State Contract

Allowed state effects on successful construction:

- create exactly one `L3ReconciliationRecord`;
- create exactly three `L3OutputPackage` rows;
- write exactly one package payload file per package row unless the implementation freezes a stricter shared-payload reference strategy;
- optionally record session/operator summary state needed for existing readiness projections.

Forbidden state effects:

- create or mutate package-review submit state;
- create handoff/export, APS dispatch, external export/download, connector, provider, delivery, signed-reference, auth, source-ingestion, RAG/vector, runtime snapshot, mockup, or destination state;
- create `AnalysisRun`;
- create or mutate source authority rows;
- alter qualitative execution output;
- alter result-review state;
- mutate existing package rows or package payload files;
- create replacement package-set, supersession, mutation, reconstruction, or namespace state.

## Package Contract

The qualitative APS package set has exactly three package kinds:

- `canonical_internal`
- `user_facing`
- `review_facing`

Each package row must preserve:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `package_kind`;
- package payload ref;
- package payload hash;
- source engine family;
- source document/content id;
- material snapshot id;
- analysis unit id;
- analysis set id;
- result-review record ref;
- package-review preview hash;
- construction basis hash.

Payloads must include enough authority for later review and downstream readiness without requiring browser state:

- qualitative output schema id and output hash;
- source content id and content contract ids;
- chunk ids, chunk ordinals, and chunk hashes;
- citation/trace references from the qualitative output;
- selected method and pass scope;
- negative capability flags for submit, handoff/export, APS dispatch, external export/download, connector/destination, provider URL, source expansion, RAG/vector, hidden LLM, mockup, UI, and auth/security behavior.

Payloads must not include credentials, local paths, provider URLs, raw prompts, model settings, mutable package-edit instructions, connector credentials, destination credentials, or browser-only state.

## Idempotency And Concurrency Contract

The implementation must provide deterministic duplicate behavior:

- duplicate `client_request_id` with the same construction basis returns the same constructed package set or an explicit already-committed response;
- duplicate `client_request_id` with a different construction basis fails closed;
- concurrent duplicate construction attempts cannot create duplicate reconciliation rows, duplicate package rows, or divergent payload files;
- package payload file writes must be atomic enough that partial files cannot become referenced package authority.

The construction basis hash must include:

- request identity fields;
- package-review preview hash;
- source document/material/unit/set authority;
- output payload ref/hash;
- result-review record ref;
- package kinds;
- generated payload hashes.

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
- `output_packages`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_commit_enabled`;
- `package_review_submit_enabled`;
- `handoff_enabled`;
- `aps_handoff_enabled`;
- `external_export_download_enabled`;
- `connector_dispatch_enabled`;
- `provider_public_url_enabled`;
- `downstream_unavailable`;
- `next_allowed_actions`.

`package_review_submit_enabled` and all downstream flags must remain false in this construction tranche.

## Failure Contract

The runtime must fail closed when:

- session, plan, preview hash, pass run, output metadata, result-review state, package-review preview state, content document, chunks, material snapshot, analysis unit, or analysis set is missing;
- pass run is not qualitative APS document execution;
- result review is not approved;
- package-review preview hash does not match server-derived preview authority;
- output payload hash/ref does not match result-review state;
- candidate package kinds differ from the frozen set;
- client provides document/source/package/downstream authority fields;
- existing package/reconciliation/downstream state conflicts with construction semantics;
- request attempts source expansion, RAG/vector retrieval, local upload/directory ingestion, connector/destination dispatch, provider/public URL, handoff/export, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration changes, rendered UI changes, or auth/security behavior.

## Test Contract

Minimum implementation tests:

- one successful API construction commit after approved standalone APS qualitative package-review preview;
- bounded E2E reaches construction commit and stops before submit;
- missing result review fails closed;
- non-approved result review fails closed;
- missing or stale package-review preview hash fails closed;
- stale preview id/hash fails closed;
- stale output payload ref/hash fails closed;
- mismatched content id, material snapshot id, analysis unit id, analysis set id, chunk ids, or chunk hashes fail closed;
- wrong engine family and wrong source shape fail closed;
- forbidden request fields fail closed before mutation;
- duplicate `client_request_id` same basis is deterministic;
- duplicate `client_request_id` different basis fails closed;
- concurrent duplicate requests do not create duplicate rows or files;
- exactly one reconciliation row and three package rows are created on success;
- payload refs exist and hashes match row metadata;
- existing quantitative single-item and associated-cohort package construction remains unchanged;
- package-review submit remains blocked for qualitative APS with `qualitative_aps_package_review_submit_not_admitted`;
- no handoff/export, APS dispatch, external export/download, connector, provider/public URL, source, RAG/vector, model/migration, hidden LLM, full mockup, rendered UI, theme, or auth/security side effects;
- progress checker guard if needed;
- headed and headless Chrome proof only if rendered UI changes.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- package-review submit;
- handoff/export, APS dispatch, external export/download, connector/destination dispatch, or provider/public URL behavior;
- source expansion, ingestion, RAG/vector retrieval, or adapter registry behavior;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- package mutation/reconstruction or supersession;
- schema/model/migration changes not already covered by existing package/reconciliation tables;
- rendered UI controls without a UI freeze and browser proof.
