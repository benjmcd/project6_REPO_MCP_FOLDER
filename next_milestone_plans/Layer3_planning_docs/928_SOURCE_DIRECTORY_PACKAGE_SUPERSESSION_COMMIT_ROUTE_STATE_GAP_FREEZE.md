# 928 - Source-Directory Package Supersession Commit Route-State Gap Freeze

## Status

Status: no-runtime/no-rendered route-state gap freeze for `source_directory_package_supersession_commit_rendered_control`.

Doc: `928_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE.md`.

Predecessor current-main sync doc: `927_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_RENDERED_CONTROL_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before gap freeze: `4b40109e3922399c3b4a86f8d158ed5d9907599c`.

Gap-freeze branch: `codex/l3-package-commit-gap-freeze`.

Blocked target: `source_directory_package_supersession_commit_rendered_control`.

Blocked implementation action: `implement_source_directory_package_supersession_commit_rendered_control_after_freeze_sync`.

Selected stop action: `source_directory_package_supersession_commit_route_state_gap_freeze`.

Existing rendered node: `/review/layer3 #package-supersession-commit-panel`.

Existing commit route: `POST /api/v1/layer3/package/supersession/commit`.

Owner service: `backend/app/services/layer3_package_supersession_commit.py`.

Source-directory preview service: `backend/app/services/layer3_source_directory_qualitative_analysis.py`.

Replacement authority service: `backend/app/services/layer3_replacement_package_set_authority.py`.

Runtime behavior introduced by this gap freeze: `false`.

Rendered behavior introduced by this gap freeze: `false`.

Backend behavior introduced by this gap freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this gap freeze: `false`.

Executable test behavior introduced by this gap freeze: `false`.

Production UI behavior introduced by this gap freeze: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed by this gap freeze alone: `false`.

## Canonical Source Of Truth

The canonical source of truth is current `project6-origin/main` at `4b40109e3922399c3b4a86f8d158ed5d9907599c`.

Doc `927` allowed implementation only if current browser/server response state could assemble the existing commit request from governed authority. Current source inspection proves that condition is not met.

## Proven Gap

The source-directory package supersession preview service computes the source package-set and preview hashes from source-directory-specific redacted authority:

- source package set schema: `layer3.source_directory_package_supersession_source_package_set.v1`;
- preview basis schema: `layer3.source_directory_package_supersession_preview_basis.v1`;
- source package-set fields include `output_package_ids`, `package_kinds`, `payload_hashes`, `payload_refs_redacted`, and source-directory gates;
- response field: `source_package_set_hash`;
- response field: `package_supersession_preview_hash`.

The replacement package-set authority rendered path records durable replacement authority from that source-directory preview state. That durable authority therefore carries the source-directory `source_package_set_hash`.

The existing package supersession commit service recomputes generic package authority instead:

- source package set schema: `layer3.package_supersession_source_package_set.v1`;
- preview basis schema: `layer3.package_supersession_preview_basis.v1`;
- source package-set fields include full `output_packages` projections with server package `payload_ref` values;
- required replacement authority check: `authority.source_package_set_hash == source_package_set_hash`;
- required preview hash check: supplied `package_supersession_preview_hash == computed_preview_hash`.

Therefore the current source-directory replacement authority and the existing generic commit route do not share the same source package-set hash or preview hash contract. A rendered frontend-only implementation would either submit source-directory hashes and hit server conflicts, or substitute generic hashes while claiming source-directory authority. Both paths violate doc `926`/`927`.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Can the current rendered frontend safely select `State.sourceDirectoryPackageSupersessionPreview` and call the existing commit route? | No. The selected source-directory authority uses source-directory hash bases that the existing commit service does not accept. |
| Can the frontend fix this by using `State.packageSupersessionPreview` hashes while showing source-directory authority? | No. That would make the rendered source label stronger than the request authority and preserve ambiguous authority. |
| Is the correct next action a backend widening now? | No. This pass is a gap freeze only. A later freeze must select the exact route/state contract change before runtime behavior changes. |
| Does this gap freeze admit full mockup activation? | No. Package commit remains explicitly blocked for the source-directory path. |

## Required Future Contract Selection

The next admissible pass must select one exact route/state contract before implementation. Candidate directions are:

- add a source-directory-specific package supersession commit route/mode that validates the source-directory preview basis and source-directory replacement authority without mutating packages or widening downstream behavior;
- add a server-owned authority bridge that records a commit-compatible generic package supersession preview basis from the source-directory package lifecycle, with explicit provenance back to the source-directory preview;
- or explicitly mark source-directory package supersession commit as blocked/read-only until a broader package-authority unification milestone.

Any future contract must prove:

- no browser-provided arbitrary hashes are promoted to durable authority;
- no package payload bytes, package row mutation, package payload rewrite, replacement namespace rows, artifact manifests, downstream invalidation, connector dispatch, provider delivery, source expansion, RAG/vector/model/provider runtime, auth/security widening, browser-storage authority, frontend-only durable authority, or full mockup activation;
- generic package supersession commit behavior remains unchanged unless separately frozen; and
- source-directory package lifecycle state has an unambiguous server-owned hash basis before the rendered commit submit control is enabled.

## Non-Admission Boundary

This gap freeze admits no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior change, executable test behavior, production UI behavior, package supersession commit implementation, package replacement activation, source `L3OutputPackage` row mutation, source package payload write, source package payload rewrite, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, provider-private signed URL behavior, public proxy runtime, connector dispatch, destination write, `ConnectorRun`, `ConnectorRunTarget`, source expansion, RAG/vector/model/provider runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond already-admitted surfaces, or full mockup program activation.

## Validation

This gap-freeze branch must pass:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

No headed/headless browser run is required for this gap-freeze-only pass because it changes only planning/control/proof/checker metadata.

## Next Posture

Next exact posture: `current_main_sync_source_directory_package_supersession_commit_route_state_gap_freeze_then_select_commit_contract`.

Do not implement `source_directory_package_supersession_commit_rendered_control` until a later current-main-synced contract freeze selects the exact server-owned route/state basis that resolves this mismatch.
