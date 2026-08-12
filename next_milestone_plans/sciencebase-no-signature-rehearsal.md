# ScienceBase W6 no-signature rehearsal record

Date: 2026-08-12

Baseline: `1667890344653e342793c12d9fbd6cc894d08d4d`

Harness commit: `d4ae332d`

Command: `py -3.12 -m pytest .\tests\test_sciencebase_no_signature_rehearsal.py -q -s`

Scope was synthetic/local fixtures only. No GO was signed or consumed; no credential, UAC,
network, ScienceBase request, worker launch, external effect, or live run occurred. R2 was not run
because real AppContainer and worker provisioning remain owner-gated.

## R1 — unsigned owner-GO template

Inputs: campaign `campaign-rehearsal`; run `11111111-1111-4111-8111-111111111111`; GO
`22222222-2222-4222-8222-222222222222`; query `synthetic public geology`; item
`synthetic-item`; file `synthetic-map.json`; synthetic envelope/authorization/grant/manifest
SHA-256 bindings; an existing temporary canonical root; and an external temporary owner path.

Observed output:

```text
PREPARED: owner_go_template_written
OWNER_GO_PATH: C:\Users\benny\AppData\Local\Temp\pytest-of-benny\pytest-2183\test_sciencebase_no_signature_0\r1-owner\owner-go.json
OWNER_GO_SHA256: sha256:776bc3e376e1cf9f8a55fde6a7a49853c11218650befb122ca11f4b1ab00de11
HOLD: live_go_template_exists
HOLD: live_go_template_inside_canonical_root
```

PASS. The create-once file contained exactly the 15 canonical fields. Fixed values were
`schema=project6.sciencebase_live_go.v1`, `credential_mode=none_public`,
`egress_mode=capability_scoped_default_off`, and the internally derived
`wrapper_start_token_ref=retired:sciencebase-live-v2`. Re-emission preserved the original bytes.
The inside-root attempt wrote nothing. Execution was a hard failure tripwire; the isolated spent
marker and reservation database remained absent, and cleanup ran after every attempt.

## R4 — independent closeout verification

Each case used a fresh temporary root and a synthetic `reservation.db` with one deterministic GO
consumption event, one successful terminal event, a locally written artifact, and the stated
reservation mutation. The command received only the canonical root, exact run UUID, exact
`<root>\reservation.db`, and `sha256:` plus 64 `9` characters as the GO digest.

Observed outputs/codes:

| Case | Exit | Status and exact code |
|---|---:|---|
| Exactly 3 reservations + matching artifact | 0 | `VERIFIED: sciencebase_closeout_verified` |
| Only 2 reservations | 2 | `HOLD: sciencebase_closeout_evidence_malformed` |
| 4 reservations | 2 | `HOLD: sciencebase_closeout_evidence_malformed` |
| Artifact bytes changed after terminal metadata | 2 | `HOLD: sciencebase_artifact_verification_failed` |
| `reservation.db` renamed to `reservation.db.bak` | 2 | `HOLD: sciencebase_closeout_failed` |
| GO-consumption row deleted | 2 | `HOLD: sciencebase_closeout_evidence_incomplete` |

PASS. The valid case recorded exactly one `sciencebase_closeout_verified` event; every HOLD case
recorded zero. Artifact tampering was detected only after the verifier reopened and hashed the
artifact bytes, proving the terminal record's claimed hash was not trusted.

## R0 — fresh-root initializer

Input: an existing empty temporary canonical root and run
`11111111-1111-4111-8111-111111111111`. `DUAL_LIVE_RUNTIME_ENABLED` was absent.

Observed output:

```text
INITIALIZED: C:\Users\benny\AppData\Local\Temp\pytest-of-benny\pytest-2183\test_sciencebase_no_signature_0\r0-root\reservation.db
PREPARED: dual_live_runtime_prepared_non_live
```

PASS with a boundary note: `INITIALIZED` is the initializer's stdout. The second line is the
harness's observation of the separately invoked non-live prepare result, not initializer stdout.
The created store opened in SQLite `mode=rw`, the exact run row existed, the reservation census was
empty, and preparation did not return `reservation_store_unavailable`. Synthetic boundary,
transport, and broker tripwires proved that prepare did not acquire/launch/serve/effect. Static
inspection also confirmed the initializer contains no runtime-enable, prepare, execution, request,
or worker-launch surface.

## Finding at the W6 baseline

`initialize_reservation_database` closes the create-once file descriptor before SQLite reopens the
pathname. This leaves a pathname-substitution window and does not establish native Windows
owner/DACL/reparse/link custody during initialization. If SQLite schema initialization or its
verification fails after file creation, the empty/partial `reservation.db` remains and all retries
HOLD as `reservation_database_exists`. The behavior is fail-closed but operationally poisoned.
Per the W6 scope fence, production code was not changed. This must be resolved or explicitly
accepted before treating initialization as a secure owner ceremony step.

## W7 resolution

Resolved by `33102a89` (`fix(sciencebase): atomically initialize reservation store`). The
initializer now creates a protected same-directory staging file, initializes SQLite through
`?mode=rw`, explicitly closes the SQLite connection, rebinds the pathname-opened object to the
retained handle identity, flushes and revalidates custody, and publishes that exact file under
`reservation.db` with a pinned-directory-relative, no-replace native rename. The root and file must
remain fixed-local, owner-controlled, protected owner-and-SYSTEM-only, non-reparse, single-link,
same-volume, and identity-stable. Pre-publication failures dispose only the attempt's exact staging
handle, so the canonical name remains absent and retryable; a concurrent canonical winner is never
replaced.

TDD proof includes wrong-owner directory/file, reparse directory/file, hard-link, non-fixed volume,
staging-path substitution, identity drift, incomplete-canonical visibility, schema failure after a
partial transaction, retry, native Windows publication, and thread/process concurrency. The broad
offline dual-live surface passed `307 passed, 2 skipped`; Ruff and `git diff --check` passed. No
signature, credential, UAC, network, ScienceBase request, worker launch, external effect, or live
run occurred.
