# M0 range review 2 — external Codex 019faa86, range 356eff2e..1bfce554

Date: 2026-07-29. VERDICT: DO-NOT-FREEZE, narrowly — X1 (arming predicate) PASS, X3 (parser lane) PASS,
X2 one blocking defect: 32 KiB header bound unenforceable at the post-parse adapter seam. Prescribed:
correct X2 header-bound/owner-budget semantics, re-review accounting delta + guarantee-hunt.
source-sha256: c64bfb60deb5d9fb29791d513717a42bc4de76e4e0be31525d55216e184746c7

---

# Full-range re-review — dual-live M0 `356eff2e..1bfce554`

Codex session: `019faa86-8d5f-7a20-b107-bb71437f438e`

## Verdict

**DO-NOT-FREEZE**

Correction round 2 closes X1 and X3 at the design/specification level and makes most of X2 materially more honest. One authority/mechanism blocker remains: the chosen post-parse Requests-adapter seam cannot enforce the claimed `32 KiB` header portion of the `32 KiB + 64 KiB` maximum crossing-detection bound. A response with individually legal headers whose aggregate canonical serialization exceeds 32 KiB is fully parsed before that seam can reject it. Classifying the later excess as `INDETERMINATE` prevents a false campaign pass, but it does not enforce the stated owner byte boundary or make the “at most” overshoot claim true.

## Scope and identity

- **REPO-CONFIRMED:** local `project6-origin/main` is `c1fcd840b421ceafb560266858a75808207f4540`; reviewed branch/worktree HEAD is `1bfce554573649925876815838dac2ffb4b904f1`.
- **REPO-CONFIRMED:** `356eff2e..1bfce554` is a four-commit linear range: `78eb3146`, `3ed5589a`, `a0cefbd6`, `1bfce554`.
- **REPO-CONFIRMED:** the range changes only the plan, campaign record, and prior review record. `git diff --check` passes; the worktree remains clean.
- **REPO-CONFIRMED:** final identities:
  - [implementation plan](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md): 149,443 bytes; SHA-256 `e65239f303a6ac2670257d79c0dcc1ccd0a517c18abc97015e7696c6b07e2e1f`;
  - [campaign record](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/campaign-records/2026-07-29-dual-live-proof.md): 70,097 bytes; SHA-256 `e9083b4b4094954a01b1b9c1a7f36da8507e5e47dc2ed69c69538ebd5464da11`;
  - [prior review record](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/campaign-records/2026-07-29-m0-range-review-1.md): 17,532 bytes; SHA-256 `f96e04fab4e6f0c06106c0261275cf9a366849b5062cf93a6d28552704c8c1c7`.
- **LOG-ASSERTED, non-authoritative:** the handoff says two internal verifiers returned `GO-FOR-REREVIEW`; their conclusions were not used as freeze authority.
- **UNVERIFIED:** proposed implementation behavior and tests. The audit boundary prohibited Python, pytest, Alembic, Node, and npm execution.

## X1 — NRC predecessor arming predicate

**PASS — REPO-CONFIRMED.**

The plan now defines `evaluate_nrc_acquisition_success` once as the authoritative five-clause predicate and requires `create_connector_egress_arming` to invoke it in the same ScienceBase creation call before consumption-marker creation ([plan lines 955–1001](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:955)). It rederives:

1. strict `completed` finalization plus unique terminal-event/no-later-failure evidence;
2. absence of an unexpired lease;
3. ledger reservation/completion parity, ceiling compliance, and no `spent_unknown`;
4. exact one-to-one manifest-bound counter reconciliation;
5. complete in-limit `200` PDF receipt/hash equality.

The adversarial matrix falsifies every clause independently and requires zero ScienceBase marker/row/event mutation ([plan lines 810–831](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:810)). The campaign record matches and explicitly demotes wrapper ordering to flow control, not enforcement ([campaign lines 935–963](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/campaign-records/2026-07-29-dual-live-proof.md:935)). No described caller path reaches marker creation on a weaker check.

## X2 — counted-byte accounting

**FAIL — one blocking mechanism defect remains.**

What is corrected:

- **REPO-CONFIRMED:** the currency is now application-visible counted bytes: deterministic canonical status/header serialization plus body bytes delivered through the wrapped urllib3 read path before content decoding.
- **REPO-CONFIRMED:** original wire octets, transfer framing, TLS/TCP/DNS, and lower-layer buffered bytes are explicit non-claims.
- **REPO-CONFIRMED:** grant threshold, reservation arithmetic, counter, evaluator, and acceptance text use the same conceptual currency; a crossed run is never `fresh_live`.
- **REPO-CONFIRMED:** body crossing is checked at fixed 64 KiB read granularity and all delivered bytes remain spent ([plan lines 1339–1453](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:1339); [campaign lines 638–680](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/campaign-records/2026-07-29-dual-live-proof.md:638)).

Blocking defect:

- **REPO-CONFIRMED:** the plan itself says `http.client` parses the complete status/header block before the adapter sees parsed fields, then says the adapter rejects canonical status/header serialization over 32 KiB ([plan lines 1340–1350](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:1340), [1391–1402](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:1391)).
- **INFERENCE, directly corroborated by current host library source:** Requests calls `conn.urlopen(...)` and only afterward builds its response; urllib3 calls `http.client.getresponse()`, then constructs `HTTPHeaderDict` from the already parsed message. Python’s current parser permits up to 100 header lines, each individually up to 65,536 bytes. Therefore a valid parsed canonical header block can materially exceed 32 KiB before the proposed check runs.
- **CONSEQUENCE:** with a small remaining aggregate budget, the counted aggregate can cross by more than the declared 32 KiB header allowance before any body read. The evaluator’s later “counter defect/INDETERMINATE” disposition is fail-closed for acceptance, but post-hoc rejection cannot enforce the owner’s stated byte boundary. The same false bound appears in the test contract and evaluator ([plan lines 1166–1174](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:1166), [2362–2381](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:2362)).

Required closure:

1. Either enforce a total header cap before/during header parsing at a lower bounded response-parser boundary, or retract the 32 KiB maximum-overshoot claim and bind an explicit, truthful owner-authorized detection allowance into the grant and every downstream layer.
2. If `max_run_bytes` remains a hard owner maximum, reserve sufficient headroom and use a mechanism that makes actual counted bytes unable to exceed it; a post-crossing failure classification is insufficient.
3. Add an adversarial response with many individually legal headers whose aggregate canonical serialization exceeds 32 KiB, under a nearly exhausted run budget, and prove the selected semantics mechanically.

## X3 — secret-free strict parser lane

**PASS at design level — REPO-CONFIRMED; runtime UNVERIFIED.**

The edit surface is now complete and matches current direct call sites: create `nrc_aps_strict_parse.py`; modify `nrc_aps_document_processing.py`; audit-only the OCR, advanced-OCR, and advanced-table modules; add a dedicated strict-parse test file ([plan lines 1638–1651](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:1638)).

Current-source tracing confirms the plan covers the material escape hatches: the generic thirtyfold PDF allowance, hybrid OCR path lacking `ocr_enabled`, OCR exception-to-degradation conversions, Paddle/Tesseract rendering, Camelot routing, candidate-B external conversion, visual rendering, and Tesseract `subprocess.run`. The frozen profile supplies exact page, rendered-pixel, text, table, scratch, peak-RSS, wall-clock, CPU, output, and subprocess limits, with named measurement/enforcement points and honest checkpoint/OS-sandbox non-claims ([plan lines 1738–1868](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/superpowers/plans/2026-07-29-dual-live-proof.md:1738); [campaign lines 482–519](C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan/docs/campaign-records/2026-07-29-dual-live-proof.md:482)).

Nonblocking implementation clarifications worth pinning before Task 5: make the 10,000-row limit explicitly document-global across per-page `_extract_native_pdf_units` calls; specify `ru_maxrss` unit conversion; keep the strict module’s application imports lazy so both guards are installed first; describe the zero-byte scratch check as residual occupancy unless peak temp I/O is also instrumented.

## X4 — prior findings 4–7

1. **Finding 4, admission parsing wording: RESOLVED.** Architecture now carves out only the enumerated bounded acquisition-time media/shape checks; substantive/document parsing remains post-quiescence.
2. **Finding 5, campaign-close head advancement: PARTIAL, nonblocking for M0 but required before Task 11.** The record now explains ancestor invalidation, but failure handling still asserts “campaign-close head advancement” without an executable close operation. Under the stated index invariant, a successor must add a complete new campaign slice. Specify that actual owner-authorized successor operation or reword the claim as later successor/expiry retirement.
3. **Finding 6, request-fingerprint preimage: PARTIAL hardening condition.** Reservation and send use the same eight-component prose list, but there is still no named canonical helper/schema with exact field names, header ordering/duplicate rules, URL normalization, encoding, and body-absence representation. Add that before implementation.
4. **Finding 7, process count wording: OPEN editorial condition.** “At most one campaign process alive” remains inaccurate while a wrapper and one child coexist. Say “network-inert wrapper plus at most one application/runtime child.”

Additional nonblocking clarity: current connector source acquires a generic lease and mutates status before loading the envelope. The tests require strict lease acquisition to be the sole `pending -> running` transition, which should force the repair, but the implementation steps should explicitly require strict-envelope detection and the `pending` predicate before the current lease mutation.

## X5 — consistency, guarantees, posture, and gates

- **REPO-CONFIRMED:** plan and campaign agree on X1, the application-visible byte currency/non-claims, strict parser file surface/constants, process separation, state machine, ordinals, receipt continuity, and fail-closed evaluator. They also share the X2 header-bound defect rather than contradicting one another.
- **REPO-CONFIRMED:** default-off/no-authority/no-egress posture remains intact: the plan is an M0 candidate, Tasks 1–9 are offline, Task 10 sends nothing, Task 11 is separately owner-gated, validation is read-only/fail-closed on empty state, and M9 remains a separate promotion decision.
- **REPO-CONFIRMED:** campaign milestones M0–M4 and M9 are present. **UNVERIFIED/UNMAPPED:** literal gates named G0–G4 still do not appear in either changed document. If “G0–G4” means M0–M4, the posture is intact; if they are distinct canonical gates, the mapping remains absent.
- **CURRENT PRIMARY-SOURCE CONFIRMATION:** the official [NRC APS API Developer’s Guide](https://adams-search.nrc.gov/assets/APS-API-Guide.pdf) supports two endpoints, the keyed Get Document request, returned `Url`, and the `www.nrc.gov/docs/...pdf` sample shape. The current [NRC ADAMS Public Documents page](https://www.nrc.gov/reading-rm/adams) identifies APS as the latest public interface and ADAMS documents as PDFs. Neither source proves the exact live URL for `ML17123A319`; the campaign correctly leaves that empirically open and fail-closed.

## X6 — fresh-eyes result and decision debate

No additional blocking defect was found beyond X2.

**Freeze case:** round 2 makes the NRC-first grant isolation service-enforced, replaces unobservable raw-wire claims with an application-visible metric and explicit non-claims, and turns the parser lane into a concrete bounded edit/test surface. Governance remains conservative.

**Hold case:** M0 freezes an authority-sensitive executable design. A maximum crossing bound that is impossible at the named seam is not editorial: a failed campaign can still consume more counted bytes than the owner-facing contract says the mechanism permits.

**Consensus:** **DO-NOT-FREEZE**, narrowly. Correct X2’s header-bound/owner-budget semantics, retain the successful X1/X3 corrections, apply the small nonblocking clarifications above, and re-review the corrected accounting delta plus a guarantee-hunt over the final two documents.

This verdict is advisory and non-authorizing. It grants no implementation, egress, acceptance, landing, PR, merge, repeatability, or production-promotion authority. No repository/worktree file was written; no prohibited runtime or test command was run; the correction blob and agent inbox were not touched.

Goal usage: 432,061 tokens over 14m 50s.
