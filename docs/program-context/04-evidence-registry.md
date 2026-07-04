# 04 — Evidence Registry

Every load-bearing anchor. A claim elsewhere in this set that cites one of these is
re-derivable from the anchor alone. Dates 2026. "Inbox" = `state/agent-inbox/for-claude.md`
report markers (operator-lane coordination ledger, tracked in the root checkout).

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

## Real-data proof artifacts (operator-local; verified independently by two blind auditors)

| Artifact | Anchor | Meaning |
|---|---|---|
| Reveal proof report | sha256 `790fbb8eaa7de4be447f6c401089cb3b6435ff86614f4f0f57e656fc287a39d8` | CK1-3 outcome record (report file in operator sandbox reports dir) |
| Revealed facts | 523 total / 497 non-empty | CK3 controlled-submit response (real STLD 10-Q values) |
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

## Inbox report markers (coordination ledger, chronological)

M-ADVERSARIAL-REVIEW-AUDIT (~2002) · M-A8-PRECLEARANCE-PROGRAM PHASE 1-5 + CLOSEOUT
(~2102-2295) · M-A8-RUNTIME-GO REPORT 1-3 (~2432, ~2556, ~2655) · M-OPS-UTILIZATION-READY
REPORT 1-4 + CLOSEOUT + 2b (~2299-2605) · M-A8-RECORD-TRUTH (~2709) · M-ADV-STATE-AUDIT-A2/A1
(~2770/~2871) · M-A8-RECORD-TRUTH-2 (~2997) · M-FWD-OPTIONS-2 (~3048) · M-O6-HARDENING-DOCS
(~3223) · M-FWD3-CRITERIA (~3247) · M-FWD3-EVIDENCE (~3388) · M-A8-RECORD-TRUTH-3 (~3554) ·
M-P3-DURABLE-ROOT-REPO (~3607). Line numbers are as-of this set's authoring; grep markers,
don't trust offsets.

## Counts worth remembering

- 15 PRs merged in the campaign (#2409-#2423), zero cross-lane collisions, every bot review
  thread resolved pre-merge.
- M-FWD3-EVIDENCE recorded 347 git worktrees and 11 mechanically-safe cleanup candidates;
  inventory sha `6bcb7fe11ab6410155d175682c43791af3b2b84cdff903c15632b6f27418788a`.
  Refresh live counts before any cleanup lane because later worktrees change the total.
- Nonlocal production-readiness gate: 6 of 7 criteria pass; sole blocked criterion
  `final_nonlocal_production_admission_present`, with blocked reason
  `nonlocal_production_readiness_final_admission_missing`.
- RC3 acceptance list: declared=58, tracked=58, drift-guarded.
