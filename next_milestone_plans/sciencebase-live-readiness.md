# ScienceBase Live-Readiness Tranche

## Current status

This is the canonical prospective Lane B planning and status surface. It is not live authority, owner GO, an authority envelope, a launch token, credential authority, or permission to acquire from ScienceBase.

The local `codex/sciencebase-live-v2` subject is based on the owner-accepted B0 head and implements the bounded path described below. It remains local and unlanded. No live GO was issued or consumed, no ScienceBase request was made, no credential was placed or inspected, and egress was not activated. The waived B0 Windows proof remains `OWNER-WAIVED/UNPROVEN`, never PASS.

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

Before signing, record at least three consecutive same-sitting observations for each of the exact search, hydrate, and download stage URLs using plain `curl.exe` GET requests with redirects disabled. Every observation must report HTTP 200 and no `Location` header. Any non-200, `Location`, curl failure, stage drift, or interrupted sequence resets the count; do not sign until all three stages have three consecutive clean observations in one sitting. Preserve the timestamped commands, exact URLs, status lines, and response-header names with the owner packet.

```powershell
$ExactSearchUrl = '<OWNER-FILL exact bound search URL>'
$ExactHydrateUrl = '<OWNER-FILL exact bound item hydrate URL>'
$ExactDownloadUrl = '<OWNER-FILL exact hydrate-derived download URL>'
if (@($ExactSearchUrl, $ExactHydrateUrl, $ExactDownloadUrl).Where({ [string]::IsNullOrWhiteSpace($_) -or $_ -like '<OWNER-FILL*' }).Count -ne 0) { throw 'W5 exact stage URLs are incomplete.' }
$StageUrls = @(
  @{ Name = 'search'; Url = $ExactSearchUrl },
  @{ Name = 'hydrate'; Url = $ExactHydrateUrl },
  @{ Name = 'download'; Url = $ExactDownloadUrl }
)
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
foreach ($Attempt in 1..3) {
  foreach ($Stage in $StageUrls) {
    $Observed = & curl.exe --disable --silent --show-error --proto '=https' --noproxy '*' --globoff --request GET --max-redirs 0 --output NUL --dump-header - --write-out "`nCURL_STATUS=%{http_code}`n" -- $Stage.Url
    $ObservedText = $Observed -join "`n"
    if ($LASTEXITCODE -ne 0 -or $ObservedText -notmatch '(?m)^CURL_STATUS=200$' -or $ObservedText -match '(?im)^Location\s*:') { throw "W5 stability HOLD: $($Stage.Name) attempt $Attempt" }
    [pscustomobject]@{ Timestamp = (Get-Date).ToString('o'); Attempt = $Attempt; Stage = $Stage.Name; Url = $Stage.Url; Observation = $ObservedText }
  }
}
```

The exact values are owner-filled from the already prepared request and its known/observed stage bindings; placeholders, empty values, URI whitespace, any non-HTTPS scheme, any host other than exactly `www.sciencebase.gov`, any non-default port, userinfo or `@`, any fragment, or any drift are HOLD before the first request. `curl.exe --disable` ignores ambient curl configuration; the explicit protocol, direct/no-proxy, globbing, and redirect constraints prevent the observation recipe from silently widening egress. W5 is a separately authorized operator observation outside the broker/runtime run. Its record is mandatory but non-authorizing and is not runtime availability evidence. The first reserved GET remains the sole audited runtime availability evidence; it is not retried.

## Owner signing and later actuation

First run the standard launcher in prepare-only template mode. `$CanonicalRoot` is a dedicated non-Git campaign/evidence state root; the launcher separately binds and verifies its own clean source checkout. Supply the already-provisioned worker binding and authority-envelope values as the variables below; the launcher revalidates them, derives 14 GO fields from `PreparedRuntime`, adds the caller's explicit fresh `go_id`, writes canonical bytes with create-once semantics, prints the exact digest, closes the prepared runtime, and performs no signature, GO consumption, worker launch, or external effect.

```powershell
$RepositoryRoot = (Get-Location).Path
$CanonicalRoot = 'C:\owner-controlled\project6\sciencebase-campaign'
$CampaignId = 'sciencebase-live-v2'
$ConnectorRunId = '11111111-1111-4111-8111-111111111111' # replace with a fresh UUID
$AuthorityEnvelope = 'C:\owner-controlled\project6\sciencebase-authority.json'
$AuthorizationDigest = 'sha256:' + ('a' * 64) # replace with the exact prepared authorization digest
$GrantDigest = 'sha256:' + ('b' * 64) # replace with the exact prepared grant digest
$ProfileBinding = 'C:\owner-controlled\project6\sciencebase-profile.json'
$WorkerBinding = 'C:\owner-controlled\project6\sciencebase-worker.json'
$WorkerProvisioningRoot = 'C:\ProgramData\Project6\sciencebase-worker'
$PythonArchive = 'C:\owner-controlled\project6\python-3.12.6-embed-amd64.zip'
$AmbientInterpreterRoot = Split-Path -Parent (Get-Command python.exe).Source
$ProfileMoniker = 'Project6.ScienceBase.LiveV2.' + ([guid]::NewGuid().ToString('N').Substring(0,8))
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
$AmbientInterpreterRoot = $Worker.ambient_interpreter_root
$CampaignRoot = $Worker.campaign_root
$AppContainerProfileRoot = $Worker.appcontainer_profile_root
$BrokerProfileRoot = $Worker.broker_profile_root
$UserDataRoot = $Worker.user_data_root
$SourceCommit = (& git rev-parse HEAD).Trim()
$InterpreterIdentity = 'sha256:' + (Get-FileHash -LiteralPath $WorkerInterpreter -Algorithm SHA256).Hash.ToLowerInvariant()
$Query = 'Mineral Commodity Summaries'
$ExpectedItemId = '63d1a3c6d34e06fef15006be'
$ExpectedFileName = 'mcs2023-germa_salient.csv'
.\project6.ps1 -Action initialize-dual-live -- reservation-store --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId
.\project6.ps1 -Action initialize-dual-live -- authority-envelope --output $AuthorityEnvelope --campaign-id $CampaignId --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId --source-commit $SourceCommit --interpreter-identity $InterpreterIdentity --authorization-digest $AuthorizationDigest --grant-digest $GrantDigest
$AuthorityEnvelopeDigest = 'sha256:' + (Get-FileHash -LiteralPath $AuthorityEnvelope -Algorithm SHA256).Hash.ToLowerInvariant()
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
$GoId = '00000000-0000-4000-8000-000000000000' # replace with an explicit fresh UUID
$PriorDualLiveEnabled = $env:DUAL_LIVE_RUNTIME_ENABLED
try {
  $env:DUAL_LIVE_RUNTIME_ENABLED = 'true'
  .\project6.ps1 -Action run-dual-live -- @PreparedRuntimeArgs --emit-owner-go-template $Go --owner-go-id $GoId
} finally {
  $env:DUAL_LIVE_RUNTIME_ENABLED = $PriorDualLiveEnabled
}
```

The target values above are the complete bounded acquisition subject; changing any of them requires a fresh preparation and owner act. `CampaignRoot` is exactly the canonical campaign/evidence root, never the executable source checkout.

Two external, non-authorizing inputs remain. The profile binding must be produced from an actually provisioned broker profile and AppContainer profile—not hand-filled—and contains exactly `profile_moniker`, `package_sid`, `broker_sid`, `appcontainer_profile_root`, `broker_profile_root`, and `user_data_root`. The explicit `initialize-dual-live authority-envelope` step emits canonical JSON with exactly `schema_version`, `campaign_id`, `canonical_root`, `connector_run_id`, `source_commit`, `interpreter_identity`, `authorization_digest`, `grant_digest`, and `wrapper_start_token_ref`. Its schema is `project6.connector_authority.v1`, and its mandatory non-caller-configurable sentinel is `wrapper_start_token_ref=retired:sciencebase-live-v2`. The source commit and worker-interpreter digest must be observed only after the final clean source and external worker closure exist; the two opaque authority/grant references do not themselves grant live authority. B0 does not create or issue either input, and neither substitutes for the later signed one-use owner GO.

The provision commands above require an already-elevated Windows PowerShell 5.1 shell; neither script elevates itself or removes a profile.

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

After a terminal success, perform the separate no-live closeout verification. Artifact writing rejects a body whose decoded leading content, after leading whitespace and an optional UTF-8, UTF-16LE, UTF-16BE, UTF-32LE, or UTF-32BE BOM, begins with `<` (including `<!DOCTYPE`, `<html`, and `<?xml`); the independent verifier repeats the same negative content-shape floor after length and SHA-256 verification and writes no closeout-verified event on rejection.

```powershell
.\project6.ps1 -Action run-dual-live -- --verify-closeout --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId --reservation-database (Join-Path $CanonicalRoot 'reservation.db') --owner-go-sha256 $GoDigest
```

Keep the manual W7 belt-and-suspenders check: before accepting closeout, decode the artifact under any detected UTF-8, UTF-16LE/BE, or UTF-32LE/BE BOM, inspect its leading content, and confirm the expected CSV header/data shape rather than `<`, `<!DOCTYPE`, `<html`, or `<?xml`, even when the automated verifier returns `VERIFIED`.

The launcher pins signer identity `project6-sciencebase-owner-go-v1`, fingerprint `SHA256:wD25Cry/4ZcGWBZXolmIOUNEF96p/yMxQ+y0dZeFZVU`, namespace `project6-sciencebase-live-go-v1`, and the exact public key. None is caller-configurable. This instruction is usage documentation, not a GO or permission to invoke it.
