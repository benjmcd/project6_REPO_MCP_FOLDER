# Source Breadth Named Use Case Packet

Status: current-main source-breadth named-use-case packet for `source_breadth_named_use_case_packet`.

## Decision YAML

```yaml
selected_planning_mode: source_breadth_named_use_case_packet
entry_decision: no_runtime_now_named_source_use_case_absent
base_branch: main
implementation_branch: codex/l3-source-use-case-packet
live_behavior_change: false
upstream_adjudication_doc: 260_POST_REENTRY_NAMED_USE_CASE_ADJUDICATION.md
named_source_use_case: null
source_family_selected: false
selected_source_family: none_selected_runtime_blocked
adapter_input_mode_selected: false
source_of_truth: current_classes_only_server_owned_manifest_hash_authority
current_supported_sources:
  - dataset_version
  - aps_content_document
current_supported_sources_sufficient_for_named_new_use_case: unproven
implementation_entry_allowed_next: false
next_required_boundary: user_or_product_named_source_use_case_before_runtime
source_breadth_runtime_status: blocked
```

## Purpose

Doc `260_POST_REENTRY_NAMED_USE_CASE_ADJUDICATION.md` selected `source_breadth_named_use_case_packet` as the next planning artifact. This packet answers that requirement from current repo evidence.

The result is no runtime now. Current repo authority proves a bounded source boundary, not a concrete new source product need. Selecting local upload, local directory ingestion, broad file upload, web connector retrieval, RAG/vector retrieval, unbounded runtime DB reads, or a generic source adapter registry from repo structure alone would be speculative and fragile.

## Repo-confirmed source truth

Current source authority remains:

- `backend/app/services/layer3_source_boundary.py` supports only `dataset_version` and `aps_content_document`.
- `backend/app/services/layer3_source_boundary.py` lists `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db` as unsupported source classes.
- `backend/app/services/layer3_source_boundary.py` reports `source_upload_enabled: false`, `local_directory_enabled: false`, `broad_file_upload_enabled: false`, `web_connector_enabled: false`, `rag_vector_enabled: false`, and `unbounded_runtime_db_enabled: false` through the source-boundary contract.
- Doc `153_SOURCE_BREADTH_FREEZE.md` freezes current admitted classes with server-owned raw materialization only.
- Doc `154_RAW_INGESTION_MATERIALIZATION_FREEZE.md` governs the already-live raw-mixed materialization boundary for existing source classes only.
- Doc `215_SOURCE_BREADTH_AUTHORITY_DISCOVERY_CLOSEOUT.md` records insufficient authority for source-breadth runtime and keeps all broader source families blocked.
- Docs `249` and `250` require a named source use case and already record `entry_decision: no_runtime_now` when that use case is absent.

## Named-use-case gate result

```yaml
named_source_use_case_gate:
  concrete_operator_problem_current_sources_cannot_solve:
    status: not_found_in_current_authority
    consequence: runtime_blocked
  selected_source_family:
    status: none_selected_runtime_blocked
    consequence: runtime_blocked
  adapter_input_mode:
    status: not_selected
    consequence: runtime_blocked
  source_of_truth:
    status: current_classes_only_server_owned_manifest_hash_authority
    consequence: sufficient_for_existing_paths_only
  storage_security_model:
    status: current_storage_root_manifest_hash_check_only
    consequence: insufficient_for_new_source_surface
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

## Why no source runtime is selected

The blocker is not missing engineering effort. The blocker is missing product/operator specificity.

A safe source runtime must start from one named operator need, then choose the smallest source family and authority model for that need. Current authority does not answer:

- whether the next source should be uploaded files, local directories, web retrieval, RAG/vector retrieval, runtime DB reads, or another source class;
- whether bytes should be operator-provided, server-owned, connector-fetched, provider-hosted, or already staged;
- whether network retrieval is forbidden, fake-provider-only, local-only, or explicitly admitted;
- whether auth/security must precede source expansion;
- whether rendered controls are needed or the source use case can be operated through backend/API only;
- how downstream material preview, Gate B/Gate C, execution, package, handoff/export, and qualitative/RAG semantics should treat the new source.

Guessing any of those would create a brittle source abstraction and could leak local paths, connector/provider assumptions, browser state, or prompt/vector behavior into the authority chain.

## Required future source-use-case packet contents

A future source runtime entry may proceed only after a packet names:

- one concrete source use case;
- why current `dataset_version` and `aps_content_document` paths are insufficient;
- one selected source family;
- one adapter/input mode;
- canonical authority for identity, bytes, metadata, freshness, and provenance;
- storage-root and security/leakage rules;
- network retrieval policy;
- request/response and forbidden-field contracts;
- idempotency, stale-authority, rollback, and conflict behavior;
- downstream semantics for material preview through package/export/RAG lanes;
- rendered-control and headed/headless/theme proof obligations if UI changes are required;
- auth/security escalation rule if the source surface introduces identity, permission, credential, or nonlocal exposure risk.

## Non-admission

This packet admits no runtime behavior, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, source adapter registry behavior, local upload, local-directory ingestion, broad file upload, arbitrary local path input, web connector retrieval, RAG/vector retrieval, vector index creation, unbounded runtime DB source reads, external connector invocation, destination writes, package mutation/reconstruction, broad qualitative/hybrid/RAG execution, full mockup activation, auth/security behavior, hidden LLM planning, provider/public URL behavior, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Stop condition

Stop before implementation if the next source proposal cannot name one concrete operator/product use case and resolve the source family, input mode, authority, storage/security, provenance, downstream, rendered-control, and auth/security dimensions from explicit evidence rather than inference.
