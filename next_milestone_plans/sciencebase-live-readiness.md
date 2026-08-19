# ScienceBase Live-Readiness Tranche

## Current status

This is the canonical prospective Lane B planning and status surface. It is not live authority, owner GO, an authority envelope, a launch token, credential authority, or permission to acquire from ScienceBase.

The `codex/sb-live-impl` subject was pushed to `project6-origin` per the recorded push and remains unlanded on `main`. No live GO was issued or consumed and no signed live acquisition has occurred. Two non-authorizing characterization runs made one and three ScienceBase GETs respectively, per the recorded characterization records; no credential was placed or inspected, and production live-run egress was not activated. The waived B0 Windows proof remains `OWNER-WAIVED/UNPROVEN`, never PASS.

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

## Implemented local state

The tranche reuses B0's default-off broker, zero-capability worker, reservation-before-effect transport, exact ScienceBase producer, and containment path. It adds a canonical external GO document bound to the exact envelope, worker manifest, request, credentialless public posture, and capability-scoped egress posture; mandatory authentication of those exact GO bytes and digest by the pinned Project6 owner Ed25519 identity; a run-scoped create-once GO-consumption event; a content-addressed public artifact plus secret-free terminal event; and a separate verifier that requires the exact three durable reservations, rehashes the artifact, rejects HTML/XML-shaped error content, and records one closeout event. The owner-ratified D6 reversal removes the pre-consume HEAD health gate: within the broker/runtime chain the order is consume-exact GO, first durable reservation, then the first outbound runtime request, the reserved ordinal-1 GET. That GET doubles as the sole audited runtime availability observation instead of adding a probe; no broker HEAD or other unreserved runtime availability request precedes the reservation. Any missing or invalid owner signature, drift, prior GO, reservation mismatch, external-effect ambiguity, terminal-evidence failure, content-shape rejection, or containment uncertainty remains HOLD with no retry. A redirect, 5xx response, target flap, or inactivity-permitted response that cannot complete before the session watchdog expires, including a slow-trickle degraded target, is an accepted fail-closed member of this burn set: it yields no artifact or `VERIFIED` closeout, only a burned one-use signature, and never authorizes automatic retry. Recovery requires investigation, a freshly prepared run, and a fresh owner-authorized signed GO; the burned run and signature are not reused.

The enclosing session watchdog and each worker-frame read retain the 135,000 ms fail-closed total-time ceiling calculated from the configured quantities: `3 * (max_redirect_hops + 1)` request slots at the 30-second ScienceBase inactivity timeout, the 30-second worker-exit wait, and the named 15-second launch/IPC overhead. For the bound no-redirect request, those accounting inputs are 90,000 ms, 30,000 ms, and 15,000 ms respectively, below the Windows boundary's existing 15-minute validity limit. A request timeout limits the permitted inactivity gap between socket reads; it is not a total response-duration bound. Consequently, this ceiling is not a worst-case wall-clock sum or a guarantee that every inactivity-permitted response completes. Any response still running when the session watchdog expires fails closed with `broker_session_deadline`, produces no artifact or `VERIFIED` closeout, and burns the one-use signature as documented above.

## Mandatory same-sitting pre-signature stability gate

Before signing, record three complete same-sitting search -> hydrate -> download observations using saved response bytes and separate saved headers. Every stage must report exact HTTP 200 with no `Location` header. Any non-200, `Location`, curl failure, parse failure, membership/file/URI drift, or interruption invalidates the complete set; restart with three fresh complete attempts in the same sitting. Retain only the timestamped stage records, exact URIs, status, body SHA-256, body byte length, and derived download URI with the owner packet. Raw vendor bodies and headers are always removed in `finally`.

```powershell
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

$Py = (& py -3.12 -c "import sys; print(sys.executable)").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Py)) {
  throw 'W5 exact Python 3.12 resolution failed.'
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
$ObservationSet
```

The required exact values are owner-filled from the already prepared request and its known/observed stage bindings; placeholders, empty required values, URI whitespace, any non-HTTPS scheme, any host other than exactly `www.sciencebase.gov`, any non-default port, userinfo or `@`, any fragment, or any drift are HOLD before the first request. `$ExactDownloadUrl` is the sole optional confirmation and may remain empty; hydrate bytes remain authoritative. The single search response is intentionally unpaginated: no max, offset, sort, or pagination parameter is added. The local PowerShell 5.1 duplicate-key probe result is recorded, while the explicit Python duplicate-key check remains mandatory whether or not `ConvertFrom-Json` throws. `curl.exe --disable` ignores ambient curl configuration; the explicit protocol, direct/no-proxy, globbing, redirect, and symbolically derived timeout constraints prevent the observation recipe from silently widening or hanging egress. W5 is a separately authorized operator observation outside the broker/runtime run. Its record is mandatory but non-authorizing and is not runtime availability evidence. It reduces burn probability; it does not close R1, authorize W7, replace same-sitting review, become a GO, or alter the first reserved GET as the sole audited runtime availability evidence.

## Owner signing and later actuation

First run the standard launcher in prepare-only template mode. `$CanonicalRoot` is a dedicated non-Git campaign/evidence state root; the launcher separately binds and verifies its own clean source checkout. Supply the already-provisioned worker binding and authority-envelope values as the variables below; the launcher revalidates them, derives 14 GO fields from `PreparedRuntime`, adds the caller's explicit fresh `go_id`, writes canonical bytes with create-once semantics, prints the exact digest, closes the prepared runtime, and performs no signature, GO consumption, worker launch, or external effect.

```powershell
$RepositoryRoot = (Get-Location).Path
$ExpectedBranch = 'codex/sb-live-impl'
$ExpectedSourceCommit = '<OWNER-FILL reviewed head>'
$ObservedBranch = (& git branch --show-current).Trim()
$BranchExit = $LASTEXITCODE
$SourceStatus = @(& git status --porcelain=v1 --untracked-files=all)
$StatusExit = $LASTEXITCODE
$SourceCommit = (& git rev-parse HEAD).Trim()
$CommitExit = $LASTEXITCODE
if (
  $BranchExit -ne 0 -or $StatusExit -ne 0 -or $CommitExit -ne 0 -or
  $ExpectedSourceCommit -like '<OWNER-FILL*' -or
  $ObservedBranch -cne $ExpectedBranch -or
  $SourceStatus.Count -ne 0 -or
  $SourceCommit -cne $ExpectedSourceCommit
) { throw 'Source checkout is not the exact clean reviewed subject.' }
$CanonicalRoot = 'C:\owner-controlled\project6\sciencebase-campaign'
$CampaignId = 'sciencebase-live-v2'
$ConnectorRunId = '<OWNER-FILL fresh UUID>'
if ($ConnectorRunId -like '<OWNER-FILL*') { throw 'ConnectorRunId requires a fresh UUID.' }
$AuthorityEnvelope = 'C:\owner-controlled\project6\sciencebase-authority.json'
$AuthorizationDigest = 'sha256:061102e5c209f4b426ac4c23d0a25514da9d29384e4e24c16306ef7ef587edb2' # B2 authorization label: UTF-8 sha256 of project6:sciencebase-live-v2:B2:authorization-non-authorizing
$GrantDigest = 'sha256:199263280d7c0ea3a880091ebc6d0654d6abca72674bf800c94c11b3580d1ba5' # B2 grant label: UTF-8 sha256 of project6:sciencebase-live-v2:B2:grant-non-authorizing
$W6PreAttempt = '<OWNER-FILL owner-budgeted attempt 1..5>'
if ($W6PreAttempt -notin 1..5) { throw 'W6-PRE attempt must be within the owner-budgeted maximum of five.' }
$AttemptNonce = [guid]::NewGuid().ToString('N')
$BindingParent = 'C:\owner-controlled\project6-bindings'
if ($W6PreAttempt -gt 1) {
  $BindingParent = "C:\owner-controlled\project6-bindings-$W6PreAttempt"
}
if (-not (Test-Path -LiteralPath $BindingParent)) {
  New-Item -ItemType Directory -Path $BindingParent | Out-Null
}
$ProfileBinding = Join-Path $BindingParent "sciencebase-profile-$AttemptNonce.json"
$WorkerBinding = Join-Path $BindingParent "sciencebase-worker-$AttemptNonce.json"
$WorkerProvisioningRoot = 'C:\p6-sciencebase-worker'
if ($W6PreAttempt -gt 1) {
  $WorkerProvisioningRoot = "C:\p6-sciencebase-worker-$W6PreAttempt"
}
$PythonArchive = 'C:\owner-controlled\project6\python-3.12.6-embed-amd64.zip'
$Py = (& py -3.12 -c "import sys; print(sys.executable)").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Py)) { throw 'Exact Python 3.12 resolution failed.' }
$CampaignRootWasPresent = Test-Path -LiteralPath $CanonicalRoot -PathType Container
if (-not $CampaignRootWasPresent) {
  $CampaignRootOwnerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  $CampaignRootSecurity = New-Object Security.AccessControl.DirectorySecurity
  $CampaignRootSecurity.SetSecurityDescriptorSddlForm(
    ('O:{0}D:P(A;;FA;;;{0})(A;;FA;;;SY)' -f $CampaignRootOwnerSid)
  )
  [IO.Directory]::CreateDirectory($CanonicalRoot, $CampaignRootSecurity) | Out-Null
}
$CampaignRootVerifier = @'
from pathlib import Path
import sys
from backend.app.services.sciencebase_spent_marker import WindowsMarkerBackend, _valid_identity
root = Path(sys.argv[1])
backend = WindowsMarkerBackend()
handle = None
try:
    handle = backend.open_existing_directory(root)
    if (
        not _valid_identity(backend.identity(handle), directory=True)
        or backend.secure(handle) != (True, True, True)
        or not backend.fixed_local(handle)
    ):
        raise SystemExit("campaign_root_custody_invalid")
finally:
    if handle is not None:
        backend.close(handle)
'@
& $Py -c $CampaignRootVerifier $CanonicalRoot
if ($LASTEXITCODE -ne 0) { throw 'Campaign root custody verification failed.' }
if ($CampaignRootWasPresent) {
  Write-Host "VERIFIED: secure campaign root $CanonicalRoot"
} else {
  Write-Host "CREATED: secure campaign root $CanonicalRoot"
}
$AmbientInterpreterRoot = Split-Path -Parent $Py
$AmbientInterpreterSha256 = (Get-FileHash -LiteralPath $Py -Algorithm SHA256).Hash.ToLowerInvariant()
$ProfileMoniker = 'Project6.ScienceBase.LiveV2.' + $AttemptNonce.Substring(0,8)
.\scripts\provision-dual-live-profile.ps1 -ProfileMoniker $ProfileMoniker -OutputBinding $ProfileBinding
.\scripts\provision-dual-live-worker.ps1 -PythonArchive $PythonArchive -ProfileBinding $ProfileBinding -ProvisioningRoot $WorkerProvisioningRoot -OutputBinding $WorkerBinding -CampaignRoot $CanonicalRoot -AmbientInterpreterRoot $AmbientInterpreterRoot -RepositoryRoot $RepositoryRoot
$Profile = Get-Content -Raw -LiteralPath $ProfileBinding | ConvertFrom-Json
$Worker = Get-Content -Raw -LiteralPath $WorkerBinding | ConvertFrom-Json
$WorkerBundleRoot = $Worker.root
$WorkerProvisioningRoot = $Worker.provisioning_root
$WorkerProfileMoniker = $Worker.profile_moniker
if ($WorkerProfileMoniker -ne $ProfileMoniker) { throw 'Worker/profile moniker drift.' }
$WorkerManifestDigest = $Worker.manifest_digest
$WorkerInterpreter = Join-Path $Worker.root $Worker.interpreter
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
$WorkerInterpreterSha256 = (Get-FileHash -LiteralPath $WorkerInterpreter -Algorithm SHA256).Hash.ToLowerInvariant()
if (
  [IO.Path]::GetFullPath($BoundAmbientInterpreterRoot) -cne [IO.Path]::GetFullPath($AmbientInterpreterRoot) -or
  $AmbientInterpreterSha256 -cne $WorkerInterpreterSha256
) { throw 'Resolved Python 3.12 and worker runtime binding are not byte-identical.' }
$InterpreterIdentity = 'sha256:' + $WorkerInterpreterSha256
$Query = 'Mineral Commodity Summaries 2023 GERMANIUM'
$ExpectedItemId = '63d1a3c6d34e06fef15006be'
$ExpectedFileName = 'mcs2023-germa_salient.csv'
.\project6.ps1 -Action initialize-dual-live -- reservation-store --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId
.\project6.ps1 -Action initialize-dual-live -- authority-envelope --output $AuthorityEnvelope --campaign-id $CampaignId --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId --source-commit $SourceCommit --interpreter-identity $InterpreterIdentity --authorization-digest $AuthorizationDigest --grant-digest $GrantDigest
$AuthorityEnvelopeDigest = 'sha256:' + (Get-FileHash -LiteralPath $AuthorityEnvelope -Algorithm SHA256).Hash.ToLowerInvariant()
[pscustomobject]@{
  SourceCommit = $SourceCommit
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
} | Format-List
```

The target values above are the complete bounded acquisition subject; changing any of them requires a fresh preparation and owner act. `CampaignRoot` is exactly the canonical campaign/evidence root, never the executable source checkout. The later ceremony uses a dedicated, quiesced checkout at the final reviewed commit, separate from `sb-impl`.

Two external, non-authorizing inputs remain. The profile binding must be produced from an actually provisioned broker profile and AppContainer profile—not hand-filled—and contains exactly `profile_moniker`, `package_sid`, `broker_sid`, `appcontainer_profile_root`, `broker_profile_root`, and `user_data_root`. The explicit `initialize-dual-live authority-envelope` step emits canonical JSON with exactly `schema_version`, `campaign_id`, `canonical_root`, `connector_run_id`, `source_commit`, `interpreter_identity`, `authorization_digest`, `grant_digest`, and `wrapper_start_token_ref`. Its schema is `project6.connector_authority.v1`, and its mandatory non-caller-configurable sentinel is `wrapper_start_token_ref=retired:sciencebase-live-v2`. The source commit and worker-interpreter digest must be observed only after the final clean source and external worker closure exist; the two opaque authority/grant references do not themselves grant live authority. B0 does not create or issue either input, and neither substitutes for the later signed one-use owner GO.

The `authorization_digest:B2` and `grant_digest:B2` labels are KNOWINGLY-RATIFIED non-authorizing attestations that bind nothing. `wrapper_start_token_ref` remains untouched.

W6-PRE may create the output-binding parent under `C:\owner-controlled\project6-bindings` and the dedicated campaign root under `C:\owner-controlled\project6`; both provisioners then run in an already-elevated Windows PowerShell 5.1 shell. Campaign-root creation is create-once: an absent root receives the custody implementation's exact current-token-owner/SYSTEM protected DACL, then identity, fixed-local volume, and `secure()==(True,True,True)` are immediately verified. An already-present root is verified without ACL mutation, so rerunning the step is idempotent and an insecure existing root fails closed. Do not pre-create the worker provisioning root, `C:\ProgramData\Project6`, or its Authority child, and do not add manual ACL steps for those paths: the provisioner remains the sole worker-root and ProgramData ACL mechanism. Each retry requires a fresh single-segment worker root, worker binding, profile binding, and moniker; attempts after the first also take an attempt-scoped binding parent, `C:\owner-controlled\project6-bindings-<attempt>`, a sibling of the campaign root that leaves retained earlier-attempt binding state untouched. There are at most five owner-budgeted elevated W6-PRE attempts; five is an operational stop, not a code ceiling, and failed-attempt state is retained. Capture the final Phase-1 record printed by the block before closing the elevated shell. W7 and template emission are non-elevated and never rerun either provisioner or either initializer.

The worker provisioner invokes `git cat-file blob` once for each of the 8 worker files and explicitly treats any stderr as `worker_source_copy_failed`, even when Git exits 0 (`provision-dual-live-worker.ps1:23-31`, `:122-126`). Whether `2>$null` at `:227`, `:229`, `:247`, and `:248` can itself raise a terminating `NativeCommandError` on Windows PowerShell 5.1 under the script's `$ErrorActionPreference = 'Stop'` at `:13` is not asserted; verify locally before the sitting. A stderr-silent `git` on PATH is a hard prerequisite either way. CI corroborates topology and ACL sequencing only; it is not owner-host broker-identity or interpreter evidence.

The still-HIGH DACL residual is accepted only for this public credential-free run and is not transferable to NRC or another credentialed tranche. The owner accepts the structural-burn risk only with same-sitting W5 and T1.6 pre-7 interruption invalidation; neither R19 nor the separately required characterization is waived.

### Non-elevated Phase-1 rehydration and template emission

Exit the elevated shell after recording the Phase-1 values above. In a fresh non-elevated Windows PowerShell 5.1 shell at the same exact reviewed checkout, assign every `<PHASE-1-RECORD ...>` value below from that output and the two durable binding records. Do not regenerate a nonce, rerun a provisioner, rerun an initializer, or carry an in-memory array across the elevation boundary. The fixed B2 values are the reviewed UTF-8 SHA-256 digests of the named non-authorizing labels; they bind nothing and grant nothing.

```powershell
$RepositoryRoot = (Get-Location).Path
$ExpectedBranch = 'codex/sb-live-impl'
$ExpectedSourceCommit = '<PHASE-1-RECORD source commit>'
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
) { throw 'Non-elevated checkout is not the exact Phase-1 reviewed subject.' }
$CanonicalRoot = 'C:\owner-controlled\project6\sciencebase-campaign'
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
$ObservedAuthorityEnvelopeDigest = 'sha256:' + (Get-FileHash -LiteralPath $AuthorityEnvelope -Algorithm SHA256).Hash.ToLowerInvariant()
if (
  [IO.Path]::GetFullPath($BoundAmbientInterpreterRoot) -cne [IO.Path]::GetFullPath($AmbientInterpreterRoot) -or
  [IO.Path]::GetFullPath($CampaignRoot) -cne [IO.Path]::GetFullPath($CanonicalRoot) -or
  $ObservedInterpreterIdentity -cne $InterpreterIdentity -or
  $ObservedAuthorityEnvelopeDigest -cne $AuthorityEnvelopeDigest
) { throw 'Recorded Phase-1 identity drift.' }
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
$Go = 'C:\owner-controlled\project6\owner-go.json' # outside $CanonicalRoot
$GoId = '<OWNER-FILL fresh UUID>'
if ($GoId -like '<OWNER-FILL*') { throw 'GoId requires a fresh UUID.' }
$PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
try {
  $env:DUAL_LIVE_RUNTIME_ENABLED = 'true'
  .\project6.ps1 -Action run-dual-live -- @PreparedRuntimeArgs --emit-owner-go-template $Go --owner-go-id $GoId
} finally {
  $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
}
```

Place the template outside the canonical run root so run containment and closeout cannot modify owner-act bytes. On success, capture the printed `OWNER_GO_SHA256` value as `$GoDigest`; independently rehash the unchanged file before signing. The emitted document has exactly these canonical fields: `schema`, `go_id`, `envelope_digest`, `campaign_id`, `canonical_root`, `connector_run_id`, `source_commit`, `interpreter_identity`, `worker_manifest_digest`, `request_digest`, `authorization_digest`, `grant_digest`, `wrapper_start_token_ref`, `credential_mode`, and `egress_mode`. The fixed values are `schema=project6.sciencebase_live_go.v1`, `credential_mode=none_public`, and `egress_mode=capability_scoped_default_off`.

If the create-once write succeeds but prepared-runtime cleanup fails, the launcher returns `HOLD: runtime_cleanup_failed` and reports `UNSIGNED_TEMPLATE_RETAINED_NON_AUTHORITATIVE_POSSIBLY_STALE`. It intentionally does not delete or overwrite those evidence bytes. That file must not be signed or used; investigate cleanup, then choose a fresh path and fresh `go_id` for a newly validated preparation.

Signing is a separate external owner act and does not itself launch anything. Keep the private key outside the repository. Sign the exact emitted bytes with the fixed namespace:

```powershell
$ExternalPrivateKey = 'C:\path\outside-repo\to\owner-private-key'
$GoDigest = 'sha256:' + (Get-FileHash -LiteralPath $Go -Algorithm SHA256).Hash.ToLowerInvariant()
& 'C:\Windows\System32\OpenSSH\ssh-keygen.exe' -Y sign -f $ExternalPrivateKey -n project6-sciencebase-live-go-v1 $Go
```

OpenSSH writes the detached signature to `$Go.sig`. Only a later direct owner-authorized invocation may re-run the exact same prepared inputs and present the signed GO:

```powershell
$PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
try {
  $env:DUAL_LIVE_RUNTIME_ENABLED = 'true'
  .\project6.ps1 -Action run-dual-live -- @PreparedRuntimeArgs --owner-go $Go --owner-go-sha256 $GoDigest --owner-go-signature "$Go.sig"
} finally {
  $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
}
```

After a terminal success, perform the separate no-live closeout verification. Artifact writing rejects content that is empty after whitespace/BOM normalization or whose decoded leading content begins with `<`, `{`, or `[` after leading whitespace and an optional UTF-8, UTF-16LE, UTF-16BE, UTF-32LE, or UTF-32BE BOM. The independent verifier repeats the same negative content-shape floor after length and SHA-256 verification and writes no closeout-verified event on rejection.

```powershell
.\project6.ps1 -Action run-dual-live -- --verify-closeout --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId --reservation-database (Join-Path $CanonicalRoot 'reservation.db') --owner-go-sha256 $GoDigest
```

`--verify-closeout` checks internal consistency; it neither re-authenticates the GO nor measures containment. Its `sciencebase_closeout_verified` metrics carry `boundary_assurance=owner_waived_unproven`, so `containment_status=contained` is never presented as measured boundary proof. R5 remains OPEN; this is disclosure, not control.

Keep the manual W7 belt-and-suspenders check: before accepting closeout, decode the artifact under any detected UTF-8, UTF-16LE/BE, or UTF-32LE/BE BOM, inspect its leading content, and confirm the expected CSV header/data shape rather than `<`, `<!DOCTYPE`, `<html`, or `<?xml`, even when the automated verifier returns `VERIFIED`.

The launcher pins signer identity `project6-sciencebase-owner-go-v1`, fingerprint `SHA256:wD25Cry/4ZcGWBZXolmIOUNEF96p/yMxQ+y0dZeFZVU`, namespace `project6-sciencebase-live-go-v1`, and the exact public key. None is caller-configurable. This instruction is usage documentation, not a GO or permission to invoke it.
