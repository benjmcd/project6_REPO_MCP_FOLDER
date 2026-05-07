# Layer 3 Qualitative APS Package-Review Contract

Status: current runtime contract paired with `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md`.

This contract defines the API/state/proof shape for the live `qual_aps_package_review_preview_only` implementation. It admits only read-only package-review preview for one approved standalone APS content-document qualitative result. Package construction is admitted only by the separate docs `140`/`141` runtime boundary. This contract does not admit package-review submit, handoff/export, APS dispatch, external export/download, connector/destination dispatch, provider/public URLs, source expansion, broad qualitative/hybrid/RAG behavior, rendered controls, model/migration changes, hidden LLM planning, full mockup activation, or authentication/security behavior.

## Authority Order

Qualitative APS package-review preview must resolve authority in this order:

1. live source and tests on `project6-origin/main`;
2. `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md`;
3. existing qualitative execution governance in `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`, and `124_QUAL_HYBRID_RAG_FREEZE.md`;
4. `backend/app/services/layer3_qual_aps_execution.py` for qualitative execution output authority;
5. `backend/app/services/layer3_workbench.py` for API flow state, result/status, result-review, read-only qualitative package-preview authority, and downstream fail-closed behavior;
6. `backend/app/services/layer3_workbench_package_state.py` for existing package-preview candidate vocabulary and downstream-unavailable patterns;
7. `backend/tests/test_layer3_bounded_e2e.py` and `backend/tests/test_layer3_qual_aps_execution.py`;
8. request payload as operator intent only;
9. browser state as non-authoritative display/cache only.

Mockups, browser-visible state, planning prose, PR titles, branch names, or copied qualitative output text are never sufficient package authority.

## Route Decision

Live route target:

- `POST /api/v1/layer3/package/review/preview`

Route reuse is admitted because the existing request/response envelope now distinguishes:

- wrapped quantitative single-item preview;
- associated-cohort descriptive-summary preview;
- standalone APS content-document qualitative preview.

No separate qualitative preview route is admitted in this boundary.

## Request Contract

Allowed request fields for the default route:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- `client_request_id`

Conditionally allowed only if current-main status/result authority still exposes it:

- `analysis_run_id`, but it must be absent or null for qualitative APS execution because current qualitative APS execution does not create `AnalysisRun`

Forbidden request fields include:

- `dataset_version_id`
- `content_id` as client authority
- `material_snapshot_id` as client authority
- `analysis_unit_id` as client authority
- `analysis_set_id` as client authority
- raw document text
- raw chunk text
- local paths
- provider paths, URLs, buckets, ACLs, signed URL fields, or public URL fields
- package ids, package kinds, package bytes, payload refs, payload hashes, replacement package fields, supersession fields, mutation fields, or reconstruction fields
- package-review submit decisions
- handoff/export fields
- APS dispatch fields
- external export/download fields
- connector ids, destination ids, connector credentials, or provider credentials
- source expansion, local upload, local-directory, web connector, RAG/vector, adapter registry, or runtime DB expansion fields
- prompt, model, LLM, temperature, tool, retry, recovery, rerun, cancel, auth, or mockup flags

The server must derive source, document, unit, set, chunk, output, and package-compatibility authority from persisted Layer 3 and APS state.

## Admission Contract

An available qualitative APS package-review preview requires:

- current session exists and matches the request;
- approved analysis plan exists and matches `preview_id` and `preview_hash`;
- selected pass run exists for the same session and approved plan;
- pass run engine family is `qualitative_aps_document`;
- pass scope/method is `single_aps_doc_qualitative_pass`;
- selected pass is terminal with readable qualitative output metadata;
- output metadata binds to one APS content document and the server-owned execution output payload;
- result-review state exists, is approved, and matches the same session, plan, preview id/hash, pass run, output payload, and source document;
- content document, chunks, material snapshot, analysis unit, and analysis set still match the output authority;
- no existing package/reconciliation/downstream state makes preview ambiguous.

Any missing, stale, malformed, mismatched, non-approved, or cross-session authority must fail closed before row or file mutation.

## Response Contract

Minimum response fields:

- `schema_id`, preferably `layer3.qual_aps_package_review_preview.v1` if the existing schema cannot safely distinguish qualitative output;
- `status`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_identity`;
- `result_review_record_ref`;
- `engine_family`;
- `pass_scope`;
- `method`;
- `source_shape`;
- `content_id`;
- `content_contract_id`;
- `chunking_contract_id`;
- `material_snapshot_id`;
- `analysis_unit_id`;
- `analysis_set_id`;
- `output_payload_ref`;
- `output_payload_hash`;
- `candidate_package_kinds`;
- `package_review_preview_hash` or equivalent deterministic preview-basis hash;
- `package_review_preview_enabled`;
- `package_commit_enabled`;
- `package_review_submit_enabled`;
- `handoff_enabled`;
- `aps_handoff_enabled`;
- `external_export_download_enabled`;
- `connector_dispatch_enabled`;
- `provider_public_url_enabled`;
- `downstream_unavailable`;
- `blocked_reasons` when unavailable.

The response must not include package ids, reconciliation ids, package payload refs, handoff refs, dispatch refs, delivery refs, provider URLs, connector refs, local paths, raw prompts, credentials, package bytes, editable payloads, or browser-only authority.

## State Contract

Allowed state effects:

- read existing Layer 3 and APS state;
- compute response-safe preview/readiness data;
- optionally record deterministic preview metadata only if implementation explicitly freezes it as non-constructive and proves no package/downstream side effects.

Forbidden state effects:

- create or mutate `L3OutputPackage`;
- create or mutate `L3ReconciliationRecord`;
- create or mutate `AnalysisRun`;
- create or mutate source authority rows;
- create package payload files;
- create handoff/export, APS dispatch, external export/download, connector, provider, delivery, signed-reference, auth, source-ingestion, RAG/vector, or runtime snapshot state;
- alter qualitative execution output;
- alter result-review state.

## Compatibility Contract

The preview may use candidate package descriptors only. The first candidate vocabulary is:

- `canonical_internal`
- `user_facing`
- `review_facing`

Those names are preview descriptors until the separate package-construction boundary creates qualitative APS package rows and payloads. The preview itself must not imply those packages already exist.

The compatibility projection must decide, at minimum:

- whether qualitative APS output has enough response-safe result/citation/trace data to become packageable later;
- whether chunk/citation trace is complete or degraded;
- whether package construction is blocked by missing qualitative package taxonomy;
- whether handoff/export remains blocked due to absent package construction.

## UI And Theme Contract

This contract does not admit UI work.

If a later implementation changes `/review/layer3`, it must:

- use server-provided preview/readiness only;
- keep package construction, submit, handoff/export, APS dispatch, external export/download, connector, provider URL, source expansion, RAG/vector, and auth/security controls absent or disabled;
- not add raw manifest upload, directory picker, raw document text entry, model/prompt controls, package editor, package mutation controls, or destination controls;
- preserve existing workbench theme behavior;
- prove the changed rendered path in headless and headed Chrome, including relevant theme checks.

## Failure Contract

The runtime must fail closed when:

- session, plan, preview hash, pass run, output metadata, result-review state, content document, chunks, material snapshot, analysis unit, or analysis set is missing;
- pass run is not qualitative APS document execution;
- result review is not approved;
- output payload hash/ref does not match result-review state;
- client provides document/source/package/downstream authority fields;
- qualitative output cannot be converted into response-safe package-preview descriptors;
- existing package/reconciliation/downstream state conflicts with preview-only semantics;
- request attempts source expansion, RAG/vector retrieval, local upload/directory ingestion, connector/destination dispatch, provider/public URL, handoff/export, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration changes, or auth/security behavior.

## Test Contract

Minimum implementation tests:

- one success path for approved standalone APS qualitative result-review preview;
- missing approved result review fails closed;
- wrong engine family fails closed without changing quantitative behavior;
- stale preview id/hash fails closed;
- stale output payload ref/hash fails closed;
- mismatched content id, material snapshot id, analysis unit id, or analysis set id fails closed;
- forbidden request fields fail closed before mutation;
- existing quantitative single-item package preview remains unchanged;
- existing associated-cohort package preview remains unchanged;
- standalone APS qualitative E2E reaches read-only package preview and then the separate package-construction commit boundary;
- package-review submit is admitted only by the separate docs `143`/`144` boundary after construction authority exists;
- no package, reconciliation, handoff/export, APS dispatch, external export/download, connector, provider/public URL, source, RAG/vector, model/migration, or auth/security side effects;
- progress checker guard if needed;
- headed and headless Chrome proof if UI changes.

## Implementation Stop Conditions

Stop and return to planning if implementation would require:

- package construction;
- package-review submit;
- package payload writes;
- package mutation/reconstruction;
- handoff/export, APS dispatch, external export/download, connector/destination dispatch, or provider/public URL behavior;
- source expansion, ingestion, RAG/vector retrieval, or adapter registry behavior;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, or prompt/model behavior;
- schema/model/migration changes not separately frozen;
- rendered UI controls without a UI freeze and browser proof.
