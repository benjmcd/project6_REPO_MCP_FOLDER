# 1328 - SEC XBRL Nonlocal Admission And Backfill Disposition

Milestone: `sec_xbrl_nonlocal_production_admission_or_historical_backfill_disposition_v1`

Base authority: `project6-origin/main` at
`27088eea9bb186066f569631af999f49dc6d01c7`

Prior milestone:
`sec_xbrl_nonlocal_readiness_in_app_auth_reconciliation_v1`

## Status

Branch-local Tier-1 validate-only diagnostic/report/test gate.

This pass does not implement production readiness. It adds a validation gate
for the two authority gaps left after current in-app auth evidence was
reconciled:

- final nonlocal admission authority; and
- historical unbound SEC XBRL receipt inventory/backfill disposition.

The committed report is intentionally blocked because no operator-provided
redacted final-admission packet or historical backfill disposition is present
in repo authority.

## Claim Ledger

Repo-confirmed:

- `sec-xbrl-nonlocal-production-readiness-gate-report.json` now records
  current in-app auth evidence as admissible.
- The same report remains blocked on
  `nonlocal_production_readiness_final_admission_missing`.
- `1326-auth-owner-binding-route-enforcement.md` records that current
  protected mutating routes commit source receipts and auth-binding receipts in
  one route transaction.
- `backend/tests/test_sec_xbrl_operator_review_workflow.py` includes focused
  rollback proof for decision submit, value-reveal authority prepare, and
  controlled value-reveal submit when auth-binding creation fails.
- Historical unbound receipts, if any exist in a runtime database, remain a
  separate repair/backfill authority question.

Inference:

- The repo can validate redacted final-admission and backfill-disposition
  packets, but it cannot manufacture them.
- Until both authority packets are supplied and validated, the next state must
  remain blocked and validate-only.

## Gate Contract

The new diagnostic is:

`diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py`.

It reads current repo evidence and optionally accepts:

- `--admission-packet <json>`;
- `--backfill-disposition <json>`.

The committed no-packet report must emit:

- `decision: nonlocal_production_admission_disposition_blocked`;
- `blocking_reasons: [sec_xbrl_nonlocal_admission_packet_missing,
  sec_xbrl_nonlocal_backfill_disposition_packet_missing]`;
- `production_readiness_claimed: false`;
- `next_slice:
  sec_xbrl_nonlocal_final_admission_packet_and_backfill_disposition_v1`.

Passing temp packets prove only that the authority artifacts are admissible for
operator review. They still do not enable production runtime behavior.

## Packet Boundaries

Both packets must be redacted and server/operator-owned. They may contain stable
refs, hashes, counts, modes, policy ids, and verification refs. They must not
contain raw operator identity, issuer identity, accessions, CIKs, SEC URLs,
local paths, period dates, raw values, raw payloads, residual magnitudes, local
evidence filenames, or free-text deployment notes.

The backfill disposition must explicitly state whether historical unbound
receipts are absent, fail-closed pending backfill, or backfill-authorized. A
nonzero unbound count without a matching backfill-required disposition is
invalid.

## Non-Goals

- no schema, `models.py`, Alembic migration, or durable persistence changes;
- no backend API/UI behavior changes;
- no runtime-default changes;
- no source acquisition, live SEC network access, or Arelle subprocess
  invocation;
- no raw runtime artifacts;
- no value reveal default-on or automatic value delivery;
- no export/delivery or provider dispatch;
- no historical receipt rewrite or backfill;
- no redaction-posture change;
- no production-readiness claim.

## Next Safe Action

The next admissible pass is
`sec_xbrl_nonlocal_final_admission_packet_and_backfill_disposition_v1`: supply
or create a redacted final-admission packet and historical backfill disposition,
run the diagnostic against those packet paths, and stop if either packet is
missing, raw, inconsistent, or ambiguous.

Only after that gate is clean should the lane consider a separate operator
review for production-readiness admission. Production enablement remains a
separate later lane.

