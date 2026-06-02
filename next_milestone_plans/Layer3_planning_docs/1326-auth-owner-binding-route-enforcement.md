# 1326 - SEC XBRL Auth Owner-Binding Route Enforcement

Milestone: `sec_xbrl_nonlocal_in_app_auth_owner_binding_route_enforcement_v1_tier2`

Base authority: `project6-origin/main` at
`bea8a49ccea009afb85f7473da9675734dc059e1`

Prior milestone:
`sec_xbrl_nonlocal_in_app_auth_owner_binding_table_implementation_v1_tier2`

## Status

Branch-local Tier-2 route-enforcement implementation entry.

This slice wires the existing SEC XBRL protected route families to the landed
hash-only auth-binding receipt service. It changes API behavior only for the
already-admitted SEC XBRL operator-review, value-reveal authority, controlled
value-reveal submit, and controlled-submit status routes.

It does not add schema, migrations, `models.py`, source acquisition, Arelle
subprocess invocation, raw runtime artifacts, UI, default-on behavior,
export/delivery, provider dispatch, redaction-posture changes, or a
production-readiness claim.

## Claim Ledger

Repo-confirmed:

- `1325-auth-owner-binding-table-implementation.md` landed the
  `L3SecXbrlAuthBindingReceipt` table, model, and service.
- `backend/app/core/config.py` already admits `AUTH_OWNER=none` for local
  single-operator development and requires `AUTH_OWNER=proxy` plus
  `TRUSTED_PROXY_MODE=true` for nonlocal deployment mode.
- The protected SEC XBRL route families are present in
  `backend/app/api/layer3.py`: workflow status, decision submit/status,
  value-reveal authority prepare, controlled value-reveal submit, and
  controlled-submit status.

Inference:

- Source-only binding is too coarse for separate read/write and owner/auditor
  route families. The durable binding must prove source, route,
  owner/workspace identity, role, and policy context; later protected access
  may reuse only explicitly route-compatible prior write bindings for
  downstream/status routes.

## Implemented Contract

Implemented runtime policy service:

- `backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py`
  derives hash-only `actor_ref_hash` and `workspace_ref_hash` from server-owned
  context.
- In local development (`AUTH_OWNER=none`), it uses deterministic local
  single-operator hashes.
- In proxy mode (`AUTH_OWNER=proxy`), it requires `TRUSTED_PROXY_MODE=true` and
  configured proxy identity/workspace headers.
- It rejects caller-supplied auth/security/raw identity, source, value,
  default-on, Arelle, and export/delivery override fields.

Implemented route enforcement:

- workflow status requires an existing workflow auth binding before returning a
  status projection;
- decision submit requires an existing workflow auth binding before recording a
  decision, then records an auth binding for the decision receipt before
  returning it;
- decision status requires an existing decision auth binding before returning a
  status projection;
- value-reveal authority prepare requires an existing decision auth binding
  before preparing authority, then records an auth binding for the authority
  receipt before returning it;
- controlled value-reveal submit requires an existing authority auth binding
  before returning transient revealed values, then records an auth binding for
  the submit receipt before returning it;
- controlled-submit status requires an existing submit auth binding before
  returning the hash/count-only status projection.

Implemented service reconciliation:

- `require_sec_xbrl_owner_binding(...)` accepts source receipt id or source
  basis hash.
- It still checks that the current route family is admitted for the source kind
  and that the current policy decision role is admitted for the route.
- It compares stored and current `actor_ref_hash`, `workspace_ref_hash`, and
  role.
- Exact-route matches compare the stored and current policy hash.
- Route-compatible matches are limited to explicitly admitted downstream/status
  transitions: decision submit to decision status and value-reveal authority,
  value-reveal authority to controlled submit, and controlled submit to
  controlled-submit status.
- Auditor/read bindings do not authorize owner/write routes. This supersedes
  the earlier one-binding-per-source wording with a
  source/route/actor/workspace/role-scoped binding contract.

## Rollback And Containment

Rollback:

- revert the route calls and the new runtime policy service;
- the route-enforcement slice itself added no table, model, or migration, but
  the later review-thread closeout adds a migration that narrows auth-binding
  uniqueness to source/route/actor/workspace/role. Rollback for that closeout
  is owned by its migration and must preserve existing SEC XBRL receipt rows.

Containment:

- existing unbound source receipts are not backfilled or rewritten;
- protected route reads and downstream value-reveal operations fail closed when
  a source receipt has no auth binding;
- mutating routes do not return a newly-created source receipt unless the
  auth-binding write succeeds;
- source receipt creation and auth-binding creation are not yet one database
  transaction because the existing receipt services commit internally before
  the API layer records the auth binding. If binding creation fails after source
  receipt creation, the response is blocked and the unbound receipt remains
  inaccessible until separate repair/backfill authority is admitted. This
  atomicity/backfill gap remains the next Tier-2 design/implementation risk and
  is not closed by route/actor-scoped uniqueness alone.

## Original Route-Enforcement Non-Goals

- the original route-enforcement slice added no schema, model, or Alembic
  change; this later review-thread closeout does add the scoped uniqueness
  migration described above;
- no source acquisition or live SEC network behavior;
- no Arelle subprocess invocation;
- no raw value default-on behavior;
- no export/delivery or provider dispatch;
- no UI or operator workflow expansion;
- no production-readiness claim;
- no final financial-statement semantics or cross-company comparability claim.

## Verification Plan

Minimum verification for this slice:

- focused auth-binding and operator-review workflow tests;
- full `backend/tests/test_sec_xbrl*.py` suite;
- focused nonlocal/default-on/value-reveal API subset;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- `python -m py_compile` over touched Python files;
- JSON validation for changed manifests and committed SEC XBRL reports;
- redaction and residual-magnitude scan over committed SEC XBRL reports;
- `git diff --check`.
