# 1325 - SEC XBRL Auth Owner-Binding Table Implementation

Milestone: `sec_xbrl_nonlocal_in_app_auth_owner_binding_table_implementation_v1_tier2`

Base authority: `project6-origin/main` at
`031c66e555d2dc47b684537ad59f6bf7c2b772bb`

Prior milestone: `sec_xbrl_nonlocal_in_app_auth_owner_binding_table_design_v1`

## Status

Branch-local Tier-2 schema/persistence implementation entry.

This slice implements the additive hash-only auth-binding receipt table,
model, migration, service, and focused tests selected by the prior design. It
does not wire route auth dependencies, change API behavior, change config
defaults, expose values, enable default-on behavior, run source acquisition,
invoke Arelle, export/deliver data, dispatch providers, persist raw runtime
artifacts, change redaction posture, or claim production readiness.

## Claim Ledger

Repo-confirmed:

- `1324-auth-owner-binding-table-design.md` selected the future
  `L3SecXbrlAuthBindingReceipt` model,
  `l3_sec_xbrl_auth_binding_receipt` table,
  `0046_layer3_sec_xbrl_auth_binding_receipt.py` migration, and
  `layer3_sec_xbrl_auth_binding.py` service.
- Current main before this branch was
  `031c66e555d2dc47b684537ad59f6bf7c2b772bb`; the prior Alembic head was
  `0045_layer3_sec_xbrl_controlled_value_reveal_submit`.
- The current SEC XBRL receipt families remain mixed owner-binding surfaces;
  a separate additive binding receipt table is still the narrowest uniform
  owner/workspace binding strategy.

Inference:

- Route-level enforcement should remain future work until the additive binding
  table/service contract is landed and verified independently.
- Existing source receipts without an auth-binding receipt must be treated as
  unbound by future route wiring; this slice does not backfill or rewrite them.

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `backend/app/models/models.py`: adds auth-binding constants and
  `L3SecXbrlAuthBindingReceipt`.
- `backend/app/models/__init__.py`: exports the new model.
- `backend/alembic/versions/0046_layer3_sec_xbrl_auth_binding_receipt.py`:
  adds one additive auth-binding receipt table, constraints, and indexes.
- `backend/app/services/layer3_sec_xbrl_auth_binding.py`: records, inspects,
  and validates hash-only source receipt auth bindings.

Supporting surfaces:

- `backend/tests/test_sec_xbrl_auth_binding_receipt.py`: focused model,
  migration, service, idempotency, fail-closed, redaction, and owner-context
  tests.
- Layer 3 progress/proof manifests: record Tier-2 surface and verification
  state.

## Implemented Contract

Implemented model/table:

- `L3SecXbrlAuthBindingReceipt`;
- `l3_sec_xbrl_auth_binding_receipt`;
- unique `client_request_id`;
- unique `binding_basis_hash`;
- unique tuple `source_receipt_kind`, `source_receipt_id`, `route_family`,
  `actor_ref_hash`, `workspace_ref_hash`, and `role`;
- checks for binding policy, owner-bound state, redaction policy, source kind,
  route family, and role;
- indexes on source basis, actor/workspace hashes, policy hash, and route
  family.

Implemented service functions:

- `record_sec_xbrl_auth_binding(...)`;
- `inspect_sec_xbrl_auth_binding(...)`;
- `require_sec_xbrl_owner_binding(...)`.

The service validates:

- source receipt kind, source receipt id, and source receipt basis hash;
- source-kind and route-family compatibility;
- server-derived hash-only actor/workspace refs and policy hash;
- owner/auditor role constraints;
- idempotency by request id and binding basis;
- one immutable binding per source/route/actor/workspace/role tuple;
- missing source receipt, unsupported source kind, unsupported route, unsupported
  role, rejected policy decision, raw/caller identity fields, route mismatch,
  stale policy hash, and cross-owner context fail closed.

Review-thread closeout clarification: source-only uniqueness was too coarse
for separate status/read, write, owner, and auditor bindings. Protected access
must compare current actor/workspace refs and role, then require either an
exact route binding with matching policy hash or an explicitly admitted
route-compatible prior write binding for downstream/status access. Auditor/read
bindings must not authorize owner/write routes.

## Rollback And Containment

Rollback:

- downgrade drops indexes first and then drops
  `l3_sec_xbrl_auth_binding_receipt`;
- no existing SEC XBRL receipt table is altered;
- no source receipt, projection, statement packet, value-reveal authority,
  controlled-submit, value-store, API, UI, or config default is changed.

Containment:

- route auth enforcement is not wired by this slice, so existing route behavior
  is unchanged;
- future protected route wiring must require a matching binding before status
  reads or downstream value-reveal operations;
- future protected route wiring must interpret matching binding as matching
  actor/workspace refs and role, plus an exact route policy-hash match or an
  explicitly route-compatible prior write binding;
- unbound source receipts remain unmodified and must fail closed only when a
  future route-enforcement slice admits that behavior;
- this slice stores only hashes, route family, role, policy id/hash, source kind
  and source basis; it does not store raw actor identity, workspace identity,
  proxy headers, local paths, SEC accessions/URLs, raw values, residual
  magnitudes, source-acquisition directives, Arelle directives, default-on
  directives, export/delivery directives, provider secrets, or destination
  names.

## Branch-Local Verification

Branch-local verification on
`codex/secxbrl-auth-binding-table-impl`:

- Focused auth-binding receipt tests:
  `python -m pytest ./backend/tests/test_sec_xbrl_auth_binding_receipt.py -q`
  - PASS: `5 passed`.
- Focused auth-binding plus owner-binding strategy tests:
  `python -m pytest ./backend/tests/test_sec_xbrl_auth_binding_receipt.py
  ./backend/tests/test_sec_xbrl_auth_owner_binding_strategy.py -q`
  - PASS: `11 passed`.
- Focused nonlocal/default-on API tests:
  `python -m pytest ./backend/tests/test_layer3_api.py -q -k
  "deployment_profile or default_arelle_cutover or arelle_sidecar or
  default_on or value_reveal"`
  - PASS: `27 passed, 249 deselected, 3 warnings`.
- Full SEC XBRL suite:
  `python -m pytest <31 backend/tests/test_sec_xbrl*.py files> -q`
  - PASS: `340 passed, 3 warnings`.
- `python -m py_compile` over touched model, service, migration, and test files:
  - PASS.
- JSON validation:
  - PASS: changed manifests parse with `utf-8-sig`; `46` SEC XBRL reports
    parse with `utf-8-sig`.
- Target-selection validation:
  `python ./tools/l3-target-selection-validate.py --expect frozen`
  - PASS: `Layer 3 target-selection validation: PASS (frozen)`.
- Progress check:
  `python ./tools/l3-progress-check.py`
  - PASS: `Layer 3 progress state check: PASS`.
- Redaction and residual-magnitude scan over committed SEC XBRL reports:
  - PASS: `46` SEC XBRL reports, `0` raw value-like fields, raw identity key
    values, local paths, URLs, raw SEC accessions, emails, or nonzero
    residual-magnitude payload fields.
- `git diff --check`:
  - PASS: exit code `0`; Git emitted only CRLF working-copy warnings for
    changed files.
