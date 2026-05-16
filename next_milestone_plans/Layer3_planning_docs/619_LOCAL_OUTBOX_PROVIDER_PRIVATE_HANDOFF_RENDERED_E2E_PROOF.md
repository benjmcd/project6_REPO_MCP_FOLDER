# 619 Local-Outbox Provider-Private Handoff Rendered E2E Proof

Status: focused rendered E2E proof for the local-outbox provider-private handoff lifecycle.

Current-main checkpoint at proof entry: `5b243b147adb1f186547bb5a6b0681be257af367`.

Document: `619_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_RENDERED_E2E_PROOF.md`.

Branch: `codex/l3-local-outbox-provider-private-e2e`.

Owner proof: `e2e/layer3-workbench.spec.js`.

## Authority

Canonical runtime authority already lives in:

- `backend/app/services/layer3_local_outbox_provider_private_handoff.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`

Rendered read-only authority already lives in:

- `backend/app/review_ui/static/layer3.js`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`

Planning/control authority remains:

- `612_TARGET_SELECTION_INTAKE.md`
- `613_LAYER3_OBJECTIVE_COMPLETION_AUDIT_AFTER_TARGET_SELECTION_INTAKE.md`
- `614_TARGET_SELECTION_VALIDATE_ONLY_GUARD.md`
- `615_TARGET_SELECTION_VALIDATE_ONLY_GUARD_CURRENT_MAIN_SYNC.md`
- `616_TARGET_SELECTION_FIELD_CONTRACT.md`
- `617_TARGET_SELECTION_STRUCTURED_RECORD_VALIDATOR.md`
- `618_TARGET_SELECTION_VALIDATOR_CLI.md`

The selected real target remains `null`, `selection_complete` remains `false`, and this proof does not alter the target-selection gate.

## Proof Scope

This pass extends the existing rendered external export/download delivery E2E path through the local receipt lifecycle:

Proof focus: local-outbox provider-private prepare/status after server-owned local outbox write.

1. APS download readiness.
2. Connector dispatch record.
3. Local fake receipt.
4. Server-owned fake target record.
5. Server-owned local outbox write.
6. Local-outbox provider-private prepare.
7. Local-outbox provider-private status.
8. Session-summary refresh and rendered read-only status/history/audit/idempotency/blocked-runtime projection in `#local-outbox-provider-private-handoff-panel`.

The focused test helper is `recordRenderedLocalOutboxProviderPrivateHandoffSmoke`.

The rendered E2E calls only these local/fake endpoints after existing handoff/export readiness:

- `/api/v1/layer3/handoff/connector/local-receipt`
- `/api/v1/layer3/handoff/connector/local-target`
- `/api/v1/layer3/handoff/connector/local-outbox/write`
- `/api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare`
- `/api/v1/layer3/handoff/connector/local-outbox/provider-private/status/{receipt_id}`

## Required Rendered Assertions

The E2E proof must assert all of the following:

- `#server-owned-local-outbox-write-panel` is read-only before and after the write.
- `#local-outbox-provider-private-handoff-panel` is read-only before and after prepare/status.
- The server-owned local outbox write reaches `server_owned_local_outbox_write_recorded`.
- The provider-private handoff reaches `local_outbox_provider_private_handoff_prepared`.
- The latest provider-private handoff receipt is redacted.
- The rendered handoff panel shows `Handoff History`.
- The rendered handoff panel shows `Audit History`.
- The rendered handoff panel shows `same key conflict: local_outbox_provider_private_handoff_client_request_conflict`.
- The rendered handoff panel shows `raw token replay: blocked`.
- The rendered handoff panel shows `provider private use route: blocked`.
- The rendered handoff panel shows `real connector invocation: blocked`.
- No raw provider-private token, provider signature, credential, destination address, connector run, connector target, provider-public delivery, or provider-public use is exposed in the response or rendered summary.

## Validation

Headless proof:

```powershell
$env:CI='0'
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench drives raw mixed rendered external export download delivery"
```

Observed result on this branch: `1 passed`.

Headed proof:

```powershell
$env:CI='0'
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench drives raw mixed rendered external export download delivery"
```

Observed result on this branch: `1 passed`.

`node --check .\e2e\layer3-workbench.spec.js` is not a valid gate for this repo because the package is configured as CommonJS while Playwright specs use top-level `import`.

## Non-Admission Boundary

This proof admits no real connector invocation.

This proof admits no destination write.

This proof admits no `ConnectorRun` or `ConnectorRunTarget` creation.

This proof admits no credentials.

This proof admits no provider-public delivery or provider-public use.

This proof admits no raw provider-private token use route.

This proof admits no raw token persistence or rendered token exposure.

This proof admits no provider network call, object-store write, or public proxy behavior.

This proof admits no package mutation or package reconstruction.

This proof admits no source expansion.

This proof admits no RAG/vector behavior.

This proof admits no auth/security runtime change.

This proof admits no full mockup durable workflow activation.

This proof admits no frontend-durable authority.

## Future Steps

Immediate next pass:

1. Keep doc `612_TARGET_SELECTION_INTAKE.md` pending until an operator names exactly one real connector or destination target.
2. Use `tools/l3-target-selection-validate.py --expect pending` to prove current-main target selection is still pending.
3. Keep local/fake lifecycle hardening bounded to existing receipt, status, history, audit, stale-authority, idempotency, retry, and failure-state semantics.

Mid-term passes after a target is named:

1. Validate a completed selected-state copy of doc `612_TARGET_SELECTION_INTAKE.md`.
2. Write a separate implementation-entry freeze for exactly one named connector or destination target.
3. Define the target's server authority, side-effect boundary, idempotency key, retry/failure lifecycle, credential model, receipt/audit contract, and rendered operator proof.
4. Implement only the named target slice.
5. Prove the named target with focused API tests and headed/headless rendered E2E tests.
6. Keep provider-public delivery/use, package mutation, source expansion, RAG/vector, broad auth/security, full mockup activation, and frontend-durable authority blocked unless separately frozen and admitted.

Long-term milestone path:

1. Complete the local receipt and local-outbox lifecycle as the stable handoff substrate.
2. Admit one real external target only through an operator-filled target selection plus separate freeze.
3. Add any provider-public delivery/use only after exposure/security/public-access authority is defined.
4. Add package mutation/reconstruction only after a named operator package action is selected.
5. Add source expansion only one named source family at a time.
6. Add RAG/vector only after source/index authority is defined.
7. Tie auth/security hardening to the first external surface that becomes real.
8. Preserve the active Layer 3 objective as incomplete until server-owned source/intake, durable ledger/workspace state, pass orchestration, package generation, local and admitted external handoff lifecycles, operator-visible surfaces, focused proof, and current-main control artifacts all close without pending target gates.
