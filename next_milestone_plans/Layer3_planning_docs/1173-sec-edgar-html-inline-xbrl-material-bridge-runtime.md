# SEC EDGAR HTML Inline XBRL Material Bridge Runtime

```yaml
milestone: sec_edgar_html_inline_xbrl_material_bridge_runtime_v1
source_bridge_selection: next_milestone_plans/Layer3_planning_docs/1172-sec-edgar-html-inline-xbrl-material-bridge-selection.md
current_main_entry: c8b42bb9c67052cfabc54e6381be898d5532fb93
entry_decision: runtime_implementation
runtime_status: implemented
rendered_status: not_implemented
implemented_service: backend/app/services/layer3_sec_edgar_html_inline_xbrl_material_bridge.py
implemented_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/material-authority/bridge
implemented_status_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/material-authority/bridge/status/{sec_edgar_html_inline_xbrl_material_bridge_receipt_id}
implemented_bridge_mode: sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority_v1
implemented_operator_decision: bridge_sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority
implemented_source_authority: sec_edgar_html_inline_xbrl_parser_receipt_plus_connector_receipt_plus_live_source_artifact_receipt
implemented_material_source_class: dataset_version
implemented_typed_content_contract_id: sec_edgar_html_inline_xbrl_material_units_v1
implemented_material_payload: bounded_primary_document_narrative_segments_and_html_table_candidate_units_from_retained_complete_submission_text
implemented_bridge_output: materialized_dataset_version_material_preview_request_basis_gate_b_authority_binding_and_redacted_status_projection
implemented_receipt_model: deterministic_material_bridge_receipt_with_parser_receipt_hash_materialization_hash_material_preview_hash_and_gate_b_manifest_binding
implemented_material_preview_compatibility: existing_layer3_dataset_version_material_preview_without_source_class_widening
implemented_gate_b_compatibility: existing_gate_b_material_preview_hash_and_decision_basis_validation
direct_unbridged_html_inline_xbrl_parser_receipt_material_authority_admitted: false
live_sec_network_fetch_performed_by_bridge: false
submissions_lookup_runtime_performed_by_bridge: false
arbitrary_url_or_upload_parse_admitted: false
xml_xbrl_fact_authority_created: false
financial_statement_semantics_enabled: false
candidate_b_general_sec_parser_admitted: false
generic_connector_dispatch_enabled: false
provider_object_write_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_sec_url_rendered: false
raw_local_path_rendered: false
artifact_bytes_rendered: false
focused_py_compile: python -m py_compile ./backend/app/services/layer3_sec_edgar_html_inline_xbrl_parser.py ./backend/app/services/layer3_sec_edgar_html_inline_xbrl_material_bridge.py ./backend/app/services/layer3_aps_source_family.py ./backend/app/api/layer3.py ./backend/tests/test_layer3_api.py PASS
focused_api_pytest: pytest ./backend/tests/test_layer3_api.py -k "html_inline_xbrl_material_bridge or html_inline_xbrl_source_family or sec_edgar_real_filing_connector" PASS
next_exact_posture: sec_edgar_html_inline_xbrl_downstream_layer3_proof_selection_v1
```

This runtime bridges a ready SEC EDGAR HTML/iXBRL parser receipt into existing Layer 3 `dataset_version` material authority. The server revalidates the parser receipt, connector receipt, retained live source artifact, source artifact hash, reparsed document inventory, content-order hash, table-candidate hash, and inline-XBRL marker inventory before materializing bounded narrative/table units.

The bridge writes a server-owned DatasetVersion CSV and provenance row for material preview compatibility, returns only redacted material-candidate/Gate B authority, and records an append-only bridge receipt. It does not fetch SEC content, run a submissions lookup, admit raw URLs/uploads, create XBRL fact authority, claim financial-statement semantics, dispatch connectors, write provider objects, activate RAG/model behavior, activate full mockups, or trust frontend/browser durable authority.

## Grill Check

- Why `dataset_version` instead of a new source class? Recommended answer: current Layer 3 material preview admits `dataset_version` and `aps_content_document`; the selected bridge required existing `dataset_version` compatibility without source-class widening.
- Does this make a raw parser receipt sufficient material authority? Recommended answer: no. The bridge requires parser receipt hash, connector receipt hash, retained live source-artifact hash, source artifact hash, materialization hash, material-preview hash, and Gate B manifest binding.
- Are HTML/iXBRL markers converted into XBRL facts? Recommended answer: no. Inline XBRL markers remain evidence for a later separately frozen fact-authority slice.
- What comes next? Recommended answer: select `sec_edgar_html_inline_xbrl_downstream_layer3_proof_selection_v1` before proving the bridged material through downstream retrieval/context, analysis, package/review, handoff/export, delivery/status, and operator inspection.
