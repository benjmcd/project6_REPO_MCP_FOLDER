# ScienceBase Live-Readiness Tranche

## Current status

This is the canonical prospective Lane B planning and status surface. It is not live authority, owner GO, an authority envelope, a launch token, credential authority, or permission to acquire from ScienceBase.

R3 is not implementation-ready for Attempt 4: the exact-host DELETE-journal characterization failed the frozen safe-posture requirement, so the design is reopened and Attempt 4 remains HOLD. The prospective commands below document the closed topology and evidence contract; none may be used to create custody, sign, launch, or close out until that journal blocker is separately resolved and reviewed.

The `codex/sb-live-impl` subject was pushed to `project6-origin` per the recorded push and remains unlanded on `main`. Attempts 1-3 are spent and preserved; exactly 3 of the 5 owner-budgeted attempts are spent, so Attempts 4 and 5 remain. No live GO was issued or consumed and no signed live acquisition has occurred. Two non-authorizing characterization runs made one and three ScienceBase GETs respectively, per the recorded characterization records; no credential was placed or inspected, and production live-run egress was not activated. The waived B0 Windows proof remains `OWNER-WAIVED/UNPROVEN`, never PASS.

## Selected tranche

Implement one efficient, complete end-to-end live-readiness tranche for exactly one bounded ScienceBase acquisition. Keep the tightly coupled path in one coherent implementation PR so review and required CI prove the whole authority-to-closeout chain without serial planning or integration PRs.

The tranche includes only what is mechanically required for:

- exact, one-use owner-GO binding without treating the authority envelope as GO;
- credentialless public acquisition with default-off, capability-scoped egress posture;
- one bounded ScienceBase acquisition through the landed B0 broker and durable pre-effect reservation controls;
- durable, secret-free terminal outcome evidence;
- terminal containment and cleanup after success, failure, or ambiguity;
- independent verification and clean closeout.

## Boundaries

Reuse landed B0. Minimize PR, review, and GitHub Actions cycles. Exclude NRC, a second producer, UI, generic frameworks, historical campaign-receipt choreography, and speculative retry. Any reservation, external-effect ambiguity, authority drift, or containment uncertainty remains HOLD with no retry.

Planning and implementation readiness never substitute for a later direct owner GO binding the exact prepared acquisition.

## Remaining-attempt topology and guarded phase contract

Attempts 4 and 5 are separate protected custody families. Paths are selected from this fixed table as one row; never suffix sidecars independently.

| Surface | Attempt 4 | Attempt 5 |
| --- | --- | --- |
| custody parent | `C:\owner-controlled\project6-attempt-4` | `C:\owner-controlled\project6-attempt-5` |
| canonical campaign child | `C:\owner-controlled\project6-attempt-4\sciencebase-campaign` | `C:\owner-controlled\project6-attempt-5\sciencebase-campaign` |
| authority envelope | `C:\owner-controlled\project6-attempt-4\sciencebase-authority.json` | `C:\owner-controlled\project6-attempt-5\sciencebase-authority.json` |
| GO / detached signature | `C:\owner-controlled\project6-attempt-4\owner-go.json` / `C:\owner-controlled\project6-attempt-4\owner-go.json.sig` | `C:\owner-controlled\project6-attempt-5\owner-go.json` / `C:\owner-controlled\project6-attempt-5\owner-go.json.sig` |
| elevated / non-elevated transcripts | `C:\owner-controlled\project6-attempt-4\attempt4-elevated-transcript.txt` / `C:\owner-controlled\project6-attempt-4\attempt4-nonelevated-transcript.txt` | `C:\owner-controlled\project6-attempt-5\attempt5-elevated-transcript.txt` / `C:\owner-controlled\project6-attempt-5\attempt5-nonelevated-transcript.txt` |
| binding parent | `C:\owner-controlled\project6-bindings-4` | `C:\owner-controlled\project6-bindings-5` |
| W5 scratch | `C:\owner-controlled\project6-w5obs-4` | `C:\owner-controlled\project6-w5obs-5` |
| worker root | `C:\p6-sciencebase-worker-4` | `C:\p6-sciencebase-worker-5` |

Each custody parent has a protected inheritable owner-and-SYSTEM-only FullControl DACL; its campaign child has a separate protected non-inheritable owner-and-SYSTEM-only FullControl DACL. Bindings, W5 scratch, and worker roots remain outside both custody families. Attempts remain strictly serial. Attempt 5 remains absent until separately authorized; this tranche adds no Attempt-5 activation, release, recovery, parser, serializer, or disposition machinery. A failed Attempt-4 family is preserved and never cleaned, renamed, repaired, or reused.

The validate-only Python binding gate runs exactly six times, and only its returned `ambient_interpreter` may become `$Py`. The wrapper modes are closed: `NonRuntime` accepts only `-Mode NonRuntime -Action { ... }`; `LiveRuntime` accepts only the four parameters `Mode`, `CurrentRoot`, `Py`, and `PyArgumentList`, never `Action`. The live wrapper invokes the exact `$Py` process inside its lease and returns that child's exit semantics.

| Gate call | Fresh-shell point and guarded extent | Failure disposition |
| ---: | --- | --- |
| 1 | ordinary pre-sitting `NonRuntime`; frozen owner/current SID and retained Attempt-3 proof before Attempt-4 custody | `PRE-SITTING HOLD` |
| 2 | elevated `NonRuntime`; owner/current SID and Python parity before custody | `PRE-SITTING HOLD` |
| 3 | same elevated `NonRuntime` callback after custody validation and before `$P1_IexBegun`; guard stays held through provisioning, both initializers, and the Phase-1 record | `PRE-BEGIN HOLD` |
| 4 | fresh non-elevated Phase-1b `NonRuntime`; rehydration, both Phase-2 pytest checks, W5, and unsigned-template emission | terminal `ATTEMPT HOLD` |
| 5 | immediately before the separately owner-authorized `LiveRuntime` invocation | terminal `SIGNED-AUTHORITY HOLD` before callback entry; after entry, durable live evidence controls the result |
| 6 | post-live `NonRuntime`; no-live closeout only | `POST-LIVE CLOSEOUT HOLD` |

Thus calls 1-2 are `PRE-SITTING HOLD`; call 3 is `PRE-BEGIN HOLD`; call 4 is terminal `ATTEMPT HOLD`; call 5 is terminal `SIGNED-AUTHORITY HOLD`; call 6 is `POST-LIVE CLOSEOUT HOLD`. Guard failures map at the same phase boundary. The `Local\` guard serializes active governed actions in the same Windows session; shell-transition gaps remain governed by the one-action/no-concurrent-sitting rule. It is not a host-global or continuous attempt-lifetime lease.

### Ordinary pre-sitting call 1

Run this in a fresh ordinary Windows PowerShell 5.1 shell before creating any Attempt-4 custody, binding, profile, nonce, or worker state. First load the `$NewPreservationBaseline` and `$AssertPreservationUnchanged` definitions from the next subsection in that same shell; loading them performs no action. The retained Attempt-3 paths are owner-filled from the preservation baseline; this check hashes the retained worker interpreter directly and does not substitute a binding hash.

```powershell
$RepositoryRoot = (Get-Location).Path
$PythonArchive = 'C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip'
$PythonGate = Join-Path $RepositoryRoot 'scripts\validate-dual-live-python-binding.ps1'
$FamilyGuard = Join-Path $RepositoryRoot 'scripts\invoke-dual-live-family-guard.ps1'
$ExpectedOwnerSid = '<OWNER-FILL frozen owner SID>'
$ExpectedAmbientInterpreter = '<OWNER-FILL frozen ambient interpreter>'
$Attempt3ProfileBinding = '<OWNER-FILL retained Attempt-3 profile binding>'
$Attempt3WorkerBinding = '<OWNER-FILL retained Attempt-3 worker binding>'
$RetainedAttempt3InterpreterBytes = 103704
$RetainedAttempt3InterpreterSha256 = '737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae'
if (@(
  $ExpectedOwnerSid, $ExpectedAmbientInterpreter,
  $Attempt3ProfileBinding, $Attempt3WorkerBinding
).Where({ [string]::IsNullOrWhiteSpace($_) -or $_ -like '<OWNER-FILL*' }).Count -ne 0) {
  throw 'PRE-SITTING HOLD: frozen owner or retained Attempt-3 input missing.'
}

& $FamilyGuard -Mode NonRuntime -Action {
  if ($null -eq $NewPreservationBaseline -or $null -eq $AssertPreservationUnchanged) {
    throw 'PRE-SITTING HOLD: preservation actions are not loaded.'
  }
  $PreservationContext = & $NewPreservationBaseline -AmbientInterpreter $ExpectedAmbientInterpreter
  $CurrentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  if ([string]::IsNullOrWhiteSpace($CurrentSid) -or $CurrentSid -cne $ExpectedOwnerSid) {
    throw 'PRE-SITTING HOLD: sciencebase_owner_identity_mismatch'
  }

  # Python binding gate call 1 of 6.
  $PythonBinding = & $PythonGate -PythonArchive $PythonArchive
  if ($LASTEXITCODE -ne 0 -or $null -eq $PythonBinding -or $PythonBinding.status -cne 'PYTHON_BINDING_OK') {
    throw 'PRE-SITTING HOLD: binding gate 1 failed.'
  }
  $Py = [string]$PythonBinding.ambient_interpreter
  if ([IO.Path]::GetFullPath($Py) -cne [IO.Path]::GetFullPath($ExpectedAmbientInterpreter)) {
    throw 'PRE-SITTING HOLD: gate-bound ambient interpreter path drift.'
  }

  $PriorAttempt3BundleBinding = $env:PROJECT6_B0_BUNDLE_BINDING
  $PriorBytecode = $env:PYTHONDONTWRITEBYTECODE
  $PriorPytestAddopts = $env:PYTEST_ADDOPTS
  $OriginalLocation = (Get-Location).Path
  try {
    $env:PROJECT6_B0_BUNDLE_BINDING = $Attempt3WorkerBinding
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTEST_ADDOPTS = '-p no:cacheprovider'
    Set-Location -LiteralPath $RepositoryRoot
    & $Py -m pytest .\tests\test_dual_live_worker_bundle.py::test_windows_probe_validates_preprovisioned_fixture -q
    $RetainedValidationExit = $LASTEXITCODE
  } finally {
    $env:PROJECT6_B0_BUNDLE_BINDING = $PriorAttempt3BundleBinding
    $env:PYTHONDONTWRITEBYTECODE = $PriorBytecode
    $env:PYTEST_ADDOPTS = $PriorPytestAddopts
    Set-Location -LiteralPath $OriginalLocation
  }
  if ($RetainedValidationExit -ne 0) {
    throw 'PRE-SITTING HOLD: retained Attempt-3 production bundle validation failed.'
  }

  $RetainedProfile = Get-Content -Raw -LiteralPath $Attempt3ProfileBinding | ConvertFrom-Json
  $RetainedWorker = Get-Content -Raw -LiteralPath $Attempt3WorkerBinding | ConvertFrom-Json
  if (
    [string]$RetainedProfile.broker_sid -cne $CurrentSid -or
    [string]$RetainedWorker.broker_sid -cne $CurrentSid -or
    [string]$RetainedProfile.profile_moniker -cne [string]$RetainedWorker.profile_moniker -or
    [string]$RetainedWorker.python_version -cne '3.12.6' -or
    [string]$RetainedWorker.architecture -cne 'amd64' -or
    [string]$RetainedWorker.interpreter -cne 'python.exe'
  ) { throw 'PRE-SITTING HOLD: retained bundle binding or broker/current SID mismatch.' }

  $RetainedWorkerInterpreter = Join-Path ([string]$RetainedWorker.root) ([string]$RetainedWorker.interpreter)
  $RetainedWorkerItem = Get-Item -Force -LiteralPath $RetainedWorkerInterpreter
  $RetainedWorkerSha256 = (Get-FileHash -LiteralPath $RetainedWorkerInterpreter -Algorithm SHA256).Hash.ToLowerInvariant()
  if (
    $RetainedWorkerItem.Length -ne $RetainedAttempt3InterpreterBytes -or
    ($RetainedWorkerItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
    $RetainedWorkerSha256 -cne $RetainedAttempt3InterpreterSha256
  ) {
    throw 'PRE-SITTING HOLD: retained Attempt-3 3.12.6 worker interpreter drift.'
  }
  "RETAINED_ATTEMPT3_WORKER_SHA256=$RetainedWorkerSha256"
  & $AssertPreservationUnchanged $PreservationContext
}
```

### Exhaustive pre/post preservation receipts

Before any mutation-capable Attempt-4 action, run the following inside the ordinary call-1 `NonRuntime` lease. Regenerate it once more after the complete validate-only pre-activation checks and before leaving that same lease. These two snapshots prove that the validation action itself seeded nothing; they do not claim that the later, separately authorized custody/live action leaves the deliberately created Attempt-4 family unchanged. The reviewed helper is validate-only: it returns canonical JSON and counts to the caller and writes no report. Wildcards, category-only claims, guessed counts, unresolved profiles, omitted children, or an unclassified path are HOLD.

```powershell
$NewPreservationBaseline = {
param([Parameter(Mandatory = $true)][string]$AmbientInterpreter)
$ReceiptHelper = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot 'scripts\validate-dual-live-preservation-receipts.ps1'))
$CeremonyCheckout = '<OWNER-FILL exact quiesced ceremony checkout>'
$CanonicalInbox = 'C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\state\agent-inbox'
$GovernanceCarriers = @(
  (Join-Path $CanonicalInbox 'plan-of-record-sciencebase-signed-go-2026-08-12.md'),
  (Join-Path $CanonicalInbox 'SITTING-RUNBOOK-2026-08-14.md'),
  (Join-Path $CanonicalInbox 'Q12-EVIDENCE-POINTER-INDEX-2026-08-15.md'),
  (Join-Path $CanonicalInbox 'owner-decision-sheet-sciencebase-signed-go-2026-08-12.md'),
  (Join-Path $CanonicalInbox 'amendment-addendum-v1.1-sciencebase-signed-go-2026-08-12.md'),
  (Join-Path $CanonicalInbox 'forward-map-signed-go-lane-2026-08-13.md'),
  (Join-Path $CanonicalInbox 'HANDOFF-SESSION-CONTINUATION-2026-08-14.md'),
  (Join-Path $CanonicalInbox 'AUDIT-LEDGER-2026-08-14.md')
)
$HistoricalRoots = @(
  (Join-Path $CanonicalInbox 'session-8e8b798b-archive'),
  (Join-Path $CanonicalInbox 'session-9ee3527a-adversarial-pass'),
  (Join-Path $CanonicalInbox 'characterization-record-2026-08-13'),
  (Join-Path $CanonicalInbox 'characterization-record-2-2026-08-14')
)
$RecursiveRetainedRoots = @(
  'C:\owner-controlled\project6',
  'C:\owner-controlled\project6-bindings',
  'C:\owner-controlled\project6-bindings-3',
  'C:\owner-controlled\project6-w5obs',
  'C:\owner-controlled\project6-w5obs-3',
  'C:\p6-sciencebase-worker-2',
  'C:\p6-sciencebase-worker-3'
)
$FrozenImmediateChildren = @{
  'C:\owner-controlled\project6' = @('<OWNER-FILL exact immediate child>')
  'C:\owner-controlled\project6-bindings' = @('<OWNER-FILL exact immediate child>')
  'C:\owner-controlled\project6-bindings-3' = @('<OWNER-FILL exact immediate child>')
  'C:\owner-controlled\project6-w5obs' = @('<OWNER-FILL exact immediate child>')
  'C:\owner-controlled\project6-w5obs-3' = @('<OWNER-FILL exact immediate child>')
  'C:\p6-sciencebase-worker-2' = @('<OWNER-FILL exact immediate child>')
  'C:\p6-sciencebase-worker-3' = @('<OWNER-FILL exact immediate child>')
  (Join-Path $CanonicalInbox 'session-8e8b798b-archive') = @('<OWNER-FILL exact immediate child>')
  (Join-Path $CanonicalInbox 'session-9ee3527a-adversarial-pass') = @('<OWNER-FILL exact immediate child>')
  (Join-Path $CanonicalInbox 'characterization-record-2026-08-13') = @('<OWNER-FILL exact immediate child>')
  (Join-Path $CanonicalInbox 'characterization-record-2-2026-08-14') = @('<OWNER-FILL exact immediate child>')
  'C:\owner-controlled\project6\sciencebase-campaign' = @('<OWNER-FILL exact immediate child>')
  '<OWNER-FILL exact Attempt-1 appcontainer profile root>' = @('<OWNER-FILL exact immediate child>')
  '<OWNER-FILL exact Attempt-2 appcontainer profile root>' = @('<OWNER-FILL exact immediate child>')
  '<OWNER-FILL exact Attempt-3 appcontainer profile root>' = @('<OWNER-FILL exact immediate child>')
}
$LoadBearingLeaves = @(
  '<OWNER-FILL exact Attempt-1 phase record>',
  '<OWNER-FILL exact Attempt-1 stranded profile binding>',
  '<OWNER-FILL exact Attempt-2 elevated transcript>',
  '<OWNER-FILL exact Attempt-3 elevated transcript>',
  '<OWNER-FILL exact Attempt-2 profile binding>',
  '<OWNER-FILL exact Attempt-3 profile binding>',
  '<OWNER-FILL exact Attempt-3 worker binding>',
  '<OWNER-FILL exact Attempt-1 appcontainer profile root>',
  '<OWNER-FILL exact Attempt-2 appcontainer profile root>',
  '<OWNER-FILL exact Attempt-3 appcontainer profile root>',
  'C:\owner-controlled\project6\sciencebase-campaign',
  'C:\owner-controlled\project6\python-3.12.6-embed-amd64.zip',
  'C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip',
  ([IO.Path]::GetFullPath($AmbientInterpreter))
)
if ($LoadBearingLeaves.Where({ $_ -like '<OWNER-FILL*' }).Count -ne 0) {
  throw 'PRE-SITTING HOLD: exhaustive load-bearing leaf table is incomplete.'
}
$AttemptTopology = @(
  [pscustomobject]@{ Attempt=4; Role='custody-parent'; Path='C:\owner-controlled\project6-attempt-4' },
  [pscustomobject]@{ Attempt=4; Role='campaign'; Path='C:\owner-controlled\project6-attempt-4\sciencebase-campaign' },
  [pscustomobject]@{ Attempt=4; Role='authority'; Path='C:\owner-controlled\project6-attempt-4\sciencebase-authority.json' },
  [pscustomobject]@{ Attempt=4; Role='go'; Path='C:\owner-controlled\project6-attempt-4\owner-go.json' },
  [pscustomobject]@{ Attempt=4; Role='signature'; Path='C:\owner-controlled\project6-attempt-4\owner-go.json.sig' },
  [pscustomobject]@{ Attempt=4; Role='elevated-transcript'; Path='C:\owner-controlled\project6-attempt-4\attempt4-elevated-transcript.txt' },
  [pscustomobject]@{ Attempt=4; Role='nonelevated-transcript'; Path='C:\owner-controlled\project6-attempt-4\attempt4-nonelevated-transcript.txt' },
  [pscustomobject]@{ Attempt=4; Role='binding-parent'; Path='C:\owner-controlled\project6-bindings-4' },
  [pscustomobject]@{ Attempt=4; Role='w5'; Path='C:\owner-controlled\project6-w5obs-4' },
  [pscustomobject]@{ Attempt=4; Role='worker'; Path='C:\p6-sciencebase-worker-4' },
  [pscustomobject]@{ Attempt=5; Role='custody-parent'; Path='C:\owner-controlled\project6-attempt-5' },
  [pscustomobject]@{ Attempt=5; Role='campaign'; Path='C:\owner-controlled\project6-attempt-5\sciencebase-campaign' },
  [pscustomobject]@{ Attempt=5; Role='authority'; Path='C:\owner-controlled\project6-attempt-5\sciencebase-authority.json' },
  [pscustomobject]@{ Attempt=5; Role='go'; Path='C:\owner-controlled\project6-attempt-5\owner-go.json' },
  [pscustomobject]@{ Attempt=5; Role='signature'; Path='C:\owner-controlled\project6-attempt-5\owner-go.json.sig' },
  [pscustomobject]@{ Attempt=5; Role='elevated-transcript'; Path='C:\owner-controlled\project6-attempt-5\attempt5-elevated-transcript.txt' },
  [pscustomobject]@{ Attempt=5; Role='nonelevated-transcript'; Path='C:\owner-controlled\project6-attempt-5\attempt5-nonelevated-transcript.txt' },
  [pscustomobject]@{ Attempt=5; Role='binding-parent'; Path='C:\owner-controlled\project6-bindings-5' },
  [pscustomobject]@{ Attempt=5; Role='w5'; Path='C:\owner-controlled\project6-w5obs-5' },
  [pscustomobject]@{ Attempt=5; Role='worker'; Path='C:\p6-sciencebase-worker-5' }
)
$MustRemainAbsentBeforeAttempt4 = @(
  '<OWNER-FILL exact Attempt-3 non-elevated transcript path>',
  'C:\owner-controlled\project6\sciencebase-campaign\reservation.db',
  'C:\owner-controlled\project6\sciencebase-authority.json',
  'C:\owner-controlled\project6\owner-go.json',
  'C:\owner-controlled\project6\owner-go.json.sig',
  'C:\ProgramData\Project6'
)
if ($MustRemainAbsentBeforeAttempt4.Where({ $_ -like '<OWNER-FILL*' }).Count -ne 0) {
  throw 'PRE-SITTING HOLD: must-remain-absent table is incomplete.'
}
if (
  $CeremonyCheckout -like '<OWNER-FILL*' -or
  -not (Test-Path -LiteralPath $ReceiptHelper -PathType Leaf) -or
  ((Get-Item -Force -LiteralPath $ReceiptHelper).Attributes -band [IO.FileAttributes]::ReparsePoint) -or
  @($FrozenImmediateChildren.Keys).Where({ $_ -like '<OWNER-FILL*' }).Count -ne 0 -or
  @($FrozenImmediateChildren.Values | ForEach-Object { @($_) } | Where-Object {
    [string]$_ -like '<OWNER-FILL*'
  }).Count -ne 0
) { throw 'PRE-SITTING HOLD: preservation receipt inputs are incomplete.' }

function New-ClosedMutationEntry(
  [string]$Class,
  [string]$Path,
  [ValidateSet('present','absent')][string]$Expected,
  [bool]$Recurse,
  [string[]]$AllowedChildren
) {
  [pscustomobject][ordered]@{
    Class = $Class
    Path = $Path
    Expected = $Expected
    Recurse = $Recurse
    AllowedChildren = @($AllowedChildren)
  }
}

$MutationVector = @(
  @($RecursiveRetainedRoots | ForEach-Object {
    New-ClosedMutationEntry -Class 'retained-root' -Path $_ -Expected 'present' -Recurse $true -AllowedChildren $FrozenImmediateChildren[$_]
  })
  @($GovernanceCarriers | ForEach-Object {
    New-ClosedMutationEntry -Class 'governance-carrier' -Path $_ -Expected 'present' -Recurse $false -AllowedChildren @()
  })
  @($HistoricalRoots | ForEach-Object {
    New-ClosedMutationEntry -Class 'historical-root' -Path $_ -Expected 'present' -Recurse $true -AllowedChildren $FrozenImmediateChildren[$_]
  })
  @($LoadBearingLeaves | ForEach-Object {
    $KnownChildren = $FrozenImmediateChildren[$_]
    New-ClosedMutationEntry -Class 'load-bearing-leaf' -Path $_ -Expected 'present' -Recurse ($null -ne $KnownChildren) -AllowedChildren @($KnownChildren)
  })
  @($AttemptTopology | ForEach-Object {
    [pscustomobject][ordered]@{ Class="attempt-$($_.Attempt)-$($_.Role)"; Path=$_.Path; Expected='absent'; Recurse=$false; AllowedChildren=@() }
  })
  @($MustRemainAbsentBeforeAttempt4 | ForEach-Object {
    [pscustomobject][ordered]@{ Class='must-remain-absent'; Path=$_; Expected='absent'; Recurse=$false; AllowedChildren=@() }
  })
)
$BoundaryRoots = @(
  $RepositoryRoot,
  $CeremonyCheckout,
  'C:\owner-controlled\project6-rehearsal',
  'C:\owner-controlled\project6-bindings-rehearsal',
  'C:\owner-controlled\project6-w5obs-rehearsal',
  'C:\p6-sciencebase-worker-rehearsal'
)

. $ReceiptHelper
$BeforeReceipt = New-DualLivePreservationReceipt -MutationVector $MutationVector -RepositoryRoot $RepositoryRoot -BoundaryRoot $BoundaryRoots -QualifyNonDriveAgainst 'C:\'
if ($BeforeReceipt.Status -cne 'PRESERVATION_RECEIPT_OK') { throw 'PRE-SITTING HOLD: preservation baseline failed.' }
$MutationVector = @($BeforeReceipt.MutationVector)
$WorktreeVector = @($BeforeReceipt.WorktreeVector)
"MUTATION_VECTOR_COUNT=$($BeforeReceipt.MutationCount)"
"WORKTREE_VECTOR_COUNT=$($BeforeReceipt.WorktreeCount)"
$WorktreeVector | ForEach-Object { "WORKTREE_ROOT=$($_.Path)" }
[pscustomobject]@{
  ReceiptHelper = $ReceiptHelper
  RepositoryRoot = $RepositoryRoot
  BoundaryRoots = [string[]]$BoundaryRoots
  MutationVector = [object[]]$MutationVector
  BeforeReceipt = $BeforeReceipt
}
}

$AssertPreservationUnchanged = {
param([Parameter(Mandatory = $true)][object]$Context)
. $Context.ReceiptHelper
# Invoke only after every validate-only pre-activation check and before the
# guarded callback returns. This call regenerates both vectors and their counts.
$AfterReceipt = New-DualLivePreservationReceipt -MutationVector $Context.MutationVector -RepositoryRoot $Context.RepositoryRoot -BoundaryRoot $Context.BoundaryRoots -QualifyNonDriveAgainst 'C:\'
if (
  $AfterReceipt.Status -cne 'PRESERVATION_RECEIPT_OK' -or
  $Context.BeforeReceipt.MutationCount -ne $AfterReceipt.MutationCount -or
  $Context.BeforeReceipt.WorktreeCount -ne $AfterReceipt.WorktreeCount -or
  $Context.BeforeReceipt.CanonicalJson -cne $AfterReceipt.CanonicalJson
) { throw 'PRE-SITTING HOLD: preservation receipt drift.' }
'BEFORE_AFTER_IDENTICAL'
}
```

The real helper parses one successful `git worktree list --porcelain`, rejects malformed or duplicate records, qualifies non-drive roots against `C:\`, and sorts and counts the complete `$WorktreeVector`. For every worktree it captures path, HEAD, branch/detached state, raw `git status --porcelain=v1 -z --untracked-files=all` bytes, raw `git diff --binary` and `git diff --cached --binary` bytes, and a deterministic type/length/SHA manifest for every untracked path without following reparse points. Each external entry includes existence, rooted type, raw `ReparseData`, `VolumeIdentity`, `FileIdentity`, `LinkCount`, `CreationTimeUtc`, `LastWriteTimeUtc`, length/hash, owner SID, `DaclProtected`, `OrderedSddl`, and `SortedAceTuples`; last-access time, SACL, and primary group are excluded. The eight exact governance carriers and four historical roots are independently hashed. Every candidate family/binding/W5/worker/rehearsal/scratch path is boundary-compared with every worktree and named repository/ceremony root. Before Attempt-5 activation, the sealed Attempt-4 vector must be present and identical while every Attempt-5 path remains absent; that later activation proof and consumer remain separately owner-gated and absent from this tranche.

C5 rehearsal root population is pending the owner-gated R4 journal resolution. The four generic rehearsal paths in `$BoundaryRoots` are comparison anchors only, not claimed present artifacts or completed rehearsal evidence. The later owner packet must freeze unique exact rehearsal custody, binding, W5, worker, and scratch roots. After the guarded Phase-1-through-template rehearsal completes, those exact roots and their closed immediate-child sets must be added to `$MutationVector` as present recursive receipts and pairwise boundary-compared with every other candidate and anchor. Until those owner-filled paths exist and are receipted, this document cannot yet claim an exhaustive pre-Attempt-4 preservation baseline.

## Implemented local state

The tranche reuses B0's default-off broker, zero-capability worker, reservation-before-effect transport, exact ScienceBase producer, and containment path. It adds a canonical external GO document bound to the exact envelope, worker manifest, request, credentialless public posture, and capability-scoped egress posture; mandatory authentication of those exact GO bytes and digest by the pinned Project6 owner Ed25519 identity; a run-scoped create-once GO-consumption event; a content-addressed public artifact plus secret-free terminal event; and a separate verifier that requires the exact three durable reservations, rehashes the artifact, rejects HTML/XML-shaped error content, and records one closeout event. The owner-ratified D6 reversal removes the pre-consume HEAD health gate: within the broker/runtime chain the order is consume-exact GO, first durable reservation, then the first outbound runtime request, the reserved ordinal-1 GET. That GET doubles as the sole audited runtime availability observation instead of adding a probe; no broker HEAD or other unreserved runtime availability request precedes the reservation. Any missing or invalid owner signature, drift, prior GO, reservation mismatch, external-effect ambiguity, terminal-evidence failure, content-shape rejection, or containment uncertainty remains HOLD with no retry. A redirect, 5xx response, target flap, or inactivity-permitted response that cannot complete before the session watchdog expires, including a slow-trickle degraded target, is an accepted fail-closed member of this burn set: it yields no artifact or `VERIFIED` closeout, only a burned one-use signature, and never authorizes automatic retry. Recovery requires investigation, a freshly prepared run, and a fresh owner-authorized signed GO; the burned run and signature are not reused.

The enclosing session watchdog and each worker-frame read retain the 135,000 ms fail-closed total-time ceiling calculated from the configured quantities: `3 * (max_redirect_hops + 1)` request slots at the 30-second ScienceBase inactivity timeout, the 30-second worker-exit wait, and the named 15-second launch/IPC overhead. For the bound no-redirect request, those accounting inputs are 90,000 ms, 30,000 ms, and 15,000 ms respectively, below the Windows boundary's existing 15-minute validity limit. A request timeout limits the permitted inactivity gap between socket reads; it is not a total response-duration bound. Consequently, this ceiling is not a worst-case wall-clock sum or a guarantee that every inactivity-permitted response completes. Any response still running when the session watchdog expires fails closed with `broker_session_deadline`, produces no artifact or `VERIFIED` closeout, and burns the one-use signature as documented above.

## Mandatory same-sitting pre-signature stability gate

The following block defines `Invoke-W5Observation`; it does not run W5 by itself. Define it in the fresh Phase-1b shell, then invoke it exactly once inside gate call 4's `NonRuntime` callback. It accepts only the gate-4 `$Py`; it neither resolves nor carries an interpreter across shells. When invoked, it records three complete same-sitting search -> hydrate -> download observations using saved response bytes and separate saved headers. Every stage must report exact HTTP 200 with no `Location` header. Any non-200, `Location`, curl failure, parse failure, membership/file/URI drift, or interruption invalidates the complete set; restart with three fresh complete attempts in the same sitting. Retain only the timestamped stage records, exact URIs, status, body SHA-256, body byte length, and derived download URI with the owner packet. Raw vendor bodies and headers are always removed in `finally`.

```powershell
function Invoke-W5Observation {
param([Parameter(Mandatory = $true)][string]$Py)

$ExactSearchUrl = '<OWNER-FILL exact bound search URL>'
$ExactHydrateUrl = '<OWNER-FILL exact bound item hydrate URL>'
$ExactDownloadUrl = '' # optional confirmatory value only; hydrate remains authoritative
$ExactItemId = '<OWNER-FILL exact target item ID>'
$ExactFileName = '<OWNER-FILL exact elected filename>'
$ObservationRoot = '<OWNER-FILL existing non-repo W5 scratch root>'
$W5CanonicalRoot = '<OWNER-FILL canonical campaign root>'
$CeremonyCheckout = '<OWNER-FILL later quiesced ceremony checkout>'
if (@(
  $ExactSearchUrl, $ExactHydrateUrl, $ExactItemId,
  $ExactFileName, $ObservationRoot, $W5CanonicalRoot, $CeremonyCheckout
).Where({ [string]::IsNullOrWhiteSpace($_) -or $_ -like '<OWNER-FILL*' }).Count -ne 0) {
  throw 'W5 exact-chain inputs are incomplete.'
}
$StageUrls = @(
  @{ Name = 'search'; Url = $ExactSearchUrl },
  @{ Name = 'hydrate'; Url = $ExactHydrateUrl }
)

function Test-PathInside([string]$Candidate, [string]$Root) {
  $CandidateFull = [IO.Path]::GetFullPath($Candidate).TrimEnd('\') + '\'
  $RootFull = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
  return $CandidateFull.StartsWith($RootFull, [StringComparison]::OrdinalIgnoreCase)
}

$ObservationRoot = (Resolve-Path -LiteralPath $ObservationRoot).Path
$WorktreeRoots = @(
  & git worktree list --porcelain |
    Where-Object { $_ -like 'worktree *' } |
    ForEach-Object { $_.Substring('worktree '.Length) }
)
if ($LASTEXITCODE -ne 0) { throw 'W5 could not enumerate worktree roots.' }
foreach ($ForbiddenRoot in @($W5CanonicalRoot, $CeremonyCheckout) + $WorktreeRoots) {
  if (
    (Test-PathInside $ObservationRoot $ForbiddenRoot) -or
    (Test-PathInside $ForbiddenRoot $ObservationRoot)
  ) {
    throw 'W5 scratch root must be outside every worktree, the canonical root, and the ceremony checkout.'
  }
}

foreach ($Stage in $StageUrls) {
  $RawUrl = [string]$Stage.Url
  $ParsedUrl = $null
  if (
    $RawUrl -cne $RawUrl.Trim() -or
    -not [uri]::TryCreate($RawUrl, [System.UriKind]::Absolute, [ref]$ParsedUrl) -or
    $ParsedUrl.Scheme -cne 'https' -or
    $ParsedUrl.DnsSafeHost -ine 'www.sciencebase.gov' -or
    -not $ParsedUrl.IsDefaultPort -or
    $ParsedUrl.Port -ne 443 -or
    $ParsedUrl.UserInfo.Length -ne 0 -or
    $RawUrl.Contains('@') -or
    $ParsedUrl.Fragment.Length -ne 0
  ) { throw "W5 URL authority HOLD: $($Stage.Name)" }
}

$DuplicateKeyCheck = @'
import json
import pathlib
import sys

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

json.loads(pathlib.Path(sys.argv[-1]).read_bytes(), object_pairs_hook=reject_duplicates)
'@
function Assert-NoDuplicateJsonKeys([string]$Path) {
  & $Py -c $DuplicateKeyCheck $Path
  if ($LASTEXITCODE -ne 0) { throw "W5 duplicate-key or JSON parse HOLD: $Path" }
}

$ConvertFromJsonRejectsDuplicates = $false
try {
  '{"duplicate":1,"duplicate":2}' | ConvertFrom-Json -ErrorAction Stop | Out-Null
} catch {
  $ConvertFromJsonRejectsDuplicates = $true
}

$ScienceBaseInactivitySeconds = 30
$ConnectTimeoutSeconds = $ScienceBaseInactivitySeconds
$ExactChainStageCount = 3
$MaxTimeSeconds = $ExactChainStageCount * $ScienceBaseInactivitySeconds
$ObservationRecords = [Collections.Generic.List[object]]::new()
$RawPaths = [Collections.Generic.List[string]]::new()
$ObservationSetValid = $false
$BaselineSearchMembership = $null
$BaselineDownloadUrl = $null

function New-W5RawPath([int]$Attempt, [string]$Stage, [string]$Kind) {
  do {
    $Candidate = Join-Path $ObservationRoot (
      'w5-{0}-{1}-{2}-{3}' -f $Attempt, $Stage, $Kind,
      [IO.Path]::GetRandomFileName()
    )
  } while (Test-Path -LiteralPath $Candidate)
  return $Candidate
}

function Invoke-W5Stage(
  [int]$Attempt,
  [string]$Stage,
  [string]$Url,
  [string]$BodyPath,
  [string]$HeaderPath,
  [string]$DerivedDownloadUri
) {
  $HttpStatus = & curl.exe --disable --silent --show-error --proto '=https' `
    --noproxy '*' --globoff --request GET --max-redirs 0 `
    --connect-timeout $ConnectTimeoutSeconds --max-time $MaxTimeSeconds `
    --output $BodyPath --dump-header $HeaderPath --write-out '%{http_code}' -- $Url
  $CurlExit = $LASTEXITCODE
  if ($CurlExit -ne 0 -or $HttpStatus -cne '200') {
    throw "W5 HTTP HOLD: $Stage attempt $Attempt"
  }
  $HeaderText = Get-Content -Raw -LiteralPath $HeaderPath
  if ($HeaderText -match '(?im)^Location\s*:') {
    throw "W5 redirect HOLD: $Stage attempt $Attempt"
  }
  $BodyInfo = Get-Item -LiteralPath $BodyPath
  return [pscustomobject]@{
    Timestamp = (Get-Date).ToString('o')
    Attempt = $Attempt
    Stage = $Stage
    Uri = $Url
    HttpStatus = [string]$HttpStatus
    BodySha256 = (Get-FileHash -LiteralPath $BodyPath -Algorithm SHA256).Hash.ToLowerInvariant()
    BodyBytes = $BodyInfo.Length
    DerivedDownloadUri = $DerivedDownloadUri
  }
}

try {
  try {
    foreach ($Attempt in 1..3) {
      $SearchBody = New-W5RawPath $Attempt 'search' 'body'
      $SearchHeaders = New-W5RawPath $Attempt 'search' 'headers'
      $HydrateBody = New-W5RawPath $Attempt 'hydrate' 'body'
      $HydrateHeaders = New-W5RawPath $Attempt 'hydrate' 'headers'
      $DownloadBody = New-W5RawPath $Attempt 'download' 'body'
      $DownloadHeaders = New-W5RawPath $Attempt 'download' 'headers'
      foreach ($RawPath in @(
        $SearchBody, $SearchHeaders, $HydrateBody, $HydrateHeaders,
        $DownloadBody, $DownloadHeaders
      )) { $RawPaths.Add($RawPath) }

      $SearchRecord = Invoke-W5Stage $Attempt 'search' $ExactSearchUrl $SearchBody $SearchHeaders $null
      Assert-NoDuplicateJsonKeys $SearchBody
      $Search = Get-Content -Raw -LiteralPath $SearchBody | ConvertFrom-Json
      $MatchingItems = @($Search.items | Where-Object { [string]$_.id -ceq $ExactItemId })
      if ($MatchingItems.Count -ne 1) { throw "W5 exact search membership HOLD: attempt $Attempt" }
      $SearchMembership = (@($MatchingItems | ForEach-Object { [string]$_.id }) -join ',')
      if ($null -eq $BaselineSearchMembership) { $BaselineSearchMembership = $SearchMembership }
      if ($SearchMembership -cne $BaselineSearchMembership) { throw 'W5 search membership drift.' }

      $HydrateRecord = Invoke-W5Stage $Attempt 'hydrate' $ExactHydrateUrl $HydrateBody $HydrateHeaders $null
      Assert-NoDuplicateJsonKeys $HydrateBody
      $Hydrate = Get-Content -Raw -LiteralPath $HydrateBody | ConvertFrom-Json
      if ([string]$Hydrate.id -cne $ExactItemId) {
        throw "W5 hydrate item identity HOLD: attempt $Attempt"
      }
      $MatchingFiles = @($Hydrate.files | Where-Object { [string]$_.name -ceq $ExactFileName })
      if ($MatchingFiles.Count -ne 1) {
        throw "W5 exact file membership HOLD: attempt $Attempt"
      }
      $DerivedDownloadUrl = [string]$MatchingFiles[0].downloadUri
      if ([string]::IsNullOrWhiteSpace($DerivedDownloadUrl)) { throw 'W5 hydrate downloadUri missing.' }
      if (
        $MatchingFiles[0].PSObject.Properties.Name -contains 'url' -and
        [string]$MatchingFiles[0].url -cne $DerivedDownloadUrl
      ) { throw 'W5 hydrate url/downloadUri mismatch.' }
      if (
        -not [string]::IsNullOrWhiteSpace($ExactDownloadUrl) -and
        $ExactDownloadUrl -notlike '<OWNER-FILL*' -and
        $ExactDownloadUrl -cne $DerivedDownloadUrl
      ) { throw 'W5 confirmatory/derived download URI mismatch.' }

      $RawUrl = $DerivedDownloadUrl
      $ParsedUrl = $null
      if (
        $RawUrl -cne $RawUrl.Trim() -or
        -not [uri]::TryCreate($RawUrl, [System.UriKind]::Absolute, [ref]$ParsedUrl) -or
        $ParsedUrl.Scheme -cne 'https' -or
        $ParsedUrl.DnsSafeHost -ine 'www.sciencebase.gov' -or
        -not $ParsedUrl.IsDefaultPort -or $ParsedUrl.Port -ne 443 -or
        $ParsedUrl.UserInfo.Length -ne 0 -or $RawUrl.Contains('@') -or
        $ParsedUrl.Fragment.Length -ne 0
      ) { throw 'W5 derived download URI authority HOLD.' }
      if ($null -eq $BaselineDownloadUrl) { $BaselineDownloadUrl = $DerivedDownloadUrl }
      if ($DerivedDownloadUrl -cne $BaselineDownloadUrl) { throw 'W5 derived download URI drift.' }

      $HydrateRecord.DerivedDownloadUri = $DerivedDownloadUrl
      $DownloadRecord = Invoke-W5Stage $Attempt 'download' $DerivedDownloadUrl $DownloadBody $DownloadHeaders $DerivedDownloadUrl
      & $Py -c "import pathlib,sys; c=pathlib.Path(sys.argv[1]).read_bytes().lstrip(); pairs=((b'\xff\xfe\x00\x00','utf-32-le'),(b'\x00\x00\xfe\xff','utf-32-be'),(b'\xff\xfe','utf-16-le'),(b'\xfe\xff','utf-16-be'),(b'\xef\xbb\xbf','utf-8')); b,e=next(((b,e) for b,e in pairs if c.startswith(b)),(b'','utf-8')); t=c[len(b):].decode(e,errors='replace'); t=t.lstrip() if b else t; lines=t.splitlines(); header='DataSource,Commodity,Year,USprod_Primary_kg,USprod_Secondary_kg,Imports_Metal_kg,Imports_GeO2_kg,Exports_kg,Shipments_Gov_kg,Consump_kg,Price_Metal_dkg,Price_GeO2_dkg,NIR_pct'; bad=not t or t.startswith(('<','{','[')); raise SystemExit(0 if not bad and len(lines)>=2 and lines[0]==header and all(line.count(',')+1==13 for line in lines[1:]) else 1)" $DownloadBody
      if ($LASTEXITCODE -ne 0) { throw "W5 download content contract HOLD: attempt $Attempt" }
      $ObservationRecords.Add($SearchRecord)
      $ObservationRecords.Add($HydrateRecord)
      $ObservationRecords.Add($DownloadRecord)
    }
    if ($ObservationRecords.Count -ne (3 * $ExactChainStageCount)) {
      throw 'W5 incomplete observation set.'
    }
    $ObservationSetValid = $true
  } catch {
    $ObservationSetValid = $false
    $ObservationRecords.Clear()
    throw "W5 observation set invalid; three fresh complete attempts in the same sitting are required. $($_.Exception.Message)"
  }
} finally {
  foreach ($RawPath in $RawPaths) {
    if (Test-Path -LiteralPath $RawPath) {
      Remove-Item -LiteralPath $RawPath -Force
    }
  }
}

$ObservationSet = [pscustomobject]@{
  Valid = $ObservationSetValid
  ConvertFromJsonRejectsDuplicates = $ConvertFromJsonRejectsDuplicates
  Records = @($ObservationRecords)
}
return $ObservationSet
}
```

The required exact values are owner-filled from the already prepared request and its known/observed stage bindings; placeholders, empty required values, URI whitespace, any non-HTTPS scheme, any host other than exactly `www.sciencebase.gov`, any non-default port, userinfo or `@`, any fragment, or any drift are HOLD before the first request. `$ExactDownloadUrl` is the sole optional confirmation and may remain empty; hydrate bytes remain authoritative. The single search response is intentionally unpaginated: no max, offset, sort, or pagination parameter is added. The local PowerShell 5.1 duplicate-key probe result is recorded, while the explicit Python duplicate-key check remains mandatory whether or not `ConvertFrom-Json` throws. `curl.exe --disable` ignores ambient curl configuration; the explicit protocol, direct/no-proxy, globbing, redirect, and symbolically derived timeout constraints prevent the observation recipe from silently widening or hanging egress. W5 is the explicit call-4 auxiliary allowlist member alongside the two named pytest commands. It is a separately authorized operator observation outside the broker/runtime run. Its record is mandatory but non-authorizing and is not runtime availability evidence. It reduces burn probability; it does not close R1, authorize W7, replace same-sitting review, become a GO, or alter the first reserved GET as the sole audited runtime availability evidence.

## Prospective disposable integrated rehearsal

The mandatory C5 rehearsal is not the synthetic ACL/helper test in `tests/test_sciencebase_live_readiness_doc.py`; that test is auxiliary coverage only. C5 remains owner-gated and R4-blocked. It must not run until a reviewed journal strategy satisfies the frozen posture across the complete runtime lifecycle and an owner packet freezes a unique rehearsal identity.

That packet must select one fresh UUID-like suffix and derive a protected custody parent, campaign child, external binding parent, W5 root, worker root, and any scratch root from that one suffix. Every rehearsal path must be absent, pairwise boundary-disjoint from all worktrees, named repository/ceremony roots, retained Attempts 1-3, and both remaining-attempt families, and captured by the complete before receipt. It must use the exact frozen owner SID, Python archive, reviewed head, atomic `CreateDirectoryW`/`SECURITY_ATTRIBUTES` helper, final parent/campaign/binding DACLs, exact binding-child stages, broker/current SID checks, full worker validator, and exact-six-ACE worker proof documented below.

The executable Phase-1-through-template blocks below are then instantiated with only those packet-frozen rehearsal paths and fresh rehearsal-only connector-run ID, nonce, profile moniker, GO ID, transcripts, and authority/template outputs. Each ordinary, elevated, and Phase-1b action uses the real closed `NonRuntime` family guard; every Python command uses the gate-returned `$Py`. The elevated action holds its lease through both direct initializers and the machine-readable Phase-1 record. The fresh non-elevated action holds its lease through rehydration, the two exact pytest checks, W5, and unsigned-template emission. The reservation initializer must expose the real DELETE journal to the reviewed observer while its transaction is open. A same-path initializer call and a same-path template call must each fail create-once with byte-identical retained outputs and no staging, journal, `-wal`, or `-shm` residue; they are not idempotent success.

No private key, signature, GO consumption, spent-marker write, worker launch, or network request is permitted in rehearsal. After it completes, the complete after receipt must prove every real Attempt-4/5 and retained path unchanged. The exact rehearsal roots are preserved, added as present recursive receipts with closed child sets, and rechecked before Attempt 4; they are not deleted or generalized back to the candidate anchors.

## Attempt-4 guarded custody, preparation, signing, and actuation

### Atomic custody helper

This helper is the only directory-creation primitive used for the Attempt-4 parent, campaign child, and binding parent. It applies the final descriptor through `SECURITY_ATTRIBUTES` in the successful `CreateDirectoryW` call, fails on an existing path, and exposes only read-only final-state/stage-set assertions after creation.

```powershell
# R3 atomic custody helper
if (-not ('Project6ScienceBaseCustodyNative' -as [type])) {
  Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class Project6ScienceBaseCustodyNative {
    [StructLayout(LayoutKind.Sequential)]
    public struct SECURITY_ATTRIBUTES {
        public int nLength;
        public IntPtr lpSecurityDescriptor;
        [MarshalAs(UnmanagedType.Bool)] public bool bInheritHandle;
    }

    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(
        string sddl, uint revision, out IntPtr descriptor, out uint descriptorBytes);

    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern bool CreateDirectoryW(string path, ref SECURITY_ATTRIBUTES attributes);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr value);

    public static int CreateOnce(string path, string sddl) {
        IntPtr descriptor;
        uint descriptorBytes;
        if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, out descriptor, out descriptorBytes)) {
            return Marshal.GetLastWin32Error();
        }
        try {
            SECURITY_ATTRIBUTES attributes = new SECURITY_ATTRIBUTES();
            attributes.nLength = Marshal.SizeOf(typeof(SECURITY_ATTRIBUTES));
            attributes.lpSecurityDescriptor = descriptor;
            attributes.bInheritHandle = false;
            if (CreateDirectoryW(path, ref attributes)) { return 0; }
            return Marshal.GetLastWin32Error();
        }
        finally { LocalFree(descriptor); }
    }
}
'@
}

function New-CustodyDirectoryOnce([string]$Path, [string]$Sddl) {
  $ERROR_ALREADY_EXISTS = 183
  $CreateError = [Project6ScienceBaseCustodyNative]::CreateOnce($Path, $Sddl)
  if ($CreateError -eq $ERROR_ALREADY_EXISTS) { throw "PRE-BEGIN HOLD: custody path already exists: $Path" }
  if ($CreateError -ne 0) { throw "PRE-BEGIN HOLD: custody create failed ($CreateError): $Path" }
}

function Assert-ExactChildSet([string]$Path, [string[]]$Expected) {
  $Observed = @(Get-ChildItem -Force -LiteralPath $Path | ForEach-Object Name)
  $ExpectedCopy = @($Expected)
  [Array]::Sort($Observed, [StringComparer]::Ordinal)
  [Array]::Sort($ExpectedCopy, [StringComparer]::Ordinal)
  if ($Observed.Count -ne $ExpectedCopy.Count) { throw "ATTEMPT HOLD: child-set count drift: $Path" }
  for ($Index = 0; $Index -lt $Observed.Count; $Index++) {
    if ($Observed[$Index] -cne $ExpectedCopy[$Index]) { throw "ATTEMPT HOLD: child-set drift: $Path" }
  }
}

function Assert-CustodyDirectory([string]$Path, [bool]$Inheritable) {
  $FullPath = [IO.Path]::GetFullPath($Path)
  $Item = Get-Item -Force -LiteralPath $FullPath
  if (-not $Item.PSIsContainer -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw "ATTEMPT HOLD: custody type invalid: $FullPath"
  }
  if ([IO.DriveInfo]::new($Item.PSDrive.Root).DriveType -ne [IO.DriveType]::Fixed) {
    throw "ATTEMPT HOLD: custody volume invalid: $FullPath"
  }
  $Acl = [IO.Directory]::GetAccessControl($FullPath)
  if (
    $Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $ExpectedOwnerSid -or
    -not $Acl.AreAccessRulesProtected -or
    @($Acl.GetAccessRules($false, $true, [Security.Principal.SecurityIdentifier])).Count -ne 0
  ) { throw "ATTEMPT HOLD: custody owner/protection invalid: $FullPath" }
  $ExpectedInheritance = if ($Inheritable) {
    [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
      [Security.AccessControl.InheritanceFlags]::ObjectInherit
  } else { [Security.AccessControl.InheritanceFlags]::None }
  $ExpectedAcl = @{
    $ExpectedOwnerSid = 0x001F01FF
    'S-1-5-18' = 0x001F01FF
  }
  $ObservedAces = @($Acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))
  $Seen = @{}
  if ($ObservedAces.Count -ne 2) { throw "ATTEMPT HOLD: custody ACE count invalid: $FullPath" }
  foreach ($Ace in $ObservedAces) {
    $Sid = $Ace.IdentityReference.Value
    if (
      -not $ExpectedAcl.ContainsKey($Sid) -or $Seen.ContainsKey($Sid) -or
      $Ace.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
      [int]$Ace.FileSystemRights -ne $ExpectedAcl[$Sid] -or $Ace.IsInherited -or
      $Ace.InheritanceFlags -ne $ExpectedInheritance -or
      $Ace.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None
    ) { throw "ATTEMPT HOLD: custody ACE invalid: $FullPath" }
    $Seen[$Sid] = $true
  }
}
```

### Attempt-4 disposition and durable-live helpers

Load these definitions in the fresh non-elevated Attempt-4 shell. Loading them performs no action. The disposition helper creates the selected transcript once if call 4 failed before callback entry, otherwise uses the transcript already open in that shell. It rejects a second line. The durable-live helper is read-only: it never calls or changes `claim_exact`; it distinguishes exact secure absence from the exact current-GO marker and treats any identity, security, shape, lock, or read ambiguity conservatively as post-live.

```powershell
# R3 Attempt-4 disposition helper
function Start-Attempt4DispositionTranscript {
  if ($AttemptState.TranscriptStarted) { return }
  if (
    [string]::IsNullOrWhiteSpace($NonElevatedTranscript) -or
    -not [IO.Path]::IsPathRooted($NonElevatedTranscript)
  ) { throw 'Attempt-4 disposition transcript binding invalid.' }
  Start-Transcript -Path $NonElevatedTranscript -NoClobber
  $AttemptState.TranscriptStarted = $true
}

function Complete-Attempt4Disposition {
  param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
      'PRE-BEGIN HOLD',
      'ATTEMPT HOLD',
      'SIGNED-AUTHORITY HOLD',
      'POST-LIVE CLOSEOUT HOLD',
      'VERIFIED'
    )]
    [string]$Disposition
  )

  if ($AttemptState.DispositionWritten) { throw 'Attempt-4 disposition already written.' }
  if (
    $PhaseFlags.Count -ne 4 -or
    [string]::IsNullOrWhiteSpace($SourceCommit) -or
    $SourceCommit -cnotmatch '^[0-9a-f]{40}$'
  ) { throw 'Attempt-4 disposition evidence binding invalid.' }
  Start-Attempt4DispositionTranscript
  $AttemptDisposition = $Disposition
  $DispositionLine = [ordered]@{
    attempt = 4
    phase_flags = $PhaseFlags
    disposition = $AttemptDisposition
    source_head = $SourceCommit
  } | ConvertTo-Json -Compress -Depth 4
  Write-Output $DispositionLine
  $AttemptState.DispositionWritten = $true
  try {
    Stop-Transcript | Out-Null
  } finally {
    $AttemptState.TranscriptStarted = $false
  }
}

if (-not ('Project6ScienceBaseSpentMarkerProbe' -as [type])) {
  Add-Type @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Win32.SafeHandles;

public static class Project6ScienceBaseSpentMarkerProbe {
    private static readonly IntPtr InvalidHandle = new IntPtr(-1);
    private const uint ReadControl = 0x00020000;
    private const uint GenericRead = 0x80000000;
    private const uint FileReadAttributes = 0x00000080;
    private const uint ShareAll = 0x00000007;
    private const uint OpenExisting = 3;
    private const uint BackupSemantics = 0x02000000;
    private const uint OpenReparsePoint = 0x00200000;
    private const uint DirectoryAttribute = 0x00000010;
    private const uint ReparseAttribute = 0x00000400;
    private const uint InvalidAttributes = 0xffffffff;
    private const uint OwnerSecurityInformation = 0x1;
    private const uint DaclSecurityInformation = 0x4;
    private const ushort DaclProtected = 0x1000;
    private const uint FileAllAccess = 0x001F01FF;

    [StructLayout(LayoutKind.Sequential)]
    private struct ByHandleFileInformation {
        public uint Attributes;
        public System.Runtime.InteropServices.ComTypes.FILETIME CreationTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME AccessTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME WriteTime;
        public uint VolumeSerial;
        public uint SizeHigh;
        public uint SizeLow;
        public uint LinkCount;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct AclHeader {
        public byte Revision;
        public byte Sbz1;
        public ushort Size;
        public ushort AceCount;
        public ushort Sbz2;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct AceHeader {
        public byte Type;
        public byte Flags;
        public ushort Size;
    }

    private sealed class Identity {
        public uint Volume;
        public ulong FileId;
        public uint Links;
        public uint Attributes;
        public ulong Size;

        public bool Same(Identity other) {
            return other != null && Volume == other.Volume && FileId == other.FileId &&
                Links == other.Links && Attributes == other.Attributes && Size == other.Size;
        }
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateFileW(
        string path, uint access, uint share, IntPtr security, uint creation,
        uint flags, IntPtr template);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr handle);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandle(
        IntPtr handle, out ByHandleFileInformation information);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetFileAttributesW(string path);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint GetSecurityInfo(
        IntPtr handle, uint objectType, uint information, out IntPtr owner,
        IntPtr group, out IntPtr dacl, IntPtr sacl, out IntPtr descriptor);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetSecurityDescriptorControl(
        IntPtr descriptor, out ushort control, out uint revision);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetAce(IntPtr acl, uint index, out IntPtr ace);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool EqualSid(IntPtr left, IntPtr right);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertStringSidToSidW(string text, out IntPtr sid);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr value);

    private static Identity GetIdentity(IntPtr handle) {
        ByHandleFileInformation value;
        if (!GetFileInformationByHandle(handle, out value)) { throw new IOException(); }
        return new Identity {
            Volume = value.VolumeSerial,
            FileId = ((ulong)value.FileIndexHigh << 32) | value.FileIndexLow,
            Links = value.LinkCount,
            Attributes = value.Attributes,
            Size = ((ulong)value.SizeHigh << 32) | value.SizeLow
        };
    }

    private static bool IsDirectory(Identity value) {
        return (value.Attributes & DirectoryAttribute) != 0;
    }

    private static bool IsReparse(Identity value) {
        return (value.Attributes & ReparseAttribute) != 0;
    }

    private static bool IsSecure(IntPtr handle, string expectedOwnerSid) {
        IntPtr expectedOwner = IntPtr.Zero;
        IntPtr system = IntPtr.Zero;
        IntPtr owner = IntPtr.Zero;
        IntPtr dacl = IntPtr.Zero;
        IntPtr descriptor = IntPtr.Zero;
        try {
            if (!ConvertStringSidToSidW(expectedOwnerSid, out expectedOwner) ||
                !ConvertStringSidToSidW("S-1-5-18", out system)) { return false; }
            uint result = GetSecurityInfo(
                handle, 1, OwnerSecurityInformation | DaclSecurityInformation,
                out owner, IntPtr.Zero, out dacl, IntPtr.Zero, out descriptor);
            if (result != 0 || descriptor == IntPtr.Zero || dacl == IntPtr.Zero ||
                !EqualSid(owner, expectedOwner)) { return false; }
            ushort control;
            uint revision;
            if (!GetSecurityDescriptorControl(descriptor, out control, out revision) ||
                (control & DaclProtected) == 0) { return false; }
            AclHeader acl = (AclHeader)Marshal.PtrToStructure(dacl, typeof(AclHeader));
            if (acl.AceCount != 2) { return false; }
            bool sawOwner = false;
            bool sawSystem = false;
            for (uint index = 0; index < acl.AceCount; index++) {
                IntPtr ace;
                if (!GetAce(dacl, index, out ace)) { return false; }
                AceHeader header = (AceHeader)Marshal.PtrToStructure(ace, typeof(AceHeader));
                uint mask = unchecked((uint)Marshal.ReadInt32(ace, 4));
                IntPtr sid = IntPtr.Add(ace, 8);
                bool isOwner = EqualSid(sid, expectedOwner);
                bool isSystem = EqualSid(sid, system);
                if (header.Type != 0 || header.Flags != 0 || mask != FileAllAccess ||
                    (!isOwner && !isSystem)) { return false; }
                if (isOwner) {
                    if (sawOwner) { return false; }
                    sawOwner = true;
                }
                if (isSystem) {
                    if (sawSystem) { return false; }
                    sawSystem = true;
                }
            }
            return sawOwner && sawSystem;
        } finally {
            if (descriptor != IntPtr.Zero) { LocalFree(descriptor); }
            if (expectedOwner != IntPtr.Zero) { LocalFree(expectedOwner); }
            if (system != IntPtr.Zero) { LocalFree(system); }
        }
    }

    private static bool IsStableAbsent(string path) {
        uint first = GetFileAttributesW(path);
        int firstError = Marshal.GetLastWin32Error();
        uint second = GetFileAttributesW(path);
        int secondError = Marshal.GetLastWin32Error();
        return first == InvalidAttributes && second == InvalidAttributes &&
            (firstError == 2 || firstError == 3) && firstError == secondError;
    }

    private static IntPtr OpenNearestDirectory(string path, out string openedPath) {
        string candidate = Path.GetDirectoryName(path);
        while (!String.IsNullOrEmpty(candidate)) {
            IntPtr handle = CreateFileW(
                candidate, FileReadAttributes | ReadControl, ShareAll, IntPtr.Zero,
                OpenExisting, BackupSemantics | OpenReparsePoint, IntPtr.Zero);
            if (handle != InvalidHandle) {
                openedPath = candidate;
                return handle;
            }
            int error = Marshal.GetLastWin32Error();
            if (error != 2 && error != 3) { break; }
            string parent = Path.GetDirectoryName(candidate.TrimEnd('\\'));
            if (String.IsNullOrEmpty(parent) ||
                String.Equals(parent, candidate, StringComparison.OrdinalIgnoreCase)) { break; }
            candidate = parent;
        }
        openedPath = null;
        return InvalidHandle;
    }

    public static string Classify(
        string path, string expectedOwnerSid, string expectedLine) {
        IntPtr directory = InvalidHandle;
        IntPtr file = InvalidHandle;
        try {
            string full = Path.GetFullPath(path);
            string parent = Path.GetDirectoryName(full);
            string openedDirectory;
            directory = OpenNearestDirectory(full, out openedDirectory);
            if (directory == InvalidHandle) { return "AMBIGUOUS"; }
            Identity directoryIdentity = GetIdentity(directory);
            if (!IsDirectory(directoryIdentity) || IsReparse(directoryIdentity) ||
                new DriveInfo(Path.GetPathRoot(full)).DriveType != DriveType.Fixed) {
                return "AMBIGUOUS";
            }

            file = CreateFileW(
                full, GenericRead | ReadControl, 0, IntPtr.Zero, OpenExisting,
                OpenReparsePoint, IntPtr.Zero);
            if (file == InvalidHandle) {
                int error = Marshal.GetLastWin32Error();
                bool immediateParent = String.Equals(
                    openedDirectory, parent, StringComparison.OrdinalIgnoreCase);
                if ((error != 2 && error != 3) ||
                    (immediateParent && !IsSecure(directory, expectedOwnerSid)) ||
                    !IsStableAbsent(full) ||
                    (!immediateParent && !IsStableAbsent(parent)) ||
                    !GetIdentity(directory).Same(directoryIdentity) ||
                    (immediateParent && !IsSecure(directory, expectedOwnerSid))) {
                    return "AMBIGUOUS";
                }
                return "ABSENT";
            }

            if (!String.Equals(openedDirectory, parent, StringComparison.OrdinalIgnoreCase) ||
                !IsSecure(directory, expectedOwnerSid)) { return "AMBIGUOUS"; }
            Identity before = GetIdentity(file);
            if (IsDirectory(before) || IsReparse(before) || before.Links != 1 ||
                before.Volume != directoryIdentity.Volume ||
                !IsSecure(file, expectedOwnerSid)) { return "AMBIGUOUS"; }
            if (before.Size == 0 || before.Size > 65536) { return "AMBIGUOUS"; }
            byte[] bytes = new byte[(int)before.Size];
            using (SafeFileHandle safe = new SafeFileHandle(file, false))
            using (FileStream stream = new FileStream(safe, FileAccess.Read, 4096, false)) {
                int offset = 0;
                while (offset < bytes.Length) {
                    int read = stream.Read(bytes, offset, bytes.Length - offset);
                    if (read <= 0) { return "AMBIGUOUS"; }
                    offset += read;
                }
            }
            if (!GetIdentity(file).Same(before) || !IsSecure(file, expectedOwnerSid) ||
                !GetIdentity(directory).Same(directoryIdentity) ||
                !IsSecure(directory, expectedOwnerSid)) {
                return "AMBIGUOUS";
            }
            string text = new UTF8Encoding(false, true).GetString(bytes);
            if (!text.EndsWith("\n", StringComparison.Ordinal) || text.IndexOf('\r') >= 0) {
                return "AMBIGUOUS";
            }
            string[] lines = text.Substring(0, text.Length - 1).Split(new char[] {'\n'});
            const string pattern = "^\\{\"envelope_digest\":\"sha256:[0-9a-f]{64}\",\"go_id\":\"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\",\"schema\":\"project6\\.sciencebase_live_go_spent\\.v1\"\\}$";
            bool found = false;
            foreach (string line in lines) {
                if (!Regex.IsMatch(line, pattern, RegexOptions.CultureInvariant)) {
                    return "AMBIGUOUS";
                }
                found |= String.Equals(line, expectedLine, StringComparison.Ordinal);
            }
            return found ? "PRESENT" : "ABSENT";
        } catch {
            return "AMBIGUOUS";
        } finally {
            bool fileClosed = file == InvalidHandle || CloseHandle(file);
            bool directoryClosed = directory == InvalidHandle || CloseHandle(directory);
            if (!fileClosed || !directoryClosed) { throw new IOException(); }
        }
    }
}
'@
}

function Get-Attempt4DurableLiveDisposition {
  param(
    [Parameter(Mandatory = $true)][string]$MarkerGoId,
    [Parameter(Mandatory = $true)][string]$MarkerEnvelopeDigest,
    [Parameter(Mandatory = $true)][string]$SpentMarkerPath
  )

  try {
    if (
      $MarkerGoId -cnotmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' -or
      $MarkerEnvelopeDigest -cnotmatch '^sha256:[0-9a-f]{64}$'
    ) { return 'POST-LIVE CLOSEOUT HOLD' }
    $ExpectedMarkerLine = '{"envelope_digest":"' + $MarkerEnvelopeDigest +
      '","go_id":"' + $MarkerGoId +
      '","schema":"project6.sciencebase_live_go_spent.v1"}'
    $Probe = [Project6ScienceBaseSpentMarkerProbe]::Classify(
      [IO.Path]::GetFullPath($SpentMarkerPath),
      $ExpectedOwnerSid,
      $ExpectedMarkerLine
    )
    if ($Probe -ceq 'ABSENT') { return 'SIGNED-AUTHORITY HOLD' }
    return 'POST-LIVE CLOSEOUT HOLD'
  } catch {
    return 'POST-LIVE CLOSEOUT HOLD'
  }
}
```

### Elevated calls 2-3, atomic custody, and Phase 1

Run the following once in one fresh elevated Windows PowerShell 5.1 shell. First reload the two preservation definitions and the atomic-custody helper definition above; loading them performs no action. The `NonRuntime` guard encloses both Python gates, a fresh before/after preservation comparison, all three create-once custody operations, exact stage checks, both provisioners, both direct initializer calls, and the durable Phase-1 record. `ERROR_ALREADY_EXISTS`, any unexpected create result, or any inability to prove which call created a directory is HOLD; there is no create-then-harden or pre-existing-success path. A failure after any custody directory is created preserves every byte. Before `$P1_IexBegun` it is `PRE-BEGIN HOLD`; after the flag it is terminal ATTEMPT HOLD.

```powershell
$ErrorActionPreference = 'Stop'
$RepositoryRoot = (Get-Location).Path
$ExpectedBranch = 'codex/sb-live-impl'
$ExpectedSourceCommit = '<OWNER-FILL reviewed head>'
$ExpectedOwnerSid = '<OWNER-FILL frozen owner SID>'
$ExpectedAmbientInterpreter = '<OWNER-FILL frozen ambient interpreter>'
$PythonArchive = 'C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip'
$PythonGate = Join-Path $RepositoryRoot 'scripts\validate-dual-live-python-binding.ps1'
$FamilyGuard = Join-Path $RepositoryRoot 'scripts\invoke-dual-live-family-guard.ps1'
$InitializeTool = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot 'tools\dual_live_initialize.py'))
$Attempt = 4
$CampaignId = 'sciencebase-live-v2'
$CustodyParent = 'C:\owner-controlled\project6-attempt-4'
$CanonicalRoot = Join-Path $CustodyParent 'sciencebase-campaign'
$AuthorityEnvelope = Join-Path $CustodyParent 'sciencebase-authority.json'
$ElevatedTranscript = Join-Path $CustodyParent 'attempt4-elevated-transcript.txt'
$BindingParent = 'C:\owner-controlled\project6-bindings-4'
$WorkerProvisioningRoot = 'C:\p6-sciencebase-worker-4'
$ConnectorRunId = '<OWNER-FILL fresh UUID>'
$AuthorizationDigest = 'sha256:061102e5c209f4b426ac4c23d0a25514da9d29384e4e24c16306ef7ef587edb2' # B2 authorization label: UTF-8 sha256 of project6:sciencebase-live-v2:B2:authorization-non-authorizing
$GrantDigest = 'sha256:199263280d7c0ea3a880091ebc6d0654d6abca72674bf800c94c11b3580d1ba5' # B2 grant label: UTF-8 sha256 of project6:sciencebase-live-v2:B2:grant-non-authorizing
if (
  $ExpectedSourceCommit -like '<OWNER-FILL*' -or
  $ExpectedOwnerSid -like '<OWNER-FILL*' -or
  $ExpectedAmbientInterpreter -like '<OWNER-FILL*' -or
  $ConnectorRunId -like '<OWNER-FILL*'
) { throw 'PRE-SITTING HOLD: elevated owner-filled inputs are incomplete.' }

$ElevatedState = [pscustomobject]@{ CustodyBegun = $false; Phase1Begun = $false }
try {
& $FamilyGuard -Mode NonRuntime -Action {
  if ($null -eq $NewPreservationBaseline -or $null -eq $AssertPreservationUnchanged) {
    throw 'PRE-SITTING HOLD: preservation actions are not loaded.'
  }
  $PreservationContext = & $NewPreservationBaseline -AmbientInterpreter $ExpectedAmbientInterpreter
  $CurrentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  if ([string]::IsNullOrWhiteSpace($CurrentSid) -or $CurrentSid -cne $ExpectedOwnerSid) {
    throw 'PRE-SITTING HOLD: sciencebase_owner_identity_mismatch'
  }

  # Python binding gate call 2 of 6.
  $PythonBinding = & $PythonGate -PythonArchive $PythonArchive
  if ($LASTEXITCODE -ne 0 -or $null -eq $PythonBinding -or $PythonBinding.status -cne 'PYTHON_BINDING_OK') {
    throw 'PRE-SITTING HOLD: binding gate 2 failed.'
  }
  $Py = [string]$PythonBinding.ambient_interpreter
  if ([IO.Path]::GetFullPath($Py) -cne [IO.Path]::GetFullPath($ExpectedAmbientInterpreter)) {
    throw 'PRE-SITTING HOLD: gate-bound ambient interpreter path drift.'
  }

  $ObservedBranch = (& git branch --show-current).Trim()
  $BranchExit = $LASTEXITCODE
  $SourceStatus = @(& git status --porcelain=v1 --untracked-files=all)
  $StatusExit = $LASTEXITCODE
  $SourceCommit = (& git rev-parse HEAD).Trim()
  $CommitExit = $LASTEXITCODE
  if (
    $BranchExit -ne 0 -or $StatusExit -ne 0 -or $CommitExit -ne 0 -or
    $ObservedBranch -cne $ExpectedBranch -or $SourceStatus.Count -ne 0 -or
    $SourceCommit -cne $ExpectedSourceCommit
  ) { throw 'PRE-SITTING HOLD: source checkout is not the exact clean reviewed subject.' }
  if (
    -not (Test-Path -LiteralPath $InitializeTool -PathType Leaf) -or
    ((Get-Item -Force -LiteralPath $InitializeTool).Attributes -band [IO.FileAttributes]::ReparsePoint)
  ) { throw 'PRE-SITTING HOLD: initializer tool path invalid.' }
  & $AssertPreservationUnchanged $PreservationContext

  $ParentSddl = "O:$ExpectedOwnerSid" + "D:P(A;OICI;FA;;;$ExpectedOwnerSid)(A;OICI;FA;;;SY)"
  $CampaignSddl = "O:$ExpectedOwnerSid" + "D:P(A;;FA;;;$ExpectedOwnerSid)(A;;FA;;;SY)"
  New-CustodyDirectoryOnce -Path $CustodyParent -Sddl $ParentSddl
  $ElevatedState.CustodyBegun = $true
  New-CustodyDirectoryOnce -Path $CanonicalRoot -Sddl $CampaignSddl
  New-CustodyDirectoryOnce -Path $BindingParent -Sddl $ParentSddl
  Assert-CustodyDirectory -Path $CustodyParent -Inheritable $true
  Assert-CustodyDirectory -Path $CanonicalRoot -Inheritable $false
  Assert-CustodyDirectory -Path $BindingParent -Inheritable $true
  Assert-ExactChildSet -Path $CustodyParent -Expected @('sciencebase-campaign')
  Assert-ExactChildSet -Path $CanonicalRoot -Expected @()
  Assert-ExactChildSet -Path $BindingParent -Expected @()

  Start-Transcript -Path $ElevatedTranscript -NoClobber
  try {
    Assert-ExactChildSet -Path $CustodyParent -Expected @('sciencebase-campaign', 'attempt4-elevated-transcript.txt')

    # Python binding gate call 3 of 6.
    $PythonBinding = & $PythonGate -PythonArchive $PythonArchive
    if ($LASTEXITCODE -ne 0 -or $null -eq $PythonBinding -or $PythonBinding.status -cne 'PYTHON_BINDING_OK') {
      throw 'PRE-BEGIN HOLD: binding gate 3 failed.'
    }
    $Py = [string]$PythonBinding.ambient_interpreter
    $CurrentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ($CurrentSid -cne $ExpectedOwnerSid) { throw 'PRE-BEGIN HOLD: owner SID parity drift.' }
    Assert-CustodyDirectory -Path $CustodyParent -Inheritable $true
    Assert-CustodyDirectory -Path $CanonicalRoot -Inheritable $false
    Assert-CustodyDirectory -Path $BindingParent -Inheritable $true

    $P1_IexBegun = $true
    $ElevatedState.Phase1Begun = $true
    $AttemptNonce = [guid]::NewGuid().ToString('N')
    $ProfileLeaf = "sciencebase-profile-$AttemptNonce.json"
    $WorkerLeaf = "sciencebase-worker-$AttemptNonce.json"
    $ProfileBinding = Join-Path $BindingParent $ProfileLeaf
    $WorkerBinding = Join-Path $BindingParent $WorkerLeaf
    $ProfileMoniker = 'Project6.ScienceBase.LiveV2.' + $AttemptNonce.Substring(0,8)
    $AmbientInterpreterRoot = [string]$PythonBinding.ambient_interpreter_root
    $AmbientInterpreterSha256 = (Get-FileHash -LiteralPath $Py -Algorithm SHA256).Hash.ToLowerInvariant()

    .\scripts\provision-dual-live-profile.ps1 -ProfileMoniker $ProfileMoniker -OutputBinding $ProfileBinding
    Assert-ExactChildSet -Path $BindingParent -Expected @($ProfileLeaf)
    .\scripts\provision-dual-live-worker.ps1 -PythonArchive $PythonArchive -ProfileBinding $ProfileBinding -ProvisioningRoot $WorkerProvisioningRoot -OutputBinding $WorkerBinding -CampaignRoot $CanonicalRoot -AmbientInterpreterRoot $AmbientInterpreterRoot -RepositoryRoot $RepositoryRoot
    Assert-ExactChildSet -Path $BindingParent -Expected @($ProfileLeaf, $WorkerLeaf)

    $Profile = Get-Content -Raw -LiteralPath $ProfileBinding | ConvertFrom-Json
    $Worker = Get-Content -Raw -LiteralPath $WorkerBinding | ConvertFrom-Json
    $WorkerBundleRoot = [string]$Worker.root
    $WorkerProfileMoniker = [string]$Worker.profile_moniker
    if ($WorkerProfileMoniker -cne $ProfileMoniker) { throw 'terminal ATTEMPT HOLD: worker/profile moniker drift.' }
    if (
      [string]$Profile.broker_sid -cne $CurrentSid -or
      [string]$Worker.broker_sid -cne $CurrentSid -or
      $CurrentSid -cne $ExpectedOwnerSid
    ) { throw 'terminal ATTEMPT HOLD: owner/current/profile/worker broker SID mismatch.' }

    $ExpectedWorkerAcl = @{
      'S-1-5-18' = 0x001F01FF
      'S-1-5-32-544' = 0x001F01FF
      ([string]$Worker.owner_sid) = 0x001F01FF
      ([string]$Worker.provisioner_sid) = 0x001F01FF
      $CurrentSid = 0x001200A9
      ([string]$Worker.package_sid) = 0x001200A9
    }
    if ($ExpectedWorkerAcl.Count -ne 6) { throw 'terminal ATTEMPT HOLD: worker ACL principals ambiguous.' }
    $WorkerAcl = Get-Acl -LiteralPath $WorkerBundleRoot
    $ObservedWorkerAces = @($WorkerAcl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))
    $SeenWorkerSids = @{}
    if (
      -not $WorkerAcl.AreAccessRulesProtected -or
      @($WorkerAcl.GetAccessRules($false, $true, [Security.Principal.SecurityIdentifier])).Count -ne 0 -or
      $ObservedWorkerAces.Count -ne 6
    ) { throw 'terminal ATTEMPT HOLD: worker DACL is not exact-six-ACE protected.' }
    foreach ($Ace in $ObservedWorkerAces) {
      $Sid = $Ace.IdentityReference.Value
      if (
        -not $ExpectedWorkerAcl.ContainsKey($Sid) -or $SeenWorkerSids.ContainsKey($Sid) -or
        $Ace.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
        [int]$Ace.FileSystemRights -ne $ExpectedWorkerAcl[$Sid] -or $Ace.IsInherited -or
        $Ace.InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::None -or
        $Ace.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None
      ) { throw 'terminal ATTEMPT HOLD: worker DACL tuple drift.' }
      $SeenWorkerSids[$Sid] = $true
    }
    if ($SeenWorkerSids.Count -ne 6) { throw 'terminal ATTEMPT HOLD: worker DACL principal set incomplete.' }

    $WorkerProvisioningRoot = [string]$Worker.provisioning_root
    $WorkerManifestDigest = [string]$Worker.manifest_digest
    $WorkerInterpreter = Join-Path $WorkerBundleRoot ([string]$Worker.interpreter)
    $WorkerEntrypoint = [string]$Worker.entrypoint
    $WorkerPythonVersion = [string]$Worker.python_version
    $WorkerArchitecture = [string]$Worker.architecture
    $WorkerPackageSid = [string]$Worker.package_sid
    $WorkerOwnerSid = [string]$Worker.owner_sid
    $WorkerProvisionerSid = [string]$Worker.provisioner_sid
    $WorkerBrokerSid = [string]$Worker.broker_sid
    $BoundAmbientInterpreterRoot = [string]$Worker.ambient_interpreter_root
    $CampaignRoot = [string]$Worker.campaign_root
    $AppContainerProfileRoot = [string]$Worker.appcontainer_profile_root
    $BrokerProfileRoot = [string]$Worker.broker_profile_root
    $UserDataRoot = [string]$Worker.user_data_root
    $WorkerInterpreterSha256 = (Get-FileHash -LiteralPath $WorkerInterpreter -Algorithm SHA256).Hash.ToLowerInvariant()
    if (
      [IO.Path]::GetFullPath($BoundAmbientInterpreterRoot) -cne [IO.Path]::GetFullPath($AmbientInterpreterRoot) -or
      $AmbientInterpreterSha256 -cne $WorkerInterpreterSha256
    ) { throw 'terminal ATTEMPT HOLD: ambient and worker interpreter bytes differ.' }
    $InterpreterIdentity = 'sha256:' + $WorkerInterpreterSha256

    $ReservationInitializerArgs = @(
      'reservation-store', '--canonical-root', $CanonicalRoot,
      '--connector-run-id', $ConnectorRunId
    )
    $PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
    $OriginalLocation = (Get-Location).Path
    try {
      Set-Location -LiteralPath $RepositoryRoot
      # Governed Python tool call 1 of 5: reservation initializer.
      & $Py $InitializeTool @ReservationInitializerArgs
      $ReservationExit = $LASTEXITCODE
      if ($ReservationExit -ne 0) { throw 'terminal ATTEMPT HOLD: reservation initializer failed.' }
    } finally {
      $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
      Set-Location -LiteralPath $OriginalLocation
    }
    Assert-ExactChildSet -Path $CanonicalRoot -Expected @('reservation.db')

    $AuthorityInitializerArgs = @(
      'authority-envelope', '--output', $AuthorityEnvelope,
      '--campaign-id', $CampaignId, '--canonical-root', $CanonicalRoot,
      '--connector-run-id', $ConnectorRunId, '--source-commit', $SourceCommit,
      '--interpreter-identity', $InterpreterIdentity,
      '--authorization-digest', $AuthorizationDigest, '--grant-digest', $GrantDigest
    )
    $PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
    $OriginalLocation = (Get-Location).Path
    try {
      Set-Location -LiteralPath $RepositoryRoot
      # Governed Python tool call 2 of 5: authority initializer.
      & $Py $InitializeTool @AuthorityInitializerArgs
      $AuthorityExit = $LASTEXITCODE
      if ($AuthorityExit -ne 0) { throw 'terminal ATTEMPT HOLD: authority initializer failed.' }
    } finally {
      $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
      Set-Location -LiteralPath $OriginalLocation
    }
    $AuthorityEnvelopeDigest = 'sha256:' + (Get-FileHash -LiteralPath $AuthorityEnvelope -Algorithm SHA256).Hash.ToLowerInvariant()
    Assert-ExactChildSet -Path $CustodyParent -Expected @(
      'sciencebase-campaign', 'attempt4-elevated-transcript.txt', 'sciencebase-authority.json'
    )

    $Phase1Record = [ordered]@{
      SourceCommit = $SourceCommit
      ExpectedOwnerSid = $ExpectedOwnerSid
      ConnectorRunId = $ConnectorRunId
      AttemptNonce = $AttemptNonce
      ProfileMoniker = $ProfileMoniker
      ProfileBinding = $ProfileBinding
      WorkerBinding = $WorkerBinding
      WorkerBundleRoot = $WorkerBundleRoot
      WorkerProvisioningRoot = $WorkerProvisioningRoot
      AuthorityEnvelope = $AuthorityEnvelope
      AuthorityEnvelopeDigest = $AuthorityEnvelopeDigest
      InterpreterIdentity = $InterpreterIdentity
      AmbientInterpreterRoot = $AmbientInterpreterRoot
      AuthorizationDigest = $AuthorizationDigest
      GrantDigest = $GrantDigest
    }
    "PHASE1_RECORD=" + ($Phase1Record | ConvertTo-Json -Compress -Depth 4)
  } finally {
    Stop-Transcript
  }
}
} catch {
  if ($ElevatedState.CustodyBegun) {
    $EarlyDisposition = if ($ElevatedState.Phase1Begun) {
      'ATTEMPT HOLD'
    } else {
      'PRE-BEGIN HOLD'
    }
    $Attempt4TerminalHandoff = [ordered]@{
      source_head = $ExpectedSourceCommit
      disposition = $EarlyDisposition
    }
    "ATTEMPT4_TERMINAL_HANDOFF=" +
      ($Attempt4TerminalHandoff | ConvertTo-Json -Compress)
  }
  throw
}
```

If the elevated block emits `ATTEMPT4_TERMINAL_HANDOFF`, custody began and the attempt is terminal even if the guard later reported release failure. Preserve every byte, close the elevated shell, and in one fresh non-elevated shell at the same reviewed head load only the disposition-helper definitions above and run this disposition-only terminal step. It performs no recovery, cleanup, validation rerun, or close attempt; it records the already-determined early outcome. The four phase flags are false because Phase 1b never began.

```powershell
$SourceCommit = '<ATTEMPT4_TERMINAL_HANDOFF source_head>'
$EarlyDisposition = '<ATTEMPT4_TERMINAL_HANDOFF disposition>'
$NonElevatedTranscript = 'C:\owner-controlled\project6-attempt-4\attempt4-nonelevated-transcript.txt'
$PhaseFlags = [ordered]@{
  phase1_rehydrated = $false
  template_created = $false
  signed_live_returned = $false
  closeout_verified = $false
}
$AttemptState = [pscustomobject]@{
  DispositionWritten = $false
  TranscriptStarted = $false
}
if (
  $SourceCommit -like '<ATTEMPT4_TERMINAL_HANDOFF*' -or
  $EarlyDisposition -like '<ATTEMPT4_TERMINAL_HANDOFF*'
) { throw 'Attempt-4 terminal handoff is incomplete.' }
Complete-Attempt4Disposition $EarlyDisposition
```

The target values above are the complete bounded Attempt-4 acquisition subject; changing any of them requires a fresh owner decision, not reuse. `CampaignRoot` is exactly the selected table-derived campaign/evidence child, never the executable source checkout. The later ceremony uses a dedicated, quiesced checkout at the final reviewed commit, separate from `sb-impl`.

The profile binding must be produced from the actually provisioned broker/AppContainer profile and contains exactly `profile_moniker`, `package_sid`, `broker_sid`, `appcontainer_profile_root`, `broker_profile_root`, and `user_data_root`. The direct authority initializer emits canonical JSON with exactly `schema_version`, `campaign_id`, `canonical_root`, `connector_run_id`, `source_commit`, `interpreter_identity`, `authorization_digest`, `grant_digest`, and `wrapper_start_token_ref`. Its schema is `project6.connector_authority.v1`, and its mandatory non-caller-configurable sentinel is `wrapper_start_token_ref=retired:sciencebase-live-v2`. The two opaque authority/grant references do not themselves grant live authority. B0 does not create or issue either input, and neither substitutes for the later signed one-use owner GO. The `authorization_digest:B2` and `grant_digest:B2` labels are KNOWINGLY-RATIFIED non-authorizing attestations that bind nothing. `wrapper_start_token_ref` remains untouched.

Creation is atomic and create-once, not a repeatable success: all three paths must be absent, each `CreateDirectoryW` call must return true with its final `SECURITY_ATTRIBUTES` descriptor already applied, and every path is reread immediately. A pre-existing path is HOLD even if its final ACL appears correct. The initial exact child sets are parent=`sciencebase-campaign`, campaign=empty, binding=empty; later checks admit only the named transcript/authority sidecars, `reservation.db`, and the exact nonce-bound profile/worker leaves at their stated stages. Unknown, case-colliding, missing, staging, journal, `-wal`, or `-shm` children are terminal ATTEMPT HOLD and are preserved rather than removed.

Reservation and authority initializers do not touch `C:\ProgramData\Project6\Authority`. `OneUseLiveGoConsumer` first reaches it during GO consumption through `SpentMarkerStore`, whose Windows backend securely creates missing managed directories. This R3 leaves `SpentMarkerStore.claim_exact` byte-for-byte unchanged: it adds no parameter, expectation object, PRESENT branch, or new behavior; Attempt 4 retains the existing ABSENT/secure-create-new behavior.

### SQLite journal observer: DESIGN REOPENED

The initializer's reviewed opt-in seam is `journal_observer: Callable[[Path, Path], None] | None = None`. When supplied, it is invoked exactly once after the connector_run INSERT and before COMMIT, while the real DELETE-mode transaction remains open, as `journal_observer(staging_database_path, staging_database_path.with_name(staging_database_path.name + "-journal"))`. The rehearsal passes `journal_observer=assert_frozen_journal_posture`. Hook exceptions propagate through the existing unwind and custody cleanup; a cleanup ambiguity remains `custody_cleanup_indeterminate`. Omitting the hook preserves byte-equivalent initializer behavior. This is observer-only: there is no PRESENT branch, no GO-consumption change, and no change to `SpentMarkerStore.claim_exact`.

The exact-host Python 3.12.10/SQLite observation found an ordinary, non-reparse, single-link file in the same directory and fixed-local volume as the staging database, with the current owner SID. It also found `protected=false` and an extra current-logon SID RX ACE whose SID is session-specific. The observed native secure tuple was `(True, False, False)`. Therefore the observed journal does not match the required protected owner-and-SYSTEM-only staging posture when its owner SID, DACL protection, ordered SDDL, and sorted ACE tuples are compared. Final disappearance does not cure that transient exposure. The frozen-safe-posture assertion remains RED, the design is reopened, and Attempt 4 remains HOLD until a separately reviewed strategy closes this condition. No custody, template, signature, live invocation, or closeout below is presently authorized by this prospective runbook.

The observer above characterizes only initializer staging. `ReservationStore.reserve` and `write_sciencebase_live_event` also open `reservation.db-journal` during live reservation and terminal-event transactions. The complete runtime journal lifecycle remains uncharacterized; an owner-gated R4 must cover those real runtime transactions as well as initialization. The candidate ObjectInherit-only campaign descriptor, parent-correlated transient oracle, and elevated token `.User` plus `.Owner` proof remain unapproved R4 design inputs, not changes made by this R3. Passing the initializer observer alone cannot close the strategy or authorize C5/Attempt 4.

The worker provisioner invokes `git cat-file blob` once for each of the 8 worker files and explicitly treats any stderr as `worker_source_copy_failed`, even when Git exits 0. Whether `2>$null` can itself raise a terminating `NativeCommandError` on Windows PowerShell 5.1 under the script's `$ErrorActionPreference = 'Stop'` is not asserted; verify locally before the sitting. A stderr-silent `git` on PATH is a hard prerequisite either way. CI corroborates topology and ACL sequencing only; it is not owner-host broker-identity or interpreter evidence.

The still-HIGH DACL residual is accepted only for this public credential-free run and is not transferable to NRC or another credentialed tranche. The owner accepts the structural-burn risk only with same-sitting W5 and T1.6 pre-7 interruption invalidation; neither R19 nor the separately required characterization is waived.

### Non-elevated Phase-1 rehydration and template emission

Exit the elevated shell after recording the Phase-1 values above. In a fresh non-elevated Windows PowerShell 5.1 shell at the same exact reviewed checkout, first load the read-only assertion functions from the atomic-custody helper, the Attempt-4 disposition/durable-live helpers, and the `Invoke-W5Observation` definition above; none performs an action when loaded. Assign every `<PHASE-1-RECORD ...>` value below from the closed elevated transcript and the two durable binding records. Do not regenerate a nonce, rerun a provisioner, rerun an initializer, or carry an in-memory array across the elevation boundary. The call-4 `NonRuntime` lease stays held across gate 4, rehydration, the two exact pytest checks, W5, and unsigned-template emission. The fixed B2 values are the reviewed UTF-8 SHA-256 digests of the named non-authorizing labels; they bind nothing and grant nothing.

```powershell
$RepositoryRoot = (Get-Location).Path
$ExpectedBranch = 'codex/sb-live-impl'
$ExpectedSourceCommit = '<PHASE-1-RECORD source commit>'
$SourceCommit = $ExpectedSourceCommit
$ExpectedOwnerSid = '<PHASE-1-RECORD frozen owner SID>'
$PythonArchive = 'C:\owner-controlled\project6\python-3.12.10-embed-amd64.zip'
$PythonGate = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot 'scripts\validate-dual-live-python-binding.ps1'))
$FamilyGuard = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot 'scripts\invoke-dual-live-family-guard.ps1'))
$RunTool = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot 'tools\dual_live_run.py'))
$CustodyParent = 'C:\owner-controlled\project6-attempt-4'
$CanonicalRoot = Join-Path $CustodyParent 'sciencebase-campaign'
$NonElevatedTranscript = Join-Path $CustodyParent 'attempt4-nonelevated-transcript.txt'
$Go = Join-Path $CustodyParent 'owner-go.json'
$GoId = '<OWNER-FILL fresh UUID>'
if (
  $ExpectedOwnerSid -like '<PHASE-1-RECORD*' -or
  $GoId -like '<OWNER-FILL*' -or
  -not (Test-Path -LiteralPath $PythonGate -PathType Leaf) -or
  -not (Test-Path -LiteralPath $FamilyGuard -PathType Leaf) -or
  -not (Test-Path -LiteralPath $RunTool -PathType Leaf)
) { throw 'terminal ATTEMPT HOLD: Phase-1b inputs or tools are incomplete.' }

$PhaseFlags = [ordered]@{
  phase1_rehydrated = $false
  template_created = $false
  signed_live_returned = $false
  closeout_verified = $false
}
$AttemptState = [pscustomobject]@{
  DispositionWritten = $false
  TranscriptStarted = $false
}

$Phase1bGuardReturned = $false
try {
$Phase1bOutput = @(& $FamilyGuard -Mode NonRuntime -Action {
  Start-Attempt4DispositionTranscript
    $CurrentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ([string]::IsNullOrWhiteSpace($CurrentSid) -or $CurrentSid -cne $ExpectedOwnerSid) {
      throw 'terminal ATTEMPT HOLD: sciencebase_owner_identity_mismatch'
    }

    # Python binding gate call 4 of 6.
    $PythonBinding = & $PythonGate -PythonArchive $PythonArchive
    if ($LASTEXITCODE -ne 0 -or $null -eq $PythonBinding -or $PythonBinding.status -cne 'PYTHON_BINDING_OK') {
      throw 'terminal ATTEMPT HOLD: binding gate 4 failed.'
    }
    $Py = [string]$PythonBinding.ambient_interpreter

$ObservedBranch = (& git branch --show-current).Trim()
$BranchExit = $LASTEXITCODE
$SourceStatus = @(& git status --porcelain=v1 --untracked-files=all)
$StatusExit = $LASTEXITCODE
$SourceCommit = (& git rev-parse HEAD).Trim()
$CommitExit = $LASTEXITCODE
if (
  $BranchExit -ne 0 -or $StatusExit -ne 0 -or $CommitExit -ne 0 -or
  $ExpectedSourceCommit -like '<PHASE-1-RECORD*' -or
  $ObservedBranch -cne $ExpectedBranch -or
  $SourceStatus.Count -ne 0 -or
  $SourceCommit -cne $ExpectedSourceCommit
) { throw 'terminal ATTEMPT HOLD: non-elevated checkout is not the exact Phase-1 reviewed subject.' }
$CampaignId = 'sciencebase-live-v2'
$ConnectorRunId = '<PHASE-1-RECORD connector run UUID>'
$AttemptNonce = '<PHASE-1-RECORD attempt nonce>'
$ProfileMoniker = '<PHASE-1-RECORD profile moniker>'
$ProfileBinding = '<PHASE-1-RECORD profile binding path>'
$WorkerBinding = '<PHASE-1-RECORD worker binding path>'
$WorkerBundleRoot = '<PHASE-1-RECORD worker bundle root>'
$WorkerProvisioningRoot = '<PHASE-1-RECORD worker provisioning root>'
$AuthorityEnvelope = '<PHASE-1-RECORD authority envelope path>'
$AuthorityEnvelopeDigest = '<PHASE-1-RECORD authority envelope digest>'
$InterpreterIdentity = '<PHASE-1-RECORD interpreter identity>'
$AmbientInterpreterRoot = '<PHASE-1-RECORD ambient interpreter root>'
$AuthorizationDigest = 'sha256:061102e5c209f4b426ac4c23d0a25514da9d29384e4e24c16306ef7ef587edb2' # B2 authorization label: UTF-8 sha256 of project6:sciencebase-live-v2:B2:authorization-non-authorizing
$GrantDigest = 'sha256:199263280d7c0ea3a880091ebc6d0654d6abca72674bf800c94c11b3580d1ba5' # B2 grant label: UTF-8 sha256 of project6:sciencebase-live-v2:B2:grant-non-authorizing
$Query = 'Mineral Commodity Summaries 2023 GERMANIUM'
$ExpectedItemId = '63d1a3c6d34e06fef15006be'
$ExpectedFileName = 'mcs2023-germa_salient.csv'
$RequiredPhase1Values = @(
  $ConnectorRunId, $AttemptNonce, $ProfileMoniker, $ProfileBinding, $WorkerBinding,
  $WorkerBundleRoot, $WorkerProvisioningRoot, $AuthorityEnvelope,
  $AuthorityEnvelopeDigest, $InterpreterIdentity, $AmbientInterpreterRoot
)
if ($RequiredPhase1Values.Where({
  [string]::IsNullOrWhiteSpace($_) -or $_ -like '<PHASE-1-RECORD*'
}).Count -ne 0) { throw 'Non-elevated Phase-1 rehydration is incomplete.' }
if (
  (Split-Path -Leaf $ProfileBinding) -cne "sciencebase-profile-$AttemptNonce.json" -or
  (Split-Path -Leaf $WorkerBinding) -cne "sciencebase-worker-$AttemptNonce.json"
) { throw 'Recorded binding path/nonce mismatch.' }
$Profile = Get-Content -Raw -LiteralPath $ProfileBinding | ConvertFrom-Json
$Worker = Get-Content -Raw -LiteralPath $WorkerBinding | ConvertFrom-Json
$WorkerProfileMoniker = $Worker.profile_moniker
if (
  [string]$Profile.profile_moniker -cne $ProfileMoniker -or
  $WorkerProfileMoniker -ne $ProfileMoniker -or
  [IO.Path]::GetFullPath([string]$Worker.root) -cne [IO.Path]::GetFullPath($WorkerBundleRoot) -or
  [IO.Path]::GetFullPath([string]$Worker.provisioning_root) -cne [IO.Path]::GetFullPath($WorkerProvisioningRoot)
) { throw 'Recorded worker/profile binding drift.' }
$WorkerManifestDigest = $Worker.manifest_digest
$WorkerInterpreter = Join-Path $WorkerBundleRoot $Worker.interpreter
$WorkerEntrypoint = $Worker.entrypoint
$WorkerPythonVersion = $Worker.python_version
$WorkerArchitecture = $Worker.architecture
$WorkerPackageSid = $Worker.package_sid
$WorkerOwnerSid = $Worker.owner_sid
$WorkerProvisionerSid = $Worker.provisioner_sid
$WorkerBrokerSid = $Worker.broker_sid
$BoundAmbientInterpreterRoot = $Worker.ambient_interpreter_root
$CampaignRoot = $Worker.campaign_root
$AppContainerProfileRoot = $Worker.appcontainer_profile_root
$BrokerProfileRoot = $Worker.broker_profile_root
$UserDataRoot = $Worker.user_data_root
$ObservedInterpreterIdentity = 'sha256:' + (Get-FileHash -LiteralPath $WorkerInterpreter -Algorithm SHA256).Hash.ToLowerInvariant()
$AmbientInterpreterSha256 = (Get-FileHash -LiteralPath $Py -Algorithm SHA256).Hash.ToLowerInvariant()
$ObservedAuthorityEnvelopeDigest = 'sha256:' + (Get-FileHash -LiteralPath $AuthorityEnvelope -Algorithm SHA256).Hash.ToLowerInvariant()
if (
  [string]$Profile.broker_sid -cne $CurrentSid -or
  [string]$Worker.broker_sid -cne $CurrentSid -or
  $CurrentSid -cne $ExpectedOwnerSid -or
  [IO.Path]::GetFullPath($BoundAmbientInterpreterRoot) -cne [IO.Path]::GetFullPath($AmbientInterpreterRoot) -or
  [IO.Path]::GetFullPath($CampaignRoot) -cne [IO.Path]::GetFullPath($CanonicalRoot) -or
  $ObservedInterpreterIdentity -cne $InterpreterIdentity -or
  $AmbientInterpreterSha256 -cne $ObservedInterpreterIdentity.Substring('sha256:'.Length) -or
  $ObservedAuthorityEnvelopeDigest -cne $AuthorityEnvelopeDigest
) { throw 'terminal ATTEMPT HOLD: recorded Phase-1 identity or broker drift.' }

$ExpectedWorkerAcl = @{
  'S-1-5-18' = 0x001F01FF
  'S-1-5-32-544' = 0x001F01FF
  ([string]$Worker.owner_sid) = 0x001F01FF
  ([string]$Worker.provisioner_sid) = 0x001F01FF
  $CurrentSid = 0x001200A9
  ([string]$Worker.package_sid) = 0x001200A9
}
$WorkerAcl = [IO.Directory]::GetAccessControl([string]$Worker.root)
$ObservedWorkerAces = @($WorkerAcl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))
$SeenWorkerSids = @{}
if (
  $ExpectedWorkerAcl.Count -ne 6 -or
  -not $WorkerAcl.AreAccessRulesProtected -or
  @($WorkerAcl.GetAccessRules($false, $true, [Security.Principal.SecurityIdentifier])).Count -ne 0 -or
  $ObservedWorkerAces.Count -ne 6
) { throw 'terminal ATTEMPT HOLD: Phase-1b worker DACL is not exact-six-ACE protected.' }
foreach ($Ace in $ObservedWorkerAces) {
  $Sid = $Ace.IdentityReference.Value
  if (
    -not $ExpectedWorkerAcl.ContainsKey($Sid) -or $SeenWorkerSids.ContainsKey($Sid) -or
    $Ace.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
    [int]$Ace.FileSystemRights -ne $ExpectedWorkerAcl[$Sid] -or $Ace.IsInherited -or
    $Ace.InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::None -or
    $Ace.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None
  ) { throw 'terminal ATTEMPT HOLD: Phase-1b worker DACL tuple drift.' }
  $SeenWorkerSids[$Sid] = $true
}
if ($SeenWorkerSids.Count -ne 6) { throw 'terminal ATTEMPT HOLD: Phase-1b worker DACL principal set incomplete.' }
$PhaseFlags.phase1_rehydrated = $true
$PreparedRuntimeArgs = @(
  '--authority-envelope', $AuthorityEnvelope,
  '--authority-envelope-sha256', $AuthorityEnvelopeDigest,
  '--campaign-id', $CampaignId,
  '--canonical-root', $CanonicalRoot,
  '--connector-run-id', $ConnectorRunId,
  '--reservation-database', (Join-Path $CanonicalRoot 'reservation.db'),
  '--query', $Query,
  '--expected-item-id', $ExpectedItemId,
  '--expected-file-name', $ExpectedFileName,
  '--worker-bundle-root', $WorkerBundleRoot,
  '--worker-provisioning-root', $WorkerProvisioningRoot,
  '--worker-profile-moniker', $WorkerProfileMoniker,
  '--worker-manifest-sha256', $WorkerManifestDigest,
  '--worker-entrypoint', $WorkerEntrypoint,
  '--worker-interpreter', $WorkerInterpreter,
  '--worker-python-version', $WorkerPythonVersion,
  '--worker-architecture', $WorkerArchitecture,
  '--worker-package-sid', $WorkerPackageSid,
  '--worker-owner-sid', $WorkerOwnerSid,
  '--worker-provisioner-sid', $WorkerProvisionerSid,
  '--worker-broker-sid', $WorkerBrokerSid,
  '--ambient-interpreter-root', $AmbientInterpreterRoot,
  '--campaign-root', $CampaignRoot,
  '--appcontainer-profile-root', $AppContainerProfileRoot,
  '--broker-profile-root', $BrokerProfileRoot,
  '--user-data-root', $UserDataRoot
)
$PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
$PriorBytecode = $env:PYTHONDONTWRITEBYTECODE
$PriorPytestAddopts = $env:PYTEST_ADDOPTS
$PriorBundleBinding = $env:PROJECT6_B0_BUNDLE_BINDING
$OriginalLocation = (Get-Location).Path
try {
  $env:DUAL_LIVE_RUNTIME_ENABLED = 'true'
  $env:PYTHONDONTWRITEBYTECODE = '1'
  $env:PYTEST_ADDOPTS = '-p no:cacheprovider'
  $env:PROJECT6_B0_BUNDLE_BINDING = $WorkerBinding
  Set-Location -LiteralPath $RepositoryRoot

  & $Py -m pytest .\tests\test_dual_live_worker_bundle.py::test_windows_probe_validates_preprovisioned_fixture -q
  $FixtureExit = $LASTEXITCODE
  if ($FixtureExit -ne 0) { throw 'terminal ATTEMPT HOLD: worker-bundle fixture validation failed.' }

  & $Py -m pytest .\tests\test_sciencebase_no_signature_rehearsal.py -q -s
  $RehearsalExit = $LASTEXITCODE
  if ($RehearsalExit -ne 0) { throw 'terminal ATTEMPT HOLD: no-signature rehearsal failed.' }

  $W5Observation = Invoke-W5Observation -Py $Py
  if ($null -eq $W5Observation -or -not $W5Observation.Valid) {
    throw 'terminal ATTEMPT HOLD: W5 observation set invalid.'
  }

  $TemplateArgs = @($PreparedRuntimeArgs) + @(
    '--emit-owner-go-template', $Go,
    '--owner-go-id', $GoId
  )
  # Governed Python tool call 3 of 5: unsigned template.
  & $Py $RunTool @TemplateArgs
  $TemplateExit = $LASTEXITCODE
  if ($TemplateExit -ne 0) { throw 'terminal ATTEMPT HOLD: unsigned-template emission failed.' }
  $GoDigest = 'sha256:' + (Get-FileHash -LiteralPath $Go -Algorithm SHA256).Hash.ToLowerInvariant()
  $PhaseFlags.template_created = $true
  Assert-ExactChildSet -Path $CustodyParent -Expected @(
    'sciencebase-campaign', 'attempt4-elevated-transcript.txt',
    'attempt4-nonelevated-transcript.txt', 'sciencebase-authority.json', 'owner-go.json'
  )
  [pscustomobject]@{
    ReceiptKind = 'PHASE1B_READY'
    PreparedRuntimeArgs = [string[]]$PreparedRuntimeArgs
    ConnectorRunId = $ConnectorRunId
    GoDigest = $GoDigest
    Py = $Py
  }
} finally {
  $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
  $env:PYTHONDONTWRITEBYTECODE = $PriorBytecode
  $env:PYTEST_ADDOPTS = $PriorPytestAddopts
  $env:PROJECT6_B0_BUNDLE_BINDING = $PriorBundleBinding
  Set-Location -LiteralPath $OriginalLocation
}
})
$Phase1bGuardReturned = $true
$Phase1bRecord = @($Phase1bOutput | Where-Object { $_.ReceiptKind -ceq 'PHASE1B_READY' })
if ($Phase1bRecord.Count -ne 1) { throw 'terminal ATTEMPT HOLD: Phase-1b durable output was not singular.' }
$PreparedRuntimeArgs = [string[]]$Phase1bRecord[0].PreparedRuntimeArgs
$ConnectorRunId = [string]$Phase1bRecord[0].ConnectorRunId
$GoDigest = [string]$Phase1bRecord[0].GoDigest
$Py = [string]$Phase1bRecord[0].Py
} catch {
  if (-not $AttemptState.DispositionWritten) {
    Complete-Attempt4Disposition 'ATTEMPT HOLD'
  }
  throw
}
```

Place the template outside the canonical run root so run containment and closeout cannot modify owner-act bytes. On success, capture the printed `OWNER_GO_SHA256` value as `$GoDigest`; independently rehash the unchanged file before signing. The emitted document has exactly these canonical fields: `schema`, `go_id`, `envelope_digest`, `campaign_id`, `canonical_root`, `connector_run_id`, `source_commit`, `interpreter_identity`, `worker_manifest_digest`, `request_digest`, `authorization_digest`, `grant_digest`, `wrapper_start_token_ref`, `credential_mode`, and `egress_mode`. The fixed values are `schema=project6.sciencebase_live_go.v1`, `credential_mode=none_public`, and `egress_mode=capability_scoped_default_off`.

If the create-once write succeeds but prepared-runtime cleanup fails, the launcher returns `HOLD: runtime_cleanup_failed` and reports `UNSIGNED_TEMPLATE_RETAINED_NON_AUTHORITATIVE_POSSIBLY_STALE`. It intentionally does not delete or overwrite those evidence bytes. That file must not be signed or used; investigate cleanup, then choose a fresh path and fresh `go_id` for a newly validated preparation.

Signing is a separate external owner act and does not itself launch anything. Keep the private key outside the repository. If the owner declines to sign, set `$SigningDeclined = $true` and run the block so the terminal disposition is still recorded. Sign the exact emitted bytes with the fixed namespace:

```powershell
$ExternalPrivateKey = 'C:\path\outside-repo\to\owner-private-key'
$SigningDeclined = $false
try {
  if ($SigningDeclined) { throw 'owner declined signing' }
  if (Test-Path -LiteralPath "$Go.sig") { throw 'signature path already exists' }
  $ObservedGoDigest = 'sha256:' + (Get-FileHash -LiteralPath $Go -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($ObservedGoDigest -cne $GoDigest) { throw 'GO digest drift before signing' }
  & 'C:\Windows\System32\OpenSSH\ssh-keygen.exe' -Y sign -f $ExternalPrivateKey -n project6-sciencebase-live-go-v1 $Go
  $SigningExit = $LASTEXITCODE
  if ($SigningExit -ne 0 -or -not (Test-Path -LiteralPath "$Go.sig" -PathType Leaf)) {
    throw 'signature creation failed'
  }
  Assert-ExactChildSet -Path $CustodyParent -Expected @(
    'sciencebase-campaign', 'attempt4-elevated-transcript.txt',
    'attempt4-nonelevated-transcript.txt', 'sciencebase-authority.json',
    'owner-go.json', 'owner-go.json.sig'
  )
} catch {
  $SigningDisposition = if (Test-Path -LiteralPath "$Go.sig" -PathType Leaf) {
    'SIGNED-AUTHORITY HOLD'
  } else {
    'ATTEMPT HOLD'
  }
  if (-not $AttemptState.DispositionWritten) {
    Complete-Attempt4Disposition $SigningDisposition
  }
  throw 'Signing declined or failed; the unsigned/signed bytes are preserved.'
}
```

OpenSSH writes the detached signature to `$Go.sig`. Only a later direct owner-authorized invocation may re-run the exact same prepared inputs and present the signed GO:

```powershell
$SpentMarkerPath = 'C:\ProgramData\Project6\Authority\sciencebase-go-spent-v1.jsonl'
$LiveGuardSubmitted = $false
$LiveGuardReturned = $false
try {
  # Python binding gate call 5 of 6.
  $PythonBinding = & $PythonGate -PythonArchive $PythonArchive
  if ($LASTEXITCODE -ne 0 -or $null -eq $PythonBinding -or $PythonBinding.status -cne 'PYTHON_BINDING_OK') {
    throw 'terminal SIGNED-AUTHORITY HOLD: binding gate 5 failed.'
  }
  $Py = [string]$PythonBinding.ambient_interpreter
  $ObservedGoDigest = 'sha256:' + (Get-FileHash -LiteralPath $Go -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($ObservedGoDigest -cne $GoDigest) { throw 'terminal SIGNED-AUTHORITY HOLD: GO digest drift.' }
  Assert-ExactChildSet -Path $CustodyParent -Expected @(
    'sciencebase-campaign', 'attempt4-elevated-transcript.txt',
    'attempt4-nonelevated-transcript.txt', 'sciencebase-authority.json',
    'owner-go.json', 'owner-go.json.sig'
  )
  $LiveArgs = @($RunTool) + @($PreparedRuntimeArgs) + @(
    '--owner-go', $Go,
    '--owner-go-sha256', $GoDigest,
    '--owner-go-signature', "$Go.sig"
  )
  $PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
  $OriginalLocation = (Get-Location).Path
  try {
    $env:DUAL_LIVE_RUNTIME_ENABLED = 'true'
    Set-Location -LiteralPath $RepositoryRoot
    # Governed Python tool call 4 of 5: signed live; the guard executes the exact child process.
    $LiveGuardSubmitted = $true
    & $FamilyGuard -Mode LiveRuntime -CurrentRoot $CanonicalRoot -Py $Py -PyArgumentList $LiveArgs
    $LiveExit = $LASTEXITCODE
    $LiveGuardReturned = $true
    $PhaseFlags.signed_live_returned = $true
  } finally {
    $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
    Set-Location -LiteralPath $OriginalLocation
  }
  if ($LiveExit -ne 0) {
    $DurableDisposition = Get-Attempt4DurableLiveDisposition `
      -GoPath $Go -SpentMarkerPath $SpentMarkerPath
    if (-not $AttemptState.DispositionWritten) {
      Complete-Attempt4Disposition $DurableDisposition
    }
    throw "terminal live child returned $LiveExit; durable disposition recorded."
  }
  $DurableDisposition = Get-Attempt4DurableLiveDisposition `
    -GoPath $Go -SpentMarkerPath $SpentMarkerPath
  if ($DurableDisposition -cne 'POST-LIVE CLOSEOUT HOLD') {
    Complete-Attempt4Disposition 'POST-LIVE CLOSEOUT HOLD'
    throw 'terminal live success lacked a matching durable spent marker.'
  }
} catch {
  if (-not $AttemptState.DispositionWritten) {
    $LiveFailureCode = $_.Exception.Message
    if (
      -not $LiveGuardSubmitted -or
      $LiveFailureCode -ceq 'sciencebase_attempt_family_active' -or
      $LiveFailureCode -ceq 'sciencebase_attempt_family_guard_indeterminate'
    ) {
      $DurableDisposition = 'SIGNED-AUTHORITY HOLD'
    } elseif ($LiveFailureCode -ceq 'sciencebase_attempt_family_guard_release_failed') {
      $DurableDisposition = Get-Attempt4DurableLiveDisposition `
        -GoPath $Go -SpentMarkerPath $SpentMarkerPath
    } else {
      $DurableDisposition = Get-Attempt4DurableLiveDisposition `
        -GoPath $Go -SpentMarkerPath $SpentMarkerPath
    }
    Complete-Attempt4Disposition $DurableDisposition
  }
  throw
}
```

After a terminal success, perform the separate no-live closeout verification. Artifact writing rejects content that is empty after whitespace/BOM normalization or whose decoded leading content begins with `<`, `{`, or `[` after leading whitespace and an optional UTF-8, UTF-16LE, UTF-16BE, UTF-32LE, or UTF-32BE BOM. The independent verifier repeats the same negative content-shape floor after length and SHA-256 verification and writes no closeout-verified event on rejection.

```powershell
$CloseoutGuardReturned = $false
try {
  & $FamilyGuard -Mode NonRuntime -Action {
    # Python binding gate call 6 of 6.
    $PythonBinding = & $PythonGate -PythonArchive $PythonArchive
    if ($LASTEXITCODE -ne 0 -or $null -eq $PythonBinding -or $PythonBinding.status -cne 'PYTHON_BINDING_OK') {
      throw 'POST-LIVE CLOSEOUT HOLD: binding gate 6 failed.'
    }
    $Py = [string]$PythonBinding.ambient_interpreter
    $CloseoutArgs = @(
      '--verify-closeout',
      '--canonical-root', $CanonicalRoot,
      '--connector-run-id', $ConnectorRunId,
      '--reservation-database', (Join-Path $CanonicalRoot 'reservation.db'),
      '--owner-go-sha256', $GoDigest
    )
    $PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
    $OriginalLocation = (Get-Location).Path
    try {
      $env:DUAL_LIVE_RUNTIME_ENABLED = 'true'
      Set-Location -LiteralPath $RepositoryRoot
      # Governed Python tool call 5 of 5: no-live closeout.
      & $Py $RunTool @CloseoutArgs
      $CloseoutExit = $LASTEXITCODE
    } finally {
      $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
      Set-Location -LiteralPath $OriginalLocation
    }
    if ($CloseoutExit -ne 0) { throw "POST-LIVE CLOSEOUT HOLD: closeout returned $CloseoutExit." }
    $PhaseFlags.closeout_verified = $true
  }
  $CloseoutGuardReturned = $true
} catch {
  if (-not $AttemptState.DispositionWritten) {
    Complete-Attempt4Disposition 'POST-LIVE CLOSEOUT HOLD'
  }
  throw
}
if (-not $CloseoutGuardReturned) { throw 'POST-LIVE CLOSEOUT HOLD: guard return indeterminate.' }
Complete-Attempt4Disposition 'VERIFIED'
```

`--verify-closeout` checks internal consistency; it neither re-authenticates the GO nor measures containment. Its `sciencebase_closeout_verified` metrics carry `boundary_assurance=owner_waived_unproven`, so `containment_status=contained` is never presented as measured boundary proof. R5 remains OPEN; this is disclosure, not control.

Keep the manual W7 belt-and-suspenders check: before accepting closeout, decode the artifact under any detected UTF-8, UTF-16LE/BE, or UTF-32LE/BE BOM, inspect its leading content, and confirm the expected CSV header/data shape rather than `<`, `<!DOCTYPE`, `<html`, or `<?xml`, even when the automated verifier returns `VERIFIED`.

The launcher pins signer identity `project6-sciencebase-owner-go-v1`, fingerprint `SHA256:wD25Cry/4ZcGWBZXolmIOUNEF96p/yMxQ+y0dZeFZVU`, namespace `project6-sciencebase-live-go-v1`, and the exact public key. None is caller-configurable. This instruction is usage documentation, not a GO or permission to invoke it.

`Complete-Attempt4Disposition` emits exactly one four-field Attempt-4 disposition line to the selected non-elevated transcript before `Stop-Transcript`. Its only top-level keys are `attempt`, `phase_flags`, `disposition`, and `source_head`; it is evidence, not a serializer, recovery frame, receipt, retry grant, or future-attempt parser. Call 4's outer catch covers acquisition, callback, record parsing, and release failure. Signing decline/failure terminates through the same writer. Call 5 maps explicit pre-entry collision/indeterminate codes to `SIGNED-AUTHORITY HOLD`; after submission, a returned child result or release failure is classified by the exact secure current-GO spent marker, with ambiguity conservatively post-live. Call 6 records HOLD on acquisition, callback, or release failure, and records `VERIFIED` only after the guard wrapper returns successfully. Attempt-5 activation remains separately owner-gated and absent, as does any abandoned-chain or missing-release durable proof.
