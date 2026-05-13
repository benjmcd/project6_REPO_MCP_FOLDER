# Source Intake Provider Public URL Rendered Controls Freeze

Status: planning/control rendered-controls freeze only; no rendered behavior admitted.

Boundary: `source_intake_provider_public_url_rendered_controls_freeze`.

Selected next implementation: `implement_source_intake_provider_public_url_rendered_controls`.

## Decision

After current-main provider-public prepare/status/revoke backend API sync, the next exact boundary is rendered controls over prepare/status/revoke only.

This intentionally does not select delivery/use. Delivery/use would require raw public URL exposure, `public_url_enabled: True`, public access semantics, and auth/security authority that remain blocked. Rendered controls are the narrower and safer next step because they can expose operator lifecycle actions and redacted state while preserving the no-raw-public-URL contract.

## Admitted future write surface

The next implementation may add only:

- rendered controls on the existing Layer 3 review/workbench surface for provider-public prepare/status/revoke lifecycle actions
- API client calls to the existing provider-public prepare/status/revoke endpoints
- redacted status display using `provider_public_url_redacted`
- disabled/blocked affordances for delivery/use and raw public URL display
- headed and headless browser proof for the rendered controls
- focused tests for redaction, disabled delivery/use controls, revoke/status state transition display, and absence of frontend-only durable authority
- progress/proof doc and verifier updates

## Required rendered-control contract

- Controls must operate over server-authoritative API state only.
- The UI must not fabricate or persist provider-public durable state in frontend-only storage.
- The UI must not display, request, cache, copy, or expose a raw public URL.
- The UI must keep delivery/use unavailable and explicitly blocked.
- The UI must display redacted provider-public URL state only.
- Revoke controls must require an explicit operator action and must show revoked state through the status endpoint.
- The pass must include headed and headless browser proof if rendered controls are implemented.

## Explicitly blocked

- No provider-public URL delivery/use route is admitted.
- No raw public URL display is admitted.
- No `public_url_enabled: True` authority rail is admitted.
- No raw public URL persistence or response exposure is admitted.
- No provider network or object-store write behavior is admitted.
- No public proxy URL runtime is admitted.
- No connector/destination dispatch is admitted.
- No package mutation/reconstruction is admitted.
- No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Validation required for this freeze

- `python .\tools\l3-progress-check.py` must pass.
- `git diff --check` must pass with no actionable whitespace errors.

## Next boundary

After this freeze is current-main synced, the next allowed implementation is `implement_source_intake_provider_public_url_rendered_controls` only.
