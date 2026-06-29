# A8 SEC XBRL Raw-At-Rest Lifecycle Design

Milestone: `M-A8-DESIGN-COMPLETE`

Base authority: refreshed `project6-origin/main` at
`525993c721cad0e1349105f7502271c2be4ae996`. The implementation branch was
rebased onto that authority before this packet was deepened.

Status: planning-only packet plus Tier-1 additive quarantine-tool tests. This
document does not implement value reveal, secure erasure, route behavior, schema,
model, persistence, redaction-posture, flag, live-network, Arelle, UI, export, or
default-on changes.

Network note: this pass used Git/GitHub network only to refresh live repository
authority. It did not perform live SEC egress, taxonomy download, Arelle
execution, source acquisition, value reveal, or operator Downloads-store access.

A7 proof note: any reported real-10-Q A7 operator evidence remains
operator-demonstrated evidence unless and until committed source, tests, CI, and
merge state separately prove it. This A8 packet does not upgrade operator-run A7
proof into committed implementation truth.

## Decision

A8 cannot graduate on the current quarantine helper alone. The existing code can
produce or consume raw value material under explicit flags, and the current H6
tool can find and move raw-at-rest candidates into a quarantine archive. What is
missing is the lifecycle that makes raw-at-rest creation, retention, quarantine,
and secure erasure a single fail-closed state machine.

Selected design boundary:

`sec_xbrl_value_reveal_raw_at_rest_lifecycle_v1`

The future implementation must add a modular raw-value lifecycle service with a
pluggable storage and erasure backend. Missing erasure support blocks reveal; it
must never silently degrade into quarantine-only retention.

## Current Source Map

### Exists

- The governed Arelle value-reveal request is tightly allowlisted to schema,
  request id, actor, explicit confirmation, sidecar id/hash, and dataset id/hash
  fields; unknown fields and raw path, URL, byte, credential, provider, storage,
  and identity fields are forbidden (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:40-101`,
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:286-303`).
- The legacy reveal service blocks by default when
  `layer3_sec_edgar_arelle_value_reveal_enabled` is false, requires the request
  schema, actor, explicit `operator_reveal_confirmation=True`, sidecar id/hash,
  and dataset version id/hash before reading authority
  (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:146-175`).
- Reveal authority is lineage-bound. The service requires a ready sidecar,
  reads the internal value store through the sidecar service, requires a ready
  dataset/provenance/bridge context, and blocks on sidecar-vs-bridge lineage
  mismatch (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:177-213`,
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:320-413`).
- The reveal audit receipt persists hashes, counts, policy ids, scope, value
  semantics, redaction policy, negative invariants, and lineage hashes; it marks
  `raw_values_persisted_in_audit_receipt` and `raw_identity_persisted_in_audit_receipt`
  false (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:517-597`).
  Status projection repeats the hash/count-only posture and records raw values
  and identity as not persisted (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:630-669`).
- Ready reveal responses can return effective and lexical values for facts that
  pass identity redaction, but status/audit projections remain hash/count-only
  (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:415-497`,
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:600-627`).
- Value-reveal defaults remain pinned off in current source:
  `layer3_sec_edgar_arelle_internal_value_store_enabled`,
  `layer3_sec_edgar_arelle_value_reveal_enabled`, and
  `layer3_sec_xbrl_controlled_value_reveal_submit_enabled` default false
  (`backend/app/core/config.py:152-175`). The support matrix pins those flags
  false and classifies value reveal, controlled submit, and internal value store
  as `experimental_default_off` (`config/support_matrix.yaml:8-18`,
  `config/support_matrix.yaml:52-64`).
- The sidecar path creates internal value-store metadata only when the internal
  value-store flag is enabled, records the value-store hash in authority hashes,
  and writes the internal store before the sidecar receipt
  (`backend/app/services/layer3_sec_xbrl_sidecar.py:209-214`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:250-251`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:321-324`).
- The sidecar internal value store is raw-at-rest material when enabled: the
  stored payload includes `value_records`; the reader fails closed if metadata is
  not persisted, the file is missing/unreadable/invalid, lineage mismatches, or
  hash/count checks fail (`backend/app/services/layer3_sec_xbrl_sidecar.py:355-413`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:1129-1161`).
- The current H6 helper is a raw-at-rest inventory and quarantine utility. Its
  dry-run report is non-mutating and records no source acquisition, SEC egress,
  Arelle invocation, value reveal, or DB mutation (`tools/sec-h6-quarantine.py:143-162`).
  Execute mode requires run-id confirmation, quarantine confirmation, and path
  acknowledgement as applicable (`tools/sec-h6-quarantine.py:304-347`).
- H6 quarantine moves files with `shutil.move` into a repo-relative flat archive
  and writes a manifest (`tools/sec-h6-quarantine.py:348-357`,
  `tools/sec-h6-quarantine.py:388-398`). That is containment, not secure
  erasure.
- Current governance classifies any implementation touching stored/revealed
  values, runtime defaults, redaction posture, durable schema, or persistence as
  Tier 2 (`next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:34-37`,
  `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:55-68`).
- Historical activation/default-on text is not current runtime authority.
  `1360-posture-reconcile.md` reasserts current config/support-matrix authority:
  controlled value reveal is experimental/default-off unless explicitly enabled
  (`next_milestone_plans/Layer3_planning_docs/1353-sec-xbrl-value-reveal-activation.md:18-35`,
  `next_milestone_plans/Layer3_planning_docs/1360-posture-reconcile.md:37-64`).

### Missing

- No current state machine binds reveal request, raw value storage, retention,
  quarantine, secure erasure, and replay/idempotency into one lifecycle.
- Before this lane, no A8/17B-named planning packet existed in
  `next_milestone_plans`; this packet fills the named raw-at-rest lifecycle
  design gap without implementing the lifecycle.
- No source-grounded secure-erasure backend exists. H6 moves candidate files and
  leaves archived bytes readable by design; it does not overwrite, unlink,
  crypto-erase, verify absence, or write an erasure receipt
  (`tools/sec-h6-quarantine.py:350-357`).
- H6 writes quarantine artifacts under `backend/app/storage_archive` relative to
  the repo root. That may be useful for emergency containment, but it is not an
  A8 raw-value store because A8 raw-at-rest storage must be off-repo, off-OneDrive,
  not static-served, and isolated per reveal.
- No retention/TTL policy, erasure deadline, quarantine-to-erasure transition,
  erasure retry semantics, or terminal `erasure_blocked` posture is implemented.
- No readiness gate currently proves that an operator cannot reveal values unless
  a supported erasure backend is configured and healthy before raw values are
  created.

### Recommended

- Implement A8 as a new lifecycle service owned by server-side reveal authority,
  not by the browser and not by the H6 quarantine helper.
- Keep H6 available as emergency containment evidence only unless a future Tier-2
  implementation explicitly adds an erasure backend, tombstone receipts,
  replay/idempotency, and failure-state tests.
- Require the readiness gate in `a8-readiness-gate.md` to be satisfied item by
  item before any value-reveal implementation PR is owner-authorized.

## Lifecycle State Machine

The future A8 lifecycle must be explicit, monotonic, and replay-safe. The state
log is authoritative; status APIs project from the log and never infer a safer
state from missing files.

| State | Entry transition | State invariant | Redaction posture | Audit/replay rule | Failure/abort transition |
|---|---|---|---|---|---|
| `resolved_redacted` | A7 sidecar/material bridge authority and redacted dataset lineage are ready. | No operator-visible values have been revealed; internal value store may be absent while flags are off. | UI/API remain redacted; identity-like values are suppressed. | Replay returns the same redacted lineage hashes. | Stale or missing authority stays blocked before reveal preparation. |
| `reveal_authority_prepared` | Server derives an owner-approved reveal authority receipt over current sidecar, dataset, and decision lineage. | Only hash/count/policy metadata exists in authority receipts. | Status/audit show authority hashes and counts only. | Idempotent by authority hash plus policy id. | Expiry or lineage drift moves to `expired`/blocked; no values are returned. |
| `reveal_requested` | Authenticated operator submits explicit confirmation against current authority. | Raw values still have not been written by A8; storage and erasure preflight must pass first. | Request payload excludes raw paths, URLs, CIK/accession, local storage, credentials, and operator free text. | Duplicate request with same idempotency basis returns the same pending receipt. | Missing confirmation, stale authority, or invalid preflight stays blocked before raw creation. |
| `erasure_preflight_passed` | Configured raw store proves isolation and supported erasure backend health. | Raw values still do not exist; this is a pre-creation gate. | Only hashed backend id, namespace id, and policy id are recorded. | Replay of the same preflight is idempotent while backend/policy hashes match. | Backend missing, unsupported, cloud-synced, static-served, or unverifiable fails closed. |
| `raw_at_rest_created` | Isolated raw store writes the encrypted or backend-owned value set in a per-reveal namespace. | Raw values exist only in A8 storage; no repo, OneDrive, static mount, status, or audit raw-value copy. | Status/audit show hashes, byte counts, namespace hash, and retention deadline only. | Replay verifies inventory hash and returns the same creation receipt. | Partial write, hash mismatch, or namespace collision enters `erasure_blocked` or `quarantined` with no reveal. |
| `revealed` | Server reads from the isolated raw store for the approved response/session. | Operator sees only permitted non-identity values; no durable raw-value copy is added to audit/status. | Response may carry allowed effective/lexical values; audit/status remain hash/count-only. | Replaying status returns receipt metadata, not values. | Session abort or response failure moves to `erase_pending`; no retry reveals without current authority. |
| `erase_pending` | TTL, operator closeout, session abort, or policy requires erasure. | No future reveal is allowed from the namespace. | Only blocked reason, deadline, namespace hash, and inventory hash are visible. | Duplicate erase request reuses the same pending receipt. | Backend unavailable, partial erase, or verification failure moves to `erasure_blocked`. |
| `securely_erased` | Supported backend erasure completes and verification passes. | Raw values are not readable by supported backend semantics; only tombstone metadata remains. | Status/audit show erasure receipt hash, backend id, verification result, and tombstone hashes. | Terminal replay returns the same erasure receipt and never recreates values. | None; conflicting replay fails closed. |
| `quarantined` | Incident containment moves/disables access before erasure. | Raw bytes may still be recoverable; quarantine is not a terminal safe state. | Status explicitly says `secure_erasure_performed=false`. | Replay returns containment receipt only. | Must proceed to `erase_pending` or `erasure_blocked`. |
| `erasure_blocked` | Erasure backend is missing, unsupported, failed, partial, or unverifiable. | Raw values are treated as still existing or not provably erased. | Reveal remains blocked; status/audit expose only blocked reason and hashes. | Replay remains blocked until manual remediation records a new authority transition. | Manual remediation only; no silent quarantine-only success. |
| `expired`/`aborted` | Authority expires, operator aborts, or current lineage changes before raw creation. | No A8 raw values exist for that authority. | Redacted/hash-only projection. | Terminal replay returns expiry/abort receipt. | A new request requires fresh authority. |

## Redaction Posture Per State

- Pre-creation states (`resolved_redacted`, `reveal_authority_prepared`,
  `reveal_requested`, `erasure_preflight_passed`) are hash/count/policy-only.
  They must not project raw effective values, raw lexical values, identity-like
  values, local paths, SEC URLs, CIKs/accessions, storage roots, operator contact
  strings, credentials, proxy headers, or source-acquisition details.
- `raw_at_rest_created` may store raw values only inside the isolated A8 raw
  store. All audit/status projections remain hash/count/tombstone-only and must
  show retention deadline, namespace hash, inventory hash, and blocked/reveal
  eligibility state without exposing values.
- `revealed` may return allowed effective/lexical fact values only in the
  approved operator response/session. It must preserve existing identity
  suppression and must not persist those raw values in receipts, status rows,
  committed artifacts, logs, or browser-supplied request fields.
- `erase_pending`, `securely_erased`, `quarantined`, and `erasure_blocked` never
  return raw values. `quarantined` and `erasure_blocked` must make the unsafe
  posture explicit by recording that secure erasure has not been verified.
- `expired` and `aborted` are terminal redacted/hash-only states; retry requires
  a fresh authority packet.

## Secure-Erasure Design

The future implementation should introduce a storage/erasure abstraction, not a
one-off file helper:

`ValueRevealRawStore`

Required operations:

1. `preflight(authority_hash, byte_count, policy_id)`: proves storage is off-repo,
   off-OneDrive, not static-served, permission-restricted, and paired with a
   supported erasure backend.
2. `create(reveal_basis)`: writes the raw value set into an isolated per-reveal
   namespace and returns only hashed path/container ids plus hashes/counts.
3. `mark_revealed(receipt_id)`: records that operator-visible reveal occurred
   without persisting raw values into status/audit rows.
4. `quarantine(receipt_id)`: moves or disables access for incident containment;
   explicitly records `secure_erasure_performed=false`.
5. `erase(receipt_id)`: performs backend-specific erasure and writes an immutable
   erasure receipt.
6. `verify_erased(receipt_id)`: checks that raw values cannot be read by the
   selected backend and that only tombstone metadata remains.

Accepted erasure backends:

- `crypto_erase`: preferred for SSD, cloud-synced, copy-on-write, and uncertain
  filesystems. Store each reveal payload encrypted with a per-reveal data key;
  erasure destroys the key material, unlinks ciphertext, fsyncs parent metadata
  where applicable, verifies key lookup failure, and records a key-id hash and
  tombstone receipt. This is the default eligible backend for Windows/OneDrive
  risk because overwriting bytes does not prove physical erasure there.
- `overwrite_unlink`: allowed only for a local backend that explicitly declares
  direct overwrite semantics and is outside repo/OneDrive/static delivery. It
  writes over the exact byte range, flushes and fsyncs file and directory metadata
  where the platform supports it, unlinks the file, verifies path absence, scans
  the raw namespace inventory for remaining candidates, and records byte count,
  pre-erasure hash, backend id, and verification result. It must fail closed on
  copy-on-write, SSD trim uncertainty, cloud sync, permission error, short write,
  partial unlink, or unverifiable directory sync.
- `quarantine_only`: never qualifies as A8 secure erasure. It may be used only as
  an incident containment state before `erase_pending`.

Audit receipts must never store raw values, raw identity values, raw local paths,
SEC URLs, CIKs/accessions, operator contact strings, or storage roots. Receipts
may store schema id, state transition, policy id, actor hash, authority hashes,
value inventory hash, byte count, hashed container id, erasure backend id, and
verification result.

## Operator Confirmation And Reveal Audit Mapping

The existing value-reveal service already gives A8 a narrow authority model to
reuse, but A8 must place raw-store and erasure preflight between confirmation and
raw creation.

- Request shape remains allowlisted to schema, request id, actor, explicit
  confirmation, sidecar id/hash, and dataset id/hash. Browser/client requests
  remain forbidden from supplying raw paths, URLs, bytes, credentials, storage
  roots, provider internals, source-acquisition fields, or identity fields.
- The feature flag, schema, `client_request_id`, `actor`,
  `operator_reveal_confirmation=True`, sidecar id/hash, and dataset id/hash
  checks remain mandatory before any reveal authority is read.
- Sidecar readiness, internal value-store readiness, dataset provenance,
  bridge/sidecar lineage, and stale-authority checks remain server-owned. A8
  cannot trust client-supplied authority ids without server re-resolution.
- The current receipt posture persists policy, scope, lineage hashes, fact/value
  inventory hashes, redaction posture, and negative invariants while recording
  that audit/status do not persist raw values or raw identity. A8 erasure
  receipts should extend that receipt family rather than introduce a browser
  supplied or path-heavy audit surface.
- The existing write-once/idempotent receipt behavior is the model for A8
  transition receipts: same idempotency basis returns the same receipt;
  conflicting replay fails closed.

## Audit Replay And Idempotency

- Each transition receipt is keyed by authority hash, prior state, target state,
  policy id, raw-store namespace hash when applicable, and value inventory hash.
- Replaying a completed transition returns the original receipt and does not
  re-read, re-write, re-reveal, or re-erase values.
- A replay with the same request id but different authority hash, namespace hash,
  backend id, value inventory hash, byte count, policy id, actor hash, or target
  state is a conflict and must fail closed.
- `securely_erased` is terminal. Replay verifies receipt/tombstone consistency
  and never reconstructs values.
- `erasure_blocked` is sticky until an explicit manual-remediation transition
  records new authority and backend evidence. It cannot be auto-upgraded to
  erased because a file is missing.
- Audit replay remains offline and local to stored receipts; it does not call SEC
  endpoints, run Arelle, fetch taxonomies, or regenerate source artifacts.

## Isolated Storage And Containment

- A8 raw storage must live outside the repo, outside OneDrive/cloud-sync roots,
  outside `settings.storage_dir` static exposure, outside committed/generated
  artifact trees, and outside operator Downloads stores.
- Every reveal authority gets a dedicated namespace. There is no shared mutable
  raw-value file across datasets, issuers, runs, browser sessions, or operators.
- Namespace metadata may expose only hashed container ids, byte counts,
  pre-erasure hashes, inventory hashes, retention deadline, erasure backend id,
  and verification/tombstone hashes.
- H6 quarantine remains a separate containment tool. Its repo archive and
  move-only semantics are useful for emergency collection, but they are not A8
  storage and not secure erasure.
- Storage preflight is fail-closed. Repo-relative, OneDrive, cloud-synced,
  static-served, permission-broad, missing-backend, unsupported-backend, or
  unverifiable storage roots block before `raw_at_rest_created`.

## Failure And Abort Handling

- Missing erasure backend, unsupported backend, unhealthy backend, or storage
  preflight failure blocks in `reveal_requested` or `erasure_preflight_passed`;
  raw values are not created.
- Partial raw-store creation, namespace collision, write failure, hash mismatch,
  or inventory mismatch blocks reveal and records containment/remediation state.
- Operator abort, session failure, response transport failure, or TTL expiry
  after raw creation moves to `erase_pending` and blocks further reveal.
- Partial overwrite, short write, unlink failure, crypto-key destruction failure,
  directory sync failure, tombstone write failure, or verify-read success moves
  to `erasure_blocked`.
- A missing file alone is not proof of erasure. Only a supported backend receipt
  plus verification can enter `securely_erased`.
- Any failure path must preserve redacted/hash-only audit evidence and must not
  return values as a fallback diagnostic.

## Modularity Non-Fragility Scalability

- The lifecycle should be modeled as one immutable transition log per
  reveal-authority receipt. Shared mutable global state is forbidden.
- Every transition must be idempotent by authority hash plus state. Replaying a
  completed transition returns the same receipt; conflicting replay fails closed.
- N revealed datasets must use N isolated raw-store namespaces and N erasure
  receipts. A failed erasure in one namespace must not block erasure or audit for
  another namespace.
- Backend selection must be explicit in config and receipt metadata. Missing,
  disabled, or unsupported backends block before `raw_at_rest_created`.
- Status/read APIs must project only state, hashes, counts, timestamps, and
  blocked reasons. They must not replay values after the initial reveal response.
- Backend operations should be injected behind an interface so tests can cover
  successful erasure, backend refusal, partial failure, and stale authority
  without invoking live SEC/Arelle/runtime network or touching operator stores.
- Scaling is per-reveal namespace and receipt, not per-process mutable globals.
  N datasets imply N namespaces, N retention deadlines, and N erasure receipts.
  One blocked namespace must not prevent independent erasure or audit replay for
  another namespace.

## Acceptance Coverage Map

- B1 state machine: `Lifecycle State Machine` defines explicit states,
  transition authority, invariants, replay, and failure transitions.
- B2 secure erasure spec: `Secure-Erasure Design` defines
  `ValueRevealRawStore`, accepted backends, proof requirements, and
  quarantine-only exclusion.
- B3 redaction per state: `Redaction Posture Per State` defines what can be
  projected before creation, during reveal, after erasure, during quarantine, and
  on abort.
- B4 operator confirmation plus reveal audit: `Operator Confirmation And Reveal
  Audit Mapping` maps A8 to the existing allowlist, confirmation, lineage, and
  receipt posture.
- B5 audit/replay/idempotency: `Audit Replay And Idempotency` defines
  idempotent receipt keys, conflict handling, and terminal replay rules.
- B6 isolated storage containment: `Isolated Storage And Containment` defines
  off-repo/off-OneDrive/off-static namespaces and H6 containment boundaries.
- B7 failure/abort handling: `Failure And Abort Handling` defines backend,
  creation, reveal, erase, and verification failure outcomes.
- B8 modularity/non-fragility/scalability: `Modularity Non-Fragility
  Scalability` defines interface boundaries, per-reveal namespaces, and
  independent failure containment.

## Non-Admissions

- No value-reveal implementation or enablement.
- No flag default change.
- No secure-erasure implementation.
- No schema, model, migration, durable persistence, route, rendered UI, or
  redaction-posture change.
- No Arelle run, live SEC request, taxonomy download, source acquisition, or
  operator Downloads store access.
- No A7 proof-surface modification.
- No operator-run A7 proof promoted into committed or CI implementation truth.
