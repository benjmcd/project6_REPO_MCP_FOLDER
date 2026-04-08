# 06E Blocker Decision Table

## Purpose

Turn the remaining open items into explicit blocker decisions tied to live evidence.

## Status categories

Each row carries one of these explicit statuses:

- **TRUE CLOSURE** - Planning and evidence-level closure achieved. No further planning or implementation work required for this item.
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
| Review/report/export field-sensitivity inventory | TRUE CLOSURE | `03Y`; `review_nrc_aps.py`; `review_nrc_aps_document_trace.py`; `nrc_aps_evidence_report*.py`; `nrc_aps_content_index.py` | The standalone field-level exposure map exists and now serves as fixed input to the achieved M5 barrier closure and the next M6 planning lane |
| Exact M5 execution packet boundary | TRUE CLOSURE | `05F`; live owner files in `review_nrc_aps_runtime*.py`, `review_nrc_aps_catalog.py`, `review_nrc_aps.py`, `nrc_aps_evidence_report*.py` | The frozen owner-file boundary, validation bundle boundary, hidden-consumer inspection set, and widening rule set were sufficient for the achieved M5 barrier lane with no default-owner widening |
| Exact M5 coexistence / visibility mechanism | TRUE CLOSURE | `03Z`; `05G`; `review_nrc_aps_runtime_roots.py`; `review_nrc_aps_runtime.py`; `nrc_aps_evidence_report*.py` | The exact canonical visibility signal, backward-compatibility fallback, path-level coexistence rule, and baseline-facing persistence rule are now frozen and implemented on merged `main` |
| Exact M6 admission/promotion packet boundary | TRUE CLOSURE | `03AA`; `05H`; `connectors_nrc_adams.py`; `nrc_aps_artifact_ingestion.py`; `nrc_aps_document_processing.py`; `review_nrc_aps_runtime.py`; `nrc_aps_promotion_gate.py`; `nrc_aps_promotion_tuning.py` | The exact M6 mechanism, owner boundary, validation packet, widening rules, and fail-closed stop conditions are now frozen. The packet remains intentionally blocked on one explicit approved target, rather than silently inferring it |
| Exact M6A PageEvidence workbench packet boundary | TRUE CLOSURE | `03AB`; `05I`; `nrc_aps_document_processing.py`; `nrc_aps_promotion_gate.py`; `nrc_aps_promotion_tuning.py`; `tools/run_nrc_aps_document_processing_proof.py`; repo-native `tools/nrc_aps_promotion_*.py` pattern | The exact dedicated PageEvidence / Option 2 workbench boundary, location strategy, owner boundary, validation packet, widening rules, and fail-closed stop conditions are frozen and were sufficient for the bounded workbench lane with no default-owner widening |
| Exact M6A PageEvidence workbench implementation | TRUE CLOSURE | `05J`; `backend/app/services/nrc_aps_page_evidence.py`; `tools/run_nrc_aps_page_evidence_workbench.py`; `backend/tests/test_nrc_aps_page_evidence.py`; `tests/test_nrc_aps_page_evidence_workbench.py` | A dedicated standalone Candidate A workbench now exists, passes the required M6A workbench bundle, preserves the baseline owner path unchanged by default, and leaves direct admission fail-closed |
| Runtime-root coexistence mechanism | TRUE CLOSURE | `03Z`; `05G`; `backend/app/services/review_nrc_aps_runtime.py`; `backend/app/services/review_nrc_aps_runtime_roots.py`; `backend/tests/test_review_nrc_aps_api.py` | Baseline default discovery now rejects arbitrary differently named configured roots and filters discovered runtime bindings by canonical baseline-visible run metadata |
| Review/catalog/report/API visibility | TRUE CLOSURE | `03Z`; `03Y`; `05G`; `review_nrc_aps_catalog.discover_candidate_runs()`; `review_nrc_aps.py` run-bound endpoints; `nrc_aps_evidence_report*.py` | Baseline-facing selector and direct run-bound review surfaces treat experiment-hidden runs as absent, and shared report/export/package persistence now fails closed for experiment-hidden runs |
| Diagnostics persistence semantics | TRUE CLOSURE | `03Z`; `05G`; `backend/tests/test_diagnostics_ref_persistence.py`; `nrc_aps_content_index.py` diagnostics payload path | The M5 barrier implementation preserves diagnostics-ref persistence and read-only runtime DB semantics for baseline-visible runs while blocking experiment-hidden outward visibility |
| Broader T5/T6 acceptance gate | TRUE CLOSURE | `tests/test_api.py`; `tests/test_nrc_aps_document_corpus.py`; `tests/test_run_nrc_aps_local_corpus_e2e.py`; `06C`; `05D` | The broader root-side context/API/corpus bundles pass under the canonical repo-root pytest posture, so M5 did not reopen the earlier T5/T6 layer |
| Performance baseline / budget | TRUE CLOSURE | `06I`; `05G`; `tests/test_nrc_aps_document_processing.py`; `backend/tests/test_visual_artifact_pipeline.py`; merged-main baseline `1fabb1ae` | The local gate was rerun on the same machine/interpreter against merged `main` after the M5 barrier changes. Tier 1 mandatory comparison and the declared-root Tier 2 fallback sample both passed without regression |

### BOUNDED RESIDUAL

| Blocker | Status | Live evidence anchor | What is bounded |
|---|---|---|---|
| Bounded uncertainty / enforcement gap | BOUNDED RESIDUAL | `00L`; `06L`; `backend/app/schemas/review_nrc_aps.py` | The pack is strong but not equivalent to repo-native total closure. Acceptance/performance controls are specified by the pack (`06J`, `06K`, `06I`), but not visibly enforced via repo-native CI/hook mechanisms. At least one additional review-schema surface was found during re-audit. Carry explicitly instead of claiming zero remaining open items |
| Tier 2 performance sample breadth | BOUNDED RESIDUAL | `06C`; `06E`; `06I`; `backend/tests/test_visual_artifact_pipeline.py` | The earlier T5/T6/T7/T8 harness defects are resolved and the full T1-T8 gate passes in this clean worktree. The remaining acceptance-side caveat is narrower: the recorded Tier 2 performance comparison uses the declared-root handoff fallback sample because the preferred real-ADAMS timed capture exceeded practical local session budget |
| Exact approved M6B target naming | BOUNDED RESIDUAL | `00D`; `03AA`; `05H`; `05J`; `05K` | The direct-admission packet is frozen, the M6A workbench is implemented, and the exact record template now exists, but no one selector value has yet been explicitly approved and recorded with evidence refs. The immediate next lane is filling `05K` and later direct admission, not more workbench construction |

---

## Interpretation

The pack is now strong enough that the next useful improvement is not more M5 barrier work and not more generic M6A construction.
It is using the achieved M5 barrier closure, the achieved M6A workbench record in `05J`, the exact target-record template in `05K`, and the frozen `03AA` + `05H` direct-admission packet as the next later-scope input.

### How to read this table

- **TRUE CLOSURE** rows require no further work for the current milestone.
- **BOUNDED RESIDUAL** rows are explicitly carried uncertainty. They are not blockers and not invitations to widen scope.
