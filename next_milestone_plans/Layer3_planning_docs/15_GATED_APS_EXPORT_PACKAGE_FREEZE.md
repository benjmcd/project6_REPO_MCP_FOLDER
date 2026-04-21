# 15 GateD APS Export Package Freeze

## Purpose and authority note

This document freezes the bounded first shared APS consumer choice after the already-landed same-run multisource admission slice.
It answers one question only:
- which exact later shared APS family should consume the now-landed multisource seam first, without reopening route/UI, runtime DB, schema, earlier APS handoff truth, or later dossier/deterministic fan-out

It is not:
- an `evidence_report_export_package` implementation lane
- a package-derived context-packet implementation lane
- a `context_dossier`, deterministic, or review-packet lane
- a report-export or context-packet widening lane
- a model or migration lane
- a route/UI lane
- a runtime DB integration lane

Applied authority order for this document:
1. current repo truth in this worktree
2. the active repo-local REV2 Phase 1A control spine
3. `14_GATED_APS_MULTISOURCE_FREEZE.md`
4. `13_GATED_APS_CONTEXT_FREEZE.md`
5. `12_GATED_APS_REPORT_EXPORT_FREEZE.md`
6. `11_GATED_APS_REPORT_FREEZE.md`
7. `10_GATED_APS_CITATION_FREEZE.md`
8. `09_GATED_APS_HANDOFF_FREEZE.md`
9. `08_GATED_PACKAGE_FREEZE.md`
10. historical Phase 1A REV1 artifacts as context only

Current branch note:
- this branch now also carries the bounded write-enabled export-package handoff slice rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- that implementation remains branch-local, is governed by this freeze, and is not yet landed on current `main`

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md|artifact|bounded shared-source admission contract already landed on current \`main\``; `R|backend/app/services/layer3_aps_multisource.py|Current bounded multisource owner surface proves same-run grouping on current durable seams|105-435`; `R|backend/tests/test_layer3_aps_multisource.py|Current bounded multisource proof covers success and fail-closed source boundaries|166-307`; `R|backend/app/services/nrc_aps_evidence_report_export_package_contract.py|Live export-package family requires at least two source exports and rejects incompatible inputs|17-18;75-76;216-216`; `R|backend/app/services/nrc_aps_evidence_report_export_package.py|Live export-package persist path mutates run refs on persist|501-582`; `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet contract accepts package source family and package selectors|22-28;145-148;181-183`; `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family requires paired packets and compatible objective plus source-family posture|18-32;166-174;237-282`; `R|backend/app/services/nrc_aps_context_dossier.py|Live context-dossier persist path mutates run refs|580-625`; `R|backend/app/services/review_nrc_aps_graph.py|Downstream shared graph places export_package before package-derived context and before context_dossier|33-37;58-64`

## Frozen tranche

The bounded APS export-package continuation is frozen as:
- `Gate D APS export-package continuation slice = one read-only freeze that selects evidence_report_export_package as the first downstream shared APS consumer of the already-landed multisource seam`
- keep the already-landed `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, `aps_evidence_report_export_handoff`, `aps_context_packet_handoff`, and `aps_multisource_admission` rows as the already-proven upstream truth
- this freeze itself does not admit direct `evidence_report_export_package` implementation; the current branch's bounded handoff lane is a separate write-enabled slice governed by this freeze
- do not admit package-derived context-packet, `context_dossier`, deterministic, review-packet, route/UI, runtime DB, or schema widening in this tranche
- if the bounded branch-local write-enabled lane cannot stay inside the already-landed multisource seam plus the live export-package contract boundary, reopen the freeze instead of improvising

Hard rule:
- do not reinterpret this freeze as permission to widen directly into export-package implementation, package-derived context, context-dossier, deterministic, review-packet, route/UI, runtime DB, or schema work

## Canonical starting point

Read these surfaces first:

1. `Current landed shared-source seam`
- `backend/app/services/layer3_aps_multisource.py`
- `backend/tests/test_layer3_aps_multisource.py`

2. `First selected shared APS consumer family`
- `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

3. `Downstream consumers of that selected family`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/nrc_aps_context_dossier_contract.py`
- `backend/app/services/nrc_aps_context_dossier.py`
- `backend/app/services/review_nrc_aps_graph.py`

Frozen reading of that starting point:
- the multisource seam is now already proven on current `main` using existing `co_retrieval_group_id` plus APS source identity without schema widening
- `evidence_report_export_package` is the first visible shared APS family in the live graph after paired branch exports
- package-derived context packets consume `evidence_report_export_package` directly through the live context-packet contract
- `context_dossier` sits further downstream of two export-derived context packets and should not skip the first shared-family freeze
- both live shared APS families still mutate `ConnectorRun.query_plan_json` on persist
- therefore this freeze selects family order only; it does not admit runtime-write implementation of the selected family

## Frozen GateD APS export-package decisions

### 1. Exact next shared-family choice

The exact next continuation admitted by this freeze is:
- `evidence_report_export_package` as the first downstream shared APS consumer of the already-landed multisource seam
- `context_dossier` remains later and must not be used to skip the earlier export-package boundary

Frozen target rule:
- the first later shared-family freeze after multisource is now settled in favor of `evidence_report_export_package`
- do not reopen that ordering unless repo truth changes on the live downstream graph or contract surfaces
- do not treat this selection freeze as proof that export-package implementation has landed on current `main`

### 2. Current write-enabled lane posture

Current owner/proof posture for the bounded branch-local write-enabled lane:
- `backend/app/services/layer3_aps_report_export_package_handoff.py`
- `backend/tests/test_layer3_aps_report_export_package_handoff.py`

Frozen implementation rule for the bounded branch-local write-enabled lane:
- source only from already-landed `aps_multisource_admission` truth and already-landed report-export refs
- reuse the live `nrc_aps_evidence_report_export_package` contract/load/gate boundary without direct edits unless a repo-confirmed blocker forces a reopened freeze
- keep `backend/app/models/models.py`, migrations, route/UI, runtime DB writes, and downstream package-derived-context or dossier fan-out out

### 3. Why dossier is not first

Frozen reason dossier is not the first shared-family choice:
- the live graph places `export_package` before package-derived context packets and before the dossier-fed deterministic chain
- the live dossier contract depends on paired context packets with compatible `objective` plus `source_family`
- selecting dossier first would skip the earlier shared-family boundary that already exists in live repo truth

### 4. Explicitly deferred downstream families

This freeze keeps deferred:
- direct edits to the shared `nrc_aps_evidence_report_export_package*.py` surfaces beyond the bounded handoff lane
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
- edits to `backend/app/services/nrc_aps_context_packet_contract.py`
- edits to `backend/app/services/nrc_aps_context_dossier_contract.py`
- edits to `backend/app/services/nrc_aps_context_dossier.py`
- package-derived context-packet implementation
- direct `context_dossier`, deterministic, or review-packet implementation
- route/schema/page changes
- runtime DB writes or runtime DB migrations

## Stop conditions

Stop and reopen the freeze instead of improvising if the bounded branch-local write lane requires:
- edits to `backend/app/models/models.py`
- a new migration
- a grouping mechanism beyond the already-landed multisource seam
- direct edits to `backend/app/services/nrc_aps_evidence_report_export_package_contract.py` or `backend/app/services/nrc_aps_evidence_report_export_package.py` without a repo-confirmed blocker
- skipping straight to package-derived context-packet, `context_dossier`, deterministic, or review-packet implementation
- route, schema, or page changes
- runtime DB writes or runtime DB migrations

## Concise readiness judgment

Readiness judgment:
- This freeze is the governing carried-forward contract now landed on current `main` for the bounded choice of `evidence_report_export_package` as the first downstream shared APS consumer beyond the already-landed multisource slice. Current branch state now also carries the bounded `aps_evidence_report_export_package_handoff` implementation slice rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`; that slice remains branch-local.

Reason:
- the already-landed multisource slice resolved the shared same-run source-admission seam on current durable Layer 3 surfaces
- repo truth shows `export_package` is the first visible shared APS family after paired branch exports
- repo truth also shows package-derived context packets consume `export_package`, while `context_dossier` remains further downstream of paired export-derived packets
- this now-landed freeze therefore settles the next shared-family choice narrowly without admitting implementation

What still remains intentionally deferred after the bounded branch-local handoff slice:
- direct edits to the shared `nrc_aps_evidence_report_export_package*.py` surfaces beyond the bounded handoff lane
- package-derived context-packet fan-out
- direct `context_dossier`, deterministic, and review-packet fan-out
- the future workbench route family
- broader qualitative, hybrid, cross-modal, and comparative execution breadth

## Evidence appendix

Repo-local anchors used most directly:
- `A|next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md|artifact|bounded shared-source admission contract already landed on current \`main\``
- `R|backend/app/services/layer3_aps_multisource.py|Current bounded multisource owner surface proves same-run grouping on current durable seams|105-435`
- `R|backend/tests/test_layer3_aps_multisource.py|Current bounded multisource proof covers success and fail-closed source boundaries|166-307`
- `R|backend/app/services/nrc_aps_evidence_report_export_package_contract.py|Live export-package family requires at least two source exports and rejects incompatible inputs|17-18;75-76;216-216`
- `R|backend/app/services/nrc_aps_evidence_report_export_package.py|Live export-package persist path mutates run refs on persist|501-582`
- `R|backend/app/services/nrc_aps_context_packet_contract.py|Live context-packet contract accepts package source family and package selectors|22-28;145-148;181-183`
- `R|backend/app/services/nrc_aps_context_dossier_contract.py|Live context-dossier family requires paired packets and compatible objective plus source-family posture|18-32;166-174;237-282`
- `R|backend/app/services/nrc_aps_context_dossier.py|Live context-dossier persist path mutates run refs|580-625`
- `R|backend/app/services/review_nrc_aps_graph.py|Downstream shared graph places export_package before package-derived context and before context_dossier|33-37;58-64`
