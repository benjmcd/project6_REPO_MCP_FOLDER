# Layer 3 Deferred Gates

## Status

Post-synthesis authority guardrail: `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` records the current local synthesis correction for mockup, Codesight, progress-prose, and stale-audit overclaims. This deferred-gates document remains a freeze/control document only; it does not implement or newly admit provider/public URLs, broad connector/destination dispatch, package mutation/reconstruction, broad source/upload expansion, broad qualitative/hybrid/RAG execution, authentication/security work, or full mockup activation. The exact `internal_dispatch_record_only` runtime is live only as an internal record and does not change the broader deferred gates.

Current-main decision freeze for the remaining requested deferred categories after PR `#499`, PR `#513`, and PR `#514` rendered signed-reference UI slice in `104_signed-ui.md`.

Current-main docs `106_DURABLE_FREEZE.md` and `107_DURABLE_CONTRACT.md` selected durable token, receipt, revocation, and audit state as the next planning/control question only after PR `#516`. PR `#520` later implemented only bounded same-origin durable signed-reference runtime behavior behind the existing PR `#499` endpoints.

Current-main docs `108_DURABLE_ENTRY.md` and `109_DURABLE_STATE.md` named the implementation-entry surfaces and state contract for that durable same-origin signed-reference code lane. They remain the implementation-entry authority for PR `#520` and do not admit provider/public URLs, connector/destination dispatch, rendered revoke/copy/share UI behavior, qualitative execution, or package/source/schema/runtime widening beyond the named durable table family.

Current-main docs `110_PROVIDER_URL_FREEZE.md` and `111_PROVIDER_URL_CONTRACT.md` freeze provider/public URL behavior as not admitted. They require a future implementation-entry freeze to choose exactly one provider/public mode and prove provider/object-store authority, ACL/expiry/revocation/header/security behavior, leakage controls, and tests before code.

Current-main docs `112_CONNECTOR_DISPATCH_FREEZE.md` and `113_CONNECTOR_DISPATCH_CONTRACT.md` freeze connector/destination/generic downstream dispatch behavior as not admitted. Doc `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` now selects and bounds `internal_dispatch_record_only`; that exact runtime is live only as an internal record in existing `L3ReconciliationRecord.summary_json`. `connector_destination_dispatch` remains deferred, and `single_named_connector_dispatch` and `single_named_destination_dispatch` remain blocked. This does not admit external connector invocation, destination writes, provider/public URLs, package mutation/reconstruction, source widening, qualitative/hybrid/RAG execution, or full mockup activation.

Current-main docs `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md` freeze and narrow qualitative APS content document execution to the one initial `single_aps_doc_qualitative_pass` mode. That exact mode is implemented on current main; broader qualitative execution, hybrid execution, RAG/vector execution, qualitative package/handoff/export, and hidden LLM planning remain not admitted.

This file does not implement deferred broad behavior. It defines the minimum questions, blockers, and proof gates required before any of the following can become an implementation lane:

- provider/public signed URL generation;
- broad connector/destination dispatch beyond the exact internal record-only lane;
- durable token, receipt, revocation, and audit behavior beyond PR `#520`, including public/API/UI revocation or cleanup/read-model expansion;
- broad qualitative execution beyond the admitted single APS-document qualitative pass.

## Provider/Public Signed URLs

Current decision: planning/control frozen by docs `110`/`111`; implementation not admitted.

Implementation cannot begin until these are specified:

- provider and object-store authority;
- public-vs-private URL policy;
- ACL ownership and expiry semantics;
- revocation behavior;
- response header contract;
- security review for URL leakage;
- tests proving no provider URL is emitted unless explicitly requested by the admitted lane.

This lane must stay separate from same-origin signed references. A same-origin signed reference is a server-owned token for the existing API path, not a public/provider URL.

## Connector/Destination Dispatch

Current decision: planning/control frozen by docs `112`/`113`; doc `121` selects `internal_dispatch_record_only` as the first exact lane. That runtime is live only as an internal record at `/api/v1/layer3/handoff/connector/record`; broad `connector_destination_dispatch` remains deferred.

Broader implementation cannot begin until the `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` constraints are preserved and these are specified or explicitly kept blocked:

- destination model and allowed destination ids;
- exact dispatch mode: `internal_dispatch_record_only` for the first lane; `single_named_connector_dispatch` and `single_named_destination_dispatch` remain blocked;
- connector-run lifecycle;
- server-side connector/destination allowlist and configuration authority;
- retry, cancel, and failure semantics;
- delivery receipt format;
- operator-visible state transitions;
- authorization boundary between Layer 3 and the external destination;
- idempotency and stale-authority behavior;
- tests proving the UI/API cannot dispatch without explicit connector/destination authority.

This lane must not be folded into signed-reference UI work. The signed-reference UI may display connector/destination as disabled only.

## Durable Token/Receipt/Audit State

Current decision: bounded same-origin durable runtime state is live through PR `#520`; public/API/UI revocation, cleanup/read-model expansion, provider/public URL coupling, and rendered revoke/copy/share controls are not admitted.

Additional implementation cannot begin until these are specified:

- whether the next behavior changes the existing `single_use` replay policy;
- table/model/migration requirements beyond PR `#520`, if any;
- audit event schema beyond current generate/use events;
- receipt schema beyond current generate/use receipts;
- retention and cleanup policy;
- concurrency and idempotency behavior;
- proof that existing PR `#499` HMAC behavior and PR `#520` durable state are either preserved or intentionally superseded.

This lane likely requires schema/model/migration review if it changes the current table family and must not be hidden inside provider/public URL, connector/destination, or UI-only patches.

## Qualitative APS Content Document Execution

Current decision: `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md` admitted and branch-local code implements the exact `single_aps_doc_qualitative_pass` mode only.

Any broader qualitative implementation cannot begin until these are specified:

- exact additional execution mode, if any, and how it composes with `single_aps_doc_qualitative_pass`;
- qualitative unit contract for APS content documents;
- method admission policy for qualitative and qualitative-document inputs;
- execution engine owner;
- input chunk ordering, limits, citation, and trace requirements;
- result schema and review semantics;
- whether output is fact/finding/insight/caveat/result, and how those terms are constrained;
- tests proving DatasetVersion quantitative execution is not reused accidentally for qualitative content.

The currently live APS content document path includes selection, trace, material preview, typing/display support, theme alignment, and the exact single-document qualitative execution pass. Current tests prove APS content documents can be listed, previewed, traced, snapshotted, typed as qualitative document chunks, executed through `single_aps_doc_qualitative_pass` without `AnalysisRun` or `DatasetVersion`, and blocked from qualitative package/handoff/export broadening.

## Common Stop Conditions

Stop before implementation if the intended change needs:

- new database tables or migrations;
- new connector or destination state;
- external provider credentials or ACL changes;
- package reconstruction or mutation;
- source ingestion/upload/directory expansion;
- broad qualitative/hybrid/RAG/vector execution beyond the admitted single APS-document qualitative pass;
- rendered controls beyond the exact lane being admitted;
- a claim that PR `#513` made runtime behavior live.
