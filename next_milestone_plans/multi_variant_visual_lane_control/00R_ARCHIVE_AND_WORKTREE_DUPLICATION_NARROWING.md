# 00R Archive and Worktree Duplication Narrowing

## Purpose

Narrow the remaining outside-scope uncertainty by checking whether `worktrees/` and `archive/` contain materially new visual-lane consumer categories or mainly duplicated copies of already-audited paths.

## Verified findings

### Worktrees
Direct file search for `nrc_aps_document_processing` in `worktrees/**/*.py` found many copies of:

- `backend/app/services/nrc_aps_document_processing.py`
- `tests/test_nrc_aps_document_processing.py`
- `tools/run_nrc_aps_document_processing_proof.py`
- related `handoff/...` copies

This pattern strongly indicates duplicated branch/worktree state around the same NRC APS surfaces.

### Archive
Direct file search for `nrc_aps_document_processing` in `archive/**/*.py` found many copies under:
- `archive/files_to_be_trashed/.../.claude/worktrees/...`

These are again dominated by duplicated copies of the same service/test/tool paths.

## Interpretation

The observed archive/worktree evidence does **not** currently suggest a materially new consumer category.
What it does suggest is:

- a large amount of duplicated historical/worktree state
- which can still make absolute closure claims unsafe
- but which is weaker evidence for hidden fundamentally different live consumer classes

## Revised outside-scope uncertainty

The remaining uncertainty is now best described as:

- duplicated archive/worktree state,
- other generated/non-audited surfaces,
- and future drift,

rather than:
- observed additional repo-native consumer categories outside the main audited surface.
