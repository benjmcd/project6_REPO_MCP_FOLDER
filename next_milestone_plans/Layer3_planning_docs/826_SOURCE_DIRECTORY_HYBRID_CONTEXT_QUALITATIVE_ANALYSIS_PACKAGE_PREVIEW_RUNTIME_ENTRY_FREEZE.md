# 826 - Source Directory Hybrid Context Qualitative Analysis Package Preview Runtime Entry Freeze

## Current-main authority

- Predecessor current-main sync: `next_milestone_plans/Layer3_planning_docs/825_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_RUNTIME_CURRENT_MAIN_SYNC.md`
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_context_qualitative_analysis_sync`
- Runtime branch: `codex/l3-hybrid-analysis-package-preview`
- Current-main preflight checkpoint: `74043b60a32c7fff23bdafba21936d00058536bc`

## Selected runtime slice

Admit one read-only package-review preview reader inside the already-synced source-directory hybrid context-packet qualitative-analysis response:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis`
- Preview schema: `layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview.v1`
- Preview mode: `read_only_source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview`
- Source gate: `826_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE`
- Required upstream authority: existing source-directory material snapshot, deterministic text-index authority, lexical context-packet authority, deterministic embedding/vector-index authority, deterministic vector-retrieval authority, source-directory hybrid context-packet authority, and source-directory hybrid context-packet qualitative-analysis authority.

The slice exposes candidate package kinds and a deterministic package-review preview hash over the hybrid qualitative-analysis authority. It does not write package rows or payloads.

## Admitted behavior

- Read-only package-review preview over source-directory hybrid context-packet qualitative-analysis authority.
- Deterministic replay of `source_directory_hybrid_package_review_preview_hash`.
- Candidate package-kind exposure for `canonical_internal`, `user_facing`, and `review_facing`.
- Bootstrap/readiness exposure for the exact embedded preview boundary.

## Not admitted

- Package construction commit or output-package row writes.
- Package-review submit.
- Handoff/export prepare.
- External export/download prepare or delivery.
- Persistent vector store.
- Durable embedding, retrieval, context-packet, qualitative-analysis, or package rows.
- RAG execution, prompt/model/provider runtime, or qualitative generation runtime.
- Package mutation, package payload rewrite, or source package row mutation.
- Connector dispatch, credentials, destination writes, or network egress.
- Provider-public or signed URL delivery/use.
- New source family expansion.
- Frontend durable authority or rendered controls.
- Raw local path or raw vector exposure.

## Proof requirements

- Compile changed API, service, contract, and targeted tests.
- Prove deterministic replay of `source_directory_hybrid_package_review_preview_hash`.
- Prove the preview source authority references the hybrid context packet, embedding/vector authority, and qualitative-analysis hash.
- Prove candidate package kinds are exposed in stable order.
- Prove package commit, package-review submit, handoff/export, external export/download, connector, provider, network, and frontend flags remain disabled.
- Prove package rows and package payloads are not written.
- Re-run source-directory vector/hybrid retrieval tests plus bootstrap/readiness tests.
- Re-run `tools/l3-progress-check.py` and `tools/l3-target-selection-validate.py --expect frozen`.

## Validation

Branch-local validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_hybrid_analysis.py .\backend\app\api\layer3.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_uses_hybrid_authority -q` - `PASS`, `1 passed`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q` - `PASS`, `9 passed`.

## Next posture

After merge, perform current-main proof/control sync for `source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_runtime`.

Do not broaden this slice into package construction commit, package-review submit, handoff/export, provider/model runtime, persistent vector stores, RAG execution, package mutation, connector dispatch, frontend controls, or new source-family expansion without a separate freeze.
