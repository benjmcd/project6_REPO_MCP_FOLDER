# Auth Security Entry Contract

Status: planning/control contract paired with `199_AUTH_SECURITY_ENTRY_FREEZE.md`.

This contract defines requirements for moving beyond the deferred `auth_security_entry_freeze` decision. It admits no authentication, authorization, tenant/session ownership runtime, operator permission matrix, route dependency change, middleware change, security audit-event runtime, provider secret handling, connector credential handling, rendered identity control, route, DTO, service behavior, model, migration, test behavior, source expansion, package mutation, provider/public URL runtime, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full mockup activation, or frontend-only durable authority.

Docs `184` through `198` remain authority for downstream, provider, connector, package, source, qualitative/RAG, and mockup entry boundaries. This contract is the narrower post-PR #754 entry-decision layer for any Layer 3 auth/security expansion.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, static UI files, Playwright tests, and checker behavior;
2. `backend/app/core/config.py`, `backend/main.py`, and deployment-profile tests in `backend/tests/test_layer3_api.py`;
3. Layer 3 route/request DTO contracts in `backend/app/api/layer3.py`;
4. existing browser/UI tests only for current rendered projection behavior, not identity authority;
5. docs `184` through `198`;
6. this contract and `199_AUTH_SECURITY_ENTRY_FREEZE.md`.

Planning prose, browser state, local storage, copied proxy headers, manually supplied usernames, screenshots, mockups, prior PR titles, and request-provided auth/security fields are not sufficient authority for runtime implementation.

## Entry Decision Contract

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_deployment_profile: local_default_with_nonlocal_proxy_guardrails
live_layer3_auth_owner: none_or_proxy_config_only
live_storage_exposure_guardrail: nonlocal_direct_storage_disabled
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed: selected auth mode, identity authority, tenant/session ownership authority, operator role and permission matrix, route dependency contract, storage exposure contract, provider/connector secret policy, audit-event contract, browser identity projection policy, headed/headless theme proof if UI changes, negative invariant proof, leakage policy, and no-cross-mode privilege escalation proof.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `deployment_profile_guardrail_only`;
- `proxy_identity_read_only_projection`;
- `route_level_operator_identity_required`;
- `session_tenant_owner_authorization`;
- `package_handoff_export_permission_gates`;
- `full_layer3_security_hardening_program`;
- `auth_security_gap_inventory_only`.

The selected mode must not rename request-supplied auth fields, browser-local state, proxy headers outside trusted proxy mode, manually clicked UI state, or planning/mockup text as server-authoritative identity, tenant, permission, or session-owner behavior.

## Request Contract For Later Runtime

A future request must be server-authority based. It may include or derive server-side actor identity, tenant/session refs, route/API refs, permission refs, deterministic policy hashes, idempotency keys, and operator confirmation only if the future freeze admits those fields.

The request must not accept auth policy overrides, arbitrary proxy headers from untrusted clients, browser-local identity dumps, local storage, screenshots as authority, provider credentials, connector credentials, destination secrets, package mutation fields, source expansion fields, prompt/model fields, or full security-program activation flags unless a later freeze explicitly admits one narrow server-authoritative mode.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later freeze: selected mode, server state refs, policy refs/hashes, idempotency status, response-safe failure code, response-safe failure reason, and next actions.

The response must not expose local filesystem paths, credentials, bearer tokens, proxy header values, provider URLs, connector targets, destination targets, prompt text, model/provider internals, package payload bodies, permission internals beyond response-safe labels, auth internals, or browser storage as authority.

## Existing Runtime Compatibility Contract

This entry freeze must preserve existing behavior:

- local proof-harness behavior remains available under local defaults;
- nonlocal deployment profile remains fail-closed unless proxy-owned auth guardrails and safe storage exposure settings are present;
- Layer 3 route/API behavior is unchanged;
- request-level auth/security override fields remain blocked where they are already declared deferred;
- rendered workbench behavior remains server-authoritative only for already-admitted workflow state and never becomes durable identity or permission authority.

## Browser And Theme Contract

This entry freeze adds no rendered UI control. If a later freeze admits rendered auth/security behavior, it must preserve `light`, `dark`, and `workbench` theme behavior, prove headed and headless Chromium consistency, prove disabled/focus/error states, avoid browser-state-only durable workflow truth, and expose no local path, credential, provider, connector, destination, prompt, auth token, or permission-secret authority in the browser.

## Test Contract For Later Runtime

Runtime or rendered implementation remains blocked until a later freeze names tests for disabled-by-default behavior, exact server identity binding, route dependency behavior, tenant/session ownership, operator permission matrix, forbidden auth/security override fields, untrusted proxy-header rejection, storage exposure confinement, provider/connector secret non-exposure, idempotency and concurrency, no unintended DB/file/package/provider/connector/destination side effects, no frontend-only durable authority, no path/credential/token/browser-storage leakage, headed/headless proof, and theme/accessibility coverage if UI changes are admitted.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only: docs `199` and `200` exist and are referenced; entry decision is `deferred`; selected mode is null; runtime status is `not_implemented`; live deployment profile and storage guardrails are acknowledged without being generalized into auth runtime; evidence ledger exists and unverified identity authority, tenant/session ownership, permission matrix, route dependency contract, audit-event contract, provider/connector secret policy, and browser identity/theme plan force deferral; exposure model exists and unknown values force deferral; capability isolation matrix exists and all runtime flags remain false; negative invariants are present; docs do not claim auth/security behavior is live.

The checker must not pretend to validate actual authentication, authorization, tenant isolation, proxy deployment safety, browser security, secret handling, audit completeness, threat modeling, penetration testing, or route/API correctness in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to activate more than one auth/security mode, trust unverified proxy headers, use browser state as identity/permission authority, change route dependencies without an explicit route contract, expose provider/connector/destination secrets, change storage exposure rules, alter auth/security behavior through another feature pass, add rendered controls without headed/headless and theme proof, or admit source/package/provider/connector/RAG/mockup behavior under auth/security scope.
