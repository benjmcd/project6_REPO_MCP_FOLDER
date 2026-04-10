# PageEvidence Strengthening Planning Pack

## Purpose

This folder is a prepared standalone PageEvidence strengthening pack for Lane Class A work under:

- `next_milestone_plans/pageevidence`

Its job is to constrain and prepare PageEvidence strengthening work without widening into unrelated runtime, schema, OCR/media, or generic multi-candidate scope.

## Current posture

The pack is built around the current live runtime facts that matter:

- `baseline` remains the current default runtime mode
- `candidate_a_page_evidence_v1` remains the current admitted non-`baseline` value
- `backend/app/services/nrc_aps_page_evidence.py` now separates shared evidence extraction from Candidate A projection inside the existing owner file; no separate projection/helper module is currently required
- hidden-consumer downstream surfaces remain real and must be treated as compatibility surfaces
- the current pinned Candidate A workbench artifact remains historically authoritative for workbench/report compatibility and before-state reference unless later explicitly superseded, but it does not override live admitted integrated Candidate A behavior in the owner path
- the current branch already cleared Pass 1 closure, and fresh truth re-establishment found no residual Pass 2 helper-extraction or compatibility-bridge obligation
- any future implementation work must begin from a new explicitly frozen objective rather than reopening Pass 2 by momentum

This pack does **not** by itself supersede the live repo's retained-`baseline` stable-hold control posture.

Local standalone refinement/use may proceed without ordinalization.
Ordinalization/adoption is required before treating these docs as repo-native active control authority.

## Authority hierarchy

Until formal adoption/insertion occurs:

1. live repo code, fixtures, pinned artifacts, and real downstream-consumer behavior
2. live repo active control docs
3. this prepared standalone pack
4. archive/context artifacts in this folder

## Current repo-native insertion targets

If this pack is later adopted into the live repo control structure on this branch, the insertion pass must reconcile against the current repo-native control spine rooted at:

- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md` for front-door/navigation placement
- `next_milestone_plans/multi_variant_visual_lane_control/03AC_EXACT_POST_ADMISSION_DEFAULTING_SCOPE_AND_DECISION_BOUNDARY.md` for the exact post-admission/defaulting boundary
- `next_milestone_plans/multi_variant_visual_lane_control/05O_POST_ADMISSION_DEFAULTING_PLANNING_FREEZE_PACKET.md` for the frozen planning packet already governing the retained-default horizon
- `next_milestone_plans/multi_variant_visual_lane_control/05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md` for the merged-main retained-`baseline` default decision
- `next_milestone_plans/multi_variant_visual_lane_control/05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md` for the current merged-main closure/handoff posture

This repo-native insertion requirement does **not** make the MVVLC pack the conceptual owner of this standalone PageEvidence pack before adoption.
It means only that formal adoption must integrate with the live repo control surfaces that currently govern the retained-`baseline` stable-hold state.

## One-line use rule

Use this folder for local standalone refinement and pre-adoption Lane Class A planning; do not treat it as repo-native active control authority until insertion/adoption succeeds.

## Pack posture

The decisions frozen into this pack are:

1. **Lane Class A only within this pack's prepared strengthening scope**
2. **Lane Class B remains future scope only and requires a separate explicit freeze**
3. **Representative fixtures are binding for equivalence/no-drift purposes**
4. **Regression-only fixtures may drift only with written justification**
5. **A threshold/percentage-based materiality rule is a possible later evolution, not the current rule**
6. **A small fixed set of pre-approved new internal evidence fields is allowed in Pass 3 only**
7. **`nrc_aps_document_processing.py` must remain untouched in Pass 1 absent explicit escalation; if analysis against a copy is useful, that copy must remain non-authoritative, non-runtime, and outside the production `backend` path**
8. **Strengthened artifacts coexist with the current pinned Candidate A artifact; the current pinned artifact remains historically authoritative for workbench/report compatibility and before-state reference unless later explicitly superseded, but it does not override live admitted integrated Candidate A behavior in the owner path**
9. **Passes 1-4 are the only prepared passes in this pack; Lane Class B remains later scope only by separate freeze**

## Doc classification table

### Active control docs

These are normative docs.
They are prepared for adoption, but remain below live repo authority until insertion/adoption succeeds.

| document | role | authority tier | intended use | should be ordinalized/adopted? |
| --- | --- | --- | --- | --- |
| `EXACT_PAGE_EVIDENCE_SHARED_EVIDENCE_AND_PROJECTION_SEPARATION_BOUNDARY.md` | lane boundary | prepared standalone normative | freeze separation boundary and non-goals | yes |
| `PAGE_EVIDENCE_STRENGTHENING_EXECUTION_PACKET.md` | execution control | prepared standalone normative | govern prepared Lane Class A execution posture | yes |
| `PAGE_EVIDENCE_SELECTOR_SEMANTICS_AND_BEHAVIOR_DRIFT_POLICY.md` | selector semantics | prepared standalone normative | control same-selector/no-drift handling | yes |
| `PAGE_EVIDENCE_LANE_A_EQUIVALENCE_AND_NO_DRIFT_GATE.md` | equivalence gate | prepared standalone normative | govern Lane Class A no-drift proof | yes |
| `PAGE_EVIDENCE_REPRESENTATIVE_FIXTURE_LOCK_AND_CANONICAL_SUBSET_NOTE.md` | representative-fixture policy | prepared standalone normative | freeze binding subset and fixture rule | yes |
| `PAGE_EVIDENCE_SCHEMA_AND_ARTIFACT_COMPATIBILITY_POLICY.md` | compatibility policy | prepared standalone normative | govern schema/artifact meaning and compatibility | yes |
| `PAGE_EVIDENCE_EVALUATION_AND_DISAGREEMENT_MATRIX.md` | evaluation control | prepared standalone normative | define disagreement/evaluation coverage expectations | yes |
| `PAGE_EVIDENCE_HIDDEN_CONSUMER_COMPATIBILITY_CHECKLIST.md` | hidden-consumer control | prepared standalone normative | define required downstream compatibility checks | yes |
| `PAGE_EVIDENCE_BLAST_RADIUS_AND_BEFORE_AFTER_TOPOLOGY.md` | blast-radius control | prepared standalone normative | govern connection-surface and topology classification | yes |
| `PAGE_EVIDENCE_INTERNAL_FIELD_DEFINITION_REGISTER.md` | field register | prepared standalone normative | freeze authorized internal field set and derivation constraints | yes |
| `PAGE_EVIDENCE_PASS_SEQUENCING_AND_COMMIT_CHOREOGRAPHY.md` | pass choreography | prepared standalone normative | freeze pass order and rollback-friendly sequencing | yes |
| `PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md` | roadmap and gate notes | prepared standalone normative | give the prepared Lane Class A roadmap narrative | yes |
| `PAGE_EVIDENCE_PASS_LEVEL_ALLOWED_FILE_MANIFEST.md` | file boundary control | prepared standalone normative | freeze per-pass editable-file envelope | yes |
| `PAGE_EVIDENCE_ROLLBACK_AND_CHANGE_CONTROL_GUARDRAILS.md` | rollback control | prepared standalone normative | govern rollback/change-control expectations | yes |

### Operational companion docs

These docs are non-normative.
They may summarize or operationalize normative rules, but they must not create new ones.

| document | role | authority tier | intended use | should be ordinalized/adopted? |
| --- | --- | --- | --- | --- |
| `README_PAGEEVIDENCE_STRENGTHENING_PACK.md` | front door | operational companion | orient readers and classify docs by role | yes |
| `PAGE_EVIDENCE_PACK_ACTIVATION_AND_WORKING_USE_PLAN.md` | session procedure | operational companion | narrative working sequence for local use and adoption prep | yes |
| `PAGE_EVIDENCE_PACK_ACTIVATION_AND_VERIFICATION_CHECKLIST.md` | insertion checklist | operational companion | pre-insertion and post-insertion verification checklist | yes |
| `PAGE_EVIDENCE_OPERATOR_EXECUTION_SHEET.md` | quick reference | operational companion | compressed operator summary of normative rules | yes |
| `PAGE_EVIDENCE_FILE_TO_TEST_TO_BUNDLE_TRACEABILITY_MATRIX.md` | validation map | operational companion | map files to tests/bundles for execution hygiene | provisional |
| `PAGE_EVIDENCE_MODULE_COMPONENT_DEPENDENCY_AND_TOUCHPOINT_INVENTORY.md` | architecture inventory | operational companion | summarize components, dependencies, and touchpoints | provisional |
| `PAGE_EVIDENCE_ASSUMPTION_REGISTER.md` | assumption log | operational companion | track assumptions and failure modes explicitly | provisional |
| `PAGE_EVIDENCE_SCHEMA_AND_ARTIFACT_BEFORE_AFTER_PAYLOAD_EXAMPLES.md` | payload examples | operational companion | illustrate payload shape without creating rules | provisional |
| `pageevidence_roadmap.png` | visual planning artifact | operational companion | maintained derived representation of `PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md`; update together | no |
| `PAGE_EVIDENCE_STRENGTHENING_IMPLEMENTATION_RECORD_TEMPLATE.md` | implementation record template | operational companion | standardize later implementation notes if adoption occurs | provisional |
| `PAGE_EVIDENCE_STRENGTHENING_PACK_VERIFICATION_REPORT.md` | pack integrity record | operational companion | record pack-only verification and limits | provisional |

### Archive / context docs

These are non-authoritative context artifacts.

| document | role | authority tier | intended use | should be ordinalized/adopted? |
| --- | --- | --- | --- | --- |
| `pageevidence_v10_codex_handoff.md` | handoff history | archive/context | continuation aid and historical context only | no |

Rule:

- if a rule exists only in an operational companion doc, move that rule into an active control doc before adoption/insertion
- operational docs should point back to this classification table rather than carrying competing partial authority maps
- current-branch status notes should distinguish between:
  - historical comparison baseline
  - current realized branch state
  - future pack-prepared but not yet justified work

## Recommended reading order

1. README / front door
2. separation boundary
3. execution packet
4. selector-semantics / behavior-drift policy
5. Lane A equivalence / no-drift gate
6. representative fixture lock
7. schema/artifact compatibility policy
8. hidden-consumer compatibility checklist
9. blast-radius / before-after topology
10. pass-level allowed file manifest
11. roadmap / decision notes
12. operational companion docs as needed

## Core pack objective

> Strengthen PageEvidence by reconstituting it as a shared deterministic evidence extractor, with candidate-policy projection separated from the core extraction layer, while preserving the current baseline-default runtime posture, avoiding outward contract widening, and improving calibration and disagreement visibility for the admitted Candidate A path.

## Documentation stop rule

Do **not** add new docs or broaden the pack unless one of the following happens:

1. live repo truth changes materially
2. Lane Class B is explicitly opened
3. hidden-consumer reality changes materially
4. implementation planning exposes a contradiction the current pack cannot resolve cleanly
5. pack overlap becomes large enough that merge/reduction is justified

If none of those triggers is present, prefer tightening existing docs over adding new ones.
