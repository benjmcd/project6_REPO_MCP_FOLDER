# 830 - Source Directory Hybrid Context Qualitative Analysis Package Review Submit Runtime Entry Freeze

## Current-main authority

- Predecessor current-main sync: `next_milestone_plans/Layer3_planning_docs/829_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_CURRENT_MAIN_SYNC.md`
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_context_qualitative_analysis_package_construction_sync`
- Runtime branch: `codex/l3-hybrid-analysis-package-submit`
- Current-main preflight checkpoint: `9bf057aa159618463324142b0d82686731088665`

## Selected runtime slice

Admit one bounded package-review submit decision over the already-synced source-directory hybrid context-packet qualitative-analysis package construction authority:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit`
- Schema: `layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit.v1`
- Mode: `source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_authority`
- Source gate: `830_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE`
- Required upstream authority: source-directory material snapshot, deterministic text-index authority, lexical context-packet authority, deterministic embedding/vector-index authority, deterministic vector-retrieval authority, source-directory hybrid context-packet authority, source-directory hybrid context-packet qualitative-analysis authority, source-directory hybrid package-review preview authority, and source-directory hybrid package-construction authority.

The route records one operator package-review decision against the constructed `canonical_internal`, `user_facing`, and `review_facing` package rows. It does not mutate package rows or payloads.

## Admitted behavior

- Package-review submit decision recording over source-directory hybrid context-packet qualitative-analysis package-construction authority.
- Decision values: `approved`, `changes_requested`, `rejected`, and `blocked`.
- Required notes for `changes_requested`, `rejected`, and `blocked`.
- Fail-closed hash checks for stale qualitative-analysis, package-preview, and construction authority.
- Exact package-id, package-kind, and payload-hash checks against the constructed package rows.
- Idempotent replay of the same submit authority.
- Bootstrap/readiness exposure for the exact submit route.

## Not admitted

- Handoff/export prepare.
- External export/download prepare or delivery.
- Package mutation, source package row mutation, package payload rewrite, replacement authority, or supersession commit.
- Persistent vector store.
- Durable embedding, retrieval, context-packet, or qualitative-analysis rows.
- RAG execution, prompt/model/provider runtime, or qualitative generation runtime.
- Connector dispatch, credentials, destination writes, or network egress.
- Provider-public or signed URL delivery/use.
- New source family expansion.
- Frontend durable authority or rendered controls.
- Raw local path or raw vector exposure.

## Proof requirements

- Compile changed API, service, package-entry, contract, and targeted tests.
- Prove package-review submit records bounded authority over exactly the constructed three package rows.
- Prove submit authority includes `hybrid_context_packet_hash` and `embedding_index_authority_hash`.
- Prove stale construction authority fails closed without package-review submit state.
- Prove duplicate same-authority submit is idempotent and conflicting decision fails closed.
- Prove handoff/export, external export/download, connector, provider, network, frontend, package mutation, and package payload rewrite remain disabled.
- Re-run source-directory vector/hybrid retrieval tests plus bootstrap/readiness tests.
- Re-run `tools/l3-progress-check.py` and `tools/l3-target-selection-validate.py --expect frozen`.

## Validation

Branch-local validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_hybrid_analysis.py .\backend\app\services\layer3_package_entry.py .\backend\app\api\layer3.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_package_commit_writes_bounded_packages .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_records_bounded_authority .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_rejects_stale_construction -q` - `PASS`, `3 passed`, `3 warnings`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q` - `PASS`, `13 passed`, `3 warnings`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null; python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

## Next posture

After merge, perform current-main proof/control sync for `source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_runtime`.

Do not broaden this slice into handoff/export, external export/download, provider/model runtime, persistent vector stores, RAG execution, package mutation, connector dispatch, frontend controls, or new source-family expansion without a separate freeze.
