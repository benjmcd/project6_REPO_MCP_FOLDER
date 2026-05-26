# SEC EDGAR Standard Concept Mapping Profile

milestone: sec_edgar_standard_concept_mapping_profile_v1
source_extension_taxonomy_retention_profile: next_milestone_plans/Layer3_planning_docs/1235-sec-edgar-extension-taxonomy-retention-profile.md
profile_version: sec_edgar_standard_concept_mapping_profile_v1
profile_scope: redacted_standard_taxonomy_role_family_hash_profile

The standard concept mapping profile adds bounded, redacted evidence that each fact has a standard-concept profile record derived from taxonomy class, statement role, and concept family. It profiles standard taxonomy concepts and preserves issuer extensions as unmapped evidence. It does not normalize concepts, resolve taxonomy networks, call SEC Companyfacts, or admit cross-company comparability.

## Runtime Evidence

The statement classification receipt now carries `standard_concept_mapping_profile` inside every semantic profile and aggregates:

```text
standard_concept_mapping_profile_version: sec_edgar_standard_concept_mapping_profile_v1
standard_concept_mapping_profile_hash: hash_bound
standard_concept_mapping_profile_assigned_count: fact_count
standard_concept_profiled_count: bounded_count
issuer_extension_standard_concept_unmapped_count: bounded_count
unknown_taxonomy_standard_concept_unmapped_count: bounded_count
standard_concept_mapping_performed: false
standard_concept_normalization_performed: false
cross_company_comparability_admitted: false
```

## Product Surface

The quality matrix and operator product surface expose the standard-concept profile status, hash, assigned count, profiled count, unmapped counts, and non-admission flags. This remains a server receipt projection only and does not create frontend durable authority.

next_exact_posture: sec_edgar_fact_deduplication_conflict_diagnostics_v1
