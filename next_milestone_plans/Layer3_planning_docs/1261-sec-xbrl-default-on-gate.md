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

Current evidence admits default-on behavior as a candidate for an explicit admission review. This is not itself a default-on runtime change.

The count/DTS and structural bridge evidence cover the expanded 12-filing corpus. The value materialization evidence now covers a 16-filing superset with `23,102` sidecar facts materialized through the bridge, including the 10-Q expansion filing. CompanyFacts effective-value correctness is `3,761/3,790` over the accession-scoped standard numeric intersection and includes both 10-K and 10-Q evidence.

## Required follow-up

`sec_edgar_arelle_default_off_to_default_on_admission_review_v1`

Scope:

- review the default-on candidate evidence without changing the runtime default
- confirm CI/local behavior remains green with Arelle absent and the flag defaulting off
- define the exact default-on admission switch and rollback criteria
- preserve the explicit operator-gated value reveal policy
- preserve default-off behavior and all existing non-admissions

Only after that review should a runtime-default change be considered.
