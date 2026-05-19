# 847 - NRC RAG Sublayer 3C Optional Tool ADR

## Status

Status: evaluation-only ADR for `nrc_rag_sublayer3c_optional_tool_adr`.

Doc: `847_NRC_RAG_SUBLAYER3C_OPTIONAL_TOOL_ADR.md`.

Branch: `codex/l3-nrc-rag-optional-tool-adr`.

Current-main preflight checkpoint: `1405234f6d44634b059b33a63787948b1e7fecb3`.

Selected from posture: `select_nrc_rag_sublayer3c_optional_tool_adr_or_tabpfn_static_benchmark_plan`.

Decision: `evaluate_nrc_rag_static_benchmark_planning_only`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this ADR: `false`.

## Decision

Evaluate nrc-licensing-rag only as a candidate for future static benchmark planning over already-authorized Layer 3 source-directory, vector, hybrid-context, and qualitative-analysis surfaces.

This ADR does not adopt nrc-licensing-rag as a runtime provider, default dependency, retrieval endpoint, source authority, vector store, rendered control, package/handoff/export/download participant, agent tool, or production feature.

The candidate remains blocked at runtime until a later current-main freeze proves all of the following:

- an exact current-main Sublayer 3C regulatory-context use-site where nrc-licensing-rag could provide measurable marginal value over project6-native source-directory/vector/hybrid surfaces;
- fixed benchmark query-set authority;
- source and license authority compatible with project6 use;
- dependency isolation that keeps the base repo working without nrc-licensing-rag, Chroma, OpenAI, or external embeddings installed;
- no hidden embedding call, no hidden vector-store startup, no hidden provider credential, and no hidden model call;
- fail-closed readiness behavior; and
- explicit rollback and no-adopt stop rules.

## Canonical Source Of Truth

Live source, tests, manifests, current-main review/check state, and repo-native validation remain authority.

The governing Layer 3 planning/control chain is:

- `844_PUBLIC_URL_DELIVERY_SUBLAYER3C_PREREQUISITE_CLOSEOUT.md`;
- `845_SUBLAYER3C_OPTIONAL_TOOL_PLANNING_INDEX_ADR_GATE.md`;
- `846_TABPFN_SUBLAYER3C_OPTIONAL_PREDICTIVE_METHOD_ADR.md`;
- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_nrc_rag_sublayer3c_tool_planning_pack`;
- `backend/app/services/layer3_source_directory_ingestion.py`;
- `backend/app/services/layer3_source_directory_text_retrieval.py`;
- `backend/app/services/layer3_source_directory_vector_retrieval.py`;
- `backend/app/services/layer3_source_directory_hybrid_context.py`;
- `backend/app/services/layer3_source_directory_hybrid_analysis.py`; and
- the corresponding source-directory tests.

The accepted NRC RAG planning pack remains planning context only. It does not authorize runtime RAG/vector behavior, new provider dependencies, source-authority promotion, package/handoff integration, quantitative method-selection changes, rendered retrieval controls, new retrieval endpoints, or agent tool-call runtime.

## Current External NRC RAG Checkpoint

Current external nrc-licensing-rag-adjacent guidance was rechecked on 2026-05-19 from:

- `https://huggingface.co/datasets/davenporten/nrc-regulatory-embeddings`;
- `https://github.com/chroma-core/chroma`.

The public Hugging Face dataset is built for the nrc-licensing-rag project and contains chunked NRC regulatory documents with OpenAI `text-embedding-3-small` embeddings, Chroma loading examples, and an MIT dataset license statement. That makes it useful as planning context for benchmark design, but it also confirms that runtime use would imply external embeddings, vector-store loading, corpus/source-authority decisions, and dependency/provider questions that current main has not admitted.

Chroma remains an external vector database dependency and is not part of current project6 default runtime for this ADR.

## Current Project6 Baseline Candidates

The only current-main comparison surfaces for future NRC RAG evaluation are existing bounded source-directory surfaces:

- `source_directory_material_preview`;
- `source_directory_vector_retrieval`;
- `source_directory_hybrid_context_packet`;
- `source_directory_qualitative_hybrid_analysis`;
- `source_directory_hybrid_context_packet_qualitative_analysis`; and
- same-origin package/handoff/export/download surfaces only as existing project6 outputs, not as nrc-licensing-rag integration points.

No provider-public URL, provider-private URL, connector, external vector store, OpenAI/Claude provider, Chroma runtime, package mutation, handoff/export/download rewrite, signed-reference, rendered retrieval control, or quantitative method-selection flow is an NRC RAG use-site under this ADR.

## Evaluation Plan

A later evaluation-planning PR may define benchmark fixtures only if it remains no-runtime and no-dependency by default.

The benchmark plan must compare nrc-licensing-rag against project6-native baselines for the exact selected regulatory-context use-site:

- fixed query set with expected source-grounding criteria;
- current source-directory lexical retrieval;
- current source-directory vector retrieval;
- current source-directory hybrid context packet;
- current qualitative hybrid analysis output;
- citation/source-span quality rubric;
- refusal or no-answer behavior when the corpus lacks support; and
- no acceptance based on demo output, hidden model behavior, or one-off manual retrieval.

Any benchmark plan must include no-adopt thresholds. If nrc-licensing-rag cannot provide measurable marginal value over project6-native source-directory/vector/hybrid surfaces, or if license/provider/corpus constraints are incompatible with project6 use, the correct result is `no_adopt_nrc_rag_for_sublayer3c_optional_tool_use`.

## Non-Admission Boundary

This ADR admits no runtime behavior, backend route, API DTO, response model, database model, migration, dependency, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, embedding call, vector-store startup, corpus download, Chroma runtime, OpenAI/Claude/provider runtime, or auth/security behavior change.

This ADR specifically admits no NRC RAG runtime, no nrc-licensing-rag dependency, no Chroma/vector provider runtime, no OpenAI embedding provider, no OpenAI/Claude generation provider, no external embeddings dataset load, no new Layer 3 retrieval endpoint, no rendered retrieval controls, no source-authority promotion, no quantitative method-selection influence, no package/handoff/export/download use, and no agent tool-call runtime.

## Validation Basis

Required validation for this ADR:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime test is required for this ADR because no runtime behavior, route, dependency, or UI behavior is changed.

## Next Posture

The next exact posture is `select_sublayer3c_optional_tool_static_benchmark_plan_or_stop_for_product_authority`.

A benchmark-planning PR for TabPFN or NRC RAG remains optional and must stay no-runtime until a later freeze explicitly admits readiness or runtime behavior.
