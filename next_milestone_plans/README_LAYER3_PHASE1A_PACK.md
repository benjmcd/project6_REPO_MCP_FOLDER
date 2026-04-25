# Layer3 Phase1A Planning Pack

## Purpose

This file is the front door for the bounded Phase 1A Layer 3 planning and closure pack that was landed from `codex/layer3-lane` and is now carried forward on current `main`.

Use it to orient quickly across the three active pack directories:
- `next_milestone_plans/Layer3_planning_docs`
- `next_milestone_plans/Layer3_execution_handoff`
- `next_milestone_plans/Layer3_execution_freeze`

It also now points to the narrow post-Phase 1A Gate C entry-freeze bridge:
- `next_milestone_plans/Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`

And to the actual first Gate C implementation-entry freeze packet:
- `next_milestone_plans/Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`

And to the carried-forward Gate C plan/pass-entry freeze packet for the landed bounded plan/pass slice:
- `next_milestone_plans/Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`

And to the carried-forward Gate C quantitative associated/cohort continuation freeze packet for the landed bounded cohort slice:
- `next_milestone_plans/Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`

And to the carried-forward Gate D package-entry freeze packet for the landed bounded packaging/reconciliation entry slice:
- `next_milestone_plans/Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`

And to the carried-forward Gate D APS handoff freeze packet for the bounded first APS evidence-bundle-family handoff slice now landed on current `main`:
- `next_milestone_plans/Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md`

And to the carried-forward Gate D APS citation continuation freeze packet for the bounded citation-pack-family handoff slice now landed on current `main` after the landed evidence-bundle handoff:
- `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`

And to the carried-forward Gate D APS report continuation freeze packet for the bounded evidence-report-family continuation slice now landed on current `main` after the landed citation-pack handoff:
- `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`

And to the carried-forward Gate D APS report-export continuation freeze packet for the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the landed evidence-report handoff:
- `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`

And to the carried-forward Gate D APS context continuation freeze packet for the bounded export-derived context-packet slice now landed on current `main` beyond the landed evidence-report-export handoff:
- `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`

And to the carried-forward Gate D APS multisource continuation freeze packet for the bounded same-run shared-source admission boundary now landed on current `main` beyond the landed export-derived context-packet slice:
- `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`

And to the carried-forward Gate D APS export-package first shared-consumer freeze packet for the bounded now-landed choice of `evidence_report_export_package` as the first later shared APS family beyond the landed multisource slice on current `main`:
- `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`

And to the carried-forward Gate D APS package-derived-context continuation freeze packet now landed on current `main` for the bounded next shared APS family beyond the landed export-package boundary:
- `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`

And to the carried-forward Gate D APS context-dossier continuation freeze packet now landed on current `main` for the bounded next later shared APS family beyond the landed package-context boundary:
- `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`

And to the carried-forward Gate D APS deterministic-insight continuation freeze packet now landed on current `main` for the bounded first deterministic continuation beyond the landed dossier boundary:
- `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`

And to the carried-forward Gate D APS deterministic-challenge continuation freeze packet now landed on current `main` for the bounded next deterministic continuation beyond the landed deterministic-insight boundary:
- `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`

And to the carried-forward Gate D APS review-packet continuation freeze packet now landed on current `main` for the bounded next deterministic continuation beyond the landed deterministic-challenge boundary:
- `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`

And to the bounded Gate D APS review-packet handoff lane now landed on current `main` for the exact deterministic continuation beyond that landed review-packet freeze:
- `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`
- `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`
- `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`

And, on this branch only, to the Layer 3 workbench execution-readiness packet that must remain planning-only unless a later PR merges it:
- `next_milestone_plans/Layer3_planning_docs/36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`

And to the Gate D APS validate-only-gates continuation freeze packet now landed on current `main` for the bounded next verification continuation beyond the landed review-packet boundary:
- `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`

And to the Gate D APS dedicated validate-only runtime/report-ref continuation freeze packet now landed on current `main` from PR `#140` for the bounded next read-only decision beyond the landed generic gate-report refresh lane:
- `next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

This README is operational and navigational.
If it conflicts with the stronger frozen control docs, the control docs govern.

## Authority note

The active control docs in this pack use `P` citations whose path segment begins `layer3_primary_planningdocs/`.
Those citations point to the external canonical Layer 3 planning corpus at `C:\Users\benny\OneDrive\Desktop\Layer3\layer3_primary_planningdocs`.
Those source files are not tracked in this repo/worktree.
Treat them as external planning authority, not repo-local implementation truth.
Repo-local implementation truth still comes from the `R|...` repo paths cited in the pack.

## Current state

The lane now contains:
- the frozen Phase 1A planning baseline
- the execution handoff/control fence
- the implementation-local freeze docs
- the committed bounded Phase 1A code slice
- the committed postcode acceptance audit
- the pack-local roadmap, reconciliation, navigation, and concrete surface-map surfaces needed for bounded Phase 1A closure
- the narrow post-Phase 1A Gate C entry-freeze bridge that identified the blocker set before later Gate C slices could open safely
- the carried-forward first Gate C typing/unit implementation-entry packet that governed the bounded typing/unit lane now landed on current `main`
- the carried-forward Gate C quantitative single-item plan/pass-entry packet that governed the bounded plan/pass lane now landed on current `main`
- the carried-forward Gate C quantitative associated/cohort shaping continuation packet that governed the bounded cohort pass lane now landed on current `main`
- the carried-forward Gate D package-entry freeze packet that governed the bounded packaging/reconciliation entry slice now landed on current `main` without reopening route/UI or APS handoff scope
- the carried-forward Gate D APS handoff freeze packet that governed the bounded APS evidence-bundle-family adapter/handoff slice now landed on current `main` without widening route/UI, runtime DB, or later APS-family scope
- the carried-forward Gate D APS citation continuation freeze packet that governed the bounded citation-pack-family handoff slice now landed on current `main` without widening route/UI, runtime DB, or later APS-family fan-out
- the carried-forward Gate D APS report continuation freeze packet that governed the bounded evidence-report-family continuation slice now landed on current `main` beyond the landed citation-pack handoff while keeping export/context/deterministic fan-out, route/UI, and runtime DB widening out
- the carried-forward Gate D APS report-export continuation freeze packet that now governs the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the landed evidence-report handoff while keeping export-package/context/deterministic fan-out, route/UI, and runtime DB widening out
- the carried-forward Gate D APS context continuation freeze packet that now governs the bounded export-derived context-packet continuation slice now landed on current `main` beyond the landed evidence-report-export handoff while keeping export-package implementation, package-derived context/dossier/deterministic fan-out, route/UI, and runtime DB widening out
- the carried-forward Gate D APS multisource continuation freeze packet that now governs the bounded same-run shared-source admission boundary now landed on current `main` beyond the landed export-derived context-packet slice while keeping direct export-package, package-derived context, dossier, deterministic fan-out, route/UI, runtime DB, and schema widening out
- the carried-forward Gate D APS export-package first shared-consumer freeze packet that now governs the landed read-only choice on current `main` of `evidence_report_export_package` as the first downstream shared APS family beyond the landed multisource slice while keeping package-derived context, context-dossier, deterministic fan-out, route/UI, runtime DB, and schema widening out
- the landed Gate D APS export-package handoff implementation slice rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`, plus the merged narrow export/export-package gate-hardening follow-up in `backend/app/services/nrc_aps_evidence_report_export_gate.py` and `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`; this still does not mean package-derived context, context-dossier, deterministic fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- the carried-forward Gate D APS package-derived-context freeze packet that now lands on current `main` and selects the next later shared APS family beyond the landed export-package boundary; it still does not mean package-derived context implementation, `context_dossier`, deterministic fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the bounded Gate D APS package-derived context handoff implementation slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, plus the now-landed malformed-scoped candidate-discovery hardening across `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, and `backend/app/services/nrc_aps_context_packet_gate.py`; this still does not mean broader package-derived context, `context_dossier`, deterministic fan-out, route/UI, runtime DB, or schema widening have landed
- current `main` now also includes the read-only Gate D APS context-dossier freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`; it settles `context_dossier` as the next later shared APS family after the landed package-context milestone while preserving paired export-derived context packets as dossier inputs, but it still does not mean `context_dossier` implementation, deterministic fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the bounded Gate D APS context-dossier handoff implementation slice rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`, plus the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`; that landed lane preserves paired export-derived context packets as dossier inputs and still does not mean deterministic fan-out, route/UI, runtime DB, or schema widening have landed
- current `main` now also includes the read-only Gate D APS deterministic-insight continuation freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`; it selects `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary without admitting deterministic implementation, challenge/review-packet fan-out, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the bounded Gate D APS deterministic-insight handoff implementation slice rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, plus the narrow deterministic-gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`; that landed lane keeps one persisted dossier as the deterministic source boundary, leaves `ConnectorRun.query_plan_json` untouched, and still does not mean challenge/review-packet fan-out, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the read-only Gate D APS deterministic-challenge continuation freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`; it selects `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary without admitting challenge implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the bounded Gate D APS deterministic-challenge handoff implementation slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, plus the narrow deterministic challenge gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`; that landed lane keeps one persisted deterministic insight artifact as the immediate source boundary and still does not mean later review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the read-only Gate D APS deterministic challenge review-packet continuation freeze packet rooted in `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`; it selects `deterministic_challenge_review_packet` as the exact next deterministic continuation beyond the landed deterministic-challenge boundary while keeping validate-only gates later
- current `main` now also includes the bounded Gate D APS deterministic challenge review-packet handoff implementation slice rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, plus the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`; that landed lane keeps one persisted deterministic challenge artifact as the immediate source boundary and still does not admit validate-only expansion, route/UI, runtime DB, or schema widening
- current `main` now also includes the read-only Gate D APS validate-only-gates continuation freeze packet from PR `#136`, rooted in `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`; it selects `validate_only_gates` as the exact next verification continuation beyond the landed review-packet handoff while keeping validate-only execution/report refresh, promotion, retrieval cutover, route/UI, runtime DB, and schema widening later
- current `main` now also includes the bounded validate-only gate-report refresh lane from PR `#138`, and the post-PR138 docs/progress sync from PR `#139`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`
- current `main` now also includes the read-only `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md` freeze from PR `#140`, selecting the dedicated validate-only family-specific runtime/report-ref decision as the next bounded continuation beyond that landed generic gate-report boundary; it still does not mean dedicated validate-only implementation, promotion, retrieval cutover, route/UI, runtime DB, or schema widening have landed on current `main`
- current `main` now also includes the post-PR140 docs/progress sync from PR `#141` and the post-PR141 docs/progress sync from PR `#142`
- current `main` now also includes the bounded dedicated validate-only runtime/report-ref implementation slice from PR `#143`, rooted in `backend/app/services/nrc_aps_validate_only_gates_contract.py`, `backend/app/services/nrc_aps_validate_only_gates.py`, `backend/app/services/nrc_aps_validate_only_gates_gate.py`, `backend/tests/test_nrc_aps_validate_only_gates.py`, `tools/nrc_aps_refresh_validate_only_gates.py`, `tools/nrc_aps_validate_only_gates_gate.py`, `backend/app/services/review_nrc_aps_runtime.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/connectors_sciencebase.py`, and `project6.ps1`; that landed lane keeps the landed generic gate-report refresh posture as upstream truth and still does not admit later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, or schema widening on current `main`
- current `main` now also includes the landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`; that freeze selected promotion as the first later APS family beyond the landed dedicated validate-only boundary, and live repo truth now also shows the existing promotion governance family already sufficient on current `main` while retrieval cutover already exists there as a separate validate-only parity-proof family, so no further later APS family decision or implementation lane is currently justified by default

Key lane closure commits include:
- `a95bc104` `docs(layer3): freeze phase1a planning pack`
- `0b0ecf7e` `feat(layer3): add Phase 1A feeder-ledger entry slice`
- `d67bc0e8` `docs(layer3): add Phase 1A postcode acceptance audit`
- `f252d820` `docs(layer3): add phase1a pack front door and roadmap`
- `119c1d73` `docs(layer3): add phase1a surface map`

These are the milestone commits that define the bounded Phase 1A lane shape.
Later doc-only alignment commits may exist without changing that milestone meaning.

Current bounded posture:
- Phase 1A remains Gate-B-only feeder / ledger entry
- landed objects remain exactly:
  - `l3_session`
  - `l3_selection_manifest`
  - `l3_descriptor`
  - `l3_retrieval_event`
  - `l3_material_snapshot`
- Phase 1A itself does not admit typing, orchestration, packaging, APS handoff, route-family work, UI widening, or consumer widening
- later carried-forward Gate C freezes now cover the landed typing/unit, single-item pass, and quantitative cohort slices
- later carried-forward Gate D freeze now covers the landed bounded package-entry slice only; it does not mean packaging or consumer routes beyond that slice have already landed
- the carried-forward Gate D APS handoff freeze now covers the bounded APS evidence-bundle-family handoff slice now landed on current `main` only; it does not mean broader APS families, route/UI surfaces, or consumer routes beyond that slice have already landed
- the carried-forward Gate D APS citation and report freezes now cover the landed bounded citation-pack and evidence-report slices only; they do not mean later APS families beyond those slices have already landed
- the carried-forward Gate D APS report-export freeze now covers the bounded evidence-report-export slice now landed on current `main` only; it does not mean evidence-report-export-package or later APS families have already landed
- the carried-forward Gate D APS context freeze now covers only the bounded export-derived context-packet slice now landed on current `main`; it does not mean export-package implementation, package-derived context, dossier, deterministic, or route/UI surfaces have already landed
- the carried-forward Gate D APS multisource freeze now covers only the bounded shared same-run source-admission slice now landed on current `main`; it does not mean export-package implementation, package-derived context, context-dossier, deterministic, or schema surfaces have already landed
- the carried-forward Gate D APS export-package first shared-consumer freeze now covers the now-landed decision on current `main` to select `evidence_report_export_package` as the first later shared APS family beyond the landed multisource slice, and the bounded export-package handoff slice now also lands on current `main`; that still does not mean package-derived context, context-dossier, deterministic, or schema surfaces have already landed
- the carried-forward Gate D APS package-derived-context freeze now covers the landed read-only choice on current `main` to select package-derived context packet as the next later shared APS family beyond the landed export-package boundary, but it does not mean package-derived context implementation, `context_dossier`, deterministic, or schema surfaces have landed on current `main`
- current `main` now also includes the bounded package-derived context handoff slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, plus the now-landed malformed-scoped candidate-discovery hardening across `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, and `backend/app/services/nrc_aps_context_packet_gate.py`; it still does not mean broader package-derived context, `context_dossier`, deterministic, or schema surfaces have landed
- current `main` now also includes the read-only `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze selecting `context_dossier` as the next later shared APS family after the landed package-context milestone while preserving paired export-derived context packets as dossier inputs; it does not mean `context_dossier` implementation, deterministic, or schema surfaces have landed on current `main`
- current `main` now also includes the bounded `aps_context_dossier_handoff` slice rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py`, plus the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`; that landed lane keeps paired export-derived context packets as dossier inputs and does not admit deterministic fan-out by itself
- current `main` now also includes the read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze selecting `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary; it does not mean deterministic implementation, challenge/review-packet fan-out, or schema surfaces have landed on current `main`
- current `main` now also includes the bounded `aps_deterministic_insight_artifact_handoff` slice rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`, plus the narrow deterministic-gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`; that landed lane preserves one persisted dossier as the deterministic source boundary and does not admit later deterministic fan-out, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze selecting `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary; it does not mean deterministic challenge implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema surfaces have landed
- current `main` now also includes the bounded `aps_deterministic_challenge_artifact_handoff` lane from PR `#130`, rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, plus the narrow deterministic challenge gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`; that landed lane preserves one persisted deterministic insight artifact as the immediate source boundary, leaves `ConnectorRun.query_plan_json` untouched, and does not admit later deterministic review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze selecting `deterministic_challenge_review_packet` as the exact next deterministic continuation beyond the landed deterministic-challenge boundary; it does not mean review-packet implementation or validate-only surfaces have landed on current `main`
- current `main` now also includes the bounded `aps_deterministic_challenge_review_packet_handoff` lane rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`, plus the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`; that landed lane preserves one persisted deterministic challenge artifact as the immediate source boundary and still does not admit validate-only expansion, route/UI, runtime DB, or schema widening by itself
- current `main` now also includes the read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze plus the post-PR136 docs/progress sync from PR `#137`, and current `main` now also includes the bounded validate-only gate-report refresh lane from PR `#138`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`

The active REV2 control docs in this pack have also been re-audited against current `main` after the repo-root analyst-insight page, alias-router, static-asset, and runtime-helper surfaces landed. Treat the REV1 artifacts and the REV1-to-REV2 correction memo as historical context only.

## One-line use rule

Use this pack as the authoritative planning and closure bundle for the bounded Phase 1A Layer 3 slice; do not treat it as permission to reopen broader Layer 3 scope.

## Pack layout

### 1. Planning baseline

Read these first when you need the tranche boundary, prep rules, and validation posture:
- `Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`

Read this after the REV2 trio if you are deciding what the first Gate C slice had to freeze before any write-enabled Gate C implementation started:
- `Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`

Read this after `04_GATEC_ENTRY_FREEZE.md` if you need the carried-forward contract for the first bounded Gate C typing/unit slice that has now landed on current `main`:
- `Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`

Read this after `05_GATEC_IMPLEMENTATION_FREEZE.md` if you need the carried-forward contract for the bounded Gate C quantitative single-item plan/pass slice that has now landed on current `main`:
- `Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`

Read this after `06_GATEC_PASS_FREEZE.md` if you need the carried-forward contract for the bounded Gate C quantitative associated/cohort continuation slice that has now landed on current `main`:
- `Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`

Read this after `07_GATEC_COHORT_FREEZE.md` if you need the carried-forward contract that governed the bounded Gate D package-entry slice now landed on current `main`:
- `Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`

Read this after `08_GATED_PACKAGE_FREEZE.md` if you need the carried-forward contract that governed the bounded APS evidence-bundle-family handoff slice now landed on current `main`:
- `Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md`

Read this after `09_GATED_APS_HANDOFF_FREEZE.md` if you need the carried-forward contract that governed the bounded citation-pack-family handoff slice now landed on current `main`:
- `Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`

Read this after `10_GATED_APS_CITATION_FREEZE.md` if you need the governing contract for the bounded evidence-report-family continuation slice now landed on current `main`:
- `Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`

Read this after `11_GATED_APS_REPORT_FREEZE.md` if you need the governing contract for the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the landed evidence-report handoff:
- `Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`

Read this after `12_GATED_APS_REPORT_EXPORT_FREEZE.md` if you need the governing contract for the bounded export-derived context-packet continuation slice now landed on current `main` beyond the landed evidence-report-export handoff:
- `Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`

Read this after `13_GATED_APS_CONTEXT_FREEZE.md` if you need the governing contract for the bounded same-run shared-source admission boundary now landed on current `main` beyond the landed export-derived context-packet slice:
- `Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`

Read this after `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md` if you need the governing contract for the now-landed next later shared APS family beyond the landed export-package boundary:
- `Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`

Read this after `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` if you need the now-landed bounded package-derived context handoff slice on current `main`:
- `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_package_handoff.py`

Read this after `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` if you need the governing contract for the now-landed next deterministic continuation beyond the landed deterministic-insight boundary:
- `Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`

Read this after `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` if you need the governing contract for the now-landed next deterministic continuation beyond the landed deterministic-challenge boundary:
- `Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`

Read this after `20_GATED_APS_REVIEW_PACKET_FREEZE.md` if you need the now-landed read-only validate-only-gates freeze on current `main` beyond the now-landed deterministic challenge review-packet handoff:
- `Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`

Read these after `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` if you need the landed bounded validate-only gate-report refresh lane on current `main` beyond that freeze:
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `tools/nrc_aps_refresh_review_gate_reports.py`
- `tools/run_nrc_aps_local_corpus_e2e.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- `project6.ps1`

Read this after the landed generic gate-report refresh lane if you need the landed read-only next decision from PR `#140` beyond that landed boundary:
- `Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

### 2. Execution handoff

Read these when you need the touch envelope, proof runbook, and direct write-enabled contract:
- `Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md`

### 3. Local freeze and closure

Read these when you need the implementation-local defaults, acceptance criteria, write-enabled prompt, reconciliation posture, roadmap, and postcode audit:
- `Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `Layer3_execution_freeze/08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `Layer3_execution_freeze/09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `Layer3_execution_freeze/10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- `Layer3_execution_freeze/11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `Layer3_execution_freeze/12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `Layer3_execution_freeze/layer3_phase1a_roadmap.png`
- `Layer3_execution_freeze/FREEZE_PACK_REV1_TO_REV2_SOURCE_HYGIENE_MEMO.md`

## Doc classification

### Normative control docs

These define the actual tranche boundary and control posture:
- `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `06_PHASE1A_CODEWRITING_HANDOFF.md`
- `07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### Operational companion docs

These help navigation, reconciliation, and visual orientation, but do not override the normative set:
- `README_LAYER3_PHASE1A_PACK.md`
- `11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `13-phase1a-surface-map.md`
- `layer3_phase1a_roadmap.png`

### Post-Phase 1A carried-forward bridge

This bridge document is not part of the accepted Phase 1A normative control spine.
It exists to explain why a separate Gate C freeze packet was required:
- `04_GATEC_ENTRY_FREEZE.md`

### Post-Phase 1A carried-forward freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the first bounded Gate C typing/unit implementation lane now landed on current `main`:
- `05_GATEC_IMPLEMENTATION_FREEZE.md`

### Post-Phase 1A carried-forward continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the bounded Gate C quantitative single-item plan/pass implementation lane now landed on current `main`:
- `06_GATEC_PASS_FREEZE.md`

### Post-Phase 1A carried-forward cohort continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the bounded Gate C quantitative associated/cohort shaping and pass-entry lane now landed on current `main`:
- `07_GATEC_COHORT_FREEZE.md`

### Post-Phase 1A carried-forward Gate D package freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the actual frozen contract that governed the bounded Gate D package-entry slice now landed on current `main`, and it does not itself imply that packaging or consumer routes beyond that slice have already landed:
- `08_GATED_PACKAGE_FREEZE.md`

### Post-Phase 1A carried-forward APS handoff freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governed the bounded APS evidence-bundle-family adapter/handoff slice now landed on current `main`, and it does not itself imply that broader APS fan-out, route/UI surfaces, or consumer routes beyond that slice have already landed:
- `09_GATED_APS_HANDOFF_FREEZE.md`

### Post-Phase 1A carried-forward APS citation continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governed the bounded citation-pack-family handoff slice now landed on current `main` after the already-landed evidence-bundle slice, and it does not itself imply that report/context/deterministic families or route/UI surfaces have already landed:
- `10_GATED_APS_CITATION_FREEZE.md`

Rule:
- if a rule exists only in an operational companion doc, move or restate it in the normative control spine before relying on it as durable control guidance

### Post-Phase 1A carried-forward APS report continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governed the bounded evidence-report-family continuation slice now landed on current `main` beyond the already-landed citation-pack slice, and it does not itself imply that export/context/deterministic families or route/UI surfaces have already landed:
- `11_GATED_APS_REPORT_FREEZE.md`

### Post-Phase 1A carried-forward APS report-export continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governs the bounded evidence-report-export-family continuation slice now landed on current `main` beyond the already-landed evidence-report slice, and it does not itself imply that evidence-report-export-package, context, deterministic, or route/UI surfaces have already landed:
- `12_GATED_APS_REPORT_EXPORT_FREEZE.md`

### Post-Phase 1A carried-forward APS context continuation freeze packet

This document is also outside the accepted Phase 1A normative control spine.
It is the narrow frozen contract that governs the bounded export-derived context-packet continuation slice now landed on current `main` beyond the already-landed evidence-report-export slice, and it does not itself imply that export-package implementation, package-derived context, dossier, deterministic, or route/UI surfaces have already landed:
- `13_GATED_APS_CONTEXT_FREEZE.md`

### Post-Phase 1A carried-forward APS multisource continuation freeze packet

It is the narrow frozen contract that governs the bounded same-run shared-source admission slice now landed on current `main` beyond the already-landed export-derived context-packet slice, and it does not itself imply that direct export-package implementation, package-derived context, context-dossier, deterministic, or schema surfaces have already landed:
- `14_GATED_APS_MULTISOURCE_FREEZE.md`

### Post-Phase 1A carried-forward APS export-package first shared-consumer freeze packet

It is the narrow frozen contract that governs the now-landed read-only choice on current `main` of `evidence_report_export_package` as the first downstream shared APS family beyond the already-landed multisource slice, and it does not itself imply that export-package implementation, package-derived context, context-dossier, deterministic, or schema surfaces have already landed:
- `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`

### Post-Phase 1A carried-forward APS package-derived-context continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the carried-forward read-only freeze now landed on current `main` that selects package-derived context packet as the next later shared APS family beyond the already-landed export-package boundary, and it does not itself imply that package-derived context implementation, `context_dossier`, deterministic, or schema surfaces have landed on current `main`:
- `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`

### Post-Phase 1A carried-forward APS context-dossier continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the carried-forward read-only freeze now landed on current `main` that selects `context_dossier` as the next later shared APS family beyond the already-landed package-context boundary while preserving paired export-derived context packets as dossier inputs, and it does not itself imply that deterministic, review-packet, or schema surfaces have landed on current `main`:
- `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`

### Post-Phase 1A carried-forward APS deterministic-insight continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects `deterministic_insight_artifact` as the first deterministic continuation beyond the already-landed dossier boundary, and it does not itself imply that deterministic implementation, challenge/review-packet fan-out, or schema surfaces have landed on current `main`:
- `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`

### Post-Phase 1A carried-forward APS deterministic-challenge continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects `deterministic_challenge_artifact` as the next deterministic continuation beyond the already-landed deterministic-insight boundary, and it does not itself imply that review-packet, validate-only, or schema surfaces have landed on current `main`:
- `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`

### Post-Phase 1A carried-forward APS review-packet continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects the bounded deterministic challenge review-packet continuation beyond the already-landed deterministic challenge boundary, and it does not itself imply that validate-only, route/UI, or schema surfaces have landed on current `main`:
- `20_GATED_APS_REVIEW_PACKET_FREEZE.md`

### Post-Phase 1A carried-forward APS validate-only gates continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects the bounded `validate_only_gates` continuation beyond the already-landed review-packet boundary, and it does not itself imply that validate-only runtime/report-ref, route/UI, or schema surfaces have landed on current `main`:
- `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`

### Post-Phase 1A carried-forward APS validate-only runtime continuation freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selects the bounded dedicated validate-only runtime/report-ref continuation beyond the already-landed `validate_only_gates` boundary, and it does not itself imply that promotion, retrieval cutover, route/UI, or schema surfaces have landed on current `main`:
- `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

### Post-Phase 1A carried-forward APS promotion settlement freeze packet

This document is outside the accepted Phase 1A normative control spine.
It is the now-landed read-only freeze on current `main` that selected promotion as the first later APS family beyond the dedicated validate-only runtime/report-ref boundary before the later APS family packet was settled, and it does not itself imply that broader deferred-scope Layer3 work, runtime DB writes, or schema widening have landed on current `main`:
- `23_GATED_APS_PROMOTION_FREEZE.md`

### Post-settlement broader workbench planning-only freeze doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged planning-only prep doc on current `main` for the deferred `future workbench route family`, and it does not itself activate that lane, reopen the settled packet, or imply route/UI, runtime DB, schema, or shared-contract widening:
- `24_L3_WB_FREEZE.md`

### Post-settlement broader workbench exact-input prep doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged planning-only companion prep doc on current `main` for the deferred `future workbench route family`, and it now records the adopted planning-only operator-insufficiency trigger, additive route-family choice, and minimum typing posture plus the exact owner-surface map, proof matrix, and remains-out list that keep a later implementation-entry packet narrow without implying activation:
- `26_L3_WB_INPUTS.md`

### Broader workbench first-slice setup freeze doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged first-slice setup doc from PR `#178` for the `future workbench route family`; it narrowed the later additive `/review/layer3` plus `/api/v1/layer3/...` implementation-entry target through Gate C typing review before PR `#184` implemented that bounded first slice. It remains the governing scope/no-go contract and does not activate downstream execution, package review, qualitative, hybrid, RAG/vector, runtime snapshot DB write, schema, or handoff scope:
- `28_L3_WB_FIRST_SLICE_FREEZE.md`

### Broader workbench first-slice API/state contract

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged API/state companion from PR `#182` for the `future workbench route family`; it froze endpoint, DTO, Gate B persistence, Gate C override, authority-rail, browser-state, and proof expectations for the later PR `#184` `/review/layer3` plus `/api/v1/layer3/...` implementation pass. It remains the governing API/state contract and does not change the no-go list:
- `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`

### Broader workbench second-slice plan-preview freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They were merged as planning docs in PR `#191` and govern the PR `#194` workbench slice after the landed first-slice shell/API: a read-only plan-preview step after explicit Gate C typing commit. PR `#194` implements that bounded endpoint/UI state, while PRs `#195` and `#196` only record/align post-merge proof and board metadata. None of these activate execution, results, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, or broader route/UI scope:
- `30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`

### Broader workbench third-slice plan-approval freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They were merged as planning docs in PR `#198` and freeze the third workbench slice after read-only plan preview: operator approval and durable formation of an approved owner-service plan, without pass-run creation, analysis execution, results review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, hidden LLM planning, or broader route/UI scope. PR `#199` implements only that approval-only persistence boundary:
- `32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`

### Broader workbench fourth-slice plan-revision freeze docs

These documents are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
PR `#203` freezes the fourth workbench slice as planning-only governance for explicit operator rejection and revision-request semantics against the current server-backed plan preview before approval, and PR `#204` corrects the associated deferred-scope count metadata. These docs govern the PR `#205` implementation and the PR `#207` submission-hardening follow-up; PR `#206` records the post-PR205 docs/control state, and PRs `#208`/`#209` record post-hardening docs/progress cohesion only. None of these docs-only or hardening follow-ups reopen or supersede already approved plans, call `materialize_pass_entry(...)`, create `L3PassRun`, run analysis, write manifests, enable results/package/handoff, widen runtime DB/schema behavior, or admit qualitative/hybrid/RAG/vector/LLM planning:
- `34_L3_WB_PLAN_REVISION_FREEZE.md`
- `35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`

### Broader workbench first-slice, plan-preview, plan-approval, and plan-revision implementation

This implementation is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the bounded first-slice workbench implementation from PR `#184`, with post-implementation status/cohesion/explicit-Gate-C-typing/review-feedback closeouts through PR `#190`; PR `#194` then adds read-only plan preview after explicit Gate C typing commit, PRs `#195`/`#196` record proof/board metadata for that state, PR `#198` freezes plan approval, PR `#199` adds approval-only `L3AnalysisPlan` persistence, PR `#205` adds pre-approval plan-revision control, and PR `#207` hardens revision submission with serialized backend decision writes and shared UI in-flight locking. PR `#206` and PRs `#208`/`#209` are docs/control or docs/progress cohesion syncs for that same bounded revision state, not new functional slices. Together they make `/review/layer3` and `/api/v1/layer3/...` live only for intent/preflight, deterministic source preview, material preview, Gate B decision recording, Gate C UI non-authoritative typing preview, explicit API owner-service typing materialization when `commit_typing` is true, explicit Gate C override unavailability, session summary, read-only plan preview, approval-only plan persistence, and revision-control for the current server-backed preview before approval:
- `backend/main.py`
- `backend/app/api/router.py`
- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`

### Broader workbench mockup source mirror

These files are outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
They mirror the text mockup/spec artifact and record the local visual asset hashes that informed the first-slice setup doc. They are planning input only; they do not make the visual assets implementation dependencies or override current repo truth:
- `layer3-mockups/mockup-spec.txt`
- `layer3-mockups/assets.md`

### Post-settlement qualitative single-item planning-only freeze doc

This document is outside the accepted Phase 1A normative control spine and outside the settled later APS family packet.
It is the merged planning-only prep doc on current `main` for the deferred qualitative single-item breadth axis, and it does not itself activate that lane, reopen the settled packet, or imply route/UI, runtime DB, schema, or shared-contract widening:
- `25_L3_QUAL1_FREEZE.md`

### Merged qualitative single-item exact-input prep doc

This is the merged planning-only companion prep doc on current `main` for the deferred qualitative single-item breadth axis.
It remains planning-only, does not itself activate the lane, and must not be described as a merged milestone, packet-reopen signal, or active lane:
- `27_L3_QUAL1_INPUTS.md`

## Current use guidance

### If you are auditing scope

Start with:
- `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### If you are checking whether the lane is closed enough to review

Start with:
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- `11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `13-phase1a-surface-map.md`

### If you need the concrete implementation surface map

Start with:
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md`
- the four code files from commit `0b0ecf7e`

### If you are deciding whether more Phase 1A code work is justified

Start with:
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- the committed code diff at `0b0ecf7e`

Current answer:
- no additional Phase 1A code work is justified by default from the current lane state

### If you are deciding what must happen before broader Gate C continuation is allowed

Start with:
- `Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`
- `Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`
- `Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`
- `Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `docs/analyst_insight/analyst_insight_status_handoff.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### If you are deciding what must happen before bounded Gate D packaging continuation is allowed

Start with:
- `Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`
- `Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`
- `Layer3_execution_freeze/13-phase1a-surface-map.md`
- `docs/analyst_insight/analyst_insight_status_handoff.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### If you are deciding what must happen before bounded later APS-family continuation is allowed

Start with:
- `Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`
- `Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`
- `Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
- `Layer3_planning_docs/23_GATED_APS_PROMOTION_FREEZE.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- no further later APS-family decision or implementation lane is justified by default from current `main`

### If you are deciding what deferred broader Layer3 planning-only prep now exists on current `main`

Start with:
- `Layer3_planning_docs/24_L3_WB_FREEZE.md`
- `Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md`
- `Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/25_L3_QUAL1_FREEZE.md`
- `Layer3_planning_docs/27_L3_QUAL1_INPUTS.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### If you are deciding the first Layer 3 workbench implementation slice

Start with:
- `Layer3_planning_docs/24_L3_WB_FREEZE.md`
- `Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md`
- `Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`

Current answer:
- first-slice setup and API/state contract docs were planning-only when PR `#178` and PR `#182` landed, but PR `#184` now implements that bounded first slice on current `main`, with closeout/correction passes through PR `#189`
- the live first-slice surface is an additive `/review/layer3` page plus `/api/v1/layer3/...` API family
- the live first implementation stops at intent/preflight, deterministic source selection, material preview, Gate B material review, Gate C UI non-authoritative typing preview, explicit API owner-service typing materialization when `commit_typing` is true, explicit Gate C override unavailability, and session summary
- the implementation uses `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` as the endpoint, DTO, state, persistence, browser-state, and proof contract
- downstream plan, execution, results, package review, qualitative, hybrid, RAG/vector, runtime snapshot DB writes, schema widening, and handoff remain unavailable unless separately activated

### If you are deciding the second Layer 3 workbench implementation slice

Start with:
- `Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`

Current answer:
- the next adequate implementation slice after the landed first-slice shell/API was read-only plan preview after explicit Gate C typing commit; PR `#194` implements that slice, and PRs `#195`/`#196` only record post-merge proof/board metadata for it
- plan preview composes around the landed pass-entry owner service through a read-only helper rather than duplicating pass-entry classification in route or browser code
- execution, results, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, and hidden LLM planning remain out of scope

### If you are auditing the third Layer 3 workbench implementation slice

Start with:
- `Layer3_planning_docs/32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `Layer3_planning_docs/33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`

Current answer:
- PR `#199` already implements operator plan approval plus durable `L3AnalysisPlan` formation only
- the existing `materialize_pass_entry(...)` helper remains execution-bearing and must not be called by the approval path
- the implementation uses a narrower owner-service helper that persists the approved plan without creating `L3PassRun`, running analysis, writing manifests, changing package/handoff state, adding migrations, or widening schema
- execution, results review, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, and hidden LLM planning remain out of scope

PR `#199` is the bounded implementation lane for that third slice. It makes only approval-only plan persistence live through `/api/v1/layer3/plan/approve` and the existing `/review/layer3` plan panel; it still does not admit `L3PassRun`, analysis execution, result review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, or hidden LLM planning.

PRs `#200`, `#201`, and `#202` are post-approval docs/control syncs. They keep approval-state, mockup-spec, and workbench progress-control surfaces aligned without making execution, results/package/handoff, runtime DB/schema widening, or qualitative/hybrid/RAG/vector/LLM planning live.

### If you are auditing the fourth Layer 3 workbench revision-control slice

Start with:
- `Layer3_planning_docs/34_L3_WB_PLAN_REVISION_FREEZE.md`
- `Layer3_planning_docs/35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- `Layer3_planning_docs/32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `Layer3_planning_docs/33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `e2e/layer3-workbench.spec.js`

Current answer:
- the fourth slice is now live only as bounded revision-control through PR `#205`, with PR `#207` hardening the same bounded behavior rather than adding a new functional slice; PR `#206` and PRs `#208`/`#209` are docs/control or docs/progress cohesion syncs only
- it admits explicit operator rejection and revision request against the current server-backed preview before approval
- already approved plans remain terminal for this slice; reopening, replacing, or superseding them requires a later freeze
- execution, results review, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime snapshot DB writes, schema widening, and hidden LLM planning remain out of scope

No functional next workbench implementation beyond revision-control is selected by this pack. The next functional pass must start with a new freeze/API-state contract before adding execution, approved-plan supersession, results/package/handoff, runtime DB/schema widening, or qualitative/hybrid/RAG/vector/LLM planning.

### If you are auditing the branch-local Layer 3 workbench execution-readiness packet

Start with:
- `Layer3_planning_docs/36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `Layer3_planning_docs/37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `Layer3_planning_docs/34_L3_WB_PLAN_REVISION_FREEZE.md`
- `Layer3_planning_docs/35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

Current answer:
- this branch-local packet is execution-readiness planning only
- it adds proof/readiness, state, preview-hash, idempotency, concurrency, revision-recovery, approved-plan-correction, output-taxonomy, and source-breadth gates before any later execution branch
- it does not make execution, `L3PassRun`, analysis execution, results/package/handoff, approved-plan supersession, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, local upload ingestion, or full mockup activation live
- browser proof is not required for this docs-only readiness packet because no runtime UI behavior changes, but any future UI or execution slice must run headed and headless browser proof when browser behavior changes

### If you are auditing the merged qualitative single-item companion prep on current `main`

Start with:
- `Layer3_planning_docs/25_L3_QUAL1_FREEZE.md`
- `Layer3_planning_docs/27_L3_QUAL1_INPUTS.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`

## Residual boundary note

This README closes the pack-local navigation gap, not broader repo-wide Layer 3 documentation closure.

It does not prove that unrelated dirty root planning pools or higher-level repo front doors are globally reconciled.
That broader question requires a separate read-only root-doc audit.
