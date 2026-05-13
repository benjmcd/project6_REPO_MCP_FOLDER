# Source Intake Provider Public URL Boundary Freeze

Status: current-main planning/control freeze for `source_intake_provider_public_url_boundary`.

This document selects `source_intake_provider_public_url_boundary` as the next exact downstream boundary after current-main PR `#924`. It is planning/control only and admits no runtime behavior by itself.

## Current authority and failure boundary

Current main now admits source-intake provider-private signed URL prepare/status/revoke through durable receipt authority, but provider-public URL behavior remains blocked. The repo-confirmed blocking evidence is:

- `backend/app/services/layer3_provider_private_signed_url.py` forbids client/provider fields including `public_url`, `public_proxy_url`, `provider_url`, `download_url`, `signed_url`, and raw `signed_reference_token` in provider-private prepare payloads.
- Provider-private responses keep `public_url_enabled: False` in their authority rails.
- `backend/app/services/layer3_external_export_response.py` still reports same-origin delivery with `public_url_enabled: False`, `signed_url_enabled: False`, `connector_dispatch_enabled: False`, and `destination_selection_enabled: False`.
- `backend/tests/test_layer3_page.py` continues to assert that rendered delivery/public URL fields are absent or disabled.
- Historical docs `110_PROVIDER_URL_FREEZE.md` and `111_PROVIDER_URL_CONTRACT.md` require a separate provider/public URL implementation-entry freeze before any provider/object-store authority, ACL/expiry/revocation/header/security behavior, leakage controls, audit/receipt behavior, or tests can become code.

The named planning failure boundary is `source_intake_provider_public_url_not_admitted`.

## Future implementation scope, if selected later

A future implementation may only proceed after auditing and proving all of the following against current-main code:

- exact source-intake authority chain from `layer3.source_intake_external_export_download_prepare.v1`, same-origin delivery, signed-reference use receipt, and provider-private receipt state;
- provider/object-store authority owner and fake-provider/public-URL substrate;
- public URL shape, TTL, revocation, redaction, leak controls, and audit/receipt contract;
- idempotent prepare/status/revoke or equivalent lifecycle semantics;
- stale-authority, mismatched artifact, mismatched source-intake identity, missing receipt, expired URL, revoked URL, and public URL leakage failures;
- rendered controls only if server-authoritative public URL state exists, never browser-only public URL authority;
- local backend/API/page tests, rendered Chromium proof, progress check, and diff hygiene.

## Explicit exclusions

- No provider-public URL runtime is admitted by this freeze.
- No public proxy URL runtime is admitted by this freeze.
- No connector/destination dispatch is admitted.
- No package mutation or reconstruction is admitted.
- No source expansion, local-directory authority, web connector retrieval, or RAG/vector behavior is admitted.
- No broad qualitative behavior or full mockup activation is admitted.
- No route, model, migration, or auth/security behavior change is admitted.
- No frontend-only durable authority is admitted.

## Next action

The next code-bearing action, if this freeze is accepted and merged, is `implement_source_intake_provider_public_url_boundary` only. It must remain in audit/recon mode until the canonical provider-public URL authority and exact server-owned lifecycle are proven from current-main code.
