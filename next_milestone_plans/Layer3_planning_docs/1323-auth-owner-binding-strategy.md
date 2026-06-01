# 1323 - SEC XBRL In-App Auth Owner-Binding Strategy

Milestone: `sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1`

Base authority: `project6-origin/main` at
`0326a4afbae78abeff46ae56eee71d855351677b`

Prior milestone: `sec_xbrl_nonlocal_in_app_auth_policy_validation_v1`

## Status

Branch-local Tier-1 validate-only diagnostic/report/test pass.

This pass selects the future owner-binding persistence strategy for SEC XBRL
in-app auth. It does not implement auth middleware, API dependencies, route
behavior changes, config defaults, schema, `models.py`, Alembic migrations,
durable persistence, owner-binding writes, UI, operator workflow changes,
source acquisition, Arelle execution, value reveal defaults, export/delivery,
provider dispatch, raw runtime artifacts, redaction-posture changes, or a
production-readiness claim.

## Claim Ledger

Repo-confirmed:

- `next_milestone_plans/Layer3_planning_docs/1322-in-app-auth-policy-validation.md`
  names `sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1` as the next
  posture.
- `diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json`
  reports `decision: sec_xbrl_in_app_auth_policy_validation_passed`,
  `blocking_reasons: []`, and
  `owner_binding_strategy_selected_for_runtime: false`.
- Current SEC XBRL protected route families remain pre-runtime auth policy
  surfaces in `backend/app/api/layer3.py`; the route signatures depend on
  `get_db`, not on a repo-owned operator auth dependency.
- Current SEC XBRL receipt families are not uniformly owner-bound:
  `L3SecXbrlOperatorReviewWorkflow`, `L3SecXbrlOperatorReviewDecision`, and
  `L3SecXbrlControlledValueRevealSubmitReceipt` have no actor/workspace
  binding columns, while `L3SecXbrlValueRevealAuthorityReceipt` has a partial
  `operator_actor_hash` but no workspace binding.
- The relevant receipt migrations are `0040`, `0042`, `0044`, and `0045`;
  this pass reads them for strategy evidence but does not modify them.

Carried-forward and still current unless a later implementation changes it:

- value reveal remains explicit and controlled, not default-on;
- export/delivery is a separate exfiltration-class gate;
- source acquisition, corpus-validation Arelle execution, provider dispatch,
  and production/nonlocal readiness remain separately blocked;
- final financial-statement semantics and cross-company comparability remain
  non-admitted.

Inference:

- Because owner/workspace binding is mixed across already-landed SEC XBRL
  receipt families, complete cross-owner isolation cannot be claimed by only
  wiring the existing policy validation into routes.
- A separate hash-only auth-binding receipt/table is the narrowest future
  persistence strategy because it can bind existing receipt ids and basis
  hashes uniformly without rewriting every existing receipt contract.

## Selected Strategy

Selected strategy:
`separate_hash_only_auth_binding_receipt_table`.

Rejected strategy:
`add_columns_to_each_existing_sec_xbrl_receipt_table`.

Rationale:

- A column-per-existing-receipt strategy would touch multiple landed receipt
  contracts and require per-service propagation/backfill logic across workflow,
  decision, value-reveal authority, and controlled-submit receipts.
- The existing value-reveal authority receipt already has one partial actor
  hash, which makes a column retrofit easy to make inconsistent unless every
  existing and future receipt surface is updated together.
- A separate binding receipt/table can use one uniform contract:
  `source_receipt_kind`, `source_receipt_id`, `source_receipt_basis_hash`,
  `route_family`, `actor_ref_hash`, `workspace_ref_hash`, `policy_hash`,
  `binding_basis_hash`, `binding_state`, and `binding_schema_id`.
- The separate table keeps value reveal and export/delivery as separate gates;
  owner binding only proves the authenticated owner/workspace that admitted a
  receipt.

This selection is a strategy decision only. The table, model, migration,
service, route dependency, and cross-owner enforcement remain future Tier-2
work.

## Future Tier-2 Contract

A later implementation must:

- add a `L3SecXbrlAuthBindingReceipt` model and
  `l3_sec_xbrl_auth_binding_receipt` migration, or stop and document why the
  selected strategy is no longer valid;
- use only hash-only actor/workspace refs derived from server-owned in-app auth
  context;
- reject caller-supplied actor, workspace, role, policy, proxy header, local
  path, URL, token, value-store, raw value, source-acquisition, Arelle,
  default-on, and export/delivery override fields;
- bind each mutating receipt to exactly one binding receipt by
  `source_receipt_kind + source_receipt_id`, with a unique
  `binding_basis_hash`;
- check binding ownership before status reads and downstream value-reveal
  operations;
- preserve rollback/containment notes because this is schema and persistence
  work;
- seek independent review when practical under the softened SEC XBRL Tier-2
  policy.

## Stop Conditions

Stop before implementation if the next pass would require any of the following
without a separate explicit Tier-2 implementation instruction:

- runtime auth dependency or middleware changes;
- SEC XBRL route behavior changes;
- config default or `AUTH_OWNER` changes;
- schema, `models.py`, Alembic, owner-binding persistence, or audit
  persistence;
- value reveal default-on or automatic value delivery;
- source acquisition, live SEC network, or Arelle subprocess execution;
- export/delivery, provider dispatch, public URL, or destination selection;
- production-readiness claim;
- raw identity, accessions, SEC URLs, local paths, raw values, or residual
  magnitude artifacts.

## Branch-Local Verification

Branch-local verification on
`codex/secxbrl-auth-owner-binding-strategy`:

- Focused owner-binding strategy test:
  `python -m pytest ./backend/tests/test_sec_xbrl_auth_owner_binding_strategy.py -q`
  - PASS: `6 passed`.
- Focused nonlocal/default-on API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- Full SEC XBRL suite:
  `python -m pytest <backend/tests/test_sec_xbrl*.py files> -q`
  - PASS: `335 passed, 4 warnings`.
- `python -m py_compile` over touched Python files:
  - PASS.
- Report regeneration:
  `python ./diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy.py
  --output diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy-report.json`
  - PASS:
    `decision=sec_xbrl_auth_owner_binding_strategy_selected`.
- JSON validation, target-selection validation, progress check,
  redaction/residual scan, and `git diff --check`:
  - PASS: changed JSON parsed with `utf-8-sig`; all `58` SEC XBRL reports
    parsed with `utf-8-sig`; target-selection validation PASS; progress check
    PASS; report redaction scan found `0` raw identity/path/SEC
    URL/accession hits; residual-magnitude scan found `0` hits; `git diff
    --check` PASS.
