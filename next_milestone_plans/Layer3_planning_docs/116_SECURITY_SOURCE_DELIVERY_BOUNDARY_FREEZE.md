# Layer 3 Security / Source / Delivery Boundary Freeze

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- authority_commit: `4d2bac8f68e52f7205210d19cce64576dc0384c4`
- baseline_ref: `project6-origin/main`
- baseline_check: PR `#533` merged at `4d2bac8f68e52f7205210d19cce64576dc0384c4`; local `git log -1 project6-origin/main` identified that commit as the PR `#533` merge and `git merge-base --is-ancestor 7c26c483426e443a584329276e48be9d5a0941d5 project6-origin/main` confirmed the implementation commit is merged.
- working_tree_caveat: pre-existing local operator/tooling state is present in `.omc/state/hud-state.json` and `.omc/state/hud-stdin-cache.json`; approved local sidecars are also present (`.codesight/`, `.cursorrules`, `.github/copilot-instructions.md`, `CLAUDE.md`, `codex.md`). These are not treated as implementation evidence.
- slice_mode: planning/docs-only boundary freeze. No runtime code, backend tests, frontend assets, models, migrations, generated artifacts, or database state are changed by this boundary document; progress/control manifests and validate-only progress checkers may be updated by separate progress-sync lanes.
- near_term_direction: remaining authentication/security work is intentionally deferred. This artifact records boundaries and blockers only; it is not a recommendation to implement auth, proxy proof, upload security, or delivery-security hardening next.

## Evidence Boundary

This freeze uses only local repo files, local audit outputs, and local filesystem evidence. It does not rely on GitHub, remote checks, browser runtime proof, deployment operator claims, or prior-session conclusions unless those claims are supported by local files.

Evidence inspected for this freeze:

- `backend/app/core/config.py`
- `backend/main.py`
- `backend/app/api/router.py`
- `backend/app/api/layer3.py`
- `backend/app/api/deps.py`
- `backend/app/services/ingest.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_signed_reference_state.py`
- `backend/tests/test_layer3_api.py`
- local audit synthesis in `C:\Users\benny\Downloads\audit\repo_audits\synthesis-adjudication-2026-05-05.md`

Authority hierarchy for this document:

1. Repo-live code and tests in the target worktree.
2. Local audit outputs only where they cite files, commands, or proof.
3. Progress/proof manifests only as scoped historical artifacts.
4. Planning docs and mockups only as planning/target-state material.
5. Inference only when explicitly marked.

## Repo-Live Security Boundary

Repo-live code contains deployment-profile guardrails but does not prove in-app request authentication.

Repo-confirmed facts:

- `backend/app/core/config.py` defines `DEPLOYMENT_MODE`, `AUTH_OWNER`, `TRUSTED_PROXY_MODE`, `PROXY_IDENTITY_HEADER`, and `STORAGE_EXPOSURE`.
- In nonlocal mode, settings validation requires explicit HTTPS origins, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, and a non-empty proxy identity header.
- `backend/tests/test_layer3_api.py` includes a deployment-profile test asserting nonlocal proxy-owned guardrails.
- Local inspection did not find FastAPI request-auth dependencies or authentication middleware on the app/router surface. The only `Authorization` hit in the inspected app code was for the Senate LDA connector client, not an inbound operator-auth boundary.

Accepted wording:

> The repo requires a proxy-owned trust posture for nonlocal deployment configuration, but the inspected local code does not itself authenticate individual inbound Layer 3 or upload requests. Operator identity and access control must therefore be either enforced by an external trusted proxy or implemented in a later in-app auth slice before nonlocal exposure.

Rejected wording:

> Layer 3 is authenticated by repo-live FastAPI code.

Reason for rejection: Codesight-style `[auth]` route tags or config fields do not prove inbound request authentication.

## Assumed External Boundary

Any nonlocal deployment currently depends on an external trusted proxy boundary unless a later implementation slice adds explicit in-app auth.

Required assumptions before nonlocal exposure:

- The proxy authenticates the operator before requests reach FastAPI.
- The proxy supplies a trustworthy identity header matching `PROXY_IDENTITY_HEADER`.
- The proxy prevents direct bypass to FastAPI.
- The proxy owns TLS termination and origin restrictions.
- The deployment does not expose `/storage` directly when `DEPLOYMENT_MODE=nonlocal`.

This document does not prove those assumptions are true in any live deployment. It only records that repo-live config expects the proxy-owned posture in nonlocal mode.

Merge/blocker rule:

- Any future claim that Layer 3 is safe for nonlocal/public operator use must include proof of one of:
  - an external trusted proxy boundary; or
  - a repo-live in-app auth implementation with negative anonymous-request tests.

## Source Ingest Boundary

`/sources/upload` is a source-ingest boundary and must not be treated as a casual helper route.

Repo-confirmed facts:

- `backend/app/api/router.py` exposes `POST /sources/upload`.
- The route accepts `UploadFile`, `name`, optional `description`, optional `domain_pack`, and optional `primary_time_column`.
- The route delegates to `upload_csv_to_dataset(db, file, name, description, domain_pack, primary_time_column)`.
- Local inspection did not find an inbound operator-auth dependency on that route.

Accepted wording:

> `/sources/upload` is a protected source-ingest boundary. Before nonlocal exposure, it needs either an externally proven auth/proxy boundary or a later in-app auth/upload-hardening slice.

This freeze does not implement upload hardening. It blocks overclaims that current repo-live Layer 3 source trust already covers arbitrary uploaded sources.

Required future proof before broad upload/source expansion:

- authenticated or proxy-proven operator identity;
- content-type and size policy;
- filename/path sanitization;
- domain-pack allowlist policy;
- source provenance persisted in a way downstream Layer 3 can audit;
- negative tests for disallowed content and oversized input.

## Signed-Reference Boundary

Repo-live signed references provide same-origin delivery reference integrity and durable lifecycle state. They do not prove requester authorization by themselves.

Repo-confirmed facts:

- `backend/app/services/layer3_signed_reference_state.py` defines single-use token states: `ready`, `used`, `revoked`, and `expired`.
- Signed-reference state records use `L3SignedReferenceToken`, `L3SignedReferenceReceipt`, `L3SignedReferenceRevocation`, and `L3SignedReferenceAuditEvent`.
- `record_generated_signed_reference()` and `record_used_signed_reference()` use durable token rows and row locking via `.with_for_update()`.
- `backend/app/services/layer3_workbench.py` requires `LAYER3_SIGNED_REFERENCE_SECRET` before signed-reference generation/use can succeed.
- `backend/tests/test_layer3_api.py` has integration coverage for missing secret, generate, use, replay denial, expiry, headers, receipt/audit rows, and same-origin no-public-url assertions.

Accepted wording:

> Same-origin signed-reference delivery is repo-live and fail-closed around token integrity, durable state, replay policy, and artifact binding. It does not authenticate who may request token generation or use unless an external proxy or later in-app auth slice supplies that boundary.

Rejected wording:

> HMAC signed references make the Layer 3 delivery API authenticated.

Reason for rejection: HMAC validates the token/reference and server-side authority basis. It is not, by itself, proof of requester identity or permission to request token generation.

Proof gap preserved:

- Dedicated service-level tests for revocation and concurrent double-use are still needed.
- Provider/public URL support remains blocked.
- Connector/destination dispatch remains blocked.

## Same-Origin Delivery Boundary

Current delivery authority is same-origin and bounded.

Repo-confirmed facts:

- Signed-reference integration tests assert `public_url_enabled` is `False`.
- Signed-reference integration tests assert `connector_dispatch_enabled`, `destination_selection_enabled`, and `generic_downstream_dispatch_enabled` are `False`.
- Signed-reference integration tests assert forbidden public delivery fields such as `download_url`, `public_url`, `signed_url`, and `connector_run_id` are absent from the signed-reference response/headers.

Accepted wording:

> Current delivery is same-origin only. Public/provider URLs and generic connector/destination dispatch are not admitted by this freeze.

## Explicit No-Go Capabilities

The following remain unavailable and must not be activated by this slice:

- broad execution
- broad qualitative execution outside the admitted single APS-document qualitative pass
- hybrid execution
- RAG retrieval
- vector retrieval
- local upload as a Layer 3 source expansion
- local directory ingestion
- broad source expansion
- provider URL support
- public URL support
- connector dispatch
- destination dispatch
- generic downstream dispatch
- `L3PassRun` creation
- `AnalysisRun` creation
- output artifact creation
- package artifact creation
- handoff artifact creation
- export artifact creation
- package mutation
- package reconstruction
- full mockup activation
- hidden LLM planning
- frontend-only durable state
- runtime schema/source widening
- destructive cleanup

If any later implementation changes one of these items, it must first pass through a separate admitted freeze/contract slice with explicit proof requirements.

## Merge / Next-Slice Blockers

Block before claiming nonlocal/public readiness:

- no proof of trusted proxy enforcement and no in-app auth implementation;
- `/sources/upload` reachable without a proven operator boundary;
- signed-reference generation/use expanded beyond same-origin delivery;
- provider/public URL fields enabled;
- connector/destination dispatch enabled;
- source expansion beyond `dataset_version` and `aps_content_document`;
- broad qualitative/hybrid/RAG execution enabled outside the admitted single APS-document qualitative pass;
- package mutation/reconstruction enabled;
- hidden LLM planning introduced into any Layer 3 decision path.

Block before signed-reference scope expansion:

- no dedicated revocation test;
- no concurrent double-use/replay test;
- no explicit authorization boundary for token generation;
- no deployment runbook for `LAYER3_SIGNED_REFERENCE_SECRET`.

Block before upload/source expansion:

- no operator identity boundary;
- no source provenance contract;
- no content-type/size/name guard tests;
- no fail-closed behavior for unsupported source classes.

## Allowed Next Slices

Allowed near-term next slices are narrow and proof-oriented, but not authentication/security work. PR `#531` already merged Gate B post-commit retry idempotency and material-preview hash hardening, and PR `#533` already merged server-derived `state_action_contract` hardening; do not treat either exact slice as still unstarted or branch-only after the post-PR533 sync.

1. Gate B idempotency/hash follow-up only if fresh proof finds a missed edge after merged PR `#531`.
2. Frontend server-contract consumption, session recovery, and Gate B draft-loss hardening.
3. State/action contract drift checker only if fresh proof shows post-PR533 contract drift.
4. Preview hash/idempotency contract hardening beyond merged PR `#531` only if evidence warrants it.
5. Progress/proof/state drift checker.
6. No-behavior-change service extraction if scoped to reducing `layer3_workbench.py` risk without changing runtime behavior.
7. CI expansion only for non-security Layer 3 state/idempotency/proof coverage.

Not allowed as immediate next slices from this freeze:

- in-app auth implementation;
- external proxy proof harness;
- upload security hardening;
- signed-reference revocation/concurrency/security hardening;
- `LAYER3_SIGNED_REFERENCE_SECRET` deployment/runbook work;
- provider/public URL implementation;
- connector/destination dispatch;
- broad upload/source expansion;
- broad qualitative/hybrid/RAG execution;
- package mutation/reconstruction;
- full mockup activation.

## Validation Commands

Run from `C:\Users\benny\Downloads\worktree_for_audits`.

Authority check:

```powershell
git status --short
git rev-parse HEAD
git rev-parse project6-origin/main
git diff --name-status HEAD project6-origin/main
```

Inbound auth inspection:

```powershell
Select-String -Path .\backend\app\**\*.py -Pattern 'HTTPBearer|OAuth2|Authorization|require_authenticated|get_current_user|AuthenticationMiddleware|APIKeyHeader|Security\(' -CaseSensitive:$false
```

Upload boundary inspection:

```powershell
Select-String -Path .\backend\app\api\router.py -Pattern 'sources/upload|UploadFile|upload_csv_to_dataset' -Context 2,4
```

Signed-reference boundary inspection:

```powershell
Select-String -Path .\backend\app\services\layer3_signed_reference_state.py,.\backend\app\services\layer3_workbench.py,.\backend\tests\test_layer3_api.py -Pattern 'LAYER3_SIGNED_REFERENCE_SECRET|SIGNED_REFERENCE_REPLAY_POLICY_SINGLE_USE|SIGNED_REFERENCE_TOKEN_STATE_REVOKED|external_export_download_signed_reference_replay_denied|public_url_enabled|connector_dispatch_enabled|destination_selection_enabled|generic_downstream_dispatch_enabled' -CaseSensitive:$false
```

Scope proof for this slice before staging:

```powershell
git status --short
git ls-files --others --exclude-standard -- .\next_milestone_plans\Layer3_planning_docs\116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md
```

Expected slice-specific result before staging:

```text
?? next_milestone_plans/Layer3_planning_docs/116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md
next_milestone_plans/Layer3_planning_docs/116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md
```

If the artifact is later staged, `git diff --name-only --cached` should list only this artifact for the slice.

Pre-existing `.omc/state/*` changes and approved sidecars may also appear in `git status --short`; they are not part of this slice and must not be edited.

## Overclaim Corrections

Correct these claims when encountered:

| Overclaim | Correct wording |
|---|---|
| Layer 3 has repo-live FastAPI auth. | Repo-live config requires a proxy-owned nonlocal posture, but inspected local code does not prove in-app request auth. |
| HMAC signed references authenticate operators. | HMAC signed references validate token integrity, authority basis, replay policy, and same-origin delivery state; requester authorization is a separate boundary. |
| `/sources/upload` is covered by Layer 3 source trust. | `/sources/upload` is a separate source-ingest boundary and needs auth/proxy plus upload hardening before nonlocal exposure. |
| Provider/public URLs are pre-wired and ready. | Provider/public URLs remain blocked and must not be enabled without a separate freeze/contract/proof slice. |
| Connector/destination dispatch is implied by response fields. | Connector/destination dispatch remains blocked; false response fields are not implementation admission. |
| Qualitative/hybrid/RAG execution is authorized by mockups. | Mockups are target-state only; current flags/docs admit only the exact single APS-document qualitative pass and keep broad qualitative, hybrid, and RAG/vector capabilities deferred. |
| Integration signed-reference tests prove concurrency safety. | Existing integration tests prove important lifecycle basics; dedicated concurrency and revocation proof is still required. |

## Final Self-Audit Checklist

- [x] This artifact is planning/docs-only.
- [x] It does not implement auth, upload hardening, signed-reference changes, provider URLs, connector dispatch, frontend recovery, models, migrations, tests, or runtime code.
- [x] It separates repo-confirmed facts from external deployment assumptions.
- [x] It does not claim in-app auth exists.
- [x] It does not underclaim signed-reference state: same-origin HMAC/durable state exists.
- [x] It keeps all deferred/no-go capabilities unavailable.
- [x] It identifies exactly which later slices are allowed.
- [x] It includes validate-only commands and scope proof.
