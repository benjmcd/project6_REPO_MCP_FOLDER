# 1265 - SEC XBRL Value-Reveal Operator Exercise Authority

## Target

`sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1`

## Result

The operator-exercise readiness packet in doc `1264` is valid, but the exercise cannot honestly run from the current configured storage authority yet.

The committed fail-closed runner:

`diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-runner.py`

produces:

`diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-run-report.json`

Current report decision:

`value_reveal_operator_exercise_blocked_missing_authority`

## Current Evidence

The current configured storage inventory is redacted by marker only. It records:

- configured storage exists
- storage file count is `0`
- Arelle sidecar receipt count is `0`
- READY sidecar with internal value store count is `0`
- bridge receipt with dataset hash count is `0`
- value-reveal receipt count is `0`

No raw storage root, local path, SEC URL, accession, ticker, actor text, or value is committed.

## Meaning

The missing authority is not a runtime defect in value reveal. It means this checkout does not currently point at retained real-filing sidecar and dataset authorities from an earlier governed run.

The operator exercise must not fabricate sidecars, use synthetic fixtures as product proof, silently fetch SEC data, or run Arelle just to make the reveal test pass. It needs either:

1. an existing isolated storage root containing real-filing READY Arelle sidecar receipts, internal value stores, and bridge/dataset receipts; or
2. a separate authority-provisioning pass that runs the already-governed acquisition, sidecar, and bridge flow under explicitly permitted live/network/Arelle settings and then stops before reveal.

## Required Before Rerunning Operator Exercise

The next pass must provide, by hash only:

- one or more READY Arelle resolved-fact sidecar receipt ids/hashes
- persisted internal value stores tied to those sidecar receipts
- matching bridge receipts carrying `dataset_version_id` and `dataset_version_hash`
- a runtime database containing those dataset_version rows
- confirmation that both committed defaults remain off

Only after that evidence exists should `sec_edgar_arelle_value_reveal_operator_exercise_v1` submit a reveal request.

## Non-Goals Preserved

- no default-on Arelle cutover
- no default-on value reveal
- no SEC network fetch by this runner
- no Arelle subprocess invocation by this runner
- no sidecar, dataset, or audit receipt creation by this runner
- no raw value exposure
- no raw identity, SEC URL, accession, ticker, local path, storage root, contact, or provider/browser authority disclosure
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Candidate B routing for SEC semantics

## Next Slice

`sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1`

That slice should either point the isolated exercise runtime at an existing retained real-filing authority set, or explicitly run the governed acquisition/sidecar/bridge authority provisioning with live network and Arelle permission. It should then stop and rerun the operator-exercise runner before any reveal request is submitted.
