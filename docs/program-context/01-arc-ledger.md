# 01 — Arc Ledger (chronological accomplishment record)

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

## Net state after Phase 10

Local SEC-XBRL pipeline proven end-to-end ON REAL DATA: live-acquired filing → parsed →
Arelle-resolved → durably retained values → controlled governed reveal; every layer
fail-closed, redaction-verified, CI-guarded where CI can reach, recorded in the repo, and
durable across all worktrees. The domestic corpus breadth lane is now executed
for the SEC inline scope with 40 supported filings across 21 supported issuers.
SEC `cyd-2025` provisioning prep and IFRS 2025 package prep are executed and
pinned. Retained foreign-annual zero-egress replay/result recording remains
open. Source defaults all False. Nothing production-claimed.
