# 00D Multi-Variant Program Decision

## Decision

Adopt a **hybrid multi-variant program**:

- one frozen baseline,
- three experimental worktree/branch tracks,
- one bounded in-repo selector seam,
- baseline-only integration first,
- later admission of one approved experimental variant at a time.

## Refined program interpretation

The selector introduction problem is now explicitly understood along **three separate control dimensions**:

1. **Activation mechanism**
   - how a variant is selected,
   - where that selection enters the system,
   - how long it lives.

2. **Boundary definition**
   - exactly which part of PDF processing is swappable,
   - especially at the OCR/visual edge.

3. **Isolation mechanism**
   - how experiments avoid contaminating baseline runtime, review, diagnostics, and artifact surfaces.

These must all be frozen before code begins.

## Hard rules

1. Baseline remains default.
2. First selector scope is PDF visual-lane only.
3. First integrated selector pass is baseline-only.
4. A/B/C remain worktree-only initially.
5. No integrated rollout with baseline + A + B + C at once.
6. Replay/promotion/review/report/export remain baseline-only initially.
7. Variant identity remains internal-only initially.
8. Experimental variants must not collide with baseline `lc_e2e` discovery.
9. Diagnostics-ref persistence semantics remain baseline-locked in pass 1.
10. Runtime DB binding/discovery semantics remain baseline-locked in pass 1.
11. Activation mechanism must be per-run/request scoped, not global-by-default.
12. Promotion requires explicit baseline comparison and approval.
