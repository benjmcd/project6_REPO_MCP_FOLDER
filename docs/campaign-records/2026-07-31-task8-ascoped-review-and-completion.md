# Task-8 A-scoped — completion record + comprehensive review verdict (2026-07-31)

Durable record of the ~30h/63-commit A-scoped Task-8 build (base 6aa98eca .. HEAD 4b01d796 on
codex/dual-live-plan) and its comprehensive review (6 Sonnet scouts -> 4 Opus verifiers -> 1 Opus
synthesis -> 1 Fable adjudication, 12 agents). Closes the record-durability gap (prior completion was
chat-only per a-scoped-plan:1147). Evidence labels: REPO-CONFIRMED / REPRODUCED / LOG-ASSERTED / INFERENCE.

## REVIEW VERDICT: ACCEPT-WITH-CONDITIONS
The BUILD is mechanism-sound and A-scope-compliant; the one MAJOR defect is EVIDENTIARY/record-honesty
(a census claim that does not reproduce on this Windows host), not correctness/security/scope. Fails SAFE.

## What is confirmed GENUINE (4 of 5 clean-ACCEPT criteria, unanimous across lanes)
- [REPO-CONFIRMED] A-SCOPE COMPLIANCE — the key review question, resolved in the build's favor. Frozen M0
  plan byte-untouched (git hash-object = 68f740af, matches gate pin; empty diff 6aa98eca..HEAD). B1a seal
  b8a89df2 intact. Gate _REQUIRED_ENVIRONMENT = exactly the 6 pre-existing vars (tools/dual_live_gate.py:
  341-354) — NO new env inputs. config.py delta = 2-line sys.flags.isolated guard, zero new Settings
  fields. Forbidden production files (dual_live_postrun_evidence.py, tools/dual_live_issue.py) ABSENT; zero
  "attestation" hits in live dual_live services — the REJECTED attestation-index was NOT reintroduced.
  Coordinated-rewrite handling limited to the 3 frozen-enumerated cases (2360-2362) via R02/R03/R04
  domain-scoped parity; nonclaims honor the frozen 668-671 disclaimer.
- [REPO-CONFIRMED] No CRITICAL/MAJOR fail-closed or false-PASS defect. Evaluator mechanically read-only
  (own mode=ro engine, INDETERMINATE>FAIL>PASS, exceptions->INDETERMINATE); gate sole PASS path guarded by
  G01/G02-first + double-evaluation byte-identity + chain/capture/DB-custody stability. No lane found a
  false-PASS path. The weaker evidence.py verifier is bracketed by the stronger capture.py verifier
  (gate.py:1551,1598) — no false-PASS gap.
- [REPRODUCED] Gate authority: 356/356 reproduced FOUR times independently.
- [REPO-CONFIRMED] Frozen docs + B1a seal untouched; no push (git ls-remote empty for the branch).
- [REPRODUCED] Nonclaims accurate, incl. host dependency-ineligibility for a real run (py3.12 mismatch;
  DualLiveDependencyError). The live/G2 path is UNEXERCISED on this machine — correctly fail-closed.

## The MAJOR defect (evidentiary; gates certification of "offline bar PASS", not the build)
- [REPRODUCED] "full test census green (evaluator 401)" does NOT reproduce on a standard Windows host:
  three lanes independently got 322-393 passed with flaky failures/errors, ALL funneling through a single
  PRE-EXISTING, OFF-DIFF over-strict file-metadata TOCTOU — _stable_managed_file
  (layer3_execution_output.py:251-270; _file_fingerprint at :209-217 includes st_mtime_ns/st_ctime_ns),
  tripped by Windows metadata churn (AV/indexer/OneDrive), ~11%/file flakiness. VERIFIED off-diff:
  git diff --numstat 6aa98eca..HEAD is EMPTY for that file. It fails SAFE (blocks, never false-PASS) and
  rides on code unchanged since base — NOT a Task-8 regression. But the headline claim is over-stated, the
  Windows fragility was undisclosed, and no green-census transcript is committed. Evidentiary MAJOR.
- [CORRECTED CLAIM POSTURE, per review condition 2] Until a green census is reproduced on an eligible host:
  cite "evaluator 401 COLLECTED; pass-count host-dependent on Windows due to a pre-existing off-diff
  file-metadata race" — NEVER "evaluator 401 green". Gate 356/356 = REPRODUCED and citable.

## Minors / caveats
- [MINOR pre-existing, off-diff] Layer3WorkbenchError @dataclass(frozen=True) subclassing ValueError
  (layer3_workbench_error.py:9-10) raises FrozenInstanceError in contextlib __exit__, masking the real
  "payload not authoritative" root cause on the acceptance error path. Surfaced, not caused.
- [LOG-ASSERTED] V7 broad (3649 passed/13 skip), V1 (264), V2 (156), 3 tamper campaigns fail-closed — NOT
  reproduced by any lane. The 3 tamper tests (test_dual_eval_acceptance.py:4298-4407) assert exactly the 3
  enumerated rewrite cases statically but die in fixture setup on this host (same TOCTOU) — tamper
  detection verified by CODE READING only, executed evidence deferred.
- [INFERENCE] Mild over-engineering signal (ceiling-removal lens): the ~13,485-line dual_live_runtime.py +
  dual_live_windows.py pair + duplicated verifier/chain-loader functions were not adjudicated for
  load-bearingness. NOT frozen over-scope, NOT exploitable; a proportionality/consolidation pass is
  recommended before the surface grows — NOT a condition of acceptance.
- The 5 disclosed P2 items were chat-only; recorded here for durability: (1) Phase-B services commit
  independently -> a mid-chain failure can retain partial durable state (evaluator/gate still fail closed,
  no false PASS); (2) non-frozen impl plan/file-map needs reconciliation with the final surface; (3)
  dual_live_windows.py has 15 Windows-ctypes mypy diagnostics (rest of the owned slice type-clean); (4)
  6-package lock verified but full transitive import closure + CVE freshness not independently attested;
  (5) docs say py3.11 but the launcher/verifier requires py3.12.
- R07_EXIT_LOGGER_CENSUS is an authorized supplement beyond the literal frozen startup-only census
  (adjudication Ruling 1) — recorded so it is not misread as scope creep.

## CONDITIONS (binding, from the review)
1. Produce ONE reproducible green offline census of test_dual_eval.py (401/401, exit 0) on a
   dependency-eligible py3.12, file-interference-quiet host, transcript committed here — OR fix the
   pre-existing _stable_managed_file TOCTOU (content-hash instead of mtime/ctime fingerprint, or bounded
   jitter tolerance) and show green on an ordinary Windows host.
2. Claim restatement (done above) until condition 1 is satisfied.
3. This committed record satisfies the labeled-completion-report requirement.
4. G2 live-acquisition stays BLOCKED until conditions 1-3 + the 3 tamper tests execute green on an
   eligible host.

## NEXT STEP (review recommendation)
Proceed to the grouped architecture/security review now (nothing blocks it — fail-closed posture sound,
A-scope confirmed), in parallel with satisfying conditions 1+ (TOCTOU fix or clean-host census). Do NOT
certify "offline bar PASS" or advance to G2 until conditions 1-4 are met.
