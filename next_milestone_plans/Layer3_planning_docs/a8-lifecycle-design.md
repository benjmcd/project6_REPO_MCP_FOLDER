# A8 SEC XBRL Durable Value Retention Design

Milestone: `M-A8-RETENTION-REDESIGN`

Base authority: refreshed `project6-origin/main` at
`c96ea5154dd13a0724d74f8979bb28651d667cb8`. The A8 branch was rebased onto
that authority before this retention redesign.

Status: planning-only packet plus Tier-1 document coverage tests. This document
changes no runtime behavior and authorizes no reveal. It does not implement value
reveal, flip feature flags, add routes, add schema/model/migration/persistence,
change redaction posture, run Arelle, fetch SEC data, touch A7 proof surfaces, or
change workflows.

Status cross-reference (2026-07-02): the current controlled-submit A8 path has
since been owner-run on real data after GO, with sanitized proof recorded in
`docs/MASTER_CONTEXT.md`, `docs/OPERATOR_UTILIZATION_INDEX.md`, the progress
board, and both manifests. The proof records 523 revealed facts, 497 non-empty
values, report SHA-256
`790fbb8eaa7de4be447f6c401089cb3b6435ff86614f4f0f57e656fc287a39d8`, value-store
SHA-256 `3bc81d84fc75bde17d074eee610130efa2659e2b2d281e756402007243eef5a0`,
`production_readiness_claimed=false`, and no A8 source-default or production
posture change. This lifecycle design remains historical design authority and
future-surface guidance, not a production-admission packet.

## Decision

A8 is a durable-retention design. SEC EDGAR XBRL financial values are public
government disclosures, and durable retention of resolved values is a product
feature. The risk boundary is not the public financial values themselves. The
risk boundary is operator identity, tenant/workspace/proxy metadata, local paths,
raw URLs, tokens, connector/provider secrets, artifact bytes, and other
operational authority material leaking into audit/status, committed artifacts, or
client-controlled request fields.

Selected design boundary:

`sec_xbrl_public_financial_value_retention_v1`

A8 should graduate by making the already-existing internal value store a governed
durable store for public SEC financial facts. Retention is owner-authorized,
feature-flagged, lineage-bound, integrity-checked, and storage-hygienic. It is
always a durable store-and-retrieve workflow.

Controlled reveal decision: explicit operator confirmation is a hard requirement
for any operator-visible display/submit of retained values. It is not a hard
requirement for durable store retention itself once the owner enables the store,
because the store is the system of record for public financial facts. Store
creation remains hard-gated by feature flag, source authority, storage hygiene,
and lineage integrity.

## Current Source Map

### Exists

- Current operator-workflow policy records redacted audit receipts and states
  that responses expose only hashes, ids, decision labels, reason codes, and
  redacted audit refs. They do not expose raw operator identity, proxy headers,
  tenant/workspace values, local paths, raw URLs, tokens, provider/connector
  secrets, or artifact bytes
  (`next_milestone_plans/Layer3_planning_docs/1061-cb-operator-workflow-ownership-access-policy-runtime.md:62-64`).
- Durable-state rules treat token hashes as sensitive operational data and keep
  raw bearer tokens out of normal response/audit paths
  (`next_milestone_plans/Layer3_planning_docs/109_DURABLE_STATE.md:143-153`).
- Historical SEC XBRL value-reveal planning records the corrected public-data
  posture: revealed data is public SEC EDGAR financial figures, while authority
  artifact redaction for identity, paths, URLs, headers, raw CIK/contact remains
  enforced (`next_milestone_plans/Layer3_planning_docs/1353-sec-xbrl-value-reveal-activation.md:80-87`).
- Value-reveal, internal value store, corpus validation, nonlocal authority, and
  controlled reveal submit remain feature-flagged/default-off in current source
  (`backend/app/core/config.py:152-175`). The support matrix also pins value
  reveal, internal value store, and controlled submit false/default-off
  (`config/support_matrix.yaml:8-18`, `config/support_matrix.yaml:52-64`).
- The sidecar service already has an internal value-store concept. When the flag
  is enabled it records `internal_value_store_hash`, writes `value_records`,
  stores `value_store_hash` and `value_record_count`, marks the store as
  `persisted`, and records retention as `tied_to_sidecar_receipt_lifecycle`
  (`backend/app/services/layer3_sec_xbrl_sidecar.py:206-214`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:248-251`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:321-322`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:1129-1161`,
  `backend/app/services/layer3_sec_xbrl_sidecar.py:1164-1189`).
- The internal value-store reader fails closed if metadata was not persisted, the
  file is missing or unreadable, the payload is invalid, lineage mismatches, or
  hash/count checks fail (`backend/app/services/layer3_sec_xbrl_sidecar.py:355-413`).
- The value-reveal service already has a controlled request shape: schema,
  request id, actor, explicit confirmation, sidecar id/hash, and dataset id/hash
  are allowed; caller paths, URLs, bytes, credentials, identity, raw provider
  fields, connector dispatch, source expansion, and frontend authority are
  forbidden (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:40-101`,
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:286-303`).
- The value-reveal service requires explicit `operator_reveal_confirmation=True`,
  sidecar/dataset lineage, and idempotent receipt persistence. Its audit receipt
  stores hashes/counts/policy/scope/lineage and records that audit receipts do
  not persist raw values or raw identity
  (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:160-175`,
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:530-596`,
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:683-698`).
- Controlled value-reveal submit remains default-off, requires explicit
  confirmation, rejects raw/local authority fields, resolves server-owned
  authority lineage, requires an existing sidecar/value store, and returns
  idempotent replay for an existing receipt
  (`backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py:98-179`,
  `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py:306-321`).
- H6 remains a separate containment utility and is not an A8 dependency. Its
  existing tests should keep proving dry-run, refusal, storage-root, collision,
  and move-only containment behavior.

### Missing

- No owner-approved A8 retention state machine currently names the durable value
  store as the intended endpoint for public financial values.
- No readiness gate currently separates retained public financial values from
  redacted operator identity, paths, tokens, source URLs, proxy headers, and
  connector/provider secrets.
- No future implementation packet has yet specified storage hygiene for the
  durable store as a product organization and integrity requirement: isolated
  namespace, off repo, off OneDrive/cloud sync, not git-committed, and not
  static-served.
- No future implementation packet has yet stated the controlled-reveal split:
  explicit confirmation is mandatory for display/submit, while durable retention
  is the owner-enabled system-of-record behavior for public values.

### Recommended

- Treat the retained internal value store as the canonical A8 runtime direction.
- Keep audit/status redacted for operator identity and operational secrets while
  retaining public financial values in the store.
- Keep H6 out of A8 except as separately scoped containment tooling.
- Require a Tier-2 implementation packet before any runtime, persistence, flag,
  route, schema/model, or redaction-posture change.

## Retention State Machine

The future A8 lifecycle is monotonic retention with fail-closed integrity gates.
There are no disposal states.

| State | Entry transition | State invariant | Audit/status posture | Allowed next state | Failure posture |
|---|---|---|---|---|---|
| `resolved_redacted_authority` | A7 sidecar/material authority exists and financial facts are resolved into redacted authority. | Public values may exist in source-side authority, but no A8 durable store is admitted yet. | Hash/count/source-family/lineage only; operator identity and operational fields redacted. | `retention_preflight_passed`, `retention_blocked` | Missing authority, stale hashes, or disabled flags block before store creation. |
| `retention_preflight_passed` | Owner-enabled internal value-store flag, current authority hash, and storage hygiene checks pass. | Durable namespace is selected but values are not yet written by A8. | Store namespace id is hashed; no local path, storage root, token, URL, proxy header, or operator identity is exposed. | `values_retained_durable`, `retention_blocked` | Repo, OneDrive/cloud-sync, git-committed, static-served, shared, or unverifiable storage blocks. |
| `values_retained_durable` | Value records are written to the internal value store with value-store hash, count, semantics, and sidecar lineage. | Public financial values are retained durably as product data. | Audit/status expose hashes, counts, policy ids, state, and lineage; public values remain in the store, not in audit/status receipts. | `reveal_requested`, `retention_replayed` | Write failure, lineage mismatch, hash mismatch, or unreadable store blocks access. |
| `reveal_requested` | Authenticated operator requests display/submit with explicit confirmation, current authority hash, and server-resolved sidecar/dataset/value-store lineage. | Durable values already remain retained; operator-visible display is still not performed until request binding passes. | Request/audit redacts actor identity, path, URL, CIK/contact when applicable, tokens, proxy headers, and storage roots. | `values_displayed_controlled`, `retention_blocked` | Missing confirmation, stale authority, client-supplied raw/source fields, or lineage mismatch blocks. |
| `values_displayed_controlled` | Server reads retained value records and returns the approved display/submit page or response. | Public financial values may be displayed to the authorized operator; store remains durable. | Receipts/status carry hashes/counts/policy/scope/lineage and do not persist operator identity or operational secrets. | `retention_replayed` | Projection redaction violation or receipt persistence failure blocks rather than returning an unsafe response. |
| `retention_replayed` | Duplicate request or status inspection reuses the same idempotency basis and store hash. | No duplicate store is written and no conflicting receipt is admitted. | Same receipt/status projection is returned. | terminal until a new authority packet exists | Conflicting request id, authority hash, value-store hash, policy id, or lineage fails closed. |
| `retention_blocked` | Any preflight, lineage, storage, flag, request, receipt, or projection invariant fails. | Public values are not newly displayed and no unsafe audit/status projection is produced. | Blocked reason exposes only safe codes, hashes, and counts. | manual remediation or fresh authority packet | No fallback to client-supplied paths, source acquisition, Arelle execution, or artifact bytes. |

## Durable Value Store Model

- The retained value store is the durable system-of-record direction for public
  SEC EDGAR financial values once the owner authorizes A8 runtime work.
- Store records retain public financial values with sidecar receipt id/hash,
  value-store hash, value count, value semantics, source ordering, and lineage
  needed for replay and provenance.
- Store placement is a hygiene and operability requirement, not a secrecy claim:
  isolated namespace, off repo, off OneDrive/cloud-sync roots, not git-committed,
  not static-served, and not mixed with operator Downloads stores.
- The store must fail closed on missing metadata, missing file/object, unreadable
  payload, invalid payload, sidecar lineage mismatch, value-store hash mismatch,
  count mismatch, or unsupported backend.
- Status and audit projections may expose store state, hashes, counts, policy ids,
  lineage ids, timestamps, and blocked reasons. They must not expose operator
  identity, tokens, raw URLs, local paths, storage roots, proxy headers,
  connector/provider secrets, artifact bytes, or tenant/workspace values.

## Redaction Boundary

A8 redaction is about identity and operational authority, not public financial
values in the retained store.

- Retained: public SEC EDGAR financial values, value semantics, fact ids, source
  order, sidecar lineage, store hashes, counts, and provenance needed to make the
  facts durable and reproducible.
- Redacted from audit/status/committed artifacts/request authority: raw operator
  identity, actor strings unless hashed, tenant/workspace values, proxy headers,
  tokens and token hashes when operationally sensitive, local paths, storage
  roots, raw URLs, credentials, provider/connector secrets, raw CIK/contact where
  treated as authority metadata, and artifact bytes.
- Display boundary: authorized display/submit may return public financial values
  after explicit confirmation and server-resolved authority. That does not mean
  audit/status receipts should duplicate those values.
- Failure boundary: blocked responses expose reason codes and safe hashes/counts,
  not raw authority material or diagnostics that contain operational secrets.

## Request Binding And Controlled Reveal

- Display/submit is a hard controlled-reveal requirement: authenticated operator
  identity, explicit confirmation, current authority hash, and server-resolved
  sidecar/dataset/value-store lineage are mandatory.
- The browser/client does not supply raw local paths, raw URLs, source-acquisition
  fields, storage roots, sidecar internals, CIK/accession/source identity, Arelle
  execution fields, connector dispatch fields, credentials, proxy headers, or
  operator contact fields.
- Server code re-resolves authority from the approved receipt and validates the
  internal value store before returning values.
- Idempotent replay of the same request basis returns the same receipt/projection;
  conflicting replay fails closed.
- Retention itself is governed by owner-enabled internal value-store settings and
  current source authority. It is not a per-click display preference because the
  public values are the durable product data.

## Provenance Integrity And Idempotency

- Every retained value set is bound to sidecar receipt id/hash, dataset version
  hash when applicable, value-store hash, value count, value semantics, source
  order, policy id, and storage namespace hash.
- Replaying store creation with the same authority and value-store hash returns
  the existing store metadata without duplicating records.
- Replaying display/submit with the same request and receipt basis returns the
  existing receipt/status projection.
- Any mismatch in authority hash, sidecar hash, dataset hash, value-store hash,
  value count, policy id, namespace hash, or request basis is a conflict and
  fails closed.
- Provenance should be replayable offline from retained receipts and store
  metadata. Validation must not require live SEC egress, taxonomy download,
  Arelle execution, or operator Downloads-store access.

## H6 Boundary

H6 remains outside A8. It can continue to prove inventory, dry-run, refusal, and
move-only containment behavior for already-existing local artifacts. A8 retention
must not call H6, upgrade H6, or describe H6 as part of the retained public-value
store. The retained store is a governed storage/retrieval surface, not an archive
movement utility.

## Conditional Future Source-Class Caveat

A hypothetical non-public, licensed, contractual, paid-vendor, or no-retention
source class would need a separate source-class disposition policy before any
runtime work. That future policy is out of scope for SEC EDGAR A8 because SEC
EDGAR financial facts are public government disclosures and should be retained as
product data.

## Modularity Non-Fragility Scalability

- Model retention behind a store interface so local filesystem, object storage,
  or database-backed implementations can share the same receipt and integrity
  contract.
- Keep each retained dataset in an isolated namespace keyed by authority and
  value-store hash. N retained datasets imply N independently replayable store
  records and receipt projections.
- Do not rely on shared mutable globals or browser-provided storage authority.
- A failure in one retained namespace must not corrupt, hide, or block unrelated
  retained datasets.
- Store readers must verify hash/count/lineage on every read and fail closed on
  mismatch.
- Store writers must be idempotent and conflict-aware.
- Retrieval should support pagination/windowing for large filings while preserving
  the same value-store hash and receipt basis.

## Acceptance Coverage Map

- B1 durable value-store retention model: `Retention State Machine` and `Durable
  Value Store Model` define retained public financial values as the endpoint.
- B2 identity/secret/path/token redaction: `Redaction Boundary` separates public
  retained values from operational identity and secret material.
- B3 storage hygiene: `Durable Value Store Model` defines isolated/off-repo/
  off-OneDrive/non-git/non-static durable placement.
- B4 provenance/integrity: `Provenance Integrity And Idempotency` defines hashes,
  receipts, lineage, and conflict handling.
- B5 reveal request binding: `Request Binding And Controlled Reveal` defines
  auth, explicit confirmation, current authority, and server-resolved lineage.
- B6 idempotency: `Retention State Machine` and `Provenance Integrity And
  Idempotency` define replay and conflict behavior.
- B7 conditional future non-public-source caveat: `Conditional Future
  Source-Class Caveat` keeps non-public source policy out of SEC EDGAR A8.
- B8 modularity/non-fragility/scalability: `Modularity Non-Fragility Scalability`
  defines the pluggable store, isolated namespaces, verified reads, and scaling
  shape.

## Non-Admissions

- No value-reveal implementation or enablement.
- No internal value-store flag default change.
- No controlled-submit flag default change.
- No runtime, route, rendered UI, schema, model, migration, persistence, workflow,
  or redaction-posture change.
- No Arelle run, live SEC request, taxonomy download, source acquisition, value
  reveal, controlled submit, or operator Downloads-store access.
- No A7 proof-surface modification.
- No H6 dependency or upgrade.
