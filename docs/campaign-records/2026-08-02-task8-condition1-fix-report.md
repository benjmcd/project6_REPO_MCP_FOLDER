# Task-8 Condition-1 TOCTOU fix report — Codex 019faabd

Date: 2026-08-02. Fix range d4159ff8..402bd173 (4 commits). Replaces the mtime/ctime file fingerprint
with content-based (bounded SHA-256) stability in layer3_execution_output.py + layer3_origin_continuity.py
(downstream snapshot guard + publication comparison). REPRODUCED on host <operator-host> py3.12.10:
test_dual_eval.py 401/401 green x2 (290s/291s exit 0); 3 tamper campaigns 5 passed exit 0 (satisfies
condition 1 + condition-4 tamper-execution half); gate 356 green; V4 806 green; affected-module 126 green;
Ruff clean; git diff --check clean. Independent Sol review of exact delta: APPROVE 0 findings (C/H/M/L=0).
WorkbenchError left unchanged (did not mask diagnosis after the fix). Scope: 6 files (2 production Layer-3
+ 2 tests + dual_gate test + this evidence). Frozen plan 68f740af + B1a seal b8a89df2 untouched (seal passed
in the 356 gate); no push. Disclosed limit: finite observation protocol (not an atomic snapshot) — mutation
wholly before first / after final / changed-and-restored between observations is unobservable (userspace
minimum); +~50% hash I/O on protected reads, localized. Adversarial Fable check running (guarantee-
preservation + broader-Layer-3 regression). Self-verified: scope/frozen/seal/push/evidence all confirmed.
source-sha256: 4e9d4002f603bc039181ecc115c71d3667acdbfe92ec9532bd68b4fc76e8514a

---

# Codex reply — Task 8 Condition 1 TOCTOU fix

Codex session: `019faabd-31a1-7293-a3e7-d49087b95bcf`

## Outcome

COMPLETE and independently APPROVED on branch `codex/dual-live-plan`, worktree `worktrees/dual-live-plan`. No push or merge was performed.

The pre-existing Layer 3 Windows metadata-TOCTOU false trip is corrected with content-based stability checks while preserving fail-closed behavior for observed byte mutation. Timestamp-only churn is accepted; same-size mutation between hashes and after the former final hash is rejected. A third reopened-path bounded SHA-256 observation closes the discovered late-mutation window.

The same minimal correction was applied to the downstream snapshot guard only after the first 401 census exposed it as the identical second blocker. The homologous publication comparison was corrected only after V4 exposed the last timestamp false trip. `Layer3WorkbenchError` was not changed because it did not mask diagnosis after these corrections.

## Commits

- `f571be83b21ea4b7da4331893999e48ee5d082ba` — `fix(layer3): use content stability for managed files`
- `5f76f94969bea8ae8d004de7402c3094ce46ac0d` — `fix(layer3): stabilize downstream content verification`
- `a13a5fa0b3d513e79bbe0d72a32693ca9d5ba202` — `fix(layer3): ignore publication metadata churn`
- `402bd17374af0b858a9c5d400f7c218e75dec2da` — `docs(layer3): record TOCTOU condition proof`

Final HEAD: `402bd17374af0b858a9c5d400f7c218e75dec2da`.
Tested implementation HEAD/tree: `a13a5fa0b3d513e79bbe0d72a32693ca9d5ba202` / `42e01ff3f45ec37f0ff9a6644a0c79fd139700fb`; final commit adds the evidence record only.

## Files touched

- `backend/app/services/layer3_execution_output.py`
- `backend/app/services/layer3_origin_continuity.py`
- `backend/tests/test_layer3_execution_output.py`
- `backend/tests/test_layer3_origin.py`
- `tests/test_dual_gate.py`
- `docs/campaign-records/2026-08-02-task8-toctou-condition1.md`

No frozen/fenced files were touched. The only remaining worktree residue is the pre-existing untracked `.omc/state/sessions/`.

## Reproduced evidence

Host: `<operator-host>`, Alienware Aurora ACT1250, Windows 11 Home 10.0.26200 64-bit, Python 3.12.10.

- Standalone dual evaluator run 1: `401 passed, 1 warning in 290.63s`, exit 0.
- Standalone dual evaluator run 2: `401 passed, 1 warning in 291.31s`, exit 0.
- Three named tamper campaigns: `5 passed, 1 warning in 69.53s`, exit 0. Five items are expected because the third campaign is parametrized for delete/duplicate/rewrite.
- Final-head gate: `356 passed, 1 warning in 98.02s`, exit 0.
- Exact final-head V4: `806 passed, 3 warnings in 335.05s`, exit 0.
- Combined affected-module regression: `126 passed, 1 warning`.
- New publication regression plus exact formerly failing V4 node: `2 passed`.
- Ruff on affected Python files: `All checks passed`.
- `git diff --check`: clean.

The committed host-bound transcript and evidence classification are in `docs/campaign-records/2026-08-02-task8-toctou-condition1.md`.

## Independent verification

Final Sol review mechanically inspected exact delta `d4159ff8..402bd173` and returned APPROVE:

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

It confirmed the six-file scope, identity plus three bounded SHA-256 observations, exact publication-byte and DB-bound payload-hash checks, narrow gate allowlist, evidence/count consistency, frozen hashes, and G2 nonclaims.

## Authority and limits

- Frozen M0 plan remains `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`.
- Prior accepted completion record remains `8d5e9dafc10de67f5dcf499f900169c0175197e2`.
- B1a pilot-seal assertion remains `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` and passed in the 356-test gate.
- Offline only: no egress, credentials, push, merge, default-on change, or live acquisition.
- This is a finite observation protocol, not an atomic filesystem snapshot. Mutation wholly before the first observation, after the final observation, or changed-and-restored wholly between observations is not observable.
- The third bounded content pass adds approximately 50% hash I/O to these protected reads; this is documented and localized.
- The host still emits a Requests dependency warning and is not claimed dependency-eligible for a real/live run.
- Condition 1 and the tamper-execution half of condition 4 are now evidenced. G2/live acquisition remains blocked by the other governing prerequisites, explicit authorization, and live-run dependency eligibility.

Goal usage: 428,700 tokens over approximately 1 hour 14 minutes.

## Adversarial verification (Fable, 2026-08-02) — TOCTOU-FIX-SOUND (ACCEPT, no critical/major)
Scope expanded beyond the diff to all 14 _stable_managed_file call sites across 3 modules + the
evaluator's own fingerprint + gate semantics. Independently REPRODUCED at final HEAD 402bd173: census
401/401 green (a THIRD run, 317.74s exit 0), gate 356, affected-module 126, package_entry 15 (the
formerly-failing V4 node) — zero new failures. GUARANTEE PRESERVED: content-hash fail-closes on real byte
mutation incl. SAME-SIZE (test-proven b"before"->b"after!"); mid-pass/between-pass/after-pass-2 all
rejected (3rd observation, hash_count==3); growth trips remaining+1 overread, shrink trips size!=initial,
symlink/rename trips dev/ino, reparse rejected by _managed_regular_file walk; no new TOCTOU (callers
consume captured pass-1 bytes, never a post-guard re-read). Downstream snapshot guard got STRONGER
(anchored to DB-bound payload_hash, layer3_origin_continuity.py:4118). Frozen 68f740af + B1a seal +
completion-record blob 8d5e9daf + tree 42e01ff3 all byte-verified; no push. Sol 0-findings confirmed
sound (Fable adds 2 recorded minors).
TWO MINORS (non-blocking, optional one-line fixes):
1. The pre-first-read unobservable window is marginally wider than the old code for ONE class (same-size
   mtime-visible rewrite between preflight-stat and first read, in the artifact-receipt path) because
   identity dropped mtime. MITIGATED: mtime was never adversarial (forgeable via os.utime), every
   ground-truth consumer (DB-bound payload_hash) still fail-closes, and keeping any mtime reintroduces the
   false-trip — effectively the irreducible userspace minimum under the no-false-positive requirement.
   OPTIONAL: add one disclosure sentence acknowledging the comparative loss (recorded here in lieu of
   editing Codex's evidence doc).
2. Gate allowlist widening (test_dual_gate.py:101 adds execution_output.py to
   ALLOWED_CHANGED_PRODUCTION_PATHS) is permanent + file-level vs range-scoped — same kind as existing
   entries (origin_continuity already listed), disclosed. OPTIONAL future hardening: content-hash-pinned
   allowlist. Not actionable now.

## CONDITION-1 CERTIFICATION
Census reproduces GREEN (3 independent runs: 2 Codex + 1 Fable, ordinary Windows py3.12.10 host);
guarantee-sound + no regression, adversarially confirmed. **Review condition 1 SATISFIED. Condition-4
tamper-execution half SATISFIED (3 campaigns execute green).** The Task-8 A-scoped OFFLINE BAR is now
CERTIFIED PASS. Remaining G2 prerequisites (unchanged): py3.12 dependency provisioning + explicit owner
live-run authorization + the full governing gate.
