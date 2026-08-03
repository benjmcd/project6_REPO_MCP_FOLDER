# G2-P1 eligible-host provisioning (eligibility half) — evidence record (2026-08-03)

> Evidence record. Measured 2026-08-03 BEFORE any credential existed; measurement independently
> reproduced by an adversarial verification pass. Landed under owner authorization 2026-08-03.
> This appends measurement evidence to the OPEN G2-P1 gate defined in
> `2026-08-02-g2-p1-host-provisioning.md` (its §5 checklist) — it is NOT a gate closure.
> Redaction posture: operator-identifying absolute paths / hostname given as neutral placeholders
> (omission only, never false).

## Gate
G2-P1, eligible-host provisioning — the offline eligibility half only. No connector credential,
no egress arming, no network acquisition. This record discharges the *host + dependency-set*
eligibility element measured offline; it does not arm or run the connector, and it does not by
itself close G2-P1.

## Host / runtime
- Host: an eligible operator workstation (identity redacted).
- Interpreter: **CPython 3.12.10** (`py -3.12`).
- Eligibility verified through a **curated virtual environment** under a non-OneDrive scratch root,
  built from the base 3.12.10 interpreter (`include-system-site-packages = false`).

## Curated dependency set (the six exact pins)
Installed `--no-compile` (no `.pyc` emitted into any of the six import roots — verified 0 pyc each):
- certifi==2026.6.17
- chardet==7.4.3
- charset-normalizer==3.4.7
- idna==3.18
- requests==2.34.2
- urllib3==2.7.0

`pip freeze` = exactly those six, nothing else in the reviewed stack.

Three `../../Scripts/*.exe` RECORD lines (the console-script shims in the chardet-7.4.3,
charset_normalizer-3.4.7, and idna-3.18 `.dist-info/RECORD` files) were stripped so the
RECORD manifests contain no `..` path escape — verified 0 remaining dot-dot lines in all three.
On Windows this stripping is structurally required: pip records console scripts as
`..\..\Scripts\*.exe`, and the verifier hard-rejects any `..` component. Only out-of-root shim
lines were removed; every in-root package-file hash still reconciles (see Digest coverage note).

## Verifier
`backend/app/services/dual_live_dependencies.py :: verify_dual_live_dependencies()`
enforces, and this run satisfied:
- `python_version == (3, 12)` — observed (3, 12, 10) → major/minor (3, 12). PASS
- `sys.dont_write_bytecode is True` — set via `PYTHONDONTWRITEBYTECODE=1`. PASS
- `sys.pycache_prefix == "NUL"` — set via `PYTHONPYCACHEPREFIX=NUL`. PASS
- lock SHA256 == `bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02`
  (`backend/requirements.lock.txt`) — confirmed by independent `sha256sum`. PASS
- exactly one installed distribution per pinned name; per-distribution RECORD manifest
  reconciles against disk with no `..` escape and no hash/file drift. PASS

## Result
- **RESULT: PASS**
- **Eligibility digest:** `1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d`
- **Determinism:** identical digest across independent invocations by two separate parties
  (measurement + adversarial re-derivation), loading the verifier + lock both from the in-place
  worktree and from a non-OneDrive detached checkout of the same commit. Byte-for-byte identical.

## D12 doc-drift disposition
Already discharged on-branch at commit **7ab61510** ("G2-P1 doc-drift disposition
py3.11->py3.12 …"): the frozen plan's "Python 3.11+" line is superseded by reference to the
code-enforced exact-3.12 gate at `dual_live_dependencies.py:339-341` (frozen doc blob
`68f740af…` unedited); the non-frozen occurrence corrected in place. No further doc action
required for P1's documentation element.

## Install provenance
The six pins were installed from stock PyPI wheels via
`pip install --no-compile --only-binary=:all: <the six exact pins>`. `--require-hashes` was NOT
used, so wheel-file hashes were not bound against the lock at install time; the verifier's own
`DEPENDENCY_PROVENANCE_NONCLAIM` ("same-version package bytes and RECORD rewritten by the owning
account are not independently authenticated") covers exactly this and is carried, not cured, here.

## Digest coverage note (owner-aware, pre-arming)
The eligibility digest manifests IMPORT-ROOT files only. Out-of-root artifacts — the three
console-script shims and charset_normalizer's site-packages-root `…__mypyc.cp312-win_amd64.pyd` —
are hashed in their RECORDs but excluded from the digest by design (`_canonical_record_path`
returns None for out-of-root paths). The digest is therefore not a full wheel-content binding.
The digest is also platform-specific (win_amd64/cp312): a different-OS eligible host produces a
different value. The verifier only *computes and returns* this digest; the runtime compares it
against a run-configured expected value (`DUAL_LIVE_DEPENDENCY_SET_SHA256`), not a repo constant —
so the value is host-derived by design, but this win_amd64 digest's acceptability for the eventual
live run is an owner/authority determination external to this module.

## File-interference-quiet posture (P1 offline half only)
Strong for the offline digest: the six-pin distributions live in a non-OneDrive scratch venv, the
digest is invariant to OneDrive placement (re-derived identically from a non-OneDrive copy of the
verifier + lock), and bytecode emission was disabled throughout. The clause's live-run
evidence-root quietness remains an OPEN, owner/infra-gated item (not established here).

## No-credential attestation
No connector/NRC credential existed at measurement time; none was created, requested, or armed;
no network acquisition or connector run occurred. This is the offline eligibility half only.

## Verdict and standing
**G2-P1 offline eligibility (host + dependency set): PASS** on CPython 3.12.10, digest
`1c24c982…7885217d`. G2-P1 as a whole remains **OPEN**: actual connector provisioning, egress
arming, live-run evidence-root quietness, and the acquisition-child extras check are
owner/infra-gated and out of scope for this offline measurement.
