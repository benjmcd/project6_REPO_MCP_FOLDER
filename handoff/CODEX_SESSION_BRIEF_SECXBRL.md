# SEC XBRL Track — Session Brief (2026-06-04)

Start from a clean worktree off `origin/main`. Read `AGENTS.md` first.
Note: on this machine the remote is `origin`, not `project6-origin`. Use `git fetch origin main --prune`.

**Wait for PR #2174 (`claude/sprint-20260604`) to merge before starting.** It updates the progress board (marks PRs #2172/#2173 as merged) and adds doc 1350 (activation lane selection).

---

## Current State (verified against git log, 2026-06-04)

### Consolidation Series Complete

PRs #2128–#2173 (docs 1344–1349) are all merged. Current main is `a2775067` (PR #2173 merge). The shared modules are in place: diagnostic framework, public authority guard, report leak guard, canonical concepts, redaction helpers, package-family policy, mixed-source contract, unadmitted-key adapter, resolved-fact redaction wrappers.

**Test state (last verified):** `477 passed, 3 warnings` on the full SEC XBRL suite.

### Activation Lane (Doc 1350)

After PR #2174 merges, doc `1350-sec-xbrl-activation-lane-selection.md` is on main with:
```yaml
entry_decision: deferred_pending_auth_framework
selected_activation_mode: null
runtime_status: not_implemented
```

**Do NOT activate any of the six activation surfaces** (default-on runtime, value-reveal, controlled-submit, E2E integration, multi-filing gate, in-app auth policy) until:
- Auth framework mode is selected (doc 200 `selected_mode` is still null)
- Operator acceptance criteria are defined
- Each activation surface has its own separate freeze/contract/proof

### Branch-Local Items (Priority Merge Queue)

The following guard consolidation branches are on the remote, verified but unmerged. Merge in this order (each depends on the prior):

| Doc | Branch | Milestone |
|-----|--------|-----------|
| 1346 | `codex/secxbrl-authority-guard` | `sec_xbrl_public_authority_guard_persistence_family_v1` |
| 1347 | `codex/secxbrl-authority-guard-tranche2` | `sec_xbrl_public_authority_guard_value_reveal_family_v1` |
| 1348 | `codex/secxbrl-auth-binding-guard` | `sec_xbrl_public_authority_guard_auth_binding_family_v1` |

Then continue with the deeper items (in order from the progress board):

| Branch | Milestone |
|--------|-----------|
| `codex/secxbrl-review-debt` | `sec_xbrl_transaction_safe_operator_review_persistence_v1_review_debt_closeout` |
| `codex/secxbrl-e2e-offline-orchestrator` | `sec_xbrl_e2e_offline_evidence_orchestrator_v1` |
| `codex/secxbrl-e2e-integration-design` | E2E contract adapter + design |
| `codex/secxbrl-packet-dir-intake` | Nonlocal admission/backfill disposition |
| `codex/secxbrl-residual-review-closeout` | Residual review-thread closeout #2070/#2074 |

---

## Prioritized Work Queue

### 1. Merge guard consolidation branches (IMMEDIATE)

For each branch (1346 → 1347 → 1348 in order):

```
# Check out branch and verify
git fetch origin codex/secxbrl-authority-guard
git checkout -b local-verify origin/codex/secxbrl-authority-guard

# Run verification
python -m pytest backend/tests/test_sec_xbrl*.py -q
python tools/l3-progress-check.py
git diff --check

# If clean: create PR and merge
gh pr create --title "..." --base main --head codex/secxbrl-authority-guard
```

After persistence-family merges, rebase or re-verify value-reveal and auth-binding branches on the new main before merging them.

**Tier classification**: per doc 1346/1347/1348. All three are Tier-1 behavior-preserving consolidations — verify + CI pass is sufficient; independent review not required unless a concrete risk trigger appears.

### 2. Continue with deeper branch-local items

After the three guard branches merge, work through the remaining branch-local items in the order shown in the progress board (top = newest, merge in reverse order = oldest first). For each:
1. Check out the branch
2. Run the verification commands listed in the progress board entry for that milestone
3. If clean: create PR, let CI run, merge
4. Update `next_milestone_plans/layer3_progress_board.md` status to reflect the merge

### 3. New work after branch-local queue clears

Only after branch-local queue is clear: check `1336-transaction-safe-review.md` for the next design gate, then write the next implementation doc. The activation lane (doc 1350) stays deferred until auth framework is unblocked.

---

## What Is EXPLICITLY OUT OF SCOPE for this session

- Auth/security framework implementation (see doc 200 `selected_mode: null`)
- Default-on runtime activation
- Value-reveal behavior changes
- Controlled-submit behavior changes
- E2E integration route activation
- Multi-filing evidence authority gate activation
- In-app auth policy activation
- Frontend/UI changes
- Alembic migrations
- Source acquisition (no live Arelle invocation, no live SEC network calls)
- Layer 3 workbench services (`layer3_workbench.py`, `layer3_sec_edgar_*.py`) — owned by Layer 3 session

---

## File Ownership — Avoid Collisions with Layer 3 Session

This session owns:
- `backend/app/services/layer3_sec_xbrl_*.py`
- `backend/tests/test_sec_xbrl*.py`
- `diagnostics/assessment/sec_xbrl_*.py`
- `next_milestone_plans/Layer3_planning_docs/1349-*.md`, `1350-*.md`, and future SEC XBRL docs

**Do NOT touch:**
- `backend/app/services/layer3_workbench.py` or Layer 3 workbench services
- `backend/app/services/layer3_sec_edgar_*.py`
- `backend/app/review_ui/static/layer3.js` or `.html`
- `backend/app/api/layer3.py`
- `next_milestone_plans/Layer3_planning_docs/199_*.md`, `200_*.md`
- `next_milestone_plans/layer3_progress_manifest.json` (owned by Layer 3 session)

---

## Verification Commands (run after each PR)

```
# Full SEC XBRL suite
python -m pytest backend/tests/test_sec_xbrl*.py -q

# Progress check
python tools/l3-progress-check.py

# JSON validity
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > /dev/null
python -m json.tool next_milestone_plans/layer3_workbench_proof_manifest.json > /dev/null

# Clean diff
git diff --check
```
