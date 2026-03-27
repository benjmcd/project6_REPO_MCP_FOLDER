# Agent Bake-Off Submission Checklist: APS Tier1 Retrieval Plane Phase1A

## 1. Purpose

Each retrieval-plane submission must satisfy this checklist so the two outputs can be compared on equal terms.

## 2. Required Submission Items

Each submission should provide all of the following.

Submission artifacts should be written into the tool's owned Phase1A output directory.

### 2.1 Change Summary

- concise implementation summary
- explicit statement of what was in scope
- explicit statement of what was intentionally not implemented

### 2.2 Changed File List

- list of existing files modified
- list of new files added
- short reason for each touched file

### 2.3 Architecture Notes

- migration-layer notes
- model-layer notes
- service/module boundary notes
- test-coverage notes

### 2.4 Assumptions

- any assumptions made that were not directly specified
- any places where the agent chose one reasonable approach over another

### 2.5 Risks And Tradeoffs

- known weaknesses
- deferred concerns
- anything intentionally left for a later retrieval-plane slice

### 2.6 Validation Evidence

- tests added
- tests run
- commands used
- results summary
- any tests not run and why
- whether review UI regression tests were run

### 2.7 Optional Evidence

When useful, include:

- parity-report examples
- concise notes showing derived-row examples

Do not inflate the slice with UI walkthroughs unless shared code unexpectedly required UI regression evidence.

### 2.8 Scope-Conformance Statement

Explicitly confirm whether the submission:

- stayed additive
- preserved canonical APS evidence truth
- avoided read-path cutover
- avoided public API/UI changes
- avoided embeddings/vector work
- preserved validate-only semantics

## 3. Required Comparison Questions

Each submission should make it easy to answer:

- Did the agent follow the retrieval-plane phase docs?
- Did the agent stay in Phase1A rather than broadening to full Phase 1?
- Did the agent preserve canonical APS truth correctly?
- Did the agent keep derivation and validation logic modular?
- Did the agent avoid regressing the current review UI baseline?

## 4. Completion Standard

A submission is not comparison-ready unless it includes:

- changed file inventory
- validation evidence
- assumptions
- risks
- scope-conformance statement
