# SEC XBRL Real Coverage Measurement

```yaml
milestone: sec_edgar_xbrl_processor_adapter_and_source_fidelity_assessment_v1_part1
governing_strategy: strategy_a_governed_sec_edgar_ingestion_integrity_provenance_coverage_product
strategy_b_arelle_companyfacts_semantic_resolution: deferred_criteria_gated_later_decision
supersedes_selected_posture: sec_edgar_statement_role_quality_profile_rendered_detail_ui_v1
assessment_scope: measure_strategy_a_real_fact_coverage_trust_only
runtime_product_gate_b_api_ui_mutation_performed: false
parser_expansion_performed: false
adapter_design_performed: false
adr_written: false
invariant_registration_performed: false
issuer_breadth_added: false
render_work_added: false
value_unredaction_performed: false
candidate_b_sec_routing_performed: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
```

## Authority

Live current-main authority for this pass was `17d6068ab0b6f286770a4d31460377531f24355d`. The measurement branch started from the earlier Part 1 commit and remains a diagnostic/planning-only lane. The prior rendered statement-role detail posture remains superseded for this measurement pass.

## Gate Fix

The diagnostic gate now resolves `settings.storage_dir` at runtime instead of hardcoding `backend/app/storage`. It reports the resolved storage directory only as a hash marker, file counts, SEC receipt directory hashes, and retained-byte presence. It also accepts a configurable corpus path and keeps the stdlib shadow parser labeled as a lower-bound sanity check only.

The diagnostic script is quarantined at:

```text
diagnostics/assessment/sec-xbrl-measure.py
```

Generated redacted outputs:

```text
diagnostics/assessment/sec-xbrl-report.json
diagnostics/assessment/sec-xbrl-corpus.json
```

## Real Corpus

```text
processed_filing_count: 6
issuer_hash_count: 3
forms: 10-K, 8-K, 20-F, 6-K, 40-F
retained_source_bytes_present: true
storage_dir_path_redacted: true
raw_tickers_urls_paths_storage_roots_committed: false
```

The live run used the existing governed connector and live-source-artifact path with live network enabled only in-process for the diagnostic run. Runtime defaults were not changed.

## Oracle Status

```text
gold_arelle:
  oracle_used: true
  confidence: gold_arelle_inline_xbrl_model_fact_count
  filing_count_with_arelle: 6

primary_companyfacts:
  oracle_used: true
  confidence: primary_companyfacts_us_gaap_dei_accession_scope
  filing_count_with_companyfacts: 6

sanity_shadow_parse:
  oracle_used: true
  confidence: low_lower_bound
```

CompanyFacts is accession-scoped and limited to standardized `us-gaap`/`dei` facts. Arelle is the full fact-count comparator for the retained primary iXBRL documents.

## Per-Filing Trust Table

| fixture_hash | form | prod_factauthority | companyfacts | arelle | missed | confidence | pipeline |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `e2a1ce9350e4e36a977f2c92` | 10-K | 438 | 359 | 643 | 205 | gold_arelle_count_available | ready |
| `89552a931742f0f75ab5d071` | 8-K | 23 | 0 | 23 | 0 | gold_arelle_count_available | ready |
| `fc184386967ce997055b62e1` | 20-F | 2019 | 0 | 5000 | 2981 | gold_arelle_count_available | fact_material_bridge_fact_count_mismatch |
| `69a4911cba60d2db0c2bfd02` | 6-K | 0 | 0 | 0 | 0 | gold_arelle_count_available | fact_authority_no_inline_xbrl_markers |
| `dd5a43fd97ace277e35a8917` | 40-F | 43 | 2 | 43 | 0 | gold_arelle_count_available | ready |
| `79db4eac8f68f3307aaa23b3` | 6-K | 0 | 0 | 0 | 0 | gold_arelle_count_available | fact_authority_no_inline_xbrl_markers |

Main missed/degradation categories observed:

```text
ix_hidden_present
continuation_present
contexts_present_but_unresolved
units_present_but_unresolved
text_segment_inventory_cap_possible
unsupported_marker_shape
fact_authority_no_inline_xbrl_markers
fact_material_bridge_fact_count_mismatch
```

## Headline Finding

```text
POOR: production fact-authority coverage captured only 2523/5709 Arelle facts across real filings.
```

The governed acquisition and retained-byte path works for this corpus. The fact coverage is not trustworthy enough to protect Strategy A product claims without a hardening pass. Three filings reached bridge/classification readiness; one high-fact 20-F blocked at fact-material bridge parity, and two 6-Ks had no inline XBRL markers for fact authority.

## Preserved Non-Admissions

```text
final_financial_statement_semantics_claimed: false
cross_company_comparability_claimed: false
runtime_authority_created_by_diagnostic: false
parser_expansion_performed: false
value_unredaction_performed: false
candidate_b_sec_routing_performed: false
raw_tickers_urls_paths_storage_roots_committed: false
```

## Stop Posture

Stop after this bounded measurement pass. Do not proceed to adapter design, platform-fit assessment, CompanyFacts design, ADR, invariant registration, issuer breadth, or rendered UI work in this pass.
