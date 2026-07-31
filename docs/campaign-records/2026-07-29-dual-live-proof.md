> **Planning record, not runtime authority.** This dated campaign record is
> exhaustive for the proposed ScienceBase + NRC ADAMS Public Search (APS)
> fresh-live proof campaign. It is subordinate to live source and tests,
> `project6-origin/main`, `docs/MASTER_CONTEXT.md`, and `docs/program-context/`.
> It does not replace the master context, grant network egress, arm a connector,
> accept a result, authorize implementation, or claim production readiness.
> It is the candidate input to M0 review, not a completed planning freeze.

# Dual Live Acquisition-to-Handoff Proof Campaign

Baseline: `project6-origin/main` at
`c1fcd840b421ceafb560266858a75808207f4540` (2026-07-20).

Companion execution plan:
[`docs/superpowers/plans/2026-07-29-dual-live-proof.md`](../superpowers/plans/2026-07-29-dual-live-proof.md).

## 1. Purpose and decision

The next product-level proof should show that Project6 can acquire one newly
retrieved source artifact from each of two materially different public-data
connectors, preserve its identity and bytes through the system, and carry it
through the appropriate Layer 3 review, package, and internal handoff boundary.

The two proof sources are:

1. one exact public CSV from ScienceBase, using the repository-backed USGS
   Mineral Commodity Summaries item `63d1a3c6d34e06fef15006be`; and
2. one exact NRC APS PDF for accession `ML17123A319`.

This is the best-fitting next proof because it joins capabilities that currently
exist as credible but partly separate halves:

- connector execution, target records, provenance, raw storage, and dataset
  versions;
- ScienceBase CSV source-intake and Gate B fixture proof;
- NRC APS document processing and a mature qualitative Layer 3 workflow;
- Layer 3 execution, result review, exactly-three-package construction,
  package review submission, and handoff preparation.

The campaign targets the missing connective tissue: bounded first-use egress,
fresh-byte proof, physical-request accounting, and end-to-end content-hash
continuity. Building another fixture-only connector would add breadth without
answering whether the existing system can safely cross this boundary.

## 2. Vocabulary and claim classes

Every statement in this record uses one of these classes:

| class | meaning |
|---|---|
| `LANDED` | present on the pinned baseline and supported by source/tests |
| `OFFLINE-PROVEN` | exercised with fixtures or isolated local state, not fresh network bytes |
| `HISTORICAL-EVIDENCE` | observed in a prior run/export but not current implementation authority |
| `PROPOSED` | recommended design or target state; not implemented |
| `OWNER-GATED` | cannot proceed without a named, bounded owner decision |
| `EMPIRICALLY-OPEN` | must be learned from an authorized live response |
| `NOT-CLAIMED` | expressly outside the evidence or campaign |

“Fresh” means a new HTTP `200` retrieval in the authorized proof window with no
fixture, replay corpus, local cache, conditional request, or `304`. It does not
mean the publisher changed the content since a prior retrieval.

“Handoff” means the existing internal or same-origin handoff/export-preparation
boundary. It does not mean that a third-party provider received anything.

## 3. What has already been accomplished

### 3.1 Connector platform foundation — `LANDED`

The connector platform already supplies durable run, submission, target, event,
checkpoint, lease, policy-snapshot, provenance, raw-storage, and dataset-version
concepts. Current generic connector routes create and immediately enqueue runs.
The reusable base is visible in:

- [`backend/app/models/models.py`](../../backend/app/models/models.py):
  `ConnectorRun`, `ConnectorRunSubmission`, `ConnectorRunTarget`,
  `ConnectorRunEvent`, and `ConnectorPolicySnapshot`;
- [`backend/app/api/router.py`](../../backend/app/api/router.py):
  `_connector_executor`, `_enqueue_connector_run`, and current submit/read
  routes;
- [`backend/app/services/connectors_sciencebase.py`](../../backend/app/services/connectors_sciencebase.py);
- [`backend/app/services/connectors_nrc_adams.py`](../../backend/app/services/connectors_nrc_adams.py).

Practical value: a proof does not need a new orchestration system. It can reuse
run identity, idempotency, observability, raw bytes, and durable result records.

### 3.2 ScienceBase public acquisition — `LANDED` and `OFFLINE-PROVEN`

The public ScienceBase connector supports explicit item IDs, file discovery,
downloaded-target records, provenance, dataset versions, recovery, and a
validate-only pilot surface. Its selected support posture is anonymous,
ScienceBase-only, local operator use.

The canonical MCS pilot item is pinned in
[`tools/run_sciencebase_live_pilot_validation.py`](../../tools/run_sciencebase_live_pilot_validation.py)
as `63d1a3c6d34e06fef15006be`.

Historical operator evidence associates that item with the Germanium files
`mcs2023-germa_salient.csv` and `mcs2023-germa_world.csv`. Only the item ID is
tracked as current authority. Therefore the first filename is a proposed target
that the fresh hydration response must confirm; absence or mismatch is a STOP,
not permission to select another file.

Practical value: operators already have a working public connector and dataset
ingestion path. The remaining work is to constrain it to one exact fresh file
and bind its bytes to downstream Layer 3 receipts.

### 3.3 ScienceBase connector-source admission — `LANDED` and `OFFLINE-PROVEN`

[`backend/app/services/layer3_connector_source_intake.py`](../../backend/app/services/layer3_connector_source_intake.py)
rehashes the stored CSV, compares it with the connector target hash, records
source identity and provenance, creates a material preview, and supplies the
Gate B decision basis.

[`backend/tests/test_layer3_connector_source_intake_pilot.py`](../../backend/tests/test_layer3_connector_source_intake_pilot.py)
proves the fixture-based ScienceBase CSV intake and rejection cases.

Practical value: raw connector output can already become a governed Layer 3
candidate rather than an untracked file. What remains is live-origin continuity,
Gate C execution, review, packaging, and handoff proof.

### 3.4 NRC APS acquisition and document-processing foundation — `LANDED`

The NRC APS connector has search/detail execution, artifact download,
safeguards, replay validation, content extraction/indexing, evidence products,
and operator review surfaces. A representative real-document fixture exists at
[`tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`](../../tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf).
Focused baseline evidence includes
[`tests/test_nrc_aps_safeguards.py`](../../tests/test_nrc_aps_safeguards.py),
[`tests/test_nrc_aps_artifact_ingestion.py`](../../tests/test_nrc_aps_artifact_ingestion.py),
and the connector-specific tests under `backend/tests/`. These are
fixture/replay or mocked-transport evidence, not a current live response.

The current implementation is feature-rich but not safe enough for this
first-use proof without a narrower execution mode. It may retry, follows
redirects too broadly, can apply artifact credentials automatically, unions
broad default hosts, and records URL-shaped material more liberally than the
proposed campaign permits.

Practical value: the difficult document and qualitative-analysis machinery does
not need to be rebuilt. The work is to introduce a one-shot transport boundary
and bind newly live bytes to the existing downstream chain.

### 3.5 Layer 3 qualitative workflow — `LANDED` and `OFFLINE-PROVEN`

The current NRC qualitative path can traverse material selection, snapshot,
typing/unit selection, plan creation, execution, result review, three package
kinds, package review submission, and handoff/export preparation. The three
package kinds are exactly:

- `canonical_internal`;
- `user_facing`;
- `review_facing`.

The front door is
[`next_milestone_plans/README_LAYER3_PHASE1A_PACK.md`](../../next_milestone_plans/README_LAYER3_PHASE1A_PACK.md).
Relevant services include:

- [`backend/app/services/layer3_qual_aps_execution.py`](../../backend/app/services/layer3_qual_aps_execution.py);
- [`backend/app/services/layer3_execution_output.py`](../../backend/app/services/layer3_execution_output.py);
- [`backend/app/services/layer3_execution_review.py`](../../backend/app/services/layer3_execution_review.py);
- [`backend/app/services/layer3_package_entry.py`](../../backend/app/services/layer3_package_entry.py);
- [`backend/app/services/layer3_aps_handoff.py`](../../backend/app/services/layer3_aps_handoff.py).

Focused baseline tests include
[`backend/tests/test_layer3_qual_aps_execution.py`](../../backend/tests/test_layer3_qual_aps_execution.py),
[`backend/tests/test_layer3_execution_output.py`](../../backend/tests/test_layer3_execution_output.py),
[`backend/tests/test_layer3_execution_review.py`](../../backend/tests/test_layer3_execution_review.py),
[`backend/tests/test_layer3_package_entry.py`](../../backend/tests/test_layer3_package_entry.py),
and
[`backend/tests/test_layer3_handoff_export_response.py`](../../backend/tests/test_layer3_handoff_export_response.py).
This is code/test evidence for the existing workflow, not evidence that fresh
connector-origin continuity has passed.

Practical value: a newly acquired APS document can use an existing deep
workflow. The missing claim is that one fresh connector artifact—not a fixture
or separately created document—retains the same identity through every stage.

### 3.6 Governance foundation — `LANDED`

The repository already separates generic directives from named first-use host
authority:

- D27 requires a named owner grant for a new host class and request budget.
- D28 requires that grant to become a concrete arming record before egress,
  with a finite request ledger that stops at its ceiling.

The current supported profile remains local expert use with anonymous public
connectors and offline SEC XBRL. NRC APS is keyed and therefore this campaign,
if authorized, remains an experimental local-operator proof. It is not a
supported-profile promotion.

Practical value: the project has a policy vocabulary for bounded experiments.
The new work makes that policy mechanically enforceable at the request-send
boundary.

## 4. Current gaps

| gap | consequence if ignored | required closure |
|---|---|---|
| generic submit auto-enqueues | an arming record cannot be reviewed before egress | separate arm and execute routes |
| no exact ScienceBase filename selector | a run can acquire more than the named artifact | exact-name predicate, fail closed |
| ScienceBase permits conditionals/automatic redirects | “fresh” and request count become ambiguous | no-conditionals mode and manual redirect |
| ScienceBase buffers before enforcing the cap | an oversized object can consume memory before rejection | streaming byte cap |
| NRC request schema accepts extra fields | unreviewed controls can enter the proof envelope | strict campaign schema |
| NRC automatic retry/auth/redirect behavior | physical sends and secret audience can exceed the grant | one-send transport, keyed exact API call, unkeyed artifact policy |
| request attempts are not committed before send | crash ambiguity can cause replay | durable reservation-before-send events |
| rate bucket is not destination-specific | artifact host accounting can be wrong | bucket by actual destination host |
| URL-shaped sensitive material can persist | query/header/body secrets may enter evidence | safe host/path/query class plus URL hash only |
| connector hashes are not uniformly rechecked downstream | a different artifact can be reviewed or packaged | continuity receipt at every boundary |
| analysis artifact bytes lack one uniform receipt | manifest/package identity can be incomplete | artifact hash and ordered set hash |
| no fresh dual-source proof exists | fixtures can be mistaken for operational evidence | two separately armed live acquisitions |

## 5. Campaign architecture

### 5.1 Group governance; keep authority separate

One campaign definition may group the shared milestone, evidence schema,
acceptance matrix, reviewers, code revision, and expiry. It must not merge the
two connector grants.

The recommended structure is:

1. one strict owner-approved campaign-definition document, loaded from a
   protected server-configured path and verified against a configured raw
   SHA-256, whose canonical bytes rederive the immutable campaign fingerprint;
2. two connector-specific owner grant documents, loaded from separate protected
   server-configured paths and verified against separately configured SHA-256
   digests, each matching that definition and binding one UUID4 nonce plus
   `max_armings=1`;
3. one protected server-configured campaign-evidence index head whose immutable
   content-addressed revisions form one no-overwrite, gap-free predecessor
   chain; each revision maps the exact campaign-definition
   digest/fingerprint and each connector/grant digest to immutable
   content-addressed bytes plus expected deterministic consumption-marker
   hashes for later read-only verification, and fixes the one protected
   four-stream runtime-log directory/manifest/separate-seal contract;
4. one NRC APS arming that binds its verified grant digest, the campaign
   fingerprint, and only the exact NRC target/host/method/path/credential/budget
   authority described below;
5. one ScienceBase arming, creatable only after the arming service itself
   rederives and passes the full NRC acquisition-success predicate (single
   definition referenced in section 11), that binds its verified grant
   digest, the same campaign fingerprint, the predecessor NRC parent-run ID
   and the service-rederived `ledger_terminal_hash`,
   and only ScienceBase target/host/method/path/budget authority;
6. a committed hash/class-only derived arming before either connector sends a
   detail-derived artifact request;
7. independent technical outcomes;
8. one campaign closeout that passes only when both outcomes and both
   downstream continuity chains pass.

Each selected index slice is exact: one definition ref, two grant refs with
connector set `{sciencebase_mcs, nrc_adams_aps}`, and one log-capture ref.
Reject orphan, duplicate, extra, or cross-ID/fingerprint refs. A selected
two-campaign repeatability union is exactly two definitions, four grants, and
two captures while each slice remains exact. The global index may preserve
additional structurally complete, exact-reference, disjoint failed/historical
slices; their technical outcome may remain failed, and the index must never
drop or relabel them merely to satisfy the selected-union count.

Revision 1 has no predecessor and contains exactly one complete campaign slice.
Every successor increments the revision by one, names the exact predecessor
path/digest, preserves all predecessor refs byte-for-byte, and adds exactly one
complete disjoint campaign slice. Before use, the
service traverses and rehashes the whole `indexes/<sha256>.json` chain,
enumerates the protected index directory, and requires the configured object to
be the unique maximal head. Rollback, fork, gap, orphan object, partial
addition, or mutation/drop/relabel of any earlier slice fails. Arming resolves
the earliest revision containing the selected exact complete slice and requires
that introduction revision/digest to be the current unique-maximal head before
marker creation. A preserved ancestor slice is historical-only even if its
grant remains unused. The introduction revision/digest is bound into each
campaign arming, the log seal, and the seal event of every extant connector
run; later head rotation does not
erase that binding. This is the bounded local mechanism that makes “preserved”
enforceable rather than a procedural promise.

Head advancement is a one-way campaign-close boundary. It intentionally
abandons any unused grant in an ancestor slice; recovery needs a new campaign
definition/revision and new grants. That availability cost is appropriate for
the serial experiment because rebinding a stale slice would make its immutable
evidence identity ambiguous at the moment of egress.

The definition binds only shared governance: campaign ID, code revision, exact
two connector keys/targets, acceptance/evidence/review profiles, required review
roles, NRC-first execution order, exact three-package contract, common
half-open window, and non-authorities. Canonical definition bytes contain
neither their own fingerprint nor either grant digest, avoiding a digest cycle.
The definition can reject a mismatched grant but cannot add or widen a host,
method, path, credential audience, request, byte, or time permission; those
remain connector-grant authority.

Why this is optimal: common review work happens once, while compromise,
failure, expiry, or budget exhaustion in one connector cannot authorize or
contaminate the other.

No caller-supplied campaign/grant reference is authority. The arming service
must load and rederive the exact definition, then load the exact
connector-specific grant bytes, verify their configured digests, strictly parse
them, require definition/grant intersection, and construct egress authority
only from the verified grant. A request may select only a connector and name
expected digests; it cannot supply or widen targets, hosts, methods, paths,
credentials, budgets, expiry, revision, or non-authorities.

Execution and historical verification are deliberately different
capabilities. A physical send may use only the currently configured definition
intersected with the current connector grant while both are unexpired and while
the configured evidence-index revision remains both the unique maximal head and
the selected campaign's earliest complete-slice introduction bound by the
arming. Arming fails before marker/DB/event/network activity if that
introduction is already an ancestor; every reservation and immediate pre-send
check reloads all three.
Later validation resolves the original bytes only through the protected index
chain, verifies index/archive/canonical digests, and proves each recorded
reservation/send time fell inside both original half-open windows. Historical
definition/grant evidence is distinct read-only typing: it cannot arm, execute,
reserve, send, or revive unused budget. The validator accepts a campaign ID and
fingerprint, never an archive or index path.

Each grant also has one deterministic parent-run ID and one canonical
consumption-marker path keyed by its digest. Arming atomically creates that
no-overwrite marker before DB creation; its existence consumes the grant across
client idempotency keys, run statuses, and isolated DBs that share the
protected campaign-evidence root. A marker-only crash is intentionally
fail-closed. Recovery requires a fresh campaign definition/raw digest/canonical
fingerprint and a fresh owner grant/digest/nonce explicitly superseding the
consumed digest. Same-campaign recovery is forbidden because another isolated
database cannot prove the absence of old-run reservations from the marker
alone. Unused budget never transfers implicitly.

A parent grant may pre-authorize a hash/class-only derived artifact arming only
when the fresh metadata response supplies exactly one URL that satisfies every
closed grant rule. The exact URL remains process-memory-only until the
corresponding one-send call; the committed derived arming carries its SHA-256
and safe host/path/query class. A mismatch requires a new owner decision.

Rejected alternatives:

- one combined grant: faster to sign, but it obscures credential and host
  boundaries and increases blast radius;
- two unrelated campaigns: strongest isolation, but duplicates governance and
  makes the product-level dual-source claim harder to reconstruct;
- reusing current generic submit routes: minimal code, but arm and send remain
  one operation and therefore cannot meet D28.

### 5.2 No-migration serial MVP

For a trusted, serial, single-operator proof, the narrowest design can
reuse existing tables:

- a `ConnectorRun` with status `armed` is the arming record;
- immutable grant/request configuration and the arming fingerprint live in
  `request_config_json`;
- the deterministic policy lives in `ConnectorPolicySnapshot`;
- `ConnectorRunSubmission` supplies idempotent creation;
- `ConnectorRunEvent` records reservations, completions, blocks, and terminal
  outcomes with deterministic IDs;
- an atomic no-overwrite
  `consumed/<raw_grant_sha256>.json` marker under the protected evidence root
  supplies the cross-client/cross-DB one-parent-arming fence;
- an execute call atomically transitions `armed` to `pending` and enqueues only
  the frozen configuration, and only when its compare-and-swap claim returns
  `claimed_now=true`; executor lease acquisition is the only transition from
  `pending` to `running`, every physical reservation requires `running` plus
  the exact active lease, and a strict-only finalizer commits the one terminal
  transition to `completed`, `failed`, or `cancelled` while releasing the
  lease and emitting one deterministic terminal event; generic resume, cancel,
  and target-count finalize paths are rejected for strict runs.

The execute request must not accept replacement connector configuration.

Derived artifact armings do not mutate the parent `request_config_json` and do
not create another executable connector run. Each is a new logically immutable
`ConnectorPolicySnapshot` plus a deterministic
`derived_egress_arming_created` event under the claimed run. The policy
snapshot carries only the exact URL hash and safe host/path/query class. The
snapshot and event commit before the corresponding request reservation; the
exact URL is then used once from process memory and discarded. A crash after
the derived commit cannot resume because the URL was deliberately not made
durable.

This is deliberately not the production architecture. A normalized campaign,
grant, reservation, and budget schema becomes necessary before multi-process,
recurring, shared-budget, auto-resume, default-on, or production use.
Immutability in this MVP is service-enforced rather than protected by a
database trigger. That limitation is acceptable only inside the exclusive
serial proof—at most one campaign process alive at any instant—and is
independently checked by the evaluator.
The consumption marker deliberately cannot be rolled back if the following DB
transaction fails; availability is sacrificed so owner authority cannot be
silently restored.

### 5.3 Proposed control surfaces

- `POST /api/v1/connectors/egress-armings`
- `GET /api/v1/connectors/egress-armings/{connector_run_id}`
- `POST /api/v1/connectors/egress-armings/{connector_run_id}/execute`

Creation records intent only and performs no network operation. Execution is a
second call that independently reloads the same exact owner grant and caller
posture. Both operations fail closed when the campaign feature flag is off.

The proof runs in an isolated, exclusive serial runtime with a hard
acquisition/downstream process boundary. An acquisition-only child process
alone holds credentials and live egress and ends at raw admission; a
secret-free, network-denied process performs parsing and Layer 3C only after
the child's process tree is stopped and process/port quiescence is proven. At
most one campaign process is alive at any instant. While the
proof flag is enabled, generic ScienceBase/NRC submit and resume routes are
blocked so unrelated connector traffic cannot be mistaken for or escape the
campaign ledger. Existing generic behavior remains unchanged when the proof
flag is off.

The strict arming envelope includes:

- schema/version/state and requested transition;
- campaign ID and fingerprint;
- connector key and exact target;
- allowed host, method, path predicate, and credential audience;
- maximum physical sends, bytes, duration, rate, and expiry;
- server-verified owner grant ID/digest and non-authorities;
- campaign-introduction evidence-index revision/digest, which was the current
  unique-maximal head at arming;
- code revision, workspace/principal hashes, authorization mode, and role;
- `written_before_first_request = true`;
- an arming fingerprint over stable canonical JSON excluding the fingerprint
  field itself.

### 5.4 Exact URL custody

The generic connector code currently has legitimate recurrence-oriented URL
sinks: target/provenance `sciencebase_download_uri`, artifact-alias
`alias_url`, raw item/detail snapshots, source-reference JSON, and downstream
intake metadata. The strict proof cannot reuse those persistence paths
unchanged while claiming process-memory-only artifact URLs.

For both strict connectors:

- exact derived artifact URLs exist only in a non-serializable, `repr=False`
  frozen request object from admitted metadata parsing through the one send;
- target and provenance download-URI scalars and alias URL scalars are null;
- item/detail, source-reference, alias, permission, linkage, intake, API,
  event, report, error, and log projections use an explicit safe whitelist;
- no raw ScienceBase item/`files[]` object or NRC Get Document object is
  written to DB or snapshot storage;
- persisted locator evidence is only URL SHA-256 plus the admitted
  scheme/host/port/path/query class and response-body hash;
- the evaluator enumerates all campaign-related scalar/text/JSON columns and
  scans every non-source snapshot/report/generated file, rather than checking
  JSON fields alone.

The acquired CSV/PDF bytes are the immutable source and are not rewritten for
redaction. Their exact storage refs and hashes identify the only opaque-source
scan exceptions; all surrounding metadata and all generated outputs remain in
scope. This separation preserves source integrity without allowing application
metadata to become an accidental bearer-URL store.

The live runtime also has a closed declared application-process log-custody
surface. Its protected evidence index fixes
`logs/<campaign_fingerprint>/`, one manifest, a separate
`log-seals/<campaign_fingerprint>.json` path, and exactly four UTF-8 streams:
application, HTTP-library, stdout, and stderr. The directory and seal must be
absent before preflight. The campaign wrapper alone creates the directory,
captures those streams, rejects any unindexed enabled process-owned logging
handler, stops and flushes the runtime, and atomically seals a strict
file-count/size/hash manifest.

The wrapper then hashes the manifest and canonical ordered file set, atomically
creates the strict no-overwrite seal at its separately indexed path, and appends
one matching deterministic `campaign_log_capture_sealed` event to each extant
connector run in one DB transaction. Seal-event cardinality is conditional on
run existence: exactly one event per connector run that exists — two in a
completed dual run, exactly one after an NRC-first stop, where the ScienceBase
run correctly does not exist and no run is created merely to receive an
event. The seal and every extant-run event bind the
campaign-introduction evidence-index revision/digest used by the immutable
armings. The preflight
index revision is never rewritten; a later no-overwrite head can only add a
complete disjoint slice while preserving it through the predecessor chain. The
read-only evaluator resolves the four files, manifest, and seal only from
protected server configuration plus the verified unique-maximal index chain,
independently queries the event of every extant connector run, and requires
exact cross-domain parity; it never requires a seal event for a run whose
creation was correctly prevented, and a seal naming a nonexistent run fails.
It
accepts no index/log/seal path from a caller. This is local experimental tamper
evidence, not a signature, WORM store, or cryptographic nonrepudiation.

The network privilege window closes at raw admission. The acquisition child
never parses acquired bytes beyond the bounded admission media/shape checks
(ScienceBase nonempty CSV header/data-row shape; NRC `%PDF-` magic bytes): the
existing NRC document path runs native PDF
parsing, a default-on OCR fallback, in-process PaddleOCR, a Tesseract
subprocess, and Camelot table extraction in the invoking process, so parsing
may not share a process with the key or live egress. After the child's tree is
terminated and quiescence is proven, the downstream phase parses the admitted
NRC PDF only through `parse_admitted_blob_strict`
(`backend/app/services/nrc_aps_strict_parse.py`, frozen profile
`dual_live_proof_v1`), which rehashes the blob against its admitted SHA-256
and accepts no caller configuration. The profile forces the baseline engine
explicitly — the unforced PDF default would select the artifact-writing
OpenDataLoader engine — sets `ocr_enabled=false` behind a repaired gate that
now also closes the hybrid image-OCR branch (today that branch invokes
Tesseract on availability alone), carries no `document_type` or
`artifact_storage_dir`, and turns every prohibited branch fatal at its call
site: reached OCR attempt blocks, Camelot/advanced-table routing, and the
current exception-to-degradation conversions all raise instead of degrading.
The fixed bounds are exact, each with its measurement point and enforcing
code: 500 pages (page count at document open, without the generic thirtyfold
allowance); zero rendered pixels (no rasterization site is reachable and a
test sentinel proves zero render calls); 20,000,000 UTF-8 bytes of extracted
text (running counter at each unit append); 10,000 table rows and 200 columns
(native table extraction); zero temp-disk bytes (the entry point points the
process temp root at one fresh directory and requires it empty after parse);
2,147,483,648 bytes peak RSS and 300 CPU-seconds (checkpoint-sampled at
100-page chunk boundaries and parse end); 300 seconds wall-clock (the
existing monotonic parse deadline); 30,000,000 output bytes (the serialized
payload measured once on return); zero subprocess spawns (a pre-import
Python-level guard over the spawn primitives raises on any call). The entry
point also rejects any returned payload whose extractor identity is not the
baseline PDF extractor, whose OCR page count is nonzero, or whose degradation
codes include any OCR/advanced/visual code. Any refusal or breached bound
fails the campaign; nothing degrades. Memory, CPU, and wall-clock are
checkpoint-sampled failure detectors, not preemption of a blocking native
call, and the guards are Python process-level guards, not an OS sandbox — an
explicit experimental limitation and production-promotion requirement.

Validation starts only after both campaign phases are stopped and the
manifest/seal/events are complete. Its separate CLI requires live egress disabled, current
campaign-definition/grant settings cleared, and a fail-closed
application-process network guard installed before application/service imports;
raw socket, DNS, HTTP-client, and connector-transport probes must all be denied
in tests. The NRC key remains available only for in-memory exact-byte leak
comparison. This is a network-inert validator process, not a claim of
OS/firewall isolation.

The evaluator reconstructs the finite forbidden artifact-URL candidates from
the original grants and safe locator classes, verifies their hashes, loads the
NRC key only long enough to scan for its exact bytes, and examines raw,
JSON/HTML-unescaped, and percent-decoded-once/twice forms of every bounded
text/URI token. It reports only sink identity, offset, and a one-way hit digest.
OS, proxy, provider, and other machine-global logs remain outside this
experimental proof and are an explicit production-promotion requirement.

## 6. Authorization posture

Identity/role and connector authority are separate predicates. Reuse
`route_level_operator_authorization_required(headers, access="write")` only to
derive caller posture. It is never the grant resolver.

| runtime posture | arming behavior |
|---|---|
| `AUTH_OWNER=none` | permit only a direct-loopback, local, non-proxy, exclusive single-operator proof **and only** after the protected campaign definition and connector-specific grant bytes/digests verify and intersect; otherwise deny |
| trusted proxy + role enforcing + derived owner | require derived owner role, the independently verified definition, and the exact connector grant |
| trusted proxy + identity-presence mode | deny arming because owner role was not proved |
| caller-supplied reference, absent definition/grant, changed bytes, bad digest, expired/mismatched definition or grant | deny |

The campaign definition and each grant are strict JSON documents outside the
repository and runtime DB. The definition supplies the shared correlation
fields listed in section 5.1; its configured raw SHA-256 and rederived canonical
fingerprint must agree. Each grant must name schema/version, grant ID,
connector, campaign ID/fingerprint/definition digest, exact target, UUID4
arming nonce, `max_armings=1`, optional superseded-grant digest, ordered request
rules, host/port/method/path/query predicates, credential audience, per-stage
and total byte/request ceilings, the single-send detection allowance field,
timeout/rate, issued/expiry times, reviewed
code revision, operator mode, and explicit non-authorities. Its configured
SHA-256 is the lookup and authority key. The public arming request carries the
connector key, campaign fingerprint, expected grant digest, and client
idempotency key only.

Both grants must explicitly deny: other connectors/targets, search, automatic
retry, resume/recurrence, alternative-file selection, credential fallback,
post-expiry sends, continuation after code/revision change, external delivery,
production/support-profile promotion, additional parent armings, and implicit
unused-budget transfer. The NRC grant additionally denies all redirect
following; the ScienceBase grant admits only its separately reserved ordinal-3
redirect rule.

In local mode the protected server configuration and exact grant file—not the
campaign definition, `AUTH_OWNER=none`, the feature flag, or the HTTP
caller—supply connector authority. The definition is a required deny-only
intersection. The route must also require a direct loopback peer and
`TRUSTED_PROXY_MODE=false`. This is practical for the first local proof but is
not cryptographic nonrepudiation; supported multi-user operation requires a
signed grant service or equivalent trusted control plane.

## 7. Physical-request accounting

Every possible HTTP send has a connector-specific deterministic stage/ordinal
map:

- ScienceBase: `1=item_hydration`, `2=artifact`, `3=artifact_redirect`;
- NRC APS: `1=exact_accession_api`, `2=artifact`; no redirect follow is
  authorized in the first campaign.

Immediately before every send, one independent reservation transaction must:

1. reload/rederive the server-configured campaign definition, reload/rehash the
   connector grant, traverse the evidence-index chain, and require its
   configured revision to remain both the unique maximal head and the earliest
   complete-slice introduction revision bound by the arming;
2. lock/load the run and verify strict proof mode, `running` state, the exact
   active lease token, arming/definition/grant/campaign fingerprints, active
   index revision/digest, code revision, and both original half-open windows;
3. verify the requested stage/ordinal is the next permitted one, within the
   connector map and frozen ceiling, with every prior reservation terminal;
4. revalidate method, host, port, path/query rule, credential audience, the
   effective byte cap — the lesser of the stage cap and the remaining
   aggregate counted-byte budget under `max_run_bytes` — and any required
   derived-arming hash;
5. insert the deterministic `egress_reserved` event and commit;
6. recheck time/lease/flags/definition/grant hashes and unique-maximal
   index-head revision/digest, then capture `send_started_at` immediately before
   transport; an expired or changed definition/grant/index head records
   `reserved_not_sent` and sends nothing;
7. perform exactly one HTTP send with library retries and redirects disabled,
   cookies rejected, `Accept-Encoding: identity`, the final prepared request
   fingerprint-matched to the reservation, the counting adapter appending its
   counted-byte accounting record, and the absolute monotonic deadline and
   effective byte cap enforced at each chunk boundary while streaming;
8. record one completion or classified failure event, including the captured
   send-start time, and commit.

An existing reservation without completion is spent/unknown. It is never
replayed automatically. Commit uncertainty means no send. Every retry,
redirect, fallback, or probe is a distinct reserved physical send. A lease and
atomic compare-and-swap prevent concurrent execution of the same arming.

The canonical terminal-ledger projection is stable JSON over: schema ID,
connector/run/campaign/arming/definition/grant digests, evidence-index
revision/digest, frozen ceiling, and ordered entries containing only ordinal,
stage, reservation/completion event IDs,
normalized `reserved_at`/`send_started_at`/`completed_at`, request fingerprint,
method, safe host/path/query class, credential audience, status class, byte
count, and response-body SHA-256. It excludes free-text messages and secrets.
`ledger_terminal_hash` is the SHA-256 of that projection, rederived from DB
events. It is eligible for a `fresh_live` receipt only when all required stages
are terminal, no ordinal is missing/extra/reordered, every reservation has
exactly one completion, each reservation/send start falls inside the original
definition and grant windows, and the artifact completion hash equals the
admitted raw bytes. Completion may follow expiry only for a bounded request that
started inside both windows. Equality with either `expires_at` is expired in
current and historical checks.

The transport counter is concrete, not aspirational: a counting HTTP adapter
at the lowest application-visible Requests boundary, inside the
acquisition-only child that alone performs physical sends, appends one
secret-free deterministic record per physical send — exactly one even when a
send dies before any HTTP status exists, with a null status and a closed
error class — to the manifest-bound, seal-covered `http.jsonl` capture:
ordinal, stage, fingerprint of the final prepared request, canonical
status/header bytes, delivered body bytes, decoded body bytes, decoded-body
SHA-256, nullable response status, error class, and monotonic start/stop
readings paired with injected UTC evidence timestamps. The budget currency is
counted bytes, an application-visible metric, not wire octets: per send, a
deterministic re-serialization of the parsed status line and headers — the
Requests-adapter seam never sees the transmitted octets — plus body bytes as
delivered by the wrapped urllib3 read path before content decoding, including
redirect, partial, failed, and oversized responses. Chunked framing,
trailers, TLS records, TCP/IP traffic, DNS, and bytes buffered below the seam
but never delivered are outside the counted entity, and no claim covers them.
`max_run_bytes` bounds the run aggregate of counted bytes: exhaustion refuses
the next reservation before any send, and a chunk-boundary check that finds
the remainder crossed mid-stream aborts the read, counts every delivered
byte, and terminally classifies the send. Because `http.client` fully parses
the status/header block before the adapter seam runs (admitting up to 100
header lines of 65,536 B each), there is no per-send header threshold:
canonical status/header bytes are counted in full and spent, and the counted
aggregate can exceed `max_run_bytes` by at most one SINGLE-SEND DETECTION
ALLOWANCE of 6,684,672 B (defined in the plan's enforced-budgets section).
Any larger excess is a counter defect. This is an application-delivered
ceiling with a disclosed allowance — not a hard maximum and not a
network-level never-exceeded guarantee. A campaign
whose counted aggregate crossed the ceiling is never `fresh_live`.
`Accept-Encoding: identity` is sent so delivered and decoded body counts
coincide, and a response declaring any other encoding stops; canonical
status/header bytes are counted in full per send and recorded in the
counter; cookies are never stored or
replayed. Each send runs under an absolute deadline derived from
`request_timeout_seconds` and measured on the process monotonic clock, and
`min_request_interval_ms` is monotonic spacing per actual destination host —
no duration, budget, or rate decision reads the wall clock. The absolute
authority-window membership checks (campaign and grant `not_before`/`issued_at`/
`expires_at`) are the stated exception: they read the injected UTC clock, and
wall-clock trust there is an explicit, disclosed limitation of this MVP.
This app ledger plus that counter is adequate for the exclusive serial
experimental proof. It is not an independent network-provider
audit. Production promotion requires proxy-, firewall-, or OS-level egress
accounting in addition to the application ledger. The experimental transport
must ignore ambient proxy/cookie configuration, retain TLS verification, and
reject any allowed hostname whose immediate resolution includes a non-public
address. Those application checks reduce, but do not eliminate, DNS
time-of-check/time-of-use risk; the remaining limitation is explicit evidence,
not a production-readiness claim.

## 8. Exact ScienceBase contract

Target:

- connector: `sciencebase_mcs`;
- item: `63d1a3c6d34e06fef15006be`;
- desired filename: `mcs2023-germa_salient.csv`;
- surface: one public `.csv` file only;
- credentials/cookies: none.

Maximum three physical requests, zero automatic retries:

1. `GET https://www.sciencebase.gov/catalog/item/63d1a3c6d34e06fef15006be?format=json`;
2. `GET` the exact `downloadUri` from the unique item `files[]` object whose
   `name` equals `mcs2023-germa_salient.csv` exactly and case-sensitively;
3. optionally, one separately validated same-class redirect `GET` only after
   `301`, `302`, `303`, `307`, or `308`.

Allowed hosts are exactly `www.sciencebase.gov` and `sciencebase.gov`, HTTPS
port 443, after public-address validation. The hydration response is capped at
5 MiB; the artifact BODY-STAGE cap is 64 MiB; the nominal run ceiling is the
grant's `max_run_bytes`, which uses the disclosed one-allowance detection
semantics (a crossing is terminally classified and never `fresh_live`); concurrency is one.
The artifact is streamed through the cap.

Hydration is strict UTF-8 JSON with duplicate object-member rejection before
ordinary dictionary materialization. The root has one `files` array. Exactly
one object may carry the exact filename; it must contain exactly one nonblank
string `downloadUri`, no `url` fallback or dual locator, and no surrounding
whitespace/control characters. Lexically duplicate `files`, `name`, or
`downloadUri` keys fail even when their values agree. The untrimmed locator is
checked against the raw URL grammar before normalization.

The parent grant fixes ordinal 1 to the raw ASCII item path and raw query
`format=json` byte-for-byte. For ordinal 2, the returned URL must use an
allowed host, port 443, raw ASCII path byte-for-byte
`/catalog/file/get/63d1a3c6d34e06fef15006be`, no raw `@` authority or `#`
delimiter (including empty), and raw ASCII query byte-for-byte
`f=mcs2023-germa_salient.csv` **before** strict UTF-8
confirmation of that one pair. A permissive query helper is not an admission
parser. Leading/trailing/repeated `&`, `;`, empty segments, missing/extra `=`,
`+`, any `%` encoding, duplicate/alternate/extra keys, raw-path percent
encoding/backslash/dot segments, or filename case drift fails before
reservation. The executor commits a derived arming
containing only the URL hash and safe host/path/query class
`exact_single_f_expected_filename` before reserving ordinal 2; the exact URL
and raw query remain only in process memory. The optional ordinal 3 must
satisfy the same closed host/path/query grammar and receive its own derived
arming. It also requires exactly one nonblank raw `Location` value from a
lossless header multimap, with no surrounding whitespace/control characters;
duplicate/disagreeing locations, `300`, `304`, `305`, `306`, or any other
status stop without reserving ordinal 3. Any other URL or redirect stops for a
new owner decision.

Strict target/provenance download-URI scalars and alias URLs remain null. The
raw hydrated item and its `files[]` objects are not snapshotted; only the
response-body hash, selected filename/checksum facts, URL hash, and safe
host/path/query class persist.

The file response must be complete nonzero `200` content. Admit `text/csv` or
`application/csv`; admit `application/octet-stream` only when the exact `.csv`
name is unchanged and strict BOM-tolerant UTF-8 CSV parsing produces a nonempty
header and at least one data row. Reject HTML/PDF/archive signatures, NUL bytes,
an empty table, or a media/parse disagreement.

No search, conditional headers, `304`, resume, recurring sync, distribution
link, web link, automatic alternative-file selection, or automatic retry is
allowed. If the filename is absent, duplicated, malformed, points outside the
host/path policy, has no unique admitted `downloadUri`, or changes before
download, the run stops.

## 9. Exact NRC APS contract

Target accession: `ML17123A319`.

Current official evidence supports a narrower first attempt:

- the current NRC APS API guide documents exactly two keyed API endpoints and
  says Get Document returns metadata, indexed content, and a `Url`;
- the guide's current sample result uses the public artifact shape
  `https://www.nrc.gov/docs/<prefix>/<accession>.pdf`;
- the current NRC ADAMS page says APS is the latest public interface and that
  ADAMS documents are PDFs. It does **not** currently reproduce the earlier
  WBA-transition notice observed during planning, so that earlier observation
  is historical, unbound evidence and is not used as design authority.

Sources checked 2026-07-29:

- [NRC APS API Guide](https://adams-search.nrc.gov/assets/APS-API-Guide.pdf);
- [NRC ADAMS public-documents page](https://www.nrc.gov/reading-rm/adams);
- [NRC APS developer portal](https://adams-api-developer.nrc.gov/).

Because the accession is already exact, a search POST adds no identification
value and is omitted. The initial parent grant allows at most two physical
requests, zero automatic retries:

1. keyed `GET` to
   `https://adams-api.nrc.gov/aps/api/search/ML17123A319`;
2. unkeyed `GET` only when the returned URL is exactly
   `https://www.nrc.gov/docs/ML1712/ML17123A319.pdf`, after its hash/class
   derived arming commits.

The APS response must be strict UTF-8 JSON decoded with duplicate object-member
rejection before ordinary dictionary materialization. It must contain exactly
one lexical `Url` member; duplicate `Url` keys fail whether their values agree
or differ.

That proposed artifact path is a deliberately narrow inference from the
official guide's sample grammar and the named accession; it is not claimed as
the live target's current URL. The owner may grant it for a fail-closed first
attempt. The response must match exactly—HTTPS, port 443, host
`www.nrc.gov`, raw case-sensitive ASCII path byte-for-byte, no path percent
encoding/backslash/dot segment, no userinfo, and no raw `?`/`#` delimiter—even
an empty one—or the run stops without an artifact send.
`adams-search.nrc.gov` is documentation evidence, not a runtime artifact
allowlist entry.

The subscription key is sent only as `Ocp-Apim-Subscription-Key` to
`adams-api.nrc.gov:443` on the exact Get Document API request. It is never sent
on the artifact request. A direct artifact
`401` or `403` is a STOP; credential fallback would require a separately
reviewed owner grant after its audience is known. API and artifact redirects
always stop; the first campaign follows none.

The artifact client accepts only a nonzero complete `200` PDF under 64 MiB with
`application/pdf`, or `application/octet-stream` when `%PDF-` magic and the
document metadata both identify PDF content. Reject redirects, partial, empty,
not-modified, multi-choice, unauthorized, rate-limited, HTML, and server-error
responses.

The exact normalized artifact URL is held only between parsing the Get Document
response and the one artifact send. Target/provenance download-URI and alias
URL scalar columns are null; the raw Get Document response is not snapshotted.
The committed derived arming, every other DB field, logs, ordinary API
serialization, events, reports, and exported evidence carry only its SHA-256
plus the safe exact-path class. Secret headers, query/fragment material, and
request/response bodies are never persisted.

The repository fixture proves downstream document behavior. It does not prove
that the current live response will match the proposed public artifact rule.
That fact remains `EMPIRICALLY-OPEN`, which is precisely why the derived arming
and fail-closed exact match are required.

## 10. End-to-end continuity

One authoritative `layer3.connector_origin_continuity.v1` receipt is persisted
under the connector target's `source_reference_json`. Other provenance,
source-intake, APS-linkage, Layer 3, review, package, and handoff records carry
only its target ID and receipt hash. They are projections, not competing
canonical copies. The evaluator rehashes raw storage and reconstructs the
authoritative receipt rather than trusting any stored projection.

`fresh_live` is derived, never accepted as an input field. It requires a
server-verified original grant digest, exact one-use consumption marker, a
strict proof arming bound to its evidence-index introduction revision/digest, a
valid terminal-ledger projection, every
reservation/send timestamp inside
`issued_at <= timestamp < expires_at`, exact required request stages, complete
fresh `200` facts, and an artifact completion hash equal to the admitted raw
bytes. The grant may be current or resolved from the protected historical
evidence index for read-only rederivation; its present-day expiry does not
erase historical proof, and historical evidence never authorizes another
send. A fixture without that ledger is mechanically `offline_fixture` and
cannot be relabeled by a caller or by copying receipt JSON.

For the reserved campaign lane, continuity is checked inside the same
transaction and **before** each authoritative mutation: Gate C typing commit,
execution selection/start and artifact creation, result-review commit, package
commit, package-review submit, and handoff preparation. A failed check leaves
DB state and artifact files unchanged.

### 10.1 ScienceBase vertical

The named first vertical is:

`live response bytes`
→ `ConnectorRunTarget`
→ `DatasetSourceProvenance`
→ `DatasetVersion`
→ connector source-intake record
→ Gate B material admission
→ Gate C `descriptive_summary`
→ execution output
→ result review
→ three packages
→ package review submission
→ handoff/export preparation.

Before every transition, recompute or compare the same content identity:

`SHA256(raw bytes)`
`= ConnectorRunTarget.downloaded_sha256`
`= DatasetSourceProvenance.downloaded_sha256`
`= DatasetVersion.content_hash`
`= connector-source-intake content_sha256`.

The authoritative continuity receipt also binds connector key, item ID, exact filename,
source-artifact key, raw-storage reference, run ID, target ID, version ID,
campaign-definition digest/fingerprint, evidence-index introduction
revision/digest, arming fingerprint, grant digest, and `ledger_terminal_hash`.

The first Gate C method is one bounded descriptive summary because it
demonstrates actual analytical utility without introducing model egress or a
domain-specific inference claim.

### 10.2 NRC APS vertical

The companion vertical is:

`live APS detail/artifact`
→ connector target/raw artifact
→ APS process/content document
→ material snapshot
→ qualitative typing/unit
→ plan
→ execution/pass output
→ result review
→ three packages
→ package review submission
→ handoff/export preparation.

The existing downstream qualitative chain should remain intact. The new seam
must prove that its initial document hash is the freshly acquired connector
artifact hash and that every downstream receipt continues to bind that origin.

### 10.3 Output and package receipts

- Hash every analysis-artifact byte sequence and record the digest in
  `AnalysisArtifact.metadata_json`.
- Construct an ordered artifact receipt list and an artifact-set hash.
- Store the exact output-manifest byte hash outside the manifest itself, for
  example in `L3PassRun.summary_json`, to avoid a self-hash.
- Recompute these receipts at execution-output materialization, review,
  package construction, package submit, and handoff preparation.
- Require one ScienceBase `descriptive_summary_result` artifact.
- Require exactly the three named package kinds.
- Require package payload bytes to match `L3OutputPackage.payload_hash`.
- A mismatch blocks the current operation; it does not repair or regenerate
  evidence silently.

## 11. Milestones and grouped gates

| milestone | output | grouped governance gate | proof state on success |
|---|---|---|---|
| M0 | this record and executable plan | architecture/spec review | design frozen; no egress |
| M1 | protected campaign-definition correlation, current-grant authority, one-campaign-per-index-revision lifecycle, one-use grant-consumption fence, historical evidence resolvers, arming, CAS, ledger, one-send transport | shared offline control review | non-multipliable egress controls and post-expiry auditability offline-proven |
| M2 | connector-specific strict modes | one shared adversarial network-contract review; separate connector tests | both clients fail closed offline |
| M3 | source-to-Layer3 continuity receipts | shared integrity review | both verticals hash-bound offline |
| M4 | crash/concurrency/redaction/negative suite | one readiness review | implementation candidate ready for owner preflight |
| M5 | exact server-configured campaign definition, single-use connector grants, new immutable evidence-index revision/marker bindings, and the NRC parent arming only — both grant digests verified, ScienceBase grant left unconsumed | common campaign review, connector-separated grant digests/receipts | live execution authorized once as written; original definition, grant, consumption, and index bytes preserved |
| M6 | NRC acquisition; then, only after the service-rederived NRC acquisition-success predicate, ScienceBase parent arming and acquisition, all executed inside the acquisition-only child, with derived artifact armings created only from admitted responses; network/credential capability removed at raw admission by process-tree stop, session close, key/grant clear, and quiescence proof | per-connector budget and outcome check | fresh bytes acquired or safely stopped; privilege window closed; an NRC stop leaves the ScienceBase grant unconsumed |
| M7 | network-inert Layer 3C, review, three packages, submit, handoff prepare in a secret-free process with network and subprocess spawn denied, parsing only through the strict entry point under the exact `dual_live_proof_v1` bounds | combined campaign closeout | one named workflow per source proven through boundary |
| M8 | second campaign under a new definition/grants and strict-superset index successor, no code changes; reject index rollback/fork and old-grant re-arming, then re-evaluate both campaigns | repeatability and historical-lifecycle review | repeatability evidenced without losing campaign-1 auditability or reviving budget |
| M9 | explicit promotion decision | new owner/product/security decision | either remain experimental or design production controls |

NRC runs first because its keyed API/public-artifact behavior has more unknowns and can
invalidate the shared campaign before the simpler anonymous acquisition spends
its grant. The isolation is mechanical, not procedural: preflight verifies both
grant digests but arms and consumes NRC only. The ScienceBase parent arming —
and with it the atomic consumption marker that spends its grant — cannot be
created until the arming service itself, inside the same creation call and
before the consumption-marker create-new operation, rederives and passes the
full NRC acquisition-success predicate. That predicate has one authoritative
definition — `evaluate_nrc_acquisition_success` in the plan's Task 2 arming
service — restated here in governance form, with every clause rederived from
authoritative records and never trusted from a stored hash or projection
column: strict terminal `completed` committed only by the strict-only
finalizer, with exactly one valid terminal event and no later failure or
cancellation evidence; no unexpired execution lease; a terminal ledger
rederived from DB events with reservation/completion parity within the NRC
grant ceiling and no `spent_unknown` entry; one-to-one field agreement
between that rederived ledger and the strictly parsed manifest-bound
transport counter; and a complete admitted `200` PDF within byte limits
whose raw SHA-256 REHASHED at evaluation time from the content-addressed NRC
target blob (never a stored-column/receipt read) equals the
rederived ledger and counter hashes. [S3 delta 2026-07-30: this governance
restatement formerly read "on the canonical connector-target receipt"; synced
to the plan Option-B amendment.] The service binds the NRC parent-run ID
and the `ledger_terminal_hash` it rederived into the ScienceBase envelope;
because marker creation is reachable only through this service call, no
caller path — the exposed arming route included — can consume the
ScienceBase grant on a weaker check, and wrapper ordering is never the
enforcement mechanism. Any failed or indeterminate predicate clause —
including an NRC failure, safe stop, or indeterminate outcome —
therefore ends the campaign while the expected ScienceBase consumption-marker
path is verifiably absent and its grant unconsumed; the abandoned grant is
retired by campaign-close head advancement, never transferred or reused.
Campaign-log closeout is phase-aware in that state: the wrapper still seals
the capture, exactly one `campaign_log_capture_sealed` event is expected — on
the extant NRC run only — and neither the closeout nor the evaluator may
require a seal event for the ScienceBase run whose creation was correctly
prevented, or create a run merely to receive one.

M0/M1 may proceed in an isolated worktree independently of the current Claude
session's B1b review/capture lane. If both lanes would share a mutable worktree,
runtime, port, evidence root, credential process, or sole operator attention,
the operator must schedule an explicit resource mutex. That is a collision
control only: B1b status, authority, protected artifacts, and external-review
results neither block nor authorize connector work.

## 12. Acceptance and failure criteria

### Campaign pass

The campaign passes only if:

1. baseline code revision, verified unique-maximal evidence-index chain and
   campaign introduction revision/digest that was the head before arming,
   verified campaign-definition raw digest and
   rederived canonical fingerprint, both verified owner grant digests/nonces,
   both exact one-use consumption markers, both deterministic parent armings —
   the ScienceBase envelope binding the NRC parent-run ID and the
   `ledger_terminal_hash` the arming service rederived when the full NRC
   acquisition-success predicate passed at creation, proving the whole
   predicate — not terminal status alone — preceded ScienceBase
   consumption — and every response-derived arming are recorded;
2. every physical request reloads/rederives the exact server definition,
   revalidates the exact connector grant and the unique-maximal index head
   against the arming-bound revision/digest, and has a prior committed
   in-ceiling reservation, with reservation/send start inside both original
   half-open windows;
3. observed sends do not exceed either connector’s ceiling;
4. no credential reaches an unapproved audience or redirect;
5. both artifacts are complete `200` responses within byte limits, each strict
   connector run carries exactly one valid deterministic terminal event with
   status `completed`, no unexpired execution lease, and no later failure or
   cancellation evidence, and `fresh_live` is independently derived from
   their terminal ledgers;
6. exact target predicates pass;
7. raw hashes and every continuity receipt agree;
8. each appropriate Layer 3 chain reaches result review;
9. exactly three packages per result are produced and payload hashes match;
10. package submission and handoff preparation revalidate the same origin;
11. strict URL scalar fields are null; the four files, manifest, separate
    no-overwrite seal, and both connector-run seal events have exact
    cross-domain parity; and every scalar/text/JSON/non-source-file plus
    protected runtime-log scan contains no raw secret, exact derived URL/query
    in raw or escaped form, raw metadata object, or unredacted header;
12. the log seal and both connector-run seal events bind the same introduction
    index revision/digest as the armings, even after a later strict-superset head
    rotation; and
13. an independent review finds no blocking discrepancy.

### Connector-local fail

A connector stops safely on any definition/grant/host/path/method mismatch,
introduction-revision/current-head mismatch, unknown redirect, expired
definition or grant (including equality with either
`expires_at`), consumed/missing/mismatched grant marker,
second-parent-arming attempt, budget exhaustion, reservation ambiguity,
duplicate executor, timeout, partial/empty/oversized/wrong-type content, target
mismatch, hash mismatch, secret-audience ambiguity, or persistence failure.

One connector’s failure does not make the other connector successful, does not
expand the other grant, and does not satisfy the combined campaign. An NRC
stop precedes ScienceBase arming, so it leaves the expected ScienceBase
consumption-marker path absent and that grant unconsumed; the evaluator
verifies that absence directly rather than inferring it from ordering.

### Evidence insufficiency

If the DB request ledger and the manifest-bound transport counter disagree in
any way — a missing, extra, or unparseable counter record; a mismatched
ordinal, fingerprint, status, byte count, or body hash; or a failed
rederivation of the `max_run_bytes` counted-byte aggregate — including a
ceiling crossing without its terminal oversized or budget-exhaustion
classification, or an overshoot beyond the SINGLE-SEND DETECTION ALLOWANCE
stated in section 7 — or of
`min_request_interval_ms` spacing — the result is `INDETERMINATE` and fails; it is never narrated into
success. If a live send could have occurred but its completion
is unknown, count it as spent and do not replay it. If downstream bytes cannot
be re-derived, do not claim continuity.

## 13. Risks and containment

| risk | likely implication | containment |
|---|---|---|
| caller presents a plausible campaign/grant reference | identity or correlation is mistaken for egress authority | server-load/rederive exact definition, then server-load exact grant bytes; configured SHA-256; closed schemas; per-send intersection/revalidation |
| opaque/reused campaign fingerprint | unrelated grants can be grouped under unbound governance | strict protected definition; raw digest plus rederived canonical fingerprint; exact one-definition/two-grant/one-capture index slice |
| live publisher shape drift | target unavailable or parser mismatch | exact predicates; stop; new offline fixture before retry |
| permissive query parsing drops empty/trailing fields | artifact authority silently widens | byte-for-byte raw path/query grammar before strict pair confirmation; adversarial separator/encoding tests |
| permissive JSON collapses duplicate members or locator preference | a non-unique file/URL looks unique | strict duplicate-member rejection; exact `downloadUri` only; no trim/fallback/dual locator |
| broad `3xx` handling or collapsed `Location` headers | an unreviewed redirect becomes ordinal 3 | admit only 301/302/303/307/308; lossless exactly-one `Location`; every other case stops |
| secret crosses host/redirect | credential disclosure | unkeyed artifact fetch; explicit API-key audience; never follow an API redirect |
| credential-like derived URL is persisted | DB/backup/log becomes a bearer-secret store | strict URL scalars null; raw metadata never snapshotted; safe whitelists; protected manifest/seal/event-bound runtime logs; raw/escaped scalar/text/JSON/non-source-file scan; persist URL hash plus closed class only |
| logs and self-hashing manifest are rewritten together | historical custody scan passes altered bytes | separate indexed no-overwrite seal plus matching deterministic events on every extant connector run; production still requires signed/WORM evidence |
| hidden HTTP retry | request ceiling exceeded | one-send transport below retry layers |
| ambient proxy/cookie state or DNS rebinding | credential audience or destination differs from the reviewed request | isolated session with `trust_env=False`, empty cookies, TLS verification, public-address checks; production requires independent egress enforcement |
| network privilege outlives acquisition | parser/OCR/table workloads execute while the key and live egress are still present | acquisition-only child ends at raw admission; process-tree stop, session close, key/grant clear, and quiescence proof before parse; secret-free network- and subprocess-denied downstream process; strict entry point with every OCR path closed and Paddle/Camelot routing fatally refused at their call sites; exact `dual_live_proof_v1` parse bounds |
| crash after send | result unknown, accidental replay | reservation counts spent; no auto-resume |
| concurrent executor | duplicate sends | atomic `armed → pending` claim with `claimed_now`-gated enqueue; lease-acquisition-only `pending → running`; reservation requires `running` plus the exact active lease |
| oversized response | memory/disk pressure | streamed byte ceilings, hydration cap |
| large legal header block under nearly exhausted budget | counted aggregate exceeds `max_run_bytes` by up to one SINGLE-SEND DETECTION ALLOWANCE | allowance disclosed (sections 7 and 15) and grant-bound; every header byte counted in full; terminal oversized classification; never `fresh_live`; adversarial test in plan Task 3 |
| stale historical filename | wrong ScienceBase file | confirm exact name in hydration; no fallback |
| fixture/live conflation | overclaimed readiness | separate `OFFLINE-PROVEN` and fresh-live receipts |
| combined governance conflates grants | authority bleed | canonical shared definition is deny-only; independent grants/armings |
| internal handoff called delivery | false product claim | explicit same-origin/internal terminology |
| event-table MVP outgrows use | race/accounting weakness | promotion trigger for normalized schema |
| caller or copied JSON asserts `fresh_live` | fixture enters the live proof chain | derive proof class from verified ledger and raw-byte equality; evaluator rederives |
| current definition/grant expires or rotates | an older valid campaign becomes unverifiable, or stale authority is accidentally revived | protected content-addressed index revision chain; both event-time window checks; historical evidence types rejected by every send-capable API |
| configured index rolls back or forks | a valid-looking head silently drops failed/history slices | unique-maximal linear-chain census; exact predecessor; monotonic revision; strict-superset successor; no-overwrite content-addressed objects; arming/seal/event introduction binding |
| an unused campaign slice survives under a later head | it can arm under the descendant but fail introduction-parity only after consuming its grant or sending | one complete campaign per revision; resolve the earliest complete-slice revision; require it to equal the current head before marker/DB/event/network activity |
| one grant creates multiple parent armings | per-arming ceilings multiply beyond owner intent | UUID4 nonce; `max_armings=1`; deterministic run ID; atomic no-overwrite consumption marker; new definition/campaign plus explicit superseding grant after fail-closed loss |
| live session authority bleed | unrelated B1b decision reused | separate lane, records, grants, and closeouts |

## 14. Proximity and trajectory

The project is not starting from zero and is not one click from the goal.

- Acquisition foundation: strong.
- Offline ScienceBase-to-Gate-B proof: present.
- NRC downstream qualitative workflow: strong.
- Shared review/package/handoff machinery: present.
- Strict campaign-definition/fingerprint correlation: missing.
- First-use arming and physical-send ledger: missing.
- Strict fresh one-file ScienceBase mode: missing.
- Strict NRC keyed-API/unkeyed-artifact credential and redirect mode: missing.
- Connector-origin hash continuity through final handoff: incomplete.
- Fresh dual-source evidence: not run and not authorized.

The shortest defensible trajectory is therefore controls → strict connector
modes → continuity → offline adversarial proof → owner armings → live bytes →
downstream closeout. Reordering live egress before the control and continuity
work would produce weaker evidence and create avoidable safety ambiguity.

## 15. Explicit non-claims

This record does not claim:

- that either fresh live acquisition has occurred;
- that the current owner has granted either connector’s egress;
- that the historical ScienceBase filename is still exposed live;
- that the APS live artifact URL or credential behavior is known;
- that fixtures prove live acquisition;
- that one connector’s grant covers the other;
- that the existing supported profile includes keyed NRC APS;
- that application-ledger counts are an independent network audit;
- that the counted-byte aggregate can never exceed `max_run_bytes` — it is
  bounded, under non-defective counting, by `max_run_bytes` plus one disclosed SINGLE-SEND DETECTION
  ALLOWANCE;
- that current handoff preparation is third-party delivery;
- that the no-migration MVP is safe for multi-process or production use;
- that a technical pass equals owner acceptance or product promotion;
- that the live Claude session has ended;
- that its B1b work grants, modifies, or supersedes connector authority.

## 16. Live-session coordination boundary

The operator-supplied Claude export is a changing, noncanonical coordination
artifact. The snapshot inspected for this record was:

- updated `2026-07-29T05:50:53.8317628Z`;
- 2,340,667 bytes;
- SHA-256
  `2a2369125fecb40261de1ec10f36b66628c5cc7a827a2c1504d03e638e2e8407`.

Its latest exported state ends with an external re-audit waiter for the B1b
minimal capture instrument. That observation is a snapshot, not proof that the
live session stopped or completed. The export contains no authority for the
targets or egress contracts in this campaign.

Offline connector M0/M1 work is not semantically dependent on that waiter. It
may proceed only in collision-free resources. Any shared-resource scheduling
decision is an operator mutex, not a transfer of authority or proof between
the lanes.

## 17. Maintenance rule

Update this record append-only when a campaign-level decision, target,
milestone, proof outcome, or non-claim changes. Record the exact code revision
and evidence hash for live outcomes. Do not rewrite a failed or superseded
attempt into success; add a dated correction or successor record.

Implementation details belong in the companion plan. Whole-program history
belongs in `docs/MASTER_CONTEXT.md` and `docs/program-context/`. Layer 3 progress
manifests and the progress board change only when implementation/proof claims
actually change; this planning record alone does not do so.
