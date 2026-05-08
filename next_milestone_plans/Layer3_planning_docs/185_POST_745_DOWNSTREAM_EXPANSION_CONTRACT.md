# Post-745 Downstream Expansion Contract

Status: planning/control contract paired with `184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md`.

This contract specifies how future work must move from the current raw mixed rendered signed-reference proof toward any broader downstream capability. It is not an implementation and admits no route, DTO, model, migration, production service, rendered control, provider URL, connector dispatch, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM behavior, or auth/security change.

## Selected Planning Mode

Selected mode: `post_745_raw_mixed_rendered_downstream_expansion_governance`.

This mode means the project has a proven rendered same-origin signed-reference path but must still freeze any future downstream expansion before implementation.

## Current-Main Capability Boundary

Current main proves:

- raw mixed rendered materialization through `dataset_version` and `aps_content_document`;
- rendered Gate B and Gate C progression for the admitted raw mixed path;
- rendered plan preview, approval, execution selection, execution start, result status, and result review;
- rendered package preview, package construction commit, and package review submit;
- rendered handoff/export prepare;
- rendered APS handoff dispatch;
- rendered external export/download prepare;
- rendered same-origin external export/download delivery;
- rendered same-origin signed-reference generation and single-use use.

Current main does not prove:

- provider/public URL generation;
- connector or destination dispatch;
- generic downstream dispatch;
- rendered package mutation/reconstruction controls;
- source-class expansion beyond `dataset_version` and `aps_content_document`;
- local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, or unbounded runtime DB source reads;
- broad qualitative, hybrid, RAG, or vector execution;
- full mockup activation;
- hidden LLM planning;
- auth/security behavior changes.

## Future Freeze Contract

Every future downstream implementation-entry freeze must contain:

- exact selected capability mode and non-goal list;
- exact owner route, service, and rendered control if any;
- exact request DTO, response schema, and forbidden field set;
- exact source authority and artifact authority basis;
- exact rows read and rows written;
- exact files/artifacts read and files/artifacts written;
- exact idempotency key behavior, concurrency behavior, replay behavior, and stale-authority failure behavior;
- exact provider, connector, destination, package, source, or security configuration variables if applicable;
- exact cleanup, expiry, revocation, retention, and audit expectations if applicable;
- exact tests, including headed and headless Chromium proof for rendered changes;
- exact light, dark, and workbench theme expectations for rendered workbench changes;
- exact negative side effects that must remain absent.

Planning prose, browser state, copied URLs, local fixture state, operator notes, mockup screenshots, or prior PR titles are not sufficient authority to start implementation.

## Provider/Public URL Entry Contract

A future provider/public URL freeze must choose exactly one mode:

- `provider_private_signed_url`;
- `provider_public_url`;
- `public_proxy_url`.

It must prove current same-origin attachment delivery and same-origin durable signed references are insufficient for a named use case. It must name provider/storage authority, configuration, object namespace, TTL, revocation policy, leak controls, error handling, and audit/receipt behavior before code.

It must fail closed for missing provider configuration, stale artifact authority, wrong session, wrong package, wrong APS bundle hash/size, expired or revoked authority, provider errors, forbidden client URL fields, and provider URL leakage into non-admitted responses.

It must not include connector dispatch, destination writes, package mutation, source expansion, RAG/vector behavior, full mockup activation, or auth/security widening unless those are separately frozen.

## Connector/Destination Dispatch Entry Contract

A future connector/destination freeze must choose exactly one mode:

- `internal_dispatch_record_only`;
- `single_named_connector_dispatch`;
- `single_named_destination_dispatch`.

It must name connector keys or destination ids, credentials/configuration, lifecycle states, retry/cancel/failure semantics, idempotency keys, receipt/audit shape, and operator-visible response behavior before code.

It must fail closed for missing connector/destination configuration, stale artifact authority, wrong destination, wrong connector, duplicate idempotency key, connector failure, destination failure, timeout, malformed request, and forbidden provider/package/source fields.

It must not include provider/public URL behavior, package mutation, source expansion, RAG/vector behavior, full mockup activation, or auth/security widening unless those are separately frozen.

## Package Mutation/Reconstruction Entry Contract

A future rendered package mutation freeze must name whether it is:

- preview-only;
- lineage-only commit;
- replacement package set;
- replacement artifact manifest;
- namespace/supersession behavior;
- rendered operator control.

It must prove package immutability rules, downstream dependency detection, invalidation/re-delivery semantics, and receipt compatibility across package review, handoff/export, APS handoff, external export/download, same-origin delivery, signed-reference use, provider URL, and connector dispatch authority before any rendered control or mutation behavior.

It must fail closed for stale payload refs, stale payload hashes, stale reconciliation records, stale package review submit refs, existing downstream receipts, forbidden package payload fields, and unsupported mutation modes.

## Source Breadth Entry Contract

A future source expansion freeze must name exactly one new source class or adapter mode and must not reopen broad source expansion.

It must prove source authority, ingestion boundary, path safety, storage-root policy, hash/provenance behavior, DB row ownership, cleanup/retention, and E2E fixture strategy before code.

It must fail closed for arbitrary local paths, local upload if not selected, local-directory traversal, web connector retrieval if not selected, RAG/vector retrieval if not selected, unbounded runtime DB reads, malformed manifests, unsupported source classes, and hidden source expansion through browser state.

## Qualitative/Hybrid/RAG/Vector Entry Contract

A future qualitative, hybrid, RAG, or vector freeze must choose one execution mode and one output taxonomy.

It must specify source classes, retrieval/index lifecycle, pass admission, artifact strategy, provenance, evaluation fixtures, failure modes, and downstream package compatibility before code.

It must not imply broad qualitative/hybrid/RAG activation from the existing narrow qualitative APS and raw mixed rendered proofs.

## UI Theme Contract

Any future rendered workbench change must preserve the current theme posture:

- `light` remains valid for status, preview, and review inspection;
- `dark` remains valid for execution and package construction surfaces;
- `workbench` remains valid for package submit, handoff/export, APS handoff, external export/download, and any downstream operation dock flow.

Rendered tests must avoid brittle visual assertions but must prove:

- controls are reachable and visible in the selected theme;
- text does not overlap or escape its container at the tested viewport;
- no target-state mockup control appears as a live durable authority control;
- headed and headless Chromium behavior is consistent for the admitted rendered path.

## Negative-Invariant Contract

Until a more specific implementation freeze admits otherwise, all future PRs must preserve:

- no provider/public URL behavior;
- no connector/destination dispatch;
- no package mutation/reconstruction beyond already admitted backend/API preview or lineage-only behavior;
- no new rendered controls for deferred capabilities;
- no source expansion beyond `dataset_version` and `aps_content_document`;
- no local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, or arbitrary local path input;
- no broad qualitative/hybrid/RAG/vector execution;
- no hidden LLM planning;
- no full mockup activation;
- no frontend-only durable authority;
- no auth/security behavior change.

## Proof Contract

This planning/control pass is valid only when:

- `184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md` and this contract exist;
- `layer3_progress_board.md`, `layer3_progress_manifest.json`, and `layer3_workbench_proof_manifest.json` record this docs/proof-only boundary;
- `tools/l3-progress-check.py` requires the freeze, the contract, the selected planning mode, the ranked future passes, and the negative invariants;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
