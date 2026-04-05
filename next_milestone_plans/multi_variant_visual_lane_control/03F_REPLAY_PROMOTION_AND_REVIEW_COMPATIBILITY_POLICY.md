# 03F Replay, Promotion, and Review Compatibility Policy

## Decision

These remain baseline-only in the first integrated selector pass:

- replay
- promotion
- safeguards/governance
- evidence report/export package flows
- review/trace/runtime review flows
- live batch / validation governance flows

## Additional baseline-lock surfaces

The following also remain baseline-locked in the first integrated pass:
- diagnostics-ref persistence behavior
- runtime DB binding/discovery behavior
- default review/runtime-root discovery behavior

## Allowed non-baseline contexts initially
- worktree-local development
- controlled diagnostics
- bakeoff harnesses
- offline comparison runs
- manual experiment runs outside default review/runtime discovery

## Not allowed initially
- default automated runtime
- replay governance truth
- promotion evaluation
- report/export/review contractual outputs
- live batch governance outputs
- baseline runtime-root replacement
- baseline diagnostics-ref persistence semantics drift
- baseline runtime DB binding/discovery drift
