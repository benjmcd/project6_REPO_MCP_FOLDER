> Tracked connector-program execution record, frozen at PR #2465 (program state = main `e7e887aa` / #2464). Sources: the nine untracked inbox files `state/agent-inbox/wb-connector-source.md` sha256 `078ee827973edf87d6eea836fea654d6688d948e5f4d70fe15344827d608f7ee`; `state/agent-inbox/cftc-connector-source.md` sha256 `f54cc94b58097158fd3e14d7ed510841b1a24f192f4fbddee3d478914282aef0`; `state/agent-inbox/usgs-mcs-source.md` sha256 `71c8d8fe31753c958543ad1c14b3ddcf4b0d5cfa06b8a3a037431eb4c1debba4`; `state/agent-inbox/bls-connector-source.md` sha256 `0fad36a4bac42c85f160ea0238ac94a933d7b5c001c479fb6b66952aa0017834`; `state/agent-inbox/oecd-connector-source.md` sha256 `f23a526610ddb61a0402e11083b1f488ef91aeecf9a33313896a968a2d3e6618`; `state/agent-inbox/imf-connector-source.md` sha256 `6770142c3ea0ea926c1ad501e14bb956b8213572e57d9e11df84da4c046b4937`; `state/agent-inbox/wb-polish-source.md` sha256 `8752ec191b45fa104b56651af46a16ac42c0839470c4fd84ecc990f9427594d5`; `state/agent-inbox/source-conditions-research.md` sha256 `8189817e62058e3ff182392b8151dd00549fb6f6d84debd791316f78cfb20237`; `state/agent-inbox/wb-landing-adversarial-source.md` sha256 `9b1c1052044a989b3a970296fffc93eeeb0496202b04908b67c22d96485168bf`. This tracked copy publication-normalizes role and model labels while preserving the claims. This is a dated EXECUTION record subordinate to `docs/MASTER_CONTEXT.md` and `docs/program-context/` (D10: not a second master context). Sibling records in this folder include `docs/campaign-records/2026-07-07-source-candidates.md`.

# Connector Program Execution Record

This tracked record freezes the connector-breadth execution chain after the World Bank, CFTC, USGS MCS, BLS, OECD, IMF Phase-0, and World Bank polish lanes. It records what landed, what stopped, what remains owner-gated, and how the frozen source mandates map to the committed program state.

---

## 1. Execution Table

| wave | source | PR | merge SHA | capability | key posture |
|---|---|---:|---|---:|---|
| 1 | World Bank Indicators | #2459 | `2a697131` | 29 | keyless, CC BY 4.0 attribution carried in reports |
| 2 | CFTC COT public reports | #2460 | `78837774` | 30 | keyless file-path report rows, no live file downloads in build lane |
| 3 | USGS MCS data release seam | #2461 | `cd7e4088` | 30 | explicit item ids through existing ScienceBase public connector seam |
| 4 | BLS Public Data API v1 | #2462 | `2c95e1d0` | 31 | v1 anonymous, caps encoded as code |
| 5 | OECD SDMX | #2463 | `4d541677` | 32 | SDMX-CSV anonymous slice with 60-downloads/hour residual owner responsibility |
| polish | World Bank hardening | #2464 | `e7e887aa` | 32 | redirect, normalization, and counter hardening; capability count unchanged |

The PR numbers, merge SHAs, merge state, and capability-count progression were re-derived from GitHub PR state and local Git before this table was written.

## 2. IMF Owner Gate

The IMF DataMapper lane stopped at Phase 0. The official help page pinned the v2 URL grammar, the one-request-per-indicator request model, and no key or registration parameter for the DataMapper help grammar. It did not publish the response envelope example required by the parser mandate, so the lane failed closed instead of inventing a fixture from unstated behavior.

The pending owner decision is a named D27 grant for one or two ledgered envelope-pin GETs to `www.imf.org/external/datamapper/api/v2`, after which the rev-2 mandate can be re-dispatched unchanged if the envelope is pinned. The IMF terms posture carries the anti-bulk boundary verbatim: "prohibits the bulk download of information by automated technology".

## 3. Defer-Final Sources

| source | current disposition | attempt-ledger pointer |
|---|---|---|
| FAO / FAOSTAT | defer-final; the documentation/auth path was not resolved enough for a Tier-1 anonymous connector mandate | `state/agent-inbox/source-conditions-research.md` FAO entries and web ledger |
| BTS / DOT | defer-final; DOT developer resources were identified, but BTS API auth/rate terms stayed unresolved | `state/agent-inbox/source-conditions-research.md` BTS/DOT entries and web ledger |

## 4. D27 Live-Pilot Sketch

This table is a SKETCH for owner-facing D27 decisions. It is not itself a grant, arming record, or permission to run live pilots.

| connector | host class | suggested pilot budget | fixture-model note |
|---|---|---:|---|
| World Bank | `api.worldbank.org` | 15-20 requests with retry reserve | API JSON fixtures with attribution and null/empty/error cases |
| CFTC COT | `www.cftc.gov` | about 12 requests, or two-scenario reduced pilot around 8 | public report text/CSV-shaped fixtures plus unavailable and malformed cases |
| USGS MCS | `sciencebase.gov` established class; `data.usgs.gov` optional new class | class-specific grant required for any optional new host | ScienceBase metadata/item-id fixtures; data-host access remains separately gated |
| BLS v1 | `api.bls.gov` | small pilot inside 25/day terms envelope | single and multi-series response fixtures plus 429, unauthorized, and malformed cases |
| OECD SDMX | `sdmx.oecd.org` | no more than 30 per run under 60/hour residual | SDMX-CSV fixtures with dataflow, restricted-parameter, redirect, and empty cases |
| IMF DataMapper | `www.imf.org` DataMapper v2 | 1-2 envelope-pin GETs before any pilot | first fixture must pin the official response envelope; pilot remains blocked until then |

## 5. Frozen Sources

The following source texts are copied from the frozen inbox source set in binding order. Publication normalization has removed role/model labels, local-user paths, and thread identifiers while preserving lane names, source paths, tool-failure names, and `C:/p6store` class paths. Acceptance scan over this tracked record was required to produce zero hits for the lane-provided normalization pattern.

### 5.1. Wave 1 - World Bank connector mandate

Source path: `state/agent-inbox/wb-connector-source.md`  
Frozen sha256: `078ee827973edf87d6eea836fea654d6688d948e5f4d70fe15344827d608f7ee`

# M-CONNECTOR-WORLDBANK-OFFLINE — Lane source (Tier-1 IMPLEMENTATION: World Bank Indicators anonymous connector, OFFLINE-COMPLETE, zero egress, zero new tables)
(rev 2 — 2026-07-07; adversarially pre-reviewed by two independent critics [1 BLOCKING + 5 MATERIAL fixed]; supersedes rev 1 in full. Decisions + checklist derive from the triple-reviewed source-candidates chain: dossier -> adjudication REV-2/REV-3 -> adversarial review. Those docs are EVIDENCE BASE; THIS file is the executable mandate.)

## Objective
Implement the World Bank Indicators API anonymous public connector as a fully OFFLINE-PROVEN
Tier-1 unit: service module + typed schema + gated POST route + dispatch entry + config +
support-matrix surfaces + docs front-door + fixture-backed tests. ZERO live network calls to
worldbank.org in this lane (hard STOP) — the live pilot is a FUTURE lane gated on a named D27
owner grant (api.worldbank.org is a new host class; not covered by generic delegation).

## Pre-made decisions (do NOT re-open)
1. SOURCE: World Bank Indicators API v2 (keyless — verified: "API keys and other
   authentication methods are no longer necessary"; license CC BY 4.0, attribution format
   "The World Bank: Dataset name: Data source").
2. DISPATCH PATTERN: Senate-style service module (backend/app/services/connectors_worldbank.py).
   PRECISION (critic-verified): "senate-style" means the CLIENT LAYER ONLY (HTTP client,
   _RateLimiter, backoff, error classification) is copied in-module; the lease/cancel/finalize/
   run-event/provenance lifecycle helpers are IMPORTED from connectors_sciencebase EXACTLY as
   connectors_senate_lda.py:26-38 does (_acquire_lease, _cooperate_with_cancel_request,
   _finalize_run, _record_run_event, _release_lease, _renew_lease, _write_json,
   SubmissionConflictError, ExecutorGuards) — NEVER re-implemented (forking lease semantics
   inside Tier-1 is forbidden). Do NOT refactor/extract anything from the senate module (its
   monkeypatchers + rc2 node-id pins forbid touching it; dedup is a future cleanup candidate,
   note it in the closeout).
3. SURFACE POLICY: metadata_only, official_api_only, allowed_hosts=["api.worldbank.org"],
   max_rps<=2.0 token-bucket, https-only + SSRF private-IP rejection (senate/sciencebase mold).
   Zero new tables: alias onto ConnectorRun/ConnectorRunTarget/Dataset/DatasetSourceProvenance/
   DatasetVersion exactly as connectors_senate_lda.py does (:16-38, :351-365, :899-906).
4. ATTRIBUTION: record CC BY 4.0 + the attribution string + ToS URL
   (data.worldbank.org/summary-terms-of-use) in DatasetSourceProvenance and the run
   report/observability projections wherever senate records source terms.
5. VALIDATION CHAIN THIS LANE: offline tests only. NO live-pilot validator work, NO
   project6.ps1 action changes, NO validator generalization (deferred to the live-pilot lane).

## Authority + isolation
Fetch fresh project6-origin/main and branch worktrees/wb-connector on the WB implementation branch from
the live tip (a parallel docs lane M-SOURCE-RECORD-LAND may advance main mid-PR — rebase
normally; fences are disjoint: that lane touches only docs/campaign-records/ +
docs/program-context/04-evidence-registry.md). Root checkout = preserved dirty state, never
edit from it. Stage exact paths only; never git add -A; no Co-Authored-By/AI trailers.

## File fence (the COMPLETE landing surface; nothing else)
NEW:  backend/app/services/connectors_worldbank.py
EDIT: backend/app/api/router.py            (typed POST route + _connector_executor dispatch entry;
                                            in-handler _route_level_operator_identity(request,
                                            access="write") EXACTLY as create_senate_lda_run,
                                            router.py:446-457 mold)
EDIT: backend/app/schemas/api.py           (typed request schema, senate mold :278-301)
EDIT: backend/app/core/config.py           (WORLDBANK_API_BASE_URL appended AFTER line 214 —
                                            test_support_matrix.py:127-143 dynamically asserts
                                            the senate/sciencebase alias line numbers in yaml
                                            evidence; appending after avoids breaking it.
                                            CRITIC-FOUND TRAP: inserting after :214 still
                                            SHIFTS every config.py:NNN>214 reference embedded
                                            in support_matrix.yaml evidence strings — these
                                            are NOT CI-checked (existence-only validation) so
                                            drift lands silently. In the SAME edit: grep the
                                            yaml for every config.py:NNN reference > 214
                                            (known: nonlocal_multi_trust_multi_identity cites
                                            config.py:370-404 at yaml ~:144) and re-point them
                                            to post-insert values. Verify live before editing.)
EDIT: backend/main.py                      (add (f"{p}/connectors/worldbank/runs", "write") to
                                            _build_static_pre_body_routes _exact list, ~:286-292)
EDIT: backend/.env.example                 (commented # WORLDBANK_API_BASE_URL=... block
                                            APPENDED AT END OF FILE (after current line 100) —
                                            do NOT insert beside the senate block at :48-50:
                                            yaml evidence cites .env.example line ranges
                                            :47-49 and :62-99 which would silently shift)
EDIT: config/support_matrix.yaml           (new capability entry + BOUNDARY_NOTE wording update —
                                            it currently bounds public connectors to
                                            "ScienceBase public/MCS and Senate LDA anonymous
                                            metadata only"; extend honestly)
EDIT: scripts/support_matrix_constants.py  (mirror ids/statuses/markers)
EDIT: scripts/support_matrix_check.py      (only if it enumerates ids — verify)
EDIT: scripts/support_matrix_runtime_contract_audit.py (NEW probe fn in the _senate_runtime mold
                                            (~:328; ~60-70 LOC: stub SessionLocal, client getter,
                                            time.sleep, _RateLimiter.wait) + PROBES entry — the
                                            audit FAILS CLOSED on undeclared capability ids)
EDIT: backend/tests/test_support_matrix.py (EXPECTED_CAPABILITY_STATUSES exact dict + PR marker
                                            requirements + boundary-token guards :68-91)
EDIT: backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py
                                           (capability_count 28 -> 29 + exact per-status lists)
EDIT: tests/test_api.py                    (new tests APPENDED; root tests/ auto-collects — do
                                            NOT create a new backend/tests file, which would
                                            require extending the workflow pattern tuple + its
                                            fail-closed mirror; do NOT rename/move ANY existing
                                            senate/sciencebase test: rc2_public_connectors_
                                            acceptance.py pins their exact node ids)
EDIT (conventional): backend/tests/test_legacy_api_operator_identity.py (add route to the
                                            parametrized 401 list, :117 senate mold)
EDIT docs front-door (only truth-claims that change): README.md (active tracks + endpoint list;
     guarded by tests/test_readme_frontdoor_truth.py), docs/support-matrix-local-expert.md,
     docs/first-boot-capabilities.md, docs/public-connectors-journey.md. REPO_INDEX.md optional
     one-line alignment.
CONDITIONAL (in-lane determination, report the branch taken WITH evidence):
- SUPPORT STATUS: inspect what evidence class senate_lda_anonymous_connector_slice's
  "supported" status rests on. Critic pre-verification: senate's yaml evidence
  (support_matrix.yaml:34) cites offline test node-ids + config lines + PR markers ONLY (no
  live-pilot artifact) — so the SUPPORTED branch is the expected outcome. If supported:
  evidence string MUST follow the senate format exactly — semicolon-separated test node-ids +
  config.py line ref + docs ref + the FIVE LITERAL TOKENS "PR-1 ...", "PR-2 ...", "PR-3 ...",
  "PR-4 ...", "PR-5 ..." (support_matrix_check.py:178-186 enforces the literal tokens via
  PUBLIC_CONNECTORS_REQUIRED_EVIDENCE; do NOT replace them with node-ids). If (contrary to
  pre-verification) senate's support demonstrably rests on live-pilot artifacts, the honest
  lower status is **experimental_default_off** — STATUS_VOCABULARY = {supported,
  experimental_default_off, simulation, unsupported}; there is NO "deferred" token and you
  must NOT invent one — mirrored identically in support_matrix_constants.EXPECTED_STATUS_BY_ID,
  test_support_matrix.EXPECTED_CAPABILITY_STATUSES, the exhaustive test's
  experimental_default_off list, with a live-pilot upgrade note in yaml evidence + boundary
  note. Do not fabricate parity either direction.
- scripts/rc3_sec_xbrl_offline_acceptance.py: extend its public-connector node-id groups ONLY
  if the supported branch is taken AND the file's own convention requires the new connector
  (read the RC2_PUBLIC_CONNECTOR_REGRESSION_TESTS list at ~:117-141 first); otherwise leave
  untouched and record why.
- scripts/support_matrix_check.py: critic pre-verified it derives all sets from
  support_matrix_constants imports and hardcodes no connector ids — expected NO edit; record
  that as the branch evidence.

## Implementation requirements
- Client: WB Indicators v2 REST/JSON. format=json, per_page pinned high (e.g. 1000) to
  minimize pagination. Endpoints for the pilot slice: source/indicator metadata + country
  query + indicator series observations (3-5 fixture shapes total).
- FIXTURES: in-file fake clients in tests/test_api.py (senate mold, :7133-7185) hand-authored
  from the OFFICIAL API documentation examples — NOT captured live. No on-disk fixture files.
  Fixture bodies must contain zero machine-local paths / operator identity / real request
  headers (they will be leak-scanned).
- Rate limiter: token-bucket ~2rps + Retry-After-honoring backoff + terminal-vs-retryable
  per-target classification (copy senate :145-159, :164-177, :180-194 semantics).
- Error surface: reuse the senate error-classification taxonomy; empty-result and malformed-
  response paths FAIL CLOSED into blocked/error target states, never fabricate rows.
- requests_total accounting per attempt (senate :227-229) — the future D28 ledger depends on it.

## Tests (8-12 new, all offline; APPEND to tests/test_api.py)
happy-path submit->execute->targets/report; pagination handling; empty result fail-closed;
malformed payload fail-closed; rate-limiter/backoff behavior (monkeypatched clock); 401
operator-identity rejection (parametrized list + direct); lease/idempotency-conflict if the
senate lifecycle mold carries them; support-matrix mirrors green (test_support_matrix.py +
exhaustive runtime-contract test + runtime probe); POST-enumeration cross-check green.

## Hard STOP conditions (stop + report, never improvise)
S1 any live network call to any worldbank host (this lane is zero-egress by definition);
S2 any need for a new table/migration/raw-content persistence (breaks Tier-1 — escalate);
S3 any discovery that the WB v2 API path chosen requires a key/registration (contradicts the
   verified basis — report with evidence, do not work around);
S4 boundary-note/support-matrix guard conflicts unresolvable inside the fence;
S5 red CI after bounded re-runs (investigate, never force-merge);
S6 any required context stuck Expected/pending 30+ min after runs complete;
S7 the fence proves insufficient (a file outside it genuinely must change) — STOP, report the
   exact file + why; do not silently expand scope.

## Known-green guards + operational notes (critic-added; prevents misdiagnosis)
- backend/tests/test_honesty_machinery_coherence.py cross-checks yaml/constants/PROBES
  dynamically — it needs NO edit and passes once all three surfaces carry the worldbank entry
  consistently. If it fails, one of the three is OUT OF SYNC — that is NOT an S7
  fence-insufficiency; fix the desync.
- The new runtime probe must return a NON-EMPTY payload dict (exhaustive test asserts
  runtime_probe != {} per capability).
- A parallel docs lane (M-SOURCE-RECORD-LAND) runs concurrently: retry transient git
  lock/worktree-add errors ONCE before reporting; write your inbox closeout as ONE
  atomic append and re-read the tail to confirm both lanes' report headers survive.
- S6 nuance while two PRs share CI runners: distinguish QUEUED (pending, runner backlog — not
  stuck; keep waiting) from STARTED-THEN-SILENT (stuck; STOP applies). The 30-min window
  starts when triggered runs COMPLETE, not from PR creation.

## Verification chain (self-verify each; orchestrator re-verifies independently)
- Local: targeted pytest slices SERIAL (no xdist) per hardware rail; python -m json.tool on
  yaml-adjacent JSON if any; git diff --check; added-line leak scan (machine-local paths,
  operator identity, AI/vendor branding, secrets, CIK/accession, raw financial values —
  fixture bodies included; public indicator VALUES in fixtures are fine per retention posture).
- PR: title suggestion "feat: add World Bank anonymous public connector (offline-proven)".
  Body: decisions, fence, supported-vs-deferred branch taken + evidence, attribution posture,
  zero-egress statement. CI gate: three required contexts (release-gate, test, root-tests)
  green; poll ~300s. Resolve ALL reviewThreads (re-query GraphQL to confirm resolution posted).
- Squash merge; detached post-merge proof at merge SHA: route present + gated (both auth tests
  green), capability count 29, probe present, boundary note updated, README/docs claims
  consistent, no senate test node-id changed (rc2 pin check), leak scan clean on merged diff.
- Closeout: append "## [From lane executor] M-CONNECTOR-WORLDBANK-OFFLINE REPORT" to
  the inbox closeout file + IPC reply. Remove lane worktrees; preserve branch refs.

## Non-goals (hard)
No live pilot / egress / D27-D28 artifacts. No validator or project6.ps1 changes. No senate/
sciencebase module refactors. No analysis-method additions. No new backend/tests files. No
layer3 manifest edits (no planning-claim changes). No support-matrix claims beyond what the
landed tests prove.

### 5.2. Wave 2 - CFTC connector mandate

Source path: `state/agent-inbox/cftc-connector-source.md`  
Frozen sha256: `f54cc94b58097158fd3e14d7ed510841b1a24f192f4fbddee3d478914282aef0`

# M-CONNECTOR-CFTC-COT-OFFLINE — Lane source (Tier-1 IMPLEMENTATION: CFTC Commitment-of-Traders anonymous connector, OFFLINE-COMPLETE, zero egress, zero new tables)
(rev 2 — 2026-07-07; adversarially pre-reviewed by two independent critics [2 BLOCKING + 5 MATERIAL fixed]; supersedes rev 1 in full. Template = the LANDED World Bank lane (PR #2459, 2a697131) + its conventions AS LANDED. ANCHOR-AGNOSTIC RULE: derive every line anchor and count LIVE from current main.)

## Objective
Implement the CFTC Commitment-of-Traders public connector as a fully OFFLINE-PROVEN Tier-1
unit. ZERO live data/file downloads from any cftc.gov host (hard STOP S1). Live pilot = future
lane gated on a named D27 grant. THIS lane includes ONE bounded Phase-0 documentation-page
read pass (research browsing, not corpus egress — see Phase 0).

## PHASE 0 — FORMAT PIN (gate; BEFORE any code)
The evidence chain pinned CFTC keylessness but NOT the file format. Before writing any code:
- Read 2-3 official CFTC doc pages ONLY (the COT Explanatory Notes page and the field-names /
  variable-definitions page(s) linked from the COT index/historical pages; HTTPS GET doc pages,
  NO file downloads, NO data endpoints; ledger each URL in your report — this fits the
  standing 4-page-per-candidate research budget, CFTC has used 1/4).
- PIN, with quoted excerpts: (a) column layout per chosen report variant(s) (futures-only and
  futures-and-options, long/short format), (b) header-row presence/shape for current vs
  historical comma-delimited files, (c) the exact non-HTML comma-delimited file URL pattern —
  CFTC_COT_API_BASE_URL's default is DERIVED from this, never guessed; record it as
  unverified-until-live-pilot in provenance/report surfaces.
- Append the format pin (quotes + URLs) to the inbox closeout file BEFORE first code.
- S8 (now a pre-code gate): if the three pins cannot be quoted from official pages, STOP and
  report — do not guess a column layout into fixtures and parser.

## Pre-made decisions (do NOT re-open)
1. SOURCE PATH: keyless comma-delimited COT report FILES on www.cftc.gov (verified keyless;
   PRE/Socrata path EXCLUDED this lane). allowed_hosts=["www.cftc.gov"].
2. SHAPE: file-download + in-memory parse connector. CURRENT documented format only; anything
   unrecognized FAILS CLOSED into a blocked/error target state with a clear reason (no
   format-archaeology code, no partial rows).
3. MODULE backend/app/services/connectors_cftc_cot.py — IMPORT/IMPLEMENT TABLE (binding;
   critic-derived from the landed molds — senate has NO download path, WB's client enforces
   https+host only; the DOWNLOAD leg must mirror sciencebase enforcement):
   IMPORT from app.services.connectors_sciencebase: _precheck_download_url,
     _classify_download_exception, and the lifecycle helpers exactly as the WB module does
     (_acquire_lease, _cooperate_with_cancel_request, _finalize_run, _record_run_event,
     _release_lease, _renew_lease, _write_json).
   IMPORT from app.services.sciencebase_connector (contracts/executor as WB does):
     DownloadResult, FetchPolicyBlockedError, SubmissionConflictError, ExecutorGuards,
     RUN_TERMINAL_STATUSES (whichever of these the WB module imports — mirror it).
   IMPLEMENT in-module: (1) CFTC fetch-policy dict {allowed_schemes:["https"],
     allowed_hosts:["www.cftc.gov"], max_redirects:settings.connector_max_redirects} — do NOT
     call _build_fetch_policy; (2) a download function mirroring
     ScienceBaseAdapter.download_artifact's body (stream, redirect-count cap ->
     FetchPolicyBlockedError, sha256, final_url/resolved_ip capture; sb mold ~:410-438);
     (3) the enforcement SEQUENCE mirroring _download_target: precheck(url) -> host slot ->
     download -> precheck(final_url) -> byte cap (sb mold ~:2010-2033); (4) in-module
     max_file_bytes check on len(DownloadResult.content), default 8MB (weekly files <5MB);
     (5) _RateLimiter/backoff/error-classification copied in-module (senate/WB mold),
     max_rps SCHEMA-ENFORCED via Field(default=2.0, le=2.0) (WB precedent api.py mold).
4. PERSISTENCE SHAPE (binding; the WB-landed shape — resolves the raw-persistence boundary):
   parse DownloadResult.content IN MEMORY; persist exactly (a) a metadata-only DatasetVersion
   (version_type="source_metadata", row_count + content_hash, NO row values in tables — WB
   mold connectors_worldbank.py ~:524-537), (b) the normalized rows in the connector report
   JSONs via _write_json to the manifests dir (WB selection-manifest mold ~:767-794 — parsed
   PUBLIC rows in reports are consistent with the retention posture and REQUIRED for report
   parity with WB; do not strip them), (c) DatasetSourceProvenance with source attribution
   (CFTC public data + COT index URL + the no-token statement + the Phase-0 doc URLs).
   FORBIDDEN CALLS (each persists raw bytes durably = S2): _write_raw_blob, _download_target,
   _run_target_pipeline, ingest_csv_bytes_to_dataset.
5. VALIDATION: offline tests only; no live-pilot/validator/project6.ps1 work.

## Fence (WB 19-file pattern mapped 1:1; derive anchors live)
NEW  backend/app/services/connectors_cftc_cot.py
EDIT backend/app/api/router.py (typed POST /api/v1/connectors/cftc-cot/runs + dispatch +
     in-handler _route_level_operator_identity(request, access="write"))
EDIT backend/app/schemas/api.py (request schema: report_variant Literal + optional market/
     exchange filter + max-rows cap + max_rps le=2.0)
EDIT backend/app/core/config.py (CFTC_COT_API_BASE_URL appended after the WB alias; EXACTLY
     ONE support_matrix.yaml anchor shifts: nonlocal_multi_trust_multi_identity
     config.py:371-405 -> 372-406 — re-point it in the same edit; verify no other >insert-line
     anchors exist at edit time)
EDIT backend/main.py (pre-body _exact entry (f"{p}/connectors/cftc-cot/runs", "write"))
EDIT backend/.env.example (commented sibling at EOF — file currently ends with the WB block)
EDIT config/support_matrix.yaml (capability cftc_cot_anonymous_connector_slice, status per the
     supported-branch logic [WB precedent: supported; experimental_default_off is the only
     honest lower token — NO "deferred" exists]; evidence string in the WB format INCLUDING
     the legacy-identity test ref; five literal PR-1..PR-5 tokens; BOUNDARY NOTE: extend
     honestly — CFTC delivers parsed report ROWS, not metadata: use wording like "CFTC COT
     anonymous public report rows only", never copy "anonymous metadata only" verbatim;
     preserve all guarded tokens)
EDIT scripts/support_matrix_constants.py + scripts/support_matrix_runtime_contract_audit.py
     (new probe fn, WB mold, non-empty payload dict) — support_matrix_check.py expected
     NO-EDIT (record as evidence)
EDIT backend/tests/test_support_matrix.py (EXPECTED_CAPABILITY_STATUSES +1; BOTH
     capability-iteration tuples; AND a line_number_for("CFTC_COT_API_BASE_URL")
     evidence-alias assertion in
     test_support_matrix_connector_evidence_points_to_actual_config_aliases — WB precedent;
     omitting it fails nothing = silent-staleness, so it is REQUIRED)
EDIT backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py
     (capability_count live+1 [29->30]; SORTED-LIST TRAP: coverage_by_status lists are
     sorted() — cftc_cot_... inserts ALPHABETICALLY FIRST in the supported list, BEFORE
     connector_run_observability, NOT appended after worldbank)
EDIT tests/test_api.py (8-12 tests APPENDED; in-file fake seam; fixture strings <=50 rows /
     <=25KB hand-authored FROM THE PHASE-0 PINNED FORMAT with doc-quote provenance comments;
     no on-disk fixtures; never rename/move existing tests)
EDIT backend/tests/test_legacy_api_operator_identity.py (parametrized entry AND the
     _POST_JSON_ROUTES count assert bump 25->26 — WB bumped 24->25)
REQUIRED (WB precedent — NOT conditional): scripts/rc3_sec_xbrl_offline_acceptance.py (append
     the CFTC tests/test_api.py::... node-ids to RC2_PUBLIC_CONNECTOR_REGRESSION_TESTS — only
     test_api entries count) + backend/tests/test_release_rc3_sec_xbrl_offline_acceptance.py
     (bump the exact-count assert 34 -> 34+N to match precisely)
EDIT docs front-door whose truth-claims change: README, docs/support-matrix-local-expert.md,
     docs/first-boot-capabilities.md, docs/public-connectors-journey.md

## Tests (8-12, all offline; include critic-mandated seams)
happy path submit->execute->rows->report; variant selection; malformed/unrecognized format
FAIL-CLOSED; empty report fail-closed; row-cap + byte-cap (low configured max against fixture
string); rate-limiter/backoff (monkeypatched clock; senate precedent tests/test_api.py:3076);
401 identity rejection; lease/idempotency conflict; support-matrix mirrors + probe;
POST-enum cross-check. DNS-LEAK SEAM (critic-found; WB never hit it because it never calls
_precheck_download_url): keep the policy precheck OUTSIDE the fake-able client so tests
exercise it; tests monkeypatch _resolve_host_ip VIA THE CFTC MODULE'S REFERENCE to a fixed
public IP or None; add one deterministic test that precheck rejects (a) a non-cftc host and
(b) a blocked-IP resolution. No test may perform a real DNS lookup.

## Hard STOPs
S1 any live download/data call to any cftc host (Phase-0 doc PAGES only); S2 tables/raw
persistence (incl. any FORBIDDEN CALL); S3 auth/key surprise; S4 guard conflicts; S5 red CI;
S6 stuck required context (queued-vs-stuck nuance); S7 fence insufficiency; S8 format
unpinnable in Phase 0 (pre-code gate).

## Known-green guards + operational notes
test_honesty_machinery_coherence.py needs NO edit (failure = your three surfaces desync);
probe returns non-empty dict; atomic single-append closeouts + tail re-read; retry transient
git locks once; serial pytest, no xdist; kill any stale pytest processes before worktree
removal (WB lane hit orphaned processes holding SQLite files).

## Verification chain (WB shape)
Local slices serial; git diff --check; added-line leak scan incl. fixture strings; PR "feat:
add CFTC COT anonymous public connector (offline-proven)" (no AI trailers; body: Phase-0
format pin summary + decisions + zero-egress statement); three required contexts green;
reviewThreads resolved (re-query); squash; detached post-merge proof (route gated, capability
30, probe present, boundary note honest, rc2/rc3 pins intact incl. exact-count asserts,
leak-clean); closeout "## [From lane executor] M-CONNECTOR-CFTC-COT-OFFLINE REPORT" + IPC reply;
remove lane worktrees, preserve branch refs.

## Non-goals
No PRE/Socrata path, no live pilot/egress/D27-D28 artifacts, no legacy-format parsers, no
validator/project6.ps1 changes, no module refactors, no new backend/tests files, no on-disk
fixtures, no ingest.py changes, no edits to scripts/rc2_public_connectors_acceptance.py (the
frozen pre-WB capstone — CFTC, like WB, relies on its support-matrix evidence + the rc3 list;
this is an EXPLICIT decision, not silence).

## ADDENDUM (2026-07-07) — template lessons from the WB-landing adversarial review (CLEAN
## verdict; these BIND this lane)
L1 REDIRECT POSTURE EVERYWHERE: every HTTP GET in the module (the file download AND any other
   fetch) carries the sibling-connector redirect posture — len(response.history) checked
   against settings.connector_max_redirects AND the final response.url host re-checked against
   the allowlist after each GET (~6 lines; sciencebase/nrc mold). The WB client lacks this
   (adjudicated MINOR there); do not clone the gap.
L2 STATUS-FILTER FIX: when copying _discover_targets/report scaffolding, compute any
   "completed" counters against the REAL terminal-status vocabulary (e.g. exclude
   'download_failed'), never the literal 'failed' (WB's :783 filter is dead code that counts
   failures; do not clone it).
L3 ALL-ROWS-NORMALIZE-AWAY = FAIL CLOSED: a downloaded file that parses but whose rows ALL
   normalize away must produce a failed/blocked target with a clear error class (e.g.
   empty_after_normalization), never a silent skip. Add a test for it (WB has this honesty
   gap for all-null observation pages; do not clone it).
L4 BASE-URL TRIPWIRE: the happy-path test asserts the canonical CFTC_COT_API_BASE_URL string
   exactly (WB's tests/test_api.py:8042 pattern) — proven the only drift detector under
   env-poison, and it fails as a clean assertion, never a network attempt.
L5 SEAM ARCHITECTURE: settings-only base_url (per-run config may never override authority),
   https+exact-host allowlist raised in client __init__, module-level monkeypatchable
   get_cftc_cot_client factory — the trio that made WB's offline purity mechanically provable.
L6 EVIDENCE ANCHORS: keep exact pytest node-ids + config file:line in the yaml evidence
   (survived adversarial replay character-exact); line-number anchors rot under edits above
   them — re-derive at commit time.

### 5.3. Wave 3 - USGS MCS seam mandate

Source path: `state/agent-inbox/usgs-mcs-source.md`  
Frozen sha256: `71c8d8fe31753c958543ad1c14b3ddcf4b0d5cfa06b8a3a037431eb4c1debba4`

# M-USGS-MCS-EXTEND-OFFLINE — Lane source (Tier-1: USGS Mineral Commodity Summaries reach via the EXISTING ScienceBase/MCS seam, OFFLINE-COMPLETE, zero egress)
(rev 1 — 2026-07-07; wave-3. This is NOT a new-connector lane: the sciencebase-mcs route exists, the boundary note already covers "ScienceBase public/MCS", and *.usgs.gov is already allowlisted. The lane pins the current MCS data-release targets and proves/extends the existing seam offline.)

## Objective
Make the existing ScienceBase/MCS connector demonstrably able to target the current USGS
Mineral Commodity Summaries data release (CC0, CSV tables): pin the exact ScienceBase item
IDs/download surfaces (Phase 0, metadata pages only), then land whatever MINIMAL offline
extension the pin shows is needed (presets/schema defaults/fixtures/tests/evidence refresh) on
the EXISTING sciencebase_public_connector_slice capability. Zero live downloads (hard S1).

## PHASE 0 — TARGET PIN (gate; before any code)
- Read 2-4 official catalog METADATA pages only (data.usgs.gov data-catalog entry and/or
  ScienceBase catalog item pages for the 2025/2026 MCS data releases; HTTPS doc/metadata pages,
  NO file downloads; ledger each URL). Budget note + provenance: the 4-per-candidate research
  budget is an orchestrator mandate-local rule (from the source-candidates investigation),
  extended here by the same authority to +4 pages for this pin pass; D27 owner-grants govern
  runtime/connector egress, NOT ledgered doc-page research reads. USGS cumulative page count
  (3 prior + up to 4 new) must be stated in the inbox closeout pin append.
- PIN with quoted excerpts: (a) the ScienceBase item ID(s) for the target MCS release,
  (b) whether the item + its CSV file attachments are reachable through www.sciencebase.gov
  catalog surfaces (existing host class) or ONLY via data.usgs.gov / other hosts (NEW host
  class -> record for the future D27 grant; the offline build proceeds either way),
  (c) the file inventory shape (names/count/approx sizes) sufficient to hand-author fixtures.
- Append the pin to the inbox closeout file BEFORE code. S8-analog: if item IDs cannot
  be pinned from official metadata pages, STOP and report.

## BRANCH RULE (decided by Phase 0; report the branch with evidence)
BRANCH A (near-certain — critic-verified): (1) EXPECTED ZERO schemas/api.py change —
  scope_mode="explicit_item_ids" + scope_values ALREADY expresses release targeting natively
  (schemas/api.py:168-190 base Literal incl. explicit_item_ids/explicit_dois;
  connectors_sciencebase.py _resolve_scope_items hydrates given IDs directly, discovery skips
  search; the MCS subclass inherits it; the force-appended systemType=Data Release filters are
  inert on the explicit path). A schema edit requires PR-body justification of why
  explicit_item_ids is insufficient — treat any urge to edit the schema as a signal you are
  doing it wrong. (2) in-file fixtures modeled on the pinned item/file metadata. (3) 4-8 new
  tests in tests/test_api.py. SEAM (critic-pinned): monkeypatch get_sciencebase_adapter on the
  sb module (tests/test_api.py:1563/2188 mold) with a duck-typed fake
  (search_page/hydrate_item/extract_artifacts/download_artifact); "fixture-ingest" means the
  FAKE adapter's download_artifact returns in-file CSV bytes (offline, zero egress) — the
  fence forbids EDITING pipeline code, not EXERCISING it through the fake; use
  run_mode="dry_run" variants for pure discover/select assertions (dry_run_skipped path).
  (4) support_matrix.yaml EVIDENCE refresh for sciencebase_public_connector_slice: append
  tokens as "; tests/test_api.py::<test_name>" (semicolon-separated; the runtime-contract
  audit resolves each token's path prefix to an existing FILE — node names unvalidated); do
  NOT touch the config.py:210 token, the first token, or the PR-1..PR-5 trailer; NO status
  change, NO new capability id, NO count change, NO boundary-note change; do NOT add tests to
  scripts/rc2_public_connectors_acceptance.py (frozen hardcoded surface). (5) docs touch ONLY
  pages whose truth-claims change.
BRANCH B: the pin shows the existing seam CANNOT express MCS-release targeting without a new
  route/module/capability -> STOP after Phase 0, report exactly what is missing; a new-surface
  lane needs its own pre-reviewed mandate (do not improvise one here).

## Fence (Branch A; strictly minimal)
tests/test_api.py (append only); config/support_matrix.yaml (evidence string of the EXISTING
sciencebase capability only); backend/app/schemas/api.py ONLY if a preset/default genuinely
needs it (justify in PR body); docs pages only where claims change; state/agent-inbox +
the inbox closeout file + IPC reply (untracked). NOTHING else — no new modules, no router/main/config.py
edits, no constants/audit/exhaustive-test edits (no capability change = no mirror edits), no
rc3/rc2 list changes unless a NEW test-node evidence convention requires it (justify).

## Binding lessons (from WB/CFTC adversarial reviews)
L4 tripwire pattern where a URL default is asserted; L6 evidence anchors re-derived at commit;
fixtures in-file <=50 rows/<=25KB, hand-authored from the Phase-0 pinned metadata with
doc-quote provenance comments; leak scan incl. fixture bodies; serial pytest; atomic closeout
append; retry git locks once; queued-vs-stuck S6 nuance.

## STOPs
S1 any live download/data call (metadata doc pages in Phase 0 only); S2 any new
table/raw-persistence; S4 guard conflicts; S5 red CI; S6 stuck contexts; S7 fence
insufficiency (incl. ANY temptation to edit mirror surfaces — that means you are in Branch B);
S8-analog Phase-0 unpinnable.

## Verification chain
Local serial slices; git diff --check; leak scan; PR "test: prove ScienceBase MCS data-release
reach offline" (or "feat:" if a schema default lands — title matches content); three required
contexts green; threads resolved (re-query); squash; detached post-merge proof (new tests
green at merge SHA, evidence string updated, capability count UNCHANGED at 30, boundary note
byte-identical); closeout "## [From lane executor] M-USGS-MCS-EXTEND-OFFLINE REPORT" + IPC reply;
worktrees removed, branches preserved.

## Non-goals
No new capability/connector/module/route; no data.usgs.gov host adoption (record-only if
Phase 0 surfaces it); no live pilot/egress; no boundary-note or count changes; no PDF paths.

### 5.4. Wave 4 - BLS connector mandate

Source path: `state/agent-inbox/bls-connector-source.md`  
Frozen sha256: `0fad36a4bac42c85f160ea0238ac94a933d7b5c001c479fb6b66952aa0017834`

# M-CONNECTOR-BLS-V1-OFFLINE — Lane source (Tier-1 IMPLEMENTATION: BLS Public Data API v1 anonymous connector, OFFLINE-COMPLETE, zero egress, zero new tables)
(rev 2 — 2026-07-08; critic-patched [4 MATERIAL]: POST method-split redirect policy, no-key enforcing test, daily-cap honesty split, runtime-host linkage. Template = WB (PR #2459) + CFTC (PR #2460) as landed, + lessons L1-L6, + the conditions-research verdicts. ANCHOR-AGNOSTIC: derive every count/line live; USGS may land first (counts hold regardless of order — critic-verified).)

## Objective
Implement the BLS Public Data API **v1** anonymous connector as a fully OFFLINE-PROVEN Tier-1
unit. ZERO live calls to any bls.gov host (hard S1) beyond the Phase-0 doc pages. Live pilot =
future lane gated on a named D27 grant.

## PHASE 0 — ENDPOINT PIN (gate; before any code; <=2 official doc pages, ledgered)
Pin from the official v1 signature/docs pages (www.bls.gov/developers/...): (a) the exact v1
runtime endpoint URL + host FQDN (expected api.bls.gov path family — DERIVE, never assume),
(b) the v1 request/response JSON shape (single + multi-series) AND the exact HTTP METHOD
matrix (which operations are GET vs POST-with-JSON-body) — the method matrix is PINNED here
and mirrored in the fake client, (c) confirmation v1 needs no key parameter. Quoted excerpts
appended to the inbox closeout file BEFORE code. S8-analog: unpinnable -> STOP.
HOST LINKAGE (binding): the module ALLOWED_HOST literal, the BLS_API_BASE_URL config default,
and the L4 tripwire assertion ALL use the Phase-0-pinned RUNTIME FQDN (expected api.bls.gov);
the www.bls.gov DOC host must never appear in any allowlist, default, or tripwire.

## Pre-made decisions (do NOT re-open; grounded in the RESOLVED-CLEAR research verdict)
1. V1 ONLY: the anonymous tier is API v1; v2/registration/keys are OUT OF FENCE permanently in
   this lane. Any code path that could send a registrationkey parameter = S3.
2. CAPS — HONEST SPLIT (critic-corrected; do not over-claim):
   CODE-ENFORCED: 25 series/query (schema Field(max_length=25) on the list — pydantic v2,
   needs the field_validator/model_validator import, first use in this schemas file);
   <=10-year span (model_validator(mode="after") cross-field check); 50 req/10s (the standing
   2rps min-interval limiter yields <=20 req/10s structurally — keep 2rps); per-run request
   budget = HARD schema cap Field(default=10, ge=1, le=25) with its own rejection test.
   Rejection tests assert 422s for 26 series and 11-year span.
   OPERATOR-LEVEL RESIDUAL (cannot be code without durable state = new table = forbidden):
   the 25 queries/DAY cap across runs. The boundary note AND provenance/report text must
   state plainly that daily-cap compliance across runs is operator responsibility — never
   imply code enforcement.
3. MOLD + METHOD-SPLIT REDIRECT POLICY (critic-corrected; the WB client has NO redirect
   check — the graft source for GET is connectors_cftc_cot.py:259-263):
   Client layer copied in-module (_RateLimiter/backoff/error-classification); lifecycle
   helpers IMPORTED from connectors_sciencebase (never re-implemented). _request_json gains
   method + json_body parameters per the Phase-0 method matrix (GET single-series;
   POST-with-JSON-body multi-series/year-ranged).
   GET: CFTC posture — allow_redirects=True, len(response.history) checked vs
   settings.connector_max_redirects, final-URL host recheck.
   POST: allow_redirects=False; ANY 3xx response is TERMINAL redirect_policy_violation — no
   tolerated hops (requests rewrites POST->GET on 301/302/303 and silently drops the JSON
   body; a redirected POST returning a well-formed wrong envelope would otherwise pass
   fail-closed checks). One test asserts the POST-3xx terminal path.
   Settings-only base_url; https + exact-host allowlist in client __init__; module-level
   get_bls_client factory (L5 seam trio).
4. PERSISTENCE: WB-landed shape — metadata-only DatasetVersion (source_metadata, row_count +
   content_hash), normalized observations in the connector report/selection JSON, provenance
   in DatasetSourceProvenance. FORBIDDEN CALLS unchanged (_write_raw_blob, _download_target,
   _run_target_pipeline, ingest_csv_bytes_to_dataset).
5. PROVENANCE TEXT (research-mandated): include access-date citation and the BLS no-vouch
   disclaimer language in provenance/report surfaces; record the ToS URL.
6. FAIL-CLOSED: 429/right-to-limit responses classify terminal-or-retryable per the mold and
   NEVER silently retry past the rate budget; empty series, all-null normalization (L3),
   malformed envelope -> failed target with clear error class. L2: real terminal-status vocab
   in every counter. L4: base-URL tripwire assertion in the happy-path test.

## Fence (the established 19-file-class pattern; derive anchors live)
NEW  backend/app/services/connectors_bls.py
EDIT router.py (POST /api/v1/connectors/bls/runs + dispatch + in-handler
     _route_level_operator_identity(request, access="write")); schemas/api.py (typed request:
     series_ids list max 25, start/end year with <=10-span validator, max_rps le=2.0);
     config.py (BLS_API_BASE_URL appended after the LAST connector alias; re-point any shifted
     support_matrix.yaml config.py:NNN>insert-line anchors in the same edit); main.py
     (pre-body _exact entry); .env.example (EOF sibling)
EDIT config/support_matrix.yaml (capability bls_v1_anonymous_connector_slice — NOTE sorted
     position: "bls_" sorts FIRST, before cftc_...; boundary-note honest extension naming the
     v1 anonymous tier + caps; WB-format evidence string incl. legacy-identity ref + PR-1..5
     literal tokens); scripts/support_matrix_constants.py; support_matrix_runtime_contract_
     audit.py (new probe, non-empty dict) — support_matrix_check.py expected NO-EDIT
EDIT backend/tests/test_support_matrix.py (dict +1, iteration tuples, line_number_for
     ("BLS_API_BASE_URL") evidence-alias assertion); test_layer3_support_matrix_runtime_
     contract_exhaustive.py (count live+1; alphabetical insert); test_legacy_api_operator_
     identity.py (parametrized entry + count assert live+1)
EDIT tests/test_api.py (9-13 tests APPENDED: happy single+multi series, cap-rejection tests
     [26 series -> 422; 11-year span -> 422; budget >25 -> 422], 429 fail-closed,
     empty/all-null/malformed fail-closed, rate-limiter clock test (CFTC clock-test mold),
     POST-3xx terminal redirect_policy_violation test, NO-KEY NEGATIVE TEST (senate no-key
     mold: the fake client RECORDS every request url/params/body; assert case-insensitive
     "registrationkey" appears NOWHERE across a happy single+multi run AND
     client.auth_mode == "anonymous"), 401, lease/idempotency, L4 tripwire; in-file fake
     client mirrors the Phase-0 method matrix, <=25KB strings, no live capture. Add
     "registrationkey" to the added-line leak-scan token list for this PR's diff.)
REQUIRED: scripts/rc3_sec_xbrl_offline_acceptance.py + backend/tests/test_release_rc3_sec_
     xbrl_offline_acceptance.py (append node-ids + bump exact count live+N)
EDIT docs front-door where truth-claims change (README, support-matrix-local-expert,
     first-boot-capabilities, public-connectors-journey)
Do NOT touch scripts/rc2_public_connectors_acceptance.py (frozen).

## STOPs (S1-S8 as established; S3 explicitly includes any key/registration parameter path)
## Known-green guards + ops notes (as established: honesty-coherence test no-edit; probe
## non-empty; atomic closeout + tail re-read; git-lock retry; serial pytest; stale-process
## cleanup before worktree removal; queued-vs-stuck S6)

## Verification chain (established shape; PR title "feat: add BLS v1 anonymous public
## connector (offline-proven)"; detached post-merge proof incl. capability count, alphabetical
## position, caps-rejection tests green, boundary note, rc pins, leak scan)
Closeout: "## [From lane executor] M-CONNECTOR-BLS-V1-OFFLINE REPORT" + IPC reply; worktrees removed,
branches preserved.

## Non-goals
No v2/key paths, no live pilot/egress/D27-D28, no validator/project6.ps1 changes, no module
refactors, no new backend/tests files, no on-disk fixtures, no rc2 edits.

### 5.5. Wave 5 - OECD connector mandate

Source path: `state/agent-inbox/oecd-connector-source.md`  
Frozen sha256: `f23a526610ddb61a0402e11083b1f488ef91aeecf9a33313896a968a2d3e6618`

# M-CONNECTOR-OECD-SDMX-OFFLINE — Lane source (Tier-1 IMPLEMENTATION: OECD SDMX anonymous connector, OFFLINE-COMPLETE, zero egress, zero new tables)
(rev 2 — 2026-07-08; critic-patched [2 MATERIAL: SDMX-CSV pre-committed; research-§2 carries pinned]. Template = WB/CFTC/BLS as landed + L1-L6 + conditions-research verdicts (OECD RESOLVED-CLEAR). ANCHOR-AGNOSTIC: derive every count/anchor live (capability = live+1; legacy-identity live+1; rc3 live+N; sorted position post-BLS = 7th of 10, between method_aware_ and sciencebase_). DISPATCH GATE: only after the BLS lane lands+verifies (serial-build rule).)

## Objective
Implement the OECD SDMX data connector as a fully OFFLINE-PROVEN Tier-1 unit against
sdmx.oecd.org. ZERO live calls to any oecd.org host beyond the Phase-0 doc pages (hard S1).
Live pilot = future lane gated on a named D27 grant.

## PHASE 0 — GRAMMAR PIN (gate; before any code; <=3 official doc pages, ledgered)
Pin from official OECD API docs: (a) the exact SDMX data-query URL grammar on sdmx.oecd.org
(agency/dataflow/key/params), (b) FORMAT = **SDMX-CSV, PRE-COMMITTED** (rationale: flat-row
parse grafts the landed CFTC csv mold [connectors_cftc_cot.py LEGACY_COT_FIELDS pattern];
SDMX-JSON is index-coded with NO in-repo mold and ~3x parser cost). Phase 0 pins the CSV
request mechanism (format parameter or Accept header — DERIVE from docs) and ONE complete
documented CSV example. If the documented CSV example is insufficient to hand-author fixtures
-> S9 STOP; do NOT fall back to SDMX-JSON — that is a mandate revision, not an executor
choice. (c) one small documented dataflow example (id + dimension shape) to model fixtures
on, (d) the structure/codelist query grammar IF needed (else record not-needed). Quoted
excerpts to the inbox closeout file BEFORE code. S8-analog: unpinnable -> STOP.
Phase-0 page budget is GRAMMAR-ONLY — all terms/413/registration URLs are pre-pinned in
decision 5; do not spend pages re-fetching them.

## Pre-made decisions (grounded in the research verdicts; do NOT re-open)
1. HOST: sdmx.oecd.org exact-host allowlist; settings-only OECD_SDMX_API_BASE_URL; module
   get_oecd_client factory (L5 trio). GET-only API -> CFTC redirect posture
   (allow_redirects=True, len(history) vs settings.connector_max_redirects, final-URL host
   recheck) on EVERY request (graft connectors_cftc_cot.py:259-263; NOT the WB client).
2. RATE — HONEST SPLIT: research pinned "maximum of 60 data downloads per hour" [DOC OECD API
   best-practices]. CODE-ENFORCED: per-run data-query budget = schema Field(default=6, ge=1,
   le=30) with 422 rejection test (le=30 keeps any single run <=half the hourly ceiling);
   standing 2rps limiter stays (politeness; the hourly cap is the binding constraint).
   OPERATOR RESIDUAL (stated in boundary note + provenance AND report text, never implied as
   code): the 60/hour ceiling ACROSS runs, and the ToS clause that traffic from
   VPNs/anonymized sources is not allowed (an egress-environment property, not code-checkable).
3. HTTP 413 / RESTRICTED-PARAMETER FAIL-CLOSED: OECD returns HTTP 413 for restricted
   parameters on very large dataflows. 413 is TERMINAL, error class restricted_parameter_413,
   NEVER retried (it is not transient). Dedicated test. Also fail closed on: empty dataset,
   rows that all normalize away (L3, error class empty_after_normalization), malformed
   envelope/CSV (schema_validation_failed).
4. PERSISTENCE: WB-landed shape (metadata-only DatasetVersion source_metadata + normalized
   observations in the report/selection JSON + DatasetSourceProvenance). FORBIDDEN CALLS
   unchanged. Zero new tables.
5. PROVENANCE (carried from source-conditions-research.md §2 — do NOT re-fetch):
   terms URL pinned = https://www.oecd.org/en/about/terms-conditions.html; the
   registration-voluntary line QUOTED as the anonymous-tier basis in boundary note +
   provenance ("Registration in no way impacts the application of these Terms");
   restricted-parameter doc URL pinned =
   https://www.oecd.org/en/data/insights/data-explainers/2026/03/Restricted-API-parameter.html
   (cite in the 413 test's provenance comment); module-level ATTRIBUTION constant naming OECD
   as source (CFTC mold); the no-VPN posture line; access date.
6. PARSER SCOPE: SDMX-CSV exactly; unrecognized structure fails closed — no dual-format
   parser, no format sniffing.

## Fence — the established pattern, derive anchors live
NEW  backend/app/services/connectors_oecd.py
EDIT router.py (POST /api/v1/connectors/oecd-sdmx/runs + dispatch + in-handler identity gate);
     schemas/api.py (typed request: dataflow id, key/dimension filter string, optional
     lastNObservations INT — note it may be a RESTRICTED parameter on large flows: keep it
     optional, document the 413 linkage; per-run budget le=30; max_rps le=2.0); config.py
     (OECD_SDMX_API_BASE_URL appended after the LAST connector alias; re-point shifted yaml
     config.py:NNN anchors in the same edit); main.py (pre-body _exact entry); .env.example
     (EOF sibling)
EDIT config/support_matrix.yaml (capability oecd_sdmx_anonymous_connector_slice; sorted
     position derived live; boundary-note honest extension naming SDMX data queries + the
     60/hr + no-VPN operator residuals; WB-format evidence incl. legacy-identity ref + PR-1..5
     literal tokens); scripts/support_matrix_constants.py; support_matrix_runtime_contract_
     audit.py (new probe, non-empty dict); support_matrix_check.py expected NO-EDIT (record)
EDIT backend/tests/test_support_matrix.py (dict +1, tuples, line_number_for
     ("OECD_SDMX_API_BASE_URL") assertion); test_layer3_support_matrix_runtime_contract_
     exhaustive.py (count live+1, alphabetical insert); test_legacy_api_operator_identity.py
     (entry + count live+1)
EDIT tests/test_api.py (9-13 tests APPENDED: happy dataflow query, budget>30 -> 422,
     413-terminal test — its TRIGGERING REQUEST must include lastNObservations, proving the
     documented restricted-parameter linkage, empty/all-null/malformed fail-closed,
     rate-limiter clock test, GET-redirect-cap test, 401, lease/idempotency, L4 tripwire
     asserting the exact sdmx.oecd.org base URL; in-file fixtures from the Phase-0 pinned
     example, <=25KB, doc-quote provenance comments)
REQUIRED: rc3 script + backend guard (append node-ids + bump exact count live+N)
EDIT docs front-door where truth-claims change. Do NOT touch rc2 (frozen).

## STOPs (S1-S8 as established; plus S9: any Phase-0 discovery that the chosen format's
## documented example is insufficient to hand-author meaningful fixtures -> STOP, do not guess
## dimension semantics)

## Known-green guards + ops notes (as established; honesty-coherence no-edit; probe non-empty;
## atomic closeout; git-lock retry; serial pytest; stale-process cleanup; queued-vs-stuck S6)

## Verification chain (established; PR "feat: add OECD SDMX anonymous public connector
## (offline-proven)"; detached post-merge proof incl. count, position, 413 test, boundary
## residuals wording, rc pins, leak scan)
Closeout: "## [From lane executor] M-CONNECTOR-OECD-SDMX-OFFLINE REPORT" + IPC reply.

## Non-goals
No live pilot/egress/D27-D28, no dual-format parsing, no dimension-discovery UI, no validator/
project6.ps1 changes, no refactors, no new backend/tests files, no on-disk fixtures, no rc2.

### 5.6. Wave 6 - IMF owner-gated mandate

Source path: `state/agent-inbox/imf-connector-source.md`  
Frozen sha256: `6770142c3ea0ea926c1ad501e14bb956b8213572e57d9e11df84da4c046b4937`

# M-CONNECTOR-IMF-DATAMAPPER-OFFLINE — Lane source (Tier-1 IMPLEMENTATION: IMF DataMapper v2 anonymous connector, OFFLINE-COMPLETE, zero egress, zero new tables; BOUNDED anti-bulk posture)
(rev 2 — 2026-07-08; critic-patched [1 BLOCKING: request-count model + budget arithmetic; 3 MATERIAL: shared-host path-prefix recheck + non-JSON classification, S3-vs-runtime clarity, parser pin table]. Wave-6, the LAST build lane of the connector program. Template = WB/CFTC/BLS/OECD as landed + L1-L6 + conditions-research verdicts (IMF RESOLVED-CLEAR for DataMapper v2 ONLY). ANCHOR-AGNOSTIC: OECD lands first — derive every count/anchor live (capability = live+1; legacy-identity live+1; rc3 live+N; imf_ sorts between health_ and layer3_ — derive live). DISPATCH GATE: after OECD lands+verifies.)

## Objective
Implement the IMF DataMapper v2 anonymous connector as a fully OFFLINE-PROVEN Tier-1 unit
with a deliberately BOUNDED posture (IMF ToS "prohibits the bulk download of information by
automated technology" — this connector is a small-slice query tool by construction, never a
sweeper). ZERO live calls to any imf.org host beyond Phase-0 doc pages (hard S1). Live pilot
= future lane gated on a named D27 grant.

## PHASE 0 — GRAMMAR PIN (gate; <=2 official doc pages, ledgered; the DataMapper help page is
## the primary source)
Pin from official pages (www.imf.org/external/datamapper/api/help family): (a) the exact v2
URL grammar (indicator list, country list, series query paths), (b) the response ENVELOPE
shape with a complete documented example (DataMapper returns nested-dict values keyed
indicator->country->year — pin the exact nesting from the doc example; this parser is a
bounded nested-dict walk, no in-repo mold — the doc example is the fixture basis),
(c) re-confirm no key/registration parameter exists in the v2 grammar. Quoted excerpts to
the inbox closeout file BEFORE code. S8-analog: unpinnable -> STOP. SCOPE FENCE: portal.api.imf.org and
any SDMX surface are OUT (account-gated; research verdict covers DataMapper v2 ONLY).
PARSER PIN TABLE (these DEFAULTS are orchestrator decisions, not doc claims — record them as
such in the report; never probe live to "check"): year keys string->int, non-numeric year key
-> schema_validation_failed; per-value null SKIPPED-not-failed (WB precedent
test_worldbank_connector_null_values_are_skipped_not_failed), ALL-null ->
empty_after_normalization; a requested country absent from values -> skip-and-record
per-country zero, ALL absent -> empty_after_normalization; top-level values key missing or
non-dict -> schema_validation_failed; empty values dict -> empty_after_normalization;
unknown-indicator responses resolve through the above rules, never live-probed; country list
accepts ISO3 codes only (region/group ids rejected by pattern) unless the Phase-0 doc example
shows otherwise; year-range applied via the pinned periods parameter, empty-after-filter ->
empty_after_normalization.

## Pre-made decisions (grounded in research §3; do NOT re-open)
1. HOST: www.imf.org exact-host allowlist; settings-only IMF_DATAMAPPER_API_BASE_URL
   (defaulting to the Phase-0-pinned v2 base path — the PATH PREFIX is part of the settings
   default, so every request starts from the pinned API family; per-run config can never
   move authority). GET-only -> CFTC redirect posture on every request (graft
   connectors_cftc_cot.py:259-263). L5 seam trio (get_imf_datamapper_client factory).
   SHARED-HOST HARDENING (critic-mandated; www.imf.org is the program's only genuinely shared
   FQDN — docs/publications/API on one host): (a) after redirects, recheck final host ==
   www.imf.org AND final URL path startswith the pinned /external/datamapper/api/ prefix;
   violation -> FetchPolicyBlockedError(redirect_policy_violation); (b) CLASSIFICATION
   HONESTY: wrap response.json() parse failure as the connector's
   SchemaValidationError(non_json_response) so a shared-host HTML page classifies as
   schema_validation_failed, NOT orchestrator_internal_error (the mold's fallback). One fence
   test: redirect-to-HTML fixture asserting the policy-block/schema classification.
2. ANTI-BULK POSTURE AS CODE + HONESTY SPLIT:
   REQUEST-COUNT MODEL (Phase 0 must CONFIRM from the help page): one GET per indicator, all
   requested countries appended to that indicator's path — N indicators = N requests minimum,
   and RETRIES COUNT against the budget (BLS mold connectors_bls.py:257-260). If Phase 0
   reveals a per-(indicator,country) request grammar instead, that is an S8-analog STOP:
   report and await a re-pinned cap set — never improvise.
   CODE-ENFORCED (aligned to the model): per-run request budget = schema
   Field(default=6, ge=1, le=10) (indicator cap 5 + 1 retry headroom) with 422 rejection
   test, PLUS a validation cross-check rejecting budget < len(indicator_ids) with 422 (and
   its test); indicator list max_length <=5; country list max_length <=10 (ISO3 codes only —
   see parser pin table); standing 2rps limiter.
   OPERATOR RESIDUAL (boundary note + provenance AND report text): the ToS anti-bulk clause
   quoted verbatim ("prohibits the bulk download of information by automated technology") with
   the statement that cross-run restraint is operator responsibility; no numeric IMF rate
   limit is published — the bounded budget is the compliance posture.
3. FAIL-CLOSED: empty values-dict, all-null normalization (L3 empty_after_normalization),
   malformed envelope (schema_validation_failed), auth-surprise (any 401/403 = terminal +
   S3-class report in the run error, never retried as transient), 429 terminal-or-retryable
   per mold. L2 real terminal-status vocab in counters. L4 tripwire asserting the exact
   pinned base URL.
4. PERSISTENCE: WB-landed shape (metadata-only DatasetVersion + normalized observations in
   report/selection JSON + DatasetSourceProvenance). FORBIDDEN CALLS unchanged. Zero tables.
5. PROVENANCE (carried from research §3 — do NOT re-fetch): DataMapper help URL; the
   anti-bulk ToS quote + its source URL as recorded in
   state/agent-inbox/source-conditions-research.md §3; access date; attribution constant
   naming IMF as source (CFTC mold); note that the SDMX/portal surface is explicitly out of
   scope for the anonymous program.

## Fence — established pattern, derive anchors live
NEW  backend/app/services/connectors_imf_datamapper.py
EDIT router.py (POST /api/v1/connectors/imf-datamapper/runs + dispatch + in-handler identity
     gate); schemas/api.py (typed request: indicator ids list <=5, country codes list <=10,
     optional year range, budget le=10, max_rps le=2.0); config.py (IMF_DATAMAPPER_API_BASE_URL
     appended after the LAST connector alias; re-point shifted yaml config.py:NNN anchors);
     main.py (pre-body _exact entry); .env.example (EOF sibling)
EDIT config/support_matrix.yaml (capability imf_datamapper_anonymous_connector_slice; honest
     boundary-note extension naming the bounded anti-bulk posture; WB-format evidence incl.
     legacy-identity ref + PR-1..5 literal tokens); scripts/support_matrix_constants.py;
     support_matrix_runtime_contract_audit.py (new probe, non-empty dict);
     support_matrix_check.py expected NO-EDIT (record)
EDIT backend/tests/test_support_matrix.py (dict +1, tuples, line_number_for
     ("IMF_DATAMAPPER_API_BASE_URL") assertion); exhaustive test (count live+1, alphabetical
     insert); test_legacy_api_operator_identity.py (entry + count live+1)
EDIT tests/test_api.py (9-13 tests APPENDED: happy single-indicator query, multi-country,
     budget>10 -> 422, indicator-list>5 -> 422, empty/all-null/malformed fail-closed,
     auth-surprise terminal test, rate-limiter clock test, GET-redirect-cap test, 401,
     lease/idempotency, L4 tripwire; in-file fixtures from the Phase-0 pinned envelope
     example, <=25KB, doc-quote provenance comments)
REQUIRED: rc3 script + backend guard (append node-ids + bump exact count live+N)
EDIT docs front-door where truth-claims change. Do NOT touch rc2 (frozen).

## STOPs (S1-S9 as established; S3 explicitly includes ANY discovery that a key/registration/
## account parameter exists in the v2 grammar — that contradicts the research basis: STOP and
## report with the doc quote, never work around)
CLARITY (critic-mandated): S3 as a STOP applies ONLY to Phase-0/doc discoveries. The
auth-surprise TEST asserts runtime terminal classification (http_4xx family, never retried)
plus S3-class wording in the run-error/report text; a 401/403 FIXTURE in tests is expected
behavior and never stops the lane.

## Known-green guards + ops notes (as established)

## Verification chain (established; PR "feat: add IMF DataMapper v2 anonymous connector
## (offline-proven)"; detached post-merge proof incl. count, position, anti-bulk boundary
## wording, auth-surprise test, rc pins, leak scan)
Closeout: "## [From lane executor] M-CONNECTOR-IMF-DATAMAPPER-OFFLINE REPORT" + IPC reply.

## Non-goals
No SDMX/portal.api.imf.org surface, no live pilot/egress/D27-D28, no pagination/sweep
features, no validator/project6.ps1 changes, no refactors, no new backend/tests files, no
on-disk fixtures, no rc2.

### 5.7. World Bank polish mandate

Source path: `state/agent-inbox/wb-polish-source.md`  
Frozen sha256: `8752ec191b45fa104b56651af46a16ac42c0839470c4fd84ecc990f9427594d5`

# M-WB-POLISH — Lane source (Tier-1 micro: the three adversary-identified WB MINOR fixes)
(rev 1 — 2026-07-08; pre-review = the WB-landing adversarial review itself (2-independent critic, CLEAN verdict, findings severity MINOR with exact file:line patches) — no separate critic pass. ANCHOR-AGNOSTIC: derive line numbers live; five connectors have landed since the findings were written.)

## Objective
Land the three MINOR defects the WB-landing adversarial review identified, exactly as
specified — no scope beyond them. Zero egress. Zero new tables.

## The three fixes (adversary-specified)
F1 REDIRECT POSTURE: graft the CFTC redirect discipline into the WB client's GET
   (connectors_worldbank.py _request_json): len(response.history) checked vs
   settings.connector_max_redirects + final response.url host recheck vs ALLOWED_HOST ->
   FetchPolicyBlockedError(redirect_policy_violation). (WB currently has NO redirect check;
   sibling connectors all do.)
F2 DEAD STATUS FILTER: connectors_worldbank.py page_count_completed filter uses literal
   status != 'failed' which never occurs (vocabulary: recommended/dry_run_skipped/
   download_failed) — failed targets are silently counted. Fix to exclude the REAL terminal
   failure status 'download_failed' (+ keep excluding dry_run rows only if that matches the
   field's documented meaning — read the field's consumers first; the fix must make the
   counter true, not merely different).
F3 ALL-NULL PAGE HONESTY: a WB observations page that is non-empty but whose rows ALL
   normalize away currently vanishes silently (no target row, no event). Fix: produce a
   failed target with error class empty_after_normalization (the vocabulary the later
   connectors already use), preserving the existing per-value null-skip behavior
   (test_worldbank_connector_null_values_are_skipped_not_failed must stay green).

## Fence (EXACT)
backend/app/services/connectors_worldbank.py + tests/test_api.py (2-4 new/adjusted tests:
redirect-cap test [WB fake with redirect history], counter-truth test, all-null-page test;
existing WB tests must stay green — especially the null-skip test and the yaml-evidence
node-ids). NOTHING else: no support-matrix/mirror edits (no capability/status/evidence
change), no docs, no schema, no config.

## STOPs: established S-set; plus if F2's field turns out to have a consumer that depends on
## the current (wrong) semantics, STOP and report instead of changing both ends.

## Verification chain (established shape)
Serial local slices (full -k worldbank selection green); git diff --check; leak scan; PR
"fix: harden World Bank connector redirect posture and counters" (no AI trailers); three
required contexts green; threads resolved (re-query); squash; detached post-merge proof
(worldbank selection green at merge SHA, yaml-cited node-ids all collect+pass, capability
count UNCHANGED); closeout "## [From lane executor] M-WB-POLISH REPORT" + IPC reply; worktrees
removed, branches preserved.

## Non-goals
No netblock CI plugin (defer-candidate, owner option), no other connectors touched, no
mirror-surface edits, no L1-retrofits to other modules (CFTC/BLS/OECD already have the
posture; senate/sciencebase out of scope).

### 5.8. Source conditions research report

Source path: `state/agent-inbox/source-conditions-research.md`  
Frozen sha256: `8189817e62058e3ff182392b8151dd00549fb6f6d84debd791316f78cfb20237`

# M-SOURCE-CONDITIONS-RESEARCH

Status: COMPLETE

Authority and scope:
- Binding lane source: `state/agent-inbox/source-conditions-research-source.md`.
- Repo authority refreshed: `project6-origin/main` at `78837774abf1e523eaf2e913d37545a9b1a2f22d`.
- Root `HEAD` observed at `c10b2645e2f416b3ca4e204666e8a97abd75d1aa`; root checkout is not used as implementation authority.
- Mode: read-only doc-gate research. No worktree, branch, PR, runtime validator, data API call, dataset download, signup, or key request.
- Allowed writes only: this report, one `inbox closeout` append, and the IPC reply.

## Verdict Summary

| Source | Verdict | Host FQDN for future D27 sketch | Updated fit class |
| --- | --- | --- | --- |
| BLS Public Data API | RESOLVED-CLEAR | `api.bls.gov`, docs/auth at `www.bls.gov`, registration at `data.bls.gov` only if excluded v2 is later allowed | STRONG-ANONYMOUS-PILOT, v1 only, hard low caps |
| OECD Data Explorer SDMX API | RESOLVED-CLEAR | `sdmx.oecd.org`; related browser/download host `data-explorer.oecd.org` | STRONG-ANONYMOUS-PILOT, SDMX complexity |
| IMF DataMapper API | RESOLVED-CLEAR for DataMapper v2 only | `www.imf.org` under `/external/datamapper/api/...`; keep `portal.api.imf.org` out of scope | VIABLE-ANONYMOUS-PILOT, no bulk/systematic use |
| FAO / FAOSTAT | DEFER-FINAL | unpinned from official fetchable docs; candidate portal under `www.fao.org/faostat/en/` | VIABLE-BUT-NOT-MANDATE-READY |
| BTS / DOT Open Data | DEFER-FINAL | `data.bts.gov`; platform docs linked externally to `dev.socrata.com` | DEFER until BTS/DOT source-owned auth/rate page is pinned |

## 1. BLS Public Data API

Condition:
- Confirm whether BLS ToS permits automated anonymous v1 retrieval, attribution requirements, and relevant connector prohibitions.
- Re-confirm v1/v2 boundary and anonymous caps.

Verdict: RESOLVED-CLEAR.

Decisive evidence:
- Scope/acceptance: [DOC `https://www.bls.gov/developers/termsOfService.htm` L220-L222] quote: "Access to or use of BLS.gov services or its content constitutes acceptance".
- End-use posture: [DOC `https://www.bls.gov/developers/termsOfService.htm` L223-L225] quote: "Data accessed through BLS.gov do not... include controls over its end use".
- Attribution: [DOC `https://www.bls.gov/developers/termsOfService.htm` L226-L228] quote: "Users of the public API should cite the date".
- Misrepresentation and limits: [DOC `https://www.bls.gov/developers/termsOfService.htm` L233-L240] quote: "Users may not modify or falsely represent content".
- v2 boundary: [DOC `https://www.bls.gov/developers/api_faqs.htm` L270-L324] quote: "API Version 2.0 requires registration".
- v1 anonymous limits: [DOC `https://www.bls.gov/developers/api_faqs.htm` L281-L303, L345-L354] the unregistered column gives daily query limit 25, series/query 25, years/query 10, and 50 requests per 10 seconds.

Synthesis:
- Anonymous BLS is mandate-ready only as API v1. API v2 registration/key behavior is out of fence for the anonymous connector program.
- A build mandate should encode a hard config/test budget no higher than 25 queries/day, 25 series/query, 10 years/query, and 50 requests/10 seconds; it should also require access-date citation and the BLS no-vouch disclaimer in provenance text.
- No ToS sentence found prohibits a bounded automated connector when it stays inside the published API limits. The right-to-limit clause means retry/backoff and fail-closed 429/blocked behavior must be explicit.

Recommended build slot:
- Wave 4 candidate if the owner accepts the low anonymous daily cap. It is the simplest high-value macro/labor follow-up after the already-landed earlier connectors.

## 2. OECD Data Explorer SDMX API

Condition:
- Pin actual terms page, numeric rate limits, and runtime API host.

Verdict: RESOLVED-CLEAR.

Decisive evidence:
- API identity and free use: [DOC `https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html` L3701-L3704] quote: "These APIs are free of charge".
- Host/query grammar: [DOC same URL L3715-L3726] quote: "Host URL" is a required element in the API data query.
- Numeric rate limit: [DOC `https://www.oecd.org/en/data/insights/data-explainers/2024/11/Api-best-practices-and-recommendations.html` L3701-L3705] quote: "maximum of 60 data downloads per hour".
- VPN/anonymizer restriction: [DOC same URL L3703-L3705] quote: "traffic originating from VPNs or anonymized sources is not allowed".
- Terms/data reuse: [DOC `https://www.oecd.org/en/about/terms-conditions.html` L3752-L3757] quote: "you can extract from, download, copy, adapt, print, distribute".
- API registration: [DOC same URL L3763-L3770] quote: "Registration in no way impacts the application of these Terms".
- Parameter restrictions: [DOC `https://www.oecd.org/en/data/insights/data-explainers/2026/03/Restricted-API-parameter.html` L3700-L3728] selected very large dataflows block `lastNObservations` / `firstNObservations` and return HTTP 413.

Synthesis:
- Runtime host is `sdmx.oecd.org`; the browser/download companion host is `data-explorer.oecd.org`.
- Mandate-ready, with a hard 60 data-downloads/hour ceiling, no VPN/anonymized egress posture, local cache expectation, and a STOP condition for HTTP 413 or restricted-parameter failures.
- Data attribution and third-party-source metadata review remain build requirements, but not blockers.

Recommended build slot:
- Wave 5. OECD has cleaner rate documentation than IMF and broader macro value than FAO/BTS, but the SDMX parser is higher effort than BLS v1.

## 3. IMF DataMapper API

Condition:
- Confirm whether DataMapper v2 requires key/registration for production use; pin runtime host.

Verdict: RESOLVED-CLEAR for DataMapper v2 only. IMF SDMX/swagger remains out of scope unless an owner accepts account-gated exploration.

Decisive evidence:
- DataMapper API purpose: [DOC `https://www.imf.org/external/datamapper/api/help` L0-L4] quote: "current version of the API is v2".
- DataMapper endpoint shape: [DOC same URL L5-L17] lists base endpoints for indicators/countries/regions/groups and time-series retrieval using appended IDs and `periods`.
- Separate IMF Data API / SDMX path: [DOC `https://data.imf.org/en/Resource-Pages/IMF-API` L18-L35] quote: "Use your beta portal account to sign in".
- IMF data terms: [DOC `https://www.imf.org/en/about/copyright-and-terms` L316-L324] quote: "You may download, extract, copy, create derivative works, publish, distribute, and use Data".
- Automation constraint: [DOC same URL L289-L295] quote: "prohibits the bulk download of information by automated technology".

Synthesis:
- The DataMapper help page documents a public v2 URL grammar and does not describe an API key, account, token, or registration step. The account language found is on the separate IMF Data API swagger page, not the DataMapper help page.
- Runtime host for a D27 sketch should be `www.imf.org` and path-bounded to `/external/datamapper/api/...`; `portal.api.imf.org` and broader SDMX APIs should be excluded unless separately authorized.
- IMF terms make a broad always-on scraper inappropriate. A mandate can still be decision-complete as a bounded, low-request, non-bulk DataMapper pilot with cache/retry discipline, attribution, and explicit STOP on any auth, 403, 429, or bulk-download warning.

Recommended build slot:
- Wave 6. Keep it behind BLS and OECD because no numeric rate limit was found and the IMF anti-bulk/systematic-automation language requires a narrower production posture.

## 4. FAO / FAOSTAT

Condition:
- Locate official API documentation; pin API host, anonymous access yes/no, and ToS.

Verdict: DEFER-FINAL.

Decisive evidence:
- API portal existence: [DOC `https://www.fao.org/statistics/highlights-archive/highlights-detail/faostat-launches-a-new-api-developer-portal-to-make-data-access-easier/en` L63-L76] quote: "FAOSTAT has launched a new API developer portal".
- FAOSTAT free access: [DOC `https://www.fao.org/statistics/en` L85-L92] quote: "FAOSTAT provides free access".
- Statistical database terms: [DOC `https://www.fao.org/contact-us/terms/db-terms-of-use/en/` L52-L58] quote: "datasets free of charge, in machine-readable format".
- FAOSTAT included in terms annex: [DOC same URL L82-L89] Annex 1 lists FAOSTAT as an FAO corporate statistical database.
- Reuse/attribution and restrictions: [DOC same URL L60-L68] quote: "must give appropriate attribution and credit to FAO".

Synthesis:
- Official FAO pages now prove the FAOSTAT API developer portal exists, that FAOSTAT data are free, and that database datasets are machine-readable and generally CC BY 4.0 unless metadata says otherwise.
- The exact fetchable API documentation page, runtime API host, anonymous/key requirement, and numeric rate policy were not pinned from official pages within the lane budget. The direct FAOSTAT portal page rendered zero lines through the fetch tool, and the API-developer-portal link routed back to the JS-heavy FAOSTAT page.
- Because the source asked for host plus anonymous-access pinning, this must remain DEFER-FINAL rather than being upgraded from "viable" to "build-mandate-ready".

Updated fit:
- VIABLE-BUT-NOT-MANDATE-READY. The next mandate should first obtain the official API developer portal text through a manual browser or operator-provided excerpt, then freeze the host/rate/auth tuple before implementation.

## 5. BTS / DOT Open Data

Condition:
- Pin source-owned developer/auth docs for data.bts.gov, Socrata app-token optionality on data.bts.gov specifically, and rate policy.

Verdict: DEFER-FINAL.

Decisive evidence:
- Source portal identity: [DOC `https://data.bts.gov/` L2-L13] data.bts.gov is an official .gov HTTPS site and links to Catalog, User Guide, and a `Developers` page hosted at `dev.socrata.com`.
- BTS dataset page shape: [DOC `https://data.bts.gov/Research-and-Statistics/Monthly-Transportation-Statistics/crem-w557` L2-L13] the dataset page repeats the official .gov / HTTPS banner and the external developer link.
- DOT developer page: [DOC `https://www.transportation.gov/developer` L145-L155] quote: "open datasets and APIs".
- DOT developer inventory scope: [DOC same URL L148-L153] it lists FMCSA, FRA, FAA, and NHTSA APIs, but not a BTS/Data Inventory API.

Synthesis:
- The source-owned pages confirm that data.bts.gov is an official BTS open-data portal and that it delegates developer docs to Socrata. They do not pin, in BTS/DOT-owned text, whether app tokens are optional for data.bts.gov or what numeric rate policy applies.
- I did not use generic Socrata docs as verdict-bearing evidence because the lane specifically asked for source-owned BTS/DOT pages and warned not to generalize from other Socrata instances.

Updated fit:
- DEFER. BTS should not enter waves 4-6 until a BTS/DOT-owned page, or an operator-accepted source-specific Socrata page for `data.bts.gov`, pins app-token optionality and rate behavior.

## Build-Order Synthesis For Waves 4-6

Debate:
- BLS-first argument: highest-value labor/macro signal, simple v1 endpoint family, and the source condition is now resolved. Weakness: 25/day cap is tight.
- OECD-first argument: cleaner numeric rate policy at 60 downloads/hour and no registration effect. Weakness: SDMX implementation cost and structure/codelist complexity are higher.
- IMF-first argument: simplest JSON-style DataMapper shape. Weakness: no numeric rate limit and IMF terms require careful avoidance of bulk/systematic automated downloading.

Consensus:
- Recommended order is BLS -> OECD -> IMF DataMapper.
- BLS is build-mandate-ready as a low-budget v1 anonymous connector with registration/v2 explicitly out of scope.
- OECD is build-mandate-ready with 60 downloads/hour, no VPN/anonymized egress, attribution, and restricted-parameter STOP conditions.
- IMF is build-mandate-ready only as a narrow DataMapper v2 pilot, not a broad IMF SDMX/swagger connector and not a bulk/systematic downloader.
- FAO and BTS remain deferred and should not be included in waves 4-6 until their host/auth/rate tuples are pinned from source-owned documentation.

## Request Ledger

Verdict-bearing official evidence pages used:
- BLS 1/2: `https://www.bls.gov/developers/termsOfService.htm` - ToS, citation, limits, no false representation.
- BLS 2/2: `https://www.bls.gov/developers/api_faqs.htm` - v1/v2 boundary and anonymous caps.
- OECD 1/4: `https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html` - API identity, free access, query shape.
- OECD 2/4: `https://www.oecd.org/en/data/insights/data-explainers/2024/11/Api-best-practices-and-recommendations.html` - 60 downloads/hour and no VPN/anonymized traffic.
- OECD 3/4: `https://www.oecd.org/en/about/terms-conditions.html` - data/API terms, attribution, voluntary registration.
- OECD 4/4: `https://www.oecd.org/en/data/insights/data-explainers/2026/03/Restricted-API-parameter.html` - restricted parameters and HTTP 413 behavior.
- IMF 1/3: `https://www.imf.org/external/datamapper/api/help` - DataMapper v2 documentation.
- IMF 2/3: `https://data.imf.org/en/Resource-Pages/IMF-API` - separate SDMX/swagger beta-portal sign-in boundary.
- IMF 3/3: `https://www.imf.org/en/about/copyright-and-terms` - IMF data reuse and automation constraints.
- FAO 1/4: `https://www.fao.org/statistics/highlights-archive/highlights-detail/faostat-launches-a-new-api-developer-portal-to-make-data-access-easier/en` - FAOSTAT API portal announcement.
- FAO 2/4: `https://www.fao.org/statistics/en` - FAOSTAT free-access statement.
- FAO 3/4: `https://www.fao.org/contact-us/terms/en/` - FAO reuse terms and statistical-database terms pointer.
- FAO 4/4: `https://www.fao.org/contact-us/terms/db-terms-of-use/en/` - FAO statistical database terms and FAOSTAT annex.
- BTS 1/4: `https://data.bts.gov/` - official data.bts.gov portal and external developer-doc link.
- BTS 2/4: `https://data.bts.gov/Research-and-Statistics/Monthly-Transportation-Statistics/crem-w557` - BTS dataset-page shape and external developer-doc link.
- BTS 3/4: `https://www.transportation.gov/developer` - DOT developer-resource page.
- BTS 4/4: `https://www.transportation.gov/web-policies` - DOT source-owned web-policy surface checked; no BTS API auth/rate details found.

Non-verdict navigation/error notes:
- `https://www.oecd.org/en/data/insights/data-explainers/2025/02/OECD-Data-Explorer-News.html` was opened during OECD rate-limit triangulation but not needed for the final verdict.
- `https://www.fao.org/faostat/en/` was opened and rendered zero lines in the fetch tool; it is treated as a failed portal read, not as decisive evidence.
- `https://data.transportation.gov/videos` was opened through the DOT/data portal user-guide link; no BTS auth/rate evidence was found.
- `https://data.bts.gov/developers` was blocked by the browser safety gate before content retrieval.
- `https://www.tylertech.com/terms` returned 403 and was not used as source-owned evidence.
- `https://openknowledge.fao.org/handle/20.500.14283/cd7464en` timed out and was not used.

Budget note:
- Verdict-bearing evidence pages: 17/20 total; each source uses <=4 verdict-bearing pages.
- Including non-verdict navigation pages that returned content, total official/source-adjacent retrieved pages stayed within 20 unique pages. Blocked, 403, and timeout entries above are disclosed as no-content attempts and were not used as evidence.
- No API endpoint invocation, dataset/file download, PDF download, account creation, signup, or key request was performed.

## Done-Criteria Self-Check

- Five sources have verdicts: BLS RESOLVED-CLEAR, OECD RESOLVED-CLEAR, IMF RESOLVED-CLEAR for DataMapper-only, FAO DEFER-FINAL, BTS DEFER-FINAL.
- All verdict-bearing claims are tagged to official [DOC] pages or explicitly framed as synthesis.
- Build-order synthesis for waves 4-6 is included.
- Writes are limited to the report, the shared closeout append, and the IPC reply.
- Tail re-read of `the inbox closeout file` must be performed after the closeout append.

### 5.9. World Bank landing review mandate

Source path: `state/agent-inbox/wb-landing-adversarial-source.md`  
Frozen sha256: `9b1c1052044a989b3a970296fffc93eeeb0496202b04908b67c22d96485168bf`

# M-WB-LANDING-ADVERSARIAL — Lane source (READ-ONLY adversarial review of the first connector landing, PR #2459 / 2a69713115a169e1724445452ae1937aba9d0f00)
(rev 1 — 2026-07-07. This landing is the TEMPLATE-SETTER for 4-6 more connector lanes; defects found here multiply if unfound.)

## Objective
Adversarially review the merged World Bank connector landing against its binding mandate
(state/agent-inbox/wb-connector-source.md, rev 2). You did not author the mandate or the code.
Verdict: CLEAN / FIX-LANE-NEEDED (with severity-tagged defects). Orchestrator has already
verified: merge state, 19-file set, in-handler gating + pre-body entry present,
capability_count==29, PROBES entry, PR-1..5 markers + supported status, boundary tokens
survive, senate test defs present, added-line leak scan zero, PR CI green, 5/5 threads. Do
NOT re-do those surface checks — go DEEPER.

## Rules
Read-only repo (no commits/PRs/tracked edits). You MAY create a detached proof worktree at
2a69713115a169e1724445452ae1937aba9d0f00 and run TARGETED pytest slices (serial, no xdist,
bounded timeouts, one process at a time — hardware rail). No live network calls to any
worldbank host (grep-prove the tests don't either). Writes allowed ONLY:
state/agent-inbox/wb-landing-adversarial-report.md + closeout append to the inbox closeout file + IPC reply.

## Attack surface
1. FENCE ADJUDICATION: 19 files landed. The mandate's conditional rc3 branch named
   scripts/rc3_sec_xbrl_offline_acceptance.py; the landing ALSO touched
   backend/tests/test_release_rc3_sec_xbrl_offline_acceptance.py. Adjudicate: legitimate
   consequential edit of the conditional (a guard mirroring the script) or silent scope
   expansion? Any other file whose necessity is not mandate-derivable?
2. CLIENT-VS-LIFECYCLE SPLIT: diff connectors_worldbank.py against the mandate rule — client
   layer (HTTP/_RateLimiter/backoff/error classification) copied in-module; lifecycle
   (_acquire_lease/_finalize_run/_record_run_event/etc) IMPORTED from connectors_sciencebase.
   Any re-implemented lifecycle semantics = MATERIAL defect (lease-fork risk).
3. OFFLINE PURITY: prove the test suite cannot hit the network — fake-client seam
   (get_worldbank_client monkeypatch mold), no requests/urllib direct calls in tests, no
   fixture that embeds a live-capture artifact. Also verify the module itself enforces
   https-only + allowed_hosts=["api.worldbank.org"] + SSRF private-IP rejection at the same
   enforcement points the senate/sciencebase mold uses.
4. EVIDENCE HONESTY: every test node-id named in the yaml evidence string EXISTS and PASSES
   (run that exact slice in the detached worktree); PR-1..PR-5 markers map to real test
   groups, not decorative tokens. Attribution: CC BY 4.0 + "The World Bank: Dataset name:
   Data source" + ToS URL recorded where the mandate said (DatasetSourceProvenance path +
   report surfaces) — verify in code, not just yaml.
5. ACCOUNTING + FAIL-CLOSED: requests_total incremented per attempt (D28 dependency);
   empty-result and malformed-response paths fail closed (run those tests); rate-limiter
   token-bucket <=2rps default with Retry-After honoring.
6. MIRROR INTEGRITY: config.py insertion — did any support_matrix.yaml config.py:NNN>214
   evidence anchors shift without re-pointing (the critic-found silent-staleness trap —
   check nonlocal_multi_trust_multi_identity's anchor against live config.py)? .env.example
   appended at EOF (not mid-file)? test_honesty_machinery_coherence.py green?
7. RC2/RC3 PIN INTEGRITY: every node-id in scripts/rc2_public_connectors_acceptance.py still
   collects (no senate test renamed/moved); the rc3 extension follows the file's own
   convention (compare to how senate entries appear).
8. POST-MERGE MAIN RUN: 28883979652 was in_progress at dispatch — confirm terminal state =
   success (poll bounded ~300s intervals; if failure, that is automatically FIX-LANE-NEEDED
   with the failing job named).
9. TEMPLATE LESSONS: anything the NEXT connector lane (CFTC, file-download shaped) should do
   differently — list explicitly (this feeds the next mandate).

## Deliverable
state/agent-inbox/wb-landing-adversarial-report.md: verdict, severity-tagged findings
(CRITICAL/MATERIAL/MINOR/NON-ISSUE), evidence per finding (file:line / test output), template
lessons. Closeout append "## [From lane executor] M-WB-LANDING-ADVERSARIAL REPORT" + IPC reply.

## Addendum (2026-07-08): IMF Envelope Grant Exercised - Hard STOP, Returned Owner-Gated

This addendum supersedes the pending-owner-decision framing in Section 2 for IMF DataMapper. The narrow named D27 grant was received and armed for envelope pinning only, bounded to host `www.imf.org`, path family `/external/datamapper/api/v2`, and at most four counted GETs: two planned requests plus two contingency requests. The arming record and per-request D28 ledger were kept in the coordination inbox.

Request 1 of 4 was `GET /external/datamapper/api/v2/indicators`. It returned HTTP 403 with `text/html`, 418 bytes, no redirect, and no retry. Under the grant, HTTP 403 was a hard STOP. No contingency request was spent because contingency covered non-auth and non-policy repairs only. No further request was made, no build was started, and the working tree was verified clean.

The observed 403 is consistent with the WAF or bot-block class previously seen on other agency documentation hosts for automated clients, while the endpoint remains publicly documented as keyless. The distinction does not change the grant outcome: 403 means STOP.

Disposition: IMF DataMapper returns to owner-gated and deferred status under the grant's no-escalation rule. The recorded unlock paths are: accept deferred-final, or provide owner-supplied envelope evidence captured through ordinary human browser access so the build lane can re-run fully offline with zero agent egress. Automated transport-posture workarounds are explicitly not pursued.

Program tally after this outcome: five connectors landed and verified; IMF remains owner-gated, grant-exercised, and fail-closed; FAO and BTS remain deferred-final.
