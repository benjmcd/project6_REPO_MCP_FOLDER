# 03 — Forward Plan

Every open pursuit: status, precise residual delta, acceptance criteria (pass), fail
criteria, SHOULD-NOTs, gates, size/risk, sequencing. Criteria derive from the M-FWD3-CRITERIA
report (inbox ~3247) as verified/adjudicated, grounded in repo authorities (merge-gate
policy, admission runbook, A8 docs, support matrix). Nothing here is authorized by this
document — it specifies what authorization would require.

## Sequencing map (dependencies, not conventions)

- P2 offline variant: unblocked now. P2 live variant: owner authorization only.
- P4: unblocked now (independent).
- P5: depends on the human final-admission packet + P7b-settled semantics (settled: I10) +
  durable posture (done) + record truth (done). Corpus breadth (P2) strengthens but does not
  formally gate it.
- P6: owner authorization only.
- Horizon items sequence AFTER their prerequisites, never bundled.

## P2 — Corpus / multi-filing broadening

- Status: machinery exists end-to-end (`layer3_sec_edgar_real_company_corpus_validation.py`,
  routes in `source_sec_edgar.py`); gated by BOTH
  `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED` (default true) AND
  `LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED` (default false). Current real-data
  evidence = one filing (STLD 10-Q); breadth is the main confidence gap before any
  production conversation.
- Residual delta: a bounded first corpus run — offline variant over already-retained /
  inherited evidence first; live acquisition matrix second if authorized.
- Pass criteria: corpus matrix predeclared before work (issuer/form scope); authority states
  offline-import vs new-live per filing; explicit operator confirmation for any egress;
  companyfacts oracle/quorum thresholds predeclared; per-filing receipts + ownership marker;
  redaction guard blocks raw CIK/accession/URL/value/path in committed text; sanitized
  report (counts/hashes/blockers per filing) is the only committed artifact; corpus flag
  armed per-run only.
- Fail criteria: any egress without owner authorization; CI or automatic egress; raw
  evidence committed; corpus results represented as production coverage; inherited evidence
  represented as a current run.
- SHOULD-NOT: combine with P3-class storage changes, P5 admission, or legacy reveal in one
  lane; treat a focused matrix as broad product coverage.
- Gates: OWNER — live matrix + egress authorization. Agent-executable: offline/report-only
  variant now.
- Size/risk: medium offline / large live. Tier-1 if validate-only diagnostics; Tier-2 if
  runtime/persistence behavior changes.
- Why this next (if product confidence is the goal): it is the only remaining item that
  changes evidence BREADTH; everything else changes posture or record.

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
