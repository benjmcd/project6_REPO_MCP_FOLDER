# Authority regeneration #3 bound to the defect-#2 fix (2026-08-07)

> L3 regeneration record. The new set is bound to
> `818cc37e2f626bf8bb46056674d302df2765c7f0` and staged at a fresh evidence root. This
> record does not authorize a run: **fresh, non-inheritable G2-P8 authorization remains a separate
> owner act.** No credential was present or used, egress remained disabled, and all verification was
> key-free and offline.

## 1. Method self-validation before emission

The owner-authorized scratch generator was read before use. Phase 1 re-derived every derived value
of the existing `live2` authority set and compared it to the existing index before phase 2 could
write anything. The dry run printed the required target guard and all 9 checks passed:

```text
[guard] REGEN_NEW_ROOT = C:\p6-run\live3  (phase 2 will rmtree this path; inspect before REGEN_APPLY=1)
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

Only after that result, and after rechecking that `C:\p6-run\live3` did not exist, phase 2 was
enabled once with `REGEN_APPLY=1`.

### Scratch-script adaptation, exactly disclosed

Initial script SHA-256:
`c0faa9a0ef34e7c4b243d9abc12df1e69949652b58c0349556c703489e79121d`.

The sole content change was:

```diff
-OLD = Path(r"C:\p6-run\live")
+OLD = Path(r"C:\p6-run\live2")
```

Adapted script SHA-256:
`346ac93af4e9a1635cb86d21b80b004e9f0f966d467425455a0daec002c4f7d5`.

The explicit-target guard was unchanged. It refuses an unset target and refuses `live`, `live2`, or
the current `OLD` value as a phase-2 destination.

## 2. New authority identities

| Field | Value |
|---|---|
| Code revision | `818cc37e2f626bf8bb46056674d302df2765c7f0` |
| Campaign ID | `e5da5d33-d39f-4a91-b446-4cd902d3e1d1` |
| Campaign fingerprint | `f113ca41c54d5310075303712222ed0b3fbafa826d56a38c23858e980a96e3f2` |
| Campaign-definition SHA-256 | `2b9878f24476af77e90caed085a14d0d8299fac68c6cb136ccf281d5291e3b65` |
| Evidence-index SHA-256 | `1ea375923c17235528c3409686da2eebabb56b65c56751a84dad6e921f2b83da` |
| Not before | `2026-08-07T03:47:17.580652+00:00` |
| Expires at | `2026-08-14T03:47:17.580652+00:00` |

The campaign ID is a fresh UUID4 and both arming nonces are fresh. Grant details:

| Connector | Raw grant SHA-256 | Canonical grant fingerprint | Arming nonce | Connector run ID | Marker SHA-256 |
|---|---|---|---|---|---|
| `nrc_adams_aps` | `7ba50f2d9a8e8445782c84845ea11cfe2a4c9b0886f9b9b383bfc45986e1db5f` | `586abbdc9fc231c9d043ae75d735613fcd0a29299f5db8750d8bd3cf4a7b1a4d` | `ba93e8db-262f-42ba-9d7d-90356f1fd90c` | `3cad6f47-78d9-57c8-9591-462045a21b9f` | `758e736855c7a5ecba8343f7abfa6a0013ce6c039a749d12b52a2e79353ec194` |
| `sciencebase_mcs` | `491e154bcfeac3b87afd2704dd8ab96d594156fa3b4553ea71dd1b9ee5278473` | `df0b2fd455aa61a6f1fcfa268a89a8f3209b204ec13b8681fe858e6f68ce2daf` | `61c1c2be-42de-40e4-b786-3bc6211fd8a4` | `db258901-239e-5cd8-add3-67fafce3bdb1` | `aae2634a94214791deffa92bd8fbc6946c78186eb3b6552d1d1104cee57fc3e3` |

The generator emitted evidence-index revision `1` with both
`predecessor_index_relative_path = null` and `predecessor_index_sha256 = null`, preserving the
validated D5=a independent-root mechanism. Top-level campaign/grant artifacts are byte-identical to
their content-addressed archive copies. `consumed/`, `logs/`, and `log-seals/` each contained zero
entries after verification.

## 3. Purpose-prepared run checkout

`C:\p6-scratch\dl-run3` is a standalone clone, not a linked worktree. It is detached at the exact
landed revision. Final checks:

```text
HEAD=818cc37e2f626bf8bb46056674d302df2765c7f0
extensions.worktreeConfig=absent
core.longpaths=true
core.autocrlf=true
tools/dual_live_run.py CR bytes=0
backend/requirements.lock.txt CR bytes=3018
git diff --quiet HEAD exit=0
dependency_set_sha256=1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d
reviewed source revision=818cc37e2f626bf8bb46056674d302df2765c7f0
wrapper image sha256=fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f
interpreter image sha256=4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a
```

The source repository was shallow, so Git warned that `--local` was ignored; the result remains a
standalone clone with its own `.git` directory and no `extensions.worktreeConfig`.

### Stat-cache/EOL settlement disclosure

The handoff's stated one-pass order (`git add` while `core.autocrlf=false`, then set it true) did not
settle content-neutrally on this Git: it staged the CRLF lock bytes. A second add reused the stale
index stat. The executor restored **only the staged index entry** from `HEAD`, retained the required
3,018-CR working file, and re-added under `core.autocrlf=true`. Final filtered hash equals the HEAD
blob, raw working hash reflects CRLF as intended, the index is clean, and the purpose-tree bytes were
not otherwise changed. This correction is recorded rather than hidden because source identity is a
load-bearing gate.

## 4. Database and resolver verification

Alembic initialized `C:\p6-run\live3\db\method_aware.db` to the single head
`0056_layer3_connector_source_intake_record`. The repository producer-state checker passed. An
independent read-only SQLite connection reported:

```text
PRAGMA quick_check(1)=[('ok',)]
model table count=94
schema table count=95
missing model tables=[]
```

Resolver verification ran with `NRC_ADAMS_APS_SUBSCRIPTION_KEY` absent,
`CONNECTOR_LIVE_EGRESS_ENABLED=false`, and socket connect/DNS functions replaced with explicit
denials. The following repository checks all passed without arming:

- `resolve_current_dual_live_campaign_definition`;
- `resolve_current_connector_egress_grant` for NRC APS;
- `resolve_current_connector_egress_grant` for ScienceBase;
- `connector_campaign_log_capture._current_authority` with two deterministic run bindings;
- `_derive_reviewed_runtime_source_identity` at `818cc37e`;
- archive byte identity and empty unconsumed marker/log/seal directories.

## 5. Disposition of live2 — declarative retirement, not mutation

`C:\p6-run\live2` is **SPENT / RETIRED** and remains preserved read-only. Its NRC grant
`5c4cfe20…` was consumed by the refused 2026-08-05 run. Its unconsumed ScienceBase grant
`b51cc632…` is stranded because campaign budget is non-transferable and the paired NRC leg cannot
re-arm. Neither grant may be reissued.

Retirement is declarative, not a claim that the bytes ceased to parse. Paired with its own
`e53955d2` checkout, live2 still identifies its original defective code and evidence history; using
that pairing would be an unauthorized relaunch of known-defective transport behavior. Mixed pairings
fail closed in both directions: live2 does not bind `818cc37e`, and live3 does not bind `e53955d2`.
No file, directory, launcher, marker, database, or mtime under `live2` or `live` was written, renamed,
or removed during regeneration #3.

## 6. CI-completeness debt carried explicitly

`backend/tests/test_connector_transport_loopback.py` matches no `BACKEND_SHARD_PATTERNS` entry and
is not present in `EXCLUDED_BACKEND_TESTS`. This is one additional branch-local completeness debt
item. It must be paid before any merge to main; it is deliberately not actioned in this L3/L4 lane,
which permits docs-only repository changes and forbids production/test/CI edits.

## 7. Staging script and non-claims

`C:\p6-run\live3\set-live-env.ps1` is a non-secret staging script. It points to the standalone
checkout and live3 paths, pins the exact HEAD and authority digests, leaves the credential unset,
keeps egress disabled, prints the campaign ID/fingerprint, and states that G2-P8 **has not been
given**. It contains no launch command.

This regeneration does not authorize P8, credentials, egress arming, a live run, L5, a PR, or a
merge to main. It does not re-run or alter the already landed 356/404/10/92 counters. External review
of these L3/L4 records follows.
