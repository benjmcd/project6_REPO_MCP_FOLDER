# G2-P8 live4 branch CI-debt closure

Status: `B_OWNER_PACKET_READY / LOCAL CI-COVERAGE DEBT CLOSED / NON-AUTHORIZING`

Recorded: `2026-08-08`

Task ceiling: `B_OWNER_PACKET_READY`

Lease observation: **NO LEASE EXISTS.** This is not terminal `NO_LEASE_ISSUED`.

Owner fields: **ALL BLANK.** Lane A: **LOCKED.**

This append-only record closes only the exact 16-file branch CI-coverage debt recorded in section 4
of the C3 readiness receipt. It does not rewrite that historical C3 observation, alter the bound
runtime, rebind the packet or custody envelope, fill an owner field, issue P8, place a credential,
arm egress, authorize or perform a launch or retry, clear any non-CI residual, authorize Lane A, or
grant publication, PR, merge, or landing authority.

## 1. Immutable subject and correction

| Binding | Exact value |
|---|---|
| Packet content commit (C1) | `48305f1a7c84012ba15b7c98c45f866835b1d83d` |
| Custody commit (C2) | `c1954020b57095f954cfb6139e01ee6db2b5fdee` |
| Readiness receipt commit (C3) | `834014fbcea80724193dc2cc981efeea5bc99b91` |
| C3 tree | `be41fec1db1bccb8cc38e23f3077b6ef9739f5c8` |
| Readiness receipt path | `docs/campaign-records/2026-08-08-p8-readiness.md` |
| Readiness receipt blob / raw SHA-256 | `d4c24c89f1a05942218f2b541081aa0b98449e46` / `70d14ae8ad92b559e246a5f02f0fa0a8a95041ea4bc84760ab67e0532e7b9ddb` |
| CI correction commit (CI1) | `542e889fc65b44e0085ab81fc831610141ffd685` |
| CI1 tree | `1ebc846a171dd517e68e14d10cbb2193cd17f4c1` |
| CI1 direct parent | C3 `834014fbcea80724193dc2cc981efeea5bc99b91` |
| Implementation branch | `codex/dl-ci-coverage` |

CI1 changes exactly four paths:

| Path | Git blob | Raw SHA-256 |
|---|---|---|
| `.github/workflows/playwright.yml` | `2ca87e1150f0c8cebb8e891637713393b81dac55` | `ba1c07c5785fed046c31d5740b2c9e1caf05383d867e757e07f9f5b808aa32de` |
| `backend/tests/requirements-layer3-api.txt` | `ef921039c2e8d7cb348eb04df783f8b14361a2b1` | `0e2a9022d8b978097d8dcc6ffe6a02e2f8cc379dacc0898a35fa43cff184b8b9` |
| `backend/tests/test_campaign_log_capture.py` | `8768cf80b3aa28670fb6c89da12bf294033d6b84` | `404c2d02a9743b2feef701e77125cff781fb2859a0f5e0707a8bdc8e181f3d74` |
| `backend/tests/test_ci_coverage_completeness.py` | `8b1040fca5a4712d448f5a07badc619a27fb0990` | `9a37af6fe293d57de20d1f6d162f1b7425b2405cb1e67c6e09964fee5925762d` |

All four committed blobs are UTF-8 without BOM, LF-only, final-LF terminated, and the CI1 diff
passes `git diff --check`. The Windows working-tree copies were normalized to CRLF before staging;
Git's clean filter produced the immutable LF-only blobs listed above.

## 2. Exhaustive CI classification

The canonical exhaustive inventory remains every top-level `backend/tests/test_*.py` file. The
fresh CI1 partition is:

```text
296 total = 286 sharded + 1 serial + 1 support + 8 explicitly excluded + 0 uncovered
```

The 40 shard patterns in the completeness guard and workflow are ordered mirrors. No file matches
more than one pattern, no class overlaps another class, and every classified path exists.

The 14 newly sharded files are:

1. `test_arming_api.py`
2. `test_campaign_log_capture.py`
3. `test_connector_transport_loopback.py`
4. `test_dual_live_dependencies.py`
5. `test_dual_live_p4_faults.py`
6. `test_egress_arming.py`
7. `test_egress_auth.py`
8. `test_egress_crash.py`
9. `test_egress_schema.py`
10. `test_egress_transport.py`
11. `test_nrc_fresh.py`
12. `test_nrc_strict_parse.py`
13. `test_sciencebase_fresh.py`
14. `test_sciencebase_locator_live_shape.py`

`test_dual_eval.py` runs exactly once in the existing `backend-layer3-api` aggregator, serially and
with xdist disabled. `test_dual_eval_acceptance.py` remains support-only through nine exact aliases
in `test_dual_eval.py`; it is neither independently collected nor silently excluded. The prior eight
runtime-dependent exclusions are unchanged.

## 3. Narrow correction behavior

CI1 makes only these behavior changes:

1. adds the 14 exact basenames to the four-way Layer 3 backend shard tuple and its guard mirror;
2. classifies the evaluator and its support module explicitly in the exhaustive guard;
3. extends the existing `backend-layer3-api` aggregator to install the same test requirements and
   run `tests/test_dual_eval.py` serially after all four shards pass;
4. raises that aggregator timeout from 10 to 20 minutes, leaving the release-gate job identity and
   dependency edge unchanged;
5. pins `urllib3==2.7.0`, matching the loopback test's enforced version and the production lock; and
6. makes two subprocess-newline assertions follow `os.linesep`, so the newly admitted test is valid
   on the Ubuntu runner and Windows.

The serial step injects no secret and explicitly sets `CONNECTOR_LIVE_EGRESS_ENABLED=false`. Static
review found no `secrets.*`, live4 path, credential value, or external endpoint added by CI1. The only
real socket exercised by the new cohort is the bounded `127.0.0.1` loopback transport test with DNS
stubbed locally.

## 4. Verification evidence

### Red and green guard

- On clean C3, the guard failed with the exact 16-file uncovered set: `1 failed, 5 passed`.
- On the final CI1 bytes, the guard passed: `7 passed in 1.05s`.
- An independent recomputation returned 296 inventory files, 40 patterns, 286 sharded, one serial,
  one support, eight excluded, zero uncovered, zero overlaps, and zero multiply matched files.

### Collection, dependency, and structure

- Fresh collect-only census of all 16 debt files: `1058 tests collected in 17.05s`.
- Loopback transport under the bound Python environment and `urllib3 2.7.0`: `10 passed`.
- Bound-environment `pip check`: `No broken requirements found.`
- Ruff on both edited Python files: `All checks passed!`
- YAML parse: 12 jobs; `backend-layer3-api` timeout 20; five aggregator steps.
- Final `git diff --check`: PASS.

### Serial evaluator

- Full clean-environment, no-xdist census: `404 passed in 383.70s`.
- A separate explicit-false-egress run passed 403 nodes; its only failure was a Windows-only child
  test that deliberately requires the inherited authority variables to be absent. That node is
  skip-bound when `os.name != "nt"` and passed separately under the clean project environment.
  Therefore the Ubuntu CI posture and the Windows-only invariant are both represented without
  treating the intermediate failure as a pass.

### Sharded cohort and platform qualification

- A no-default-DB Windows probe produced `535 passed, 119 failed`; diagnosis rederived the missing
  `backend/method_aware.db` default leaf. The Windows fixed-local checker requires every path
  component to exist and reports the missing leaf through its generic fixed-volume error. The
  corresponding checker is a no-op when `os.name != "nt"`.
- An isolated in-memory rerun narrowed the cohort to `642 passed, 12 failed`. One failure was caused
  by a test-harness `PYTHONPYCACHEPREFIX=NUL` setting and passed after that invalid override was
  removed on the edited branch. Each of the remaining 11 nodes was mechanically verified to carry
  `@pytest.mark.skipif(os.name != "nt", ...)`; they are Windows proof-containment tests and are not
  executed by this Ubuntu job.
- The 642 cohort passes plus the separately passing portability node provide local passing evidence
  for every node not confined to the unresolved Windows-only probe. No Windows-only failure is
  relabeled as a pass, and Ubuntu success is not represented as Windows fixed-volume proof.

### Post-run parity

- CI1 implementation worktree: clean after commit.
- Designated runtime checkout: still clean at `d781adfcaab2eb880456aef7ac49ee589105bbbe`.
- No runtime default DB was created; no Python process remained.
- No implementation-worktree `.pytest_cache`, `__pycache__`, or `method_aware.db` exists.

No remote workflow was run, no branch was published, and no PR was opened. This record therefore
claims local closure of the exact coverage debt, not remote/full-CI, PR-ready, merge-ready, or landed
status.

## 5. State and remaining boundaries

The only state addition is:

```text
exact_branch_ci_coverage_debt=closed_locally_at_CI1
```

All readiness and authority boundaries remain:

```text
state=B_OWNER_PACKET_READY
owner_fields=ALL BLANK
LEASE_STATE_OBSERVATION=NO LEASE EXISTS
B_OWNER_AUTHORIZED=false
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

C4-i, C4-ii, C4-iii, enumeration drift, L2 live frontier, clone-source trust hop, staging order,
point-in-time quiescence, and all fresh owner-decision and launch-final gates remain live. CI1 does
not change the bound runtime revision, plan, seal, campaign, grants, packet, custody envelope, or C3
receipt and therefore does not require a full packet/custody rebind.

The next permitted state-changing step remains a direct owner decision against the exact packet
subject, or an applicable no-lease terminal path. This record is not that decision and does not
issue P8.

## 6. Add-only closure-record acceptance criteria

This closure record is valid only if all of the following pass after its containing commit:

1. the containing commit's parent is exactly CI1
   `542e889fc65b44e0085ab81fc831610141ffd685`;
2. the commit adds only `docs/campaign-records/2026-08-08-ci-closure.md`;
3. all four CI1 blobs in section 1 remain unchanged;
4. the committed record is UTF-8 without BOM, LF-only, final-LF terminated, and passes
   `git diff --check`;
5. the worktree is clean and the C3 packet, custody, readiness, and owner-field state is unchanged;
   and
6. no P8, credential, egress, lease, launch, retry, residual clearance, publication, PR, merge,
   landing, terminal clearance, or Lane A authority is claimed or performed.

The record cannot embed its own future Git identity without changing itself. Its containing commit,
tree, blob, raw SHA-256, byte count, and line-ending facts are therefore derived and reported after
the add-only commit; no self-pinning follow-up commit is required.

## 7. Explicit nonclaims

This record claims only local closure of the exact C3 16-file CI-coverage debt at CI1. It claims no
remote or full CI success; PR readiness; publication; merge authority; main landing; runtime change;
production readiness; residual acceptance; P8; owner authorization; credential placement; egress
authority; lease; run readiness; launch, run, retry, or second launch; terminal disposition;
`NO_LEASE_ISSUED`; `B_CLEARANCE_RECORDED`; remote custody; or Lane A authority.
