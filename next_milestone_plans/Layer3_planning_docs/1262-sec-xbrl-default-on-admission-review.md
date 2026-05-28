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

## Review result

`diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json`

Decision on the admission-review slice after PR #1966 governance remediation:
`admission_review_requires_post_1966_governance_followup`.

The runtime default remains off. The report retains the Arelle candidate evidence, but it no longer marks the default-on runtime slice ready while `1261-sec-xbrl-arelle-governance-remediation.md` requires another default-on attempt to first restate the sidecar selection, product-path readiness, completeness aggregation, CompanyFacts oracle coverage and mismatch framing, no-silent-regex-fallback, and redaction evidence.

The Arelle path remains implemented and available behind explicit flag admission. The admission evidence is retained as candidate evidence only; it is not current runtime default-on admission.

## Next slice

If the operator wants to attempt default-on again:

`sec_edgar_arelle_governance_remediation_followups_v1`

That follow-up must refresh the governance evidence before any future `sec_edgar_arelle_fact_authority_default_on_runtime_v1` slice can be selected again.
