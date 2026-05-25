# SEC EDGAR Text Table Layer 3 Material Authority Bridge Selection

```yaml
milestone: sec_edgar_text_table_layer3_material_authority_bridge_selection_v1
source_authority_envelope_runtime: next_milestone_plans/Layer3_planning_docs/1116-sec-edgar-text-table-authority-envelope-validation-runtime.md
current_main_entry: a593cc9dc6612b232d871957e080901cc90ea691
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
selected_next_runtime_target: sec_edgar_text_table_layer3_material_authority_bridge_runtime_v1
selected_bridge_mode: sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1
selected_source_family: sec_edgar_text_table
selected_parser_family: sec_edgar_filing
selected_typed_content_contract_id: aps_sec_edgar_filing_units_v1
selected_authority_envelope_schema_id: layer3.sec_edgar_text_table_authority_envelope_validation.v1
selected_authority_envelope_mode: sec_edgar_text_table_authority_envelope_validation_runtime_v1
required_ready_envelope_state: sec_edgar_text_table_authority_envelope_ready
required_blocked_envelope_state: sec_edgar_text_table_authority_envelope_blocked
selected_material_source_class: dataset_version
selected_material_preview_source_candidate_prefix: src-dataset_version-
selected_material_preview_request_schema: layer3.material_preview_request.v1
selected_gate_b_decision_request_schema: layer3.gate_b_decision_request.v1
selected_material_payload: text_filing_narrative_units_and_table_units_from_existing_aps_sec_edgar_filing_units_v1_materialization
selected_bridge_output: material_preview_request_basis_and_gate_b_authority_binding
selected_receipt_model: deterministic_bridge_projection_with_ready_envelope_hash_binding
required_hash_bindings: dataset_version_hash,materialization_receipt_hash,authority_envelope_hash,material_preview_hash,gate_b_decision_manifest_id
required_provenance_binding: redacted_authority_envelope_ref,source_family,parser_family,typed_content_contract_id,dataset_version_id,materialization_receipt_id,form_type,accession_or_submission_id,filer_or_cik,filing_date
required_fail_closed_conditions: missing_ready_envelope,blocked_envelope,stale_authority_envelope_hash,dataset_version_mismatch,parser_family_mismatch,source_family_mismatch,typed_content_contract_mismatch,material_preview_hash_mismatch,gate_b_decision_basis_mismatch,raw_path_or_url_authority,missing_operator_confirmation,missing_rollback_confirmation
required_material_preview_compatibility: existing_layer3_dataset_version_material_preview_without_source_class_widening
required_gate_b_compatibility: existing_gate_b_material_preview_hash_and_decision_basis_validation
direct_unbridged_sec_edgar_dataset_version_material_authority_admitted: false
bridge_runtime_admitted_after_current_main_sync: true
material_preview_runtime_implementation_in_this_freeze: false
gate_b_runtime_implementation_in_this_freeze: false
sec_edgar_network_fetch_admitted: false
sec_edgar_parser_expansion_admitted: false
xml_html_inline_xbrl_admitted: false
raw_sec_filing_url_authority_admitted: false
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
artifact_bytes_exposed: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
next_exact_posture: sec_edgar_text_table_layer3_material_authority_bridge_runtime_v1
```

This freeze admits the next implementation slice only: a server-owned bridge from a ready SEC EDGAR text-table authority envelope into existing Layer 3 material preview and Gate B authority. It introduces no runtime code, route, DTO, model, migration, rendered UI, source fetch, parser, provider, connector, auth/security, RAG/vector/model, browser-storage, frontend-only durable authority, or full mockup behavior change.

The bridge must not treat a raw `dataset_version_id` alone as sufficient SEC EDGAR material authority. The future runtime must first validate or consume a ready `sec_edgar_text_table_authority_envelope_ready` projection, bind the `authority_envelope_hash` to the selected dataset version and materialization receipt, and then produce a material-preview/Gate B authority binding that remains compatible with the existing `dataset_version` material-preview and Gate B decision-hash contracts.

## Admitted Bridge Shape

The future bridge may accept:

- `client_request_id`;
- `dataset_version_id`;
- `authority_envelope_hash`;
- optional `authority_envelope_ref`;
- optional expected `materialization_receipt_hash`;
- optional expected `material_preview_hash`;
- `operator_confirmed`;
- `rollback_confirmed`.

The future bridge may produce:

- a deterministic bridge receipt id;
- redacted SEC EDGAR authority-envelope provenance;
- a material-preview request basis using `source_candidate_ids` with the existing `src-dataset_version-` shape and the selected `dataset_version_ids`;
- a `material_preview_hash` binding after preview;
- a Gate B decision-basis binding after admission;
- status projection of ready or blocked bridge state.

## Required Runtime Behavior

Implementation must fail closed unless:

- the referenced envelope validates through `layer3.sec_edgar_text_table_authority_envelope_validation.v1`;
- the envelope state is `sec_edgar_text_table_authority_envelope_ready`;
- the envelope hash matches the caller's expected hash;
- the envelope dataset version, parser family, source family, typed-content contract, and materialization receipt still match current database authority;
- the material-preview candidate basis is generated through the existing Layer 3 `dataset_version` source class without widening supported source classes;
- the Gate B decision basis binds to the returned `material_preview_hash`;
- operator and rollback confirmations are present;
- rendered/operator surfaces expose only redacted refs and deterministic hashes.

## Material Scope

Admitted material payload is limited to text filing narrative units and table units from the existing `aps_sec_edgar_filing_units_v1` materialized dataset version. The bridge does not admit raw SEC URLs, source fetch, XML/HTML/inline XBRL parsing, arbitrary filing content, local directories, source PDFs/images as text payload, broad runtime storage, or new source families.

Retained SEC EDGAR source provenance and product/inspection metadata may remain governed evidence, but raw local paths, raw URLs, raw storage refs, provider keys, local roots, credentials, and artifact bytes must not appear in rendered or operator-facing bridge output.

## Compatibility Rule

The bridge must use the current Layer 3 material-preview and Gate B contracts as downstream authority:

- `layer3.material_preview_request.v1`;
- `dataset_version_ids`;
- `src-dataset_version-` source candidate ids;
- `layer3.material_preview_basis.v1`;
- `material_preview_hash`;
- `layer3.gate_b_decision_request.v1`;
- Gate B decision manifest idempotency.

It must not bypass material-preview hash checks, Gate B decision-basis validation, source-family metadata checks, or stale authority rejection. If the existing material-preview path would expose raw SEC provenance for this source family, the runtime must block or redact before declaring the bridge ready.

## Stop Conditions

Implementation must stop if:

- the authority-envelope runtime returns blocked or cannot validate current database authority;
- only historical reports exist and the live DatasetVersion/provenance rows are absent;
- the material-preview request would rely on unbridged raw dataset ids without envelope hash binding;
- material preview or Gate B would expose raw paths, raw URLs, raw storage refs, or artifact bytes;
- parser/source-family/contract metadata has drifted;
- source-class widening is required;
- network fetch, parser expansion, XML/HTML/inline XBRL reinterpretation, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, browser storage, or frontend durable authority would be required.

## Coherence Check

- Does this implement the bridge? Recommended answer: no. It freezes the exact bridge contract for the next runtime slice.
- Why not use `dataset_version_ids` directly? Recommended answer: direct dataset ids are existing material-preview selectors, but SEC EDGAR governed authority requires the ready envelope hash, parser/source-family/contract checks, stale-authority rejection, and redacted provenance binding.
- What is the next runtime? Recommended answer: `sec_edgar_text_table_layer3_material_authority_bridge_runtime_v1`, using bridge mode `sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1`.
- What remains out of scope? Recommended answer: SEC fetch, parser expansion, XML/HTML/inline XBRL, raw SEC URL authority, source expansion, runtime DB/storage expansion, provider writes, connector dispatch, RAG/model runtime, full mockup activation, and frontend/browser durable authority.
