# RC2 Public Connectors Acceptance

Historical note: this document records the RC2 public-connectors acceptance
capstone. The current selected profile is the later final 0.3.0 matrix in
`config/support_matrix.yaml`: `base=local_expert`,
`overlays=["public_connectors","sec_xbrl_offline"]`. Use
`docs/support-matrix-local-expert.md` for current selected-profile status.

This is the explicit RC2 acceptance checklist for `base=local_expert`, `overlays=["public_connectors"]`, public/anonymous connectors only.

RC2 proof level: operator-workflow + local-deployment. ScienceBase public/MCS and Senate LDA anonymous metadata are accepted only as local operator workflows with observable run state, bounded degraded states, source-fidelity evidence, and explicit resume/lease behavior.

No SEC. No OCR. No model/agent egress. No nonlocal deployment. No keyed connector. No high availability. No real provider delivery. The selected overlay does not claim live SEC network, value reveal, controlled submit, durable queues, automatic replay, multi-executor execution, provider fulfillment, or production admission.

OWNER sign-off required before merge.

RC2 verdict: PASS when `scripts/rc2_public_connectors_acceptance.py --json` reports `verdict=PASS` for version `0.2.0-rc1`, `/ready BUILD_INFO.source_sha` records the source SHA, `config/release_readiness.yaml` keeps `owner_selected_profile_specific_gates == []`, and `config/support_matrix.yaml` selects only the `public_connectors` overlay.

| Criterion | Required proof |
| --- | --- |
| Support matrix valid | `scripts/support_matrix_check.py` validates `config/support_matrix.yaml` for `local_expert` and `overlays=["public_connectors"]`. |
| PR-1 correctness | ScienceBase retry/backoff behavior and Senate LDA duplicate filing provenance remain covered by `tests/test_api.py`. |
| PR-2 L17 negative cases | ScienceBase and Senate LDA malformed schema, partial page, and detail/download negative cases stay bounded and observable. |
| PR-3 L20 lifecycle | Completed-run resume no-op, active lease conflict, checkpointed resume, target retry posture, and Senate executor resume stay covered. |
| PR-4 L11 source fidelity | ScienceBase CSV ingest source fidelity, cross-surface dedupe preference, and Senate LDA provenance stay covered. |
| PR-5 canonical journey | ScienceBase public/MCS bridges connector output into analysis, network-unreachable posture is degraded rather than complete, and Senate LDA anonymous metadata requires no key. |
| Forbidden-surface boundary | SEC, OCR, model/agent egress, nonlocal deployment, keyed connector, high availability, and real provider delivery remain excluded from the supported overlay. |
| Owner gate | `config/release_readiness.yaml` stays profile-neutral; `owner_selected_profile_specific_gates` remains empty. |

This acceptance claim is limited to the selected local source-run profile plus the public_connectors overlay. It does not activate or accept SEC value reveal, live SEC behavior, OCR, model/agent egress, keyed connectors, real provider delivery, HA, nonlocal deployment, or default-on external behavior.
