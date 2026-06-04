# SEC XBRL Track — Session Brief (2026-06-04)

Start from a clean worktree off `origin/main`. Read `AGENTS.md` first.
Note: on this machine the remote is `origin`, not `project6-origin`. Use `git fetch origin main --prune`.

---

## Current State (verified against git log, 2026-06-04)

### Consolidation Series Complete

PRs #2120–#2174 are all merged. Current main is `fa205665` (sprint planning docs + manifest refresh, 2026-06-04). The shared modules are in place: diagnostic framework, public authority guard (persistence/value-reveal/auth-binding families — PRs #2120/#2121/#2122), report leak guard, canonical concepts, redaction helpers, package-family policy, mixed-source contract, unadmitted-key adapter, resolved-fact redaction wrappers.

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

### Branch-Local Items (Actual Queue as of 2026-06-04)

**Guard branches 1346/1347/1348 are already merged** (PRs #2120, #2121, #2122). Do not attempt to re-merge them.

**Also already merged** (0 commits ahead of main): `codex/secxbrl-review-debt`, `codex/secxbrl-residual-review-closeout`.

Current unmerged work — merge in this priority order:

**Tier A — Review-debt** (merge in sequence — these branches share `sec-xbrl-nonlocal-admission-disposition.py` and wrong order causes conflicts):

| Branch | Content |
|--------|---------|
| `codex/secxbrl-2082-review-closeout` | PR #2082 readiness gate threads |
| `codex/secxbrl-2083-review-closeout` | PR #2083 admission disposition threads |
| `codex/secxbrl-2086-ref-redaction-fix` | Admission disposition ref redaction fix (same file as 2083 — merge after) |
| `codex/secxbrl-late-review-ledger-closeout` | Late ledger threads + both diagnostic files + manifests |
| `codex/secxbrl-review-thread-closeout` | Authority gap closeout |

**Tier B — Hardening + UI** (rebase check against current main before PR):

| Branch | Content |
|--------|---------|
| `codex/secxbrl-2039-review-fix` | Migration 0043 downgrade safety guard + `layer3.js` SEC XBRL review-decision UI additions + tests |

**Tier C — Complex rebase required** (~130 commits behind current main):

| Branch | Notes |
|--------|-------|
| `codex/secxbrl-offline-gate` | Sector family offline gate hardening; rebase required before PR; progress board and manifests in branch are stale relative to PRs #2120–#2174 |

Then continue with deeper items in order from the progress board (verify each with `git log origin/main..origin/<branch> --oneline` to confirm they're not already merged before creating a PR).

---

## Prioritized Work Queue

### 1. Merge review-debt branches (IMMEDIATE — in exact order to avoid conflicts)

For each Tier A branch in sequence (2082 → 2083 → 2086 → late-review-ledger → review-thread-closeout):

```
git fetch origin <branch>
# Confirm not already merged:
git log origin/main..origin/<branch> --oneline
git checkout -b local-verify origin/<branch>
python -m pytest backend/tests/test_sec_xbrl*.py -q
python tools/l3-progress-check.py
git diff --check
gh pr create --title "..." --base main --head <branch>
```

After each merge, rebase the next branch on the new main before verifying.

**Tier B**: After Tier A is clear, check out `codex/secxbrl-2039-review-fix`, verify rebase against current main, then run the full SEC XBRL suite plus `npx playwright test --project=chromium e2e/layer3-workbench.spec.js` (branch contains bounded `layer3.js` SEC XBRL review-decision UI additions).

**Tier C**: After Tier B, rebase `codex/secxbrl-offline-gate` against current main (progress board and manifest in the branch are stale; resolve conflicts carefully). Then verify and PR.

### 2. Continue with deeper branch-local items

After Tier A/B/C merge, work through remaining branch-local items in order from the progress board. For each:
1. Confirm not already merged: `git log origin/main..origin/<branch> --oneline`
2. Check out and run the verification commands from the progress board entry
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
- `backend/app/review_ui/static/layer3.js` or `.html` — **exception**: `codex/secxbrl-2039-review-fix` contains bounded SEC XBRL review-decision UI additions to `layer3.js`; land that branch before the Layer 3 session begins new UI work
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
