# Source Directory Hybrid Context Packet Runtime Entry Freeze

## Current-main authority

- Predecessor current-main sync: `next_milestone_plans/Layer3_planning_docs/821_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_CURRENT_MAIN_SYNC.md`
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_package_supersession_preview_sync`
- Runtime branch: `codex/l3-source-directory-hybrid-context`
- Current-main preflight checkpoint: `5277f521f0e80245704c38bb1e8ec05e6e5f3539`

## Selected runtime slice

Admit one downstream retrieval/qualitative-hybrid substrate:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet`
- Schema: `layer3.source_directory_hybrid_retrieval_context_packet.v1`
- Mode: `source_directory_hybrid_retrieval_context_packet_authority`
- Source gate: `822_SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_RUNTIME_ENTRY_FREEZE`
- Required upstream authority: existing source-directory material snapshot, deterministic text-index authority, lexical context-packet authority, deterministic embedding/vector-index authority, and deterministic vector-retrieval authority.

The route fuses existing lexical context-packet results with deterministic local hash-vector retrieval results into one redacted hybrid context packet. It returns stable hybrid context hashes, lexical/vector authority hashes, segment identifiers, excerpts, ranks, vector scores, and negative invariants.

## Admitted behavior

- Read-only hybrid retrieval context packet.
- Deterministic fusion of existing lexical context-packet and vector-retrieval authority.
- Stable `hybrid_context_packet_hash`.
- Request fail-closed on stale text-index or embedding/vector-index authority.
- Bootstrap/readiness exposure for the exact route.

## Not admitted

- Persistent vector store.
- Durable embedding or retrieval rows.
- RAG execution, prompt/model/provider runtime, or qualitative generation runtime.
- Package construction, package mutation, package payload writes, or package payload rewrites.
- Connector dispatch, credentials, destination writes, or network egress.
- Provider-public or signed URL delivery/use.
- New source family expansion.
- Frontend durable authority or rendered controls.
- Raw local path or raw vector exposure.

## Proof requirements

- Compile changed API, service, contract, and targeted tests.
- Prove deterministic replay of `hybrid_context_packet_hash`.
- Prove API output fuses lexical and vector authority without full text, raw vectors, normalized features, or raw paths.
- Prove stale embedding/vector-index authority fails closed.
- Prove no analysis, package, connector, or retrieval rows are written.
- Re-run source-directory vector retrieval tests plus bootstrap/readiness tests.
- Re-run `tools/l3-progress-check.py` and `tools/l3-target-selection-validate.py --expect frozen`.

## Next posture

After merge and current-main sync, select the next named Layer 3 end-to-end gap. Do not broaden this slice into provider/model runtime, persistent vector stores, RAG execution, package mutation, connector dispatch, frontend controls, or new source-family expansion without a separate freeze.
