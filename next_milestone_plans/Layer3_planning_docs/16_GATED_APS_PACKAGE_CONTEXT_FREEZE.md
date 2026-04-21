# 16 GateD APS Package Context Freeze

## Purpose and authority note

This document freezes the bounded later shared APS continuation immediately after the now-landed export-package handoff boundary.
It answers one question only:
- which exact later shared APS family should continue next from the landed `aps_evidence_report_export_package_handoff` seam, without reopening route/UI, runtime DB, schema, earlier APS truth, or later dossier/deterministic fan-out

It is not:
- a package-derived context-packet implementation lane
- a `context_dossier`, deterministic, or review-packet lane
- an export-package widening lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
4. `14_GATED_APS_MULTISOURCE_FREEZE.md`
5. `13_GATED_APS_CONTEXT_FREEZE.md`
6. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
7. `11_GATED_APS_REPORT_FREEZE.md`
8. `10_GATED_APS_CITATION_FREEZE.md`
9. `09_GATED_APS_HANDOFF_FREEZE.md`
10. historical Phase 1A REV1 artifacts as context only

Current-state note:
- current `main` now includes the bounded `aps_evidence_report_export_package_handoff` slice rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- current `main` also now includes the narrow export/export-package gate hardening follow-up in `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, and `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- current `main` now includes this read-only freeze selecting the next later shared-family boundary beyond that landed export-package seam
- current branch/workspace now also carries the bounded package-derived context handoff implementation slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, plus the narrow context-packet gate hardening in `backend/app/services/nrc_aps_context_packet_gate.py` and `backend/tests/test_layer3_aps_context_packet_handoff.py`, but that branch-local slice is not yet landed on current `main`

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md|artifact|current governing freeze for the landed export-package boundary`; `R|backend/app/services/layer3_aps_report_export_package_handoff.py|Current bounded export-package handoff owner surface|35-405`; `R|backend/tests/test_layer3_aps_report_export_package_handoff.py|Current bounded export-package handoff proof covers success, fail-closed boundaries, and scope-collision hardening|46-428`; `R|backend/app/services/nrc_aps_evidence_report_export_gate.py|Current export gate now filters by exact embedded run identity instead of sanitized filename scope alone|25-188`; `R|backend/app/services/nrc_aps_evidence_report_export_package_gate.py|Current export-package gate now filters by exact owner_run_id instead of sanitized filename scope alone|25-203`; `R|backend/app/services/layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff owner surface in the current branch/workspace|31-277`; `R|backend/tests/test_layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff proof surface in the current branch/workspace|38-230`; `R|backend/app/services/nrc_aps_context_packet_gate.py|Current context-packet gate now filters exact owner-run identity under sanitized filename-scope collisions|31-67;122-233`; `R|backend/tests/test_layer3_aps_context_packet_handoff.py|Current bounded context-packet proof surface now covers non-path-safe run ids and exact owner-run collision filtering|124-255`; `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet contract accepts evidence_report_export_package as a package source family|22-28;145-148;181-183`; `R|backend/app/services/nrc_aps_context_packet.py|Live package-derived context packet family still mutates run refs on persist|468-549`; `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family remains later and depends on paired context packets with compatible source-family posture|18-32;166-174;237-282`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream shared graph places export_package before context_packet_package and before context_dossier|33-37;58-64;99-105`

## Frozen tranche

The bounded APS package-derived context continuation is frozen as:
- `Gate D APS package-derived context continuation slice = one read-only freeze selecting package-derived context packet as the exact next later shared APS family beyond the landed export-package handoff boundary`
- keep the already-landed `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, `aps_evidence_report_export_handoff`, `aps_context_packet_handoff`, `aps_multisource_admission`, and `aps_evidence_report_export_package_handoff` rows as the already-proven upstream truth
- this freeze itself does not admit implementation of package-derived context, `context_dossier`, deterministic, route/UI, runtime DB, or schema widening
- do not admit direct shared export-package widening in this tranche
- if any later continuation cannot stay inside the landed export-package handoff seam plus the live context-packet contract boundary, reopen the freeze instead of improvising

Hard rule:
- do not reinterpret this freeze and the bounded current branch handoff slice as permission to widen directly beyond package-derived context into `context_dossier`, deterministic, review-packet, route/UI, runtime DB, or schema work

## Canonical starting point

Read these surfaces first:

1. `Current landed export-package seam`
- `backend/app/services/layer3_aps_report_export_package_handoff.py`
- `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- `backend/app/services/nrc_aps_evidence_report_export_gate.py`
- `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`

2. `Next later shared APS consumer family`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/nrc_aps_context_packet.py`

3. `Later consumer beyond that next family`
- `backend/app/services/nrc_aps_context_dossier_contract.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- the export-package boundary is now already proven on current `main`
- the export/export-package gate pair now also proves exact raw run ownership under sanitized filename-scope collisions, so the landed boundary is no longer relying on lossy filename scope alone
- the live graph places `context_packet_package` directly after `export_package`
- the live context-packet contract accepts `evidence_report_export_package` as a package source family
- `context_dossier` remains later because it still depends on paired context packets rather than directly on the export-package handoff seam
- both live later shared APS families still mutate `ConnectorRun.query_plan_json` on persist
- therefore this freeze selects next-family order only; it does not admit runtime-write implementation of the selected family

## Frozen GateD APS package-derived context decisions

### 1. Exact next shared-family choice

The exact next continuation admitted by this freeze is:
- package-derived context packet as the next later shared APS family beyond the landed export-package handoff boundary
- `context_dossier` remains later and must not be used to skip the earlier package-derived context boundary

Frozen target rule:
- the next later shared-family freeze after the landed export-package handoff is now settled in favor of package-derived context packet
- do not reopen that ordering unless repo truth changes on the live downstream graph or contract surfaces
- do not treat this read-only freeze as proof that package-derived context implementation has landed on current `main`

### 2. Expected bounded implementation posture

The expected owner/proof posture admitted after this freeze is now present in the current branch/workspace as:
- a new bounded Layer 3 package-derived context handoff surface rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- focused proof rooted in `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- narrow shared context-packet gate hardening rooted in `backend/app/services/nrc_aps_context_packet_gate.py` and `backend/tests/test_layer3_aps_context_packet_handoff.py`

Frozen implementation rule for the current branch-local write-enabled lane admitted after this freeze:
- source only from the already-landed `aps_evidence_report_export_package_handoff` truth and the live package-source branch of the context-packet contract
- reuse the live `nrc_aps_context_packet` contract/load boundary and keep gate edits narrow; the current branch-local slice hardens only the shared context-packet gate because a repo-confirmed sanitized filename-scope collision blocker required exact owner-run filtering
- keep `backend/app/models/models.py`, migrations, route/UI, runtime DB writes, and later dossier/deterministic fan-out out

### 3. Why dossier is not next

Frozen reason dossier is not the next shared-family choice:
- the live graph places `export_package` before `context_packet_package`, and `context_dossier` still consumes paired context packets further downstream
- the live dossier contract still depends on at least two source packets with compatible source-family posture
- selecting dossier next would skip the earlier package-derived context boundary that already exists in live repo truth

### 4. Explicitly deferred downstream families

This freeze keeps deferred:
- direct edits to the shared `nrc_aps_evidence_report_export_package*.py` runtime surfaces beyond the now-landed handoff and gate-hardening boundary
- package-derived context implementation beyond the bounded current branch handoff slice
- direct `context_dossier` implementation
- deterministic-insight, deterministic-challenge, and review-packet families
- route/UI widening
- runtime DB writes or migrations
- schema widening

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/nrc_aps_context_packet_contract.py`
- edits to `backend/app/services/nrc_aps_context_packet.py`
- edits to `backend/app/services/nrc_aps_context_dossier_contract.py`
- direct `context_dossier`, deterministic, or review-packet implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- a grouping mechanism beyond the already-landed export-package handoff seam
- direct edits to `backend/app/services/nrc_aps_context_packet_contract.py` or `backend/app/services/nrc_aps_context_packet.py` without a repo-confirmed blocker
- skipping straight to `context_dossier`, deterministic, or review-packet implementation
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This freeze is the governing carried-forward contract now landed on current `main` for the bounded choice of package-derived context packet as the next later shared APS family beyond the landed export-package handoff boundary.

Reason:
- the landed export-package seam is now proven on current `main`
- the merged gate-hardening follow-up closes the lossy sanitized-scope ambiguity at that boundary by filtering on embedded raw run identity
- repo truth shows `context_packet_package` is the first visible shared APS family after `export_package`
- repo truth also shows `context_dossier` remains further downstream of paired context packets
- this branch-local freeze therefore settles the next shared-family choice narrowly without admitting implementation

What still remains intentionally deferred after this landed freeze:
- package-derived context-packet implementation
- direct `context_dossier`, deterministic, and review-packet fan-out
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md|artifact|current governing freeze for the landed export-package boundary`
- `R|backend/app/services/layer3_aps_report_export_package_handoff.py|Current bounded export-package handoff owner surface|35-405`
- `R|backend/tests/test_layer3_aps_report_export_package_handoff.py|Current bounded export-package handoff proof covers success, fail-closed boundaries, and scope-collision hardening|46-428`
- `R|backend/app/services/nrc_aps_evidence_report_export_gate.py|Current export gate now filters by exact embedded run identity instead of sanitized filename scope alone|25-188`
- `R|backend/app/services/nrc_aps_evidence_report_export_package_gate.py|Current export-package gate now filters by exact owner_run_id instead of sanitized filename scope alone|25-203`
- `R|backend/app/services/layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff owner surface in the current branch/workspace|31-277`
- `R|backend/tests/test_layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff proof surface in the current branch/workspace|38-230`
- `R|backend/app/services/nrc_aps_context_packet_gate.py|Current context-packet gate now filters exact owner-run identity under sanitized filename-scope collisions|31-67;122-233`
- `R|backend/tests/test_layer3_aps_context_packet_handoff.py|Current bounded context-packet proof surface now covers non-path-safe run ids and exact owner-run collision filtering|124-255`
- `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet contract accepts evidence_report_export_package as a package source family|22-28;145-148;181-183`
- `R|backend/app/services/nrc_aps_context_packet.py|Live package-derived context packet family still mutates run refs on persist|468-549`
- `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family remains later and depends on paired context packets with compatible source-family posture|18-32;166-174;237-282`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream shared graph places export_package before context_packet_package and before context_dossier|33-37;58-64;99-105`
