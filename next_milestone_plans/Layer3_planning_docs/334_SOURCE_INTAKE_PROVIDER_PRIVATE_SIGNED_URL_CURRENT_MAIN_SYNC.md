# Source Intake Provider Private Signed URL Current-main Sync

Status: current-main proof/control sync after PR `#924`.

PR `#924` merged `333_SOURCE_INTAKE_PROVIDER_PRIVATE_SIGNED_URL_BOUNDARY.md` at merge commit `1ff2e3a4d55e41d1936f067cbc9c8f9a610f448e`. The source-intake provider-private signed URL prepare/status/revoke path is now current-main behavior for source-intake external export/download readiness when same-origin signed-reference use has produced a durable receipt.

## Merge gate evidence

- merged_pr: `#924`
- merged_at: `2026-05-13T16:12:57Z`
- merge_commit: `1ff2e3a4d55e41d1936f067cbc9c8f9a610f448e`
- implementation_branch: `codex/l3-source-intake-provider-private-url`
- merged_doc: `333_SOURCE_INTAKE_PROVIDER_PRIVATE_SIGNED_URL_BOUNDARY.md`
- GitHub check `backend-layer3-api`: `SUCCESS`
- GitHub check `test`: `SUCCESS`
- comments: `[]`
- reviews: `[]`
- reviewThreads: `[]`
- merge_state_before_ready_merge: `CLEAN`
- post_merge_validation: `python .\tools\l3-progress-check.py` -> `PASS` on `project6-origin/main`

## Current-main behavior now admitted

- `backend/app/services/layer3_provider_private_signed_url.py` accepts source-intake readiness only when `signed_reference_receipt_id` resolves to durable same-origin signed-reference receipt/token authority.
- The resolved token must be `used`, have `use_count >= 1`, and match the source-intake prepare/readiness artifact refs, artifact hash/size, session, reconciliation, and source-intake identity.
- `backend/app/review_ui/static/layer3.js` can render source-intake provider-private prepare only after `State.externalExportDownloadSignedReferenceUse` exists, while preserving non-source-intake provider-private behavior.
- `backend/app/api/layer3.py` documents optional `signed_reference_receipt_id` in the existing provider-private prepare request schema.

## Still blocked after PR #924

- provider-public URL behavior remains blocked.
- connector/destination dispatch remains blocked.
- package mutation or reconstruction remains blocked.
- source expansion, local-directory authority, web connector retrieval, and RAG/vector behavior remain blocked.
- broad qualitative behavior and full mockup activation remain blocked.
- route, model, migration, and auth/security behavior remain unchanged.
- frontend-only durable authority remains blocked.

## Next boundary selected

The next exact boundary selected by this sync is `source_intake_provider_public_url_boundary_freeze`. This is a planning/control freeze only; no provider-public URL runtime, public proxy URL, ACL change, connector/destination dispatch, route/model/migration change, auth/security behavior, or rendered public URL control is admitted by this document.
