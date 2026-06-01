# 1301 - SEC XBRL Value-Reveal Authority Design

Milestone: `sec_xbrl_value_reveal_authority_design_v1`

Base authority: `project6-origin/main` at `d992cb7be014ea3d3352a315b5aa7ea6107ba1d0`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1300-decision-rendered-submit.md`

## Status

Planning-only Tier-2 risk-assessed design entry.

This document admits no runtime implementation by itself. It does not add or change
`models.py`, Alembic migrations, schema, durable persistence, backend API contracts,
rendered UI, workflow-open behavior, value reveal, default-on behavior, source
acquisition, SEC network execution, Arelle invocation, delivery/export, raw runtime
artifacts, authorization behavior, redaction posture, product-flow docs, or
production-readiness claims.

## Authority

Canonical governance is
`next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`.
Any later value-reveal implementation is Tier 2 because it touches revealed-value
handling, even if the first implementation is only an authority receipt. Under the
softened policy, the implementation must record exact Tier-2 surfaces, use narrow tests,
include rollback or containment notes for schema/persistence changes, seek independent
review when practical, and stop for failed checks, unresolved blocking findings, missing
rollback or containment notes, unclear authority, or an explicit operator instruction
requiring review.

Current repo authority before this design:

- `1260-sec-xbrl-operator-value-reveal.md` defines a governed sibling reveal endpoint:
  value reveal is default-off, explicit, audit-bound, and outside the default product
  surface.
- `1267-sec-xbrl-value-reveal-live-proof.md` records bounded live proof for two filings
  through coherent sidecar, value-store, bridge, dataset, provenance, and reveal-receipt
  authority.
- `1269-sec-xbrl-default-posture-decision.md` selects
  `explicit_operator_only_default_off`; it does not admit default-on value reveal.
- `1286-projection-persistence.md`, `1288-statement-packet-persistence.md`,
  `1291-operator-review-workflow-impl.md`, `1296-decision-receipt-impl.md`,
  `1298-decision-status-api.md`, and `1300-decision-rendered-submit.md` establish the
  newer SEC XBRL path: redacted projection persistence, redacted statement packets,
  durable operator-review workflow, durable operator-review decision receipts, status
  APIs, and a rendered decision submit/status panel.
- `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py` is the existing value
  reveal engine. It requires a feature flag, request schema, actor, explicit operator
  confirmation, sidecar receipt ID/hash, and dataset version ID/hash; it returns values
  only for a successful explicit reveal and persists an audit receipt with hashes and
  counts, not raw values.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` currently leaves
  `reveal_values` blocked after a decision with `requires_separate_value_reveal_freeze`;
  workflow and decision status projections still report `value_reveal_performed=false`.
- `backend/app/models/models.py` stores redacted projection and statement-packet
  authority. `L3SecXbrlProjectionSet` includes `dataset_version_id`,
  `sidecar_receipt_hash`, and `value_store_hash`, but not a client-visible raw value or
  a persisted sidecar receipt ID/hash pair sufficient for direct reveal by the browser.

## Design Decision

The next code-bearing slice should not expose value reveal directly from the rendered
decision UI and should not accept sidecar or dataset authority from the client.

Selected first implementation boundary:

`sec_xbrl_value_reveal_authority_receipt_v1`

It should create a server-owned value-reveal authority receipt over an existing approved
SEC XBRL operator-review decision. The receipt is an eligibility and authority bridge
only. It does not reveal values.

The server, not the browser, resolves the lower-level reveal inputs:

1. decision receipt: `sec_xbrl_operator_review_decision_id` and `decision_basis_hash`;
2. workflow receipt: `sec_xbrl_operator_review_workflow_id` and `workflow_basis_hash`;
3. statement packet: `sec_xbrl_statement_packet_set_id` and `statement_packet_basis_hash`;
4. projection set: `sec_xbrl_projection_set_id`, `projection_basis_hash`,
   `dataset_version_id`, `sidecar_receipt_hash`, and `value_store_hash`;
5. runtime dataset/provenance: matching `dataset_version_id` and dataset hash;
6. sidecar/value-store authority: exactly one READY sidecar receipt and internal value
   store matching the projection's sidecar and value-store hashes.

If any join is missing, ambiguous, stale, mismatched, redaction-invalid, or sourced from a
non-approved decision, the authority receipt request fails closed and creates no partial
authority row.

## Eligibility Predicate

The v1 authority receipt should require all of the following:

- the decision exists and `decision_basis_hash` matches;
- `review_decision == "approved"`;
- `decision_reason_code == "ready_for_next_freeze"`;
- `decision_status == "decision_recorded"`;
- the linked workflow exists, remains `review_ready=true`, and has the same workflow,
  statement-packet, and projection basis hashes recorded by the decision;
- the linked statement packet remains materialized, redacted, and value-redacted;
- the linked projection set remains materialized, redacted, and value-redacted;
- every projection fact and statement-packet row remains `value_redacted=true`;
- the projection authority resolves to exactly one coherent sidecar/value-store/dataset
  bundle;
- raw values, raw resolved fact authority IDs, issuer identity, accessions, raw period
  dates, SEC URLs, local paths, operator contact fields, residual magnitudes, source
  acquisition controls, Arelle invocation controls, delivery/export controls, and
  default-on controls are absent from the request, persisted receipt, status projection,
  and committed proof artifacts.

The first implementation should require `review_exception_count == 0`. If later operator
evidence shows some review exceptions are compatible with reveal, that expansion needs a
separate exception-taxonomy design because it changes the semantics of "approved for
reveal."

## Proposed Durable Shape

Use one additive table:

`l3_sec_xbrl_value_reveal_authority_receipt`

One row records one immutable server-owned authority bridge over one approved SEC XBRL
operator-review decision. The first implementation should admit at most one authority
receipt per decision. Supersession, revocation, expiry, or multi-actor approval requires a
separate lifecycle design.

Required fields:

- `sec_xbrl_value_reveal_authority_receipt_id`: UUID primary key.
- `client_request_id`: idempotency key, unique.
- `authority_basis_hash`: stable hash over the authority receipt basis, unique.
- `authority_schema_id`: `layer3.sec_xbrl_value_reveal_authority_receipt.v1`.
- `sec_xbrl_operator_review_decision_id`.
- `decision_basis_hash`.
- `sec_xbrl_operator_review_workflow_id`.
- `workflow_basis_hash`.
- `sec_xbrl_statement_packet_set_id`.
- `statement_packet_basis_hash`.
- `sec_xbrl_projection_set_id`.
- `projection_basis_hash`.
- `dataset_version_id`.
- `dataset_version_hash`: server-resolved from `DatasetVersion`/provenance, not supplied
  by the browser as reveal authority.
- `sidecar_receipt_id_hash`: hash of the resolved sidecar receipt id, not the raw id if
  status projections do not need it.
- `sidecar_receipt_hash`.
- `value_store_hash`.
- `authority_state`: `ready_for_explicit_value_reveal`.
- `authority_policy_id`: `sec_xbrl_approved_decision_bound_value_reveal_authority_v1`.
- `redaction_policy`: `sec_xbrl_value_reveal_authority_hashes_only_v1`.
- `operator_actor_hash`: optional only if the authority-receipt step itself is
  actor-attested; raw actor text is not stored.
- `authority_summary_json`: counts, policy IDs, and redacted reason codes only.
- `negative_invariants_json`: explicit false values for default-on, value reveal
  performed, source acquisition, Arelle invocation, delivery/export, raw value persisted,
  and frontend durable authority.
- `created_at`, `updated_at`.

Indexes should cover decision id, authority basis hash, dataset version id, sidecar hash,
and projection basis hash.

The authority receipt may store the raw sidecar receipt ID only if the implementation
keeps it server-internal and proves it never appears in committed artifacts or public
status projections. If that cannot be proven, the first implementation should store a hash
in the authority receipt and resolve the raw ID only transiently from server-owned storage
during the later reveal-submit request.

## API Boundary For The First Implementation

The first implementation may add a backend authority endpoint only:

`POST /api/v1/layer3/sec-xbrl/value-reveal/authority/prepare`

Request fields:

- `client_request_id`
- `authority_mode=sec_xbrl_value_reveal_authority_receipt_v1`
- `operator_decision=prepare_sec_xbrl_value_reveal_authority`
- `sec_xbrl_operator_review_decision_id`
- `decision_basis_hash`
- optional bounded `operator_attestation` only if raw text is hashed and never returned

Response fields:

- authority receipt id/hash/ref;
- linked decision/workflow/packet/projection basis hashes;
- dataset/version, sidecar, and value-store hashes or hashed refs only;
- eligibility status and redacted blocked reasons;
- negative invariant booleans;
- next allowed action:
  `submit_explicit_sec_xbrl_value_reveal_from_authority_receipt`;
- no revealed facts and no raw values.

Rejected request fields include sidecar receipt ID/hash as client authority,
dataset version ID/hash as client authority, raw value filters, SEC URLs, local paths,
accessions, issuer identity, actor contact fields, source acquisition inputs, Arelle
runtime inputs, delivery/export inputs, default-on toggles, and frontend durable
authority fields.

## Later Reveal Submit Boundary

Only after `sec_xbrl_value_reveal_authority_receipt_v1` lands and current-main
verification is clean should a later implementation add:

`sec_xbrl_controlled_value_reveal_submit_v1`

That later slice may submit an explicit reveal from the authority receipt. It should
server-resolve the sidecar/dataset inputs and call the existing governed reveal engine
rather than trusting browser-supplied lower-level authority. The later request must require
actor attestation and explicit reveal confirmation, and it must remain feature-flagged and
default-off. A flag-off request must block with a stable reason and create no receipt.

Revealed values may appear only in that explicit reveal response and any separately
admitted transient rendered reveal panel. They must not be persisted into SEC XBRL
projection, statement-packet, workflow, decision, authority-receipt, or status tables.
Status projections and committed reports remain hash/count-only.

## Modularity And Scalability

Keep the boundary modular:

- a small SEC XBRL authority service owns decision-to-reveal eligibility;
- the existing SEC EDGAR/Arelle reveal service remains the lower-level reveal engine;
- the rendered workbench, if later admitted, uses the SEC XBRL authority/reveal APIs only;
- projection and packet persistence continue to own redacted statement authority and do
  not learn raw values;
- source acquisition and Arelle invocation remain outside the request path.

This keeps future scaling tractable: multiple filings or operators can be added by
extending authority receipt lifecycle and indexes without changing projection row shape or
turning the default product/status surfaces into value surfaces.

## Rollback And Containment

For the first implementation:

- the migration must be additive and downgrade must remove only the new authority receipt
  table/indexes;
- failed preparation must leave no partial authority receipt row;
- replaying the same `client_request_id` or same `authority_basis_hash` must return the
  existing receipt;
- disabling the later value-reveal feature flag must keep reveal submit blocked even when
  an authority receipt exists;
- deleting or archiving runtime receipts is not part of rollback; no files are deleted by
  this design.

If a later implementation persists raw sidecar receipt IDs, introduces auth policy, stores
revealed values, allows transient browser rendering of values, or admits default-on
behavior, rollback must be redesigned before that PR lands.

## Verification Required For First Implementation

Minimum local verification:

- focused authority receipt model/service/API tests;
- migration upgrade/downgrade or project-standard migration proof;
- approved-decision eligibility test;
- non-approved decision, wrong reason code, and nonzero review-exception rejection tests;
- mismatched decision/workflow/packet/projection hash rejection tests;
- missing, ambiguous, or stale sidecar/value-store/dataset authority rejection tests;
- raw request field rejection tests;
- idempotent replay tests for `client_request_id` and `authority_basis_hash`;
- partial-write rollback test;
- status projection redaction test;
- proof that default workflow/decision/product/status surfaces still report
  `value_reveal_performed=false`;
- proof that no values are returned or persisted by the authority receipt;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- focused SEC XBRL tests over touched service/API/model paths;
- full `backend/tests/test_sec_xbrl*.py` suite;
- py_compile on touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed SEC XBRL committed reports or proof artifacts;
- residual-magnitude scan across changed SEC XBRL committed reports or proof artifacts;
- `git diff --check`.

CI must be green before merge. Independent review should be requested because this is the
authority gate immediately before controlled value reveal. Merge is blocked by failed
required checks, unresolved critical/blocking findings, missing rollback or containment
notes, unclear authority, or an explicit operator instruction requiring review.

## Non-Goals Preserved

- no value reveal in this design pass;
- no default-on value reveal;
- no default-on Arelle cutover;
- no source acquisition;
- no live SEC network;
- no Arelle subprocess invocation;
- no raw values persisted in SEC XBRL tables;
- no raw values committed;
- no issuer identity, accession, SEC URL, local path, storage root, operator contact, or
  raw actor text in committed artifacts;
- no rendered value panel;
- no delivery/export;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim.

## Next Slice

`sec_xbrl_value_reveal_authority_receipt_v1`

The next slice may implement only the server-owned authority receipt described here. It
must stop before returning revealed values. Controlled reveal submit, rendered reveal UI,
and default-on admission remain separate later milestones.
