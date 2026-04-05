# 03O `_process_pdf(...)` Seam Candidate Map

## Purpose

Reduce ambiguity around the exact first-pass selector seam inside `nrc_aps_document_processing._process_pdf(...)`.

This document is grounded in the current live line structure of the owner file.

## Live line-based structure

### Zone A — PDF open / page-limit / run initialization
**Lines:** 518-555  
**Role:** document open, encryption/page-limit checks, result structure initialization, chunk loop setup

**Current disposition:** baseline-locked

Reason:
- not part of visual-lane experimentation,
- contains global stability/error behavior,
- changing it would widen scope beyond the intended first pass.

---

### Zone B — Per-page preamble and native extraction
**Lines:** 557-597  
**Role:** page load, early image detection, native unit extraction, native text normalization, native quality calculation, doc-type / low-info routing signals

**Current disposition:** shared-evidence candidate, but not yet fully swappable

Reason:
- this zone produces signals later consumed by both OCR and visual decisions,
- it is the strongest candidate source for a shared page-evidence layer,
- but changing it too freely risks altering OCR fallback triggers in pass 1.

---

### Zone C — OCR fallback branch
**Lines:** 599-645  
**Role:** weak/unusable-text fallback, advanced-doc routing, low-info/no-significant-image fallback, OCR payload selection, OCR replacement of native text

**Current disposition:** baseline-locked in first integrated pass

Reason:
- explicitly governs OCR fallback behavior,
- tests already protect OCR fallback strictness,
- visual-selector work is not allowed to silently alter this branch before the OCR/visual edge is frozen.

---

### Zone D — Hybrid OCR / image supplement branch
**Lines:** 647-680  
**Role:** OCR supplement for significant-image pages, append `ocr_image_supplement` units when novel OCR words exceed threshold

**Current disposition:** baseline-locked in first integrated pass

Reason:
- also sits at the OCR/visual boundary,
- affects page units and downstream normalized text,
- not safe to mutate before boundary freeze.

---

### Zone E — Page-source accounting
**Lines:** 682-685  
**Role:** increments native/ocr page counters based on final page source

**Current disposition:** baseline-locked in first integrated pass

Reason:
- downstream extractor metadata depends on OCR/native counts,
- altering this would be broader than the intended selector pass.

---

### Zone F — Visual-preservation lane
**Lines:** 687-718  
**Role:** visual significance evaluation, visual class assignment, visual ref capture, optional visual artifact write, failure handling for visual capture/artifact creation

**Current disposition:** primary candidate selector-owned region

This is the clearest first-pass candidate region because it contains:
- `has_visual = _has_significant_visual_content(page)`
- `_classify_visual_page(...)`
- `_capture_visual_page_ref(...)`
- `_write_visual_page_artifact(...)`
- visual-capture failure handling

However, it is **not** fully free-floating because:
- it consumes pre-branch quality state from Zone B,
- it writes `visual_page_refs`,
- it contributes `visual_page_class` into page summaries,
- it can trigger artifact persistence behavior.

---

### Zone G — Page summaries and unit accumulation
**Lines:** 720-729  
**Role:** append page units, append page summary including `visual_page_class`

**Current disposition:** mostly baseline-locked, with controlled dependency on visual class output

Reason:
- selector may influence `visual_page_class`,
- but page summary structure itself should remain baseline-locked in pass 1.

---

### Zone H — Final aggregate result
**Lines:** 736-773  
**Role:** final text normalization, final quality, unusable/OCR-required failure, document classification, final result payload assembly

**Current disposition:** baseline-locked in first integrated pass

Reason:
- result payload is a broad contract surface,
- selector may indirectly influence some fields through `visual_page_refs` and page summaries,
- but the structure and non-visual behavior should remain locked.

## First-pass seam interpretation

The safest current interpretation is:

- **Shared-evidence candidate region:** Zone B
- **Primary selector-owned region:** Zone F
- **Baseline-locked regions:** Zones A, C, D, E, G structure, H

## What this does *not* settle yet

This document does **not** freeze:
- whether Zone B is merely observed or partially refactored in pass 1,
- whether selector receives raw page + quality state or a more formal evidence object,
- the final function/interface shape for the selector.

It only reduces ambiguity about where the seam pressure really is in the live owner file.

## Minimum freeze rule derived from this map

Any first-pass selector/bootstrap proposal that reaches into:
- OCR fallback (Zone C),
- hybrid OCR (Zone D),
- page-source accounting (Zone E),
- final result assembly (Zone H),
without an explicit scope re-decision is too broad.


## Closure after this revision

The line-based candidate map is now promoted into an exact seam specification by:
- `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`

So the first-pass seam is no longer only “candidate.”
It is now frozen at the helper-contract level.
