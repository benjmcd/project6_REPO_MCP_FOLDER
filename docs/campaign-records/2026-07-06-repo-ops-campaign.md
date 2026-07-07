> Tracked campaign record, frozen at PR #2454 (campaign end state = main 254e2f81 / #2453). Source: the untracked living dossier at state/agent-inbox/CAMPAIGN_DOSSIER_2026-07-06.md, sha256 72ec9abdff999c7a346c2bde26549159d4e0d6d5c93fb15269b578d5bab62efc at landing. This is a dated CAMPAIGN record subordinate to docs/MASTER_CONTEXT.md and docs/program-context/ (D10: it is not a second master context; its own §preamble states the authority order). Future campaign records land as siblings in this folder.

# Campaign Dossier — Repo-Operations / Governance / Hygiene Arc, 2026-07-06 → 2026-07-07

Living synthesis document. Maintained by the orchestrating Claude session; updated at each
milestone closeout. This is the ONE place the whole campaign is contextualized end-to-end with
per-decision reasoning; the canonical program record remains `docs/program-context/` (per D10
there is no second master-context — this dossier is a CAMPAIGN synthesis that cites the
canonical surfaces, it does not replace them).

Authority order for anything asserted here: live `project6-origin/main` > merged PR evidence >
hash-anchored untracked artifacts (named below) > this dossier's narrative. If this document
ever disagrees with those, those win and this document gets a dated correction.

Status at last update: main tip `254e2f81` (#2453); campaign execution COMPLETE — all
agent-actionable work done; remainder is owner-only + fail-closed holds (see §6/§7).

---

## 1. How this campaign started (context + problem statement)

A four-session-log review (owner-directed, 2026-07-06) reconstructed the state of two programs
(project6 SEC-XBRL arc; sibling observatory repo) from ~33k lines of session exports, verified
every load-bearing claim against live git/GitHub, and found the project6 actionable frontier
quiescent EXCEPT for three unmitigated exposures:

- R1 STORAGE: ~350 registered worktrees (~246GB real, initially underestimated at ~45GB from a
  3-item sample — lesson: never extrapolate from tiny samples) under an OneDrive-synced path,
  on a machine with a PRIOR 0-free-bytes incident. Only frontier item with a realized failure.
- R2 CLASS-RISK: zip metadata platform-divergence (create_system) had broken a taxonomy pin
  once and was fixed reactively for one archive only; every future operator-built pin could
  re-trip it, caught only by Linux CI after the fact.
- R3 GOVERNANCE DURABILITY: the campaign's only Tier-2 approval (#2415) existed solely in an
  untracked, single-copy inbox log; GitHub shows no human APPROVED review. The dual-agent audit
  trail had no durable anchor.

Why these three first: R1 had a realized failure mode; R2 was a proven recurrence class with a
cheap preventive fix; R3 was a single-point-of-failure on the evidence chain that everything
else's auditability depends on. All other candidate work was either owner-gated by policy
(value-reveal, egress, production arming) or cosmetic.

## 2. Operating model used throughout (and why it is the right fit)

- Claude (this session) = orchestrator/verifier: plans, adversarially reviews plans BEFORE
  dispatch, verifies every closeout independently (never trusts reports), maintains records.
- Codex threads (p6_agent1/2/3) = executors: one lane per dispatch, isolated fresh worktrees
  off live main, self-verification mandated, closeout reports appended to the shared inbox log.
- Opus workflows = exploration/verification fan-outs; Fable agents reserved for the highest-
  stakes adversarial verification (they independently re-derive rather than sample).
Justification: separation of author/verifier is the standing rail; parallel Codex lanes with
disjoint file fences preserve isolation on one shared machine; adversarial pre-dispatch review
is empirically load-bearing here — EVERY pass found real defects (8, then 6, then 3, then 3;
including two genuine data-loss vectors). The loop is: draft mandate → adversarial critique
against live repo → patch → dispatch → pickup-verify → poll → independently verify closeout.
- Hardware rail (standing): serialize heavy python; one process at a time in ops lanes;
  bounded timeouts on OneDrive traversals (a du over nested clones exceeded 120s in testing).
- Honesty rails (standing, owner directive): fail-closed everywhere; supersession-not-rewrite
  in records; no value erasure ever (SEC values are public-domain — placement is a posture
  question, never a secrecy question); leak scans on every added tracked line (no machine-local
  user paths, no branding, no accession/CIK, no raw values; bare C:/p6store is the committed
  precedent form).

## 3. Campaign ledger (chronological; each entry: what / why / verification / residuals)

### 3.1 Four-session review (no PR — analysis artifact)
What: 10-agent workflow digested 4 session logs, adversarially verified claims vs live state,
reconstructed timeline/frontier. Why: owner asked for evidence-grounded situational truth; the
memory pointer had gone stale once before (a "frontier exhausted" claim later disproven), so
re-derivation from primary evidence was required rather than trusting prior summaries.
Verification: every verdict carried live git/gh evidence; contradictions between sessions
resolved by evidence, not seniority. Output became the campaign's work-list.

### 3.2 PR #2445 — M-ZIP-DETERMINISM-GUARD (merge 2c4f160d)
What: fail-closed `verify_zip_determinism` post-build guard (5 machine-readable mismatch
classes) wired temp-sibling→verify→promote, operator-built specs only; 3 tests added to the
already-declared test file. Why-optimal: preventive rail beats reactive patching for a proven
recurrence class; temp-sibling promote means a rejected archive can never land at the final
taxonomy path; scoping to operator_built_archive=True avoids asserting determinism on
SEC-published archives the repo never built. Pre-dispatch critique materially fixed the
mandate: no validate-CLI exists (guard wired into the real build path), docs edit dropped
(fence collision), egress framing corrected (CI already egresses; guard adds none).
Verification: merge scope exact 2 files (+166/−6); CI green incl. the provisioning job that
exercises the guard on a real build; thread 1/1 resolved; grandfathered pin re-checked
read-only (hash unchanged). Residual: none (a failed verify leaves a harmless .tmp sibling).

### 3.3 PR #2446 — M-GOV-RECORD-DURABILITY (merge 4e9001ee)
What: D29 decision entry + I12 standing archival protocol + evidence-registry row; off-repo
point-in-time archive `C:/p6store/inbox-archive/2026-07-06/` (50 files, aggregate 42cd507b…).
Why-optimal vs alternatives: committing raw inbox logs was rejected (they carry machine-local
paths the redaction posture forbids; also bloats git); summary-without-anchor was rejected (not
re-checkable). Hash-anchored off-repo archive + in-repo pointer is the established D29 pattern
and makes the snapshot immutable while the live log stays mutable-by-design. CRITICAL honesty
content: the #2415 record documents what does NOT exist (no independent reviewer verdict block;
approval attested only via merge action + implementer report) — recording the absence is the
fix, not fabricating provenance. Verification: my own leak scan clean; archived copy re-hashed
byte-exact by me; 3/3 threads resolved. Residual: archive refresh cadence now standing (I12).

### 3.4 PR #2447 — M-WORKTREE-CLEANUP-EXEC, phases 1+2 (merge 63f7f92d)
What: registered-worktree cleanup, 353→163 registrations, 190 removed (176 in P2; 164 via a
three-gate --force rule with per-entry justification), ~85GB reclaimed; record in
03-forward-plan (F6) — deliberately NOT the arc-ledger (category mismatch; its entries are
corpus phases and its trailer follows an insert-before+rewrite pattern).
Why the two-phase shape was correct: Phase 1 ran with git's native protections plus an
ignored-content guard and a >20% same-cause STOP; it halted at 47% skips — surfacing that most
"dirty" content was machine artifacts (playwright reports, generated .codesight) while ~25
worktrees held modified tracked files (possible unlanded work). Phase 2 encoded the ANALYZED
response: expanded regenerable-safe list (deliberately excluding .claude/ — agent-authored
settings), exact/segment-boundary matching (a substring matcher would have swallowed
storage_test_runtime under storage/), --ignore-submodules=none, and the three-gate force rule
(every status line ??+safe-listed, every !! safe-listed, immediate pre-removal re-scan).
The stop-then-analyze-then-refine sequence is the model for all deletion-class work here:
never push through a surprising pattern; make the pattern the next mandate's evidence.
Verification: force audit clean (zero unsafe tokens, all-?? justifications, commits/branches
preserved on sampled removals), drive free space independently corroborated (+79GB).
Operational lesson recorded: a Codex turn died silently mid-generation (renderer eviction);
detection = frozen rollout + no pending tool call; response = idempotent resume nudge with
materialization verification.

### 3.5 PR #2448 — M-RECORD-SYNC (merge 3b6ea8ca)
What: 4-file extension-only sync (+50/−0): registry PR/SHA rows for #2445–#2447, arc-ledger
hardening addendum for #2445 only (docs PRs stay out per practiced convention — an explicit
scoping decision, not omission), two D26 supersession notes in MASTER_CONTEXT carrying the full
owner-gated remainder, and the forward-plan clauses (dirty-class may hold unlanded work;
placement-violation framing for the /tmp anomaly). Why: the record surfaces are
exhaustive-by-convention for merged tranches; a 3-auditor sweep found the exact gaps with
line-level evidence and per-file convention adjudications (which surfaces are intentionally
scoped vs exhaustive) — edits were made per each file's OWN update pattern, never a generic
append. Verification: zero deleted lines proven, my leak scan clean, manifest sha re-hashed
byte-exact, all markers confirmed on main.

### 3.6 Dirty-class adjudication (read-only; artifact 0c87d88f…, 189,380B)
What: 12 agents adjudicated all 139 protected worktrees per-item (8 dirty adjudicators, 2
ignored-class reviewers, 1 consistency critic). Adjusted tally: 115 TOOL-STATE-ONLY /
8 SUPERSEDED / 11 UNIQUE-CONTENT / 5 AMBIGUOUS. Why read-only-first: deletion decisions must
rest on per-item evidence, and the evidence-gathering itself must be provably non-destructive
(registry count verified identical before/after). The critic deliberately re-checked the
DANGEROUS class (SUPERSEDED — a wrong one loses work) and caught two errors, both from one
root cause: grepping stale pre-refactor paths against the rebuilt main → false-absent verdicts
(l3-package-life UNIQUE→SUPERSEDED; sec-family-res UNIQUE→AMBIGUOUS). That trap became D30.
Key finds: unlanded slice-4 implementation that main's docs claimed live (doc-truth asymmetry);
onlook nested repos with unpushed commits; 17A/17B evidence artifacts.

### 3.7 PR #2449 — M-ADJUDICATION-RECORD (merge a8927c45) + I12 refresh `2026-07-06-adj`
What: 4-file record (+59/−0) incl. the analyst-insight target-state correction note. The lane
STOPPED on two review threads demanding out-of-fence changes — correct rail behavior — and was
completed under explicit direction: thread 1 (commit the raw JSON) resolved via the D29/I12
mechanism (raw artifact stays untracked BY POLICY — it contains machine-local absolute paths;
durability = fresh I12 archive, 42 files, aggregate 9291ee34…, + hash citation in-fence);
thread 2 (rewrite rows in place) resolved by supersession-not-rewrite posture. Why-optimal:
both resolutions apply standing conventions instead of inventing one-off exceptions; the
archive refresh strengthened durability MORE than committing the file would have.

### 3.8 Unlanded-content deep-dive (artifact 03f50a85…, 132,716B) + Fable verification
What: 6 Opus investigators (one per content unit, full lane-context reconstruction) + 2 Fable
adversarial verifiers who independently re-derived the highest-stakes claims. Units 1
(analyst-insight) and 2 (sec-family-res) HELD at byte level; units 3/4/5/6 had completeness
failures → 14 corrected dispositions. Why Fable here: the preserve/discard boundary is where
an error is unrecoverable; redundant same-class verification would repeat the same blind spots,
so the verifiers were tasked to re-enumerate, not re-read. Material new facts they produced:
7 unregistered onlook dirs invisible to `git worktree list` (6 nested repos w/ unpushed
commits); the shared `.git/info/exclude` `/archive/` line blinds plain status in EVERY
worktree; main's tracked onlook proof gate references a runtime clone (641c3a85) surviving
nowhere — that provenance was ALREADY unreproducible before any sweep; a NOT-gitignored 17A
driver (.lane4a) that v1 would have silently swept; cb-runtime-audit-p1 is real code (+1,260/−84),
not tool-state.

### 3.9 worktree-disposition-plan-v2 (ca5b0630…, 8,169B) — the execution spec
What/why: v1's prose plan had four adjudicated inadequacies (unnamed destination, no
containment framing for the 17A bundle, no serialization/timeout bounds, no acceptance/rollback
gates). v2 pins: destination `C:/p6store/worktree-preserve-archive/<date>/<slug>/` (the
posture-blessed root — NEVER state/agent-inbox, which is tracked on main); enumeration =
`--porcelain --ignored --untracked-files=all --ignore-submodules=none` + unregistered-dir
sweep; serial + ~120s bounds; hash-gated acceptance (SNAPSHOT_MANIFEST per item; bundle verify
for nested repos; removal gated on PASS); rollback for untracked items = the verified off-repo
copy (there is no branch fallback for them — this is exactly why copy-verify precedes removal);
p6xbrl relocation framed as an I4/I5/D8/D9 containment OBLIGATION (retained values belong at
the canonical root, not under an OneDrive-synced repo tree).

### 3.10 PR #2450 — M-ADJUDICATION-RECORD-2 (merge bc4dabb2)
What: I11 supersession note; D30 ("uniqueness verdicts grep the current refactored layout");
deep-dive addendum inside the adjudication refresh (+90/−0). Review threads improved two
specifics (require `--untracked-files=all` in inventory rules; mark the pre-Fable 123/16 tally
superseded pending recount) and one out-of-fence deferral later closed by #2452's registry rows.

### 3.11 Execution round (owner "proceed as you see fit", round 3)
Decision analysis: sweep GO + slice-4 GO; queue items #3/#4/#5 collapsed into the sweep as
preserve-first (verified bundles/tar/diff-capture make the keep/land/discard questions
deferrable at zero cost — the preserved copy IS the decision-preserving move); #6 (upstream
push) held back as genuinely owner-personal (public, identity-bearing, third-party repo).
Pre-dispatch critique caught: a nested clone inside a REGISTERED worktree dropped by the
"unregistered dirs" phrasing (ext-onlook-ab — real zero-loss hole); loose top-level content in
the unregistered dirs unguarded by clone-bundle gates (two-part gate added: per-file verified
duplicate pointer OR loose-tar, for everything >100KB); a doc self-contradiction the slice-4
landing note would have created (supersession sentence made mandatory); plus timeout=failure
semantics, a 2GB p6store floor, atomic closeout appends, and a never-`git add -A` rule.

### 3.12 PR #2451 — M-SLICE4-LAND (merge 803143be) — VERIFIED
Exact 5-file scope (+6/−0): nav-link in both review shells (semantic re-apply — the reference
commit's raw hunks no longer applied because main's shells diverged via #2404), two test
assertions, doc landing note superseding the correction note. Post-merge checks: link + tests
+ note all confirmed on main. The doc-truth asymmetry that the adjudication surfaced is closed
in the strongest possible way — by making the documentation TRUE rather than weakening it.

### 3.13 PR #2452 — M-PRESERVE-SWEEP (merge 3f6b4169) — VERIFIED; fail-closed holds
Executed v2: registry 164→25, 138 removed, 89.0GB reclaimed (172.8→83.8GB, one consistent
measurement method), preserve archive with 30 per-item manifests + aggregate (b45fcb61…;
NOTE: aggregate/manifests are utf-8-sig — decode accordingly). 20/30 snapshots verified;
10 FAILED and were HELD, not deleted — the acceptance-gate design working exactly as intended.
Record PR review added MASTER_CONTEXT to the fence (INDEX names it the supersession authority —
a narrow, justified amendment). Diagnosed hold causes (verified, not assumed):
p6xbrl = 2 source-path misses (files live under `17a-aapl-2024-10k/`, present on disk);
7 onlook dirs = bounded-tar timeouts (content intact); candidate-b pair = per-manifest
diagnosis pending. Census also surfaced ~14 NEVER-ADJUDICATED unregistered dirs beyond the 7
onlook ones (csb-*, cb-live-server-scan, l3-snapshot-index, mainline-lane, …).

### 3.14 PR #2453 — M-PRESERVE-SWEEP-P2 (merge 254e2f81) — VERIFIED; campaign execution done
Outcomes (each verified post-merge): p6xbrl + both candidate-b holds completed and removed —
the p6xbrl completion CLOSES the I4/I5 containment obligation (17A values + drivers + branch
bundle now live only under the canonical root; worktree gone). The 7 onlook dirs were RE-HELD
after a second bounded selective-tar failure each (300s timeouts even on selective tars —
OneDrive read cost on those trees is the persistent cause) — the second-failure=hold rule
honored exactly; nothing forced. Of the 14 newly-adjudicated unregistered dirs: 9 removed
after D30-discipline classification + gates (p2-ops, p3-ops, sec-transforms, tax-cache-fix,
tax-pins, csb-r18/r19/w16, l3-snapshot-index); 5 held (cb-live-server-scan, wb-compare-prep,
mainline-lane, pr83-audit, w3). Final state: ZERO repo-local registered worktrees; 12
unregistered dirs held; footprint 82.1GB. Aggregate updated to 44 manifests / 32 verified
(1ae49356…, re-hashed byte-exact by the orchestrator). Record PR review narrowly amended the
fence to include MASTER_CONTEXT + evidence-registry for coherence (the MASTER_CONTEXT edit
rewrote the same-campaign current-pointer summary in place — D26-consistent: the superseded
text/hash remain recoverable in git history and the #2452 dated record). CI green on PR +
post-merge main; 2/2 threads resolved; detached proof PASS; leak scan clean (my re-run).

## 4. Standing lessons extracted (each anchored to its incident)

- D30 (tracked): uniqueness verdicts vs a rebuilt/refactored main need repo-wide symbol greps +
  tree-identity checks (`git diff <sha> <merge> --numstat` empty = fully landed); path-scoped
  greps and ancestry tests under-count landed work. (From the two adjudication corrections.)
- Enumeration traps (tracked in D30's body): `git worktree list` is not a directory inventory
  (unregistered dirs exist); plain `git status` is blind to `/archive/` payloads via the shared
  info/exclude — always `--ignored --untracked-files=all --ignore-submodules=none`.
- Deletion-class discipline: preserve-verify-then-remove; per-item hash manifests; three-gate
  force only; STOP thresholds that convert surprises into analysis rather than pushing through.
- git worktree remove without --force does NOT protect gitignored content — guard explicitly.
- CRLF phantom diffs: classify via `git diff --numstat` (empty = line-ending only), not status
  letters.
- IPC mechanics: run the handoff wrapper from the repo cwd (silent no-op otherwise); verify
  pickup by grepping the thread rollout for the lane-source filename; dead turns = frozen
  rollout + no pending call → idempotent nudge + materialization check; never send while
  genuinely mid-turn.
- Records: each surface has its OWN update convention (insert-before-trailer, prepend-refresh,
  per-lane extension tables, D26 supersession notes) — adjudicate the convention before
  editing; extension-only has one exception class: a supersession sentence is mandatory when
  an old note would otherwise read as currently-true-but-false.
- Estimates: never extrapolate sizes from tiny samples (45GB estimate vs 246GB reality).
- Encodings: PowerShell-authored JSON is utf-8-sig; hash on-disk bytes, never in-memory strings.

## 5. Current state snapshot (as of last update — post-#2453)

- main: `254e2f81`; zero open PRs; CI green on tip (PR + post-merge push runs).
- Worktrees: ZERO repo-local registered entries under `worktrees/`; 12 unregistered dirs held
  (7 onlook re-held on persistent tar timeouts + 5 newly-held: cb-live-server-scan,
  wb-compare-prep, mainline-lane, pr83-audit, w3); external/owner-keyed + .cursor registrations
  untouched by design; /tmp/audit-wt/p6main still locked (owner). Footprint 82.1GB (from ~246GB
  at campaign start; per-round reclaim figures use different measurement methods — do not sum
  naively across methods).
- Archives (owner-durable under C:/p6store): inbox-archive/2026-07-06 (42cd507b…),
  inbox-archive/2026-07-06-adj (9291ee34…), worktree-preserve-archive/2026-07-06 — aggregate
  NOW 1ae49356… (44 manifests / 32 verified / 12 failed-held; prior b45fcb61… superseded,
  recoverable via #2452 record). Evidence artifacts: adjudication 0c87d88f…, deep-dive
  03f50a85…, disposition-plan-v2 ca5b0630….
- Tracked record surfaces current through #2453 (every round verified; conventions adjudicated).
- PR arc this campaign: #2445 #2446 #2447 #2448 #2449 #2450 #2451 #2452 #2453 — all merged,
  all independently verified, zero rollbacks, zero data loss, all safety stops honored.
- Hardware/disk: no rail violations in any lane; C: free grew correspondingly.

## 6. Forward plan (each item: scope, gate, why-this-shape)

1. DONE (was: P2 completion) — see §3.14. Residual from it: the 12 held dirs. The 7 onlook
   holds fail on tar-create timeouts even selectively; the graceful next options, in preference
   order: (a) leave held — content is intact on disk, nested-clone bundles + patch archives
   already preserve the git-valuable material, so the loose residue is low-value; (b) an owner
   session runs the tars WITHOUT bounds (interactive patience) or after pausing OneDrive; (c)
   accept recorded duplicate-pointers for the known-duplicated loose files and delete. The 5
   newly-held dirs carry per-item hold reasons in the manifest — review when convenient.
   Recommendation: (a) now; fold (b/c) into any future owner disk pass. Why: zero-loss beats
   marginal disk gain; the campaign's storage objective is already achieved (246→82GB).
2. OWNER-ONLY queue (unchanged in nature; all recorded on main):
   a. Onlook upstream contribution — content preserved in bundles + on-main patch archives;
      pushing is identity-bearing on a third-party repo. Recommendation when taken up: fresh
      re-derivation from the patch archives against current upstream, not a raw push of stale
      branches.
   b. Mass remote-branch deletion (~1,726 codex/* refs) — cosmetic; PR refs preserve heads;
      recommend a batched GraphQL classification (merged-PR-backed only) if/when authorized.
   c. `/tmp/audit-wt/p6main` locked registration — needs owner unlock; placement violation
      recorded; nothing depends on it.
   d. A8 O3 real-data controlled reveal + P4/P5 — the SEC-XBRL program's own gates; out of this
      campaign's scope by design (this campaign deliberately touched no runtime posture).
3. Deferred-optional (agent-executable when convenient; low value-density, so batched):
   banner backfill for ~22 pre-convention lane sources; evidence-registry dating smell (base
   "Counts worth remembering" section lacks the dated-extension convention — either date it
   retroactively or add a see-current-pointers banner); v2→v3 adjudication schema fields
   (disposition/snapshot_dest/sweep_precondition/verification as structured fields — spec
   already written into the v2 plan's §4 lessons).
4. Sibling repo (observatory): unchanged this campaign; its frontier (INC-09 chunk pick,
   INC-06 CAP-007 doc) awaits owner steer in ITS OWN session context — cross-repo work from
   this session was deliberately avoided (different memory/authority context).
5. This dossier: on P2 closeout, update §3.14→outcome + §5 snapshot; include in the next I12
   archive refresh; OPTIONAL owner decision — land it as a tracked doc (it is leak-clean and
   repo-relative by construction; landing would put the campaign synthesis under the same
   durability as the program record; cost = one Tier-1 docs lane).

## 7. Risk register (residual, post-campaign)

| Risk | Current posture | Residual owner action |
|---|---|---|
| Storage regrowth | ~164GB freed campaign-total (246→82GB); lesson-encoded gates standing | none (watch) |
| Held dirs (12) | Fail-closed; content intact; git-valuable material already bundled/archived; per-item reasons in manifest | optional (see §6.1) |
| Governance durability | I12 protocol + 3 archives + D29/D30 tracked; 17A containment obligation CLOSED | keep I12 cadence |
| Zip determinism class | Fail-closed guard on build path, CI-exercised | none |
| Coordination substrate (inbox) mutability | Archives at each record-lane closeout; [From Claude] precedent set | none |
| Onlook proof provenance | Already unreproducible (predates campaign); canonical-remnant material inside held dir (intact) | decide re-proof vs remnant tar |
| OneDrive sync hazards | All value/evidence material relocated to C:/p6store; nested .git population mostly bundled+removed | none |

## 8. Maintenance protocol for this dossier

Update triggers: any lane closeout, any owner decision, any correction to a claim herein.
Update style: dated, additive where history matters; §5/§6/§7 are current-state sections and
may be rewritten in place (they are snapshots, not ledgers). Every factual claim keeps its
anchor (PR/SHA/hash). At each I12 archive refresh, this file rides along; its own sha256 gets
recorded in the closeout that triggered the refresh.
