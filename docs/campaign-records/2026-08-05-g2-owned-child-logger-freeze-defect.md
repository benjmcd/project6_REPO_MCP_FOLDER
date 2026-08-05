# G2 owned-child logger-topology-freeze defect — root-cause and fix record (2026-08-05)

> Defect record. The defect was found by attempting the G2 live run; it is fixed at commit
> `e53955d29c9ff3efcf17316d499f1aa6a64b58ae`. This record does not authorize anything: G2-P8
> remains a separate owner act and the real workload has still never executed end to end.
> Redaction posture: operator-identifying absolute paths given as neutral placeholders.

## 1. Symptom

The G2 live run refused with the opaque `dual_live_run_refused` (exit 2), with no further output.
The refusal reproduced **key-free and pre-arming**, so it was never credential-related.

## 2. Root cause

The owned child freezes its logger topology (`tools/dual_live_run.py`, `_configure_logger_topology`)
**before** dispatching the phase workloads. `run_owned_phase_a_workload` then lazily imports
`app.db.session` (`backend/app/services/dual_live_runtime.py:5373` at the pre-fix revision).
SQLAlchemy creates loggers **at import** (`sqlalchemy/log.py:53`) **and per Engine/Pool instance**
(`:248`), and `backend/app/db/session.py:18` builds the engine at module scope. The first workload
import therefore raised `dual_live_logger_topology_frozen`, which the child's `_refuse` flattened to
the generic string (only codes in `_PUBLIC_REFUSAL_CODES` are surfaced), and the parent's pump
independently latched `pump_failure` on the unframed child stderr.

The child already preloaded `requests` before the freeze for exactly this class of problem; the
DB/connector surface was simply missed.

## 3. Why no gate caught it

The real-workload path requires all four `DUAL_LIVE_CAMPAIGN_ID` / `_FINGERPRINT` / `_CODE_REVISION` /
`_DEPENDENCY_SET_SHA256` variables (`tools/dual_live_run.py:760-766`), which only a real campaign
sets. Both the 356-test gate and the 404-test evaluator census exercise the **mechanical** child
(`real_workload=False`). **The real Phase-A workload had never executed.** This is stronger, and more
uncomfortable, than the previously accepted residual "the first credentialed run is its first real
exercise", and is recorded here as a correction to that framing rather than an instance of it.

## 4. Fix

`_preload_owned_workload_modules()` (new, `dual_live_runtime.py`) materializes the workload module set
— `app.db.session`, `app.models.models`, `app.schemas.api`, and the five connector/egress services —
and is called from `tools/dual_live_run.py` **after** the boot-frame write and **before** the freeze,
**ungated for both phases**, with `guards.assert_intact()` hoisted to cover both.

Rejected alternatives, recorded so they are not re-proposed: placing the preload earlier (inside the
hard 5.0 s owned-boot window — would trade this defect for `dual_live_owned_boot_timeout`);
pre-creating logger *names* without importing (Engine/Pool instance loggers only exist once the
objects are constructed); relaxing the freeze to permit post-freeze logger creation (breaks the
exit-equals-initial census invariant — a proof-surface amendment, never a continuation of this fix).

## 5. Evidence

Measured at the landed revision with the curated interpreter (python 3.12.10, image sha256
`4d6f5f81…`):

| Check | Result |
|---|---|
| Gate `tests/test_dual_gate.py` | **356 passed** |
| Evaluator census `backend/tests/test_dual_eval.py` | **404 passed** |
| Regression check (new, non-certified) | **3 passed** |
| Replay CONTROL (no preload) | **12 denials**, incl. instance-level `SessionLocal()+execute` |
| Replay FIXED (preload) | **0 denials over 15 steps** |

The 404 census **includes** the three named P2 tamper campaigns: `test_dual_eval_acceptance.py` sets
`__test__ = False` (so pytest does not collect it directly — direct node-id invocation returns "no
tests ran") and is driven by `test_dual_eval.py`, which re-exports the three campaigns. The P2 record's
quoted stand-alone command shape no longer reflects collection semantics.

Full disclosure: the **first** post-fix gate run failed
`test_frozen_and_sealed_authority_files_are_unchanged` (355 passed / 1 failed). The cause was a
prototyping-environment artifact — a clone configured with `core.autocrlf=false`, which makes
`git hash-object` skip the CRLF→LF clean filter so the working-tree frozen plan hashed `1d8a2482…`
instead of `68f740af…`. It was not the patch (that file is untouched by it). With the setting
corrected the gate is green.

## 6. Primary exhibits

The refused-run artifacts are preserved untouched at the retired evidence root under
`evidence/logs/<retired-campaign-fingerprint>/`: `app.jsonl` records `runtime_start` →
`phase_child_start` → `logger_census` → `phase_go` → `stop_latched(reason_code="pump_failure")` →
clean teardown; `http.jsonl` is **0 bytes** and the socket census is all-zero, which is the positive
evidence that **no network egress occurred**.

## 7. Named residuals (enumeration drift)

Per C4 doctrine these are named, never silent. Both are post-freeze `getLogger` sites that this fix
does **not** preload:

1. `backend/app/services/layer3_pass_entry.py:79` and `:85` — deferred `app.services.analysis`
   (matplotlib/PIL, ~29 loggers). Phase-B reachable only through the non-nominal quantitative arm.
   Owner ruled **name-it, do not preload** (D1=a): preloading would drag native font/image codecs into
   the credentialed child for a path this campaign profile should not take. The new regression check
   carries a tripwire asserting the module stays absent.
2. `backend/app/services/nrc_aps_advanced_ocr.py:25-26` — runtime `logging.getLogger("paddleocr")` /
   `("ppocr")` inside `_get_paddle_instance()`, currently fenced by the strict-parse refusal.

**Maintenance burden, stated plainly:** five of the fourteen post-freeze modules are covered only
*transitively* by the preload. A future post-freeze import added to a workload would manifest as a
**live-run refusal, not a test failure**, unless the regression check's replay list is maintained in
step.

## 8. Non-claims

Does not authorize the live run (G2-P8 separate). Does not close G2-P3/P5. Does not modify the frozen
plan blob `68f740af…` or the B1a seal `b8a89df2…`. Does not change the dependency digest (computed
from installed distributions + lock, not repo source). The new regression file is deliberately outside
the certified 356 count and must not be cited as part of any counted bar.
