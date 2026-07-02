# RC3 SEC XBRL Offline Acceptance

This is the explicit RC3 acceptance checklist for `base=local_expert`, `overlays=["public_connectors","sec_xbrl_offline"]`, SEC XBRL offline/simulation only.

RC3 proof level: operator-workflow + local-deployment. The accepted SEC XBRL surface is bounded to offline evidence loading, offline companyfacts staging/oracle checks, offline orchestration, redacted operator review, and release-profile honesty controls. The selected profile keeps live SEC egress, Arelle network resolution, source acquisition, value reveal, controlled submit, model/agent egress, nonlocal deployment, keyed connectors, high availability, and real provider delivery outside the accepted surface.

RC3 verdict: PASS when `python ./scripts/rc3_sec_xbrl_offline_acceptance.py --json` reports `verdict=PASS` for version `0.3.0`, `/ready BUILD_INFO.source_sha` records the source SHA, `config/release_readiness.yaml` keeps `owner_selected_profile_specific_gates == []`, and `config/support_matrix.yaml` selects the `public_connectors` and `sec_xbrl_offline` overlays.

| Criterion | Required proof |
| --- | --- |
| Release identity | `scripts/release_readiness_check.py` and `/ready` build identity prove version `0.3.0` and a source SHA. |
| Support matrix valid | `scripts/support_matrix_check.py` validates `config/support_matrix.yaml` for `local_expert` plus the public connector and SEC XBRL offline overlays. |
| PR-3 loader and proof honesty | `backend/tests/test_sec_xbrl_offline_evidence_loader.py` and `backend/tests/test_sec_xbrl_offline_evidence_proof_capability.py` prove missing/offline evidence fails closed without seeding runtime state. |
| PR-4 orchestrator honesty | `backend/tests/test_sec_xbrl_e2e_offline_orchestrator.py` proves the offline orchestrator preserves redaction and offline controls. |
| Companyfacts offline stage/oracle | `backend/tests/test_layer3_sec_xbrl_companyfacts_stage_and_oracle.py` proves companyfacts staging and oracle-packet checks stay offline and redacted. |
| Full SEC XBRL suite | The `pr5_full_sec_xbrl_suite` command in `scripts/rc3_sec_xbrl_offline_acceptance.py` runs every tracked `backend/tests/test_sec_xbrl_*.py` file. `backend/tests/test_release_rc3_sec_xbrl_offline_acceptance.py` guards that this list stays exhaustive and contains no globs. |
| RC2 connector regression | The selected RC2 public connector tests in `tests/test_api.py` prove the public connector overlay still works under the RC3 profile. |
| Forbidden-surface boundary | The runner inspects `config/support_matrix.yaml` to keep unsupported, experimental-default-off, simulation-only, and pinned-false surfaces bounded. |

The RC3 claim does not authorize live SEC network requests, Arelle network resolution, value reveal, controlled submit, default-on flag changes, schema or migration changes, source acquisition, model/agent egress, nonlocal deployment, keyed connectors, high availability, or real provider delivery.

## 2026-07-02 Full-Suite Reconciliation

The RC3 full-suite list is intentionally exhaustive for `backend/tests/test_sec_xbrl_*.py`. The 2026-07-02 reconciliation added these merged tests that were not in the previous runner list:

| File | Inclusion rationale |
| --- | --- |
| `backend/tests/test_sec_xbrl_a7_chain_ci_durability.py` | Offline synthetic connector-to-material-bridge durability for the A7 fact-authority chain; this is the direct post-PR-2412 completeness gap. |
| `backend/tests/test_sec_xbrl_a7_real_arelle_resolution.py` | Real Arelle fixture proof, skipped unless the pinned Arelle and offline taxonomy/cache are provisioned; no live SEC egress. |
| `backend/tests/test_sec_xbrl_a8_implementation_spec.py` | Planning/readiness authority assertions for merged A8 preclearance docs; no runtime behavior or flag flips. |
| `backend/tests/test_sec_xbrl_a8_lifecycle_design.py` | A8 lifecycle/readiness design assertions, including no reveal enablement and no A7 proof-surface modification. |
| `backend/tests/test_sec_xbrl_offline_honesty_audit.py` | Script-level offline honesty audit coverage for support-matrix, release-gate, and default posture drift. |
| `backend/tests/test_sec_xbrl_offline_honesty_ceiling_exhaustive.py` | Exhaustive offline honesty ceiling coverage for capability evidence, pinned false flags, blocked egress, and simulation-only controls. |

No tracked `backend/tests/test_sec_xbrl_*.py` files are intentionally excluded.
