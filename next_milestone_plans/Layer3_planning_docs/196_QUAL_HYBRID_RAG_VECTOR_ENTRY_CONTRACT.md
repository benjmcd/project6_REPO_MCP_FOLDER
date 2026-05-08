# Qualitative Hybrid RAG Vector Entry Contract

Status: planning/control contract paired with `195_QUAL_HYBRID_RAG_VECTOR_ENTRY_FREEZE.md`.

This contract defines requirements for moving beyond the deferred `qual_hybrid_rag_vector_entry_freeze` decision. It admits no broad qualitative execution, qualitative associated-cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector retrieval, vector index creation, embedding generation, retrieval-augmented planning, hidden LLM planning, prompt/model/provider runtime, output taxonomy expansion, route, DTO, service behavior, model, migration, test behavior, rendered UI control, source expansion, package mutation, provider/public URL runtime, connector/destination dispatch, full mockup activation, frontend-only durable authority, or auth/security behavior change.

Docs `119` and `124` remain authority for the exact single APS-document qualitative pass. Docs `138` through `152` remain authority for the already-live bounded qualitative APS backend/API and rendered downstream chain. Docs `184` through `194` remain the broader downstream/source governance chain. This contract is the narrower post-PR #752 entry-decision layer for any expansion beyond the current qualitative APS chain.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior;
2. `backend/app/services/layer3_qual_aps_execution.py` and `backend/tests/test_layer3_qual_aps_execution.py`;
3. `backend/app/services/layer3_workbench.py`, `backend/tests/test_layer3_bounded_e2e.py`, and qualitative APS route behavior;
4. rendered workbench sources and Playwright proofs only for current rendered qualitative APS existing controls;
5. docs `119`, `124`, and `138` through `152`;
6. post-signed-reference, downstream, package, and source docs `184` through `194`;
7. this contract and `195_QUAL_HYBRID_RAG_VECTOR_ENTRY_FREEZE.md`.

Planning prose, browser state, mockup screenshots, copied prompts, model output, vector index state, local fixture state, connector history, package text, or prior PR titles are not sufficient authority for runtime implementation.

## Entry Decision Contract

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_single_aps_doc_qualitative_status: single_aps_doc_qualitative_pass_only
live_qual_aps_downstream_status: bounded_qual_aps_backend_api_downstream_chain
live_rendered_qual_aps_status: qual_aps_rendered_downstream_existing_controls_only
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed: selected expansion mode, selected source scope, execution authority, retrieval corpus if any, vector storage boundary if any, embedding/model/prompt authority if any, idempotency/concurrency/failure policy, output taxonomy, package compatibility, downstream delivery semantics, leakage policy, no-cross-mode privilege escalation proof, test architecture, and theme/headed/headless proof if rendered controls are admitted.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `single_aps_doc_qualitative_current_chain_extension`;
- `qualitative_associated_cohort_execution`;
- `comparative_qualitative_execution`;
- `cross_document_synthesis`;
- `hybrid_quantitative_qualitative_execution`;
- `rag_vector_retrieval`;
- `retrieval_augmented_qualitative_pass`;
- `qualitative_output_taxonomy_expansion`.

The selected mode must not rename broad qualitative, hybrid, RAG/vector, prompt/model/provider, source expansion, or package mutation behavior as an existing single APS-document qualitative pass.

## Request Contract For Later Runtime

A future request must be server-authority based. It may include or derive server-side selected mode, source/session/plan/pass ids, material or output refs, retrieval corpus refs, vector index refs, model profile refs, deterministic hashes, idempotency key, and operator confirmation only if the future freeze admits those fields.

The request must not accept arbitrary prompt text, hidden LLM instructions, model credentials, provider keys, embedding vectors, vector-index write instructions, raw source bytes, arbitrary local paths, directory paths, external URLs to fetch, connector credentials, provider URLs, destination URLs, package mutation fields, auth/security overrides, or full mockup activation fields unless a later freeze explicitly admits one narrow server-authoritative mode.

## Response Contract For Later Runtime

A future response may expose only response-safe metadata admitted by the later freeze: selected mode, source/session/plan/pass ids, output refs/hashes/sizes, retrieval refs, vector index refs, model profile refs, provenance/audit refs, idempotency status, failure code, response-safe failure reason, and next actions.

The response must not expose prompt text, model credentials, provider keys, embedding vectors, raw vector contents, local filesystem paths, bearer tokens, raw provider URLs, connector targets, destination targets, package payload bodies, hidden LLM state, auth internals, or new source/material/result fields unless a later compatibility freeze admits it.

## Existing Runtime Compatibility Contract

This entry freeze must preserve existing qualitative APS runtimes:

- `single_aps_doc_qualitative_pass` remains the only admitted qualitative execution mode;
- `qual_aps_package_review_preview_only`, `qual_aps_package_construction_commit_entry`, `qual_aps_package_review_submit_entry`, `qual_aps_handoff_export_prepare_entry`, `qual_aps_aps_handoff_dispatch_entry`, and `qual_aps_external_export_download_prepare_deliver` remain bounded to the exact APS content-document qualitative authority chain;
- `qual_aps_rendered_downstream_existing_controls_only` remains bounded to existing rendered controls and server-authoritative state;
- no qualitative APS endpoint may become broad qualitative, hybrid, RAG/vector, prompt/model/provider, source-expansion, package-mutation, provider/public URL, connector/destination, mockup, or auth/security authority.

## Browser And UI Contract

This entry freeze adds no rendered UI control. If a later freeze admits rendered qualitative, hybrid, or RAG/vector controls, it must preserve `light`, `dark`, and `workbench` theme behavior, prove headed and headless Chromium consistency, expose no prompt/model/provider/local path/credential authority in the browser, and avoid browser-state-only execution authority.

## Test Contract For Later Runtime

Runtime or rendered implementation remains blocked until a later freeze names tests for disabled-by-default behavior, exact server authority binding, forbidden prompt/model/provider/vector/source/package/connector/provider/mockup/auth fields, retrieval corpus confinement, vector index isolation, missing/stale source/result/package authority, idempotency and concurrency, no unintended Layer 3 flow/package/provider/connector/destination side effects, no frontend-only durable authority, no prompt/model credential/vector/path/token leakage, and headed/headless plus theme coverage if UI changes are admitted.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only: docs `195` and `196` exist and are referenced; entry decision is `deferred`; selected mode is null; runtime status is `not_implemented`; the current single APS-document qualitative pass and qualitative APS downstream chain are acknowledged without being generalized; evidence ledger exists and unverified broad qualitative, qualitative cohort, comparative/cross-document, hybrid, RAG/vector, embedding/vector storage, model/prompt/provider, output taxonomy, and theme authority force deferral; exposure model exists and unknown values force deferral; capability isolation matrix exists and all new runtime flags remain false; negative invariants are present; docs do not claim broad qualitative/hybrid/RAG/vector runtime is live; docs do not conflate the existing qualitative APS downstream chain with broad qualitative, hybrid, RAG/vector, hidden LLM, source expansion, provider/public URL, connector/destination, or package mutation behavior.

The checker must not pretend to validate actual broad qualitative execution, cross-document synthesis, vector stores, embedding models, LLM providers, prompt safety, retrieval quality, source-family semantics, auth/security posture, or operator usability in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to implement more than one qualitative/hybrid/RAG/vector mode, widen qualitative execution beyond the exact APS content-document chain without a selected mode freeze, accept arbitrary prompt/model/provider/vector/local path fields from a request, fetch external URLs or connectors, build vector indexes, expose embeddings, mutate packages, generate provider/public URLs, dispatch connectors/destinations, activate target-state mockups as durable authority, or alter auth/security behavior without a later freeze that explicitly admits that scope.
