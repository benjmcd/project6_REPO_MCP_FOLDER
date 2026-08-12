# ScienceBase Live-Readiness Tranche

## Current status

This is the canonical prospective Lane B planning surface. It records owner intent only. It is not live authority, owner GO, an authority envelope, a launch token, credential authority, or permission to acquire from ScienceBase.

The next implementation subject must first rebase onto the main commit containing the landed B0 capability boundary and reuse those controls. Until that rebase and implementation land, the behavior below is target state rather than current repo behavior.

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
