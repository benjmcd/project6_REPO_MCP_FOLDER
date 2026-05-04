# Layer 3 Signed Reference UI Freeze

## Status

Branch-local implementation-entry freeze for the rendered `/review/layer3` signed-reference control after PR `#499` backend/API same-origin signed-reference generation/use and PR `#513` Claude theme APS content-document trace alignment.

This freeze admits only an operator-visible same-origin signed-reference control over the existing PR `#499` endpoints:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`

It does not admit public URLs, provider-specific URLs, connector dispatch, destination selection, generic downstream dispatch, durable token/receipt/audit/revocation state, schema/model/migration/runtime/source widening, package mutation, qualitative execution, hybrid/RAG/vector behavior, or full mockup activation.

## Source Of Truth

Use this authority order:

1. current `project6-origin/main` source/tests;
2. PR `#499` backend/API signed-reference behavior;
3. docs `102`/`103` signed-reference governance;
4. PR `#487` rendered delivery UI gate behavior;
5. docs `100`/`101` rendered delivery gate governance;
6. PR `#513` UI/theme trace alignment for current `/review/layer3` related theme surfaces;
7. this branch-local freeze for the rendered signed-reference control only.

Browser state and copied token text are never authority for artifact identity, expiry, replay policy, downstream enablement, package mutation, or delivery availability.

## Admitted UI Behavior

The rendered UI may:

- show a signed-reference panel under External Export / Download;
- enable generation only after recorded external export/download readiness and explicit server delivery UI authority;
- call only the existing same-origin signed-reference generation endpoint;
- display token prefix, expiry, artifact hash/ref basis, TTL, and disabled downstream flags;
- enable signed-reference use only after a server-generated ready token exists;
- call only the existing signed-reference use endpoint with `{ signed_reference_token }`;
- display use-result headers/state without creating public/provider URLs or connector/destination state.
- keep generation one-shot for the loaded UI state after a token is present, so the rendered control is not a refresh/revoke/share workflow.

The UI must not:

- construct, copy, expose, or claim a public/provider URL;
- treat the token as durable, revocable, one-time-use, or audited state;
- add retry/recovery/rerun/cancel controls;
- add connector, destination, generic dispatch, or package mutation controls;
- expand source ingestion, qualitative execution, hybrid/RAG/vector execution, schema/model/migration behavior, or runtime DB writes.

## Implementation Requirements

The implementation must be narrow:

- edit only the existing Layer 3 static UI and targeted UI tests unless a repo-confirmed blocker proves otherwise;
- reuse `externalExportDownloadDeliveryPayload(...)` as the signed-reference generation payload so forbidden fields remain absent;
- use a separate use payload containing only `signed_reference_token`;
- preserve existing same-origin delivery controls and PR `#487` delivery UI admission checks;
- fail closed when the server rejects generation/use, including missing `LAYER3_SIGNED_REFERENCE_SECRET`;
- keep all public/provider/connector/destination/durable-state labels visibly disabled or blocked.

## Proof Requirements

Minimum proof:

- static FastAPI page test confirms rendered controls and JS route use;
- Playwright headless and headed proof confirms blocked-to-enabled gate behavior, generation request payload exclusions, and token-only use request;
- existing Layer 3 API tests continue to pass for PR `#499` signed-reference backend/API behavior;
- `npm run validate:structure` and `git diff --check` pass.
