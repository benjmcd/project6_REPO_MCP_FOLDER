# G1 continuation report — Codex 019faabd (substrate build)

Date: 2026-07-30. Base ec506fe7; final HEAD 75460571. Tasks 1-8 built+tested; two deliberate STOPs
(clause-5 unwired [no cleared S3 record existed at build time — now cleared at f7393131]; B1a external
seal governance). Broad suite: 48 prior compat failures -> 0; 1,232 passed before the explicit B1a STOP
receipt (not a failure). No egress/grants/push; frozen docs byte-untouched ec506fe7..HEAD.
source-sha256: 83e826a63888c950db2b29c865159621e6fc1037bb91b822fb13ce365d12388b

---

# G1 continuation result — offline Tasks 1–9

Codex session: `019faabd-31a1-7293-a3e7-d49087b95bcf`

## Disposition

**AUTHORIZED IMPLEMENTATION COMPLETE; TASK-9 HAS ONE EXTERNAL GOVERNANCE STOP; NO FULL-GREEN OR LIVE-PROOF CLAIM.**

The owner-cleared offline substrate was implemented from base `ec506fe7` in `worktrees/dual-live-plan` on branch `codex/dual-live-plan`. Final HEAD is `754605718ac9449771d8b6bca3b9c95a013fe967` (`fix(layer3): preserve legacy authority boundaries`), tree `10f4fa5ead6ef129c1becdbcd74f39875e77f2da`.

All prescribed Task-9 commands are now available and were run. Ordinary regressions found by the broad gate were repaired and reverified. The only remaining nonzero Task-9 exits are caused by the pre-existing B1a explicit STOP receipt, whose sealed source authority is externally hash-bound. Updating that seal without successor governance would be an authority violation, so it was not changed.

No network, egress, credentials, live acquisition, push, PR, deployment, or external handoff delivery occurred. No plan/campaign document changed in `ec506fe7..HEAD`. The current campaign-record directory still contains the S3 decision record saying external review is pending and contains no cleared S3 verdict record; amended clause 5 therefore remains deliberately unwired.

## What was built

### S4 / guarded NRC parser command

Commit `94f6fd99` split the guarded strict-parser proof into a launcher plus a non-collected guarded module. The prescribed connector command now has zero top-level skips: 154 collected and 154 passed.

### S1 / lease finalization and counter authority

Commits `b556de99` and `770f011b` implement the adjudicated token-identity reading. An exact lease-token holder can finalize a strict run as `failed` after expiry; expiry still blocks send/reservation and grants no renewal, resume, additional persistence, or egress authority. Shared campaign-counter reconciliation remains fail-closed.

### ScienceBase Phase-A persistence

Commits `268ab673`, `5947f6d5`, and `9a3e0af1` add the required raw acquisition graph before receipt derivation:

- content-addressed raw bytes and exact `DatasetVersion.content_hash`;
- `DatasetSourceProvenance` plus connector-source-intake rows;
- the frozen safe-field whitelist, with URL scalars null;
- raw-storage handle locking, identity/nlink/parent validation, and POSIX-safe behavior;
- no document parsing in Phase A.

This supplies the provenance/version/intake inputs required by downstream connector-origin receipt derivation while preserving invariant 21.

### NRC Phase-B linkage and custody

Commits `cdc6a4c1`, `a071679e`, `2b0d1fe2`, and `a87649bb` bind `ApsContentLinkage.blob_sha256` in Phase B against the admitted content-addressed bytes. Atomic linkage, recovery custody, concurrent-state revalidation, and failure containment were hardened without moving parsing into the live acquisition phase.

### NRC predicate decoupling

Commits `f8d672cf` and `c0b0734b` remove receipt derivation/continuity from `evaluate_nrc_acquisition_success` and add the bounded read-only Phase-B verifier. Clauses 1–4 remain enforceable from Phase-A evidence. Amended clause 5 was not wired because no cleared external verdict record exists.

### Task 6 / canonical connector-origin receipt

Commit `305a1985` mints and stores `connector_origin_receipt_v1` on the canonical connector target, binds its canonical hash and source-specific authority, and exposes read-only continuity assertions. NRC derives only after Phase-B linkage; ScienceBase derives only after Phase-A provenance/version/intake persistence.

### Task 7 / continuity through Layer 3, review, packaging, and handoff

Commit `fcd278df` preserves and revalidates connector-origin and output-integrity projections through execution, review, package construction, package review, and prepared internal handoff response. Projections are cloned rather than recomputed or flattened. No external delivery was enabled.

A final bounded repair in `75460571`:

- distinguishes weak legacy connector hints from campaign-exclusive strong markers and receipt claims;
- keeps strong ScienceBase/NRC campaign signals fail-closed and rejects contradictory kinds;
- permits only generic in-memory `StaticPool` SQLite forms (`sqlite://` and `sqlite:///:memory:`) to bypass the independent committed-reader requirement;
- continues rejecting reserved markers and file-backed `StaticPool` bypasses;
- revalidates locked session revision, singleton approved plan, ordered pass set, preview, source-intake projection, output metadata, status bindings, and analysis-run identity before result-review mutation.

This removed all 48 broad-suite compatibility failures without weakening reserved-origin authority.

### Task 8A / sealed campaign-log capture

Commit `d5e6d2d5` adds deterministic, bounded, sealed capture of the required connector campaign streams. It validates terminal state, lease/counter/cap authority, canonical snapshots, DB locks, exact stream sets, atomic no-replace manifest/seal publication, file identity and fsync boundaries, rollback/ambiguity handling, and session-bound cleanup. It is not wired to S3 or to a live campaign.

Focused evidence: 67 capture tests passed; 96 egress-authority tests passed; 9 raw-storage tests passed (78 deselected). Four independent bounded reviews returned PASS.

### Task 8B / independent evaluator and validate-only gate

Commit `4727cd12` adds:

- `backend/app/services/dual_live_evaluator.py`;
- `backend/tests/test_dual_eval.py`;
- `tools/dual_live_gate.py`;
- `tests/test_dual_gate.py`;
- default-off `run-dual-live-proof` and validate-only `validate-dual-live-proof` PowerShell actions.

The runner is inert and fail-closed: deterministic environment/argv, child-only socket/DNS guards, dirty-child refusal, strict UUID/fingerprint validation, exact report drift detection, secret-safe refusals, and no app-config/DB/connector imports. `run-dual-live-proof` refuses without authority (exit 2, no child). A safe validate probe returns `INDETERMINATE` (exit 2), not a fabricated verdict. Focused evidence: 23 evaluator tests and 71 gate/PowerShell tests passed. Four independent frozen-byte reviews returned PASS.

## Exact Task-9 verification

Every prescribed command ran offline. Counts below distinguish collection from execution when the explicit B1a STOP prevented a normal pytest completion summary.

### V1 — control suite (`backend`)

`python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py tests/test_egress_arming.py tests/test_arming_api.py tests/test_egress_transport.py tests/test_egress_crash.py -q`

Exit 0: 193 collected, 193 passed, 0 failed, 0 skipped; 2 warnings.

### V2 — connector suite (`backend`)

`python -m pytest tests/test_sciencebase_fresh.py tests/test_nrc_fresh.py tests/test_nrc_strict_parse.py -q`

Exit 0: 154 collected, 154 passed, 0 failed, 0 skipped; 1 warning.

### V3 — root connector API slice

`python -m pytest tests/test_api.py -q -k "sciencebase or nrc_adams"`

Exit 0: 164 collected; 30 selected and passed, 0 failed, 134 deselected; 11 warnings.

### V4 — exact Layer-3/Task-8 suite (`backend`), rerun on final commit

`python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q`

Collect-only census: 314 tests. Execution exit 1: 103 passed, 0 failed, 0 skipped before the explicit `B1a STOP receipt emitted; zero further test mutation`; 211 were not executed. Three warnings. This is not a normal test failure and is not reported as green.

### V5 — root dual gate, rerun on final commit

`python -m pytest tests/test_dual_gate.py -q`

Exit 0: 71 collected, 71 passed, 0 failed, 0 skipped.

### V6 — full root API, rerun on final commit

`python -m pytest tests/test_api.py -q`

Exit 0: 164 collected, 164 passed, 0 failed; 55 warnings in 32.00 seconds.

### V7 — exact broad backend selector, rerun on final commit

`python -m pytest tests -q -k "layer3 or connector or nrc"`

Collect-only census: 4,812 total; 3,575 selected and 1,237 deselected. Execution exit 1 solely because of the explicit B1a STOP: 1,232 passed, 9 pre-existing environment-conditional skips, 0 failed, and 2,334 selected tests not executed after the stop; 7 warnings in 216.08 seconds. The earlier 48 ordinary failures are now zero.

The nine in-command skips do not represent skipped/unavailable prescribed commands and were not introduced by G1. Under adjudicated S4, every prescribed command ran; net-new guarded tests introduce no skip.

### V8 — progress checker

`python .\tools\l3-progress-check.py`

Exit 0: `Layer 3 progress state check: PASS`.

### V9 — integrity

`git diff --check` and `git diff 4727cd12..75460571 --check`

Both exit 0 with no output. Critical Ruff (`E9,F63,F7,F82`) on the final three repair files passed. The tracked worktree is clean.

Supplemental final-repair evidence:

- 12 authority-boundary regressions passed, 45 deselected;
- full selected `test_layer3_api.py` Layer-3/connector/NRC slice: 327 passed;
- non-sealed Task-7 execution/review/package/handoff core: 57 passed;
- progress checker passed after restoring its exact one-line import contract.

## Historical V4/V5 correction

The predecessor report incorrectly called the missing-file pytest usage exits 1. Their historical pre-build exit code was **4**, not 1. On the current implementation the files exist: current V4 reaches the independently governed B1a STOP after 103 passes (exit 1), while current V5 is 71/71 green (exit 0).

## Independent final review

Two independent read-only reviewers rebound approval to exact commit `754605718ac9449771d8b6bca3b9c95a013fe967` and parent `4727cd124f4278e31ef80918b9155f45601f2641`:

- authority/locking review: APPROVE, zero issues;
- tests-to-code/regression review: APPROVE, zero issues.

They verified the exact three-file set, blob basis, and clean diff. A third lock/projection review had already approved the identical frozen working bytes. Parent-side verification, not reviewer assertion, supplies the test evidence.

Final repair file SHA-256 values:

- `backend/app/services/layer3_origin_continuity.py`: `FB295E09AC6F1A12F8A4C4F018A8BB43049CAE7A62411E4D35B76CBF88B064CC`
- `backend/app/services/layer3_workbench.py`: `2D1CF882DCF6AE98D3B27CF01C497E9B27CE9BCD46A155B42678186973B37D52`
- `backend/tests/test_layer3_connector_vertical_loop.py`: `CE61001CEDF5895D1818F7AEF1C210C640EB7986CDFA639893F8E0ECD622DA36`

## Remaining governance stop: B1a

The B1a test is externally bound to source blob `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` and an external child manifest that also binds its locator/authority. The final source blob is now `3e46ccf88a0cf0329cf1be075d8fa073ac2d33cf` because authorized Tasks 1–7 and the compatibility repair legitimately changed the production source.

A local constant bump would not prove the same object and would cascade into manifest/seal hashes. It was therefore rejected. The owner/reviewer must choose what the successor proof means:

1. validate the historical sealed object;
2. split or restore the sealed source-authority object while separately testing successor behavior; or
3. authorize a full successor reseal and external review of the new exact bytes.

These choices are not equivalent. Until one is selected, V4/V7 remain honest STOPs and no named connector-originated workflow is claimed fully proven through the externally sealed Layer-3C/review/package/handoff gate.

## Residual risks and explicit nonclaims

- No cleared S3 verdict record exists; clause 5 is not wired.
- No fresh live ScienceBase or NRC APS acquisition was performed; no live campaign logs or live evaluator PASS exist.
- No production-readiness, credentials-readiness, egress-readiness, deployment, delivery, or external-handoff claim follows.
- The Python child guard does not claim OS-firewall isolation, pre-interpreter `.pth` protection, native/private socket coverage, inherited-FD containment, or arbitrary subprocess containment.
- Row locks prove current-row revalidation under the active DB isolation; they do not establish a universal phantom/serializable guarantee.
- Unit/integration evidence is not multi-process or production-host proof.
- Dependency/deprecation warnings remain; no Python CVE-clean claim was made.

## Final repository state and commits

Tracked state is clean. The only status entry is pre-existing untracked `.omc/state/sessions/`; it was neither inspected, touched, staged, nor committed. No push was performed.

Commits from `ec506fe7`:

1. `94f6fd99` — test(nrc): split guarded strict parser launcher
2. `b556de99` — fix(egress): allow finalization after lease expiry
3. `268ab673` — feat(sciencebase): persist strict phase-a graph
4. `5947f6d5` — fix(sciencebase): lock raw storage handles
5. `9a3e0af1` — fix(sciencebase): preserve posix raw storage
6. `770f011b` — fix(egress): reconcile shared counter segment
7. `cdc6a4c1` — feat(nrc-aps): bind strict phase-b linkage
8. `a071679e` — fix(nrc-aps): harden phase-b atomic linkage
9. `2b0d1fe2` — fix(nrc-aps): harden Phase B recovery custody
10. `a87649bb` — feat(connectors): harden NRC Phase-B custody
11. `f8d672cf` — fix(connectors): decouple uncleared NRC predicate
12. `c0b0734b` — feat(connectors): add read-only NRC Phase-B verifier
13. `305a1985` — feat(layer3): mint connector origin receipts
14. `fcd278df` — feat(layer3): preserve connector origin through handoff
15. `d5e6d2d5` — feat(proof): seal connector campaign logs
16. `4727cd12` — feat(proof): add fail-closed dual-live validation scaffold
17. `75460571` — fix(layer3): preserve legacy authority boundaries

## Recommended next action

Do not add more implementation churn. First resolve the B1a proof-object choice above. Separately, wait for an explicit cleared S3 verdict record before wiring clause 5. Only after both authorities are clear should a separately authorized, isolated-runtime live campaign acquire fresh ScienceBase and NRC APS evidence, seal its logs, run the independent evaluator, and exercise the named Layer-3C → review → package → handoff proof.

Goal accounting: 7,237,005 tokens; 75,420 seconds (about 20 hours 57 minutes).
