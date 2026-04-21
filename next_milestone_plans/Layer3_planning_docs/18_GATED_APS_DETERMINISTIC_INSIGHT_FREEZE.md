# 18 GateD APS Deterministic Insight Freeze

## Purpose and authority note

This document freezes the bounded deterministic APS continuation immediately after the now-landed `aps_context_dossier_handoff` milestone.
It answers one question only:
- which exact deterministic APS family should continue next after the landed `aps_context_dossier_handoff` slice, without reopening challenge/review-packet/validate-only families, route/UI, runtime DB, schema, or earlier APS truth

It is not:
- a deterministic insight implementation lane
- a deterministic challenge, review-packet, or validate-only expansion lane
- a dossier widening lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
4. `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
5. `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
6. `14_GATED_APS_MULTISOURCE_FREEZE.md`
7. `13_GATED_APS_CONTEXT_FREEZE.md`
8. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
9. `11_GATED_APS_REPORT_FREEZE.md`
10. `10_GATED_APS_CITATION_FREEZE.md`
11. `09_GATED_APS_HANDOFF_FREEZE.md`
12. historical Phase 1A REV1 artifacts as context only

Current-state note:
- current `main` now includes the bounded `aps_context_dossier_handoff` slice rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`
- current `main` now also includes the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`, and that landed lane still keeps paired export-derived context packets as dossier inputs
- current `main` already has the live deterministic insight runtime, contract, and validate-only gate surfaces rooted in `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, and `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- current `main` already has run-level report-ref registry buckets for deterministic insight, deterministic challenge, and deterministic challenge review packet in `backend/app/services/connectors_sciencebase.py`
- current `main` now also includes this read-only freeze selecting `deterministic_insight_artifact` as the exact next deterministic APS family after the landed dossier handoff

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md|artifact|current governing freeze for the landed dossier boundary`; `R|backend/app/services/layer3_aps_context_dossier_handoff.py|Current bounded dossier handoff owner surface on current \`main\`|323-427`; `R|backend/tests/test_layer3_aps_context_dossier_handoff.py|Current bounded dossier handoff proof surface on current \`main\`|1-326`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph places deterministic insight immediately after context_dossier and before challenge/review packet/validate-only|37-41;65-68;84-88;106-109`; `R|backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py|Live deterministic insight contract is a single-dossier deterministic rules-only family with frozen rule specs and payload builder|11-20;67-104;201-209;436-460`; `R|backend/app/services/nrc_aps_deterministic_insight_artifact.py|Live deterministic insight runtime loads one persisted dossier, derives a deterministic artifact, and persists or validates it fail-closed|60-92;374-428;491-500`; `R|backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py|Live deterministic insight gate is validate-only and recomputes the deterministic artifact from the persisted dossier|16-18;87-199`; `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry already reserves deterministic insight/challenge/review packet buckets|2947-2961`

## Frozen tranche

The bounded APS deterministic continuation is frozen as:
- `Gate D APS deterministic insight continuation slice = one read-only freeze selecting deterministic_insight_artifact as the exact next deterministic APS family after the landed context_dossier handoff milestone`
- keep the already-landed `aps_context_dossier_handoff` row as the immediate upstream truth
- this freeze itself does not admit deterministic insight implementation, deterministic challenge, deterministic challenge review packet, validate-only gates, route/UI, runtime DB, or schema widening
- do not reinterpret the landed dossier handoff as permission to widen directly into later deterministic families
- if any later continuation cannot stay inside the live deterministic insight contract plus the landed dossier boundary, reopen the freeze instead of improvising

Hard rule:
- do not skip directly from `context_dossier` to `deterministic_challenge_artifact` or `deterministic_challenge_review_packet`

## Canonical starting point

Read these surfaces first:

1. `Current landed dossier boundary`
- `backend/app/services/layer3_aps_context_dossier_handoff.py`
- `backend/tests/test_layer3_aps_context_dossier_handoff.py`
- `backend/app/services/nrc_aps_context_dossier_contract.py`
- `backend/app/services/nrc_aps_context_dossier.py`
- `backend/app/services/nrc_aps_context_dossier_gate.py`

2. `Next deterministic consumer family`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/connectors_sciencebase.py`

Frozen reading of that starting point:
- current `main` now proves the bounded dossier handoff and its persisted `aps.context_dossier.v1` artifact boundary
- the live deterministic insight family already derives one deterministic artifact from one persisted dossier under a fixed ruleset and fail-closed gate
- the live downstream graph still places deterministic insight immediately after dossier and before challenge/review-packet/validate-only
- the run-level report-ref registry already has deterministic-family buckets, so the next continuation does not need a new registry family to exist
- therefore `deterministic_insight_artifact` is the exact next APS family to freeze after the landed dossier boundary

## Frozen GateD APS deterministic-insight decisions

### 1. Exact next deterministic-family choice

The exact next continuation admitted by this freeze is:
- `deterministic_insight_artifact` as the next deterministic APS family after the landed `aps_context_dossier_handoff` slice
- deterministic challenge, deterministic challenge review packet, and validate-only gates remain later

Frozen target rule:
- the next deterministic APS freeze after the landed dossier handoff is now settled in favor of `deterministic_insight_artifact`
- do not reopen that ordering unless repo truth changes on the live downstream graph or deterministic insight contract surfaces
- do not treat this read-only freeze as proof that any Layer 3 deterministic insight handoff has landed on current `main`

### 2. Source-boundary rule

The bounded deterministic insight continuation frozen here must preserve:
- the landed dossier handoff as the immediate Layer 3 source boundary for this tranche
- one persisted `aps.context_dossier.v1` artifact as the live deterministic insight source
- the existing deterministic rules-only runtime posture

Frozen source rule:
- the later write-enabled lane must source from the persisted dossier artifact emitted by `aps_context_dossier_handoff`
- do not bypass the dossier boundary by sourcing directly from export-derived context packets, package-derived context packets, or export-package artifacts in this tranche
- do not reopen `backend/app/services/nrc_aps_context_dossier_contract.py`, `backend/app/services/nrc_aps_context_dossier.py`, or `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py` in this read-only freeze

### 3. Expected bounded implementation posture

The expected owner/proof posture admitted after this freeze is:
- a new bounded Layer 3 deterministic insight handoff surface rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`
- focused proof rooted in `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
- reuse of the live deterministic insight contract/runtime/gate boundary in `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, and `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`

Frozen implementation rule for the later write-enabled lane admitted after this freeze:
- admit one deterministic insight artifact from one persisted dossier handoff package on current `main`
- reuse the existing deterministic ruleset and validate-only gate rather than widening deterministic semantics
- keep `backend/app/models/models.py`, migrations, route/UI, runtime DB writes, and later deterministic families out

### 4. Why deterministic challenge is not next

Frozen reason deterministic challenge is not the next APS family:
- the live downstream graph still places `deterministic_challenge_artifact` after `deterministic_insight_artifact`
- the live challenge family derives from the persisted deterministic insight artifact, not directly from the dossier
- selecting challenge next would skip the immediate deterministic boundary that already exists in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, or `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py` in this read-only lane
- deterministic challenge, deterministic challenge review packet, and validate-only families
- route/UI widening
- runtime DB writes or migrations
- schema widening

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- direct edits to `backend/app/services/nrc_aps_context_dossier_contract.py`
- direct edits to `backend/app/services/nrc_aps_context_dossier.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- direct edits to `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- direct deterministic insight, challenge, review-packet, or validate-only implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- sourcing deterministic insight directly from anything other than the landed dossier handoff boundary
- direct edits to `backend/app/services/nrc_aps_context_dossier_contract.py`, `backend/app/services/nrc_aps_context_dossier.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, or `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py` without a repo-confirmed blocker
- skipping straight to deterministic challenge, deterministic review packet, or validate-only expansion
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This now-landed read-only freeze on current `main` is the governing carried-forward contract for the bounded choice of `deterministic_insight_artifact` as the next APS family after the landed dossier handoff boundary.

Reason:
- current `main` already proves the bounded dossier handoff and its persisted dossier artifact boundary
- repo truth already contains the deterministic insight contract/runtime/gate family and report-ref registry buckets
- the live downstream graph still places deterministic insight before challenge/review-packet/validate-only
- this read-only freeze therefore settles the next deterministic-family choice narrowly without admitting implementation

What still remains intentionally deferred after this now-landed read-only freeze:
- Layer 3 deterministic insight handoff implementation on current `main`
- deterministic challenge and deterministic challenge review-packet fan-out
- validate-only top-chain expansion
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md|artifact|current governing freeze for the landed dossier boundary`
- `R|backend/app/services/layer3_aps_context_dossier_handoff.py|Current bounded dossier handoff owner surface on current \`main\`|323-427`
- `R|backend/tests/test_layer3_aps_context_dossier_handoff.py|Current bounded dossier handoff proof surface on current \`main\`|1-326`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream graph places deterministic insight immediately after context_dossier and before challenge/review packet/validate-only|37-41;65-68;84-88;106-109`
- `R|backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py|Live deterministic insight contract is a single-dossier deterministic rules-only family with frozen rule specs and payload builder|11-20;67-104;201-209;436-460`
- `R|backend/app/services/nrc_aps_deterministic_insight_artifact.py|Live deterministic insight runtime loads one persisted dossier, derives a deterministic artifact, and persists or validates it fail-closed|60-92;374-428;491-500`
- `R|backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py|Live deterministic insight gate is validate-only and recomputes the deterministic artifact from the persisted dossier|16-18;87-199`
- `R|backend/app/services/connectors_sciencebase.py|Current run-level report-ref registry already reserves deterministic insight/challenge/review packet buckets|2947-2961`
