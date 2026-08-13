# S3 AMENDMENT CLEARED — external Codex 019faa86 delta review

Date: 2026-07-30. **VERDICT: CLEARED** (was CLEARED-WITH-CONDITIONS; the one Y4 condition is now
satisfied at commit 96caa58a — the campaign-record governance restatement synced to the blob-rehash
referent). The Option-B S3 amendment is phase-correct (Y1 circularity resolved — every clause-5 input
exists in Phase A before ScienceBase arming), not-weaker (Y2 — fresh blob rehash triangulated vs ledger
+ counter, invariant 12 + Phase-B receipt intact, never-trust-projections survives), confined (Y3 —
exactly three plan hunks + decision record + campaign sync), guarantee-clean (Y5).

**CLAUSE 5 WIRING IS NOW AUTHORIZED** for the G1 continuation lane: implement evaluate_nrc_acquisition_success
clause 5 as the evaluation-time rehash of the content-addressed NRC target blob (ConnectorRunTarget.downloaded_sha256
bytes, rehashed — never a stored-column read), equal to the rederived ledger body_sha256 and the counter
decoded-body SHA-256. Amended plan sha256 ba8b41940b654e13d13316967b7a21c935dfadef3490f2660fe722cb6a39f555.

source-sha256: 046ec716618aab29408aa575880c015e718088a6e4ea49ec201055a64dcfaee5

---

# Focused S3 frozen-spec amendment review

**Verdict: CLEARED-WITH-CONDITIONS**

The Option-B amendment in the authoritative plan is phase-correct, not weaker for the acquisition-success property, and confined to the three declared plan loci. One frozen governance restatement still carries the old Phase-B receipt semantics, so the amended frozen packet is not yet internally coherent.

## Required condition

Before declaring the amendment packet cleared, synchronize `docs/campaign-records/2026-07-29-dual-live-proof.md` lines 970–972. Its current normative governance restatement still says the complete PDF's raw SHA-256 comes from “the canonical connector-target receipt.” Replace that leg with the fresh evaluation-time rehash of the content-addressed NRC target blob, never a stored-column/receipt read, equal to the rederived ledger and counter hashes. Update the S3 decision record’s consequential-edit list to disclose this additional campaign-record synchronization, then rederive any hash bound to that campaign document.

No further plan change is required by this review.

## Y1 — PASS: circularity resolved

[REPO-CONFIRMED] Every operative clause-5 input exists in Phase A before ScienceBase arming:

- Task 5 execution step 6 persists the content-addressed NRC bytes; step 7 permits terminal `completed` only after that persistence commits (plan lines 1793–1801).
- The predicate rederives the terminal ledger from committed events (995–998).
- It parses and reconciles the manifest-bound counter; the adapter flushes each record before the matching completion event commits (999–1007).
- Clause 5 rehashes the persisted blob at evaluation time and compares that fresh digest with the ledger and counter digests (1008–1018).
- The operative clause contains no receipt, linkage, or provenance dependency. Its sole receipt mention is inside the explicitly historical `[S3 delta]` annotation.

The function derives the NRC parent run server-side and takes no caller path/hash. A stored `downloaded_sha256` may identify/cross-check the target binding, but its value is not accepted as the third equality leg; the blob bytes are freshly rehashed.

## Y2 — PASS: not weaker in the relevant scope

[REASONED FROM REPO MECHANISM] For the Phase-A acquisition-success question—whether persisted raw bytes equal the transport completion evidence—a fresh blob rehash is stronger than reading a previously recorded receipt field. It triangulates three separately persisted/rederived evidence channels: raw storage bytes, the terminal ledger, and the transport counter.

This does not waive Phase-B origin continuity. Invariant 12 remains unchanged, Task 6 still rehashes the blob and mints the sole canonical origin receipt after linkage/provenance exist, and later evaluation still validates that receipt. Thus the amendment removes an impossible early dependency without weakening the later provenance/linkage proof.

The never-trust-projections rule survives: lines 977–986 retain the single authoritative predicate, server-derived identity/path, and prohibition on trusting `proof_class`, stored `ledger_terminal_hash`, or projection columns; clause 5 adds “rehashed at evaluation time—never a stored column read.”

## Y3 — PASS: delta confined

[MEASURED]

- HEAD is `ec506fe7f113d495f7596659f1659f7576fb9c13` on `codex/dual-live-plan`.
- `c7b47543..HEAD` changes the frozen plan in exactly three hunks: the falsification bullet, clause 5 plus its inline historical annotation, and `NrcAcquisitionSuccessEvidence` naming.
- The net amendment range `05d6049a..HEAD` contains only the modified plan and added S3 decision record.
- Commit `4130d44b` accidentally tracked the runtime session-state file; `ec506fe7` removes it, leaving no net tracked state delta. Its contents were not inspected.
- Because the full frozen-plan diff contains only those three hunks, invariant 12, Task 6 receipt text, execution order, and all other plan bytes are unchanged from `c7b47543`. The intervening G1 implementation commits are separate pre-amendment ancestors.

## Y4 — FAIL pending the required synchronization

[REPO-CONFIRMED] One current normative old-semantics reference survives:

- `docs/campaign-records/2026-07-29-dual-live-proof.md:960–972` calls the text a governance restatement of the authoritative predicate, then says the raw SHA-256 is “on the canonical connector-target receipt.” That recreates the Phase-B referent in the frozen companion document.

Other exact old-referent hits are historical, not operative: the prior M0 review, G1 owner-delta packet, S3 decision record, and the plan’s labeled `[S3 delta]` annotation quote/formally describe the former wording. They may remain as history.

The plan’s declaration that `evaluate_nrc_acquisition_success` is authoritative prevents this stale companion sentence from changing the implementation contract, which is why the verdict is conditional rather than rejection. But the campaign record itself says “restated here in governance form”; leaving it contradictory is not adequate for a coherent frozen pair.

## Y5 — PASS except for Y4

The new plan text makes no guarantee beyond the specified mechanism. It distinguishes a fresh byte rehash from trusting a target projection and preserves downstream receipt/provenance requirements.

[RELAYED/DOCUMENTED, NOT INDEPENDENTLY AUTHENTICATED] The decision record is candid about delegation provenance: it quotes the owner’s general delegation, states that Option B was selected by the session rather than by direct per-item owner ballot, discloses the 2-of-3 Opus lean toward A, and explains the Fable/anti-churn basis for B. That is honest governance labeling on the inspected bytes. Once the campaign synchronization is made, its consequential-edit list should be updated so its blast-radius account remains accurate.

## Re-derived hash and self-verification

Plan SHA-256:
`ba8b41940b654e13d13316967b7a21c935dfadef3490f2660fe722cb6a39f555`

Mechanical self-verification passed for exact branch/HEAD, scoped document cleanliness, exact two-file net amendment, exactly three frozen-plan hunks, absence of Phase-B dependencies from the operative clause, exactly one stale normative campaign reference, delegation disclosures, plan hash, and `git diff --check`.

`project6-origin/main = c1fcd840` is task-supplied authority and was not fetched or reverified under the read-only boundary. No repository writes, implementation, test execution, external dispatch, merge, egress, or authority promotion occurred. This verdict is advisory and non-authorizing.

Codex conversation/session ID: `019faa86-8d5f-7a20-b107-bb71437f438e`
