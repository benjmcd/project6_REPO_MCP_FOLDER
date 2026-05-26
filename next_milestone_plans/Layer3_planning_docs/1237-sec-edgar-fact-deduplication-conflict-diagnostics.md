# SEC EDGAR Fact Deduplication Conflict Diagnostics

milestone: sec_edgar_fact_deduplication_conflict_diagnostics_v1
source_standard_concept_mapping_profile: next_milestone_plans/Layer3_planning_docs/1236-sec-edgar-standard-concept-mapping-profile.md
diagnostics_version: sec_edgar_fact_deduplication_conflict_diagnostics_v1
diagnostics_scope: redacted_fact_identity_and_conflict_basis_hash_profile

The fact de-duplication/conflict diagnostics pass adds bounded, redacted evidence over the classification inventory for exact duplicate candidates and conflicting fact candidates. It is diagnostic-only: it does not deduplicate facts, resolve conflicts, drop values, normalize facts, or admit final financial-statement semantics.

## Runtime Evidence

The statement classification receipt now carries aggregate diagnostics:

```text
fact_deduplication_conflict_diagnostics_version: sec_edgar_fact_deduplication_conflict_diagnostics_v1
fact_deduplication_conflict_diagnostics_hash: hash_bound
fact_deduplication_conflict_diagnostics_status: bounded_status
fact_identity_group_count: bounded_count
fact_conflict_basis_group_count: bounded_count
exact_duplicate_fact_group_count: bounded_count
exact_duplicate_fact_candidate_count: bounded_count
conflicting_fact_group_count: bounded_count
conflicting_fact_candidate_count: bounded_count
exact_duplicate_fact_group_hashes_hash: hash_bound
conflicting_fact_group_hashes_hash: hash_bound
fact_deduplication_performed: false
fact_conflict_resolution_performed: false
fact_values_dropped: false
```

## Product Surface

The quality matrix and operator product surface expose the diagnostics status, hash, counts, group hashes, and non-action flags. This remains a server receipt projection only and does not create frontend durable authority.

next_exact_posture: sec_edgar_cross_company_comparability_readiness_audit_v1
