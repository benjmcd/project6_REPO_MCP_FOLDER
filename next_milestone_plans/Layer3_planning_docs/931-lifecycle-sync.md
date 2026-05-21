# 931 - Source-Directory Package Lifecycle Contract Current-Main Sync

## Status

Status: current-main sync for `source_directory_package_lifecycle_contract_freeze`.

Doc: `931-lifecycle-sync.md`.

Predecessor contract-freeze doc: `930-lifecycle-contract.md`.

Merged PR: `#1546`.

Source branch: `codex/l3-package-lifecycle-contract-freeze`.

Contract-freeze commit: `056467bb7f6dc52b9799f996bf813bce21ceea20`.

Merge commit: `7a7b7599c21168f7e7ebb043bb277370b7d7e636`.

Sync branch: `codex/l3-package-lifecycle-contract-sync`.

Base authority: `project6-origin/main` at `7a7b7599c21168f7e7ebb043bb277370b7d7e636`.

Synced contract: `source_directory_package_lifecycle_server_owned_contract`.

Synced blocked rendered target: `source_directory_package_supersession_commit_rendered_control`.

Synced immediate implementation slice: `implement_source_directory_package_lifecycle_server_owned_contract`.

Synced rendered implementation after contract proof: `implement_source_directory_package_supersession_commit_rendered_control_against_server_owned_lifecycle_contract`.

Synced source-directory preview route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`.

Synced generic replacement artifact route: `POST /api/v1/layer3/package/replacement-artifact/materialize`.

Synced generic replacement authority route: `POST /api/v1/layer3/package/replacement-set/record`.

Synced generic commit route: `POST /api/v1/layer3/package/supersession/commit`.

Synced corrected-artifact precedent routes: `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set` and `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Backend behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Executable test behavior introduced by this sync: `false`.

Production UI behavior introduced by this sync: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed for full mockup activation by this sync alone: `false`.

Backend contract implementation entry allowed after sync: `true`.

Rendered commit-control implementation entry allowed after sync: `false`.

## Current-Main Authority

Current main now includes doc `930` as the no-runtime/no-rendered contract freeze for `source_directory_package_lifecycle_server_owned_contract`.

The synced current-main decision is backend-first: implement a source-directory-aware server-owned package lifecycle contract before any rendered package supersession commit control is wired. The contract must bridge source-directory package supersession preview to durable replacement authority and replacement authority to package supersession commit without moving durable refs, hashes, commit basis calculation, or package row authority into browser state.

This sync introduces no runtime, rendered, backend, route/API/DTO/model/migration/service, executable test, or production UI behavior. It makes the contract-freeze decision current-main authority for the next backend/API implementation pass only.

## Merge Gate

PR `#1546` merged at `7a7b7599c21168f7e7ebb043bb277370b7d7e636`.

PR `#1546` checks:

- `backend-layer3-api`: `SUCCESS` in `3m17s`;
- `test`: `SUCCESS` in `3m59s`.

PR `#1546` review state before merge:

- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

## Validation

Contract-freeze branch validation recorded before PR `#1546` merge:

- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json`;
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `python -m py_compile ./tools/l3-progress-check.py`;
- `python ./tools/l3-progress-check.py`;
- `git diff --check`.

Current-main sync preflight:

- `python ./tools/l3-progress-check.py` after PR `#1546` merge - `PASS`.

This sync branch validation must additionally pass:

- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json`;
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `python -m py_compile ./tools/l3-progress-check.py`;
- `python ./tools/l3-progress-check.py`;
- `git diff --check`.

## Non-Admission Boundary

This sync introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, package supersession commit implementation, replacement package-set implementation, source `L3OutputPackage` row mutation, source package payload write, source package payload rewrite, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, provider-private signed URL behavior, public proxy runtime, connector dispatch, destination write, `ConnectorRun`, `ConnectorRunTarget`, source expansion, RAG/vector/model/provider runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond already-admitted surfaces, or full mockup program activation.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is doc `930` current-main authority now? | Yes. PR `#1546` merged at `7a7b7599c21168f7e7ebb043bb277370b7d7e636`. |
| Were checks green before merge? | Yes. `backend-layer3-api` and `test` both passed. |
| Were review surfaces clean? | Yes. Comments, reviews, latestReviews, reviewThreads, and unresolved reviewThreads were all `0`; merge state was `CLEAN`. |
| Does this sync add behavior? | No. It is docs/progress/checker metadata only. |
| Does this unblock rendered package supersession commit control implementation? | No. It unblocks only backend/API implementation of the server-owned lifecycle contract. |

## Next Posture

Next exact posture: `implement_source_directory_package_lifecycle_server_owned_contract`.

The next pass may implement only the backend/API contract for `source_directory_package_lifecycle_server_owned_contract`, with stale-authority, scope mismatch, redaction, no-mutation, and idempotency tests. The rendered package supersession commit control remains blocked until that server-owned lifecycle contract lands and is current-main synced.
