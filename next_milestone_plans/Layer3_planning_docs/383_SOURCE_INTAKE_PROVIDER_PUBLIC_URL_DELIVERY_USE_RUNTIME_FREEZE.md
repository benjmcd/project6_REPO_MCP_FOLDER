# 383 - Source Intake Provider Public URL Delivery/Use Runtime Freeze

## Status

Status: planning/control freeze for `source_intake_provider_public_url_delivery_use_runtime_freeze`; no provider-public delivery/use runtime behavior admitted.

This freeze follows current-main doc `382_NEXT_LAYER3_SERVER_AUTHORITATIVE_RUNTIME_TRANCHE_SELECTION_FREEZE.md`, merged by PR `#977` at merge commit `f79c92905854f14471133fd29e37cd03d0b9b3f4`.

Freeze result: `no_runtime_now_provider_public_delivery_use_raw_url_authority_absent`.

No code-bearing provider-public delivery/use implementation is selected by this freeze.

## Canonical Source Of Truth

The canonical current-main source of truth is:

- `backend/app/services/layer3_provider_public_url.py`
- `backend/app/services/layer3_provider_public_url_state.py`
- `backend/app/api/layer3.py`
- `backend/app/models/models.py`
- `backend/tests/test_layer3_provider_public_url_state.py`
- `backend/tests/test_layer3_api.py`
- `next_milestone_plans/Layer3_planning_docs/352_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/353_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`
- `next_milestone_plans/Layer3_planning_docs/382_NEXT_LAYER3_SERVER_AUTHORITATIVE_RUNTIME_TRANCHE_SELECTION_FREEZE.md`

## Authority Audit

Current main stores provider-public URL state as redacted durable metadata:

- `L3ProviderPublicUrlReceipt` stores `provider_public_url_hash` and `provider_public_url_prefix`, not the raw public URL.
- `layer3_provider_public_url_state.py` returns `PROVIDER_PUBLIC_URL_REDACTED_MARKER`.
- `layer3_provider_public_url.py` returns `raw_public_url_exposed: False` and `public_url_enabled: False`.
- `test_layer3_provider_public_url_state.py` asserts the raw URL and token are not serialized.
- `test_layer3_api.py` asserts `/api/v1/layer3/handoff/export/download/provider-public-url/use` and `/api/v1/layer3/handoff/export/download/provider-public-url/deliver` are absent from OpenAPI.

That authority is sufficient for prepare/status/revoke over redacted durable state.

That authority is not sufficient for raw public URL delivery/use, because current main intentionally does not persist or return the raw public URL needed to implement a use route without either regenerating a new provider URL or widening provider/object-store authority.

## Required Proof Check

Doc `352` required exact proof before any future delivery/use implementation. The current repo state does not satisfy the required proof:

- exact delivery/use route names, methods, DTOs, and status codes are not selected
- raw public URL response policy cannot be admitted because current main does not retain raw public URL material
- `public_url_enabled: True` has no authority source
- provider/object-store ownership remains fake-provider redacted lifecycle only
- public access behavior for anyone possessing the URL is not selected
- revocation-after-exposure behavior cannot be proven because no raw exposure is admitted
- auth/security caller model is not selected
- leak controls for logs, telemetry, browser storage, clipboard, DOM, screenshots, network traces, and errors cannot be proved for a raw URL that current main does not admit
- cache-control and response-header behavior for raw public URL delivery/use is not selected
- headed/headless proof for rendered delivery/use controls is not applicable because no rendered delivery/use control is admitted

## Freeze Decision

`source_intake_provider_public_url_delivery_use_runtime_freeze` stops as no-runtime.

The selected code-bearing action is `none`.

This freeze preserves the redacted provider-public lifecycle as current authority and keeps delivery/use blocked.

## Explicit Non-Goals

No provider-public URL delivery/use route is admitted.

No raw public URL display is admitted.

No raw public URL persistence is admitted.

No raw public URL response exposure is admitted.

No `public_url_enabled: True` rail is admitted.

No provider network/object-store write is admitted.

No public proxy URL runtime is admitted.

No rendered provider-public delivery/use control is admitted.

No connector/destination dispatch is admitted.

No package mutation or reconstruction is admitted.

No source expansion is admitted.

No RAG/vector behavior is admitted.

No broad qualitative behavior is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No frontend-only durable authority is admitted.

## Next Required Action

The next required action is `current_main_sync_source_intake_provider_public_url_delivery_use_runtime_freeze_after_merge`.

After this freeze is merged and synced, the whole-project runtime posture returns to `select_next_bounded_layer3_runtime_tranche_via_later_exact_named_freeze_only`.

Provider-public delivery/use may only be reopened by a later exact named freeze that selects a concrete raw URL authority model, provider/object-store owner, exposure policy, revocation-after-exposure model, auth/security caller model, leak-control policy, response-header policy, and focused negative tests before code.
