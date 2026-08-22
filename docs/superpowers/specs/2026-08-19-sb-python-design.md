# ScienceBase Python Binding Correction

Status: R4 approved by owner; minimum test-first implementation tranche complete,
with elevated exact-host acceptance still owner-gated, 2026-08-21

Implementation base: `57c40338aff658bca0a692581fe62353138b6a69` (`codex/sb-live-impl`)

Specification lane: `codex/sb-python-bind-fix` in `worktrees/sb-pyfix`

## Purpose and authority

Correct the ScienceBase preparation flow that combined a floating ambient
Python locator with a patch-pinned worker archive and then required their
`python.exe` bytes to match. Move Python compatibility proof ahead of
attempt-consuming state, preserve the strict byte-identity design unless the
owner later chooses the explicitly open relaxation decision, close the archive
hash-to-extraction race, and preserve both remaining attempts with protected,
attempt-scoped custody families.

The specification alone authorized no implementation. The owner's later
`APPROVE REVISED R4 SPEC AS WRITTEN` instruction authorizes only the minimum
test-first R4 implementation tranche in the isolated implementation worktree.
It does not authorize custody creation, governing-record writes, land, push,
elevation, signing, key access, network access, W5 observation, an attempt
spend, or live ScienceBase execution.

## Confirmed state

- Attempt 3 stopped fail-closed after profile and worker provisioning but before
  reservation-store or authority-envelope initialization.
- `$P1_IexBegun` had already crossed the campaign's spend boundary. The owner
  ratified `RATIFY W6-PRE ATTEMPT 3=SPENT`: exactly 3 of 5 attempts are spent;
  Attempts 4 and 5 remain. No GO, signature, GO consumption, governed network
  request, or live execution occurred in Attempt 3.
- The ambient root recorded by the owner diagnostic equals the root bound into
  the retained Attempt-3 worker record.
- Ambient Python is CPython 3.12.10. Its `python.exe` is 104,952 bytes with
  SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
- H3 pins the worker to `python-3.12.6-embed-amd64.zip`. Its `python.exe` is
  103,704 bytes with SHA-256
  `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae`.
- Official PSF Python 3.12.10 embeddable-archive bytes were independently
  characterized as 11,133,606 bytes with SHA-256
  `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`;
  their `python.exe` member was characterized as the ambient identity above.
  The owner-host archive path remains an owner-placed prerequisite and this
  equality must be re-proven from that exact disk file before Attempt 4.
- On the owner host, both `py -V:PythonCore/3.12.10` and `py -V:3.12.10`
  returned exit 103. `py -V:PythonCore/3.12` and `py -3.12` resolved to the
  installed Python312 interpreter. The launcher tag is therefore a vendor/minor
  locator; it does not enforce patch 3.12.10.
- The worker profile provisioner records the provisioning account's current
  Windows user SID as `broker_sid`, and the exact six-ACE protected worker DACL
  grants that broker SID RX mask `0x001200A9`. Owner-host evidence proved the
  current SID equals both retained profile/worker broker SIDs and that a fresh
  non-elevated `Get-FileHash` of the hardened worker interpreter succeeds. The
  adversarial claim of a deterministic non-elevated denial is false. Full non-elevated
  bundle validation remains a required pre-Attempt-4 proof.
- Reservation initialization's only durable output is
  `<canonical-root>\reservation.db`; it uses a same-directory
  `.reservation.db.<32-hex>.tmp` staging leaf that must be published or discarded.
  Authority initialization performs an `O_EXCL` write to its supplied output.
  `C:\ProgramData\Project6\Authority` is first reached by one-use GO consumption,
  not by either initializer.
- The production runtime mutex name hashes normalized `canonical_root`, a NUL,
  and `campaign_id`. Different Attempt-4 and Attempt-5 canonical roots therefore
  have different mutex names; strict serial operation needs an explicit
  phase-scoped family action guard.

## Evidence provenance

- Repository-confirmed: the H3 selector, provisioner pin, profile-to-broker SID
  derivation, exact six-ACE ACL, post-provision equality, create-once
  initializers, ProgramData consumption point, and mutex derivation.
- Owner-observed: Attempt-3 stopping point and identities, launcher behavior,
  broker/current-user SID equality, and successful non-elevated worker hash.
- Primary external: the 3.12.10 archive URL and characterized archive/member
  identities came from the official PSF distribution. They remain inputs to be
  reproduced from the later owner-placed file, not current disk proof.
- Owner-set governance: `D-AROOT=approve-protected-attempt-family` and definitive
  Attempt-3 spend accounting (3/5 spent, 2 remain).

## Settled owner rulings

Attempts 4 and 5 use separate protected custody families:

| Attempt | Custody parent | Canonical campaign child |
| ---: | --- | --- |
| 4 | `C:\owner-controlled\project6-attempt-4` | `C:\owner-controlled\project6-attempt-4\sciencebase-campaign` |
| 5 | `C:\owner-controlled\project6-attempt-5` | `C:\owner-controlled\project6-attempt-5\sciencebase-campaign` |

Each family contains its authority envelope, GO, detached signature, and
attempt transcripts as sidecars of `sciencebase-campaign`. Each parent has a
protected inheritable owner-and-SYSTEM-only FullControl DACL. Each campaign
child has the protected non-inheritable owner-and-SYSTEM-only campaign-root
DACL. Python validation, ordinary/elevated current-SID parity, and complete
activation-stage absence/preservation and containment checks precede custody
creation; parent, child, and binding-parent validation precede `$P1_IexBegun`.

Bindings, W5 scratch, and worker roots remain outside those families. Preserve
all Attempts 1-3 residue and both archive versions; keep
`CampaignId=sciencebase-live-v2`, `reservation.db`, the query/item/file, schemas,
signing identity, and effect ordering unchanged. Attempts remain strictly
serial. Attempt 5 is a separately activated remaining attempt, not an automatic
retry authorized by this design.

## Decision

Use `-V:PythonCore/3.12` only to locate the installed vendor/minor runtime. Make
the frozen ambient executable size/hash and ZIP-member equality the sole
patch-level enforcement. The validate-only gate returns one verified absolute
interpreter path; the five governed initializer/template/live/closeout calls
invoke that exact path directly and never ask `project6.ps1` or `py.exe` to
resolve Python again.

The Python-binding portion retains the strict `python.exe` byte-equality design
and the post-provision comparison as defense in depth. A later owner decision must
confirm acceptance of its per-host-patch re-cure cost before implementation; a
decision to use a PSF-signed/same-minor/owner-ratified floor instead reopens this
design and is not silently inferred.

Use the protected attempt family to isolate each create-once reservation,
authority, GO, signature, and transcript namespace. Add a fail-closed,
phase-scoped cross-attempt action guard using the existing root-derived mutex
names without changing the production mutex derivation. It mechanically
serializes active governed actions in the same Windows session; the settled
one-action/no-concurrent-sitting rule governs the disclosed gaps between shells.

## Still owner-gated before sitting or broader implementation

- D2: re-pin the required `dual-live-windows-boundary` B0 fixture, including its
  archive URL/hash, from 3.12.6 to 3.12.10.
- D3/M7: confirm the strict executable-byte floor and accept its recurrence
  treadmill, or direct a separately reviewed relaxation.
- D4: re-prove archive `python.exe` equals the ambient executable in GREEN from
  the exact owner-placed archive.
- D5: place
  `C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip` without changing
  the retained 3.12.6 archive.
- Any implementation outside the approved minimum R4 tranche, external
  rehearsal, custody/governance write, land, push, elevation, signature, key
  access, network request, Attempt-5 activation, or live act requires its own
  later authority.

## Rejected alternatives

### Retain 3.12.6 and change the host

Installing or registering ambient 3.12.6 would modify the shared workstation.
Retaining an unconstrained minor locator without exact byte enforcement would
also preserve the original drift defect.

### Treat an exact patch launcher tag as the identity control

The target host proves `-V:PythonCore/3.12.10` is not registered. A launcher
tag cannot substitute for frozen executable bytes on this host.

### Re-resolve through `project6.ps1`

`project6.ps1` prepends `-` to `-PythonVersion` and invokes `py` independently.
Passing `V:PythonCore/3.12` through it would reopen the resolution gap after the
gate. The global wrapper remains unchanged; the five governed calls bypass it.

### Replace the direct worker re-hash or expand/elevate its ACL

Using only the binding-record hash weakens drift detection. Adding a redundant
interactive-user ACE would violate the exact six-ACE contract because the
existing broker RX ACE already is the owner's user SID; elevating Phase 1b would
mask the required broker-access proof. Keep the direct non-elevated re-hash,
explicitly bind current user to broker SID, and prove the real access path.

### Add a content-addressed ambient bootstrap subsystem

An absolute-path ambient bootstrap adds new custody and lifecycle surfaces. The
verified vendor/minor locator plus frozen bytes is narrower.

### Reuse the shared campaign/sidecar namespace

The reservation, envelope, and GO are create-once. Reuse would make Attempt-4
residue collide with Attempt 5 and would place new sidecars under a shared parent
whose ACL is not the approved attempt-family custody contract.

### Change the production mutex derivation or add a resident keeper now

A stable family-wide mutex could mechanically serialize roots, but it changes a
production effect-boundary identity and needs a new security/lifecycle contract.
A resident cross-shell keeper adds liveness, authentication, crash-recovery, and
terminal-state machinery. This cycle instead holds the unchanged root-derived
names for each complete governed action and retains strict operator seriality
between shells. Any requirement for host-global or mechanically continuous
attempt-lifetime exclusion reopens a separate design.

## Components

### 1. Validate-only Python binding gate

Add `scripts/validate-dual-live-python-binding.ps1`. It has one responsibility:
return a verified binding observation or fail closed without creating,
modifying, or deleting any filesystem object.

The script must:

1. Use `System.Diagnostics.ProcessStartInfo` under Windows PowerShell 5.1 with
   `UseShellExecute=$false`, `CreateNoWindow=$true`, and separately redirected
   stdout/stderr. Invoke `py.exe` with first argument exactly
   `-V:PythonCore/3.12`, followed by `-I -S -c` and
   `import sys; print(sys.executable)`. Read both redirected streams with
   `ReadToEnd()`, call `WaitForExit()`, and dispose the process. Do not use
   native PowerShell redirection (`2>&1` or `2>$null`) under
   `$ErrorActionPreference='Stop'`.
2. Require exit code zero, empty stderr, and exactly one non-empty stdout line
   containing an absolute `sys.executable` path. Any process-start exception,
   launcher diagnostic, extra/empty line, or malformed path maps to
   `python_binding_launcher_invalid`, never a raw `NativeCommandError`.
3. Require the interpreter leaf, archive leaf, and every existing ancestor up
   to their drive roots to be ordinary non-reparse filesystem objects on fixed
   local volumes. Resolve their rooted paths using the repository's existing
   exact-path helper pattern; reject rather than follow any reparse point.
4. Open the ambient executable once, read-only and without write/delete sharing.
   Require that handle to contain 104,952 bytes with SHA-256
   `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
5. Require the archive leaf name
   `python-3.12.10-embed-amd64.zip`, length 11,133,606, and SHA-256
   `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.
6. Open the ZIP once, read-only and without write/delete sharing; hash that
   handle and rewind it. Require exactly one case-insensitive match for
   `python.exe`, require its full name to be the exact case-sensitive string
   `python.exe`, and hash that member without extraction.
7. Require the member length/hash to equal the ambient length/hash. The
   vendor/minor launcher locator contributes no patch assertion; these frozen
   bytes and the member equality are the sole patch-level proof.
8. Return one structured PowerShell object containing status
   `PYTHON_BINDING_OK`, launcher tag exactly `-V:PythonCore/3.12`, interpreter
   path/root, archive
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

The production entry point accepts only `-PythonArchive`. Its internal launcher
and comparison functions accept a launcher executable, resolved paths, and
expected identities as test seams so Windows tests can use disposable
executables/files while exercising the production functions. The production
entry point passes only frozen constants; caller-configurable launcher,
version/hash/size identities, and member name are not exposed.

### 2. Worker pin

Update `scripts/provision-dual-live-worker.ps1` to pin:

- `PythonVersion = 3.12.10`;
- archive leaf `python-3.12.10-embed-amd64.zip`;
- official archive URL
  `https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip`;
- archive SHA-256
  `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.

Retain the current exact archive validation, content inventory, manifest,
content-addressed root, ACL hardening, binding schema, and final verification.
Do not add downloading to the provisioner.

Close the existing hash-to-extraction race. The provisioner must open the
archive once with `FileAccess.Read` and `FileShare.Read`, compute the pinned
length/hash from that handle, rewind it, and construct one read-mode
`System.IO.Compression.ZipArchive` over that same stream with the stream left
open. Windows PowerShell 5.1 must load
`System.IO.Compression` and `System.IO.Compression.FileSystem` explicitly with
`Add-Type` before using its
entry-extraction extension.

Before writing, validate the complete entry set. Reject absolute/rooted names,
empty file names, `.` or `..` traversal components, drive/colon forms,
case-insensitive duplicate destinations, and file-vs-directory prefix
collisions. Extraction must iterate that held archive's `Entries` and use
the PS5.1-compatible static extension call
`[System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destination, $false)`
for each file while the original stream and archive
remain open. `Expand-Archive`, `ZipFile.ExtractToDirectory(path,...)`, or any
other extraction API that reopens the archive by path is forbidden.

Preserve the existing topology: extract into the fresh
`stage-<guid>` directory, overlay the reviewed Git blobs, build the deterministic
inventory and manifest there, and only then `Move-Item` the stage to
`sha256-<manifest-digest>`. Place open/hash/rewind/validate/extract in one
production helper so executable Windows tests exercise the same code the
provisioner calls.

The extracted inventory and manifest remain the downstream proof of what was
written. Windows regressions must prove that a second opener cannot obtain
write/delete sharing and that replacement, rename, and deletion are denied with
the held stream open. They must also prove extraction bytes come from the held
`ZipArchive`, not a later path open; exercise traversal, case, and prefix
collisions; and statically forbid the path-taking extraction APIs above.

### 3. Attempt-family custody and phase-scoped action guard

Derive every remaining-attempt path from a fixed table; never independently
suffix individual sidecars:

| Surface | Attempt 4 | Attempt 5 |
| --- | --- | --- |
| custody parent | `C:\owner-controlled\project6-attempt-4` | `C:\owner-controlled\project6-attempt-5` |
| canonical root | `<parent>\sciencebase-campaign` | `<parent>\sciencebase-campaign` |
| authority envelope | `<parent>\sciencebase-authority.json` | `<parent>\sciencebase-authority.json` |
| GO / signature | `<parent>\owner-go.json` / `<parent>\owner-go.json.sig` | `<parent>\owner-go.json` / `<parent>\owner-go.json.sig` |
| transcripts | `<parent>\attempt4-elevated-transcript.txt`; `<parent>\attempt4-nonelevated-transcript.txt` | `<parent>\attempt5-elevated-transcript.txt`; `<parent>\attempt5-nonelevated-transcript.txt` |
| binding parent | `C:\owner-controlled\project6-bindings-4` | `C:\owner-controlled\project6-bindings-5` |
| W5 scratch | `C:\owner-controlled\project6-w5obs-4` | `C:\owner-controlled\project6-w5obs-5` |
| worker root | `C:\p6-sciencebase-worker-4` | `C:\p6-sciencebase-worker-5` |

The parent and campaign child are separate custody contracts. The future H4
packet freezes one `<expected-owner-sid>`; it cannot be supplied ad hoc at the
sitting. In both the ordinary pre-sitting shell and the fresh elevated shell, a
read-only token-identity gate obtains
`[Security.Principal.WindowsIdentity]::GetCurrent().User.Value`, requires one
nonempty SID equal by ordinal comparison to that frozen value, and emits no file
or registry state. Empty, malformed, unequal, or alternate-credential identity
is `sciencebase_owner_identity_mismatch` PRE-SITTING HOLD before custody,
binding-parent creation, or `$P1_IexBegun`. The parent descriptor has the
equivalent of
`O:<expected-owner-sid>D:P(A;OICI;FA;;;<expected-owner-sid>)(A;OICI;FA;;;SY)`:
protected DACL, exactly two explicit non-inherited Allow FullControl ACEs, both
`ContainerInherit,ObjectInherit`, for owner and SYSTEM only. The campaign child
has the equivalent of
`O:<expected-owner-sid>D:P(A;;FA;;;<expected-owner-sid>)(A;;FA;;;SY)`:
protected DACL, exactly two explicit non-inherited Allow FullControl ACEs with
no inheritance or propagation flags. The primary group is system-set and is
neither changed nor asserted by this contract.

All three custody directories receive their final descriptor in the same
creation operation. The production helper must call `CreateDirectoryW` through
a `SetLastError=true` P/Invoke with `SECURITY_ATTRIBUTES` carrying that exact
descriptor, require a true create result, and reread identity/security
immediately. `ERROR_ALREADY_EXISTS`, an unexpected error, or inability to prove
that this call created the directory is HOLD. `New-Item`, managed or native
parameterless creation followed by `Set-Acl`, or any create-then-harden/
pre-existing-success fallback is forbidden. This strengthens the H3
descriptor-at-creation precedent with atomic create-once detection; it is not
merely a final-state DACL assertion.

The selected attempt's external binding parent is a third create-once custody
contract. In the same elevated `NonRuntime` callback, after all pre-custody gates
and before `$P1_IexBegun`, create `project6-bindings-4` or
`project6-bindings-5` as an empty, ordinary, non-reparse directory on a fixed
local volume. It uses the same protected, owner-and-SYSTEM-only, inheritable
two-ACE DACL as the attempt parent. Verify rooted identity, stable file identity,
frozen owner SID, protection, exact ACE tuples, emptiness, and boundary
disjointness before profile provisioning. The profile provisioner never creates
this parent. Rehearsal uses a separately named binding parent with the same
contract. Failure after any binding parent is created but before
`$P1_IexBegun` is `PRE-BEGIN HOLD`: preserve it and require owner adjudication;
never repair its ACL, empty it, or reuse it automatically.

Its exact stage sets are closed. It is empty before profile provisioning; after
profile provisioning it contains only
`sciencebase-profile-<attempt-nonce>.json`; after worker provisioning it
contains exactly that leaf plus `sciencebase-worker-<attempt-nonce>.json`.
Both leaves are ordinary, non-reparse, create-once files whose rooted paths and
identities equal the provisioner outputs. A third child, a malformed/case-
colliding nonce leaf, or a stage-inconsistent absence is terminal `ATTEMPT
HOLD`; preserve the parent and do not delete or rename a child.

The later owner-authorized custody action creates the selected parent, child,
and binding parent create-once with those descriptors. The required order is:

1. in the ordinary pre-sitting shell, enter a non-runtime family guard and, while
   it remains held, run the frozen-owner-SID check, Python gate, and complete
   worktree/named-path/retained-residue state and boundary-aware containment
   comparisons for the selected activation stage;
2. close that guard and shell, then in the fresh elevated shell acquire a new
   non-runtime guard before repeating owner-SID parity, Python parity, and the
   complete comparisons;
3. while that same elevated guard remains held, atomically create only the
   separately authorized attempt parent, campaign child, and selected binding
   parent with their final descriptors in their respective creation calls;
4. verify all three rooted identities, ordinary/non-reparse type, fixed-local
   volume, owner, protected DACL, exact ACE set, emptiness/stage-allowed child
   set, and boundary disjointness;
5. repeat Python/custody validation before setting `$P1_IexBegun`; and
6. keep that guard held through profile/worker provisioning, post-provision
   checks, the two initializers, and durable Phase-1 record completion. That
   record is a fixed machine-readable block inside the elevated transcript
   listed in the path table; it is not a separate file or parent child. The
   fresh Phase-1b shell rehydrates only from that closed transcript plus the two
   binding leaves, and the terminal manifest preserves the transcript bytes.

The activation-stage comparison is explicit. Before Attempt 4, every Attempt-4
and Attempt-5 family, binding-parent, W5, worker, profile, and sidecar path must
be absent. Before a separately authorized Attempt 5, the complete sealed
Attempt-4 artifact vector must instead be present and byte-, identity-, and
security-identical to its terminal preservation baseline, while every Attempt-5
path remains absent. The two vectors must remain boundary-disjoint at both
stages. A present Attempt-4 artifact is never deleted, renamed, relabeled, or
required to become absent to activate Attempt 5.

Initially the parent's exact allowed child set is only
`sciencebase-campaign`, and that child is empty. Later checks use an explicit
stage-specific exact allowed set as the two transcript leaves, authority
envelope, GO, and signature are legitimately created. An unknown or omitted
child is a HOLD, not a reason to mutate the DACL or delete the child. Attempt 5
remains absent until separately activated. Never clean, rename, reuse, or delete
a failed attempt family.

### R4 SQLite custody correction

The campaign child's protected, non-inheritable D-AROOT descriptor is unchanged:

```text
O:<owner-sid>D:P(A;;FA;;;<owner-sid>)(A;;FA;;;SY)
```

ObjectInherit-only is rejected. The owner-host experiment proved that it creates
inherited, unprotected children that fail the unchanged durable `secure()`
oracle. Inheritance is therefore not an authority mechanism for either the
durable database or its transient journal.

During an open SQLite transaction, the only permitted transient entries are
`.reservation.db.<32-lowercase-hex>.tmp` and its exact `-journal` sibling;
`-wal`, `-shm`, master-journal, persistent-journal, or any other child is
forbidden. `PRAGMA journal_mode=DELETE` remains mandatory; WAL, PERSIST,
TRUNCATE, MEMORY, and OFF remain forbidden.

Durable and transient files use distinct security oracles:

1. After SQLite closes and before atomic publication, the pinned staging-file
   handle is re-secured with a full, replacement DACL using native
   `SetSecurityInfo`. Owner is the frozen owner SID and the descriptor is
   `D:P(A;;FA;;;<owner-sid>)(A;;FA;;;SY)`. Every prior, inherited, logon,
   Administrators, or unknown ACE is removed. The same pinned identity must then
   satisfy unchanged `secure() == (True, True, True)` before it is flushed and
   atomically published as `reservation.db`. Runtime transactions verify this
   posture before and after writes and never repair drift. Path-based `Set-Acl`,
   additive grants, and post-publication repair are forbidden.
2. Every dirty SQLite transaction runs synchronously under a duplicate
   thread-scoped impersonation token. Its `TokenUser` must equal the frozen
   owner; only the duplicate's `TokenOwner` and `TokenDefaultDacl` are set and
   read back as exactly two flag-zero FullControl allow ACEs for owner and
   SYSTEM. The process token is snapshotted and must remain unchanged. The scope
   starts before `sqlite3.connect`, remains through begin, mutation, journal
   observation, commit or rollback, and connection close, and restores and
   verifies the exact prior thread-token state in `finally`.
3. A dedicated transient-journal oracle runs after the first dirty write and
   before commit while SQLite is paused. Using no-follow handles without delete
   sharing, it proves the exact `<active-database-name>-journal` binding, direct
   parent, fixed-local volume, stable root/database/journal identities, ordinary
   non-reparse type, link count one, frozen owner, DACL protection flag false,
   and exactly two explicit non-inherited, non-inheritable flag-zero FullControl
   allow ACEs for owner and SYSTEM. It does not weaken or special-case the
   durable `secure()` oracle. A missing journal during a known dirty transaction
   is HOLD; after commit or rollback it must be absent.

The scope and journal oracle cover reservation initialization, GO consumption,
all three physical-request reservations, the terminal event, and closeout. An
existing-row/no-write branch may produce no journal and is handled separately.
Observer failure forces rollback and connection closure; it cannot permit
publication, reservation success, egress, or automatic retry. A residual or
inaccessible journal is terminal HOLD and is preserved rather than deleted to
make a later check pass.

Stable R4 failure classifications are:

```text
reservation_birth_token_invalid
reservation_birth_token_restore_failed
reservation_database_resecure_failed
reservation_database_security_invalid
reservation_journal_missing
reservation_journal_binding_invalid
reservation_journal_security_invalid
reservation_journal_cleanup_indeterminate
```

Initialization maps them to `LiveReadinessHold`; runtime maps them through the
existing `ReservationHold/HOLD` boundary. Required non-live Windows coverage
runs the same complete lifecycle under ordinary and elevated owner contexts,
with zero skips in each context. It proves source-token immutability, duplicate
owner/default-DACL correction, thread-token restoration, durable owner and DACL
replacement, every journal's birth posture and disappearance, and absence of
WAL/SHM or unknown children. Negative cases reject durable extra/inherited/
unprotected ACLs and transient extra/inherited/deny/logon ACLs with the exact
HOLD code and no publication, egress, automatic repair, or retry. Real elevated
execution remains separately owner-authorized and is required before Attempt 4.

At Attempt-4 closeout or HOLD, the head-bound runbook emits exactly one
machine-readable disposition line to the selected non-elevated transcript before
`Stop-Transcript`. Its top-level fields are limited to `attempt`,
`phase_flags`, `disposition`, and `source_head`; `attempt` is 4,
`source_head` is the exact reviewed head, the phase flags are derived from
durable evidence, and the disposition is the already-determined Attempt-4
outcome. Tests require exactly one such line. It is evidence only: it grants no
recovery, retry, or future-attempt authority and has no canonical serializer,
release frame, recovery parser, sidecar, or receipt subsystem.

Attempt-5 activation and any abandoned-chain / missing-release adjudication
require a separately-designed, owner-gated durable proof designed against its
real consumer; out of scope here.

Add `scripts/invoke-dual-live-family-guard.ps1` as a Windows action wrapper, not
a `validate-*` action. Its production root table is fixed, in one global order,
to the retained shared canonical root and the Attempt-4/5 canonical roots with
`CampaignId=sciencebase-live-v2`; callers cannot add, omit, duplicate, or reorder
a root. It reproduces the production `_mutex_name` normalization and SHA-256
algorithm. Its only modes are:

- `NonRuntime`: create and hold all three derived names for the complete action;
- `LiveRuntime`: require `CurrentRoot` to equal the selected Attempt-4 or
  Attempt-5 canonical root, create and hold the other two names, prove the
  current name absent, then invoke the exact `$Py` live command inside the same
  callback. The unchanged Python boundary performs the authoritative atomic
  creation of the current-root mutex before GO consumption or worker creation.

For every name the wrapper uses a P/Invoke declaration with `SetLastError=true`,
sets the calling thread's Win32 last-error value to zero immediately before
`CreateMutexW(NULL, FALSE, name)`, and reads `GetLastWin32Error()` immediately
afterward. A newly created handle is retained for the entire callback.
`ERROR_ALREADY_EXISTS` closes that handle and every partially acquired handle in
reverse order, never enters the callback, and yields
`sciencebase_attempt_family_active` HOLD. A null handle, access
denial, wrong named-object type, unexpected result, empty table, or name-parity
failure closes the partial lease and yields
`sciencebase_attempt_family_guard_indeterminate` HOLD. It never waits or steals.

The P/Invoke helper uses null security attributes, `bInitialOwner=FALSE`, and
non-inheritable raw handles retained by a strongly referenced lease. Cleanup is
reverse-order `CloseHandle` in `finally`, followed by `GC.KeepAlive(lease)`; it
never uses `WaitOne`, `ReleaseMutex`, handle ownership, inheritance, or
finalizer-dependent cleanup. Every `CloseHandle` result is checked; cleanup
attempts every retained handle exactly once even after an earlier close failure.
Any false return or exception yields
`sciencebase_attempt_family_guard_release_failed`, never reports the lease as
released, and never re-enters the callback. The action's exact exit/HOLD
semantics survive the wrapper, and callback failure still attempts the entire
lease cleanup.

In `LiveRuntime` mode, `OpenMutexW(SYNCHRONIZE, FALSE, currentName)` is only an
early absence probe: found means `sciencebase_attempt_family_active`; access
denial, wrong type, or unexpected error is indeterminate; only
`ERROR_FILE_NOT_FOUND` permits the callback. A current-root race after that
probe remains safe because the unchanged production `CreateMutexW` rejects
`ERROR_ALREADY_EXISTS` before GO consumption. Never describe the probe alone as
the exclusion mechanism. A successful probe handle is closed and its close
result checked before either returning HOLD or proceeding; the callback cannot
run while that probe handle remains open. Probe-close failure uses the release-
failed code above.

Executable parity tests compare every PowerShell-derived name with the real
Python `_mutex_name` result and inject stale `ERROR_ALREADY_EXISTS` before a
new-name acquisition to prove the explicit clear prevents misclassification.
The non-runtime guard encloses each complete custody/provisioning/initialization
and closeout action. One fresh Phase-1b `NonRuntime` callback spans rehydration,
both Phase-2 checks, W5, and unsigned-template emission without an unguarded gap.
The live guard encloses the direct live `$Py` call. Handles are not transferred
between elevated and non-elevated shells; each fresh shell reacquires a complete
guard before its governed action. Thus active actions are mechanically serial
within the production `Local\` namespace, while inactive shell-transition gaps
remain governed by the one-action-at-a-time runbook and no-concurrent-sitting
rule. This design makes no host-global, cross-session, or mechanically
continuous attempt-lifetime claim. Such a requirement needs separately reviewed
`Global\` or durable-state coordination rather than a hidden keeper.

### 4. Readiness and exact interpreter flow

Update `next_milestone_plans/sciencebase-live-readiness.md` so its first two
validate-only Python gates run before nonce creation, custody, profile creation,
or worker provisioning. Remove every independent `py -3.12`,
`py -V:PythonCore/3.12`, `$PythonLauncherTag`, and ScienceBase
`-PythonVersion` flow. Each phase requires
`status -ceq 'PYTHON_BINDING_OK'` and sets `$Py` from that gate result's
`ambient_interpreter`.

Repath the shared campaign root at exact targets
`next_milestone_plans/sciencebase-live-readiness.md:295`, `:360`, `:390-391`,
`:444`, `:501`, `:509`, and `:572` to the selected table-derived attempt family.
Delete that file's create-then-verify/idempotent-rerun instructions at
`:321-328` and the `:417` statement that rerunning is idempotent; pre-existing
success is forbidden by the atomic create-once custody contract.

The head-bound runbook's two Phase-2 `pytest` commands and W5 block consume
call 4's verified `$Py` in the same fresh Phase-1b shell. They are an explicit
auxiliary allowlist, not governed production calls. They must not invoke
`py`, `python`, `project6.ps1`, carry `$Py` across shells, or resolve a
minor prefix independently.

Correct the stale ProgramData sentence in readiness and the later runbook.
Reservation and authority initializers do not touch ProgramData;
`OneUseLiveGoConsumer` first reaches it during GO consumption through
`SpentMarkerStore`, whose Windows backend securely creates missing managed
directories. This corrects existing effect ownership. The Attempt-4 slice must
leave `SpentMarkerStore.claim_exact` byte-for-byte unchanged: add no parameter,
expectation object, PRESENT branch, or new behavior. Attempt 4 retains the
existing ABSENT/secure-create-new behavior.

Repeat the validate-only Python gate exactly six times:

1. fresh ordinary pre-sitting shell, before remaining-attempt custody;
2. fresh elevated parity-precheck shell, also before custody;
3. elevated Phase 1 after custody validation but before `$P1_IexBegun`;
4. fresh non-elevated rehydration shell before template emission;
5. immediately before a separately authorized signed-live invocation; and
6. immediately before closeout after the one live invocation terminates.

Use `$Py` directly for exactly five governed Python tool invocations:
reservation initializer, authority initializer, unsigned template, signed live,
and no-live closeout. Derive absolute tool paths from the verified repository,
validate them, preserve argv without wrapper-only `--`, inspect
`$LASTEXITCODE` immediately, and restore location and
`DUAL_LIVE_RUNTIME_ENABLED` in `finally`. None may call `project6.ps1` or
`py.exe`; the global wrapper remains unchanged.

Retain the elevated post-provision ambient-root/length/hash comparison. Require
the current user SID to equal both profile and worker `broker_sid` values and
the worker DACL to retain exactly six unique ACEs with broker RX mask
`0x001200A9`. Any ambient/worker mismatch is terminal `ATTEMPT HOLD`,
definitively spends the attempt, and preserves all bytes. Any broker-SID or DACL
mismatch at that same post-provision gate is explicitly the same terminal
`ATTEMPT HOLD`, with the attempt spent and no continuation or reuse.

Before Attempt-4 custody, the ordinary shell validates and directly hashes the
retained Attempt-3 bundle with current SID equal to both broker SIDs. Phase 1b
repeats current/frozen-owner/broker equality, full bundle validation, and direct
worker hashing in a fresh non-elevated shell. Do not substitute a binding hash
or elevate Phase 1b.

Python-gate dispositions are fixed: calls 1-2 are `PRE-SITTING HOLD`; call 3
is `PRE-BEGIN HOLD`; call 4 is terminal `ATTEMPT HOLD`; call 5 is terminal
`SIGNED-AUTHORITY HOLD`; call 6 is `POST-LIVE CLOSEOUT HOLD`. Guard failures
map by the same phase boundary. Before callback entry no governed effect occurs;
after signed-live callback entry the durable live result controls the
signed-authority versus post-live disposition. No timeout, stale-lease
inference, automatic repair, reuse, or second close attempt is allowed.

### 5. Disposable integrated rehearsal before Attempt 4

Under separate owner authority for elevation and external persistent writes,
run the reviewed Phase-1-through-template path in a unique protected family
disjoint from all real and retained paths. Use distinct bindings, W5 scratch,
worker root, profile, connector-run ID, GO ID, and transcripts.

The rehearsal must hold the correct family guard across each action; pass
ordinary/elevated frozen-owner and Python gates; atomically create and verify the
parent, campaign child, and binding parent; provision the real profile and
3.12.10 worker; prove ambient/worker and broker/current-user equality; initialize
reservation plus authority; and capture the live DELETE-mode SQLite journal's
frozen ordinary/non-reparse/single-link/same-volume owner/DACL posture. First
initialization succeeds and same-path repetition returns create-once HOLD with
unchanged bytes and no staging or journal residue; it is not idempotent success.

After closing elevation, a fresh non-elevated guarded phase repeats identity,
bundle, hash, authority, and reservation checks and emits the unsigned template
through the gate-returned `$Py`. A second same-path template call must fail
create-once with unchanged bytes and clean runtime state. Before/after manifests
prove the real Attempt-4/5 vectors, Attempts 1-3 residue, both archives, and
`C:\ProgramData\Project6` unchanged.

No private key, signature, GO consumption, spent-marker write, network request,
live invocation, or closeout occurs. Preserve the rehearsal as explicitly
non-authoritative evidence; never delete or reuse it.

### 6. External archive prerequisite

The owner later places
`C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip` from
`https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip`.
Do not remove, overwrite, rename, or reuse the retained 3.12.6 archive. After
placement and verification, both archives are immutable retained inputs.

## Verification

Use staged RED then GREEN. First prove the gate's missing interface and
synthetic mismatch; then exercise its inert production functions. Before the
composition RED, fresh ordinary and elevated PS5.1 shells must resolve
`-V:PythonCore/3.12` with zero exit, empty stderr, one absolute path, and the
frozen ambient size/hash. Route valid ambient 3.12.10 and retained official
3.12.6 member identities through the comparison seam so only
`python_binding_mismatch` fails.

Readiness/topology RED must name the shared-root hardcodings above, wrapper
re-resolution, the missing explicit broker/DACL disposition, action calls
outside guards, missing owner-SID parity, insecure binding custody, and the
specific idempotent-rerun sentence. Cross-token coverage must prove the real
broker/current-user can fully validate and hash the exact six-ACE bundle from a
filtered non-elevated token; a filtered token with no matching enabled principal
and no backup/restore privilege must be denied.

The no-mutation proof uses two exhaustive, printed, counted vectors. A literal
`$MutationVector` derives the complete Attempt-4/5 table and a frozen retained
table. Its recursive retained roots are:

- `C:\owner-controlled\project6` after D5 placement;
- `C:\owner-controlled\project6-bindings` and
  `C:\owner-controlled\project6-bindings-3`;
- `C:\owner-controlled\project6-w5obs` and
  `C:\owner-controlled\project6-w5obs-3`; and
- `C:\p6-sciencebase-worker-2` and `C:\p6-sciencebase-worker-3`.

Independently hash the eight exact governance carriers below the canonical
`state\agent-inbox` root: plan of record, sitting runbook, Q12 index, owner
decision sheet, amendment addendum, forward map, continuation handoff, and audit
ledger. Also recursively hash the four historical roots
`session-8e8b798b-archive`, `session-9ee3527a-adversarial-pass`,
`characterization-record-2026-08-13`, and
`characterization-record-2-2026-08-14`.

Enumerate as load-bearing leaves the Attempt-1 phase record and stranded profile
binding; Attempt-2/3 elevated transcripts; shared campaign and both archives;
Attempt-2 profile binding; Attempt-3 profile and worker bindings; every retained
binding's resolved `appcontainer_profile_root`; both remaining-attempt families
and sidecars; both bindings/W5/worker roots; ProgramData; and the ambient
executable. The Attempt-4 must-remain-absent set includes the Attempt-3
non-elevated transcript, shared-root reservation/envelope/GO/signature leaves,
ProgramData, and every Attempt-4/5 table-derived path before activation.
Wildcards, category-only claims, guessed counts, unresolved profiles, or
unclassified children HOLD.

A separate exhaustive `$WorktreeVector` parses one successful
`git worktree list --porcelain`, rejects malformed/duplicate records, qualifies
non-drive paths against `C:\`, sorts them, and prints/asserts the actual count
and roots. Every new family/binding/W5/worker/rehearsal/scratch path is compared
with every worktree and named repository/ceremony root using boundary-aware
equal/ancestor/descendant rejection.

For every worktree capture path, HEAD, branch/detached state, full NUL-delimited
porcelain, raw binary working-tree and index diffs, and a deterministic
type/length/SHA manifest of every untracked path without following reparse
points. For each external manifest entry capture existence, rooted type,
reparse data, volume/file identity, link count, creation/last-write times,
content length/hash, owner SID, DACL protection/SDDL, and sorted ACE tuples.
Exclude last-access time, SACL, and primary group. Before/after vectors and
regenerated counts must be identical; validate-only actions seed nothing.

Automated coverage must prove:

- no exact-patch launcher selector; only the vendor/minor locator plus frozen
  size/hash and archive-member equality;
- exact 3.12.10 re-pins in the provisioner, readiness, Playwright setup/archive/
  worker literals, `tests/test_dual_live_worker_provisioner.py:18-19`, and
  `backend/tests/test_ci_coverage_completeness.py:258-260`;
- exactly six gate calls, five governed direct-`$Py` calls, and the call-4
  auxiliary pytest/W5 allowlist, with fixed phase dispositions;
- PS5.1 executable capture, stable failure codes, one success object, closed
  production parameters, reparse/path/ZIP collision rejection, held-stream
  extraction, and unchanged stage-to-manifest-to-content-addressed move;
- atomic custody DACL creation, exact binding-child stages, broker/ACL proof,
  create-once initializer/template behavior, pinned durable database re-securing,
  thread-scoped journal birth security, and the dedicated transient oracle;
- guard name parity/order, stale-error clearing, nonruntime/live composition,
  collisions, partial acquisition, cleanup, noninheritance, forced-GC/crash,
  cross-token behavior, and the disclosed same-session boundary; and
- exactly one four-field Attempt-4 disposition line, with no receipt, recovery,
  second-stage framing, golden fixture, or future-attempt parser.

Run focused readiness, provisioner, runtime, elevated-ACL, Python-binding, and
family-guard suites under PS5.1 with cache/bytecode generation disabled. Wire
`tests/test_dual_live_python_binding.py` and
`tests/test_dual_live_family_guard.py` into the required
`dual-live-windows-boundary` job with zero skips; re-pin that job's B0 runtime
and archive to exact 3.12.10. Real-host GREEN requires the ordinary/elevated free
gates, retained-bundle validation, and the separately authorized integrated
rehearsal; none authorizes real custody or live execution.

## Preservation, governing records, and refreeze

Preserve every Attempt-1/2/3 transcript, packet, carrier, freeze, binding,
worker, W5, profile/AppContainer, campaign artifact, and named residue; the
shared campaign; the 3.12.6 archive; and, after D5/D4, both archives. Archive
placement is the only planned shared-parent change before the preservation
baseline. Later writes go only to the selected protected family or separately
named external roots.

Attempt 4 uses the complete table-derived topology and wholly fresh nonce,
profile, bindings, AppContainer identity, connector-run ID, worker manifest,
Phase-1 record, envelope, GO/template/digest, and—only if separately
authorized—signature. Failed Attempt-4 state is preserved. Attempt-5 activation
and any abandoned-chain or missing-release durable proof remain separately
owner-gated and out of scope; no Attempt-4 namespace or authority is reusable.

The canonical record root is
`C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox`.
H3b is exhaustive only over its closed eight-carrier set, not the directory.
Attempt-3 packet/freeze/evidence/carrier bytes remain historical and immutable.

A separately authorized head-independent correction records Attempt 3 SPENT,
3/5 spent and 2 remaining, exact fail-closed cause, preserved residue, and no
GO/signature/consumption/network/live act, without inventing H4. Only after
reviewed implementation and a fresh exact-head land/push token may head-bound
records add H4 commit/blob/ranges, tests, CI, owner-host receipts, freeze,
packet, and carrier. The plan and forward map remain unchanged absent a real
semantic contradiction.

A later freeze hashes all eight raw carrier files in canonical order, recording
lowercase SHA-256 and raw length without encoding/EOL normalization. Use actual
dates in a fresh `packet-attempt4/S6-H4-FREEZE-RECORD-<date>.md`; never hash
the freeze into itself or overwrite a freeze. Generate a fresh Attempt-4 packet,
carrier status, AST/synthetic evidence, independent dual review, and actual
named/worktree counts. Every identity binds H4 and Attempt 4 and states exactly
3 of 5 spent, 2 remain. No prior land token, packet approval, Q12 attestation,
GO, signature, or Attempt-5 permission transfers.

## Non-goals and acceptance

No global Python manager/installation or `project6.ps1` change; no schema,
query/item/file, signer, credential, egress, effect-order, broker-order,
AppContainer, or campaign-subject change; no binding-only hash substitute,
seventh ACE, or elevated Phase 1b. No claim that the launcher tag pins a patch,
that `python.exe` proves the full ambient closure, that Python validation covers
custody/ACL/initializer/guard behavior, or that the `Local\` guard is
host-global or continuous. No deletion, cleanup, rename, or reuse of historical,
failed, or rehearsal evidence.

Acceptance requires one-spec-file local change; consistent D-AROOT and 3/5
accounting; validate-only frozen-byte proof before mutation; six fixed gates,
five direct-`$Py` governed calls, and explicit broker/DACL terminal disposition;
exact 3.12.10 pin and held-stream extraction; complete disjoint attempt vectors
with atomic custody; exhaustive mutation/worktree receipts; guard parity,
full-callback exclusion, cleanup, and honest scope; filtered-token broker proof;
the full exact-host rehearsal; preserved Attempts 1-3 and governing bytes; one
minimal Attempt-4 disposition record; and no future-attempt recovery or
ProgramData consumer machinery.

D2-D5, exact-host elevated GREEN, rehearsal, implementation beyond the approved
minimum R4 tranche, governance writes, land/push, signing, key, network, live
acts, and Attempt-5 activation remain separately owner-gated. No later test
success is a GO, land token, signature authority, Attempt-5 activation, or live
authority.

Reopen before implementation if the locator or token parity diverges; the
owner-placed archive/member hashes fail; non-elevated broker validation fails;
the exact create-once/journal rehearsal fails; guard parity/exclusion/cleanup
fails; retained/worktree vectors or AppContainer roots cannot be resolved;
3.12.10 tests drift; the owner selects the relaxed D3/M7 floor; or a canonical
record proves Python 3.12.6 itself is mandatory.
