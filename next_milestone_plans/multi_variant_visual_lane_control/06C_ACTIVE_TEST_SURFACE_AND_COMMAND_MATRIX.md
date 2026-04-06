# 06C Active Test Surface and Command Matrix

## Status

This revision strengthens the matrix by explicitly recognizing diagnostics-persistence, review-root/runtime-data safety, activation semantics, and isolation semantics as first-class validation surfaces.

The canonical repo-root `python -m pytest` posture is now live-verified for T1-T8 in this clean worktree. The local performance gate from `06I` has also been executed: Tier 1 main-vs-candidate comparison passed without regression, and a declared-root Tier 2 fallback artifact-aware sample also passed after the preferred real-ADAMS timed attempt exceeded a practical local session budget. This satisfies the bootstrap gate in the clean worktree; repo-native CI enforcement remains a separate bounded residual.

---

## 1. Verified active test roots

### Root tests
Verified:
- `tests/`

### Backend tests
Verified:
- `backend/tests/`

---

## 2. Verified active tests most relevant to selector safety

### Root `tests/`
- document-processing tests
- document corpus / e2e tests
- artifact-ingestion tests
- replay / promotion / safeguard / sync drift / live batch / live validation tests
- evidence/report/export/citation tests
- context packet / dossier tests
- API and import guardrail tests

### `backend/tests/`
- `test_visual_artifact_pipeline.py`
- `test_nrc_aps_advanced_adapters.py`
- `test_nrc_aps_run_config.py`
- `test_diagnostics_ref_persistence.py`
- `test_nrc_aps_evidence_bundle_integration.py`
- `test_review_nrc_aps_api.py`
- `test_review_nrc_aps_catalog.py`
- `test_review_nrc_aps_details.py`
- `test_review_nrc_aps_document_trace_api.py`
- `test_review_nrc_aps_document_trace_service.py`
- `test_review_nrc_aps_document_trace_page.py`
- other `backend/tests/test_review_nrc_aps_*`

---

## 3. Important verified structure inside tests

### `tests/test_nrc_aps_document_processing.py`
Covers:
- core document processing behavior
- visual page classification
- visual-lane integration behavior
- non-fatal visual capture failure
- OCR fallback strictness

### `backend/tests/test_nrc_aps_run_config.py`
Covers:
- processing override preservation in request-config normalization
- exclusion of processing controls from lenient pass-through query payload

### `backend/tests/test_visual_artifact_pipeline.py`
Covers:
- artifact output
- file SHA-256 computation
- artifact file verification
- artifact metadata verification
- content-index roundtrip for artifact metadata

### `backend/tests/test_review_nrc_aps_catalog.py`
Covers:
- summary-backed candidate run discovery
- golden-run presence
- stable default-run selection contract

### `backend/tests/test_review_nrc_aps_api.py`
Covers:
- review route wiring for runs / pipeline-definition / overview / tree / node / file surfaces on audited run ids

### `backend/tests/test_diagnostics_ref_persistence.py`
Covers:
- diagnostics-ref persistence
- cross-run diagnostics safety
- absent linkage behavior

### `backend/tests/test_review_nrc_aps_document_trace_api.py` and `backend/tests/test_review_nrc_aps_document_trace_service.py`
Covers:
- run-scoped review-root resolution
- read-only behavior
- path safety
- diagnostics / normalized-text / indexed-chunk / trace payload behavior against an audited `lc_e2e` runtime

---

## 4. Command bundle matrix

### Interpretation rule

This matrix has three distinct layers:

- **Verified test files:** The individual test files listed in each bundle have been verified to exist in the live repo (Section 2 and 3 above).
- **Command bundles:** The grouped `pytest` invocations below are intended operational groupings. They use the canonical acceptance convention frozen in `06K` (repo root, `PYTHONPATH=backend`, `python -m pytest`). When a bundle has known collection/order/runtime caveats, carry them explicitly in Section 6 instead of treating the grouped invocation as already proven green.
- **Acceptance gates:** T1 through T8 collectively form the hard acceptance gate for baseline-only selector bootstrap. All must pass before bootstrap can be accepted (Section 5 below).

### Status labels

- **FILES VERIFIED** — Individual test files confirmed to exist. Command bundle uses canonical convention from `06K`.
- **PROVISIONAL** — Test files listed but not yet individually confirmed against live repo in this pass.

| Command ID | Status | Purpose | Command Bundle |
|---|---|---|---|
| T1 | FILES VERIFIED | Core visual-lane owner behavior | `pytest tests/test_nrc_aps_document_processing.py` |
| T2 | FILES VERIFIED | Root artifact/ingestion behavior | `pytest tests/test_nrc_aps_artifact_ingestion.py tests/test_nrc_aps_artifact_ingestion_gate.py` |
| T3 | FILES VERIFIED | Root governance behavior | `pytest tests/test_nrc_aps_replay_gate.py tests/test_nrc_aps_promotion_gate.py tests/test_nrc_aps_promotion_tuning.py tests/test_nrc_aps_safeguard_gate.py tests/test_nrc_aps_safeguards.py tests/test_nrc_aps_sync_drift.py tests/test_nrc_aps_live_batch.py tests/test_nrc_aps_live_validation.py` |
| T4 | FILES VERIFIED | Root evidence/report/export behavior | `pytest tests/test_nrc_aps_evidence_bundle.py tests/test_nrc_aps_evidence_bundle_gate.py tests/test_nrc_aps_evidence_report.py tests/test_nrc_aps_evidence_report_gate.py tests/test_nrc_aps_evidence_report_export.py tests/test_nrc_aps_evidence_report_export_gate.py tests/test_nrc_aps_evidence_report_export_package.py tests/test_nrc_aps_evidence_report_export_package_gate.py tests/test_nrc_aps_evidence_citation_pack.py tests/test_nrc_aps_evidence_citation_pack_gate.py` |
| T5 | FILES VERIFIED | Root context/API/guardrail behavior | `pytest tests/test_nrc_aps_context_packet.py tests/test_nrc_aps_context_packet_gate.py tests/test_nrc_aps_context_dossier.py tests/test_nrc_aps_context_dossier_gate.py tests/test_api.py tests/test_import_guardrail.py` |
| T6 | FILES VERIFIED | Root corpus/E2E checks | `pytest tests/test_nrc_aps_document_corpus.py tests/test_run_nrc_aps_local_corpus_e2e.py` |
| T7 | FILES VERIFIED | Backend visual/artifact/config/diagnostics behavior | `pytest backend/tests/test_visual_artifact_pipeline.py backend/tests/test_nrc_aps_advanced_adapters.py backend/tests/test_nrc_aps_run_config.py backend/tests/test_diagnostics_ref_persistence.py backend/tests/test_nrc_aps_evidence_bundle_integration.py` |
| T8 | FILES VERIFIED | Backend review/trace/runtime-root behavior | `pytest backend/tests/test_review_nrc_aps_api.py backend/tests/test_review_nrc_aps_document_trace_api.py backend/tests/test_review_nrc_aps_document_trace_service.py backend/tests/test_review_nrc_aps_document_trace_page.py backend/tests/test_review_nrc_aps_catalog.py backend/tests/test_review_nrc_aps_details.py backend/tests/test_review_nrc_aps_graph.py backend/tests/test_review_nrc_aps_tree.py backend/tests/test_review_nrc_aps_page.py` |

---

## 5. Minimum acceptance set for baseline-only selector bootstrap

At minimum, bootstrap cannot be accepted until T1 through T8 are frozen and passing under live-verified command conventions.

Additional acceptance expectations:
- review/runtime-root behavior remains baseline-stable
- experiments do not silently appear under the baseline `lc_e2e` namespace
- artifact-equivalence controls are satisfied
- diagnostics-ref persistence behavior is unchanged
- review-root/runtime-data behavior is unchanged

---

## 6. Closure status and remaining items

### Closed since earlier revisions
- **Runner convention:** Frozen in `06K`. Repo root + `PYTHONPATH=backend` + `python -m pytest tests backend/tests`. Shell-specific realizations provided for PowerShell, CMD, and POSIX.
- **Working directory:** Repo root, per `06K`.
- **T3/T4 file inventory and grouped execution:** Live-verified under the canonical repo-root `pytest` posture.
- **T7 grouped backend bundle:** `backend/tests/test_visual_artifact_pipeline.py` is now pytest-collectible, and `backend/tests/test_nrc_aps_advanced_adapters.py` no longer poisons grouped imports via `sys.modules["numpy"]`.
- **T8 clean-worktree execution:** `backend/tests/review_nrc_aps_runtime_fixture.py` now aligns clean-worktree review/runtime validation with the shared audited runtime root without requiring manual shell-level `STORAGE_DIR`.
- **Performance regression gate:** Defined in `06I`. Execution depends on applying the frozen command convention.

### Remaining
- Repo-native CI enforcement of the Python acceptance path is not yet implemented (bounded residual, not a blocker for this matrix)
- The recorded `06I` Tier 2 comparison uses the declared-root handoff fallback sample (`layout.pdf`, `mixed.pdf`, `scanned.pdf`) because the preferred real-ADAMS timed attempt exceeded practical local session budget. Carry that capture-breadth limitation explicitly instead of pretending the preferred heavier sample was completed.
