# Source Intake Provider Public URL Delivery/Use Authority Contract

## Status

Status: planning/control delivery-use authority contract only; no runtime delivery/use behavior admitted.

This document completes the `provider_public_url_delivery_use_authority_contract_only` branch selected by the current-main sync doc `351_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_FREEZE_CURRENT_MAIN_SYNC.md`.

The selected contract is `source_intake_provider_public_url_delivery_use_authority_contract`.

## Current-main authority

Current main admits only the provider-public redacted lifecycle:

- provider-public durable authority, receipt, revocation, and audit state
- provider-public prepare/status backend APIs
- provider-public revoke backend API
- rendered `/review/layer3` provider-public prepare/status/revoke controls
- redacted provider-public state display
- delivery/use freeze as current-main planning/control truth

Current main does not admit raw public URL delivery, public URL use, `public_url_enabled: True`, public proxy runtime, provider network/object-store writes, connector/destination dispatch, package mutation, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority.

## External pattern check

The standard signed/public URL pattern treats possession of the URL as access authority during the URL's valid period, bounded by signer permissions, expiration, credential lifetime, key or policy revocation, transport safety, and distribution controls.

That pattern is compatible with the repo's current conservative boundary: a redacted provider-public lifecycle is safe to keep, but raw public URL delivery/use is not safe to admit without an explicit authority contract for bearer-token-like exposure, revocation, cache/log leakage, and public access behavior.

The external pattern is advisory only. Repo authority remains the source of truth for what can be implemented.

## Contract decision

Provider-public delivery/use is not admitted as a runtime implementation.

The next required decision is `next_deferred_server_authoritative_runtime_lane_freeze`.

No provider-public delivery/use implementation freeze may proceed unless a later user-selected pass explicitly reopens `source_intake_provider_public_url_delivery_use_implementation_freeze` and proves every required authority below.

## Required proof before any future delivery/use implementation

A future delivery/use implementation freeze must prove all of the following before code:

- exact delivery/use route names, HTTP methods, DTOs, and response status codes
- exact raw public URL response policy, including whether the URL is ever returned, copied, displayed, logged, cached, or stored
- exact `public_url_enabled: True` authority source, if that rail is ever admitted
- exact provider/object-store owner and whether the implementation is fake-provider-only, real-provider-only, or adapter-bounded
- exact public access behavior for anyone possessing the URL
- exact TTL, expiration, clock source, credential lifetime, and stale-authority behavior
- exact revocation model after URL exposure, including expired, revoked, missing, mismatched, and already-used states
- exact HTTPS-only and transport assumptions
- exact auth/security model for the API caller requesting delivery/use
- exact leak controls for logs, telemetry, browser storage, clipboard, DOM, screenshots, network traces, and error messages
- exact cache-control and response-header behavior
- exact audit trail and redaction behavior
- exact headed and headless browser proof, if rendered controls are involved
- exact negative tests proving fail-closed behavior when runtime state is empty, stale, expired, revoked, mismatched, or unauthorized

## Explicit non-goals

No provider-public URL delivery/use route is admitted.

No raw public URL display is admitted.

No `public_url_enabled: True` rail is admitted.

No raw public URL persistence or response exposure is admitted.

No provider network/object-store write is admitted.

No public proxy URL runtime is admitted.

No connector/destination dispatch is admitted.

No package mutation or reconstruction is admitted.

No source expansion is admitted.

No RAG/vector behavior is admitted.

No broad qualitative behavior is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No frontend-only durable authority is admitted.

## Whole-project next step

The provider-public lane has reached a coherent stopping point:

- server-owned provider-public state exists
- prepare/status/revoke APIs exist
- rendered prepare/status/revoke controls exist
- current-main sync docs and progress checker enforce that delivery/use remains blocked
- this contract defines the proof required before raw public URL delivery/use can be reopened

The next whole-project pass should select a separate deferred server-authoritative Layer 3 runtime lane via `next_deferred_server_authoritative_runtime_lane_freeze`.

That next lane must be named, bounded, source-of-truth identified, tested, review-cleared, and synced back to current main before any broader work proceeds.
