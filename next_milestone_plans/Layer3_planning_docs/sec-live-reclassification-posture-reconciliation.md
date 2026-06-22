# SEC live source-artifact reclassification — posture reconciliation & disposition

Status: orchestration disposition record (process/governance only; no code, runtime, schema, flag, or redaction-posture change introduced by this document).
Scope: reconciles the `sec_live_network_egress` reclassification (`unsupported` -> `experimental_default_off`, merged via PRs #2383/#2385/#2386 on `project6-origin/main` at `532e69dd`) against the RC3 `0.3.0-rc1` release declaration, records the independent verification result, and sets the forward owner-gate. Decision: KEEP (do not revert).

## What changed
PRs #2383 (posture reconcile), #2385 (manual SEC live source smoke freeze), and #2386 (SEC live smoke preflight) reclassified `config/support_matrix.yaml` capability `sec_live_network_egress` from `unsupported` to `experimental_default_off`, rewrote the `boundary_note` to disclose "bounded SEC live source-artifact acquisition is armable only by explicit server configuration and remains default-off", added a fail-closed preflight (`diagnostics/assessment/sec-live-preflight.py`), and updated every honesty checker / RC3 acceptance / runtime-contract audit / README / test to the new tier. No actual SEC network egress has occurred (blocked on operator User-Agent).

## Independent verification (orchestrator, adversarial)
A three-dimension adversarial verification (flag+matrix honesty; checkers-not-gamed; no-egress/scope/CI) returned HONEST on all three:
- `backend/app/core/config.py` was NOT modified; `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED` still defaults False and remains in `pinned_false_flags`. No flag default flipped True in production code.
- Only `sec_live_network_egress` status changed; all six forbidden capabilities (`real_provider_delivery`, `model_agent_egress`, `nonlocal_multi_trust_multi_identity`, `high_availability`, `keyed_connectors`, `signed_reference_export`) remain `unsupported`; value-reveal group remains `experimental_default_off`; offline items remain `simulation`.
- The new tier is genuinely enforced: the live-source service is fail-closed (`_require_live_network_enabled()` raises a governed blocked error when the flag is off); the runtime-contract probe was STRENGTHENED to prove zero-fetch default-off behavior; `FORBIDDEN_SUPPORTED` union still contains `sec_live_network_egress` so it can never be classified `supported`; the preflight performs no live request and asserts no fetch / no artifact / redaction preserved.
Conclusion: an honesty *accuracy upgrade*, not an overclaim and not checks-gamed-to-pass.

## RC3 `0.3.0-rc1` consistency — no version bump required
The RC3 release declaration is about the SELECTED SUPPORTED profile: `base=local_expert`, `overlays=[public_connectors, sec_xbrl_offline]`. The reclassification did NOT change the supported surface — `experimental_default_off` is not `supported`. It expanded the experimental (off-by-default, armable-by-config) tier by one capability and strengthened the honesty machinery. Therefore:
- The `0.3.0-rc1` release identity and its supported-profile declaration remain valid and internally consistent on `main`.
- No version bump or supported-profile re-declaration is warranted by this change alone. The `boundary_note`/README updates are honesty completions (disclosing the experimental tier), not new supported claims.

## Value vs. cost (decision basis)
- Value: (1) honesty accuracy — the live-source machinery already exists; `unsupported` was an under-claim, `experimental_default_off` is the truthful tier; (2) a disciplined, fail-closed on-ramp (preflight + freeze + strengthened checks) for an eventual owner-gated real SEC source-artifact smoke; (3) verified-safe, high-quality engineering.
- Cost: (1) one-time posture reconciliation (this document); (2) an open-but-multiply-locked door to real egress (flag off + preflight + owner-arm required); (3) a governance-process note (see below); (4) added maintenance surface (already well-tested).
- Net: value exceeds cost. Reverting would re-introduce the under-claim and discard verified work. KEEP.

## Governance disposition
PRs #2383/#2385/#2386 are Tier-2-class honesty-posture changes (they touch capability classification / redaction-adjacent boundary disclosure). Per `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`, such changes seek independent pre-merge review when practical. They were executor-self-merged without independent pre-merge review. Disposition: retroactive independent verification (this assessment) found them HONEST and fail-closed; no rework required. Going forward, SEC-live posture changes that touch the fail-closed gate behavior or redaction posture must obtain independent review BEFORE merge (encoded in the active M-SEC-LIVE-HARDEN handoff as a Tier-2 hold condition).

## Forward owner-gate (what remains reserved)
- The real one-filing SEC live source-artifact smoke (set `LAYER3_SEC_EDGAR_USER_AGENT`, arm `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=true`, run the preflight, then the smoke) remains an explicit OWNER step — not performed by any agent.
- Graduation of `sec_live_network_egress` beyond `experimental_default_off` (toward `supported`) remains a future OWNER decision, contingent on a successful owner-run smoke with redacted/hash-only evidence and review.
- Milestone M-SEC-LIVE-HARDEN (delegated, in progress) makes the acquisition path production-quality and exhaustively proven SAFE using MOCKED transport only — no real egress, no flag/status/posture change — so the owner can arm with confidence.
