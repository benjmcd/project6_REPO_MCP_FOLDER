# 00F Live Repo Verified Facts and Open Items

## Section index

- **Section A** - Verified live facts (sequentially numbered, no duplicates)
- **Section B** - Inferred design implications
- **Section C** - Closure-state determinations
- **Section D** - Bounded residuals and next-lane open items
- **Section E** - Proceed position

---

## A. Verified live facts

### A.1 Core architecture

1. `nrc_aps_document_processing.py` is central.
2. `process_document(...)` routes by media type.
3. `_process_pdf(...)` contains OCR fallback, hybrid OCR, visual-preservation, artifact writing, and summary logic together.
4. Active visual classes are:
   - `diagram_or_visual`
   - `text_heavy_or_empty`
5. `_has_significant_visual_content(page)` uses image `>=100x100` or drawings `>=20`.
6. OCR fallback separately uses image-only significance.
7. `default_processing_config(...)` exists.
8. `nrc_aps_artifact_ingestion.py` directly imports and calls document-processing.
9. `processing_config_from_run_config(...)` forwards processing overrides into `default_processing_config(...)`.
10. `connectors_nrc_adams.py` calls `nrc_aps_artifact_ingestion.extract_and_normalize(...)`.
11. `nrc_aps_content_index.py` calls `nrc_aps_artifact_ingestion.extract_and_normalize(...)`.
12. `nrc_aps_content_index.py` rebuilds diagnostics payloads including `visual_page_refs` and writes diagnostics blobs.

### A.2 Runtime and review discovery

13. `review_nrc_aps_runtime.get_allowlisted_roots()` explicitly includes:
    - `backend/app/storage_test_runtime/lc_e2e`
    - `backend/storage_test_runtime/lc_e2e`
14. The same discovery path appends a normalized configured `settings.storage_dir` only when it resolves to a baseline-style root ending in `/storage/lc_e2e` or `/storage_test_runtime/lc_e2e`; differently named configured roots are no longer baseline allowlisted directly.
15. `review_nrc_aps_runtime.discover_review_roots()` scans those allowlisted bases for summary-backed directories, and `discover_runtime_bindings()` now filters discovered bindings by the canonical run-level visibility signal from `ConnectorRun.request_config_json["visual_lane_mode"]` when a runtime DB row exists.
16. `review_nrc_aps_catalog._load_connector_run(binding)` remains best-effort and may return `None`; summary-backed historical roots that lack a `ConnectorRun` row remain baseline-visible for backward compatibility.

### A.3 Test roots and verified tests

17. Two live test roots exist:
    - `tests/`
    - `backend/tests/`
18. `backend/tests/test_nrc_aps_run_config.py` verifies preserved processing overrides.
19. `backend/tests/test_visual_artifact_pipeline.py` verifies artifact existence, file SHA-256, artifact metadata, and content-index roundtrip behavior.
20. `backend/tests/test_review_nrc_aps_catalog.py` verifies summary-backed candidate run discovery and stable default-run selection.
21. `backend/tests/test_diagnostics_ref_persistence.py` verifies diagnostics-ref persistence and cross-run safety.
22. `backend/tests/test_review_nrc_aps_document_trace_api.py` and `backend/tests/test_review_nrc_aps_document_trace_service.py` verify run-scoped review-root resolution, read-only runtime DB-backed trace access, path safety, and missing-layer handling against an audited `lc_e2e` runtime.

### A.3a Root-live correction

The focused workspace root now contains:
- `review_nrc_aps_runtime_roots.py`
- `candidate_review_runtime_roots(...)`
- `review_nrc_aps_runtime_db.py`
- `runtime_db_session_for_run(...)`
- `backend/tests/test_review_nrc_aps_runtime_db.py`

Current root-live review/runtime authority includes:
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- run-bound review routes in `backend/app/api/review_nrc_aps.py`
- runtime DB review tests in `backend/tests/test_review_nrc_aps_runtime_db.py`
- document-trace review tests under `backend/tests/test_review_nrc_aps_document_trace_*.py`

Current validation caveat:
- this clean worktree does **not** carry its own `backend/app/storage_test_runtime/lc_e2e` fixture tree
- clean-worktree review/runtime validation now auto-aligns read-only to the shared audited runtime root under the repo root through `backend/tests/review_nrc_aps_runtime_fixture.py`
- grouped T8 review/runtime acceptance currently passes under the canonical repo-root `pytest` posture without seeding new runtime data

### A.4 Control-key and packaging surface

23. `connectors_nrc_adams._normalize_request_config(...)` has an explicit `control_keys` exclusion set for lenient pass-through mode.
24. Root `package.json` exists but has no scripts.
25. No live `pytest` references were found in the scanned root/docs/backend/tests/tools surfaces during this pass.

### A.5 Review/catalog/API visibility surface

26. `review_nrc_aps_catalog.discover_candidate_runs()` enumerates already-filtered visible runtime bindings, loads `ConnectorRun` rows when available, and still allows summary-backed candidates without a `ConnectorRun` row.
27. `backend/app/api/review_nrc_aps.py:get_runs()` returns `discover_candidate_runs()` directly.
28. `backend/app/api/review_nrc_aps.py:get_run_documents()`, `get_document_trace()`, `get_document_source()`, `get_document_visual_artifact()`, `get_document_diagnostics()`, `get_document_normalized_text()`, `get_document_indexed_chunks()`, and `get_document_extracted_units()` all gate through `runtime_db_session_for_run(run_id)`, which first resolves a runtime binding by `run_id`.
29. `backend/app/api/review_nrc_aps.py` run-bound overview/tree/node/file-detail/file-preview surfaces gate through `find_review_root_for_run(run_id)`.
30. Default review/catalog/API discoverability is therefore driven by discovered runtime bindings that now enforce the canonical baseline-visible classification before selector exposure or direct run-bound review access.
31. Baseline-facing direct `run_id` access is now controlled on both sides: discovered runtime-binding paths filter hidden runs as absent, and direct run-bound report/export persistence paths separately fail closed when the owning `ConnectorRun` is experiment-hidden.

### A.6 Report/export run-bound persistence

32. `nrc_aps_evidence_report.py` derives `run_id` from persisted source payloads, resolves `ConnectorRun` via `_candidate_run(db, run_id)`, and now refuses `persist_report` for experiment-hidden runs before shared ref/summarized writes into `run.query_plan_json`.
33. `nrc_aps_evidence_report_export.py` derives `run_id` from persisted source report payloads, resolves `ConnectorRun`, and now refuses `persist_export` for experiment-hidden runs before shared writes into `run.query_plan_json`.
34. `nrc_aps_evidence_report_export_package.py` resolves `owner_run_id`, rejects cross-run package composition in v1, resolves `ConnectorRun`, and now refuses `persist_package` for experiment-hidden runs before shared writes into `run.query_plan_json`; `connectors_sciencebase.py` later merges only persisted report-ref keys outward.

### A.7 Direct backend caller closure

35. Exact backend search for `process_document(` found only:
    - the owner definition,
    - ZIP recursion inside the owner,
    - and the direct call from `nrc_aps_artifact_ingestion.py`.
36. Exact backend search for `extract_and_normalize(` found only:
    - the owner definition in `nrc_aps_artifact_ingestion.py`,
    - the call from `connectors_nrc_adams.py`,
    - and the call from `nrc_aps_content_index.py`.

### A.8 Negative evidence (runner/benchmark)

37. Exact search for `benchmark` across scanned authority surfaces returned no hits.
38. Exact search for `perf` across scanned authority surfaces returned no hits.
39. No `pytest.ini`, `conftest.py`, `tox.ini`, `noxfile.py`, or `Makefile` was found at repo level in the current pass.

### A.9 Narrowed app-surface consumer closure

40. Exact search for `extract_and_normalize(` limited to `backend/app/**/*.py` found only:
    - the owner definition in `nrc_aps_artifact_ingestion.py`
    - the call in `connectors_nrc_adams.py`
    - the call in `nrc_aps_content_index.py`
41. Exact search for `nrc_aps_artifact_ingestion` in `backend/app/**/*.py` confirms the major live app-surface consumers are connectors, content index, and artifact-ingestion gate, with other downstream effects already covered by separate review/report/runtime blocker docs.

### A.10 Test framework evidence

42. `tests/test_nrc_aps_document_processing.py` directly uses `import pytest`, `@pytest.mark.parametrize`, `pytest.raises`, and the `monkeypatch` fixture.
43. `backend/tests/test_nrc_aps_run_config.py` directly uses `import unittest` and `unittest.TestCase`.

### A.11 Test path bootstrap evidence

44. `backend/tests/test_review_nrc_aps_document_trace_page.py` explicitly inserts `Path(__file__).resolve().parents[1]` into `sys.path` before importing `main`.
45. `backend/tests/test_nrc_aps_run_config.py` imports `app.services...` without explicit backend path insertion.

### A.12 Fixture root evidence

46. `tests/test_nrc_aps_document_processing.py` provides a lightweight deterministic fixture root at `tests/fixtures/nrc_aps_docs/v1` and actively exercises `born_digital.pdf`, `mixed.pdf`, and `scanned.pdf`.
47. `backend/tests/test_visual_artifact_pipeline.py` provides a heavier artifact-aware fixture declaration using `handoff/tests/fixtures/nrc_aps_docs/v1` and `data_demo/nrc_adams_documents_for_testing`, with a listed real-ADAMS subset.

### A.13 Config chain and seam evidence

48. `processing_config_from_run_config(...)` forwards only an explicit whitelist of processing controls into `default_processing_config(...)`.
49. `default_processing_config(...)` provides defaults by key update and does not itself normalize enum-like selector controls.
50. `_normalize_request_config(...)` already uses safe-default fallback for several enum-like controls (`mode`, `wire_shape_mode`, `run_mode`, `report_verbosity`, `sync_mode`).
51. `_process_pdf(...)` visual-preservation lane now begins with local `visual_lane_mode` fail-closed normalization after page-source accounting and before `all_units.extend(page_units)`, which is the current first owner-path consumption zone for `visual_lane_mode`.
52. `_normalize_request_config(...)`, `processing_config_from_run_config(...)`, and `default_processing_config(...)` together form a complete request->processing->owner path suitable for canonical selector-key propagation.

### A.14 Seam decomposition

53. The visual-preservation lane already decomposes into four concrete helpers: `_has_significant_visual_content`, `_classify_visual_page`, `_capture_visual_page_ref`, and `_write_visual_page_artifact`.
54. The exact first-pass seam is now frozen as the visual-preservation lane after page-source accounting and before page-summary accumulation, with inputs limited to `page`, `page_number`, `pre_branch_native_quality_status`, and `config`.

### A.15 Model/schema/retrieval/evidence chain

55. `backend/app/models/models.py` stores `visual_page_refs_json` on document-oriented rows.
56. `backend/app/schemas/api.py` exposes `visual_page_refs` fields in API schemas.
57. `backend/app/services/aps_retrieval_plane.py` includes `visual_page_refs_json` in canonical retrieval-row construction.
58. `backend/app/services/aps_retrieval_plane_read.py` deserializes and returns `visual_page_refs` in retrieval-row payloads.
59. `backend/app/services/nrc_aps_evidence_bundle.py` includes deserialized `visual_page_refs` in bundle items.
60. `backend/app/services/nrc_aps_evidence_bundle_contract.py` retains `visual_page_refs` in contract shaping.
61. `backend/app/schemas/review_nrc_aps.py` includes `NrcApsReviewVisualArtifactItemOut.visual_page_class`, confirming an additional review-schema exposure surface.

### A.16 Workflow, migration, and enforcement surface

62. Root workflow surface `.github/workflows/playwright.yml` exists and appears Playwright/UI-oriented.
63. `backend/migration_compat.py` provides explicit Alembic migration-compat helpers.
64. `tools/migrate_sqlite_to_postgres.py` provides repo-native SQLite->Postgres migration tooling.
65. `backend/alembic/versions/0010_visual_page_refs_json.py` explicitly adds `visual_page_refs_json`.
66. `backend/alembic/versions/0011_aps_retrieval_chunk_v1.py` carries `visual_page_refs_json` into retrieval-chunk schema evolution.
67. Exact root workflow search found exactly one repo-native root workflow: `.github/workflows/playwright.yml`.
68. File search found no repo-native `pre-commit` surface.
69. Exact search for `pytest` across repo-native workflow/config/hook files checked (`.github/**/*`, pre-commit-like files, `Makefile`, `tox.ini`, `noxfile.py`, `package.json`) returned no hits.

### A.17 Extended schema/contract evidence

70. `backend/app/schemas/api.py` includes `visual_page_refs` fields.
71. `backend/app/services/aps_retrieval_plane_contract.py` includes `visual_page_refs_json` handling and `canonicalize_visual_page_refs(...)`.
72. `backend/app/services/nrc_aps_evidence_bundle_contract.py` retains `visual_page_refs`.
73. `backend/app/schemas/review_nrc_aps.py` includes `visual_page_class`, but `visual_page_class` was not broadly found across the contract files checked.

### A.18 Roundtrip test evidence

74. `backend/tests/test_nrc_aps_advanced_adapters.py` proves `visual_page_class` survives JSON persist -> deserialize -> API response roundtrip within `visual_page_refs`.
75. `backend/tests/test_nrc_aps_evidence_bundle_integration.py` proves evidence-group output accepts `visual_page_class` nested inside `visual_page_refs`.

### A.19 Non-app surface checks

76. Exact searches in `tools/**/*.py` found no `visual_page_refs` or `visual_page_class` consumers.
77. Exact searches in checked live root/docs/helper-script surfaces (`README.md`, `REPO_INDEX.md`, `docs/**/*`, `run_*.py`, `postreview_eval.py`, `corpus_diagnostics.py`) found no `visual_page_refs` or `visual_page_class` consumers.

### A.20 Worktree/archive surface

78. Direct file search in `worktrees/**/*.py` for `nrc_aps_document_processing` found many duplicated worktree copies of the same service/test/tool paths.
79. Direct file search in `archive/**/*.py` for `nrc_aps_document_processing` found many duplicated archive copies under historical `.claude/worktrees/...` paths.

### A.21 M6B direct-admission implementation

80. `connectors_nrc_adams._normalize_request_config(...)` now preserves exactly `baseline` and `candidate_a_page_evidence_v1`, while fail-closing every other non-`baseline` `visual_lane_mode` value to `baseline`.
81. `nrc_aps_artifact_ingestion.processing_config_from_run_config(...)` still forwards `visual_lane_mode` and required no code widening for the M6B lane.
82. `nrc_aps_document_processing._normalize_visual_lane_mode(...)` now preserves exactly `baseline` and `candidate_a_page_evidence_v1`, while fail-closing every other value to `baseline`.
83. `nrc_aps_document_processing._run_candidate_a_visual_lane(...)` now exists and reuses `app.services.nrc_aps_page_evidence.analyze_pdf_page_evidence(...)` to derive a seam-local `has_visual` decision from deterministic PageEvidence image/drawing/coverage signals, then falls back to `_run_baseline_visual_lane(...)` if PageEvidence computation fails.
84. `review_nrc_aps_runtime.request_config_is_baseline_visible(...)` now treats `candidate_a_page_evidence_v1` as baseline-visible while still hiding every other explicit non-`baseline` value.
85. `backend/tests/test_review_nrc_aps_api.py` now proves both halves of the admitted-visibility rule:
   - `candidate_a_page_evidence_v1` is review-visible
   - unapproved values such as `variant_a` remain hidden
86. The required `05H` validation bundles and the mandatory `06I` local performance gate now pass in the current clean M6B worktree, with Tier 1 and the stronger artifact-aware Tier 2 comparison both staying within the frozen thresholds.

---

## B. Inferred design implications

These are planning inferences derived from verified facts, not repo facts by themselves.

1. First selector scope should remain PDF visual-lane only.
2. Selector control should align with existing run-config -> processing-config patterns.
3. Shared evidence should be introduced before whole-pipeline swapping.
4. Variant identity should stay internal-only initially.
5. Replay/promotion/review/report/export should remain baseline-only initially.
6. A/B/C should remain worktree-only until the seam is proven.
7. Experimental runtime outputs should remain out-of-band from baseline default review/runtime discovery.
8. Separate runtime/artifact roots are insufficient for full isolation if review/catalog/API surfaces still enumerate or expose experiment runs by `run_id`.
9. Separate runtime/artifact roots are also insufficient if shared run-bound report/export surfaces still resolve and persist artifacts by shared `run_id` / `owner_run_id`.
10. Diagnostics-ref persistence semantics must remain baseline-locked initially.
11. Runtime DB binding/discovery semantics must remain baseline-locked initially.
12. Selector activation mechanism must remain consistent with the already-frozen selector activation/control docs and must not be widened during implementation.
13. OCR fallback and hybrid OCR remain baseline-locked outside the frozen visual-lane seam in the first integrated phase.
14. Experiment isolation must continue to satisfy the already-frozen isolation/visibility constraints and must not be reduced to runtime-root separation alone.
15. Any future selector key must be treated as a processing control and prevented from leaking into query payload surfaces.
16. The strongest live candidate for baseline-facing visibility control is the already-persisted `ConnectorRun.request_config_json["visual_lane_mode"]` slot, with backward-compatible allowance for summary-backed historical runs that lack a `ConnectorRun` row.

---

## C. Closure-state determinations

Items that have been planning-closed or narrowed to explicit remaining scope.

1. **Baseline-only selector/bootstrap path:** CLOSED through M4. `visual_lane_mode` is normalized, forwarded, defaulted, fail-closed, and first-consumed at the frozen visual-preservation seam. T1-T8 and the local `06I` gate were executed for the merged baseline path. Later experiment coexistence/visibility work remains separate scope.
2. **Seam boundary:** CLOSED by exact helper-contract freeze (`03W`) and retained for future later-scope work. Future experiment work remains bounded to the same seam and does not reopen OCR/hybrid zones.
3. **Acceptance command convention:** CLOSED and live-executed in the clean merged-main worktree. Shell-specific realizations for PowerShell, CMD, and POSIX are frozen in `06K`. Repo-native enforcement is not yet implemented.
4. **Residual consumer/visibility closure beyond live app-surface chain:** CLOSED for the merged baseline-only bootstrap path. Residual app-surface consumers are explicitly enumerated across models, schemas, retrieval-plane, evidence-bundle, review, and report/export layers.
5. **Validation harness operability for baseline-only bootstrap:** CLOSED. The grouped T1-T8 bundles and the local performance gate are operational and recorded in the clean merged-main worktree.
6. **Standalone review/report/export field-sensitivity map:** CLOSED as `03Y`. The field-level exposure inventory is now explicit, so the remaining later-scope work is the coexistence/visibility mechanism itself, not discovery of which baseline-facing fields matter.
7. **Exact M5 execution packet boundary:** CLOSED as `05F`, and the bounded implementation stayed within the default owner set with no widening.
8. **Exact M5 coexistence / visibility mechanism:** CLOSED by freeze-and-implementation. `03Z` froze the mechanism, and merged `main` now implements the baseline-facing root-placement, runtime-binding visibility filter, and run-bound report/export/package persistence guards recorded in `05G`.
9. **Exact M6 planning/freeze packet boundary:** CLOSED as planning input. `03AA` now freezes the direct admission/promotion mechanism, and `05H` now freezes the owner boundary, validation boundary, widening rules, and fail-closed stop conditions for the later direct-admission lane.
10. **Exact M6A workbench planning/freeze packet boundary:** CLOSED as planning input. `03AB` freezes the dedicated PageEvidence / Option 2 workbench boundary, and `05I` freezes the owner boundary, validation packet, location strategy, widening rules, and fail-closed stop conditions for the immediate workbench lane.
11. **Exact M6A workbench implementation:** CLOSED on merged `main`. The dedicated PageEvidence service, standalone runner, bounded validation bundle, no-drift findings, and pinned canonical Candidate A workbench report artifact are now recorded in `05J` without widening into the integrated owner path.
12. **Exact approved M6B target naming:** CLOSED on merged `main`. `05L` records one exact approved non-`baseline` selector value, its provenance, its comparison/evidence refs, its required invariants, and its explicit approval record without widening direct-admission scope.
13. **Exact M6B direct-admission implementation:** CLOSED on merged `main`. The one approved Candidate A value is now admitted through the integrated owner path, the required `05H` validation bundles passed, `06I` was rerun and passed, no conditional owner-file widening was required, and the achieved implementation remains recorded in `05M`.
14. **Exact M6B merged-main closure and handoff:** CLOSED in this reconciliation lane. `05N` now records that PR `#21` merged the achieved M6B lane into `main` on April 8, 2026 and that any broader post-admission/defaulting work requires a separate explicit freeze.
15. **Exact post-admission/defaulting planning freeze boundary:** CLOSED in this lane. `03AC` and `05O` now freeze the exact later-scope planning boundary, decision questions, owner surfaces to consider, dependency posture, prohibited widenings, and allowed next outcomes without authorizing new code by inference.
16. **Exact current-horizon retain-`baseline`-default decision:** CLOSED in this lane. `05P` now records that the current `00D` baseline-default rule remains in force for the current horizon, that Candidate A remains admitted but non-default, and that no default-promotion or additional-candidate lane opens without a separate explicit program-decision amendment.

---

## D. Bounded residuals and next-lane open items

Items that remain genuinely open or bounded.

1. **Tier 2 performance sample breadth:** The local performance gate was executed and passed, but the recorded artifact-aware Tier 2 comparison still uses the declared-root handoff fallback sample because the preferred real-ADAMS timed capture exceeded practical local session budget.
2. **Broader residual consumer/visibility effects:** Residual effects beyond the already-verified live app-surface chain remain bounded but not zero. Mostly duplicated worktree/archive state and non-audited/generated surfaces.
3. **Repo-native Python enforcement:** The Python acceptance path is pack-specified (`06J`, `06K`) but not visibly repo-enforced in the root workflow/hook/config surfaces checked.
4. **Broader future default-promotion / additional-candidate scope:** Still later-scope. `05P` now explicitly retains `baseline` as the default for the current horizon, but any future attempt to amend that rule, promote Candidate A to default, admit Candidate B/C, reopen OCR-routing/media scope, or authorize further variant work still requires a separate explicit decision record beyond `03AC` + `05O` + `05P`.

---

## E. Proceed position

### Recommended stop condition

At the current evidence level, the next justified operational move is no longer more M6B implementation work, no longer review/merge of the achieved Candidate A lane, no longer opening the post-admission/defaulting planning freeze itself, and no longer deciding whether to retain `baseline` as the default for the current horizon. That decision is now frozen explicitly in `05P`.
Repo-native Python enforcement remains a valid parallel hardening lane. Any future MVVLC widening would first require a separate explicit program-decision amendment and later target-definition record rather than a new implementation lane by inference.

### Current proceed position

Proceeding is justified with the current retained-default closure state: the achieved M5 barrier closure, the achieved M6A workbench record and pinned canonical report artifact in `05J`, the frozen approved target record in `05L`, the achieved M6B implementation record in `05M`, the merged-main closure/handoff in `05N`, the frozen `03AC` + `05O` planning packet, the retained-default decision in `05P`, and the frozen `03AA` + `05H` packet as the already-completed admission boundary.
Baseline-only bootstrap closure, the later-scope M5 barrier closure, the standalone M6A workbench lane, the exact Candidate A approved-target freeze, the merged-main M6B implementation, the merged-main closure/handoff, and the current-horizon retain-`baseline` decision remain accepted; the remaining uncertainty is bounded, explicit, and concentrated on any future attempt to reopen broader post-admission scope rather than on the current admitted Candidate A lane itself.
