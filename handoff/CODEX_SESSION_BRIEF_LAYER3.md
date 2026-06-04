# Layer 3 Workbench Track — Session Brief (2026-06-04)

Start from a clean worktree off `origin/main`. Read `AGENTS.md` first.
Note: on this machine the remote is `origin`, not `project6-origin`. Use `git fetch origin main --prune`.

---

## Orientation — Read These First

1. `AGENTS.md` (harness rules, editing constraints, validation protocol)
2. `docs/agent-harness.md` (command-oriented execution map)
3. `next_milestone_plans/layer3_progress_board.md` (current milestone status — read `Layer 3 Workbench Current Decision` and `Current Focus` sections first)
4. `next_milestone_plans/Layer3_planning_docs/1252-sec-edgar-period-unit-context-dimension-rendered-detail-ui.md` (last Layer 3 workbench planning doc on main)
5. `next_milestone_plans/Layer3_planning_docs/1251-sec-edgar-durable-delivery-archive-status-rendered-ui.md` (prior doc for context)

---

## Current State (verified against git log and planning docs, 2026-06-04)

### Layer 3 Track Last Confirmed Planning Position

- **Doc 1252** (`1252-sec-edgar-period-unit-context-dimension-rendered-detail-ui.md`) is the last Layer 3 workbench planning doc on main.
- `entry_main_commit: dfb150c54cc9c5c4c796e450c24bee8ab8624eae` (current main is `fa205665` — sprint planning commit 2026-06-04, after PRs #2174/#2175)
- `runtime_status: implemented_branch_local` — the implementation is on a remote branch, not yet merged.
- **Next exact posture**: `sec_edgar_statement_role_quality_profile_rendered_detail_ui_v1`

### Unmerged Implementation Branches

There are 43 `codex/sec-edgar-*` branches on the remote. Before writing new planning docs, check which of these have unmerged implementation work that should be PR'd and merged. Key examples visible in the remote:
- `codex/sec-edgar-html-ixbrl-*` series (parser, material bridge, operator status, rendered status, downstream proof)
- `codex/sec-edgar-downstream-*` series
- `codex/l3-sec-edgar-p9`
- `codex/sec-edgar-live-closeout-readiness`
- `codex/sec-edgar-current-main-sync`

**First action:** Run `git ls-remote origin 'refs/heads/codex/sec-edgar*'` to list these branches, then check the progress board and each branch's tip commit against current main to identify which are ready to merge.

### Doc Numbering

PR #2174 (`claude/sprint-20260604`) is merged. Doc `1350-sec-xbrl-activation-lane-selection.md` is confirmed on main. The next available Layer 3 planning doc number is **1351**.

---

## Prioritized Work Queue

### 1. Verify and merge ready sec-edgar implementation branches (IMMEDIATE)

**Goal:** Bring branch-local sec-edgar implementations to current main before starting new work.

For each unmerged `codex/sec-edgar-*` branch:
1. Check if it has an open PR (`gh pr list --head codex/sec-edgar-<name>`)
2. If no PR, fetch the branch and compare to current main (`git log origin/sec-edgar-<name>..origin/main --oneline`)
3. If the branch has new commits relative to main: run the branch's verification commands, create a PR, merge it
4. Follow the Tier classification from the branch's planning doc (Tier-1 = self-verify + CI; Tier-2 = independent review or recorded justification before merge)

**Verification for each branch:**
```
python -m pytest backend/tests/test_layer3*.py -q
python tools/l3-progress-check.py
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > /dev/null
git diff --check
```

### 2. Write next planning doc (after branch-local merges resolve)

**Goal:** Write the next Layer 3 workbench planning doc continuing from doc 1252's posture.

- Next posture from doc 1252: `sec_edgar_statement_role_quality_profile_rendered_detail_ui_v1`
- Write doc 1351 (or the next available number after 1350 is confirmed taken): `1351-sec-edgar-statement-role-quality-profile-rendered-detail-ui.md`
- Before writing: read docs 1248–1252 for the existing arc of operator product surface / rendered UI controls for SEC EDGAR to ensure the new doc is consistent.

**Stop conditions for the planning doc:**
- No code changes in this PR
- No new routes, schema, or persistence in this PR
- Doc only: capability isolation matrix, evidence ledger, entry decision, stop conditions

**Verification:**
```
python tools/l3-progress-check.py
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > /dev/null
git diff --check
```

### 3. Implement per new planning doc

Only after the planning doc is merged: implement the bounded UI control, verify with Playwright headed + headless, and merge.

---

## Progress Manifest Refresh

The progress manifest (`next_milestone_plans/layer3_progress_manifest.json`) has been refreshed: `snapshot_date: 2026-06-04`, `snapshot_base_main_commit: 3c7ab08e` (PR #2174 merge, updated in commit `fa205665`). The notes entries below the header are accurate only through PR #609 / `ad51b1c6` (2026-05-06) — a full notes refresh for docs 868-929 and 1115-1350 is pending. After each batch of new implementations merges, run a separate manifest-refresh PR to bring the notes up to date.

---

## What Is EXPLICITLY OUT OF SCOPE for this session

- SEC XBRL services (`backend/app/services/layer3_sec_xbrl_*.py`) — owned by SEC XBRL session
- `backend/tests/test_sec_xbrl*.py` and `diagnostics/assessment/sec_xbrl_*.py`
- `next_milestone_plans/Layer3_planning_docs/1344-*.md` through `1350-*.md`
- Auth/security implementation (zero auth infrastructure; see `200_AUTH_SECURITY_ENTRY_CONTRACT.md`)
- Provider/public URL runtime
- Connector/destination dispatch runtime
- Qualitative/hybrid/RAG execution beyond already-admitted
- Source breadth expansion beyond server-configured recursive ingestion
- Full mockup program activation (blocked; see doc 917)

---

## File Ownership — Avoid Collisions with SEC XBRL Session

This session owns:
- `backend/app/review_ui/static/layer3.js`, `layer3.html`, `layer3.css`
- `backend/app/services/layer3_sec_edgar_*.py` and other Layer 3 workbench services (non-SEC XBRL)
- `backend/app/api/layer3.py`
- `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/Layer3_planning_docs/1351_*.md` and beyond (non-SEC XBRL docs)

**Do NOT touch:**
- `backend/app/services/layer3_sec_xbrl_*.py`
- `backend/tests/test_sec_xbrl*.py`
- `diagnostics/assessment/sec_xbrl_*.py`
- `next_milestone_plans/Layer3_planning_docs/1344-*.md` through `1350-*.md`

---

## Verification Commands (run after each PR)

```
# Backend Layer 3 tests
python -m pytest backend/tests/test_layer3*.py -q

# Playwright headed+headless (for UI PRs)
npx playwright test --project=chromium e2e/layer3-workbench.spec.js --headed
npx playwright test --project=chromium e2e/layer3-workbench.spec.js

# Progress check
python tools/l3-progress-check.py

# JSON validity
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > /dev/null
python -m json.tool next_milestone_plans/layer3_workbench_proof_manifest.json > /dev/null

# Clean diff
git diff --check
```
