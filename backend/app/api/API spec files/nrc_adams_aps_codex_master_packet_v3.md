# NRC ADAMS APS — Codex Master Packet v3

## Use this file as the primary handoff to Codex

This file supersedes handing Codex only the earlier v2 handoff. The earlier v2 handoff is still useful, but by itself it is not the strongest packet because it is architecture-heavy and deliberately non-restrictive. The attached Golden Record dossier contains stricter factual detail about APS request variants, response-envelope ambiguity, validation tests, provenance requirements, and the shared connector contract. Codex should work from this merged packet.

## Priority order of truth

1. Live observed APS behavior in controlled probes/tests.
2. Official APS guide / developer portal semantics.
3. Golden Record APS dossier as the current authoritative local synthesis.
4. Existing repo code/types/tests as non-authoritative local assumptions.
5. Earlier v2 handoff as the architecture/anti-fragility overlay.

If any lower layer conflicts with a higher layer, the higher layer wins.

---

## What Codex should receive

Give Codex this file as the main instruction packet.

Also attach or paste alongside it:
- the existing repo/project,
- the Golden Record dossier,
- the earlier v2 handoff only as supporting architecture rationale if needed.

If only one file can be supplied, use this file alone.

---

## Core implementation stance

Implement APS as a:
- tolerant request builder,
- tolerant compatibility mapper,
- tolerant response normalizer,
- raw exchange recorder,
- normalized persistence mapper,
- connector-ready orchestrator.

Reject any implementation that directly couples:
- UI request types to the vendor contract,
- one fixture JSON shape to the parser,
- saved query definition to concrete page traversal state,
- narrow normalized DB rows to the full vendor payload.

---

## Confirmed base API surface

Base URL:
- `https://adams-api.nrc.gov`

Developer portal:
- `https://adams-api-developer.nrc.gov/`

UI search site:
- `https://adams-search.nrc.gov`

Auth:
- subscription key via `Ocp-Apim-Subscription-Key`
- never expose key in browser/client-side code

Primary endpoints:
- `POST /aps/api/search`
- `GET /aps/api/search/{AccessionNumber}`

Expected headers:
- GET: `Ocp-Apim-Subscription-Key`, `Accept: application/json`
- POST: `Ocp-Apim-Subscription-Key`, `Content-Type: application/json`

---

## Query contract: design rules

### 1. Separate logical query from concrete request

Maintain at least two objects:
- logical query definition
- concrete page request payload

`skip` and other traversal/runtime knobs must live in the concrete page request, not the saved logical query identity.

### 2. Support guide-native request shape first

Treat this as the primary canonical outbound shape:

```json
{
  "skip": 0,
  "sort": "DateAddedTimestamp",
  "sortDirection": 1,
  "searchCriteria": {
    "q": "nuclear safety",
    "mainLibFilter": true,
    "legacyLibFilter": false,
    "properties": [
      {
        "name": "DocumentType",
        "operator": "equals",
        "value": "Letter"
      },
      {
        "name": "DocumentDate",
        "operator": "ge",
        "value": "2024-01-01"
      }
    ]
  }
}
```

### 3. Preserve compatibility with older/draft shapes

Also accept and translate these inbound shapes:
- Shape A: `q/filters/anyFilters/...`
- Shape B: `queryString/docketNumber/...`

Do not send those blindly to the wire unless live validation proves acceptance. Normalize them into the guide-native shape first, while preserving the original inbound payload for audit.

### 4. Builder + pass-through, not builder-only

Provide typed helpers for common cases, but allow raw vendor-compatible payload pass-through.
Unknown top-level fields must be preserved in lenient mode instead of rejected.

### 5. Validation must be mode-based

Two modes:
- strict-builder mode
- lenient-pass-through mode

Lenient mode must warn, not over-block.

### 6. Canonicalization rules

Allowed:
- sort object keys for fingerprints
- preserve array order
- preserve omitted vs explicit-null distinctions
- preserve exact outbound request body

Disallowed:
- mutating saved logical queries when injecting `skip`
- silently injecting ambiguous defaults without recording them

### 7. Library flags

Do not rely on vendor defaults for `mainLibFilter` / `legacyLibFilter`.
Apply defaults in one explicit place and record that they were applied.

---

## Deterministic compatibility mapper

Codex must implement a deterministic mapper from draft/local shapes into the guide-native outbound shape.

### Field mapping

| Inbound field | Shape | Outbound target | Rule |
|---|---|---|---|
| `q` | A | `searchCriteria.q` | direct copy |
| `filters[{field,value}]` | A | `searchCriteria.properties[]` | map to `{name: field, operator: "equals", value}` if operator absent |
| `anyFilters[{field,value}]` | A | `searchCriteria.properties[]` | same mapping; preserve advisory OR logic in logs/metadata |
| `mainLibFilter` | A | `searchCriteria.mainLibFilter` | direct copy |
| `legacyLibFilter` | A | `searchCriteria.legacyLibFilter` | direct copy |
| `sort` | A | `sort` | direct copy |
| `sortDirection` | A | `sortDirection` | direct copy |
| `skip` | A | `skip` | direct copy |
| `queryString` | B | `searchCriteria.q` | direct copy |
| `docketNumber` | B | `searchCriteria.properties[]` | map to one or more `DocketNumber` equals filters |
| `sort` with `+/-` prefix | B | `sort` + `sortDirection` | strip prefix, map `+`→asc(0), `-`→desc(1) |
| `filters[{name,operator,value}]` | B | `searchCriteria.properties[]` | map `eq→equals`, `gt→ge`, `lt→le`; otherwise pass through if official |

### Required mapper behavior

- preserve original inbound payload untouched
- record mapper version used
- record warnings when OR semantics are only approximated
- strip internal advisory fields before wire send
- persist exact final outbound payload actually sent

---

## Filter handling rules

Support at minimum the official text operators:
- `contains`
- `notcontains`
- `starts`
- `notstarts`
- `ends`
- `notends`
- `equals`
- `notequals`

Support official date-filter expressions using `name/operator/value`, including `DocumentDate` with `ge` semantics. Treat `DateAddedTimestamp` filter syntax as operationally important but not fully proven until live validation.

Do not hard-code a tiny enum that blocks future property names or future operators surfaced by the developer portal.

---

## Response boundary: mandatory tolerant normalizer

### Search response

Do not hard-code one response envelope. Handle at least:
- root results key variants: `results`, `Results`, `documents`, `Documents`
- total/count variants: `count`, `total`, `Total`, `totalHits`, `total_hits`, `TotalHits`
- flat document rows inside results
- hit objects containing nested `document`

Normalize all search pages into one internal structure such as:

```json
{
  "total_hits": 142,
  "raw_total_key": "count",
  "hits": [
    {
      "hit_meta": {
        "score": 0.98,
        "highlights": null,
        "semantic": {"rerankerScore": null, "captions": null}
      },
      "vendor_hit": {"...": "raw hit object"},
      "vendor_document": {"...": "raw document object"},
      "accession_number": "ML12345A678",
      "url": "https://...",
      "title": "Inspection Report",
      "document_date": "2024-01-10"
    }
  ],
  "extra": {}
}
```

### Get-document response

Handle both:
- top-level document payloads
- wrapped payloads under `document`

### Content extraction

Do not bind text extraction to only one field name. Use a ranked path extractor across candidates such as:
- `document.content`
- `content`
- `IndexedContent`
- `indexedContent`
- `DocumentText`
- `documentText`
- `DocumentContent`
- `documentContent`
- `Text`
- `text`

Record which field/path produced extracted text.

### Unknown fields

Preserve full raw vendor payloads at every layer.
Do not destructively flatten away vendor properties.

---

## Artifact retrieval rules

Treat `Url` as the current primary vendor locator, but do not assume:
- it is always a PDF,
- it is always stable,
- it never redirects,
- it never requires auth,
- it is always the only artifact pointer.

For every artifact fetch, record:
- vendor URL
- request URL
- final resolved URL
- response status
- response headers
- content type
- byte size
- sha256
- fetched_at
- whether auth was required

Artifact fetch failure must not invalidate the metadata entity.

---

## Pagination and incremental sync

Pagination is offset-based via `skip`.
Do not assume page size or count semantics are stable.
Loop until the stop condition is empirically confirmed, but default operationally to stopping on empty results.

Incremental sync defaults:
- watermark field: `DateAddedTimestamp`
- overlap: 259200 seconds (3 days) as conservative default
- deterministic sort: `DateAddedTimestamp desc`
- dedupe key: `AccessionNumber`

Canonical incremental loop:
1. Build query for `DateAddedTimestamp >= last_watermark - overlap`
2. Send search with deterministic sort
3. Page by `skip`
4. Normalize each hit/document
5. Download artifact when possible
6. Compute sha256 and store provenance
7. Advance watermark to max observed `DateAddedTimestamp`

---

## Storage and provenance: minimum contract

Persist, at minimum:

### Request log
- request_id
- endpoint
- subscription_key_hash
- payload_hash
- sent_at
- request URL
- request headers subset/redacted
- exact request body

### Response log
- request_id
- status_code
- schema_variant_observed
- count_returned
- received_at
- response headers
- raw body bytes/text
- parse status

### Search-page capture
- run_id
- logical query fingerprint
- concrete page fingerprint
- skip
- page index
- observed total/count key
- observed results key
- raw search JSON

### Document/vendor object capture
- accession_number
- vendor_hit_json
- vendor_document_json
- normalized projection fields
- content_source_path

### Artifact log
- accession_number
- url
- final_url
- sha256
- bytes
- fetched_at
- http_status
- url_still_valid / observed_ttl
- content_type

### Compliance flag
- `retention_allowed: yes|no|unknown`

Do not assume retention/redistribution permission; default to `unknown` until confirmed.

---

## Shared connector contract

APS must emit records compatible with the broader connector system using a canonical additive schema such as:

```json
{
  "provider": "nrc_adams_aps",
  "accession_number": "ML12345A678",
  "docket_number": "05000275",
  "document_date": "2024-01-10",
  "date_added_timestamp": "2024-01-11T08:22:00Z",
  "url": "https://...",
  "sha256": "...",
  "bytes": 2048000,
  "fetched_at": "2024-01-12T10:00:00Z",
  "retention_allowed": "unknown"
}
```

Provider-specific extras must live under nested provider-specific objects rather than polluting the shared namespace.

---

## Architecture decomposition

### 1. APS client layer
Responsibilities:
- authenticated HTTP I/O
- timeout/retry classification
- raw exchange capture
- no persistence decisions

### 2. payload builder / validator layer
Responsibilities:
- strict builder helpers
- lenient pass-through acceptance
- compatibility translation
- canonicalization for fingerprints

### 3. response normalizer layer
Responsibilities:
- envelope detection
- hit/document normalization
- content extraction path ranking
- preservation of raw payloads

### 4. connector orchestration layer
Responsibilities:
- run modes
- paging
- incremental sync
- dedupe
- provenance writes
- partial-failure state handling

### 5. persistence layer
Responsibilities:
- raw exchanges
- normalized entities
- artifact lineage
- query/run state

### 6. diagnostics/test layer
Responsibilities:
- live probes
- schema-drift reports
- ramp tests
- replay tests from stored raw responses

---

## Mandatory live validation tests before production

Codex must wire explicit validation hooks for these tests:
- APS-V1: QPS ramp test
- APS-V2: request shape acceptance
- APS-V3: response envelope variant / count semantics
- APS-V4: `Url` auth and TTL behavior
- APS-V5: `DateAddedTimestamp` filter syntax
- APS-V6: pagination stop condition
- APS-V7: `content` boolean behavior
- APS-V8: page-size cap / `take` parameter behavior

The implementation must not hard-code unverified assumptions where one of these tests is the known resolution path.

---

## Existing repo: how to treat it

Useful current artifacts:
- APS client code
- probe workflow
- live smoke script
- pipeline code
- API route code
- fixtures
- frontend request types

But repo artifacts are not vendor truth. They are local assumptions.

Codex should preserve the useful structure while widening these weak points:
- search parsing that assumes `total` + flat `results[]`
- get-document parsing that assumes top-level fields instead of possible `document` wrapper
- DB schema that is too lossy for provenance-heavy connectors
- query type definitions that are too narrow to define the whole backend contract

---

## Hard requirements / anti-fragility rules

1. Raw-first capture is mandatory.
2. Unknown vendor fields must be preserved, not discarded.
3. Compatibility mapping must be deterministic and logged.
4. Normalization must be reversible enough to re-derive from stored raw payloads.
5. Query identity and traversal state must remain separate.
6. Partial failures must be represented explicitly.
7. Rate limiting must be centralized per `(subscription_key, host)`.
8. Config linting must block obvious host/profile mismatches.
9. Tests must assert tolerance for both flat and nested vendor envelopes.
10. No single fixture is allowed to define the parser contract.

---

## Practical answer to the original question

Do not give Codex only the earlier v2 handoff unless you have no alternative.

Best practice:
- give Codex this merged v3 packet as the primary file,
- also provide the repo,
- optionally include the Golden Record dossier as supporting evidence/reference.

If constrained to one artifact, this v3 file is the one to use.
