# 23 GateD APS Promotion Freeze

## Purpose and authority note

This document freezes the bounded APS continuation immediately after the now-landed dedicated `validate_only_gates` runtime/report-ref boundary.
It answers one question only:
- which concrete later family should continue next beyond the landed validate-only runtime/report-ref boundary, without reopening retrieval cutover, route/UI, runtime DB, schema, or earlier APS truth

It is not:
- a validate-only implementation lane
- a retrieval-cutover implementation lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
4. `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`
5. `20_GATED_APS_REVIEW_PACKET_FREEZE.md`
6. `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`
7. `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
8. `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
9. `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
10. historical Phase 1A REV1 artifacts as context only

Current upstream merged-state note:
- current `main` now includes the bounded `aps_deterministic_challenge_review_packet_handoff` slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`
- current `main` now also includes the landed read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze from PR `#136`, the bounded generic validate-only gate-report refresh lane from PR `#138`, the landed read-only `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md` freeze from PR `#140`, and the bounded dedicated validate-only runtime/report-ref implementation slice from PR `#143`
- the live downstream graph on current `main` still ends the bounded tracked chain at `validate_only_gates`
- current `main` already contains concrete later-family surfaces for promotion governance and retrieval cutover proof, but no later post-validate-only freeze has yet landed on current `main`

Current merged-state note:
- current `main` now also includes this landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`, selecting promotion governance as the next bounded later family beyond the landed validate-only runtime/report-ref boundary
- current `main` keeps retrieval cutover later
- this landed freeze still does not admit promotion implementation changes, retrieval cutover changes, route/UI widening, runtime DB writes, or schema widening

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md|artifact|current governing freeze for the landed dedicated validate_only runtime/report-ref boundary`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph still ends the bounded tracked chain at validate_only_gates and does not define a later named post-validate-only node|38-45;67-72;87-92;108-113`; `R|backend/app/services/nrc_aps_validate_only_gates_contract.py|Current dedicated validate-only contract surface already landed on current \`main\`|1-203`; `R|backend/app/services/nrc_aps_validate_only_gates.py|Current dedicated validate-only runtime surface already landed on current \`main\`|1-508`; `R|backend/app/services/nrc_aps_validate_only_gates_gate.py|Current dedicated validate-only gate surface already landed on current \`main\`|1-264`; `R|backend/tests/test_nrc_aps_validate_only_gates.py|Current dedicated validate-only proof surface already landed on current \`main\`|1-277`; `R|backend/app/services/nrc_aps_promotion_gate.py|Current promotion governance family already exists on current \`main\`, including policy loading, governance evaluation, and validation entrypoints|14-19;174-182;518-727`; `R|tests/test_nrc_aps_promotion_gate.py|Current promotion governance proof surface already exists on current \`main\`|136-205`; `R|backend/app/services/nrc_aps_promotion_tuning.py|Current promotion policy comparison and rationale surface already exists on current \`main\`|15-22;106-205`; `R|tests/test_nrc_aps_promotion_tuning.py|Current promotion tuning proof surface already exists on current \`main\`|110-177`; `R|backend/app/services/aps_retrieval_plane_cutover_validation.py|Current retrieval cutover family is a separate parity-proof surface over retrieval materialization and canonical payload comparison|20-27;164-340`; `R|backend/tests/test_aps_retrieval_plane_cutover_validation.py|Current retrieval cutover proof surface already exists on current \`main\`|193-316`; `R|backend/tests/test_aps_retrieval_plane_cutover_gate.py|Current retrieval cutover CLI gate proof surface already exists on current \`main\`|187-196`; `R|tools/nrc_aps_retrieval_cutover_gate.py|Current retrieval cutover CLI wrapper already exists on current \`main\`|1-12`; `R|project6.ps1|Current operator entrypoints already expose validate-only, promotion, and retrieval-cutover actions, with promotion and retrieval cutover kept distinct|3-3;56-58;628-679`

## Frozen tranche

The bounded APS continuation is frozen as:
- `Gate D APS post-validate-only continuation slice = one read-only freeze selecting the first concrete later family beyond the landed dedicated validate_only runtime/report-ref boundary`
- keep the landed dedicated validate-only runtime/report-ref boundary as the immediate upstream truth for this tranche
- keep retrieval cutover later
- this freeze itself does not admit promotion implementation changes, retrieval cutover changes, route/UI widening, runtime DB writes, or schema widening
- do not invent a separate later `validate-only top-chain expansion` family unless live repo truth actually defines one

Hard rule:
- do not skip directly from the landed dedicated validate-only runtime/report-ref boundary to retrieval cutover without first settling the first concrete later family

## Canonical starting point

Read these surfaces first:

1. `Current landed validate-only boundary`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/nrc_aps_validate_only_gates_contract.py`
- `backend/app/services/nrc_aps_validate_only_gates.py`
- `backend/app/services/nrc_aps_validate_only_gates_gate.py`
- `backend/tests/test_nrc_aps_validate_only_gates.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `project6.ps1`

2. `Promotion governance family`
- `backend/app/services/nrc_aps_promotion_gate.py`
- `tests/test_nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `tests/test_nrc_aps_promotion_tuning.py`
- `backend/app/services/nrc_adams_resources/aps_promotion_policy_v1.json`
- `project6.ps1`

3. `Retrieval cutover family`
- `backend/app/services/aps_retrieval_plane_cutover_validation.py`
- `backend/tests/test_aps_retrieval_plane_cutover_validation.py`
- `backend/tests/test_aps_retrieval_plane_cutover_gate.py`
- `tools/nrc_aps_retrieval_cutover_gate.py`
- `project6.ps1`

Frozen reading of that starting point:
- current `main` now proves the dedicated validate-only runtime/report-ref boundary selected by `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
- the live downstream graph still ends the bounded tracked chain at `validate_only_gates` and does not define another named post-validate-only node
- current `main` already contains a concrete promotion governance family with policy loading, governance evaluation, tuning comparison, proof tests, and operator entrypoints
- current `main` already contains a concrete retrieval-cutover parity-proof family, but it is a separate retrieval-plane validation surface over canonical payload and materialized retrieval comparison
- current `main` does not yet define a separate repo-backed later `validate-only top-chain expansion` implementation family beyond the landed validate-only boundary

## Frozen GateD APS promotion decisions

### 1. Exact next continuation choice

The exact next continuation admitted by this freeze is:
- a read-only decision selecting `promotion` as the first concrete later APS family beyond the landed dedicated validate-only runtime/report-ref boundary
- retrieval cutover remains later

Frozen target rule:
- the first later post-validate-only family is settled in favor of promotion governance
- do not reopen that ordering unless live repo truth changes materially
- do not invent a separate repo-backed validate-only top-chain family without direct repo evidence
- this landed freeze still does not admit promotion implementation changes, retrieval cutover changes, route/UI widening, runtime DB writes, or schema widening

### 2. Source-boundary rule

The later continuation frozen here must preserve:
- the landed dedicated validate-only runtime/report-ref boundary as the immediate upstream source boundary
- the existing validate-only contract/runtime/gate/report-ref surfaces already present on current `main`
- the separation between later promotion governance and later retrieval-cutover parity proof

Frozen source rule:
- the later continuation must treat the landed dedicated validate-only runtime/report-ref boundary as complete upstream truth
- the later continuation must not reopen generic gate-report refresh or dedicated validate-only runtime/report-ref implementation surfaces
- do not bypass the landed validate-only boundary by jumping directly to retrieval cutover, route/UI, runtime DB, or schema work in this tranche

### 3. Expected bounded later-lane posture

The expected later posture admitted after this freeze is:
- a bounded promotion-governance continuation centered on the existing promotion family already present on current `main`
- primary owner surfaces:
- `backend/app/services/nrc_aps_promotion_gate.py`
- `tests/test_nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `tests/test_nrc_aps_promotion_tuning.py`
- `backend/app/services/nrc_adams_resources/aps_promotion_policy_v1.json`
- `project6.ps1`

Frozen later-lane rule:
- prefer verification/adoption of the existing promotion family before inventing new promotion code
- keep retrieval cutover later
- do not widen into route/UI, runtime DB writes, or schema changes
- if live repo truth proves the existing promotion family is already sufficient and needs no bounded follow-up, stop instead of widening by default

### 4. Why retrieval cutover is not next

Frozen reason retrieval cutover is not the next APS family:
- the landed validate-only boundary is the last tracked node in the live downstream graph
- current `main` already contains a richer promotion-governance family over finalized validation batches, policy, and tuning rationale
- current retrieval cutover surfaces are parity-proof utilities over retrieval materialization rather than the first later governance family beyond the landed validate-only boundary
- selecting retrieval cutover next would skip the clearer later governance family already present in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- retrieval cutover
- route/UI widening
- runtime DB writes or migrations
- schema widening
- broader qualitative, hybrid, comparative, or cross-modal Layer 3 breadth
- any newly invented post-validate-only family not already backed by live repo truth

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- promotion implementation changes
- retrieval cutover changes
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- retrieval cutover before the promotion family is settled
- route, schema, or page changes
- runtime DB writes or runtime DB migrations
- a claim that a separate later validate-only top-chain family exists without direct repo proof

## Concise readiness judgment

Readiness judgment:
- current `main` already proves the landed dedicated validate-only runtime/report-ref boundary
- current repo truth now justifies freezing promotion as the first later APS family beyond that landed boundary
- retrieval cutover remains later

Reason:
- the live downstream graph stops at `validate_only_gates`
- promotion governance is the clearest concrete later family already present on current `main`
- retrieval cutover is present too, but as a separate later parity-proof family
- this freeze therefore records the first later family choice without widening implementation scope

What still remains intentionally deferred after this landed read-only freeze:
- retrieval cutover
- route/UI widening
- runtime DB writes or migrations
- schema widening
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md|artifact|current governing freeze for the landed dedicated validate_only runtime/report-ref boundary`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph still ends the bounded tracked chain at validate_only_gates and does not define a later named post-validate-only node|38-45;67-72;87-92;108-113`
- `R|backend/app/services/nrc_aps_validate_only_gates_contract.py|Current dedicated validate-only contract surface already landed on current \`main\`|1-203`
- `R|backend/app/services/nrc_aps_validate_only_gates.py|Current dedicated validate-only runtime surface already landed on current \`main\`|1-508`
- `R|backend/app/services/nrc_aps_validate_only_gates_gate.py|Current dedicated validate-only gate surface already landed on current \`main\`|1-264`
- `R|backend/tests/test_nrc_aps_validate_only_gates.py|Current dedicated validate-only proof surface already landed on current \`main\`|1-277`
- `R|backend/app/services/nrc_aps_promotion_gate.py|Current promotion governance family already exists on current \`main\`|14-19;174-182;518-727`
- `R|tests/test_nrc_aps_promotion_gate.py|Current promotion governance proof surface already exists on current \`main\`|136-205`
- `R|backend/app/services/nrc_aps_promotion_tuning.py|Current promotion policy comparison surface already exists on current \`main\`|15-22;106-205`
- `R|tests/test_nrc_aps_promotion_tuning.py|Current promotion tuning proof surface already exists on current \`main\`|110-177`
- `R|backend/app/services/aps_retrieval_plane_cutover_validation.py|Current retrieval cutover family is a separate later parity-proof surface|20-27;164-340`
- `R|backend/tests/test_aps_retrieval_plane_cutover_validation.py|Current retrieval cutover proof surface already exists on current \`main\`|193-316`
- `R|backend/tests/test_aps_retrieval_plane_cutover_gate.py|Current retrieval cutover CLI gate proof surface already exists on current \`main\`|187-196`
- `R|tools/nrc_aps_retrieval_cutover_gate.py|Current retrieval cutover CLI wrapper already exists on current \`main\`|1-12`
- `R|project6.ps1|Current operator entrypoints already expose validate-only, promotion, and retrieval-cutover actions|3-3;56-58;628-679`
