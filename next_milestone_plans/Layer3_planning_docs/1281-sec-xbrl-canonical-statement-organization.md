# 1281 - SEC XBRL Canonical Statement Organization

## Target

`sec_xbrl_canonical_statement_organization_validate_only_v1`

## Purpose

This slice validates the reviewed canonical statement crosswalk from Lineage B against Lineage A's independent statement-role classifier. It does not add financial-statement assembly or change either lineage's runtime behavior. B's `statement` field remains the authoritative organization source; A is used only as corroborating evidence and taxonomy-divergence measurement.

## Scope

Files:

- `backend/app/services/layer3_sec_xbrl_canonical_statement_organization.py`
- `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.py`
- `diagnostics/assessment/sec-xbrl-canonical-statement-organization.py`
- `diagnostics/assessment/sec-xbrl-canonical-statement-organization-report.json`
- `backend/tests/test_sec_xbrl_canonical_statement_organization.py`

The only Lineage A change is the public `statement_role_view_from_retained_records(records)` accessor. It reuses the existing `_classify_role` and `_concept_family` helpers and does not change the gated `classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates` entrypoint, classifier rules, receipt shape, downstream product chain, or hashes.

The new statement-organization primitive imports neither SEC XBRL lineage. It consumes canonical projection items that already carry B's `statement`, plus the A accessor's per-fact role view, and joins them by resolved fact authority.

## Contract

Pass gates:

- `contract_b_authoritative_organization`: every non-absent projected canonical fact has a B statement in `income`, `balance`, or `cashflow`.
- `contract_every_fact_id_bound`: every direct projected fact joins to an A role view record by resolved fact authority.
- `contract_derived_inputs_bound_and_corroborated`: every derived canonical fact has both source input ids bound and A-corroborated for the B statement.
- `contract_passed`: all gates pass and normalized fact count is non-zero.

Reported measures, not gates:

- `a_corroborated_count`
- `a_divergent_count`
- `a_role_unknown_count`
- `a_divergent`
- `a_role_unknown`
- `a_full_corroboration`

The alignment map is versioned as `sec_xbrl_canonical_statement_alignment_v1`:

- `income` aligns with `income_statement` and `comprehensive_income_statement`
- `balance` aligns with `balance_sheet` and `stockholders_equity_statement`
- `cashflow` aligns with `cash_flow_statement`

## Evidence

The committed diagnostic report is a redacted taxonomy aggregate. It records:

- US-GAAP taxonomy: 1 reference filing, 22 normalized facts, 22 A-corroborated, 0 divergent, 0 unknown, 2 derived with both derived inputs corroborated.
- IFRS taxonomy: 2 reference filings, 42 normalized facts, 36 A-corroborated, 2 divergent, 4 unknown, 0 unjoined.
- Known IFRS A-classifier drift set: `OperatingIncome[total]` classified by A as `cash_flow_statement`; `Equity[total]` and `Equity[parent]` classified by A as `unknown_or_unclassified`.

These IFRS divergences document Lineage A heuristic limitations and do not fail the B-authoritative organization contract.

## Guardrails

- Under 1317, Arelle fact-authority cutover is admitted default-on; live SEC network, value reveal, and controlled value-reveal submit remain default-off.
- This is validate-only: no live SEC network, no Arelle invocation, no value reveal, no source acquisition, no runtime artifact generation, no persistence, and no config change beyond the already-admitted 1317 cutover posture.
- Existing canonical concept resolution/projection logic is not changed.
- Existing retained coherence logic is not changed.
- Existing Lineage A classifier rules and gated entrypoint behavior are not changed.
- Sector-conditioned canonical families, statement assembly, per-period projection, persisted store behavior, linkbase emission, FX/scale normalization, provider/model/RAG/auth behavior, and default-on readiness remain deferred.
- The committed report excludes issuer identities, accessions, period dates, URLs, local paths, raw financial values, raw resolved fact authorities, source qualified names, and raw retained total-fact counts.

## Validation

Required validation before merge:

- focused canonical statement-organization tests
- existing canonical retained-coherence, canonical projection, canonical coverage-breadth, canonical comparability, material-bridge, and statement-classification import-affected suites
- diagnostic report generation
- JSON validation for the committed report and progress manifests
- `tools/l3-progress-check.py`
- `git diff --check`
- redaction scan over added or changed files, with the committed report checked for absence of issuer identities, source accessions, period dates, source URLs, local paths, raw values, raw resolved fact authorities, source qualified names, and raw retained total-fact counts
