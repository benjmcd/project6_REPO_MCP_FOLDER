# 935 - Source-Directory Hybrid Authority Bridge Implementation

## Status

Status: branch-local implementation proof for `source_directory_hybrid_authority_generation_operator_bridge`.

Doc: `935-hybrid-authority-implementation.md`.

Predecessor freeze doc: `934-hybrid-authority.md`.

Implementation branch: `codex/l3-hybrid-authority-bridge`.

Current-main checkpoint before implementation: `d8a3cc3b6e723fb1b29adad34be0e9a2bb54da18`.

Selected route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare`.

Rendered control: `/review/layer3 #source-directory-hybrid-authority-prepare`.

## Implemented Boundary

This pass implements the server-owned Gate B/session/material snapshot to source-directory hybrid authority bridge selected by doc `934`.

The production route derives `index_authority_hash` and `embedding_index_authority_hash` from the admitted source-directory material snapshot by calling the existing text-index and embedding-vector-index owner services. The browser request carries only the current source-directory session and optional tuning fields; it does not supply index hashes, raw paths, payload refs, file bytes, provider URLs, connector destinations, webhook destinations, package payloads, or browser-storage authority.

The rendered `/review/layer3` control now prepares that authority through the production route, fills the existing middle-lifecycle authority textarea from the server response, and then continues through the already-live retrieval/context/qualitative-analysis/package/review/handoff/export/delivery/internal-webhook route chain.

## Proof

Passed validation in the implementation lane:

- `python -m py_compile ./backend/app/services/layer3_source_directory_hybrid_authority.py`
- `node --check ./backend/app/review_ui/static/layer3.js`
- `python -m pytest ./backend/tests/test_layer3_page.py -q` -> `16 passed`
- `python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q` -> `22 passed`
- Headless Chromium focused E2E: `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` -> `1 passed`
- Headed Chromium focused E2E: `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` -> `1 passed`

The focused E2E proof no longer calls `POST /__test/layer3/source-directory-hybrid-authority`; it clicks the rendered production prepare control and asserts the prepare request contains only `client_request_id` and `session_id`.

## Non-Admission Boundary

This implementation does not add a model, migration, durable frontend authority, browser localStorage/sessionStorage authority, provider-private signed URL runtime, provider-public URL runtime, external object-store behavior, public proxy behavior, connector dispatch, connector destination writes, caller-supplied webhook destination authority, package mutation, source expansion, broader RAG/model/provider behavior, hidden LLM planning, auth/security expansion, or full mockup activation.

Frontend-only durable authority remains `false`.

Full mockup program activation remains `false`.

## Next Posture

Next exact posture: `publish_and_settle_source_directory_hybrid_authority_generation_operator_bridge_pr`.

After the PR is merged and current main is synced, the next useful whole-path step is to record the clean bounded trial-usable checkpoint and minimal operator runbook, unless current-main evidence exposes an unresolved source-directory package replacement/supersession proof gap that should be closed first.
