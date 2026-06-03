# 1335 SEC XBRL offline evidence proof-of-capability

Target: `sec_xbrl_offline_evidence_proof_capability_v1`.

This slice adds a validate-only proof report for operator-supplied SEC XBRL
offline evidence. It proves, in isolated in-memory persistence, that already
governed evidence can pass the offline loader, CompanyFacts oracle packet, and
offline orchestrator path into a redacted operator-review workflow.

## Scope

- Add a proof service that composes the existing offline evidence loader,
  CompanyFacts oracle packet, and offline orchestrator.
- Add a CLI diagnostic that emits a redacted hash/count/state report.
- Add a committed default blocked report for the no-operator-evidence path.
- Add focused tests for fail-closed behavior, blocked loader propagation,
  ready-report shaping, report redaction, and default-report drift.

## Non-goals

- no source acquisition;
- no live SEC network access;
- no Arelle invocation;
- no production database persistence;
- no API or UI route;
- no value reveal;
- no default-on behavior change;
- no raw storage or CompanyFacts payload committed;
- no production-readiness claim.

## Design

The default committed diagnostic remains blocked when no operator storage is
supplied. A ready report requires:

- loader status `offline_evidence_bundle_ready`;
- oracle status `offline_companyfacts_oracle_packet_ready`;
- offline orchestrator status `review_ready`;
- isolated in-memory persistence of one redacted review workflow;
- exactly one isolated projection set, statement packet set, and operator-review
  workflow, plus positive projection fact and statement row counts;
- no raw accession, SEC URL, local path, or raw value key in the public report.
- fail-closed blocking if the redaction scan reports any public response leak or
  any persisted projection/statement row is not value-redacted.

The report is intentionally hash/count/state-only. It records authority hashes,
storage markers, counts, readiness flags, containment flags, and redaction scan
flags. It does not persist or replay raw values.

The orchestrator `source_report_hash` is derived from the proof schema, loader
status, oracle status, redacted storage marker, merged loader-plus-oracle
authority refs, loader/oracle count summaries, period limit, and proof artifact
policy. It is not just the CompanyFacts payload hash, because the proof binds
the whole operator-supplied evidence authority chain and the quantified proof
claim. The same hash is exposed as
`authority_refs.proof_source_report_hash` in ready and post-oracle blocked
reports so audits can connect the public proof report to the isolated
orchestrator lineage handle.

Ready proof reports require the isolated orchestrator response to bind the same
`source_report_hash`. If that binding is absent or mismatched, the proof blocks
with `offline_evidence_proof_source_hash_unbound` before any ready claim.

Ready proof reports also expose `authority_refs.proof_result_hash`. The source
hash binds the operator-supplied evidence input basis; the result hash binds the
isolated orchestrator status/count output, isolated persistence counts,
redaction scan flags, and the preserved non-production-admission posture.
Ready reports assert the two hashes are distinct so input lineage and output
lineage cannot collapse into a single ambiguous authority handle.
Focused tests require both lineage handles to be 64-character lowercase hex
hashes, not merely non-empty strings or opaque identifiers.
Blocked reports may expose `authority_refs.proof_source_report_hash` after
loader/oracle context exists, but must not expose `proof_result_hash`; a result
hash is ready-only because failed proofs have no admitted output result to bind.
The no-operator default blocked report and generic diagnostic-exception fallback
have no evidence context, so they expose neither source nor result proof hashes.

A ready proof remains a proof artifact, not raw evidence admission. The report
policy keeps `operator_supplied_evidence_required` true,
`default_reports_remain_blocked_without_operator_evidence` true,
`raw_storage_committed` false, `raw_companyfacts_committed` false, and
`production_admission_claimed` false.
The source/result proof hashes are redacted authority handles, not raw evidence
refs; the policy records this distinction explicitly.

Ready proof controls also remain non-production: offline storage is read-only,
source acquisition is false, Arelle is not invoked, network activity is false,
production database persistence is false, value reveal is false, API route
activation is false, and production readiness is not claimed.

Blocked reports preserve containment accounting explicitly: once an
operator-supplied storage path is processed, `operator_evidence_files_read`
remains true even if the loader, oracle, or redaction scan blocks before a
storage marker is reportable.

The committed default report must remain byte-equivalent in meaning to the
service's no-operator-storage output. A focused regression test compares the
committed JSON report to `inspect_sec_xbrl_offline_evidence_proof_capability()`
with no arguments so schema or default-control drift fails closed.

The CLI default path is also covered: running the diagnostic with no
operator-supplied storage must write the same blocked report as the service
no-argument path. Operator evidence is therefore opt-in rather than implied by
the committed diagnostic artifact.

If the proof inspection raises before a report can be emitted, the CLI fails
closed by writing a generic blocked report with only the exception type. It does
not reflect raw exception text, which may contain local paths or value-bearing
details. Because this fallback cannot prove where the exception occurred, it does
not claim that operator evidence files were read.

## Current evidence

A local FIZZ 10-K operator-supplied run on current main proved the path before
this slice was created:

- loader status: `offline_evidence_bundle_ready`;
- oracle status: `offline_companyfacts_oracle_packet_ready`;
- projected facts: 22;
- oracle-confirmed facts: 20;
- CompanyFacts observations: 15010;
- orchestrator status: `review_ready`;
- isolated persistence: one projection set, one statement packet set, one
  operator-review workflow, 22 redacted projection facts, and 22 redacted
  statement packet rows;
- no network, source acquisition, Arelle, API route, value reveal, or
  production-readiness claim.

## Historical S1 proof snapshots

PR #2109 added dated, operator-supplied S1 proof snapshots under
`diagnostics/assessment`:

- `sec-xbrl-s1-fizz-10k-proof.json`;
- `sec-xbrl-s1-fizz-10q-proof.json`;
- `sec-xbrl-s1-ccj-10k-proof.json`;
- `sec-xbrl-s1-fizz-10q-oracle.json`;
- `sec-xbrl-s1-real-evidence-proof-report.json`.

These artifacts are frozen, hash-bound, point-in-time proof records. They were
derived from governed operator evidence and are not repo-reproducible without
that external evidence. Do not edit the proof JSON files in place: changing their
bytes would break their historical hash binding. Instead, keep additive guard
tests that load the committed snapshots, validate them against the current
proof-capability invariants, and fail if schema, redaction, lineage-hash, or
non-production posture expectations drift.

## Known remaining work

- Run the diagnostic against the operator-supplied FIZZ 10-K evidence and decide
  whether to commit a redacted ready proof report.
- Repair or regenerate the FIZZ 10-Q and CCJ offline storage authority before a
  multi-filing proof. Current local FIZZ 10-Q and CCJ storage is blocked by
  missing top-level `fact_inventory_hash` or missing sidecar receipt authority.
- Design a transaction strategy before any production workflow activation. The
  existing materializers still commit per stage; this proof does not claim a
  single cross-stage transaction.
