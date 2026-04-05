# 00S Narrowing Stop Rule and Recommendation

## Purpose

State clearly whether the narrowing pass should continue.

## Current state

The control pack already has strong direct evidence for:

- direct processing chain
- review/catalog/API visibility
- report/export/package visibility
- diagnostics/runtime DB baseline locks
- selector key and propagation path
- exact visual-preservation seam freeze
- acceptance command convention
- local performance gate definition
- visual output surface mapping
- migration support for `visual_page_refs_json`
- non-app live-surface checks
- archive/worktree duplication characterization

## Remaining residuals

1. Python acceptance path is pack-specified but not visibly repo-enforced in the checked root workflow/hook/config surfaces.
2. Bounded uncertainty remains in duplicated archive/worktree state and other non-audited/generated surfaces.

## Stop rule

Do **not** continue narrowing by default when all of the following are true:

1. remaining items are already explicitly stated as bounded residuals,
2. additional checks are increasingly likely to examine duplicated or generated state rather than active control surfaces,
3. the next useful work would be implementation/enforcement, not more classification.

## Continue only if one of these is true

### Case A — You want repo-native enforcement, not just pack-defined convention
Then the next work is not more narrowing prose.
It is verifying or adding:
- Python CI workflow
- repo-native runner/hook enforcement

### Case B — You want exhaustive closure over duplicated/non-audited surfaces
Then the next work is a deliberate exhaustive audit of:
- worktrees
- archive
- generated/helper surfaces

That is a different scope, with lower expected marginal value.

## Recommendation

**Stop narrowing now unless you explicitly want one of those two higher-cost scopes.**

The current residual uncertainty is already small, honest, and well-bounded enough for planning and controlled implementation.
