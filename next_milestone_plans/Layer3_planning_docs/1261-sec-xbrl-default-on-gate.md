# 1261 - SEC XBRL Default-On Gate

## Target

`sec_edgar_arelle_default_on_corpus_expansion_gate_v1`

## Governing posture

This is an admission gate, not a runtime cutover. It reads the current redacted SEC XBRL diagnostic reports and decides whether the Arelle fact-authority cutover is ready to be considered for default-on behavior.

The gate does not acquire filings, run Arelle, mutate bridge/Gate B/product/package/UI behavior, expose values, or change the default-off flag.

## Gate criteria

The default-on candidate must have all of the following current evidence:

- corpus breadth across at least 12 real filings, at least 6 issuer hashes, and forms `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`
- independent raw inline count reconciliation and zero unresolved DTS concepts
- flag-on bridge parity across the expanded corpus
- internal effective-value materialization across the same expanded corpus
- CompanyFacts effective-value correctness for the standard numeric intersection, including both `10-K` and `10-Q` forms

## Current decision

Current evidence does not admit default-on behavior yet.

The count/DTS and structural bridge evidence cover the expanded 12-filing corpus, but the value materialization and CompanyFacts effective-value correctness reports still cover the later 8-filing value corpus. That leaves the 10-Q expansion filing without effective-value correctness proof.

## Required follow-up

`sec_edgar_arelle_expanded_value_materialization_and_companyfacts_gate_v1`

Scope:

- rerun the value materialization report over the expanded corpus
- prove bridge effective values across the same 12-filing sidecar/completeness corpus
- prove CompanyFacts effective-value correctness includes both 10-K and 10-Q standard numeric intersections
- preserve default-off behavior and all existing non-admissions

Only after that gate passes should a default-on admission review be considered.
