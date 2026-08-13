# G2-P2 offline evaluator bar — evidence record (2026-08-03)

> Evidence record. Measured 2026-08-03 BEFORE any credential existed; measurement independently
> reproduced by an adversarial verification pass (full census re-run: 404 passed, exit 0). Landed
> under owner authorization 2026-08-03. Redaction posture: operator-identifying absolute paths /
> hostname given as neutral placeholders (omission only, never false).

## Gate / acceptance bar (D13-restated)
G2-P2 offline bar: the FULL `backend/tests/test_dual_eval.py` evaluator census green, plus the
three named tamper campaigns green, on the eligible py3.12 host — with the census count
**re-derived at run time** (not hardcoded), before any credential exists. The restated bar is at
`2026-08-02-g1-grouped-gate-verdict.md` (G2-P2 census-reconciliation amendment).

## Dependence on P1 (formal standing)
G2-P2 remains **formally OPEN pending owner acceptance of the P1 eligibility record**
(`2026-08-03-g2-p1-host-eligibility.md`): the census counts as "on the eligible host" only once
that host's eligibility is accepted. This record discharges the **MEASUREMENT** of the offline
bar; it is not a standalone P2 closure.

## Test environment (discovered, not built)
An existing runnable backend test environment was discovered on the eligible host; no
build/pip-install of backend test deps was necessary:
- CPython **3.12.10** (`py -3.12`)
- pytest **9.0.2**, fastapi **0.137.2**, sqlalchemy **2.0.48**; suite collected with zero errors.
- This general test env carries an incidental requests-stack (urllib3 2.6.3 / chardet 7.1.0 /
  charset_normalizer 3.4.4) distinct from the six-pin *eligibility* set of G2-P1; it emits one
  benign `RequestsDependencyWarning` and is orthogonal to the census. P1 (the arming-path six-pin
  gate) and P2 (the evaluator suite) are deliberately distinct env concerns; the suite's only
  `requests` reference is a string literal written into a generated fixture, and the warning
  arises transitively at collection — the evaluator never functionally exercises the requests
  stack. (Inherent residual: the evaluator has not run under the curated six-pin stack on any
  host; that conjunction is the CI/linux target.)

## Quiet checkout (file-interference-quiet)
Ran from a **non-OneDrive detached worktree** at commit **b1486887** (identical tip to the
in-place dual-live-plan worktree). Run flags across every invocation:
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPYCACHEPREFIX=NUL`, `-p no:cacheprovider`, `-p no:xdist`
(serial; no parallel workers — the bar has a known timing-sensitive flake, so xdist would measure
the wrong thing). Post-run: worktree `git status` clean, 0 stray `.pyc` in backend.

## (a) Census count re-derived at run time
`pytest tests/test_dual_eval.py --collect-only -q` → **404 tests collected** (was 401; +3
phase_b_sources structural tests, attributed to 8260c66c + 6bf4e6bf in commit 7ab61510). Derived,
not hardcoded; observed == expected == 404. Independently re-derived by the adversarial pass: 404.

## (b) Full evaluator census
`pytest tests/test_dual_eval.py -p no:cacheprovider -p no:xdist -ra --tb=short -q`
→ **404 passed, 1 warning, exit 0** (measurement run 323.53s; adversarial re-run 310.12s). All 404
green on the first serial run in both parties' executions, with zero skipped/deselected/xfailed —
verified against per-test output, not a summary paraphrase. The single warning is the benign
RequestsDependencyWarning noted above.

## (c) Three named tamper campaigns
`pytest <the three ids> -p no:cacheprovider -p no:xdist -v --tb=short` → **5 passed** (measurement
81.42s; adversarial re-run 81.61s):
- test_one_log_byte_and_rebuilt_manifest_preserve_exact_seal_taxonomy — PASSED
- test_one_log_byte_rebuilt_manifest_and_seal_exposes_database_witness — PASSED
- test_database_seal_event_rewrite_cannot_rewrite_original_files[delete|duplicate|rewrite] — PASSED
(1 + 1 + 3 parametrized = 5 collected cases, matching the bar.)

## Known flake disposition
The documented isolated-passing timing flake —
`test_seq_owned_binder_records_exact_two_phase_order_and_seals` (test_dual_eval.py:8515) and
`test_seq_owned_binder_runs_real_inert_children_and_seals_exactly_once` (:8876) — **did NOT fire**.
Both passed inside the full serial census (all 404 green) in both parties' runs, so no isolation
re-run was required. No test or source file was modified; the flake was handled by serial
execution alone. Disposition: **green as-run; flake did not manifest**.

## No-credential / no-arming attestation
No connector/NRC credential existed at measurement time; none was created, requested, or armed;
no network acquisition or connector run occurred. Pure offline bar; the suite's own
F06_NO_EGRESS_DEPENDENCY family passed.

## Verdict and standing
**G2-P2 offline bar MEASUREMENT: PASS.** Census count re-derived = 404; full census 404 passed,
exit 0; the three named tamper campaigns 5/5; known flake did not fire; serial, bytecode-off,
no-cache, no-xdist; before any credential. Formal G2-P2 standing remains OPEN pending owner
acceptance of the P1 eligibility record, and the live-run half (credential, arming) is
owner/infra-gated.
