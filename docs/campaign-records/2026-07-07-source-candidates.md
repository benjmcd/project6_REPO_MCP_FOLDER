> Tracked source-candidates record, frozen at PR #2458 (chain state = main 3c669256 / #2458). Sources: the untracked inbox files `state/agent-inbox/source-candidates-dossier.md` sha256 `d204e8485aceeab4ba0fbe030934d51d83416610f7cfa6c399023395dc4260f9`; `state/agent-inbox/source-candidates-adjudication.md` sha256 `a0127d85628bb795179f95c562f1887e93db9bf0dcbe803586b05737f4853117`; `state/agent-inbox/source-candidates-adversarial-review.md` sha256 `0d9d8ed3b7db9f89d5cf39df4bc4bc711d113e0d73f66affc8689e86961166ec`; this tracked copy publication-normalizes role labels while preserving the claims. This is a dated PLANNING/GOVERNANCE record subordinate to `docs/MASTER_CONTEXT.md` and `docs/program-context/` (D10: not a second master context). Future campaign/frontier records land as siblings in this folder.

# Source-Candidates Decision Chain Record

This tracked record freezes the source-candidates decision chain for the connector-breadth / local-depth track. It is subordinate to `docs/MASTER_CONTEXT.md` and `docs/program-context/` and does not replace those canonical program surfaces.

---

## Investigation dossier

# M-SOURCE-CANDIDATES-INVESTIGATION Dossier

Authority: live `project6-origin/main` at `3c669256c7246c1b8d16312226235e9a1c2495b4`; root checkout is preserved dirty state and not implementation authority. [REPO project6-origin/main]

Owner priors were read from `the owner-provided candidate list`; the source lane says those group labels are priors, not verdicts. [REPO state/agent-inbox/source-candidates-investigation-source.md]

Evidence tags: `[REPO path:lines]` is live-main repo evidence, `[DOC url]` is an official HTTPS page read in this lane, and `[KNOWLEDGE]` is unverified prior knowledge. [REPO state/agent-inbox/source-candidates-investigation-source.md]

## 1. Repo Evidence Base

- Anonymous boundary: `support_matrix.yaml` selects `profile=local_expert` with overlays `public_connectors` and `sec_xbrl_offline`; its boundary note says public connector support is bounded to ScienceBase public/MCS and Senate LDA anonymous metadata only, and says no keyed connector claim is selected. [REPO config/support_matrix.yaml:1-8]
- Supported public connector entries are exactly `sciencebase_public_connector_slice` and `senate_lda_anonymous_connector_slice`; `keyed_connectors` is explicitly `unsupported`. [REPO config/support_matrix.yaml:27-34] [REPO config/support_matrix.yaml:152-154]
- The README front door says public connector support is bounded to public/anonymous connector use and is not a production-ready claim for keyed connectors. [REPO README.md:3]
- The local-expert support doc says the posture has no authentication boundary, claims only public/anonymous connectors plus offline SEC proof, and excludes keyed connector secrets, HA, OCR, provider delivery, model/agent egress, and nonlocal trust. [REPO docs/support-matrix-local-expert.md:3-19] [REPO docs/support-matrix-local-expert.md:82-84]
- Existing connector shape: README describes ScienceBase flow as submit -> discover/hydrate/select -> download -> ingest/profile/recommend -> reports/events, and Senate LDA flow as submit -> query official filings API -> persist targets -> optional detail hydrate -> reports/events. [REPO README.md:28-33]
- Existing endpoint family includes `POST /api/v1/connectors/sciencebase-public/runs`, `sciencebase-mcs`, `nrc-adams-aps`, and `senate-lda`, plus run detail/targets/events/reports/cancel/resume/content-units. [REPO README.md:48-60]
- Config base URLs follow the pattern `*_api_base_url` plus optional key fields; current defaults are ScienceBase catalog, NRC ADAMS APS, and Senate LDA. [REPO backend/app/core/config.py:210-220]
- Dispatch extends `_connector_executor` with a connector key to executor function mapping; a new unit would need a dispatch entry, typed schema, POST route, service module, support-matrix entry, docs/front-door alignment, and tests. [REPO backend/app/api/router.py:154-160] [REPO backend/app/api/router.py:339-366] [REPO backend/app/api/router.py:446-472] [REPO backend/app/schemas/api.py:168-207] [REPO backend/app/schemas/api.py:278-301]
- The Senate LDA connector is currently 1207 physical lines and reuses `ConnectorRun`, `ConnectorRunTarget`, `Dataset`, `DatasetSourceProvenance`, and `DatasetVersion` rather than adding new tables. [REPO backend/app/services/connectors_senate_lda.py:16-38]
- Senate LDA normalizes to `max_rps=2.0`, `allowed_hosts=["lda.senate.gov"]`, `official_api_only`, and `metadata_only`; its client runs anonymous unless an optional API key is configured. [REPO backend/app/services/connectors_senate_lda.py:145-159] [REPO backend/app/services/connectors_senate_lda.py:198-210]
- Senate LDA aliases source fields onto generic ScienceBase-shaped target columns and records API base URL, auth mode, logical query, lease conflicts, and metadata-only execution state. [REPO backend/app/services/connectors_senate_lda.py:351-365] [REPO backend/app/services/connectors_senate_lda.py:899-906] [REPO backend/app/services/connectors_senate_lda.py:951-984]
- Egress safety: ScienceBase defaults to allowed host patterns `sciencebase.gov`, `www.sciencebase.gov`, and `*.usgs.gov`; fetch policy allows only HTTPS, applies host allowlist checks, resolves host IPs, and rejects loopback/private/link-local/multicast/unspecified/reserved IPs. [REPO backend/app/services/sciencebase_connector/contracts.py:24-25] [REPO backend/app/services/connectors_sciencebase.py:155-185]
- Download execution enforces redirect limits and records final URL, host, and resolved IP; blocked targets become `blocked_by_fetch_policy` / `host_policy_violation`. [REPO backend/app/services/connectors_sciencebase.py:407-431] [REPO backend/app/services/connectors_sciencebase.py:1667-1675] [REPO backend/app/services/connectors_sciencebase.py:2010-2019]
- D27 says a new host class requires a named owner grant identifying host class and request budget before the first request; D28 says a named new-host grant must become a concrete arming record and finite request ledger. [REPO docs/program-context/02-decision-record.md:541-558] [REPO docs/program-context/02-decision-record.md:588-603]
- Forward plan keeps D27/D28 active for future first-use host classes, new live taxonomy vintages, or broader request budgets. [REPO docs/program-context/03-forward-plan.md:349-352] [REPO docs/program-context/03-forward-plan.md:411-412]
- Tier-2 triggers include value reveal, durable persistence, schema/migrations, default-on behavior, and redaction posture; the SEC merge policy adds Alembic migrations, ORM schema, durable persistence, and revealed-value handling to the Tier-2 surface list. [REPO docs/program-context/00-posture-and-invariants.md:91-96] [REPO next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:39-63]
- Support-matrix exact assert set includes `config/support_matrix.yaml`, `scripts/support_matrix_constants.py`, `scripts/support_matrix_check.py`, `scripts/support_matrix_runtime_contract_audit.py`, README/front-door tests, and local-expert docs; the constants require public connector slices supported and keyed connectors unsupported. [REPO docs/support-matrix-local-expert.md:7] [REPO scripts/support_matrix_constants.py:21-50] [REPO scripts/support_matrix_check.py:156-165] [REPO scripts/support_matrix_runtime_contract_audit.py:626-674] [REPO tests/test_readme_frontdoor_truth.py:34-70]
- Analytics consumers are `cross_correlation`, `decomposition`, `structural_break`, and `descriptive_summary`; time-indexed multivariate data maps to lag/decomposition/break detection, single numeric time series maps to decomposition plus structural breaks, and other tabular data maps to descriptive summary. [REPO backend/app/services/analysis.py:43-123] [REPO backend/app/services/analysis.py:217-231]
- Market insight categories are deterministic `trend`, `correlation`, and `emerging_risk`; the shown rules emit correlation and trend findings from integrated signal shapes. [REPO backend/app/services/market_insight_ai.py:8-18] [REPO backend/app/services/market_insight_ai.py:74-130]
- USGS overlap: ScienceBase base URL is `https://www.sciencebase.gov/catalog`, external allowlist can include `*.usgs.gov`, and the ScienceBase schema already defaults query text to `Mineral Commodity Summaries`. [REPO backend/app/core/config.py:210] [REPO backend/app/services/sciencebase_connector/contracts.py:24-25] [REPO backend/app/schemas/api.py:168-182]

## 2. Per-Candidate Entries

### 1. EIA - U.S. Energy Information Administration

- IDENTITY: U.S. Energy Information Administration; Open Data API v2 and bulk facility; D27 hosts `api.eia.gov` and `www.eia.gov`. [DOC https://www.eia.gov/opendata/documentation.php] [DOC https://www.eia.gov/opendata/register.php]
- ACCESS MODE: Primary owner-implied mode is REST/JSON API for energy prices/reserves; EIA also exposes Excel add-in and bulk files. [DOC https://www.eia.gov/opendata/documentation.php]
- ANONYMITY VERDICT: KEY-REQUIRED for the API because the registration page says API users are required to obtain a key; bulk download is a keyless exception, but it is not the owner's implied API path. [DOC https://www.eia.gov/opendata/register.php] [REPO config/support_matrix.yaml:152-154]
- RATE/TOS: HTML FAQ says 5,000 rows per API response, 300 for XML, and says roughly under 9,000 per hour and 5 per second should avoid throttling under ideal conditions. [DOC https://www.eia.gov/opendata/faqs.php]
- DATA CLASS: Numeric energy time series and metadata JSON; a pilot could use 3-5 small monthly price/reserve series with pagination fixtures. [DOC https://www.eia.gov/opendata/documentation.php] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed service pattern if keyed policy is solved; current Tier-1 connector unit is blocked by keyed boundary. [REPO backend/app/services/analysis.py:43-123] [REPO config/support_matrix.yaml:152-154]
- TIER + ESCALATION TRIGGERS: Not Tier-1 now; keyed source hits unsupported keyed connectors and would require owner policy, secret handling, and support-matrix reclassification. [REPO config/support_matrix.yaml:152-154] [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: Fixture budget 3 doc/API-response captures after a keyed policy grant; live pilot budget 20 API requests plus ledger; canned fixtures should cover category discovery, one data response, pagination, throttle error, and malformed series. [REPO docs/program-context/02-decision-record.md:541-558] [KNOWLEDGE]
- UTILITY MAP: Feeds decomposition, structural breaks, and correlations for energy price/reserve questions; answers "which fuels are moving together", "when did a price regime shift", and "how do energy indicators compare with macro data"; overlaps OPEC and partly FRED/World Bank. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 350-550 LOC plus config, schema, route, dispatch, support-matrix entries, front-door docs, and 8-12 tests if policy permits keyed access. [REPO backend/app/api/router.py:154-160] [REPO tests/test_api.py:7410-7503] [KNOWLEDGE]
- RISKS: Key handling, rate throttling, series hierarchy drift, pagination, revisions, and overlap with EIA bulk/download options. [DOC https://www.eia.gov/opendata/faqs.php] [KNOWLEDGE]
- PRELIM FIT-CLASS: DISQUALIFIED(keyed-for-API-now) for anonymous Tier-1; strong later if a keyed-connector policy program is authorized. [DOC https://www.eia.gov/opendata/register.php] [REPO config/support_matrix.yaml:152-154]
- UNVERIFIED REMAINDER: Confirm current API terms, whether any specific price/reserve bulk slice is keyless enough to replace the API path, and exact fixture response shapes without invoking data endpoints. [KNOWLEDGE]

### 2. FRED - Federal Reserve Bank of St. Louis

- IDENTITY: Federal Reserve Bank of St. Louis FRED API; D27 hosts `api.stlouisfed.org`, `fred.stlouisfed.org`, and registration host `fredaccount.stlouisfed.org`. [DOC https://fred.stlouisfed.org/docs/api/api_key.html] [DOC https://fred.stlouisfed.org/docs/api/terms_of_use.html]
- ACCESS MODE: REST web service returning XML or JSON for macro series, releases, categories, and observations. [DOC https://fred.stlouisfed.org/docs/api/fred/]
- ANONYMITY VERDICT: KEY-REQUIRED because the API-key doc says all web service requests require an API key, and the terms say implementations must use the issued key. [DOC https://fred.stlouisfed.org/docs/api/api_key.html] [DOC https://fred.stlouisfed.org/docs/api/terms_of_use.html] [REPO config/support_matrix.yaml:152-154]
- RATE/TOS: Official error docs confirm rate limiting and HTTP 429 but did not publish a numeric rate in pages read; terms allow St. Louis Fed to impose bandwidth/transaction limits and include third-party series copyright obligations. [DOC https://fred.stlouisfed.org/docs/api/fred/errors.html] [DOC https://fred.stlouisfed.org/docs/api/terms_of_use.html]
- DATA CLASS: Numeric macro time series with metadata; pilot slice could be 3-5 well-known series across inflation, rates, employment, and commodities. [DOC https://fred.stlouisfed.org/docs/api/fred/] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed after keyed policy; not Senate LDA mold because source objects are time series, not target metadata records. [REPO backend/app/services/analysis.py:43-123] [KNOWLEDGE]
- TIER + ESCALATION TRIGGERS: Not Tier-1 now because keyed API registration collides with unsupported keyed connectors. [REPO config/support_matrix.yaml:152-154]
- EGRESS PLAN SKETCH: Fixture budget 4 keyed-response captures after policy grant; live pilot 20 requests; fixtures should cover search, series metadata, observations, 429, and invalid key. [DOC https://fred.stlouisfed.org/docs/api/fred/errors.html] [KNOWLEDGE]
- UTILITY MAP: Feeds all time-series methods and market trend/correlation rules; answers inflation-energy correlations, rate breakpoints, and macro regime shifts; overlaps OECD/IMF/World Bank/BLS. [REPO backend/app/services/analysis.py:217-231] [REPO backend/app/services/market_insight_ai.py:8-18]
- EFFORT: 300-450 LOC plus route/schema/dispatch/config/support-matrix updates and 8-10 tests if keyed policy exists. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: API key governance, rate-limit ambiguity, third-party copyright restrictions, vintage/revision handling, and series-ID selection. [DOC https://fred.stlouisfed.org/docs/api/terms_of_use.html] [KNOWLEDGE]
- PRELIM FIT-CLASS: DISQUALIFIED(keyed-now) for anonymous Tier-1; high utility later. [DOC https://fred.stlouisfed.org/docs/api/api_key.html] [REPO config/support_matrix.yaml:152-154]
- UNVERIFIED REMAINDER: Confirm exact numeric limits from official support or docs and identify a no-key bulk alternative if the owner wants an anonymous-only FRED-like path. [KNOWLEDGE]

### 3. OECD

- IDENTITY: Organisation for Economic Co-operation and Development data API / Data Explorer API; D27 host `sdmx.oecd.org` with docs at `www.oecd.org`. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html]
- ACCESS MODE: SDMX REST with XML, JSON, or CSV response formats; primary mode for economic outlook/statistics is SDMX data queries. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html]
- ANONYMITY VERDICT: KEYLESS (UNVERIFIED rate/ToS) because the official API page exposes public SDMX examples and no API-key requirement was found in the page read; follow-up must confirm ToS and throttles before build. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html] [KNOWLEDGE]
- RATE/TOS: No rate or attribution limit was found in the OECD page read; record as UNVERIFIED. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html]
- DATA CLASS: Numeric macro/statistical panel time series; pilot could use 2 datasets, 3 countries, and annual/quarterly slices. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed with an SDMX client and offline fixtures; Senate LDA mold only partially helps for rate/backoff/metadata logging. [REPO backend/app/services/connectors_senate_lda.py:145-159] [REPO backend/app/services/analysis.py:43-123]
- TIER + ESCALATION TRIGGERS: Tier-1 candidate if no new tables, no raw persistence, no key, and no default-on broad live egress; D27 host grant and request ledger still required. [REPO docs/program-context/02-decision-record.md:541-558] [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: Fixture budget 5 doc/API-shape captures after grant; live pilot 15 requests; fixtures should cover dataflow discovery, structure/codelist, one data query, empty result, and rate/error response. [REPO docs/program-context/02-decision-record.md:588-603] [KNOWLEDGE]
- UTILITY MAP: Feeds macro trend, decomposition, structural breaks, and cross-country comparisons; answers OECD-vs-energy trends, policy-regime breaks, and peer-country macro divergence; overlaps IMF, World Bank, and FRED. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 450-650 LOC plus SDMX parser, config, route/schema/dispatch, support-matrix assertions, and 10-12 tests. [REPO backend/app/schemas/api.py:278-301] [KNOWLEDGE]
- RISKS: SDMX structure complexity, dataset-code drift, large dimensions, rate silence, and macro overlap. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html] [KNOWLEDGE]
- PRELIM FIT-CLASS: VIABLE, pending auth/rate confirmation. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html] [REPO config/support_matrix.yaml:27-34]
- UNVERIFIED REMAINDER: Confirm no registration is required, exact rate/ToS terms, and stable dataflow IDs for a minimal pilot. [KNOWLEDGE]

### 4. IMF

- IDENTITY: International Monetary Fund IMF Data APIs and IMF DataMapper API; D27 hosts `data.imf.org`, `www.imf.org`, and possible API portal host `portal.api.imf.org`. [DOC https://data.imf.org/en/Resource-Pages/IMF-API] [DOC https://www.imf.org/external/datamapper/api/help]
- ACCESS MODE: IMF Data page says SDMX 2.1/3.0 APIs; DataMapper API is JSON time-series oriented. [DOC https://data.imf.org/en/Resource-Pages/IMF-API] [DOC https://www.imf.org/external/datamapper/api/help]
- ANONYMITY VERDICT: MIXED (UNVERIFIED production SDMX auth) because DataMapper help presents time-series endpoints without key language, while the IMF Data API page says swagger exploration uses a beta portal account sign-in. [DOC https://www.imf.org/external/datamapper/api/help] [DOC https://data.imf.org/en/Resource-Pages/IMF-API]
- RATE/TOS: No numeric rate limits were found in pages read; beta portal sign-in for swagger is a gating risk for SDMX exploration. [DOC https://data.imf.org/en/Resource-Pages/IMF-API] [KNOWLEDGE]
- DATA CLASS: Numeric macro/monetary time series and SDMX datasets; pilot could use DataMapper CPI/inflation-style annual series if keyless path is confirmed. [DOC https://www.imf.org/external/datamapper/api/help] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed; SDMX variant resembles OECD, DataMapper variant is simpler JSON. [REPO backend/app/services/analysis.py:43-123] [KNOWLEDGE]
- TIER + ESCALATION TRIGGERS: Tier-1 only for a confirmed no-key DataMapper slice with no durable schema/raw persistence; account-gated SDMX exploration would force owner decision. [REPO config/support_matrix.yaml:152-154] [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: Fixture budget 4 captures after grant; live pilot 10-15 requests; fixtures should cover indicator list, country list, one series, empty series, and malformed indicator. [DOC https://www.imf.org/external/datamapper/api/help] [KNOWLEDGE]
- UTILITY MAP: Feeds inflation, monetary, and country macro trend questions; overlaps OECD, World Bank, and FRED. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 350-600 LOC depending on DataMapper vs SDMX, plus 8-12 tests and support-matrix/front-door updates. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Ambiguous auth boundary, API migration, SDMX complexity, country/indicator code drift, and overlap. [DOC https://data.imf.org/en/Resource-Pages/IMF-API] [KNOWLEDGE]
- PRELIM FIT-CLASS: VIABLE only for DataMapper/no-key path; NEEDS-OWNER-DECISION for account-gated SDMX. [DOC https://www.imf.org/external/datamapper/api/help] [DOC https://data.imf.org/en/Resource-Pages/IMF-API]
- UNVERIFIED REMAINDER: Confirm whether production IMF Data SDMX calls require auth, whether DataMapper covers the owner's monetary/inflation use cases, and current ToS/rate limits. [KNOWLEDGE]

### 5. CFTC Commitment of Traders

- IDENTITY: U.S. Commodity Futures Trading Commission Commitment of Traders reports; D27 hosts `www.cftc.gov` and possibly `publicreporting.cftc.gov`. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [KNOWLEDGE]
- ACCESS MODE: Primary mode is public report/download pages with comma-delimited COT reports and long/short formats; Socrata/public-reporting access is possible but not verified by source docs here. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [KNOWLEDGE]
- ANONYMITY VERDICT: KEYLESS (UNVERIFIED Socrata/app-token limits) because the official COT page exposes public comma-delimited report links and no key requirement was found on the page read; Socrata app-token limits remain unverified. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [KNOWLEDGE]
- RATE/TOS: No automated-retrieval rate limit was found in the COT page read. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm]
- DATA CLASS: Weekly numeric positioning tables by market and trader class; pilot could use one current financial-futures comma-delimited report plus one historical fixture. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed or lightweight file-tabular connector; ScienceBase mold helps if treating report files as download targets, but no new tables are needed. [REPO backend/app/services/connectors_sciencebase.py:155-185] [REPO backend/app/services/analysis.py:43-123]
- TIER + ESCALATION TRIGGERS: Tier-1 candidate if keyless CFTC-hosted HTTPS report files are used, raw-content persistence is avoided, and only normalized CSV-like rows feed existing datasets. [REPO docs/program-context/00-posture-and-invariants.md:91-96] [REPO backend/app/services/connectors_sciencebase.py:1667-1675]
- EGRESS PLAN SKETCH: Fixture budget 3 report-page/file-shape captures after host grant; live pilot 5-8 requests; fixtures should cover current report, historical report, empty market filter, malformed row, and CFTC unavailable response. [REPO docs/program-context/02-decision-record.md:541-558] [KNOWLEDGE]
- UTILITY MAP: Feeds futures-positioning trend and correlation questions; answers "are commercial positions diverging", "which commodity positioning shifted", and "do positions lead prices"; overlaps EIA/OPEC/FAO/USGS commodity signals. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 250-400 LOC plus 7-10 tests if report format is stable and no Socrata auth path is used. [REPO tests/test_api.py:7410-7503] [KNOWLEDGE]
- RISKS: Legacy formats, file naming drift, weekly revisions, public-reporting host policy, and ambiguous Socrata throttles. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [KNOWLEDGE]
- PRELIM FIT-CLASS: STRONG for a CFTC-hosted current-report pilot; VIABLE if Socrata/public-reporting is required. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [KNOWLEDGE]
- UNVERIFIED REMAINDER: Confirm exact non-HTML report URLs, public-reporting/Socrata terms, and whether app tokens are optional for desired volumes. [KNOWLEDGE]

### 6. U.S. Census Bureau

- IDENTITY: U.S. Census Bureau developer APIs, including International Trade Program; D27 hosts `www.census.gov` and `api.census.gov`. [DOC https://www.census.gov/data/developers/data-sets.html]
- ACCESS MODE: REST API for many datasets; owner-implied trade path is International Trade monthly datasets. [DOC https://www.census.gov/data/developers/data-sets.html]
- ANONYMITY VERDICT: KEY-REQUIRED for current Census Data API use because Census says all Census Data API queries now require a key; microdata key guidance also says all microdata queries require a key. [DOC https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html] [DOC https://www.census.gov/data/developers/guidance/microdata-api-user-guide/api-key.html] [REPO config/support_matrix.yaml:152-154]
- RATE/TOS: Rate limits were not found in pages read; key setup and terms must be reviewed before any build. [DOC https://www.census.gov/data/developers/data-sets.html] [KNOWLEDGE]
- DATA CLASS: Numeric trade tables by month, product, partner, and flow; pilot could use a tiny imports/exports slice. [DOC https://www.census.gov/data/developers/data-sets.html] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed if keyed policy exists; current anonymous Tier-1 is blocked. [REPO backend/app/services/analysis.py:43-123] [REPO config/support_matrix.yaml:152-154]
- TIER + ESCALATION TRIGGERS: Not Tier-1 now due keyed source; keyed connector, secret, support-matrix, and policy surfaces are triggered. [REPO config/support_matrix.yaml:152-154] [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: After owner policy, fixture budget 4 keyed responses; live pilot 20 requests; fixtures should cover dataset discovery, variables, one trade query, invalid key, and empty result. [DOC https://www.census.gov/data/developers/data-sets.html] [KNOWLEDGE]
- UTILITY MAP: Feeds U.S. trade questions, product/partner shifts, and import/export breakpoints; overlaps WTO and UN Comtrade but has U.S.-specific monthly detail. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 350-500 LOC plus 8-12 tests after keyed policy. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Key requirement, API-variable complexity, Census 2026 auth change, trade taxonomy changes, and overlap. [DOC https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html] [KNOWLEDGE]
- PRELIM FIT-CLASS: DISQUALIFIED(keyed-now) for anonymous Tier-1; strong later for U.S. trade if policy changes. [DOC https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html] [REPO config/support_matrix.yaml:152-154]
- UNVERIFIED REMAINDER: Confirm exact trade API key/rate limits, allowed caching, and whether any non-API public trade CSV path can satisfy owner intent anonymously. [KNOWLEDGE]

### 7. USGS Mineral/Commodities Data

- IDENTITY: U.S. Geological Survey National Minerals Information Center, Mineral Commodity Summaries and data releases; D27 hosts `www.usgs.gov`, `data.usgs.gov`, `pubs.usgs.gov`, and possibly `www.sciencebase.gov`. [DOC https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries] [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9]
- ACCESS MODE: Public reports, data-release metadata, CSV table files, and Science Data Catalog/ScienceBase-harvested releases; the preferred primary pilot is CSV data release metadata, not PDF parsing. [DOC https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025] [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9]
- ANONYMITY VERDICT: KEYLESS because USGS data-catalog metadata says access is public and the USGS data-release page marks the work CC0; no key requirement was found in pages read. [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9] [DOC https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025]
- RATE/TOS: No rate limit was found in pages read; rights on the 2025 data-release page are CC0, while specific PDF/report terms should still be checked if PDF path is used. [DOC https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025] [KNOWLEDGE]
- DATA CLASS: Bulk tabular CSV files and report PDFs; pilot volume can be one annual data-release package or 3-5 commodity CSV tables. [DOC https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025] [KNOWLEDGE]
- TEMPLATE FIT: ScienceBase-mold if using ScienceBase/data-catalog item metadata and files; analytics-feed after ingest; existing MCS defaults and `*.usgs.gov` allowlist make this the closest existing overlap. [REPO backend/app/schemas/api.py:168-182] [REPO backend/app/services/sciencebase_connector/contracts.py:24-25]
- TIER + ESCALATION TRIGGERS: Tier-1 if only public metadata plus normalized CSV ingest is used and no raw-content persistence/new tables are added; PDF parsing or durable raw off-repo storage would trigger escalation. [REPO docs/program-context/00-posture-and-invariants.md:91-96] [REPO next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:53-63]
- EGRESS PLAN SKETCH: Fixture budget 5 requests after grant; live pilot 8-12 requests; fixtures should cover data-catalog metadata, ScienceBase-harvested item, one CSV metadata manifest, blocked external host, and malformed CSV. [REPO docs/program-context/02-decision-record.md:588-603] [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9]
- UTILITY MAP: Feeds commodity production/import/reliance trend questions and correlation with energy/macro series; answers "which minerals have rising import reliance", "which production series broke trend", and "which commodities correlate with trade stress"; overlaps ScienceBase MCS, CFTC, and trade sources. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 150-300 LOC if extending ScienceBase/MCS presets; 350-500 LOC if building direct USGS data-release discovery; 7-10 tests either way. [REPO backend/app/schemas/api.py:168-207] [KNOWLEDGE]
- RISKS: Relationship between ScienceBase catalog and USGS data catalog must be pinned, table schemas vary by release, PDF path is expensive, and file sizes can grow. [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9] [KNOWLEDGE]
- PRELIM FIT-CLASS: STRONG, especially as a ScienceBase-overlap/MCS slice rather than a PDF parser. [REPO backend/app/schemas/api.py:168-182] [DOC https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025]
- UNVERIFIED REMAINDER: Confirm exact ScienceBase item IDs/download surfaces for the desired release without downloading files, and decide whether direct `data.usgs.gov` hosts need a new D27 grant. [KNOWLEDGE]

### 8. FAO / FAOSTAT

- IDENTITY: Food and Agriculture Organization FAOSTAT; D27 hosts `www.fao.org` and likely API host `fenixservices.fao.org`. [DOC https://www.fao.org/faostat/en/] [KNOWLEDGE]
- ACCESS MODE: FAOSTAT web/API and CSV-style agricultural datasets; primary owner-implied path is agriculture production/trade/stocks tabular data. [DOC https://www.fao.org/faostat/en/] [KNOWLEDGE]
- ANONYMITY VERDICT: KEYLESS (UNVERIFIED auth/rate docs) because no key requirement was found on the official FAOSTAT page read, but the page did not expose usable auth/rate text in this browser. [DOC https://www.fao.org/faostat/en/] [KNOWLEDGE]
- RATE/TOS: UNVERIFIED; no source-owned rate/ToS details were available within the page read budget. [DOC https://www.fao.org/faostat/en/]
- DATA CLASS: Numeric agricultural panel tables; pilot could use one commodity group, 3 countries, 5 years, and production/trade/stocks variables. [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed after tabular ingest; not ScienceBase mold unless using downloadable files rather than API. [REPO backend/app/services/analysis.py:43-123] [KNOWLEDGE]
- TIER + ESCALATION TRIGGERS: Tier-1 only after keyless/rate confirmation and if no raw-content persistence/new tables are added. [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: Fixture budget 5 requests after grant; live pilot 10-15 requests; fixtures should cover domains, item/country dimensions, one data slice, empty result, and error/rate behavior. [REPO docs/program-context/02-decision-record.md:541-558] [KNOWLEDGE]
- UTILITY MAP: Feeds agricultural production/trade trends and commodity risk comparisons; answers "which crops have production breaks", "which countries dominate stock shifts", and "does ag trade correlate with macro stress"; overlaps UN Comtrade/WTO/Census for trade and CFTC for commodity signals. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 350-550 LOC plus 8-12 tests after official API/auth docs are pinned. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: API docs visibility, terminology/dimension complexity, large panel responses, and ToS/rate ambiguity. [DOC https://www.fao.org/faostat/en/] [KNOWLEDGE]
- PRELIM FIT-CLASS: VIABLE but not build-ready until official API terms/auth are confirmed. [DOC https://www.fao.org/faostat/en/] [KNOWLEDGE]
- UNVERIFIED REMAINDER: Confirm API documentation URL, exact FQDN, anonymous access, rate limits, and stable dimensions for a pilot. [KNOWLEDGE]

### 9. OPEC

- IDENTITY: Organization of the Petroleum Exporting Countries publications, including Monthly Oil Market Report; D27 host `www.opec.org`. [DOC https://www.opec.org]
- ACCESS MODE: Public web publications and PDF reports; no machine API was verified in pages read. [DOC https://www.opec.org]
- ANONYMITY VERDICT: KEYLESS for public report pages, but PDF/document-only for the owner-implied oil report content and not an anonymous API candidate. [DOC https://www.opec.org] [KNOWLEDGE]
- RATE/TOS: No automated-retrieval rate limit was found; OPEC publication/copyright terms must be reviewed before any extraction. [DOC https://www.opec.org] [KNOWLEDGE]
- DATA CLASS: Documents-PDF and publication pages; pilot would be small in request count but high in parsing cost. [DOC https://www.opec.org] [KNOWLEDGE]
- TEMPLATE FIT: Infeasible-now for current Tier-1 analytics because PDF parsing/raw document handling is outside public connector claims; could become a document-ingest/Tier-2 program. [REPO docs/support-matrix-local-expert.md:82-84] [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- TIER + ESCALATION TRIGGERS: Not Tier-1 if PDF parsing/raw-content persistence is required; OCR/document processing and raw persistence trigger escalation. [REPO docs/support-matrix-local-expert.md:82-84] [REPO next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:53-63]
- EGRESS PLAN SKETCH: Fixture-only research could use 2-3 HTML publication metadata pages; live pilot should be deferred until PDF permissions and parsing scope are authorized. [REPO docs/program-context/02-decision-record.md:541-558] [KNOWLEDGE]
- UTILITY MAP: Oil-market context can answer demand/supply balance questions and overlap EIA energy series, but current analysis consumers need structured numeric tables first. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 700+ LOC plus document parsing tests if pursued; near-zero connector value unless structured table extraction is authorized. [REPO docs/support-matrix-local-expert.md:82-84] [KNOWLEDGE]
- RISKS: PDF parsing, copyright/usage terms, report layout drift, OCR scope, and direct overlap with cleaner EIA structured sources. [DOC https://www.opec.org] [KNOWLEDGE]
- PRELIM FIT-CLASS: WEAK for this lane. [REPO docs/support-matrix-local-expert.md:82-84] [KNOWLEDGE]
- UNVERIFIED REMAINDER: Confirm whether OPEC offers a structured data API or CSV tables, and review publication terms before any PDF handling. [KNOWLEDGE]

### 10. BLS - Bureau of Labor Statistics

- IDENTITY: U.S. Bureau of Labor Statistics Public Data API; D27 hosts `www.bls.gov` and `api.bls.gov`. [DOC https://www.bls.gov/developers/home.htm] [DOC https://www.bls.gov/developers/api_signature_v2.htm]
- ACCESS MODE: REST API with JSON-style signatures for employment, wages, productivity, and related time series. [DOC https://www.bls.gov/developers/home.htm] [DOC https://www.bls.gov/developers/api_signature_v2.htm]
- ANONYMITY VERDICT: KEY-OPTIONAL because BLS FAQ says unregistered users may request 25 queries daily, 25 series per query, and 10 years per query, while registered users get higher limits. [DOC https://www.bls.gov/developers/api_faqs.htm]
- RATE/TOS: Registered limit is 500 queries daily, 50 series per query, and 20 years per query; anonymous limit is 25 queries daily, 25 series per query, and 10 years per query. [DOC https://www.bls.gov/developers/api_faqs.htm]
- DATA CLASS: Numeric labor/productivity/wage time series; pilot can fit anonymous limits with 3-5 series and 10 years. [DOC https://www.bls.gov/developers/api_faqs.htm] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed; optional parameters requiring registration key should be excluded from Tier-1 anonymous pilot. [DOC https://www.bls.gov/developers/api_signature_v2.htm] [REPO backend/app/services/analysis.py:43-123]
- TIER + ESCALATION TRIGGERS: Tier-1 candidate only if anonymous limits are enforced in config/tests and no registration-key path is selected; optional-key expansion would hit keyed boundary. [REPO config/support_matrix.yaml:152-154] [DOC https://www.bls.gov/developers/api_faqs.htm]
- EGRESS PLAN SKETCH: Fixture budget 4 requests after grant; live pilot 8-12 requests under anonymous cap; fixtures should cover one series, multi-series, anonymous-limit planning, invalid series, and optional-parameter rejection. [REPO docs/program-context/02-decision-record.md:588-603] [DOC https://www.bls.gov/developers/api_signature_v2.htm]
- UTILITY MAP: Feeds employment/wage/productivity trends, macro correlations, and structural breaks; answers "did productivity break trend", "do wages correlate with inflation", and "which labor series diverged"; overlaps FRED/World Bank/OECD macro. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 250-400 LOC plus 7-10 tests for anonymous-only guardrails. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Anonymous cap, series-ID discovery, optional parameter key temptation, annual revisions, and no catalog in API docs. [DOC https://www.bls.gov/developers/api_faqs.htm] [DOC https://www.bls.gov/developers/api_signature_v2.htm]
- PRELIM FIT-CLASS: STRONG for a deliberately tiny anonymous pilot. [DOC https://www.bls.gov/developers/api_faqs.htm] [REPO config/support_matrix.yaml:27-34]
- UNVERIFIED REMAINDER: Confirm ToS/attribution, exact base endpoint behavior without calling it, and the best public series-ID source for fixtures. [KNOWLEDGE]

### 11. WTO

- IDENTITY: World Trade Organization API Developer Portal; D27 host `apiportal.wto.org`, with runtime API host still to be confirmed. [DOC https://apiportal.wto.org/] [DOC https://apiportal.wto.org/apis]
- ACCESS MODE: API portal products for trade statistics; primary owner-implied mode is trade statistics API, but specific endpoints were not opened. [DOC https://apiportal.wto.org/apis] [KNOWLEDGE]
- ANONYMITY VERDICT: KEY-REQUIRED because the portal says users sign up for an API key before consuming APIs. [DOC https://apiportal.wto.org/] [REPO config/support_matrix.yaml:152-154]
- RATE/TOS: Portal pages read did not expose numeric rate limits; registration terms require follow-up if policy allows keyed sources. [DOC https://apiportal.wto.org/] [DOC https://apiportal.wto.org/apis]
- DATA CLASS: Numeric trade-statistics API data; pilot likely tabular panel slices. [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed after keyed policy; current anonymous connector unit is blocked. [REPO backend/app/services/analysis.py:43-123] [REPO config/support_matrix.yaml:152-154]
- TIER + ESCALATION TRIGGERS: Not Tier-1 because API-key signup collides with unsupported keyed connectors. [REPO config/support_matrix.yaml:152-154]
- EGRESS PLAN SKETCH: After owner keyed-policy grant, fixture budget 4 docs/responses; live pilot 10-15 API requests; fixtures should cover product list, dimensions, one data slice, invalid key, and rate/error response. [REPO docs/program-context/02-decision-record.md:541-558] [KNOWLEDGE]
- UTILITY MAP: Feeds global trade trend and cross-country comparisons; overlaps UN Comtrade and Census Trade. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 350-550 LOC plus 8-12 tests after key policy. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Key signup, portal docs behind account flows, runtime host unknown, trade taxonomy complexity, and overlap. [DOC https://apiportal.wto.org/] [KNOWLEDGE]
- PRELIM FIT-CLASS: DISQUALIFIED(keyed-now) for anonymous Tier-1. [DOC https://apiportal.wto.org/] [REPO config/support_matrix.yaml:152-154]
- UNVERIFIED REMAINDER: Confirm runtime API FQDN, rate limits, ToS, and whether any WTO bulk open data path is keyless. [KNOWLEDGE]

### 12. UN Comtrade

- IDENTITY: United Nations Comtrade database and developer portal; D27 hosts `comtradedeveloper.un.org`, `comtradeplus.un.org`, and likely runtime host `comtradeapi.un.org`. [DOC https://comtradedeveloper.un.org/] [DOC https://comtradeplus.un.org/API] [KNOWLEDGE]
- ACCESS MODE: Developer portal/API and Comtrade Plus data pages for trade flows; primary owner-implied mode is global commodity trade flows API. [DOC https://comtradedeveloper.un.org/] [DOC https://comtradeplus.un.org/API]
- ANONYMITY VERDICT: KEY-REQUIRED (UNVERIFIED anonymous preview limits) because the developer portal redirects to sign-in and official search/result text says users sign up to acquire keys; the exact anonymous preview/download limits need account-free doc confirmation. [DOC https://comtradedeveloper.un.org/] [DOC https://comtradeplus.un.org/TradeFlow] [KNOWLEDGE] [REPO config/support_matrix.yaml:152-154]
- RATE/TOS: Search-discovered official text indicates a free key path with call/record limits, but no usable account-free rate page was read; mark exact limits UNVERIFIED. [DOC https://comtradeplus.un.org/TradeFlow] [KNOWLEDGE]
- DATA CLASS: Numeric global trade-flow panel data by reporter, partner, product, flow, and period. [DOC https://comtradeplus.un.org/API] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed after keyed policy; not Tier-1 anonymous now. [REPO backend/app/services/analysis.py:43-123] [REPO config/support_matrix.yaml:152-154]
- TIER + ESCALATION TRIGGERS: Not Tier-1 because key/account path appears required for meaningful API use; keyed connector policy and D27 grant are needed. [REPO config/support_matrix.yaml:152-154] [REPO docs/program-context/02-decision-record.md:541-558]
- EGRESS PLAN SKETCH: After policy, fixture budget 5 docs/responses; live pilot 10-15 requests; fixtures should cover metadata, one trade flow, pagination/record cap, invalid key, and empty result. [KNOWLEDGE]
- UTILITY MAP: Highest global trade coverage for commodity-flow questions; overlaps WTO and Census but broader than Census and more detailed than many WTO summaries. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 450-650 LOC plus 10-12 tests after auth/terms are resolved. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Account/key requirement, premium/free split, record caps, product taxonomy, large result handling, and portal JS opacity. [DOC https://comtradedeveloper.un.org/] [KNOWLEDGE]
- PRELIM FIT-CLASS: DISQUALIFIED(keyed-now) for anonymous Tier-1; strong later for trade breadth. [REPO config/support_matrix.yaml:152-154] [KNOWLEDGE]
- UNVERIFIED REMAINDER: Confirm official no-login docs for key limits, ToS, runtime API host, and whether small previews can be used anonymously without account creation. [KNOWLEDGE]

### 13. Bureau of Transportation Statistics

- IDENTITY: U.S. Bureau of Transportation Statistics statistical products and BTS Open Data catalog; D27 hosts `www.bts.gov`, `data.bts.gov`, and possibly `www.transtats.bts.gov`. [DOC https://www.bts.gov/browse-statistical-products-and-data] [DOC https://data.bts.gov/]
- ACCESS MODE: Public statistical product pages, BTS Open Data catalog, and likely Socrata-style tabular APIs/downloads; primary owner-implied mode is freight/maritime/rail tabular data. [DOC https://www.bts.gov/browse-statistical-products-and-data] [KNOWLEDGE]
- ANONYMITY VERDICT: MIXED (UNVERIFIED API auth/rate docs) because the BTS pages expose public data products and catalog pages, but source-owned API auth/rate docs were not found in the pages read. [DOC https://www.bts.gov/browse-statistical-products-and-data] [DOC https://data.bts.gov/] [KNOWLEDGE]
- RATE/TOS: No source-owned rate-limit page was found; Socrata/app-token behavior should not be assumed without source-owned confirmation. [DOC https://data.bts.gov/] [KNOWLEDGE]
- DATA CLASS: Numeric transportation/freight time series and tabular datasets; pilot could use Monthly Transportation Statistics or TransBorder Freight metadata. [DOC https://www.bts.gov/browse-statistical-products-and-data] [KNOWLEDGE]
- TEMPLATE FIT: Analytics-feed or file-tabular connector; no new tables needed if normalized rows feed existing datasets. [REPO backend/app/services/analysis.py:43-123] [KNOWLEDGE]
- TIER + ESCALATION TRIGGERS: Tier-1 only after anonymous API/download terms are confirmed and raw persistence/new tables are avoided. [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: Fixture budget 5 requests after grant; live pilot 8-12 requests; fixtures should cover catalog metadata, one tabular view, transport-series rows, missing dataset, and rate/error behavior. [REPO docs/program-context/02-decision-record.md:588-603] [KNOWLEDGE]
- UTILITY MAP: Feeds logistics/freight trend and correlation questions; answers "are freight indicators breaking trend", "do port metrics correlate with trade", and "which transport modes diverge"; overlaps Census/Comtrade trade and macro sources. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 300-500 LOC plus 8-10 tests after source-owned API docs are pinned. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Catalog/API docs ambiguity, Socrata dependence, host stability, data product heterogeneity, and large datasets. [DOC https://www.bts.gov/browse-statistical-products-and-data] [KNOWLEDGE]
- PRELIM FIT-CLASS: VIABLE but not first until anonymous/rate facts are official. [DOC https://www.bts.gov/browse-statistical-products-and-data] [KNOWLEDGE]
- UNVERIFIED REMAINDER: Confirm official API/developer docs on source-owned hosts, anonymous limits, and best freight/maritime/rail pilot tables. [KNOWLEDGE]

### 14. World Bank

- IDENTITY: World Bank Indicators API and Developer Information; D27 hosts `api.worldbank.org` and `datahelpdesk.worldbank.org`. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation] [DOC https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information]
- ACCESS MODE: REST Indicators API plus SDMX/catalog query docs; primary owner-implied mode is development and macro indicator time series. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation] [DOC https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information]
- ANONYMITY VERDICT: KEYLESS because the World Bank doc says API keys and other authentication methods are no longer necessary. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- RATE/TOS: No numeric rate limit was found in pages read; World Bank help desk page points to website terms of use. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- DATA CLASS: Nearly 16,000 numeric time-series indicators across 45+ databases; pilot could use 3 indicators, 5 countries, annual data. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- TEMPLATE FIT: Analytics-feed with simple REST pagination and existing dataset/analysis consumers. [REPO backend/app/services/analysis.py:43-123] [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- TIER + ESCALATION TRIGGERS: Tier-1 candidate if host grant is named, request budget is finite, and no new tables/raw persistence/default-on behavior are introduced. [REPO docs/program-context/02-decision-record.md:541-558] [REPO docs/program-context/00-posture-and-invariants.md:91-96]
- EGRESS PLAN SKETCH: Fixture budget 5 requests after grant; live pilot 10-15 requests; fixtures should cover indicator metadata, country query, one indicator series, pagination, and error/empty result. [REPO docs/program-context/02-decision-record.md:588-603] [KNOWLEDGE]
- UTILITY MAP: Feeds macro/development trend, decomposition, break, and cross-correlation questions; answers "which countries diverged", "which indicators broke trend", and "how macro indicators correlate with commodity data"; overlaps IMF/OECD/FRED/BLS. [REPO backend/app/services/analysis.py:217-231] [KNOWLEDGE]
- EFFORT: 250-400 LOC plus 7-10 tests. [REPO backend/app/api/router.py:154-160] [KNOWLEDGE]
- RISKS: Indicator selection, pagination, country-code drift, missing values, and macro overlap. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation] [KNOWLEDGE]
- PRELIM FIT-CLASS: STRONG for anonymous Tier-1 breadth. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation] [REPO config/support_matrix.yaml:27-34]
- UNVERIFIED REMAINDER: Confirm website terms, polite request rate, and the exact minimal indicator/country fixture set. [KNOWLEDGE]

## 3. Cross-Cutting Synthesis

- Dedup matrix - macro: FRED, OECD, IMF, BLS, and World Bank all answer macro time-series questions; FRED/Census/WTO/Comtrade are blocked by keys, BLS and World Bank are the best anonymous/near-anonymous macro first slices, and OECD/IMF need auth/rate confirmation. [DOC https://fred.stlouisfed.org/docs/api/api_key.html] [DOC https://www.bls.gov/developers/api_faqs.htm] [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation] [REPO config/support_matrix.yaml:152-154]
- Dedup matrix - trade: Census, WTO, and UN Comtrade overlap on trade flows; Census is U.S.-monthly and keyed, WTO is portal-keyed, and UN Comtrade is global/high-coverage but appears keyed/account-gated. [DOC https://www.census.gov/data/developers/data-sets.html] [DOC https://apiportal.wto.org/] [DOC https://comtradedeveloper.un.org/]
- Dedup matrix - energy/commodities: EIA and OPEC overlap oil/energy, but EIA API is keyed and OPEC is PDF-heavy; CFTC, USGS, and FAO add positioning/minerals/agriculture commodity signals with better anonymous potential. [DOC https://www.eia.gov/opendata/register.php] [DOC https://www.opec.org] [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9]
- Two-first-units recommendation input: World Bank plus USGS MCS/Data Release maximizes anonymous Tier-1 coverage-per-effort because World Bank gives broad macro time series and USGS gives commodity/materials data while reusing the existing ScienceBase/MCS seam. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation] [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9] [REPO backend/app/schemas/api.py:168-182]
- Next-best anonymous follow-ups: BLS is strong if anonymous caps are encoded as hard limits; CFTC COT is strong if CFTC-hosted report URLs and terms are confirmed; OECD and FAO are viable after auth/rate docs are pinned. [DOC https://www.bls.gov/developers/api_faqs.htm] [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm] [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html] [DOC https://www.fao.org/faostat/en/]
- Policy-program bucket: EIA API, FRED, Census Data API, WTO, and likely UN Comtrade need keyed-connector governance before implementation. [DOC https://www.eia.gov/opendata/register.php] [DOC https://fred.stlouisfed.org/docs/api/api_key.html] [DOC https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html] [DOC https://apiportal.wto.org/] [DOC https://comtradedeveloper.un.org/] [REPO config/support_matrix.yaml:152-154]
- Registry gap: existing analysis supports time-series correlation, decomposition, structural breaks, and descriptive summary, but the candidate set suggests future methods for panel ranking/peer comparison, trade-share/market-concentration decomposition, revision-aware vintage analysis, and commodity balance arithmetic. [REPO backend/app/services/analysis.py:43-123] [KNOWLEDGE]

## 4. Research-Request Ledger

Doc-page requests counted: 33 official/source-owned HTTPS pages requested or opened for documentation/registration/metadata facts; budget was max 60 total and max 4 per candidate. [REPO state/agent-inbox/source-candidates-investigation-source.md]

- EIA 1/3: `https://www.eia.gov/opendata/documentation.php` - API documentation, response mode, API hierarchy. [DOC https://www.eia.gov/opendata/documentation.php]
- EIA 2/3: `https://www.eia.gov/opendata/register.php` - API key requirement and bulk exception. [DOC https://www.eia.gov/opendata/register.php]
- EIA 3/3: `https://www.eia.gov/opendata/faqs.php` - row limits and throttle guidance. [DOC https://www.eia.gov/opendata/faqs.php]
- FRED 1/4: `https://fred.stlouisfed.org/docs/api/api_key.html` - API key requirement. [DOC https://fred.stlouisfed.org/docs/api/api_key.html]
- FRED 2/4: `https://fred.stlouisfed.org/docs/api/fred/` - API overview and modes. [DOC https://fred.stlouisfed.org/docs/api/fred/]
- FRED 3/4: `https://fred.stlouisfed.org/docs/api/fred/errors.html` - rate-limit/error behavior. [DOC https://fred.stlouisfed.org/docs/api/fred/errors.html]
- FRED 4/4: `https://fred.stlouisfed.org/docs/api/terms_of_use.html` - terms, key, limits, copyright obligations. [DOC https://fred.stlouisfed.org/docs/api/terms_of_use.html]
- OECD 1/1: `https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html` - SDMX API docs and response formats. [DOC https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html]
- IMF 1/2: `https://data.imf.org/en/Resource-Pages/IMF-API` - IMF Data SDMX API page and swagger sign-in note. [DOC https://data.imf.org/en/Resource-Pages/IMF-API]
- IMF 2/2: `https://www.imf.org/external/datamapper/api/help` - DataMapper API time-series docs. [DOC https://www.imf.org/external/datamapper/api/help]
- CFTC 1/1: `https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm` - COT reports and comma-delimited links. [DOC https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm]
- Census 1/4: `https://www.census.gov/data/developers/data-sets.html` - available APIs and International Trade listing. [DOC https://www.census.gov/data/developers/data-sets.html]
- Census 2/4: `https://www.census.gov/data/developers/guidance/api-key-setup.html` - requested key-setup guidance; no decisive excerpt used. [DOC https://www.census.gov/data/developers/guidance/api-key-setup.html]
- Census 3/4: `https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html` - all-query key requirement. [DOC https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html]
- Census 4/4: `https://www.census.gov/data/developers/guidance/microdata-api-user-guide/api-key.html` - microdata API key guidance. [DOC https://www.census.gov/data/developers/guidance/microdata-api-user-guide/api-key.html]
- USGS 1/3: `https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries` - MCS publication page. [DOC https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries]
- USGS 2/3: `https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9` - 2026 MCS data-catalog metadata and ScienceBase harvest. [DOC https://data.usgs.gov/datacatalog/data/USGS%3A69837ec8b66b01367d7ec7d9]
- USGS 3/3: `https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025` - 2025 CSV/table-file data-release metadata. [DOC https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025]
- FAO 1/1: `https://www.fao.org/faostat/en/` - official FAOSTAT page; no usable auth/rate excerpt returned. [DOC https://www.fao.org/faostat/en/]
- OPEC 1/1: `https://www.opec.org` - OPEC publications navigation and MOMR listing. [DOC https://www.opec.org]
- BLS 1/3: `https://www.bls.gov/developers/home.htm` - Public Data API developer home. [DOC https://www.bls.gov/developers/home.htm]
- BLS 2/3: `https://www.bls.gov/developers/api_signature_v2.htm` - v2 signatures and optional key parameters. [DOC https://www.bls.gov/developers/api_signature_v2.htm]
- BLS 3/3: `https://www.bls.gov/developers/api_faqs.htm` - anonymous/registered limits. [DOC https://www.bls.gov/developers/api_faqs.htm]
- WTO 1/2: `https://apiportal.wto.org/` - API key signup requirement. [DOC https://apiportal.wto.org/]
- WTO 2/2: `https://apiportal.wto.org/apis` - API list portal page. [DOC https://apiportal.wto.org/apis]
- UN Comtrade 1/3: `https://comtradedeveloper.un.org/` - developer portal sign-in page. [DOC https://comtradedeveloper.un.org/]
- UN Comtrade 2/3: `https://comtradeplus.un.org/API` - Comtrade API/resource page; JS rendered no detailed excerpt. [DOC https://comtradeplus.un.org/API]
- UN Comtrade 3/3: `https://comtradeplus.un.org/TradeFlow` - Comtrade trade-flow page; no API call or data download performed. [DOC https://comtradeplus.un.org/TradeFlow]
- BTS 1/3: `https://data.bts.gov/` - BTS Open Data catalog page. [DOC https://data.bts.gov/]
- BTS 2/3: `https://data.bts.gov/developers` - requested developer page; no decisive source-owned excerpt used. [DOC https://data.bts.gov/developers]
- BTS 3/3: `https://www.bts.gov/browse-statistical-products-and-data` - statistical products/data list. [DOC https://www.bts.gov/browse-statistical-products-and-data]
- World Bank 1/2: `https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation` - Indicators API access/auth documentation. [DOC https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- World Bank 2/2: `https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information` - Developer Information index. [DOC https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information]

No data API endpoint was deliberately invoked, no dataset/bulk file/PDF/CSV/XLSX was downloaded, no account was created, and no API key was requested or used. A search-result snippet exposed a BTS JSON endpoint and OPEC PDF results, but those endpoint/PDF URLs were not opened, cited as evidence, or used for classification. [KNOWLEDGE]


---

## Adjudication record

# Source-Candidates Adjudication (orchestrator, 2026-07-07)

Basis: state/agent-inbox/source-candidates-dossier.md (M-SOURCE-CANDIDATES-INVESTIGATION,
investigation lane, 14/14 candidates, 33-request doc ledger) + orchestrator independent verification.
Repo authority: project6-origin/main @ 3c669256. Gating rule: keyed source = collides with
keyed_connectors unsupported (support_matrix.yaml) = policy program, not a Tier-1 unit.

## Orchestrator verification performed (beyond delegate self-report)
- DIRECT re-read (WebFetch): World Bank keyless quote ("API keys and other authentication
  methods are no longer necessary"); EIA key-required + keyless-bulk exception; Census
  key-required ("The Census Bureau now requires an API key for all queries made to the Census
  Data API" — a 2026 change from the historical optional-key posture); USGS MCS 2025 release
  CC0/CSV; CFTC COT comma-delimited files public AND the decisive Public Reporting API quote
  the dossier lacked: "Currently, we are not providing tokens to use the Public Reporting
  APIs" — CFTC is confirmed token-less on BOTH paths (upgrade vs dossier's UNVERIFIED remainder).
- BOT-BLOCKED (WebFetch 403 / curl empty / browse daemon broken): FRED api_key page, BLS FAQ.
  Both accepted on delegate [DOC] quote + exact knowledge-match + verdict-insensitivity
  (FRED is keyed under any reading; BLS caps 25/day/25-series/10-years anonymous vs
  500/50/20 registered match the published v2 numbers exactly). Honest caveat recorded.
- REPO anchors spot-checked on live main: keyed_connectors unsupported; Senate LDA
  max_rps=2.0 / lda.senate.gov / official_api_only / metadata_only; analysis.py method names
  (55 hits); MCS default query "Mineral Commodity Summaries"; *.usgs.gov allowlist. All match.

## CLASSIFICATION

### INCLUDE-NOW (anonymous Tier-1, build-ready; fixture-first, live gated on D27 grant)
1. WORLD BANK Indicators API — keyless (orchestrator-verified), simple REST/JSON, ~16k macro
   indicators, 250-400 LOC + 7-10 tests, analytics-feed onto existing 4-method registry.
   D27 grant when live: host api.worldbank.org, pilot budget <=15.
2. CFTC COT — keyless BOTH paths (orchestrator-verified: comma-delimited files + token-less
   Public Reporting API), weekly positioning tables = a signal class nothing else on the list
   provides, 250-400 LOC. D27 grant when live: www.cftc.gov (+ publicreporting.cftc.gov if PRE
   path chosen), pilot budget <=8.
3. USGS MCS data-release — keyless/CC0 (orchestrator-verified), CSV tables. PATH DECISION for
   owner/mandate: (a) extend the EXISTING ScienceBase/MCS seam (default query is already
   "Mineral Commodity Summaries"; *.usgs.gov already allowlisted; 150-300 LOC; possibly NO new
   D27 host class) vs (b) direct data.usgs.gov discovery (new host grant, 350-500 LOC).
   Recommend (a) first.

### INCLUDE-CONDITIONAL (one bounded confirmation each, then mandate-ready)
4. BLS — key-optional; anonymous caps 25/day, 25 series/query, 10 years/query. CONDITION:
   encode anonymous caps as hard config+test limits; registration-key path explicitly out of
   fence. Confirm ToS/attribution in mandate Phase 0.
5. OECD SDMX — keyless-apparent; CONDITION: pin auth/rate/ToS from official docs (the one page
   read was silent). SDMX parser adds effort (450-650 LOC).
6. IMF DataMapper — keyless-apparent for DataMapper JSON (SDMX portal shows account-gated
   swagger); CONDITION: confirm no-key production path + that DataMapper covers the
   monetary/inflation questions. If only SDMX portal works => NEEDS-OWNER-DECISION.

### DEFER (park until an operator question needs them)
7. FAO/FAOSTAT — likely keyless; official API host/docs/ToS unpinned (fao.org page was
   JS-opaque). Ag coverage partially reachable via World Bank indicators meanwhile.
8. BTS — public Socrata catalog, but source-owned auth/rate docs not found. NOTE: CFTC's
   token-less statement is CFTC-specific; do NOT generalize to BTS's Socrata instance.

### EXCLUDE — keyed (parked behind an owner-authorized keyed-connector policy program)
9.  EIA API (key-required; keyless BULK facility exists — optional future file-connector variant).
10. FRED (key-required).
11. Census Data API (key-required — 2026 change, orchestrator-verified; owner's starred
    candidate: high utility, but it is now a policy-program candidate, not an anonymous unit).
12. WTO (portal key signup).
13. UN Comtrade (key/account-gated).
These five become ONE owner decision ("charter a keyed-connector policy program: secrets
handling, support-matrix reclassification, per-source ToS") — not five separate questions.

### EXCLUDE — shape mismatch
14. OPEC — PDF-only publications, no structured API found; document-ingest would be a separate
    (Tier-2-ish) program; energy coverage available cleaner via EIA bulk (keyless) if ever needed.

## Portfolio call (orchestrator override of delegate pairing, reasoned)
First two units: WORLD BANK + CFTC COT (delegate suggested WB + USGS). Rationale: USGS is
partially reachable TODAY through the existing ScienceBase MCS seam, so a new unit there adds
less net-new capability than CFTC's wholly-new positioning-signal class; and both WB + CFTC
anonymity verdicts are orchestrator-verified directly. USGS slots third as the cheap
seam-extension. Delegate pairing remains valid if the owner weights minerals over positioning.

## Standing constraints for every build mandate (from repo posture, all verified)
Fixture-first: build+test fully offline (3-5 canned responses per source; zero egress, no grant
needed). First LIVE request gated on a NAMED D27 grant (host class + finite budget) executed as
a D28 arming record + per-request ledger. Tier-1 fence: zero new tables (alias onto
ConnectorRun*/Dataset* like Senate LDA), no raw-content persistence, no key handling, https-only
+ host allowlist + SSRF private-IP rejection in-code, serial rate-limited client (~2rps
token-bucket mold), support-matrix exact-assert set updated (support_matrix.yaml + constants +
check scripts + runtime-contract audit + README front door + local-expert doc + mirrored tests),
7-12 tests in the PR-1..PR-5 lane pattern. Hardware rail: serial, no xdist beyond 4, CI-first soak.

## Open owner decisions surfaced
- OD-1: approve first-unit pairing (WB + CFTC recommended) or reorder.
- OD-2: USGS path (a) ScienceBase-seam extension vs (b) new data.usgs.gov host class.
- OD-3: D27 grants at live-pilot time (per unit; fixture builds need none).
- OD-4: whether a keyed-connector policy program is EVER wanted (unlocks EIA/FRED/Census/WTO/
  Comtrade as a class). No urgency; anonymous frontier is deep enough for multiple units.
- OD-5: BLS anonymous-cap acceptance (25/day is tight but sufficient for a pilot slice).

---

# REV 2 — SECOND-PASS CORRECTIONS (2026-07-07; second-pass audit audit: fidelity + repo-spec + risk; all
# verdicts CONFIRMED unchanged, corrections below SUPERSEDE conflicting rev-1 lines)

## R2.1 Classification-entry corrections
- #1 WORLD BANK: ToS now CONFIRMED PERMISSIVE (data.worldbank.org/summary-terms-of-use: "You may
  use our application programming interfaces ('APIs') to facilitate access to the Datasets...");
  no published rate limit. NEW OBLIGATION carried into the unit mandate: record ToS URL +
  ATTRIBUTION requirement in the connector's provenance surface (DatasetSourceProvenance, senate
  mold); keep ~2rps token-bucket as politeness default. (Rev-1 had silently dropped the
  dossier's unread-ToS remainder.)
- #2 CFTC: effort estimate is CONDITIONAL — 250-400 LOC assumes current-format files and no
  Socrata auth path; legacy-format/naming-drift/weekly-revision risks stand; exact non-HTML
  report URLs to be pinned during the fixture phase. PRE host FQDN (publicreporting.cftc.gov)
  is KNOWLEDGE-only — confirm from official docs at grant time if the PRE path is chosen.
- #3 USGS path (a) gains Phase-0 step: pin exact ScienceBase item IDs / download surfaces for
  the target MCS release (metadata-only, no downloads).
- #4 BLS: the Phase-0 ToS confirmation is UN-EXECUTABLE by agent tooling (whole bls.gov +
  stlouisfed.org doc trees bot-block WebFetch/curl; archive.org blocked at tool level; browse
  daemon broken). Condition restated: owner does a manual browser check of
  developers/termsOfService.htm + api_faqs.htm and pastes quotes into the mandate artifact, OR
  explicitly accepts the knowledge-matched caps (25/day, 25 series, 10y) with a hard-config
  fence. Route must be pre-stated; silent waiver forbidden.
- #8 BTS: "public Socrata catalog" softened to "apparent Socrata-style catalog (unconfirmed by
  source-owned docs)".
- #14 OPEC: EIA-bulk sufficiency softened — "energy coverage likely available cleaner via
  keyless EIA bulk (slice coverage unconfirmed)". Exclusion unaffected.
- FRED: alternate-route verification ATTEMPTED AND FAILED this pass (archive.org tool-blocked;
  research.stlouisfed.org 403; sibling doc pages 403). Delegate-quote + knowledge-match +
  verdict-insensitivity remains the recorded basis; exclusion stands.

## R2.2 Build-mandate checklist — REPO surfaces rev-1 MISSED (all repo-verified, file:line in
## audit record; these are MANDATORY for any connector landing)
a) OPERATOR-IDENTITY SEAM (was entirely absent): new POST handler MUST call
   _route_level_operator_identity(request, access="write") in-handler (senate precedent
   router.py:446-457) AND register (f"{p}/connectors/<x>/runs", "write") in the _exact list of
   _build_static_pre_body_routes in backend/main.py (~:292). Enforced bidirectionally by
   test_pre_body_operator_authorization.py and
   test_layer3_post_route_operator_authorization_coverage.py (via backend/tests/_route_enum.py).
   Optional but conventional: add route to the parametrized 401 list in
   backend/tests/test_legacy_api_operator_identity.py:117.
b) SUPPORT-MATRIX ASSERT SET = EIGHT surfaces (rev-1 implied six): config/support_matrix.yaml
   (new capability entry WITH PR-1..PR-5 evidence markers) + scripts/support_matrix_constants.py
   + scripts/support_matrix_check.py + scripts/support_matrix_runtime_contract_audit.py
   (**author a NEW runtime probe fn + PROBES entry, ~60-70 LOC — audit fails closed on
   undeclared capabilities**) + backend/tests/test_support_matrix.py (EXPECTED_CAPABILITY_STATUSES
   exact dict) + backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py
   (capability_count 28 -> 29 + exact per-status lists) + docs/support-matrix-local-expert.md +
   README front door (guarded by tests/test_readme_frontdoor_truth.py).
c) TEST PLACEMENT RULE: put connector tests in root tests/ (auto-collected by root-tests;
   senate precedent = 14 tests in tests/test_api.py) OR, if adding a backend/tests file, extend
   the pattern tuple in BOTH .github/workflows/playwright.yml (backend-layer3-api-shard) AND
   backend/tests/test_ci_coverage_completeness.py BACKEND_SHARD_PATTERNS — fails closed
   otherwise (RC3-trap shape).
d) CONFIG INSERTION POINT: append new *_api_base_url fields AFTER config.py:214, or update
   support_matrix.yaml's config-line evidence refs in the same commit
   (test_support_matrix.py:126-142 asserts exact line numbers). Add commented sibling to
   backend/.env.example (convention, not CI-forced).
e) CLIENT SCAFFOLDING IS COPY-PASTE, NOT IMPORT: _RateLimiter is module-private to
   connectors_senate_lda.py; no shared connector-client module exists. Either budget the
   copy-paste honestly or make task-1 a small shared-helper extraction (touches senate
   monkeypatchers at tests/test_api.py:3076 + support_matrix_runtime_contract_audit.py:338).
   Rev-1's 250-400 LOC figures cover the service module only; TOTAL landing surface = the
   senate 29-file static footprint class (original landing PR unrecoverable — 2026-06-06
   history rewrite; static footprint is the true template).
f) DO NOT rename/move existing senate/sciencebase tests: scripts/
   rc2_public_connectors_acceptance.py pins exact tests/test_api.py node-ids.
g) ADDED-LINE LEAK SCAN (standing rail, was missing from rev-1 constraints): full PR diff, with
   explicit attention to FIXTURE BODIES (no machine-local paths, real request headers/UA,
   operator identity). Fixture VALUES are a non-issue (public-domain data; retention posture).
h) COVERAGE FLOOR: NON-ISSUE, verified — backend-coverage --cov scope is app.api.layer3 + one
   auth module only; connector code is outside it. (Rev-1 was silent; recorded to prevent
   future re-litigating.)

## R2.3 Live-pilot corrections (D27/D28 mechanics)
- FIXTURE MODEL must be stated per mandate (rev-1 contradiction fixed): DEFAULT = hand-authored
  fixtures from doc examples (zero egress, no grant; accept shape-mismatch risk; reserve 2-3
  pilot requests for first-contact shape diagnosis). ALTERNATIVE = D27 grant names TOTAL budget
  = fixture-capture + pilot (WB would need ~20, not 15). Pick one in the D28 arming record; no
  mid-lane second grants.
- BUDGETS re-baselined: retries COUNT as real requests (retry loop increments requests_total
  per attempt, default 4 attempts/request); the golden-path convention runs FOUR scenarios +
  up to 2 resume passes. CFTC <=8 has zero retry headroom: raise to ~12 with an explicit 3-4
  retry reserve OR pre-scope to first_import + recurring_sync only (state which in the
  mandate). WB <=15 plausible-but-tight: pin per_page high, state a retry reserve. USGS budget
  MUST be fixed before its D28 arming record.
- STOP POSTURE (mechanical, not just procedural): (1) retries count against the D28 ledger;
  (2) pilot runner reconciles sum(requests_total) across runs AFTER EACH scenario and halts
  remaining scenarios at budget-minus-reserve or on a systemic 429/403 pattern; (3) a halted
  pilot is a CLEAN D28 outcome (report exact unresolved scenario set), not a failure; (4)
  rollback is trivial by construction (metadata-only, zero new tables: cancel run + ledger
  entry) — state it. No in-code request-count ceiling exists (only a bytes budget); the ledger
  reconciliation is the enforcement.
- EXECUTION ENVIRONMENT: build + live pilots run from a short-path NON-OneDrive worktree
  (worktrees/ convention or C:\p6* lane) and/or STORAGE_DIR pointed off-OneDrive for live runs
  (default STORAGE_DIR writes 12 report files/run into the OneDrive-synced tree).
- FIXTURE CONVENTION: in-file fake clients (senate mold, tests/test_api.py:7133) as default;
  on-disk fixtures only if genuinely needed, capped <=50 rows / <=25KB truncated-real-shape,
  under backend/tests/fixtures/<connector>/.

## R2.4 New owner-decision items
- OD-6 (from dossier §3 Registry gap, dropped in rev-1): four future analysis-METHOD classes
  suggested by the candidate set — panel ranking/peer comparison, trade-share/market-
  concentration decomposition, revision-aware vintage analysis, commodity balance arithmetic —
  parked as a separate analytics-method lane candidate, distinct from connector units.
- OD-7: land frozen copies of the dossier + this adjudication as a tracked campaign record
  (docs/campaign-records/, publication-normalized) before/with the first build PR — the whole
  decision chain is currently untracked single-copy (only state/agent-inbox/README.md is
  tracked; OneDrive replica is the sole backup; p6store replica does NOT cover these newer
  files until its next manual re-mirror).

---

# REV 3 — FINAL ADVERSARIAL GATE (2026-07-07; independent adversarial reviewer review M-SOURCE-CANDIDATES-
# ADVERSARIAL-REVIEW, report at state/agent-inbox/source-candidates-adversarial-review.md;
# orchestrator spot-verified. A-claims 7 CONFIRMED / 1 PARTIAL / 0 REFUTED. Chain is now
# triple-reviewed: investigation (investigation lane) -> second-pass audit second pass -> adversarial (adversarial review lane).)

## R3.1 Verification-gap CLOSED (C4)
- FRED: page reached by reviewer tooling — web service requests REQUIRE an API key. Exclusion
  final, now [DOC]-anchored, no longer knowledge-corroborated-only.
- BLS PRECISION UPGRADE (material): the anonymous tier is API **v1**; **v2 requires
  registration**. Anonymous caps 25/day, 25 series/query, 10 years/query confirmed from the
  page. Any BLS anonymous pilot MUST target the v1 endpoint family — "v2 without a key" is not
  a thing. Rev-2's manual-owner-ToS-check route stands for the remaining ToS/attribution nuance.

## R3.2 Corrections to REV-2 (accepted; spot-verified by orchestrator)
- A7a: the 4-scenario live validator is SCIENCEBASE-SPECIFIC (project6.ps1:37 hardwires
  tools/run_sciencebase_live_pilot_validation.py). A WB/CFTC/USGS pilot needs its OWN validator
  scope decision (new P1 below); the 4-scenario request-budget arithmetic still applies as the
  proof-convention baseline.
- A7b: "only a bytes budget exists in-code" was too broad — max_items / max_files /
  per_host_fetch_limit exist in the request schema (verified). Still NO request-COUNT ceiling
  tied to a D27 grant, so REV-2's per-scenario ledger-reconciliation stop mechanism stands.
- Numerics: senate static footprint = 28 files (not 29; orchestrator re-derived 28); backend
  shard pattern tuple = ~25 entries (counting-window dependent; the NUMBER is irrelevant — the
  fail-closed workflow<->BACKEND_SHARD_PATTERNS mirror rule is the constraint).
- World Bank attribution sharpened: license is CC BY 4.0, attribution format "The World Bank:
  Dataset name: Data source" (orchestrator re-verified) — goes verbatim into the connector's
  provenance surface.

## R3.3 New obligations from the gap hunt (B-pass; add to the build checklist)
- BOUNDARY NOTE (test-guarded): support_matrix.yaml boundary_note currently bounds public
  connector support to "ScienceBase public/MCS and Senate LDA anonymous metadata only"
  (orchestrator re-verified the exact sentence) — a third connector MUST update this wording;
  test_support_matrix.py:68-91 guards boundary tokens.
- DOCS/FRONT-DOOR SET: README active-tracks + endpoint list, docs/first-boot-capabilities.md,
  docs/public-connectors-journey.md, docs/support-matrix-local-expert.md all currently name
  exactly two public connectors; update the ones whose truth-claims change. REPO_INDEX.md if
  maintained as current map.
- PER-ROUTE OPENAPI/AUTH TESTS: no frozen whole-app route count exists (good), but the new
  endpoint needs its own route/schema/auth tests and must pass the POST-enumeration cross-check
  vs main.app.openapi().
- DISPATCH-PATTERN CHOICE (new P1): generic ScienceBase-style keyed-config service vs
  Senate-style self-contained service module — decide BEFORE implementation.
- CONDITIONAL: rc3_sec_xbrl_offline_acceptance.py includes public-connector node-ids — a new
  supported connector may need analogous acceptance coverage if selected-profile support is
  widened; layer3 progress manifests only if planning/proof claims change.
- NON-ISSUES (verified, recorded to stop re-litigation): release_readiness.yaml, nginx/compose
  proxy config (local anonymous connector adds no proxy exposure); connector_key is String(100)
  with no enum/check constraint (zero-migration claim HOLDS for the senate mold).

## R3.4 Classification updates (C-pass)
- OECD STRENGTHENED: official page confirms APIs are free, SDMX-based, rate-limited, subject to
  terms — moves from "keyless-apparent" to "confirmed-free with terms/rate review remaining".
- IMF DataMapper: v2 JSON time-series API documented; plausible-keyless stands; SDMX portal
  remains account-gated for swagger.
- Census: an FTP/bulk open-data surface exists — a possible NON-API bulk path (like EIA bulk);
  does NOT re-qualify the Data API. Both escape hatches are file-connector variants, parked.
- FAO: fao.org returns zero content to reviewer tooling too — stays DEFER; BTS unresolved
  (DOT developer page confirms resources, not auth/rate) — stays DEFER.
- WTO/Comtrade: no keyless path found within budget — exclusions final.

## R3.5 Sufficiency verdict (D) — the standing conclusion for the next step
Adjudication + REV-2 + REV-3 = SUFFICIENT EVIDENCE BASE; NOT an executable mandate. The first
build mandate must explicitly decide: (1) source choice [OD-1; reviewer consensus: World Bank
cleanest — auth settled, main trap is attribution; CFTC needs PRE/reasonable-use bounds; USGS
needs release/DOI pinning + API-vs-file mechanics]; (2) dispatch pattern [R3.3]; (3) exact
acceptance criteria (PR-1..PR-5 test names, capability id, probe, fixture convention,
no-live-network unit-test boundary); (4) STOP conditions (rate/usage, auth-appearance,
ToS/attribution failure, schema drift, empty-result fail-closed); (5) validation chain
(ScienceBase-only validator vs new source-specific pilot validator/action). Rollback = P2
(code/config/docs removal; no DB rollback — escalates to P1 only if a new table/durable
artifact appears, which the Tier-1 fence already forbids.)


---

## Adversarial review

# M-SOURCE-CANDIDATES-ADVERSARIAL-REVIEW

## Scope And Authority

- Repo authority: `project6-origin/main` fetched at `3c669256c7246c1b8d16312226235e9a1c2495b4`.
- Chain docs read: `state/agent-inbox/source-candidates-investigation-source.md`, `state/agent-inbox/source-candidates-dossier.md`, `state/agent-inbox/source-candidates-adjudication.md`, and the binding task packet.
- Work mode: read-only repo audit. No branch, worktree, commit, PR, API call, dataset download, signup, or runtime validator execution was performed.
- Web ledger: 16 unique official documentation/terms pages consulted, within the <=20 page budget. All web access was HTTPS GET to docs/ToS/developer pages only.

## A. REV-2 Mechanical Claims

### A1 - POST route auth and pre-body registration

Verdict: CONFIRMED.

Fresh evidence:
- `backend/app/api/router.py:446-455` registers `POST /connectors/senate-lda/runs` and calls `_route_level_operator_identity(request, access="write")`.
- `backend/main.py:87-95` defines `_build_static_pre_body_routes`; `backend/main.py:286-292` includes `/api/v1/connectors/senate-lda/runs` with `write`.
- `backend/tests/test_pre_body_operator_authorization.py:37-49` checks pre-body map coverage for registered protected POST routes.
- `backend/tests/test_layer3_post_route_operator_authorization_coverage.py:65-83` fails on any POST route gated by neither handler auth nor pre-body registry.
- `backend/tests/_route_enum.py:22-72` is the version-robust route enumerator used by those tests.

### A2 - Support-matrix assert set

Verdict: CONFIRMED, with terminology corrected: "8 surfaces" means files/surfaces to update, not capability count.

Fresh evidence:
- `config/support_matrix.yaml:27-39` carries public connector capability entries with PR-1..PR-5 evidence markers.
- `backend/tests/test_support_matrix.py:23-52` pins exact `EXPECTED_CAPABILITY_STATUSES`.
- `backend/tests/test_support_matrix.py:68-94` checks profile, overlays, boundary note tokens, exact id/status map, and evidence shape.
- `backend/tests/test_support_matrix.py:116-124` requires PR-1..PR-5 markers for connector capabilities.
- `scripts/support_matrix_constants.py:21-88` mirrors expected status ids and PR markers.
- `scripts/support_matrix_check.py:178-195` rejects missing PR markers and RC3 boundary drift.
- `scripts/support_matrix_runtime_contract_audit.py:657-708` maps every capability id to a runtime probe and fails undeclared/missing-probe cases.
- `backend/tests/test_layer3_support_matrix_runtime_contract_exhaustive.py:41-86` requires `capability_count == 28` and exact per-status lists.
- `docs/support-matrix-local-expert.md:17-44`, `README.md:1-3`, and `tests/test_readme_frontdoor_truth.py:51-63` are front-door documentation surfaces guarded by tests.

### A3 - Test placement and CI collection

Verdict: CONFIRMED, with exact backend pattern count corrected to 25.

Fresh evidence:
- `.github/workflows/playwright.yml:127-153` defines the backend shard filename tuple; counting the live tuple gives 25 patterns, not 26.
- `.github/workflows/playwright.yml:160-193` collects and shards backend node ids only from those matched files.
- `.github/workflows/playwright.yml:249-289` separately collects root `./tests/test_*.py`.
- `backend/tests/test_ci_coverage_completeness.py:16-42` mirrors the backend pattern tuple.
- `backend/tests/test_ci_coverage_completeness.py:188-193` fails if the workflow tuple diverges from `BACKEND_SHARD_PATTERNS`.

### A4 - backend-coverage scope

Verdict: CONFIRMED.

Fresh evidence:
- `.github/workflows/playwright.yml:542-569` defines `backend-coverage` as `tests/test_layer3_*.py` with `--cov=app.api.layer3` and `--cov=app.services.layer3_sec_xbrl_in_app_auth_policy`.
- Connector service modules are outside that coverage target; a connector landing still needs targeted tests, but the CI coverage floor itself is not a connector-code coverage blocker.

### A5 - support_matrix.yaml line-number fragility

Verdict: CONFIRMED.

Fresh evidence:
- `backend/app/core/config.py:210-214` currently holds ScienceBase and Senate LDA setting aliases.
- `config/support_matrix.yaml:27-34` embeds `backend/app/core/config.py:210` and `backend/app/core/config.py:213-214` in evidence strings.
- `backend/tests/test_support_matrix.py:127-143` recomputes current alias line numbers and asserts those exact strings appear in the matrix.
- Therefore new config fields inserted before line 214 require either appending instead or updating support-matrix evidence.

### A6 - Senate helper locality and static footprint

Verdict: CONFIRMED, with exact current footprint count corrected to 28 non-archive tracked files.

Fresh evidence:
- `backend/app/services/connectors_senate_lda.py:180-194` defines the only tracked non-archive `class _RateLimiter` found by `git grep`.
- `scripts/rc2_public_connectors_acceptance.py:51-159` pins exact `tests/test_api.py::...` node ids across PR-1..PR-5 command groups.
- A live `git grep -l -e senate_lda -e senate-lda project6-origin/main -- ':!archive/**'` found 28 non-archive tracked files, not 29. The count correction does not change the substance of the claim.

### A7 - Pilot mechanics

Verdict: PARTIALLY CONFIRMED.

Confirmed:
- `backend/app/services/connectors_senate_lda.py:227-229` increments `requests_total` once per HTTP attempt.
- `backend/app/services/connectors_senate_lda.py:128-133`, `:653`, and `:1017` establish default `retry_max_attempts_per_request=4` unless overridden.
- `tools/run_sciencebase_live_pilot_validation.py:66-92` has up to two resume attempts while stabilizing nonterminal targets.
- `tools/run_sciencebase_live_pilot_validation.py:282-293` runs four ScienceBase scenarios: `first_import`, `recurring_sync`, `budget_cap`, and `cancel_resume`.
- `backend/app/core/config.py:13-16` and `:113` default `STORAGE_DIR` to `backend/app/storage`, which is in-tree for this OneDrive-rooted checkout.

Corrections:
- The four-scenario validator is ScienceBase-specific, not a generic WB/CFTC connector mandate harness. `project6.ps1:37` and `:439-443` wire `validate-sciencebase-live` and `validate-live` to that ScienceBase validator.
- "Only bytes budget exists" is too broad if read literally. `backend/app/schemas/api.py:176-201` also exposes `max_items`, `max_files`, and `per_host_fetch_limit`; `backend/app/services/connectors_sciencebase.py:527-528` and `:2048-2055` show byte budget enforcement. I found no global request-count budget ceiling, but count/fetch limits do exist.

### A8 - Fixture convention

Verdict: CONFIRMED.

Fresh evidence:
- `tests/test_api.py:7133-7185` defines in-file Senate fake clients.
- `tests/test_api.py:7405-7420` uses those fakes for Senate happy-path/detail hydration tests.
- `git grep` for `25KB`, `25 KB`, `fixture_size`, `max_fixture`, `fixture size`, `25600`, and `kilobyte` under non-archive tracked test/doc/tool paths found no first-party repo-wide fixture-size limit. A future size cap would be a new convention, not an existing enforced rule.

## B. Gap Hunt Beyond REV-2

### B1 - OpenAPI / route-shape assertions

Verdict: OBLIGATION, but not an all-route-count blocker.

Evidence:
- `backend/tests/test_layer3_api.py:842-875` and many later tests inspect specific Layer 3 OpenAPI paths/schemas.
- `backend/tests/test_layer3_post_route_operator_authorization_coverage.py:86-103` cross-checks POST enumeration against `main.app.openapi()`.
- I found no frozen whole-app route count for legacy connector routes. A new connector must add route/auth/schema tests for its own endpoint and pass the existing POST enumeration cross-check.

### B2 - e2e / project6.ps1 / browser surfaces

Verdict: OBLIGATION if the mandate claims live validation or operator journey parity; otherwise mostly NON-ISSUE.

Evidence:
- `project6.ps1:1-3` lists `validate-sciencebase-live` and `validate-live`; `project6.ps1:37` points both at `tools/run_sciencebase_live_pilot_validation.py`.
- `project6.ps1:439-443` wires both actions to the ScienceBase live validator.
- `backend/app/review_ui/static/layer3.js` contains many generic `connector_dispatch_enabled=false` rendered surfaces, but these are Layer 3 provider/local receipt controls, not public-source connector enumerations.
- I found no e2e/browser test that enumerates World Bank/CFTC/source connector names today.

### B3 - Docs/front-door surfaces

Verdict: OBLIGATION.

Evidence:
- `README.md:24-33` states the active tracks and names ScienceBase plus Senate LDA.
- `README.md:48-60` enumerates connector endpoints.
- `docs/first-boot-capabilities.md:20-27` lists first-boot supported capabilities and currently names ScienceBase and Senate LDA only.
- `docs/public-connectors-journey.md:1-38` describes the current public connector journey as ScienceBase plus Senate LDA.
- `docs/support-matrix-local-expert.md:17-44` names the canonical selected-profile journey and capability table.

### B4 - release_readiness / nginx / compose / proxy config

Verdict: NON-ISSUE for a normal anonymous local connector landing.

Evidence:
- `config/release_readiness.yaml:1-45` is profile-neutral and does not enumerate connector source keys.
- Repo grep over `config/release_readiness.yaml`, compose/nginx/Docker surfaces, workflow files, `project6.ps1`, and `README.md` found connector enumeration in docs and runner surfaces, not in proxy/compose allowlists.
- This verdict changes if the connector adds nonlocal/proxy exposure, provider delivery, secrets, or a new production deployment claim.

### B5 - Progress manifests and board

Verdict: CONDITIONAL OBLIGATION.

Evidence:
- `AGENTS.md:63` requires `next_milestone_plans/layer3_progress_manifest.json`, `next_milestone_plans/layer3_workbench_proof_manifest.json`, and `next_milestone_plans/layer3_progress_board.md` to stay aligned when a Layer 3 planning or implementation tranche changes their claims.
- `tools/l3-progress-check.py:12-16` treats those files as maintained proof/progress inputs.
- A code-only connector patch need not touch them unless it makes/changes planning/proof claims.

### B6 - Alembic/model schema and connector key admission

Verdict: NON-ISSUE for schema if existing connector tables are reused; OBLIGATION for service dispatch/config admission.

Evidence:
- `backend/alembic/versions/0002_connector_subsystem.py:16-71` uses `sa.String(length=100)` for `connector_key`; no enum/check-constrained connector-key list appears there.
- `backend/app/models/models.py:413-420` maps `ConnectorRun.connector_key` as `String(100)`.
- `backend/app/models/models.py:486-493` maps `ConnectorRunSubmission.connector_key` as `String(100)` with only a uniqueness constraint with idempotency key.
- `backend/app/services/connectors_sciencebase.py:454-502` normalizes generic ScienceBase keyed config; `backend/app/services/connectors_senate_lda.py:580-645` hard-codes Senate-specific key handling. A mandate must choose which dispatch pattern a new connector follows.

### B7 - Support-matrix boundary note

Verdict: OBLIGATION.

Evidence:
- `config/support_matrix.yaml:8` explicitly says public connector support is bounded to ScienceBase public/MCS and Senate LDA anonymous metadata only.
- `backend/tests/test_support_matrix.py:68-91` guards the profile, overlay, boundary tokens, and exact capability id/status mapping.
- `backend/tests/test_support_matrix.py:231-254` also checks deferral behavior for the current connector capability ids.
- A third supported anonymous connector needs boundary-note language plus exact capability/probe/test updates.

### B8 - Other footprint deltas

Verdict: OBLIGATION/PARTIAL depending on claim.

Additional live surfaces found by `git grep -l -e senate_lda -e senate-lda project6-origin/main -- ':!archive/**'`:
- `REPO_INDEX.md:23-25`, `:103-131`, and `:198` still document ScienceBase/Senate surfaces and the ScienceBase live validator. If maintained as a current repo map, it should be updated.
- `SCIENCEBASE_PILOT_RUNBOOK.md:1-12` and `:51-60` are ScienceBase-only. Non-issue unless the new mandate claims live-pilot parity.
- `scripts/rc3_sec_xbrl_offline_acceptance.py:118-141` includes public connector node ids in the RC3 acceptance runner. A new supported connector may need analogous acceptance coverage if selected-profile support is widened.
- `docs/campaign-records/2026-07-07-forward-frontier-dossier.md:333-395` contains strategic connector framework notes. Treat as planning/historical unless the mandate cites it as current authority.

## C. Classification Stress

### C1 - Excluded/keyed candidates

Verdict: mostly still excluded for first API connector; one keyless non-API escape hatch exists.

- EIA: still keyed for API use, but the official page says the bulk download facility does not require an API key. This can requalify EIA only if the mandate intentionally chooses a bulk-download path instead of an API connector. [WEB https://www.eia.gov/opendata/register.php L0-L4]
- FRED: the key page was reachable; it says web service requests require an API key and key viewing requires account login. No official no-key API path found. [WEB https://fred.stlouisfed.org/docs/api/api_key.html L70-L77]
- Census: current API page says all Census Data API queries require a key; separate Census open-data page exposes an FTP Server for full datasets. This creates a possible bulk/non-API path, not a no-key API connector path. [WEB https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html L200-L208; https://www.census.gov/about/policies/open-gov/open-data.html L182-L211]
- WTO: developer portal says to sign up for an API key before consuming APIs. No no-key API path found. [WEB https://apiportal.wto.org/ L0-L3]
- UN Comtrade: developer portal redirected to sign-in/welcome. No no-signup public-preview API path was confirmed within budget. [WEB https://comtradedeveloper.un.org/ L0-L6]

### C2 - Include-now candidates

Verdict: INCLUDE-NOW remains plausible, with source-specific traps.

- World Bank: V2 Indicators API does not need API keys or authentication, but data use requires CC BY 4.0 attribution/compliance. This is the lowest-friction first mandate if attribution is explicitly accepted. [WEB https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation L470-L478; https://data.worldbank.org/summary-terms-of-use L50-L56]
- CFTC COT/PRE: CFTC says PRE API access generally works without a token if not overused, and PRE exports CSV/RDF/RSS/TSV/XML. The mandate must pin exact PRE/API/query/format and reasonable-use stop conditions. [WEB https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm L195-L215]
- USGS MCS: current 2025 data release page says the database contains CSV table files and marks rights as CC0 1.0 Universal. The mandate must pin the release/DOI and decide API-vs-page-data retrieval mechanics. [WEB https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025 L258-L274]

### C3 - Conditional/defer candidates

Verdict: several conditions are now partially resolvable.

- OECD: condition resolved enough to move from vague defer to candidate-with-terms/rate-limit review. Official page says the APIs are free, SDMX-based, subject to terms, and rate-limited; XML/JSON/CSV are documented. [WEB https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html L3701-L3704, L3798-L3812]
- IMF: DataMapper API is documented as a v2 JSON time-series API; IMF Data API page separately says SDMX APIs are available, but the swagger explorer requires beta portal sign-in. DataMapper is plausible keyless; broader SDMX needs auth/portal clarification. [WEB https://www.imf.org/external/datamapper/api/help L0-L22; https://data.imf.org/en/Resource-Pages/IMF-API L18-L38]
- FAO: official FAOSTAT page returned zero lines through this fetch tool, so I did not resolve the API docs/auth condition within budget. [WEB https://www.fao.org/faostat/en/]
- BTS/DOT: DOT developer page confirms developer resources and over 700 datasets/tools, but the page does not settle BTS API auth/rate terms. Keep deferred. [WEB https://www.transportation.gov/developer L145-L155]

### C4 - FRED and BLS bot-blocked pages

Verdict: CLOSED. Both pages were reachable with current tooling.

- FRED: page explicitly requires an API key for web service requests. [WEB https://fred.stlouisfed.org/docs/api/api_key.html L70-L77]
- BLS: page states API v2 requires registration; unregistered v1 access exists with lower limits of 25 daily queries, 25 series/query, and 10 years/query. This makes BLS not a clean first anonymous connector unless the mandate accepts the low unregistered tier and no registration. [WEB https://www.bls.gov/developers/api_faqs.htm L270-L327, L345-L354]

## D. Sufficiency Verdict

Plain answer: adjudication plus REV-2 is sufficient as the basis for authoring a first build mandate only if the mandate author makes the remaining source-specific decisions explicitly. It is not sufficient as the sole build mandate by itself.

Talmudic debate:
- Position 1: Sufficient. REV-2 identifies the repo fences, support-matrix surfaces, auth gates, test collection behavior, and source classification well enough to draft a narrow connector mandate.
- Position 2: Insufficient. It still does not pick WB vs CFTC vs USGS, route/schema shape, dispatch pattern, exact acceptance tests, live-pilot requirements, output artifact policy, and rollback/STOP conditions.
- Consensus: use REV-2 as the evidence base, not as the executable mandate. World Bank is the cleanest first mandate because auth is settled and the main trap is attribution. CFTC is viable but needs stricter PRE/query/reasonable-use boundaries. USGS is viable if the build is data-release/CSV oriented rather than API-shaped.

Residual ambiguities:
- P1 - Source choice: WB/CFTC/USGS must be selected before code; each has different route schema, fixture, ToS, and acceptance obligations.
- P1 - Dispatch pattern: decide generic ScienceBase-style keyed service versus Senate-style separate service before implementation.
- P1 - Acceptance criteria: define PR-1..PR-5 test names, support-matrix capability id, runtime probe, exact fake-client/fixture convention, and no-live-network unit-test boundary.
- P1 - STOP conditions: define rate/usage, auth/key appearance, ToS/attribution failure, schema drift, non-CSV/non-JSON surprise, and runtime empty-result fail-closed behavior.
- P1 - Validation chain: decide whether project6 live validator remains ScienceBase-only or whether a new source-specific live-pilot validator/action is in scope.
- P2 - Docs/progress surfaces: README, support-matrix doc, first-boot capabilities, public-connectors journey, REPO_INDEX, and progress manifests need only the surfaces whose authority claims actually change.
- P2 - Rollback/containment: no DB rollback needed if existing tables are reused; rollback should be code/config/docs removal plus route/auth/test removal. If a new table or durable artifact format appears, migration/rollback becomes P1.

## E. Summary

- A-claims: 7 confirmed, 1 partially confirmed, 0 refuted.
- B-surfaces: 5 obligations, 2 conditional/partial obligations, 1 schema non-issue with code-dispatch obligation.
- C-results: FRED/BLS bot-block gap closed; OECD and IMF partially strengthened; EIA and Census have keyless bulk/FTP escape hatches but not clean no-key API connector paths; WTO/Comtrade remain excluded for no-key/no-signup first connector.
- New P1 gaps: source choice, dispatch pattern, acceptance criteria, STOP conditions, validation chain, source-specific ToS/attribution/rate policy.
- New P2 gaps: doc/front-door/progress-map alignment, fixture-size convention if external fixtures are introduced, optional live-pilot generalization.

## Web Ledger

1. `https://fred.stlouisfed.org/docs/api/api_key.html` - FRED key requirement; C4 closed.
2. `https://www.bls.gov/developers/api_faqs.htm` - BLS v1/v2 registration and limits; C4 closed.
3. `https://www.eia.gov/opendata/register.php` - EIA API key and bulk exception.
4. `https://www.census.gov/library/video/2026/adrm/requesting-a-census-data-api-key.html` - current Census API key requirement.
5. `https://www.census.gov/about/policies/open-gov/open-data.html` - Census open-data/FTP surface.
6. `https://apiportal.wto.org/` - WTO API key signup requirement.
7. `https://comtradedeveloper.un.org/` - UN Comtrade developer portal sign-in/welcome.
8. `https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation` - World Bank V2 no-auth API.
9. `https://data.worldbank.org/summary-terms-of-use` - World Bank CC BY 4.0 terms.
10. `https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm` - CFTC COT/PRE no-token and formats.
11. `https://www.usgs.gov/data/us-geological-survey-mineral-commodity-summaries-2025-data-release-ver-20-april-2025` - USGS MCS CSV/CC0 data release.
12. `https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html` - OECD SDMX API, terms/rate, formats.
13. `https://www.imf.org/external/datamapper/api/help` - IMF DataMapper API.
14. `https://data.imf.org/en/Resource-Pages/IMF-API` - IMF SDMX API and beta portal sign-in for swagger.
15. `https://www.fao.org/faostat/en/` - FAOSTAT page returned zero lines in this fetch tool.
16. `https://www.transportation.gov/developer` - DOT developer resources; BTS auth/rate unresolved.
