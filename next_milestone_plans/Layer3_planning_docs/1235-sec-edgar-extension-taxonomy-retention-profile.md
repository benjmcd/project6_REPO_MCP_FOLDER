# SEC EDGAR Extension Taxonomy Retention Profile

milestone: sec_edgar_extension_taxonomy_retention_profile_v1
source_statement_role_quality_profile: next_milestone_plans/Layer3_planning_docs/1234-sec-edgar-statement-role-quality-profile.md
entry_decision: runtime_implementation
runtime_status: implemented

## Scope

The extension taxonomy retention profile adds redacted, hash-bound evidence that issuer extension concepts are retained, surfaced, and marked unmapped instead of silently dropped or promoted into final semantics. It does not resolve extension taxonomy networks, does not call SEC Companyfacts, and does not admit cross-company comparability.

## Runtime Evidence

profile_version: sec_edgar_extension_taxonomy_retention_profile_v1
profile_scope: redacted_extension_namespace_qualified_name_hash_profile
extension_taxonomy_retention_surface: extension_taxonomy_retention_profile
extension_taxonomy_retention_profile_hash: receipt_bound
extension_taxonomy_retention_profile_assigned_count: fact_count_bound
retained_company_extension_profile_count: recorded
standard_taxonomy_retention_profile_count: recorded
unknown_taxonomy_retention_profile_count: recorded
extension_taxonomy_mapping_performed: false
taxonomy_network_resolution_performed: false
sec_companyfacts_api_called: false
extension_taxonomy_facts_dropped: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false

## Product Surface

The operator product surface exposes extension taxonomy retention profile status, profile hash, assigned count, retention counts, and non-admission flags. It remains a server receipt projection only and does not create frontend durable authority.

next_exact_posture: sec_edgar_standard_concept_mapping_profile_v1
