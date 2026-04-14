# Secondary Packs

## Status note

This document records a historical earlier audit of root-vs-worktree drift.
It is not current authority for the shipped post-PR50 compare + Candidate B Trace baseline.
The file-level findings below should be read as historical findings from that earlier audit, not as current repo assertions.

Use current authority docs instead:

- `next_milestone_plans/pageevidence/README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
- `next_milestone_plans/candidate_b_workbench/README_CANDIDATE_B_OPENDATALOADER_PACK.md`
- `frontend_UI_plans/README.md`

## Root `pageevidence` pack

### Git authority status

- `next_milestone_plans/pageevidence/` exists in the root working tree
- it is not tracked in the root git index
- it therefore cannot currently be treated as committed root branch authority

### Root-vs-worktree drift

The root and worktree `pageevidence` directories are not identical.

Examples:

- root-only file:
  - `pageevidence_strengthening_pack_v10.zip`
- worktree-only file:
  - `pageevidence_roadmap.png`
- content drift exists across many overlapping files, including:
  - `README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
  - `EXACT_PAGE_EVIDENCE_SHARED_EVIDENCE_AND_PROJECTION_SEPARATION_BOUNDARY.md`
  - most operational and control files in that pack

### Important content drift

Root README posture:

- still reads like an active planning/control pack for the current primary lane
- still says `backend/app/services/nrc_aps_page_evidence.py` "still fuses" shared extraction, candidate identity, and projected-class logic

Other root PageEvidence docs repeat the same active-lane and fused-state framing:

- `pageevidence_v10_codex_handoff.md`
  - still says the owner file "still fuses" extraction, candidate identity, and projected-class logic
  - still tells the reader to treat the v10 pack as the active standalone PageEvidence planning/control layer and execute Passes 1-4
- `EXACT_PAGE_EVIDENCE_SHARED_EVIDENCE_AND_PROJECTION_SEPARATION_BOUNDARY.md`
  - still states that current PageEvidence fuses raw extraction with projected classification

Merged-main worktree README posture:

- treats PageEvidence as an adopted closed hold-state pack
- explicitly says current merged main already separates shared extraction from Candidate A projection inside `nrc_aps_page_evidence.py`
- explicitly says any future work requires a new freeze

Live merged-main code supports the worktree reading more than the root reading:

- `worktrees/pageevidence-main-merge/backend/app/services/nrc_aps_page_evidence.py:110-172`
- `worktrees/pageevidence-main-merge/backend/tests/test_nrc_aps_page_evidence.py:70-92`

But the worktree pack also correctly preserves the remaining caveat:

- outward artifact shape still remains candidate-shaped at `nrc_aps_page_evidence.py:225-234`

### PageEvidence assessment

The root `pageevidence` pack is not unified with the merged-main adopted pack and should not be treated as the cleaner authority copy.
Its drift is broader than one stale README; multiple root docs still frame PageEvidence as the active current lane after the merged-main pack has already moved into adopted hold-state posture.

### PageEvidence blast radius in live merged-main

The live implementation blast radius is narrower than the root planning sprawl suggests.

Owner-path code radius:

- core owner file:
  - `worktrees/pageevidence-main-merge/backend/app/services/nrc_aps_page_evidence.py`
- single processing seam:
  - `worktrees/pageevidence-main-merge/backend/app/services/nrc_aps_document_processing.py:198-236`
  - `worktrees/pageevidence-main-merge/backend/app/services/nrc_aps_document_processing.py:800-822`
- run-config admission gate:
  - `worktrees/pageevidence-main-merge/backend/app/services/connectors_nrc_adams.py:76`
  - `worktrees/pageevidence-main-merge/backend/app/services/connectors_nrc_adams.py:649-715`
- review/runtime baseline-visibility gate:
  - `worktrees/pageevidence-main-merge/backend/app/services/review_nrc_aps_runtime.py:19-39`

Validation and reporting radius:

- direct owner tests:
  - `worktrees/pageevidence-main-merge/backend/tests/test_nrc_aps_page_evidence.py`
- workbench runner tests:
  - `worktrees/pageevidence-main-merge/tests/test_nrc_aps_page_evidence_workbench.py`
- processing seam tests:
  - `worktrees/pageevidence-main-merge/tests/test_nrc_aps_document_processing.py`
- admitted run-config / review visibility tests:
  - `worktrees/pageevidence-main-merge/backend/tests/test_nrc_aps_run_config.py`
  - `worktrees/pageevidence-main-merge/backend/tests/test_review_nrc_aps_api.py`
- pinned workbench artifact:
  - `worktrees/pageevidence-main-merge/tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`

Cross-pack coupling:

- Candidate B support explicitly names PageEvidence owner/workbench files in:
  - `worktrees/pageevidence-main-merge/tests/support_nrc_aps_candidate_b_opendataloader.py:58-59`
- that is evidence/provenance coupling only, not runtime-path ownership coupling

Focused verification rerun:

- `worktrees/pageevidence-main-merge`
  - `python -m pytest ./backend/tests/test_nrc_aps_page_evidence.py ./tests/test_nrc_aps_page_evidence_workbench.py ./tests/test_nrc_aps_document_processing.py -q`
  - result: `42 passed`

Implication:

- the PageEvidence implementation area of effect is a narrow owner-path seam with a broader test/report perimeter
- the much larger current risk surface is planning/doc authority drift, not a sprawling live-code blast radius across unrelated runtime subsystems

## Root `candidate_b_workbench` pack

### Git authority status

- `next_milestone_plans/candidate_b_workbench/` exists in the root working tree
- it is not tracked in the root git index

### Root-vs-worktree drift

All overlapping files in the root and worktree Candidate B packs currently differ in content.

That includes:

- `README_CANDIDATE_B_OPENDATALOADER_PACK.md`
- `00A` through `00N`
- `03AD`
- `04A` through `04C`
- `05R`, `05S`
- `06A`, `06R`
- `08A` through `08D`
- `09A`
- `MANIFEST.json`

### Important content drift

Root Candidate B README:

- older "v6 execution-determinism hardening" framing
- narrower local workbench comparator framing
- does not present the adopted shared-main stop-and-hold baseline as the front door

Root Candidate B contract docs also preserve older execution semantics:

- `00D_CANDIDATE_B_OPENDATALOADER_CONFIG_AND_PROCESS_CONTRACT.md`
  - freezes Candidate B as a local Python-wrapper comparator
  - requires wrapper-only `opendataloader_pdf.convert(...)`
  - requires batch-first multi-file conversion and only allows splitting after full-batch failure
- `00N_CANDIDATE_B_OPENDATALOADER_EXECUTION_ENVELOPE_AND_PACKAGE_VERIFICATION.md`
  - repeats wrapper-only invocation and one-corpus-level-batch posture

Cross-pack inconsistency inside the root working tree:

- root Candidate B `00K` says the merged-main control spine already includes the adopted subordinate PageEvidence hold-state pack
- root Candidate B `00M` says the adopted PageEvidence pack under `next_milestone_plans/pageevidence/` is subordinate lane-local hold-state only
- but the visible root PageEvidence pack still presents itself as the current active planning/control lane and primary planning/implementation lane

Why this matters:

- even before comparing against live implementation, the root secondary packs are not fully unified with each other about whether PageEvidence is active or adopted/closed
- that means the root working tree can tell two different stories about the same lane depending on which pack a reader opens first

Worktree Candidate B README:

- front-doors the current adopted shared-main stop-and-hold posture
- explicitly roots Candidate B under MVVLC retained-default authority plus the PageEvidence hold-state pack
- treats any future Candidate B work as requiring a new explicit objective

### Candidate B contract drift against live implementation

Even the worktree adopted pack still has specific drifts against the actual shared-main implementation:

- `00D_CANDIDATE_B_OPENDATALOADER_CONFIG_AND_PROCESS_CONTRACT.md:18-26`
  freezes Python-wrapper-only `opendataloader_pdf.convert(...)`
- live implementation uses CLI subprocess invocation at:
  `worktrees/pageevidence-main-merge/tests/support_nrc_aps_candidate_b_opendataloader.py:569-603`

- `00D_CANDIDATE_B_OPENDATALOADER_CONFIG_AND_PROCESS_CONTRACT.md:95-108`
  freezes batch-first conversion with split fallback only after failure
- live implementation always builds one fixture per batch at:
  `worktrees/pageevidence-main-merge/tests/support_nrc_aps_candidate_b_opendataloader.py:694-705`
- adopted compare artifact confirms that one-fixture batching:
  `worktrees/pageevidence-main-merge/tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json:36-70`

- `08D_CANDIDATE_B_OPENDATALOADER_NONINTERFERENCE_PROOF_SEQUENCE.md:37-42`
  requires touched-file inventory in the proof record
- live proof serialization at:
  `worktrees/pageevidence-main-merge/tests/support_nrc_aps_candidate_b_opendataloader.py:903-977`
  does not serialize that inventory even though `git_protected_diff()` exists at lines 230-240

### Candidate B artifact provenance wrinkle inside the adopted worktree

The adopted Candidate B reports checked into `worktrees/pageevidence-main-merge/tests/reports/` are not purely worktree-local provenance artifacts.

Observed provenance fields:

- `nrc_aps_candidate_b_opendataloader_compare_report.json`
  - `repo_root` points to `worktrees/candidate-b-second-iteration-workbench-only`
  - `python_executable` points to `worktrees/candidate-b-preflight-envelope-workbench-only\\.candidate_b_preflight_venv\\Scripts\\python.exe`
  - `prior_iteration_compare_reference` also points to `worktrees/candidate-b-preflight-envelope-workbench-only`
- `nrc_aps_candidate_b_opendataloader_proof_report.json`
  - `repo_root` also points to `worktrees/candidate-b-second-iteration-workbench-only`
  - `python_executable` also points to the preflight worktree venv
- `nrc_aps_candidate_b_opendataloader_retention_manifest.json`
  - `repo_root` also points to `worktrees/candidate-b-second-iteration-workbench-only`

Additional verification:

- current `worktrees/pageevidence-main-merge` `HEAD` is `b0741aa45522dbeb79d0410c9ad7d74a2a51d8a4`
- `worktrees/candidate-b-second-iteration-workbench-only` `HEAD` is `505f859f6ead9d28c67f1bacd2bee97c8b8f9e98`
- `worktrees/candidate-b-preflight-envelope-workbench-only` `HEAD` is `9c2d52e28c639be47c04ac9633d7aad59b688502`
- the checked-in Candidate B reports embed `git_revision: 9c2d52e28c639be47c04ac9633d7aad59b688502`
- the generating script in `worktrees/pageevidence-main-merge/tests/support_nrc_aps_candidate_b_opendataloader.py:903-914` would emit `repo_root` and `git_revision` from the current worktree if the reports had been generated there

Assessment:

- the adopted Candidate B reports are imported historical proof artifacts from sibling Candidate B worktrees, not artifacts generated directly inside the current `pageevidence-main-merge` worktree
- that does not invalidate the workbench-only hold-state posture
- but it does mean the checked-in reports should be read as adopted evidence imports, not as direct proof of current-worktree-local reproducibility

### Candidate B assessment

The root Candidate B pack is not unified with the merged-main adopted pack.
The worktree adopted pack is the better authority surface, but it still contains contract drift on invocation model, batching semantics, proof-detail completeness, and report-provenance clarity.

## Combined assessment

The root `pageevidence` and `candidate_b_workbench` directories currently amplify the overall doc-unification problem:

- they are visible in the root working tree
- they are not tracked in the root git index
- they drift from their merged-main counterparts
- they are not fully unified with each other on whether PageEvidence is still active or already adopted into hold-state
- readers can easily mistake them for stable root branch authority
