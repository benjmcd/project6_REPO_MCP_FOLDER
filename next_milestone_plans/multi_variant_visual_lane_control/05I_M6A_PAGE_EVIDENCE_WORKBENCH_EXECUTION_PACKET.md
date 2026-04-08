# 05I M6A PageEvidence Workbench Execution Packet

## Purpose

Freeze the concrete execution packet for the first dedicated PageEvidence / Candidate workbench lane.

This packet turns the chosen Option 2 direction into a bounded executable plan without confusing it with direct integrated admission.

---

## Status note

This packet is built on:

- achieved M3/M4 closure,
- achieved M5 coexistence / visibility barrier closure,
- the frozen direct-admission packet in `03AA` + `05H`,
- and the new M6A boundary frozen in `03AB`.

This packet does **not** itself admit Candidate A.
It freezes the owner boundary, validation boundary, location strategy, widening rules, and no-drift rules for the dedicated workbench lane.

---

## Current milestone position

- M3 baseline-only selector bootstrap is merged and accepted.
- M4 acceptance closure is merged and recorded.
- M5 coexistence / visibility barrier is merged and recorded.
- Direct M6 admission remains frozen but fail-closed under `03AA` + `05H`.
- The immediate next bounded lane is now **M6A**: a dedicated PageEvidence workbench for Candidate A.

What remains before direct M6 admission can be called approve-as-is is not immediate owner-path widening.
It is a bounded M6A lane that:

1. creates a dedicated PageEvidence workbench surface,
2. keeps integrated runtime behavior unchanged by default,
3. captures Candidate A evidence in isolated form,
4. and prepares a later exact target record for M6B.

---

## Exact working-location rule

### Current planning/freeze lane

- `worktrees/mvvlc-candidate-a-freeze-next`

### Later workbench implementation lane

Start from a fresh merged-`main` worktree.
Recommended location:

- `worktrees/mvvlc-page-evidence-workbench-next`

### Later direct-admission lane

Start from a separate fresh merged-`main` worktree.
Recommended location:

- `worktrees/mvvlc-candidate-a-admission-next`

### Disallowed working location

- the dirty root workspace

---

## Canonical live authority chain for the M6A lane

The M6A lane must start from these live authority files:

- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `tools/run_nrc_aps_document_processing_proof.py`
- `tools/nrc_aps_promotion_gate.py`
- `tools/nrc_aps_promotion_tuning.py`

The M6A lane must also respect:

- `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
- `03E_VARIANT_IDENTITY_VISIBILITY_POLICY.md`
- `03J_ARTIFACT_EQUIVALENCE_CONTROL_POLICY.md`
- `03K_DIAGNOSTICS_REF_PERSISTENCE_POLICY.md`
- `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`
- `03M_SELECTOR_ACTIVATION_SCOPE_AND_LIFETIME_POLICY.md`
- `03N_EXPERIMENT_ISOLATION_MECHANISM_POLICY.md`
- `03Y_REVIEW_REPORT_EXPORT_FIELD_SENSITIVITY_MAP.md`
- `03Z_EXACT_M5_BASELINE_VISIBILITY_AND_RUNTIME_ROOT_COEXISTENCE_MECHANISM.md`
- `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
- `03AB_EXACT_M6A_PAGE_EVIDENCE_WORKBENCH_AND_OPTION2_BOUNDARY.md`
- `05H_M6_APPROVE_AS_IS_EXECUTION_PACKET.md`
- `06E_BLOCKER_DECISION_TABLE.md`
- `06J_CANONICAL_ACCEPTANCE_COMMAND_CONVENTION.md`
- `06K_SHELL_SPECIFIC_CANONICAL_ACCEPTANCE_COMMANDS.md`

---

## Exact pre-edit stop conditions

The M6A lane must stop before editing if any of the following is true:

1. the needed implementation would directly admit a non-`baseline` selector value
2. the needed implementation would edit the M5 visibility barrier path by default
3. the needed implementation would add empty candidate-specific A/B/C scaffolding
4. the needed implementation would require new outward variant-identity fields
5. the needed implementation would depend on shared seeded runtime data
6. the needed implementation would reopen OCR / hybrid OCR / media-scope boundaries

If a stop condition is encountered, report it explicitly instead of widening by inference.

---

## Exact lane outcome required

The M6A lane must make all of the following true:

1. a dedicated PageEvidence workbench surface exists
2. Candidate A can be executed through that workbench in isolated mode
3. integrated runtime behavior remains unchanged by default
4. no new outward review/API/report/export identity fields are introduced
5. any workbench outputs are isolated and do not contaminate shared runtime roots
6. Candidate A evidence produced by the workbench is suitable for later explicit approval review
7. direct M6 admission remains separately fail-closed until a later target record exists

If the implementation cannot make all seven true, it is not approve-as-is for M6A.

---

## Exact owner-file boundary

### Primary owner files expected to change

These are the only files that should be assumed editable at the start of the M6A lane:

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

### Inspect-only compatibility files

These must be inspected for compatibility, but should remain edit-free unless a repo-confirmed blocker forces widening:

- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `tools/run_nrc_aps_document_processing_proof.py`
- `tests/test_nrc_aps_document_processing.py`
- `backend/tests/test_nrc_aps_run_config.py`

### Exact scope exclusion

The default M6A lane does **not** authorize:

- edits to `connectors_nrc_adams.py`
- edits to `nrc_aps_artifact_ingestion.py`
- edits to `review_nrc_aps_runtime.py`
- direct `visual_lane_mode` admission widening
- report/export/schema widening
- candidate B/C code surfaces
- runtime-root allowlist changes

---

## Exact validation boundary

### Required workbench bundle

- `backend/tests/test_nrc_aps_page_evidence.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- `tests/test_import_guardrail.py`

### Required baseline-compatibility bundle

- `backend/tests/test_nrc_aps_run_config.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_artifact_ingestion_gate.py`

### Performance posture

`06I` is **not** mandatory for a pure standalone-workbench lane.

Rerun `06I` only if the lane widens into:

- integrated owner-path execution,
- companion-run behavior inside normal ingestion,
- or another touched surface that can affect merged runtime cost.

---

## Exact widening rules

The M6A lane must not widen casually.

Allowed widening trigger classes are only:

1. the workbench cannot be exercised without a narrow shared-helper extraction from the existing PDF seam
2. the standalone workbench runner cannot be validated without a narrow fixture/runner compatibility change
3. an inspect-only file proves to be the real canonical location for PageEvidence logic and the default owner set would create duplication debt

Every widening decision must be recorded explicitly in the final report as:

- file widened into
- reason class
- why the default owner set was insufficient
- what new risk the widening introduced

---

## Exact no-drift assertions the lane must prove

The M6A lane must prove all of the following:

- baseline integrated runtime remains unchanged by default
- no non-`baseline` selector value is admitted through the owner path
- no new outward review/API/report/export identity fields were introduced
- no review/runtime/report/export/package visibility rules were widened
- no shared runtime roots were seeded or contaminated by validation
- workbench outputs remain isolated to explicit caller-owned or temp locations

---

## Exact status language allowed at the end of the lane

The next lane may be described as approve-as-is only if it provides:

1. a dedicated PageEvidence workbench surface
2. passing execution evidence for the required M6A validation bundles
3. explicit no-drift findings for the baseline owner path and visibility surfaces
4. explicit evidence that Candidate A remains pre-admission rather than silently integrated

Do not use direct-admission language such as:

- admitted
- promoted
- integrated variant closed
- M6 complete

unless the later `03AA` + `05H` packet has actually been satisfied.

---

## Immediate next action after this packet

The next justified move is:

1. keep working on a fresh merged-`main` M6A workbench lane
2. implement the dedicated PageEvidence surface only within the packet frozen here
3. validate it in isolated standalone form
4. capture Candidate A evidence refs and outputs
5. freeze that lane separately
6. only then decide whether a later M6B admission record is justified

The project is now prepared enough to proceed with M6A,
but direct integrated admission remains intentionally fail-closed.
