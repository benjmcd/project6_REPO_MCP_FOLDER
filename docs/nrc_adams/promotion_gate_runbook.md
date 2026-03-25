# NRC APS Promotion Readiness Runbook

> Status note (2026-03-11): current NRC APS status, proof artifacts, closed-layer guidance, and next-step handoff are frozen in [nrc_aps_status_handoff.md](nrc_aps_status_handoff.md). This runbook remains gate-specific/operator-procedural.

## Purpose
This runbook defines the local, fail-closed promotion-readiness workflow for NRC APS:
1. collect a fresh isolated live-validation batch,
2. evaluate promotion using that batch manifest only,
3. optionally compare tuned policy thresholds without mutating canonical baseline policy.

This workflow is artifact-first and auditable.

## Batch Contract
- Manifest schema: `aps.live_validation_batch.v1`
- Manifest fields include:
  - `finalized` and `finalized_at_utc`
  - `manifest_sha256`
  - `manifest_checksum.algorithm` (`sha256`) and `manifest_checksum.value`
  - per-cycle report refs and checksums
  - collector provenance (`collector_version`, `collector_invocation_argv`, `collector_config`)
  - cycle spacing semantics (`cycle_spacing_seconds_requested`, `cycle_spacing_enforced`, `cycle_spacing_affects_batch_validity`)
- Finalized manifests are immutable.
- Promotion evaluation fails closed on:
  - invalid/missing manifest checksum or sidecar checksum mismatch
  - missing/mutated cycle report refs/checksums
  - mixed or unexpected report schemas

## Live Validation Report Contract
- Report schema: `aps.live_validation_report.v1`
- APS-V1 key must be present as `tests.APS-V1_qps_ramp_test` in fresh reports.
- `APS-V1_qps_ramp_test.status` is one of:
  - `observed`
  - `skipped`
  - `error`

## Promotion Evaluation Contract
- Promotion report schema: `aps.promotion_governance.v2`
- Evaluator version is recorded in report (`evaluator_version`).
- Evaluation is manifest-authoritative:
  - one `--batch-manifest` at a time
  - no directory scan mixing
  - no cross-batch aggregation
- Stable machine-readable failure codes are emitted in `evaluation.failures`.
- Report records:
  - batch manifest ref/hash
  - policy ref/hash
  - collector provenance copied from manifest
  - per-cycle evidence rows

## Policy-Only Tuning Contract
- Comparison schema: `aps.promotion_policy_compare.v1`
- Diff schema: `aps.promotion_policy_diff.v1`
- Rationale schema: `aps.promotion_policy_rationale.v1`
- Rules:
  - baseline canonical policy is read-only in experiments
  - tuned policy is an override artifact only
  - every tuned key requires rationale entry
  - non-tunable key changes fail closed
  - tuned-policy PASS is `experimental_pass_not_promoted` until explicitly promoted

## Commands
Run from repo root.

### 1) Collect a fresh isolated batch
```powershell
.\project6.ps1 -Action collect-nrc-aps-live-batch -ConsecutiveRuns 3 -BatchSpacingSeconds 5 -TimeoutSeconds 45
```

### 2) Evaluate promotion for one batch
If `-NrcApsBatchManifest` is omitted, script uses the latest manifest under the batch root.

```powershell
.\project6.ps1 -Action validate-nrc-aps-promotion -NrcApsBatchManifest "<abs_manifest_path>"
```

Direct CLI:
```powershell
py -3.12 tools/nrc_aps_promotion_gate.py --batch-manifest "<abs_manifest_path>" --policy backend/app/services/nrc_adams_resources/aps_promotion_policy_v1.json
```

### 3) Compare tuned thresholds (code-free tuning)
Create a rationale file:
```json
{
  "schema_id": "aps.promotion_policy_rationale.v1",
  "schema_version": 1,
  "entries": [
    {
      "key": "min_pass_rate",
      "reason": "Temporary adjustment for observed live variability in current batch window."
    }
  ]
}
```

Run comparison:
```powershell
.\project6.ps1 -Action compare-nrc-aps-promotion-policy `
  -NrcApsBatchManifest "<abs_manifest_path>" `
  -NrcApsTunedPromotionPolicy "<abs_tuned_policy_path>" `
  -NrcApsPromotionRationale "<abs_rationale_path>"
```

## Output Artifacts
- Promotion report:
  - `tests/reports/<batch_id>_aps_promotion_eval_v1.json` (default)
- Policy tuning artifacts:
  - `tests/reports/<batch_id>_aps_promotion_policy_diff_v1.json`
  - `tests/reports/<batch_id>_aps_promotion_compare_v1.json`
  - `tests/reports/<batch_id>_aps_promotion_baseline_eval_v1.json`
  - `tests/reports/<batch_id>_aps_promotion_tuned_eval_v1.json`

## Safeguard Boundary
- Live batch collection reuses the existing APS safeguard layer.
- No separate live-execution path is allowed to bypass safeguards.
- Replay gate and 2A sync-drift gates remain unchanged and separate.
