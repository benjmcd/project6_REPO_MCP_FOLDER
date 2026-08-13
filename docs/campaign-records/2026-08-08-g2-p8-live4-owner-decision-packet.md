# G2-P8 live4 owner-decision packet — PACKET AUDIT HOLD

> **FORM ONLY / OWNER FIELDS BLANK / NOT ISSUED / NOT RUN-READY / NOT MERGE-READY**
>
> Packet ceiling: `B_OWNER_PACKET_READY` only. This packet does not establish
> `B_OWNER_AUTHORIZED`, issue a lease, authorize a run, or clear any residual.
>
> Current attained state: `B_PACKET_AUDIT / AUDIT_HOLD`.
> `LEASE_STATE_OBSERVATION: NO LEASE EXISTS`; no terminal `NO_LEASE_ISSUED` receipt or
> `B_CLEARANCE_RECORDED` exists. `B_OWNER_PACKET_READY` is not attained, and Lane A remains locked.

## 1. Purpose and evidence discipline

This packet presents one narrowly bound owner decision for a possible single live4 campaign run.
It is a decision form, not an authorization record or runbook. Every owner field remains blank.
No agent may choose, fill, paraphrase, infer, inherit, or relay an owner act.

Evidence labels used here:

- **CURRENT-REF-CHECKED**: read-only Git/GitHub identity check performed at the stated time.
- **BRANCH-RECORD-ASSERTED**: statement is preserved in the named committed record; runtime evidence
  was not reopened for this packet.
- **LOCAL-STRUCTURE-CHECKED**: bounded local filesystem structure was read at the stated time; this
  is not proof of global non-use, non-tampering, or absence of concurrent activity.
- **UNVERIFIED NOW / RECHECK REQUIRED**: stale PASS is prohibited; a fresh packet-readiness result is
  mandatory and must fail closed.

## 2. Bound subject and time limits

Read-only identity check at `2026-08-08T19:23:00.218Z` found local
`project6-origin/main` and GitHub `main` equal. They must be rederived again immediately before any
owner-packet issuance or later action.

| Binding | Exact value | Evidence class |
|---|---|---|
| Verification-base `main` | `0b65b4f0b06fdbd1e34460800ef8251cebbb9307` | CURRENT-REF-CHECKED; rederive before action |
| Pre-packet evidence-base tip | `e32da9925ca52ba0391ccedb4f81a7548a2ca429` | CURRENT-REF-CHECKED; not corrected-packet identity |
| Pre-packet evidence-base tree | `50843c56a2c374426919f509c66611cca4f5c0d2` | CURRENT-REF-CHECKED; not corrected-packet identity |
| Runtime correction and live4-bound revision | `d781adfcaab2eb880456aef7ac49ee589105bbbe` | CURRENT-REF-CHECKED; runtime checkout RECHECK REQUIRED |
| Runtime revision tree | `da21ee59890e03c0245ff12f2bec5ae3ce1730a0` | CURRENT-REF-CHECKED; checkout tree RECHECK REQUIRED |
| Frozen plan blob | `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f` | CURRENT-REF-CHECKED; byte identity RECHECK REQUIRED |
| B1a seal blob | `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` | CURRENT-REF-CHECKED; byte identity RECHECK REQUIRED |
| Campaign ID | `ff1af01b-785e-4c12-98d1-3f278039b4ea` | BRANCH-RECORD-ASSERTED; local structure checked once |
| Campaign fingerprint | `3c415b6fe717810c47c506c9de8ce9c0ec5b78e9a633db080cdce91f16915e01` | BRANCH-RECORD-ASSERTED; local structure checked once |
| Authority expiry | `2026-08-14T14:06:52.580652Z` | exact bound; current validity recheck required |
| Owner-packet/latest-launch cutoff | `2026-08-13T14:06:52.580652Z` | issuance and launch require trusted UTC strictly before this instant; equality is HOLD |
| Minimum TTL at packet-readiness and launch-final preflights | `>= 86400` seconds | fresh computation at each preflight |

The pre-packet evidence-base tuple predates this packet and does not bind these packet bytes. Any
readiness receipt, owner act, or future lease must additionally bind the corrected packet's exact
path, containing commit/tree, blob, and raw SHA-256, plus the containing commit/tree, path, and blob
of `docs/campaign-records/2026-08-08-g2-p8-live4-owner-packet-custody.md`. Those identities are
derived after the relevant commits; embedding a same-file self-hash here is prohibited because it
would change the subject being bound. The companion record is custody evidence only; it supplies no
owner act, lease, credential, egress, launch, retry, landing, or merge authority.

The packet, any owner decision, and any possible launch remain on HOLD unless the packet-readiness
preflight records trusted UTC strictly earlier than the cutoff, expiry still future, and at least
86,400 seconds remaining. Any later launch requires a fresh launch-final preflight with those same
time conditions immediately before launch. Neither preflight substitutes for the other. A revision,
tree, packet, custody record, plan, seal, campaign, grant, or time-binding change requires a new bound
subject; authority is not inheritable.

## 3. Run #2 and grant posture

**BRANCH-RECORD-ASSERTED:**

- NRC run `3cad6f47-78d9-57c8-9591-462045a21b9f` completed acquisition through strict raw intake with
  terminal reason `nrc_raw_admission_completed`.
- ScienceBase run `db258901-239e-5cd8-add3-67fafce3bdb1` received HTTP 200 item hydration, then
  refused terminally at exact-locator raw admission with `sciencebase_exact_file_locator_invalid`.
- Both live3 grants are spent. No retry was authorized.
- Run #2 produced no dual PASS and no live3 log seal.

These are historical branch-record claims from
`docs/campaign-records/2026-08-07-defect3-sciencebase-locator-landing.md`, not a fresh runtime
replay or independent reopening of the evidence tree.

## 4. Live4 custody posture

At `2026-08-08T18:20:27Z`, a bounded read classified live4 as
**LOCAL-STRUCTURE-CHECKED**: expected consumption markers were absent; `consumed/`, `logs/`, and
`log-seals/` had zero children; the expected log and log-seal paths were absent; top-level
campaign/grant bytes matched their content-addressed archive copies. This proves only the observed
local structure at that instant. It does not prove global non-use, prior non-tampering, current
compatibility, absence of a concurrent producer, or continuing emptiness. Fresh recheck is required.

Authority identities to recheck byte-for-byte:

| Item | Exact identity |
|---|---|
| Campaign-definition SHA-256 | `07ef4c182d320f43163ff039e90f885bcee8e72a30e9b819732ff358c93c25c7` |
| Evidence-index SHA-256 | `e54ae4f30122293bf926fad89085472325c15279d642eb712e8e3deba16e6d6b` |
| NRC grant ID | `nrc-aps-fa4cc6c53e76` |
| NRC raw-grant SHA-256 | `8f0e5c778f76d0da272ba636308faeaef85693bbce95e4c9b508185ac91e79e1` |
| NRC canonical grant fingerprint | `af753222bcbf4a524f63275dde2a1563b5edb6ee9952a3edae430bf4b0b86c38` |
| NRC expected marker SHA-256 | `1a862282ee40ecfaa30c52075584ae592486c3bc1f84ef9ad9499b18b2a68841` |
| ScienceBase grant ID | `sciencebase-mcs-8ae20b6e8f89` |
| ScienceBase raw-grant SHA-256 | `b1819f62ffbf3f7f83814ec061f0e37f99937d9e5e3e2c39b81370071787dd8d` |
| ScienceBase canonical grant fingerprint | `f9b868cef8051af749c5de74d78d46162a3cf7c25123963fb705ba302dd400ae` |
| ScienceBase expected marker SHA-256 | `85a68fe3c92312a817a828fe4f202cd1e029bdbc9863b3735badec6240d5e371` |

The registered records worktree at `worktrees/dual-live-plan` is **not literally clean**. It has
exactly these two observed untracked tool-state files:

- `.omc/state/sessions/755e2273-2877-42e8-bf9b-06c8ab93fae3/last-tool-error-state.json`
- `.omc/state/sessions/91b270df-110e-4a84-915d-d187bcf9589e/last-tool-error-state.json`

They are local tool residue, not committed records or live4 evidence. Their presence is disclosed,
not normalized away. This packet asserts no currently valid detached runtime checkout. A fresh
designated runtime checkout path, `HEAD`, tree, Git registration/standalone status, source provenance,
configuration, EOL custody, and literal cleanliness must be recorded before issuance. Historical
claims about `C:\p6-scratch\dl-sbfix` do not substitute for that check.

## 5. CI completeness — corrected exhaustive disclosure

The earlier branch-record three-file CI disclosure is **SUPERSEDED, stale, and incomplete**. Static
exhaustive accounting at the pre-packet evidence-base tip is:

`296 tracked backend test files = 272 shard-matched + 8 justified allowlisted exclusions + 16 uncovered`.

The 16 uncovered basenames are:

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

`backend/tests/test_ci_coverage_completeness.py` requires the uncovered set to be exactly zero; that
guard is itself shard-matched and would fail with the present 16. Exact-branch CI is therefore not
green; PR readiness and merge readiness are not proven. `B_OWNER_PACKET_READY` requires exact
disclosure, not debt payment. This debt does not itself prevent placing the corrected form before the
owner, but it blocks any CI-complete or merge-ready claim.

Before any transition beyond `B_OWNER_PACKET_READY`, this exact 16-file debt must be resolved or
explicitly contained by a separately authorized policy decision bound to this exact uncovered set.
Disclosure alone is insufficient.

## 6. Residuals carried, not cleared

All previously accepted or named residuals remain governing:

1. **C4-i / recovery:** Phase-B durability is non-atomic. Interrupted poison publication or archival
   can leave retained partial state requiring explicit operator adjudication and possibly fresh
   reacquisition under fresh authority. Producer quiescence is external and not tool-proven.
2. **C4-ii / hostile PDF:** hostile native-PDF parsing remains in-process under Python-only spawn
   denial, not an OS sandbox; the PyMuPDF/MuPDF mapping and lapse trigger remain live.
3. **C4-iii / credential seam:** the shared-executor HTTP credential seam remains a carried residual;
   its live-host half is not pre-discharged by this form.
4. **Enumeration drift:** deferred `app.services.analysis` import/logger expansion and runtime
   `paddleocr`/`ppocr` logger creation remain fail-closed live-run refusal risks.
5. **L2 live frontier:** TLS/`ssl.SSLSocket` arming shape, real-endpoint framing, and real-timing
   quiescence/evidence-chain behavior remain unproven.
6. **Clone-source trust hop:** the historical purpose checkout was recorded as cloned from the local
   root rather than directly from the upstream remote. Current checkout source and reviewed-source
   identity must be rederived; the historical hop is not current proof.
7. **Staging order:** prep must remain credential-free and egress-disabled; direct owner fields come
   first; credential placement, egress arming, launch-final preflight, and one launch are later distinct
   owner acts. No step may be collapsed, reordered, inherited, or pre-recorded.
8. **Quiescence and CI:** actual producer quiescence must be freshly established externally, and the
   16-file CI debt remains open.

No statement above is a waiver, closure, compatibility claim, or prediction of success.

## 7. Owner acts — all BLANK, direct, separate, and ordered

The owner must personally issue the following exact acts, in this order, only after receiving the
fresh packet-readiness evidence. Relayed, inferred, inherited, agent-written, or draft text fills no
field.

| Order | Exact owner act | Current status |
|---:|---|---|
| 1 | `P5-live: discharged at run` | **BLANK — OWNER ONLY** |
| 2 | `C4-i: understood; quiescence established` | **BLANK — OWNER ONLY** |
| 3 | `G2-P8: AUTHORIZED` | **BLANK — OWNER ONLY** |

Credential placement, egress arming, and exactly one launch are later, separate owner acts. They are
also **BLANK / UNPERFORMED**:

| Later owner act | Current status |
|---|---|
| Place credential out of band in the dedicated acquisition shell only | **BLANK / UNPERFORMED** |
| Arm egress only for the exact campaign/grants after authorization | **BLANK / UNPERFORMED** |
| Perform exactly one absolute-interpreter launch | **BLANK / UNPERFORMED** |

## 8. Fresh packet-readiness preflight checklist

Every row is **UNVERIFIED NOW / RECHECK REQUIRED**. No historical PASS may be copied forward.
Validate-only probes must fail closed on empty state and must not seed or generate artifacts.
`B_OWNER_PACKET_READY` is not attained until every packet-readiness row passes and is bound to the
corrected packet plus its companion custody record.

1. **Time, cutoff, and TTL — UNVERIFIED NOW / RECHECK REQUIRED.** Record trusted UTC; require packet
   issuance and any later launch strictly before `2026-08-13T14:06:52.580652Z`; equality or a later
   instant is HOLD. Require expiry `2026-08-14T14:06:52.580652Z` still future; compute and record at
   least 86,400 seconds remaining at packet-readiness, then recompute immediately before any launch
   in the distinct launch-final preflight.
2. **Revision, tree, and checkout — UNVERIFIED NOW / RECHECK REQUIRED.** Record one designated runtime
   checkout's absolute path; require `HEAD=d781adfcaab2eb880456aef7ac49ee589105bbbe`,
   tree `da21ee59890e03c0245ff12f2bec5ae3ce1730a0`, no extra/different worktree registration or
   `extensions.worktreeConfig`, literal clean status, clean index/worktree, exact source provenance,
   `core.longpaths`, and expected EOL custody. Recheck current GitHub/local `main` and ancestry without
   treating main as run authority.
3. **Frozen review objects — UNVERIFIED NOW / RECHECK REQUIRED.** Require frozen plan blob
   `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f` and B1a seal blob
   `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` present and byte-exact at the bound revision.
4. **Dependencies and PyMuPDF — UNVERIFIED NOW / RECHECK REQUIRED.** Require dependency-set digest
   `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d`, lock SHA-256
   `bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02`, installed/imported
   `pymupdf 1.27.2.3`, wrapper SHA-256
   `fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f`, and interpreter SHA-256
   `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
5. **DB integrity and schema — UNVERIFIED NOW / RECHECK REQUIRED.** Using read-only/validate-only
   access, require one Alembic head `0056_layer3_connector_source_intake_record`,
   `PRAGMA quick_check = ok`, 94 model tables, 95 schema tables including `alembic_version`, and zero
   missing model tables. Empty/missing state must refuse; no initialization or migration is allowed.
6. **Secret-free denied-network resolution — UNVERIFIED NOW / RECHECK REQUIRED.** Require credential
   absent and egress false. Under explicit DNS and socket denial, resolve the campaign definition,
   both grants, current authority with deterministic run bindings, and reviewed runtime source identity.
   Any attempted network access, secret presence, resolver ambiguity, or source mismatch fails.
7. **Campaign, grants, markers, and evidence roots — UNVERIFIED NOW / RECHECK REQUIRED.** Recompute all
   hashes/fingerprints in §4; require exact campaign/revision/plan/seal/grant identities and archive
   byte parity; require both expected consumption markers absent; require expected log and seal paths
   absent; require `consumed/`, `logs/`, and `log-seals/` empty. Do not infer global non-use.
8. **Disposable prep child and staging — UNVERIFIED NOW / RECHECK REQUIRED.** Start a fresh dedicated
   PowerShell child with history disabled and no credential; bind it to the freshly verified runtime
   checkout and live4 subject; require the prep output to state no P8 and egress false. Close and
   discard on any drift. Do not place a credential, arm egress, or launch during packet preflight.
9. **Quiescence and residual acceptance — UNVERIFIED NOW / RECHECK REQUIRED.** Establish actual
   producer quiescence externally before `B_OWNER_PACKET_READY`, then freshly rebind it at owner
   decision and launch-final preflight because an earlier result is not inheritable. Present every C4,
   enumeration-drift, L2 live-frontier, clone-source, staging-order, quiescence, and corrected CI
   residual to the owner. Only direct owner acts in §7 can proceed; silence or prior acceptance cannot
   be reused.

## 9. Global lease and clearance boundary

The task-scope ceiling is `B_OWNER_PACKET_READY`. This packet currently remains within
`B_PACKET_AUDIT` and establishes neither `B_OWNER_PACKET_READY` nor `B_OWNER_AUTHORIZED`.

Current lease observation: **NO LEASE EXISTS.** This is not the terminal `NO_LEASE_ISSUED` receipt,
an owner act, containment assertion, release receipt, terminal disposition, or
`B_CLEARANCE_RECORDED`. Correction and re-audit remain active inside `B_PACKET_AUDIT`. If a future
lease is considered, it must be separately created and must bind:

- one unique lease ID, explicit lease state, issue time, expiry, and lane;
- the exact pre-packet evidence-base revision/tree and runtime revision/tree from §2;
- the corrected owner packet's exact path, containing commit/tree, blob, and raw SHA-256;
- the companion custody record's exact path, containing commit/tree, and blob;
- one designated checkout's absolute path, exact `HEAD`, Git registration or standalone state, and
  literal cleanliness receipt;
- the exact live4 campaign ID/fingerprint/expiry and both grant IDs, raw hashes, canonical
  fingerprints, and expected-marker hashes from §§2 and 4;
- the exact frozen plan and B1a seal identities, staging-script identity, bounded evidence roots,
  owner-packet/latest-launch cutoff, and minimum TTL;
- immutable references to each of the three direct owner-act receipts in §7, without relayed,
  inferred, inherited, or draft substitution;
- exactly one permitted run command class with action count fixed to one, plus separate bounded
  containment command classes; no operational command is supplied in this packet;
- distinct run and containment phases;
- distinct named run and containment operators;
- separate operator ACKs for both phases;
- `B_RUN_READY` only after credential-placement, egress-arming, one-launch-authority,
  launch-final preflight, minimum-TTL, and containment-readiness receipts all exist;
- a containment-readiness receipt that binds the named containment operator and covers these duties:
  - credential removal and verified absence;
  - egress disarm;
  - producer quiescence;
  - exact authority and grant disposition;
  - evidence sealing without deletion;
  - terminal-status receipt; and
  - actual capability and lease release;
- automatic terminal stop for success, refusal, failure, timeout, or ambiguity;
- containment after every terminal outcome;
- actual capability/lease release, not merely an intended release; and
- terminal `B_CLEARANCE_RECORDED` after release evidence is recorded.

Every disposition, including `DECLINED`, `HOLD`, `EXPIRED`, redirect, authorization, or a terminal
run outcome, converges on `B_CLEARANCE_RECORDED` through exactly one applicable path:

- **Lease existed:** containment and actual capability/lease release are mandatory before
  `B_CLEARANCE_RECORDED`.
- **No lease existed:** record `NO_LEASE_ISSUED`, do not invent containment or release, then record
  `B_CLEARANCE_RECORDED` for the no-lease disposition.

No disposition bypasses clearance. No lease state may be inferred from this packet or from an owner
field left blank.

## 10. Fail-closed conditions

Before terminal disposition, remain in `B_PACKET_AUDIT / AUDIT_HOLD` and issue nothing on TTL below
86,400 seconds, identity or byte drift, consumed marker, nonempty evidence/log/seal state, ambiguous
source/custody/lease state, failed or missing check, inferred or relayed owner field, incomplete CI
disclosure, producer quiescence failure, or any mismatch in revision, tree, plan, seal, campaign,
grant, dependency, interpreter, wrapper, DB, resolver, network-denial, secret-free, or checkout-state
proof.

When trusted UTC is at or after the cutoff, or authority expires, take the applicable terminal
`HOLD` / `EXPIRED` path in §9. If no lease existed, record terminal `NO_LEASE_ISSUED` and then
`B_CLEARANCE_RECORDED`; do not preserve an active audit HOLD beyond the terminal boundary.

## 11. Explicit nonclaims

This form claims no current `B_OWNER_PACKET_READY` attainment; P8; credential placement; egress
authority; run, retry, or second launch; dual PASS; current runtime compatibility; CI completeness or
green branch CI; PR readiness; merge authority; main landing; production readiness; or Lane A
authority. It does not execute, authorize, waive, clear, or predict anything.

## 12. Committed evidence paths

- `docs/campaign-records/2026-08-07-defect3-sciencebase-locator-landing.md`
- `docs/campaign-records/2026-08-07-authority-regeneration-4.md`
- `docs/campaign-records/2026-08-07-g2-p8-live-run-authorization.md` — historical live3 form only;
  its issued fields and stale checkout facts do not transfer to live4
- `docs/campaign-records/2026-08-04-g2-p6-residual-acceptance.md`
- `docs/campaign-records/2026-08-05-g2-owned-child-logger-freeze-defect.md`
- `docs/campaign-records/2026-08-07-l2-delta-review-818cc37e.md`
- `docs/campaign-records/2026-08-07-defect2-transport-fix-landing.md`
- `docs/campaign-records/2026-08-02-g2-prep-report.md`
- `docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md`
- `.github/workflows/playwright.yml`
- `backend/tests/test_ci_coverage_completeness.py`

These paths are evidence inputs, not owner authority.
