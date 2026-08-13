# G2-P8 live4 owner-authorization receipt

Status: `B_OWNER_AUTHORIZED / DIRECT OWNER ACTS ISSUED / NO LEASE / NOT RUN-READY / NON-LAUNCHING`

Recorded: `2026-08-09`

Task ceiling: `B_OWNER_AUTHORIZED`

Lease observation: **NO LEASE EXISTS.** This is not terminal `NO_LEASE_ISSUED`.

This append-only receipt records the owner's direct, ordered acts against the exact live4 subject.
It does not issue a lease, place or inspect a credential value, arm egress, establish run readiness,
launch, retry, merge, clear a residual, record terminal clearance, or authorize Lane A.

## 1. Immutable subject

| Binding | Exact value |
|---|---|
| Corrected packet path | `docs/campaign-records/2026-08-08-g2-p8-live4-owner-decision-packet.md` |
| Packet content commit (C1) | `48305f1a7c84012ba15b7c98c45f866835b1d83d` |
| C1 tree / packet blob | `e418488dcb6a3dfe683cfa489271050dcd9a3ca6` / `78adb72591185c46fba85dea225ae5188e41e13d` |
| Packet canonical bytes / raw SHA-256 | `21410` / `844a0c183d795731f8dc5b25b7b8da68bc2a69ea04546d8b9678581adefa6c68` |
| Custody path | `docs/campaign-records/2026-08-08-g2-p8-live4-owner-packet-custody.md` |
| Custody commit (C2) | `c1954020b57095f954cfb6139e01ee6db2b5fdee` |
| C2 tree / custody blob | `fbed6d33feddceaf0a58957d1e2e001daef63517` / `8fc73317ca5f26dbc5f648e0e379737a7fa96581` |
| Custody canonical bytes / raw SHA-256 | `8091` / `03d6801ca7b25ad5f85a95f199901e4106c736fc6fe635e8e9d5cb0b7121e35f` |
| Packet-readiness path | `docs/campaign-records/2026-08-08-p8-readiness.md` |
| Packet-readiness commit (C3) | `834014fbcea80724193dc2cc981efeea5bc99b91` |
| C3 tree / readiness blob | `be41fec1db1bccb8cc38e23f3077b6ef9739f5c8` / `d4c24c89f1a05942218f2b541081aa0b98449e46` |
| Readiness canonical bytes / raw SHA-256 | `17309` / `70d14ae8ad92b559e246a5f02f0fa0a8a95041ea4bc84760ab67e0532e7b9ddb` |
| Lane B CI closeout path | `docs/campaign-records/2026-08-08-ci-r7-closeout.md` |
| Lane B CI closeout (R7) | `441572b5737911f8104c559f570bc0e2d6edac4d` |
| R7 tree / closeout blob | `5ace56f580440cf178f451d15a265545db37e412` / `61bcc3b4a4b9d6a5c0b718f10621028a2f046020` |
| R7 canonical bytes / raw SHA-256 | `2581` / `2ab861234263b92f91fb5654959ccbbe24166c58a854d8ee8a75bcd216772282` |
| Owner-decision preflight path | `docs/campaign-records/2026-08-09-g2-p8-live4-owner-decision-preflight.md` |
| Owner-decision preflight commit (C4) | `3a2fc5882181c6e1a7aec76a15ad97711d2753fc` |
| C4 tree / preflight blob | `3dc65289b59841c95d6ab31b6e3642a26e31da1c` / `3a246e39528c9de6fbd21d54efe701d12a4a9f3d` |
| Preflight canonical bytes / raw SHA-256 | `14727` / `2e3021ccf613eff3a218551f7c3908000624fdafd5089b4a75f25559ced79edd` |
| Branch / draft PR | `codex/dl-ci-coverage` / `#2485` |
| Authorization-time remote branch head | `3a2fc5882181c6e1a7aec76a15ad97711d2753fc` |
| Current `project6-origin/main` / PR base | `0b65b4f0b06fdbd1e34460800ef8251cebbb9307` |

C1, C2, C3, and R7 are ancestors of C4. C4's direct parent is R7 and its sole path delta is the
owner-decision preflight record. All predecessor blobs remain byte-identical at C4. The direct owner
act changes live authority; it does not rewrite any immutable predecessor.

## 2. Correction chronology and direct owner acts

The owner's earlier message contained both a non-issuance header and the three authorization lines.
That earlier message remains non-authorizing; this receipt does not relabel it retroactively.

The owner then supplied this separate direct correction and issuance:

> I withdraw the “OWNER TO ISSUE — NOT YET ISSUED” header from my prior message.
>
> Against preflight commit 3a2fc5882181c6e1a7aec76a15ad97711d2753fc and its stated
> C1/C2/C3/R7 bindings, I personally issue, in order:
>
> P5-live: discharged at run
>
> C4-i: understood; quiescence established
>
> G2-P8: AUTHORIZED

No chat timestamp is invented. The separate trusted intervals in section 3 provide conservative
receipt and completed-validation timing evidence. The second message is the operative direct
issuance. No agent chose, paraphrased, inherited, or filled an owner value.

## 3. Trusted time, cutoff, and TTL

Fresh no-cache GitHub API HTTP `Date` evidence established:

- authorization-time interval: `[2026-08-09T20:02:49Z, 2026-08-09T20:02:50Z)`;
- completed-validation interval: `[2026-08-09T20:19:33Z, 2026-08-09T20:19:34Z)`;
- owner-packet/latest-launch cutoff: `2026-08-13T14:06:52.580652Z`;
- authority expiry: `2026-08-14T14:06:52.580652Z`;
- conservative cutoff time remaining at the final interval ceiling: `323238` seconds; and
- conservative authority TTL at the final interval ceiling: `409638` seconds.

Both intervals are strictly before the cutoff, expiry remains future, and the final conservative TTL
is at least `86400` seconds. Any launch still requires a distinct immediate launch-final time/TTL
preflight; this receipt cannot be reused for that gate.

## 4. Fresh authorization-time rebind

All checks were validate-only and preserved repository, runtime, database, and live4 state.

| Check | Result | Fresh evidence |
|---|---|---|
| Immutable subject and branch | **PASS** | C1-C4/R7 commit, tree, blob, byte, raw-SHA, ancestry, and sole-delta fences rederived. Record worktree/index clean; `git diff --check` passed. |
| Draft PR and CI | **PASS** | PR `#2485` open and draft; remote head exact C4; base `0b65b4f0...`; mergeable/clean; `22/22` checks successful; no ready/merge inference. |
| Runtime checkout | **PASS** | Designated runtime `C:\p6-scratch\dl-sbfix`; detached `d781adfcaab2eb880456aef7ac49ee589105bbbe`; tree `da21ee59890e03c0245ff12f2bec5ae3ce1730a0`; index/worktree clean. |
| Frozen objects and dependencies | **PASS** | Plan blob `68f740af...`; seal blob `b8a89df2...`; designated `C:\p6-run\py312\python.exe`; interpreter `4d6f5f81...`; DLL `9a0e3435...`; wrapper `fe9ee12d...`; lock `bfbe4722...`; dependency digest `1c24c982...`; PyMuPDF `1.27.2.3`. |
| DB integrity and schema | **PASS** | Immutable/read-only; `query_only=1`; `quick_check=ok`; Alembic `0056_layer3_connector_source_intake_record`; 94 model/95 schema tables; missing `[]`; only extra `alembic_version`; DB SHA `6222a9e8...`; no sidecars or byte/mtime drift. |
| Secret-free denied-network resolution | **PASS** | Fresh isolated child; credential absent; egress `false`; sockets/DNS hard-denied after imports; exact campaign/index/grants/two deterministic bindings/reviewed source identity resolved; network attempts `[]`. |
| Campaign, grants, markers, roots | **PASS** | Campaign `ff1af01b...` / SHA `07ef4c18...` / fingerprint `3c415b6f...`; index revision `1` / SHA `e54ae4f3...`; NRC and ScienceBase identities exact; expected markers absent; expected log/manifest/seal absent; `consumed/`, `logs/`, and `log-seals/` empty; 18 live4 items, 9 files/9 directories, zero reparses. |
| Preparation and staging | **PASS** | `set-live-env.ps1` SHA `210d9910...`; fresh no-profile/noninteractive child; PSReadLine absent; credential absent before/after; exact bindings; egress `false`; no launch; live4/runtime-index/Git pre/post parity exact. |
| Prep banner classification | **PASS WITH DISCLOSURE** | The script still prints historical `G2-P8 HAS NOT BEEN GIVEN`. That conservative prep-only text predates this direct issuance and is not current authority. It cannot negate the owner act or authorize execution. |
| External quiescence | **PASS FOR OWNER AUTHORIZATION** | The direct `C4-i: understood; quiescence established` act supplies current external quiescence and acknowledges the recovery residual. A supportive executable-path census found zero matching processes, but does not independently establish global quiescence. |
| Residual and CI posture | **PASS FOR AUTHORIZATION** | R7's exact CI closure remains applicable because executable/workflow bytes are unchanged. All non-CI residuals in section 6 remain carried, not cleared. |

## 5. Owner-act disposition

| Order | Exact owner act | Result |
|---:|---|---|
| 1 | `P5-live: discharged at run` | **ISSUED** — verification-at-run election; live verification not yet performed |
| 2 | `C4-i: understood; quiescence established` | **ISSUED** — point-in-time external quiescence; recovery residual carried, not cleared |
| 3 | `G2-P8: AUTHORIZED` | **ISSUED** — exact bound live4 subject only |

All three direct acts are issued in the required order. The attained state is therefore
`B_OWNER_AUTHORIZED`. This permits consideration and separate issuance of one exact global lease; it
does not itself create that lease or any runtime capability.

## 6. Residuals carried, not cleared

1. C4-i non-atomic Phase-B durability and retained-partial-state recovery/adjudication risk.
2. C4-ii hostile native-PDF parsing in-process under Python-only spawn denial, not an OS sandbox.
3. C4-iii shared-executor HTTP credential seam.
4. Deferred `app.services.analysis` and runtime `paddleocr` / `ppocr` logger-enumeration drift.
5. L2 real-endpoint TLS/framing/timing and evidence-chain frontier.
6. The disclosed local-root clone-source trust hop.
7. Separate credential placement, egress arming, launch-final preflight, one-launch authority, and
   containment readiness remain required.
8. External producer quiescence remains point-in-time and must be freshly rebound at launch-final.

Nothing in this receipt waives, closes, accepts as harmless, or predicts the outcome of a residual.

## 7. Attained state and later gates

```text
packet_content_complete=true
custody_bound=true
packet_readiness_rows=9/9 PASS at C3
owner_decision_preflight_rows=9/9 PASS at C4
owner_fields=3/3 ISSUED
state=B_OWNER_AUTHORIZED
P5_live_runtime_verification=NOT YET PERFORMED
C4_i_residual=CARRIED_NOT_CLEARED
LEASE_STATE_OBSERVATION=NO LEASE EXISTS
B_RUN_READY=false
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

| Later act, lease, or receipt | Current status |
|---|---|
| Global lease | **ABSENT / NOT ISSUED** |
| Run-operator ACK | **ABSENT** |
| Containment-operator ACK/readiness | **ABSENT** |
| Credential placement | **BLANK / UNPERFORMED** |
| Egress arming | **BLANK / UNPERFORMED** |
| One-launch authority/reservation | **BLANK / UNSPENT / UNPERFORMED** |
| Launch-final preflight | **ABSENT / UNPERFORMED** |
| Launch-final minimum TTL `>=86400` seconds | **ABSENT / UNVERIFIED** |
| Terminal containment and actual release | **NOT APPLICABLE YET** |

The only permitted next transition is separate issuance of one exact global lease with distinct run
and containment phases, named operators, immutable subject/owner-act bindings, automatic stop, and
mandatory containment/release terms. Credential placement, egress arming, run readiness, and launch
remain later gates.

## 8. Record fence and self-identity

This receipt cannot embed its own future Git blob, containing commit, or containing tree. Its
containing commit is valid only if:

1. its direct parent is C4 `3a2fc5882181c6e1a7aec76a15ad97711d2753fc`;
2. its sole path delta is this added receipt;
3. C1, C2, C3, R7, and C4 remain byte-identical;
4. the fresh authorization-time posture in section 4 remains fully PASS;
5. the correction chronology and exact direct owner text remain unaltered;
6. strict UTF-8, no BOM, LF-only, final LF, no trailing whitespace, and `git diff --check` pass; and
7. no lease, credential, egress, launch, PR-ready, merge, clearance, or Lane A act occurs in this
   commit.

The containing commit/tree, receipt blob, and raw SHA-256 are derived after commit. No self-pinning
follow-up commit is required.

## 9. Non-claims

This receipt claims only direct owner authorization of the exact bound subject and attainment of
`B_OWNER_AUTHORIZED`. It claims no global lease; operator ACK; credential access or value; egress;
`B_RUN_READY`; launch, run, retry, or second launch; dual PASS; residual clearance; ready-for-review,
merge, main, production, terminal containment, terminal clearance, or Lane A authority. It executes
no runtime action.
