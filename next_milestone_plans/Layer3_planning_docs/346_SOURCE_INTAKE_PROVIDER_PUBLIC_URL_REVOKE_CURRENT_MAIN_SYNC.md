# Source Intake Provider Public URL Revoke Current-main Sync

Status: current-main proof/control sync.

Synced implementation: `source_intake_provider_public_url_revoke_backend_api`.

Merged PR: PR `#935`.

Merge commit: `4f29b6db1879749ada7a2d5e66aa3ff6778f79e1`.

## Current-main authority

Provider-public URL revoke backend API is now current-main behavior. The current-main runtime surface is limited to:

- owner service revoke logic in `backend/app/services/layer3_provider_public_url.py`
- POST `/api/v1/layer3/handoff/export/download/provider-public-url/revoke`
- DTO/schema guards in `backend/app/api/layer3.py`
- focused API tests in `backend/tests/test_layer3_api.py`
- progress/proof controls in `tools/l3-progress-check.py`

## Merge gate evidence

- GitHub `backend-layer3-api` check passed.
- GitHub `test` check passed.
- PR comments were empty.
- PR reviews were empty.
- PR `reviewThreads` were empty.
- Merge state was `CLEAN`.
- Post-merge validation on `project6-origin/main` passed: `python .\tools\l3-progress-check.py` -> PASS.

## Preserved blocked scope

- Provider-public URL delivery/use route remains blocked.
- Rendered provider-public controls remain blocked.
- `public_url_enabled: True` remains blocked.
- Raw public URL persistence or response exposure remains blocked.
- Provider network/object-store writes remain blocked.
- Public proxy URL runtime remains blocked.
- Connector/destination dispatch remains blocked.
- Package mutation/reconstruction remains blocked.
- Source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, and frontend-only durable authority remain blocked.

## Next boundary

The next required decision is `source_intake_provider_public_url_delivery_use_or_rendered_control_freeze`.

That decision must select exactly one next provider-public URL boundary before any delivery/use route, rendered control, `public_url_enabled: True` rail, public proxy runtime, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, or frontend-only durable authority can proceed.
