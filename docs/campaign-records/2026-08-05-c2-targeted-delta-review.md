# C2 targeted delta review — owned-child workload preload (2026-08-05)

> Review record produced under condition **C2** of the grouped G1→G2 gate verdict
> (`2026-08-02-g1-grouped-gate-verdict.md:30-32`): the verdict binds `cf57de58` + frozen plan
> `68f740af` + B1a seal `b8a89df2`, and any substrate change triggers a **targeted** delta review of
> the seam — targeted, **not** a full rerun. Conducted by an independent reviewer that did not author
> the change, in the precedent shape of the `590a04c2` pass.

## Verdict: **C2-DELTA-SOUND**

No critical or major findings. Three MINOR/NIT items, none blocking.

## Delta reviewed

`e53955d2` vs parent `39c611cc` (single-parent fast-forward, now the branch tip): 3 files,
**173 insertions / 1 deletion** — `dual_live_runtime.py` (+28, the preload function),
`tools/dual_live_run.py` (+4/−1, Protocol declaration + the call site), and a new **non-certified**
regression check under `tests/`.

## D6 classification, stated explicitly

The owner ruled **D6 = (a)**: this defect fix is read as **inside the G2-prereq carve-out** of the C2
clause. The operative consequence is identical under either reading — a targeted delta review — but
the reading is stated rather than left to inference. Corpus precedent (G2-P3 landing while P1/P2 were
open) supports the carve-out reading.

## Findings

**Security posture: preserved, and in one respect strengthened.** `_StandardLibraryGuards` is
constructed and installed well before the preload, so every preloaded import executes under the
already-active stdlib/network denial. The six preloaded service modules perform **zero `os.environ`
reads**, so nothing at import time touches credentials; `create_engine` connects lazily and only to
the local database. Phase-B connector denial is unaffected because the guard installer wraps
*attributes* on resident modules — import origin is immaterial. Hoisting `guards.assert_intact()` out
of the phase-B branch gives **Phase A** an integrity assertion it previously lacked at that point,
re-checking the enlarged import surface against guard tampering.

**The pre-freeze mutable window (the sharpest question): not a material weakening.** More third-party
code now runs while logging is still mutable (loggers at freeze rise from 8 to 46 in the replay
harness). The posture's enforcement, however, never rested on pre-freeze code *volume*; it is a
three-stage pipeline, unchanged by this delta and designed to be applied to whatever exists at freeze
time: (1) normalization clears handlers/filters, attaches a bare `NullHandler`, sets
`propagate=False`, and drops `lastResort`; (2) census projection **fails closed**
(`dual_live_logger_handler_invalid`) on anything other than a bare `NullHandler` or the single
correctly-bound `CampaignPipeHandler`; (3) the freeze denies all subsequent mutation and the
**exit-equals-initial invariant holds by construction** — the delta changes what `initial` contains,
not the invariant. Nothing an import can attach survives invisibly. The steelman for "minimum
pre-freeze code" collapses against the measurement: keeping the imports post-freeze is not a stricter
posture, it is a proof that the real workload can never run.

**Evidence integrity: no landed expectation breaks.** The Phase-A `pre_activity` census will report a
larger `handler_count` and a different `topology_sha256`. An exhaustive check of every consumer of
that field found the evaluator validates **shape only** and compares **intra-run only**; no cross-run
or expected-constant comparison exists anywhere. A reviewer diffing a pre-fix evidence bundle against
a future one will see the jump — it is the intended consequence of this fix and must be read as such.

**Unchanged invariants, verified from git objects at the landed commit:** frozen plan blob
`68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`; B1a seal `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`;
`dual_live_dependencies.py` diff **0 lines** (dependency digest inputs untouched); timeout contract
unchanged; the three carried C4 residuals neither worsened nor silently altered.

## Gate allowlist — explicit statement

**No widening occurred and none was needed.** The delta does not touch `tests/test_dual_gate.py` at
all. Both edited production files were already allowlisted since Task-8 and flow into
`ALLOWED_CHANGED_PRODUCTION_PATHS`; the new `tests/` file is invisible to the production-path
predicate (which covers `project6.ps1`, `backend/app/`, `tools/` only). The standing caution that
"every future delta review must diff the allowlist" is **discharged for this delta by direct diff**.

## New-surface risk

Negligible, and correctly outside the certified count. The regression file spawns offline
`sys.executable -B -c` children against a temporary sqlite database, and **strips** the credential and
egress variables from each child's environment copy — an affirmative safety measure, not a risk. Its
positive control is load-bearing: without it a future preload gap would pass silently.

## Residuals carried forward

The C4 trio (Phase-B non-atomic durability; hostile-native-PDF in-process parse under Python-only
spawn denial; shared-executor HTTP credential seam) — pre-existing and unchanged. Plus the two named
enumeration-drift instances and the preload-maintenance burden recorded in the defect record. One
pre-existing hardening candidate, independent of this fix: `logging.disable` / `Manager.disable` is
neither frozen nor censused (bounded here — the pinned dependency stack contains no such call).

## What this review does NOT certify

Not a live-run authorization — **G2-P8 remains a separate explicit owner act**, credential
provisioning remains owner out-of-band, and C3 PREP-ONLY scope is unchanged. Not a full G1 rerun
(targeted by design). The real workload has **still never executed end to end**; this fix removes a
proven structural blocker, it does not prove live success. The C4 residuals are carried, not closed.
