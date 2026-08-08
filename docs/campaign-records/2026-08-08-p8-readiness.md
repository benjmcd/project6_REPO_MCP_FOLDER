# G2-P8 live4 packet-readiness receipt

Status: `B_OWNER_PACKET_READY / OWNER REVIEW ONLY / NON-AUTHORIZING`

Recorded: `2026-08-08`

Task ceiling: `B_OWNER_PACKET_READY`

Lease observation: **NO LEASE EXISTS.** This is not terminal `NO_LEASE_ISSUED`.

Owner fields: **ALL BLANK.** Lane A: **LOCKED.**

This receipt records the fresh nine-row packet-readiness preflight required by the corrected owner
packet. It advances the session-local state from `B_PACKET_AUDIT / AUDIT_HOLD` to
`B_OWNER_PACKET_READY` only after its add-only commit fence is mechanically verified. It does not
fill an owner field, issue P8, create a lease, place a credential, arm egress, authorize or perform a
launch or retry, clear a residual, record terminal clearance, authorize Lane A, or grant landing or
merge authority.

## 1. Exact subject and receipt time

The HTTP `Date` header from a fresh, no-cache GitHub API request supplied a one-second-resolution
trusted receipt interval:

- trusted UTC floor: `2026-08-08T23:11:36Z`;
- trusted UTC ceiling, exclusive: `2026-08-08T23:11:37Z`;
- request-local bracket: `2026-08-08T23:11:36.7910682Z` through
  `2026-08-08T23:11:37.1510226Z`;
- GitHub `main`: `0b65b4f0b06fdbd1e34460800ef8251cebbb9307`;
- strict latest-launch / packet cutoff: `2026-08-13T14:06:52.580652Z`;
- authority expiry: `2026-08-14T14:06:52.580652Z`; and
- conservative TTL at the interval ceiling: `485715` seconds.

The entire trusted interval is strictly before the cutoff, expiry remains future, and the
conservative TTL exceeds `86400` seconds.

| Binding | Exact value |
|---|---|
| Corrected packet path | `docs/campaign-records/2026-08-08-g2-p8-live4-owner-decision-packet.md` |
| Packet content commit (C1) | `48305f1a7c84012ba15b7c98c45f866835b1d83d` |
| C1 tree | `e418488dcb6a3dfe683cfa489271050dcd9a3ca6` |
| Packet blob | `78adb72591185c46fba85dea225ae5188e41e13d` |
| Packet raw SHA-256 | `844a0c183d795731f8dc5b25b7b8da68bc2a69ea04546d8b9678581adefa6c68` |
| Custody path | `docs/campaign-records/2026-08-08-g2-p8-live4-owner-packet-custody.md` |
| Custody commit (C2) | `c1954020b57095f954cfb6139e01ee6db2b5fdee` |
| C2 tree | `fbed6d33feddceaf0a58957d1e2e001daef63517` |
| Custody blob | `8fc73317ca5f26dbc5f648e0e379737a7fa96581` |
| Custody raw SHA-256 | `03d6801ca7b25ad5f85a95f199901e4106c736fc6fe635e8e9d5cb0b7121e35f` |
| Operating-design commit / tree | `20e68d901f9f249c14dcf41428edf60da6a86208` / `67adf13aa51ffd652e54019df041f322cdb65229` |
| Operating-design blob / raw SHA-256 | `8cba0de6047ad19e2a7de5bbc6160ebb3aef7008` / `03b9dddf8b4a2a32a4f4c593f199d22c53038cd43ec79c3eade49476816aa4e2` |

C2 is the direct child of C1, its sole path delta is the added custody record, the packet blob is
unchanged across C1 and C2, and the packet worktree was clean before this receipt was added. Remote
custody or publication is not claimed.

Evidence classes used below:

- `CURRENT-REF-CHECKED`: freshly observed GitHub or local Git ref;
- `REPO-CONFIRMED`: derived from tracked code or immutable Git objects;
- `MEASURED`: produced by the stated fresh probe;
- `LOCAL-STRUCTURE-CHECKED`: bounded filesystem or process observation;
- `DIRECT-OPERATOR-ATTESTED`: supplied directly by the operator in this task and not inferred by an
  agent;
- `BRANCH-RECORD-ASSERTED`: stated by the controlling local branch record and rebound to its exact
  object; and
- `NON-CLAIM`: an explicit authority boundary.

## 2. Fresh nine-row readiness result

Every row below is bound to the C1 packet and C2 custody tuples in section 1. No historical PASS was
copied forward.

| Row | Result | Fresh evidence |
|---:|---|---|
| 1. Time, cutoff, TTL | **PASS** | `CURRENT-REF-CHECKED / MEASURED`: trusted interval `[2026-08-08T23:11:36Z, 2026-08-08T23:11:37Z)`; entire interval before cutoff; expiry future; conservative TTL `485715s >= 86400s`. |
| 2. Revision, tree, checkout | **PASS** | `MEASURED`: designated runtime `C:\p6-scratch\dl-sbfix`; detached `HEAD=d781adfcaab2eb880456aef7ac49ee589105bbbe`; tree `da21ee59890e03c0245ff12f2bec5ae3ce1730a0`; standalone `.git`; sole registered worktree; literal status `0`; index/worktree diffs exit `0`; no `extensions.worktreeConfig`; `core.longpaths=true`; `core.autocrlf=true`; wrapper CR count `0`; lock CR count `3018`. Origin is the disclosed local-root trust hop `C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER`. The runtime clone's own stale `origin/main=8fb4e5a930f56431c54b32eb0d329fe8b79d0561` has no merge-base with the bound runtime HEAD and is not the packet's verification-base ref. Fresh GitHub `main` and packet-repo `project6-origin/main` both equal `0b65b4f0b06fdbd1e34460800ef8251cebbb9307`; in the root object store, current main and the runtime diverge at merge-base `c1fcd840b421ceafb560266858a75808207f4540`, with neither ancestry direction. Main is not run authority; the reviewed source-custody function independently returned the exact runtime revision, wrapper, and interpreter identities. |
| 3. Frozen review objects | **PASS** | `REPO-CONFIRMED / MEASURED`: plan `HEAD` and working blobs both `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`; B1a seal `HEAD` and working blobs both `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`. |
| 4. Dependencies and PyMuPDF | **PASS** | `MEASURED`: direct CPython `3.12.10`, isolated `1`, `-B`, `pycache_prefix=NUL`, prefix equals base prefix; interpreter SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`; `python312.dll` SHA-256 `9a0e3435aaa680d868150f87ab3e388ad2eebc22f87e036155c7b4eda8cd2120`; no `pyvenv.cfg`; dependency digest `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d`; lock SHA-256 `bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02`; wrapper SHA-256 `fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f`; installed/imported PyMuPDF `1.27.2.3`; runtime index mtime unchanged. |
| 5. DB integrity and schema | **PASS** | `MEASURED`: SQLite `mode=ro&immutable=1` with connection-local `query_only=1`; `quick_check=ok`; exactly one Alembic row `0056_layer3_connector_source_intake_record`; 94 model tables; 95 schema tables including only extra `alembic_version`; missing model tables `[]`; DB SHA-256 `6222a9e8ac93955ac217e624d383b273c29b454b5e058806de0db4f10ed68ba7`; hash, length, mtime, and directory inventory unchanged; no WAL, SHM, or journal sidecar. |
| 6. Secret-free denied-network resolution | **PASS** | `MEASURED`: fresh shell credential absent and egress `false`; campaign, both grants, current authority with two deterministic run bindings, and reviewed runtime source identity resolved after `socket.socket`, `socket.create_connection`, and `socket.getaddrinfo` were hard-denied; network attempts `[]`; probe exit `0`. |
| 7. Campaign, grants, markers, roots | **PASS** | `MEASURED / LOCAL-STRUCTURE-CHECKED`: campaign, evidence-index, grant, canonical-fingerprint, expected-marker, revision, plan, and seal identities exact; current/archive length-plus-SHA parity true for campaign and both grants; both expected markers absent; expected log directory, manifest, and seal absent; `consumed/`, `logs/`, and `log-seals/` each have zero children; live4 has 18 items, 9 files, 9 directories, and zero reparse points. No global non-use is inferred from local structure. |
| 8. Disposable prep and staging | **PASS** | `MEASURED`: staging script SHA-256 `210d99102a40d7f78bcbcaae53c64b1a2cb6ec5b3cd99f97dc389873f4b173a9`; fresh `-NoProfile -NonInteractive` PowerShell child with PSReadLine absent before/after and credential absent; source identity exact; output states `G2-P8 HAS NOT BEEN GIVEN`, no credential, egress disabled, and stop before L5; child egress `false`; live4 snapshot `18|1f3c8c70392ec736f746919707e0c2c9e226978af8d147529befb30e308600e5` unchanged; runtime index unchanged; corrected post-child census found zero non-audit dual-live processes. |
| 9. Quiescence and residual presentation | **PASS FOR PACKET-READY ONLY** | `DIRECT-OPERATOR-ATTESTED`: the operator directly asserted control of every producer/writer able to target `C:\p6-run\live4`, present quiescence, C1/C2 binding, and no P8/run authority. `LOCAL-STRUCTURE-CHECKED`: a fresh supportive census found zero non-audit dual-live processes. C4-i/ii/iii, enumeration drift, L2 live frontier, clone-source trust hop, staging order, quiescence, and the exact CI debt are presented below and remain live. Quiescence is point-in-time and must be freshly rebound at owner decision and launch-final preflight. |

### Campaign and grant bindings

| Binding | Exact value |
|---|---|
| Campaign ID | `ff1af01b-785e-4c12-98d1-3f278039b4ea` |
| Campaign raw SHA-256 | `07ef4c182d320f43163ff039e90f885bcee8e72a30e9b819732ff358c93c25c7` |
| Campaign canonical fingerprint | `3c415b6fe717810c47c506c9de8ce9c0ec5b78e9a633db080cdce91f16915e01` |
| Evidence index revision / SHA-256 | `1` / `e54ae4f30122293bf926fad89085472325c15279d642eb712e8e3deba16e6d6b` |
| Evidence root | `C:\p6-run\live4\evidence` |
| NRC grant ID | `nrc-aps-fa4cc6c53e76` |
| NRC raw SHA-256 / canonical fingerprint | `8f0e5c778f76d0da272ba636308faeaef85693bbce95e4c9b508185ac91e79e1` / `af753222bcbf4a524f63275dde2a1563b5edb6ee9952a3edae430bf4b0b86c38` |
| NRC expected-marker SHA-256 | `1a862282ee40ecfaa30c52075584ae592486c3bc1f84ef9ad9499b18b2a68841` |
| NRC deterministic run binding | `a4111769-3868-5f0c-9c16-eeb4130594b4` |
| ScienceBase grant ID | `sciencebase-mcs-8ae20b6e8f89` |
| ScienceBase raw SHA-256 / canonical fingerprint | `b1819f62ffbf3f7f83814ec061f0e37f99937d9e5e3e2c39b81370071787dd8d` / `f9b868cef8051af749c5de74d78d46162a3cf7c25123963fb705ba302dd400ae` |
| ScienceBase expected-marker SHA-256 | `85a68fe3c92312a817a828fe4f202cd1e029bdbc9863b3735badec6240d5e371` |
| ScienceBase deterministic run binding | `622cb673-254b-56c4-9e9c-1d5c8d3908d8` |

## 3. Direct operator attestation

The operator supplied the following direct task message. No chat timestamp is invented; section 1
records the fresh trusted receipt interval separately.

> I control every producer/writer that could target C:\p6-run\live4, and they are quiescent now.
> Record this against C1 48305f1a… and C2 c1954020…; this is not P8 or run authorization.

The abbreviated C1/C2 references resolve uniquely to the full immutable tuples in section 1. This
attestation establishes the external producer-quiescence fact required for packet readiness only. It
does **not** fill the later owner field `C4-i: understood; quiescence established`; accept a residual;
issue P8; authorize credential, egress, launch, retry, or containment; or create a reusable
quiescence fact. It must be rebound at owner decision and again at launch-final preflight.

## 4. Residuals and exact CI debt presented, not cleared

The following remain live and are not waived or accepted by this receipt:

1. C4-i non-atomic Phase-B durability and retained-partial-state recovery/adjudication risk.
2. C4-ii hostile native-PDF parsing in-process under Python-only spawn denial, not an OS sandbox,
   including the PyMuPDF/MuPDF mapping and lapse trigger.
3. C4-iii shared-executor HTTP credential seam.
4. Deferred `app.services.analysis` and runtime `paddleocr` / `ppocr` logger-enumeration drift.
5. L2 real-endpoint TLS/framing/timing and evidence-chain frontier.
6. The disclosed local-root clone-source trust hop; current source identity was freshly rederived.
7. Credential-free, egress-disabled prep followed only later by distinct owner acts for credential
   placement, egress arming, launch-final preflight, and one launch.
8. Point-in-time external producer quiescence, which is non-inheritable.
9. Exact branch CI debt: `296 = 272 shard-covered + 8 explicitly excluded + 16 uncovered` with 26
   mirrored shard patterns. The guard expects zero and freshly failed as designed: `1 failed, 5
   deselected`.

The exact uncovered set is:

1. `test_arming_api.py`
2. `test_campaign_log_capture.py`
3. `test_connector_transport_loopback.py`
4. `test_dual_eval.py`
5. `test_dual_eval_acceptance.py`
6. `test_dual_live_dependencies.py`
7. `test_dual_live_p4_faults.py`
8. `test_egress_arming.py`
9. `test_egress_auth.py`
10. `test_egress_crash.py`
11. `test_egress_schema.py`
12. `test_egress_transport.py`
13. `test_nrc_fresh.py`
14. `test_nrc_strict_parse.py`
15. `test_sciencebase_fresh.py`
16. `test_sciencebase_locator_live_shape.py`

This debt does not block `B_OWNER_PACKET_READY`, but branch CI is not green and no CI-complete, PR-
ready, or merge-ready claim exists. Before any transition beyond `B_OWNER_PACKET_READY`, the exact
debt must be resolved or explicitly contained by a separately authorized policy decision bound to
this same set.

## 5. Owner fields and later acts remain blank

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

Only direct owner acts against this exact subject can change these fields. Silence, the quiescence
attestation, this receipt, prior live3 authority, or any agent-authored text cannot substitute.

## 6. State transition and next boundary

After the add-only receipt commit passes section 8, the attained state is:

```text
packet_content_complete=true
custody_bound=true
packet_readiness_rows=9/9 PASS
state=B_OWNER_PACKET_READY
owner_fields=ALL BLANK
LEASE_STATE_OBSERVATION=NO LEASE EXISTS
B_OWNER_AUTHORIZED=false
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

The only permitted next step is to stop for a direct owner decision against this exact subject, or to
take an applicable no-lease terminal `DECLINED` / `HOLD` / `EXPIRED` path. If no lease is ever issued,
that terminal path must record `NO_LEASE_ISSUED` and then `B_CLEARANCE_RECORDED` before Lane A can
begin. If the owner later supplies every exact act, a separate global lease and all later gates remain
required.

## 7. Probe correction notes

These non-load-bearing harness corrections are recorded to avoid evidence inflation:

- The first DB probe used immutable read-only mode but did not set connection-local `query_only`; it
  returned `0`. The load-bearing rerun set `PRAGMA query_only=ON`, returned `1`, and retained exact DB
  and directory parity.
- The first denied-network harness replaced `socket.socket` before importing `ssl` and failed during
  class construction before any resolver ran. The load-bearing rerun imported required modules,
  installed hard socket/DNS denial immediately before resolution, recorded zero attempts, and exited
  `0`.
- The first post-prep process count included its own audit command because the command contained the
  search string. The corrected separate census excluded its own PID and found zero dual-live
  processes.
- An unavailable PowerShell byte-array extension was replaced with exact length-plus-SHA comparison;
  all three current/archive pairs matched.

None of these failed harness attempts placed a credential, armed egress, launched a runner, wrote the
database, seeded state, migrated state, modified Git, or changed the live4 snapshot.

## 8. Add-only receipt acceptance criteria

This readiness receipt is valid only if all of the following pass after commit:

1. its containing commit's parent is exactly C2
   `c1954020b57095f954cfb6139e01ee6db2b5fdee`;
2. the commit adds only
   `docs/campaign-records/2026-08-08-p8-readiness.md`;
3. the packet and custody blobs remain exactly `78adb72591185c46fba85dea225ae5188e41e13d`
   and `8fc73317ca5f26dbc5f648e0e379737a7fa96581`;
4. the committed receipt is strict UTF-8 without BOM, LF-only, has a final LF, has no trailing
   whitespace, and passes `git diff --check`;
5. all nine rows remain PASS at commit verification and live4 remains structurally unconsumed;
6. all three direct owner fields and all three later owner acts remain blank or unperformed; and
7. no P8, credential, egress, lease, launch, retry, residual clearance, CI-green, PR, merge, main,
   production, Lane A, terminal-clearance, or remote-publication authority is claimed or performed.

The receipt cannot embed its own future Git identity without changing itself. Its containing commit,
tree, blob, raw SHA-256, bytes, and line-ending facts are therefore derived and reported after the
add-only commit; no self-pinning follow-up commit is required.

## 9. Explicit nonclaims

This receipt claims only current `B_OWNER_PACKET_READY` attainment after section 8 passes. It claims
no `B_OWNER_AUTHORIZED`; P8; owner residual acceptance; credential placement; egress authority;
lease; run readiness; launch, run, retry, or second launch; dual PASS; durable quiescence; exact-branch
CI success; PR readiness; merge authority; main landing; production readiness; terminal disposition;
`NO_LEASE_ISSUED`; `B_CLEARANCE_RECORDED`; remote custody; or Lane A authority. It executes,
authorizes, waives, clears, and predicts nothing beyond the packet-ready state.
