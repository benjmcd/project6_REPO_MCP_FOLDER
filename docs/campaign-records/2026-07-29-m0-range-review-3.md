# M0 range review 3 — external Codex 019faa86, range 356eff2e..c8b367a6

Date: 2026-07-29/30. VERDICT: DO-NOT-FREEZE, narrowed — seam disclosure truthful, headroom arithmetic
viable (worst-case 6,684,672 B derived), but (1) the headroom guard is not bound into the executable
reservation step 6 / evaluator, and (2) NEW: campaign promises two connector-run seal events even in an
NRC-first failure state where the ScienceBase run must not exist.
source-sha256: 4ecd5cbe03f6c9339e51a6fd381bb79f1232749f500202fc9acfad37f4ea93d0

---

# Focused accounting-delta re-review — dual-live M0 `356eff2e..c8b367a6`

Codex session: `019faa86-8d5f-7a20-b107-bb71437f438e`

## Verdict

**DO-NOT-FREEZE**

The correction has fixed the original seam-description defect: the documents now truthfully say that `http.client` parses the complete status/header block before the Requests adapter can inspect it, that the 32 KiB canonical-header rule is post-parse rejection, and that rejected canonical header bytes remain counted and spent.

The proposed headroom idea is also arithmetically viable. It is not, however, bound into the executable reservation algorithm or evaluator. A second, independent failure-closeout contradiction also remains: the campaign promises two connector-run seal events even in an NRC-first failure state where the ScienceBase run is required not to exist.

Those are mechanism defects, not editorial polish. `FREEZE-WITH-CONDITIONS` is therefore insufficient.

## Scope and identity

- **REPO-CONFIRMED:** reviewed worktree is `C:/Users/<operator>/OneDrive/Desktop/project6_REPO_MCP_FOLDER/worktrees/dual-live-plan`, branch `codex/dual-live-plan`, clean HEAD `c8b367a63099a823167984cae43fa01dc6f077be`.
- **REPO-CONFIRMED:** local `refs/remotes/project6-origin/main` is the stipulated `c1fcd840b421ceafb560266858a75808207f4540`. No fetch or other Git-state mutation was performed; the unrelated `origin` remote was not used.
- **REPO-CONFIRMED:** `356eff2e..c8b367a6` is a six-commit linear range:
  `78eb3146`, `3ed5589`, `a0cefbd6`, `1bfce554`, `468252c5`, `c8b367a6`.
- **REPO-CONFIRMED:** `468252c5` changes only the plan and campaign record. `c8b367a6` adds only review record 2.
- **REPO-CONFIRMED:** the complete range changes only:
  - `docs/superpowers/plans/2026-07-29-dual-live-proof.md`;
  - `docs/campaign-records/2026-07-29-dual-live-proof.md`;
  - `docs/campaign-records/2026-07-29-m0-range-review-1.md`;
  - `docs/campaign-records/2026-07-29-m0-range-review-2.md`.
- **REPO-CONFIRMED:** `git diff --check 356eff2e..c8b367a6` passes.
- **REPO-CONFIRMED:** final reviewed identities:
  - plan: 150,460 bytes, 2,989 lines, SHA-256 `a6616ed8a3ac3429fdb2f80d19eb645066f48009c8b51f74ad953e6639353ffc`, Git blob `46875c52dad5bf426918ccaefd6d3fb6ae1df953`;
  - campaign: 70,607 bytes, 1,150 lines, SHA-256 `6f9569c4d5eb4b6016b3aacaa8e962afaf03e7d0147b5414da31bf81e77d9ec0`, Git blob `04eb02eacb19e1aad154a907ff75d9a8beb389b1`;
  - review 2: 14,076 bytes, 107 lines, SHA-256 `96cd7ccd82a74b0e564b31b57c7f07e0fe2386f049999cf713982313f75d47fc`, Git blob `fb9d663d5a85b40eccdcf67a6c3b58cf3cc481f2`.
- **UNVERIFIED:** proposed runtime behavior and tests. The audit ran no Python, Node, pytest, Alembic, or npm command.

## Y1 — header-bound defect and headroom arithmetic

**PARTIAL PASS; overall X2 remains FAIL.**

### What is now correct

- **REPO-CONFIRMED:** plan lines 1397–1406 and campaign lines 655–671 correctly disclose the post-parse seam and count/spend rejected canonical header bytes.
- **HOST-SOURCE-CONFIRMED:** current Requests calls `conn.urlopen(...)` before response construction (`requests/adapters.py` 644–696); urllib3 calls `http.client.getresponse()` and only afterward builds `HTTPHeaderDict` from the parsed message (`urllib3/connection.py` 570–600).
- **HOST-SOURCE-CONFIRMED:** current `http.client` has `_MAXLINE = 65536`, `_MAXHEADERS = 100`, reads the status line separately with the same line limit, reads the complete header list before parsing, and decodes those bytes as ISO-8859-1 (`http/client.py` 111–112, 213–243, 285–288).
- **DERIVED:** the plan’s conservative stated formula is:
  - parsed header allowance including status line:
    `(100 × 65,536) + 65,536 = 6,619,136` bytes;
  - plus one 65,536-byte body chunk:
    `6,684,672` bytes = `6.375 MiB`.

Conditional on an exact canonical-header upper bound `Hmax`, a pre-reservation requirement `R >= Hmax + 65,536`, and immediate no-body termination when canonical headers exceed 32,768 bytes, the idea works:

1. a rejected large header cannot cross the aggregate ceiling because the remaining budget already covers `Hmax` plus a chunk;
2. any ceiling crossing after an admitted header has `H <= 32,768`, so the tighter crossing bound is at most `32,768 + 65,536 = 98,304` bytes.

Thus the lower parser seam does not need to prevent receipt for this application-counted metric. The correction’s conceptual direction is sound.

### Blocking defect B1 — the declared guard is not in the normative mechanism

- **REPO-CONFIRMED:** the new test prose at plan lines 1171–1180 says a send is admitted only when remaining budget is at least the worst-case allowance, and a smaller remainder stops before reservation.
- **REPO-CONFIRMED:** the actual reservation algorithm at plan lines 1261–1267 still stops only when the remainder is zero or negative (or prior spent bytes are unresolved), then sets the effective streaming cap to `min(stage cap, remainder)`. It contains no `remainder >= allowance` predicate.
- **REPO-CONFIRMED:** campaign reservation steps 1–8 at lines 590–615 likewise contain no headroom predicate. They proceed from `min(stage cap, remaining budget)` to reservation and send.
- **REPO-CONFIRMED:** the evaluator at plan lines 2380–2394 rederives only the final aggregate/crossing disposition. It does not reconstruct and require the headroom predicate for each reservation.

This admits a concrete false-pass path. If an earlier ScienceBase redirect response leaves a positive remainder smaller than the allowance, the normative step 6 permits the optional redirect reservation. If that final response is small and the aggregate remains below `max_run_bytes`, the current evaluator has no predicate that detects the forbidden low-headroom admission. The campaign can therefore be called `fresh_live` even though the newly promised pre-send guard never ran.

The stage/aggregate arithmetic also needs one explicit rule. Headers count against the run aggregate but not the per-stage body cap. A single recorded cap `min(stage cap, R)` cannot express both constraints unless the implementation either:

- debits canonical header bytes after parsing and computes `body_budget = min(stage_body_cap, R - H)`; or
- retains stage and aggregate limits separately and checks `body_bytes <= stage_body_cap` plus `H + body_bytes <= R` at every chunk.

The documents currently specify neither operation.

Finally, the parser-derived allowance is not yet an exact bound on the counted canonical bytes. The documents do not name a canonical serializer, encoding, normalization rule, or frozen integer constant. Current `http.client` converts header octets to ISO-8859-1 strings; a conforming implementation that re-encodes those strings as UTF-8 can expand `obs-text`, making the raw parser-line formula too small. Python is described as `3.11+`, but no fail-closed assertion pins the private parser limits. An arithmetic authority guard needs these choices closed, not inferred.

### Required B1 closure

1. Define one named canonical status/header serializer, including encoding, duplicate/order/folding treatment, and an exact conservative `COUNTED_HEADER_ALLOWANCE_BYTES`.
2. Pin or fail closed on the `http.client` parser limits on which that allowance depends.
3. Add `R < allowance => budget_exhaustion, no reservation` to plan Task 3 Step 3 and campaign section 7, before the reservation event.
4. Debit `H` from the aggregate body remainder or retain independent body-stage and aggregate counters.
5. Make the evaluator rederive the headroom predicate for every ordinal, not merely the final aggregate.
6. Align terminology: the ~6.375 MiB value is reservation headroom; under the guard and immediate >32 KiB header rejection, the actual admitted-header crossing bound can remain the evaluator’s tighter 96 KiB. State that derivation explicitly.
7. Add adversarial cases for `R = allowance - 1`, `R = allowance`, many legal headers, non-ASCII `obs-text`, a stage cap smaller than aggregate remainder, exact-EOF at the aggregate boundary, and the optional ScienceBase redirect after a large prior response.

## Y2 — conflicts with stage caps, exhaustion, and evaluator

- **Stage caps:** no inherent design conflict, provided body-stage and aggregate-header/body accounting are kept as two explicit quantities. The current single-cap wording is insufficient.
- **Reservation Step 6:** direct conflict. It admits every positive resolved remainder, while the new guard promises to reject all remainders below the allowance.
- **Budget exhaustion:** direct conflict for the same reason; the test/narrative and executable algorithm define different exhaustion thresholds.
- **Evaluator:** the retained 32 KiB + 64 KiB bound is not inherently stale. With the guard actually enforced and >32 KiB headers terminating before body reads, 96 KiB is a valid tighter upper bound. The defect is that the evaluator does not rederive the guard, and the documents call two different quantities the “stated allowance/detection bound” without explaining their relationship.

## Y3/Y5 — complete-document guarantee hunt and fresh eyes

### Blocking defect B2 — impossible two-run seal closeout after NRC-first failure

- **REPO-CONFIRMED:** `ConnectorCampaignLogSealV1.connector_run_ids` is fixed as `tuple[str, str]` at plan line 397.
- **REPO-CONFIRMED:** plan lines 621–647 and 2481–2489, plus campaign lines 458–480, require the wrapper to append one matching deterministic seal event to each of both connector runs.
- **REPO-CONFIRMED:** plan execution step 10 says this happens “in success or failure” (lines 2803–2806).
- **REPO-CONFIRMED:** NRC failure/safe-stop/indeterminate handling requires that the ScienceBase parent arming and run/submission/policy rows do not exist (plan lines 2862–2867; campaign lines 942–970).
- **REPO-CONFIRMED:** the current `ConnectorRunEvent.connector_run_id` is non-null and foreign-keyed to `connector_run` (`backend/app/models/models.py` 599–616).

On an NRC-first stop there is therefore no ScienceBase run to receive the second seal event. Creating one would violate the predecessor isolation and absence proof; omitting its event violates the fixed two-run seal/evaluator contract. The stated “success or failure” closeout has no valid state transition.

Required closure: make seal/event cardinality phase-aware (zero, one, or two extant runs), while keeping two matching events mandatory for a passing campaign; or add a real campaign-level anchor. A failed NRC closeout should bind the filesystem seal to the NRC run if it exists and separately prove the absent ScienceBase marker/run. It must not create a dummy ScienceBase run.

### No other new blocker found

- X1 remains **PASS at design level**: the single authoritative NRC predecessor predicate and pre-marker mutation ordering remain intact.
- X3 remains **PASS at design level; runtime UNVERIFIED**.
- Default-off, no-authority, no-egress-through-M10, owner-gated M11, validate-only/fail-closed, and separate M9 promotion posture remain intact.
- Plan and campaign remain materially aligned apart from the defects above.

## Y4 — re-adjudication of review-2 clarifications

These remain nonblocking M0 hardening items, but should be fixed before their owning implementation tasks:

1. Make the 10,000-row parser limit explicitly document-global; the named helper is currently called once per page.
2. Specify `ru_maxrss` platform-unit conversion.
3. Require lazy application imports so network/subprocess guards are installed first.
4. Reword the zero-byte scratch check as residual post-parse occupancy, or instrument peak temp I/O if zero peak usage is intended.
5. Give the request fingerprint a named canonical helper/schema with exact URL, header ordering/duplicate, encoding, and absent-body rules.
6. Replace “at most one campaign process” with “network-inert wrapper plus at most one application/runtime child.”
7. State strict-envelope detection before the current generic lease/status mutation.
8. Specify the actual successor/head-advance operation before Task 11, or describe unused-grant retirement as later successor/expiry rather than immediate campaign-close advancement.
9. Change plan line 1189’s “raw response headers” wording to “canonical parsed status/header bytes.”

**No G0–G4 mapping defect exists in the documents.** A mechanical scan found zero literal `G0`–`G4` names and fourteen `M0`–`M9` references. The campaign’s canonical milestone vocabulary is M0–M9; the G labels were dispatch vocabulary, so no in-document mapping is required.

## Decision debate

**Freeze case:** the correction now tells the truth about the Requests/http.client seam, uses a defensible application-visible currency, keeps all rejected bytes spent, and proposes a conservative pre-send allowance. With the missing predicates inserted, no lower-level parser replacement is necessary for M0.

**Hold case:** a frozen executable plan cannot place the new authority guard only in a test bullet and narrative while its normative reservation transaction and evaluator omit it. Nor can it promise two run-bound closeout events in a failure state that deliberately has one run.

**Consensus:** **DO-NOT-FREEZE**, narrowly. Close B1 and B2, retain the successful seam disclosure and X1/X3 work, apply the listed hardening items in their owning tasks, then perform one final bounded delta review.

This verdict is advisory and non-authorizing. It grants no implementation, egress, acceptance, landing, PR, merge, repeatability, or production-promotion authority. The repository/worktree remained read-only and clean; no prohibited runtime/test command, subagent, further IPC action, Git write/fetch, protected correction-blob access, or agent-inbox access occurred.

Goal usage: 206,401 tokens over 13m 51s.
