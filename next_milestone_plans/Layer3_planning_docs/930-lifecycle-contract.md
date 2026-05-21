# 930 - Source-Directory Package Lifecycle Contract Freeze

## Status

Status: no-runtime/no-rendered route-state contract freeze for `source_directory_package_lifecycle_server_owned_contract`.

Doc: `930-lifecycle-contract.md`.

Predecessor current-main sync doc: `929_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before contract freeze: `4448adf6ea168abde8346c1601ab3be52d570dbf`.

Contract-freeze branch: `codex/l3-package-lifecycle-contract-freeze`.

Originating posture: `select_source_directory_package_supersession_commit_route_state_contract_after_gap_freeze_sync`.

Blocked rendered target remains: `source_directory_package_supersession_commit_rendered_control`.

Selected contract: `source_directory_package_lifecycle_server_owned_contract`.

Selected immediate implementation slice after current-main sync: `implement_source_directory_package_lifecycle_server_owned_contract`.

Selected rendered implementation after contract proof: `implement_source_directory_package_supersession_commit_rendered_control_against_server_owned_lifecycle_contract`.

Existing source-directory preview route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`.

Existing generic replacement artifact route: `POST /api/v1/layer3/package/replacement-artifact/materialize`.

Existing generic replacement authority route: `POST /api/v1/layer3/package/replacement-set/record`.

Existing generic commit route: `POST /api/v1/layer3/package/supersession/commit`.

Repo-local server-owned precedent routes: `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set` and `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`.

Selected future route-state contract: source-directory package lifecycle replacement authority and commit must be server-owned, source-directory-aware, and minimal-identity only.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed by this freeze alone: `false`.

Backend contract implementation entry allowed after current-main sync: `true`.

Rendered commit-control implementation entry allowed by this freeze alone: `false`.

## Current-Main Authority

Doc `929` makes current-main authority explicit: the old next action cannot be the rendered package supersession commit submit control. The source-directory preview route exposes `source_package_set_hash` and `package_supersession_preview_hash` from source-directory schemas with redacted payload refs, while the generic replacement and commit services recompute generic package-set and preview bases from raw `L3OutputPackage` payload refs and generic package review state.

That mismatch is not only a final commit-submit problem. It also affects the replacement package lifecycle rail when the UI prefers `State.sourceDirectoryPackageSupersessionPreview` for replacement package-set authority. Feeding that source-directory preview into generic materialization or generic commit state turns the browser into an authority translator, which is the wrong boundary for this path.

The repo already contains the safer local pattern in the corrected-artifact route family: accept only identity and basis hashes from the operator surface, reload durable authority on the server, recompute refs/hashes/basis payloads server-side, and return redacted responses. The selected contract reuses that pattern for the source-directory package lifecycle instead of widening the generic routes or relying on frontend-computed durable authority.

## Selected Contract

The next backend implementation pass must introduce a source-directory-aware server-owned lifecycle contract with these boundaries:

- accept only minimal identity and basis fields from the rendered/operator surface: `client_request_id`, `session_id`, `analysis_plan_id`, `pass_run_id`, `reconciliation_record_id`, source-directory package supersession preview hash, source package set hash, replacement authority identity and basis hash, and operator decision;
- reload source-directory package authority, source `L3OutputPackage` rows, replacement materialization or replacement authority rows, and downstream dependencies on the server;
- compute any raw payload refs, replacement payload refs, source package-set hash bridge, replacement package-set hash, downstream dependency hash, and commit basis hash server-side;
- preserve raw local payload refs as server-private data in responses;
- preserve generic replacement and generic supersession routes without broadening their browser-supplied payload contracts;
- fail closed on stale source-directory preview hash, source package-set hash, replacement authority basis hash, replacement authority mode mismatch, scope mismatch, missing source package rows, or missing replacement authority;
- preserve idempotency by `client_request_id` and by server-computed basis hash;
- keep all response bodies redacted, status-oriented, and compatible with the existing `/review/layer3` state model.

The selected implementation shape may be two route entries or one narrow composed route, but it must prove both halves of the lifecycle bridge:

1. source-directory package supersession preview to durable replacement package-set authority;
2. durable replacement package-set authority to package supersession commit.

The implementation must not move final package-commit authority into JavaScript state, hidden form fields, browser storage, or mockup-local state.

## Non-Admission Boundary

This freeze introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, package supersession commit implementation, replacement package-set implementation, source `L3OutputPackage` row mutation, source package payload write, source package payload rewrite, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, provider-private signed URL behavior, public proxy runtime, connector dispatch, destination write, `ConnectorRun`, `ConnectorRunTarget`, source expansion, RAG/vector/model/provider runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond already-admitted surfaces, or full mockup program activation.

## Future Step Map

Immediate next pass after current-main sync:

1. Implement the server-owned source-directory package lifecycle contract in backend service/API tests first.
2. Prove stale hash, stale replacement authority, scope mismatch, raw-ref redaction, no package-row mutation, and idempotency behavior.
3. Sync the contract implementation to current main.
4. Wire the rendered package supersession commit control only to the new server-owned contract, then prove static, API, headless Chromium, and headed Chromium behavior.

Bounded operator path proof after the rendered control lands:

1. Source-directory scan/status rendered proof.
2. Material preview and Gate B rendered proof.
3. Retrieval/context and source-directory qualitative analysis proof.
4. Package construction, package review submit, package supersession preview, replacement authority, and supersession commit proof.
5. Package review, handoff/export prepare, admitted same-origin or redacted delivery/use, internal webhook dispatch/status, and Analysis Environment/mockup projection proof.
6. Bounded trial-usable checkpoint and minimal operator runbook.

Longer-term closeout:

1. Every critical mockup operator journey becomes live, read-only, intentionally excluded, or explicitly blocked through current-main evidence.
2. Full mockup activation remains blocked until a final readiness audit proves the bounded path, durable state owners, browser-storage policy, security posture, headed/headless consistency, and residual blockers.
3. Auth/security, observability/performance, connector/provider, broader source, and RAG/model/provider behavior remain separate product-authority gates unless current main later admits a named slice.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is the old immediate rendered commit-control implementation still valid? | No. Doc `929` explicitly blocks it until route/state contract selection, and current source confirms the mismatch. |
| Is the gap only the final commit submit payload? | No. `layer3.js` prefers `State.sourceDirectoryPackageSupersessionPreview` for replacement authority, while materialization and commit services recompute generic source/preview bases. |
| Is there a local precedent for the selected server-owned pattern? | Yes. The corrected-artifact replacement authority and commit routes accept minimal identity/basis inputs and recompute durable refs and hashes server-side. |
| Does this contract freeze add behavior? | No. It is docs/progress/checker metadata only. |
| Should generic routes be broadened now? | No. The contract selects a source-directory-aware bridge and preserves generic route contracts. |
| Does this activate the full mockup program? | No. Full mockup activation remains a governed evidence track, not a blanket implementation permission. |

## Next Posture

Next exact posture: `current_main_sync_source_directory_package_lifecycle_contract_freeze_then_backend_contract`.

After current-main sync, the next implementation pass is backend/API contract proof only for `source_directory_package_lifecycle_server_owned_contract`. The rendered package supersession commit control remains blocked until that server-owned lifecycle contract has landed and been synced.
