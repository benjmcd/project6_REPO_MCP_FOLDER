# Candidate B Broader Eligible Corpus Default Scope Selection

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selection_v1
source_operator_workflow_proxy_owner_storage_policy_runtime: next_milestone_plans/Layer3_planning_docs/1067-cb-operator-workflow-proxy-owner-storage-policy-runtime.md
current_main_entry: 39c23a61c306695b801158fef6e871182a825f46
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_audit_target: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
selected_decision_scope: candidate_b_default_scope_after_eligible_effective_pdf_acceptance
current_default_scope: eligible_effective_pdfs_only
selected_evaluation_mode: read_only_no_runtime_scope_readiness_audit
default_scope_expansion_admitted_now: false
non_pdf_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
bundle_and_runtime_authority_remain_distinct: true
pdf_scope_already_accepted: eligible_effective_pdfs
candidate_scope_classes_to_audit: office_documents,images_or_ocr,zip_members,structured_json_or_csv_or_xlsx,sec_edgar,web_or_database_sources,mixed_corpus_batches
required_scope_evidence: exact_corpus_class_list,explicit_exclusion_list,current_parser_or_engine_authority,baseline_rollback_behavior,candidate_a_interaction,candidate_b_runtime_compatibility,layer3_material_authority_bridge_compatibility,artifact_family_preservation,redaction_and_status_projection,corpus_scale_proof,fail_closed_stale_or_missing_authority,regression_disposition
selector_mutation_admitted: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
```

This freeze records the next bounded decision after Candidate B reached accepted default status for eligible/effective PDFs and after the proxy-owner storage policy runtime landed. It does not broaden Candidate B default behavior. The current default remains Candidate B only for eligible/effective PDF processing, while non-PDF processing remains baseline and explicit baseline rollback remains available.

The selected next slice is a read-only readiness audit. Its job is to classify whether any broader eligible-corpus default scope can be admitted later, not to implement that expansion. The audit must name exact corpus classes, exclusion classes, parser or engine authority, fallback behavior, Candidate A interaction, Candidate B runtime compatibility, Layer 3 material authority compatibility, retained artifact handling, operator-visible provenance, redaction posture, regression disposition, and fail-closed stale/missing authority behavior before any selector mutation can be selected.

## Coherence Check

- Does this change Candidate B's current default scope? Recommended answer: no. Candidate B remains the default only for eligible/effective PDFs.
- Does this admit non-PDF corpus processing by Candidate B? Recommended answer: no. Office, image/OCR, ZIP-member, structured file, SEC EDGAR, web/database, and mixed-corpus expansion are audit subjects, not admitted runtime behavior.
- Does this weaken baseline or Candidate A? Recommended answer: no. Baseline remains rollback and non-PDF default; Candidate A remains its explicit PageEvidence visual-lane variant.
- What comes next? Recommended answer: implement a read-only broader eligible-corpus scope readiness audit that can fail closed and select only a later separately frozen default-scope runtime if evidence supports it.
