# 1327 - SEC XBRL Nonlocal Readiness In-App Auth Reconciliation

Milestone: `sec_xbrl_nonlocal_readiness_in_app_auth_reconciliation_v1`

Base authority: `project6-origin/main` at
`d9e6aa47281bffecfc13458b695945bda5181360`

Prior milestone:
`sec_xbrl_residual_review_thread_closeout_2070_2074_v1` and PR #2081
auth-binding review closeout.

## Status

Branch-local Tier-1 validate-only diagnostic/report/test reconciliation.

This pass updates the nonlocal production-readiness gate so current repo
evidence no longer reports the in-app auth fork as absent after the policy
validation, auth-binding table, route-enforcement, residual closeout, and PR
#2081 review-debt fixes have landed.

It does not claim production readiness. It keeps the readiness report blocked
until a separate final nonlocal production admission or historical backfill
disposition is supplied.

## Claim Ledger

Repo-confirmed:

- `diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json`
  emits `decision: sec_xbrl_in_app_auth_policy_validation_passed` with no
  blocking reasons.
- `diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy-report.json`
  selects `separate_hash_only_auth_binding_receipt_table` with no blocking
  reasons.
- `backend/app/services/layer3_sec_xbrl_in_app_auth_policy.py` owns the
  protected SEC XBRL route-family map, hash-only actor/workspace projection,
  role allowlist, forbidden request fields, and legacy policy-hash candidate.
- `backend/app/services/layer3_sec_xbrl_auth_binding.py` records and requires
  source/route/actor/workspace/role-scoped auth bindings, with explicit
  downstream/status route compatibility.
- `backend/app/api/layer3.py` wires the protected SEC XBRL operator-review and
  controlled value-reveal route families through auth-binding helpers.
- `1326-auth-owner-binding-route-enforcement.md` records that protected
  mutating routes now commit source receipts and auth-binding receipts in one
  route transaction, while historical unbound receipts remain a separate
  repair/backfill authority question.

Inference:

- In-app auth evidence is now current enough for the nonlocal readiness gate to
  record the repo-owned in-app auth fork as present, but it is not sufficient
  by itself to admit production readiness.
- The next safe blocker is not "in-app auth missing"; it is final nonlocal
  production admission or historical backfill disposition.

## Reconciled Gate Contract

The gate now records:

- `authority_packet_or_in_app_auth_fork_evidence_present`: passed when either
  an admissible external authority packet is supplied or the current repo-owned
  in-app auth evidence is present.
- `in_app_auth_fork_evidence_current`: passed when current reports, services,
  API wiring, route-enforcement docs, and focused tests all match the in-app
  auth fork.
- `final_nonlocal_production_admission_present`: still blocked unless an
  admissible final production-readiness authority is supplied.

The committed report is therefore expected to remain:

- `decision: nonlocal_production_readiness_blocked`;
- `blocking_reasons: [nonlocal_production_readiness_final_admission_missing]`;
- `production_readiness_claimed: false`;
- `nonlocal_runtime_boundary.in_app_auth_implementation_evidence_present:
  true`.

## Non-Goals

- no schema, `models.py`, Alembic migration, or durable persistence changes;
- no backend API/UI behavior changes;
- no runtime-default changes;
- no source acquisition, live SEC network access, or Arelle subprocess
  invocation;
- no raw runtime artifacts;
- no value reveal default-on, automatic value delivery, export/delivery, or
  provider dispatch;
- no redaction-posture change;
- no production-readiness claim;
- no historical receipt backfill or rewrite.

## Next Safe Action

After this reconciliation merges, the next admissible lane is
`sec_xbrl_nonlocal_production_admission_or_historical_backfill_disposition_v1`:
a validate-first authority/disposition pass that decides whether current
in-app auth evidence plus any historical unbound receipt inventory is
sufficient to proceed, or whether a separate backfill/repair design is required
before production-readiness admission can be considered.

That lane must remain separate from export/delivery, provider dispatch, source
acquisition, Arelle execution, value-reveal default-on, and production
enablement.

