# 03 — Forward Plan

Every open pursuit: status, precise residual delta, acceptance criteria (pass), fail
criteria, SHOULD-NOTs, gates, size/risk, sequencing. Criteria derive from the M-FWD3-CRITERIA
report as verified/adjudicated, grounded in repo authorities (merge-gate
policy, admission runbook, A8 docs, support matrix). Nothing here is authorized by this
document — it specifies what authorization would require.

## 2026-07-06 Forward Program Refresh (M-WORKTREE-CLEANUP-EXEC)

Supersession boundary: this block is the current F6 pointer after the
owner-authorized local worktree cleanup execution. It supersedes only the
operational worktree-count/disk-pressure state for P6/F6. It does not authorize
mass remote branch deletion, deletion of protected local work, or cleanup of
worktrees that still carry modified tracked files or non-adjudicated ignored
content.

### F6 - Worktree cleanup: EXECUTED FOR ADJUDICATED LOCAL CLASS

- Status: EXECUTED for the mechanically-safe and Phase-2-adjudicated local
  worktree classes. Phase 1 correctly stopped on the ignored-content threshold
  after surfacing the pattern. Phase 2 then re-ran all remaining repo-local
  candidates with refined safe matching, protected `.claude/`, used
  `--ignore-submodules=none`, and allowed `git worktree remove --force` only
  when all status entries were safe untracked paths, all ignored entries were
  safe, and the immediate pre-removal rescan matched.
- Counts: the cleanup began from 353 registered worktrees, including 331
  repo-local registrations and 329 Phase-1 candidates. Phase 1 removed 14 and
  stopped with 125 recorded skips plus 190 unevaluated candidates. Phase 2
  re-evaluated 315 repo-local candidates, removed 176, and left 139 protected.
  The final registry after prune is 163 total registrations: 141 repo-local,
  21 external, and the root checkout.
- Force-gated removals: 164 of the Phase-2 removals used `--force`; each is
  recorded in `state/agent-inbox/worktree-cleanup-exec-manifest.json` with
  the full pre-removal status lines, ignored scan, and force justification.
  There were zero unjustified force removals and zero branch deletions.
- Disk impact: `worktrees/` moved from 246,075,642,767 bytes at the Phase-1
  baseline to 160,990,819,317 bytes after Phase 2 and prune, reclaiming
  85,084,823,450 bytes cumulatively. Phase 2 alone reclaimed 83,172,282,072
  bytes.
- Remaining local worktree state: 76 repo-local worktrees remain protected for
  non-safe ignored content under the refined matcher, and 63 remain protected
  for tracked or unsafe untracked dirty status. These are an owner/session
  review list, not mechanically-safe cleanup candidates.
  The 63 dirty-status worktrees in particular may carry unlanded or in-flight
  work and must be reviewed per item before any removal; per-entry SKIPPED-DIRTY
  evidence is in `state/agent-inbox/worktree-cleanup-exec-manifest.json`.
- Remote branches: the remote `codex/*` census remains report-only at 1,726
  heads. The eight sampled leftovers (`codex/a8-runtime`,
  `codex/ops-ready-b1`, `codex/ops-ready-b2-fix`, `codex/ops-ready-b3`,
  `codex/ops-ready-b5`, `codex/p3-durable-root-repo`,
  `codex/program-context`, and `codex/record-truth-3`) each map to merged PRs.
  Mass remote branch deletion remains a separate owner-gated decision.
- Anomaly: `/tmp/audit-wt/p6main` remains an external locked registration
  (`locked initializing`) and is outside this local repo-worktree cleanup class.
  It is also a placement violation, a registration outside the owning repo's
  `worktrees/` folder, and remains locked; resolving it requires an owner
  unlock/decision.

## 2026-07-06 Forward Program Refresh (M-CORPUS-46-RECORD)

Supersession boundary: this block is the current pointer after the retained
foreign IFRS annual replay closeout. The M-PROGRAM-CONTEXT-4 refresh and older
P-number sections remain historical and still govern where not superseded here.
This refresh admits no production-readiness, default-on, new live SEC EDGAR
egress, value reveal, raw-value disclosure, nonlocal admission, or broader
taxonomy-host authority.

### F1 - M-COVERAGE-XDIST: DONE (#2438)

- Status: DONE. No change from the M-PROGRAM-CONTEXT-4 pointer.

### F2 - Program-context payload landings: DONE (#2439, #2441)

- Status: DONE. PR #2439 landed D20-D26. PR #2441 landed D27 and the F3a/F3b
  split after PR #2440 and PR #2442.

### F3a - cyd-2025 provisioning prep: EXECUTED (#2440)

- Status: EXECUTED. No remaining CYD prep delta for the retained foreign
  annual replay set.

### F3b - IFRS package prep and retained annual replay: EXECUTED (#2442, M-CORPUS-46-RECORD)

- Status: EXECUTED. PR #2442 pinned/admitted retained `IFRSAT-2025.zip` with
  sha256 `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19`
  at 2,103,003 bytes. The owner-named IFRS grant then executed within a 5/5
  request ledger recorded by PINNING hash
  `20dfec68cccba35eb9969763ec056ac568824dd0df5f5b9c43151ac854945c07`.
- Replay closeout: six retained IFRS annuals replayed at zero SEC EDGAR egress
  using fresh client_request_ids `ifrs-replay-01-r1` through
  `ifrs-replay-06-r1`. All 6/6 reached `READY`, stores persisted, named blocks
  were zero, and resolved/value record counts were 4693 / 886 / 1582 / 7335 /
  2670 / 3565, totaling 20,731.
- Record anchors: `IFRS_REPLAY_RESULTS.json` hashes to
  `7d691b6ac96fe31e40797b9e1ef582274e4792fb331c0071f821250c9189bbc7`;
  evidence bundle hash
  `a49b9c5553fd21788307b2dae9407b36582a97b467780aeeceda7772c44c40ff`;
  independent regrade hash
  `6e755725e65c11fb7fd1ddc926911804aebf924b79da9fc553f56a88b2bce2e3`
  with verdict `PASS_WITH_ATTESTED_FIELDS`; r3 provisioning hash
  `6ff72308060a5769ff708b556bc3e9a6269ac867b1f06eaa6d0291f4a8a9708c`
  reports `ready=true`, 13/13 packages loaded, 26/26 SEC entrypoints intact,
  and IFRS 2025 offline entrypoints loaded.
- Corpus state: current supported count is 46 filings. The historical
  39-filing and 40-filing records remain true in time and are not rewritten;
  this block supersedes only the current P2/F3 residual that retained
  foreign-annual replay/result recording remained open.
- Remaining resolvable F3 delta: none. `6-K` no-inline dispositions remain by
  design, and `KAP`, `PDN`, `YCA`, and `TSMC-as-written` remain non-SEC or
  alias-resolution dispositions rather than taxonomy replay blocks.

### F4 - Coverage Option B (optional)

- Status: OPTIONAL. No change from the M-PROGRAM-CONTEXT-4 pointer.

### F5 - Release-gate needs gap and orphaned workflow registration

- Status: OWNER DECISION. No change from the M-PROGRAM-CONTEXT-4 pointer.

### F6 - Worktree cleanup

- Status: OWNER GO REQUIRED for broad cleanup. This lane's own worktree cleanup
  remains ordinary lane closeout only.

### F7 - Owner-keyed decisions remain parked

- P4 legacy Arelle reveal disposition remains a one-line owner posture choice.
- P5 nonlocal production admission remains blocked solely on the human final
  admission packet. Corpus breadth and replay proofs are not nonlocal
  production admission evidence.

### F8 - Standing rails

- D27/D28 still govern future egress: established host classes and named
  grants do not become blanket authority for future first-use host classes,
  new live taxonomy vintages, or broader request budgets.

## 2026-07-06 Forward Program Refresh (M-PROGRAM-CONTEXT-4)

Supersession boundary: this block is the current pointer after #2442. The
M-PROGRAM-CONTEXT-3 refresh and older P-number sections remain historical and
still govern where not superseded here. This refresh admits no
production-readiness, default-on, new live-egress, foreign-annual replay/result,
or value-reveal claim.

### F1 - M-COVERAGE-XDIST: DONE (#2438)

- Status: DONE. PR #2438 remains the current coverage Option A record:
  `backend-coverage` uses pytest-xdist while preserving job id, target globs,
  coverage targets, and `--cov-fail-under=90`.
- Current relevance: no further action unless optional F4 becomes material.

### F2 - Program-context payload 3 landing: DONE (#2439)

- Status: DONE. PR #2439 merged to `project6-origin/main` at
  `2edcd37dbb52478a20147e842d43d900fc9e6ed3`.
- Current relevance: future operators should not treat the D20-D26 landing
  lane as open; it is historical authority for D27 and the F3a/F3b split.

### F3a - cyd-2025 provisioning prep: EXECUTED (#2440)

- Status: EXECUTED. PR #2440 merged to `project6-origin/main` at
  `6d962b248ffdaaf35adc8467dbaad171fb873537` on 2026-07-06.
- Scope landed: `sec-cyd-2025` is pinned as an operator-built deterministic
  archive from the SEC loose-file base URL; `cyd/2025` flat extraction and SEC
  entrypoint verification are covered; the sidecar admits provisioned
  `cyd-2025.zip` through the provisioner package set.
- Operator evidence re-verified by this lane: `CYD2025_FETCH_ARMING.json`
  was written before first request, armed only `xbrl.sec.gov`, budgeted 10
  requests, and explicitly did not authorize `xbrl.ifrs.org`; `cyd-2025.zip`
  hashes to
  `ad7b166a3913778a4fabb15f3a4431d80eb1930d9cc1e271c318f7b4cffdfc33`
  at 208,667 bytes; the PINNING note hashes to
  `9cb98156f2780efd44e8a9954881331e96b00b6b86c726b77bf9e0211bec2e8e`;
  all 7 zip members match the PINNING hashes and deterministic metadata.
- Post-#2440 provisioning evidence: `provision_report_2021_2026_r2.json`
  hashes to
  `7d5f719c274b2c64275498b52832913d6ad0914847bc4abde54e2842063527ee`;
  structured read reports `ready=true`, 12/12 packages loaded, 26/26 offline
  entrypoints OK, and both `cyd/2024` and `cyd/2025` entrypoints loaded.
- Remaining delta for CYD: none for the SEC `cyd-2025` pin/admission prep
  surface.

### F3b - IFRS 2025 package prep: EXECUTED (#2442)

- Status: EXECUTED for package pin/admission prep. PR #2442 merged to
  `project6-origin/main` at `e7e9e8675fa6bbe8ec75172162c0cebba3bdfc2a` on
  2026-07-06.
- Scope landed: retained local `IFRSAT-2025.zip` is pinned as the IFRS 2025
  taxonomy package with sha256
  `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19`
  at 2,103,003 bytes; the provisioner package set and sidecar admission now
  cover the IFRS 2025 package.
- Remaining F3 delta: replay the retained foreign annuals at zero SEC EDGAR
  egress and record supported-equivalent or exact named-block outcomes.
- D27 boundary still applies: a future first-use host class, new live taxonomy
  vintage, or broader request budget still requires a named owner grant before
  the first request. #2442 does not make generic directives blanket egress
  authority.

### F4 - Coverage Option B (optional)

- Status: OPTIONAL. Only proceed if #2438's residual still materially slows the
  release gate.
- Guardrail: this remains a coverage-enforcement semantics change, not merely
  a speed patch; exact line-set union proof and fail-closed floor-trip evidence
  are required before any release-gate change.

### F5 - Release-gate needs gap and orphaned workflow registration

- Status: OWNER DECISION. The release-gate dependency and orphaned workflow
  registration questions remain unchanged by #2440.

### F6 - Worktree cleanup

- Status: OWNER GO REQUIRED for broad cleanup. This lane's own worktree cleanup
  is ordinary lane closeout only; it does not authorize deleting or removing
  unrelated worktrees.

### F7 - Owner-keyed decisions remain parked

- P4 legacy Arelle reveal disposition remains a one-line owner posture choice.
- P5 nonlocal production admission remains blocked solely on the human final
  admission packet. Reveal proofs and taxonomy pinning are not admission
  evidence.

### F8 - Standing rails

- Enumerate before fetch; source-default raw/reveal/network flags stay false by
  default; no live egress outside an established host class without named owner
  grant; current-pointer fields get supersession pointers; heavy local
  Python/Arelle work serializes by machine; docs updates append and supersede
  instead of rewriting history.

## 2026-07-06 Forward Program Refresh (M-PROGRAM-CONTEXT-3)

Supersession boundary: this block is the current pointer for the open program
after #2438. The older P-number sections remain historical and still govern
where not superseded here. This refresh admits no production-readiness,
default-on, live-egress, or value-reveal claim.

### F1 - M-COVERAGE-XDIST: DONE (#2438)

- Status: DONE. PR #2438 merged to `project6-origin/main` at
  `be8efadbc810ee78867ab6de4ba3ed6a11082c4e` on 2026-07-06.
- Scope landed: `backend-coverage` now runs the existing Layer 3 coverage pytest
  invocation with pytest-xdist; the job id, target globs, coverage targets, and
  `--cov-fail-under=90` threshold stayed intact.
- Acceptance evidence re-verified: PR body records exact covered-line-set
  parity, 2659/2659 collect parity, floor-trip exit 1 at 88.86% with one final
  threshold failure, and 10/10 capped local soak runs. Post-merge main Actions
  run `28776807974` completed green; `backend-coverage` ran from 08:01:32 to
  08:09:46 UTC (494 seconds / 8m14s).
- Scope note: this is a CI-operations/program-context completion record, not a
  Layer 3 progress-manifest tranche. It changes no Layer 3 runtime, proof
  manifest, progress-board entry, or workbench proof claim; those surfaces are
  intentionally unchanged by PR #2439.
- Remaining delta: none for Option A. Optional F4 below is the only path to
  further coverage-wall reduction if the residual still matters.

### F2 - Program-context payload 3 landing

- Status: LANDING AS PR #2439; complete once that PR is merged. Scope is
  docs-only: append D20-D26, refresh this forward pointer, extend the evidence
  registry, refresh `docs/MASTER_CONTEXT.md`, and append a narrow arc-ledger
  tranche for already merged work. After PR #2439 merges, future operators
  should not treat F2 as an open lane.
- Acceptance: re-verify every anchor before admission; preserve
  operator-attested wording for bundle-only fields; keep machine-local artifacts
  hash-only; run `l3-progress-check`, link check, `git diff --check`, CI, review
  thread re-query, merge, detached post-merge proof, and inbox report.

### F3 - IFRS + cyd-2025 provisioning and foreign-annual replays

- Status: OWNER SIGN-OFF REQUIRED. No agent lane may fetch taxonomy artifacts
  without a bounded grant.
- Scope, in order: enumerate retained artifacts (already hash-recorded);
  operator fetches exactly IFRS 2025-03-27 plus the enumerated `cyd-2025` loose
  files under grant; operator records per-file provenance and builds a
  deterministic `cyd-2025` zip; a repo lane pins/adopts the packages without
  network access; operator reruns the six retained IFRS annuals with zero SEC
  EDGAR egress; a record lane publishes supported-equivalent or named-block
  results.
- Acceptance: pinned package hashes and provenance are re-derivable; admission
  is year/family aware; each of the six annuals resolves to supported-equivalent
  or a specific named block; committed surfaces contain no raw values, no
  accession/CIK, no operator identity, and no local path beyond the
  `C:/p6store` root convention.
- Why next substantive frontier: the domestic SEC inline corpus is closed at
  40 supported filings / 21 issuers; the remaining corpus work is now a
  bounded foreign-taxonomy family problem.

### F4 - Coverage Option B (optional)

- Status: OPTIONAL. Only proceed if #2438's residual still materially slows the
  release gate.
- Scope: emit coverage from the existing shards, combine it once, enforce the
  floor on combined data, and retire the duplicate standalone coverage run.
- Acceptance: exact line-set union equivalence versus monolithic coverage on
  the same SHA; proof that all shard data files were consumed; combined
  floor-trip failure; release-gate fail-closed proof; meta-guard updated.
- Risk: this is a coverage-enforcement semantics change, not just a speed patch.
  Missing or aliased shard data could silently pass if the proof is weaker than
  the risk.

### F5 - Release-gate needs gap and orphaned workflow registration

- Status: OWNER DECISION. Current `release-gate` depends on
  `release-lock-install`, `backend-layer3-api`, `backend-coverage`,
  `backend-migrations-postgres`, and `sec-xbrl-arelle-provisioning`. It does
  not depend on `root-tests`, `nrc-aps-ocr`, or the Playwright `test`
  aggregator.
- Recommendation to owner: decide whether `root-tests`, `nrc-aps-ocr`, and/or
  the Playwright aggregator should become release-gate blockers. Also clean up
  the active GitHub workflow registration named `SEC XBRL Tier-2 review gate`,
  whose `.github/workflows/sec-xbrl-tier2-gate.yml` file is absent on current
  main.
- Why owner-level: changing release-gate dependencies changes merge semantics
  for every future PR.

### F6 - Worktree cleanup

- Status: OWNER GO REQUIRED. Deletion-class operation.
- Drift evidence: `worktree-cleanup-manifest.json` hashes to
  `9b98fab6ade7ff21fa95e1c66855378f4d5f0ee2365586716e7d0621a8a5c943`, but it
  was computed as of main `873d8883` and is stale. During this landing audit,
  a fresh count found 352 registered worktrees including the active
  `prog-ctx-3` lane; use that only as evidence that counts drift quickly.
- Acceptance: fresh recompute; per-entry clean/merged/not-active verification;
  `git worktree remove` only; no branch deletion unless separately authorized;
  no file deletion beyond explicit owner-approved worktree removal.

### F7 - Owner-keyed decisions remain parked

- P4 legacy Arelle reveal disposition remains a one-line owner posture choice.
- P5 nonlocal production admission remains blocked solely on the human final
  admission packet. Reveal proofs are not admission evidence.
- No useful preparatory lane exists before the owner decisions.

### F8 - Standing rails

- Enumerate before fetch; source-default raw/reveal/network flags stay false by
  default; no live egress without owner grant; current-pointer fields get
  supersession pointers; heavy local Python/Arelle work serializes by machine;
  docs updates append and supersede instead of rewriting history.

## Sequencing map (dependencies, not conventions)

- P2 corpus scope: EXECUTED by the owner-authorized 2026-07-05 corpus-go run
  and supersession addenda. After #2440/#2442 package prep and
  M-CORPUS-46-RECORD replay closeout, the retained foreign IFRS annual replay
  follow-up is closed at 46 supported filings.
- P4: unblocked now (independent).
- P5: depends on the human final-admission packet + P7b-settled semantics (settled: I10) +
  durable posture (done) + record truth (done). Corpus breadth (P2) strengthens but does not
  formally gate it.
- P6: owner authorization only.
- Horizon items sequence AFTER their prerequisites, never bundled.

## P2 - Corpus / multi-filing broadening

- Status: EXECUTED for the current retained corpus scope through
  M-CORPUS-46-RECORD. The owner-authorized corpus-go run remains historical at
  39 supported filings; the MSFT/CYD supersession addendum records 40 supported
  filings / 21 supported issuers after MSFT FY2025 10-K moved from named block
  to supported-equivalent via governed receipt-bound replay; and
  M-CORPUS-46-RECORD records the retained IFRS annual replay closeout at 46
  supported filings. All original run-level gates passed:
  every-ticker-dispositioned, zero-unnamed-failures, min-filings, and
  min-issuers. The corpus-40 and corpus-46 addenda both use the
  `PASS_WITH_ATTESTED_FIELDS` regrade boundary rather than unqualified claims.
- Supported scope: 46 supported filings / 27 supported issuers. The issuer
  count is derived from the prior 21 supported issuers plus the six named
  distinct retained IFRS issuers. This includes 19 full domestic 10-K/10-Q
  pairs, CURLF/CRLBF 40-F through US-GAAP inline handling, and six retained
  IFRS annuals now replayed to `READY` with persisted stores.
- Named residuals: zero remaining resolvable taxonomy replay blocks for the
  retained annual set. `6-K` filings remain `no_inline_facts_pre_inline_era`;
  `KAP`, `PDN`, and `YCA` map to `official_ticker_resolution_missing`; and
  `TSMC-as-written` maps to `ticker_alias_resolution_required`.
- Residual delta: none for retained foreign-annual replay/result recording.
  Future live acquisition, new vintages, or broader host classes require a new
  owner grant and a separate record.
- Pass criteria for any future corpus addendum: no raw values/paths/user-agent
  or operator identity in committed text; public tickers/forms/dates only where
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
- Size/risk: small-medium for future report-only corpus addenda; Tier-2 only if
  runtime/persistence behavior changes.
- Why this changed state: the domestic breadth confidence gap was already
  closed for the SEC inline scope, and the retained IFRS annual taxonomy-family
  follow-up is now closed by zero-egress replay evidence. Remaining gaps are
  not resolvable by replaying retained annuals.

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
- Superseded current-state pointer: see the 2026-07-06
  M-WORKTREE-CLEANUP-EXEC refresh above for the executed local worktree cleanup
  record, remaining owner-review local worktrees, and report-only remote branch
  posture.
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
