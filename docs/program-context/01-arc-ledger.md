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

## Net state at ledger time

Local SEC-XBRL pipeline proven end-to-end ON REAL DATA: live-acquired filing → parsed →
Arelle-resolved → durably retained values → controlled governed reveal; every layer
fail-closed, redaction-verified, CI-guarded where CI can reach, recorded in the repo, and
durable across all worktrees. Source defaults all False. Nothing production-claimed.
