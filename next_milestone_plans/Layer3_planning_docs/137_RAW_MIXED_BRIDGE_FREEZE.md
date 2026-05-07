# Layer 3 Raw Mixed Bridge Freeze

Status: implementation-entry freeze plus bounded runtime contract for `raw_mixed_corpus_bridge_seed_only` on branch `codex/l3-raw-mixed-bridge-seed` from `project6-origin/main=b6446d53`.

This artifact now governs the bounded seed-only runtime after the bounded API-created mixed `dataset_version` plus APS companion path from PR #689 and the planning/control freeze from PR #690. Runtime implementation scope is limited to `POST /api/v1/layer3/source/mixed-corpus/seed`; it reuses already materialized admitted source authority from a hash-checked server-owned storage-root manifest. It does not implement broad ingestion, add models or migrations, change downstream Layer 3 flow services, start a Layer 3 flow, accept local uploads, traverse local directories, fetch web connectors, read unbounded runtime DB sources, build RAG/vector indexes, mutate packages, dispatch connectors, generate provider/public URLs, activate mockups, or change auth/security behavior.

## Authority Snapshot

- authority_ref: `project6-origin/main`
- authority_commit: `b6446d53ce0e1f90837d5d491c898ad5fd29a51b`
- implementation_branch: `codex/l3-raw-mixed-bridge-seed`
- predecessor runtime proof: PR `#689` bounded API-created `dataset_version` associated-cohort plus APS companion delivery path
- predecessor planning/control proof: PR `#690` raw mixed bridge freeze
- current source boundary: `123_SOURCE_EXPANSION_FREEZE.md`
- current source owner: `backend/app/services/layer3_source_boundary.py`
- raw mixed bridge owner: `backend/app/services/layer3_raw_mixed_bridge.py`
- current supported source classes: `dataset_version`, `aps_content_document`
- current bounded E2E proof: `backend/tests/test_layer3_bounded_e2e.py`
- current raw mixed seed proof: `backend/tests/test_layer3_raw_mixed_bridge.py`
- existing APS artifact services inspected: `backend/app/services/nrc_aps_artifact_ingestion.py`, `backend/app/services/nrc_aps_artifact_ingestion_gate.py`
- existing post-session APS multisource owner inspected: `backend/app/services/layer3_aps_multisource.py`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Decision

The selected raw mixed bridge mode is exactly:

- selected_raw_mixed_bridge_mode: `raw_mixed_corpus_bridge_seed_only`

The runtime may only bridge server-owned, already materialized APS artifacts into the existing admitted Layer 3 source classes before a Layer 3 flow begins:

- existing `dataset_version` source rows
- existing `aps_content_document` source rows
- existing APS provenance/linkage rows needed to make those two source classes traceable

The implementation must keep source seeding separate from Layer 3 flow execution. It may return stable source ids for a later normal Layer 3 API flow, but it must not call preflight, source preview, material preview, Gate B, Gate C, planning, execution, package, handoff, APS dispatch, or export/download endpoints as part of the seed action.

## Why This Is The Next Safe Boundary

PR #689 proved that the current Layer 3 API path can carry an already selected APS content document as handoff companion provenance alongside an API-created deterministic `dataset_version` associated cohort. That did not prove raw mixed-corpus ingestion.

Current `123_SOURCE_EXPANSION_FREEZE.md` still selects `supported_source_classes_only`. Therefore a direct implementation of local upload, directory ingestion, web connector retrieval, RAG/vector retrieval, or broad source adapter expansion would overrun current authority. The next safe step is to freeze a seed-only bridge that targets the existing admitted source classes and makes every broader source family remain blocked until separately selected.

## Runtime Scope

The bounded implementation may add only:

- owner service: `backend/app/services/layer3_raw_mixed_bridge.py`
- route: `POST /api/v1/layer3/source/mixed-corpus/seed`
- request DTO: `Layer3RawMixedCorpusSeedRequest`
- response DTO: `Layer3RawMixedCorpusSeedResponse`
- request schema id: `layer3.raw_mixed_corpus_seed_request.v1`
- response schema id: `layer3.raw_mixed_corpus_seed_result.v1`
- manifest schema id: `layer3.raw_mixed_corpus_seed_manifest.v1`
- mode: `raw_mixed_corpus_bridge_seed_only`
- persistence target: existing source/provenance families needed to reuse `DatasetVersion` and `ApsContentDocument` authority
- artifact behavior: reference an existing server-owned storage-root manifest only, with the manifest hash checked before use
- DB read behavior: reads existing `DatasetVersion`, `DatasetSourceProvenance`, `ApsContentDocument`, `ApsContentLinkage`, `ConnectorRun`, and `ConnectorRunTarget` rows
- DB write behavior: writes no database rows
- file read behavior: reads only the named server-owned storage-root manifest file after requiring a SHA-256 hash
- file write behavior: writes no files
- flow behavior: none

No implementation under this freeze may add a broad adapter registry, plugin system, browser upload target, local directory crawler, web connector fetch, RAG/vector retrieval path, full corpus search, package mutation, provider URL, connector/destination dispatch, hidden LLM plan, or full mockup behavior.

## Request Contract

The request must be strict and response-safe:

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

The route must reject these before service mutation:

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

## Response Contract

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

## Required Tests

The implementation must prove:

- missing `client_request_id` fails closed;
- unsupported requested source classes fail closed;
- forbidden source/upload/local-directory/web/RAG/vector/package/connector/provider/mockup/auth fields fail validation before service mutation;
- stale artifact manifest hash fails closed;
- unknown APS run or target ids fail closed;
- successful seed action returns existing deterministic `DatasetVersion` and `ApsContentDocument` source authority only and writes no database rows or files;
- duplicate `client_request_id` is deterministic;
- no Layer 3 session, descriptor, material snapshot, typing, plan, pass, execution, result, package, handoff, APS dispatch, export/download, connector, provider URL, vector index, package mutation, mockup, or auth/security side effect occurs;
- the returned ids can be consumed through the normal separate API preflight/source-preview/material-preview path without special browser or planning-doc authority.

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

This bounded runtime slice is accepted only when:

- this file exists and contains `selected_raw_mixed_bridge_mode: raw_mixed_corpus_bridge_seed_only`;
- `layer3_progress_board.md`, `layer3_progress_manifest.json`, and `layer3_workbench_proof_manifest.json` record this slice as the bounded seed-only runtime;
- `tools/l3-progress-check.py` requires this document, the owner service, the API route, and focused tests, and fails closed if the selected mode or seed-only boundary drifts;
- `backend/app/services/layer3_raw_mixed_bridge.py` owns the seed-only runtime and writes no DB rows or files;
- `backend/app/api/layer3.py` exposes only `POST /api/v1/layer3/source/mixed-corpus/seed` for this bridge;
- `backend/tests/test_layer3_raw_mixed_bridge.py` proves success, idempotent reuse, forbidden fields, unsupported classes, stale manifest hash, unknown APS target, missing client request id, and no flow/package/export side effects;
- `backend/app/services/layer3_source_boundary.py` still reports `SOURCE_BOUNDARY_MODE = "supported_source_classes_only"`;
- `python .\tools\l3-progress-check.py` passes;
- `python -m pytest .\backend\tests\test_layer3_raw_mixed_bridge.py -q` passes;
- `git diff --check` reports no whitespace errors.
