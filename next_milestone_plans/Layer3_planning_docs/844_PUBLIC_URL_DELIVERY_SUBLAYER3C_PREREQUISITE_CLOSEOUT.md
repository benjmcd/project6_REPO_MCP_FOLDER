# 844 - Public URL Delivery Sublayer 3C Prerequisite Closeout

## Status

Status: planning/control closeout and next-lane selection for `public_url_delivery_sublayer3c_prerequisite_closeout`.

Doc: `844_PUBLIC_URL_DELIVERY_SUBLAYER3C_PREREQUISITE_CLOSEOUT.md`.

Branch: `codex/l3-public-url-sublayer3c-prereq`.

Current-main preflight checkpoint: `d6d0b119e570e87af5d59b544df603f3425177c7`.

Selected from posture: `select_next_major_layer3_end_to_end_gap_from_current_main_evidence`.

Closeout result: `public_url_delivery_prerequisite_satisfied_for_sublayer3c_optional_tool_planning`.

Entry decision: `planning_control_closeout_and_next_lane_selection`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this closeout: `false`.

## Canonical Source Of Truth

Live source, tests, manifests, and current-main review/check state remain authority.

The current provider-public delivery/use authority is:

- `backend/app/services/layer3_provider_public_url.py`;
- `backend/app/services/layer3_provider_public_url_state.py`;
- `backend/app/services/layer3_provider_public_url_fake_provider.py`;
- `backend/app/services/layer3_provider_public_url_delivery_use.py`;
- `backend/app/api/layer3.py`;
- `backend/tests/test_layer3_provider_public_url_state.py`;
- `backend/tests/test_layer3_provider_public_url_delivery_use.py`;
- `794_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_IMPLEMENTATION_ENTRY_FREEZE.md`; and
- `795_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_CURRENT_MAIN_SYNC.md`.

The current bounded source-directory and delivery authority is:

- `839_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CURRENT_MAIN_SYNC.md`;
- `841_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_DELIVERY_CONTROL_CURRENT_MAIN_SYNC.md`;
- `843_SERVER_CONFIGURED_SOURCE_DIRECTORY_INGESTION_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`;
- `backend/app/services/layer3_source_directory_hybrid_analysis.py`;
- `backend/app/services/layer3_source_directory_ingestion.py`;
- `backend/app/review_ui/static/layer3.html`; and
- `backend/app/review_ui/static/layer3.js`.

The accepted Sublayer 3C planning packs are planning context only:

- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_tabpfn_sublayer3c_tool_planning_pack`;
- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_nrc_rag_sublayer3c_tool_planning_pack`.

They do not override current-main source, tests, progress manifests, proof manifests, review state, or repo-native validation.

## Public URL Delivery Prerequisite Decision

The amount of public URL delivery necessary before pursuing Sublayer 3C optional-tool planning is complete under current-main authority.

Current main already has a bounded fake-provider redacted provider-public delivery/use decision runtime:

- route: `POST /handoff/export/download/provider-public-url/use`;
- response schema: `layer3.provider_public_url.delivery_use.v1`;
- provider mode: `fake_provider_only_contract_runtime`;
- fixed request mode: `fake_provider_redacted_use_decision`;
- fixed operator decision: `use_provider_public_url_redacted_fake_provider`; and
- current-main sync: `current_main_synced_provider_public_delivery_use_fake_provider_redacted_runtime_implementation`.

This is sufficient as a prerequisite for Sublayer 3C optional-tool planning because the next Sublayer 3C step is an ADR/evaluation decision gate, not external delivery runtime and not optional-tool runtime.

It is not necessary or correct to implement raw provider-public URL exposure, real provider object writes, public redirects, byte streaming, public proxy behavior, provider credentials, network egress, rendered provider-public controls, or production auth/security before the Sublayer 3C planning index or ADR gate.

## Selected Next Lane

Selected next major lane: `sublayer3c_optional_tool_planning_index_adr_gate`.

Selected next posture: `select_sublayer3c_optional_tool_planning_index_or_adr_gate_after_public_url_delivery_prerequisite_closeout`.

The first valid Sublayer 3C action is a planning/ADR gate using the accepted planning packs as context:

- `ADR: evaluate or no-adopt TabPFN for Layer 3 Sublayer 3C optional predictive-method use`;
- `ADR: evaluate or no-adopt nrc-licensing-rag for Layer 3 Sublayer 3C optional-tool use`; or
- one narrow optional-tool planning index that records both ADR gates and their no-runtime boundaries.

The ADR/index must define exact Sublayer 3C use-sites, project6-native baselines, benchmark/evaluation sets, proof obligations, stop rules, dependency isolation, and current-state revalidation before any runtime or readiness work.

## Non-Admission Boundary

This closeout admits no runtime behavior, backend route, API DTO, response model, database model, migration, dependency, provider adapter, provider credential, provider object write, provider ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, public anonymous access, public redirect, byte streaming, rendered provider-public control, frontend durable authority, connector dispatch, real connector invocation, destination write, network egress, package mutation, package payload rewrite, source package row mutation, source expansion, arbitrary ingestion, semantic/vector RAG widening, prompt/model/provider runtime, hidden model call, auth/security behavior change, full mockup activation, or raw local path exposure.

This closeout also admits no TabPFN runtime, no TabPFN dependency, no TabPFN model/checkpoint loading, no NRC RAG runtime, no Chroma/vector provider integration, no OpenAI/Claude/provider runtime, no new retrieval endpoint, no rendered optional-tool controls, no agent tool-call runtime, no Gate C/pass-entry admission, no package/handoff/export/download integration for optional tools, no provider credentials, no network egress, and no hidden model calls.

If a later Sublayer 3C lane requires an external/public/credentialed surface, the provider-public/provider-private URL, connector/network, and auth/security gates must be reopened with exact product authority before implementation.

## Validation Basis

This closeout is based on current-main evidence and focused validation, not on the strategic context file alone.

Required validation for this closeout:

- `python -m pytest .\backend\tests\test_layer3_provider_public_url_delivery_use.py -q`;
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py .\backend\tests\test_layer3_provider_public_url_delivery_use.py -q`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

## Next Posture

Do not continue same-family public URL delivery proof loops unless current-main evidence names a concrete defect, failed check, unresolved review item, stale sync, missing required proof, or operator-flow blocker.

The next exact posture is `select_sublayer3c_optional_tool_planning_index_or_adr_gate_after_public_url_delivery_prerequisite_closeout`.

The next PR should be planning/control only unless current main later admits exact optional-tool readiness or runtime behavior.
