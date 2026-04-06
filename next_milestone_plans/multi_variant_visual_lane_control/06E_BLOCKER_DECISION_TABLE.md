# 06E Blocker Decision Table

## Purpose

Turn the remaining open items into explicit blocker decisions tied to live evidence.

## Status categories

Each row carries one of these explicit statuses:

- **TRUE CLOSURE** - Planning and evidence-level closure achieved. No further planning or implementation work required for this item.
- **PLANNING-CLOSED** - Planning freeze is complete. Implementation work remains before this item can be marked implementation-closed.
- **IMPLEMENTATION REQUIRED** - Specific implementation work is defined. The planning pack specifies what must be done, but the work itself is not yet done.
- **BOUNDED RESIDUAL** - Uncertainty is acknowledged, bounded, and carried explicitly. Not a blocker, but not zero.

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
| Artifact equivalence | TRUE CLOSURE | `backend/tests/test_visual_artifact_pipeline.py`; grouped T7 backend bundle; `03J` | Artifact behavior is now guarded by a pytest-collectible surface inside the canonical grouped backend bundle, which passes in the clean worktree |
| Run-scoped review-root / runtime DB access semantics | TRUE CLOSURE | `backend/tests/review_nrc_aps_runtime_fixture.py`; grouped T8 backend bundle; `backend/tests/test_review_nrc_aps_runtime_db.py`; `03L` | Clean-worktree review/runtime validation now resolves the shared audited runtime root read-only without seeding new data, and grouped review/runtime acceptance passes under the canonical command posture |
| Review/report/export field-sensitivity inventory | TRUE CLOSURE | `03Y`; `review_nrc_aps.py`; `review_nrc_aps_document_trace.py`; `nrc_aps_evidence_report*.py`; `nrc_aps_content_index.py` | The standalone field-level exposure map now exists. Remaining work is the exact coexistence/visibility mechanism, not identifying which outward fields and persistence keys are sensitive |
| Exact M5 execution packet boundary | TRUE CLOSURE | `05F`; live owner files in `review_nrc_aps_runtime*.py`, `review_nrc_aps_catalog.py`, `review_nrc_aps.py`, `nrc_aps_evidence_report*.py` | The next lane now has a frozen owner-file boundary, validation bundle boundary, hidden-consumer inspection set, and widening rule set. Remaining work is implementing the frozen coexistence/visibility mechanism inside that packet |

### PLANNING-CLOSED

| Blocker | Status | Live evidence anchor | Notes |
|---|---|---|---|
| Exact M5 coexistence / visibility mechanism | PLANNING-CLOSED | `03Z`; `review_nrc_aps_runtime_roots.py`; `review_nrc_aps_runtime.py`; `review_nrc_aps_catalog.py`; `nrc_aps_evidence_report*.py`; `connectors_sciencebase.py` | The exact canonical visibility signal, backward-compatibility fallback, path-level coexistence rule, and baseline-facing persistence rule are now frozen. Implementation work remains. |

### IMPLEMENTATION REQUIRED

| Blocker | Status | Live evidence anchor | What implementation must produce |
|---|---|---|---|
| Runtime-root coexistence mechanism | IMPLEMENTATION REQUIRED | `03Z`; `backend/app/services/review_nrc_aps_runtime.py`; `backend/app/services/review_nrc_aps_runtime_roots.py`; `backend/tests/test_review_nrc_aps_catalog.py`; `backend/tests/test_review_nrc_aps_details.py` | Implement the frozen two-layer rule: experiment roots must stay outside baseline default discovery, and discovered runtime bindings must still be filtered by the canonical run-level visibility signal. |
| Review/catalog/report/API visibility | IMPLEMENTATION REQUIRED | `03Z`; `03Y`; `review_nrc_aps_catalog.discover_candidate_runs()`; `review_nrc_aps.py` run-bound endpoints; `nrc_aps_evidence_report*.py` run-bound persistence into `run.query_plan_json` | Implement baseline-facing absence for experiment-hidden runs across selector, direct run-bound review/API surfaces, and shared report/export/package persistence while preserving current baseline behavior. |
| Diagnostics persistence semantics | IMPLEMENTATION REQUIRED | `03Z`; `backend/tests/test_diagnostics_ref_persistence.py`; `nrc_aps_content_index.py` diagnostics payload path | Implement the coexistence / visibility barrier without drifting diagnostics-ref persistence or runtime DB semantics for baseline-visible runs. |
| Broader T5/T6 acceptance gate | TRUE CLOSURE | `tests/test_api.py`; `tests/test_nrc_aps_document_corpus.py`; `tests/test_run_nrc_aps_local_corpus_e2e.py`; `06C`; `05D` | The broader root-side context/API/corpus bundles now pass under the canonical repo-root pytest posture. The earlier DB/runtime-isolation drift in `tests/test_api.py` and expectation drift in `tests/test_nrc_aps_document_corpus.py` were resolved in this clean worktree, so T1-T8 are no longer blocked at the T5/T6 layer |
| Performance baseline / budget | TRUE CLOSURE | `06I`; `tests/test_nrc_aps_document_processing.py`; `backend/tests/test_visual_artifact_pipeline.py`; `project6-origin/main` baseline worktree | The local gate was executed on the same machine/interpreter against merged `main`. Tier 1 mandatory comparison passed without regression. A preferred real-ADAMS Tier 2 timed attempt exceeded practical local session budget, so the declared-root handoff fallback artifact-aware sample was used for the recorded comparison and also passed without regression |

### BOUNDED RESIDUAL

| Blocker | Status | Live evidence anchor | What is bounded |
|---|---|---|---|
| Bounded uncertainty / enforcement gap | BOUNDED RESIDUAL | `00L`; `06L`; `backend/app/schemas/review_nrc_aps.py` | The pack is strong but not equivalent to repo-native total closure. Acceptance/performance controls are specified by the pack (`06J`, `06K`, `06I`), but not visibly enforced via repo-native CI/hook mechanisms. At least one additional review-schema surface was found during re-audit. Carry explicitly instead of claiming zero remaining open items |
| Tier 2 performance sample breadth | BOUNDED RESIDUAL | `06C`; `06E`; `06I`; `backend/tests/test_visual_artifact_pipeline.py` | The earlier T5/T6/T7/T8 harness defects are resolved and the full T1-T8 gate passes in this clean worktree. The remaining acceptance-side caveat is narrower: the recorded Tier 2 performance comparison uses the declared-root handoff fallback sample because the preferred real-ADAMS timed capture exceeded practical local session budget |

---

## Interpretation

The pack is now strong enough that the *next* useful improvement is not more broad architecture prose.
It is closing individual rows in this table one by one, with explicit freeze outputs.

### How to read this table

- **TRUE CLOSURE** rows require no further work for the current milestone.
- **PLANNING-CLOSED** rows have frozen planning decisions but still need implementation to produce the specified outputs.
- **IMPLEMENTATION REQUIRED** rows have defined requirements but the implementation work itself is not done. Do not treat the existence of this row as proof that the implementation exists.
- **BOUNDED RESIDUAL** rows are explicitly carried uncertainty. They are not blockers and not invitations to widen scope.
