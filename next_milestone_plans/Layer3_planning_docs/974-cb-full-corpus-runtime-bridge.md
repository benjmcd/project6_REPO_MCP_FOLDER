# 974 - Candidate B Full-Corpus Runtime Bridge Runtime

## Purpose

Record the runtime implementation of `candidate_b_full_corpus_runtime_to_layer3_material_authority_v1` after the admission freeze in `973-cb-full-corpus-runtime-bridge-freeze.md`.

This pass implements the bounded full-corpus bridge and proves that the real 69-PDF Candidate B runtime triplet can produce a server-owned Layer 3 source-directory-compatible material root without using the workbench fixture target set.

```yaml
milestone: candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
current_main: b4599050419e6ceef2db3d8a6bf44e4c5111404f
admitted_by: 973-cb-full-corpus-runtime-bridge-freeze.md
bridge_mode: candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
implementation_status: implemented_branch_local
real_bridge_status: prepared
real_bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
full_corpus_target_count: 69
admitted_material_file_count: 71
admitted_text_file_count: 69
trace_file_count_in_full_corpus_curated_root: 0
normalized_json_file_count_in_full_corpus_curated_root: 0
source_directory_scan_status: 201
source_directory_eligible_file_count: 71
material_preview_status: 200
gate_b_status: 200
gate_b_session_id: a8b2e2da-0e49-44cb-8c5d-decf8e5b8350
raw_curated_root_exposed: false
full_downstream_package_delivery_status: not_executed_next_posture
```

## Authority Inputs

- Current main `b4599050419e6ceef2db3d8a6bf44e4c5111404f`.
- `973-cb-full-corpus-runtime-bridge-freeze.md`.
- `tools/validate_full_corpus_triplet.py`.
- `backend/app/services/layer3_candidate_b_runtime_bridge.py`.
- `backend/app/services/layer3_candidate_b_downstream_proof.py`.
- `backend/tests/test_layer3_candidate_b_runtime_bridge.py`.
- Real bridge receipt under the local isolated runtime root `backend/app/storage_test_runtime/lc_e2e/cb-full-corpus-l3-bridge-v1/`.

## Implemented Behavior

The runtime bridge now admits both bridge modes:

- `candidate_b_runtime_source_to_layer3_material_authority_v1` for the existing workbench fixture target set.
- `candidate_b_full_corpus_runtime_to_layer3_material_authority_v1` for the validated 69-PDF full-corpus triplet.

The full-corpus mode:

- discovers baseline, Candidate A, and Candidate B run ids through current-main runtime discovery;
- validates each summary schema, pass state, 69-PDF count, target outcomes, and validate-only gate results;
- validates `connector_run.request_config_json` from each runtime DB;
- requires explicit baseline rollback for baseline and Candidate A;
- requires Candidate A `candidate_a_page_evidence_v1`;
- requires Candidate B `candidate_b_opendataloader_pdf` plus `candidate_b_opendataloader_page_evidence_v1`;
- proves all three runs share the same ordered 69-target accession set;
- rejects target-set mismatch, missing DB/storage, stale/missing request config, failed gates, missing Candidate B visual refs, missing retained source-PDF refs, or missing normalized text authority.

## Material Subset

The implemented full-corpus curated root intentionally materializes 71 files rather than 209 files:

- `runtime-summary.json`;
- `compare-targets.json`;
- 69 `text/target-000NN.md` files.

The bridge still validates normalized text authority for every Candidate B target. It does not place per-target trace JSON or per-target normalized JSON in the source-directory material root because current source-directory ingestion is bounded to 100 files. This preserves the existing source-directory policy instead of widening it.

PDFs, annotated PDFs, extracted images, runtime DB rows, runtime storage blobs, and visual/page evidence remain governed retained Candidate B evidence/product artifacts. They are not material-text payloads in this bridge.

## Real Receipt Proof

Executed against the real same-checkout runtime receipts:

```powershell
py -3.12 - <<'PY'
# prepared bridge mode candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
PY
```

Result:

```json
{
  "admitted_file_count": 71,
  "bridge_receipt_id": "cb-runtime-l3-0110fe894c68d6a0291f9979",
  "candidate_b_run_id": "f644b3f6-a7a9-4889-84d9-d842f5d12e79",
  "compare_target_set_hash": "1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f",
  "curated_root_absolute_path_exposed": false,
  "gate_b_material_authority_compatible": true,
  "layer3_material_preview_compatible": true,
  "mode": "candidate_b_full_corpus_runtime_to_layer3_material_authority_v1",
  "normalized_file_count": 0,
  "status": "prepared",
  "target_count": 69,
  "text_file_count": 69,
  "trace_file_count": 0
}
```

## Material Preview / Gate B Proof

Executed source-directory scan, material preview, and Gate B approval against the real curated root using isolated in-memory Layer 3 state.

Result:

```json
{
  "eligible_file_count": 71,
  "gate_b_session_id": "a8b2e2da-0e49-44cb-8c5d-decf8e5b8350",
  "gate_b_status": 200,
  "preview_file": "text/target-00001.md",
  "preview_status": 200,
  "raw_curated_root_exposed": false,
  "scan_status": 201
}
```

## Focused Tests

The focused runtime bridge suite now includes:

- `test_candidate_b_full_corpus_runtime_bridge_uses_triplet_and_reaches_gate_b`;
- existing fixture/workbench bridge tests;
- existing Candidate B runtime downstream package, handoff, delivery, provider-private, and internal-webhook tests.

The full-corpus test proves:

- workbench fixture compare is not used;
- the full-corpus triplet hash is preserved;
- the curated root stays under 100 source-directory files;
- no raw runtime root is exposed;
- scan, material preview, and Gate B work over the full-corpus bridge material root.

## Remaining Work

The full-corpus bridge and Gate B material authority are now proven. The next exact posture is:

```text
candidate_b_full_corpus_runtime_downstream_e2e_proof_v1
```

That next proof should drive the full-corpus bridge receipt through the downstream package/review, handoff/export, same-origin delivery, provider-private redacted lifecycle, internal webhook, status/projection, and retained artifact-family inspection path. The existing fixture/runtime downstream proof path remains proven, but this checkpoint does not overclaim full downstream package/delivery proof for the exact 69-PDF full-corpus receipt.

## Negative Invariants

- Baseline rollback remains explicit and fail-closed.
- Candidate A semantics are unchanged.
- Candidate B remains bounded to eligible/effective PDFs.
- The full-corpus bridge does not use the fixture manifest or `compose_workbench_compare_targets`.
- The bridge does not ingest PDFs/images into text-material analysis.
- The bridge does not ingest broad runtime DB/storage as source material.
- The bridge does not add provider object writes, arbitrary connector dispatch, broad source expansion, RAG/vector/model runtime, auth/security changes, browser-storage authority, frontend-only durable authority, or full mockup activation.
- Rendered/operator responses do not expose raw local paths, raw URLs, provider keys, local roots, or unredacted artifact refs.
