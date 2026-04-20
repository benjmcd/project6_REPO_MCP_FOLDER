# 14 GateD APS Multisource Freeze

## Purpose and authority note

This document freezes the bounded APS multisource continuation contract after the already-landed direct export-derived context-packet slice.
It answers one question only:
- what exact precondition boundary must be resolved next before later shared APS families can be admitted, without reopening route/UI, runtime DB, earlier APS handoff truth, or later dossier/deterministic fan-out

It is not:
- an `evidence_report_export_package` implementation lane
- a package-derived context-packet lane
- a `context_dossier`, deterministic, or review-packet lane
- a `report_export` or `context_packet` widening lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `13_GATED_APS_CONTEXT_FREEZE.md`
4. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
5. `11_GATED_APS_REPORT_FREEZE.md`
6. `10_GATED_APS_CITATION_FREEZE.md`
7. `09_GATED_APS_HANDOFF_FREEZE.md`
8. `08_GATED_PACKAGE_FREEZE.md`
9. historical Phase 1A REV1 artifacts as context only

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md|artifact|bounded direct export-derived context continuation contract`; `R|backend/app/models/models.py|L3Session remains session-scoped and L3 durable output surfaces remain unique by session and package kind|742-750;931-948`; `R|backend/app/services/layer3_aps_report_export_handoff.py|Current report-export handoff loads one session and one source package kind|83-128`; `R|backend/app/services/layer3_aps_context_packet_handoff.py|Current context-packet handoff loads one session and one source package kind|83-128`; `R|backend/app/services/nrc_aps_evidence_report_export_package_contract.py|Live export-package family requires at least two source exports|17-18;69-76`; `R|backend/app/services/nrc_aps_evidence_report_export_package.py|Live export-package family rejects cross-run composition and mutates run refs on persist|501-582`; `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family requires at least two source packets and compatible source-family posture|18-32;161-174;237-321`; `R|backend/app/services/nrc_aps_context_dossier.py|Live context-dossier persist path mutates run refs|580-625`; `R|backend/app/services/review_nrc_aps_graph.py|Downstream shared graph places export_package and context_dossier after paired export/context nodes|33-67`

## Frozen tranche

The bounded APS multisource continuation is frozen as:
- `Gate D APS multisource continuation slice = one read-only freeze that makes the shared same-run source-admission seam the next required boundary before later shared APS families`
- keep the already-landed `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, `aps_evidence_report_export_handoff`, and `aps_context_packet_handoff` rows as the already-proven upstream truth
- do not admit direct `evidence_report_export_package` or `context_dossier` implementation in this tranche
- do not pre-authorize model or migration changes in this tranche
- if the next write-enabled lane cannot prove the shared-source seam on existing durable Layer 3 surfaces, reopen the freeze instead of improvising

Hard rule:
- do not reinterpret this freeze as permission to widen directly into export-package, package-derived context, context-dossier, deterministic, review-packet, route/UI, or runtime DB work

## Canonical starting point

Read these surfaces first:

1. `Current landed single-source APS handoff truth`
- `backend/app/services/layer3_aps_report_export_handoff.py`
- `backend/app/services/layer3_aps_context_packet_handoff.py`

2. `Current Layer 3 durable surfaces`
- `backend/app/models/models.py`
- `backend/app/services/layer3_package_entry.py`

3. `Later shared APS families`
- `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `backend/app/services/nrc_aps_context_dossier_contract.py`
- `backend/app/services/nrc_aps_context_dossier.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- the current landed Layer 3 APS handoff services still load one `L3Session`, build `rows_by_kind` for that session, and admit one output package kind per session
- `L3ReconciliationRecord` is still unique per `session_id`
- `L3OutputPackage` is still unique by `(session_id, package_kind)`
- the live `evidence_report_export_package` family requires at least two same-run source exports and rejects cross-run composition
- the live `context_dossier` family requires at least two context packets and enforces compatible `objective` plus `source_family`
- both live shared APS families mutate `ConnectorRun.query_plan_json` on persist
- therefore the next unresolved boundary is not another single-source APS handoff family; it is the shared same-run source-admission seam required before either later shared APS family can be admitted on Layer 3 surfaces

## Frozen Gate D APS multisource decisions

### 1. Exact next continuation boundary

The exact next continuation admitted by this freeze is:
- the shared same-run multisource admission boundary for later APS shared families
- as a prerequisite boundary before direct `evidence_report_export_package` or `context_dossier` implementation

Frozen target rule:
- any next write-enabled lane must first prove how two same-run APS sources are identified, paired, and carried on existing Layer 3 durable surfaces
- it must not invent cross-run composition just to satisfy later shared APS families
- it must not reinterpret the already-landed `aps_evidence_report_export_handoff` or `aps_context_packet_handoff` slices as permission to widen directly into later shared APS families
- it must not skip straight to direct `evidence_report_export_package` or `context_dossier` implementation without first freezing and proving the shared-source seam

### 2. Durable-surface posture

Frozen durable-surface rule:
- treat current durable Layer 3 surfaces as session-scoped until a later write lane proves otherwise on existing repo truth
- do not assume that `selection_manifest_id` or any other current field is already a proven shared-source grouping contract
- do not add a new schema or migration in this tranche

Hard rule:
- if the next write lane cannot derive a stable same-run multisource grouping posture from existing landed durable surfaces, stop and reopen the freeze instead of improvising a new schema or hidden grouping mechanism

### 3. Proof posture for the next write-enabled lane

Frozen minimum proof for the next write-enabled lane:
- show that two same-run APS sources can be selected or grouped without cross-run composition
- show that the grouping mechanism is stable enough to feed later shared APS families without rewriting already-landed single-source rows
- show that one-source, duplicate-source, or incompatible-source inputs fail closed
- show that route/UI and runtime DB surfaces remain untouched unless separately frozen later

### 4. Explicitly deferred downstream families

This freeze keeps deferred:
- direct `evidence_report_export_package` implementation
- package-derived context-packet implementation
- direct `context_dossier` implementation
- deterministic-insight, deterministic-challenge, and review-packet families
- route/UI widening
- runtime DB writes or migrations
- schema widening

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- edits to `backend/app/services/nrc_aps_evidence_report_export_package.py`
- edits to `backend/app/services/nrc_aps_context_dossier_contract.py`
- edits to `backend/app/services/nrc_aps_context_dossier.py`
- direct `evidence_report_export_package` implementation
- package-derived context-packet implementation
- direct `context_dossier`, deterministic, or review-packet implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if the next write lane requires:
- edits to `backend/app/models/models.py`
- a new migration
- a grouping mechanism that is not derivable from current landed Layer 3 durable surfaces
- widening `backend/app/services/layer3_aps_report_export_handoff.py` or `backend/app/services/layer3_aps_context_packet_handoff.py` without a repo-confirmed blocker
- direct `evidence_report_export_package` or `context_dossier` implementation before the shared-source seam is separately proven
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This freeze is the governing carried-forward contract for the bounded APS multisource admission slice now implemented in the current branch state but not yet landed on current `main`.

Reason:
- the already-landed direct export-derived context-packet slice was the last single-source APS continuation compatible with the current Layer 3 handoff shape
- repo truth shows the next visible shared APS families require at least two same-run sources
- repo truth also shows current Layer 3 durable and handoff surfaces remain session-scoped and single-source
- this document froze that exact shared-source seam narrowly, and the bounded multisource admission slice governed by it is now implemented in the current branch state using existing `co_retrieval_group_id` plus APS source identity without schema widening
- that bounded slice still does not admit direct export-package or context-dossier implementation, and it is not yet landed on current `main`

What still remains intentionally deferred after this freeze:
- direct `evidence_report_export_package` implementation
- package-derived context-packet fan-out
- direct `context_dossier`, deterministic, and review-packet fan-out
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md|artifact|bounded direct export-derived context continuation contract`
- `R|backend/app/models/models.py|L3Session remains session-scoped and L3 durable output surfaces remain unique by session and package kind|742-750;931-948`
- `R|backend/app/services/layer3_aps_report_export_handoff.py|Current report-export handoff loads one session and one source package kind|83-128`
- `R|backend/app/services/layer3_aps_context_packet_handoff.py|Current context-packet handoff loads one session and one source package kind|83-128`
- `R|backend/app/services/nrc_aps_evidence_report_export_package_contract.py|Live export-package family requires at least two source exports|17-18;69-76`
- `R|backend/app/services/nrc_aps_evidence_report_export_package.py|Live export-package family rejects cross-run composition and mutates run refs on persist|501-582`
- `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family requires at least two source packets and compatible source-family posture|18-32;161-174;237-321`
- `R|backend/app/services/nrc_aps_context_dossier.py|Live context-dossier persist path mutates run refs|580-625`
- `R|backend/app/services/review_nrc_aps_graph.py|Downstream shared graph places export_package and context_dossier after paired export/context nodes|33-67`
