# HANDOFF Index

This file maps the portable `handoff/` package across package-local controls and mirrored live-repo surfaces.

## 1. Package Role

- Package type: current-state portable handoff for the frozen upper analytical ceiling through Deterministic Challenge Artifact v1 plus the reopened lower document-processing workstream.
- Truth model: mixed package (`MODEL B`).
- Control docs (`handoff/README.md`, `handoff/START_HERE.txt`, `handoff/HANDOFF_INDEX.md`, `handoff/handoff_manifest.json`, `handoff/docs/nrc_adams/nrc_aps_status_handoff.md`) are package-local handoff surfaces.
- Code/tests/proof anchors are mirrored copies unless explicitly marked otherwise in `handoff/handoff_manifest.json`.
- Source-of-truth precedence is live repo first, then handoff navigation controls, then historical docs.
- Canonical status file in package: `handoff/docs/nrc_adams/nrc_aps_status_handoff.md`.
- Manifest of entry mode/provenance: `handoff/handoff_manifest.json`.
- Entry guide: `handoff/START_HERE.txt`.
- Manifest coverage semantics: intentionally scoped current-state authority subset, not exhaustive of every file under `handoff/`.

## 2. Current Authority Surfaces Included

### Top-level guides
- `handoff/README.md`
- `handoff/START_HERE.txt`
- `handoff/HANDOFF_INDEX.md`
- `handoff/handoff_manifest.json`
- `handoff/docs/nrc_adams/nrc_aps_status_handoff.md`

### Contract/service/gate families (through Deterministic Challenge Artifact v1)
- `handoff/backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- `handoff/backend/app/services/nrc_aps_evidence_citation_pack.py`
- `handoff/backend/app/services/nrc_aps_evidence_citation_pack_gate.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_contract.py`
- `handoff/backend/app/services/nrc_aps_evidence_report.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_gate.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_export_contract.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_export.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_export_gate.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_export_package.py`
- `handoff/backend/app/services/nrc_aps_evidence_report_export_package_gate.py`
- `handoff/backend/app/services/nrc_aps_context_packet_contract.py`
- `handoff/backend/app/services/nrc_aps_context_packet.py`
- `handoff/backend/app/services/nrc_aps_context_packet_gate.py`
- `handoff/backend/app/services/nrc_aps_context_dossier_contract.py`
- `handoff/backend/app/services/nrc_aps_context_dossier.py`
- `handoff/backend/app/services/nrc_aps_context_dossier_gate.py`
- `handoff/backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- `handoff/backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `handoff/backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- `handoff/backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`
- `handoff/backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
- `handoff/backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`

### Reopened lower document-processing surfaces mirrored here (STALE)
> [!WARNING]
> `handoff/backend/*` is an explicitly STALE repository mirror. It is preserved for lineage references only and NOT as live implementation authority. You must use root `backend/` instead.
- `handoff/backend/app/services/connectors_nrc_adams.py`
- `handoff/backend/app/services/nrc_aps_media_detection.py`
- `handoff/backend/app/services/nrc_aps_document_processing.py`
- `handoff/backend/app/services/nrc_aps_ocr.py`
- `handoff/backend/app/services/nrc_aps_artifact_ingestion.py`
- `handoff/backend/app/services/nrc_aps_content_index.py`
- `handoff/backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `handoff/backend/app/services/nrc_aps_evidence_bundle.py`
- `handoff/backend/app/services/nrc_aps_evidence_bundle_gate.py`
- `handoff/backend/app/models/models.py`
- `handoff/backend/app/schemas/api.py`
- `handoff/backend/alembic/versions/0009_aps_document_processing_metadata.py`
- `handoff/backend/requirements.txt`

### API/schema/run-surfacing/operator wiring
- `handoff/backend/app/api/router.py`
- `handoff/backend/app/services/connectors_sciencebase.py`
- `handoff/project6.ps1`
- `handoff/tools/run_nrc_aps_document_processing_proof.py`
- `handoff/tools/nrc_aps_evidence_bundle_gate.py`
- `handoff/tools/nrc_aps_evidence_citation_pack_gate.py`
- `handoff/tools/nrc_aps_evidence_report_gate.py`
- `handoff/tools/nrc_aps_evidence_report_export_gate.py`
- `handoff/tools/nrc_aps_evidence_report_export_package_gate.py`
- `handoff/tools/nrc_aps_context_packet_gate.py`
- `handoff/tools/nrc_aps_context_dossier_gate.py`
- `handoff/tools/nrc_aps_deterministic_insight_artifact_gate.py`
- `handoff/tools/nrc_aps_deterministic_challenge_artifact_gate.py`

### Focused test/proof coverage
- `handoff/tests/test_api.py`
- `handoff/tests/support_nrc_aps_doc_corpus.py`
- `handoff/tests/test_nrc_aps_artifact_ingestion.py`
- `handoff/tests/test_nrc_aps_content_index.py`
- `handoff/tests/test_nrc_aps_content_index_gate.py`
- `handoff/tests/test_nrc_aps_media_detection.py`
- `handoff/tests/test_nrc_aps_document_processing.py`
- `handoff/tests/test_nrc_aps_document_corpus.py`
- `handoff/tests/test_nrc_aps_evidence_bundle_contract.py`
- `handoff/tests/test_nrc_aps_evidence_bundle.py`
- `handoff/tests/test_nrc_aps_evidence_bundle_gate.py`
- `handoff/tests/test_nrc_aps_context_dossier_contract.py`
- `handoff/tests/test_nrc_aps_context_dossier.py`
- `handoff/tests/test_nrc_aps_context_dossier_gate.py`
- `handoff/tests/test_nrc_aps_deterministic_insight_artifact_contract.py`
- `handoff/tests/test_nrc_aps_deterministic_insight_artifact.py`
- `handoff/tests/test_nrc_aps_deterministic_insight_artifact_gate.py`
- `handoff/tests/test_nrc_aps_deterministic_challenge_artifact_contract.py`
- `handoff/tests/test_nrc_aps_deterministic_challenge_artifact.py`
- `handoff/tests/test_nrc_aps_deterministic_challenge_artifact_gate.py`
- `handoff/tests/reports/nrc_aps_document_processing_proof_report.json`
- `handoff/tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
- `handoff/tests/reports/nrc_aps_content_index_validation_report.json`
- `handoff/tests/reports/nrc_aps_context_dossier_validation_report.json`
- `handoff/tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
- `handoff/tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- `handoff/tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `handoff/tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`

Proof note for this package:
- current fresh OCR-enabled lower-layer proof in this package is:
  - `handoff/tests/reports/nrc_aps_document_processing_proof_report.json`
  - `handoff/tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `handoff/tests/reports/nrc_aps_content_index_validation_report.json`
- current fresh aggregate gate proof in this package is:
  - `handoff/tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `handoff/tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `handoff/tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `handoff/tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `handoff/tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `handoff/tests/reports/nrc_aps_context_packet_validation_report.json`
  - `handoff/tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `handoff/tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `handoff/tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- other checked-in `handoff/tests/reports/*.json` files are historical snapshots unless explicitly regenerated in the current verification pass

## 3. Proof Artifacts Included

- `handoff/tests/reports/nrc_aps_document_processing_proof_report.json`
- `handoff/tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
- `handoff/tests/reports/nrc_aps_content_index_validation_report.json`
- `handoff/tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
- `handoff/tests/reports/nrc_aps_evidence_report_validation_report.json`
- `handoff/tests/reports/nrc_aps_evidence_report_export_validation_report.json`
- `handoff/tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
- `handoff/tests/reports/nrc_aps_context_packet_validation_report.json`
- `handoff/tests/reports/nrc_aps_context_dossier_validation_report.json`
- `handoff/tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
- `handoff/tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`

These are the carried proof anchors in the handoff package. The three lower-layer document-processing reports above are current for the OCR-enabled lane, and the aggregate-scoped APS gate reports above are current for the fresh March 13, 2026 aggregate gate rerun; remaining proof artifacts stay historical unless explicitly regenerated.

## 4. Frozen Ceiling and Current Operator Truth

- Closed/frozen upper analytical ceiling: through Deterministic Challenge Artifact v1.
- Reopened lower-layer exception: artifact ingestion, content indexing, and document/media handling are active additive surfaces in the live repo and are mirrored here only for safe continuation of this workstream.
- Validator semantics at this ceiling:
  - validate-only
  - persisted test-runtime artifacts only
  - fail closed on empty runtime
  - no artifact generation
- `gate-nrc-aps` code path now includes Challenge pytest coverage.
- It now invokes the standalone `validate-nrc-aps-deterministic-challenge-artifact` action after the Insight validator.
- Current Challenge aggregate runtime coherence is proven in the live repo.
- Current lower-layer focused verification now includes manifest-driven corpus coverage and fresh isolated proof on March 13, 2026:
  - lower-layer pytest proof: `46 passed`
  - real extracted API proof: `3 passed, 53 deselected`
- Current lower-layer isolated gate proof is fresh on March 13, 2026:
  - `handoff/tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `handoff/tests/reports/nrc_aps_content_index_validation_report.json`
- Current lower-layer fresh proof summary is:
  - `handoff/tests/reports/nrc_aps_document_processing_proof_report.json`
- Fresh full aggregate PASS was rerun on March 13, 2026:
  - aggregate pytest slice: `143 passed, 29 deselected`
  - post-validator dossier ambiguity negative slice: `1 passed, 55 deselected`
  - aggregate validate-only reports refreshed to PASS through Deterministic Challenge Artifact
- Current Challenge report inside that refreshed aggregate report set is:
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json` PASS with `checked_runs=1`
- Current aggregate dossier operator behavior still matches the prior accepted isolation:
  - the main API pytest slice excludes only `test_nrc_context_dossier_get_fails_closed_on_ambiguous_id`
  - that negative dossier ambiguity test runs after the validator phase
- Current live `validate-nrc-aps-context-packet` also invokes the dossier gate in the same action block; this package records that live operator truth and does not treat it as settled design precedent.

## 5. Dossier Retrieval Note

- Same `context_dossier_id` may legitimately exist in more than one run scope.
- Current id-only retrieval fails closed on ambiguity with `409 context_dossier_conflict`.
- `context_dossier_ref` is the deterministic retrieval surface in that case.

## 6. Historical Surfaces

- `handoff/_legacy_flat_copy/` is intentionally historical and kept for lineage/reference.
- It is not the current authority package and was not rewritten as current-state truth in this refresh.
