# 03N Experiment Isolation Mechanism Policy

## Purpose

Define what “out-of-band experiments” must mean operationally.

## Why this doc exists

Earlier revisions stated that experiments should remain out-of-band, but that was still too loose.
This document freezes the required behavior. The exact M5 mechanism is now frozen separately in `03Z_EXACT_M5_BASELINE_VISIBILITY_AND_RUNTIME_ROOT_COEXISTENCE_MECHANISM.md`.

## Required isolation outcomes

Experimental runs must not silently contaminate:

1. baseline runtime-root discovery
2. baseline review/runtime API discoverability
3. baseline diagnostics-ref persistence semantics
4. baseline runtime DB binding expectations
5. baseline artifact-equivalence expectations
6. baseline report/export/review/governance flows

## Allowed initial experiment model

Experiments may run only when they use:
- explicit non-default runtime/artifact roots,
- explicit manual or bakeoff invocation paths,
- explicit comparison workflows outside default review/runtime discovery.

## Mechanism note

This document still does **not** require:
- a specific context-manager abstraction,
- a specific experiment ID field,
- a specific namespacing scheme inside persisted payloads.

The exact coexistence / visibility mechanism is now frozen by `03Z`.

## Current operational rule

If an experiment can be auto-discovered through the same baseline runtime-root/review path, then it is not isolated enough for the first integrated phase.


## Additional tightening from attached-session evidence

A useful attached-session finding is that separate runtime/artifact roots alone may still be insufficient, because baseline-facing review/catalog/report surfaces may remain able to see experiment runs through shared discovery and shared run visibility.

Therefore, in current scope, “out-of-band” must be interpreted more strictly:

An experiment is **not** sufficiently isolated if it remains visible through:
- default review/runtime discovery,
- review catalog aggregation,
- shared run/report/export lookup surfaces,
even if its raw artifact files live under a separate root.


## Additional API-facing isolation implication

Separate runtime/artifact roots are also insufficient if baseline-facing review API endpoints can still expose experiment-derived:
- diagnostics
- artifacts
- normalized text
- indexed chunks
- extracted units
- traces

So experiment isolation must be interpreted as invisibility to baseline-facing API surfaces too, not just filesystem/root separation.


## Additional verified tightening

The live repo now confirms that separate roots are not enough by themselves, because baseline-facing review/catalog/API surfaces can still expose runs and run-bound data by `run_id`.

So an experiment is **not** sufficiently isolated if it remains visible through:
- `get_runs()`
- review catalog run selectors
- pipeline-definition / overview / tree views
- node details / file details / file preview
- document selector retrieval
- document trace retrieval
- source blob retrieval
- diagnostics retrieval
- normalized text retrieval
- indexed chunk retrieval
- extracted-unit retrieval


## Additional verified tightening from report/export surfaces

Experiments are also **not** sufficiently isolated if they can still:
- resolve a shared `ConnectorRun`,
- persist report refs into `run.query_plan_json`,
- persist export refs into `run.query_plan_json`,
- persist export-package refs into `run.query_plan_json`.

So isolation must be judged against shared run-bound report/export persistence, not just runtime discovery and review APIs.
