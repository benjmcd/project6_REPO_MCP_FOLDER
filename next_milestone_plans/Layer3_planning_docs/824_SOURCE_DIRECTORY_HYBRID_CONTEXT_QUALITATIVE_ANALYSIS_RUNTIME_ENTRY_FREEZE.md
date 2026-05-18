# 824 - Source Directory Hybrid Context Qualitative Analysis Runtime Entry Freeze

## Current-main authority

- Predecessor current-main sync: `next_milestone_plans/Layer3_planning_docs/823_SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_RUNTIME_CURRENT_MAIN_SYNC.md`
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_context_packet_sync`
- Runtime branch: `codex/l3-hybrid-context-analysis`
- Current-main preflight checkpoint: `8a8156292c2b8e6c0e8726859aa60cf4ea053d3b`

## Selected runtime slice

Admit one downstream qualitative-analysis reader over the already-synced hybrid context-packet authority:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis`
- Schema: `layer3.source_directory_hybrid_context_packet_qualitative_analysis.v1`
- Mode: `source_directory_hybrid_context_packet_qualitative_analysis_authority`
- Source gate: `824_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_RUNTIME_ENTRY_FREEZE`
- Required upstream authority: existing source-directory material snapshot, deterministic text-index authority, lexical context-packet authority, deterministic embedding/vector-index authority, deterministic vector-retrieval authority, and source-directory hybrid context-packet authority.

The route builds a deterministic, read-only qualitative-analysis packet from the admitted hybrid context packet. It returns stable qualitative-analysis hashes, redacted excerpts, hybrid/lexical/vector authority refs, hybrid-ranked supporting segments, salient terms, coverage notes, analysis limits, row-write flags, and negative invariants.

## Admitted behavior

- Read-only qualitative-analysis reader over source-directory hybrid context-packet authority.
- Deterministic replay of `qualitative_analysis_hash`.
- Request fail-closed on stale text-index or embedding/vector-index authority through the hybrid context authority chain.
- Bootstrap/readiness exposure for the exact route.

## Not admitted

- Package construction, package-review submit, handoff/export prepare, or external export/download.
- Persistent vector store.
- Durable embedding, retrieval, context-packet, qualitative-analysis, or analysis-run rows.
- RAG execution, prompt/model/provider runtime, or qualitative generation runtime.
- Package mutation, package payload writes, or package payload rewrites.
- Connector dispatch, credentials, destination writes, or network egress.
- Provider-public or signed URL delivery/use.
- New source family expansion.
- Frontend durable authority or rendered controls.
- Raw local path or raw vector exposure.

## Proof requirements

- Compile changed API, service, contract, and targeted tests.
- Prove deterministic replay of `qualitative_analysis_hash`.
- Prove the API output validates and references hybrid context-packet authority.
- Prove response segments are hybrid-ranked and do not expose full text, raw vectors, normalized features, or raw paths.
- Prove stale embedding/vector-index authority fails closed.
- Prove package, analysis-run, connector, and downstream rows are not written.
- Re-run source-directory vector/hybrid retrieval tests plus bootstrap/readiness tests.
- Re-run `tools/l3-progress-check.py` and `tools/l3-target-selection-validate.py --expect frozen`.

## Validation

Branch-local validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_hybrid_analysis.py .\backend\app\api\layer3.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_uses_hybrid_authority -q` - `PASS`, `1 passed`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q` - `PASS`, `9 passed`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null; python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warning only.

## Next posture

After merge, perform current-main proof/control sync for `source_directory_hybrid_context_packet_qualitative_analysis_runtime`.

Do not broaden this slice into package construction, package-review submit, handoff/export, provider/model runtime, persistent vector stores, RAG execution, package mutation, connector dispatch, frontend controls, or new source-family expansion without a separate freeze.
