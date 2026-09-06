# 03 — Forward Plan

## 2026-09-04 current forward pointer

The current state and boundaries are in
[MASTER_CONTEXT](../MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).
The ordered next work is:

1. Done: this tracked documentation synchronization landed as PR #2497
   (`7d390a644330d07e1c999da7bbf0005bbf1ffafa`, 2026-09-05 UTC).
2. Done: PR #2495 (`44c3a433d39c5c676c2e1d163ab19b8e0965f6bf`) merged as
   `de693eea607fba511fb4e95f121bebaa54e82e13` and PR #2496
   (`1de3b1e291a854ef69a3d46bfa1cfd31cc240349`) merged as
   `348956f38eccac4d55e2e42857f1ad5eecbd1382` on 2026-09-06 UTC, each on an
   explicit owner decision after refreshing heads/checks/reviews. Method
   selection remains default-off.
3. Run a fresh isolated persisted real-data proof with explicit normalized-time
   and per-point lineage, accepting a valid no-break result and keeping
   stationarity/segment/overlap limits visible. The qualified local derivative
   needs no fresh download. A public-envelope proof requires an appropriate
   admitted public input. A bounded operator-local execution of this proof on
   2026-09-05 UTC (valid zero-break outcome) exists only in unpublished
   workspace records; this plan does not claim it as tracked evidence.
4. Keep armed-browser coverage, post-land nits, source-specific public proof,
   and any connector-to-intake automation as separate bounded pursuits.

The plan does not authorize a merge, acquisition, flag arm, support-matrix
expansion, schema/default/status change, or new owner decision. Items 1-2 are
complete; any tracked follow-on proof needs its own explicit scope.

Every open pursuit: status, precise residual delta, acceptance criteria (pass), fail
criteria, SHOULD-NOTs, gates, size/risk, sequencing. Criteria derive from the M-FWD3-CRITERIA
report as verified/adjudicated, grounded in repo authorities (merge-gate
policy, admission runbook, A8 docs, support matrix). Nothing here is authorized by this
document — it specifies what authorization would require.

## 2026-07-13 Current Admission-Spine Refresh (M-ADMISSION-SPINE-B1-RECORD)

Supersession boundary: this block is the current admission-spine pointer through
PR #2476 / `56c56e77ebe435c3a9f035f47de2d8611efee7d7`. It supersedes older
current-frontier and open-owner-queue wording only where those blocks still
describe the enumeration or precedence rule as unresolved. Historical refreshes
and every F/P section remain prior context where not explicitly superseded.

### Current B1 record and next gate

- Source frontier: #2473 /
  `cdc832d9cbfba5b0485ed0cca0c2a79854605044`, #2474 /
  `2b7973d72e65661acc30c3ec88791fe1c88061e0`, #2475 /
  `4439b1de50d85b2bc72bd92fa8e54717b7e9d500`, and #2476 /
  `56c56e77ebe435c3a9f035f47de2d8611efee7d7` are merged in order.
- B1a: bounded pass and CL-6 closure are operator-held evidence, recorded by
  hash/byte anchors in `04-evidence-registry.md`. This is not integrated-loop
  proof, analytical-utility proof, Phase 4/5/6 completion, production
  readiness, or B1b implementation.
- Owner frontier: the complete 58-disposition enumeration is
  `RATIFIED-EXACTLY-AS-PROPOSED`; precedence is
  `RATIFIED-AS-PROPOSED`. Remove both from the open owner queue. The only
  remaining B1b packet gate is the explicit second key.
- Second-key posture: `NOT-GRANTED`; future intent
  `INTENDED-NON-AUTHORIZING`; `WITHHELD` is `NOT-CLAIMED`. The next posture is
  `explicit_second_key_owner_gate`, not a build lane.
- Exact standing:
  `B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`
- Authority boundary: implementation, schema, ORM, migration, runtime, build
  dispatch, B1b build PR, and B1b build merge remain not authorized.

### Progress-surface fence widened for this records lane

The earlier M-ADMISSION-MAP progress-surface exclusion is superseded only for
this authorized records-alignment lane; the orchestrated scope audit derived its
complete ten-file write fence as:

1. `docs/MASTER_CONTEXT.md`
2. `docs/program-context/00-posture-and-invariants.md`
3. `docs/program-context/01-arc-ledger.md`
4. `docs/program-context/02-decision-record.md`
5. `docs/program-context/03-forward-plan.md`
6. `docs/program-context/04-evidence-registry.md`
7. `next_milestone_plans/Layer3_planning_docs/1366-source-artifact-admission-map.md`
8. `next_milestone_plans/layer3_progress_manifest.json`
9. `next_milestone_plans/layer3_workbench_proof_manifest.json`
10. `next_milestone_plans/layer3_progress_board.md`

`docs/program-context/INDEX.md` remains an intentional exclusion: its static
exhaustive inventory, reading order, authority order, and maintenance
conventions do not change. This records lane grants none of the implementation
authority withheld above.

## 2026-07-08 Forward Program Refresh (M-ADMISSION-MAP)

Supersession boundary: this block is the current admission-spine program pointer. It supersedes older program-frontier planning only for the local-depth source-artifact admission-spine program selection and the Phase 0-7 sequencing recorded here. Historical F-sections and prior refresh blocks remain prior context where not explicitly superseded.

### F10 - admission spine: PHASE 0+1 CONTRACT, PHASE 2-7 PROGRAM SEQUENCE

- Current pointer: `next_milestone_plans/Layer3_planning_docs/1366-source-artifact-admission-map.md`
  is the Phase 0+1 source-artifact admission-map contract and the durable
  program sequence for this lane.
- Phase 2: add a neutral NRC APS facade with behavior-neutral pinning coverage.
- Phase 3: run the ScienceBase direct-envelope pilot as Tier-2 because
  `L3SourceIntakeRecord` CheckConstraints force a migration.
- Phase 4: run shape pilots for World Bank, BLS v1, OECD SDMX, CFTC COT, and
  optional Senate LDA, each relinquishing connector-owned downstream
  admission state.
- Phase 5: reconstruct proofs by claimed posture; Phase 6 proves one named
  operator workflow through 3C/package-handoff; Phase 7 lands a static/CI
  guard with the first pilot, not after the program is over.
- Progress manifest/board artifacts are intentionally unchanged by this
  Phase-1 five-file fence; `tools/l3-progress-check.py` remains the guard for
  this docs-only publication. A later lane must widen the fence explicitly if
  those progress surfaces become part of admission-spine publication.

2026-07-09 D26 supersession: this admission-spine pointer is closed through the
executed Phase 2, Phase 3, and Phase 7 landings. Phase 2 is EXECUTED in PR #2471
/ `e413d2df7cf0adeda2fd538bc4a3a2f87a5cfcc2` as the neutral NRC APS facade with
behavior-neutral routing. Phase 3 is EXECUTED in PR #2472 /
`e31f5ebd5dcc0ae7820252d04cf47db4946d6743` as the ScienceBase/MCS connector
source-intake Gate-B envelope. Phase 7 is EXECUTED in PR #2472 /
`e31f5ebd5dcc0ae7820252d04cf47db4946d6743` as the static/CI guard for the first
pilot. Phase 4 shape pilots, Phase 5 proof reconstruction, and Phase 6 one
named operator workflow proof remain future or residual unless superseded by a
newer live-main authority.

Progress-surface boundary: `next_milestone_plans/layer3_progress_manifest.json`,
`next_milestone_plans/layer3_workbench_proof_manifest.json`, and
`next_milestone_plans/layer3_progress_board.md` remain intentionally unchanged
under this exact docs fence. This block is a program-context supersession
pointer, not a dashboard or manifest update; any later lane that promotes this
admission-spine closure into those surfaces must widen the file fence
explicitly.

## 2026-07-08 Forward Program Refresh (M-PROGRAM-SYNC)

Supersession boundary: this block is the current connector-breadth pointer. It
supersedes older connector-breadth planning only for the executed Wave 1-6
public-connector program, the IMF grant outcome, and the remaining connector
forks recorded here. Historical F-sections remain prior context where not
explicitly superseded.

### F9 - connector breadth: EXECUTED PROGRAM, REMAINING FORKS

- Status: EXECUTED and closed for the safe anonymous connector set. The durable
  execution record is `docs/campaign-records/2026-07-08-connector-program.md`:
  World Bank, CFTC COT, USGS MCS, BLS v1, and OECD SDMX landed; World Bank
  polish landed; support-matrix capability count moved 29 -> 32; FAO/BTS
  remain defer-final.
- IMF fork: the owner-granted DataMapper envelope pin was exercised on
  2026-07-08 and stopped on `GET 1/4` HTTP 403, with zero contingency spent and
  no build. Remaining owner choices are exactly: keep IMF deferred-final, or
  provide a manual browser-captured envelope sufficient for a zero-egress
  rebuild. Automated WAF workarounds, broader probing, SDMX/portal paths, and
  account-gated exploration remain refused.
- Per-connector live-pilot grants: the connector-program record's D27 sketch
  table is only a forward gate. Any live pilot still needs a separate named
  owner grant with host class, request budget, fixture model, and STOP rules.
- Defer-candidate from WB landing review: a netblock/socket-block CI-invariant
  plugin remains a small Tier-1 candidate, derived from the World Bank landing
  adversarial review and not required for the already landed connector slices.
- OD-6 analytics-method lane: tracked by the source-candidates record as the
  separate local-depth direction; it is not bundled with connector breadth.
- FAO and BTS: remain defer-final until source-owned host/auth/rate and terms
  conditions are pinned enough to create a bounded build mandate.

## 2026-07-07 Forward Program Refresh (M-RELEASE-GATE-F5)

Supersession boundary: this block is the current F5 pointer. It supersedes the
older F5 release-gate planning sections only for the live branch-protection
state, release-gate aggregate membership, orphan workflow disposition, and the
scoped item-3 adjudication recorded here. Historical F5 sections remain prior
context, not current authority.

### F5 - release-gate hardening and orphan workflow cleanup: EIGHT-FAMILY GATE RECORD

- Decision basis: under the owner's standing delegation, release-gate should
  aggregate all meaningful CI families. Live branch protection for `main` is
  active with required contexts `release-gate`, `test`, and `root-tests`;
  `strict=false`; and `enforce_admins=true`.
- True delta: adding `test` and `root-tests` to release-gate is
  coverage-coherence because both contexts are already independently
  merge-blocking. The net-new release-gate-blocking family is `nrc-aps-ocr`.
- Release-gate membership after this lane: `release-lock-install`,
  `backend-layer3-api`, `backend-coverage`, `backend-migrations-postgres`,
  `sec-xbrl-arelle-provisioning`, `root-tests`, `nrc-aps-ocr`, and `test`.
- Test guard: `backend/tests/test_ci_coverage_completeness.py` now treats
  `RELEASE_GATE_AGGREGATED_JOBS` as the enforced tuple and asserts that
  `release-gate.needs` is the exact same set, while the shell loop continues to
  check every `needs['<job>'].result`.
- Scoped-out item 3: `config/release_readiness.yaml` remains untouched. Its
  `required_gates` list is a curated profile-neutral subset, and broadening it
  would cascade into unrelated exact-equality assertions in
  `backend/tests/test_release_readiness.py` and the
  `EXPECTED_RELEASE_GATE_COVERAGE` map. Those lists are intentionally not part
  of this F5 change.
- Orphan workflow cleanup: workflow registration `286330393` (`SEC XBRL Tier-2
  review gate`) was active while its workflow file was absent on `main`. This
  lane disables, but does not delete, the registration. Re-enable is the exact
  inverse GitHub workflow enable action.
- Acceptance evidence pointers: the lane closes only after its PR's own CI run
  proves the eight-dependency release-gate wiring, the targeted local pytest
  slice remains green, the orphan workflow re-query reports `disabled_manually`,
  review threads are resolved, and detached post-merge proof confirms the
  eight-job gate and exact-set assertion on `project6-origin/main`.

## 2026-07-06 Forward Program Refresh (M-PRESERVE-SWEEP)

Supersession boundary: this block is the current F6 pointer after the
owner-authorized preserve-then-sweep execution. It supersedes the prior protected
worktree disposition state only for the classes actually preserved and swept
here. It does not authorize mass remote branch deletion, upstream third-party
contribution work, or removal of failed-preserve / failed-loose-gate leftovers.

### F6 - Worktree cleanup: PRESERVE-SWEEP EXECUTED WITH PROTECTED HOLDS

- Status: EXECUTED for v2-dispositioned registered worktrees whose preservation
  gate passed or whose v2 class required no file copy. The lane re-hashed the v2
  plan (`ca5b06307ac2a6c3fdcdea932fae97ad49264677c82b361eb84555b9e7984afa`),
  the dirty adjudication artifact, and the unlanded deep-dive artifact before
  mutating worktree state.
- Phase-0 census: 164 registered worktrees, including 142 repo-local registered
  worktrees, plus 21 unregistered directories under `worktrees/`. The fresh
  `worktrees/` byte baseline was 172,834,879,088 bytes.
- Preserve archive: snapshot manifests were written under
  `C:/p6store/worktree-preserve-archive/2026-07-06/`. The archive aggregate is
  `PRESERVE_ARCHIVE_AGGREGATE.json` with sha256
  `b45fcb611af657ed0edd925bd13cfe6bd3edc0206b45c08b11c2897efc2539b3`.
  It includes verified durable copies of the authority artifacts and covers
  30 snapshot manifests: 20 verified and 10 failed/protected.
- Registered sweep: 142 repo-local registered worktrees were processed; 135 were
  removed by `git worktree remove`, and 3 additional deregistered residual
  directories were removed after exact path-boundary checks and verified
  snapshots. Four registered worktrees were not removed by this lane: three
  failed-preserve holds and one allowlisted concurrent/owner lane that was not
  swept here. By the post-sweep registry, that allowlisted lane was no longer
  registered outside this lane's sweep, so the current repo-local registered
  remainder is the three failed-preserve holds.
- Remaining registered local holds: `worktrees/p6xbrl` is protected because the
  widened-scope preserve gate found two expected source files absent live;
  `worktrees/candidate-b-preflight-envelope-workbench-only` and
  `worktrees/candidate-b-second-iteration-workbench-only` are protected because
  their raw-report preserve copies did not fully verify.
- Unregistered directory holds: the seven onlook unregistered directories had
  nested bundles preserved where present, but their loose top-level content did
  not complete the two-part deletion gate. They were therefore not deleted. The
  other fourteen unregistered directories found in Phase 0 remain out of this
  onlook-specific deletion class.
- Post-sweep census: 25 total registered worktrees remain. The only repo-local
  registered entries are the three failed-preserve holds above; external,
  `.cursor/**`, and the locked external temp-placement registration remain
  outside this cleanup class. The final `worktrees/` byte measurement was
  83,841,051,452 bytes, reclaiming 88,993,827,636 bytes from the Phase-0
  baseline.
- Slice4 update: the prior `analyst-insight-layer-slice4` unlanded headline is
  superseded by PR #2451 on current main. That implementation is no longer an
  unlanded worktree-preservation reason in this record.
- Remote branches and upstream work: no local branch deletion, no remote branch
  deletion, and no upstream Onlook push/PR occurred. The upstream contribution
  question remains owner-only.

#### P2 addendum - fail-closed hold remediation

- Status: P2 executed for the 10 failed/protected preserve targets and the 14
  never-adjudicated unregistered directories found by the parent census. The
  updated preserve aggregate at
  `C:/p6store/worktree-preserve-archive/2026-07-06/PRESERVE_ARCHIVE_AGGREGATE.json`
  hashes to
  `1ae49356c7154446c0e03d65812cf804c7d3a76510d40c4f221b6b42ddb2f67b`.
- Completed parent holds: `worktrees/p6xbrl`,
  `worktrees/candidate-b-preflight-envelope-workbench-only`, and
  `worktrees/candidate-b-second-iteration-workbench-only` were corrected,
  fully re-verified, and removed. The p6xbrl failure was a source-path miss
  under `17a-aapl-2024-10k/`; the candidate-b failures were missing archive
  destinations that were copied and hash-verified.
- Re-held parent holds: the seven unregistered `worktrees/onlook-*` directories
  were retried with selective loose top-level tars and 300-second bounds. Each
  hit a second tar-create timeout, so each remains held rather than forced past
  a failed preservation gate.
- Newly adjudicated unregistered directories: five empty tool-state directories
  (`p2-ops`, `p3-ops`, `sec-transforms`, `tax-cache-fix`, `tax-pins`) and four
  small preserved directories (`csb-r18`, `csb-r19`, `csb-w16`,
  `l3-snapshot-index`) passed their P2 gates and were removed.
- Newly held unregistered directories: `cb-live-server-scan` and
  `wb-compare-prep` remain held after real tar missing-path failures; `mainline-lane`,
  `pr83-audit`, and `w3` remain held as large ambiguous project snapshots, with
  `w3` carrying nested git metadata. They require a later owner decision before
  any destructive cleanup.
- P2 census: the repo-local worktree registry now has zero registered entries
  under `worktrees/`; 12 unregistered directories remain held. The final
  `worktrees/` measurement was 82,091,968,899 bytes. The aggregate now covers
  44 snapshot manifests: 32 verified and 12 failed/held.
- Unchanged owner-only questions: no branch deletion, no remote branch deletion,
  and no upstream Onlook contribution work occurred in P2.

## 2026-07-06 Forward Program Refresh (M-DIRTY-ADJUDICATION)

Supersession boundary: this block is the current F6 pointer after the
read-only dirty-class worktree adjudication. It supersedes only the protected
worktree classification and disposition plan; it does not authorize removals,
mass remote-branch deletion, external locked-registration cleanup, or deletion
of protected local work.

### F6 - Worktree cleanup: ADJUDICATED REMAINDER, OWNER-GATED EXECUTION

- Method: read-only, per-item dirty-class adjudication plus ignored-class
  review and consistency critique. Registry count stayed 163 before and after;
  zero worktrees, branches, files, or registrations were mutated.
- Evidence: `state/agent-inbox/worktree-dirty-adjudication-2026-07-06.json`,
  sha256 `0c87d88f0a6efb7bf056cbf82c12b649979b2cb522639d7db01a9a279bf2c3a0`,
  189,380 bytes, records the per-item evidence, critic corrections, and
  snapshot-first disposition plan for the 139 protected worktrees.
- I12 archive anchor: operator-local archive folder `2026-07-06-adj`
  retains the raw adjudication JSON and companion inbox/source artifacts under
  the record-lane archive policy; aggregate sha256
  `9291ee34af6c510329818488b2bfe834559308def95bd3cfdb58b537a1a392ea`
  and manifest sha256
  `170ebdcba03a4e05e1830ea5e090d54eb6036f5e330266c0eecffdbc477e3614`
  cover 41 files and 6,516,906 bytes.
- Adjusted tally: 115 `TOOL-STATE-ONLY`, 8 `SUPERSEDED`, 11
  `UNIQUE-CONTENT`, and 5 `AMBIGUOUS` after applying the two critic
  corrections.
- Critic correction: `worktrees/l3-package-life` moved from
  `UNIQUE-CONTENT` to `SUPERSEDED`; P22 runtime and both P22 docs are on main,
  while the original verdict checked a stale pre-refactor path.
- Critic correction: `worktrees/sec-family-res` moved from `UNIQUE-CONTENT` to
  `AMBIGUOUS`; the models, migration, and service concept landed under renamed
  paths, while the `.v1` schema-id variant and one doc still need owner review.
- Preserve headlines: superseded by M-PRESERVE-SWEEP and PR #2451 for
  `worktrees/analyst-insight-layer-slice4`; `worktrees/onlook-proof-settle`
  has nested repositories with four unpushed commits; `worktrees/p6xbrl` holds
  the 17A evidence bundle and `worktrees/p6xbrl17b` holds the 17B driver, both
  retained under the value-retention posture.
- Disposition: 123 of 139 protected worktrees are mechanically clearable after
  snapshot-first archives, but execution remains owner-gated. The remaining 16
  need per-item owner decisions before preserve-or-remove action.
- Unchanged gates: mass remote-branch deletion remains a separate owner-gated
  decision, and the external locked placement anomaly remains unresolved.

### Deep-dive verification addendum (same day, later)

- A later six-investigator plus two-adversarial-verifier pass extended the
  same M-DIRTY-ADJUDICATION record. Units 1 and 2 remain HOLD/owner-review,
  while Units 3, 4, 5, and 6 had completeness failures that produced 14
  corrected dispositions.
- New operational facts: seven unregistered `worktrees/onlook-*` plain
  directories are invisible to `git worktree list`, and six contain nested
  repositories with unpushed commits that were verified equivalent to
  on-main patch archives; the shared `.git/info/exclude` `/archive/` line
  hides archive payloads in every worktree from plain status enumeration;
  main's tracked onlook proof surfaces reference runtime clone `641c3a85`,
  which survives nowhere on disk, so that gate provenance is already
  unreproducible on this machine; `worktrees/p6xbrl/.lane4a/17a_driver.py`
  and `worktrees/cb-runtime-audit-p1` were reclassified as real preserved
  content/owner-decision items rather than disposable tool state.
- Execution spec pointer: `state/agent-inbox/worktree-disposition-plan-v2.md`
  names the `C:/p6store/worktree-preserve-archive/2026-07-06/` destination,
  requires `git status --porcelain --ignored --untracked-files=all
  --ignore-submodules=none` or an equivalent recursive ignored-directory hash
  inventory, serial and bounded execution, hash-gated acceptance before any
  removal, and a containment relocation obligation for the 17A bundle.
- Evidence pointer: `state/agent-inbox/worktree-unlanded-deepdive-2026-07-06.json`
  hashes to
  `03f50a85e452121ddc65af4cecf3ba8f7cf98fb6e84f1dd1c9c3398a5c46c5fd`
  at 132,716 bytes; `state/agent-inbox/worktree-disposition-plan-v2.md`
  hashes to
  `ca5b06307ac2a6c3fdcdea932fae97ad49264677c82b361eb84555b9e7984afa`
  at 8,169 bytes.
- OWNER-DECISION queue headline: sweep GO; slice-4 landing;
  `sec-family-res`; onlook canonical-remnant tar; `cb-runtime-audit-p1`;
  onlook upstream contribution.
- Count authority: this addendum supersedes the immediately preceding
  `123 of 139` mechanically clearable / `16` owner-decision tally for
  execution. Until a fresh v2 count is computed from
  `worktree-disposition-plan-v2.md`, operators must treat the six-item
  owner-decision queue above and the v2 plan as controlling, not the older
  count pair alone.

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
  evidence is in `state/agent-inbox/worktree-cleanup-exec-manifest.json`
  (sha256 `bed6ccfc908f4d321c139075bd0111f66a0a1bff44d61bd49740d49947ae630f`,
  5,172,540 bytes).
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
