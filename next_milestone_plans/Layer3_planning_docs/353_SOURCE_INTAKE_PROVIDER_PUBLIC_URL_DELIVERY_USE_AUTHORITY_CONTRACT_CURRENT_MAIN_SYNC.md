# Source Intake Provider Public URL Delivery/Use Authority Contract Current-main Sync

## Status

Status: current-main proof/control sync for provider-public delivery/use authority contract; no runtime delivery/use behavior admitted.

PR `#942` merged `352_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_AUTHORITY_CONTRACT.md` into `project6-origin/main` at merge commit `6c493ea1ba44329ebaba93a86b04fb932efd07b4`.

The merged contract records `source_intake_provider_public_url_delivery_use_authority_contract` as current-main planning/control truth.

## Merge gate evidence

- Branch: `codex/l3-provider-public-delivery-use-authority-contract`
- Head commit: `c45af3a004b73caa9a2d0c35129b235d7586f21e`
- Merge commit: `6c493ea1ba44329ebaba93a86b04fb932efd07b4`
- GitHub check `backend-layer3-api`: `SUCCESS`
- GitHub check `test`: `SUCCESS`
- PR comments: empty
- PR reviews: empty
- PR review threads: empty
- Merge state before merge: `CLEAN`
- Mergeable state before merge: `MERGEABLE`
- Post-merge `python .\tools\l3-progress-check.py`: `PASS`

## Current-main decision

Provider-public delivery/use remains blocked as runtime behavior.

Current main admits only:

- provider-public durable state substrate
- provider-public prepare/status backend API
- provider-public revoke backend API
- rendered `/review/layer3` provider-public prepare/status/revoke controls
- delivery/use freeze
- delivery/use authority contract

The required proof for any later delivery/use reopening is now documented, but the implementation itself is not admitted.

## Current-main blocked scope

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

## Next required decision

The next required decision is `next_deferred_server_authoritative_runtime_lane_freeze`.

The provider-public lane is at a safe planning/control stop point. The next pass should select a separate named server-authoritative Layer 3 runtime lane unless a later user-selected pass explicitly reopens provider-public delivery/use with all required proof from doc `352`.
