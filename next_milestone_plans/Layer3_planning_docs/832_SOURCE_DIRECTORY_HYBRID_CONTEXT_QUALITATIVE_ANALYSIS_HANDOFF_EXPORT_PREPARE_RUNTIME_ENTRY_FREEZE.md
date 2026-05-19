# 832 - Source Directory Hybrid Context Qualitative Analysis Handoff Export Prepare Runtime Entry Freeze

## Current-main authority

- Predecessor current-main sync: `next_milestone_plans/Layer3_planning_docs/831_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_CURRENT_MAIN_SYNC.md`
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_context_qualitative_analysis_package_review_submit_sync`
- Runtime branch: `codex/l3-hybrid-analysis-handoff-export-prepare`
- Current-main preflight checkpoint: `7199cfc404eb9c1cdaf414fc5eb67253c07d6d39`

## Selected runtime slice

Admit one bounded handoff/export prepare decision over the already-synced source-directory hybrid context-packet qualitative-analysis approved package-review submit authority:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare`
- Schema: `layer3.source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare.v1`
- Mode: `source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_authority`
- Source gate: `832_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE`
- Required upstream authority: source-directory material snapshot, deterministic text-index authority, lexical context-packet authority, deterministic embedding/vector-index authority, deterministic vector-retrieval authority, source-directory hybrid context-packet authority, source-directory hybrid context-packet qualitative-analysis authority, source-directory hybrid package-review preview authority, source-directory hybrid package-construction authority, and approved source-directory hybrid package-review submit authority.

The route records one prepare-only internal export envelope over exactly the constructed `canonical_internal`, `user_facing`, and `review_facing` package rows. It does not mutate package rows or payloads.

## Admitted behavior

- Handoff/export prepare decision recording after approved source-directory hybrid package-review submit.
- Decision values: `authorize_prepare`, `hold`, `decline`, and `blocked`.
- Required notes for `hold`, `decline`, and `blocked`.
- Target/mode fixed to `internal_export_envelope` and `prepare_only`.
- Fail-closed hash checks for stale qualitative-analysis, package-preview, construction, hybrid-context, and embedding-index authority.
- Exact package-id, package-kind, payload-hash, and package-review-submit record checks.
- Idempotent replay of the same prepare authority.
- Bootstrap/readiness exposure for the exact prepare route.

## Not admitted

- External export/download prepare or delivery.
- APS handoff dispatch.
- Package mutation, source package row mutation, package payload rewrite, replacement authority, or supersession commit.
- Persistent vector store.
- Durable embedding, retrieval, context-packet, or qualitative-analysis rows.
- RAG execution, prompt/model/provider runtime, or qualitative generation runtime.
- Connector dispatch, credentials, destination writes, or network egress.
- Provider-public, provider-private signed URL, or raw URL delivery/use.
- New source family expansion.
- Frontend durable authority or rendered controls.
- Raw local path or raw vector exposure.

## Proof requirements

- Compile changed API, service, contract, and targeted tests.
- Prove approved source-directory hybrid package-review submit exposes the bounded handoff/export prepare next action.
- Prove handoff/export prepare records bounded authority over exactly the constructed three package rows.
- Prove prepare authority includes `hybrid_context_packet_hash` and `embedding_index_authority_hash`.
- Prove non-approved package-review submit fails closed without handoff/export prepare state.
- Prove duplicate same-authority prepare is idempotent and conflicting decision fails closed.
- Prove external export/download, provider URLs, connector, network, frontend, package mutation, and package payload rewrite remain disabled.
- Re-run source-directory vector/hybrid retrieval tests plus bootstrap/readiness tests.
- Re-run `tools/l3-progress-check.py` and `tools/l3-target-selection-validate.py --expect frozen`.

## Validation

Branch-local validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_hybrid_analysis.py .\backend\app\api\layer3.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_records_bounded_authority .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_records_bounded_authority .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_requires_approved_submit -q` - `PASS`, `3 passed`, `3 warnings`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q` - `PASS`, `15 passed`, `3 warnings`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null; python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

## Next posture

After merge, perform current-main proof/control sync for `source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_runtime`.

Do not broaden this slice into external export/download, APS dispatch, provider/model runtime, persistent vector stores, RAG execution, package mutation, connector dispatch, frontend controls, provider URLs, or new source-family expansion without a separate freeze.
