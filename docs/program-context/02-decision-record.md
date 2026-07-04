# 02 — Decision Record

ADR-style. Each: context → alternatives → decision → why optimal given the circumstances →
evidence → revisit-when. Dates 2026.

## D1. Retention over erasure (06-28, reaffirmed throughout)

- Context: original A8 design was a secure-erasure lifecycle for "raw-at-rest" SEC values.
- Alternatives: (a) erasure lifecycle; (b) avoidance (never store); (c) durable retention.
- Decision: (c), with redaction re-aimed at identity/paths/secrets.
- Why optimal: the data is public-domain; erasure destroyed evidence while defending
  nothing; avoidance made the product (value analysis) impossible. Independently verified
  against source before adoption (no documented erasure rationale existed).
- Evidence: PR #2406 rewrite; posture recorded repo-wide; I1/I2.
- Revisit when: a non-public/licensed/contractual source class is ever ingested — that class
  needs its own disposition policy (explicitly out of scope for SEC EDGAR).

## D2. Controlled-submit surface over legacy Arelle reveal (07-02)

- Context: two reveal surfaces existed; owner had to pick one for GO.
- Alternatives: (a) current controlled-submit path; (b) legacy Arelle reveal service;
  (c) both.
- Decision: (a). Legacy stays default-off governed sibling; (c) rejected outright.
- Why optimal: (a) is newer, fail-closed by construction, bound to server-owned lineage
  (decision → workflow → packet → projection → authority), and is the surface the A7 proof
  chain feeds. (b) predates the lineage model and would need independent hardening. (c)
  doubles the audit surface for zero product gain.
- Evidence: a8-owner-decision-brief.md; owner GO text; CK3 executed through (a).
- Revisit when: a distinct product use for legacy reveal appears — requires its own
  authorization + acceptance criteria (P4 handles labeling meanwhile).

## D3. Hygiene override-ack design (07-02)

- Context: owner's chosen proof root was Downloads-like/temp-named — classes the owner's own
  authorization contract rejected.
- Alternatives: (a) reject owner root, force a compliant one; (b) silently weaken the rail;
  (c) strict contract + narrow recorded override for NAME classes only.
- Decision: (c).
- Why optimal: (a) blocks the owner on their own machine for a heuristic, not a structural
  risk; (b) silently destroys the rail; (c) preserves the full contract, honors owner intent,
  and converts the exception into recorded evidence (override flag + reason code + namespace
  hash in every receipt). Structural classes stay non-overridable because no owner intent
  makes cloud-sync corruption or git churn safe.
- Evidence: #2415 implementation + tests; both operator proofs carry the recorded override.
- Revisit when: never silently; only via explicit Tier-2 posture change.

## D4. Op-time hygiene enforcement, not boot gate (07-02)

- Context: `settings.storage_dir` defaults repo-relative and feeds non-A8 subsystems.
- Alternatives: (a) validate root at app startup; (b) validate at A8 value-store operations.
- Decision: (b).
- Why optimal: (a) breaks every ordinary dev run for subsystems that never touch retained
  values (fragility for zero safety). (b) puts the check exactly where the protected asset
  is touched. The separate boot-time containment validator still guards the genuinely global
  condition (raw-bearing flags armed with unsafe storage/db).
- Evidence: config.py:113 default; sidecar op-time checks; containment validator; the
  first CK2 run failing closed at boot until containment env was correct.

## D5. Asymmetric merge gates (07-02)

- Context: velocity mandate vs a value-reveal runtime change.
- Alternatives: (a) review everything; (b) review nothing (velocity); (c) Tier-triggered
  asymmetry.
- Decision: (c) — Tier-1 self-merge on green + resolved threads; Tier-2 risk documentation,
  targeted verification, and independent review when the live merge-gate policy's concrete
  review triggers or blockers apply.
- Why optimal: (a) would have added ~12 review round-trips to docs lanes for zero findings;
  (b) would have merged #2415 with a real OneDrive-variant hygiene bypass (caught in review
  round 1). The asymmetry provably paid for itself exactly once — on the one lane that
  needed it.
- Evidence: #2415 two-round review record; every other lane's clean self-merge.

## D6. Fused operator lane D1→O2→O3 (07-02)

- Context: three ranked pursuits (replay-proof, Arelle binding proof, real-data reveal) each
  needed the previous one's artifacts.
- Alternatives: (a) three serialized lanes with separate closeouts; (b) one checkpointed
  lane.
- Decision: (b), each checkpoint individually fail-closed and banked.
- Why optimal: identical safety semantics (abort at any checkpoint = the serialized version),
  one-third the ceremony, and CK3 structurally requires CK2's store anyway. The
  investigating agent recommended (a) for provenance cleanliness; the fusion preserved that
  cleanliness via per-checkpoint evidence records — a case where the orchestrator's
  adversarial review improved on the investigator's ranking.
- Evidence: ck1/ck2/ck3 outputs; a8_real_reveal_report.json; #2422 record.

## D7. Zero-egress replay over fresh live smoke (07-02→03)

- Context: board language said "live smoke next"; June artifacts existed on disk.
- Alternatives: (a) fresh SEC egress smoke; (b) replay retained artifacts by receipt+hash.
- Decision: (b), with (a) demoted to fallback-if-artifacts-stale.
- Why optimal: retained public artifacts carry full hash lineage; a new fetch adds network
  risk, rate-limit cost, and fair-access footprint to prove something the receipts already
  prove. The board's "next" language was verified HISTORICAL per its own supersession rules
  before deciding.
- Evidence: M-FWD-OPTIONS-2 analysis + orchestrator sandbox inventory verification; CK1's
  `network_request_made=false` chain.

## D8. Canonical machine-root over in-repo root (07-04)

- Context: owner requested an in-repo durable root that "exists in every new worktree."
- Alternatives: (a) in-repo tracked folder; (b) rail change to permit (a); (c) canonical
  machine-level root auto-provisioned by repo tooling; (d) repo-adjacent sibling.
- Decision: (c) `C:/p6store`, owner-approved after the conflict was surfaced.
- Why optimal: (a) is triple-rejected by I4 (repo_relative + OneDrive-synced repo +
  git_tracked) AND cannot deliver durability — worktrees share only tracked files, so the
  folder arrives empty or the values enter git history. (b) removes a rail that guards a
  real corruption mechanism (OneDrive sync mid-write) to simulate a property (per-worktree
  store) that still wouldn't exist. (d) fails because the repo's parent (Desktop) is also
  OneDrive-synced on this machine. (c) delivers the actual intent — always-present,
  zero-setup, rebase-proof — more strongly than the literal request: one shared store
  pre-exists every worktree by construction.
- Evidence: #2423; MIGRATION_MANIFEST.json (sha 845974f7…); live `provision-a8-root` proof
  from a fresh worktree.
- Revisit when: multi-machine operation begins (then the canonical-root concept needs a
  per-machine provisioning story, same design).

## D9. Migration = copy-verify-repoint, never move/delete (07-04)

- Context: existing store lived in the sandbox (recorded-override root).
- Alternatives: (a) move; (b) copy + delete source; (c) copy + verify + repoint, source
  retained.
- Decision: (c).
- Why optimal: I1 forbids destroying retained values under any pretext including migration;
  the source doubles as an independent backup; namespace hashes inside copied artifacts
  describe the ORIGIN root and are preserved as historical evidence rather than falsified —
  new writes under the new root mint new namespace hashes.
- Evidence: robocopy 43/43 zero-fail; p3_verify.py PASS (hygiene accepted no-override,
  chain + store re-verified); both manifests.

## D10. Program-context set as a structured file family (07-04, this set)

- Context: owner requested an exhaustive all-encompassing context artifact.
- Alternatives: (a) grow MASTER_CONTEXT into a monolith; (b) new competing master doc;
  (c) structured set under docs/program-context/ with MASTER_CONTEXT as executive summary.
- Decision: (c).
- Why optimal: (a) makes the executive summary unreadable and churn-heavy; (b) creates dual
  sources of truth (the exact drift failure mode three audits flagged); (c) separates
  concerns (invariants / history / reasoning / plan / evidence) with explicit authority
  ordering and a maintenance protocol. Authored by the session holding the decision
  reasoning; independently anchor-verified before landing (I8).
- Revisit when: the set itself drifts — the INDEX maintenance protocol is the guard.

## D11. Delegation architecture (standing)

- Context: two repo-lane desktop threads + one orchestrator session; owner directive to delegate
  most execution.
- Decision: repo-lane threads own repo/git lanes (fenced, one PR at a time); the orchestrator
  session owns operator-private lanes (proofs, migrations — where the authorization chain
  lives), independent Tier-2 review, cross-lane adjudication, and record dispatch.
- Why optimal: subagents cannot verify in-band owner authorization (demonstrated by an
  executor's correct refusal of the proof task); git surfaces stay single-writer per lane;
  and every repo-lane product gets adversarially reviewed by a party that didn't write it.
- Evidence: 15 PRs landed collision-free; the refusal incident; two-round #2415 review.
