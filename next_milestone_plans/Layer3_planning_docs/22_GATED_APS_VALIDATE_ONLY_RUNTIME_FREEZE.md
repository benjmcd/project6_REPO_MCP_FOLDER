# 22 GateD APS Validate-Only Runtime Freeze

## Purpose and authority note

This document freezes the bounded APS continuation immediately after the now-landed generic `validate_only_gates` gate-report refresh lane.
It answers one question only:
- whether the repo should admit a dedicated `validate_only_gates` family-specific report-ref and runtime boundary beyond the landed generic `gate_reports` plus `summary.gate_results` posture, without reopening promotion, retrieval cutover, route/UI, runtime DB, schema, or earlier APS truth

It is not:
- a validate-only implementation lane
- a generic gate-report refresh lane
- a promotion gate lane
- a retrieval-cutover lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`
4. `20_GATED_APS_REVIEW_PACKET_FREEZE.md`
5. `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`
6. `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
7. `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
8. `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
9. `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
10. `14_GATED_APS_MULTISOURCE_FREEZE.md`
11. `13_GATED_APS_CONTEXT_FREEZE.md`
12. historical Phase 1A REV1 artifacts as context only

Current merged-state note:
- current `main` now includes the bounded `aps_deterministic_challenge_review_packet_handoff` slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`
- current `main` now also includes the landed read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze from PR `#136`, which selected `validate_only_gates` as the exact next verification continuation beyond that landed review-packet boundary
- current `main` now also includes the post-PR136 docs/progress sync from PR `#137`
- current `main` now also includes the bounded generic validate-only gate-report refresh lane from PR `#138`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`
- current `main` now also includes the post-PR138 docs/progress sync from PR `#139`
- current `main` already maps `validate_only_gates` to generic `gate_reports` plus `summary.gate_results` in `backend/app/services/review_nrc_aps_graph.py` and `backend/app/services/review_nrc_aps_tree.py`
- current `main` now also includes this landed read-only freeze from PR `#140`, selecting the dedicated validate-only runtime/report-ref boundary as the only admissible next continuation beyond that landed generic gate-report refresh lane
- current `main` now also exposes a dedicated `aps_validate_only_gates_report_refs` bucket in `backend/app/services/connectors_sciencebase.py`
- current `main` now also includes the bounded dedicated validate-only runtime/report-ref implementation slice from PR `#143`, rooted in `backend/app/services/nrc_aps_validate_only_gates_contract.py`, `backend/app/services/nrc_aps_validate_only_gates.py`, `backend/app/services/nrc_aps_validate_only_gates_gate.py`, `backend/tests/test_nrc_aps_validate_only_gates.py`, `tools/nrc_aps_refresh_validate_only_gates.py`, `tools/nrc_aps_validate_only_gates_gate.py`, `backend/app/services/review_nrc_aps_runtime.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/connectors_sciencebase.py`, and `project6.ps1`
- that landed lane keeps the landed generic gate-report refresh boundary as its immediate upstream truth, adds the dedicated validate-only contract/runtime/gate plus report-ref registry surfaces selected by this freeze, and still does not admit later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, or schema widening
- no later post-validate-only freeze has yet landed on current `main`
- open PR `#145` now carries the read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze selecting promotion as the first later APS family beyond that landed validate-only boundary while keeping retrieval cutover later

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md|artifact|current governing freeze for the landed generic validate_only_gates boundary`; `R|backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff owner surface on current \`main\`|1-392`; `R|backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff proof surface on current \`main\`|1-627`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph still places validate_only_gates immediately after deterministic challenge review packet and now projects that node from the dedicated validate-only artifact plus expected generic gate reports|38-41;67-68;87-88;108-109;303-305;580-596;823-840`; `R|backend/app/services/review_nrc_aps_tree.py|Live review tree still treats gate_reports and gate_results as first-class runtime layout surfaces|61-71`; `R|backend/app/services/review_nrc_aps_gate_reports.py|Current landed bounded generic validate-only refresh owner surface on current \`main\`|25-212`; `R|backend/tests/test_review_nrc_aps_gate_reports.py|Current landed bounded generic validate-only refresh proof surface on current \`main\`|31-141`; `R|backend/app/services/nrc_aps_validate_only_gates_contract.py|Current dedicated validate-only contract surface on current \`main\`|1-203`; `R|backend/app/services/nrc_aps_validate_only_gates.py|Current dedicated validate-only runtime surface on current \`main\`|1-508`; `R|backend/app/services/nrc_aps_validate_only_gates_gate.py|Current dedicated validate-only gate surface on current \`main\`|1-264`; `R|backend/tests/test_nrc_aps_validate_only_gates.py|Current dedicated validate-only proof surface on current \`main\`|1-277`; `R|backend/app/services/review_nrc_aps_runtime.py|Current shared validate-only runtime-binding surface on current \`main\`|1-379`; `R|project6.ps1|Current operator entrypoints expose refresh-nrc-aps-review-gate-reports plus refresh-nrc-aps-validate-only-gates as bounded validate-only execution on current \`main\`|53-53;581-612`; `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry now includes a dedicated validate_only_gates bucket on current \`main\`|2962-2962`

## Frozen tranche

The bounded APS continuation is frozen as:
- `Gate D APS validate-only runtime/report-ref continuation slice = one read-only freeze selecting whether and how to admit a dedicated validate_only_gates family-specific report-ref/runtime boundary after the landed generic gate-report refresh lane`
- keep the landed generic gate-report refresh lane as the immediate upstream truth for this tranche
- keep the later continuation grounded in the existing live graph and review-tree facts already present on current `main`
- this freeze itself does not admit dedicated runtime/report-ref implementation, promotion, retrieval cutover, route/UI, runtime DB, or schema widening
- do not reinterpret the landed generic gate-report refresh lane as proof that a dedicated validate-only runtime family has already landed on current `main`
- if repo truth proves the generic gate-report boundary is already sufficient and no dedicated family is needed, stop instead of widening by default

Hard rule:
- do not skip directly from the landed generic validate-only gate-report refresh lane to promotion or retrieval cutover without first settling whether dedicated validate-only runtime/report-ref surfaces are required

## Canonical starting point

Read these surfaces first:

1. `Current landed generic validate-only boundary`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_details.py`
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `tools/nrc_aps_refresh_review_gate_reports.py`
- `tools/run_nrc_aps_local_corpus_e2e.py`
- `backend/tests/test_review_nrc_aps_graph.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- `project6.ps1`

2. `Next dedicated runtime/report-ref decision surfaces`
- `backend/app/services/connectors_sciencebase.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_details.py`
- `project6.ps1`

Frozen reading of that starting point:
- current `main` now proves the bounded generic validate-only gate-report refresh lane and its adopted review-runtime `gate_reports/*.json` plus `summary.gate_results` refresh posture
- the live downstream graph still places `validate_only_gates` immediately after `deterministic_challenge_review_packet`
- the live review graph and review tree still treat `gate_reports/*.json` plus `summary.gate_results` as the runtime surfaces for that `validate_only_gates` node
- current operator entrypoints already expose validate-only execution through `refresh-nrc-aps-review-gate-reports` and aggregate `gate-nrc-aps`
- current `main` now also defines a dedicated validate-only family-specific report-ref bucket plus a dedicated `nrc_aps_validate_only_gates_*` contract/runtime/gate trio
- therefore current `main` now proves the bounded dedicated validate-only runtime/report-ref continuation selected by this freeze, while later validate-only top-chain expansion, promotion, and retrieval cutover remain outside the landed packet until a fresh read-only freeze admits them

## Frozen GateD APS validate-only runtime/report-ref decisions

### 1. Exact next continuation choice

The exact next continuation admitted by this freeze is:
- a read-only decision on dedicated `validate_only_gates` family-specific report-ref/runtime surfaces as the next continuation beyond the landed generic gate-report refresh lane
- promotion and retrieval cutover remain later

Frozen target rule:
- the next APS freeze beyond the landed generic validate-only gate-report refresh lane is now settled in favor of the dedicated runtime/report-ref family decision
- do not reopen that ordering unless repo truth changes on the live downstream graph or validate-only runtime surfaces
- this now-landed read-only freeze plus the now-landed bounded implementation lane on current `main` still do not admit later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, or schema widening

### 2. Source-boundary rule

The bounded continuation frozen here must preserve:
- the landed generic validate-only gate-report refresh lane as the immediate upstream Layer 3 boundary for this tranche
- the existing generic validate-only operator and review surfaces already present on current `main`
- the existing `gate_reports/*.json` plus `summary.gate_results` posture used by the live review graph and review tree

Frozen source rule:
- the later continuation must treat the landed generic gate-report refresh lane as the immediate upstream source boundary
- the later continuation must stay validate-only and fail-closed on empty runtime
- do not bypass the generic validate-only boundary by jumping directly to promotion, retrieval cutover, route/UI, runtime DB, or schema work in this tranche
- do not reopen the landed generic gate-report refresh owner/proof surfaces in this read-only freeze

### 3. Expected bounded implementation posture

The expected owner/proof posture admitted after this freeze, and now landed on current `main` from PR `#143`, is:
- a bounded dedicated validate-only runtime/report-ref lane rooted in the current run-level report-ref registry plus dedicated validate_only runtime surfaces
- primary owner surfaces:
- `backend/app/services/connectors_sciencebase.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `project6.ps1`
- landed dedicated surfaces:
- `backend/app/services/nrc_aps_validate_only_gates_contract.py`
- `backend/app/services/nrc_aps_validate_only_gates.py`
- `backend/app/services/nrc_aps_validate_only_gates_gate.py`
- focused proof surfaces:
- `backend/tests/test_review_nrc_aps_graph.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- `backend/tests/test_nrc_aps_validate_only_gates.py`

Frozen implementation rule for the later lane admitted after this freeze:
- keep the later continuation validate-only
- keep it fail-closed on empty runtime
- do not seed new artifacts
- do not widen into promotion, retrieval cutover, route/UI, runtime DB writes, or schema changes
- if a later post-validate-only continuation can be proven unnecessary because the landed dedicated validate-only boundary is sufficient, stop instead of widening

### 4. Why promotion and retrieval cutover are not next

Frozen reason promotion and retrieval cutover are not the next APS family:
- the live downstream graph still places `validate_only_gates` immediately after `deterministic_challenge_review_packet`
- current `main` now proves both the landed generic gate-report refresh posture and the landed dedicated validate-only runtime/report-ref boundary for that validate-only node
- no later post-validate-only freeze has yet admitted validate-only top-chain expansion, promotion, or retrieval cutover
- selecting promotion or retrieval cutover next without a fresh freeze would skip the remaining post-validate-only decision boundary that still exists in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- later validate-only top-chain expansion
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
- direct dedicated validate-only runtime/report-ref implementation
- direct promotion or retrieval-cutover implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- promotion or retrieval cutover before the dedicated validate-only runtime/report-ref question is settled
- route, schema, or page changes
- runtime DB writes or runtime DB migrations
- a claim that the landed generic gate-report boundary already implies a dedicated validate-only family without direct repo proof

## Concise readiness judgment

Readiness judgment:
- This now-landed read-only freeze on current `main` from PR `#140`, plus the now-landed bounded dedicated validate-only runtime/report-ref implementation lane from PR `#143`, are the governing carried-forward contract for the validate-only boundary beyond the landed generic gate-report refresh lane.

Reason:
- current `main` already proves the landed generic validate-only gate-report refresh lane and the dedicated validate-only family-specific report-ref/runtime stack that this freeze selected
- the live downstream graph still ends the bounded tracked chain at `validate_only_gates`
- no later post-validate-only freeze has yet landed on current `main`, and open PR `#145` now carries the read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze selecting promotion while keeping retrieval cutover later
- this freeze therefore remains the governing carried-forward boundary while later continuation still requires a fresh read-only freeze rather than direct widening

What still remains intentionally deferred after this now-landed read-only freeze and now-landed implementation lane:
- later validate-only top-chain expansion
- promotion
- retrieval cutover
- route/UI widening
- runtime DB writes or migrations
- schema widening
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md|artifact|current governing freeze for the landed generic validate_only_gates boundary`
- `R|backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff owner surface on current \`main\`|1-392`
- `R|backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff proof surface on current \`main\`|1-627`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph still places validate_only_gates immediately after deterministic challenge review packet and still projects that node from gate_reports plus gate_results|38-41;67-68;87-88;108-109;413-428;543-548;774-779`
- `R|backend/app/services/review_nrc_aps_tree.py|Live review tree still treats gate_reports and gate_results as first-class runtime layout surfaces|61-71`
- `R|backend/app/services/review_nrc_aps_details.py|Live review details surface still derives node/file detail from the generic review graph and tree rather than a dedicated validate_only family|1-155`
- `R|backend/app/services/review_nrc_aps_gate_reports.py|Current landed bounded generic validate-only refresh owner surface on current \`main\`|25-212`
- `R|tools/nrc_aps_refresh_review_gate_reports.py|Current landed generic validate-only refresh CLI bridge on current \`main\`|1-36`
- `R|tools/run_nrc_aps_local_corpus_e2e.py|Current local-corpus proof runner now reuses the shared generic gate-report refresh helper on current \`main\`|26-27;973-985`
- `R|backend/tests/test_review_nrc_aps_gate_reports.py|Current landed bounded generic validate-only refresh proof surface on current \`main\`|31-141`
- `R|project6.ps1|Current operator entrypoints expose refresh-nrc-aps-review-gate-reports as validate-only execution on current \`main\`|53-53;581-593`
- `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry still stops at deterministic challenge review packet and does not yet define a dedicated validate_only_gates bucket|2948-2962`
