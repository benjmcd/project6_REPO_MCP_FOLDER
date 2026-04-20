# 13 GateD APS Context Freeze

## Purpose and authority note

This document freezes the bounded APS context-packet continuation contract after the already-landed Gate D APS evidence-report-export slice.
It answers one question only:
- what exact later APS family is admitted next, and with what source and proof posture, without reopening route/UI, runtime DB, earlier report/export truth, package-derived context truth, or later dossier/deterministic fan-out

It is not:
- an evidence-report-export redo or widening pass
- an evidence-report-export-package lane
- a package-derived context-packet lane
- a context-dossier, deterministic-family, or review-packet-family lane
- a public route-family or workbench/UI freeze
- a runtime DB integration lane
- a package-entry rewrite
- an evidence-report-export, export-package, or context-packet contract, service, or gate widening lane

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
11. `11_GATED_APS_REPORT_FREEZE.md`
12. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
13. historical Phase 1A REV1 artifacts as context only

Evidence basis: `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Candidate ranking and downstream sequencing posture|225-239`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`; `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family first does not imply later-family widening|6-44`; `R|backend/app/services/layer3_aps_report_export_handoff.py|Current bounded report-export handoff owner surface and single-source package posture|29-32`; `R|backend/app/services/layer3_aps_report_export_handoff.py|Current report-export handoff admits one source package kind and one persisted export artifact|83-183`; `R|backend/app/services/layer3_aps_report_export_handoff.py|Current report-export handoff summary contract keeps runtime DB writes false|186-245`; `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet schema ids and allowed source families include direct evidence_report_export|12-29`; `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet selector normalization and direct export-source descriptor rules|128-245`; `R|backend/app/services/nrc_aps_context_packet.py|Live context-packet source resolution accepts direct export refs and later package refs|329-366`; `R|backend/app/services/nrc_aps_context_packet.py|Live context-packet assembly and runtime-write path|468-549`; `R|backend/app/services/nrc_aps_context_packet_gate.py|Live context-packet gate and fail-closed validation surface|18-180`; `R|backend/app/services/nrc_aps_evidence_report_export_package_contract.py|Live export-package family requires at least two source exports|10-18`; `R|backend/app/services/nrc_aps_evidence_report_export_package.py|Live export-package family rejects cross-run composition and mutates run refs on persist|507-588`; `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph places export-package and direct export-derived context packets after branch exports|27-67`; `R|tests/test_nrc_aps_context_packet.py|Live context-packet service accepts direct report, export, and package source families|292-351`; `R|tests/test_nrc_aps_context_packet.py|Live context-packet persist path updates run refs|245-286`; `R|tests/test_nrc_aps_evidence_report_export_package.py|Live export-package path requires two source exports and updates run refs|227-278`; `R|tests/test_nrc_aps_evidence_report_export_package.py|Live export-package path rejects cross-run composition|284-317`

## Frozen tranche

The bounded APS context continuation is frozen as:
- `Gate D APS context continuation slice = one bounded adapter from the already-landed Layer 3 aps_evidence_report_export_handoff output row into the existing APS context-packet-family boundary only`
- keep the already-landed `canonical_internal`, `user_facing`, `review_facing`, `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, and `aps_evidence_report_export_handoff` rows as the already-proven upstream truth
- admit one additional APS-facing Layer 3 output package family only for the direct export-sourced context-packet target
- reuse the existing `L3OutputPackage` durable surface; do not add new Layer 3 package tables or migrations for this tranche
- target the live APS context-packet contract family directly, not a pseudo-context package, an export-package bridge, or a later dossier/deterministic family
- no evidence-report-export-package implementation in this tranche
- no package-derived context-packet, context-dossier, deterministic-insight, deterministic-challenge, or review-packet family in this tranche
- no route/UI widening
- no runtime DB writes

Hard rule:
- do not reinterpret this tranche as permission to widen into export-package aggregation, package-derived context, later APS families, or to back-edit the already-landed report-export handoff slice without a repo-confirmed blocker and a new freeze

## Canonical starting point

Read these surfaces first:

1. `Current Layer 3 APS evidence-report-export handoff truth`
- `backend/app/services/layer3_aps_report_export_handoff.py`
- `backend/tests/test_layer3_aps_report_export_handoff.py`

2. `Current APS context-packet family`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `tests/test_nrc_aps_context_packet.py`
- `tests/test_nrc_aps_context_packet_gate.py`

3. `Later-family stop-boundary proof`
- `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- the repo now already has landed Layer 3 APS evidence-bundle, citation-pack, evidence-report, and evidence-report-export handoff families
- the current Layer 3 APS report-export handoff admits exactly one `aps_evidence_report_export_handoff` row per packaged terminal session and requires `aps_evidence_report_handoff` as its sole source package kind
- the live APS export-package family requires at least two source exports from the same run and rejects cross-run composition
- the live APS context-packet family accepts direct `evidence_report_export` as an allowed source family, so the export-derived context-packet path is the first next live APS family compatible with the current single-export Layer 3 handoff shape
- the stock context-packet service persists artifacts and mutates `ConnectorRun.query_plan_json`, so the bounded Layer 3 continuation must preserve the contract family without inheriting runtime DB writes
- export-package implementation, package-derived context, dossier, deterministic, and review-packet fan-out remain later and broader than this tranche

## Frozen Gate D APS context decisions

### 1. Exact next APS family

The exact APS family admitted by this freeze is:
- the live APS context-packet-family boundary
- using the existing repo-local context-packet contract, persisted artifact expectations, and fail-closed gate surface
- using the `evidence_report_export` source family directly

Frozen target rule:
- the bounded APS-facing lane admitted by this freeze must target the live context-packet family directly
- it must source from the already-landed `aps_evidence_report_export_handoff` row and its persisted evidence-report-export artifact
- it must not invent a second export or aggregate across Layer 3 sessions just to satisfy the live export-package family
- it must not jump directly to export-package, package-derived context, dossier, deterministic, or review-packet families

### 2. Source and output row posture

Frozen first-v1 output row rule:
- the new row is `aps_context_packet_handoff`
- it must point at one persisted APS context-packet artifact payload
- it must treat `aps_evidence_report_export_handoff` as the required source package kind for this tranche
- it must encode that the admitted source family is `evidence_report_export`
- it must not replace or relabel the existing `canonical_internal`, `user_facing`, `review_facing`, `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, or `aps_evidence_report_export_handoff` rows

Frozen provenance rule:
- the new row must record the source `aps_evidence_report_export_handoff` row ref and stable context-packet artifact ref
- if the report-export handoff row or its persisted export payload is missing, unreadable, or incompatible with the live context-packet contract, fail closed before the new row is accepted

### 3. APS context-packet compatibility posture

The bounded APS-facing lane must treat the live APS context-packet family as the compatibility boundary.

Frozen compatibility requirements:
- reuse the live context-packet schema ids
- reuse the live context-packet projection and fact-grammar contract ids
- reuse the live context-packet checksum and file naming rules
- reuse the live context-packet fail-closed gate surface
- reuse the live direct-export source-family descriptor rules
- preserve connector-run runtime refs untouched even though the stock `persist_context_packet=True` path updates `aps_context_packet_report_refs` and `aps_context_packet_summaries`

Hard rule:
- this tranche must not widen the context-packet contract, gate codes, or validation semantics just to make Layer 3 handoff pass
- this tranche must not adopt the stock runtime-mutating `persist_context_packet=True` side effects into the Layer 3 handoff path

### 4. Owner, touch, and proof posture

Default owner surface:
- `backend/app/services/layer3_aps_context_packet_handoff.py`

Default proof surface:
- `backend/tests/test_layer3_aps_context_packet_handoff.py`

Read-only reuse allowed:
- `backend/app/services/layer3_aps_report_export_handoff.py`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`

Read-only stop-boundary evidence only:
- `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `tests/test_nrc_aps_evidence_report_export_package.py`

Frozen minimum proof:
- one terminal packaged session with an existing `aps_evidence_report_export_handoff` row emits one additional `aps_context_packet_handoff` row and one persisted APS context-packet artifact
- the emitted APS context-packet artifact satisfies the live context-packet load and gate validation path
- the new Layer 3 handoff row records stable source package refs and explicit `source_family=evidence_report_export` compatibility notes
- one missing or malformed report-export handoff ref fails closed before the new context-packet handoff row is accepted
- one attempt to bypass the source-family boundary or invent export-package aggregation fails closed rather than widening semantics
- connector-run runtime refs remain untouched in this Layer 3 handoff path
- no export-package implementation, package-derived context, dossier, deterministic, route, or runtime DB widening occurs

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/layer3_aps_report_export_handoff.py`
- edits to `backend/app/services/nrc_aps_context_packet.py`
- edits to `backend/app/services/nrc_aps_context_packet_contract.py`
- edits to `backend/app/services/nrc_aps_context_packet_gate.py`
- edits to `backend/app/services/nrc_aps_evidence_report_export_package.py`
- edits to `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- evidence-report-export-package implementation
- package-derived context-packet, dossier, deterministic, or review-packet implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if the bounded write lane requires:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/layer3_aps_report_export_handoff.py`
- edits to `backend/app/services/nrc_aps_context_packet.py`
- edits to `backend/app/services/nrc_aps_context_packet_contract.py`
- edits to `backend/app/services/nrc_aps_context_packet_gate.py`
- edits to `backend/app/services/nrc_aps_evidence_report_export_package.py`
- edits to `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- invention of a second export or cross-session aggregation step to satisfy export-package composition
- widening into package-derived context, dossier, deterministic, or review-packet services
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- `This freeze is the governing carried-forward contract for the bounded APS-family export-derived context-packet continuation slice now landed on current `main` beyond the landed evidence-report-export slice`

Reason:
- the earlier assumption that evidence-report-export-package was the likeliest next slice is not supported by the current Layer 3 handoff shape
- repo truth shows the live export-package family requires at least two same-run exports while the current Layer 3 APS report-export handoff admits exactly one export row per session
- repo truth also shows the live context-packet family already accepts `evidence_report_export` directly as an allowed source family, so this is the first next APS family that fits the current bounded Layer 3 source posture without inventing wider semantics
- this document froze that decision narrowly, and the bounded export-derived context-packet handoff slice governed by it has now landed on current `main` while keeping export-package implementation, package-derived context, dossier, deterministic, route/UI, runtime DB, and broader consumer widening out
- the exact next later continuation beyond that landed direct export-derived context slice is now governed by `14_GATED_APS_MULTISOURCE_FREEZE.md`, and the bounded shared same-run multisource admission slice governed by that freeze has now landed on current `main`

What still remains intentionally deferred after this freeze:
- APS evidence-report-export-package implementation
- package-derived context-packet fan-out
- context-dossier, deterministic, and review-packet fan-out beyond the export-derived context-packet family
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth
- deeper runtime-facing consumer widening

## Evidence appendix

Primary-planning anchors used most directly:
- `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Candidate ranking and downstream sequencing posture|225-239`
- `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`
- `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`
- `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family first does not imply later-family widening|6-44`

Repo-local anchors used most directly:
- `R|backend/app/services/layer3_aps_report_export_handoff.py|Current bounded report-export handoff owner surface and single-source package posture|29-32`
- `R|backend/app/services/layer3_aps_report_export_handoff.py|Current report-export handoff admits one source package kind and one persisted export artifact|83-183`
- `R|backend/app/services/layer3_aps_report_export_handoff.py|Current report-export handoff summary contract keeps runtime DB writes false|186-245`
- `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet schema ids and allowed source families include direct evidence_report_export|12-29`
- `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet selector normalization and direct export-source descriptor rules|128-245`
- `R|backend/app/services/nrc_aps_context_packet.py|Live context-packet source resolution accepts direct export refs and later package refs|329-366`
- `R|backend/app/services/nrc_aps_context_packet.py|Live context-packet assembly and runtime-write path|468-549`
- `R|backend/app/services/nrc_aps_context_packet_gate.py|Live context-packet gate and fail-closed validation surface|18-180`
- `R|backend/app/services/nrc_aps_evidence_report_export_package_contract.py|Live export-package family requires at least two source exports|10-18`
- `R|backend/app/services/nrc_aps_evidence_report_export_package.py|Live export-package family rejects cross-run composition and mutates run refs on persist|507-588`
- `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph places export-package and direct export-derived context packets after branch exports|27-67`
- `R|tests/test_nrc_aps_context_packet.py|Live context-packet persist path updates run refs|245-286`
- `R|tests/test_nrc_aps_context_packet.py|Live context-packet service accepts direct report, export, and package source families|292-351`
- `R|tests/test_nrc_aps_evidence_report_export_package.py|Live export-package path requires two source exports and updates run refs|227-278`
- `R|tests/test_nrc_aps_evidence_report_export_package.py|Live export-package path rejects cross-run composition|284-317`
