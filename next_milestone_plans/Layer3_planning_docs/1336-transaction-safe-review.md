# 1336 SEC XBRL transaction-safe operator review design gate

Target: `sec_xbrl_transaction_safe_operator_review_persistence_design_v1`.

This slice selects the next production-readiness blocker after the offline
evidence proof-of-capability: the evidence-to-review chain must have a
transaction-safe persistence boundary before it can support an operator API/UI,
controlled value release, or production-admission claim.

## Current basis

The offline evidence proof can validate loader, CompanyFacts oracle, and
orchestrator behavior in isolated persistence. That proves the chain can produce
redacted operator-review state from governed real evidence. It does not prove
production transaction safety.

Current containment remains:

- existing projection, statement packet, and operator-review materializers commit
  independently;
- `single_transaction_claimed` remains false;
- production database persistence is not performed by the proof diagnostic;
- API/UI activation remains false;
- value reveal remains false;
- production readiness remains unclaimed.

## Decision

The next implementation boundary should be an atomic SEC XBRL evidence-to-review
service that wraps projection materialization, statement packet materialization,
and operator-review workflow opening in one caller-owned transaction.

The atomic service should become the only admitted path for future operator API
activation. Existing independently committing materializers may remain for their
current tests and internal use, but production-facing orchestration must not
claim atomicity unless the caller can prove all three stages commit or roll back
together.

## Required properties

- A single transaction covers projection set, projection facts, statement packet
  set, statement packet rows, operator-review workflow, and review rows.
- A failure after projection materialization but before workflow opening rolls
  back all SEC XBRL persistence from the attempted chain.
- Idempotency semantics are explicit: either the transaction reuses a completed
  prior request safely, or it fails closed without partial duplicate state.
- Public responses remain hash/count/state-only and value-redacted.
- Raw storage, CompanyFacts payloads, local paths, SEC URLs, accessions, and raw
  values are never persisted into public operator-review state.
- The service accepts already-loaded governed evidence or a redacted proof
  authority handle; it does not acquire sources, invoke Arelle, perform network
  access, or read arbitrary operator paths from an API request.
- Production admission remains false until atomicity, redaction, rollback,
  monitoring, and runbook gates have separate evidence.

## Implementation shape

The implementation should not wrap the existing commit-per-stage services and
call that atomic. The transaction-safe path needs one of these explicit shapes:

- extract no-commit core functions from projection, statement packet, and
  operator-review materializers, then call those cores inside one outer
  transaction; or
- add an explicit `commit=False`/`flush_only=True` mode to the existing
  materializers, with tests proving no internal commit occurs in atomic mode.

The preferred shape is no-commit core extraction because it makes the persistence
boundary obvious: public/legacy materializers may own their existing commits,
while the new atomic service owns exactly one transaction around the three SEC
XBRL stages.

The atomic service should have a narrow input contract:

- already-loaded governed evidence or an internal redacted proof authority
  packet;
- caller-owned SQLAlchemy session;
- stable client request id;
- source/proof authority hashes;
- optional deterministic fault-injection label for tests only.

The service should return a hash/count/state response with projection set id,
statement packet set id, operator-review workflow id, counts, redaction flags,
and transaction containment flags. It should not return raw values, local paths,
raw storage references, CompanyFacts payloads, accessions, or SEC URLs.

## Fault-injection contract

The implementation slice should support deterministic test-only fault injection
after each stage has flushed but before the final commit:

- after projection set/facts are flushed;
- after statement packet set/rows are flushed;
- after operator-review workflow is flushed;
- after review rows are flushed but before commit.

Each injected failure must leave zero newly persisted SEC XBRL projection,
statement packet, workflow, and review rows for the attempted request. This is
the proof that the transaction boundary is real rather than narrative.

## Sequencing after atomic persistence

Operator API work remains blocked until the atomic service is proven. Once the
atomic persistence slice lands, the next slices should proceed in this order:

- freeze an operator API contract that accepts only server-owned/redacted
  authority handles, not raw operator paths or CompanyFacts payloads;
- implement the API with the atomic service as the only admitted persistence
  path;
- add rendered UI controls that call the admitted API rather than reconstructing
  authority client-side;
- add controlled value reveal only after review workflow state, auth ownership,
  and redaction status are all proven;
- add rollback, monitoring, and runbook gates before any production-admission
  decision.

## Non-goals

- no new database tables in this design slice;
- no API route;
- no UI;
- no value reveal;
- no live SEC network access;
- no Arelle invocation;
- no raw evidence persistence;
- no production-readiness claim;
- no broad refactor of unrelated Layer 3 materializers.

## Acceptance criteria for the implementation slice

- Add an atomic orchestration service or transaction wrapper with an explicit
  caller-owned session boundary.
- Add tests proving rollback after injected failures at each stage:
  projection-created/packet-not-created, packet-created/workflow-not-created,
  workflow-created/review-rows-not-created.
- Add tests proving successful commit creates exactly one coherent projection
  set, statement packet set, operator-review workflow, and expected redacted rows.
- Add tests proving raw values, local paths, SEC URLs, accessions, and raw
  CompanyFacts/storage payloads do not appear in public response or persisted
  review state.
- Preserve existing validate-only diagnostics and default blocked reports.
- Keep production admission false and do not expose API/UI in the same slice.

## Tier and review posture

The implementation slice is Tier 2 because it changes persistence semantics and
will become the basis for future operator workflow activation. It requires
risk-assessed documentation, targeted rollback/redaction/idempotency tests, and
explicit review of transaction boundaries before any API/UI or controlled value
release work builds on it.

## Next posture

After this design gate, the next concrete implementation should be:

`sec_xbrl_transaction_safe_operator_review_persistence_v1`.

Only after that implementation is proven should the roadmap proceed to an
operator API contract, rendered UI controls, controlled value reveal, monitoring,
rollback runbooks, and production-admission gates.

## Implementation progress

The first transaction-safe implementation step is now an opt-in atomic mode on
the offline evidence orchestrator. The existing default remains stage-owned
commits for backward compatibility, but `single_transaction=True` runs projection
materialization, statement-packet materialization, and operator-review workflow
opening with no internal stage commits, then performs one outer commit on the
caller-owned session.

The atomic path adds deterministic test-only fault injection after each flushed
stage:

- `after_projection_flush`;
- `after_statement_packet_flush`;
- `after_operator_review_workflow_flush`.

The proof-capability diagnostic remains a later S1 proof slice. That slice
should call the isolated orchestrator with `single_transaction=True` and block
readiness if the isolated response does not prove both
`single_transaction_claimed=true` and
`existing_materializers_commit_per_stage=false`.

Review-debt closeout tightens the first atomic implementation step by rejecting
`commit=false` outside `single_transaction=true` and by failing closed when an
atomic run sees only a partial idempotent replay across the projection,
statement-packet, and operator-review workflow stages. A mixed replay cannot
claim a single transaction boundary; only a fresh all-new atomic run or a
completed all-stage replay is admissible.

This is still not a production-admission claim. It advances the transaction
boundary required before API/UI activation, but the future gates remain:
live validation against operator evidence, broader filing authority repair,
operator API contract, UI controls, controlled value reveal authorization,
monitoring, rollback runbooks, and final production-admission review.
