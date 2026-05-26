# SEC EDGAR Statement Role Quality Profile

milestone: sec_edgar_statement_role_quality_profile_v1
source_period_unit_context_dimension_profile: next_milestone_plans/Layer3_planning_docs/1233-sec-edgar-period-unit-context-dimension-profile.md
entry_decision: runtime_implementation
runtime_status: implemented

## Scope

The statement-role quality profile adds redacted, hash-bound evidence for how SEC HTML/iXBRL facts were assigned to statement candidate roles. It does not finalize financial-statement semantics, does not resolve taxonomy presentation linkbase roles, and does not admit cross-company comparability.

## Runtime Evidence

profile_version: sec_edgar_statement_role_quality_profile_v1
profile_scope: redacted_statement_role_rule_confidence_profile
statement_role_quality_surface: statement_role_quality_profile
statement_role_quality_profile_hash: receipt_bound
statement_role_quality_profile_assigned_count: fact_count_bound
medium_statement_role_confidence_count: recorded
low_statement_role_confidence_count: recorded
presentation_linkbase_role_resolution_performed: false
taxonomy_network_resolution_performed: false
statement_role_semantics_finalized: false
statement_role_semantics_claimed: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false

## Product Surface

The operator product surface exposes statement-role quality profile status, profile hash, assigned count, confidence counts, and non-admission flags. It remains a server receipt projection only and does not create frontend durable authority.

next_exact_posture: sec_edgar_extension_taxonomy_retention_profile_v1
