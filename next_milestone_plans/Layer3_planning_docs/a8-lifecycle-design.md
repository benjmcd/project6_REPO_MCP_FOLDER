# A8 SEC XBRL Raw-At-Rest Lifecycle Design

Milestone: `M-A8-LIFECYCLE-DESIGN`

Base authority: local `project6-origin/main` at
`1a5a59f31c9af8dc7cd646ca5ddbd679e10efa69`.

Status: planning-only packet plus Tier-1 additive quarantine-tool tests. This
document does not implement value reveal, secure erasure, route behavior, schema,
model, persistence, redaction-posture, flag, live-network, Arelle, UI, export, or
default-on changes.

Network note: this pass did not run `git fetch` because the handoff also required
no network in the final report. The local `project6-origin/main` ref already
matched the handoff's `1a5a59f3` / PR `#2404` authority.

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
- No A8/17B-named planning packet existed in `next_milestone_plans` during this
  audit; this packet fills that named raw-at-rest lifecycle gap.
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

## Lifecycle State Machine

The future A8 lifecycle should be explicit and replay-safe:

| State | Entry authority | Raw value posture | Allowed next state |
|---|---|---|---|
| `resolved_redacted` | A7 sidecar/material bridge authority and redacted dataset lineage | No operator value exposure; internal value store may be absent if flag off | `reveal_authority_prepared` |
| `reveal_authority_prepared` | Server-owned value-reveal authority receipt over approved workflow/decision lineage | No revealed raw values; only hash/count metadata | `reveal_requested`, `expired` |
| `reveal_requested` | Authenticated owner/operator plus explicit confirmation and current authority hash | Still no new raw store until storage and erasure preflight pass | `raw_at_rest_created`, `blocked` |
| `raw_at_rest_created` | Raw store allocates isolated dataset/reveal container and writes encrypted raw value set | Raw values exist only in the A8 raw store; no repo, OneDrive, static mount, status, or audit raw-value copy | `revealed`, `quarantine_pending`, `erase_pending` |
| `revealed` | Response/page reads from the isolated raw store under request/session bounds | Operator sees only permitted non-identity values; audit/status stays hash/count-only | `erase_pending`, `quarantine_pending` |
| `quarantine_pending` | Operator or policy marks raw store unsafe or ready for retention containment | Raw values still exist; no future reveal allowed | `quarantined`, `erasure_blocked` |
| `quarantined` | Move/containment receipt over raw files | Raw bytes may still be recoverable; this is not a terminal safe state | `erase_pending` |
| `erase_pending` | TTL, operator closeout, or policy requires erasure | Reveal is blocked while erasure runs | `securely_erased`, `erasure_blocked` |
| `securely_erased` | Erasure backend writes a receipt and verification passes | Raw values no longer readable by supported backend semantics; only hash/count/tombstone metadata remains | terminal/idempotent replay |
| `erasure_blocked` | Erasure backend missing, unsupported, failed, or unverifiable | Raw values are contained but not safe to claim erased; reveal remains blocked | manual remediation only |

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

## Modularity And Scalability

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

## Non-Admissions

- No value-reveal implementation or enablement.
- No flag default change.
- No secure-erasure implementation.
- No schema, model, migration, durable persistence, route, rendered UI, or
  redaction-posture change.
- No Arelle run, live SEC request, taxonomy download, source acquisition, or
  operator Downloads store access.
- No A7 proof-surface modification.
