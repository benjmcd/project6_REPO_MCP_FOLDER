# 976 - Candidate B Full-Corpus Operator Runbook Checkpoint

## Purpose

Record the operator-repeatable checkpoint after the Candidate B full-corpus runtime bridge and downstream proof landed.

This pass does not add a new runtime path. It freezes the current repeatable workflow in `docs/nrc_adams/local_corpus_e2e_runbook.md` so the next operator or agent can rerun the same Candidate B full-corpus corpus-processing to Layer 3 path from current main without relying on session memory.

```yaml
milestone: candidate_b_full_corpus_operator_runbook_checkpoint_v1
current_main: b13ff594a4c0d773c6cd6d6605c67d5668d9ed35
runbook: docs/nrc_adams/local_corpus_e2e_runbook.md
bridge_runtime_checkpoint: 974-cb-full-corpus-runtime-bridge.md
downstream_proof_checkpoint: 975-cb-full-corpus-runtime-downstream-proof.md
bridge_mode: candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
proof_mode: candidate_b_visual_lane_runtime_downstream_e2e_proof_v1
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
downstream_proof_id: cb-runtime-downstream-proof-1a8c44a841830707c2168578
source_directory_eligible_file_count: 71
material_file_for_smoke: text/target-00001.md
coverage_count: 17
repeatability_smoke: py -3.12 -m pytest .\backend\tests\test_layer3_candidate_b_runtime_bridge.py::test_candidate_b_full_corpus_runtime_bridge_uses_triplet_and_reaches_gate_b -q
candidate_b_default_promotion_enabled: false
```

## Runbook Coverage

The runbook now names the repeatable sequence:

- generate or validate baseline full-corpus evidence;
- generate or validate Candidate A PageEvidence full-corpus evidence;
- generate or validate Candidate B OpenDataLoader PDF full-corpus evidence;
- validate the triplet without seeding or generating artifacts;
- prepare `candidate_b_full_corpus_runtime_to_layer3_material_authority_v1`;
- scan the 71-file curated Layer 3 source-directory root;
- preview and approve `text/target-00001.md` at Gate B;
- run qualitative analysis;
- commit and review packages;
- prepare handoff/export and external export download;
- prove same-origin delivery;
- prove provider-private prepare/status/use/revoke;
- prove internal webhook dispatch/status;
- inspect status/session projections;
- inspect Candidate B visual-lane status;
- record Candidate B runtime downstream proof with all 17 required coverage steps.

## Stop Conditions

The runbook explicitly stops on missing runtime roots, missing run ids, missing bridge receipt, missing curated root, dependency drift, or API failure. It also repeats the current rule that historical reports alone are not sufficient when live artifact roots are absent.

## Remaining Work

The next exact posture is:

```text
candidate_b_full_corpus_operator_repeatability_smoke_v1
```

That pass should rerun the runbook from clean current main and report whether it is operator-repeatable without session-only scripts or ad hoc state. If that smoke exposes a concrete gap, fix only that gap. If it passes cleanly, the next higher-level work is Candidate B default-operational acceptance: deciding whether any remaining non-PDF or mixed-corpus expansion, UI affordance, production auth/security, or full mockup activation work is separately warranted.

## Negative Invariants

- Baseline rollback remains explicit and fail-closed.
- Candidate A semantics are unchanged.
- Candidate B remains bounded to eligible/effective PDFs.
- Candidate B default promotion is not changed by this checkpoint.
- The runbook does not admit new source families, runtime DB ingestion, provider object writes, arbitrary connector dispatch, RAG/vector/model runtime, auth/security changes, browser-storage authority, frontend-only durable authority, or full mockup activation.
