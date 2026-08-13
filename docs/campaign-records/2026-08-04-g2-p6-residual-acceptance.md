# G2-P6 residual acceptance — owner disposition (2026-08-04)

> **Status: OWNER ACCEPTANCE GIVEN. G2-P6 CLOSED.** This is the P6 instrument. It is to be landed at
> `docs/campaign-records/2026-08-04-g2-p6-residual-acceptance.md` so that G2-P8's "confirm P1-P7 closed"
> has an on-disk artifact and the G2-P3 record's `OWNER-DECISION-REQUIRED-AT-P6` row has an on-disk
> resolution; the chat/memory record is the corroborating private trail, not the instrument.
> Redaction posture: operator-identifying absolute paths / hostname given as neutral placeholders
> (omission only, never false).

## Authority and scope

- Branch `codex/dual-live-plan` in the dual-live worktree; authority commit `7d6d3e72`.
- Binding gate: `docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md`, prerequisite G2-P6 at
  `:57-58`.
- Frozen plan blob `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`: **not edited by this record.**
- B1a seal constant `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`: **not edited.**
- Offline only, under C3 PREP-ONLY: no push of substrate change, no live connector request, no credential
  created or handled, no grant or campaign authority, no egress arming.
- Substrate certification chain: **G1-PASS-WITH-CONDITIONS at `b743aaae`**, C1 discharged at `dbb87740`
  (G1 fully certified; **C2/C3/C4 remain governing** — `verdict:103-104`); `cf57de58` is the condition-1
  certification and serves as the **C2 verdict-binding anchor and the G2-P8 drift-check target**
  (`verdict:30-32`, `:60-62`); `590a04c2` is the G2-prep adversarial verdict / C2 delta PASS. The Task-8
  A-scoped result, where cited at all, is **ACCEPT-WITH-CONDITIONS at `d4159ff8`** — never a bare PASS
  (`verdict:167-171`).

## The act

I accept the residuals named below for the G2 live acquisition run on the elected host — an eligible
operator workstation (identity redacted), CPython 3.12.10, eligibility measured through a curated
non-OneDrive scratch venv. This is the acceptance G2-P6 reserves to the owner. It authorizes nothing
else.

### Residual 1 — hostile-native-PDF in-process parse — ACCEPTED

The live-fetched **untrusted** NRC ADAMS PDF (one artifact, selected by the owner; selection provenance
is context, not a containment property) is parsed by PyMuPDF **in-process, with no OS sandbox**, only
inside the Phase-B process. Call chain, code-established: `dual_live_runtime.py:6277-6280`
(`_prepare_owned_phase_b` → `bind_strict_nrc_phase_b_linkage`; the `nrc_strict_parse` action receipt is
recorded separately at `:6284-6292`) → `nrc_aps_phase_b_linkage.py:1583`/`:1829` →
`nrc_aps_strict_parse.parse_admitted_blob_strict:99-140` → `nrc_aps_document_processing.process_document`
(which imports `fitz`).

**What is actually bound.** The Phase-B child's environment is secret-free by construction: the phase_b
mapping omits `NRC_ADAMS_APS_SUBSCRIPTION_KEY` and forces `CONNECTOR_LIVE_EGRESS_ENABLED` and
`CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE` to `"false"` (`dual_live_runtime.py:5315-5328`), validated
fail-closed before work (`:5661-5671`), after authority-clear has asserted `all_required_absent`
(`:4321-4398`, per `verdict:78-80`). Python-level network and subprocess denial is comprehensive at the
Python layer: the owned child rebinds `socket.socket`/`create_connection`/`getaddrinfo`/`gethostbyname*`/
`getnameinfo`, `http.client.HTTPConnection.request`, `urllib.request.urlopen`, `requests.request`,
`requests.sessions.Session.request` and the four `subprocess` entries to a deny guard
(`tools/dual_live_run.py:497-515`, `:522-539`, `:792-793`), the parser additionally denies
`subprocess.Popen` and `os.system/startfile/spawn*/exec*` (`nrc_aps_strict_parse.py:70-82`), and
Phase-B connector/transport entry points are guarded (`dual_live_runtime.py:5674-5712`). The
evidence-integrity chain is unchanged: exact-registry `INDETERMINATE > FAIL > PASS`, exceptions →
INDETERMINATE, read-only DB custody, cross-domain DB↔file parity, gate re-derives the aggregate
(`verdict:81-85`).

**What is NOT bound — stated as the accepted bound, not as a hedge.** All of the above is
**Python-level, not OS-level**, and none of it binds native code executing inside the parser. The
substrate says so itself: spawn denial "is a Python process-level guard, not an OS sandbox", and the
profile's RSS/CPU/wall-clock ceilings "fail at the next checkpoint; they cannot preempt one blocking
native call in flight" (`nrc_aps_strict_parse.py:3-5`, ceilings at `:20-30`); the child-creation gate
"does not claim to contain malicious same-process code that cached a prior Popen/native entry point or
invokes CreateProcess through a native extension" (`dual_live_windows.py:1941-1943`); the Win32 job
object sets only `KILL_ON_JOB_CLOSE` with breakaway forbidden (`dual_live_windows.py:3728-3749`) — it
bounds child **lifetime**, not child creation or child action.

**ACCEPTED CONSEQUENCE BOUND:** arbitrary code execution under **the operator's own account** on the
elected host for the duration of the Phase-B parse, with native process-spawn and native network
capability unconstrained by the Python-level guards — including possible off-host effects, which are
not ruled out — and read reach over the campaign/evidence roots and
over any credential-bearing configuration present on disk in that account during the campaign window.
Contained only by: job-object kill-on-close, the absence of a subscription key or grant/campaign
authority in the Phase-B child's environment, the absence of any long-lived credentialed process, and
the evidence chain's refusal to emit a false PASS. This is the program's standing non-claim, restated
rather than newly conceded: the design "does not claim protection if an attacker controls ... the
Windows account that owns the evidence process" (`docs/dual-live-postrun-evidence-design.md:146-151`)
and is "not protection against compromise of the owning Windows account" (`:626-628`); the carried
non-claim list includes "no protection against a hostile local account".

**STRUCTURALLY UNEXERCISED OFFLINE.** The containment above is asserted by construction and has never
been exercised against a real hostile PDF; C4 classifies this residual as **live-manifesting**
(`verdict:36-40`). I am accepting an unexercised bound, knowingly.

**Accepted trade on the elected mitigations.** Quiescing OneDrive/AV for the run improves
file-interference quietness but removes the host's last non-Python mitigation for exactly this residual.
That trade is accepted. The clause's **live-run evidence-root quietness remains OPEN** and is not
established by the offline measurement (`2026-08-03-g2-p1-host-eligibility.md:83-87`).

### Residual 2 — single-fsync buffered-evidence window — ACCEPTED as a forensic-replay cost

Stated in its own terms. Campaign-log writers fsync **only on explicit flush**: `flush()` performs
`raw.flush()` + `os.fsync()` + an `fstat` state capture (`connector_campaign_log_capture.py:189-193` —
the module's only fsync), and any subsequent `write()` clears that flushed state (`:181-187`). Content
written but not yet flushed is therefore process-buffered and is lost on abrupt termination. The cost is
**evidence completeness / forensic replay**, not availability.

**No false-PASS impact — derived, not assumed.** `close()` marks a writer `_closed_clean` only if the
last captured flush state still matches at close (`:206-223`), and campaign closeout **fails closed**
unless every session-owned writer was explicitly flushed and cleanly closed —
`connector_campaign_log_writer_not_final`, "Every session-owned writer must be explicitly flushed and
closed" (`:1466-1473`). A run that dies inside the buffered window therefore produces no valid closeout
and no seal, and the evaluator's fail-closed aggregation and cross-domain parity resolve it to
FAIL/INDETERMINATE (`verdict:81-85`). Accepted on that basis.

Noted for honesty: no record defines or measures this residual — the phrase occurs in the corpus only at
`verdict:58` and `:94`. The mechanism and the fail-closed derivation above are stated here so the
acceptance names something concrete.

### Residual 3 — pymupdf 1.27.2.3 / MuPDF C-core advisory set — ACCEPTED AS INDETERMINATE RESIDUAL

Explicitly **NOT waived, NOT cleared**. What is being accepted: a set of **25 GHSA entries under the
distinct "MuPDF" package entity (the C library), with stated severities spanning Low to Critical**, whose
applicability to this pinned build **could not be established by any GET-only source** — several stated
ranges ("through 1.27.0", "1.23.0 through 1.27.0", "up to 1.28.0") numerically overlap the 1.27.x/1.28.x
space, but MuPDF-the-C-library and PyMuPDF-the-binding are versioned independently and no queried source
states which core build `pymupdf==1.27.2.3` embeds (`2026-08-02-g2-p3-advisory-sweep.md:546-561`,
`:581-584`). The one advisory scoped to the Python binding (GHSA-cxqh-p2w9-fmr7 / CVE-2026-3029) is NOT
AFFECTED at the pin (`:531-545`). The indeterminacy rides the same Phase-B containment — and the same
stated bound — as residual 1.

**Re-open trigger.** If the embedded MuPDF core version is later resolved and falls inside a published
affected range, this acceptance **lapses** and returns to owner decision before any further live run.

**Aggregate freshness, disposed.** Rows 1-6 returned zero applicable advisories (NONE-REQUIRED). The
freshness gap is accepted for this run: certifi 2026.6.17 (at least 1 release / ~5 weeks behind),
charset-normalizer 3.4.7 (2 releases behind), pymupdf 1.27.2.3 (at least 1 minor behind)
(`advisory-sweep:132`, `:134`, `:584-586`).

## C4 carriage — disposition map

C4 requires all three named residuals "discharged or owner-accepted, never silently dropped"
(`verdict:36-40`):

- **C4-i** (Phase-B non-atomic durability + deterministic campaign_id poisoning forcing real
  re-acquisition on retry, `verdict:36-40`) — **DISCHARGED by P4
  evidence**, not accepted here: 22 real killed children at 22 durable commit boundaries, "every partial
  FAIL/INDETERMINATE never PASS", independently reproduced (`2026-08-02-g2-prep-report.md:6-10`,
  `:47-56`, `:187-190`). Its disclosed recovery limits are **outside this acceptance and remain
  undisposed**: interrupted poison publication can leave a stage-only artifact and interrupted archival a
  partial no-overwrite archive, both retained and requiring explicit operator adjudication (`:68`);
  producer quiescence is a mandatory external operator prerequisite the tool does not enforce or prove
  (`:65`); and there is **no interrupted-ARCHIVE test** — that path is design-bounded and disclosed only
  (`:197-198`).
- **C4-ii** (hostile-native-PDF in-process parse), together with the G2-P3 CVE result — **OWNER-ACCEPTED
  here** (residuals 1 and 3).
- **C4-iii** (shared-executor HTTP credential seam) — **NOT accepted here; substantially contained, not
  yet fully discharged.** The C1 sweep UPGRADED it from "acceptance-only": the subscription key is
  cryptographically pinned to `adams-api.nrc.gov:443` at PHYSICAL send via a header allow-list, with
  audience equality, and G2-P5's route-disable stands as belt-and-suspenders (`verdict:88-92`). The P5
  offline half is complete — route CLI-only with a deterministic 409 before any side effect, plus the
  written safety-net statement (`2026-08-02-g2-prep-report.md:11-13`). The **P5 live-host half — the
  operational verification that the key and the grant/campaign files exist only in the short-lived
  acquisition child and never in a long-lived FastAPI process (`verdict:53-56`) — is still owed**, so
  C4-iii's discharge completes at P5, not here, and is not claimed here.

## Non-claims

- This does **not** authorize the live run. G2-P8 remains a separate explicit owner act, with its own
  drift check (`verdict:60-62`).
- This creates, requests, and handles **no credential**, and arms no egress. C3 PREP-ONLY holds until P8.
- The frozen plan blob `68f740af…` and the B1a seal `b8a89df2…` are **not edited** by this record.
- This does **not** close G2-P3. It disposes P3's row-7 finding and the aggregate freshness gap; P3's
  attestation "accepts nothing, waives nothing, and closes nothing" by itself
  (`advisory-sweep:3-7`), it is "not a security clearance for the live run" (`:593-594`), and the
  **child-env half of the extras sub-clause is still owed**, carried on the P1 §5 checklist (`:74-77`,
  `:592-593`; `2026-08-02-g2-p1-host-provisioning.md:144-146`).
- The eligibility digest `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d`
  (`2026-08-03-g2-p1-host-eligibility.md:53`) is cited as the P1 **offline eligibility measurement**
  context, not as a predicate of this acceptance. It **binds the declared lock content** — the payload
  embeds `lock_sha256` and the verifier fails closed unless `backend/requirements.lock.txt` hashes to
  `_LOCK_SHA256` (`dual_live_dependencies.py:24`, `:360-361`, `:391-397`), and that lock pins
  `pymupdf==1.27.2.3` (`requirements.lock.txt:2160`) — but it **does not verify the installed PyMuPDF
  distribution**: only the six named distributions are RECORD-verified (`:27-32`, `:368-390`),
  `backend/requirements.txt:19` declares only `PyMuPDF>=1.24`, and no runtime check asserts the installed
  version. The digest is also import-root-only, not a full wheel-content binding, and is
  win_amd64/cp312-specific (`eligibility:72-81`). The curated six-pin venv is the eligibility
  **measurement** environment (`pip freeze` = exactly those six — `eligibility:22-31`); it is not the
  Phase-B run environment, and the digest is invariant across any environment carrying the six exact pins
  (manifest paths are canonicalized relative to the import root — `dual_live_dependencies.py:180`,
  `:243-275`).

## Standing of the other prerequisites (unchanged by this act)

**G2-P6 is CLOSED.** The consequence bound stated for residual 1 is stated for the elected host; a change
of host does not reopen P6, but requires restatement of that bound and re-satisfaction of P1/P2 on their
own terms.

Textual tension, met head-on. `2026-08-02-g2-p1-host-provisioning.md:149-151` states that until P1's
evidence is appended to that record, "G2-P1 is OPEN and every downstream prerequisite — G2-P2 in
particular, which requires reproduction **on that host** — is unreachable", and the P1 eligibility
evidence in fact landed as a separate file rather than as an appended section of that designated target.
Read at maximum strictness that sentence would bar this closure. It is read here as scoped to the
**host-dependent** prerequisites it names and reasons from: G2-P6's gate text carries no host predicate
(`verdict:57-58`), it is an owner act rather than a host measurement, and the program has already
produced prerequisite work out of order under exactly that reading — the G2-P3 attestation was produced
and landed while recording that "G2-P1 and G2-P2 remain OPEN and BLOCKING"
(`2026-08-02-g2-p3-advisory-sweep.md:36-37`), as were P4, the P5 offline half, and P9. If a later reader
rejects that reading, the consequence is bounded rather than silent: G2-P8's own "confirm P1-P7 closed"
test re-checks P6 at authorization time, and this record exists on disk to be re-checked against.

The gate is ordered and all-BLOCKING except P9 (`verdict:42`). This act closes P6 only. **G2-P1 remains
OPEN** (`eligibility:5-6`, `:93-97`); **G2-P2 remains formally OPEN pending owner acceptance of the P1
eligibility record** (`2026-08-03-g2-p2-offline-evaluator-bar.md:14-18`; `verdict:199-202`); **G2-P3 is
not closed** (above); the P5 live-host half is outstanding. Owner acceptance of the P1 eligibility record
is **not** effected here and is still owed.

## Carried to G2-P8 (checklist additions from this act)

1. Assert the **installed** PyMuPDF version in the actual Phase-B environment immediately before the run;
   confirm it is `1.27.2.3`. If it is not, residual 3's factual predicate fails and this acceptance does
   not cover the loaded build.
2. Confirm the run-configured `DUAL_LIVE_DEPENDENCY_SET_SHA256` matches the landed P1 record (D6
   semantics: determinism + match-to-landed-record).
3. Confirm the C4-i recovery caveats above are understood as undisposed operator-adjudication paths, and
   that producer quiescence has been established externally.
4. Confirm the C4-iii live-host half (P5) is discharged before authorization — it is not discharged by
   this record.
5. Re-run the drift check vs `cf57de58` and byte-verify `68f740af…` / `b8a89df2…`, and confirm P1-P7
   closed — including this P6 record on disk.

## DECISION CONTEXT

Owner elected option **(a) accept-all-three-with-containment** over:

- **(b) upgrade pymupdf to 1.28.0.** PyMuPDF is not one of the six RECORD-verified pins
  (`advisory-sweep:58-63`), so the cost is not a six-pin change: the upgrade edits
  `backend/requirements.lock.txt`, which changes the hash the verifier enforces, which requires editing
  the `_LOCK_SHA256` source constant (`dual_live_dependencies.py:24`, `:360-361`) — a substrate change
  triggering a C2 targeted delta review, a re-derived eligibility digest (`lock_sha256` is in the digest
  payload, `:391-397`), and re-attestation. Marginal on the merits: 1.28.0 also falls inside some stated
  MuPDF core ranges (`advisory-sweep:551-553`).
- **(c) demand a resolved MuPDF-core mapping.** Plausibly unresolvable from GET-only sources
  (`advisory-sweep:555-561`) — a stall, not a resolution.

Prior owner elections this session: **HOST = (a)** the elected operator workstation with a curated venv,
with mandatory mitigations (campaign runs from a non-OneDrive detached checkout of `7d6d3e72`;
OneDrive/AV quiesced — see the accepted trade under residual 1). **D6 = (a)** digest acceptance =
determinism + match-to-landed-record, verified in the P8 checklist.

Prep-1 / Prep-2, 2026-08-04, both green (read-only / offline, zero egress): remote == worktree ==
`7d6d3e72`; frozen blob `68f740af` exact at HEAD; seal `b8a89df2` present; `cf57de58` and `590a04c2` both
ancestors. Four commits have landed since the `590a04c2` C2 delta review — `d1b2be27`, `7ab61510`,
`b1486887`, `7d6d3e72` — **all docs-only**, therefore inside C2's G2-prereq carve-out (`verdict:30-32`);
this is stated precisely rather than as "zero drift", because a P8 reader must be able to tell "no
substrate change" from "no commits". Verifier re-run **PASS x2** in the curated venv with the digest
byte-identical to the landed P1 record, corroborating the two-party determinism recorded at
`eligibility:54-56`.

## Evidence basis (read-only)

Dual-live worktree at `7d6d3e72`. `docs/campaign-records/`: `2026-08-02-g1-grouped-gate-verdict.md`
(binding gate: C4 at `:36-40`, P1-P9 ladder at `:42-65`, P6 at `:57-58`, C1 sweep at `:67-104`, C4
upgrades at `:88-94`, Task-8 claim form at `:167-171`, standing at `:199-202`);
`2026-08-02-g2-p1-host-provisioning.md`; `2026-08-03-g2-p1-host-eligibility.md`;
`2026-08-03-g2-p2-offline-evaluator-bar.md`; `2026-08-02-g2-p3-advisory-sweep.md` (landed at
`b1486887`); `2026-08-02-g2-prep-report.md`. Frozen plan `docs/superpowers/plans/2026-07-29-dual-live-proof.md`
(blob `68f740af`). Design non-claims: `docs/dual-live-postrun-evidence-design.md:146-151`, `:626-628`.
Source: `backend/app/services/nrc_aps_strict_parse.py`, `dual_live_windows.py`, `dual_live_runtime.py`,
`dual_live_dependencies.py`, `connector_campaign_log_capture.py`, `nrc_aps_phase_b_linkage.py`;
`tools/dual_live_run.py`. All git usage read-only (`log`, `rev-parse`, `rev-list`, `merge-base
--is-ancestor`, `show`, `diff --name-only`, `for-each-ref`); no scripts run; no file written or edited by
this adjudication.

## Dated append — 2026-08-05: code landing at e53955d2 (residuals unaffected)

This section is append-only; no line above is edited.

**Why appended.** The owned-child logger-topology-freeze defect was found and fixed at commit
`e53955d29c9ff3efcf17316d499f1aa6a64b58ae`. Two consequences bear on this record.

**1. The three accepted residuals are untouched by that fix.** The patch adds a module-preload call
before the logger freeze and changes nothing else. It does not touch the PDF parser, the fsync/
buffered-evidence path, or the pymupdf pin. Residual 1 (hostile-native-PDF in-process parse),
residual 2 (single-fsync buffered-evidence window), and residual 3 (pymupdf / MuPDF-core advisory
mapping, accepted as INDETERMINATE) therefore stand exactly as accepted on 2026-08-04, with the same
bounds and the same lapse trigger. This append re-affirms them; it does not re-adjudicate them.

**2. The "docs-only" statement in DECISION CONTEXT is now non-exhaustive.** That paragraph enumerated
four named commits since the C2 delta review and observed they were all docs-only. Those four commits
remain docs-only and the sentence stays true of them; it is no longer an exhaustive account of the
branch, because `e53955d2` is a **code** change. It was reviewed under a C2 targeted delta review
(verdict `C2-DELTA-SOUND`, recorded at `2026-08-05-c2-targeted-delta-review.md`), read under owner
ruling D6=(a) as inside the G2-prereq carve-out. A P8 reader must take the drift disclosure from that
record, not from the enumeration above.

**Authority note.** The authority set in force when this record was written has been retired and
regenerated against the landed revision (`2026-08-05-authority-regeneration.md`). The pymupdf residual
disposition at P6 is unaffected: the pin did not change.

**Still not authorized.** G2-P8 remains a separate explicit owner act; it cannot be inherited, and the
drift check it requires now has a real, non-docs delta to disclose.
