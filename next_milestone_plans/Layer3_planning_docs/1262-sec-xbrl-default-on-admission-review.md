# 1262 - SEC XBRL Default-On Admission Review

## Target

`sec_edgar_arelle_default_off_to_default_on_admission_review_v1`

## Governing posture

This is a review and admission-prep slice. It must not flip the runtime default by itself.

The Arelle fact-authority path is now admitted as a default-on candidate by the corpus gate, but the actual default change still needs an explicit review of rollback, Arelle-absent behavior, local/CI posture, operator value reveal boundaries, and remaining non-admissions.

## Evidence now available

- count/DTS completeness: `18,156/18,156` independent raw inline facts reconciled on the original expanded corpus
- bridge parity: `18,156/18,156` sidecar facts materialized on the structural cutover corpus
- value materialization: `23,102/23,102` sidecar facts materialized on a 16-filing value corpus
- CompanyFacts effective-value correctness: `3,761/3,790` matched on the accession-scoped standard numeric intersection
- required value-correctness forms include `10-K` and `10-Q`

## Review requirements

- prove flag default remains off before the actual default-change slice
- prove Arelle-absent app/test behavior remains green
- define rollback criteria for missing sidecar, stale lineage, blocked value store, taxonomy/cache failure, and redaction violation
- keep non-PDF SEC semantics out of Candidate B
- keep final financial-statement semantics and cross-company comparability non-admitted
- keep operator value reveal explicitly gated and capped

## Next slice

If the admission review passes:

`sec_edgar_arelle_fact_authority_default_on_runtime_v1`

That future slice may change the default only with the review evidence attached and with immediate rollback proof.
