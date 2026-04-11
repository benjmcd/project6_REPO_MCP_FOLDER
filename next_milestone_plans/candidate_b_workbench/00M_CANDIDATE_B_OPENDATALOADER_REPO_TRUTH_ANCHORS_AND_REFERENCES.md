# 00M - Candidate B OpenDataLoader Repo-Truth Anchors and References

## Purpose

State exactly what was re-verified from the current merged baseline and what remains implementation-day preflight rather than live repo truth.

## Verified current baseline anchors

### A. Baseline source branch and commit
Candidate B planning is reconciled against merged `main` at baseline commit:
- `88d7e0f0` (`docs(pageevidence): adopt pack into repo control spine`)

### B. Current merged-main control posture
Verified from the live merged-main control docs:
- `baseline` remains the default posture
- `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` value
- Candidate B remains non-admitted
- the PageEvidence Lane Class A objective is closed
- Pass 2 is not needed on the merged baseline
- any later PageEvidence or candidate work requires a new explicit freeze

Authority refs:
- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md`
- `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
- `05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`
- `next_milestone_plans/pageevidence/README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
- `next_milestone_plans/pageevidence/PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md`

### C. Current owner-path and Candidate A anchors
Verified from live files on merged `main`:
- `backend/app/services/nrc_aps_document_processing.py` remains the protected integrated owner path
- admitted visual-lane modes are still `baseline` and `candidate_a_page_evidence_v1`
- `backend/app/services/nrc_aps_page_evidence.py` now contains the current shared extraction plus Candidate A projection split
- `tools/run_nrc_aps_page_evidence_workbench.py` is the current Candidate A workbench runner

### D. Current baseline proof anchors
Verified on disk:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`

### E. Current pinned Candidate A artifact
Verified on disk:
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`
- SHA256: `2A999C1CC2452FDFD539349B9D324241CE2D35B04864CAFA854EB0DEB77E5959`

Supporting baseline hashes captured in this reconciliation pass:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json` -> `D6554DCA48DFFEFCDCA89F486E1A60559F53E999C7E0662907E97AE8713645D1`
- `backend/app/services/nrc_aps_page_evidence.py` -> `F0E8B7FF2FCC917FE834B61E39ADC1645012B16EBB0EC0E189454462FDCD1D8A`
- `tools/run_nrc_aps_page_evidence_workbench.py` -> `DDC9F457ECDB70A7E74F46ACEBBE5A3F474A573C31124E5C85BD20D70361FBA8`

### F. Root-repo authority anchors
Verified on disk:
- `README.md`
- `REPO_INDEX.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`

### G. Missing navigation aid
`.codesight/wiki/index.md` is not present on the merged-main baseline used for this pass.
It is therefore not treated as an authority source here.

## What remains preflight rather than current repo truth

This pass did not promote the following to live repo truth:
- actual OpenDataLoader package availability on the future implementation machine
- actual OpenDataLoader package hash revalidation on implementation day
- current OpenDataLoader license confirmation on implementation day
- Java availability on implementation day
- wrapper API or signature verification on implementation day
- exact future Candidate B label sidecar contents

Those items remain future implementation preflight burden.

## Planning implication

The correct Candidate B posture is now:
- merged-main grounded
- baseline preserving
- admitted Candidate A aware
- workbench-only
- non-interfering by default
- dependency cautious

That is the minimum truthful basis for a future Candidate B implementation lane.
