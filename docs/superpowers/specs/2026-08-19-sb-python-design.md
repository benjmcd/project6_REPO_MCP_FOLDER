# ScienceBase Python Binding Correction

Status: draft implementing the owner-approved direction; written-spec review pending, 2026-08-19

Implementation base: `57c40338aff658bca0a692581fe62353138b6a69` (`codex/sb-live-impl`)

Implementation lane: `codex/sb-python-bind-fix` in `worktrees/sb-pyfix`

## Purpose

Correct the ScienceBase preparation flow that combined a floating ambient
Python selector with a patch-pinned worker archive and then required their
`python.exe` bytes to match. Preserve the exact byte-identity invariant, move
compatibility proof ahead of attempt-consuming state, add executable Windows
regression coverage, and prepare a wholly fresh Attempt-4 authority package.

This design does not authorize landing, pushing, elevation, signing, private-key
access, W5 observation, or live ScienceBase execution.

## Confirmed State

- Attempt 3 stopped fail-closed after profile and worker provisioning but before
  reservation-store or authority-envelope initialization.
- The ambient root recorded by the owner diagnostic equals the root bound into
  the worker record.
- Ambient Python is CPython 3.12.10. Its `python.exe` is 104,952 bytes with
  SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
- H3 pins the worker to `python-3.12.6-embed-amd64.zip`. Its `python.exe` is
  103,704 bytes with SHA-256
  `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae`.
- Bytes streamed from the official PSF Python 3.12.10 embeddable-archive URL
  were 11,133,606 bytes with SHA-256
  `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.
  Their `python.exe` exactly matches the ambient executable above.
- `py -3.12` is a version-prefix selection. The exact registered selector for
  this runtime is `-V:PythonCore/3.12.10`.
- Attempt 3 is conservatively retired as spent: 3 of 5 attempts are spent and
  Attempts 4 and 5 remain. No GO, signature, GO consumption, or governed live
  request occurred in Attempt 3.

## Evidence Provenance

- Repository-confirmed: H3 readiness resolves `py -3.12`, the provisioner pins
  3.12.6, and the later runbook gate requires equal executable SHA-256 values.
- Owner-observed: the retained Attempt-3 diagnostic supplied the ambient and
  worker versions, paths, byte lengths, and hashes listed above.
- Primary external: the 3.12.10 archive bytes came from the
  [official PSF archive URL](https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip),
  and exact launcher-tag semantics come from the
  [Python 3.12 Windows documentation](https://docs.python.org/3.12/using/windows.html#python-launcher-for-windows).
- Governance ruling: Attempt 3 is counted as spent conservatively because the
  frozen Phase-1 execution boundary began and attempt-scoped residue exists;
  absence of a GO is not treated as an unspent provisioning attempt.

## Decision

Treat the installed owner-host Python 3.12.10 runtime as fixed. Re-pin the
worker to the official Python 3.12.10 embeddable archive, resolve the ambient
runtime by exact launcher tag, and prove archive/ambient compatibility before
any attempt-scoped mutation.

Keep the existing post-provision ambient/worker equality comparison as defense
in depth. Do not weaken equality to major/minor, ABI, version-string, or
path-only compatibility.

## Rejected Alternatives

### Retain 3.12.6 and change the host

Installing or registering an exact ambient 3.12.6 runtime would modify the
shared workstation. Retaining `py -3.12` would also preserve the underlying
patch-drift defect. This route is outside the approved host constraint.

### Remove ambient/worker byte equality

The durable runtime independently validates the worker and records the ambient
root, but it does not durably bind the ambient executable hash. Removing the
preparation equality check would weaken a frozen trust assumption and require a
separate owner threat-model decision.

### Add a content-addressed bootstrap subsystem

An isolated absolute-path bootstrap would avoid launcher registration but adds
new custody, provisioning, cleanup, and lifecycle surfaces. It is unnecessary
while exact registered 3.12.10 resolves consistently and matches official
worker bytes.

## Components

### 1. Validate-only Python binding gate

Add `scripts/validate-dual-live-python-binding.ps1`. It has one responsibility:
return a verified binding observation or fail closed without creating,
modifying, or deleting any filesystem object.

The script must:

1. Invoke the Python launcher as
   `py -V:PythonCore/3.12.10 -I -S -c "import sys; print(sys.executable)"`.
   Require exit code zero and exactly one non-empty stdout line containing an
   absolute `sys.executable` path; treat any launcher diagnostic as failure.
2. Require the interpreter leaf, archive leaf, and every existing ancestor up
   to their drive roots to be ordinary non-reparse filesystem objects on fixed
   local volumes. Resolve their rooted paths using the repository's existing
   exact-path helper pattern; reject rather than follow any reparse point.
3. Open the ambient executable once, read-only and without write/delete sharing.
   Require that handle to contain 104,952 bytes with SHA-256
   `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
4. Require the archive leaf name
   `python-3.12.10-embed-amd64.zip`, length 11,133,606, and SHA-256
   `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.
5. Open the ZIP once, read-only and without write/delete sharing; hash that
   handle and rewind it. Require exactly one case-insensitive match for
   `python.exe`, require its full name to be the exact case-sensitive string
   `python.exe`, and hash that member without extraction.
6. Require the member length/hash to equal the ambient length/hash.
7. Return one structured PowerShell object containing status
   `PYTHON_BINDING_OK`, the exact launcher tag, interpreter path/root, archive
   identity, and ambient/member identities.

The success object has exactly these ordered properties:
`status`, `launcher_tag`, `ambient_interpreter`,
`ambient_interpreter_root`, `ambient_bytes`, `ambient_sha256`, `archive_path`,
`archive_bytes`, `archive_sha256`, `archive_member`, `archive_member_bytes`,
`archive_member_sha256`, and `expected_worker_sha256`. Hash fields are lowercase
64-character hexadecimal without a `sha256:` prefix; equality is ordinal.

Expected failure codes are stable and distinct:
`python_binding_launcher_invalid`, `python_binding_ambient_invalid`,
`python_binding_archive_invalid`, `python_binding_archive_member_invalid`, and
`python_binding_mismatch`. Empty or partial observations fail closed. The
script emits no record file and does not provision or seed runtime state.

The production entry point accepts only `-PythonArchive`. Its internal
comparison function accepts resolved paths and expected identities as
parameters so the production entry point can pass frozen constants while
Windows tests execute that exact function against disposable synthetic files.
Caller-configurable expected identities are not exposed by the production entry
point.

### 2. Worker pin

Update `scripts/provision-dual-live-worker.ps1` to pin:

- `PythonVersion = 3.12.10`;
- archive leaf `python-3.12.10-embed-amd64.zip`;
- archive SHA-256
  `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.

Retain the current exact archive validation, content inventory, manifest,
content-addressed root, ACL hardening, binding schema, and final verification.
Do not add downloading to the provisioner.

Close the existing hash-to-extraction race. The provisioner must open the
archive once with `FileAccess.Read` and `FileShare.Read`, compute the pinned
length/hash from that handle, rewind it, and construct one read-mode
`System.IO.Compression.ZipArchive` over the same stream. Before extraction,
reject rooted/traversing entry names and case-insensitive destination
collisions. Extract that same `ZipArchive` into the new provisioning root with
`ZipFileExtensions.ExtractToDirectory`; keep the original handle open until
extraction completes. Do not hash one path open and extract from another.
Place this sequence in one production helper so the Windows race/traversal
tests execute the same code the provisioner calls.

The extracted inventory and manifest remain the downstream proof of what was
written. Add a Windows regression that attempts archive replacement, rename,
and deletion between hash and extraction. The operation must either be denied
by the no-write/no-delete share or the provisioner must fail closed; extraction
may never silently continue from replacement bytes.

### 3. Readiness flow

Update `next_milestone_plans/sciencebase-live-readiness.md` so the validate-only
gate runs before attempt nonce creation, binding-parent creation, campaign-root
creation, profile creation, or worker provisioning.

Use a single `$PythonLauncherTag = 'V:PythonCore/3.12.10'` value. Pass it through
the existing `project6.ps1 -PythonVersion` parameter for every ScienceBase
initializer, template, live, and closeout invocation. Do not change the global
`project6.ps1` default because unrelated actions use it.

Remove every direct `py -3.12` resolution from the readiness document. Each
phase obtains one gate result, requires `status -ceq 'PYTHON_BINDING_OK'`, and
sets `$Py` from that result's `ambient_interpreter`; it never independently
re-resolves a minor-version prefix.

Repeat the validate-only gate:

- in a fresh ordinary pre-sitting shell before any Attempt-4 custody creation;
- in a fresh elevated parity-precheck shell, also before any Attempt-4 custody
  creation;
- again in the elevated Phase-1 shell after custody validation but before the
  attempt-begun boundary;
- in the fresh non-elevated rehydration shell before template emission;
- immediately before any later signed live invocation;
- immediately before closeout after the live invocation terminates.

After worker provisioning, retain the current comparison between the observed
ambient root/hash and the emitted worker binding/interpreter. That comparison
detects extraction, provisioning, or between-check drift.

Gate failure disposition is phase-sensitive and explicit:

- before the Attempt-4 nonce or any Attempt-4 state exists: `PRE-SITTING HOLD`;
  no attempt is consumed, no automatic repair/retry occurs, and the prerequisite
  may be rerun only after the owner understands the changed host fact;
- after Attempt-4 state exists but before the attempt-begun boundary:
  `PRE-BEGIN HOLD`; the provisioning attempt is not automatically spent, but
  every byte is preserved and neither resume nor namespace retirement occurs
  without an explicit owner ruling. Any authorized resume must rerun the gate
  and revalidate the complete pre-begin custody/identity set first;
- after the attempt-begun boundary but before any signature exists: terminal
  `ATTEMPT HOLD`; conservatively count the attempt spent, preserve every byte,
  prohibit continuation/reuse, and require fresh identities under the remaining
  owner budget;
- after a signature exists but before live invocation: terminal
  `SIGNED-AUTHORITY HOLD`; count the attempt spent, retire the unconsumed
  signature and its GO from all future use, preserve them as evidence, and
  require a wholly fresh attempt and signing decision;
- after live invocation terminates but before closeout:
  `POST-LIVE CLOSEOUT HOLD`; never rerun live or reuse the signature, preserve
  all terminal evidence, and resume closeout only under the existing closeout
  recovery rules plus explicit owner direction after the gate passes again.

The gate itself emits or throws only its stable code; it never infers campaign
phase. Each documented call site owns one fixed disposition label from the list
above, catches any gate failure, prints the stable code and that one label, then
stops. Executable tests bind every call site and its ordering to exactly one
label. Neither layer repairs, deletes, relabels, resumes, or retries.

### 4. External archive prerequisite

The new official archive belongs at
`C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip`. Creating that
file is a later owner-authorized prerequisite action outside the repository.
The existing 3.12.6 archive is historical input and must not be removed,
overwritten, renamed, or reused for Attempt 4.

## Data and Authority Flow

1. A free validate-only check proves exact launcher, ambient, archive, and ZIP
   member identity.
2. Only after that proof may Attempt-4 custody and provisioning begin.
3. The provisioner builds the worker from the same pinned archive and a clean,
   reviewed source commit.
4. The existing post-provision check proves the emitted worker executable still
   matches the ambient executable.
5. Worker manifest and interpreter hashes flow into the binding, authority
   envelope, prepared runtime, GO template, and eventual signature.
6. Every source or runtime-pin change therefore requires new downstream bytes;
   no Attempt-3 identity is reusable.

## Test-Driven Verification

### RED

Use staged RED so a missing new script is not misreported as proof of the
interpreter defect:

1. First add the gate's public-interface and executable behavior tests. Observe
   their expected missing-entry-point failure, then add the still-inert gate and
   make its synthetic mismatch-rejection and match-acceptance tests pass.
2. Before changing the worker pin or readiness flow, run a read-only real-host
   characterization through the gate's production comparison function. Derive
   the worker-side expected identity from the current provisioner pin and use
   the existing official 3.12.6 archive plus the installed 3.12.10 ambient
   executable. It must fail specifically with `python_binding_mismatch`.
3. Snapshot the complete Attempt-4 named-path vector immediately before and
   after that characterization. The fixed vector is:

   - `C:\owner-controlled\project6-bindings-4`;
   - `C:\owner-controlled\project6-w5obs-4`;
   - `C:\p6-sciencebase-worker-4`;
   - `C:\ProgramData\Project6`;
   - `C:\owner-controlled\project6\sciencebase-authority.json`;
   - `C:\owner-controlled\project6\owner-go.json`;
   - `C:\owner-controlled\project6\owner-go.json.sig`;
   - `C:\owner-controlled\project6\attempt4-elevated-transcript.txt`;
   - `C:\owner-controlled\project6\attempt4-nonelevated-transcript.txt`.

   Record existence for every path. For anything present, record type,
   `CreationTimeUtc`, `LastWriteTimeUtc`, and a deterministic recursive manifest
   of relative path, type, byte length, and SHA-256. Record the same fields for
   the archive and ambient executable. Exclude last-access time because a read
   may update it. Require the before/after snapshots to be identical.

The automated suite must also require:

- exact 3.12.10 constants and selector;
- the initial gate invocation to precede the first Attempt-4 mutation;
- the complete readiness file to contain zero `py -3.12` or other minor-prefix
  resolutions, to assign every `$Py` from a successful gate object, and to
  contain exactly six gate calls including pre-closeout;
- a synthetic mismatched ambient/archive member to throw
  `python_binding_mismatch` without changing a disposable mutation sentinel;
- a synthetic matching ambient/archive member to return `PYTHON_BINDING_OK`
  and the expected worker interpreter hash;
- executable selector forwarding through both `initialize-dual-live` and
  `run-dual-live`. A Windows PowerShell 5.1 subprocess must place a disposable
  `py.cmd` capture shim first on a temporary `PATH`, invoke each action without
  Python/provisioning/network execution, and prove the first launcher argument
  is exactly `-V:PythonCore/3.12.10`.

An executable call-site-order test must prove the six phase calls map in order
to `PRE-SITTING HOLD`, `PRE-SITTING HOLD`, `PRE-BEGIN HOLD`, `ATTEMPT HOLD`,
`SIGNED-AUTHORITY HOLD`, and `POST-LIVE CLOSEOUT HOLD`; no call site may infer,
omit, or select among labels dynamically.

The executable failure matrix must cover every stable code:

- `python_binding_launcher_invalid`: nonzero launch, empty/multiple stdout
  lines, non-rooted path, and launcher diagnostics;
- `python_binding_ambient_invalid`: missing/wrong-identity leaf plus interpreter
  leaf and ancestor reparse cases;
- `python_binding_archive_invalid`: missing/wrong-name/wrong-size/wrong-hash
  archive plus archive leaf and ancestor reparse cases;
- `python_binding_archive_member_invalid`: missing, duplicate-exact,
  case-colliding, rooted/traversing, and destination-colliding ZIP entries;
- `python_binding_mismatch`: individually valid but unequal ambient/member
  identities.

Every failure case must emit zero success objects. Success must emit exactly one
object with the exact field set and `PYTHON_BINDING_OK`. Tests must also prove
the production entry point rejects caller-supplied version/hash/size identities
and that archive replacement/rename/deletion cannot cross the locked
hash-to-extraction boundary.

Retain both RED outputs. A source-token failure, missing-file failure, or the
historical Attempt-3 diagnostic alone is insufficient evidence for the
composition RED.

### GREEN

Run the same executable tests under Windows PowerShell 5.1 against disposable
temporary files. Then run the focused readiness, provisioner, runtime, and
existing elevated ACL suites with cache and bytecode generation disabled.

Add `tests/test_dual_live_python_binding.py` explicitly to the required
`dual-live-windows-boundary` job in `.github/workflows/playwright.yml`. Its
Windows PowerShell 5.1 cases must execute with zero skips. Extend
`backend/tests/test_ci_coverage_completeness.py` to prove that exact wiring.
Re-pin that job's B0 setup runtime and embeddable archive from 3.12.6 to exact
3.12.10 (including archive URL/hash), so the required AppContainer boundary
proof exercises the corrected worker patch version rather than a generic stale
fixture.

Repeat the same real-host characterization after the 3.12.10 repin and archive
placement. It must return `PYTHON_BINDING_OK`; the ambient, archive-member, and
expected-worker hashes must agree; and the before/after no-mutation snapshots
must remain identical.

Obtain separate real-host evidence using the installed 3.12.10 interpreter and
the owner-placed official archive. The free gate must pass in both fresh
non-elevated and elevated Windows PowerShell 5.1 shells before any Attempt-4
path is created. That host gate performs no provisioning and is not an attempt.

The retained Attempt-3 diagnostic is historical RED evidence. It does not
substitute for the new composition RED or the post-fix real-host GREEN.

## Attempt-3 Preservation and Attempt-4 Regeneration

Preserve unchanged:

- Attempt-3 elevated transcript and packet/carrier/freeze set;
- `project6-bindings-3` and its profile/worker bindings;
- `p6-sciencebase-worker-3` and its content-addressed bundle;
- Attempt-3 W5 scratch and profile/AppContainer state;
- all Attempt-1 and Attempt-2 residue;
- the shared campaign root and fixed campaign subject.

Attempt 4 must use fresh `-4` topology, nonce, profile moniker, profile and
worker bindings, AppContainer identity, connector-run ID, worker manifest,
Phase-1 correlation/transcripts, W5 scratch, authority envelope, GO ID,
template, digest, and—only if separately authorized—signature.

## Governing Records and Refreeze

The canonical record root is
`C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox`.
All eight files below are workspace-local canonical governance carriers outside
the implementation worktree and are not tracked by implementation Git.

| Hash order | Exact path below the record root | Required action and phase |
| ---: | --- | --- |
| 1 | `plan-of-record-sciencebase-signed-go-2026-08-12.md` | After authorized landing, verify unchanged unless a cited semantic contradiction requires a separately reviewed amendment. |
| 2 | `SITTING-RUNBOOK-2026-08-14.md` | Reconcile to H4/Attempt 4: 3/5 spent, exact 3.12.10 gate order, fresh paths, failure dispositions, exact copy ranges, and retained Attempt-3 residue. |
| 3 | `Q12-EVIDENCE-POINTER-INDEX-2026-08-15.md` | Append/correct Attempt-3 failure evidence and point only to newly generated H4/Attempt-4 review evidence. |
| 4 | `owner-decision-sheet-sciencebase-signed-go-2026-08-12.md` | Record the owner's 3.12.10 invariant-preserving ruling, conservative Attempt-3 accounting, and absence of land/sign/live authority. |
| 5 | `amendment-addendum-v1.1-sciencebase-signed-go-2026-08-12.md` | Add the exact runtime correction, archive identity, gate/failure rules, and identity-regeneration consequence. |
| 6 | `forward-map-signed-go-lane-2026-08-13.md` | Verify unchanged unless a cited semantic contradiction requires a separately reviewed amendment. |
| 7 | `HANDOFF-SESSION-CONTINUATION-2026-08-14.md` | Reconcile failed Attempt 3, H4 implementation/review evidence, two remaining attempts, and the exact next owner gate. |
| 8 | `AUDIT-LEDGER-2026-08-14.md` | Append the Attempt-3 stop, preserved residue, root-cause evidence, corrective review/verification, H4 identity, and refreeze result. |

All tracked source, test, workflow, and readiness corrections occur before the
final reviewed H4 commit. Any tracked change after that review creates a new
head and requires re-review plus a newly head-bound owner land/push token.
Only after authorized landing/push may the eight external records be reconciled
to the landed head.

Hash the eight raw files in the table order with SHA-256. Hash exactly the bytes
stored on disk; do not normalize encoding, BOM, or line endings. Record each
lowercase digest and raw byte length. Write the new freeze record as UTF-8
without BOM and LF endings at
`state/agent-inbox/session-9ee3527a-adversarial-pass/packet-attempt4/S6-H4-FREEZE-RECORD-2026-08-19.md`.
The freeze record is not one of its own eight inputs.

Retain `packet-attempt3/S6-H3b-FREEZE-RECORD-2026-08-19.md` unchanged as
historical Attempt-3 authority. Never overwrite a freeze record: any later
record correction requires a newly suffixed freeze record and invalidates every
packet/carrier derived from the earlier one.

Generate a wholly fresh
`packet-attempt4/PACKET-ATTEMPT4-2026-08-19.md` plus
`packet-attempt4/CARRIER-STATUS.md`, AST/synthetic verification evidence, and an
independent dual-review handoff. Every carrier self-identity, embedded record
hash, source head/blob/range, attempt path, nonce-bearing field, and count must
refer to H4/Attempt 4. State `3 of 5 spent, 2 remain` and include every
Attempt-3 path in the retained-residue set.

No previous land token, packet approval, Q12 attestation, GO, or signature
travels to the new head or Attempt 4.

## Non-goals and Residuals

- No generic Python version manager or global `project6.ps1` behavior change.
- No worker-binding schema, GO schema, signing, key, egress, reservation,
  broker-ordering, AppContainer, or campaign-subject change.
- No full ambient DLL/stdlib closure attestation. Exact `python.exe` equality is
  retained as the currently ratified floor.
- No claim that exact-tag selection is immutable across host changes. Repeated
  phase-boundary validation is the containment.
- No live request or private-key read during implementation or verification.

## Acceptance Criteria

1. The correction is isolated from the dirty root and frozen ceremony worktree.
2. Attempt-3 residue is unchanged and operational accounting says 3/5 spent.
3. Automated executable coverage proves mismatch rejection and match acceptance
   through the production comparison function; retained real-host composition
   evidence fails before the repin and passes after it.
4. The initial preflight is validate-only and precedes every Attempt-4 mutation;
   repeated phase-boundary checks use the explicit HOLD dispositions.
5. Every ScienceBase Python launcher invocation uses exact 3.12.10 selection.
6. Worker pin, archive identity, ambient identity, and ZIP member identity agree.
7. Provisioning hashes and extracts one locked archive stream; replacement,
   rename, deletion, traversal, and case-collision tests fail closed.
8. Every stable failure code, zero-object failure, exact one-object success, and
   closed production parameter surface has executable coverage.
9. Existing post-provision byte equality remains enforced.
10. Focused tests, required no-skip Windows CI, and real host/elevated gates pass.
11. An independent reviewer finds no unresolved critical or major issue.
12. No land/push occurs without a fresh owner token bound to the reviewed head.
13. All required governing records and identities are freshly reconciled after
    any authorized land.
14. The Attempt-4 packet is fresh, self-consistent, independently approved, and
    still grants no signing or live-execution authority.

## Recommendation Invalidation Conditions

Reopen the design before implementation if the exact tag resolves differently
between fresh elevated and non-elevated shells, the owner-host archive/member
hashes do not reproduce, focused worker tests show 3.12.10 behavior drift, or a
governing record establishes that Python 3.12.6 itself—not merely exact
ambient/worker equality—is mandatory.
