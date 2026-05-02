# Layer 3 Analysis Method Registry Freeze

Status: historical current-methods registry governance for the initial three-method registry tranche. PR `#411` later added the separately governed `descriptive_summary` lower-level analysis API method; this document should no longer be read as a current-main claim that the registry contains only three methods.

Status: planning-only governance for the current wrapped quantitative method registry boundary.

This document freezes the smallest safe boundary for governing the existing `backend/app/services/analysis.py` method family before any method expansion. It does not implement a registry, add methods, change execution behavior, change Layer 3 workbench UI, or widen source/runtime/schema scope.

## Current Live Boundary

Current `main` has an existing quantitative analysis spine:

- `recommend_analysis(...)` recommends only the current starter methods: `cross_correlation`, `decomposition`, and `structural_break`.
- `run_analysis(...)` creates an `AnalysisRun`, dispatches through hardcoded method-name branches, and records normal `AnalysisArtifact`, `AssumptionCheck`, and `CaveatNote` rows produced by the selected method.
- `layer3_pass_entry.py` and the Layer 3 workbench execution path reuse that wrapped quantitative spine for already admitted execution slices.
- Unsupported method names are not admitted as new methods by this governance packet.

At the time of this freeze, the live repo did not expose a typed `AnalysisMethod` registry object, registry-derived OpenAPI enum, method capability catalog, DAG engine, qualitative method engine, hybrid/RAG/vector execution, or method-extension workflow. Current `main` now includes the bounded registry implementation from PR `#316` and the separately governed `descriptive_summary` lower-level method support from PR `#411`.

## Problem Statement

The existing method spine works for the current starter methods, but new quantitative methods would currently increase contract debt because method identity, parameter defaults, prerequisites, assumptions, artifacts, and provenance are scattered through code branches and prose. Before adding methods, the repo needs a current-methods-only registry contract that defines what must be true for a method to be supported.

## Slice Decision

The next safe support boundary is:

> Freeze a current-methods-only `AnalysisMethod` registry contract for the then-current `cross_correlation`, `decomposition`, and `structural_break` methods, without adding methods or changing runtime behavior from this document alone.

This is intentionally governance first. It gives future implementation work a precise target while preserving the working execution path.

## Admitted Future Implementation Scope

A later implementation PR governed by this freeze may add only:

- a small registry or registry-like metadata table in code for the three current methods
- registry-derived supported method ids for recommendation, validation, execution dispatch, and API/schema documentation where applicable
- typed method parameter metadata for the existing defaults and accepted parameters
- method prerequisite metadata for current dataset/time/numeric/profile requirements
- method output metadata for current artifact, assumption, and caveat families
- focused tests proving the registry describes existing behavior and does not add methods

## Explicit Non-Goals

This freeze does not admit:

- adding a new analysis method
- changing `run_analysis(...)` behavior by itself
- changing artifact persistence semantics
- changing `AnalysisRun`, `AnalysisArtifact`, `AssumptionCheck`, or `CaveatNote` schema
- adding a plugin framework, DAG engine, background worker, agent conductor, or LLM planner
- qualitative, hybrid, RAG, vector, local upload, local directory, or source-breadth expansion
- public/signed URL behavior, connector dispatch, destination selection, package mutation, or downstream handoff expansion
- UI changes or full mockup activation

## Required Decisions Frozen Here

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Method set | registry starts with current methods only | This avoids using governance as hidden method expansion |
| Method ids | preserve `cross_correlation`, `decomposition`, `structural_break` | These are the live method names in `analysis.py` and tests |
| Runtime posture | no behavior change from docs alone | Planning docs must not become implementation truth |
| Parameter posture | capture current accepted/default parameters | Future method additions need a comparable contract |
| Output posture | capture current artifacts, assumptions, and caveats | Provenance must remain reviewable and deterministic |
| Expansion posture | new methods require a separate governance/implementation pass | Prevents method creep and hidden source/runtime widening |

## Required Future Proof

A later implementation PR must prove:

- the registry contains exactly the current methods unless a separate method-expansion packet is merged first
- recommendation and execution still produce the current method ids
- current parameter defaults are preserved
- unsupported methods do not become silently supported
- existing analysis API tests and Layer 3 pass-entry tests still pass
- no schema/model/migration/runtime/source/UI changes are introduced unless separately governed

## Stop Conditions

Stop and return to planning if implementation requires:

- changing database schema or adding a model
- changing artifact storage shape
- adding new third-party method dependencies
- adding qualitative/hybrid/RAG/vector behavior
- broad workbench/service decomposition
- deciding product priority among new quantitative methods

## Relationship To Existing Docs

This freeze supports, but does not replace:

- `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`

It freezes only the method-governance prerequisite for future quantitative expansion.
