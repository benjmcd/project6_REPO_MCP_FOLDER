# Layer 3 Provider/Public URL Freeze

## Status

Current-main planning/control freeze for provider/public signed URL behavior after the existing selected-pass associated-cohort same-origin delivery and signed-reference chain.

This document does not implement provider URLs, public URLs, object-store ACL changes, connector dispatch, destination selection, rendered controls, package mutation, schema/runtime/source widening, qualitative execution, or any route by itself. It freezes the decision that provider/public URL behavior remains not admitted until a later implementation contract proves a concrete provider authority model and security posture.

## Current Live Boundary

Current `project6-origin/main` already supports these bounded same-origin delivery surfaces:

- PR `#483` backend/API same-origin associated-cohort APS evidence-bundle delivery through the existing delivery endpoint.
- PR `#487` explicit server-authoritative rendered delivery UI gate over the existing same-origin attachment form.
- PR `#499` backend/API same-origin signed-reference generation/use through dedicated POST endpoints.
- PR `#514` rendered `/review/layer3` same-origin signed-reference controls over PR `#499`.
- PR `#520` durable same-origin signed-reference backing state: token hashes, generation/use receipts, audit rows, revocation table awareness without a public endpoint, durable missing-state failure, and single-use replay denial.
- PR `#522` bounded APS parser/bridge/provenance residual hardening only.

None of those PRs admit provider-hosted URLs, public URLs, external object-store ACL behavior, connector/destination dispatch, package mutation, source/schema/runtime widening beyond the named durable state tables, qualitative execution, broader UI behavior, or full mockup activation.

## Decision

Provider/public URL behavior remains blocked.

The next admissible step is not implementation. The next admissible step is a future implementation-entry freeze only if live repo evidence proves that same-origin attachment delivery plus same-origin durable signed references are insufficient for a concrete operator or downstream integration need.

If that evidence exists later, the future freeze must choose exactly one of these provider/public modes:

- `provider_private_signed_url`: provider-hosted private object URL with short-lived signed access and no anonymous public ACL.
- `provider_public_url`: provider-hosted URL backed by explicit public ACL or public-read object policy.
- `public_proxy_url`: application-owned public route/proxy that hides provider details and preserves server-side authority.

Do not implement more than one mode in the first provider/public URL lane.

## Required Activation Evidence

Before implementation can begin, the future lane must prove:

- same-origin delivery and durable same-origin signed references cannot satisfy the named use case;
- the requested URL mode maps to exactly one artifact family, initially the existing associated-cohort APS evidence-bundle artifact;
- object ownership, storage provider, bucket/container namespace, and ACL authority are repo-confirmed rather than inferred;
- credentials and deployment environment are available through named configuration, not hard-coded values;
- expiry, revocation, rotation, and access-denial behavior are specified;
- response headers and browser exposure rules are specified;
- provider URL leakage risks are reviewed and bounded;
- audit and receipt behavior is defined without exposing raw credentials, local paths, or provider internals;
- tests can prove that no provider/public URL is emitted unless the admitted lane explicitly asks for it.

## Non-Goals

This freeze does not admit:

- public URL generation or anonymous public access;
- provider-specific signed URL generation;
- external object-store ACL changes;
- connector dispatch, connector-run handling, destination selection, or generic downstream dispatch;
- package payload copy, rewrite, reconstruction, amendment, or supersession;
- new `AnalysisArtifact`, package, reconciliation, source, plan, pass, analysis, or runtime snapshot rows;
- rendered copy/share/refresh/revoke/provider-link controls;
- qualitative APS content document execution;
- source ingestion/upload/directory expansion;
- schema/model/migration changes;
- background jobs, cleanup workers, retry/recovery/rerun, or queue behavior;
- full mockup activation.

## Required Future Implementation Scope

A future provider/public URL implementation freeze must name:

- exact provider mode from this freeze;
- exact API route or service seam;
- exact provider/storage adapter owner;
- exact configuration variables and fail-closed behavior when absent;
- exact artifact authority basis and hash/size binding;
- exact URL TTL and revocation semantics;
- exact response schema and header contract;
- exact audit/receipt state behavior;
- exact forbidden request fields;
- exact tests and browser proof, if rendered controls change.

The implementation must preserve the existing same-origin delivery and durable same-origin signed-reference paths unless the future freeze explicitly supersedes them with compatibility and rollback coverage.

## Stop Conditions

Stop before implementation if the intended change needs:

- a provider or object store that is not named in tracked repo configuration or deployment policy;
- public ACL changes without a security review;
- long-lived bearer URLs;
- connector or destination dispatch;
- package reconstruction or source artifact byte mutation;
- schema/model/migration changes not named by the future freeze;
- UI behavior beyond a separately admitted rendered provider/public URL control;
- qualitative/hybrid/RAG/vector execution;
- runtime snapshot DB writes;
- a claim that PR `#499`, PR `#514`, PR `#520`, or PR `#522` already made provider/public URL behavior live.

## Proof Required For A Later Implementation

The first implementation PR must prove:

- provider/public URL generation is disabled by default;
- missing provider configuration fails closed;
- existing same-origin delivery and same-origin signed-reference behavior still work;
- public/provider URL fields are still rejected on all non-admitted request paths;
- generated URLs are bound to exact session, plan, pass, package, handoff/export, APS dispatch, readiness, delivery, artifact ref/hash/size, and durable signed-reference authority where applicable;
- expired, revoked, stale-authority, wrong-artifact, wrong-session, malformed, and forbidden-field cases fail closed;
- no local filesystem path, provider credential, connector target, destination id, package payload byte, or source path leaks to the client;
- audit/receipt rows are response-safe if the future freeze admits any new rows;
- no package mutation, schema/runtime/source widening, connector dispatch, qualitative execution, or full mockup behavior occurs as a side effect.
