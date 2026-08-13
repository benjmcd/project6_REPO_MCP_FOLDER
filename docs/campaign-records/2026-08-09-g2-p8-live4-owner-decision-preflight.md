# G2-P8 live4 owner-decision preflight

Status: `B_OWNER_PACKET_READY / OWNER-DECISION PREFLIGHT PASS / AWAITING DIRECT OWNER DECISION / NON-AUTHORIZING`

Recorded: `2026-08-09`

Task ceiling: `B_OWNER_PACKET_READY`

Lease observation: **NO LEASE EXISTS.** This is not terminal `NO_LEASE_ISSUED`.

Owner fields: **ALL BLANK.** Lane A: **LOCKED.**

This append-only record refreshes the evidence required to present the exact live4 subject for a
direct owner decision. It binds the corrected packet, its companion custody record, the packet-
readiness receipt, and the Lane B CI closeout. It does not fill or relay an owner field, issue P8,
create a lease, place or inspect a credential value, arm egress, authorize or perform a launch or
retry, clear a residual, record terminal clearance, ready or merge the draft PR, or authorize Lane A.

## 1. Exact subject

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
| Lane B CI closeout / pre-record head (R7) | `441572b5737911f8104c559f570bc0e2d6edac4d` |
| R7 tree / closeout blob | `5ace56f580440cf178f451d15a265545db37e412` / `61bcc3b4a4b9d6a5c0b718f10621028a2f046020` |
| R7 canonical bytes / raw SHA-256 | `2581` / `2ab861234263b92f91fb5654959ccbbe24166c58a854d8ee8a75bcd216772282` |
| Branch / draft PR | `codex/dl-ci-coverage` / `#2485` |
| Pre-record remote branch head | `441572b5737911f8104c559f570bc0e2d6edac4d` |
| Current `project6-origin/main` / PR base | `0b65b4f0b06fdbd1e34460800ef8251cebbb9307` |

C1, C2, C3, and R7 are ancestors of the pre-record head. Their bound blobs match the corresponding
`HEAD` and working Git blobs. The packet, custody, and readiness records remain immutable historical
objects; this record does not rewrite them.

## 2. Trusted time, cutoff, and TTL

Fresh no-cache GitHub API HTTP `Date` headers supplied two one-second-resolution trusted intervals:

- initial preflight interval: `[2026-08-09T08:07:59Z, 2026-08-09T08:08:00Z)`;
- final operator-attestation receipt interval: `[2026-08-09T08:28:56Z, 2026-08-09T08:28:57Z)`;
- final request-local bracket: `2026-08-09T08:28:56.7290151Z` through
  `2026-08-09T08:28:57.0824470Z`;
- strict owner-packet/latest-launch cutoff: `2026-08-13T14:06:52.580652Z`;
- authority expiry: `2026-08-14T14:06:52.580652Z`; and
- conservative TTL at the final interval ceiling: `452275` seconds.

The entire final interval is strictly before the cutoff, expiry remains future, and conservative TTL
is at least `86400` seconds. This does not replace the distinct launch-final time/TTL preflight.

## 3. Fresh nine-row owner-decision preflight

Evidence classes:

- `CURRENT-REF-CHECKED`: freshly observed GitHub or local Git ref;
- `TRUSTED-REMOTE-TIME-CHECKED`: freshly observed no-cache remote HTTP `Date` interval;
- `REPO-CONFIRMED`: derived from tracked code or immutable Git objects;
- `MEASURED`: produced by the fresh probe described below;
- `LOCAL-STRUCTURE-CHECKED`: bounded filesystem or process observation;
- `DIRECT-OPERATOR-ATTESTED`: supplied directly by the operator in this task; and
- `NON-CLAIM`: an explicit authority boundary.

| Row | Result | Fresh evidence |
|---:|---|---|
| 1. Time, cutoff, TTL | **PASS** | `TRUSTED-REMOTE-TIME-CHECKED / MEASURED`: final trusted interval `[2026-08-09T08:28:56Z, 2026-08-09T08:28:57Z)` is wholly before cutoff; expiry is future; conservative TTL `452275s >= 86400s`. |
| 2. Revision, tree, checkout | **PASS** | `MEASURED`: designated standalone runtime `C:\p6-scratch\dl-sbfix`; detached `HEAD=d781adfcaab2eb880456aef7ac49ee589105bbbe`; tree `da21ee59890e03c0245ff12f2bec5ae3ce1730a0`; one registered worktree; literal status `0`; index/worktree diffs exit `0`; no `extensions.worktreeConfig`; `core.longpaths=true`; `core.autocrlf=true`; wrapper CR `0`; lock CR `3018`. Origin is the disclosed local-root trust hop `C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER`. Current `project6-origin/main=0b65b4f0...`; runtime/current-main merge-base `c1fcd840...`; neither ancestry direction holds; main is not run authority. Reviewed source custody returned the exact runtime, wrapper, and interpreter identities. |
| 3. Frozen review objects | **PASS** | `REPO-CONFIRMED / MEASURED`: frozen plan `HEAD` and working blobs both `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`; B1a seal `HEAD` and working blobs both `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`. |
| 4. Dependencies and PyMuPDF | **PASS** | `MEASURED`: designated interpreter `C:\p6-run\py312\python.exe`; direct CPython `3.12.10`; isolated `1`; bytecode disabled; `pycache_prefix=NUL`; no `pyvenv.cfg`; interpreter SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`; `python312.dll` SHA-256 `9a0e3435aaa680d868150f87ab3e388ad2eebc22f87e036155c7b4eda8cd2120`; dependency digest `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d`; lock SHA-256 `bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02`; wrapper SHA-256 `fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f`; installed/imported PyMuPDF `1.27.2.3`; runtime index unchanged. |
| 5. DB integrity and schema | **PASS** | `MEASURED`: SQLite `mode=ro&immutable=1`; connection-local `query_only=1`; `quick_check=ok`; exactly one Alembic row `0056_layer3_connector_source_intake_record`; 94 model tables; 95 schema tables with only extra `alembic_version`; missing model tables `[]`; DB SHA-256 `6222a9e8ac93955ac217e624d383b273c29b454b5e058806de0db4f10ed68ba7`; hash, length, mtime, directory inventory, and runtime index unchanged; no WAL, SHM, or journal. |
| 6. Secret-free denied-network resolution | **PASS** | `MEASURED`: fresh isolated child under designated `C:\p6-run\py312\python.exe`; dependency verifier returned `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d` and imported PyMuPDF `1.27.2.3`; credential absent; egress `false`; `socket.socket`, `socket.create_connection`, and `socket.getaddrinfo` hard-denied after imports; exact campaign, evidence index, both grants, two deterministic run bindings, and reviewed source identity resolved; network attempts `[]`; exit `0`. |
| 7. Campaign, grants, markers, roots | **PASS** | `MEASURED / LOCAL-STRUCTURE-CHECKED`: campaign SHA-256 `07ef4c18...` and fingerprint `3c415b6f...`; index revision `1` / SHA-256 `e54ae4f3...`; NRC grant `8f0e5c77...` / fingerprint `af753222...` / marker `1a862282...`; ScienceBase grant `b1819f62...` / fingerprint `f9b868ce...` / marker `85a68fe...`; current/archive byte parity true; both markers absent; expected log directory, manifest, and seal absent; `consumed/`, `logs/`, and `log-seals/` each have zero children; live4 has 18 items, 9 files, 9 directories, and zero reparse points. No global non-use is inferred. |
| 8. Disposable prep and staging | **PASS** | `MEASURED`: script SHA-256 `210d99102a40d7f78bcbcaae53c64b1a2cb6ec5b3cd99f97dc389873f4b173a9`; fresh Windows PowerShell `-NoProfile -NonInteractive` child; PSReadLine absent before/after; credential absent before/after; exact source/campaign/grant/index/DB/storage bindings; output states `G2-P8 HAS NOT BEEN GIVEN`, no credential, egress disabled, and `STOP before L5`; `ROW8=PASS_NO_LAUNCH`; final live4 inventory digest and runtime-index identity unchanged. |
| 9. External quiescence and residual presentation | **PASS FOR OWNER-DECISION PRESENTATION ONLY** | `DIRECT-OPERATOR-ATTESTED`: the operator directly asserted control of every producer/writer able to target `C:\p6-run\live4`, present quiescence, binding to C1/C2/C3/R7, and no P8/run authority. `LOCAL-STRUCTURE-CHECKED`: final supportive census found zero matching non-audit processes. Residuals are presented in section 5. Quiescence remains point-in-time and must be freshly rebound again at launch-final preflight. |

Two final probes required normal-host execution after the sandbox account could not exercise the
unchanged source-custody and Git checks. The unchanged normal-host probes passed. Non-load-bearing
harness corrections failed before authority-bearing success and final byte/metadata parity showed no
live4, database, runtime-index, or Git artifact mutation.

## 4. Direct operator attestation

The operator supplied this direct task message. No chat timestamp is invented; section 2 records the
fresh trusted receipt interval separately.

> I control every producer/writer that could target C:\p6-run\live4, and they are quiescent now;
> bind this to C1 48305f1a…, C2 c1954020…, C3 834014fb…, and R7 441572b5…; this is not P8 or run
> authorization.

The abbreviated identifiers map to the full immutable values in section 1. This attestation supplies
the external producer-quiescence fact for this owner-decision presentation only. It does **not** fill
`C4-i: understood; quiescence established`; accept or clear a residual; issue P8; create a lease;
authorize credential access, egress, launch, retry, or containment; or establish reusable quiescence.

## 5. Residuals presented, not accepted or cleared

The following remain live:

1. C4-i non-atomic Phase-B durability and retained-partial-state recovery/adjudication risk.
2. C4-ii hostile native-PDF parsing in-process under Python-only spawn denial, not an OS sandbox,
   including the PyMuPDF/MuPDF mapping and lapse trigger.
3. C4-iii shared-executor HTTP credential seam.
4. Deferred `app.services.analysis` and runtime `paddleocr` / `ppocr` logger-enumeration drift.
5. L2 real-endpoint TLS/framing/timing and evidence-chain frontier.
6. The disclosed local-root clone-source trust hop; current source identity was freshly rederived.
7. Credential-free, egress-disabled prep followed only later by distinct owner acts for credential
   placement, egress arming, launch-final preflight, and exactly one launch.
8. Point-in-time external producer quiescence, which remains non-inheritable.

The earlier exact 16-file CI debt is **not** an open residual. R7 records two consecutive full code-
equivalent green workflows and closes that debt. Immediately before this record was added, draft PR
`#2485` was open, draft, merge posture `CLEAN`, at exact head `441572b5...`, with all 22 checks
passing. This is a pre-record-head observation, not a claim about a future record-bearing workflow,
ready-for-review state, or merge authority.

## 6. Owner fields and later acts remain blank

| Order | Exact owner act | Current status |
|---:|---|---|
| 1 | `P5-live: discharged at run` | **BLANK — OWNER ONLY** |
| 2 | `C4-i: understood; quiescence established` | **BLANK — OWNER ONLY** |
| 3 | `G2-P8: AUTHORIZED` | **BLANK — OWNER ONLY** |

| Later owner act | Current status |
|---|---|
| Place credential out of band in the dedicated acquisition shell only | **BLANK / UNPERFORMED** |
| Arm egress only for the exact campaign/grants after authorization | **BLANK / UNPERFORMED** |
| Perform exactly one absolute-interpreter launch | **BLANK / UNPERFORMED** |

Required later gate receipts are also absent:

| Required later gate or receipt | Current status |
|---|---|
| Launch-final preflight | **ABSENT / UNPERFORMED** |
| Launch-final minimum TTL `>= 86400` seconds | **ABSENT / UNVERIFIED** |
| Containment readiness | **ABSENT / UNVERIFIED** |

Only direct owner acts against this exact subject can change the owner fields or later owner acts.
The quiescence attestation, generic direction to proceed, this record, prior authority, silence, or
agent-authored text cannot substitute. Later gate receipts must be established independently; they
are not owner fields.

## 7. State and stop boundary

```text
packet_content_complete=true
custody_bound=true
packet_readiness_rows=9/9 PASS at C3
owner_decision_preflight_rows=9/9 PASS
state=B_OWNER_PACKET_READY
owner_fields=ALL BLANK
LEASE_STATE_OBSERVATION=NO LEASE EXISTS
B_OWNER_AUTHORIZED=false
B_RUN_READY=false
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

The only permitted next step is to stop for the owner's direct decision against this exact subject,
or to take an applicable no-lease terminal `DECLINED` / `HOLD` / `EXPIRED` path. If no lease is ever
issued, the terminal path must record `NO_LEASE_ISSUED` and then `B_CLEARANCE_RECORDED` before Lane A
can begin. If the owner later supplies every exact act, a separate global lease and all later gates
remain required.

## 8. Record fence and self-identity

This record cannot embed its own future Git blob, containing commit, or containing tree without
changing the object being named. Its containing commit is valid only if:

1. its direct parent is R7 `441572b5737911f8104c559f570bc0e2d6edac4d`;
2. its sole path delta is this added record;
3. C1, C2, C3, and R7 remain byte-identical;
4. `git diff --check` passes;
5. all owner fields and later acts remain blank or unperformed; and
6. the branch remains draft and no P8, lease, credential, egress, launch, merge, or Lane A act is
   performed.

The containing commit/tree, record blob, and raw SHA-256 are derived after commit. No self-pinning
follow-up commit is required.

## 9. Non-claims

This record claims only a fresh, non-authorizing owner-decision presentation at the already-attained
`B_OWNER_PACKET_READY` state. It claims no `B_OWNER_AUTHORIZED`; owner residual acceptance; P8;
credential access; egress authority; lease; run readiness; launch, run, retry, or second launch; dual
PASS; durable quiescence; ready-for-review, merge, main, production, terminal clearance, or Lane A
authority. It executes, authorizes, waives, clears, and predicts nothing beyond presentation.
