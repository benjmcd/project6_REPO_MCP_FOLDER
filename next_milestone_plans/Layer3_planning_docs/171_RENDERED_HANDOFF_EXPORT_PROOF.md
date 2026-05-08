# Rendered Handoff Export Prepare Proof

Status: live test-only rendered browser proof for `raw_mixed_rendered_handoff_export_prepare`.

This document records the implementation proof selected by `169_RENDERED_HANDOFF_EXPORT_FREEZE.md` and `170_RENDERED_HANDOFF_EXPORT_CONTRACT.md`. It proves that the existing rendered `/review/layer3` workbench can continue from raw mixed rendered package-review authority through handoff/export prepare by using existing rendered controls and the existing backend route.

This pass changes no production backend route, DTO, service, model, migration, rendered UI control, source handling, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or Layer 3 runtime behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-handoff-proof`
- selected rendered handoff mode: `raw_mixed_rendered_handoff_export_prepare`
- frozen governing docs: `169_RENDERED_HANDOFF_EXPORT_FREEZE.md` and `170_RENDERED_HANDOFF_EXPORT_CONTRACT.md`
- existing handoff route reused: `POST /api/v1/layer3/handoff/export/prepare`
- existing request DTO reused: `Layer3HandoffExportPrepareRequest`
- existing response schema reused: `Layer3HandoffExportPrepareResponse`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- browser proof: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Proof Boundary

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered handoff export prepare`

The reusable proof helper is:

- `submitRenderedHandoffExportPrepare`

The proof drives the already-live raw mixed rendered path through:

1. rendered raw mixed materialization;
2. rendered material preview;
3. rendered Gate B decision;
4. rendered Gate C preview and commit;
5. rendered plan preview and approval;
6. rendered execution selection and start;
7. rendered result/status inspection;
8. rendered approved result-review submit;
9. rendered package-review preview inspection;
10. rendered package construction commit;
11. rendered package-review submit;
12. rendered handoff/export prepare.

It stops after the handoff/export prepare response records `handoff_export_prepared`. APS handoff dispatch, external export/download prepare, external export/download deliver, package mutation, package replacement, package supersession, provider URL generation, and connector/destination dispatch remain outside this proof.

## Request and Response Proof

The browser proof asserts that `/handoff/export/prepare` receives only admitted request fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `analysis_run_id`
- `result_review_record_ref`
- `package_review_preview_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_refs`
- `payload_hashes`
- `package_review_submit_record_ref`
- `package_review_state`
- `package_review_submit_schema_id`
- `handoff_target`
- `export_mode`
- `operator_decision`
- `decision_notes`
- `expected_package_kinds`

The proof rejects deferred request fields such as `aps_handoff`, `dispatch`, `send`, `external_export`, `external_target`, `download`, `connector_run_id`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `package_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, and `schema_migration`.

The response proof checks:

- response schema `layer3.cohort_handoff_export_prepare.v1`;
- status `prepared`;
- matching `session_id`, `analysis_plan_id`, `pass_run_id`, `preview_id`, and `preview_hash`;
- matching `analysis_run_id`;
- matching `result_review_record_ref`;
- matching `package_review_preview_hash`;
- matching `reconciliation_record_id`;
- three package ids;
- package kinds `canonical_internal`, `user_facing`, and `review_facing`;
- three payload refs;
- three payload hashes;
- matching package-review submit schema and submit ref;
- package-review state `package_review_approved`;
- operator decision `authorize_prepare`;
- handoff/export state `handoff_export_prepared`;
- handoff target `internal_export_envelope`;
- export mode `prepare_only`;
- server-returned `prepare_record_ref`;
- server-returned `handoff_export_envelope`;
- provider/public URL, connector dispatch, external export, external export/download, and package mutation flags remain disabled.

## Rendered State Proof

The proof uses existing selectors only:

- `[data-operation-target="handoff-export-band"]`
- `#handoff-export-prepare-decision`
- `#handoff-export-prepare-notes`
- `#handoff-export-prepare-submit`
- `#handoff-export-prepare-panel`

It verifies the notes-required branch by selecting `hold`, observing submit disabled without notes, switching back to `authorize_prepare`, filling notes, and submitting. It verifies `handoff_export_ready` before submit and `handoff_export_prepared` after submit.

The current rendered workbench surfaces `#aps-handoff-dispatch-submit` as enabled after handoff/export prepare. This proof treats that as next-step readiness only: it does not click the APS dispatch control, and it asserts no `/handoff/aps/dispatch` request is made. It also asserts no `/handoff/export/download` request is made.

The proof distinguishes rendered controls from frontend-only durable authority. The handoff/export prepare action is driven only after server-authoritative result-review, package-preview, package-construction, and package-review-submit responses. The operation dock is not treated as durable authority.

## Theme and Browser Proof

The proof preserves the existing theme posture by passing through the upstream path:

- `light` around result/status and package preview;
- `dark` around execution/package construction;
- `workbench` around package-review submit and handoff/export prepare operation-dock navigation.

Because the Playwright harness uses fixed port `8031`, headed and headless proof runs must remain sequential unless a later freeze implements isolated ports/state.

## Negative Invariants

This proof admits no:

- production backend route, DTO, service, model, or migration change;
- rendered UI control change;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- APS handoff dispatch request execution;
- external export/download prepare or deliver;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.

## Next Boundary

The next pass must not assume APS dispatch, external export/download prepare, external export/download deliver, provider URL, connector/destination dispatch, package mutation, package replacement, or package supersession is proven for the raw mixed rendered path. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
