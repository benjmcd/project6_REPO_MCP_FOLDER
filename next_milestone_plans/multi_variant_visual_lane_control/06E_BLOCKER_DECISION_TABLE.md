# 06E Blocker Decision Table

## Purpose

Turn the remaining open items into explicit blocker decisions tied to live evidence.

## Status categories

Each row carries one of these explicit statuses:

- **TRUE CLOSURE** — Planning and evidence-level closure achieved. No further planning or implementation work required for this item.
- **PLANNING-CLOSED** — Planning freeze is complete. Implementation work remains before this item can be marked implementation-closed.
- **IMPLEMENTATION REQUIRED** — Specific implementation work is defined. The planning pack specifies what must be done, but the work itself is not yet done.
- **BOUNDED RESIDUAL** — Uncertainty is acknowledged, bounded, and carried explicitly. Not a blocker, but not zero.

---

## Blocker table

### TRUE CLOSURE

| Blocker | Status | Live evidence anchor | Notes |
|---|---|---|---|
| Exact `_process_pdf(...)` seam | TRUE CLOSURE | `_process_pdf(...)`; `_has_significant_visual_content`; `_classify_visual_page`; `_capture_visual_page_ref`; `_write_visual_page_artifact`; `03W` | First-pass seam frozen as visual-preservation helper-contract boundary after page-source accounting and before page-summary accumulation |
| OCR vs visual edge | TRUE CLOSURE (first phase) | `_process_pdf(...)` zones C/D vs frozen seam in `03W` | OCR fallback and hybrid OCR remain outside the frozen seam and baseline-locked for first integrated phase |
| Final acceptance command conventions | TRUE CLOSURE | `06J`; `06K` | Canonical repo-root + pytest-family + backend-on-`sys.path` convention with shell-specific realizations for PowerShell, CMD, and POSIX. Repo-native enforcement is a separate bounded residual, not a blocker |
| Residual consumer/visibility closure beyond live app-surface chain | TRUE CLOSURE | `visual_page_refs` search across `backend/app/**/*.py`; `00K`; `03X` | Residual app-surface consumers explicitly enumerated across models, schemas, retrieval-plane, evidence-bundle, review, and report/export layers |
| Selector config key / failure mode | TRUE CLOSURE | `_normalize_request_config(...)`; `processing_config_from_run_config(...)`; `default_processing_config(...)`; `_process_pdf(...)`; `backend/tests/test_nrc_aps_run_config.py`; `tests/test_nrc_aps_document_processing.py` | `visual_lane_mode` is now normalized, forwarded, defaulted, fail-closed, and first-consumed at the frozen visual-preservation seam. This closes the localized selector path itself, not full bootstrap acceptance |
| Control-key / query-payload leakage | TRUE CLOSURE | `connectors_nrc_adams._normalize_request_config(...)`; `backend/tests/test_nrc_aps_run_config.py` | Selector key remains a processing control and is excluded from lenient pass-through query payload construction |

### PLANNING-CLOSED

No current rows.

### IMPLEMENTATION REQUIRED

| Blocker | Status | Live evidence anchor | What implementation must produce |
|---|---|---|---|
| Runtime-root coexistence mechanism | IMPLEMENTATION REQUIRED | `backend/app/services/review_nrc_aps_runtime.py`; `backend/app/services/review_nrc_aps_runtime_roots.py`; `backend/tests/test_review_nrc_aps_catalog.py`; `backend/tests/test_review_nrc_aps_details.py` | Behavior requirement is frozen, but exact coexistence mechanism for experiments is not. Must produce exact experiment root naming/placement plus discovery-exclusion rule for summary-backed review roots |
| Review/catalog/report/API visibility | IMPLEMENTATION REQUIRED | `review_nrc_aps_catalog.discover_candidate_runs()`; `review_nrc_aps.py` run-bound endpoints; `nrc_aps_evidence_report*.py` run-bound persistence into `run.query_plan_json` | Separate runtime/artifact roots are insufficient if baseline-facing surfaces can still enumerate or expose experiment runs. Must produce exact visibility behavior for experiment runs across catalog/review/API/report/export surfaces |
| Review API exposure surface | IMPLEMENTATION REQUIRED | attached-session API exposure corroboration; review API already known live surface | API endpoints may expose processing-derived state even when underlying storage/runtime separation looks isolated. Must produce exact endpoint classes that remain baseline-locked in first pass |
| Diagnostics persistence semantics | IMPLEMENTATION REQUIRED | `backend/tests/test_diagnostics_ref_persistence.py`; `nrc_aps_content_index.py` diagnostics payload path | Behavior is baseline-locked, but selector proposals could contaminate serializer/linkage expectations. Must produce exact no-change rule for persistence surfaces during baseline bootstrap |
| Run-scoped review-root / runtime DB access semantics | IMPLEMENTATION REQUIRED | `backend/app/api/review_nrc_aps.py`; `backend/app/services/review_nrc_aps_runtime.py`; `backend/app/services/review_nrc_aps_runtime_db.py`; `backend/tests/test_review_nrc_aps_document_trace_api.py`; `backend/tests/test_review_nrc_aps_document_trace_service.py`; `backend/tests/test_review_nrc_aps_runtime_db.py` | Shared-root read-only validation now largely passes, but full closure still depends on stable audited runtime fixture quality and a canonical worktree/runtime-root convention that does not require seeding new data |
| Artifact equivalence | IMPLEMENTATION REQUIRED | `backend/tests/test_visual_artifact_pipeline.py`; `03J` | Baseline-integrated path must preserve artifact behavior if selector bootstrap is supposed to be no-op externally. Current live probe is script-style rather than pytest-collected, so closure requires either a pytest-collectible gate or an explicitly frozen non-pytest acceptance procedure plus thresholds for artifact sameness |
| Performance baseline / budget | IMPLEMENTATION REQUIRED | negative benchmark/perf search evidence; fixture sources from active owner/artifact tests; `06I` | Local gate is explicitly defined in `06I`. Execution depends on applying the frozen command convention from `06K`. Must execute the defined local gate |

### BOUNDED RESIDUAL

| Blocker | Status | Live evidence anchor | What is bounded |
|---|---|---|---|
| Bounded uncertainty / enforcement gap | BOUNDED RESIDUAL | `00L`; `06L`; `backend/app/schemas/review_nrc_aps.py` | The pack is strong but not equivalent to repo-native total closure. Acceptance/performance controls are specified by the pack (`06J`, `06K`, `06I`), but not visibly enforced via repo-native CI/hook mechanisms. At least one additional review-schema surface was found during re-audit. Carry explicitly instead of claiming zero remaining open items |
| Acceptance harness operability gap | BOUNDED RESIDUAL | `backend/tests/test_visual_artifact_pipeline.py`; `backend/tests/test_nrc_aps_advanced_adapters.py`; `backend/tests/review_nrc_aps_runtime_fixture.py`; shared runtime `20260331_101919` | T7 is not yet a stable single grouped pytest invocation because one file is script-style and another mutates `sys.modules["numpy"]` at import time. T8 largely passes when pointed read-only at the shared audited runtime root, but one summary-marked runtime currently lacks `aps_content_*` rows. Carry these as harness/fixture gaps instead of calling acceptance fully green |

---

## Interpretation

The pack is now strong enough that the *next* useful improvement is not more broad architecture prose.
It is closing individual rows in this table one by one, with explicit freeze outputs.

### How to read this table

- **TRUE CLOSURE** rows require no further work for the current milestone.
- **PLANNING-CLOSED** rows have frozen planning decisions but still need implementation to produce the specified outputs.
- **IMPLEMENTATION REQUIRED** rows have defined requirements but the implementation work itself is not done. Do not treat the existence of this row as proof that the implementation exists.
- **BOUNDED RESIDUAL** rows are explicitly carried uncertainty. They are not blockers and not invitations to widen scope.
