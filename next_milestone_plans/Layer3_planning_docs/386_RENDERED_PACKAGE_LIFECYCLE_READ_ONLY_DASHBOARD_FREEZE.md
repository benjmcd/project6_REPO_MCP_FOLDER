# 386 - Rendered Package Lifecycle Read-Only Dashboard Freeze

## Status

Status: implementation-entry freeze for `rendered_package_lifecycle_read_only_dashboard`; no runtime implementation begins in this pass.

This freeze follows current-main doc `385_LAYER3_RUNTIME_FREEZE_SEQUENCE_COMPLETION_AUDIT_AFTER_PROVIDER_PUBLIC_NO_RUNTIME.md`, merged by PR `#980` at merge commit `1e51a3ceea91e9ea5cbb161a603bf586c8db533e`.

This governing artifact is `386_RENDERED_PACKAGE_LIFECYCLE_READ_ONLY_DASHBOARD_FREEZE.md`.

The selected exact named Layer 3 product/use-case requirement is `operator_inspects_package_lifecycle_without_mutation`.

The selected implementation-entry mode is `rendered_package_lifecycle_read_only_dashboard`.

## Product Requirement

An operator needs one rendered `/review/layer3` inspection surface for the existing server-owned package lifecycle state after package review, construction, submit, supersession preview, replacement package-set authority, supersession lineage, replacement artifact manifest, and replacement namespace authority have been recorded.

The operator task is inspection only:

- understand which server-owned package lifecycle records exist for the current session;
- compare response-safe package ids, kinds, refs, hashes, statuses, and authority-basis hashes already returned by current server authority;
- see which package lifecycle capabilities remain disabled;
- confirm that no package payload rewrite, source package row mutation, replacement payload generation, downstream invalidation, re-delivery, connector/destination dispatch, provider/public URL behavior, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is available from the dashboard.

## Selection Basis

This is the narrowest selectable product/use-case after the provider-public no-runtime completion audit because it uses existing server-owned package lifecycle authority and does not reopen any closed deferred runtime lane by implication.

Current main already admits bounded backend/API package lifecycle runtimes:

- `package_supersession_preview_only`
- `replacement_package_set_authority`
- `package_supersession_commit_entry`
- `replacement_package_artifact_manifest_only`
- `replacement_package_namespace_rows`

Docs `191_PACKAGE_MUTATION_RENDERED_ENTRY_FREEZE.md`, `192_PACKAGE_MUTATION_RENDERED_ENTRY_CONTRACT.md`, and `216_PACKAGE_MUTATION_RENDERED_AUTHORITY_DISCOVERY_CLOSEOUT.md` name `rendered_package_lifecycle_read_only_dashboard` as a future candidate mode, while keeping rendered package mutation controls blocked.

The selected mode deliberately avoids the still-unverified rendered mutation modes:

- `rendered_package_supersession_preview_control`
- `rendered_package_supersession_commit_control`
- `rendered_replacement_package_namespace_review_control`

## Source-Of-Truth Audit

Canonical authority for the later implementation is:

- `backend/app/api/layer3.py`
- `backend/app/services/layer3_package_mutation_entry.py`
- `backend/app/services/layer3_replacement_package_set_authority.py`
- `backend/app/services/layer3_package_supersession_commit.py`
- `backend/app/services/layer3_replacement_package_artifact_manifest.py`
- `backend/app/services/layer3_replacement_package_namespace.py`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`
- `e2e/layer3-handoff.spec.js`

The later implementation must read actual source before editing. It must not infer available response fields from planning docs alone.

If current server responses do not expose enough response-safe package lifecycle fields for a read-only dashboard, implementation must stop and return to a narrower API/contract freeze. It must not silently add routes, DTO fields, model fields, migrations, or backend service behavior under this rendered-only freeze.

## Bounded Contract

The later implementation may add only a rendered read-only dashboard over existing server-owned response-safe state.

Allowed rendered behavior:

- one `/review/layer3` package lifecycle inspection panel or band;
- response-safe display of package lifecycle ids, package kinds, refs, hashes, statuses, authority-basis hashes, source gates, and disabled capability flags already available from current server responses;
- disabled/non-interactive affordances for mutation-only capabilities;
- clear separation between existing package review controls and the new read-only lifecycle dashboard;
- light, dark, and workbench theme rendering that preserves the current theme split.

Forbidden rendered behavior:

- package mutation buttons;
- package payload editing;
- package diff editing;
- package reconstruction controls;
- source `L3OutputPackage` row mutation controls;
- replacement payload generation controls;
- downstream invalidation controls;
- re-delivery controls;
- connector/destination controls;
- provider/public URL controls;
- source expansion controls;
- RAG/vector controls;
- full mockup activation controls;
- auth/security controls;
- browser-local package lifecycle authority.

Forbidden backend behavior:

- new route;
- new DTO field;
- new model;
- new migration;
- service behavior change;
- executable backend test behavior change;
- package row creation, update, or deletion;
- package payload file creation, overwrite, rewrite, reconstruction, or deletion;
- package payload bytes accepted from browser state;
- provider/public URL generation;
- connector/destination dispatch;
- source expansion;
- RAG/vector retrieval;
- auth/security behavior.

## Tests And Proof Plan

The later implementation must prove:

- static source audit confirms the rendered dashboard reads only existing response-safe package lifecycle fields;
- focused rendered tests prove the dashboard appears only as read-only inspection;
- mutation, payload, package-row, connector, provider URL, source expansion, RAG/vector, mockup activation, and auth/security controls are absent or disabled;
- no backend API/model/migration/service files changed unless a separate freeze admits them;
- headed and headless Chromium render the panel consistently;
- light, dark, and workbench theme coverage remains coherent;
- text does not overflow or overlap at the existing supported desktop/mobile viewports;
- existing package review, package construction, package submit, handoff/export, APS handoff, external export/download, signed-reference, provider-private, provider-public prepare/status/revoke, and connector-record flows remain unchanged.

Minimum validation commands for the later implementation:

- `python .\tools\l3-progress-check.py`
- `git diff --check`
- focused backend/API tests only if any backend files are separately admitted by a later freeze
- focused Playwright headed and headless checks for `/review/layer3` if rendered UI changes are made

## Review And Sync Gate

The later implementation PR must not merge until:

- GitHub `backend-layer3-api` passes;
- GitHub `test` passes;
- PR comments are reviewed and either addressed or explicitly adjudicated;
- PR reviews are reviewed and either addressed or explicitly adjudicated;
- PR review threads are empty, resolved, or explicitly superseded by a follow-up PR with current-main sync;
- merged `project6-origin/main` passes `python .\tools\l3-progress-check.py`;
- a current-main sync doc records the merge commit, check state, review-thread state, validation, and next posture.

## Explicit No-Go Boundaries

No package mutation runtime is admitted.

No rendered package mutation control is admitted.

No package payload rewrite, package payload generation, package payload deletion, package reconstruction, or source package row mutation is admitted.

No downstream invalidation or re-delivery runtime is admitted.

No provider-public delivery/use is admitted.

No connector/destination dispatch is admitted.

No source expansion is admitted.

No broad qualitative, hybrid, RAG/vector, or hidden LLM behavior is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No frontend-only durable authority is admitted.

No backend route, DTO, model, migration, or service behavior is admitted by this freeze.

## Next Allowed Action

The next allowed action is `implement_rendered_package_lifecycle_read_only_dashboard` only.

That action is allowed only if source audit proves current server responses already expose sufficient response-safe package lifecycle state for a read-only rendered dashboard. Otherwise the next action is `stop_and_write_package_lifecycle_response_authority_freeze`.
