# G1 completion report — Codex 019faabd

Date: 2026-07-30. VERDICT: STOP / G1 NOT COMPLETE. Items 2/3/4 done; item 1 (FULL Task-8 evaluator)
STOPped on a producer/evidence-independence contract gap (frozen clauses 2315-2322, 2350-2362 require
independent evidence the current producer does not emit: coordinated-rewrite detection, prior-runtime
logger census, runtime-child quiescence). Codex refused to ship a fake/weakened evaluator; produced a
design doc (docs/dual-live-postrun-evidence-design.md, commit 0fd9525e). OWNER CHOICE A/B required.
HEAD e24b29e4. Clause-5 real-ledger e2e PASS (e24b29e4). B1a provenance docstring (90a0447d), seal
UNCHANGED. Task-9 FULL census GREEN: V1 199, V2 154, V3 30/134-desel, V4 305, V4-corrected 314, V5 71,
V6 164, V7 3578/13-skip, V8 PASS, git diff --check clean — zero B1a STOP, zero weakening. Only 2 test
files changed since 3f6035e0; no push/egress/plan-edit.
source-sha256: e7288221304c7a322c245e1c9bc4c6821cc4fcbe3fd54b1f500c14b67572546f

---

# G1 completion handoff result

Codex session/conversation ID: 019faabd-31a1-7293-a3e7-d49087b95bcf

## Overall verdict

**STOP / G1 NOT COMPLETE.**

The independently valid folded deferrals are complete and the entire Task-9 offline census is green, but the requested **FULL Task-8 evaluator** cannot truthfully be implemented as PASS-capable against the evidence the current producer creates. I did not ship a partial evaluator and label it complete.

Current branch: `codex/dual-live-plan`  
Current HEAD: `e24b29e4aaa86c84edb7d5a3c13e3e6f5ad8aa59`  
Push: none.

## Evidence-classified result by requested item

### 1. FULL Task-8 evaluator + validate-only gate — STOP / OPEN

**REPO-CONFIRMED blocker:** three frozen acceptance clauses require independent evidence that the present producer does not emit.

1. **Coordinated rewrite detection is unprovable.** The current proof graph is logs -> manifest -> seal <-> ordinary mutable DB seal event. A coordinated rewrite of every mutable domain can retain perfect final parity because no independently protected post-run digest anchors the cycle.
2. **Prior-runtime logger census is absent.** Capture startup opens the four streams but does not record an independently bound handler census. The manifest contains runtime timestamps and file projections only; a post-run evaluator cannot reconstruct disappeared process handler state.
3. **Runtime-child quiescence is absent.** `runtime_stopped_at` is caller-supplied. No wrapper-owned child identity, exit record, process-tree/socket census, lock, or immutable quiescence attestation exists. The current `run-dual-live-proof` action remains a static refusal.

A PASS-capable evaluator would therefore have to trust absent/unbound producer assertions or weaken frozen clauses 2315-2322 and 2350-2362. The task explicitly required STOP-and-record on code-forced deviation, so no evaluator/gate weakening was committed.

**Also repo-confirmed:** the current evaluator remains a static `INDETERMINATE` scaffold, and the current gate still passes `_NoAccess` for DB/settings and accepts only that exact scaffold report. Green V4/V5 tests confirm the fail-closed scaffold contract; they do **not** establish full Task-8 acceptance.

**Required owner choice before resumption:**

- **A — recommended for the frozen milestone:** authorize a zero-egress producer/quiescence tranche and a frozen evidence-format amendment. Add a wrapper-owned independently protected post-run attestation binding campaign/index identity, manifest/file-set/seal digests, exact run/seal-event identities, startup logger census, wrapper nonce, child start/exit, and process-tree/socket quiescence. Then implement the hybrid read-only evaluator and real gate through the complete frozen evaluator contract.
- **B — narrower:** explicitly authorize a partial, permanently non-PASS analyzer for presently derivable checks and keep Task-8/G1 OPEN with stable `INDETERMINATE` blocker codes.

Do not infer B from the truncated line reference.

### 2. Clause-5 deferred hardening — COMPLETE / PASS

Commit: `e24b29e4aaa86c84edb7d5a3c13e3e6f5ad8aa59`

Added one parametrized end-to-end test in `backend/tests/test_egress_arming.py`:

- creates real ordinal-1 and ordinal-2 reservation/completion events;
- writes the canonical two-record HTTP counter;
- commits real derived URL arming;
- stores and rehashes the real artifact blob;
- finalizes the strict run;
- calls the real `derive_terminal_request_ledger`;
- runs `evaluate_nrc_acquisition_success` without mocking ledger derivation, predicate, counter reconciliation, or blob rehash;
- proves genuine agreement succeeds;
- proves a same-length blob-only mutation fails closed with `nrc_acquisition_success_blob_mismatch`;
- proves evaluator DB state remains unchanged.

Targeted evidence: exit 0, `2 passed, 48 deselected`.

Independent security/egress exact-commit review: **PASS, no findings**. It additionally ran both cases with socket connect/create_connection hard-blocked and confirmed no network call.

### 3. B1a auditability minors — COMPLETE WITH BOUNDARY NOTE

Commit: `90a0447df496a264a13f7ba4826c2f2e9d182519`

- Added the exact one-line successor module provenance: `B1a Option-2 successor split provenance: predecessor blob 8ec90984.`
- Current pilot seal remains exactly `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`.
- Successor test: exit 0, `9 passed`.
- Exact frozen V4 was run unchanged, and a second corrected V4 was run with `tests/test_layer3_intake_successor.py` appended after the pilot file.
- No tracked V1-V8 orchestrator/gate script exists to pin. The only full-list restatements are the frozen plan and historical campaign reports. They were not edited because the dispatch forbids plan/campaign-doc edits and rewriting old commands while retaining old counts would falsify history.
- Independent Layer-3 exact-commit review: **PASS, no findings**. It verified 22 predecessor tests remain 13 pilot + 9 successor, with no count/name laundering, no plan/report edits, unchanged seal, and no later interference.

### 4. Task-9 full offline census — COMPLETE / GREEN, with Task-8 non-claim

All commands used Python 3.11. Every prescribed command ran. No command was weakened or skipped.

| Gate | Workdir | Exact command | Exit | Counts/result |
|---|---|---|---:|---|
| V1 | `backend` | `python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py tests/test_egress_arming.py tests/test_arming_api.py tests/test_egress_transport.py tests/test_egress_crash.py -q` | 0 | 199 collected; 199 passed; 0 failed; 0 skipped |
| V2 | `backend` | `python -m pytest tests/test_sciencebase_fresh.py tests/test_nrc_fresh.py tests/test_nrc_strict_parse.py -q` | 0 | 154 collected; 154 passed; 0 failed; 0 skipped |
| V3 | repo root | `python -m pytest tests/test_api.py -q -k "sciencebase or nrc_adams"` | 0 | 164 collected; 30 passed; 0 failed; 134 deselected |
| V4 frozen | `backend` | `python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q` | 0 | 305 collected; 305 passed; 0 failed; 0 skipped |
| V4 corrected | `backend` | same V4 with `tests/test_layer3_intake_successor.py` inserted after the pilot file | 0 | 314 collected; 314 passed; 0 failed; 0 skipped |
| V5 | repo root | `python -m pytest tests/test_dual_gate.py -q` | 0 | 71 collected; 71 passed; 0 failed; 0 skipped |
| V6 | repo root | `python -m pytest tests/test_api.py -q` | 0 | 164 collected; 164 passed; 0 failed; 0 skipped |
| V7 | `backend` | `python -m pytest tests -q -k "layer3 or connector or nrc"` | 0 | 4827 collected; 3578 passed; 0 failed; 13 skipped; 1236 deselected |
| V8 | repo root | `python .\tools\l3-progress-check.py` | 0 | `Layer 3 progress state check: PASS` |
| Integrity | repo root | `git diff --check` | 0 | no errors |

The 13 V7 skips are existing conditional skips; the two new clause-5 cases are not skipped. Zero B1a STOP occurred.

## Final integrity and scope

- Changed since dispatch baseline `3f6035e0`: exactly:
  - `backend/tests/test_layer3_intake_successor.py`
  - `backend/tests/test_egress_arming.py`
- Final branch is 58 commits ahead of local `project6-origin/main`.
- Worktree has no tracked modifications. Only the pre-existing `?? .omc/state/sessions/` remains.
- Both new commits have empty bodies and no AI/co-author/generated trailers.
- No push, egress, credentials, live acquisition, plan/campaign-doc edit, seal edit, state/agent-inbox read, forbidden-blob read, fenced-worktree touch, deployment, delivery, or external handoff occurred.

## Non-claims

This result does **not** claim:

- full Task-8 completion;
- a PASS-capable deep evaluator;
- a real validate-only gate over runtime evidence;
- a live ScienceBase/NRC campaign;
- privileged-runner readiness;
- production readiness;
- deployment;
- third-party delivery or handoff.

The concrete value landed is narrower but real: the previously tautological NRC clause-5 seam is now covered through the genuine terminal ledger and blob mismatch boundary; B1a split provenance and current V4 coverage are mechanically explicit; and the complete offline regression census is green. The remaining blocker is an evidence-production/independence contract, not a failing test suite.

