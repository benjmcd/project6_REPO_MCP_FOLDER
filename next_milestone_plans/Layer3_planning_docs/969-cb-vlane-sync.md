# 969 - Candidate B Visual-Lane Current-Main Sync

## Purpose

Record the current-main Candidate B visual-lane implementation and add a regression-check target for the landed behavior.

This is a sync/proof guard only. It introduces no runtime, route, DTO, model, migration, rendered UI, parser, provider, connector, auth/security, source-expansion, RAG/vector/model, browser-storage, frontend-only durable-authority, or full-mockup behavior change.

## Current-Main Authority

Current main `2df6e31adc8eda24bd27a964e344b80cfcf93b5b` includes the Candidate B default-selector and visual-lane chain:

- PR `#1610` promoted Candidate B as the omitted-engine default for eligible PDF/corpus processing only.
- PR `#1611` froze Candidate B visual-lane admission.
- PR `#1612` implemented explicit Candidate B visual-lane admission.
- PR `#1613` proved the Candidate B visual-lane runtime path.
- PR `#1654` guarded Candidate A against the Candidate B default selector.
- PR `#1655` exposed effective Candidate B runtime metadata.

## Synced Behavior

The admitted Candidate B visual-lane mode is:

```text
candidate_b_opendataloader_page_evidence_v1
```

Current main now recognizes that value as an explicit visual/page-evidence lane in these source-authority surfaces:

- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/review_nrc_aps_runtime.py`

The implementation preserves these relationships:

- omitted `visual_lane_mode` still resolves to `baseline`;
- invalid `visual_lane_mode` still fails closed to `baseline`;
- `candidate_a_page_evidence_v1` remains the admitted Candidate A lane and stays routed through baseline PDF processing when the processing engine is omitted;
- `candidate_b_opendataloader_page_evidence_v1` is explicit visual/page evidence, not an implicit default visual lane;
- omitted `document_processing_engine` still selects `candidate_b_opendataloader_pdf` only for eligible PDFs;
- explicit `document_processing_engine="baseline"` remains the rollback path;
- Candidate B bundle and runtime bridge authority stay distinct;
- Candidate B visual/page artifacts are retained evidence/product artifacts, not Layer 3 text-material payloads unless a separate material-ingestion slice admits them.

## Guarded Evidence

The progress checker now guards the minimum source and proof terms for the current-main Candidate B visual-lane state:

- Candidate B is admitted in the document-processing visual-lane allowlist.
- Candidate B is admitted in the APS connector visual-lane allowlist.
- Candidate B is visible in review runtime classification.
- Candidate A default-selector protection remains tested.
- Candidate B explicit visual-lane selection remains tested.
- Candidate B runtime bridge receipts preserve visual evidence counts and keep PDF/image material text ingestion disabled.
- Candidate B default-readiness blocks stale, missing, or baseline visual-lane evidence.

## Boundaries

This sync does not admit:

- Candidate B visual lane as an omitted/default visual lane;
- Candidate B default behavior beyond eligible PDF/corpus processing;
- Candidate A semantic changes;
- direct PDF, annotated-PDF, image, or arbitrary binary material ingestion into Layer 3 text analysis;
- broad runtime DB or storage ingestion;
- provider object writes;
- connector dispatch;
- RAG/vector/model runtime;
- auth/security changes;
- browser-storage authority;
- frontend-only durable authority;
- full mockup activation.

## Next Posture

The next Candidate B work should be selected from current-main evidence, not from the stale pre-implementation posture in `968-cb-visual-lane-admission.md`.

The highest-value remaining Candidate B direction is a requirement-by-requirement completion audit over the first-class path:

```text
candidate_b_first_class_path_completion_audit_v1
```

That audit should prove, with live source/test/operator evidence, whether Candidate B now fully satisfies the long-term path: eligible PDF/corpus default selection, explicit visual-lane evidence, retained artifact governance, Layer 3 material/analysis authority, package/review, handoff/export, delivery/internal-webhook/provider-private-redacted use, final operator inspection, rollback/fail-closed behavior, and default-promotion readiness.
