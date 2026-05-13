# Source Intake Provider Public URL Delivery/Use Freeze

## Status

Status: planning/control delivery-use freeze only; no runtime delivery/use behavior admitted.

Current-main authority is PR `#939` at merge commit `bd4c230fd84e26e5c314c0be2a8138fc6e2667c8`, which synced PR `#938` provider-public rendered controls into `project6-origin/main`.

The admitted provider-public surface is limited to:

- durable provider-public URL authority/receipt/revocation/audit state
- backend provider-public prepare/status APIs
- backend provider-public revoke API
- `/review/layer3` provider-public prepare/status/revoke rendered controls
- redacted provider-public state display only

This document freezes the next boundary as `source_intake_provider_public_url_delivery_use_freeze`.

## Canonical authority

Canonical current-main authority is the server-owned source-intake provider-public URL chain:

- `L3SourceIntakeRecord` remains the source-intake material authority.
- Gate B, Gate C, plan preview, plan approval, execution selection, execution start, external export/download prepare, same-origin signed-reference use, and provider-private signed URL receipt authority remain required predecessor authority.
- Provider-public durable state records authority/receipt/revocation/audit state without raw public URL persistence or response exposure.
- Provider-public prepare/status/revoke backend APIs expose redacted provider-public state only.
- Rendered provider-public controls project only prepare/status/revoke over existing backend APIs and hold no frontend-only durable provider-public authority.

## Freeze decision

Provider-public delivery/use is not selected as the next implementation.

The next allowed action is `select_next_deferred_server_authoritative_layer3_lane_or_write_provider_public_delivery_use_authority_contract`.

That action must choose exactly one of the following:

- `provider_public_url_delivery_use_authority_contract_only`: a planning/control contract that proves raw public URL exposure semantics, public access behavior, auth/security authority, leak controls, logging/cache behavior, revocation enforcement, and tests before any delivery/use code.
- `next_deferred_server_authoritative_runtime_lane_freeze`: a separate named server-authoritative Layer 3 lane outside provider-public delivery/use.

No code-bearing provider-public delivery/use implementation may proceed from this freeze.

## Why delivery/use remains blocked

Delivery/use would require stronger authority than current-main has admitted:

- Raw public URL exposure semantics are not defined.
- Public access behavior is not defined.
- `public_url_enabled: True` authority is not admitted.
- Auth/security behavior is not admitted.
- Public proxy runtime behavior is not admitted.
- Browser durable storage, copy/display, logs, cache, and telemetry leak boundaries are not admitted.
- Revocation-after-exposure enforcement semantics are not admitted.
- Provider network/object-store writes remain out of scope for the current fake-provider substrate.
- Connector/destination dispatch remains out of scope.

## Explicitly blocked scope

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

## Required future proof before delivery/use

Before delivery/use can become a code-bearing slice, a later authority contract must prove:

- exact route and DTO shape
- exact raw public URL redaction/display/copy rules
- exact `public_url_enabled: True` authority source, if it is ever admitted
- exact public access behavior and TTL behavior
- exact stale, expired, revoked, missing, and mismatched authority failures
- exact post-revoke exposure behavior
- exact provider/object-store authority and fake/real provider boundary
- exact auth/security behavior
- exact logging/cache/telemetry leak controls
- exact browser storage prohibition
- exact negative tests and headed/headless proof

## Next whole-project direction

The provider-public sequence has now reached a safe redacted lifecycle surface: durable state, prepare/status, revoke, and rendered controls.

The whole-project continuation should not default to public URL delivery/use. The next pass should either:

- write the provider-public delivery/use authority contract as planning/control only, if raw-public exposure is still the intended next conceptual lane; or
- select the next deferred server-authoritative Layer 3 runtime lane that can proceed without raw public URL exposure, connector/destination dispatch, package mutation, RAG/vector indexing, broad qualitative execution, full mockup activation, or auth/security expansion.

## Validation requirement

This freeze is valid only if:

- `python .\tools\l3-progress-check.py` passes.
- `git diff --check` has no actionable whitespace defects.
- GitHub PR checks pass before merge.
- GitHub comments, reviews, and review threads are empty or resolved before merge.
