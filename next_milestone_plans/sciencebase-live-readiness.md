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

The tranche reuses B0's default-off broker, zero-capability worker, reservation-before-effect transport, exact ScienceBase producer, and containment path. It adds a canonical external GO document bound to the exact envelope, worker manifest, request, credentialless public posture, and capability-scoped egress posture; mandatory authentication of those exact GO bytes and digest by an independently trusted owner capability; a run-scoped create-once GO-consumption event; a content-addressed public artifact plus secret-free terminal event; and a separate verifier that requires the exact three durable reservations, rehashes the artifact, and records one closeout event. The standard launcher has no owner authenticator and therefore remains HOLD even when a caller supplies a self-consistent GO file and digest. Any missing owner authentication, drift, prior GO, reservation mismatch, external-effect ambiguity, terminal-evidence failure, or containment uncertainty remains HOLD with no retry.
