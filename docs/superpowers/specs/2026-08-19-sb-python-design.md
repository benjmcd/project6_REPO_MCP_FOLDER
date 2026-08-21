# ScienceBase Python Binding Correction

Status: R2 revised and independently reviewed; implementation remains owner-gated, 2026-08-20

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

This specification authorizes no implementation, custody creation, governing-
record write, land, push, elevation, signing, key access, network access, W5
observation, or live ScienceBase execution. Its own revision may change only
this file and may be committed locally in the isolated specification lane.

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

This R2 specifies the strict `python.exe` byte-equality design and retains the
post-provision comparison as defense in depth. A later owner decision must
confirm acceptance of its per-host-patch re-cure cost before implementation; a
decision to use a PSF-signed/same-minor/owner-ratified floor instead reopens this
design and is not silently inferred.

Use the protected attempt family to isolate each create-once reservation,
authority, GO, signature, and transcript namespace. Add a fail-closed,
phase-scoped cross-attempt action guard using the existing root-derived mutex
names without changing the production mutex derivation. It mechanically
serializes active governed actions in the same Windows session; the settled
one-action/no-concurrent-sitting rule governs the disclosed gaps between shells.

## Still owner-gated before implementation or sitting

- D2: re-pin the required `dual-live-windows-boundary` B0 fixture, including its
  archive URL/hash, from 3.12.6 to 3.12.10.
- D3/M7: confirm the strict executable-byte floor and accept its recurrence
  treadmill, or direct a separately reviewed relaxation.
- D4: re-prove archive `python.exe` equals the ambient executable in GREEN from
  the exact owner-placed archive.
- D5: place
  `C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip` without changing
  the retained 3.12.6 archive.
- Any implementation, external rehearsal, custody/governance write, land, push,
  elevation, signature, key access, network request, Attempt-5 activation, or
  live act requires its own later authority.

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
`System.IO.Compression.FileSystem` explicitly with `Add-Type` before using its
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
| owner-adjudication receipts | `<parent>\owner-adjudication-<receipt-nonce>.json` (closed cumulative set; owner recovery only) | `<parent>\owner-adjudication-<receipt-nonce>.json` (closed cumulative set; owner recovery only) |
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
envelope, GO, and signature are legitimately created. Each separately
authorized adjudication invocation adds exactly one new nonce-bound receipt
leaf to a closed cumulative set. Its recovery packet enumerates complete
manifest entries for every prior receipt leaf and fixes the one new nonce; the
action must prove that exact prior set before creating the new leaf. Partial,
complete-but-unused, and previously consumed receipts all remain immutable
members of that set. A filename pattern, glob, count, or unenumerated leaf never
authorizes a child. An unknown or omitted child is a HOLD, not a reason to
mutate the DACL or delete the child. Attempt 5 remains absent until separately
activated. Never clean, rename, reuse, or delete a failed attempt family.

The campaign child's stage-specific set is equally exact at callback boundaries.
During the open SQLite transaction, the only permitted transient entries are
`.reservation.db.<32-lowercase-hex>.tmp` and its exact `-journal` sibling;
`-wal`, `-shm`, or any other child is forbidden. After success it contains only
`reservation.db`. Success, expected create-once failure, and ordinary failure
must leave neither staging nor journal leaf. `custody_cleanup_indeterminate`,
multiple/malformed staging names, or a residual staging/journal leaf is terminal
`ATTEMPT HOLD`; preserve the family and do not delete the residual to make a
later check pass.

While the DELETE-mode `-journal` exists, an observer/test hook must prove it is
an ordinary, non-reparse, single-link file in the same directory and on the same
volume as its staging database. It must capture owner SID, DACL protection,
ordered SDDL, and sorted ACE tuples and compare them with a frozen safe posture
characterized from the reviewed Windows/SQLite build before Attempt 4. A journal
that is inaccessible, reparse-backed, cross-volume, multiply linked, or has an
uncharacterized/insecure owner or DACL invalidates this strategy and reopens the
design; final disappearance alone is not proof that the transient was safe.

Attempt-5 activation requires an authoritative Attempt-4 terminal preservation
chain; a fresh H5 census cannot retroactively become that baseline. Add
`scripts/seal-dual-live-attempt.ps1` as an explicit writing action. It writes no
new sidecar: the carrier is the table-derived non-elevated transcript after
`Stop-Transcript` has closed it. The chain has two append-only records in that
same carrier so the durable artifact baseline precedes mutex cleanup while the
final record can truthfully report cleanup.

The public production entry point accepts the fixed Attempt-4/5 selector,
`Mode` in `NORMAL` or `OWNER_ADJUDICATION`, and `Disposition` in the closed set
below. Its normal parameter set accepts nothing else. The owner-adjudication
parameter set additionally requires exactly one `-OwnerAdjudicationReceipt`
path under the selected attempt parent. Except for that narrowly validated
receipt, it derives every carrier, root, path, manifest observation, identity,
hash, and encoding value from the fixed table and disk and rejects caller-
supplied versions. `OWNER_ADJUDICATION` and the receipt parameter are absent
from ordinary H4/H5 and may appear only in a newly owner-authorized recovery
packet. Internal functions may accept resolved disposable paths as executable
test seams; those seams are not production parameters. Tests prove normal mode
cannot enter an adjudication branch; an adjudication-originated `BASELINE` can
emit only `OWNER_ADJUDICATED_ABANDONED_SPENT`. A recovery invocation emits only
a `RELEASE` and must preserve the referenced baseline's disposition.

#### Owner-adjudication receipt

Owner adjudication is authorized by a create-once receipt, never by `Mode`
alone. Add `scripts/new-adjudication-receipt.ps1` as the separate owner-gated
receipt action. Its leaf is exactly
`<attempt-parent>\owner-adjudication-<receipt-nonce>.json`, where the nonce is
32 lowercase hex, is fixed by the owner recovery packet, and matches the record.
Its production inputs are only that packet's fixed attempt selector, receipt
nonce, operation, disposition, and exact `CanonicalJsonV1` prior-receipt
manifest plus its SHA-256. The packet, not a live caller, fixes that sorted
manifest. The action derives every current carrier and receipt field and rejects
an added, omitted, reordered, or disk-divergent prior entry. It first requires
its current SID to equal the frozen owner SID and proves every prior receipt is
an ordinary, non-reparse, single-link same-volume file with the frozen owner and
exact protected owner/SYSTEM DACL. A prior receipt's bytes may be partial or
otherwise unusable as authority; its complete manifest entry still preserves
and binds that residue.

The creator forms the complete canonical bytes in memory before mutation, then
uses `CreateFileW(CREATE_NEW)` with no sharing and `SECURITY_ATTRIBUTES`
carrying a protected non-inheritable DACL with exactly owner and SYSTEM
FullControl. It performs checked full `WriteFile` progress, calls
`FlushFileBuffers`, closes, reopens read-only with no sharing, and verifies the
exact raw bytes, canonical re-encoding, SHA-256, volume/file identity, link
count, owner, and DACL. Only that durable reread returns a validated receipt
handle/result to the terminal action in the same guarded invocation.
`scripts/seal-dual-live-attempt.ps1` never creates, replaces, hardens, or edits
it.

The nonce is single-invocation authority. If a receipt leaf demonstrably exists
after any creator or downstream failure, however partial, it is preserved and
`CREATE_NEW` mechanically rejects that nonce on a later invocation; the leaf is
never truncated, completed, replaced, deleted, or reused. If the leaf is
authoritatively absent and the carrier unchanged, there is no durable replay
marker. If leaf existence/recheck or carrier state is indeterminate, the current
action is HOLD. In either latter case the packet is one-shot only as a governance
rule and any later invocation requires newly granted owner authority with a fresh
nonce; no filesystem-enforced later rejection is claimed. Every later packet's
exact prior-receipt manifest includes every then-existing leaf. Failure before a
provably durable receipt may therefore consume an attempt at adjudication, but
cannot silently broaden authority or brick the namespace behind an exact-one-
receipt rule.

The head-bound recovery command encloses receipt creation, immediate validation,
current-vector comparison, and any `BASELINE` append in one fresh all-three-name
`NonRuntime` callback. There is no shell or guard gap between receipt prefix
capture and the governed baseline/recovery validation. As with a normal chain,
only the bound `RELEASE` is appended after that guard reports cleanup.

Its raw content is `CanonicalJsonV1` with no BOM or newline and exactly these
keys: `attempt`, `baseline_line_sha256`, `carrier_path`,
`carrier_prefix_length`, `carrier_prefix_sha256`, `disposition`, `operation`,
`owner_sid`, `prior_receipts`, `prior_receipts_sha256`, `receipt_generation`,
`receipt_nonce`, `schema`, `source_head`, and `status`. `schema` is
`project6.sciencebase_attempt_adjudication.v1`; `status=OWNER_AUTHORIZED`;
`attempt`, owner SID, source head, and carrier path equal the selected frozen
values. Prefix length/hash bind every current carrier byte, using zero and
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
when the carrier is absent.

`prior_receipts` is the packet-fixed sorted array of complete `FILE/FULL`
manifest entries for every pre-existing adjudication-receipt leaf under this
attempt parent. It excludes the new leaf. `prior_receipts_sha256` hashes
`CanonicalJsonV1(prior_receipts)`, and `receipt_generation` is the positive
integer `prior_receipts.length + 1`. Duplicate or case-colliding paths, an entry
outside the selected parent, a nonce not matching its leaf, or any other
receipt-like child absent from this array is HOLD before create.

`operation` is exactly `CREATE_ABANDONMENT_CHAIN` or
`RECOVER_MISSING_RELEASE`. The first requires null `baseline_line_sha256` and
`disposition=OWNER_ADJUDICATED_ABANDONED_SPENT`. The second requires the exact
lowercase SHA-256 of a valid baseline-only final frame and copies that
baseline's disposition, including a normal disposition. The receipt action
derives carrier fields from an exclusive read; the owner supplies no hash,
prefix, or current-receipt identity value. The prior-receipt hash is accepted
only as part of the packet's closed authority manifest and must reproduce from
disk.

Before any adjudication write, the terminal action accepts only the freshly
created validated handle/result from the same guarded invocation; an existing
path supplied to a later invocation is never authority. It revalidates direct-
child containment, leaf/nonce equality, ancestor and leaf non-reparse state,
file/volume identity, link count one, frozen owner, protected DACL, exact
owner/SYSTEM ACEs, exact canonical raw bytes, SHA-256, generation, and complete
prior-receipt set. It then requires attempt/head/carrier/current-prefix/
operation/disposition/baseline bindings to match the requested transition. It
rejects a wrong attempt, head, prefix, carrier, operation, disposition, reused
nonce/digest, or receipt already named by any terminal frame. Owner-mode
baseline manifests include every prior receipt plus the new receipt. Recovery
`RELEASE` records bind the post-baseline receipt delta defined below. The
validated receipt handle remains open with no write/delete sharing through the
corresponding durable terminal frame and reread. Thus replay, cross-attempt use,
wrong-prefix recovery, and a bare owner-mode flag all HOLD without carrier
mutation.

Normal mode opens the existing transcript with `FileMode.Open`, read/write
access, and `FileShare.None`. Missing carrier is HOLD with no file creation or
other mutation. Only separately owner-authorized adjudication may use
`FileMode.CreateNew` when the carrier is absent. Its exact initial bytes are
`EF BB BF || UTF8("PROJECT6 ATTEMPT TERMINAL-ONLY TRANSCRIPT V1\r\n")`—the
three-byte UTF-8 BOM, the shown ASCII text, and bytes `0D 0A`. Existing carriers
are never replaced. This fixed header is not used by normal mode.

#### Terminal framing and canonical JSON

Each record is one ASCII frame:

`@@PROJECT6_ATTEMPT_TERMINAL_V1@@:<kind>:<length>:<base64url>\r\n`

`<kind>` is exactly `BASELINE` or `RELEASE`; `<length>` is the nonzero decoded
JSON byte length as base-10 ASCII with no sign or leading zero; `<base64url>` is
unpadded RFC 4648 base64url of those exact bytes; and the terminator is bytes
`0D 0A`. Length mismatch, padding, noncanonical base64url, invalid UTF-8,
duplicate JSON keys, unknown/missing keys, or a decoded value that does not
re-encode to the identical frame is malformed.

`CanonicalJsonV1` permits only objects, arrays, strings, signed 64-bit integers,
booleans, and null; floats are forbidden. Object keys are unique and emitted in
`StringComparer.Ordinal` order. There is no whitespace or BOM. Integers use
minimal base-10 form; literals are lowercase. Strings reject unpaired
surrogates, encode as UTF-8, escape quote and reverse solidus as `\"` and `\\`,
use `\b`, `\f`, `\n`, `\r`, and `\t`, encode every other U+0000-U+001F code
point as lowercase `\u00xx`, and do not escape other Unicode. These rules apply
recursively to every nested object. SHA-256 means lowercase 64-character hex of
the named exact raw bytes, without a prefix.

The exact `BASELINE` object key set is:
`accounting`, `attempt`, `campaign_id`, `disposition`, `identities`, `manifest`,
`manifest_sha256`, `mode`, `owner_sid`, `paths`, `phase_flags`, `program_data`,
`record_type`, `schema`, `source_head`, `status`, and `transcript_prefix`.
`schema` is `project6.sciencebase_attempt_terminal.v1`; `record_type` is
`BASELINE`; `status` is `BASELINE_SEALED_PENDING_RELEASE`; `attempt` is integer
4 or 5; `campaign_id` is exactly `sciencebase-live-v2`; `mode` is the selected
mode; `owner_sid` is the frozen SID;
`source_head` is exactly 40 lowercase hexadecimal characters.

`accounting` has exactly integer keys `attempts_total`, `spent_before`,
`spent_after`, and `remaining_after`, plus Boolean `current_attempt_spent`.
They equal `(5,3,4,1,true)` for Attempt 4 and `(5,4,5,0,true)` for Attempt 5.
Every terminalized namespace is conservatively spent; a different accounting
tuple is malformed and requires a new owner ruling, not a caller override.

`phase_flags` has exactly these Boolean keys in monotonic order:
`custody_created`, `p1_iex_begun`, `authority_created`,
`go_template_created`, `go_signed`, `go_consumption_entered`,
`live_terminal_durable`, and `closeout_terminal_durable`. Each true value must
be derived from the named durable transcript/artifact receipt and each false
value from proven absence; later true implies every prerequisite to its left
except that `authority_created` and `go_template_created` are separately
create-once and both require `p1_iex_begun`. `go_signed` requires both;
`go_consumption_entered` requires `go_signed`; `live_terminal_durable` requires
GO consumption; and `closeout_terminal_durable` requires a live terminal.

`disposition` is exactly one of:

- `ATTEMPT_COMPLETED_SPENT`: normal mode, P1/sign/consumption/live/closeout all
  durably true, and the live plus closeout receipts are successful;
- `ATTEMPT_HOLD_SPENT`: normal mode, `p1_iex_begun=true`, `go_signed=false`, and
  an exact terminal ATTEMPT-HOLD receipt is present;
- `SIGNED_AUTHORITY_HOLD_SPENT`: normal mode, `go_signed=true`,
  `live_terminal_durable=false`, and an exact signed-authority HOLD is present;
- `POST_LIVE_CLOSEOUT_HOLD_SPENT`: normal mode,
  `live_terminal_durable=true` and an exact post-live/closeout HOLD is present;
  or
- `OWNER_ADJUDICATED_ABANDONED_SPENT`: owner-adjudication mode only, with a
  non-null adjudication-receipt digest and the current vector declared abandoned
  by that separately authorized receipt.

No disposition may cross those predicates. A release failure later changes the
final release-record disposition by the phase rule below; it never rewrites the
baseline disposition.

`paths` has exactly string keys `attempt_parent`, `authority_envelope`,
`binding_parent`, `canonical_root`, `elevated_transcript`, `go`,
`nonelevated_transcript`, `profile_binding`, `signature`, `w5_root`,
`worker_binding`, and `worker_root`, plus nullable string
`appcontainer_profile_root` and `owner_adjudication_receipt`. Every non-null
value is fully qualified, table-/nonce-derived, normalized, and boundary-
consistent. The transcript path
equals the carrier. `identities` has exactly nullable string keys
`appcontainer_sid`, `authority_envelope_sha256`, `connector_run_id`, `go_id`,
`go_sha256`, `owner_adjudication_receipt_sha256`, `request_sha256`,
`signature_sha256`, and `worker_manifest_sha256`, plus non-null strings
`attempt_nonce`, `interpreter_sha256`, and `profile_moniker`. Non-null hashes
are lowercase SHA-256; the nonce is 32 lowercase hex; IDs use their canonical
lowercase UUID form. The adjudication receipt path/digest is non-null exactly
for an owner-adjudication baseline. Presence/null must agree with paths, phase
flags, and manifest state.

`program_data` has exactly `state`, `path`, `length`, and `sha256`. `path` is
`C:\ProgramData\Project6\Authority\sciencebase-go-spent-v1.jsonl`. `state` is
`ABSENT` or `PRESENT`; ABSENT requires length zero, null hash, and an ABSENT
manifest entry; PRESENT requires positive length, lowercase hash, and a matching
ordinary-file manifest entry. These length/hash values are also the only sealed
expected prefix admitted by a later Attempt-5 atomic claim.

`transcript_prefix` has exactly integer `length`, lowercase SHA-256 `sha256`,
and `separator` in `NONE` or `CRLF`. It identifies every carrier byte present
before the baseline write. `separator=NONE` is required when that prefix is
empty or already ends in `0D 0A`; otherwise the writer appends exactly one
`0D 0A` and records `CRLF`. The immutable pre-frame bytes are therefore exactly
`prefix || optional-CRLF`. A torn prior marker in adjudication mode remains part
of `prefix`; it is never truncated or repaired.

Each `manifest` entry has exactly: string `path`; `state` in `ABSENT`, `FILE`, or
`DIRECTORY`; `content_scope` in `NONE`, `FULL`, or `TRANSCRIPT_PREFIX`; nullable
strings `volume_serial`, `file_id`, `reparse_tag`, `sha256`, `owner_sid`, and
`sddl`; nullable integers `hard_link_count`, `length`,
`creation_time_utc_ticks`, and `last_write_time_utc_ticks`; nullable Boolean
`access_rules_protected`; and array `aces`. Each ACE has exactly string `sid`,
`type`, `mask`, `inheritance_flags`, and `propagation_flags`, plus Boolean
`is_inherited`. ACEs sort by that six-field tuple using ordinal string order
then false-before-true. `volume_serial` is 16 lowercase hex from
`FILE_ID_INFO.VolumeSerialNumber`, `file_id` is its 32-lowercase-hex 128-bit file
ID, and `reparse_tag` is eight lowercase hex; hashes remain 64 lowercase hex.
ACE `type` is `ALLOW` or `DENY`; `mask` is `0x` plus eight uppercase hex;
inheritance/propagation names are uppercase underscore tokens joined by `|` in
ordinal order, or `NONE`. SDDL is the exact reread descriptor string. Manifest
paths are canonical rooted strings sorted first with
`StringComparer.OrdinalIgnoreCase`, then `StringComparer.Ordinal`; case-colliding
duplicates are forbidden. ABSENT entries use `content_scope=NONE`, require every
nullable observation null, and have `aces=[]`. DIRECTORY entries use
`content_scope=NONE`, null length/hash, and non-null identity, link, owner,
security, creation-time, and last-write observations. Ordinary files use `FULL`
and require those same observations plus non-null length/hash. All admitted
objects are ordinary/non-reparse, so `reparse_tag` is null.

The carrier alone uses `TRANSCRIPT_PREFIX`, with length/hash equal to
`transcript_prefix`; identity, link, owner, security, and creation time are
non-null, but `last_write_time_utc_ticks` is normatively null because both frame
appends change it. H5 does not compare carrier last-write time and compares every
other carrier field. No other present entry may use a null last-write value.
`manifest_sha256` is SHA-256 of `CanonicalJsonV1(manifest)` and
covers the complete Attempt artifact/mutation vector, including ProgramData.

#### Two-stage append and recovery

Inside the final all-three-name `NonRuntime` callback, the normal writer opens
the closed existing carrier, rejects any full or partial terminal marker,
captures the exact prefix and deterministic manifest, appends the optional
separator plus one canonical `BASELINE` frame, durably flushes, closes, reopens
read-only, and verifies exact `prefix || separator || baseline-frame` with no
tail. It recomputes every non-self entry before the callback returns. Only that
sequence yields `BASELINE_SEALED_PENDING_RELEASE`.

The guard wrapper then performs every probe/lease `CloseHandle` and returns a
structured cleanup result. Immediately after cleanup, the seal action reopens
the carrier with no sharing, verifies the exact prefix and baseline with no
tail, and appends one `RELEASE` frame. Its exact object key set is `accounting`,
`adjudication_delta`, `attempt`, `baseline_disposition`,
`baseline_line_sha256`, `baseline_mode`, `campaign_id`,
`cleanup_error`, `disposition`, `mode`, `prior_failure_code`, `record_type`,
`release_status`, `schema`, and `status`.
The common values match the baseline; `record_type=RELEASE`,
`status=ATTEMPT_TERMINAL_RELEASE_RECORDED`, and `baseline_line_sha256` hashes the
complete raw baseline frame including its CRLF. `baseline_mode` and
`baseline_disposition` equal the baseline fields; `accounting` is byte-
canonically identical. `cleanup_error`, `prior_failure_code`, and
`adjudication_delta` are nullable and may be non-null only in the combinations
stated below. The first two are strings.

`adjudication_delta` is null for a normal-mode release. Otherwise it is an object
with exactly `attempt_parent`, `authority_receipt`, and `preserved_receipts`.
`authority_receipt` is the complete `FILE/FULL` manifest entry for the fresh
validated receipt, whose content SHA-256 is the authority digest.
`preserved_receipts` is a manifest-sorted array of complete `FILE/FULL` entries
for every prior receipt leaf created after the referenced baseline and absent
from that baseline manifest; it excludes `authority_receipt`.
`attempt_parent` is null when all receipts already appear in the baseline.
Otherwise it is the complete current `DIRECTORY/NONE` entry for the attempt
parent after the packet-enumerated receipt additions. No other null/object or
entry-set combination is valid.

`release_status` is exactly `RELEASED`, `RELEASE_FAILED`, or
`RECOVERED_MISSING_RELEASE`. A normal successful cleanup uses mode `NORMAL`, null
error/authorization fields, `RELEASED`, and the baseline disposition. A
successful owner-adjudication baseline uses mode `OWNER_ADJUDICATION`, null error
fields, `RELEASED`, its baseline disposition, and an adjudication delta whose
null parent, authority receipt, and empty preserved-receipt array all match its
baseline manifest. A cleanup failure uses
`RELEASE_FAILED`, `cleanup_error=sciencebase_attempt_family_guard_release_failed`,
null `prior_failure_code`, and final disposition `POST_LIVE_CLOSEOUT_HOLD_SPENT`
when `live_terminal_durable=true`, `SIGNED_AUTHORITY_HOLD_SPENT` when signed but
no live terminal exists, otherwise `ATTEMPT_HOLD_SPENT`. It is durably recorded
even though the failed OS handle may persist until process exit. Its
adjudication delta follows the same mode/recovery rules as the attempted release.

A crash or write failure after a valid baseline but before a valid release
record blocks H5. When the carrier ends exactly after that valid baseline, only
separately owner-authorized recovery may reacquire an all-three guard. Inside
that guard it creates and validates the fresh receipt, then revalidates the exact
carrier plus `baseline manifest + authorized adjudication delta`. Every baseline
entry except the attempt parent must remain identical. The parent's volume/file
identity, link count, owner, DACL/SDDL/ACEs, creation time, and ordinary/
non-reparse type must remain identical; only its last-write time and exact child
set may transition. The current parent entry must equal
`adjudication_delta.attempt_parent`, and the only children absent from the
baseline that may now exist are the current authority receipt and every
enumerated preserved receipt in that delta. Omission, an unknown child, a prior
receipt whose entry changed, or any other field/path change is HOLD before
carrier mutation.

After that overlay validation, recovery releases its guard and appends
`RECOVERED_MISSING_RELEASE` with mode
`OWNER_ADJUDICATION`, `prior_failure_code=sciencebase_terminal_release_receipt_missing`,
null `cleanup_error`, the baseline disposition, and an adjudication delta with
the post-receipt parent entry, fresh authority receipt, and all packet-enumerated
post-baseline prior receipts. Recovery cannot change the baseline. If recovery
cleanup itself fails, it appends `RELEASE_FAILED` and uses the phase-derived HOLD
above with that same delta.

When no complete chain exists and the suffix is not an exact recoverable
baseline-only frame—for example a torn baseline or release—owner-adjudication
mode may preserve every existing byte as a new immutable prefix and append one
adjudication baseline plus its later release record. A prior normal baseline or
torn frame may therefore remain inside that prefix but is never treated as the
final chain. This includes a prior owner-adjudication baseline whose release is
torn: its receipt must appear in the fresh receipt's cumulative prior set, and a
new `CREATE_ABANDONMENT_CHAIN` receipt is required. When the carrier is absent it
may first create only the fixed header above. It never truncates, replaces, or
repairs bytes. An existing complete chain, an exact baseline-only suffix that
must use `RECOVER_MISSING_RELEASE`, an unreadable vector, or any evidence/
disposition mismatch is HOLD without mutation.

Every frame append is followed by durable flush, close, read-only reopen, exact
byte reread, canonical re-encode, and no-tail proof. The final carrier is exactly
`prefix || separator || baseline-frame || release-frame`; an incomplete,
duplicate, reordered, unknown-kind, or trailing byte blocks Attempt 5. A normal
second call and any H5 attempt to originate/recover a chain fail with unchanged
bytes. The runbook's no-concurrent-sitting rule covers the short post-guard
release-record window; H5 later reacquires all three names and revalidates the
complete baseline plus any exact release-bound adjudication delta, so
intervening mutation cannot be accepted.

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

Update `next_milestone_plans/sciencebase-live-readiness.md` so the first two
validate-only Python gates run before nonce creation, binding-parent creation,
attempt-family custody creation, profile creation, or worker provisioning.
Remove every independent `py -3.12`, `py -V:PythonCore/3.12`,
`$PythonLauncherTag`, and ScienceBase `-PythonVersion` flow from the document.
Each phase requires `status -ceq 'PYTHON_BINDING_OK'` and sets `$Py` from that
gate result's `ambient_interpreter`. The W5 operator-observation block, if later
authorized, runs in the Phase-1b non-elevated shell and consumes call 4's fresh
gate result; it performs no separate minor-prefix resolution and carries no
in-memory value across a shell boundary.

The head-bound sitting runbook's two Phase-2 `pytest` commands and the W5 block
also consume call 4's verified `$Py` in that same fresh shell. The test commands
use `& $Py -m pytest` with bytecode and pytest-cache generation disabled; the W5
content-contract probe uses the same `$Py`. These are an explicit auxiliary
allowlist, not part of the five governed initializer/template/live/closeout
calls. No auxiliary site may invoke `py`, `python`, `project6.ps1`, carry `$Py`
from Phase 1, or resolve a minor prefix independently.

Correct the stale ProgramData sentence in both the readiness document and the
later head-bound sitting runbook. The worker provisioner is not the sole ACL
mechanism. Reservation and authority initializers do not touch ProgramData;
`OneUseLiveGoConsumer` first reaches it during GO consumption through
`SpentMarkerStore`, whose Windows backend securely creates the missing
`C:\ProgramData\Project6\Authority` directory. This is a documentation/test
correction to existing effect ownership, not a new initializer side effect.

Close the Attempt-5 preflight-to-consumption race in that same implementation.
Add a local `SpentPrefixExpectation` to the exact head-bound live invocation and
thread it through `OneUseLiveGoConsumer` to `SpentMarkerStore.claim_exact`; it is
not a worker, authority-envelope, GO, reservation, or closeout schema field. It
has exact fields `state`, `length`, `sha256`, `directories`, and `file`.
`directories` is either empty or the two complete terminal-manifest directory
entries for `C:\ProgramData\Project6` and its `Authority` child in that order;
`file` is null or the complete marker-file manifest entry. ABSENT requires
`(0,null,[],null)`. PRESENT requires positive length/hash, both directory
entries, and the matching file entry. Attempt 4 supplies ABSENT. Attempt 5
derives ABSENT when the verified Attempt-4 chain proves no GO consumption and
ProgramData absence, or the exact PRESENT expectation when it proves a claim.

The marker backend enforces this expectation under the same exclusive file lock
used for the claim. ABSENT first requires both managed directories and the marker
absent, then creates each directory once with its final descriptor and creates
the marker with secure `CREATE_NEW`; any pre-existing managed leaf HOLDs. This is
not a three-object atomic transaction. A failure after any one create preserves
the exact partial subtree and returns HOLD; it never removes or completes residue
to make a later absence check pass.
PRESENT opens both directories and the marker with `OPEN_EXISTING` only and never
creates a missing object. After the file handle is locked, the backend compares
all three pinned handles against every expected volume/file ID, link count,
owner SID, DACL protection, ordered SDDL, ACE tuple, creation time, and last-write
time, then reads current raw bytes immediately before duplicate parsing or append
and compares exact length and SHA-256. State, custody, identity, security, or
byte mismatch returns HOLD before any write, truncate, replacement, claim, or
GO consumption. The head-
bound runbook derives the expectation rather than accepting arbitrary operator
bytes. Barrier tests pause after H5 preflight and separately replace a disposable
log with an identical-byte, safe-looking one-link file and swap a managed
directory before the live claim. Both must be rejected with drift state
unchanged and no Attempt-5 line appended; an ordinary byte-change race must
fail identically.

Repeat the validate-only Python gate exactly six times:

1. fresh ordinary pre-sitting shell, before any remaining-attempt custody;
2. fresh elevated parity-precheck shell, also before custody;
3. elevated Phase 1 after attempt-parent, campaign-child, and binding-parent
   custody validation but before `$P1_IexBegun`;
4. fresh non-elevated rehydration shell before template emission;
5. immediately before a separately authorized signed-live invocation; and
6. immediately before closeout after the one live invocation terminates.

Use `$Py` directly for exactly five governed Python tool invocations: reservation
initializer, authority-envelope initializer, unsigned template emission,
signed-live invocation, and no-live closeout. Derive absolute tool paths from
the already verified `$RepositoryRoot` (`tools\dual_live_initialize.py` and
`tools\dual_live_run.py`), validate those leaves, `Push-Location` to the exact
repository, pass the existing tool argv without the wrapper-only `--`, check
`$LASTEXITCODE` immediately, and restore location and
`DUAL_LIVE_RUNTIME_ENABLED` in `finally` blocks. Those five sites must not call
`project6.ps1` or `py.exe`. `project6.ps1` and its global `-PythonVersion`
semantics remain unchanged for unrelated actions.

Retain the elevated post-provision comparison between the gate-observed ambient
root/length/hash and the emitted worker binding/interpreter. Also require the
current user SID to equal both profile and worker `broker_sid` values and the
worker DACL to retain exactly six unique ACEs and its broker RX mask `0x001200A9`
before the binding is accepted. Any post-provision ambient/worker mismatch is
terminal `ATTEMPT HOLD`, definitively spends that attempt, preserves all bytes,
and prohibits continuation or reuse. This is the exact disposition of the check
that stopped Attempt 3.

Before Attempt-4 custody, the ordinary shell must read the retained Attempt-3
profile/worker bindings, prove current-user SID equals both broker SIDs, run the
production full `validate_worker_bundle` path against the hardened retained
bundle, and directly hash its interpreter. Any access or validation failure is
`PRE-SITTING HOLD`. After Attempt-4 provisioning, Phase 1b repeats
current-user/frozen-owner/broker equality, full bundle validation, and the direct
worker-interpreter hash in a fresh non-elevated shell. Do not substitute a
binding-record hash. A failure there is terminal `ATTEMPT HOLD`; the separately
authorized integrated rehearsal below must close this path before the real
attempt is allowed to begin.

Python-gate failure disposition is fixed by call site:

- calls 1-2: `PRE-SITTING HOLD`; no attempt consumed and no custody created;
- call 3: `PRE-BEGIN HOLD`; preserve created custody, do not resume or retire a
  namespace without a later owner ruling;
- call 4: terminal `ATTEMPT HOLD`; attempt spent, all bytes preserved, no reuse;
- call 5: terminal `SIGNED-AUTHORITY HOLD`; attempt spent, GO/signature retired
  from all future use and preserved; and
- call 6: `POST-LIVE CLOSEOUT HOLD`; never rerun live or reuse the signature;
  closeout recovery requires its existing rules plus explicit owner direction.

Family-guard acquisition, probe, callback, and release failures are equally
fail-closed. The wrapper does not infer phase; the call site and already-set
monotonic phase flags map its stable code as follows:

- ordinary pre-sitting guard: `PRE-SITTING HOLD`, no attempt consumed;
- elevated guard acquisition before custody: `PRE-SITTING HOLD`; after custody
  but before `$P1_IexBegun`: `PRE-BEGIN HOLD`; at or after `$P1_IexBegun`,
  including final release: terminal `ATTEMPT HOLD`, attempt spent;
- fresh Phase-1b/unsigned-template guard: terminal `ATTEMPT HOLD`, attempt spent;
- signed-live guard before its callback enters: terminal
  `SIGNED-AUTHORITY HOLD`, attempt spent and GO/signature retired;
- signed-live guard after its callback enters: preserve the live tool's durable
  result; a guard release failure is `POST-LIVE CLOSEOUT HOLD` only when a
  terminal live outcome is durably present, otherwise `SIGNED-AUTHORITY HOLD`.
  Both dispositions retire the signature and prohibit another live call; and
- closeout guard: `POST-LIVE CLOSEOUT HOLD`, with no live rerun or signature
  reuse.

A release failure may end when its host process exits, but that observation does
not authorize retry or downgrade the recorded HOLD. There is no timeout,
stale-lease inference, automatic repair, attempt reuse, or second close attempt.

After the final governed effect and any required closeout are settled, the
runbook writes the terminal baseline inside its own final `NonRuntime` callback,
then writes the bound release record only after the wrapper reports cleanup. A
complete chain records the already-determined disposition; it never converts a
recoverable/incomplete state into terminal state by itself. Missing, partial,
duplicate, or drifted terminal-chain state blocks Attempt 5 and follows the
terminalization/adjudication rules above.

The Python gate emits only its stable code and never infers campaign phase. Every
call site owns one label, prints that label with the stable code, and stops.
Neither layer repairs, deletes, relabels, resumes, or retries.

### 5. Disposable integrated rehearsal before Attempt 4

The Python gate cannot prove ACL access or create-once initializer behavior.
Before Attempt 4, and only under a separate owner authorization for elevation
and external persistent writes, run the exact reviewed Phase-1-through-template
path in a unique disposable protected family that is disjoint from all real
Attempt-4/5 and retained paths. Use distinct rehearsal bindings, W5 scratch,
worker root, profile moniker, connector-run ID, GO ID, and transcript paths.

The rehearsal must:

1. enter non-runtime family guards in its ordinary and elevated phases and pass
   the frozen-owner-SID and Python gates inside those guards;
2. create and verify the protected inheritable parent, protected
   non-inheritable campaign child, and separate protected empty binding parent;
3. provision the real profile and exact 3.12.10 worker, verify post-provision
   equality and broker/current-user identity, and initialize
   `<rehearsal-campaign>\reservation.db` plus the sibling authority envelope.
   While the reservation transaction is open, the owner-host observer hook must
   capture the live DELETE-mode journal using the actual elevated owner token and
   reviewed SQLite build and prove the frozen type/identity/security posture;
4. prove first initialization succeeds, then prove a second same-path
   initializer call returns the expected create-once HOLD with every existing
   byte/hash unchanged and no reservation staging leaf remains; create-once is
   not "idempotent success";
5. close the elevated shell, then in a fresh non-elevated shell enter a new
   non-runtime family guard and, while it remains held, run frozen-owner/broker
   parity, full bundle validation, direct interpreter hashing, authority/
   reservation census, and production unsigned-template emission through the
   exact gate-returned `$Py`;
6. prove a second same-path template emission fails create-once with the first
   template unchanged and runtime cleanup complete; and
7. prove the real Attempt-4/5 vectors, retained Attempts 1-3 residue, both
   archives, and `C:\ProgramData\Project6` are unchanged before/after.

No private key, signature, GO consumption, spent-marker write, network request,
live invocation, or closeout occurs. Preserve the rehearsal family and receipts
as explicitly non-authoritative evidence; do not delete or reuse them. The
rehearsal's ProgramData assertion is an unchanged census because the two
initializers do not use ProgramData and the flow stops before GO consumption.

### 6. External archive prerequisite

The official archive belongs at
`C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip`. Creating that
file is a later owner-authorized prerequisite outside the repository. The
source URL is
`https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip`.
The existing 3.12.6 archive is historical input and must not be removed,
overwritten, renamed, or reused for Attempt 4. Once placed and verified, both
archive versions are immutable retained inputs.

## Data and Authority Flow

1. A validate-only gate uses the vendor/minor launcher only as a locator and
   proves the frozen ambient, archive, and ZIP-member byte identities.
2. The phase-scoped family guard encloses the frozen-owner-SID check, complete
   activation-stage state/containment comparison, and protected attempt-parent,
   campaign-child, and binding-parent custody validation before `$P1_IexBegun`.
3. The provisioner builds the worker from that same locked archive and the exact
   clean reviewed source commit, preserving the stage/inventory/manifest move.
4. The post-provision gate proves current-user/broker identity, exact worker
   ACL, ambient-root equality, and ambient/worker executable equality.
5. Reservation and authority create-once state lives wholly in the selected
   attempt family. The Phase-1 record carries the attempt number, parent,
   canonical root, bindings, worker, envelope, and exact interpreter identity
   across the elevation boundary.
6. The fresh non-elevated phase revalidates those durable facts. Across the
   fixed Phase-1, template, live, and closeout sites, exactly five governed calls
   use their phase's gate-returned absolute interpreter.
7. Canonical root, worker manifest, interpreter, envelope, request, GO, and
   signature identities flow together to live and closeout. Changing the root,
   source, runtime pin, or connector run requires wholly new downstream bytes.
8. A guarded baseline record captures the complete Attempt-4 artifact and
   ProgramData baseline before guard release; a second append-only record binds
   the actual cleanup result afterward. H5 verifies the complete chain but can
   neither originate nor recover it.
9. Attempt-3 and failed Attempt-4 identities are evidence only; none is reusable.

Repeated Python gates contain the Python identity family only. The custody,
broker-access, initializer, mutex, and integrated-rehearsal gates are separate;
this design does not represent Python revalidation as whole-sitting coverage.

## Test-Driven Verification

### RED

Use staged RED so a missing new script is not misreported as proof of the
interpreter defect:

1. First add the gate's public-interface and executable behavior tests. Observe
   their expected missing-entry-point failure, then add the still-inert gate and
   make its synthetic mismatch-rejection and match-acceptance tests pass.
2. Before the composition RED is accepted, prove in fresh ordinary and elevated
   Windows PowerShell 5.1 shells that the real host launcher resolves
   `-V:PythonCore/3.12` with exit zero, empty stderr, and exactly one absolute
   path whose size/hash is the frozen ambient identity. Non-resolution or token
   divergence is `python_binding_launcher_invalid` and reopens the design; it is
   not a valid composition RED.
3. Before changing the worker pin or readiness flow, route the installed 3.12.10
   ambient and retained official 3.12.6 archive through the production
   comparison function with test-injected expected archive/member identities.
   Ambient validation and archive/member validation must each pass, while only
   member-vs-ambient equality fails with `python_binding_mismatch`.
4. Add direct readiness/topology tests that fail on H3's shared campaign root,
   fixed sidecars, wrapper re-resolution, missing post-provision disposition,
   an action outside the phase-scoped family guard, missing ordinary/elevated
   owner-SID parity, absent/insecure binding-parent custody, a missing terminal-
   chain producer, and an incomplete Attempt-5 namespace.
5. Add the executable cross-token worker test before changing ACL behavior. It
   must show the real broker/current-user SID can read and fully validate the
   exact six-ACE hardened bundle from a filtered non-elevated token. The negative
   control is another filtered token with no enabled SID matching any of the six
   allowed principals and no enabled backup/restore privilege; that token is
   denied. This RED is about missing coverage and explicit identity checks; it
   must not falsely expect the real broker read to fail or an administrator to
   lack rights granted by the DACL.

Snapshot the complete mutation boundary immediately before and after every
validate-only characterization. Before any implementation test, materialize one
exhaustive, literal `$MutationVector` from the fixed Attempt-4/5 path table plus
a separately frozen retained-residue table. The old H3 seven-entry array is a
seed, not an exhaustive historical manifest. The retained table must include
these exact recursive roots:

- `C:\owner-controlled\project6` after D5 archive placement;
- `C:\owner-controlled\project6-bindings` and
  `C:\owner-controlled\project6-bindings-3`;
- `C:\owner-controlled\project6-w5obs` and
  `C:\owner-controlled\project6-w5obs-3`; and
- `C:\p6-sciencebase-worker-2` and `C:\p6-sciencebase-worker-3`.

The retained table also has a closed repository-owned governance/evidence
subvector. Materialize these eight exact rooted carrier leaves independently;
do not rely on the dirty root's porcelain or replace them with a category:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\plan-of-record-sciencebase-signed-go-2026-08-12.md`;
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\SITTING-RUNBOOK-2026-08-14.md`;
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\Q12-EVIDENCE-POINTER-INDEX-2026-08-15.md`;
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\owner-decision-sheet-sciencebase-signed-go-2026-08-12.md`;
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\amendment-addendum-v1.1-sciencebase-signed-go-2026-08-12.md`;
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\forward-map-signed-go-lane-2026-08-13.md`;
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\HANDOFF-SESSION-CONTINUATION-2026-08-14.md`; and
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox\AUDIT-LEDGER-2026-08-14.md`.

Materialize recursive raw-byte manifests for these exact historical roots as
well: `state\agent-inbox\session-8e8b798b-archive`,
`state\agent-inbox\session-9ee3527a-adversarial-pass`,
`state\agent-inbox\characterization-record-2026-08-13`, and
`state\agent-inbox\characterization-record-2-2026-08-14`, all resolved beneath
the absolute repository root above. These roots cover the sealed Attempt-1/2/3
packet, freeze, carrier, and evidence bytes currently in preservation scope.
Missing roots, unclassified children, or any before/after drift are HOLD.

It must also enumerate as independent load-bearing leaves, even when a recursive
root already covers them:

- `C:\owner-controlled\project6\phase1-record.txt`;
- the stranded Attempt-1 profile binding
  `C:\owner-controlled\project6\sciencebase-profile-058560b617074b1c903b1e667cec78d9.json`;
- `C:\owner-controlled\project6\attempt2-elevated-transcript.txt` and
  `C:\owner-controlled\project6\attempt3-elevated-transcript.txt`;
- `C:\owner-controlled\project6\sciencebase-campaign` and both archive leaves;
- the Attempt-2 profile binding
  `C:\owner-controlled\project6-bindings\sciencebase-profile-80fecb16adbd49c5ae0bb7f8ae541928.json`; and
- the Attempt-3 profile and worker bindings
  `C:\owner-controlled\project6-bindings-3\sciencebase-profile-8688cea4cae54e60980aa33db8ca5b38.json`
  and
  `C:\owner-controlled\project6-bindings-3\sciencebase-worker-8688cea4cae54e60980aa33db8ca5b38.json`.

For every retained profile binding, the separately authorized pre-H4 read-only
census must resolve `appcontainer_profile_root` to one rooted literal, add that
exact path to the table, and freeze the corresponding profile moniker/SID lookup
identity. Missing/unreadable bindings, unresolved roots, unclassified children,
or profile-lookup drift are HOLD; this spec does not invent values that the
current non-elevated review could not read. The Attempt-4 fixed must-remain-absent table,
not the retained table, contains
`C:\owner-controlled\project6\attempt3-nonelevated-transcript.txt`,
`C:\owner-controlled\project6\sciencebase-campaign\reservation.db`,
`C:\owner-controlled\project6\sciencebase-authority.json`,
`C:\owner-controlled\project6\owner-go.json`,
`C:\owner-controlled\project6\owner-go.json.sig`, and
`C:\ProgramData\Project6`.

Recursive manifests make every child of those roots part of the proof. The H4
packet must print and assert the actual vector count and every literal entry.
Wildcards, category-only phrases such as "all named residue," and guessed
inherited counts are forbidden in the executable vector. Its required coverage
also includes:

- both remaining-attempt parents and every logical child/sidecar;
- both binding parents, W5 scratch roots, and worker roots;
- `C:\ProgramData\Project6`;
- the retained shared campaign root and every literal retained-table entry;
- the 3.12.6 archive and, once placed, the 3.12.10 archive; and
- the ambient executable.

Maintain a separate exhaustive `$WorktreeVector`. Parse every `worktree` record
from one successful `git worktree list --porcelain` call, require empty stderr,
reject empty/malformed/duplicate records, qualify a non-drive-qualified record
against `C:\` before comparison, normalize paths with Windows boundary semantics,
sort them ordinal-ignore-case, and print/assert the actual count and every root.
Do not freeze the previously observed count. Compare every remaining-attempt
parent, child, sidecar, binding, W5, worker, rehearsal, and scratch path against
every enumerated worktree and against the named repository/ceremony roots; equal,
ancestor, or descendant relationships are HOLD.

For the dirty root checkout, frozen `sb-ceremony` checkout, implementation lane,
and every other enumerated worktree, record the rooted path, HEAD, branch or
detached state, and NUL-delimited full porcelain including untracked files with
optional Git locks disabled. The implementation and ceremony lanes additionally
require the expected exact heads and source-blob identities.

HEAD and porcelain are inventory receipts, not byte invariants for an already
dirty path. For every worktree, also capture raw byte length and SHA-256 of
successful, empty-stderr `git diff --binary --no-ext-diff --no-textconv` and
`git diff --cached --binary --no-ext-diff --no-textconv` outputs. Use
`git ls-files --others --exclude-standard -z` to obtain the NUL-delimited
untracked-path set; reject malformed, duplicate, escaping, or reparse-ambiguous
paths; and materialize a sorted type/length/SHA-256 manifest without following
reparse points. Hash the raw untracked-name stream and the manifest as well. An empty
porcelain plus empty diffs/untracked set is sufficient for a clean worktree;
dirty worktrees require all three content receipts. Ignored caches are outside
the general Git receipt, while the exact ignored/untracked ScienceBase governance
paths above remain covered by their independent literal raw-byte manifests.
The external mutation vector uses recursive filesystem manifests; Git
administration/cache files themselves are not recursively hashed. Both vectors,
all content receipts, and both regenerated counts are before/after invariants.

Record existence for every external mutation path. For every present root and
manifest child, without following a reparse point, record rooted type, reparse
tag/target, volume serial, stable file identity, hard-link count,
`CreationTimeUtc`, `LastWriteTimeUtc`, byte length, and SHA-256 for ordinary
files. Also record owner SID, `AreAccessRulesProtected`, ordered access-DACL SDDL,
and a separately sorted ACE tuple list containing SID, Allow/Deny type, numeric
mask, inheritance flags, propagation flags, and `IsInherited`. Failure to obtain
or normalize identity or security metadata is HOLD; neither timestamps nor content hashes substitute for
it. Every source contract that requires a one-link ordinary file—including the
spent-marker log—must assert link count exactly one; any hard-link drift is
HOLD. Exclude last-access time because reads may update it, and make no SACL or
primary-group invariant claim. Before/after recursive manifests must be
identical; validate-only actions may not seed missing state.

The automated suite must also require:

- no `PythonCore/3.12.10` selector anywhere in the corrected production or
  readiness surface; `-V:PythonCore/3.12` is a locator only and the exact
  size/hash assertions are present;
- exact 3.12.10 re-pins at every tracked literal: provisioner version/archive/
  hash, readiness archive and expected worker version,
  `.github/workflows/playwright.yml` setup-Python value formerly at line 639,
  archive URL/hash formerly at lines 650-651, and worker-bundle
  `python_version` literals formerly at lines 775 and 785;
  `tests/test_dual_live_worker_provisioner.py` archive/hash assertions formerly
  at lines 18-19; and `backend/tests/test_ci_coverage_completeness.py` setup-
  Python/URL/hash assertions formerly at lines 258-260;
- the ordinary and elevated gates plus activation-stage state/containment checks
  to precede custody, both shells to equal the one frozen owner SID, and attempt-
  parent/campaign-child/binding-parent validation to precede `$P1_IexBegun`;
- readiness and the head-bound runbook to attribute first ProgramData creation
  to spent-marker GO consumption, never to either initializer or solely to the
  worker provisioner;
- the complete readiness file to contain zero independent `py -3.12` or other
  ScienceBase minor-prefix resolutions, including the W5 block; every `$Py`
  comes from a successful gate object;
- exactly six Python gate calls in the fixed phase order; exactly five governed
  initializer/run `$Py` call sites; and only the separately enumerated Phase-2
  pytest/W5 auxiliary sites. None uses `project6.ps1`, `py`,
  `$PythonLauncherTag`, `-PythonVersion`, or a cross-shell `$Py` value;
- a synthetic mismatched ambient/archive member to throw
  `python_binding_mismatch` without changing a disposable mutation sentinel;
- a synthetic matching ambient/archive member to return `PYTHON_BINDING_OK`
  and the expected worker interpreter hash;
- a PS5.1 disposable executable capture shim, injected only through the internal
  launcher test seam, to prove the gate's first launcher argument is exactly
  `-V:PythonCore/3.12`; a `.cmd` shim is forbidden because
  `UseShellExecute=$false` launches the frozen executable directly. Real-host
  resolution GREEN is separate and cannot be replaced by the shim;
- absolute initializer/run tool paths under the verified repository root,
  exact argv preservation without wrapper-only `--`, immediate nonzero-exit
  HOLD, and location/environment restoration;
- one fixed terminal-chain carrier, exact frame/schema/enums, a golden canonical
  byte vector, baseline-in-guard/release-after-cleanup ordering, durable flush/
  reread, complete artifact manifest, no H5 origin or recovery, normal-missing-
  carrier no-mutation, adjudication-only create-new, and exact absent/partial/
  duplicate/drift/mode-crossing dispositions; and
- family-guard name parity and fixed global ordering for the retained/
  Attempt-4/Attempt-5 roots; existing, absent, access-denied, wrong-object,
  unexpected-error, empty-table, and partial-acquisition cases; and proof that
  every losing or indeterminate path enters the action callback zero times.

An executable call-site-order test must prove the six phase calls map in order
to `PRE-SITTING HOLD`, `PRE-SITTING HOLD`, `PRE-BEGIN HOLD`, `ATTEMPT HOLD`,
`SIGNED-AUTHORITY HOLD`, and `POST-LIVE CLOSEOUT HOLD`; no call site may infer,
omit, or select among labels dynamically. The same test must separately prove
the post-provision ambient/worker mismatch maps to terminal `ATTEMPT HOLD` and
spends the attempt.

The executable failure matrix must cover every stable code:

- `python_binding_launcher_invalid`: nonzero launch, empty/multiple stdout
  lines, non-rooted path, launcher diagnostics, process-start exceptions, and a
  PS5.1 diagnostic case that proves no uncaught `NativeCommandError` escapes;
- `python_binding_ambient_invalid`: missing/wrong-identity leaf plus interpreter
  leaf and ancestor reparse cases;
- `python_binding_archive_invalid`: missing/wrong-name/wrong-size/wrong-hash
  archive plus archive leaf and ancestor reparse cases;
- `python_binding_archive_member_invalid`: missing, duplicate-exact,
  case-colliding, rooted/traversing, and destination-colliding ZIP entries;
- `python_binding_mismatch`: individually valid but unequal ambient/member
  identities.

The same suite must distinguish `sciencebase_owner_identity_mismatch`,
`sciencebase_attempt_family_active`,
`sciencebase_attempt_family_guard_indeterminate`, and
`sciencebase_attempt_family_guard_release_failed`, and prove their exact
phase/accounting mappings without substituting one generic HOLD.

Every failure case must emit zero success objects. Success must emit exactly one
object with the exact field set and `PYTHON_BINDING_OK`. Tests must also prove
the production entry point rejects caller-supplied version/hash/size identities
and that archive replacement/rename/deletion cannot cross the held-stream
hash-to-extraction boundary.

Additional Windows coverage must prove:

- the held object is the extraction source; no `Expand-Archive` or path-taking
  ZIP extraction survives;
- write/delete/rename sharing is denied, and traversal, case, duplicate, and
  prefix collisions fail before extraction;
- the existing `stage-<guid>` to manifest to `sha256-<digest>` move remains;
- current-user/profile/worker broker equality, exact six-ACE DACL with broker
  mask `0x001200A9`, successful filtered-token full validation/direct hash, and
  denial of the filtered no-matching-principal/no-backup-or-restore-privilege
  negative-control token;
- ordinary and elevated tokens equal the frozen owner SID before custody; an
  alternate-credential shell fails before callback mutation;
- Attempt-4/5 and rehearsal custody parents, campaign children, and binding
  parents receive their final descriptor atomically in the creation call inside
  the elevated guard and before `$P1_IexBegun`; a source-level discriminator
  forbids `New-Item`, `Set-Acl`, and create-then-harden fallbacks. Missing,
  pre-existing, nonempty, reparse, wrong-owner, wrong-volume, inherited/insecure-
  DACL, existence-race, or containment-drift cases fail before provisioning and
  preserve any created root. Binding-parent stage checks admit exactly zero,
  then profile-only, then profile-plus-worker nonce leaves with no third child;
- the two attempt families are complete and disjoint, have the exact two DACL
  shapes, enforce the activation-stage absent/sealed split, and ensure a failed
  Attempt 4 cannot collide with fresh Attempt 5;
- identical porcelain cannot mask a changed already-dirty tracked file or an
  already-listed untracked file; the binary-diff and untracked manifests detect
  both, and the exact historical governance vector is independently hashed;
- owner-only, DACL-only, file-identity, hard-link-count, and reparse-target
  changes are detected even when bytes and ordinary timestamps remain unchanged;
- Attempt-5 ProgramData preflight accepts only proven absence after no Attempt-4
  GO consumption or a secure log whose exact Attempt-4 bytes become the prefix
  of one canonical Attempt-5 append. ABSENT selects create-new; PRESENT enforces
  the same bytes plus marker and two managed-directory identity/security entries
  on pinned handles under the claim's exclusive lock immediately before append.
  Byte drift, identical-byte file replacement with a safe-looking DACL, and a
  directory-swap barrier race after H5 all HOLD without an Attempt-5 line;
  partial, extra-entry, rewritten, or contradictory state likewise HOLDs without
  deletion/truncation. ABSENT tests inject failure after each managed-object
  creation and prove the partial subtree is preserved and blocks reuse;
- same-path reservation/envelope/template second calls fail create-once with
  bytes unchanged, while an independently fresh rehearsal namespace succeeds;
  reservation staging and its DELETE-mode `-journal` sibling are absent after
  every clean outcome. While present, the journal is observed as ordinary,
  non-reparse, single-link, same-directory/same-volume and compared with the
  frozen safe owner/DACL posture; either residual is preserved and HOLD;
- terminal-chain tests use a checked-in golden JSON/frame/hash fixture and prove
  exact prefix/separator/baseline/release bytes, complete manifest, disposition-
  evidence predicates, normal `OpenExisting` no-create, adjudication `CreateNew`
  fixed-header create-once, torn-prefix framing, cleanup failure, missing-release
  recovery, the carrier-only null/non-comparable last-write rule, duplicate/
  partial/unknown-tail rejection, and that H5 can neither replace the baseline
  nor accept a baseline without release. Recovery tests prove the exact parent-
  last-write/child-set overlay, unchanged parent identity/security/creation
  fields, complete release delta, and rejection of an omitted, extra, changed,
  or misclassified receipt. Receipt tests prove protected create-once custody,
  checked full write/flush/close/reopen/reread, and reject bare owner mode,
  normal-mode receipt input, wrong attempt/head/carrier/prefix/operation/
  disposition, insecure/reparse/multilink receipt, nonce/digest replay, and
  cross-attempt use. Crash/short-write injection covers create, pre-/post-flush,
  validation, header creation, partial baseline, cleanup, and partial release;
  each demonstrably existing orphan remains immutable and mechanically rejects
  the same nonce. Authoritatively absent/unchanged and indeterminate-state cases
  instead exercise the explicit governance one-shot/HOLD and non-enforcement
  disclosures. Every case requires separately granted fresh-nonce authority,
  which succeeds only with the exact cumulative prior-receipt manifest;
- non-runtime guards hold all three names across the whole callback; live guards
  hold the two non-current names while the unchanged production boundary alone
  acquires the current name before GO consumption;
- partial acquisition rolls back in reverse order; forced GC, callback failure,
  and parent-process termination cannot leak a name; guard handles are not
  inherited by a long-lived child;
- a stale thread-local `ERROR_ALREADY_EXISTS` value is cleared before a fresh
  acquisition and cannot misclassify a newly created name;
- ordinary-held guards block elevated acquisition and elevated-held guards block
  ordinary acquisition in the same session; access denial remains HOLD;
- a current-root collision after the early live probe fails before GO
  consumption, reservation, worker, transport, terminal, or closeout effect;
- executable composition proves custody/provisioning/initializers, template,
  live, closeout, and the terminal baseline are inside the correct guard
  callback—not merely preceded by it—and that the release record is emitted only
  after cleanup result capture; and
- the Python gate contains only Python identity claims; custody, ACL, owner-SID,
  initializer, and action-guard assertions remain separate.

Place the guard cases in `tests/test_dual_live_family_guard.py`. Its zero-skip
Windows PowerShell 5.1 matrix must include simultaneous same-current and
different-current live guards, all-three `NonRuntime`, other-two `LiveRuntime`
plus real production current-root acquisition, invalid `CurrentRoot`, partial
acquisition and callback/release failure injection, probe-handle cleanup,
stale-last-error injection, noninheritance, forced GC, parent-process
termination, ordinary/elevated token composition, and the explicit same-session/
nonclaim boundary.

Retain both RED outputs. A source-token failure, missing-file failure, or the
historical Attempt-3 diagnostic alone is insufficient evidence for the
composition RED.

### GREEN

Run the same executable tests under Windows PowerShell 5.1 against disposable
temporary files. Then run the focused readiness, provisioner, runtime, and
existing elevated ACL suites with cache and bytecode generation disabled.

Add `tests/test_dual_live_python_binding.py`,
`tests/test_dual_live_family_guard.py`, and
`tests/test_dual_live_attempt_terminal.py` explicitly to the required
`dual-live-windows-boundary` job in `.github/workflows/playwright.yml`. Their
Windows PowerShell 5.1 cases must execute with zero skips. Extend
`backend/tests/test_ci_coverage_completeness.py` to prove that exact wiring.
Commit the normative complete-chain byte vector as
`tests/fixtures/terminal-v1.bin`; the terminal tests construct its known object
graph independently, compare every raw byte and digest, parse it back, and reject
any serializer or field-order drift.
Re-pin that job's B0 setup runtime and embeddable archive from 3.12.6 to exact
3.12.10 (including archive URL/hash), so the required AppContainer boundary
proof exercises the corrected worker patch version rather than a generic stale
fixture. This workflow mutation remains gated on D2; the specification does not
pretend that approval or CI execution has occurred.

Repeat the same real-host characterization after the 3.12.10 repin and archive
placement. It must return `PYTHON_BINDING_OK`; the ambient, archive-member, and
expected-worker hashes must agree; and the before/after no-mutation snapshots
must remain identical.

Obtain separate real-host evidence using the installed 3.12.10 interpreter and
the owner-placed official archive. The free gate must pass in both fresh
non-elevated and elevated Windows PowerShell 5.1 shells before any Attempt-4
path is created. In the ordinary shell, the retained Attempt-3 bundle must also
pass full validation/direct hashing with current user equal to broker SID. These
host gates perform no provisioning and are not an attempt.

Under a separate later authorization, the disposable integrated rehearsal must
then pass end to end exactly as specified above, including the fresh
non-elevated broker read and the expected second-create HOLDs. Unit/CI evidence
does not substitute for that exact-host rehearsal, and the rehearsal does not
authorize real Attempt-4 custody.

The retained Attempt-3 diagnostic is historical RED evidence. It does not
substitute for the new composition RED or the post-fix real-host GREEN.

## Attempts 1-3 preservation and remaining-attempt regeneration

Preserve unchanged:

- every Attempt-1, Attempt-2, and Attempt-3 transcript, packet, carrier, freeze,
  binding, worker bundle, W5 scratch root, profile/AppContainer artifact,
  campaign artifact, and other named residue;
- the shared `C:\owner-controlled\project6\sciencebase-campaign` root and its
  create-once state;
- the retained 3.12.6 archive; and
- after the separately authorized D5 placement and D4 verification, both the
  3.12.6 and 3.12.10 archives.

Archive placement is the one planned change inside the shared `project6`
parent. Snapshot the preservation baseline after that later placement and
verification; all ceremony writes thereafter go only to the selected protected
attempt family or separately named external roots. Do not claim that the
metadata of ancestor `C:\owner-controlled` never changes.

Attempt 4 uses its complete table-derived `-4` topology plus fresh attempt nonce,
profile moniker, profile/worker bindings, AppContainer identity, connector-run
ID, worker manifest, Phase-1 record, authority envelope, GO ID/template/digest,
and—only if separately authorized—signature. If Attempt 4 is spent and the owner
later activates Attempt 5, regenerate the corresponding complete `-5` vector
and all downstream identities. No Attempt-4 attempt-scoped path or authority byte
is reused; the shared ProgramData log is the explicit append-only-history
exception and retains the Attempt-4 prefix under the rules below.

Before H5 custody, a fresh all-three `NonRuntime` guard must parse the unique
complete Attempt-4 baseline/release chain from the end of the carrier, reproduce
both canonical frames, verify exact prefix/optional-separator/no-tail bytes,
verify the release record's baseline-line digest and evidence/disposition rules,
and compare the complete baseline plus its release-bound adjudication delta to
disk. With a null delta, every baseline artifact, identity, hard-link, timestamp,
and security-manifest entry must match directly. A non-null delta with a null
attempt parent is valid only for an owner-adjudication baseline: every baseline
entry still matches directly, its authority receipt matches the baseline, and
its preserved-receipt array is empty. A non-null delta with a parent entry is
valid only for missing-release recovery: every baseline entry except the parent
still matches directly; the parent matches the delta entry while retaining its
baseline identity, link count, owner, DACL/SDDL/ACEs, creation time, and ordinary/
non-reparse type, and only its last-write time and exact child set may have made
the enumerated transition. In that recovery case, the fresh authority receipt
and every preserved-receipt entry must match disk. The current receipt set must
equal the disjoint union of baseline receipt entries, preserved receipts, and
the authority receipt; no other child or field may differ. A missing release,
nonfinal/malformed frame, duplicate chain, impossible null/object combination,
mismatch, or record originated/recovered by H5 itself is HOLD. The validated
baseline plus delta is the authoritative Attempt-4 preservation state for
family, binding, worker, W5, profile, sidecar, receipts, and ProgramData; its
bound release is the final cleanup receipt.
Ordinary production receipts or a fresh census do not substitute.

The ProgramData precondition is attempt-stage-specific. It is absent before
Attempt 4 because Attempts 1-3 never consumed a GO. Before any Attempt-5
activation, derive the expected state from Attempt 4's preserved terminal
receipts:

- if Attempt 4 provably never entered GO consumption, ProgramData must remain
  absent and Attempt 5 derives the exact ABSENT expectation, selecting secure
  create-new at claim time;
- if Attempt 4 durably claimed its one-use GO, the existing securely owned
  `C:\ProgramData\Project6\Authority\sciencebase-go-spent-v1.jsonl` and exact
  Attempt-4 marker entry must be present. Its file identity, link count, owner,
  protected DACL, ACE state, and exact pre-A5 bytes must equal the terminal
  baseline.
  Here “immutable” means prefix preservation: under separate activation/live
  authority, Attempt 5 uses a fresh GO/envelope identity, retains every pre-A5
  byte as an exact prefix, and appends exactly one canonical Attempt-5 line with
  no rewrite, replacement, truncation, or extra entry. The sealed prefix bytes,
  file identity/security, and two managed-directory identities/security are
  passed as the PRESENT `SpentPrefixExpectation` and must all match again on
  pinned handles under the claim's exclusive lock immediately before that
  append; or
- a created directory without a provable claim outcome, a torn/unreadable log,
  ACL/owner drift, an unexpected entry, or conflict with the terminal receipt is
  HOLD pending explicit owner adjudication.

Never delete, truncate, replace, or recreate ProgramData to satisfy an Attempt-5
absence check. The terminal baseline freezes whichever of the first two states
is proved. The fresh H5 packet verifies that prior baseline—it never creates or
recovers a chain—and tests valid absence, exact retained prefix plus one
Attempt-5 append, after-preflight/before-claim drift, and all indeterminate
branches before Attempt-5 custody/live progression.

The protected-parent ruling and initializer rehearsal are coupled: moving
authority/GO/signature state out of the shared parent fixes custody and
Attempt-5 collision risk, while moving the create-once initializers to virgin
per-attempt paths makes the disposable exact-host rehearsal mandatory. The
Python gate alone does not cover that risk.

## Governing records and refreeze

The canonical record root is
`C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox`.
The H3b freeze is exhaustive only over the intentionally closed eight-carrier
set below; it is not a directory manifest. All eight are outside implementation
Git. The Attempt-3 packet, H3/H3b freezes, evidence, and carrier are immutable
historical bytes and must never be edited into Attempt 4.

| Hash order | Exact path below the record root | Future treatment |
| ---: | --- | --- |
| 1 | `plan-of-record-sciencebase-signed-go-2026-08-12.md` | Verify unchanged unless a cited semantic contradiction requires separately reviewed amendment. |
| 2 | `SITTING-RUNBOOK-2026-08-14.md` | Record current 3/5 accounting, then later bind exact H4/Attempt-4 paths, gates, holds, copy ranges, and retained residue. |
| 3 | `Q12-EVIDENCE-POINTER-INDEX-2026-08-15.md` | Record Attempt-3 failure evidence; add only newly generated H4/Attempt-4 pointers later. |
| 4 | `owner-decision-sheet-sciencebase-signed-go-2026-08-12.md` | Record D-AROOT, definitive Attempt-3 spend, 3.12.10 direction, open D2-D5, and absence of land/sign/live authority. |
| 5 | `amendment-addendum-v1.1-sciencebase-signed-go-2026-08-12.md` | Record the reviewed runtime/topology correction and identity-regeneration consequence. |
| 6 | `forward-map-signed-go-lane-2026-08-13.md` | Verify unchanged unless a cited semantic contradiction requires separately reviewed amendment. |
| 7 | `HANDOFF-SESSION-CONTINUATION-2026-08-14.md` | Record failed Attempt 3 and exact next owner gate; add H4 evidence only after it exists. |
| 8 | `AUDIT-LEDGER-2026-08-14.md` | Add a new topmost current-authority row; supersede by DATE+LABEL, never by row number, and cross-check fresh hash/length to disk. |

Reconciliation has two authority phases and neither is authorized by this spec:

1. **Head-independent historical truth.** After a separate owner governance-
   write authorization, promptly record Attempt 3 SPENT, 3/5 spent and 2 remain,
   exact fail-closed root cause, preserved residue, and no GO/signature/
   consumption/network/live act. Until then, the canonical ledger/runbook
   understate the spend; the settled owner accounting ruling recorded in this
   pending specification is interim evidence for the 3/5 count. Do not invent
   H4 identity; state it as TBD.
2. **Head-bound correction.** Only after reviewed implementation and a fresh
   owner token authorizing the exact land/push may the carriers bind H4 commit,
   blobs/ranges, tests, required CI, owner-host receipts, parity results, freeze,
   packet, and carrier. Any tracked change after review creates a new head and
   requires re-review plus a newly head-bound owner token.

The plan and forward map remain unchanged unless source review identifies a
real semantic contradiction. Do not churn them merely to restate status.

At the later freeze, hash the eight raw files in table order with SHA-256. Hash
exact disk bytes without encoding, BOM, or EOL normalization; record lowercase
digest and raw length. Use the actual freeze date in a newly named
`packet-attempt4/S6-H4-FREEZE-RECORD-<ACTUAL-FREEZE-DATE>.md`, UTF-8 without BOM
and LF endings. The freeze record is not one of its own eight inputs. Never
overwrite a freeze: a correction requires a new suffix and invalidates every
packet/carrier derived from the earlier record.

Generate a wholly fresh
`packet-attempt4/PACKET-ATTEMPT4-<ACTUAL-PACKET-DATE>.md`,
`packet-attempt4/CARRIER-STATUS.md`, AST/synthetic evidence, and independent
dual review. Regenerate the named-target and worktree counts from the actual
Attempt-4 topology; do not copy or guess Attempt 3's count. Every self-identity,
record hash, source head/blob/range, path, nonce field, and count must bind H4
and Attempt 4. State exactly `3 of 5 spent, 2 remain` and include all prior
attempt paths in the retained-residue set.

No previous land token, packet approval, Q12 attestation, GO, signature, or
Attempt-5 permission travels to the new head or Attempt 4.

## Non-goals and residuals

- No generic Python manager, ambient installation change, or global
  `project6.ps1` behavior change.
- No worker-binding, authority-envelope, GO, reservation, or closeout schema
  change; no query/item/file, signer identity, credential, egress, effect-order,
  broker-ordering, AppContainer, or campaign-subject change. A fresh canonical
  storage namespace is not a reservation-semantic or campaign-subject change.
- The terminal chain is append-only operator transcript evidence; it is not a
  worker, reservation, authority, GO, signature, runtime, or closeout schema and
  grants no Attempt-5 authority. The local spent-prefix expectation adds an
  atomic precondition to claim execution without changing those schemas.
- No binding-record-only replacement for direct worker hashing, no seventh
  worker ACE, and no elevated Phase 1b based on the disproven B2 premise.
- No claim that reservation/authority initialization creates ProgramData. The
  ProgramData spent marker remains live-consumption state outside rehearsal.
- No full ambient DLL/stdlib closure attestation. The whole archive pins the
  worker closure separately; this design's equality floor concerns
  `python.exe` only.
- No claim that the vendor/minor launcher tag pins a patch or is immutable.
  Strict bytes fail closed on every host patch and require archive placement,
  new constants, implementation/review, refreeze, and a fresh packet. D3/M7
  must explicitly accept that cost or reopen the floor.
- No claim that repeated Python validation de-risks ACL, initializer, custody,
  owner identity, or mutex behavior; they have separate gates, action guards,
  and rehearsal.
- No host-global, cross-session, or continuous attempt-lifetime exclusion claim;
  the phase-scoped guard is limited to active actions in the production
  `Local\` namespace and the runbook prohibits concurrent sittings between them.
- No deletion, cleanup, rename, or reuse of prior-attempt or rehearsal evidence.
- No private-key access, signing, W5 observation, network, live invocation,
  custody/governance write, land, push, elevation, or Attempt-5 activation
  follows from this specification or from a green test.

## Acceptance criteria

1. This R2 commit changes only this specification in `worktrees/sb-pyfix`; the
   dirty root's Git-visible source state, exact governance/evidence subvector,
   and frozen ceremony worktree remain invariant.
2. D-AROOT paths/DACLs and definitive Attempt-3 accounting are consistent
   everywhere: 3 of 5 spent, Attempts 4 and 5 remain.
3. `-V:PythonCore/3.12` is only a locator; no exact-patch launcher tag survives,
   and PS5.1 `ProcessStartInfo` produces stable launcher failures.
4. The gate is validate-only, has a closed production parameter surface, and
   proves frozen ambient/archive/member bytes before remaining-attempt mutation.
5. Exactly six Python phase gates and their five fixed call-site dispositions are
   executable-tested; the separate post-provision mismatch is terminal
   `ATTEMPT HOLD` and spent.
6. Exactly five governed tool calls invoke the gate-returned absolute `$Py`
   directly with verified absolute tool paths; the Phase-2 pytest/W5 auxiliary
   allowlist also uses call 4's `$Py`; none re-resolves via wrapper or launcher.
7. Every enumerated 3.12.6 tracked literal is re-pinned to exact 3.12.10 under a
   later authorized implementation, with required CI wiring and zero skips.
8. Provisioning hashes and extracts one held stream into the retained
   stage/manifest/content-addressed topology; path reopen, replacement, rename,
   delete, traversal, case, duplicate, and prefix-collision tests discriminate.
9. Attempts 4 and 5 have complete disjoint path/identity vectors. Attempt parent,
    campaign child, and external binding parent receive the exact approved DACL
    atomically in their creation calls, with no create-then-harden path, and use
    the exact emptiness/stage-child contracts; the exhaustive literal mutation/
    worktree vectors have
    asserted regenerated counts plus byte, filesystem-identity, link-count, and
    DACL receipts. Attempt-4 activation proves both vectors absent; Attempt-5
    activation proves sealed Attempt 4 invariant and Attempt 5 absent. Every
    applicable state/containment check precedes creation.
10. The phase-scoped family action guard has executable mutex-name parity and
    ordering, clears stale Win32 last error before acquisition, encloses each
    whole governed callback, proves live/non-runtime composition and cleanup,
    and fails closed without changing production `_mutex_name` derivation or
    overstating its `Local\` session scope.
11. Ordinary and elevated shells equal one frozen owner SID before custody; that
    SID equals the profile/worker broker SID afterward. Exact six-ACE ACL with
    broker mask `0x001200A9`, filtered-token full bundle validation/direct hash,
    and denial of the no-matching-principal/no-backup-or-restore-privilege
    negative control pass without ACL mutation or elevation of Phase 1b.
12. The separately authorized integrated rehearsal proves first-create success,
    protected empty binding-parent custody, same-path create-once HOLD with
    unchanged bytes, live owner-host observation of the transient journal's
    frozen safe posture, and no staging/`-journal` residue; it also proves fresh
    non-elevated Phase 1b, unsigned template cleanup, and no ProgramData/live/
    signature effect.
13. Attempts 1-3 residue, the exact eight carriers, sealed historical evidence
    roots, both archive versions, the create-once Attempt-4 terminal transcript
    chain, and any valid spent-marker prefix are preserved by raw-byte/identity/
    security manifests. Attempt 5 requires the complete prior baseline/release
    chain, enforces the marker prefix again inside the exclusive claim lock before
    exactly one canonical append, and never deletes, truncates, rewrites, or
    reuses failed/rehearsal namespaces or marker history. Every owner-
    adjudication transition requires a durably published protected create-once
    receipt bound to attempt, head, carrier prefix, operation, disposition, and
    the exact cumulative prior-receipt set. Orphans are preserved under fresh-
    nonce authority, and missing-release recovery is accepted only through the
    exact release-bound parent/receipt delta; mode alone grants no recovery
    authority.
14. Head-independent accounting and head-bound H4 reconciliation remain
    separate; the exact eight-carrier current-authority and raw-byte freeze rules
    are followed only after separate authorization.
15. Freeze/packet names use their actual future dates and actual regenerated
    counts; no historical freeze or carrier is overwritten.
16. D2-D5, exact-host ordinary/elevated GREEN, external rehearsal, implementation,
    governance write, land/push, signing, key, network, and live acts are never
    presented as already approved or executed.
17. Independent written-spec review finds no unresolved critical or major
    defect before implementation planning begins.
18. No later test or review success is treated as a GO, signature, land token,
    Attempt-5 activation, or live-execution authority.

## Recommendation invalidation conditions

Reopen before implementation if the vendor/minor locator fails or diverges
between fresh ordinary/elevated shells; either token differs from the frozen
owner SID; the owner-placed archive/member hashes do not reproduce; full
non-elevated broker validation fails; the disposable initializer/template
rehearsal does not produce the exact first-success/second-HOLD behavior or the
owner-host journal hook cannot observe/reproduce the frozen safe posture; guard
name parity, full-callback exclusion, cross-token behavior, or deterministic
cleanup cannot be proved; the exhaustive retained/worktree vectors or referenced
AppContainer profiles cannot be resolved; Attempt-5 ProgramData state is
indeterminate; 3.12.10 worker tests drift; the owner selects the relaxed D3/M7
floor; or a canonical governing record establishes that Python 3.12.6 itself—
not merely ambient/worker identity—is mandatory.
