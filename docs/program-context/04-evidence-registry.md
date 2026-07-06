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
`project6-origin/main`, committed code paths, the read-only canonical durable
root `C:/p6store`, and the #2433 count surface.

Supersession boundary: for the aggregate report hash and the supported-scope
distribution, this dated extension is the current evidence authority over older
corpus evidence summaries in `docs/MASTER_CONTEXT.md`,
`docs/program-context/01-arc-ledger.md`, `docs/program-context/03-forward-plan.md`,
the Layer 3 progress board, and the Layer 3 progress/proof manifests. Those
older surfaces remain historical until a broader alignment lane is explicitly
authorized; do not use their stale hash or "all major domestic 10-K+10-Q pairs"
wording as current evidence.

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
| Aggregate run report | sha256 `52385f07a1a4dc29871708602bacadb159da44499bb950fd887665abd3879e91` at durable-root relative `corpus_run/CORPUS_GO_RUN_REPORT.json` under canonical root `C:/p6store` | Per-ticker outcomes, run gates, and notes. The source payload hash `113ce73679547f5d202cb273ebca9d2373f90fab9ae688e9159cc7894c3cee10` is stale for the file currently present at this path. |
| Supported filings | `39` | Verified from `supported_filing_count`. |
| Supported issuers | `21` | Verified from `supported_issuer_count`. Distribution: 18 full domestic 10-K/10-Q pairs, MSFT supported 10-Q with named 10-K block, plus CURLF/CRLBF supported 40-F filings. |
| Run gates | 4/4 PASS | `every_ticker_dispositioned`, `zero_unnamed_failures`, `min_30_supported_filings`, and `min_15_supported_issuers` are all `true`. |
| Named blocks | IFRS annuals x6; 6-K no-inline slots; unknown/alias rows x4; MSFT 10-K named model-error block | All named by ticker/form/reason in the aggregate report; no unnamed failure was found. |
| Per-chunk/ticker summaries | 37 JSON summaries at durable-root relative `corpus_run/*.json` | One per attempt/supplement family, preserving fresh-id discipline. |
| Preserved chunk DBs | 35 DB files at durable-root relative `corpus_run/db` | Verifies the storage supplement's DB preservation count. |
| Storage/integrity supplement | sha256 `bce4d7800db4742577fcfe1214618ab7730057e46a4e6bd374b7d8848f6eb1e3` at durable-root relative `corpus_run/STORAGE_INTEGRITY_SUPPLEMENT.json` under canonical root `C:/p6store` | H6 PASS; 1,660 artifacts; 1,822,365,176 bytes; 861,740,326,912 free bytes; `validate_only=true`; `mutation_performed=false`. The source payload hash `22cda8340cef3ae68cd08d1a09748e384feefc8a82700ddfb4b8304294be0141` is stale for the file currently present at this path. |
| Supplemental storage evidence | The owner-handoff completion gates remain the four #2433 run-level gates | The storage/integrity supplement provides additional storage-preflight evidence for the historical run-plan checklist; it is not a fifth completion gate for the completed corpus record. |

## Root-Cause Probe Context and Committed Anchors

| Step | Anchor |
|---|---|
| Pilot/probe facts | Payload-authored operator context only in this lane; not admitted here as registry evidence because no durable probe report hash or committed artifact path was located. |
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

## Corpus-Go 39 -> 40 Addendum (M-CORPUS-40-ADDENDUM, 2026-07-05)

This addendum supersedes only the MSFT 10-K disposition and supported-filing
distribution recorded by #2433/#2434. The 39-filing record remains historical:
this lane records the later zero-egress governed replay that moved the MSFT
FY2025 10-K from named block to supported-equivalent via governed receipt-bound
replay; operator-attested + independently regraded
(`PASS_WITH_ATTESTED_FIELDS`). Attested fields are not treated as unqualified
verification.

### Addendum PR / SHA Anchors

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2434 | `873d8883` | `docs: append corpus-go program context addenda` | merged; ancestor of `project6-origin/main` |
| #2436 | `fc141039` | `Pin SEC CYD taxonomy family` | merged; ancestor of `project6-origin/main`; adds `cyd-2024` family pin and the `taxonomy_family_vintage_unprovisioned` reason code |
| #2435 | `fab89ced` | `docs: add SEC corpus run gate spec` | merged; ancestor of `project6-origin/main`; records the G1/G4/G6/G9/G10 gate framing used by this addendum |

### Addendum Artifacts (Hash-Only Admission)

| Artifact | Anchor | Meaning |
|---|---|---|
| Provisioning rerun report | sha256 `04b3e9354cf92ffd6221d2859b64d2e60c698df323938e5e4614cf9b861ff159` for `provision_report_2021_2026.json` under canonical root `C:/p6store` | Operator rerun reported `ready=true`, 12 packages, and 25/25 offline entrypoints including `cyd-2024`; closes the #2434 evidence gap where this report was previously not found. Content is not committed because it embeds machine-local paths. |
| Governed MSFT FY2025 10-K replay | `client_request_id` `cyd-replay-msft-10k-r1`; parser receipt hash `4bf632ece7dc4a0c23661d954b8f4475c7f4e0e26303eb6a20b68469ad8ba911`; sidecar self-declared hash `dc3f38132db62b331d469d0307f62e805ad164580253d455ea65103e462edd87` | Status `READY`; 1829/1829 facts resolved; model_error_count 0; value store persisted 1829 records. |
| Replay value-store binding | value_store_hash `bb76a9cd074f6f16446f1ce33638c12607675efaaa9d2e430f16f747265b98dd`; namespace `4502e1c70863a4bd0067e5f0de4325758d3542e05df223d702747c1886ee6ca9`; retention `sec_xbrl_public_financial_value_retention_v1` | Hygiene accepted with no override; records hash/count/policy evidence only, with no raw values. |
| Evidence bundle | sha256 `e1b15bd206ee271fbd4131f7cb083f71f04573a4bbc318bb51b4f531dbd00199` for `corpus_run/CYD_PHASE2_REPLAY_EVIDENCE.json` under canonical root `C:/p6store` | Hash-anchored zero-egress replay bundle; content is not committed. |
| Independent regrade | sha256 `214f2f1014d3ecc06f7e49fd6ce1fc2d17a1811ce53452966d5381329aadff6d` for `corpus_run/CYD_PHASE2_REGRADE.md` under canonical root `C:/p6store` | Verdict `PASS_WITH_ATTESTED_FIELDS`; zero hash mismatches. Attested-only fields are the sidecar self-reported zero-network invariants, PR-verification metadata, and arming narrative. |

### Corpus Delta And Gate Framing

| Field | Addendum record |
|---|---|
| Supported filings | `40`, with MSFT FY2025 10-K supported-equivalent via governed receipt-bound replay |
| Supported issuers | `21`, unchanged |
| Domestic pairs | `19` full domestic 10-K/10-Q pairs |
| Foreign/OTC scope | CURLF/CRLBF 40-Fs unchanged |
| MSFT disposition | Previous named 10-K block superseded by governed replay; MSFT is no longer the domestic pair exception |
| Historical 72-vs-16 divergence | Reconciled: 72 = 16 genuine CYD errors plus 56 probe-local `ixt` invalidTransformation results from a direct-API probe that loaded the plugin without `loadCustomTransforms`; the governed helper count of 16 was correct. |
| Gate status | Single-filing zero-egress replay lane: G1 disposition taxonomy addressed by the MSFT supported-equivalent disposition and registry-by-reference reason-code posture; G2 zero unnamed/silent failures addressed by receipt hashes, disposition, and regrade; G3 volume threshold addressed by 40 supported filings / 21 supported issuers against the 30/15 historical thresholds; G4 storage preflight PASS validate-only with 863.9GB free; G6 regrade redaction scan clean; G9 independent regrade complete; G10 no deviations. Live-egress-only controls remain dormant for this zero-egress replay. |

This addendum admits no backend/tool/test change, no network egress by this
record lane, no production-readiness/default-on/value-reveal claim, no raw
values, no accession/CIK, and no local path beyond the established `C:/p6store`
root convention.

## Program-Context 3 Evidence Registry Extension (M-PROGRAM-CONTEXT-3, 2026-07-06)

This extension records the verified anchors used by the M-PROGRAM-CONTEXT-3
landing PR #2439 to land D20-D26, the forward program refresh, and the
MASTER_CONTEXT current-pointer refresh. Handoff payload files were read in full
and hash-verified during landing, but they are not committed or re-derivable
from repo history, so they are not admitted as registry evidence here. Every
load-bearing claim below was re-derived from live GitHub state, current
`project6-origin/main`, or hash-only durable artifacts.

### Merged PR / SHA Table Extension

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2435 | `fab89ced` | `docs: add SEC corpus run gate spec` | merged; ancestor of `project6-origin/main`; `corpus-run-gate-spec.md` records ACTIVE-NOW and LIVE-RUN-ONLY gate classes |
| #2436 | `fc141039` | `Pin SEC CYD taxonomy family` | merged; ancestor of `project6-origin/main`; current source contains `sec-cyd-2024` pin, flat CYD archive extraction, and `taxonomy_family_vintage_unprovisioned` |
| #2437 | `c6bb87f8` | `docs: record corpus 40 addendum` | merged; ancestor of `project6-origin/main`; records 40 supported filings, 21 issuers, 19 full domestic pairs, and operator-attested + independently regraded MSFT replay framing |
| #2438 | `be8efadb` | `ci: parallelize backend coverage job` | merged; ancestor of `project6-origin/main`; changed only `.github/workflows/playwright.yml` and `backend/tests/requirements-layer3-api.txt` |

### Durable Artifact Hashes Re-Verified For This Extension

| Artifact | SHA-256 / Anchor | Meaning |
|---|---|---|
| Provisioning rerun report | `04b3e9354cf92ffd6221d2859b64d2e60c698df323938e5e4614cf9b861ff159` for `provision_report_2021_2026.json` under `C:/p6store` | Structured read: `ready=true`, 12 taxonomy packages, 12 loaded packages, 25 offline entrypoints, years 2021-2026. Content remains hash-only because it contains machine-local paths. |
| Governed replay evidence bundle | `e1b15bd206ee271fbd4131f7cb083f71f04573a4bbc318bb51b4f531dbd00199` for `corpus_run/CYD_PHASE2_REPLAY_EVIDENCE.json` under `C:/p6store` | Structured read: `client_request_id=cyd-replay-msft-10k-r1`, status `ready`, 1829 resolved facts, model_error_count 0, `network_request_made=false` as operator-attested bundle/receipt invariant. |
| Governed replay value-store binding | value_store_hash `bb76a9cd074f6f16446f1ce33638c12607675efaaa9d2e430f16f747265b98dd`; namespace `4502e1c70863a4bd0067e5f0de4325758d3542e05df223d702747c1886ee6ca9`; retention `sec_xbrl_public_financial_value_retention_v1` | Structured read: value store persisted 1829 records; hygiene accepted with no override. |
| Independent regrade | `214f2f1014d3ecc06f7e49fd6ce1fc2d17a1811ce53452966d5381329aadff6d` for `corpus_run/CYD_PHASE2_REGRADE.md` under `C:/p6store` | Verdict `PASS_WITH_ATTESTED_FIELDS`; mismatches NONE; operator-attested-only fields named explicitly. |
| IFRS/CYD vintage enumeration | `72391c5da90bb3e3439979fcf23106f0b664617e6a091b5a153bf3978ca896e4` for `ifrs-cyd-vintage-enumeration.md` | Handoff-local enumeration artifact; admitted by name and hash only. |
| Worktree cleanup manifest | `9b98fab6ade7ff21fa95e1c66855378f4d5f0ee2365586716e7d0621a8a5c943` for `worktree-cleanup-manifest.json` | Stale sign-off artifact computed as of main `873d8883`; not a live deletion list. Fresh recompute required before any cleanup. |

### Coverage-Xdist Evidence (#2438)

| Evidence | Anchor |
|---|---|
| Scope fence | PR #2438 changed `.github/workflows/playwright.yml` and `backend/tests/requirements-layer3-api.txt` only; no backend app/test source edits and no release-gate `needs` edit. |
| Coverage parity | PR #2438 body records serial and capped `-n 4` coverage at 95.18%, XML lines-covered 12063 / lines-valid 12674, exact covered-line-set and executable-line-set parity for `app.api.layer3` and `app.services.layer3_sec_xbrl_in_app_auth_policy`. |
| Collect parity | PR #2438 body records 2659 tests collected serial and 2659 under capped xdist. |
| Floor-trip | PR #2438 body records scratch-only proof exit 1 at 88.86% with exactly one required-coverage failure. |
| Soak | PR #2438 body records 10/10 strictly serial capped `-n 4` local runs, all exit 0, min/mean/max 209.57s / 222.77s / 234.42s. |
| Post-merge CI | Main run `28776807974` on `be8efadb` succeeded; `backend-coverage` job `85322639931` ran 08:01:32-08:09:46 UTC (494 seconds / 8m14s); `release-gate` job `85324062233` succeeded. |

### Current Source / Workflow Anchors Re-Verified

| Surface | Verification |
|---|---|
| 12 default-false boolean gates | AST count over `backend/app/core/config.py`: 12 `bool` settings default false, including live network, corpus validation, nonlocal authorization, value reveal, official ticker resolution, controlled value reveal submit, storage-root override ack, model egress, production admission evaluator, and trusted proxy mode. |
| CYD family pin and reason code | `tools/sec-xbrl-arelle-provision.py` declares `sec-cyd-2024`; `backend/tests/test_sec_xbrl_arelle_provisioning.py` covers the pin and flat archive extraction; `backend/app/services/layer3_sec_xbrl_sidecar.py` contains `taxonomy_family_vintage_unprovisioned`. |
| Corpus-run gate registry | `next_milestone_plans/Layer3_planning_docs/corpus-run-gate-spec.md` classifies G1, G2, G4, G6, G9, and G10 as ACTIVE-NOW, G3/G5/G7/G8 as LIVE-RUN-ONLY where applicable or dormant for zero-egress lanes. |
| Release-gate needs gap | `.github/workflows/playwright.yml` release-gate needs are `release-lock-install`, `backend-layer3-api`, `backend-coverage`, `backend-migrations-postgres`, and `sec-xbrl-arelle-provisioning`; it does not need `root-tests`, `nrc-aps-ocr`, or the Playwright `test` aggregator. |
| Orphaned workflow registration | GitHub lists an active `SEC XBRL Tier-2 review gate` workflow, while current main has no `.github/workflows/sec-xbrl-tier2-gate.yml`. |

This extension admits no backend/tool/test change, no live egress, no production
readiness, no default-on change, no raw retained values, no accession/CIK, and
no machine-local path beyond the established `C:/p6store` root convention.

## Program-Context 4 Evidence Registry Extension (M-PROGRAM-CONTEXT-4, 2026-07-06)

This extension records the verified anchors used by the M-PROGRAM-CONTEXT-4
landing lane to add D27, split F3 into F3a/F3b, and refresh current pointers
after #2440. Handoff payload files were read in full and hash-verified during
landing, but they are not committed or re-derivable from repo history, so they
are not admitted as registry evidence. Every load-bearing claim below was
re-derived from live GitHub state, current `project6-origin/main`, committed
source, or hash-only durable artifacts.

### Merged PR / SHA Table Extension

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2440 | `6d962b24` | `Pin SEC CYD 2025 taxonomy archive` | merged; ancestor of `project6-origin/main`; changed `tools/sec-xbrl-arelle-provision.py`, `backend/tests/test_sec_xbrl_arelle_provisioning.py`, and `backend/tests/test_sec_xbrl_sidecar.py`; 1/1 review thread resolved; CI green |

### Durable Artifact Hashes Re-Verified For This Extension

| Artifact | SHA-256 / Anchor | Meaning |
|---|---|---|
| CYD 2025 fetch arming record | `af704db4bf1b171bd1a8bea7a6b03fcf7bbd57e8f1a92cdadc02256ef5f490f6` for `corpus_run/CYD2025_FETCH_ARMING.json` under `C:/p6store` | Structured read: `written_before_first_request=true`, host list exactly `xbrl.sec.gov`, request budget 10, and `xbrl.ifrs.org` explicitly not authorized. |
| Operator-built `cyd-2025.zip` | `ad7b166a3913778a4fabb15f3a4431d80eb1930d9cc1e271c318f7b4cffdfc33`, 208,667 bytes | Machine-local taxonomy archive, admitted by hash/size only. Re-read zip has 7 root-level members; all member hashes match the PINNING note; zip metadata is deterministic: 1980-01-01 timestamps, `create_system=0`, stored compression, `0o644` external attrs. |
| `PINNING-cyd-2025.md` | `9cb98156f2780efd44e8a9954881331e96b00b6b86c726b77bf9e0211bec2e8e`, 2,347 bytes | Machine-local provenance note, admitted by hash/size only. The note records 7 SEC loose-file member hashes and the deterministic zip recipe. |
| Post-#2440 provisioning report | `7d5f719c274b2c64275498b52832913d6ad0914847bc4abde54e2842063527ee` for `provision_report_2021_2026_r2.json` under `C:/p6store` | Structured read: `ready=true`, 12/12 taxonomy packages loaded, 26/26 offline entrypoints OK, no blocked reasons, and both `cyd/2024` and `cyd/2025` entrypoints loaded. Content is not committed because it embeds machine-local paths. |

### Current Source / Workflow Anchors Re-Verified

| Surface | Verification |
|---|---|
| `sec-cyd-2025` pin | `tools/sec-xbrl-arelle-provision.py` declares `sec-cyd-2025` with URL `https://xbrl.sec.gov/cyd/2025/`, operator-built flag, archive hash `ad7b166a...fc33`, 208,667 bytes, and 7 member hashes. |
| Operator-built archive construction | `tools/sec-xbrl-arelle-provision.py` contains `_download_operator_built_archive` and deterministic `_build_flat_zip_archive`; tests assert fixed timestamp, `create_system=0`, stored compression, and deterministic byte equality. |
| CYD 2025 extraction/admission | `backend/tests/test_sec_xbrl_arelle_provisioning.py` verifies `cyd/2025` flat extraction and 2025 SEC entrypoint URLs; `backend/tests/test_sec_xbrl_sidecar.py` verifies sidecar readiness when the provisioner package set includes `cyd-2025.zip`. |
| PR #2440 validation record | PR body records focused suite `86 passed, 1 skipped`, deterministic archive rebuild matching `ad7b166a...fc33`, `py_compile`, and `git diff --check`; final CI run green including `sec-xbrl-arelle-provisioning`, `backend-coverage`, and `release-gate`. |
| Review-thread state | GraphQL `reviewThreads(first:100)` for PR #2440 returned `totalCount=1` and `isResolved=true`. |
| 12 default-false boolean gates | AST/source-aware check over `backend/app/core/config.py` found the same 12 false defaults for live network, corpus validation, nonlocal authority, value reveal, official ticker resolution, controlled submit, storage-root override ack, model egress, production admission evaluator, trusted proxy, and related inventory/internal-store gates. |

This extension admits no backend/tool/test change by this docs lane, no new
live egress, no IFRS fetch, no production readiness, no default-on change, no
value reveal, no raw retained values, no accession/CIK, and no machine-local
path beyond the established `C:/p6store` root convention.
