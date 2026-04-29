# Layer 3 Non-Local Deployment Hardening Governance

Status: governance for the first non-local deployment hardening boundary. PR #319 is the governance-only packet. PR #320 and PR #321 implemented the first startup/settings guardrail.

This document does not admit additional runtime behavior by itself. It defines the smallest safe hardening slice to prepare the Layer 3 workbench and adjacent FastAPI review surfaces for any use beyond trusted local/dev proof, and records which part of that slice is now live.

## Current Evidence

Current main has a local/dev posture plus the first non-local settings guardrail documented in `docs/layer3-deployment-security.md`:

- `DEPLOYMENT_MODE=local` remains the default and preserves wildcard CORS with credentials plus direct `/storage` mounting for trusted local/dev proof.
- `DEPLOYMENT_MODE=nonlocal` requires explicit HTTPS `ALLOWED_ORIGINS`, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, and a nonblank `PROXY_IDENTITY_HEADER`.
- In non-local mode, `CORS_ALLOW_CREDENTIALS` defaults to false unless explicitly configured with exact origins.
- In non-local mode, direct app-owned `/storage` mounting is disabled by default, and `STORAGE_EXPOSURE=enabled` or `STORAGE_EXPOSURE=proxy_protected` fails closed.
- `backend/main.py` serves the review UI pages and static assets.
- `backend/app/core/config.py` defaults to local SQLite and local storage paths, with `.env` overrides.
- Layer 3 external export/download delivery is same-origin delivery of an existing validated APS evidence-bundle artifact, not public or signed URL behavior.

That posture supports local/dev and proof harness use by default, and it prevents several unsafe non-local startup configurations. It does not authorize internet-facing, multi-user, or sensitive-artifact deployment by itself because auth enforcement, concrete proxy/TLS deployment, secrets injection, artifact retention, and future file-delivery policy remain deployment-owned or separately governed.

## Selected First Boundary

The first non-local hardening slice is a deployment-profile guardrail:

> Preserve the current local/dev behavior by default, and require explicit non-local posture settings before the app can be treated as safe for non-local use.

PR #320 and PR #321 implemented this boundary as narrow configuration, startup validation, CORS/static mount wiring, and focused tests. The implementation does not introduce a product feature or change Layer 3 workflow behavior.

## Selected Defaults And Remaining Decisions

The first implementation uses these defaults:

1. **Deployment mode:** `DEPLOYMENT_MODE=local` by default; `DEPLOYMENT_MODE=nonlocal` selects the fail-closed profile.
2. **CORS:** non-local mode requires explicit HTTPS origins; wildcard origins are rejected. `CORS_ALLOW_CREDENTIALS` defaults to false in non-local mode unless explicitly configured.
3. **Authentication and authorization:** non-local mode requires `AUTH_OWNER=proxy`. `X-Forwarded-User` is the default required identity header, with `X-Forwarded-Email` and `X-Forwarded-Groups` available as optional header names.
4. **Storage exposure:** non-local mode disables direct `/storage` mounting by default and rejects `enabled` or `proxy_protected` app mounts.
5. **Proxy/TLS:** non-local mode requires `TRUSTED_PROXY_MODE=true`; HTTPS termination and forwarded-header enforcement remain trusted-proxy owned.
6. **Secrets:** settings remain environment-injected; no deployment secrets are embedded in the repo.
7. **Artifacts and retention:** artifact retention and logging policy remain deployment/storage-owned in this first slice.

Remaining deployment decisions before broader non-local exposure:

- concrete production origin list;
- reverse-proxy authentication and authorization policy;
- proxy/TLS/forwarded-header enforcement outside the app process;
- secrets/config injection mechanism for the selected deployment target;
- artifact retention, logging, and file-delivery policy;
- whether any future application-owned auth middleware or authorized file delivery should be separately governed.

## Proxy-Owned Non-Local Profile Decision Packet

Use this packet before any further deployment-hardening implementation. It records the concrete choices the deployment owner must make without inventing repo-local production values.

### Required Operator Choices

1. **Allowed browser origins:** replace the placeholders with exact HTTPS origins for the deployed review UI/API clients. Do not use `*`.
2. **Credentialed CORS:** keep `CORS_ALLOW_CREDENTIALS=false` unless a later cookie/session-auth design is explicitly selected and governed.
3. **Auth owner:** keep `AUTH_OWNER=proxy`; the app currently requires proxy-owned posture but does not enforce in-app authorization.
4. **Identity header:** keep `PROXY_IDENTITY_HEADER=X-Forwarded-User` unless the proxy contract chooses another nonblank identity header name. The proxy must strip or overwrite client-supplied identity headers before forwarding to the app.
5. **Optional identity metadata:** configure `PROXY_EMAIL_HEADER` and `PROXY_GROUPS_HEADER` only if the proxy can supply trustworthy values; current app behavior names these headers but does not authorize requests from them.
6. **Proxy/TLS boundary:** terminate HTTPS at the trusted proxy and forward only from that proxy to the app. `TRUSTED_PROXY_MODE=true` is a posture declaration, not proof that the network path is protected.
7. **Storage exposure:** keep `STORAGE_EXPOSURE=auto` or `disabled`; non-local mode rejects direct and `proxy_protected` app-owned `/storage` mounts.
8. **Secrets/config injection:** inject deployment values through the environment or deployment secret manager. Do not commit production origins, secrets, signing keys, or connector credentials into the repo.
9. **Artifact retention/logging:** decide retention, audit logging, and storage ownership outside this first guardrail before exposing sensitive artifacts to non-local users.

### Minimal Non-Local Environment Shape

The following is a template, not a production configuration:

```text
DEPLOYMENT_MODE=nonlocal
ALLOWED_ORIGINS=https://review.example.invalid,https://ops.example.invalid
CORS_ALLOW_CREDENTIALS=false
AUTH_OWNER=proxy
PROXY_IDENTITY_HEADER=X-Forwarded-User
PROXY_EMAIL_HEADER=X-Forwarded-Email
PROXY_GROUPS_HEADER=X-Forwarded-Groups
TRUSTED_PROXY_MODE=true
STORAGE_EXPOSURE=auto
```

`STORAGE_EXPOSURE=auto` disables the direct `/storage` app mount in non-local mode. Use `STORAGE_EXPOSURE=disabled` when the deployment owner wants that policy to be explicit. Do not use `enabled` or `proxy_protected` in non-local mode; both fail closed.

### What This Proves

The current startup/settings guardrail proves that the app rejects several unsafe non-local configurations before startup use: wildcard or non-HTTPS origins, missing proxy-owned auth posture, missing trusted-proxy posture, blank identity header, and direct or proxy-protected app-owned storage exposure.

### What This Does Not Prove

This packet does not prove that the reverse proxy is correctly configured, that users are authenticated or authorized, that identity headers are stripped or overwritten by the proxy, that `/storage` is safely deliverable, that artifacts have a retention policy, or that public/signed URLs are available. Those remain separate deployment or product decisions.

## Implemented Guardrail

The implemented startup/settings guardrail:

- adds explicit deployment-mode settings with local/dev as the backward-compatible default;
- makes CORS configurable and fail closed for non-local wildcard origins;
- gates direct `/storage` exposure behind local/default behavior and non-local fail-closed validation;
- adds startup/settings validation for missing non-local proxy-auth and trusted-proxy posture;
- keeps required environment values external to the repo;
- adds focused tests proving local/dev behavior remains unchanged and non-local posture fails closed when required settings are missing.

## Explicit Non-Goals

This governance packet and the implemented first guardrail do not admit:

- public or signed URL generation;
- browser download behavior beyond the already-live same-origin delivery control;
- connector dispatch, destination selection, or generic downstream dispatch;
- package mutation, rebuild, amendment, or supersession;
- schema, model, migration, runtime, or source widening;
- new `AnalysisArtifact`, package, reconciliation, or connector-run row families;
- qualitative, hybrid, RAG, vector, or full mockup activation;
- changing Layer 3 API semantics, UI workflows, APS handoff behavior, or export/download package behavior;
- deploying to a specific provider or embedding deployment secrets in the repo.

## Proof Status And Future Requirements

PR #320 and PR #321 added focused tests proving:

- default local/dev proof behavior still works without new required production settings;
- non-local mode rejects wildcard or non-HTTPS origins;
- non-local mode requires proxy-owned auth posture and trusted proxy mode;
- non-local mode disables direct app-owned `/storage` by default and rejects direct or proxy-protected `StaticFiles` exposure;
- no Layer 3 workflow state, package payload, export/download, connector, schema, or UI behavior changes are introduced by the posture guardrail.

Future implementation slices must add their own proof for any new auth middleware, authorized file delivery, proxy integration, public/signed URL behavior, provider-specific deployment settings, or artifact retention/logging behavior.

## Stop Conditions

Stop and return to governance if implementation requires:

- selecting a production domain, identity provider, or hosting platform not already decided;
- public/signed download URLs;
- connector dispatch or destination selection;
- package mutation or reconstruction;
- schema/runtime/source widening;
- broad auth middleware redesign;
- secrets or credentials unavailable in the repo/test environment.
