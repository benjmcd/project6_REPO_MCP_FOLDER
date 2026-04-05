# 03V Selector Key Insertion and Consumption Map

## Purpose

Freeze the exact code-level insertion/consumption map for the canonical selector key:

- `visual_lane_mode`

This document does not reopen the seam question.
It only fixes where the key belongs in the live code path.

## Canonical path

### 1. Request-level normalization
**Function:** `connectors_nrc_adams._normalize_request_config(...)`  
**Live lines:** 550-812

### Required role
- preserve incoming `visual_lane_mode`
- treat it as a control key
- exclude it from lenient-pass-through query payload construction
- normalize absent/invalid/unapproved values to `baseline`

### Why here
This is the repo’s existing normalization point for enum-like request controls.

---

### 2. Processing-config forwarding
**Function:** `nrc_aps_artifact_ingestion.processing_config_from_run_config(...)`  
**Live lines:** 146-164

### Required role
- explicitly forward `visual_lane_mode` from normalized run config into processing overrides

### Why here
This is the current adapter boundary from request/run config into document-processing config.

---

### 3. Processing-config default
**Function:** `nrc_aps_document_processing.default_processing_config(...)`  
**Live lines:** 148-163

### Required role
- define default:
  - `visual_lane_mode = "baseline"`

### Why here
This is the owner module’s default processing-config constructor.

---

### 4. First owner-path consumer
**Function:** `nrc_aps_document_processing._process_pdf(...)`  
**Live lines:** 511-777

### Required role
- read `visual_lane_mode` from normalized processing config
- first consume it only at the visual-preservation decision zone

### First-consumption zone
**Primary zone:** visual-preservation lane  
**Live lines:** 687-718

This is where the key should first matter conceptually, because that is the currently selected first-pass target zone.

---

## What should *not* consume the key first

Before the seam is formally reopened, `visual_lane_mode` should **not** first alter:

- OCR fallback branch  
  lines 599-645

- hybrid OCR branch  
  lines 647-680

- page-source accounting  
  lines 682-685

- final aggregate result assembly  
  lines 736-773

## Preferred first-pass flow

1. request payload enters `_normalize_request_config(...)`
2. normalized config carries `visual_lane_mode`
3. control-key exclusion prevents query-payload leakage
4. `processing_config_from_run_config(...)` forwards it
5. `default_processing_config(...)` supplies `baseline` when absent
6. `_process_pdf(...)` first consumes it in the visual-preservation lane

## What remains separate from this document

This document does **not** decide:
- the internal branch shape inside lines 687-718
- whether the mode gates only classification, or classification + capture, or classification + capture + artifact write
- how future non-baseline modes are admitted

Those remain part of the separate seam-freeze problem.
