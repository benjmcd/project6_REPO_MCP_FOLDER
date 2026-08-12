# ScienceBase Live-Readiness Tranche

## Current status

This is the canonical prospective Lane B planning and status surface. It is not live authority, owner GO, an authority envelope, a launch token, credential authority, or permission to acquire from ScienceBase.

The local `codex/sciencebase-live-v2` subject is based on the owner-accepted B0 head and implements the bounded path described below. It remains local and unlanded. No live GO was issued or consumed, no ScienceBase request was made, no credential was placed or inspected, and egress was not activated. The waived B0 Windows proof remains `OWNER-WAIVED/UNPROVEN`, never PASS.

## Selected tranche

Implement one efficient, complete end-to-end live-readiness tranche for exactly one bounded ScienceBase acquisition. Keep the tightly coupled path in one coherent implementation PR so review and required CI prove the whole authority-to-closeout chain without serial planning or integration PRs.

The tranche includes only what is mechanically required for:

- exact, one-use owner-GO binding without treating the authority envelope as GO;
- owner-only credential handling and default-off, capability-scoped egress posture;
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

Signing is an external owner act and does not itself launch anything. Keep the private key outside the repository. In PowerShell, bind the exact canonical GO file and sign those bytes with the fixed namespace:

```powershell
$Go = 'C:\path\to\owner-go.json'
$ExternalPrivateKey = 'C:\path\outside-repo\to\owner-private-key'
$GoDigest = 'sha256:' + (Get-FileHash -LiteralPath $Go -Algorithm SHA256).Hash.ToLowerInvariant()
& 'C:\Windows\System32\OpenSSH\ssh-keygen.exe' -Y sign -f $ExternalPrivateKey -n project6-sciencebase-live-go-v1 $Go
```

OpenSSH writes the detached signature to `$Go.sig`. A later direct owner-authorized invocation uses the existing complete prepared-runtime arguments plus exactly:

```powershell
.\project6.ps1 -Action run-dual-live -- <prepared-runtime-arguments> --owner-go $Go --owner-go-sha256 $GoDigest --owner-go-signature "$Go.sig"
```

The launcher pins signer identity `project6-sciencebase-owner-go-v1`, fingerprint `SHA256:wD25Cry/4ZcGWBZXolmIOUNEF96p/yMxQ+y0dZeFZVU`, namespace `project6-sciencebase-live-go-v1`, and the exact public key. None is caller-configurable. This instruction is usage documentation, not a GO or permission to invoke it.
