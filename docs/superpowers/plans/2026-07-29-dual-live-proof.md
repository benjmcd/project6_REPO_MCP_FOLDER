# Dual Live Acquisition-to-Handoff Proof Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
>
> **Status:** M0 candidate. This plan grants no implementation or network
> authority and is not frozen until co-committed after architecture/spec review.

**Goal:** Prove one freshly retrieved ScienceBase CSV and one freshly retrieved
NRC APS PDF from connector-specific owner authority through Layer 3C execution,
review, exactly three packages, package submission, and internal handoff
preparation without exceeding a physical-request or credential boundary.

**Architecture:** Add a default-off, no-migration proof lane that separates
immutable arming from execution and splits every live campaign at a hard
process boundary: an acquisition-only child process alone holds credentials
and narrow live egress and ends at raw admission (performing only the bounded
admission media/shape checks of invariant 21), and a secret-free,
network-denied downstream process performs all document parsing and Layer 3C
work only after the child's process tree is stopped and process/port
quiescence is proven. At most one campaign process is alive at any instant, preserving the
serial single-writer budget model. Reuse `ConnectorRun`,
`ConnectorRunSubmission`, `ConnectorPolicySnapshot`, and deterministic
`ConnectorRunEvent` rows for armings and request reservations. Load two exact
connector-specific owner grants plus one strict shared campaign definition from
protected server paths by configured SHA-256. Rederive the definition's
canonical fingerprint as a non-authoritative correlation fence, use a one-send
transport under connector-specific strict modes, and persist one canonical
origin receipt on the connector target. Preserve the verified non-secret
definition/grant bytes through separately configured, protected,
content-addressed campaign-evidence-index revisions forming one unique-maximal
strict-superset chain, so an expired or rotated campaign remains
read-only-verifiable without making an old grant executable. Both flows commit
a URL-hash/path/query-class derived arming before a detail-derived artifact GET;
exact derived URLs remain process-memory-only. The campaign's index revision
also binds one protected four-stream runtime-log capture so the evaluator can
rehash and scan the declared application-process log surface without caller
paths.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy, Requests, SQLite
and PostgreSQL-compatible SQL, pytest, PowerShell, SHA-256, UUIDv5.

---

## Authority, baseline, and execution rules

- Design baseline:
  `c1fcd840b421ceafb560266858a75808207f4540`.
- Before implementation, fetch `project6-origin/main`, create a clean short
  worktree under `worktrees/`, and re-audit every named symbol against that
  fresh tip.
- Do not implement in the dirty preservation root or in this documentation
  worktree.
- Tasks 1-9 are offline. Monkeypatched transports and fixtures are mandatory;
  they authorize zero egress.
- Task 10 aligns operator/canonical documentation but still sends nothing.
- Task 11 is owner-gated and cannot begin from this plan alone.
- Keep generic connector behavior backward-compatible. The reserved proof mode
  may be created only by the arming service, never by the current generic
  `/connectors/*/runs` routes.
- Every test uses isolated runtime state. No validate action seeds or generates
  evidence; an empty runtime fails closed.
- No schema migration is allowed in the experimental serial MVP. Stop and
  redesign if a correct implementation requires a new table or multi-process
  budget guarantee.
- Commit each task separately after its focused tests and `git diff --check`
  pass. Do not push or open a PR without the normal project authority.

## Target state and fixed invariants

The campaign record is
[`docs/campaign-records/2026-07-29-dual-live-proof.md`](../../campaign-records/2026-07-29-dual-live-proof.md).
The implementation must preserve these invariants:

1. caller identity, role, flags, and caller-supplied references are not grant
   authority; exact server-loaded grant bytes and configured digest are;
2. arming creation performs no network call and queues no background task;
3. execute accepts only the path arming ID, execution idempotency key, and
   expected arming fingerprint, never replacement connector configuration or
   grant fields;
4. a strict run moves only along
   `armed -> pending -> running -> completed|failed|cancelled`: one atomic
   `armed -> pending` compare-and-swap admits exactly one claim, executor
   lease acquisition is the only `pending -> running` transition, and the
   strict-only finalizer commits the one terminal transition;
5. every physical send atomically revalidates the definition/grant
   intersection, the unique-maximal arming-bound evidence-index head, expiry,
   lease, stage, ordinal, ceiling, and request rule before its committed
   reservation and repeats the head check immediately before transport;
6. an unresolved reservation is spent and cannot be replayed automatically;
7. Requests retries and redirects are disabled at the physical-send boundary;
8. ScienceBase is anonymous and exact-item/exact-file only;
9. the NRC key reaches only `adams-api.nrc.gov:443`; the initial artifact is an
   unkeyed exact `www.nrc.gov` PDF and no NRC redirect is followed;
10. `fresh_live` is derived from the canonical terminal ledger and raw bytes,
    never accepted from a caller or stored projection;
11. raw bytes retain one SHA-256 through source admission, execution, review,
    packaging, submission, and handoff preparation;
12. one connector-target receipt is canonical; all downstream copies are
    receipt-ID/hash projections;
13. every continuity guard executes before its authoritative state/file
    mutation and in the same transaction where applicable;
14. package kinds are exactly `canonical_internal`, `user_facing`, and
    `review_facing`;
15. handoff preparation is not represented as third-party delivery;
16. live sends use only the current configured campaign definition intersected
    with the current connector grant while both are unexpired; historical
    validation uses distinct non-executable evidence resolvers and checks that
    recorded sends occurred inside both original windows;
17. each connector grant binds one owner-chosen arming nonce and exactly one
    deterministic parent arming; client idempotency keys cannot multiply its
    physical-request ceiling;
18. exact derived artifact URLs and raw metadata objects remain ephemeral:
    strict-lane URL scalar fields are null, metadata is whitelist-sanitized,
    and only URL hashes plus closed host/path/query classes persist;
19. ScienceBase raw path/query authority is byte-for-byte exact before
    permissive parsing, while the protected four-stream runtime-log capture is
    manifest-bound and scanned in raw/escaped forms; machine-global logs are
    outside the experimental claim.
20. immutable content-addressed evidence-index revisions form one no-overwrite,
    gap-free linear chain with a unique maximal configured head; every successor
    is a strict superset that introduces exactly one complete campaign slice,
    arming requires that campaign's introduction to be the current head, and
    each campaign's arming/seal/events bind that revision/digest.
21. credentials and live egress capability exist only inside the
    acquisition-only child process, which fetches and durably content-addresses
    the raw artifacts and never parses them beyond the bounded admission
    media/shape checks (ScienceBase nonempty CSV header/data-row shape under the
    streamed cap; NRC `%PDF-` magic-byte inspection); before any document
    parse, the entire
    child process tree is stopped, HTTP sessions are closed, key/grant/live-
    egress environment is cleared, and process/port quiescence is proven;
    document parsing and every Layer 3C step run in a secret-free process
    whose pre-import guard denies socket, DNS, HTTP, and subprocess-spawn
    activity; the first proof parses only through the strict entry point,
    which closes every OCR path and fatally refuses the Paddle/Camelot and
    external-engine routings at their call sites, under the fixed
    `dual_live_proof_v1` bounds (Task 5 Step 3) whose breach is a campaign
    failure, not a degradation.

## Task 1: Add strict campaign, grant, target, and authorization contracts

**Files:**

- Create: `backend/app/services/connector_egress_authorization.py`
- Modify: `backend/app/schemas/api.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_egress_auth.py`
- Test: `backend/tests/test_egress_schema.py`

### Step 1: Write failing schema tests

Cover:

- `extra="forbid"` at every grant/rule/arming/target level;
- a protected strict campaign definition binds the exact campaign ID, code
  revision, two connector keys/targets, acceptance/evidence/review profiles,
  NRC-first order, exact package kinds, common half-open governance window, and
  non-authorities;
- its canonical fingerprint is rederived from canonical definition bytes that
  exclude both the fingerprint and all grant digests, avoiding a digest cycle;
- exact connector discriminator;
- SHA-256, ID, hostname, method, path-class, expiry, and positive-ceiling
  validation;
- ScienceBase fixed item and filename;
- NRC fixed accession and exact first-attempt public artifact rule;
- a credential audience naming any host except `adams-api.nrc.gov` is rejected;
- the exact connector-specific stage/ordinal maps are enforced;
- a campaign fingerprint mismatch is rejected;
- missing, changed, malformed, oversized, symlink/reparse-point, expired, or
  wrong-revision configured campaign-definition bytes/digest fail closed;
- no secret value or authority field can appear in the public arming request;
- an unknown, changed, malformed, oversized, symlink/reparse-point, expired, or
  wrong-revision configured grant fails closed;
- ScienceBase artifact rules require the raw ASCII query component to equal
  `f=mcs2023-germa_salient.csv` byte-for-byte before any query helper runs,
  then confirm the single strict UTF-8 pair; leading/trailing/repeated
  separators, blank fields, `;`, `+`, `%` encodings, extra `=`, and alternate
  keys fail;
- the protected campaign-evidence index is strict, duplicate-free,
  content-addressed, path-traversal-safe, and cannot be selected by caller
  input;
- its immutable revisions form one no-overwrite, gap-free linear chain whose
  configured head is uniquely maximal; rollback, fork, wrong predecessor,
  non-monotonic revision, dropped/changed prior reference, partial new slice,
  orphan index object, or non-content-addressed filename fails;
- revision 1 contains exactly one complete campaign slice, and each successor
  adds exactly one complete disjoint slice; a campaign may arm only while its
  earliest complete-slice revision is the configured unique-maximal head;
- its log-capture reference must equal the one deterministic campaign
  directory/manifest and exact four-stream set; missing, duplicate, extra,
  pre-existing, traversing, or caller-selected paths fail;
- each grant has `max_armings=1`; different or concurrent client keys cannot
  create a second parent arming from the same grant in any run status;
- caller JSON cannot override any server-loaded grant field.

Use these closed grant, public-request, and protected-evidence models:

```python
class ScienceBaseFreshTargetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_key: Literal["sciencebase_mcs"]
    item_id: Literal["63d1a3c6d34e06fef15006be"]
    exact_file_name: Literal["mcs2023-germa_salient.csv"]
    locator_key: Literal["downloadUri"]


class NrcApsFreshTargetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connector_key: Literal["nrc_adams_aps"]
    accession_number: Literal["ML17123A319"]


class DualLiveCampaignDefinitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.dual_live_campaign_definition.v1"]
    campaign_id: UUID4
    code_revision: str
    connector_keys: tuple[
        Literal["sciencebase_mcs"], Literal["nrc_adams_aps"]
    ]
    sciencebase_target: ScienceBaseFreshTargetV1
    nrc_target: NrcApsFreshTargetV1
    acceptance_profile: Literal["dual_live_to_internal_handoff_v1"]
    evidence_profile: Literal["dual_live_evidence_v1"]
    review_policy: Literal["security_egress_and_layer3_integrity_v1"]
    required_review_roles: tuple[
        Literal["security_egress"], Literal["layer3_integrity"]
    ]
    execution_order: Literal["nrc_then_sciencebase"]
    package_kinds: tuple[
        Literal["canonical_internal"],
        Literal["user_facing"],
        Literal["review_facing"],
    ]
    not_before: datetime
    expires_at: datetime
    non_authorities: tuple[str, ...]


class ConnectorGrantRequestRuleV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ordinal: int
    stage: Literal[
        "item_hydration",
        "artifact",
        "artifact_redirect",
        "exact_accession_api",
    ]
    method: Literal["GET"]
    scheme: Literal["https"]
    allowed_hosts: tuple[str, ...]
    port: Literal[443]
    path_rule_id: Literal[
        "sciencebase_item_exact_v1",
        "sciencebase_file_exact_v1",
        "nrc_get_document_exact_v1",
        "nrc_public_pdf_exact_v1",
    ]
    query_rule_id: Literal[
        "format_json_exact_v1",
        "sciencebase_exact_file_selector_v1",
        "none_v1",
    ]
    credential_audience: Literal["none", "nrc_aps_api_key"]
    max_response_bytes: int


class ConnectorEgressGrantV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.connector_egress_grant.v1"]
    grant_id: str
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    arming_nonce: UUID4
    max_armings: Literal[1]
    supersedes_grant_sha256: str | None = None
    issued_at: datetime
    expires_at: datetime
    operator_mode: Literal["local_loopback", "proxy_owner"]
    target: ScienceBaseFreshTargetV1 | NrcApsFreshTargetV1
    request_rules: tuple[ConnectorGrantRequestRuleV1, ...]
    max_physical_requests: int
    max_run_bytes: int
    max_single_send_detection_allowance_bytes: int
    request_timeout_seconds: int
    min_request_interval_ms: int
    non_authorities: tuple[str, ...]


class ConnectorEgressArmingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.connector_egress_arming.v1"]
    client_request_id: str
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    grant_sha256: str


class ConnectorGrantEvidenceRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    code_revision: str
    raw_grant_sha256: str
    canonical_grant_fingerprint: str
    grant_relative_path: str
    consumption_marker_sha256: str
    consumption_marker_relative_path: str


class ConnectorCampaignDefinitionRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: str
    campaign_fingerprint: str
    code_revision: str
    raw_definition_sha256: str
    definition_relative_path: str


class ConnectorCampaignLogCaptureRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    log_dir_relative_path: str
    manifest_relative_path: str
    seal_relative_path: str
    expected_stream_files: tuple[
        Literal["app.jsonl", "http.jsonl", "stdout.log", "stderr.log"], ...
    ]


class ConnectorGrantConsumptionMarkerV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.connector_grant_consumption.v1"]
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    raw_grant_sha256: str
    canonical_grant_fingerprint: str
    arming_nonce: UUID4
    connector_run_id: str
    max_armings: Literal[1]


class ConnectorCampaignEvidenceIndexV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.connector_campaign_evidence_index.v1"]
    revision: PositiveInt
    predecessor_index_sha256: str | None
    predecessor_index_relative_path: str | None
    campaigns: tuple[ConnectorCampaignDefinitionRefV1, ...]
    entries: tuple[ConnectorGrantEvidenceRefV1, ...]
    log_captures: tuple[ConnectorCampaignLogCaptureRefV1, ...]


class ConnectorCampaignLogFileV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relative_path: str
    stream_class: Literal["app", "http", "stdout", "stderr"]
    byte_count: int
    sha256: str


class ConnectorCampaignLogManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.connector_campaign_log_manifest.v1"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    runtime_started_at: datetime
    runtime_stopped_at: datetime
    files: tuple[ConnectorCampaignLogFileV1, ...]


class ConnectorCampaignLogSealV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: Literal["project6.connector_campaign_log_seal.v1"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    campaign_introduction_index_revision: PositiveInt
    campaign_introduction_index_sha256: str
    code_revision: str
    manifest_relative_path: str
    manifest_sha256: str
    file_set_hash: str
    # one entry per extant connector run, sorted: two in a completed dual
    # run, exactly one after an NRC-first stop (length 1 or 2, never 0 once
    # any connector run exists)
    connector_run_ids: tuple[str, ...]
    sealed_at: datetime
```

The grant validator must require these exact rule matrices:

| connector | ordinal/stage | host/path/query | audience | cap |
|---|---|---|---|---|
| ScienceBase | `1/item_hydration` | `www.sciencebase.gov`, raw path exactly `/catalog/item/63d1a3c6d34e06fef15006be`, raw query exactly `format=json` | none | 5 MiB |
| ScienceBase | `2/artifact` | `sciencebase.gov` or `www.sciencebase.gov`, raw path exactly `/catalog/file/get/63d1a3c6d34e06fef15006be`, raw query exactly `f=mcs2023-germa_salient.csv` | none | 64 MiB |
| ScienceBase | `3/artifact_redirect` | same exact host/path/query class; optional only after `301`, `302`, `303`, `307`, or `308` plus exactly one raw `Location` from ordinal 2 | none | 64 MiB |
| NRC APS | `1/exact_accession_api` | `adams-api.nrc.gov`, raw path exactly `/aps/api/search/ML17123A319`, no raw `?`/`#` delimiter | `nrc_aps_api_key` | 5 MiB |
| NRC APS | `2/artifact` | `www.nrc.gov`, raw path exactly `/docs/ML1712/ML17123A319.pdf`, no raw `?`/`#` delimiter | none | 64 MiB |

ScienceBase grants require ceiling `3`; NRC grants require ceiling `2`. Every
rule rejects any raw `@` in authority and any raw `#` delimiter, including an
empty fragment. Before `parse_qsl` or any other permissive
query helper can run, require the original `urlsplit` raw ASCII query component
to equal `f=mcs2023-germa_salient.csv` byte-for-byte for artifact/redirect and
`format=json` for hydration. The raw path must likewise equal its literal
ASCII rule before decoding; reject percent escapes, backslashes, dot segments,
control characters, or Unicode normalization in exact paths. Then decode the
one artifact field strictly as UTF-8 and require the ordered pair list to equal
`[("f", "mcs2023-germa_salient.csv")]`. Leading/trailing/repeated `&`, `;`,
blank fields, `+`, `%` encodings, extra `=`, duplicate/alternate/extra keys,
and non-UTF-8 fail. Persist only the URL hash and query class
`exact_single_f_expected_filename`, never the raw query. The NRC path is a
proposed owner-approved first-attempt inference from the current official
guide, not a live fact; a different returned URL stops before ordinal 2.
For every `none_v1` query rule, require the original URL to contain no `?` or
`#` delimiter at all; an empty query/fragment delimiter is not normalized away.

Every parent grant requires a canonical lowercase-hyphenated UUID4
`arming_nonce`, `max_armings=1`, and an exact half-open authority interval:
`issued_at <= authorization_time < expires_at`. Derived URL armings are
subordinate policy snapshots inside that one parent run and do not consume
another parent-arming slot.

`max_run_bytes`, `request_timeout_seconds`, and `min_request_interval_ms` are
enforced budgets, not annotations. `max_run_bytes` bounds the run aggregate of
counted bytes across every physical send — per send, the canonical
status/header bytes plus the body bytes delivered by the wrapped urllib3 read
path before Requests-level content decoding, including redirect, partial,
failed, and oversized responses, exactly as Task 3's one-send transport
defines them. It is an application-delivered ceiling with header-block-granular
and 64 KiB chunk-granular crossing detection, not a network-wire octet count:
original status/header octets, chunked transfer framing, TLS records, and bytes
buffered below the Requests-adapter seam are outside the counted entity.
SINGLE-SEND DETECTION ALLOWANCE = 6,684,672 bytes (100 x 65,536 header-line
bytes + one 65,536-byte status line + one 65,536-byte read chunk), derived from
the pinned interpreter's `http.client` header-admission limits
(`_MAXLINE=65536`, `_MAXHEADERS=100`); the operative mechanism is the fail-closed
equality assertion below — parser-limit drift stops the run regardless of
interpreter version — and
the grant-bound `max_single_send_detection_allowance_bytes` field must equal
this computed constant — asserted fail-closed at reservation and transport
construction, so interpreter drift is a hard stop. `max_run_bytes` is therefore
a ceiling plus that one disclosed allowance, not a hard maximum: the counted
aggregate may exceed it by at most one SINGLE-SEND DETECTION ALLOWANCE before
terminal detection, and any larger excess is a counter defect.
`request_timeout_seconds` is the absolute per-send deadline measured on the
process monotonic clock from immediately before the transport call to the last
body byte; the derived Requests connect/read socket timeouts are each clamped
to the remaining monotonic budget and never extend it. `min_request_interval_ms`
is the minimum monotonic-clock spacing between consecutive `send_started_at`
captures inside the same actual-destination-host rate bucket. No duration, deadline, budget, or
rate decision reads the wall clock, so a wall-clock rollback or jump changes
no duration, deadline, budget, or rate decision. The absolute authority-window
checks are the stated exception: `campaign.not_before <= now < campaign.expires_at`
and `grant.issued_at <= now < grant.expires_at` read the injected UTC clock, so
wall-clock trust for window membership is an explicit, disclosed limitation of
this MVP — not covered by the monotonic guarantees above.

Canonical campaign-definition bytes are UTF-8 JSON from the validated model
with UTC timestamps normalized to exactly six fractional digits plus `Z`, UUIDs
lowercase-hyphenated, keys sorted, no insignificant whitespace, and tuple order
preserved. The definition contains no fingerprint and no grant digest.
`campaign_fingerprint` is the lowercase SHA-256 of those canonical bytes; the
separately configured raw-definition SHA-256 binds the exact owner file. Both
connector grants must match the rederived campaign ID, fingerprint, revision,
target, and half-open subwindow. The definition is an intersection/correlation
control only: it can reject a grant but can never add a host, method, path,
credential audience, request, byte, or time authority absent from that
connector's exact grant.

Require canonical non-authority codes for other connector/target, search,
automatic retry, resume/recurrence, alternate selection, credential fallback,
post-expiry send, continuation after code change, external delivery, and
production/support promotion. NRC additionally requires
`redirect_follow_not_authorized`; ScienceBase permits only its exact ordinal-3
rule. Both require `additional_parent_arming_not_authorized` and
`unused_budget_transfer_not_authorized`.

### Step 2: Run the tests and confirm the expected failure

```powershell
Push-Location backend
python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py -q
Pop-Location
```

Expected: collection or import fails because the models and authorization
service do not exist.

### Step 3: Implement configuration and schema validation

Add:

```python
connector_live_egress_enabled: bool = Field(
    default=False,
    alias="CONNECTOR_LIVE_EGRESS_ENABLED",
)
connector_egress_arming_max_ttl_seconds: int = Field(
    default=86_400,
    alias="CONNECTOR_EGRESS_ARMING_MAX_TTL_SECONDS",
)
connector_live_egress_exclusive_proof_mode: bool = Field(
    default=True,
    alias="CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
)
connector_campaign_definition_path: Path | None = Field(
    default=None,
    alias="CONNECTOR_CAMPAIGN_DEFINITION_PATH",
)
connector_campaign_definition_sha256: str | None = Field(
    default=None,
    alias="CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
)
connector_sciencebase_grant_path: Path | None = Field(
    default=None,
    alias="CONNECTOR_SCIENCEBASE_GRANT_PATH",
)
connector_sciencebase_grant_sha256: str | None = Field(
    default=None,
    alias="CONNECTOR_SCIENCEBASE_GRANT_SHA256",
)
connector_nrc_aps_grant_path: Path | None = Field(
    default=None,
    alias="CONNECTOR_NRC_APS_GRANT_PATH",
)
connector_nrc_aps_grant_sha256: str | None = Field(
    default=None,
    alias="CONNECTOR_NRC_APS_GRANT_SHA256",
)
connector_campaign_evidence_root: Path | None = Field(
    default=None,
    alias="CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
)
connector_campaign_evidence_index_path: Path | None = Field(
    default=None,
    alias="CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
)
connector_campaign_evidence_index_sha256: str | None = Field(
    default=None,
    alias="CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
)
```

The Pydantic models must normalize but never silently widen:

- methods to uppercase;
- hosts to lowercase ASCII without a trailing dot;
- default port to explicit `443`;
- SHA-256 to lowercase 64-hex;
- arming nonce to canonical lowercase-hyphenated UUID4 text;
- TTL to server time plus the configured maximum;
- authority time to the half-open interval
  `issued_at <= authorization_time < expires_at`;
- parent arming ceiling exactly `1`;
- ScienceBase physical ceiling exactly `3`;
- NRC physical ceiling exactly `2`.

Campaign-definition and grant paths must be absolute regular files outside the
repository, runtime DB, artifact root, and web-served roots; reject
symlinks/reparse points and files over 64 KiB. Read bytes once, verify the
configured raw-byte SHA-256, strict UTF-8/JSON parse with duplicate-member
rejection, and separately compute the stable canonical definition/grant
fingerprint. Missing configuration is harmless while live egress is off and
fatal to the matching arming/execute path when it is on.

The campaign-evidence index head is a distinct, protected, configured server
input. Every revision is immutable canonical JSON stored at
`indexes/<its_raw_sha256>.json` below the protected evidence root; the
configured path/digest identify the current head without placing its own digest
inside its bytes. Revision 1 has `revision=1`, both predecessor fields null, and
exactly one complete campaign slice.
Every later revision increments by exactly one and names
`indexes/<predecessor_sha256>.json` plus that predecessor's digest. The loader
must traverse and rehash the complete chain before accepting the head, enumerate
the protected `indexes/` directory, and require the configured object to be the
unique maximal head of one linear chain. Reject rollback to an ancestor, a
fork, gap, orphan, malformed/unindexed object, alternate filename, or revision
collision. A later revision must contain every predecessor definition, grant,
marker, and log-capture reference byte-for-byte and must add exactly one
structurally complete, exact-reference, disjoint campaign slice. It may never
delete, rewrite, relabel, or alias a prior slice. Create every revision with
no-overwrite semantics, verify the strict-superset relation, and rotate the
configured head only after the new chain passes.

Within each revision, the index first maps
`(campaign_id, campaign_fingerprint, code_revision,
raw_definition_sha256)` to one content-addressed definition path, then maps
`(campaign_id, campaign_fingerprint, campaign_definition_sha256, connector_key,
raw_grant_sha256, canonical_grant_fingerprint)` to one content-addressed grant
path relative to
the configured evidence root. The root and index must satisfy the same
outside-repo/runtime/artifact/web-root,
regular-file, no-symlink/reparse rules; reject absolute entry paths, `..`,
alternate data streams, case-colliding entries, duplicate tuple keys, and
archive bytes over 64 KiB. Require each definition path to equal
`campaigns/<raw_definition_sha256>.json`, each grant path to equal
`grants/<raw_grant_sha256>.json`, and each marker path to equal
`consumed/<raw_grant_sha256>.json` exactly after separator normalization.
Marker bytes are deterministic canonical JSON over
`ConnectorGrantConsumptionMarkerV1`; the index binds their expected SHA-256
before arming. Verify the configured index and archived definition/grant hashes
before arming; a marker already present means the grant was consumed. After
creation, idempotent lookup and historical validation require the exact indexed
marker bytes/hash. Neither the public arming request nor the validator accepts
an index, index revision, head digest, or archive path.

For each selected campaign, the index must contain exactly one definition ref,
exactly two grant entries whose connector set equals
`{sciencebase_mcs, nrc_adams_aps}`, and exactly one log-capture reference.
Reject an orphan entry/reference, duplicate definition/connector, second log
reference, one campaign ID paired with multiple fingerprints, one fingerprint
paired with multiple IDs, or any selected slice with another cardinality. One
selected campaign union is exactly one definition, two entries, and one
capture; the two Task 12 selected campaigns are exactly two definitions, four
entries, and two captures. The global index may retain additional structurally
complete, exact-reference, disjoint historical/failed campaign slices; their
technical outcomes may remain failed, and every slice must stay unrelabelled.
The append-only revision chain, not selected-union cardinality alone, enforces
that preservation.

For each indexed campaign, the same protected index fixes exactly one log
directory, manifest path, and separate post-run seal path:
`logs/<campaign_fingerprint>/` and
`logs/<campaign_fingerprint>/manifest.json`, plus
`log-seals/<campaign_fingerprint>.json`. It requires exactly
`app.jsonl`, `http.jsonl`, `stdout.log`, and `stderr.log` plus that one manifest,
with no caller path, duplicate stream name, symlink/reparse point, alternate
data stream, or extra/unclassified file. The directory must not exist before
owner preflight. The campaign launcher creates
it with exclusive permissions, captures the declared runtime-owned log surface,
stops and flushes the runtime, then atomically writes the strict manifest with
file byte counts/hashes. It then computes the manifest SHA-256 and the canonical
ordered file-set hash, atomically creates the strict no-overwrite seal at the
pre-indexed separate path, and in one DB transaction appends one deterministic
`campaign_log_capture_sealed` event to each extant connector run. Seal-event
cardinality is conditional on run existence: exactly one seal event per
connector run that exists — two in a completed dual run, exactly one after an
NRC-first stop, where the ScienceBase run correctly does not exist and no run
is ever created merely to receive an event. The seal and every extant-run
event payload bind the same campaign-introduction evidence-index
revision/digest, seal
SHA-256, manifest SHA-256, file-set hash, raw campaign-definition digest,
campaign/revision, and sorted extant-run set. The preflight evidence-index revision
is never rewritten; a later head can only add a complete disjoint slice while
retaining it through the verified predecessor chain.

The evaluator resolves these paths only through server configuration plus the
protected index and requires exact parity among the four files, manifest, seal,
and the independently queried DB events of every extant connector run; it
never requires a seal event for a run whose creation was correctly prevented,
and a seal naming a nonexistent run fails. A log/manifest rewrite, seal rewrite,
missing/duplicate event, or cross-run disagreement fails. This protected
no-overwrite filesystem plus DB cross-domain anchor is adequate only for the
local experiment; it is not a signature, WORM store, or cryptographic
nonrepudiation. OS/provider logs outside the launched process remain an explicit
production-promotion non-claim.

Do not change `NrcAdamsApsConnectorRunIn(extra="allow")` in this task. The new
campaign envelope is the strict compatibility boundary.

### Step 4: Implement connector-specific owner authorization

Implement:

```text
resolve_current_dual_live_campaign_definition(
    *,
    expected_campaign_id: str,
    expected_campaign_fingerprint: str,
    code_revision: str,
    now: datetime,
) -> VerifiedDualLiveCampaignDefinition

resolve_current_connector_egress_grant(
    *,
    verified_campaign: VerifiedDualLiveCampaignDefinition,
    connector_key: str,
    expected_grant_sha256: str,
    campaign_id: str,
    campaign_fingerprint: str,
    code_revision: str,
    now: datetime,
) -> VerifiedConnectorGrant

resolve_historical_connector_grant_evidence(
    *,
    connector_key: str,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    expected_grant_sha256: str,
) -> VerifiedHistoricalGrantEvidence

authorize_connector_egress_owner(
    request: Request,
    *,
    verified_grant: VerifiedConnectorGrant,
    access: Literal["write"],
) -> ConnectorEgressAuthorizationReceipt
```

The current campaign resolver reloads/rederives the protected definition and
traverses the unique-maximal evidence-index chain at arming and every
physical-send reservation. It resolves the earliest revision containing that
definition's exact complete campaign slice. Before marker creation, this
introduction revision/digest must equal the configured unique-maximal head;
therefore a preserved ancestor slice is historical-only even if its grant was
never consumed. Advancing the head intentionally abandons any unused ancestor
grant; recovery requires a new campaign definition/revision and new grants
rather than rebinding stale authority. The current connector resolver remains
the only egress-authority boundary: it must reload and rehash the currently
configured connector grant, intersect it with the verified definition, require
the current head revision/digest to equal the immutable introduction
revision/digest bound by the arming and contain that exact complete campaign
slice, and require both current half-open windows
(`not_before <= now < campaign.expires_at` and
`grant.issued_at <= now < grant.expires_at`), reject any
request/definition/grant/revision/target/non-authority mismatch, and materialize
the canonical egress envelope exclusively from the verified grant. A grant
window must be wholly inside the definition window. The definition can deny but
never authorize or widen a send.

The historical resolver is read-only evidence plumbing, not authority. It
selects the exact definition and grant only after traversing the configured
unique-maximal index chain to the revision bound by that campaign's immutable
arming/seal/events, returns distinct types that the arming/execute/reservation/
transport APIs cannot accept, and does not require either old file to remain
current or unexpired today. It verifies exact index/archive/canonical digests,
schema, campaign, connector, target, rules, and code revision. Receipt/evaluator
logic must separately prove that every recorded reservation and physical-send
timestamp fell inside both original half-open definition and grant windows. A
timestamp equal to either `expires_at` is expired in current and historical
paths. It must never call transport, arm a run, or revive unused budget.

The caller wrapper must:

1. call `route_level_operator_authorization_required` for caller posture only;
2. require the default-off and exclusive-proof flags;
3. when `AUTH_OWNER=none`, require `DEPLOYMENT_MODE=local`,
   `TRUSTED_PROXY_MODE=false`, a direct loopback peer, no forwarded-identity
   headers, a verified campaign definition, and a verified grant;
4. when `AUTH_OWNER=proxy`, require trusted proxy mode,
   `LAYER3_ROUTE_AUTHORIZATION_MODE=role_enforcing`, and derived role `owner`;
5. reject proxy identity-presence mode;
6. return principal/workspace hashes, never raw forwarded identity;
7. never treat `AUTH_OWNER`, role, flag, request fields, campaign definition,
   fingerprint, or a grant ID/reference as grant authority;
8. use connector-specific error codes and schema IDs.

### Step 5: Run focused tests and static checks

```powershell
Push-Location backend
python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py -q
Pop-Location
git diff --check
```

Expected: all focused tests pass; no whitespace errors.

### Step 6: Commit

```powershell
git add backend/app/schemas/api.py backend/app/core/config.py backend/.env.example backend/app/services/connector_egress_authorization.py backend/tests/test_egress_auth.py backend/tests/test_egress_schema.py
git commit -m "feat(connectors): define strict live egress authority"
```

## Task 2: Persist immutable armings and separate arm from execute

**Files:**

- Create: `backend/app/services/connector_egress_arming.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/schemas/api.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_egress_arming.py`
- Test: `backend/tests/test_arming_api.py`

### Step 1: Write failing service tests

Prove:

- stable canonical JSON produces the same fingerprint independent of input-key
  order;
- changing any grant, target, limit, expiry, revision, principal, or campaign
  field changes the fingerprint;
- changing the campaign-introduction evidence-index revision/digest changes the
  arming fingerprint, and a configured head that is not the unique maximal
  linear successor is rejected before marker creation;
- arming creates one `ConnectorRun(status="armed")`, one
  `ConnectorRunSubmission`, one `ConnectorPolicySnapshot`, and one
  `egress_arming_created` event;
- the grant's deterministic parent-run ID is UUIDv5 over connector, campaign,
  raw grant digest, and owner nonce;
- arming atomically creates one no-overwrite deterministic consumption marker
  before the DB transaction; marker-create or DB failure sends/enqueues
  nothing, and a marker-only crash consumes the grant;
- the creation transaction sends and enqueues nothing;
- same idempotency key plus same fingerprint returns the original arming;
- same idempotency key plus different bytes returns `409`;
- a different client key against the same grant returns
  `409 connector_grant_already_consumed` for `armed`, `pending`, `running`,
  `completed`, `failed`, `cancelled`, stuck, and marker-only states;
- concurrent same-grant creation under different client keys produces at most
  one arming and one consumption marker;
- rotating the grant away and back, or pointing it at another isolated DB
  under the same protected evidence root, cannot create another parent arming;
- a fresh grant that supersedes a consumed digest is rejected under the same
  campaign even when the visible runtime DB has zero reservations; it is
  accepted only under a new campaign definition/ID/fingerprint after the
  protected index proves the prior digest and consumption marker;
- revision 1 introduces unconsumed campaign A, revision 2 adds campaign B, and
  later configuring A's definition/grants is rejected because A's introduction
  revision is no longer the current head; rejection occurs before marker, DB
  run, submission, policy, event, enqueue, or network activity;
- derived artifact armings do not consume another parent-arming slot;
- when the verified campaign definition binds NRC-first execution order,
  creating the ScienceBase parent arming is rejected before its
  consumption-marker create-new operation unless
  `evaluate_nrc_acquisition_success` passes every clause of the NRC
  acquisition-success predicate defined once in Step 3; adversarial tests
  falsify each clause individually — an NRC run that is absent, `armed`,
  `pending`, `running`, `failed`, `cancelled`, or terminally ambiguous; a
  terminal `completed` status whose transition was not committed by
  `finalize_strict_run`; a duplicate or competing terminal event; later
  failure or cancellation evidence; an unexpired execution lease; a
  rederived ledger with a missing completion, missing/extra/reordered
  ordinal, `spent_unknown` entry, or ceiling breach; a missing, extra,
  unparseable, or field-disagreeing `http.jsonl` counter record; a
  non-`200`, incomplete, or over-limit artifact completion; and a
  blob-rehash raw SHA-256 (rehashed from the content-addressed NRC target
  bytes) that mismatches the rederived ledger or counter hashes — and each falsification leaves the ScienceBase marker
  uncreated, its grant unconsumed, and zero marker, DB row, or event
  mutation; a stored `ledger_terminal_hash` or `proof_class` column that
  disagrees with the rederived evidence is itself a rejection, and the
  accepted ScienceBase envelope binds the server-derived NRC parent-run ID
  and the rederived `ledger_terminal_hash`, never caller-supplied or
  stored-column values;
- caller target/host/path/budget/expiry fields are rejected and cannot alter the
  server-materialized arming;
- changing or removing the configured campaign definition or grant after arming
  blocks execute;
- changing the active evidence-index head during a campaign blocks execute and
  reservation until a separately authorized new campaign is armed against the
  new head;
- expired or fingerprint-mismatched arming cannot execute;
- two concurrent execute attempts produce one successful
  `armed -> pending` compare-and-swap; exactly one caller observes
  `claimed_now=true` and enqueues, and the non-winning caller receives the
  same run with `claimed_now=false` and enqueues nothing;
- lease acquisition on the claimed run is the only `pending -> running`
  transition; no strict path sets `running` from any other state;
- generic resume and generic submit cannot execute a reserved proof envelope;
- generic cancel is rejected for a strict run in every state with `409` and
  zero mutation of `status`, `cancellation_requested_at`, or lease fields,
  because strict cancellation semantics are not owner-specified in this MVP;
  `cancelled` remains a declared terminal state that no strict path reaches
  in the first campaign, and any `cancelling` or cancellation-marker evidence
  on a strict run fails evaluation;
- strict-lane target/provenance `sciencebase_download_uri` and alias
  `alias_url` scalar columns are null; no exact derived artifact URL or raw
  query appears in any other scalar/text/JSON DB column, GET serialization,
  metadata snapshot, intake record, event, report, generated artifact, or
  captured log;
- enabling exclusive proof mode blocks generic ScienceBase/NRC submit and
  resume routes without changing their behavior when the proof flag is off.

### Step 2: Run tests and confirm failure

```powershell
Push-Location backend
python -m pytest tests/test_egress_arming.py tests/test_arming_api.py -q
Pop-Location
```

Expected: import failure for `connector_egress_arming`.

### Step 3: Implement canonical arming persistence

Expose:

```text
canonical_arming_payload(payload: Mapping[str, Any]) -> dict[str, Any]

compute_arming_fingerprint(payload: Mapping[str, Any]) -> str

compute_parent_arming_id(
    *,
    connector_key: str,
    campaign_id: str,
    grant_sha256: str,
    arming_nonce: UUID,
) -> str

create_connector_egress_arming(
    db: Session,
    *,
    payload: ConnectorEgressArmingIn,
    verified_grant: VerifiedConnectorGrant,
    operator_receipt: Mapping[str, Any],
    code_revision: str,
) -> tuple[ConnectorRun, bool]

evaluate_nrc_acquisition_success(
    db: Session,
    *,
    verified_definition: VerifiedDualLiveCampaignDefinition,
) -> NrcAcquisitionSuccessEvidence

claim_connector_egress_arming(
    db: Session,
    *,
    connector_run_id: str,
    execution_idempotency_key: str,
    now: datetime,
) -> tuple[ConnectorRun, bool]

finalize_strict_run(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    terminal_status: Literal["completed", "failed", "cancelled"],
    outcome_class: str,
    now: datetime,
) -> None

commit_derived_url_arming(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    ordinal: int,
    stage: str,
    normalized_url: str,
    verified_grant: VerifiedConnectorGrant,
) -> DerivedEgressTarget
```

Fingerprint stable canonical JSON with sorted keys, UTF-8, compact separators,
and no floating-point fields. Exclude only `arming_fingerprint` itself.

Materialize the envelope from `verified_grant`, never from overlapping public
request fields. Store the logically immutable envelope under
`request_config_json["connector_egress_arming"]`; store only its fingerprint in
ordinary response projections. Store policy under
`ConnectorPolicySnapshot.policy_json`. Derive `connector_run_id` as
`uuid5(NAMESPACE_URL, "project6:parent-arming:<connector>:<campaign>:<grant_sha256>:<arming_nonce>")`.
Create deterministic UUIDv5 event IDs from that run ID, event kind, and ordinal.

The envelope binds raw campaign-definition SHA-256, canonical campaign
fingerprint, raw grant SHA-256, canonical grant fingerprint,
campaign-introduction evidence-index revision/digest, exact code revision,
`arming_nonce`,
`max_armings=1`, optional superseded-grant digest, every closed request rule,
and authorization receipt. When the definition binds NRC-first execution
order, the ScienceBase envelope additionally binds the predecessor NRC
parent-run ID and its `ledger_terminal_hash`, both server-derived — and the
bound hash is the one `evaluate_nrc_acquisition_success` rederives in the
same creation call, never a stored column value.

`evaluate_nrc_acquisition_success` is the single authoritative definition of
the NRC acquisition-success predicate. Every other statement of the
predicate in this plan and in the campaign record is a reference to this
definition; no wrapper, caller, or execution-order step may substitute a
weaker check. The function takes no caller-supplied run ID, path, or hash:
it server-loads the NRC grant bytes by configured digest, derives the
deterministic NRC parent-run ID from them, resolves the campaign's capture
path through the protected evidence index, and rederives every clause from
authoritative records — never trusting `proof_class`, a stored
`ledger_terminal_hash`, or any projection column. The predicate holds only
when all of the following pass:

1. the deterministic NRC parent run exists in strict terminal `completed`
   whose one terminal transition was committed by `finalize_strict_run`:
   exactly one valid deterministic `egress_run_terminal` event with status
   `completed` exists, and the event stream carries no other terminal,
   failure, or cancellation evidence;
2. no unexpired execution lease survives on the run;
3. the canonical terminal request ledger, rederived in the same call via
   `derive_terminal_request_ledger`, shows every reservation matched by
   exactly one completion (reservation/completion parity) within the NRC
   grant ceiling and contains no `spent_unknown` entry;
4. the transport-counter records, strictly parsed from the manifest-bound
   `http.jsonl` capture at the index-bound deterministic path (necessarily
   unsealed at this mid-campaign point; Task 8's evaluator later re-verifies
   the sealed capture), reconcile one-to-one with that rederived ledger — no
   missing, extra, or unparseable line, with agreement on ordinal, stage,
   request fingerprint, response status, decoded body count, and
   decoded-body SHA-256; the counting adapter flushes each record before the
   matching completion event commits, so a terminal run whose records are
   absent fails this clause rather than racing it;
5. the admitted artifact completion is a complete `200` within its byte
   limits, and the raw SHA-256 REHASHED from the content-addressed blob
   recorded for the NRC target (the bytes behind
   `ConnectorRunTarget.downloaded_sha256`, rehashed at evaluation time —
   never a stored column read) equals both the rederived ledger's
   artifact-completion `body_sha256` and the matching counter record's
   decoded-body SHA-256. [S3 delta 2026-07-30, owner-delegated Option B:
   the referent was formerly "recorded on the canonical connector-target
   receipt", which cannot exist at this Phase-A gate — the canonical origin
   receipt (invariant 12) mints in Phase B; the blob rehash is the stronger,
   phase-consistent third leg of the same triangulation.]

It returns `NrcAcquisitionSuccessEvidence` — the rederived
`ledger_terminal_hash`, blob-rehash raw SHA-256, and counter-reconciliation
summary — and `create_connector_egress_arming` invokes it inside the same
ScienceBase creation call, before the consumption-marker create-new
operation, rejecting on any failed clause with zero marker, DB row, or
event mutation. Because every creation path —
`POST /api/v1/connectors/egress-armings` included — reaches marker creation
only through this service call, no caller path can consume the ScienceBase
grant on a weaker check. `ConnectorEgressArmingIn`
carries no sequencing field; a caller cannot assert or waive the predecessor
check.
The deterministic `egress_arming_created` event binds the arming fingerprint
and the same campaign-introduction evidence-index revision/digest.
Also store the arming fingerprint in
`ConnectorRun.request_fingerprint` and the grant expiry in the creation
`ConnectorRunSubmission.expires_at`. Namespace submission keys as
`egress-arm:<client key>` and
`egress-execute:<execution key>` so creation and execution idempotency cannot
collide. Reuse of an execution key for another run or fingerprint is `409`.

Before opening the DB creation transaction, canonicalize the expected
`ConnectorGrantConsumptionMarkerV1` already bound by the protected evidence
index and create `consumed/<grant_sha256>.json` with an atomic create-new
operation, never overwrite/rename/delete. Flush the file before DB work. If the
marker already exists, verify its exact bytes and deterministic run ID, then:

- return the existing DB arming only for the same creation idempotency key and
  same fingerprint;
- otherwise return `409 connector_grant_already_consumed`, regardless of run
  status;
- if the marker exists but the DB arming does not, return
  `409 connector_grant_consumed_without_arming`.

The marker is the cross-DB one-use fence; deterministic run ID/primary-key and
submission checks are independent DB fences. A crash after marker creation but
before DB commit deliberately sacrifices availability rather than restoring
owner budget. Recovery requires a fresh owner grant with a new digest/nonce
and `supersedes_grant_sha256` naming the consumed digest, plus a new campaign
ID/fingerprint. Same-campaign recovery is always rejected: a separate isolated
DB can see the marker but cannot prove an absence of old-run reservations.
When `supersedes_grant_sha256` is present, resolve that prior digest only
through the protected evidence index, require the same connector and its exact
consumption marker, and require different campaign ID/fingerprint, grant
digest, and nonce. Unused budget never transfers implicitly.

For both connectors, keep the parent request configuration immutable.
`commit_derived_url_arming` must normalize and validate the URL against the
verified rule, reject userinfo/fragment and any non-admitted query, then persist
only URL SHA-256 plus safe scheme/host/port/path/query class in a new
`ConnectorPolicySnapshot` and deterministic
`derived_egress_arming_created` event. The exact URL remains only inside the
returned in-memory object. It must be absent even from raw DB inspection. A
crash loses it and makes the run non-resumable.

Claim by reloading and rehashing the configured campaign definition and grant,
rederiving the campaign fingerprint, comparing definition/grant digests, both
half-open windows, and every frozen arming binding, creating/reusing the
namespaced execute submission, then performing one SQL update constrained by
primary key,
`status == "armed"`, and `request_fingerprint == expected_fingerprint`.
Recheck the creation-submission expiry and verified grant expiry immediately
before commit; `now >= expires_at` is expired. Roll back if either elapsed.
Commit before enqueue. The claim returns `(run, claimed_now)`: the winning
compare-and-swap returns `claimed_now=true`; an idempotent replay of the same
execution key against the already-claimed run returns the same run with
`claimed_now=false`. Enqueue the executor exactly and only when
`claimed_now=true`, so a replayed execute call can never schedule a second
executor. `pending` means claimed-and-not-yet-leased; the executor's existing
lease acquisition (which sets the lease fields and moves the run to
`running`) is the only `pending -> running` transition, and every physical
reservation then requires `running` plus the exact active lease token.
A crash after claim but before enqueue, or after enqueue but before lease
acquisition, leaves a safely stuck pending run; it
does not permit generic resume or reuse of the consumed grant. Recovery
follows the fresh explicitly superseding-grant plus new-campaign rule above.

`finalize_strict_run` is the only exit from `running`. It performs one SQL
update constrained by primary key, `status == "running"`, and the exact
active lease token; sets exactly one of `completed`, `failed`, or `cancelled`
plus `completed_at` from the injected UTC clock; clears or expires the
execution lease in the same transaction so no unexpired lease survives the
terminal transition; and inserts one deterministic UUIDv5
`egress_run_terminal` event binding terminal status, outcome class, arming
fingerprint, and the campaign-introduction evidence-index revision/digest.
The deterministic event ID is the second-finalize fence: a repeated or
competing finalize fails on event uniqueness and mutates nothing. Generic
target-count finalization, `completed_with_errors`, generic resume, and the
generic executor failure relabel are all unreachable for a strict run: strict
branches return before generic finalize code, and the generic exception
handler, on a strict envelope, may only call
`finalize_strict_run(..., terminal_status="failed")` while the run is still
`running` under the current lease and no strict terminal event exists.

### Step 4: Add the three API routes

Implement:

```text
POST /api/v1/connectors/egress-armings
GET  /api/v1/connectors/egress-armings/{connector_run_id}
POST /api/v1/connectors/egress-armings/{connector_run_id}/execute
```

The execute body contains only:

```python
class ConnectorEgressExecuteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_idempotency_key: str
    arming_fingerprint: str
```

Add the two POST paths to `backend/main.py` static pre-body authorization
classification. Both POST routes independently resolve the server-configured
grant and caller posture; execute uses the persisted connector/grant digest,
not a caller-selected grant. Reuse `_connector_executor` only after the claim
transaction commits and only when the claim returned `claimed_now=true`; a
`claimed_now=false` replay returns the current run projection and enqueues
nothing.

### Step 5: Run focused and route-auth tests

```powershell
Push-Location backend
python -m pytest tests/test_egress_arming.py tests/test_arming_api.py tests/test_sec_xbrl_in_app_auth_policy_validation.py -q
Pop-Location
git diff --check
```

### Step 6: Commit

```powershell
git add backend/app/services/connector_egress_arming.py backend/app/api/router.py backend/app/schemas/api.py backend/main.py backend/tests/test_egress_arming.py backend/tests/test_arming_api.py
git commit -m "feat(connectors): separate live arming from execution"
```

## Task 3: Add the durable reservation ledger and one-send transport

**Files:**

- Create: `backend/app/services/connector_egress_transport.py`
- Test: `backend/tests/test_egress_transport.py`
- Test: `backend/tests/test_egress_crash.py`

### Step 1: Write failing ledger and transport tests

The test matrix must include:

- reservation commits before the injected send callable observes execution;
- deterministic duplicate reservation is treated as already spent;
- reservation commit failure calls the transport zero times;
- process failure after send and before completion leaves spent/unknown;
- unknown reservation cannot be retried;
- run not `running`, stale/missing lease token, arming/grant/campaign mismatch,
  changed definition/grant bytes, changed/non-maximal evidence-index head,
  expired definition/grant, wrong stage,
  out-of-order ordinal,
  over-ceiling ordinal, or absent derived arming stops before send;
- definition or grant expiry between reservation commit and transport start
  records
  `reserved_not_sent`, spends the ordinal, and sends nothing;
- exact boundary tests prove campaign `not_before` and grant `issued_at` are
  admitted, while equality with either `expires_at` is not, for arming, claim,
  reservation, send start, and historical validation;
- an unresolved earlier reservation blocks every later ordinal;
- redirects are returned, not followed;
- transport-level retry count is zero;
- the optional ScienceBase redirect consumes ordinal 3; NRC has no
  redirect-follow ordinal;
- actual destination host selects the rate bucket, and a send attempted before
  `min_request_interval_ms` of monotonic time has elapsed since the previous
  send start in that bucket does not reach the transport;
- timeout, `429`, `5xx`, partial, oversized, empty, and wrong media remain
  one physical send each, and every counted byte delivered before the failure
  still counts against `max_run_bytes`;
- the counted-byte aggregate across ordinals is enforced against
  `max_run_bytes`: an exhausted remaining aggregate budget — a remainder of
  zero or less — stops before reservation as budget exhaustion; a crossing
  found at a chunk-boundary check is terminal oversized with every delivered
  byte counted and spent; the counted aggregate exceeds `max_run_bytes` by at
  most one SINGLE-SEND DETECTION ALLOWANCE; any larger excess is a counter
  defect; a run whose counted aggregate crossed the ceiling is never
  `fresh_live`-eligible;
- the absolute monotonic send deadline aborts a slow-dripping response that
  never violates the per-read socket timeout, as one spent send;
- a wall-clock rollback or jump between sends changes no budget, deadline, or
  rate decision;
- a final prepared request whose adapter-seam fingerprint differs from the
  reserved request fingerprint sends nothing;
- `Accept-Encoding: identity` is sent, and a response declaring any other
  `Content-Encoding` stops without entering the admitted-artifact path;
- canonical status/header bytes are counted in full and recorded per send in
  the counter record; there is no per-send header threshold and no
  header-rejection path;
- a response with 99 individually legal header fields plus the terminating
  blank line (the pinned parser rejects a 101st entry, so 99 fields is the
  executable maximum) whose aggregate
  canonical serialization far exceeds 32,768 bytes, delivered under a nearly
  exhausted remaining budget, counts every header byte, terminates with the
  correct terminal oversized or budget-exhaustion classification, is never
  `fresh_live`, leaves the aggregate excess at or below the SINGLE-SEND
  DETECTION ALLOWANCE, and proves no header-threshold rejection path exists;
- aggregate-crossing fixtures: H > R with B = 0 (header alone crosses,
  terminal oversized at the post-serialization check); H < R with
  H + B > R while B stays within min(stage cap, R) (aggregate check fires at
  a chunk boundary or EOF though the body predicate never does); H + B = R
  exact boundary (no crossing, send completes); a body-stage crossing without
  aggregate crossing (body predicate fires, aggregate does not); a grant
  whose max_single_send_detection_allowance_bytes mismatches the computed
  constant (fail-closed stop before any send); and a simulated
  _MAXLINE/_MAXHEADERS drift (equality assertion trips, hard stop pre-send);
- exactly one secret-free counter record per physical send appears in the
  manifest-bound `http.jsonl` capture — including exactly one record with a
  null `response_status` and a closed `error_class` for a send that dies
  before any HTTP status exists — and a missing, extra, or mismatched
  record against the derived terminal ledger yields `INDETERMINATE`, never
  success;
- ambient proxy variables and cookie jars are ignored, TLS verification remains
  enabled, and a non-public DNS answer stops before reservation/send;
- event/report payloads contain no raw URL, query, `Location`, authorization
  header, subscription key, request body, or response body;
- two workers cannot reserve the same ordinal and both send;
- the terminal-ledger projection/hash is stable and rejects missing, extra,
  reordered, duplicated, or mutated events and response/body-hash mismatch.

### Step 2: Run tests and confirm failure

```powershell
Push-Location backend
python -m pytest tests/test_egress_transport.py tests/test_egress_crash.py -q
Pop-Location
```

### Step 3: Implement the reservation API

Expose:

```text
reserve_physical_request(
    *,
    connector_run_id: str,
    lease_token: str,
    arming_fingerprint: str,
    ordinal: int,
    stage: str,
    request: FrozenPhysicalRequest,
    expected_derived_arming_hash: str | None,
    now: datetime,
) -> PhysicalRequestReservation

complete_physical_request(
    *,
    reservation: PhysicalRequestReservation,
    outcome: PhysicalRequestOutcome,
) -> None

derive_terminal_request_ledger(
    db: Session,
    *,
    connector_run_id: str,
) -> VerifiedTerminalRequestLedger
```

`FrozenPhysicalRequest` carries the exact ephemeral URL and headers only in
memory. `reserve_physical_request` opens a short-lived independent SQLAlchemy
session and must atomically:

1. reload and rehash the configured campaign definition and connector grant,
   traverse the protected evidence-index chain, and require its configured
   revision to remain both the unique maximal head and the earliest
   complete-slice introduction revision bound by the arming;
2. lock/load the run and verify `running`, strict marker, the exact active
   lease token,
   arming/definition/grant/campaign fingerprints, evidence-index
   revision/digest, code revision, feature flags,
   `campaign.not_before <= now < campaign.expires_at`, and
   `grant.issued_at <= now < grant.expires_at` plus an unexpired lease;
3. validate the exact connector stage/ordinal map and frozen ceiling;
4. prove all prior ordinals have one terminal completion and no later ordinal
   exists;
5. validate the exact request against the closed method/host/port/path/query/
   credential rule and required derived-arming hash;
6. compute the remaining aggregate counted-byte budget as `max_run_bytes`
   minus the counted bytes of every prior reservation, terminal or
   spent/unknown; a remainder of zero or less — or a prior spent/unknown
   reservation whose counted bytes cannot be resolved from the manifest-bound
   counter stream — stops as budget exhaustion before any send, and the
   effective streaming cap for this ordinal is the lesser of the stage byte
   cap and that remainder;
7. insert the deterministic reservation event and commit.

The UUIDv5 event ID is
`uuid5(NAMESPACE_URL, "project6:egress:<run>:<arming>:<ordinal>:<kind>")`.
The reservation metrics include only ordinal, stage, method, host, safe
path/query class, credential-audience class, request hash, grant digest,
derived-arming hash, effective streaming cap, remaining aggregate
counted-byte budget, and the detection allowance in effect.

The request fingerprint hashes stable JSON over arming/grant digest, ordinal,
stage, method, normalized exact URL, non-secret header names/values, credential
audience label, and body hash/absence. It never includes the subscription-key
value. Persist the fingerprint, not the URL-bearing preimage.

The canonical terminal projection is:

```text
{
  schema_id,
  connector_run_id,
  connector_key,
  campaign_fingerprint,
  arming_fingerprint,
  grant_sha256,
  campaign_introduction_index_revision,
  campaign_introduction_index_sha256,
  frozen_max_physical_requests,
  entries: [
    {
      ordinal,
      stage,
      reservation_event_id,
      completion_event_id,
      reserved_at,
      send_started_at,
      completed_at,
      request_fingerprint,
      method,
      host,
      path_class,
      query_class,
      credential_audience,
      outcome_class,
      response_status,
      byte_count,
      body_sha256,
    },
  ],
}
```

Entries sort numerically by ordinal; keys use stable canonical JSON. The three
timestamps are normalized UTC RFC 3339 with exactly six fractional digits and
`Z`; they bind later original-grant-window validation. Free text, raw
URLs/queries/headers/bodies, and secrets are excluded. A physical send that
failed before any HTTP status existed still projects exactly one entry with a
null `response_status`, a closed failure `outcome_class`, and null
`byte_count`/`body_sha256` when no body byte was delivered — null is a
recorded value under the closed schema, not an omission, so one entry per
physical send stays deterministic. A missing completion or
missing `send_started_at` for a claimed send derives `spent_unknown` and makes
the ledger ineligible for `fresh_live`. `ledger_terminal_hash` is the SHA-256
of these rederived bytes.

Use deterministic event IDs as the no-migration uniqueness fence. This remains
application-enforced; the exclusive serial boundary—at most one campaign
process alive at any instant—and adversarial tests are mandatory.

### Step 4: Implement one-send HTTP behavior

`BoundedConnectorTransport.send_once` must:

- validate the exact request against the frozen arming;
- use an isolated Requests session with `trust_env=False` and TLS certificate
  verification enabled; cookie persistence is disabled by a rejecting cookie
  policy, the jar must be empty before and after the send, and any
  `Set-Cookie` value is discarded, never stored or replayed;
- mount a counting HTTP adapter as the lowest application-visible transport
  boundary: a Requests `HTTPAdapter` subclass whose `send` observes the final
  prepared request and wraps the returned urllib3 response's read path so
  every body byte delivered to the application is counted before
  Requests-level content decoding. That seam exposes only parsed status and
  header fields — Requests and urllib3 rebuild them after `http.client`
  parsing — so original wire octets are not observable there; the counter
  instead computes canonical status/header bytes, a deterministic
  re-serialization of the parsed HTTP version, status code, reason, and
  headers in received order, one `name: value` CRLF line each plus terminal
  CRLF, byte-encoded as ISO-8859-1 — the same byte-preserving decoding http.client
  applies at parse — so canonical bytes never exceed parser-admitted bytes by
  re-encoding. Chunked transfer framing and trailers are stripped below the seam and
  are not counted. The adapter appends one deterministic counter record per
  physical send — exactly one even when the send fails before any HTTP status
  exists, with `response_status` null and a closed `error_class` — to the
  manifest-bound, seal-covered `http.jsonl` capture carrying only ordinal,
  stage, request fingerprint, canonical status/header bytes, delivered body
  bytes, decoded body bytes, decoded-body SHA-256, nullable response status,
  closed error class, and monotonic start/stop readings paired with injected
  UTC evidence timestamps — never a raw URL, query, header value, or secret;
  original wire octets, TLS framing, and provider-level accounting remain
  outside the experimental claim;
- immediately reject an admitted hostname if any resolved address is
  non-public, while recording that this app-level check is not protection
  against all DNS time-of-check/time-of-use behavior;
- reserve and commit;
- immediately recheck wall-clock expiry, lease deadline, feature flags, and
  configured definition/grant hashes plus the unique-maximal evidence-index
  head revision/digest after reservation commit; on mismatch, record
  `reserved_not_sent`, spend the ordinal, and call no transport;
- capture `send_started_at` from the injected UTC clock immediately before the
  transport call, require it inside both original campaign-definition and grant
  half-open windows, and include it in the later
  completion/failure event; a process death before that event leaves the
  reservation spent/unknown;
- enforce `min_request_interval_ms` as monotonic-clock spacing against the
  previous send start in the same actual-destination-host rate bucket; an
  interval that cannot be satisfied inside both remaining authority windows
  records `reserved_not_sent` and calls no transport;
- fingerprint the final prepared request and require equality with the
  reservation's request fingerprint; both fingerprints are computed by the SAME
  secret-free preimage schema — the full eight-component schema defined in the
  reservation-fingerprint paragraph above (arming/grant digest, ordinal, stage,
  method, normalized exact URL, non-secret header names/values, credential
  audience label, body hash/absence — never the subscription-key value) —
  with the send-side fingerprint recomputed over the request Requests hands to
  the adapter after its own header merging; a mismatch records
  `reserved_not_sent` and calls no transport;
- send `Accept-Encoding: identity` explicitly; a response declaring any other
  `Content-Encoding` is counted at its delivered pre-decode size, classified
  as a stop, and never silently decompressed into the admitted-artifact path;
- call an injected transport once with `allow_redirects=False`;
- configure a Requests adapter with `max_retries=0`;
- count response headers, post-parse and honestly: `http.client` fully parses
  the complete status/header block BEFORE the adapter seam sees parsed fields,
  and the parser itself admits up to 100 header lines of up to 65,536 bytes
  each plus a 65,536-byte status line — so no seam-level threshold is claimed
  or implemented. The counter records the canonical status/header bytes of
  every send in full; the maximum single-send header contribution is the
  parser's own admission ceiling of 6,619,136 bytes;
- stream the body in fixed 64 KiB (65,536-byte) reads under the effective
  streaming cap recorded at reservation — the lesser of the stage cap and the
  remaining aggregate counted-byte budget — while the counting adapter
  independently accumulates delivered bytes; the streaming chunk-boundary
  check compares body bytes delivered against that effective streaming cap,
  and canonical status/header bytes count toward the run aggregate and
  `max_run_bytes` but never against the per-stage body caps or the streaming
  check — consistent with the header-bytes-never-count-against-stage-caps
  rule below; the adapter additionally maintains a separate AGGREGATE tally
  aggregate_crossed := H + B > R (H = canonical status/header bytes of this
  send, B = body bytes delivered, R = the remaining aggregate budget computed
  at reservation), checked immediately after canonical header serialization,
  at every body chunk boundary, and at EOF/completion; the first check that
  finds EITHER the body bound or the aggregate crossed aborts the read, keeps
  every delivered byte counted against `max_run_bytes`, and terminally
  classifies the send as oversized; body-crossing abort
  granularity is one 64 KiB read chunk, the header contribution is
  whole-block granular, and the total single-send overshoot is bounded by the
  SINGLE-SEND DETECTION ALLOWANCE; no claim covers bytes the socket, TLS
  layer, or urllib3 buffered below the seam without delivering them;
- enforce the absolute send deadline on the process monotonic clock during
  streaming: every chunk boundary rechecks the remaining monotonic budget
  derived from the frozen `request_timeout_seconds`, and exhaustion aborts the
  read and classifies the send as a timeout — one spent physical send, never a
  retry;
- return status, safe header facts, body bytes, body hash, byte count, and
  a lossless in-memory raw `Location` value list without following it; never
  collapse duplicate `Location` fields or persist their values;
- record a terminal completion/classification event;
- count an exception after send as spent/unknown.

`completed_at` may follow definition/grant expiry when the bounded request
started inside both windows; it remains constrained by the absolute monotonic
send deadline derived from the frozen `request_timeout_seconds`. Expiry blocks
new sends, not completion accounting for an already-started one.

Do not put retry, redirect, credential fallback, or target selection inside this
class. Connector-specific state machines own those decisions and therefore
reserve new ordinals explicitly.

Byte accounting is defined mechanically, not by intent. The budget currency is
counted bytes — canonical status/header bytes plus delivered body bytes per
physical send — and the grant's `max_run_bytes`, the reservation arithmetic,
the counter records, the evaluator's rederivation, and every acceptance
statement use that one currency:

- delivered body bytes are what the wrapped urllib3 read path handed the
  application before Requests-level content decoding; decoded bytes are what
  streaming yielded after that decoding — under enforced identity encoding the
  two body counts are equal, and any divergence is a counter/ledger
  disagreement;
- canonical status/header bytes count against `max_run_bytes` and never
  against per-stage body caps;
- a redirect response counts in full — canonical status/header bytes plus any
  delivered body bytes — even though its `Location` is never followed on the
  same ordinal;
- a partial, failed, timed-out, or oversized response counts every byte
  actually delivered, and those bytes stay spent; no failure refunds budget;
- explicitly outside the counted entity, with no claim made over them:
  original status-line/header octets as transmitted, chunked transfer framing
  and trailers, TLS records and handshakes, TCP/IP framing and retransmission,
  DNS traffic, and bytes received by the socket, TLS layer, or urllib3 but
  never delivered through the wrapped read path — `max_run_bytes` is an
  application-delivered ceiling with header-block-granular and 64 KiB
  chunk-granular crossing detection, its overshoot bounded by one SINGLE-SEND
  DETECTION ALLOWANCE, not a
  network-receipt guarantee, and the network-level claim belongs to the
  proxy-, firewall-, or OS-level accounting that production promotion already
  requires;
- the ledger entry `byte_count` is the decoded admitted body byte count and
  `body_sha256` hashes those decoded bytes; the counter record carries
  canonical status/header, delivered, and decoded counts so the evaluator
  reconciles them without trusting either side alone.

The DB request ledger and the manifest-bound transport counter are two
independent records of the same physical sends. Neither substitutes for the
other, and any disagreement between them is `INDETERMINATE`, never success.

### Step 5: Run tests and commit

```powershell
Push-Location backend
python -m pytest tests/test_egress_transport.py tests/test_egress_crash.py -q
Pop-Location
git diff --check
git add backend/app/services/connector_egress_transport.py backend/tests/test_egress_transport.py backend/tests/test_egress_crash.py
git commit -m "feat(connectors): ledger every physical live request"
```

## Task 4: Implement the exact fresh ScienceBase state machine

**Files:**

- Modify: `backend/app/services/connectors_sciencebase.py`
- Modify: `backend/app/schemas/api.py`
- Test: `backend/tests/test_sciencebase_fresh.py`
- Test: `tests/test_api.py`

### Step 1: Write failing strict-mode tests

Use an injected fake transport and prove:

- generic submit rejects the reserved proof marker;
- armed execution makes one item-hydration GET and no search request;
- exact filename produces exactly one target;
- missing, duplicate, case-changed, extension-changed, or alternate filename
  stops before artifact send;
- hydration is strict UTF-8 JSON with duplicate object-member rejection before
  ordinary dictionary materialization; lexical duplicate `files`, `name`,
  `downloadUri`, or any other object key fails;
- the selected file object has exactly one string `name` with exact bytes and
  exactly one nonblank string `downloadUri`; absent/blank/non-string locator,
  leading/trailing whitespace/control characters, a `url` fallback, or both
  `downloadUri` and `url` fail before normalization;
- the two admitted ScienceBase hosts pass and every other host fails;
- hydration raw query is byte-for-byte `format=json`; artifact and redirect
  URLs require the raw path byte-for-byte
  `/catalog/file/get/63d1a3c6d34e06fef15006be`, no userinfo/fragment, port
  443, and the raw query byte-for-byte
  `f=mcs2023-germa_salient.csv` before strict UTF-8 pair confirmation;
- leading/trailing/repeated `&`, `;`, empty segments, `f` without `=`,
  extra `=`, blank/alternate keys, `+`, any `%` encoding, double-encoding,
  duplicate `f`, filename case drift, raw-path percent encoding, backslash, and
  dot-segment variants, raw `@` authority, and empty/nonempty `#` delimiters
  fail before reservation for both artifact and redirect;
- cookies, auth, and conditional headers are absent;
- hydration over 5 MiB stops;
- artifact over 64 MiB stops while streaming;
- `304`, partial content, empty content, and non-CSV media/parse shape fail;
- `application/octet-stream` passes only for the unchanged exact `.csv` name
  with no NUL/archive/HTML/PDF signature and a nonempty header/data parse;
- only `301`, `302`, `303`, `307`, or `308` can become the separately armed
  ordinal-3 redirect; require exactly one nonblank raw `Location` field from a
  lossless header multimap, and reject duplicate/disagreeing fields,
  leading/trailing whitespace/control characters, `300`, `304`, `305`, `306`,
  or any other `3xx` without reserving ordinal 3;
- artifact and optional redirect derived armings commit before reservation and
  persist only URL hash plus safe class;
- `ConnectorRunTarget.sciencebase_download_uri`,
  `DatasetSourceProvenance.sciencebase_download_uri`, and every
  `ConnectorArtifactAlias.alias_url` are null in the strict lane;
- no raw hydrated item object or `files[]` object is persisted. Target,
  provenance, alias, permission, and intake JSON use an explicit safe-field
  whitelist; metadata snapshots contain response-body hash and safe projection
  only;
- an isolated-runtime scan across every scalar/text/JSON DB column, all
  non-source storage files, GET responses, events, reports, generated
  artifacts, and the manifest-bound test log capture finds neither the exact
  URL nor its raw query;
- no retry or resume is possible;
- a complete `200` stores raw bytes, target SHA-256, provenance, and
  `DatasetVersion.content_hash` with equality;
- a successful strict run terminates `completed` through
  `finalize_strict_run` with exactly one deterministic terminal event and no
  unexpired lease afterward; every strict stop terminates `failed` the same
  way; `completed_with_errors`, generic finalize, generic resume, and generic
  cancel are unreachable, and a second finalize attempt fails without
  mutation.

### Step 2: Run the failing tests

```powershell
Push-Location backend
python -m pytest tests/test_sciencebase_fresh.py -q
Pop-Location
python -m pytest tests/test_api.py -q -k "sciencebase and (explicit or journey or ingest)"
```

### Step 3: Add the reserved execution branch

Inside `execute_connector_run`, dispatch an envelope with
`schema_id == "project6.connector_egress_arming.v1"` and connector
`sciencebase_mcs` to:

```text
_execute_fresh_exact_sciencebase_run(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    transport: BoundedConnectorTransport,
) -> None
```

Implement three explicit steps:

1. fetch the exact item JSON under the 5 MiB cap and strictly decode UTF-8 with
   duplicate object-member rejection before ordinary dictionary
   materialization;
2. require one root `files` array and exactly one object whose one string `name`
   equals `mcs2023-germa_salient.csv` byte-for-byte and case-sensitively; require
   that object to contain exactly one nonblank string `downloadUri`, no `url`
   fallback/dual locator, and no surrounding whitespace/control characters;
   validate the untrimmed raw URL before any normalization, create exactly one
   target, and commit a hash/class-only derived artifact arming;
3. use that in-memory URL exactly once and anonymously; if it returns `3xx`,
   proceed only for `301/302/303/307/308` with exactly one nonblank raw
   `Location` from the lossless header multimap and no surrounding whitespace/
   controls; validate the untrimmed candidate, commit a second hash/class-only
   derived arming, then use it in memory for reserved ordinal 3. Every other
   `3xx`, missing/duplicate `Location`, or malformed candidate stops.

Do not call `ScienceBaseAdapter.search_page`. Do not swallow hydration errors.
Do not use conditional-request, recurring-sync, resume, or current
`allow_redirects=True` behavior. A crash after either derived arming is not
resumable because no exact URL is durable.

The strict branch owns its terminal transition. On success it calls
`finalize_strict_run(..., terminal_status="completed")` after persistence
commits; on any strict guard, transport, or admission failure it records the
classified failure event and calls
`finalize_strict_run(..., terminal_status="failed")`, then returns without
entering generic discovery, target-pipeline, checkpoint, resume, or generic
finalize code. The generic `execute_connector_run` exception handler must not
relabel a strict run whose deterministic terminal event already exists.

Do not route strict results through current generic URL-bearing persistence.
Add a strict safe projection containing only connector/item/filename/surface,
response-body hash, URL SHA-256, safe scheme/host/port/path/query classes,
checksum facts, byte facts, and continuity identifiers. For this lane:

- set target/provenance `sciencebase_download_uri` and alias `alias_url` to
  `None`;
- construct source-artifact identity from item ID plus exact filename, never
  URL text;
- replace raw/normalized hydration snapshots with one whitelist-sanitized
  metadata projection; never write the upstream item or `files[]` object;
- remove URL fields from target/provenance/alias/source-reference/
  permission/intake JSON and from API/report/log/error projections;
- keep the exact URL only in a non-serializable, `repr=False`
  `FrozenPhysicalRequest` until `send_once` returns, then discard it.

Existing storage/hash helpers may be reused only after auditing that their
arguments and outputs contain no URL-bearing source object. Existing generic
connector behavior remains unchanged.

Raw publisher CSV bytes are an integrity-bound source artifact and must not be
rewritten merely to remove text. Redaction scans classify that one raw blob as
opaque source content; every control-plane or generated file remains in scope.

### Step 4: Run focused and existing regression tests

```powershell
Push-Location backend
python -m pytest tests/test_sciencebase_fresh.py tests/test_layer3_connector_source_intake_pilot.py -q
Pop-Location
python -m pytest tests/test_api.py -q -k "sciencebase"
git diff --check
```

### Step 5: Commit

```powershell
git add backend/app/services/connectors_sciencebase.py backend/app/schemas/api.py backend/tests/test_sciencebase_fresh.py tests/test_api.py
git commit -m "feat(sciencebase): add one-file fresh proof mode"
```

## Task 5: Implement the NRC exact-accession and derived-artifact state machine

**Files:**

- Modify: `backend/app/services/connectors_nrc_adams.py`
- Modify: `backend/app/schemas/api.py`
- Create: `backend/app/services/nrc_aps_strict_parse.py`
- Modify: `backend/app/services/nrc_aps_document_processing.py`
- Audit only, no modification: `backend/app/services/nrc_aps_ocr.py`,
  `backend/app/services/nrc_aps_advanced_ocr.py`,
  `backend/app/services/nrc_aps_advanced_table_parser.py`
- Test: `backend/tests/test_nrc_fresh.py`
- Test: `backend/tests/test_nrc_strict_parse.py`
- Test: `tests/test_api.py`

### Step 1: Write failing strict-mode tests

Prove:

- generic NRC submit rejects the reserved proof marker;
- exactly one keyed Get Document request is sent, with no search POST;
- the key appears only on `adams-api.nrc.gov:443`;
- a missing, malformed, non-HTTPS, userinfo/query/fragment-bearing,
  empty-`?`/`#`-delimited, percent-encoded-path, backslash/dot-segment,
  private-IP, or non-exact `Url` stops;
- strict UTF-8 JSON decoding rejects duplicate object members before ordinary
  dictionary materialization; lexically duplicated `Url` keys stop whether
  their values agree or differ;
- the only first-attempt artifact rule is exact host `www.nrc.gov`, port 443,
  raw path `/docs/ML1712/ML17123A319.pdf`, and no raw `?`/`#` delimiter;
- an admitted detail URL is canonicalized and hashed; only hash plus safe exact
  path class is persisted;
- strict NRC never persists the raw Get Document response or its `Url`:
  target/provenance URL scalars and alias URL are null, document/detail/
  linkage JSON is whitelist-sanitized, and a full scalar/text/JSON/non-source
  storage/serialization/event/report plus manifest-bound test-log scan finds
  no exact artifact URL in raw or escaped form;
- artifact GET is unkeyed;
- artifact request cannot occur until a derived arming event commits;
- `401`/`403` stops without key fallback;
- any API or artifact `3xx` stops and no NRC redirect is followed;
- `application/pdf`, or guarded `application/octet-stream`, plus `%PDF-`,
  nonzero, complete `200`, and the 64 MiB cap are enforced;
- current retry/safeguard and `allow_redirects=True` paths are never invoked;
- successful bytes bind `ConnectorRunTarget.downloaded_sha256`,
  `ApsContentLinkage.blob_sha256`, and the content-addressed blob;
- the strict NRC run terminates only through `finalize_strict_run` with
  exactly one deterministic terminal event, `completed` on success and
  `failed` on every stop, no unexpired lease afterward, and rejection of
  generic resume/cancel in every state;
- the strict parse-lane refusal, bound, and zero-render behaviors enumerated
  in Step 3 (in `backend/tests/test_nrc_strict_parse.py`), exercised in a
  process with the network-deny and subprocess-denial guards installed.

### Step 2: Run the failing tests

```powershell
Push-Location backend
python -m pytest tests/test_nrc_fresh.py -q
Pop-Location
python -m pytest tests/test_api.py -q -k "nrc and (adams or hydrate or artifact)"
```

### Step 3: Add the reserved NRC execution branch

Dispatch the reserved NRC envelope from `execute_nrc_adams_run` to:

```text
_execute_fresh_exact_nrc_aps_run(
    db: Session,
    *,
    run: ConnectorRun,
    lease_token: str,
    transport: BoundedConnectorTransport,
) -> None
```

The state machine is:

1. reserve ordinal 1 and keyed-GET the exact accession;
2. strictly decode UTF-8 JSON with duplicate object-member rejection, require
   the returned accession to equal `ML17123A319`, and require exactly one
   lexical `Url` member;
3. extract that `Url`, require its original raw scheme/authority/path and
   absent `?`/`#` delimiters to match the exact first-attempt
   `https://www.nrc.gov/docs/ML1712/ML17123A319.pdf` rule, then normalize it;
4. commit a new immutable policy snapshot and derived-artifact arming event
   whose fingerprint binds the parent arming, ordinal, URL hash, and safe exact
   path class, without storing the URL;
5. retain the exact URL in memory, reserve ordinal 2, and GET it once without
   credentials;
6. on direct `200`, enforce PDF rules, persist content-addressed bytes, and
   stop without parsing; on `3xx`, stop;
7. commit the one strict terminal transition through `finalize_strict_run`:
   `completed` only after content-addressed persistence commits; `failed` for
   every stop or classified failure. The generic `execute_nrc_adams_run`
   failure path must not relabel a strict run whose deterministic terminal
   event exists, and `completed_with_errors` is unreachable in the strict
   lane.

The strict NRC executor ends at raw admission and never calls the document-
processing path. That path runs native `fitz` parsing, an OCR fallback that is
enabled by default, in-process PaddleOCR, a Tesseract subprocess, and Camelot
table extraction in the invoking process, and the invoking executor here still
holds the NRC key and live egress. Expose instead one strict parse
entry point with a complete enumerated edit surface and exact fail-closed
bounds, invoked only from the secret-free, network-denied downstream phase
(Task 8 Step 4).

The complete parser-lane edit surface is:

- Create `backend/app/services/nrc_aps_strict_parse.py` with:
  - `STRICT_PARSE_PROFILE_ID = "dual_live_proof_v1"`, the frozen bound
    constants below, and `class StrictParseViolation(RuntimeError)`;
  - `install_subprocess_denial_guard()` — idempotent; wraps
    `subprocess.Popen` (the primitive under Tesseract's `subprocess.run`),
    `os.system`, `os.spawn*`, `os.exec*`, `os.posix_spawn*`, and
    `os.startfile` so any call raises `StrictParseViolation`; installed
    before application imports by the phase-B wrapper and re-asserted by the
    entry point;
  - `parse_admitted_blob_strict(*, blob_path, expected_sha256)` — the only
    strict entry: rehash the blob and require equality with the admitted
    SHA-256; build the pinned profile config internally and accept no config
    mapping, engine, document type, or override from any caller; create one
    fresh empty scratch directory and point `tempfile.tempdir` at it for the
    parse; call `nrc_aps_document_processing.process_document`; then apply
    the post-parse checks: scratch directory still empty, serialized output
    within the output bound, returned `extractor_id` equal to the baseline
    `aps_pdf_text_extractor`, `ocr_page_count` zero, and `degradation_codes`
    free of every OCR/advanced/visual code (`ocr_fallback_used`,
    `ocr_required_but_unavailable`, `ocr_execution_failed`,
    `ocr_hybrid_failed`, `advanced_ocr_weights_missing`,
    `advanced_ocr_execution_failed`, `visual_artifact_failed`,
    `visual_capture_failed`); any miss raises.
- Modify `backend/app/services/nrc_aps_document_processing.py` at exactly
  these points, keyed on a new `strict_parse_profile` field added to
  `default_processing_config` (default `None`; generic callers unchanged):
  - `_process_pdf` page cap: under the profile,
    `total_pages > content_parse_max_pages` raises
    `strict_page_limit_exceeded`; the generic thirtyfold allowance
    (`content_parse_max_pages * 30`) is not applied;
  - `_process_pdf` hybrid image branch: its entry gate gains the missing
    `ocr_enabled` check — today the branch invokes Tesseract on availability
    alone — so `ocr_enabled=false` closes every OCR path; this is a generic
    repair whose default-on behavior is unchanged;
  - `_process_pdf` OCR attempt blocks (fallback and hybrid): under the
    profile, reaching either block despite the gates raises
    `strict_ocr_path_refused`; weak/unusable native pages proceed with
    native units and honest quality metrics instead of invoking any engine;
  - the two exception-to-degradation conversions (`ocr_execution_failed`,
    `ocr_hybrid_failed`): under the profile they re-raise instead of
    degrading;
  - `_extract_native_pdf_units`: the `COMPLEX_TABLE_DOC_TYPES` routing
    raises `strict_advanced_table_refused` under the profile before any
    Camelot call, and native `find_tables()` extraction enforces the strict
    row/column caps below;
  - `_process_pdf` accumulation loop: a running UTF-8 byte counter over
    every appended unit text enforces the text ceiling, and a checkpoint
    helper at each existing 100-page chunk boundary and at parse end samples
    peak RSS and CPU seconds against their bounds.
- Do not modify `nrc_aps_ocr.py`, `nrc_aps_advanced_ocr.py`, or
  `nrc_aps_advanced_table_parser.py`: the profile makes their call sites
  unreachable, the routing refusals make reaching them fatal, and the
  subprocess-denial guard makes any residual spawn fatal; they are
  read-audit and test-fixture surface only.

The pinned profile is frozen constants — no field is caller-overridable:
`document_processing_engine="baseline"` with
`document_processing_engine_explicit=true`, required because the unforced
PDF default resolves to the candidate-B OpenDataLoader engine, which writes
input/output artifacts and invokes an external converter;
`ocr_enabled=false`; no `document_type`, so
`ADVANCED_OCR_DOC_TYPES`/`COMPLEX_TABLE_DOC_TYPES` routing is structurally
unselectable; no `artifact_storage_dir`, `file_path`, or `pdf_path`, so no
visual-page artifact write or Camelot path fallback exists;
`visual_lane_mode="baseline"`.

Exact bounds — breach fails the campaign; each names value, unit,
measurement point, and enforcing code:

- pages: 500 pages, read from `document.page_count` immediately after open
  and before any page load, enforced by the `_process_pdf` strict cap;
- rendered pixels: 0 — the strict lane never rasterizes; every render site
  (page-OCR pixmap, advanced-OCR pixmap, visual-page artifact) lies on a
  refused or unconfigured path, and the test suite pins a
  `fitz.Page.get_pixmap` sentinel proving zero calls;
- extracted text: 20,000,000 cumulative UTF-8 bytes, measured at each unit
  append by the `_process_pdf` strict counter;
- table rows/columns: 10,000 rows total and 200 columns per row, measured on
  `find_tables()` extraction results in `_extract_native_pdf_units` before
  unit construction;
- temp disk: 0 bytes, measured by the entry point's post-parse scan of the
  fresh scratch directory `tempfile.tempdir` was pointed at;
- memory: 2,147,483,648 bytes peak RSS, sampled per 100-page chunk boundary
  and at parse end (`resource.getrusage` where available, Windows
  `GetProcessMemoryInfo` peak working set via ctypes otherwise);
- wall-clock: 300 seconds monotonic, via the existing per-page/per-chunk
  parse-deadline checkpoints with `content_parse_timeout_seconds=300`;
- CPU: 300 `time.process_time()` seconds, sampled at the same checkpoints;
- output: 30,000,000 bytes of canonical-JSON serialization of the returned
  payload, measured once after `process_document` returns;
- subprocess: 0 spawns — any wrapped spawn-primitive call raises
  `StrictParseViolation`.

State the mechanism limits as explicit non-claims: memory, CPU, and
wall-clock are checkpoint-sampled failure detectors that fail the campaign
at the next checkpoint; they do not preempt one blocking native `fitz` call
mid-flight. The subprocess-denial and network-deny guards are Python
process-level guards, not an OS sandbox. Refusal-by-construction plus
checkpoint failure detection is the experimental claim; OS-level parse
sandboxing is a production-promotion requirement.

`backend/tests/test_nrc_strict_parse.py` must prove, with both guards
installed: a 501-page fixture raises `strict_page_limit_exceeded` while the
generic path still admits it under the thirtyfold allowance; the current
hybrid branch — a significant image plus available Tesseract under
`ocr_enabled=false` — attempts no OCR and appends no degradation code after
the gate repair, and forcing entry under the profile raises
`strict_ocr_path_refused` rather than degrading to `ocr_hybrid_failed`; a
weak-native-text page parses natively with zero OCR attempts (engine-call
sentinels on `nrc_aps_ocr.run_tesseract_ocr` and
`nrc_aps_advanced_ocr.run_advanced_ocr`); a `COMPLEX_TABLE_DOC_TYPES`
document type raises `strict_advanced_table_refused` before any Camelot
call; the `get_pixmap` sentinel records zero calls across the strict suite;
text, table, temp-disk, output, and injected memory/CPU/deadline breaches
each raise; the entry point rejects a blob-hash mismatch; and its signature
admits no engine, document-type, artifact-dir, or config override. Exceeding
any bound fails the campaign rather than degrading.
`ApsContentLinkage.blob_sha256` binding therefore occurs in the downstream
phase against the admitted bytes; the raw-hash equality it must prove is
unchanged.

Use the same strict safe-projection boundary as Task 4. Do not call current NRC
helpers that persist `normalized_document["url"]`,
`target.sciencebase_download_uri`, `request_url`, `final_url`, raw APS exchange
payloads, or URL-bearing artifact payloads. Store only accession/document
safe fields, response-body hash, artifact URL hash and exact safe path class,
byte facts, and continuity identifiers. Keep target/provenance URL scalar
columns and alias URL null. The exact `Url` exists only in the in-memory
`FrozenPhysicalRequest` through the one send.

The raw PDF is an opaque hash-bound source artifact and is not rewritten for
redaction; all control-plane snapshots, extracted/generated artifacts, DB
fields, API projections, events, reports, and logs remain scan-in-scope.

The current official guide supports the API endpoint/key and shows
`www.nrc.gov/docs/...pdf` in sample results, but it does not prove the live URL
for `ML17123A319`. Treat the exact proposed path as owner-approved
first-attempt authority, not current-source fact. A mismatch stops before the
artifact request.

### Step 4: Run regressions and commit

```powershell
Push-Location backend
python -m pytest tests/test_nrc_fresh.py tests/test_nrc_strict_parse.py -q
Pop-Location
python -m pytest tests/test_api.py tests/test_nrc_aps_safeguards.py tests/test_nrc_aps_artifact_ingestion.py -q -k "nrc or aps"
git diff --check
git add backend/app/services/connectors_nrc_adams.py backend/app/schemas/api.py backend/app/services/nrc_aps_strict_parse.py backend/app/services/nrc_aps_document_processing.py backend/tests/test_nrc_fresh.py backend/tests/test_nrc_strict_parse.py tests/test_api.py
git commit -m "feat(nrc-aps): add exact-accession fresh proof mode"
```

## Task 6: Add one canonical connector-origin continuity receipt

**Files:**

- Create: `backend/app/services/layer3_origin_continuity.py`
- Modify: `backend/app/services/layer3_connector_source_intake.py`
- Modify: `backend/app/services/connectors_nrc_adams.py`
- Modify: `backend/app/services/layer3_qual_aps_execution.py`
- Test: `backend/tests/test_layer3_origin.py`
- Test: `backend/tests/test_layer3_connector_source_intake_pilot.py`
- Test: `backend/tests/test_layer3_qual_aps_execution.py`

### Step 1: Write failing receipt tests

Cover both connectors:

- stable receipt hashing;
- raw blob rehash before minting;
- target, provenance, dataset-version, source-intake, and APS-linkage hash
  equality;
- campaign and arming fingerprint binding;
- evidence-index introduction revision/digest binding;
- connector/run/target/version/content IDs and target identity binding;
- missing or contradictory fields fail closed;
- changing one byte invalidates the receipt;
- caller-supplied or copied `proof_class="fresh_live"` is rejected;
- a strict arming without a verified complete terminal ledger cannot mint a
  receipt;
- a fixed manifest-bound fixture derives `offline_fixture`, never
  `fresh_live`;
- changing, removing, duplicating, or reordering a ledger event changes/fails
  the independently derived terminal ledger;
- exactly one canonical receipt lives on the connector target; every other
  record carries only target ID plus receipt hash;
- an NRC content document cannot enter qualitative execution without its
  connector-origin receipt in the reserved proof lane.

### Step 2: Run and confirm failure

```powershell
Push-Location backend
python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_qual_aps_execution.py -q
Pop-Location
```

### Step 3: Implement the canonical derived receipt contract

Expose:

```text
derive_connector_origin_receipt(
    db: Session,
    *,
    connector_run_target_id: str,
) -> dict[str, Any]

assert_connector_origin_continuity(
    db: Session,
    *,
    connector_run_target_id: str,
    expected_receipt_hash: str,
    expected_bindings: Mapping[str, str],
) -> None
```

Use schema ID `layer3.connector_origin_continuity.v1`.
`derive_connector_origin_receipt` loads run/target/provenance/version/linkage,
rehashes the raw storage reference, and calls
`derive_terminal_request_ledger`.

Proof class is mechanical:

- strict proof arming + verified unique-maximal index chain and matching
  introduction revision/digest + verified original campaign-definition/grant
  evidence + complete eligible terminal ledger + every reservation/send
  timestamp inside both original half-open windows + artifact completion/raw
  hash equality => `fresh_live`;
- fixed test-fixture manifest/source marker + no strict arming/live ledger =>
  `offline_fixture`;
- every other combination is outside this campaign and fails receipt minting.

No function or API accepts `proof_class` as input. Stable-hash the receipt
without `receipt_hash`; never trust stored hashes or projections without
rehashing.

Definition/grant evidence resolution is read-only and target-derived: use the
frozen campaign/connector/index/digest bindings to traverse the configured
unique-maximal chain, resolve the campaign's earliest complete-slice
introduction revision, then select either the matching current definition plus
grant or their matching protected historical-index entries. It accepts no
caller path, definition/grant document, proof class, or "historical" override.
Historical evidence types can prove the intersection that existed when recorded
sends occurred, but cannot be passed to arming, execution, reservation, or
transport.

The authoritative receipt binds the evidence-index introduction
revision/digest alongside the campaign-definition digest/fingerprint, arming
and grant fingerprints/digests, terminal-ledger hash, source identity, storage
reference, and raw content hash.

Persist the receipt without a migration:

- authoritative copy for both connectors:
  `ConnectorRunTarget.source_reference_json["connector_origin_receipt_v1"]`;
- every `DatasetSourceProvenance`, connector-source-intake, `ApsContentLinkage`,
  Layer 3, result-review, package, and handoff surface: only
  `connector_run_target_id` and `connector_origin_receipt_hash`.

For strict live targets, the source-intake metadata contract must omit
`sciencebase_download_uri` and any equivalent URL field. Its safe metadata
binds connector/item-or-accession/exact-filename identifiers, target ID,
content hash/size/media type, and the origin-receipt hash. This reserved-lane
projection must not change the existing generic/fixture intake contract.

The authoritative JSON remains service-enforced mutable storage in this
no-migration MVP. Every guard and evaluator must reconstruct it from raw DB
relationships, ledger events, and bytes; a changed stored copy fails rather
than becoming authority.

### Step 4: Run tests and commit

```powershell
Push-Location backend
python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_qual_aps_execution.py -q
Pop-Location
git diff --check
git add backend/app/services/layer3_origin_continuity.py backend/app/services/layer3_connector_source_intake.py backend/app/services/connectors_nrc_adams.py backend/app/services/layer3_qual_aps_execution.py backend/tests/test_layer3_origin.py backend/tests/test_layer3_connector_source_intake_pilot.py backend/tests/test_layer3_qual_aps_execution.py
git commit -m "feat(layer3): bind connector origin to admitted source"
```

## Task 7: Revalidate origin at execution, review, package, and handoff

**Files:**

- Modify: `backend/app/services/analysis.py`
- Modify: `backend/app/services/layer3_execution_output.py`
- Modify: `backend/app/services/layer3_execution_review.py`
- Modify: `backend/app/services/layer3_package_entry.py`
- Modify: `backend/app/services/layer3_workbench.py`
- Test: `backend/tests/test_layer3_connector_vertical_loop.py`
- Test: `backend/tests/test_layer3_execution_output.py`
- Test: `backend/tests/test_layer3_execution_review.py`
- Test: `backend/tests/test_layer3_package_entry.py`
- Test: `backend/tests/test_layer3_handoff_export_response.py`

### Step 1: Write failing end-to-end continuity tests

Add one offline ScienceBase vertical using the exact filename and one offline
NRC vertical using `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`.

Each test must prove:

- the source receipt is required before a mutating Gate C commit;
- ScienceBase selects `descriptive_summary`;
- exactly one `descriptive_summary_result` artifact is created;
- artifact bytes are rehashed and the digest appears in
  `AnalysisArtifact.metadata_json`;
- `L3PassRun.summary_json` carries origin receipt hash, ordered artifact
  receipts, artifact-set hash, and output-manifest byte hash;
- review rejects a changed artifact or changed origin receipt;
- package construction emits exactly the three admitted package kinds;
- every `L3OutputPackage.payload_hash` matches its payload bytes;
- package submit and handoff prepare reject any origin/artifact/package hash
  mismatch;
- every failed guard leaves affected DB rows/counts/status and artifact files
  byte-for-byte unchanged;
- the successful handoff response says prepared/internal and contains no
  provider-delivery claim.

Negatives must mutate one field or one byte at each boundary. Do not satisfy
the acceptance contract with a single umbrella assertion.

### Step 2: Run the tests and observe failure

```powershell
Push-Location backend
python -m pytest tests/test_layer3_connector_vertical_loop.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py -q -k "connector or origin or descriptive or handoff"
Pop-Location
```

### Step 3: Hash analysis artifacts at creation

Before any artifact write, assert connector-origin continuity for the reserved
lane. In `backend/app/services/analysis.py`, write to an isolated staged path,
calculate SHA-256 and byte count after the staged file is complete, then move
it into its authoritative location and commit the `AnalysisArtifact` row. A
failed validation quarantines the staged file under the repo/runtime archive
policy; it is never silently deleted or admitted.
Record:

```python
{
    "artifact_sha256": artifact_sha256,
    "artifact_size_bytes": artifact_size_bytes,
    "connector_origin_receipt_hash": receipt_hash,
    "proof_class": derived_receipt["proof_class"],
}
```

Reject missing receipt only for the reserved dual-live proof lane; preserve
existing non-campaign callers.

### Step 4: Add a shared downstream verifier

Extend `layer3_origin_continuity.py` with:

```text
assert_downstream_connector_origin(
    db: Session,
    *,
    session_id: str,
    expected_receipt_hash: str,
    boundary: Literal[
        "execution_output",
        "result_review",
        "package_commit",
        "package_submit",
        "handoff_prepare",
    ],
) -> dict[str, Any]
```

Call it **before mutation**, not in response/projection helpers:

- `gate_c_preview(commit_typing=True)`, before `materialize_typing_entry`;
- `execution_selection`, before creating `L3PassRun` rows;
- `analysis_execution_start` and connector-specific execution, before output
  file or `AnalysisArtifact` creation;
- `execution_result_review`, before either summary JSON changes or `db.commit`;
- `materialize_package_entry` and the applicable workbench package commit,
  before package rows/payloads are written;
- `package_review_submit`, before submit-state mutation;
- `handoff_export_prepare`, before prepared-handoff mutation.

`output_metadata_summary` and `execution_result_review_response` may project the
verified receipt hash but are not enforcement points. Keep each guard in the
same transaction/lock scope as its authoritative mutation. Do not fork package
or handoff implementations.

### Step 5: Construct non-self-referential output receipts

The ordered artifact receipt contains artifact ID, type, SHA-256, and size,
sorted by `(artifact_type, artifact_id)`. Hash its stable JSON as
`artifact_set_hash`.

Hash the exact serialized output manifest bytes after construction and store
that hash in `L3PassRun.summary_json`, outside the manifest. Recompute rather
than trust stored values at every later boundary.

### Step 6: Run the focused vertical and regressions

```powershell
Push-Location backend
python -m pytest tests/test_layer3_connector_vertical_loop.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py -q
Pop-Location
git diff --check
```

Expected: both offline verticals reach prepared handoff; every single-axis
mutation fails at its next boundary.

### Step 7: Commit

```powershell
git add backend/app/services/analysis.py backend/app/services/layer3_origin_continuity.py backend/app/services/layer3_execution_output.py backend/app/services/layer3_execution_review.py backend/app/services/layer3_package_entry.py backend/app/services/layer3_workbench.py backend/tests/test_layer3_connector_vertical_loop.py backend/tests/test_layer3_execution_output.py backend/tests/test_layer3_execution_review.py backend/tests/test_layer3_package_entry.py backend/tests/test_layer3_handoff_export_response.py
git commit -m "feat(layer3): preserve connector origin through handoff"
```

## Task 8: Add a validate-only campaign evaluator

**Files:**

- Create: `backend/app/services/connector_campaign_log_capture.py`
- Create: `backend/app/services/dual_live_evaluator.py`
- Create: `tools/dual_live_gate.py`
- Modify: `project6.ps1`
- Test: `backend/tests/test_campaign_log_capture.py`
- Test: `backend/tests/test_dual_eval.py`
- Test: `tests/test_dual_gate.py`

### Step 1: Write failing evaluator tests

The evaluator must report independently for ScienceBase, NRC, and combined
campaign:

- arming/grant validity;
- protected original grant bytes/digests versus frozen arming fields;
- exact protected campaign-definition bytes/raw digest/canonical fingerprint,
  with both grant entries and the one capture reference in the selected
  two-connector slice matching it;
- campaign-introduction evidence-index revision/digest parity across the
  arming, ledger, log seal, and the seal events of every extant connector run
  (both runs for a passing campaign), plus a complete
  unique-maximal predecessor chain whose every successor adds exactly one
  complete disjoint slice as a strict superset;
- exact one-use consumption-marker bytes/hash, deterministic parent-run ID,
  nonce, and `max_armings=1`;
- original campaign-definition and grant-window parity for every reservation
  and physical-send timestamp;
- code and campaign fingerprints;
- independently reconstructed terminal-ledger hashes, reservation/completion
  parity, stage ordering, and physical-send ceilings;
- the counted-byte aggregate rederived from the counter records: an aggregate
  excess over `max_run_bytes` at or below the SINGLE-SEND DETECTION ALLOWANCE
  carrying its correct terminal oversized or budget-exhaustion classification
  passes; an excess above the allowance is a counter defect and
  `INDETERMINATE`; a crossing lacking its terminal oversized or
  budget-exhaustion classification fails;
- per connector run, exactly one valid deterministic strict terminal event, a
  stored terminal status equal to that event's status and equal to
  `completed` for a passing campaign, `completed_at` present, no unexpired
  execution lease, and no failure, cancellation, `cancelling`, or
  lease-reacquisition evidence recorded after the terminal event;
- host/method/path/credential compliance;
- fresh `200` byte evidence;
- raw/provenance/version/content-linkage equality;
- Layer 3 execution and review result;
- exact package-set and payload integrity;
- submit and handoff-prepared receipt;
- redaction scan;
- explicit null checks for strict target/provenance download-URI scalars and
  alias URL scalars;
- scan every campaign-related scalar/text/JSON DB column plus non-source
  snapshots/storage, API serializations, events, reports, generated artifacts,
  and the protected manifest/seal/event-bound runtime logs for exact derived
  URLs, raw exact query strings, encoded/escaped URL forms, fragment material,
  key/header names with values, and duplicate canonical receipts;
- missing/unsealed log capture, wrong campaign/revision, missing/extra log file,
  file/manifest hash mismatch, caller-selected log path, or an unscannable log
  encoding fails closed;
- selected-campaign index cardinality other than exactly one definition,
  exactly two connector entries with the exact connector set, and one capture
  reference fails; the two-campaign selected union must be exactly two
  definitions, four entries, and two captures with no orphan,
  cross-ID/fingerprint alias, or duplicate; additional structurally complete,
  exact-reference, disjoint historical/failed slices are retained and
  permitted without implying a passing outcome;
- any index rollback, fork, gap, orphan object, wrong predecessor/revision,
  non-maximal configured head, changed/dropped predecessor reference, partial
  new slice, or mismatch between a campaign's bound introduction revision and
  its arming/seal/events fails;
- attempting to arm an unconsumed campaign whose introduction revision is a
  preserved ancestor fails before marker/run/event/network activity;
- missing, changed, or overwritten post-run seal, missing/duplicate/mismatched
  `campaign_log_capture_sealed` event on any extant connector run, a seal or
  event naming a connector run that does not exist, or any
  manifest/file-set/seal/event parity failure fails closed — while no seal
  event is required for a run whose creation was correctly prevented;
- strict-mode startup fails if the application/root/HTTP logger census contains
  an enabled file, stream, queue, socket, event-log, or other process-owned
  handler outside the indexed app/HTTP streams and wrapper-owned stdout/stderr;
- validation refuses to start while live egress is enabled, current
  campaign-definition or send-capable grant paths/digests remain configured,
  the runtime child is active, or the log manifest is unsealed; its pre-import
  network-deny guard blocks tested raw-socket, DNS, Requests, and
  connector-transport attempts;
- explicit non-claims.

Pass only when both connector rows pass. Fail closed on:

- missing campaign ID;
- zero connector runs;
- only one connector;
- a stored/caller assertion of `fresh_live` that cannot be independently
  derived, or any fixture/non-campaign proof class;
- pending/unknown reservation;
- a strict run without exactly one valid terminal event, in any nonterminal
  state (`armed`, `pending`, `running`, `cancelling`), in
  `completed_with_errors`, holding an unexpired lease, or carrying any
  failure or cancellation evidence after its terminal event;
- any missing downstream receipt;
- duplicate package kind;
- any secret/redaction hit.

The redaction test injects unique sentinel URLs/queries into both fake metadata
responses, then enumerates mapped SQLAlchemy columns rather than assuming URLs
live only in JSON. It verifies strict scalar URL fields are `NULL`, recursively
scans all JSON/text values, and scans every non-source file below the isolated
snapshot/report/generated-artifact roots. The two admitted raw source blobs
are classified by exact storage ref and hash and excluded from content
redaction because publisher bytes must remain unmodified; their paths and all
surrounding metadata remain in scope.

The same test launches the proof runtime through the campaign capture wrapper,
injects sentinel URLs, queries, and a fake NRC key into each of the four log
streams in raw, JSON-escaped, percent-encoded, and embedded-text forms, stops
the runtime, and seals the manifest. Every form must fail. A clean capture must
pass only when the manifest names exactly the indexed four files, their freshly
rederived byte counts/hashes match, the separate no-overwrite seal binds the
manifest and canonical file set, and every extant connector run — both in
this test's completed dual capture — carries the matching deterministic seal
event. Add an NRC-first-stop capture case: only the NRC run exists, the seal
binds exactly that one run, exactly one seal event is required, and demanding
or fabricating a ScienceBase event fails. Coordinated rewrites of logs plus
manifest, logs plus
manifest plus seal, or any extant-run DB event must fail at cross-domain parity.

Add a two-campaign lifecycle test: campaign 1 passes, its definition/grants
expire, current definition/grant configuration rotates to campaign 2, and both
campaigns still evaluate independently through the protected evidence index.
Prove that the expired campaign-1 evidence cannot arm, execute, reserve, or
send; a missing, changed,
repointed, path-traversing, or caller-supplied archive/index entry makes
historical evaluation fail closed. Campaign 1 must select exactly one
definition, two grant entries, and one capture; campaign 2 must produce a global
selected union of two definitions/four entries/two captures whose per-campaign
slices remain exact. Orphan, duplicate, partial, cross-campaign, or extra refs
inside either selected slice fail. Add a failed-campaign, replacement-campaign,
repeatability-campaign case: all three disjoint slices remain indexed and exact,
while evaluation of the chosen passing pair selects only its exact `2+4+2`
union.

Build that lifecycle with immutable index revision 1 introducing campaign 1
and revision 2 naming revision 1 as its exact predecessor and adding campaign 2
as one complete disjoint slice. Prove revision 2 is the configured unique
maximal head and preserves every revision-1 reference byte-for-byte. Reject an
ancestor rollback, same-revision sibling, forked child, missing index object,
revision gap, predecessor mismatch, mutation/drop/relabel of campaign 1,
partial campaign-2 addition, or a campaign-1 arming/seal/event that names the
wrong introduction revision/digest.
Even if campaign 1's grants and markers remain unused, selecting it after
revision 2 exists must fail before marker, row, event, or transport because its
earliest complete-slice revision is now an ancestor, not the current head.

Add exact-boundary cases: reservation/send at both campaign `not_before` and
grant `issued_at` is eligible; equality with either campaign or grant
`expires_at` is ineligible in current and historical resolution; bounded
completion after expiry remains eligible only when its send started inside both
windows.

### Step 2: Run tests and observe failure

```powershell
Push-Location backend
python -m pytest tests/test_campaign_log_capture.py tests/test_dual_eval.py -q
Pop-Location
python -m pytest tests/test_dual_gate.py -q
```

### Step 3: Implement a read-only evaluator

Expose:

```text
evaluate_dual_live_proof(
    db: Session,
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    settings: Settings,
) -> dict[str, Any]
```

The function may query and rehash referenced bytes. It must not create, update,
delete, seed, normalize, repair, or generate any row or artifact. The CLI writes
its report only to stdout unless the operator explicitly redirects it outside
the validator.

Before per-connector evaluation, it must enumerate and rehash every protected
index object, require the configured head to be the unique maximal member of
one gap-free linear chain, verify every predecessor/successor relation and
strict-superset addition, and resolve the campaign's exact introduction
revision/digest. For each connector it then resolves the exact original
campaign definition and grant only through that chain, rehashes and strictly
parses those bytes and its exact one-use consumption marker, requires
arming/ledger/seal/event introduction-index parity, validates every
reservation/send timestamp against both original half-open windows, reconstructs
the terminal ledger from events, derives the canonical
connector-origin receipt from raw relationships/bytes, and compares the one
stored target receipt plus all downstream hash projections. For the
ScienceBase run it must also require the arming envelope's bound NRC
parent-run ID and `ledger_terminal_hash` to equal its own independently
rederived NRC values, re-verifying — never trusting — the recorded
NRC-first sequencing proof. It must then
reconcile the DB ledger against the manifest-bound transport counter: parse
the sealed `http.jsonl` capture strictly, require exactly one counter record
per ledger send and no unmatched record, and require agreement on ordinal,
stage, request fingerprint, response status, decoded body count, and
decoded-body SHA-256. From the counter's canonical status/header and
delivered-body counts it rederives the run's counted-byte aggregate in the
same currency the grant binds: `fresh_live` eligibility requires that
aggregate to be at most the original grant's `max_run_bytes`, and a crossed
ceiling must carry its terminal oversized or budget-exhaustion
classification, with the aggregate above the ceiling by no more than one
SINGLE-SEND DETECTION ALLOWANCE (defined in the enforced-budgets section) —
a crossing classified any other way, or any larger excess,
failing as a counter defect. It also rederives that
consecutive same-bucket monotonic send starts respected
`min_request_interval_ms`; monotonic readings are comparable only within the
one recorded acquisition process, and records spanning more than one process
boot make the spacing rederivation `INDETERMINATE`. Any missing, extra,
unparseable, or disagreeing record — or a failed budget or spacing
rederivation — classifies the campaign `INDETERMINATE`: ineligible for
`fresh_live` and never reported as success. It must not require
the original definition/grant to remain current or unexpired at evaluation
time, and it must not trust `proof_class`,
`ledger_terminal_hash`, receipt JSON, URL hash, artifact hash, or package hash
merely because a row contains it.

It must also repeat the strict URL-custody audit over all relevant scalar and
JSON columns, all non-source evidence/generated files, and the closed
runtime-log capture resolved from `settings` plus the protected evidence index.
A null violation, raw upstream metadata object, exact URL/query sentinel,
missing/unsealed capture, manifest/file mismatch, or unclassified file fails
closed. Hash/class-only projections are allowed; source blobs are exempt only
when their exact content hashes and storage refs match the continuity receipt.

Before scanning content, rederive the selected campaign's exact one-definition,
two-entry, one-capture index slice and require connector-set, ID, fingerprint,
revision, targets, non-authorities, and both original window checks. Rehash the
strict manifest, rederive its
canonical ordered file-set hash, rehash/parse the separate no-overwrite seal,
and independently query the deterministic seal event of every extant connector
run. All file/manifest/
seal/event values and the sorted extant-run set must agree: the seal's bound
run set must equal the set of extant connector runs, a run whose creation was
correctly prevented requires no event, and a seal or event naming a
nonexistent run fails. The evaluator does not
repair or complete a partial seal.

The custody scanner has an executable bounded algorithm:

1. derive the finite forbidden canonical artifact-URL candidates from the
   original grant plus safe host/path/query classes, rehash them, and require
   equality with each stored URL digest;
2. load the NRC key from protected server configuration only while validating;
   scan for its exact bytes without ever returning them;
3. scan raw bytes for those URLs, `f=mcs2023-germa_salient.csv`, query/fragment
   delimiters adjacent to admitted paths, and subscription-key header/value
   forms;
4. force campaign logs to UTF-8, parse each JSONL line strictly, walk every
   string, and extract URI-like tokens from plain text;
5. for each bounded token/string, scan its raw, JSON-unescaped, HTML-unescaped,
   and percent-decoded-once and -twice forms; invalid encoding or a third
   residual escape layer fails closed rather than widening;
6. report only sink class, relative file/row identity, byte offset, and a
   one-way hit digest—never the URL, query, header value, or key.

The scanner does not claim visibility into OS, proxy, provider, or other
machine-global logs. Those surfaces remain a stated experimental limitation
and a production-promotion requirement.

The evaluator exposes no archive/index path argument, never falls back to a
caller-supplied file, and never calls the current egress resolver or any
arming/execute/transport path. Evidence-index configuration is read-only
validation input, not permission to send.

### Step 4: Add capture and validate PowerShell actions

Add `run-dual-live-proof` and `validate-dual-live-proof` to the
`project6.ps1` action list.

`run-dual-live-proof` performs no HTTP request itself. It resolves the
campaign-log contract from protected settings/index, requires the deterministic
directory to be absent, creates it exclusively, forces UTF-8, and runs the
campaign as two sequential processes that append to the same four indexed
streams with deterministic phase-boundary records.

Phase A launches the acquisition-only child with stdout/stderr redirection and
the exact application/HTTP log handlers and waits in the foreground. Only this
child receives the NRC key, the campaign-definition/grant paths, and
`CONNECTOR_LIVE_EGRESS_ENABLED=true`. It executes armings through raw
admission only and never invokes document parsing. On child exit or operator
stop the wrapper terminates the entire child process tree, closes its
sessions, clears the key, grant, and live-egress environment, and proves
quiescence before anything parses: it re-enumerates the OS process table for
any surviving child-tree process and the socket table for any listening or
established endpoint owned by the campaign runtime, then writes the
quiescence result as a deterministic record to the wrapper stream. A surviving
process or endpoint is a campaign failure and phase B never starts.

Phase B launches a second, secret-free process with no NRC key, no
campaign-definition/grant paths, `CONNECTOR_LIVE_EGRESS_ENABLED=false`, the
same pre-import fail-closed network-deny guard specified for the validator,
and `install_subprocess_denial_guard` from `nrc_aps_strict_parse`, both
installed before application/service imports. It parses the admitted NRC PDF
only through `parse_admitted_blob_strict` under the frozen
`dual_live_proof_v1` profile (Task 5 Step 3)—baseline engine forced
explicitly, every OCR path closed, Paddle/Camelot routing fatally refused,
each fixed bound enforced at its named measurement point—and runs Layer 3C,
review, packaging, submission, and handoff preparation; the ScienceBase CSV
enters Layer 3C through its existing bounded intake path inside the same
guarded process. A `StrictParseViolation`, routing refusal, prohibited
degradation code, or breached bound is a campaign failure. On phase-B exit or operator stop the wrapper flushes/closes all
handlers, rehashes the exact four files, rejects extras, and atomically
creates the manifest. It then computes the raw manifest SHA-256
and canonical ordered file-set hash, atomically creates the strict seal at the
separate pre-indexed `log-seals/<campaign_fingerprint>.json` path, and appends
one matching deterministic seal event to each extant connector run in one DB
transaction — both runs in success, exactly one after an NRC-first stop in
which the ScienceBase run correctly does not exist and is never created to
receive an event. It never rewrites the preflight evidence-index revision. Failure
at any step is a campaign failure, and neither run nor validator may overwrite
an existing index object, directory, manifest, seal, or event.

`validate-dual-live-proof` requires:

- `DUAL_LIVE_CAMPAIGN_ID`;
- `DUAL_LIVE_CAMPAIGN_FINGERPRINT`;
- an existing isolated runtime DB/storage root;
- the configured protected evidence-index root, unique-maximal head path/digest,
  complete predecessor chain, and exact sealed campaign-log manifest/seal
  contract;
- `CONNECTOR_LIVE_EGRESS_ENABLED=false`, no current campaign-definition or
  send-capable connector grant paths/digests, and proof from the sealed manifest
  that the launched runtime stopped;
- the NRC key still available only to the application-network-inert validator
  for in-memory exact-byte leak scanning. No CLI path or report exposes it.

Before importing application/service modules, the CLI installs a fail-closed
process-level network guard for raw socket connect/bind, DNS resolution,
Requests, and connector transport. Tests exercise each route and require zero
network calls. This makes the validator application-network-inert; it is not an
OS/firewall isolation claim.

The action invokes:

```powershell
python .\tools\dual_live_gate.py --campaign-id $env:DUAL_LIVE_CAMPAIGN_ID --campaign-fingerprint $env:DUAL_LIVE_CAMPAIGN_FINGERPRINT
```

It exits nonzero on empty runtime and does not create a report file.

### Step 5: Run tests and commit

```powershell
Push-Location backend
python -m pytest tests/test_campaign_log_capture.py tests/test_dual_eval.py -q
Pop-Location
python -m pytest tests/test_dual_gate.py -q
git diff --check
git add backend/app/services/connector_campaign_log_capture.py backend/app/services/dual_live_evaluator.py tools/dual_live_gate.py project6.ps1 backend/tests/test_campaign_log_capture.py backend/tests/test_dual_eval.py tests/test_dual_gate.py
git commit -m "feat(proof): evaluate dual live continuity read only"
```

## Task 9: Run the complete offline adversarial gate

**Files:**

- Modify only if a defect is found in Tasks 1-8.
- Evidence remains test output; do not generate runtime proof artifacts.

### Step 1: Run the control suite

```powershell
Push-Location backend
python -m pytest tests/test_egress_schema.py tests/test_egress_auth.py tests/test_egress_arming.py tests/test_arming_api.py tests/test_egress_transport.py tests/test_egress_crash.py -q
Pop-Location
```

### Step 2: Run both connector suites

```powershell
Push-Location backend
python -m pytest tests/test_sciencebase_fresh.py tests/test_nrc_fresh.py tests/test_nrc_strict_parse.py -q
Pop-Location
python -m pytest tests/test_api.py -q -k "sciencebase or nrc_adams"
```

### Step 3: Run the Layer 3 continuity suite

```powershell
Push-Location backend
python -m pytest tests/test_layer3_origin.py tests/test_layer3_connector_source_intake_pilot.py tests/test_layer3_connector_vertical_loop.py tests/test_layer3_qual_aps_execution.py tests/test_layer3_execution_output.py tests/test_layer3_execution_review.py tests/test_layer3_package_entry.py tests/test_layer3_handoff_export_response.py tests/test_campaign_log_capture.py tests/test_dual_eval.py -q
Pop-Location
python -m pytest tests/test_dual_gate.py -q
```

### Step 4: Run broader structural checks

```powershell
python -m pytest tests/test_api.py -q
Push-Location backend
python -m pytest tests -q -k "layer3 or connector or nrc"
Pop-Location
python .\tools\l3-progress-check.py
git diff --check
```

Do not claim a full green suite if any command is skipped or unavailable.
Record exact command, exit code, and collected/passed/failed counts.

### Step 5: Perform two independent reviews

Request:

1. a security/egress reviewer to trace every physical send, redirect, retry,
   credential audience, redaction surface, and crash window;
2. a Layer 3 integrity reviewer to rederive every raw/artifact/manifest/package
   hash and check that fixture/live proof classes cannot be confused.

Each reviewer self-verifies against the exact commit. Blocking findings return
to the owning task and repeat its focused tests plus this gate.

### Step 6: Commit any narrow review repairs

Use one commit per coherent defect class. If no repair is needed, create no
empty review commit.

## Task 10: Align operator and canonical documentation after controls land

**Files:**

- Modify: `docs/campaign-records/2026-07-29-dual-live-proof.md`
- Modify: `docs/MASTER_CONTEXT.md`
- Conditional: `docs/program-context/00-posture-and-invariants.md`
- Conditional: `docs/program-context/01-arc-ledger.md`
- Modify: `docs/program-context/02-decision-record.md`
- Modify: `docs/program-context/03-forward-plan.md`
- Modify: `docs/program-context/04-evidence-registry.md`
- Modify: `REPO_INDEX.md`
- Modify: `SCIENCEBASE_PILOT_RUNBOOK.md`
- Modify: `docs/nrc_adams/nrc_aps_status_handoff.md`
- Modify: `next_milestone_plans/README_LAYER3_PHASE1A_PACK.md`
- Conditional: Layer 3 progress board/manifests only if implementation/proof
  claims actually change their declared scope.

### Step 1: Record landed controls without claiming live proof

Add exact merge commit, changed surfaces, focused-test evidence, and independent
review disposition. Use `OFFLINE-PROVEN` for the controls and strict connector
modes. Keep both live acquisitions `OWNER-GATED`.

### Step 2: Preserve the ScienceBase pilot distinction

`SCIENCEBASE_PILOT_RUNBOOK.md` must distinguish:

- its existing recurring/conditional/no-op pilot;
- this exact one-shot, no-conditionals, fresh-byte proof.

Do not silently replace the existing three-cycle acceptance semantics.

### Step 3: Record current NRC evidence without stale transition claims

The status handoff must cite:

- `GET /aps/api/search/{accessionNumber}`;
- the required `Ocp-Apim-Subscription-Key` API header;
- Get Document's returned `Url`;
- the current guide's `www.nrc.gov/docs/...pdf` sample shape;
- the current NRC page's APS/PDF posture and current artifact-URL uncertainty.

The current ADAMS page no longer contains the previously observed WBA
transition notice. Do not cite that mutable page as if it does, and do not use
the unarchived prior observation as current design authority.

### Step 4: Determine index/manifest scope before editing

- `REPO_INDEX.md` is intentionally scoped: add only a status pointer.
- `docs/program-context/` is exhaustive and redacted: `00` changes only for a
  newly standing rail, `01` only for a merged tranche/PR/proof, `02` for a
  durable decision, `03` for the open pursuit, and `04` only for committed or
  re-derivable anchors. Never place a local Downloads path there.
- Do not make `02`-`04` authoritative references to the campaign/plan until
  those exact files are co-committed; while uncommitted, label the whole
  addition candidate-only or omit it. Bind final campaign/plan blob hashes.
- `layer3_progress_manifest.json`,
  `layer3_workbench_proof_manifest.json`, and `layer3_progress_board.md` are
  excluded while the work remains planning/offline controls. Include them only
  when their declared implementation/proof claims change, and then update all
  three coherently.

### Step 5: Validate documentation

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json
git diff --check
git status --short
```

Check every new relative link and every cited path. Scan for unfinished-marker
strings and for overclaim phrases such as “live proven,” “production ready,”
and “delivered”; every hit must be removed or be an explicit non-claim.

### Step 6: Commit

Stage only documentation actually changed. Include `00` only if a new standing
rail was established and `01` only after the controls have a landed commit:

```powershell
git add docs/campaign-records/2026-07-29-dual-live-proof.md docs/superpowers/plans/2026-07-29-dual-live-proof.md docs/MASTER_CONTEXT.md docs/program-context/00-posture-and-invariants.md docs/program-context/02-decision-record.md docs/program-context/03-forward-plan.md docs/program-context/04-evidence-registry.md REPO_INDEX.md SCIENCEBASE_PILOT_RUNBOOK.md docs/nrc_adams/nrc_aps_status_handoff.md next_milestone_plans/README_LAYER3_PHASE1A_PACK.md
git commit -m "docs(connectors): prepare owner-gated dual live proof"
```

## Task 11: Execute the first campaign only after exact owner authority

**Files:**

- No source edits are permitted in this task.
- Runtime evidence uses an isolated operator-selected DB/storage root and the
  protected, index-derived campaign-log directory; no HTTP/CLI caller supplies
  any of those paths.
- One owner-approved campaign-definition file plus two connector grant files
  and their configured digests become protected server inputs; they are not
  posted by the HTTP caller.

### Owner preflight gate

Before either arming:

1. verify the deployed commit equals the reviewed commit;
2. verify the worktree is clean;
3. verify isolated DB/storage roots and the exclusive serial runtime, with at
   most one campaign process alive at any instant;
4. verify no B1b or other lane shares the worktree, runtime process, port,
   evidence root, or credential environment; schedule an operator mutex if it
   would, without treating that lane as connector authority;
5. keep `CONNECTOR_LIVE_EGRESS_ENABLED=false` everywhere through steps 1-11 and
   verify that only the later wrapper-launched acquisition child will receive
   `true`; verify the phase-B downstream process configuration is secret-free—
   no NRC key, no campaign-definition/grant paths—with the pre-import
   network-deny guard enabled;
6. prepare `CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE=true` for that child and
   verify generic ScienceBase/NRC submit/resume routes will be blocked there;
7. in local mode verify direct loopback binding/request path, no trusted proxy,
   and protected operator-only campaign-definition/grant files; in proxy mode
   verify role-enforcing owner identity;
8. independently hash and strictly decode the campaign-definition file, match
   its configured raw digest, rederive its canonical fingerprint, and verify
   ID/revision/targets/profiles/order/package set/half-open window/
   non-authorities; then hash both grant files and require their configured
   digests, strict schemas, campaign/revision/targets, windows wholly inside the
   definition window, exact rules, limits, and non-authorities; record the
   owner acknowledgement that each grant's
   `max_single_send_detection_allowance_bytes` equals exactly 6,684,672 —
   the SINGLE-SEND DETECTION ALLOWANCE — and that `max_run_bytes` is a
   ceiling plus that one disclosed allowance, not a hard maximum;
9. copy the exact non-secret definition and grant bytes, without overwrite, to
   content-addressed files under the protected campaign-evidence root; create a
   new no-overwrite content-addressed evidence-index revision whose exact
   predecessor is the currently configured unique-maximal head (or null only
   for revision 1), which preserves all predecessor refs byte-for-byte and adds
   the one exact definition mapping, two exact grant mappings, deterministic
   expected consumption-marker paths/hashes, and exact log-capture
   directory/manifest/separate-seal contract as one complete disjoint slice;
   require exactly one definition, two connector entries, and one capture for
   this campaign, verify the entire linear chain, strict-superset relation, and
   every archive/index hash independently, then rotate configuration to the new
   uniquely maximal index path/digest and verify both new marker paths, the
   deterministic log directory, and the no-overwrite seal path are absent;
10. verify NRC key presence by hash/presence only, never print the key;
11. run the complete offline gate from Task 9;
12. launch only through the campaign wrapper, setting live egress true only in
    the acquisition child: create the log directory with exclusive permissions, force
    UTF-8, redirect process stdout/stderr, route application and HTTP-library
    logs to `app.jsonl` and the wrapper-owned stdout/stderr streams while
    `http.jsonl` receives counter records ONLY (any other line in `http.jsonl`
    makes the evaluator's strict parse INDETERMINATE), disable other
    process-owned handlers, and record runtime start without logging secrets or
    exact URLs;
13. re-resolve the campaign's earliest complete-slice revision, require it to
    equal the configured unique-maximal head, then create the NRC parent
    arming only, without executing; the ScienceBase parent arming is not
    created here — its grant stays digest-verified but unconsumed until the
    service-defined NRC acquisition-success predicate
    (`evaluate_nrc_acquisition_success`, Task 2) passes inside ScienceBase
    arming creation;
14. verify the NRC atomic consumption marker now exists with the exact indexed
    bytes/hash and deterministic run ID, and verify the indexed expected
    ScienceBase consumption-marker path is still absent and no ScienceBase
    parent run, submission, or policy snapshot exists;
15. inspect the NRC redacted projection, grant digest, and arming fingerprint.

Any mismatch stops before network.

### Execution order

1. execute the NRC parent arming;
2. if the detail `Url` is not exactly the owner-granted
   `https://www.nrc.gov/docs/ML1712/ML17123A319.pdf`, stop for a new owner
   decision;
3. if admitted, require the committed derived arming before artifact GET;
4. stop on artifact redirect, `401`, or `403`; do not send the key to an
   artifact host;
5. evaluate the NRC acquisition-success predicate — the single predicate
   defined once on `evaluate_nrc_acquisition_success` in Task 2 and
   referenced here without restatement. On any failed or indeterminate
   clause — failure, safe stop, or indeterminate — stop: the ScienceBase
   parent arming was never created, so no mechanism has consumed its grant
   and its expected consumption-marker path remains verifiably absent. Only
   after the predicate passes, create the ScienceBase parent arming through
   the same arming service; this wrapper-side evaluation is a campaign-flow
   decision only, because `create_connector_egress_arming` rederives the
   identical predicate inside the creation call — wrapper ordering is never
   the enforcement mechanism. Before the consumption-marker create-new
   operation the service both passes the rederived predicate and re-resolves
   the campaign introduction revision as the current unique-maximal head; it
   binds the NRC parent-run ID and the `ledger_terminal_hash` it rederived
   into the ScienceBase arming envelope. Verify that marker's exact indexed
   bytes/hash and deterministic run ID, inspect its redacted projection,
   then execute the ScienceBase arming;
6. stop if the exact CSV name is absent or ambiguous;
7. require the committed ScienceBase derived arming before artifact and any
   separately admitted redirect GET;
8. after both raw byte sets are admitted and content-addressed, and each
   connector run has already committed its one strict terminal transition
   through `finalize_strict_run` inside its own executor (the NRC transition
   preceded step 5; no run is finalized twice — the deterministic-event fence
   rejects any repeat), the acquisition child exits without parsing either
   artifact; the wrapper terminates the entire child process tree, closes
   sessions, clears the key/grant/live-egress environment, and proves
   process/port quiescence; a surviving process or endpoint stops the campaign
   here;
9. only after that recorded quiescence proof, the wrapper launches the
   secret-free, network- and subprocess-denied phase-B process, which parses
   the admitted NRC PDF only through `parse_admitted_blob_strict` under the
   frozen `dual_live_proof_v1` profile and bounds (Task 5 Step 3) and runs
   each existing Layer 3 workflow through review, three packages, package
   submission, and handoff preparation; any refusal, prohibited degradation
   code, or breached bound stops the campaign here;
10. in success or failure, quiesce and stop the runtime, flush/close all four
    capture streams, atomically seal the strict campaign-log manifest,
    atomically create the separately indexed no-overwrite seal, and append its
    matching deterministic event to each extant connector run — both in
    success; in an NRC-first failure state the ScienceBase run does not
    exist, exactly one seal event is expected, and no run is created merely
    to receive an event;
11. from a separate application-network-inert validation process using the same
    server-configured DB/storage/evidence/log settings, with live egress off,
    current campaign-definition/grant settings cleared, the pre-import
    network-deny guard active, and the key available only for in-memory leak
    scanning, run `validate-dual-live-proof`.

### Pass evidence

Record:

- exact commit, raw campaign-definition digest, rederived canonical campaign
  fingerprint, arming fingerprints, separate raw/canonical grant digests,
  single-use nonce/marker hashes, deterministic parent-run IDs, the NRC
  parent-run ID and the `ledger_terminal_hash` rederived by
  `evaluate_nrc_acquisition_success` at ScienceBase arming creation and
  bound inside the ScienceBase arming envelope as the NRC-first
  full-predicate sequencing proof, and the
  protected campaign-evidence-index introduction revision/digest and verified
  unique-maximal head revision/digest;
- safe per-request ordinal, method, host, path/query class, credential
  audience, status, byte count, and body hash;
- terminal-ledger projections/hashes and reservation/completion parity;
- raw and continuity hashes;
- Layer 3 session/pass/review/package/submit/handoff IDs and hashes;
- validator stdout and exit code;
- sealed campaign-log manifest SHA-256, exact file-set hashes, and custody-scan
  disposition, separate seal SHA-256, and both deterministic seal-event IDs
  without any leaked value;
- independent review disposition;
- explicit non-claims.

Preserve the exact non-secret campaign-definition and grant bytes in the
protected campaign evidence root so later validation can rehash them. The
configured evidence index, not a caller path, resolves them; export only hashes
and a safe scope summary. Do not place local evidence paths in
`docs/program-context/`.

Do not record keys, raw headers, request/response bodies, full artifact URLs,
query strings, or redirect `Location`.

### Failure handling

- A request reservation with unknown completion is spent.
- Never rerun the same arming.
- Never create a second parent arming from the same grant. A marker-only or
  stuck-claim failure consumes it; recovery requires a new grant/nonce/digest
  that explicitly supersedes the old digest plus a new campaign definition/raw
  digest/ID/fingerprint. Same-campaign recovery is forbidden.
- Do not edit code during the campaign and continue under the old grant.
- A code repair requires a new reviewed commit, new protected campaign
  definition/raw digest/canonical fingerprint, new owner grants, and new
  armings.
- Preserve failed evidence; do not delete, rewrite, or relabel it as success.
- A ScienceBase pass plus NRC fail, or NRC pass plus ScienceBase fail, is a
  partial technical outcome and a combined campaign fail.
- An NRC failure, safe stop, or indeterminate outcome occurs before the
  ScienceBase parent arming exists, so no mechanism can have consumed the
  ScienceBase grant. Record the absent expected ScienceBase
  consumption-marker path and the absence of any ScienceBase parent
  run/submission/policy rows as closeout evidence; the evaluator verifies
  that absence rather than inferring it. Campaign-log closeout is phase-aware
  in that state: the wrapper still seals the capture, exactly one
  `campaign_log_capture_sealed` event is expected — on the extant NRC run
  only — and neither the closeout nor the evaluator may require a seal event
  for the ScienceBase run whose creation was correctly prevented, or create
  one merely to receive it. The unconsumed grant is not
  reusable authority: campaign-close head advancement abandons it, and
  recovery follows the new-definition/superseding-grant rule above.

## Task 12: Prove repeatability, then make a promotion decision

After the first campaign passes, execute a second campaign with:

- the same code bytes;
- a new protected campaign definition, raw digest, canonical campaign
  fingerprint, and arming fingerprints;
- new exact owner grants;
- the same two targets and limits;
- no implementation changes between campaigns.

Repeatability passes only if both campaigns independently satisfy the evaluator.
Content hashes may differ if publishers changed bytes; identity, policy, and
continuity invariants must not.

Before campaign 2 arming, create a new immutable no-overwrite evidence-index
revision whose direct predecessor is the configured campaign-1 head, whose
revision increments by one, and whose only additions are campaign 2's complete
definition/two-grant/one-capture slice. Verify it as the unique maximal head
before rotating the configured index path/digest. After campaign 2, point
current definition/grant configuration only at campaign 2, let campaign-1
definition/grants remain expired, and evaluate campaign 1 and campaign 2
separately through the protected evidence-index chain. Both immutable
definitions, both grant/marker sets, and both sealed campaign-log
captures/manifests/seals plus their four cross-domain DB events remain indexed
and must pass. The selected Task 12 union in the global index has exactly two
definitions, four grant entries, and two capture refs; each selected campaign
has exactly its one definition, two connector entries, and one capture, with no
orphan or alias. Additional structurally complete, exact-reference, disjoint
failed/historical slices remain preserved, keep their failed disposition, and
do not enter this pair's union. Then prove a
campaign-1 historical definition/grant evidence cannot be accepted by arming,
execute, reservation, or transport. Rotating the original definition/grant back
while revision 2 remains head must fail before marker lookup because campaign
1's introduction is an ancestor. Separately retain and reverify campaign 1's
permanent consumption marker as historical evidence; Task 2 already proves
same-head grant rotation cannot mint a second parent arming after consumption.
These independent checks are mandatory: without them, repeatability would only
prove the newest campaign and would silently discard the auditability of the
first or conflate the head-only and one-use fences.

Also prove the configured index head cannot roll back to campaign 1 or point to
a sibling/fork, every prior index object remains content-addressed and
no-overwrite, each successor is a strict superset, and each campaign's
arming/seal/events retain its introduction revision/digest even after head
rotation.
Even if campaign 1's grants were never consumed, campaign 1 cannot arm after
campaign 2's successor becomes head because its introduction revision is now a
preserved ancestor; this rejection must precede marker creation and all DB or
network effects.

Then choose explicitly:

### Remain experimental

Choose this when usage stays occasional, local, serial, and owner-operated.
Keep the feature default-off, retain no-migration records, and require new
finite grants for every campaign.

### Promote to supported operation

Promotion requires a separate Tier-2 design and migration for normalized
campaign, grant, request-reservation, and shared-budget tables plus:

- multi-process-safe leases and atomic global ceilings;
- durable dispatch/recovery;
- proxy or OS-level independent egress accounting;
- secret-manager integration and credential rotation;
- normalized protected URL storage and export redaction;
- recurring/default-on policy;
- operator UX, alerting, retention, and incident response;
- rollback/containment proof;
- support-matrix and production-readiness review.

The two experimental campaigns are evidence for that decision. They do not
themselves authorize promotion.

## Definitions of done

### Offline control implementation complete

1. Tasks 1-10 are merged on current main with exact green evidence.
2. Independent egress/authority and Layer 3 integrity reviews have no
   unresolved blocker.
3. The current docs say offline controls are ready while both live connector
   runs remain owner-gated.
4. No owner grant, fresh acquisition, campaign pass, repeatability, delivery,
   or production readiness is implied.

Owner withholding Task 11 does not make the offline implementation incomplete.

### First dual-live campaign proof complete

1. Task 11 receives one exact independently verified campaign definition and
   two exact independently verified connector grants.
2. Both fresh acquisitions and downstream workflows pass the read-only
   evaluator.
3. Every live claim is bound to protected definition/grant bytes and digests,
   the verified unique-maximal index chain and campaign-introduction
   revision/digest that was current before arming, the rederived canonical
   campaign fingerprint, canonical one-use consumption markers, canonical
   terminal ledgers, both original half-open-window send timestamps, rederived
   origin/byte receipts, the sealed protected runtime-log manifest, separate
   no-overwrite seal, matching cross-domain DB events/custody scan, and explicit
   non-claims.

### Repeatability complete

Task 12 independently passes a second campaign under a new definition/grants
with unchanged code, then re-evaluates both campaigns after current-definition/
grant rotation and first-campaign expiry. The second index revision is a direct
strict-superset successor introducing only campaign 2, and even an unused
campaign-1 slice cannot arm once it is an ancestor. Even then, production
promotion remains a separate decision.

The long-term milestone is not “two downloads.” It is a repeatable,
reviewable, bounded proof that connector-origin bytes can become useful Layer 3
work products without losing provenance, exceeding authority, leaking a
credential, or confusing internal preparation with external delivery.
