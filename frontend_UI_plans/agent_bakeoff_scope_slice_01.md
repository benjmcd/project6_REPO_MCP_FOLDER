# Agent Bake-Off Scope Slice 01

## 1. Purpose

This document defines the first bounded implementation slice both agents should execute.

It is intentionally large enough to reveal architectural quality, but small enough to compare fairly.

## 2. Slice Goal

Deliver the minimum reviewable NRC APS UI slice that proves the implementation shape without broadening scope.

## 3. Slice Contents

The first slice should include all of the following.

### 3.1 Read-Only Review API

Implement the additive GET endpoints needed for:

- run selector
- canonical pipeline definition
- run-specific overview
- strict filesystem tree
- node details
- file details

The route family should follow the planning docs.

### 3.2 Review Model Plumbing

Implement the modular service layers needed to:

- discover reviewable runs
- select the latest completed reviewable run
- build canonical and run-specific node payloads
- build the strict filesystem tree
- build the details drawer payloads

### 3.3 Minimal Backend-Served UI Shell

Implement a minimal page that includes:

- run selector
- view toggle
- diagram pane shell
- filesystem tree pane
- right-side details drawer shell

The diagram can initially render a minimal but functional version of the canonical/run-specific graph so long as it is wired to the correct node ids and interactions.

### 3.4 Cross-Selection Wiring

Implement basic interaction wiring so that:

- clicking a diagram node highlights mapped tree entries and opens the details drawer
- clicking a tree entry highlights the mapped node when available and opens the details drawer
- the strict filesystem tree auto-reveals the selected node's mapped files

### 3.5 Focused Tests

Implement the tests required to validate the slice according to:

- `nrc_aps_review_ui_validation_plan.md`

## 4. What This Slice Must Not Include

Do not include:

- file preview
- JSON/text preview
- image preview
- live polling
- curated alternate tree mode
- cross-run comparison
- execution controls
- generalized multi-pipeline support

## 5. Required Repo-Fit Shape

This slice should follow the implementation blueprint for:

- exact files to modify
- exact files to add
- module boundaries
- backend-served asset strategy

## 6. Expected Output Quality

This slice is not a throwaway prototype.

It should be:

- modular
- testable
- repo-fit
- consistent with the frozen planning docs
- simple enough to extend later without restructuring the whole feature

## 7. Completion Standard

Slice 01 is complete only if:

- the read-only review API exists
- the UI shell loads
- the selector defaults correctly
- the tree is strict filesystem based
- the details drawer works at a basic useful level
- the interactions between graph, tree, and details are present
- the slice validates against the golden runtime

