# 04 — Evidence Registry

## 2026-09-04 current evidence anchors

| Claim | Re-derivable or sanitized anchor | Limit |
|---|---|---|
| Current implementation frontier | `project6-origin/main` `348956f38eccac4d55e2e42857f1ad5eecbd1382` (#2496 merge, 2026-09-06 UTC) | Source/config/tests remain authority |
| Public analysis default | `backend/app/core/config.py` field `LAYER3_PUBLIC_DATASET_ANALYSIS_ENABLED=false` | Default-off; not an arming record |
| Public values default | `backend/app/core/config.py` field `LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED=false` | Values require both flags |
| Public-source admission | `backend/app/services/layer3_workbench.py`; newest `sciencebase/public_api` provenance | New public family only; does not widen shared APS admission |
| Value response boundary | `backend/app/services/layer3_workbench.py`; provenance co-display and storage-reference exclusion | Bounded admitted JSON output only |
| Merged PR #2495 | head `44c3a433d39c5c676c2e1d163ab19b8e0965f6bf`; merge commit `de693eea607fba511fb4e95f121bebaa54e82e13`; 2026-09-06 UTC | On main; directory-wide `state/agent-inbox/` ignore rule; untracks nothing |
| Merged PR #2496 | head `1de3b1e291a854ef69a3d46bfa1cfd31cc240349`; merge commit `348956f38eccac4d55e2e42857f1ad5eecbd1382`; 2026-09-06 UTC | On main; method selection remains default-off |
| Qualified local derivative | 60 complete quarterly observations; SHA-256 `5ad88a04e4232227b5d1a59bbc1531dfd3deca8665401b0184b16d0310eb4bd0` | Operator-local unpublished evidence; normalized coordinate and per-point lineage; not ScienceBase or persisted Layer 3 proof |

The relevant merged tranches and analytical qualifications are in
[MASTER_CONTEXT](../MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).
No local raw path, issuer/accession identifier, SEC URL, raw observation value,
operator identity, or private record is carried into this registry.

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
| IFRS follow-up group | `SONY`, `CCJ`, `DNN`, `NXE`, `MT`, `TSM` | Acquired and retained; admitted reason code `taxonomy_year_unprovisioned`; operator symptom `arelle_model_errors_present`; package prep superseded by #2440/#2442; current follow-up is retained foreign-annual replay/result recording |
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

(Base counts below are as-of their original authoring; for live values see the dated extension sections and the current-pointer docs — MASTER_CONTEXT and 03-forward-plan.)

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

This extension records the verified anchors used by M-PROGRAM-CONTEXT-4 /
PR #2441 to add D27, split F3 into F3a/F3b, and refresh current pointers
after #2442. Handoff payload files were read in full and hash-verified during
landing, but they are not committed or re-derivable from repo history, so they
are not admitted as registry evidence. Every load-bearing claim below was
re-derived from live GitHub state, current `project6-origin/main`, committed
source, or hash-only durable artifacts.

### Merged PR / SHA Table Extension

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2440 | `6d962b24` | `Pin SEC CYD 2025 taxonomy archive` | merged; ancestor of `project6-origin/main`; changed `tools/sec-xbrl-arelle-provision.py`, `backend/tests/test_sec_xbrl_arelle_provisioning.py`, and `backend/tests/test_sec_xbrl_sidecar.py`; 1/1 review thread resolved; CI green |
| #2442 | `e7e9e867` | `Pin IFRS 2025 taxonomy package` | merged; ancestor of `project6-origin/main`; changed the same provisioner/sidecar test surfaces; 0 review threads; CI green |

### Durable Artifact Hashes Re-Verified For This Extension

| Artifact | SHA-256 / Anchor | Meaning |
|---|---|---|
| CYD 2025 fetch arming record | `af704db4bf1b171bd1a8bea7a6b03fcf7bbd57e8f1a92cdadc02256ef5f490f6` for `corpus_run/CYD2025_FETCH_ARMING.json` under `C:/p6store` | Structured read: `written_before_first_request=true`, host list exactly `xbrl.sec.gov`, request budget 10, grant basis is the owner 2026-07-06 generic proceed directive class-scoped by D27, and `xbrl.ifrs.org` explicitly not authorized. |
| Operator-built `cyd-2025.zip` | `ad7b166a3913778a4fabb15f3a4431d80eb1930d9cc1e271c318f7b4cffdfc33`, 208,667 bytes | Machine-local taxonomy archive, admitted by hash/size only. Re-read zip has 7 root-level members; all member hashes match the PINNING note; zip metadata is deterministic: 1980-01-01 timestamps, `create_system=0`, stored compression, `0o644` external attrs. |
| `PINNING-cyd-2025.md` | `9cb98156f2780efd44e8a9954881331e96b00b6b86c726b77bf9e0211bec2e8e`, 2,347 bytes | Machine-local provenance note, admitted by hash/size only. The note records 7 SEC loose-file member hashes and the deterministic zip recipe. |
| Post-#2440 provisioning report | `7d5f719c274b2c64275498b52832913d6ad0914847bc4abde54e2842063527ee` for `provision_report_2021_2026_r2.json` under `C:/p6store` | Structured read: `ready=true`, 12/12 taxonomy packages loaded, 26/26 offline entrypoints OK, no blocked reasons, and both `cyd/2024` and `cyd/2025` entrypoints loaded. Content is not committed because it embeds machine-local paths. |
| Retained IFRS 2025 package | `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19`, 2,103,003 bytes | Machine-local taxonomy archive admitted by hash/size and PR #2442 source/test evidence only. It is not committed into program-context docs and does not by itself publish retained foreign-annual replay results. |

### Current Source / Workflow Anchors Re-Verified

| Surface | Verification |
|---|---|
| `sec-cyd-2025` pin | `tools/sec-xbrl-arelle-provision.py` declares `sec-cyd-2025` with the SEC CYD 2025 loose-file base host class, operator-built flag, archive hash `ad7b166a...fc33`, 208,667 bytes, and 7 member hashes. |
| Operator-built archive construction | `tools/sec-xbrl-arelle-provision.py` contains `_download_operator_built_archive` and deterministic `_build_flat_zip_archive`; tests assert fixed timestamp, `create_system=0`, stored compression, and deterministic byte equality. |
| CYD 2025 extraction/admission | `backend/tests/test_sec_xbrl_arelle_provisioning.py` verifies `cyd/2025` flat extraction and 2025 SEC entrypoint URLs; `backend/tests/test_sec_xbrl_sidecar.py` verifies sidecar readiness when the provisioner package set includes `cyd-2025.zip`. |
| PR #2440 validation record | PR body records focused suite `86 passed, 1 skipped`, deterministic archive rebuild matching `ad7b166a...fc33`, `py_compile`, and `git diff --check`; final CI run green including `sec-xbrl-arelle-provisioning`, `backend-coverage`, and `release-gate`. |
| Review-thread state | GraphQL `reviewThreads(first:100)` for PR #2440 returned `totalCount=1` and `isResolved=true`. |
| IFRS 2025 package/admission | Current source declares the retained IFRS 2025 package pin, and PR #2442 validation records package-set/sidecar admission for the IFRS 2025 taxonomy package. |
| PR #2442 validation record | PR body records red expected failures, focused suite `89 passed, 1 skipped`, retained package hash `302afc7f...d19`, `py_compile`, and `git diff --check`; final CI run green including `sec-xbrl-arelle-provisioning`, `backend-coverage`, and `release-gate`. |
| 12 default-false boolean gates | AST/source-aware check over `backend/app/core/config.py` found the same 12 false defaults for live network, corpus validation, nonlocal authority, value reveal, official ticker resolution, controlled submit, storage-root override ack, model egress, production admission evaluator, trusted proxy, and related inventory/internal-store gates. |

This extension admits no backend/tool/test change by this docs lane, no new
live egress, no foreign-annual replay/result publication, no production
readiness, no default-on change, no value reveal, no raw retained values, no
accession/CIK, and no machine-local path beyond the established `C:/p6store`
root convention.

## Corpus 46 Evidence Registry Extension (M-CORPUS-46-RECORD, 2026-07-06)

This extension records the verified anchors used by M-CORPUS-46-RECORD /
PR #2443 to append D28, refresh the forward/P2 current pointers, and record the
retained foreign IFRS annual replay closeout. Payload files were read in full
and hash-verified during landing, but they are not committed or re-derivable
from repo history, so they are not admitted as registry evidence. Every
load-bearing claim below was re-derived from live GitHub state, current
`project6-origin/main`, committed source, or hash-only durable artifacts.

### Merged PR / SHA Table Extension

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2437 | `c6bb87f8` | `docs: record corpus 40 addendum` | merged; ancestor of `project6-origin/main`; 4/4 review threads resolved; CI green including `backend-coverage` |
| #2440 | `6d962b24` | `Pin SEC CYD 2025 taxonomy archive` | merged; ancestor of `project6-origin/main`; 1/1 review thread resolved; CI green including `backend-coverage` |
| #2441 | `098e96ea` | `docs: land program context payload 4` | merged; current base for this lane; 3/3 review threads resolved; CI green including `backend-coverage` |
| #2442 | `e7e9e867` | `Pin IFRS 2025 taxonomy package` | merged; ancestor of `project6-origin/main`; 0 review threads; CI green including `backend-coverage` |

### Durable Artifact Hashes Re-Verified For This Extension

| Artifact | SHA-256 / Anchor | Meaning |
|---|---|---|
| IFRS fetch arming record | `cb275a03cbbadfcdb55a8eedc3d585f8dd5eb6cb4c9a8b45bac986ceb080b8f6` for `corpus_run/IFRS2025_FETCH_ARMING.json` under `C:/p6store` | Structured read: `written_before_first_request=true`, owner grant text present, IFRS host class allowed, request budget 5, and non-authorized classes include SEC EDGAR filing egress, default flips, value reveal, and production claims. |
| IFRS 2025 PINNING note | `20dfec68cccba35eb9969763ec056ac568824dd0df5f5b9c43151ac854945c07`, 1,957 bytes | Records the 5/5 budget-constrained request ledger and package verification by hash/size only. Raw request URLs are not copied into committed docs. |
| Retained IFRS 2025 package | `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19`, 2,103,003 bytes | Retained taxonomy package admitted by hash/size and PR #2442 source/test evidence. |
| Post-#2442 r3 provisioning report | `6ff72308060a5769ff708b556bc3e9a6269ac867b1f06eaa6d0291f4a8a9708c` for `provision_report_2021_2026_r3.json` under `C:/p6store` | Structured read: `ready=true`, 13/13 taxonomy packages loaded, 26/26 SEC entrypoints intact, IFRS 2025 offline entrypoints loaded, no blocked reasons, and raw/default/value-reveal non-goals preserved. Content is not committed because it embeds machine-local paths. |
| IFRS replay results | `7d691b6ac96fe31e40797b9e1ef582274e4792fb331c0071f821250c9189bbc7` for `corpus_run/IFRS_REPLAY_RESULTS.json` under `C:/p6store` | Six rows: all `ready`, stores persisted, counts 4693 / 886 / 1582 / 7335 / 2670 / 3565, total 20,731 records. |
| IFRS phase-3 replay evidence bundle | `a49b9c5553fd21788307b2dae9407b36582a97b467780aeeceda7772c44c40ff` for `corpus_run/IFRS_PHASE3_REPLAY_EVIDENCE.json` under `C:/p6store` | Structured read: 6/6 retained annual replays `READY`, zero named blocks, stores persisted, corpus delta 40 -> 46, #2440/#2442 pins merged, G4/H6 storage preflight validate-only, and no production/default/value-reveal/SEC-egress claim. |
| IFRS phase-3 independent regrade | `6e755725e65c11fb7fd1ddc926911804aebf924b79da9fc553f56a88b2bce2e3` for `corpus_run/IFRS_PHASE3_REGRADE.md` under `C:/p6store` | Verdict `PASS_WITH_ATTESTED_FIELDS`; mismatches NONE; row-1 and row-4 sidecar receipts re-derived for counts, persisted store state, retention policy, hygiene accepted/no override, sidecar receipt hash, and value_store_hash. |

### Replay Result Rows

| Client request id | Status | Resolved/value records | Sidecar receipt hash | Value-store hash |
|---|---|---:|---|---|
| `ifrs-replay-01-r1` | `ready` | 4693 | `5885118dc204f47c98c09dd6a7cceaca276bb3846e262a799806199d43d85fec` | `6790e8868a0db8dd366fbc1cb161a6a4bdc141c3f41ec2ec7542697b6655eda8` |
| `ifrs-replay-02-r1` | `ready` | 886 | `d6730fa69ad957a992d9f680b693d7650f95c4b31d56bfcf7329c11dfd80cb03` | `007ed5424a0286ccae8880882905e2d8922fc5786c908f9a4f35082dad06627a` |
| `ifrs-replay-03-r1` | `ready` | 1582 | `5d86cd123b42bf693e75255c94a1c739cdba02a343e272e93b945292a647df27` | `6d5ec3b23cf8290158799d58d14edeeb8eaa4b7ea70a99b0a3cd25cd119a2caf` |
| `ifrs-replay-04-r1` | `ready` | 7335 | `396d0dd06fcced5812bb2059f7e2192da7412175ff4256550db14f80249e0f41` | `ac1a17738c9116d706f8196fbe3ad1301e15417418264cb72a00488ba11e150c` |
| `ifrs-replay-05-r1` | `ready` | 2670 | `e59cb5e8f826b4a938fce7e070111569bd7858f29fd3151721aadf228aee5c77` | `68ea993d2f1b4c689075ac9cd8af2da26d0a23a3798fb1a695066ced561e96be` |
| `ifrs-replay-06-r1` | `ready` | 3565 | `e3c86ef81c6fa5f5f784a665cba7ee47f916a54b2c389586f35e0e953fc47798` | `7d68a925173a1190fcb6a81acdce897efd171e366e84ab41d7c44e553e8a6565` |

### Corpus Delta And Gate Framing

| Field | Current record |
|---|---|
| Supported filings / issuers | `46` supported filings / `27` supported issuers. The issuer count is derived from the prior 21 supported issuers plus the six named distinct retained IFRS issuers moved to supported-equivalent replay outcomes after #2440/#2442 package prep. |
| Historical preservation | The #2433/#2434 39-filing record and #2437 40-filing addendum remain historical; this extension supersedes only the current open-F3 residual. |
| Replay totals | 6/6 `READY`; stores persisted; zero named blocks; 20,731 total resolved/value records. |
| Non-replay dispositions | `6-K` no-inline dispositions remain by design; `KAP`, `PDN`, `YCA`, and `TSMC-as-written` remain non-SEC or alias-resolution dispositions. |
| Gate status | G1/G2/G3 addressed by supported replay outcomes, zero unnamed replay failures, and 46 supported filings; G4/H6 storage preflight PASS validate-only; G6 redaction scan clean in regrade; G9 independent regrade complete; G10 no deviations. Live-egress-only controls remain dormant for this zero-SEC-egress replay record. |

### Current Source / Workflow Anchors Re-Verified

| Surface | Verification |
|---|---|
| Source base | Worktree based on `project6-origin/main` at `098e96eafd799d3a322d754b88058e5bd3ea7650`, the PR #2441 merge commit. |
| PR review-thread state | GraphQL `reviewThreads(first:100)` returned zero unresolved threads for #2437, #2440, #2441, and #2442 before this lane edited docs. |
| Provisioner/package source | PR #2440 and #2442 source/test anchors remain merged; this lane changes docs/manifests only and does not edit backend/tool/test source. |
| Sample sidecar receipts | Re-derived row-1 and row-4 sidecar receipt fields match the replay results for sidecar receipt hash, value_store_hash, resolved/value counts, persisted store state, retention `sec_xbrl_public_financial_value_retention_v1`, and hygiene accepted/no override. Raw receipt file hashes are intentionally not used as substitutes for embedded sidecar receipt hashes. |

This extension admits no backend/tool/test change, no network egress by this
record lane, no runtime/flag/schema/model/migration change, no sandbox or
`C:/p6store` mutation by this record lane, no raw value disclosure, no
accession/CIK disclosure, no local path disclosure beyond `C:/p6store`, no
production-readiness claim, no value-reveal claim, no nonlocal admission claim,
no default-on expansion, no unsupported IFRS readiness claim, and no broader
host-class authority for future taxonomy fetches.

## Preserve Sweep Archive (M-PRESERVE-SWEEP, 2026-07-06)

| Artifact | sha256 anchor | Meaning |
|---|---|---|
| Worktree disposition plan v2 | `ca5b06307ac2a6c3fdcdea932fae97ad49264677c82b361eb84555b9e7984afa`; 8,169 bytes; archived as `_authority/worktree-disposition-plan-v2.md` under `C:/p6store/worktree-preserve-archive/2026-07-06/` | Owner-authorized preserve-then-sweep plan used as the per-item disposition authority for the registered worktree cleanup execution. |
| Unlanded-content deep-dive and adversarial verification | `03f50a85e452121ddc65af4cecf3ba8f7cf98fb6e84f1dd1c9c3398a5c46c5fd`; 132,716 bytes; archived as `_authority/worktree-unlanded-deepdive-2026-07-06.json` under `C:/p6store/worktree-preserve-archive/2026-07-06/` | Evidence sibling for unique-content, ambiguous-content, nested Onlook, and unregistered-directory hardening corrections. |
| Preserve archive aggregate | `b45fcb611af657ed0edd925bd13cfe6bd3edc0206b45c08b11c2897efc2539b3`; `PRESERVE_ARCHIVE_AGGREGATE.json` under `C:/p6store/worktree-preserve-archive/2026-07-06/` | Aggregate over the three durable authority copies plus 30 snapshot manifests: 20 verified preserve snapshots and 10 failed/protected snapshots. This closes the previously deferred out-of-fence preserve-archive row by recording hash/count/disposition only. |
| Preserve archive aggregate P2 | `1ae49356c7154446c0e03d65812cf804c7d3a76510d40c4f221b6b42ddb2f67b`; `PRESERVE_ARCHIVE_AGGREGATE.json` under `C:/p6store/worktree-preserve-archive/2026-07-06/` | P2 update after fail-closed hold remediation and unregistered-directory adjudication. Aggregate now covers 44 snapshot manifests: 32 verified and 12 failed/held. This supersedes the parent aggregate row only for post-P2 verification of the same archive path. |

## Governance Record Durability Archive (M-GOV-RECORD-DURABILITY, 2026-07-06)

| Artifact | sha256 anchor | Meaning |
|---|---|---|
| Inbox archive manifest | aggregate sha256 `42cd507ba527597fa5ab4128889ac5cf7caef3d213debd6cab65a19b4fb3a337`; archived primary inbox-log sha256 `861b55ec3ceb1a9bffd4faaf3e985f6d9d14ad800daafc63ec48f18a5597c1b7`; `ARCHIVE_MANIFEST.json` under `C:/p6store/inbox-archive/2026-07-06/` | Point-in-time off-repo archive of the dual-agent inbox logs, source mandates, JSON manifests, and program-context payload dirs; 50 copied files / 2,140,077 bytes; raw logs are not committed. |
| Campaign closeout record and inbox archive | Landed campaign record path `docs/campaign-records/2026-07-06-repo-ops-campaign.md`; source dossier sha256 `72ec9abdff999c7a346c2bde26549159d4e0d6d5c93fb15269b578d5bab62efc`; close archive aggregate sha256 `9691b2fa29f3eccff132ce4aba963bef154602d030a1f4fc889b09db32397ee3`; `ARCHIVE_MANIFEST.json` under `C:/p6store/inbox-archive/2026-07-07-close/` | Dated campaign record subordinate to `docs/MASTER_CONTEXT.md` and `docs/program-context/`; closing point-in-time archive of inbox logs, lane sources after banner backfill, inbox JSON manifests, worktree disposition plan v2, and the source campaign dossier; 48 copied files / 8,257,809 bytes; raw logs remain off-repo. |
| Forward-frontier dossier record and inbox archive | Landed record path `docs/campaign-records/2026-07-07-forward-frontier-dossier.md`; source dossier sha256 `48c6cdd1261bc3fb585982243cc451b5bde77b994132a293766c7b4b9899f06c` at landing; frontier archive aggregate sha256 `7aa1315f94170fe166e11e6eaf171d9e18153d3c3603d34585d09da9a09bb900`; `ARCHIVE_MANIFEST.json` under `C:/p6store/inbox-archive/2026-07-07-forward-frontier/` | Dated planning/frontier record subordinate to `docs/MASTER_CONTEXT.md` and `docs/program-context/`; direction fork open at landing. |
| Dirty-class worktree adjudication artifact | sha256 `0c87d88f0a6efb7bf056cbf82c12b649979b2cb522639d7db01a9a279bf2c3a0`; 189,380 bytes; dated 2026-07-06; `state/agent-inbox/worktree-dirty-adjudication-2026-07-06.json` | Read-only per-item adjudication and snapshot-first disposition plan for the 139 protected worktrees; records adjusted tally 115 tool-state-only, 8 superseded, 11 unique-content, 5 ambiguous, with zero mutations during adjudication. |
| Source-candidates decision chain record | Landed path `docs/campaign-records/2026-07-07-source-candidates.md`; source sha256 values at landing: dossier `d204e8485aceeab4ba0fbe030934d51d83416610f7cfa6c399023395dc4260f9`; adjudication `a0127d85628bb795179f95c562f1887e93db9bf0dcbe803586b05737f4853117`; adversarial review `0d9d8ed3b7db9f89d5cf39df4bc4bc711d113e0d73f66affc8689e86961166ec` | Dated planning record subordinate to `docs/MASTER_CONTEXT.md` and `docs/program-context/`; classifies 14 candidate anonymous public sources (3 include-now / 3 conditional / 2 defer / 6 excluded); evidence base for connector build mandates (connector-breadth / local-depth track); no off-repo archive refresh at landing - p6store replica cadence is owner-triggered and the next manual re-mirror will cover these files. |
| Connector-breadth program execution record | Landed path `docs/campaign-records/2026-07-08-connector-program.md`; nine source sha256 values at landing: `state/agent-inbox/wb-connector-source.md` `078ee827973edf87d6eea836fea654d6688d948e5f4d70fe15344827d608f7ee`; `state/agent-inbox/cftc-connector-source.md` `f54cc94b58097158fd3e14d7ed510841b1a24f192f4fbddee3d478914282aef0`; `state/agent-inbox/usgs-mcs-source.md` `71c8d8fe31753c958543ad1c14b3ddcf4b0d5cfa06b8a3a037431eb4c1debba4`; `state/agent-inbox/bls-connector-source.md` `0fad36a4bac42c85f160ea0238ac94a933d7b5c001c479fb6b66952aa0017834`; `state/agent-inbox/oecd-connector-source.md` `f23a526610ddb61a0402e11083b1f488ef91aeecf9a33313896a968a2d3e6618`; `state/agent-inbox/imf-connector-source.md` `6770142c3ea0ea926c1ad501e14bb956b8213572e57d9e11df84da4c046b4937`; `state/agent-inbox/wb-polish-source.md` `8752ec191b45fa104b56651af46a16ac42c0839470c4fd84ecc990f9427594d5`; `state/agent-inbox/source-conditions-research.md` `8189817e62058e3ff182392b8151dd00549fb6f6d84debd791316f78cfb20237`; `state/agent-inbox/wb-landing-adversarial-source.md` `9b1c1052044a989b3a970296fffc93eeeb0496202b04908b67c22d96485168bf` | Dated execution record subordinate to MASTER_CONTEXT + program-context; five connectors landed (#2459-#2463) plus polish #2464; capability 29->32; IMF owner-gated with envelope-pin D27 grant pending; FAO/BTS defer-final; the tracked campaign record is the durable publication-normalized copy, while the nine inbox hashes are freeze/merge-time mismatch anchors rather than a claim that raw inbox originals were committed or newly archived; no off-repo archive refresh at landing because replica cadence remains owner-triggered. |
| Connector-breadth IMF grant correction | PR #2466 `d8f7b6df` addendum; D27/D28 arming record `state/agent-inbox/imf-envelope-arming-record.md` | Supersedes the prior connector-breadth row only where it says the IMF D27 grant was pending: the grant was exercised on 2026-07-08, `GET 1/4` returned HTTP 403, zero contingency was spent, no envelope was pinned, no build started, and IMF remains owner-gated/deferred. |
| Connector-program inbox archive | aggregate sha256 `c4dec0d95a613cc20f50324161618ad31acb5b2288a84d6f1045397a5b2bab49`; `ARCHIVE_MANIFEST.json` under `C:/p6store/inbox-archive/2026-07-08-connector-program/` | Point-in-time off-repo archive of the connector-program inbox set after IMF grant exercise and before this PR body cites it; 23 copied source/evidence files / 251,978 bytes. The p6store replica covers this folder only after the owner's next manual re-mirror; archive creation and replica refresh are distinct steps. |
| Connector-program inbox archive correction | Refreshed 2026-07-08 after stage-2 closeout audit: aggregate sha256 `4b1e7b6758ea6442f8b39c3acaa8f2742a236d9758e22fddb4cb6d8df92ced47`; `ARCHIVE_MANIFEST.json` under `C:/p6store/inbox-archive/2026-07-08-connector-program/` | Supersedes only the prior connector-program archive count/aggregate values in the row above: refreshed archive covers 27 copied source/evidence files / 280,012 bytes after adding `source-candidates-adversarial-review-source.md`, refreshed now-bannered `program-sync-source.md`, `closeout-adversarial-source.md`, `closeout-adversarial-report.md`, and `closeout-fixes-source.md`; calibration first matched the prior recorded aggregate `c4dec0d95a613cc20f50324161618ad31acb5b2288a84d6f1045397a5b2bab49`. |

### Merged PR / SHA Table Extension

| PR | Merge SHA | Title / tranche | Verification |
|---|---|---|---|
| #2445 | `2c4f160d` | `Guard operator-built zip determinism` (`tools/sec-xbrl-arelle-provision.py` + `backend/tests/test_sec_xbrl_arelle_provisioning.py`, +166/-6) | CI run 28814395628 green; 1 review thread resolved; detached merged-main proof with targeted slice 16 passed |
| #2446 | `4e9001ee` | `docs: anchor governance record archive` (D29 + I12 + registry archive row, +54) | CI run 28815380142 green; 3 threads resolved; leak scan pass |
| #2447 | `63f7f92d` | `docs: record worktree cleanup execution` (`03-forward-plan.md` only, +49) | PR CI run 28823637387 and post-merge main run 28824285087 green; 0 threads |

### Current Source / Workflow Anchor Extension

| Surface | Verification |
|---|---|
| Operator-built zip determinism guard | `tools/sec-xbrl-arelle-provision.py` defines `verify_zip_determinism`, invoked post-build for `operator_built_archive` specs only; it fails closed with machine-readable reason codes for member order, `date_time`, `create_system`, `compress_type`, and `external_attr`; rejected archives never land at the final taxonomy path because the flow verifies a temp sibling before promotion; asserted by `backend/tests/test_sec_xbrl_arelle_provisioning.py` and landed by PR #2445 (`2c4f160d`). |

## Admission-Spine Contract Anchor (M-ADMISSION-MAP, 2026-07-08)

| Artifact | sha256 anchor | Meaning |
|---|---|---|
| `state/agent-inbox/decision-brief-2026-07-08.txt` | `ec81e1ca25edb4621fe62146a0de1662f79452be457b08fee8356e5cdbf590b9` | Owner authorization for the Phase-1 shared admission-map contract (planning doc 1366) recorded as D32. The brief itself is inbox-local; the committed digest is D32 plus planning doc 1366's authority, non-goals, and Phase 0-7 sequence. |
| PR #2470 | commit `423fbbae5d7bf94d84d596fad1ea23b079e535dc` | Admission-map count and posture reconciliation after #2469; documentation record only, with no runtime, value, schema, persistence, default-on, or support-matrix change by this registry row. |
| PR #2471 | commit `e413d2df7cf0adeda2fd538bc4a3a2f87a5cfcc2` | Neutral NRC APS facade executed with behavior-neutral routing and preserved material-admission semantics. |
| PR #2472 | commit `e31f5ebd5dcc0ae7820252d04cf47db4946d6743` | Connector source-intake envelope: ScienceBase/MCS connector Gate-B next_state closure and four-producer static guard. |

## Admission-Spine B1 Evidence Registry Extension (2026-07-13)

### Live merge chain through the current source frontier

| PR | Merge SHA | Title / tranche |
|---|---|---|
| #2473 | `cdc832d9cbfba5b0485ed0cca0c2a79854605044` | `docs: publish admission spine closure record` |
| #2474 | `2b7973d72e65661acc30c3ec88791fe1c88061e0` | `test(layer3): close Lane A admission guard gaps` |
| #2475 | `4439b1de50d85b2bc72bd92fa8e54717b7e9d500` | `test(layer3): add B1a connector vertical loop proof` |
| #2476 | `56c56e77ebe435c3a9f035f47de2d8611efee7d7` | `test(layer3): allow guarded loopback sockets`; current source frontier |

### Operator-held local evidence anchors

These four files are operator-held local evidence. They are not repository-
carried files, and their names do not imply that their raw payloads are
committed. The tracked record admits only basename, byte count, hash, evidence
role, and the semantic facts copied into D33/D34 and the current-status
surfaces.

| Evidence basename | Bytes | Full SHA-256 | Canonical self-hash | Evidence role |
|---|---:|---|---|---|
| `b1b-ratification-2026-07-13.md` | 10,942 | `CC56D146D2574CE66E80E0B4BF3DC509B5213BDFD8B9310EC06EF99EE4D5298A` | `6B21BC536C49708E72F4B8C15CCE1AE2BEC483C4C659D426F62A8F46CE7AFA9B` | Complete enumeration and precedence ratification receipt; records-only scope |
| `b1b-scope-2026-07-13.md` | 4,304 | `94667BF8B61902F2ABD79CDF531177D55BFC3A30FD3AC8B4158D9024D48F940E` | `CC5E7D62DFE41E407EE180CAEEF95CE29F7D2DBCEDFFF5C8D90C0AFF2A095A4B` | Post-seal clarification that predecessor PR/merge negatives apply to the B1b build lane, not separately authorized records alignment |
| `v2-b1a-run-report.md` | 28,922 | `93BB7D1E606A083B888E55B658BAACBB4C1158AF2C5FDAF021C970936B65FB51` | n/a | Bounded B1a successful-run closure record with historical STOP attempts retained |
| `v2-b1a-cl6-report.md` | 21,009 | `9B875CE36FCA1EAEA6A49B56B0897191394FD596088913644785D8B652548A05` | n/a | CL-6 convergence rerun and exact standing/fix-fence verification |

Provenance qualification: direct current-owner chat is the authority for the
ratifications, and the records writer received the decision through a relayed
instruction. The precise owner timestamp was not provided, the message
identifier was not exposed, and no independent owner artifact was provided.
This registry does not invent or infer any of them.

The B1a evidence is bounded: it is not integrated-loop proof, analytical-
utility proof, Phase 4/5/6 completion, production readiness, or B1b
implementation. The ratification evidence settles target semantics only and
does not authorize implementation, schema, ORM, migration, runtime, build
dispatch, B1b build PR, or B1b build merge.

`B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`

## Stage-1 bounded prekey archive receipt (2026-07-18)

Owner-granted Section 13.1 archive-only act (key grammar-valid, single mark
`GRANTED-ARCHIVE-ONLY`): the exact 15-source bounded snapshot was captured to
the durable root and verified by a dual-read census. This is redundancy
evidence only. It retains `OPEN-I12-ARCHIVE-PENDING` and adds
`BOUNDED-PREKEY-SNAPSHOT-COMPLETE`; it does not close, waive, or supersede I12,
and it authorizes no B1b implementation, schema, ORM, migration, runtime,
build dispatch, build PR, or build merge. The compound Stage-2 second key
remains ungranted at this citation's capture time.

| Field | Value |
|---|---|
| Authorization record | `b1b-i12-archive-authorization-2026-07-13.md` — 895 B; canonical (zero-field rule) `4F1DEEA441FADF4BE76CB3B84BAD37F752F20E0EC3F67DEC6144AB8D963C43E2`; full `E3E4DC7C5D639DF340AFA85A754E7CB70EF5F2D9E4CAEDDA1D2DBFFF42755B5D` |
| Owner act timestamp | `2026-07-18T11:16:34.434418Z` (RFC3339Z, owner-supplied) |
| Destination basename | `20260718T112014493Z-b1b-prekey` |
| Manifest | `ARCHIVE_MANIFEST.json` — 4,604 B; full SHA-256 `cc2aec5985dae721e9c141960088bf6ed66b6e07c52fdfe82b31535e5e9cab6e` |
| Entry aggregate | `34c10823a487100d2dae75b6961b21dac6a118841cd46ae152560cc668146d31` (D33-canonical entry array, sorted by archive-relative path) |
| Source census | `b1b-bounded-prekey-archive.v1` — exactly 15 sources: 14 operator-root files plus the correction read from Git blob `0ec2c9fa93fbdb9d3ac1d456e5d900283882f33a` at `fcf6070d046a9232ec009d55b767a248ad44a4a2` (505,389 B / `FAC9E02B58A5536FC9F77D5E0E86430075059C352F21EA927C132A23012C92A6`) |
| Census result | 15/15 copied, dual-read hash-verified, final second-read census PASS; named-mutex, free-space, no-overwrite, and no-reparse rules observed |

The snapshot is intentionally scoped, not exhaustive (living coordination
files and other lane payloads are excluded by design); it therefore records
`BOUNDED-PREKEY-SNAPSHOT-COMPLETE; I12-OPEN` and is inadmissible for any
`I12-EXHAUSTIVE-ARCHIVE-COMPLETE` selection.
