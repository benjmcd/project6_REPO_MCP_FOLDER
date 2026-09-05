# 01 — Arc Ledger (chronological accomplishment record)

## 2026-09-04 current ledger extension

Current main is `d9412188e9581302429112cc637e416fe666994f`. The landed chain after
the July admission-spine checkpoint is #2477 `1b2e170b`, #2478 `fcf6070d`,
#2479 `f6b70030`, #2481 `c1fcd840`, #2482 `0b65b4f0`, #2486 `89b04fef`,
#2487 `2182177e`, #2489
`892a6b0a2fd8be4b3385c9304974e1e0a523cd40`, #2490
`d7488c05520405716eceab7093ec84d268870b68`, #2491 `f8f4ee9c`, #2492
`9d358139dcc05386a8b956691af478ccaa62038a`, #2493
`c979edad991bef3ecc1b310edeb8bd9964f40333`, and #2494 at the current-main
hash. Exact bounded outcomes and non-claims are summarized in
[MASTER_CONTEXT](../MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).

PR #2495 at `44c3a433d39c5c676c2e1d163ab19b8e0965f6bf` and PR #2496 at
`1de3b1e291a854ef69a3d46bfa1cfd31cc240349` are open, clean, and reported
with 21 successful checks each. Neither is landed. Their merges remain owner
decisions. This extension records no merge authority and does not declare the
whole B1b program, integrated-loop utility, or Phase 4/5/6 complete.

Each entry: what landed, evidence anchor, and why it was the right move at that point.
Dates 2026. All PRs merged to `project6-origin/main`; squash SHAs given.

## Phase 0 — Repo-state audit and course correction (07-01)

- Multi-agent audit of two session exports + live main established the true frontier:
  preclearance docs merged through #2408, repo-lane spec PR #2409 open. Why it mattered: prior
  session memory claimed states that had drifted; re-deriving from live main prevented
  building on stale anchors.
- Independent adversarial review (M-ADVERSARIAL-REVIEW-AUDIT) REFUTED the initial
  "#2409 merge-ready" verdict: 3 unresolved bot review threads (P1 ledger alignment, P2
  design-authority reference, P2 temp-root blessing). Lesson institutionalized as I6/I8:
  merge-readiness includes GraphQL reviewThreads, not just CI+mergeable. Why optimal: the
  refuted verdict would have signed a flawed owner-authorization packet.

## Phase 1 — A8 preclearance program (07-01 → 07-02), M-A8-PRECLEARANCE-PROGRAM

- #2409 `54d616b3` — corrected A8 implementation spec + folded ledger reconciliation
  (fixed all three bot findings; temp-roots narrowed to test-fixture-only). Why: the spec is
  the document the owner authorizes from; its quality gates everything downstream.
- #2410 `abd8c3f8` — docs/MASTER_CONTEXT.md published (with bot-driven identity-redaction
  fixes). Why: made 72h of campaign context durable instead of branch-stranded.
- #2411 `0290ff5b` — proof-provenance policy docs landed (refreshed against live main rather
  than landing stale). Why: honest provenance beats archaeology.
- #2412 `67bab0b0` — A7 full-chain CI durability: synthetic offline integration tests of
  connector→parser→regex→sidecar→bridge incl. the fail-closed no-receipt block, wired into
  `sec-xbrl-arelle-provisioning`. Why: before this, a regression anywhere in the real chain
  was invisible to CI (only Arelle resolution was covered by #2407).
- #2413 `265c1a12` — A8 owner decision brief: GO/GO-PARTIAL/HOLD with consequences, surface
  choice (controlled-submit recommended vs legacy), acceptance criteria embedded. Why: the
  owner decision needed a single signable document with pass/fail-checkable criteria.
- Historical CI note: the main-branch run at #2413 failed transiently
  (backend-layer3-api shard + release-gate) and recovered on later runs — recorded so no one
  claims "every main run in the sequence was green."

## Phase 2 — Owner GO and the runtime (07-02)

- Owner GO received from the operator-supplied authorization source: surface = current
  SEC-XBRL controlled-submit; durable root via local STORAGE_DIR only; explicit
  Not-Authorized list.
- #2414 `c64ed422` — RC3 acceptance completeness: 6 missing SEC-XBRL test files wired in +
  a drift guard so the list can never silently lag again (declared=58 tracked=58). Why:
  acceptance surfaces that silently omit tests are worse than none.
- #2415 `6a28d0a4` — **the Tier-2 runtime**: storage-root hygiene (I4), retention policy v1
  emission, no-deletion guard, override-ack flag, containment coupling. Merged only after a
  two-round independent review: round 1 NEEDS-CHANGES (OneDrive-variant detection bypass +
  6 untested hygiene classes — both confirmed by adversarial verification), round 2 approved
  after fix verification plus a ledger-truth correction (manifest cited an undiffed file).
  Why the process: value reveal is the named Tier-2 trigger; the review demonstrably caught
  a real rail bypass pre-merge.
- #2416 `5a3cc213` — OPERATOR_UTILIZATION_INDEX: single operator entry point. #2417
  `6b735721` — ops closeout + ledgers. #2418 `f2eb7f7f` — golden-path fix: the ScienceBase
  live fixture queried a nonexistent 2026 dataset; re-pointed to a verified 2023 item with
  gate strictness unchanged; `project6.ps1 -Action all` proven green over 3 consecutive
  runs. Why: "functions as intended" includes the golden path actually completing.
- Operator proof (synthetic, off-repo): hygiene reject/accept-with-override on the owner
  root, durable store write/read, cross-process durability, reveal-guard slice 13/13, and a
  live demonstration of the boot containment guard. Why synthetic first: proved the merged
  machinery end-to-end before real data touched it.
- #2419 `7fa72e74` — record truth v1 (proof recorded, arming recipe documented).
  #2420 `a1637393` — record reconciliation v2 (supersession notes in A8 planning docs,
  historical anchors marked, #2419 entries re-worded merged) — the unanimous single next
  action of the dual adversarial audits.

## Phase 3 — Dual adversarial audits (07-02)

- Two blind-lens audits (M-ADV-STATE-AUDIT-A1/A2) re-derived the entire arc with zero trust:
  bounded claim CONFIRMED ("A8 value-retention arc closed, defaults false"), broad claim
  REFUTED ("functions in full / nothing remains" — the repo's own authorities keep
  production-readiness gates open). Why run two: convergence between independent auditors is
  the strongest verification signal available; their one divergence (admission semantics)
  was adjudicated from source and became I10.

## Phase 4 — O6 hardening + forward options (07-02 → 07-03)

- #2421 `f566ddb1` — O6: support-matrix boundary wording (chose wording-path over pin-list
  expansion — the matrix pins capability defaults, not acknowledgement knobs), CI-subset
  documentation, no-deletion threat-model note, hygiene edge tests (case/separator/OneDrive
  variants, symlink rejection). Why wording-path: keeps the matrix's meaning crisp instead of
  growing an unbounded knob inventory.
- M-FWD-OPTIONS-2: evidence-anchored option analysis; determined the board's
  "live smoke / Arelle binding next" language was HISTORICAL (superseded by the A7 PROVEN
  entry) and that retained June artifacts made a zero-egress replay possible. Adversarial
  verification then found the retained artifacts present on disk — collapsing the biggest
  ranked risk.

## Phase 5 — Real-data proof: the fused operator lane (07-02)

- D1→O2→O3 executed in ONE checkpointed owner-local lane (orchestrator main session, worktree at
  then-tip `a1637393`, zero repo file changes, ZERO SEC egress):
  - CK1: June one-filing chain replayed by receipt+hash under current main (523 facts,
    `network_request_made=false`, 7.07MB retained bytes sha-verified).
  - CK2: internal value store armed per-run → 523 real records retained durably
    (513 non-empty), policy v1, receipt projection still redacted.
  - CK3: full real service chain — material bridge → DatasetVersion → projection → packet →
    workflow → approved decision → value-reveal authority (real resolver, hash-only) →
    controlled submit: **523 facts revealed, 497 non-empty real values**,
    `value_reveal_performed=true`, `production_readiness_claimed=false`, fail-closed on
    missing confirmation.
- Why fused instead of three serialized lanes: each checkpoint is individually fail-closed,
  so staging inside one lane gives identical safety at a fraction of the ceremony; and CK3
  structurally requires CK2's artifacts anyway. Why replay instead of fresh smoke: retained
  public artifacts made new egress pure cost.
- Why run by the orchestrator session, not a subagent: an executor subagent correctly
  refused (it could not verify the owner-authorization chain that lived in the main
  session's context) — operator proofs run where the authorization chain is held.

## Phase 6 — FWD3 dual investigation + record/durability closure (07-03 → 07-04)

- M-FWD3-EVIDENCE + M-FWD3-CRITERIA (blind lenses): both independently
  hash-verified the real-data proof artifacts; unanimous P1 = record-truth PR. Orchestrator
  adjudications: 347 worktrees confirmed real (earlier counts were head-truncated views);
  corpus validation gated by BOTH cutover+corpus flags; I10 admission semantics settled from
  source.
- #2422 `be6d9b1b` — record truth v3: real-data proof recorded across 9 surfaces (all
  sanitized hashes/counts, both receipt generations distinguished), O6 tranche recorded,
  I10 clarification recorded.
- Durable-root decision (owner): initial in-repo request surfaced as code-rejected and
  durability-impossible (see I5); owner approved canonical `C:/p6store`. Operator migration
  executed same day: copy-verify-repoint, 43 files/16.62MB, source retained, hygiene
  `accepted` with NO override, store 523/policy-v1/hash-match re-verified, manifests written
  to both locations.
- #2423 `e661e05a` — repo side: `provision-a8-root` action + warning-only `setup` hook
  (the machine-level root is shared by every worktree after provisioning; `setup` attempts
  non-fatal provisioning and the dedicated action is strict), guidance-only env comment,
  migration recorded in ledgers by manifest sha. Main tip at ledger time.

## Phase 7 - Corpus-go domestic breadth closure (07-05)

- #2427 `99efa28d` - hardening tranche for corpus admission gates. Why: before
  broadening evidence, empty/ambiguous corpus outcomes needed to fail closed
  instead of becoming soft operator interpretation.
- #2428 `154b8a38`, #2429 `4ad672f3`, and #2430 `24502721` - historical SEC
  taxonomy pins, bare cache layout handling, and 2026 SEC taxonomy pins. Why:
  the corpus runner needed year-aware taxonomy resolution before broad
  multi-filing evidence could be trusted.
- #2431 `92b069b9` - explicit corpus form selection. Why: the owner matrix had
  public form intent, and the runner needed to prefer the requested 10-K/10-Q
  path before discovery fallback.
- #2432 `2d6fdbde` - SEC inline transforms plugin. Why: the operator probe proved
  that the `ixt-sec` registry was absent from Arelle core; the plugin fixed the
  root cause and re-proved the previously blocked filing with
  `model_error_count=0`.
- 2026-07-05 corpus-go run - owner-authorized 30-ticker matrix plus TSM
  supplemental, per-ticker isolated two-pass handling, 39 supported filings and
  21 supported issuers, with run-plan minimums 30/15 exceeded and all run-level
  gates passing. The committed record is hash/count/disposition only:
  aggregate report SHA-256
  `113ce73679547f5d202cb273ebca9d2373f90fab9ae688e9159cc7894c3cee10` at
  durable-root relative `corpus_run/CORPUS_GO_RUN_REPORT.json`.
- Named residuals are honest follow-ups, not unnamed failures: foreign IFRS
  annuals for `SONY`, `CCJ`, `DNN`, `NXE`, `MT`, and `TSM` remain blocked with
  admitted reason code `taxonomy_year_unprovisioned` after the operator symptom
  `arelle_model_errors_present`; `6-K` filings block as pre-inline-era/no-iXBRL
  by design; `KAP`, `PDN`, and `YCA` map to
  `official_ticker_resolution_missing`; and `TSMC-as-written` maps to
  `ticker_alias_resolution_required`.

## Phase 8 - Corpus 40 addendum (07-05)

- #2436 `fc141039` - SEC CYD family pin and family-vintage reason code. Why:
  MSFT FY2025 10-K imported CYD 2024 despite the fiscal-year label, so the
  helper needed pinned CYD family-vintage awareness and a named fail-closed
  disposition for future unprovisioned family vintages.
- Phase-2 operator replay - zero-egress governed receipt-bound MSFT FY2025 10-K
  replay using `cyd-replay-msft-10k-r1`: 1829/1829 facts resolved,
  model_error_count 0, value store persisted 1829 records, and independent
  regrade verdict `PASS_WITH_ATTESTED_FIELDS` with zero hash mismatches. Why:
  retained evidence plus the CYD pin closed the only domestic named 10-K block
  without adding live egress.
- Corpus distribution supersession: the #2433/#2434 39-filing record remains
  historical; current corpus evidence records 40 supported filings, 21 supported
  issuers, and 19 full domestic 10-K/10-Q pairs. IFRS annuals and `cyd-2025`
  loose-file packaging remain explicit follow-ups.

## Phase 9 - Gate registry, program hygiene, and coverage critical path (07-06)

- #2435 `fab89ced` - corpus-run gate registry. Why: the executed corpus arc
  revealed gate-count drift and unclear applicability between live-run controls
  and zero-egress replay/report-only controls. The registry now names G1-G10,
  classifies ACTIVE-NOW versus LIVE-RUN-ONLY gates, and requires independent
  regrade before run-level "gates passed" claims.
- #2437 `c6bb87f8` - corpus-40 record addendum. Why: after #2436 and the
  governed zero-egress MSFT replay, the current record needed a dated
  supersession that preserved #2433/#2434 as historical while recording the
  current 40 supported-equivalent filings / 21 issuers / 19 full domestic
  pairs distribution. The addendum kept the replay operator-attested +
  independently regraded (`PASS_WITH_ATTESTED_FIELDS`) instead of overstating
  it as an unqualified live-run result.
- #2438 `be8efadb` - backend-coverage xdist Option A. Why: backend-coverage
  was the release-gate critical path; in-job pytest-xdist reduced the
  post-merge main backend-coverage job to 494 seconds while preserving the job
  id, test target, coverage targets, and `--cov-fail-under=90` semantics. The
  proof preserved line-set parity, collect parity, floor-trip failure, and
  hardware-capped soak evidence.
- Program hygiene decisions from the same arc: enumerate taxonomy families
  before fetch, build `cyd-2025` as a deterministic operator-provenance zip if
  owner-authorized, treat cleanup manifests as stale until recomputed, serialize
  heavy local Python/Arelle work per machine, and refresh current-pointer fields
  whenever they quote superseded facts.

## Phase 10 - CYD 2025 pin and egress-class boundary (07-06)

- #2440 `6d962b24` - SEC `cyd-2025` taxonomy archive pin. Why: after D20
  selected a deterministic operator-built zip for the loose-file CYD 2025
  vintage, the repo needed the actual pin, extraction, entrypoint, and sidecar
  admission surface. The lane landed `sec-cyd-2025` as an operator-built archive
  with 7 member hashes, deterministic zip construction, flat extraction, and
  sidecar readiness when `cyd-2025.zip` is in the provisioner package set.
- Operator arming discipline now has a dated record: `CYD2025_FETCH_ARMING.json`
  hash `af704db4bf1b171bd1a8bea7a6b03fcf7bbd57e8f1a92cdadc02256ef5f490f6`
  armed only the established `xbrl.sec.gov` taxonomy host class and explicitly
  did not arm `xbrl.ifrs.org`. That record forced D27: generic owner directives
  apply only inside established egress classes; new host classes still require a
  named grant with host and request budget.
- Post-#2440 provisioning report
  `7d5f719c274b2c64275498b52832913d6ad0914847bc4abde54e2842063527ee`
  reports 12/12 packages loaded and 26/26 offline entrypoints OK, including
  both `cyd/2024` and `cyd/2025`. This closes the CYD prep side of F3, but
  did not itself execute the IFRS side.
- #2442 `e7e9e867` - IFRS 2025 taxonomy package pin. Why: after the IFRS
  package grant/admission lane landed, the repo needed the program-context
  frontier to stop describing IFRS package prep as blocked. The lane pins
  retained `IFRSAT-2025.zip` hash
  `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19` and
  verifies package-set/sidecar admission without publishing a foreign-annual
  replay result.

## Phase 11 - Corpus 46 retained foreign-annual replay record (07-06)

- Owner-named IFRS grant executed within its 5-request budget. The arming
  record hash
  `cb275a03cbbadfcdb55a8eedc3d585f8dd5eb6cb4c9a8b45bac986ceb080b8f6`
  records `written_before_first_request=true`; the PINNING note hash
  `20dfec68cccba35eb9969763ec056ac568824dd0df5f5b9c43151ac854945c07`
  records the 5/5 request ledger; `IFRSAT-2025.zip` hashes to
  `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19`.
- Post-#2442 r3 provisioning report
  `6ff72308060a5769ff708b556bc3e9a6269ac867b1f06eaa6d0291f4a8a9708c`
  reports `ready=true`, 13/13 packages loaded, 26/26 SEC entrypoints intact,
  and IFRS 2025 offline entrypoints loaded.
- Six retained IFRS annuals replayed with zero SEC EDGAR egress and fresh
  client_request_ids `ifrs-replay-01-r1` through `ifrs-replay-06-r1`: 6/6
  `READY`, stores persisted, zero named blocks, fact/value counts 4693 / 886 /
  1582 / 7335 / 2670 / 3565, total 20,731 records. Results hash
  `7d691b6ac96fe31e40797b9e1ef582274e4792fb331c0071f821250c9189bbc7`;
  evidence bundle hash
  `a49b9c5553fd21788307b2dae9407b36582a97b467780aeeceda7772c44c40ff`;
  independent regrade hash
  `6e755725e65c11fb7fd1ddc926911804aebf924b79da9fc553f56a88b2bce2e3`,
  verdict `PASS_WITH_ATTESTED_FIELDS`.
- Corpus distribution supersession: the #2433/#2434 39-filing record and
  #2437 40-filing addendum remain historical. Current corpus evidence records
  46 supported filings, with zero remaining resolvable retained-annual replay
  blocks. `6-K` no-inline and non-SEC/alias dispositions remain by design.
  #2443 records the current 27 supported issuers, derived from the prior 21
  supported issuers plus the six named distinct retained IFRS issuers (`SONY`,
  `CCJ`, `DNN`, `NXE`, `MT`, and `TSM`).

## Post-Phase-11 hardening addendum (07-06)

- #2445 `2c4f160d` - post-build fail-closed `verify_zip_determinism` guard
  on operator-built taxonomy archives. The guard checks five mismatch reason
  classes (`member_order`, `date_time`, `create_system`, `compress_type`, and
  `external_attr`) and keeps the temp-sibling verify-then-promote flow from
  landing rejected archives at the final taxonomy path; code and tests only.
  Why: a platform-metadata drift in a future operator-built pin would otherwise
  be caught only by Linux CI after the fact, the same incident class as the
  `cyd-2025` `create_system` mismatch.

## Phase 12 - Governance durability, forward frontier, and connector breadth (07-06 -> 07-08)

- #2446 through #2455 compressed the repo-ops and release-governance record:
  governance inbox durability, worktree cleanup execution records, dirty
  adjudication records, preserve-sweep records, campaign closeout, and the
  eight-family release-gate/orphan-workflow record. The durable pointer is
  `docs/campaign-records/2026-07-06-repo-ops-campaign.md`. Why: the program
  had accumulated operational facts that needed hash/count/disposition records
  instead of relying on mutable inbox state or stale worktree narratives.
- #2456 through #2458 closed the forward-frontier and connector-source decision
  chain: the forward-frontier dossier, replica-cadence fence, and
  source-candidates record established the connector-breadth / local-depth
  fork and classified FAO/BTS/IMF boundaries. Why: build mandates needed a
  source-owned, bounded authority trail before individual connector lanes could
  proceed without reopening broad web research.
- #2459 through #2466 executed and closed the connector-breadth program:
  World Bank, CFTC COT, USGS MCS, BLS v1, and OECD SDMX landed as bounded
  anonymous/public connector slices, World Bank polish landed, and the IMF
  DataMapper owner grant was exercised to a grant-hard STOP (`GET 1/4` returned
  HTTP 403, zero contingency spent, no build). Capability count moved 29 -> 32.
  The durable execution pointer is
  `docs/campaign-records/2026-07-08-connector-program.md`. Why: the program
  closed the safe anonymous connector set while preserving IMF as an explicit
  owner-gated/deferred fork rather than working around the 403.

## Net state after Phase 12

Local SEC-XBRL pipeline proven end-to-end ON REAL DATA: live-acquired filing → parsed →
Arelle-resolved → durably retained values → controlled governed reveal; every layer
fail-closed, redaction-verified, CI-guarded where CI can reach, recorded in the repo, and
durable across all worktrees. The domestic corpus breadth lane is now executed
for the SEC inline scope and the retained foreign-annual replay follow-up is
closed at 46 supported filings. SEC `cyd-2025` provisioning prep and IFRS 2025
package prep are executed and pinned; the six retained IFRS annual replays are
hash-recorded, zero-egress, store-persisted, and independently regraded with
attested-field boundaries. Source defaults all False. Nothing production-claimed.
Connector breadth is now closed for the safe anonymous/public set: World Bank,
CFTC COT, USGS MCS, BLS v1, and OECD SDMX landed offline-proven in PRs
#2459-#2464, moving support-matrix capability count 29 -> 32. The execution
record and connector-program archive landed in #2465-#2467. IMF DataMapper
envelope grant was exercised and stopped hard on HTTP 403 (`GET 1/4`, zero
contingency spent), leaving IMF owner-gated with the unlock fork recorded in
F9/D31. FAO and BTS remain defer-final. Live pilots still require per-connector
D27 owner grants, and all connector source defaults remain default-off/local.

## Phase 13 - Admission spine frontier closure (07-09)

- #2469 `6eb2fab4` published D32 and planning doc 1366 as the Phase 0+1
  source-artifact admission-spine contract. Why: the program needed a single
  documented admission axis for source-family artifacts before later code lanes
  could close individual seams.
- #2470 `423fbbae` reconciled the admission-map count and posture record after
  stage-2 audit feedback. Why: the durable contract needed to distinguish
  program source families, raw-mixed workbench materialization, and exact
  producer-count facts without relying on review-session memory.
- #2471 `e413d2df` executed Phase 2 by routing NRC APS through a neutral facade
  with behavior-neutral coverage. Why: the reference family could be
  decoupled from direct workbench imports without changing admitted behavior.
- #2472 `e31f5ebd` executed Phase 3 by landing the ScienceBase/MCS connector
  direct envelope to connector source-intake Gate B, and executed Phase 7 by
  adding the static/CI guard that keeps the material-preview producer registry
  exact. Why: the first connector pilot needed both a landed connector
  admission path and a guard against silent reintroduction of connector-owned
  downstream admission state.

This entry fixes cold-start reachability from `docs/program-context/INDEX.md`
to this chronological ledger: a new reader can reconstruct the landed
admission-spine set (#2469-#2472) without untracked session memory. Phase 4
shape pilots, Phase 5 proof reconstruction, Phase 6 one named operator workflow
proof, and owner-gated future decisions remain separate unless later authority
lands them.

## Phase 14 - Admission-spine B1 closure, bounded proof, and owner ratification (07-11 to 07-13)

- #2473 `cdc832d9cbfba5b0485ed0cca0c2a79854605044` - `docs: publish
  admission spine closure record`. Why: the landed Phase 2/3/7 chain needed a
  durable closure surface before the remaining B1 proof and owner gates could
  be evaluated without session-local context.
- #2474 `2b7973d72e65661acc30c3ec88791fe1c88061e0` - `test(layer3): close
  Lane A admission guard gaps`. Why: the B1a lane required the admitted-source
  and fail-closed guard gaps to be pinned before a vertical-loop proof could be
  treated as bounded evidence.
- #2475 `4439b1de50d85b2bc72bd92fa8e54717b7e9d500` - `test(layer3): add B1a
  connector vertical loop proof`. Why: this supplied the connector-loop test
  proof while preserving the distinction between a bounded B1a run and an
  integrated production loop.
- #2476 `56c56e77ebe435c3a9f035f47de2d8611efee7d7` - `test(layer3): allow
  guarded loopback sockets`. Why: it removed the documented loopback false
  positive without widening non-loopback network authority.
- The operator-held B1a run record closes with a bounded pass, and the separate
  CL-6 convergence rerun closes the record-fix checks. Those receipts are
  hash/byte anchored in `04-evidence-registry.md`; they prove neither an
  integrated connector-originated loop nor analytical utility, Phase 4/5/6
  completion, production readiness, or B1b implementation.
- Owner disposition: the complete 58-row identity-metadata enumeration is
  `RATIFIED-EXACTLY-AS-PROPOSED`; the promotion-identity precedence rule is
  `RATIFIED-AS-PROPOSED`. The only remaining B1b owner gate is an explicit
  second key. Future intent is non-authorizing, the key is not granted, and no
  withheld disposition is claimed.
- Exact standing:
  `B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`
- Authority boundary: this phase records decisions and evidence only. It grants
  no implementation, schema, ORM, migration, runtime, build-dispatch, B1b
  build-PR, or B1b build-merge authority.
