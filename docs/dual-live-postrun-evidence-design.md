# Dual-Live Post-Run Evidence Design

Status: owner-approved G1 Option-A approach; detailed design pending owner review

Scope: offline producer/quiescence evidence substrate, protected post-run
attestation, deep Task-8 evaluation, and validate-only gate integration

Frozen baseline: `docs/superpowers/plans/2026-07-29-dual-live-proof.md`

## 1. Authority and purpose

This document specifies the additional evidence substrate authorized after the
G1 review proved that the existing four-log manifest, seal, and ordinary DB seal
events could not independently establish three Task-8 facts:

1. startup logger custody;
2. Phase-A and Phase-B child/process/socket quiescence; and
3. detection of a coordinated rewrite spanning logs, manifest, seal, and the DB
   seal events.

This document supplements the frozen Task-8 requirements. It does not edit,
supersede, weaken, or reinterpret the frozen plan or any campaign record. If an
implementation choice conflicts with the frozen plan, implementation stops and
records the conflict. The stricter fail-closed requirement governs until the
owner resolves it.

The deliverable is G1's offline substrate. It does not authorize live
acquisition, credentials, egress, deployment, push, production promotion, or a
claim that a real ScienceBase/NRC campaign has run. `run-dual-live-proof` remains
an exact default-refusing action during this tranche. Tests use isolated fake
children, fake metadata, sentinel values, and loopback-only socket fixtures.

## 2. Existing evidence and the missing edge

Current capture code creates exactly four streams, then publishes the manifest,
the seal, and matching per-run DB seal events:

```text
four logs -> manifest -> seal <-> ordinary DB seal events
```

The manifest and seal contracts are in `backend/app/schemas/api.py:705-805`.
Publication occurs in
`backend/app/services/connector_campaign_log_capture.py:1715-1900`. The seal
events are ordinary rows written by
`backend/app/services/connector_campaign_log_capture.py:1560-1712`.

Create-new publication prevents name reuse during issuance, but it does not
make later bytes independently immutable. Rewriting the four files, manifest,
seal, and DB events coherently can preserve their internal parity. A final
one-way edge must therefore bind the completed filesystem and DB domains to a
separately pinned post-run authority:

```text
runtime records
  -> manifest
  -> seal + DB seal events
  -> post-run attestation
  -> protected attestation-index head digest
```

There is no reverse link from the earlier frozen seal or preflight evidence
index to the later post-run attestation. The attestation necessarily binds
those earlier objects; adding an attestation hash back into either earlier
object would create recursive evidence rather than independent protection.

## 3. Selected design and rejected alternatives

### 3.1 Selected: protected post-run attestation index

The selected design uses:

- structured wrapper-owned runtime records inside the existing four sealed
  streams;
- a content-addressed post-run attestation created only after the seal events
  have committed and all referenced state is stable;
- a separate append-only attestation-index chain retaining one exact
  attestation reference per campaign; and
- an environment-only configured head SHA-256 whose content-addressed path is
  derived by a fresh validation process.

This requires no signing secret and retains historical failed, expired, and
replacement campaigns without rotating away their evidence.

### 3.2 Rejected: extend the preflight evidence index

The existing index introduces one complete new campaign slice per successor.
Adding a post-run object for an already-introduced campaign would change that
invariant and combine pre-run send authority with post-run validation authority.
The wider governance and regression surface is unnecessary.

### 3.3 Rejected: signature, HMAC, or WORM service

A signer or WORM service can provide stronger external nonrepudiation, but it
adds key custody, recovery, rotation, service availability, and credential
handling. Those properties are beyond this local offline experiment and are not
required to detect post-pin coordinated rewrites.

### 3.4 Rejected: create-once file or additional DB event alone

Create-once protects initial publication, not permanent custody. An additional
event remains in the same mutable DB domain. Neither supplies an independent
expected value.

### 3.5 Rejected: independently pin only one attestation digest

Directly pinning one content-addressed attestation digest is sufficient to
protect one named campaign and is the simpler design for that narrower goal. It
does not establish which other failed, expired, or replacement campaign
attestations existed, prevent invocation-by-invocation omission of those
objects, or provide one head from which the exact two- and three-campaign
historical unions can be rederived. Supplying a protected list of direct pins to
close those gaps recreates an index without predecessor continuity.

The cumulative index is retained because this tranche requires one configured
head to bind the complete append-only campaign history and its exact selected
union, not merely integrity of one caller-selected object. That benefit carries
the explicit operational costs in Sections 6.2, 6.4, and 14; if complete-history
validation is later removed, direct per-campaign pinning becomes the preferred
narrower design.

## 4. Trust domains and threat model

The design separates five domains:

1. **Trusted code:** the reviewed code revision and this contract.
2. **Preflight authority:** the protected campaign definition, grants,
   consumption markers, and preflight evidence-index chain.
3. **Runtime evidence:** the isolated DB, storage, four logs, manifest, seal, and
   DB seal events.
4. **Post-run authority:** a separate operator-provisioned attestation root and
   protected attestation-index head digest.
5. **OS observations:** Windows Job Object membership/accounting, process
   identity, campaign and post-run-root mutex state, and owner-PID socket tables.

After a trusted index-head digest is pinned, validation must detect:

- a change to any indexed runtime log;
- coordinated log and manifest changes;
- coordinated log, manifest, and seal changes;
- matching insertion, deletion, or rewriting of run/seal-event rows;
- replacement, deletion, rollback, fork, or repointing of the attestation or
  attestation-index chain; and
- concurrent runtime activity while validation is reading evidence.

The design does not claim protection if an attacker controls the trusted code,
the process environment that supplies the pinned head, the Windows account that
owns the evidence process, or the operator who pins already-forged evidence. It
does not claim a trusted timestamp, nonrepudiation, WORM durability, physical
secret erasure, machine-global log visibility, or protection from hardware
failure.

## 5. Configuration and custody boundary

Add post-run fields with exact process-environment aliases:

```text
DUAL_LIVE_POSTRUN_MODE
CONNECTOR_CAMPAIGN_POSTRUN_EVIDENCE_ROOT
CONNECTOR_CAMPAIGN_POSTRUN_INDEX_SHA256
DUAL_LIVE_VALIDATE_ONLY_PROCESS
DUAL_LIVE_SCAN_NRC_KEY
```

`DUAL_LIVE_POSTRUN_MODE` is exactly `disabled`, `issue`, or `verify` and defaults
to `disabled`. Mode is never inferred from missing fields:

- `disabled` requires every post-run root/index field and the scan-only key to
  be absent and cannot produce or validate an accepted result;
- `issue` requires the root; SHA is absent for revision 1 or present as the
  exact predecessor head for a successor; the scan-only key is forbidden; and
- `verify` requires the root, SHA, and a nonempty scan-only key together
  and is strictly read-only.

The root is an absolute, pre-existing, non-reparse directory. The head path is
never configured or accepted from a caller; it is derived exactly as
`indexes/<configured_sha256>.json`. The post-run root must be mutually
non-nested with the repository, runtime storage, SQLite DB parent, and preflight
evidence root. Alternate data streams, symlinks, reparse points, hard-link
substitutions, traversal, case aliases, and fallback paths fail closed.

The gate sets `DUAL_LIVE_VALIDATE_ONLY_PROCESS=1` before importing application
configuration. In that posture, the global `Settings` instance and the explicit
instance passed to the evaluator must ignore `backend/.env` and load only the
current process environment. Any helper reused by the evaluator must accept the
explicit `Settings` object or an immutable verified value derived from it. It
must not consult the normal global settings object.

`DUAL_LIVE_SCAN_NRC_KEY` is scan-only input. It is never exposed to connector
transport, emitted, persisted, or returned. The standard NRC subscription-key
variable and every current campaign/grant path or digest remain forbidden in
the validator. Tests supply a unique fake sentinel; this tranche uses no real
credential. The variable name denotes only that offline sentinel in G1. Real
campaign key injection, lifetime, process isolation, and crash-dump posture are
not authorized by this design and require separate governance before any live
validation.

## 6. Post-run contracts

### 6.1 Attestation reference

Each index entry contains exactly:

```text
campaign_id
campaign_fingerprint
campaign_definition_sha256
code_revision
attestation_relative_path
attestation_sha256
```

The relative path is
`attestations/<campaign_fingerprint>/<attestation_sha256>.json`. Campaign ID,
fingerprint, definition hash, and code revision form the unique campaign key.

### 6.2 Attestation-index chain

Each canonical index revision contains:

```text
schema_id = project6.connector_campaign_postrun_index.v1
revision
predecessor_index_relative_path | null
predecessor_index_sha256 | null
attestations[]
```

Its content-addressed path is `indexes/<index_sha256>.json`; the digest is over
the exact canonical bytes. Revision 1 requires empty managed subtrees except for
the exact Section-6.4 attestation-only adoption candidate. A successor requires
the configured SHA to resolve to the unique maximal predecessor before any new
bytes are staged.

Revision 1 has no predecessor. Every successor names the exact prior raw digest
and path, preserves all prior entries byte-for-byte and in order, and appends
exactly one complete new campaign entry. Duplicate campaign keys, duplicate
paths or hashes, mutation, deletion, relabeling, gap, fork, rollback, partial
addition, orphan attestation, or a configured head that is not the unique
maximal revision fails closed.

The managed `indexes/` and `attestations/` subtrees are exhaustive, not
intentionally partial. Their permitted files are exactly the configured
gap-free index chain and the attestation objects referenced by that chain.
Every undeclared file, directory, alternate stream, or stage residue fails
`verify` closed. `Issue` recognizes only the exact attestation-only adoption
case in Section 6.4; every other orphan fails closed.

The index never grants permission to arm, reserve, send, parse, submit, or
mutate. Expired evidence remains evaluable without becoming current authority.

### 6.3 Post-run attestation

The canonical attestation is strict JSON, rejects extra fields, is at most
64 KiB, has no self-hash field, and contains:

- schema ID, campaign ID/fingerprint/definition hash, and code revision;
- campaign-introduction index revision/digest and observed preflight head
  digest;
- runtime-instance UUID and wrapper executable SHA-256;
- the ordered wrapper-record chain head and record count;
- Phase-A and Phase-B child identity hashes, process-boot IDs, exit codes,
  logger-census hashes/results, Job-zero results, and socket-census
  protocol/state counts plus summary hashes;
- an authority-posture hash containing field names and safe presence booleans,
  never values or paths;
- the exact `http.jsonl` SHA-256, counter-record count, runtime-instance ID, and
  singleton Phase-A process-boot ID;
- manifest relative path/digest and file-set hash;
- seal relative path/digest and sorted extant connector-run IDs;
- deterministic per-run seal-event IDs and canonical full-row hashes;
- a canonical post-seal DB snapshot hash over the complete `ConnectorRun` rows
  and every `ConnectorRunEvent` row for the extant run set, including every
  mapped scalar and JSON column in deterministic order; and
- the exact Section-6.3.1 attested projection binding the remaining durable
  ledger, origin, downstream, package, and classified-file closure.

The attestation contains no URL, query, fragment, header/key value, credential,
command line, endpoint, raw source bytes, absolute path, or database DSN.

#### 6.3.1 Canonical hash contract

Every new v1 digest uses SHA-256 over exact UTF-8 canonical JSON bytes and is
lowercase hexadecimal. Canonicalization recursively applies these rules:

- mappings require string keys and serialize in code-point key order;
- arrays preserve declared order;
- aware datetimes normalize to UTC as `%Y-%m-%dT%H:%M:%S.%fZ`;
- UUIDs use lowercase canonical text;
- null, booleans, strings, and integers retain their JSON values;
- finite floats retain Python's JSON numeric form; non-finite values, naive
  datetimes, paths, bytes, sets, unknown objects, duplicate JSON keys, and extra
  schema fields are rejected; and
- serialization uses `ensure_ascii=False`, `allow_nan=False`, sorted keys, and
  separators `(',', ':')`, with no BOM or trailing newline.

Parity tests bind these rules to the existing
`connector_egress_authorization.canonical_json_bytes` behavior for every shared
type. New evidence code must not import a helper that reads global settings or
performs bootstrap side effects.

Mapped DB rows normalize as strict objects whose keys are sorted mapped column
names. Rows sort by fully qualified model name, then canonical primary-key
tuple; JSON columns recursively use the rules above. Deferred, unloaded,
unknown, unsupported, duplicate, or non-finite values make the snapshot
`INDETERMINATE`; they are never omitted. The bounded row closure includes every
mapped row actually consumed by stages 5 through 12, not only
`ConnectorRun`/`ConnectorRunEvent`.

The attestation contains exactly one
`project6.dual_live_attested_projection.v1` object with these keys:

```text
schema_id
campaign_id
campaign_fingerprint
preflight_chain_sha256
runtime_chain_sha256
manifest_sha256
file_set_sha256
seal_sha256
sealed_run_ids
sealed_row_snapshot_sha256
ledger_union_sha256
origin_continuity_sha256
downstream_closure_sha256
package_closure_sha256
classified_file_set_sha256
```

Each closure hash is over a named strict projection implemented once in the
read-only evidence kernels and reused by issuer and evaluator. The package and
classified-file projections contain relative identity, kind, byte length, and
fresh SHA-256 for every bounded object outside the post-run root; the downstream
projection includes the Layer-3 execution, review, submit-response, and
handoff-prepared durable row closure. The projection contains no scan sentinel
or custody verdict: issuance has no credential-like input. Instead, it binds all
non-post-run bytes that verification later scans. Evaluation stage 13 compares
the freshly rederived exact projection bytes--not the broader status report--to
this attested projection.

The post-run root is deliberately excluded from `classified_file_set_sha256` to
avoid self-reference. Its exact index and attestation bytes are separately bound
by the content-addressed chain and configured head. Verify-mode custody scanning
still scans every classified post-run file after that chain is loaded; issuance
performs only structural/hash validation of the predecessor root and newly
created candidate.

The authority-posture projection has a separate fixed field-name list:
`CONNECTOR_LIVE_EGRESS_ENABLED`, all six campaign-definition/grant path and hash
variables, and `NRC_ADAMS_APS_SUBSCRIPTION_KEY`. It records only normalized
presence/false-state booleans and a hash of their canonical object. The offline
scan sentinel is excluded because it grants no transport authority in G1.

### 6.4 Issuance

Issuance is a fresh offline process with live egress disabled, send-capable
authority absent, no active runtime mutex owner, and no connector credential.
It performs this sequence:

1. acquire and retain the post-run-root mutex, then the campaign mutex, in that
   fixed order;
2. require an already-closed isolated SQLite DB in `journal_mode=DELETE`, with
   no `-journal`, `-wal`, or `-shm` sidecar, retain the same no-write/no-delete
   Windows handle used by verification, then record its stable raw identity;
3. strictly re-read the preflight chain, four logs, manifest, seal, and DB;
4. require the exact terminal/seal-event set, derive the post-seal snapshot, and
   derive the complete Section-6.3.1 attested projection;
5. create the canonical content-addressed attestation with atomic strict-new
   publication;
6. create the next canonical attestation-index revision with atomic strict-new
   publication;
7. re-read both publications, rederive the DB snapshot through a fresh read-only
   connection, require unchanged DB/sidecar identities, print only public
   digests and campaign identities; and
8. release the mutex.

An issued but unpinned index is `ISSUED_UNPINNED` and can never validate as
`PASS`. The operator independently rehashes the head and supplies its digest to
a fresh `verify` process, which derives the content-addressed path. Issuance
never changes its own mode or configuration to validate what it wrote.

Only an already-complete attestation/index pair whose exact final bytes both
match is reconciled read-only, and it is never treated as newly issued. One
bounded recovery exists for an attestation-only orphan: a fresh `issue` process
can publish its missing index revision only when it rederives the exact
attestation bytes from unchanged protected sources, the content-addressed path
and digest match, the configured predecessor is still the unique head, and no
stage residue or conflicting final exists. The result is `ADOPTED_UNPINNED`,
never `PASS`, until the operator independently pins the adopted head.

An index-only orphan, conflicting final, stage residue, changed predecessor,
fsync/rename ambiguity, or any orphan that cannot meet all adoption predicates
is `PUBLICATION_AMBIGUOUS`. No final path is overwritten, deleted, or retried in
place. The operator must provision a fresh post-run root/epoch and rerun the
campaign; the ambiguous root is retained for diagnosis.

## 7. Wrapper-owned runtime evidence

### 7.1 Process containment

Phase A and Phase B use separate unnamed Windows Job Objects. Each Job is
configured with kill-on-close and no breakaway. The controller creates the
child atomically into the Job with an extended startup attribute list; it does
not create the process and assign it later. The child inherits only its exact
pipe handles and Phase-A revocation/send-idle event handles, never the Job handle
or a log-file handle. The bootstrap immediately makes inherited handles
non-inheritable so a grandchild cannot receive them.

Unsupported Windows versions, nested-Job incompatibility, Job configuration
failure, identity ambiguity, or inability to read back required properties fail
before child creation. There is no PowerShell, `taskkill`, or `psutil` fallback
for acceptance evidence.

### 7.2 Wrapper-only streams and protocol

The existing capture service continues to own the exact four files:

```text
app.jsonl
http.jsonl
stdout.log
stderr.log
```

Children receive bounded pipe endpoints. The wrapper alone writes disk.
`http.jsonl` accepts only strict counter frames; application and HTTP-library
logging belongs in `app.jsonl`. Child frames cannot use reserved wrapper schema
IDs. Pipe backpressure, invalid UTF-8, malformed frames, overlong frames,
unexpected EOF, or writer failure triggers the single stop latch.

#### 7.2.1 Runtime-record chain

Reserved wrapper evidence appears only in `app.jsonl` and uses
`project6.dual_live_runtime_record.v1` with this exact envelope:

```text
schema_id
ordinal
runtime_instance_id
phase
event
process_boot_id | null
previous_record_sha256 | null
payload
record_sha256
```

`ordinal` starts at 1 and is gap-free across both phases. The first predecessor
is null; every later predecessor equals the prior record hash. `record_sha256`
is SHA-256 over the Section-6.3.1 canonical envelope with only that field
removed. `phase` is exactly `wrapper`, `A`, or `B`. Child frames cannot select
this schema, ordinal, predecessor, or hash; the wrapper constructs all four.

The strict event union and required payloads are:

| Event | Required payload |
|---|---|
| `runtime_start` | `code_revision`, `wrapper_image_sha256`, `interpreter_image_sha256`, `mutex_identity_sha256` |
| `phase_child_start` | `process_creation_identity_sha256`, `executable_sha256`, `job_policy_sha256` |
| `logger_census` | `census_point`, `topology_sha256`, `handler_count`, `guard_state`, `topology_matches_initial` |
| `phase_go` | `prior_state`, `next_state`, `control_nonce_sha256` |
| `stop_latched` | `reason_code`, `monotonic_tick_ns` |
| `socket_census` | `tcp4_state_counts`, `tcp6_state_counts`, `udp4_count`, `udp6_count`, `process_identity_sha256`, `stable` |
| `job_zero` | `active_process_count=0`, `process_list_sha256` |
| `authority_cleared` | `authority_posture_sha256`, `all_required_absent` |
| `phase_complete` | `terminal_state`, `exit_code` |
| `runtime_complete` | `phase_a_result_sha256`, `phase_b_result_sha256`, `terminal_state` |

Each payload is a strict discriminated schema; the table is exhaustive, not a
minimum-key list. Field names are the snake-case names shown. Every `hash` is a
lowercase SHA-256, IDs are canonical UUIDs, counts/ticks are nonnegative
integers, booleans are literal, FSM states and reason codes are closed enums,
and each socket state-count object has the exact Windows MIB state keys plus
nonnegative counts. `census_point` is exactly `pre_activity` or `exit`. A passing
record sequence is also exact: runtime start; Phase-A child/pre-census/go/exit-
census/socket/job/authority/complete; Phase-B child/pre-census/go/exit-census/
socket/job/complete; runtime complete. A passing sequence has no `stop_latched`
record. When the app writer remains usable, a failure persists its first-stop
record before teardown. If writer failure prevents that record, the capture
remains incomplete and unaccepted: it is never sealed/attested as success and a
later gate/evaluator returns `REFUSED` or `INDETERMINATE`, never `PASS`.

### 7.3 Logger census

The child bootstrap installs the exact campaign pipe handlers, configures the
application under the accidental-call guards, and performs a census before the
wrapper releases the child to perform any marker, run, reservation, or send
activity.
It enumerates the root logger, every real logger and placeholder, propagation,
disabled/effective levels, filters, `logging.lastResort`, and every handler.

Only the exact campaign pipe handlers, wrapper-owned stdout/stderr streams, and
sinkless exact `NullHandler` instances are permitted. File, stream-to-unknown,
queue, memory-target, socket, HTTP, SMTP, event-log, arbitrary subclass,
duplicate effective sink, or unknown handler state fails startup. A final
census must equal the protected topology. The bootstrap locks normal handler
mutation APIs after startup; direct in-process list mutation is not presented
as an OS security boundary and is checked again at exit. Each phase emits both
the pre-activity and exit census; the exit record must match the initial
topology exactly.

#### 7.3.1 Phase-control state machines

Runtime bootstrap does not reuse the validator's permanent monkeypatch state.
Phase A uses this exact one-way FSM:

```text
A_BOOT_DENY -> A_CENSUS_OK -> A_GO -> A_EGRESS_ENABLED -> A_STOPPED
            \-> A_ABORTED
```

The child installs reversible accidental-call guards, completes configuration,
emits its census frame, and blocks in `A_CENSUS_OK`. The wrapper validates and
persists that census, then sends exactly one nonce-bound `A_GO` control frame on
the private pipe. Only the child bootstrap can consume it and restore the saved
standard socket/DNS/Requests functions plus enable the connector transport
policy gate. A duplicate, early, malformed, or late GO latches stop. Any send
before `A_EGRESS_ENABLED` or after stop is denied and latched. The stop latch
sets the inherited Windows manual-reset revocation event before the Job is
terminated; there is no transition back to an enabled state.

The connector transport serializes physical sends. Under its send lock it checks
the revocation event before reservation, resets the inherited send-idle event to
acquire the one-send lease, checks revocation again immediately before the
physical-send boundary, and signals send-idle in `finally`. If revocation is set
at either check, no send begins. A send that passed the second check before
revocation is explicitly in flight; revocation does not claim to cancel its OS
I/O. Its terminal counter/ledger evidence must complete and the stop-boundary
ordering is recorded. An abnormal stop with an in-flight or incomplete send is
`FAIL` when complete evidence proves it and otherwise `INDETERMINATE`; it can
never `PASS`.

G1 tests inject only fake connector transport and loopback fixtures at the
`A_EGRESS_ENABLED` transition. Enabling real external transport is not
authorized here and requires the separately reviewed live runner.

Phase B uses:

```text
B_BOOT_DENY -> B_CENSUS_OK -> B_GO -> B_ACTIVE -> B_STOPPED
            \-> B_ABORTED
```

`B_GO` releases local parsing/evaluation only. Phase B has no egress-enable
transition, no saved credential, no grant path/hash, and permanent standard and
connector accidental-call guards. Tests prove pre-GO denial, exactly-one A-GO,
post-stop A denial, absence of a B enable edge, and denial after every failure.

### 7.4 Runtime and process-boot identity

The new record is `project6.connector_http_counter.v2`: the exact v1 key set plus
`runtime_instance_id` (canonical UUID) and `process_boot_id` (lowercase SHA-256).
The boot ID binds the wrapper nonce, OS PID, OS process-creation identity, and
executable hash. A record from more than one runtime instance or boot makes
spacing and campaign evaluation `INDETERMINATE`.

Both exact-key consumers--`connector_egress_transport.py` and
`connector_egress_arming.py`--must accept v1 or v2 explicitly. Mixed schemas,
mixed runtime IDs, or mixed boot IDs inside one sealed counter file are invalid.
Historical v1 fixtures and non-campaign behavior remain readable and green, but
v1 lacks boot proof and therefore cannot make a new deep evaluation `PASS`.
Campaign writer/constructor plumbing emits v2 only when the wrapper supplies an
immutable runtime context; it never guesses identity from the current process.

This closes the current ambiguity in
`backend/app/services/connector_egress_transport.py:132-148` and
`backend/app/services/connector_egress_arming.py:478-495`, whose exact v1
contracts record monotonic readings without their process-clock identity.

### 7.5 Stop and quiescence

The wrapper uses one atomic first-stop latch for abnormal termination only.
Unexpected or nonzero primary exit, protocol/census/pump failure, timeout,
operator stop, or console close sets it and blocks every later transition,
including Phase B. A clean Phase-A exit instead closes its connector policy
gate by setting the same revocation event, requires send-idle and terminal
counter evidence, performs the exit census, and enters the planned quiescence
sequence without setting the global stop latch. Both paths set revocation before
terminating the entire active Job once, wait for retained process handles, and
require Job accounting and the Job PID list to reach zero. Event failure or
send-idle timeout fails closed and prevents Phase B.

Socket census uses Windows owner-PID TCP4, TCP6, UDP4, and UDP6 tables while the
Job remains open. It records only protocol/state counts and a retained-process
identity hash, never addresses, ports, or hashes derived from endpoint tuples.
Listening, connection-progress, established, incomplete-teardown, or UDP
ownership fails quiescence; `TIME_WAIT` is counted but allowed. API churn, PID
reuse ambiguity, inaccessible ownership, or an unstable census is
`INDETERMINATE`.

Only `JOB_ZERO + SOCKET_QUIESCENT + AUTHORITY_CLEARED` permits Phase B. Phase B
uses a new Job, an explicit secret-free environment allowlist, live egress
false, the pre-import accidental-call guards, and the subprocess-denial guard.
Those Python/socket/Requests/connector guards are defense in depth, not an OS
network-isolation boundary. The G1 proof covers the standard application paths;
hostile native calls, `ctypes`, and alternate transports remain nonclaims. A
future live runner requires separately reviewed OS firewall or sandbox
isolation.

The wrapper claims semantic capability extinction: Phase-B lacks the Phase-A
key and send authority. It does not claim forensic erasure from Python memory,
page files, crash dumps, or prior external copies.

### 7.6 Lock hierarchy

The wrapper, issuer, and validator use the same campaign-scoped mutex inside a
Windows private namespace whose boundary descriptor contains the current user
SID. Namespace and mutex handles are non-inheritable; their explicit security
descriptor grants only that SID and `SYSTEM`. One deterministic namespace name
binds the fixed Project6 dual-live domain and SID-boundary descriptor. Within it,
the campaign mutex name hashes campaign ID, fingerprint, and campaign-definition
SHA-256, but not code revision. Protected runtime records bind the namespace and
mutex names, SID, descriptor, wrapper-nonce, code revision, and creator process
identities through one-way hashes; they expose none of those raw values.

Every participant atomically creates or opens that exact namespace, validates
its effective descriptor, creates or opens the exact mutex, and attempts a
zero-time acquisition. Newly created objects receive the exact descriptor;
existing objects with any different descriptor fail closed. `WAIT_OBJECT_0`
permits work, `WAIT_TIMEOUT` means another participant is active, and
`WAIT_ABANDONED`, access failure, or identity mismatch fails closed. The wrapper
does this before capture creation and retains ownership through final closeout;
issuer and validator retain ownership through their final stable reread. Active
runtime is `REFUSED`. This prevents cross-session accidental concurrency and
same-account accidental collision, but it is not protection against compromise
of the owning Windows account.

Issuer and validator additionally serialize the cumulative index through one
post-run-root mutex in the same SID-bound namespace. Its name hashes the retained
canonical directory identity--volume serial, directory file ID, normalized
final path, and security-descriptor hash--so every campaign sharing that physical
root contends on one object. They retain a non-reparse directory handle that
denies deletion while the mutex exists.

Lock order is always root mutex, then campaign mutex; release is the reverse.
The wrapper acquires only the campaign mutex. Issuer and validator use zero-time
acquisition and retain both locks through their final rereads. Root contention,
abandonment, identity/ACL mismatch, or inability to retain the directory handle
is `REFUSED` before evaluation/publication. This serializes issuers for different
campaigns, prevents sibling successors from one predecessor, and prevents a
validator from racing any issuer on the same root.

## 8. Read-only evaluator architecture

### 8.1 Component boundaries

Keep each new unit focused:

- `dual_live_runtime_evidence.py` owns strict runtime-record schemas, record
  chaining, pipe framing, logger census, and safe authority-posture projections.
- `dual_live_windows_supervisor.py` owns Job Objects, atomic child creation,
  retained process identity, mutexes, stop latching, and socket census.
- `dual_live_controller.py` owns the wrapper FSM, one-use control frames, pump
  ordering, and the only disk writers.
- `dual_live_child_bootstrap.py` owns child guard transitions, logger census,
  private-pipe framing, and the immutable runtime context.
- `dual_live_postrun_evidence.py` owns attestation/index schemas, strict-new
  issuance, protected-chain loading, and post-seal DB snapshot projection.
- `dual_live_evidence_checks.py` owns explicit-context read-only authority,
  ledger/counter, continuity, downstream, package, and custody kernels.
- `dual_live_evaluator.py` only orchestrates those kernels and constructs the
  fixed secret-safe report.
- `tools/dual_live_issue.py` owns the writeful post-run issuer CLI and no other
  runtime, DB, or artifact mutation.
- `tools/dual_live_gate.py` owns process posture, pre-import accidental-call
  guards, environment-only settings, mutex lifetime, read-only SQLite, stdout,
  and exit codes.

Existing capture, transport, configuration, PowerShell, and tests change only
where these interfaces require them. No unrelated framework extraction is
part of this design.

### 8.2 Evaluation stages

`evaluate_dual_live_proof` retains the exact frozen public signature. It never
creates, updates, deletes, repairs, normalizes, seeds, checkpoints, or publishes
a row or artifact.

The evaluator executes fixed stages:

1. validate canonical campaign inputs and explicit environment-only settings;
2. load and rehash the unique-maximal preflight evidence-index chain;
3. load and rehash the unique-maximal post-run attestation-index chain;
4. select the exact per-campaign `1 definition + 2 grant refs + 1 capture ref +
   1 attestation ref` slice and, in the two-campaign lifecycle proof, the exact
   `2 + 4 + 2 + 2` selected union without orphan or cross-campaign aliases;
5. rederive manifest/file-set/seal/extant-run/seal-event/attestation parity;
6. verify original definition/grant bytes, arming fields, exact marker bytes and
   hash, deterministic run ID, nonce, `max_armings=1`, original half-open
   windows, terminal cardinality, stored status, lease extinction, and absence
   of post-terminal failure or reacquisition evidence;
7. derive each terminal request ledger and reconcile the union of both run
   ledgers against the entire sealed `http.jsonl`, rejecting every missing,
   duplicate, extra, foreign, reordered, or disagreeing record while also
   verifying host/method/path/credential policy and fresh `200` byte evidence;
8. rederive counted bytes, the single-send allowance classification, and
   same-process monotonic spacing;
9. independently rederive NRC-first parent run/hash binding;
10. rederive raw/provenance/version/content-linkage and the single canonical
    origin receipt plus all downstream projections without trusting stored
    `proof_class`, ledger, receipt, URL, artifact, or package hashes;
11. verify Layer 3C execution, review, the exact `canonical_internal`,
    `user_facing`, and `review_facing` package kinds, package bytes, submit
    response, and handoff-prepared response;
12. run the bounded custody scanner across mapped DB values, API/event/report
    projections, all classified non-source files, and the sealed four logs;
13. compare the exact Section-6.3.1 attested projection with the protected
    post-run attestation;
14. end the first SQLite read transaction, compare same-connection
    `data_version`, repeat the complete semantic snapshot through a fresh
    read-only connection, and repeat all protected-file, DB-file, and sidecar
    identities before returning.

Implementation extracts only the required explicit-context read-only kernels
from:

- `connector_egress_authorization.py` for index chains and historical grants;
- `connector_egress_transport.py` for terminal-ledger and counter derivation;
- `layer3_origin_continuity.py` for origin receipt/continuity checks; and
- `layer3_package_entry.py` for package-byte verification.

The evaluator must not call arming, send, mint, materialize, package creation,
submission mutation, capture sealing, or directory-creating helpers.

### 8.3 Fixed resource ceilings

The G1 constants are not caller-configurable. Nothing is truncated, sampled, or
skipped:

- 4 KiB per control frame, 64 KiB per evidence/log frame, 10,000 frames per
  stream, the existing 16 MiB per-stream ceiling, and the existing 32 MiB
  aggregate ceiling across the four sealed streams;
- 1 MiB per index object, 64 KiB per attestation, 1,024 index revisions/entries,
  4,096 managed post-run files, and 512 MiB in the managed post-run root;
- 100,000 mapped DB rows in the bounded closure, 8 MiB per scalar/JSON value,
  and 256 MiB of canonical row-snapshot bytes;
- 10,000 classified files and 512 MiB across all custody-scanned roots, with
  raw-source exemptions counted for classification but not content scanning;
- 4,096 derived forbidden tokens, 4 KiB per token, 32 container/decoding depth,
  and exactly the raw/JSON/HTML/percent once/percent twice variants; and
- 600 seconds total evaluator wall time, 120 seconds per fake child, and 30
  seconds for each Job/socket quiescence convergence.

Counts are checked before allocating or reading the next item. Tests exercise
each equality boundary and its first-over-limit value. Increasing a ceiling is
a reviewed contract change, not an operator override.

Limit outcomes depend on the phase and are exact:

| Phase | Limit outcome |
|---|---|
| Runtime producer | A frame/stream/child/quiescence breach latches abnormal stop and is `FAIL` when the sealed evidence is complete. Writer failure that leaves capture unsealed is gate-level `REFUSED`; a present seal whose protected runtime record is missing/mismatched is evaluator-level `INDETERMINATE`. Neither can `PASS`. |
| Evaluator | Inspection, row/file/token, or evaluator-time limit is `INDETERMINATE`; the evaluator emits no partial verdict. |
| Issuer before any final publication | Unsafe or over-limit input is `REFUSED`; no final file is created. |
| Issuer after a final publication or uncertain rename/fsync | The result is `PUBLICATION_AMBIGUOUS`. Recovery follows Section 6.4 exactly: complete-pair reconciliation; attestation-only adoption; otherwise a fresh root/epoch and rerun. |

The issuer never emits `INDETERMINATE`, and a producer's proven protocol or
quiescence violation is never relabeled as evaluator uncertainty merely because
the same numeric ceiling is involved.

## 9. Custody scanner

The scanner implements the frozen bounded algorithm through Task-8 line 2512.
It derives finite forbidden URL/query/header candidates from protected
definition/grant rules and the fake or scan-only NRC key. For every bounded
string/token it scans raw, JSON-unescaped, HTML-unescaped, and percent-decoded
once and twice forms. Invalid encoding or a residual third escape layer fails
closed.

The DB scan enumerates mapped SQLAlchemy scalar, text, and JSON columns for the
campaign-related row closure rather than assuming URL data lives in known JSON
fields. The file scan begins from explicit isolated snapshot, report,
generated-artifact, log, and post-run roots. Every encountered regular file
must be classified before content is read.

API surfaces are scanned by invoking their canonical read-only serializers over
the frozen DB snapshot, not by starting a server or issuing HTTP requests.

Only the exact admitted raw source blobs are exempt from content redaction, and
only when storage refs and freshly rehashed bytes match the continuity receipt.
Their paths and surrounding metadata remain in scope. Hits report sink class,
relative identity, byte offset, and a one-way digest only.

## 10. Issuer and gate behavior

### 10.1 Writeful post-run issuer

`tools/dual_live_issue.py` is the sole executable owner of Section 6.4. The
PowerShell action is `issue-dual-live-evidence`; like validation, it accepts no
free-form `ActionArgs` and obtains campaign ID/fingerprint from
`DUAL_LIVE_CAMPAIGN_ID` and `DUAL_LIVE_CAMPAIGN_FINGERPRINT`. It requires
`DUAL_LIVE_POSTRUN_MODE=issue`, the exact root/predecessor posture in Section 5,
an existing isolated SQLite URL, and no scan sentinel, connector credential,
current send grant, or live-egress flag.

The issuer imports only environment-only settings and the read-only evidence
kernels. Its write fence is the configured post-run root; DB, runtime storage,
logs, manifest, seal, packages, source blobs, repository, and preflight root are
read-only. It never invokes the validate-only gate or changes mode in-process.

It emits one canonical JSON line with schema
`project6.dual_live_postrun_issue.v1` and exact keys:

```text
schema_id
campaign_id
campaign_fingerprint
status
code
predecessor_index_sha256 | null
attestation_sha256 | null
index_sha256 | null
```

Status is exactly `ISSUED_UNPINNED`, `ADOPTED_UNPINNED`,
`PUBLICATION_AMBIGUOUS`, or `REFUSED`. Public digests are permitted; paths,
source/DB values, exceptions, credentials, and DSNs are not. Exit 0 means issued
or adopted; exit 2 means ambiguous or refused. There is no issuance `PASS`, and
operator pinning plus a new verify process remains mandatory.

### 10.2 Validate-only gate

`tools/dual_live_gate.py` installs raw-socket/DNS accidental-call guards before
application imports, then Requests and connector-transport guards before
evaluation. It rejects preloaded forbidden modules, re-verifies guards after
imports and after evaluation, and never weakens the guard to access PostgreSQL.
These guards prove that standard G1 code paths do not attempt network access;
they do not claim OS-level isolation from hostile or native code.

After environment/root validation and before opening the DB or reading any
campaign evidence, the gate acquires the root and campaign mutexes in the exact
Section-7.6 order. It retains both through the final fresh-connection and file
rereads and releases them in reverse order.

The gate supports existing local SQLite evidence only. Before SQLite opens, it
retains a Windows database handle that permits sharing for reads but denies new
writes and deletion. Failure to obtain that handle is unsafe to start. It
records main-file identity/SHA-256 and absence of `-journal`, `-wal`, and `-shm`
sidecars, opens SQLite URI `mode=ro`, enables `PRAGMA query_only=ON`, disables
autoflush, records `PRAGMA data_version`, and holds one read transaction.

After evaluation, the gate ends that transaction, queries `data_version` again
on the same connection, closes it, and opens a fresh `mode=ro`/`query_only`
connection. The fresh connection rederives the complete bounded semantic
snapshot; its result must equal the first snapshot. The gate then repeats the
main-file identity/SHA-256 and sidecar census before releasing the retained
handle. Any change or unstable observation is `INDETERMINATE`.

The database must already be closed, nonempty, compatible, and
`journal_mode=DELETE`, with no sidecar. The gate never changes journal mode,
checkpoints, performs recovery, creates a file, or runs migrations. A bad
starting posture and every non-SQLite URL are `REFUSED`; drift after evaluation
starts is `INDETERMINATE`. PostgreSQL validation is an explicit nonclaim for G1.

The gate emits one secret-safe canonical JSON line to stdout and no report file.
Exit codes are:

```text
0  PASS
1  FAIL
2  INDETERMINATE or REFUSED
```

## 11. Result taxonomy and report contract

Within validation results, `REFUSED` is gate-only and means evaluation was
unsafe to start: egress or send authority present, incomplete settings,
unsupported/missing DB, active runtime, unsealed capture, or guard failure. The
issuer's separately schematized `REFUSED` is not a validation result.

`INDETERMINATE` means evidence cannot support a truth claim: missing/unreadable
or hash-mismatched protected evidence, index rollback/fork/gap, snapshot drift,
ledger/counter disagreement, process-boot ambiguity, unstable custody scan, or
attestation mismatch.

`FAIL` means complete trusted evidence proves a campaign violation: terminal
failure/incompletion, missing connector/downstream result, redaction hit,
logger/quiescence failure, NRC-only stop, window violation, or a correctly
classified budget crossing. A crossing at or below the single-send allowance
can pass the accounting subcheck but cannot make the campaign `fresh_live`.

`PASS` requires exactly two completed connector runs and every frozen and
supplemental check to pass. `fresh_live` is true only for `PASS`.
`evaluation_complete` is true only for completed `PASS` or `FAIL` evaluation;
it is false for gate-level `REFUSED` and evidence-level `INDETERMINATE`.

Decision precedence is fixed. Before evaluator entry, the gate checks posture in
document order and emits the first `REFUSED` code. After entry, any authority,
hash, snapshot, resource-limit, or observation uncertainty makes the combined
status `INDETERMINATE`, even if another check found a violation. When all
evidence is determinate, any connector or global violation makes the combined
status `FAIL`; only two connector passes plus every global pass makes `PASS`.
Guard loss or DB/file drift discovered after evaluator entry is
`INDETERMINATE`, not retroactive `REFUSED`. The public `code` is the first code
in fixed stage/check order; later safe checks remain represented in their fixed
slots and cannot change precedence.

A pre-entry refusal is a distinct exact five-field object in this order:

```text
schema_id = project6.dual_live_gate_refusal.v1
status = REFUSED
fresh_live = false
evaluation_complete = false
code
```

It contains no campaign fields because structural refusal can occur before they
are trustworthy. Every post-entry result uses
`project6.dual_live_evaluation.v1` and the full contract below.

The report uses fixed field order and includes:

```text
schema_id
campaign_id
expected_campaign_fingerprint
status
fresh_live
evaluation_complete
code
connector_results[]       # NRC, then ScienceBase
combined_result
validated_surfaces[]
nonclaims[]
```

Each connector result contains only connector key, run ID or null, status,
reason code, ledger terminal hash or null, counted bytes or null, and fixed
check IDs/statuses/codes. `combined_result` contains only status, reason code,
and its fixed check IDs/statuses/codes. `validated_surfaces` and `nonclaims` are
closed, ordered enums; unknown or duplicate members are invalid. Reports never
expose paths, URLs, queries, headers, keys, receipts, raw metadata, endpoint
tuples, exception text, or DSNs.

## 12. Testing strategy

Implementation follows TDD in independently reviewable tranches:

1. **Runtime evidence:** logger-census, pipe protocol, runtime/boot identity,
   stop latch, Job Object, mutex, socket census, and A-to-B authority boundary.
2. **Post-run authority:** attestation/index contracts, strict-new issuance,
   historical chain, rotation, collision, and coordinated rewrite detection.
3. **Read-only kernels:** explicit-settings index loading, stable SQLite
   snapshots, ledger/counter union, origin/downstream/package verification, and
   custody scanning.
4. **Evaluator:** full positive fake dual campaign plus frozen failure matrix,
   exact taxonomy, repeatability, and before/after DB/filesystem identity.
5. **Issuer:** strict-new/adoption state machine, write fence, environment-only
   settings, stdout/exit contract, and PowerShell issuance action.
6. **Gate:** pre-import guards, environment-only settings, mutex, read-only DB,
   stdout/exit contract, PowerShell validation action, and default-refusing run
   action.

Required adversarial cases include:

- clean dual campaign, NRC-only stop, failed and replacement campaigns;
- two-campaign and three-campaign retained-history selection;
- preflight and post-run index rollback/fork/gap/orphan/partial/duplicate cases;
- boundary-equal `not_before`/`issued_at` and expiry-equal rejection;
- zero/one/two terminals, status/lease/post-terminal contradictions;
- extra/missing/duplicate/foreign/reordered counter records and multi-boot data;
- exact v1/v2 counter parsing in both consumers, mixed-version rejection, and
  v1 historical-read versus new-PASS ineligibility;
- NRC-first parent run/hash mismatch;
- raw/provenance/version/receipt/projection mismatch;
- missing/duplicate package kinds and changed payload bytes;
- sentinel URL/query/key forms in every DB/file/log encoding class;
- unexpected logger handlers and late topology mutation;
- sleeping grandchild, abrupt controller death, socket-table instability,
  PID-reuse ambiguity, and Phase-B-before-quiescence attempts;
- every invalid Phase-A/Phase-B FSM edge, pre-GO/post-stop send denial, both
  logger-census points, clean Phase-A-to-B progress, and error-latch blocking;
- revocation before reservation, revocation between lease and second check,
  in-flight-at-revocation accounting, send-idle timeout, and event-handle
  noninheritance by grandchildren;
- clean wrapper close followed by issuer private-namespace recreation, existing
  mutex contention, abandoned mutex, ACL mismatch, and name squatting;
- concurrent different-campaign issuers at one predecessor, validator/issuer
  contention, fixed lock order, code-revision contention for one campaign, and
  distinct-root independence;
- attestation and index replacement/deletion/repointing;
- coordinated logs+manifest+seal+matching-DB-event rewrite;
- write/fsync/rename/post-publication fault injection;
- every resource ceiling at equality and first-over-limit;
- issuer stdout/exit/write-fence tests; and
- proof that evaluator/gate issue no SQL writes and create no files.

Windows integration tests use fake child processes and loopback only. They must
prove that a child-spawned grandchild is contained, Job active-process count
reaches zero, and a loopback TCP/UDP owner is detected before termination and
absent after termination. No test performs DNS or external network access.

## 13. Acceptance criteria

This design is implemented only when all of the following are true:

- before code changes, the implementation plan maps every frozen Task-8 line to
  one stable check ID, owning module, positive test, and negative/adversarial
  test, with no umbrella check standing in for an unimplemented clause;
- the existing Clause-5 real-ledger test and B1a successor provenance remain
  green and the B1a seal remains unchanged;
- `run-dual-live-proof` still refuses without process, DB, event, log, or network
  effects;
- an isolated fake campaign produced through the real evidence constructors can
  be issued, independently pinned, and evaluated as `PASS`;
- every frozen Task-8 requirement through line 2512 maps to a named executable
  check and at least one positive or adversarial test;
- the evaluator and gate remain validate-only under mechanical DB/filesystem
  before/after comparison;
- no command/API caller can select evidence, archive, attestation, or index
  paths; only the validated process environment supplies roots/digests and all
  child paths are derived;
- every disagreement and uncertainty is classified by the fixed taxonomy and
  never upgraded to success;
- all prescribed Task-9 V1-V8, root API, progress, and `git diff --check`
  commands run and are recorded with exact exit and pytest counts;
- exact-commit security and Layer-3 reviews have no unresolved blocking finding;
  and
- the final report claims G1 offline substrate only, not live acquisition,
  deployment, or production readiness.

## 14. Practical implications

The selected design adds a deliberate two-step ceremony: issue evidence, then
independently pin the new attestation-index head before validation. That cost is
the mechanism that creates the missing independent edge; eliminating it would
return to self-consistent but rewritable evidence.

Because attestation and index publication cannot be one atomic filesystem
operation, recovery is intentionally asymmetric. An exact attestation-only
orphan can be adopted into a newly published, still-unpinned index after full
rederivation. Every other partial or ambiguous state strands that root and
campaign acceptance; it is retained for diagnosis, and the operator must use a
fresh root/epoch and rerun the campaign.

The Windows-only Job/mutex/socket implementation is appropriate for the current
host and frozen workflow. Unsupported platforms fail closed rather than
silently substituting weaker evidence. A future cross-platform runner requires
a separately reviewed containment design.

The G1 accidental-call guards and fake-sentinel custody tests are offline
controls, not proof of hostile-code network isolation or real-credential
custody. Those live-operation concerns remain a separately governed milestone.

The attestation-index root is public integrity material, not secret storage. Its
operational protection and retained head history remain operator duties. Code
can verify path topology and hashes but cannot prove filesystem ACL or backup
policy from inside the process.

Finally, the deep evaluator will be larger than the current scaffold, but it
must remain an orchestrator over focused, explicit-context read-only kernels.
New generic frameworks or unrelated Layer-3 refactors are out of scope.
