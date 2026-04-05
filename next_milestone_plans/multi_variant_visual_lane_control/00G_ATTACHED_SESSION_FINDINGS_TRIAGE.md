# 00G Attached Session Findings Triage

## Purpose

Record which findings from the attached external session should tighten the control model, and how much trust they should receive.

## Evidence class used here

These findings are treated as:

- **Session-origin repo evidence**
- useful and material
- but not automatically equivalent to direct live re-verification in the current pass

Therefore each finding below is classified as one of:
- **Already aligned with current pack**
- **Material tightening**
- **Still provisional / needs live re-check**

---

## 1. `document_type` threading through the processing path

### Session-origin claim
The session reports that:

- `connectors_nrc_adams.py` builds `extraction_config`
- `run.request_config_json` flows into that config
- `_process_pdf(...)` consults `config.get("document_type")` for advanced-doc routing
- `target.source_reference_json["aps_normalized"]["document_type"]` exists as an upstream source, but is not currently injected into processing config

### Current status in this pack
**Material tightening, but still partly provisional**

Why:
- it fits the already verified config-path model,
- it plausibly explains how future selector-like routing could piggyback on an existing document-type signal,
- but the full threading claim has not been re-verified directly in the current pass.

### Control implication
Treat this as a candidate activation/control surface, not a closed implementation fact.

---

## 2. Boundary option: post-classification / pre-artifact seam

### Session-origin claim
The session recommends a narrow first-pass seam centered on:
- visual significance,
- visual classification,
- conditional visual artifact writing,
while excluding:
- OCR fallback,
- hybrid OCR,
- summary aggregation.

### Current status in this pack
**Already aligned with current pack**

Why:
- this closely matches the line-based seam map and blocker logic already in the pack,
- it strengthens confidence that the visual-preservation zone is the leading first-pass seam candidate.

### Control implication
No redesign needed, but the pack should continue treating the OCR/visual edge as a blocker until formally frozen.

---

## 3. Separate `storage_dir` is not enough for full out-of-band isolation

### Session-origin claim
The session reports that:
- runtime-root discovery is additive,
- review/catalog discovery finds runs from all roots,
- shared DB visibility means baseline-facing surfaces can still see experiment runs,
- therefore experiments are not truly “out-of-band” merely by using separate runtime/artifact roots.

### Current status in this pack
**Material tightening**

Why:
- this corrects an important residual optimism in earlier packs,
- it makes clear that runtime-root isolation alone does not imply review/catalog/report invisibility.

### Control implication
The pack must treat “out-of-band experiments” as requiring more than:
- separate `storage_dir`
- separate `artifact_storage_dir`

It must explicitly baseline-lock:
- review/runtime discovery,
- catalog visibility,
- shared run/report surfaces,
unless and until a later explicit reopening occurs.

---

## 4. Review discoverability through catalog/runtime surfaces

### Session-origin claim
The session points to:
- `review_nrc_aps_catalog.py`
- discovery of runtime bindings across roots
- lack of namespace filtering
as a reason baseline-facing review can still see experiment runs.

### Current status in this pack
**Material tightening, still needs direct re-check**

Why:
- this is plausible and important,
- but the exact live catalog behavior has not yet been re-read directly in the current pass.

### Control implication
Add review/catalog visibility as an explicit blocker rather than leaving it implied under generic review/runtime language.

---

## 5. Report/export visibility through shared ConnectorRun surfaces

### Session-origin claim
The session reports that report/export surfaces read `ConnectorRun` from shared DB-backed state, so even with separate report directories, run visibility itself may still be shared.

### Current status in this pack
**Material tightening, still needs direct re-check**

Why:
- this is consistent with the broader shared-DB concern,
- but the exact file/line behavior has not yet been re-verified in the current pass.

### Control implication
The pack should explicitly treat shared run/report/export visibility as a blocker for any claim that experiments are fully isolated.

---

## 6. Net effect on the control model

The most important impact of the attached session is:

**the phrase “experiments remain out-of-band initially” was still too weak unless it explicitly excludes review/catalog/report visibility, not just runtime-root and artifact collisions.**

That is the main tightening adopted in this revision.


---

## 7. Exact direct caller map reported by the session

### Session-origin claim
The session reports exactly two direct callers for `process_document(...)`:
- internal ZIP recursion in `nrc_aps_document_processing.py`
- `nrc_aps_artifact_ingestion.extract_and_normalize(...)`

It also reports near-direct consumers through:
- `connectors_nrc_adams.py`
- `nrc_aps_content_index.py`

### Current status in this pack
**Material corroboration**

### Control implication
This strengthens confidence that the current pack is centered on the right minimum non-owner live surfaces, even if full caller closure is still open.

## 8. Review API endpoint exposure

### Session-origin claim
The session reports a broader review API exposure surface including:
- visual artifacts
- diagnostics
- normalized text
- indexed chunks
- extracted units
- document trace

### Current status in this pack
**Material tightening**

### Control implication
This justifies elevating API-facing exposure as a distinct baseline-lock concern rather than subsuming it under generic review/runtime wording.
