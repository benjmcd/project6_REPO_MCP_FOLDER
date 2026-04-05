# 03M Selector Activation Scope and Lifetime Policy

## Purpose

Freeze the activation semantics of any future selector before code begins.

## Why this doc exists

A second-opinion critique correctly pointed out that selector introduction is under-specified unless the following are made explicit:

- how a variant is activated,
- where that activation enters the system,
- how long it lasts,
- and how it propagates across nested processing paths.

## Current policy

### Allowed design target
Selector activation must be **request-scoped or run-scoped**, not global-by-default.

### Not allowed as the primary control surface
- a hidden global mutable toggle
- a process-wide default change without explicit per-run context
- an env-only primary selector

## Required freeze questions

1. Is activation carried through processing config?
2. Is activation visible at the artifact-ingestion adapter layer?
3. How is activation propagated for ZIP member recursion?
4. How is activation propagated for connector-initiated runs?
5. Does activation survive only one call, one run, or a larger process lifetime?

## Baseline-first implication

In the first integrated pass:
- baseline must be the only effective normal-runtime activation,
- non-baseline activation must remain unavailable in ordinary integrated runtime.

## Important restraint

This doc does **not** freeze a specific config key such as `variant`.
That remains a candidate, not a settled implementation fact.
