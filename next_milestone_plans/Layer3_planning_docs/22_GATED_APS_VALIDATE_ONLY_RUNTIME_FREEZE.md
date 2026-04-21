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
- current `main` does not yet expose a dedicated `aps_validate_only_gates_report_refs` bucket in `backend/app/services/connectors_sciencebase.py`
- current `main` does not yet contain a dedicated `nrc_aps_validate_only_gates_contract.py`, `nrc_aps_validate_only_gates.py`, or `nrc_aps_validate_only_gates_gate.py`
- current `main` now also includes this landed read-only freeze from PR `#140`, selecting the dedicated validate-only runtime/report-ref boundary as the only admissible next continuation beyond that landed generic gate-report refresh lane

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md|artifact|current governing freeze for the landed generic validate_only_gates boundary`; `R|backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff owner surface on current \`main\`|1-392`; `R|backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py|Current bounded deterministic challenge review-packet handoff proof surface on current \`main\`|1-627`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph still places validate_only_gates immediately after deterministic challenge review packet and still projects that node from gate_reports plus gate_results|38-41;67-68;87-88;108-109;413-428;543-548;774-779`; `R|backend/app/services/review_nrc_aps_tree.py|Live review tree still treats gate_reports and gate_results as first-class runtime layout surfaces|61-71`; `R|backend/app/services/review_nrc_aps_gate_reports.py|Current landed bounded generic validate-only refresh owner surface on current \`main\`|25-212`; `R|backend/tests/test_review_nrc_aps_gate_reports.py|Current landed bounded generic validate-only refresh proof surface on current \`main\`|31-141`; `R|project6.ps1|Current operator entrypoints expose refresh-nrc-aps-review-gate-reports as validate-only execution on current \`main\`|53-53;581-593`; `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry still stops at deterministic challenge review packet and does not yet define a dedicated validate_only_gates bucket|2948-2962`

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
- current `main` does not yet define a dedicated validate-only family-specific report-ref bucket or a dedicated `nrc_aps_validate_only_gates_*` contract/runtime/gate trio
- therefore, if continuation resumes beyond the landed generic gate-report boundary, the next step must be a read-only decision on that dedicated runtime/report-ref family rather than a direct implementation jump

## Frozen GateD APS validate-only runtime/report-ref decisions

### 1. Exact next continuation choice

The exact next continuation admitted by this freeze is:
- a read-only decision on dedicated `validate_only_gates` family-specific report-ref/runtime surfaces as the next continuation beyond the landed generic gate-report refresh lane
- promotion and retrieval cutover remain later

Frozen target rule:
- the next APS freeze beyond the landed generic validate-only gate-report refresh lane is now settled in favor of the dedicated runtime/report-ref family decision
- do not reopen that ordering unless repo truth changes on the live downstream graph or validate-only runtime surfaces
- do not treat this read-only freeze as proof that any dedicated validate-only implementation has landed on current `main`

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

The expected owner/proof posture admitted after this freeze, if a later write-enabled lane is justified, is:
- a bounded dedicated validate-only runtime/report-ref lane rooted in the current run-level report-ref registry plus dedicated validate_only runtime surfaces
- likely owner surfaces:
- `backend/app/services/connectors_sciencebase.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_details.py`
- `project6.ps1`
- likely dedicated new surfaces, only if later admitted by a write-enabled lane:
- `backend/app/services/nrc_aps_validate_only_gates_contract.py`
- `backend/app/services/nrc_aps_validate_only_gates.py`
- `backend/app/services/nrc_aps_validate_only_gates_gate.py`
- likely focused proof surfaces:
- `backend/tests/test_review_nrc_aps_graph.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- any future dedicated validate-only gate/runtime proof files admitted by that later lane

Frozen implementation rule for the later lane admitted after this freeze:
- keep the later continuation validate-only
- keep it fail-closed on empty runtime
- do not seed new artifacts
- do not widen into promotion, retrieval cutover, route/UI, runtime DB writes, or schema changes
- if a later continuation can be proven unnecessary because the landed generic gate-report boundary is already sufficient, stop instead of widening

### 4. Why promotion and retrieval cutover are not next

Frozen reason promotion and retrieval cutover are not the next APS family:
- the live downstream graph still places `validate_only_gates` immediately after `deterministic_challenge_review_packet`
- current `main` now proves only the generic gate-report refresh posture for that validate-only node
- current repo truth still leaves the dedicated validate-only runtime/report-ref family unresolved
- selecting promotion or retrieval cutover next would skip the remaining validate-only boundary question that still exists in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- dedicated validate-only runtime/report-ref implementation
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
- This landed read-only freeze on current `main` from PR `#140` is the governing carried-forward contract for the bounded next decision on whether to admit dedicated validate-only runtime/report-ref surfaces beyond the landed generic gate-report boundary.

Reason:
- current `main` already proves the landed generic validate-only gate-report refresh lane and the runtime surfaces that back it
- repo truth still does not contain a dedicated validate-only family-specific report-ref/runtime stack
- this read-only freeze therefore settles the next decision narrowly without overclaiming implementation

What still remains intentionally deferred after this landed read-only freeze:
- dedicated validate-only runtime/report-ref implementation
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
