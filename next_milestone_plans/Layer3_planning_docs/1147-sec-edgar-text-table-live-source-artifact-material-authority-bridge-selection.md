# SEC EDGAR Text Table Live Source Artifact Material Authority Bridge Selection

```yaml
milestone: sec_edgar_text_table_live_source_artifact_material_authority_bridge_selection_v1
source_current_main_sync: next_milestone_plans/Layer3_planning_docs/1146-sec-edgar-text-table-live-source-artifact-acquisition-rendered-status-review-remediation-current-main-sync.md
current_main_entry: f8781fa4379dd1687e688d544365b737e4e8d3fa
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: sec_edgar_text_table_live_source_artifact_material_authority_bridge_runtime_v1
selected_bridge_mode: sec_edgar_text_table_live_source_artifact_to_layer3_material_authority_v1
selected_source_family: sec_edgar_text_table
selected_parser_family: sec_edgar_filing
selected_typed_content_contract_id: aps_sec_edgar_filing_units_v1
selected_existing_parser_contract_id: aps_sec_edgar_filing_parser_v1
selected_live_acquisition_mode: sec_edgar_text_table_live_source_artifact_acquisition_v1
selected_live_source_artifact_family: complete_submission_text_filing_artifact
selected_source_acquisition_mode: sec_edgar_text_table_source_acquisition_authority_v1
selected_existing_material_bridge_mode: sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1
selected_bridge_scope: bind_verified_live_source_artifact_receipt_to_existing_source_acquisition_authority_and_ready_material_authority_envelope
selected_material_source_class: dataset_version
selected_material_preview_request_schema: layer3.material_preview_request.v1
selected_gate_b_decision_request_schema: layer3.gate_b_decision_request.v1
selected_output_authority: deterministic_live_source_artifact_material_authority_bridge_receipt_and_redacted_status_projection
selected_bridge_receipt_prefix: sec-edgar-text-table-live-source-artifact-l3-material-bridge
selected_status_states: not_recorded,ready,blocked
required_live_artifact_authority: live_source_artifact_receipt_id,live_source_artifact_receipt_hash,source_artifact_receipt_id,source_artifact_receipt_hash,source_artifact_ref_hash,content_sha256,content_length,accession_or_submission_id_hash,cik_or_filer_ref_hash,form_type,filing_date
required_source_acquisition_authority: source_acquisition_receipt_id,source_acquisition_receipt_hash,source_artifact_receipt_hash,materialization_receipt_hash,dataset_version_hash,authority_envelope_hash
required_material_authority: dataset_version_id,materialization_receipt_hash,authority_envelope_hash,material_preview_hash,gate_b_decision_manifest_id
required_hash_bindings: live_source_artifact_receipt_hash,source_artifact_receipt_hash,source_artifact_ref_hash,content_sha256,source_acquisition_receipt_hash,dataset_version_hash,materialization_receipt_hash,authority_envelope_hash,material_preview_hash,gate_b_decision_manifest_id
required_provenance_binding: redacted_live_source_artifact_ref,redacted_source_acquisition_receipt_ref,redacted_authority_envelope_ref,source_family,parser_family,typed_content_contract_id,dataset_version_id,form_type,filing_date,accession_or_submission_id_hash,cik_or_filer_ref_hash
required_compatibility_target: existing_sec_edgar_text_table_source_acquisition_authority_runtime_and_material_authority_bridge_runtime
required_downstream_target: layer3_material_preview_gate_b_downstream_proof_status_repeatability_package_delivery_operator_inspection
live_source_artifact_receipt_authority_admitted_for_next_runtime: true
existing_source_acquisition_authority_reuse_required: true
existing_material_authority_bridge_reuse_required: true
direct_live_artifact_to_material_without_source_acquisition_admitted: false
direct_raw_artifact_parse_or_materialization_admitted: false
dataset_version_creation_admitted: false
gate_b_mutation_admitted_in_bridge: false
live_sec_network_fetch_admitted_for_bridge: false
sec_network_cache_or_rate_behavior_admitted_for_bridge: false
raw_sec_filing_url_as_authority_admitted_for_bridge: false
xml_html_inline_xbrl_parser_admitted_for_bridge: false
broad_source_expansion_admitted: false
source_family_expansion_scope: sec_edgar_text_table_only
runtime_db_or_storage_expansion_admitted: false
new_runtime_storage_root_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
browser_supplied_local_path_admitted: false
browser_supplied_raw_url_admitted: false
browser_supplied_artifact_bytes_admitted: false
browser_supplied_command_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_token_exposed: false
missing_live_source_artifact_receipt_must_reject: true
stale_live_source_artifact_receipt_hash_must_reject: true
retained_artifact_content_hash_mismatch_must_reject: true
missing_source_acquisition_receipt_must_reject: true
source_acquisition_receipt_hash_mismatch_must_reject: true
source_artifact_receipt_hash_mismatch_must_reject: true
missing_materialization_linkage_must_reject: true
parser_contract_mismatch_must_reject: true
typed_content_contract_mismatch_must_reject: true
dataset_version_hash_mismatch_must_reject: true
authority_envelope_hash_mismatch_must_reject: true
material_preview_hash_mismatch_must_reject: true
gate_b_decision_basis_mismatch_must_reject: true
operator_confirmation_required: true
rollback_to_authority_envelope_bridge_preserved: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
runtime_implementation_in_this_freeze: false
rendered_runtime_in_this_freeze: false
next_exact_posture: sec_edgar_text_table_live_source_artifact_material_authority_bridge_runtime_v1
```

This freeze selects the next SEC EDGAR text/table slice: a bridge from a verified live source-artifact receipt to Layer 3 material authority. The selected runtime should not parse the retained filing artifact, create a DatasetVersion, mutate Gate B, or fetch SEC content. It should verify the live source-artifact receipt and retained content hash, require the existing source-acquisition authority receipt, require a ready materialized DatasetVersion authority envelope, and then reuse the existing SEC EDGAR material-authority bridge contract.

The retained complete-submission text artifact remains source evidence, parser input evidence, provenance/audit evidence, and operator inspection evidence. It is not itself a Layer 3 material payload until an existing materialized DatasetVersion and authority envelope bind it through source-acquisition authority and the material-authority bridge.

## Admitted Bridge Shape

The future runtime may accept:

- `client_request_id`;
- `live_source_artifact_receipt_id`;
- `live_source_artifact_receipt_hash`;
- `source_acquisition_receipt_id`;
- `source_acquisition_receipt_hash`;
- `dataset_version_id`;
- `authority_envelope_hash`;
- optional expected `materialization_receipt_hash`;
- optional expected `material_preview_hash`;
- optional expected `gate_b_decision_manifest_id`;
- `operator_confirmed`;
- `rollback_confirmed`.

The future runtime may produce:

- a deterministic bridge receipt id;
- a redacted live source-artifact provenance binding;
- a redacted source-acquisition receipt binding;
- an authority-envelope/material-bridge compatibility binding;
- material-preview and Gate B decision-basis references from the existing material bridge;
- a ready or blocked status projection.

## Required Runtime Behavior

Implementation must fail closed unless:

- the live source-artifact receipt exists, validates its receipt hash, and the retained artifact bytes still match `content_sha256`;
- the nested source-artifact receipt hash matches the source-acquisition authority receipt;
- the source-acquisition authority receipt exists and still binds the same source artifact, materialization receipt, DatasetVersion hash, and authority-envelope hash;
- the existing authority envelope validates as ready for the same DatasetVersion, parser family, source family, and typed-content contract;
- the existing material-authority bridge can produce or verify material-preview/Gate B compatibility without raw artifact exposure;
- operator and rollback confirmations are present;
- rendered/operator output is limited to redacted refs, hashes, status, and bounded failure codes.

## Material Scope

The admitted material payload remains the parsed narrative/table units from the existing `aps_sec_edgar_filing_units_v1` materialized DatasetVersion. The live retained complete-submission text artifact is an evidence and inspection artifact for this slice, not a direct material-analysis payload. A future parser/materialization slice would be required before raw retained filing content could create new material authority.

## Stop Conditions

Implementation must stop if:

- only a live source-artifact receipt exists and no source-acquisition authority or materialized DatasetVersion authority exists;
- retained artifact bytes are missing or fail the content hash check;
- the source-acquisition receipt, authority envelope, material-preview hash, or Gate B decision basis is stale or mismatched;
- the runtime would need to parse raw SEC content, create DatasetVersion rows, mutate Gate B, fetch from SEC, widen source families, expose raw paths/URLs/artifact bytes, add provider writes, dispatch connectors, add RAG/model runtime, activate full mockups, or rely on frontend/browser durable authority.

## Coherence Check

- Does this freeze make a retained live source artifact a Layer 3 material by itself? Recommended answer: no. It requires source-acquisition authority plus a ready materialized DatasetVersion authority envelope.
- Does the next runtime fetch SEC content or parse the retained filing artifact? Recommended answer: no. Acquisition and parsing/materialization remain separate authority slices.
- Why require the existing source-acquisition receipt? Recommended answer: it prevents a direct raw artifact to material shortcut and preserves the already governed source-artifact to materialization linkage.
- What is the next runtime? Recommended answer: `sec_edgar_text_table_live_source_artifact_material_authority_bridge_runtime_v1`, using bridge mode `sec_edgar_text_table_live_source_artifact_to_layer3_material_authority_v1`.
- What remains out of scope? Recommended answer: SEC fetch, parser/materialization expansion, XML/HTML/inline XBRL, DatasetVersion creation, Gate B mutation, raw URL/path/artifact exposure, provider writes, connector dispatch, RAG/model runtime, full mockup activation, and frontend/browser durable authority.
