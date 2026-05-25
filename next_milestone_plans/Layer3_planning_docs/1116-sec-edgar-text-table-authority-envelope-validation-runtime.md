# SEC EDGAR Text Table Authority Envelope Validation Runtime

```yaml
milestone: sec_edgar_text_table_authority_envelope_validation_runtime_v1
source_authority_envelope_selection: next_milestone_plans/Layer3_planning_docs/1115-sec-edgar-text-table-authority-envelope-selection.md
current_main_entry: aceceded3de9d4e4e8d45bc717750b6a459379ed
entry_decision: runtime_implementation
runtime_status: implemented
rendered_status: not_implemented
implemented_service: backend/app/services/layer3_sec_edgar_authority_envelope.py
implemented_endpoint: /api/v1/layer3/source/sec-edgar/text-table/authority-envelope/validate
implemented_request_model: Layer3SecEdgarTextTableAuthorityEnvelopeRequest
implemented_response_model: Layer3SecEdgarTextTableAuthorityEnvelopeResponse
implemented_schema_id: layer3.sec_edgar_text_table_authority_envelope_validation.v1
implemented_mode: sec_edgar_text_table_authority_envelope_validation_runtime_v1
implemented_ready_state: sec_edgar_text_table_authority_envelope_ready
implemented_blocked_state: sec_edgar_text_table_authority_envelope_blocked
implemented_source_family: sec_edgar_text_table
implemented_parser_family: sec_edgar_filing
implemented_typed_content_contract_id: aps_sec_edgar_filing_units_v1
implemented_authority_envelope_shape: mixed_narrative_table
implemented_runtime_scope: validate_and_project_existing_materialized_dataset_version_sec_edgar_text_table_envelope_only
implemented_materialization_receipt_model: deterministic_validation_projection_no_new_write
implemented_authority_hash_version: sec_edgar_text_table_authority_envelope_hash_v1
implemented_redacted_ref_prefix: sec-edgar-text-table-authority-envelope
required_input_fields: dataset_version_id,rollback_confirmed,operator_confirmed
optional_stale_authority_fields: expected_authority_envelope_hash,expected_parser_family,expected_source_family,expected_typed_content_contract_id
required_fail_closed_conditions: missing_dataset_version,missing_materialization,not_ready_dataset_version,parser_family_mismatch,source_family_mismatch,typed_content_contract_mismatch,stale_authority_envelope_hash,raw_url_or_path_authority,missing_rollback_confirmation,missing_operator_confirmation,forbidden_input_authority
redacted_source_artifact_key_exposed: false
redacted_raw_storage_ref_exposed: false
redacted_diagnostics_ref_exposed: false
layer3_material_bridge_admitted_now: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
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
focused_py_compile: python -m py_compile ./backend/app/services/layer3_sec_edgar_authority_envelope.py ./backend/app/api/layer3.py ./tools/l3-progress-check.py PASS
focused_service_pytest: python -m pytest ./backend/tests/test_layer3_sec_edgar_authority_envelope.py -q PASS
focused_api_pytest: python -m pytest ./backend/tests/test_layer3_api.py -q -k "sec_edgar_text_table_authority_envelope or lists_aps_derived_dataset_version_candidates" PASS
next_exact_posture: sec_edgar_text_table_layer3_material_authority_bridge_selection_v1
```

The runtime validates and projects a SEC EDGAR text-table authority envelope over existing materialized DatasetVersion authority. It accepts only a dataset version id, optional expected authority bindings, rollback confirmation, and operator confirmation. The server validates the stored DatasetVersion, DatasetSourceProvenance, parser family, source family, typed-content contract, deterministic dataset/materialization hashes, stale expected hash behavior, and redacted provenance before returning a ready envelope.

This is not a Layer 3 material bridge yet. It does not fetch SEC data, add parser support, accept raw filing URLs, expose raw storage refs, expand source ingestion, write provider objects, dispatch connectors, run RAG/model behavior, activate full mockups, or create frontend durable authority. The next selected slice should freeze the exact material-authority bridge from ready SEC EDGAR text-table envelopes into Layer 3 material preview and Gate B.

## Coherence Check

- Does this runtime write a durable artifact or seed data? Recommended answer: no. It is validation/projection only and computes deterministic hashes without writing new records or files.
- What proves it is server-authoritative? Recommended answer: it reads DatasetVersion and DatasetSourceProvenance from the database, maps source family through the repo-owned APS source-family metadata, computes server-side hashes, and rejects stale or mismatched caller authority.
- What remains blocked? Recommended answer: SEC network fetch, parser expansion, XML/HTML/inline XBRL reinterpretation, raw SEC URL authority, broad source expansion, runtime DB/storage expansion, provider writes, connector dispatch, RAG/model runtime, full mockup activation, and frontend/browser durable authority.
- What comes next? Recommended answer: select `sec_edgar_text_table_layer3_material_authority_bridge_selection_v1` before implementing the bridge into Layer 3 material preview and Gate B.
