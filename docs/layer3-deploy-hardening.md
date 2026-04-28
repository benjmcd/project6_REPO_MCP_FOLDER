# Layer 3 Non-Local Deployment Hardening Governance

Status: planning-only governance for the first non-local deployment hardening boundary.

This document admits no runtime behavior by itself. It defines the smallest safe hardening slice to prepare the Layer 3 workbench and adjacent FastAPI review surfaces for any use beyond trusted local/dev proof.

## Current Evidence

Current main has a local/dev posture documented in `docs/layer3-deployment-security.md`:

- `backend/main.py` configures wildcard CORS with credentials.
- `backend/main.py` directly mounts `settings.storage_dir` at `/storage`.
- `backend/main.py` serves the review UI pages and static assets.
- `backend/app/core/config.py` defaults to local SQLite and local storage paths, with `.env` overrides.
- Layer 3 external export/download delivery is same-origin delivery of an existing validated APS evidence-bundle artifact, not public or signed URL behavior.

That posture supports local/dev and proof harness use only. It does not authorize internet-facing, multi-user, or sensitive-artifact deployment.

## Selected First Boundary

The first non-local hardening slice is a deployment-profile guardrail:

> Preserve the current local/dev behavior by default, and require explicit non-local posture settings before the app can be treated as safe for non-local use.

A later implementation governed by this note may add only narrow configuration, startup validation, and tests needed to fail closed for a non-local deployment profile. It must not introduce a product feature or change Layer 3 workflow behavior.

## Required Decisions

Before implementation, the deployment owner must choose concrete values or policies for:

1. **CORS:** allowed browser origins; wildcard origins with credentials must not be the non-local posture.
2. **Authentication and authorization:** whether auth is enforced in-app or by a trusted reverse proxy for `/api/v1`, `/review/*`, and any file-serving surface.
3. **Storage exposure:** whether `/storage` is disabled, left local-only, or replaced by an authorized delivery path in non-local mode.
4. **Proxy/TLS:** whether the app is behind a trusted proxy, how HTTPS is terminated, and which forwarded headers are trusted.
5. **Secrets:** how connector/API credentials, future signing keys, and deployment secrets are injected and validated.
6. **Artifacts and retention:** sensitivity, retention, and logging policy for APS bundles, package payloads, downloads, reports, and operator decisions.

## Future Implementation Allowance

A later implementation PR may:

- add explicit deployment-mode settings with local/dev as the backward-compatible default;
- make CORS configurable and fail closed for non-local wildcard credentialed CORS;
- gate direct `/storage` exposure behind an explicit local-only or non-local storage policy;
- add startup validation for missing non-local auth/proxy/TLS/secret posture decisions;
- document required environment variables for the selected deployment profile;
- add focused tests proving local/dev behavior remains unchanged and non-local posture fails closed when required settings are missing.

## Explicit Non-Goals

This governance packet does not admit:

- public or signed URL generation;
- browser download behavior beyond the already-live same-origin delivery control;
- connector dispatch, destination selection, or generic downstream dispatch;
- package mutation, rebuild, amendment, or supersession;
- schema, model, migration, runtime, or source widening;
- new `AnalysisArtifact`, package, reconciliation, or connector-run row families;
- qualitative, hybrid, RAG, vector, or full mockup activation;
- changing Layer 3 API semantics, UI workflows, APS handoff behavior, or export/download package behavior;
- deploying to a specific provider or embedding deployment secrets in the repo.

## Proof Requirements

A future implementation must prove:

- default local/dev proof behavior still works without new required production settings;
- non-local mode rejects wildcard credentialed CORS;
- non-local mode refuses direct storage exposure unless the selected policy explicitly allows a safe path;
- API/review/storage auth assumptions are explicit and tested or documented as reverse-proxy-owned;
- no Layer 3 workflow state, package payload, export/download, connector, schema, or UI behavior changes are introduced by the posture guardrail.

## Stop Conditions

Stop and return to governance if implementation requires:

- selecting a production domain, identity provider, or hosting platform not already decided;
- public/signed download URLs;
- connector dispatch or destination selection;
- package mutation or reconstruction;
- schema/runtime/source widening;
- broad auth middleware redesign;
- secrets or credentials unavailable in the repo/test environment.
