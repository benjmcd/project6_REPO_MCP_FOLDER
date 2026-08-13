# B1a Option 2 report — Codex 019faabd (PASS)

Date: 2026-07-30. Owner-ruled Option 2. Commits 890f5fc7 (B1a successor split) + 2111c72f
(sec-xbrl redaction harden). SEAL PRESERVED: FIXTURE_SOURCE_FILE_GIT_BLOB = b8a89df2 UNCHANGED
(self-verified: zero seal-constant edits in the range, pilot file restored to exact sealed bytes,
only test files touched). 9 successor tests split into self-contained test_layer3_intake_successor.py
(AST-identical to the 8ec90984 predecessors, no import from the sealed module); historical 13 +
successor 9 = the 22 from 8ec90984. V4 305 passed, V7 broad 3576 passed/13 skipped/exit 0, ZERO B1a
STOP. Two intermediate regressions (StaticPool test helper; timestamp-substring 200-collision) both
test-only, reproduced+fixed. Independent 5.6-sol reviews (correctness/adequacy/governance) APPROVE.
No production/plan/campaign/seal/inbox/push. This is NOT a reseal — historical attestation intact.
source-sha256: 2df6ce3de99ef3a1bad9e2512769aeeee00971c603b9aa8b2bb2c3722d335c6f

---

# Codex reply — B1a Option 2 complete

Codex session/conversation: `019faabd-31a1-7293-a3e7-d49087b95bcf`

## Verdict

**PASS — owner-selected B1a Option 2 is implemented.** The historically attested source object is restored at its original bound path, its seal constant is unchanged, the nine post-seal behaviors have separate collected coverage, and V4/V7 complete with zero B1a STOP.

This is not an external reseal or re-attestation.

## Authority result

- `backend/tests/test_layer3_connector_source_intake_pilot.py`
  - committed Git blob: `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`
  - working Git blob: `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`
  - SHA-256: `57bc553198c142446ba5b693bc7855e43a6e3c7c63b5d409de04cb09365b749d`
  - 13 historical tests
- `backend/tests/test_layer3_connector_vertical_loop.py`
  - seal remains exactly `FIXTURE_SOURCE_FILE_GIT_BLOB = "b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2"`
  - zero diff mentions of the seal constant
  - bound locator/authority logic remains intact
- `backend/tests/test_layer3_intake_successor.py`
  - 9 successor tests, collected independently of the sealed module
  - zero overlap with the 13 historical tests
  - historical 13 + successor 9 equals all 22 tests from blob `8ec90984fc01d1290f72a56109b26564505056d4`
  - all nine successor test bodies are AST-identical to their `8ec90984...` predecessors
  - self-contained fixture/helpers; no import from the sealed module

**CONFIRMATION: the B1a seal constant was not modified. The sealed source bytes were not modified; they were restored exactly.**

## Implemented changes

1. Restored the frozen pilot path to the exact historical `b8a89df...` object.
2. Added a self-contained nine-test successor module for the authorized Tasks 1–7 behavior previously added to the pilot.
3. Fixed a vertical-loop test-order/import-isolation defect by conditionally synchronizing the mocked origin module onto the cached `app.services` package attribute. No production logic changed.
4. Fixed the pass-entry test harness to use the contract-admitted in-memory `StaticPool`; production committed-authority admission was not widened or reordered.
5. Made the SEC-XBRL receipt redaction test deterministic: it forces the timestamp substring collision, verifies the exact excluded `recorded_at`, and still scans every payload-relevant receipt field.

## Exact verification

CWD `backend` unless stated otherwise.

- `python -m pytest tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_intake_successor.py --collect-only -q -p no:cacheprovider`
  - `22 tests collected`
- `python -m pytest tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_intake_successor.py -q -p no:cacheprovider`
  - `22 passed, 2 warnings`
- `python -m pytest tests/test_layer3_connector_vertical_loop.py -q -p no:cacheprovider`
  - `57 passed, 3 warnings`; zero B1a STOP
- V4:
  - `python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q -p no:cacheprovider`
  - `305 passed, 4 warnings`
  - Together with the separately collected 9 successor tests, the prior 314-test behavior census is preserved without duplicate historical execution.
- `python -m pytest tests/test_layer3_pass_entry.py -q -p no:cacheprovider`
  - `24 passed, 1 warning`
- `python -m pytest tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py -q -p no:cacheprovider`
  - `28 passed`
- V7 broad Step-4 backend gate:
  - `python -m pytest tests -q -k "layer3 or connector or nrc" -p no:cacheprovider`
  - `3576 passed, 13 skipped, 1236 deselected, 23 warnings`; exit 0; zero B1a STOP
- Root Step-4 API gate, CWD repo root:
  - `python -m pytest tests/test_api.py -q -p no:cacheprovider`
  - `164 passed, 55 warnings`
- Root progress gate:
  - `python .\tools\l3-progress-check.py`
  - `Layer 3 progress state check: PASS`
- Integrity:
  - `git diff --check` and `git diff --check HEAD~2..HEAD`: exit 0; only non-failing Windows line-ending advisories appeared
- Post-commit touched-surface rerun:
  - `python -m pytest tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_intake_successor.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_pass_entry.py tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py -q -p no:cacheprovider`
  - `131 passed, 3 warnings`
- Ruff:
  - new successor and modified vertical-loop module: clean
  - pass-entry retained the same 9 inherited `E402` findings as HEAD
  - SEC-XBRL test retained the same 3 inherited `F401` plus 1 inherited `F841` findings as HEAD
  - no lint-code regression was introduced

Two intermediate broad runs provided regression evidence:

- Before the StaticPool correction: `4 failed, 3572 passed, 13 skipped, 1236 deselected`; all four failures were the same deliberate authority admission reached through the old test helper.
- Before the deterministic timestamp correction: `1 failed, 3575 passed, 13 skipped, 1236 deselected`; the only failure was the server timestamp `...420032...` accidentally containing banned substring `200`.

Both causes were independently reproduced and resolved by test-only changes; the final broad run is green.

## Files touched

- `backend/tests/test_layer3_connector_source_intake_pilot.py`
- `backend/tests/test_layer3_intake_successor.py`
- `backend/tests/test_layer3_connector_vertical_loop.py`
- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py`

No production, plan, campaign, documentation, manifest, `state/agent-inbox`, `bc47335c`, `forward-plan-review`, or fenced-worktree file was edited. Ambient pre-existing `?? .omc/state/sessions/` remains untracked and was excluded from both commits.

## Independent review

Three independent `gpt-5.6-sol` max reviews examined the frozen five-file candidate:

- code correctness: **APPROVE**, 0 findings
- test/acceptance adequacy: **APPROVE**, no blocking gaps
- authority/governance/fence compliance: **APPROVE**, no critical or major defect

## Commits and handoff state

Branch: `codex/dual-live-plan`

- `890f5fc75ba1f85bdc84f9c4fbcd5e777fac3ee5` — `test(layer3): split B1a successor coverage`
- `2111c72fd6dd84e6524bf55609a5f3ed5005dbcf` — `test(sec-xbrl): harden receipt redaction scan`

Tracked worktree and index are clean. No AI trailers. No fetch, network acquisition, push, PR, merge, external reseal, or live-runtime authority action was performed.

## Adversarial verification (Fable, 2026-07-30) — B1A-OPTION2-SOUND
No coverage laundering. Independent AST reconstruction (location-stripped ast.dump, per-fn sha256):
all 9 successor tests IDENTICAL to their 8ec90984 predecessors; all 13 restored pilot tests
byte-identical to sealed13 by blob identity; old22 − sealed13 = exactly the 9 successor tests (zero
overlap/missing/extra). Seal assertion at vertical_loop.py:2767 provably FIRED against the restored
bytes (seven sealed instruments present → EARLY_EXTERNAL_SEAL_RECEIPTS armed, not vacuous). Both
"test-only" fixes verified genuinely test-only: StaticPool (canonical sqlite fresh-DB-per-connection
fix, production admission untouched) and — critically — the sec-xbrl REDACTION change STRENGTHENED
(exact-equality assert on recorded_at + fixed "200"-containing timestamp pins the flake permanently;
banned-substring set + _LONG_HEX_RUN unchanged; nothing loosened). Touched surface reproduced: 131
passed exit 0. Scope confirmed: seal constant untouched, successor self-contained (zero pilot-module
import), 5 test files + 1 report only, no push.
THREE MINORS (auditability, non-blocking — folded into the G1-completion dispatch):
1. Successor tests fall outside the conventional 10-file V4 gate command (V7 broad -k catches them);
   append tests/test_layer3_intake_successor.py to the V4 list.
2. _decision_basis helper in the successor dropped a dead include_connector_target param (no test
   uses it; report's "test BODIES AST-identical" claim remains precise).
3. Successor module lacks a provenance docstring citing predecessor blob 8ec90984.
