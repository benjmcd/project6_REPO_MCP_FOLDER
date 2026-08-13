# G2-P8 — live-run authorization (2026-08-05)

> **OWNER AUTHORIZATION GIVEN. G2-P8 CLOSED.** This is the gate proper: the explicit, separate,
> non-inheritable owner authorization of the first live credentialed acquisition, together with the
> drift check and the P1–P7 confirmation required by
> `2026-08-02-g1-grouped-gate-verdict.md:60-62`. Redaction posture: operator-identifying absolute
> paths given as neutral placeholders (omission only, never false).

## 1. The authorizing acts

The owner issued three statements in direct chat on 2026-08-05, in this order:

1. **`P5-live: discharged at run`** — see §3.
2. **`C4-i: understood; quiescence established`** — see §4.
3. **`G2-P8: AUTHORIZED`** — the authorization itself.

This authorization is specific to the campaign and revision named in §2. It is **not inheritable**:
any change of code revision voids it, as the authority set itself declares
(`continuation_after_code_change_not_authorized`).

## 2. What is authorized

One live campaign run, under the authority set regenerated against the landed fix:

| Binding | Value |
|---|---|
| code revision | `e53955d29c9ff3efcf17316d499f1aa6a64b58ae` |
| campaign id | `8fcf1699-8008-43b9-9ec2-3519807ecd18` |
| campaign fingerprint | `8b3c52d05615a137a7b131b0f3176d8fc3a3cff047a91094f1dff2e801bd42f9` |
| window | 2026-08-05T18:15:17Z → 2026-08-12T18:15:17Z |

Scope: one NRC accession and one ScienceBase target, as bound in the campaign definition and the two
grants — acquisition only, then a secret-free, network- and subprocess-denied Phase B. Nothing else is
authorized: no alternate selection, no retry, no resume, no search, no external delivery.

## 3. G2-P5 — live half, disposition

The offline half was complete (strict egress-execute HTTP route CLI-only with a deterministic `409`
before any side effect, plus the written safety-net statement). The **live half** — that the
subscription key and the current grant/campaign files exist only in the short-lived acquisition child
and never in a long-lived process — is **discharged at run**, by owner election.

Stated plainly: this is a verification the run *performs*, not one performed before it. It is
structurally enforced (the Phase-B child's environment is constructed without the key, and the
authority-clear step asserts all required values absent before Phase B begins), and the run's own
evidence records it. The owner accepts verification-at-run rather than pre-verification.

## 4. C4-i recovery caveats and producer quiescence

The owner confirms understanding that a mid-run failure can force a **real re-acquisition** on retry —
an availability and budget cost, never a false PASS — and that interrupted poison-publication or
archival can leave a retained partial state requiring explicit operator adjudication.

**Producer quiescence is an external operator precondition** which the tool does not enforce or prove.
The owner states it is established for this window.

## 5. Drift check and P1–P7 confirmation (re-derived at authorization time)

Re-derived immediately before issuing this record, not carried from earlier passes:

| Check | Result |
|---|---|
| Run checkout HEAD == authority binding | `e53955d2…` — match |
| Drift vs `cf57de58` | ancestor — pass |
| Frozen plan blob | `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f` — exact |
| B1a seal object | present |
| Run checkout tree | clean; no `extensions.worktreeConfig` |
| Dependency lock digest | `bfbe4722…` — matches the enforced constant |
| Reviewed source identity | derives `e53955d2…` |
| Dependency set digest (D6) | `1c24c982…` — matches the landed G2-P1 record |
| Installed PyMuPDF in the run environment | `1.27.2.3` |

**P1–P7:** P1 and P2 closed by owner acceptance (2026-08-04); P3 attestation landed, its row-7 finding
disposed at P6; P4 complete; **P5 offline complete, live half discharged at run per §3**; P6 closed
2026-08-04 and re-affirmed by its 2026-08-05 dated append; P7 closed by the consolidated security
sweep. **P1–P7 confirmed closed.**

The run checkout deliberately sits at `e53955d2` — the revision the authority binds — and **not** at
the branch tip, which is docs-only ahead. Running at the tip would fail the binding.

## 6. Carried residuals, unchanged by this authorization

The three C4 residuals accepted at P6 (Phase-B non-atomic durability; hostile-native-PDF in-process
parse under Python-only spawn denial, which is **not** an OS sandbox; the shared-executor HTTP
credential seam) stand as accepted, with the pymupdf/MuPDF-core mapping accepted as an **indeterminate**
residual — not waived, not cleared, and subject to its stated lapse trigger.

Two named enumeration-drift residuals remain live and are **not** closed by this authorization: the
deferred `app.services.analysis` import and the runtime `paddleocr`/`ppocr` logger creation. Either, if
reached, would refuse **fail-closed** mid-run. The owner authorizes the run in full knowledge of this.

## 7. What this authorization does not claim

It does not claim the run will succeed. The real workload has never executed end to end; the landed fix
removed one proven structural blocker, and the residuals above may surface another. It does not close
G3/M7 or anything beyond this single campaign, and it does not promote the dual-live lane beyond
experimental status. A refusal is a legitimate outcome and must be recorded as evidence, not retried
outside a fresh authority set.
