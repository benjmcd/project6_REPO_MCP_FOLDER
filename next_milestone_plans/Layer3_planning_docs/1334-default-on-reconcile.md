# 1334 - SEC XBRL Predecessor Default-On Reconciliation

## Target

Complete the 1317-mandated reconciliation for the eight predecessor SEC XBRL validate-only diagnostics:
canonical comparability, canonical projection, canonical coverage breadth, canonical retained coherence,
canonical statement organization, multi-period projection, sector-family coverage, and statement assembly.

## Authority

- `next_milestone_plans/Layer3_planning_docs/1314-default-on-admission-restatement.md`
- `next_milestone_plans/Layer3_planning_docs/1317-default-on-runtime-design.md`

1317 admits Arelle fact-authority cutover as default-on while preserving live SEC network,
value reveal, and controlled value-reveal submit as default-off safety boundaries. This slice
completes that posture distinction for predecessor validate-only diagnostics that still used the
older all-three-off runtime-default criterion.

## Implementation

- `committed_runtime_defaults_remain_off` keeps its criterion key for continuity.
- Criterion pass/fail is now governed by the safety subset: live network default-off and value reveal default-off.
- Evidence remains posture-honest: `config_defaults_off=false`, `config_safety_defaults_off=true`,
  `arelle_cutover_default_on_admitted=true`, and `superseded_by_default_on_runtime=true` on current main.
- Projection, comparability, and statement-assembly reports redact zero-valued residual-magnitude keys.
- Canonical comparability regenerates the current-code `canonical_concepts[].family` enrichment to match sibling canonical reports.

## Non-Goals

No `config.py`, runtime behavior, `models.py`, Alembic migration, schema, API, UI, persistence,
source acquisition, SEC network, Arelle invocation, value reveal, operator workflow, export/delivery,
raw runtime artifact, or production-readiness change is made here.

## Verification

The PR for this slice must run the full enumerated SEC XBRL test suite, the posture-freshness guard,
the residual-key guard, target-selection frozen validation, Layer 3 progress validation, py_compile,
double regeneration of the eight reports for byte stability, committed-report redaction/residual scans,
`git diff --check`, and a config-untouched status check.

## Next Posture

After this reconciliation, the predecessor validate-only reports remain ready under 1317's admitted
Arelle fact-authority cutover posture while preserving the hard-off safety boundaries for live network,
value reveal, and controlled value-reveal submit.
