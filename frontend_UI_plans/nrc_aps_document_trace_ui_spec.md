# NRC APS Document Trace UI Specification

## 1. Objective

Design a read-only document-trace review surface for NRC APS runs that lets a user inspect one source document beside the document-scoped outputs produced from that same document in the selected run.

This feature is not a generic file preview page. It is a run-scoped provenance and extraction inspection surface.

## 2. Repo-Fit Authority Model

This specification relies on the following repo-confirmed authority surfaces:

- live web entrypoint:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- live review API routes:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- live review schemas:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\schemas\review_nrc_aps.py`
- live review runtime/path helpers:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_runtime.py`
- live review UI assets:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\index.html`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.css`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.js`
- live ORM models:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\models\models.py`
- current audited runtime example:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260328_150207\`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260328_150207\local_corpus_e2e_summary.json`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260328_150207\lc.db`

Important repo-confirmed facts that shape this feature:

- the live review UI already exists at `/review/nrc-aps`
- the current review API only exposes safe JSON/text preview and metadata; it does not yet expose a review-safe source-document stream for binary/PDF inspection
- the strongest document provenance spine is run-scoped and distributed across:
  - `connector_run_target`
  - `aps_content_linkage`
  - `aps_content_document`
  - `aps_content_chunk`
  - file-backed refs such as `blob_ref`, `normalized_text_ref`, and `diagnostics_ref`
- the current review tree is runtime-root oriented, not source-corpus oriented, so it is not the correct primary launch surface for document inspection
- the latest audited runtime has:
  - `69` linkage rows for the run
  - `68` distinct `content_id` values
  - `0` retrieval rows in `aps_retrieval_chunk_v1`
- therefore retrieval cannot be treated as a required v1 layer
- `aps_content_units_v2` is chunk-oriented in the audited runtime and is not the authoritative fine-grained extraction surface
- diagnostics `ordered_units` provide the strongest fine-grained page/unit/bbox extraction surface currently available
- `visual_page_refs_json` is empty for at least the audited sample document `LOCALAPS00001`, so the UI cannot depend on precomputed visual page derivatives

## 3. Product Goal

The product goal is to let a reviewer answer this question without manually traversing JSON, database tables, and artifact folders:

- what did this source document become in this run

The page must allow a user to:

- choose a run and a specific run target
- see the run-processed source document or source file representation
- see the document-scoped extraction and provenance layers derived from that target
- navigate between source pages and extracted units where the pipeline supports it
- understand what is present, what is missing, and what is only available at lower precision
- see downstream usage when it exists without pretending it always exists

## 4. Product Identity

The product name for this feature is:

- `Document Trace`

The page shell route for v1 should be:

- `/review/nrc-aps/document-trace`

The canonical page selection state is:

- `run_id + target_id`

The page shell should use query parameters for deep-linkable state:

- `run_id`
- `target_id`
- optional `tab`
- optional `page`

Reason:

- the review UI is currently served as backend-hosted static HTML
- a fixed page shell route plus query-string state is the narrowest additive fit
- the canonical identity still remains run-scoped and target-scoped even if the HTML route itself is not path-parameterized

## 5. In Scope For V1

- NRC APS only
- separate document-trace page, not a permanently expanded section under the current review page
- run selector
- document selector driven by run targets, not by the strict runtime filesystem tree
- PDF-first source rendering from the durable run `blob_ref`
- text-like fallback rendering for non-PDF files when the source media type supports it
- right-hand trace workspace with these tabs:
  - `Summary`
  - `Extracted Units`
  - `Normalized Text`
  - `Indexed Chunks`
  - `Diagnostics`
  - `Downstream Usage`
- explicit trace-completeness and missingness reporting
- page-level synchronization between source pages and extracted layers
- opportunistic unit-level synchronization where diagnostics metadata supports it
- read-only API routes and read-only UI behavior
- dark-mode/light-mode compatibility with the existing review UI theme system

## 6. Out Of Scope For V1

- editing, annotation, or mutation
- any regeneration of missing document artifacts
- exact arbitrary click-anywhere bidirectional alignment across all representations
- retrieval as a required or default right-side layer
- context packets, dossiers, evidence reports, or exports as the default extracted-content pane
- generic XML/XBRL/HTML semantic rendering
- multi-document comparison
- embedding this feature as a permanent lower section of the existing graph page
- dependence on the current local corpus path as the durable source contract

## 7. Required Invariants

- the feature must be strictly read-only
- the feature must remain run-scoped
- the authoritative source object for v1 must be the run-processed blob referenced by `blob_ref`, not the current corpus file path
- the feature must not silently invent unavailable trace layers
- the feature must not imply exact sync precision when only page-level or best-effort mapping exists
- the feature must not depend on retrieval rows being present
- the feature must not depend on `visual_page_refs_json` being populated
- the current review page must remain functional and structurally unchanged except for narrow launch/navigation additions
- the frontend must not reconstruct the provenance bundle by stitching together unrelated endpoints ad hoc; the backend must assemble a document-trace model

## 8. Identity And Provenance Model

The feature must model identity in layers.

### 8.1 Source Identity

Human-facing/source-facing identity:

- file name
- accession number when present
- document title when present
- source media type
- source URL or source reference metadata when present

### 8.2 Run-Scoped Target Identity

This is the primary identity for the page:

- `run_id`
- `target_id`

This layer answers:

- was this document selected/downloaded in this run
- what run-specific object is being inspected

### 8.3 Persisted Content Identity

This layer captures document-level processing identity:

- `content_id`
- `content_contract_id`
- `chunking_contract_id`
- `normalization_contract_id`

This layer must be surfaced because the same run can contain deduplicated content identities.

### 8.4 Chunk Identity

This layer supports indexed/output inspection:

- `chunk_id`
- `chunk_ordinal`
- `page_start`
- `page_end`
- `start_char`
- `end_char`

### 8.5 Dedupe Reality

The audited runtime contains `69` linkage rows but only `68` distinct `content_id` values. That is a legitimate deduplication state, not a broken one.

Therefore:

- `target_id` must remain the page key
- `content_id` must be displayed as a secondary identity, not used as the only page key

## 9. Page Layout

The page should use a stable three-zone structure:

- header
  - back link to the main review page
  - run selector
  - document selector
  - theme control
  - summary identity badges
- main body
  - left pane: source viewer
  - right pane: document-trace workspace
- optional secondary rail within the right pane
  - identity/provenance badges
  - completeness indicators

This is a dedicated document workspace, not a modal.

### 9.1 Alignment With User Mockup And Earlier Articulation

The user-provided mockup and prior articulation establish these required product-shape expectations:

- source/original document on the left
- extracted/processed/provenance content on the right
- both sides visible at the same time
- current run/review context retained at the top
- the right side must show real outputs of processing/ingestion/extraction, not only a summary badge set

The v1 specification remains aligned with those expectations.

The one intentional implementation deviation from the mockup is page composition:

- the mockup visually places the document workspace below the existing review UI
- v1 instead freezes this as a separate page reachable from the existing review UI

Reason:

- this is the narrowest way to preserve the current review page behavior
- it prevents the existing graph/tree/details surface from turning into a second monolith
- it reduces regression risk to current interactions, zoom state, theme behavior, and drawer/tree logic

The other important implementation interpretation is right-pane organization:

- the mockup suggests multiple extracted outputs visible in one vertically stacked workspace
- v1 freezes a tabbed right pane with lazy loading

Reason:

- the user explicitly left open whether the extracted side should be organized as chunks, blobs, context packets, dossiers, or other strata
- tabbed/lazy organization is the least fragile way to preserve multiple real representations without forcing all of them into one long always-rendered column
- each tab may still render stacked cards or panels internally

These deviations are intentional and must not be treated as accidental drift from the requested product intent.

## 10. Left Pane: Source Viewer

### 10.1 PDF

For PDF sources, the left pane must use a controllable client-side PDF renderer.

It must support:

- page navigation
- scrollable multi-page view
- zoom
- stable page anchors
- page-focused highlighting when the right pane requests a jump

The left pane must not rely on native browser PDF embedding for v1 because controlled page navigation and synchronization are required.

### 10.2 Text-Like Sources

For txt/json/csv and other text-readable sources, the left pane may render:

- formatted text
- code-style preview
- structured pretty-print when appropriate

### 10.3 Unsupported Or Limited Sources

If the source media type is not supported for rich rendering, the page must:

- show source metadata
- show a clear unsupported-view message
- keep the right-hand trace tabs usable where data exists

## 11. Right Pane: Trace Workspace

The right pane must be stratified. It must not flatten all downstream and extraction outputs into one untyped blob.

### 11.1 Summary

Must include:

- run identity
- target identity
- accession number
- document title
- media type
- document class
- page count
- quality status
- completeness indicators
- mapping/sync precision indicators

### 11.2 Extracted Units

Primary fine-grained extraction surface for v1:

- diagnostics `ordered_units`

Each unit should include, when present:

- page number
- unit kind
- text
- bbox
- start/end char
- source-of-truth flag that this unit came from diagnostics

### 11.3 Normalized Text

Document-level normalized text surface from `normalized_text_ref`.

### 11.4 Indexed Chunks

Chunk/index surface derived from:

- `aps_content_chunk`
- optionally corroborated by the chunk-oriented `aps_content_units_v2` artifact

This tab is chunk-level, not unit-level.

### 11.5 Diagnostics

Diagnostics surface should include:

- quality status
- degradation or warning codes
- extraction metadata
- page counts
- unit counts
- any structured warnings relevant to trace quality

### 11.6 Downstream Usage

This tab is secondary and conditional.

It should summarize:

- branch participation
- attributable downstream appearances
- downstream artifact references when the attribution is strong enough

It must not imply that every document necessarily flows into branch evidence products.

## 12. Synchronization Precision Model

Synchronization must be modeled explicitly in tiers.

### 12.1 Required V1 Precision

Required:

- extracted unit click -> source page jump
- source page focus -> highlight/filter right-side content for the same page

### 12.2 Opportunistic V1 Precision

Allowed when supported by diagnostics metadata:

- extracted unit click -> source region highlight using bbox
- source click -> nearest extracted unit by page and bbox proximity

### 12.3 Best-Effort Precision

Allowed but must be labeled as best-effort:

- normalized text click -> nearest unit/page using char offsets
- chunk click -> source page and rough text neighborhood only

### 12.4 Explicit Non-Claims

V1 must not claim:

- exact phrase-level sync
- exact table-cell sync
- exact arbitrary click-anywhere reverse mapping

The page must surface a machine-readable and user-visible precision classification such as:

- `page`
- `unit`
- `best_effort`
- `none`

## 13. Trace Completeness And Missingness

The page must explicitly model whether each layer exists.

Required layer states:

- source blob present/missing
- linkage row present/missing
- content document row present/missing
- diagnostics present/missing
- normalized text present/missing
- indexed chunks present/missing
- visual derivatives present/missing
- downstream usage present/not_attributed/not_exercised
- retrieval available/unavailable

Missingness is a first-class state, not an implementation error to hide.

## 14. Launch And Navigation Model

The current review page remains the system-level entry surface.

V1 launch model:

- add a narrow navigation affordance from the existing review page into `Document Trace`
- preseed the current `run_id` when possible
- once on the page, let the user choose a document from a run-scoped selector built from `connector_run_target`

The current strict review tree is not the primary selector authority for this feature.

## 15. Performance And UX Constraints

- do not preload every tab on page load
- do not render every PDF page eagerly
- virtualize or lazily expand long unit/chunk lists
- preserve dark/light theme support
- preserve keyboard accessibility and visible focus states
- keep first meaningful paint bounded to summary plus source-view bootstrap

### 15.1 Preservation Of Existing Review Functionality

The implementation must preserve the current review surface while adding document trace.

At minimum, the following existing behavior must remain intact:

- `/review/nrc-aps` loads and behaves as it does before the document-trace feature
- the three existing review modes remain:
  - `Pipeline Overview`
  - `Run-specific Overview (Light)`
  - `Run-specific Overview (Heavy)`
- current graph rendering semantics remain unchanged
- current tree/drawer/file-preview behavior remains unchanged
- current dark-mode/theme behavior remains unchanged
- current graph zoom-preservation behavior remains unchanged
- current read-only API routes remain backward compatible

The implementation must prefer additive behavior over modification of existing behavior unless a repo-confirmed blocker makes a narrow shared change necessary.

## 16. Representative V1 Scenarios

The implementation must be coherent for at least these significant scenarios.

### 16.1 Strong PDF Trace

Example shape:

- source is a PDF
- source blob is present
- diagnostics are present
- normalized text is present
- indexed chunks are present
- downstream usage may or may not be present

Expected outcome:

- source PDF renders on the left
- `Summary`, `Extracted Units`, `Normalized Text`, `Indexed Chunks`, and `Diagnostics` are available
- page-level synchronization works

### 16.2 Deduplicated Content Identity

Example shape:

- two different `target_id` values map to one `content_id`

Expected outcome:

- the page remains keyed by `run_id + target_id`
- the UI surfaces `content_id` as a secondary identity
- the implementation does not collapse the two targets into one document selector row without explicit product intent

### 16.3 Missing Optional Layers

Example shape:

- source blob exists
- linkage and document rows exist
- one or more optional layers such as normalized text, diagnostics, visual derivatives, or downstream usage are absent

Expected outcome:

- the page still loads
- missing layers are shown explicitly
- absent tabs or panels degrade with explanation instead of vanishing silently

### 16.4 Non-PDF Fallback

Example shape:

- source media type is text-like or otherwise not supported by the rich PDF viewer

Expected outcome:

- the left pane falls back to text-like render or explicit unsupported-view messaging
- the right-side trace surfaces still function where data exists

### 16.5 Retrieval-Absent Runtime

Example shape:

- the run has zero retrieval rows

Expected outcome:

- the page still works
- no required tab or page behavior depends on retrieval availability

## 17. Implementation Guardrails

- do not overload the existing `review.js` page controller with the new page's full logic
- do not use local corpus paths as the durable document contract
- do not treat `aps_content_units_v2` as the authoritative fine-grained unit surface for v1
- do not require retrieval-plane rows
- do not make downstream usage the default right-side representation
- do not hide deduplication states where multiple targets share one `content_id`
