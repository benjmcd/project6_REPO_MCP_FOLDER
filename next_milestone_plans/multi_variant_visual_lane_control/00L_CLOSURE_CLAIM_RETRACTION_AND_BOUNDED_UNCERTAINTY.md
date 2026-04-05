# 00L Closure Claim Retraction and Bounded Uncertainty

## Purpose

Correct the strongest overclaim in v25:
that there were no remaining open items at the control-doc level.

## Why the v25 wording was too strong

The live evidence supports strong closure for the audited app-surface planning problem.
But it does **not** justify claiming that all meaningful uncertainty is gone.

Two problems remain:

### 1. Bounded-scope closure was overstated as total closure
Most of the audit work was performed against:
- `backend/app/**/*.py`
- selected active tests
- selected review/report/runtime surfaces

That is a strong planning surface, but it is still a bounded authority set.
It is not equivalent to:
- all repo surfaces
- all non-Python surfaces
- all operational enforcement surfaces
- all future drift risks

### 2. Pack-defined conventions were treated too much like repo-native guarantees
Examples:
- canonical acceptance command convention
- local performance regression gate

These are now well-specified **control-pack decisions**, but they are not the same thing as:
- repo-native CI enforcement
- repo-native benchmark harness
- repo-native script/runner guarantees

## Additional missed live surface found during re-audit

`backend/app/schemas/review_nrc_aps.py`
- `NrcApsReviewVisualArtifactItemOut.visual_page_class`

This means even after the strong earlier closure work, one more review-schema surface still needed explicit acknowledgment.
That alone is enough to show the “no remaining open items” wording was too aggressive.

## Revised closure statement

The defensible claim is:

**The control pack is materially strong and largely closed for the audited live app authority surface, but a bounded uncertainty set remains and should stay explicit.**

## Reopened bounded uncertainty set

1. **Non-audited or lightly audited surfaces**
   - non-app surfaces
   - non-Python surfaces
   - CI/enforcement surfaces
   - migration/backfill/drift surfaces not directly verified here

2. **Operational enforcement gap**
   - acceptance command convention is specified
   - performance gate is specified
   - but these remain pack-defined controls, not verified repo-native enforcement mechanisms

3. **Residual schema/contract surface drift risk**
   - the re-audit found at least one additional review-schema surface (`visual_page_class`) after the earlier “closed” claim

## What remains true

This correction does **not** undo the substantial closure work already done on:
- direct processing chain
- review/catalog/API visibility
- report/export/package visibility
- diagnostics/runtime DB baseline locks
- selector key policy
- seam freeze
- visual output surface mapping

It only corrects the final degree of certainty.


## Narrowing after direct workflow/migration audit

The bounded uncertainty is now better scoped than in v26:

- the repo does contain explicit migration support for `visual_page_refs_json`
- therefore the remaining uncertainty should not be described as generic absence of migration support
- the stronger remaining issue is the enforcement gap: the visible root workflow surface is Playwright-oriented, not visibly Python-acceptance enforcing


## Additional narrowing after enforcement-surface check

The enforcement-gap point is now stronger and more concrete than in v27:

- exactly one root workflow was found
- it is Playwright-only
- no pre-commit surface was found
- no visible pytest references were found in the checked repo-native workflow/config/hook files

So this is now a specific enforcement observation, not generic caution.


## Additional narrowing after schema/contract audit

The residual schema/contract issue is now more specific than in v28:

- broad visual-ref schema/contract coverage exists
- the narrower point is `visual_page_class`, which appears mainly in review-oriented schema/trace surfaces

So the residual risk is localized asymmetry, not broad schema/contract incompleteness.


## Additional narrowing after non-app live-surface check

The outside-scope uncertainty is now narrower than in v30:

- checked live non-app repo-native surfaces (tools/root/docs/helper scripts) do not show additional visual-lane consumers
- so the remaining uncertainty is pushed further toward archive/worktree and other non-audited/generated surfaces


## Additional narrowing after archive/worktree check

The archive/worktree portion of the remaining uncertainty is now better characterized:
- observed matches are dominated by duplicated copies of already-audited NRC APS paths
- this supports caution against absolute closure
- but it is weaker support for the existence of materially new consumer categories
