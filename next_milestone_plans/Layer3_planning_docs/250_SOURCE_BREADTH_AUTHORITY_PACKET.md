# Source Breadth Authority Packet

Status: current-main planning/control authority packet for `source_breadth_reentry_authority_packet`.

This document follows `248_POST_PROVIDER_PRIVATE_ROADMAP_SELECTION_FREEZE.md` and `249_SOURCE_BREADTH_REENTRY_CONTRACT.md`. It answers the source-breadth reentry gates from current repo evidence. It does not implement source runtime, source adapter registry behavior, local upload, local-directory ingestion, broad file upload, web connector retrieval, RAG/vector retrieval, vector index creation, unbounded runtime DB source reads, route behavior, DTO behavior, model or migration behavior, production service behavior, executable test behavior, rendered UI controls, connector/destination dispatch, package mutation/reconstruction, broad qualitative/hybrid/RAG runtime, full mockup activation, auth/security behavior, hidden LLM planning, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: source_breadth_reentry_authority_packet
entry_decision: no_runtime_now
runtime_status: not_implemented
source_family_selected: false
selected_source_family: none_selected_runtime_blocked
adapter_input_mode_selected: false
operator_storage_security_model_selected: false
provenance_contract_selected: current_classes_only
rendered_source_control_selected: false
implementation_entry_allowed_next: false
no_runtime_reason: named_source_use_case_and_source_family_not_selected
```

The source-breadth reentry packet does not justify implementation. Current main remains bounded to already-admitted source classes and current-class raw-mixed seed/materialization behavior.

## Current Repo Authority

Current implementation authority is:

- `backend/app/services/layer3_source_boundary.py` keeps `SUPPORTED_SOURCE_CLASSES` to `dataset_version` and `aps_content_document`.
- `backend/app/services/layer3_source_boundary.py` marks `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db` unsupported.
- `backend/app/services/layer3_raw_mixed_bridge.py` admits only `raw_mixed_corpus_bridge_seed_only` over existing `dataset_version` and `aps_content_document` sources.
- `backend/app/services/layer3_raw_mixed_materialization.py` admits only `raw_mixed_existing_source_materialization_entry` for current classes through server-owned, hash-checked manifests.
- `backend/tests/test_layer3_source_boundary.py` proves the source-boundary contract remains fail-closed for deferred source classes and forbidden runtime fields.
- `backend/tests/test_layer3_raw_mixed_bridge.py` proves seed-only behavior, forbidden-field rejection, unsupported-class rejection, stale-manifest rejection, and no Layer 3 flow/file side effects.
- `backend/tests/test_layer3_raw_mixed_materialization.py` proves bounded materialization for current classes, no file writes, no Layer 3 flow start, idempotency, storage-root checks, forbidden request/manifest field rejection, unsupported-class rejection, and authority-conflict rollback.

This evidence proves current-source boundary strength. It does not prove readiness for a new source family.

## Authority Gate Results

```yaml
authority_packet:
  named_source_use_case:
    status: not_selected
    consequence: runtime_blocked
  selected_source_family:
    status: none_selected_runtime_blocked
    consequence: runtime_blocked
  adapter_input_mode:
    status: not_selected
    consequence: runtime_blocked
  source_of_truth:
    status: current_classes_only_server_owned_manifest_hash_authority
    consequence: sufficient_for_existing_raw_mixed_paths_only
  storage_security_model:
    status: current_storage_root_manifest_hash_check_only
    consequence: insufficient_for_local_upload_directory_web_or_rag
  network_retrieval_policy:
    status: not_selected
    consequence: web_connector_runtime_blocked
  provenance_contract:
    status: current_classes_only
    consequence: insufficient_for_new_source_family
  downstream_semantics:
    status: current_material_preview_preflight_path_only
    consequence: insufficient_for_broad_execution_or_rag
  rendered_control_plan:
    status: not_selected
    consequence: rendered_source_controls_blocked
  auth_security_posture:
    status: not_selected_for_new_source_behavior
    consequence: source_runtime_blocked
```

## Why This Outcome Is Correct

The previous roadmap-selection freeze chose source breadth as the next planning lane because it is foundational for later broad qualitative, hybrid/RAG, connector/destination, and package lifecycle work. That selection did not by itself make source runtime admissible.

The current authority packet confirms that the repo already has a bounded current-class source path, but it lacks the product and security authority required to widen the source surface. Implementing a new source family now would require guessing at least one of these unresolved decisions:

- which operator problem current sources cannot solve;
- which source family is the smallest correct next family;
- whether source bytes come from server-owned manifests, uploads, local directories, web retrieval, or another adapter;
- how storage, local path exposure, network retrieval, and provenance should work;
- whether auth/security must come first;
- how rendered controls should prove headed/headless/theme behavior if UI changes are required.

Guessing any of those would create fragility and tech debt because source admission is upstream of analysis, packaging, connector dispatch, external delivery, and security.

## Current Supported Path Preserved

The following remain admitted:

- `dataset_version`;
- `aps_content_document`;
- current-class raw-mixed seed-only bridge;
- current-class raw-mixed materialization from server-owned, hash-checked manifests;
- preview/preflight use of materialized current-class source ids.

These are not generalized into broad source expansion.

## Runtime Non-Admission

```yaml
runtime_admission:
  new_source_family_runtime: false
  source_adapter_registry: false
  local_upload: false
  local_directory_ingestion: false
  broad_file_upload: false
  arbitrary_local_path_input: false
  web_connector_retrieval: false
  rag_vector_retrieval: false
  vector_index_creation: false
  unbounded_runtime_db_source_read: false
  rendered_source_controls: false
  source_runtime_implementation_entry: false
```

## Next Allowed Moves

The next move should be one of:

- select a concrete source use case and source family, then write a source-breadth implementation-entry freeze;
- choose connector/destination instead if external delivery has become the actual product priority;
- choose auth/security first if the desired source family requires identity, permissions, credential, or nonlocal exposure decisions;
- stop at no-runtime if no concrete source use case exists.

## Negative Invariants

- no source runtime implementation;
- no new source family;
- no source adapter registry;
- no local upload;
- no local-directory ingestion;
- no broad file upload;
- no arbitrary local path input;
- no web connector retrieval;
- no RAG/vector retrieval;
- no vector index creation;
- no unbounded runtime DB source reads;
- no browser-local source authority;
- no rendered source controls;
- no route/API/DTO/model/migration/service behavior change;
- no executable test behavior change;
- no connector/destination dispatch;
- no package mutation/reconstruction;
- no provider/public URL runtime;
- no broad qualitative/hybrid/RAG runtime;
- no full mockup activation;
- no auth/security behavior change;
- no hidden LLM planning;
- no frontend-only durable authority.

## Stop Condition

Stop before implementation if a source-breadth task does not name one concrete source use case, one selected source family, one adapter/input mode, a source-of-truth and storage/security model, a provenance contract, downstream semantics, rendered-control obligations if any, and auth/security/leakage posture.
