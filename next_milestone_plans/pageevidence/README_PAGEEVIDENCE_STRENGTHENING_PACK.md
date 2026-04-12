# PageEvidence Strengthening Planning Pack

## Purpose

This folder is the root-local planning/control branch copy for the PageEvidence strengthening lane.

It is a standalone planning pack under:

- `next_milestone_plans/pageevidence`

Its job is to constrain and prepare PageEvidence strengthening work without widening into unrelated runtime, schema, OCR/media, or generic multi-candidate scope.

## Current lane position

Within this root-local planning branch, this remains the local PageEvidence planning lane.
It is **not** the live merged-main authority copy of the PageEvidence pack.

The pack is built around the current live runtime facts that matter:

- `baseline` remains the current default runtime mode
- `candidate_a_page_evidence_v1` remains the current admitted non-`baseline` value
- this branch-local pack was drafted against an earlier state where `backend/app/services/nrc_aps_page_evidence.py` still fused shared evidence extraction, candidate identity, and projected-class logic
- the live merged authority worktree has since landed an internal whole-document split between shared document extraction and Candidate A projection in `worktrees/pageevidence-main-merge/backend/app/services/nrc_aps_page_evidence.py`
- hidden-consumer downstream surfaces remain real and must be treated as compatibility surfaces
- the current pinned Candidate A workbench artifact remains historically authoritative unless later explicitly superseded

Merged-main note:
- the stronger merged-main worktree copy has already moved this lane into adopted hold-state posture
- the worktree copy now already contains the Pass 1-style service-layer shared-evidence / candidate-projection split for whole-document PageEvidence handling
- do not treat this root-local copy as the cleaner live authority surface

## Pack posture

The decisions frozen into this pack are:

1. **Lane Class A only within this pack's prepared strengthening scope**
2. **Lane Class B remains future scope only and requires a separate explicit freeze**
3. **Representative fixtures are binding for equivalence/no-drift purposes**
4. **Regression-only fixtures may drift only with written justification**
5. **A threshold/percentage-based materiality rule is a possible later evolution, not the current rule**
6. **A small fixed set of pre-approved new internal evidence fields is allowed in Pass 3 only**
7. **`nrc_aps_document_processing.py` should remain untouched in Pass 1; if analysis against a copy is useful, that copy must remain non-authoritative, non-runtime, and outside the production `backend` path**
8. **Strengthened artifacts coexist with the current pinned Candidate A artifact; the current pinned artifact remains historically authoritative unless later explicitly superseded**
9. **Passes 1-4 are the only prepared passes in this pack; Lane Class B remains later scope only by separate freeze**
10. **Current filenames are working labels for this separate pack; no ordinalization step is required for pack use**

## Authority note

Within this standalone lane:

- live repo code, fixtures, pinned artifacts, and real downstream-consumer behavior outrank pack interpretation if conflict appears
- this pack is the root-local planning/control surface for this branch copy of the PageEvidence lane
- other planning packs may provide background context, but they do not govern this pack unless you explicitly decide otherwise later

## Files in this pack

### Core planning/control docs

1. `README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
2. `EXACT_PAGE_EVIDENCE_SHARED_EVIDENCE_AND_PROJECTION_SEPARATION_BOUNDARY.md`
3. `PAGE_EVIDENCE_STRENGTHENING_EXECUTION_PACKET.md`
4. `PAGE_EVIDENCE_SELECTOR_SEMANTICS_AND_BEHAVIOR_DRIFT_POLICY.md`
5. `PAGE_EVIDENCE_SCHEMA_AND_ARTIFACT_COMPATIBILITY_POLICY.md`
6. `PAGE_EVIDENCE_EVALUATION_AND_DISAGREEMENT_MATRIX.md`
7. `PAGE_EVIDENCE_HIDDEN_CONSUMER_COMPATIBILITY_CHECKLIST.md`
8. `PAGE_EVIDENCE_MODULE_COMPONENT_DEPENDENCY_AND_TOUCHPOINT_INVENTORY.md`
9. `PAGE_EVIDENCE_ROLLBACK_AND_CHANGE_CONTROL_GUARDRAILS.md`
10. `PAGE_EVIDENCE_BLAST_RADIUS_AND_BEFORE_AFTER_TOPOLOGY.md`
11. `PAGE_EVIDENCE_FILE_TO_TEST_TO_BUNDLE_TRACEABILITY_MATRIX.md`
12. `PAGE_EVIDENCE_INTERNAL_FIELD_DEFINITION_REGISTER.md`
13. `PAGE_EVIDENCE_SCHEMA_AND_ARTIFACT_BEFORE_AFTER_PAYLOAD_EXAMPLES.md`
14. `PAGE_EVIDENCE_PASS_SEQUENCING_AND_COMMIT_CHOREOGRAPHY.md`
15. `PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md`
16. `PAGE_EVIDENCE_ASSUMPTION_REGISTER.md`
17. `PAGE_EVIDENCE_PACK_ACTIVATION_AND_WORKING_USE_PLAN.md`
18. `PAGE_EVIDENCE_LANE_A_EQUIVALENCE_AND_NO_DRIFT_GATE.md`
19. `PAGE_EVIDENCE_PASS_LEVEL_ALLOWED_FILE_MANIFEST.md`
20. `PAGE_EVIDENCE_STRENGTHENING_IMPLEMENTATION_RECORD.md`
21. `PAGE_EVIDENCE_STRENGTHENING_IMPLEMENTATION_RECORD_TEMPLATE.md`
22. `PAGE_EVIDENCE_STRENGTHENING_PACK_VERIFICATION_REPORT.md`

### Operational companion docs

23. `PAGE_EVIDENCE_PACK_ACTIVATION_AND_VERIFICATION_CHECKLIST.md`
24. `PAGE_EVIDENCE_OPERATOR_EXECUTION_SHEET.md`
25. `PAGE_EVIDENCE_REPRESENTATIVE_FIXTURE_LOCK_AND_CANONICAL_SUBSET_NOTE.md`
26. `pageevidence_v10_codex_handoff.md`

### Support artifact

27. `pageevidence_strengthening_pack_v10.zip`

Interpretation note:

- the handoff doc is a pack-local continuation aid, not higher authority than live repo truth
- the zip file is archival source material, not the active working authority copy

## Recommended reading / use order

1. README / front door
2. separation boundary
3. execution packet
4. selector-semantics / behavior-drift policy
5. Lane A equivalence / no-drift gate
6. representative fixture lock
7. hidden-consumer checklist
8. file-to-test-to-bundle traceability matrix
9. pass-level allowed file manifest
10. pass sequencing / commit choreography
11. module/component/dependency/touchpoint inventory
12. schema/artifact compatibility policy
13. internal field-definition register
14. evaluation / disagreement matrix
15. activation / working-use plan
16. activation / verification checklist
17. operator execution sheet
18. implementation record
19. implementation-record template
20. handoff doc

## Core pack objective

> Strengthen PageEvidence by reconstituting it as a shared deterministic evidence extractor, with candidate-policy projection separated from the core extraction layer, while preserving the current baseline-default runtime posture, avoiding outward contract widening, and improving calibration and disagreement visibility for the admitted Candidate A path.

## Immediate next step

This pack is already strong enough to guide implementation planning.

The next justified step is no longer "start separation from scratch."
That separation is already live in the canonical merged authority worktree.

If PageEvidence work reopens from this branch-local pack, the next step is:

- re-establish live repo truth directly from code, fixtures, pinned artifacts, and downstream-consumer surfaces
- then decide whether the lane should:
  - stop-and-hold on the now-landed split, or
  - reopen a later bounded pass such as internal field enrichment, evaluation expansion, or outward-contract cleanup
