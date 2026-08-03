# B1b Dispatch Correction

Prospective state if this correction is eventually identified, landed, and
published: corrected, hash-bound planning record; **not authorized for dispatch
or implementation**. These bytes do not self-establish freeze, publication,
landing, implementation, or authority.

Authoring marker: **UNFROZEN**. This is not a live runtime state. An external
identity-bound PASS may later freeze these unchanged bytes and supersede this
marker without mutating this file.

Preparation baseline: `project6-origin/main` at `1b2e170b0d44646d6fe62720058a83d437cc2da2`

## 1. Purpose and authority boundary

This document corrects the B1b successor dispatch specification without replacing or weakening the owner-ratified decisions in D33 and D34. It is a planning and ballot surface only. It does not grant the B1b build-lane second key, authorize a schema change, authorize runtime work, authorize a branch or pull request, or establish that the integrated loop has passed.

Authority remains ordered as follows:

1. Live `project6-origin/main` and its tracked program-context decision records;
   execution additionally requires the exact post-correction main SHA in a valid
   final owner key. The preparation baseline above is audit provenance, not an
   execution-base substitute.
2. The sealed successor packet identified in Section 2.
3. This correction, solely for the gaps and clarifications stated here.

Where this document is silent, the sealed packet remains controlling. Once this
correction lands, its express corrections control the planning specification and
the only valid future ballot; that precedence does not authorize any corrected
action. Execution remains blocked until the owner separately grants the compound
ballot in Section 13. No agent may infer owner authorization from the existence,
location, completeness, merge, or review status of this file.

## 2. Sealed packet binding

This correction binds to exactly this packet:

- Basename: `b1b-successor-packet-2026-07-12.md`
- Workspace-relative path: `state/agent-inbox/b1b-successor-packet-2026-07-12.md`
- Byte length: `38,002`
- Full-file SHA-256: `4895028DF74591B850B1DE4FC619D586AB2D3DD33A2227C4DF0C2BB8F41628FD`
- Canonical packet SHA-256: `A7BD7DF512ED53B97C3A10878C3F8FA040826A8566D4E3347BA3F021E800E38C`

All five values are conjunctive. Before dispatch, the gate auditor must recompute the byte length and full-file SHA-256 and compare the basename and relative path literally. The canonical hash rule is executable and exact: read the complete LF-only UTF-8 file bytes with no BOM; replace only the single 64-hex value immediately after `NEW_FILE_SHA256_CANONICAL=` with 64 ASCII `0` bytes without changing any other byte; SHA-256 the resulting complete file, including its one final LF. Exactly one target must exist. Any mismatch, extra target, missing target, BOM, CR byte, or terminal-newline difference is a hard stop; a similarly named, copied, reflowed, normalized, or reconstructed file is not the sealed packet.

### 2.1 Predecessor and C01 fixture binding

The successor is a mandatory child of this exact prior proof chain, which must
also be reverified before dispatch:

| Artifact | Bytes | Full-file SHA-256 |
|---|---:|---|
| `state/agent-inbox/b1-vertical-loop-packet.md` | 52,631 | `1D0201668A9A4976B2D30267386FE4FCB23413EC717B82CA356EB0DB7919370E` |
| `state/agent-inbox/ct4b-bound-fixture.md` | 27,366 | `EBA6301A9B7B35AEC9D07641F5F16DD93996B26F3CD6AD8A070E0F2FDD664E73` |
| `worktrees/manifest-children/ct4b-fixture-child-manifest.json` | 4,184 | `F56CAD4693468A5163B6FAE30FB3D2AE12044A3014CDA608C451C2B0D82B66B4` |
| `state/agent-inbox/v2-ct4b-fixture-report.md` | 19,449 | `17D43F3E255C84CF6F89CB37655D77066EA245F41FF1BBA523B33E47B3646324` |

The bound input is the canonical regular, non-reparse, Windows-ReadOnly file
`C:/p6fixtures/sciencebase-v1/water-quality.csv`, exactly 34 bytes, SHA-256
`D4EB55501D9003C9C769FA3DBD5D92C9B68A7C42F8BE493A17B1E6EC42ECA3AD`,
with no BOM, zero CR bytes, three LF bytes, and exactly one final LF. Its complete
bytes are:

```text
site_id,value
SB-001,42
SB-002,43
```

The gate auditor must verify the four artifact bindings above and the fixture's
path, regular/non-reparse status, ReadOnly attribute, bytes, length, and hash
before any B1b read. The runtime must repeat the fixture checks immediately
before every read, after package/handoff/replay checks, and at closeout. Any
change or replacement fails closed; a value-equivalent reconstruction is not
F07. The Section 9 predicate-backed negative is valid only when every fixed
F07/C01 field above remains exact and solely `reverified=false`. An actual path,
attribute, readability, identity, byte, length, hash, or completeness mismatch
remains this predecessor hard stop and runtime no-root, never that valid negative.

### 2.2 Earlier owner-selection binding

The operator-root file `state/agent-inbox/owner-decision-record-2026-07-10.md`
is exactly 9,063 bytes with full-file SHA-256
`534CD5A70825C88B3F722754BB0E6DFFB52626C5BB3DA4C32E33FE5AFB24CA9F`.
It is direct authority only for D1 vertical-first and `CT3-08=M1`/C-m4; it is
not D33/D34 authority and does not decide O5. Resolve and verify it only under the
Section 13 operator-context namespace. A copied equivalent is inadmissible.

## 3. Decisions preserved without reinterpretation

### 3.1 D33: material-identity tuple

D33 is the complete 58-disposition record in
`docs/program-context/02-decision-record.md`, Section D33, with disposition count
`58` and overrides `NONE`. That canonical record is incorporated by citation and
is not duplicated here. The executable details below are derived constraints for
this prospective correction; they neither replace the 58-row record nor enlarge
D33's authority.

- The exact preimage is
  `{"fields":{"connector_key":<str>,"media_type":{"charset":<str|null>,"essence":<str>,"parameters":{<lowercased-name>:<str>}},"sciencebase_item_id":<str>},"schema_id":"layer3.connector_source_intake.identity_metadata.v1"}`.
  `source_family` and `content_sha256` are outer tuple axes and are not duplicated
  inside that preimage.
- `connector_key` and `sciencebase_item_id` must be strings, trimmed using Unicode
  whitespace, NFC-normalized, and case-preserved. Empty, missing, or null is
  invalid and unhashable, never a wildcard.
- Parse the complete `media_type`. Lowercase its essence and parameter names;
  reject malformed syntax and duplicate names after lowercasing; unquote, trim,
  and NFC-normalize parameter values; preserve parameter-value case except for
  `charset`; move `charset` to the explicit nullable key and lowercase only its
  token; do not guess aliases (`utf8` is not `utf-8`). Parameter order cannot
  affect the digest.
- Validate every value as a JSON primitive before serialization. The digest is
  exactly
  `sha256(json.dumps(preimage, sort_keys=True, ensure_ascii=True, separators=(",",":"), allow_nan=False).encode("utf-8")).hexdigest()`.
  `default=str` or any other coercion is forbidden. The serialized bytes have no
  BOM or terminal newline; the digest is lowercase 64-hex.
- The operational lookup tuple is exactly
  `(identity_metadata_hash_version, source_family, content_sha256, identity_metadata_hash)`
  and is compared component-by-component, never by raw concatenation or by a
  digest substitute. `source_family` is the exact nonempty server-controlled
  token; `content_sha256` is the recomputed lowercase 64-hex raw-byte digest.
- The same tuple means the same material, not the same capture, request, run,
  decision, or receipt row. The same content digest with different identity
  metadata is distinct material; multiple intake rows may share a tuple and are
  not collapsed. The same identity digest with different reconstructed preimages
  is a critical collision/integrity fault. The same content digest with a
  different recomputed byte length is a corruption fault, not a new identity.
- Version, field set, normalization, null rules, and JSON form change together.
  Any change requires a newly owner-ratified version; v1 is never reinterpreted.
  The persisted `identity_metadata_hash_version` literal is exactly
  `layer3.connector_source_intake.identity_metadata.v1`; that same literal is
  represented in the preimage by `schema_id` and no additional version key is
  permitted. A row missing
  any required field retains capture lineage but keeps both version and hash null
  and is P1-ineligible.
- D33 ratifies only the design of nullable
  `identity_metadata_hash_version String(64)` and
  `identity_metadata_hash String(64)`, their joint-null constraint, and the
  non-unique lookup index
  `ix_l3_connector_intake_material_identity (identity_metadata_hash_version, source_family, content_sha256, identity_metadata_hash)`.
  It grants no persistence implementation, schema/ORM edit, migration, backfill,
  or runtime activation; there is no intake-layer identity uniqueness constraint.
- The compound owner ballot in Section 13.2 prospectively proposes two additional
  B1b policies: permanent no-backfill for all preexisting intake rows, and
  flag-true population only for the exact side-effect-free-classified F07/C01
  path. If that ballot is later validly granted and every separate gate passes,
  preexisting rows remain permanently joint-null and P1-ineligible; flag-false
  and every non-F07/C01 capture also remain joint-null and byte-current. No value
  may be invented. Existing `metadata_hash`, `authority_basis_hash`, constraints,
  and request-replay behavior remain unchanged. Any proposal to broaden
  population or reverse permanent no-backfill requires a new explicit owner
  decision and an amended, independently audited correction.
- Those two policies are `PROPOSED-NOT-RATIFIED` in this planning record. Their
  description creates no schema, migration, backfill, runtime, or dispatch
  authority and must never be attributed to D33.
- Null, malformed, unknown-version, mismatch, collision, or corruption never
  falls back to `metadata_hash`, byte-only identity, filename, URI, storage
  reference, or an arbitrary row. It fails closed with zero promotion reuse.

### 3.2 D34: approved promotion identity

D34 remains ratified exactly as follows:

> For one final I1 identity, the first successfully committed approved receipt
> wins. A later semantically equivalent approval reuses that receipt and mints
> no new receipt. A divergent Gate-B decision fails closed with dedicated `409
> promotion_identity_decision_conflict`, changes zero rows, and requires explicit
> owner-authorized supersession. A prior non-approved decision mints no receipt
> and occupies no promotion identity.

`Prior` is load-bearing. A non-approved decision before any approved receipt is
non-occupying; after an approved receipt exists, a later non-approved decision
for the same I1 is divergent and returns the dedicated zero-row `409
promotion_identity_decision_conflict`.

The dedicated `409 promotion_identity_decision_conflict` is not a continuation
token, a receipt pointer, or permission to reuse without a full-basis comparison.

## 4. Corrected schema choice: Option II only

Option II is the only accepted B1b design: a new persisted `L3ConnectorPromotionReceipt`. Option I may remain a read projection but is rejected as the authoritative receipt because it has no dedicated I1 uniqueness, no receipt foreign-key spine, and no concurrency-safe first-commit winner.

The receipt contract is:

- Inside the existing Gate-B transaction, insert the one receipt only for the
  bounded manifest containing exactly one candidate total, whose single decision
  is approved and whose server-derived identity is exact F07/C01. Mixed or
  multi-candidate manifests, including approved F07 plus denied/flagged siblings,
  stay on byte-current Gate-B and mint no B1b receipt.
- Preserve immutable origin fields: receipt ID and schema version; identity hash version and all outer axes; `identity_metadata_hash`; `canonical_identity_key_hash`; intake ID; Gate-B session, selection-manifest, and material-snapshot IDs; decision-manifest ID and hash; preview and approval hashes; promotion-basis hash; and `created_at`.
- Permit nullable, one-time output links for Dataset, DatasetVersion, promoted session, materialization status, and materialization basis. Those links move only from null to value, or are replayed with the exact same basis. A differing materialization basis fails closed with `409 connector_materialization_basis_conflict`.
- Enforce exactly this authoritative uniqueness tuple:
  `UNIQUE(identity_metadata_hash_version, source_family, content_sha256, identity_metadata_hash)`.
- Add foreign keys for every referenced durable row.
- Treat `canonical_identity_key_hash` as an audit digest only. It never replaces component-wise comparison of the unique tuple.
- Do not automatically backfill historic Gate-B approvals into promotion receipts.

The receipt DDL is exhaustive, not a builder-selected data model. The table is
`l3_connector_promotion_receipt`; its ORM class is
`L3ConnectorPromotionReceipt`; and it contains only these persisted columns:

| Column | Portable SQLAlchemy type | Null | Contract |
|---|---|---:|---|
| `connector_promotion_receipt_id` | `String(36)` | no | primary key; generated UUID string |
| `receipt_schema_version` | `String(64)` | no | exactly `layer3.connector_promotion_receipt.v1` |
| `identity_metadata_hash_version` | `String(64)` | no | immutable lookup-tuple version component |
| `source_family` | `String(64)` | no | immutable D33 outer axis |
| `content_sha256` | `String(64)` | no | lowercase 64-hex D33 outer axis |
| `identity_metadata_hash` | `String(64)` | no | lowercase 64-hex inner metadata digest component |
| `canonical_identity_key_hash` | `String(64)` | no | lowercase 64-hex audit digest |
| `connector_source_intake_record_id` | `String(36)` | no | FK to intake record |
| `gate_b_session_id` | `String(36)` | no | FK to original Gate-B session |
| `gate_b_selection_manifest_id` | `String(36)` | no | FK to original Gate-B selection manifest |
| `gate_b_material_snapshot_id` | `String(36)` | no | FK to approved material snapshot |
| `gate_b_decision_manifest_id` | `String(64)` | no | immutable canonical manifest ID |
| `gate_b_decision_manifest_hash` | `String(64)` | no | lowercase 64-hex complete manifest hash |
| `material_preview_hash` | `String(64)` | no | lowercase 64-hex approved preview hash |
| `approval_hash` | `String(64)` | no | lowercase 64-hex approval-basis hash |
| `promotion_basis_hash` | `String(64)` | no | lowercase 64-hex complete receipt basis |
| `dataset_id` | `String(36)` | yes | one-time FK to materialized Dataset |
| `dataset_version_id` | `String(36)` | yes | one-time FK to materialized DatasetVersion |
| `promoted_session_id` | `String(36)` | yes | one-time FK to promoted session |
| `materialization_status` | `String(32)` | yes | only null, `materializing`, or `materialized` |
| `materialization_basis_hash` | `String(64)` | yes | one-time lowercase 64-hex resolver basis |
| `created_at` | `DateTime(timezone=True)` | no | immutable receipt-commit time |
| `materialized_at` | `DateTime(timezone=True)` | yes | one-time materialization commit time |

Every row-valued reference uses `ON DELETE RESTRICT`/no cascade and has an
explicit index. The primary key and D33 four-column unique constraint are the
only uniqueness rules; no digest-only or target/output uniqueness substitutes
for D33. Add database checks for the exact receipt schema and these only valid
joint states:

1. initial committed receipt: all five output/basis fields
   (`dataset_id`, `dataset_version_id`, `promoted_session_id`,
   `materialization_basis_hash`, `materialized_at`) and
   `materialization_status` are null;
2. uncommitted in-transaction claim: status is `materializing`, basis is
   nonnull, and all output IDs/timestamp remain null; this state must never be
   visible as a committed row;
3. committed output: status is `materialized`, basis, all three output IDs, and
   `materialized_at` are nonnull.

There is no durable `failed` status: a resolver failure rolls the claim and all
output links back to the exact pre-claim state. Origin columns never update;
output columns make one atomic null-to-final transition; an exact-basis replay
performs zero update; and any different or partial transition fails closed.
No JSON, raw path, secret, operator-identity, generic metadata, soft-delete, or
additional status column is permitted. Relationship properties and constraint/
index symbol names may follow existing repo naming conventions, but physical
types, nullability, FKs, delete behavior, logical columns, joint states, and
semantics above may not change without a new audited correction and owner key.

The canonical identity-key digest preimage is exactly:

```json
{"fields":{"content_sha256":"<lowercase-64-hex>","identity_metadata_hash":"<lowercase-64-hex>","identity_metadata_hash_version":"<string>","source_family":"<string>"},"schema_id":"layer3.connector_promotion_identity_key.v1"}
```

It uses the same ratified canonical JSON rules as D33.

### 4.1 Decision equivalence and receipt-hash contracts

The landed Gate-B manifest digest and the new promotion-equivalence digest have
different purposes and must not be substituted for one another.

- `gate_b_decision_manifest_hash` is provenance for the complete decision
  manifest, not for the complete Gate-B request.
  It is exactly `stable_hash(candidate_decision_manifest(decisions))` from
  `layer3_gate_b_state.py`: all complete decision objects, sorted by the string
  `candidate_id`, wrapped by schema `layer3.gate_b_decision_manifest.v1`, and
  serialized by the existing `layer3_utils.stable_json_bytes` implementation
  (`sort_keys=True`, compact separators, `ensure_ascii=False`, UTF-8). The
  `gate_b_decision_manifest_id` must be `gate-b-` plus the first 16 characters of
  that same digest. This legacy manifest hash remains complete lineage; it is
  never the D34 equivalence key and is not reserialized with D33 rules.
- Every new hash defined below uses the D33 serializer exactly: validated JSON
  primitives only, `sort_keys=True`, `ensure_ascii=True`, compact separators,
  `allow_nan=False`, UTF-8, no `default=str`, BOM, or terminal newline.
- For each candidate, reconstruct the four I1 components from the validated
  intake row; request-supplied identity components are never authoritative. The
  exact semantic-decision preimage is:

```json
{"decision":"<approved|denied|isolated|flagged>","eligibility_policy_id":"layer3.connector_promotion_eligibility.f07-c01.v1","identity":{"content_sha256":"<lowercase-64-hex>","identity_metadata_hash":"<lowercase-64-hex>","identity_metadata_hash_version":"<string>","source_family":"<string>"},"schema_id":"layer3.connector_promotion_decision_semantics.v1"}
```

For a committed approval, the digest of that preimage is stored as
`approval_hash`. Candidate ID, request/run/target/intake IDs, operator reason,
freshness, full manifest composition, and preview lineage are deliberately not
semantic approval axes; they remain auditable through the immutable winning
receipt lineage. A later approval is semantically equivalent only when all four
I1 components, the eligibility policy, and this digest equal the stored values.
A later non-approved
decision necessarily has a different semantic digest and, after an approved
receipt exists, is D34 divergence.

The complete winning-receipt basis preimage is exactly:

```json
{"approval_hash":"<lowercase-64-hex>","gate_b":{"decision_manifest_hash":"<lowercase-64-hex>","decision_manifest_id":"gate-b-<16-lowercase-hex>","material_preview_hash":"<lowercase-64-hex>","material_snapshot_id":"<uuid-string>","selection_manifest_id":"<uuid-string>","session_id":"<uuid-string>"},"identity":{"canonical_identity_key_hash":"<lowercase-64-hex>","content_sha256":"<lowercase-64-hex>","identity_metadata_hash":"<lowercase-64-hex>","identity_metadata_hash_version":"<string>","source_family":"<string>"},"intake":{"connector_source_intake_record_id":"<uuid-string>"},"receipt_schema_version":"layer3.connector_promotion_receipt.v1","schema_id":"layer3.connector_promotion_receipt_basis.v1"}
```

Its D33-canonical digest is `promotion_basis_hash`. It binds every immutable
winning origin field except the generated receipt ID and commit timestamp. A
later equivalent approval reuses the first receipt after verifying its complete
stored basis for integrity; new request lineage does not replace, update, or
need to equal that winning basis.

Gate-B enters the single-I1 v1 flow atomically as follows:

1. Before new I1 validation or mutation, a side-effect-free server check examines
   the entire manifest. The B1b shape is exactly one candidate total with
   server-known connector-only F07 source family, connector key, ScienceBase item
   ID, media type, 34-byte content length, and F07 content hash; its decision may
   be approved, denied, isolated, or flagged. Mixed, multi-candidate,
   other-connector, other-content, and legacy manifests bypass every new branch
   and follow byte-current Gate-B. Exact-shape manifests also follow byte-current
   Gate-B when the flag is false. When the flag is true, exact shape requires the
   valid Section 8 attestation before continuing; absent/invalid attestation is
   `503 connector_promotion_bridge_unavailable` and zero mutation. `B1b
   arbitration scope` means exact shape plus true flag plus valid attestation.
2. For the one arbitration-scoped candidate, reconstruct the complete D33
   preimage/tuple and re-read/rehash the raw object. A missing, malformed,
   mismatched, collided, or corrupt field fails closed before any Gate-B row or
   file. Approved and non-approved decisions acquire the same Section 10 writer
   arbitration so D34 precedence is race-safe.
3. `Receipt mint eligibility` is arbitration scope plus decision `approved` plus
   strict transform/method-input reproduction. Under the lock, eligible plus
   absent I1 mints one receipt; eligible plus equivalent existing receipt reuses
   it; non-approved plus absent I1 commits the current no-receipt Gate-B path;
   any decision divergent from an existing approved receipt rolls back the whole
   transaction and returns `409 promotion_identity_decision_conflict`.
4. The internal result has exactly `candidate_id`, `decision`,
   `receipt_disposition` (`created`, `reused`, or `none`), and nullable receipt ID.
   It is consumed only by the promotion service/resolver, never added to the
   existing Gate-B response/OpenAPI model, and never changes a prior receipt.

The v1 eligibility policy is deliberately narrower than generic connector
approval. A receipt may be minted only when the flag is true, the complete
owner/packet preflight passes, the server-verified candidate is connector-only
with exact identity
`(layer3.connector_source_intake.identity_metadata.v1, connector_produced_single_source, d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad, 6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7)`,
its raw object is exactly 34 bytes, strict UTF-8/CSV parsing reproduces the frozen
transformation and method-input hashes in Section 5, and the manifest contains
exactly one candidate total whose decision is approved. That identity is reconstructed from
`connector_key=sciencebase_public`,
`sciencebase_item_id=synthetic-sb-item-001`, and `media_type=text/csv`; its
canonical identity-key hash is
`2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0`.
All other connector manifests remain on the byte-current Gate-B path and mint no
B1b receipt; they are not rejected or generalized by this correction. A future
eligibility policy, fixture, identity, or transform requires an amended
correction and owner key.

### 4.2 Materialization basis, durable record, and target mutation

The resolver arbitration key is the D33-canonical SHA-256 of exactly this
`layer3.connector_promotion_materialization_basis.v1` object:

```json
{"code":{"dataframe_io_git_blob":"<40-lowercase-hex>","implementation_commit":"<40-lowercase-hex>","ingest_git_blob":"<40-lowercase-hex>","metadata_contract_sha256":"86d8ab86401f1a7fa84f42e63bc288da1fe05d670cde1ec98c9387f136deb644","promotion_git_blob":"<40-lowercase-hex>"},"expected_output":{"column_count":2,"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"dropped_row_count":0,"row_count":2,"source_row_count":2},"input":{"bytes":34,"content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","storage_ref_hash":"<lowercase-64-hex>"},"lineage":{"connector_run_id":"<uuid-string>","connector_run_target_id":"<uuid-string>","connector_source_intake_record_id":"<uuid-string>","gate_b_material_snapshot_id":"<uuid-string>","gate_b_selection_manifest_id":"<uuid-string>","gate_b_session_id":"<uuid-string>"},"receipt":{"canonical_identity_key_hash":"<lowercase-64-hex>","connector_promotion_receipt_id":"<uuid-string>","promotion_basis_hash":"<lowercase-64-hex>"},"schema_id":"layer3.connector_promotion_materialization_basis.v1","transformation":{"contract_sha256":"951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179","method_input_sha256":"907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b","parameters":{},"schema_id":"layer3.connector_promotion_transform.v1","version":"1"}}
```

The metadata contract bound above is the 2,180-byte D33-canonical object below;
its SHA-256 is
`86d8ab86401f1a7fa84f42e63bc288da1fe05d670cde1ec98c9387f136deb644`:

```json
{"dataset":{"description":"Two-row synthetic, non-temporal, non-official C01 fixture for local B1b proof only.","domain_pack":null,"frequency_hint":null,"name":"Synthetic F07 C01 connector material","time_column":null},"dataset_source_provenance":{"artifact_locator_type":"intake_storage_ref","artifact_surface":"synthetic_fixture","blocked_reason":null,"discovered_at":null,"downloaded_at":null,"downloaded_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","etag":null,"fetch_policy_mode":"synthetic_local_no_network","last_modified":null,"raw_storage_ref_policy":"reuse_exact_intake_storage_ref","redirect_count":null,"remote_checksum_type":null,"remote_checksum_value":null,"resolved_ip":null,"retrieved_http_json":{},"sciencebase_download_uri":null,"sciencebase_file_name":null,"sciencebase_item_id":"synthetic-sb-item-001","sciencebase_item_url":null,"source_artifact_key":"f07-c01-synthetic","source_mode":"synthetic_local_direct_intake","source_query_fingerprint":null,"source_reference_json_policy":"exact_materialization_wrapper_only","source_system":"sciencebase_public_synthetic_fixture"},"dataset_version":{"content_hash":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","dropped_row_count":0,"notes":"synthetic=true; official_public_read_evidence=false; f20_status=NOT-ESTABLISHED; encoding=utf-8; transform=layer3.connector_promotion_transform.v1","parent_version_id":null,"row_count":2,"source_row_count":2,"status":"ready","storage_ref_policy":"final_parquet_under_dataset_storage_root","version_label":"b1b_f07_c01_v1","version_type":"synthetic_connector_promotion"},"schema_id":"layer3.connector_promotion_materialization_metadata.v1","source_connector":{"api_available_flag":false,"automation_tier":"tier_0","cleanup_burden":null,"domain_pack":null,"source_category":"synthetic_local_proof","source_name":"synthetic_f07_c01_connector","update_cadence":null},"variables":[{"dtype":"object","is_numeric":false,"is_time_index":false,"ordinal_position":0,"role":"measure","variable_name":"site_id"},{"dtype":"float64","is_numeric":true,"is_time_index":false,"ordinal_position":1,"role":"measure","variable_name":"value"}]}
```

Generated IDs and model timestamps are the only values outside this profile.
`DatasetVersion.storage_ref` is the server-private final Parquet reference;
`DatasetSourceProvenance.raw_storage_ref` is the exact existing intake reference,
never a copy; and `source_reference_json` is exactly the materialization wrapper
defined below. Every other model column not represented by a value or policy in
the profile is null/default exactly as shown. The promotion service must not call
the legacy copy-producing `ingest_csv_bytes_to_dataset` path; it extracts or uses
a no-commit, existing-reference primitive that reproduces this profile exactly.

Required foreign-key values are equality bindings, not executor metadata:
`Dataset.source_id` equals the new `SourceConnector.source_id`;
`DatasetVersion.dataset_id` equals that Dataset; both VariableDefinition rows and
the provenance row equal that DatasetVersion; and
`DatasetSourceProvenance.connector_run_id` equals the bound capture
`ConnectorRun`. The receipt's three output FKs equal the resulting Dataset,
DatasetVersion, and promoted session. This provenance schema has no target FK;
target lineage remains through the receipt/basis and the existing target's exact
two output links. No other FK may be populated.

`materialization_basis_hash` is that digest. All commit/blob IDs are re-read
from the clean audited implementation checkout immediately before the claim;
dirty, missing, non-hex, or changed code identity fails before mutation.
`storage_ref_hash` is SHA-256 over the ASCII bytes
`project6-storage-ref-v1`, followed by exactly one NUL byte `0x00`, followed by
`relative_ref.encode("utf-8")`, where
`relative_ref` is obtained only after resolving the intake storage reference,
proving it is a regular non-reparse file contained by the configured storage
root, converting the root-relative path to `/`, NFC-normalizing it,
case-preserving it, and rejecting empty segments, `.`, `..`, a drive prefix,
UNC syntax, NUL, or a leading/trailing slash. The relative reference itself is
never persisted in a B1b projection.

`dataset_storage_ref_hash` uses the same containment and relative-path
normalization against the independently configured DatasetVersion storage root,
but its distinct preimage is ASCII `project6-dataset-storage-ref-v1`, one NUL,
then the normalized UTF-8 relative reference. Input and output domains are never
interchanged. Before final commit, re-resolve both roots and references, reject
reparse/nonregular/cross-root results, and re-read final file bytes/length.

Materialization ordering is stage, verify, publish, reverify, then database
commit. Write the Parquet to an absent lane-owned staging file on the same volume,
flush/close it, reopen and hash it, and flush all uncommitted rows. Require the
final relative destination
`b1b/dataset-versions/<basis-hash-first-two>/<materialization_basis_hash>.parquet`
absent, then atomically rename on that volume without overwrite. The destination
is basis-derived, never UUID-derived. Reopen the final file, reproduce
bytes/hash, fill the closed record and receipt/target links, and commit once. A failure before publish
leaves no authoritative output. A failure after publish but before commit rolls
back every row/link, rehashes and moves the orphan only to lane containment under
the no-delete rule, and records it as non-authoritative/non-reusable. Replay
reopens and rehashes the already-linked final file and creates no staging file.

Exception cleanup is not crash recovery. Under the I1 writer lock and before
every claim/retry, census the deterministic final path and the lane-owned B1b
staging namespace against committed DatasetVersion/receipt references. Rehash
and move every unreferenced final or staging file into containment, record its
basis/path-namespace hash and non-authoritative status, and refuse to adopt it
even when its bytes match. Only a final file already linked by the one exact
committed receipt is replayable. A kill-after-rename/before-commit test must
restart in a fresh process/session, discover and contain the orphan, then prove
the retry creates one authoritative file with no silent accumulation.

After the staged file and database rows have been verified but before the final
receipt transition commits, build this redacted record:

```text
{"basis_hash":"<materialization_basis_hash>","output":{"dataset_file_bytes":<positive-integer>,"dataset_file_sha256":"<lowercase-64-hex>","dataset_id":"<uuid-string>","dataset_source_provenance_id":"<uuid-string>","dataset_storage_ref_hash":"<lowercase-64-hex>","dataset_version_content_sha256":"<lowercase-64-hex>","dataset_version_id":"<uuid-string>","dropped_row_count":0,"promoted_session_id":"<uuid-string>","row_count":2,"source_connector_id":"<uuid-string>","source_row_count":2,"variable_count":2},"schema_id":"layer3.connector_promotion_materialization_record.v1"}
```

Compute `record_hash` over that record and persist the exact wrapper
`{"record":<record>,"record_hash":"<lowercase-64-hex>"}` identically at
`promoted_session.operator_context_json["layer3_connector_promotion_materialization_v1"]`
and
`dataset_source_provenance.source_reference_json["layer3_connector_promotion_materialization_v1"]`.
`record_hash` is the D33-canonical SHA-256 of the inner
`layer3.connector_promotion_materialization_record.v1` object, not of the
wrapper. The resolve response's `materialization_record_hash` and
`dataset-lineage.json.materialization.materialization_record_sha256` both equal
that same inner `record_hash` byte-for-byte. They are aliases, not two
producers. The persisted wrapper is not separately hashed and is not a
normative digest preimage; no wrapper-hash field or alternate digest is
permitted. The 848-byte vector below remains the normative inner-record vector.
The receipt row's `materialization_basis_hash` must equal `record.basis_hash`, and
the inner record's output IDs/hashes/counts must equal the linked rows and re-read
file. `dataset_version_content_sha256` is the fixture/input digest stored in
`DatasetVersion.content_hash`; `dataset_file_sha256` is independently recomputed
over the final Parquet bytes and is never substituted by the input digest. No raw
storage reference or extra B1b receipt JSON is permitted. A mismatch
rolls back the final transition and contains the staged file as a failed,
non-authoritative artifact.

The existing `ConnectorRunTarget` changes in place only by setting its previously
null `dataset_id` and `dataset_version_id` to the receipt-linked outputs; the ORM
may update its standard `updated_at`. Status, stage timestamps, reason/error
fields, source/provenance fields, raw reference, and every other target column
remain byte-equivalent. A non-null unequal link is a hard conflict; exact links
are a zero-update replay.

### 4.3 Handoff idempotency basis and golden vectors

Package construction stores only the approved result-review hash, the
server-derived package-review **preview** hash, package IDs/hashes/byte lengths,
and pre-operation eligibility—not package bytes, paths, or a not-yet-existent
approved package-review hash—in the existing reconciliation summary. After the
immutable three-package set has closed, the existing package-review submit
operation validates that set and, in the same transaction as the approved
review state, derives and stores the final handoff basis below. Prepare is then
read-only and validates that stored basis. The idempotency preimage is exactly:

```text
{"approved_reviews":{"package_review_hash":"<lowercase-64-hex>","result_review_hash":"<lowercase-64-hex>"},"canonical_internal":{"byte_length":<positive-integer>,"output_package_id":"<uuid-string>","payload_hash":"<lowercase-64-hex>"},"package_set":{"reconciliation_record_id":"<uuid-string>","review_facing_output_package_id":"<uuid-string>","review_facing_payload_hash":"<lowercase-64-hex>","user_facing_output_package_id":"<uuid-string>","user_facing_payload_hash":"<lowercase-64-hex>"},"promoted_session_id":"<uuid-string>","promotion_receipt_id":"<uuid-string>","schema_id":"layer3.connector_dataset_handoff_basis.v1"}
```

The D33-canonical digest is stored as
`connector_dataset_handoff_basis_hash` only by the successful approved
package-review submit transaction. Exact replay returns the same eligibility
projection without mutation; any field difference is a conflict. The two review
hashes are the persisted hashes of the exact approved result-review and
package-review records, not caller-provided labels. Package construction may
store the preview hash and expected review input, but it must not prepopulate,
predict, or embed either the final handoff-basis hash or an approved
package-review hash.

The following golden vectors are normative. Production helpers and tests must
reproduce both the byte counts and lowercase SHA-256 values; changing a byte,
normalization rule, schema ID, field, or type requires a correction amendment.

Legacy Gate-B manifest vector—266 bytes; SHA-256
`d638c20b28c201a5b18747519547fd5af332d445e66b966282c84c29732c9963`;
ID `gate-b-d638c20b28c201a5`:

```json
{"items":[{"candidate_id":"mat-a","decision":"approved","decision_basis":{"x":1},"operator_reason":""},{"candidate_id":"mat-b","decision":"denied","decision_basis":{"x":2},"operator_reason":"out"}],"schema_id":"layer3.gate_b_decision_manifest.v1","schema_version":1}
```

D33 F07 identity vector—228 bytes; SHA-256
`6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7`:

```json
{"fields":{"connector_key":"sciencebase_public","media_type":{"charset":null,"essence":"text/csv","parameters":{}},"sciencebase_item_id":"synthetic-sb-item-001"},"schema_id":"layer3.connector_source_intake.identity_metadata.v1"}
```

Canonical F07 identity-key vector—383 bytes; SHA-256
`2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0`:

```json
{"fields":{"content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","identity_metadata_hash":"6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7","identity_metadata_hash_version":"layer3.connector_source_intake.identity_metadata.v1","source_family":"connector_produced_single_source"},"schema_id":"layer3.connector_promotion_identity_key.v1"}
```

Approval vector—489 bytes; SHA-256
`197ab9e9d6c753483c01d2a86787ed222c5aa22e3292c48df6d250e2e2540a65`:

```json
{"decision":"approved","eligibility_policy_id":"layer3.connector_promotion_eligibility.f07-c01.v1","identity":{"content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","identity_metadata_hash":"6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7","identity_metadata_hash_version":"layer3.connector_source_intake.identity_metadata.v1","source_family":"connector_produced_single_source"},"schema_id":"layer3.connector_promotion_decision_semantics.v1"}
```

Promotion-basis vector—1,137 bytes; SHA-256
`cd3edda3b436481aaf4caaa39d483b54b2c86979ae9b6df6b293d1c1c9e6a938`:

```json
{"approval_hash":"197ab9e9d6c753483c01d2a86787ed222c5aa22e3292c48df6d250e2e2540a65","gate_b":{"decision_manifest_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","decision_manifest_id":"gate-b-dddddddddddddddd","material_preview_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","material_snapshot_id":"44444444-4444-4444-4444-444444444444","selection_manifest_id":"33333333-3333-3333-3333-333333333333","session_id":"22222222-2222-2222-2222-222222222222"},"identity":{"canonical_identity_key_hash":"2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0","content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","identity_metadata_hash":"6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7","identity_metadata_hash_version":"layer3.connector_source_intake.identity_metadata.v1","source_family":"connector_produced_single_source"},"intake":{"connector_source_intake_record_id":"11111111-1111-1111-1111-111111111111"},"receipt_schema_version":"layer3.connector_promotion_receipt.v1","schema_id":"layer3.connector_promotion_receipt_basis.v1"}
```

Materialization-basis vector—1,787 bytes; SHA-256
`2f4b1251c42f753558d66352218358883c33de44543adfc497d209b783dfaca7`:

```json
{"code":{"dataframe_io_git_blob":"4444444444444444444444444444444444444444","implementation_commit":"1111111111111111111111111111111111111111","ingest_git_blob":"3333333333333333333333333333333333333333","metadata_contract_sha256":"86d8ab86401f1a7fa84f42e63bc288da1fe05d670cde1ec98c9387f136deb644","promotion_git_blob":"2222222222222222222222222222222222222222"},"expected_output":{"column_count":2,"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"dropped_row_count":0,"row_count":2,"source_row_count":2},"input":{"bytes":34,"content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","storage_ref_hash":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"},"lineage":{"connector_run_id":"66666666-6666-6666-6666-666666666666","connector_run_target_id":"77777777-7777-7777-7777-777777777777","connector_source_intake_record_id":"11111111-1111-1111-1111-111111111111","gate_b_material_snapshot_id":"44444444-4444-4444-4444-444444444444","gate_b_selection_manifest_id":"33333333-3333-3333-3333-333333333333","gate_b_session_id":"22222222-2222-2222-2222-222222222222"},"receipt":{"canonical_identity_key_hash":"2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0","connector_promotion_receipt_id":"55555555-5555-5555-5555-555555555555","promotion_basis_hash":"cd3edda3b436481aaf4caaa39d483b54b2c86979ae9b6df6b293d1c1c9e6a938"},"schema_id":"layer3.connector_promotion_materialization_basis.v1","transformation":{"contract_sha256":"951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179","method_input_sha256":"907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b","parameters":{},"schema_id":"layer3.connector_promotion_transform.v1","version":"1"}}
```

Materialization-record vector—848 bytes; SHA-256
`b43f3ba85a0ec153367368cc7a895dd8d0377a282d65ef6ac81df4c8e3483d0f`:

```json
{"basis_hash":"2f4b1251c42f753558d66352218358883c33de44543adfc497d209b783dfaca7","output":{"dataset_file_bytes":1234,"dataset_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","dataset_id":"88888888-8888-8888-8888-888888888888","dataset_source_provenance_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","dataset_storage_ref_hash":"9999999999999999999999999999999999999999999999999999999999999999","dataset_version_content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","dataset_version_id":"99999999-9999-9999-9999-999999999999","dropped_row_count":0,"promoted_session_id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb","row_count":2,"source_connector_id":"cccccccc-cccc-cccc-cccc-cccccccccccc","source_row_count":2,"variable_count":2},"schema_id":"layer3.connector_promotion_materialization_record.v1"}
```

Handoff-basis vector—977 bytes; SHA-256
`c50b1d64c491b469db72cf945789f635102b1ed11280721572bc3f6210913fa3`:

```json
{"approved_reviews":{"package_review_hash":"1111111111111111111111111111111111111111111111111111111111111111","result_review_hash":"2222222222222222222222222222222222222222222222222222222222222222"},"canonical_internal":{"byte_length":1234,"output_package_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","payload_hash":"3333333333333333333333333333333333333333333333333333333333333333"},"package_set":{"reconciliation_record_id":"99999999-9999-9999-9999-999999999999","review_facing_output_package_id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb","review_facing_payload_hash":"4444444444444444444444444444444444444444444444444444444444444444","user_facing_output_package_id":"cccccccc-cccc-cccc-cccc-cccccccccccc","user_facing_payload_hash":"5555555555555555555555555555555555555555555555555555555555555555"},"promoted_session_id":"88888888-8888-8888-8888-888888888888","promotion_receipt_id":"55555555-5555-5555-5555-555555555555","schema_id":"layer3.connector_dataset_handoff_basis.v1"}
```

## 5. Corrected B1b implementation tranche

The authorized tranche, if and only if Section 13 is validly granted, consists of B1b-01 through B1b-06 below. No adjacent cleanup, generalized framework, user-interface work, connector-family expansion, or real-network orchestration is included.

### 5.1 Exact corrected file fence

The original packet's blast-radius descriptions plus this correction resolve to the
following exhaustive allowed edit set. A later gate may narrow it, but may not add a path
without returning to audit and obtaining an amended owner-bound correction.

Core, persistence, services, and API:

1. `backend/app/core/config.py`
2. `backend/app/models/models.py`
3. `backend/app/models/__init__.py`
4. exactly one new `backend/alembic/versions/<b1b-rebased-revision>.py`, whose exact
   basename and parent revision are frozen after the entry-gate head rebase and before any
   model/migration edit
5. `backend/app/services/layer3_connector_source_intake.py`
6. one new `backend/app/services/layer3_connector_promotion.py`
7. one new `backend/app/services/layer3_connector_dataset_handoff.py`
8. `backend/app/services/layer3_workbench.py`
9. `backend/app/services/layer3_pass_entry.py`
10. `backend/app/services/ingest.py`
11. `backend/app/services/dataframe_io.py`
12. `backend/app/services/layer3_package_entry.py`
13. `backend/app/api/layer3/__init__.py`
14. `backend/app/api/layer3/source_ingestion.py`
15. `backend/app/api/layer3/handoff.py`
16. `backend/app/api/layer3/package.py`
17. `backend/main.py`

Tests:

18. one new `backend/tests/test_layer3_connector_promotion_bridge.py`
19. `backend/tests/test_layer3_connector_vertical_loop.py`
20. `backend/tests/test_layer3_migrations.py`
21. `backend/tests/test_pre_body_operator_authorization.py`
22. `backend/tests/test_layer3_post_route_operator_authorization_coverage.py`
23. `backend/tests/test_support_matrix.py`
24. `backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py`
25. `backend/tests/test_sec_xbrl_offline_honesty_ceiling_exhaustive.py`
26. `backend/tests/test_layer3_deploy_compose_contract.py`
27. `backend/tests/test_layer3_safety_contract.py`
28. `tests/test_api.py`
29. one new `backend/tests/test_layer3_b1b_runner.py`

Support, dependent enforcement, current documentation, and environment mirrors:

30. one new `scripts/run-b1b-proof.ps1`
31. `config/support_matrix.yaml`
32. `scripts/support_matrix_constants.py`
33. `scripts/support_matrix_check.py`
34. `scripts/support_matrix_runtime_contract_audit.py`
35. `scripts/local_profile_acceptance.py`
36. `docs/support-matrix-local-expert.md`
37. `docs/first-boot-capabilities.md`
38. `README.md`
39. `docs/layer3-production-activation.md`
40. `docs/layer3-route-authorization.md`
41. `next_milestone_plans/Layer3_planning_docs/1366-source-artifact-admission-map.md`
42. `deploy/docker-compose.production.yml`
43. `backend/.env.example`
44. `backend/.env.production.example`
45. `deploy/.env.deploy.example`
46. `docs/layer3-nonlocal.env.template`
47. one new `backend/tests/requirements-b1b-proof.lock.txt`
48. `docs/dependency-and-environment-reproducibility.md`

Proof control plugin:

49. one new `backend/b1b_pytest.py`

Canonical closeout/status surfaces:

50. `docs/MASTER_CONTEXT.md`
51. `docs/program-context/00-posture-and-invariants.md`
52. `docs/program-context/01-arc-ledger.md`
53. `docs/program-context/02-decision-record.md`
54. `docs/program-context/03-forward-plan.md`
55. `docs/program-context/04-evidence-registry.md`
56. `next_milestone_plans/layer3_progress_manifest.json`
57. `next_milestone_plans/layer3_workbench_proof_manifest.json`
58. `next_milestone_plans/layer3_progress_board.md`

Paths 50-58 are a separate post-merge records-closeout tranche. They must not
claim B1b PASS in the implementation PR. Only after the implementation merge and
the independent rerun from the exact merged `project6-origin/main` SHA passes may
a records writer update them in a fresh clean docs worktree; an independent
post-closeout records reviewer then directly produces the exact Section 9
`records_semantic_review` object from the landed nine-path diff. Only semantic-
review PASS permits the final aggregator's one fresh fetch and machine records-
parity evaluation.
Until that docs-only closeout lands, B1b may be runtime-proven but is not
administratively current/closed. No source or runtime file is edited in that
post-merge tranche. Pre-merge changes to other documentation in this fence must
say target/default-off/pending, never implemented or passed.

If a final correction identity is landed and hash-bound, that tracked file must
be immutable before dispatch and is not a B1b implementation edit. These bytes
do not self-establish that freeze/publication condition. PR/closeout text is
evidence, not a substitute for a file-fence entry.
Any need for another source, test, migration, configuration, documentation, package, route,
or generated file is a hard pre-edit STOP and correction/owner-key amendment; it is not an
executor discretion.

### B1b-01: promotion receipt and resolver

- Add default-false `LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED`.
- Insert the one Option II receipt in the existing Gate-B transaction only under
  the exact single-I1 arbitration/mint policy in Sections 4 and 10.
- Make the resolver/materializer non-decisional. It locks or atomically claims the receipt, rehashes the existing raw object, and either materializes exactly once or reuses the exact materialization basis.
- Do not persist a second raw copy. Extract a no-commit existing-reference primitive from the current ingestion path where needed.
- Create a separate promoted `L3Session` containing exactly one `dataset_version` snapshot. Never relabel the original E2 connector snapshot and never mix connector and dataset snapshots in one session.
- With the flag false, preserve byte/status/code-path parity for the existing
  Gate-B response/model/errors and all ordinary noneligible connector/session,
  plan, review, package, and handoff paths; create no B1b row or application file
  and do not backfill. The only intentional parity exclusions are the additive
  support/OpenAPI inventory entries, the three new routes returning their defined
  default-off `503 connector_promotion_bridge_unavailable`, and the inert
  additive migration schema itself. Schema presence is not permission for a
  runtime row delta.

### B1b-02: canonical 3C typing

- Reuse current DatasetVersion typing.
- Create exactly one each of `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisGroup`, and `L3AnalysisSet` for the promoted snapshot.
- Prefer zero typing-engine changes. Any claimed need to modify shared typing semantics returns the lane to audit rather than widening B1b.

### B1b-03: synthetic C01 analysis

Freeze the analysis question as:

- Question ID: `CT4B-C01-DESC-001`
- Question text: the exact single-line UTF-8 value below, excluding the Markdown fence
  and terminal newline:

```text
Within the two synthetic C01 rows (`SB-001=42` and `SB-002=43`), what per-column classification, missingness, top values, and `value` minimum, maximum, mean, median, and sample standard deviation does `descriptive_summary` report, subject to the fixture being synthetic, non-temporal, and too small for official, causal, or population-wide inference?
```

- Method: `descriptive_summary`
- Parameters: `{}`
- `goal_type`: null
- `annotation_window_id`: null
- Inputs: the expected promoted DatasetVersion ID and promotion-receipt ID
- Method schema, method version, transformation hash, method-input hash, and
  method-contract hash: the exact v1 contracts below

All three preimages use D33 canonical JSON: UTF-8, lexicographically sorted
object keys at every depth, compact separators, JSON lowercase booleans/null,
JSON numbers, preserved array order, no BOM, and no terminal newline. SHA-256 is
over exactly those canonical bytes.

Transformation receipt preimage (531 bytes; SHA-256
`951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179`):

```json
{"input":{"bom":false,"bytes":34,"encoding":"utf-8-strict","final_lf":true,"line_endings":"lf","sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad"},"output":{"coercion_count":0,"column_count":2,"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"drop_count":0,"row_count":2,"rows":[["SB-001",42],["SB-002",43]]},"parse":{"fallbacks":[],"header":["site_id","value"],"row_order":"source"},"schema_id":"layer3.connector_promotion_transform.v1"}
```

Method-input preimage (224 bytes; SHA-256
`907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b`):

```json
{"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"rows":[["SB-001",42],["SB-002",43]],"schema_id":"layer3.descriptive_summary.input.v1","time_column":null}
```

Method-contract preimage (894 bytes; SHA-256
`586745d83f62f60e32a94fb62cd5557341866e5319d48eece7d0ea741a5e89e5`):

```json
{"analysis_authority":{"git_blob":"e38beab8a29d3e024a442573624199dc2e93fba0","path":"backend/app/services/analysis.py","runner":"_run_descriptive_summary"},"annotation_window_id":null,"dependency_lock_git_blob":"3a0fec8abe04341a192822862dfa0be1861d137b","goal_type":null,"method_id":"descriptive_summary","method_input_sha256":"907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b","method_version":"1","parameters":{},"question_id":"CT4B-C01-DESC-001","question_text":"Within the two synthetic C01 rows (`SB-001=42` and `SB-002=43`), what per-column classification, missingness, top values, and `value` minimum, maximum, mean, median, and sample standard deviation does `descriptive_summary` report, subject to the fixture being synthetic, non-temporal, and too small for official, causal, or population-wide inference?","schema_id":"layer3.descriptive_summary.method_contract.v1"}
```

Parsing is strict UTF-8 with no fallback, row dropping, value coercion, column
reordering, or row reordering. The actual DatasetVersion Parquet bytes and
storage object are rehashed for integrity, but cross-run deterministic Parquet
bytes are not claimed unless separately proven. At entry, reverify the pinned
`analysis.py` and `backend/requirements.lock.txt` Git blobs; any drift
requires a correction amendment rather than an executor-selected method version.
The `dependency_lock_git_blob` in this method contract is deliberately the
release/application lock that governs analysis semantics; it is not the
Section 16 Windows proof-environment lock, which is bound separately and never
changes this golden preimage.

The persisted materialization receipt additionally binds the code that executed
the stable semantic contract. It records
`transformation_schema_id=layer3.connector_promotion_transform.v1`,
`transformation_version=1`, `transformation_parameters={}`,
`transformation_contract_sha256=951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179`,
the audited final implementation commit, and the final Git blob IDs for
`layer3_connector_promotion.py`, `ingest.py`, and `dataframe_io.py`. Missing,
dirty, or post-audit-different code identity fails the receipt and closeout.

For receipt-bound promoted sessions only, the server must derive these values into the
owner plan payload in `layer3_pass_entry.py` before preview hashing. No request-model field
or caller-supplied override may set or replace them. With the flag false, plan formation and
preview hashing remain byte-current.

### B1b-04: review projection

- Add only server-derived `connector_b1_evidence` for the scoped connector result-review path.
- Do not accept client-supplied evidence widening.
- Preserve ordinary non-connector session responses and review behavior byte-for-byte when the feature is disabled or the session is out of scope.

For a receipt-bound B1b session, the generic result-review request/state is
narrowed to a redacted closed profile. The request contains exactly
`client_request_id`, `session_id`, `analysis_plan_id`, `pass_run_id`,
`preview_id`, `preview_hash`, `analysis_run_id`, `operator_decision`, and
`review_notes`; `reviewed_output_items` and every generic optional field are
absent. The service derives and locks the authoritative result artifact,
payload hash, four checks, and one caveat. It creates exactly two reviewed item
projections in order:

1. `{index:0,item_ref:"analysis-artifact:<analysis_artifact_id>",item_type:"fact",trace_status:"resolved",missing_trace_fields:[]}`;
2. `{index:1,item_ref:"caveat:<caveat_note_id>",item_type:"caveat",trace_status:"resolved",missing_trace_fields:[]}`.

`operator_decision` is exactly one of `approved`, `changes_requested`,
`rejected`, or `blocked`. For `approved`, `review_notes` is exactly the empty
string and is persisted as null. For each other decision,
`normalized_review_notes=review_notes.strip()` must be nonempty and that
stripped string is persisted exactly as JSON; no other normalization or
substitution is allowed. The request basis is the exact request without `client_request_id`;
its D33-canonical SHA-256 is `result_review_request_basis_hash`, and
`client_request_id` is exactly
`b1b-result-review-<result_review_request_basis_hash>`.

The persisted record for every decision is the following exhaustive preimage,
with no
timestamp, raw/storage reference, URL, request identity, or caller-supplied
projection:

```text
schema_id = layer3.b1b_result_review_record.v1
promotion_receipt_id = <UUID string>
promoted_session_id = <UUID string>
analysis_plan_id = <UUID string>
pass_run_id = <UUID string>
preview_id = <nonempty string>
preview_hash = <lowercase 64-hex>
analysis_run_id = <UUID string>
result_payload_sha256 = <lowercase 64-hex>
analysis_artifact_id = <UUID string>
analysis_artifact_sha256 = <lowercase 64-hex>
assumption_check_ids = <ordered array of exactly four UUID strings>
caveat_note_id = <UUID string>
reviewed_output_items = <the exact two-object array above>
unresolved_trace_count = 0
operator_decision = <approved|changes_requested|rejected|blocked>
review_notes = <null when approved; otherwise normalized_review_notes>
result_review_request_basis_hash = <lowercase 64-hex>
```

No other key is permitted. The D33-canonical SHA-256 of that object is
`result_review_hash`, and `review_record_ref` is exactly
`b1b-result-review-<result_review_hash>`. The pass summary stores that closed
record plus `review_record_ref`, the mapped `review_state`, and
`result_review_hash`. The session summary uses one stable schema for every later
outcome and has exactly twelve keys:
`schema_id=layer3.b1b_session_state.v1`, `review_record_ref`, `review_state`,
`result_review_hash`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`,
`package_review_state`, `package_review_hash`, `reconciliation_record_id`,
`packages`, and `connector_dataset_handoff_basis_hash`. Result review writes the
first seven keys and sets the last five exactly to null. No later operation
removes a key, swaps a schema, or stores the full handoff basis in the session;
that complete basis remains reconciliation-only. The exhaustive decision-to-state map is
`approved -> execution_result_review_approved`,
`changes_requested -> execution_result_review_changes_requested`,
`rejected -> execution_result_review_rejected`, and
`blocked -> execution_result_review_blocked`; no alias such as
`result_review_approved` is valid. A receipt time may be stored only as separate
event metadata outside the record hash and outside packages/receipts.
The receipt-bound B1b branch explicitly extends every result-review state reader
used by preview, package construction/submit, and handoff to recognize this
closed B1b schema; the native `layer3.execution_result_review_state.v1` extractor
and all non-B1b behavior remain unchanged. An unrecognized/mixed schema fails
closed rather than being treated as approved.

The closed response for all four outcomes has exactly the common result-review
fields listed in the response table below plus the mapped decision/state,
`review_notes_present=false`, `review_notes_sha256=null`, and
`package_review_preview_enabled=true` for `approved`; each nonapproved outcome
has `review_notes_present=true`, `review_notes_sha256=SHA256(UTF-8 exact normalized
note bytes)`, and `package_review_preview_enabled=false`. Only `approved` may
create the package-review preview or enter package construction. An exact
request-basis replay returns the same canonical B1b response bytes with zero
updates. Reuse of the request identity with an unequal basis, or any later
second decision for the same locked review subject, is
`409 connector_result_review_decision_conflict` with zero mutation. Promotion-
basis conflicts remain a different error domain. This B1b-only mapping
intentionally replaces native `execution_result_review_already_recorded`; the
native code/status behavior remains unchanged outside the selected branch.

`result_payload_sha256` is the one field name used in the persisted review,
result member, trace map, package projection, and all cross-member assertions.
It is exactly the SHA-256 of the closed descriptive result payload; the alias
`result_payload_hash` is forbidden rather than silently translated.

### B1b-05: proof packages

- Reuse exactly the three existing package kinds: `canonical_internal`, `review_facing`, and `user_facing`.
- Do not add a fourth package kind and do not fabricate an APS package.
- Put the self-contained `b1_evidence_bundle` in `canonical_internal`.
- Give `review_facing` the complete bounded reviewer projection.
- Give `user_facing` only approved bounded disclosures and hashes.
- Embed exactly the nine logical evidence members listed in Section 9.
- In `result-review.json`, `package_review` is the exact server-derived
  package-review preview/expected-input projection with
  `review_state=package_review_preview_ready`; it is never an approved outcome,
  submit record, or final package-review hash.
- Build every member in memory, canonicalize it, hash it, and then embed it under
  the acyclic Section 9 contract. Never recursively include an outer-package hash
  or a member's own hash inside that member.
- Treat the embedded handoff, replay, rehash, and verdict members as pre-operation
  contract/basis/eligibility receipts only. Actual post-package rehash, handoff,
  replay, census, and final-verdict outcomes are external closeout receipts in the
  lane-unique isolated evidence root; immutable package bytes are never rewritten.
- Construct and no-leak-check all three canonical payloads before writing any
  final path. Stage, close, and hash all three under absent lane-owned staging
  paths; publish all three with no-clobber semantics; reopen and verify each;
  only then flush and commit the one reconciliation plus three package rows in
  one database transaction. A partial publish or database failure rolls back
  the rows and moves/re-hashes every owned orphan into containment as
  non-authoritative. A pre-existing exact final file is reusable only through
  the explicit exact-basis replay branch; an unequal existing file is a hard
  conflict. No implicit `Path.exists()` reuse is permitted.
- Before every construction/retry, a fresh-session census scans the isolated
  lane's package staging/final namespace and cross-checks every file against a
  committed `L3OutputPackage` row and reconstruction of its exact basis. Any
  unreferenced final or staged file is rehashed and moved to containment; it is
  never adopted. Tests kill the process after publishing file 1 and file 2 and
  after all renames but before DB commit, then restart in a fresh process and
  prove orphan discovery/containment plus one clean three-file/three-row retry.
- Reopen/hash each package once before package-review submit and independently
  once after it; both reads must equal each other and the persisted
  `payload_hash`. Package-review submit cannot mutate a package row or file.

After all three in-memory outer bytes exist and before any file publication,
compute `construction_basis_hash` as the D33-canonical SHA-256 of exactly:

```text
schema_id = layer3.b1b_package_construction_basis.v1
authority = {correction_full_sha256,owner_bound_main_sha,promotion_receipt_id,promoted_session_id,result_review_hash,package_review_preview_hash}
bundle = {member_count=9,bundle_index_order_hash,package_manifest_sha256,package_rehash_sha256}
packages = [{package_kind,output_package_id,payload_bytes,payload_sha256}, ...]
```

The package array order is exactly canonical, user, review. Each authority and
bundle object is closed, all six authority values and all three bundle hashes
are nonempty, and there is no path/ref, request ID, timestamp, approved package-
review outcome, handoff hash, or arbitrary extra. Replay recomputes the complete
basis from locked rows and reopened package bytes. The generic workbench
construction basis is not B1b authority.

The normative construction-basis golden vector is 1,447 bytes with SHA-256
`2c3bca8c8b3e40b625c8a70878e57a37e4e97a5d3a7c6ab28f07c921bfbf7aa9`:

```json
{"authority":{"correction_full_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","owner_bound_main_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","package_review_preview_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","promoted_session_id":"22222222-2222-2222-2222-222222222222","promotion_receipt_id":"11111111-1111-1111-1111-111111111111","result_review_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"bundle":{"bundle_index_order_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","member_count":9,"package_manifest_sha256":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","package_rehash_sha256":"0000000000000000000000000000000000000000000000000000000000000000"},"packages":[{"output_package_id":"33333333-3333-3333-3333-333333333333","package_kind":"canonical_internal","payload_bytes":1000,"payload_sha256":"1111111111111111111111111111111111111111111111111111111111111111"},{"output_package_id":"44444444-4444-4444-4444-444444444444","package_kind":"user_facing","payload_bytes":900,"payload_sha256":"2222222222222222222222222222222222222222222222222222222222222222"},{"output_package_id":"55555555-5555-5555-5555-555555555555","package_kind":"review_facing","payload_bytes":1100,"payload_sha256":"3333333333333333333333333333333333333333333333333333333333333333"}],"schema_id":"layer3.b1b_package_construction_basis.v1"}
```

### B1b-06: connector-dataset handoff

- Add separate default-off connector-dataset prepare and deliver operations in `backend/app/api/layer3/handoff.py`.
- Package construction writes only the ID/hash/byte-length package-set basis,
  exact approved result-review hash, and server-derived package-review preview
  hash. It never embeds canonical package bytes, a payload/path reference, a
  predicted approved package-review hash, or a final handoff-basis hash.
- The existing package-review submit route gains a receipt-bound B1b-only
  branch. It re-derives every authority field and the complete three-package set
  from locked rows/files, accepts no `payload_refs`, and rejects every supplied
  value that differs from the server projection. Only its successful
  `operator_decision=approved` transaction may add the exact approved review
  record and Section 4.3 handoff basis/hash to the existing reconciliation
  summary and the bounded review state to the existing session summary. This is
  the only allowed post-package in-place database update before C2; it creates
  no row or application file and changes no package row/file.
- Prepare requires and revalidates that final basis but is pure validation/read;
  it does not update reconciliation JSON, create a file, or create/mutate a row.
- Deliver revalidates linkage, path, byte length, and hash under the existing
  rollback/read-lock posture, performs the Section 8.2 bounded reopen/read/hash,
  and returns the exact full `canonical_internal` bytes through an in-memory
  `Response` with zero database or file mutation; range/conditional delivery and
  `FileResponse` are forbidden.
- APS or mixed-session substitution fails closed.
- This tranche adds no handoff schema and no handoff user interface.

The B1b package-review sequence and input surface are closed as follows; the
generic route's broader optional request model is not B1b authority:

1. Persist an approved result review and its exact hash.
2. Compute `layer3.b1b_package_review_preview_basis.v1` from exactly
   `promotion_receipt_id`, `promoted_session_id`, `analysis_plan_id`,
   `pass_run_id`, `preview_id`, `preview_hash`, `analysis_run_id`,
   `result_review_hash`, the ordered candidate kinds
   `[canonical_internal,user_facing,review_facing]`,
   `package_contract_schema_id=layer3.b1b_package_contract.v1`, and the bound
   correction full SHA-256. It contains no member, index, package ID, or package
   payload hash. Its D33-canonical SHA-256 is
   `package_review_preview_hash`.
3. Construct and commit the immutable package set against that preview.
4. Submit one exact B1b request with the following keys and no others:
   `client_request_id`, `session_id`, `analysis_plan_id`, `pass_run_id`,
   `preview_id`, `preview_hash`, `analysis_run_id`,
   `result_review_record_ref`, `package_review_preview_hash`,
    `construction_basis_hash`, `reconciliation_record_id`,
    `output_package_ids`, `payload_hashes`, `operator_decision`,
    `decision_notes`, and `expected_package_kinds`. Each of
    `output_package_ids`, `payload_hashes`, and `expected_package_kinds` has
    cardinality exactly three in canonical/user/review order. The service derives
    one and only one ordered three-object review projection from the locked
    construction basis, each object exactly
    `{package_kind,output_package_id,payload_sha256}`; those three request arrays
    are its respective field projections. `payload_refs` and all material-authority or
    generic optional fields are absent. The service derives every value except
    the operator's decision/notes, then requires exact equality.
5. `operator_decision` is exactly one of `approved`, `changes_requested`,
   `rejected`, or `blocked`. Approved requires `decision_notes=""` and persists
   null; each other decision requires
   `normalized_decision_notes=decision_notes.strip()` nonempty and persists that
   stripped string exactly as JSON. The request basis is the
   exact request above without `client_request_id`; its D33-canonical SHA-256 is
   `review_request_basis_hash`, and `client_request_id` is exactly
   `b1b-package-review-<review_request_basis_hash>`.
6. The package-review record for every decision is exactly
    `schema_id=layer3.b1b_package_review_record.v1`,
    `review_request_basis_hash`, `package_review_preview_hash`,
    `construction_basis_hash`, `reconciliation_record_id`,
    `output_package_ids`, `package_kinds`, `payload_hashes`, the exact
    `operator_decision`, and `decision_notes` (null only for approved; otherwise
    `normalized_decision_notes`). The three named arrays each have cardinality
    three and are the corresponding canonical/user/review field projections of
    the same one review projection above; no second ordering or package view is
    permitted. Its
   D33-canonical SHA-256 is
   `package_review_hash`; receipt time and request identity are event metadata
   outside that hash.
   The receipt-bound submit/handoff readers explicitly recognize this closed
   B1b record; the native `layer3.package_review_submit_state.v1` extractor and
   non-B1b behavior remain unchanged. Mixed or unrecognized state fails closed.
7. In the same database transaction, the reconciliation summary gains the
    closed `package_review_submit` record and `package_review_hash`; the session
    summary retains `schema_id=layer3.b1b_session_state.v1` and all twelve keys.
    Approved changes exactly its five initially null keys:
    `package_review_state`, `package_review_hash`, `reconciliation_record_id`,
    `packages`, and `connector_dataset_handoff_basis_hash`. Each nonapproved
    decision changes exactly the first four and leaves
    `connector_dataset_handoff_basis_hash=null`. `packages` is the same ordered
    three-object review projection above; no schema swap, key removal, full basis,
    or alternate package projection is allowed. The exhaustive
    map is `approved -> package_review_approved`,
   `changes_requested -> package_review_changes_requested`,
   `rejected -> package_review_rejected`, and
    `blocked -> package_review_blocked`. Only approved also adds the exact
    Section 4.3 handoff basis/hash to reconciliation and the hash alone to the
    session. Every nonapproved
   decision leaves the immutable three-package set byte- and row-equivalent,
   creates no handoff basis or basis hash, leaves handoff unavailable, and
   cannot satisfy C2.
8. The closed submit response exposes the decision/state and
   `decision_notes_present` plus `decision_notes_sha256`, never raw notes.
   Approved uses `false`/null and `handoff_eligibility_status=eligible`; every
   nonapproved decision uses `true`/the SHA-256 of exact UTF-8 normalized-note bytes,
   omits `connector_dataset_handoff_basis_hash`, and uses
   `handoff_eligibility_status=ineligible`. Exact request-basis replay returns
   the same canonical B1b response bytes with zero updates. Reuse of the request
   identity with an unequal basis, or any second decision for the same locked
   package set, is `409 connector_package_review_decision_conflict` with zero
   mutation. Package-construction and materialization basis conflicts remain
   separate domains. This B1b-only mapping intentionally replaces native
   `package_review_submit_already_recorded`; generic behavior is unchanged.

This order is normative: result review -> package-review preview -> immutable
package construction/persistence -> package rehash read 1 -> approved package
review plus bounded summary/handoff-basis update -> package rehash read 2 ->
read-only handoff prepare/deliver. No package may contain or predict a later
approved-review or handoff outcome.

The four existing review/package routes also require a dedicated response
branch. The current generic response models are not B1b-safe: they declare
open-ended result/trace bodies and expose sensitive reference fields. In the
live models, `review_record_ref`, `result_review_record_ref`, `payload_refs`, and
`output_packages` are required on particular commit/submit surfaces, while
`output_payload_ref` is optional; none is valid in a closed B1b body. The B1b
service branch therefore returns a distinct immutable
`B1BClosedApiResponse` wrapper, never a magic discriminator dictionary. Its
sole constructor validates an `extra="forbid"` closed body, runs the Section 9
recursive assertion, D33-canonicalizes it to UTF-8/no-BOM/no-newline bytes, and
stores only those bytes and the enumerated HTTP status.

The four B1b route-body schemas have no request/server timestamp, `*_ref`,
arbitrary metadata, or extra field. This is deliberate B1b behavior: unlike the
native generic replay bodies, it does not add `server_time` or change a status
literal on replay, so an exact replay is byte-identical:

| Route | Exact closed body |
|---|---|
| `POST /execution/result/review` | `schema_id=layer3.b1b_result_review_response.v1`, `promotion_receipt_id`, `promoted_session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `operator_decision=<one of four>`, `review_state=<exact mapped execution_result_review_* state>`, `result_review_hash`, `review_notes_present`, `review_notes_sha256`, `package_review_preview_enabled` |
| `POST /package/review/preview` | `schema_id=layer3.b1b_package_review_preview_response.v1`, `promotion_receipt_id`, `promoted_session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `result_review_hash`, `package_review_preview_hash`, `candidate_package_kinds`, `member_count=9`, `package_contract_schema_id=layer3.b1b_package_contract.v1`, `correction_full_sha256` |
| `POST /package/review/commit` | `schema_id=layer3.b1b_package_construction_commit_response.v1`, `promotion_receipt_id`, `promoted_session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `result_review_hash`, `package_review_preview_hash`, `construction_basis_hash`, `reconciliation_record_id`, `packages`, `package_count=3`, `member_count=9`, `persistence_status=committed` |
| `POST /package/review/submit` | `schema_id=layer3.b1b_package_review_submit_response.v1`, `promotion_receipt_id`, `promoted_session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `result_review_hash`, `package_review_preview_hash`, `construction_basis_hash`, `package_review_hash`, `reconciliation_record_id`, `packages`, `operator_decision=<one of four>`, `package_review_state=<exact mapped package_review_* state>`, `decision_notes_present`, `decision_notes_sha256`, `handoff_eligibility_status`; only approved also has `connector_dataset_handoff_basis_hash` |

`candidate_package_kinds` is exactly the canonical/user/review array. Each
`packages` array has exactly three objects in that order and each object has
exactly `package_kind`, `output_package_id`, `byte_length`, and
`payload_sha256`. No B1b success body has `reviewed_output_items`,
`trace_summary`, `output_metadata_summary`, generic `output_packages`, any
payload/storage/path reference, `authority_rail`, or an extra key. A resolved
B1b typed error is another closed wrapper with exactly
`schema_id=layer3.b1b_error.v1`, `status=error`, `error_code`, `message`, and
`retryable`; its message is fixed per enumerated code and never echoes a request
value, exception, database value, or path. Pre-body identity/role failures keep
the existing common auth envelope because the body/session has not been read;
tests separately prove that envelope has no registered sensitive value.

The exhaustive B1b v1 valid-code array, in exact order, is:

```json
["promotion_identity_decision_conflict","connector_promotion_bridge_unavailable","b1b_handoff_full_body_required","connector_promotion_session_not_found","connector_promotion_not_eligible","b1b_request_validation_failed","promotion_identity_lock_unavailable","connector_promotion_basis_conflict","connector_result_review_decision_conflict","connector_package_basis_conflict","connector_package_review_decision_conflict","connector_materialization_basis_conflict"]
```

No other code is valid in the selected B1b typed envelope. Its closed mapping is:

| `error_code` | HTTP | Exact `message` | `retryable` |
|---|---:|---|---|
| `promotion_identity_decision_conflict` | 409 | `Promotion identity decision conflicts with the committed receipt.` | `false` |
| `connector_promotion_bridge_unavailable` | 503 | `Connector promotion bridge is unavailable.` | `true` |
| `b1b_handoff_full_body_required` | 400 | `Handoff requires a full-body request.` | `false` |
| `connector_promotion_session_not_found` | 404 | `Connector promotion session was not found.` | `false` |
| `connector_promotion_not_eligible` | 409 | `Connector promotion is not eligible.` | `false` |
| `b1b_request_validation_failed` | 422 | `Request body failed validation.` | `false` |
| `promotion_identity_lock_unavailable` | 503 | `Promotion identity lock is unavailable.` | `true` |
| `connector_promotion_basis_conflict` | 409 | `Promotion basis conflicts with the committed receipt.` | `false` |
| `connector_result_review_decision_conflict` | 409 | `Result review decision conflicts with the recorded review.` | `false` |
| `connector_package_basis_conflict` | 409 | `Package basis conflicts with the committed package set.` | `false` |
| `connector_package_review_decision_conflict` | 409 | `Package review decision conflicts with the recorded review.` | `false` |
| `connector_materialization_basis_conflict` | 409 | `Materialization basis conflicts with the committed output.` | `false` |

The closed-wrapper constructor owns this array and mapping; the route helper
uses them without caller text or per-route overrides. An unknown code, unequal
status/message/retryable tuple, changed order, or extra mapping entry fails
closed and fails proof. The common pre-body auth envelope remains outside this
array and is not translated into a B1b typed code.
The route tests parameterize all twelve entries in this exact order, assert the
fixed tuple at every selected route, and separately prove that the two review-
decision conflicts cannot be emitted as promotion/package/materialization basis
conflicts or native generic replay codes.

Scope selection is server-only: the production attestation verifies, the
supplied session resolves to exactly one matching promotion receipt, and the
request keys equal the exact B1b surface before the service enters this branch.
No request flag or caller-supplied schema marker selects it. In particular, the
package service branches occur before generic source-intake validation reads or
requires `payload_refs`.

The route implementation must not depend on ambiguous union-model selection or
an untyped result dictionary. It leaves the four existing decorators and
`response_model=` classes unchanged. After server-only scope resolution, the
service returns `B1BClosedApiResponse` for success and raises the distinct
`B1BClosedApiError` for a typed B1b failure. A shared route helper used by the
execution-result route in `__init__.py` and the three routes in `package.py`
catches that type before the existing generic `Layer3WorkbenchError` conversion,
constructs the closed error wrapper, and converts either wrapper directly to
`Response(content=canonical_bytes, media_type="application/json",
status_code=...)`. FastAPI bypasses generic response-model serialization for a
`Response`. Only ordinary/flag-off results and generic errors continue through
the existing `_json_or_error` conversion and response models, byte-for-byte.
The B1b branch may not raise a generic workbench error after it is selected; an
unmapped exception is a fail-closed server error with no exception text in the
body and makes the proof fail.

The ordinary OpenAPI schema is unchanged; the B1b body is an explicitly
documented runtime variant selected by server authority, not a falsely generic
OpenAPI union. Tests hit all four routes and prove exact/canonical replay bytes,
exact key equality, recursive no-leak success/error behavior, absence of
model-added nulls, server-only branch selection, typed-error interception before
the generic helper, unmapped-exception containment, and ordinary flag-off
response-byte and OpenAPI-schema parity. This requirement is why
`backend/app/api/layer3/package.py` is inside the exhaustive file fence.

## 6. Exact first-path and replay row contract

Use four named checkpoints; no report may collapse them into one baseline.

- **C0 — capture committed / pre-Gate-B.** Take the census after exactly one
  `ConnectorRun`, one `ConnectorRunTarget`, one
  `L3ConnectorSourceIntakeRecord`, the material preview, and the single 34-byte
  connector raw object have committed, after expiring ORM state, and immediately
  before Gate-B. The six current Gate-B tables and
  `L3ConnectorPromotionReceipt` are all zero.

  C0's exact expected count projection is the concatenation of these two arrays,
  in displayed order, yielding exactly the declared 28 surfaces:

  ```json
  [{"surface":"ConnectorRun","row_count":1},{"surface":"ConnectorRunTarget","row_count":1},{"surface":"L3ConnectorSourceIntakeRecord","row_count":1}]
  ```

  ```json
  [{"surface":"L3GateBIdempotencyKey","row_count":0},{"surface":"L3Session","row_count":0},{"surface":"L3SelectionManifest","row_count":0},{"surface":"L3Descriptor","row_count":0},{"surface":"L3RetrievalEvent","row_count":0},{"surface":"L3MaterialSnapshot","row_count":0},{"surface":"L3ConnectorPromotionReceipt","row_count":0},{"surface":"SourceConnector","row_count":0},{"surface":"Dataset","row_count":0},{"surface":"DatasetVersion","row_count":0},{"surface":"VariableDefinition","row_count":0},{"surface":"DatasetSourceProvenance","row_count":0},{"surface":"DatasetRow","row_count":0},{"surface":"L3TypingRecord","row_count":0},{"surface":"L3AnalysisUnit","row_count":0},{"surface":"L3AnalysisGroup","row_count":0},{"surface":"L3AnalysisSet","row_count":0},{"surface":"L3AnalysisPlan","row_count":0},{"surface":"L3PassRun","row_count":0},{"surface":"AnalysisRun","row_count":0},{"surface":"AssumptionCheck","row_count":0},{"surface":"AnalysisArtifact","row_count":0},{"surface":"CaveatNote","row_count":0},{"surface":"L3ReconciliationRecord","row_count":0},{"surface":"L3OutputPackage","row_count":0}]
  ```

- **C1 — first Gate-B committed.** For a fresh eligible I1, `C1-C0` is exactly
  `+1` for `L3GateBIdempotencyKey`, the original connector `L3Session`,
  `L3SelectionManifest`, `L3Descriptor`, `L3RetrievalEvent`,
  `L3MaterialSnapshot`, and `L3ConnectorPromotionReceipt`. Those seven rows and
  no others commit or roll back together. The original Gate-B snapshot payload
  JSON is the only successful application-file delta.
- **C2 — first B1b final / pre-handoff.** Take this after materialization,
  promoted-session/3C/analysis, approved result review, package-review preview,
  immutable package completion, the first package reopen/hash, approved package
  review plus its bounded reconciliation/session summary update, and the second
  package reopen/hash, but before prepare/deliver. The table below is exactly
  `C2-C1`; its session-spine rows are the promoted dataset session, never the
  original Gate-B spine.
- **C3 — post-handoff/same-request-replay/final census.** The authoritative
  database executes only prepare/deliver and same-request replays after C2.
  Every application DB row and application-storage file count/hash equals C2.
  The separately defined post-package outcome receipts exist only in the
  isolated evidence root. Cross-run and divergent new-request seams are not
  executed in this database.

The only allowed `C2-C1` durable row changes are:

| Surface | Exact delta |
|---|---:|
| `L3ConnectorPromotionReceipt` | +0 rows; the C1 row atomically changes `dataset_id`, `dataset_version_id`, `promoted_session_id`, `materialization_basis_hash`, and `materialized_at` from null to final, and `materialization_status` from null through the uncommitted `materializing` claim to committed `materialized`; every origin field remains byte-equivalent |
| `SourceConnector` | +1 |
| `Dataset` | +1 |
| `DatasetVersion` | +1 |
| `VariableDefinition` | +2 |
| `DatasetSourceProvenance` | +1 |
| `DatasetRow` | +0 |
| `ConnectorRunTarget` | null-to-final `dataset_id`/`dataset_version_id` plus standard `updated_at` only |
| promoted `L3Session` | +1; its `summary_json` retains the stable exact twelve-key `layer3.b1b_session_state.v1` schema in [B1b-06 item 7](#b1b-06-connector-dataset-handoff); result review writes the first seven keys, every package-review decision writes the first four initially null review/package keys, and approved alone also writes the final handoff-basis hash; the full handoff basis exists only in the reconciliation summary |
| `L3SelectionManifest` | +1 |
| `L3Descriptor` | +1 |
| `L3RetrievalEvent` | +1 |
| `L3MaterialSnapshot` | +1 |
| `L3GateBIdempotencyKey` | +0 for the derived session |
| `L3TypingRecord` | +1 |
| `L3AnalysisUnit` | +1 |
| `L3AnalysisGroup` | +1 |
| `L3AnalysisSet` | +1 |
| `L3AnalysisPlan` | +1 |
| `L3PassRun` | +1 |
| `AnalysisRun` | +1 |
| `AssumptionCheck` | +4 |
| `AnalysisArtifact` | +1 |
| `CaveatNote` | +1, exactly `non_time_series_interpretation` |
| `L3ReconciliationRecord` | +1; after package persistence its `summary_json` receives only the closed approved package-review record/hash and final Section 4.3 handoff basis/hash in the same review transaction |
| `L3OutputPackage` | +3 |
| handoff product/DB rows and files | +0 |

The two summary updates named in this table are the complete allowed
post-package in-place mutation set. Their before/after canonical JSON hashes and
exact changed-key sets are recorded in `row-file-census.json`; no other session,
reconciliation, package, review, or analysis column changes between package
commit and C2.

Combined `C0-C2`, a fresh I1 therefore has `L3ConnectorPromotionReceipt +1`,
`L3GateBIdempotencyKey +1`, and `L3Session`, `L3SelectionManifest`,
`L3Descriptor`, `L3RetrievalEvent`, and `L3MaterialSnapshot +2` each: one
original Gate-B spine and one promoted-session spine. Every other combined delta
is the C2 table above.

Same-request replay in the authoritative database has zero rows, files, and
in-place updates. The cross-run and divergent new-request seams run serially in
the exact `replay_cross_run` and `replay_divergent` namespaces defined below
under the existing database, storage, and evidence children. Each namespace set
is absent before create. Neither sandbox is seeded, cloned from the
authoritative database, or counted in authoritative C0-C3. Each first builds and
independently verifies its own ordinary original approval/receipt baseline
through the public service boundary.

In the exact-reuse sandbox, a second run then completes its ordinary capture
boundary: its new `ConnectorRun`, `ConnectorRunTarget`, intake row, material
preview, and one capture raw object are committed at that request's local C0.
After local C0 it reconstructs and compares the full I1/approval/basis, then
reuses the sandbox's original receipt **before** `claim_gate_b_idempotency`; it
is a validated reuse of the original committed approval, not a second committed
Gate-B audit session. The new target is linked in place to the original
receipt's exact `dataset_id` and `dataset_version_id`; those two null-to-final
links plus its standard `updated_at` are the only allowed target changes. Every
other target column remains byte-equivalent. This creates no second six-row
Gate-B spine, snapshot file, receipt, Dataset, DatasetVersion, promoted session,
typing/analysis chain, reconciliation row, or package set. Relative to its
local C0, reuse has zero new rows/files and exactly that bounded target update.

In the divergent sandbox, the new divergent request likewise commits its own
ordinary local-C0 capture rows and raw object before Gate-B. Its D34 submission
returns `409 promotion_identity_decision_conflict` with zero delta from that
local-C0 entry to the decision return: no new six-row spine, receipt, file, or
update. The committed capture rows/raw object remain preserved, are never rolled
back or deleted, and its target links remain null. Each replay sandbox records
baseline, local-C0, and post-decision row/file hashes plus an explicit
`excluded_from_authoritative_c0_c3=true`.
Authoritative C2-C3 equality is therefore not weakened by evidence that
necessarily creates new-request capture state.

Application files are censused separately from database-engine files and the
isolated evidence root:

| Interval | Exact successful application-file delta |
|---|---:|
| pre-capture to C0 | one connector raw object, exactly 34 bytes with the F07 hash |
| C0 to C1 | one original Gate-B snapshot payload JSON |
| C1 to C2 | one DatasetVersion Parquet; one promoted-session snapshot JSON; one descriptive-result artifact JSON; one pass output-manifest JSON; three outer package JSON files |
| C2 to C3 | +0 |

Thus C1-C2 is exactly seven application files, C0-C2 is eight, and
pre-capture-to-C2 is nine. Logical evidence members are embedded values and
create zero sidecar files; raw copies after C0 are zero. Every successful file is
listed by lane-relative logical class, byte length, and SHA-256 in the final
file ledger. Database/WAL files are excluded from this application ledger and
are monitored only through the isolated database-volume census.

The pre-operation first-path contract is one exact closed object. It has only
`schema_id`, `checkpoint_order`, `c0`, `deltas`, and `c2_to_c3`.
`schema_id` is `layer3.b1b_expected_first_path_contract.v1` and
`checkpoint_order` is exactly `["C0","C1","C2","C3"]`. `c0` has only
`capture_rows`, `gate_b_rows`, `other_tranche_rows`, and `application_files`.
Each row-count entry is exactly `{surface:<literal>,row_count:<nonnegative
integer>}`; each application-file entry is exactly `{logical_class:<literal>,
byte_length:<positive integer>,sha256:<H>}`. The arrays are exhaustive and in
the following order:

```json
{"capture_rows":[{"surface":"ConnectorRun","row_count":1},{"surface":"ConnectorRunTarget","row_count":1},{"surface":"L3ConnectorSourceIntakeRecord","row_count":1}],"gate_b_rows":[{"surface":"L3GateBIdempotencyKey","row_count":0},{"surface":"L3Session","row_count":0},{"surface":"L3SelectionManifest","row_count":0},{"surface":"L3Descriptor","row_count":0},{"surface":"L3RetrievalEvent","row_count":0},{"surface":"L3MaterialSnapshot","row_count":0},{"surface":"L3ConnectorPromotionReceipt","row_count":0}],"other_tranche_rows":[{"surface":"SourceConnector","row_count":0},{"surface":"Dataset","row_count":0},{"surface":"DatasetVersion","row_count":0},{"surface":"VariableDefinition","row_count":0},{"surface":"DatasetSourceProvenance","row_count":0},{"surface":"DatasetRow","row_count":0},{"surface":"L3TypingRecord","row_count":0},{"surface":"L3AnalysisUnit","row_count":0},{"surface":"L3AnalysisGroup","row_count":0},{"surface":"L3AnalysisSet","row_count":0},{"surface":"L3AnalysisPlan","row_count":0},{"surface":"L3PassRun","row_count":0},{"surface":"AnalysisRun","row_count":0},{"surface":"AssumptionCheck","row_count":0},{"surface":"AnalysisArtifact","row_count":0},{"surface":"CaveatNote","row_count":0},{"surface":"L3ReconciliationRecord","row_count":0},{"surface":"L3OutputPackage","row_count":0}],"application_files":[{"logical_class":"connector_raw","byte_length":34,"sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad"}]}
```

`deltas` contains exactly four objects in order: `pre-capture` to `C0`, `C0`
to `C1`, `C1` to `C2`, and `C2` to `C3`. Each has only `from`, `to`,
`row_deltas`, and `file_deltas`. A row delta has exactly `surface`, `inserted`,
`updated`, `deleted=0`, and ordered `changed_columns`; a file delta has exactly
`logical_class`, `created`, `changed=0`, and `removed=0`. Their complete arrays
are:

```json
[
  {"from":"pre-capture","to":"C0","row_deltas":[{"surface":"ConnectorRun","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"ConnectorRunTarget","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3ConnectorSourceIntakeRecord","inserted":1,"updated":0,"deleted":0,"changed_columns":[]}],"file_deltas":[{"logical_class":"connector_raw","created":1,"changed":0,"removed":0}]},
  {"from":"C0","to":"C1","row_deltas":[{"surface":"L3GateBIdempotencyKey","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3Session","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3SelectionManifest","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3Descriptor","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3RetrievalEvent","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3MaterialSnapshot","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3ConnectorPromotionReceipt","inserted":1,"updated":0,"deleted":0,"changed_columns":[]}],"file_deltas":[{"logical_class":"gate_b_snapshot","created":1,"changed":0,"removed":0}]},
  {"from":"C1","to":"C2","row_deltas":[{"surface":"L3ConnectorPromotionReceipt","inserted":0,"updated":1,"deleted":0,"changed_columns":["dataset_id","dataset_version_id","promoted_session_id","materialization_basis_hash","materialized_at","materialization_status"]},{"surface":"SourceConnector","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"Dataset","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"DatasetVersion","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"VariableDefinition","inserted":2,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"DatasetSourceProvenance","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"DatasetRow","inserted":0,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"ConnectorRunTarget","inserted":0,"updated":1,"deleted":0,"changed_columns":["dataset_id","dataset_version_id","updated_at"]},{"surface":"L3Session","inserted":1,"updated":1,"deleted":0,"changed_columns":["summary_json"]},{"surface":"L3SelectionManifest","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3Descriptor","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3RetrievalEvent","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3MaterialSnapshot","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3GateBIdempotencyKey","inserted":0,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3TypingRecord","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3AnalysisUnit","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3AnalysisGroup","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3AnalysisSet","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3AnalysisPlan","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3PassRun","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"AnalysisRun","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"AssumptionCheck","inserted":4,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"AnalysisArtifact","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"CaveatNote","inserted":1,"updated":0,"deleted":0,"changed_columns":[]},{"surface":"L3ReconciliationRecord","inserted":1,"updated":1,"deleted":0,"changed_columns":["summary_json"]},{"surface":"L3OutputPackage","inserted":3,"updated":0,"deleted":0,"changed_columns":[]}],"file_deltas":[{"logical_class":"dataset_version_parquet","created":1,"changed":0,"removed":0},{"logical_class":"promoted_session_snapshot","created":1,"changed":0,"removed":0},{"logical_class":"descriptive_result_artifact","created":1,"changed":0,"removed":0},{"logical_class":"pass_output_manifest","created":1,"changed":0,"removed":0},{"logical_class":"canonical_internal_package","created":1,"changed":0,"removed":0},{"logical_class":"user_facing_package","created":1,"changed":0,"removed":0},{"logical_class":"review_facing_package","created":1,"changed":0,"removed":0}]},
  {"from":"C2","to":"C3","row_deltas":[],"file_deltas":[]}
]
```

`c2_to_c3` is exactly
`{"application_database_rows_equal":true,"application_storage_files_equal":true,"allowed_authoritative_mutations":[]}`.
The service is the sole producer of this prospective object before result
review. `expected_first_path_contract_sha256` is its D33-canonical digest and is
identical in `connector_b1_evidence`, the package cross-member checks, and the
external census comparison. Any missing/extra/reordered entry, unequal digest,
or actual-census deviation fails closed; the object predicts no actual outcome
and does not replace the external C0-C3 evidence.

Gate-B writes its snapshot payload before the DB commit. If that transaction
fails, all seven C1 rows roll back, but any staged/orphan snapshot is rehashed,
censused, moved only into the lane's containment area under the no-delete rule,
and marked non-authoritative/non-reusable. It is never omitted from the failure
ledger or counted as successful state.

Before each first Gate-B attempt/retry, scan the exclusive isolated lane's
snapshot namespace and cross-check every file against committed material-
snapshot payload references. Any unreferenced file is rehashed and moved to
containment before a new write; no orphan is adopted as a successful snapshot.
A kill-after-snapshot-write/before-commit test restarts in a fresh process and
proves discovery, containment, zero surviving C1 rows from the killed attempt,
and one clean retry. Exception-handler cleanup alone does not satisfy this gate.

SQLite-authorized replay and comparison sandboxes use namespaces, never extra
roots. Each `sandbox_namespaces_sha256` hashes exactly the D33-canonical object
`{"database":{"child_canonical_sha256":H,"child_root_id":T,"relative_namespace":T},"evidence":{"child_canonical_sha256":H,"child_root_id":T,"relative_namespace":T},"lane_parent_id":T,"role":<replay_cross_run|replay_divergent|sandbox_a|sandbox_b>,"sandbox_id":<P|null>,"schema_id":"layer3.b1b.sandbox_namespaces.v1","storage":{"child_canonical_sha256":H,"child_root_id":T,"relative_namespace":T}}`.
The nested `database`, `storage`, and `evidence` child IDs/hashes exactly alias
their correspondingly named invocation `root_bindings` children, and
`lane_parent_id` aliases that binding's parent. Role-to-slug mapping is exact:
`replay_cross_run -> replay-cross-run`, `replay_divergent -> replay-divergent`,
`sandbox_a -> sandbox-a`, and `sandbox_b -> sandbox-b`. Each of the three
`relative_namespace` values equals that role slug beneath its existing child.

Each namespace is absent before create and final-handle-derived after create. It
is `/`-separated and child-relative with no empty, dot, dot-dot, drive, UNC, or
reparse segment. All four role namespaces are pairwise distinct and
nonancestor. Replay roles require their enclosing positive `sandbox_id`;
comparison roles require null. No namespace becomes a new root identity.

Each sandbox SQLite `database_identity_sha256` hashes exactly
`{"database_child_canonical_sha256":H,"profile":"sqlite","relative_database_path":"<role-slug>/b1b.sqlite3","sandbox_namespaces_sha256":H,"schema_id":"layer3.b1b.sandbox_database_identity.v1"}`.
The database-child hash and role slug come from the same namespace object. A
sandbox DB identity cannot alias the authoritative SQLite DB identity.
Successful sandbox evidence namespaces contain no files: replay/comparison
evidence remains inline in the enclosing receipt/census under the invocation's
evidence child. Empty directories are the only allowed successful evidence-
namespace membership. Any file or partial output in a sandbox evidence
namespace makes the sandbox execution unaccepted and leaves it in external
containment.

The required SQLite-authorized comparison battery has exactly two serial,
isolated, non-authoritative sandbox lifecycles, in `sandbox_a`, then `sandbox_b`,
order. The runner creates each role's database, storage, and evidence namespaces
exactly once. In each role it materializes exactly one immutable DatasetVersion
counterpart with the frozen materialization semantics, captures that role's
materializer checkpoint, continues in the same database and namespaces without
deletion or recreation, executes exactly one direct persisted
`descriptive_summary` run against that role-local DatasetVersion, and captures
that role's method checkpoint. The two DatasetVersion rows and their physical
databases are distinct; only their frozen semantics are equal. Within each role,
the method stage reuses its materializer-created row and may not create a second
DatasetVersion. Across both method checkpoints the method-stage additions are
exactly two AnalysisRuns, eight AssumptionChecks, two
`descriptive_summary_result` rows and artifact JSON files, and two
`non_time_series_interpretation` caveats; the battery creates no pass-output
manifest, package, reconciliation, handoff, or authoritative B1b output. Compare
all substantive JSON, check/caveat names and messages,
row/column data, classes, missingness, top values, and numerical summaries
under predecessor `b1-vertical-loop-packet.md` Section 3: strings, integers,
nulls, keys, and ordered arrays are exact; floats use absolute and relative
tolerance `1e-12`; normalize only IDs, timestamps, storage references, and
content-neutral UUID filename segments. The required values are summary rows 2,
columns 2, numeric 1, categorical 1, boolean/time 0, no missing cells, `site_id`
counts `SB-001:1` then `SB-002:1`, and `value` min 42.0, max 43.0,
mean/median 42.5, sample standard deviation `0.7071067811865476`, then top
values `42:1` and `43:1`, with exactly four named checks, one named caveat, and
one `descriptive_summary_result` artifact per run. Its rows/files never enter C0-C3
or a package. The authoritative first path remains the single-run table above
and is packaged only after the sandbox comparison passes. A second
DatasetVersion inside either role, an extra row/file/caveat, namespace deletion
or recreation, cross-role physical-row reuse, or packaging a sandbox output is
a hard failure. Each run's four AssumptionChecks are exactly:

| name | method | result | severity | notes |
|---|---|---|---|---|
| `data_availability` | `dataframe_shape` | `pass` | `high` | `rows=2; columns=2` |
| `column_classification` | `deterministic_dtype_scan` | `pass` | `medium` | `{"categorical": 1, "numeric": 1}` |
| `missingness_scan` | `cell_missingness` | `pass` | `medium` | `missing_cells=0; missing_fraction=0.000000` |
| `time_column_coverage` | `declared_time_column_scan` | `warn` | `medium` | `time_column=; present=False` |

The one caveat is type `non_time_series_interpretation`, severity `medium`, and
message `Dataset does not declare a usable time column; descriptive summary is
non-time-series only.` The analysis code blob is pinned; any message/field drift
requires a correction amendment, not tolerance widening.

Sandbox-to-sandbox agreement is necessary but insufficient. Before result
review or package construction, the authoritative C1-to-C2 `AnalysisRun`,
result payload/artifact, four checks, and caveat must reproduce the same exact
substantive values, ordered structures, messages, and semantic hashes as both
sandbox runs under the identical normalization and `1e-12` float rule above.
The authoritative result IDs/timestamps/storage refs may differ only in those
named normalized fields. Any authoritative-versus-sandbox difference is a hard
failure even when the two sandboxes agree with each other.

At each SQLite-authorized materializer checkpoint, before that role's method
stage starts, the role has exactly these rows: ConnectorRun +1, target +1,
intake +1, Gate-B idempotency +1, receipt +1, SourceConnector +1, Dataset +1,
DatasetVersion +1, VariableDefinition +2, DatasetSourceProvenance +1, and two
L3 session spines (each one session, selection manifest, descriptor, retrieval
event, and material snapshot). The target has only its two output links plus
`updated_at`; typing, analysis, pass, review, reconciliation, and package rows
are zero. Each run has exactly four application files: capture raw, original
Gate-B snapshot, DatasetVersion Parquet, and promoted snapshot. After this
checkpoint is serialized once, the runner continues that same role's lifecycle
to its method checkpoint; it does not stop, delete, or recreate the role.

Both runs must reproduce one exact semantic object. Its D33-canonical preimage
is the following single-line JSON, 1,295 UTF-8 bytes with no BOM or terminal
newline; its SHA-256 and the only valid
`materialization_semantic_sha256` are
`4bf4b24ded8e29087d1a8503e92d6141f59beb1356f3c9e7fadce1a250fbe2b0`:

```json
{"approval":{"approval_hash":"197ab9e9d6c753483c01d2a86787ed222c5aa22e3292c48df6d250e2e2540a65","eligibility_policy_id":"layer3.connector_promotion_eligibility.f07-c01.v1"},"identity":{"canonical_identity_key_hash":"2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0","content_sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad","identity_metadata_hash":"6139864817c74663634763dbb5fe2fa389ec4581eb158f17a4862412756907e7","identity_metadata_hash_version":"layer3.connector_source_intake.identity_metadata.v1","source_family":"connector_produced_single_source"},"metadata_contract_sha256":"86d8ab86401f1a7fa84f42e63bc288da1fe05d670cde1ec98c9387f136deb644","output":{"column_count":2,"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"dropped_row_count":0,"row_count":2,"rows":[["SB-001",42],["SB-002",43]],"source_row_count":2,"variable_count":2},"schema_id":"layer3.connector_promotion_materialization_semantic.v1","transformation":{"contract_sha256":"951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179","method_input_sha256":"907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b","parameters":{},"schema_id":"layer3.connector_promotion_transform.v1","version":"1"}}
```

The materializer is the sole producer: it builds this object from the verified
fixture, D33 identity, approved receipt, frozen transform/method-input, and
metadata contracts before any comparison. All package, review, census, and
verdict consumers use the exact digest above; no alias is permitted. A byte,
type, key, nesting, schema, array-order, or digest difference fails before
review/package authority and leaves the run nonpassing. The object intentionally
excludes promotion/materialization bases, generated IDs/timestamps, all physical
storage refs, physical byte lengths/hashes, and storage-ref hashes because those
are run-local lineage/physical facts. No other exclusion or normalization is
allowed. Reopen/hash every file twice within its own run.
Parquet bytes, byte lengths, physical hashes, storage-ref hashes, and therefore
the complete materialization-record hashes need not equal across runs; that
cross-run equality is explicitly unclaimed, while each run's own
promotion/materialization bases must independently verify against its own
lineage and its own record-to-file bytes/length/hash/ref linkage must be exact
and stable. The closed
`row-file-census.json.materializer_comparison` and `.method_comparison` objects
record both exact row/file ledgers, semantic comparison hashes, normalized-
equality booleans, exclusions/nonclaims, and artifact rehash results; their hash
is bound by the final verdict/evidence manifest. Neither sandbox enters C0-C3 or
an authoritative package.

The authoritative C1-to-C2 materialization must also match both isolated
materializer runs on the complete semantic preimage/hash, ordered
values/types/counts, transformation and method-input hashes, metadata-contract
hash, D33 identity, approval hash, and eligibility policy. Each run separately
proves its own promotion/materialization basis plus complete
materialization-record-to-file bytes/hash/ref linkage and double rehash; those
physical facts are not cross-run normalized or asserted equal. Three-way
semantic equality (sandbox A = sandbox B = authoritative) and three separate
physical-linkage booleans are recorded explicitly; sandbox-only agreement
cannot authorize the authoritative output.

`row-file-census.json.materializer_comparison` is exactly a closed
`layer3.b1b.materializer_comparison.v1` object with only `schema_id`, `runs`,
`semantic_equal`, `physical_equality_claimed`, `exclusions`, and `nonclaims`.
`runs` contains exactly `sandbox_a`, `sandbox_b`, `authoritative` in that order.
Each run has exactly `role`, `sandbox_namespaces_sha256`, `row_file_ledger_sha256`,
`materialization_semantic_sha256`, `promotion_basis_hash`,
`materialization_basis_hash`, `materialization_record_sha256`,
`dataset_file_bytes`, `dataset_file_sha256`, `dataset_storage_ref_hash`,
`reopen_1_sha256`, `reopen_2_sha256`, `physical_linkage_valid`, and
`excluded_from_authoritative_c0_c3`. The first two exclusion booleans are true;
the authoritative value is false. For `sandbox_a` and `sandbox_b`,
`sandbox_namespaces_sha256` is `H` from the exact role namespace above; for
`authoritative` it is null. Every other hash is `H`, bytes are positive, and
PASS requires the three semantic hashes equal the frozen Section 6 semantic
digest, both reopen hashes equal each run's dataset-file hash, all three physical
linkage booleans true, and `semantic_equal=true`.
For each sandbox role, `row_file_ledger_sha256` binds the ledger captured at
that role's materializer checkpoint before its method stage. The authoritative
binding covers the corresponding authoritative materializer-stage checkpoint.
No later method-stage row or file may be backfilled into a materializer ledger.

`physical_equality_claimed` is false. `exclusions` is exactly
`["generated_ids","timestamps","physical_storage_refs","dataset_file_bytes","dataset_file_sha256","dataset_storage_ref_hash","promotion_basis_hash","materialization_basis_hash","materialization_record_sha256"]`.
`nonclaims` is exactly
`["Parquet byte equality across sandbox and authoritative runs is not claimed.","Run-local bases and record-to-file linkage remain mandatory."]`.
Those exclusions apply only to cross-run semantic equality; no run-local
physical field may be omitted, normalized, or left unverified.

`row-file-census.json.method_comparison` is exactly a closed
`layer3.b1b.method_comparison.v1` object with only `schema_id`, `runs`,
`semantic_equal`, `physical_equality_claimed`, `float_tolerance`, `exclusions`,
and `nonclaims`. Its `runs` order is again `sandbox_a`, `sandbox_b`,
`authoritative`. Each run has exactly `role`, `sandbox_namespaces_sha256`,
`row_file_ledger_sha256`,
`normalized_semantic_sha256`, `result_payload_sha256`,
`analysis_artifact_sha256`, `assumption_checks_sha256`, `caveat_sha256`,
`reopen_1_sha256`, `reopen_2_sha256`, `physical_linkage_valid`, and
`excluded_from_authoritative_c0_c3`; only the first two exclusion booleans are
true. Sandbox namespace hashes are `H` for the first two roles and null for
`authoritative`. `float_tolerance` is exactly
`{absolute:1e-12,relative:1e-12}`.

For `normalized_semantic_sha256`, project exactly the Section 9 bounded result,
the four checks without their generated IDs, and the caveat without its
generated ID into
`{schema_id:"layer3.b1b.method_semantic.v1",bounded_result,
assumption_checks,caveat}`. IDs, timestamps, storage references, and content-
neutral UUID filename segments are absent. Every nonfloat value must equal the
frozen value. Each named float must first satisfy both the absolute and relative
`1e-12` comparison against its frozen Section 6 value and is then emitted as
that frozen JSON number before D33 hashing. No other replacement or tolerance
is allowed. PASS requires all three normalized digests equal, both per-run
reopen hashes equal that run's artifact hash, all physical-linkage booleans
true, and `semantic_equal=true`.
For each sandbox role, `row_file_ledger_sha256` binds the ledger captured after
that role's one method run in the same unrecreated namespaces. The authoritative
binding covers the corresponding authoritative method-stage checkpoint. No
materializer-only checkpoint may substitute for a method ledger.

Method `physical_equality_claimed` is false; `exclusions` is exactly
`["generated_ids","timestamps","storage_refs","uuid_filename_segments"]`;
`nonclaims` is exactly
`["Artifact byte equality across sandbox and authoritative runs is not claimed.","Each run's artifact linkage and double rehash remain mandatory."]`.
The census producer builds both comparison objects after all three runs. Their
exact D33 digests are the evidence hashes for the corresponding comparison
entries and are consumed by the invocation and integrated verdicts. Any key,
run, order, exclusion, nonclaim, tolerance, alias, or linkage difference fails.

Each comparison run's `row_file_ledger_sha256` has one closed preimage:
`{"application_files":[...],"comparison":<materializer|method>,"database_identity_sha256":H,"evidence_root_excluded":true,"profile":"sqlite","role":<sandbox_a|sandbox_b|authoritative>,"sandbox_namespaces_sha256":<H|null>,"schema_id":"layer3.b1b.run_row_file_ledger.v1","tables":[...]}`.
For each comparison, the
three ledgers occur in `sandbox_a`, `sandbox_b`, `authoritative` order. Every
`tables` array contains the same 28 table literals and exact
`{table,row_count,rowset_sha256}` entry shape as Section 9, in that order. The
shared contract ends at table names, order, and entry shape: every row count and
rowset hash is the actual value at that run's named materializer or method
checkpoint and may not be copied from another checkpoint, role, or authoritative
run. Every `application_files` array likewise contains all and only the files
present at that run's named checkpoint, ordered by the frozen class rank
`connector_raw`, `gate_b_snapshot`,
`dataset_version_parquet`, `promoted_session_snapshot`,
`descriptive_result_artifact`, `pass_output_manifest`,
`canonical_internal_package`, `user_facing_package`,
`review_facing_package`; each entry is exactly
`{logical_class,byte_length,sha256}`. Sandbox roles use their exact namespace
hash and sandbox DB identity; the authoritative role uses null plus the
invocation's authoritative SQLite DB identity. Neither can alias the other or
an authoritative checkpoint. Each sandbox materializer ledger has exactly the
first four listed file classes; its method ledger retains those four and adds
exactly one `descriptive_result_artifact`. Authoritative ledgers contain their
own actual stage-local files under the same rank and entry-shape rules; comparison
ledgers never replace an authoritative C0-C3 checkpoint. These comparison ledgers exist only for
`sqlite_authorized`; PostgreSQL comparison fields are null. The per-run
census serializer is the sole producer; neither comparison object hashes a
reconstructed or abbreviated ledger.

The handoff `+0` row means no product, package, handoff, or application-storage
row/file mutation. It does not prohibit the explicitly named post-package
outcome receipts or separately enumerated runner/control evidence in the
isolated evidence root; those are recursively redacted non-product closeout
evidence and never linked as delivered or authoritative application output.

Any unexpected table delta, file creation, second raw copy, or uncensused `CaveatNote` is a failed proof, not harmless test residue.

## 7. Support-matrix and environment correction

The support matrix is exhaustive for capability mirrors. The new capability identifier is exactly `layer3_connector_promotion_bridge`; no alias or second capability entry is permitted. B1b must add that one experimental, default-off capability consistently across exactly these eight support surfaces:

1. `config/support_matrix.yaml`
2. `scripts/support_matrix_constants.py`
3. `scripts/support_matrix_check.py`
4. `scripts/support_matrix_runtime_contract_audit.py`
5. `backend/tests/test_support_matrix.py`
6. `backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py`
7. `docs/support-matrix-local-expert.md`
8. `README.md` front door

No ninth support-matrix authority may be invented. The eight entries must agree on capability identifier `layer3_connector_promotion_bridge`, `experimental_default_off` posture, exact flag name, default false value, and synthetic/local proof boundary. Add `LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED` to the selected profile's `pinned_false_flags`, to `PINNED_FALSE_FLAGS`, and to the pinned runtime-default audit and exhaustive tests; a missing, true, non-boolean, aliased, or unprobed value fails the support contract. The entries must not upgrade the current ScienceBase acquisition slice to integrated, official-data, production, breadth, utility, or default-on support.

The eight entries above are the canonical support-matrix authorities, but they are not the
entire dependent edit census. Keep the exact capability count/status coverage in
`backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py`, the independent
pinned-flag list in
`backend/tests/test_sec_xbrl_offline_honesty_ceiling_exhaustive.py`, and the ambient-env
false pin in `scripts/local_profile_acceptance.py` coherent. Update the independent root API
capability-count assertion in `tests/test_api.py`, the current first-boot flag inventory, and
the admission map's exact capability-count statement. The bridge is a
local synthetic capability: startup must fail closed if the flag is true in nonlocal mode,
`docs/layer3-production-activation.md` must keep it outside the activated production set,
and the reference production Compose file must not thread or assign it. The deploy Compose
contract test must enforce that absence. Extend the canonical nonlocal forbidden-flag
coverage in `backend/tests/test_layer3_safety_contract.py`. Update
`docs/layer3-route-authorization.md` for the three protected pre-body routes and freshly
derive its route census. In `docs/first-boot-capabilities.md`, freshly regenerate and verify
the full OpenAPI path count; do not arithmetically assume the old count plus three, and
downgrade any `[verified]` claim that was not actually exercised. Dynamic consumers that import the canonical
constants need no mechanical edit unless the changed contract actually requires one.

Environment examples are supplemental configuration surfaces, not additional support-matrix authorities. Add `LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED=false` to every applicable tracked example:

- `backend/.env.example`
- `backend/.env.production.example`
- `deploy/.env.deploy.example`
- `docs/layer3-nonlocal.env.template`

No applicable example may set it true, imply rollout, or omit the default-off warning.
`onlook-ui/.env.example` is intentionally excluded: it configures the separate Onlook UI
development surface and does not configure the FastAPI/Layer 3 runtime or reference deploy.

## 8. Pre-body authorization and route coverage

### 8.1 Outer-controller custody and worker-issued PASS-TO-LAUNCH attestation

Section 16 rails are universal literals, not attestation-derived values. Every
profile derives preflight authority, environment, root, fixture, test-manifest,
and resource facts directly from the frozen sources and verified runtime. Only
`sqlite_authorized` and `postgresql_authorized` additionally persist and reopen
the exact PASS-TO-LAUNCH equalities below. `sqlite_default` never creates, opens,
hashes, or dereferences `pass-to-launch.json`.

Path 30 has exactly two mutually exclusive modes in the same PowerShell file:
the default outer controller and a private inner worker mode that only that
controller may start with the exact intent/hash/controller-identity arguments
defined below plus exactly one private-worker-only `deadline_section_handle`
argument. It is the controller's exact inheritable read-only duplicate raw
`HANDLE`, encoded as positive canonical unsigned pointer-width ASCII decimal.
The worker rejects an empty or duplicate argument, any sign or whitespace, a
leading zero, zero, `INVALID_HANDLE_VALUE`, pointer-width overflow or out-of-
range value, or any noncanonical encoding. Direct worker-mode invocation, a
second controller, another wrapper, or arbitrary command passthrough fails
before application import.
The outer controller remains outside the unnamed attempt Job. The inner worker
is one added PowerShell process relative to the predecessor topology; it and
every descendant are inside that Job before first resume. No Python process is
added. Except where a clause expressly says `controller`, the prospective
`runner` role and legacy `runner_*` evidence fields below mean the inner worker.

PowerShell trust is frozen, never runtime-selected. The controller image and the
image it launches for private worker mode are both the final-handle path
`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`, byte length
`454656`, AMD64, file/product version `10.0.26100.8457`, and SHA-256
`0ff6f2c94bc7e2833a5f7e16de1622e5dba70396f31c7d5f56381870317e8c46`.
Its offline Catalog/OS-binary chain must be valid and contain exactly the
SHA-256 leaf `3f069b40083185292bc236dbe97b21e0be81bac58935c5c1534005845987c639`,
intermediate `e8e95f0733a55e8bad7be0a1413ee23c51fcea64b3c8fa6a786935fddcc71961`,
and root `df545bf919a2439c36983b54cdfc903dfa4f37d3996d8d84b4c31eec6f3c163e`.
The controller launches that same image by verified full path and the worker
reproduces every literal from its own final handle. These values are candidate
constants, not values learned from the host at execution. Any OS-servicing
mismatch requires a successor candidate. Native interop is in-memory
`Reflection.Emit` only; `Add-Type`, CodeDOM, `csc`, a temporary assembly, or any
helper process/file is forbidden.

The feature flag is necessary but never sufficient. The authorized proof runner
is the only production issuer of `pass-to-launch.json`; its closed top-level
schema is exactly:

```json
{"schema_id":"layer3.b1b.pass_to_launch.v1","issued_at_utc":"<RFC3339Z>","expires_at_utc":"<RFC3339Z>","single_run_nonce":"<64-lowercase-hex>","authority":{},"runtime":{}}
```

`authority` has exactly `packet`, `predecessors`, `fixture`, `correction`,
`ratification`, `scope_clarification`, `earlier_owner_selection`,
`dispatch_owner_decision`,
`operator_context_root`, `owner_bound_main_sha`, `candidate_head_sha`, and
`i12_disposition`. In this subsection, `P` is a positive JSON integer only, `N`
is a nonnegative JSON integer, `H` is a lowercase 64-hex SHA-256, `G` is a
lowercase 40-hex Git object ID, and `T` remains a nonempty NFC-normalized safe
ASCII token whose exact bytes number 1 through 160, without slash, backslash,
colon, whitespace, or traversal. `J` is the exact pytest-emitted Unicode-scalar
safe repo-relative node ID whose D33-encoded UTF-8 bytes number 1 through 1024: it
has `/` separators, no empty/dot/dot-dot segment, drive/UNC prefix, NUL, CR, or
LF, and undergoes no Unicode, slash, case, or other normalization.
`DBNAME` is the exact nonempty Unicode-scalar text returned by
`current_database()`, with no NUL or rewriting. `RFC3339Z` is exactly a valid UTC
instant rendered `YYYY-MM-DDTHH:MM:SS.ffffffZ`. `U64DEC` is canonical nonzero
unsigned-64-bit ASCII decimal with no leading zero and value from 1 through
18446744073709551615. `U64ZDEC` is canonical unsigned-64-bit ASCII decimal with
no leading zero except the literal `0` and value from 0 through
18446744073709551615. `WINNS` is the exact existing-normalization Windows socket
namespace defined below. `IPHEX` is lowercase hex of exactly 8 or 32 characters;
the selected address family fixes which length is valid. Relative paths are NFC,
slash-normalized, contain no empty/dot/dot-dot segment, drive/UNC prefix, or
percent encoding, and must resolve beneath the already verified operator root
without a reparse point. Their closed schemas are:

- `packet` = `{operator_root_relative_path:<slash-normalized relative path>,
  byte_length:38002,full_sha256:<Section 2 full hash>,
  canonical_sha256:<Section 2 canonical hash>}`.
- `predecessors` is exactly the four Section 2.1 entries in order, each
  `{operator_root_relative_path:<relative>,byte_length:P,full_sha256:H}`.
- `fixture` = `{source_fixture_id:"F07",proof_cell_id:"C01",byte_length:34,content_sha256:<F07 hash>,
  regular_file:true,read_only:true,reparse_point:false,
  canonical_path_namespace_sha256:H}`; no path is recorded.
- `correction` = `{repo_relative_path:
  "next_milestone_plans/Layer3_planning_docs/b1b-dispatch-correction.md",
  byte_length:P,full_sha256:H,git_blob:G,owner_bound_main_sha:G}`.
- `ratification` = `{operator_root_relative_path:
  "state/agent-inbox/b1b-ratification-2026-07-13.md",byte_length:10942,
  full_sha256:"cc56d146d2574ce66e80e0b4bf3dc509b5213bdfd8b9310ec06ef99ee4d5298a",
  canonical_sha256:"6b21bc536c49708e72f4b8c15cce1ae2bec483c4c659d426f62a8f46ce7afa9b"}`.
- `scope_clarification` = `{operator_root_relative_path:
  "state/agent-inbox/b1b-scope-2026-07-13.md",byte_length:4304,
  full_sha256:"94667bf8b61902f2abd79cdf531177d55bfc3a30fd3ac8b4158d9024d48f940e",
  canonical_sha256:"cc5e7d62dfe41e407ee180caeef95ce29f7d2dbcedfff5c8d90c0aff2a095a4b"}`.
- `earlier_owner_selection` binds only the Section 2.2 record and is exactly
  `{operator_root_relative_path:<relative>,byte_length:9063,
  full_sha256:"534cd5a70825c88b3f722754bb0e6dffb52626c5bb3da4c32e33fe5afb24ca9f"}`.
  It carries no invented canonical/self hash and authorizes only D1=B and
  CT3-08=M1.
- `dispatch_owner_decision` is the later valid Section 13 Stage-2 record and is
  exactly `{operator_root_relative_path:<relative>,byte_length:P,
  full_sha256:H,canonical_sha256:H,decision_key_sha256:H}`. The last digest is
  SHA-256 of `project6-owner-decision-key-v1`, NUL, then the exact UTF-8 owner
  key. The raw key is a nonsecret authorization phrase retained only inside the
  owner decision record (and an authorized byte-for-byte archive copy); it never
  enters the runner child, attestation, package, API body, external evidence,
  log, or other status mirror. Runtime/evidence carries only this domain-
  separated digest.
- `operator_context_root` = `{root_id:T,canonical_namespace_sha256:H}`;
  `owner_bound_main_sha:G` and `candidate_head_sha:G` are scalar siblings.
- `i12_disposition` = `{selection:<I12-EXHAUSTIVE-ARCHIVE-COMPLETE|I12-PENDING-DOES-NOT-BLOCK-THIS-DISPATCH>,
  exhaustive_archive_manifest_full_sha256:<H|"NA">,
  decision_child_manifest_full_sha256:<H|"NA">,
  source_census_sha256:<H|"NA">}`. COMPLETE
  requires three hashes; PENDING requires three exact `NA` values. Under COMPLETE,
  `exhaustive_archive_manifest_full_sha256` is the lowercase full-file SHA-256
  of the ballot-identified exhaustive `ARCHIVE_MANIFEST.json`,
  `decision_child_manifest_full_sha256` is the lowercase full-file SHA-256 of
  the exact `DECISION_ARCHIVE_MANIFEST.json`, and `source_census_sha256` retains
  the exact ballot-to-census mapping below. These names are atomic and exhaustive;
  no receipt, child, generic digest, or compatibility alias is accepted. Under
  PENDING all three fields are exactly `NA`; no absent, partial, bounded-archive,
  or inferred value is accepted.

`fixture.canonical_path_namespace_sha256` is produced only after opening the
Section 2.1 fixture by handle, proving regular/non-reparse/ReadOnly status, and
normalizing the final handle path by uppercasing the drive letter, converting
`\` to `/`, NFC-normalizing, preserving all other case, and removing no segment.
The normalized value must equal the literal
`C:/p6fixtures/sciencebase-v1/water-quality.csv`. The digest is the
D33-canonical SHA-256 of exactly:

```json
{"canonical_path":"C:/p6fixtures/sciencebase-v1/water-quality.csv","normalization":"windows-final-handle-upper-drive-forward-slash-nfc-case-preserved-v1","schema_id":"layer3.b1b.fixture_path_namespace.v1"}
```

The runner is the sole producer. `preflight.fixture` persists the digest for all
profiles; launched-authorized PASS-TO-LAUNCH is the second persisted consumer and
carries only that same digest. Path inequality, alternate namespace, reparse resolution,
or digest mismatch fails before any B1b read.

`i12_disposition.source_census_sha256` is not a second census producer. For
`I12-EXHAUSTIVE-ARCHIVE-COMPLETE`, it equals the final ballot's
`i12_source_census_sha256` after validating exactly 64 uppercase hex characters
and converting only ASCII `A`-`F` to lowercase; the underlying 32 digest bytes
are unchanged. For `I12-PENDING-DOES-NOT-BLOCK-THIS-DISPATCH`, both fields are
the literal `NA`. Any other spelling, case, length, selection/value combination,
or inequality invalidates the owner record and stops before attestation.

`runtime` has exactly `profile`, `lane_parent_id`,
`lane_parent_canonical_sha256`, `runtime_root_id`,
`runtime_root_canonical_sha256`, `storage_root_id`,
`storage_root_canonical_sha256`, `database_root_id`,
`database_root_canonical_sha256`, `evidence_root_id`,
`evidence_root_canonical_sha256`, `root_bindings_sha256`,
`database_identity_sha256`, `postgresql_storage_binding_sha256`,
`runner_git_blob`, `runner_full_sha256`, `release_lock_git_blob`,
`release_lock_full_sha256`, `proof_lock_git_blob`, `proof_lock_full_sha256`,
`python_runtime`, `environment_inventory_sha256`,
`environment_allowlist_sha256`,
`distribution_record_inventory_sha256`, `pip_check_output_sha256`,
`test_manifest`, `test_manifest_sha256`, `application_source_sha`,
`launch_protocol`, `launch_claim_id`, `expected_command_sha256`, `launch_ordinal`,
`external_request_budget`, `max_process_tree_rss_bytes`,
`max_profile_bounded_bytes`, and `max_invocation_seconds`. Values must equal the
Section 16 profile and ceilings; `profile` is `sqlite` or `postgresql`, and
`external_request_budget` is zero. `max_profile_bounded_bytes` is exactly
`1073741824` and caps the complete profile accounting defined in Section 9, not
only the runtime child or on-disk lane parent. `python_runtime` is the closed Section 16
CPython identity object; `launch_protocol` is exactly
`windows-suspended-single-child-v1` and `launch_ordinal=1`. Root IDs/hashes
reveal no absolute path. `postgresql_storage_binding_sha256` is `H` only for
`postgresql_authorized` and is null for `sqlite_authorized`.

`runtime.application_source_sha:G` equals
`authority.candidate_head_sha`, `preflight.candidate_head_sha`, and the verified
child `PROJECT6_SOURCE_SHA` exactly. The runner derives all four from the one
candidate-head Git identity before launch; no worktree label, branch name,
checkout guess, or separately supplied source value may substitute.

The controller creates one absent lane parent and then exactly four absent
direct directory children in this order: `runtime`, `storage`, `database`,
`evidence`. No directory child is nested beneath another. The lane parent's
exhaustive permitted direct-member set is those four directories plus exactly
the control basenames `attempt-intent.json` and `attempt-closeout.json`.
`attempt-intent.json` is absent until the final durable pre-`CreateProcess`
step; `attempt-closeout.json` is absent until controller closeout. Both are
outside the evidence child and never enter a worker manifest, package, or
application artifact. Any other direct member is invalid control state.
The controller supplies the verified parent and child bindings to the worker,
which persists every `root_id` plus `canonical_sha256` in preflight for every
profile and additionally in PASS-TO-LAUNCH runtime for launched authorized
profiles; no path persists.
For each role, `canonical_sha256` hashes exactly
`{"canonical_namespace":<normalized absolute namespace>,"normalization":
"windows-upper-drive-forward-slash-nfc-case-preserved-no-terminal-slash-v1",
"role":<lane_parent|runtime|storage|database|evidence>,"root_id":T,
"schema_id":"layer3.b1b.root_namespace.v1"}`. The verified final handle of the
nearest existing parent plus the single absent descendant name produces the
lane-parent namespace; after create-once, each root's own final handle must
reproduce it. The controller's root resolver is the sole producer; the worker
reopens and validates the supplied bindings before application import.

`root_bindings_sha256` hashes exactly
`{"children":[...],"parent":{"canonical_sha256":H,"root_id":T},
"schema_id":"layer3.b1b.root_bindings.v1"}`. `children` contains four objects
in `runtime`, `storage`, `database`, `evidence` order, each exactly
`{canonical_sha256:H,parent_canonical_sha256:H,parent_id:T,role:<exact>,
root_id:T}`. Every child names the persisted lane parent. Handle-based ancestry
must prove each child is one segment below that parent, all five roots are
non-reparse, and the four children are pairwise distinct, nonancestor siblings.
Any alias, descendant nesting, pre-existence, order drift, undeclared direct
member, or hash inequality stops before application import.

`database_identity_sha256` has one profile-specific preimage. SQLite hashes
exactly `{"database_root_canonical_sha256":H,"database_root_id":T,
"profile":"sqlite","relative_name":"b1b.sqlite3",
"schema_id":"layer3.b1b.database_identity.v1"}`. PostgreSQL hashes exactly
`{"database_name_sha256":H,"database_root_canonical_sha256":H,
"database_root_id":T,"profile":"postgresql",
"schema_id":"layer3.b1b.database_identity.v1",
"server_instance_identity_sha256":H}`.

The PostgreSQL leaf digests are closed. `database_name_sha256` hashes exactly
the D33-canonical object
`{"database_name":DBNAME,"schema_id":"layer3.b1b.postgresql_database_name.v1"}`.
`DBNAME` comes from that connection's `current_database()` result exactly;
trimming, case folding, Unicode normalization, or other rewriting fails.
`server_instance_identity_sha256` hashes exactly
`{"pg_postmaster_start_utc":RFC3339Z,"schema_id":"layer3.b1b.postgresql_server_instance_identity.v1","server_version_num":P,"system_identifier":U64DEC}`.
`server_version_num` is a positive JSON integer; the other fields use the exact
closed types above.

`socket_or_loopback_identity_sha256` hashes exactly one profile-selected
D33-canonical transport object. Unix socket form is
`{"class":"unix_socket","peer_namespace":WINNS,"schema_id":"layer3.b1b.postgresql_transport_identity.v1"}`.
`WINNS` is the nonempty filesystem namespace read from the connected OS socket
handle, normalized by uppercasing the drive letter, using `/`, NFC, preserving
remaining case, and removing a terminal slash; abstract namespaces fail. TCP
form is
`{"address_family":<ipv4|ipv6>,"class":"loopback_tcp","peer_address_hex":IPHEX,"peer_port":P,"schema_id":"layer3.b1b.postgresql_transport_identity.v1"}`.
IPv4 hex is exactly 8 lowercase characters and must decode inside `127/8`; IPv6
hex is exactly 32 lowercase characters and must decode to `::1`; IPv4-mapped
IPv6 is rejected. `peer_port` is an integer from 1 through 65535.

The same connected socket handle supplies the transport peer. The same
unpooled PostgreSQL connection and one short read-only transaction supply
`current_database()`, postmaster start, server version, system identifier, and
the preprovisioned role contract; reconnect, pooling, DNS, or cross-connection
composition fails. Every runner, monitor, provider, Alembic, SQLAlchemy, and
application connection must reproduce `current_user=session_user`; that role
owns the bound database and schema; `rolcanlogin=true`, `rolinherit=true`,
`rolsuper=false`, `rolcreatedb=false`, `rolcreaterole=false`,
`rolreplication=false`, `rolbypassrls=false`, `rolconnlimit=3`, and
`rolvaliduntil=null`. Its only direct role membership is `pg_monitor`, whose
`pg_auth_members` row has `admin_option=false`, `inherit_option=true`, and
`set_option=false`. No `SET ROLE`, grant, ACL, role/config, service, or engine
mutation is permitted. At most three connections may be simultaneous, and all
control transactions are short and read-only. The runner verifies these values
in memory; only existing hashes and endpoint accounting persist.

The runner is the sole leaf producer and only the hashes persist. Neither
DB-identity preimage contains endpoint identity. PostgreSQL endpoint identity
hashes exactly
`{"class":<unix_socket|loopback_tcp>,"database_identity_sha256":H,"schema_id":"layer3.b1b.endpoint_identity.v1","server_instance_identity_sha256":H,"socket_or_loopback_identity_sha256":H}`.
Endpoint identity consumes DB identity one way; DB identity never consumes or
predicts endpoint identity. No sandbox DSN, extra database, plural endpoint, or
runtime-created role resource is introduced.

Every persisted volume-identity digest uses one exact path-free preimage:
`{"schema_id":"layer3.b1b.windows_volume_identity.v1","volume_guid":"<36-lowercase-uuid>","volume_serial_hex":"<8-lowercase-hex>"}`.
The controller is the sole producer for the lane-parent control-volume identity;
the worker is the sole producer for the runtime, storage, database, evidence, and
engine-volume identities. The applicable producer obtains both values from the
verified final handle's fixed local Windows volume, D33-canonicalizes that object,
and persists only its SHA-256. It reopens the relevant handle and reproduces the
digest before every free-space or size sample. A nonfixed, mapped, UNC, network,
inaccessible, or identity-drifting volume fails before the sample is accepted.
For SQLite, the database-volume identity is the volume containing its bound
database child.

Authoritative PostgreSQL proof is narrower than ordinary semantic CI. It requires
one native same-host Windows PostgreSQL engine under the runner's existing
process/endpoint policy. A container, Windows service, remote engine, UNC or
mapped/network storage, POSIX engine path, or unresolvable engine path may run
non-authoritative fake/semantic checks but cannot produce
`postgresql_authorized` proof. Resolution is read-only: no elevation, ACL change,
service mutation, helper process, engine reconfiguration, or filesystem write is
permitted.

The retained unpooled read-only identity connection and its existing transaction
also enumerate `data_directory`, the current database OID and database
tablespace, the effective default tablespace, every effective temporary
tablespace, every relation tablespace, and the final target of `pg_wal`. The
runner final-handle resolves every writable location, rejects an inaccessible,
nonlocal, nonfixed, reparse, or identity-drifting result, and deduplicates the
resulting volume identities. Nondefault tablespaces are admissible only when all
resolved locations still satisfy the one-fixed-volume requirement.

`postgresql_storage_binding` is exactly
`{database_identity_sha256:H,endpoint_identity_sha256:H,layout:"windows-native-all-writable-one-fixed-volume-v1",database_oid:P,writable_locations:[...],distinct_volume_identities:[H],distinct_volume_count:1,database_volume_identity_sha256:H,schema_id:"layer3.b1b.postgresql_storage_binding.v1"}`.
Each `writable_locations` entry is exactly
`{kind:<data_directory|database_tablespace|default_tablespace|temp_tablespace|relation_tablespace|pg_wal>,object_oid:<P|null>,ordinal:P,volume_identity_sha256:H}`.
Entries use that displayed kind order, then unsigned OID and source order; every
applicable location occurs once. `distinct_volume_identities` is the sorted,
deduplicated identity array and contains exactly the same single `H` as every
location and `database_volume_identity_sha256`. Raw engine paths, volume GUIDs,
serials, role rows, and endpoint material remain memory-only. The binding hash is
the D33-canonical SHA-256 of the complete object.

The producer graph is strictly one-way: `database_identity_sha256` feeds
`endpoint_identity_sha256`; both feed `postgresql_storage_binding`; that binding
then feeds preflight and the resource state contract for every PostgreSQL
invocation. It feeds launched-authorized PASS-TO-LAUNCH and an endpoint-ledger
sibling co-binding only on a launched path. Every reached C0-C3 checkpoint state
carries the binding in memory when that checkpoint state is applicable; complete
persisted checkpoint siblings consume it only after C3 publication. Neither
storage binding nor any storage fact feeds back into database identity, endpoint
identity, or endpoint policy. A cycle, omitted writable location or applicable
consumer, hash inequality, layout/order drift, more or less than one deduplicated
fixed volume, inaccessible handle, or tablespace mismatch is STOP.

File-identity edges are exact. `runner_full_sha256`,
`release_lock_full_sha256`, `proof_lock_full_sha256`, and
`test_manifest.plugin_policy.explicit_plugin.full_sha256` each hash the complete
bytes read once through the verified regular non-reparse file handle. Those
handle-read bytes must equal the contents of the corresponding candidate-head
Git blob byte-for-byte. `runner_git_blob`, `release_lock_git_blob`,
`proof_lock_git_blob`, and `test_manifest.plugin_policy.explicit_plugin.git_blob`
remain native Git object IDs; none is a SHA-256 alias or digest preimage.
`python_runtime.executable_sha256` likewise hashes complete executable-image
bytes read through the verified interpreter file handle. Competing-process
census entries intentionally carry no executable-byte digest, path, command, or
semantic-role claim; their identity is only the verified PID/start pair under
the closed basename selector below. No path string, worktree read, metadata-only
interpreter identity, or reconstructed content may substitute for the runtime
handle-byte hash.

`environment_allowlist_sha256` has one exact preimage. The runner builds
`{"entries":[...],"profile":"<sqlite|postgresql>","schema_id":"layer3.b1b.environment_allowlist.v1"}`
with the following `{name,source}` entries in ASCII name order and no others:

```text
COMSPEC = verified_system32_cmd
DATABASE_URL = isolated_database_url
DB_INIT_MODE = literal_none
DEPLOYMENT_MODE = literal_local
LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED = literal_false
LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED = manifest_bridge_enabled
LAYER3_MIGRATION_TEST_DATABASE_URL = isolated_same_identity_postgresql_url
LAYER3_MODEL_EGRESS_ENABLED = literal_false
LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED = literal_false
LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED = literal_false
LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED = literal_false
LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED = literal_false
LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED = literal_false
LAYER3_SEC_EDGAR_OFFICIAL_TICKER_RESOLUTION_ENABLED = literal_false
LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED = literal_false
LAYER3_SEC_XBRL_STORAGE_ROOT_HYGIENE_OVERRIDE_ACK = literal_false
PATH = verified_venv_scripts_only
PATHEXT = literal_com_exe_bat_cmd
PIP_CONFIG_FILE = literal_NUL
PIP_DISABLE_PIP_VERSION_CHECK = literal_1
PIP_NO_CACHE_DIR = literal_1
PIP_NO_INDEX = literal_1
PROJECT6_B1B_ATTESTATION_PATH = verified_attestation_path
PROJECT6_B1B_ATTESTATION_SHA256 = attestation_sha256
PROJECT6_B1B_CONTROL_CONTINUE_EVENT_HANDLE = runner_inherited_control_continue_event_wait_handle
PROJECT6_B1B_CONTROL_SAMPLE_PIPE_HANDLE = runner_inherited_control_sample_pipe_write_handle
PROJECT6_B1B_DATABASE_PROFILE = manifest_database_profile
PROJECT6_B1B_RUN_NONCE = runner_single_run_nonce
PROJECT6_B1B_TEST_MANIFEST_SHA256 = test_manifest_sha256
PROJECT6_SOURCE_SHA = candidate_head_sha
PYTEST_DISABLE_PLUGIN_AUTOLOAD = literal_1
PYTHONDONTWRITEBYTECODE = literal_1
PYTHONHASHSEED = literal_0
PYTHONIOENCODING = literal_utf_8
PYTHONNOUSERSITE = literal_1
PYTHONPATH = candidate_head_backend
SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED = literal_false
STORAGE_DIR = isolated_storage_root
SYSTEMDRIVE = verified_system_drive
SYSTEMROOT = verified_system_root
TEMP = isolated_runtime_temp
TMP = isolated_runtime_temp
WINDIR = verified_system_root
```

Every profile includes both `PROJECT6_B1B_CONTROL_*_HANDLE` entries at their
displayed positions. `sqlite_default` omits exactly the two attestation entries
and `LAYER3_MIGRATION_TEST_DATABASE_URL`; `sqlite_authorized` omits exactly the
migration URL; `postgresql_authorized` includes the complete displayed set.
`literal_none` is the string `none`,
`literal_local` is `local`, `literal_false` is `false`,
`literal_com_exe_bat_cmd` is `.COM;.EXE;.BAT;.CMD`, `literal_0` is `0`,
`literal_utf_8` is `utf-8`, `literal_NUL` is `NUL`, and `literal_1` is `1`.
Every other source resolves
from profile-applicable frozen authority, manifest, verified OS/runtime identity,
or isolated root. The two handle sources resolve only at suspended-child creation
to canonical unsigned pointer-width decimal values with no leading zero; they
are process-local capabilities, not persisted identities. The runner rejects a
missing, extra, duplicate, case-different, or value-different environment entry
before launch.

The runner is the sole producer and D33-canonicalizes that closed profile object.
Every selected invocation's command binding consumes its lowercase digest;
authorized `runtime.environment_allowlist_sha256`, `expected_command_sha256`, and
launch claim persist the same value. Default uses the runner's direct transient
command binding and never dereferences those authorized records. No child
recomputes or widens it. Any inequality stops before resume and terminates the
owned suspended child. Raw URLs, roots, an authorized attestation path, and
control-handle values remain environment-only and never enter this preimage or
any persisted receipt.

The runner emits the exact D33-canonical object bytes: UTF-8, no BOM, and no
terminal newline. The environment SHA binds those exact bytes. For launched
authorized profiles it expires the attestation exactly 1,200 seconds after
issuance, reopens/re-hashes it, and sets Windows ReadOnly. Every child starts from
a scrubbed allowlist environment, not inherited ambient state. Every child
receives exactly its profile projection
of the exhaustive Section 8.1 list and no others. `STORAGE_DIR` is the sole storage-root
environment entry; current settings derive the artifact, raw, and snapshot
descendants from that isolated root in process, so no additional root variable
is permitted. The displayed default-off capability entries are the exhaustive
false set. Every launched profile receives its two inherited control-handle
values; launched authorized profiles alone receive the attestation path/hash, and
PostgreSQL alone also receives the same-identity
`LAYER3_MIGRATION_TEST_DATABASE_URL`.
Credentials, URLs, and raw handles remain environment-only and are redacted from
every receipt and log. No proxy, index URL, package config, user-site, ambient
`PYTHONPATH`, cloud, browser, telemetry, package-manager, credential-store, or
user Python environment value is inherited. The target's displayed
`PYTHONPATH=candidate_head_backend` is a runner-created replacement, never an
inherited value; isolated `-I` probes ignore it. Authorized
attestation values, root/URL values, and raw handles are never persisted or
projected.

Activation is split rather than implicit. Default/posture/regression
invocations receive `LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED=false`.
Authorized B1b integration invocations receive it as `true`, and the production
verifier requires the real runner attestation before every B1b write. The
inert verifier adapter is permitted only in isolated unit tests of call order
and failure wiring; it is forbidden in the authoritative SQLite integrated
slice, the PostgreSQL concurrency/migration slice, and merged-main rerun. A
global true environment over default-posture tests, a settings monkeypatch in
the authoritative slice, or proof through the inert adapter is inadmissible.

The outer controller acquires `Global\project6-b1b-controller-v1` before lane
inspection and holds it to process teardown; its ACL admits only the verified
operator SID and `SYSTEM`. Inaccessible/contended acquisition stops. An abandoned
mutex permits only the following retained-lane census.

Under that mutex the controller exhaustively enumerates every direct lane parent
under `%LOCALAPPDATA%/project6-b1b`. Each must contain one valid, identity-matched
intent/closeout pair. No intent, orphan intent, unreadable/torn/hash/schema/
identity-invalid or inaccessible closeout, or `BARRED_UNKNOWN` bars every later
attempt. PID absence, age, cleanup, copying, or reconstruction cannot clear it;
only a separately owner-authorized recovery audit and specification amendment can.

Every retained `PASS`, `FAIL`, incomplete, quarantined, orphaned, or otherwise
barred lane consumes one irrevocable slot and one full `1073741824`-byte logical
reservation. The cap is exactly 14 slots: cycle 1 is the seven Section 16
invocations in displayed order and cycle 2 repeats that complete order once.
The existing lane-parent basename therefore includes canonical `c<1|2>-s<01..14>`
components before backend and nonce; this is classification of the existing root,
not a new path or artifact. Missing, duplicate, malformed, or out-of-cycle slot
identity bars the census. Logical reservation is admission arithmetic, not disk
preallocation and not a 14-GiB free-space claim. Slot 15 is rejected before lane,
root, control, or process creation.

After a clean census and admitted slot, the controller creates the lane parent
and its four roots, binds their handles and identities, and derives the fixed
expected lane-control volume identity before any control write. It pre-renders the complete intent and
requires its exact byte length to be at most `65536`. Immediately before the
create-new write, a trusted lane-parent handle must reproduce that expected fixed
local volume identity and report free bytes at least
`4294967296 + attempt_intent_byte_length + 262144`. A failure creates no control
artifact and performs no `CreateProcess`; the untouched no-intent partial lane is
permanently barred by every later retained-lane census unless a separate owner-
authorized recovery audit and specification amendment permits recovery.

The controller then create-once writes `attempt-intent.json` with exactly:

```text
schema_id=layer3.b1b.attempt_intent.v1; attempt_id:H; created_at_utc:RFC3339Z; profile:<sqlite_default|sqlite_authorized|postgresql_authorized>; invocation_name:T; candidate_head_sha:G; correction_full_sha256:H; controller:{pid:P,process_start_sha256:H}; runner_full_sha256:H; lane_parent_id:T; lane_parent_canonical_sha256:H; root_bindings_sha256:H; worker_mode:"private-inner-worker-v1"; job_policy:{unnamed:true,kill_on_close:true,breakaway_ok:false,silent_breakaway_ok:false,active_process_limit:3,job_memory_limit_bytes:1610612736,atomic_job_list:true,descendants_inherit_job:true}; limits:{proof_deadline_milliseconds:900000,containment_deadline_milliseconds:930000,max_process_tree_rss_bytes:2147483648,max_owned_private_commit_bytes:2147483648,min_free_memory_bytes:4294967296,max_profile_bounded_bytes:1073741824}
```

`attempt_id` is fresh lowercase 64-hex. Intent is D33-canonical UTF-8/no-BOM/no-
newline, create-new/no-clobber, flushed, closed, ReadOnly, then no-follow reopened
through a regular non-reparse handle and byte/schema/hash verified.
`attempt_intent_sha256` is SHA-256 of those exact complete reopened bytes. Intent
is the last durable pre-`CreateProcess` act; no temp, rename, journal, marker, or
third control artifact exists.
`max_process_tree_rss_bytes` is an observational-vector ceiling only; the
`job_policy` hard limits and later Job accounting are authoritative.

Before the intent write, the controller creates the endpoint monitor, one unnamed
noninheritable Job, one noninheritable one-shot nonresetting waitable timer, and
one unnamed pagefile-backed 4096-byte section by
`CreateFileMapping(INVALID_HANDLE_VALUE,null,PAGE_READWRITE|SEC_COMMIT,0,4096,
null)`. It configures and queries back kill-on-close, no breakaway or silent
breakaway, `ActiveProcessLimit=3`, and `JobMemoryLimit=1610612736` before any
process creation; mismatch stops with no intent. Its read-write handle and view
are noninheritable. `DuplicateHandle`
uses `dwDesiredAccess=SECTION_MAP_READ`, `bInheritHandle=TRUE`, and
`dwOptions=0`, never `DUPLICATE_SAME_ACCESS`, for one worker duplicate. The
controller constructs the exact `deadline_section_handle` argument and one-entry
`PROC_THREAD_ATTRIBUTE_HANDLE_LIST` from that raw value. A controller watchdog
thread is ready before intent. The controller then irrevocably sets
`attempt-D0=GetTickCount64()`, computes checked `attempt-D1=D0+900000` and
`attempt-D2=D0+930000`, arms the timer, and verifies timer/watchdog readiness.
Overflow or readiness failure stops with no intent or process. At D1 the watchdog
calls `TerminateJobObject`; at D2 it calls `TerminateProcess` on the controller
itself unless a create-new, reopened, valid closeout has been acknowledged.
Neither deadline resets. Intent remains the last durable pre-`CreateProcess` act.

The sole worker `CreateProcess` uses `bInheritHandles=TRUE`, exactly
`EXTENDED_STARTUPINFO_PRESENT|CREATE_SUSPENDED`, and one `STARTUPINFOEX` with
exactly two attributes: `PROC_THREAD_ATTRIBUTE_JOB_LIST` containing the Job
handle and `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` containing only the deadline-
section handle. The Job handle is noninheritable and never enters the worker.
Atomic creation in the Job is mandatory; `AssignProcessToJobObject` and every
post-create fallback are forbidden. Any requested/injected extra attribute or
handle fails before creation. The controller and database engine remain outside
the Job. After successful suspended creation it binds the exact worker PID/start,
queries the Job to reproduce membership and limits, and closes its local read-
only section duplicate. Create failure closes transient handles and follows the
orphan/barred rules without retry.

The section's exact D33-canonical payload has only
`schema_id="layer3.b1b.controller_worker_deadline.v1"`, `attempt_id`,
`attempt_intent_sha256`, `profile`, `invocation_name`, `controller`, `worker`,
`clock="GetTickCount64"`, `attempt_d0_tick_milliseconds`,
`attempt_d1_tick_milliseconds`, and `attempt_d2_tick_milliseconds`.
`controller` and `worker` are their exact `{pid:P,process_start_sha256:H}`
objects; each tick is `U64ZDEC`. Bytes 0-3 are unsigned little-endian length `L`;
bytes 4 through `3+L` are the exact UTF-8/no-BOM/no-newline payload; every
remaining byte is zero; and `1<=L<=4092`. The payload has no self-hash.

The controller immediately zeros all 4096 bytes, writes the payload, executes a
publication barrier, writes the length last, executes a second barrier and
`FlushViewOfFile`, then copies, rereads, and validates all 4096 bytes. It computes
`deadline_mapping_sha256` as SHA-256 of all final 4096 bytes, unmaps the writable
view, and closes every writable section handle before worker resume. There is no
file, pipe, event, artifact, environment value, or separately durable handoff of
deadline bytes or an expected mapping hash. The sole transient locator is the
private-worker `deadline_section_handle` argument, and it conveys only the
section handle.

Only after all three nonnull `attempt-D0`/`attempt-D1`/`attempt-D2` facts, atomic
worker membership, the
exact mapping length/hash facts, successful full-byte validation, writable-view
unmap, and closure of every writable mapping reference exist does the attempt
cross its closeout-eligibility boundary. Any failure after worker creation but
before that complete boundary immediately calls `TerminateJobObject`, performs
best-effort physical custody, leaves the durable-intent orphan bar, creates no
closeout and no disposition, and permits no retry.

After that boundary, the controller rechecks the already-armed timer and watchdog;
`GetTickCount64` comparisons remain authoritative. It then takes ordinal-1
resource sample at
actual elapsed time less than 1000 milliseconds. Immediately before resume it
requires the timer remains unsignaled, current tick is less than both
`attempt-D0+1000` and `attempt-D1`, sample cadence is intact, and no writable
section reference remains. It calls `ResumeThread` exactly once and records
`resume_succeeded` plus `resume_previous_suspend_count`; successful resume
requires the returned count to be exactly `1`. `attempt-D0` remains valid if
resume fails. A timer/watchdog recheck, ordinal-1 sample, final pre-resume guard, or
resume failure immediately terminates the Job and may create a null-manifest
closeout. Such a closeout is `CONTAINED` only when every exhaustive custody
predicate below is proved; otherwise it is `BARRED_UNKNOWN` when writable, or
the orphan bar remains. No second create, mapping publication, or resume is
permitted.

The worker's first post-resume act, before application import, probe, child,
thread, or state production, parses and range-checks its sole
`deadline_section_handle` argument and calls `MapViewOfFile(FILE_MAP_READ)` on
that exact handle. It performs no handle-table enumeration, `NtQuery*` call, or
writable-map probe. It copies all 4096 bytes once, independently hashes them, and
validates length, canonical reserialization, zero tail,
attempt/intent/profile/invocation, controller/worker identities,
`GetTickCount64`, and checked deadline arithmetic. No bootstrap argument,
environment value, or second handle supplies expected mapping bytes or hash; the
locator supplies only the handle, the worker computes the digest independently,
persists it in preflight, and v2 later compares it with controller closeout. It
then unmaps and closes the section handle and requires current tick less than
`attempt-D1`. The locator's sole allowed exposure is private-worker argv/process
command line; it never reaches Python-target argv or environment, an artifact,
schema, manifest, ledger, digest/hash preimage, output, or log. A direct,
replayed, missing, duplicate, malformed, wrong, or nonmapping locator, including
zero, `INVALID_HANDLE_VALUE`, overflow, or out-of-range encoding, fails before
application import or state production. The mapping never enters any probe or
Python target. Every later
worker wait, bounded chunk, probe, launch, resume, ACK, frame, evidence write, or
root act checks `attempt-D1`; setup after `attempt-D0` consumes the same 900-second
budget.

The Job-bound worker creates exactly `Q=2` serial probes and then any target
suspended, verifies inherited membership, and resumes each once; it creates no Job, watchdog, timer, cancellation
handle, helper, or control artifact. Probes use the bound interpreter, `-B -I`,
scrubbed environment, isolated `TEMP`/`TMP`, and exact
`<venv-python> -B -I -m pip --isolated check`. Each serial probe's exit code and
physical exit are captured, then every probe process/thread reference is closed
before the worker requires Job active-process count exactly `1` (worker only).
Empty temp, endpoint, RECORD/venv, source-cache, process, and resource checks then
pass in that order before target creation. Before worker exit, every target and
descendant process/thread/control/monitor/DB reference is closed.

Controller resource sampling uses the `attempt-D0` clock. One initial stable
sample completes at actual elapsed time from 0 through 999 milliseconds; one
occurs at every completed `attempt-D0`-based 1000-millisecond cadence position
strictly before the terminal boundary; and one terminal sample occurs at
`min(observed worker exit,attempt-D2)`, replacing rather than adding to a
coincident prior query. Stored actual elapsed values are strictly increasing,
adjacent gaps are at most 1000 milliseconds, no sample follows `attempt-D2`, and
no missing value is reconstructed. A complete `PASS|FAIL` resource result has
1 through 931 samples; `INCOMPLETE` has 0 through 931.

The one-second cadence performs only cheap Job accounting, controller RSS, free-
RAM, fixed-volume free-space, and existing endpoint/network-counter reads. IOCP
notifications are advisory only. Exhaustive process, local-file/storage, and
PostgreSQL size censuses occur only at quiescent boundaries. No cadence result,
IOCP notification, or per-process observation may override hard Job limits or
accounting, and no process event is added.

Every B1b `free_memory_bytes` observation uses a zeroed `MEMORYSTATUSEX` with
`dwLength=sizeof(MEMORYSTATUSEX)`, one successful `GlobalMemoryStatusEx` call,
and exact `ullAvailPhys`. Every recorded per-process B1b RSS value uses
`PROCESS_MEMORY_COUNTERS_EX` with `cb=sizeof(PROCESS_MEMORY_COUNTERS_EX)` and
`K32GetProcessMemoryInfo(...).WorkingSetSize`. Controller peak private commit
uses `PROCESS_MEMORY_COUNTERS_EX.PeakPagefileUsage`; Job peak private commit uses
`QueryInformationJobObject(JobObjectExtendedLimitInformation).PeakJobMemoryUsed`.
The outer controller always passes its explicit controller-owned Job handle.
The worker process-ledger sampler and the exact preflight-only resource sampler
below pass `NULL` only for `JobObjectBasicAccountingInformation` and
`JobObjectBasicProcessIdList` queries against the worker's immediate attempt Job.
Neither performs a `PeakJobMemoryUsed` query; the process ledger has no peak
consumer or threshold, and the preflight-only resource branch persists only its
two checked middle-read RSS samples in the closed resource-ledger field below.
These facts make no PostgreSQL engine RSS claim.

Every quiescent-boundary observational process sample uses this exact stable-
census procedure:

1. Census 1 obtains `TotalProcesses`, unsigned-DWORD active count `C`, and
   `TotalTerminatedProcesses` from one successful
   `JobObjectBasicAccountingInformation` query and reproduces the configured
   active-process and memory limits. Checked arithmetic computes both
   required returned bytes
   `FIELD_OFFSET(JOBOBJECT_BASIC_PROCESS_ID_LIST,ProcessIdList)+C*sizeof(ULONG_PTR)`
   and allocation bytes
   `FIELD_OFFSET(JOBOBJECT_BASIC_PROCESS_ID_LIST,ProcessIdList)+max(1,C)*sizeof(ULONG_PTR)`;
   allocation bytes must fit both `SIZE_T` and the `DWORD` `cb` argument. One
   `JobObjectBasicProcessIdList` query then uses that buffer and a nonnull
   `ReturnLength`. Required returned bytes must be at most `ReturnLength`, which
   must be at most allocated `cb`; `NumberOfAssignedProcesses`,
   `NumberOfProcessIdsInList`, and `C` must be equal. When `C=0`, the allocated
   slot is ignored. Otherwise every returned PID is unique and in
   `1..DWORD_MAX`.
2. For each PID, the sampler borrows the exact already-retained,
   identity-bound lifecycle/monitor handle only when that handle supports every
   required query; a borrowed handle is never closed by the sampler. Otherwise
   it opens one temporary RSS handle with exact access `0x410`
   (`PROCESS_QUERY_INFORMATION|PROCESS_VM_READ`). An identity-only query uses
   exact `0x1000` (`PROCESS_QUERY_LIMITED_INFORMATION`). Neither path enables
   elevation or `SeDebugPrivilege`, and neither requests `PROCESS_ALL_ACCESS`.
   `GetProcessId` must round-trip to the enumerated PID, and
   `GetProcessTimes` creation `FILETIME` must derive the existing exact
   `process_start_sha256`. Borrowed and temporary handles remain open through
   Census 2.
3. Between censuses, the sampler reads each member handle's `WorkingSetSize`
   exactly once. Where applicable, the outer sampler also reads controller
   `WorkingSetSize` and `PeakPagefileUsage` exactly once. The outer sampler also
   reads explicit-Job-handle `PeakJobMemoryUsed` and
   `GlobalMemoryStatusEx(...).ullAvailPhys` exactly once. The worker Job census
   reads neither; any separate worker resource-ledger free-memory observation
   follows the provider rule above. No first/second maximum, equality, resample,
   reconstruction, or substitution is permitted. Worker process-ledger
   `rss_bytes` and each preflight-only resource
   `preflight_only_job.samples[].rss_bytes` are the checked sum of their respective
   middle member reads. Any outer quiescent per-process sum is diagnostic and
   memory-only. The per-process working-set sum is conservative and may
   double-count shared pages; it is sampled only and makes no continuous-memory
   claim. These per-process values are observational and churn-tolerant: an
   unstable set is discarded rather than converted into a hard-cap or custody
   fact, and a required quiescent boundary must stabilize before its deadline.
4. Census 2 repeats only the count/list procedure and requires the same sorted
   set of `{pid,process_start_sha256}`. Every retained member handle is rechecked
   for unchanged `GetProcessId` and creation `FILETIME`. The sampler closes only
   temporary opened handles, frees both census buffers, and proves successful
   cleanup before taking the checked `GetTickCount64` elapsed value. Only then
   may it accept the observational sample. Borrowed handles remain
   with their lifecycle/monitor owner. There is no retry or reconstruction.

Every accepted one-second controller sample is exactly
`{ordinal:P,elapsed_milliseconds:N,controller_rss_bytes:N,active_processes:N,
total_processes:N,total_terminated_processes:N,free_memory_bytes:N}`. Ordinals
are contiguous; elapsed time is at most `930000`; counts are unsigned DWORDs;
byte counters are unsigned 64-bit. The closeout vector must mechanically prove
its 931-sample maximum remains within the existing `262144`-byte reserve before
freeze. Quiescent stable-census detail remains validation-only except for the
existing process-ledger observations.

Lifetime Job accounting is frozen. A complete preflight failure has
`TotalProcesses` exactly `1`, `2`, or `3`; the launched baseline after worker,
two serial probes, and target is `4`; one legitimate target child yields PASS
`5`; a valid FAIL ends at `4|5`; and the active-cap denial vector ends at
`TotalProcesses=6` and `TotalTerminatedProcesses=1`. No other terminal total is
admissible. Terminal `ActiveProcesses` is exactly `0`. These accounting facts and
the configured `ActiveProcessLimit=3`/`JobMemoryLimit=1610612736` are authoritative;
per-process RSS never supplies a limit, custody predicate, or process event.

The controller `PeakPagefileUsage` and Job `PeakJobMemoryUsed` values read
exactly once within each accepted outer sample form a checked sum that updates the
provisional conservative owned-private-commit maximum. The first hard Job-
accounting, cadence, or arithmetic failure irreversibly sets resource status `INCOMPLETE`,
records the first stop, and immediately calls `TerminateJobObject`. API,
allocation, structure, range, or arithmetic failure records
`reason=query_failure`; a cadence/timestamp invariant failure records
`reason=cadence_failure`. A discarded observational process census is not such a
failure and never triggers a hard stop; inability to stabilize a required
quiescent boundary by its deadline follows that ledger's no-root path. On a hard
failure the sampler best-effort closes temporary handles and accepts no sample.
An incomplete API, census, identity, provider, cleanup, range, or arithmetic
result in preflight, the process ledger, or the resource ledger follows its
fail-closed no-root path; it adds no outer reason or code. A complete worker-local
resource threshold breach follows the resource-ledger partition below and may
perform only its bounded evidence-only failure finalization; it neither sets nor
substitutes for the controller's `first_resource_stop`. The first outer-controller
private-commit, hard Job-limit, or sampled-free-memory threshold breach records
`FAIL` when final closeout evidence can be completed, uses the corresponding
`private_commit_breach`, `job_limit_breach`, or `free_memory_breach` reason, and
immediately terminates the Job. After an outer-controller stop, no later worker
application, evidence, or root write is valid; the controller continues best-
effort containment sampling through observed exit or `attempt-D2`. If the mandatory
immediate pre-serialization controller peak query is the first failing/breaching
fact after worker exit and Job closure, it records `INCOMPLETE`/`FAIL`
respectively; no Job remains to terminate and no later worker act exists. After a
cadence/query failure, later best-effort observations are containment-only and do
not enter the accepted `samples` array.

At `attempt-D1` the controller records proof expiry and calls
`TerminateJobObject`; a termination request is not an exit observation. At
`attempt-D2` the watchdog self-terminates the controller unless valid closeout
acknowledgement already exists; no later user-mode assertion is admissible. For a terminal worker, the controller captures
the worker PID/start, unsigned-DWORD exit code from 0 through 4294967295, terminal
sample, and preliminary Job peak when available. A failed or null preliminary
Job-peak observation makes resources `INCOMPLETE` but does not replace or waive
the final resource query. It then closes the controller-owned worker
process/thread and every required non-Job attempt reference, including section,
timer, I/O, monitor, retained-DB, and temporary sampling references. Only after
that closure, with the controller-owned Job query handle plus controller
self/thread and mutex remaining, it polls
`JOBOBJECT_BASIC_ACCOUNTING_INFORMATION.ActiveProcesses` until zero. It then
performs one final `PeakJobMemoryUsed` resource query. A failed or null
preliminary or final value keeps resources `INCOMPLETE` without changing
independently established custody. When both values are nonnull, final must be at
least preliminary; violation also makes resources `INCOMPLETE`. Successful final
peak evidence is mandatory for resource `PASS|FAIL`. The controller then closes
the Job and every remaining required attempt handle. Immediately before closeout
serialization it queries controller `PeakPagefileUsage`; no earlier controller
peak may substitute, and failure is a resource fact rather than a custody
failure.

`CONTAINED` requires the complete closeout-eligibility boundary, atomic Job-list
creation before resume, descendant custody, physical worker exit, required non-Job
reference closure before the post-closure `ActiveProcesses==0` observation,
successful post-closure Job-zero observation, and Job plus remaining-handle
closure. `attempt_handles_closed` excludes only controller self/thread, the
teardown-held mutex, and the current closeout handle. Apart from that
post-closure Job-zero observation, no cadence sample, other process-count query,
controller RSS/peak query, Job-peak query, free-memory query, control-storage
query, or other resource query is a custody predicate. If any custody predicate
remains unproved at `attempt-D2`,
disposition is `BARRED_UNKNOWN` when a valid closeout can still be written;
otherwise the orphan bar remains.
Writable paths create-once write `attempt-closeout.json` with exactly:

```text
schema_id=layer3.b1b.attempt_closeout.v1; attempt_id:H; attempt_intent_sha256:H; profile:<sqlite_default|sqlite_authorized|postgresql_authorized>; invocation_name:T; candidate_head_sha:G; correction_full_sha256:H; controller:{pid:P,process_start_sha256:H}; worker:<null|{pid:P,process_start_sha256:H,exit_code:<N>}>; lane_parent_id:T; lane_parent_canonical_sha256:H; root_bindings_sha256:H; deadlines:{clock:"GetTickCount64",attempt_d0_tick_milliseconds:U64ZDEC,attempt_d1_tick_milliseconds:U64ZDEC,attempt_d2_tick_milliseconds:U64ZDEC,deadline_mapping_byte_length:4096,deadline_mapping_sha256:H,resume_succeeded:<boolean>,resume_previous_suspend_count:<N|null>}; worker_manifest:<null|{byte_length:P,sha256:H,status:<PASS|FAIL>}>; custody:{disposition:<CONTAINED|BARRED_UNKNOWN>,proof_deadline_reached:<boolean>,containment_deadline_reached:<boolean>,worker_exit_observed:<boolean>,job_zero_observed:<boolean>,worker_created_in_job:<boolean>,descendants_job_bound:<boolean>,attempt_handles_closed:<boolean>}; resources:{job:{active_process_limit:3,job_memory_limit_bytes:1610612736,limits_readback:true,total_processes:N,active_processes:0,total_terminated_processes:N},thresholds:{max_owned_private_commit_bytes:2147483648,min_free_memory_bytes:4294967296},samples:[...],sampling_complete:<boolean>,peak_accounting_complete:<boolean>,first_resource_stop:<null|{sample_ordinal:<P|null>,elapsed_milliseconds:N,reason:<query_failure|cadence_failure|private_commit_breach|job_limit_breach|free_memory_breach>}>,controller_peak_private_commit_bytes:<N|null>,preliminary_job_peak_memory_used_bytes:<N|null>,final_job_peak_memory_used_bytes:<N|null>,conservative_peak_owned_private_commit_bytes:<N|null>,observed_min_sampled_free_memory_bytes:<N|null>,threshold_breached:<boolean|null>,status:<PASS|FAIL|INCOMPLETE>}; control_storage:{expected_lane_volume_identity_sha256:H,observed_lane_volume_identity_sha256:H,min_volume_free_bytes:4294967296,attempt_intent_byte_length:P,attempt_intent_max_bytes:65536,attempt_intent_prewrite_free_bytes:N,attempt_closeout_prewrite_free_bytes:<N|null>,attempt_closeout_reserve_bytes:262144,status:<PASS|FAIL|INCOMPLETE>}; closed_at_utc:RFC3339Z
```

`proof_deadline_reached` is true exactly when the controller observes
`attempt-D1`. `containment_deadline_reached` is false in every valid closeout;
reaching `attempt-D2` without prior valid closeout acknowledgement self-terminates
the controller and permits no closeout. Successful resume facts imply the full
pre-resume guard and the sole resume occurred before `attempt-D1`; otherwise
`resume_previous_suspend_count` is null or the actual failed return count.

The closeout's intent digest hashes the exact complete reopened intent bytes; its
worker-manifest binding hashes the exact complete reopened manifest bytes.
Controller/worker identities equal the live handle-captured identities. For a
`test_terminal=true` root the worker equals process-ledger `runner`; for the sole
`preflight/false,test_terminal=false` root it instead equals
resource-ledger `preflight_only_job.runner`. The manifest binding equals the exact
reopened worker manifest. The correction, candidate head, lane parent, root
bindings, mapping, profile, invocation, and attempt values equal intent,
preflight, PASS-TO-LAUNCH where applicable, and worker evidence wherever those
records carry them. When preflight or a manifest exists, both control-storage
volume digests also equal the preflight evidence-volume identity. A null manifest
is permitted for custody closeout but cannot enter a profile verdict.

`first_resource_stop` is null exactly when no resource stop occurred; otherwise
it is immutable and records the earliest actual elapsed stop. If multiple reasons
are first observed at the same elapsed value, the one fixed precedence is
`query_failure`, `cadence_failure`, `private_commit_breach`, `job_limit_breach`, then
`free_memory_breach`. `sample_ordinal` is null for a query/cadence-invalid sample
and for a non-sample final-query stop; it is the associated accepted-sample
ordinal when an accepted threshold sample triggers the stop. No later observation
may replace or refine the selected reason or ordinal.
`sampling_complete` and `peak_accounting_complete` are true only when every
required cadence, preliminary and final peak query, range, and checked arithmetic
fact is complete. A null or failed preliminary or final Job peak, or a final
value below a nonnull preliminary value, therefore keeps resources `INCOMPLETE`
without changing independently established custody.
`conservative_peak_owned_private_commit_bytes` is the checked sum of immediate
pre-serialization controller `PeakPagefileUsage` and final Job
`PeakJobMemoryUsed`; it is a conservative private-commit fact, not RSS and not a
measurement of closeout serialization. `threshold_breached` is true exactly when
that sum exceeds `2147483648`, a configured hard Job limit acts, or sampled free
memory is below `4294967296`. Final Job accounting must also match the frozen
terminal matrix above; mismatch is structural, not an invented FAIL.

Resource `PASS` requires `CONTAINED`, complete sampling/peak accounting, no first
resource stop, and `threshold_breached=false`. Resource `FAIL` requires
`CONTAINED`, complete sampling/peak accounting, and
`threshold_breached=true`. Resource `INCOMPLETE` applies to `BARRED_UNKNOWN` or
any missing cadence/query/range/arithmetic fact; then `threshold_breached` is
exactly null. `CONTAINED+INCOMPLETE` is valid custody but cannot form a profile
root. Before freeze, Path 29 must mechanically reproduce the empty and exact
931-sample maximum closeouts and prove both remain within the existing `262144`
reserve; a larger vector blocks freeze.

Before any closeout namespace write, trusted lane handles must reproduce both
control-storage volume identities and prove them equal. Mismatch or unverifiable
identity forbids a namespace write and leaves the orphan bar. On the same verified
identity, the reopened intent length must be at most `65536` and its recorded
`attempt_intent_prewrite_free_bytes` must be at least
`4294967296 + attempt_intent_byte_length + 262144`; inequality invalidates the
control record. A complete closeout free-space fact makes control-storage `PASS`
exactly when `attempt_closeout_prewrite_free_bytes` is at least
`4294967296+262144`; below that threshold it is
`FAIL` and the controller may still write a complete closeout if physically
possible. An unavailable free-space fact on the same verified identity permits
only `INCOMPLETE`. No closeout self length/hash appears inside the closeout;
profile verdict v2 binds actual reopened bytes. These temporary lane query handles
close before serialization and are included in `attempt_handles_closed`; only the
current closeout handle is then excepted. Write/reopen failure leaves the orphan
bar.

Closeout uses intent's canonical create/flush/ReadOnly/no-follow-reopen
verification with no temp and must have actual byte length at most `262144`.
`attempt_closeout.sha256` is SHA-256 of those exact complete reopened bytes.
After reopen the controller produces no state and returns, letting OS teardown
release the mutex. Closeout is the terminal user-mode assertion; no recursive
supervisor, controller-exit artifact, or third process exists. Only a fresh
controller plus clean retained-lane census permits a later attempt; barred/torn/
inaccessible state remains barred despite an empty later PID census.

That final census is the process-creation cutoff. No probe, interpreter, helper,
or other process may start afterward; the one target child is the sole permitted
post-census process creation. For a launched authorized profile, the exact tail
is final census -> attestation and PASS-TO-LAUNCH creation/reopen -> control pipe/event
handle creation -> exactly one suspended target `CreateProcess` -> inherited
membership verification in the controller-owned Job -> OS-handle query and
binding of child PID/creation identity -> create-once, protect, rehash, and
validate `launch-claim.json` -> exactly one resume. `sqlite_default` creates no
attestation, PASS-TO-LAUNCH, or launch claim; after the same final census it
creates the control handles and suspended target, verifies inherited Job
membership, records that verified child identity only in the process ledger,
validates the direct command binding, and resumes once. Any missing Job
membership or other pre-resume failure returns nonzero without retry or closed
worker root; the controller then applies the durable closeout contract.

On normal Python-target exit before both deadlines, the worker requires the
target and every target descendant exited, closes its target/control/monitor/DB
handles, finalizes worker evidence, and exits. The sole complete, canonical,
predicate-backed `preflight/false,test_terminal=false` branch instead closes its
preflight handles and performs only the bounded FAIL finalization in Section 9.
Every structural, incomplete, or other pretarget worker stop closes every
worker-owned handle and exits nonzero under the existing no-root rules. An
outer-controller stop still forbids worker evidence/root finalization. The
worker never disarms or closes the controller timer or Job.
The controller alone converts the resulting observed physical worker exit into
`CONTAINED` only after every Section 8.1 `CONTAINED` predicate is proved. Any
unproved custody predicate follows `BARRED_UNKNOWN`/orphan rules. Resource or
control-storage `INCOMPLETE` alone does not alter otherwise-proved `CONTAINED`
custody.

Before every B1b write transaction, the production verifier independently opens
that path without following a reparse point, requires regular/read-only and
evidence-root containment, rehashes/parses the closed schema, and compares the
expected file hash, nonce, test-manifest hash, current UTC validity window,
profile/database/root identities, `PROJECT6_SOURCE_SHA`, candidate head, flag,
and every authority binding. A changed/expired/replayed/cross-profile/root/head
attestation, absent environment value, or unverifiable authority returns `503
connector_promotion_bridge_unavailable` before service lookup/mutation. The
worker invocation mutex and nonce bind one attestation to one Python target;
it cannot authorize a later invocation. Mechanically, the attestation binds
`launch_protocol=windows-suspended-single-child-v1`, `launch_claim_id`,
`expected_command_sha256`, and launch ordinal `1`. The worker uses Windows
`CreateProcess` suspended for exactly one manifest command. For every profile,
immediately before that launch it creates one anonymous control sample pipe whose
noninheritable read handle remains worker-owned and whose child handle is
write-only, plus one worker-owned auto-reset continuation event whose inheritable
child duplicate grants wait-only `SYNCHRONIZE` access. The exact
`STARTUPINFOEX` `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` contains only those two child
handles; the worker read/signal handles and every other worker handle are
noninheritable. The sole controller-to-worker inherited-handle exception is the
read-only 4096-byte deadline-section handle in Section 8.1; the worker closes it
before import, probe, target creation, thread creation, or state production, and
it never enters the target's handle list or environment. Controller Job, timer,
mutex, process, writable-section, I/O, and closeout handles never enter the
worker. Worker process/thread/I/O/retained-DB handles never enter the Python
target's list or environment. The two target control-handle raw process-local
decimal values appear only in the two
generic scrubbed control environment entries and never in a receipt, digest
preimage, manifest, ledger, test output, or log. This
channel adds no process, root, database identity, helper, evidence file, or
second plugin; the one bound `b1b_pytest` plugin is its sole child endpoint.

For launched authorized profiles, the worker then records the child's PID plus OS
process-creation time and create-once writes canonical
`launch-claim.json` under the evidence root with exactly `schema_id`,
`launch_claim_id`, `attestation_sha256`, `single_run_nonce`, `runner_pid`,
`runner_process_start_sha256`, `child_pid`, `child_process_start_sha256`,
`expected_command_sha256`, and `launch_ordinal=1`. It sets the claim ReadOnly,
reopens and rehashes it, revalidates every binding against the live suspended-
child handle, then resumes that child once. Failure before resume enters attempt
containment, creates no STOP/root, and attempts no second launch.
`sqlite_default` instead records the same child identity only in its process
ledger and resumes after direct preflight/control validation without any
attestation or launch claim.

`expected_command_sha256` is SHA-256 over the ASCII domain
`project6-b1b-command-v1`, one NUL byte, then the D33-canonical bytes of exactly
`{schema_id:"layer3.b1b.command.v1",profile,invocation_name,argv,
expected_skips,expected_deselections,cwd_id:"repo_root",
environment_allowlist_sha256,test_manifest_sha256}`. A process-start digest is
SHA-256 over ASCII `project6-b1b-process-start-v1`, NUL, the unsigned decimal
PID, NUL, and the unsigned decimal Windows process-creation FILETIME, with no
padding/newline; the responsible producer queries those facts from the OS handle
rather than wall-clock text. This one unchanged preimage defines the controller,
worker/runner, and Python-child process-start digests, including
`controller_process_start_sha256`, `runner_process_start_sha256`, and
`child_process_start_sha256`.

The claim locator is not caller-selected or ambient: the verifier derives the
fixed sibling basename `launch-claim.json` from the canonical parent directory
of `PROJECT6_B1B_ATTESTATION_PATH`, requires both files to be regular,
non-reparse, and in that same evidence root, then compares the attestation's
`launch_claim_id`, nonce, command hash, and attestation SHA-256 to the claim.
There is no separate claim-path environment variable.

Every production verifier call requires the worker's invocation mutex still held,
the outer controller's namespace mutex remains a separate custody control, the claim
and attestation mutually bound, and the current process PID/create-time hash to
equal the one claimed child. A copied file, released/reacquired lock, second
child, later process with a recycled PID, ordinal other than one, or second
resume/launch fails `503 connector_promotion_bridge_unavailable`. The runner
records one launch and one terminal child exit before releasing the mutex. Unit
tests prove same-child reuse within the one invocation succeeds while later-
child, sibling-child, recycled-PID, released-lock, altered-command, and copied-
attestation reuse fail.

Isolated verifier unit tests may inject only an inert adapter to prove call
ordering and each failure mode; they must never construct a production-valid
attestation or weaken the verifier. The authoritative integrated tests instead
use the production verifier and the runner-issued PASS-TO-LAUNCH file without
an adapter. Only an authorized runner invocation after the compound key may
produce that real file.

### 8.2 Exact routes and pre-body behavior

Freeze these new write routes for the corrected tranche:

- `POST /api/v1/layer3/source/connector/promotion/resolve`
- `POST /api/v1/layer3/handoff/connector-dataset/prepare`
- `POST /api/v1/layer3/handoff/connector-dataset/deliver`

All three Pydantic request models use `extra="forbid"`; no caller supplies a
receipt/intake/candidate/package ID, material or receipt identity/hash component,
storage/path/ref, review decision, row count, or materialization parameter. The
one exact exception is delivery's `expected_handoff_basis_hash`: it is only an
optimistic equality guard against the server-rederived final basis, cannot select
or create authority, and a mismatch fails before any file body is opened.

`promotion/resolve` accepts exactly:

```json
{"gate_b_session_id":"<uuid-string>"}
```

The server resolves that committed session's one eligible approved candidate,
I1, receipt, intake, original snapshot, and full winning basis. Its redacted
response is exactly:

```json
{"approval_hash":"<lowercase-64-hex>","canonical_identity_key_hash":"<lowercase-64-hex>","connector_promotion_receipt_id":"<uuid-string>","dataset_id":"<uuid-string>","dataset_version_id":"<uuid-string>","disposition":"materialized|reused","gate_b_session_id":"<uuid-string>","materialization_basis_hash":"<lowercase-64-hex>","materialization_record_hash":"<lowercase-64-hex>","promoted_session_id":"<uuid-string>","promotion_basis_hash":"<lowercase-64-hex>","row_count":2,"schema_id":"layer3.connector_promotion_resolve_response.v1","source_row_count":2,"variable_count":2}
```

The first successful call materializes once and returns `materialized`; an exact
repeat returns `reused` with identical IDs/hashes/counts and zero mutation. The
existing Gate-B response/OpenAPI model remains byte-current and contains no new
receipt mapping or field.

`connector-dataset/prepare` accepts exactly:

```json
{"promoted_session_id":"<uuid-string>"}
```

The server selects the receipt, approved result/package reviews, one exact
three-package set, reconciliation row, and canonical package; it never accepts a
caller selection. Its exact response is:

```text
{"approved_package_review_hash":"<lowercase-64-hex>","approved_result_review_hash":"<lowercase-64-hex>","canonical_internal_byte_length":<positive-integer>,"canonical_internal_output_package_id":"<uuid-string>","canonical_internal_payload_sha256":"<lowercase-64-hex>","connector_promotion_receipt_id":"<uuid-string>","eligibility_status":"eligible","handoff_basis_hash":"<lowercase-64-hex>","promoted_session_id":"<uuid-string>","schema_id":"layer3.connector_dataset_handoff_prepare_response.v1"}
```

`prepare_response_sha256` is the SHA-256 of exactly those D33-canonical body
bytes. The prepare-response serializer is its sole producer; the handoff
delivery receipt copies that hash as an alias and may not hash a response model,
headers, wrapper, or reconstructed projection instead.

It is pure validation/read and exact repeat returns byte-equivalent JSON.
`connector-dataset/deliver` accepts exactly:

```json
{"expected_handoff_basis_hash":"<lowercase-64-hex>","promoted_session_id":"<uuid-string>"}
```

It re-derives and compares the complete basis under the existing rollback/read-
lock posture, reopens the server-selected canonical row, validates containment,
length, and both hashes, reads the bounded canonical bytes into memory, and
returns a plain full-body `Response`; `FileResponse` and its range/automatic
file-metadata behavior are forbidden. Any `Range`, `If-Range`,
`If-Modified-Since`, or `If-None-Match` header returns the fixed closed
`400 b1b_handoff_full_body_required` error before the file is opened. The only B1b-specific
headers are `X-Project6-Handoff-Basis-SHA256` and
`X-Project6-Payload-SHA256`; `Content-Length` is exact, media type is
`application/json`, and the bounded download name is
`project6-b1b-canonical-internal.json`. No path/ref or trusted identity header is
returned; no `Accept-Ranges`, `ETag`, or `Last-Modified` header is emitted.

Precedence for each of these three new routes is exact: static pre-body trusted-
identity and operator-role authorization runs first; only an authorized operator
then reaches bridge flag/runner-attestation availability; only after that
precheck passes may request-body validation and service resolution run. Thus an
absent/untrusted/non-operator identity returns `401`/`403` without disclosing
bridge availability, while an authorized operator receives `503
connector_promotion_bridge_unavailable` when the flag or owner/packet/runner
preflight is unavailable. No service lookup or mutation occurs in either case.
Unknown/nonmatching sessions return `404
connector_promotion_session_not_found`; ineligible or incomplete authority
returns `409 connector_promotion_not_eligible`; D34 divergence uses `409
promotion_identity_decision_conflict`, changed promotion basis uses `409
connector_promotion_basis_conflict`, an unequal/second result-review decision
uses `409 connector_result_review_decision_conflict`, changed package-
construction basis uses `409 connector_package_basis_conflict`, an unequal/
second package-review decision uses `409
connector_package_review_decision_conflict`, and changed materialization basis
uses `409 connector_materialization_basis_conflict`. Malformed bodies remain
`422` only after authorization and the availability precheck. These domains do
not substitute for one another.

The default FastAPI `422` body is inadmissible because it echoes rejected
`input`. `backend/main.py` installs a path-scoped handler for the three new
routes and the four shared result/package routes. It activates only after the
pre-body middleware marks the request as an authorized operator and the B1b
flag plus process attestation precheck are valid; it returns the canonical
closed B1b error with `error_code=b1b_request_validation_failed`, fixed
`message="Request body failed validation."`, and `retryable=false`, with no
validation detail, input, exception, ID, path/ref, or secret. In the authorized
B1b process this deliberately redacts malformed ordinary requests on the four
shared paths; that narrow security behavior is an explicit exception to
authorized-process invalid-request parity. Flag-off/default ordinary behavior,
valid ordinary responses, and OpenAPI remain byte-current. All post-validation
B1b errors use the closed typed envelope from Section 5; every error has zero
mutation.

Error transport is therefore unambiguous by phase: pre-body identity/trust/role
rejection uses only the existing common auth envelope; an authorized new-route
availability failure, an authorized B1b-scoped `422`, and every selected B1b
service failure use only the closed `layer3.b1b_error.v1` envelope; an ordinary
shared-route request outside an authorized B1b process uses only its existing
generic workbench envelope. No phase may fall through to a second envelope or
include both forms.

Each route must be registered as `write` in the static pre-body route registry in `backend/main.py`. Update both of these exact test authorities:

- `backend/tests/test_pre_body_operator_authorization.py`
- `backend/tests/test_layer3_post_route_operator_authorization_coverage.py`

For every new route, tests must prove all of the following:

1. Malformed JSON plus absent operator identity yields `401` before request-body parsing can yield `422`.
2. Malformed JSON plus an untrusted proxy identity yields the expected `401` or `403` before `422`.
3. An authenticated auditor is rejected for the write route before body-driven mutation.
4. An authorized operator reaches normal request validation.
5. The static registry and the registered protected POST-route set remain exact in both directions: no protected POST is undeclared and no registry entry names a nonexistent route.
6. Malformed, wrong-type, missing, and forbidden-extra bodies containing sentinel
   credentials/references return the fixed redacted `422
   b1b_request_validation_failed`; the sentinel is absent from body, headers,
   logs, and evidence.
7. Deliver returns only full `200` bytes for an ordinary request and rejects
   Range/conditional variants with the fixed `400
   b1b_handoff_full_body_required`, no body fragment, no file metadata headers,
   and zero mutation.

The authorization middleware must not inspect, buffer, or partially parse the request body before identity and role rejection. There is no new public or read-only promotion route.

## 9. Recursive no-leak, redaction, and package fence

Comparison/determinism conditions in Sections 6 and 9, including comparison-run
ledgers, comparison objects, and comparison-run battery evidence, are
`sqlite_authorized` evidence only. `postgresql_authorized` remains an
authoritative migration, concurrency, and row/file checkpoint proof. It may
exercise the declared authoritative package row/file surfaces and carries the
profile-qualified zero/zero prospective package battery expected-census contract
defined below. After immutable package persistence, C2 cross-checks that contract
against locked actual state. That digest is not comparison evidence or a
replay/comparison source or gate. PostgreSQL executes no replay, produces or
consumes no replay outcome, receipt, comparison, or gate, and runs no
materializer/method sandboxes; both
census comparison fields remain null. No PostgreSQL authority or package gate
requires three-way evidence.

The B1b package projection is scoped from its first commit. This correction does
not authorize a global redaction-posture change. The generic workbench payloads
already contain raw `output_payload_ref`, artifact `storage_ref`, and payload-ref
arrays, so the additive extras hook is not an admissible B1b design.
Receipt-bound B1b construction takes a dedicated branch before any generic
raw-reference-bearing payload is built. Flag-off, noneligible, and ordinary
package bytes remain byte-current.

The exhaustive outer-package mapping is:

| Package kind | Exact top-level keys |
|---|---|
| `canonical_internal` | `package_header`, `b1_evidence_bundle`, `b1_evidence_bundle_index` |
| `review_facing` | `package_header`, `b1_evidence_bundle`, `b1_evidence_bundle_index`, `canonical_package_binding` |
| `user_facing` | `package_header`, `b1_public_disclosure`, `b1_evidence_bundle_index`, `canonical_package_binding` |

`package_header` is closed, not merely helper-compatible. Canonical has exactly
`schema_id`, `schema_version=1`, `package_key`,
`package_kind=canonical_internal`, `package_status=package_complete`,
`session_id`, and
`source_gate=50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE`; its schema ID is
`layer3.canonical_internal_package.v1`. Review and user have those seven keys
with their corresponding kind/schema ID plus exactly
`canonical_package_key=<canonical logical package key>`. Package keys use the
existing `l3:<session UUID>:<kind>` grammar. No generic authority, output,
artifact-inventory, reference, or construction-basis section is copied.
Canonical and review embed byte-equivalent bounded bundles and indexes; user
embeds no member body.

The reconciliation summary is exactly
`schema_id=layer3.b1b_reconciliation_summary.v1`,
`profile=receipt_bound_b1b`, `source_gate`, `promotion_receipt_id`,
`promoted_session_id`, `result_review_hash`,
`package_review_preview_hash`, `package_set`, `package_review_submit`,
`package_review_hash`, `connector_dataset_handoff_basis`, and
`connector_dataset_handoff_basis_hash`. `package_set` contains exactly
`construction_basis_hash`, `member_count=9`, `bundle_index_order_hash`,
`package_manifest_sha256`, `package_rehash_sha256`, and `packages`. `packages`
equals the construction-basis `packages` array byte-for-byte after D33
canonicalization: exactly three canonical/user/review objects, each containing
only `package_kind`, `output_package_id`, `payload_bytes`, and `payload_sha256`.
All four post-review values are null at package commit.
Every completed review atomically sets only `package_review_submit` and
`package_review_hash`; only approved also atomically sets the two handoff-basis
values. Each output-package summary is exactly
`schema_id=layer3.b1b_output_package_summary.v1`,
`profile=receipt_bound_b1b`, `package_kind`, `member_count` (9 for canonical
and review, 0 for user), `bundle_index_order_hash`,
`package_manifest_sha256`, `package_rehash_sha256`, and
`canonical_binding_present` (false for
canonical, true for review/user). Their internal database `payload_ref` remains
server-private and is never serialized into a package, summary, response,
header, or receipt.

`b1_evidence_bundle` uses the following schema notation; angle-bracket values
and the single displayed array entry are metavariables, not literal output. The
actual array has exactly nine complete entries:

```text
{"schema_id":"layer3.b1b_evidence_bundle.v1","member_count":9,"members":[<nine {"logical_path":"<frozen-name>","content":<closed-member-object>} entries>]}
```

The array follows frozen ordinal order. Canonicalizing each `content` object
alone reproduces its index length and SHA-256. Every complete index entry is:

```text
{"logical_path":"<frozen-name>","ordinal":<1-through-9>,"media_type":"application/json","encoding":"utf-8","bom":false,"terminal_newline":false,"byte_length":<positive-integer>,"sha256":"<64-lowercase-hex>"}
```

`b1_evidence_bundle_index` uses the same notation and contains nine entries:

```text
{"schema_id":"layer3.b1b_evidence_bundle_index.v1","member_count":9,"members":[<nine-complete-index-entries>],"package_order_hash":"<64-lowercase-hex>"}
```

The index serializer is the sole producer of
`bundle_index_order_hash`: that name is an exact alias of
`b1_evidence_bundle_index.package_order_hash`, whose only preimage is the
D33-canonical JSON array of all nine complete index-entry objects in frozen
ordinal order. `package_manifest_sha256` is the SHA-256 of the exact canonical
member bytes of `package-manifest.json` and equals the complete-index ordinal-5
entry's `sha256`; `package_rehash_sha256` is equivalently the exact canonical
member-byte SHA-256 and complete-index ordinal-6 `sha256` for
`package-rehash.json`. No summary, construction-basis builder, canonical binding,
or assertion recomputes or renames those three values: each copies the sole
producer's bytes exactly. These are alias closures only and do not change the
normative construction-basis preimage or golden vector.

`canonical_package_binding`, present only in review and user, is exactly:

```text
{"schema_id":"layer3.b1b_canonical_package_binding.v1","canonical_package_key":"<logical-package-key>","canonical_payload_bytes":<positive-integer>,"canonical_payload_sha256":"<64-lowercase-hex>","package_manifest_sha256":"<64-lowercase-hex>","package_rehash_sha256":"<64-lowercase-hex>","bundle_index_order_hash":"<64-lowercase-hex>"}
```

The canonical package never hashes itself. User-only `b1_public_disclosure` has
exactly `schema_id=layer3.b1b_public_disclosure.v1`, `fixture_disclosure`,
`question`, `bounded_result`, and `limitations`. `fixture_disclosure` is exactly
`source_fixture_id=F07`, `proof_cell_id=C01`, `synthetic=true`, `byte_length=34`, the bound
`content_sha256`, `official_public_read_evidence=false`, and
`f20_status=NOT-ESTABLISHED`. `question` is exactly `question_id`, the frozen
Section 5 text, and `question_sha256`, computed over those UTF-8 text bytes alone
with no terminal newline. `bounded_result` is exactly `row_count=2`,
`column_count=2`, `class_counts={numeric:1,categorical:1,boolean:0,time:0}`,
`missing_cells=0`, `missing_fraction=0.0`, and ordered `columns` with these two
closed objects:

1. `{name:"site_id",inferred_class:"categorical",non_null_count:2,
   missing_count:0,missing_fraction:0.0,unsupported_nested_values:false,
   unique_count:2,top_values:[{value:"SB-001",count:1},{value:"SB-002",count:1}]}`;
2. `{name:"value",inferred_class:"numeric",non_null_count:2,
   missing_count:0,missing_fraction:0.0,unsupported_nested_values:false,
   numeric_summary:{non_null_count:2,min:42.0,max:43.0,mean:42.5,
   median:42.5,std_dev:0.7071067811865476},
   top_values:[{value:42,count:1},{value:43,count:1}]}`.

These are a key-preserving bounded projection of the current
`_column_summary` result: categorical alone emits `unique_count`; numeric emits
`numeric_summary.non_null_count` and the key `std_dev`, whose implementation is
the sample standard deviation with `ddof=1`. No `sample_stddev` alias or numeric
`unique_count` is added. Both classes emit `top_values` in current source.

`limitations` is the exact ordered Section 11 limitation array defined below.
It contains no lineage body or reference.

Apply one structural recursive no-leak assertion to every mapping key and value
and every list/tuple element across all three packages, all member bodies,
reviewer evidence/trace, receipt/materialization JSON, reconciliation/output
summaries, API bodies/errors, delivery headers, and external evidence records.
Mapping keys must be strings; values must be JSON null, boolean, integer, finite
float, string, mapping, or array. Bytes, nonfinite numbers, non-string keys,
arbitrary objects, and serializer coercion fail.

Normalize keys by Unicode NFKC, `casefold()`, mapping spaces/hyphens to `_`, and
collapsing repeated underscores. Exact forbidden normalized keys include
`authorization`, `proxy_authorization`, `cookie`, `set_cookie`, `password`,
`passwd`, `token`, `access_token`, `refresh_token`, `secret`, `api_key`,
`credential`, `credentials`, trusted-proxy identity-header names,
`storage_ref`, `raw_storage_ref`, `input_payload_ref`, `output_payload_ref`,
`payload_ref`, `source_reference`, `storage_path`, `file_path`, and `local_path`.
No substring-only rejection is permitted. A closed-schema key ending `_hash` or
`_sha256` is exempt only from the corresponding raw-reference rule, and its
value must be the schema-prescribed lowercase 64-hex digest. Thus
`storage_ref_hash` is allowed while `storage_ref` is not. Tests cover every
forbidden key, case/separator/NFKC evasions, allowed hash keys, and benign
status/nonclaim text to prove both evasion and false-positive behavior.

Every string is independently checked for a Windows drive absolute path,
UNC/device path, POSIX/container absolute path, `file:` URI,
repository/OneDrive/temp absolute location, normalized or percent-encoded
`.`/`..` traversal segments, credential-bearing URL, or sensitive URL query key.
The only logical member-path values are the nine frozen slash-free basenames;
logical package keys must pass their existing bounded key grammar. Reject the exact 34-byte
fixture text under CRLF or LF normalization, its base64 encoding, strings
containing the complete header and both records, and any second embedded raw
object. Also reject Basic/Bearer authorization syntax, Cookie/Set-Cookie header
syntax, and a match to any nonempty sensitive value actually resident in the app:
settings credentials/database URLs/absolute roots and the attestation path are
registered at startup; current request auth/cookie/trusted-identity values are
registered only for that request and then cleared. The raw owner key and other
runner-only preimages never enter the child and therefore cannot be registered.
The registry is comparison-only and never persisted/logged; tests use sentinel
secrets and prove leakage through benign keys such as `note` and `value`. Public ScienceBase
item IDs are bounded source identifiers. Values `42` and `43` may occur only in
the frozen question/result/disclosure fields.

The same comparison-only registry must separately load every nonempty
raw/storage/payload/artifact reference reachable from the locked B1b rows before
package construction: connector target/intake refs, both session-snapshot refs,
Dataset/DatasetVersion/provenance refs, pass input/output refs, analysis-artifact
refs, reconciliation refs, and all three package refs after staging. Compare
both original text and a bounded canonical form after NFKC, case folding where
Windows applies, backslash-to-slash conversion, percent decoding to a fixed
point of at most two passes, and dot-segment normalization. Any exact registered
reference, prefixed/suffixed embedding of one, or equivalent canonical form is
forbidden under every key, including benign keys such as `message`, `note`, or
`value`. For every registered sensitive/reference value of at least eight UTF-8
bytes, also register and reject its standard-base64 and URL-safe-base64 forms
with and without permitted padding, and compare a bounded two-pass percent-
decoded form for every value, not only paths. Reversible encodings never qualify
as redaction; only schema-prescribed one-way SHA-256 fields are allowed. Closed
field-specific value grammars remain mandatory; the registry is
defense in depth, not permission for undeclared strings. Tests inject
`connectors/raw/<id>.csv`, a DatasetVersion relative ref, and encoded/separator
variants through benign allowed keys and require failure, while the nine frozen
logical basenames and `application/json` remain allowed. Credential, cookie,
identity-header, and storage-ref base64/URL-safe/percent-encoded benign-key
evasions are mandatory tests.

The package fence is exact:

- Package kinds: exactly `canonical_internal`, `review_facing`, and `user_facing`.
- Logical evidence members: exactly:
  1. `dataset-lineage.json`
  2. `canonical-3c.json`
  3. `analysis-plan-pass.json`
  4. `result-review.json`
  5. `package-manifest.json`
  6. `package-rehash.json`
  7. `same-origin-handoff.json`
  8. `downstream-replay.json`
  9. `b1b-verdict.json`

The exact ordinal/schema/field contract is:

| Ordinal/member | Schema ID | Exact fields after `schema_id` |
|---|---|---|
| 1 `dataset-lineage.json` | `layer3.b1b_dataset_lineage.v1` | `authority_bindings`, `fixture`, `material_identity`, `capture_lineage`, `gate_b_lineage`, `promotion_receipt`, `materialization`, `dataset_lineage`, `nonclaims` |
| 2 `canonical-3c.json` | `layer3.b1b_canonical_3c.v1` | `promotion_receipt_id`, `promoted_session`, `material_snapshot`, `typing_record`, `analysis_unit`, `analysis_group`, `analysis_set`, `census` |
| 3 `analysis-plan-pass.json` | `layer3.b1b_analysis_plan_pass.v1` | `question`, `method_contract`, `analysis_plan`, `pass_run`, `analysis_run`, `assumption_checks`, `caveat`, `hash_links` |
| 4 `result-review.json` | `layer3.b1b_result_review.v1` | `connector_b1_evidence`, `bounded_result`, `result_artifact`, `result_review`, `package_review`, `limitations`, `hash_links` |
| 5 `package-manifest.json` | `layer3.b1b_package_manifest.v1` | `member_count`, `members`, `package_order_hash` |
| 6 `package-rehash.json` | `layer3.b1b_package_rehash.v1` | `member_count`, `members` |
| 7 `same-origin-handoff.json` | `layer3.b1b_same_origin_handoff.v1` | `eligibility_status`, `basis`, `expected_invariants`, `forbidden_substitutions` |
| 8 `downstream-replay.json` | `layer3.b1b_downstream_replay.v1` | `eligibility_status`, `basis_hashes`, `expected_seams`, `expected_zero_mutation` |
| 9 `b1b-verdict.json` | `layer3.b1b_package_verdict.v1` | `verdict`, `pending_operations`, `required_external_receipts`, `nonclaims` |

The table above is completed by this normative nested catalog. In this catalog,
`U` means a canonical lowercase hyphenated UUID string, `H` a lowercase 64-hex
SHA-256, `G` a lowercase 40-hex Git object ID, `T` a nonempty NFC-normalized
ASCII token of at most 160 characters with no slash, backslash, colon,
whitespace, or traversal segment, `N` a nonnegative JSON integer, and `P` a
positive JSON integer. `null` is allowed only where written. Every object has
exactly the named keys, every array has the stated order/cardinality, and every
literal/enum is exact.

`dataset-lineage.json` nested objects are:

- `authority_bindings` = `{packet_full_sha256:H,
  packet_canonical_sha256:H, correction_full_sha256:H,
  owner_decision_full_sha256:H, owner_decision_canonical_sha256:H,
  owner_bound_main_sha:G, implementation_head_sha:G,
  pass_to_launch_sha256:H}`.
  Mapping is exact: packet hashes come from `authority.packet`; correction hash
  comes from `authority.correction`; owner-decision hashes come from
  `authority.dispatch_owner_decision`; `owner_bound_main_sha` comes from
  `authority.owner_bound_main_sha` and equals
  `authority.correction.owner_bound_main_sha`; and `implementation_head_sha`
  comes from `authority.candidate_head_sha`. `pass_to_launch_sha256` is SHA-256
  of the exact reopened `pass-to-launch.json` file bytes and equals both the
  scrubbed-environment `PROJECT6_B1B_ATTESTATION_SHA256` value and
  `launch-claim.json.attestation_sha256`. No parsed-object hash, package-local
  derivation, worktree identity, or renamed authority field is valid.
- `fixture` = `{source_fixture_id:"F07",proof_cell_id:"C01",synthetic:true,byte_length:34,
  content_sha256:"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad",
  media_type:"text/csv",official_public_read_evidence:false,
  f20_status:"NOT-ESTABLISHED"}`.
- `material_identity` = `{source_family:
  "connector_produced_single_source",content_sha256:H,
  identity_metadata_hash:H,identity_metadata_hash_version:
  "layer3.connector_source_intake.identity_metadata.v1",
  canonical_identity_key_hash:H}`.
- `capture_lineage` = `{connector_run_id:U,connector_run_target_id:U,
  connector_source_intake_record_id:U}`.
- `gate_b_lineage` = `{session_id:U,selection_manifest_id:U,
  material_snapshot_id:U,decision_manifest_id:T,decision_manifest_hash:H,
  material_preview_hash:H}`.
- `promotion_receipt` = `{connector_promotion_receipt_id:U,
  receipt_schema_version:"layer3.connector_promotion_receipt.v1",
  approval_hash:H,promotion_basis_hash:H,
  materialization_status:"materialized",materialization_basis_hash:H}`.
- `materialization` = `{materialization_record_sha256:H,
  materialization_semantic_sha256:H,dataset_file_bytes:P,
  dataset_file_sha256:H,dataset_storage_ref_hash:H,source_row_count:2,
  row_count:2,dropped_row_count:0,column_count:2,variable_count:2}`.
- `dataset_lineage` = `{source_connector_id:U,dataset_id:U,
  dataset_version_id:U,dataset_version_content_sha256:H,
  dataset_source_provenance_id:U,
  variable_definition_ids:[U,U]}` in `site_id`,`value` ordinal order.
- `nonclaims` is the exact seven-string limitation array defined below.

`canonical-3c.json` nested objects are:

- `promoted_session` = `{session_id:U,status:"completed_with_warnings",snapshot_count:1}`.
- `material_snapshot` = `{material_snapshot_id:U,
  source_shape:"dataset_version",dataset_version_id:U,
  content_sha256:H}`.
- `typing_record` = `{typing_record_id:U,material_snapshot_id:U,
  candidate_modalities:["quantitative"],chosen_modality:"quantitative",
  confidence:1.0,overridden_by_operator:false}`.
- `analysis_unit` = `{analysis_unit_id:U,unit_kind:"atomic",
  analysis_modality:"quantitative",material_snapshot_ids:[U],
  typing_record_ids:[U],must_remain_intact:false,unit_hash:H}`.
- `analysis_group` = `{analysis_group_id:U,
  analysis_modality:"quantitative",group_basis:"singleton",
  analysis_unit_ids:[U],status:"formed"}`.
- `analysis_set` = `{analysis_set_id:U,set_type:"single_item",
  analysis_group_ids:[U],analysis_unit_ids:[U]}`.
- `census` = `{promoted_sessions:1,material_snapshots:1,typing_records:1,
  analysis_units:1,analysis_groups:1,analysis_sets:1}`.
  The top-level `promotion_receipt_id:U` and every repeated child ID must equal
  the corresponding member-1 value.

`analysis-plan-pass.json` nested objects are:

- `question` = `{question_id:"CT4B-C01-DESC-001",text:<exact Section 5
  single-line text>,question_sha256:H}` where the hash covers the UTF-8 text
  alone with no terminal newline.
- `method_contract` = `{method:"descriptive_summary",version:"1",
  parameters:{},contract_sha256:H,method_input_sha256:H}`.
- `analysis_plan` = `{analysis_plan_id:U,analysis_set_id:U,
  status:"approved",approved_by_operator:true,preview_id:T,preview_hash:H}`.
- `pass_run` = `{pass_run_id:U,analysis_plan_id:U,analysis_set_id:U,
  pass_type:"single_item",selected_method_name:"descriptive_summary",
  status:"completed_with_warnings",result_payload_sha256:H}`.
- `analysis_run` = `{analysis_run_id:U,pass_run_id:U,
  dataset_version_id:U,method:"descriptive_summary",status:"completed",
  result_payload_sha256:H}`.
- `assumption_checks` is exactly four objects in the Section 6 table order,
  each `{assumption_check_id:U,name:<exact>,method:<exact>,result:<exact>,
  severity:<exact>,notes:<exact>}`.
- `caveat` = `{caveat_note_id:U,type:"non_time_series_interpretation",
  severity:"medium",message:"Dataset does not declare a usable time column; descriptive summary is non-time-series only."}`.
- `hash_links` = `{question_sha256:H,method_contract_sha256:H,
  method_input_sha256:H,result_payload_sha256:H,
  analysis_artifact_sha256:H,materialization_semantic_sha256:H}`.

`result-review.json` nested objects are:

- `connector_b1_evidence` = `{promotion_receipt_id:U,promoted_session_id:U,
  dataset_id:U,dataset_version_id:U,gate_b_session_id:U,
  connector_source_intake_record_id:U,canonical_identity_key_hash:H,
  fixture_disclosure_sha256:H,
  promotion_basis_hash:H,materialization_basis_hash:H,
  materialization_semantic_sha256:H,transformation_contract_sha256:H,
  question_sha256:H,
  method_contract_sha256:H,method_input_sha256:H,analysis_run_id:U,
  result_payload_sha256:H,analysis_artifact_id:U,
  analysis_artifact_sha256:H,assumption_checks_sha256:H,caveat_sha256:H,
  limitations_sha256:H,battery_census_sha256:H,result_review_hash:H,
  package_review_preview_hash:H,assumption_check_count:4,caveat_count:1,
  expected_first_path_contract_sha256:H,replay_contract_sha256:H}`.
  `expected_first_path_contract_sha256` is exactly the digest of the complete
  Section 6 object; it is an expected-contract hash only and embeds no actual
  C2/final census or outcome. Actual census hashes exist only in external
  evidence.
- `bounded_result` is byte-equivalent to the user `bounded_result` object.
- `result_artifact` = `{analysis_artifact_id:U,
  artifact_type:"descriptive_summary_result",byte_length:P,sha256:H,
  result_payload_sha256:H}`.
- `result_review` is exactly the approved record in B1b-04 plus
  `review_record_ref:"b1b-result-review-<result_review_hash>"` and
  `result_review_hash:H`.
- `package_review` = `{schema_id:
  "layer3.b1b_package_review_expected.v1",review_state:
   "package_review_preview_ready",package_review_preview_hash:H,
  result_review_hash:H,candidate_package_kinds:
  ["canonical_internal","user_facing","review_facing"],
  expected_member_count:9,package_contract_schema_id:
  "layer3.b1b_package_contract.v1",correction_full_sha256:H}`. It contains no submit,
  approved-review, package payload, or handoff hash.
- `limitations` is the exact limitation array; `hash_links` =
  `{dataset_lineage_sha256:H,canonical_3c_sha256:H,
  analysis_plan_pass_sha256:H,result_review_hash:H,
  package_review_preview_hash:H}`.

The exact ordered limitation array used by member 1, member 4, member 9, and the
user disclosure is:

1. `Synthetic C01 fixture; not acquired from ScienceBase or USGS.`
2. `public_read_confirmed=true is synthetic test state only.`
3. `official_public_read_evidence=false.`
4. `F20 is NOT-ESTABLISHED.`
5. `The two-row sample is degenerate and non-temporal.`
6. `Only bounded deterministic repeatability of descriptive_summary on C01 is supported.`
7. `No official-data, source-availability, public-read, production, utility, causal, temporal, representativeness, or population-wide claim is supported.`

The remaining `connector_b1_evidence` digests are closed aliases, not opaque
claims. All use the D33 serializer over the named complete object or array:

- `fixture_disclosure_sha256` hashes the exact user
  `b1_public_disclosure.fixture_disclosure` object;
- `transformation_contract_sha256` equals
  `951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179`
  and equals the materialization-semantic transformation contract;
- `assumption_checks_sha256` hashes the exact ordered four-object
  `analysis-plan-pass.json.assumption_checks` array;
- `caveat_sha256` hashes the exact `analysis-plan-pass.json.caveat` object;
- `limitations_sha256` hashes the exact seven-string array above; and
- `battery_census_sha256` hashes exactly one fixed, prospective,
  profile-qualified expected-C2/count contract. For `sqlite_authorized`, the
  preimage is:

```json
{"analysis_artifact_count":1,"analysis_run_count":1,"assumption_check_count":4,"authoritative_application_file_count_at_c2":9,"authoritative_session_spine_count":2,"caveat_count":1,"dataset_count":1,"dataset_version_count":1,"materializer_comparison_run_count":3,"method_comparison_run_count":3,"output_package_count":3,"profile":"sqlite_authorized","promotion_receipt_count":1,"schema_id":"layer3.b1b_battery_expected_census.v1","variable_definition_count":2}
```

  For `postgresql_authorized`, the preimage is:

```json
{"analysis_artifact_count":1,"analysis_run_count":1,"assumption_check_count":4,"authoritative_application_file_count_at_c2":9,"authoritative_session_spine_count":2,"caveat_count":1,"dataset_count":1,"dataset_version_count":1,"materializer_comparison_run_count":0,"method_comparison_run_count":0,"output_package_count":3,"profile":"postgresql_authorized","promotion_receipt_count":1,"schema_id":"layer3.b1b_battery_expected_census.v1","variable_definition_count":2}
```

For `sqlite_authorized`, the review service is the sole producer of those six
digests from locked, server-derived objects after the authoritative result and
both comparison batteries pass, but before result-review or package construction.
For `postgresql_authorized`, it produces the prospective digest after the
authoritative result and after verifying that no sandbox/comparison run was
authorized or produced; the prospective contract prescribes both later census
comparison fields as null but does not observe those not-yet-created fields. It
does so before result-review or package construction. The corresponding
profile's package builder independently
re-derives the complete fixed object and digest before persistence; the
result-review member and applicable cross-member assertions consume only that
same-profile value. `sqlite_default` constructs no B1b package or expected census
and carries no `battery_census_sha256`. A missing/extra key, count, profile, or
digest, independent substitution, or cross-profile reuse fails before package
persistence.

The expected-census object predicts no actual C2 state, count, package success,
or verdict. After the three immutable package rows/files are persisted, the C2
census reopens `result-review.json`, independently re-derives the expected object,
and compares every actual locked C2 count to its named expected count. SQLite
also proves actual three/three comparison membership; PostgreSQL proves actual
zero/zero comparison absence and null comparison fields. Any actual/expected
inequality fails package/files/census gates. This post-package C2 step is the
sole actual null-field validation. The package and nested member are never
rewritten to reflect actual state. PostgreSQL's expected digest remains an
absence/state contract only, never comparison evidence or a comparison/replay
source or gate.

`replay_contract_sha256` is the D33-canonical SHA-256 of exactly this
pre-operation object; array order and every literal are normative:

```json
{"authoritative_same_request":{"changed_columns":[],"http_status":200,"new_files":0,"new_rows":0,"zero_mutation":true},"cross_run_same_i1":{"changed_columns":["dataset_id","dataset_version_id","updated_at"],"excluded_from_authoritative_c0_c3":true,"http_status":200,"new_files":0,"new_rows":0},"divergent_d34":{"changed_columns":[],"error_code":"promotion_identity_decision_conflict","excluded_from_authoritative_c0_c3":true,"http_status":409,"new_files":0,"new_rows":0},"schema_id":"layer3.b1b_replay_contract.v1","seam_order":["same_request_exact_replay","cross_run_same_i1_reuse","divergent_d34_conflict"]}
```

For each authorized profile, the review service is the sole producer of that
digest from this fixed contract before package construction, and that profile's
package builder independently re-derives it from the same literal object. For
`sqlite_authorized`, `connector_b1_evidence`, `downstream-replay.json`, and the
replay receipt/verdict comparisons consume the same-profile value;
`downstream-replay.json` must equal its three named seam projections exactly.
For `postgresql_authorized`, `connector_b1_evidence.replay_contract_sha256` is
only the fixed pre-operation expected-contract alias needed by the closed package
member. It is never replay evidence, an actual-outcome receipt, a row/file-census
comparison source, or an invocation/integrated/aggregate gate, and PostgreSQL
creates no replay artifact. `sqlite_default` creates no package or replay-contract
field. Even though the fixed contract bytes are profile-independent, a stored
value must be produced and re-derived inside its own authorized profile; a value
copied from another profile is forbidden. The digest is never computed from
actual outcomes. Any schema, ordering, literal, code, projection, producer, or
digest difference fails closed, while actual outcomes remain external evidence.

The remaining members are closed as follows:

- `package-manifest.json.members` has exactly eight complete index entries for
  ordinals 1-4 and 6-9; `member_count=8`. `package-rehash.json.members` has
  exactly seven `{logical_path:T,sha256:H}` entries for ordinals 1-4 and 7-9;
  `member_count=7`. Their order/hash rules remain those below.
- `same-origin-handoff.json` has
  `eligibility_status="pending_approved_package_review"`; `basis` =
  `{promotion_receipt_id:U,promoted_session_id:U,result_review_hash:H,
  package_review_preview_hash:H,required_handoff_basis_schema:
  "layer3.connector_dataset_handoff_basis.v1"}`;
  `expected_invariants` is exactly
  `["one_receipt","one_three_package_set","canonical_bytes_rehashed","approved_reviews_required","prepare_and_deliver_zero_mutation"]`;
  `forbidden_substitutions` is exactly
  `["aps_package","mixed_session","caller_selected_package","payload_reference","predicted_review_outcome"]`.
- `downstream-replay.json` has `eligibility_status="not_yet_executed"`;
  `basis_hashes` = `{canonical_identity_key_hash:H,approval_hash:H,
  promotion_basis_hash:H,materialization_basis_hash:H,
  result_review_hash:H,package_review_preview_hash:H}`;
  `expected_seams` is exactly
  `["same_request_exact_replay","cross_run_same_i1_reuse","divergent_d34_conflict"]`;
  `expected_zero_mutation` is exactly
  `{same_request:true,cross_run_new_rows:0,cross_run_new_files:0,
  cross_run_changed_columns:["dataset_id","dataset_version_id","updated_at"],
  divergent:true}`.
- `b1b-verdict.json` has `verdict="PACKAGE-ELIGIBLE-NOT-FINAL"`;
  `pending_operations` exactly
  `["package_persistence","package_review_submit","package_rehash","handoff_prepare","handoff_deliver","downstream_replay","final_census"]`;
  `required_external_receipts` exactly
  `["package-postclose-rehash.json","handoff-delivery-receipt.json","downstream-replay-receipt.json","b1b-integrated-run-verdict.json"]`;
  `nonclaims` is the exact limitation array.

Every member and named nested object is nonempty and closed: undeclared fields,
empty required objects/arrays, alternate schema IDs, caller-supplied values, and
implicit string coercion fail before persistence. Row projections carry only
their exact persisted ID, type/status/count fields and content/basis hashes;
timestamps are omitted except where a named immutable event timestamp belongs
to the closed schema. `connector_b1_evidence` binds the C01 synthetic disclosure,
frozen question, method ID/version/parameters/contract hash, transformation and
method-input hashes, analysis-run/result/artifact IDs and hashes, exactly four
named checks, the one named caveat, every Section 11 limitation, connector/
intake/Gate-B/receipt/promoted-session/Dataset/DatasetVersion IDs and basis
hashes, the exact prospective battery expected census, and both exact pre-
operation contracts through the explicit fields and equality rules above. It may
contain no raw object, value outside the bounded question/result, or request-
derived widening.

Cross-member assertions require equality of receipt, Gate-B, promoted-session,
snapshot, Dataset, and DatasetVersion identities; all D33, approval, promotion,
materialization, transform, method-input, result, artifact, result-review, and
package-review-preview hashes; the expected handoff identities; question/method
contract; four-check/one-caveat census; manifest,
rehash, and index hashes/order; canonical/review bundle bytes; and review/user
canonical binding against the actual closed canonical bytes. Specifically,
every `bundle_index_order_hash` equals the sole nine-entry index order hash,
every `package_manifest_sha256` equals complete-index ordinal 5 `sha256`, and
every `package_rehash_sha256` equals ordinal 6 `sha256`, including construction
basis, reconciliation package set, output summaries, and canonical bindings.

- No undeclared package kind or logical member is permitted.
- Every member is canonical JSON with media type `application/json`, UTF-8,
  no BOM, and no terminal newline. Each ordered entry carries logical path,
  ordinal, media type, encoding, BOM policy, newline policy, canonical byte
  length, and lowercase SHA-256.
- Construction order is acyclic and distinct from the frozen logical ordinals:
  first build the seven members other than `package-manifest.json` and
  `package-rehash.json`; then build `package-rehash.json`; then
  `package-manifest.json`; then the non-member index; then the outer packages.
- `package-rehash.json` lists hashes only for the seven first-built members. It
  explicitly excludes itself, `package-manifest.json`, the non-member index,
  and every outer package, and contains no final outer-package hash.
- Its exact content after `schema_id` is `member_count=7` plus seven
  `{logical_path,sha256}` entries in frozen ordinal order.
- `package-manifest.json` lists exactly the other eight logical members in frozen
  ordinal order with all entry fields above. It does not list or hash itself.
  Its `package_order_hash` is SHA-256 over the D33-canonical JSON array of those
  eight complete entry objects in ordinal order, with no terminal newline.
- Its `member_count` is exactly `8`; the non-member index has exactly `9`.
- A top-level `b1_evidence_bundle_index` object, which is not itself a logical
  member, lists all nine members in frozen ordinal order with the same complete
  entry fields. Its `package_order_hash` is computed by the same rule over the
  nine-entry array. It never lists or hashes itself or any outer package.
- `same-origin-handoff.json` and `downstream-replay.json` contain only immutable
  pre-operation basis, expected invariants, and eligibility; they do not claim
  that handoff or replay has happened.
- Embedded `b1b-verdict.json` is explicitly
  `PACKAGE-ELIGIBLE-NOT-FINAL`, never PASS. It precedes persistence, rehash,
  handoff, replay, and final census.
- Persist exactly three package rows and one reconciliation row.
- Persist exactly three outer package files and zero logical-member sidecars.
- Both post-close hashes of each package must equal its database `payload_hash`.
- Delivery returns only the exact `canonical_internal` bytes.

After immutable package persistence, write exactly these four redacted receipts
under the lane-unique isolated evidence root, outside the package and application
storage trees:

1. `package-postclose-rehash.json` — two independent reopen/read hashes for each
   of the three package files and equality with each persisted `payload_hash`;
2. `handoff-delivery-receipt.json` — prepare eligibility, delivered byte length
   and hash, and exact equality with `canonical_internal`, with no raw path;
3. `downstream-replay-receipt.json` — actual seam-specific replay outcomes and
   zero-mutation census;
4. `b1b-integrated-run-verdict.json` — this SQLite integrated run's PASS/FAIL
   only after every preceding receipt, fixture recheck, row/file census, and
   run-local gate has completed. It is not the cross-profile/final program
   verdict.

These receipts are external proof, not logical package members, application
artifacts, handoff files, or new durable product rows. Their basenames, order,
canonical bytes, lengths, and hashes are recorded in closeout. This two-phase
contract is acyclic: no immutable package claims an event that consumes that
package, and no package or member hashes itself.

The four list entries above are only the human-readable purpose summary. Their
normative closed schemas use the Section 9 `U`/`H`/`N`/`P` types and are:

1. `package-postclose-rehash.json` has exactly `schema_id=
   layer3.b1b.package_postclose_rehash.v1`, `packages`, and
   `package_set_sha256`. `packages` contains exactly three ordered objects
   (canonical,user,review), each `{package_kind:<exact>,output_package_id:U,
   payload_bytes:P,persisted_sha256:H,reopen_1_sha256:H,reopen_2_sha256:H,
   persisted_equals_reopen_1:true,reopen_1_equals_reopen_2:true}`.
   `package_set_sha256` hashes that canonical array. Reopen 1 occurs before
   approved package-review submit; reopen 2 occurs after it.
2. `handoff-delivery-receipt.json` has exactly `schema_id=
   layer3.b1b.handoff_delivery_receipt.v1`, `promotion_receipt_id:U`,
   `promoted_session_id:U`, `handoff_basis_hash:H`,
   `canonical_expected_bytes:P`, `canonical_expected_sha256:H`,
   `prepare_response_sha256:H`, `prepare_status="eligible"`,
   `delivered_bytes:P`, `delivered_sha256:H`, `bytes_equal:true`,
   `hashes_equal:true`, `c2_state_census_sha256:H`,
   `post_handoff_state_census_sha256:H`, and `handoff_zero_mutation:true`. This
   immediate receipt does not name or predict C3.
3. `downstream-replay-receipt.json` has exactly `schema_id=
   layer3.b1b.downstream_replay_receipt.v1`, `same_request`,
   `cross_run_sandbox`, `divergent_sandbox`,
   `authoritative_pre_replay_state_census_sha256:H`, and
   `authoritative_post_replay_state_census_sha256:H`. `same_request` is exactly
   `{disposition:"exact_replay",http_status:200,promotion_receipt_id:U,
   dataset_id:U,dataset_version_id:U,new_rows:0,new_files:0,
   changed_columns:[]}` and is the only replay executed between authoritative
   C2 and C3. `cross_run_sandbox` has exactly `sandbox_id:P`,
   `sandbox_namespaces_sha256:H`, `baseline`, `local_c0`, `post_decision`,
   `excluded_from_authoritative_c0_c3:true`, and `result`. Its namespace hash is
   the exact `replay_cross_run` object from Section 6 with the same `sandbox_id`.
   Each of those three census fields is an inline wrapper exactly
   `{sha256:H,census:<closed body>}`. The body has exactly
   `schema_id=layer3.b1b.replay_sandbox_census.v1`, `sandbox_id`, `checkpoint`,
   `sandbox_namespaces_sha256`, `database_identity_sha256`, `tables`,
   `application_files`, and `evidence_root_excluded=true`. `checkpoint` is
   respectively `baseline`, `local_c0`, or `post_decision`; `sandbox_id` and
   `sandbox_namespaces_sha256` equal their enclosing values. Its DB identity is
   the exact role-bound sandbox SQLite identity from Section 6.
   `tables` contains all 28 Section 9 table entries in declared order, each
   exactly `{table,row_count,rowset_sha256}`. `application_files` contains all
   and only present files ordered by the Section 9 logical-class rank, each
   exactly `{logical_class,byte_length,sha256}`.

   Wrapper `sha256` covers only the exact D33-canonical census body bytes. The
   measured canonical byte length used by evidence/resource accounting covers
   those same body bytes and is not an extra wrapper field. The replay runner is
   sole producer: it captures `baseline` before sandbox-local work, `local_c0`
   after local capture and before the decision, and `post_decision` after the
   committed result and stable reread. It serializes each once and persists all
   three complete wrappers inline inside the replay receipt in that order.
   Its `result` is exactly
   `{disposition:"same_i1_reuse",http_status:200,promotion_receipt_id:U,
   dataset_id:U,dataset_version_id:U,new_rows:0,new_files:0,
   changed_columns:["dataset_id","dataset_version_id","updated_at"]}`.
   `divergent_sandbox` has the same seven keys and wrapper rules, using exact
   `replay_divergent` namespaces and its own positive `sandbox_id`; its
   `result` is exactly `{disposition:"d34_conflict",http_status:409,
   error_code:"promotion_identity_decision_conflict",
   promotion_receipt_id:null,dataset_id:null,dataset_version_id:null,
   new_rows:0,new_files:0,changed_columns:[]}`. Comparisons consume each complete
   wrapper, verify body/hash/timing/order, and never accept an opaque hash or
   body-only substitute. Neither sandbox wrapper can equal or substitute for an
   authoritative C0-C3 census. PostgreSQL has no replay receipt, sandbox census,
   or replay-comparison source.
4. The evidence dependency graph is one-way and acyclic. Durable intent precedes
   the transient deadline mapping, which binds intent and live controller/worker
   identities without becoming durable evidence. Worker preflight consumes those
   bindings; primitive evidence records are then produced. The SQLite integrated
   verdict consumes only primitive evidence; it never consumes an invocation
   verdict or a manifest.
   The invocation verdict then consumes primitive evidence plus, for
   `sqlite_authorized`, that integrated verdict through the separate
   `integrated_consistency` gate. The worker evidence manifest consumes the
   completed invocation verdict and preceding immutable worker members. The
   controller closeout then
   binds the durable intent, mapping, worker identity, optional
   worker manifest, custody, and controller-observed resources. Profile
   aggregation consumes only a verified intent/worker-manifest/closeout attempt
   binding; upper aggregation consumes only a v2 profile verdict or declared
   aggregate record. No node consumes itself or any downstream node, and no
   closeout, profile verdict, or upper aggregate feeds back into a worker
   invocation or integrated gate.

   `b1b-integrated-run-verdict.json` is created only for
   `sqlite_authorized/final/test_terminal=true`, after the three outcome
   receipts, row/file census, test result, and every other primitive dependency
   are present. It has exactly `schema_id=layer3.b1b.integrated_run_verdict.v1`,
   `candidate_head_sha`, `profile`, `invocation_name`, `verdict`,
   `outcome_receipts`, `control_evidence`, `fixture`, `census`, `gate_results`,
   `standing`, and `nonclaims`. `profile` is `sqlite_authorized` and
   `invocation_name` is `sqlite-authoritative-b1b`. `outcome_receipts` contains
   manifest ordinals 7-9 (package rehash, handoff, replay). `control_evidence`
   contains ordinals 1-6 and 10-11 (preflight, PASS-TO-LAUNCH, launch claim,
   process, resource, endpoint, row/file census, test result). Every binding is
   exactly `{basename:<frozen basename>,ordinal:P,byte_length:P,sha256:H}`.
   `fixture` is exactly `{byte_length:34,content_sha256:<F07 hash>,
   reverified:true}`. `census` is exactly
   `{c2_state_sha256:H,c3_state_sha256:H,c2_equals_c3:true}` and both hashes are
   the authoritative aliases defined below, never the row/file-census file hash.

   `gate_results` always has the exact twenty primitive gates, in order:
   `authority`, `environment`, `roots`, `launch`, `processes`, `endpoints`,
   `fixture`, `census`, `rows`, `files`, `sqlite_concurrency`,
   `materializer_three_way`, `method_three_way`, `package_transaction`,
   `no_leak`, `reviews`, `handoff`, `replay`, `resources`, `tests`. Every entry
   is `{gate:<exact>,status:<PASS|FAIL>}`; `NOT-RUN` is forbidden because this
   file is not created until every primitive dependency is present. Each gate
   uses the exact same primitive source/predicate as the SQLite invocation gate
   map below. The set exhaustively covers authority, environment, parent/child
   roots, launch, processes, endpoints, fixture, the applicable row/file
   comparison set, SQLite concurrency, materializer and method three-way
   checks, package transaction, Gate-B/materialization/package orphan and
   no-leak checks, review/summary fence, handoff, replay, resources, and tests.
   PASS requires all twenty PASS. FAIL records every independently evaluated
   FAIL; it is not a first-failure prefix.

   PASS `standing` is exactly
   `B1A-PASS; B1B-WORKER-EVIDENCE-PASS; CONTROLLER-CLOSEOUT-PENDING; CROSS-PROFILE-AGGREGATION-PENDING; INTEGRATED-LOOP-NOT-YET-FINAL; SCHEMA-CHANGED-AS-AUTHORIZED.`
   FAIL `standing` is exactly
   `B1A-PASS; B1B-WORKER-EVIDENCE-FAIL; CONTROLLER-CLOSEOUT-PENDING; CROSS-PROFILE-AGGREGATION-NOT-STARTED; INTEGRATED-LOOP-NOT-PROVEN; SCHEMA-CHANGED-AS-AUTHORIZED.`
   For either verdict, `nonclaims` is the seven-string Section 9 package/data
   limitation array followed by the five exact Section 15 custody nonclaims, in
   that order. An earlier failure creates no integrated verdict.

   Every bound status-bearing primitive record must carry explicit `status=PASS`
   before an integrated or invocation PASS is valid. This includes preflight,
   resource, endpoint, census, test, and PostgreSQL proof records. The process
   ledger is statusless PASS-only. Statusless PASS-TO-LAUNCH, launch-claim,
   process-ledger, package-rehash, handoff, and replay records instead require the
   complete closed schema and every invariant declared for that record. Absence,
   an invalid status value, a non-PASS status where one exists, a missing field,
   an extra field, or an invariant mismatch fails the consuming gate. A worker evidence manifest's status
   exactly aliases its bound invocation verdict status; profile and upper
   manifests exactly alias their bound record status.

The control files named by those bindings are closed too; an executor may not
invent a looser ledger:

- `preflight.json` has exactly
  `schema_id=layer3.b1b.preflight.v1`, `profile`, `invocation_name`,
  `candidate_head_sha`, `authority_sha256`, `correction_full_sha256`, `attempt`,
  `fixture`, `environment`, `roots`, `resources`, `process_census`, `endpoint_policy`,
  `postgresql_storage_binding`, `test_manifest_sha256`, and
  `status=PASS|FAIL`. `attempt` is exactly
  `{attempt_id:H,attempt_intent_byte_length:P,attempt_intent_sha256:H,
  controller_process_start_sha256:H,deadline_mapping_sha256:H}`. `fixture` is exactly
  `{source_fixture_id:"F07",proof_cell_id:"C01",byte_length:34,
  content_sha256:<F07 H>,regular_file:true,read_only:true,reparse_point:false,
  canonical_path_namespace_sha256:H,reverified:<boolean>}`. `environment` is
  exactly `{python_runtime_sha256:H,release_lock_full_sha256:H,
  proof_lock_full_sha256:H,environment_inventory_sha256:H,
  distribution_record_inventory_sha256:H,pip_check_output_sha256:H}`.
  `roots` is exactly `{lane_parent_id:T,lane_parent_canonical_sha256:H,
  runtime_root_id:T,runtime_root_canonical_sha256:H,storage_root_id:T,
  storage_root_canonical_sha256:H,database_root_id:T,
  database_root_canonical_sha256:H,evidence_root_id:T,
  evidence_root_canonical_sha256:H,root_bindings_sha256:H,
  database_identity_sha256:H,all_absent_before_create:<boolean>,
  direct_children:<boolean>,pairwise_disjoint_nonancestor:<boolean>,
  no_reparse:<boolean>}`. `resources` is
  exactly `{free_memory_bytes:<nonnegative-integer>,runtime_volume_free_bytes:
  <nonnegative-integer>,runtime_volume_identity_sha256:H,
  database_volume_free_bytes:<nonnegative-integer>,
  database_volume_identity_sha256:H,storage_volume_free_bytes:
  <nonnegative-integer>,storage_volume_identity_sha256:H,
  evidence_volume_free_bytes:<nonnegative-integer>,
  evidence_volume_identity_sha256:H,heavy_process_count:<nonnegative-integer>}`.
  `process_census` is exactly
  `{matching_process_count:<nonnegative-integer>,census_sha256:H}` and
  `endpoint_policy` is exactly `{external_budget:0,policy_sha256:H}`.
  `postgresql_storage_binding` is null for either SQLite profile and is the exact
  complete Section 8 `layer3.b1b.postgresql_storage_binding.v1` object for
  PostgreSQL. Its D33-canonical SHA-256 equals the same-named runtime scalar in
  the launched-authorized PASS-TO-LAUNCH record when present and every later
  PostgreSQL storage-binding hash; SQLite has no nonnull storage-binding hash.

  Every `attempt` value is direct worker evidence from the exact reopened intent,
  live controller handle, and validated 4096-byte deadline mapping. It equals the
  same attempt, byte length, intent hash, controller-start digest, and mapping hash
  carried or implied by closeout. Profile, invocation, candidate head, correction,
  lane parent, and root bindings equal the durable intent. For a launched
  authorized profile, those root values also equal reopened PASS-TO-LAUNCH runtime
  values; the intent roots, preflight roots, and pass-to-launch roots are one exact
  equality set, never independently selected aliases.

  `preflight.resources` remains the closed launch-time free-space, free-memory,
  and competing-process projection; no duplicate size fields are added. Its four
  volume free-byte values plus free memory exactly equal the `preflight` boundary
  observation in the resource ledger. That observation has
  `current_evidence_bytes=0` and `projected_next_write_bytes=0`; its actual
  `bounded_bytes` must be at most `1073741824`. `free_memory_bytes` is exact
  `GlobalMemoryStatusEx(...).ullAvailPhys` under the Section 8.1 native rule.
  `heavy_process_count` equals the separate competing-process census count, never
  either owned Job census, and
  PASS requires the declared minima, zero heavy processes, and that observation's
  exact `bounded_bytes <= 1073741824`. That literal is the universal frozen
  Section 16 cap. A launched authorized profile additionally requires it to equal
  the reopened `pass-to-launch.runtime.max_profile_bounded_bytes`; a default or
  authorized preflight-only profile never creates, opens, hashes, dereferences,
  or passes a PASS-TO-LAUNCH record to child launch.
  PostgreSQL `database_volume_identity_sha256` and
  `database_volume_free_bytes` come from the storage binding's actual engine
  volume, not the empty local database child; SQLite uses the bound database-
  child volume. Each identity equals its adjacent preflight-boundary resource
  observation. Evidence free space and identity always come from the verified
  evidence-child volume, even when that volume aliases another fixed local
  volume; equality never permits omission of the evidence fields.
  PostgreSQL obtains the preflight DB size through the already required identity
  connection and same read-only identity transaction. The runner retains that
  read-only host connection. On a launched path it retains that connection
  through child startup solely for the `monitor_ready` identity comparison; the
  pre-ready one-second cadence performs no PostgreSQL query, and it is not the
  child monitor connection. After validating the child's
  `monitor_ready` database, endpoint, and storage-binding identities and
  independently validating both point-in-time size observations, the
  runner closes the host connection before it signals the continuation event. On
  the sole preflight-only failure path, no child starts: the terminal resource
  observation reuses that already verified read-only host connection for its one
  fresh point-in-time size read, then closes it before any evidence
  file is written. Host/child or cross-time size equality is never required.

  All profiles derive the closed authority object, correction/fixture bindings,
  environment and root facts, frozen test manifest, and Section 16 resource
  literals directly from their verified frozen sources before launch. The
  default profile retains those facts only in its closed preflight and direct
  command binding. A launched authorized profile additionally persists the one-
  use PASS-TO-LAUNCH record, reopens it by handle, and requires every
  corresponding preflight-to-attestation edge below to be an exact equality, not a similarly
  named claim. `authority_sha256` is the
  D33-canonical SHA-256 of the complete closed Section 8 PASS-TO-LAUNCH
  `authority` object; the runner builds that object once from verified owner,
  packet, predecessor, fixture, correction, namespace, head, and I12 bindings.
  `preflight.authority_sha256` always equals that directly derived hash and, for
  a launched authorized profile only, equals the reopened hash of
  `pass-to-launch.authority`.

  `preflight.correction_full_sha256` and every preflight fixture field other
  than `reverified` equal their directly derived frozen-source values, and PASS
  requires `reverified=true`. For a launched authorized profile they additionally
  equal `pass-to-launch.authority.correction.full_sha256` and the same-named fields in
  `pass-to-launch.authority.fixture`.
  `release_lock_full_sha256`, `proof_lock_full_sha256`,
  `environment_inventory_sha256`, `distribution_record_inventory_sha256`, and
  `pip_check_output_sha256` equal their direct verified environment values.
  Parent and all four child root IDs/hashes, `root_bindings_sha256`, and
  `database_identity_sha256` equal the directly verified root values. PASS
  additionally requires all four root booleans true. `test_manifest_sha256`
  equals the directly derived frozen manifest digest. For a launched authorized
  profile only, every value in this paragraph additionally equals its same-named
  reopened `pass-to-launch.runtime` value.
  No short-name alias such as `correction_sha256`, `release_lock_sha256`,
  `runtime_namespace_sha256`, or `inventory_sha256` is valid.

  `python_runtime_sha256` is the D33-canonical SHA-256 of exactly the Section 16
  object `{implementation:"cpython",version:<3.12.patch>,platform:"win32",
  architecture:"AMD64",executable_sha256:H}` after verifying the interpreter
  by handle. It equals `preflight.environment.python_runtime_sha256`; no
  executable path is in the object. For a launched authorized profile only, it
  also equals the hash of reopened `pass-to-launch.runtime.python_runtime`. Every
  direct-source check, plus every applicable authorized persisted equality, is
  checked before launch and again when the invocation verdict is assembled.

  Preflight status has a local exhaustive partition. A valid `FAIL` requires a
  complete, canonical, safely obtained preflight object and at least one of these
  observed false predicates: a complete fixed F07/C01 fixture binding with every
  field other than `reverified` exact and only `reverified=false`; verified
  runtime/version/platform/architecture or complete dependency/inventory
  comparison; resource minimum or heavy-process count; closed no-egress/local
  endpoint policy; complete PostgreSQL
  isolation/storage sufficiency; or frozen test-manifest selection, node, and
  order. Authority, correction, candidate-head, intent, control, or root-binding
  mismatch; any fixture fixed-field, content, path-namespace, readability,
  identity, or completeness failure; unsafe evidence root, root collision, or topology;
  unreadable or unclassifiable input; incomplete API/hash/arithmetic/schema/
  equality proof; an actual preflight `bounded_bytes` value above `1073741824`;
  reopen mismatch; or status inconsistent with the complete predicate set is
  structural no-root, never a synthetic preflight `FAIL`.
  Individual invocation gates evaluate their own complete projections; a valid
  preflight `PASS` does not force an unrelated later gate to pass, and a valid
  preflight `FAIL` is not a blanket substitute for unevaluated later evidence.

  Process `census_sha256` hashes exactly
  `{"entries":[...],"schema_id":"layer3.b1b.process_census.v1","scope":["analysis.exe","project_api.exe","pytest.exe","python.exe","pythonw.exe","uvicorn.exe"]}`.
  Each entry has only `pid` and `process_start_sha256`; `pid` is positive and the
  digest is `H`. Immediately before target creation, the worker takes exactly one
  complete `PROCESSENTRY32W` snapshot. It selects an entry iff `szExeFile`
  ordinal-ignore-case equals one of those six exact basenames. For each selected
  PID it opens the minimum query handle, requires `GetProcessId` and creation
  `FILETIME` to reproduce the PID/start identity, and requires the final
  `QueryFullProcessImageNameW` basename to equal the snapshot basename under the
  same comparison. It persists no executable hash, path, command, or semantic
  role. The exact bound controller and worker identities are excluded if their
  basenames match; the target does not yet exist. Inaccessible, vanished,
  PID-reused, basename-drifted/mismatched, incomplete, or duplicate candidates
  are structural no-root. Entries sort by unsigned PID then start digest.
  `matching_process_count` equals both array length and
  `preflight.resources.heavy_process_count`; PASS requires zero. This is a
  conservative candidate selector, not a process-role classifier.

  Endpoint `policy_sha256` hashes exactly
  `{"database_endpoint":<null|object>,"external_allowed":[],"external_request_budget":0,"plumbing_classifier":{"git_blob":G,"policy_id":"b1a-v6"},"profile":"<sqlite|postgresql>","schema_id":"layer3.b1b.endpoint_policy.v1"}`.
  SQLite uses null. PostgreSQL uses exactly `{class:<unix_socket|loopback_tcp>,
  endpoint_identity_sha256:H}` for the predeclared isolated endpoint. The runner
  produces this object before any possible launch.
  `preflight.endpoint_policy.policy_sha256` always equals the produced policy
  hash. Only when a launched path creates `endpoint-ledger.json` must
  `endpoint-ledger.json.policy_sha256` equal it; a preflight-only path has no
  endpoint ledger and no endpoint-ledger equality claim. A hash, count, scope,
  process-order, classifier, endpoint, or alias mismatch stops the invocation;
  raw process paths, commands, host, port, URL, and credentials are never persisted.
- `process-ledger.json` is statusless PASS-only and has exactly
  `schema_id=layer3.b1b.process_ledger.v1`, `profile`, `invocation_name`,
  `runner`, `child`, `samples`, `monitor_interval_seconds=1`,
  `observed_max_process_tree_rss_bytes`, `observed_wall_milliseconds`,
  `observed_attempt_milliseconds`, and `launch_count=1`. `runner` is exactly
  `{pid:P,process_start_sha256:H}`; `child` is exactly
  `{pid:P,process_start_sha256:H,exit_code:<integer>}`. Each sample is exactly
  `{ordinal:P,elapsed_milliseconds:N,process_count:N,rss_bytes:N}`. It carries no
  role, runner exit code, limit, violation, or status field.

  Every sample comes only from the exact Section 8.1 quiescent-boundary worker-Job
  stable census with `QueryInformationJobObject(NULL,...)`: RSS is the checked
  sum of the one middle `WorkingSetSize` read for the worker, target, and every
  then-active target descendant. It excludes the outside controller and database
  engine; the conservative shared-page double-count nonclaim applies. Process
  samples are contiguous and correspond one-for-one, in order, only to reached
  quiescent `resource-ledger` boundary observations. Periodic and final cadence
  perform no per-process census and add no process sample. The retained
  `monitor_interval_seconds=1` binds the separate controller/resource cadence,
  not a claim of one-second RSS census.

  `observed_max_process_tree_rss_bytes` is the exact maximum accepted boundary
  sample RSS and equals resource-ledger `maxima.process_tree_rss_bytes`; both are
  observational, churn-tolerant facts and never enforce a process limit.
  `observed_wall_milliseconds` is the monotonic interval from child resume through
  actual child exit; `observed_attempt_milliseconds` is the same-clock interval
  from immediately before the first probe through that exit, with
  `0 <= observed_wall_milliseconds <= observed_attempt_milliseconds`. Actual exit
  is proved by the child exit field, wall/attempt values, physical target and
  descendant exit, and worker-owned target/control/monitor/DB handle closure.
  The process ledger validates identity, boundary-sample order, and closure only;
  it does not enforce RSS, process count, target-wall, or attempt-D1 limits. Hard
  Job limits/accounting own process/memory enforcement; resource ledger owns
  target-wall thresholds; controller intent/deadline mapping/closeout owns
  attempt-D1. A nonzero child/test exit may coexist with a structurally valid
  statusless process ledger. Any required boundary-sample mismatch, missing/extra
  boundary observation,
  arithmetic/identity/clock drift, incomplete exit, or handle-cleanup failure
  produces no accepted process ledger/root. Controller-plus-Job sampling remains
  separately closed in `attempt-closeout.json`; neither source substitutes for
  the other.
- `resource-ledger.json` has exactly
  `schema_id=layer3.b1b.resource_ledger.v1`, `profile`, `invocation_name`,
  `postgresql_storage_binding_sha256`, `preflight_only_job`, `thresholds`,
  `observations`, `maxima`, `terminal_profile_bytes`, `threshold_breached`, and
  `status=PASS|FAIL`.
  `postgresql_storage_binding_sha256` is null for SQLite and equals the
  D33-canonical hash of the complete preflight storage-binding object for
  PostgreSQL. `preflight_only_job` is null for every `test_terminal=true` tuple.
  For the sole `preflight/false,test_terminal=false` tuple it is exactly
  `{runner:{pid:P,process_start_sha256:H},samples:[
  {observation_ordinal:1,process_count:1,rss_bytes:N},
  {observation_ordinal:2,process_count:1,rss_bytes:N}]}`.
  `thresholds` has exactly
  `{min_free_memory_bytes,max_process_tree_rss_bytes,min_volume_free_bytes,
  max_profile_bounded_bytes,max_invocation_seconds}`; `max_profile_bounded_bytes`
  is exactly `1073741824`. `max_process_tree_rss_bytes` remains a direct frozen
  observational-vector ceiling only; it cannot set `threshold_breached` or
  override the intent/closeout hard Job limits. All five values are direct
  universal Section 16 literals; for a launched authorized profile the three maximum values
  additionally equal the same-named reopened PASS-TO-LAUNCH runtime values. A
  default or authorized preflight-only profile has no PASS-TO-LAUNCH dependency,
  and the ledger cannot select independent thresholds. Each observation has exactly
  `{ordinal:P,sample_kind:<cadence|boundary>,boundary:<null|exact-token>,
  elapsed_milliseconds:<nonnegative-integer>,free_memory_bytes:
  <nonnegative-integer>,runtime_bytes:<nonnegative-integer>,database_bytes:
  <nonnegative-integer>,storage_bytes:<nonnegative-integer>,profile_local_bytes:
  <nonnegative-integer>,current_evidence_bytes:<nonnegative-integer>,
  projected_next_write_bytes:<nonnegative-integer>,
  bounded_bytes:<nonnegative-integer>,runtime_volume_free_bytes:
  <nonnegative-integer>,runtime_volume_identity_sha256:H,
  database_volume_free_bytes:<nonnegative-integer>,
  database_volume_identity_sha256:H,storage_volume_free_bytes:
  <nonnegative-integer>,storage_volume_identity_sha256:H,
  evidence_volume_free_bytes:<nonnegative-integer>,
  evidence_volume_identity_sha256:H,
  database_volume_sha256:H}`.
  `maxima` has exactly `{process_tree_rss_bytes:<nonnegative-integer>,
  runtime_bytes:<nonnegative-integer>,database_bytes:<nonnegative-integer>,
  storage_bytes:<nonnegative-integer>,profile_local_bytes:
  <nonnegative-integer>,current_evidence_bytes:<nonnegative-integer>,
  bounded_bytes:<nonnegative-integer>,wall_milliseconds:
  <nonnegative-integer>}`; and
  `terminal_profile_bytes` has exactly `{runtime:<nonnegative-integer>,database:
  <nonnegative-integer>,storage:<nonnegative-integer>}` and is captured at the
  terminal sampling boundary.

  For every `test_terminal=true` tuple, observation ordinals are contiguous from
  one and elapsed time comes from one monotonic invocation clock. Each reached
  quiescent boundary observation has exactly one same-order process-ledger sample
  with the same elapsed value; cadence observations have none. Process-sample
  ordinals are independently contiguous across those boundaries, and the sample
  supplies observational RSS without duplicating that field in the resource
  observation. `sample_kind="cadence"` requires `boundary=null`;
  the first cadence observation occurs no later than 1,000 milliseconds after
  child start, every adjacent cadence elapsed-time difference while the child is
  alive is from 1 through 1,000 milliseconds, and even a shorter child lifetime
  has one cadence observation. A boundary observation cannot replace a cadence
  tick. At most one periodic cadence occurs in each one-second epoch, at most 901
  periodic cadence observations occur before `final_requested`, exactly one
  linked final cadence occurs, at most 24 boundary observations occur, and the
  complete observation array contains from 1 through 930 entries. The process
  array contains exactly the reached quiescent-boundary count. No observation
  follows final cadence and no process sample is unbound to a boundary.

  The sole `preflight/false,test_terminal=false` tuple has no target, process
  ledger, cadence emitter, or final cadence. Its resource ledger instead has
  exactly two boundary observations, `preflight` then `terminal`, with ordinals
  one and two and strictly increasing worker-clock elapsed values. Each
  `preflight_only_job.samples` entry corresponds by ordinal to that observation.
  Both use the exact Section 8.1 `NULL` stable Job census, and both censuses must
  contain exactly the identity-bound `runner`: no target, probe, descendant, or
  other process is present. `process_count` is exactly one and `rss_bytes` is the
  checked sole middle `WorkingSetSize` read. Any census, runner, ordinal, count,
  sample, or observation mismatch is structural no-root. No per-observation RSS
  field is added to `observations`, and no process ledger is created. This
  exception grants no launch, target-exit, cadence, or process-gate claim.
  `sample_kind="boundary"` requires one applicable exact token from this closed
  vocabulary: `preflight`, `monitor_ready`, `pre_upgrade`, `post_upgrade`, `pre_downgrade`,
  `post_downgrade`, `pre_reupgrade`, `post_reupgrade`,
  `pre_race_approved_first`, `post_race_approved_first`,
  `pre_race_nonapproved_first`, `post_race_nonapproved_first`, `pre_timeout`,
  `post_timeout`, `pre_corrupt_basis`, `post_corrupt_basis`, `pre_rollback`,
  `post_rollback`, `C0`, `C1`, `C2`, `C3_prepare`, `C3`, or `terminal`. Every
  boundary reached
  by the selected closed profile manifest occurs exactly once in execution order;
  a later unstarted boundary is absent. Authorized first-path runs require C0,
  C1, C2, C3_prepare, and C3 in that exact order,
  and every selected upgrade/downgrade/reupgrade, both race orders, timeout,
  corrupt-basis, and rollback case has its pre/post pair. Every root, successful
  or failed, ends with exactly one `terminal` boundary when a closed resource
  ledger is admissible. A launched PostgreSQL tuple requires `preflight`, at least
  one runner-side pre-ready cadence sample, then exactly one `monitor_ready`
  before collection may continue, any operation boundary, any test body, or any
  database mutation.

  Arithmetic is exact at every observation:
  `profile_local_bytes = runtime_bytes + database_bytes + storage_bytes`, and
  `bounded_bytes = profile_local_bytes + current_evidence_bytes +
  projected_next_write_bytes + 65536 + attempt_intent_byte_length + 262144`,
  where `attempt_intent_byte_length` exactly equals the preflight attempt value.
  Intent length and closeout reserve are each included once.
  `projected_next_write_bytes` is zero at every observation except
  `C3_prepare`, where it equals the exact prepared `row-file-census.json` binding
  byte length. Both preflight-only observations therefore have
  `current_evidence_bytes=0` and `projected_next_write_bytes=0` and precede every
  evidence-file write.
  At each quiescent boundary, runtime and storage bytes are verified recursive
  byte sums under their bound child namespaces, and `current_evidence_bytes` is
  the verified handle-read sum of all immutable evidence-child files already
  present. A cadence observation performs no file or PostgreSQL census: it
  carries forward the latest accepted quiescent component values, cannot lower a
  maximum, and refreshes only cheap free-memory, free-volume, and endpoint facts.
  Every size-changing action is bracketed by fresh quiescent boundaries. Evidence
  predicts no future write and the manifest is excluded; it is not a fourth
  profile-local component. Every free-space sample is taken on the volume
  named by its adjacent identity hash after revalidating the final handle; for
  SQLite the database identity is the bound database-child volume, while for
  PostgreSQL it is the single deduplicated fixed engine volume from the complete
  writable-location binding, never the empty local database child. Every resolved
  PostgreSQL location reproduces that identity before the one deduplicated volume
  sample is accepted. All three profile-component
  volume identities plus the evidence-volume identity equal their preflight
  resource identities; PostgreSQL's database-volume
  identity also equals the complete binding's `database_volume_identity_sha256`.
  Evidence-volume and the deduplicated PostgreSQL-volume free bytes meet
  `min_volume_free_bytes` at every accepted
  observation, even when its identity equals another fixed local volume. Any
  identity drift fails before accepting that sample. Every observation whose
  projection is zero and every actually executed state is at most `1073741824`.
  For PostgreSQL this means lane-attributable local, control, and evidence bytes
  plus the point-in-time `pg_database_size` value are together at most one GiB.
  The four-GiB remaining-volume floor is conservative policy headroom, not proof
  of 14 GiB capacity or a complete physical PostgreSQL footprint.
  In a PASS ledger, every observation and `maxima.bounded_bytes` is at most that
  cap; the sole permitted over-cap ledger value is a complete prevented nonzero
  projection under the FAIL partition below. A projected breach stops before the
  action and cannot be hidden by later shrinkage. Each component maximum is the
  high-water mark over all observations. For `test_terminal=true`,
  `process_tree_rss_bytes` equals the process ledger's observational maximum over the
  exact Section 8.1 middle-read RSS samples. For the preflight-only tuple it is
  exactly the maximum of the two persisted `preflight_only_job` RSS values. Every
  observation's
  `free_memory_bytes` uses that section's exact
  `GlobalMemoryStatusEx(...).ullAvailPhys` rule; neither value may use a
  reconstructed or alternate provider.
  For `test_terminal=true`, `wall_milliseconds` equals the process ledger's
  actual-exit `observed_wall_milliseconds`, is at least the terminal observation's
  elapsed value, and is at most `900000`; it is not an observation high-water
  claim. The process ledger continues RSS/wall closure through actual exit.
  Terminal is the last boundary observation, not the last observation: only the
  exact already-started/periodic and one linked final-cadence tail below may
  follow it. Maxima include every accepted later cadence observation; no later
  boundary, operation, test, or mutation is accepted. For the preflight-only
  tuple, `wall_milliseconds=0` because no target starts; terminal elapsed may be
  positive and is exempt from the launched target-wall lower bound. Its terminal
  observation is the final observation.
  `terminal_profile_bytes` exactly aliases the terminal
  boundary observation's runtime, database, and storage values and is not
  rewritten by later cadence; maxima retain any earlier or later high-water value.

  `C3_prepare` is an authorized-only compound resource boundary immediately
  before C3. Its pre-ACK observation requires the fixed known-root
  `row-file-census.json` basename absent, consumes the same frozen profile-
  specific database sample and exact prepared binding as the `c3_prepare` frame,
  measures actual current evidence bytes, and sets
  `projected_next_write_bytes` to that binding's exact positive byte length. While
  the provider retains its sole immutable canonical buffer, the runner also takes
  the matching process-tree RSS sample and incorporates it into both process and
  resource maxima. After revalidating the evidence-volume identity, free bytes
  before prepare ACK must be at least
  `4294967296 + projected_next_write_bytes + 65536 + 262144`; intent is already
  on disk and is not added again to free-space demand. The resulting exact bounded
  projection must remain within the one-GiB cap. The C3 observation uses the same
  frozen database sample, requires the closed census file now present, counts its
  bytes in `current_evidence_bytes`, resets `projected_next_write_bytes=0`, and
  therefore observes the post-publication state. Any absent/present inversion,
  sample/binding/accounting mismatch, hard Job or local high-water breach, identity
  drift, or insufficient free space receives no corresponding ACK.

  Resource status has a local exhaustive partition. `status=PASS` iff every
  applicable observation, identity, arithmetic, maximum, threshold, and cleanup
  fact is complete and `threshold_breached=false`. A launched tuple additionally
  requires exact cadence/process-sample equality, terminal/final-cadence/exit,
  and target-handle closure. The preflight-only tuple instead requires its exact
  two observations and persisted sole-runner samples, zero target wall, no target
  or process ledger, and closure of every preflight input/measurement handle. A
  complete measured free-memory, volume-free, hard Job-limit, or launched target-
  wall breach may produce valid `status=FAIL` only when the next runtime/
  application action or ACK is withheld and all applicable terminal, exit,
  cleanup, and containment facts close exactly. A nonresource preflight FAIL may
  coexist with a resource PASS. Incomplete termination or cleanup produces no
  resource ledger/root rather than a partial FAIL.

  After a worker-local resource breach, no later runtime/application operation,
  mutation, or ACK is valid. Bounded evidence-only failure finalization remains
  permitted under every existing per-write free-space, reserve, cap, immutable-
  member, and manifest check; it cannot add an observation or recast the breach.
  An outer-controller resource stop is stricter and forbids every later worker
  evidence/root write under Section 8.1.

  A nonzero pre-operation `bounded_bytes` projection above `1073741824` may
  produce valid `FAIL` only when the corresponding action is not executed and the
  same actual state recomputed with `projected_next_write_bytes=0` remains at or below
  `1073741824`; the projected value itself is retained as the first threshold
  breach and is not admitted as an executed state. Preflight-only projection is
  always zero, so an actual preflight bounded value above the cap is no-root, not
  FAIL. Any actual or unprevented bounded state above the cap, post-breach runtime/
  application mutation or ACK, unbounded evidence write, incomplete read or
  cadence, identity drift, arithmetic mismatch, incomplete cleanup/exit, or
  status inconsistent with this partition is structural no-root. Thus
  `threshold_breached` is true iff one of the complete admissible measured or
  prevented-projection breaches above occurred; no global catch-all converts an
  invalid observation into FAIL.

  For SQLite, `database_bytes` is the verified recursive byte sum of the entire
  database child, including the authoritative DB and every replay/comparison
  sandbox still retained under the no-delete rule. Its observation
  `database_volume_sha256` is the D33-canonical SHA-256 of exactly
  `{"database_bytes":N,"database_root_canonical_sha256":H,"profile":"sqlite","schema_id":"layer3.b1b.sqlite_profile_database_volume.v1"}`.
  The runner derives both values from one exhaustive regular, non-reparse,
  handle-based traversal; this resource digest does not alias the authoritative-
  DB-only checkpoint volume digest.

  For PostgreSQL, the bound local database child remains empty at every
  observation. At a quiescent boundary, `database_bytes` is the nonnegative
  point-in-time `pg_database_size` result for the same bound database identity and
  is counted exactly once; it is never added again as local-child bytes. This
  value is not transaction-consistent and excludes WAL, temporary files,
  tablespace-wide/shared engine data, and other physical engine footprint. It
  supports no complete physical-storage claim. The complete writable-location
  binding and fixed-volume checks remain separate.

  The observation `database_volume_sha256` is the exact Section 9
  `layer3.b1b.database_volume.v1` digest built from that point-in-time size, the
  same DB identity, empty `physical_files`, and profile literal; free-space and
  volume-identity measurements are adjacent observation fields, never digest
  inputs. The plugin's PostgreSQL monitor API is the sole C0-C3 database-sample
  producer. At each quiescent boundary it verifies the same database, endpoint,
  role, and storage-binding identities, executes exactly one `pg_database_size`
  call, and freezes the resulting complete database-sample object. At C0-C2 it
  emits that object and supplies it to the checkpoint census component. At C3 it
  passes the same object into registered provider control and compound frames;
  the provider never calls `pg_database_size`, and the plugin never receives
  census bytes. A second call at one boundary, reconstructed size, or cross-
  boundary reuse fails. At C3, resource `database_bytes` and digest equal the
  checkpoint's `logical_bytes` and digest because both consume the same immutable
  boundary sample; storage-binding hashes also equal.

  Terminal is a fresh quiescent read-only measurement, not a cross-time alias.
  It independently recomputes the same digest from its point-in-time size; neither
  terminal value must equal C3. No selected test body, application operation, or
  database-mutating hook/finalizer may run after C3. Periodic and final cadence
  perform no PostgreSQL size call and carry forward the latest accepted boundary
  value without claiming contemporaneous size. Maxima retain every larger fresh
  boundary value.

  Every launched pytest invocation loads the one bound prospective
  `backend/b1b_pytest.py` plugin inside the existing single child. Pytest capture
  remains enabled: `-s`, `--capture=no`, tee capture, stdout/stderr parsing, and
  console text as evidence authority are forbidden. The plugin is the sole child
  control-event producer and the runner is the sole persisted-ledger and test-
  result producer. SQLite opens no database monitor connection. PostgreSQL opens
  exactly one read-only monitor connection in `pytest_sessionstart`, before
  collection, re-verifies the bound database/server/endpoint/storage identities,
  and performs only point-in-time size reads at quiescent boundaries.

  Every pipe message is one strict frame: a four-byte unsigned big-endian payload
  length from 1 through 4096 followed by exactly that many D33-canonical UTF-8
  JSON bytes with no BOM or newline. Those payload bytes are the complete event
  envelope, not a body fragment; the entire canonical envelope must be at most
  4096 bytes. Length 4096 is accepted; 0, 4097, truncation, surplus bytes,
  noncanonical JSON, or a short/interleaved write is rejected. The plugin holds
  one process-local write lock across the complete prefix-plus-payload write. Its exact envelope is
  `{schema_id:"layer3.b1b.control_event.v1",single_run_nonce:H,child_pid:P,
  child_process_start_sha256:H,event_ordinal:P,event_type:<exact>,body:<exact>}`.
  Event ordinals are contiguous from one. A PostgreSQL database sample is exactly
  `{database_identity_sha256:H,endpoint_identity_sha256:H,
  postgresql_storage_binding_sha256:H,database_bytes:N}`. The closed
  C3 census binding is exactly
  `{basename:"row-file-census.json",byte_length:P,sha256:H}`. The closed
  `event_type`/`body` union is:

  - `monitor_ready`: the exact PostgreSQL database-sample object; exactly one,
    PostgreSQL only, and first in its stream;
  - `cadence`: exactly one of
    `{cadence_kind:"periodic",database_sample:<null|postgresql-database-sample>}`
    or `{cadence_kind:"final",terminal_event_ordinal:P,
    database_sample:<null|postgresql-database-sample>}`; the sample is null for
    SQLite and nonnull for PostgreSQL;
  - `c3_prepare`: `{name:"C3",database_sample:<null|postgresql-database-sample>,
    census_binding:<exact-C3-census-binding>}`;
  - `boundary`: either `{name:<one applicable child-reachable closed boundary
    token other than preflight|monitor_ready|C3_prepare|C3|terminal>,
    database_sample:<null|postgresql-database-sample>}` or, for C3 only,
    `{name:"C3",database_sample:<null|postgresql-database-sample>,
    census_binding:<exact-C3-census-binding>}`. Both forms use the same profile-
    specific null/sample rule;
  - `collection_item`: `{collection_index:N,node_id:J}`;
  - `deselection`: `{node_id:J}`;
  - `collection_error`: `{collector_node_id:<J|"<root>">,message_sha256:H}`;
  - `collection_closed`: `{collected:N,deselected:N,collection_errors:N}`;
  - `endpoint_attempt`: exactly one of
    `{attempt_class:"external",attempt_kind:<name_resolution|socket_connect>,
    disposition:"denied"}`,
    `{attempt_class:"plumbing",closed:true,disposition:"allowed",
    plumbing_kind:<loopback_tcp|socketpair|unix_socket>}`, or
    `{attempt_class:"database",attempt_index:P,closed:<true|null>,
    control_kind:<child_monitor|provider_census|null>,
    disposition:<allowed|denied>,endpoint_identity_sha256:H,
    outcome:<connected_closed|failed_no_connection|ceiling_denied_no_side_effect>}`;
  - `postgresql_proof_case`: one exact Section 10 PostgreSQL case entry;
  - `node_outcome`: `{node_id:J,classification:<passed|failed|skipped|xfailed|
    xpassed|error>,terminal_phase:<setup|call|teardown>}`; and
  - `terminal`: `{pytest_exit_code:<integer>,collected:N,node_outcomes:N,
    provider_disposition:<not_applicable|not_registered|discarded|consumed>,
    database_sample:<null|postgresql-database-sample>}` with the same profile-
    specific null rule. Terminal has no future-cadence ordinal or other backlink.

  Event-local bounds are closed. `child_pid` is `1..4294967295`; event ordinal is
  `1..13244`; every `T` is 1..160 safe ASCII bytes; every HTTP status inside a
  proof-case body is `100..599`; and every union count is bounded. Let `C` be
  pre-deselection collection items, `D` deselections, `R` collection errors, and
  `E` `endpoint_attempt` events: `C<=4096`, `D<=C`, outcomes `<=C-D`, `R<=20`, and
  `E<=4096`. Fixed events are exactly at most `936 = 901` periodic cadence + one
  final cadence + 20 ordinary boundaries + one `monitor_ready` + one `c3_prepare`
  + one terminal + one `collection_closed` + ten PostgreSQL cases. The exhaustive
  ceiling is `936+C+D+(C-D)+R+E<=13244`. No padding or new event is permitted.
  Reproduced largest PostgreSQL-case envelope is 1997 payload bytes/2001 framed
  bytes; its ceiling is 2048/2052. Universal payload/frame ceilings are
  4096/4100.

  Every item, deselection, and outcome `J` has as prefix exactly one selected
  manifest file; the remaining text is empty or begins `::`. A collector `J`
  has as prefix a selected file or is a strict safe repo-relative ancestor of one.
  Only pytest's raw empty root/session collector maps to the literal `<root>`;
  `<root>` is forbidden for every other raw value, field, event, and node. Prefix
  ambiguity, normalization, unsafe text, or an envelope over 4096 bytes fails the
  stream before persistence.

  PostgreSQL uses one in-memory attempt counter across every runner-host, plugin-
  monitor, provider, Alembic, SQLAlchemy, and application connection request;
  successful and failed requests both count. `128` is a conservative F479
  planning ceiling, not a previously owner-selected or observed count. A request
  with 128 earlier attempts is the mechanical 129th and is denied before DNS,
  socket, provider, or database side effect through the existing endpoint control
  and `endpoint_attempt` event surface, with no new event, schema ID, or path.
  Path 29 drives that control directly and proves the denial. The role's separate
  simultaneous-connection ceiling remains three.

  A child-originated `endpoint_attempt` is emitted synchronously on the attempt
  thread under the same pipe write lock; it adds no thread or channel. An
  external attempt emits before any side effect and must be denied. Plumbing and
  connected database attempts emit only after the connection/socket has closed;
  failed attempts emit after proving no connection exists, and the ceiling denial
  emits before side effect. The child
  monitor connection is the sole exception: it emits no `endpoint_attempt`; its
  database-attempt entry is derived from accepted `monitor_ready` with
  `control_kind="child_monitor"`. The runner records its retained host identity
  connection directly. The provider census session uses the database event with
  `control_kind="provider_census"`; every application/Alembic/SQLAlchemy
  connection uses null. No raw endpoint, name, address, port, URL, credential,
  path, or command enters any event.

  Monitor closure is proved only by the accepted `monitor_ready`, the final
  cadence as last frame, static candidate-blob proof that monitor close occurs
  before pipe close, pipe EOF, and physical child exit. Those facts may not
  interleave or be replaced by a count. An exception, alternate close path,
  missing final cadence/EOF/exit, or identity/exit mismatch produces no endpoint
  ledger/root. Every endpoint variant and `postgresql_proof_case` envelope is
  mechanically reproduced prefreeze against its closed body and must fit its
  applicable case ceiling and the universal 4096-byte payload/4100-byte framed
  ceiling.

  Within the collection-event subsequence, `collection_item` events use
  contiguous zero-based indices and reproduce the complete pre-deselection order.
  They occur first, then all `deselection` events in pytest order, then all
  normalized `collection_error` events in report order, then exactly one
  `collection_closed`; cadence may interleave, but no later collection event or
  earlier node outcome is valid. The closed counts equal those event arrays. No
  selected node is also deselected. Each executed selected node emits exactly one
  aggregate `node_outcome` after its last applicable phase. Any non-passed
  teardown report classifies as `error` with `terminal_phase=teardown` and
  overrides earlier reports. Otherwise, setup failure is `error`, setup skip is
  `skipped`, and both use `terminal_phase=setup`. Otherwise the call report is
  decisive: `wasxfail` supplies `xfailed` or `xpassed`, failure is `failed`, skip
  is `skipped`, and success is `passed`, all with `terminal_phase=call`. No
  duplicate per-phase outcome arrays or raw exception/skip text enters a frame.
  For collection errors, the plugin takes pytest's `CollectReport.longreprtext`,
  converts CRLF and bare CR to LF, replaces the verified repo, venv, and lane-
  parent absolute namespaces with `<repo>`, `<venv>`, and `<lane>` longest-first
  under Windows ordinal-ignore-case matching, replaces every ASCII
  `0x[0-9A-Fa-f]+` token with `0xADDR`, removes trailing spaces/tabs from each
  line, removes leading and trailing empty lines, rejoins with LF and no terminal
  LF, and requires nonempty text. `message_sha256` hashes those exact UTF-8 bytes;
  raw text is not persisted or logged.

  Cadence and collection/outcome events do not wait. For `monitor_ready` and every
  nonterminal ordinary `boundary` other than C3, the plugin pauses cadence, emits
  one complete frame under the write lock, releases that lock, and waits on the
  inherited auto-reset continuation event; no cadence appears between such a
  frame and its one matching runner signal. The `c3_prepare` and C3 epochs instead
  obey the uninterrupted compound pause below. Terminal is different: it is the
  last boundary but not the last frame. The plugin emits terminal under the write
  lock without pausing cadence, releases the write lock, and waits outside it, so
  zero or more periodic frames may be written while the runner validates terminal.
  `c3_prepare`, C3, and terminal each have a distinct wait/ACK epoch and distinct
  runner signal. An early, duplicate, reused, stale, skipped, or cross-epoch ACK
  fails; the one inherited event cannot make epoch identities alias. The runner
  validates envelope, nonce, child identity, event order, profile-specific body,
  same-boundary host/root measurements, arithmetic, thresholds, and cap before
  each signal. A malformed or out-of-order frame, identity mismatch, timeout,
  premature EOF, or resource breach receives no signal, terminates only the owned
  tree, and enters external containment.

  PostgreSQL must deliver valid `monitor_ready` within exactly 30000 monotonic
  milliseconds after resume. The runner compares it with the retained host
  connection's database, endpoint, and complete storage-binding identities,
  closes that host connection, records the boundary, and only then signals. Host
  and child `database_bytes` are separately valid point-in-time
  observations; they are never required or asserted equal. No collection, test
  body, or database mutation starts earlier. SQLite has no `monitor_ready` event
  and begins collection after direct preflight/control validation.

  On the main pytest thread, at exact final-bridge-node entry and before its first
  application mutation, the node registers exactly one nonreplaceable, single-
  use C3 provider. Registration is bound to that node ID and the candidate-head
  Git blob for
  `backend/tests/test_layer3_connector_promotion_bridge.py`; no other node, blob,
  hook, or later registration can supply or replace it. Its registered authority
  remains live and usable only through the eventual consume or discard transition.
  Successful provider state is exactly
  `EMPTY -> REGISTERED -> PREPARED -> AUTHORIZED -> WRITING -> CLOSED ->
  CONSUMED`, with no duplicate transition, replacement, reentry, retry, rewind,
  or second publication. A non-PASS final node emits its classified
  `node_outcome`, then performs terminal in-memory `REGISTERED -> DISCARDED` before
  any prepare. A normal missing-success path after registration performs that
  same irreversible discard before prepare. Discard permits no prepare,
  publication, C3 frame/ACK, or PASS, but it permits the orderly failure terminal,
  linked final cadence, pipe EOF, physical exit, closed FAIL test result, and
  valid FAIL root described below. Abrupt process death records no discard
  transition and enters external no-root containment.

  For a PASS final node, its last application mutation, teardown, and every
  fixture finalizer complete; all application/DB background writers are joined;
  then its aggregate PASS `node_outcome` frame emits. Only afterward, in
  `pytest_runtest_logfinish`, the plugin obtains the sole C3 PostgreSQL database
  sample through the one-call monitor API; SQLite uses null. The plugin passes
  only that frozen sample and control intent to the registered provider. The
  provider opens exactly one read-only census session, re-verifies database,
  endpoint, and storage identities, remains endpoint-accounted and attempt-
  bounded, and never calls `pg_database_size`. It builds the complete C3 census,
  D33-canonicalizes the closed `row-file-census.json` object once, closes the DB
  session, retains those immutable canonical bytes in its own buffer, moves
  `REGISTERED -> PREPARED`, and returns only the exact C3 census binding. The
  plugin never receives, copies, parses, hashes, serializes, or persists any
  census byte.

  After `prepare()` returns, the plugin acquires the existing cadence lock. Any
  already-started periodic frame finishes before acquisition completes; the
  plugin then sets the compound pause and permits no new cadence start. While
  holding that same pause, it emits `c3_prepare` with C3 name, frozen sample, and
  binding. The runner validates the frame and exact `C3_prepare` resource
  observation: fixed census file absent, identities equal, hard Job accounting
  and local high-water within limits, evidence-volume identity unchanged, free
  space sufficient for exact draft plus `65536` manifest reserve plus `262144`
  closeout reserve, and complete cap arithmetic.
  Only return from the distinct prepare-ACK wait permits the plugin to invoke
  `provider.authorize()`, whose sole valid transition is
  `PREPARED -> AUTHORIZED`.

  Still under the same uninterrupted cadence pause, the plugin invokes
  `provider.publish()`. The provider alone moves `AUTHORIZED -> WRITING`, creates
  the fixed known-root `row-file-census.json` basename with create-new/no-clobber
  semantics, writes exactly its retained buffer, flushes without any ORM or DB
  mutation, closes it, protects it Windows ReadOnly, reopens it no-follow through
  a regular non-reparse handle, and reproduces byte length/hash before moving to
  `CLOSED`. The plugin then emits the C3 boundary with the same frozen
  sample and binding. The runner independently reopens and parses the file,
  verifies its closed schema, profile, invocation, C0-C3 lineage, comparisons,
  sample-derived database digest, resource accounting, and committed datetime-
  witness registry, takes the C3 post-publication resource observation including
  census bytes, and records the accepted binding in its immutable C3 registry.
  A structurally valid census with `status=FAIL` may receive the C3 ACK but later
  fails the census/invocation gate. Only return from the distinct C3-ACK wait
  permits the plugin to invoke `provider.consume()`, whose sole valid transition
  is `CLOSED -> CONSUMED`; cadence resumes only after that transition.

  No cadence, collection, outcome, or other boundary frame may interleave from
  compound-pause acquisition through C3 ACK, and no protocol consumer may open,
  read, hash, parse, count, accept, or bind the census until `CLOSED` and
  successful no-follow reopen; direct-create directory-entry, length, or
  partial-byte visibility is not denied and carries no authority. A prepare/publish/reopen/schema/hash/sample/accounting/registry/
  state mismatch, partial write, or malformed frame holds the pause until the
  worker stops and the controller enters attempt containment; it permits no retry,
  terminal, closed root,
  or cadence resume and makes no complete-reap claim unless the containment
  predicates actually close. The plugin imports no application module,
  SQLAlchemy surface, or file-I/O implementation and invokes only the registered
  provider control interface. C3 adds no additional OS/IPC control handle or
  channel, process, background thread, helper, artifact, manifest member, file
  basename/path, or second plugin. The already declared transient provider DB-
  session and census data-file handles are the sole C3 data handles and close at
  their specified prepare/publish/reopen transitions. The controller-owned Job,
  timer, namespace mutex, process, and closeout handles remain outside C3 and are
  never inherited by the worker or target. Every complete event envelope remains
  at most 4096 bytes.

  After accepted C3 ACK, zero or more periodic frames may precede terminal. The
  exact remaining order is terminal boundary/frame; zero or more already-started
  or periodic frames while the runner validates terminal; terminal ACK;
  `final_requested` set under the cadence lock; completion of any already-started
  periodic frame with no new periodic start; exactly one final cadence linked to
  the terminal ordinal; cadence-emitter join; pipe EOF; actual child exit. The
  runner provisionally captures `final_tail_anchor` at the runner-monotonic
  instant it reads the complete final-cadence frame; that instant becomes valid
  only if the frame later passes every envelope, identity, sample, linkage,
  resource, and ordering check. Join, EOF, and exit must occur in that order and
  each no later than `final_tail_anchor + 1000` milliseconds. Existing
  `exit_within_1000_milliseconds` is true only under that complete three-boundary
  rule. The separate target and whole-attempt deadlines also continue to apply.
  Final cadence is the last frame; its PostgreSQL sample is fresh, while
  terminal's sample remains the terminal resource-boundary measurement and
  `terminal_profile_bytes` alias.

  The cadence emitter is the only permitted post-C3 child thread and is read-
  only. Missing/mislinked final cadence, invalid anchor, delayed join/EOF/exit,
  an intervening or late boundary, ACK race, new periodic start after
  `final_requested`, unjoined emitter, frame after final cadence, premature EOF,
  timeout, abrupt exit, or exit-code disagreement enters attempt containment and
  leaves no closed terminal root.
- `endpoint-ledger.json` has exactly
  `schema_id=layer3.b1b.endpoint_ledger.v1`, `profile`, `invocation_name`,
  `policy_sha256`, `external_request_budget=0`, `external_attempts`,
  `loopback_plumbing`, `database_endpoint`, `postgresql_storage_binding_sha256`,
  `counts`, and `status=PASS|FAIL`. Each `external_attempts` entry is exactly
  `{ordinal:P,attempt_kind:<name_resolution|socket_connect>,disposition:"denied"}`.
  Each `loopback_plumbing` entry is exactly
  `{ordinal:P,plumbing_kind:<loopback_tcp|socketpair|unix_socket>,
  disposition:"allowed",closed:true}`. These arrays contain no free `class`,
  endpoint hash, role, or separate denied-attempt object.

  `database_endpoint` is null for SQLite and exactly
  `{class:<unix_socket|loopback_tcp>,endpoint_identity_sha256:H,attempts:[...],
  control_ordinals:{runner_identity:P,child_monitor:P,
  provider_census:<P|null>},attempt_count:N,connection_count:N}` for PostgreSQL.
  Each nested attempt is exactly `{ordinal:P,attempt_index:P,
  disposition:<allowed|denied>,closed:<true|null>,
  outcome:<connected_closed|failed_no_connection|ceiling_denied_no_side_effect>}`. Every
  nonnull control ordinal is a distinct reference into that array.
  `provider_census` is null iff the provider is not applicable, never registered,
  or discarded; it is nonnull iff the provider is consumed. The remaining
  database attempts are unclassified application/Alembic/SQLAlchemy connections
  by exclusion, not by a free role field. `attempt_index` is contiguous from one;
  `attempt_count` equals array length, while `connection_count` counts only
  `connected_closed`. `counts` is exactly `{external:N,plumbing:N,database:N}`;
  `database` equals attempt count, not successful connections.

  One global ordinal spans the disjoint union of external, plumbing, and database
  attempts; sorted union ordinals are exactly `1..N`, with no gap or duplicate.
  The retained runner host connection is recorded directly, the child monitor is
  derived from `monitor_ready` under the closure proof above, and the provider
  census connection is recorded by its post-close event. Every PostgreSQL
  database attempt uses the one approved endpoint identity. All application and
  finalizer connections close before terminal/C3 as applicable; no more than
  three are simultaneous; provider census
  closes before `c3_prepare`; the host closes before the `monitor_ready` ACK; and
  the monitor closes after final cadence and before EOF. Every connection closes
  before ledger creation. Observed PostgreSQL total is at least runner plus
  monitor plus every applicable provider/application connection; a consumed
  provider therefore requires at least three connections.

  Endpoint `PASS` requires complete accounting, zero external attempts, at most
  128 database attempts, every plumbing attempt closed, every database outcome
  `connected_closed`, exact ordinals/counts/controls, and all role/policy/storage/
  endpoint identities equal. A valid `FAIL` requires a complete ledger with one
  or more denied external, failed database, or ceiling-denied database attempts;
  each denial precedes side effect, every successful local connection closes, no
  failed/denied attempt leaves a connection, actual egress is zero, and ordinals/
  counts/closure remain exact. A gap, allowed external attempt, open/unknown attempt,
  alternate endpoint, count/control/order mismatch, raw secret, or status
  inconsistent with this partition is structural no-root.
  `postgresql_storage_binding_sha256` is null for SQLite. For each launched
  PostgreSQL endpoint ledger, it always equals the exact preflight,
  PASS-TO-LAUNCH, and resource-ledger binding hashes; it equals the checkpoint
  binding hash only when both `row-file-census.json` and the checkpoint siblings
  exist. It is a sibling co-binding and never changes endpoint identity.
- `row-file-census.json` has exactly
  `schema_id=layer3.b1b.row_file_census.v1`, `profile`, `invocation_name`,
  `checkpoints`, `deltas`, `summary_update_fence`, `comparisons`, `materializer_comparison`,
  `method_comparison`, `orphan_containment`, and `status=PASS|FAIL`.
  For `sqlite_authorized`, both comparison fields are the exact closed Section 6
  objects. For `postgresql_authorized`, `materializer_comparison` and
  `method_comparison` are exactly null; any object or other value fails.
  Each checkpoint is exactly `{name:T,tables,application_files,
  authoritative_state_census_sha256:H,database_volume_sha256:H,
  postgresql_storage_binding_sha256:<H|null>,evidence_root_excluded:true}`;
  each table entry is
  `{table:T,row_count:<nonnegative-integer>,rowset_sha256:H}` and each file entry
  is `{logical_class:T,byte_length:P,sha256:H}`. Each delta is exactly
  `{from:T,to:T,row_deltas,file_deltas}`; row deltas are
  `{surface:T,inserted:<nonnegative-integer>,updated:<nonnegative-integer>,
  deleted:0,changed_columns:[T...]}` and file deltas are
  `{logical_class:T,created:<nonnegative-integer>,changed:0,removed:0}`.

  `checkpoints` contains exactly `C0`, `C1`, `C2`, `C3` in that order. Every
  checkpoint `tables` array contains these 28 literals in order:
  `ConnectorRun`, `ConnectorRunTarget`, `L3ConnectorSourceIntakeRecord`,
  `L3GateBIdempotencyKey`, `L3Session`, `L3SelectionManifest`, `L3Descriptor`,
  `L3RetrievalEvent`, `L3MaterialSnapshot`, `L3ConnectorPromotionReceipt`,
  `SourceConnector`, `Dataset`, `DatasetVersion`, `VariableDefinition`,
  `DatasetSourceProvenance`, `DatasetRow`, `L3TypingRecord`, `L3AnalysisUnit`,
  `L3AnalysisGroup`, `L3AnalysisSet`, `L3AnalysisPlan`, `L3PassRun`,
  `AnalysisRun`, `AssumptionCheck`, `AnalysisArtifact`, `CaveatNote`,
  `L3ReconciliationRecord`, `L3OutputPackage`. No table is implicit.

  Checkpoint `application_files` order is exact: C0 has `connector_raw`; C1 adds
  `gate_b_snapshot`; C2 and C3 then add, in order,
  `dataset_version_parquet`, `promoted_session_snapshot`,
  `descriptive_result_artifact`, `pass_output_manifest`,
  `canonical_internal_package`, `user_facing_package`, and
  `review_facing_package`. `deltas` is exactly the four complete Section 6
  objects in `pre-capture` to C0, C0 to C1, C1 to C2, C2 to C3 order. Actual
  values must equal that expected object; no zero row/file entry may be omitted.

  For each checkpoint the census component first builds exactly
  `{schema_id:"layer3.b1b.authoritative_state_census.v1",
  profile:<sqlite|postgresql>,invocation_name:T,database_identity_sha256:H,
  tables:<the exact ordered 28-table projection above>,
  application_files:<that checkpoint's exact ordered projection above>,
  evidence_root_excluded:true}`. Its D33-canonical SHA-256 is the checkpoint's
  `authoritative_state_census_sha256`. Database-volume/free-space/physical-file
  facts, the PostgreSQL storage-binding sibling, and the checkpoint wrapper are
  excluded from this preimage. SQLite uses null for every checkpoint storage-
  binding hash. PostgreSQL uses the one hash shared by preflight, authorized
  PASS-TO-LAUNCH, resource ledger, and endpoint ledger. The census component is
  the checkpoint sibling's sole producer from that already verified binding.

  Authoritative aliases are profile-local and exact. For `sqlite_authorized`,
  `C2 = handoff.c2 = post-handoff = pre-replay = post-replay = C3 =
  integrated.census.c2 = integrated.census.c3`. Concretely,
  `checkpoints[C2].authoritative_state_census_sha256` equals both handoff receipt
  census fields, both authoritative replay-receipt census fields,
  `checkpoints[C3].authoritative_state_census_sha256`, and both integrated
  verdict census hashes. For `postgresql_authorized`, the complete alias chain is
  exactly `C2 = C3`; the PostgreSQL proof receipt has no census backlink, and no
  handoff, replay, or integrated alias exists. Every equality is within one profile,
  invocation, database identity, and C0-C3 lineage. A SQLite value may not alias
  or substitute for a PostgreSQL value, or conversely, even if bytes happen to
  match. SQLite receipts consume their declared state-census hashes; they never
  consume, predict, or alias the future `row-file-census.json` file hash. The
  PostgreSQL receipt carries neither authoritative-state-census nor row-file-
  census hash.
  For PostgreSQL C2, the census component reopens the authoritative package's
  immutable `result-review.json`, validates its closed schema, re-derives
  `connector_b1_evidence.battery_census_sha256` from the exact prospective
  profile-qualified PostgreSQL zero/zero contract, and compares every locked
  actual C2 count plus absent/null comparison state against it. Opaque package-
  byte equality is insufficient. A missing member, wrong profile/count, unequal
  digest, nonzero comparison run, or nonnull comparison object makes the package,
  files, and census predicates FAIL; C2 never rewrites the member. The PostgreSQL
  proof receipt carries no battery field; it binds only the resulting
  `authoritative_state_census_sha256`.

  `summary_update_fence` is exactly a two-entry array in `L3Session`, then
  `L3ReconciliationRecord`, order. Each entry is exactly
  `{surface:<literal>,row_id:U,before_summary_sha256:H,after_summary_sha256:H,
  changed_keys:[...]}`. The session `changed_keys` array is exactly
  `["package_review_state","package_review_hash","reconciliation_record_id",
  "packages","connector_dataset_handoff_basis_hash"]`; the reconciliation
  array is exactly `["package_review_submit","package_review_hash",
  "connector_dataset_handoff_basis","connector_dataset_handoff_basis_hash"]`.
  The before/after hashes bind the complete D33-canonical summary objects and an
  exact JSON diff must contain those keys and no other key or nested change.
  C2 is reachable only after approved package review: its session before-image
  is the stable twelve-key `layer3.b1b_session_state.v1` object with the final
  five keys null, and its after-image changes exactly all five while retaining
  the same schema and first seven values. `packages` is the exact ordered
  three-object review projection and the session carries only the handoff-basis
  hash. A changes-requested, rejected, or blocked review instead changes exactly
  the first four session keys, leaves the basis hash null, changes only the first
  two reconciliation keys, and cannot create C2 or satisfy this fence.

  For `sqlite_authorized`, `comparisons` contains exactly named
  `{name:T,passed:<boolean>,evidence_sha256:H}` objects in this exhaustive order:

  1. `c0_capture_rows_exact`
  2. `c0_application_files_exact`
  3. `c1_gate_b_rows_atomic`
  4. `c1_snapshot_file_exact`
  5. `c2_row_deltas_exact`
  6. `c2_application_files_exact`
  7. `summary_update_fence_exact`
  8. `c2_c3_rowsets_equal`
  9. `c2_c3_application_files_equal`
  10. `same_request_zero_mutation`
  11. `cross_run_same_i1_reuse`
  12. `divergent_d34_conflict`
  13. `gate_b_orphan_containment`
  14. `materialization_orphan_containment`
  15. `package_orphan_containment`
  16. `no_raw_copy_after_c0`
  17. `materializer_semantic_three_way`
  18. `materializer_physical_linkage_each`
  19. `method_semantic_three_way`
  20. `method_artifact_rehash_each`
  21. `evidence_root_excluded`

  Both candidate-head and merged-main SQLite-authorized reruns use all 21.
  `postgresql_authorized` uses exactly these 14 names in the same relative order:
  `c0_capture_rows_exact`, `c0_application_files_exact`,
  `c1_gate_b_rows_atomic`, `c1_snapshot_file_exact`, `c2_row_deltas_exact`,
  `c2_application_files_exact`, `summary_update_fence_exact`,
  `c2_c3_rowsets_equal`, `c2_c3_application_files_equal`,
  `gate_b_orphan_containment`, `materialization_orphan_containment`,
  `package_orphan_containment`, `no_raw_copy_after_c0`, and
  `evidence_root_excluded`. It excludes the three replay-only names and all four
  materializer/method three-way names, has no replay/comparison-sandbox source,
  and requires both comparison fields null. `sqlite_default` produces no
  `row-file-census.json`, census
  binding, comparison member, or census/comparison gate.

  Every displayed JSON pointer follows RFC 6901: empty pointer means the whole
  document; `/` separates reference tokens; `~0` and `~1` decode only to `~` and
  `/`; array tokens are canonical unsigned decimal indices without leading
  zeros. The displayed `*` is the sole extension. It expands before projection:
  array children by ascending numeric index, object children by ascending
  unsigned UTF-8 bytes of decoded key. Expansion is deterministic, exhaustive,
  duplicate-free, and an empty/missing/type-mismatched expansion fails.

  Each `evidence_sha256` hashes the D33-canonical object
  `{schema_id:"layer3.b1b.comparison_evidence.v1",name:<exact>,evidence:<the
  exact projection below>}`. Source notation is `basename#/JSON-pointer`; a `+`
  means every displayed pointer is consumed in displayed order. Within one
  exact-source table cell only, a later bare `#/...` inherits the immediately
  preceding explicit basename. It never inherits across cells or rows; a cell
  without a prior explicit basename is invalid.

  | # | Exact name | Exact source | Exact `evidence` projection | PASS predicate |
  |---:|---|---|---|---|
  | 1 | `c0_capture_rows_exact` | `row-file-census.json#/checkpoints/0/tables` | `{actual:[{surface:T,row_count:N}...],expected:[{surface:T,row_count:N}...]}` | `actual` projects the checkpoint's declared 28 table entries to `surface=table,row_count` in declared order; `expected` is the concatenation of the Section 6 C0 28-entry count arrays in their displayed order; their D33 bytes are equal. |
  | 2 | `c0_application_files_exact` | `row-file-census.json#/checkpoints/0/application_files` | `{actual:<file projection>,expected:<Section 6 C0 file projection>}` | The two arrays are exactly equal. |
  | 3 | `c1_gate_b_rows_atomic` | `row-file-census.json#/deltas/1/row_deltas` | `{actual:<complete row-delta array>,expected:<Section 6 C0-to-C1 row-delta array>}` | The two arrays are exactly equal, including zero entries. |
  | 4 | `c1_snapshot_file_exact` | `row-file-census.json#/deltas/1/file_deltas` | `{actual:<complete file-delta array>,expected:<Section 6 C0-to-C1 file-delta array>}` | The two arrays are exactly equal. |
  | 5 | `c2_row_deltas_exact` | `row-file-census.json#/deltas/2/row_deltas` | `{actual:<complete row-delta array>,expected:<Section 6 C1-to-C2 row-delta array>}` | The two arrays are exactly equal, including the summary updates. |
  | 6 | `c2_application_files_exact` | `row-file-census.json#/deltas/2/file_deltas` | `{actual:<complete file-delta array>,expected:<Section 6 C1-to-C2 file-delta array>}` | The two arrays are exactly equal. |
  | 7 | `summary_update_fence_exact` | `row-file-census.json#/summary_update_fence` | `{entries:<the exact two-entry fence>}` | Both complete summary diffs equal their declared `changed_keys`, with no third row or change. |
  | 8 | `c2_c3_rowsets_equal` | `row-file-census.json#/checkpoints/2/tables` + `#/checkpoints/3/tables` | `{c2:<28-entry table projection>,c3:<28-entry table projection>}` | `c2` equals `c3`. |
  | 9 | `c2_c3_application_files_equal` | `row-file-census.json#/checkpoints/2/application_files` + `#/checkpoints/3/application_files` | `{c2:<file projection>,c3:<file projection>}` | `c2` equals `c3`. |
  | 10 | `same_request_zero_mutation` | `downstream-replay-receipt.json#/same_request` + `#/authoritative_pre_replay_state_census_sha256` + `#/authoritative_post_replay_state_census_sha256` | `{same_request:<exact closed object>,pre_state_sha256:H,post_state_sha256:H}` | Disposition/status/counts/changes are exact and both state hashes are equal. |
  | 11 | `cross_run_same_i1_reuse` | `downstream-replay-receipt.json#/cross_run_sandbox` | `{cross_run_sandbox:<exact closed sandbox object>}` | Result equals the frozen same-I1 reuse result and all sandbox-local census bindings verify. |
  | 12 | `divergent_d34_conflict` | `downstream-replay-receipt.json#/divergent_sandbox` | `{divergent_sandbox:<exact closed sandbox object>}` | Result equals the frozen D34-conflict result and all sandbox-local census bindings verify. |
  | 13 | `gate_b_orphan_containment` | `row-file-census.json#/orphan_containment/gate_b` | `<the exact gate_b sibling object itself>` | The sibling, receipts, artifact set, counts, ordinals, and no-reuse assertions below all verify. |
  | 14 | `materialization_orphan_containment` | `row-file-census.json#/orphan_containment/materialization` | `<the exact materialization sibling object itself>` | The same predicate holds for `materialization`. |
  | 15 | `package_orphan_containment` | `row-file-census.json#/orphan_containment/package` | `<the exact package sibling object itself>` | The same predicate holds for `package`. |
  | 16 | `no_raw_copy_after_c0` | `row-file-census.json#/checkpoints/*/application_files` + `#/deltas/*/file_deltas` | `{checkpoints:[{name,application_files}...],deltas:[{from,to,file_deltas}...]}` | Exactly one `connector_raw` exists at every checkpoint and no post-C0 raw file is created, changed, or removed. |
  | 17 | `materializer_semantic_three_way` | `row-file-census.json#/materializer_comparison` | `{runs:[{role,materialization_semantic_sha256}...],semantic_equal}` | Roles are sandbox A/B/authoritative; all three hashes equal and `semantic_equal=true`. |
  | 18 | `materializer_physical_linkage_each` | `row-file-census.json#/materializer_comparison` | `{runs:[{role,materialization_basis_hash,materialization_record_sha256,dataset_file_bytes,dataset_file_sha256,dataset_storage_ref_hash,reopen_1_sha256,reopen_2_sha256,physical_linkage_valid}...]}` | Each run independently verifies both reopens and every record/file/basis link; no cross-run physical equality is required. |
  | 19 | `method_semantic_three_way` | `row-file-census.json#/method_comparison` | `{runs:[{role,normalized_semantic_sha256}...],semantic_equal,float_tolerance:{absolute:1e-12,relative:1e-12}}` | Roles/order/tolerance are exact, all three hashes equal, and `semantic_equal=true`. |
  | 20 | `method_artifact_rehash_each` | `row-file-census.json#/method_comparison` | `{runs:[{role,analysis_artifact_sha256,reopen_1_sha256,reopen_2_sha256,physical_linkage_valid}...]}` | Each run's two reopens equal its artifact hash and all three linkage booleans are true. |
  | 21 | `evidence_root_excluded` | `row-file-census.json#/checkpoints/*/evidence_root_excluded` | `{checkpoints:[{name:"C0",evidence_root_excluded:true},{name:"C1",evidence_root_excluded:true},{name:"C2",evidence_root_excluded:true},{name:"C3",evidence_root_excluded:true}]}` | All four exact entries are present in order and true. |

  Where a row says table/file/delta projection, it means the complete closed
  entry schemas already defined above, never a digest-only abbreviation. The
  census component separately validates every table `rowset_sha256` against its
  complete rowset preimage; `c0_capture_rows_exact` neither replaces nor aliases that hash
  check. It is the sole comparison-evidence producer. Census `status=PASS` iff
  its complete closed structure, profile membership/order, schemas, hashes,
  counts, equalities, and comparisons all validate and every `passed` value is
  true. Valid `FAIL` requires that same complete structural proof with at least
  one evaluated comparison false. A missing/extra/reordered member, malformed
  schema/hash, identity or count mismatch, unresolved comparison, incomplete C3,
  or status inconsistent with those predicates is structural no-root, never a
  catch-all census FAIL.

  The two comparison objects use the exact three-way schemas defined in Section
  6. `orphan_containment` has exactly three sibling keys in order: `gate_b`,
  `materialization`, `package`; it has no aggregate count, receipt, or backlink.
  Each sibling is exactly `{domain:<same literal>,orphan_count:N,
  contained_count:N,artifact_set_sha256:<H|null>,receipts:[...],
  reuse_allowed:false}`. Each receipt binding is exactly
  `{ordinal:P,artifact_count:P,byte_length:P,sha256:H,receipt:<closed body>}`.

  The embedded receipt body is exactly
  `{schema_id:"layer3.b1b.orphan_containment_receipt.v1",domain:<literal>,
  ordinal:P,artifacts:[...]}`. Each artifact is exactly
  `{logical_class:<domain-allowed literal>,byte_length:P,sha256:H,
  path_namespace_sha256:H,authority_status:"non-authoritative-contained"}` and
  is ordered by its D33-canonical bytes. The class map is exhaustive:
  `gate_b -> gate_b_snapshot`; `materialization ->
  dataset_version_parquet|promoted_session_snapshot`; and `package ->
  descriptive_result_artifact|pass_output_manifest|canonical_internal_package|
  user_facing_package|review_facing_package`. No source-stage, free class, or
  provenance label is persisted. Wrapper `ordinal` and `artifact_count`
  equal the embedded ordinal and artifact-array length. Wrapper `byte_length`
  and `sha256` cover only the exact D33-canonical embedded body bytes; the body
  has no wrapper, set-hash, census, comparison, or manifest backlink.

  `path_namespace_sha256` hashes exactly
  `{"lane_parent_id":T,"normalized_lane_relative_path":<relative>,"schema_id":"layer3.b1b.orphan_path_namespace.v1"}`. The relative path
  is final-handle-derived, `/`-separated, NFC, case-preserved, and has no empty,
  dot, dot-dot, drive/UNC, percent-encoded, or reparse segment. Its first segment
  is exactly `runtime`, `storage`, or `database`, never `evidence`; no raw path
  persists. No gate/materialization/package domain token enters this preimage;
  the schema ID supplies cryptographic separation from other hash schemas. The
  enclosing/receipt domain-equality rule remains separate. The containment
  scanner is sole producer.

  `artifact_set_sha256` hashes exactly
  `{schema_id:"layer3.b1b.orphan_artifact_set.v1",domain:<literal>,
  artifacts:[...]}`, where artifacts are concatenated in receipt ordinal then
  artifact order by rereading the embedded bodies, never wrapper metadata.
  Enclosing sibling `domain` equals every embedded receipt domain. The identity
  tuple `{path_namespace_sha256,byte_length,sha256}` is globally unique across
  the union of `gate_b`, `materialization`, and `package`; no artifact can be
  assigned twice even under another domain. Every artifact must resolve outside
  the evidence child and cannot be a census, receipt, verdict, stop,
  containment, aggregate, manifest, or any other evidence artifact. Receipts
  contain no global, comparison, census, receipt-set, or artifact-set backlink
  and therefore cannot self-hash or cycle.
  Across the complete containment union, domain order is `gate_b`,
  `materialization`, `package`, then D33-canonical artifact bytes within each
  domain. Ordinals are contiguous from one; empty receipts and null artifact-set hash
  occur iff both counts are zero; otherwise `orphan_count=contained_count` and
  both equal the sum of wrapper `artifact_count`, which equals the sum of
  embedded `artifacts` array lengths. Receipt/body order, counts, set hash, disjointness,
  exclusions, no cycles, and `reuse_allowed=false` are all mandatory.

  Each checkpoint `database_volume_sha256` is the D33-canonical digest of
  exactly `{"database_identity_sha256":H,"logical_bytes":N,"physical_files":[...],"profile":"<sqlite|postgresql>","schema_id":"layer3.b1b.database_volume.v1"}`.
  For SQLite, `physical_files` contains only present files in fixed
  `sqlite_main`, `sqlite_wal`, `sqlite_shm` order, each exactly
  `{logical_class:<literal>,byte_length:N,sha256:H}`, and `logical_bytes` is
  their sum. The census takes a stable database read lock and hashes each file
  through a regular non-reparse handle. For PostgreSQL, `physical_files` is
  exactly `[]` and `logical_bytes` is the nonnegative result of one
  point-in-time `pg_database_size` call for the bound isolated
  database. Free-space and volume-identity facts remain adjacent preflight or
  resource-observation fields and never enter this logical database-state digest.
  No raw path, URL, credential, or engine filename is persisted.

  Every table `rowset_sha256` is the D33-canonical digest of exactly
  `{"columns":[...],"rows":[...],"schema_id":"layer3.b1b.table_rowset.v1","table":T}`.
  `columns` is the candidate-head ORM declaration order and every entry has only
  `name`, `primary_key`, and `type`; `type` is one of `binary`, `boolean`,
  `date`, `datetime`, `decimal`, `float`, `integer`, `json`, or `string`.
  Database metadata must agree with that closed projection. Each `rows` entry is
  an array with one normalized cell per column in the same order. Null, boolean,
  integer, and exact string remain their JSON primitives; finite floats use the
  pinned CPython 3.12 D33 JSON rendering; decimal is a sign-preserving canonical
  base-10 string without exponent or redundant trailing zeros; date is
  `YYYY-MM-DD`; datetime is UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`; JSON is parsed to
  closed JSON primitives; binary is exactly `{byte_length:N,sha256:H}`.
  Nonfinite, naive datetime, undecodable, coercion-dependent, or unsupported
  cells fail. Rows are ordered by the D33-canonical bytes of their primary-key
  cell subarray; missing/duplicate primary keys fail. The checkpoint
  `row_count` equals array length.

  Every proof-created datetime is timezone-aware before persistence. An aware
  non-UTC input is converted to UTC before ORM assignment; a naive input fails.
  PostgreSQL retrieval must remain aware and is normalized to UTC before the
  exact `RFC3339Z` rowset rendering. For SQLite only, the census reads raw stored
  text only for candidate-head ORM columns declared `DateTime(timezone=True)`.
  Each nonnull value must be exactly valid `YYYY-MM-DD HH:MM:SS.ffffff` text; the
  rowset renderer replaces the one space with `T` and appends `Z`, with no parse
  tolerance, precision change, offset inference, or normalization beyond that
  operation, and only when the exact committed write witness below exists.

  Before any authoritative-database write, the proof registers its SQLAlchemy
  datetime listeners; they remain installed through accepted C3 and may be
  removed only afterward. The registry key `K` is the exact four-part tuple
  `(database_identity_sha256,table,canonical_primary_key,column)`, where
  `canonical_primary_key` is the D33-canonical bytes of that row's complete
  primary-key cell subarray. At `after_flush_postexec`, each SQLite witnessed
  value is captured in the outer transaction's pending registry as exactly
  `{flush_ordinal:P,raw_sqlite_text:<exact SQLite grammar above>,
  normalized_utc:RFC3339Z}` after proving the raw text and normalized UTC value
  correspond. Flush ordinals are contiguous from one within the outer
  transaction. A duplicate K with the same value in one flush is idempotent; an
  unequal same-flush value fails. A later flush in the same outer transaction
  replaces that pending K with its final value. Any nested transaction or
  savepoint containing a witnessed write is rejected.

  Outermost commit atomically overlays the pending entries onto a thread-safe
  registry partitioned by database identity, replacing any older committed K
  even when the value changed. Outermost rollback discards that transaction's
  pending entries and preserves the committed registry. At C3 the corresponding
  SQLite partition has exactly one final committed witness for every nonnull
  `DateTime(timezone=True)` cell in the authoritative census and no extra K; each
  witness equals the raw value and the rendered rowset UTC value. Missing, extra,
  conflicting, naive, non-UTC, bypassed, untyped-column, rollback-leaked, or
  stale-before-update witness state fails C3. The same census independently
  requires PostgreSQL aware/UTC round-trip equality; it never applies the SQLite
  raw-text rule to PostgreSQL.

  The checkpoint census component alone accumulates C0-C2 state immediately
  after expiring ORM state at each checkpoint. For a PASS final node, the one
  registered provider is the sole producer of the complete C3 checkpoint and
  the D33-canonical `row-file-census.json` buffer and file under the compound
  protocol above. It consumes only the immutable C0-C2 state and the fresh
  frozen C3 sample. The runner never produces a post-exit census, and the plugin
  never sees census bytes. The acyclic dependency is exactly frozen sample to
  census bytes to C3 binding to runner immutable C3 registry to invocation
  manifest/verdict to aggregates. The census object contains no callback, event,
  binding, self-hash, or downstream backlink.

  `database_volume_sha256` is only the checkpoint's physical database-volume
  measurement; it is excluded from authoritative state and sandbox census
  preimages and is never a replay input or alias. Table `rowset_sha256` values
  are consumed by checkpoint/delta comparison evidence. Replay receipts and
  verdicts consume the authoritative state-census hashes and the exact sandbox
  wrappers defined above, never database-volume digests. Source order,
  normalization, count, hash, or declared C2/C3 row/application-file equality
  drift fails; no raw row or database-file projection leaves the in-memory
  hasher. Database-volume digests remain boundary-local.
- `test-result.json` has exactly
  `schema_id=layer3.b1b.test_result.v1`, `profile`, `invocation_name`,
  `argv_sha256`, `collection_order`, `deselections`, `collection_errors`,
  `node_outcomes`, `counts`, `closure`, `exits`, `duration_milliseconds`, and
  `status=PASS|FAIL`. `collection_order` is the exact pre-deselection collected
  node-ID order. `deselections` is the exact ordered deselected subset.
  `collection_errors` contains only exact
  `{collector_node_id:<J|"<root>">,message_sha256:H}` objects in control-event
  order. `collection_order`, `deselections`, and every non-root collector use the
  exact validated `J` bytes from the control stream. `node_outcomes` contains at
  most one exact `{node_id:J,classification:<passed|failed|
  skipped|xfailed|xpassed|error>,terminal_phase:<setup|call|teardown>}` object for
  each executed selected node, in `collection_order` after removing
  `deselections`; an unexecuted maxfail tail is absent rather than synthesized.

  `counts` is exactly `{collected:N,selected:N,deselected:N,collection_errors:N,
  passed:N,failed:N,skipped:N,xfailed:N,xpassed:N,errors:N}`. Every value is
  nonnegative; `collected`, `deselected`, and `collection_errors` equal their
  respective array lengths, `selected = collected - deselected`, each
  classification count equals its `node_outcomes` projection, and the six
  classifications sum exactly to the node-outcome array length, which is at most
  `selected`. `closure` is exactly
  `{collection_closed:<boolean>,node_outcomes_complete:<boolean>,
  c3_required:<boolean>,c3_prepare_received:<boolean>,
  c3_prepare_acknowledged:<boolean>,c3_received:<boolean>,
  c3_acknowledged:<boolean>,
  provider_disposition:<not_applicable|not_registered|discarded|consumed>,
  terminal_received:<boolean>,terminal_acknowledged:<boolean>,
  final_cadence_received:<boolean>,final_cadence_linked:<boolean>,
  cadence_emitter_joined:<boolean>,pipe_eof_after_final_cadence:<boolean>,
  process_exit_observed:<boolean>,exit_within_1000_milliseconds:<boolean>}`.
  `c3_required` is true exactly for the SQLite- and PostgreSQL-authorized
  invocations and false for default invocations. Default has all four C3
  booleans false and `provider_disposition="not_applicable"`; it may PASS or
  validly FAIL because of another predicate. Authorized success has all four C3
  booleans true and `provider_disposition="consumed"`. An authorized orderly
  early FAIL has all four false and either `not_registered` when the final node
  was never entered or `discarded` after the exact
  `REGISTERED -> DISCARDED` transition. It is valid only when independently
  grounded by at least one collection error, failed/error node, exact selected-
  set mismatch, maxfail-truncated execution prefix, or mutually equal nonzero
  pytest/process exits. Missing C3 without one of those facts is no-root. A
  consumed provider with all four C3 booleans true may still yield valid FAIL
  from an independent later semantic predicate. Any partial/mixed C3 booleans,
  disposition/state mismatch, or intermediate provider state is structural
  no-root. Terminal event and test closure dispositions must be exactly equal.
  `node_outcomes_complete` is true iff the outcome node-ID projection equals
  every selected node in order. `exits` is exactly
  `{pytest:<integer>,process:<integer>}`. `duration_milliseconds` equals the
  actual-exit process-ledger wall value.

  PASS requires complete structural closure, the profile-appropriate provider
  state above, no collection error;
  `failed=0`, `xfailed=0`, `xpassed=0`, and `errors=0`; the skipped node-
  ID projection exactly equal to the selected manifest invocation's ordered
  `expected_skips`; `deselections` exactly equal to `expected_deselections`; both
  exits zero and mutually equal; exact terminal receipt/ACK, final-cadence
  receipt/linkage, emitter join, EOF, and bounded-tail exit ordering; and every
  other structural and semantic invariant. A valid FAIL requires the same exact
  collection/deselection/error/outcome arrays and counts, executed-prefix rule,
  profile/provider partition, terminal/final-cadence/EOF/physical-exit closure,
  and mutually equal exits, plus at least one evaluated semantic predicate false.
  A malformed array/count, exit disagreement, missing tail/cleanup, partial C3,
  unresolved provider state, or merely absent evidence is no-root, not FAIL. A
  missing expected skip or
  deselection is as invalid as an unexpected one. Raw pytest output, duplicate
  phase-report arrays, traceback/reason text, and parser-derived console counts
  are forbidden.
  `argv_sha256` is the D33-canonical SHA-256 of exactly
  `{"argv":<the selected Section 16 symbolic array>,"invocation_name":T,"profile":"<sqlite|postgresql>","schema_id":"layer3.b1b.argv.v1"}`.
  The runner is the sole producer from the selected closed manifest entry;
  `argv` retains symbolic `python` at element zero. It must equal the `argv`
  array embedded in that invocation's `expected_command_sha256` preimage and the
  test-result digest. Substitution of the already hashed verified interpreter is
  an execution step, not a second argv preimage. A different order, option,
  node, profile/name, extra argument, or digest fails before launch or makes the
  result FAIL.
- `postgresql-proof-receipt.json` has exactly
  `schema_id=layer3.b1b.postgresql_proof_receipt.v1`, `profile`,
  `invocation_name`, `database_identity_sha256`, `cases`, `gate_results`, and
  `status=PASS|FAIL`. `cases` contains
  the exact ten Section 10 entries in fixed case/node order. Each entry is exactly
  `{case_id:<fixed literal>,node_id:<fixed J>,scope:<null|closed scope>,
  facts:<null|case-specific closed facts>,cleanup:<null|closed cleanup>,
  status:<PASS|FAIL|NOT-RUN>}`. `gate_results` contains exactly
  `{gate:<migration|concurrency|lock_timeout|corrupt_basis|rollback>,
  status:<PASS|FAIL|NOT-RUN>}` in that order and uses only the fixed case mapping
  below. No census hash or future-evidence backlink is present.

  Receipt `PASS` requires all ten cases PASS. Receipt `FAIL` requires an exact
  PASS prefix, one FAIL, and a NOT-RUN suffix; a NOT-RUN case has null scope,
  facts, and cleanup and no outcome/event. Gate status is PASS iff every mapped
  case is PASS, FAIL iff at least one mapped case is FAIL, and otherwise NOT-RUN
  iff no mapped case failed and at least one is NOT-RUN. A receipt, case, or gate
  order/count/schema/identity/cleanup/event/status mismatch is structural no-root.
  No database URL, credential, raw exception, free case name, or summary digest
  may substitute for the exact case evidence.

Manifest order is a canonical sort contract, not physical write order. Every
worker evidence manifest is written last inside the evidence child and has exactly
`schema_id=layer3.b1b.evidence_manifest.v1`, `profile`, `invocation_name`,
`status`, `phase`, `test_terminal`, `file_count`, `evidence_bytes`,
`manifest_reserve_bytes=65536`, `profile_bounded_bytes`,
`control_accounting`, `finalization_free_space`, `files`, and `file_order_sha256`.
`control_accounting` is exactly
`{attempt_id:H,attempt_intent_byte_length:P,attempt_intent_sha256:H,
attempt_closeout_reserve_bytes:262144}` and exactly equals preflight attempt and
the reopened intent.
`finalization_free_space` is exactly
`{evidence_volume_identity_sha256:H,min_volume_free_bytes:4294967296,
observations:[...],status:"PASS"}`. Each observation is exactly
`{ordinal:P,next_basename:T,free_bytes_before_write:N,
projected_write_bytes:P,manifest_reserve_bytes:<65536|0>}`. Nonmanifest
observations use reserve `65536`; the final-manifest observation alone uses `0`.
Both top-level PASS and top-level FAIL manifests require the nested status to be
exactly `PASS`. A finalization-space failure creates no accepted manifest or
invocation root. Each file binding is exactly
`{ordinal:P,basename:<frozen>,byte_length:P,sha256:H}`;
`files`, `file_count`, and `evidence_bytes` are self-excluding;
`file_count` equals array length, `evidence_bytes` is the binding byte-length
sum, and `file_order_sha256` hashes the complete canonical binding array.
`profile_bounded_bytes` is exactly
`resource-ledger.maxima.profile_local_bytes + evidence_bytes +
manifest_reserve_bytes + control_accounting.attempt_intent_byte_length + 262144`
and must be at most `1073741824`. This deliberately uses the complete observation
high-water, not the terminal subtotal, and reserves actual intent plus maximum
closeout exactly once. That literal is the universal cap. For a launched
authorized profile only, it must also be at most the equal reopened
`pass-to-launch.runtime.max_profile_bounded_bytes`; a default or authorized
preflight-only aggregator has no PASS-TO-LAUNCH input or dereference. No local
PostgreSQL database-child bytes are
added to the already counted PostgreSQL database size. Evidence membership still
excludes both lane-parent controls; accounting does not.

Worker resource closure is temporal and fail closed. For `test_terminal=true`,
the resource ledger's PASS/FAIL status covers every recorded component,
arithmetic equality, cadence/boundary, high-water, memory, volume-free, process-
tree, duration, and terminal threshold through linked final cadence and actual
Python-target-exit wall closure. For the preflight-only tuple it instead covers
the exact two persisted sole-runner samples/observations, zero target wall, and
preflight-handle closure. It excludes controller RSS and later worker evidence
finalization. The
controller independently samples its own RSS plus the complete Job, queries
homogeneous controller/Job private-commit peaks, and closes control storage
through physical worker exit; it persists those facts only in
`attempt-closeout.json`.
The worker ledger measures evidence files present at each observation but cannot
predict evidence written after it, so it cannot by itself establish the final
profile cap. On a launched path, preflight and mid-run evidence files are written
once into the unfinalized evidence child and become immutable immediately, but
their presence is not PASS; the worker accounts their actual handle-read byte
lengths. On the preflight-only path both observations precede all evidence, so
their current-evidence values are exactly zero and later failure finalization is
bounded only by the sequential checks below.

On a prospective success path, provider-published `row-file-census.json` is
closed, reopened, and accepted at C3 before terminal. After the accepted terminal/
final-cadence handshake, pipe closure, and actual Python-child exit, the worker
physically closes/writes process ledger, resource ledger, endpoint ledger,
PostgreSQL proof receipt when applicable, then `test-result.json`, then the
invocation verdict and manifest; SQLite's already-applicable primitive/receipt
objects and integrated verdict retain their declared dependency order. Census is
only rebound during finalization and is never produced or rewritten after exit.
The test result is the end of child/application evidence. The worker holds no
more than one D33-canonical object buffer at a time.

Immediately before every physical post-runtime-closure evidence write, after
target exit when launched or exact preflight-only sample/handle closure otherwise,
the worker revalidates the evidence-volume identity against preflight and records
the next
contiguous `finalization_free_space.observations` entry. For a nonmanifest write,
`projected_write_bytes` is that exact pre-rendered byte length,
`manifest_reserve_bytes=65536`, and the worker resamples the canonical evidence
volume and requires free bytes at least
`4294967296 + projected_write_bytes + 65536 + 262144`. Intent is already on disk
and is not added again to free-space demand. It proves exactly
`resource-ledger.maxima.profile_local_bytes + <already-written nonmanifest
evidence bytes> + projected_write_bytes + 65536 +
control_accounting.attempt_intent_byte_length + 262144 <= 1073741824`, where the
already-written term is the reopened byte sum and
`projected_write_bytes` is only the current exact draft. It does not render,
precompute, or retain any future dependent draft. It records the current draft
length/hash, writes it once in dependency order, reopens it by handle, forbids
overwrite/removal/substitution, and releases that sole canonical buffer before
drafting the next object. Every later write repeats the complete procedure.

Once every self-excluding binding and preceding free-space observation is known,
the worker proves
`resource-ledger.maxima.profile_local_bytes + evidence_bytes + 65536 +
control_accounting.attempt_intent_byte_length + 262144 <= 1073741824`, resamples
the same canonical evidence volume, and requires free bytes at least
`4294967296 + 65536 + 262144`. It adds the final observation with
`next_basename="evidence-manifest.json"`, `projected_write_bytes=65536`, and
`manifest_reserve_bytes=0`, then pre-renders the complete canonical manifest in
the sole buffer. Its actual byte length must be at most `65536`. The nested status
remains exact `PASS` only when every observation has the exact next basename,
identity, projection, conditional reserve, and minimum-volume-free result. The
worker writes the exact manifest last, reopens it by handle, emits no later
evidence write, closes its remaining worker-owned handles, and exits. Thus the
manifest and closeout reserves bound worker profile high-water, final evidence,
exact intent, and future closeout, while the controller remains able to sample
the complete Job through worker exit.

Before treating a worker manifest as a candidate attempt input, the profile
aggregator reopens the
resource ledger, every listed member, and the manifest, recomputes every member
length/hash, requires the actual manifest length at most its exact reserve,
proves exact evidence-child membership, verifies every ordered finalization-
space observation, recomputes `profile_bounded_bytes` from the resource
high-water, verifies `control_accounting` against preflight and exact reopened
intent bytes, reproduces each sequential current-draft check and the final
complete-evidence check, and rechecks the cap. A projected cap/space breach, evidence-
volume identity drift, observation bypass, non-PASS nested status, or oversize
pre-render creates no accepted/finalized invocation root. Provisional bytes
remain outside the evidence DAG for
external containment/recovery; the worker must not rewrite the closed resource
ledger, synthesize a second profile-cap gate, or manufacture a closed FAIL root.
Even a structurally valid worker manifest remains provisional until the
aggregator separately validates the exact intent and `CONTAINED` closeout,
reopens the closeout-bound same manifest, and constructs the v2 attempt binding.

If postwrite reopen finds a byte, member, arithmetic, reserve, or cap mismatch,
the physical immutable manifest and other bytes remain retained but the root is
invalid and unaccepted in external containment. They are never described as
nonexistent, and no downstream PASS may consume them. Closed FAIL manifests use
the same `manifest_reserve_bytes=65536`, exact `control_accounting`, closeout
reserve, high-water cap arithmetic,
`finalization_free_space.status="PASS"`, observations, pre-render, write-last,
reopen, retained-invalid, and no-downstream-PASS rules. A closed FAIL root is
valid only when already bound immutable evidence supports one explicit
phase/terminal tuple below and every membership/hash/resource/control-accounting
check passes.

The three successful manifest orders are exhaustive:

- `sqlite_default`: six bound files, seven total files, and five invocation-
  verdict evidence inputs: `preflight.json`, `process-ledger.json`,
  `resource-ledger.json`, `endpoint-ledger.json`, `test-result.json`,
  `invocation-verdict.json`; phase is `preflight`, `test_terminal=true`.
- `sqlite_authorized`: thirteen bound files, fourteen total files, and twelve
  invocation-verdict evidence inputs: `preflight.json`, `pass-to-launch.json`,
  `launch-claim.json`, `process-ledger.json`, `resource-ledger.json`,
  `endpoint-ledger.json`, `package-postclose-rehash.json`,
  `handoff-delivery-receipt.json`, `downstream-replay-receipt.json`,
  `row-file-census.json`, `test-result.json`,
  `b1b-integrated-run-verdict.json`, `invocation-verdict.json`; phase is
  `final`, `test_terminal=true`.
- `postgresql_authorized`: ten bound files, eleven total files, and nine
  invocation-verdict evidence inputs: `preflight.json`, `pass-to-launch.json`,
  `launch-claim.json`, `process-ledger.json`, `resource-ledger.json`,
  `endpoint-ledger.json`, `row-file-census.json`,
  `postgresql-proof-receipt.json`, `test-result.json`,
  `invocation-verdict.json`; phase is `post-census`,
  `test_terminal=true`.

For the integrated SQLite verdict, ordinals 7-9 are its three
`outcome_receipts`; ordinals 1-6 and 10-11 are its eight `control_evidence`
bindings. The integrated verdict itself remains distinct from the invocation
verdict.

Failure membership is governed by two axes: `phase` and `test_terminal`. Start
with the phase contribution, union the terminal contribution, sort the union by
that profile's successful manifest order, then append
`invocation-verdict.json`, `stop.json`, and `containment.json`; the manifest is
written last and excludes itself. `test_terminal=false` contributes nothing.
`test_terminal=true` contributes the all-or-none four-file membership set
`process-ledger.json`, `resource-ledger.json`, `endpoint-ledger.json`, and
`test-result.json`. The all-or-none rule is a finalized-root membership invariant, not
a claim of atomic filesystem writes: each member is written once and reverified
in dependency order. A crash or partial write leaves provisional evidence only
and creates no finalized invocation root, invocation verdict, stop,
containment, or manifest. The controller may still write `BARRED_UNKNOWN`; a
missing/torn closeout leaves the orphan-intent bar. Neither case may produce a
profile verdict or invoke an in-spec recovery path.

Phase contributions are exact. Every profile's `preflight` phase contributes
`preflight.json` followed by `resource-ledger.json`. For a valid
`preflight/false,test_terminal=false` result, the worker first builds the complete
preflight object in memory while accepting resource observation/sample one. Once
that object deterministically evaluates FAIL, it creates no target, cadence
emitter, or process ledger; it takes fresh terminal observation/sample two. A
PostgreSQL profile uses its already retained read-only host connection for that
terminal measurement and then closes it. The worker closes every remaining
preflight input/measurement handle before writing either evidence file. The
single-cause fixture vectors are exact. For `sqlite_default`, a complete fixed
F07/C01 projection with only `reverified=false` produces preflight FAIL,
`phase=preflight`, `test_terminal=false`, `authority=FAIL`,
`environment=PASS`, `roots=PASS`, `processes=NOT-RUN`, `resources=PASS`,
`endpoints=PASS`, `tests=PASS`, invocation FAIL, and five bound/six physical
files. For either authorized profile, the analogous complete negative produces
`fixture=FAIL`; preflight authority/environment/roots/resources/endpoints/tests
are PASS, launch/processes and every post-launch gate are NOT-RUN, and the same
preflight/false, resource-PASS, invocation-FAIL, five-bound/six-physical closure
applies. Fixed-field/content/path/readability/identity/incomplete fixture state
is no-root, and no gate duplicates or cross-routes either profile's fixture
result. When `test_terminal=true`, the
terminal union contains the same resource ledger and deduplicates it by exact
basename/binding; it never creates a second ledger. SQLite `launched` adds
PASS-TO-LAUNCH and launch claim; `post-package`, `post-handoff`, and
`post-replay` cumulatively add their one correspondingly named receipt;
`post-census` adds row/file census; `final` adds the integrated verdict.
PostgreSQL semantic phases are exactly `preflight -> launched ->
post-postgresql-proof -> post-census`. `launched` adds PASS-TO-LAUNCH and launch
claim; `post-postgresql-proof` adds the PostgreSQL receipt after the ten-case
phase closes; `post-census` adds row/file census after final C0-C3. Physical
post-exit write order remains ledgers, receipt, test result, verdict, stop/
containment on FAIL, then manifest; semantic phase names record completed runtime
milestones rather than file-write chronology. There is no `post-test` phase and
no duplicate default or PostgreSQL `final` alias.

The only valid failure tuples and manifest `file_count` values are:

| Profile | `phase` | `test_terminal` | `file_count` |
|---|---|---:|---:|
| `sqlite_default` | `preflight` | `false` | 5 |
| `sqlite_default` | `preflight` | `true` | 8 |
| `sqlite_authorized` | `preflight` | `false` | 5 |
| `sqlite_authorized` | `launched` | `true` | 10 |
| `sqlite_authorized` | `post-package` | `true` | 11 |
| `sqlite_authorized` | `post-handoff` | `true` | 12 |
| `sqlite_authorized` | `post-replay` | `true` | 13 |
| `sqlite_authorized` | `post-census` | `true` | 14 |
| `sqlite_authorized` | `final` | `true` | 15 |
| `postgresql_authorized` | `preflight` | `false` | 5 |
| `postgresql_authorized` | `launched` | `true` | 10 |
| `postgresql_authorized` | `post-postgresql-proof` | `true` | 11 |
| `postgresql_authorized` | `post-census` | `true` | 12 |

Each `file_count` is the self-excluding bound-member count. Thus every
`preflight/false` root has five bound members and six physical files including
its manifest; the `5/10/11/12` PostgreSQL failure sequence is unchanged.

Failure physical orders are exact. After the in-memory/two-observation/handle-
closure sequence above, `preflight/false` writes preflight, resource ledger,
invocation verdict, stop, containment, then manifest. `launched/true`, after
physical target/descendant exit and worker-handle closure, is process ledger,
resource ledger, endpoint ledger, test result, invocation verdict, stop,
containment, manifest, with preflight/launch files already closed.
`post-postgresql-proof/true` inserts the PostgreSQL receipt before test result.
`post-census/true` has the census already closed at C3 and uses ledgers, receipt,
test result, invocation verdict, stop, containment, manifest. Any skipped,
reordered, duplicated, or later-phase write is no-root.

An authorized `preflight/true` tuple is invalid; every authorized phase at or
after `launched` with `test_terminal=false` is invalid. PASS-TO-LAUNCH and launch
claim are both present or both absent, and phase chains cannot skip. The child
and every application/runtime action end at `test-result.json`; no child,
database, package, handoff, replay, census, or other application phase may start
after that boundary. No terminal root is finalized while the child is running.
No profile root is created before physical worker exit and a valid
intent/worker-manifest/`CONTAINED`-closeout binding.
After the complete four-file terminal membership set is closed, the sole
permitted SQLite transition is the worker's evidence-only finalization from
`post-census/true` to `final/true`: it writes the integrated verdict, then the
invocation verdict, then the manifest under the dependency/resource rules
above. That transition is not a child/runtime/application phase. Default and
PostgreSQL likewise write only their verdict and manifest after their terminal
set; they gain no `final` phase alias. The integrated verdict exists only for
SQLite `final/true`, after post-census and all three outcome receipts.

`stop.json` is exactly
`{schema_id:"layer3.b1b.stop.v1",status:"FAIL",profile:<exact>,phase:<exact>,
test_terminal:<boolean>,completed_evidence_order_sha256:H,
stopped_at:RFC3339Z}`. Its order hash is the D33-canonical SHA-256 of
exactly `{"completed_evidence":[...],"phase":<exact>,"profile":<exact>,
"test_terminal":<boolean>,"schema_id":"layer3.b1b.completed_evidence_order.v1"}`.
The array contains the complete bindings before the invocation verdict in
manifest order. The worker is the sole producer; the stop, invocation verdict,
and FAIL manifest consume the same profile/phase/terminal model. Stop has no free
error taxonomy: the exact exhaustive invocation gate array and completed evidence
bindings identify every evaluated failure.

`containment.json` has exactly
`{schema_id:"layer3.b1b.containment.v1",attempt_id:H,profile:<exact>,
phase:<exact>,test_terminal:<boolean>,artifacts:[...],
row_file_census_sha256:<H|null>,endpoint_ledger_sha256:<H|null>,
resource_ledger_sha256:<H|null>,reuse_allowed:false}`. Every artifact entry is
exactly `{domain:<gate_b|materialization|package>,
logical_class:<domain-allowed literal>,path_namespace_sha256:H,byte_length:P,
sha256:H,authority_status:"non-authoritative-contained"}`. The exact class map,
path-namespace preimage, global uniqueness, and domain-then-D33 order are the
orphan-receipt rules above. On a launched path, the worker scanner is sole
producer after physical target/descendant exit and process/handle closure; it
exhaustively records every non-authoritative application artifact outside the
evidence child. On the preflight-only path there is no target or application act;
the scanner runs only after both resource observations and every preflight
input/measurement handle close, and `artifacts=[]` is mandatory. That tuple has
`resource_ledger_sha256=H` and null row-census and endpoint-ledger hashes. In all
other tuples each sibling hash is `H` iff that exact evidence file is a completed
member; otherwise it is null. No empty/future ledger is implied.

A live target or descendant permits no worker root or worker-written containment;
only the outer controller may perform its separately specified physical custody
and closeout. For a valid worker FAIL root, write order is invocation verdict,
then stop, then containment, then the self-excluding manifest; the still-live
worker writes only those evidence objects after applicable launched-target or
preflight-only closure, and the outer controller later proves worker exit. The
FAIL manifest binds only the sorted
phase/terminal union plus invocation verdict, stop, and containment, has the
tuple's exact `file_count`, and excludes itself. No other root file is permitted.

Evidence aggregation is deliberately three-layered; no invocation may claim a
later profile, CI, review, merge, or records event:

1. **Worker-invocation/profile layer.** These are the three SUCCESSFUL-root layouts
   only. A `sqlite_default` SUCCESSFUL root contains exactly `preflight.json`, `process-ledger.json`,
   `resource-ledger.json`, `endpoint-ledger.json`, `test-result.json`,
   `invocation-verdict.json`, and `evidence-manifest.json`; it has no production
   PASS-TO-LAUNCH file because the bridge is false and no B1b write is allowed.
   The `sqlite_authorized` SUCCESSFUL root uses the exact thirteen-file successful order
   above plus its manifest; its integrated-run verdict is a bound input to its
   distinct invocation verdict.
   The `postgresql_authorized` SUCCESSFUL root contains exactly `preflight.json`,
   `pass-to-launch.json`, `launch-claim.json`, the three ledgers, `row-file-census.json`,
   `postgresql-proof-receipt.json`, `test-result.json`, `invocation-verdict.json`, and
   `evidence-manifest.json`. The PostgreSQL receipt binds migration upgrade/
   rollback, both transaction-order races, timeout, corrupt-basis, and rollback
   facts. Failure roots use only the already-defined exact phase/terminal union
   and never inherit these SUCCESSFUL-root layouts. Every invocation verdict has exactly
   `schema_id=layer3.b1b.invocation_verdict.v1`, `profile`, `invocation_name`,
    `candidate_head_sha`, `status=PASS|FAIL`, `completed_gate_results`,
    `evidence_bindings`, and `nonclaims`; it can claim only facts executed in that
    worker root. It cannot claim controller custody, physical worker exit,
    control-file validity, or profile completion. Its `nonclaims` array is the
    seven package/data limitations followed by the five Section 15 custody
    nonclaims. Each gate result is exactly
    `{gate:T,status:<PASS|FAIL|NOT-RUN>}` and
   each binding is exactly `{ordinal:P,basename:T,byte_length:P,sha256:H}` in
   manifest order. For `sqlite_authorized`, the binding set includes the
   integrated-run verdict; the two verdict schemas remain distinct.

   `completed_gate_results` is a legacy field name but its array is always
   exhaustive. Membership and order are fixed by profile:

   - every `sqlite_default` invocation uses
     `["authority","environment","roots","processes","resources","endpoints","tests"]`;
   - `sqlite_authorized` uses
     `["authority","environment","roots","launch","processes","endpoints","fixture","census","rows","files","sqlite_concurrency","materializer_three_way","method_three_way","package_transaction","no_leak","reviews","handoff","replay","resources","tests","integrated_consistency"]`;
   - `postgresql_authorized` uses
     `["authority","environment","roots","launch","processes","endpoints","fixture","census","rows","files","migration","postgresql_concurrency","lock_timeout","corrupt_basis","rollback","resources","tests"]`.

   Every entry has exactly `gate` and `status`. A gate is `PASS` exactly when all
   declared dependencies are present, structurally valid, and its predicate is
   true. It is `FAIL` exactly when all required evidence for that evaluated gate
   is structurally valid and at least one predicate is false. `NOT-RUN` is allowed
   only when a valid earlier phase stop makes a later-phase dependency absent;
   unreadable, malformed, hash/identity-mismatched, ambiguous, or status-
   inconsistent evidence is structural no-root, not FAIL or NOT-RUN. Evaluation
   continues across independent present dependencies, retaining every independent
   FAIL. Invocation PASS requires every fixed entry PASS. Invocation FAIL requires
   at least one evaluated FAIL, the exact exhaustive fixed array, permitted
   NOT-RUN positions, and exact phase/evidence/terminal closure. Missing, extra,
   duplicate, reordered, prefix-only, synthetic-failure, or absent-gate arrays
   are invalid.

   The dependency map is exhaustive; `#` denotes the complete JSON document and
   `+` joins required projections in displayed order under the same cell-local
   bare-pointer inheritance rule above. A source of the form
   `comparisons[name="T"]` selects exactly one member from
   `row-file-census.json#/comparisons` after that profile's exact applicable
   membership and order have already validated. Zero matches, multiple matches,
   extra membership, or name-order drift fails before predicate evaluation.
   Numeric comparison indices are never authority.

   | Profile(s) | Gate | Exact evidence source | PASS predicate |
   |---|---|---|---|
   | `sqlite_default` | `authority` | `preflight.json#/authority_sha256` + `#/fixture` | The preflight hash equals the exact D33 authority object, every fixed F07/C01 fixture field is exact, and `reverified=true`. The authority hash/preimage is unchanged and does not absorb the fixture projection. |
   | authorized | `authority` | `preflight.json#/authority_sha256` + launched-authorized-only `pass-to-launch.json#/authority` | The preflight hash equals the exact D33 authority object; if PASS-TO-LAUNCH is present, its complete authority projection is equal. Preflight-only failure consumes no nonexistent attestation. |
   | all | `environment` | `preflight.json#/environment` + launched-authorized-only `pass-to-launch.json#/runtime` | Every direct preflight environment predicate passes; if PASS-TO-LAUNCH is present, every Section 9 environment/runtime equality also holds. |
   | all | `roots` | `preflight.json#/roots` + launched-authorized-only `pass-to-launch.json#/runtime` | Parent and all four child IDs/hashes, root-binding hash, DB identity, absence, direct-child, disjoint/nonancestor, and no-reparse facts pass; if PASS-TO-LAUNCH is present, its root projection is equal. |
   | authorized | `launch` | `pass-to-launch.json#` + `launch-claim.json#` | Both statusless closed records have their exact schemas and fields; all authority/runtime/nonce/claim/hash equalities and launch invariants pass. |
   | all | `processes` | launched-only `process-ledger.json#` | If launched, the statusless ledger has its closed schema; worker/target identities, one launch, exact quiescent-boundary resource-sample pairing, observational maxima equality, physical target/descendant exit, worker-owned handle closure, and `0 <= wall <= attempt` verify. A preflight-only root has no process ledger, grants no launch claim, and records this gate as `NOT-RUN`. This gate enforces no RSS/process/wall/attempt cap; controller custody is not this gate. |
   | all | `resources` | `preflight.json#/resources` + `#/process_census` + `#/postgresql_storage_binding` + `resource-ledger.json#` | Preflight minima, exact zero competing-process census/count, zero-projection actual cap, and applicable PostgreSQL isolation/storage sufficiency pass and the closed worker ledger is PASS. If launched, cheap cadence, quiescent-boundary process-sample pairing, linked final cadence, target exit/wall, observational maxima, and applicable C3/PostgreSQL facts verify. If preflight-only, the exact nonnull sole-runner/two-observation branch, zero wall/projection/current-evidence, handle closure, and null process ledger verify. Outer sampled resources, hard Job accounting, private commit, control storage, and physical worker exit remain v2 profile predicates. |
   | all | `endpoints` | `preflight.json#/endpoint_policy` + `#/postgresql_storage_binding` + `resource-ledger.json#` + launched-only `endpoint-ledger.json#` | Preflight policy is exact, local, and zero-egress. SQLite preflight-only performs zero database connection and has no endpoint ledger. PostgreSQL preflight-only uses exactly one approved same-endpoint unpooled read-only runner host connection, performs no reconnect or pooling, reuses it for the terminal database-size read, closes it before evidence, and has no target/child event, monitor/provider/application connection, or endpoint ledger; its endpoint/storage identity and closure agree with the preflight binding and resource-ledger hash/status. If launched, the closed endpoint ledger's hash, ordinals/counts, local closure, PostgreSQL controls/provider ordinal, endpoint, and storage sibling verify unchanged. |
   | all | `tests` | `preflight.json#/test_manifest_sha256` + launched-only `test-result.json#` | The frozen manifest selection/node/order and digest pass. If launched, the closed result's collection/outcome/provider/C3/tail/exit/wall/argv facts match it; a preflight-only root has no test result. |
   | authorized | `fixture` | `preflight.json#/fixture` | The fixture equals F07/C01 and `reverified=true`; the integrated verdict copies this projection without becoming its own dependency. |
   | SQLite authorized | `census` | `row-file-census.json#` | Census status is PASS; its exact 21-name array is exhaustive, unique, ordered, and all true; the summary fence, all three orphan comparisons, and evidence-root exclusion are included. |
   | PostgreSQL authorized | `census` | `row-file-census.json#` | Census status is PASS; its exact 14-name array is exhaustive, unique, ordered, and all true; both three-way comparison fields are null; the summary fence, all three orphan comparisons, and evidence-root exclusion are included. |
   | SQLite authorized | `rows` | `comparisons[name="c0_capture_rows_exact"]` + `comparisons[name="c1_gate_b_rows_atomic"]` + `comparisons[name="c2_row_deltas_exact"]` + `comparisons[name="c2_c3_rowsets_equal"]` + `comparisons[name="same_request_zero_mutation"]` + `comparisons[name="cross_run_same_i1_reuse"]` + `comparisons[name="divergent_d34_conflict"]` | All seven exact row/replay comparison objects are present and passed. |
   | PostgreSQL authorized | `rows` | `comparisons[name="c0_capture_rows_exact"]` + `comparisons[name="c1_gate_b_rows_atomic"]` + `comparisons[name="c2_row_deltas_exact"]` + `comparisons[name="c2_c3_rowsets_equal"]` | All four exact row comparison objects are present and passed. |
   | authorized | `files` | `comparisons[name="c0_application_files_exact"]` + `comparisons[name="c1_snapshot_file_exact"]` + `comparisons[name="c2_application_files_exact"]` + `comparisons[name="c2_c3_application_files_equal"]` + `comparisons[name="no_raw_copy_after_c0"]` + `comparisons[name="evidence_root_excluded"]` | All six exact file/exclusion comparison objects are present and passed. |
   | SQLite authorized | `sqlite_concurrency` | `test-result.json#` | The exact SQLite concurrency nodes selected by its Section 16 argv passed with no unexpected skip/deselection. |
   | SQLite authorized | `materializer_three_way` | `comparisons[name="materializer_semantic_three_way"]` + `comparisons[name="materializer_physical_linkage_each"]` | Both exact comparison objects passed. |
   | SQLite authorized | `method_three_way` | `comparisons[name="method_semantic_three_way"]` + `comparisons[name="method_artifact_rehash_each"]` | Both exact comparison objects passed. |
   | SQLite authorized | `package_transaction` | `package-postclose-rehash.json#` + `comparisons[name="package_orphan_containment"]` | The statusless package record's complete closed schema and all three rehash invariants verify, and package orphan containment passed. |
   | SQLite authorized | `no_leak` | `comparisons[name="gate_b_orphan_containment"]` + `comparisons[name="materialization_orphan_containment"]` + `comparisons[name="no_raw_copy_after_c0"]` + `comparisons[name="evidence_root_excluded"]` + `test-result.json#` | Both applicable non-package orphan checks, raw/evidence-root exclusions, and exact no-leak/redaction nodes pass. |
   | SQLite authorized | `reviews` | `comparisons[name="summary_update_fence_exact"]` + `row-file-census.json#/summary_update_fence` + `test-result.json#` | The named comparison is PASS, the exact two-row fence verifies, and four-way review plus replay/conflict tests pass. |
   | SQLite authorized | `handoff` | `handoff-delivery-receipt.json#` | The statusless closed receipt has its complete schema and verifies prepare/delivery equality and exact state-census aliases. |
   | SQLite authorized | `replay` | `downstream-replay-receipt.json#` | The statusless closed receipt has its complete schema; same-request/cross-run/divergent results and all state/sandbox census bindings verify. |
   | SQLite authorized | `integrated_consistency` | `b1b-integrated-run-verdict.json#` + `preflight.json#/candidate_head_sha` + the invocation evaluator's twenty primitive gate results | Integrated `candidate_head_sha`, profile, and invocation name equal the invocation values; integrated verdict is PASS; and all twenty integrated gate names/statuses exactly equal the first twenty invocation gate names/statuses. No invocation or manifest bytes feed the integrated record. |
   | PostgreSQL authorized | `migration` | `postgresql-proof-receipt.json#` | Closed receipt identity equals preflight; the exact `migration` gate result and case 1 are PASS; re-upgrade leaves the database at head before bridge proof. No census backlink is consumed. |
   | PostgreSQL authorized | `postgresql_concurrency` | `postgresql-proof-receipt.json#` | Closed receipt identity equals preflight and the exact `concurrency` gate result plus cases 2, 3, 4, 6, and 7 are PASS. |
   | PostgreSQL authorized | `lock_timeout` | `postgresql-proof-receipt.json#` | Closed receipt identity equals preflight and the exact `lock_timeout` gate result plus case 5 are PASS. |
   | PostgreSQL authorized | `corrupt_basis` | `postgresql-proof-receipt.json#` | Closed receipt identity equals preflight and the exact `corrupt_basis` gate result plus case 8 are PASS. |
   | PostgreSQL authorized | `rollback` | `postgresql-proof-receipt.json#` | Closed receipt identity equals preflight and the exact `rollback` gate result plus cases 9 and 10 are PASS. |

   Successful `evidence_bindings` order is also exact. `sqlite_default` binds
   `preflight.json`, `process-ledger.json`, `resource-ledger.json`,
   `endpoint-ledger.json`, `test-result.json`. `sqlite_authorized` binds
   `preflight.json`, `pass-to-launch.json`, `launch-claim.json`,
   `process-ledger.json`, `resource-ledger.json`, `endpoint-ledger.json`,
   `package-postclose-rehash.json`,
   `handoff-delivery-receipt.json`, `downstream-replay-receipt.json`,
   `row-file-census.json`, `test-result.json`,
   `b1b-integrated-run-verdict.json`. `postgresql_authorized` binds
   `preflight.json`, `pass-to-launch.json`, `launch-claim.json`,
   `process-ledger.json`, `resource-ledger.json`, `endpoint-ledger.json`,
   `row-file-census.json`, `postgresql-proof-receipt.json`, `test-result.json`.

   On failure, bindings are exactly the permitted two-axis union before the
   invocation verdict, sorted in successful manifest order. Every invocation
   verdict excludes itself, `stop.json`,
   `containment.json`, `evidence-manifest.json`, incomplete/later-phase files,
   aggregate files, and future bindings. The worker derives both arrays from the
   frozen profile contract; any omission, addition, reorder, duplicate, self-
   binding, or gate/evidence inconsistency makes the invocation verdict invalid.

   Each profile aggregator owns a new absent profile-aggregate root containing
   only `profile-verdict.json` and `aggregate-manifest.json` on success. The
   profile verdict is the first full-custody authority and has exactly
   `schema_id=layer3.b1b.profile_verdict.v2`, `profile`,
   `candidate_head_sha`, `status=PASS|FAIL`, `expected_invocations`,
   `completed_invocations`, `attempts`, `gate_results`, and `nonclaims`.
   `layer3.b1b.profile_verdict.v1`, an alias, fallback, compatibility reader,
   migration, or inferred v2 object is invalid and produces no aggregate root.
   `expected_invocations` is the Section 16 order (five names for
   `sqlite_default`, one for each authorized profile); `completed_invocations`
   contains only the verified PASS prefix.

   Each path-free `attempts` entry has exactly
   `{profile:<exact>,invocation_name:<exact>,
    attempt_intent:{byte_length:P,sha256:H},
    worker_manifest:{byte_length:P,sha256:H,status:<PASS|FAIL>},
    attempt_closeout:{byte_length:P,sha256:H,disposition:"CONTAINED"}}`.
   The aggregator reopens all three exact control files plus every manifest-bound
   preflight and resource ledger and, when `test_terminal=true`, the process
   ledger. It recomputes complete file lengths/hashes and
   requires the closeout manifest binding to equal the exact reopened manifest
   length, hash, and status.

   Equality closure is exhaustive. Attempt ID agrees across intent, preflight
   attempt, manifest `control_accounting`, and closeout; intent byte length/hash
   also equal the profile entry. Profile, invocation, candidate head, correction hash,
   controller PID/start, lane parent, and root bindings agree across every record
   that carries them. Intent roots equal preflight roots and, for launched
   authorized profiles, reopened PASS-TO-LAUNCH roots and worker pass-to-launch
   inputs. Closeout worker PID/start equals the controller's live handle-captured
   worker and, for `test_terminal=true`, process-ledger `runner`; for the sole
   preflight-only tuple it equals resource-ledger `preflight_only_job.runner`.
   Target child equality is required only for a launched tuple and remains the
   launch-claim/process-ledger contract. Deadline mapping hash agrees across preflight and
   closeout; closeout binds byte length `4096` and every full payload value.
   `resume_succeeded=true` means the complete pre-resume guard passed and the sole
   `ResumeThread` succeeded before `attempt-D1`; v2 requires that value and
   `resume_previous_suspend_count=1`. Any missing edge or transitive inequality
   is structural no-root.

   Closeout must satisfy every `CONTAINED` predicate. Its complete outer resource
   sample array must reproduce all extrema and status predicates with
   `status=PASS|FAIL`; `INCOMPLETE` cannot form a profile root. That controller
   array keeps its own one-second cadence and clock and never substitutes for or
   borrows an ordinal/time from either worker resource branch. Control storage
   must have equal volume identities, exact intent length, exact `262144` reserve,
   equality to preflight evidence-volume identity, and actual reopened closeout
   length at most the reserve. The intent prewrite inequality
   `attempt_intent_prewrite_free_bytes >=
   4294967296 + attempt_intent_byte_length + 262144` must hold. A complete,
   nonnull `attempt_closeout_prewrite_free_bytes` reproduces status exactly:
   `PASS` iff it is at least `4294967296+262144`, and `FAIL` iff it is below that
   threshold. Null requires `INCOMPLETE`, which cannot form a root. The aggregator
   first reproduces
   `worker_manifest.profile_bounded_bytes`, then checked-arithmetic computes
   `attempt_bounded_bytes = worker_manifest.profile_bounded_bytes - 262144 +
   attempt_closeout.byte_length`. The reserve must be present without underflow,
   and the exact total must be at most `1073741824`.

   Exit status is downstream attempt evidence, not a manifest-creation predicate.
   An admissible PASS-manifest attempt requires every existing PASS predicate plus
   closeout worker exit code `0`; its profile gate is PASS only when closeout
   resources and control storage are both PASS. An admissible FAIL-manifest
   attempt requires a valid closed worker FAIL root plus a nonzero unsigned-DWORD exit code.
   A resource-only or control-storage-only profile FAIL may instead use a valid
   PASS manifest, exit code `0`, and the corresponding complete closeout `FAIL`.
   Null/invalid manifest, non-`CONTAINED` custody, incomplete resource/storage,
   failed resume facts, identity mismatch, orphan/torn pair, or inaccessible
   control state is structural no-root.

   `attempts` contains the verified PASS prefix plus the first evaluated FAIL
   attempt, if any. A valid worker-manifest FAIL with valid `CONTAINED` closeout,
   or a worker-manifest PASS whose complete controller resource or control-storage
   result is FAIL, may occupy that first FAIL position. Structural no-root state
   is never converted into synthetic FAIL.
   The profile verdict's `gate_results` array is always exhaustive. Each entry is
   exactly `{gate:<exact invocation name>,status:<PASS|FAIL|NOT-RUN>,
   evidence_sha256:<H|null>}`. A completed gate's evidence hash is the
   D33-canonical SHA-256 of its complete `attempts` entry, not any one file.
   `sqlite_default` membership/order is
   `["runner-contract-unit","bridge-flag-off-parity","default-posture-and-authorization","shared-workbench-regression","shared-package-pass-ingest-regression"]`;
   `sqlite_authorized` is `["sqlite-authoritative-b1b"]`; and
   `postgresql_authorized` is
   `["postgresql-authoritative-migration-concurrency"]`.
   An unstarted gate is `NOT-RUN` with null and no attempt binding.
   PASS requires every entry `PASS` with `H`. After the first FAIL, every later
   entry is `NOT-RUN`; no reorder, duplicate, omission, future invocation, or
   nonnull NOT-RUN hash is permitted. The profile aggregator may consume the
   first valid worker FAIL only when its exact `CONTAINED` closeout also verifies.
   `nonclaims` is the seven package/data strings followed by the five exact
   Section 15 custody strings.

   The profile manifest
   has exactly `schema_id=layer3.b1b.aggregate_manifest.v1`, `layer="profile"`,
   `status`, `file_count=1`, `files`, and `file_order_sha256`; `files` binds the
   verdict as one standard ordinal/basename/bytes/hash object and excludes the
   manifest itself.

   External assessment objects are closed before premerge aggregation. The audit
   object is exactly
   `{schema_id:"layer3.b1b.independent_audit.v1",candidate_head_sha:G,
   principal:T,role:"independent_gate_auditor",independence:{candidate_coauthored:false,
   candidate_write_authority:false,profile_runtime_root_shared:false},checks:[...],
   blocking_finding_count:N,status:<PASS|FAIL>,assessed_at_utc:RFC3339Z}`.
   `checks` has exactly `{name:<fixed>,status:<PASS|FAIL>}` entries in this order:
   `authority_and_scope`, `changed_file_fence`, `schema_migration_rollback`,
   `row_file_census`, `targeted_tests`, `nonclaims_and_evidence_bindings`.

   The review object is exactly
   `{schema_id:"layer3.b1b.independent_review.v1",candidate_head_sha:G,
   audit_sha256:H,principal:T,role:"independent_premerge_reviewer",
   independence:{audit_coauthored:false,candidate_coauthored:false,
   candidate_write_authority:false,profile_artifact_root_shared:false,
   profile_database_shared:false,worktree_shared:false},checks:[...],
   blocking_finding_count:N,status:<PASS|FAIL>,assessed_at_utc:RFC3339Z}`.
   Its check names/order are `correctness`, `data_integrity`,
   `concurrency_and_rollback`, `resource_and_containment`,
   `authority_and_nonclaims`. For either object, blocking count is exactly the
   number of FAIL checks; PASS requires all checks PASS and zero, while valid FAIL
   requires at least one FAIL and a positive exact count. Any other schema,
   missing/extra/reordered check, status/count mismatch, or malformed timestamp is
   not an explicit FAIL input and creates no premerge root.

   The aggregator receives two explicit nonambient paths plus expected principal
   IDs out of band. Paths, files, and principals are pairwise distinct; audit and
   review candidate heads equal the unchanged candidate; review `audit_sha256`
   equals the audit file's exact SHA-256. Principal equality is identifier
   equality only and makes no cryptographic, authentication, or identity-provider
   claim. For each file it calls `CreateFileW` with `GENERIC_READ`, exactly
   `FILE_SHARE_READ`, `OPEN_EXISTING`, and `FILE_FLAG_OPEN_REPARSE_POINT`; the
   retained final handle must identify a regular, non-reparse, Windows-ReadOnly
   file with fixed basename `b1b-independent-audit.json` or
   `b1b-independent-review.json`. It reads/parses canonical bytes, resets and
   rereads through that same handle, and reproduces byte length/hash; it never
   reopens by path. A sharing, identity, basename, attribute, byte, schema, head,
   principal, or cross-binding mismatch creates no aggregate root.

   Premerge bindings are exact
   `{source_schema_id:<exact>,basename:<exact>,head_sha:G,byte_length:P,sha256:H,
   status:<PASS|FAIL>}` objects and consume the source object's schema, fixed
   basename, candidate head, complete bytes, SHA-256, and status. Assessment files
   remain external: they are never tracked, copied into any evidence/aggregate
   root, made a manifest member, or treated as implementation/runtime artifacts.
2. **Pre-merge gate layer.** Only after all three profile verdicts pass, an
   independent read-only aggregator writes `b1b-premerge-gate.json` with exactly
   `schema_id=layer3.b1b.premerge_gate.v1`, `candidate_head_sha`,
   `profile_verdicts`, `independent_audit`, `independent_review`, `ci`,
    `verdict=PASS|FAIL`, and `nonclaims`. `profile_verdicts` contains three
    ordered nonnull `{profile,byte_length,sha256}` PASS bindings. Each binding
    must reopen an exact `layer3.b1b.profile_verdict.v2` file; v1, alias, fallback,
    or inferred compatibility is schema-invalid and creates no premerge root.
    `nonclaims` is the seven package/data strings followed by the five Section 15
     custody strings. Audit and review positions are each either null or their
    exact external-assessment binding above; their source schema/basename pairs
    are respectively `layer3.b1b.independent_audit.v1`/
    `b1b-independent-audit.json` and `layer3.b1b.independent_review.v1`/
    `b1b-independent-review.json`. The
   `ci` position is either null or exactly `{head_sha:G,check_set_sha256:H,
   required_count:P,passed_count:<nonnegative-integer>,status:<PASS|FAIL>}`. A
   PASS record has no null position; FAIL uses the fixed-position rules below.
   `check_set_sha256` is the D33-canonical SHA-256 of exactly
   `{"checks":["release-gate","test","root-tests"],"head_sha":G,"policy_git_blob":G,"schema_id":"layer3.b1b.ci_check_set.v1","workflow_git_blob":G}`.
   `policy_git_blob` is the candidate-head blob for
   `docs/branch-protection-e-route.md`; `workflow_git_blob` is the candidate-head
   blob for `.github/workflows/playwright.yml`. The read-only premerge aggregator
   is the sole producer after proving those three literal aggregate contexts
   exist for the unchanged head. Matrix/shard jobs and every unlisted optional
   context are excluded from this projection. `required_count` is exactly `3`;
   PASS requires `passed_count=3` and success for each context in displayed
   order. A missing, duplicate, renamed, skipped, pending, stale-head, extra-
   required, blob, order, count, or digest mismatch makes CI FAIL.
   The separate root contains only this record and `aggregate-manifest.json`,
   using the same self-excluding one-file manifest contract with
   `layer="premerge"`. PASS requires all inputs at the unchanged candidate head. This
   record authorizes no merge by itself and makes no merged-main claim.
3. **Post-merge/final layer.** After an all-PASS premerge gate and merge, all
   three profiles rerun in new roots at the exact merged
   `project6-origin/main` SHA and produce new profile
   verdicts. A read-only `b1b-merged-proof.json` has exactly
   `schema_id=layer3.b1b.merged_proof.v1`, `merged_main_sha`,
    `profile_verdicts`, `verdict=PASS|FAIL`, and `nonclaims`; its three fixed
    profile positions are each either null or the same closed binding form, and
    every nonnull binding must reopen an exact v2 profile verdict at
    `merged_main_sha`. No v1/fallback input is accepted. `nonclaims` retains the
    same exact twelve-string order. A
   PASS record has three nonnull PASS bindings; the aggregator may consume the
   first valid merged-profile FAIL under the rules below. Its two-file root uses
   a `layer="merged-proof"` aggregate manifest. On the all-PASS path, after paths
    50-58 land at their records-closeout commit and the independent human records
    reviewer produces the required post-closeout semantic review, a final read-only aggregator
    writes
    `b1b-final-verdict.json` in a separate aggregate root. Its exact keys are
    `schema_id=layer3.b1b.final_verdict.v1`, `verdict`, `dispatch_authority`,
    `premerge_gate`, `merged_proof`, `records_semantic_review`,
     `records_closeout`, `gate_results`,
     `standing`, and `nonclaims`. Final `nonclaims` retains the same exact
     twelve-string order. Each of `dispatch_authority`, `premerge_gate`,
    `merged_proof`, `records_semantic_review`, and `records_closeout` is either
    null or its exact closed object below; PASS has no nulls and FAIL follows the
    fixed-position rules below. The human reviewer solely produces
    `records_semantic_review`; the final aggregator is the sole machine producer of the inline
    `records_closeout`; no separate records artifact, aggregator, root, manifest,
   or earlier machine fetch exists. As a reporting-only exception it may consume
   a valid status-bearing FAIL from `premerge_gate` or `merged_proof` and emit
   final FAIL without starting merge, rerun, the human records tranche, or other
    state-producing work. If the records gate is reached, it first validates the
    direct-human semantic review. Only semantic-review PASS permits it to derive
    the closed PASS or closed FAIL records object below directly from the two Git
    trees; semantic-review FAIL leaves records parity NOT-RUN. A nonnull
   `dispatch_authority` is exactly
   `{decision_record_bytes:P,decision_record_full_sha256:H,
   decision_record_canonical_sha256:H,decision_key_sha256:H,
    correction_bytes:P,correction_full_sha256:H,correction_git_blob:G,
    owner_bound_main_sha:G}`. Mapping is exact:
    `decision_record_bytes <- authority.dispatch_owner_decision.byte_length`;
    `decision_record_full_sha256 <- .full_sha256`;
    `decision_record_canonical_sha256 <- .canonical_sha256`;
    `decision_key_sha256 <- .decision_key_sha256`;
    `correction_bytes <- authority.correction.byte_length`;
    `correction_full_sha256 <- .full_sha256`;
    `correction_git_blob <- .git_blob`; and
    `owner_bound_main_sha <- authority.owner_bound_main_sha`, which must also
    equal `authority.correction.owner_bound_main_sha`. The Section 13 record and
    owner-bound Git tree independently reproduce these values. No generic
    `*_sha256`, worktree bytes, or path alias may substitute. Dispatch authority
    is statusless PASS-only derived evidence: exact sources and predicates yield
    `dispatch_authority=PASS`; an absent, malformed, mismatched, or invalid
    source makes final aggregation structurally invalid, creates no final
    record/root, and is externally contained. It never becomes explicit FAIL or
    occupies the first-FAIL position.
   Nonnull `premerge_gate` and `merged_proof` are exact imported-file bindings:
   `{source_schema_id:<exact>,basename:<exact>,head_sha:G,byte_length:P,sha256:H,
   status:<PASS|FAIL>}`. Their fixed schema/basename pairs are respectively
   `layer3.b1b.premerge_gate.v1`/`b1b-premerge-gate.json` and
   `layer3.b1b.merged_proof.v1`/`b1b-merged-proof.json`; `head_sha` equals the
   source record's candidate or merged-main SHA. The final aggregator receives
   explicit nonambient distinct paths and applies the same retained-handle
   create/open/share/no-follow/regular/ReadOnly/basename/read-reset-reread proof as
   external assessment ingestion. It copies neither source file into its root
   and makes no generic `artifact_id` alias.

   A nonnull `records_semantic_review` is the direct human review object with
   exactly `schema_id="layer3.b1b.records_semantic_review.v1"`, `reviewer_id:T`,
   `review_role="post_closeout_records_reviewer"`, `base_commit:G`,
   `closeout_commit:G`, `diff_sha256:H`, `checks`,
   `blocking_finding_count:N`, `status:<PASS|FAIL>`, and
   `reviewed_at_utc:RFC3339Z`. `checks` is exactly, in order,
   `["authority_and_standing_consistency","cross_file_claim_evidence_parity",
   "current_target_state_separation","supersession_nonclaim_integrity"]`.
   `diff_sha256` uses the existing exact nine-path records-diff preimage below;
   `base_commit` is the merged-proof main and `closeout_commit` is the landed
   records commit. The independent post-closeout human reviewer solely produces
   the status and complete D33-canonical UTF-8 object bytes, with no BOM or
   trailing LF. PASS is valid iff `blocking_finding_count=0`; a positive count is
   valid iff status is FAIL. The aggregator validates and embeds that identical
   object without synthesizing, defaulting, repairing, or rewording any value.
   Missing, malformed, noncanonical, commit-mismatched, status/count-inconsistent,
   or altered review input creates no final root. This review is distinct from
   premerge `independent_review` and adds no file, artifact, manifest, or root.

   A nonnull PASS `records_closeout` remains exactly
   `{commit:G,diff_sha256:H,parity_evidence,parity_evidence_bytes:P,
   parity_evidence_sha256:H,status:"PASS"}`. Its `parity_evidence` is embedded and
   closed with exactly `schema_id="layer3.b1b.records_parity_evidence.v1"`,
   `base_commit`, `closeout_commit`, `paths`, and `git_tree_predicates`, in that
   declared schema order before D33 canonical key ordering.
   `git_tree_predicates` is exactly
   `{base_tree_read:true,closeout_tree_read:true,path_set_exact:true,
   no_deletion:true,no_submodule:true,no_mode_only:true,
   out_of_fence:false}`. Its `diff_sha256` is the D33-canonical SHA-256 of exactly
   `{"base_commit":G,"closeout_commit":G,"paths":[...],"schema_id":"layer3.b1b.records_diff.v1"}`.
   That preimage is rebuilt only from nested `base_commit`, `closeout_commit`,
   and `paths`. `base_commit` is the verified merged-main proof SHA and nested
   `closeout_commit` equals `records_closeout.commit`. A records-closeout PASS
   additionally requires semantic-review PASS and exact equality of its
   `base_commit`, `closeout_commit`, and `diff_sha256` to those derived records
   values. PASS `paths` contains
   exactly the following nine entries in order:

   1. `docs/MASTER_CONTEXT.md`
   2. `docs/program-context/00-posture-and-invariants.md`
   3. `docs/program-context/01-arc-ledger.md`
   4. `docs/program-context/02-decision-record.md`
   5. `docs/program-context/03-forward-plan.md`
   6. `docs/program-context/04-evidence-registry.md`
   7. `next_milestone_plans/layer3_progress_manifest.json`
   8. `next_milestone_plans/layer3_workbench_proof_manifest.json`
   9. `next_milestone_plans/layer3_progress_board.md`

   Each entry has exactly `path`, `before_mode`, `before_git_blob`, `after_mode`,
   and `after_git_blob`, read directly from the two Git trees. Modes are six-
   digit lowercase octal strings and blobs are `G`; every before/after blob must
   differ. The final aggregator is the sole producer. The deterministic tree-
   entry changed-path set must equal these nine paths, with no deletion,
   submodule, mode-only, or out-of-fence change. No textual diff, worktree line
   ending, or renderer output is normalized or hashed. Any tree/path/order/mode/blob/count/digest
   difference makes records parity FAIL.

   A nonnull FAIL `records_closeout` is exactly
   `{commit:G,parity_evidence:<failure-body>,parity_evidence_bytes:P,
   parity_evidence_sha256:H,status:"FAIL"}`. It has no `diff_sha256` and may not
   embed the PASS body or PASS-only `paths`. Its closed failure body has exactly
   `schema_id="layer3.b1b.records_parity_failure.v1"`, `base_commit`,
   `closeout_commit`, `git_tree_predicates`, `observed_changed_path_count`,
   `observed_changed_path_set_sha256`, and `failure_codes`. For either PASS or
   FAIL, the wrapper `commit` and nested `closeout_commit` are equal, nested
   `base_commit` is the verified merged-main proof SHA, and both commit objects
   and both trees must be readable and valid before any final root is created;
   otherwise there is no final root and the provisional attempt is externally
   contained.

   Only after validating a nonnull PASS `records_semantic_review`, and
   immediately before deriving a nonnull PASS or FAIL `records_closeout`, the
   final aggregator performs its one and only fresh fetch of
   `project6-origin/main`, resolves that fetched ref, and requires both that
   `base_commit` is an ancestor of `closeout_commit` and that `closeout_commit`
   equals fetched `project6-origin/main` exactly. No records writer/reviewer fetch
   is machine evidence and no earlier aggregator fetch is reused. A fetch, ref-
   resolution, tree-read, or ancestry failure, or a remote-main advance during
   this authority check, creates no final record/root and is externally
   contained; it is structural authority failure, never records-parity FAIL.
   These checks add no field to either closed records schema.

   The FAIL body's `git_tree_predicates` is exactly
   `{path_set_exact:<boolean>,no_deletion:<boolean>,no_submodule:<boolean>,
   no_mode_only:<boolean>,out_of_fence:<boolean>,
   expected_blobs_changed:<boolean>}`. Each value records the actual exhaustive
   tree-to-tree result: whether the path set is exactly the nine-path fence,
   whether no deletion, submodule, or mode-only change occurred, whether
   any out-of-fence change occurred, and whether every expected path's Git blob
   changed. No desired or predicted value may substitute for an observation.
   Rename detection or similarity scoring is never run and supplies no predicate,
   code, or evidence.

   `observed_changed_path_count` is the exact cardinality of the exhaustive
   changed-path array. `observed_changed_path_set_sha256` is the D33-canonical
   SHA-256 of exactly
   `{"base_commit":G,"changed_paths":[...],"closeout_commit":G,"schema_id":"layer3.b1b.observed_changed_path_set.v1"}`.
   To build `changed_paths`, the final aggregator recursively enumerates both Git trees
   without rename detection and forms the sorted union of every repo-relative
   non-tree entry path. For each union member it reads the exact
   `(mode,object_type,object_id)` tuple on each side or the literal absence of an
   entry; the path is included iff those two values differ. A move therefore
   contributes its absent old endpoint and added new endpoint naturally, without
   classification. Directory-tree entries are traversal structure, not members.
   Included paths occur exactly once, use `/` separators, and are sorted by
   unsigned UTF-8 bytes. `path_set_exact` is exact equality with the nine-path
   fence; `no_deletion` is true iff no included path is present only in the base;
   `no_submodule` is true iff neither differing entry is a Gitlink/commit;
   `no_mode_only` is true iff no path has equal object type and ID but unequal
   mode; `out_of_fence` is true iff any included path is outside the fence; and
   `expected_blobs_changed` is true iff all nine expected same paths are blobs on
   both sides with unequal object IDs. The two commits equal the failure body.
   Only the count and digest are stored in the FAIL body; the raw changed-path
   array, textual diff, renderer output, and raw Git/error text are never
   embedded, persisted, or logged as records-closeout evidence.

   `failure_codes` is nonempty and contains, in this fixed order, exactly each
   applicable code:
   `path_set_mismatch`, `deletion_detected`, `submodule_detected`,
   `mode_only_change_detected`,
   `out_of_fence_change_detected`, `expected_blob_not_changed`.
   Correspondence is exact: the first four occur iff `path_set_exact`,
   `no_deletion`, `no_submodule`, or `no_mode_only`, respectively,
   is false; `out_of_fence_change_detected` occurs iff `out_of_fence` is true;
   and `expected_blob_not_changed` occurs iff `expected_blobs_changed` is false.
   A missing, extra, reordered, empty, or predicate-inconsistent code array is
   structurally invalid, not a valid FAIL.

   For either status, `parity_evidence_bytes` and
   `parity_evidence_sha256` cover only the exact D33-canonical nested body bytes.
   The body contains no `records_closeout`, final-verdict, hash/length backlink,
   or locator to its enclosing wrapper. The final aggregator is the sole
   nested-body producer after reading both exact Git trees and evaluating every
   predicate. It serializes the selected PASS or FAIL body once, then copies
   only the resulting length/hash to the enclosing fields.

   The final `gate_results` array is always exhaustive. Every entry is exactly
   `{gate:<literal below>,status:<PASS|FAIL|NOT-RUN>,evidence_sha256:<H|null>}`
   and membership/order is exactly:

   ```json
   ["dispatch_authority","premerge_sqlite_default","premerge_sqlite_authorized","premerge_postgresql_authorized","independent_audit","independent_review","ci","merged_main_identity","merged_sqlite_default","merged_sqlite_authorized","merged_postgresql_authorized","records_semantic_review","records_parity"]
   ```

   `dispatch_authority.evidence_sha256` is the D33-canonical SHA-256 of the exact
   final-verdict `dispatch_authority` object. The three `premerge_*` hashes equal
   the corresponding ordered `profile_verdicts[].sha256` values reopened from
   `b1b-premerge-gate.json`; `independent_audit` and `independent_review` equal
   their respective `.sha256` fields there. `ci.evidence_sha256` is the D33-
   canonical SHA-256 of the exact closed `ci` object in that record. The three
   `merged_*` hashes equal the corresponding ordered
   `profile_verdicts[].sha256` values reopened from `b1b-merged-proof.json`.
   `records_semantic_review.evidence_sha256` is the SHA-256 of the exact direct-
   human D33-canonical review-object bytes embedded at top level; the aggregator
   does not re-author them. A valid semantic-review FAIL occupies this gate and
   forces `records_parity` to `NOT-RUN`/null.
   For either PASS or FAIL, `records_parity.evidence_sha256` equals the hash of
   the selected nested `records_closeout.parity_evidence` body and therefore
   equals `records_closeout.parity_evidence_sha256`; it never hashes the closeout
   or final wrapper.

   `records_closeout` is not consumed from another artifact: the final aggregator
   constructs it inline during the same evaluation that constructs the final
   verdict. The single fetch and landed-authority check above are therefore the
   only such machine operation; there is no second fetch, earlier records root,
   or trust handoff between aggregators.

   `merged_main_identity.evidence_sha256` is the D33-canonical SHA-256 of exactly
   `{"candidate_head_sha":G,"merged_main_sha":G,"merged_proof_sha256":H,"premerge_gate_sha256":H,"schema_id":"layer3.b1b.merge_main_identity.v1"}`.
   `candidate_head_sha` is reopened from the premerge record,
   `merged_main_sha` from the merged-proof record, and the two hashes equal the
   corresponding final-verdict artifact-binding hashes. The final aggregator is
   the sole producer of this unchanged identity preimage. Git must prove that the
    candidate commit is an ancestor of that exact merged main. Every nonnull
    merged-profile binding, including a PASS prefix and the first valid FAIL
    binding, must reopen an exact `layer3.b1b.profile_verdict.v2` whose
    `candidate_head_sha` is exactly that `merged_main_sha`; a null later profile
    makes no candidate-head claim. A v1 or compatibility object is invalid.
   Every nonnull `records_semantic_review.base_commit` equals that merged SHA.
   When `records_closeout` is nonnull, its nested base/closeout commits equal the
   semantic review's corresponding commits; a null records position makes no
   records-closeout claim. A stale head, non-ancestor, unequal nonnull profile
   SHA, unequal review/records commit binding, or digest mismatch makes final
   aggregation structurally invalid, creates no
   final record/root, and is externally contained. `merged_main_identity` is
   statusless PASS-only derived evidence, never a new artifact, explicit FAIL,
   or first-FAIL occupant.

   A completed gate has `H`; an unevaluated gate is `NOT-RUN` with null.
   `dispatch_authority` and `merged_main_identity` are PASS-or-no-final-root and
   can never carry FAIL. PASS requires all thirteen entries PASS with `H`. On a
   valid final FAIL, evaluated earlier entries are PASS, the first failing entry
   is backed either by a valid status-bearing upstream input, including the
   direct-human semantic review, or by the final aggregator's closed inline
   records-parity failure body, is FAIL with its
   evaluated evidence hash, and every later entry is NOT-RUN/null. Missing, extra, duplicate,
   reordered, self-referential, future, or nonnull NOT-RUN evidence invalidates
   the final verdict. The final aggregator derives the array from this frozen
   contract and aliases only the upstream inputs and exact derived records body
   above; it does not invent evidence or hash its own verdict/manifest.

   The final root also contains only the verdict plus the self-excluding
   `layer="final"` aggregate manifest. Gate results
   cover authority, all candidate and merged profiles, audit, premerge review,
   CI, merge-main identity, records semantic review, and records parity. Only an
   all-PASS final aggregate may
   carry the exact Section 15 final standing. It is not a profile evidence file,
   package member, application artifact, or prerequisite that an earlier
   invocation could predict.

Each launched authorized profile invocation receives a distinct one-use nonce and
PASS-TO-LAUNCH attestation. Default invocations run first as non-writing
prerequisites; the worker issues no production-valid attestation to them. A
complete default F07/C01 projection with only `reverified=false` routes solely
to the existing `authority` gate's FAIL, while fixed-field/content/path/
readability/identity/incomplete fixture state is no-root. Authorized profiles
route that same complete negative solely to their existing `fixture` gate.
Neither route changes a gate array, member count, or file order.
Worker manifests, profile v2 verdicts, and aggregate records are canonical
UTF-8/no-BOM/no-newline,
exclude themselves, and bind only already-existing immutable inputs.

The two-axis invocation rule above is global. Success evidence-input counts are
exactly five, twelve, and nine for default, SQLite-authorized, and PostgreSQL-
authorized respectively. Failure roots use only one valid tuple from the table,
the sorted phase/terminal union, invocation verdict, stop, containment, and the
self-excluding manifest. Default roots never contain PASS-TO-LAUNCH or a launch
claim; authorized roots contain both or neither. No empty placeholder,
undeclared phase alias, or later-phase file is created.

Aggregate FAIL propagation is exact. A profile aggregator may consume the first
valid worker FAIL only with its verified `CONTAINED` closeout and complete
attempt binding. Premerge never starts unless all three v2 profile verdicts
are PASS. A merged-proof aggregator may consume the first valid merged-profile
FAIL after an all-PASS premerge gate and merge. The final read-only reporting
aggregator may consume a valid premerge, merged-proof, or direct-human records-
semantic-review FAIL, or derive the closed inline records-parity FAIL after all
earlier inputs pass, and emit final FAIL.
After an upstream FAIL, no
state-producing phase, merge, rerun, records closeout, or other downstream
aggregator starts; the reporting-only final aggregator is the sole downstream
aggregate exception and launches/mutates nothing.

Every read-only aggregate root has a closed failure set only when its next
ordered upstream input is a valid explicit FAIL, including final records semantic
review, or, solely for final `records_parity`, when the one-fetch/two-tree evaluation produces the complete
closed inline FAIL body. An upstream valid explicit FAIL is a complete, readable,
immutable input whose schema, identity, member set, byte length, hash, and
status/verdict field all verify and whose status/verdict is exactly `FAIL`. The
evaluated sequence is exactly zero or more verified PASS inputs followed by that
first valid upstream FAIL or derived records FAIL. The completed sequence is only
the PASS prefix; the failing position is evaluated but never completed, and no
later position is evaluated.

The aggregator writes its layer's normal verdict/gate/proof schema with the
record status/verdict set to `FAIL`, then `aggregate-stop.json`, then a
self-excluding `aggregate-manifest.json`. The normal FAIL record exposes the
evaluated sequence without an added opaque list:

- A profile FAIL has `completed_invocations` equal to the PASS-name prefix,
  `attempts` equal to the PASS attempt bindings plus the first valid FAIL
  attempt binding, and exhaustive `gate_results` equal to PASS with `H` for that
  prefix, FAIL with the D33-canonical FAIL-attempt-binding `H`, then
  NOT-RUN/null.
- Premerge starts only after all three fixed profile bindings are nonnull PASS.
  Its `independent_audit`, `independent_review`, and `ci` positions then contain
  the PASS objects before failure, the first valid FAIL object itself, and null
  in every later position.
- Merged-proof's three fixed profile positions contain the PASS bindings before
  failure, the first valid FAIL binding, and null in every later position.
- Final's fixed `dispatch_authority`, `premerge_gate`, `merged_proof`,
  `records_semantic_review`, and `records_closeout` positions contain the fully
  verified nonnull prefix, the first valid upstream FAIL object or the derived
  closed records FAIL, and null
  in every later position. A malformed statusless dispatch-authority object or
  derived merged-main identity is not an explicit FAIL and produces no final
  root. Its thirteen fixed `gate_results` use the same PASS, first
  FAIL, then NOT-RUN/null rule and bind only the corresponding exposed upstream
  evidence or derived records body.

`aggregate-stop.json` has exactly
`schema_id=layer3.b1b.aggregate_stop.v1`, `layer=<profile|premerge|merged-proof|final>`,
`completed_input_order_sha256:H`, and `stopped_at:RFC3339Z`. It carries no error
taxonomy: the enclosing FAIL record's fixed exposed input/gate positions identify
the first valid upstream FAIL, including records semantic review or derived
records-parity FAIL. The FAIL
manifest uses the aggregate-manifest keys, exactly aliases the FAIL record's
status, has `file_count=2`, and binds only the FAIL record followed by the stop
record. `completed_input_order_sha256` is the D33-canonical SHA-256 of exactly
`{"completed_inputs":[...],"layer":"<profile|premerge|merged-proof|final>","schema_id":"layer3.b1b.completed_input_order.v1"}`.
`completed_inputs` contains only the verified PASS prefix. Each input binding
has only `input_kind`, `input_id`, `byte_length`, and `sha256`. The kind/order
contract is exact:

- `profile`: `input_kind="attempt_binding"`, with invocation-name `input_id`, in
  the selected profile's Section 16 order;
- `premerge`: three `input_kind="profile_verdict_file"` inputs with IDs
  `profile:sqlite_default`, `profile:sqlite_authorized`,
  `profile:postgresql_authorized`; then two
  `input_kind="external_assessment_file"` inputs with IDs
  `independent_audit`, `independent_review`; then one `inline_object` input with
  ID `ci`;
- `merged-proof`: three `profile_verdict_file` inputs with those same profile IDs;
- `final`: `inline_object:dispatch_authority`,
  `aggregate_file:premerge_gate`, `aggregate_file:merged_proof`, then
  `inline_object:records_semantic_review`, then
  `inline_object:records_closeout`.

For every `*_file` binding, byte length and SHA-256 cover the exact immutable
file bytes, not a parsed object or manifest wrapper. For `attempt_binding`,
bytes are exactly the D33-canonical bytes of the complete v2 `attempts` entry;
its length/hash therefore cover intent, worker-manifest, and closeout bindings
without inventing another artifact. For `ci`, bytes are exactly
the D33-canonical bytes of the complete closed `ci` object in
`b1b-premerge-gate.json`; for `dispatch_authority`, `records_semantic_review`,
and `records_closeout`, bytes are exactly the D33-canonical bytes of those
complete closed objects in `b1b-final-verdict.json`. The inline binding
length/hash cover those exact bytes. The human review bytes remain direct and
unchanged; the aggregator serializes each machine-produced inline object once
and is sole producer only for those machine objects. An inline input enters
`completed_inputs` only when verified PASS. The enclosing aggregate record
consumes the same bytes.

`input_id` is the exact displayed literal; all byte lengths are positive and
hashes are `H`. The read-only aggregator is the sole producer of the completed-
input hash immediately before its FAIL record and stop. The FAIL record, stop,
and manifest must agree exactly on layer/profile identity, record status,
evaluated PASS-plus-FAIL sequence, completed PASS-only prefix, bindings, and
hashes. They exclude the aggregate result from its own inputs, the stop and
manifest from both sequences, every later input, and every future binding.

An absent, unreadable, partially written, hash-mismatched, schema-invalid,
identity-mismatched, statusless-invalid, or otherwise unverified next input is
not converted into a synthetic FAIL. In those cases no aggregate record, stop,
manifest, or aggregate root is created; the caller reports external
containment/recovery. An order, layer, schema, membership, binding, or digest
mismatch likewise invalidates the set. Aggregators launch no child and mutate
no application state, so valid aggregate FAIL roots have no containment record;
any unexpected file is itself a failed member-set check. A missing manifest
starts no downstream aggregate; an upstream FAIL follows only the explicit
propagation exception above.

A no-leak, hash, member-set, or redaction failure creates no authoritative package file and no package, reconciliation, or handoff row. Temporary staging, if unavoidable, must be rehashed, censused, isolated, and retained/archive-contained for diagnosis under the repo's no-delete rule; it is non-authoritative, may not be mistaken for a passed package, and may not be reused unless a later authorized attempt performs exact-basis validation.

## 10. Independent-session concurrency proof

Concurrency is required on SQLite and PostgreSQL. Receipt uniqueness cannot by
itself arbitrate an approved resolver against a non-approved Gate-B/promotion
decision occupying the same I1 because the non-approved branch inserts no
receipt. Every exact one-candidate F07/C01 decision therefore acquires the same
transaction-scoped I1 writer lock before any Gate-B row or snapshot-file write,
then re-reads the receipt under that lock. Shared ORM sessions, nested savepoints,
mocked repositories, SQLite `with_for_update`, in-memory SQLite, `StaticPool`, and
separate database files are not proof.

SQLite keeps the predecessor's one isolated file-backed database/two-connection
proof. Each connection sets `PRAGMA busy_timeout=5000`, begins the competing
transaction with `BEGIN IMMEDIATE`, and re-runs I1/receipt lookup after the writer
lock is held. A bounded `SQLITE_BUSY` rolls back and returns `503
promotion_identity_lock_unavailable` with zero Gate-B row/file mutation and no
hidden retry.

PostgreSQL uses the one profile-bound isolated database/schema and two real
connections. Before row/file mutation each competing transaction executes
`SET LOCAL lock_timeout='5s'` and
`pg_advisory_xact_lock(<signed-bigint>)`. The key is the first 16 hex digits of
`canonical_identity_key_hash` parsed unsigned-64, then minus `2^64` iff at least
`2^63`. A prefix collision may conservatively serialize unrelated identities but
cannot admit conflict. B1b v1 permits one candidate/I1; any future multi-I1
operation sorts complete identity tuples before locking. Timeout returns the same
bounded 503 and zero mutation. Unsupported dialects fail closed.

The PostgreSQL proof has exactly these ten cases and exact node IDs, in order:

| # | `case_id` | Exact `node_id` |
|---:|---|---|
| 1 | `migration_cycle` | `backend/tests/test_layer3_migrations.py::test_b1b_postgresql_migration_cycle` |
| 2 | `equivalent_approval_uniqueness` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_equivalent_approval_uniqueness` |
| 3 | `race_approved_first` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_approved_first` |
| 4 | `race_nonapproved_first` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_nonapproved_first` |
| 5 | `lock_timeout` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_lock_timeout` |
| 6 | `resolver_reuse` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_reuse` |
| 7 | `resolver_basis_conflict` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_basis_conflict` |
| 8 | `corrupt_basis` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_corrupt_basis_conflict` |
| 9 | `initial_transaction_rollback` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_initial_transaction_rollback` |
| 10 | `materializer_rollback` | `backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_materializer_rollback` |

Cases 2-10 retain the exact canonical F07 I1 components and exact D34 approval
semantics from Sections 4 and 6. `case_id` is evidence/isolation metadata only: it
never enters I1, material identity, approval semantics, receipt, promotion basis,
or any other authoritative preimage. A nonnull case `scope` is exactly
`{canonical_identity_key_hash:"2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0",
decision_semantics_sha256:H,case_fixture_sha256:H}`. The semantic digest is the
D33-canonical SHA-256 of the exact displayed F07 decision-semantics object in
Section 4. `case_fixture_sha256` is the D33-canonical SHA-256 of exactly
`{case_id:<fixed literal>,decision_semantics_sha256:H,fixture:{byte_length:34,
content_sha256:"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad"},
identity:<the exact complete canonical F07 I1 preimage>,
schema_id:"layer3.b1b.postgresql_case_fixture.v1"}`. This binding supplies case
evidence without inventing variant connector keys or changing production
identity.

Cases run serially in that same database/schema. Cases 2-10 use unique case/run/
target/receipt/lineage identifiers and case-relative authoritative and retained-
containment namespaces. Immediately before each case, an exact case-scoped DB
and file census must be zero and the canonical F07 I1 must be absent. After its
facts are frozen, verification-only cleanup removes case-owned DB rows in reverse
foreign-key order and moves, never deletes, every case-owned file to a retained
non-authoritative containment namespace. Cleanup is exactly
`{database_rows_remaining:0,authoritative_files_remaining:0,completed:true}`.
Case 1 has `cleanup=null` and leaves the migration at candidate head. A cleanup
failure stops every later case and forbids final C0/C3 authority; it cannot be
represented as completed cleanup or a valid receipt. Only after case 10 cleanup
PASS may the final authoritative bridge node establish canonical F07 C0. This is
isolated verification cleanup, not production deletion, recovery, backfill,
seed/generate authority, or permission to reuse a retained artifact.

The plugin exposes one in-process `register_postgresql_proof_case` control on the
main pytest thread. It is bound to current node ID, its candidate-head test blob,
and state `EMPTY -> REGISTERED` exactly once; replacement, reuse, cross-node call,
or registration by another thread fails. The test captures its exact facts,
registers them, then asserts the same predicate. After teardown and completed
cleanup, the plugin pauses cadence and emits `postgresql_proof_case`, immediately
followed by that node's `node_outcome`, under one uninterrupted pipe-write lock;
no cadence, endpoint, collection, or other frame may interleave. The plugin
retains the registered immutable facts; it does not infer them from console text.

A PASS case has one exact event, `classification="passed"`, and its predicate
true. Case 1 has `scope=null`, nonnull facts, and `cleanup=null`; cases 2-10 have
nonnull scope/facts and completed cleanup. A failed/error
node before registration may have null scope/facts and no case event; after
registration it must have the exact event and facts. A passed node without its
event, duplicate/mismatched event, false predicate with passed outcome, or event/
outcome nonadjacency is no-root. `skipped`, `xfailed`, and `xpassed` are statically
forbidden for these ten nodes and are runtime no-root if observed. After the
first valid case FAIL, later cases are NOT-RUN with null scope/facts/cleanup and
no event/outcome. An off-case earlier failure produces no PostgreSQL receipt;
the semantic phase remains `launched` and never advances to
`post-postgresql-proof`.

Case `facts` schemas and PASS values are exact:

1. `migration_cycle` uses `{upgrade_status:<PASS|FAIL>,rollback_status:<PASS|FAIL>,
   reupgrade_status:<PASS|FAIL>,head_revision:T,database_at_head:<boolean>}`;
   PASS requires three PASS values, exact candidate migration head, and true.
2. `equivalent_approval_uniqueness` uses
   `{first_http_status:P,second_http_status:P,first_disposition:T,
   second_disposition:T,receipt_count:N,winning_basis_count:N,
   first_new_rows:N,first_new_files:N,second_new_rows:N,second_new_files:N}`;
   PASS is exactly `200,200,"created","reused",1,1,7,1,0,0` in that field order.
3. `race_approved_first` uses
   `{approved_http_status:P,nonapproved_http_status:P,
   nonapproved_error_code:T,approved_committed:<boolean>,
   nonapproved_committed:<boolean>,receipt_count:N,approved_new_rows:N,
   approved_new_files:N,nonapproved_new_rows:N,nonapproved_new_files:N,
   partial_snapshot_count:N}`; PASS is exactly `200,409,
   "promotion_identity_decision_conflict",true,false,1,7,1,0,0,0`.
4. `race_nonapproved_first` uses
   `{nonapproved_http_status:P,approved_http_status:P,
   nonapproved_committed:<boolean>,approved_committed:<boolean>,receipt_count:N,
   nonapproved_new_rows:N,nonapproved_new_files:N,approved_new_rows:N,
   approved_new_files:N,partial_snapshot_count:N}`; PASS is exactly
   `200,200,true,true,1,6,1,7,1,0`.
5. `lock_timeout` uses `{http_status:P,error_code:T,new_rows:N,new_files:N,
   receipt_count:N}`; PASS is exactly
   `503,"promotion_identity_lock_unavailable",0,0,0`.
6. `resolver_reuse` uses
   `{first_http_status:P,second_http_status:P,first_disposition:T,
   second_disposition:T,receipt_count:N,source_connector_count:N,dataset_count:N,
   dataset_version_count:N,variable_definition_count:N,
   dataset_source_provenance_count:N,promoted_session_count:N,
   promoted_snapshot_count:N,typing_record_count:N,analysis_unit_count:N,
   analysis_group_count:N,analysis_set_count:N,analysis_plan_count:N,
   pass_run_count:N,analysis_run_count:N,assumption_check_count:N,
   analysis_artifact_count:N,caveat_count:N,reconciliation_count:N,
   package_count:N,second_new_rows:N,second_new_files:N}`; PASS is exactly
   `200,200,"materialized","reused",1,1,1,1,2,1,1,1,1,1,1,1,1,1,1,4,1,1,1,3,0,0`.
7. `resolver_basis_conflict` uses
   `{http_status:P,error_code:T,new_rows:N,new_files:N}`; PASS is exactly
   `409,"connector_materialization_basis_conflict",0,0`.
8. `corrupt_basis` uses
   `{http_status:P,error_code:T,new_rows:N,new_files:N,receipt_count:N}`; PASS is
   exactly `409,"connector_promotion_basis_conflict",0,0,1`.
9. `initial_transaction_rollback` uses
   `{receipt_count:N,gate_b_row_count:N,authoritative_file_count:N,
   identity_occupied:<boolean>}`; PASS is exactly `0,0,0,false`.
10. `materializer_rollback` uses
    `{receipt_preserved:<boolean>,gate_b_spine_preserved:<boolean>,
    preclaim_state_restored:<boolean>,output_row_count:N,
    authoritative_file_count:N}`; PASS is exactly `true,true,true,0,0`.

Every count is case-scoped before cleanup. Equivalent approvals converge on one
receipt/basis. Approved-first rolls the later non-approved transaction back with
the exact 409 and zero delta; non-approved-first permits its ordinary six-row/
one-file commit, then the approved seven-row/one-file transaction. Resolver reuse
creates one complete materialization/analysis/package chain. Different resolver
basis and corrupt stored promotion basis return their respective exact 409s with
zero new state. Initial rollback leaves no occupied identity; materializer
rollback preserves the committed receipt/spine and restores every uncommitted
status/basis/output link.

Receipt gate mapping is exact: `migration={1}`;
`concurrency={2,3,4,6,7}`; `lock_timeout={5}`; `corrupt_basis={8}`; and
`rollback={9,10}`. A gate is PASS iff every mapped case is PASS, FAIL iff at least
one mapped case is FAIL, otherwise NOT-RUN iff none failed and at least one is
NOT-RUN. Whole-receipt FAIL never substitutes for an individual mapped gate.
The reproduced largest complete PostgreSQL-case envelope is exactly 1997 payload
bytes and 2001 framed bytes. The case ceiling is 2048/2052; the universal
payload/frame ceiling is 4096/4100. Before candidate freeze, the same mechanical
vector must reproduce every one of the ten schemas; a larger or unreproduced
vector blocks freeze. No padding or extra event may manufacture equality.

Use deterministic barriers after independent preflight/before lock acquisition
and before commit. All ten designated cases run against actual PostgreSQL only;
SQLite/service coverage remains in the bridge file but cannot satisfy this
receipt. Migration rollback is operationally flag-off and reverses indexes,
checks, foreign keys, table, then nullable intake pair in dependency order. A
database with a promotion receipt fails destructive downgrade pending separately
authorized export/disposition. No historic receipt backfill, intake-row rewrite,
population-policy change, production deletion, seed/generate action, or recovery
authority is granted; preexisting joint-null rows remain P1-ineligible.

## 11. Synthetic C01 boundary and later real acquisition lane

The B1b acceptance fixture is a two-row synthetic ScienceBase-family fixture only: `SB-001=42` and `SB-002=43`.

- It is not acquired from ScienceBase or USGS.
- `public_read_confirmed=true` is synthetic test state only.
- `official_public_read_evidence=false` remains explicit.
- F20 is not established.
- The sample is degenerate and non-temporal.
- The only supported claim is bounded deterministic repeatability of the named method on the named fixture.
- It proves no official-data, source-availability, public-read, production, utility, causal, temporal, representativeness, or population-wide claim.

Real ScienceBase acquisition-to-intake orchestration is a separate later lane. That lane must begin at the real acquisition result, explicitly invoke the intake/capture boundary under its own default-off authority, prove raw-object ownership and no-copy behavior, and receive its own security, network, support-matrix, acceptance, and owner authorization. It is not a B1b acceptance criterion, may not run during B1b proof, and may not be inferred from source functions that exist without a production caller.

## 12. Closed historical labels and non-gates

### C-m4

`C-m4` was settled by the owner-selected `CT3-08=M1`: intake uses conflict-only `409`,
`client_request_id` and `basis_hash` remain unique, and `target_ref` remains non-unique.
That owner decision is the authority for C-m4. The later `CT3-07=DUAL-RETENTION` and Q4
Bundle A decisions preserve and contextualize both replay seams; they did not replace or
reopen C-m4:

- Intake exact replay uses the native `409` path and reloads by `client_request_id`, followed by full authority and basis comparison.
- Gate-B exact replay returns `200` with `already_committed`.
- A changed repeated request returns `409` and does not continue.
- A `409` by itself is never a durable pointer or continuation grant.

Therefore C-m4 is settled, is not an open B1b gate, and must not be placed on the owner
ballot or re-resolved after B1b.

### O5

`O5` remains **OPEN/DEFERRED**: it is the later owner direction choice between deeper local
proof and OUTWARD/nonlocal work. It is not a B1b gate, not the B1b second key, and has no
effect on the local synthetic proof. D32 supplies the safe current local-depth default and
parks OUTWARD; it does not close O5. Any OUTWARD, nonlocal, network, or security expansion
requires a separate lane and owner authority.

## 13. Optional bounded preservation and final compound owner ballot

Stage 1 is an intentionally bounded prekey evidence snapshot. It is useful
redundancy but is not the exhaustive mutable record-lane closeout required by I12
and cannot make I12 complete. An `I12-EXHAUSTIVE-ARCHIVE-COMPLETE` selection is
available only after a separately audited exhaustive census/receipt is cited on
tracked main. The pending-I12 path may skip Stage 1 and go directly to Stage 2.

The `2026-07-13` suffix on both prospective record basenames identifies this
ballot-instrument version, not the date of a future owner act. It cannot be used
as decision-time evidence or to backdate a grant. The only authoritative act
time is the filled `owner_utc_timestamp`; archive manifests separately record
their actual capture times.

In both ballots, `owner_decision_key` is a nonsecret, single-line owner-chosen
authorization phrase whose UTF-8 bytes must match
`[A-Za-z0-9][A-Za-z0-9._:-]{15,127}` exactly. It is therefore 16-128 ASCII
bytes, has no whitespace, Unicode normalization ambiguity, `=`, CR, LF, NUL, or
control character, and is copied verbatim into the record. Anything outside
that grammar makes the ballot invalid rather than being trimmed or normalized.
Stage 1 and Stage 2 require different key values and their domain-separated
hashes must differ.

### 13.1 Optional Stage 1: bounded prekey archive-only owner key

Before any `C:/p6store` write, the owner must directly grant the exact archive-
only block below. It authorizes no implementation. The mechanically captured
record path is
`state/agent-inbox/b1b-i12-archive-authorization-2026-07-13.md`.

```text
B1B BOUNDED PREKEY ARCHIVE-ONLY KEY
correction_path=next_milestone_plans/Layer3_planning_docs/b1b-dispatch-correction.md
correction_bytes=<decimal-byte-length>
correction_full_sha256=<64-uppercase-hex>
post_correction_project6_origin_main_sha=<40-lowercase-hex>
operator_context_root_id=<opaque-lane-local-id>
operator_context_root_canonical_sha256=<64-uppercase-hex>
source_census=b1b-bounded-prekey-archive.v1
[ ] GRANTED-ARCHIVE-ONLY - authorize only the exact 15-source bounded snapshot
    and its docs-only evidence citation; I12 remains open; no B1b implementation
[ ] WITHHELD-ARCHIVE
owner_decision_key=<nonempty-owner-key>
owner_utc_timestamp=<RFC3339Z>
ARCHIVE_AUTH_CANONICAL_SHA256=0000000000000000000000000000000000000000000000000000000000000000
```

Exactly one mark is required. The recorder copies the owner's selected block
into the fixed path as UTF-8, LF-only, no BOM, exactly one final LF, with no
paraphrase. The only mechanical post-copy change is replacing the 64 zeros after
`ARCHIVE_AUTH_CANONICAL_SHA256=` with the uppercase SHA-256 computed after
zeroing that exact field; the full-file hash is then recorded externally.

The granted bounded snapshot contains exactly these 15 sources, no wildcard expansion:

1. `state/agent-inbox/b1b-successor-packet-2026-07-12.md`
2. `state/agent-inbox/b1b-ratification-2026-07-13.md`
3. `state/agent-inbox/b1b-scope-2026-07-13.md`
4. `state/agent-inbox/v2-b1a-run-report.md`
5. `state/agent-inbox/v2-b1a-cl6-report.md`
6. `state/agent-inbox/owner-decision-record-2026-07-10.md`
7. `state/agent-inbox/owner-decision-ct3-capture-2026-07-12.md`
8. `state/agent-inbox/ct3-clarification-addendum.md`
9. `state/agent-inbox/b1-vertical-loop-packet.md`
10. `state/agent-inbox/ct3-semantics-table.md`
11. `state/agent-inbox/ct4b-bound-fixture.md`
12. `state/agent-inbox/v2-ct4b-fixture-report.md`
13. `worktrees/manifest-children/ct4b-fixture-child-manifest.json`
14. `next_milestone_plans/Layer3_planning_docs/b1b-dispatch-correction.md`
15. `state/agent-inbox/b1b-i12-archive-authorization-2026-07-13.md`

This manifest is intentionally scoped, not exhaustive. It excludes the mutable
living coordination files `admission-spine-program-context.md` and
`owner-items-post-b1a-2026-07-11.md`, other lane-source payloads/logs, and any
future record-lane content; `for-claude.md` is excluded as a historical
navigation surface. These omissions are why the snapshot records
`BOUNDED-PREKEY-SNAPSHOT-COMPLETE; I12-OPEN`, never I12 completion.

Source resolution is part of the census, not an executor choice. In local
preflight only, map `operator_context_root_id` to the focused operator context
root, resolve it canonically, and compare the uppercase SHA-256 of its normalized
canonical namespace to `operator_context_root_canonical_sha256`. Never persist
the raw absolute root. Entries 1-13 and 15 resolve only beneath that verified
root; resolve each existing path canonically, require containment by the root,
and reject a symlink/reparse point, missing path, duplicate canonical path, or
outside-root result. Entry 14 is different: read only the exact Git blob at
`<post_correction_project6_origin_main_sha>:next_milestone_plans/Layer3_planning_docs/b1b-dispatch-correction.md`
from `project6-origin`, or a clean worktree whose `HEAD` equals that SHA and whose
checked-out bytes reproduce the blob. Never substitute a root-checkout,
operator-inbox, uncommitted, or similarly named correction. Rehash all 15
resolved sources immediately before copying and again from the archive bytes.
The archive manifest records only `operator_context_root_id` or `git_blob`, the
relative source path, bytes, and hash; it never records the absolute root.

For the root namespace hash, obtain the operating system's final canonical path,
strip a Windows `\\?\` prefix, change `\` to `/`, uppercase only the drive
letter, normalize the complete string to Unicode NFC, and remove a trailing
slash. Preserve all remaining character case exactly. Hash the UTF-8 bytes of
`project6.operator-context-root.v1` followed by one NUL byte and that normalized
path, with no BOM or terminal newline. Two independent preflight processes must
reproduce the value; neither persists the preimage.

The raw F07 fixture is not copied; D4 remains deferred. The filename-safe UTC
token is exactly zero-padded UTC `yyyyMMddTHHmmssfffZ` (regex
`^[0-9]{8}T[0-9]{9}Z$`), with no colon or local-time conversion. Create one new
`C:/p6store/inbox-archive/<UTC>-b1b-prekey/` directory and
`ARCHIVE_MANIFEST.json`. Every entry records source namespace
(`operator_context_root_id` or `git_blob`), relative source path,
archive-relative path, bytes, and lowercase SHA-256. The aggregate is SHA-256
over the D33-canonical
JSON array of complete entry objects sorted by archive-relative path. The
manifest records that aggregate but excludes itself from the entry array. Verify
every copied file by a second read, then land a tracked evidence-registry entry
with destination basename, manifest bytes/full hash, aggregate, and exact source
census. That tracked citation advances main.

Before writing, resolve `C:/p6store/inbox-archive` to an existing non-reparse
directory on one volume, acquire the process-wide named mutex
`Global\project6-b1b-prekey-archive`, and require the exact lane directory to be
absent. A collision stops that attempt; acquire a fresh current UTC token after
re-preflight, never append a counter/suffix and never overwrite. Require
destination free bytes greater than or equal to twice the total
source bytes plus `1,048,576`; an unavailable or nonnumeric result stops the
lane. Create the lane directory once, never reuse or overwrite it, and keep the
mutex through the final second-read census. On any later failure, stop copying,
retain the partial directory under the no-delete rule, write a bounded
`FAILED.json` census containing only relative names/bytes/hashes and the failed
step, and never treat or resume it as an archive-complete receipt.

The archive-only key permits one clean docs branch/PR limited to the relevant
records paths to cite the bounded receipt and keep status mirrors aligned. It
must retain `OPEN-I12-ARCHIVE-PENDING` and add
`BOUNDED-PREKEY-SNAPSHOT-COMPLETE`; it cannot close, waive, or supersede I12.
It does not authorize source/runtime/schema edits or B1b execution. Merge still
requires green relevant checks, clean review, and the operator's normal merge
action. Stage 2 may proceed only through a valid final Part B choice.

### 13.2 Stage 2: final compound dispatch key

The final ballot is valid only when the owner supplies the final correction
bytes/hash, exact then-current `project6-origin/main` SHA, verified operator-
context root ID/hash, one Part A selection, one Part B selection, one decision
key, and one UTC timestamp. If exhaustive archive-complete is selected, every
receipt field is mandatory and the separately audited exhaustive receipt must
already be cited on that main. Missing, mismatched, double-marked, conditional,
or ambiguous input means `NOT-GRANTED`; `WITHHELD` is not inferred.

No repository attribute pin is assumed. The final correction Git blob and its
checkout bytes must each independently be LF-only. Before presenting the
ballot, the gate auditor reads both in binary, requires strict UTF-8, no BOM, no
CR byte, and exactly one final LF, then requires byte-for-byte equality and the
declared byte length/full SHA-256 against the exact blob at the supplied main
SHA:

```text
B1B BUILD-LANE COMPOUND SECOND KEY
packet_path=state/agent-inbox/b1b-successor-packet-2026-07-12.md
packet_bytes=38002
packet_full_sha256=4895028DF74591B850B1DE4FC619D586AB2D3DD33A2227C4DF0C2BB8F41628FD
packet_canonical_sha256=A7BD7DF512ED53B97C3A10878C3F8FA040826A8566D4E3347BA3F021E800E38C
operator_context_root_id=<opaque-lane-local-id>
operator_context_root_canonical_sha256=<64-uppercase-hex>
correction_path=next_milestone_plans/Layer3_planning_docs/b1b-dispatch-correction.md
correction_bytes=<decimal-byte-length>
correction_full_sha256=<64-uppercase-hex>
post_correction_project6_origin_main_sha=<40-lowercase-hex>

Part A - select exactly one
[ ] GRANTED - authorize B1b-01 through B1b-06 and the bounded closeout tranches
[ ] WITHHELD - do not authorize B1b dispatch

Part B - select exactly one
[ ] I12-EXHAUSTIVE-ARCHIVE-COMPLETE
[ ] I12-PENDING-DOES-NOT-BLOCK-THIS-DISPATCH
i12_archive_folder=<required-basename-for-exhaustive-complete-or-NA>
i12_manifest_bytes=<decimal-or-NA>
i12_manifest_full_sha256=<64-uppercase-hex-or-NA>
i12_aggregate_sha256=<64-uppercase-hex-or-NA>
i12_source_census_sha256=<64-uppercase-hex-or-NA>

owner_decision_key=<nonempty-owner-key>
owner_utc_timestamp=<RFC3339Z>
budget_resource_cap=NONE
DECISION_RECORD_CANONICAL_SHA256=0000000000000000000000000000000000000000000000000000000000000000
```

For `I12-PENDING-DOES-NOT-BLOCK-THIS-DISPATCH`, all five archive fields must be
`NA`, and all three `i12_disposition` hash fields must independently be exact
`NA`; the owner explicitly accepts current single-copy risk. That choice does
not close or waive I12 or any other gate. A mixed COMPLETE/PENDING projection,
partial hash set, alternate spelling, or compatibility alias is invalid. For
`I12-EXHAUSTIVE-ARCHIVE-COMPLETE`, none may be `NA`; the census must cover all
mutable record-lane logs/payloads and living coordination state required by I12,
and a tracked independent audit must say why every nearby undeclared file is an
intentional exclusion. The bounded Stage-1 snapshot is inadmissible for this
selection. Exhaustive completion also authorizes the one minimal decision-child
archive below. Part B never authorizes implementation without Part A `GRANTED`.

The COMPLETE mapping is atomic. First resolve the exact ballot-named archive
folder, require its basename equal `i12_archive_folder`, read its canonical
`ARCHIVE_MANIFEST.json` bytes, and require byte length equal
`i12_manifest_bytes`. Before conversion, validate each of
`i12_manifest_full_sha256`, `i12_aggregate_sha256`, and
`i12_source_census_sha256` as exactly 64 uppercase hexadecimal characters.
Independently recompute the manifest's uppercase full-file SHA-256, its D33 entry-
array aggregate, its canonical schema, and the audited exhaustive source census;
require exact equality to all three ballot digests and the declared folder/byte
facts. Only after every equality holds may ASCII `A`-`F` be converted to lowercase
for `exhaustive_archive_manifest_full_sha256` and `source_census_sha256`; the
underlying digest bytes may not change. Second, independently verify the exact
eleven-key decision-child manifest below and copy only its externally computed
lowercase full-file SHA-256 into
`decision_child_manifest_full_sha256`. The complete three-field disposition is
accepted or rejected as one unit. No legacy alias or substitute hash is read,
written, or mirrored. None of the fourteen fixed golden vectors contains this
actual I12 preimage, so their bytes and hashes remain unchanged.

`budget_resource_cap=NONE` is the only valid literal for this instrument and
preserves every fixed ceiling and serialization rail in Section 16. A narrower
or additional cap requires an amended audited correction and refreshed key;
free-form or non-`NONE` ballot text invalidates this key rather than being
interpreted by an executor.

Stage 2 reuses the exact Section 13.1 canonical-root normalization. Resolve the
sealed packet, ratification/scope records, four predecessors, and owner decision
records only beneath that verified non-reparse operator-context root; compare
their literal root-relative paths and bound bytes/hashes. The correction alone
is resolved from the owner-bound Git blob. An exact copied/reconstructed packet
outside that namespace remains inadmissible. These root fields are also mandatory
in the Section 8 PASS-TO-LAUNCH authority object.

The owner must provide the filled block directly; no agent chooses or paraphrases
a value. The mechanically captured decision record is
`state/agent-inbox/b1b-dispatch-owner-decision-2026-07-13.md`, UTF-8, LF-only,
no BOM, one final LF. The recorder replaces only the zero canonical-hash field
using the same zero-field rule, computes the full-file hash, and the gate auditor
independently reproduces both. That record is authoritative only together with
the direct owner reply and all bound hashes.

When `I12-EXHAUSTIVE-ARCHIVE-COMPLETE` is selected, the cited exhaustive archive
remains immutable: no descendant or byte is added to it. Dispatch remains blocked until
a new absent sibling lane
`C:/p6store/inbox-archive/<UTC>-b1b-decision-child/` contains exactly the final
decision record plus `DECISION_ARCHIVE_MANIFEST.json`. That manifest binds the
parent folder basename, parent manifest bytes/full hash, parent aggregate,
owner-bound main SHA, decision record bytes/full hash/canonical hash, and
correction bytes/full hash. Its schema is closed at exactly eleven total keys:
`schema_id="layer3.b1b.decision_archive_manifest.v1"`,
`parent_folder_basename`, `parent_manifest_bytes`,
`parent_manifest_full_sha256`, `parent_aggregate_sha256`,
`owner_bound_main_sha`, `decision_record_bytes`,
`decision_record_full_sha256`, `decision_record_canonical_sha256`,
`correction_bytes`, and `correction_full_sha256`. The exact type/source map adds
no key or alias:

- `schema_id` <- exact `layer3.b1b.decision_archive_manifest.v1`;
- `parent_folder_basename:T` <- ballot `i12_archive_folder`;
- `parent_manifest_bytes:P` <- ballot `i12_manifest_bytes`, which equals the
  actual `ARCHIVE_MANIFEST.json` byte length;
- `parent_manifest_full_sha256:H` <-
  `i12_disposition.exhaustive_archive_manifest_full_sha256`, which equals the
  lowercase form of validated ballot `i12_manifest_full_sha256`;
- `parent_aggregate_sha256:H` <- the lowercase form of validated ballot
  `i12_aggregate_sha256`, already independently equal to the actual parsed
  manifest aggregate;
- `owner_bound_main_sha:G` <- ballot
  `post_correction_project6_origin_main_sha`, which equals
  `authority.owner_bound_main_sha`;
- `decision_record_bytes:P` <-
  `authority.dispatch_owner_decision.byte_length`;
- `decision_record_full_sha256:H` <-
  `authority.dispatch_owner_decision.full_sha256`;
- `decision_record_canonical_sha256:H` <-
  `authority.dispatch_owner_decision.canonical_sha256`;
- `correction_bytes:P` <- `authority.correction.byte_length`; and
- `correction_full_sha256:H` <- `authority.correction.full_sha256`.

The lowercase full-file hash
copied into `i12_disposition.decision_child_manifest_full_sha256` is computed
externally over the complete canonical manifest bytes; the manifest contains no
self hash, receipt hash, timestamp, status, PENDING field/marker, or invented
provenance/history field. The ballot's uppercase validation-before-lowercasing
rules remain unchanged, and the external child-manifest self hash remains outside
the child. Apply the same canonical destination containment,
named-mutex, free-space, no-reparse, one-create, no-overwrite, failure-census,
and independent-second-read rules as Stage 1. No pre-dispatch tracked citation
is required for this sibling because that would recurse; its receipt is
mandatory at Gate 1 and is cited in the eventual B1b records closeout. When the
pending-I12 choice is selected, no decision-child copy is made and the decision
record joins the next record-lane archive under the explicitly accepted pending
risk.

Prospective publication baseline, only if a final correction identity is landed
and published: **Stage 1 unmarked/not authorized; Part A unmarked; Part B
unmarked; second key not granted; no dispatch authorization.** These bytes do
not self-establish freeze, publication, landing, implementation, or authority.
After a final identity exists, the baseline remains identity-conditional and is
not rewritten by a later owner act; current posture is carried only by the
hash-bound authorization/decision records, applicable archive receipts, and
tracked status mirrors.

## 14. Entry, acceptance, and failure gates

### 14.1 Entry gates

All entry gates are conjunctive:

1. Reverify the exact successor packet, predecessor-chain, and F07 bindings in
   Section 2, including canonical packet hash and every fixture property.
2. Reconfirm D33 and D34 from tracked decision authority.
3. Capture and independently verify the valid final owner-decision record from
   Section 13 with Part A granted and exactly one valid I12 posture. If archive-
   complete is selected, its already-complete receipt must match the citation on
   the supplied current main and the decision-child archive must independently
   verify; Stage-1 archive authority alone is never dispatch.
4. Reverify correction file bytes/hash equal its Git blob at the owner-bound main.
5. Fetch `project6-origin/main` and require it still equals the exact SHA in the
   final owner key. GitHub mergeability and required-check success do not satisfy
   this equality, especially while branch protection is non-strict.
6. Start from a clean worktree based on that current `project6-origin/main`,
   confirm no active agent owns it, and rebase the migration head before any
   model or migration edit.
7. Record the exact 58-path phased fence, three-principal ownership, isolated
   roots/databases, process/memory/disk/network ceilings, and stop actions before
   edits or runtime.

### 14.2 Acceptance gates

B1b final success requires the implementation, independent audit, mandatory
review, merge, merged-main rerun, and post-merge records closeout to prove all of
the following against isolated empty runtime state:

- D33/D34 hashes, constraints, indexes, receipt uniqueness, foreign keys,
  rollback behavior, and the exact no-historic-backfill/joint-null posture.
- The scoped flag-off parity contract in B1b-01 and zero B1b row/application-file
  deltas, with only its three explicit additive inventory/route/schema exclusions.
- The exact authoritative first-path row/file contract for both authorized
  profiles and the SQLite-authorized replay contract in Section 6, with all
  unexpected rows and files censused as zero.
- The F07 file is reverified before every read, after each profile-applicable
  package/handoff/replay checkpoint, and at closeout; all four predecessor
  artifacts retain their bound bytes/hashes.
- The complete single-cause fixture-negative vectors are exact: default maps
  only `reverified=false` to `authority=FAIL` with every other evaluated default
  gate PASS and `processes=NOT-RUN`; an authorized profile maps the same complete
  negative only to `fixture=FAIL`, keeps its other evaluated preflight gates
  PASS, and leaves launch/processes/post-launch gates NOT-RUN. Both close as
  preflight FAIL/resource PASS/invocation FAIL with five bound/six physical
  files. Fixed-field/content/path/readability/identity/incomplete fixture state
  remains no-root; gate arrays, counts, and order remain unchanged.
- For `sqlite_authorized`, exact-I1 equivalence reuse and divergent-decision
  `409 promotion_identity_decision_conflict` behavior.
- All SQLite races plus the exact ten-case PostgreSQL receipt, fixed node/case
  order, case-fixture bindings, same-database/schema isolation, pre-case zero/I1-
  absence checks, reverse-FK/file-move cleanup, exact facts, event/outcome
  adjacency, gate algebra, and both rollback cases in Section 10. Only completed
  case-10 cleanup permits final canonical F07 C0.
- Event-local J/PID/ordinal/T/HTTP/count bounds, exact `13244` event algebra,
  `1997/2001` case vector, `2048/2052` case ceiling, and `4096/4100` universal
  ceiling reproduce mechanically without padding or a new event. Deselect argv/
  expected arrays are exactly `9/10/0` for flag-off SQLite/authorized SQLite/
  PostgreSQL and zero for every other invocation.
- The exact one-snapshot promoted session, existing-reference raw reuse, no second raw copy, and full chain back to the approved receipt.
- Exactly one native 3C typing/unit/group/set chain, all three frozen C01
  canonical preimages/hashes, code-identity receipt, and, for
  `sqlite_authorized`, the exact `sandbox_a` then `sandbox_b` lifecycles: create
  each role once, materialize one semantically identical but physically distinct
  immutable DatasetVersion counterpart, capture its materializer checkpoint,
  continue without namespace recreation, run one method against that same
  role-local row, and capture its method checkpoint.
- For `sqlite_authorized`, approved result/package reviews and server-derived
  connector evidence without request widening; PostgreSQL remains the declared
  migration/concurrency/row-file proof with null three-way objects.
- For `sqlite_authorized`, exactly one reconciliation row, three package rows,
  the acyclic nine-member package/index contract, four ordered external outcome
  receipts, post-close double hashes, and the recursive no-leak/redaction fence.
- For `sqlite_authorized`, prepare and deliver preconditions, exact canonical-
  internal delivery bytes, and zero handoff product/DB row, file, or in-place mutation.
- The three new write routes pass pre-body authorization and exhaustive route-registry tests.
- All eight support-matrix surfaces agree; the dependent capability-count, independent
  pinned-list, local-profile ambient-env, current-doc, nonlocal-startup, and production-
  Compose guards in Section 7 agree; and every applicable environment example pins the flag
  to false.
- The synthetic-only boundary remains visible in API, evidence, package, support, and closeout language.
- The one-snapshot competing-process census uses only the six fixed executable
  basenames, exact PID/start identity and final-basename recheck, no role/path/
  command/image hash, and zero matches. Every launched statusless process ledger
  has one launch, exact target exit, and one-for-one ordered equality only with
  quiescent-boundary resource observations; cadence performs no process census.
  The preflight-only branch
  instead has no process ledger and exact `preflight_only_job` runner plus two
  sole-process RSS samples bound to its two observations, wall zero, and
  `processes=NOT-RUN`. RSS remains observational. Hard Job limits/accounting
  enforce process/memory bounds, resource ledger enforces applicable target wall,
  and controller closeout enforces D1.
- Preflight, resource, endpoint, census, test, invocation, and aggregate status
  partitions distinguish complete predicate-backed FAIL from structural no-root.
  Nonzero resource-projection FAIL stops before the projected action; every
  actual bounded state remains within one GiB; PostgreSQL counts point-in-time DB
  size plus all lane-attributable local/evidence/control bytes. Every writable PG
  location resolves to the same one fixed volume; the four-GiB floor is policy
  headroom, and every retained lane consumes one of the exact 14 two-cycle slots.
  Worker-local breach permits only
  bounded evidence-only failure finalization, while an outer-controller stop
  forbids later worker writes. The first controller resource stop is immutable
  and uses the fixed same-elapsed precedence. Launched endpoint proof has one
  global ordinal, zero egress, exact bound role, 128-attempt/129th-denial control,
  exact local closes/control ordinals, monitor EOF/exit closure, and no free role/
  class/hash or raw endpoint field. SQLite
  preflight-only performs zero database connection and creates no endpoint
  ledger. PostgreSQL preflight-only proves exactly one approved same-endpoint
  unpooled read-only runner host connection, no reconnect/pool, fresh terminal
  point-in-time size, closure before evidence, no target/child event or monitor/provider/
  application connection, and no endpoint ledger through its preflight storage
  binding plus resource-ledger binding/closure.
- Provider disposition is exact for default, unregistered, discarded, and
  consumed vectors. Authorized orderly early FAIL closes terminal/final cadence/
  EOF/exit only under an independent failure; partial C3/provider state or abrupt
  death is no-root. Containment binds attempt ID and the exhaustive domain/class/
  path-namespace artifact union after applicable target or preflight-only
  closure; the no-target branch requires an empty array, resource hash only, no
  process array or source-stage field, and exact verdict/stop/containment/manifest
  write order.
- All inherited process, memory, disk, wall, database-isolation, and egress rails
  pass with no competing heavy runtime. Path 30 runs only as the outer controller
  plus its private inner worker, adds one PowerShell process and zero Python
  processes, reproduces every frozen PowerShell/catalog/certificate and wheel/
  DLL/export pin, and proves configured/read-back Job plus ready watchdog,
  `attempt-D0`/`attempt-D1`/`attempt-D2`, and armed timer before durable intent as
  the last pre-`CreateProcess` act. The worker is created atomically in the Job by
  exact `JOB_LIST`, then identity-bound; exact immutable deadline mapping
  publication/hash and writable teardown precede
  ordinal-1 sample, final guard, and one successful resume with prior suspend
  count one. Any earlier post-create failure leaves the orphan bar and no
  closeout/disposition; only a later sample/guard/resume failure is eligible
  for a null-manifest closeout. Exact native free-memory, per-process RSS,
  controller-peak, and outer-controller Job-peak APIs; explicit outer Job handle
  for census/peak versus worker-`NULL` only for count/PID census; no worker
  `PeakJobMemoryUsed` query; stable two-census count/list and identity validation;
  one middle read; checked sums; cleanup-before-timestamp; and query/cadence
  classification pass. The outer one-second monitor remains active and independent
  through preflight-only worker exit; its clock/ordinals never substitute for the
  worker's two persisted resource samples. The sole complete, canonical,
  predicate-backed `preflight/false,test_terminal=false` branch may close its
  handles and perform bounded FAIL finalization; every structural, incomplete,
  or other pretarget stop is no-root, and an outer-controller stop permits no
  worker finalization.
  Exact `Q=2` and the frozen `1|2|3`, `4`, `5`, `4|5`, `6/1`, terminal-zero Job
  accounting vectors pass. Inherited descendant custody, D1 Job termination, D2
  controller self-termination absent valid closeout acknowledgement, required non-Job-handle closure before post-closure Job zero,
  remaining handle closure, and exactly one valid `CONTAINED|BARRED_UNKNOWN`
  closeout also pass. Outer preliminary/final Job-peak accounting is resource-
  only: complete monotonic evidence is required for resource `PASS|FAIL`, while
  failed or null peak evidence leaves independently proved `CONTAINED` unchanged,
  sets resources `INCOMPLETE`, and bars profile admission. The Section 16 B2
  predicate mapping creates no legacy artifact. Only
  `CONTAINED` attempts with a bound worker manifest and complete `PASS|FAIL`
  resource/control-storage results may enter `profile_verdict.v2`; v1, alias,
  fallback, incomplete, orphan, and barred state never do. The registered two-phase C3 provider
  success/discard transitions, complete anchored final tail, profile/control
  high-water cap, and sequential one-buffer finalization-space observations also
  pass exactly.
- Fetch and require exact owner-bound `project6-origin/main` equality at Gate 1,
  before the Gate-2 audit, and immediately before Gate-3 merge. Any remote-main
  advance stops the lane: rebase the branch and Alembic head, obtain a refreshed
  compound key bound to the new main SHA, and rerun Gates 1-3 from the resulting
  unchanged head. No earlier audit or owner-bound baseline is carried forward.
- The external gate audit and independent review use their exact closed schemas,
  fixed check arrays, expected distinct principals, candidate/audit bindings, and
  same-handle Windows no-follow/ReadOnly reread proof. Their external files remain
  outside every repo/evidence/aggregate root. Final premerge/merged bindings use
  exact schema, basename, head, bytes, hash, and status without generic artifact
  aliases.
- Targeted tests, migration upgrade and rollback/containment checks, all relevant CI,
  `git diff --check`, changed-file fence, and a fresh final re-audit all pass. The executor
  must freshly query the branch rule/check set; GitHub's required-check floor is not a license
  to ignore another relevant failing or missing check.
- Only bounded synthetic direct-intake-to-local-handoff loop success may be claimed after
  merge and an independent rerun from current merged `project6-origin/main` under the same
  acceptance contract. Real connector acquisition-to-intake integration remains unproven.
- Paths 50-58 then land as a docs-only evidence sync; before that, no final PASS
  or administratively closed claim is allowed. A separate post-closeout human
  reviewer must then directly produce the exact Section 9
  `records_semantic_review` object over that landed nine-path diff. A semantic-
  review FAIL is the final gate's first valid FAIL and leaves records parity NOT-
  RUN; a missing, malformed,
  noncanonical, or inconsistent review creates no final root. Only after semantic-
  review PASS, immediately before deriving the one inline records verdict, the
  final aggregator performs exactly one fresh fetch: fetched
  `project6-origin/main` must equal the closeout commit and contain the merged-
  proof base as an ancestor. Authority-check failure creates no final root, not
  parity FAIL; there is no earlier records aggregator or second fetch.

### 14.3 Hard failures

Any one of these fails or blocks the lane:

- Invalid or absent final compound authorization, treating Stage 1 as dispatch,
  packet/predecessor/fixture/correction hash mismatch, unverified I12 selection,
  authority ambiguity, worktree collision, or stale migration head.
- Mapping a complete fixed F07/C01 projection with only `reverified=false` to
  any default gate other than `authority` or any authorized gate other than
  `fixture`; duplicate/cross-profile routing; treating a fixed-field/content/
  path/readability/identity/incomplete fixture failure as valid FAIL; altering
  the authority hash/preimage, gate arrays, counts, or order; or creating,
  opening, or hashing PASS-TO-LAUNCH for default or any preflight-only failure.
- Owner-bound main SHA drift at any gate, reuse of an audit after rebase, or merge
  against a newer remote main merely because non-strict branch protection allows it.
- Any default true, runtime auto-enable, nonlocal flag acceptance, production-Compose
  threading, historic automatic backfill, or unsupported scope expansion.
- Option I used as authoritative receipt; intake uniqueness substituted for receipt uniqueness; or a digest substituted for component comparison.
- Duplicate or partial receipt/materialization rows; a non-approved decision occupying identity; or a divergent decision mutating state.
- Any authoritative/promoted row or file delta outside Section 6; any retained failure artifact that is not rehashed, censused, isolated, and containment-only; any reuse of such an artifact without exact-basis validation; any second raw copy, mixed session, relabeled connector snapshot, or generated seed artifact.
- Shared-session pseudo-concurrency, SQLite-only concurrency proof, PostgreSQL
  ten-case/node/event omission, variant case identity, case ID entering semantic
  authority, cleanup failure or false completion, later case after first FAIL,
  final C0 before case-10 cleanup, receipt census backlink, or whole-receipt FAIL
  substituted for a mapped gate.
- Any J/PID/ordinal/T/HTTP/count overflow, event algebra above `13244`, vector or
  frame-ceiling mismatch, padding/new event, or deselection count/order/argv/
  expected-array drift from exact `9/10/0`.
- Authentication after body parsing, `422` before absent/untrusted identity rejection, missing static route entry, or route-registry drift.
- Any secret, identity header, raw storage reference, absolute local path, credential-bearing URL, full raw object, undeclared package member, fourth package kind, or APS substitution.
- Any package/hash mismatch, mutable deliver path, handoff row/file creation, or delivery bytes differing from `canonical_internal`.
- Any circular/self hash, embedded claim of a post-package outcome, rewritten
  package after close, missing external outcome receipt, or final verdict before
  rehash/handoff/replay/census completion.
- Any missing or inconsistent one of the exact eight support surfaces or applicable false-valued environment examples.
- Any real ScienceBase/USGS network acquisition, official-public-read claim, OUTWARD work, browser/UI expansion, or production invocation in B1b.
- Any selected `analysis.exe|project_api.exe|pytest.exe|python.exe|pythonw.exe|
  uvicorn.exe` competitor, inaccessible/drifted one-snapshot census candidate,
  persisted process role/path/command/image hash, external egress, unprevented
  resource-ceiling breach, shared database/artifact root, second heavy lane,
  retained-slot reuse, or slot 15 reaching lane/root/control/process creation.
- Any PowerShell path/byte/version/architecture/hash/catalog/certificate mismatch,
  wheel/DLL/hash/export/`PQlibVersion`/`LoadLibraryExW(0x900)` mismatch, runtime-
  derived trust substitution, OS-servicing drift without a successor candidate,
  `Add-Type`/CodeDOM/`csc`/temporary assembly, or helper file/process.
- Any attempt-deadline reset; direct/replayed worker invocation; failure to make
  durable intent the last pre-`CreateProcess` act; failure to configure/read back
  hard Job limits or ready watchdog/D0/D1/D2/armed timer before intent; post-create
  `AssignProcessToJobObject` or fallback; wrong/missing `JOB_LIST`; a closeout/
  disposition for any failure before the complete closeout-eligibility boundary; ordinal-1
  sample, guard, or resume before full mapping validation/hash and writable
  teardown; probe, worker, or target resume before required Job custody;
  breakaway; inheritance of controller Job, timer,
  mutex, process, writable-section, closeout, or other control handles except the
  exact read-only deadline-section handle; a missing/extra/inherited-to-target
  section handle, invalid mapping byte/hash/canonical payload, writable reference
  at resume, resume count other than one, or post-`attempt-D1` probe/launch/resume/
  ACK/frame/evidence/root action; containment-time use as proof time; a
  controller surviving D2 without valid closeout acknowledgement; a `CONTAINED`
  disposition without every physical-exit, Job-zero, atomic Job-list creation,
  descendant-custody, close-before-Job-zero, and handle-closure
  predicate; incomplete resource/control-storage evidence entering a root; any
  PASS-manifest/nonzero-exit or FAIL-manifest/zero-exit attempt;
  disposition other than `CONTAINED|BARRED_UNKNOWN`; any later runtime after
  barred/orphan/torn/inaccessible control state; or any v1/alias/fallback profile
  verdict; or any `Q` other than two or terminal Job accounting outside exact
  `1|2|3`, `4`, `5`, `4|5`, `6/1`, and active-zero cases.
- Any alternate free-memory/RSS provider; missing `MEMORYSTATUSEX.dwLength` or
  `PROCESS_MEMORY_COUNTERS_EX.cb`; wrong native API/field; failure to use an
  explicit outer Job handle for census/peak or worker `NULL` only for count/PID
  census; any worker `PeakJobMemoryUsed` query; unchecked/overflowed census
  allocation; null or
  inconsistent `ReturnLength`; count/list/required-byte/truncation/zero-slot/PID-
  uniqueness violation; closing a borrowed sample handle or leaking a temporary
  one; RSS access other than exact `0x410`, identity access other than `0x1000`,
  elevation/`SeDebugPrivilege`/`PROCESS_ALL_ACCESS`; more than one middle working-set read; accepted identity/PID-reuse/set
  drift; unchecked RSS sum or shared-page equality claim; elapsed timestamp
  before cleanup; query/cadence misclassification; or PostgreSQL engine RSS
  inclusion claim. A missing/failed final Job peak or final below a nonnull
  preliminary peak must preserve independently proved `CONTAINED`, force
  resources `INCOMPLETE`, and bar root admission; any other handling fails.
  Treating null/failed preliminary or final peak as a custody failure, treating
  any resource query including either Job peak as custody, omitting post-closure
  `ActiveProcesses==0`, or creating/admitting any legacy scratch, raw-output, or
  receipt artifact also fails. Replacing the immutable earliest resource stop,
  violating same-elapsed reason precedence, assigning an ordinal to an invalid
  query/cadence sample, quiescent-boundary process/resource sample mismatch, or wrong
  `preflight_only_job` nullability, runner identity, two-sample ordinal/count/RSS,
  sole-Job-member, observation, wall, projection, evidence-byte, or handle-closure
  fact also fails. So does enforcing process caps in the statusless process
  ledger; admitting an actual bounded state above one GiB; omitting a writable
  PostgreSQL data/tablespace/temp/WAL location, resolving more than one fixed
  volume, treating `pg_database_size` as transaction-consistent/physical-complete,
  claiming the four-GiB floor proves 14 GiB, or running full process/file/PG census
  on cadence; executing a projected
  action after its breach; performing a runtime/application mutation or ACK after
  a worker-local measured breach; performing any worker evidence/root write after
  an outer-controller stop; bypassing bounded evidence-only finalization;
  treating the sole complete, canonical, predicate-backed
  `preflight/false,test_terminal=false` branch as no-root; admitting a structural,
  incomplete, or other pretarget stop as a valid root; or converting incomplete
  census/provider/cleanup/exit state into valid resource FAIL.
- C3 provider replacement/reentry, wrong state/sample/binding, or failure to
  perform irreversible discard after registration on a normal non-PASS or
  missing-success path; partial or interleaved
  publication, plugin census-byte access, added C3 control handle, or ACK-epoch
  alias; invalid final-cadence anchor or delayed/misordered join, EOF, or exit;
  terminal-subtotal substitution for the profile high-water; future-draft
  precomputation; or missing, bypassed, identity-drifted, low-space, wrong-reserve,
  non-PASS-nested, or inconsistent finalization observation. A wrong/missing
  provider disposition, partial C3 vector, discarded-provider PASS, discarded
  provider without orderly failure tail, or abrupt death represented as FAIL also
  fails. So does an endpoint ordinal/count/control mismatch, unclosed local
  attempt, allowed external attempt, monitor without final-cadence/EOF/exit proof,
  raw endpoint field, free/unbound database-role classification, mismatch from the
  exact preprovisioned role/membership/three-connection contract, failure to count
  a successful/failed request, or any side effect on the mechanical 129th; any SQLite preflight-only
  database connection; or a PostgreSQL preflight-only zero/multiple/alternate-
  endpoint/reconnected/pooled/unclosed host connection, target/child endpoint
  event, monitor/provider/application connection, endpoint ledger, or preflight/
  resource storage-binding mismatch.
- Any containment source-stage/owned-process/free-class field, wrong domain/class
  map or order, missing attempt ID, nonexhaustive outside-evidence artifact scan,
  live target/descendant worker root, wrong ledger-nullability, or write-order
  mismatch.
- Missing, malformed, noncanonical, principal/head/audit/status/count-inconsistent,
  path-ambient, shared-principal, reparse/writable, basename-drifted, or same-
  handle-reread-failing independent audit/review input; copying either assessment
  into a repo/evidence/aggregate root; or generic artifact-ID substitution.
- Any relevant failed or missing CI/check, unresolved critical/blocking finding, missing
  schema rollback/containment evidence, or changed-file fence breach. The mechanically
  required branch-rule check set is only a floor.
- Missing, malformed, noncanonical, commit/diff-mismatched, or status/count-
  inconsistent post-closeout semantic review; a semantic-review FAIL followed by
  records-parity evaluation; or any records fetch/parity operation before the
  valid review PASS.

## 15. Exact nonclaims and standing

This correction preserves the following nonclaims and limitations:

- That B1b is authorized, implemented, reviewed, merged, or run.
- That Option II is schema-free or that current P1 already implements it.
- That current Gate-B emits canonical 3C, or that current handoff consumes connector-derived DatasetVersions.
- That existing tests prove B1b.
- That a native intake `409` is a direct receipt pointer, or that changed replay may continue.
- That separately proven seams constitute one integrated HTTP loop.
- That an agent can make an owner decision or select the I12 deviation.
- That the synthetic fixture is official ScienceBase/USGS data or proves real acquisition, public availability, production readiness, connector breadth, utility, causality, temporality, representativeness, or population-wide inference.
- That B1b changes global redaction posture, grants value reveal, enables default-on behavior, proves durable off-repo preservation, or proves operating-system immutability.
- That B1b authorizes OUTWARD, nonlocal, network, browser, UI, or generalized security work.
- No progress is guaranteed while relevant user-mode execution is suspended.
- No driver or kernel-mode blocking operation is guaranteed cancellable.
- No physical worker exit exactly at D2 is guaranteed.
- No protection against malicious same-user handle duplication or control-artifact deletion is claimed.
- No replayable measurement of the controller closeout serialization's own RSS is claimed.

In the third custody nonclaim, `D2` means the exact nonresetting `attempt-D2`;
the bullet itself remains the required fixed string.

Current entry standing remains exactly:

`B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`

Standing advances only on the corresponding evidence:

- after a valid final owner decision but before runtime:
  `B1A-PASS; B1B-AUTHORIZED-NOT-RUN; INTEGRATED-LOOP-NOT-PROVEN; SCHEMA-NOT-CHANGED.`
- after an authorized implementation merge but before the merged-main proof:
  `B1A-PASS; B1B-MERGED-PROOF-PENDING; INTEGRATED-LOOP-NOT-PROVEN; SCHEMA-CHANGED-AS-AUTHORIZED.`
- only after every merged-main acceptance gate, landed post-merge records
  closeout, valid post-closeout semantic-review PASS, and records-parity PASS:
  `B1A-PASS; B1B-PASS; BOUNDED-SYNTHETIC-DIRECT-INTAKE-TO-LOCAL-HANDOFF-LOOP-PROVEN; REAL-CONNECTOR-ACQUISITION-TO-INTAKE-NOT-PROVEN; SCHEMA-CHANGED-AS-AUTHORIZED; O5-OPEN-DEFERRED.`

A failed, stopped, or partial run records its actual blocked/failed state and
must not copy the success standing.

## 16. Resource serialization and closeout ownership

If dispatch is later authorized, resources are serialized as follows:

The predecessor's B2-01 through B2-16 safety predicates remain mandatory, but
Sections 8-9 fully supersede every legacy wrapper, topology, provider, API,
scratch, probe, monitor, raw-output, and receipt mechanism. The mapping is exact:

- B2-01 through B2-07 old single-root/SQLite topology map to one new absent/
  empty, non-reparse lane parent with four direct sibling `runtime`, `storage`,
  `database`, and `evidence` roots and one isolated database identity per
  profile. The preserved predicates require the parent and every child absent
  before creation and empty immediately after, every root outside the repo and
  OneDrive, no reparse or namespace escape, and complete handle/canonical/
  containment validation before any write. The parent remains
  `%LOCALAPPDATA%/project6-b1b/<owner-decision-hash-prefix>-c<1|2>-s<01..14>-<backend>-<nonce>`;
  SQLite and PostgreSQL lane parents/database identities are distinct and run
  serially. Absolute paths remain process-local; persisted evidence uses only
  lane-local IDs, namespace hashes, relative descendants, volume facts, and
  containment booleans.
- B2-08 old Win32 provider/raw-census mechanics map to the existing namespace
  mutex plus the exact one-`PROCESSENTRY32W` six-basename competing-process
  census, preserving exclusive lock ownership, zero unexplained competitors, and
  fail-closed inaccessible/PID-reused/basename-drifted process handling without a
  path, command, role, or executable-byte hash.
  That census remains distinct from every owned Job census. B2-09 old wrapper
  mechanics map to the sole outer controller, its private inner worker, and one
  serial Python target, preserving no xdist, GPU, uvicorn, background helper,
  second target, simultaneous backend, or shared profile DB, plus the same wall
  and stop bounds.
- B2-10 and B2-11 scratch `sitecustomize`/`PYTHONPATH`, config-probe, raw guard/
  load, and zero-attempt-receipt mechanics map universally to the existing
  endpoint policy, isolated `-B -I` probes, and preflight; only on launched paths
  and when applicable do they map to the existing monitor, existing-pipe
  endpoint-attempt events, bound plugin, and endpoint ledger.
  They preserve zero egress, validate-only behavior, and no application state.
  B2-12 and B2-14 CIM/Win32 raw memory/process receipt mechanics map to the exact
  Section 8.1 native measurement rule, statusless process ledger, resource
  ledger, worker manifest, and closeout schemas, preserving the four-GiB free-
  memory floor and fail-closed unexplained/inaccessible process result. B2-13's
  threshold is retained and strengthened by enforcement at every accepted
  sample.
- B2-15 scratch STOP-evidence mechanics map to exact process/resource/closeout
  evidence, status partitions, immutable first-resource-stop precedence, fixed
  gate arrays, and code-free stop schemas, preserving one-second cheap cadence,
  hard `ActiveProcessLimit=3`/`JobMemoryLimit=1610612736`, observational RSS,
  900-second proof termination, retained containment evidence, and no retry.
  A preflight-only worker has the exact persisted two-sample resource branch while
  the controller's independent one-second cadence continues unchanged.
  B2-16 raw prelaunch-receipt shape maps, in order, to durable attempt intent,
  preflight, the current Section 8 launched-authorized PASS-TO-LAUNCH record,
  existing ledgers, and durable closeout, preserving prelaunch order and finality;
  `sqlite_default` creates no PASS-TO-LAUNCH record. No legacy scratch, raw-
  output, or receipt file is added or becomes an evidence member. Legacy names
  occur here only as explanatory supersession prose.

Sections 8-9 remain the sole exact resource contract. In summary: external/DNS/
non-loopback budget is `0` except the one verified same-host PostgreSQL endpoint;
SQLite loopback/socketpair plumbing stays separately classified; no competing
heavy process, xdist, GPU, helper, second plugin, or simultaneous backend is
allowed; sampled free memory and the one fixed volume resolved for every bound
writable location remain at least `4294967296` bytes; Job active count/memory are
hard-limited at `3`/`1610612736`, while per-process RSS is observational;
conservative pre-closeout-serialization controller-plus-Job private committed
memory remains at most `2147483648`; lane-attributable local/evidence/control
bytes plus the point-in-time PostgreSQL database size remain at most `1073741824`;
target wall time is at most `900` seconds; and fixed nonresetting `attempt-D1`/
`attempt-D2` intervals are `900000`/`930000` milliseconds. No continuous RSS or
free-memory claim is made. Evidence stores only redacted endpoint classes/hashes.

B1a wrappers remain historical and unusable. Path 30 is the sole B1b `run-*`
wrapper: default outer controller plus controller-only private worker mode. It
adds exactly one PowerShell process and zero Python processes. Direct/replayed
worker use, another controller/helper, command passthrough, seed/generate/report,
browser/UI, or extra pytest arguments fail.
Both PowerShell modes reproduce the frozen Section 8 image/catalog/certificate
contract; neither derives or substitutes trust at runtime.

The controller alone owns the namespace mutex, retained-lane census, roots, Job,
watchdog/timer, durable intent, transient deadline mapping, atomic suspended
worker creation in the Job/resume, outer resource sampling, `attempt-D1` Job
termination, `attempt-D2` self-termination, Job/accounting closure, and durable closeout. The worker alone
reopens bindings, runs serial Job-bound probes and an applicable target,
maintains worker evidence, closes its handles, writes its manifest last, and
exits. The only lane-parent
control basenames are `attempt-intent.json` and `attempt-closeout.json`; neither
is worker evidence.

Path 29 mechanically tests the complete Sections 8-9 contract: all static pins,
PowerShell/catalog/certificate and wheel/DLL/export pins,
and the 58-path fence; private-mode/mutex/prior-lane bars; intent order and orphan/
torn/inaccessible handling; atomic `JOB_LIST` creation, inherited Job custody,
breakaway/handle denial, transient mapping, `attempt-D0`/`attempt-D1`/`attempt-D2`
and every `CONTAINED|BARRED_UNKNOWN` predicate; v2-only aggregation; serial owned
`-B -I` probes; no post-`attempt-D1` state production; sampled/peak resource,
endpoint, exhaustive writable-location storage, point-in-time database, 14-slot/
two-cycle lane cap, one-GiB combined cap, four-GiB policy floor, reserve, one-
buffer, and closeout arithmetic;
manifest/exit equality; worker-bootstrap positives for exact
`SECTION_MAP_READ` desired access, `bInheritHandle=TRUE`, `dwOptions=0`,
`bInheritHandles=TRUE`, exact
`EXTENDED_STARTUPINFO_PRESENT|CREATE_SUSPENDED`, the exact two attributes with a
noninherited Job handle and the same raw
`deadline_section_handle` value in the private-worker argument and exact one-
entry handle list, `FILE_MAP_READ`, closure, and nonforwarding; negatives for a
missing, duplicate, malformed, zero, `INVALID_HANDLE_VALUE`, overflow, out-of-
range, wrong, or nonmapping locator rejected before application import/state,
plus an injected extra handle-list entry rejected before `CreateProcess`;
  exact two-handle target inheritance; C3 provider/pause/ACK/control-
  frame/final-tail rules; environment/RECORD/pip and source-cache integrity; and
  clean/abrupt failures. It also proves exact six-basename process selection and
  deleted process fields, launched-only statusless ledger/sample pairing, the
  exact no-target preflight-only resource branch, preflight/resource/endpoint/
  test/census/invocation status partitions, and absence of free stop codes.

Its inert positive/negative fixtures also prove the semantic-closure details without
adding a gate, path, process, or artifact:

- post-create failure before mapping length/hash and
  writable teardown leaves an orphan with no closeout/disposition, while only a
  later sample/guard/resume failure is closeout-eligible; the positive order is
  configured/read-back Job -> ready watchdog -> `attempt-D0`/`attempt-D1`/
  `attempt-D2` -> armed timer -> durable intent -> atomic suspended Job creation
  -> identity binding -> full mapping publish/hash -> writable teardown ->
  ordinal-1 sample -> guard -> one resume;
- exact `GlobalMemoryStatusEx`, `K32GetProcessMemoryInfo`,
  `PeakPagefileUsage`, and outer-only `PeakJobMemoryUsed` APIs/fields; explicit
  outer Job handle for census/peak versus worker `NULL` only for count/PID
  census; absence of a worker Job-peak query; checked count/list buffer sizing;
  nonnull `ReturnLength`; required/returned/allocated byte inequalities;
  assigned/listed/count equality; truncated/oversized output rejection; zero-
  count slot ignore; and PID range/uniqueness rejection;
- exact `Q=2`, active/memory Job-limit readback, preflight `1|2|3`, launched
  `4`, child `5`, valid-FAIL `4|5`, cap-denial `6/1`, and terminal-active-zero
  accounting vectors; D1 Job termination; and D2 controller self-termination;
- borrowed-versus-temporary handle ownership, exactly one middle
  `WorkingSetSize` read per member, identity round-trip, PID reuse, two-census set
  drift, checked RSS sums, the shared-page double-count nonclaim, temporary
  cleanup before elapsed timestamp, and exact query-failure versus cadence-
  failure classification;
- mandatory post-closure Job zero then remaining-handle closure; preliminary and
  final outer Job peaks as resource-only facts; successful final at least nonnull
  preliminary for complete resource `PASS|FAIL`; null/failed peak or monotonicity
  failure leaving independently proved `CONTAINED` unchanged while forcing
  resources `INCOMPLETE`; and rejection of any resource query as custody; and
- every B2-01 through B2-16 predicate-to-current-mechanism mapping plus proof
  that no legacy scratch, raw-output, or receipt artifact is created or admitted
  as evidence;
- immutable earliest resource stop plus same-elapsed reason precedence; exact
  quiescent-boundary process/resource pairing with cadence free of full process/
  file/PostgreSQL census; and the preflight-only field's
  conditional nullability, runner/closeout equality, two sole-runner censuses,
  observation bindings, RSS maximum, zero wall/projection/evidence bytes,
  preflight/terminal/handle-close/write order, PostgreSQL host reuse/close, five-
  bound/six-physical membership, `processes=NOT-RUN`, evaluated resource gate,
  empty containment, and independent outer cadence/clock;
- the default complete fixture-negative vector with `authority=FAIL`,
  environment/roots/resources/endpoints/tests PASS, and `processes=NOT-RUN`;
  the authorized complete vector with `fixture=FAIL`, authority/environment/
  roots/resources/endpoints/tests PASS, and launch/processes/post-launch gates
  NOT-RUN; structural fixture no-root variants; no duplicate/cross-profile route;
  and unchanged gate arrays/counts/order and five-bound/six-physical closure;
  plus the sole exact pretarget
  bounded-FAIL exception versus structural/incomplete/other pretarget no-root
  and outer-stop no-finalization vectors;
- worker-local breach versus outer-controller stop, bounded evidence-only failure
  finalization, projected-before-action FAIL versus actual over-cap no-root, and
  no process-ledger RSS/wall/attempt limit field;
- all endpoint event variants, exact 13244 event ceiling, 1997/2001 case vector,
  4096/4100 universal vector, global ordinal/count/control closure, mechanical
  128/129 attempt denial, monitor final-cadence/EOF/exit proof, conditional
  provider ordinal, denied-external valid FAIL, exact bound role and no free role/
  class/per-attempt endpoint hash/raw secret; plus SQLite preflight-only zero connection/no ledger and
  PostgreSQL preflight-only exact one approved same-endpoint unpooled read-only
  runner host connection, no reconnect/pool, fresh terminal point-in-time size, pre-evidence
  close, no target/child event or monitor/provider/application connection, no
  endpoint ledger, and exact preflight/resource storage binding;
- every profile's direct frozen test-manifest derivation/canonicalization/
  verification/hash and preflight binding, launched-authorized-only complete
  object/hash embedding and reopen in PASS-TO-LAUNCH, and no default or
  preflight-only PASS-TO-LAUNCH create/open/hash;
- default `not_applicable`, authorized `not_registered|discarded|consumed`,
  consumed-later-FAIL, partial-C3 no-root, discard orderly-tail, and abrupt-death
  vectors with exact test-result closure;
- ten PostgreSQL case schemas, fixed node order, register/event/outcome adjacency,
  case-identity nonauthority, same-database cleanup barriers, PASS-prefix/one-
  FAIL/NOT-RUN suffix, gate mapping, 2048-byte case ceiling, receipt-without-census
  backlink, physical evidence order, and 10-bound/11-total/9-input success plus
  5/10/11/12 failure counts;
- orphan/containment domain-class map, path-namespace identity, global ordering,
  attempt binding, null-ledger rules, empty array, post-target or preflight-only
  scan, and no
  source-stage/owned-process field; and
- exact external audit/review schemas and check arrays, principal/head/audit
  equalities and inequalities, same-handle Windows ingestion, external-assessment
  input kind, fixed final aggregate bindings, and no assessment copy/root/member.

Inert adapters may prove ordering only: they may not seed, network, manufacture
authority, create current-repo cache, or author preflight/control artifacts.
Ad-hoc shell monitoring is inadmissible.

The worker derives the same frozen test-manifest object directly for every
profile; only a launched authorized profile additionally embeds and reopens it as
`runtime.test_manifest` in PASS-TO-LAUNCH. That object is a closed
`layer3.b1b.test_manifest.v1` object with exactly `schema_id`, `python_policy`,
`plugin_policy`, `pytest_workers`, `no_extra_args`, `required_test_blobs`, and
`profiles`. `python_policy` is a closed object with exactly `policy_id`,
`implementation`, `major`, `minor`, `platform`, `architecture`, `release_lock`,
`proof_lock`, `overlap_rule`, `installed_set_rule`, `bootstrap_rule`,
`record_rule`, `pip_check_rule`, and `provisioning_rule`. Its scalar values are
exactly:

- `policy_id=cpython-3.12-x64-windows-b1b-proof-v1`,
  `implementation=cpython`, `major=3`, `minor=12`, `platform=win32`, and
  `architecture=AMD64`;
- `release_lock={path:"backend/requirements.lock.txt",git_blob:G,
  full_sha256:H}` and `proof_lock={path:
  "backend/tests/requirements-b1b-proof.lock.txt",git_blob:G,full_sha256:H}`,
  both resolved from the candidate head;
- `overlap_rule=proof-lock-runtime-overlap-must-equal-release-lock`,
  `installed_set_rule=exact-proof-lock-no-extras-no-editables`,
  `bootstrap_rule=pip-setuptools-wheel-explicitly-pinned`,
  `record_rule=all-installed-records-contained-complete-and-hash-verified`,
  `pip_check_rule=offline-exit-zero`, and
  `provisioning_rule=preproof-only-runner-never-installs`.

The release lock remains the Python 3.12 Linux CI/production application
dependency authority; it is not falsely treated as the complete Windows test
environment. The new proof lock is a complete `--require-hashes` CPython 3.12
x64 Windows closure compiled from the Layer 3 API test requirements under the
release-lock constraints. It pins pytest and every test/bootstrap/transitive
distribution, including `pip`, `setuptools`, and `wheel`; every distribution
shared with the release lock must have the identical normalized name/version.
The dependency reproducibility doc freezes the reviewed generation command,
inputs, target platform, and update procedure. Environment provisioning is a
separate, recorded pre-proof step; the proof worker performs no installation,
package resolution, index access, or other network activity.

Literal `python` in each manifest argv is a symbolic token, not a PATH lookup.
The worker accepts one configured absolute venv interpreter path out of band,
proves it is a regular non-reparse file inside the audited venv, and requires
`sys.implementation.name="cpython"`, `sys.version_info[:2]=(3,12)`,
`sys.platform="win32"`, and 64-bit AMD64. The attestation `python_runtime` is
exactly `{implementation:"cpython",version:<3.12.patch>,platform:"win32",
architecture:"AMD64",executable_sha256:H}`; it exposes no path. The worker
substitutes that verified executable for argv element zero, substitutes nothing
else, and has no PATH fallback. Wrong-PATH, shadow-`python`, wrong-patch-family,
wrong-platform, and wrong-architecture tests must fail before launch.

Before launch, the reviewed lock parser requires the normalized installed
`{name,version}` set to equal the proof-lock set exactly. Missing, extra,
editable, direct-URL, or version-different distributions fail; bootstrap tools
have no implicit exception. For every installed distribution, every `RECORD`
entry must remain inside the venv and every declared digest/length must match.
Blank wheel-metadata digest/length fields are allowed only for that
distribution's own `RECORD` row and interpreter-generated `__pycache__/*.pyc`
rows; those paths must still be unique, regular, non-reparse, contained, and
present. Any other blank field, missing metadata/file, traversal, duplicate
normalized path, or file outside the venv fails. Independently of wheel-declared
hashes, the worker computes SHA-256 and byte length for every listed file,
including the two allowed blank-field classes, so no file is exempt from the
post-install integrity ledger. The sorted distribution inventory and complete
per-distribution file aggregate are independently D33-canonicalized as
`environment_inventory_sha256` and `distribution_record_inventory_sha256`.
The worker executes exactly
`<venv-python> -B -I -m pip --isolated check` as its serial owned pre-census pip
probe under the scrubbed `PIP_CONFIG_FILE=NUL`, `PIP_NO_INDEX=1`,
`PIP_NO_CACHE_DIR=1`, and `PIP_DISABLE_PIP_VERSION_CHECK=1` environment. It
requires exit zero, complete descendant-tree reap, and empty stderr, and records
only the normalized output hash as `pip_check_output_sha256`.

Those three digests have exact preimages. Distribution names are normalized by
lowercasing and collapsing every maximal `-`, `_`, or `.` run to one `-`; an
empty/non-ASCII result fails. A version is the exact nonempty ASCII token after
`==` in the proof lock and must equal the installed `METADATA` version; it is
not re-rendered. The installed inventory is exactly
`{"distributions":[...],"proof_lock_full_sha256":H,"schema_id":"layer3.b1b.environment_inventory.v1"}`.
Each distribution entry has only `name` and `version`, and the array is sorted
by UTF-8 bytes of normalized name then version. Missing, extra, duplicate,
editable, direct-URL, or unequal entries fail before launch.

The RECORD inventory is exactly
`{"distributions":[...],"proof_lock_full_sha256":H,"schema_id":"layer3.b1b.distribution_record_inventory.v1"}`
in the same distribution order. Each distribution has exactly `name`, `version`,
and `files`. Each file entry has exactly `actual_byte_length`, `actual_sha256`,
`blank_reason`, `record_digest`, `record_length`, and `venv_relative_path`.
RECORD is decoded strict UTF-8 without BOM and parsed as strict CSV. A path is
resolved beneath the verified venv, made venv-relative with `/`, NFC-normalized,
and case-preserved; empty/dot/dot-dot segments, drive/UNC prefixes, percent
encoding, reparse/nonregular results, and ordinal- or Windows-case-equivalent
duplicates fail. `files` is sorted by UTF-8 bytes of that relative path.

For a declared RECORD hash, `record_digest` is the verified canonical
`<lowercase-algorithm>=<base64url-without-padding>` token and `record_length` is
its nonnegative decimal integer. `blank_reason` is null. When both RECORD fields
are blank, `record_digest` and `record_length` are null and `blank_reason` is
exactly `own_record` or `pycache_pyc`; no other blank is valid. Every entry,
including those two classes, has the independently measured nonnegative
`actual_byte_length` and lowercase SHA-256. The complete object, not a list of
per-distribution opaque hashes, is the D33 preimage.

For `pip check`, decode stdout/stderr strict UTF-8 without BOM, convert CRLF and
bare CR to LF, remove exactly one terminal LF if present, and reject any
remaining terminal LF or other leading/trailing whitespace. Exit code must be
zero, normalized stderr empty, and normalized stdout exactly
`No broken requirements found.`. `pip_check_output_sha256` is the D33-canonical
digest of exactly:

```json
{"exit_code":0,"schema_id":"layer3.b1b.pip_check_output.v1","stderr":"","stdout":"No broken requirements found."}
```

The worker is the sole producer after verifying the locked interpreter and
before any launch. Preflight always carries the direct verified digests. For a
launched authorized profile only, attestation `runtime.environment_inventory_sha256`
equals `preflight.environment.environment_inventory_sha256`, attestation
`runtime.distribution_record_inventory_sha256` equals
`preflight.environment.distribution_record_inventory_sha256`, and both
attestation and preflight `pip_check_output_sha256` are identical. Extra/missing entries,
normalization drift, RECORD mismatch, pip output drift, or any alias inequality
fails before child launch; no digest falls back to raw command output.

`plugin_policy` is exactly
`{pytest_disable_plugin_autoload:true,explicit_plugin:{module:"b1b_pytest",
path:"backend/b1b_pytest.py",git_blob:G,full_sha256:H}}`. Every child gets
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and loads that one verified candidate-head
module only through the exact `-p b1b_pytest` manifest argv. A sentinel installed
entry-point plugin must not load. Neither pytest-cov nor pytest-xdist may be
activated even if present in the proof lock; a second non-built-in explicit or
implicit plugin, plugin-path substitution, or hash mismatch is rejected.
`pytest_workers=1` and
`no_extra_args=true`.

The plugin's direct imports are limited to the standard library, the proof-lock
pytest distribution, and, only for the PostgreSQL profile after
`pytest_sessionstart`, proof-lock `psycopg==3.3.4` with
`psycopg-binary==3.3.4`; their transitive imports must remain inside the verified
proof-lock closure. It may not import the project application, SQLAlchemy,
Alembic, another plugin, or any undeclared distribution; use subprocess, shell,
network discovery, or stdout/stderr authority; or create/mutate a file, root,
database, row, or application artifact. Module import performs no environment or
handle read, connection, thread start, registration side effect, or mutation;
the bound pytest hooks initialize control only after plugin registration. The
plugin file is bound only by `plugin_policy`; `required_test_blobs` remains an
exhaustive tests-only list and must not gain the plugin path.

The audited Windows `psycopg-binary==3.3.4` wheel is frozen at `3560782` bytes
and SHA-256 `494ca54901be8cf9eb7e02c25b731f2317c378efa44f43e8f9bd0e1184ae7be4`.
Its verified full-path DLLs are frozen as `libpq` SHA-256
`eab732054d7b11ab8aaf2b3cdd03d923a14bf8b87f729e1f2f7add790185174e`,
`libcrypto` SHA-256
`6709bb77b9a31d2b3a21b362bd21c6da745511d68ad16e175c69899fa7815b36`,
and `libssl` SHA-256
`183dba53cf832056f5d59ec0bad2327107839d9591a37e7c11fc5642b98e722e`.
The worker loads only those verified full paths through `LoadLibraryExW` flags
`0x900`; `PQlibVersion()` must equal `180003`. The exact required libpq export
set is `PQlibVersion`, `PQconnectStartParams`, `PQconnectPoll`, `PQstatus`,
`PQsocket`, `PQerrorMessage`, `PQfinish`, `PQsetnonblocking`,
`PQsendQueryParams`, `PQconsumeInput`, `PQisBusy`, `PQgetResult`,
`PQresultStatus`, `PQntuples`, `PQnfields`, `PQgetisnull`, `PQgetvalue`,
`PQgetlength`, `PQclear`, `PQparameterStatus`, `PQhost`, `PQhostaddr`, `PQport`,
`PQdb`, `PQuser`, and `PQtransactionStatus`; missing or extra trust substitution
fails before connection. Interop remains in-memory `Reflection.Emit`; no Python
helper, `Add-Type`, CodeDOM, `csc`, temporary assembly, or helper file/process is
permitted.

`required_test_blobs` is the following ordered path list, each paired with its
40-hex Git blob read from the exact candidate head:

1. `backend/tests/test_layer3_b1b_runner.py`
2. `backend/tests/test_layer3_connector_promotion_bridge.py`
3. `backend/tests/test_layer3_connector_vertical_loop.py`
4. `backend/tests/test_layer3_migrations.py`
5. `backend/tests/test_pre_body_operator_authorization.py`
6. `backend/tests/test_layer3_post_route_operator_authorization_coverage.py`
7. `backend/tests/test_support_matrix.py`
8. `backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py`
9. `backend/tests/test_sec_xbrl_offline_honesty_ceiling_exhaustive.py`
10. `backend/tests/test_layer3_deploy_compose_contract.py`
11. `backend/tests/test_layer3_safety_contract.py`
12. `tests/test_api.py`
13. `backend/tests/test_layer3_workbench.py`
14. `backend/tests/test_layer3_workbench_package_state.py`
15. `backend/tests/test_layer3_package_entry.py`
16. `backend/tests/test_layer3_pass_entry.py`
17. `backend/tests/test_layer3_connector_source_intake_pilot.py`
18. `backend/tests/test_layer3_api.py`
19. `backend/tests/test_layer3_bounded_e2e.py`
20. `backend/tests/test_layer3_artifact_ingestion_facade.py`

This list is source-to-test mapped, not a generic smoke set:
`layer3_workbench.py` maps to files 13-14 and 18-19;
`layer3_package_entry.py` to 14-15 and 19; `layer3_pass_entry.py` to 16 and 18;
connector intake to 3 and 17; `ingest.py`/`dataframe_io.py` to 3, 16, 18-20;
route/auth registration to 5-6, 12, and 18; migration/model behavior to 2-4;
and default/support/environment posture to 7-11. The new bridge test is not a
substitute for these ordinary flag-off regression authorities.

`profiles` has exactly `sqlite_default`, `sqlite_authorized`, and
`postgresql_authorized`. Each is a closed object with exactly
`database_profile`, `bridge_enabled`, `production_verifier_required`, and
`invocations`; every invocation has exactly `name`, `argv`, `expected_skips`,
and `expected_deselections`. All use symbolic
cwd `repo_root`, set `PYTHONPATH` to the candidate-head `backend`, disable the
pytest cache provider, and accept no additional pytest/config/plugin argv. Each
invocation receives its own absent lane parent with exactly four direct runtime,
storage, database, and evidence children plus its fresh bound database identity;
no invocation consumes another's seeded or retained state.

The scrubbed child `PATH` contains only the audited venv's `Scripts` directory;
it cannot discover ambient Tesseract or another host executable. That makes the
one NRC OCR skip below deterministic. A collected node may skip or be deselected
only when its exact node ID appears in that invocation's frozen array, and the
actual array/count must equal it; unexpected or missing expected entries fail.

`sqlite_default` has `database_profile="sqlite"`, `bridge_enabled=false`,
`production_verifier_required=false`, and these five invocations in order:

```json
[
  {"name":"runner-contract-unit","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_layer3_b1b_runner.py"],"expected_skips":[],"expected_deselections":[]},
  {"name":"bridge-flag-off-parity","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_layer3_connector_promotion_bridge.py","backend/tests/test_layer3_connector_vertical_loop.py","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_equivalent_approval_uniqueness","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_approved_first","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_nonapproved_first","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_lock_timeout","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_reuse","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_basis_conflict","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_corrupt_basis_conflict","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_initial_transaction_rollback","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_materializer_rollback"],"expected_skips":[],"expected_deselections":["backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_equivalent_approval_uniqueness","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_approved_first","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_nonapproved_first","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_lock_timeout","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_reuse","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_basis_conflict","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_corrupt_basis_conflict","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_initial_transaction_rollback","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_materializer_rollback"]},
  {"name":"default-posture-and-authorization","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_pre_body_operator_authorization.py","backend/tests/test_layer3_post_route_operator_authorization_coverage.py","backend/tests/test_support_matrix.py","backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py","backend/tests/test_sec_xbrl_offline_honesty_ceiling_exhaustive.py","backend/tests/test_layer3_deploy_compose_contract.py","backend/tests/test_layer3_safety_contract.py","tests/test_api.py"],"expected_skips":["tests/test_api.py::test_nrc_scanned_content_search_and_evidence_bundle_with_ocr"],"expected_deselections":[]},
  {"name":"shared-workbench-regression","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_layer3_workbench.py","backend/tests/test_layer3_workbench_package_state.py"],"expected_skips":[],"expected_deselections":[]},
  {"name":"shared-package-pass-ingest-regression","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_layer3_package_entry.py","backend/tests/test_layer3_pass_entry.py","backend/tests/test_layer3_connector_source_intake_pilot.py","backend/tests/test_layer3_api.py","backend/tests/test_layer3_bounded_e2e.py","backend/tests/test_layer3_artifact_ingestion_facade.py"],"expected_skips":[],"expected_deselections":[]}
]
```

`sqlite_authorized` has `database_profile="sqlite"`,
`bridge_enabled=true`, `production_verifier_required=true`, and exactly:

```json
[
  {"name":"sqlite-authoritative-b1b","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_layer3_migrations.py","backend/tests/test_layer3_connector_vertical_loop.py","backend/tests/test_layer3_connector_promotion_bridge.py","--deselect=backend/tests/test_layer3_migrations.py::test_b1b_postgresql_migration_cycle","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_equivalent_approval_uniqueness","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_approved_first","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_nonapproved_first","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_lock_timeout","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_reuse","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_basis_conflict","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_corrupt_basis_conflict","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_initial_transaction_rollback","--deselect=backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_materializer_rollback"],"expected_skips":["backend/tests/test_layer3_migrations.py::test_alembic_upgrade_head_postgres","backend/tests/test_layer3_migrations.py::test_alembic_upgrade_head_idempotent_postgres","backend/tests/test_layer3_migrations.py::test_connector_source_intake_record_0056_constraints_postgres","backend/tests/test_layer3_migrations.py::test_alembic_orm_metadata_match_postgres"],"expected_deselections":["backend/tests/test_layer3_migrations.py::test_b1b_postgresql_migration_cycle","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_equivalent_approval_uniqueness","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_approved_first","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_race_nonapproved_first","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_lock_timeout","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_reuse","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_resolver_basis_conflict","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_corrupt_basis_conflict","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_initial_transaction_rollback","backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_postgresql_materializer_rollback"]}
]
```

That invocation uses an absent file-backed SQLite `DATABASE_URL`, no migration-
test URL, and the real production attestation verifier. It contains the full
authoritative C0-C3 integrated proof; a unit-only adapter test elsewhere cannot
substitute for it.

`postgresql_authorized` has `database_profile="postgresql"`,
`bridge_enabled=true`, `production_verifier_required=true`, and exactly:

```json
[
  {"name":"postgresql-authoritative-migration-concurrency","argv":["python","-m","pytest","-q","--maxfail=1","-p","no:cacheprovider","-p","b1b_pytest","backend/tests/test_layer3_migrations.py","backend/tests/test_layer3_connector_promotion_bridge.py"],"expected_skips":[],"expected_deselections":[]}
]
```

Only `bridge-flag-off-parity` has the nine case-2-through-10 deselections, and
only `sqlite-authoritative-b1b` has all ten case deselections; each argv and
expected array uses exact Section 10 table order. PostgreSQL and every other
invocation have zero deselections. File and node order are normative. For
PostgreSQL, the bound plugin performs the
sole `monitor_ready` handshake in `pytest_sessionstart` before collection. No
selected test module has an import-time bootstrap. SQLite collects migrations,
then vertical-loop, then bridge; PostgreSQL collects migrations, then bridge.
Every selected node in each earlier module precedes every bridge-module node.
The PostgreSQL migration phase finishes with the isolated database re-upgraded at
the exact candidate head before any bridge node executes. The ten Section 10
designated nodes appear in their exact table order only in this PostgreSQL
invocation; case 1 is the migration-file
node, cases 2-10 are bridge-file nodes, and all ten precede the terminal node
below. Static candidate-head proof requires each exact definition to be collected
once with no `skip`, `skipif`, `xfail`, parametrized alternate ID, dynamic rename,
or conditional-registration mark/decorator; runtime `skipped|xfailed|xpassed` for
any designated node is no-root. The exact source-last node ID
`backend/tests/test_layer3_connector_promotion_bridge.py::test_b1b_authorized_c0_c3_terminal`
must be the final collected node in both authorized profiles. It is the final
selected database-mutating node and owns the authoritative bridge C0-C3 proof.
At entry on the main pytest thread and before its first mutation, it registers the
one node/blob-bound C3 provider and uses pytest's built-in request/session view to
require the profile's exact module order and
`request.session.items[-1].nodeid` equal to that literal.
Its last application mutation, teardown, and fixture finalizers finish; every
application/DB writer joins; and its PASS `node_outcome` emits. Only then does
`pytest_runtest_logfinish` obtain the one frozen C3 sample and drive the
provider's prepare/publish plus distinct `c3_prepare`/C3 ACK compound protocol in
Section 9. The plugin never produces or receives census bytes.

Static candidate-head and plugin-policy proof exhaustively covers every
registered hook provider, binds the sole permitted C3 provider to that final node
and candidate blob, and covers `pytest_sessionfinish`, `pytest_unconfigure`,
`atexit`, child thread/process creation, and application/DB background writers.
Every other provider/hook is absent or proven nonmutating after the final node;
the read-only cadence emitter is the only post-C3 child thread. A non-PASS final
node emits only its outcome, then irreversibly performs in-memory
`REGISTERED -> DISCARDED` before prepare and cannot emit C3_prepare/C3 or PASS.
It may continue only through the exact independent-failure terminal, final
cadence, EOF, physical exit, and closed FAIL root. A normal missing-success path
after registration performs the same discard; abrupt process death records no
discard transition and enters external no-root containment. Registered authority remains
live only through consume or discard. These checks add no collection invocation,
process, second plugin, or argument; each unchanged single invocation keeps
pytest capture enabled.

It requires `DATABASE_URL` and `LAYER3_MIGRATION_TEST_DATABASE_URL` to name the
same worker-verified isolated local PostgreSQL database/schema and uses the real
production verifier. Raw URLs/credentials are environment-only; the manifest
records only endpoint/database identity hashes. For every profile, the worker
directly derives and D33-canonicalizes this complete frozen object, verifies
every referenced blob, and sets `preflight.test_manifest_sha256` to the digest
of those no-newline canonical bytes. Only a launched authorized profile also
embeds and reopens the complete object and same hash as
`pass-to-launch.runtime.test_manifest` and `.test_manifest_sha256`.
`sqlite_default` and every preflight-only failure create, open, and hash no
PASS-TO-LAUNCH record. Omitted, reordered, or extra tests/invocations, plus any
unexpected or missing-expected skip/deselection, invalidate preflight and, when
applicable, the attestation and final verdict.

1. One builder owns the implementation worktree, branch, and all candidate/runtime
   writes. No second agent edits that worktree.
2. One gate auditor has no candidate write authority or shared profile runtime
   root, works read-only against the unchanged builder tranche, independently
   checks the six fixed audit domains, and writes only the explicit external
   `b1b-independent-audit.json` assessment path under its expected principal.
3. One independent reviewer must review the unchanged audited head before merge;
   it binds the exact audit hash and writes only external
   `b1b-independent-review.json`. The reviewer does not co-author audit or build
   and does not share the builder's database, artifact directory, worktree, or
   write authority. Auditor/reviewer principals and explicit paths are distinct.
   Operator merge
   authority is additional and does not substitute for Gate-3 review.
4. Git and GitHub operations are sequential. No parallel fetch, rebase, migration-head update, commit, push, check watch, or merge operation is permitted.
5. Model and Alembic migration-head edits are serialized first and rebased against the then-current head. Shared central files, including models, support configuration, workbench/API registration, `backend/main.py`, package entry points, ingestion, and dataframe I/O, have one writer at a time.
6. The exact eight support-matrix surfaces are one atomic documentation/configuration tranche. A partial mirror is never handed off as acceptable.
7. SQLite and PostgreSQL tests use unique database names/connections and isolated artifact directories. Concurrency threads exist only inside the test process; agents do not race the same database.
8. Migration upgrade/rollback and PostgreSQL concurrency tests run serially against their allocated database. No shared seeded runtime is admissible.
9. Package tests use lane-unique artifact roots. No browser, real network, real ScienceBase acquisition, or UI resource is allocated to B1b.
10. The builder stops after implementation and local verification; auditor and
    reviewer stop after their exact external assessment objects; neither file is
    copied, tracked, rooted, or manifested; the independent reviewer records Gate 3;
    merge authority remains with the operator under the repository's merge-gate
    policy.
11. After merge and independent merged-main proof, a separate records writer
    owns only paths 50-58 in a clean docs worktree. A separate records reviewer
    works read-only only after that closeout lands and directly produces the exact
    Section 9 `records_semantic_review` object from the landed nine-path diff. Only its
    valid PASS permits the final aggregator's one-fetch/two-tree parity check.
    Any root-inbox or outside-memory mirror sync is later, mirror-only, never an
    authority prerequisite, and requires then-current outside-workspace permission.

The administrative closeout records base/final commits, migration, changed files,
commands/statuses, redacted database/root identities, relative artifacts, row/
package censuses and hashes, packet/fixture seals, I12 posture, support parity,
findings, and Section 15 standing. For every attempted invocation it also binds
intent, worker manifest when present, closeout bytes/hashes and disposition, and
the consuming `profile_verdict.v2` when one exists. Pre-merge records only entry/
authorized state; final success is reserved for merged proof and records closeout.

<!-- B1B-AMENDMENT-V2-BEGIN -->

## 17. Owner-confirmed prospective amendment

Only these six decisions amend the preceding correction; every preexisting clause remains byte-current.

1. **Non-waiver and non-authorization.** Adoption below does not waive the historical one-builder violation, retroactively authorize any work, validate any prior informal audit or review, or itself authorize dispatch, implementation, runtime, repair, B1b-04, merge, or publication. Authority still requires the refreshed Section 13.2 key and every fresh entry gate.

2. **Preserved prior work product.** The exact direct-parent chain below is adopted without re-execution only as valid prior work product and repair input, not as certified conforming to decision 4:

   | Commit | Owner-adjudicated execution provenance |
   |---|---|
   | `26f933a4a8ec7e0c222bdfdd3a13bde75a50ab19` | inherited-checkpoint/foreground-Claude |
   | `5bac0b0c68c39a23c4a79f8cdd63f1f95fb17980` | foreground-Claude |
   | `13631e89594c6ed69629b759c818e73f80c1b5fd` | p6_main_thread |
   | `901bce8eeaac835a0a663d697f0e45947389ed64` | p6_main_thread |
   | `141be3517e6baca28120b9893ef7c10a7c03b7cc` | p6_main_thread |
   | `f91257900b9d1b0227bba9cfdd9ce87b4ad95035` | p6_main_thread |
   | `7f942518b9c3f57d159dfee8385aec070e47f2ac` | p6_main_thread |

3. **Prospective roles.** `p6_main_thread` (`019f5a7d-78d4-75d1-bddb-04d48d3dec84`) is the sole candidate writer; `p6_agent1` (`019f497a-bece-7162-9d0b-5d2a21e8b23d`) is the independent auditor; `p6_agent3` (`019f497b-591b-7341-87bd-65154f49fb21`) is the independent reviewer; and `p6_agent2` (`019f497b-15a8-7763-a3a4-20a29046dd26`) is the unassigned fourth allowlisted task. Unlisted workflow outputs are advisory-only.

4. **Option (a) replay closure.** `_verify_materialized_replay` accepts `summary_json` without `schema_id` only when its key set and values are exactly `{"descriptor_status_counts":{"resolved_loaded":1},"retrieval_outcome_counts":{"loaded":1},"loaded_snapshot_count":1,"source_planes":["dataset"],"warning_reasons":["synthetic_non_official_fixture"],"retrieved_descriptor_count":1,"unresolved_descriptor_count":0,"descriptor_coverage_status":"complete"}`. With `schema_id`, it accepts only `schema_id=layer3.b1b_session_state.v1` and exactly these twelve keys: `schema_id`, `review_record_ref`, `review_state`, `result_review_hash`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `package_review_state`, `package_review_hash`, `reconciliation_record_id`, `packages`, and `connector_dataset_handoff_basis_hash`. Values must be stage-valid under lines 817-834, including the transitions at lines 999-1017. Eight-plus-extra, twelve-plus-extra, partial, mixed, unknown, unrecognized-schema, or stage-invalid state fails closed.

5. **Refreshed ballot record.** The mechanically captured refreshed record is `state/agent-inbox/b1b-dispatch-v2.md`; it must be absent before create and written once. The historical `state/agent-inbox/b1b-dispatch-owner-decision-2026-07-13.md` remains byte-immutable and may not be reused, appended to, or overwritten.

6. **Pre-B1b-04 conformance repair.** Only after a valid refreshed key and fresh E0/Gate 7, the repair file fence is exactly `backend/app/services/layer3_connector_promotion.py` and `backend/tests/test_layer3_connector_promotion_bridge.py`. No other candidate file may change, and B1b-04 remains blocked until this repair passes its required verification, independent audit, and independent review.

<!-- B1B-AMENDMENT-V2-END -->

<!-- B1B-AMENDMENT-V3-BEGIN -->

## 18. Owner-directed remediation refinement

Section 17 items 1, 2, 3, and 5 are preserved unchanged. This section
supersedes Section 17 items 4 and 6 and the inherited Section 13.2 Part-A grant
scope, only as stated below; every other preexisting clause remains
byte-current. Section 18 is the sole contract authority for the repair it
authorizes.

1. **Closed receipt-bound replay contract.** This contract supersedes
   Section 17 item 4 and is self-contained. Let B be exactly
   `{"descriptor_status_counts":{"resolved_loaded":1},"retrieval_outcome_counts":{"loaded":1},"loaded_snapshot_count":1,"source_planes":["dataset"],"warning_reasons":["synthetic_non_official_fixture"],"retrieved_descriptor_count":1,"unresolved_descriptor_count":0,"descriptor_coverage_status":"complete"}`.
   For the receipt-bound B1b staged path **without a top-level `schema_id`**,
   `_verify_materialized_replay` accepts exactly these four top-level
   progressions and no other, with predecessor-complete ordering (a later key
   is valid only when every predecessor key is present):

   - B;
   - B plus `plan_approval`;
   - B plus `plan_approval` plus `execution_selection`, where
     `execution_selection` is the 13-key pre-start object only;
   - B plus `plan_approval` plus the 14-key terminal `execution_selection` plus
     the 14-key `analysis_execution_start`.

   The staged objects are closed as follows.

   `plan_approval` has exactly `analysis_plan_id`, `approved_set_count`,
   `excluded_set_count`, `planned_pass_count`, `source_preview_id`,
   `source_preview_hash`, `source_gate`, `approval_only`, and
   `execution_started`, with `approved_set_count=1`, `excluded_set_count=0`,
   `planned_pass_count=1`, `source_gate="06_GATEC_PASS_FREEZE"`,
   `approval_only=true`, `execution_started=false`, and `analysis_plan_id`,
   `source_preview_id`, and `source_preview_hash` equal to the linked
   approved-plan/preview values.

   Pre-start `execution_selection` has exactly `schema_id`, `state`,
   `client_request_id`, `analysis_plan_id`, `source_preview_id`,
   `source_preview_hash`, `pass_run_ids_json`, `pass_run_count`,
   `execution_started`, `analysis_run_ids_json`, `downstream_unavailable`,
   `operator_reason_recorded`, and `selected_at`, with
   `schema_id="layer3.execution_selection_state.v1"`,
   `state="execution_selected_not_started"`,
   `pass_run_ids_json=[<the one linked pass_run_id>]`, `pass_run_count=1`,
   `execution_started=false`, `analysis_run_ids_json=[]`,
   `downstream_unavailable=["results","package","handoff"]`, the linked
   `L3PassRun` status equal to `"selected_not_started"`, and
   `client_request_id`, the plan/preview identities, `selected_at`, and all
   duplicated values equal to the preserved pass-summary/row values.

   Terminal `execution_selection` has exactly those 13 keys plus
   `pass_run_statuses_json`, and continues to satisfy every pre-start
   constraint for its inherited 13 keys except the explicitly transitioned
   fields below. Its schema remains
   `"layer3.execution_selection_state.v1"`; its selection
   `client_request_id`, plan/preview identities, one-item
   `pass_run_ids_json`, `pass_run_count=1`, `selected_at`, and other preserved
   values remain bound to the original selection state.
   `analysis_execution_start` has exactly `schema_id`, `client_request_id`,
   `state`, `analysis_plan_id`, `pass_run_id`, `source_preview_id`,
   `source_preview_hash`, `analysis_run_id`, `pass_run_status`,
   `output_payload_ref`, `downstream_unavailable`,
   `operator_reason_recorded`, `started_at`, and `completed_at`, where
   `analysis_execution_start.client_request_id` is the linked execution-start
   request ID. Both nested objects independently require
   `downstream_unavailable=["results","package","handoff"]`.

   For the completed terminal pair:
   `execution_selection.state="execution_pass_completed"`,
   `execution_started=true`,
   `analysis_run_ids_json=[<the linked analysis_run_id>]`,
   `pass_run_statuses_json={<pass_run_id>:"completed_with_warnings"}`,
   `analysis_execution_start.schema_id="layer3.analysis_execution_start_state.v1"`,
   `analysis_execution_start.state="execution_pass_completed"`,
   `analysis_run_id` equal to the one linked `AnalysisRun` whose status is
   `"completed"`, `pass_run_status="completed_with_warnings"`,
   `output_payload_ref` nonempty and equal to `L3PassRun.output_payload_ref`,
   and `started_at` and `completed_at` equal to the corresponding `L3PassRun`
   timestamps.

   For the failed terminal pair:
   `execution_selection.state="execution_pass_failed"`,
   `execution_started=true`, `analysis_run_ids_json=[]`,
   `pass_run_statuses_json={<pass_run_id>:"failed"}`,
   `analysis_execution_start.schema_id="layer3.analysis_execution_start_state.v1"`,
   `analysis_execution_start.state="execution_pass_failed"`,
   `analysis_run_id=null` with no linked `AnalysisRun` existing,
   `pass_run_status="failed"`, `output_payload_ref=null`, and `started_at`
   and `completed_at` equal to the corresponding failed `L3PassRun`
   timestamps.

   For both terminal alternatives, the same plan, pass-run, preview, request,
   status, output, and timestamp relationships must hold across the two nested
   objects and their database rows. A valid failed replay preserves
   materialization replay only; it does not satisfy or complete B1b-03. Each
   `operator_reason_recorded` receives Boolean-domain validation only, because
   no independent persisted source rederives it; no stronger verification is
   claimed. Unknown nested fields and any mismatch are rejected without
   mutation. Nested `schema_id` fields never select the twelve-key branch.

   **With top-level `schema_id=layer3.b1b_session_state.v1`**, the only
   accepted state has exactly the twelve keys `schema_id`,
   `review_record_ref`, `review_state`, `result_review_hash`,
   `analysis_plan_id`, `pass_run_id`, `analysis_run_id`,
   `package_review_state`, `package_review_hash`, `reconciliation_record_id`,
   `packages`, and `connector_dataset_handoff_basis_hash`, stage-valid as
   follows. Result review writes the first seven keys and sets the last five
   exactly to null; its exhaustive decision-to-state map is
   `approved -> execution_result_review_approved`,
   `changes_requested -> execution_result_review_changes_requested`,
   `rejected -> execution_result_review_rejected`, and
   `blocked -> execution_result_review_blocked`. `review_record_ref` must
   equal `"b1b-result-review-" + result_review_hash`, and
   `result_review_hash` must equal the D33 hash of the exact persisted
   result-review record. `analysis_plan_id`, `pass_run_id`, and
   `analysis_run_id` must identify one coherent promoted-session chain.
   Package review may follow only an approved result review and preserves the
   first seven keys unchanged; its exhaustive map is
   `approved -> package_review_approved`,
   `changes_requested -> package_review_changes_requested`,
   `rejected -> package_review_rejected`, and
   `blocked -> package_review_blocked`. Approved changes exactly all five
   initially null keys: `package_review_state`, `package_review_hash`,
   `reconciliation_record_id`, `packages`, and
   `connector_dataset_handoff_basis_hash`. Each nonapproved decision changes
   exactly the first four and leaves
   `connector_dataset_handoff_basis_hash=null`. `package_review_hash` must
   equal the D33 hash of the exact persisted package-review record, and
   `reconciliation_record_id` and every package projection must equal the
   linked reconciliation/package rows. `packages` is exactly the ordered
   three-object projection over `canonical_internal`, `user_facing`, and
   `review_facing` in that order, each object exactly
   `{package_kind, output_package_id, payload_sha256}`. For approved package
   review, `connector_dataset_handoff_basis_hash` must equal the hash of the
   exact Section 4.3 basis stored in reconciliation; the full basis is never
   stored in the session. The repair must structurally test this twelve-key
   validator but claims no runtime producer proof before B1b-04 through
   B1b-06 exist. Any arbitrary, unknown, extra, partial, malformed, mixed,
   out-of-order, unrecognized-schema, or stage-invalid state fails closed
   without mutation.

   Flag-false and all non-B1b behavior remain unchanged. The repair file fence
   is exactly `backend/app/services/layer3_connector_promotion.py` and
   `backend/tests/test_layer3_connector_promotion_bridge.py`. Encoding this
   section's literals and model-row checks locally in
   `layer3_connector_promotion.py` is implementation of this contract, not
   duplicated authority. The repair must not import `layer3_pass_entry` or
   `layer3_workbench` (both already depend on promotion), must not modify
   either producer, and must not add a shared third file. The lane stops and
   reports a blocker only if model queries and local validators cannot
   implement this contract within the exact two-file fence.

2. **Fresh E0, Gate-7 confirmation, and transplantation.** The fresh
   entry-gate record is the create-once, pre-edit
   `state/agent-inbox/b1b-e0-v2.md`, and the refreshed ballot record is
   `state/agent-inbox/b1b-dispatch-v2.md`; both resolve beneath the verified
   operator-context root, not inside the fresh candidate worktree, and are
   never candidate commits. E0 is absent before creation, written only by
   `p6_main_thread` (`019f5a7d-78d4-75d1-bddb-04d48d3dec84`), and never
   changed thereafter. It records Gates 1-6 as PASS with evidence and Gate 7
   as `RECORDED-PENDING-INDEPENDENT-CONFIRMATION`; it never claims Gate 7
   PASS. It binds: the captured refreshed ballot, the correction and
   owner-bound-main identities, the exact seven source commit SHAs of
   Section 17 item 2 in order, the clean fresh worktree path, branch, and
   initial HEAD, the migration identity, the 58-path fence, the Section 17
   item 3 roles as refined by this section, the lane roots, the resource
   rails, and the stop conditions. It does not contain a transplant map. The
   candidate worktree must be clean at Gate-7 confirmation. After E0 creation,
   `p6_agent1` issues a separate read-only Gate-7 verdict bound to E0's exact
   full-file SHA-256 and reverified custody; no transplantation or repair may
   start before `GATE7-CONFIRMED`. Immediately before transplantation, the
   lane reverifies that owner-bound main has changed no source-chain path:
   the owner-bound-main tree must equal source base
   `f6b7003015e68c40dea9629a4f171987bb545070` on the exact 14 paths changed by
   the seven-commit chain. Transplantation is conflict-free ordered
   application of the seven source commits; verification requires identical
   per-commit changed-path sets, `git patch-id --stable` equality per commit,
   and, before the repair, that the aggregate diff from source base
   `f6b7003015e68c40dea9629a4f171987bb545070` to source head
   `7f942518b9c3f57d159dfee8385aec070e47f2ac` equals the aggregate diff from
   the fresh worktree's initial HEAD to the transplanted head on those paths.
   The old-to-new commit map is derived mechanically from the resulting Git
   history; no new map artifact is created. Any conflict, drift, or mismatch
   stops the lane. The source worktree is never modified or cleaned. The
   later final `p6_agent1` audit is distinct from the Gate-7 confirmation and
   precedes the `p6_agent3` review. The historical Rev-9 E0 record remains
   byte-immutable.

3. **Ballot authority.** The refreshed record path remains
   `state/agent-inbox/b1b-dispatch-v2.md`; no further record path is created.
   The captured ballot must reproduce the following Part-A block exactly; Part
   B and every subsequent field are copied verbatim from Section 13.2,
   preserving the five conditional I12 placeholders,
   `owner_decision_key=<nonempty-owner-key>`,
   `owner_utc_timestamp=<RFC3339Z>`, `budget_resource_cap=NONE`, the zero
   canonical-hash field, the existing key grammar, and the Stage-1/Stage-2 key
   distinction, with no uniqueness requirement added or removed:

   Part A - select exactly one
   [ ] GRANTED - authorize only fresh E0, p6_agent1 Gate-7 confirmation, ordered seven-patch transplantation, the two-file repair, verification, final p6_agent1 audit, and p6_agent3 review; then stop before B1b-04
   [ ] WITHHELD - do not authorize B1b dispatch

4. **Later GO.** A later direct owner message authorizes only the milestone or
   milestones it explicitly names; `GO B1B-04` does not imply B1b-05 or
   B1b-06. Any such GO must bind the exact repaired candidate head SHA, the E0
   full-file SHA-256, the final audit full-file SHA-256, the final review
   full-file SHA-256, and an owner-supplied RFC3339Z timestamp. No GO is
   inferred from ballot capture, test results, audit, review, or silence, and
   this amendment creates no additional GO-record path.

5. **Authority and custody.** Only `p6_main_thread`
   (`019f5a7d-78d4-75d1-bddb-04d48d3dec84`), `p6_agent1`
   (`019f497a-bece-7162-9d0b-5d2a21e8b23d`), and `p6_agent3`
   (`019f497b-591b-7341-87bd-65154f49fb21`) perform their assigned acts —
   writer, Gate-7 confirmer and final auditor, and final reviewer
   respectively; `p6_agent2` (`019f497b-15a8-7763-a3a4-20a29046dd26`) remains
   allowlisted but unassigned and inactive under this grant. Additional
   delegated or orchestration workflows, descendants, and agents are
   prohibited; repository CI/check workflows required by this correction are
   preserved. The seven adopted commits are used as Git objects only;
   `worktrees/b1b-build` is neither modified nor cleaned, and its untracked
   harness state is not evidence.

6. **Amendment authoring and ballot preflight.** This section is authored
   against exactly this predecessor now on live main: main
   `fe73b5d14fbd76a3430f1dc830d3f3d90b4eaacf`, correction blob
   `69bf154518bbdfbe1962cc343ba74805c140d4c7`, 508,912 bytes, full SHA-256
   `A01C56B256D32CCE51A0EC6293F44CCA6C49BE482AD81E32F4F46A3D12EC972B`. That
   exact blob must be the byte-for-byte prefix of the amended file; if any of
   these identities differs at authoring time, the lane stops and re-presents
   rather than silently rebinding. Authoring must additionally prove strict
   UTF-8, LF-only encoding with no BOM, no CR, exactly one final LF, and
   one-file scope. After landing, every ballot field is rebound to the newly
   landed identity and the complete Section 13.2 binary preflight is
   performed, including exact byte equality between the owner-bound Git blob
   and the checkout bytes; blob-only verification is insufficient.

<!-- B1B-AMENDMENT-V3-END -->

<!-- B1B-AMENDMENT-V7-BEGIN -->

## 19. B1b-05 provenance breach record and candidate adoption

This section is append-only and changes authority only. Sections 1-18 remain
byte-current and in force except where a clause below expressly and narrowly
supersedes a named requirement for the single adopted commit identified in
decision 2. No architecture, scalability, or runtime claim is made.

1. **Breach and evidence record (self-contained; breach non-waived).** During
   the owner-authorized B1b-05 build turn, the writer violated Section 18
   decision 5, as established from the raw session records: a first
   descendant spawn attempt failed (p6_main rollout lines 65954-65955); a
   second succeeded and started `/root/b1b05_contract_audit` (lines
   65958-65959), which was interrupted while running (lines 65967-65969) and
   whose output was never consumed (line 66727); separately `p6_agent2`
   (`019f497b-15a8-7763-a3a4-20a29046dd26`), required to remain unassigned
   and inactive, was assigned substantive B1b-05 audits (line 67319 and
   later assignments) whose rulings were read and consumed (lines
   67624-68824) before the candidate commit (lines 68831-68832); two
   consumed findings - exact-basis census reconstruction and full locked
   ambiguous-commit reconstruction - were materially applied to candidate
   content before commit (line 67764) and were not independently
   pre-discovered by conforming actors. The breach is not waived and is not
   retroactively authorized; no descendant or `p6_agent2` output is or
   becomes conforming evidence. The provenance adjudication produced two
   verdicts: `p6_agent1` returned `NO-AMENDMENT-PATH-SUPPORTED` (deliverable
   6,198 bytes, SHA-256
   `854F1A5E3A2CA3AF5A6BDD772DDEF8C232DFEB32260D7E386985E20FA4B389D8`);
   `p6_agent3` returned `AMENDMENT-REQUIRED` (deliverable 14,941 bytes,
   SHA-256
   `91569CD4E32FF9EE28FA3EAAA6B6BD31D489E092066BF0AC5F23EA6A072ACF29`); the
   fail-closed rule made `AMENDMENT-REQUIRED` controlling. The earlier
   technical audit (2,223 bytes, SHA-256
   `AFA61148D31C31349AA2184908B39CF7A44F227C6BF9B5EC2261DA52648FB407`, no
   final LF) and technical review (1,486 bytes, SHA-256
   `14A3D6B917532458354EED36A4622837634A6FF9E2B033E626C86FBCAE30AE09`, two
   final LFs) are supporting current-byte evidence only; their bytes are
   bound exactly as they exist and are not altered or canonicalized. These
   temporary historical files are supporting evidence, never availability or
   durability prerequisites.

2. **Adoption.** Exact commit `b27e8738fa7d6a68276a0b7177f1a74c97909d6c`,
   parent `b39efafa9ee6340072836037b6d651de06cd1920`, is adopted as
   preserved prior work product despite the non-waived breach. Adoption
   becomes effective only when all of the following hold: the owner has
   issued the `AUTHORIZE-S19-V7` authorization; both affirmative create-once
   records of decision 5 exist; every required PR check has passed; and
   exactly the authorized bytes have landed on `project6-origin/main`.
   Reports and verdicts are evidence satisfying owner-defined conditions,
   never independent owner authority. No mutable branch, worktree, or
   publication state is bound by this decision. Adoption does not accept the
   B1b-05 milestone, does not authorize B1b-06, and creates no candidate
   implementation, candidate landing, or runtime authority. Required
   docs-only PR CI is amendment evidence only; it does not prove candidate
   tests, runtime readiness, compatibility, scalability, or B1b-06
   readiness.

3. **Authorization sequence.** The owner token `AUTHORIZE-S19-V7` authorizes
   exactly this sequence and nothing else: (a) `p6_main_thread` reverifies
   the bound main, correction prefix, candidate HEAD and parent, E0-v2
   identity, custody, and absence of both capture paths; (b) if unchanged,
   `p6_main_thread` alone authors and commits the exact one-file amendment
   in a fresh, collision-free docs-only worktree created from the bound
   main; (c) `p6_agent1` performs one read-only combined audit; (d) only an
   exact `B1B05-S19-AUDIT-CONFIRMED` verdict permits `p6_main_thread` to
   capture that output verbatim; (e) `p6_agent3` then performs one read-only
   combined review bound to the captured audit; (f) only an exact
   `B1B05-S19-REVIEW-CONFIRMED` verdict permits capture of the review,
   publication of the docs-only PR, required CI, and landing of the exact
   amendment blob; (g) after mechanical post-landing verification, the lane
   stops before B1b-05 acceptance. Any drift, nonaffirmative verdict,
   malformed deliverable, substantive condition, failed required check, or
   unexpected changed path stops the lane without repair, retry, landing, or
   widened authority.

4. **Fresh evidence scope.** The `p6_agent1` combined audit must
   independently rederive, from the specification and the current candidate
   bytes and without reliance on any `p6_agent2` or descendant output: the
   exact-basis census reconstruction; and the full fresh-lock
   ambiguous-commit reconstruction, including the fail-before-commit and
   commit-then-raise distinction. It must also mechanically confirm the
   exact six-file B1b-05 delta, the full candidate and parent identities,
   aggregate candidate custody, and unchanged implementation bytes. The
   `p6_agent3` combined review must independently spot-check both
   derivations and review the amendment text and the captured audit. Each
   deliverable must bind the proposed amended correction blob and its full
   SHA-256, the full candidate commit and parent, the E0-v2 SHA-256, and the
   four supporting evidence hashes in decision 1, and is valid only if that
   exact correction blob lands unchanged. No TDD, test creation or
   modification, local suite rerun, or second full technical audit is
   performed. Identity drift stops the lane; it does not authorize tests,
   repair, or rebasing.

5. **Create-once captures.** The capture paths are exactly
   `state/agent-inbox/b1b05-adopt-audit.md` and
   `state/agent-inbox/b1b05-adopt-review.md`, both currently absent, both
   beneath the verified operator-context root. Reviewers remain read-only;
   `p6_main_thread` validates source-byte hygiene (strict UTF-8, LF-only, no
   BOM, no CR, exactly one final LF) before verbatim capture; no
   normalization or overwrite is allowed; capture is atomic create-new. If
   the lane stops, captured audit and review files remain immutable and
   non-authorizing. Any branch, PR, or CI state is left without further
   agent mutation and remains non-authorizing; because external state may
   change independently, continuation requires later direct owner
   authority bound to the exact then-observed identities. No automatic
   retry, repair, cleanup, deletion, or overwrite follows. Each capture
   binds its path, byte length, and full-file SHA-256, and each report
   must be self-contained.

6. **Authority transition (narrow).** No new ballot record and no new
   entry-gate record are created. `state/agent-inbox/b1b-e0-v2.md`
   (full-file SHA-256
   `C09061EA429D55A11A102884D41A209630CA3B5E7AFA30C9778F37901D918430`)
   remains the historical entry-gate anchor, and the old main
   `c1fcd840b421ceafb560266858a75808207f4540` and correction full SHA-256
   `08F061F7B58C7DFF61EE7CA25BBBBC958CFD1E005D427FBBDE4BD449FBF0788A` are
   preserved as historical facts. For adopted commit
   `b27e8738fa7d6a68276a0b7177f1a74c97909d6c` only, the following are
   narrowly superseded: the Section 18 decision 6 post-landing
   ballot-field-rebinding requirement; the E0-v2 forward main/correction
   stop conditions solely as necessary for this exact one-file Section 19
   landing; and literal `worktrees/b1b-r2` cleanliness solely to tolerate
   the exact known untracked file
   `.omc/state/sessions/7df22f6a-9e78-4ba3-ace1-8d719c4d54a6/last-tool-error-state.json`,
   whose mutable contents are non-evidence and are never bound or made
   authoritative. Exact candidate HEAD and parent, tracked and index
   cleanliness, and the absence of any other untracked path remain required.
   Every other E0-v2 fact, role, rail, custody rule, stop condition, and
   non-authorization boundary remains in force, including
   `worktrees/b1b-build` preservation.

7. **PR, landing, and boundaries.** The amendment PR must contain exactly
   the correction file with the authorized suffix. Required CI must pass;
   no test additions, local suite reruns, automatic CI repairs, or repeated
   retry loops are authorized. Immediately before landing, the exact
   amendment blob, the correction-file predecessor and resulting blob, the
   one-file PR scope, the candidate and parent identities, the E0-v2
   identity, both capture paths with their byte lengths and full-file
   SHA-256 values, and custody are reverified; relevant drift or conflict
   stops the lane. Unrelated live-main movement alone does not invalidate
   or silently rebind the amendment when all those identities remain
   exact; the then-current main SHA is preserved only as contextual input
   to the later GO. After landing, the live-main blob, checkout
   bytes, byte length, full SHA-256, and one-file scope are verified
   mechanically; no second agent round and no cleanup, deletion, branch
   removal, or worktree removal occurs. The candidate remains unchanged and
   local-only: no candidate push, merge, cleanup, deletion, test work,
   generalized refactor, architecture claim, or B1b-06 work is authorized.
   Only `p6_main_thread`, `p6_agent1`, and `p6_agent3` act; direct
   communication and IPC transport to the exact existing `p6_agent1` and
   `p6_agent3` tasks and required repository CI/check workflows are
   permitted and create no additional actor or authority; new agents,
   descendants, subdelegation, and additional orchestration workflows are
   prohibited; `p6_agent2` remains inactive; `p6_main_thread` alone
   performs capture, PR publication, and landing acts. A
   later B1b-05 acceptance GO must bind: the full candidate SHA and parent
   above; the E0-v2 SHA-256 above; both capture paths with their byte
   lengths and full-file SHA-256 values; the amended correction byte length
   and full SHA-256; the then-current `project6-origin/main` SHA, which is
   contextual only and claims no compatibility, mergeability, landing
   readiness, runtime readiness, scalability, or B1b-06 authority; and an
   owner-supplied RFC3339Z timestamp. Such a GO grants only the milestone it
   explicitly names; B1b-06 requires a separate owner GO and a fresh
   main/custody/compatibility entry gate.

8. **Authoring bindings.** This section is authored against exactly this
   predecessor now on live main: main
   `c1fcd840b421ceafb560266858a75808207f4540`, correction blob
   `1694e90918f7111311e795eea30c55dd575033e0`, 523,623 bytes, full SHA-256
   `08F061F7B58C7DFF61EE7CA25BBBBC958CFD1E005D427FBBDE4BD449FBF0788A`. That
   exact blob must be the byte-for-byte prefix of the amended file; any
   identity drift at authoring time stops the lane and re-presents. The
   appended suffix is ASCII-safe; authoring must prove strict UTF-8, LF-only
   encoding, no BOM, no CR, exactly one final LF, and one-file scope. After
   landing, exact byte equality between the owner-bound Git blob and the
   checkout bytes is required; blob-only verification is insufficient.

<!-- B1B-AMENDMENT-V7-END -->
