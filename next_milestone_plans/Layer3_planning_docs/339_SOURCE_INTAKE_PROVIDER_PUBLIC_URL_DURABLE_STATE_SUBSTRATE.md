# 339 - Source Intake Provider Public URL Durable State Substrate

Status: branch-local substrate implementation; targeted validation passed.

## Implemented boundary

`source_intake_provider_public_url_durable_state_substrate` implements only the durable state and fake-provider contract substrate selected by doc `338`.

## Implementation surface

- `backend/app/models/models.py` adds provider-public URL authority, receipt, revocation, and audit-event models.
- `backend/alembic/versions/0024_layer3_provider_public_url_state.py` adds matching migration tables and indexes.
- `backend/app/services/layer3_provider_public_url_state.py` owns deterministic receipt identity, authority hashing, public URL hashing, TTL bounds, revocation, stale-authority failure, and redacted response fields.
- `backend/app/services/layer3_provider_public_url_fake_provider.py` adds a fake-provider contract double that exposes only redacted provider-public URL state and keeps provider network/object writes disabled.
- `backend/tests/test_layer3_provider_public_url_state.py` proves idempotent prepare, conflict rejection, TTL bounds, stale-authority failure, revocation, audit redaction, and fake-provider redaction.

## Preserved blocks

No provider-public URL route is added.
No public URL delivery/use route is added.
No rendered provider-public URL controls are added.
No `public_url_enabled: True` rail is enabled.
No raw public URL value is persisted in authority snapshots, receipts, revocation payloads, audit payloads, or fake-provider responses.
No provider-private signed URL route behavior is changed.
No real provider network, object-store, ACL, public proxy, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Validation

Targeted validation passed:

- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py` -> 5 passed
- `python -m pytest .\backend\tests\test_layer3_provider_private_signed_url_state.py` -> 9 passed
- `python .\tools\l3-progress-check.py` -> PASS
- `git diff --check` -> CRLF warnings only

## Next required decision

After merge, the next required action is current-main proof/control sync for this substrate before any provider-public route, rendered control, or delivery behavior can be frozen.
