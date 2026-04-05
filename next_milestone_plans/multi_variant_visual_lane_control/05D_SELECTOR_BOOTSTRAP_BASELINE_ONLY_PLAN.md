# 05D Selector Bootstrap Baseline-Only Plan

## Objective

Introduce selector/registry structure without introducing experimental runtime behavior yet.

## This pass does

1. define registry shape
2. define selector config surface
3. register baseline replay implementation
4. route baseline through selector
5. keep outward behavior unchanged
6. optionally emit internal-only provenance

## This pass does not do

- no integrated A/B/C variants
- no public contract change
- no artifact change
- no report/export/review/replay/promotion change
- no widened media scope
- no deterministic replacement yet
- no default runtime-root change
- no diagnostics-ref persistence change
- no runtime DB binding/discovery change

## Preconditions

Each precondition references its governing doc(s).

1. baseline freeze complete (`00F`, `00E`)
2. consumer/invariant map complete (`00E`)
3. PDF-only selector scope frozen (`03D`)
4. variant identity visibility frozen (`03E`)
5. replay/promotion/review compatibility frozen (`03F`)
6. active test/command matrix frozen (`06C`)
7. seam checklist completed and confirmed consistent with the frozen seam specification (`03G`, `03W`)
8. selector config insertion policy frozen (`03H`)
9. runtime-root / run-namespace policy frozen (`03I`)
10. artifact-equivalence control policy frozen (`03J`)
11. diagnostics-ref persistence policy frozen (`03K`)
12. runtime DB binding/isolation policy frozen (`03L`)
13. selector activation scope/lifetime policy frozen (`03M`)
14. experiment isolation mechanism policy frozen (`03N`)
15. blocker decision table reviewed and all still-open blockers explicitly accepted or closed (`06E`)
16. exact seam boundary frozen (`03W`)

## Acceptance criteria

1. baseline remains default
2. no public behavior drift
3. no artifact-equivalence drift
4. no unrelated route regression
5. no report/export/review/replay/promotion/safeguard drift
6. non-baseline selection unavailable in normal runtime
7. baseline review/runtime discovery behavior unchanged
8. baseline diagnostics-ref persistence behavior unchanged
9. baseline runtime DB binding/discovery behavior unchanged


## Performance acceptance linkage

Before accepting selector bootstrap:
- execute the local performance gate defined in
  `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`
- or explicitly document why the local performance gate has not yet been executed, while treating the command convention itself as already frozen by `06J` and `06K`


## Seam closure after this revision

The seam boundary for first-pass selector work is now closed by
`03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`.

So bootstrap planning no longer needs to discover where the selector belongs.
It only needs to respect the frozen seam and keep all surrounding surfaces baseline-locked.
