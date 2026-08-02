# Task-8 A-Scoped Offline Build Implementation Plan

> **For implementation workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the owner-approved, offline-only Task-8 producer, protected runtime evidence, read-only evaluator, and validate-only gate at the frozen acceptance bar without an attestation object, a post-run index, a new required environment input, or a frozen-plan amendment.

**Architecture:** A Windows-only controller owns the four existing campaign log files and pumps bounded child frames into them. It runs acquisition and downstream phases as separate Job-contained processes, records logger and quiescence evidence in the sealed `app.jsonl` stream, and seals through the existing capture service. A fixed check registry reuses the existing evidence-index, ledger, origin, package, and capture contracts; the gate acquires ordered evidence-root and campaign locks, opens an existing SQLite database read-only, and proves DB/filesystem stability before emitting one secret-safe verdict.

**Tech Stack:** Python 3.11, FastAPI/Pydantic v2, SQLAlchemy 2, SQLite read-only URI mode, Windows Job Objects/private namespaces/owner-PID TCP and UDP tables through `ctypes`, pytest, PowerShell.

## Global Constraints

- Authority is `docs/campaign-records/2026-07-30-task8-adjudication.md` at branch HEAD `6aa98ecafb7ce3fddfc37e1e859b2ef7c8e77e50` plus the frozen `docs/superpowers/plans/2026-07-29-dual-live-proof.md`.
- Offline only: no live acquisition, no external egress, no real credential use, no deployment, no push, and no production-readiness claim.
- Do not edit the frozen plan, any campaign/sealed record, `docs/dual-live-postrun-evidence-design.md`, the B1a seal, `state/agent-inbox`, blob `bc47335c`, `forward-plan-review`, or another fenced worktree.
- Do not create a post-run attestation, attestation index, issuer, fifth capture stream, configuration key, or required environment variable.
- Preserve the exact four capture files: `app.jsonl`, `http.jsonl`, `stdout.log`, and `stderr.log`.
- The wrapper is the only disk writer. Children receive bounded anonymous-pipe endpoints, not log paths or log-file handles.
- `http.jsonl` contains canonical counter records only. Wrapper runtime records and JSON application logs belong in `app.jsonl`.
- The default `run-dual-live-proof` invocation refuses without the existing campaign, evidence, database, storage, and authority settings and causes no file, row, process, socket, or marker effect.
- Validation is validate-only: it may query and rehash but never create, update, delete, seed, normalize, repair, checkpoint, migrate, or generate a row or artifact.
- Unsupported platforms and unverifiable Windows features fail closed; there is no `taskkill`, PowerShell-process-census, or `psutil` acceptance fallback.
- Locks are acquired evidence-root first and campaign second and retained through the participant's final stability reread; release is the reverse.
- A new counter record uses `project6.connector_http_counter.v2`; historical v1 remains readable but cannot support a new Task-8 PASS.
- Evaluator `PASS` requires two completed connector runs and every A/R/L/D/C/F check. The gate may expose that result only after both G checks pass; demonstrated policy failure is `FAIL`, missing/conflicting/ambiguous evidence is `INDETERMINATE`, and unsafe invocation is `REFUSED`.
- Preserve the scaffold's existing `fresh_live` and `evaluation_complete` report keys as descriptive, non-authoritative fields: `fresh_live` is true only for `PASS`, while `evaluation_complete` is true only when the fixed registry completed as `PASS` or `FAIL`.
- Small reviewable commits, no automated-tool attribution or trailers, no unrelated refactor, and `git diff --check` after every tranche.

---

## File and Interface Map

### New focused units

- `backend/app/services/dual_live_runtime.py`
  - Canonical runtime-record envelope and hash chain.
  - Bounded pipe framing, child control frames, wrapper FSM, first-stop latch, and pipe pumps.
  - Strict logger topology census, handler freeze/recheck, child sequencing, environment allowlists, capture integration, and final sealing.
  - Child bootstrap entrypoints for one-use GO, counter context, Phase-A raw acquisition, Phase-B strict parsing/downstream flow, and secret-safe authority posture.
- `backend/app/services/dual_live_windows.py`
  - SID-private namespace and exact-DACL mutexes.
  - Evidence-root then campaign lock acquisition.
  - Atomic child creation inside a kill-on-close/no-breakaway Job.
  - Retained process identity, Job-zero proof, descendant process-table census, and owner-PID TCP4/TCP6/UDP4/UDP6 census.
  - Public immutable projection of handle-bound child-start evidence for the runtime record.
- `tools/dual_live_run.py`
  - Strict CLI adapter for wrapper and internal phase child modes.
  - Installs the required pre-import guards for Phase B before importing application services.

### Existing production units modified narrowly

- `backend/app/services/connector_egress_authorization.py`
  - Add explicit-settings read-only evidence-chain and historical-grant adapters; preserve existing default callers.
  - Add a local-runner owner receipt that is limited to local, non-proxy, exclusive proof mode and a `local_loopback` grant; proxy-owner authority remains request-bound and refused by the CLI.
- `backend/app/services/connector_egress_transport.py`
  - Add counter-v2/runtime-context parsing and emission, wrapper pipe sink, serialized physical-send boundary, revocation checks, and send-idle lease.
- `backend/app/services/connector_egress_arming.py`
  - Accept exact v1 or exact v2 counter records and reject mixed runtime/boot identity.
- `backend/app/services/connectors_nrc_adams.py`
  - Accept the canonical strict-run `source_system` emitted by the arming and capture owners; retain every other reserved-run guard.
- `backend/app/services/nrc_aps_phase_b_linkage.py`
  - Use the same canonical strict NRC run identity during Phase-B linkage.
- `backend/app/core/config.py`
  - Disable dotenv loading at module-singleton construction under Python isolated mode before any service import; retain normal non-isolated application startup behavior.
- `backend/app/services/connector_campaign_log_capture.py`
  - Add read-only manifest/seal/event verification adapter and controller-safe capture metadata projection; preserve strict-new sealing.
- `backend/app/services/dual_live_evaluator.py`
  - Retain the frozen public signature and own the Task-8-specific fixed check registry and read-only check functions.
  - No generic policy engine and no write-capable imports.
- `tools/dual_live_gate.py`
  - Retain pre-import network denial, load environment-only existing settings, acquire locks, open SQLite read-only, run evaluator, prove stability, and emit one verdict.
- `project6.ps1`
  - Replace the authorized run-action scaffold with the strict runner launcher while retaining no-argument shape and default refusal.

### Tests modified

- `backend/tests/test_dual_eval.py`
  - Runtime record, logger, counter, capture, evaluator, fake-campaign PASS, and single-axis adversarial cases.
- `backend/tests/test_campaign_log_capture.py`
  - Read-only verification and wrapper integration without weakening existing strict-new tests.
- `backend/tests/test_egress_transport.py`
  - Counter v1/v2 compatibility, sink, revocation, send-idle, and boot identity.
- `backend/tests/test_egress_arming.py`
  - NRC v1/v2 acceptance and mixed-identity rejection.
- `backend/tests/test_nrc_fresh.py`
  - Real arming-created strict NRC run reaches the public executor.
- `backend/tests/test_nrc_phase_b_linkage.py`
  - Real arming-created completed NRC run reaches the public Phase-B linkage.
- `tests/test_dual_gate.py`
  - Gate posture, read-only SQLite, stable reread, PowerShell run/validate behavior, fake Job/socket integration, and no-effect refusal.

### Final surface reconciliation (2026-08-02)

The map above was exhaustive for the production and test surfaces predicted by
this Task-8 plan, not an exhaustive repository manifest. Mechanical comparison
of base `6aa98ecafb7ce3fddfc37e1e859b2ef7c8e77e50` with reviewed completion HEAD
`dbb87740d418a34bc519a54c9befbca83a53d1ff` (tree
`1543524230e78dacb62c81de4dc0b9f81f85825a`) confirms that all 20 predicted
files landed. The final non-document implementation surface contains 38 files:
the 20 predicted files plus these 18 implementation-emergent files:

- `backend/app/services/connector_egress_evidence.py`
- `backend/app/services/dual_live_dependencies.py`
- `backend/app/services/layer3_connector_source_intake.py`
- `backend/app/services/layer3_execution_output.py`
- `backend/app/services/layer3_gate_b_state.py`
- `backend/app/services/layer3_origin_continuity.py`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_typing_entry.py`
- `backend/app/services/layer3_workbench.py`
- `config/support_matrix.yaml`
- `backend/tests/test_dual_eval_acceptance.py`
- `backend/tests/test_dual_live_dependencies.py`
- `backend/tests/test_egress_auth.py`
- `backend/tests/test_layer3_connector_vertical_loop.py`
- `backend/tests/test_layer3_execution_output.py`
- `backend/tests/test_layer3_intake_successor.py`
- `backend/tests/test_layer3_origin.py`
- `backend/tests/test_layer3_qual_aps_execution.py`

These additions are reconciled as Task-8 production/test/support surfaces, not
as permission for future edits and not as a claim that unrelated repository
files belong to Task 8. Five documentation files in the same historical range
remain intentionally outside the production/test map. In particular,
`backend/tests/test_egress_auth.py`, already named by Tasks 5 and 7 below, is
now also represented in the top-level reconciled map.

## Stable Interfaces

```text
dual_live_runtime.RuntimeIdentity(
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
    code_revision: str,
    wrapper_image_sha256: str,
    interpreter_image_sha256: str,
    root_mutex_identity_sha256: str,
    campaign_mutex_identity_sha256: str,
)
dual_live_runtime.RuntimeRecordWriter.append(
    phase: str, event: str, process_boot_id: str | null,
    payload: Mapping[str, Any],
) -> dict[str, Any]
dual_live_runtime.read_runtime_records(app_log: bytes) -> ordered runtime records
dual_live_runtime.census_loggers(allowed_pipe_tokens: immutable set[str]) -> dict[str, Any]

dual_live_windows.ProofLocks(
    root_identity_sha256: str,
    campaign_identity_sha256: str,
)
dual_live_windows.acquire_proof_locks(
    evidence_root: Path,
    campaign_id: str,
    campaign_fingerprint: str,
    campaign_definition_sha256: str,
    wait_ms: int = 0,
) -> ProofLocks
dual_live_windows.JobChild(
    pid: int,
    process_creation_identity_sha256: str,
    process_boot_id: str,
)
dual_live_windows.JobChild.wait(timeout_seconds: float) -> int
dual_live_windows.JobChild.terminate_tree() -> None
dual_live_windows.create_child_in_job(
    argv: ordered sequence[str],
    environment: Mapping[str, str],
    inherited_handles: ordered sequence[int],
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
) -> JobChild
dual_live_windows.prove_child_quiescence(child: JobChild) -> dict[str, Any]

connector_egress_transport.ConnectorCounterRuntimeContext(
    runtime_instance_id: str,
    process_boot_id: str,
    append_frame: Callable[[bytes], None],
    revocation_is_set: Callable[[], bool],
    acquire_send_idle: Callable[[], None],
    release_send_idle: Callable[[], None],
)
connector_egress_transport.connector_counter_runtime(
    context: ConnectorCounterRuntimeContext,
) -> context manager

dual_live_evaluator.CheckResult(
    check_id: str,
    status: PASS | FAIL | INDETERMINATE,
    code: str,
    evidence: Mapping[str, Any],
)
dual_live_evaluator.EVALUATOR_CHECK_ORDER -> ordered immutable sequence of every A/R/L/D/C/F check ID below
dual_live_evaluator._run_dual_live_checks(
    db: Session,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    settings: Settings,
) -> ordered immutable sequence[CheckResult]

dual_live_gate.GATE_CHECK_ORDER -> (G01_GATE_REFUSAL_PRECONDITIONS, G02_GATE_NETWORK_DENIAL)
dual_live_gate.GateCheckResult(
    check_id: str,
    status: PASS | REFUSED,
    code: str,
)

dual_live_runtime.run_dual_live_campaign(
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> dict[str, Any]
dual_live_runtime.run_phase_child(
    phase: A | B,
    control_handle: int,
    app_handle: int,
    http_handle: int,
) -> int
```

## Named Check Registry and Frozen-Clause Coverage

Every A/R/L/D/C/F check below is an executable evaluator function, emits one `CheckResult`, and has at least one passing and one single-axis negative/adversarial test. A check may call an existing narrowly authoritative verifier; no umbrella result substitutes for the enumerated checks.

| Check ID | Frozen lines | Exact purpose | Positive test | Negative/adversarial test |
|---|---:|---|---|---|
| `A01_INPUT_IDENTITY` | 2327, 2408-2418 | Canonical UUID4 campaign ID and lowercase fingerprint | `test_a01_accepts_canonical_identity` | `test_a01_rejects_missing_or_noncanonical_identity` |
| `A02_INDEX_LINEAR_HEAD` | 2257-2261, 2304-2307, 2425-2429 | Rehash all index objects; one gap-free chain and unique maximal configured head | `test_a02_accepts_two_revision_linear_chain` | `test_a02_rejects_rollback_fork_gap_or_orphan` |
| `A03_ARCHIVE_EXACT` | 2253-2256, 2429-2432 | Strict protected definition/grant bytes, raw hashes, canonical fingerprints | `test_a03_rehashes_exact_archives` | `test_a03_rejects_changed_repointed_or_caller_selected_archive` |
| `A04_SLICE_CARDINALITY` | 2297-2303, 2474-2476 | Exact selected `1 definition + 2 grants + 1 capture` | `test_a04_accepts_exact_campaign_slice` | `test_a04_rejects_extra_missing_duplicate_or_cross_alias_ref` |
| `A05_SELECTED_UNION` | 2364-2377 | Exact two-campaign `2+4+2` union while retaining disjoint failed history | `test_a05_accepts_exact_selected_union_with_history` | `test_a05_rejects_partial_or_cross_campaign_union` |
| `A06_INTRODUCTION_PARITY` | 2257-2261, 2304-2309, 2379-2389 | Earliest complete-slice revision/digest equals arming, ledger, seal, and events | `test_a06_accepts_bound_introduction` | `test_a06_rejects_ancestor_or_wrong_introduction_binding` |
| `A07_MARKER_ONE_USE` | 2262-2263, 2430-2432 | Exact marker bytes/hash, deterministic run ID, nonce, `max_armings=1` | `test_a07_accepts_exact_markers` | `test_a07_rejects_marker_change_duplicate_or_wrong_run_id` |
| `A08_ORIGINAL_WINDOWS` | 2264-2265, 2391-2395, 2432-2434 | Every reservation/send inside original half-open campaign and grant windows | `test_a08_accepts_not_before_and_issued_at_boundaries` | `test_a08_rejects_expiry_equality_and_out_of_window_send` |
| `A09_CODE_CAMPAIGN_FINGERPRINTS` | 2266 | Code revision and campaign fingerprints agree across every domain | `test_a09_accepts_cross_domain_fingerprints` | `test_a09_rejects_one_domain_fingerprint_change` |
| `A10_PROOF_CLASS` | 2330-2331, 2462-2464 | Rederive each origin proof class from authoritative bytes and bindings; never accept a caller/stored projection | `test_a10_accepts_rederived_proof_classes` | `test_a10_rejects_copied_or_caller_selected_proof_class` |
| `R01_CAPTURE_MEMBERSHIP` | 2294-2296, 2350-2355, 2477-2480 | Exact four files plus manifest; no extra, missing, alias, reparse, or caller path | `test_r01_accepts_exact_four_stream_capture` | `test_r01_rejects_missing_extra_or_unsafe_member` |
| `R02_MANIFEST_FILE_HASHES` | 2310-2314, 2354-2356, 2477-2481 | Fresh byte counts/hashes and canonical file-set hash match manifest | `test_r02_accepts_fresh_stream_hashes` | `test_r02_rejects_log_plus_manifest_rewrite` |
| `R03_SEAL_PARITY` | 2310-2314, 2355-2357, 2478-2484 | Strict-new seal raw hash binds manifest, file set, campaign, index, and run set | `test_r03_accepts_exact_seal` | `test_r03_rejects_logs_manifest_and_seal_rewrite` |
| `R04_SEAL_EVENT_PARITY` | 2257-2259, 2310-2314, 2356-2362, 2479-2485 | One deterministic matching seal event per extant run and no fabricated run | `test_r04_accepts_two_run_and_nrc_only_event_sets` | `test_r04_rejects_any_extant_run_db_event_rewrite` |
| `R05_RUNTIME_CHAIN` | 2519-2523, 2532-2536 | Gap-free wrapper record ordinals/hash chain and exact phase sequence | `test_r05_accepts_exact_runtime_record_sequence` | `test_r05_rejects_gap_reorder_duplicate_or_child_reserved_record` |
| `R06_STARTUP_LOGGER_CENSUS` | 2315-2317, 2525-2527 | Pre-activity root/application/HTTP census admits only pipe handlers and wrapper streams | `test_r06_accepts_exact_pipe_logger_topology` | `test_r06_rejects_file_queue_socket_eventlog_or_unknown_handler` |
| `R07_EXIT_LOGGER_CENSUS` | 2315-2317, 2550-2552 | Exit topology exactly equals protected startup topology | `test_r07_accepts_unchanged_exit_census` | `test_r07_rejects_late_handler_or_topology_change` |
| `R08_PHASE_A_IDENTITY` | 2453-2457, 2525-2531 | One recorded acquisition process/boot and acquisition-only role | `test_r08_accepts_one_phase_a_boot` | `test_r08_rejects_multiple_or_ambiguous_boots` |
| `R09_PHASE_A_JOB_ZERO` | 2530-2536, 2866-2871 | Job active count zero and no surviving child-tree process | `test_r09_job_kills_nested_fake_child_and_records_zero` | `test_r09_surviving_or_ambiguous_process_blocks_phase_b` |
| `R10_PHASE_A_SOCKET_QUIESCENCE` | 2532-2536, 2867-2871 | Stable owner-PID TCP/UDP census has no prohibited endpoint | `test_r10_allows_zero_and_time_wait_only` | `test_r10_loopback_listener_or_established_socket_blocks_phase_b` |
| `R11_AUTHORITY_CLEARED` | 2530-2531, 2538-2540, 2867-2872 | Key, grants, definition, and live-egress authority absent before B | `test_r11_phase_b_environment_is_secret_free` | `test_r11_any_authority_value_blocks_phase_b` |
| `R12_PHASE_B_GUARDS` | 2538-2549, 2576-2580 | Pre-import socket/DNS/Requests/connector/subprocess denial, no enable edge | `test_r12_phase_b_denies_every_guarded_route` | `test_r12_guard_replacement_or_enable_attempt_fails` |
| `R13_PHASE_B_JOB_ZERO` | 2550-2551, 2878-2879 | Phase-B Job/process/socket quiescence before sealing | `test_r13_phase_b_quiesces_before_seal` | `test_r13_phase_b_survivor_prevents_seal` |
| `R14_RUNTIME_TERMINAL` | 2519-2523 | Runtime complete record agrees with the exact sequential two-phase record sequence and capture times | `test_r14_accepts_complete_two_phase_runtime` | `test_r14_rejects_missing_or_contradictory_terminal_record` |
| `R15_WRAPPER_NETWORK_INERT` | 2519-2523 | Wrapper owns records, streams, locks, and child lifecycle but has no connector/network send path | `test_r15_accepts_network_inert_wrapper` | `test_r15_rejects_wrapper_socket_or_connector_access` |
| `R16_PHASE_A_RAW_ONLY` | 2528-2531 | Phase A can arm and acquire raw bytes but cannot execute Layer 3, review, package, submit, handoff, or seal | `test_r16_accepts_acquisition_only_phase_a` | `test_r16_rejects_any_downstream_phase_a_action` |
| `R17_PHASE_B_STRICT_FLOW` | 2538-2549 | Phase B consumes captured raw inputs only and executes the required downstream order under denial guards | `test_r17_accepts_strict_offline_downstream_order` | `test_r17_rejects_reorder_live_fetch_or_missing_downstream_step` |
| `R18_PHASE_A_TERMINAL_ONCE` | 2860-2866 | ScienceBase derived arming precedes its artifact/redirect; both raw sets are content-addressed and each executor commits exactly one strict terminal transition before the child exits unparsed | `test_r18_accepts_ordered_once_finalized_raw_acquisition` | `test_r18_rejects_late_arming_unbound_raw_or_repeated_terminalization` |
| `R19_A_TO_B_ORDER` | 2530-2542, 2866-2877 | Tree/session/authority teardown and recorded process/socket quiescence strictly precede creation/import/work in B | `test_r19_accepts_quiescence_before_phase_b_creation` | `test_r19_rejects_any_phase_b_creation_or_import_before_quiescence` |
| `R20_FOUR_STREAM_CLOSEOUT` | 2550-2554, 2878-2880 | On success or failure, stop runtime, flush/close exact four streams, reject extras, rehash, and atomically create manifest then no-overwrite seal | `test_r20_accepts_exact_ordered_four_stream_closeout` | `test_r20_rejects_extra_open_unflushed_reordered_or_overwritten_closeout` |
| `R21_EXTANT_RUN_SEAL_EVENTS` | 2555-2560, 2880-2884 | One transaction appends one matching deterministic event per extant run; NRC-first has exactly one and creates no ScienceBase run | `test_r21_accepts_success_and_nrc_first_event_cardinality` | `test_r21_rejects_missing_duplicate_fabricated_or_overwritten_event` |
| `R22_CAPTURE_START_CONTRACT` | 2519-2523 | Resolve the protected capture contract, require the directory absent, create exclusively in UTF-8, and route both sequential phases through the same four wrapper-owned streams | `test_r22_accepts_exclusive_utf8_shared_stream_start` | `test_r22_rejects_existing_directory_wrong_encoding_or_changed_stream_set` |
| `L01_RUN_CARDINALITY` | 2325-2331 | Exactly NRC and ScienceBase extant for PASS; NRC-only is a demonstrated campaign failure | `test_l01_accepts_exact_two_connector_rows` | `test_l01_rejects_zero_one_extra_or_fixture_run` |
| `L02_TERMINAL_EVENT` | 2275-2279, 2332-2336 | Exactly one deterministic strict terminal event, completed status/time, expired lease | `test_l02_accepts_one_completed_terminal_per_run` | `test_l02_rejects_nonterminal_duplicate_failure_cancel_or_live_lease` |
| `L03_POST_TERMINAL_EXTINCTION` | 2275-2279, 2333-2336 | No later failure, cancellation, cancelling, or lease reacquisition evidence | `test_l03_accepts_clean_terminal_tail` | `test_l03_rejects_post_terminal_contradiction` |
| `L04_LEDGER_RECONSTRUCTION` | 2267-2268, 2433-2440 | Independently reconstruct terminal ledgers, hashes, ordering, reservation/completion parity | `test_l04_accepts_rederived_ledgers` | `test_l04_rejects_missing_duplicate_reordered_or_changed_event` |
| `L05_COUNTER_BIJECTION` | 2441-2446, 2457-2459 | Entire sealed `http.jsonl` is exact counter-v2 and bijects to both ledgers | `test_l05_accepts_exact_counter_ledger_union` | `test_l05_rejects_missing_extra_foreign_or_disagreeing_counter` |
| `L06_COUNTER_BOOT` | 2453-2457 | One runtime and process boot; v1 or mixed identity cannot PASS | `test_l06_accepts_single_v2_boot` | `test_l06_classifies_v1_mixed_or_multiboot_indeterminate` |
| `L07_BYTE_ALLOWANCE` | 2269-2274, 2445-2453 | Rederive counted bytes and the single-send allowance/terminal classification | `test_l07_accepts_within_ceiling_and_correct_allowed_crossing` | `test_l07_rejects_wrong_class_and_indetermines_excess_over_allowance` |
| `L08_REQUEST_CADENCE` | 2453-2459 | Same-bucket monotonic starts meet `min_request_interval_ms` in one boot | `test_l08_accepts_exact_interval_boundary` | `test_l08_rejects_short_interval_and_indetermines_boot_ambiguity` |
| `L09_TRANSPORT_POLICY` | 2280, 2433-2445 | Host, method, path, query, redirect, and credential audience comply | `test_l09_accepts_exact_request_rules` | `test_l09_rejects_each_host_method_path_query_or_credential_axis` |
| `L10_FRESH_200_BYTES` | 2281, 2441-2447 | Fresh 200 counter evidence, decoded bytes/hash, and admitted raw bytes agree | `test_l10_accepts_exact_fresh_200_bytes` | `test_l10_rejects_status_count_or_body_hash_change` |
| `L11_NRC_FIRST_BINDING` | 2437-2440, 2842-2856 | ScienceBase arming binds independently rederived NRC run and terminal hash | `test_l11_accepts_nrc_first_parent_binding` | `test_l11_rejects_changed_parent_run_or_terminal_hash` |
| `L12_RESERVATION_RESOLUTION` | 2332-2336 | No pending/unknown reservation, ambiguous completion, or unresolved egress event remains | `test_l12_accepts_fully_resolved_reservations` | `test_l12_rejects_pending_unknown_or_ambiguous_reservation` |
| `D01_ORIGIN_RECEIPT` | 2282, 2434-2436 | Recompute the single canonical origin receipt; never trust stored proof class/hash | `test_d01_accepts_rederived_origin_receipts` | `test_d01_rejects_copied_proof_class_or_changed_receipt` |
| `D02_RAW_PROVENANCE_LINKAGE` | 2282, 2434-2436 | Raw blob, provenance, version, target, and content linkage are equal | `test_d02_accepts_exact_raw_linkage` | `test_d02_rejects_one_byte_or_one_binding_change` |
| `D03_LAYER3_EXECUTION` | 2283, 2546-2549 | Both connector sources reached the required Layer 3 execution results | `test_d03_accepts_both_layer3_results` | `test_d03_rejects_missing_or_foreign_execution_result` |
| `D04_REVIEW_RESULT` | 2283, 2546-2549 | Review result binds the rederived origin and artifact set | `test_d04_accepts_bound_review` | `test_d04_rejects_changed_origin_or_artifact_review_binding` |
| `D05_PACKAGE_SET` | 2284, 2328, 2546-2549 | Exactly canonical-internal, user-facing, and review-facing packages | `test_d05_accepts_exact_three_package_kinds` | `test_d05_rejects_missing_extra_or_duplicate_kind` |
| `D06_PACKAGE_PAYLOAD` | 2284, 2435-2436 | Rehash each exact package payload and compare its stored projection | `test_d06_accepts_exact_package_payload_bytes` | `test_d06_rejects_payload_byte_or_hash_change` |
| `D07_SUBMIT_RECEIPT` | 2285, 2337, 2546-2549 | Submit receipt exists and binds origin/artifact/package hashes | `test_d07_accepts_bound_submit_receipt` | `test_d07_rejects_missing_or_changed_submit_receipt` |
| `D08_HANDOFF_RECEIPT` | 2285, 2337, 2546-2549 | Prepared/internal handoff receipt exists with no delivery claim | `test_d08_accepts_prepared_internal_handoff` | `test_d08_rejects_missing_changed_or_delivery_claiming_handoff` |
| `C01_STRICT_NULLS` | 2287-2288, 2466-2472 | Strict download-URI and alias URL scalar fields are null | `test_c01_accepts_null_strict_url_scalars` | `test_c01_rejects_nonnull_download_or_alias_url` |
| `C02_DB_SCALAR_JSON_SCAN` | 2289-2293, 2341-2348 | Scan every campaign-related scalar/text/JSON column | `test_c02_accepts_clean_mapped_database_columns` | `test_c02_finds_raw_escaped_encoded_fragment_header_and_duplicate_receipt` |
| `C03_NON_SOURCE_FILE_SCAN` | 2289-2293, 2344-2348, 2466-2472 | Scan all bounded non-source snapshot/storage/report/generated files | `test_c03_accepts_clean_non_source_roots` | `test_c03_rejects_forbidden_material_in_each_file_class` |
| `C04_SERIALIZATION_EVENT_SCAN` | 2289-2293 | Scan API serializations, events, reports, and generated artifacts | `test_c04_accepts_clean_serializations_and_events` | `test_c04_rejects_forbidden_material_in_each_projection_class` |
| `C05_RUNTIME_LOG_SCAN` | 2291-2293, 2350-2353, 2466-2470 | Strict UTF-8/JSONL scan of the sealed four-stream capture | `test_c05_accepts_clean_sealed_capture` | `test_c05_rejects_raw_json_percent_and_embedded_log_forms` |
| `C06_BOUNDED_DECODERS` | 2487-2503 | Raw, JSON, HTML, percent-once/twice transforms; third layer/invalid encoding fails | `test_c06_accepts_bounded_decoder_forms` | `test_c06_rejects_third_escape_layer_invalid_encoding_and_cap_overrun` |
| `C07_SOURCE_EXEMPTION` | 2345-2348, 2471-2472 | Exempt only exact admitted raw source refs whose rehashed bytes equal receipts | `test_c07_accepts_two_exact_raw_source_exemptions` | `test_c07_rejects_wrong_ref_hash_or_extra_source_exemption` |
| `C08_SECRET_SCAN` | 2339, 2492-2503, 2573-2574 | In-memory NRC key scan returns only sink identity and hit digest | `test_c08_accepts_clean_fake_key_scan` | `test_c08_detects_fake_key_without_echoing_it` |
| `F01_EVIDENCE_STABILITY` | 2420-2423, 2509-2512 | Final locked reread matches all protected file identities, bytes, and membership | `test_f01_accepts_unchanged_evidence_reread` | `test_f01_indetermines_file_or_membership_drift` |
| `F02_DATABASE_STABILITY` | 2420-2423 | Fresh second semantic DB snapshot and mechanical DB-file fingerprint are unchanged | `test_f02_accepts_unchanged_read_only_database` | `test_f02_indetermines_concurrent_row_or_file_drift` |
| `F03_NONCLAIMS_REPORT` | 2323, 2505-2507 | Fixed secret-safe report and explicit local-experiment nonclaims | `test_f03_emits_exact_ordered_nonclaims` | `test_f03_rejects_report_contract_or_positive_claim_drift` |
| `F04_READ_ONLY_EVALUATION` | 2420-2423 | Evaluator and gate perform no write, seed, migration, generation, or mutable-VFS action | `test_f04_evaluation_leaves_all_protected_state_unchanged` | `test_f04_refuses_any_write_capable_adapter_or_connection` |
| `F05_PROJECTION_REDERIVATION` | 2462-2464 | Stored hashes, proof classes, status projections, and caller summaries are never accepted without independent derivation | `test_f05_accepts_only_rederived_projections` | `test_f05_rejects_trusted_stored_projection` |
| `F06_NO_EGRESS_DEPENDENCY` | 2509-2512 | Evaluator has no connector, resolver, arming, transport, caller-path, or network dependency | `test_f06_accepts_offline_dependency_graph` | `test_f06_rejects_connector_resolver_arming_transport_or_socket_dependency` |
| `F07_PUBLIC_API_CONTRACT` | 2408-2418 | Public evaluator signature remains exact and admits no caller-selected evidence path or mutable runtime input | `test_f07_accepts_exact_public_signature` | `test_f07_rejects_added_evidence_path_or_runtime_selector` |
| `F08_RESULT_AGGREGATION` | 2325-2339 | Deterministically aggregate named evaluator results so only two complete connector rows with every A/R/L/D/C/F check PASS produce PASS | `test_f08_accepts_only_complete_two_connector_pass` | `test_f08_rejects_each_nonpass_precedence_and_status_projection` |
| `F09_CONNECTOR_AND_COMBINED_REPORTS` | 2249-2250 | Emit independently derived NRC, ScienceBase, and combined-campaign results without treating the combined projection as connector evidence | `test_f09_accepts_independent_connector_and_combined_results` | `test_f09_rejects_missing_copied_or_disagreeing_result_domain` |

### Gate Precondition Registry

Gate checks execute in fixed `GATE_CHECK_ORDER` before evaluator import/entry. Each emits a gate-local `GateCheckResult` and has a passing and a single-axis negative/adversarial test. A failed gate check emits the refusal schema and the evaluator never starts; successful gate checks remain gate-local control-flow facts and never masquerade as evaluator evidence.

| Check ID | Frozen lines | Exact purpose | Positive test | Negative/adversarial test |
|---|---:|---|---|---|
| `G01_GATE_REFUSAL_PRECONDITIONS` | 2318-2320 | Refuse before evaluator entry when egress/authority/runtime is active or the selected capture is unsealed | `test_g01_accepts_only_inert_sealed_gate_input` | `test_g01_refuses_each_active_or_unsealed_precondition_without_effect` |
| `G02_GATE_NETWORK_DENIAL` | 2320-2322 | Install pre-import raw-socket, DNS, Requests, and connector-transport denial and prove zero attempted call reaches an implementation | `test_g02_accepts_guarded_offline_evaluation` | `test_g02_blocks_each_network_route_before_evaluator_import` |

## Fixed Result and Gate Contract

Evaluation result order is exact:

```text
schema_id
campaign_id
expected_campaign_fingerprint
status
fresh_live
evaluation_complete
code
checks
nonclaims
```

Decision precedence is deterministic:

1. Gate precondition cannot be established safely: emit `project6.dual_live_gate_refusal.v1`, `REFUSED`, exit 2; evaluator does not start.
2. Any required domain is missing, unreadable, unparseable, inconsistent, unstable, capped, or boot-ambiguous: evaluation `INDETERMINATE`, exit 2.
3. Otherwise, any complete evidence proves a policy/outcome violation: evaluation `FAIL`, exit 1.
4. Otherwise every A/R/L/D/C/F check is PASS for both completed connector runs: evaluation `PASS`, `fresh_live=true`, exit 0.

The three frozen coordinated-rewrite cases are not a new check family. They are mandatory cross-domain adversaries:

- logs + manifest rewrite fails `R02` or `R03/R04` parity;
- logs + manifest + seal rewrite fails `R04` DB-event parity;
- any extant-run DB event rewrite fails `R04`, `L02`, or `L04` parity.

The implementation does not claim detection of a coherent rewrite of every filesystem and DB domain; that class is outside the frozen local-experiment threat model.

The gate selects its database, storage root, evidence root, evidence index,
index SHA-256, and evidence-key locations from its process environment. Those
configured locations are trusted selection inputs. The evaluator proves the
internal consistency and content-hash bindings of the selected bundle; it does
not independently authenticate that the environment selected the intended
root. Forging PASS therefore requires a fully coherent bundle that also hashes
to the configured index SHA-256, which is the intended local-experiment proof
burden. If the threat model expands beyond trusted local operator selection,
an owner-signed pinned location manifest is a separate future authority change,
not an implied part of this implementation.

An unsealed capture detected by the gate before evaluator entry is `REFUSED`. A selected protected capture that becomes missing, unreadable, or mismatched after evaluator entry is `INDETERMINATE`. A within-allowance byte crossing with the correct oversized/budget terminal classification passes `L07_BYTE_ALLOWANCE` as an accounting check, but the non-completed connector outcome still makes the combined campaign `FAIL`.

Only Task-11 lines 2860-2884 are used here as a reinforcing producer-order contract. Owner approval, deployed-commit identity, live key presence, operator allowance acknowledgement, real acquisition, campaign-close head advancement, independent live review, and every other Task-11 live ceremony remain outside this offline build and cannot be represented as pytest PASS authority.

---

## Task 1: Freeze the A-Scoped Surface and Baseline

**Files:**
- Modify: `backend/tests/test_dual_eval.py`
- Modify: `tests/test_dual_gate.py`
- Test: `backend/tests/test_dual_eval.py`
- Test: `tests/test_dual_gate.py`

**Interfaces:**
- Consumes: adjudication constraints and current scaffold behavior.
- Produces: executable source-surface guards that later tasks cannot accidentally widen.

- [ ] **Step 1: Write the failing surface-closure tests**

Add tests that inspect the changed production surface and assert:

```python
FORBIDDEN_REQUIRED_ALIASES = (
    "DUAL_LIVE_POSTRUN",
    "DUAL_LIVE_ATTESTATION",
    "DUAL_LIVE_ISSUER",
)
FORBIDDEN_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_postrun_evidence.py",
    "tools/dual_live_issue.py",
)
ALLOWED_NEW_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
    "backend/app/services/dual_live_windows.py",
    "tools/dual_live_run.py",
)
FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
)

def test_a_scoped_build_adds_no_attestation_index_or_env_contract() -> None:
    tracked = _tracked_source_text()
    assert all(alias not in tracked for alias in FORBIDDEN_REQUIRED_ALIASES)
    assert all(not (ROOT / path).exists() for path in FORBIDDEN_PRODUCTION_PATHS)

def test_frozen_and_sealed_authority_files_are_unchanged() -> None:
    assert _git_blob_sha(FROZEN_PLAN) == EXPECTED_FROZEN_PLAN_BLOB
    assert _pilot_seal() == "b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2"

def test_a_scoped_build_has_required_runtime_units() -> None:
    assert all((ROOT / path).is_file() for path in FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS)
```

- [ ] **Step 2: Run the tests and verify the implementation-surface assertion fails only because the new allowed file list is not present yet**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py -q
Pop-Location
python -m pytest tests/test_dual_gate.py -q
```

Expected: current scaffold tests pass; the new forward-looking surface test fails because the first-tranche runtime unit is absent, not because of a frozen hash or seal mismatch.

- [ ] **Step 3: Record the exact allowed production file set in the tests**

`ALLOWED_NEW_PRODUCTION_PATHS` is the new-unit subset of the production file map in this plan; the complete changed-production allowlist also contains the narrowly modified existing units listed above. It excludes the plan itself, tests, and already committed docs. Do not assert an exhaustive repository manifest; assert only that Task-8 production changes are a subset of the enumerated A-scoped files and contain none of the forbidden aliases/paths. Later tasks prove their new unit first by import-level RED tests rather than keeping this completed tranche intentionally red.

- [ ] **Step 4: Re-run the two files and preserve the expected pre-implementation failure evidence**

Expected: one deliberate forward-looking failure remains; all existing assertions stay green.

- [ ] **Step 5: Commit after the first implementation tranche makes the surface test green**

Commit with the tranche that first creates the allowed runtime files; do not make a test-only commit that leaves the branch intentionally red.

## Task 2: Runtime Records, Pipe Frames, and Logger Census

**Files:**
- Create: `backend/app/services/dual_live_runtime.py`
- Modify: `backend/tests/test_dual_eval.py`
- Test: `backend/tests/test_dual_eval.py`

**Interfaces:**
- Consumes: `ConnectorCampaignLogWriter.write`, canonical JSON rules from `connector_egress_authorization.canonical_json_bytes`.
- Produces: `RuntimeIdentity`, `RuntimeRecordWriter`, `read_runtime_records`, `encode_pipe_frame`, `read_pipe_frame`, `census_loggers`, and `freeze_logger_topology`.

- [ ] **Step 1: Write failing canonical-chain and framing tests**

Cover exact keys, canonical UUID/hash types, ordinal 1 with null predecessor, later predecessor linkage, reserved-event union, 64 KiB frame equality, 64 KiB+1 refusal, invalid UTF-8, partial frame, unexpected EOF, child-selected reserved schema, and aggregate pump cap.

```python
def test_r05_runtime_records_form_exact_canonical_hash_chain() -> None:
    sink = MemorySink()
    writer = RuntimeRecordWriter(sink.write, identity=RUNTIME_IDENTITY)
    first = writer.append(phase="wrapper", event="runtime_start", process_boot_id=None,
                          payload=RUNTIME_START_PAYLOAD)
    second = writer.append(phase="A", event="phase_child_start",
                           process_boot_id=BOOT_ID, payload=CHILD_START_PAYLOAD)
    assert first["ordinal"] == 1
    assert second["previous_record_sha256"] == first["record_sha256"]
    assert read_runtime_records(sink.bytes()) == (first, second)
```

- [ ] **Step 2: Run the named runtime tests and observe import failure**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py -q -k "r05 or r06 or r07"
Pop-Location
```

Expected: FAIL because `dual_live_runtime` does not exist.

- [ ] **Step 3: Implement strict canonical records and bounded frames**

Use the exact envelope:

```python
RUNTIME_RECORD_KEYS = (
    "schema_id", "ordinal", "runtime_instance_id", "phase", "event",
    "process_boot_id", "previous_record_sha256", "payload", "record_sha256",
)
RUNTIME_SCHEMA_ID = "project6.dual_live_runtime_record.v1"
MAX_FRAME_BYTES = 64 * 1024

def _record_hash(record: Mapping[str, Any]) -> str:
    preimage = {key: value for key, value in record.items() if key != "record_sha256"}
    return hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()
```

The event union is closed: `runtime_start`, `phase_child_start`, `logger_census`, `phase_go`, `stop_latched`, `socket_census`, `job_zero`, `authority_cleared`, `phase_complete`, `runtime_complete`. Validate payload keys per event and reject all secret, URL, query, header-value, command-line, endpoint, and raw-path fields.

- [ ] **Step 4: Write failing logger-topology tests**

Test root logger, every real logger and placeholder, propagation, disabled/effective levels, filters, `logging.lastResort`, duplicate effective sinks, and exact handler destinations. Positives allow only pipe handlers and sinkless exact `NullHandler`; negatives add `FileHandler`, unknown `StreamHandler`, `QueueHandler`, `MemoryHandler`, `SocketHandler`, `HTTPHandler`, `SMTPHandler`, `NTEventLogHandler`, arbitrary subclass, duplicate pipe sink, late handler, and changed filter.

- [ ] **Step 5: Implement census after complete imports and before GO**

`census_loggers` returns a strict secret-safe projection plus `topology_sha256`; `freeze_logger_topology` wraps normal handler mutation APIs and returns a final recheck callback. It does not claim protection from direct list mutation; the exit census detects it.

- [ ] **Step 6: Run the focused tests**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py -q -k "r05 or r06 or r07"
Pop-Location
```

Expected: all selected tests pass.

- [ ] **Step 7: Run formatting and integrity checks**

Run:

```powershell
Push-Location backend
python -m ruff check app/services/dual_live_runtime.py tests/test_dual_eval.py
Pop-Location
git diff --check
```

Expected: exit 0.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/dual_live_runtime.py backend/tests/test_dual_eval.py tests/test_dual_gate.py
git commit -m "feat(proof): define sealed dual-live runtime evidence"
```

## Task 3: Windows Locks, Atomic Job Admission, and Quiescence

**Files:**
- Create: `backend/app/services/dual_live_windows.py`
- Modify: `tests/test_dual_gate.py`
- Test: `tests/test_dual_gate.py`

**Interfaces:**
- Consumes: existing evidence-root path and campaign identity; no new environment keys.
- Produces: `ProofLocks`, `acquire_proof_locks`, `JobChild`, `create_child_in_job`, and `prove_child_quiescence`.

- [ ] **Step 1: Write failing root/campaign lock tests**

Tests cover root-before-campaign acquisition, reverse release, same-campaign contention, different-campaign root contention, abandoned mutex, current-SID plus SYSTEM DACL, ACL mismatch, namespace squatting, reparse evidence root, non-inheritable handles, and acquisition before any index/capture/DB read.

```python
def test_proof_locks_are_root_then_campaign_and_busy_refuses(tmp_path: Path) -> None:
    with acquire_proof_locks(evidence_root=tmp_path, campaign_id=CAMPAIGN_ID,
                             campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                             campaign_definition_sha256=DEFINITION_SHA):
        with pytest.raises(DualLiveWindowsError, match="dual_live_lock_busy"):
            acquire_proof_locks(evidence_root=tmp_path, campaign_id=CAMPAIGN_ID,
                                campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                                campaign_definition_sha256=DEFINITION_SHA)
```

- [ ] **Step 2: Write failing atomic Job tests**

Use isolated fake child scripts and loopback-only fixtures. Cover Windows version/API absence, nested-Job incompatibility, Job policy readback mismatch, exact inherited handles, no inherited Job handle, normal exit, nonzero exit, timeout, abrupt wrapper close, sleeping grandchild, process identity ambiguity, and Job PID-list truncation/retry.

- [ ] **Step 3: Run the Windows slice and observe import failure**

Run: `python -m pytest tests/test_dual_gate.py -q -k "proof_lock or job or quiescence or socket"`

Expected: FAIL because `dual_live_windows` does not exist.

- [ ] **Step 4: Implement exact private-namespace locks**

Open a non-reparse root directory handle, derive volume serial + file ID + normalized final path + security descriptor hash, build a current-user-SID boundary descriptor, create/open a private namespace, and create root/campaign mutexes with an explicit DACL for the current SID and SYSTEM. `WAIT_TIMEOUT` is busy; `WAIT_ABANDONED`, access failure, or descriptor mismatch is refusal.

- [ ] **Step 5: Implement atomic CreateProcessW Job admission**

Use `STARTUPINFOEX` with both `PROC_THREAD_ATTRIBUTE_JOB_LIST` and exact `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`. Set and read back `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; require both breakaway flags absent. Create an explicit sorted, case-insensitive-unique, double-NUL Unicode environment block. There is no suspended-create/late-assign fallback.

- [ ] **Step 6: Implement retained-identity process and socket census**

Retain process handles and creation `FILETIME`; bind every PID to creation identity. Resize and retry `JobObjectBasicProcessIdList` until untruncated. Take two stable full owner-PID TCP4/TCP6/UDP4/UDP6 samples. Allow attributable TCP `TIME_WAIT` only; any other TCP state or UDP row fails. PID reuse, inaccessible owner, API/buffer churn, or unequal samples is `INDETERMINATE`. Runtime records expose counts and one-way identity hashes, never addresses or ports.

- [ ] **Step 7: Run the Windows integration slice twice**

Run twice to detect leaked handles/processes:

```powershell
python -m pytest tests/test_dual_gate.py -q -k "proof_lock or job or quiescence or socket"
python -m pytest tests/test_dual_gate.py -q -k "proof_lock or job or quiescence or socket"
```

Expected: both exit 0; no surviving fixture child or listener.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/dual_live_windows.py tests/test_dual_gate.py
git commit -m "feat(proof): contain dual-live child processes on Windows"
```

## Task 4: Counter-v2, Wrapper Pipe Sink, and Physical-Send Revocation

**Files:**
- Modify: `backend/app/services/connector_egress_transport.py`
- Modify: `backend/app/services/connector_egress_arming.py`
- Modify: `backend/tests/test_egress_transport.py`
- Modify: `backend/tests/test_egress_arming.py`

**Interfaces:**
- Consumes: `ConnectorCounterRuntimeContext` installed by Phase-A bootstrap.
- Produces: exact v2 records and one serialized, revocable physical-send boundary while preserving v1 non-campaign compatibility.

- [ ] **Step 1: Write failing exact-v2 parser/emitter tests**

Test v1 historical read, v2 emit/read, exact key sets, canonical UUID/hash, singleton runtime/boot, v1-v2 mix, runtime mix, boot mix, missing/extra key, and a new dual-live evaluation refusing v1 as PASS evidence.

- [ ] **Step 2: Write failing sink and revocation tests**

Use a fake HTTP adapter only. Assert the process-global send lock serializes calls; revocation before reservation creates no reservation; revocation after reservation but before the physical boundary creates the existing reserved-not-sent terminal evidence; send-idle resets before and signals in `finally`; an in-flight send completes its counter/ledger evidence but cannot make an abnormal-stop campaign PASS.

- [ ] **Step 3: Run focused tests and observe v2 failures**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_egress_transport.py tests/test_egress_arming.py -q -k "counter or revocation or send_idle or boot"
Pop-Location
```

- [ ] **Step 4: Implement dual exact-key contracts**

```python
COUNTER_V2_EXTRA_KEYS = frozenset(("runtime_instance_id", "process_boot_id"))
COUNTER_V2_KEYS = COUNTER_V1_KEYS | COUNTER_V2_EXTRA_KEYS

def _counter_schema(record: Mapping[str, Any]) -> Literal["v1", "v2"]:
    if record.get("schema_id") == "project6.connector_http_counter.v1" and set(record) == COUNTER_V1_KEYS:
        return "v1"
    if record.get("schema_id") == "project6.connector_http_counter.v2" and set(record) == COUNTER_V2_KEYS:
        return "v2"
    raise CounterEvidenceError("connector_http_counter_schema_invalid")
```

Both transport and arming consumers use one shared parser; they do not maintain divergent key sets.

- [ ] **Step 5: Implement runtime context and pipe sink**

When a context is installed, `_counter_record` emits v2 and `append_frame` receives canonical bytes. No child receives `http.jsonl` path. Without context, the existing path-backed v1 behavior remains unchanged.

- [ ] **Step 6: Implement serialized revocation boundary**

Under one module-level send lock: check revocation before reservation, acquire/reset send-idle, perform the existing reservation, check revocation immediately before the adapter send, then release/signal send-idle in `finally`. Preserve existing terminal/ledger rules and do not claim cancellation of already in-flight OS I/O.

- [ ] **Step 7: Run full transport and arming files**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_egress_transport.py tests/test_egress_arming.py -q
Pop-Location
git diff --check
```

Expected: all pass, including historical v1 fixtures and clause-5 e2e cases.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/connector_egress_transport.py backend/app/services/connector_egress_arming.py backend/tests/test_egress_transport.py backend/tests/test_egress_arming.py
git commit -m "feat(egress): bind dual-live counters to one process boot"
```

## Task 4A: Code-Forced Task-5 Prerequisite Seams

This corrects the execution map, not the frozen plan. The owner-approved CLI wrapper cannot truthfully use private Job fields, load and later clear `.env`, fabricate a loopback `Request`, or rewrite a malformed NRC row in the runtime. These seams therefore land before controller integration.

**Files:**
- Modify: `backend/app/services/connectors_nrc_adams.py`
- Modify: `backend/app/services/nrc_aps_phase_b_linkage.py`
- Modify: `backend/app/services/connector_egress_authorization.py`
- Modify: `backend/app/services/dual_live_windows.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/tests/test_nrc_fresh.py`
- Modify: `backend/tests/test_nrc_phase_b_linkage.py`
- Modify: `backend/tests/test_egress_auth.py`
- Modify: `tests/test_dual_gate.py`

**Interfaces:**
- Produces: canonical NRC strict-run identity parity, immutable child-start evidence, isolated no-dotenv imports, and a narrowly bounded local-runner receipt.
- Preserves: request-bound proxy-owner authority, the normal non-isolated `.env` startup path, frozen ScienceBase raw-custody staging, and every existing default caller.

- [ ] **Step 1: Write failing NRC identity parity tests**

Create an NRC run through the real arming service. Prove the public executor and the public Phase-B binder accept that unchanged row. Reject an alternate source system without mutation or send.

- [ ] **Step 2: Write failing Job-evidence and isolated-config tests**

Prove the public projection exactly exposes the retained handle-bound creation identity, boot ID, executable SHA, and Job-policy SHA and cannot be mutated. In a real `python -I` subprocess with a temporary `.env`, prove `.env`-only key/grant authority is never loaded. Preserve ordinary non-isolated config behavior.

- [ ] **Step 3: Write failing local-runner authorization tests**

The runner entry derives its receipt from server-owned verified grant state plus an OS-derived local-user/workspace identity. It admits only `AUTH_OWNER=none`, local deployment, no trusted proxy, live egress enabled, exclusive proof mode, `operator_mode=local_loopback`, and write access. Proxy-owner, role/header emulation, caller-supplied hashes, nonlocal mode, or disabled/exclusive-false posture refuses. The receipt must revalidate through the existing arming receipt contract.

- [ ] **Step 4: Implement the narrow seams**

Use one shared canonical NRC source-system constant or exact literal in both executor and Phase-B guards. Add a frozen/read-only `JobStartEvidence` projection owned by `dual_live_windows`. At config module initialization use `_env_file=None` when `sys.flags.isolated` is true; do not add an environment switch. Factor receipt construction so the existing Request path and the new local-runner path share exact grant/campaign binding, while only the Request path can authorize `proxy_owner`.

- [ ] **Step 5: Run focused and full owner files**

```powershell
Push-Location backend
python -m pytest tests/test_nrc_fresh.py tests/test_nrc_phase_b_linkage.py tests/test_egress_auth.py -q
Pop-Location
python -m pytest tests/test_dual_gate.py -q -k "job_start or isolated or dotenv or runner_owner"
```

- [ ] **Step 6: Commit in narrow reviewed tranches**

Keep identity, runner authorization, and Windows/config seams independently reviewable when their file sets do not overlap.

## Task 5: Controller, Child Bootstrap, and Existing Capture Integration

**Files:**
- Modify: `backend/app/services/dual_live_runtime.py`
- Create: `tools/dual_live_run.py`
- Modify: `backend/app/services/connector_campaign_log_capture.py`
- Modify: `project6.ps1`
- Modify: `backend/tests/test_dual_eval.py`
- Modify: `backend/tests/test_campaign_log_capture.py`
- Modify: `tests/test_dual_gate.py`

**Interfaces:**
- Consumes: Tasks 2-4 runtime/Windows/counter contracts and existing begin/seal capture APIs.
- Produces: a default-refusing, two-phase, wrapper-owned-stream producer and sealed logger/quiescence records.

- [ ] **Step 1: Write failing default-refusal and no-effect tests**

For each missing existing requirement—campaign ID, fingerprint, evidence root/head path/head digest, database, storage, definition/grants/digests, exclusive proof mode, key, Windows support—assert exit 2, one secret-safe refusal, and no child, socket, marker, capture directory, DB row, or file effect. Include mixed-case environment aliases and `.env`-only authority to prove Phase B cannot reload them.

- [ ] **Step 2: Write failing fake-child controller tests**

Use isolated fake children with anonymous pipes only. Prove exact record order, wrapper-only writes, stdout/stderr pumping, app JSON frames, counter-only HTTP frames, one-use GO, Phase A tree/socket quiescence before B creation, authority-cleared record, Phase-B guard posture, stop latch, no B after A failure, final four-stream seal, and NRC-only one-event closeout.

- [ ] **Step 3: Run the controller slices and observe failures**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py tests/test_campaign_log_capture.py -q -k "runtime or wrapper or phase or logger or quiescence"
Pop-Location
python -m pytest tests/test_dual_gate.py -q -k "run_action or controller or phase"
```

- [ ] **Step 4: Implement strict CLI and environment blocks**

`tools/dual_live_run.py` accepts only `--campaign-id`, `--campaign-fingerprint`, and wrapper-owned internal child handle arguments. It adds no required public configuration. Invoke Python with `-I -B`. Every child uses an explicit case-insensitive environment allowlist and `Settings(_env_file=None)`; it never inherits parent variables implicitly.

- [ ] **Step 5: Implement wrapper-owned pumps and one-use phase control**

The controller owns all four `ConnectorCampaignLogWriter` objects. Four bounded pump threads write app, HTTP, stdout, and stderr frames; the app and HTTP pumps validate their formats before disk writes. A child blocks after logger census until the wrapper validates and seals the census record, then consumes exactly one nonce-bound GO. Duplicate, early, malformed, or late GO latches stop.

- [ ] **Step 6: Implement Phase-A and Phase-B child boundaries**

Phase A installs reversible accidental-call guards, configures pipe logging, performs the census, waits for GO, installs `ConnectorCounterRuntimeContext`, and calls only strict arming/raw-acquisition services. It retains the frozen ScienceBase safety-shape validation and raw-custody `Dataset`/raw `DatasetVersion`/provenance/inert-intake staging required by the original Task 4; that is not Phase-B semantic ingestion. It must not call NRC artifact parsing, origin-receipt minting, material preview, Gate B/C, Layer 3 analysis/execution, review, package, submit, or handoff paths. Phase B installs permanent socket/DNS/Requests/connector and subprocess guards before service imports, has no key/current-definition/current-grant variables, retains only the protected historical evidence index inputs, calls `parse_admitted_blob_strict` for NRC, mints the existing ScienceBase intake row's origin receipt rather than a second intake row, and then invokes the existing downstream workflow services.

- [ ] **Step 7: Implement stop/quiescence/seal ordering**

On every stop: set revocation, wait send-idle, terminate the active Job once, wait retained handles, prove Job/process/socket quiescence, clear authority posture, persist wrapper records, and only then allow B. After B: repeat quiescence, close/flush pumps and handlers, close all four writers cleanly, and call the existing strict-new manifest/seal/event transaction. Never rewrite the preflight index or repair partial publication.

- [ ] **Step 8: Replace the PowerShell run scaffold narrowly**

The action retains no `ActionArgs`, validates the two existing ID variables, then launches:

```powershell
& py "-$PythonVersion" -I -B .\tools\dual_live_run.py --campaign-id $env:DUAL_LIVE_CAMPAIGN_ID --campaign-fingerprint $env:DUAL_LIVE_CAMPAIGN_FINGERPRINT
```

The Python runner performs all remaining validation and refuses before effects when authority is absent. The PowerShell wrapper does not print, serialize, or transform credentials.

- [ ] **Step 9: Run focused producer/capture tests**

Expected: all fake-child and capture cases pass; no external network call occurs.

- [ ] **Step 10: Commit**

```powershell
git add backend/app/services/dual_live_runtime.py tools/dual_live_run.py backend/app/services/connector_campaign_log_capture.py project6.ps1 backend/tests/test_dual_eval.py backend/tests/test_campaign_log_capture.py tests/test_dual_gate.py
git commit -m "feat(proof): produce sealed dual-live quiescence evidence"
```

## Task 6: Explicit-Settings Evidence and Read-Only Capture Adapters

**Files:**
- Modify: `backend/app/services/connector_egress_authorization.py`
- Modify: `backend/app/services/connector_campaign_log_capture.py`
- Modify: `backend/tests/test_egress_auth.py`
- Modify: `backend/tests/test_campaign_log_capture.py`

**Interfaces:**
- Consumes: existing `VerifiedEvidenceIndexChain`, archived definition/grant readers, capture schemas, and seal-event metrics.
- Produces: explicit-settings read-only adapters usable without global `.env` state or current send authority.

- [ ] **Step 1: Write failing explicit-settings authority tests**

Prove the adapter loads a unique-maximal chain from the supplied `Settings(_env_file=None)`, resolves historical definition/grants/markers without requiring current unexpired authority, exposes the introduction revision, and performs a final unchanged-chain reread. Prove caller-supplied archive/index paths, current resolver fallback, global settings drift, and ancestor arming are rejected.

- [ ] **Step 2: Add the narrow adapters**

```text
load_evidence_index_chain_read_only(settings: Settings) -> VerifiedEvidenceIndexChain
resolve_historical_connector_grant_evidence_read_only(
    settings: Settings,
    connector_key: str,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    expected_grant_sha256: str,
) -> VerifiedHistoricalGrantEvidence
```

Keep current public behavior by having existing callers pass no override. No adapter accepts an archive path, proof class, historical flag, or write authority.

- [ ] **Step 3: Write failing read-only capture verification tests**

Cover exact manifest/stream/seal/event rehash, two-run and NRC-only extant-run sets, introduction parity, code/campaign identity, no overwrite/repair, three literal rewrite cases, and before/after snapshot equality.

- [ ] **Step 4: Implement one read-only capture adapter**

```text
VerifiedCampaignLogCapture(
    manifest: ConnectorCampaignLogManifestV1,
    manifest_sha256: str,
    file_set_hash: str,
    seal: ConnectorCampaignLogSealV1,
    seal_sha256: str,
    stream_bytes: Mapping[str, bytes],
    seal_event_ids: ordered immutable sequence[str],
    stable_snapshot: ordered immutable sequence[(relative_path, size, sha256)],
)
verify_connector_campaign_log_capture_read_only(
    db: Session,
    chain: VerifiedEvidenceIndexChain,
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> VerifiedCampaignLogCapture
```

The adapter reuses existing strict schemas/canonical hash formulas and queries DB events. It does not reuse the writeful begin/seal path, repair partial state, or accept a caller path.

- [ ] **Step 5: Run focused and existing authority/capture files**

```powershell
Push-Location backend
python -m pytest tests/test_egress_auth.py tests/test_campaign_log_capture.py -q
Pop-Location
git diff --check
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/connector_egress_authorization.py backend/app/services/connector_campaign_log_capture.py backend/tests/test_egress_auth.py backend/tests/test_campaign_log_capture.py
git commit -m "feat(proof): expose read-only campaign evidence adapters"
```

## Task 7: Authority, Runtime, Terminal, Ledger, and Counter Checks

**Files:**
- Modify: `backend/app/services/dual_live_evaluator.py`
- Modify: `backend/tests/test_dual_eval.py`

**Interfaces:**
- Consumes: Task 6 read-only adapters, `read_runtime_records`, `derive_terminal_request_ledger`, and historical grant evidence.
- Produces: `CheckResult`, `EVALUATOR_CHECK_ORDER`, A/R/L check functions, and fixed aggregation precedence.

- [ ] **Step 1: Replace static-report tests with parameterized named-check failures**

Keep the public signature test. Add individually collected positive and negative nodes for `A01-A10`, `R01-R22`, and `L01-L12`. Each negative mutates exactly one field, row, event, byte sequence, runtime record, or counter frame and asserts its exact check ID/status/code; an end-to-end helper assertion does not substitute.

```python
@pytest.mark.parametrize("check_id,mutator,expected_status,expected_code", AUTH_RUNTIME_LEDGER_CASES,
                         ids=lambda case: case.id)
def test_named_check_rejects(fake_campaign, check_id, mutator,
                             expected_status, expected_code):
    mutator(fake_campaign)
    result = _result_by_id(_evaluate(fake_campaign), check_id)
    assert (result["status"], result["code"]) == (expected_status, expected_code)
```

- [ ] **Step 2: Run the new check nodes and observe the static scaffold failures**

Run:

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py -q -k "a0 or r0 or r1 or r2 or l0 or l1"
Pop-Location
```

- [ ] **Step 3: Implement the exact result types and registry**

The registry is a tuple of functions, not string-to-dynamic dispatch. Each function catches only its expected domain error and returns a secret-safe `CheckResult`; unexpected exceptions become one top-level `INDETERMINATE` internal code without exception text.

```python
CHECKS = (
    _check_a01_input_identity,
    _check_a02_index_linear_head,
    # exact order continues through _check_f09_connector_and_combined_reports
)
```

- [ ] **Step 4: Implement A01-A10 using the authority adapter**

Validate the complete chain before selecting a campaign. Select exact `1+2+1`; derive exact `2+4+2` only in the lifecycle case. Rehash definition/grants/markers, derive introduction, compare arming/ledger/seal/event bindings, and validate all half-open timestamps. Never call current egress resolution or trust stored hashes.

- [ ] **Step 5: Implement R01-R22 using capture/runtime records**

Verify exact four-stream membership/hashes, seal/events, runtime chain, census topology, one Phase-A boot, Job/process/socket records, authority clearing, Phase-B guards, Phase-B quiescence, and terminal sequence. A recorded clean quiescence record is necessary but is not independently trusted unless its Job/process/socket identity matches the wrapper record chain and final seal.

- [ ] **Step 6: Implement L01-L12 using DB events and full counter stream**

Query exactly the selected extant runs; reconstruct terminal ledgers; parse the complete counter stream; require counter/ledger bijection, one v2 runtime/boot, byte allowance/classification, cadence, transport policy, fresh 200 bytes, and NRC-first binding. A v1 counter or ambiguity is `INDETERMINATE`, never automatic `FAIL` or `PASS`.

- [ ] **Step 7: Run the named slices and existing ledger regressions**

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py tests/test_egress_transport.py tests/test_egress_arming.py -q
Pop-Location
git diff --check
```

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/dual_live_evaluator.py backend/tests/test_dual_eval.py
git commit -m "feat(proof): evaluate dual-live authority and ledgers"
```

## Task 8: Origin, Downstream, Package, and Custody Checks

**Files:**
- Modify: `backend/app/services/dual_live_evaluator.py`
- Modify: `backend/tests/test_dual_eval.py`

**Interfaces:**
- Consumes: origin-continuity derivation/assertion, package payload verifier, mapped SQLAlchemy models, protected source receipts, and isolated storage roots.
- Produces: D/C/F named checks and a complete PASS-capable evaluator.

- [ ] **Step 1: Write failing D01-D08 tests**

Build the ScienceBase and NRC fake verticals through the existing real constructors. Prove origin/raw/provenance/version/linkage, execution, review, exact three packages, payload bytes, submit, and prepared/internal handoff. Add one-axis mutation for every named boundary and assert no evaluator write.

- [ ] **Step 2: Implement D01-D08 by rederiving existing contracts**

Call read-only derivation/verification helpers only. Where existing response helpers merely project stored state, query the durable row and recompute its hash instead. Do not call workbench mutators, package materializers, submit mutators, or handoff mutators.

- [ ] **Step 3: Write failing C01-C08 bounded custody tests**

Inject unique fake URL/query/key sentinels into each mapped DB class, non-source file class, API-shaped serialization, event, report, generated artifact, and all four logs. Exercise raw, JSON, HTML, percent-once, percent-twice, invalid, and third-layer residual encodings. Verify only exact source ref+hash blobs are exempt and reports never echo forbidden bytes.

- [ ] **Step 4: Implement the bounded scanner**

Use fixed caps copied from existing capture and design bounds: 16 MiB per stream, 32 MiB capture aggregate, 64 KiB protected JSON, finite DB row/file/token counts pinned in constants and equality/+1 tests. Walk mapped column values using SQLAlchemy inspection and explicit campaign relationships; never issue unbounded table scans. Derive forbidden canonical candidates from protected grants and key bytes; report only sink class, relative row/file identity, offset, and one-way hit digest.

- [ ] **Step 5: Implement F01-F09 final stability, independence, API, aggregation, and report checks**

Reread the full evidence-chain membership/bytes and capture snapshot while locks remain held. Re-run the complete canonical DB projection in a fresh read-only transaction supplied by the gate. Emit the fixed report with no path, URL, query, key, header value, body, command line, endpoint, or exception text.

- [ ] **Step 6: Prove the evaluator itself is read-only**

Before and after every PASS/FAIL/INDETERMINATE test compare DB rows, SQLite bytes, evidence files, storage files, and directory membership. Instrument forbidden writeful functions so any call fails the test.

- [ ] **Step 7: Run the evaluator and downstream suites**

```powershell
Push-Location backend
python -m pytest tests/test_dual_eval.py tests/test_layer3_origin.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py -q
Pop-Location
git diff --check
```

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/dual_live_evaluator.py backend/tests/test_dual_eval.py
git commit -m "feat(proof): verify dual-live continuity through handoff"
```

## Task 9: Real Validate-Only Gate and Mechanical Stability

**Files:**
- Modify: `tools/dual_live_gate.py`
- Modify: `tests/test_dual_gate.py`

**Interfaces:**
- Consumes: exact existing environment settings, `ProofLocks`, read-only evaluator, local SQLite path.
- Produces: one JSON stdout result and fixed exit codes with no persistent effect.

- [ ] **Step 1: Write failing gate-precondition tests**

Implement the paired `G01_GATE_REFUSAL_PRECONDITIONS` and `G02_GATE_NETWORK_DENIAL` test nodes. Cover invalid/missing args, egress true/invalid, any current authority alias including case variants and `.env` reload, missing/empty/nonlocal/relative/UNC/reparse/memory/query-overridden DB, absent storage/evidence, lock busy/abandoned/ACL mismatch, unsealed capture, missing key for scan, guard failure, unsupported platform, and each guarded network route. Each must refuse or deny before evaluator entry and before file/DB/process/network effects.

- [ ] **Step 2: Write failing read-only SQLite tests**

Cover retained `GENERIC_READ` share-read-only handle, `mode=ro&cache=private`, `PRAGMA query_only=1`, `journal_mode=delete`, no `-journal/-wal/-shm`, no global engine, no migration/bootstrap, no `ATTACH`, no DDL/DML/flush, active writer, file replacement, between-snapshot row mutation, sidecar appearance, and same-connection `data_version` drift.

- [ ] **Step 3: Run gate tests and observe `_NoAccess` scaffold failures**

Run: `python -m pytest tests/test_dual_gate.py -q`

- [ ] **Step 4: Replace obsolete import prohibition with guarded evaluation**

Install low-level and Requests guards before backend path/import and implement `G01`/`G02` as the gate-owned named pre-evaluator checks. Load `Settings(_env_file=None)` from the current environment only. Do not import `app.db.session` or use global `SessionLocal`; connector modules may load after the guard, and tests prove all send paths remain denied.

- [ ] **Step 5: Acquire locks before protected reads**

Derive only enough lexical root/campaign identity from validated existing environment values to acquire the root then campaign mutex. Do not enumerate the index, capture, or DB first. Retain both locks through the second semantic DB snapshot and final file reread.

- [ ] **Step 6: Open and retain SQLite read-only**

Use a Windows file handle that denies write/delete sharing, then a private SQLAlchemy engine over an exact absolute local `file:` URI with `mode=ro&cache=private`. Verify closed DELETE-journal posture and no sidecars. Run snapshot 1, end the transaction, compare same-connection `data_version`, open a fresh read-only connection for snapshot 2, then rehash DB/file identity and sidecars. Never use `immutable=1`, `nolock`, custom VFS, checkpoint, or recovery.

- [ ] **Step 7: Emit exact result and exit**

Emit exactly one compact ASCII JSON line. Exit 0 for PASS, 1 for FAIL, 2 for INDETERMINATE/REFUSED. Unexpected exceptions emit a fixed internal refusal/indeterminate code with no exception text. Close DB engine/handles and release campaign then root locks in `finally`.

- [ ] **Step 8: Run gate tests twice and compare repo/runtime bytes**

```powershell
python -m pytest tests/test_dual_gate.py -q
python -m pytest tests/test_dual_gate.py -q
git diff --check
```

Expected: both pass; no report, DB, evidence, cache, or storage artifact is created.

- [ ] **Step 9: Commit**

```powershell
git add tools/dual_live_gate.py tests/test_dual_gate.py
git commit -m "feat(proof): validate dual-live evidence read only"
```

## Task 10: Real-Constructor Fake Campaign and Three Frozen Rewrites

**Files:**
- Modify: `backend/tests/test_dual_eval.py`
- Modify: `backend/tests/test_campaign_log_capture.py`
- Modify: `tests/test_dual_gate.py`

**Interfaces:**
- Consumes: complete producer/evaluator/gate implementation.
- Produces: the decisive offline G1 proof that Task-8 can PASS and literal partial rewrites fail closed.

- [ ] **Step 1: Build one isolated fake campaign through real constructors**

Use a new temporary SQLite DB, storage root, and evidence root. Construct the campaign definition, both grants, exact index slice, markers, strict armings, real reservation/completion events, counter-v2 frames, terminal ledgers, admitted source blobs, canonical origin receipts, Layer 3 execution/review rows, exactly three packages, submit and prepared-handoff state, wrapper runtime records, manifest, seal, and seal events through production constructors. Fake transports are deterministic and loopback-only; no credential or external network exists.

- [ ] **Step 2: Prove direct evaluator PASS and gate PASS**

Assert every A/R/L/D/C/F evaluator check is present exactly once and PASS, both G gate checks passed before evaluator entry, the combined status is PASS, `fresh_live=true`, `evaluation_complete=true`, gate exit 0, and before/after DB/filesystem snapshots are identical.

- [ ] **Step 3: Prove literal rewrite case 1**

Clone the isolated campaign, change one log byte, and rebuild the manifest only. Keep the original seal and DB events. Assert non-PASS at manifest/seal cross-domain parity and no mutation.

- [ ] **Step 4: Prove literal rewrite case 2**

Clone the isolated campaign, change one log byte, and rebuild manifest plus seal. Keep original DB seal events. Assert non-PASS at seal-event metrics parity and no mutation.

- [ ] **Step 5: Prove literal rewrite case 3**

Clone the isolated campaign and independently delete, duplicate, and rewrite one extant-run `campaign_log_capture_sealed` event. Keep original filesystem evidence. Assert non-PASS at event cardinality/parity and no mutation.

- [ ] **Step 6: Prove no all-domain overclaim**

Inspect report nonclaims and source constants: no signature, WORM, cryptographic nonrepudiation, owning-account compromise, or coherent all-domain-rewrite claim; no attestation/index/env alias exists.

- [ ] **Step 7: Run the decisive suite**

```powershell
Push-Location backend
python -m pytest tests/test_campaign_log_capture.py tests/test_dual_eval.py -q
Pop-Location
python -m pytest tests/test_dual_gate.py -q
git diff --check
```

Expected: all pass; rewrite cases collect independently.

- [ ] **Step 8: Commit**

```powershell
git add backend/tests/test_dual_eval.py backend/tests/test_campaign_log_capture.py tests/test_dual_gate.py
git commit -m "test(proof): prove dual-live pass and tamper refusal"
```

## Task 11: Full Task-9 Census, Re-Audit, and Evidence-Classified Closeout

**Files:**
- Modify only if a defect is found in Tasks 1-10.
- Do not create runtime proof artifacts or edit frozen/campaign records for test reporting.

**Interfaces:**
- Consumes: committed Tasks 1-10.
- Produces: exact V1-V8/root/progress/integrity evidence, independent exact-commit reviews, and the final correlated IPC result.

- [ ] **Step 1: Verify the changed-file and forbidden-surface set**

Run sequentially:

```powershell
git status --short
git diff --name-only 6aa98ecafb7ce3fddfc37e1e859b2ef7c8e77e50..HEAD
git diff --check
```

Expected: only the reconciled Task-8 production/test/support map above plus this non-frozen implementation plan and committed completion/review records; pre-existing `.omc/state/sessions/` remains untouched; no forbidden authority file, attestation/index/issuer/env surface, B1a seal, or unrelated file.

- [ ] **Step 2: Run V1 from `backend`**

```powershell
python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py tests/test_egress_arming.py tests/test_arming_api.py tests/test_egress_transport.py tests/test_egress_crash.py -q
```

Record exit, collected, passed, failed, skipped.

- [ ] **Step 3: Run V2 from `backend`**

```powershell
python -m pytest tests/test_sciencebase_fresh.py tests/test_nrc_fresh.py tests/test_nrc_strict_parse.py -q
```

- [ ] **Step 4: Run V3 from repo root**

```powershell
python -m pytest tests/test_api.py -q -k "sciencebase or nrc_adams"
```

Record deselected count as well.

- [ ] **Step 5: Run exact frozen V4 from `backend`**

```powershell
python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q
```

- [ ] **Step 6: Run corrected V4 from `backend`**

```powershell
python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_intake_successor.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q
```

- [ ] **Step 7: Run V5 and V6 from repo root**

```powershell
python -m pytest tests/test_dual_gate.py -q
python -m pytest tests/test_api.py -q
```

- [ ] **Step 8: Run V7 from `backend`**

```powershell
python -m pytest tests -q -k "layer3 or connector or nrc"
```

Do not call it green if any unexpected skip, failure, collection error, or interrupted shard exists.

- [ ] **Step 9: Run V8, root API/progress, and final integrity from repo root**

```powershell
python .\tools\l3-progress-check.py
git diff --check
```

Verify the pilot seal still equals `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` and report zero B1a STOP.

- [ ] **Step 10: Run exact-commit independent reviews**

Dispatch one security/Windows reviewer and one frozen-acceptance/Layer-3 reviewer at the exact HEAD. Each must self-verify source claims and targeted tests. Resolve critical/blocking findings narrowly; rerun affected focused tests and the full census after any code change.

- [ ] **Step 11: Verify commit hygiene**

```powershell
git log --format=fuller 6aa98ecafb7ce3fddfc37e1e859b2ef7c8e77e50..HEAD
git status --short
git diff --check
```

Expected: small coherent commits, no automated-tool attribution or trailers, no push, only pre-existing untracked session state.

- [ ] **Step 12: Write the exact correlated IPC reply once, as the final action**

After every self-verification and no further repo/tool action is needed, create exactly:

```text
C:/Users/<operator>/.claude/ipc/91b270df-110e-4a84-915d-d187bcf9589e/019faabd-31a1-7293-a3e7-d49087b95bcf/1785519952-490-2bfe6d4f188b9f32.reply.md
```

The reply contains: session ID if available; per-item done criteria; commits; exact V1-V8/root/progress/integrity commands, exits, and counts; PASS-capable fake campaign evidence; three rewrite-case evidence; unchanged B1a seal; changed-file scope; `REPO-CONFIRMED`/`TEST-MEASURED`/`INFERENCE`/`UNVERIFIED` labels; nonclaims; no live/acquisition/deployment/push claim.

Attempt the write exactly once. If denied, do not retry, debug, escalate, or substitute; put the full substantive report in the final response and state the denial in one line.

## Plan Self-Review Checklist

- [ ] Every frozen Task-8 line 2247-2512 maps to at least one stable check ID.
- [ ] Producer lines 2519-2560 and reinforcing Task-11 lines 2860-2884 map to named runtime checks and positive/negative tests.
- [ ] No umbrella test substitutes for a mapped clause.
- [ ] Every evaluator check and every gate check has at least one positive and one single-axis negative/adversarial test name.
- [ ] Result taxonomy, precedence, exit codes, unsealed distinction, and allowed-crossing distinction are explicit.
- [ ] No attestation, post-run index, issuer, fifth stream, environment alias, frozen amendment, coherent all-domain rewrite claim, or live Task-11 authority is introduced.
- [ ] Phase A and Phase B use explicit environment allowlists with `_env_file=None`; Phase B cannot reload `.env` authority.
- [ ] Atomic Job admission uses Job-list and handle-list attributes; no late-assignment fallback exists.
- [ ] PID/socket proof binds process creation identity and requires stable complete tables.
- [ ] Root/campaign lock order and final-reread lifetime are explicit.
- [ ] SQLite validation is existing-file, local, read-only, sidecar-free, query-only, and mechanically rechecked without checkpoint/recovery.
- [ ] The evaluator public signature is unchanged and accepts no caller path.
- [ ] Full Task-9 census and final one-shot IPC discipline are exact.
- [ ] Placeholder scan finds no forbidden placeholder marker or undefined adjacent interface.
