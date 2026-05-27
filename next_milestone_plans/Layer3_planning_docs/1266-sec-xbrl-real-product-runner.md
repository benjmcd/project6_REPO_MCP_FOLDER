# 1266 - SEC XBRL Real-Corpus Product-Path Runner

## Target

`sec_edgar_real_corpus_product_path_runner_v1`

## Governing Posture

This is a diagnostic runner and gate report for the real-corpus product path. It does not change runtime defaults, product/package/UI behavior, Gate B logic, operator value exposure, source shapes, or SEC routing.

The runner uses the existing governed SEC acquisition/source-artifact/receipt spine and the existing Arelle sidecar, bridge, statement classification, statement product, package/review, handoff/export, delivery/status/provenance, operator inspection, operator product surface, and durable archive services.

It fails closed unless a live run is explicitly requested with:

- a descriptive SEC user agent;
- the pinned Arelle execution environment;
- the offline taxonomy package configuration as explicit package files, not a package directory;
- an Arelle cache directory outside the repo and outside OneDrive, matching the sidecar containment contract;
- the default-off Arelle cutover enabled only inside the diagnostic run.

## Current Committed Report

Report:

`diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json`

Current decision:

`real_corpus_product_path_blocked`

The committed report is a preflight-safe blocked report. It records that a live run was requested with a configured SEC user agent and Arelle Python, but the taxonomy env pointed at a directory and the cache env pointed inside the repo. Both are rejected by the sidecar containment contract. It therefore made no network call, records zero real product-path filings, and does not admit broader real-corpus product reliability.

This preserves the prior gate result instead of upgrading fake-client product-chain evidence into a real-corpus claim.

## Runner Behavior

Script:

`diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`

When run with `--live`, the runner:

- uses a gitignored diagnostic storage directory unless an explicit storage directory is supplied;
- enables SEC live network only inside the diagnostic process;
- applies a one-request-per-second SEC access posture;
- enables the Arelle resolved-fact authority cutover only inside the diagnostic process;
- runs the existing validation/product path over three admitted four-issuer matrix chunks;
- records only redacted matrix hashes, form counts, filing counts, receipt hashes, readiness states, and non-admission evidence;
- keeps operator value reveal disabled;
- restores settings after the diagnostic run.

## Gate Criteria

The report admits only if all criteria pass:

- live preflight satisfied;
- at least 12 real filings observed;
- required forms observed: `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`;
- every supported record uses the Arelle sidecar as the selected fact authority;
- validation, delivery/status/provenance, operator inspection, operator product surface, and durable archive are ready for every matrix chunk;
- operator values remain unexposed;
- final financial-statement semantics and cross-company comparability remain non-admitted.

## Non-Goals Preserved

- no runtime default change;
- no operator value reveal;
- no Candidate-B routing for SEC semantics;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Gate B decision-logic redesign;
- no product/package/UI redesign;
- no RAG/vector/model/provider/auth behavior;
- no new Layer 3 source shape.

## Next Action

Run the same diagnostic with the provisioned SEC/Arelle environment and a descriptive SEC user agent. If the live report admits, the next slice is:

The taxonomy package env must be an `os.pathsep`-separated list of package zip files. The cache env must point outside the repo and outside OneDrive. The runner preflight now mirrors this sidecar contract so invalid Arelle setup blocks before SEC acquisition.

`sec_edgar_operator_surface_gated_value_reveal_v1`

If the live report blocks, keep the next slice on the exact blocked stage reported by the runner.
