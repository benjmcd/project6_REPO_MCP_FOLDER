# Rendered APS Handoff Dispatch Proof

Status: live test-only rendered browser proof for `raw_mixed_rendered_aps_handoff_dispatch`.

This document records the implementation proof selected by `172_RENDERED_APS_HANDOFF_FREEZE.md` and `173_RENDERED_APS_HANDOFF_CONTRACT.md`. It proves that the existing rendered `/review/layer3` workbench can continue from raw mixed rendered handoff/export prepared authority through APS handoff dispatch by using existing rendered controls and the existing backend route.

This pass changes no production backend route, DTO, service, model, migration, rendered UI control, source handling, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or Layer 3 runtime behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-aps-proof`
- selected rendered APS handoff mode: `raw_mixed_rendered_aps_handoff_dispatch`
- frozen governing docs: `172_RENDERED_APS_HANDOFF_FREEZE.md` and `173_RENDERED_APS_HANDOFF_CONTRACT.md`
- existing APS handoff route reused: `POST /api/v1/layer3/handoff/aps/dispatch`
- existing request DTO reused: `Layer3ApsHandoffDispatchRequest`
- existing response schema reused: `Layer3ApsHandoffDispatchResponse`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- browser proof: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Proof Boundary

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered APS handoff dispatch`

The reusable proof helper is:

- `submitRenderedApsHandoffDispatch`

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
12. rendered handoff/export prepare;
13. rendered APS handoff dispatch.

It stops after the APS handoff dispatch response records `aps_handoff_dispatched`. External export/download prepare, external export/download deliver, package mutation, package replacement, package supersession, provider URL generation, and connector/destination dispatch remain outside this proof.

## Request and Response Proof

The browser proof asserts that `/handoff/aps/dispatch` receives only admitted request fields:

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
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- `package_review_submit_record_ref`
- `package_review_state`
- `prepare_record_ref`
- `handoff_export_state`
- `handoff_export_envelope_ref`
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- `operator_decision`

The proof rejects deferred request fields such as `external_export`, `external_target`, `download`, `download_url`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `dispatch`, `send`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `package_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, and `schema_migration`.

The response proof checks:

- response schema `layer3.aps_handoff_dispatch.v1`;
- status `dispatched`;
- matching `session_id`, `analysis_plan_id`, `pass_run_id`, `preview_id`, and `preview_hash`;
- matching `analysis_run_id`;
- matching `result_review_record_ref`;
- matching `package_review_preview_hash`;
- matching `reconciliation_record_id`;
- three package ids;
- package kinds `canonical_internal`, `user_facing`, and `review_facing`;
- three payload refs;
- three payload hashes;
- matching package-review submit ref;
- package-review state `package_review_approved`;
- matching handoff/export `prepare_record_ref`;
- handoff/export state `handoff_export_prepared`;
- matching `handoff_export_envelope_ref`;
- handoff target `internal_export_envelope`;
- export mode `prepare_only`;
- APS target `aps_evidence_bundle`;
- dispatch mode `server_side_aps_handoff`;
- operator decision `dispatch_aps_handoff`;
- APS handoff state `aps_handoff_dispatched`;
- server-returned `aps_handoff_record_ref`;
- server-returned `aps_bundle_ref`;
- server-returned `aps_bundle_id`;
- server-returned `aps_schema_id`;
- provider/public URL, connector dispatch, external export, direct download, and package mutation flags remain disabled.

## Rendered State Proof

The proof uses existing selectors only:

- `[data-operation-target="aps-handoff-band"]`
- `#aps-handoff-dispatch-submit`
- `#aps-handoff-dispatch-panel`

It verifies `aps_handoff_ready` before submit and `aps_handoff_dispatched` after submit. It also verifies `#external-export-download-prepare-submit` as enabled after dispatch while treating that only as next-step readiness. It does not click the external export/download prepare control, and it asserts no `/handoff/export/download` request is made.

The proof distinguishes rendered controls from frontend-only durable authority. The APS handoff dispatch action is driven only after server-authoritative result-review, package-preview, package-construction, package-review-submit, and handoff/export prepare responses. The operation dock is not treated as durable authority.

## Theme and Browser Proof

The proof preserves the existing theme posture by passing through the upstream path:

- `light` around result/status and package preview;
- `dark` around execution/package construction;
- `workbench` around package-review submit, handoff/export prepare, and APS handoff dispatch operation-dock navigation.

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

The next pass must not assume external export/download prepare, external export/download deliver, provider URL, connector/destination dispatch, package mutation, package replacement, or package supersession is proven for the raw mixed rendered path. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
