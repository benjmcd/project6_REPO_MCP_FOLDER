# 03W Exact `_process_pdf(...)` Seam Freeze Specification

## Purpose

Freeze the first integrated seam inside `nrc_aps_document_processing._process_pdf(...)` at a helper-contract level.

This closes the last major technical ambiguity left by the earlier line-range seam map.

## Live helper structure already present

The current visual-preservation lane already decomposes into these concrete helpers:

- `_has_significant_visual_content(page)`  
  lines 55-68

- `_classify_visual_page(native_quality_status, has_visual)`  
  lines 71-83

- `_capture_visual_page_ref(page, page_number, visual_page_class)`  
  lines 86-96

- `_write_visual_page_artifact(artifact_storage_dir, page, page_number, config)`  
  lines 105-145

And the current in-loop caller zone is:

- `_process_pdf(...)` lines 687-718

## Exact first-pass seam

The first-pass extracted seam is now frozen conceptually as:

### Seam location
After:
- page-source accounting  
  lines 682-685

Before:
- page summary accumulation / `all_units.extend(...)`  
  lines 720-729

### Seam responsibility
Only the **visual-preservation lane**:
- determine visual significance
- determine visual page class
- attempt visual ref capture
- optionally attempt visual artifact write
- emit visual-lane degradation deltas

## Canonical seam interface

### Inputs
The seam may consume only:

- `page`
- `page_number`
- `pre_branch_native_quality_status`
- `config`

### Outputs
The seam must return only:

- `visual_page_class: str`
- `visual_ref: dict[str, Any] | None`
- `visual_degradation_codes: list[str]`

### Caller-owned post-processing
The caller remains responsible for:

- appending `visual_ref` into `visual_page_refs` if present
- extending `degradation_codes`
- writing `visual_page_class` into `page_summaries`

## What stays outside the seam

The seam must **not** own or alter:

- native extraction
- OCR fallback
- hybrid OCR
- page-source accounting
- `page_units`
- `all_units`
- final `page_summaries` structure
- final aggregate result assembly
- document-level counters

## Why this exact boundary is correct

It matches the live helper decomposition already present.
It also minimizes scope:
- classification/capture/artifact logic is isolated
- OCR and final-result logic stay baseline-locked
- page summary structure stays baseline-locked

## Required behavior inside the seam

The seam may internally use the existing helpers in this order:

1. `_has_significant_visual_content(page)`
2. `_classify_visual_page(pre_branch_native_quality_status, has_visual)`
3. if preserve-eligible:
   - `_capture_visual_page_ref(...)`
   - optionally `_write_visual_page_artifact(...)`

The seam must preserve the current failure behavior:
- capture failure -> `visual_capture_failed`
- artifact write failure -> `visual_artifact_failed`
- text-heavy path -> no ref emitted

## Interaction with `visual_lane_mode`

Once `visual_lane_mode` is propagated to `_process_pdf(...)`, this seam is the first and only first-pass consumer zone for that key.

That means:
- key propagation path is closed by `03V`
- seam boundary is closed by this document
- future non-baseline mode behavior must be implemented only inside this seam boundary in pass 1

## What this does not reopen

This document does **not** allow:
- OCR fallback changes
- hybrid OCR changes
- artifact schema changes
- page summary schema changes
- report/review/runtime visibility changes

Those remain baseline-locked.
