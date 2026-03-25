# Handoff Package Index

## Authoritative Implementation
- `backend/app/services/nrc_aps_advanced_ocr.py` (PaddleOCR Adapter)
- `backend/app/services/nrc_aps_advanced_table_parser.py` (Camelot Adapter)
- `backend/app/services/nrc_aps_document_processing.py` (Updated routing and extraction)
- `backend/app/services/nrc_aps_settings.py` (Advanced routing triggers)

## Authoritative Evidence
- **Validation Package**: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136`
- **Audit Findings**: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit`

## Documentation Entrance
1. [nrc_aps_status_handoff.md](../../docs/nrc_adams/nrc_aps_status_handoff.md) - Canonical Repo Truth.
2. [closeout_summary.md](closeout_summary.md) - This summary.
3. [accepted_facts.json](accepted_facts.json) - Machine-readable metrics.

## Engineering Read Order
1. Review `docs/nrc_adams/nrc_aps_status_handoff.md` for current operational state.
2. Review the `artifact_audit_report.md` in the validation package for proof of work.
3. Inspect `nrc_aps_document_processing.py` for advanced feature routing logic.
