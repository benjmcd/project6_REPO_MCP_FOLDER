# Layer 3 Deployment Security Posture

## Purpose

This note tracks the current deployment/security posture for the Layer 3 workbench and adjacent FastAPI review surfaces. PR #319 froze the first non-local hardening governance boundary. PR #320 and PR #321 implemented the first startup/settings guardrail for that boundary. This note does not itself change runtime behavior and does not admit further route, schema, UI, connector, package, or export/download behavior.

## Current Repo-Confirmed Posture

- Local/dev remains the default posture: `DEPLOYMENT_MODE=local`, wildcard CORS origins, credentialed CORS, and direct `/storage` mounting preserve the existing proof-harness behavior.
- `backend/main.py` creates the FastAPI app and configures `CORSMiddleware` from `backend/app/core/config.py` settings instead of hardcoded CORS values.
- `backend/main.py` mounts `settings.storage_dir` at `/storage` with `StaticFiles` only when `settings.storage_mount_enabled` is true.
- `backend/main.py` mounts review UI static assets at `/review/nrc-aps/static` and `/review/layer3/static`.
- `backend/app/core/config.py` defaults `DATABASE_URL` to local SQLite under `backend/method_aware.db` and `STORAGE_DIR` to `backend/app/storage`, with `.env`-based overrides.
- `DEPLOYMENT_MODE=nonlocal` now fails closed unless `ALLOWED_ORIGINS` is an explicit HTTPS origin list, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, and `PROXY_IDENTITY_HEADER` is nonblank. When `LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing`, `PROXY_ROLES_HEADER` must also be nonblank.
- Four new env knobs govern route-level role authorization: `LAYER3_ROUTE_AUTHORIZATION_MODE` (default `identity_presence`; `role_enforcing` activates role checks), `PROXY_ROLES_HEADER` (default `X-Forwarded-Roles`), `LAYER3_OWNER_ROLE_TOKENS` (default `owner`), `LAYER3_AUDITOR_ROLE_TOKENS` (default `auditor`). All have safe defaults and are inert unless `role_enforcing` is selected. See `docs/layer3-route-authorization.md`.
- In non-local mode, `CORS_ALLOW_CREDENTIALS` defaults to false unless explicitly configured, and direct app-owned `/storage` mounting is disabled by default.
- In non-local mode, `STORAGE_EXPOSURE=enabled` and `STORAGE_EXPOSURE=proxy_protected` are rejected because the app does not yet wrap `StaticFiles` with in-app auth.
- In proxy-owned non-local posture, the route-level operator-identity seam now fails closed before service logic on Layer 3 core workbench, handoff, package, source-ingestion, and source/sec-edgar routes (read and write access classes per route semantics); all 23 NRC APS review API GET routes (access="read"); all 45 legacy dataset/connector routes in `router.py` (read/write per route semantics); and GET `/sec-xbrl/runtime/posture` (access="read"). The `/api/v1/sources/upload` route is also enrolled in the pre-body identity middleware. The seam is inert under the local default profile. The public metadata GETs `/bootstrap`, `/readiness`, and `/authority-matrix`, the root `/` and `/health` probes, and the fail-soft `/sec-xbrl/identity/projection` route remain explicitly exempt. Static and UI surfaces, `/docs`, and `/openapi.json` remain reverse-proxy-owned.
- Current Layer 3 export/download delivery remains same-origin delivery over the existing validated APS evidence-bundle artifact. It does not create public or signed URLs.

## Current Admitted Use

Current repo evidence supports local/dev and proof-harness use by default. It also supports a first non-local startup/settings guardrail that rejects unsafe CORS, proxy-auth, and storage exposure posture at settings construction time. That guardrail does not, by itself, make the app safe for internet-facing or multi-user deployment.

## Remaining Decisions Before Non-Local Exposure

Before deploying beyond a trusted local/dev environment, choose and document:

1. The concrete allowed browser origin list for the target deployment and whether credentialed cross-origin requests are truly required.
2. Reverse-proxy authentication and authorization enforcement for `/api/v1`, `/review/*`, and any file-serving surface; the app requires proxy-owned posture. Route-level operator-identity is now enforced in-app for the full Layer 3 core-workbench/handoff/package/source_ingestion/source-sec-edgar surface, all 23 NRC APS review API GET routes, all 45 legacy dataset/connector routes, and GET `/sec-xbrl/runtime/posture`: fail-closed under proxy posture, inert under local default. Identity-presence is the active default (`LAYER3_ROUTE_AUTHORIZATION_MODE=identity_presence`); role enforcement (`role_enforcing`) exists but is opt-in. See `docs/layer3-route-authorization.md` for mode flag semantics, role model, and coverage details. Public metadata GETs stay open; static/UI surfaces, `/docs`, `/openapi.json`, and reverse-proxy authn/authz remain deployment-owned.
3. Whether future file delivery should remain disabled in-app, move behind authorized application delivery, or use a separately governed public/signed URL design.
4. Artifact sensitivity and retention rules for APS evidence bundles, Layer 3 package payloads, downloads, logs, and reports.
5. Deployment proxy/TLS/header assumptions, including whether the app runs behind a trusted reverse proxy.
6. Secret handling for connector/API credentials and any future production environment variables.
7. Audit/logging expectations for download delivery and operator decisions.

## Hard Non-Goals

- No public or signed URL generation.
- No connector dispatch.
- No destination selection.
- No generic downstream dispatch.
- No package mutation, rebuild, amendment, or supersession.
- No schema, model, migration, runtime, or source widening.
- No qualitative, hybrid, RAG, vector, or full mockup activation.
- No additional CORS, auth middleware, static mount, route, UI, or storage behavior change by this note.

## Acceptance Criteria For Future Hardening Slices

The first startup/settings guardrail is live through PR #320 and PR #321. Any future implementation may proceed only after the next slice is separately governed. The narrow hardening contract should state the target environment, exact changed settings/routes/middleware, backward-compatible local proof behavior, focused API/static-delivery tests, and rollback expectations.

The first selected governance boundary for that work is `docs/layer3-deploy-hardening.md`. PR #319 is the governance-only packet; PR #320 and PR #321 are the separate implementation of the startup/settings guardrail.
