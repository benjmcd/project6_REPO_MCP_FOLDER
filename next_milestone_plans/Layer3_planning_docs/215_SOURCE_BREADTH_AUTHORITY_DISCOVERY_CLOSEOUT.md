# Source Breadth Authority Discovery Closeout

Status: current-main planning/control closeout for `source_breadth_authority_discovery_closeout`.

This document is a post-PR #770 authority-discovery closeout over docs `193_SOURCE_BREADTH_ENTRY_FREEZE.md`, `194_SOURCE_BREADTH_ENTRY_CONTRACT.md`, `203_POST_756_GOVERNANCE_CLOSEOUT.md`, `213_PROVIDER_PUBLIC_URL_AUTHORITY_DISCOVERY_CLOSEOUT.md`, and `214_CONNECTOR_DESTINATION_AUTHORITY_DISCOVERY_CLOSEOUT.md`. It does not replace those docs and does not implement source-class expansion, a source adapter registry, local upload, local-directory ingestion, broad file upload, web connector retrieval, RAG/vector retrieval, unbounded runtime DB source reads, arbitrary local path input, route, DTO, model, migration, service behavior, test behavior, rendered UI controls, package mutation, provider/public URLs, connector/destination dispatch, full mockup activation, hidden LLM planning, frontend-only durable authority, or auth/security behavior.

## Decision

```yaml
selected_planning_mode: source_breadth_authority_discovery_closeout
entry_decision: no_runtime_now
selected_mode: null
runtime_status: not_implemented
live_supported_source_boundary_status: supported_source_classes_only
live_raw_mixed_seed_status: raw_mixed_corpus_bridge_seed_only
live_raw_mixed_materialization_status: raw_mixed_existing_source_materialization_entry
authority_discovery_result: insufficient_authority_for_source_breadth_runtime
implementation_entry_required_before_runtime: true
next_product_boundary_required: true
```

No new source family or source ingestion runtime is admitted by this pass.

The currently admitted source classes remain exactly:

- `dataset_version`;
- `aps_content_document`.

The already-live raw mixed seed-only and current-class materialization boundaries remain available only for those admitted classes and server-owned manifest/hash authority. They are not generalized into broad ingestion, local upload, directory ingestion, web retrieval, source adapter registry behavior, or RAG/vector retrieval.

Docs `193` and `194` already freeze the source-breadth entry posture as deferred. This pass records the current-main discovery result after connector/destination authority discovery was closed out: the repo still has no concrete new source-family authority, selected source family, selected adapter/input mode, operator input/storage security model, network retrieval policy, downstream source semantics, provenance contract, rendered control proof plan, or auth/security posture sufficient to select a runtime mode.

The only future candidate modes remain:

- `single_named_source_family_expansion`;
- `single_named_server_owned_adapter`;
- `source_breadth_read_only_inventory`;
- `raw_mixed_current_classes_only_extension`.

Do not choose a runtime mode unless a later implementation-entry freeze proves why current admitted source classes and raw mixed current-class materialization are insufficient for a named source use case.

## Current-Main Authority Evidence

```yaml
authority_evidence:
  live_main_anchor:
    status: verified
    evidence:
      - project6-origin/main at 23c8bd20354bae265806fa884147bf5a7f8568ac during this pass
      - python .\tools\l3-progress-check.py
      - git diff --check
  supported_source_classes_only:
    status: verified
    evidence:
      - backend/app/services/layer3_source_boundary.py
      - backend/tests/test_layer3_source_boundary.py
      - tools/l3-progress-check.py
  raw_mixed_corpus_bridge_seed_only:
    status: verified
    evidence:
      - backend/app/services/layer3_raw_mixed_bridge.py
      - backend/tests/test_layer3_raw_mixed_bridge.py
  raw_mixed_existing_source_materialization_entry:
    status: verified
    evidence:
      - backend/app/services/layer3_raw_mixed_materialization.py
      - backend/tests/test_layer3_raw_mixed_materialization.py
  new_source_family_authority:
    status: unverified
    evidence: []
  source_adapter_contract:
    status: unverified
    evidence: []
  operator_input_and_storage_security_model:
    status: unverified
    evidence: []
  network_retrieval_policy:
    status: unverified
    evidence: []
  downstream_source_semantics:
    status: unverified
    evidence: []
  rendered_source_control_theme_proof_plan:
    status: unverified
    evidence: []
```

The repo-confirmed source-breadth references in current source and tests prove the admitted source-class boundary and fail-closed posture for unsupported source classes. They are not authority for new source ingestion.

## Source/Test Discovery Result

Current source/test inspection confirms this posture:

- `backend/app/services/layer3_source_boundary.py` keeps `SUPPORTED_SOURCE_CLASSES` to `dataset_version` and `aps_content_document`, lists `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db` as unsupported, and exposes disabled flags for upload, directory, broad file, web connector, RAG/vector, and unbounded runtime DB behavior.
- `backend/tests/test_layer3_source_boundary.py` proves default supported classes, unsupported source-class rejection, candidate-id parsing limited to admitted classes, and fail-closed deferred source expansion contract flags.
- `backend/app/services/layer3_raw_mixed_bridge.py` accepts only admitted raw mixed source classes, uses server-owned manifest/hash authority, blocks local upload, directory, broad file, web connector, provider/public URL, RAG/vector, package, destination, hidden LLM, mockup, and auth override fields, and does not become a broad ingestion bridge.
- `backend/tests/test_layer3_raw_mixed_bridge.py`, `backend/tests/test_layer3_source_boundary.py`, `backend/tests/test_layer3_preflight_request_contract.py`, `backend/tests/test_layer3_bounded_e2e.py`, and related focused tests assert broad source expansion remains forbidden, disabled, absent from side effects, or deferred.

This evidence proves non-admission and fail-closed source-boundary behavior. It does not prove readiness for a new source family, adapter, rendered source control, local upload, directory ingestion, web retrieval, or RAG/vector behavior.

## Authority Discovery Ledger

```yaml
authority_discovery_ledger:
  new_source_family_authority:
    result: not_found
    consequence: runtime_blocked
  selected_source_family:
    result: null
    consequence: runtime_blocked
  selected_adapter_or_input_mode:
    result: null
    consequence: runtime_blocked
  source_adapter_contract:
    result: not_defined
    consequence: runtime_blocked
  operator_input_and_storage_security_model:
    result: not_defined
    consequence: runtime_blocked
  network_retrieval_policy:
    result: not_defined
    consequence: runtime_blocked
  provenance_model:
    result: not_defined
    consequence: runtime_blocked
  downstream_source_semantics:
    result: not_defined
    consequence: runtime_blocked
  rendered_source_control_theme_proof_plan:
    result: not_defined
    consequence: runtime_blocked
```

## Runtime Non-Admission

```yaml
runtime_admission:
  new_source_family_runtime: false
  source_adapter_registry: false
  local_upload: false
  local_directory_ingestion: false
  broad_file_upload: false
  web_connector_retrieval: false
  rag_vector_retrieval: false
  vector_index_creation: false
  unbounded_runtime_db_source_read: false
  arbitrary_local_path_input: false
  raw_mixed_seed_behavior_change: false
  raw_mixed_materialization_behavior_change: false
  layer3_flow_start_inside_source_setup: false
  rendered_source_control_change: false
  package_mutation_reconstruction: false
  provider_public_url_runtime: false
  connector_destination_dispatch_runtime: false
  hidden_llm_planning: false
  full_mockup_activation: false
  auth_security_behavior_change: false
  test_behavior_change: false
```

## Theme And UI Posture

This pass adds no rendered UI controls. If a later freeze admits rendered source-breadth controls, it must preserve the current theme split:

- `light` remains the inspection/status/preview/review theme surface;
- `dark` remains the execution/package-construction theme surface;
- `workbench` remains the source selection, material preview, Gate B/Gate C, package submit, handoff/export, APS handoff, external export/download, signed-reference, and downstream operation-dock theme surface.

A later rendered implementation must prove headed and headless Chromium consistency before merge and must not treat browser state, local files, local paths, or mockups as source authority.

## Negative Invariants

- no new source family runtime;
- no source adapter registry;
- no local upload;
- no local-directory ingestion;
- no broad file upload;
- no arbitrary local path input;
- no web connector retrieval;
- no RAG/vector retrieval;
- no vector index creation;
- no unbounded runtime DB source read;
- no source-class expansion beyond dataset_version and aps_content_document;
- no raw mixed seed behavior change;
- no raw mixed materialization behavior change;
- no Layer 3 flow start inside source seeding or materialization;
- no package mutation or reconstruction;
- no provider/public URL runtime;
- no connector or destination dispatch;
- no generic downstream dispatch;
- no broad qualitative execution;
- no hybrid execution;
- no full mockup activation;
- no hidden LLM planning;
- no frontend-only durable state;
- no auth/security behavior change;
- no browser-only source authority;
- no source credentials, local paths, provider URL, connector target, destination target, or token leakage;
- no cross-mode privilege escalation;
- no CI workflow change;
- no route, DTO, model, migration, production service behavior, test behavior, or rendered UI control.

## Next Boundary

Source-breadth runtime should not be implemented next unless a concrete named source use case emerges and a later implementation-entry freeze proves the missing authority listed above.

The next implementation-eligible boundary should move to one of:

1. `package_mutation_rendered_authority_discovery_freeze_or_entry_freeze_update`, if operator package revision is the blocker;
2. `qual_hybrid_rag_authority_discovery_freeze_or_entry_freeze_update`, if broader analysis execution is the blocker;
3. `source_breadth_runtime_entry_freeze_update` only if a named source-family use case requires source expansion and the required authority is proven.

## Stop Condition

Stop before implementation if any proposed change needs a new source family, adapter registry, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, unbounded runtime DB reads, arbitrary local path input, rendered source controls, source credentials, network retrieval policy, provenance semantics, storage security model, downstream materialization semantics, headed/headless proof, theme behavior proof, or auth/security posture that this closeout has not verified.
