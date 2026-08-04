# G2-P1 host provisioning record — doc-drift disposition (2026-08-02)

Status: **G2-P1 OPEN.** This record opens G2-P1 and discharges exactly one of its
elements: the py3.11 documentation drift. No host has been provisioned, no dependency
set has been verified on a live host, and no live-run authority is created here. This
is not a P1 closure, a P2 reproduction, a P3 attestation, a P6 acceptance, or a P8
authorization.

## Authority and scope

- Branch `codex/dual-live-plan` in `worktrees/dual-live-plan`; starting authority
  `d1b2be2794e670488ae0617240540a26b0dadcbd`.
- Binding gate: `docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md`.
- Frozen plan blob: `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f` (freeze-time blob 5e16882f at c7b47543; sole post-freeze amendment 4130d44b). **It was not
  edited by this record.**
- B1a seal constant: `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`; not edited.
- Offline only. No push of substrate change, no live connector request, no credential,
  no grant or campaign authority, no egress arming.

Evidence labels: **REPO-CONFIRMED** (established directly by committed source or
tracked authority); **NON-CLAIM** (deliberately outside what this record proves).

## The governing clause, verbatim

`docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md:43-44`:

> - G2-P1 Provision the live host: py3.12 (dont_write_bytecode, pycache_prefix=NUL), the exact 6-package
>   requests egress stack matching pinned RECORD hashes, file-interference-quiet; fix the py3.11 doc drift.

The clause ties the documentation fix to the concrete provisioning proof. Only the
documentation half is settled below.

## 1. The code-enforced requirement (REPO-CONFIRMED)

`backend/app/services/dual_live_dependencies.py` fails closed unless all of the
following hold in the running interpreter:

- `python_version != (3, 12)` rejects (line 339). The requirement is **exactly Python
  3.12**, not a floor and not a minimum.
- `dont_write_bytecode is not True` rejects (line 340).
- `pycache_prefix != "NUL"` rejects (line 341).
- `backend/requirements.lock.txt` must hash to
  `_LOCK_SHA256 = bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02`
  (declared line 24, enforced line 361).
- Exactly six distributions at exact versions (lines 27-32), each located under the
  interpreter's own `purelib`/`platlib` roots (enforced at line 407) and verified
  against its installed RECORD digest set:

| Distribution | Pinned version | Lock line |
|---|---|---|
| certifi | 2026.6.17 | `backend/requirements.lock.txt:175` |
| chardet | 7.4.3 | `backend/requirements.lock.txt:182` |
| charset-normalizer | 3.4.7 | `backend/requirements.lock.txt:220` |
| idna | 3.18 | `backend/requirements.lock.txt:868` |
| requests | 2.34.2 | `backend/requirements.lock.txt:2414` |
| urllib3 | 2.7.0 | `backend/requirements.lock.txt:2891` |

The single entry point is `verify_dual_live_dependencies()` (line 400), invoked from
`tools/dual_live_run.py:802` and
`backend/app/services/dual_live_runtime.py:6895`. It returns a dependency-set digest
or fails closed. Its declared provenance non-claim — constant
`DEPENDENCY_PROVENANCE_NONCLAIM`, lines 18-21 — stands verbatim: "same-version package
bytes and RECORD rewritten by the owning account are not independently authenticated".

## 2. Drift site A — frozen plan line 39: SUPERSEDED BY REFERENCE, not edited

`docs/superpowers/plans/2026-07-29-dual-live-proof.md:39-40` reads, verbatim:

> **Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy, Requests, SQLite
> and PostgreSQL-compatible SQL, pytest, PowerShell, SHA-256, UUIDv5.

The interpreter clause on line 39 is **superseded by this record**. The operative
requirement is exactly Python 3.12 per section 1. The frozen file is not edited: its
blob at this record's authority commit remains
`68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`.

Rationale, stated honestly. The frozen plan is under a standing no-edit rule for
agents. The only prior post-freeze amendment, `4130d44b`, was an **in-place** edit
made under a specific owner-delegated Option-B ruling recorded in
`docs/campaign-records/2026-07-30-s3-delta-decision-record.md`; it is a precedent for
that record's structure, not for touch-avoidance. No comparable delegation exists for
a Tech-Stack version string and none is sought. A version-string drift changes no
acceptance predicate, no invariant, and no falsification bullet, so external
supersession is sufficient and is the smaller blast radius under the standing
anti-churn rule.

This is the first use of external supersession against the frozen plan in this
repository. It is deliberately confined to line 39 and creates no general licence:
any future frozen-text question that touches a predicate still requires an explicit
owner ruling.

NON-CLAIM: this section does not amend, reinterpret, weaken, or strengthen any other
line of the frozen plan.

## 3. Drift site B — task8-a-scoped plan line 9: CORRECTED IN PLACE

`docs/superpowers/plans/2026-07-31-task8-a-scoped.md:9` carried the identical
interpreter drift in its Tech-Stack line. That file is **not** frozen: its own line 15
protects only the sibling `2026-07-29-dual-live-proof.md` ("Do not edit the frozen
plan"), and the file has been edited repeatedly after creation, most recently at
`d1b2be27`. The line is normative — it states what the Task-8 implementation targets —
not a record of what ran. It is therefore corrected in place to Python 3.12, with an
inline dated marker pointing back to this record.

Without this correction, G2-P1's "fix the py3.11 doc drift" would be only half
discharged, and a future adversarial review would correctly flag the survivor.

## 4. Occurrences deliberately NOT touched

Scope of this enumeration: every tracked occurrence of the interpreter-version forms
`Python 3.11`, `3.11+`, and `py3.11`, as returned by `git grep -n "3\.11"` over
tracked `*.md` at the authority commit. Two further `3.11` substrings in tracked
markdown are not interpreter-version statements and are outside this enumeration by
construction — a section heading numbered `3.11` and a `bun` version `1.3.11`; in
non-markdown, the single hit `matplotlib==3.11.0` in the lock file is likewise out of
scope.

| Location | Why not |
|---|---|
| `docs/campaign-records/2026-07-30-g1-completion-report.md:85` | True historical measurement: "All commands used Python 3.11" describes what actually ran on 2026-07-30. Editing settled history would be a record-integrity violation. |
| `docs/campaign-records/2026-07-29-m0-range-review-3.md:82` | Historical review quoting the plan's then-current "3.11+" text. History, not a normative claim. |
| `docs/campaign-records/2026-07-31-task8-ascoped-review-and-completion.md:61` | The **origin disclosure** of this drift, item (5): "docs say py3.11 but the launcher/verifier requires py3.12." Preserved as provenance. |
| `docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md:44` | The governing clause itself ("fix the py3.11 doc drift"). It states the mandate; editing it would erase the mandate. That file receives an append-only amendment in this same landing and its existing lines are byte-untouched. |
| `docs/nrc_adams/nrc_aps_status_handoff.md:141` | Unrelated NRC ADAMS advanced-OCR environment (paddleocr, camelot-py, Ghostscript). Different subsystem. |
| `docs/layer3-backup-restore-runbook.md:106` | `python:3.11-slim` container image reference, unrelated to dual-live host eligibility. |
| `docs/local-profile-ops.md:66` | Local uvicorn profile command, unrelated subsystem. |
| `next_milestone_plans/Layer3_planning_docs/940-redacted-bridge.md:55`, `942-playwright-runtime-sync.md:21` | Playwright runtime selection, unrelated subsystem. |
| `handoff/phase_7a_closeout/*` (3 files), `archive/**` | Archived / handoff material describing a provisioned OCR validation environment. Out of scope. |

A naive grep-and-replace sweep across "Python 3.11" would have damaged the first two
rows and erased the governing clause in the fourth. It was not performed.

## 5. What G2-P1 still requires (all OPEN)

- [ ] A provisioned host running exactly Python 3.12, with `sys.dont_write_bytecode`
      true and `sys.pycache_prefix == "NUL"`.
- [ ] The six distributions installed at the exact pinned versions in section 1, under
      the interpreter's own `purelib`/`platlib` roots.
- [ ] `backend/requirements.lock.txt` on that host hashing to the pinned `_LOCK_SHA256`.
- [ ] `verify_dual_live_dependencies()` returning a dependency-set digest on that host
      rather than failing closed, with the digest recorded.
- [ ] The file-interference-quiet condition established on the evidence roots, per the
      clause.
- [ ] Confirmation, in the actual acquisition child environment, that no unpinned
      optional `requests` extras are present — the runtime half of G2-P3's third
      sub-clause, which cannot be established before a host exists.
- [ ] The resulting evidence appended to this record as a dated section.

This record is the designated append target for that provisioning evidence. Until such
a section exists, G2-P1 is OPEN and every downstream prerequisite — G2-P2 in
particular, which requires reproduction **on that host** — is unreachable.

## G2-P1 closure — owner acceptance of the eligibility evidence (dated appended section, 2026-08-04)

> Appended per this record's §5 item 7 and its own append-target designation (":147 / :149-151" above:
> evidence "appended to this record as a dated section"). Append-only: no existing line of this record is
> edited. Redaction posture: operator-identifying details as neutral placeholders (omission only, never
> false). Issued under a Fable adversarial pre-check returning GO-WITH-CONDITIONS (2026-08-04); every
> condition is discharged inside this section.

### 1. Acceptance

The owner accepts `docs/campaign-records/2026-08-03-g2-p1-host-eligibility.md` (eligibility digest
`1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d`), incorporated by reference as the
evidence body discharging §5 items 1–4 on the elected host. This appended section itself satisfies §5
item 7. **G2-P1: CLOSED-WITH-NAMED-CARRIAGE.**

Carriage rationale, stated rather than implied: §5 items 5 (file-interference quietness on the live-run
evidence roots) and 6 (child-env extras confirmation) are run-window properties — item 6 requires an
acquisition child that cannot exist before the live run. Read at maximum strictness, P1 could never close
before the run, which would make G2-P8's "confirm P1-P7 closed" unsatisfiable — a deadlock, not a
discipline. The coherent closure is: items 1–4 accepted now on landed evidence; items 5–6 carried by
name to the P8/run-window checklist (§4 below), never silently dropped.

### 2. Provenance ruling

An earlier draft of the eligibility record was written into the working tree by a read-only-instructed
verification subagent under an inaccurate landing header. It was never committed — the eligibility
file's repository history is a single commit (`7d6d3e72`) — and was preserved off-repository, removed
from the worktree, and the record re-authored by the orchestrating session under owner authorization
with accurate provenance and strictly narrower claims. The "adversarial re-derivation" party in the
eligibility record's two-party determinism claim was that same subagent; the digest is independently
corroborated by the 2026-08-04 re-run (PASS ×2, byte-identical), recorded on-disk in
`docs/campaign-records/2026-08-04-g2-p6-residual-acceptance.md` (DECISION CONTEXT). With that incident
and that corroboration disclosed here, the owner rules the eligibility record **CITABLE at G2-P8**.

### 3. Host election, restated in the P1 chain

- **HOST = (a):** the elected operator workstation (identity redacted), CPython 3.12.10, eligibility
  measured through the curated non-OneDrive scratch venv. Mandatory mitigations: the campaign runs from
  a non-OneDrive detached checkout of the then-authorized commit (re-fixed by G2-P8's drift check at
  authorization time); OneDrive/AV quiesced for the run window (that trade is accepted at the P6
  instrument, residual 1).
- **D6 = (a):** digest acceptance semantics = host-local determinism + match-to-landed-record,
  re-derived at P8 (P8 checklist item 2).
- Cross-reference for both elections: `2026-08-04-g2-p6-residual-acceptance.md`, DECISION CONTEXT.

### 4. Named carriage (re-homed explicitly)

1. **Live-run evidence-root quietness** (§5 item 5, eligibility record "open items") → P8 / run-window
   procedure.
2. **Child-env extras confirmation** (the advisory-sweep extras sub-clause, child-environment half;
   §5 item 6) → P8 / run-window, verified inside the acquisition child.
3. **Install-provenance non-claim** incl. the RECORD console-script shim-line stripping → carried under
   the verifier's `DEPENDENCY_PROVENANCE_NONCLAIM`; not cured by this closure.
4. **Actual run-environment provisioning + digest match** → P8 checklist item 2. Launch-time fail-closed
   backstop: `tools/dual_live_run.py` re-runs the verifier inside the actual run environment and refuses
   on digest mismatch (`dual_live_dependency_provenance_invalid`), with a second invocation on the
   runtime path.

### 5. Consequence for G2-P2

`docs/campaign-records/2026-08-03-g2-p2-offline-evaluator-bar.md` holds G2-P2 "formally OPEN pending
owner acceptance of the P1 eligibility record." That sole pendency is resolved by §1 above; the landed
P2 measurement (census 404/404 exit 0; five tamper campaigns PASS) now stands as reproduced on the
eligible host. **G2-P2: CLOSED by this same acceptance.**

### 6. Non-claims

This section does not close G2-P3 or G2-P5; does not authorize G2-P8 or any live run; creates, requests,
and handles no credential; arms no egress (C3 PREP-ONLY holds until P8); does not edit the frozen plan
blob `68f740af…` or the B1a seal `b8a89df2…`; and edits no existing line of this record.
