# G2 offline-prep report — Codex 019faabd

Date: 2026-08-02. Owner-authorized offline G2 PREP subset. Base dbb87740 -> HEAD 13b75253, 13 commits,
11 files +3610/-80. COMPLETE. Frozen 68f740af + B1a seal b8a89df2 intact (self-verified); no push.
Evaluator census 404 (was 401, +3 phase_b_sources structural tests), gate 356. Independent reviews 0 findings.
- G2-P4: 22 Phase-B durable commit boundaries fault-injected in real killed children; every partial ->
  FAIL/INDETERMINATE never PASS; Phase-A invariant; no silent-refetch; operator poison->inspect->archive
  recovery tool (no repair/delete/rewrite/retry/refetch), atomic anchored publisher, symlink-refusal +
  network-denial. 27 + 21 tests pass. Discloses: interrupted poison-publish/archival leaves retained
  partial requiring operator adjudication.
- G2-P5 offline half: strict egress-execute HTTP route now CLI-only (deterministic 409 before DB/authority/
  grant/executor/claim/enqueue); written safety-net statement; provisioning-boundary check procedure (key +
  current grant only in short-lived Phase-A CLI child; Phase B secret-free). No credential created.
- G2-P9: impl-map reconciled (20 planned + 18 emergent surfaces); structural phase_b_sources fail-closed
  materialization; env-evidence-location trust boundary documented; 15 Win32 mypy errors (0 runtime, 3 stub,
  12 annotation) WAIVED (clearing touches load-bearing Win32).
STOP boundaries honored: no load-bearing Win32 change, no atomicity-model change, no credential provisioning.
Remaining G2 (owner): P1 host provision, P2 host reproduction, P3 CVE attestation, P5 live-host half, P6
residual acceptance, P8 explicit live-run authorization. P7 closed by G1; P9 nonblocking.
source-sha256: a0ad962b1deb438b93cd2605b25a107c96d8fd43d0f04cf3973cf4133cc4fdcd

---

# Codex completion reply

Codex session/conversation ID: 019faabd-31a1-7293-a3e7-d49087b95bcf
Dispatch: 1785682658-1982-4d58e047922a39e4
Outcome: COMPLETE for the owner-authorized offline G2 PREP subset.

## Authority and final state

- Worktree: C:\Users\<operator>\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\dual-live-plan
- Branch: codex/dual-live-plan
- Starting authority: dbb87740d418a34bc519a54c9befbca83a53d1ff
- Final HEAD: 13b75253ac38cdd2d532b791276d1f41044f4986
- Final tree: ae6e4734ee8e4903b6180f635ab244295407a00c
- Final implementation HEAD before the record: 7c13ee089f818cc090a258770b06af745718ec6f
- Evidence record: docs/campaign-records/2026-08-02-g2-prep.md
- Evidence-record SHA-256: 9B3B6C4B47035B5BDC324CB460E70D20CD96879FA38B2DF67B1885131870E9EE
- Worktree status after commit: only the pre-existing untracked .omc/state/sessions/ preservation state remains.
- No fetch, push, live connector request, credential provisioning, grant/campaign provisioning, or external egress was performed.

## G2-P4 — COMPLETE

MEASURED and REPO-CONFIRMED:

- Exercised the canonical Phase-B path in a real child process at all 22 durable commit boundaries:
  - NRC linkage and custody: 2
  - NRC and ScienceBase origin receipts: 2
  - NRC workbench chain: 9
  - ScienceBase workbench chain: 9
- Every child was proven alive and blocked after the exact real commit returned, then terminated externally with process.kill().
- Every persisted result was the exact contiguous durable prefix, with no later state.
- Every partial result evaluated FAIL or INDETERMINATE, never PASS.
- Phase-A transport reservation, arming, completed acquisition, target/raw artifacts, and original acquisition evidence remained invariant.
- Fault children use a minimal secret-free/default-off environment and install, exercise, and reassert the production connector/transport denial guards before Phase-B work. No silent real refetch path was observed or permitted.
- Added an operator-reachable offline poison command to tools/dual_live_recovery.py.
- Poison publication uses the repository’s existing anchored, parent-identity-bound, atomic strict-new raw-storage publisher. It checks lexical and resolved reparse components, rehashes/fyncs staged bytes, never exposes a partial final poison.json, and fails closed on source/seal/identity drift.
- Added and exercised poison -> inspect -> archive end to end on a real killed cell.
- Recovery preserves the exact raw SQLite DB/WAL/SHM/journal family and all evidence, inventories campaign-scoped and orphan Layer-3 rows in a separate analysis clone, publishes a canonical no-overwrite manifest, and never repairs, deletes, rewrites, retries, or refetches.
- Real host symlink refusal passed; network denial encloses poison, inspect, and archive.

NON-CLAIMS:

- Producer quiescence is a mandatory external operator prerequisite; the tool does not enforce or prove it.
- The kill proof brackets a durable commit; it is not power-loss injection inside native COMMIT.
- This proves safe failure and preservation/reconciliation, not all-or-nothing Phase-B atomicity or automatic availability recovery.
- Interrupted poison publication can leave a stage-only artifact; interrupted archival can leave a partial no-overwrite archive. Both are retained and require explicit operator adjudication.

## G2-P5 — OFFLINE HALF COMPLETE

- The authenticated strict egress-execute HTTP route remains registered but is permanently CLI-only.
- Every schema-valid authorized HTTP invocation deterministically returns 409 connector_strict_egress_http_execute_disabled before DB lookup, authority resolution, grant validation, executor selection, claim, clock read, or enqueue.
- Malformed bodies may still receive framework 422; authentication behavior remains intact.
- The record explicitly states that fail-closed evaluator refusal of HTTP-driven, partial, duplicate, foreign, incorrectly ordered, or incomplete runs is the intended safety net for the shared-executor seam.
- The provisioning procedure now checks the exact Settings effective configuration, including .env/singleton behavior, and requires the NRC key plus current definition/grant authority only in the short-lived Phase-A CLI acquisition child.
- Phase B receives no key/current definition/current grant authority; it retains only protected historical evidence-root/index coordinates needed for evaluation.
- No real credential was created, loaded, or tested.

## G2-P9 — COMPLETE/WAIVED

- Reconciled the non-frozen Task-8 implementation map: 20 original planned paths plus 18 emergent implementation/test surfaces, with current base/head/tree and evidence-location trust boundary.
- Added structural phase_b_sources dependency failure materialization:
  - phase_b_sources depends on origin;
  - downstream depends on origin and phase_b_sources;
  - direct missing/invalid Phase-B sources propagate fail closed;
  - R17 exposes only the gate-safe downstream domain and cannot PASS on those failures.
- Documented that environment-selected evidence locations are trusted operator configuration, not content authority; content remains bound by canonical hashes/schema/identity.
- Re-ran the exact Windows mypy census: exactly 15 errors in dual_live_windows.py.
- Independent classification: 0 runtime defects, 3 platform-stub limitations, 12 annotation issues.
- Explicitly waived as nonblocking because clearing them would touch the 13.5k-line load-bearing Win32/runtime surface. No Win32, ABI, handle, ACL, job-object, environment-block, broad-ignore, or config-suppression change was made.

## Independent review

All final reviews are CLEAN with zero critical/high/medium/low findings:

- P5 substrate delta
- P9 evaluator delta
- P4 fault harness after secret-free/default-off connector-guard closure
- P4 recovery after atomic publication, reparse/identity, seal/source-race, real-symlink, fsync-failure, drift, credential, and network challenges
- Final whole-record authority/provenance/claim audit

All prior findings were resolved before closeout. The verification ledger distinguishes final-HEAD reruns from carried-forward measurements whose relevant source/test bytes were mechanically proven identical through HEAD.

## Exact verification evidence

- Phase-B fault/recovery suite, final HEAD: 27 passed, 1 dependency warning, 161.13s
- Poisoned recovery suite, final HEAD: 21 passed, 0.77s
- Strict HTTP arming API suite, carried forward over byte-identical final route/test surface: 39 passed, 1 dependency warning, 8.24s
- Phase-A/Phase-B environment split, carried forward over byte-identical runtime/test surface: 7 passed, 169 deselected, 1 dependency warning, 0.79s
- Evaluator census, carried forward over byte-identical final evaluator/test surface: 404 passed, 1 dependency warning, 292.02s
- Gate suite at 4afb3281 with production and gate-suite bytes identical through final implementation HEAD: 356 passed, 1 dependency warning, 99.78s
- Ruff over every changed Python file: All checks passed
- git diff --check from starting authority through final HEAD: clean
- Frozen-plan Git blob: 68f740af86dc7d1ac2227f81a6ea28e7e2c7458f
- B1a pilot-seal constant: b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2; unchanged and asserted by the gate
- Win32 mypy census: expected waiver, exactly 15 errors in 1 file

The repeated RequestsDependencyWarning for urllib3 2.6.3 or chardet 7.1.0 / charset_normalizer 3.4.4 remains explicit open evidence for G2-P3. It did not fail any suite and is not waived here.

## Commits

1. 2b5112ed fix(egress): disable strict HTTP execution
2. 8260c66c fix(dual-live): bind Phase B sources to origin
3. 377c577d docs(dual-live): reconcile final Task 8 surface
4. 6bf4e6bf fix(dual-live): propagate Phase B source failures
5. e54ed685 docs(api): expose CLI-only egress execution
6. 48d82865 feat(dual-live): archive poisoned recovery state
7. e9b0f0fc test(dual-live): prove Phase B kill boundaries
8. 3bf0ba23 test(dual-live): allow G2 prep production paths
9. 7eaf92db test(dual-live): guard Phase B fault children
10. 855658e6 feat(dual-live): add operator poison action
11. 4afb3281 fix(dual-live): harden poison marker publication
12. 7c13ee08 test(dual-live): close poison safety review
13. 13b75253 docs(dual-live): close G2 offline prep

No commit contains an AI/co-author/generated trailer.

## Exact changed surface from starting authority

1. backend/app/api/router.py
2. backend/app/services/dual_live_evaluator.py
3. backend/tests/support_dual_live_p4.py
4. backend/tests/test_arming_api.py
5. backend/tests/test_dual_eval.py
6. backend/tests/test_dual_live_p4_faults.py
7. docs/campaign-records/2026-08-02-g2-prep.md
8. docs/superpowers/plans/2026-07-31-task8-a-scoped.md
9. tests/test_dual_gate.py
10. tests/test_dual_live_recovery.py
11. tools/dual_live_recovery.py

No frozen plan, sealed campaign/record, B1a source, state/agent-inbox, forward-plan-review, fenced worktree, load-bearing Win32 source, or production transaction model was changed.

## Remaining G2 boundary

This PREP subset does not authorize or complete G2. Remaining blockers are exactly:

- P1 host provisioning
- P2 host reproduction
- P3 supply-chain/CVE attestation
- live-host/provisioning half of P5
- P6 owner residual acceptance
- P8 separate explicit live-run authorization

P7 was already closed by G1. P9 is nonblocking. Nothing in this reply permits fresh live ScienceBase or NRC APS acquisition.

Goal accounting: 1,049,113 tokens; 7,728 seconds (about 2h 8m 48s).

## Adversarial verification (Fable, 2026-08-02) — G2-PREP-SOUND; C2 delta review PASS
Zero critical/major. Every quantitative claim reproduced on this host (21/39/27/356/404 tests, 15 mypy,
evidence-record SHA-256, frozen blob 68f740af, seal b8a89df2, no-push). Both substrate changes PASS C2:
- Route-disable (router.py:593-613): the 409 fires BEFORE any side effect — lazy SQLAlchemy session
  (never touched), header-only auth gate, all 4 service seams + the route clock monkeypatched to
  pytest.fail and proven un-reached; OpenAPI advertises only the 409 contract; auth behavior + non-strict
  routes unchanged; no alternate HTTP path to claim/executor (claim only called from the CLI child).
- Evaluator structural fail-closed (dual_live_evaluator.py:1183-1184): phase_b_sources->origin,
  downstream->origin+phase_b_sources; propagation is ADD-ONLY; r17 blocks via _domain_error (INDETERMINATE)
  before any evidence read and cannot PASS on those failures; aggregation blocks on INDETERMINATE; base-vs-
  head confirms the pre-fix incidental-only gap is now structural. No new false-PASS.
- Recovery tool (tools/dual_live_recovery.py, fully read): stdlib-only, SQLite mode=ro+immutable/query_only,
  zero DML/deletion; poison publish via production atomic strict-new no-replace publisher (partial final
  poison.json structurally impossible, fsync-injection test confirms); raw SQLite family byte-preserved
  (SQLite never opens the raw DB during archive); symlink/reparse+junction refusal (real-host test);
  network denial. Disclosed residuals (interrupted poison-publish / archive) correctly bounded — retained,
  never a false/actionable state, force operator adjudication.
- P4 harness: real Popen(-I -B) children killed at 22 REAL commit boundaries (trip() after the ORIGINAL
  production commit returns), DB-derived contiguous-prefix classification (independent of the harness),
  every partial FAIL/INDETERMINATE never PASS; secret-free/default-off children with production denial
  guards installed+exercised+re-asserted; no silent-refetch path.
- Scope/STOP clean: exactly 11 files, frozen+seal untouched, dual_live_windows.py zero changes, no
  atomicity-model change, no credential provisioning, no C3 PREP-ONLY violation; 15-mypy waiver legit
  (0 runtime defects); G2-P3 dependency warning correctly left OPEN not waived.
3 MINORS (non-blocking, for a future hygiene pass / the P5 live-host half): (1) a pre-existing census
flake (test_seq_owned_binder... , range-untouched, isolated-passing — harden its timing before a gate run);
(2) gate-allowlist self-widening (legitimate/minimal here, but every future delta review must diff it —
this one did); (3) no interrupted-ARCHIVE test (poison-interrupt is tested; archive-interrupt is design-
bounded+disclosed only). NITs: dead route params, a dead except-branch, add a tripwire-seam comment on
_strict_egress_executor so a future dead-code cleanup doesn't remove the seam the tests depend on.

**G2 OFFLINE-PREP COMPLETE + VERIFIED. Remaining G2 is entirely owner/infra-gated (P1/P2/P3 provisioning
+ CVE, P5 live-host half, P6 residual acceptance, P8 live-run authorization).**
