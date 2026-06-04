# Codex Session Brief — Layer 3 Workbench Track

**Date:** 2026-06-04  
**Branch scope:** Start from a clean worktree off `project6-origin/main` (currently at `a2775067`, PR #2173).  
**Authority file:** `AGENTS.md` governs all work. Read it before starting.  
**This brief:** Provides context, current state, and a prioritized work queue for the Layer 3 workbench track.

---

## Orientation — Read These First

Before doing any work, read the following in order:

1. `AGENTS.md` (harness rules, editing constraints, validation protocol)
2. `docs/agent-harness.md` (short command-oriented execution map)
3. `next_milestone_plans/layer3_progress_board.md` (current workbench milestone status)
4. `next_milestone_plans/Layer3_planning_docs/929_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE_CURRENT_MAIN_SYNC.md` (the last confirmed current-main sync)
5. `next_milestone_plans/Layer3_planning_docs/928_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE.md` (the gap freeze that 929 synced)

---

## Current State (verified against git log and planning docs, 2026-06-04)

### Layer 3 Track Last Confirmed Position

- **Doc 929** (`929_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE_CURRENT_MAIN_SYNC.md`) merged as PR #1544.
- Merge commit: `a7ec760f387e9b790146354ac874aab1fb01e225`
- Merge date: before 2026-06-02 (confirmed in planning doc)

### SEC XBRL Work That Followed (out of scope for this session)

After PR #1544, the Codex sessions spent May 31–June 3 on SEC XBRL consolidation (PRs #2128–#2173). That work is tracked separately in docs 1344–1349 and is owned by the SEC XBRL session. **Do not touch those files.**

### Current Exact Next Posture (from doc 929)

> `select_source_directory_package_supersession_commit_route_state_contract_after_gap_freeze_sync`

This means: write a new planning doc (doc 930) that selects the exact route/state contract
for resolving the source-directory package supersession commit mismatch identified in the
gap freeze.

### What the Gap Freeze Found (from doc 928/929)

The existing route `POST /api/v1/layer3/package/supersession/commit` uses:
- `backend/app/services/layer3_package_supersession_commit.py`
- `backend/app/services/layer3_source_directory_qualitative_analysis.py` (for preview)
- `backend/app/services/layer3_replacement_package_set_authority.py` (replacement authority)

The gap: the source-directory preview/replacement authority hash bases are not compatible
with the existing generic package supersession commit route contract. The blocked target
remains `/review/layer3 #package-supersession-commit-panel`.

---

## Prioritized Work Queue

### 1. Write contract-selection doc (doc 930) — IMMEDIATE

**Goal:** Write `next_milestone_plans/Layer3_planning_docs/930_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_CONTRACT_SELECTION.md`.

This doc selects the exact route/state contract that resolves the gap identified in doc 928.

**What to include in doc 930:**
- The exact route surface: `POST /api/v1/layer3/package/supersession/commit`
- The exact hash-compatibility fix: how source-directory preview hashes will be compatible with the commit contract
- The exact state transitions admitted: what happens after a successful commit
- The exact non-admission list: no new routes, no model/migration changes, no RAG/provider/connector widening
- A capability isolation matrix (same format as doc 199)
- Stop conditions

**Before writing:** Read these files to understand the gap:
- `backend/app/services/layer3_package_supersession_commit.py` (current commit service)
- `backend/app/services/layer3_replacement_package_set_authority.py` (replacement authority)
- `backend/app/services/layer3_source_directory_qualitative_analysis.py` (preview service)
- `backend/tests/test_layer3_package_supersession_commit.py` (if it exists)

**Verification for this PR (docs only, no code):**
```powershell
python tools/l3-progress-check.py
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > $null
git diff --check
```

### 2. Implement the route/state contract fix (doc 931) — after doc 930 merges

**Goal:** Write the implementation freeze doc (931) and implement the hash-compatibility fix.

This is a bounded backend fix: modify `layer3_package_supersession_commit.py` to accept
source-directory preview hashes using the contract defined in doc 930.

**Constraints:**
- Backend-only: no UI changes yet
- No new routes
- No model/migration changes
- Full backend test suite must pass

### 3. Implement the rendered commit control UI (doc 932) — after doc 931 merges

**Goal:** Write the rendered UI doc (932) and implement `/review/layer3 #package-supersession-commit-panel`.

This completes the source-directory package supersession commit UI chain started in doc 918/919.

**Constraints:**
- `layer3.js` only (no new HTML elements if avoidable)
- Requires headed AND headless Chromium proof via Playwright
- No full mockup activation
- No frontend-only durable authority

### 4. Select next full mockup blocker (after rendered commit merges)

**Goal:** Write the next gap-selection or blocker-selection doc.

Reference: `next_milestone_plans/Layer3_planning_docs/917_FULL_MOCKUP_ACTIVATION_NEXT_BLOCKER_SELECTION.md` — read this to understand the full mockup program's remaining blockers.

---

## Progress Manifest Refresh

**Note:** The progress manifest (`next_milestone_plans/layer3_progress_manifest.json`) has
`snapshot_date: 2026-05-06` which predates doc 929 (merged before June 2). The manifest
needs updating to include docs 867–929 history.

**How to update:**
- Read the planning docs from 868 to 929 in order
- Add notes entries for each merged doc (pattern: match existing notes style)
- Update `snapshot_date` to `2026-06-04`
- Update `snapshot_base_main_commit` to `a2775067`
- Run `python tools/l3-progress-check.py` after

**This is optional for the first PR** — do it as a separate clean PR after doc 930 merges.

---

## Auth/Security Note

Doc 200 (`200_AUTH_SECURITY_ENTRY_CONTRACT.md`) currently has `entry_decision: deferred` and
`selected_mode: null`. A Claude sprint doc has been added:
`next_milestone_plans/Layer3_planning_docs/200_AUTH_SECURITY_ENTRY_CONTRACT.md` (read the
stop conditions there before making any auth decisions).

**Do not implement auth until the mode selection is explicitly authorized in a follow-up freeze.**

---

## What Is EXPLICITLY OUT OF SCOPE for this session

- SEC XBRL services (`backend/app/services/layer3_sec_xbrl_*.py`) — owned by SEC XBRL session
- `backend/tests/test_sec_xbrl*.py` — owned by SEC XBRL session
- `diagnostics/assessment/sec_xbrl_*.py`
- `next_milestone_plans/Layer3_planning_docs/1344-*.md` through `1350-*.md`
- Auth/security implementation (zero auth infrastructure; see doc 200)
- Full mockup program activation (blocked by doc 917 remaining items)
- Provider/public URL runtime
- Connector/destination dispatch runtime
- Qualitative/hybrid/RAG execution (beyond already-admitted)
- Source breadth expansion beyond recursive server-configured ingestion

---

## File Ownership — Avoid Collisions with SEC XBRL Session

This session owns:
- `backend/app/review_ui/static/layer3.js`, `layer3.html`, `layer3.css`
- `backend/app/services/layer3_workbench.py` and workbench services (non-SEC XBRL)
- `backend/app/services/layer3_package_supersession_commit.py`
- `backend/app/services/layer3_replacement_package_set_authority.py`
- `backend/app/api/layer3.py`
- `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/Layer3_planning_docs/930_*.md` and beyond

**Do NOT touch:**
- `backend/app/services/layer3_sec_xbrl_*.py`
- `backend/tests/test_sec_xbrl*.py`
- `diagnostics/assessment/sec_xbrl_*.py`
- `next_milestone_plans/Layer3_planning_docs/1344-*.md` through `1350-*.md`
- `next_milestone_plans/layer3_progress_board.md` (for SEC XBRL entries — those are owned by the SEC XBRL session)

---

## Verification Commands (run after each PR)

```powershell
# Backend Layer 3 tests
python -m pytest backend/tests/test_layer3*.py -q

# Playwright headed+headless (for UI PRs)
npx playwright test --project=chromium e2e/layer3-workbench.spec.js --headed
npx playwright test --project=chromium e2e/layer3-workbench.spec.js

# Progress check
python tools/l3-progress-check.py

# JSON validity
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > $null
python -m json.tool next_milestone_plans/layer3_workbench_proof_manifest.json > $null

# Clean diff
git diff --check
```

---

## Reference

- Last synced doc: `next_milestone_plans/Layer3_planning_docs/929_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE_CURRENT_MAIN_SYNC.md`
- Gap freeze: `next_milestone_plans/Layer3_planning_docs/928_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ROUTE_STATE_GAP_FREEZE.md`
- Full mockup blockers: `next_milestone_plans/Layer3_planning_docs/917_FULL_MOCKUP_ACTIVATION_NEXT_BLOCKER_SELECTION.md`
- Progress manifest: `next_milestone_plans/layer3_progress_manifest.json`
- Auth scoping: `next_milestone_plans/Layer3_planning_docs/200_AUTH_SECURITY_ENTRY_CONTRACT.md`
- AGENTS.md (canonical harness entry)
- Agent harness: `docs/agent-harness.md`
