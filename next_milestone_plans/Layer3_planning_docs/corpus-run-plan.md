# SEC XBRL Corpus Run Plan

Status: Tier-1 planning doc for an owner-authorized future operator run. This
document does not authorize live SEC egress, source changes, runtime-default
changes, durable schema changes, persistence changes, redaction-posture changes,
value reveal, or production-readiness claims.

The static ticker list below is public ticker metadata supplied by the owner for
planning. The source list file is not committed. Live CIK resolution, filing
selection, source acquisition, Arelle execution, and proof import all remain
operator-phase actions behind the existing preflight and default-off gates.

## Source Authority

- Rate and live-source posture: `backend/app/core/config.py` and
  `backend/app/services/layer3_sec_edgar_live_source_artifact.py`. Current
  defaults are live network off, one request per second, ten live requests per
  process, 25 MB source-artifact max bytes, and official ticker resolution off.
  The live-source service admits rates from 1 to 10 requests per second and
  records the policy id
  `sec_edgar_text_table_live_source_artifact_default_1rps_max_10rps_v1`.
- Live preflight: `diagnostics/assessment/sec-live-preflight.py`, summarized in
  `next_milestone_plans/Layer3_planning_docs/1363-sec-live-preflight.md`.
  Artifact-free operator checks use `./project6.ps1 -Action
  validate-sec-live-preflight` or the direct `--no-report` script mode.
- Stratified matrix preflight:
  `diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight.py`.
  It is validate-only and requires explicit live authorization, a User-Agent
  marker, Arelle/taxonomy readiness, isolated storage outside the repo, and an
  external matrix plan.
- Current real-corpus gates:
  `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py` and
  `next_milestone_plans/Layer3_planning_docs/1266-sec-xbrl-real-product-runner.md`.
  The in-repo minimum is 30 filings across 15 issuer hashes with required form
  families and no silent completeness/truncation failures.
- Delivery/status/provenance:
  `backend/app/services/layer3_sec_edgar_delivery_status_provenance.py`.
  This is the current per-filing supported/degraded/blocked status and hash-only
  provenance surface.
- Redaction guard:
  `backend/app/services/layer3_sec_xbrl_public_authority_guard.py`. Generic
  current committed surfaces reject raw values, raw CIK/accession/company/ticker
  authority keys, SEC URLs, local paths, storage paths, and operator contacts
  unless a narrower schema-specific policy explicitly admits a public field.
- Durable storage record:
  `docs/program-context/04-evidence-registry.md` names `C:/p6store` as the
  public-by-design accepted root. This plan does not provision, migrate, or write
  to that root.
- Merge policy:
  `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`.
  This doc-only lane is Tier 1 because it changes planning text only.

## Static Ticker Matrix

This table is a predeclared plan, not resolved issuer truth. The operator phase
must resolve every ticker through the admitted static allow-list or the official
ticker resolver when that resolver is explicitly enabled. A failed resolution is
a named disposition, not a silent failure.

| # | Ticker | Static SEC posture | Planned form request | Required disposition rule |
|---:|---|---|---|---|
| 1 | NVDA | Domestic issuer expected; already in static allow-list. | Latest 10-K and 10-Q if available. | Supported if inline facts and Arelle sidecar succeed; otherwise named degraded/blocked reason. |
| 2 | AMD | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 3 | TSMC | Owner ticker is an alias-like token; SEC-listed ADR symbol may differ. | Annual foreign form and 6-K only after official resolution. | Record `ticker_alias_resolution_required` unless the operator supplies admitted public resolution. |
| 4 | MSFT | Domestic issuer expected; already in static allow-list. | Latest 10-K and 10-Q if available. | Supported if current machinery admits the filing. |
| 5 | GOOG | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 6 | AMZN | Domestic issuer expected; already in static allow-list. | Latest 10-K and 10-Q if available. | Supported if current machinery admits the filing. |
| 7 | META | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 8 | AAPL | Domestic issuer expected; already in static allow-list. | Latest 10-K and 10-Q if available. | Supported if current machinery admits the filing. |
| 9 | DIS | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 10 | HOOD | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 11 | NFLX | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 12 | SONY | Foreign private issuer expected; already in static allow-list. | Latest 20-F plus 6-K/current report when applicable. | Supported annual, sparse/diagnostic 6-K if no inline facts. |
| 13 | AMCX | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 14 | CCJ | Canadian/foreign private issuer expected; already in static allow-list. | Latest 40-F or 20-F plus 6-K when applicable. | Supported annual, sparse/diagnostic 6-K if no inline facts. |
| 15 | UUUU | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 16 | DNN | Canadian issuer expected; resolver may be required. | Latest 40-F or 20-F plus 6-K when applicable. | Resolve live or record named no-resolution/no-filing disposition. |
| 17 | KAP | Public ticker token, but SEC company-filing availability is uncertain. | Attempt only after official resolution. | Likely `likely_no_sec_company_filings` unless resolver proves otherwise. |
| 18 | LEU | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 19 | PDN | Public foreign ticker token; SEC company-filing availability is uncertain. | Attempt only after official resolution. | Likely `likely_no_sec_company_filings` unless resolver proves otherwise. |
| 20 | YCA | Public foreign ticker token; SEC company-filing availability is uncertain. | Attempt only after official resolution. | Likely `likely_no_sec_company_filings` unless resolver proves otherwise. |
| 21 | NXE | Canadian issuer expected; resolver may be required. | Latest 40-F or 20-F plus 6-K when applicable. | Resolve live or record named no-resolution/no-filing disposition. |
| 22 | GEV | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 23 | NUE | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 24 | MT | Foreign private issuer expected; resolver may be required. | Latest 20-F plus 6-K when applicable. | Supported annual, sparse/diagnostic 6-K if no inline facts. |
| 25 | CLF | Domestic issuer expected; resolver likely required unless allow-list expands before run. | Latest 10-K and 10-Q if available. | Resolve live or record `official_ticker_resolution_missing`. |
| 26 | STLD | Domestic issuer expected; already in static allow-list. | Latest 10-K and 10-Q if available. | Supported if current machinery admits the filing. |
| 27 | TRLV | Public ticker token; may not be the SEC company ticker. | Attempt only after official resolution. | Likely `ticker_alias_resolution_required` or `likely_no_sec_company_filings`. |
| 28 | GTBIF | OTC/foreign reporting posture uncertain. | Attempt only after official resolution. | Likely `likely_no_sec_company_filings` unless resolver proves otherwise. |
| 29 | CURLF | OTC/foreign reporting posture uncertain. | Attempt only after official resolution. | Likely `likely_no_sec_company_filings` unless resolver proves otherwise. |
| 30 | CRLBF | OTC/foreign reporting posture uncertain. | Attempt only after official resolution. | Likely `likely_no_sec_company_filings` unless resolver proves otherwise. |

## Operator Run Design

1. Start from current `project6-origin/main` in an isolated worktree. This plan
   does not authorize running from the dirty root checkout.
2. Run live preflight in artifact-free mode. Stop before any SEC request unless
   live network, User-Agent marker, safe database, storage, request controls, and
   smoke identity checks are ready.
3. Run stratified matrix preflight with an external matrix plan. The committed
   repo may record hashes/counts/policy identifiers, but not raw CIK,
   accession, URL, path, User-Agent, contact, raw filing bytes, or raw fact
   values.
4. Resolve ticker identities only in the operator phase. Existing static
   allow-list entries may be used. Off-list tickers require the official resolver
   flag and live preflight; unknown resolver results become named dispositions.
5. Batch by current connector ceilings: at most four CIK refs, six form types,
   and eight examples per connector request. Use deterministic chunk ids such as
   `corpus-go-static-01`, not raw accessions.
6. Treat each selected filing as isolated. One filing may be supported while the
   adjacent filing is degraded or blocked. Every filing slot must carry a final
   state and reason code.

## Rate, Request, And Time Budget

Rate policy has three layers:

- Default: one request per second when not configured.
- Admitted ceiling: ten requests per second.
- Selected plan: approximately two requests per second only when the operator
  entry point honors `LAYER3_SEC_EDGAR_RATE_LIMIT_PER_SECOND=2`. If the selected
  runner still pins the current one-request-per-second diagnostic posture, the
  slower posture is compliant and must be logged as the actual rate.

Use serial requests with per-request pacing. At two requests per second, the
operator should enforce at least 0.55 seconds between SEC requests. At one
request per second, use the current one-request posture. Do not parallelize SEC
requests to simulate a higher effective rate.

Approximate request budget for the 30-ticker plan:

- 1 official ticker snapshot request when off-list resolution is enabled.
- Up to 30 submissions metadata requests, one per resolved issuer.
- About 60 filing artifact requests, targeting one annual and one interim or
  current filing per resolved issuer when available.
- Up to 30 CompanyFacts/oracle requests for resolved issuer checks.
- 20 percent retry/headroom reserve.

Planning estimate: about 120 to 150 SEC requests if every ticker resolves and
both filing slots are available. Wire-time minimum is about 60 to 75 seconds at
two requests per second, or 120 to 150 seconds at one request per second. Real
elapsed time should be budgeted in tens of minutes because Arelle, storage,
sidecar verification, and proof generation dominate the request minimum.

## Storage Budget

The current live source-artifact default max bytes is 25 MB. For 60 filing
artifacts, the raw source-artifact ceiling is therefore about 1.5 GB before
sidecars, value stores, receipts, proof files, and retry residue. If the operator
raises the filing cap for genuinely larger filings, use a per-filing written
justification and preserve the 120-second timeout ceiling. A conservative 120 MB
large-filing cap over 60 filings implies about 7.2 GB of source-artifact headroom
before derived artifacts.

Gate the run on storage preflight:

- storage root exists outside the repo and outside OneDrive;
- storage exposure remains disabled;
- canonical root marker is `C:/p6store` when that public-by-design root is
  selected, otherwise committed proof records only a storage-root hash/marker;
- free-space reserve is at least 10 GB or two times the configured source cap
  estimate, whichever is larger;
- artifact count and namespace count are logged by hash/count only.

## Client Request Id Namespace

Use a stable public namespace that does not embed raw CIKs or accessions:

- run namespace: `sec-xbrl-corpus-go-2026q3-v1`;
- chunk namespace: `sec-xbrl-corpus-go-2026q3-v1-chunk-XX`;
- filing slot namespace:
  `sec-xbrl-corpus-go-2026q3-v1-<ticker_symbol>-<form_family>-slot-XX`.

The request id is a routing/idempotency key, not proof of filing identity. Bind
actual filing authority through existing receipt hashes after operator
resolution. Reusing the same client request id for a different basis must fail;
replaying the same basis may return the existing receipt.

## Per-Filing Isolation

Every planned filing slot must resolve to exactly one state:

- `supported`: official resolution succeeded, filing acquired under preflight,
  inline facts were parsed, Arelle sidecar was selected as fact authority,
  completeness checks passed, and handoff/export prepare reached ready state.
- `degraded`: official resolution or filing acquisition succeeded, but the
  filing is sparse, current-report-only, no-inline, pre-inline-era, or otherwise
  diagnostic rather than fully supported.
- `blocked`: preflight failed, storage failed, rate policy was not admitted,
  official ticker resolution failed, filing metadata was unavailable, taxonomy
  support was not provisioned, standalone XML/XBRL was unsupported, or another
  fail-closed guard stopped the slot.

The following reason codes are admitted by this plan. Codes marked "hardening"
come from the parallel hardening mandate and must be accepted by the future
proof-import schema even if current main does not yet emit them:

- `supported_inline_xbrl_sidecar_selected`
- `foreign_private_issuer_sparse_6k_diagnostic`
- `official_ticker_resolution_missing`
- `ticker_alias_resolution_required`
- `likely_no_sec_company_filings`
- `storage_preflight_failed`
- `rate_policy_noncompliant`
- `source_artifact_size_cap_exceeded`
- `companyfacts_oracle_unavailable`
- `supported_filing_shortfall_explained`
- `taxonomy_year_unprovisioned` (hardening)
- `no_inline_facts_pre_inline_era` (hardening)
- `standalone_xml_xbrl_unsupported` (hardening)

## Sanitized Proof Import Schema

Schema id:
`diagnostics.sec_xbrl_corpus_run_sanitized_import.v1`.

Mode:
`operator_sanitized_proof_import`.

Allowed run-level fields:

- `schema_id`
- `mode`
- `run_namespace`
- `repo_main_sha`
- `operator_report_hash`
- `rate_policy_id`
- `configured_requests_per_second`
- `observed_request_count`
- `pacing_log_hash`
- `storage_root_marker`
- `storage_preflight_hash`
- `redaction_scan_policy_id`
- `redaction_scan_hash`
- `supported_filing_count`
- `issuer_hash_count`
- `required_forms_present`
- `shortfall_reason_codes`

Allowed ticker record fields:

- `ticker_symbol`
- `static_expected_sec_posture`
- `resolution_state`
- `resolution_source_hash`
- `cik_hash`
- `issuer_hash`
- `named_disposition`
- `reason_codes`

Allowed filing record fields:

- `ticker_symbol`
- `form_type`
- `filing_date_public`
- `filing_period_year_public`
- `form_family`
- `filing_slot_id`
- `cik_hash`
- `issuer_hash`
- `source_artifact_receipt_hash`
- `sidecar_receipt_hash`
- `validation_record_hash`
- `delivery_status_record_hash`
- `supported_degraded_blocked`
- `reason_codes`
- `resolved_fact_count`
- `independent_inline_fact_count`
- `value_redacted_fact_count`
- `policy_ids`

Forbidden fields in committed proof import:

- raw fact values, amounts, effective values, lexical values, and residual
  magnitudes;
- raw CIK in v1, even though it is public, because the current generic guard
  treats CIK as raw authority unless a schema-specific exception is created and
  tested;
- accession numbers and accession-like strings;
- SEC URLs, source URLs, local paths, storage directories, and artifact bytes;
- company names, issuer names, registrant names, operator contacts, User-Agent
  values, credentials, browser/model state, raw SEC submissions payloads, raw
  CompanyFacts payloads, and raw Arelle output.

Public identifier decision:

- Position A: Admit only hashes because the current generic guard treats ticker,
  CIK, accession, path, URL, and dates as potentially raw authority.
- Position B: Admit some public fields because this run is impossible to inspect
  without stable human-readable ticker/form/date labels.
- Ruling: v1 admits `ticker_symbol`, `form_type`, `form_family`,
  `filing_date_public`, and `filing_period_year_public` as schema-specific
  public metadata. It does not admit raw CIK or accession. A future importer may
  admit raw public CIK only after a narrow policy update and conformance test.

Rate decision:

- Position A: Use the existing one-request-per-second posture because it is the
  current runner baseline.
- Position B: Plan for approximately two requests per second because the service
  policy admits 1 to 10 and the corpus run is bounded.
- Ruling: the operator plan selects about two requests per second when the entry
  point honors configuration; otherwise, one request per second remains the
  compliant fallback. The proof report must log the actual configured and
  observed pacing.

## Run-Level Gates

The operator proof is complete only when all gates are satisfied or a named
shortfall is explicitly justified:

1. All 30 public tickers have a named final disposition.
2. Every selected filing slot is `supported`, `degraded`, or `blocked`; no null
   or missing states.
3. Redaction scan is clean under the proof-import policy.
4. Storage preflight passed before acquisition and recorded hash/count-only
   evidence.
5. Rate compliance is logged: policy id, configured rate, observed request
   count, pacing log hash, and any fail-closed deferrals.
6. Supported records meet or exceed the current in-repo minimums of 30 filings
   and 15 issuer hashes, or the proof records an explicit justified shortfall
   caused by named no-resolution/no-filing/unsupported dispositions.
7. Required form-family coverage is recorded. A shortfall must name whether the
   matrix lacked annual, interim/current, foreign private issuer, sparse 6-K,
   current-report, amendment, or no-inline/zero-fact diagnostic coverage.
8. Every supported filing has Arelle sidecar selected as fact authority and
   reaches handoff/export prepare readiness.
9. Completeness checks show zero silent truncation for supported filings.
10. The proof states that it does not authorize value reveal, production
    readiness, default flips, redaction-posture changes, schema/persistence
    changes, or raw artifact publication.

## Explicit Non-Authorization

This plan does not authorize:

- live SEC network calls by an agent;
- committing the owner source list file;
- committing raw CIKs, accessions, SEC URLs, local paths, storage roots beyond
  the public `C:/p6store` marker, User-Agent values, contacts, artifact bytes,
  raw values, or raw SEC payloads;
- default-on corpus validation, nonlocal authorization, value reveal, controlled
  submit activation, production-readiness claims, runtime/schema/persistence
  changes, or redaction-posture changes;
- increasing source-artifact size caps without a per-filing operator rationale;
- treating static ticker expectations as live SEC authority before the operator
  resolver phase.
