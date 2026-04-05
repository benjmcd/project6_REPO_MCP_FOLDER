# 03I Runtime Root and Run Namespace Policy

## Verified live evidence

### Runtime-root normalization
`review_nrc_aps_runtime_roots.py`:
- appends `lc_e2e` when given a root named `storage` or `storage_test_runtime`
- uses deterministic candidate roots including:
  - `backend/app/storage_test_runtime/lc_e2e`
  - `backend/storage_test_runtime/lc_e2e`

### Runtime-root caller
`review_nrc_aps_runtime.get_allowlisted_roots()` calls `candidate_review_runtime_roots(...)` with `settings.storage_dir`.

### Tests
`backend/tests/test_review_nrc_aps_api.py` verifies:
- deterministic candidate review/runtime roots
- configured `storage_test_runtime` roots normalize to `.../lc_e2e`

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
