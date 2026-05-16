# 632 - Package Supersession Preview Operator Action Freeze

## Status

Status: implementation-entry freeze for `rendered_package_supersession_preview_control`; no runtime implementation begins in this pass.

This freeze follows current-main doc `631_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RENDERED_E2E_CURRENT_MAIN_SYNC.md`.

The selected next surface is `package_mutation_reconstruction`.

The selected exact named operator action is `supersede_package_preview`.

The selected implementation-entry mode is `rendered_package_supersession_preview_control`.

The selected server-authoritative backend surface already exists as `/api/v1/layer3/package/mutation/preview`, owned by `backend/app/services/layer3_package_mutation_entry.py`.

## Selection Basis

This is the narrowest implementation-bearing package action after the external local export rendered E2E sync because current main already admits the server-authoritative `package_supersession_preview_only` API while keeping package rows and payload files immutable.

The selected action lets an operator preview package supersession readiness from existing package lifecycle authority before any package mutation, commit, rebuild, replacement payload generation, downstream invalidation, or re-delivery behavior is admitted.

This freeze deliberately does not select:

- `rendered_package_supersession_commit_control`;
- `rendered_replacement_package_namespace_review_control`;
- `rebuild_package_from_corrected_artifacts`;
- package payload rewrite;
- source `L3OutputPackage` row mutation;
- replacement payload generation.

## Canonical Source Of Truth

The canonical current-main source of truth for a later implementation is:

- `backend/app/api/layer3.py`;
- `backend/app/services/layer3_package_mutation_entry.py`;
- `backend/app/services/layer3_workbench_package_state.py`;
- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.js`;
- `e2e/layer3-workbench.spec.js`;
- `backend/tests/test_layer3_api.py`.

The later implementation must read actual source before editing. It must not infer request fields, response fields, lifecycle status, or UI authority from this planning document alone.

## Admitted Later Slice

After this freeze is current-main synced, the next allowed implementation action is `implement_rendered_package_supersession_preview_control`.

That implementation may add only a rendered `/review/layer3` operator control that:

- derives its request from existing server-owned package review, package construction, package submit, and session-summary response state already present in the browser runtime;
- calls only `/api/v1/layer3/package/mutation/preview`;
- uses operator decision `preview_package_supersession`;
- displays the response-safe `package_supersession_preview_only` status, preview hash, package-set hash, immutable package rows, downstream dependency status, disabled capability flags, and next state;
- treats browser state as transient request assembly only, not durable authority;
- preserves the existing read-only package lifecycle dashboard;
- proves the control in headed and headless Chromium if rendered UI changes are made.

If current server/browser response state cannot assemble the preview request without adding backend authority, the later implementation must stop and write `package_supersession_preview_response_authority_freeze` instead.

## Request Boundary

The later rendered control may submit only existing response-safe server authority:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_preview_hash`;
- optional server-known downstream record refs already present in response state;
- `operator_decision: preview_package_supersession`.

The later rendered control must not accept or submit package payload bytes, edited package content, browser-generated diffs, arbitrary local paths, upload payloads, local directories, provider URLs, public URLs, signed URLs, connector ids, connector credentials, destination ids, destination URLs, package commit fields, replacement package payloads, source expansion fields, RAG/vector fields, hidden LLM fields, retry/rerun/cancel fields, or auth/security fields.

## Non-Admission Boundary

This freeze admits no runtime behavior by itself.

No backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, package row mutation, package payload write, package payload rewrite, replacement payload generation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority is admitted in this pass.

`package_supersession_commit_enabled` remains false for the selected preview action. A separate freeze is required before any supersession commit control, replacement package-set control, replacement namespace review, rebuild action, downstream invalidation, or re-delivery behavior can be implemented.

## Proof Plan For Later Implementation

The later implementation must prove:

- source audit confirms current browser/server response state can assemble the existing preview request without backend widening;
- the rendered control calls only `/api/v1/layer3/package/mutation/preview`;
- same-state retry does not create package rows, payload files, connector runs, destination writes, provider URLs, source rows, RAG/vector state, or frontend-durable authority;
- stale session, pass, reconciliation, package id, payload ref, payload hash, package review preview hash, and downstream record refs fail closed through the existing API;
- forbidden request fields are absent from the rendered request and remain rejected by the API;
- the response displays only response-safe status/history metadata and does not expose raw local paths or package payload bytes;
- mutation, commit, rebuild, replacement payload generation, downstream invalidation, re-delivery, connector/destination, provider-public, source expansion, RAG/vector, full mockup, and auth/security controls remain absent or disabled;
- headed and headless Chromium proof covers the rendered ready, submitted, previewed, and failed states if UI changes are made.

## Required Validation

This freeze branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this freeze because it changes planning/control metadata only.

## Next Posture

After this freeze merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

After that sync, the next exact posture is `implement_rendered_package_supersession_preview_control_after_freeze_sync`.
