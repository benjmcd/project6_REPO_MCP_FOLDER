# ScienceBase defect #3 external security review (2026-08-07)

> L4 record of the independent pre-landing review of the ScienceBase strict-locator correction.
> Three Opus reviewers returned `SOUND-WITH-FINDINGS`; the Fable adjudicator returned
> `LAND-WITH-CONDITIONS`. The landing conditions are recorded below. This verdict did not itself
> authorize the owner-gated allowlist change, P8, credential use, or a live retry.

## 1. Review result

The three independent axes were:

- `R-SSRF`: `SOUND-WITH-FINDINGS`, with no blocking or material finding;
- `R-CORRECT`: `SOUND-WITH-FINDINGS`, with no blocking or material finding;
- `R-GOV`: `SOUND-WITH-FINDINGS`, with three material landing/governance findings: the certified
  production-path allowlist expansion, incomplete patch-carrier risk, and CI-shard coverage debt.

The Fable adjudicator resolved the combined result as **LAND-WITH-CONDITIONS**. Security was the
decisive axis: any SSRF weakening would have required `DO-NOT-LAND`. No such weakening was found.

## 2. Why the SSRF gate remains sound

The review independently traced the full validator and downstream use:

- The query relaxation is a two-way byte-exact comparison against two module constants: the
  original filename query and one pinned uppercase-`%2F` storage-key query. The `else` path raises;
  there is no wildcard, prefix, suffix, normalization, or attacker-influenced comparison.
- `downloadUri` remains the sole locator and fetch target. The optional `url` field is
  consistency-check-only: it must be a string byte-equal to `downloadUri` or validation rejects it;
  it is never selected for fetching. `viewUri` remains inert.
- All prior constraints remain: ASCII only; no whitespace, control character, backslash, or `#`;
  exactly one `?`; HTTPS; hostname and netloc in the two-host ScienceBase allowlist; port absent or
  443; no username, password, `@`, or fragment; exact catalog path; strict single `f=` pair.
- The validated projection is rechecked at arming and redirect handling. The artifact send remains
  hash-bound to that projection. The variable `query_class` is also included in the arming identity.
- Negative tests reject a hostile host, modified storage key, decoded slash, lowercase `%2f`, and
  appended parameter.

The accepted surface is therefore one additional pinned URL form, not a general `__disk__` parser.
The pre-existing SSRF boundary is as strong as before.

## 3. Six landing prerequisites and disposition

The adjudicator imposed six ordered prerequisites. Their landing disposition is now complete:

1. **Owner-gated allowlist resolution.** Add
   `backend/app/services/connectors_sciencebase.py` to
   `ALLOWED_CHANGED_PRODUCTION_PATHS`. The owner approved this certified-surface expansion, and
   commit `d781adfc` landed it adjacent to `connectors_nrc_adams.py`.
2. **Land the complete branch, not the incomplete patch alone.** The patch carrier omitted the new
   regression file. Landing came from `codex/sb-locator-fix3`, and the 135-line
   `test_sciencebase_locator_live_shape.py` is present in the landed commit.
3. **Run the full certified gate after allowlisting.** A clean standalone clone at the landed
   revision measured **356 passed** under the required plain pytest invocation.
4. **Resolve or formally record CI-shard debt.** The debt is formally recorded as a pre-main-merge
   item covering `test_connector_transport_loopback.py`, `test_sciencebase_fresh.py`, and
   `test_sciencebase_locator_live_shape.py`, none of which matches `BACKEND_SHARD_PATTERNS`.
5. **No assistant attribution in the commit.** The landed commit message is trailer-free and the
   four landed blobs are LF.
6. **Preserve the post-landing authority order.** Landing voided live3 for new code. Regeneration
   #4 is now complete at `d781adfc`; a fresh non-inheritable P8 and any owner retry remain later,
   separate acts. Satisfying this prerequisite means preserving the order, not pre-authorizing or
   collapsing those owner gates.

Thus all conditions required to land the fix were satisfied. The remaining P8, credential, and
retry are intentionally not conditions that this record may execute.

## 4. Carried findings

- **Pinned-key brittleness:** the exact storage key and uppercase `%2F` spelling can change if
  ScienceBase re-stores or re-encodes the file. Such drift fails closed. This is an availability
  risk, not a security weakening.
- **Variable query projection:** `query_class` may now be either
  `exact_single_f_expected_filename` or `exact_single_f_pinned_storage_key`. It is bound into the
  arming hash; downstream consumers must not assume the old single value.
- **Primary query gate:** the byte-exact `if`/`elif`/fail-closed `else` is load-bearing. The later
  `parse_qsl` check is retained as redundant defense in depth.
- **Test interpretation:** the discriminating RED test is the captured live-entry admission case.
  A conflicting-`url` negative could fail pre-fix for the old blanket-rejection reason and is not,
  by itself, proof of the new behavior.

## 5. Non-claims

This review does not grant P8, credential issuance or handling, live egress, retry authority, a PR,
or a merge to main. External review of the regeneration-and-records tranche follows separately.
