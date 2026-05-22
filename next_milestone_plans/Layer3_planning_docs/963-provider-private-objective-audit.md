# 963 - Provider-Private Objective Evidence Audit

## Status

Status: current-main evidence audit for the active provider-private/redacted delivery lifecycle objective after `962-provider-private-runbook-refresh.md`.

Current-main authority: `project6-origin/main` at `0db5dca7 Merge pull request #1598 from benjmcd/codex/l3-provider-private-runbook-refresh`.

This audit introduces no route, DTO, database model, migration, service behavior, rendered UI behavior, executable behavior, provider object behavior, connector dispatch, source expansion, RAG/vector/model runtime, public URL/proxy behavior, frontend-only durable authority, or full mockup activation.

## Objective Requirements

The active objective requires current-main evidence for each exact admitted package or handoff artifact family:

1. prepare/status/use/revoke-or-expiry lifecycle;
2. durable receipt/audit state;
3. artifact authority binding;
4. stale-authority rejection;
5. redacted rendered controls or intentionally read-only rendered status surface;
6. headed and headless operator proof;
7. current-main sync;
8. explicit prohibition of raw URL or credential exposure, provider-public URL enablement, public proxying, provider object write/copy/mutation, arbitrary connector dispatch, frontend-only durable authority, source expansion, RAG/vector/model runtime, and full mockup activation unless separately frozen.

## Current-Main Admitted Families

### Source-Directory Hybrid Handoff/Export Package Artifact

Status: proved current-main admitted signed-URL lifecycle.

Authority:

- API routes: `/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/{prepare,status,use,revoke}`.
- Owner service: `backend/app/services/layer3_source_directory_hybrid_analysis.py`.
- Rendered surface: `#provider-private-signed-url-*` controls in `backend/app/review_ui/static/layer3.js`.
- Live rendered proof: `e2e/layer3-workbench.spec.js` test `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path`.

Evidence:

- prepare/status/use/revoke are exercised on the source-directory live path;
- durable provider-private receipt and audit response fields are asserted without raw token exposure;
- artifact authority is bound to source-directory external export/download package authority;
- stale package payload hash rejection is proved by `source_directory_hybrid_external_export_download_delivery_payload_hash_mismatch`;
- replay rejection is proved by `provider_private_signed_url_state_replay_denied`;
- use-after-revoke rejection is proved by `provider_private_signed_url_state_revoked`;
- provider-public URL controls remain disabled and rendered as not admitted;
- headed and headless live-path proof passed in `962-provider-private-runbook-refresh.md`.

### Source-Directory Package Replacement/Supersession Artifact

Status: proved current-main admitted signed-URL lifecycle.

Authority:

- API routes: `/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/provider-private-signed-url/{prepare,status,use,revoke}`.
- Owner service: `backend/app/services/layer3_package_supersession_commit.py`.
- Rendered surface: source-directory package supersession option in `#provider-private-signed-url-artifact-family`.
- Live rendered proof: `e2e/layer3-workbench.spec.js` test `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path`.

Evidence:

- prepare/status/use/revoke are exercised on the source-directory live path;
- durable provider-private receipt and audit response fields are asserted without raw token exposure;
- artifact authority is bound to package supersession commit authority;
- stale commit basis rejection is proved by `source_directory_package_supersession_provider_private_package_supersession_commit_basis_hash_mismatch`;
- replay rejection is proved by `provider_private_signed_url_state_replay_denied`;
- use-after-revoke rejection is proved by `provider_private_signed_url_state_revoked`;
- provider-public URL controls remain disabled and rendered as not admitted;
- headed and headless live-path proof passed in `962-provider-private-runbook-refresh.md`.

### Local-Outbox Provider-Private Handoff

Status: proved local/fake provider-private handoff substrate; not a real external target admission.

Authority:

- API routes: `/handoff/connector/local-outbox/provider-private/prepare` and `/handoff/connector/local-outbox/provider-private/status/{provider_private_handoff_receipt_id}`.
- Owner service: `backend/app/services/layer3_local_outbox_provider_private_handoff.py`.
- Rendered surface: `#local-outbox-provider-private-handoff-panel`.
- Rendered proof: `recordRenderedLocalOutboxProviderPrivateHandoffSmoke` in `e2e/layer3-workbench.spec.js` plus local-outbox handoff tests in `e2e/layer3-handoff.spec.js`.
- Current-main sync docs: `620_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_RENDERED_E2E_CURRENT_MAIN_SYNC.md` and `691_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_RUNTIME_CURRENT_MAIN_SYNC.md`.

Evidence:

- prepare/status are exercised after server-owned local outbox write;
- expiry is represented by `local_outbox_provider_private_handoff_expired`;
- durable local-outbox provider-private handoff receipt and audit event rows are proved;
- artifact authority is bound to server-owned local outbox write receipt, artifact hash, and size;
- stale authority is rejected by `local_outbox_provider_private_handoff_stale_authority`;
- rendered surface is intentionally read-only and shows history, audit, idempotency, raw token replay blocked, provider-private use route blocked, and real connector invocation blocked;
- headed/headless rendered proof is current-main recorded for the local/fake substrate;
- real connector target selection remains gated and is not admitted by this family.

## Explicit Non-Admissions

Current-main evidence preserves these non-admissions:

- generic provider-private signed URL use route remains absent;
- provider-public URL enablement remains blocked for source-directory provider-private families;
- public proxy behavior is absent;
- provider object write/copy/mutation is absent;
- arbitrary connector dispatch and real destination write remain blocked;
- credentials are not exposed or enabled;
- frontend-only durable authority is not used;
- source expansion is not admitted;
- RAG/vector/model runtime is not admitted;
- full mockup activation remains blocked.

## Completion Posture

The objective is satisfied for the currently identified current-main-admitted provider-private/redacted package and handoff artifact families above.

The objective is not closed as a permanent project-wide goal because future current-main admissions can add new exact artifact families. Any such family must repeat this evidence pattern: freeze the exact family, implement or prove prepare/status/use/revoke-or-expiry, prove durable receipt/audit and stale-authority behavior, prove headed/headless rendered operator behavior, sync current main, and preserve every non-admission unless separately frozen.

## Next Action

Immediate:

1. Stop implementation unless a failed proof, stale evidence, or newly admitted exact provider-private/redacted artifact family appears.
2. If a new family is selected, write a separate freeze naming authority, routes, controls, rollback, and proof before implementation.
3. If a real connector or destination target is selected, start from target-selection authority rather than the local/fake provider-private handoff substrate.

Mid-term:

1. Keep provider-public URL, public proxy, real provider object operations, arbitrary connector dispatch, credentials, source expansion, RAG/vector/model runtime, Analysis Environment interactivity, frontend-only durable authority, and full mockup activation as blocked or intentionally excluded unless separately frozen.
2. Re-run the bounded operator runbook after any operator-path change.
3. Record current-main sync only when it closes a named proof gap or materially refreshes readiness evidence.

Long-term:

1. Maintain server-authoritative provider-private/redacted delivery lifecycle coverage for every admitted package/handoff family.
2. Keep every critical mockup journey classified as live, read-only, intentionally excluded, or blocked from current-main evidence.
3. Admit broader activation only after a separate readiness audit proves each requirement and blocker with direct current-main evidence.
