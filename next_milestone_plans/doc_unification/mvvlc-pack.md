# MVVLC Pack

## Most important inconsistencies found during audit

Status note:

- the specific source-doc overclaim lines described below were the findings that triggered the cleanup pass
- the primary MVVLC front-door/control docs and verifier mirrors have since been re-scoped to present this tree as a root-local planning branch with imported merged-main references
- remaining live concerns are the dirty-tree breadth, untracked pack expansion, derivative-doc propagation risk, and active-worktree parity beyond the now-resolved root-local and `worktrees/pageevidence-main-merge` T8 fixture-authority surfaces

### `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`

Pre-cleanup dirty file issues identified in this audit:

- lines 54-72 claim the focused workspace root now contains `review_nrc_aps_runtime_roots.py`, `review_nrc_aps_runtime_db.py`, `backend/tests/test_review_nrc_aps_runtime_db.py`, and `backend/tests/review_nrc_aps_runtime_fixture.py`-style validation behavior
- lines 82-93 describe binding-based discoverability and `runtime_db_session_for_run(run_id)`-gated run-bound endpoints as root-live behavior
- lines 193-201 describe M6B direct admission as if the root owner/test files carry it now
- lines 69-72 specifically claim clean-worktree auto-alignment to a shared audited runtime root and a passing grouped T8 bundle without seeding new runtime data

Counter-evidence in the actual root checkout:

- `backend/app/services/review_nrc_aps_runtime.py:15-110`
  no `ReviewRuntimeBinding`
  no `discover_runtime_bindings()`
  no `request_config_is_baseline_visible(...)`
- `backend/app/services/review_nrc_aps_catalog.py:49-114`
  summary-backed roots plus `ConnectorRun` merge, not binding-based filtered discovery
- `backend/app/api/review_nrc_aps.py:23-36`
  imports `find_review_root_for_run`, not `runtime_db_session_for_run`
- root searches for `candidate_a_page_evidence_v1`, `_normalize_visual_lane_mode`, `_run_candidate_a_visual_lane`, and `request_config_is_baseline_visible` in the root owner/test set returned no matches

The live code matching those claims exists in merged main only:

- `worktrees/pageevidence-main-merge/backend/app/services/review_nrc_aps_runtime.py:22-40,221-261`
- `worktrees/pageevidence-main-merge/backend/app/services/review_nrc_aps_catalog.py:87-138`
- `worktrees/pageevidence-main-merge/backend/app/api/review_nrc_aps.py:21-24,126-249`
- `worktrees/pageevidence-main-merge/backend/app/services/connectors_nrc_adams.py:76`
- `worktrees/pageevidence-main-merge/backend/app/services/nrc_aps_document_processing.py:88,198,801-806`

Additional correction from this pass:

- the old clean-worktree review/runtime auto-alignment claim was false when first audited, but the root-local branch now materially carries an adopted audited runtime plus `backend/tests/review_nrc_aps_runtime_fixture.py`, and the grouped root T8 bundle now passes there

### `03L_RUNTIME_DB_BINDING_AND_ISOLATION_POLICY.md`

Pre-cleanup dirty lines 9-40 narrated:

- `review_nrc_aps_runtime_roots.py`
- `review_nrc_aps_runtime_db.py`
- `backend/tests/test_review_nrc_aps_runtime_db.py`
- `backend/tests/review_nrc_aps_runtime_fixture.py`
- grouped T8 clean-worktree passing

Those were not true for the root checkout when first audited.
They became partly true only in later root-local/workspace-local validation: root gained `backend/tests/review_nrc_aps_runtime_fixture.py`, a workspace-local copy of `backend/app/storage_test_runtime/lc_e2e/20260327_062011` was adopted on the root-local branch, and the grouped T8 review bundle reran green there. The committed `main` tree preserved by this pack contains the helper/test repairs but not that runtime directory.

### `06C_ACTIVE_TEST_SURFACE_AND_COMMAND_MATRIX.md`

Pre-cleanup dirty issues identified in this audit:

- line 7 claims T1-T8 are live-verified in this clean worktree
- lines 145-146 claim grouped T7 no longer suffers `numpy` poisoning and that T8 clean-worktree execution is aligned through `review_nrc_aps_runtime_fixture.py`

Pre-fix execution evidence disproved those claims for root:

- grouped T7 still fails because `backend/tests/test_nrc_aps_advanced_adapters.py:14` poisons grouped imports via fake `numpy`
- grouped T8 then failed because `backend/tests/test_review_nrc_aps_document_trace_api.py:34-37` required a missing audited runtime DB

Current corrected status for root:

- later root-local reruns produced a green grouped root T8 result (`76 passed`) after adopting `backend/app/storage_test_runtime/lc_e2e/20260327_062011` in workspace-local branch state, adding `backend/tests/review_nrc_aps_runtime_fixture.py`, and switching the stale hardcoded review tests to shared runtime discovery

Current corrected status for the active merged-main worktree:

- `worktrees/pageevidence-main-merge` later validated successfully against that adopted workspace-local `20260327_062011` runtime through its shared runtime helper
- `worktrees/pageevidence-main-merge/backend/tests/test_review_nrc_aps_document_trace_api.py` no longer hard-codes vanished representative run ids; it now derives representative positive/mixed/negative/large targets dynamically from the current available runtime and conditionally skips cross-runtime comparison if no second qualifying runtime exists
- the full worktree review/runtime T8 bundle now passes there: `137 passed, 3 skipped`

### `06D_CRITICAL_BLOCKER_VALIDATION_SET.md`

Pre-cleanup dirty issues identified in this audit:

- B2 says the live file passes under the canonical grouped T7 bundle
- B6 says review/runtime validation aligns through `backend/tests/review_nrc_aps_runtime_fixture.py`
- B6 says grouped T8 passes without seeding new runtime data

Those statements were not true in the current root checkout when first audited.
The root-local T8 part is now repaired, but the broader grouped T7/T8 closure posture still remains too strong to apply generically across separate worktrees.

### `06E_BLOCKER_DECISION_TABLE.md`

Pre-cleanup dirty issues identified in this audit:

- the status legend removes `PLANNING-CLOSED` and `IMPLEMENTATION REQUIRED`
- many rows become `TRUE CLOSURE`
- rows for artifact equivalence, run-scoped review/runtime access, runtime-root coexistence, review/catalog/report/API visibility, diagnostics persistence, and broader T5/T6 acceptance are now treated as fully closed

That closure posture was not supported by root execution evidence when first audited.
That later root-local grouped T8 rerun was green, but it still does not automatically upgrade broader grouped T7/T8 closure across separate worktrees or all other validation layers.

### `README_INDEX.md`

Pre-cleanup dirty issues identified in this audit:

- lines 7-55 front the pack with merged-main closure language for M3, M4, M5, M6A, M6B, `05P`, and `05Q`
- lines 70-86 and later sections treat `03AA` through `05Q` as active pack reading order

Those files currently exist only as untracked local files in the root checkout.

Implication:

- the README is fronting a pack that is larger than the committed root branch state
- readers cannot infer from the README alone which parts are committed branch truth and which parts are only local working-tree additions

### `00T_STRICT_ADEQUACY_AUDIT_AND_PROCEED_DECISION.md`

Pre-cleanup dirty issues identified in this audit:

- lines 23-28 and 97-98 treat untracked `05M`, `05N`, `05Q`, and the `TRUE CLOSURE` rows in dirty `06E` as settled current pack authority
- lines 89 and 106-108 use that closure posture to justify proceeding

Why this matters:

- `00T` is derivative, but it now inherits the same overclaim chain as `00F` and `06E`
- because `06E` currently overstates grouped T7/T8 closure and `05M` is untracked, `00T` is stronger than the current active evidence supports

### `00V_PLANNING_TRACEABILITY_AND_DEPENDENCY_MATRIX.md`

Pre-cleanup dirty issues identified in this audit:

- lines 29-31 and 63-73 front untracked `03AA` through `05Q` as part of the active control spine and execution layer
- lines 219-230 then summarize the current milestone position using those same untracked files as if they were already established pack authority

Why this matters:

- `00V` is a reasoning map, but it currently maps readers into an untracked expanded pack without clearly separating committed root state, dirty local additions, and merged-main authority

### `03J_ARTIFACT_EQUIVALENCE_CONTROL_POLICY.md`

Pre-cleanup dirty issue identified in this audit:

- lines 17-19 say grouped canonical acceptance behavior for the artifact surface is operational and tracked in `06C`, `06D`, and `06E`

Why this matters:

- the artifact test file itself is real and the grouped T7 bundle does pass in `worktrees/pageevidence-main-merge`
- but `03J` currently delegates current-operational proof to the same dirty `06C` / `06D` / `06E` surfaces that overclaim broader closure, so it should not be read as independent proof of pack-wide acceptance

### `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`

Current untracked issue identified in this audit:

- lines 88-151 record clean-worktree validation including `142 passed` for the required M5 no-drift backend bundle and `111 passed` for the root-side report/export/context bundle

Why this matters:

- `05M` is not tracked in the root git index
- its clean-worktree validation record is still not fully reproducible as written on current active checked-out authority surfaces here, even though `worktrees/pageevidence-main-merge` now reproduces a green T8 bundle against the adopted root-local runtime. The exact historical counts and corpus shape recorded in `05M` should still be treated as imported historical validation rather than current literal replay.

### `00A_MASTER_NAVIGATION_AND_REVIEW_MAP.md`, `00B_REVIEW_AUDIT_ASSESSMENT_PLAYBOOK.md`, and `00C_IMPLEMENTATION_PREPARATION_AND_EXECUTION_PLAYBOOK.md`

Pre-cleanup dirty issue identified in this audit:

- `00A` repeatedly routes readers into `03AA`, `03AB`, `03AC`, `05M`, `05N`, `05P`, `05Q`, and `06E` as active foundational, control, and validation inputs
- `00B` makes `README_INDEX`, `00T`, `06E`, `05M`, `05N`, `03AC`, `05P`, and `05Q` mandatory or near-mandatory audit inputs for full-pack review
- `00C` operationalizes the same chain for implementation preparation, presenting `05M`, `05N`, `03AC`, `05P`, and `05Q` as achieved/current implementation-state context

Why this matters:

- these three files are operational playbooks rather than primary fact surfaces
- but they direct reviewers and implementers into the same expanded closure stack that is partly untracked in root and partly not reproducible in the current checked-out root/worktree state
- that makes them derivative amplifiers of the authority-drift problem, not neutral navigation aids

### `VERIFIER_FRONT_DOOR.txt` and `VERIFIER_TEMP_DUMP.txt`

Pre-cleanup dirty issue identified in this audit:

- both mirror files repeat the same merged-main closure chain around `05M`, `05N`, `05P`, and `05Q`
- both assert that T1-T8 were executed for the merged baseline path and that the review/runtime T8 surface is green under the canonical grouped bundle
- `VERIFIER_TEMP_DUMP.txt` also embeds the stronger clean-worktree review/runtime auto-alignment claims for the audited `lc_e2e` corpus and then repeats the `TRUE CLOSURE` table that marks artifact equivalence, run-scoped review/runtime access, visibility, diagnostics persistence, T5/T6 acceptance, and performance as fully closed

Why this matters:

- these files are mirrors or derived verifier artifacts, not independent corroboration
- they currently duplicate the same unsupported closure language, so they should be read as overclaim propagation, not as separate evidence
- because they are easy to mistake for corroborating summaries, they increase the risk of readers treating the dirty closure chain as multiply verified when it is actually circular

## Internal pack non-unification

### `03I` vs current dirty `00F`

`03I` still carries the older root-discovery model:

- append `settings.storage_dir / "lc_e2e"` only when `settings.storage_dir` ends in `storage`

Current dirty `00F` carries the newer normalized binding/filter model:

- normalized `/storage/lc_e2e` or `/storage_test_runtime/lc_e2e`
- `discover_runtime_bindings()`
- `ConnectorRun.request_config_json["visual_lane_mode"]` visibility filtering

These are different architectural models.

### `06C` vs `06D` / `06E`

`06C` still defines a T8 grouped bundle that omits `backend/tests/test_review_nrc_aps_runtime_db.py`.
Current dirty `06D` and `06E` treat that file as core review/runtime closure evidence.

The pack still does not hold a single unified definition of T8.

## Assessment

The MVVLC pack currently has three simultaneous states layered on top of each other:

1. committed root branch state at `551b8ecd`
2. dirty local root edits that overclaim merged-main materialization
3. actual merged-main worktree owner-path implementation authority
4. a formerly missing review/runtime fixture authority story, later repaired in workspace-local validation on the root-local branch and on `worktrees/pageevidence-main-merge` via the adopted `20260327_062011` runtime, shared helper-driven review tests, and dynamic representative target selection in the worktree API tests, while other active-worktree executable parity remains a separate question and the committed `main` tree still omits the adopted runtime directory itself

Those states are not clearly separated in the current root docs.
