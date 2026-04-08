# 05O Post-Admission Defaulting Planning Freeze Packet

## Purpose

Freeze the exact planning packet for the post-admission/defaulting phase that follows merged M6B Candidate A closure.

This packet is for explicit planning and decision framing.
It is not a code-execution packet.

---

## Status note

Merged `main` already contains the admitted Candidate A state recorded by:

- `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`
- `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`

So the current question is no longer whether Candidate A can be admitted.
The current question is how later post-admission/defaulting scope should be decided without widening by inference.

That current-horizon decision has since been frozen explicitly in:

- `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`

---

## Current state entering this planning packet

1. `baseline` remains the default for missing, invalid, unsupported, and unapproved `visual_lane_mode` values.
2. `candidate_a_page_evidence_v1` is the only admitted non-`baseline` value on merged `main`.
3. Candidate A is review-visible under the already-admitted rules.
4. Candidate A is not the default.
5. Candidate B and Candidate C remain non-admitted.

---

## Required authority set

Read together:

1. `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
2. `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
3. `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
4. `03AC_EXACT_POST_ADMISSION_DEFAULTING_SCOPE_AND_DECISION_BOUNDARY.md`
5. `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`
6. `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`
7. `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`
8. `06E_BLOCKER_DECISION_TABLE.md`
9. `06I_LOCAL_PERFORMANCE_BASELINE_AND_REGRESSION_CHECK_SPECIFICATION.md`

---

## Exact decision questions for this planning phase

1. Should the current `00D` program rule that `baseline` remains the default be reaffirmed for the current horizon?
2. If not, is `candidate_a_page_evidence_v1` the only selector value eligible for any future default-promotion discussion?
3. What exact evidence beyond `05M`, `05N`, and the accepted `06I` results would be required before any explicit program-decision amendment or default-promotion record could be frozen?
4. Should Candidate B and Candidate C remain explicitly non-admitted for the current horizon?
5. Should OCR-routing, media scope, policy tuning, and outward identity expansion remain explicitly locked?

---

## Required modules, components, and outward surfaces to consider

### Core owner path

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/review_nrc_aps_runtime.py`

### Conditional downstream surfaces

- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_overview.py`
- `backend/app/services/review_nrc_aps_details.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

### Frozen persistence and contract surfaces to re-check if any later proposal touches shared downstream representation

- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/aps_retrieval_plane.py`
- `backend/app/services/aps_retrieval_plane_contract.py`
- `backend/app/services/aps_retrieval_plane_read.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_citation_pack.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/schemas/api.py`
- `backend/app/models/models.py`

### Existing externalized route classes

- run submission through `POST /connectors/nrc-adams-aps/runs`
- review run selection through `GET /review/nrc-aps` and `GET /runs`
- review/document-trace entry through `GET /review/nrc-aps/document-trace`
- run-bound review and document endpoints under `/runs/{run_id}/...`
- NRC APS evidence-bundle/citation-pack endpoints
- NRC APS evidence-report/export/package endpoints

### Frozen dependency posture

- current deterministic PageEvidence / PyMuPDF mechanism only
- no new libraries, packages, schemas, models, or migrations in scope for this planning phase

---

## Allowed outcomes

This planning phase may end in only one of these explicit outcomes:

1. **Retain baseline default**
   - keep `baseline` as the default
   - keep Candidate A admitted but non-default
   - keep Candidate B/C non-admitted

2. **Open exact Candidate A default-promotion target-definition work**
   - still no code
   - first freeze an explicit program-decision amendment to the current `00D` baseline-default rule
   - then freeze one exact later target-definition lane for Candidate A only
   - carry forward exact evidence and no-drift requirements before any implementation

3. **Explicit defer**
   - preserve current merged-main behavior
   - state that broader defaulting work is intentionally deferred

---

## Prohibited outcomes

This planning phase must not:

1. start implementation by implication
2. admit Candidate B or Candidate C
3. promote Candidate A to default in code
4. reopen OCR-routing or media scope
5. introduce policy tuning or threshold retuning
6. add outward variant-identity fields
7. introduce new libraries, packages, schema surfaces, model changes, or migrations

---

## Decision-quality bar

No later default-promotion target-definition should be opened unless the planning result can state, explicitly:

1. which selector value is under consideration
2. what exact defaulting behavior would change
3. what exact behaviors and surfaces would remain unchanged
4. what additional evidence or validation would be required
5. what modules, endpoints, and downstream surfaces would need re-audit
6. what stop conditions would still block widening

---

## Next-step rule

At the time this packet was frozen, the next justified move was not generic implementation.

It is either:

1. a docs-only retain-`baseline`-as-default decision record
2. a docs-only explicit program-decision-amendment plus exact Candidate A default-promotion target-definition lane
3. an explicit defer record preserving the current admitted-but-non-default state

No code lane should begin until one of those outcomes is frozen explicitly.
