# SEC EDGAR Text Table Source Acquisition Authority Runtime Current-Main Sync

```yaml
milestone: sec_edgar_text_table_source_acquisition_authority_runtime_current_main_sync_v1
source_runtime: next_milestone_plans/Layer3_planning_docs/1134-sec-edgar-text-table-source-acquisition-authority-runtime.md
current_main_entry: af95f4fd10231c9d690a575328e660e70f4a4bf3
merged_pr: 1838
entry_decision: current_main_sync
runtime_status: merged_on_current_main
rendered_status: not_implemented
implemented_endpoint: /api/v1/layer3/source/sec-edgar/text-table/source-acquisition/authority
implemented_action: record_sec_edgar_text_table_source_acquisition_authority
implemented_service: backend/app/services/layer3_sec_edgar_source_acquisition.py
implemented_api: backend/app/api/layer3.py
implemented_receipt_schema_id: layer3.sec_edgar_text_table_source_acquisition_authority.v1
implemented_source_artifact_receipt_schema_id: layer3.sec_edgar_text_table_source_artifact_receipt.v1
implemented_receipt_prefix: sec-edgar-text-table-source-acquisition
implemented_receipt_storage: existing_layer3_storage_root_append_only_receipt
implemented_status_states: not_recorded,available,blocked
implemented_material_preview_gate_b_compatibility: true
implemented_idempotent_replay: true
implemented_stale_source_artifact_hash_rejection: true
implemented_operator_confirmation_required: true
local_validation_py_compile: passed
local_validation_sec_edgar_api_tests: passed
local_validation_bootstrap_contract_test: passed
local_validation_l3_progress_check: passed
local_validation_l3_target_selection_validate_frozen: passed
local_validation_git_diff_check: passed
local_validation_git_diff_cached_check: passed
github_checks: passed
review_threads: none
open_prs_after_merge: none
live_sec_network_fetch_admitted: false
raw_sec_filing_url_as_authority_admitted: false
xml_html_inline_xbrl_parser_admitted: false
runtime_db_or_storage_expansion_admitted: false
new_runtime_storage_root_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
next_exact_posture: sec_edgar_text_table_source_acquisition_authority_rendered_status_selection_v1
```

Current main now contains the SEC EDGAR text/table source-acquisition authority runtime. The runtime is still intentionally API/server-authority only: it records a redacted append-only authority receipt over server-owned `DatasetSourceProvenance` plus a ready authority envelope, then leaves rendered/operator source-acquisition status controls for a separate selected slice.

## Coherence Check

- Did this sync add new runtime behavior? Recommended answer: no. It records the already merged runtime posture on current main.
- Did the runtime change SEC acquisition scope? Recommended answer: no. Live SEC fetch, raw SEC URL authority, cache/rate behavior, and parser expansion remain blocked.
- Does current main now have the source-acquisition API needed before downstream SEC EDGAR material use? Recommended answer: yes, bounded to existing materialized DatasetVersion authority and server-owned provenance.
- What comes next? Recommended answer: select the rendered/operator status or inspection slice for source-acquisition authority, then prove it only reflects server-owned receipt state without adding browser durable authority.
