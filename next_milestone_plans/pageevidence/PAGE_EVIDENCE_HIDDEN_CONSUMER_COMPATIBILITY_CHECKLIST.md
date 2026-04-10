# PageEvidence Hidden-Consumer Compatibility Checklist

## Purpose

Provide an explicit compatibility checklist for hidden or downstream consumers touched by PageEvidence-related fields, artifacts, or derived meanings.

This document exists because PageEvidence strengthening may appear local while still affecting:

- content indexing
- retrieval
- evidence bundles
- review surfaces
- report/export/package persistence
- diagnostics refs
- and workbench/report readers

No strengthening lane should claim no-drift without explicitly checking these surfaces.

This checklist is complementary to, not a substitute for:

- `PAGE_EVIDENCE_BLAST_RADIUS_AND_BEFORE_AFTER_TOPOLOGY.md`

---

## How to use this checklist

For each surface below, mark one of:

- `Unaffected`
- `Inspected and compatible`
- `Requires compatibility handling`
- `Requires widening / blocked`

If a surface is marked anything other than `Unaffected` or `Inspected and compatible`, the execution packet widening rules must be consulted before implementation proceeds.

---

## Checklist

### 1. Core ingestion / indexing chain

- [ ] `backend/app/services/nrc_aps_artifact_ingestion.py`
- [ ] `backend/app/services/nrc_aps_content_index.py`

Questions:
- Does the strengthening lane change any field shape or derived meaning these surfaces assume?
- Are diagnostics payloads or stored refs still compatible?

### 2. Model / schema surfaces

- [ ] `backend/app/models/models.py`
- [ ] `backend/app/schemas/api.py`
- [ ] `backend/app/schemas/review_nrc_aps.py`

Questions:
- Does any field name, meaning, or expectation change?
- Is any compatibility bridge needed?

### 3. Retrieval plane surfaces

- [ ] `backend/app/services/aps_retrieval_plane.py`
- [ ] `backend/app/services/aps_retrieval_plane_read.py`
- [ ] `backend/app/services/aps_retrieval_plane_contract.py`
- [ ] retrieval contracts/canonicalizers involving `visual_page_refs` or related persisted payload fields

Questions:
- Do retrieval-row constructors/deserializers assume existing shape or meaning?
- Do retrieval canonicalizers assume a stable serialized form for `visual_page_refs`?
- Is additive-only change sufficient?

### 4. Evidence bundle surfaces

- [ ] `backend/app/services/nrc_aps_evidence_bundle.py`
- [ ] `backend/app/services/nrc_aps_evidence_bundle_contract.py`

Questions:
- Do bundle items or contract shaping assume current PageEvidence-related field structure?
- Are strengthened fields internal-only or must they be tolerated here?

### 5. Review/runtime surfaces

- [ ] `backend/app/services/review_nrc_aps_runtime.py`
- [ ] `backend/app/services/review_nrc_aps_document_trace.py`
- [ ] `backend/app/api/review_nrc_aps.py`
- [ ] review service / API consumers of visual-page-related fields

Questions:
- Does strengthening PageEvidence alter any review-visible field meaning?
- Do document-trace or visual-artifact readers assume the current `visual_page_refs` structure or persisted artifact refs?
- Is the current retained-default visibility posture unaffected?

### 6. Report / export / package surfaces

- [ ] `backend/app/services/nrc_aps_evidence_report.py`
- [ ] `backend/app/services/nrc_aps_evidence_report_export.py`
- [ ] `backend/app/services/nrc_aps_evidence_report_export_package.py`

Questions:
- Do these surfaces read, persist, or indirectly depend on strengthened artifact shapes through indexed/bundled payloads?
- Does the lane require compatibility handling for persisted report refs or package composition?

### 7. Workbench artifact readers / validators

- [ ] tests or tools that parse `aps.page_evidence.v1`
- [ ] tests or tools that parse `aps.page_evidence_workbench_report.v1`
- [ ] planning docs that cite the pinned Candidate A workbench artifact

Questions:
- Can the existing pinned artifact remain historical truth?
- Does the strengthened lane need a new schema/version or a dual-output transition?

### 8. Selector / admitted-behavior compatibility

- [ ] `backend/app/services/nrc_aps_document_processing.py`
- [ ] tests covering `candidate_a_page_evidence_v1`
- [ ] any doc or test that assumes current admitted Candidate A behavior

Questions:
- Is the lane Lane Class A or Lane Class B?
- If Lane Class B, has the selector-semantics / behavior-drift policy been satisfied?

---

## Required summary section for implementation record

Any strengthening implementation record should include a condensed version of this checklist showing:

- surfaces checked
- status of each surface
- whether compatibility handling was needed
- whether any widening was triggered


## Completion rule

The strengthening lane should not be described as no-drift or compatible unless each relevant checklist item is marked as:

- unchanged by construction
- explicitly revalidated
- or explicitly excluded with justification

A skipped item without justification is not acceptable closure.
