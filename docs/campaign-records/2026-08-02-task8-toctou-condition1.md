# Task 8 Condition 1 — Content-Stability Correction and Host Proof

Date: 2026-08-02 PDT
Branch: `codex/dual-live-plan`
Implementation HEAD tested: `a13a5fa0b3d513e79bbe0d72a32693ca9d5ba202`
Implementation tree tested: `42e01ff3f45ec37f0ff9a6644a0c79fd139700fb`

## Verdict

- `[REPRODUCED]` Review condition 1 is satisfied through its authorized TOCTOU-fix alternative: the standalone dual evaluator passed `401/401`, exit 0, twice on this ordinary Windows host.
- `[REPRODUCED]` The three named tamper campaigns now execute rather than dying in fixture setup. Pytest reports five passing cases because the third named test is parametrized for delete, duplicate, and rewrite variants.
- `[REPRODUCED]` The final implementation HEAD passes the 356-test gate and the exact V4 command (`806/806`).
- `[REPO-CONFIRMED]` The correction remains fail-closed for observed content mutation. Timestamp-only churn is accepted, while same-size byte changes between the first and second hashes or after the second hash are rejected.
- `[NOT AUTHORIZED / NOT CLAIMED]` This record does not authorize G2, live acquisition, egress, credentials, push, merge, default-on behavior, or any change to the frozen campaign authority.

## Host binding

- Computer: `<operator-host>`
- Manufacturer/model: `Alienware / Alienware Aurora ACT1250`
- OS: `Microsoft Windows 11 Home`, version/build `10.0.26200`, 64-bit
- Interpreter: `C:\Users\<operator>\AppData\Local\Programs\Python\Python312\python.exe`, Python `3.12.10`
- Execution posture: offline; no egress or credentials used
- Python emitted `RequestsDependencyWarning`: installed `urllib3 2.6.3` and `chardet 7.1.0` / `charset_normalizer 3.4.4` do not match the installed Requests support declaration. This correction does not make the host dependency-eligible for a real/live run.

## Minimal implementation

### Commit `f571be83` — managed output content stability

- `backend/app/services/layer3_execution_output.py`
  - Retains the existing regular-file, path-containment, size-cap, and two-hash checks.
  - Uses stable file identity `(mode, device, inode, size)` instead of `mtime/ctime` for metadata comparisons.
  - Adds a final reopened-path bounded hash and identity checks, rejecting a same-size change after the original second hash.
- `backend/tests/test_layer3_execution_output.py`
  - Proves timestamp-only churn is accepted.
  - Proves same-size mutations between hashes and after the second hash fail closed.

### Commit `5f76f949` — downstream snapshot homolog

The first admissible census attempt reached a second pre-existing guard with the same metadata-TOCTOU defect in `layer3_origin_continuity.py`; it produced `330 passed, 2 failed, 69 errors` in `173.33s`. This was the only adjacent production correction required to unblock the mandated census.

- `backend/app/services/layer3_origin_continuity.py`
  - Applies the same identity-plus-three-bounded-content-observations rule.
  - Preserves the exact database-bound `payload_hash` comparison and fail-closed authority error.
- `backend/tests/test_layer3_origin.py`
  - Proves timestamp-only churn is accepted.
  - Proves same-size mutations between hashes and after the second hash fail closed.
- The exact previously failing A01 node then passed: `1 passed` in `16.99s`.

### Commit `a13a5fa0` — publication metadata churn

The first final V4 attempt exposed the last homologous comparison in output-manifest publication: `804 passed, 1 failed`, with the failure at `test_gated_package_entry_marks_excluded_inventory_as_warning_packages`. The correction changes only the publication metadata comparison to file identity; the subsequent stable-file content verification and exact `published_bytes == payload_bytes` check remain intact.

- Added a publication timestamp-churn regression test.
- Added the already changed production path to the existing gate allowlist.
- The new regression and exact formerly failing V4 node passed together: `2 passed`.
- Combined affected-module regression: `126 passed, 1 warning`.
- Ruff on the affected Python files: `All checks passed`.

`Layer3WorkbenchError` was not changed: it did not mask diagnosis after these corrections.

## Exact reproduced evidence

All pytest commands used `-p no:cacheprovider`; no test artifacts were intentionally seeded or generated.

### Standalone evaluator census — run 1

Working directory: `backend`

```text
C:\Users\<operator>\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/test_dual_eval.py -q -p no:cacheprovider
401 passed, 1 warning in 290.63s
exit 0
```

### Standalone evaluator census — run 2

Working directory: `backend`

```text
C:\Users\<operator>\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/test_dual_eval.py -q -p no:cacheprovider
401 passed, 1 warning in 291.31s
exit 0
```

Both standalone census runs were made on production HEAD `5f76f949`. Final HEAD `a13a5fa0` changes only the homologous publication comparison, its regression test, and the gate allowlist; the exact final-head V4 below reruns the complete 401-node evaluator module.

### Three named tamper campaigns

Working directory: `backend`

```text
C:\Users\<operator>\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/test_dual_eval.py::test_one_log_byte_and_rebuilt_manifest_preserve_exact_seal_taxonomy tests/test_dual_eval.py::test_one_log_byte_rebuilt_manifest_and_seal_exposes_database_witness tests/test_dual_eval.py::test_database_seal_event_rewrite_cannot_rewrite_original_files -q -p no:cacheprovider
5 passed, 1 warning in 69.53s
exit 0
```

The direct acceptance module is intentionally non-collected; these are its collected wrapper nodes. The five cases cover the three named campaigns, with delete/duplicate/rewrite parameterization in the third.

### Final-head gate

Working directory: repository root

```text
C:\Users\<operator>\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/test_dual_gate.py -q -p no:cacheprovider
356 passed, 1 warning in 98.02s
exit 0
```

Before the one-path allowlist correction, the gate result was `355 passed, 1 failed`; the sole failure was the gate correctly rejecting the newly changed production path.

### Final-head V4

Working directory: `backend`

```text
C:\Users\<operator>\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q -p no:cacheprovider
806 passed, 3 warnings in 335.05s
exit 0
```

## Authority preservation and scope

- Frozen M0 plan remains byte-identical: `docs/superpowers/plans/2026-07-29-dual-live-proof.md` hashes to `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`.
- The final gate reproduced the B1a pilot seal assertion `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`.
- The accepted completion record was referenced, not edited: `docs/campaign-records/2026-07-31-task8-ascoped-review-and-completion.md` hashes to `8d5e9dafc10de67f5dcf499f900169c0175197e2`.
- No frozen plan, sealed record, `state/agent-inbox`, `forward-plan-review`, fenced worktree, or B1a-seal source was edited.
- No network, push, or merge operation was performed.

## Limits, cost, and remaining gate

- `[BOUNDARY]` This is a finite observation protocol, not an atomic filesystem snapshot. A mutation completed before the first observation, after the final observation, or changed and restored wholly between observations cannot be represented as a concurrent difference. Every mutation deliberately injected at an observed boundary fails closed.
- `[COST]` Protected reads now perform a third bounded content pass, approximately 50% more hash I/O than the prior two-pass check. The change is local to these integrity paths and adds no framework or background work.
- `[BOUNDARY]` Identity includes size but not `mtime/ctime`, so metadata-only churn cannot create a false failure. Content equality is enforced by SHA-256 observations; database-bound downstream payloads retain their authoritative hash comparison.
- `[REMAINING]` Condition 1 and the tamper-execution half of condition 4 are now evidenced. G2/live acquisition remains blocked by the other governing prerequisites, explicit authorization, and current live-run dependency eligibility; this record must not be used as G2 authority.
