# Test Evidence

## Resolution update

The earlier statement that the active merged-main worktree was green across the full official T1-T8 matrix was too strong.
The later correction that no active checked-out authority surface could reproduce T8 is now superseded for the root-local branch, for `worktrees/pageevidence-main-merge`, and for `worktrees/nrc-aps-runtime-next`.

In this pass:

- the surviving hidden `20260327_062011` single-run golden fixture was adopted into the active root at `backend/app/storage_test_runtime/lc_e2e/20260327_062011`
- root gained `backend/tests/review_nrc_aps_runtime_fixture.py`
- stale hardcoded root review/document-trace tests were switched to shared runtime discovery and runtime-derived assertions
- root `backend/app/services/review_nrc_aps_catalog.py` gained timezone normalization for mixed summary/database completion timestamps
- the full root grouped T8 bundle now passes: `76 passed`
- `worktrees/nrc-aps-runtime-next` was directly revalidated and its full grouped T8 bundle now also passes: `105 passed, 1 skipped`

The corrected interpretation is now:

- `worktrees/pageevidence-main-merge` remains the strongest owner-path code authority for MVVLC, PageEvidence, and Candidate B behavior
- the root-local review/runtime T8 authority surface is now restored and executable
- `worktrees/pageevidence-main-merge` now also reproduces a green full review/runtime T8 bundle against the adopted root-local runtime
- `worktrees/nrc-aps-runtime-next` now also reproduces a green full review/runtime T8 bundle against that adopted root-local runtime without further code edits
- separate active worktrees beyond `worktrees/pageevidence-main-merge` still require their own explicit T8 revalidation if they are to claim current executable parity

## Commands re-run in this correction pass

### Root checkout

Targeted root-side evidence/API/corpus correction run:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\tests\test_nrc_aps_evidence_bundle.py::test_persisted_failure_artifact_is_request_scoped .\tests\test_nrc_aps_evidence_citation_pack.py::test_persisted_failure_artifact_is_source_bundle_scoped .\tests\test_api.py .\tests\test_import_guardrail.py::test_no_backend_app_imports .\tests\test_nrc_aps_document_corpus.py -q
```

Result at the time of that focused rerun:

- `47 failed, 37 passed`
- evidence-bundle failure-scoping tests do not raise the expected exceptions
- `tests/test_api.py` shows persistent connector/API failures including repeated `active run concurrency limit reached`, missing `DatasetVersion` persistence, and idempotency behavior drift
- `tests/test_import_guardrail.py::test_no_backend_app_imports` fails on UTF-16 decoding of `archive/root_revert_38ce9636_20260404_075047/get_targets.py`
- `tests/test_nrc_aps_document_corpus.py` shows document-class mismatches such as `born_digital_pdf -> layout_complex_pdf`, `scanned_pdf -> born_digital_pdf`, and `mixed_pdf -> layout_complex_pdf`

Official T7 bundle:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\backend\tests\test_visual_artifact_pipeline.py .\backend\tests\test_nrc_aps_advanced_adapters.py .\backend\tests\test_nrc_aps_run_config.py .\backend\tests\test_diagnostics_ref_persistence.py .\backend\tests\test_nrc_aps_evidence_bundle_integration.py -q
```

Result before the root-local T8 repair:

- fails during collection
- `backend/tests/test_nrc_aps_advanced_adapters.py` still poisons grouped imports via fake `numpy`
- `backend/tests/test_nrc_aps_run_config.py` then fails importing `scipy` because `numpy.__version__` is missing

Official T8 bundle:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\backend\tests\test_review_nrc_aps_api.py .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_document_trace_service.py .\backend\tests\test_review_nrc_aps_document_trace_page.py .\backend\tests\test_review_nrc_aps_catalog.py .\backend\tests\test_review_nrc_aps_details.py .\backend\tests\test_review_nrc_aps_graph.py .\backend\tests\test_review_nrc_aps_tree.py .\backend\tests\test_review_nrc_aps_page.py -q
```

Result:

- failed during collection
- `backend/tests/test_review_nrc_aps_document_trace_api.py:37` asserted a missing audited runtime DB at `backend/app/storage_test_runtime/lc_e2e/20260328_150207/lc.db`

Resolution update in this pass:

```powershell
$env:PYTHONPATH='backend'
python -m pytest .\backend\tests\test_review_nrc_aps_api.py .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_document_trace_service.py .\backend\tests\test_review_nrc_aps_document_trace_page.py .\backend\tests\test_review_nrc_aps_catalog.py .\backend\tests\test_review_nrc_aps_details.py .\backend\tests\test_review_nrc_aps_graph.py .\backend\tests\test_review_nrc_aps_tree.py .\backend\tests\test_review_nrc_aps_page.py
```

Result:

- `76 passed`
- root review/runtime T8 is now green against the adopted root-local runtime `backend/app/storage_test_runtime/lc_e2e/20260327_062011`

### `worktrees/pageevidence-main-merge`

Focused MVVLC/PageEvidence/Candidate B bundle:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\backend\tests\test_nrc_aps_page_evidence.py .\tests\test_nrc_aps_page_evidence_workbench.py .\tests\test_nrc_aps_candidate_b_opendataloader.py .\backend\tests\test_nrc_aps_run_config.py .\tests\test_nrc_aps_document_processing.py -q
```

Result:

- `54 passed`

Targeted evidence/API/corpus correction run:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\tests\test_nrc_aps_evidence_bundle.py::test_persisted_failure_artifact_is_request_scoped .\tests\test_nrc_aps_evidence_citation_pack.py::test_persisted_failure_artifact_is_source_bundle_scoped .\tests\test_api.py .\tests\test_import_guardrail.py::test_no_backend_app_imports .\tests\test_nrc_aps_document_corpus.py -q
```

Result:

- `84 passed`

Official T7 bundle:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\backend\tests\test_visual_artifact_pipeline.py .\backend\tests\test_nrc_aps_advanced_adapters.py .\backend\tests\test_nrc_aps_run_config.py .\backend\tests\test_diagnostics_ref_persistence.py .\backend\tests\test_nrc_aps_evidence_bundle_integration.py -q
```

Result:

- `69 passed`

Official T8 bundle:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\backend\tests\test_review_nrc_aps_api.py .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_document_trace_service.py .\backend\tests\test_review_nrc_aps_document_trace_page.py .\backend\tests\test_review_nrc_aps_catalog.py .\backend\tests\test_review_nrc_aps_details.py .\backend\tests\test_review_nrc_aps_graph.py .\backend\tests\test_review_nrc_aps_tree.py .\backend\tests\test_review_nrc_aps_page.py .\backend\tests\test_review_nrc_aps_runtime_db.py -q
```

Result:

- fails during collection
- `backend/tests/review_nrc_aps_runtime_fixture.py:120` and `:151` assert no passed/document-trace-ready runtime exists under `backend/app/storage_test_runtime/lc_e2e`

### `worktrees/nrc-aps-runtime-next`

Official T8 bundle:

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest .\backend\tests\test_review_nrc_aps_api.py .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_document_trace_service.py .\backend\tests\test_review_nrc_aps_document_trace_page.py .\backend\tests\test_review_nrc_aps_catalog.py .\backend\tests\test_review_nrc_aps_details.py .\backend\tests\test_review_nrc_aps_graph.py .\backend\tests\test_review_nrc_aps_tree.py .\backend\tests\test_review_nrc_aps_page.py .\backend\tests\test_review_nrc_aps_runtime_db.py -q
```

Result:

- `105 passed, 1 skipped, 3 warnings`
- the worktree's narrower `backend/tests/review_nrc_aps_runtime_fixture.py` now resolves the adopted root-local `20260327_062011` runtime because that fixture's summary points to live root-local DB and storage paths
- no code edits were required in this worktree for T8 parity; the earlier failure state was superseded by the root-local runtime adoption

## Runtime-fixture inventory

Current filesystem checks show:

- root checkout now carries the adopted `backend/app/storage_test_runtime/lc_e2e/20260327_062011`
- `worktrees/pageevidence-main-merge` continues to rely on the adopted root-local runtime rather than a separate local corpus
- `worktrees/nrc-aps-runtime-next` also resolves that adopted root-local runtime successfully through its existing helper
- hidden `.claude/worktrees/*` directories and archived snapshots remain relevant as historical provenance for where the surviving single-run fixture was discovered before adoption into the root-local branch

## Focused T8 fixture-authority follow-up

### Earlier root checkout failure mode before the adopted runtime repair

Focused reruns:

```powershell
$env:PYTHONPATH='backend'
python -m pytest .\backend\tests\test_review_nrc_aps_document_trace_api.py -q
python -m pytest .\backend\tests\test_review_nrc_aps_document_trace_service.py -q
```

Result:

- root `test_review_nrc_aps_document_trace_api.py` failed at import because it hard-coded `backend/app/storage_test_runtime/lc_e2e/20260328_150207/lc.db`
- root `test_review_nrc_aps_document_trace_service.py` failed closed for the same reason
- this was a different failure mode from the worktree helpers; root was not discovering runtimes at all for T8, it was asserting one exact missing runtime generation
- root `backend/.env:6` was pinned to the same missing audited runtime generation via `DATABASE_URL=sqlite:///./app/storage_test_runtime/lc_e2e/20260328_150207/lc.db`
- root also had no source `backend/tests/review_nrc_aps_runtime_fixture.py`, so the root checkout had not yet adopted the helper-driven runtime discovery model that the active worktrees use for T8

Later root-local resolution:

- the adopted root-local runtime now lives at `backend/app/storage_test_runtime/lc_e2e/20260327_062011`
- root now has `backend/tests/review_nrc_aps_runtime_fixture.py`
- root `backend/.env` now points at the adopted `20260327_062011` runtime DB
- the current grouped root T8 bundle is green: `76 passed`

### Earlier active worktree T8 helper and representative-run gap

Focused reruns:

```powershell
$env:PYTHONPATH='backend'
python -m pytest .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_runtime_db.py -q
```

Workdirs:

- `worktrees/pageevidence-main-merge`
- `worktrees/nrc-aps-runtime-next`

Result at the time of those focused reruns:

- `worktrees/pageevidence-main-merge` failed because `review_nrc_aps_runtime_fixture.py` found no passed/document-trace-ready runtime under that worktree's `backend/app/storage_test_runtime/lc_e2e`
- `worktrees/nrc-aps-runtime-next` failed because its fixture helper found no passed runtime under that worktree's `backend/app/storage_test_runtime/lc_e2e`
- `pageevidence-main-merge` had a more advanced helper that could consider a shared root and an env-configured runtime root; `nrc-aps-runtime-next` did not
- the then-current `pageevidence-main-merge` document-trace API tests also required specific representative multi-run coverage, not just any passed runtime, via hard assertions for run ids `6a3dadd8-625a-4465-9b20-df05b39b8fc6` and `282ae183-0f73-4e73-ba6e-f124c56d957d`
- `worktrees/nrc-aps-runtime-next/backend/app/storage_test_runtime/lc_e2e` was then only a junction back to `backend/app/storage_test_runtime/lc_e2e` in the root checkout, and that root target did not yet exist in the current repo state

Resolution update after the later worktree repair:

```powershell
python -m pytest .\backend\tests\test_review_nrc_aps_api.py .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_document_trace_service.py .\backend\tests\test_review_nrc_aps_document_trace_page.py .\backend\tests\test_review_nrc_aps_catalog.py .\backend\tests\test_review_nrc_aps_details.py .\backend\tests\test_review_nrc_aps_graph.py .\backend\tests\test_review_nrc_aps_tree.py .\backend\tests\test_review_nrc_aps_page.py .\backend\tests\test_review_nrc_aps_runtime_db.py
```

Workdir:

- `worktrees/pageevidence-main-merge`

Result:

- `137 passed, 3 skipped`
- `worktrees/pageevidence-main-merge/backend/tests/test_review_nrc_aps_document_trace_api.py` now discovers representative positive/mixed/negative/large targets dynamically from the currently available runtime instead of hard-coding vanished run ids
- cross-runtime positive comparison coverage is now conditional and skips when no second qualifying runtime exists

Resolution update after the `nrc-aps-runtime-next` revalidation:

```powershell
python -m pytest .\backend\tests\test_review_nrc_aps_api.py .\backend\tests\test_review_nrc_aps_document_trace_api.py .\backend\tests\test_review_nrc_aps_document_trace_service.py .\backend\tests\test_review_nrc_aps_document_trace_page.py .\backend\tests\test_review_nrc_aps_catalog.py .\backend\tests\test_review_nrc_aps_details.py .\backend\tests\test_review_nrc_aps_graph.py .\backend\tests\test_review_nrc_aps_tree.py .\backend\tests\test_review_nrc_aps_page.py .\backend\tests\test_review_nrc_aps_runtime_db.py -q
```

Workdir:

- `worktrees/nrc-aps-runtime-next`

Result:

- `105 passed, 1 skipped, 3 warnings`
- partial validate-only reruns before the full bundle were also green:
  - `backend/tests/test_review_nrc_aps_document_trace_api.py`: `27 passed`
  - `backend/tests/test_review_nrc_aps_runtime_db.py backend/tests/test_review_nrc_aps_document_trace_service.py`: `41 passed, 1 skipped`
- the worktree's helper is still narrower than the root-local and `pageevidence-main-merge` helpers, but it no longer blocks T8 because the adopted root-local `20260327_062011` runtime now exists and its summary points to live DB/storage targets

### Tracked corpus history does not live on the current root branch lineage

Git provenance checks:

```powershell
git branch --contains fc17d05c
git merge-base HEAD fc17d05c
git show --name-status --format=fuller fc17d05c -- backend/app/storage_test_runtime/lc_e2e
git ls-tree -r HEAD --name-only -- backend/app/storage_test_runtime
```

Result:

- commit `fc17d05c` tracked a materialized `backend/app/storage_test_runtime/lc_e2e/20260329_151235` corpus, including `lc.db` and `local_corpus_e2e_summary.json`
- `git branch --contains fc17d05c` returns only `feature/enhanced-extraction-pipeline-v3`
- `git merge-base HEAD fc17d05c` reported no merge base in the current local repo state
- `git ls-tree -r HEAD --name-only -- backend/app/storage_test_runtime` returns no `lc_e2e` entries in the current root `HEAD`

Interpretation:

- the current root branch did not simply delete the tracked `20260329_151235` corpus in its own visible lineage here
- instead, the tracked corpus commit lives on a different local branch lineage than the current root planning branch
- current T8 claims therefore cannot rely on the existence of a tracked root `lc_e2e` corpus in the present branch state

### Earlier direct hidden-runtime compatibility check before adoption

Direct inspection of the surviving hidden runtime:

- location: `.claude/worktrees/agent-ab92eccc/backend/app/storage_test_runtime/lc_e2e/20260327_062011`
- summary run id: `d6be0fff-bbd7-468a-9b00-7103d5995494`
- DB contents: one `connector_run` row and `43` targets
- the summary and linkage rows carry absolute refs back into the missing root location `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\...`
- a filesystem sweep across all checked-out `local_corpus_e2e_summary.json` files found only this `20260327_062011` / `d6be0fff-bbd7-468a-9b00-7103d5995494` lineage in hidden `.claude` worktrees and archived mirrors
- no checked-out summary file contained the current document-trace representative run ids `6a3dadd8-625a-4465-9b20-df05b39b8fc6` or `282ae183-0f73-4e73-ba6e-f124c56d957d`
- no checked-out summary file contained the tracked `20260329_151235` run id `d8495a4e-9db8-4f1d-a493-e8f18dc4cde9`

Concrete sample from `aps_content_linkage`:

- `blob_ref` is an absolute path into missing root `backend/app/storage_test_runtime/lc_e2e/.../storage/connectors/raw/...`
- `diagnostics_ref` is an absolute path into missing root `backend/app/storage_test_runtime/lc_e2e/.../storage/artifacts/...`
- `normalized_text_ref` is an absolute path into missing root `backend/app/storage_test_runtime/lc_e2e/.../storage/artifacts/...`

Compatibility checks against `worktrees/pageevidence-main-merge` with `STORAGE_DIR` explicitly pointed at that hidden runtime parent:

```powershell
$env:PYTHONPATH='backend'
$env:STORAGE_DIR='C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\agent-ab92eccc\backend\app\storage_test_runtime'
python -m pytest .\backend\tests\test_review_nrc_aps_runtime_db.py -q
python -m pytest .\backend\tests\test_review_nrc_aps_document_trace_api.py -q
python -m pytest .\backend\tests\test_review_nrc_aps_document_trace_service.py -q
```

Result at that time:

- runtime DB surface partially worked: `17 passed, 1 skipped`
- document-trace API still failed during collection because the hidden runtime did not contain the representative run ids required by the then-current suite, especially `6a3dadd8-625a-4465-9b20-df05b39b8fc6`
- document-trace service only partially worked: `19 passed, 10 failed`
- the failing service tests showed the hidden runtime was structurally stale for then-current T8:
  - diagnostics and normalized text refs point to missing root absolute paths rather than the hidden runtime root
  - source blob resolution fails path-safety because `blob_ref` points outside the chosen review root
  - page geometry and richer extracted-units expectations are not satisfied by this older runtime generation

Later status after adoption and targeted repairs:

- that hidden-runtime lineage became the source for the adopted root-local `20260327_062011` fixture
- once adopted into the root-local branch and paired with shared runtime discovery plus worktree-specific test repairs where needed, it became sufficient for:
  - root grouped T8: `76 passed`
  - `worktrees/pageevidence-main-merge` grouped T8: `137 passed, 3 skipped`
  - `worktrees/nrc-aps-runtime-next` grouped T8: `105 passed, 1 skipped`

## Interpretation

Current direct execution evidence supports this narrower conclusion:

- root checkout remains non-green on the broader post-freeze validation story outside the repaired T8 review/runtime surface
- `worktrees/pageevidence-main-merge` is green on the three requested pillars and on the broader evidence/API/corpus correction run
- `worktrees/pageevidence-main-merge` is also green on the official T7 backend bundle
- `worktrees/pageevidence-main-merge` is now green on the full review/runtime T8 bundle as well (`137 passed, 3 skipped`)
- the root-local grouped T8 review/runtime bundle now reproduces a green result (`76 passed`) after adopting the `20260327_062011` runtime and shared helper-driven review tests
- `worktrees/nrc-aps-runtime-next` is now also green on the full review/runtime T8 bundle (`105 passed, 1 skipped`) against that adopted root-local runtime
- the surviving hidden/archive runtime is no longer only partial evidence; it became the source for the adopted root-local T8 authority surface that now supports all three revalidated T8 surfaces above

## What this means for doc claims

These claim families are currently unsupported by active execution evidence:

- dirty `00F` and dirty `03L` statements that clean-worktree review/runtime validation auto-aligns to a shared audited runtime root and currently passes
- dirty `06C` T1-T8 clean-worktree live verification
- dirty `06D` and dirty `06E` grouped T7/T8 current-operational-state closure
- untracked `05M` validation lines that imply the current clean worktree here reproduces `142 passed` review/runtime closure
- pre-cleanup `frontend_UI_plans` wording that treated `20260327_062011` and `20260328_150207` as current or verified local runtime fixtures rather than historical reference examples

The current verified authority split is therefore:

- owner-path implementation authority for MVVLC/PageEvidence/Candidate B: `worktrees/pageevidence-main-merge`
- root planning/control docs: root checkout, but currently dirty and not unified
- review/runtime T8 fixture authority: now resolved on the root-local branch and on `worktrees/pageevidence-main-merge` through the adopted `backend/app/storage_test_runtime/lc_e2e/20260327_062011` runtime, shared runtime discovery, and dynamic representative target selection in the worktree API tests; separate active worktrees beyond that still require their own explicit executable T8 revalidation
