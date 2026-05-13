# Source Intake Provider Public URL Rendered Controls Current-main Sync

Status: current-main proof/control sync after PR `#938`.

Merged PR: `#938`.

Merge commit: `e0540652e9528cb72e68bc4af625254f5b7a44a0`.

Merged at: `2026-05-13T23:17:57Z`.

Boundary synced: `source_intake_provider_public_url_rendered_controls`.

## Current-main result

Current `project6-origin/main` now includes the bounded provider-public rendered controls implementation from PR `#938`.

The merged implementation adds only `/review/layer3` provider-public prepare/status/revoke controls over the existing backend provider-public prepare/status/revoke APIs. The UI renders server-returned redacted state only and keeps provider-public delivery/use, raw public URL display, public proxy runtime, and frontend-only durable provider-public authority blocked.

## Merge gate evidence

- PR `#938` head commit: `20e5e63c0b949a1277784fdc3029873cd890ceb0`.
- PR `#938` merge commit: `e0540652e9528cb72e68bc4af625254f5b7a44a0`.
- GitHub checks before merge:
  - `backend-layer3-api` -> `SUCCESS`
  - `test` -> `SUCCESS`
- PR comments: none.
- PR reviews: none.
- PR review threads: none.
- Merge state before merge: `CLEAN`.
- Post-merge `project6-origin/main` progress check: `python .\tools\l3-progress-check.py` -> `PASS`.

## Preserved negative boundary

- No provider-public delivery route is admitted.
- No provider-public use route is admitted.
- No raw public URL display, copy, cache, or browser durable authority is admitted.
- No `public_url_enabled: True` UI authority is admitted.
- No public proxy runtime is admitted.
- No connector/destination dispatch is admitted.
- No package mutation or reconstruction is admitted.
- No source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Next boundary

The next step is a new planning/control freeze before any provider-public delivery/use or downstream expansion. Delivery/use remains blocked because it would require raw public URL exposure semantics, public access behavior, and auth/security authority that are not admitted by PR `#938`.
