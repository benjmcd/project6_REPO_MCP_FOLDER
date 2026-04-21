# 19 GateD APS Deterministic Challenge Freeze

## Purpose and authority note

This document freezes the bounded deterministic APS continuation immediately after the now-landed `aps_deterministic_insight_artifact_handoff` milestone.
It answers one question only:
- which exact deterministic APS family should continue next after the landed `aps_deterministic_insight_artifact_handoff` slice, without reopening review-packet/validate-only families, route/UI, runtime DB, schema, or earlier APS truth

It is not:
- a deterministic challenge implementation lane
- a deterministic challenge review-packet or validate-only expansion lane
- a deterministic insight widening lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
4. `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
5. `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
6. `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
7. `14_GATED_APS_MULTISOURCE_FREEZE.md`
8. `13_GATED_APS_CONTEXT_FREEZE.md`
9. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
10. `11_GATED_APS_REPORT_FREEZE.md`
11. `10_GATED_APS_CITATION_FREEZE.md`
12. `09_GATED_APS_HANDOFF_FREEZE.md`
13. historical Phase 1A REV1 artifacts as context only

Current merged-state note:
- current `main` now includes the bounded `aps_deterministic_insight_artifact_handoff` slice rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
- current `main` now also includes the narrow deterministic-gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`, and that landed lane still keeps one persisted deterministic insight artifact as the immediate downstream source boundary
- current `main` already has the live deterministic challenge runtime, contract, and validate-only gate surfaces rooted in `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, and `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`
- current `main` already has run-level report-ref registry buckets for deterministic challenge and deterministic challenge review packet in `backend/app/services/connectors_sciencebase.py`
- current `main` now also includes this read-only freeze selecting `deterministic_challenge_artifact` as the exact next deterministic APS family after the landed deterministic insight handoff
- current branch now also carries open PR `#130` for the bounded deterministic challenge handoff slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py`, plus narrow deterministic challenge gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`; that open lane has not landed on current `main` yet

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md|artifact|current governing freeze for the landed deterministic insight boundary`; `R|backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py|Current bounded deterministic insight handoff owner surface on current \`main\`|1-313`; `R|backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py|Current bounded deterministic insight handoff proof surface on current \`main\`|1-428`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph places deterministic challenge immediately after deterministic insight and before deterministic challenge review packet and validate-only gates|38-40;65-68;85-87;106-109`; `R|backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py|Current bounded deterministic challenge handoff owner surface on current branch for open PR \`#130\`|31-341`; `R|backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py|Live deterministic challenge contract is a single-insight deterministic rules-only family with frozen check specs and payload builder|11-20;76-126;228-240;344-370`; `R|backend/app/services/nrc_aps_deterministic_challenge_artifact.py|Live deterministic challenge runtime loads one persisted insight artifact, derives a deterministic challenge artifact, and persists or validates it fail-closed|47-84;123-283;347-481`; `R|backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py|Current deterministic challenge gate hardening surface on current branch for open PR \`#130\`|27-260`; `R|backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py|Current bounded deterministic challenge handoff proof surface on current branch for open PR \`#130\`|46-491`; `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry already reserves deterministic challenge and deterministic challenge review packet buckets|2959-2961`

## Frozen tranche

The bounded APS deterministic continuation is frozen as:
- `Gate D APS deterministic challenge continuation slice = one read-only freeze selecting deterministic_challenge_artifact as the exact next deterministic APS family after the landed deterministic insight handoff milestone`
- keep the already-landed `aps_deterministic_insight_artifact_handoff` row as the immediate upstream truth
- this freeze itself does not admit deterministic challenge implementation, deterministic challenge review packet, validate-only gates, route/UI, runtime DB, or schema widening
- do not reinterpret the landed deterministic insight handoff as permission to widen directly into later deterministic families
- if any later continuation cannot stay inside the live deterministic challenge contract plus the landed deterministic insight boundary, reopen the freeze instead of improvising

Hard rule:
- do not skip directly from `deterministic_insight_artifact` to `deterministic_challenge_review_packet` or `validate_only_gates`

## Canonical starting point

Read these surfaces first:

1. `Current landed deterministic insight boundary`
- `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`

2. `Next deterministic consumer family`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/connectors_sciencebase.py`

Frozen reading of that starting point:
- current `main` now proves the bounded deterministic insight handoff and its persisted `aps.deterministic_insight_artifact.v1` artifact boundary
- the live deterministic challenge family already derives one deterministic artifact from one persisted deterministic insight artifact under a fixed ruleset and fail-closed gate
- the live downstream graph still places deterministic challenge immediately after deterministic insight and before challenge-review-packet and validate-only gates
- the run-level report-ref registry already has deterministic challenge and review-packet buckets, so the next continuation does not need a new registry family to exist
- therefore `deterministic_challenge_artifact` is the exact next APS family to freeze after the landed deterministic insight boundary

## Frozen GateD APS deterministic-challenge decisions

### 1. Exact next deterministic-family choice

The exact next continuation admitted by this freeze is:
- `deterministic_challenge_artifact` as the next deterministic APS family after the landed `aps_deterministic_insight_artifact_handoff` slice
- deterministic challenge review packet and validate-only gates remain later

Frozen target rule:
- the next deterministic APS freeze after the landed deterministic insight handoff is now settled in favor of `deterministic_challenge_artifact`
- do not reopen that ordering unless repo truth changes on the live downstream graph or deterministic challenge contract surfaces
- do not treat this read-only freeze as proof that any Layer 3 deterministic challenge handoff has landed on current `main`

### 2. Source-boundary rule

The bounded deterministic challenge continuation frozen here must preserve:
- the landed deterministic insight handoff as the immediate Layer 3 source boundary for this tranche
- one persisted `aps.deterministic_insight_artifact.v1` artifact as the live deterministic challenge source
- the existing deterministic rules-only runtime posture

Frozen source rule:
- the later write-enabled lane must source from the persisted deterministic insight artifact emitted by `aps_deterministic_insight_artifact_handoff`
- do not bypass the deterministic insight boundary by sourcing directly from `context_dossier`, export-derived context packets, package-derived context packets, or export-package artifacts in this tranche
- do not reopen `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, or `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py` in this read-only freeze

### 3. Expected bounded implementation posture

The expected owner/proof posture admitted after this freeze is:
- a new bounded Layer 3 deterministic challenge handoff surface rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py`
- focused proof rooted in `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`
- reuse of the live deterministic challenge contract/runtime/gate boundary in `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, and `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`

Frozen implementation rule for the later write-enabled lane admitted after this freeze:
- admit one deterministic challenge artifact from one persisted deterministic insight handoff package on current `main`
- reuse the existing deterministic ruleset and validate-only gate rather than widening deterministic semantics
- keep `backend/app/models/models.py`, migrations, route/UI, runtime DB writes, and later deterministic families out

### 4. Why deterministic challenge review packet is not next

Frozen reason deterministic challenge review packet is not the next APS family:
- the live downstream graph still places `deterministic_challenge_review_packet` after `deterministic_challenge_artifact`
- the live review-packet family derives from the persisted deterministic challenge artifact, not directly from the persisted insight artifact
- selecting review packet next would skip the immediate deterministic boundary that already exists in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- direct edits to `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, or `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py` in this read-only lane
- deterministic challenge review packet and validate-only families
- route/UI widening
- runtime DB writes or migrations
- schema widening

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`
- direct deterministic challenge, deterministic challenge review-packet, or validate-only implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- sourcing deterministic challenge directly from anything other than the landed deterministic insight handoff boundary
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, or `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py` without a repo-confirmed blocker
- skipping straight to deterministic challenge review packet or validate-only expansion
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This landed read-only freeze on current `main` is the governing carried-forward contract for the bounded choice of `deterministic_challenge_artifact` as the next APS family after the landed deterministic insight boundary.

Reason:
- current `main` already proves the bounded deterministic insight handoff and its persisted deterministic insight artifact boundary
- repo truth already contains the deterministic challenge contract/runtime/gate family and report-ref registry buckets
- the live downstream graph still places deterministic challenge before challenge review-packet and validate-only
- this read-only freeze therefore settles the next deterministic-family choice narrowly without admitting implementation

What still remains intentionally deferred after this now-landed read-only freeze:
- the later write-enabled deterministic challenge handoff lane is now open on PR `#130` but not yet landed on current `main`
- deterministic challenge review-packet fan-out
- validate-only top-chain expansion
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md|artifact|current governing freeze for the landed deterministic insight boundary`
- `R|backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py|Current bounded deterministic insight handoff owner surface on current \`main\`|1-313`
- `R|backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py|Current bounded deterministic insight handoff proof surface on current \`main\`|1-428`
- `R|backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py|Current bounded deterministic challenge handoff owner surface on current branch for open PR \`#130\`|31-341`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph places deterministic challenge immediately after deterministic insight and before deterministic challenge review packet and validate-only gates|38-40;65-68;85-87;106-109`
- `R|backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py|Live deterministic challenge contract is a single-insight deterministic rules-only family with frozen check specs and payload builder|11-20;76-126;228-240;344-370`
- `R|backend/app/services/nrc_aps_deterministic_challenge_artifact.py|Live deterministic challenge runtime loads one persisted insight artifact, derives a deterministic challenge artifact, and persists or validates it fail-closed|47-84;123-283;347-481`
- `R|backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py|Current deterministic challenge gate hardening surface on current branch for open PR \`#130\`|27-260`
- `R|backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py|Current bounded deterministic challenge handoff proof surface on current branch for open PR \`#130\`|46-491`
- `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry already reserves deterministic challenge and deterministic challenge review packet buckets|2959-2961`
