# NRC ADAMS APS Status Handoff

## 1. Purpose and truth model
This document is the canonical live-repo status surface for the NRC ADAMS APS stack. Last updated April 25, 2026 to reflect the landed bounded Layer 3 and validate-only packet through PR `#148`, the later APS family settlement on current `main`, the landed runtime-centric review/document-trace shift plus runtime DB safety rails on current `main`, the landed runtime-authority transparency pass across review/document-trace/workbench on current `main`, the repo-native review-browser harness import hardening landed on current `main` through PR `#156`, the bounded Layer 3 first-slice workbench shell/API plus post-implementation closeouts now landed on current `main` through PR `#190`, the merged planning-only second-slice Layer 3 plan-preview packet from PR `#191`, and the post-PR191 progress-metadata sync from PR `#192`, on top of the earlier bounded evidence-bundle, citation-pack, evidence-report, and evidence-report-export handoff slices, the Deterministic Challenge Review Packet v1 closeout, and the narrow Tier2 diagnostics-write closeout.

Repo truth precedence used here:
1. live code, tests, scripts, migrations, and repo-contained proof artifacts
2. this live status doc and other current root docs
3. handoff package control surfaces
4. older planning/history only when not contradicted by the live repo

Status wording used below:
- `repo-confirmed in this workspace`
- `carried-forward but not revalidated here`
- `inferred from repo shape`

## 2. Current status summary
### Repo-confirmed in this workspace
| Surface | Current state | Proof |
| --- | --- | --- |
| Upper analytical ceiling | Still closed/frozen through Deterministic Challenge Review Packet v1 | current live contract/service/gate/tests/report surfaces for citation pack, evidence report/export/package, context packet, context dossier, deterministic insight, deterministic challenge, deterministic challenge review packet |
| Lower document-processing layer | Reopened additively for deterministic media detection, real PDF extraction, OCR fallback hooks, quality gating, and content-units v2 | `backend/app/services/nrc_aps_media_detection.py`, `backend/app/services/nrc_aps_document_processing.py`, `backend/app/services/nrc_aps_ocr.py`, `backend/app/services/nrc_aps_artifact_ingestion.py`, `backend/app/services/nrc_aps_content_index.py`, `backend/alembic/versions/0009_aps_document_processing_metadata.py` |
| Phase 8 APS bridge | **Closed** - All required APS-table materialization invariants satisfied (41 targets, 41 linkages, 40 distinct content IDs, 40 documents) using run `closure-run-005`. | `backend/app/services/nrc_adams_index_builder.py` run with `closure-run-005` on `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136` |
| Bounded Layer 3 APS evidence-bundle handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-bundle family; emits `aps_evidence_bundle_handoff` from already-packaged terminal Layer 3 sessions without widening APS contract/gate files. | `backend/app/services/layer3_aps_handoff.py`, `backend/tests/test_layer3_aps_handoff.py`, `next_milestone_plans/Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md` |
| Bounded Layer 3 APS citation-pack handoff consumer | Present as one additive Layer 3 consumer of the live APS citation-pack family; emits `aps_evidence_citation_pack_handoff` from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_citation_handoff.py`, `backend/tests/test_layer3_aps_citation_handoff.py`, `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md` |
| Bounded Layer 3 APS evidence-report handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-report family; emits `aps_evidence_report_handoff` from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_report_handoff.py`, `backend/tests/test_layer3_aps_report_handoff.py`, `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md` |
| Bounded Layer 3 APS evidence-report-export handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-report-export family; emits `aps_evidence_report_export_handoff` from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md` |
| Bounded Layer 3 APS export-derived context-packet handoff consumer | Present as one additive Layer 3 consumer of the live APS context-packet family; emits `aps_context_packet_handoff` from already-packaged terminal Layer 3 sessions using direct export-derived sources without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_context_packet_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md` |
| Bounded Layer 3 APS same-run multisource admission consumer | Present as one additive Layer 3 consumer of the live shared-source admission boundary; emits `aps_multisource_admission` from already-packaged terminal Layer 3 sessions using existing durable same-run grouping seams without route/UI widening, runtime DB writes, or schema widening. | `backend/app/services/layer3_aps_multisource.py`, `backend/tests/test_layer3_aps_multisource.py`, `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md` |
| Bounded Layer 3 APS evidence-report-export-package handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-report-export-package family; emits `aps_evidence_report_export_package_handoff` from `aps_multisource_admission` plus matched persisted same-run exports while keeping route/UI, runtime DB, and schema widening out. Current `main` also now includes the narrow export/export-package gate hardening that filters exact embedded run identity under sanitized filename-scope collisions. | `backend/app/services/layer3_aps_report_export_package_handoff.py`, `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md` |
| Bounded Layer 3 APS package-derived context handoff consumer | Present as one additive Layer 3 consumer of the live APS context-packet package family; emits `aps_context_packet_package_handoff` from `aps_evidence_report_export_package_handoff` while keeping route/UI, runtime DB, and schema widening out. Current `main` now also includes the adjacent export, export-package, and context-packet gate hardening that preserves exact owner-run filtering and closes malformed-scoped candidate discovery when `run_ids` are omitted. | `backend/app/services/layer3_aps_context_packet_package_handoff.py`, `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, `backend/app/services/nrc_aps_context_packet_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` |
| Bounded Layer 3 APS context-dossier handoff consumer | Present as one additive Layer 3 consumer of the live APS context-dossier family; emits `aps_context_dossier_handoff` from the landed package-derived context handoff only as gating provenance, then resolves the actual dossier inputs from the paired persisted export-derived context packets required by the live dossier contract. Current `main` also now includes the narrow dossier-gate scope hardening that preserves exact owner-run filtering under sanitized filename-scope collisions. | `backend/app/services/layer3_aps_context_dossier_handoff.py`, `backend/app/services/nrc_aps_context_dossier_gate.py`, `backend/tests/test_layer3_aps_context_dossier_handoff.py`, `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` |
| Bounded Layer 3 APS deterministic-insight handoff consumer | Present as one additive Layer 3 consumer of the live APS deterministic-insight family; emits `aps_deterministic_insight_artifact_handoff` from one persisted `aps_context_dossier_handoff` package while leaving `ConnectorRun.query_plan_json` runtime refs and summaries untouched. Current `main` now also includes narrow deterministic-gate hardening that restores exact owner-run filtering under sanitized filename-scope collisions and keeps malformed-scoped candidate discovery fail-closed. | `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`, `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` |
| Read-only Gate D APS deterministic-challenge continuation freeze | Landed on current `main`; selects `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary without admitting challenge implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening. | `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`, `backend/app/services/review_nrc_aps_graph.py` |
| Bounded Layer 3 APS deterministic-challenge handoff consumer | Present as one additive Layer 3 consumer of the live APS deterministic-challenge family; emits `aps_deterministic_challenge_artifact_handoff` from one persisted `aps_deterministic_insight_artifact_handoff` package while leaving `ConnectorRun.query_plan_json` runtime refs and summaries untouched. Current `main` now also includes narrow deterministic challenge gate hardening that restores exact owner-run filtering under sanitized filename-scope collisions and keeps malformed-scoped candidate discovery fail-closed. | `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`, `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` |
| Read-only Gate D APS deterministic challenge review-packet continuation freeze | Landed on current `main`; selects `deterministic_challenge_review_packet` as the next deterministic continuation beyond the landed deterministic challenge handoff while keeping validate-only gates later and still excluding route/UI, runtime DB, and schema widening. | `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet.py`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`, `backend/app/services/review_nrc_aps_graph.py` |
| Bounded Layer 3 APS deterministic challenge review-packet handoff consumer | Present as one additive Layer 3 consumer of the live APS deterministic challenge review-packet family; emits `aps_deterministic_challenge_review_packet_handoff` from one persisted `aps_deterministic_challenge_artifact_handoff` package while leaving `ConnectorRun.query_plan_json` runtime refs and summaries untouched. Current `main` now also includes narrow review-packet gate hardening that restores exact owner-run filtering under sanitized filename-scope collisions and keeps malformed-scoped candidate discovery fail-closed. | `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`, `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`, `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md` |
| Read-only Gate D APS validate-only-gates continuation freeze | Landed on current `main` from PR `#136`; selects `validate_only_gates` as the exact next verification continuation beyond the landed deterministic challenge review-packet handoff while making explicit that current `main` still relies on generic `gate_reports` plus `gate_results` surfaces rather than a dedicated validate-only runtime family. | `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/tests/test_review_nrc_aps_graph.py`, `project6.ps1`, `backend/app/services/connectors_sciencebase.py` |
| Bounded Layer 3 APS validate-only gate-report refresh slice | Landed on current `main` from PR `#138`; refreshes one adopted review runtime's `gate_reports/*.json` plus `summary.gate_results` from the existing generic validate-only gates without seeding artifacts or widening promotion, retrieval cutover, route/UI, runtime DB, schema, or a dedicated validate-only runtime family. | `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, `project6.ps1`, `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` |
| Read-only Gate D APS dedicated validate-only runtime/report-ref continuation freeze | Landed on current `main` from PR `#140`; selects the dedicated `validate_only_gates` family-specific runtime/report-ref decision as the next bounded continuation beyond the landed generic gate-report refresh lane while still excluding implementation, promotion, retrieval cutover, route/UI, runtime DB, and schema widening. | `next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`, `backend/app/services/connectors_sciencebase.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `project6.ps1` |
| Bounded Layer 3 APS dedicated validate-only runtime/report-ref implementation slice | Landed on current `main` from PR `#143`; adds the dedicated validate-only contract/runtime/gate trio plus run-level report-ref registry, review graph/tree, shared runtime-binding, operator entrypoint integration, and narrow validate-only boundary hardening while preserving the landed generic gate-report refresh lane as the immediate upstream truth and still excluding later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, and schema widening. | `backend/app/services/nrc_aps_validate_only_gates_contract.py`, `backend/app/services/nrc_aps_validate_only_gates.py`, `backend/app/services/nrc_aps_validate_only_gates_gate.py`, `backend/app/services/review_nrc_aps_runtime.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/connectors_sciencebase.py`, `backend/tests/test_nrc_aps_validate_only_gates.py`, `tools/nrc_aps_refresh_validate_only_gates.py`, `tools/nrc_aps_validate_only_gates_gate.py`, `project6.ps1` |
| Later APS family settlement beyond validate-only | Live repo truth on current `main` already proves the existing promotion governance family is sufficient and the separate retrieval cutover parity-proof family is already present, so no further later APS family decision or implementation lane is justified by default. | `next_milestone_plans/Layer3_planning_docs/23_GATED_APS_PROMOTION_FREEZE.md`, `backend/app/services/nrc_aps_promotion_gate.py`, `tests/test_nrc_aps_promotion_gate.py`, `backend/app/services/nrc_aps_promotion_tuning.py`, `tests/test_nrc_aps_promotion_tuning.py`, `backend/app/services/aps_retrieval_plane_cutover_validation.py`, `backend/tests/test_aps_retrieval_plane_cutover_validation.py`, `backend/tests/test_aps_retrieval_plane_cutover_gate.py`, `tools/nrc_aps_retrieval_cutover_gate.py`, `project6.ps1` |
| Runtime-centric review/document-trace/workbench operator surfaces | Current `main` now also carries read-only runtime DB safety rails, operator-safe runtime binding summaries, explicit runtime/DB/storage authority labeling across review, document trace, and workbench compare, bounded large-document page-window gating plus virtualized render guards in document trace, explicit indexed-chunks sync controls, route/session data-path audit coverage for representative document-trace flows, and repo-native Playwright/browser-harness coverage whose boot path now resolves locally from `backend/tests` instead of depending on the repo-wide `tests` namespace. | `backend/app/api/review_nrc_aps.py`, `backend/app/services/review_nrc_aps_runtime_db.py`, `backend/app/services/review_nrc_aps_catalog.py`, `backend/app/services/review_nrc_aps_workbench_compare.py`, `backend/app/review_ui/static/review.js`, `backend/app/review_ui/static/document_trace.js`, `backend/app/review_ui/static/workbench_compare.js`, `backend/tests/test_review_nrc_aps_document_trace_api.py`, `backend/tests/test_review_nrc_aps_document_trace_page.py`, `backend/tests/review_browser_server.py`, `backend/tests/test_review_browser_server.py`, `e2e/nrc-aps-review.spec.js`, `playwright.config.js`, `frontend_UI_plans/README.md`, `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md`, `frontend_UI_plans/nrc_aps_runtime_db_reconceptualization_and_next_steps.md` |
| Bounded Layer 3 first-slice workbench shell/API and planning-only plan-preview prep | Current `main` now ships `/review/layer3` plus `/api/v1/layer3/...` for the bounded first-slice workbench only: intent/preflight, deterministic source preview, material preview, Gate B decision recording, Gate C UI non-authoritative typing preview, explicit API owner-service typing materialization when `commit_typing` is true, explicit Gate C override unavailability, and session summary. Post-PR184 closeouts through PR `#190` preserve response envelopes, blocked Gate B error semantics, Gate C authority-rail counts/source context, and tracked-PR metadata without expanding the live scope. PR `#191` adds `30_L3_WB_PLAN_PREVIEW_FREEZE.md` / `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` as the merged planning-only next bounded plan-preview slice after explicit Gate C typing commit, and PR `#192` records that merged state in progress/control metadata; they do not make plan preview live and do not admit execution, results, package review, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, handoff scope, or LLM planning. | `backend/main.py`, `backend/app/api/router.py`, `backend/app/api/layer3.py`, `backend/app/services/layer3_workbench.py`, `backend/app/services/layer3_pass_entry.py`, `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.css`, `backend/app/review_ui/static/layer3.js`, `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_api.py`, `backend/tests/test_layer3_page.py`, `backend/tests/test_layer3_pass_entry.py`, `e2e/layer3-workbench.spec.js`, `next_milestone_plans/Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md`, `next_milestone_plans/Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`, `next_milestone_plans/Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md`, `next_milestone_plans/Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` |
| API/schema wiring for lower-layer controls | Present | `backend/app/schemas/api.py`, `backend/app/api/router.py` |
| Lower-layer fixture corpus | Present and manifest-driven | `tests/fixtures/nrc_aps_docs/v1/manifest.json`, `tests/support_nrc_aps_doc_corpus.py`, `tests/test_nrc_aps_document_corpus.py`, plus live text/PDF/corrupt/truncated fixtures including `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf` |
| Fresh lower-layer proof runner | Present and current | `tools/run_nrc_aps_document_processing_proof.py`, `project6.ps1 -Action prove-nrc-aps-document-processing`, and `tests/reports/nrc_aps_document_processing_proof_report.json` |
| Focused lower-layer verification | Green (March 13 baseline; March 25 adds new coverage) | fresh isolated proof rerun on March 13, 2026: `46 passed` across lower-layer media-detection/document-processing/corpus/content-index/OCR-adapter tests plus `3 passed` API proof tests. March 25 hardening (`2f597f9`) added `backend/tests/test_diagnostics_ref_persistence.py` and expanded `backend/tests/test_nrc_aps_evidence_bundle_integration.py`; these test files are on disk but not yet reflected in a refreshed checked-in report. |
| Fresh lower-layer gate proof | Green in isolated temp runtime | `validate-nrc-aps-artifact-ingestion` and `validate-nrc-aps-content-index` both reran PASS on March 13, 2026 against a fresh isolated SQLite/runtime proof set built from repaired hydrate-process, download-only, and OCR-backed lower-layer paths |
| Upper-layer schema stability during lower-layer changes | Preserved | broader APS pytest rerun on March 13, 2026: `208 passed`; no upper `v1` schema ids were widened |
| Phase 7A Advanced Validation | `accepted-state` | Rerun on March 14, 2026: 43/43 files processed with real advanced OCR (19) and advanced table (28) evidence |

### Current proof freshness and remaining gaps
| Surface | Current state | Proof |
| --- | --- | --- |
| Fresh full aggregate NRC gate PASS after lower-layer expansion | Available; covers pre-March-25 state | rerun on March 13, 2026 via `./project6.ps1 -Action gate-nrc-aps`: aggregate pytest slice `143 passed, 29 deselected`, post-validator dossier ambiguity negative slice `1 passed, 55 deselected`, and aggregate validate-only reports refreshed to PASS through Deterministic Challenge Artifact. Note: March 25, 2026 hardening commits (`2f597f9`, `90c0c58`) changed diagnostics_ref resolution and visual artifact materialization behavior after this gate run. |
| Fresh bounded Layer 3 APS continuation proof | Available in this workspace for the current merged export-package, package-derived-context, context-dossier, deterministic-insight, deterministic-challenge, and deterministic challenge review-packet handoff slices, plus the merged export/export-package/context-packet/dossier/deterministic/review-packet gate hardening follow-ups | focused rerun on April 21, 2026: `90 passed, 2 warnings` across `backend/tests/test_layer3_session_entry.py`, `backend/tests/test_layer3_typing_entry.py`, `backend/tests/test_layer3_pass_entry.py`, `backend/tests/test_layer3_package_entry.py`, `backend/tests/test_layer3_aps_handoff.py`, `backend/tests/test_layer3_aps_citation_handoff.py`, `backend/tests/test_layer3_aps_report_handoff.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, `backend/tests/test_layer3_aps_context_dossier_handoff.py`, `backend/tests/test_layer3_aps_multisource.py`, `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py` |
| Existing APS validation reports under `tests/reports/` | Partially fresh | refreshed in this workspace for the March 26 closeouts: `nrc_aps_content_index_validation_report.json`, `nrc_aps_evidence_bundle_validation_report.json`, and `nrc_aps_deterministic_challenge_review_packet_validation_report.json`; other checked-in APS reports remain prior generated artifacts unless explicitly rerun |
| Fresh live batch and promotion validation | Not rerun in this pass | existing manifests/reports remain available under `backend/app/storage/connectors/reports/` and `tests/reports/` |
| Fresh review/runtime/browser proof on current `main` | Available in this workspace for the landed runtime-clarity and review-browser harness posture | focused rerun on April 21, 2026: `114 passed, 3 skipped, 3 warnings` across `backend/tests/test_review_browser_server.py`, `backend/tests/test_review_nrc_aps_api.py`, `backend/tests/test_review_nrc_aps_document_trace_api.py`, `backend/tests/test_review_nrc_aps_workbench_compare_api.py`, `backend/tests/test_review_nrc_aps_runtime_db.py`, `backend/tests/test_review_nrc_aps_page.py`, `backend/tests/test_review_nrc_aps_document_trace_page.py`, and `backend/tests/test_review_nrc_aps_workbench_compare_page.py`, plus repo-native Playwright headless `2 passed` and headed `2 passed` via `e2e/nrc-aps-review.spec.js` and `playwright.config.js` |
| Fresh bounded Layer 3 first-slice workbench proof | Available in this workspace for the PR `#184` implementation plus post-PR184 closeouts through PR `#190`; local proof was captured on the PR #189 branch before merge, and current `main` GitHub Playwright passed at `56874333eb016c261d00a42faecfcefcd0eb2ff8` | focused rerun on April 24, 2026: `14 passed, 3 warnings` across `backend/tests/test_layer3_workbench.py`, `backend/tests/test_layer3_api.py`, and `backend/tests/test_layer3_page.py`; existing Layer 3 owner-service regression slice `17 passed`; adjacent review/static page regression slice `25 passed, 3 warnings`; repo-native Playwright first-slice operator path headless `1 passed` and headed `1 passed` via `e2e/layer3-workbench.spec.js`; GitHub `Playwright Tests` main run `24916587442` succeeded for commit `56874333eb016c261d00a42faecfcefcd0eb2ff8` |

## 3. Active lower-layer implementation state
### Media detection
- Header normalization is still used, but it is no longer the only decision surface.
- `aps_media_detection_v1` now performs deterministic byte sniffing for PDF, text, HTML, JSON, XML, PNG, JPEG, TIFF, ZIP, and unknown binary.
- Supported processing classes remain `application/pdf` and `text/plain`.
- HTML, JSON, XML, ZIP, and image signatures are refused explicitly as artifact bodies in the APS document-processing path.
- Generic or missing headers can now be overridden by a supported sniffed type; supported mismatches are processed with recorded degradation.

### Document extraction
- `aps_document_extraction_v1` now routes through `nrc_aps_document_processing.py`.
- Plain text decoding is BOM-aware and attempts UTF-8/UTF-16 before CP1252 fallback.
- PDF extraction now uses PyMuPDF block extraction instead of raw `latin-1` byte decoding.
- OCR support is wired through `nrc_aps_ocr.py` using the Tesseract CLI, with fixed language/DPI/timeout config surfaces.
- The OCR adapter now auto-detects the standard Windows install path `C:\Program Files\Tesseract-OCR\tesseract.exe` (and the x86 equivalent) in addition to `PATH` and `TESSERACT_CMD`.
- `content_parse_timeout_seconds` is now enforced cooperatively inside the lower-layer processing path.
- When OCR is required but unavailable, scanned PDFs fail closed and mixed PDFs degrade explicitly if native text still exists.
### Normalization and quality
- Lower-layer normalization contract is now `aps_text_normalization_v2`.
- Quality states are `strong`, `limited`, `weak`, and `unusable`.
- Weak and unusable extraction outcomes are preserved with provenance and diagnostics, but are excluded from downstream chunk indexing.
### Content indexing
- Content-unit schema is now `aps.content_units.v2`.
- Content contract is now `aps_content_units_v2`.
- Chunking contract is now `aps_chunking_v2`.
- Chunks are now built from ordered document units with page/unit metadata rather than pure raw-character slicing.
- DB metadata now includes media type, document class, quality status, page count, diagnostics refs, and chunk page spans/unit kinds.
- `download_only` reprocessing now persists a diagnostics artifact as part of content-index derivation.
- `diagnostics_ref` is authoritative at the run-target/linkage and content-artifact level; the deduplicated content-document row must not be treated as the authoritative diagnostics pointer across runs. Hardened March 25, 2026 (`2f597f9`): the upsert path now correctly persists `diagnostics_ref` from payload (prior code hardcoded `None`), and the serializer uses linkage-only authority via `_resolve_diagnostics_ref` with no document-level fallback.
- Visual artifact materialization in the production hydrate pipeline was corrected March 25, 2026 (`90c0c58`): `connectors_nrc_adams.py` now passes `artifact_storage_dir` from settings into the extraction config, enabling visual page refs to be written to storage during the hydrate-process path.

### Corpus and proof
- `tests/fixtures/nrc_aps_docs/v1/manifest.json` is now the executable corpus oracle rather than a descriptive inventory only.
- `tests/support_nrc_aps_doc_corpus.py` and `tests/test_nrc_aps_document_corpus.py` now drive lower-layer fixture expectations from that manifest.
- Representative fixtures now exist for UTF-8 text, UTF-16 text, born-digital PDF, layout/font-oriented PDFs, scanned/mixed PDFs, mismatch cases, and corrupt/truncated PDFs.
- The corpus now includes a representative real NRC PDF fixture at `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`, copied from the local example dropped under `data_demo/`.
- Real born-digital downstream usefulness is now proven in `tests/test_api.py` through content search and evidence-bundle persistence using extracted text rather than seeded synthetic chunks.
- OCR-backed downstream usefulness is now also proven in `tests/test_api.py` through the scanned fixture path when Tesseract is available.
- Current fresh OCR-enabled proof is recorded in:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- Fresh aggregate gate proof is now also recorded in:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- OCR-success is now proven in this workspace. Tesseract remains an external prerequisite for reproducing that proof elsewhere.

### Phase 7 / 7A: Advanced capabilities
- `nrc_aps_advanced_table_parser.py` implements borderless table extraction using Camelot and Ghostscript.
- `nrc_aps_advanced_ocr.py` implements high-accuracy OCR using local PaddleOCR models.
- Advanced routing is triggered by category-based rules (`Technical Specification Amendment`, etc.) OR health-based triggers (low-quality native text detection).
- Phase 7A validation proved these capabilities on 43 real NRC ADAMS documents.
- Verified counts: 19 files utilized Advanced OCR, 28 files utilized Advanced Tables.
- Advanced environment provenance: Requires Python 3.11, `paddleocr` (v2.10.0), `camelot-py` (v1.0.9), and Ghostscript.

## 4. Closed layers
These layers remain closed/frozen except for defect-driven work:
- replay regression control
- 2A sync delta / drift correctness
- operational safeguards
- 2B promotion governance
- evidence retrieval / assembly
- citation-pack v1
- evidence-report v1
- evidence-report export v1
- evidence-report export package v1
- Context Packet v1
- Context Dossier v1
- Deterministic Insight Artifact v1
- Deterministic Challenge Artifact v1
- Deterministic Challenge Review Packet v1

Important correction:
- artifact ingestion and content indexing are no longer treated as closed/frozen in this document-processing workstream
- upper analytical schemas remain frozen while lower-layer document/media handling evolves additively

## 5. Lower-layer contract and schema inventory
### New or updated lower-layer contracts
- `aps_media_detection_v1`
- `aps_document_extraction_v1`
- `aps_text_normalization_v2`
- `aps_content_units_v2`
- `aps_chunking_v2`

### Persisted lower-layer metadata surfaces
- declared/sniffed/effective content type
- media detection contract/status/reason
- document class
- extractor family/id/version
- quality status and degradation codes
- page count
- diagnostics refs
- chunk page spans and unit kind

### Schema/migration authority
- DB/model changes live in `backend/app/models/models.py`
- schema migration lives in `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- API request/response wiring lives in `backend/app/schemas/api.py`

## 6. Operator and validation notes
- Existing `validate-*` actions remain validate-only, fail closed on empty runtime, and must not seed artifacts.
- `project6.ps1` remains the operator entrypoint for migrations and APS validators.
- `project6.ps1 -Action prove-nrc-aps-document-processing` is now the fresh isolated lower-layer proof runner for this reopened workstream. It is not a validate-only action: it builds isolated runtime state, runs lower-layer pytest proof, then invokes the existing validate-only artifact-ingestion and content-index gates against that isolated runtime.
- OCR success paths remain environment-dependent because Tesseract is not bundled in the repo, but the current workspace now has a passing OCR-enabled proof run.
- For the shipped review/document-trace/workbench/Candidate B Trace operator flow on current `main`, use:
  - `docs/nrc_adams/nrc_aps_ui_launch_runbook.md` for the canonical launch contract
  - `frontend_UI_plans/README.md` as the retained reference index
  - `frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md` for the concise startup walkthrough layered on top of the launch runbook
  - `frontend_UI_plans/wb-compare-validation.md` for same-checkout prep and the `tools/validate_wb_prep.py` readiness gate
  - `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md` for the broader manual validation pass after launch and prep succeed
  - `playwright.config.js`, `.github/workflows/playwright.yml`, `backend/tests/review_browser_server.py`, `backend/tests/test_review_browser_server.py`, and `e2e/nrc-aps-review.spec.js` for the repo-native review-browser regression lane

## 7. Current explicit limits
- Tesseract CLI availability is an external prerequisite for scanned/mixed PDF OCR success.
- In a no-Tesseract environment, scanned PDFs fail closed with `ocr_required_but_unavailable`, and mixed PDFs may degrade to weak/native-only output.
- The current merged `main` state now includes bounded Layer 3 APS evidence-bundle, citation-pack, evidence-report, evidence-report-export, export-derived context-packet, multisource-admission, export-package first shared-consumer freeze, export-package handoff, narrow export/export-package gate-hardening, package-derived context, context-dossier, deterministic-insight, deterministic-challenge, deterministic challenge review-packet, validate-only gate-report refresh, dedicated validate-only runtime/report-ref, the later APS family settlement packet through PR `#148`, and the bounded Layer 3 first-slice workbench shell/API from PR `#184` plus closeout/correction passes through PR `#190`. PR `#191` adds the `30`/`31` plan-preview docs as planning-only second-slice prep for the future workbench route family, and PR `#192` records that state in progress/control metadata; neither makes plan preview or downstream execution scope live. The existing promotion governance family is already sufficient on current `main`, retrieval cutover already exists there as a separate validate-only parity-proof family, and no further later APS family decision or implementation lane is currently justified by default.
- The checked-in fixture corpus now proves manifest-driven parser routing, degradation semantics, downstream usefulness for representative born-digital content, and OCR-success usefulness for the scanned/mixed corpus fixtures in this workspace.
- The current checked-in lower-layer proof basis in this workspace (covers behavior through March 13, 2026) is:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- The current checked-in fresh aggregate gate proof basis in this workspace (covers behavior through March 13, 2026) is:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- The current checked-in dedicated post-challenge validate-only proof basis in this workspace is:
  - `tests/reports/nrc_aps_deterministic_challenge_review_packet_validation_report.json`
- March 25, 2026 hardening commits (`2f597f9`, `90c0c58`) changed diagnostics_ref resolution semantics and visual artifact materialization behavior. Proof of those changes still lives in `backend/tests/test_diagnostics_ref_persistence.py` and the expanded `backend/tests/test_nrc_aps_evidence_bundle_integration.py`. The narrow March 26, 2026 Tier2 closeout resolved the local diagnostics-write blocker and refreshed `tests/reports/nrc_aps_content_index_validation_report.json` plus `tests/reports/nrc_aps_evidence_bundle_validation_report.json` in this workspace. The post-commit March 26, 2026 review-packet closeout refreshed `tests/reports/nrc_aps_deterministic_challenge_review_packet_validation_report.json` via the dedicated validate-only action from current `HEAD`; other checked-in `tests/reports/*.json` artifacts remain historical unless regenerated separately.
- Other checked-in `tests/reports/*.json` artifacts should still be treated as historical snapshots unless explicitly regenerated in the current verification pass.
- **Phase 7A Validation Package**: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136`
- **Phase 7A Artifact Audit**: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit`

## 8. Current continuation posture
The bounded later APS family packet beyond the landed dedicated validate-only runtime/report-ref boundary is now settled on current `main`.

Current settled posture:
1. current `main` now also includes the landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`, the post-PR145 docs/progress sync from PR `#146`, the later APS family settlement closeout from PR `#147`, and the post-PR147 progress-packet closeout from PR `#148`
2. promotion is the landed first later APS family choice beyond the landed dedicated validate-only runtime/report-ref boundary, but live repo truth now also shows the existing promotion governance family already sufficient on current `main`
3. retrieval cutover already exists on current `main` as a separate validate-only parity-proof family rooted in `backend/app/services/aps_retrieval_plane_cutover_validation.py`, `backend/tests/test_aps_retrieval_plane_cutover_validation.py`, `backend/tests/test_aps_retrieval_plane_cutover_gate.py`, `tools/nrc_aps_retrieval_cutover_gate.py`, and `project6.ps1`
4. no further later APS family decision or implementation lane is currently justified by default from this merged-main state
5. do not invent another later APS family lane unless live repo truth proves a concrete gap in the promotion or retrieval-cutover surfaces
6. current `main` also includes the merged deferred-scope prep packet rooted in `24_L3_WB_FREEZE.md`, `25_L3_QUAL1_FREEZE.md`, `26_L3_WB_INPUTS.md`, and `27_L3_QUAL1_INPUTS.md` from PR `#165`, `#168`, and `#172`; current `main` also includes `28_L3_WB_FIRST_SLICE_FREEZE.md` from PR `#178` and `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` from PR `#182` as the governing first-slice scope/API contract, plus the PR `#184` implementation and PR `#185` through PR `#190` closeout/correction passes that make `/review/layer3` and `/api/v1/layer3/...` live only for the bounded first-slice workbench without reopening or extending the settled later APS family packet. PR `#191` adds `30_L3_WB_PLAN_PREVIEW_FREEZE.md` and `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` as only the next planning-only plan-preview slice after explicit Gate C typing commit, and PR `#192` records that state in progress/control metadata; they still leave execution, results, package review, handoff, runtime DB writes, schema widening, qualitative/hybrid/RAG/vector execution, and LLM planning out.

Operational refresh rule:
- preserve the restored lower-layer baseline and current OCR-enabled proof basis
- rerun `.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr` when OCR or corpus behavior changes
- treat `.\project6.ps1 -Action validate-nrc-aps-content-index` plus `.\project6.ps1 -Action validate-nrc-aps-evidence-bundle` as the validate-only refresh path for checked-in lower-layer reports
- use `.\project6.ps1 -Action refresh-nrc-aps-review-gate-reports -NrcApsRunId <run_id>` for adopted review-runtime `gate_reports` plus `summary.gate_results`
- use `.\project6.ps1 -Action refresh-nrc-aps-validate-only-gates -NrcApsRunId <run_id>` plus `.\project6.ps1 -Action validate-nrc-aps-validate-only-gates [-NrcApsRunId <run_id>]` for the landed dedicated validate-only runtime/report-ref boundary

## 9. Primary live authority surfaces for this workstream
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `backend/app/models/models.py`
- `backend/app/services/layer3_session_entry.py`
- `backend/app/services/layer3_typing_entry.py`
- `backend/app/services/layer3_package_entry.py`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/app/services/layer3_aps_citation_handoff.py`
- `backend/app/services/layer3_aps_report_handoff.py`
- `backend/app/services/layer3_aps_report_export_handoff.py`
- `backend/app/services/layer3_aps_context_packet_handoff.py`
- `backend/app/services/layer3_aps_multisource.py`
- `backend/app/services/layer3_aps_report_export_package_handoff.py`
- `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- `backend/app/services/layer3_aps_context_dossier_handoff.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/app/services/nrc_aps_context_dossier_gate.py`
- `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `backend/app/services/review_nrc_aps_details.py`
- `backend/tests/test_layer3_session_entry.py`
- `backend/tests/test_layer3_typing_entry.py`
- `backend/tests/test_layer3_package_entry.py`
- `backend/tests/test_layer3_aps_handoff.py`
- `backend/tests/test_layer3_aps_citation_handoff.py`
- `backend/tests/test_layer3_aps_report_handoff.py`
- `backend/tests/test_layer3_aps_report_export_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_multisource.py`
- `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- `backend/tests/test_layer3_aps_context_dossier_handoff.py`
- `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- `next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`
- `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/connectors_nrc_adams.py`
- `tools/nrc_aps_refresh_review_gate_reports.py`
- `tools/run_nrc_aps_local_corpus_e2e.py`
- `project6.ps1`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- `backend/app/services/nrc_aps_evidence_citation_pack.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_gate.py`
- `backend/app/services/nrc_aps_evidence_report_contract.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_gate.py`
- `backend/app/services/nrc_aps_evidence_report_export_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_gate.py`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/app/models/models.py`
- `backend/app/schemas/api.py`
- `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_media_detection.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_content_index_gate.py`
- `tests/test_nrc_aps_evidence_citation_pack.py`
- `tests/test_nrc_aps_evidence_citation_pack_gate.py`
- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_gate.py`
- `tests/test_nrc_aps_context_packet.py`
- `tests/test_nrc_aps_context_packet_gate.py`
- `tests/test_api.py`
- `backend/tests/test_layer3_aps_handoff.py`
- `backend/tests/test_diagnostics_ref_persistence.py`
- `backend/tests/test_nrc_aps_evidence_bundle_integration.py`
- `tools/run_nrc_aps_document_processing_proof.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`

## 10. Closed Phase 8 Boundary
- **Closed milestone**: Downstream bridge reconciliation and validation from accepted Phase 7A outputs into the APS content tables.
- **Closure criterion satisfied**: Successful population of the APS content tables (`ApsContentDocument`, `ApsContentChunk`, `ApsContentLinkage`); Evidence Bundle execution remained a downstream consumer and was **not** required for closure.
- **Authoritative inputs used for closure**:
  - Content Schema: `aps_content_units_v2` (extracted text units, table markdown units, quality metadata)
  - Validation Basis: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136`
  - Audit Basis: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit`
- **Immutable Facts**: OCR (19) and Table (28) counts are frozen as verified in the Artifact Audit.
- **Do Not Reopen**: Ingestion routing logic and advanced capability adapters are considered stable/frozen for this closed bridge milestone.

## 11. Phase 7A Closeout Archive
- **Closeout Package**: [handoff/phase_7a_closeout/](../../handoff/phase_7a_closeout/)
- **Audit Findings**: Corroborated internal consistency and evidence provenance.
