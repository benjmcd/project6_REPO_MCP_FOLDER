# Layer 3 Selected-Pass Cohort External Export Download Signed URL Freeze

## Status

Branch-local planning/control freeze for a possible future selected-pass associated-cohort external export/download signed delivery reference.

This document does not implement signed URL generation, token minting, URL serving, rendered UI changes, connector dispatch, destination selection, package mutation, schema/runtime/source widening, or any new route by itself. Current live behavior remains the PR `#483` same-origin attachment delivery endpoint plus the PR `#487` explicit server-authoritative rendered delivery UI gate. The PR `#496` package-review submit legacy idempotency hardening remains part of the current upstream authority chain, but it does not widen delivery or URL behavior.

## Current Live Baseline

Current `project6-origin/main` proves this chain:

- PR `#432` selected-pass associated-cohort execution-start/result-status;
- PR `#438` selected-pass associated-cohort result review;
- PR `#443` rendered associated-cohort result-review UI;
- PR `#447` read-only package-review preview/readiness;
- PR `#451` bounded associated-cohort package construction;
- PR `#456` bounded associated-cohort package-review submit, with PR `#496` preserving legacy submit-ref idempotency for existing submitted records;
- PR `#460` bounded handoff/export prepare-only state;
- PR `#462` rendered handoff/export prepare authority projection;
- PR `#466` bounded APS evidence-bundle handoff dispatch;
- PR `#479` reference-only external export/download readiness;
- PR `#483` backend/API same-origin delivery proof through the existing delivery endpoint;
- PR `#487` explicit rendered associated-cohort delivery UI gate over the existing generic same-origin attachment form.

The live repo still explicitly rejects or disables public URL, signed URL, download token, connector/generic dispatch, destination selection, package mutation, schema/runtime/source widening, retry/recovery/rerun, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior.

## Slice Decision

The only selected planning boundary is:

> Define the minimum governance needed before a future implementation may introduce a short-lived, server-authorized signed delivery reference for the existing associated-cohort APS evidence-bundle download.

This freeze does not admit runtime generation yet. It exists because the current delivery path is intentionally same-origin attachment only, and signed URL behavior has higher blast radius than the PR `#487` rendered gate. A future implementation must first prove the token/signature strategy, route ownership, revalidation behavior, expiry, replay/idempotency behavior, and no-go boundaries before any URL field can become live.

## Candidate Future Behavior

A later implementation may be considered only if it remains within this future shape:

- generate at most one short-lived server-owned signed delivery reference for the existing APS evidence-bundle artifact already validated by PR `#483`;
- bind that reference to exact session, plan, pass, result-review, package-review, package, handoff/export, APS dispatch, readiness, artifact ref/hash/size, and delivery authority;
- require full server-side authority revalidation at generation time and at use time;
- keep the current same-origin attachment endpoint valid and unchanged for the existing delivery path;
- return only server-generated URL/token metadata, never accept URL/token authority from a client payload;
- expire quickly and fail closed when stale, mismatched, reused outside its allowed policy, or presented against changed upstream authority;
- avoid holding database locks while streaming or validating artifact bytes, following the existing delivery lock-release boundary;
- create no package, reconciliation, artifact, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files unless a separate freeze explicitly admits that write.

## No-Go List

This freeze does not admit:

- public URL generation or anonymous public access;
- long-lived bearer URLs;
- external object-store ACL changes or provider-specific signed URL behavior without a separate implementation contract;
- connector dispatch, connector-run handling, generic downstream dispatch, destination selection, or external target selection;
- rendered UI controls for requesting, copying, sharing, refreshing, revoking, or using a signed URL;
- package payload copy, rewrite, reconstruction, amendment, supersession, or source artifact byte mutation;
- additional package, reconciliation, artifact, receipt, audit-log, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files;
- `AnalysisArtifact` expansion;
- schema/runtime/source/model/migration widening;
- durable token tables, delivery receipt tables, or runtime write state;
- retry/recovery/rerun behavior beyond a separately proven idempotency policy;
- qualitative/hybrid/RAG/vector behavior;
- broader UI, broader associated-cohort review, or full mockup activation.

If a future implementation needs any item above, stop and create a narrower freeze before editing code.

## Required Authority Before Future Implementation

A later implementation must prove all of these before it may generate or expose a signed delivery reference:

1. exact associated-cohort readiness from PR `#479` remains recorded;
2. exact same-origin delivery authority from PR `#483` remains valid;
3. PR `#487` rendered UI gate remains separate from backend signed URL authority unless a later UI freeze explicitly admits UI behavior;
4. PR `#496` legacy submit-ref idempotency compatibility is preserved for already-submitted package-review state;
5. `pass_type == associated_cohort`;
6. `pass_scope == quantitative_associated_cohort_dataset_version`;
7. `method == descriptive_summary`;
8. `source_gate == 78_COHORT_FREEZE`;
9. `source_shape == aligned_wide_table`;
10. `source_dataset_version_ids` match package, submit, handoff/export, APS dispatch, readiness, and delivery authority;
11. package-review submit, handoff/export prepare, APS dispatch, readiness, and delivery refs match stored authority;
12. APS bundle ref/id/schema/hash/size validates through the existing APS evidence-bundle owner-service contract;
13. the signed reference is bound to the same artifact ref/hash/size and cannot be replayed against a different artifact;
14. public URL, connector dispatch, destination selection, generic downstream dispatch, package mutation, schema/runtime/source widening, retry/recovery/rerun, and broader UI flags remain disabled unless separately frozen.

## Implementation Entry Conditions

Before any code changes for this future slice, the implementation lane must answer these questions from repo evidence:

- Is a signed reference required, or is existing same-origin attachment delivery sufficient?
- Can the implementation stay stateless and server-revalidated without adding durable token or receipt storage?
- If persistence is required for expiry, revocation, replay prevention, audit, or receipt semantics, which separate freeze admits the exact table/state write?
- Which exact endpoint owns generation and which exact endpoint owns reference use?
- How will stale upstream authority fail closed at both generation and use time?
- How will duplicate generation requests behave under the existing `client_request_id` and idempotency conventions?
- Which focused API tests prove absent forbidden fields, no URL leakage in existing delivery, expiry, stale mismatch, replay policy, and no row/file creation?

Unanswered items keep this slice in planning/recon mode.

## Required Proof For Future Implementation

A future implementation must include focused proof for:

- current same-origin delivery remains unchanged and still emits no public/signed URL headers;
- existing delivery requests still reject client-supplied `download_url`, `download_token`, `public_url`, `signed_url`, connector, destination, dispatch, package mutation, schema, runtime, source, retry, and rerun fields;
- signed reference generation is server-owned and cannot be supplied or altered by the browser/client;
- signed reference use revalidates the exact upstream associated-cohort chain before streaming;
- expired, stale, mismatched, malformed, replayed, and cross-session references fail closed;
- no local filesystem path, source path, connector target, or external provider detail leaks to the client;
- no package, reconciliation, artifact, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files are created unless a separate freeze admits them;
- existing API tests for package-review submit, handoff/export, APS dispatch, readiness, delivery, and rendered delivery UI still pass;
- browser proof is required only if a later UI freeze admits rendered signed URL behavior.

## Deferred After This Freeze

Still separate and not admitted:

- signed URL implementation;
- public URL generation;
- rendered signed URL controls;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment, rebuild, copy, rewrite, or supersession;
- durable token, receipt, audit, or runtime write state;
- additional reconciliation/package/artifact rows;
- `AnalysisArtifact` expansion;
- schema/runtime/source/model/migration widening;
- qualitative/hybrid/RAG/vector behavior;
- broader UI or full mockup activation.
