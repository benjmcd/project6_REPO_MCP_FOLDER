# ScienceBase v1.3.3 Pilot Runbook

## Purpose
Operational runbook for the Annual MCS pilot gate using the public-read ScienceBase connector.

## Preconditions
- API is running with migrations applied through `0006_connector_run_core_counters`.
- ScienceBase connectivity is available from the API runtime.
- Pilot scope is Annual MCS only (`mcs_release_mode=annual_release`).

## Run Submission and Replay
1. Submit via `POST /api/v1/connectors/sciencebase-mcs/runs` with `Idempotency-Key`.
2. On client retry:
   - same key + same payload returns existing run.
   - same key + different payload returns `409`.
3. Poll `GET /api/v1/connectors/runs/{id}` until terminal.

## Cancellation and Resume
1. Cancel with `POST /api/v1/connectors/runs/{id}/cancel`.
2. Wait for run status `cancelled`.
3. Resume with `POST /api/v1/connectors/runs/{id}/resume`.
4. Validate resumed run reaches terminal without non-terminal leftovers.

## Lease Conflict Handling
1. If run `error_summary=lease_conflict`, inspect `GET /runs/{id}/events`.
2. Confirm only one active executor instance owns the lease.
3. Resume the run once lease contention is resolved.

## Budget Exhaustion Handling
1. If `budget_blocked_count > 0` or `budget_summary.budget_exhausted=true`, run completed with budget limits hit.
2. Increase `max_run_bytes` and/or `max_file_bytes` in next submission when appropriate.
3. Keep previous run for audit; do not mutate historical artifacts.

## Reconciliation Interpretation
- Reconciliation-only statuses (`missing_upstream`, `removed_from_item`, `superseded`, `withdrawn`, `out_of_scope`) are terminal and do not enter downloader/ingest.
- Review `reconciliation_summary` and `targets_failures.csv` for operator actions.

## Report Triage Order
1. `GET /api/v1/connectors/runs/{id}` for top-level status and counters.
2. `GET /api/v1/connectors/runs/{id}/events` for stage timeline and reason codes.
3. `GET /api/v1/connectors/runs/{id}/reports` and inspect:
   - `run_summary.json`
   - `targets_failures.csv`
   - `targets_selected.csv`
   - `versioning_decisions.csv`

## Live Pilot Gate
Run:

```powershell
py -3.12 tools/run_sciencebase_live_pilot_validation.py --base-url http://127.0.0.1:8000 --consecutive-runs 3 --timeout-seconds 600
```

Gate passes only if:
- three consecutive suite cycles pass,
- no run is stuck/non-terminal,
- operator surfaces are complete (`/runs`, `/targets`, `/events`, `/reports`),
- at least one run in the gate window proves conditional no-op through either:
  - `not_modified_remote` (HTTP 304), or
  - `skipped_unchanged_after_conditional_revalidate` (conditional request sent, upstream returned unchanged content with HTTP 200).

Validator JSON summary fields:
- `failed_cycles`: suite cycles that had one or more failed scenarios.
- `missing_conditional_noop_gate`: true when no accepted conditional no-op evidence was observed.
- `failed_gate_checks`: aggregate gate failure count (`failed_cycles` plus conditional-noop gate miss).

Note:
- The live validator attempts bounded automatic resume for runs that finish with retryable non-terminal targets before deciding pass/fail.

## Freeze/Tag
After gate pass:
1. Freeze connector changes.
2. Tag release `v1.3.3`.
3. Record pilot evidence bundle (validator output + report references).

## Prospective exact fresh-byte campaign boundary (2026-07-29)

The v1.3.3 pilot above and the proposed dual-live proof answer different
questions. Neither supersedes the other.

### Existing v1.3.3 pilot

- Exercises a recurring operator workflow over multiple cycles.
- Admits conditional requests, `304`, and unchanged-after-`200` no-op evidence.
- Permits bounded resume.
- Demonstrates recurrence, operator surfaces, and reconciliation behavior.

### Proposed dual-live ScienceBase proof

- Uses only exact item `63d1a3c6d34e06fef15006be`.
- Requests exact filename `mcs2023-germa_salient.csv`; the authorized item JSON
  must confirm exactly one match or the run stops.
- Strictly decodes UTF-8 JSON with duplicate object-member rejection. The one
  selected file must have exactly one nonblank untrimmed `downloadUri`; missing,
  duplicate, `url` fallback/dual locator, whitespace/control, or disagreement
  stops before URL normalization.
- Admits only the exact returned file URL shape
  `/catalog/file/get/63d1a3c6d34e06fef15006be` and raw ASCII query
  `f=mcs2023-germa_salient.csv`, both byte-for-byte before strict UTF-8 pair
  confirmation. Empty/trailing/repeated separators, `;`, `+`, `%` encoding,
  missing/extra `=`, alternate keys, path encoding, raw `@` authority, or any
  `#` delimiter stops before the artifact send; no permissive query-helper
  normalization grants authority.
- Makes no search request.
- Sends no conditional header and rejects `304`.
- Permits no resume, recurring sync, automatic retry, or automatic redirect.
  A separately reserved redirect is considered only for
  `301`/`302`/`303`/`307`/`308` with exactly one raw `Location` from a lossless
  header multimap; every other `3xx` or missing/duplicate locator stops.
- Requires a newly retrieved complete `200` CSV and binds its SHA-256 through
  connector provenance, Layer 3C descriptive-summary execution, review, three
  packages, package submission, and internal handoff preparation.
- Requires a protected strict campaign definition/raw digest/rederived
  fingerprint plus exact server-loaded owner grant bytes/digest, a separately
  committed parent arming, hash/class-only derived artifact arming, and a
  per-send physical-request ledger. The definition is deny-only correlation;
  the connector grant remains egress authority.
- Binds one UUID4 nonce and `max_armings=1` into a deterministic parent-run ID,
  then atomically creates one digest-keyed no-overwrite consumption marker.
  Another client key, run state, or isolated database cannot reuse the grant;
  marker-only failure is spent and requires a new definition/campaign plus an
  explicitly superseding grant. Same-campaign recovery is forbidden.
- Preserves the verified non-secret definition/grant bytes through protected,
  content-addressed campaign-evidence-index revisions. Exact predecessor links,
  strict-superset successors, a unique-maximal-head check, and no-overwrite
  creation make rollback/fork/drop fail closed. Each revision introduces exactly
  one complete campaign slice, and arming requires that slice's earliest
  revision to be the current head; a preserved ancestor is historical-only even
  if unused. The arming, log seal, and both connector events bind that
  introduction revision/digest. Later validation survives expiry/rotation
  without letting historical evidence authorize another send.
- Keeps the exact artifact URL process-memory-only. Strict-lane
  `sciencebase_download_uri` and alias URL scalars remain null, raw item/`files[]`
  snapshots and URL-bearing intake metadata do not persist, and only a URL
  digest plus the admitted scheme/host/port/path/query class crosses a storage
  boundary. Custody validation covers scalar, text, JSON, and generated
  non-source files plus exactly four protected runtime log streams whose
  manifest is anchored by a separate no-overwrite seal and matching events on
  both connector runs, scanning raw and escaped forms. The acquired CSV remains
  an opaque hash-bound source; OS/provider logs and cryptographic
  nonrepudiation remain production-promotion boundaries.

The proposed mode is documented in:

- `docs/campaign-records/2026-07-29-dual-live-proof.md`;
- `docs/superpowers/plans/2026-07-29-dual-live-proof.md`.

Current status is planning only. This section is not an owner grant, does not
enable the mode, and does not alter the v1.3.3 gate or tag.
