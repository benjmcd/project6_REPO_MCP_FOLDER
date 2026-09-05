# Operator Utilization Index

## 2026-09-04 current operator pointer

Current tracked state is summarized in
[MASTER_CONTEXT](MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).
On current main, public ScienceBase DatasetVersions can enter the bounded Layer
3 analysis path only when `LAYER3_PUBLIC_DATASET_ANALYSIS_ENABLED=true`; the
source default is `false`. Inspecting public result values additionally requires
`LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED=true`, so both flags must be armed.
The value response remains bound to approved plan/pass/run identity, newest
`sciencebase/public_api` provenance, provenance co-display, and storage-reference
exclusion. This docs pointer is not an arming recipe or authorization.

Retained public runs prove workflow plumbing, not robust temporal findings.
Cross-sectional row order must not be interpreted as time. The next planned
persisted proof uses a qualified operator-local 60-quarter derivative with
explicit normalized-time and per-point lineage; it has not been run through a
persisted API/Layer 3 flow. No fresh download is required for that local proof;
a public-envelope proof requires an appropriate admitted public input.

This is the single entry point for intended local operator use. It is an index,
not a replacement for the source runbooks. Follow the linked authority for the
surface you are using, and keep generated runtime state isolated unless a
runbook explicitly says otherwise.

## Authority And Guardrails

- Repo harness and command rules: [docs/agent-harness.md](agent-harness.md).
- Wrapper action semantics: [docs/harness-validate-inventory.md](harness-validate-inventory.md).
- Current selected local profile: [docs/support-matrix-local-expert.md](support-matrix-local-expert.md) and [docs/local-profile-ops.md](local-profile-ops.md).
- Public connector workflow and the default-off Layer 3 extension: [docs/public-connectors-journey.md](public-connectors-journey.md).
- NRC APS truth model and review path: [docs/nrc_adams/nrc_aps_reader_path.md](nrc_adams/nrc_aps_reader_path.md).
- Layer 3 operator smoke path: [next_milestone_plans/Layer3_execution_handoff/09_L3_OPERATOR_SMOKE_RUNBOOK.md](../next_milestone_plans/Layer3_execution_handoff/09_L3_OPERATOR_SMOKE_RUNBOOK.md).
- SEC/XBRL operator CLI and UI path: [next_milestone_plans/Layer3_execution_handoff/10_SEC_XBRL_OPERATOR_CLI_RUNBOOK.md](../next_milestone_plans/Layer3_execution_handoff/10_SEC_XBRL_OPERATOR_CLI_RUNBOOK.md).

Do not treat archive, handoff mirror, generated map, or populated local runtime
state as implementation truth until the relevant runbook or source file confirms
that authority.

## Setup, Migrate, Start, Status

Use [project6.ps1](../project6.ps1) for the repo-owned wrapper actions. Read
[docs/harness-validate-inventory.md](harness-validate-inventory.md) before using
a wrapper as validate-only proof.

```powershell
.\project6.ps1 -Action setup -Tier1DatabaseBackend sqlite
.\project6.ps1 -Action migrate -Tier1DatabaseBackend sqlite
.\project6.ps1 -Action start-api -Tier1DatabaseBackend sqlite -BaseUrl "http://127.0.0.1:8000"
.\project6.ps1 -Action status -BaseUrl "http://127.0.0.1:8000"
```

The full wrapper flow is:

```powershell
.\project6.ps1 -Action all -Tier1DatabaseBackend sqlite -ConsecutiveRuns 3 -TimeoutSeconds 600
```

`all` performs setup, migration, API start, `/health`, the public ScienceBase
live validation, and API stop. It uses public ScienceBase network access, not
SEC egress. Treat failures as operator evidence to investigate, not as a reason
to seed shared state.

## Acceptance Runners

Run these from the repo root when validating release-profile acceptance. For
the current selected 0.3.0 profile, use the RC3 and local-profile rows. RC1 and
RC2 remain historical capstones for their earlier profile slices.

| Surface | Command | Authority |
| --- | --- | --- |
| Historical RC1 local-expert slice | `python .\scripts\rc1_local_expert_acceptance.py --json` | [docs/rc1-local-expert-acceptance.md](rc1-local-expert-acceptance.md) |
| Historical RC2 public-connectors slice | `python .\scripts\rc2_public_connectors_acceptance.py --json` | [docs/rc2-public-connectors-acceptance.md](rc2-public-connectors-acceptance.md) |
| Current RC3 SEC XBRL offline profile | `python .\scripts\rc3_sec_xbrl_offline_acceptance.py --json` | [docs/rc3-sec-xbrl-offline-acceptance.md](rc3-sec-xbrl-offline-acceptance.md) |
| Local profile operational proof | `python .\scripts\local_profile_acceptance.py --work-dir .\tmp\local-profile-acceptance --json` | [docs/local-profile-ops.md](local-profile-ops.md) |

RC3 is offline/simulation only. It does not authorize live SEC requests,
taxonomy download, Arelle online resolution, value reveal, controlled submit, or
default-on flag changes.

## Proof Gates

Use the narrowest gate that matches the surface being checked. Validation-only
actions must fail closed on missing runtime state and must not seed or generate
runtime artifacts unless the command explicitly declares that behavior.

| Surface | Wrapper | Authority |
| --- | --- | --- |
| Structural harness | `.\project6.ps1 -Action validate-structure` | [docs/agent-harness.md](agent-harness.md) |
| NRC APS replay corpus | `.\project6.ps1 -Action check-nrc-aps-replay-corpus` | [docs/nrc_adams/replay_gate_runbook.md](nrc_adams/replay_gate_runbook.md) |
| NRC APS sync drift | `.\project6.ps1 -Action validate-nrc-aps-sync-drift` | [docs/nrc_adams/sync_drift_gate_runbook.md](nrc_adams/sync_drift_gate_runbook.md) |
| NRC APS safeguards | `.\project6.ps1 -Action validate-nrc-aps-safeguards` | [docs/nrc_adams/safeguard_gate_runbook.md](nrc_adams/safeguard_gate_runbook.md) |
| NRC APS artifact/content indexing | `.\project6.ps1 -Action validate-nrc-aps-content-index` | [docs/nrc_adams/content_index_gate_runbook.md](nrc_adams/content_index_gate_runbook.md) |
| NRC APS evidence bundle | `.\project6.ps1 -Action validate-nrc-aps-evidence-bundle` | [docs/nrc_adams/evidence_bundle_gate_runbook.md](nrc_adams/evidence_bundle_gate_runbook.md) |
| NRC APS validate-only packet refs | `.\project6.ps1 -Action validate-nrc-aps-validate-only-gates -ActionArgs "--no-report"` | [docs/agent-harness.md](agent-harness.md) |
| NRC APS promotion | `.\project6.ps1 -Action validate-nrc-aps-promotion -NrcApsBatchManifest "<manifest>"` | [docs/nrc_adams/promotion_gate_runbook.md](nrc_adams/promotion_gate_runbook.md) |

Some NRC APS gates require existing review/runtime artifacts. If a clean
checkout has no eligible runtime, use the corresponding runbook to create or
restore the runtime before treating a gate failure as product failure.

## NRC APS Review Surfaces

The canonical launch path for shipped NRC APS UI surfaces is
[docs/nrc_adams/nrc_aps_ui_launch_runbook.md](nrc_adams/nrc_aps_ui_launch_runbook.md).
It intentionally binds to an explicit review runtime before the UI is trusted.

```powershell
python .\tools\nrc_ui_launch.py discover
python .\tools\nrc_ui_launch.py serve --latest
python .\tools\nrc_ui_launch.py verify --latest
python .\tools\nrc_ui_launch.py urls
```

Use [docs/nrc_adams/local_corpus_e2e_runbook.md](nrc_adams/local_corpus_e2e_runbook.md)
when you need to create a fresh isolated local-corpus runtime. Use the UI launch
runbook after that runtime exists.

## Layer 3 Workbench

Start with the operator smoke runbook:
[next_milestone_plans/Layer3_execution_handoff/09_L3_OPERATOR_SMOKE_RUNBOOK.md](../next_milestone_plans/Layer3_execution_handoff/09_L3_OPERATOR_SMOKE_RUNBOOK.md).

Core smoke checks include:

```powershell
npx playwright test e2e/layer3-workbench.spec.js --grep "server-backed" --project=chromium
python -B -m pytest backend/tests/test_layer3_api.py backend/tests/test_layer3_page.py -q
python -B -m pytest backend/tests/test_layer3_workbench.py -q
```

The current workbench safety posture keeps connector dispatch, provider/public
URL delivery, APS handoff, and external export/download disabled unless the
specific server-backed path and runbook state admit them.

## SEC XBRL Offline And Operator Path

For the accepted offline release profile, use the RC3 runner and doc:
[docs/rc3-sec-xbrl-offline-acceptance.md](rc3-sec-xbrl-offline-acceptance.md).

For the SEC/XBRL operator-review lifecycle, use
[next_milestone_plans/Layer3_execution_handoff/10_SEC_XBRL_OPERATOR_CLI_RUNBOOK.md](../next_milestone_plans/Layer3_execution_handoff/10_SEC_XBRL_OPERATOR_CLI_RUNBOOK.md).
That runbook separates deliberate CLI `open` from browser UI review controls.
The CLI requires explicit confirmation for live acquisition and reveal.

For nonlocal production admission checks, use
[docs/layer3-admission-runbook.md](layer3-admission-runbook.md). The runtime
evaluator is default-off unless its explicit flag is set in operator-local
runtime configuration.

## A8 Posture

A8 flags are default-off. Arming is owner-local runtime configuration, not a
source default. The authoritative current decision reference is
[next_milestone_plans/Layer3_planning_docs/a8-owner-decision-brief.md](../next_milestone_plans/Layer3_planning_docs/a8-owner-decision-brief.md).
PR #2415 is now the runtime implementation authority for the default-off A8
guard packet. The implementation does not make reveal, internal value-store, or
controlled submit default-on in source.

### Sanitized Real-Data Proof Record (2026-07-02)

A later owner-local D1 -> O2 -> O3 proof exercised the current controlled-submit
reveal path on real data after owner GO. The committed record is sanitized only:
report SHA-256
`790fbb8eaa7de4be447f6c401089cb3b6435ff86614f4f0f57e656fc287a39d8`;
`revealed_fact_count=523`; `non_empty_value_count=497`;
`value_reveal_performed=true`; `production_readiness_claimed=false`;
internal value-store file SHA-256
`3bc81d84fc75bde17d074eee610130efa2659e2b2d281e756402007243eef5a0`;
`value_record_count=523`;
`retention_policy=sec_xbrl_public_financial_value_retention_v1`;
`value_store_hash=eb702c84d42e16200f9f07bbb5888b277b987bca028a51304e922ef2377ce285`;
persisted sidecar receipt hash
`7fe4c3da194396dbe11261eb6ec42942b4c23ce534c37e982f2c872cc4a50546`;
prior flag-off receipt hash
`d5c3585e91397f778f7d0f0297ac05d168dd7410fdaea1e2db7d18cbd3d5036d`;
storage namespace hash
`6483a8de2d45e2f79150273cbb0fcdfcf21bf7769132f19ecf01e71b6de9b354`;
missing-confirmation fail-closed probe SHA-256
`edfdf1ca3d68baacdef80c01cb6cbb0e60496dd59ea7b9102dfe9e90ca097819`.

This was per-run owner-local arming, not a source-default change. The original
proof used a recorded storage-hygiene override case for proof replay, not a
durable-root endorsement.

### Canonical Durable Root (2026-07-04)

The owner-selected canonical durable root for A8 operator runs is `C:/p6store`.
`project6.ps1` attempts best-effort, non-fatal provisioning during `setup`, and
the dedicated `provision-a8-root` action strictly provisions it without changing
global `STORAGE_DIR` behavior for non-A8 flows.

Operator migration record: the durable-root migration copied and verified 43
files (16.62 MB) from the prior proof store, retained the source untouched, and
repointed A8 evidence to `C:/p6store`. The new root passed storage hygiene as
`accepted` with no override. Sanitized migration proof: namespace hash
`4502e1c70863a4bd0067e5f0de4325758d3542e05df223d702747c1886ee6ca9`;
migration manifest SHA-256
`845974f765dc8e7985105053b77e97d6983d94a02f0f015454e9f023e77384fb`;
retained value records `523`; retention policy
`sec_xbrl_public_financial_value_retention_v1`; value-store hash
`eb702c84d42e16200f9f07bbb5888b277b987bca028a51304e922ef2377ce285`.
Do not record the prior sandbox root in committed docs.

PR #2421 (`f566ddb14f62cd717f697f1d13b533ff434785ed`) is the latest O6
guard-doc/support-matrix hardening authority after PR #2415, PR #2419, and
PR #2420. It did not change A8 source defaults or production posture.

Admission note: production-admission evidence is evaluated by
`layer3_sec_xbrl_production_admission.py`, whose containment check requires
`value_reveal_performed=false` in the evaluated evidence run. This real-data
reveal proof is A8 evidence only, not production/nonlocal admission evidence.

For an owner-local A8 run, arm only the needed per-run environment:

- Set `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED=true` when the run
  must persist retained public SEC financial values in the internal value store.
- Also set `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED=true` when
  the run will exercise the controlled reveal-submit path.
- Set `STORAGE_DIR=C:/p6store` for A8 operator runs that arm raw-bearing
  SEC/XBRL flags. This is operator-local runtime configuration, not a source
  default.
- Keep durable A8 roots out of Downloads-like and temp-named locations. Set
  `LAYER3_SEC_XBRL_STORAGE_ROOT_HYGIENE_OVERRIDE_ACK=true` only when
  deliberately proving or replaying the recorded override path for a
  non-durable hygiene case; the override is recorded in receipts and does not
  bypass structural hygiene failures.
- Keep `STORAGE_EXPOSURE=disabled` and set
  `DATABASE_URL=<operator-database-outside-repo-and-cloud-sync>`. The
  containment guard fails closed during Settings initialization when a
  raw-bearing A8 flag is armed with default storage exposure or unsafe database
  placement.

Tracked authority: [project6.ps1](../project6.ps1),
[backend/.env.example](../backend/.env.example),
[a8-implementation-spec.md](../next_milestone_plans/Layer3_planning_docs/a8-implementation-spec.md),
[a8-readiness-gate.md](../next_milestone_plans/Layer3_planning_docs/a8-readiness-gate.md), and
[a8-owner-decision-brief.md](../next_milestone_plans/Layer3_planning_docs/a8-owner-decision-brief.md).

## Stop Conditions

Stop and return to the linked authority instead of improvising when an action
would require any of these:

- live SEC egress, taxonomy download, or Arelle online resolution outside an
  explicitly authorized runbook path
- flag default changes, default-on value reveal, or controlled submit enablement
  in source
- schema/model/migration work
- seeding shared runtime state to make a validate-only command pass
- relying on stale handoff mirrors or generated maps as source truth
- adding browser/UI controls that a runbook or e2e invariant says must remain
  absent
