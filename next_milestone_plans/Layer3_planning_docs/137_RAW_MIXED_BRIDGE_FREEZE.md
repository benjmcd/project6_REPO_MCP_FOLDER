# Layer 3 Raw Mixed Bridge Freeze

Status: planning/control implementation-entry freeze only for `raw_mixed_corpus_bridge_seed_only` on branch `codex/l3-raw-mixed-bridge-freeze` from `project6-origin/main=70edbbf6`. No runtime behavior is admitted by this document.

This artifact selects the next source-side bridge decision after the bounded API-created mixed `dataset_version` plus APS companion path from PR #689. It does not implement ingestion, add a route, add models or migrations, change existing Layer 3 services, start a Layer 3 flow, accept local uploads, traverse local directories, fetch web connectors, read unbounded runtime DB sources, build RAG/vector indexes, mutate packages, dispatch connectors, generate provider/public URLs, activate mockups, or change auth/security behavior.

## Authority Snapshot

- authority_ref: `project6-origin/main`
- authority_commit: `70edbbf600c096ffcef8972d1839589488a02cec`
- planning_branch: `codex/l3-raw-mixed-bridge-freeze`
- predecessor runtime proof: PR `#689` bounded API-created `dataset_version` associated-cohort plus APS companion delivery path
- current source boundary: `123_SOURCE_EXPANSION_FREEZE.md`
- current source owner: `backend/app/services/layer3_source_boundary.py`
- current supported source classes: `dataset_version`, `aps_content_document`
- current bounded E2E proof: `backend/tests/test_layer3_bounded_e2e.py`
- existing APS artifact services inspected: `backend/app/services/nrc_aps_artifact_ingestion.py`, `backend/app/services/nrc_aps_artifact_ingestion_gate.py`
- existing post-session APS multisource owner inspected: `backend/app/services/layer3_aps_multisource.py`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Decision

The selected future raw mixed bridge mode is exactly:

- selected_raw_mixed_bridge_mode: `raw_mixed_corpus_bridge_seed_only`

The future implementation may only bridge server-owned, already materialized APS artifacts into the existing admitted Layer 3 source classes before a Layer 3 flow begins:

- existing `dataset_version` source rows
- existing `aps_content_document` source rows
- existing APS provenance/linkage rows needed to make those two source classes traceable

The future implementation must keep source seeding separate from Layer 3 flow execution. It may return stable source ids for a later normal Layer 3 API flow, but it must not call preflight, source preview, material preview, Gate B, Gate C, planning, execution, package, handoff, APS dispatch, or export/download endpoints as part of the seed action.

## Why This Is The Next Safe Boundary

PR #689 proved that the current Layer 3 API path can carry an already selected APS content document as handoff companion provenance alongside an API-created deterministic `dataset_version` associated cohort. That did not prove raw mixed-corpus ingestion.

Current `123_SOURCE_EXPANSION_FREEZE.md` still selects `supported_source_classes_only`. Therefore a direct implementation of local upload, directory ingestion, web connector retrieval, RAG/vector retrieval, or broad source adapter expansion would overrun current authority. The next safe step is to freeze a seed-only bridge that targets the existing admitted source classes and makes every broader source family remain blocked until separately selected.

## Future Runtime Scope

A later implementation PR may add only:

- future owner service: `backend/app/services/layer3_raw_mixed_bridge.py`
- future route: `POST /api/v1/layer3/source/mixed-corpus/seed`
- future request DTO: `Layer3RawMixedCorpusSeedRequest`
- future response DTO: `Layer3RawMixedCorpusSeedResponse`
- future request schema id: `layer3.raw_mixed_corpus_seed_request.v1`
- future response schema id: `layer3.raw_mixed_corpus_seed_result.v1`
- future mode: `raw_mixed_corpus_bridge_seed_only`
- future persistence target: existing source/provenance families needed to create or reuse `DatasetVersion` and `ApsContentDocument` authority
- future artifact behavior: reference existing server-owned APS artifacts only, with hashes checked before use
- future flow behavior: none

No future implementation under this freeze may add a broad adapter registry, plugin system, browser upload target, local directory crawler, web connector fetch, RAG/vector retrieval path, full corpus search, package mutation, provider URL, connector/destination dispatch, hidden LLM plan, or full mockup behavior.

## Future Request Contract

The future request must be strict and response-safe:

```json
{
  "schema_id": "layer3.raw_mixed_corpus_seed_request.v1",
  "client_request_id": "string",
  "seed_mode": "raw_mixed_corpus_bridge_seed_only",
  "corpus_batch_id": "string",
  "aps_run_id": "string",
  "target_ids": ["string"],
  "artifact_manifest_ref": "server-owned-ref",
  "artifact_manifest_hash": "sha256",
  "requested_source_classes": ["dataset_version", "aps_content_document"],
  "operator_confirmation": true
}
```

The request must fail closed if `requested_source_classes` includes anything outside `dataset_version` and `aps_content_document`.

## Forbidden Request Fields

The future route must reject these before service mutation:

- `source_upload`
- `local_upload`
- `local_directory`
- `local_path`
- `directory_path`
- `broad_file_upload`
- `file_bytes`
- `file_glob`
- `web_connector`
- `connector_key`
- `connector_secret`
- `source_url`
- `provider_url`
- `public_url`
- `rag_vector_index`
- `rag_plan`
- `vector_plan`
- `embedding_model`
- `runtime_db_write`
- `unbounded_runtime_db`
- `package_payload`
- `rebuild_package`
- `rewrite_output`
- `destination_id`
- `destination_url`
- `hidden_llm_planning`
- `mockup_activation`
- `auth_policy_override`

## Future Response Contract

Successful response shape:

```json
{
  "schema_id": "layer3.raw_mixed_corpus_seed_result.v1",
  "request_id": "string",
  "seed_mode": "raw_mixed_corpus_bridge_seed_only",
  "source_seed_state": "seeded",
  "dataset_version_ids": ["string"],
  "aps_content_document_ids": ["string"],
  "source_classes": ["dataset_version", "aps_content_document"],
  "artifact_manifest_ref": "server-owned-ref",
  "artifact_manifest_hash": "sha256",
  "layer3_flow_started": false,
  "next_allowed_actions": ["run_layer3_preflight_with_seeded_source_ids"]
}
```

The response must not include uploaded file refs, local directory refs, connector ids, provider URLs, public URLs, vector ids, package ids, handoff ids, execution ids, destination ids, generated plan ids, browser-local authority, or raw file bytes.

## Positive Invariants

- `raw_mixed_corpus_bridge_seed_only` is the only selected future bridge mode.
- The bridge produces or reuses only `dataset_version` and `aps_content_document` authority.
- Source seeding remains separate from Layer 3 flow execution.
- Stable ids and stable hashes are required for every seeded source and server-owned artifact ref.
- Repeated `client_request_id` behavior must be deterministic.
- Existing Layer 3 preflight/source-preview/material-preview/Gate B/Gate C contracts remain the only way to start the Layer 3 flow.
- Existing `SUPPORTED_SOURCE_CLASSES` remains unchanged until the future implementation is explicitly admitted.
- Existing `SOURCE_EXPANSION_DEFERRED_CAPABILITIES` remains active for local upload/directory, broad file upload, web connector, RAG/vector, and unbounded runtime DB source expansion.

## Negative Invariants

This planning/control slice must not accidentally admit:

- runtime behavior by this document alone;
- source upload, local upload, or local directory ingestion;
- broad file upload or file glob ingestion;
- web connector source retrieval;
- RAG/vector retrieval or index creation;
- unbounded runtime DB source reads or writes;
- broad source adapter registry behavior;
- Layer 3 preflight, source preview, material preview, Gate B, Gate C, planning, execution, package, handoff, APS dispatch, or export/download as part of source seeding;
- `L3Session`, `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `L3ReconciliationRecord`, connector, destination, provider/public URL, package mutation, qualitative/hybrid/RAG, hidden LLM, full mockup, or auth/security behavior.

## Required Future Tests

A later implementation PR must prove:

- missing `client_request_id` fails closed;
- unsupported requested source classes fail closed;
- forbidden source/upload/local-directory/web/RAG/vector/package/connector/provider/mockup/auth fields fail validation before service mutation;
- stale artifact manifest hash fails closed;
- unknown APS run or target ids fail closed;
- successful seed action creates or reuses deterministic `DatasetVersion` and `ApsContentDocument` source authority only;
- duplicate `client_request_id` is deterministic;
- no Layer 3 session, descriptor, material snapshot, typing, plan, pass, execution, result, package, handoff, APS dispatch, export/download, connector, provider URL, vector index, package mutation, mockup, or auth/security side effect occurs;
- the existing bounded E2E can consume the returned ids through the normal separate API flow without special browser or planning-doc authority.

## Stop Conditions

Stop before implementation if the intended change requires:

- accepting local files or directories from a user request;
- crawling a directory;
- fetching a web connector source;
- adding RAG/vector retrieval;
- widening `SUPPORTED_SOURCE_CLASSES`;
- adding a general source adapter registry;
- starting a Layer 3 flow inside the seed route;
- adding model/migration/schema changes not limited to deterministic source/provenance authority;
- package mutation/reconstruction;
- connector/destination dispatch;
- provider/public URL generation;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior.

## Acceptance Criteria

This planning/control slice is accepted only when:

- this file exists and contains `selected_raw_mixed_bridge_mode: raw_mixed_corpus_bridge_seed_only`;
- `layer3_progress_board.md`, `layer3_progress_manifest.json`, and `layer3_workbench_proof_manifest.json` record this slice as planning/control only;
- `tools/l3-progress-check.py` requires this document and fails closed if the selected mode or no-runtime boundary drifts;
- `backend/app/services/layer3_source_boundary.py` still reports `SOURCE_BOUNDARY_MODE = "supported_source_classes_only"`;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
