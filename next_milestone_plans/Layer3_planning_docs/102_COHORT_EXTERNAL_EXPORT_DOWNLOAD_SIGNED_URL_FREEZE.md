# Layer 3 Selected-Pass Cohort External Export Download Signed URL Freeze

## Status

Current-main planning/control freeze for the selected-pass associated-cohort external export/download signed delivery reference boundary.

This document did not implement signed-reference generation, token minting, URL serving, rendered UI changes, connector dispatch, destination selection, package mutation, schema/runtime/source widening, or any route by itself. PR `#499` is the separate implementation authority: current `project6-origin/main` now includes bounded backend/API same-origin signed delivery reference generation and use under the existing Layer 3 external export/download route family. Current live behavior remains limited to same-origin delivery surfaces: the PR `#483` attachment endpoint, the PR `#487` explicit server-authoritative rendered delivery UI gate, and the PR `#499` same-origin signed-reference generation/use endpoints. The PR `#496` package-review submit legacy idempotency hardening remains part of the current upstream authority chain, but it does not widen delivery or URL behavior.

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
- PR `#487` explicit rendered associated-cohort delivery UI gate over the existing generic same-origin attachment form;
- PR `#499` backend/API same-origin signed delivery reference generation and use through dedicated POST endpoints.

The live repo still explicitly rejects or disables public URL authority, provider-specific signed URLs, client-supplied download tokens, connector/generic dispatch, destination selection, package mutation, schema/runtime/source widening, retry/recovery/rerun, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior. PR `#499` does not render signed-reference controls in `/review/layer3`.

## Slice Decision

The selected planning boundary was:

> Define the minimum governance needed before a future implementation may introduce a short-lived, server-authorized signed delivery reference for the existing associated-cohort APS evidence-bundle download.

PR `#499` satisfied that backend/API implementation-entry boundary with a same-origin signed delivery reference, not a public URL or provider URL. The implementation proves token/signature strategy, route ownership, generation-time and use-time revalidation, short expiry, stale-authority failure, and no row/file creation while preserving the PR `#483` same-origin attachment endpoint and the PR `#487` rendered delivery UI gate.

## Implemented Backend/API Behavior

PR `#499` remains within this shape:

- generate a short-lived server-owned same-origin signed delivery reference for the existing APS evidence-bundle artifact already validated by PR `#483`;
- bind that reference to exact session, plan, pass, result-review, package-review, package, handoff/export, APS dispatch, readiness, artifact ref/hash/size, and delivery authority;
- require full server-side authority revalidation at generation time and at use time;
- keep the current same-origin attachment endpoint valid and unchanged for the existing delivery path;
- return only server-generated URL/token metadata, never accept URL/token authority from a client payload;
- expire quickly and fail closed when stale, mismatched, reused outside its allowed policy, or presented against changed upstream authority;
- avoid holding database locks while streaming or validating artifact bytes, following the existing delivery lock-release boundary;
- create no package, reconciliation, artifact, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files unless a separate freeze explicitly admits that write.

The live PR `#499` route surface is:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`;
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`.

The implementation uses `same_origin_signed_delivery_reference` delivery mode, HMAC signing, a 300-second TTL, and requires `LAYER3_SIGNED_REFERENCE_SECRET` before generation or use. If the secret is absent, signed-reference generation/use fails closed instead of returning process-local tokens that can break across workers.

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
- durable token tables, delivery receipt tables, audit tables, revocation tables, or runtime write state;
- retry/recovery/rerun behavior beyond a separately proven idempotency policy;
- qualitative/hybrid/RAG/vector behavior;
- broader UI, broader associated-cohort review, or full mockup activation.

If later work needs any item above, stop and create a narrower freeze before editing code.

## Required Authority For Signed Reference Generation

PR `#499` proves all of these before it may generate or use a signed delivery reference:

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
14. public URL, provider URL, connector dispatch, destination selection, generic downstream dispatch, package mutation, schema/runtime/source widening, retry/recovery/rerun, and broader UI flags remain disabled unless separately frozen.

## Implementation Entry Answers

PR `#499` answered the implementation-entry questions from repo evidence:

- a signed reference is admitted only as an additive same-origin backend/API reference; the existing attachment delivery remains valid and unchanged;
- the implementation stays stateless and server-revalidated, without durable token or receipt storage;
- no persistence freeze is consumed because no expiry, revocation, replay-prevention, audit, or receipt table/state write is added;
- generation is owned by `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`;
- use is owned by `POST /api/v1/layer3/handoff/export/download/signed-reference/use`;
- stale upstream authority fails closed at both generation and use time through the same associated-cohort delivery authority validation basis;
- duplicate generation remains stateless and request-scoped; no persistent token clutter is created;
- focused API tests cover forbidden fields, expiry, stale authority, malformed references, no row/file creation, OpenAPI route presence, and preservation of existing delivery behavior.

Any later requirement for revocation, durable audit, public/provider URL behavior, rendered controls, or destination/connector dispatch remains outside PR `#499` and requires separate governance.

## Required Proof For PR #499

PR `#499` includes focused proof that:

- current same-origin delivery remains unchanged and still emits no public/signed URL headers;
- existing delivery requests still reject client-supplied `download_url`, `download_token`, `public_url`, `signed_url`, connector, destination, dispatch, package mutation, schema, runtime, source, retry, and rerun fields;
- signed reference generation is server-owned and cannot be supplied or altered by the browser/client;
- signed reference use revalidates the exact upstream associated-cohort chain before streaming;
- expired, stale, mismatched, malformed, replayed, and cross-session references fail closed;
- no local filesystem path, source path, connector target, or external provider detail leaks to the client;
- no package, reconciliation, artifact, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files are created unless a separate freeze admits them;
- existing API tests for package-review submit, handoff/export, APS dispatch, readiness, delivery, and rendered delivery UI still pass;
- browser proof remains deferred because PR `#499` admits no rendered signed-reference UI behavior.

## Deferred After PR #499

Still separate and not admitted:

- public URL generation;
- provider-specific signed URL generation;
- rendered signed URL controls;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment, rebuild, copy, rewrite, or supersession;
- durable token, revocation, receipt, audit, or runtime write state;
- additional reconciliation/package/artifact rows;
- `AnalysisArtifact` expansion;
- schema/runtime/source/model/migration widening;
- qualitative/hybrid/RAG/vector behavior;
- broader UI or full mockup activation.
