# Layer 3 Deployment Security Posture

## Purpose

This note tracks the current deployment/security posture for the Layer 3 workbench and adjacent FastAPI review surfaces. PR #319 froze the first non-local hardening governance boundary. PR #320 and PR #321 implemented the first startup/settings guardrail for that boundary. This note does not itself change runtime behavior and does not admit further route, schema, UI, connector, package, or export/download behavior.

## Current Repo-Confirmed Posture

- Local/dev remains the default posture: `DEPLOYMENT_MODE=local`, wildcard CORS origins, credentialed CORS, and direct `/storage` mounting preserve the existing proof-harness behavior.
- `backend/main.py` creates the FastAPI app and configures `CORSMiddleware` from `backend/app/core/config.py` settings instead of hardcoded CORS values.
- `backend/main.py` mounts `settings.storage_dir` at `/storage` with `StaticFiles` only when `settings.storage_mount_enabled` is true.
- `backend/main.py` mounts review UI static assets at `/review/nrc-aps/static` and `/review/layer3/static`.
- `backend/app/core/config.py` defaults `DATABASE_URL` to local SQLite under `backend/method_aware.db` and `STORAGE_DIR` to `backend/app/storage`, with `.env`-based overrides.
- `DEPLOYMENT_MODE=nonlocal` now fails closed unless `ALLOWED_ORIGINS` is an explicit HTTPS origin list, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, and `PROXY_IDENTITY_HEADER` is nonblank.
- In non-local mode, `CORS_ALLOW_CREDENTIALS` defaults to false unless explicitly configured, and direct app-owned `/storage` mounting is disabled by default.
- In non-local mode, `STORAGE_EXPOSURE=enabled` and `STORAGE_EXPOSURE=proxy_protected` are rejected because the app does not yet wrap `StaticFiles` with in-app auth.
- Current Layer 3 export/download delivery remains same-origin delivery over the existing validated APS evidence-bundle artifact. It does not create public or signed URLs.

## Current Admitted Use

Current repo evidence supports local/dev and proof-harness use by default. It also supports a first non-local startup/settings guardrail that rejects unsafe CORS, proxy-auth, and storage exposure posture at settings construction time. That guardrail does not, by itself, make the app safe for internet-facing or multi-user deployment.

## Remaining Decisions Before Non-Local Exposure

Before deploying beyond a trusted local/dev environment, choose and document:

1. The concrete allowed browser origin list for the target deployment and whether credentialed cross-origin requests are truly required.
2. Reverse-proxy authentication and authorization enforcement for `/api/v1`, `/review/*`, and any file-serving surface; the app currently requires proxy-owned posture but does not enforce in-app auth.
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
