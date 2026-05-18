# Source Directory Package Supersession Preview Runtime Entry Freeze

## Current-main authority

- Predecessor current-main sync: `next_milestone_plans/Layer3_planning_docs/819_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_STATUS_RUNTIME_CURRENT_MAIN_SYNC.md`
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_qualitative_hybrid_analysis_status_sync`
- Runtime branch: `codex/l3-next-gap-after-analysis-status-sync`
- Current-main preflight checkpoint: `8c147cf2e25d69f3e5160bab23639ced379a73f7`

## Selected runtime slice

Admit one source-directory package lifecycle and mutation/reconstruction reader:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`
- Schema: `layer3.source_directory_qualitative_analysis_package_supersession_preview.v1`
- Mode: `source_directory_qualitative_analysis_package_supersession_preview_authority`
- Source gate: `820_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_ENTRY_FREEZE`
- Required upstream authority: existing source-directory package construction plus approved package-review submit authority.

The route recomputes and validates the current source-directory qualitative-analysis authority, package-review preview hash, construction basis, approved submit record, and immutable package set. It returns only redacted package-set and downstream dependency hashes plus bounded downstream state summaries.

## Admitted behavior

- Read-only source-directory package supersession preview.
- Source package-set hash over existing package ids, package kinds, and payload hashes.
- Downstream dependency hash over approved package-review submit, handoff/export prepare if present, and external export/download prepare if present.
- Bootstrap/readiness exposure for the exact source-directory supersession preview route.
- Fail-closed mismatch handling for stale qualitative-analysis, package-preview, construction-basis, submit-record, package-state, and package-set inputs.

## Not admitted

- Replacement package-set authority.
- Supersession commit.
- Source `L3OutputPackage` row mutation.
- Package payload write or rewrite.
- Source package row mutation.
- Provider-public or signed URL delivery.
- Connector dispatch, credentials, destination writes, or network egress.
- New source family expansion.
- RAG/vector indexing expansion.
- Frontend durable authority or rendered controls.

## Proof requirements

- Compile changed API, service, contract, and targeted tests.
- Prove the new route returns stable preview hashes and redacted downstream dependencies.
- Prove stale package-set input fails closed.
- Prove no connector rows or extra package rows are written by the preview.
- Re-run source-directory qualitative-analysis tests plus bootstrap/readiness tests.
- Re-run `tools/l3-progress-check.py` and `tools/l3-target-selection-validate.py --expect frozen`.

## Next posture

After merge and current-main sync, select the next named Layer 3 end-to-end gap. Do not continue same-family source-directory package supersession preview loops unless current-main evidence names a concrete unresolved defect or a named downstream reader.
