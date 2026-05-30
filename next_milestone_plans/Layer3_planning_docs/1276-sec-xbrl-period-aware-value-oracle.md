# 1276 - SEC XBRL Period-Aware Value Oracle

## Target

`sec_xbrl_period_aware_divided_unit_value_oracle_v1`

## Purpose

This slice adds an explicit period-aware CompanyFacts value-match metric beside the existing period-blind metric used by the SEC XBRL real-corpus product runner and measurement diagnostic.

The existing period-blind metric and `MIN_COMPANYFACTS_MATCH_RATE = 0.98` gate remain unchanged. This slice does not switch the gate, raise the threshold, enable defaults, run live SEC network, invoke Arelle, reveal values, acquire filings, create sidecars, create datasets, create audit receipts, or admit production readiness.

## Implementation

Files:

- `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`
- `diagnostics/assessment/sec-xbrl-measure.py`
- `backend/tests/test_sec_xbrl_real_corpus_product_runner.py`
- `backend/tests/test_sec_xbrl_measure_companyfacts.py`

The existing metric continues to key CompanyFacts candidates by concept and unit only. The new additive metric keys candidates by concept, unit, and period. It also normalizes divided units only inside the period-aware metric, allowing per-share units to participate without changing the currency-only behavior of the existing gated metric.

## New Fields

Per filing:

- `companyfacts_effective_value_match_count_period_aware`
- `companyfacts_effective_value_compared_count_period_aware`
- `companyfacts_effective_value_mismatch_count_period_aware`
- `companyfacts_effective_value_match_rate_period_aware`

Summary:

- `companyfacts_value_match_count_period_aware`
- `companyfacts_value_compared_count_period_aware`
- `companyfacts_value_mismatch_count_period_aware`
- `companyfacts_value_match_rate_period_aware`

The measurement diagnostic also reports period-aware aggregate match, compared, and rate fields in its CompanyFacts effective-value summary.

## Guardrails

- Runtime defaults remain off.
- The existing period-blind fields and gate remain the compatibility posture.
- Divided-unit normalization is used only by the new period-aware metric.
- The committed changes contain no raw issuer identity, accessions, SEC URLs, local storage roots, raw runtime artifacts, or real filing values.
- This slice does not claim default-on readiness, production readiness, final financial-statement semantics, cross-company comparability, statement assembly, FX comparability, UI behavior, Candidate B routing, RAG, model, provider, auth, or package behavior.

## Validation

Focused tests cover:

- period-aware matching that skips unmatched periods while preserving the existing conservative period-blind result;
- divided-unit matching for per-share facts in the period-aware metric while the existing currency-only metric remains unchanged;
- parallel divided-unit behavior in the measurement diagnostic.

## Next Slice

`sec_xbrl_canonical_comparability_validate_only_v1`

The next slice should add the validate-only canonical comparability diagnostic as a separate PR after this metric-fidelity slice lands.
