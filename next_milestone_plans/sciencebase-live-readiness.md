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

The tranche reuses B0's default-off broker, zero-capability worker, reservation-before-effect transport, exact ScienceBase producer, and containment path. It adds a canonical external GO document bound to the exact envelope, worker manifest, request, credentialless public posture, and capability-scoped egress posture; mandatory authentication of those exact GO bytes and digest by the pinned Project6 owner Ed25519 identity; a run-scoped create-once GO-consumption event; a content-addressed public artifact plus secret-free terminal event; and a separate verifier that requires the exact three durable reservations, rehashes the artifact, and records one closeout event. Any missing or invalid owner signature, drift, prior GO, reservation mismatch, external-effect ambiguity, terminal-evidence failure, or containment uncertainty remains HOLD with no retry.

## Owner signing and later actuation

First run the standard launcher in prepare-only template mode. `$CanonicalRoot` is a dedicated non-Git campaign/evidence state root; the launcher separately binds and verifies its own clean source checkout. Supply the already-provisioned worker binding and authority-envelope values as the variables below; the launcher revalidates them, derives 14 GO fields from `PreparedRuntime`, adds the caller's explicit fresh `go_id`, writes canonical bytes with create-once semantics, prints the exact digest, closes the prepared runtime, and performs no signature, GO consumption, worker launch, or external effect.

```powershell
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
  '--worker-entrypoint', 'tools/dual_live_run.py',
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

After a terminal success, perform the separate no-live closeout verification:

```powershell
.\project6.ps1 -Action run-dual-live -- --verify-closeout --canonical-root $CanonicalRoot --connector-run-id $ConnectorRunId --reservation-database (Join-Path $CanonicalRoot 'reservation.db') --owner-go-sha256 $GoDigest
```

The launcher pins signer identity `project6-sciencebase-owner-go-v1`, fingerprint `SHA256:wD25Cry/4ZcGWBZXolmIOUNEF96p/yMxQ+y0dZeFZVU`, namespace `project6-sciencebase-live-go-v1`, and the exact public key. None is caller-configurable. This instruction is usage documentation, not a GO or permission to invoke it.
