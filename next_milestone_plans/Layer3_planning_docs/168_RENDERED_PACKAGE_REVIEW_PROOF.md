# Rendered Package Review Proof

Status: live test-only rendered browser proof for `raw_mixed_rendered_package_review_preview_commit_submit`.

This document records the implementation proof selected by `166_RENDERED_PACKAGE_REVIEW_FREEZE.md` and `167_RENDERED_PACKAGE_REVIEW_CONTRACT.md`. It proves that the existing rendered `/review/layer3` workbench can continue from raw mixed rendered execution result/status authority through an approved result review and then through package-review preview, package construction commit, and package-review submit by using existing rendered controls and existing backend routes.

This pass changes no production backend route, DTO, service, model, migration, rendered UI control, source handling, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or Layer 3 runtime behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-package-proof`
- selected rendered package-review mode: `raw_mixed_rendered_package_review_preview_commit_submit`
- frozen governing docs: `166_RENDERED_PACKAGE_REVIEW_FREEZE.md` and `167_RENDERED_PACKAGE_REVIEW_CONTRACT.md`
- existing package-preview route reused: `POST /api/v1/layer3/package/review/preview`
- existing package-construction route reused: `POST /api/v1/layer3/package/review/commit`
- existing package-review submit route reused: `POST /api/v1/layer3/package/review/submit`
- existing request DTOs reused: `Layer3PackageReviewPreviewRequest`, `Layer3PackageConstructionCommitRequest`, and `Layer3PackageReviewSubmitRequest`
- existing response schemas reused: `layer3.package_review_preview.v1`, `layer3.package_construction_commit.v1`, and `layer3.cohort_package_review_submit.v1`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- browser proof: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Proof Boundary

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered package-review preview commit and submit`

The reusable proof helpers are:

- `inspectRenderedPackagePreview`
- `commitRenderedPackageConstruction`
- `submitRenderedPackageReview`

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
11. rendered package-review submit.

It stops after the package-review response records `package_review_approved`. Handoff/export prepare, APS handoff dispatch, external export/download prepare, external export/download deliver, package mutation, package replacement, package supersession, provider URL generation, and connector/destination dispatch remain outside this proof.

## Request and Response Proof

The browser proof asserts that `/package/review/preview` receives only admitted request fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `analysis_run_id`
- `result_review_record_ref`

The browser proof asserts that `/package/review/commit` receives only admitted request fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `analysis_run_id`
- `result_review_record_ref`
- `package_review_preview_hash`
- `expected_package_kinds`

The browser proof asserts that `/package/review/submit` receives only admitted request fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `analysis_run_id`
- `result_review_record_ref`
- `package_review_preview_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_refs`
- `payload_hashes`
- `operator_decision`
- `decision_notes`
- `expected_package_kinds`

The proof rejects deferred request fields such as `handoff`, `export`, `aps_handoff`, `create_package`, `rebuild_package`, `package_payload`, `rewrite_output`, `result_review_amendment`, local upload/local-directory fields, provider/public URL fields, RAG/vector fields, connector/destination fields, package mutation fields, hidden LLM fields, mockup fields, and auth/security fields.

The response proof checks:

- package preview schema `layer3.package_review_preview.v1`;
- package construction schema `layer3.package_construction_commit.v1`;
- package submit schema `layer3.cohort_package_review_submit.v1`;
- matching `session_id`, `analysis_plan_id`, `pass_run_id`, `preview_id`, and `preview_hash`;
- matching `analysis_run_id`;
- matching `result_review_record_ref`;
- server-returned `package_review_preview_hash`;
- server-returned `reconciliation_record_id`;
- three package ids;
- package kinds `canonical_internal`, `user_facing`, and `review_facing`;
- three payload refs;
- three payload hashes;
- package-review submit state `package_review_approved`;
- server-returned `submit_record_ref`;
- no provider/public URL, connector dispatch, APS handoff, or external export/download capability is enabled by the package-review submit response.

The current cohort package submit response may leave `construction_basis_hash` null even though the rendered request submits the construction hash. The proof therefore asserts the request hash strictly and treats the response field as nullable current-main behavior, not as package-review authority.

## Rendered State Proof

The proof uses existing selectors only:

- `#package-review-preview-inspect`
- `#package-construction-commit`
- `#package-review-submit-decision`
- `#package-review-submit-notes`
- `#package-review-submit`
- `#package-review-preview-panel`
- `[data-operation-target="package-review-band"]`

It verifies `package_review_preview_available`, `package_review_preview_ready`, `package_review_submit_ready`, and `package_review_approved` in the rendered package-review panel. It also verifies the package-review notes-required branch by selecting `changes_requested`, observing submit disabled without notes, switching back to `approved`, filling notes, and submitting.

The proof distinguishes rendered controls from frontend-only durable authority. The package-review action buttons are driven only after server-authoritative result-review, package-preview, and package-construction responses. The side-step chip is not treated as durable authority.

## Theme and Browser Proof

The proof preserves the existing theme posture by passing through:

- `light` around package-review preview;
- `dark` around package construction commit;
- `workbench` around package-review submit.

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
- handoff/export prepare;
- APS handoff dispatch;
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

The next pass must not assume handoff/export prepare, APS dispatch, external export/download prepare, external export/download deliver, provider URL, connector/destination dispatch, package mutation, package replacement, or package supersession is proven for the raw mixed rendered path. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
