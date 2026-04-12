# Doc Unification Audit

## Scope

This folder records the current audit of planning-doc authority, unification, and validation posture across:

- `next_milestone_plans/multi_variant_visual_lane_control`
- `next_milestone_plans/pageevidence`
- `next_milestone_plans/candidate_b_workbench`
- `worktrees/pageevidence-main-merge`

## Canonical authority split

There are two distinct authority layers and they must not be blended:

1. Root planning and control authority lives in the root checkout under `next_milestone_plans/...`.
2. Newer live runtime-binding, runtime-DB, PageEvidence-admission, and Candidate B proof implementation authority lives in `worktrees/pageevidence-main-merge`.

The main doc-unification problem is authority drift between those two layers.

## Git anchor used in this audit

- Freeze commit: `56c4147c` (`Freeze MVVLC baseline planning pack`)
- Current root `HEAD`: `551b8ecd` (`docs(mvvlc): align planning pack with root-live review surfaces`)
- Important current-state caveat: the root checkout is dirty beyond `551b8ecd`, including tracked MVVLC doc edits and many untracked planning files/directories.

## What each file in this folder covers

- `freeze-delta.md`
  Committed branch delta from `56c4147c` to `551b8ecd`.
- `dirty-tree.md`
  Uncommitted tracked and untracked drift on top of `551b8ecd`.
- `test-evidence.md`
  Current execution evidence from root and merged-main validation runs.
- `mvvlc-pack.md`
  Exact MVVLC doc inconsistencies, contradictions, and overclaims with file and line anchors.
- `secondary-packs.md`
  PageEvidence and Candidate B root-vs-worktree drift and alignment findings.

## High-level conclusion

The earlier audit conclusion still broadly stands, but it needed one important correction:

- The committed branch delta from `56c4147c` to `551b8ecd` mostly moved the MVVLC pack toward the older root-live review surface.
- The strongest overclaims currently visible in the root docs are not all in `HEAD`; many were introduced by uncommitted local edits on top of `551b8ecd`.
- The earlier note that merged-main was fully green through T8 was too strong, but the later note that no active checked-out authority surface could reproduce T8 is now superseded for the root-local branch, for `worktrees/pageevidence-main-merge`, and for `worktrees/nrc-aps-runtime-next`.
- The focused T8 follow-up found one viable surviving single-run golden fixture under hidden `.claude` worktrees. In this pass that fixture was adopted into the active root at `backend/app/storage_test_runtime/lc_e2e/20260327_062011`, a root-local `backend/tests/review_nrc_aps_runtime_fixture.py` helper was added, and the stale hardcoded root review tests were switched to shared runtime discovery.
- Current direct execution evidence now shows the full root grouped T8 bundle passing (`76 passed`) against that adopted root-local runtime.
- The live owner-path worktree `worktrees/pageevidence-main-merge` is now also green on the full review/runtime T8 bundle (`137 passed, 3 skipped`) against that adopted root-local runtime after replacing stale hardcoded representative run pins in `backend/tests/test_review_nrc_aps_document_trace_api.py` with dynamic runtime-derived representative target selection and conditional cross-runtime comparison coverage.
- The remaining noncanonical validation surface `worktrees/nrc-aps-runtime-next` is now also directly revalidated green on the full review/runtime T8 bundle (`105 passed, 1 skipped`) against that same adopted root-local runtime. No code edits were required there; its narrower helper now resolves the restored root-local runtime successfully because the adopted fixture's summary points at live root-local DB and storage paths.
- Root T8 drift was not limited to tests. In the same repair pass, root `backend/.env` was aligned to the adopted `20260327_062011` runtime DB so the legacy review surfaces and direct config path now agree; that alignment should still be read narrowly as T8 review-surface restoration, not as blanket config normalization across every runtime consumer.
- The tracked `lc_e2e` corpus commit found during the audit (`fc17d05c`, `20260329_151235`) is not on the current root branch lineage here. `git branch --contains fc17d05c` returns only `feature/enhanced-extraction-pipeline-v3`, and `git merge-base HEAD fc17d05c` reported no merge base in this local repo state.
- The retained `frontend_UI_plans` folder also carried stale runtime-authority wording. Earlier in this audit its review-UI and document-trace docs cited `20260327_062011` and `20260328_150207` as current or verified fixtures even though neither runtime was then present in the current root checkout. After the root-local T8 repair, `20260327_062011` is now the adopted current root-local runtime while `20260328_150207` remains historical/absent, and the retained UI docs were updated to reflect that split.
- The retained `frontend_UI_plans` folder was also under-specified on live module and route inventory. Its README did not enumerate the full live review/document-trace authority surface, and the retained document-trace data contract still described `downstream-usage` as a concrete endpoint even though current live root implementation only ships an unavailable manifest-tab placeholder with no route.
- Repo orientation aids also remain imperfect. `./.codesight/wiki/index.md` is still absent even though repo guidance points readers to it first, and the untracked local `.codesight` metadata bundle repeats a stale document-trace `visual-artifacts` route in `routes.md`, `CODESIGHT.md`, `coverage.md`, and `report.html` even though the live root `backend/app/api/review_nrc_aps.py` does not implement that route. Those `.codesight` files were treated as navigation aids only, not implementation authority.
- The authority-drift problem is also being amplified by derivative operational docs (`00A`, `00B`, `00C`) and verifier mirror artifacts (`VERIFIER_FRONT_DOOR.txt`, `VERIFIER_TEMP_DUMP.txt`) that route readers back into the same unsupported closure chain.
- The root `pageevidence` and `candidate_b_workbench` packs are not just root-vs-worktree drifts; they are also not fully unified with each other about whether PageEvidence is an active lane or an adopted hold-state lane.

## Source-doc cleanup applied in this pass

The root planning tree has now been explicitly reframed as a separate root-local planning branch in the primary MVVLC front-door/control files and verifier mirrors.

Patched source-doc set in this pass:

- `README_INDEX.md`
- `00A`
- `00B`
- `00C`
- `00F`
- `06C`
- `06D`
- `06E`
- `03J`
- `03L`
- `00T`
- `00V`
- `VERIFIER_FRONT_DOOR.txt`
- `VERIFIER_TEMP_DUMP.txt`
- root `pageevidence` front-door/separation docs
- root `candidate_b_workbench` front-door/authority docs

Those source docs now distinguish:

- current root-local planning branch state
- imported merged-main implementation authority
- historical/imported validation records
- active-worktree validation state, which must still be checked per worktree rather than inferred from root-local repair alone

The remaining concerns are no longer the same exact front-door overclaim lines that were found earlier in the pass. The remaining concerns are the broad dirty-tree state, untracked pack expansion, and validation separation for worktrees that have not yet been explicitly rerun outside the now-repaired root-local, `pageevidence-main-merge`, and `nrc-aps-runtime-next` T8 surfaces.

Remaining intentional merged-main wording:

- a few docs such as `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md` and `mvvlc_milestone_roadmap_notes.md` still say that merged `main` contains specific decisions or closure states
- those are intentional record-level or roadmap-level merged-main references, not current root-checkout execution claims

That means there are two different problems:

1. `HEAD` is already behind merged-main implementation authority.
2. The dirty working tree then widens and overclaims further, often narrating merged-main materialization as if it exists and passes in the current root checkout.
3. The review/runtime validation story had a separate fixture-authority gap. That gap is now resolved on the root-local branch, on `worktrees/pageevidence-main-merge`, and on `worktrees/nrc-aps-runtime-next` through the adopted `20260327_062011` runtime, shared or compatible runtime discovery, and dynamic representative target selection where needed. Separate active worktrees still require their own explicit executable revalidation.

## Proceed rule

Do not treat the current root planning surface as unified or fully reliable until both of these are separated explicitly:

- committed root branch state
- uncommitted local planning edits

And do not treat merged-main passing bundles as proof that the current root checkout is green.
