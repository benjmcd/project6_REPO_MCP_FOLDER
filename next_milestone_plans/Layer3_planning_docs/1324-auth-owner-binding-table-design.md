# 1324 - SEC XBRL Auth Owner-Binding Table Design

Milestone: `sec_xbrl_nonlocal_in_app_auth_owner_binding_table_design_v1`

Base authority: `project6-origin/main` at
`1116faf84d28e8a70f6657d867552bb9ca2b3c8f`

Prior milestone: `sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1`

## Status

Branch-local docs-only design/pre-review entry for a future Tier-2
implementation.

This pass freezes the future table, model, migration, service, rollback, and
verification contract for SEC XBRL in-app auth owner binding. It does not
implement auth middleware, API dependencies, route behavior changes, config
defaults, schema, `models.py`, Alembic migrations, durable persistence,
owner-binding writes, UI, operator workflow changes, source acquisition,
Arelle execution, value reveal defaults, export/delivery, provider dispatch,
raw runtime artifacts, redaction-posture changes, or a production-readiness
claim.

## Claim Ledger

Repo-confirmed:

- `diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy-report.json`
  reports `decision: sec_xbrl_auth_owner_binding_strategy_selected`,
  `blocking_reasons: []`, and
  `selected_strategy: separate_hash_only_auth_binding_receipt_table`.
- Current SEC XBRL receipt families are present but not uniformly
  owner-bound: workflow receipt absent, decision receipt absent,
  value-reveal authority receipt partial, controlled-submit receipt absent.
- Current SEC XBRL Alembic chain ends at
  `0045_layer3_sec_xbrl_controlled_value_reveal_submit.py`; a future
  owner-binding migration should use `down_revision =
  "0045_layer3_sec_xbrl_controlled_value_reveal_submit"` unless main changes
  before implementation.
- Current SEC XBRL migrations use `create_table_idempotent`,
  `create_index_idempotent`, `drop_index_idempotent`, and
  `drop_table_idempotent`; future implementation should follow that pattern.
- Candidate B owner-access policy provides repo-local precedent for
  server-derived `actor_ref_hash`, workspace/tenant hash, `policy_hash`,
  request-field rejection, and cross-owner binding checks.

Carried-forward and still current unless a later implementation changes it:

- value reveal remains explicit and controlled, not default-on;
- export/delivery is a separate exfiltration-class gate;
- source acquisition, corpus-validation Arelle execution, provider dispatch,
  and production/nonlocal readiness remain separately blocked;
- final financial-statement semantics and cross-company comparability remain
  non-admitted.

Inference:

- The future implementation should bind every mutating SEC XBRL receipt to a
  hash-only owner/workspace policy decision in one separate receipt table
  rather than adding per-receipt owner columns.
- Read-side cross-owner isolation should be enforced by looking up this binding
  before returning receipt status for any protected SEC XBRL route family.
- The table contract below extends the prior strategy report's minimum field
  list with receipt-grade `client_request_id`, `role`, `binding_policy_id`,
  `redaction_policy`, `binding_summary_json`, `negative_invariants_json`, and
  `updated_at` fields. Those additions are design choices grounded in current
  SEC XBRL receipt tables and the Candidate B owner-access policy precedent,
  not claims that the strategy report already emitted those fields.

## Selected Future Artifacts

Future migration:
`backend/alembic/versions/0046_layer3_sec_xbrl_auth_binding_receipt.py`.

Future model:
`L3SecXbrlAuthBindingReceipt` in `backend/app/models/models.py`.

Future table:
`l3_sec_xbrl_auth_binding_receipt`.

Future service:
`backend/app/services/layer3_sec_xbrl_auth_binding.py`.

Future route wiring:
central SEC XBRL in-app auth dependency or service call from the existing
protected route families in `backend/app/api/layer3.py`. The future runtime
must use server-owned auth context, not request JSON fields or arbitrary proxy
headers.

## Table Contract

The required minimum anchors from the selected strategy remain
`source_receipt_kind`, `source_receipt_id`, `source_receipt_basis_hash`,
`route_family`, `actor_ref_hash`, `workspace_ref_hash`, `policy_hash`,
`binding_basis_hash`, `binding_state`, `binding_schema_id`, and `created_at`.
The additional receipt-grade fields below are included so the future migration
has a complete idempotency, role, policy, redaction, and negative-invariant
contract before implementation starts.

Columns:

- `sec_xbrl_auth_binding_receipt_id`: `String(36)`, primary key.
- `client_request_id`: `String(255)`, not null.
- `binding_basis_hash`: `String(64)`, not null.
- `binding_schema_id`: `String(128)`, not null.
- `binding_policy_id`: `String(128)`, not null, constant
  `sec_xbrl_repo_owned_in_app_auth_owner_binding_v1`.
- `binding_state`: `String(64)`, not null, constant
  `owner_bound`.
- `source_receipt_kind`: `String(64)`, not null.
- `source_receipt_id`: `String(36)`, not null.
- `source_receipt_basis_hash`: `String(64)`, not null.
- `route_family`: `String(96)`, not null.
- `actor_ref_hash`: `String(64)`, not null.
- `workspace_ref_hash`: `String(64)`, not null.
- `role`: `String(32)`, not null, constrained to `owner` or `auditor`.
- `policy_hash`: `String(64)`, not null.
- `redaction_policy`: `String(128)`, not null, constant
  `hash_only_actor_workspace_policy_refs_v1`.
- `binding_summary_json`: `JSON`, not null, default `{}`.
- `negative_invariants_json`: `JSON`, not null, default `{}`.
- `created_at`: timezone-aware `DateTime`, not null.
- `updated_at`: timezone-aware `DateTime`, not null.

Admitted `source_receipt_kind` values:

- `operator_review_workflow`;
- `operator_review_decision`;
- `value_reveal_authority`;
- `controlled_value_reveal_submit`.

Admitted `route_family` values:

- `sec_xbrl_operator_review_workflow_status_read`;
- `sec_xbrl_operator_review_decision_submit_write`;
- `sec_xbrl_operator_review_decision_status_read`;
- `sec_xbrl_value_reveal_authority_prepare_write`;
- `sec_xbrl_controlled_value_reveal_submit_write`;
- `sec_xbrl_controlled_value_reveal_submit_status_read`.

Constraints:

- primary key on `sec_xbrl_auth_binding_receipt_id`;
- unique `client_request_id`;
- unique `binding_basis_hash`;
- unique tuple `source_receipt_kind`, `source_receipt_id`, `route_family`,
  `actor_ref_hash`, `workspace_ref_hash`, and `role`;
- check `binding_policy_id =
  'sec_xbrl_repo_owned_in_app_auth_owner_binding_v1'`;
- check `binding_state = 'owner_bound'`;
- check `redaction_policy = 'hash_only_actor_workspace_policy_refs_v1'`;
- check `source_receipt_kind` is one of the admitted receipt kinds;
- check `route_family` is one of the admitted protected SEC XBRL route
  families;
- check `role IN ('owner', 'auditor')`.

Indexes:

- `ix_l3_sec_xbrl_auth_binding_source_basis` on
  `source_receipt_kind`, `source_receipt_basis_hash`;
- `ix_l3_sec_xbrl_auth_binding_actor_workspace` on
  `actor_ref_hash`, `workspace_ref_hash`;
- `ix_l3_sec_xbrl_auth_binding_policy` on `policy_hash`;
- `ix_l3_sec_xbrl_auth_binding_route_family` on `route_family`.

No foreign keys are selected in this design. The source receipt ids span
multiple tables, so source existence must be enforced by the owner-binding
service before writing a binding receipt. This avoids polymorphic nullable
foreign-key columns and keeps future rollback contained to the new table.

## Binding Basis

`binding_basis_hash` should be a stable hash over:

- `binding_schema_id`;
- `binding_policy_id`;
- `source_receipt_kind`;
- `source_receipt_id`;
- `source_receipt_basis_hash`;
- `route_family`;
- `actor_ref_hash`;
- `workspace_ref_hash`;
- `role`;
- `policy_hash`.

The basis must not include raw operator identity, workspace names, proxy
headers, emails, local paths, SEC accession numbers, SEC URLs, value-store
payloads, raw values, residual magnitudes, source-acquisition directives,
Arelle directives, default-on directives, export/delivery directives, provider
secrets, or destination names.

## Service Contract

Future service functions:

- `record_sec_xbrl_auth_binding(...)`: validates server-derived auth policy
  output, loads the source receipt by kind/id/basis, derives the binding basis,
  performs idempotent write by `client_request_id`, `binding_basis_hash`, and
  the source/route/actor/workspace/role tuple, and returns a redacted binding
  summary.
- `inspect_sec_xbrl_auth_binding(...)`: loads a binding by source receipt
  kind/id or kind/basis and returns only hash refs, route family, role,
  policy id/hash, state, and negative invariant booleans.
- `require_sec_xbrl_owner_binding(...)`: checks that the current route family
  is admitted for the selected source kind, then compares the current auth
  context hash refs, role, and exact or route-compatible binding before any
  protected status read or downstream value-reveal operation returns. Exact
  route matches must compare the stored policy hash. Route-compatible matches
  are limited to the explicitly admitted downstream/status transitions and do
  not allow auditor/read bindings to authorize owner/write routes.

Write order:

1. Existing receipt service records the governed SEC XBRL receipt.
2. Auth-binding service records the binding receipt in the same DB session or
   stops the API response with a fail-closed error if the binding cannot be
   recorded.
3. API response may include a redacted `auth_binding_ref` and
   `auth_binding_basis_hash` only after both writes succeed.

Read order:

1. Route dependency derives server-owned auth context.
2. Auth-binding service loads the source receipt binding.
3. It denies cross-owner, missing-binding, stale-policy on exact-route matches,
   source-kind route incompatibility, route-incompatible prior bindings, or
   current-role route incompatibility before the source status service emits a
   response.

## Rollback And Containment

Rollback:

- downgrade drops indexes first, then drops
  `l3_sec_xbrl_auth_binding_receipt`;
- no existing SEC XBRL receipt table, value-store table, projection table, or
  statement-packet table is altered;
- no backfill is required for rollback because the new table is additive.

Containment:

- if binding writes fail, protected mutating endpoints must fail closed rather
  than returning a receipt without owner binding;
- if a source receipt exists without a binding after implementation, protected
  status reads and downstream value-reveal operations must deny access until a
  governed binding exists or a separate migration/backfill authority is
  admitted;
- the implementation must not delete or rewrite existing unbound receipts.

## Future Implementation Tests

Minimum focused tests for the future Tier-2 implementation:

- migration creates all table columns, constraints, and indexes;
- downgrade removes the new table and indexes without touching existing SEC
  XBRL receipt tables;
- model exposes the selected columns and constants only;
- binding service records one binding per source/route/actor/workspace/role
  tuple and is idempotent by request id, binding basis hash, and that tuple;
- conflicting request id, binding basis, or source/route/actor/workspace/role
  tuple fails closed;
- missing source receipt, wrong source receipt basis hash, unsupported receipt
  kind, unsupported route family, unsupported role, stale policy hash, and
  cross-owner context fail closed;
- protected route status reads deny missing, cross-owner, stale-policy, or
  source-incompatible owner binding;
- downstream/status routes may reuse only explicitly route-compatible prior
  write bindings, and auditor/read bindings must not authorize owner/write
  routes;
- mutating route responses do not return source receipts unless binding write
  succeeds;
- value-reveal authority and controlled-submit flows remain explicit and
  default-off;
- output contains no raw identities, headers, local paths, SEC identifiers,
  raw values, residual magnitudes, source-acquisition directives, Arelle
  directives, export/delivery directives, provider secrets, or destination
  names.

## Verification Plan

Minimum verification for the future Tier-2 implementation:

- focused owner-binding migration/model/service tests;
- focused API tests over all protected route families for anonymous,
  malformed, spoofed-field, unsupported-role, missing-binding, stale-policy,
  and cross-owner cases;
- focused SEC XBRL value-reveal authority and controlled-submit tests to prove
  value reveal remains explicit and default-off;
- Alembic upgrade/downgrade or equivalent migration containment proof;
- full `backend/tests/test_sec_xbrl*.py` suite;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- JSON/report validation for changed manifests and committed reports;
- redaction and residual-magnitude scan over committed SEC XBRL reports;
- `git diff --check`.

## Stop Conditions

Stop before implementation if the next pass would require any of the following
without a separate explicit Tier-2 implementation instruction:

- changing existing SEC XBRL receipt table columns rather than adding the
  separate binding table selected here;
- auth based on caller-supplied JSON fields or arbitrary proxy headers;
- value reveal default-on, automatic value delivery, or export/delivery;
- source acquisition, live SEC network, or Arelle subprocess execution;
- provider dispatch, public URL, destination selection, or production-readiness
  admission;
- raw identity, accessions, SEC URLs, local paths, raw values, or residual
  magnitude artifacts.

## Branch-Local Verification

Branch-local verification on
`codex/secxbrl-auth-binding-table-design`:

- Target-selection validation:
  `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS: `Layer 3 target-selection validation: PASS (frozen)`.
- Progress check:
  `python ./tools/l3-progress-check.py`
  - PASS: `Layer 3 progress state check: PASS`.
- Focused owner-binding strategy test:
  `python -m pytest ./backend/tests/test_sec_xbrl_auth_owner_binding_strategy.py -q`
  - PASS: `6 passed`.
- Focused nonlocal/default-on API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- Full SEC XBRL suite:
  `python -m pytest <30 backend/tests/test_sec_xbrl*.py files> -q`
  - PASS: `335 passed, 4 warnings`.
- `python -m py_compile` over relevant SEC XBRL owner-binding diagnostic/test
  files:
  - PASS.
- JSON/report validation:
  - PASS: changed manifests parse with `utf-8-sig`; `46` SEC XBRL reports
    parse with `utf-8-sig`.
- Redaction and residual-magnitude scan over committed SEC XBRL reports:
  - PASS: `46` SEC XBRL reports, `0` raw value-like fields, raw identity key
    values, local paths, URLs, raw SEC accessions, emails, or nonzero
    residual-magnitude payload fields.
- `git diff --check`:
  - PASS: exit code `0`; Git emitted only CRLF working-copy warnings for the
    two changed JSON manifests.
