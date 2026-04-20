# 11 GateD APS Report Freeze

## Purpose and authority note

This document freezes the bounded APS evidence-report continuation contract after the already-landed Gate D APS citation-pack handoff slice.
It answers one question only:
- what exact later APS family is admitted next, and with what source and proof posture, without reopening route/UI, runtime DB, earlier package truth, or later export/context/deterministic fan-out

It is not:
- a citation-pack redo or widening pass
- an evidence-report-export, export-package, context-family, dossier-family, deterministic-family, or review-packet-family lane
- a public route-family or workbench/UI freeze
- a runtime DB integration lane
- a package-entry rewrite
- an evidence-report contract, service, or gate widening lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the external canonical Layer 3 planning corpus
3. the active repo-local REV2 Phase 1A control spine
4. `04_GATEC_ENTRY_FREEZE.md`
5. `05_GATEC_IMPLEMENTATION_FREEZE.md`
6. `06_GATEC_PASS_FREEZE.md`
7. `07_GATEC_COHORT_FREEZE.md`
8. `08_GATED_PACKAGE_FREEZE.md`
9. `09_GATED_APS_HANDOFF_FREEZE.md`
10. `10_GATED_APS_CITATION_FREEZE.md`
11. historical Phase 1A REV1 artifacts as context only

Evidence basis: `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Candidate ranking and downstream sequencing posture|225-239`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`; `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family first does not imply later-family widening|6-44`; `R|backend/app/services/layer3_aps_citation_handoff.py|Current bounded citation-pack handoff owner surface and package kind|29-32`; `R|backend/app/services/layer3_aps_citation_handoff.py|Current citation-pack handoff summary and emit path|200-270`; `R|backend/app/services/nrc_aps_evidence_report_contract.py|Live evidence-report schema ids, checksum, and file naming helpers|11-120`; `R|backend/app/services/nrc_aps_evidence_report.py|Live evidence-report assembly and runtime-write path|390-438`; `R|backend/app/services/nrc_aps_evidence_report_gate.py|Live evidence-report gate and fail-closed validation surface|1-140`; `R|backend/app/services/nrc_aps_evidence_report_export.py|Later export family widens into runtime/export refs|348-400`; `R|backend/app/services/nrc_aps_context_packet.py|Later context-family depends on report, export, and package surfaces|12-16`; `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph places evidence-report immediately after citation-pack and export/context later|26-40`; `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph edges from citation-pack into report and later families|51-67`; `R|tests/test_nrc_aps_evidence_report.py|Live evidence-report persistence updates run refs and proves fail-closed behavior|185-245`; `R|tests/test_nrc_aps_evidence_report.py|Invalid source citation-pack writes failure refs fail-closed|390-405`; `R|tests/test_nrc_aps_evidence_report.py|Hidden-run persist path fails closed without artifact writes|440-452`

## Frozen tranche

The bounded APS evidence-report continuation is frozen as:
- `Gate D APS report continuation slice = one bounded adapter from the already-landed Layer 3 aps_evidence_citation_pack_handoff output row into the existing APS evidence-report-family boundary only`
- keep the already-landed `canonical_internal`, `user_facing`, `review_facing`, `aps_evidence_bundle_handoff`, and `aps_evidence_citation_pack_handoff` rows as the already-proven upstream truth
- admit one additional APS-facing Layer 3 output package family only for the evidence-report target
- reuse the existing `L3OutputPackage` durable surface; do not add new Layer 3 package tables or migrations for this tranche
- target the live APS evidence-report contract family directly, not a pseudo-report package or a later export/context family
- no evidence-report-export, evidence-report-export-package, context-packet, context-dossier, deterministic-insight, deterministic-challenge, or review-packet family in this tranche
- no route/UI widening
- no runtime DB writes

Hard rule:
- do not reinterpret this tranche as permission to widen into later APS families or to back-edit the already-landed citation-pack handoff slice without a repo-confirmed blocker and a new freeze

## Canonical starting point

Read these surfaces first:

1. `Current Layer 3 APS citation-pack handoff truth`
- `backend/app/services/layer3_aps_citation_handoff.py`
- `backend/tests/test_layer3_aps_citation_handoff.py`

2. `Current APS evidence-report family`
- `backend/app/services/nrc_aps_evidence_report_contract.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_gate.py`
- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_gate.py`

3. `Later APS family stop-boundary proof`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- the repo now already has landed Layer 3 APS evidence-bundle and citation-pack handoff families
- the immediate next live APS family after citation-pack is evidence-report, not export/context/deterministic
- the stock evidence-report service persists artifacts and mutates `ConnectorRun.query_plan_json`, so the bounded Layer 3 continuation must preserve the contract family without inheriting runtime DB writes
- the later export/context chain already widens into broader runtime/export/package surfaces, so it must stay out of this tranche

## Frozen Gate D APS report decisions

### 1. Exact next APS family

The exact APS family admitted by this freeze is:
- the live APS evidence-report-family boundary
- using the existing repo-local evidence-report contract, persisted artifact expectations, and fail-closed gate surface

Frozen target rule:
- the bounded APS-facing lane admitted by this freeze must target the live evidence-report family directly
- it must source from the already-landed `aps_evidence_citation_pack_handoff` row and its persisted citation-pack artifact
- it must not recompute from `aps_evidence_bundle_handoff` or `canonical_internal` package truth when the already-landed citation-pack handoff row is available
- it must not jump directly to export, context, dossier, deterministic, or review-packet families

### 2. Source and output row posture

Frozen first-v1 output row rule:
- the new row is `aps_evidence_report_handoff`
- it must point at one persisted APS evidence-report artifact payload
- it must treat `aps_evidence_citation_pack_handoff` as the required source package kind for this tranche
- it must not replace or relabel the existing `canonical_internal`, `user_facing`, `review_facing`, `aps_evidence_bundle_handoff`, or `aps_evidence_citation_pack_handoff` rows

Frozen provenance rule:
- the new row must record the source `aps_evidence_citation_pack_handoff` row ref and stable evidence-report artifact ref
- if the citation-pack handoff row or its persisted citation-pack payload is missing, unreadable, or incompatible with the live evidence-report contract, fail closed before the new row is accepted

### 3. APS evidence-report compatibility posture

The bounded APS-facing lane must treat the live APS evidence-report family as the compatibility boundary.

Frozen compatibility requirements:
- reuse the live evidence-report schema ids
- reuse the live evidence-report checksum and file naming rules
- reuse the live evidence-report fail-closed gate surface
- preserve connector-run runtime refs untouched even though the stock `persist_report=True` path updates `aps_evidence_report_report_refs` and `aps_evidence_report_summaries`

Hard rule:
- this tranche must not widen the evidence-report contract, gate codes, or validation semantics just to make Layer 3 handoff pass
- this tranche must not adopt the stock runtime-mutating `persist_report=True` side effects into the Layer 3 handoff path

### 4. Owner, touch, and proof posture

Default owner surface:
- `backend/app/services/layer3_aps_report_handoff.py`

Default proof surface:
- `backend/tests/test_layer3_aps_report_handoff.py`

Read-only reuse allowed:
- `backend/app/services/layer3_aps_citation_handoff.py`
- `backend/app/services/nrc_aps_evidence_report_contract.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_gate.py`

Frozen minimum proof:
- one terminal packaged session with an existing `aps_evidence_citation_pack_handoff` row emits one additional `aps_evidence_report_handoff` row and one persisted APS evidence-report artifact
- the emitted APS evidence-report artifact satisfies the live evidence-report load and gate validation path
- the new Layer 3 handoff row records stable source package refs and explicit compatibility notes
- one missing or malformed citation-pack handoff ref fails closed before the new evidence-report handoff row is accepted
- connector-run runtime refs remain untouched in this Layer 3 handoff path
- no export/context/deterministic/route/runtime DB widening occurs

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/layer3_aps_citation_handoff.py`
- edits to `backend/app/services/nrc_aps_evidence_report.py`
- edits to `backend/app/services/nrc_aps_evidence_report_contract.py`
- edits to `backend/app/services/nrc_aps_evidence_report_gate.py`
- evidence-report-export or later APS-family implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if the bounded write lane requires:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/layer3_aps_citation_handoff.py`
- edits to `backend/app/services/nrc_aps_evidence_report.py`
- edits to `backend/app/services/nrc_aps_evidence_report_contract.py`
- edits to `backend/app/services/nrc_aps_evidence_report_gate.py`
- widening into `backend/app/services/nrc_aps_evidence_report_export.py`, `backend/app/services/nrc_aps_context_packet.py`, or later APS-family services
- route, schema, or page changes
- runtime DB writes or runtime DB migrations
- invention of a pseudo-APS target because the live evidence-report family cannot be satisfied cleanly

## Concise readiness judgment

Readiness judgment:
- `This freeze is now the governing carried-forward contract for the bounded APS-family evidence-report continuation slice now landed on current main beyond the landed citation-pack-family handoff slice`

Reason:
- the earlier blocker was no longer the first post-citation APS-family choice
- the remaining missing decision at freeze time was the exact next later APS family and whether that continuation could stay outside runtime DB writes
- this document froze that decision narrowly at the live evidence-report-family boundary, and the bounded evidence-report handoff slice governed by it has now landed on current main while keeping export/context/deterministic families, route/UI, runtime DB, and broader consumer widening out

What still remains intentionally deferred after this freeze:
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth
- the exact next later APS-family continuation beyond evidence-report is now separately frozen by `12_GATED_APS_REPORT_EXPORT_FREEZE.md` at the evidence-report-export boundary, and the bounded direct export-derived context-packet slice separately frozen by `13_GATED_APS_CONTEXT_FREEZE.md` has now landed on current `main` beyond that landed export slice
- APS export-package remains later because the live export-package family requires two same-run exports while the current bounded Layer 3 evidence-report-export handoff admits one export row per session
- package-derived context, dossier, deterministic, and review-packet fan-out beyond the direct export-derived context-packet continuation
- deeper runtime-facing consumer widening

## Evidence appendix

Primary-planning anchors used most directly:
- `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Candidate ranking and downstream sequencing posture|225-239`
- `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`
- `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`
- `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family first does not imply later-family widening|6-44`

Repo-local anchors used most directly:
- `R|backend/app/services/layer3_aps_citation_handoff.py|Current bounded citation-pack handoff owner surface and package kind|29-32`
- `R|backend/app/services/layer3_aps_citation_handoff.py|Current citation-pack handoff summary and emit path|200-270`
- `R|backend/app/services/nrc_aps_evidence_report_contract.py|Live evidence-report schema ids, checksum, and file naming helpers|11-120`
- `R|backend/app/services/nrc_aps_evidence_report.py|Live evidence-report assembly and runtime-write path|390-438`
- `R|backend/app/services/nrc_aps_evidence_report_gate.py|Live evidence-report gate and fail-closed validation surface|1-140`
- `R|backend/app/services/nrc_aps_evidence_report_export.py|Later export family widens into runtime/export refs|348-400`
- `R|backend/app/services/nrc_aps_context_packet.py|Later context-family depends on report, export, and package surfaces|12-16`
- `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph places evidence-report immediately after citation-pack and export/context later|26-40`
- `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph edges from citation-pack into report and later families|51-67`
- `R|tests/test_nrc_aps_evidence_report.py|Live evidence-report persistence updates run refs and proves fail-closed behavior|185-245`
- `R|tests/test_nrc_aps_evidence_report.py|Invalid source citation-pack writes failure refs fail-closed|390-405`
- `R|tests/test_nrc_aps_evidence_report.py|Hidden-run persist path fails closed without artifact writes|440-452`
