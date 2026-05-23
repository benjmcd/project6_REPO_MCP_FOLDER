# 975 - Candidate B Full-Corpus Runtime Downstream Proof

## Purpose

Record the first bounded downstream proof for the real Candidate B 69-PDF full-corpus runtime bridge receipt created by `974-cb-full-corpus-runtime-bridge.md`.

This pass proves the existing full-corpus bridge receipt can move from a server-owned curated source-directory material root into Layer 3 material preview, Gate B, qualitative analysis, package/review, handoff/export, same-origin delivery, provider-private redacted lifecycle, internal webhook dispatch/status, visual-lane status, runtime downstream proof, and operator-visible session/status surfaces.

```yaml
milestone: candidate_b_full_corpus_runtime_downstream_e2e_proof_v1
current_main: 72efcd498fe1468fee27e140fd714a5dd6d7f23d
admitted_by: 973-cb-full-corpus-runtime-bridge-freeze.md
bridge_runtime_checkpoint: 974-cb-full-corpus-runtime-bridge.md
bridge_mode: candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
implementation_status: implemented_branch_local
real_bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
real_downstream_proof_id: cb-runtime-downstream-proof-1a8c44a841830707c2168578
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
full_corpus_target_count: 69
source_directory_eligible_file_count: 71
material_file_proven: text/target-00001.md
qualitative_analysis_status: available
external_export_download_status: prepared
same_origin_delivery_available: true
provider_private_state: provider_private_signed_url_prepared
provider_private_revoke_state: provider_private_signed_url_revoked
internal_webhook_state: source_directory_internal_webhook_dispatched
visual_lane_status: available
downstream_proof_status: proven
coverage_count: 17
raw_local_path_exposed: false
provider_public_url_enabled: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
candidate_b_default_promotion_enabled: false
```

## Authority Inputs

- Current main `72efcd498fe1468fee27e140fd714a5dd6d7f23d`.
- Candidate B full-corpus runtime bridge receipt `cb-runtime-l3-0110fe894c68d6a0291f9979`.
- `backend/app/services/layer3_candidate_b_runtime_bridge.py`.
- `backend/app/services/layer3_candidate_b_visual_lane_status.py`.
- `backend/app/services/layer3_candidate_b_downstream_proof.py`.
- `backend/tests/test_layer3_candidate_b_runtime_bridge.py`.

## Implemented Behavior

The Candidate B visual-lane status surface now admits the same bounded runtime bridge modes as the downstream proof surface:

- `candidate_b_runtime_source_to_layer3_material_authority_v1`;
- `candidate_b_full_corpus_runtime_to_layer3_material_authority_v1`.

It still validates receipt hashes, Candidate B engine and visual-lane identity, retained visual/page evidence counts, material-payload invariants, and redacted operator projection. The full-corpus bridge mode is admitted as the same Candidate B runtime source kind; it does not change baseline default behavior, Candidate A semantics, or default promotion state.

The focused full-corpus test now carries the 69-target full-corpus bridge through:

- source-directory scan over 71 admitted curated files;
- material preview and Gate B over `text/target-00001.md`;
- text/vector index construction for the admitted material snapshot;
- qualitative analysis;
- package commit and package review submit;
- handoff/export prepare;
- external export download prepare;
- same-origin delivery status and delivery;
- provider-private prepare, status, use, and revoke;
- internal webhook dispatch and status;
- qualitative-analysis status projection;
- session projection;
- Candidate B visual-lane status;
- Candidate B runtime downstream proof with all 17 required coverage steps.

## Real Receipt Proof

Executed against the real same-checkout bridge receipt and curated root:

```json
{
  "bridge_receipt_id": "cb-runtime-l3-0110fe894c68d6a0291f9979",
  "candidate_b_default_promotion_enabled": false,
  "candidate_b_run_id": "f644b3f6-a7a9-4889-84d9-d842f5d12e79",
  "connector_dispatch_enabled": false,
  "coverage_count": 17,
  "downstream_proof_id": "cb-runtime-downstream-proof-1a8c44a841830707c2168578",
  "downstream_proof_status": "proven",
  "eligible_file_count": 71,
  "external_export_download_status": "prepared",
  "internal_webhook_state": "source_directory_internal_webhook_dispatched",
  "material_file": "text/target-00001.md",
  "provider_object_writes_enabled": false,
  "provider_private_revoke_state": "provider_private_signed_url_revoked",
  "provider_private_state": "provider_private_signed_url_prepared",
  "provider_public_url_enabled": false,
  "qualitative_analysis_status": "available",
  "raw_local_path_exposed": false,
  "same_origin_delivery_available": true,
  "visual_lane_status": "available"
}
```

## Remaining Work

The next exact posture is:

```text
candidate_b_full_corpus_operator_runbook_checkpoint_v1
```

That next pass should turn the proven command/test workflow into the smallest operator-repeatable checkpoint/runbook: exact commands, required runtime roots, required run ids, expected receipts, validation checks, and rollback/fail-closed handling. Do not add new bridge variants unless this runbook pass exposes a concrete blocker.

## Negative Invariants

- Baseline rollback remains explicit and fail-closed.
- Candidate A semantics are unchanged.
- Candidate B remains bounded to eligible/effective PDFs.
- Candidate B default promotion is not enabled by this proof.
- Full-corpus bridge mode is not treated as a visual-lane selector.
- PDFs, annotated PDFs, extracted images, runtime DB rows, and runtime storage blobs remain governed retained evidence/product artifacts, not text-material payloads.
- The proof does not add broad runtime DB/storage ingestion, arbitrary source expansion, RAG/vector/model runtime, provider object writes, arbitrary connector dispatch, auth/security changes, browser-storage authority, frontend-only durable authority, or full mockup activation.
- Rendered/operator responses do not expose raw local paths, raw URLs, provider keys, local roots, or unredacted artifact refs.
