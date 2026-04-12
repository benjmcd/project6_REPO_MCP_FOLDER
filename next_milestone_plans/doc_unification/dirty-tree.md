# Dirty Tree

## Current working-tree state

The root checkout is dirty on top of `551b8ecd`.

Important tracked MVVLC doc modifications include:

- `00A`
- `00B`
- `00C`
- `00F`
- `00T`
- `00V`
- `03J`
- `03L`
- `03N`
- `03Q`
- `03S`
- `03T`
- `05D`
- `06C`
- `06D`
- `06E`
- `MANIFEST.json`
- `README_INDEX.md`
- `VERIFIER_FRONT_DOOR.txt`
- `VERIFIER_TEMP_DUMP.txt`
- roadmap assets

This list is only a sample.
Current `git status` shows the dirty state now spans most of the MVVLC pack, including a large portion of the `00*`, `03*`, and `06*` series plus front-door, verifier, manifest, and roadmap files.

Important untracked planning additions include:

- `.codesight/`
- `next_milestone_plans/pageevidence/`
- `next_milestone_plans/candidate_b_workbench/`
- MVVLC files `03AA` through `05Q`

## Why this matters

The current overclaim problem is not only a branch-history issue.
It is also a dirty-tree issue.

Examples found during the audit before the source-doc cleanup pass:

- `00F` said the focused workspace root "now contains" `review_nrc_aps_runtime_roots.py`, `review_nrc_aps_runtime_db.py`, and `backend/tests/test_review_nrc_aps_runtime_db.py`, even though those are absent from the root checkout.
- `06C` said the canonical repo-root pytest posture was live-verified for T1-T8 in this clean worktree, which is false for the root checkout.
- `06D` and `06E` claimed grouped T7/T8 green status and runtime-fixture/runtime-DB test closure that the current root checkout does not reproduce.
- `README_INDEX.md` narrated merged-main M5/M6A/M6B/05P/05Q closure as the pack front door of the root checkout, without a strong enough separation between merged-main authority and current root materialization.
- `00T`, `00V`, and `03J` depended on the same closure posture, so they amplified the overclaim even though they are derivative docs rather than the primary fact surface.
- `00A`, `00B`, and `00C` operationalized the same expanded closure chain for navigation, audit, and implementation preparation, which made the dirty overclaim easier to act on.
- `VERIFIER_FRONT_DOOR.txt` and `VERIFIER_TEMP_DUMP.txt` mirrored the same closure chain and could be misread as independent corroboration even though they are derivative artifacts.
- the untracked local `.codesight` bundle could also be misread as authority even though it is navigation metadata; it currently repeats a stale document-trace `visual-artifacts` route in `routes.md`, `CODESIGHT.md`, `coverage.md`, and `report.html`
- untracked `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md` records `142 passed` and `111 passed` clean-worktree validation results that are not currently reproducible in any active checked-out authority surface here.

Remediation status:

- the primary source-doc overclaim lines above were patched in this pass so the root planning tree now reads as a separate root-local planning branch
- the dirty-tree problem still remains because the working tree is still broad, the pack still depends on untracked additions, and the T8 fixture-authority gap is still unresolved

## Pack inventory integrity

`MANIFEST.json` is intentionally scoped through the `contains` array and behaves like a core-pack inventory, not a complete directory dump.

Current manifest facts:

- declared core files: 75
- actual files in the directory: 85
- no declared file is missing
- 10 present files are undeclared:
  - `99_CLAUDE_CODE_AUDIT_NOTES_AND_RECOMMENDATIONS.md`
  - `claude_code_hardening_task.txt`
  - `multi_variant_visual_lane_control_archived_files_firstset_outdated.zip`
  - `multi_variant_visual_lane_control_archived_files_unkownbutafterfirstset_outdated.zip`
  - `mvvlc_controlled_implementation_prompt.txt`
  - `mvvlc_milestone_roadmap.png`
  - `mvvlc_milestone_roadmap_notes.md`
  - `mvvlc_reconciliation_checklist_v6.md`
  - `VERIFIER_FRONT_DOOR.txt`
  - `VERIFIER_TEMP_DUMP.txt`

Assessment:

- This looks intentionally scoped rather than strictly exhaustive.
- That said, the excluded verifier and audit artifacts are still being edited and consulted, so they materially affect user interpretation even if they are outside the manifest core.

## Root pack now references untracked files as active content

The dirty root `README_INDEX.md` and dirty `MANIFEST.json` treat many later MVVLC docs as active pack files:

- `03Y`
- `03Z`
- `03AA`
- `03AB`
- `03AC`
- `05E`
- `05F`
- `05G`
- `05H`
- `05I`
- `05J`
- `05K`
- `05L`
- `05M`
- `05N`
- `05O`
- `05P`
- `05Q`

Those files currently exist in the working tree, but they are untracked in the root git index.

Implication:

- The current root planning pack is not reproducible from committed branch state alone.
- The front door and manifest are currently narrating a pack that depends on untracked local files.
- The navigation, audit, implementation, and verifier mirror docs then propagate that same expanded pack as if it were already settled current authority.

## Initial missing audited runtime fixture as a separate dirty-state problem

At the time of the initial dirty-state audit, the dirty docs told a stronger story than the active filesystem supported:

- `00F:69-72`, `03L:37-40`, `06C:145-146`, `06D:60`, and `06E:29` all imply that clean-worktree review/runtime validation can auto-align to a shared audited `lc_e2e` root.
- At that time, neither the root checkout nor `worktrees/pageevidence-main-merge` nor `worktrees/nrc-aps-runtime-next` contained a passing local `backend/app/storage_test_runtime/lc_e2e` corpus.
- The only discovered `local_corpus_e2e_summary.json` / `lc.db` pairs lived under hidden `.claude/worktrees/*` directories and archived snapshots.

Implication at that time:

- current T8 closure claims were not just "wrong for root";
- they were not reproducible on any active checked-out authority surface in the repo state at that point in the audit.

Later correction:

- later workspace-local reruns on the root-local branch used an adopted `backend/app/storage_test_runtime/lc_e2e/20260327_062011` runtime and produced a green grouped T8 review/runtime result
- `worktrees/pageevidence-main-merge` later also passed its full review/runtime T8 bundle against that same workspace-local runtime
- `worktrees/nrc-aps-runtime-next` later also passed its full review/runtime T8 bundle against that same workspace-local runtime, so the earlier dirty-state claim is preserved here as historical audit evidence only; the committed `main` tree does not itself carry that runtime directory

## Root `pageevidence` and `candidate_b_workbench` directories

Both directories currently exist in root, but neither is tracked in the root git index.

This is a separate unification problem:

- root readers can see and rely on those packs
- git-tracked root history does not actually carry them
- those root copies also drift from the worktree copies under `worktrees/pageevidence-main-merge`

## Dirty-tree proceed assessment

Do not treat the current dirty root planning tree as a stable authority surface.

Before more implementation or more planning closure claims:

1. separate committed branch truth from dirty-tree local edits
2. decide whether the root pack is meant to mirror merged-main authority or remain a root-local planning branch
3. stop using current dirty README/00F/06C/06D/06E text as if it were already proven by the root checkout
4. stop using the current dirty review/runtime closure language as if the audited `lc_e2e` fixture corpus were present in active root/worktree authority surfaces
