# NRC APS Portable Handoff Package

This `handoff/` directory is the portable current-state NRC ADAMS APS package for the frozen upper analytical ceiling through Deterministic Challenge Artifact v1 plus the reopened lower-layer document-processing status surfaces.

It is meant to let a new session determine:
- the current frozen ceiling
- which lower layers have been reopened additively
- the authoritative validator/gate semantics
- the current proof basis
- the current run-ref/report-ref surfaces
- the next safe direction above the frozen ceiling

## Package truth model

- This package uses the mixed model (`MODEL B`).
- Package-local control docs:
  - `handoff/README.md`
  - `handoff/START_HERE.txt`
  - `handoff/HANDOFF_INDEX.md`
  - `handoff/handoff_manifest.json`
  - `handoff/docs/nrc_adams/nrc_aps_status_handoff.md`
- Mirrored files:
  - code/tests/proof anchors declared in `handoff/handoff_manifest.json` with `entry_mode=mirrored_copy`
  - EXPLICIT STALE MIRROR WARNING: `handoff/backend/*` is explicitly STALE lineage garbage, NOT implementation authority. Trust ONLY live root `backend/app/services/*`.
- Source-of-truth precedence:
  - live repo code and live repo authority docs
  - package-local handoff controls for portable navigation
  - historical docs only when not contradicted by live repo state

## Manifest coverage semantics

- `handoff/handoff_manifest.json` is intentionally scoped, not exhaustive of every file under `handoff/`.
- `entries` is exhaustive for the packaged current-state authority subset.
- `_legacy_flat_copy/` remains historical-only lineage content outside the current authority subset.

## Current frozen ceiling

Upper analytical closed/frozen layers now extend through:

1. replay regression control
2. 2A sync delta / drift correctness
3. operational safeguards
4. 2B promotion governance
5. evidence retrieval / assembly
6. citation-pack v1
7. evidence-report v1
8. evidence-report export v1
9. evidence-report export package v1
10. Context Packet v1
11. Context Dossier v1
12. Deterministic Insight Artifact v1
13. Deterministic Challenge Artifact v1

Current additive lower-layer workstream now lives in the live repo:
- media detection
- document extraction / OCR wiring
- artifact ingestion metadata expansion
- content units v2 / chunking v2
- parse-timeout enforcement and run-target diagnostics persistence
- manifest-driven corpus proof and fresh isolated lower-layer proof regeneration

Current proof honesty note:
- current fresh OCR-enabled lower-layer proof carried in this repo/package is:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- current fresh aggregate gate proof carried in this repo/package is:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- other checked-in `tests/reports/*.json` files in the repo and package are historical snapshots unless explicitly regenerated in the current verification pass

## Deterministic Challenge Artifact v1 truth surfaces in this package

- Contract/service/gate:
  - `handoff/backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`
  - `handoff/backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
  - `handoff/backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`
- Current ceiling dependency immediately below:
  - `handoff/backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
  - `handoff/backend/app/services/nrc_aps_deterministic_insight_artifact.py`
  - `handoff/backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- API/schema/run-surfacing:
  - `handoff/backend/app/api/router.py`
  - `handoff/backend/app/schemas/api.py`
  - `handoff/backend/app/services/connectors_sciencebase.py`
- Operator wiring:
  - `handoff/project6.ps1`
  - `handoff/tools/nrc_aps_deterministic_challenge_artifact_gate.py`
- Proof:
  - `handoff/tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
  - `handoff/tests/test_nrc_aps_deterministic_challenge_artifact_contract.py`
  - `handoff/tests/test_nrc_aps_deterministic_challenge_artifact.py`
  - `handoff/tests/test_nrc_aps_deterministic_challenge_artifact_gate.py`
  - `handoff/tests/test_api.py`

## Validator semantics

Standalone validators for export, export-package, context-packet, context-dossier, deterministic-insight, and deterministic-challenge are validate-only:

- they validate existing persisted test-runtime artifacts
- they fail closed on empty runtime
- they do not generate artifacts

Relevant actions:

- `./project6.ps1 -Action validate-nrc-aps-evidence-report-export`
- `./project6.ps1 -Action validate-nrc-aps-evidence-report-export-package`
- `./project6.ps1 -Action validate-nrc-aps-context-packet`
- `./project6.ps1 -Action validate-nrc-aps-context-dossier`
- `./project6.ps1 -Action validate-nrc-aps-deterministic-insight-artifact`
- `./project6.ps1 -Action validate-nrc-aps-deterministic-challenge-artifact`

## Current aggregate gate note

- `./project6.ps1 -Action gate-nrc-aps` now includes Challenge pytest coverage in current code.
- It now invokes `validate-nrc-aps-deterministic-challenge-artifact` inside the aggregate path after the Insight validator.
- Fresh full aggregate PASS was rerun on March 13, 2026.
- Current aggregate proof basis is:
  - aggregate pytest slice: `143 passed, 29 deselected`
  - post-validator dossier ambiguity negative slice: `1 passed, 55 deselected`
  - refreshed PASS reports for evidence bundle, citation pack, evidence report/export/package, context packet, context dossier, deterministic insight, and deterministic challenge
- Current Challenge validation report remains PASS with `checked_runs=1` inside that refreshed aggregate report set.

## Dossier retrieval note

- `owner_run_id` is excluded from dossier identity by design.
- The same `context_dossier_id` may legitimately exist across multiple run scopes.
- Current id-only dossier retrieval therefore fails closed on ambiguity with `409 context_dossier_conflict`.
- Use `context_dossier_ref` for deterministic retrieval in that case.

## Operator note

- Current `gate-nrc-aps` dossier behavior still matches the accepted operator isolation: the main API pytest slice excludes only `test_nrc_context_dossier_get_fails_closed_on_ambiguous_id`, and that negative dossier ambiguity test runs after the validator phase.
- Current live `validate-nrc-aps-context-packet` also invokes the dossier gate in the same action block. This package records that live operator truth and does not treat it as settled design precedent.

## Canonical docs in this package

- `handoff/START_HERE.txt`
- `handoff/HANDOFF_INDEX.md`
- `handoff/handoff_manifest.json`
- `handoff/docs/nrc_adams/nrc_aps_status_handoff.md`

## Next safe direction

OCR-enabled lower-layer proof is now established in this workspace. The next safe direction can move above Deterministic Challenge Artifact v1; rerun `.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr` when changing OCR/corpus behavior or validating a new environment. The OCR adapter now auto-detects the standard Windows Tesseract install path as well as `PATH`/`TESSERACT_CMD`. Do not reopen the frozen upper analytical layers except for defect-driven work.

## Historical surfaces

- `handoff/_legacy_flat_copy/` is intentionally historical reference content.
- It is preserved for lineage only and is not the current authority package.
