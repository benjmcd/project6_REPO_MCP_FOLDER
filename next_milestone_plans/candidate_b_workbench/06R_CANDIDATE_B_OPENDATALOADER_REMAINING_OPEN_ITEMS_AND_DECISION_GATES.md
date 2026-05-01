# 06R - Candidate B OpenDataLoader Remaining Open Items and Decision Gates

## Purpose

List only the genuinely remaining open items after planning adoption reconciliation and the implementation-entry preflight/envelope freeze.

Many earlier ambiguities are now closed.
What remains open now is narrower, explicit, and separated from what this pass already froze.

---

## Resolved in this pass - docs destination

Resolved posture:
- keep the pack in `next_milestone_plans/candidate_b_workbench/`
- treat that path as committed, non-authoritative planning/workbench storage on `main`
- do not relocate the pack into `docs/nrc_adams/...` in v1

---

## Resolved in this pass - secondary Candidate A comparison decision

Resolved posture:
- first-pass secondary Candidate A comparison = `NO`
- baseline comparison remains mandatory
- any later Candidate A comparison requires a separate explicit freeze

---

## Resolved in this pass - exact first-run sidecar labels

Resolved posture:
- the exact first-run label sidecar is now frozen at `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- the frozen first-run fixture scope is `ml17123a319`, `layout`, `fontish`, `scanned`, and `mixed`
- do not backfill labels after seeing results

---

## Resolved in this pass - package/source/hash posture

Resolved posture:
- exact package source for this pass is the `opendataloader-pdf==2.0.0` PyPI release plus its published wheel
- exact published wheel SHA256 is `18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e`
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt` is the frozen sidecar requirements surface for later install
- implementation-day revalidation of the release line remains required, but that is now a known future burden rather than a planning ambiguity

---

## Remaining open item 1 - invocation tightening vs committed implementation

### What remains open
The current committed workbench support on `main` launches `sys.executable -m opendataloader_pdf`.
It does not yet use a direct `opendataloader_pdf.convert(...)` call.

### Hard rule
Do not describe direct-wrapper invocation as a current committed `main` fact unless the support module changes.

---

## Remaining open item 2 - dedicated compare pytest surface

### What remains open
The compare-surface lane adds `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`,
and an explicit isolated proof run has now been recorded locally from a prepared environment on this lane.

### Hard rule
Do not overstate validate-only green status as if it proves the full artifact-generating compare path has already been exercised.

---

## Remaining open item 3 - non-interference proof serialization depth

### What remains open
The committed support module defines `git_protected_diff()`,
but the committed proof/compare/retention artifacts do not serialize a touched-file inventory.

### Hard rule
Do not overstate the current committed artifacts as if they already include protected-diff inventory.
Treat that as a future hardening opportunity only.

---

## Remaining open item 4 - historical report provenance normalization

### What remains open
The committed proof/compare artifacts carry sibling-worktree provenance fields such as worktree-specific `repo_root` values and prior-iteration report references.

### Hard rule
Treat those artifacts as historical workbench evidence,
not as clean-`main` rerun proof.

---

## Remaining open item 5 - commit posture for any derived sample outputs

### What remains open
Whether a very small redacted sample of raw ODL output should ever be committed for reviewer convenience.

### Hard rule
Default answer is no.
Any committed sample output requires a separate explicit decision after the first proof run.

---

## Remaining open item 6 - compare proof evidence disposition

### What remains open
The compare surface is implemented on this lane, and one explicit isolated proof run has now been completed locally, including:

- a repo-native `project6.ps1` compare action
- a dedicated compare runner
- a fresh baseline-summary source for normal reruns
- a dedicated validate-only compare pytest file

The artifact-disposition decision is now closed: the completed proof artifacts remain local-only operator evidence and are not preserved in tracked history.

### Hard rule
Do not describe the compare surface artifacts as preserved in tracked history or as canonical repo evidence. Treat them only as local archived operator evidence.

---

## Resolved in this pass - compare surface landed status

Resolved posture:
- the compare surface is no longer the next planned lane; it is already landed on `main`
- future Candidate B planning must start from that shipped compare posture rather than from the older compare-gap assumptions

---

## Resolved in this pass - first inspection-lane classification boundary

Resolved posture:
- the first Candidate B inspection lane must remain bundle-scoped
- it must not modify `visual_lane_mode`
- it did not add Candidate B to the normal review run selector in that first inspection pass

### Hard rule
Do not describe Candidate B Trace as if it requires runtime admission in the first pass.
The later runtime-admission program was reopened explicitly and remains distinct from Candidate B Trace.

---

## Resolved in this pass - annotated PDF retention contract

Resolved posture:
- the Candidate B Trace lane now requests annotated PDF output from the pinned package
- the retained artifact contract now canonicalizes it under the approved raw-output root
- annotated PDF presence remains bundle-scoped and does not imply runtime admission

### Hard rule
Do not widen annotated PDF retention beyond the approved Candidate B raw-output root without a separate explicit reopen.

---

## Resolved in this pass - Candidate B Trace implementation lane

Resolved posture:
- compare manifests and Candidate B compare columns now expose `candidate_b_trace`
- the separate Candidate B-specific inspection page and API family now exist in the additive lane
- Candidate B Trace still does not enter the normal run selector or `visual_lane_mode` family

### Hard rule
Do not describe Candidate B Trace as document-trace parity or runtime admission.
It remains a separate additive inspection surface.

---

## Resolved in this pass - compare-pack bridge note

Resolved posture:
The shipped Workbench Compare docs and the Candidate B planning pack now align on one point:

- baseline and Candidate A deep links remain document-trace routes
- Candidate B deep links now reach the separate additive `Candidate B Trace` page
- Candidate B Trace remains outside the existing single-run `document-trace` contract

### Hard rule
Do not collapse that distinction in future edits.

---

## Resolved in this pass - compare-lane contract freeze

Resolved posture:
- exact action name = `compare-nrc-aps-candidate-b`
- exact compare-runner public flags = optional `--run-root` and optional `--plan-only` only
- exact baseline-tool public flags = required `--runtime-root`, `--proof-report`, and `--out`
- exact default output root = `tests/reports/cb-compare-<run_id>/`
- exact durable top-level outputs = `baseline-summary.json`, `proof.json`, `compare.json`, `retain.json`
- exact baseline proof posture = explicit `baseline-before/runtime` and `baseline-after/runtime` roots with `--require-ocr`
- protected-diff serialization is out of scope for the first pass
- no new Candidate B sidecar manifest is authorized in the first pass

---

## Resolved in this pass - post-PR50 shipped baseline freeze

Resolved posture:
- the shipped baseline now includes:
  - Workbench Compare
  - Candidate B Trace
  - inline annotated PDF delivery
  - first-load Candidate B Trace defaulting to `annotated_pdf` when present
- future planning in this pack must start from that landed posture
- do not treat already-shipped compare or trace behavior as if it were still an open implementation question

### Hard rule
Do not reopen shipped compare/trace behavior by implication.
Only reopen if a repo-confirmed blocker or explicit product decision requires it.

---

## Resolved in this pass - repo-native browser regression coverage

Resolved posture:
- the repo now carries its own targeted browser regression coverage for the shipped compare + Candidate B Trace flow
- the landed coverage is rooted in:
  - `e2e/nrc-aps-review.spec.js`
  - `playwright.config.js`
  - `.github/workflows/playwright.yml`
  - `backend/tests/review_browser_fixture.py`
  - `backend/tests/review_browser_server.py`
  - `backend/tests/requirements-browser.txt`
- the covered minimum assertions now include:
  - Workbench Compare deep-links into Candidate B Trace
  - Candidate B Trace first-load defaults to `annotated_pdf`
  - annotated PDF is requested with inline disposition
  - baseline and Candidate A still route to `document-trace`
  - no query/path leakage reaches browser-visible surfaces in the covered flow

### Hard rule
Do not describe external audit screenshots or manual passes as the primary enforcement surface for this shipped flow now that repo-native browser coverage exists.

---

## Resolved in this pass - Playwright scaffold disposition

Resolved posture:
- the root Playwright workflow is no longer placeholder-only smoke
- the repo chose the `replace with targeted NRC APS browser coverage` path for the root workflow
- future Playwright questions are now about explicit coverage expansion/refinement, not about whether the root path is authoritative at all

### Hard rule
Do not describe the root Playwright workflow as placeholder smoke for this surface unless and until a later change actually removes or bypasses the targeted NRC APS browser coverage.

---

## Resolved in this pass - current-horizon Candidate B scope decision

Resolved posture:

- retain the shipped bundle-scoped compare + Candidate B Trace boundary as the current-horizon endpoint for Candidate B
- do not open runtime admission, selector admission, or widened runtime classification for Candidate B in the current horizon
- treat any later runtime-style Candidate B move as a separate explicit reopen rather than as continuation of the current shipped lane

Post-reopen status:
- A later concrete product/operator requirement has now explicitly opened Option B for Phase 1.
- The implementation admits Candidate B as `document_processing_engine="candidate_b_opendataloader_pdf"` on the existing NRC APS run-submit flow and exposes optional runtime metadata on the existing review `/runs` selector response.
- Bounded follow-ups render Candidate B / OpenDataLoader PDF in the existing review/document-trace selectors and add an explicit Workbench Compare runtime-source option while preserving the shipped bundle-scoped compare + Candidate B Trace path.
- This does not add Candidate B Trace parity for admitted runtime runs, document-trace parity expansion, broad routes, DB schemas, DB models, migrations, new run-submission UI, or persistence redesign.

### Option A - historical bundle-scoped compare + trace boundary
Posture:

- This was the earlier current-horizon boundary for Candidate B workbench inspection.
- Candidate B bundle evidence remains available through Workbench Compare plus Candidate B Trace.
- Candidate B still remains outside `visual_lane_mode`.
- Candidate B bundle evidence continues to use bundle-root identity rather than runtime-root identity.

Recommendation:

- this remains the correct boundary for bundle-scoped Candidate B Trace, but it no longer describes the full current runtime-admission program after the explicit Option B reopen

Why this is the repo-fit default:

- the current shipped compare goal is already met on `main`
- Candidate B artifacts are bundle-root and ODL-native, not current owner-path review-runtime rows
- the current Candidate B Trace page already exposes the ODL-native inspection surface that the compare lane needed
- the repo now has targeted browser enforcement for the shipped compare + Candidate B Trace flow
- keeping Candidate B Trace bundle-scoped still avoids widening that trace surface without a repo-confirmed need

### Option B - open a separate Candidate B runtime-admission program
Posture:

- Candidate B would move toward runtime-style identity instead of bundle-only identity
- Candidate B would need explicit decisions for selector visibility, runtime classification, trace behavior, and persistence semantics

Current recommendation:

- this program was not opened by the earlier current-horizon decision
- it is now opened only because an explicit product requirement requires Candidate B / OpenDataLoader PDF to run through the corpus ingestion/processing path
- the current admitted scope is processing-engine admission plus existing `/runs` runtime metadata, rendered review/document-trace selector visibility, and explicit Workbench Compare runtime-source selection; Candidate B Trace parity for admitted runtime runs and document-trace parity expansion remain follow-on decisions

### Reopen triggers that justified Option B
At least one of these had to become true before runtime-style Candidate B work was justified:

- operators must select Candidate B from the normal run selector rather than arriving through compare or bundle-backed deep links
- Candidate B must participate in runtime-root-only workflows that cannot consume bundle-backed inspection
- Candidate B must be represented as a normal review/runtime row for downstream product behavior rather than as separate compare evidence
- bundle-scoped Candidate B Trace proves insufficient for a concrete, repo-confirmed operator task

### Expected blast radius if Option B is chosen later
This would no longer be a narrow Candidate B Trace follow-on.
It would likely widen at least:

- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/review_nrc_aps_workbench_compare.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/api/review_nrc_aps.py`
- review/runtime DB assumptions and fixture/seed flows
- operator docs in `frontend_UI_plans/`
- cross-pack assumptions in `next_milestone_plans/multi_variant_visual_lane_control/`

### Current default posture remains:

- bundle-scoped inspection surface
- runtime admission exists for the opt-in processing engine path
- the normal `/runs` response exposes Candidate B runtime metadata
- existing review/document-trace selectors render Candidate B / OpenDataLoader PDF labels
- Workbench Compare can select admitted Candidate B runtime runs through `candidate_b_source_kind=runtime` without reusing `candidate_b_bundle_id`

### Hard rule
Do not drift from the explicitly reopened processing-engine, `/runs` metadata, rendered-selector, and Workbench Compare runtime-source tranches into Candidate B Trace parity, document-trace parity expansion, broad routes, DB schemas/models/migrations, new run-submission UI, or widened persistence by incidental follow-on edits.
Do not describe Option B as a small follow-up to Candidate B Trace; it is a separate widened program and is now being reopened only in explicit bounded tranches.

---

## Remaining open item 7 - bundle-scoped operator ergonomics

### What remains open
For the preserved bundle-scoped Candidate B Trace path, there is still room for narrow operator-ergonomics improvement after hardening and scope decisions.

### Candidate examples
- stronger fixture-to-fixture navigation in Candidate B Trace
- clearer missing-artifact states
- better artifact affordances around annotated PDF, raw JSON, and raw Markdown
- compact operator shortcuts from compare to trace and back

### Hard rule
Do not broaden ergonomics work into runtime admission, schema widening, or document-trace parity by stealth.

---

## Resolved in this pass - prepared-state/operator workflow hardening

Resolved posture:

- the repo now carries one canonical same-checkout prep sequence for populated compare + Candidate B Trace operator validation:
  - `py -3.12 .\tools\seed_wb_compare.py --visual-lane-mode baseline`
  - `py -3.12 .\tools\seed_wb_compare.py --visual-lane-mode candidate_a_page_evidence_v1`
  - `.\project6.ps1 -Action compare-nrc-aps-candidate-b`
  - `py -3.12 .\tools\validate_wb_prep.py`
- `tools/validate_wb_prep.py` is now the validate-only fail-closed prep gate for same-checkout readiness
- the validator fails closed on empty, donor, ambiguous, or incoherent same-checkout prep state
- populated operator validation should now start from that canonical prep gate rather than from ad hoc source discovery or donor-worktree assumptions

### Hard rule
Do not rely on ambiguous or donor-worktree prep state when validating shipped compare/trace behavior.

---

## Resolved in this pass - documentation closeout

Resolved posture:

- active operator/front-door docs now point at one canonical flow:
  - `frontend_UI_plans/README.md` = front-door index
  - `frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md` = explicit backend binding and route bring-up
  - `frontend_UI_plans/wb-compare-validation.md` = same-checkout prep, `tools/validate_wb_prep.py`, and populated compare/Candidate B Trace validation
  - `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md` = broader manual validation pass after startup and prep succeed
- this pack stays focused on Candidate B planning/control rather than duplicated operator walkthrough steps

### Hard rule
Do not reintroduce ambiguity about which doc owns startup, prep, or broader manual validation for the shipped Option 1 flow.
