# NRC APS Document Trace UI Phase Partition Plan

## 1. Purpose

This document partitions the `Document Trace` implementation into bounded execution phases for use in Google Antigravity IDE.

It exists to make the implementation:

- narrow
- non-fragile
- regression-aware
- mechanically executable in slices

This document is not a replacement for the higher-level spec, contract, blueprint, or validation plan. It is the execution partition that should be used to sequence implementation work.

## 2. Canonical Companion Documents

This phase plan must be read together with:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_document_trace_ui_spec.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_document_trace_ui_data_contract.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_document_trace_ui_implementation_blueprint.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_document_trace_ui_validation_plan.md`

If this phase plan and those documents disagree, the implementation must stop and reconcile the docs before proceeding.

## 3. Global Execution Rules

- Work on `master` unless explicitly directed otherwise.
- Preserve the existing `/review/nrc-aps` review UI throughout the implementation.
- Prefer additive changes over shared-file edits.
- When shared-file edits are required, keep them narrow and regression-tested.
- Do not modify connector execution paths.
- Do not modify runtime artifact contents.
- Do not treat retrieval as a required dependency.
- Do not use local corpus paths as the durable source contract.
- Do not broaden into context-packet/dossier comparison, editing, or multi-document workflows in this implementation phase.

## 4. Phase Boundaries

The implementation should be executed in the following order.

No phase should begin until the previous phase has:

- completed its intended code changes
- passed its phase gate
- been re-audited for non-regression

## 5. Phase 0: Recon And Freeze

### Goal

Freeze the live authority files, audited runtime, and exact initial target behavior before changing code.

### Scope

Allowed activity:

- read current implementation files
- verify route and static asset serving path
- verify audited runtime assumptions
- verify the latest document-trace planning docs are the working authority

### Primary files to inspect

- `backend\main.py`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\schemas\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_runtime.py`
- `backend\app\models\models.py`
- `backend\app\review_ui\static\index.html`
- `backend\app\review_ui\static\review.css`
- `backend\app\review_ui\static\review.js`
- audited runtime under `backend\app\storage_test_runtime\lc_e2e\20260328_150207\`

### Must confirm before Phase 1

- `Document Trace` remains a separate page
- canonical identity is `run_id + target_id`
- source anchor is `blob_ref`
- extracted units are diagnostics `ordered_units`
- retrieval is absent/optional
- current review page behavior remains the regression baseline

### Gate

Proceed only if the audited repo state still matches the planning assumptions materially.

## 6. Phase 1: Backend Trace Manifest And Selector Contract

### Goal

Create the minimal backend contract that allows the frontend to:

- pick a document within a run
- bootstrap a document trace page

### Scope

Allowed files:

- `backend\app\api\review_nrc_aps.py`
- `backend\app\schemas\review_nrc_aps.py`
- new `backend\app\services\review_nrc_aps_document_trace.py`
- tests directly covering those additions

Avoid in this phase:

- source streaming
- PDF viewer integration
- main review UI launch controls
- tab content beyond what the trace manifest minimally needs

### Required deliverables

- document selector route
- trace manifest route
- trace assembly service capable of:
  - resolving `connector_run_target`
  - resolving `aps_content_linkage`
  - resolving `aps_content_document`
  - summarizing `aps_content_chunk`
  - classifying completeness/missingness

### Gate

Proceed only if:

- contract tests pass
- trace manifest is stable for a real run and a real `target_id`
- retrieval absence does not break the manifest

## 7. Phase 2: Source Streaming And Path Safety

### Goal

Add safe, bounded streaming of the run-scoped source object via `blob_ref`.

### Scope

Allowed files:

- `backend\app\api\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_runtime.py`
- `backend\app\services\review_nrc_aps_document_trace.py`
- tests covering source-path safety and source route behavior

Avoid in this phase:

- frontend viewer implementation
- changes to current file-preview behavior

### Required deliverables

- source-stream route
- bounded path validation for resolved blob paths
- content-type handling from durable metadata or safe fallback

### Gate

Proceed only if:

- path traversal is rejected
- missing source blobs degrade explicitly
- the route does not expose arbitrary user-controlled file access

## 8. Phase 3: Document Trace Page Shell

### Goal

Add the new page shell and minimal navigation path without yet integrating the heavy viewer logic.

### Scope

Allowed files:

- `backend\main.py`
- new `backend\app\review_ui\static\document_trace.html`
- new `backend\app\review_ui\static\document_trace.css`
- new `backend\app\review_ui\static\document_trace.js`
- narrow launch additions to:
  - `backend\app\review_ui\static\index.html`
  - `backend\app\review_ui\static\review.css`
  - `backend\app\review_ui\static\review.js`
- page-shell tests

Avoid in this phase:

- PDF rendering
- fine-grained tab implementations
- synchronization behavior

### Required deliverables

- `/review/nrc-aps/document-trace` shell route
- shell layout with:
  - back link
  - run selector
  - document selector
  - source pane placeholder
  - right-pane tab shell
- narrow launch affordance from current review UI

### Gate

Proceed only if:

- current `/review/nrc-aps` still behaves correctly
- current three review modes still load
- document-trace shell loads without breaking shared theme/layout behavior

## 9. Phase 4: Core Right-Pane Data Tabs

### Goal

Implement the right-pane data tabs that do not require source-viewer synchronization to be useful.

### Scope

Allowed files:

- `backend\app\api\review_nrc_aps.py`
- `backend\app\schemas\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_document_trace.py`
- `backend\app\review_ui\static\document_trace.js`
- `backend\app\review_ui\static\document_trace.css`
- document-trace tests

### Required v1 tabs to make useful first

- `Summary`
- `Diagnostics`
- `Normalized Text`
- `Indexed Chunks`

Avoid in this phase:

- source viewer rendering
- exact synchronization behavior

### Gate

Proceed only if:

- these tabs load lazily
- missing layers degrade explicitly
- the page is already useful for a real document even before PDF viewer integration

## 10. Phase 5: PDF-First Source Viewer Integration

### Goal

Render the source document for PDFs using a controllable client-side viewer.

### Scope

Allowed files:

- vendored assets under `backend\app\review_ui\static\vendor\`
- `backend\app\review_ui\static\document_trace.html`
- `backend\app\review_ui\static\document_trace.css`
- `backend\app\review_ui\static\document_trace.js`
- any required notice/license file under the same vendor area

Avoid in this phase:

- exact text-layer alignment
- normalization of unsupported non-PDF formats beyond simple fallback

### Required deliverables

- PDF viewer asset integration
- page rendering
- page navigation
- zoom
- stable page anchors

### Gate

Proceed only if:

- a real PDF from run storage renders
- the viewer does not break dark mode or layout
- the main review page remains unaffected

## 11. Phase 6: Extracted Units And Page-Level Sync

### Goal

Implement the primary fine-grained extraction tab and the required page-level synchronization.

### Scope

Allowed files:

- `backend\app\api\review_nrc_aps.py`
- `backend\app\schemas\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_document_trace.py`
- `backend\app\review_ui\static\document_trace.js`
- `backend\app\review_ui\static\document_trace.css`
- document-trace tests

### Required deliverables

- `Extracted Units` tab backed by diagnostics `ordered_units`
- extracted-unit click -> source page jump
- source page focus -> page-scoped right-pane filtering/highlighting
- explicit precision labeling

Avoid in this phase:

- promising exact phrase or cell sync
- broadening into downstream comparative interpretation

### Gate

Proceed only if:

- page-level sync works on a real document
- missing diagnostics degrade explicitly
- best-effort and unit precision are not mislabeled as exact

## 12. Phase 7: Downstream Usage And Non-PDF Fallback

### Goal

Fill out the remaining v1 conditional surfaces without broadening the product.

### Scope

Allowed files:

- `backend\app\api\review_nrc_aps.py`
- `backend\app\schemas\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_document_trace.py`
- `backend\app\review_ui\static\document_trace.js`
- `backend\app\review_ui\static\document_trace.css`
- document-trace tests

### Required deliverables

- `Downstream Usage` tab
- text-like fallback or explicit unsupported messaging for non-PDF sources

### Gate

Proceed only if:

- downstream usage remains conditional and non-overstated
- the non-PDF path degrades clearly
- the page does not start pretending all sources have equal sync quality

## 13. Phase 8: Hardening And Regression Closure

### Goal

Harden the implementation and prove it does not regress the existing review UI.

### Scope

Allowed files:

- all document-trace implementation files
- only narrow shared-file edits required for regression fixes
- tests

### Required deliverables

- loading, empty, and error states
- stale-request protection where needed
- accessibility pass on new page controls
- regression validation against the existing review page

### Gate

This phase is complete only if:

- focused document-trace tests pass
- existing review regression tests pass
- live manual QA passes on the document-trace page
- live manual QA confirms the current review page still behaves correctly

## 14. Phase 9: Final Re-Audit, Freeze, And Commit

### Goal

Close out the feature cleanly and explicitly.

### Required closeout actions

- re-read every edited shared file
- re-read the final route and schema surfaces
- verify the implementation still matches the planning docs materially
- verify any deviations are explicitly documented
- produce narrow logical commits

### Preferred commit grouping

1. backend trace assembly and routes
2. document-trace page shell plus viewer integration
3. hardening and tests

### Final stop conditions

Do not close out as complete if:

- the implementation depends on local corpus paths
- retrieval became a hidden dependency
- the current review page regressed
- the implementation broadened into a different product than the planned two-pane document-trace workspace

## 15. Antigravity Use Guidance

For Antigravity execution, each working session should declare:

- which phase is being worked
- which files are in scope for that phase
- what the phase gate is
- what is explicitly out of scope in that session

That keeps the implementation bounded and prevents the IDE workflow from collapsing multiple phases into one unreviewable pass.

