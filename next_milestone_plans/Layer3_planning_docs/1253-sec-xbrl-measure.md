# SEC XBRL Coverage Measurement

```yaml
milestone: sec_edgar_xbrl_processor_adapter_and_source_fidelity_assessment_v1_part1
governing_strategy: strategy_a_governed_sec_edgar_ingestion_integrity_provenance_coverage_product
strategy_b_arelle_companyfacts_semantic_resolution: deferred_criteria_gated_later_decision
supersedes_selected_posture: sec_edgar_statement_role_quality_profile_rendered_detail_ui_v1
assessment_scope: measure_strategy_a_fact_coverage_trust_only
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

Live current-main authority for this pass was `17d6068ab0b6f286770a4d31460377531f24355d`, matching `project6-origin/main`.

The prior selected posture remains visible in current-main planning/checker text, but this human-governed measurement pass supersedes it for sequencing. This document does not implement that rendered statement-role detail card.

## Measurement Artifact

The deterministic measurement script is quarantined at:

```text
diagnostics/assessment/sec-xbrl-measure.py
```

The generated measurement report is:

```text
diagnostics/assessment/sec-xbrl-report.json
```

The script is diagnostic-only. It is not imported by Layer 3 services and creates no runtime authority.

## Fixture Inventory

```text
committed_ixbrl_candidate_count: 3
real_filing_candidate_count: 0
synthetic_stub_candidate_count: 3
storage_dir_observed: true
storage_dir_gitignored: true
storage_dir_file_count: 0
retained_artifacts_observed: false
retained_artifact_byte_status: absent_empty_storage_dir
```

Only synthetic/minimal iXBRL snippets were found in this environment. No retained real filing bytes were present under the repo default storage directory.

## Oracle Results

```text
primary_companyfacts:
  oracle_used: false
  confidence: unverified
  reason: no retained real filing bytes or real filing fixture identity existed in this environment

gold_arelle:
  oracle_used: false
  confidence: available_no_real_input
  reason: contained Arelle invocation succeeded, but no real retained iXBRL filing input existed for gold counts

sanity_shadow_parse:
  oracle_used: true
  confidence: low_lower_bound
  reason: fact-bearing inline XBRL tag-shape count only; shares blind spots with the parser under test
```

The contained Arelle environment was created outside the repo and outside OneDrive. No Arelle code, cache, or output was committed.

## Per-Fixture Table

| fixture_hash | form | fixture_class | current_parser_fact_count | oracle_fact_count | oracle_used | missed_count | missed_categories | confidence |
| --- | --- | --- | ---: | ---: | --- | ---: | --- | --- |
| `371930594e0cc23415822fbc` | 10-K | synthetic_stub | 1 | null | none_real_oracle_unavailable_synthetic_fixture | null | none_observed_in_fixture | inconclusive |
| `371930594e0cc23415822fbc` | 10-K | synthetic_stub | 1 | null | none_real_oracle_unavailable_synthetic_fixture | null | none_observed_in_fixture | inconclusive |
| `51e402bba322811d84231722` | unknown | synthetic_stub | 1 | null | none_real_oracle_unavailable_synthetic_fixture | null | none_observed_in_fixture | inconclusive |

The repeated fixture hash reflects the same synthetic snippet appearing in more than one committed test source.

## Headline Finding

```text
UNVERIFIED: current parser fact coverage cannot be graded from this environment because only synthetic/minimal iXBRL fixtures and no retained real filing bytes were found.
```

## Preserved Non-Admissions

```text
final_financial_statement_semantics_claimed: false
cross_company_comparability_claimed: false
runtime_authority_created: false
parser_expansion_performed: false
value_unredaction_performed: false
candidate_b_sec_routing_performed: false
raw_tickers_urls_paths_storage_roots_committed: false
```

## Stop Posture

Stop after this bounded measurement pass. Do not proceed to adapter design, platform-fit assessment, CompanyFacts cross-check design, ADR, invariant registration, issuer breadth, or rendered UI work in this pass.
