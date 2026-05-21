# 934 - Source-Directory Hybrid Authority Bridge Freeze

## Status

Status: no-runtime/no-rendered contract freeze for `source_directory_hybrid_authority_generation_operator_bridge`.

Doc: `934-hybrid-authority.md`.

Predecessor checkpoint doc: `933-trial-runbook.md`.

Current-main checkpoint before freeze: `f4a75bb5ebc3b4f4f03247db54f61383d208f164`.

Freeze branch: `codex/l3-hybrid-authority-freeze`.

Current-main predecessor implementation: PR `#1558`, merge commit `f4a75bb5ebc3b4f4f03247db54f61383d208f164`.

Originating posture: `freeze_source_directory_hybrid_authority_generation_operator_bridge_before_runtime`.

Selected bridge: `source_directory_hybrid_authority_generation_operator_bridge`.

Selected production route contract: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare`.

Selected rendered control contract: `/review/layer3` derives the middle-lifecycle authority payload from current server-owned Gate B/session/material authority instead of accepting test-helper or browser-authored index authority.

Selected immediate implementation slice after this freeze lands: `implement_source_directory_hybrid_authority_generation_operator_bridge`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Frontend-only durable authority enabled by this freeze: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed by this freeze alone before merge/current-main adoption: `false`.

Implementation-entry allowed after this freeze is current-main authority: `true`, only for `source_directory_hybrid_authority_generation_operator_bridge`.

## Canonical Source Of Truth

The canonical source of truth is current `project6-origin/main` at `f4a75bb5ebc3b4f4f03247db54f61383d208f164`.

Current main has the rendered source-directory middle lifecycle control from PR `#1558`. That control sequences the existing production routes for vector retrieval, hybrid context packet, qualitative analysis/status, package commit, package review submit, handoff/export prepare, and external export/download prepare from a supplied source-directory hybrid authority payload.

Current main also has the production source-directory scan/status/material preview routes and the generic Gate B admission route. The remaining interruption is between the rendered Gate B/session/material state and the first rendered middle-lifecycle submit. The current proof still obtains `index_authority_hash` and `embedding_index_authority_hash` from the test-only route `POST /__test/layer3/source-directory-hybrid-authority`.

The production owner services already exist:

- `backend/app/services/layer3_source_directory_text_index.py` owns `source_directory_material_text_index`.
- `backend/app/services/layer3_source_directory_vector_index.py` owns `source_directory_material_embedding_vector_index`.
- `backend/app/services/layer3_source_directory_material_admission.py` owns source-directory material preview and Gate B decision-basis validation.
- `backend/app/api/layer3.py` owns the production source-directory scan/status/material preview and middle lifecycle route family.

Therefore the bridge must be server-owned and production-routed. The browser must not compute, persist, or translate the index authority hashes.

## Proven Gap

Current proof path:

1. rendered source-directory scan/status/material preview and Gate B admission produce a server-owned session and material snapshot;
2. test-only `POST /__test/layer3/source-directory-hybrid-authority` reloads the source-directory material snapshot and calls the text-index and vector-index services;
3. the test-only response returns `authority_payload` with `index_authority_hash` and `embedding_index_authority_hash`;
4. Playwright pastes that payload into `/review/layer3 #source-directory-hybrid-middle-lifecycle-authority`;
5. the rendered middle lifecycle then uses production routes.

That proves the middle lifecycle route chain is production-routed after authority setup, but it does not yet prove a fully operator-continuous production path from Gate B to hybrid authority generation. A production user would still need a server-derived authority payload that the current production UI cannot prepare.

## Selected Contract

The next implementation pass must add a production bridge with this exact contract boundary:

- route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare`;
- request fields: `client_request_id`, `session_id`, optional `material_snapshot_id`, optional `analysis_question`, optional `analysis_focus`, optional `query_text`, optional `top_k`, optional `limit`, and optional `offset`;
- request must reject caller-supplied `index_authority_hash`, `embedding_index_authority_hash`, `absolute_path`, `payload_ref`, `raw_payload`, `file_bytes`, provider URL, webhook destination, connector destination, package payload, or browser-storage authority fields;
- server must resolve the current source-directory material snapshot from the supplied session and optional material snapshot id;
- server must require the snapshot to be owned by the same session, have `source_shape == "server_configured_directory_file"`, and point to the persisted `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`;
- server must reuse `source_directory_material_text_index` and `source_directory_material_embedding_vector_index` to compute the text and embedding index authority hashes from current persisted and live-file authority;
- server must fail closed if the session has no admitted source-directory material snapshot, has multiple ambiguous source-directory material snapshots without an explicit `material_snapshot_id`, has stale persisted/live file authority, has missing payload authority, or has a mismatched source ingestion batch/file identity;
- response schema must be `layer3.source_directory_hybrid_authority_prepare.v1`;
- response must include only the middle lifecycle authority fields needed by `/review/layer3`: `material_snapshot_id`, `source_ingestion_batch_id`, `source_ingestion_file_id`, `content_sha256`, `file_identity_hash`, `authority_basis_hash`, `payload_hash`, `index_authority_hash`, `embedding_index_authority_hash`, `query_text`, `top_k`, `limit`, `offset`, `analysis_question`, and `analysis_focus`;
- response must also include redaction/guard metadata proving no absolute path, raw payload ref, file bytes, provider URL, connector destination, webhook destination, package payload, or frontend-only durable authority was admitted;
- idempotency must be governed by `client_request_id` and server-derived authority basis, not by browser-authored durable state.

The rendered UI implementation after the route lands must add a narrow prepare control or wire the existing source-directory workflow so the middle-lifecycle textarea is populated only by this production response. The existing manual textarea may remain as an inspection surface, but the operator proof must no longer depend on `POST /__test/layer3/source-directory-hybrid-authority`.

## Non-Admission Boundary

This freeze introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, source expansion, broader RAG/model/provider behavior, provider-private signed URL runtime, provider-public URL runtime, external object-store behavior, public proxy behavior, connector dispatch, connector destination writes, caller-supplied webhook destination authority, package mutation, package replacement/supersession widening beyond the already-admitted middle lifecycle, raw local path exposure, file-byte exposure, browser localStorage/sessionStorage authority, frontend-only durable authority, hidden LLM planning, auth/security expansion, or full mockup program activation.

## Required Future Proof

The implementation pass must prove:

1. backend API tests for successful source-directory hybrid authority prepare from a Gate B admitted session;
2. backend API tests for fail-closed missing session, no material snapshot, multiple ambiguous snapshots, stale live file, mismatched material snapshot/session, and caller-supplied forbidden authority fields;
3. static JS check for `/review/layer3`;
4. focused rendered tests proving the UI calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare`;
5. focused E2E proof that no page or test request calls `POST /__test/layer3/source-directory-hybrid-authority` in the bounded operator path;
6. headed and headless Chromium parity for the scan/status/material preview/Gate B to hybrid middle lifecycle path;
7. request allowlist proof for the source-directory path;
8. forbidden payload-key proof for absolute paths, raw payload refs, file bytes, provider URLs, connector destinations, webhook destinations, package payloads, and browser-storage authority;
9. `python ./tools/l3-progress-check.py`, JSON validation, and `git diff --check`.

No validate-only action may seed, generate, or mutate runtime artifacts. Verification must use isolated runtime state wherever possible.

## Future Step Map

Immediate next pass after this freeze lands:

1. Implement `source_directory_hybrid_authority_generation_operator_bridge` behind the selected production route.
2. Add focused backend route/service tests proving success, stale-authority rejection, ambiguity rejection, forbidden-field rejection, and redaction.
3. Wire `/review/layer3` so the rendered operator path prepares hybrid authority from server-owned Gate B/session/material state.
4. Replace the Playwright test-helper authority setup with the production route/control and prove headed/headless parity.

Next bounded operator-path passes:

1. Re-prove source-directory scan/status/material preview/Gate B through retrieval/context/qualitative analysis/package lifecycle/handoff/export/delivery/internal webhook without the test-only authority bridge.
2. Re-audit source-directory package replacement/supersession coverage and close any remaining rendered-control or proof gap that current main admits.
3. Record the clean bounded trial-usable checkpoint and minimal operator runbook only after the uninterrupted production authority bridge is proven.
4. Extend Analysis Environment/mockup projection only as live-state evidence, read-only classification, intentional exclusion, or explicit blocker status.

Whole-program remaining passes:

1. Provider-private signed URL runtime admission, if selected by current main.
2. Provider-public URL runtime admission, if selected by current main.
3. Broader source/RAG/model/provider behavior, if selected by current main.
4. Auth/security expansion and operator hardening, if selected by current main.
5. Observability/performance and headed/headless regression gates for the bounded path.
6. Final full mockup readiness audit.
7. Full mockup activation only if every critical mockup operator journey is live, read-only, intentionally excluded, or explicitly blocked by current-main evidence.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is current main clean enough to select new work? | Yes. The freeze branch started from `project6-origin/main` at `f4a75bb5ebc3b4f4f03247db54f61383d208f164`, and no open PRs were reported before this pass. |
| Is the middle lifecycle itself still branch-local? | No. PR `#1558` is merged at `f4a75bb5ebc3b4f4f03247db54f61383d208f164`; the remaining branch-local description is stale ledger wording to be superseded by this freeze. |
| Is the next useful work another broad plan? | No. The narrow next work is the production Gate B to hybrid-authority bridge because current source shows the missing piece is a route/control contract, not a new conceptual roadmap. |
| Can the browser safely compute or carry the index authority? | No. The text/vector authority belongs to backend owner services and must be regenerated from persisted source-directory authority plus live-file verification. |
| Should the production bridge accept caller-supplied index hashes? | No. It must reject those fields and return server-derived hashes. |
| Does this freeze activate provider URLs, connector dispatch, package mutation, auth/security, or the full mockup? | No. Those remain separate current-main gates. |

## Next Posture

Next exact posture: `implement_source_directory_hybrid_authority_generation_operator_bridge`.

Do not activate full mockup behavior, frontend-only durable authority, provider URL runtime, connector dispatch, or broader source/RAG/model/provider behavior in the implementation pass. The only admitted implementation target after this freeze is the production server-owned Gate B/session/material snapshot to source-directory hybrid authority bridge.
