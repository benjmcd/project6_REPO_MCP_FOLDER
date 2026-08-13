# Defect #3 ScienceBase locator fix landing (2026-08-07)

> L4 landing record for the third first-real-exercise defect. The fix is landed on
> `codex/dual-live-plan` at `d781adfcaab2eb880456aef7ac49ee589105bbbe`. This record does not
> authorize P8, credential use, egress, or another live run.

## 1. Run #2 outcome

Run #2 proved the NRC leg end-to-end through strict raw admission before the ScienceBase leg
refused:

- NRC run `3cad6f47-78d9-57c8-9591-462045a21b9f` reached terminal status `completed` with reason
  `nrc_raw_admission_completed`.
- The public PDF response was HTTP 200 and 335,284 bytes. Its persisted raw-content SHA-256 is
  `6ba1f0aa5b7a70e8ce8d1ebba9316249a02ae9404325fe5de2e2fa8035f47861`; the connector target row
  records `public_read_confirmed = 1`, `access_level_summary = public_direct_200`, and the matching
  content-addressed storage reference.
- ScienceBase run `db258901-239e-5cd8-add3-67fafce3bdb1` completed item hydration with HTTP 200,
  8,991 decoded bytes, then failed closed at `execution/raw_admission` with
  `sciencebase_exact_file_locator_invalid`; its terminal status is `failed` and retry was not
  authorized.

Both live3 consumption markers exist, so both grants are **SPENT**. The NRC credential remained
confined to its declared `nrc_aps_api_key` request audience; permanent counter/evidence surfaces
record hashes, byte counts, and audience labels, not the credential value. ScienceBase request
rules have credential audience `none`. The campaign did not create a false PASS: the ScienceBase
run and overall attempt refused, and live3 has no log seal.

## 2. Captured live locator shape and defect classification

The single authorized public, key-free item GET captured this file entry for item
`63d1a3c6d34e06fef15006be`:

```json
{"name":"mcs2023-germa_salient.csv","contentType":"text/csv","pathOnDisk":"__disk__7e/49/e8/7e49e8a4a53eb2219837f97defb22a25a286cdbc","size":510,"dateUploaded":"2023-01-25T21:48:54Z","url":"https://www.sciencebase.gov/catalog/file/get/63d1a3c6d34e06fef15006be?f=__disk__7e%2F49%2Fe8%2F7e49e8a4a53eb2219837f97defb22a25a286cdbc","downloadUri":"https://www.sciencebase.gov/catalog/file/get/63d1a3c6d34e06fef15006be?f=__disk__7e%2F49%2Fe8%2F7e49e8a4a53eb2219837f97defb22a25a286cdbc","viewUri":"https://www.sciencebase.gov/catalog/file/get/63d1a3c6d34e06fef15006be?f=__disk__7e%2F49%2Fe8%2F7e49e8a4a53eb2219837f97defb22a25a286cdbc&allowOpen=true"}
```

The observed first failure was the old blanket rejection of any `url` key even though `url` and
`downloadUri` were byte-equal. A second latent mismatch was that the live `downloadUri` used the
opaque `__disk__7e/49/e8/...` storage key rather than `f=mcs2023-germa_salient.csv`. The defect is
therefore the combined classification **(a) over-strict validator + (b) live locator-shape
change**, not a stale target.

## 3. Landed correction and security posture

The landed correction is deliberately narrow:

- `downloadUri` remains the sole selected locator and fetch target.
- A `url` field is tolerated only when it is a string byte-equal to `downloadUri`; conflicting
  metadata fails closed.
- The validator accepts either the original filename query or the one pinned uppercase-`%2F`
  storage-key query, each by byte-exact comparison to a module constant; every other query fails.
- The existing SSRF envelope remains intact: ASCII/control-character checks, HTTPS only, the exact
  two-host allowlist, exact path, port restricted to absent or 443, no userinfo or fragment, one
  `?`, and exactly one strict `f=` pair. Validation is repeated at arming and redirect handling.

Commit `d781adfcaab2eb880456aef7ac49ee589105bbbe` changed four files with 162 insertions and five
deletions: the validator, its existing strict tests, the new captured-shape regression module, and
the certified gate allowlist. The owner-approved allowlist expansion added
`backend/app/services/connectors_sciencebase.py` to `ALLOWED_CHANGED_PRODUCTION_PATHS`, adjacent to
and mirroring the already-admitted `connectors_nrc_adams.py` surface.

## 4. Landing verification and carried debt

The full certified gate was measured green at the landed revision in clean standalone clone
`C:\p6-scratch\dl-sbfix`: **356 passed**. The frozen plan blob `68f740af...` and pilot seal
`b8a89df2...` remained intact. This record cites that landing measurement and does not re-run the
gate.

Gate invocation has a non-obvious negative-controller posture requirement: use a plain pytest
invocation. Adding run-interpreter flags `-I -B -X pycache_prefix=NUL` makes the reviewed-controller
posture valid, so the negative test `test_reviewed_controller_requires_isolated_redirected_bytecode`
correctly does not raise and the gate appears to have one false-alarm failure. Plain pytest is the
certified invocation and produced all 356 passes.

CI completeness debt remains explicitly open before any merge to main. These three backend test
files match no `BACKEND_SHARD_PATTERNS` entry and are not presently covered by the release shards:

- `test_connector_transport_loopback.py`;
- `test_sciencebase_fresh.py`;
- `test_sciencebase_locator_live_shape.py`.

The defect fix, green gate, and this record do not pay that separate CI-shard debt and do not grant
main-merge authority.

## 5. Non-claims

The live3 authority set is spent and code-bound to `818cc37e`; it cannot authorize the landed
`d781adfc` code. No P8, credential, egress arming, retry, PR, or main write is authorized or claimed
here. Authority regeneration #4 and any later fresh non-inheritable P8 remain distinct acts.
