# 382 - Next Layer 3 Server-Authoritative Runtime Tranche Selection Freeze

## Status

Status: planning/control selection freeze for the next exact named Layer 3 server-authoritative runtime tranche; no runtime behavior admitted.

This document follows current-main doc `381_REVIEW_DEBT_REMEDIATION_CURRENT_MAIN_SYNC.md`, merged by PR `#970`, and the later PR `#974` through PR `#976` review-hygiene closeouts.

The selected freeze is `source_intake_provider_public_url_delivery_use_runtime_freeze`.

The selected freeze is not itself implementation permission. It is the next exact named freeze to write and prove before any provider-public delivery/use route, raw public URL response, `public_url_enabled: True` rail, public proxy runtime, provider network/object-store write, rendered delivery/use control, connector/destination dispatch, package mutation, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority can proceed.

## Selection Basis

Current main has closed or blocked the deferred server-authoritative runtime lane chain under docs `378` and `379`.

The only deferred lane with a current server-owned substrate, rendered lifecycle controls, and an explicit authority-proof checklist is provider-public delivery/use:

- provider-public durable state substrate exists
- provider-public prepare/status backend APIs exist
- provider-public revoke backend API exists
- rendered `/review/layer3` prepare/status/revoke controls exist
- doc `352_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT.md` lists the required proof before any later delivery/use runtime
- doc `353_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md` syncs that contract to current main while preserving runtime non-admission

The other deferred lanes are not selected by this freeze:

- connector/destination lacks a named connector or destination target
- package mutation lacks a named rendered operator package action
- broad qualitative/hybrid/RAG lacks a named broad analysis mode
- source expansion lacks a named unsupported source family
- full mockup activation lacks a named runtime target distinct from target-state mockups
- auth/security hardening lacks a named behavior, protected surface, threat model, and policy owner
- frontend-only durable authority remains a no-go invariant, not a server-authoritative runtime lane

## Canonical Authority

The selected next freeze must treat these files as current authority:

- `next_milestone_plans/Layer3_planning_docs/352_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/353_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`
- `backend/app/services/layer3_provider_public_url.py`
- `backend/app/services/layer3_provider_public_url_state.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_provider_public_url_state.py`
- `backend/tests/test_layer3_api.py`

Those source files currently preserve redacted durable provider-public state and do not admit raw public URL delivery/use.

## Required Next Freeze

The immediate next pass is `source_intake_provider_public_url_delivery_use_runtime_freeze`.

That freeze must prove, before code:

- exact route names, HTTP methods, request DTOs, response DTOs, and status codes for any delivery/use surface
- whether raw public URL exposure is admitted at all, and if so, exactly where it is returned, copied, displayed, logged, cached, stored, and redacted
- exact provider/object-store authority and whether the lane remains fake-provider-only or admits a real provider adapter
- exact public access semantics for anyone possessing the URL
- exact TTL, expiry, clock, credential-lifetime, revoked, expired, missing, mismatched, stale, and already-used behavior
- exact auth/security caller model for requesting delivery/use
- exact leak controls for logs, telemetry, browser storage, clipboard, DOM, screenshots, network traces, and errors
- exact cache-control and response headers
- exact audit and redaction behavior
- exact negative tests proving fail-closed behavior against empty, stale, expired, revoked, mismatched, unauthorized, and malformed runtime state

If any of those proof items cannot be made exact, the selected freeze must stop as no-runtime and must not proceed to implementation.

## Non-Admission Boundary

This selection freeze admits no runtime behavior, no rendered UI behavior, no schema change, no migration change, no route change, and no service behavior change.

Provider-public delivery/use remains blocked until `source_intake_provider_public_url_delivery_use_runtime_freeze` is written, proved, reviewed, merged, and current-main synced.

No closed or blocked deferred lane is reopened by implication.

## Next Required Action

The next required action is `source_intake_provider_public_url_delivery_use_runtime_freeze`.

After that freeze is complete and synced to current main, the only eligible code-bearing action is the implementation explicitly admitted by that freeze.
