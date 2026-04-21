# 21 GateD APS Validate-Only-Gates Freeze

## Purpose and authority note

This document freezes the bounded APS continuation immediately after the now-landed `aps_deterministic_challenge_review_packet_handoff` milestone.
It answers one question only:
- which exact verification-family boundary should continue next after the landed `aps_deterministic_challenge_review_packet_handoff` slice, without reopening promotion, retrieval cutover, route/UI, runtime DB, schema, or earlier APS truth

It is not:
- a validate-only implementation lane
- a promotion gate lane
- a retrieval-cutover lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `20_GATED_APS_REVIEW_PACKET_FREEZE.md`
4. `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`
5. `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
6. `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
7. `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
8. `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
9. `14_GATED_APS_MULTISOURCE_FREEZE.md`
10. `13_GATED_APS_CONTEXT_FREEZE.md`
11. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
12. `11_GATED_APS_REPORT_FREEZE.md`
13. `10_GATED_APS_CITATION_FREEZE.md`
14. `09_GATED_APS_HANDOFF_FREEZE.md`
15. historical Phase 1A REV1 artifacts as context only

Current merged-state note:
- current `main` now includes the bounded `aps_deterministic_challenge_review_packet_handoff` slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`
- current `main` now also includes the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`, and that landed lane still keeps one persisted deterministic challenge artifact as the immediate downstream source boundary
- current `main` already has the live `validate_only_gates` node on the downstream review graph and run projection rooted in `backend/app/services/review_nrc_aps_graph.py`
- current `main` already treats `gate_reports` and `gate_results` as the runtime surfaces for that validate-only node in `backend/app/services/review_nrc_aps_graph.py` and `backend/app/services/review_nrc_aps_tree.py`
- current `main` already has validate-only operator entrypoints through `project6.ps1`, including `validate-nrc-aps-deterministic-challenge-review-packet` and aggregate `gate-nrc-aps`
- current `main` does not yet expose a dedicated `aps_validate_only_gates_report_refs` bucket in `backend/app/services/connectors_sciencebase.py`
- current `main` does not yet contain a dedicated `nrc_aps_validate_only_gates_contract.py`, `nrc_aps_validate_only_gates.py`, or `nrc_aps_validate_only_gates_gate.py`
- current branch now also includes this read-only freeze selecting `validate_only_gates` as the exact next verification continuation beyond the landed deterministic challenge review-packet handoff while keeping later promotion, retrieval cutover, route/UI, runtime DB, and schema widening out

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md|artifact|current governing freeze for the landed deterministic challenge review-packet boundary`; `R|backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff owner surface on current \`main\`|1-392`; `R|backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff proof surface on current \`main\`|1-627`; `R|backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py|Live review-packet gate already validates the persisted review-packet boundary through a dedicated validate-only report path|137-289`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph places validate_only_gates immediately after deterministic challenge review packet and maps that node to gate_reports plus gate_results|38-41;67-68;87-88;108-109;413-428;543-548;774-779`; `R|backend/app/services/review_nrc_aps_tree.py|Live review tree already treats gate_reports and gate_results as first-class runtime layout surfaces|61-71`; `R|backend/tests/test_review_nrc_aps_graph.py|Live review-graph proof already asserts validate_only_gates exists and is backed by real gate totals in the review runtime|28-52`; `R|project6.ps1|Current operator entrypoints already expose deterministic challenge review-packet validation and aggregate gate execution as validate-only actions|569-579;664-708`; `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry stops at deterministic challenge review packet and does not yet define a dedicated validate_only_gates bucket|2948-2962`

## Frozen tranche

The bounded APS continuation is frozen as:
- `Gate D APS validate-only-gates continuation slice = one read-only freeze selecting validate_only_gates as the exact next verification family after the landed deterministic challenge review-packet handoff milestone`
- keep the already-landed `aps_deterministic_challenge_review_packet_handoff` row as the immediate upstream truth
- keep the validate-only boundary grounded in the existing generic gate-report surfaces already present on current `main`
- this freeze itself does not admit validate-only implementation, promotion, retrieval cutover, route/UI, runtime DB, or schema widening
- do not reinterpret the landed deterministic challenge review-packet handoff as permission to widen directly into promotion or cutover families
- if any later continuation cannot stay inside the existing gate-report and validate-only operator surfaces already present on current `main`, reopen the freeze instead of improvising

Hard rule:
- do not skip directly from `deterministic_challenge_review_packet` to promotion or retrieval cutover

## Canonical starting point

Read these surfaces first:

1. `Current landed review-packet boundary`
- `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`
- `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`
- `backend/app/services/nrc_aps_deterministic_challenge_review_packet_contract.py`
- `backend/app/services/nrc_aps_deterministic_challenge_review_packet.py`
- `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`

2. `Next verification-family surfaces`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_details.py`
- `backend/tests/test_review_nrc_aps_graph.py`
- `project6.ps1`
- `backend/app/services/connectors_sciencebase.py`

Frozen reading of that starting point:
- current `main` now proves the bounded deterministic challenge review-packet handoff and its persisted `aps.deterministic_challenge_review_packet.v1` artifact boundary
- the live downstream graph still places `validate_only_gates` immediately after `deterministic_challenge_review_packet`
- the live review graph and review tree already treat `gate_reports/*.json` plus `summary.gate_results` as the runtime surfaces for that `validate_only_gates` node
- the current operator entrypoints already expose validate-only execution through the deterministic challenge review-packet gate and the aggregate `gate-nrc-aps` action
- current `main` does not yet define a dedicated validate-only family-specific report-ref bucket or a dedicated `nrc_aps_validate_only_gates_*` contract/runtime/gate trio
- therefore `validate_only_gates` is the exact next family to freeze after the landed deterministic challenge review-packet boundary, but the later continuation must stay inside the existing generic validate-only/report surfaces unless repo truth changes

## Frozen GateD APS validate-only decisions

### 1. Exact next verification-family choice

The exact next continuation admitted by this freeze is:
- `validate_only_gates` as the next verification family after the landed `aps_deterministic_challenge_review_packet_handoff` slice
- promotion and retrieval cutover remain later

Frozen target rule:
- the next APS freeze after the landed deterministic challenge review-packet handoff is now settled in favor of `validate_only_gates`
- do not reopen that ordering unless repo truth changes on the live downstream graph or validate-only runtime surfaces
- do not treat this read-only freeze as proof that any dedicated validate-only implementation has landed on current `main`

### 2. Source-boundary rule

The bounded validate-only continuation frozen here must preserve:
- the landed deterministic challenge review-packet handoff as the immediate upstream Layer 3 boundary for this tranche
- the existing validate-only operator and report surfaces already present on current `main`
- the existing `gate_reports/*.json` plus `summary.gate_results` posture used by the live review graph and review tree

Frozen source rule:
- the later continuation must treat the persisted deterministic challenge review-packet boundary as the immediate upstream source boundary
- the later continuation must stay validate-only and fail-closed on empty runtime
- do not bypass the review-packet boundary by jumping directly to promotion, retrieval cutover, route/UI, runtime DB, or schema work in this tranche
- do not reopen the landed review-packet contract/runtime surfaces in this read-only freeze

### 3. Expected bounded implementation posture

The expected owner/proof posture admitted after this freeze is:
- a bounded validate-only execution or report-refresh lane rooted in the existing operator and review surfaces already present on current `main`
- primary owner surfaces:
  - `project6.ps1`
  - `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`
  - `backend/app/services/review_nrc_aps_graph.py`
  - `backend/app/services/review_nrc_aps_tree.py`
- focused proof surfaces:
  - `backend/tests/test_review_nrc_aps_graph.py`
  - any existing validate-only gate tests or checked-in gate reports directly refreshed by that later lane

Frozen implementation rule for the later lane admitted after this freeze:
- keep the later continuation validate-only
- keep it fail-closed on empty runtime
- do not seed new artifacts
- do not widen into promotion, retrieval cutover, route/UI, runtime DB writes, or schema changes
- if a later continuation requires a new dedicated `aps_validate_only_gates_report_refs` bucket or a new `nrc_aps_validate_only_gates_*` contract/runtime/gate family, reopen the freeze instead of improvising

### 4. Why promotion and retrieval cutover are not next

Frozen reason promotion and retrieval cutover are not the next APS family:
- the live downstream graph still places `validate_only_gates` immediately after `deterministic_challenge_review_packet`
- the current review surfaces already materialize a validate-only node from `gate_reports` and `gate_results`
- current operator entrypoints already stop at validate-only gate execution before later promotion or retrieval-cutover work
- selecting promotion or retrieval cutover next would skip the immediate verification boundary that already exists in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- a dedicated validate-only family-specific report-ref bucket in `backend/app/services/connectors_sciencebase.py`
- a dedicated `nrc_aps_validate_only_gates_contract.py`, `nrc_aps_validate_only_gates.py`, or `nrc_aps_validate_only_gates_gate.py` family
- promotion
- retrieval cutover
- route/UI widening
- runtime DB writes or migrations
- schema widening
- broader qualitative, hybrid, comparative, or cross-modal Layer 3 breadth

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- direct validate-only implementation
- direct promotion or retrieval-cutover implementation
- a new validate-only family-specific report-ref bucket
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- a new dedicated `aps_validate_only_gates_report_refs` bucket
- new dedicated `nrc_aps_validate_only_gates_*` contract/runtime/gate files
- promotion or retrieval cutover before the validate-only boundary is settled
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This branch-local read-only freeze is the governing carried-forward contract for the bounded choice of `validate_only_gates` as the next APS family after the landed deterministic challenge review-packet boundary.

Reason:
- current `main` already proves the bounded deterministic challenge review-packet handoff and its persisted review-packet artifact boundary
- repo truth already contains the downstream `validate_only_gates` node on the review graph plus the generic gate-report surfaces that back it
- repo truth does not yet contain a dedicated validate-only family-specific runtime stack
- this read-only freeze therefore settles the next family choice narrowly without overclaiming implementation

What still remains intentionally deferred after this branch-local read-only freeze:
- the later validate-only execution or report-refresh lane
- promotion
- retrieval cutover
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md|artifact|current governing freeze for the landed deterministic challenge review-packet boundary`
- `R|backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff owner surface on current \`main\`|1-392`
- `R|backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff proof surface on current \`main\`|1-627`
- `R|backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py|Live review-packet gate already validates the persisted review-packet boundary through a dedicated validate-only report path|137-289`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph places validate_only_gates immediately after deterministic challenge review packet and maps that node to gate_reports plus gate_results|38-41;67-68;87-88;108-109;413-428;543-548;774-779`
- `R|backend/app/services/review_nrc_aps_tree.py|Live review tree already treats gate_reports and gate_results as first-class runtime layout surfaces|61-71`
- `R|backend/tests/test_review_nrc_aps_graph.py|Live review-graph proof already asserts validate_only_gates exists and is backed by real gate totals in the review runtime|28-52`
- `R|project6.ps1|Current operator entrypoints already expose deterministic challenge review-packet validation and aggregate gate execution as validate-only actions|569-579;664-708`
- `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry stops at deterministic challenge review packet and does not yet define a dedicated validate_only_gates bucket|2948-2962`
