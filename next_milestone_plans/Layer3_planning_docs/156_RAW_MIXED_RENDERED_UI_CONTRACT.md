# Raw Mixed Rendered Manifest UI Contract

Status: planning/control UI contract paired with `155_RAW_MIXED_RENDERED_UI_FREEZE.md`.

This contract specifies the future rendered `/review/layer3` behavior for `raw_mixed_server_owned_manifest_ref_ui_entry`. It admits no current runtime behavior and does not implement UI controls by itself.

## Route And State Authority

The future rendered UI may call only the already-live materialization route for raw mixed source authority:

- `POST /api/v1/layer3/source/mixed-corpus/materialize`

After materialization, downstream rendered flow must use only the existing Layer 3 workbench routes already used by the current rendered source/material/Gate B/Gate C/plan path. Server state is the only durable authority. Browser state may hold form input, a generated `client_request_id`, an in-flight request, and display-only response data.

The browser must not create source authority, repair failed materialization, fabricate missing IDs, mutate package payloads, or authorize downstream flow without server-returned source IDs and refreshed candidate state.

## Future UI Entry Point

The first future implementation should start at the smallest rendered workflow:

1. open `/review/layer3`;
2. enter or select a server-owned manifest ref, manifest hash, corpus batch id, and admitted source classes;
3. confirm server-owned manifest authority;
4. call `POST /api/v1/layer3/source/mixed-corpus/materialize`;
5. display returned `dataset_version` and `aps_content_document` IDs as server-created source authority;
6. refresh source candidate APIs and select only the returned IDs;
7. drive existing rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval controls;
8. stop before any missing control would require source expansion, backend expansion, provider/public URL, connector/destination dispatch, package mutation, RAG/vector, mockup, hidden LLM, auth/security, or model/migration behavior.

The implementation must not present upload, directory, web connector, RAG/vector, provider, destination, or broad ingestion affordances.

## Request Contract

Rendered materialization requests must be assembled from form state plus a fresh `client_request_id`. They may include only:

- `schema_id`;
- `schema_version`;
- `client_request_id`;
- `materialization_mode`;
- `corpus_batch_id`;
- `artifact_manifest_ref`;
- `artifact_manifest_hash`;
- `requested_source_classes`;
- `operator_confirmation`.

The UI must reject or omit every field outside the live DTO. In particular, requests must not include local path, upload, directory, URL fetch, connector, destination, credential, provider/public URL, signed URL, RAG/vector, prompt/model, package mutation, package replacement, mockup, auth/security, migration, or browser-durable fields.

## Rendered States

The UI must distinguish these states:

- unavailable because the manifest form is incomplete;
- ready after admitted source classes, manifest ref, hash, mode, and operator confirmation are present;
- submitting one in-flight materialization request;
- materialized with returned source IDs and no Layer 3 flow state created by materialization itself;
- blocked by server fail-closed response;
- stale/conflicting because refreshed candidates do not include returned IDs;
- error because request or refresh failed.

Success state may enable downstream rendered source selection only after candidate refresh confirms the returned source IDs.

## Theme And Accessibility Contract

The future implementation must preserve current `/review/layer3` theme behavior:

- every new control has stable selectors;
- labels, help text, status badges, errors, disabled states, and loading states are visible in the current theme set;
- focus order reaches every new control and returns to downstream source controls after success;
- desktop and mobile layouts avoid text overlap, clipping, and layout shift;
- headed and headless Chromium run the same raw mixed rendered manifest workflow;
- theme persistence cannot change request payloads or server authority.

## Negative Invariants

The future implementation must keep all of these absent:

- arbitrary local path input;
- local upload, directory picker, broad file upload, or drag-and-drop ingestion;
- web connector retrieval, connector credentials, connector invocation, destination selection, or destination write;
- source adapter registry or source-class expansion beyond `dataset_version` and `aps_content_document`;
- RAG/vector retrieval or index creation;
- provider/public URL or signed URL generation;
- package mutation, reconstruction, supersession, replacement, or payload rewrite;
- hidden LLM planning or prompt/model control;
- full mockup activation;
- auth/security behavior changes;
- frontend-only durable authority;
- backend route, DTO, service, model, or migration changes unless separately frozen.

## Required Tests For Runtime

The later runtime PR must include:

- page/static tests for request-field allowlist, disabled-state gating, and absent deferred controls;
- Playwright headless proof for the raw mixed rendered manifest workflow;
- Playwright headed proof for the same workflow;
- candidate-refresh proof that returned IDs are visible/selectable before downstream flow;
- failure proof for server rejection without Layer 3 flow state creation;
- regression proof for existing seed-only bridge rendered smoke and materialization API-setup smoke;
- progress checker guards for this contract and stale wording;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.
