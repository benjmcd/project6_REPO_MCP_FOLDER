# 03I Runtime Root and Run Namespace Policy

## Verified live evidence

### Runtime-root normalization
`review_nrc_aps_runtime.py`:
- `get_allowlisted_roots()` deterministically includes:
  - `backend/app/storage_test_runtime/lc_e2e`
  - `backend/storage_test_runtime/lc_e2e`
- appends `settings.storage_dir / "lc_e2e"` only when `settings.storage_dir` ends in `storage`
- `discover_review_roots()` scans those allowlisted bases for summary-backed directories
- `find_review_root_for_run(run_id)` resolves run IDs by loading those summary-backed roots

### Tests and caller evidence
- `backend/tests/test_review_nrc_aps_catalog.py` verifies summary-backed candidate run discovery and stable default selection.
- `backend/tests/test_review_nrc_aps_details.py`, `backend/tests/test_review_nrc_aps_tree.py`, `backend/tests/test_review_nrc_aps_graph.py`, and `backend/tests/test_review_nrc_aps_document_trace_service.py` all rely on `find_review_root_for_run(...)` returning a valid audited review root.

## Operational decision

### Baseline integrated path
Baseline runtime continues to use the existing default/discovered `lc_e2e` roots.

### Experimental path
Experimental variants remain out-of-band initially.

## Preferred coexistence mechanism

Experimental runs should use explicit runtime/artifact roots that are **not** named `storage` or `storage_test_runtime`, and should not be fed into the default review/runtime discovery path in the first integrated pass.

## Important restraint

A second-opinion critique suggested a more explicit experiment-context abstraction.
This pack does **not** adopt that implementation construct as frozen truth yet.
It only freezes the required isolation behavior.

## Forbidden in current scope

- changing default baseline review/runtime root behavior
- making experiments auto-discoverable through baseline `lc_e2e`
- sharing the same discovered runtime namespace between baseline and experiments


## Additional limitation from attached-session evidence

Separate runtime roots reduce collision risk, but they do **not** by themselves prove full out-of-band isolation if:
- discovery is additive,
- review/catalog layers aggregate across roots,
- shared run visibility remains exposed elsewhere.

So separate runtime roots are necessary for collision control, but may still be insufficient for full baseline invisibility.
