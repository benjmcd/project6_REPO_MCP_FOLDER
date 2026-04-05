# 00E Repo Consumer and Invariant Map

## Purpose

Map the live APS surfaces relevant to a multi-variant visual-lane program.

This document distinguishes:
- verified live fact,
- inferred sensitivity,
- unresolved closure item.

---

## 1. Primary owner surface

### `backend/app/services/nrc_aps_document_processing.py`
**Verified live fact**

Observed:
- `process_document(...)` routes by media type
- `_process_pdf(...)` contains:
  - native extraction
  - OCR fallback
  - hybrid OCR
  - visual preservation
  - artifact writing
  - page summaries
- visual classes:
  - `diagram_or_visual`
  - `text_heavy_or_empty`
- visual significance helper:
  - embedded image `>=100x100`
  - or drawings `>=20`
- OCR fallback separately uses image-only significance
- `default_processing_config(...)` exists

**Sensitivity:** Highest

**Additional interpretation:**  
The OCR/visual split is real and still not fully frozen. This is now treated as a distinct boundary-definition problem, not a minor detail.

---

## 2. Verified partial direct caller map

### Direct call into `process_document(...)`
Verified:
- `backend/app/services/nrc_aps_artifact_ingestion.py`
  - `extract_and_normalize(...)` calls `nrc_aps_document_processing.process_document(...)`

### Adapter layer feeding document processing
Verified:
- `backend/app/services/nrc_aps_artifact_ingestion.py`
  - `processing_config_from_run_config(...)`
  - forwards processing overrides into `default_processing_config(...)`
  - then into `process_document(...)`

### Downstream ingestion/orchestration consumers
Verified:
- `backend/app/services/connectors_nrc_adams.py`
  - calls `nrc_aps_artifact_ingestion.extract_and_normalize(...)`
- `backend/app/services/nrc_aps_content_index.py`
  - calls `nrc_aps_artifact_ingestion.extract_and_normalize(...)`
- `backend/app/services/nrc_aps_content_index.py`
  - imports document-processing quality constants directly
  - rebuilds diagnostics payloads including `visual_page_refs`
  - writes diagnostics blobs after extraction

### Internal recursive use
Verified:
- `process_document(...)` recursively calls itself for ZIP members

**Implication:**  
The verified minimum impact surface includes:
- document-processing owner file,
- artifact-ingestion adapter,
- connector orchestration,
- content indexing and diagnostics persistence,
- ZIP recursion.

---

## 3. Runtime-root / review discovery surfaces

### `backend/app/services/review_nrc_aps_runtime_roots.py`
**Verified live fact**
- normalizes `storage` / `storage_test_runtime` roots to `.../lc_e2e`
- deterministic candidate roots include:
  - `backend/app/storage_test_runtime/lc_e2e`
  - `backend/storage_test_runtime/lc_e2e`

**Sensitivity:** Highest

### `backend/app/services/review_nrc_aps_runtime.py`
**Verified live fact**
- `get_allowlisted_roots()` delegates to `candidate_review_runtime_roots(...)`
- passes `settings.storage_dir`

**Sensitivity:** High

### `backend/app/api/review_nrc_aps.py`
**Verified live fact**
- imports `runtime_db_session_for_run`
- uses it on many review API endpoints
- also imports review/runtime and document-trace service functions

**Sensitivity:** High

**Implication:**  
Runtime DB binding is API-facing, not just an internal helper.

### `backend/app/services/review_nrc_aps_document_trace.py`
**Verified live fact**
- visual ref deserialization
- visual artifact resolution
- diagnostics / trace payload composition

**Sensitivity:** High

---

## 4. Diagnostics persistence and runtime DB surfaces

### Diagnostics persistence
Evidence:
- `backend/tests/test_diagnostics_ref_persistence.py`

Verified concerns:
- diagnostics ref persists on both document and linkage rows
- cross-run overwrite safety is enforced
- absent linkage diagnostics ref must not fall back incorrectly

**Sensitivity:** High

### Runtime DB binding / isolation
Evidence:
- `backend/tests/test_review_nrc_aps_runtime_db.py`

Verified concerns:
- runtime binding lookup per run
- runtime DB session correctness
- session closure behavior
- read-only behavior
- schema validation
- per-runtime isolation

**Sensitivity:** High

---

## 5. Governance / reporting surfaces

### `nrc_aps_contract.py`
Verified live file.  
**Sensitivity:** High.

### `nrc_aps_replay_gate.py`
Verified live file.  
**Sensitivity:** High.  
Baseline-only initially.

### `nrc_aps_promotion_gate.py`
Verified live file.  
**Sensitivity:** High.  
Baseline-only initially.

### `nrc_aps_live_batch.py`
Verified live file.  
**Sensitivity:** High.  
Baseline-only initially.

### `nrc_aps_evidence_report.py`
Verified live file.  
**Sensitivity:** High.  
Baseline-normalized initially.

### `nrc_aps_evidence_bundle*.py`
Verified live module family.  
**Sensitivity:** High.

### `nrc_aps_evidence_report_export*.py`
Verified live module family.  
**Sensitivity:** High.

### `nrc_aps_evidence_citation_pack*.py`
Verified live module family.  
**Sensitivity:** High.

---

## 6. Verified active test roots

### Root tests
Verified:
- `tests/`

### Backend tests
Verified:
- `backend/tests/`

---

## 7. Remaining unresolved closure items

1. exact full caller/call graph
2. exact public/report/review field sensitivity map
3. exact final selector config key/failure-mode naming
4. exact extracted seam inside `_process_pdf(...)`
5. exact performance baseline and budget
6. exact repo runner/wrapper conventions


## 8. Additional surfaces elevated by attached-session evidence

The attached session strongly suggests that the following should be treated as explicit closure targets, not just implicit neighbors:

### `review_nrc_aps_catalog.py`
**Status:** session-origin material signal; direct re-check still needed  
**Reason elevated:** may aggregate/discover runtime bindings across roots without enough experiment filtering.

### Report/export run-visibility paths
**Status:** session-origin material signal; direct re-check still needed  
**Reason elevated:** shared run/report lookup may still expose experiment runs even when artifacts are separately rooted.

These are now treated as likely blocker surfaces until re-verified or disproven.


## 9. Session-origin API exposure surfaces

The attached session materially strengthens the interpretation that the review API surface is broad enough to expose selector mistakes through multiple endpoint classes, not just through generic runtime discovery.

### API-facing exposure classes elevated by session evidence
- visual artifact retrieval
- diagnostics retrieval
- normalized text retrieval
- indexed chunks retrieval
- extracted units retrieval
- document trace retrieval

**Status:** session-origin material signal; safer to baseline-lock than to assume non-impact.


## 10. Verified report/export run-visibility surfaces

### `backend/app/services/nrc_aps_evidence_report.py`
**Verified live fact**
- derives `run_id` from persisted source citation-pack payloads
- resolves `ConnectorRun` from shared DB state
- persists report artifacts under that run
- writes report refs/summaries back into `run.query_plan_json`

**Sensitivity:** Highest for experiment visibility

### `backend/app/services/nrc_aps_evidence_report_export.py`
**Verified live fact**
- derives `run_id` from persisted evidence-report payloads
- resolves `ConnectorRun` from shared DB state
- persists export artifacts under that run
- writes export refs/summaries back into `run.query_plan_json`

**Sensitivity:** Highest for experiment visibility

### `backend/app/services/nrc_aps_evidence_report_export_package.py`
**Verified live fact**
- resolves `owner_run_id`
- rejects cross-run package composition in v1
- resolves `ConnectorRun` from shared DB state
- persists package artifacts under that run
- writes package refs/summaries back into `run.query_plan_json`

**Sensitivity:** Highest for experiment visibility

**Implication:**  
Shared run-bound report/export visibility is a separate blocker layer from runtime-root collision.  
Even with separate roots, experiments are not sufficiently isolated if shared run/report/export surfaces continue to resolve and persist against baseline-visible run identities.


## 11. Direct backend caller closure status

The direct backend caller chain is now explicitly verified:

- `nrc_aps_artifact_ingestion.extract_and_normalize(...)` is the direct backend caller of `process_document(...)`
- `connectors_nrc_adams.py` and `nrc_aps_content_index.py` are the direct backend callers of `extract_and_normalize(...)`
- `process_document(...)` recursively calls itself for ZIP members

This narrows the remaining open issue:
the direct backend caller map is effectively closed; the remaining uncertainty is broader indirect consumer closure beyond that chain.


## 12. Live app-surface consumer closure status

Within `backend/app/**/*.py`, exact search now confirms:

- `extract_and_normalize(...)` is only used by:
  - `connectors_nrc_adams.py`
  - `nrc_aps_content_index.py`
- `process_document(...)` is only directly called by:
  - `nrc_aps_artifact_ingestion.py`
  - plus ZIP recursion inside the owner

So the live app-surface caller chain is materially closed.
The remaining open consumer item is broader residual visibility/effect closure beyond this verified chain, not hidden live app-surface callers.


## 13. Residual app-surface closure status

The remaining residual live app-surface consumers are now explicitly identified and no longer treated as a vague open item:

- model persistence (`visual_page_refs_json`)
- API schemas (`visual_page_refs`)
- retrieval-plane rebuild/read
- evidence-bundle assembly/contract

With those added to the already-verified review/report/runtime surfaces, the in-scope live app-surface consumer/visibility map is materially closed.
