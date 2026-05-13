# 340 - Source Intake Provider Public URL Durable State Current-main Sync

Status: current-main proof/control sync.

## Synced merge

PR `#929` merged `339_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DURABLE_STATE_SUBSTRATE.md` at merge commit `7b83e7490b67e6f0f5eb815cc84716388292b1fc`.

The source-intake provider-public URL durable-state substrate is now current-main behavior. It consists only of provider-public URL authority/receipt/revocation/audit models, migration `0024_layer3_provider_public_url_state.py`, state service `layer3_provider_public_url_state.py`, fake-provider contract double `layer3_provider_public_url_fake_provider.py`, and owner-service tests.

## Merge gate

- GitHub `backend-layer3-api` passed.
- GitHub `test` passed.
- PR comments were empty.
- PR reviews were empty.
- PR reviewThreads were empty.
- Merge state was `CLEAN`.
- Post-merge `python .\tools\l3-progress-check.py` passed on `project6-origin/main` at `7b83e7490b67e6f0f5eb815cc84716388292b1fc`.

## Current-main scope

Provider-public URL durable state exists, but no provider-public URL API route, rendered control, delivery/use path, or `public_url_enabled: True` rail is live.

No raw public URL value is intentionally persisted or exposed in authority snapshots, receipts, revocation payloads, audit payloads, or fake-provider responses.

Provider-private signed URL route behavior, same-origin delivery, same-origin signed-reference behavior, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, and frontend-only durable authority remain blocked.

## Next required decision

The next required decision is `source_intake_provider_public_url_route_entry_freeze`.

That freeze must decide whether the first route slice is prepare/status backend API only, status-only inspection over already prepared state, or another narrower route posture. It must keep rendered controls, public URL delivery/use, public proxy runtime, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, and frontend-only durable authority blocked unless a later freeze explicitly admits them.
