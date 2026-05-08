# Source Breadth Entry Contract

Status: planning/control contract paired with `193_SOURCE_BREADTH_ENTRY_FREEZE.md`.

This contract defines requirements for moving beyond the deferred `source_breadth_entry_freeze` decision. It admits no source-class expansion, source adapter registry, local upload, local-directory ingestion, broad file upload, web connector retrieval, RAG/vector retrieval, unbounded runtime DB source reads, arbitrary local path input, route, DTO, service behavior, model, migration, test behavior, rendered UI control, package mutation, provider/public URL runtime, connector/destination dispatch, full mockup activation, hidden LLM planning, frontend-only durable authority, or auth/security behavior change.

Docs `123`, `137`, `153`, and `154` remain authority for the supported-source boundary, raw mixed seed-only bridge, source breadth posture, and current-class materialization runtime. Docs `184` through `192` remain the broader downstream governance chain. This contract is the narrower post-PR #751 source-breadth entry-decision layer.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior;
2. `backend/app/services/layer3_source_boundary.py` and `backend/tests/test_layer3_source_boundary.py`;
3. `backend/app/services/layer3_raw_mixed_bridge.py` and `backend/tests/test_layer3_raw_mixed_bridge.py`;
4. `backend/app/services/layer3_raw_mixed_materialization.py` and `backend/tests/test_layer3_raw_mixed_materialization.py`;
5. docs `123`, `137`, `153`, and `154`;
6. post-signed-reference and downstream docs `184` through `192`;
7. this contract and `193_SOURCE_BREADTH_ENTRY_FREEZE.md`.

Planning prose, browser state, mockup screenshots, local fixture state, manually selected files, local filesystem paths, copied URLs, connector history, vector index state, or prior PR titles are not sufficient authority for runtime implementation.

## Entry Decision Contract

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_supported_source_boundary_status: supported_source_classes_only
live_raw_mixed_seed_status: raw_mixed_corpus_bridge_seed_only
live_raw_mixed_materialization_status: raw_mixed_existing_source_materialization_entry
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed: concrete source-family use case, selected source family, selected adapter/input mode, source authority and provenance model, storage-root and path-security model, network retrieval policy if any, idempotency/concurrency/failure policy, downstream source/material/Gate B/Gate C semantics, no-cross-mode privilege escalation proof, test architecture, and theme/headed/headless proof if rendered controls are admitted.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `single_named_source_family_expansion`;
- `single_named_server_owned_adapter`;
- `source_breadth_read_only_inventory`;
- `raw_mixed_current_classes_only_extension`.

The selected mode must not rename local upload, local directory ingestion, web retrieval, RAG/vector retrieval, or unbounded DB reads as existing raw mixed materialization.

## Request Contract For Later Runtime

A future source-breadth request must be server-authority based. It may include or derive server-side selected source family, manifest ref/hash, deterministic source IDs, storage-root refs, provenance refs, idempotency key, and operator confirmation only if the future freeze admits those fields.

The request must not accept file bytes, arbitrary local paths, directory paths, glob patterns, browser-uploaded files, external URLs to fetch, connector credentials, provider URLs, destination URLs, vector-index instructions, hidden LLM instructions, package mutation fields, connector/destination dispatch fields, auth/security overrides, or full mockup activation fields unless a later freeze explicitly admits one narrow server-authoritative mode.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later freeze: selected mode, source family, deterministic source ids, source refs/hashes/sizes, provenance/audit refs, idempotency status, failure code, response-safe failure reason, and next actions.

The response must not expose local filesystem paths unless explicitly response-safe and already server-owned, credentials, bearer tokens, raw provider URLs, connector targets, destination targets, vector internals, package payloads, hidden LLM state, auth internals, or new source fields on existing source preview/material preview/Gate B/Gate C responses unless a later compatibility freeze admits it.

## Existing Source Runtime Compatibility Contract

This entry freeze must preserve existing source runtimes:

- `SUPPORTED_SOURCE_CLASSES` remains exactly `dataset_version` and `aps_content_document`;
- `raw_mixed_corpus_bridge_seed_only` remains seed-only and writes no DB rows or files;
- `raw_mixed_existing_source_materialization_entry` remains limited to server-owned manifest materialization for the current source classes;
- normal Layer 3 flow still starts only through preflight, source preview, material preview, Gate B, Gate C, plan, execution, package, handoff, and export endpoints;
- no source seeding/materialization endpoint may become a hidden Layer 3 flow start.

## Browser And UI Contract

This entry freeze adds no rendered UI control. If a later freeze admits rendered source-breadth controls, it must preserve `light`, `dark`, and `workbench` theme behavior, prove headed and headless Chromium consistency, expose no local path or credential authority in the browser, and avoid browser-state-only source authority.

## Test Contract For Later Runtime

Runtime or rendered implementation remains blocked until a later freeze names tests for disabled-by-default behavior, exact server source authority binding, forbidden local path/upload/directory/web/RAG/vector/provider/connector/package/mockup/auth fields, storage-root confinement, bad hash and missing manifest/file failure, unsupported source class failure, idempotency and concurrency, no Layer 3 flow state created by source setup alone, no package/provider/connector/destination side effects, no frontend-only durable authority, no path/credential/token leakage, and headed/headless plus theme coverage if UI changes are admitted.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only: docs `193` and `194` exist and are referenced; entry decision is `deferred`; selected mode is null; runtime status is `not_implemented`; existing supported-source, seed-only, and materialization boundaries are acknowledged without being expanded; evidence ledger exists and unverified source-family/adapter/input/storage/downstream authority forces deferral; source expansion exposure model exists and unknown values force deferral; capability isolation matrix exists and all new runtime flags remain false; negative invariants are present; docs do not claim new source-family runtime is live; docs do not conflate raw mixed current-class materialization with broad ingestion, local upload, local directory, web connector retrieval, RAG/vector, source adapter registry, or arbitrary local path input.

The checker must not pretend to validate actual source adapters, web connectors, vector stores, local upload UX, directory traversal behavior beyond existing tests, source-family semantics, network retrieval, auth/security posture, or operator usability in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to implement more than one source-breadth mode, widen supported source classes without a selected source-family freeze, accept arbitrary local paths/files/directories from a request, fetch external URLs or web connectors, build vector indexes, read unbounded runtime DB tables, add rendered controls without a rendered implementation-entry freeze and headed/headless proof, start Layer 3 flow inside source setup, mutate packages, generate provider/public URLs, dispatch connectors/destinations, activate target-state mockups as durable authority, or alter auth/security behavior without an auth/security freeze.
