# RC1 Local Expert Acceptance

This is the explicit RC1 acceptance checklist for `base=local_expert`, `overlays=none`, analytics-only.

RC1 proof level: operator-workflow + local-deployment in a clean environment; not live-external, not overlay, not nonlocal. The selected profile has connectors excluded, SEC excluded, agent/model egress excluded, public-provider delivery excluded, and the nonlocal base excluded. The release readiness manifest remains profile-neutral and `owner_selected_profile_specific_gates` must stay empty.

RC1 verdict: PASS when `scripts/rc1_local_expert_acceptance.py --json` reports `verdict=PASS` for version `0.1.0-rc1` and `/ready BUILD_INFO.source_sha` records the source SHA.

| Criterion | Required proof |
| --- | --- |
| Support matrix valid | `scripts/support_matrix_check.py` validates `config/support_matrix.yaml` for `local_expert` and `overlays=none`. |
| Canonical analytics journey | `tests/test_api.py::test_canonical_local_expert_journey_recovers_state_with_fresh_client` proves CSV upload, profile, transform, annotation, analysis, state recovery through a fresh client, and the governed `unsupported_method` degraded state. |
| CSV source fidelity recorded | `content_hash`, `source_row_count`, and `dropped_row_count` are covered by the canonical journey, focused upload tests, and `backend/alembic/versions/0055_dataset_version_source_fidelity.py`. |
| Local profile operational acceptance | `scripts/local_profile_acceptance.py` and `backend/tests/test_release_local_profile_operational_acceptance.py` prove install/run, restart-survival, backup/restore, and hidden-state refusal. The RC1 capstone runner references this proof and does not re-run the heavy live-process backup/restore path. |
| Artifact-baked build identity | `scripts/build_app_image.py` passes `PROJECT6_SOURCE_SHA` into the build; `/ready BUILD_INFO.source_sha` and `backend/tests/test_release_identity.py` prove the bounded version/source identity surface. |
| Profile-neutral release gates green | `scripts/release_readiness_check.py` proves the profile-neutral gates and preserves `config/release_readiness.yaml` with `owner_selected_profile_specific_gates == []`. |
| Defaults fail closed | `backend/tests/test_deployment_profile_validation.py` proves nonlocal misconfiguration is rejected and local defaults construct cleanly. |
| Upgrade subcontract | UPGRADE: not_claimed. Upgrade is not an implicit RC1 blocker and is not treated as accepted capability. |

The acceptance claim is limited to method-aware analytics under the selected local source-run profile. It does not activate or accept overlays, nonlocal deployment, public connectors, live SEC behavior, value reveal, controlled submit, model/agent egress, keyed connectors, real provider delivery, HA, or external OCR as an RC1 product claim.
