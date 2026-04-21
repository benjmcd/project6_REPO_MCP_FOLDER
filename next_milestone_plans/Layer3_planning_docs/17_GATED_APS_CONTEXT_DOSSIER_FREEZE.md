# 17 GateD APS Context Dossier Freeze

## Purpose and authority note

This document freezes the bounded later shared APS continuation immediately after the now-landed package-derived context handoff milestone.
It answers one question only:
- which exact later shared APS family should continue next after the now-landed `aps_context_packet_package_handoff` slice, without reopening route/UI, runtime DB, schema, earlier APS truth, or deterministic fan-out

It is not:
- a `context_dossier` implementation lane
- a deterministic, review-packet, or validate-only expansion lane
- a package-derived context widening lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
4. `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
5. `14_GATED_APS_MULTISOURCE_FREEZE.md`
6. `13_GATED_APS_CONTEXT_FREEZE.md`
7. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
8. `11_GATED_APS_REPORT_FREEZE.md`
9. `10_GATED_APS_CITATION_FREEZE.md`
10. `09_GATED_APS_HANDOFF_FREEZE.md`
11. historical Phase 1A REV1 artifacts as context only

Current-state note:
- current `main` now includes the bounded export-derived `aps_context_packet_handoff` slice rooted in `backend/app/services/layer3_aps_context_packet_handoff.py` and `backend/tests/test_layer3_aps_context_packet_handoff.py`
- current `main` now also includes the bounded package-derived `aps_context_packet_package_handoff` slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- current `main` also now includes the malformed-scoped fail-closed APS gate hardening follow-up in `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, `backend/app/services/nrc_aps_context_packet_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, and `backend/tests/test_layer3_aps_context_packet_handoff.py`
- current `main` now includes this read-only freeze selecting `context_dossier` as the next later shared APS family after the landed package-context milestone, while preserving paired export-derived context packets as the live dossier input branch
- current `main` now also includes the bounded `aps_context_dossier_handoff` slice rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`; it uses `aps_context_packet_package_handoff` only as gating provenance to recover the paired persisted export-derived context packets required by the live dossier contract
- current `main` now also includes the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`, because the live dossier gate had the same sanitized filename-scope collision risk already proven and fixed in the adjacent export, export-package, and context-packet gates; that hardening remains fail-closed and does not widen later deterministic families by itself
- open PR `#124` now also carries the read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze selecting `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary; it has not landed on current `main` yet

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md|artifact|current governing freeze for the landed package-context boundary`; `R|backend/app/services/layer3_aps_context_packet_handoff.py|Current bounded export-derived context handoff owner surface on current \`main\`|29-276`; `R|backend/tests/test_layer3_aps_context_packet_handoff.py|Current bounded export-derived context handoff proof surface on current \`main\`|124-302`; `R|backend/app/services/layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff owner surface on current \`main\`|31-277`; `R|backend/tests/test_layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff proof surface on current \`main\`|38-230`; `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet contract still separates export and package source families|22-29;145-148;181-183`; `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family requires two compatible source packets and one source_family|18-32;237-282`; `R|backend/app/services/nrc_aps_context_dossier.py|Live context-dossier runtime resolves persisted context packets and persists dossier artifacts without changing the source-family compatibility rule|427-520`; `R|backend/app/services/nrc_aps_context_dossier_gate.py|Live dossier gate validates persisted context-packet refs and now also hardens exact owner-run filtering under sanitized filename-scope collisions on current \`main\`|85-308`; `R|backend/app/services/layer3_aps_context_dossier_handoff.py|Current bounded dossier handoff owner surface on current \`main\`|1-427`; `R|backend/tests/test_layer3_aps_context_dossier_handoff.py|Current bounded dossier handoff proof surface on current \`main\`|1-326`; `R|backend/app/services/review_nrc_aps_graph.py|Live downstream shared graph routes context_dossier from paired export-derived context packets and leaves deterministic after dossier|33-37;63-68;104-109`

## Frozen tranche

The bounded APS context-dossier continuation is frozen as:
- `Gate D APS context-dossier continuation slice = one read-only freeze selecting context_dossier as the exact next later shared APS family after the landed package-context milestone`
- keep the already-landed `aps_context_packet_handoff`, `aps_multisource_admission`, `aps_evidence_report_export_package_handoff`, and `aps_context_packet_package_handoff` rows as already-proven upstream truth
- this freeze itself does not admit `context_dossier` implementation, deterministic, route/UI, runtime DB, or schema widening
- do not reinterpret the now-landed package-derived context lane as dossier input proof
- if any later continuation cannot stay inside the live dossier contract plus the export-derived context-packet branch, reopen the freeze instead of improvising

Hard rule:
- do not collapse export-derived and package-derived context branches into one undifferentiated dossier input lane

## Canonical starting point

Read these surfaces first:

1. `Current landed context-packet boundaries`
- `backend/app/services/layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- `backend/app/services/nrc_aps_context_packet_contract.py`

2. `Next later shared APS consumer family`
- `backend/app/services/nrc_aps_context_dossier_contract.py`
- `backend/app/services/nrc_aps_context_dossier.py`
- `backend/app/services/nrc_aps_context_dossier_gate.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- current `main` now proves both the export-derived and package-derived context-packet handoff branches
- the live dossier contract still requires at least two persisted context packets with compatible owner run, projection contract, fact grammar contract, objective, and source family
- the live downstream graph still routes `context_dossier` from paired export-derived context packets, not from `context_packet_package`
- therefore `context_dossier` is the next later shared APS family to freeze after the landed package-context milestone, but its live input branch remains paired export-derived context packets rather than the package-derived context handoff branch

## Frozen GateD APS context-dossier decisions

### 1. Exact next later shared-family choice

The exact next continuation admitted by this freeze is:
- `context_dossier` as the next later shared APS family after the landed package-context milestone
- deterministic fan-out remains later and must not be used to skip the dossier boundary

Frozen target rule:
- the next later shared APS freeze after the landed package-context handoff is now settled in favor of `context_dossier`
- do not reopen that ordering unless repo truth changes on the live downstream graph or dossier contract surfaces
- do not treat this read-only freeze as proof that `context_dossier` implementation has landed on current `main`

### 2. Source-branch rule

The bounded dossier continuation frozen here must preserve:
- paired export-derived context packets as the dossier input branch for this tranche
- the live dossier compatibility rule that all source packets share one compatible `source_family`
- the separation between export-derived and package-derived context branches

Frozen source rule:
- do not source dossier from `aps_context_packet_package_handoff` in this tranche
- do not reopen `backend/app/services/nrc_aps_context_packet_contract.py`, `backend/app/services/nrc_aps_context_dossier_contract.py`, or `backend/app/services/nrc_aps_context_dossier.py` in this read-only freeze

### 3. Expected bounded implementation posture

The expected owner/proof posture admitted after this freeze, and now proven on current `main`, is:
- a new bounded Layer 3 dossier handoff surface rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py`
- focused proof rooted in `backend/tests/test_layer3_aps_context_dossier_handoff.py`
- reuse of the live dossier contract/runtime/gate boundary in `backend/app/services/nrc_aps_context_dossier_contract.py`, `backend/app/services/nrc_aps_context_dossier.py`, and `backend/app/services/nrc_aps_context_dossier_gate.py`

Frozen implementation rule for the later write-enabled lane admitted after this freeze:
- source only from already-persisted export-derived `aps_context_packet_handoff` artifacts on current `main`
- preserve the live dossier compatibility rule instead of widening source-family acceptance
- keep `backend/app/models/models.py`, migrations, route/UI, runtime DB writes, and deterministic/review-packet fan-out out

### 4. Why deterministic is not next

Frozen reason deterministic is not the next shared-family choice:
- the live graph still places `context_dossier` before every deterministic family
- the live dossier contract remains the compatibility and composition boundary immediately before deterministic
- selecting deterministic next would skip the unresolved dossier boundary that already exists in live repo truth

### 5. Explicitly deferred downstream families

This freeze keeps deferred:
- direct edits to the shared `nrc_aps_context_dossier*.py` runtime surfaces beyond this read-only freeze
- deterministic-insight, deterministic-challenge, and review-packet families
- validate-only top-chain widening
- route/UI widening
- runtime DB writes or migrations
- schema widening

## Explicit non-goals

This freeze does not admit:
- edits to `backend/app/models/models.py`
- a new migration
- edits to `backend/app/services/nrc_aps_context_packet_contract.py`
- edits to `backend/app/services/nrc_aps_context_dossier_contract.py`
- edits to `backend/app/services/nrc_aps_context_dossier.py`
- edits to `backend/app/services/nrc_aps_context_dossier_gate.py`
- direct `context_dossier`, deterministic, or review-packet implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if a later continuation requires:
- edits to `backend/app/models/models.py`
- a new migration
- direct dossier sourcing from `aps_context_packet_package_handoff`
- collapsing export-derived and package-derived context branches into one dossier input lane
- direct edits to `backend/app/services/nrc_aps_context_packet_contract.py`, `backend/app/services/nrc_aps_context_dossier_contract.py`, `backend/app/services/nrc_aps_context_dossier.py`, or `backend/app/services/nrc_aps_context_dossier_gate.py` without a repo-confirmed blocker
- skipping straight to deterministic, review-packet, or validate-only expansion
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This freeze is the governing carried-forward contract on current `main` for the bounded choice of `context_dossier` as the next later shared APS family after the landed package-context milestone.

Reason:
- current `main` already proves both the export-derived and package-derived context branches
- repo truth still routes dossier from paired export-derived context packets
- the live dossier contract still enforces a single compatible source-family posture across all source packets
- this landed read-only freeze therefore settles the next later shared-family choice narrowly without admitting implementation

What still remains intentionally deferred after this landed read-only freeze:
- the open read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze on PR `#124` has not landed on current `main` yet
- deterministic insight implementation on current `main`
- deterministic and review-packet fan-out
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md|artifact|current governing freeze for the landed package-context boundary`
- `R|backend/app/services/layer3_aps_context_packet_handoff.py|Current bounded export-derived context handoff owner surface on current \`main\`|29-276`
- `R|backend/tests/test_layer3_aps_context_packet_handoff.py|Current bounded export-derived context handoff proof surface on current \`main\`|124-302`
- `R|backend/app/services/layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff owner surface on current \`main\`|31-277`
- `R|backend/tests/test_layer3_aps_context_packet_package_handoff.py|Current bounded package-derived context handoff proof surface on current \`main\`|38-230`
- `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet contract still separates export and package source families|22-29;145-148;181-183`
- `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family requires two compatible source packets and one source_family|18-32;237-282`
- `R|backend/app/services/nrc_aps_context_dossier.py|Live context-dossier runtime resolves persisted context packets and persists dossier artifacts without changing the source-family compatibility rule|427-520`
- `R|backend/app/services/nrc_aps_context_dossier_gate.py|Live dossier gate validates persisted context-packet refs and preserved compatible source-family derivation|85-213`
- `R|backend/app/services/review_nrc_aps_graph.py|Live downstream shared graph routes context_dossier from paired export-derived context packets and leaves deterministic after dossier|33-37;63-68;104-109`
