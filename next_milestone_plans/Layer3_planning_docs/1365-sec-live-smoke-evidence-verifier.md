# 1365 SEC Live Source Smoke Evidence Verifier

Target: `sec_live_source_artifact_smoke_evidence_verification_v1`.

Status: branch-local validate-only evidence verifier.

## Purpose

This pass adds a post-smoke verifier for the selected one-filing SEC live
source-artifact smoke path.

The operator-gated smoke runner can produce a private redacted/hash-only report
after a real owner-configured SEC request. Before Arelle/fact authority can
bind to that acquisition, the repo needs a repeatable validate-only check that
the report still matches the retained server-owned receipt and source-artifact
status in the current isolated runtime storage.

Runtime behavior changed by this pass: `false`.
Real SEC network request performed by committed validation: `false`.
Source artifact or receipt created by this pass: `false`.

## Verifier Surface

The verifier is:

`diagnostics/assessment/sec-live-smoke-evidence.py`.

The artifact-free wrapper is:

`./project6.ps1 -Action validate-sec-live-smoke-evidence -ActionArgs "--report", "<operator-private-report.json>"`

The wrapper appends `--no-report`. The verifier requires an existing private
smoke report path, requires the current `STORAGE_DIR` to be explicit,
off-repo/off-OneDrive, existing, and `STORAGE_EXPOSURE=disabled`, then re-reads
the existing SEC live source-artifact status surface for the reported receipt
id. It performs no SEC network request, calls no acquisition path, creates no
source artifact or receipt, and invokes no Arelle subprocess.

## Evidence Boundary

The verifier accepts only the prior smoke runner schema
`diagnostics.sec_live_source_artifact_operator_smoke.v1` with decision
`sec_live_source_artifact_smoke_executed` and no blocking reasons.

It verifies:

- the report path is private, not under the repo or OneDrive
- the report records `live_http` transport and real SEC network execution
- the report remains redacted/hash-only
- hash fields have 64-hex shape
- retained live receipt hash matches the report
- retained source-artifact receipt hash matches the report
- retained source-artifact ref hash matches the report
- retained source identity hash matches the report
- retained content hash and length match the report
- retained source artifact is available

## Negative Invariants

No SEC network request, source artifact acquisition, receipt creation, Arelle
invocation, fact authority, multi-filing enforcement, delivery/export/status
proof, provider delivery, nonlocal auth hardening, value reveal, default-on
graduation, support-matrix graduation, config default change, redaction-posture
change, model/migration change, or production-readiness claim is admitted by
this pass.

## Tier And Review

This pass is a Tier-1 validate-only harness extension over an existing
operator-private report and existing retained server-owned status. It is
Tier-2-adjacent only in the sense that it gates advancement to Arelle/fact
authority; it does not change runtime routes, schemas, persistence models,
support-matrix status, committed defaults, or redaction policy.

Review posture: self-review is adequate if the verifier remains validate-only,
the wrapper keeps `--no-report`, committed proof uses fake SEC transport only
for retained-storage fixture setup, and a fake-transport report is blocked from
normal verification.

## Next Posture

Next posture:
`bind_arelle_fact_authority_to_server_owned_live_source_artifact`.
