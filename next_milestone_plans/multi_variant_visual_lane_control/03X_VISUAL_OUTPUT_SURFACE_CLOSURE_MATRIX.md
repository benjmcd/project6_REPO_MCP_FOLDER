# 03X Visual Output Surface Closure Matrix

## Purpose

Summarize where visual-lane outputs now flow across the live app surface.

## Surface matrix

| Surface | Role | Verified signal |
|---|---|---|
| `nrc_aps_document_processing.py` | produces `visual_page_refs` | owner result payload |
| `nrc_aps_content_index.py` | persists / deserializes / republishes visual refs | `visual_page_refs_json`, diagnostics payload, response payload |
| `models.py` | stores visual refs in ORM | `visual_page_refs_json` fields |
| `schemas/api.py` | schema exposure | `visual_page_refs` fields |
| `aps_retrieval_plane.py` | canonical retrieval-row build | `visual_page_refs_json` canonicalization |
| `aps_retrieval_plane_read.py` | retrieval-row readback | `visual_page_refs` returned in payload |
| `nrc_aps_evidence_bundle.py` | bundle item assembly | deserialized visual refs included |
| `nrc_aps_evidence_bundle_contract.py` | bundle contract shaping | retains `visual_page_refs` |
| `review_nrc_aps_document_trace.py` | review trace consumption | deserializes and counts visual refs |
| `schemas/review_nrc_aps.py` | review schema exposure | `NrcApsReviewVisualArtifactItemOut.visual_page_class` |
| `review_nrc_aps_catalog.py` + `review_nrc_aps.py` | run visibility and run-bound exposure | previously verified |
| `nrc_aps_evidence_report*.py` | report/export/package visibility | previously verified |

## Closure statement

The visual output surface is now materially closed for the current live app authority scope.


## Correction after re-audit

This matrix is materially strong for the audited app surface, but should not be used as proof that no further surface drift risk exists anywhere in the repo.
