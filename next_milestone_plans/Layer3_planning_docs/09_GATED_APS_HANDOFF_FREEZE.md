# 09 GateD APS Handoff Freeze

## Purpose and authority note

This document freezes the bounded write-enabled Gate D APS handoff continuation contract after the already-landed Gate D package-entry slice.
It answers one question only:
- what exact first APS-facing adapter and handoff target is admitted without reopening route/UI, runtime DB, broader APS fan-out, or later qualitative/cross-modal scope

It is not:
- a public route-family freeze
- a workbench/UI freeze
- a citation-pack, report, context, or deterministic-family handoff lane
- a runtime DB integration lane
- a package-entry rewrite
- a qualitative, hybrid, cross-modal, or comparative execution freeze

Applied authority order for this document:
1. live repo code and live tests on current `main`
2. the external canonical Layer 3 planning corpus
3. the active repo-local REV2 Phase 1A control spine
4. `04_GATEC_ENTRY_FREEZE.md`
5. `05_GATEC_IMPLEMENTATION_FREEZE.md`
6. `06_GATEC_PASS_FREEZE.md`
7. `07_GATEC_COHORT_FREEZE.md`
8. `08_GATED_PACKAGE_FREEZE.md`
9. historical Phase 1A REV1 artifacts as context only

Primary-planning citation note:
- `P` citations whose path segment begins `layer3_primary_planningdocs/` refer to the external canonical Layer 3 planning corpus at `C:\Users\benny\OneDrive\Desktop\Layer3\layer3_primary_planningdocs`.
- Those files are external planning authority, not repo-local implementation truth.
- Repo-local implementation truth still comes from the cited `R|...` paths in the current repo/worktree.

Evidence basis: `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Canonical internal package and APS handoff posture|126-217`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D and fail-closed conditions|107-126`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`; `P|layer3_primary_planningdocs/decisions/ADR-004_ANALYST_INSIGHT_TO_APS_HANDOFF_STRATEGY.md|Canonical package first, APS adapter later|6-30`; `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family level is the first APS-facing tranche|6-44`; `R|backend/app/models/models.py|L3 output package durability and package_kind uniqueness|943-953`; `R|backend/app/services/layer3_package_entry.py|Current Gate D package kinds, package refs, and handoff-blocked posture|43-84`; `R|backend/app/services/layer3_package_entry.py|Current canonical handoff_status compatibility note|718-788`; `R|backend/app/services/layer3_package_entry.py|Current output package persistence surface|1033-1054`; `R|backend/app/services/nrc_aps_evidence_bundle_contract.py|Live APS evidence-bundle schema ids, checksum, and file naming helpers|14-22`; `R|backend/app/services/nrc_aps_evidence_bundle_contract.py|Live APS checksum and file naming helpers|111-131`; `R|backend/app/services/nrc_aps_evidence_bundle.py|Live APS persisted bundle load and validation surface|36-129`; `R|backend/app/services/nrc_aps_evidence_bundle.py|Live APS bundle assembly and persist surface|466-605`; `R|backend/app/services/nrc_aps_evidence_bundle_gate.py|Live APS evidence-bundle gate and fail-closed validation surface|1-120`

## Frozen tranche

The bounded write-enabled Gate D continuation is frozen as:
- `Gate D APS continuation = one bounded adapter from landed Layer 3 package truth into the existing APS evidence-bundle-family boundary only`
- keep the already-landed canonical internal package as the internal source of truth
- keep the already-landed `user_facing` and `review_facing` packages as derived package truth
- admit one additional APS-facing Layer 3 output package family only for the evidence-bundle target
- reuse the existing `L3OutputPackage` durable surface; do not add new Layer 3 package tables or migrations for this tranche
- target the live APS evidence-bundle contract family, not a shadow or pseudo-equivalent APS-like family
- no citation-pack, report, context, dossier, deterministic-insight, deterministic-challenge, or review-packet handoff in this tranche
- no route/UI widening
- no runtime DB writes or runtime DB migrations
- no direct collapse of Layer 3 internal truth onto APS contract ids
- no direct HTTP self-calls

Hard rule:
- do not reinterpret this tranche as permission to widen into later APS families, runtime-facing additive surfaces, or the future workbench route family

## Canonical starting point

The live repo already has five distinct surfaces this slice must respect:

1. `Current landed Layer 3 package truth`
- `backend/app/services/layer3_package_entry.py`
- `backend/tests/test_layer3_package_entry.py`

2. `Current Layer 3 package durability surface`
- `backend/app/models/models.py`

3. `Current APS evidence-bundle contract family`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_bundle_gate.py`

4. `Current APS downstream status surface`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

5. `Current read-only and no-touch adjacent boundaries`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/api/router.py`
- `backend/app/schemas/api.py`
- `backend/main.py`

Frozen reading of that starting point:
- the repo already has one internal Layer 3 package family and one mature APS evidence-bundle family
- the remaining missing decision was not whether APS handoff exists in the repo; it was which exact APS family Layer 3 should touch first and how narrowly
- the first bounded APS target should begin at the earliest live APS family boundary that already has contract, persist, and gate surfaces
- the earliest repo-confirmed bounded APS family boundary is the evidence-bundle family, not the later citation/report/context/deterministic chain

## Frozen Gate D APS handoff decisions

### 1. Admitted package posture

The bounded APS handoff lane may admit only `l3_session` rows where:
- `l3_session.status` is terminal and `completed_at` is non-null
- one `l3_reconciliation_record` already exists for the session
- exactly one `canonical_internal` `l3_output_package` row already exists
- exactly one `user_facing` `l3_output_package` row already exists
- exactly one `review_facing` `l3_output_package` row already exists
- each required package row has a readable `payload_ref`
- the canonical package status is one of:
  - `package_complete`
  - `package_complete_with_warnings`
- no existing `aps_evidence_bundle_handoff` `l3_output_package` row exists yet for the session

Hard exclusions remain:
- non-terminal sessions
- sessions missing any required landed Gate D package row
- sessions whose required package payload refs are unreadable
- `package_review_only`
- `package_failed`

### 2. Exact first APS target posture

The exact first APS-facing target is frozen now as:
- the live APS evidence-bundle-family boundary
- using the existing repo-local evidence-bundle contract, persisted artifact expectations, and fail-closed validation surface

Frozen target rule:
- the bounded APS-facing lane admitted by this freeze must target the live evidence-bundle family directly
- it must not invent a Layer 3-only pseudo-APS bundle family as a substitute
- it must not jump directly to citation-pack, report, context-packet, dossier, deterministic-insight, deterministic-challenge, or review-packet families

### 3. Adapter contract and package-identity posture

Layer 3 internal truth remains:
- canonical internal package first
- derived `user_facing` and `review_facing` packages second

The bounded APS lane may add exactly one new Layer 3 output package family:
- `package_kind == "aps_evidence_bundle_handoff"`

Frozen first-v1 Layer 3 adapter identity:
- Layer 3 package schema id remains Layer 3-owned, not APS-owned
- the admitted first-v1 adapter schema id is:
  - `layer3.aps_evidence_bundle_handoff.v1`

Frozen first-v1 output row rule:
- the new `aps_evidence_bundle_handoff` row is the Layer 3-owned durable record of APS-facing emission for the first tranche
- it must point at one persisted APS evidence-bundle artifact payload
- it must not replace or relabel the existing `canonical_internal`, `user_facing`, or `review_facing` rows

Frozen first-v1 `summary_json` minimum for the new handoff row:
- `aps_target_family`
- `aps_schema_id`
- `bundle_id`
- `bundle_ref`
- `source_package_kinds_json`
- `source_package_refs_json`
- `compatibility_notes_json`
- `field_map_json`
- `handoff_status`

Hard rule:
- do not collapse Layer 3 internal package identity onto APS schema ids or APS file naming

### 4. APS evidence-bundle compatibility posture

The bounded APS handoff lane must treat the live APS evidence-bundle family as the compatibility boundary.

Frozen compatibility requirements:
- target schema id remains `aps.evidence_bundle.v2`
- existing APS checksum rules remain authoritative
- existing APS file naming expectations remain authoritative for the APS-facing artifact
- existing APS fail-closed validation posture remains authoritative

Frozen bounded mapping rule:
- the handoff lane must map from existing Layer 3 package truth into the evidence-bundle-family boundary with explicit compatibility notes and explicit field mapping
- if the current Layer 3 package truth does not contain enough provenance to satisfy that boundary without widening APS contracts or inventing synthetic provenance, stop and reopen the freeze

Frozen first-v1 provenance rule:
- the emitted APS artifact must point back to real package/session provenance
- the Layer 3 handoff row must point back to the emitted APS artifact and the Layer 3 source package refs
- the lane must fail closed if required APS provenance fields cannot be satisfied from the landed Layer 3 package truth

### 5. Similar-problem reuse posture

The bounded APS handoff lane may reuse the live APS evidence-bundle family as a repo-grounded target and validation surface for:
- APS schema ids
- APS checksum rules
- APS file naming
- APS persisted artifact validation
- APS fail-closed gate semantics

Hard rule:
- this tranche must not widen the APS evidence-bundle contract, gate codes, or validation semantics just to make Layer 3 handoff pass

### 6. Owner, touch, and proof posture

Frozen owner posture:
- owner module: `backend/app/services/layer3_aps_handoff.py`
- proof file: `backend/tests/test_layer3_aps_handoff.py`

Frozen expected touch envelope for the bounded write lane:
- `backend/app/services/layer3_aps_handoff.py`
- `backend/tests/test_layer3_aps_handoff.py`

Expected no-touch surfaces unless a repo-confirmed blocker proves otherwise:
- `backend/app/models/models.py`
- `backend/alembic/versions/*`
- `backend/app/services/layer3_package_entry.py`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/analysis.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_bundle_gate.py`
- `backend/app/api/router.py`
- `backend/app/schemas/api.py`
- `backend/main.py`
- analyst-insight static assets and route modules

Frozen proof posture:
- extend the direct service-level pytest pattern already used for the landed Layer 3 owner modules
- prove at minimum:
  - one terminal packaged session emits one additional `aps_evidence_bundle_handoff` row and one persisted APS evidence-bundle artifact
  - the emitted APS artifact satisfies the live APS evidence-bundle contract/load validation path
  - the new Layer 3 handoff row records stable source package refs and explicit compatibility notes
  - one session missing required packaged provenance fails closed before the new handoff row is accepted
  - no route/UI/runtime DB/later APS-family widening occurs

## Explicit non-goals

Do not include in the bounded APS handoff implementation lane:
- citation-pack-family handoff
- evidence-report-family handoff
- context-packet or dossier handoff
- deterministic-insight, deterministic-challenge, or review-packet handoff
- route-family, page, or browser work
- runtime DB writes, runtime DB migrations, or runtime-helper reuse as execution state
- public workbench admission
- qualitative, hybrid, cross-modal, or comparative execution changes
- edits to APS evidence-bundle contracts or gates just to widen acceptance

## Stop conditions

Stop and reopen the freeze instead of improvising if the bounded write lane requires:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/layer3_package_entry.py`
- edits to `backend/app/services/layer3_pass_entry.py`
- edits to `backend/app/services/analysis.py`
- edits to `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- edits to `backend/app/services/nrc_aps_evidence_bundle.py`
- edits to `backend/app/services/nrc_aps_evidence_bundle_gate.py`
- route, schema, or page changes
- runtime DB writes or runtime DB migrations
- widening beyond the evidence-bundle family
- invention of a pseudo-APS target because the live evidence-bundle family cannot be satisfied cleanly

## Concise readiness judgment

Readiness judgment:
- `This freeze is sufficient for the bounded write-enabled APS handoff lane that is now present in the current implementation state after the already-landed Gate D package-entry slice on current main`

Reason:
- the earlier blocker was no longer internal packaging
- the remaining missing decision was the exact first APS-facing target and bounded adapter posture
- this document freezes that decision narrowly at the live evidence-bundle-family boundary while keeping later APS families, route/UI, runtime DB, and broader consumer widening out

What still remains intentionally deferred after this freeze:
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth
- later APS-facing fan-out beyond the separately frozen citation-pack-family continuation
- deeper runtime-facing consumer widening

## Concise evidence appendix

Primary-planning anchors used most directly:
- `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Canonical internal package and APS handoff posture|126-217`
- `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|APS downstream handoff requirements and sequencing|67-107`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D and fail-closed conditions|107-126`
- `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items and later fan-out posture|123-145`
- `P|layer3_primary_planningdocs/decisions/ADR-004_ANALYST_INSIGHT_TO_APS_HANDOFF_STRATEGY.md|Canonical package first, APS adapter later|6-30`
- `P|layer3_primary_planningdocs/decisions/ADR-007_FIRST_APS_HANDOFF_TRANCHE.md|Evidence-bundle-family level is the first APS-facing tranche|6-44`

Repo-local anchors used most directly:
- `R|backend/app/models/models.py|L3 output package durability and package_kind uniqueness|943-953`
- `R|backend/app/services/layer3_package_entry.py|Current Gate D package kinds, refs, and handoff-blocked posture|43-84`
- `R|backend/app/services/layer3_package_entry.py|Current canonical handoff_status compatibility note|718-788`
- `R|backend/app/services/layer3_package_entry.py|Current output package persistence surface|1033-1054`
- `R|backend/app/services/nrc_aps_evidence_bundle_contract.py|Live APS evidence-bundle schema ids, checksum, and file naming helpers|14-22`
- `R|backend/app/services/nrc_aps_evidence_bundle_contract.py|Live APS checksum and file naming helpers|111-131`
- `R|backend/app/services/nrc_aps_evidence_bundle.py|Live APS persisted bundle load and validation surface|36-129`
- `R|backend/app/services/nrc_aps_evidence_bundle.py|Live APS bundle assembly and persist surface|466-605`
- `R|backend/app/services/nrc_aps_evidence_bundle_gate.py|Live APS evidence-bundle gate and fail-closed validation surface|1-120`
