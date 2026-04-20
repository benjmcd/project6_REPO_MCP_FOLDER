# 10 GateD APS Citation Freeze

## Purpose and authority note

This document freezes the bounded APS citation continuation contract after the already-landed Gate D APS evidence-bundle handoff slice.
It answers one question only:
- what exact later APS family is admitted next, and with what source and proof posture, without reopening route/UI, runtime DB, earlier package truth, or later report/context/deterministic fan-out

It is not:
- an evidence-bundle redo or widening pass
- a report-family, context-family, dossier-family, deterministic-family, or review-packet-family lane
- a public route-family or workbench/UI freeze
- a runtime DB integration lane
- a package-entry rewrite
- a citation-pack contract, service, or gate widening lane

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
10. historical Phase 1A REV1 artifacts as context only

Evidence basis: `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended first APS-facing tranche and candidate ranking|217-229`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`; `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family first does not imply report/context next|6-44`; `R|backend/app/services/layer3_aps_handoff.py|Current bounded evidence-bundle handoff owner surface and package kind|32-35`; `R|backend/app/services/layer3_aps_handoff.py|Current evidence-bundle handoff row summary and emit path|385-467`; `R|backend/app/services/nrc_aps_evidence_citation_pack_contract.py|Live citation-pack schema ids, checksum, and file naming helpers|10-84`; `R|backend/app/services/nrc_aps_evidence_citation_pack.py|Live citation-pack persisted load and validation surface|115-142`; `R|backend/app/services/nrc_aps_evidence_citation_pack.py|Live citation-pack assembly and persist/failure surface|333-488`; `R|backend/app/services/nrc_aps_evidence_citation_pack_gate.py|Live citation-pack gate and fail-closed validation surface|1-216`; `R|backend/app/services/nrc_aps_evidence_report.py|Later report-family depends on citation-pack plus broader runtime/report surfaces|1-80`; `R|backend/app/services/nrc_aps_context_packet.py|Later context-family depends on report/export/package surfaces|1-60`; `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph places citation-pack immediately after evidence-bundle|146-172`; `R|tests/test_nrc_aps_evidence_citation_pack.py|Live citation-pack success/failure proof surface|1-235`; `R|tests/test_nrc_aps_evidence_citation_pack_gate.py|Live citation-pack gate proof surface|1-166`

## Frozen tranche

The bounded APS citation continuation is frozen as:
- `Gate D APS citation continuation slice = one bounded adapter from the already-landed Layer 3 aps_evidence_bundle_handoff output row into the existing APS citation-pack-family boundary only`
- keep the already-landed `canonical_internal`, `user_facing`, `review_facing`, and `aps_evidence_bundle_handoff` rows as the already-proven upstream truth
- admit one additional APS-facing Layer 3 output package family only for the citation-pack target
- reuse the existing `L3OutputPackage` durable surface; do not add new Layer 3 package tables or migrations for this tranche
- target the live APS citation-pack contract family directly, not a pseudo-citation package or a later report/context family
- no evidence-report, evidence-report-export, evidence-report-export-package, context-packet, context-dossier, deterministic-insight, deterministic-challenge, or review-packet family in this tranche
- no route/UI widening
- no runtime DB writes

Hard rule:
- do not reinterpret this tranche as permission to widen into later APS families or to back-edit the already-landed evidence-bundle handoff slice without a repo-confirmed blocker and a new freeze

## Canonical starting point

Read these surfaces first:

1. `Current Layer 3 APS evidence-bundle handoff truth`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/tests/test_layer3_aps_handoff.py`

2. `Current APS citation-pack family`
- `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- `backend/app/services/nrc_aps_evidence_citation_pack.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_gate.py`
- `tests/test_nrc_aps_evidence_citation_pack.py`
- `tests/test_nrc_aps_evidence_citation_pack_gate.py`

3. `Later APS family stop-boundary proof`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- the repo now already has one landed Layer 3 APS evidence-bundle handoff family
- the immediate next live APS family after evidence-bundle is citation-pack, not report/context/deterministic
- the later report/context chain already widens into broader runtime/export/package surfaces, so it must stay out of this tranche

## Frozen Gate D APS citation decisions

### 1. Exact next APS family

The exact APS family admitted by this freeze is:
- the live APS citation-pack-family boundary
- using the existing repo-local citation-pack contract, persisted artifact expectations, and fail-closed gate surface

Frozen target rule:
- the bounded APS-facing lane admitted by this freeze must target the live citation-pack family directly
- it must source from the already-landed `aps_evidence_bundle_handoff` row and its persisted bundle artifact
- it must not recompute from `canonical_internal` package truth when the already-landed evidence-bundle handoff row is available
- it must not jump directly to report, context, dossier, deterministic, or review-packet families

### 2. Source and output row posture

Frozen first-v1 output row rule:
- the new row is `aps_evidence_citation_pack_handoff`
- it must point at one persisted APS citation-pack artifact payload
- it must treat `aps_evidence_bundle_handoff` as the required source package kind for this tranche
- it must not replace or relabel the existing `canonical_internal`, `user_facing`, `review_facing`, or `aps_evidence_bundle_handoff` rows

Frozen provenance rule:
- the new row must record the source `aps_evidence_bundle_handoff` row ref and stable citation-pack artifact ref
- if the evidence-bundle handoff row or its persisted bundle payload is missing, unreadable, or incompatible with the live citation-pack contract, fail closed before the new row is accepted

### 3. APS citation-pack compatibility posture

The bounded APS-facing lane must treat the live APS citation-pack family as the compatibility boundary.

Frozen compatibility requirements:
- reuse the live citation-pack schema ids
- reuse the live citation-pack checksum and file naming rules
- reuse the live citation-pack persisted-load validation surface
- reuse the live citation-pack fail-closed gate surface

Hard rule:
- this tranche must not widen the citation-pack contract, gate codes, or validation semantics just to make Layer 3 handoff pass

### 4. Owner, touch, and proof posture

Default owner surface:
- `backend/app/services/layer3_aps_citation_handoff.py`

Default proof surface:
- `backend/tests/test_layer3_aps_citation_handoff.py`

Read-only reuse allowed:
- `backend/app/services/layer3_aps_handoff.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- `backend/app/services/nrc_aps_evidence_citation_pack.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_gate.py`

Frozen minimum proof:
- one terminal packaged session with an existing `aps_evidence_bundle_handoff` row emits one additional `aps_evidence_citation_pack_handoff` row and one persisted APS citation-pack artifact
- the emitted APS citation-pack artifact satisfies the live citation-pack load and gate validation path
- the new Layer 3 handoff row records stable source package refs and explicit compatibility notes
- one missing or malformed evidence-bundle handoff ref fails closed before the new citation-pack handoff row is accepted
- no report/context/deterministic/route/runtime DB widening occurs

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/nrc_aps_evidence_citation_pack.py`
- edits to `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- edits to `backend/app/services/nrc_aps_evidence_citation_pack_gate.py`
- evidence-report or later APS-family implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if the bounded write lane requires:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/layer3_aps_handoff.py`
- edits to `backend/app/services/nrc_aps_evidence_citation_pack.py`
- edits to `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- edits to `backend/app/services/nrc_aps_evidence_citation_pack_gate.py`
- widening into `backend/app/services/nrc_aps_evidence_report.py`, `backend/app/services/nrc_aps_context_packet.py`, or later APS-family services
- route, schema, or page changes
- runtime DB writes or runtime DB migrations
- invention of a pseudo-APS target because the live citation-pack family cannot be satisfied cleanly

## Concise readiness judgment

Readiness judgment:
- `This freeze is now the governing carried-forward contract for the bounded APS citation handoff slice now landed on current \`main\` after the already-landed evidence-bundle handoff slice`

Reason:
- the earlier blocker was no longer the first APS-family choice
- the remaining missing decision was the exact next later APS family and whether it should source from already-landed evidence-bundle handoff truth or reopen earlier package truth
- this document froze that decision narrowly at the live citation-pack-family boundary and now governs the bounded citation handoff slice landed on current `main` while keeping report/context/deterministic families, route/UI, runtime DB, and broader consumer widening out

What still remains intentionally deferred after this freeze:
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth
- APS evidence-report, context, dossier, deterministic, and review-packet fan-out beyond the citation-pack family
- deeper runtime-facing consumer widening

## Evidence appendix

Primary-planning anchors used most directly:
- `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended first APS-facing tranche and candidate ranking|217-229`
- `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`
- `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`
- `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family first does not imply report/context next|6-44`

Repo-local anchors used most directly:
- `R|backend/app/services/layer3_aps_handoff.py|Current bounded evidence-bundle handoff owner surface and package kind|32-35`
- `R|backend/app/services/layer3_aps_handoff.py|Current evidence-bundle handoff row summary and emit path|385-467`
- `R|backend/app/services/nrc_aps_evidence_citation_pack_contract.py|Live citation-pack schema ids, checksum, and file naming helpers|10-84`
- `R|backend/app/services/nrc_aps_evidence_citation_pack.py|Live citation-pack persisted load and validation surface|115-142`
- `R|backend/app/services/nrc_aps_evidence_citation_pack.py|Live citation-pack assembly and persist/failure surface|333-488`
- `R|backend/app/services/nrc_aps_evidence_citation_pack_gate.py|Live citation-pack gate and fail-closed validation surface|1-216`
- `R|backend/app/services/nrc_aps_evidence_report.py|Later report-family depends on citation-pack plus broader runtime/report surfaces|1-80`
- `R|backend/app/services/nrc_aps_context_packet.py|Later context-family depends on report/export/package surfaces|1-60`
- `R|backend/app/services/review_nrc_aps_graph.py|Downstream graph places citation-pack immediately after evidence-bundle|146-172`
