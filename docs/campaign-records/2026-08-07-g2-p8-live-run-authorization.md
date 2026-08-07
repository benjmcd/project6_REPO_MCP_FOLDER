# G2-P8 live-run authorization — ISSUED (2026-08-07)

> **ISSUED.** The owner performed all three §1 acts directly in chat on 2026-08-07T05:08:36Z. This record
> authorizes exactly ONE campaign run under the scope in §2. It does NOT contain, request, or handle
> a credential, and it does not itself launch anything — the launch is a separate owner act
> (runbook: state/agent-inbox/dl-run2-launch-runbook-2026-08-07.md).

## 1. Owner acts — all required, all presently unfilled

The owner must issue these statements directly, in this order. Relayed, inferred, inherited, agent,
or draft text does not fill a slot.

1. **P5 live half — ISSUED:** `P5-live: discharged at run`
2. **C4-i and external quiescence — ISSUED:** `C4-i: understood; quiescence established`
3. **Authorization — ISSUED:** `G2-P8: AUTHORIZED`

All three owner acts are complete. G2-P8 is ISSUED.

## 2. Exact proposed scope

| Binding | Value |
|---|---|
| Code revision | `818cc37e2f626bf8bb46056674d302df2765c7f0` |
| Campaign ID | `e5da5d33-d39f-4a91-b446-4cd902d3e1d1` |
| Campaign fingerprint | `f113ca41c54d5310075303712222ed0b3fbafa826d56a38c23858e980a96e3f2` |
| Window | `2026-08-07T03:47:17Z` through `2026-08-14T03:47:17Z` |
| Run count | Exactly one campaign launch |

The proposed scope is one NRC accession and one ScienceBase target, exactly as bound in the
campaign definition and two grants: credentialed acquisition only in Phase A, followed by a
secret-free, network-denied, and subprocess-denied Phase B. It authorizes no alternate selection,
search, external delivery, resume, recurrence, second launch, or retry.

This authorization is **not inheritable across any code-revision change**. A revision change voids
the authority set and requires a new authority set and fresh owner authorization.

## 3. P5-live and C4-i statements carried into the owner decision

The P5 live half is verification-at-run: the credential and current grant/campaign material exist
only in the short-lived Phase-A acquisition child; Phase B is constructed without the credential,
and the authority-clear transition verifies absence before Phase B. The owner elects this
discharged-at-run precedent rather than claiming it was pre-verified.

C4-i caveats remain: a mid-run failure can require real reacquisition under fresh authority, with
availability and budget cost but never a false PASS; interrupted poison publication or archival can
leave retained partial state requiring explicit operator adjudication. Producer quiescence is an
external operator precondition that the tool does not enforce or prove.

## 4. Authorization-time re-derivation

Re-derived on 2026-08-07 immediately before this draft. PASS means only that the named pre-flight
condition held; it does not issue P8 or predict run success.

| Check | Fresh result | Status |
|---|---|---|
| Run interpreter / PyMuPDF | `C:\p6-run\py312\python.exe`; importable `pymupdf 1.27.2.3` under `-I` | PASS |
| Dependency-set verifier | `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d` | PASS |
| Dependency lock | verifier accepted CRLF lock digest `bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02`; lock CR count `3018` | PASS |
| C4-i recovery caveats | carried in §3; owner acknowledged (§1.2) | ISSUED |
| P5 live half | discharged-at-run elected by owner (§1.1) | ISSUED |
| Drift base | `cf57de58` is an ancestor of branch tip `ba748cc0797fcd431e451a3b86bb7518bc72a4b4` | PASS |
| Frozen plan | checkout hash and `HEAD` blob both `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`; blob present | PASS |
| B1a seal | `backend/tests/test_layer3_connector_source_intake_pilot.py` is blob `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`; blob present | PASS |
| Run checkout / campaign binding | clean standalone `dl-run3`; no `extensions.worktreeConfig`; `HEAD == live3 code_revision == 818cc37e2f626bf8bb46056674d302df2765c7f0` | PASS |
| P1–P7 closure records | each closure basis listed in §5 exists at `ba748cc0` | PASS |
| Alembic | code has one head and live3 DB reports `0056_layer3_connector_source_intake_record` | PASS |
| SQLite/model schema | `PRAGMA quick_check = ok`; 94 model tables; 95 schema tables including `alembic_version`; none missing | PASS |
| Key-free authority resolvers | campaign definition, both grants, and `_current_authority` passed under explicit socket/DNS denial; reviewed source revision derives `818cc37e`; `consumed/`, `logs/`, and `log-seals/` remain empty | PASS |
| Runtime image custody | wrapper `fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f`; interpreter `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a` | PASS |
| Fresh fast suites | loopback `10 passed`; egress `92 passed`, serialized | PASS |
| Landed heavy suites | gate `356 passed`; evaluator `404 passed` at `818cc37e`, cited from the landing record and deliberately not re-run | LANDED EVIDENCE |
| Staging sanity | disposable child shell bound `dl-run3/live3`, printed the no-P8 banner, kept egress false, and had no credential | PASS |

## 5. P1–P7 closure bases present at `ba748cc0`

| Prerequisite | On-disk record |
|---|---|
| P1 | `docs/campaign-records/2026-08-02-g2-p1-host-provisioning.md` |
| P2 | `docs/campaign-records/2026-08-03-g2-p2-offline-evaluator-bar.md`; closure acceptance appended in `docs/campaign-records/2026-08-02-g2-p1-host-provisioning.md` |
| P3 | `docs/campaign-records/2026-08-02-g2-p3-advisory-sweep.md`; finding disposed in `docs/campaign-records/2026-08-04-g2-p6-residual-acceptance.md` |
| P4 | `docs/campaign-records/2026-08-02-g2-prep-report.md` |
| P5 | `docs/campaign-records/2026-08-02-g2-prep-report.md` (offline complete; live half OWNER-FILL) |
| P6 | `docs/campaign-records/2026-08-04-g2-p6-residual-acceptance.md` |
| P7 | `docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md` |

P1 and P2 stand closed by the recorded owner acceptance; P3's attestation is landed and its row-7
finding was disposed at P6; P4 is complete; P5's offline half is complete and its live half remains
the owner election in §1; P6 is closed; P7 was closed by the consolidated security sweep.

## 6. Residuals carried unchanged

The three accepted C4 residuals remain accepted, not cleared or waived:

1. Phase-B durability is non-atomic; interruption can retain partial state requiring adjudication.
2. Hostile native PDF parsing remains in-process under Python-only spawn denial, which is not an OS
   sandbox. The PyMuPDF/MuPDF-core mapping remains an indeterminate residual subject to its lapse
   trigger.
3. The shared-executor HTTP credential seam remains an accepted residual.

Both enumeration-drift residuals remain live and fail closed if reached:

1. deferred `app.services.analysis` import and its logger expansion;
2. runtime `paddleocr` / `ppocr` logger creation.

L2 note-grade live-frontier residuals also remain: TLS/`ssl.SSLSocket` arming-candidate shape is not
exercised by cleartext loopback; real-endpoint framing may take a different branch; real-timing
quiescence and evidence-chain behavior remain unproven. Two first-real-exercise failures have already
occurred, so a third is plausible. The design is expected to refuse rather than false-PASS on an
enumerated surprise.

## 7. Required disclosures

1. **Clone-source trust hop:** `C:\p6-scratch\dl-run3` was cloned from the **local root checkout**,
   not directly from the upstream remote. This is one trust hop beyond the authority-regeneration
   record's shallow-source statement. The purpose clone is nevertheless standalone, clean, detached
   at the bound revision, and passed the reviewed source-identity verifier.
2. **CI-completeness debt:** `backend/tests/test_connector_transport_loopback.py` matches no
   `BACKEND_SHARD_PATTERNS` entry and is not in `EXCLUDED_BACKEND_TESTS`. That debt must be paid
   before merge to main. It is unaffected by, and not discharged by, this proposed run.

## 8. Non-claims and refusal rule

This draft does not claim that the workload will succeed, does not close G3/M7, and does not promote
the lane beyond experimental status. A refusal is legitimate evidence. It must be preserved and
adjudicated; it must not be retried, resumed, or followed by a second launch outside a fresh authority
set and fresh owner authorization.


## 9. Issuance provenance + drift re-derived at authorization time

Issued by direct owner chat message on 2026-08-07T05:08:36Z (three verbatim acts in §1). This record
transcribes those acts; no agent chose, paraphrased, or inferred any owner value. Drift re-derived
at authorization time (this moment), all green:

- `project6-origin/main` = `0b65b4f0b06fdbd1e34460800ef8251cebbb9307` (unmoved; disjoint from Lane B).
- `project6-origin/codex/dual-live-plan` = `ba748cc0797fcd431e451a3b86bb7518bc72a4b4` (records tip;
  bound run revision is its ancestor `818cc37e2f626bf8bb46056674d302df2765c7f0`).
- frozen plan blob `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`
  (`docs/superpowers/plans/2026-07-29-dual-live-proof.md`) present at the bound revision.
- B1a seal blob `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` present.
- run checkout `C:\p6-scratch\dl-run3` HEAD == live3 `code_revision` ==
  `818cc37e2f626bf8bb46056674d302df2765c7f0`; clean; no `extensions.worktreeConfig`.
- campaign `e5da5d33-d39f-4a91-b446-4cd902d3e1d1`, fingerprint (authoritative, from the evidence
  index) `f113ca41c54d5310075303712222ed0b3fbafa826d56a38c23858e980a96e3f2`, window open through
  `2026-08-14T03:47:17Z`.

The credential and the launch remain owner-only, out-of-band, and are not part of this record.
