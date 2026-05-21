# 937 - Source-Directory Package Supersession Rendered Proof

## Status

Status: branch-local implementation proof for `source_directory_package_replacement_supersession_rendered_path_after_hybrid_authority_sync`.

Doc: `937-source-supersession-proof.md`.

Predecessor current-main sync doc: `936-hybrid-authority-current-main-sync.md`.

Implementation branch: `codex/l3-source-supersession-proof`.

Base authority: `project6-origin/main` at `2c46c06c62d2b7359c7971b2b5e2c99007783ed2`.

## Implemented Boundary

This pass closes the source-directory package replacement/supersession proof gap named by doc `936`.

The rendered hybrid middle-lifecycle control now populates the existing source-directory package supersession preview authority after package-review submit. The focused rendered E2E then clicks the existing package supersession preview, replacement package-set authority, and package supersession commit controls in the same bounded source-directory path.

Backend authority remains server-owned:

- `source_directory_qualitative_analysis_package_supersession_preview` now recognizes a persisted hybrid package-commit reconciliation and derives preview authority from server-owned reconciliation/package rows instead of recomputing against the older non-hybrid qualitative hash.
- `source_directory_package_lifecycle_context` now accepts either the older source-directory qualitative package commit summary or the hybrid-context package commit summary, while preserving the same package lifecycle route contracts and response rails.
- Replacement authority and package supersession commit continue to derive source package set, downstream dependency, replacement, and commit hashes server-side.

## Proof

Passed validation in the implementation lane:

- `node --check ./backend/app/review_ui/static/layer3.js`
- `python -m pytest ./backend/tests/test_layer3_page.py -q` -> `16 passed`
- `python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py -q -k "supersession_preview or package_lifecycle_records_authority_and_commit"` -> `1 passed`
- `python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q -k "package_review_submit_records_bounded_authority or hybrid_package_lifecycle_records_replacement"` -> `2 passed`
- Headless Chromium focused E2E: `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` -> `1 passed`
- Headed Chromium focused E2E: `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` -> `1 passed`

The focused E2E asserts the package supersession preview, replacement package-set authority, and package supersession commit requests use narrow allowlisted payloads and avoid forbidden package mutation, connector, provider URL, browser-state, and frontend-durable authority fields.

## Non-Admission Boundary

This implementation does not add a model, migration, new package mutation route, package payload rewrite, source package row mutation, provider-private signed URL runtime, provider-public URL runtime, external object-store behavior, public proxy behavior, connector dispatch, destination write, caller-supplied webhook destination authority, source expansion, broader RAG/model/provider behavior, hidden LLM planning, auth/security expansion, browser-storage authority, frontend-only durable authority, or full mockup activation.

Frontend-only durable authority remains `false`.

Full mockup program activation remains `false`.

## Next Posture

Next exact posture: `publish_and_settle_source_directory_package_replacement_supersession_rendered_proof_pr`.

After merge and current-main sync, the next useful whole-path action is `record_bounded_trial_usable_checkpoint_after_source_directory_replacement_supersession_proof`, then run the final bounded readiness/runbook audit before any full mockup activation question.
