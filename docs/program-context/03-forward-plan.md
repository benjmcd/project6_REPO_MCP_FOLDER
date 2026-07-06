# 03 — Forward Plan

Every open pursuit: status, precise residual delta, acceptance criteria (pass), fail
criteria, SHOULD-NOTs, gates, size/risk, sequencing. Criteria derive from the M-FWD3-CRITERIA
report as verified/adjudicated, grounded in repo authorities (merge-gate
policy, admission runbook, A8 docs, support matrix). Nothing here is authorized by this
document — it specifies what authorization would require.

## Sequencing map (dependencies, not conventions)

- P2 domestic SEC inline corpus scope: EXECUTED by the owner-authorized
  2026-07-05 corpus-go run. Foreign IFRS annuals remain a named
  `ifrs-taxonomy-pins` follow-up.
- P4: unblocked now (independent).
- P5: depends on the human final-admission packet + P7b-settled semantics (settled: I10) +
  durable posture (done) + record truth (done). Corpus breadth (P2) strengthens but does not
  formally gate it.
- P6: owner authorization only.
- Horizon items sequence AFTER their prerequisites, never bundled.

## P2 - Corpus / multi-filing broadening

- Status: EXECUTED for the domestic SEC inline scope. The owner-authorized
  2026-07-05 corpus-go run used the 30-ticker owner matrix plus TSM
  supplemental, isolated each ticker, tried explicit 10-K/10-Q first, and used
  discovery fallback second. Results: 39 supported filings / 21 supported
  issuers, exceeding the 30/15 run-plan minimums. All run-level gates passed:
  every-ticker-dispositioned, zero-unnamed-failures, min-filings, and
  min-issuers. Aggregate report SHA-256:
  `113ce73679547f5d202cb273ebca9d2373f90fab9ae688e9159cc7894c3cee10` at
  durable-root relative `corpus_run/CORPUS_GO_RUN_REPORT.json`.
- Supported domestic scope: all major domestic 10-K+10-Q pairs, plus CURLF and
  CRLBF 40-F through US-GAAP inline handling.
- Named residuals: foreign IFRS annuals for `SONY`, `CCJ`, `DNN`, `NXE`, `MT`,
  and `TSM` were acquired and retained but blocked with admitted reason
  code `taxonomy_year_unprovisioned` after the operator symptom
  `arelle_model_errors_present`; `6-K` filings blocked on
  `no_inline_facts_pre_inline_era`; `KAP`, `PDN`, and `YCA` map to
  `official_ticker_resolution_missing`; and `TSMC-as-written` maps to
  `ticker_alias_resolution_required`.
- Residual delta: `ifrs-taxonomy-pins` only, scoped to the blocked foreign IFRS
  annuals. Acceptance criteria: pinned `ifrs-YYYY` packages fetched and hashed
  by operator action; year-aware admission extended to the IFRS taxonomy family;
  the previously blocked foreign annuals rerun to supported-or-named-block.
- Pass criteria for future IFRS follow-up: no raw values/paths/user-agent or
  operator identity in committed text; public tickers/forms/dates only where
  needed for named disposition; hash/count/disposition-only aggregate report;
  explicit named block for any still-unsupported annual; corpus flag armed
  per-run only.
- Fail criteria: any egress without owner authorization; CI or automatic egress; raw
  evidence committed; corpus results represented as production coverage; inherited evidence
  represented as a current run.
- SHOULD-NOT: combine with P3-class storage changes, P5 admission, or legacy reveal in one
  lane; treat the executed domestic scope as production coverage or as IFRS readiness.
- Gates: OWNER for any additional live acquisition. Agent-executable:
  report-only/record-only lanes over already authorized retained evidence.
- Future SEC corpus runs use the canonical pre-registered run gate registry in
  `next_milestone_plans/Layer3_planning_docs/corpus-run-gate-spec.md`.
- Size/risk: small-medium for IFRS taxonomy pins if report-only; Tier-2 only if
  runtime/persistence behavior changes.
- Why this changed state: the domestic breadth confidence gap is closed for the
  SEC inline scope; the remaining breadth question is narrower and taxonomy-family-specific.

## P4 — Legacy Arelle reveal disposition

- Status: default-off governed sibling; surfaces enumerated (service, source_sec_edgar
  routes, posture labels, compatibility detector, tests).
- Residual delta: one-word owner disposition ("keep as labeled sibling" suffices), then a
  Tier-1 label lane: posture docs/API status name it legacy/superseded-by-controlled-submit;
  tests keep proving flag-off blocks + forbidden-field rejection.
- Pass criteria: no behavior change; labels consistent across posture surfaces; fail-closed
  tests retained; controlled-submit named as the A8 surface everywhere.
- Fail criteria: any activation; removing routes without archive/compat plan; representing
  legacy receipts as controlled-submit authority.
- Gates: owner one-liner. Size: small. Why bother: every future audit re-spends tokens
  re-establishing that this surface is intentionally dormant.

## P5 — Nonlocal / production admission

- Status: 6 of 7 nonlocal production-readiness gate criteria already pass on committed
  evidence; the SOLE blocker is
  `final_nonlocal_production_admission_present` — a human/operator-supplied packet, not
  code. Evaluator flag default-off. I10 settled: reveal proofs are never admission evidence;
  admission evidence runs must have `value_reveal_performed=false`.
- Residual delta: owner decides production is wanted → operator supplies final-admission +
  backfill-disposition packets (schema-valid, redacted) → nonlocal deployment evidence
  (proxy owner, auth boundary, storage exposure, rollback, incident owner — refs not raw
  details) → evaluator enabled for the evaluation → all 7 criteria pass with
  review_exception_count=0.
- Pass criteria: per `docs/layer3-admission-runbook.md` seven criteria verbatim; packets
  operator-authored; value-reveal flags unarmed in the nonlocal runtime (config-enforced
  conjunction ban); no honesty/containment invariant violations.
- Fail criteria: treating the 523/497 reveal proof as admission evidence; flag-flip-only
  "admission"; missing packet fields; raw deployment details in packets.
- SHOULD-NOT: be bundled with egress, corpus, exports, or legacy-reveal work; be attempted
  before the owner actually wants production.
- Gates: OWNER (the packet is definitionally theirs). Size: large. Risk: high —
  production-readiness false positives are the worst failure class this repo defines.
- Why deferred without embarrassment: default-off IS the correct posture until the owner
  wants production; nothing decays while it waits.

## P6 — Worktree/branch cleanup

- Status: 347 worktrees inventoried (hash-anchored inventory in M-FWD3-EVIDENCE §4e):
  11 mechanically-safe candidates (merged/stale), 1 active-parallel, 334 requiring
  owner/session-specific review; standing no-remove rail (I11).
- Residual delta: owner per-class authorization → removal of safe candidates (worktree
  remove preserves branches/commits), then staged review of the 334.
- Pass criteria: fresh inventory at execution time; no active/dirty/preserved lane removed;
  branch deletion only if separately authorized; archive-not-delete for any file content.
- Fail criteria: removing anything with uncommitted work; cleanup bundled into a product
  lane.
- Gates: owner go, per class. Size: small-medium operational. Why it matters now: 347 is
  operationally significant (collision surface, disk, audit noise).

## P7 — Standing small items

- P7a Sanitized proof-import schema: a stable hash/count/policy-only schema for recording
  future operator proofs, so record-truth lanes stop hand-crafting redaction. Tier-1,
  agent-executable, small. Pass: schema doc + conformance test; forbidden-field list
  explicit.
- P7c Support-matrix posture audit cadence: periodic Tier-1 check that no doc/manifest
  implies production support while the selected profile is local/offline. Small.
- Program-context maintenance: this set updates on every tranche per INDEX protocol.

## Horizon (sequenced, not scheduled)

Live SEC re-acquisition (only when retained artifacts are insufficient) → corpus breadth
(P2) → delivery/export surfaces → multi-filing gate enforcement → nonlocal auth hardening →
admission (P5) → default-on consideration (a separate owner decision with its own criteria;
nothing in this program authorizes it). Unsupported feature tracks (HA, keyed connectors,
model egress, real provider delivery, signed-reference export) are separate
architecture/security programs per the support matrix — none is an A8 follow-on slice.

## What is deliberately NOT planned

- No erasure/disposition machinery for SEC values (I1 — permanent).
- No default-on flips of any raw-bearing flag by any agent lane, ever (owner-local arming
  only, I3).
- No second master-context document (D10 — this set + MASTER_CONTEXT with authority order).
- No new SEC egress while retained artifacts satisfy the evidentiary need (D7).
