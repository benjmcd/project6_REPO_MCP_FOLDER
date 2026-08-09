# G2-P8 live4 global lease acknowledgements

Status: `GLOBAL LEASE ISSUED / REQUIRED C7 ACKS RECORDED / NO RUN CAPABILITY / NOT RUN-READY / NON-LAUNCHING`

Recorded: `2026-08-09`

Lease ID: `g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983`

Operative lease descriptor SHA-256: `663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3`

This C7 record takes immutable custody of the direct run-operator ACK, direct containment-operator ACK,
and independent-verifier receipt required by C6. It changes only acknowledgement custody. It supplies
no credential, credential access, egress, one-launch authority, acquisition context, containment
control channel, launch-final receipt, `B_RUN_READY`, issuer GO, launch, release, clearance, or Lane A
authority.

## 1. Immutable C6 and authority binding

| Binding | Exact value |
|---|---|
| C6 path | `docs/campaign-records/2026-08-09-g2-p8-live4-global-lease.md` |
| C6 commit | `cb064832c1bb66e8b69282a33a4604dc790c0334` |
| C6 tree | `c0dc2797d1b4e78c27f76ba49f32084c1eeda608` |
| C6 blob | `0711c8f4e680d8f706a879adf13916c86d2757de` |
| C6 bytes | `24057` |
| C6 raw SHA-256 | `755f23281b2699aa6b85e77b52f6c3b91738ca540dc68da98adc0e655c2e3580` |
| C6 direct parent / sole delta | C5 `06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916`; sole addition of the C6 path |
| C1 | `48305f1a7c84012ba15b7c98c45f866835b1d83d` |
| C2 | `c1954020b57095f954cfb6139e01ee6db2b5fdee` |
| C3 | `834014fbcea80724193dc2cc981efeea5bc99b91` |
| R7 | `441572b5737911f8104c559f570bc0e2d6edac4d` |
| C4 owner-decision preflight | `3a2fc5882181c6e1a7aec76a15ad97711d2753fc` |
| C5 owner authorization | `06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916` |
| Issuer/orchestrator task | `019fe239-3c80-7f70-8a6e-29735e05e7b2`, `host_id=local` |

C6 already binds the complete C1/C2/C3/R7/C4/C5 artifact identities, the owner's ordered issuance,
the exact runtime/resource scope, and all later-gate requirements. C7 incorporates that immutable C6
by exact Git and raw-byte identity; it does not reconstruct, replace, broaden, or weaken C6.

## 2. Operative C6 hash graph

| Descriptor | SHA-256 |
|---|---|
| Subject | `23039e68a5ddd718e8e39e37a4546941d75598df784913ec8a4ca42b0ef5be04` |
| Operator assignment | `58878469d07d76cd13dcf2de628965a656e6ff8a623a76eb599ccf2c883dd6f6` |
| Resource scope | `1c6a821db270d1548b1f44c287a9c1ec3b1b7b8120726deea98ba2ed94d06e0b` |
| Run-command class | `85f2fdaa0f0924c295741047b14b2aae16c83974f78d5d91710c3c2c1a24634a` |
| Containment class | `56ac14ef25f1593472afb5bfef733548596f04d1c8cbf859aae5f14672d9c6f4` |
| Lease terms | `c6318f89c34f3d1b46e85b9752418788dcb717b5a27b7478775efe65e370d7aa` |
| Receipt requirements | `8f73c0c8353438b1278b5b99a3f24278a07825ff27df6f2106aba41f57c9fd5e` |
| Root lease descriptor | `663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3` |

The earlier preliminary root `afd73dc5...` remains withdrawn and non-operative exactly as C6 records.
Only the full root above and its seven full leaf hashes are operative.

## 3. C7 custody time

A fresh no-cache GitHub HTTP `Date` response bounds this C7 custody act to
`[2026-08-09T21:01:53Z, 2026-08-09T21:01:54Z)`. At the conservative interval ceiling,
`320698` whole seconds remained before the strict latest-launch cutoff
`2026-08-13T14:06:52.580652Z`, and `407098` whole seconds remained before authority expiry
`2026-08-14T14:06:52.580652Z`. C7 is strictly before both instants and exceeds the `86400`-second
minimum launch-final TTL. This is custody-time evidence only; launch-final still requires its own
fresh trusted time/TTL receipt.

## 4. Direct receipt byte identities

The issuer/orchestrator retrieved each final message directly from the named Codex task on
`host_id=local`, encoded the returned text as UTF-8 without applying newline or Unicode normalization, and
measured the exact returned bytes. The SHA-256, byte count, thread ID, and item ID below are the
authoritative message identities. The four-backtick quotation delimiters and any separator newline
needed to render the quotations are not part of those source-message identities.

| Required receipt | Source task | Final item | Bytes | LF / CR | Raw SHA-256 | Receipt UTC interval |
|---|---|---:|---:|---:|---|---|
| Direct run-operator ACK | `019fe287-8771-77f2-9300-de4e0eac1ba6` | `item-196` | `3232` | `60 / 0` | `089d75038b94cac0bcfabe2a122e6468cbc9f38a54950b711a723d9ab610bf4d` | `[2026-08-09T20:58:37Z, 2026-08-09T20:58:38Z)` |
| Direct containment-operator ACK | `019fe286-e5f4-75e3-b047-4037129573b2` | `item-179` | `3450` | `68 / 0` | `427a25170673fd223ce6377cce78e5934a169bdefa2ac35ab8b17ddcdb91d39d` | `[2026-08-09T20:59:00Z, 2026-08-09T20:59:01Z)` |
| Independent-verifier receipt | `019fe287-24a0-7d50-8e7d-0ff0d6b7c0ec` | `item-126` | `2974` | `72 / 0` | `1afb52425af25d7a45fb2b14032d4c767821f3932c0ecf5dda4bbeaf5204cf13` | `[2026-08-09T20:58:50Z, 2026-08-09T20:58:51Z)` |

### 4.1 Direct run-operator ACK — exact returned text

````text
# DIRECT RUN-OPERATOR ACK — NON-LAUNCHING

I, run-operator task `019fe287-8771-77f2-9300-de4e0eac1ba6`, `host_id=local`, directly ACK assignment under this exact immutable C6 global lease.

## Immutable C6 binding

- Path: `docs/campaign-records/2026-08-09-g2-p8-live4-global-lease.md`
- Commit: `cb064832c1bb66e8b69282a33a4604dc790c0334`
- Tree: `c0dc2797d1b4e78c27f76ba49f32084c1eeda608`
- Blob: `0711c8f4e680d8f706a879adf13916c86d2757de`
- Bytes: `24057`
- Raw SHA-256: `755f23281b2699aa6b85e77b52f6c3b91738ca540dc68da98adc0e655c2e3580`
- Direct parent C5: `06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916`
- Commit delta: sole addition of C6 path above
- Lease ID: `g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983`
- Lease descriptor SHA-256: `663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3`
- Issuer/orchestrator task: `019fe239-3c80-7f70-8a6e-29735e05e7b2`

Leaf bindings:

- Subject: `23039e68a5ddd718e8e39e37a4546941d75598df784913ec8a4ca42b0ef5be04`
- Operator assignment: `58878469d07d76cd13dcf2de628965a656e6ff8a623a76eb599ccf2c883dd6f6`
- Resource scope: `1c6a821db270d1548b1f44c287a9c1ec3b1b7b8120726deea98ba2ed94d06e0b`
- Run class: `85f2fdaa0f0924c295741047b14b2aae16c83974f78d5d91710c3c2c1a24634a`
- Containment class: `56ac14ef25f1593472afb5bfef733548596f04d1c8cbf859aae5f14672d9c6f4`
- Lease terms: `c6318f89c34f3d1b46e85b9752418788dcb717b5a27b7478775efe65e370d7aa`
- Receipt requirements: `8f73c0c8353438b1278b5b99a3f24278a07825ff27df6f2106aba41f57c9fd5e`

## Run-class ACK

I ACK only symbolic class `project6.live4.single_wrapper_run.v1`:

- `action_count=1`; `maximum_launches=1`.
- Exactly one permitted process-creation attempt.
- First process-creation attempt consumes authority, including startup failure.
- No retry, resume, replacement process, reacquisition, alternate command class, alternate checkout/interpreter, or second launch.
- No executable command or credential value supplied by this ACK.
- Terminal outcome or cutoff requires automatic stop and immediate containment handoff to named containment operator task `019fe286-e5f4-75e3-b047-4037129573b2`.
- Run authority never substitutes for containment, actual capability/lease release, or clearance.

Fresh trusted UTC interval: `[2026-08-09T20:58:37Z, 2026-08-09T20:58:38Z)`. Interval strictly precedes cutoff and expiry.

## Non-authority

This ACK supplies no credential, credential value/access, egress, one-launch authority, `B_RUN_READY`, issuer GO, launch, retry, runtime act, release, or clearance.

I will not perform process creation or any runtime act until all C6-required receipts exist and bind exact C6:

- containment-operator ACK;
- independent-verifier receipt;
- credential-placement receipt;
- egress-arming receipt;
- one-launch-authority receipt;
- acquisition-context-custody receipt;
- containment-control-channel receipt;
- launch-final identity, time/TTL, and quiescence receipts;
- containment-readiness receipt;
- `B_RUN_READY` receipt; and
- direct exact issuer GO from task `019fe239-3c80-7f70-8a6e-29735e05e7b2`, binding this lease ID, root hash, and immutable C6 identity.

Current state after this message: direct run-operator ACK issued; lease otherwise remains non-capability and non-launching.
````

### 4.2 Direct containment-operator ACK — exact returned text

````text
[$caveman] **DIRECT CONTAINMENT-OPERATOR ACK — ISSUED**

```text
ack_type=C7_CONTAINMENT_OPERATOR_DIRECT_ACK
operator_task_id=019fe286-e5f4-75e3-b047-4037129573b2
host_id=local
issuer_orchestrator_task_id=019fe239-3c80-7f70-8a6e-29735e05e7b2

lease_id=g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983
lease_state=ISSUED_PENDING_ACKS

c6_path=docs/campaign-records/2026-08-09-g2-p8-live4-global-lease.md
c6_commit=cb064832c1bb66e8b69282a33a4604dc790c0334
c6_tree=c0dc2797d1b4e78c27f76ba49f32084c1eeda608
c6_blob=0711c8f4e680d8f706a879adf13916c86d2757de
c6_bytes=24057
c6_raw_sha256=755f23281b2699aa6b85e77b52f6c3b91738ca540dc68da98adc0e655c2e3580
c6_direct_parent=06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916
c6_delta=SOLE_ADDITION_OF_C6_PATH

lease_descriptor_sha256=663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3
subject_descriptor_sha256=23039e68a5ddd718e8e39e37a4546941d75598df784913ec8a4ca42b0ef5be04
operator_assignment_descriptor_sha256=58878469d07d76cd13dcf2de628965a656e6ff8a623a76eb599ccf2c883dd6f6
resource_scope_descriptor_sha256=1c6a821db270d1548b1f44c287a9c1ec3b1b7b8120726deea98ba2ed94d06e0b
run_command_class_descriptor_sha256=85f2fdaa0f0924c295741047b14b2aae16c83974f78d5d91710c3c2c1a24634a
containment_class_descriptor_sha256=56ac14ef25f1593472afb5bfef733548596f04d1c8cbf859aae5f14672d9c6f4
lease_terms_descriptor_sha256=c6318f89c34f3d1b46e85b9752418788dcb717b5a27b7478775efe65e370d7aa
receipt_requirements_descriptor_sha256=8f73c0c8353438b1278b5b99a3f24278a07825ff27df6f2106aba41f57c9fd5e

trusted_utc_interval=[2026-08-09T20:59:00Z,2026-08-09T20:59:01Z)
trusted_source=credential-free cache-busted GitHub HTTP Date; HTTP 200
cutoff_remaining_at_interval_ceiling_seconds=320871
expiry_remaining_at_interval_ceiling_seconds=407271
```

I directly ACK exact C6 containment assignment. I accept conditional responsibility for:

- binding acquisition context plus control channel before readiness;
- credential presence-test only; removal from named context or named-context termination; verified absence afterward;
- egress disarm plus false/absent verification;
- named run PID and descendants only; process exit and socket closure verification;
- fresh external producer-quiescence rebind;
- exact authority, grant, and marker disposition;
- evidence preservation, hashing, inventory, sealing without deletion or overwrite;
- terminal handling for `success`, `refusal`, `failure`, `timeout`, `ambiguity`, `declined`, `hold`, `expired`, and `redirect`;
- terminal receipt then containment-completion receipt;
- requesting actual capability and global-lease release;
- containment survival until actual capability **and** lease release; issuer performs release, independent verifier confirms, clearance follows.

Current limits:

```text
acquisition_context=ABSENT
containment_control_channel=ABSENT
containment_readiness=ABSENT
containment_completion=NOT_CLAIMED
credential_act=UNPERFORMED
egress_act=UNPERFORMED
B_RUN_READY=false
GO=ABSENT
launch=UNPERFORMED
runtime_capability=NONE
```

This ACK accepts future bounded duty only. No launch, retry, resume, reacquisition, credential-value read/copy/hash/log, unrelated process/service control, release, clearance, or runtime act. C7 immutable custody/verification receipt remains separately required.

Self-verification: C6 commit/tree/parent/sole delta/blob/bytes/raw hash exact; clean worktree/index; eight canonical JSON hashes exact; named operator tuple exact.


````

### 4.3 Independent-verifier receipt — exact returned text

````text
# INDEPENDENT-VERIFIER RECEIPT

```text
receipt_status=PASS
receipt_type=INDEPENDENT-VERIFIER
verifier_task_id=019fe287-24a0-7d50-8e7d-0ff0d6b7c0ec
host_id=local

path=docs/campaign-records/2026-08-09-g2-p8-live4-global-lease.md
commit=cb064832c1bb66e8b69282a33a4604dc790c0334
tree=c0dc2797d1b4e78c27f76ba49f32084c1eeda608
blob=0711c8f4e680d8f706a879adf13916c86d2757de
bytes=24057
raw_sha256=755f23281b2699aa6b85e77b52f6c3b91738ca540dc68da98adc0e655c2e3580
direct_parent=06a28e88eb1cec5162f8cc1bd15bdaf21b8a5916
sole_delta=A docs/campaign-records/2026-08-09-g2-p8-live4-global-lease.md

lease_id=g2-p8-live4-051eb679-2fcf-4a2c-85c6-46c211feb983
lease_descriptor_sha256=663c82d9712f7b7d6d76452870641515ae394bdf3f6cf889973b481ea68c31e3

subject_descriptor_sha256=23039e68a5ddd718e8e39e37a4546941d75598df784913ec8a4ca42b0ef5be04
operator_assignment_descriptor_sha256=58878469d07d76cd13dcf2de628965a656e6ff8a623a76eb599ccf2c883dd6f6
resource_scope_descriptor_sha256=1c6a821db270d1548b1f44c287a9c1ec3b1b7b8120726deea98ba2ed94d06e0b
run_command_class_descriptor_sha256=85f2fdaa0f0924c295741047b14b2aae16c83974f78d5d91710c3c2c1a24634a
containment_class_descriptor_sha256=56ac14ef25f1593472afb5bfef733548596f04d1c8cbf859aae5f14672d9c6f4
lease_terms_descriptor_sha256=c6318f89c34f3d1b46e85b9752418788dcb717b5a27b7478775efe65e370d7aa
receipt_requirements_descriptor_sha256=8f73c0c8353438b1278b5b99a3f24278a07825ff27df6f2106aba41f57c9fd5e

issuer_task_id=019fe239-3c80-7f70-8a6e-29735e05e7b2
lease_state=ISSUED_PENDING_ACKS

issuance_interval_utc=[2026-08-09T20:51:13Z,2026-08-09T20:51:14Z)
issuance_ceiling_to_cutoff_seconds=321338
issuance_ceiling_to_expiry_seconds=407738
minimum_launch_final_ttl_seconds=86400

fresh_trusted_utc_interval=[2026-08-09T20:58:50Z,2026-08-09T20:58:51Z)
fresh_ceiling_to_cutoff_seconds=320881
fresh_ceiling_to_expiry_seconds=407281

canonical_json=PASS
duplicate_keys=NONE
root_leaf_bindings=PASS
self_hash_cycle=NONE
embedded_executable_command=NONE
embedded_credential_value=NONE
implicit_run_authority=NONE

required_before_b_run_ready_order=
1:c7_run_operator_ack
2:c7_containment_operator_ack
3:c7_independent_verifier_receipt
4:credential_placement_receipt
5:egress_arming_receipt
6:one_launch_authority_receipt
7:acquisition_context_custody_receipt
8:containment_control_channel_receipt
9:launch_final_identity_receipt
10:launch_final_time_ttl_receipt
11:launch_final_quiescence_receipt
12:containment_readiness_receipt

required_after_terminal_order=
1:terminal_receipt
2:containment_completion_receipt
3:capability_release_receipt
4:lease_release_receipt
5:clearance_receipt
```

Direct verifier determination: `PASS`.

This receipt verifies immutable C6 identity and descriptor integrity only. It supplies no operator ACK, credential, egress, one-launch authority, acquisition context, containment readiness, launch-final quiescence/TTL receipt, `B_RUN_READY`, GO, launch, retry, release, clearance, PR, merge, production, or Lane A authority.
````

## 5. C7 determination

The three required C7 receipts exist, directly bind the exact immutable C6 lease and all operative
hashes, and are recorded above without paraphrase. The run operator accepts only the symbolic
`project6.live4.single_wrapper_run.v1` class and will not act before all later receipts plus direct
exact issuer GO. The containment operator accepts the bounded future duty but confirms that the
acquisition context, control channel, and containment readiness do not yet exist. The independent
verifier returns `PASS` for the C6 Git/object/hash/time/ordering graph and makes no readiness or
launch inference.

The C6 descriptor's historical issuance state remains `ISSUED_PENDING_ACKS` in immutable C6 bytes.
This append-only C7 transition records the attained custody state as follows:

```text
state=GLOBAL_LEASE_ISSUED_ACKED
lease_state=LEASE_ISSUED_ACKED
lease_exists=true
run_operator_ack=RECORDED
containment_operator_ack=RECORDED
operator_acks=2/2
independent_verification_receipt=RECORDED
required_c7_receipts=3/3
credential_placement_receipt=ABSENT
credential_placement=UNPERFORMED
egress_arming_receipt=ABSENT
egress_arming=UNPERFORMED
one_launch_authority_receipt=ABSENT
one_launch_authority=UNSPENT_NOT_ISSUED
acquisition_context_custody_receipt=ABSENT
acquisition_context_custody=ABSENT
containment_control_channel_receipt=ABSENT
containment_control_channel=ABSENT
launch_final_identity_receipt=ABSENT
launch_final_time_ttl_receipt=ABSENT
launch_final_quiescence_receipt=ABSENT
containment_readiness_receipt=ABSENT
containment_readiness=ABSENT
B_RUN_READY_receipt=ABSENT
B_RUN_READY=false
orchestrator_GO_receipt=ABSENT
orchestrator_GO=ABSENT
launch=UNPERFORMED
terminal_receipt=ABSENT
containment_completion_receipt=ABSENT
capability_release_receipt=ABSENT
lease_release_receipt=ABSENT
clearance_receipt=ABSENT
B_CLEARANCE_RECORDED=false
Lane A=LOCKED
```

An ACK is acceptance of a bounded future role, not capability. Recording all three C7 receipts does
not discharge any later gate and does not make the system run-ready.

## 6. Remaining ordered gates and stop boundary

Before `B_RUN_READY`, separate immutable receipts remain required for:

1. credential placement without value disclosure;
2. egress arming;
3. one-launch authority;
4. acquisition-context custody;
5. containment control channel;
6. launch-final runtime identity;
7. launch-final trusted time and TTL;
8. launch-final external producer quiescence; and
9. containment readiness.

Only after those receipts may a distinct `B_RUN_READY` receipt be considered. Launch additionally
requires a direct exact issuer GO binding the immutable lease and every readiness receipt. This C7
record deliberately stops before all such acts.

Because C6 issued a lease, every later terminal disposition follows the lease-existed path even if no
launch occurs: terminal receipt, containment-completion receipt, actual capability release, global
lease release, independent release verification, and clearance. The no-lease clearance path is not
available.

## 7. Record fence and self-identity

This record cannot embed its own future Git blob, containing commit, or containing tree. It is valid
only if:

1. its direct parent is C6 `cb064832c1bb66e8b69282a33a4604dc790c0334`;
2. its sole path delta is this added C7 record;
3. C1 through C6 remain byte-identical to their bound identities;
4. the three direct source messages match their exact task IDs, item IDs, byte counts, LF/CR counts,
   and raw SHA-256 values recorded in section 4;
5. the operative lease ID, seven leaf hashes, and root hash match immutable C6;
6. the file is strict UTF-8 without BOM, LF-only, final-LF terminated, and has no trailing whitespace;
7. no executable command, credential value, credential access, egress, capability, runtime mutation,
   GO, or launch is embedded or performed by this record; and
8. the resulting worktree and index are otherwise clean.

A later record, if authorized, must bind this C7 record's derived path, commit, tree, blob, bytes, and
raw SHA-256. No self-pinning follow-up is required merely to make C7 valid.

## 8. Non-claims

This record claims only direct custody of the exact two operator ACKs and one independent-verifier
receipt required by immutable C6. It claims no continuing operator availability; credential access or
value; credential placement; egress; one-launch authority; acquisition context; containment control
channel; current producer quiescence; launch-final identity or TTL; containment readiness;
`B_RUN_READY`; issuer GO; launch, run, retry, resume, replacement, or second launch; P5-live runtime
verification; dual PASS; terminal status; containment completion; actual capability or lease release;
clearance; PR-ready, merge, main, production, or Lane A authority. It executes no runtime action.
