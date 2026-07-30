# G1 implementation report — Codex 019faabd (offline Tasks 1-9)

Date: 2026-07-30. Delegated implementation against frozen M0 baseline c7b47543.
DISPOSITION: NOT a complete Tasks 1-9 implementation. Tasks 1-5 bounded-complete + independently
approved; Task 6 partial (production-unreachable); Tasks 7-8 absent; Task 9 fails (Task 8 files missing
+ no-skip contradiction). Four frozen-spec contradictions S1-S4 correctly STOPped, not silently resolved.
Final HEAD 950a2b28, worktree clean, 25 files +21,667/-31, no egress/grants/pushes.
source-sha256: c420a4822003bb488e38c7a6fff6a3b42290b35c3f2a6b242a76541cea1b18a7

---

# Codex IPC result — G1 dual-live offline controls

Codex session/conversation ID: `019faabd-31a1-7293-a3e7-d49087b95bcf`

## Disposition

**G1 IS NOT ACCEPTED AS A COMPLETE TASKS 1–9 IMPLEMENTATION.**

The bounded offline control plane for Tasks 1–5 is implemented and independently approved at the code/security level. Task 6 has a tested derivation/assertion primitive but is not production-reachable. Tasks 7–8 are not implemented. Task 9 therefore fails its exact acceptance commands. Frozen-contract contradictions were treated as STOPs, exactly as the handoff required; none was silently “resolved” by weakening an invariant.

Do not arm or run a live campaign, package anything as `fresh_live`, claim G2/egress readiness, or treat this candidate as end-to-end proof.

No live egress, credentials, grants, runtime proof artifacts, pushes, deployment, or external delivery occurred.

## Candidate binding and integrity

- Worktree: `worktrees/dual-live-plan`
- Branch: `codex/dual-live-plan`
- Frozen baseline: `c7b47543`
- Final HEAD: `950a2b28960a4c243ad9caaccd74f9588cb78ea0`
- Final tree: `2f8d004e06d59acec82eee1ef05d0e04c8f2353f`
- Worktree: clean at final commit
- Frozen plan SHA-256: `2B1CB17889CE9535EE8986EB1BD0D6773197FC96FE4455B33E0A1E599A012560`
- Frozen campaign SHA-256: `FED23FED25135C63D9D98BC06E2B43CA8CDD8B67F5A15C66B977E3F8763801CD`
- Protected-path diff from `c7b47543` was empty for both frozen documents, `state/agent-inbox`, `forward-plan-review`, and the fenced B1B correction path.
- Candidate delta: 25 files, 21,667 insertions, 31 deletions.
- `git diff --check c7b47543..HEAD`: exit 0.

## Task-by-task result

### Task 1 — strict campaign, grant, target, and authorization contracts

**Status: REPO-CONFIRMED, bounded complete.**

Implemented strict canonical campaign/grant validation, protected authority resolution, evidence-index binding, default-off configuration, strict request/schema contracts, and fail-closed equality for `max_single_send_detection_allowance_bytes == 6,684,672`.

Production files:

- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/schemas/api.py`
- `backend/app/services/connector_egress_authorization.py`

Tests added/expanded:

- `backend/tests/test_egress_schema.py`
- `backend/tests/test_egress_auth.py`

Verified in V1 below.

### Task 2 — immutable arming and arm/execute separation

**Status: REPO-CONFIRMED implementation; governance STOP for expiry terminalization.**

Implemented immutable protected armings, owner-authorized API boundaries, deterministic parent IDs/submission idempotency, `(run, claimed_now)` claims, exact-token leases, lease-gated reservations, strict-only finalization with deterministic terminal events, and the server-side `evaluate_nrc_acquisition_success` call inside ScienceBase arming creation. Generic strict subresource reads fail closed, the claim clock is captured after authorization, and execute idempotency is global across connectors.

Production files:

- `backend/app/services/connector_egress_arming.py`
- `backend/app/api/router.py`
- `backend/main.py`

Tests added/expanded:

- `backend/tests/test_egress_arming.py`
- `backend/tests/test_arming_api.py`
- `backend/tests/test_legacy_api_operator_identity.py`

Verified in V1, V6, and supplemental suites below. Independent arming/security review: bounded APPROVE, zero scoped code findings; medium governance STOP described under S1.

### Task 3 — durable reservation ledger and bounded one-send transport

**Status: REPO-CONFIRMED, bounded complete.**

Implemented reservation-before-send, completion accounting, canonical ISO-8859-1 status/header serialization, post-serialization/per-chunk/EOF `aggregate_crossed := H + B > R` enforcement, byte/run caps, terminal oversized semantics, no transport retries/redirect following, fsynced campaign `http.jsonl`, and spent-unknown crash behavior. The shared stream now accepts the canonical NRC prefix followed by ScienceBase while rejecting malformed/noncanonical predecessors, foreign records after the current segment, duplicates, reorder, mutation, and unmatched current-run records. The 99-header fixture and six aggregate fixtures are covered.

Production file:

- `backend/app/services/connector_egress_transport.py`

Tests added:

- `backend/tests/test_egress_transport.py`
- `backend/tests/test_egress_crash.py`

Verified in V1. Independent connector/security review: bounded APPROVE, zero Critical/High/Medium/Low findings.

### Task 4 — exact fresh ScienceBase state machine

**Status: REPO-CONFIRMED strict raw-acquisition lane; frozen persistence ambiguity STOP.**

Implemented exact item hydration, exact filename selection, anonymous artifact GET, at most one separately re-armed redirect, strict path/host/public-address checks, bounded transport, content-addressed raw persistence, safe projections, zero generic discovery/resume, and reserved-provenance rejection in both schema and service before database mutation or enqueue.

Production files:

- `backend/app/services/connectors_sciencebase.py`
- `backend/app/schemas/api.py`
- `backend/app/api/router.py`

Tests added/expanded:

- `backend/tests/test_sciencebase_fresh.py`
- `tests/test_api.py`

Verified in V2, V3, V7, and V8. The strict lane intentionally remains raw-only; it does not create `DatasetVersion`, `DatasetSourceProvenance`, connector-source-intake, or a stored origin receipt. Frozen line 1590 asks for provenance and `DatasetVersion.content_hash`, while the later two-phase sequencing keeps downstream interpretation/continuity after acquisition. This unresolved boundary is recorded, not guessed.

### Task 5 — NRC exact-accession and derived-artifact state machine

**Status: REPO-CONFIRMED strict raw acquisition and guarded parser; frozen linkage contradiction STOP.**

Implemented one exact accession API request with the NRC key only at ordinal 1, one anonymous exact derived PDF GET, strict identity/status/media/size checks, content-addressed raw persistence, no redirect/retry/resume, no generic OCR/index/linkage call during acquisition, plus `nrc_aps_strict_parse.py` with fixed profile, hash verification, bounded native parsing, network/subprocess denial, refusal on resource breaches, and no degradation fallback.

Production files:

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_strict_parse.py`
- `backend/app/services/nrc_aps_document_processing.py`

Tests added:

- `backend/tests/test_nrc_fresh.py`
- `backend/tests/test_nrc_strict_parse.py`

Verified in V2, V3, V7, and V8. Frozen line 1742 asks acquisition success to bind `ApsContentLinkage.blob_sha256`; lines 1797–1800 say the executor ends at raw admission without document processing; lines 1925–1927 place `ApsContentLinkage` binding downstream. No linkage was silently moved into Phase A.

### Task 6 — canonical connector-origin continuity receipt

**Status: PARTIAL / HIGH STOP.**

Implemented bounded receipt reconstruction and continuity assertion in:

- `backend/app/services/layer3_origin_continuity.py`
- `backend/tests/test_layer3_origin.py`

The 29 focused origin tests pass, and `evaluate_nrc_acquisition_success` calls both derivation and assertion. However, this is not production-reachable:

1. NRC receipt derivation requires exactly one `ApsContentLinkage` (`layer3_origin_continuity.py:521–570`).
2. Receipt assertion requires `source_reference_json["connector_origin_receipt_v1"]` already stored (`:1455–1465`).
3. The strict NRC Phase-A executor deliberately persists raw bytes and returns before generic processing/linkage.
4. ScienceBase arming calls `evaluate_nrc_acquisition_success` before ScienceBase acquisition (`connector_egress_arming.py:1015–1025`).
5. The frozen execution order creates ScienceBase arming only after the NRC predicate passes (plan 2826–2851), but delays parsing/downstream Phase B until both acquisitions and quiescence (plan 2855–2869).
6. No production writer for `connector_origin_receipt_v1` exists. Tests manually store it; arming tests mock derivation/assertion.
7. ScienceBase receipt derivation also needs DatasetVersion/provenance/intake relationships that its strict raw lane does not create.

Therefore the required NRC-to-ScienceBase order is a fail-closed dead end. The function exists; the campaign cannot reach its success state.

### Task 7 — revalidate origin through execution, review, package, and handoff

**Status: NOT IMPLEMENTED / HIGH STOP.**

The frozen order cycle in Task 6 prevents a valid production origin receipt from entering Layer 3. No false downstream continuity was built around test-only receipts. Existing package construction still hashes each of the three payload kinds, and handoff remains prepared/internal with external delivery disabled, but the required `connector_origin_receipt_hash`, `artifact_set_hash`, `output_manifest_hash`, and boundary revalidation are absent.

### Task 8 — validate-only campaign evaluator

**Status: NOT IMPLEMENTED / HIGH STOP.**

Absent by exact inventory:

- `backend/app/services/connector_campaign_log_capture.py`
- `backend/app/services/dual_live_evaluator.py`
- `tools/dual_live_gate.py`
- `backend/tests/test_campaign_log_capture.py`
- `backend/tests/test_dual_eval.py`
- `tests/test_dual_gate.py`

`project6.ps1` also has no `run-dual-live-proof` or `validate-dual-live-proof` action. Without a reachable receipt/downstream chain, an evaluator would only certify synthetic or incomplete evidence, so implementation stopped rather than creating a misleading gate.

### Task 9 — complete offline adversarial gate

**Status: FAIL / STOP; no full-green claim.**

The implemented control and connector slices pass, but the exact Layer 3 and root gate commands fail because Task 8 test files are absent. Additionally, the exact connector command reports one structural skip: its parent-only guard test launches a protected child and deliberately expects the child result `29 passed, 1 skipped`, while frozen plan line 2639 says no full-green claim if any command is skipped. The broad backend command reports 14 skips as well.

## Exact verification evidence

All commands were offline and fixture/mock based.

**V1 — exact control suite, workdir `backend`:**

`python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py tests/test_egress_arming.py tests/test_arming_api.py tests/test_egress_transport.py tests/test_egress_crash.py -q`

Exit 0: **184 passed**, 2 warnings.

**V2 — exact connector suite, workdir `backend`:**

`python -m pytest tests/test_sciencebase_fresh.py tests/test_nrc_fresh.py tests/test_nrc_strict_parse.py -q`

Exit 0: **138 passed, 1 skipped**, 1 warning. Process success, but frozen no-skip acceptance is not met.

**V3 — exact root connector API slice:**

`python -m pytest tests/test_api.py -q -k "sciencebase or nrc_adams"`

Exit 0: **30 passed, 134 deselected**, 11 warnings.

**V4 — exact Layer 3 continuity command, workdir `backend`:**

`python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q`

Exit 1: **no tests ran**; collection stopped because `tests/test_campaign_log_capture.py` is absent.

**V5 — exact root dual gate:**

`python -m pytest tests/test_dual_gate.py -q`

Exit 1: **no tests ran**; `tests/test_dual_gate.py` is absent.

**V6 — present Layer 3 subset, workdir `backend`:**

The V4 command without the two absent Task 8 files.

Exit 0: **68 passed**, 4 warnings.

**V7 — exact full root API:**

`python -m pytest tests/test_api.py -q`

Exit 0: **164 passed**, 55 warnings.

**V8 — exact broad backend structural slice, workdir `backend`:**

`python -m pytest tests -q -k "layer3 or connector or nrc"`

Exit 0: **3,240 passed, 14 skipped, 1,153 deselected**, 23 warnings in 552.89 seconds.

**V9 — exact progress checker:**

`python .\tools\l3-progress-check.py`

Exit 0: `Layer 3 progress state check: PASS`.

**V10 — exact whitespace check:**

`git diff --check`

Exit 0, no output. `git diff --check c7b47543..HEAD` also exited 0.

Supplemental verification:

- `python -m pytest backend/tests/test_legacy_api_operator_identity.py -q`: **157 passed**, 2 warnings.
- `python -m pytest backend/tests/test_layer3_origin.py -q`: **29 passed**, 1 warning.
- Full corrected Ruff check over implemented changed surfaces: `All checks passed!`. An earlier lint invocation named a nonexistent test path; this was a command-list error, not a source failure, and was corrected before closeout.
- Independent connector security: bounded APPROVE; 0 findings; focused **189 passed, 1 expected skip**.
- Independent arming/API security: bounded APPROVE; 0 scoped code findings; **237 passed**, exact regressions **9 passed**, reserved-marker API **12 passed**.
- Independent Layer 3 integrity: high-confidence STOP for Tasks 6–9; independently reproduced V2/V4/V5 and the missing production receipt path.

## Frozen-contract deviations / owner decisions required

### S1 — lease expiry has mutually exclusive terminal rules

Plan 1089–1104 requires finalization under the exact active lease. Plan 1592–1597 and 1743–1746 require every strict stop to finalize `failed`. Once the lease expires, both cannot be true. The final candidate preserves the active-only rule: expiry permits no new send or renewal, but the run can remain `running` without a terminal event.

Security impact is fail-closed for egress; availability/accounting risk remains for one consumed grant/run. Owner must choose and record either:

- narrowly authorized expired same-token **failed-only** closeout, granting no send, persistence continuation, renewal, resume, or recovery authority; or
- an explicit stranded/indeterminate state and governed recovery contract.

### S2 — raw acquisition versus provenance/linkage timing

Task 4 acceptance asks for DatasetVersion/provenance during strict ScienceBase success. Task 5 acceptance asks for ApsContentLinkage during strict NRC success. Other frozen text makes Phase A raw-only and explicitly defers NRC linkage/parsing to the secret-free, network-denied Phase B. Owner must establish one timing boundary rather than leaving two incompatible acceptance readings.

### S3 — predecessor predicate versus final origin receipt

The shortest safe correction is to split two concepts:

1. a minimal NRC acquisition-success sequencing receipt, derived only from completed strict run, terminal ledger, raw content-addressed target, authority/grant bindings, and no parsing/linkage; and
2. the final canonical connector-origin receipt, minted/stored after Phase-B linkage/provenance exists and then revalidated through Layer 3/review/package/handoff.

Alternative: explicitly authorize linkage/provenance and canonical receipt minting before ScienceBase arming. That broadens Phase A and is higher risk because it mixes downstream interpretation with a still-live acquisition process.

### S4 — no-skip acceptance is incompatible with its prescribed command

Either restructure the guarded parser test so the parent command reports zero skips, or amend Task 9 to forbid **unexpected** skips while requiring every expected skip to be named and its guarded child result to pass. Current frozen wording cannot support a full-green claim.

One owner-approved delta packet covering S1–S4 is the most efficient governance path. After that, the next implementation sequence should be: production receipt mint/store and Task 7 continuity; sealed log/evaluator/validate-only runner in Task 8; then the exact Task 9 gate. This groups the coupled governance choices once and avoids churn.

## Residual risks and nonclaims

- No Python CVE-clean claim: `pip-audit` was unavailable offline. The shared interpreter emitted Requests/dependency compatibility warnings. Re-run in lock-isolated CI with an available vulnerability audit before production consideration.
- Offline `npm audit` reported zero vulnerabilities for the applicable surface.
- Public-address DNS validation does not eliminate all DNS TOCTOU risk; this remains a documented residual.
- Unit/integration mock evidence is not multi-process, production-host, or live-network proof.
- No G2, egress-readiness, fresh-live-completed, production-readiness, delivery, deployment, owner grant, or live acquisition claim follows.

## Commit list from frozen baseline

1. `cb9b6d62499be2d754da134d77b1625c56c70c5b` — feat(nrc-aps): add strict downstream parser profile
2. `13702b35a3b3164c4541c730d913ea5a9cb571d2` — feat(connectors): add protected egress authority contracts
3. `8ba4829b9d9d93eb507c09852b28561d2b879607` — feat(connectors): add bounded strict egress transport
4. `a049a317cdfc9a8aef4b31b95aa666c0310645fe` — feat(layer3): add bounded origin continuity derivation
5. `d6d66600e9e39559a2afd9796895d211b81c515f` — feat(connectors): add strict egress arming state machine
6. `4c245e7824151bc7a219e691cba15e4b62846a00` — feat(api): protect strict egress arming operations
7. `948f7891d81a5bc6e33a3ada294c612de0fcf4ed` — fix(connectors): reconcile shared campaign counters
8. `c5da35bfd836b7dadcea72d83758b823b394521d` — fix(connectors): preserve frozen active lease finalizer
9. `4642d2a9fe95a9d8851acce6709ad8c2be7cc7a1` — fix(api): reject reserved ScienceBase egress markers
10. `c26f0b97a05d870d7c8f62335981b4c3e8291d7e` — feat(sciencebase): add strict raw admission lane
11. `950a2b28960a4c243ad9caaccd74f9588cb78ea0` — feat(nrc): add strict raw admission lane

## Final conclusion

**REPO-CONFIRMED:** Tasks 1–5 provide a substantial default-off, offline-tested authorization/arming/transport/raw-admission foundation, and the bounded Task 6 derivation is well tested. The code fails closed and independent reviewers found no scoped code vulnerability.

**REPO-CONFIRMED:** The frozen campaign is not end-to-end reachable, Tasks 7–8 are absent, and Task 9 is not green. The correct next action is an owner-approved S1–S4 delta, not more implementation against contradictory authority.

Goal accounting: 2,016,301 tokens; 13,099 seconds (about 3h 38m).
