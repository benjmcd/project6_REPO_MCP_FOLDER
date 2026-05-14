# Source Expansion Named Source Family Revalidation Packet

## Status

Status: planning/control source expansion named-source-family revalidation packet only; no runtime behavior admitted.

This packet follows current-main doc `367_NEXT_DEFERRED_SERVER_AUTHORITATIVE_RUNTIME_LANE_AFTER_BROAD_QUAL_RAG_CURRENT_MAIN_SYNC.md`.

The selected packet is `source_expansion_named_source_family_revalidation_packet`.

## Decision

No source expansion runtime is selected.

The revalidation result is `no_runtime_now_source_expansion_named_source_family_absent`.

Current repo authority admits `dataset_version`, `aps_content_document`, and bounded `operator_uploaded_single_source` source-intake/Gate B material admission only. It does not admit arbitrary local directory, broad file upload, web connector, RAG/vector source class, or unbounded runtime DB source expansion.

The next required action is `current_main_sync_source_expansion_named_source_family_revalidation_packet_after_merge`.

## Repo-confirmed authority

Current repo authority is intentionally bounded:

- `backend/app/services/layer3_source_boundary.py` defines `SOURCE_BOUNDARY_MODE = "supported_source_classes_plus_operator_source_intake"`.
- `backend/app/services/layer3_source_boundary.py` supports only `dataset_version` and `aps_content_document` as source classes, plus bounded source-intake modes for operator-uploaded single-source flow.
- `backend/app/services/layer3_source_boundary.py` lists `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db` as unsupported source classes.
- `backend/app/services/layer3_source_boundary.py` keeps `local_directory_enabled`, `broad_file_upload_enabled`, `web_connector_enabled`, `rag_vector_enabled`, and `unbounded_runtime_db_enabled` false.
- `backend/app/services/layer3_source_intake.py` keeps `local_directory`, `source_expansion`, `web_connector`, and `rag_vector_index` as forbidden or disabled for the existing source-intake path.
- `backend/app/services/layer3_preflight_request_contract.py` treats local-directory, source-expansion, web-connector, and RAG/vector sentinels as non-admitted manual constraint scope.

## Gate result

```yaml
source_expansion_named_source_family_revalidation:
  selected_planning_mode: source_expansion_named_source_family_revalidation_packet
  entry_decision: no_runtime_now_source_expansion_named_source_family_absent
  admitted_current_source_classes:
    - dataset_version
    - aps_content_document
  admitted_current_source_intake_family: operator_uploaded_single_source
  arbitrary_local_directory_runtime_selected: false
  broad_file_upload_runtime_selected: false
  web_connector_runtime_selected: false
  rag_vector_source_runtime_selected: false
  unbounded_runtime_db_source_selected: false
  named_new_source_family_selected: null
  request_response_contract_selected: false
  storage_ref_hash_authority_selected: false
  stale_authority_policy_selected: false
  idempotency_replay_recovery_policy_selected: false
  receipt_audit_contract_selected: false
  rendered_control_plan_selected: false
  auth_security_posture_selected: false
```

## Why runtime remains blocked

Current main does not prove:

- one named source family beyond the admitted dataset/APS/operator-uploaded single-source surfaces
- one operator use case for that source family
- source identity and provenance ownership
- storage/ref/hash authority for the new source family
- freshness and stale-authority behavior
- idempotency, duplicate-source, replay, or recovery behavior
- safe request/response contract
- result/receipt/audit contract
- rendered controls or headed/headless/theme proof obligations
- leak controls for local paths, directory entries, connector targets, provider URLs, raw bytes, traces, screenshots, responses, and errors
- auth/security posture

The existing source-intake runtime is not absent; it is deliberately bounded to operator-uploaded single-source intake and Gate B material admission. That existing path is not authority to widen into arbitrary local directory, broad file upload, web connector, RAG/vector source, or unbounded runtime DB source expansion.

## Explicit non-goals

No arbitrary local-directory source runtime is admitted.

No broad file-upload source runtime is admitted.

No web connector source runtime is admitted.

No RAG/vector source runtime is admitted.

No unbounded runtime DB source expansion is admitted.

No generic source upload is admitted beyond the bounded operator-uploaded single-source intake path.

No source expansion route is admitted.

No source expansion model or migration is admitted.

No broad qualitative runtime is admitted.

No hybrid execution runtime is admitted.

No connector/destination dispatch is admitted.

No provider-public delivery/use is admitted.

No package mutation or reconstruction is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No frontend-only durable authority is admitted.

## Future reopening condition

A later source-expansion runtime freeze may proceed only if it names:

- one source family and one operator use case
- exact source identity and provenance authority
- storage/ref/hash authority
- freshness and stale-authority behavior
- idempotency, duplicate-source, replay, and recovery behavior
- request/response contract
- result/receipt/audit contract
- leak controls
- browser proof obligations if rendered controls are involved
- auth/security posture

Until then, source expansion remains blocked behind the existing supported source classes and bounded source-intake boundary.
