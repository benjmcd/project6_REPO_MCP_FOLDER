# Authority regeneration #4 bound to the ScienceBase locator fix (2026-08-07)

> L3/L4 regeneration record. The new authority set is bound to
> `d781adfcaab2eb880456aef7ac49ee589105bbbe` under `C:\p6-run\live4`. This record
> does not authorize a run: **fresh, non-inheritable G2-P8 remains a separate owner act.** No
> credential was present or used, egress remained disabled, and verification was key-free and
> offline.

## 1. Method self-validation before emission

The owner-authorized scratch generator was read before use. Its SHA-256 was
`346ac93af4e9a1635cb86d21b80b004e9f0f966d467425455a0daec002c4f7d5`. No script edit was needed:
phase 1 is set-agnostic and re-derived all values from the preserved, complete `live2` set before
phase 2 could emit `live4`.

The dry run wrote nothing and printed the required target guard, nine successful comparisons, and
the terminal validation line:

```text
[guard] REGEN_NEW_ROOT = C:\p6-run\live4  (phase 2 will rmtree this path; inspect before REGEN_APPLY=1)
=== PHASE 1: method self-validation against the EXISTING authority set ===
  [OK ] campaign raw sha: c24c5e3cd12c95a5… == c24c5e3cd12c95a5…
  [OK ] campaign fingerprint: 8b3c52d05615a137… == 8b3c52d05615a137…
  [OK ] nrc_adams_aps raw grant sha: 5c4cfe20c414929f… == 5c4cfe20c414929f…
  [OK ] nrc_adams_aps canonical grant fp: 405429e85ec6c430… == 405429e85ec6c430…
  [OK ] nrc_adams_aps consumption marker sha: 0b29e52ad6bf074d… == 0b29e52ad6bf074d…
  [OK ] sciencebase_mcs raw grant sha: b51cc632f3187014… == b51cc632f3187014…
  [OK ] sciencebase_mcs canonical grant fp: c54a8ff1355e0931… == c54a8ff1355e0931…
  [OK ] sciencebase_mcs consumption marker sha: da07d0c8bed44c74… == da07d0c8bed44c74…
  [OK ] index bytes sha (== filename): 952094f0bf5f2d4f… == 952094f0bf5f2d4f…
METHOD VALIDATED: every derived value and the full index reproduce exactly.

(dry run; set REGEN_APPLY=1 to emit the new set)
```

Only after confirming `C:\p6-run\live4` was absent was `REGEN_APPLY=1` run, exactly once. The
environment was:

```text
REGEN_BACKEND=C:\p6-scratch\dl-sbfix\backend
REGEN_NEW_ROOT=C:\p6-run\live4
REGEN_CODE_REVISION=d781adfcaab2eb880456aef7ac49ee589105bbbe
```

## 2. New authority identities

| Field | Value |
|---|---|
| Code revision | `d781adfcaab2eb880456aef7ac49ee589105bbbe` |
| Campaign ID | `ff1af01b-785e-4c12-98d1-3f278039b4ea` |
| Campaign fingerprint | `3c415b6fe717810c47c506c9de8ce9c0ec5b78e9a633db080cdce91f16915e01` |
| Campaign-definition SHA-256 | `07ef4c182d320f43163ff039e90f885bcee8e72a30e9b819732ff358c93c25c7` |
| Evidence-index SHA-256 | `e54ae4f30122293bf926fad89085472325c15279d642eb712e8e3deba16e6d6b` |
| Not before | `2026-08-07T14:06:52.580652+00:00` |
| Expires at | `2026-08-14T14:06:52.580652+00:00` |

The campaign ID is a fresh UUID4 and both grants have fresh arming nonces. Grant details:

| Connector | Raw grant SHA-256 | Canonical grant fingerprint | Arming nonce | Connector run ID | Marker SHA-256 |
|---|---|---|---|---|---|
| `nrc_adams_aps` | `8f0e5c778f76d0da272ba636308faeaef85693bbce95e4c9b508185ac91e79e1` | `af753222bcbf4a524f63275dde2a1563b5edb6ee9952a3edae430bf4b0b86c38` | `68ae8a8e-a258-411d-8b86-f9fb8ca3dfb9` | `a4111769-3868-5f0c-9c16-eeb4130594b4` | `1a862282ee40ecfaa30c52075584ae592486c3bc1f84ef9ad9499b18b2a68841` |
| `sciencebase_mcs` | `b1819f62ffbf3f7f83814ec061f0e37f99937d9e5e3e2c39b81370071787dd8d` | `f9b868cef8051af749c5de74d78d46162a3cf7c25123963fb705ba302dd400ae` | `8d36b4c2-dc9f-4799-ac92-2ac1a4200c48` | `622cb673-254b-56c4-9e9c-1d5c8d3908d8` | `85a68fe3c92312a817a828fe4f202cd1e029bdbc9863b3735badec6240d5e371` |

The evidence index is revision `1`; both predecessor fields are null. Top-level campaign/grant
bytes equal their content-addressed archive copies. `consumed/`, `logs/`, and `log-seals/` were
empty after verification, and both expected marker paths were absent. This is the expected prepared
authority snapshot, not evidence that a live4 run occurred.

## 3. Purpose-prepared run checkout

The pre-existing `C:\p6-scratch\dl-sbfix` clone was reused after all required checks passed. It is
a standalone clone, not a linked worktree:

```text
HEAD=d781adfcaab2eb880456aef7ac49ee589105bbbe
status_empty=true
git_dir=.git
git_common_dir=.git
core.longpaths=true
core.autocrlf=true
extensions.worktreeConfig=absent
git diff --quiet HEAD exit=0
tools/dual_live_run.py CR bytes=0
backend/requirements.lock.txt CR bytes=3018
dependency_set_sha256=1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d
reviewed source revision=d781adfcaab2eb880456aef7ac49ee589105bbbe
wrapper image sha256=fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f
interpreter image sha256=4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a
```

The CRLF lock file was not staged. Git's `autocrlf=true` normalization leaves the index and
working-tree comparison clean while preserving the required raw on-disk EOL shape.

## 4. Database and resolver verification

Alembic initialized `C:\p6-run\live4\db\method_aware.db` to the single head
`0056_layer3_connector_source_intake_record`. A read-only SQLite URI reported:

```text
PRAGMA quick_check(1)=[('ok',)]
model_table_count=94
schema_table_count=95
missing_model_tables=[]
```

Resolver verification ran with the NRC credential absent, live egress explicitly false, and
socket/DNS functions replaced by hard denials. No network attempt occurred. All of these passed:

- `resolve_current_dual_live_campaign_definition`;
- `resolve_current_connector_egress_grant` for NRC APS and ScienceBase, each unconsumed;
- `connector_campaign_log_capture._current_authority` with two deterministic run bindings;
- `_derive_reviewed_runtime_source_identity` at `d781adfc`;
- evidence-index identity, archive byte identity, absent consumption markers, and empty
  `consumed/`, `logs/`, and `log-seals/` directories.

## 5. Preserved roots and live3 declarative retirement

`C:\p6-run\live`, `live2`, and `live3` remained read-only. Pre/post metadata projections were
byte-equal:

| Root | Entries | Metadata SHA-256 | Root mtime UTC |
|---|---:|---|---|
| `live` | 26 | `41e27aaaaa8bf4401461bb2ba9e16530583c6640734ad4d485d332f956ef3cf5` | `2026-08-05T18:44:18.6295979Z` |
| `live2` | 26 | `d9fab1365bffc18ee41aa93baad8012735db42a54e144eedf17b20e15b8000a3` | `2026-08-06T00:28:20.5369427Z` |
| `live3` | 34 | `29a6cc40a4706eb554326ec692cea8c5944624f789cfd2b8410be0d893fcc893` | `2026-08-07T03:54:39.7125071Z` |

Live3 is **SPENT / DECLARATIVELY RETIRED**, not deleted or mutated. Both of its grant consumption
markers exist. Its authority set pairs only with code revision `818cc37e`, whose strict locator does
not admit the captured ScienceBase entry. The corrected `d781adfc` checkout cannot use live3 because
the code revision differs. Mixed pairings fail closed in both directions; no grant, budget, or
unconsumed capability transfers from live3 to live4.

## 6. Staging script and non-claims

`C:\p6-run\live4\set-live-env.ps1` is a non-secret, prep-only script. It points to the verified
standalone checkout and live4 paths, pins the expected HEAD and authority digests, leaves the NRC
credential unset, refuses prep if that credential is already present, keeps egress disabled, prints
the new campaign ID/fingerprint, and states that G2-P8 **has not been given**. It contains no launch
command.

This regeneration does not authorize P8, credentials, egress arming, a live run, a PR, or a merge
to main. External review of this regeneration-and-records tranche follows.
