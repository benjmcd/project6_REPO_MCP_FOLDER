# G2-P8 live4 remote CI correction

Status: `B_OWNER_PACKET_READY / REMOTE RUN 1 RED / CORRECTION LOCALLY VERIFIED / REMOTE RECHECK REQUIRED / NON-AUTHORIZING`

Recorded: `2026-08-08` local / `2026-08-09` UTC

Task ceiling: `B_OWNER_PACKET_READY`

Lease observation: **NO LEASE EXISTS.** This is not terminal `NO_LEASE_ISSUED`.

Owner fields: **ALL BLANK.** Lane A: **LOCKED.**

This append-only record follows `2026-08-08-ci-closure.md`. That earlier record's statements that no
branch had been published, no PR had been opened, and no remote workflow had run remain true for its
recording commit. They are not the current posture after the separately authorized CI-validation
publication described here.

## 1. Remote subject

| Binding | Exact value |
|---|---|
| Packet content commit (C1) | `48305f1a7c84012ba15b7c98c45f866835b1d83d` |
| Custody commit (C2) | `c1954020b57095f954cfb6139e01ee6db2b5fdee` |
| Readiness receipt commit (C3) | `834014fbcea80724193dc2cc981efeea5bc99b91` |
| Local CI correction commit (CI1) | `542e889fc65b44e0085ab81fc831610141ffd685` |
| Published pre-correction head | `a8b9076742e270b95172a6c001cefa4caca49414` |
| Base at publication | `0b65b4f0b06fdbd1e34460800ef8251cebbb9307` |
| Branch | `codex/dl-ci-coverage` |
| Draft PR | `#2485` / `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/2485` |
| First remote run | `31287669983` / `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/actions/runs/31287669983` |
| First-run result | `completed / failure` at head `a8b9076742e270b95172a6c001cefa4caca49414` |

The draft PR spans the Lane B ancestry that is absent from `main`; it is a CI-validation vehicle,
not a claim that its full ancestry is merge-ready or authorized to land.

## 2. First-run determination

The exact 16-file inventory debt remains locally classified and guarded as recorded at CI1. The
first fresh GitHub run did not establish remote closure because it exposed these attributable
cross-platform, fixture, and harness defects:

1. `backend/requirements.lock.txt` was reviewed and hash-bound as CRLF, while an Ubuntu checkout
   supplied LF bytes, causing the dependency verifier and strict-runner checks to reject the lock.
2. the unconstrained PyMuPDF test dependency installed a newer release whose deprecated `fitz`
   shim wrote a warning to standard output before JSON-producing subprocess results;
3. a package-payload fixture intended to be noncanonical produced the canonical bytes on Linux;
4. a reparse-point mock omitted `st_mode`, which POSIX `pathlib` reads before the intended check;
5. PostgreSQL 3C fixtures wrote snapshots under a temporary root while production verification
   correctly required the configured managed artifact root;
6. the browser harness replacement for `run_analysis` had drifted behind the production call and
   rejected the `commit` and `connector_origin_integrity` keywords;
7. root-test shards used a shallow checkout even though two scope tests compare against the pinned
   historical implementation base;
8. the root subprocess environment retained database, storage, evidence-root, and credential-key
   names set during collection; and
9. eight real Windows fixed-volume or PowerShell-launcher proof nodes were being executed on the
   Ubuntu root shards instead of a Windows runner.

Backend coverage itself reached `95.33%`, above the required `90%`; its job failed on test defects,
not on the coverage threshold. PostgreSQL migrations passed before the downstream 3C fixture
failures. Aggregate `root-tests`, `test`, and `release-gate` failures were cascades from their
required child jobs.

## 3. Correction fence

The implementation correction changes exactly these ten paths; its containing commit additionally
adds this append-only record as the eleventh changed path:

1. `.gitattributes`
2. `.github/workflows/playwright.yml`
3. `backend/tests/requirements-layer3-api.txt`
4. `backend/tests/review_browser_server.py`
5. `backend/tests/test_campaign_log_capture.py`
6. `backend/tests/test_ci_coverage_completeness.py`
7. `backend/tests/test_layer3_3c_golden_path.py`
8. `backend/tests/test_layer3_package_entry.py`
9. `backend/tests/test_layer3_pass_entry.py`
10. `tests/test_dual_gate.py`

The narrow behavior is:

- enforce CRLF checkout bytes for the already-bound lock instead of changing its reviewed hash;
- pin the test environment to the packet-validated PyMuPDF `1.27.2.3`;
- make the two platform-sensitive fixtures unambiguously exercise their intended invariant;
- place only the 3C snapshots under the configured managed artifact root while retaining the
  shared helper's existing default behavior;
- make the browser harness accept the production call's two newer keyword arguments;
- fetch full history for root shards and scrub exact runtime inputs from child-test environments;
- skip only eight inherently Windows-bound nodes on non-Windows; and
- run the complete dual-gate file serially on a new `windows-latest` job that is included in the
  release-gate contract.

No production runtime, packet, custody, readiness, grant, plan, seal, database, or live4 artifact is
changed by this correction.

## 4. Local verification and limitation

Passing evidence on the correction candidate:

- coverage-completeness guard: intentional RED `1 failed, 6 passed`, then GREEN `7 passed` after
  mirroring the new Windows job in the exact release-gate contract;
- five primary backend nodes from the first remote failures: `5 passed`;
- two JSON/PyMuPDF-sensitive nodes: `2 passed`;
- full PostgreSQL 3C golden-path file: `11 passed`;
- one legacy/default helper regression: `1 passed`;
- the exact twenty initially failing dual-gate root nodes: `20 passed`;
- complete Windows dual-gate file: `356 passed`;
- focused browser boundary in headless Chromium: `2 passed`;
- the same browser boundary in headed system Chrome: `2 passed`;
- workflow parse, unique job identifiers, release-gate parity, and scoped diff checks: PASS.

The whole 14-file cohort is not relabeled as locally green. On this host it produced `525 passed,
119 failed, 10 errors` because the user-level Python dependency set differs from the CI lock and the
host lacks the suite's fixed-local default database/storage topology. The isolated, exact failure
nodes pass, but fresh GitHub Ubuntu and Windows jobs remain the deciding remote evidence.

## 5. Required remote recheck

This record does not claim the correction successful remotely. After its containing commit is
published to the same draft branch, a new GitHub Actions run must bind that exact head and establish:

1. all four root shards pass with only the eight explicitly Windows-bound nodes skipped;
2. `dual-gate-windows` runs the complete file and passes those Windows-bound nodes rather than
   weakening or omitting them;
3. all four Layer 3 backend shards, serial evaluator, coverage, PostgreSQL 3C, and all Playwright
   shards pass;
4. the release-gate aggregate passes; and
5. no new failure is hidden as an aggregate-only cascade.

If a job fails, its exact log is the authority for another narrow correction. A rerun without a
diagnosis is not evidence of closure.

## 6. State and explicit nonclaims

Current recorded state:

```text
state=B_OWNER_PACKET_READY
remote_ci_state=FIRST_RUN_RED_CORRECTION_PENDING_RECHECK
pr_state=OPEN_DRAFT_CI_VALIDATION_ONLY
owner_fields=ALL BLANK
LEASE_STATE_OBSERVATION=NO LEASE EXISTS
B_OWNER_AUTHORIZED=false
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

This record and its correction grant no P8; owner authorization; lease; credential access or
placement; egress; launch, run, retry, or second launch; residual acceptance; PR-ready conversion;
review approval; merge; landing; runtime rebind; terminal disposition; `NO_LEASE_ISSUED`;
`B_CLEARANCE_RECORDED`; remote custody; or Lane A authority. The PR must remain draft while this
remote CI-validation lane is active.
