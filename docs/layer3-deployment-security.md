# Layer 3 Deployment Security Posture

## Purpose

This note freezes the current deployment/security posture for the Layer 3 workbench and adjacent FastAPI review surfaces. It is a governance note only. It does not change runtime behavior, CORS, auth, storage mounts, routes, schemas, UI, connector behavior, package behavior, or export/download behavior.

## Current Repo-Confirmed Posture

- `backend/main.py` creates the FastAPI app and configures `CORSMiddleware` with `allow_origins=['*']`, `allow_credentials=True`, `allow_methods=['*']`, and `allow_headers=['*']`.
- `backend/main.py` mounts `settings.storage_dir` at `/storage` with `StaticFiles`.
- `backend/main.py` mounts review UI static assets at `/review/nrc-aps/static` and `/review/layer3/static`.
- `backend/app/core/config.py` defaults `DATABASE_URL` to local SQLite under `backend/method_aware.db` and `STORAGE_DIR` to `backend/app/storage`, with `.env`-based overrides.
- Current Layer 3 export/download delivery remains same-origin delivery over the existing validated APS evidence-bundle artifact. It does not create public or signed URLs.

## Current Admitted Use

Current repo evidence supports local/dev and proof-harness use. It does not, by itself, authorize internet-facing or multi-user deployment with sensitive artifacts exposed through the current wildcard CORS and `/storage` static mount posture.

## Required Decision Before Non-Local Exposure

Before deploying beyond a trusted local/dev environment, choose and document:

1. Allowed browser origins and whether credentialed cross-origin requests are needed.
2. Authentication and authorization for `/api/v1`, `/review/*`, and `/storage`.
3. Whether `/storage` should remain directly mounted, move behind authorized file delivery, or be disabled in non-local mode.
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
- No CORS, auth, static mount, route, UI, or storage behavior change by this note.

## Acceptance Criteria For A Future Hardening Slice

A future implementation may proceed only after the deployment mode is selected and the slice is separately governed. The narrow hardening contract should state the target environment, exact changed settings/routes/middleware, backward-compatible local proof behavior, focused API/static-delivery tests, and rollback expectations.

The first selected governance boundary for that work is `docs/layer3-deploy-hardening.md`. It freezes a planning-only deployment-profile guardrail for non-local use and still does not change runtime behavior by itself.
