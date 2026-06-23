# 1364 SEC Live Source Smoke Operator Runner

Target: `sec_live_source_artifact_operator_smoke_v1`.

Status: operator-gated smoke runner and fake-transport proof.

## Purpose

This pass adds an explicit diagnostic runner for the selected one-filing SEC
live source-artifact smoke.

The runner exists because the preflight can prove readiness but cannot execute
or record the actual live source-artifact authority. This pass closes that
repo-side gap without making live network egress default-on and without
claiming that a real SEC request has run in committed validation.

Runtime behavior changed by the committed default path: `false`.
Real SEC network request performed by committed validation: `false`.
Source artifact or receipt created by committed validation: only fake-transport
test artifacts under isolated pytest storage.

## Runner Surface

The smoke runner is:

`diagnostics/assessment/sec-live-smoke.py`.

Dry-run/default behavior:

`python ./diagnostics/assessment/sec-live-smoke.py --no-report`

The default path builds a redacted execution plan from the existing preflight,
exits non-zero, and performs no SEC network request, source-artifact write,
receipt creation, or status readback.

Live execution requires the explicit flag:

`python ./diagnostics/assessment/sec-live-smoke.py --execute-live --output <operator-private-report.json>`

The live execution path first requires
`sec_live_source_artifact_smoke_preflight_ready`. If the preflight is blocked,
the runner stops before importing or calling the live acquisition service. When
the preflight is ready and `--execute-live` is present, the runner calls the
existing server-owned live source-artifact acquisition service exactly for the
selected one-filing request, then re-reads status through the existing status
surface.

## Evidence Boundary

The runner treats the existing service response and status response as the
canonical authority surface. It records only selected redacted evidence:

- live source-artifact receipt id/hash
- source-artifact receipt id/hash
- source-artifact ref hash
- content hash and length
- source identity hash
- server-derived URL hash
- server-configured User-Agent hash
- acquire/status response hashes
- cache and idempotency metadata

The runner report fails closed if its selected evidence includes raw CIK,
normalized CIK, accession, User-Agent, storage path, SEC URL, or artifact bytes.

## Negative Invariants

No Arelle invocation, fact authority, multi-filing enforcement,
delivery/export/status proof, provider delivery, nonlocal auth hardening,
value reveal, default-on graduation, support-matrix graduation, config default
change, redaction-posture change, model/migration change, or production
readiness claim is admitted by this pass.

## Tier And Review

This pass is operator-workflow-sensitive because it adds a diagnostic capable of
calling the live acquisition service under explicit operator configuration.
It does not change runtime routes, schemas, persistence models, support-matrix
status, committed defaults, or redaction policy.

Review posture: Tier-2-adjacent self-review is required for the command
contract and redaction boundary; the committed proof remains fake-transport
only. A real operator execution of `--execute-live` must be recorded as a
separate evidence-bearing pass before advancing to Arelle/fact authority.

## Next Posture

Next posture:
`operator_runs_sec_live_source_artifact_smoke_with_private_redacted_report`.
