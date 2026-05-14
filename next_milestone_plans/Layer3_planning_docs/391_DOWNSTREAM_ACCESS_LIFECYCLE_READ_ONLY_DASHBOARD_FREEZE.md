# 391 - Downstream Access Lifecycle Read-Only Dashboard Freeze

## Status

Status: implementation-entry freeze for `rendered_downstream_access_lifecycle_read_only_dashboard`; no runtime implementation begins in this pass.

This freeze follows current-main doc `390_RENDERED_PACKAGE_LIFECYCLE_DASHBOARD_REVIEW_FIX_CURRENT_MAIN_SYNC.md`, merged by PR `#986` at merge commit `b02b7a076093c1f6ef11b5f04aae19ea8310271b`.

This governing artifact is `391_DOWNSTREAM_ACCESS_LIFECYCLE_READ_ONLY_DASHBOARD_FREEZE.md`.

The selected exact named Layer 3 product/use-case requirement is `operator_inspects_downstream_access_lifecycle_without_dispatch_or_raw_url_use`.

The selected implementation-entry mode is `rendered_downstream_access_lifecycle_read_only_dashboard`.

## Product Requirement

An operator needs one rendered `/review/layer3` inspection surface for existing server-owned downstream access lifecycle state after package review, handoff/export prepare, APS handoff dispatch, external export/download readiness or delivery, signed-reference generation/use, provider-private receipt prepare/status/revoke, provider-public redacted prepare/status/revoke, and internal connector-dispatch record-only state have been recorded.

The operator task is inspection only:

- understand which downstream access records exist for the current session;
- compare response-safe record refs, receipt ids, artifact refs, redacted states, disabled flags, and authority rails already returned by current server authority;
- see which downstream access capabilities remain disabled;
- confirm that no external connector invocation, destination write, raw public URL display/use, public proxy runtime, provider network/object-store write, package mutation, source expansion, RAG/vector behavior, auth/security behavior, or frontend-only durable authority is available from the dashboard.

## Selection Basis

This is the narrowest selectable product/use-case after the package lifecycle dashboard current-main sync because current `/review/layer3` already contains bounded controls and response objects for downstream access checkpoints, but lacks a single read-only lifecycle summary that shows the whole post-package access chain without activating new dispatch or raw URL behavior.

Current main already admits bounded downstream/access-adjacent behavior:

- handoff/export prepare;
- APS handoff dispatch;
- external export/download prepare and same-origin delivery;
- signed-reference generate/use with configured-secret fail-closed behavior;
- provider-private signed URL prepare/status/revoke over server-owned receipt state;
- provider-public redacted prepare/status/revoke with raw public URL delivery/use blocked;
- internal connector dispatch record-only behavior.

Current main still blocks provider-public delivery/use, external connector invocation, destination writes, connector-run creation, generic downstream dispatch, provider network/object-store writes, public proxy runtime, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative/hybrid behavior, full mockup activation, auth/security behavior, and frontend-only durable authority.

## Source-Of-Truth Audit

Canonical authority for the later implementation is:

- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_external_export_response.py`
- `backend/app/services/layer3_provider_private_signed_url.py`
- `backend/app/services/layer3_provider_private_signed_url_state.py`
- `backend/app/services/layer3_provider_public_url.py`
- `backend/app/services/layer3_provider_public_url_state.py`
- `backend/app/services/layer3_connector_dispatch_entry.py`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`
- `e2e/layer3-handoff.spec.js`

The later implementation must read actual source before editing. It must not infer available response fields from planning docs alone.

If current server responses do not expose enough response-safe downstream access lifecycle fields for a read-only dashboard, implementation must stop and return to a narrower API/contract freeze. It must not silently add routes, DTO fields, model fields, migrations, or backend service behavior under this rendered-only freeze.

## Bounded Contract

The later implementation may add only a rendered read-only dashboard over existing server-owned response-safe downstream access state.

Allowed rendered behavior:

- one `/review/layer3` downstream access lifecycle inspection panel or band;
- response-safe display of handoff/export, APS dispatch, external export/download, signed-reference, provider-private, provider-public redacted, and connector record-only states already available from current server responses;
- disabled/non-interactive affordances for unavailable delivery/use, connector invocation, destination write, provider raw URL, public proxy, and external dispatch capabilities;
- clear separation between existing downstream controls and the new read-only lifecycle dashboard;
- light, dark, and workbench theme rendering that preserves the current theme split.

Forbidden rendered behavior:

- external connector invocation controls;
- destination write controls;
- connector-run creation controls;
- raw public URL display or copy controls;
- provider-public delivery/use controls;
- public proxy controls;
- provider network/object-store write controls;
- package mutation controls;
- source expansion controls;
- RAG/vector controls;
- full mockup activation controls;
- auth/security controls;
- browser-local downstream access authority.

Forbidden backend behavior:

- new route;
- new DTO field;
- new model;
- new migration;
- service behavior change;
- executable backend test behavior change;
- connector invocation;
- destination write;
- connector-run creation;
- provider-public delivery/use;
- raw public URL persistence or response exposure;
- provider network/object-store write;
- public proxy runtime;
- package mutation;
- source expansion;
- RAG/vector retrieval;
- auth/security behavior.

## Tests And Proof Plan

The later implementation must prove:

- static source audit confirms the rendered dashboard reads only existing response-safe downstream access fields;
- focused rendered tests prove the dashboard appears only as read-only inspection;
- connector invocation, destination write, raw public URL, provider-public delivery/use, public proxy, package mutation, source expansion, RAG/vector, mockup activation, and auth/security controls are absent or disabled;
- no backend API/model/migration/service files changed unless a separate freeze admits them;
- headed and headless Chromium render the panel consistently;
- light, dark, and workbench theme coverage remains coherent;
- text does not overflow or overlap at the existing supported desktop/mobile viewports;
- existing handoff/export, APS handoff, external export/download, signed-reference, provider-private, provider-public prepare/status/revoke, package lifecycle, source-intake, plan/execution, and connector-record flows remain unchanged.

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

No external connector invocation is admitted.

No destination write or connector-run creation is admitted.

No provider-public delivery/use, raw public URL display/use, raw public URL persistence, public proxy runtime, or provider network/object-store write is admitted.

No package mutation runtime is admitted.

No source expansion is admitted.

No broad qualitative, hybrid, RAG/vector, or hidden LLM behavior is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No frontend-only durable authority is admitted.

No backend route, DTO, model, migration, or service behavior is admitted by this freeze.

## Next Allowed Action

The next allowed action is `implement_rendered_downstream_access_lifecycle_read_only_dashboard` only.

That action is allowed only if source audit proves current server responses already expose sufficient response-safe downstream access lifecycle state for a read-only rendered dashboard. Otherwise the next action is `stop_and_write_downstream_access_response_authority_freeze`.
