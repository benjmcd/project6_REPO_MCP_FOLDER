# 00K Residual App-Surface Consumer and Visibility Closure Report

## Purpose

Close the final residual open item from earlier revisions:
whether there were still meaningful live app-surface consumer/visibility surfaces not yet enumerated.

## Verified residual live app-surface consumers

The remaining residual surfaces are now explicitly identified.

### 1. ORM / storage model layer
`backend/app/models/models.py`
- stores `visual_page_refs_json` on document-oriented rows

Implication:
- visual-lane outputs are persisted structurally in the ORM model layer

### 2. API/schema layer
`backend/app/schemas/api.py`
- exposes `visual_page_refs` fields in API schemas

Implication:
- visual-lane outputs are represented in API-facing schema objects

### 3. Retrieval-plane rebuild / canonical row layer
`backend/app/services/aps_retrieval_plane.py`
- includes `visual_page_refs_json` in canonical retrieval-row construction

### 4. Retrieval-plane readback layer
`backend/app/services/aps_retrieval_plane_read.py`
- deserializes `visual_page_refs`
- returns them in retrieval-row payloads

Implication:
- visual-lane outputs are not only stored; they are re-exposed through retrieval-plane reading

### 5. Evidence-bundle layer
`backend/app/services/nrc_aps_evidence_bundle.py`
- includes deserialized `visual_page_refs` in bundle items

### 6. Evidence-bundle contract layer
`backend/app/services/nrc_aps_evidence_bundle_contract.py`
- shapes/retains `visual_page_refs` in contract outputs

### 7. Already-verified downstream visibility layers
Already closed in earlier revisions:
- review/catalog/API
- report/export/package
- diagnostics persistence
- runtime DB binding/discovery

## Net conclusion

Within the current live app-surface authority scope, the residual consumer/visibility picture is now materially closed.

The visual-lane output path is represented across:

- owner processing
- artifact-ingestion adapter
- content index
- ORM persistence
- API schemas
- retrieval-plane rebuild/read
- evidence bundle + contract
- review/catalog/API
- report/export/package
- diagnostics persistence
- runtime DB binding/discovery

## What this closure means

It means there is no longer a material planning-level unknown about where visual-lane outputs and visibility concerns live in the current live app surface.

## What this closure does not mean

It does not mean:
- implementation may ignore those surfaces
- or that non-authority/archive/worktree areas were exhaustively audited

It means the control pack’s in-scope live authority surface is now sufficiently enumerated for planning and controlled implementation.
