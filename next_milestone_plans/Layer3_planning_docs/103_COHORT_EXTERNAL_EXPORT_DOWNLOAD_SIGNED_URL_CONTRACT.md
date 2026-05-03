# Layer 3 Selected-Pass Cohort External Export Download Signed URL Contract

## Status

Current-main planning/control contract paired with `102_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_FREEZE.md`.

This contract defined the admissibility rules for a signed delivery reference after the existing associated-cohort same-origin delivery and rendered delivery gate work. It did not make signed-reference generation live or allocate routes by itself; PR `#499` is the separate implementation authority for bounded backend/API same-origin signed-reference generation and use. The contract still does not add UI behavior, persistence, schema/runtime/source widening, connector/destination/downstream dispatch, public URLs, or provider-specific signed URLs.

## Authority Order

Use this order before auditing or extending signed-reference behavior:

1. current `project6-origin/main` source and tests;
2. live GitHub PR/check/review state for the branch being implemented;
3. PR `#499` for current-main backend/API same-origin signed-reference generation and use;
4. docs `102`/`103` for signed delivery-reference governance;
5. docs `98`/`99` and PR `#483` for same-origin associated-cohort backend/API delivery proof;
6. docs `100`/`101` and PR `#487` for rendered delivery UI gate behavior;
7. docs `96`/`97` and PR `#479` for reference-only readiness;
8. upstream associated-cohort result, package, submit, handoff/export, APS dispatch, and UI proof docs/PRs;
9. browser state, rendered labels, request-local data, and operator notes.

Browser state, client-supplied URLs, request-local tokens, and copied links are never authority for delivery availability, artifact identity, expiry, replay policy, downstream enablement, or package/source mutation.

## Contract Vocabulary

This contract reserves these labels for the signed-reference boundary:

- `associated_cohort_external_export_download_signed_url_not_admitted`;
- `associated_cohort_external_export_download_signed_url_generation_blocked`;
- `associated_cohort_external_export_download_signed_url_ready`;
- `same_origin_signed_delivery_reference`;
- `short_lived_server_authorized_delivery_reference`.

These labels are not live states by themselves. PR `#499` makes only `same_origin_signed_delivery_reference` generation/use live through backend/API POST endpoints. Existing code should continue to expose public/provider URL and connector/destination/generic dispatch flags as disabled unless a later implementation PR proves otherwise.

## Implemented Route Boundary

PR `#499` allocates exactly two backend-owned POST endpoints under the existing Layer 3 external export/download route family:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`;
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`.

Any later implementation that needs an external object-store URL, public route, connector endpoint, destination selector, provider-specific ACL change, durable token table, revocation table, delivery receipt table, runtime write state, schema/model/migration change, or rendered UI control must stop for a separate freeze.

## Generation Request Contract

The generation request is built from server-confirmed authority plus a fresh `client_request_id`. It includes the same authority fields already admitted for associated-cohort same-origin delivery, including:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_id`;
- `preview_hash`;
- result-review record ref;
- package-review preview hash;
- reconciliation record id;
- output package ids;
- package kinds;
- payload refs;
- payload hashes;
- package-review submit record ref and approved state;
- handoff/export prepare record ref and prepared state;
- handoff export envelope ref;
- APS handoff record ref and dispatched state;
- APS output package id and kind;
- APS bundle ref/id/schema/hash/size;
- external export/download record ref and descriptor ref;
- `external_export_download_state == external_export_download_prepared`;
- `export_download_target == aps_evidence_bundle_download_reference`;
- `download_mode == reference_only_prepare`;
- current delivery authority from PR `#483`;
- `operator_decision` naming the signed-reference action admitted by PR `#499`.

The request must not accept:

- `download_url`;
- `download_token`;
- `public_url`;
- `signed_url`;
- `signed_delivery_url`;
- `local_file_path`;
- `external_target`;
- `destination`;
- `destination_selector`;
- `destination_id`;
- `connector_run_id`;
- `connector_dispatch`;
- `generic_dispatch`;
- `dispatch`;
- `send`;
- `runtime_db_write`;
- `analysis_artifact`;
- `artifact_manifest`;
- `create_package`;
- `rebuild_package`;
- `package_payload`;
- `package_variant_content`;
- `rewrite_output`;
- amendments to result review, package review, handoff/export, APS handoff, readiness, delivery, or package state;
- `rerun`;
- `retry`;
- `recover`;
- `cancel`;
- `selected_pass_ids`;
- `pass_run_ids`;
- `new_analysis_plan`;
- `plan_revision`;
- `source_expansion`;
- `local_upload`;
- `local_directory`;
- `schema_migration`;
- browser-inferred authority fields.

Any signed reference returned by PR `#499` must be server-generated only.

## Response Contract

The signed-reference response may expose only metadata needed by the operator/browser to use the server-authorized reference:

- a server-owned same-origin signed delivery reference;
- expiry timestamp or short TTL;
- artifact ref/hash/size basis;
- server authority state;
- disabled downstream flags;
- non-authoritative display labels.

It must not expose:

- public URL authority;
- local filesystem paths;
- source package paths;
- connector targets;
- destination ids;
- external provider credentials or ACL details;
- package payload bytes;
- mutable package content;
- durable receipt, audit, revocation, or runtime write state unless separately frozen and implemented.

The existing same-origin delivery endpoint must continue to return attachment bytes without public/signed URL headers. PR `#499` adds separate signed-reference generation/use endpoints and does not change that response contract.

## Use Contract

Using a signed reference must:

- revalidate the exact associated-cohort authority chain at use time;
- bind the reference to the same artifact ref/hash/size that generation proved;
- fail closed for expired, stale, mismatched, malformed, cross-session, or policy-disallowed references;
- avoid relying only on token contents when server-side state has changed;
- avoid holding a database lock while reading, hashing, statting, or streaming artifact bytes;
- create no package, reconciliation, artifact, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files unless a separate freeze admits the write;
- preserve PR `#496` package-review submit idempotency compatibility for legacy submitted records in the upstream chain.

## Idempotency And Replay Contract

PR `#499` defines duplicate and replay behavior without durable token state:

- duplicate generation creates no durable token rows and does not mutate package/reconciliation/artifact state;
- duplicate generation with different request ids does not create persistent token clutter;
- reference use is allowed only within the short TTL and exact authority basis;
- expired, stale, malformed, or authority-mismatched references fail closed;
- failed signed-reference use does not silently fall back to the existing same-origin attachment endpoint;
- implementation tests cover generation/use, expiry, malformed references, stale authority, and no row/file creation.

If a later replay policy requires revocation, one-time-use semantics, durable audit, or token persistence, this contract and PR `#499` are insufficient by themselves.

## UI Contract

No rendered UI behavior is admitted by this contract or PR `#499`.

A later UI freeze is required before `/review/layer3` can:

- show a signed URL button or link;
- copy a signed URL;
- refresh, revoke, or share a signed URL;
- use a signed URL in a browser-managed flow;
- render signed URL expiry or replay state as operator-facing controls.

Until that separate UI freeze lands, PR `#487` remains the only associated-cohort rendered delivery UI authority, and it remains same-origin attachment only.

## PR #499 Proof Requirements

PR `#499` proves:

- existing delivery tests still reject client-supplied URL/token fields;
- existing delivery headers still do not leak `download_url`, `public_url`, `signed_url`, local paths, connector ids, or destination ids;
- generation requires exact associated-cohort authority through PR `#479`, PR `#483`, and upstream package/handoff/APS state;
- use revalidates authority independently of generation;
- expiry, malformed token, stale upstream state, artifact hash mismatch, cross-session use, duplicate generation, and replay policy fail closed as specified;
- no new rows/files are created unless separately frozen;
- no schema/model/migration/runtime/source widening occurs;
- no connector/generic dispatch, destination selection, package mutation, qualitative/hybrid/RAG/vector, broader UI, or full mockup activation occurs;
- browser proof remains deferred because rendered signed-reference UI behavior is not admitted.
