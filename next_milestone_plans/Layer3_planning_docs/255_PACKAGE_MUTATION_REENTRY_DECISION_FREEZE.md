# Package Mutation Reentry Decision Freeze

Status: current-main reentry decision freeze for `package_mutation_reentry_decision`.

This document follows `254_CONNECTOR_DESTINATION_REENTRY_DECISION_FREEZE.md`. It records the package mutation reentry decision after the goal-stack, source rendered-control, and connector/destination reentry audits: current main already has bounded backend/API package lifecycle runtimes, but no rendered package mutation control, broad package mutation/reconstruction, source `L3OutputPackage` row mutation, source package payload rewrite, replacement package payload generation, downstream invalidation/re-delivery runtime, connector/destination dispatch side effect, provider/public URL runtime, source expansion, broad qualitative/hybrid/RAG behavior, full mockup activation, auth/security behavior, hidden LLM planning, or frontend-only durable authority is admitted.

## Decision

```yaml
selected_planning_mode: package_mutation_reentry_decision
entry_decision: backend_lifecycle_live_rendered_mutation_blocked
base_branch: main
implementation_branch: codex/l3-package-mutation-reentry-freeze
live_behavior_change: false
current_package_lifecycle_runtime: backend_api_bounded_lifecycle
package_supersession_preview_only: live
replacement_package_set_authority: live
package_supersession_commit_entry: live
replacement_package_artifact_manifest_only: live
replacement_package_namespace_rows: live
rendered_package_mutation_controls: blocked
broad_package_mutation_reconstruction: blocked
source_package_row_mutation: blocked
source_package_payload_rewrite: blocked
replacement_package_payload_generation: blocked
downstream_invalidation_re_delivery_runtime: blocked
implementation_entry_allowed_next: false
next_required_boundary: single_named_rendered_package_lifecycle_freeze_before_ui_or_runtime_expansion
```

The decision is deliberately not a new runtime implementation. The live package authority is already limited to server-owned backend/API lifecycle records and immutable metadata relationships. It is not authority to edit package bytes, rewrite package payloads, mutate source package rows, generate replacement package payloads, expose browser-supplied diffs, invalidate downstream state, re-deliver packages, or surface rendered mutation controls.

## Current Live Boundary

The current package lifecycle boundary is:

- preview endpoint: `/api/v1/layer3/package/mutation/preview`;
- preview owner service: `backend/app/services/layer3_package_mutation_entry.py`;
- preview mode: `package_supersession_preview_only`;
- replacement set endpoint: `/api/v1/layer3/package/replacement-set/record`;
- supersession commit endpoint: `/api/v1/layer3/package/supersession/commit`;
- replacement artifact manifest endpoint: `/api/v1/layer3/package/replacement-artifact/manifest/record`;
- replacement namespace endpoint: `/api/v1/layer3/package/replacement-namespace/record`;
- live authority shape: immutable source package rows and payload refs, replacement package-set metadata, supersession lineage, replacement artifact manifest metadata, and separate replacement namespace rows;
- side effects still excluded: no source package row mutation, no source package payload rewrite, no replacement package payload generation, no rendered mutation control, no provider/public URL generation, no connector/destination dispatch, no source expansion, no RAG/vector retrieval.

## Runtime Still Blocked

The following remain blocked:

- rendered package mutation controls;
- rendered package supersession preview controls;
- rendered package supersession commit controls;
- rendered replacement package namespace review controls;
- rendered package lifecycle dashboard;
- broad `package_mutation_reconstruction`;
- browser-supplied package diffs, edited content, package bytes, package payloads, artifact bytes, generated file bytes, or local paths;
- source `L3OutputPackage` row creation, update, or deletion;
- source package payload creation, rewrite, overwrite, deletion, or reconstruction;
- replacement package payload generation;
- downstream invalidation runtime;
- re-delivery runtime;
- provider/public URL runtime;
- connector/destination dispatch as a package side effect;
- source expansion, upload, directory ingestion, web retrieval, or RAG/vector retrieval;
- broad qualitative/hybrid/RAG execution;
- full mockup activation;
- auth/security behavior changes.

## Reentry Requirements

A later rendered package lifecycle implementation may proceed only if it selects exactly one mode:

- `rendered_package_supersession_preview_control`;
- `rendered_package_supersession_commit_control`;
- `rendered_replacement_package_namespace_review_control`;
- `rendered_package_lifecycle_read_only_dashboard`.

The selected mode must define:

- named operator package-revision use case;
- exact server-authority source package and replacement package ownership;
- package payload source and immutable package rule;
- downstream invalidation policy;
- re-delivery compatibility rule;
- receipt and audit contract;
- stale-authority failure behavior;
- idempotency, replay, duplicate-action, and recovery behavior;
- leak-control policy for package bytes, diffs, local paths, refs, hashes, provider URLs, connector targets, destination targets, tokens, logs, error bodies, traces, screenshots, and responses;
- rendered UI state, theme, headed Chromium proof, and headless Chromium proof if controls are admitted.

## Validation Evidence

This freeze relies on already-landed implementation/audit evidence:

- PR `#809` recorded the goal-stack implementation audit and proved the current bounded implementation state.
- PR `#810` recorded the source rendered-control decision and preserved source/rendered non-admission.
- PR `#811` recorded the connector/destination reentry decision and preserved external dispatch non-admission.
- Current backend/API package lifecycle remains governed by `122_PACKAGE_MUTATION_FREEZE.md`, `126_PACKAGE_COMMIT_FREEZE.md`, `127_PACKAGE_REPLACEMENT_SET_FREEZE.md`, `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md`, `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md`, `130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md`, and `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md`.
- Current rendered package mutation non-admission remains governed by `191_PACKAGE_MUTATION_RENDERED_ENTRY_FREEZE.md`, `192_PACKAGE_MUTATION_RENDERED_ENTRY_CONTRACT.md`, and `216_PACKAGE_MUTATION_RENDERED_AUTHORITY_DISCOVERY_CLOSEOUT.md`.
- `python .\tools\l3-progress-check.py` must pass after this freeze is wired.

This validation does not prove rendered package mutation usability, browser diff authority, package payload generation, downstream invalidation, re-delivery, package lifecycle dashboard behavior, real operator package-revision workflows, provider/public URL behavior, connector/destination dispatch, or auth/security production readiness.

## Negative Invariants

- no rendered package mutation runtime;
- no rendered package mutation control;
- no rendered package supersession preview control;
- no rendered package supersession commit control;
- no rendered replacement package namespace review control;
- no rendered package lifecycle dashboard;
- no broad package mutation/reconstruction;
- no browser-owned package lifecycle authority;
- no browser-supplied package diffs, package bytes, edited content, artifact bytes, generated file bytes, or local paths;
- no source `L3OutputPackage` row creation, update, or deletion;
- no source package payload creation, rewrite, overwrite, deletion, or reconstruction;
- no replacement package payload generation;
- no downstream invalidation runtime;
- no re-delivery runtime;
- no provider/public URL runtime;
- no connector or destination dispatch;
- no generic downstream dispatch;
- no source expansion;
- no local upload;
- no local-directory ingestion;
- no arbitrary local path input;
- no web connector retrieval;
- no RAG/vector retrieval;
- no broad qualitative/hybrid/RAG runtime;
- no full mockup activation;
- no hidden LLM planning;
- no auth/security behavior change;
- no route/API/DTO/model/migration/service behavior change;
- no executable test behavior change;
- no CI workflow or Playwright configuration change;
- no frontend-only durable authority.

## Stop Condition

Stop before code if the next package proposal lacks one named rendered package lifecycle mode, treats backend/API lifecycle metadata as rendered mutation authority, accepts package bytes, diffs, edited content, generated file bytes, or local paths from the browser, mutates source `L3OutputPackage` rows, rewrites source package payloads, generates replacement package payloads without a separate artifact-generation freeze, lacks downstream invalidation and re-delivery policy, lacks stale-authority and idempotency proof, lacks headed/headless/theme proof for rendered controls, emits package mutation fields from existing same-origin/provider/connector/source/RAG responses without a compatibility freeze, or changes connector/source/RAG/mockup/auth behavior as a side effect.
