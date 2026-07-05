# 04 — Evidence Registry

Every committed load-bearing anchor. A claim elsewhere in this set that cites one of these is
re-derivable from committed source, GitHub PR state, or read-only hash/count artifacts.
Operator coordination reports are supplementary evidence, not committed anchors.

## Merged PR / SHA table (all squash-merged to project6-origin/main)

| PR | SHA | Title / tranche |
|---|---|---|
| #2409 | 54d616b3 | A8 implementation spec (corrected) + ledger fold |
| #2410 | abd8c3f8 | MASTER_CONTEXT published |
| #2411 | 0290ff5b | Proof provenance policy docs |
| #2412 | 67bab0b0 | A7 full-chain CI durability |
| #2413 | 265c1a12 | A8 owner decision brief (transient main-run CI failure, later recovered) |
| #2414 | c64ed422 | RC3 acceptance completeness + drift guard (58/58) |
| #2415 | 6a28d0a4 | A8 runtime guards (Tier-2; two-round independent review) |
| #2416 | 5a3cc213 | Operator utilization index |
| #2417 | 6b735721 | Ops readiness closeout + ledgers |
| #2418 | f2eb7f7f | Golden-path ScienceBase fixture fix (2023 dataset; `all` green x3) |
| #2419 | 7fa72e74 | Record truth v1 (synthetic proof + arming recipe) |
| #2420 | a1637393 | Record reconciliation v2 (supersession notes, anchor hygiene) |
| #2421 | f566ddb1 | O6 hardening docs + hygiene edge tests |
| #2422 | be6d9b1b | Record truth v3 (real-data proof + O6 tranche + I10 note) |
| #2423 | e661e05a | Durable-root provisioning + migration record |
| #2424 | eefc2acc | Program-context docs landed |
| #2425 | 9d44e79b | Controlled reveal pagination gap coverage |
| #2426 | f0f32413 | Corpus run plan |
| #2427 | 99efa28d | Corpus admission gate hardening |
| #2428 | 154b8a38 | Historical SEC taxonomy pins |
| #2429 | 4ad672f3 | Bare SEC taxonomy cache layout |
| #2430 | 24502721 | 2026 SEC taxonomy pins |
| #2431 | 92b069b9 | Explicit corpus form selection |
| #2432 | 2d6fdbde | SEC inline transform plugin |

## Real-data proof artifacts (operator-local; verified independently by two blind auditors)

| Artifact | Anchor | Meaning |
|---|---|---|
| Reveal proof report | sha256 `790fbb8eaa7de4be447f6c401089cb3b6435ff86614f4f0f57e656fc287a39d8` | CK1-3 outcome record (report file in operator sandbox reports dir) |
| Revealed facts | 523 total / 497 non-empty | CK3 controlled-submit response (one real filing, issuer/form redacted) |
| Retained store records | 523 (513 non-empty at CK2) | Internal value store contents |
| Internal value store file | sha256 `3bc81d84fc75bde17d074eee610130efa2659e2b2d281e756402007243eef5a0` | The durable store artifact |
| Value-store hash | `eb702c84d42e16200f9f07bbb5888b277b987bca028a51304e922ef2377ce285` | Receipt↔store binding hash |
| Persisted sidecar receipt | hash `7fe4c3da194396dbe11261eb6ec42942b4c23ce534c37e982f2c872cc4a50546` | CK2 fresh derivation WITH store armed |
| Prior flag-off receipt | hash `d5c3585e91397f778f7d0f0297ac05d168dd7410fdaea1e2db7d18cbd3d5036d` | June A7-A receipt (store correctly not created) — distinct evidence state |
| Origin namespace hash | `6483a8de2d45e2f79150273cbb0fcdfcf21bf7769132f19ecf01e71b6de9b354` | Sandbox root identity (historical, preserved in copied artifacts) |
| Fail-closed probe | sha256 `edfdf1ca3d68baacdef80c01cb6cbb0e60496dd59ea7b9102dfe9e90ca097819` | Missing-confirmation rejection string |
| Retention policy | `sec_xbrl_public_financial_value_retention_v1` | Emitted in store + receipts |
| Flags posture | `value_reveal_performed=true`, `production_readiness_claimed=false` | The proof's honest self-description |

## Durable-root migration (07-04)

| Artifact | Anchor |
|---|---|
| Canonical root | `C:/p6store` (public-by-design path; hygiene class `accepted`, NO override) |
| New namespace hash | `4502e1c70863a4bd0067e5f0de4325758d3542e05df223d702747c1886ee6ca9` |
| Migration manifest | sha256 `845974f765dc8e7985105053b77e97d6983d94a02f0f015454e9f023e77384fb` at `C:/p6store/MIGRATION_MANIFEST.json` (+ sandbox copy) |
| Copy stats | 43 files / 16.62MB, zero failures, source retained |
| Provisioning | `project6.ps1 -Action provision-a8-root` (strict) + `setup` warning-only hook; verified live from fresh worktree |

## Corpus-go run proof artifacts (07-05)

| Artifact | Anchor | Meaning |
|---|---|---|
| Record lane | PR `#2433`, section `M-CORPUS-RECORD-TRUTH` | Hash/count/disposition-only record lane for the owner-authorized corpus-go run |
| Source frontier | `2d6fdbde0f82a836663f7e06923d1dd05cc48f3d` | Current main after PR #2432 SEC inline transform plugin |
| Aggregate report | sha256 `113ce73679547f5d202cb273ebca9d2373f90fab9ae688e9159cc7894c3cee10` at durable-root relative `corpus_run/CORPUS_GO_RUN_REPORT.json` | Operator aggregate report; path is relative to the durable root, not an absolute local path |
| Supported breadth | 39 supported filings / 21 supported issuers | Exceeds run minimums of 30 filings / 15 issuers |
| Run-level gates | `every-ticker-dispositioned=PASS`; `zero-unnamed-failures=PASS`; `min-filings=PASS`; `min-issuers=PASS` | Four owner-handoff completion gates for the completed run |
| Supported input group | `NVDA`, `AMD`, `MSFT`, `GOOG`, `AMZN`, `META`, `AAPL`, `DIS`, `HOOD`, `NFLX`, `AMCX`, `UUUU`, `LEU`, `GEV`, `NUE`, `CLF`, `STLD`, `TRLV`, `GTBIF`, `CURLF`, `CRLBF` | Final disposition `supported`; includes all major domestic 10-K+10-Q pairs plus supported foreign/OTC inline filings |
| IFRS follow-up group | `SONY`, `CCJ`, `DNN`, `NXE`, `MT`, `TSM` | Acquired and retained; admitted reason code `taxonomy_year_unprovisioned`; operator symptom `arelle_model_errors_present`; follow-up `ifrs-taxonomy-pins` |
| 6-K form slots | `6-K` | Admitted reason code `no_inline_facts_pre_inline_era`; no iXBRL by design |
| Unknown/alias group | `KAP`, `PDN`, `YCA`, `TSMC-as-written` | Operator status `company_matrix_unknown`; admitted reason codes `official_ticker_resolution_missing` for `KAP`/`PDN`/`YCA` and `ticker_alias_resolution_required` for `TSMC-as-written` |
| Enabling fix chain | PRs `#2427` through `#2432` | Hardening, SEC taxonomy pins/cache layout/2026 pins, explicit forms, and SEC inline transforms plugin; fixed absent `ixt-sec` registry and re-proved `model_error_count=0` on the previously blocked filing |

## Key code anchors (verify against live main; line numbers drift)

| Surface | Location |
|---|---|
| Hygiene classes + classification | `backend/app/services/layer3_sec_xbrl_sidecar.py` (~68-79 enum; ~1427-1533 classify/helpers) |
| Retention policy constant | same file, VALUE_RETENTION_POLICY_ID (~48) |
| Store write/read (create-only, hash/count verify) | same file (read helper ~396-454; write helper ~1170-1206; metadata/path helpers ~1209-1236, ~1388-1408) |
| Boot containment validator | `backend/app/core/config.py` `_validate_raw_bearing_sec_storage_containment` (model validation ~303-414; function starts ~346) |
| A8 flag defaults | `backend/app/core/config.py` (~152-178) |
| Admission containment (I10) | `backend/app/services/layer3_sec_xbrl_production_admission.py:141-156` |
| Corpus dual-flag gate | `backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py` (~1554-1558) |
| Reveal authority / controlled submit | `layer3_sec_xbrl_value_reveal_authority.py`, `layer3_sec_xbrl_controlled_value_reveal_submit.py` |
| No-deletion guard test | `backend/tests/test_sec_xbrl_sidecar.py` (AST+string; threat model in doc note) |
| Merge-gate policy | `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md` (Tier 1 / Tier 2 wording) |
| Admission runbook (7 criteria) | `docs/layer3-admission-runbook.md` |

## Counts worth remembering

- 24 PRs merged in the campaign through #2432 before this corpus record lane, zero
  cross-lane collisions, every bot review thread resolved pre-merge.
- M-FWD3-EVIDENCE recorded 347 git worktrees and 11 mechanically-safe cleanup candidates;
  inventory sha `6bcb7fe11ab6410155d175682c43791af3b2b84cdff903c15632b6f27418788a`.
  Refresh live counts before any cleanup lane because later worktrees change the total.
- Nonlocal production-readiness gate: 6 of 7 criteria pass; sole blocked criterion
  `final_nonlocal_production_admission_present`, with blocked reason
  `nonlocal_production_readiness_final_admission_missing`.
- RC3 acceptance list: declared=58, tracked=58, drift-guarded.

## Corpus-Go Arc Evidence Registry Extension (M-PROGRAM-CONTEXT-2, 2026-07-05)

M-PROGRAM-CONTEXT-2 verified this extension against live GitHub PR state, live
`project6-origin/main`, committed code paths, the read-only
`C:/p6store/corpus_run` durable root, and the #2433 count surface.

## Merged PR / SHA Table Extension

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2425 | `9d44e79b` | `test(sec-xbrl): cover controlled reveal pagination gaps` | merged; ancestor of `project6-origin/main` |
| #2426 | `f0f32413` | `docs: add SEC XBRL corpus run plan` | merged; ancestor of `project6-origin/main` |
| #2427 | `99efa28d` | `Harden SEC XBRL corpus admission gates` | merged; ancestor of `project6-origin/main` |
| #2428 | `154b8a38` | `Add historical SEC taxonomy pins` | merged; ancestor of `project6-origin/main` |
| #2429 | `4ad672f3` | `Handle bare SEC taxonomy cache layout` | merged; ancestor of `project6-origin/main` |
| #2430 | `24502721` | `Add 2026 SEC taxonomy pins` | merged; ancestor of `project6-origin/main` |
| #2431 | `92b069b9` | `fix(sec-xbrl): admit explicit corpus form selection` | merged; ancestor of `project6-origin/main` |
| #2432 | `2d6fdbde` | `Load SEC inline transform plugin` | merged; ancestor of `project6-origin/main` |
| #2433 | `889f8707` | `docs: record corpus-go run truth` | record lane; merged; ancestor of `project6-origin/main` |

## Corpus-Go Run Artifacts (Operator-Local Durable Root)

| Artifact | Anchor | Meaning |
|---|---|---|
| Aggregate run report | sha256 `52385f07a1a4dc29871708602bacadb159da44499bb950fd887665abd3879e91` at `C:/p6store/corpus_run/CORPUS_GO_RUN_REPORT.json` | Per-ticker outcomes, run gates, and notes. The source payload hash `113ce73679547f5d202cb273ebca9d2373f90fab9ae688e9159cc7894c3cee10` is stale for the file currently present at this path. |
| Supported filings | `39` | Verified from `supported_filing_count`. |
| Supported issuers | `21` | Verified from `supported_issuer_count`. Distribution: 18 full domestic 10-K/10-Q pairs, MSFT supported 10-Q with named 10-K block, plus CURLF/CRLBF supported 40-F filings. |
| Run gates | 4/4 PASS | `every_ticker_dispositioned`, `zero_unnamed_failures`, `min_30_supported_filings`, and `min_15_supported_issuers` are all `true`. |
| Named blocks | IFRS annuals x6; 6-K no-inline slots; unknown/alias rows x4; MSFT 10-K named model-error block | All named by ticker/form/reason in the aggregate report; no unnamed failure was found. |
| Per-chunk/ticker summaries | 37 JSON summaries under `C:/p6store/corpus_run` | One per attempt/supplement family, preserving fresh-id discipline. |
| Preserved chunk DBs | 35 DB files under `C:/p6store/corpus_run/db` | Verifies the storage supplement's DB preservation count. |
| Storage/integrity supplement | sha256 `bce4d7800db4742577fcfe1214618ab7730057e46a4e6bd374b7d8848f6eb1e3` at `C:/p6store/corpus_run/STORAGE_INTEGRITY_SUPPLEMENT.json` | H6 PASS; 1,660 artifacts; 1,822,365,176 bytes; 861,740,326,912 free bytes; `validate_only=true`; `mutation_performed=false`. The source payload hash `22cda8340cef3ae68cd08d1a09748e384feefc8a82700ddfb4b8304294be0141` is stale for the file currently present at this path. |
| Gate correction | v1 gates = 4/4 of a 5-gate plan | The run-plan's storage-preflight gate was omitted from the v1 set and is satisfied by the storage/integrity supplement; all five plan gates now have evidence. |

## Root-Cause Probe Evidence (Transforms Diagnosis)

| Step | Anchor |
|---|---|
| Pilot uniform block | Payload-authored operator evidence: 8 filings with `arelle_model_errors_present` and `model_error_count=8` per filing. |
| Hypothesis refuted | Payload-authored operator evidence: 2026 provisioning did not change the 8-error count. |
| Error class isolated | Payload-authored operator evidence: direct Arelle-API probe isolated `ix11.11.1.2:invalidTransformation` for the SEC transformation registry namespace. |
| Canonical source | `tools/arelle_sec_transforms/PINNING.md` and `tools/arelle_sec_transforms/` exist on live main; `text2num.py` is present with its MIT helper provenance. |
| Helper load and diagnostics | `tools/sec-xbrl-arelle.py` loads `tools/arelle_sec_transforms`; `backend/tests/test_sec_xbrl_arelle_helper.py` covers plugin load failure and model-error-code redaction. |
| Fix re-proven | The #2433/#2432 record carries the operator re-probe claim that the previously blocked filing reached `model_error_count=0`; code/test anchors for the fix are present on live main. |

## Provisioning State (Arelle Runtime)

- Committed provisioning anchors verified: PR #2428, #2429, and #2430 are
  merged into `project6-origin/main`; `tools/sec-xbrl-arelle-provision.py`
  exists; `backend/tests/test_sec_xbrl_arelle_provisioning.py` verifies 2026
  pin admission, partial 2019/2020 SEC cache handling, admitted years, and the
  default-year posture.
- Payload-authored runtime claim not re-hashed here: the named
  `provision_report_2021_2026.json` was not found under `C:/p6store` during
  this lane's read-only search, so the 12/12 package and 24/24 entrypoint
  details remain operator-context rather than a re-derived durable file hash in
  this registry extension.
- IFRS family remains not provisioned and is the named follow-up in D18.

## Key Code Anchors Added This Arc

| Surface | Verified location |
|---|---|
| SEC transforms plugin + pinning | `tools/arelle_sec_transforms/` and `tools/arelle_sec_transforms/PINNING.md` |
| Plugin load + error-code diagnostics | `tools/sec-xbrl-arelle.py` |
| Year/family admission + provisioning pins | `tools/sec-xbrl-arelle-provision.py` |
| Explicit corpus forms passthrough | `backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py` and `backend/app/api/layer3/__init__.py` |
| Pre-inline / XML / semantic blockers / decode parity | `backend/app/services/layer3_sec_xbrl_sidecar.py` |
| 200 MB ceiling constant | `backend/app/services/layer3_sec_edgar_live_source_artifact.py` |
| Corpus hardening tests | `backend/tests/test_sec_xbrl_corpus_hardening.py` |
