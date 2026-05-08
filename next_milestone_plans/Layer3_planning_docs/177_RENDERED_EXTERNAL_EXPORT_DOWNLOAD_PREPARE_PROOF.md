# Rendered External Export Download Prepare Proof

Status: live test-only rendered browser proof for `raw_mixed_rendered_external_export_download_prepare`.

This document records the implementation proof selected by `175_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE.md` and `176_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT.md`. It proves that the existing rendered `/review/layer3` workbench can continue from raw mixed rendered APS handoff dispatched authority through external export/download prepare by using existing rendered controls and the existing backend route.

This pass changes no production backend route, DTO, service, model, migration, rendered UI control, source handling, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or Layer 3 runtime behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-download-prepare-proof`
- selected rendered external export/download mode: `raw_mixed_rendered_external_export_download_prepare`
- frozen governing docs: `175_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE.md` and `176_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT.md`
- existing external export/download route reused: `POST /api/v1/layer3/handoff/export/download/prepare`
- existing request DTO reused: `Layer3ExternalExportDownloadPrepareRequest`
- existing response schema reused: `Layer3ExternalExportDownloadPrepareResponse`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- browser proof: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Proof Boundary

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered external export download prepare`

The reusable proof helper is:

- `submitRenderedExternalExportDownloadPrepare`

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
13. rendered APS handoff dispatch;
14. rendered external export/download prepare.

It stops after the external export/download prepare response records `external_export_download_prepared`. External export/download deliver, signed-reference generate/use, package mutation, package replacement, package supersession, provider URL generation, and connector/destination dispatch remain outside this proof.

## Request and Response Proof

The browser proof asserts that `/handoff/export/download/prepare` receives only admitted request fields, including the server-backed APS bundle identity, `aps_bundle_hash`, `aps_bundle_size_bytes`, `export_download_target: aps_evidence_bundle_download_reference`, `download_mode: reference_only_prepare`, and `operator_decision: prepare_external_export_download`.

The proof rejects deferred request fields such as `external_export`, `external_target`, `download`, `download_url`, `delivery`, `delivery_mode`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `dispatch`, `send`, `public_url`, `signed_url`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `package_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, and `schema_migration`.

The response proof checks:

- response schema `layer3.external_export_download_prepare.v1`;
- status `prepared`;
- matching session, plan, pass-run, preview, result-review, package-review, handoff/export, and APS handoff identities;
- external export/download state `external_export_download_prepared`;
- server-returned `external_export_download_record_ref`;
- server-returned `export_download_descriptor_ref`;
- `source_artifact_ref` matching the APS bundle ref;
- `source_artifact_hash` matching the request `aps_bundle_hash`;
- `source_artifact_size_bytes` matching the request `aps_bundle_size_bytes`;
- browser download, download URL, connector dispatch, destination selection, and generic downstream dispatch flags remain disabled;
- associated-cohort delivery UI readiness may be surfaced as next-step readiness only;
- provider/public URL, connector dispatch, direct download, signed-reference delivery, and package mutation remain outside the proof.

## Rendered State Proof

The proof uses existing selectors only:

- `[data-operation-target="external-export-download-band"]`
- `#external-export-download-prepare-submit`
- `#external-export-download-prepare-panel`

It verifies `external_export_download_ready` before submit and `external_export_download_prepared` after submit. It also verifies `#external-export-download-delivery-submit` as enabled after prepare while treating that only as next-step readiness. It does not click the delivery control, generate or use a signed reference, and it asserts no `/handoff/export/download/deliver` or `/handoff/export/download/signed-reference` request is made.

The proof distinguishes rendered controls from frontend-only durable authority. The external export/download prepare action is driven only after server-authoritative result-review, package-preview, package-construction, package-review-submit, handoff/export prepare, and APS handoff dispatch responses. The operation dock is not treated as durable authority.

## Theme and Browser Proof

The proof preserves the existing theme posture by passing through the upstream path:

- `light` around result/status and package preview;
- `dark` around execution/package construction;
- `workbench` around package-review submit, handoff/export prepare, APS handoff dispatch, and external export/download operation-dock navigation.

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
- external export/download deliver;
- signed-reference generation or use;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.

## Next Boundary

The next pass must not assume external export/download deliver, signed-reference generate/use, provider URL, connector/destination dispatch, package mutation, package replacement, or package supersession is proven for the raw mixed rendered path. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
