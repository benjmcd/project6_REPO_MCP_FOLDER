# 1362 SEC Live Source Manual Smoke Freeze

Target: `sec_live_source_manual_smoke_freeze_v1`.

Status: planning/control freeze only.

## Purpose

This pass selects the next production-readiness activation surface after
`sec_live_network_egress` was reclassified as `experimental_default_off`: an
operator-configured manual live SEC source-artifact smoke outside CI.

Runtime behavior introduced by this freeze: `false`.
Real SEC network request performed by this freeze: `false`.

The next pass may exercise the already-landed
`POST /api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire`
surface against one small allowlisted filing, but this freeze does not run that
request, does not create source artifacts, and does not mark the capability
supported.

## Authority Basis

Current live authority already contains the bounded runtime, API route, rendered
control, fake-client proof, redirect guard, rate/user-agent controls, and
redacted receipt/status shape recorded by
`1361-sec-live-source-matrix-transition.md`.

The coherent next proof is a real-network operator smoke because the existing
proof still uses a fake SEC client and explicitly records
`live_sec_manual_smoke_in_this_pass: false`.

## Selected Smoke Envelope

Manual smoke may run only outside CI and only with all of these conditions true:

- `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=true`
- `LAYER3_SEC_EDGAR_USER_AGENT` is configured to an operator-approved contact
  identity.
- The selected filing is one small allowlisted complete-submission text filing.
- `operator_confirmation=true` is included in the request.
- The runtime storage root is isolated from shared seeded state.
- The result records only redacted/hash-only receipt evidence in planning or
  handoff artifacts.

The smoke evidence packet must capture:

- current `project6-origin/main` SHA and smoke branch/worktree identity;
- selected CIK/accession/form/date as operator-approved request inputs;
- request id and route used;
- receipt id, receipt hash, source identity hash, content SHA-256, and content
  length;
- proof that raw SEC URL, raw local path, User-Agent value, and artifact bytes
  were not copied into docs, UI, or handoff notes;
- status re-read by receipt id;
- explicit statement that Arelle, value reveal, controlled submit,
  multi-filing enforcement, delivery/export, provider delivery, nonlocal auth,
  and default-on behavior were not exercised.

## Negative Invariants

No value reveal, controlled-submit, Arelle invocation, multi-filing enforcement, delivery/export, provider delivery, nonlocal auth, default-on behavior, model/migration/persistence change, or production-readiness claim is admitted.

The selected local profile still pins live SEC egress default-off. This freeze
does not change `config/support_matrix.yaml`, `backend/app/core/config.py`,
`.env` defaults, route semantics, redaction posture, CI behavior, models, or
migrations.

## Tier And Review

This is Tier-1 as authored because it is planning/control only and performs no
runtime, persistence, schema, default, or redaction-posture change.

The subsequent manual smoke execution is Tier-2-adjacent even if no code
changes occur, because it records real-network evidence for a live egress
surface. Its closeout must include explicit containment notes, redaction checks,
and coherence review before any downstream Arelle/fact-authority pass begins.

## Next Posture

Next posture: `execute_operator_configured_manual_live_sec_source_artifact_smoke`.

That next posture remains bounded to one real-network source-artifact smoke and
must stop before Arelle/fact authority, multi-filing authority, delivery/export
status, nonlocal auth hardening, or value-reveal/default-on graduation.
