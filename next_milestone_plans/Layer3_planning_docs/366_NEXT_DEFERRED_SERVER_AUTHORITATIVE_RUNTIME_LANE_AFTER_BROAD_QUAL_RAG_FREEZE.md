# Next Deferred Server-Authoritative Runtime Lane After Broad Qual RAG Freeze

## Status

Status: planning/control next deferred server-authoritative runtime lane freeze after broad qualitative hybrid RAG no-runtime; no runtime behavior admitted.

This freeze follows current-main doc `365_BROAD_QUALITATIVE_HYBRID_RAG_NAMED_MODE_REVALIDATION_CURRENT_MAIN_SYNC.md`.

The selected next packet is `source_expansion_named_source_family_revalidation_packet`.

This does not select source expansion runtime.

The next required action after merge is `current_main_sync_next_deferred_runtime_lane_after_broad_qual_rag_freeze`.

## Decision

The next deferred lane to revalidate is source expansion, but only as a named-source-family revalidation packet.

The freeze result is `selected_source_expansion_named_source_family_revalidation_packet_only`.

Runtime remains blocked because current repo authority admits dataset_version, aps_content_document, and the bounded operator-uploaded single-source intake/Gate B path; it does not admit arbitrary local directory, broad file upload, web connector, RAG/vector source class, or unbounded runtime DB source expansion.

## Repo-confirmed basis

Live repo surfaces show source expansion as deferred rather than admitted:

- `backend/app/services/layer3_source_boundary.py` sets supported source classes to `dataset_version` and `aps_content_document`, plus bounded source-intake modes for operator-uploaded single-source flow.
- `backend/app/services/layer3_source_boundary.py` lists unsupported source classes: `rag_vector_index`, `arbitrary_local_directory`, `broad_file_upload`, `web_connector`, and `unbounded_runtime_db`.
- `backend/app/services/layer3_source_boundary.py` keeps `local_directory_enabled`, `broad_file_upload_enabled`, `web_connector_enabled`, `rag_vector_enabled`, and `unbounded_runtime_db_enabled` false.
- `backend/app/services/layer3_source_intake.py` keeps `local_directory`, `source_expansion`, `web_connector`, and `rag_vector_index` as forbidden or disabled scope for the existing source-intake path.
- `backend/app/services/layer3_preflight_request_contract.py` keeps source expansion and local-directory/web-connector sentinel fields outside admitted preflight manual constraints.

## Why this is the narrowest next lane

Provider-public delivery/use has already been closed as contract-only/no-runtime.

Connector/destination dispatch has already been revalidated as no-runtime because no named connector or destination target exists.

Package mutation has already been revalidated as no-runtime because no named rendered operator package-revision action exists.

Broad qualitative/hybrid/RAG has already been revalidated as no-runtime because only `single_aps_doc_qualitative_pass` is admitted.

Full mockup activation remains target-state-only and blocked until a new concrete mockup activation target is named.

Auth/security behavior remains cross-cutting and should not be selected before a concrete runtime lane names the behavior it must secure.

Source expansion is the remaining deferred family with a concrete server-authoritative shape and explicit unsupported source classes, so it is the next packet to revalidate.

## Gate result

```yaml
next_deferred_runtime_lane_after_broad_qual_rag:
  selected_packet: source_expansion_named_source_family_revalidation_packet
  selected_runtime: null
  freeze_result: selected_source_expansion_named_source_family_revalidation_packet_only
  source_expansion_runtime_selected: false
  local_directory_runtime_selected: false
  broad_file_upload_runtime_selected: false
  web_connector_runtime_selected: false
  rag_vector_source_runtime_selected: false
  unbounded_runtime_db_source_selected: false
  current_failure_boundary: unsupported_source_family_absent
  next_required_action_after_merge: current_main_sync_next_deferred_runtime_lane_after_broad_qual_rag_freeze
```

## Explicit non-goals

No arbitrary local-directory source runtime is admitted.

No broad file-upload source runtime is admitted.

No web connector source runtime is admitted.

No RAG/vector source runtime is admitted.

No unbounded runtime DB source expansion is admitted.

No generic source upload is admitted beyond the bounded operator-uploaded single-source intake path.

No broad qualitative runtime is admitted.

No hybrid execution runtime is admitted.

No connector/destination dispatch is admitted.

No provider-public delivery/use is admitted.

No package mutation or reconstruction is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No route, model, migration, schema, or frontend-only durable authority is admitted.

## Future packet requirements

The later source-expansion named-source-family revalidation packet must determine whether current repo authority names exactly one source family beyond the already admitted dataset/APS/source-intake surfaces. If not, it must close as no-runtime.

If a future runtime is ever selected, it must first name:

- one source family and one operator use case
- source identity and provenance ownership
- storage/ref/hash authority
- freshness and stale-authority behavior
- idempotency, duplicate-source, replay, and recovery behavior
- leak controls for local paths, directory entries, connector targets, provider URLs, raw bytes, traces, responses, and errors
- request/response contract
- browser proof obligations if rendered controls are involved
- auth/security posture

Until those are named, source expansion remains blocked behind the existing bounded source-intake and supported-source-class boundary.
