# G2-P8 live4 global lease

Status: `GLOBAL LEASE ISSUED / ACKS PENDING / NO RUN CAPABILITY / NOT RUN-READY / NON-LAUNCHING`

Recorded: `2026-08-09`

Lease ID: `g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983`

Lease descriptor SHA-256: `663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3`

Task ceiling: `ISSUED_PENDING_ACKS`

A preliminary uncommitted candidate used root hash
`afd73dc509b0c81d574a349e66a37e5451370ae15f8a11406131f0cb5d7ec25e` and was announced as issued
before independent review completed. Review found fail-closed containment and receipt-order defects.
That candidate failed its own validity fence, was never committed, never became a valid lease, and
created no ACK, credential, egress, run capability, readiness, GO, or launch. I withdraw that
premature announcement; the old hash is non-operative and cannot be reused.

I, orchestrator and lease-issuer task `019fe239-3c80-7f70-8a6e-29735e05e7b2`, now directly issue
this corrected one Lane B global lease against the exact lease ID and descriptor hash above. The
lease exists, but its state is `ISSUED_PENDING_ACKS`: it creates mandatory containment and actual-
release duties without creating a credential, egress capability, `B_RUN_READY`, launch authority,
GO, or run.

## 1. Authority basis and immutable tail

The owner directly issued the three ordered acts in C5. This lease binds that owner authorization and
the complete immutable tail rather than inheriting or paraphrasing any owner field.

| Binding | Exact value |
|---|---|
| Owner authorization path | `docs/campaign-records/2026-08-09-g2-p8-live4-owner-authorization.md` |
| C5 commit | `06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916` |
| C5 tree / blob | `27fb186880bc02f126d7d94d90963cb1c1968d42` / `c5d93f9c5f7e078fb55ac55c6fc65e6f74aabb89` |
| C5 bytes / raw SHA-256 | `11927` / `5f120a3e2ac163b7605f747289d34fb68c244b6590005f4ec5053d2f44b74d41` |
| C5 direct parent | C4 `3a2fc5882181c6e1a7aec76a15ad97711d2753fc` |
| Pre-packet evidence base | `e32da9925ca52ba0391ccedb4f81a7548a2ca429` / tree `50843c56a2c374426919f509c66611cca4f5c0d2` |
| Runtime revision | `d781adfcaab2eb880456aef7ac49ee589105bbbe` / tree `da21ee59890e03c0245ff12f2bec5ae3ce1730a0` |
| Verification-base main | `0b65b4f0b06fdbd1e34460800ef8251cebbb9307`; not run authority |

C1, C2, C3, R7, C4, and C5 are enumerated byte-for-byte in the subject descriptor. C5 is a clean,
sole-record child of C4, and all earlier bound blobs remain exact at C5.

## 2. Canonicalization and hash graph

Every descriptor below is serialized as UTF-8 JSON with `ensure_ascii=false`, `allow_nan=false`,
lexicographically sorted object keys, separators `(',', ':')`, no duplicate keys, no BOM, and no
trailing newline. Arrays retain their schema-defined order. UUIDs and hashes are lowercase canonical
forms; UTC values use fixed RFC 3339 `Z` form; absolute Windows paths use an uppercase drive,
backslashes, no relative segments, and no trailing separator. Nulls, placeholders, truncated hashes,
extra fields, and omitted required fields fail closed.

`H(x)` is lowercase hexadecimal SHA-256 over those exact canonical JSON bytes.

| Descriptor | SHA-256 |
|---|---|
| `subject_descriptor` | `23039e68a5ddd718e8e39e37a4546941d75598df784913ec8a4ca42b0ef5be04` |
| `operator_assignment_descriptor` | `58878469d07d76cd13dcf2de628965a656e6ff8a623a76eb599ccf2c883dd6f6` |
| `resource_scope_descriptor` | `1c6a821db270d1548b1f44c287a9c1ec3b1b7b8120726deea98ba2ed94d06e0b` |
| `run_command_class_descriptor` | `85f2fdaa0f0924c295741047b14b2aae16c83974f78d5d91710c3c2c1a24634a` |
| `containment_class_descriptor` | `56ac14ef25f1593472afb5bfef733548596f04d1c8cbf859aae5f14672d9c6f4` |
| `lease_terms_descriptor` | `c6318f89c34f3d1b46e85b9752418788dcb717b5a27b7478775efe65e370d7aa` |
| `receipt_requirements_descriptor` | `8f73c0c8353438b1278b5b99a3f24278a07825ff27df6f2106aba41f57c9fd5e` |
| `lease_descriptor` | `663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3` |

The root descriptor references only the seven leaf hashes. It does not contain its own hash or this
record's future Git identity, so no self-hash cycle exists.

## 3. Canonical descriptors

### Subject descriptor

```json
{"artifacts":[{"blob":"78adb72591185c46fba85dea225ae5188e41e13d","bytes":21410,"commit":"48305f1a7c84012ba15b7c98c45f866835b1d83d","id":"C1","path":"docs/campaign-records/2026-08-08-g2-p8-live4-owner-decision-packet.md","raw_sha256":"844a0c183d795731f8dc5b25b7b8da68bc2a69ea04546d8b9678581adefa6c68","tree":"e418488dcb6a3dfe683cfa489271050dcd9a3ca6"},{"blob":"8fc73317ca5f26dbc5f648e0e379737a7fa96581","bytes":8091,"commit":"c1954020b57095f954cfb6139e01ee6db2b5fdee","id":"C2","path":"docs/campaign-records/2026-08-08-g2-p8-live4-owner-packet-custody.md","raw_sha256":"03d6801ca7b25ad5f85a95f199901e4106c736fc6fe635e8e9d5cb0b7121e35f","tree":"fbed6d33feddceaf0a58957d1e2e001daef63517"},{"blob":"d4c24c89f1a05942218f2b541081aa0b98449e46","bytes":17309,"commit":"834014fbcea80724193dc2cc981efeea5bc99b91","id":"C3","path":"docs/campaign-records/2026-08-08-p8-readiness.md","raw_sha256":"70d14ae8ad92b559e246a5f02f0fa0a8a95041ea4bc84760ab67e0532e7b9ddb","tree":"be41fec1db1bccb8cc38e23f3077b6ef9739f5c8"},{"blob":"61bcc3b4a4b9d6a5c0b718f10621028a2f046020","bytes":2581,"commit":"441572b5737911f8104c559f570bc0e2d6edac4d","id":"R7","path":"docs/campaign-records/2026-08-08-ci-r7-closeout.md","raw_sha256":"2ab861234263b92f91fb5654959ccbbe24166c58a854d8ee8a75bcd216772282","tree":"5ace56f580440cf178f451d15a265545db37e412"},{"blob":"3a246e39528c9de6fbd21d54efe701d12a4a9f3d","bytes":14727,"commit":"3a2fc5882181c6e1a7aec76a15ad97711d2753fc","id":"C4","path":"docs/campaign-records/2026-08-09-g2-p8-live4-owner-decision-preflight.md","raw_sha256":"2e3021ccf613eff3a218551f7c3908000624fdafd5089b4a75f25559ced79edd","tree":"3dc65289b59841c95d6ab31b6e3642a26e31da1c"},{"blob":"c5d93f9c5f7e078fb55ac55c6fc65e6f74aabb89","bytes":11927,"commit":"06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916","id":"C5","path":"docs/campaign-records/2026-08-09-g2-p8-live4-owner-authorization.md","raw_sha256":"5f120a3e2ac163b7605f747289d34fb68c244b6590005f4ec5053d2f44b74d41","tree":"27fb186880bc02f126d7d94d90963cb1c1968d42"}],"authority_expiry_utc":"2026-08-14T14:06:52.580652Z","b1a_seal_blob":"b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2","campaign":{"campaign_fingerprint":"3c415b6fe717810c47c506c9de8ce9c0ec5b78e9a633db080cdce91f16915e01","campaign_id":"ff1af01b-785e-4c12-98d1-3f278039b4ea","evidence_index_revision":1,"evidence_index_sha256":"e54ae4f30122293bf926fad89085472325c15279d642eb712e8e3deba16e6d6b","raw_sha256":"07ef4c182d320f43163ff039e90f885bcee8e72a30e9b819732ff358c93c25c7"},"frozen_plan_blob":"68f740af86dc7d1ac2227f81a6ea28e7e2c7458f","grants":[{"canonical_fingerprint":"af753222bcbf4a524f63275dde2a1563b5edb6ee9952a3edae430bf4b0b86c38","connector_key":"nrc_adams_aps","deterministic_run_id":"a4111769-3868-5f0c-9c16-eeb4130594b4","expected_marker_sha256":"1a862282ee40ecfaa30c52075584ae592486c3bc1f84ef9ad9499b18b2a68841","grant_id":"nrc-aps-fa4cc6c53e76","raw_sha256":"8f0e5c778f76d0da272ba636308faeaef85693bbce95e4c9b508185ac91e79e1","source_system":"nrc_adams"},{"canonical_fingerprint":"f9b868cef8051af749c5de74d78d46162a3cf7c25123963fb705ba302dd400ae","connector_key":"sciencebase_mcs","deterministic_run_id":"622cb673-254b-56c4-9e9c-1d5c8d3908d8","expected_marker_sha256":"85a68fe3c92312a817a828fe4f202cd1e029bdbc9863b3735badec6240d5e371","grant_id":"sciencebase-mcs-8ae20b6e8f89","raw_sha256":"b1819f62ffbf3f7f83814ec061f0e37f99937d9e5e3e2c39b81370071787dd8d","source_system":"sciencebase"}],"lane":"B","latest_launch_cutoff_utc":"2026-08-13T14:06:52.580652Z","minimum_launch_final_ttl_seconds":86400,"pre_packet_revision":"e32da9925ca52ba0391ccedb4f81a7548a2ca429","pre_packet_tree":"50843c56a2c374426919f509c66611cca4f5c0d2","runtime_revision":"d781adfcaab2eb880456aef7ac49ee589105bbbe","runtime_tree":"da21ee59890e03c0245ff12f2bec5ae3ce1730a0","schema_id":"project6.live4.subject.v1","verification_base_is_run_authority":false,"verification_base_main":"0b65b4f0b06fdbd1e34460800ef8251cebbb9307"}
```

### Operator-assignment descriptor

```json
{"containment_operator":{"host_id":"local","status":"PROPOSED_PENDING_DIRECT_ACK","task_id":"019fe286-e5f4-75e3-b047-4037129573b2"},"credential_value_embedded":false,"independent_verifier":{"host_id":"local","status":"PROPOSED_PENDING_VERIFICATION","task_id":"019fe287-24a0-7d50-8e7d-0ff0d6b7c0ec"},"lease_issuer":{"host_id":"local","task_id":"019fe239-3c80-7f70-8a6e-29735e05e7b2"},"orchestrator":{"host_id":"local","task_id":"019fe239-3c80-7f70-8a6e-29735e05e7b2"},"phase_operator_task_ids_distinct":true,"run_operator":{"host_id":"local","status":"PROPOSED_PENDING_DIRECT_ACK","task_id":"019fe287-8771-77f2-9300-de4e0eac1ba6"},"schema_id":"project6.live4.operator_assignment.v1"}
```

### Resource-scope descriptor

```json
{"bounded_consumption_roots":["C:\\p6-run\\live4\\evidence\\consumed"],"bounded_log_roots":["C:\\p6-run\\live4\\evidence\\logs"],"bounded_seal_roots":["C:\\p6-run\\live4\\evidence\\log-seals"],"bounded_storage_roots":["C:\\p6-run\\live4\\storage"],"campaign_lock_identity_sha256":"03a9f42741b3ccfee8ad90aa6a564653842d3b5a06fddca64c7d4fbfc68da52d","campaign_mutex_name":"project6-dual-live-v1\\campaign-03a9f42741b3ccfee8ad90aa6a564653842d3b5a06fddca64c7d4fbfc68da52d","campaign_path":"C:\\p6-run\\live4\\campaign.json","credential_present_at_issue":false,"credential_storage_in_descriptor":false,"database_path":"C:\\p6-run\\live4\\db\\method_aware.db","database_sha256":"6222a9e8ac93955ac217e624d383b273c29b454b5e058806de0db4f10ed68ba7","dependency_lock_sha256":"bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02","dependency_set_sha256":"1c24c9820e3a001e89748d7795180b68fa99e48f1d7d42fdb554049c7885217d","egress_armed_at_issue":false,"evidence_children":{"consumed":0,"log-seals":0,"logs":0},"evidence_index_path":"C:\\p6-run\\live4\\evidence\\indexes\\e54ae4f30122293bf926fad89085472325c15279d642eb712e8e3deba16e6d6b.json","evidence_root":"C:\\p6-run\\live4\\evidence","grant_paths":["C:\\p6-run\\live4\\nrc-aps-grant.json","C:\\p6-run\\live4\\sciencebase-grant.json"],"interpreter_path":"C:\\p6-run\\py312\\python.exe","interpreter_sha256":"4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a","literal_cleanliness_receipt":{"detached_head":true,"extensions_worktree_config_present":false,"head":"d781adfcaab2eb880456aef7ac49ee589105bbbe","index_diff_exit_code":0,"status_entry_count":0,"tree":"da21ee59890e03c0245ff12f2bec5ae3ce1730a0","worktree_diff_exit_code":0},"literal_cleanliness_receipt_sha256":"7d96d105597252a0c726d35cfc878d2a85d84cf80b6cd5d151a669c506b29f64","live4_inventory":{"directory_count":9,"file_count":9,"item_count":18,"reparse_count":0},"live4_root":"C:\\p6-run\\live4","mutex_boundary_name":"project6-dual-live-boundary-v1","mutex_namespace_alias":"project6-dual-live-v1","pymupdf_version":"1.27.2.3","python_dll_sha256":"9a0e3435aaa680d868150f87ab3e388ad2eebc22f87e036155c7b4eda8cd2120","root_lock_identity_sha256":"1a90dfcfd97746ddb3027072c85abf6c16829ee39f488bf6a69736bde81f6b6b","root_mutex_name":"project6-dual-live-v1\\root-1a90dfcfd97746ddb3027072c85abf6c16829ee39f488bf6a69736bde81f6b6b","runtime_checkout_path":"C:\\p6-scratch\\dl-sbfix","runtime_git_registration_state":"STANDALONE_REPOSITORY_SOLE_WORKTREE_DETACHED_HEAD","runtime_head":"d781adfcaab2eb880456aef7ac49ee589105bbbe","runtime_tree":"da21ee59890e03c0245ff12f2bec5ae3ce1730a0","schema_id":"project6.live4.resource_scope.v1","staging_script_path":"C:\\p6-run\\live4\\set-live-env.ps1","staging_script_sha256":"210d99102a40d7f78bcbcaae53c64b1a2cb6ec5b3cd99f97dc389873f4b173a9","wrapper_path":"C:\\p6-scratch\\dl-sbfix\\tools\\dual_live_run.py","wrapper_sha256":"fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f"}
```

### Run-command-class descriptor

```json
{"absolute_interpreter_required":true,"action_count":1,"alternate_checkout_permitted":false,"alternate_command_class_permitted":false,"alternate_interpreter_permitted":false,"arguments_fixed_by_launch_final_receipt":true,"bytecode_disabled_required":true,"campaign_fingerprint":"3c415b6fe717810c47c506c9de8ce9c0ec5b78e9a633db080cdce91f16915e01","campaign_id":"ff1af01b-785e-4c12-98d1-3f278039b4ea","class_id":"project6.live4.single_wrapper_run.v1","credential_fallback_permitted":false,"credential_value_embedded":false,"exact_runtime_checkout_required":true,"executable_command_embedded":false,"first_process_creation_attempt_consumes_authority":true,"interpreter_sha256":"4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a","isolated_mode_required":true,"launch_requires_explicit_issuer_go":true,"maximum_launches":1,"no_shell_substitution":true,"pycache_prefix_required":"NUL","replacement_process_permitted":false,"resume_permitted":false,"retry_permitted":false,"runtime_revision":"d781adfcaab2eb880456aef7ac49ee589105bbbe","schema_id":"project6.live4.run_command_class.v1","second_launch_permitted":false,"working_directory_required":"C:\\p6-scratch\\dl-sbfix","wrapper_sha256":"fe9ee12d97d082b55f2388298735fe77a6481e981f0a4d2be971d290c9c5576f"}
```

### Containment-class descriptor

```json
{"class_id":"project6.live4.containment.v1","containment_required_after_every_terminal_outcome":true,"containment_survives_run_window_and_lease_expiry":true,"credential_inspection_copy_hash_or_log_permitted":false,"deletion_or_overwrite_permitted":false,"duties":["bind_acquisition_context_and_control_channel_before_readiness","presence_test_credential_only","remove_credential_from_named_context_or_terminate_named_context","verify_credential_absence_after_removal","disarm_egress_and_verify_false_or_absent","stop_and_wait_named_run_pid_and_descendants_only","verify_named_process_tree_exited_and_sockets_closed","obtain_fresh_external_producer_quiescence_rebind","record_exact_authority_grant_and_marker_disposition","preserve_hash_inventory_and_seal_evidence_without_deletion","record_terminal_status","request_actual_capability_and_global_lease_release"],"executable_command_embedded":false,"failure_disposition":"CONTAINMENT_HOLD_OWNER_ADJUDICATION_REQUIRED","independent_verifier_confirms_release":true,"issuer_only_releases_capability_and_lease":true,"launch_restart_retry_or_reacquisition_permitted":false,"required_terminal_outcomes":["success","refusal","failure","timeout","ambiguity","declined","hold","expired","redirect"],"schema_id":"project6.live4.containment_class.v1","scope_after_lease_expiry":"CONTAINMENT_ONLY_UNTIL_ACTUAL_CAPABILITY_AND_LEASE_RELEASE","unrelated_process_or_service_control_permitted":false}
```

### Lease-terms descriptor

```json
{"automatic_stop":true,"b_run_ready":false,"containment_survives_lease_expiry_until_actual_capability_and_lease_release":true,"expires_at_utc":"2026-08-14T14:06:52.580652Z","issued_at_interval_end_exclusive_utc":"2026-08-09T20:51:14.000000Z","issued_at_interval_start_utc":"2026-08-09T20:51:13.000000Z","issuer_task_id":"019fe239-3c80-7f70-8a6e-29735e05e7b2","lane":"B","lane_a_locked":true,"latest_launch_cutoff_utc":"2026-08-13T14:06:52.580652Z","lease_id":"g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983","maximum_launches":1,"minimum_launch_final_ttl_seconds":86400,"renewal_permitted":false,"resume_permitted":false,"retry_permitted":false,"run_authority":false,"schema_id":"project6.live4.lease_terms.v1","state":"ISSUED_PENDING_ACKS"}
```

### Receipt-requirements descriptor

```json
{"initial_status":{"acquisition_context_custody_receipt":"ABSENT","b_run_ready_receipt":"ABSENT","c7_containment_operator_ack":"ABSENT","c7_independent_verifier_receipt":"ABSENT","c7_run_operator_ack":"ABSENT","capability_release_receipt":"ABSENT","clearance_receipt":"ABSENT","containment_completion_receipt":"ABSENT","containment_control_channel_receipt":"ABSENT","containment_readiness_receipt":"ABSENT","credential_placement_receipt":"ABSENT","egress_arming_receipt":"ABSENT","launch_final_identity_receipt":"ABSENT","launch_final_quiescence_receipt":"ABSENT","launch_final_time_ttl_receipt":"ABSENT","lease_release_receipt":"ABSENT","one_launch_authority_receipt":"ABSENT","orchestrator_go_receipt":"ABSENT","terminal_receipt":"ABSENT"},"performed_during_run":["p5_live_runtime_verification"],"required_after_terminal":["terminal_receipt","containment_completion_receipt","capability_release_receipt","lease_release_receipt","clearance_receipt"],"required_before_b_run_ready":["c7_run_operator_ack","c7_containment_operator_ack","c7_independent_verifier_receipt","credential_placement_receipt","egress_arming_receipt","one_launch_authority_receipt","acquisition_context_custody_receipt","containment_control_channel_receipt","launch_final_identity_receipt","launch_final_time_ttl_receipt","launch_final_quiescence_receipt","containment_readiness_receipt"],"required_before_launch":["b_run_ready_receipt","orchestrator_go_receipt"],"required_c7_receipts":["c7_run_operator_ack","c7_containment_operator_ack","c7_independent_verifier_receipt"],"schema_id":"project6.live4.receipt_requirements.v1"}
```

### Root lease descriptor

```json
{"canonicalization_schema_id":"project6.canonical_json.v1","containment_class_descriptor_sha256":"56ac14ef25f1593472afb5bfef733548596f04d1c8cbf859aae5f14672d9c6f4","lease_id":"g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983","lease_terms_descriptor_sha256":"c6318f89c34f3d1b46e85b9752418788dcb717b5a27b7478775efe65e370d7aa","operator_assignment_descriptor_sha256":"58878469d07d76cd13dcf2de628965a656e6ff8a623a76eb599ccf2c883dd6f6","receipt_requirements_descriptor_sha256":"8f73c0c8353438b1278b5b99a3f24278a07825ff27df6f2106aba41f57c9fd5e","resource_scope_descriptor_sha256":"1c6a821db270d1548b1f44c287a9c1ec3b1b7b8120726deea98ba2ed94d06e0b","run_command_class_descriptor_sha256":"85f2fdaa0f0924c295741047b14b2aae16c83974f78d5d91710c3c2c1a24634a","schema_id":"project6.global_lease_descriptor.v1","subject_descriptor_sha256":"23039e68a5ddd718e8e39e37a4546941d75598df784913ec8a4ca42b0ef5be04"}
```

## 4. Issuance time and fresh posture

Fresh no-cache GitHub HTTP `Date` evidence bounds corrected issuance to
`[2026-08-09T20:51:13Z, 2026-08-09T20:51:14Z)`. At the conservative interval
ceiling, `321338` whole seconds remained before the strict latest-launch cutoff and `407738` whole
seconds remained before authority expiry. Issuance is strictly before both instants and the authority
TTL exceeds `86400` seconds. Launch still requires a separate immediate launch-final time/TTL receipt.

Immediately before issuance, bounded validate-only checks rederived:

- C5 exact at `HEAD`, clean, direct child of C4, sole added authorization record;
- the runtime checkout exact, detached, standalone, sole-worktree, and clean at the bound revision/tree;
- the interpreter, DLL, wrapper, dependency lock/set, staging script, database, campaign, grants, and
  evidence index at their exact bound hashes;
- credential absent and egress not armed;
- live4 at 18 items, 9 files, 9 directories, zero reparses; `consumed/`, `logs/`, and `log-seals/`
  empty; and no database sidecars;
- root lock identity `1a90dfcfd97746ddb3027072c85abf6c16829ee39f488bf6a69736bde81f6b6b`
  and campaign lock identity `03a9f42741b3ccfee8ad90aa6a564653842d3b5a06fddca64c7d4fbfc68da52d`;
- draft PR `#2485` open, exact C4 remote head before local C5, mergeable/clean, `22/22` successful,
  with no PR-ready or merge inference.

The full C5 authorization-time dependency, database, denied-network resolver, staging, and external-
quiescence rebind remains part of the immutable subject. This lease does not claim continuing
quiescence; launch-final must obtain a fresh direct external rebind.

## 5. Operator and command boundaries

The run and containment operators are proposed, not yet ACKed. The independent verifier has not yet
verified this lease in committed custody because its future C6 Git identity does not yet exist.

The run class is symbolic and non-secret. It permits at most one process-creation attempt after all
later receipts and a direct issuer GO. The first attempt consumes the one-launch authority regardless
of success, refusal, failure, timeout, ambiguity, or startup failure. Retry, resume, replacement,
argument widening, an alternate checkout/interpreter/class, and a second launch are forbidden.

The containment class is distinct and narrow. Before `B_RUN_READY`, a later receipt must bind the
actual acquisition context, named process tree, and a control channel or bounded cleanup primitive.
No such context or control channel exists yet. Containment may presence-test but never read, copy,
hash, log, or expose a credential value; it must verify absence after removal; it may control only the
named run process and descendants; and it must preserve and seal evidence without deletion. Any
uncertain cleanup, process/socket state, producer state, grant disposition, or seal yields
`CONTAINMENT_HOLD` and owner adjudication.

Run authority ends at the cutoff or any terminal outcome. The enumerated containment-only duty
survives the run window and lease expiry until actual capability and lease release. Owner adjudication
may alter recovery instructions but cannot terminate containment duty, substitute for actual release,
or permit clearance. Containment cannot be used to launch, retry, reacquire, or control unrelated
processes or services.

## 6. Current state and later gates

```text
state=GLOBAL_LEASE_ISSUED_PENDING_ACKS
lease_exists=true
operator_acks=0/2
independent_verification_receipt=ABSENT
credential_placement=UNPERFORMED
egress_arming=UNPERFORMED
one_launch_authority=UNSPENT_NOT_ISSUED
acquisition_context_custody=ABSENT
containment_control_channel=ABSENT
launch_final_preflight=ABSENT
containment_readiness=ABSENT
B_RUN_READY=false
orchestrator_GO=ABSENT
launch=UNPERFORMED
containment_completion_receipt=ABSENT
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

The next permitted transition is a separate C7 custody receipt binding this immutable C6 plus direct
run-operator ACK, direct containment-operator ACK, and independent descriptor verification. Even
after C7, every credential, egress, acquisition-context, launch-final, containment-readiness,
`B_RUN_READY`, and GO receipt remains a distinct later gate.

Because a lease now exists, every later disposition must follow the lease-existed path: containment
and actual capability/lease release are mandatory before `B_CLEARANCE_RECORDED`, even if no launch
occurs. The no-lease terminal path is no longer applicable.

## 7. Record fence and self-identity

This record cannot embed its own future Git blob, containing commit, or containing tree. It is valid
only if:

1. its direct parent is C5 `06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916`;
2. its sole path delta is this added lease record;
3. C1, C2, C3, R7, C4, and C5 remain byte-identical;
4. all seven canonical leaf JSON objects and their hashes recompute exactly;
5. the root descriptor and `663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3`
   recompute exactly without a self-reference;
6. trusted time, subject, resource, and absence checks above pass;
7. strict UTF-8, no BOM, LF-only, final LF, no trailing whitespace, and `git diff --check` pass; and
8. no command, credential, egress, ACK, readiness, launch, PR-ready, merge, release, clearance, or
   Lane A act is embedded or inferred.

C7 must bind this record's derived path, commit, tree, blob, bytes, and raw SHA-256 plus the lease ID,
all seven leaf hashes, and the root hash. No self-pinning follow-up is required.

## 8. Non-claims

This record claims only issuance of the exact non-capability global lease in
`ISSUED_PENDING_ACKS`. It claims no operator ACK or availability; verifier receipt; acquisition
context or control channel; credential access or value; egress; one-launch authority; current
quiescence; `B_RUN_READY`; GO; launch, run, retry, resume, or second launch; P5-live verification;
dual PASS; terminal containment; actual release; clearance; PR-ready, merge, main, production, or
Lane A authority. It executes no runtime action.
