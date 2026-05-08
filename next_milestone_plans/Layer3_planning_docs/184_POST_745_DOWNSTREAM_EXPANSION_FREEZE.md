# Post-745 Downstream Expansion Freeze

Status: planning/control freeze only for `post_745_raw_mixed_rendered_downstream_expansion_governance`.

This document freezes the current-main boundary after `183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md`. It does not implement a provider URL, connector dispatch, package mutation, source expansion, RAG/vector retrieval, full mockup activation, auth/security behavior, route, DTO, model, migration, service, or rendered UI control by itself.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md`
- current rendered path proven: `raw_mixed_rendered_external_export_download_signed_reference`
- current endpoint depth proven in rendered UI: same-origin external export/download signed-reference generation and single-use use
- current browser proof file: `e2e/layer3-workbench.spec.js`
- current UI runtime: `backend/app/review_ui/static/layer3.js`
- current proof checker: `tools/l3-progress-check.py`
- existing provider/public URL governance: `110_PROVIDER_URL_FREEZE.md` and `111_PROVIDER_URL_CONTRACT.md`
- existing connector/destination governance: `112_CONNECTOR_DISPATCH_FREEZE.md` and `113_CONNECTOR_DISPATCH_CONTRACT.md`
- existing package mutation governance: `122_PACKAGE_MUTATION_FREEZE.md`, `126_PACKAGE_COMMIT_FREEZE.md`, and replacement/supersession docs `127` through `131`
- existing source boundary governance: `123_SOURCE_EXPANSION_FREEZE.md`
- existing qualitative/hybrid/RAG governance: `124_QUAL_HYBRID_RAG_FREEZE.md`
- existing mockup governance: `125_MOCKUP_TRUTH_STATE_FREEZE.md`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Decision

The next admissible work after PR #745 is not broad downstream implementation. The selected next planning state is exactly:

`post_745_raw_mixed_rendered_downstream_expansion_governance`

This state exists to prevent over-claiming from the signed-reference proof. PR #745 proves that the rendered raw mixed workbench can use existing same-origin signed-reference controls after `external_export_download_prepared` authority. It does not prove that the system is ready for provider URLs, external connector dispatch, destination writes, package reconstruction, broader source classes, RAG/vector retrieval, full mockup activation, hidden LLM planning, or auth/security changes.

## Ranked Future Passes

1. `provider_public_url_entry_freeze`
   - Goal: choose exactly one future provider/public URL mode only if same-origin attachment delivery plus same-origin durable signed references are insufficient for a concrete operator or downstream integration need.
   - Current blocker: no raw mixed rendered provider/public URL mode, provider/storage authority, TTL/revocation policy, credential/config contract, leak-control policy, or rendered control contract is frozen.
   - Why first: provider/public URL behavior is the closest conceptual extension of download/signed-reference delivery, and must be separated from connector dispatch before any shareable link behavior is admitted.

2. `connector_destination_dispatch_entry_freeze`
   - Goal: choose exactly one future connector or destination dispatch mode only if a concrete downstream integration need cannot be served by same-origin delivery or a separately admitted provider/public URL.
   - Current blocker: no connector key, destination id, lifecycle state, idempotency model, retry/cancel policy, credential boundary, or receipt/audit contract is selected for raw mixed rendered downstream dispatch.
   - Why after provider/public URL: connector dispatch should not become an accidental substitute for unresolved share-link/object-delivery semantics.

3. `package_mutation_reconstruction_rendered_entry_freeze`
   - Goal: decide whether any rendered package mutation, replacement, supersession, or reconstruction control should exist for the raw mixed path after package review and downstream proofs.
   - Current blocker: existing package mutation governance is mostly backend/API and lineage oriented; no rendered raw mixed package mutation control, mutation affordance, downstream invalidation policy, or re-delivery compatibility rule is selected.
   - Why after delivery/dispatch freezes: package mutation can invalidate package review, handoff/export, APS handoff, external export/download, signed-reference, provider URL, and connector receipts, so it must not precede downstream authority rules.

4. `source_breadth_entry_freeze`
   - Goal: decide whether source classes beyond `dataset_version` and `aps_content_document` should be admitted.
   - Current blocker: current source boundary admits only supported source classes and blocks local upload, local-directory ingestion, web connector retrieval, RAG/vector sources, and unbounded runtime DB reads.
   - Why after downstream freeze ranking: expanding source inputs before downstream authority is stable would multiply E2E fixture and artifact obligations.

5. `qual_hybrid_rag_vector_entry_freeze`
   - Goal: choose one broader qualitative, hybrid, RAG, or vector execution mode beyond the current admitted narrow qualitative APS behavior.
   - Current blocker: no raw mixed rendered RAG/vector retrieval, broad qualitative associated-cohort execution, hybrid result taxonomy, vector index lifecycle, or provenance/audit model is selected.
   - Why after source breadth: RAG/vector and hybrid execution need source-class and artifact taxonomy clarity first.

6. `browser_full_mockup_activation_freeze`
   - Goal: decide whether target-state mockups should become interactive production UI behavior.
   - Current blocker: current mockup docs remain target-state only, and no route/UI/state authority allows browser/full mockup durable behavior.
   - Why late: mockup activation can blur target-state planning with live durable authority unless all backend capability boundaries are frozen first.

7. `auth_security_entry_freeze`
   - Goal: harden authentication, authorization, tenant/session access, and operator permissions around the final admitted downstream surfaces.
   - Current blocker: current Layer 3 proofs are bounded functional and proof-harness oriented; no broad auth/security behavior change is selected.
   - Why staged: auth/security must be designed against the actual admitted surfaces, but security review is mandatory before provider/public URL or connector behavior is implemented.

## Implementation Entry Rule

No future implementation may start from this freeze alone. A future implementation must first add a more specific implementation-entry freeze that names:

- exact selected mode;
- exact owner route, service, or rendered control;
- exact DTO/schema contract;
- exact DB rows read and written;
- exact files/artifacts read and written;
- exact idempotency and concurrency behavior;
- exact provider, connector, destination, package, source, or security authority basis;
- exact headed and headless browser proof if rendered UI behavior changes;
- exact light, dark, and workbench theme obligations if the rendered workbench changes;
- exact negative side effects that must remain absent.

## Negative Invariants

This freeze admits no:

- provider/public URL generation;
- provider object-store URL, signed URL, public ACL, object-store write, or URL revocation behavior;
- connector-run creation, connector invocation, destination selection, or destination write;
- generic downstream dispatch;
- package payload mutation, reconstruction, replacement, supersession, or rendered package mutation control;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload, local-directory ingestion, arbitrary local path input, web connector retrieval, or unbounded runtime DB source read;
- RAG/vector retrieval, vector index creation, broad qualitative execution, hybrid execution, or hidden LLM planning;
- new route, DTO, model, migration, or production service behavior;
- new rendered UI control;
- frontend-only durable authority;
- full mockup activation;
- auth/security behavior change.

Future downstream work must preserve no frontend-only durable authority unless a later implementation-entry freeze explicitly admits and proves a server-authoritative replacement.

## Stop Condition

Stop and return to planning if a proposed next pass tries to implement provider URLs, connector dispatch, package mutation, source expansion, RAG/vector retrieval, full mockup activation, or auth/security behavior without a more specific implementation-entry freeze and proof plan.
