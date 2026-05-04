# Layer 3 Deferred Gates

## Status

Current-main decision freeze for the remaining requested deferred categories after PR `#499`, PR `#513`, and PR `#514` rendered signed-reference UI slice in `104_signed-ui.md`.

On this branch, docs `106_DURABLE_FREEZE.md` and `107_DURABLE_CONTRACT.md` select durable token, receipt, revocation, and audit state as the next planning/control question only. They do not implement durable behavior.

This file does not implement deferred behavior. It defines the minimum questions, blockers, and proof gates required before any of the following can become an implementation lane:

- provider/public signed URL generation;
- connector/destination dispatch;
- durable token, receipt, revocation, and audit state implementation, with docs `106`/`107` admitted as planning/control only;
- qualitative APS content document execution.

## Provider/Public Signed URLs

Current decision: not admitted.

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

Current decision: not admitted.

Implementation cannot begin until these are specified:

- destination model and allowed destination ids;
- connector-run lifecycle;
- retry, cancel, and failure semantics;
- delivery receipt format;
- operator-visible state transitions;
- authorization boundary between Layer 3 and the external destination;
- tests proving the UI/API cannot dispatch without explicit destination authority.

This lane must not be folded into signed-reference UI work. The signed-reference UI may display connector/destination as disabled only.

## Durable Token/Receipt/Audit State

Current decision: planning/control admitted by docs `106`/`107`; implementation not admitted.

Implementation cannot begin until these are specified:

- whether tokens are stateless, persisted, one-time-use, replayable, or revocable;
- table/model/migration requirements;
- audit event schema;
- receipt schema;
- retention and cleanup policy;
- concurrency and idempotency behavior;
- proof that existing PR `#499` stateless HMAC behavior is either preserved or intentionally superseded.

This lane likely requires schema/model/migration review and must not be hidden inside a UI-only patch.

## Qualitative APS Content Document Execution

Current decision: not admitted.

Implementation cannot begin until these are specified:

- qualitative unit contract for APS content documents;
- method admission policy for qualitative and qualitative-document inputs;
- execution engine owner;
- input chunk, citation, and trace requirements;
- result schema and review semantics;
- whether output is fact/finding/insight/caveat/result, and how those terms are constrained;
- tests proving DatasetVersion quantitative execution is not reused accidentally for qualitative content.

The currently live APS content document path is selection, trace, material preview, typing/display support, and theme alignment. It is not a qualitative execution engine.

## Common Stop Conditions

Stop before implementation if the intended change needs:

- new database tables or migrations;
- new connector or destination state;
- external provider credentials or ACL changes;
- package reconstruction or mutation;
- source ingestion/upload/directory expansion;
- qualitative/hybrid/RAG/vector execution;
- rendered controls beyond the exact lane being admitted;
- a claim that PR `#513` made runtime behavior live.
