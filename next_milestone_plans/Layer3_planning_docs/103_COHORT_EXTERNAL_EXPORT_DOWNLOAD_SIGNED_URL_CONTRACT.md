# Layer 3 Selected-Pass Cohort External Export Download Signed URL Contract

## Status

Branch-local planning/control contract paired with `102_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_URL_FREEZE.md`.

This contract defines the admissibility rules for a possible future signed delivery reference after the existing associated-cohort same-origin delivery and rendered delivery gate work. It does not make signed URL generation live, allocate a route by itself, add UI behavior, add persistence, widen schema/runtime/source behavior, or permit connector/destination/downstream dispatch.

## Authority Order

Use this order before any future implementation:

1. current `project6-origin/main` source and tests;
2. live GitHub PR/check/review state for the branch being implemented;
3. docs `102`/`103` for signed delivery-reference governance;
4. docs `98`/`99` and PR `#483` for same-origin associated-cohort backend/API delivery proof;
5. docs `100`/`101` and PR `#487` for rendered delivery UI gate behavior;
6. docs `96`/`97` and PR `#479` for reference-only readiness;
7. upstream associated-cohort result, package, submit, handoff/export, APS dispatch, and UI proof docs/PRs;
8. browser state, rendered labels, request-local data, and operator notes.

Browser state, client-supplied URLs, request-local tokens, and copied links are never authority for delivery availability, artifact identity, expiry, replay policy, downstream enablement, or package/source mutation.

## Contract Vocabulary

This contract reserves these planning labels for future implementation design:

- `associated_cohort_external_export_download_signed_url_not_admitted`;
- `associated_cohort_external_export_download_signed_url_generation_blocked`;
- `associated_cohort_external_export_download_signed_url_ready`;
- `same_origin_signed_delivery_reference`;
- `short_lived_server_authorized_delivery_reference`.

These labels are not live states by themselves. Existing code should continue to expose `public_url_enabled: false`, `signed_url_enabled: false`, `download_url_enabled: false`, and disabled connector/destination/generic dispatch flags until an implementation PR proves otherwise.

## Future Route Boundary

This planning contract does not allocate live routes. A later implementation may add route behavior only after the implementation audit proves the exact ownership model.

The acceptable future route shape is constrained to one of these options:

- reuse the existing delivery route family with a server-owned generation action and a same-origin signed-reference consumption path; or
- add exactly one backend-owned generation endpoint and exactly one same-origin consumption endpoint under the existing Layer 3 external export/download route family.

Any implementation that needs an external object-store URL, public route, connector endpoint, destination selector, provider-specific ACL change, durable token table, delivery receipt table, runtime write state, schema/model/migration change, or rendered UI control must stop for a separate freeze.

## Future Generation Request Contract

A future generation request may be considered only if it is built from server-confirmed authority plus a fresh `client_request_id`. It may include the same authority fields already admitted for associated-cohort same-origin delivery, including:

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
- `operator_decision` naming only the future signed-reference action if separately implemented.

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

Any URL or token returned by a future implementation must be server-generated only.

## Future Response Contract

A future signed-reference response may expose only metadata needed by the operator/browser to use the server-authorized reference:

- a server-owned same-origin signed delivery reference or tokenized URL;
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
- durable receipt, audit, or runtime write state unless separately frozen and implemented.

The existing same-origin delivery endpoint must continue to return attachment bytes without public/signed URL headers unless the future implementation separately changes that response under this contract and proves the no-go boundaries.

## Future Use Contract

Using a future signed reference must:

- revalidate the exact associated-cohort authority chain at use time;
- bind the reference to the same artifact ref/hash/size that generation proved;
- fail closed for expired, stale, mismatched, malformed, cross-session, or policy-disallowed references;
- avoid relying only on token contents when server-side state has changed;
- avoid holding a database lock while reading, hashing, statting, or streaming artifact bytes;
- create no package, reconciliation, artifact, connector-run, plan, pass, analysis, runtime DB, source, model, migration, or physical export rows/files unless a separate freeze admits the write;
- preserve PR `#496` package-review submit idempotency compatibility for legacy submitted records in the upstream chain.

## Idempotency And Replay Contract

A future implementation must define duplicate and replay behavior before code changes:

- duplicate generation with the same valid `client_request_id` must be deterministic or fail closed without creating extra durable state;
- duplicate generation with different request ids must not create persistent token clutter unless a separate persistence freeze admits it;
- token replay must either be explicitly allowed within the short TTL and exact authority basis or rejected with a named fail-closed state;
- revoked, expired, stale, or authority-mismatched references must not fall back to unsigned same-origin delivery automatically;
- implementation tests must cover duplicate generation, replay, expiry, stale authority, and cross-session mismatch.

If the correct replay policy requires durable token state, this contract is insufficient by itself.

## UI Contract

No rendered UI behavior is admitted by this contract.

A later UI freeze is required before `/review/layer3` can:

- show a signed URL button or link;
- copy a signed URL;
- refresh, revoke, or share a signed URL;
- use a signed URL in a browser-managed flow;
- render signed URL expiry or replay state as operator-facing controls.

Until that separate UI freeze lands, PR `#487` remains the only associated-cohort rendered delivery UI authority, and it remains same-origin attachment only.

## Proof Requirements For Future Implementation

A future implementation must prove:

- existing delivery tests still reject client-supplied URL/token fields;
- existing delivery headers still do not leak `download_url`, `public_url`, `signed_url`, local paths, connector ids, or destination ids unless the future response contract explicitly admits a server-owned signed reference;
- generation requires exact associated-cohort authority through PR `#479`, PR `#483`, and upstream package/handoff/APS state;
- use revalidates authority independently of generation;
- expiry, malformed token, stale upstream state, artifact hash mismatch, cross-session use, duplicate generation, and replay policy fail closed as specified;
- no new rows/files are created unless separately frozen;
- no schema/model/migration/runtime/source widening occurs;
- no connector/generic dispatch, destination selection, package mutation, qualitative/hybrid/RAG/vector, broader UI, or full mockup activation occurs;
- browser proof runs only if a later UI freeze admits rendered signed URL behavior.
