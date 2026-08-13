# M0 FREEZE VERDICT — external Codex 019faa86, focused delta re-review of f432adca

Date: 2026-07-30. **VERDICT: FREEZE-M0.** All four prior blockers closed (W1 aggregate classifier,
W2 executable fixtures, W3 ceiling semantics, W4 seal cardinality); W5 guarantee-hunt clean.
Freeze covers the M0 documentation/planning baseline ONLY — no implementation, egress, grant,
acquisition, acceptance, merge, or production authority.
source-sha256: 329e1057f0bef1235db98a271ef274e3111f3559fb0861d47a7d0d22ed77af75

---

# Focused delta re-review — `f432adca`

**Verdict: FREEZE-M0**

All four prior blockers are closed. The changed passages introduce no mechanism-exceeding guarantee. This verdict is limited to freezing the M0 documentation/planning baseline; it grants no implementation, egress, owner-grant, acquisition, acceptance, merge, or production authority.

## Evidence binding

- Reviewed HEAD: `f432adcabb9b826e001508f4571c751fb9df92dc` in `worktrees/dual-live-plan`.
- Commit delta is exactly the two authority documents plus the three named siblings; all five reviewed paths are clean.
- `git diff f432adca^ f432adca --check`: pass.
- No repository writes or prohibited execution/tooling occurred.

## Closure results

1. **W1 — PASS.** Plan lines 1448–1458 now bind an independent `aggregate_crossed := H + B > R` tally, checked after canonical header serialization, at every body boundary, and at EOF/completion. The first body-or-aggregate crossing aborts, spends/counts delivered bytes, classifies terminal oversized, and remains bounded by the disclosed allowance.

   Exact counterexample trace: with `R=1000`, `H=900`, the post-header checkpoint is invoked but does not cross (`900 + 0 > 1000` is false). After `B=200` is delivered, the next body-boundary/EOF checkpoint crosses (`900 + 200 > 1000` is true), aborts, and accounts 1100 bytes. Thus the original counterexample is closed. If “post-serialization check now fires” in the handoff means “returns true,” that phrase is arithmetically inaccurate; it is advisory handoff wording, not a defect in the canonical plan.

2. **W2 — PASS.** Plan lines 1207–1223 now use 99 individually legal header fields plus the terminating blank line and no longer contain the obsolete “100 individually legal header lines” fixture. The six requested fixtures are present: header-only aggregate crossing; body-within-stage-cap aggregate crossing; exact equality; body-stage-only crossing; grant allowance mismatch; and simulated `_MAXLINE`/`_MAXHEADERS` drift with a pre-send hard stop.

3. **W3 — PASS.** Campaign lines 664–676 define `max_run_bytes` as an application-delivered ceiling with one disclosed detection allowance, explicitly not a hard maximum. Lines 718–721 separately state the 5 MiB hydration cap, 64 MiB artifact BODY-STAGE cap, and grant-bound nominal run ceiling; crossing is terminal and never `fresh_live`. No surviving whole-run 64 MiB hard-cap implication was found.

4. **W4 — PASS.** The three sibling passages now condition seal cardinality on every extant run: two for a passing dual run, one after an NRC-first stop. The authority documents also explicitly encode the one-event failure path (campaign lines 982–986; plan lines 651–667 and 2871–2877). Residual literal “both connector-run seal events” wording occurs only inside the campaign-pass criteria, which already require both artifacts and both runs; the plan’s “both deterministic seal-event IDs” is likewise pass evidence for the successful dual sequence. Those are conditional dual-pass statements, not unconditional failure-path requirements.

5. **W5 — PASS.** The changed passages do not promise more than the specified mechanism. Non-blocking editorial hygiene only: `docs/program-context/02-decision-record.md` lines 1100–1101 duplicate “bind the introduction revision” around the supersession aside. The repeated clause neither changes seal cardinality nor widens authority, so it is not a freeze condition under the requested realistic/non-punitive standard.

## Re-derived SHA-256

- Plan: `2b1cb17889ce9535ee8986eb1bd0d6773197fc96fe4455b33e0a1e599a012560`
- Campaign: `fed23fed25135c63d9d98bc06e2b43ca8cdd8b67f5a15c66b977e3f8763801cd`

Mechanical self-verification passed for exact HEAD, exact five-file delta, scoped cleanliness, whitespace, required closure strings, obsolete-fixture absence, sibling conditional wording, both failure cardinalities, both hashes, and the counterexample arithmetic.

Codex conversation/session ID: `019faa86-8d5f-7a20-b107-bb71437f438e`
