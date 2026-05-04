# Layer 3 Connector Dispatch Freeze

## Status

Current-main planning/control freeze for connector, destination, and generic downstream dispatch behavior after the selected-pass associated-cohort same-origin delivery, same-origin signed-reference, durable same-origin state, APS parser/bridge/provenance residual settlement, and provider/public URL governance chain.

This document does not implement connector dispatch, destination selection, connector-run creation, external destination writes, provider/public URLs, object-store ACL changes, rendered controls, package mutation, schema/runtime/source widening, qualitative execution, queue behavior, retries, cancellation, or any route by itself. It freezes the decision that connector/destination dispatch remains not admitted until a later implementation-entry freeze proves one exact destination authority model and lifecycle.

## Current Live Boundary

Current `project6-origin/main` already supports these bounded delivery and dispatch-adjacent surfaces:

- PR `#460` backend/API associated-cohort handoff/export prepare-only state.
- PR `#462` rendered prepare UI authority projection over that server state.
- PR `#466` bounded backend/API associated-cohort APS evidence-bundle handoff dispatch.
- PR `#479` bounded backend/API associated-cohort external export/download readiness as a reference-only descriptor.
- PR `#483` backend/API same-origin associated-cohort evidence-bundle delivery through the existing delivery endpoint.
- PR `#487` explicit server-authoritative associated-cohort rendered delivery UI gate.
- PR `#499`, PR `#514`, and PR `#520` same-origin signed-reference backend/API, rendered UI, and durable backing state.
- PR `#522` APS parser/bridge/provenance residual hardening.
- Docs `110`/`111` provider/public URL governance as planning/control only.

The live APS handoff dispatch target is still the owner-service `aps_evidence_bundle_handoff` family through `aps_handoff_target == "aps_evidence_bundle"` and `dispatch_mode == "server_side_aps_handoff"`. Current API/service responses keep `connector_dispatch_enabled`, `destination_selection_enabled`, and `generic_downstream_dispatch_enabled` false outside separately admitted behavior.

None of those PRs admit external connector runs, destination ids, generic downstream dispatch, public/provider URL behavior, package payload mutation, schema/runtime/source widening beyond named durable state and residual parser/bridge corrections, qualitative execution, retry/cancel/recovery behavior, broader UI behavior, or full mockup activation.

## Decision

Connector/destination/generic downstream dispatch remains blocked.

The next admissible step is not implementation. The next admissible step is a future implementation-entry freeze only if live repo evidence proves that same-origin delivery, same-origin durable signed references, and owner-service APS handoff artifacts are insufficient for a concrete downstream integration need.

If that evidence exists later, the future freeze must choose exactly one initial dispatch mode:

- `internal_dispatch_record_only`: server records an operator-approved dispatch intent and response-safe receipt without invoking an external connector or destination.
- `single_named_connector_dispatch`: server invokes exactly one named connector family already present in repo authority, with a bounded connector-run lifecycle.
- `single_named_destination_dispatch`: server writes or sends to exactly one named destination family with explicit destination id authority and delivery receipt semantics.

Do not implement more than one dispatch mode in the first connector/destination lane.

## Required Activation Evidence

Before implementation can begin, the future lane must prove:

- same-origin delivery, durable same-origin signed references, and owner-service APS handoff artifacts cannot satisfy the named use case;
- the selected dispatch mode maps to exactly one artifact family, initially the existing associated-cohort APS evidence-bundle artifact unless another artifact is explicitly frozen;
- destination ids, connector keys, connector targets, credentials, and environment configuration are repo-confirmed rather than inferred from UI notes or operator memory;
- connector-run lifecycle states, allowed transitions, retry, cancel, failure, timeout, and idempotency behavior are specified;
- authorization boundary between Layer 3 workbench state and the external connector/destination is specified;
- delivery receipt and audit payloads are response-safe and do not leak local paths, credentials, provider internals, connector secrets, destination secrets, or package bytes;
- UI-visible disabled/ready/failed states are specified before rendered controls are changed;
- tests can prove no connector/destination/generic dispatch occurs unless the admitted lane explicitly asks for it.

## Non-Goals

This freeze does not admit:

- connector-run creation or external connector invocation;
- destination id selection or external destination writes;
- generic downstream dispatch;
- provider/public URL generation or object-store ACL behavior;
- rendered connector/destination controls;
- package payload copy, rewrite, reconstruction, amendment, or supersession;
- new `AnalysisArtifact`, package, reconciliation, source, plan, pass, analysis, runtime snapshot, connector-run, or destination rows;
- schema/model/migration changes;
- background queue workers, retries, recovery, cancellation, or cleanup;
- qualitative APS content document execution;
- source ingestion/upload/directory expansion;
- full mockup activation.

## Required Future Implementation Scope

A future connector/destination implementation freeze must name:

- exact dispatch mode from this freeze;
- exact API route or service seam;
- exact connector or destination authority owner;
- exact allowed connector keys or destination ids;
- exact configuration variables and fail-closed behavior when absent;
- exact artifact authority basis and hash/size binding;
- exact lifecycle states and state-transition rules;
- exact idempotency key and concurrency behavior;
- exact receipt, audit, and operator-visible response schema;
- exact forbidden request fields;
- exact tests and browser proof, if rendered controls change.

The implementation must preserve existing same-origin delivery, same-origin durable signed-reference, provider/public URL governance, and owner-service APS handoff behavior unless the future freeze explicitly supersedes them with compatibility and rollback coverage.

## Stop Conditions

Stop before implementation if the intended change needs:

- connector keys, destination ids, credentials, or provider details that are not tracked in repo configuration or deployment policy;
- multiple connector/destination modes in one PR;
- public/provider URL generation as a prerequisite;
- package reconstruction or source artifact byte mutation;
- schema/model/migration changes not named by the future freeze;
- retry/cancel/recovery/queue semantics that are not specified;
- UI behavior beyond a separately admitted rendered connector/destination control;
- qualitative/hybrid/RAG/vector execution;
- runtime snapshot DB writes;
- a claim that PR `#466`, PR `#479`, PR `#483`, PR `#487`, PR `#499`, PR `#514`, PR `#520`, PR `#522`, or docs `110`/`111` already made connector/destination dispatch live.

## Proof Required For A Later Implementation

The first implementation PR must prove:

- connector/destination dispatch is disabled by default;
- missing connector/destination configuration fails closed;
- forbidden client connector, destination, dispatch, URL, package mutation, and source-widening fields fail closed;
- generated receipts bind to exact session, plan, pass, package, handoff/export, APS dispatch, readiness, delivery, artifact ref/hash/size, signed-reference, and durable-state authority where applicable;
- wrong destination, wrong connector, stale authority, wrong artifact, wrong session, malformed request, duplicate idempotency key, provider failure, connector failure, destination failure, timeout, and cancellation cases fail closed or enter a specified terminal state;
- no local filesystem path, provider credential, connector secret, destination secret, package payload byte, raw object key, or source path leaks to the client;
- no provider/public URL, package mutation, schema/runtime/source widening, qualitative execution, or full mockup behavior occurs as a side effect.
