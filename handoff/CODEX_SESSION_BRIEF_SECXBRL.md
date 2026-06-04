# SEC XBRL Track — Session Brief (2026-06-04)

Start from a clean worktree off `project6-origin/main` (`a2775067`, PR #2173). Read `AGENTS.md` first.

---

## Current State (verified against git log, 2026-06-04)

The last two milestones recorded on the progress board as "branch-local" are **already merged**:

- `sec_xbrl_unadmitted_key_adapter_v1` → merged as PR #2172 (`dbbc84d7`)
- `sec_xbrl_resolved_fact_diagnostic_redaction_cleanup_v1` → merged as PR #2173 (`a2775067`)

**First action:** Update `next_milestone_plans/layer3_progress_board.md` to mark these as `merged`
rather than `branch-local`. Use a focused PR that touches only the board and manifest JSON files
(no code). Verify with `tools/l3-progress-check.py` after.

---

## What Was Built (consolidation series, PRs #2128–#2173)

The consolidation work landed the following shared modules:
- `diagnostics/assessment/sec_xbrl_diagnostic_framework.py` — diagnostic criterion/blocking-reason/decision/report-envelope helpers
- `backend/app/services/layer3_sec_xbrl_public_authority_guard.py` — raw/local authority violation detection + `reject_unadmitted_keys` adapter
- `backend/app/services/layer3_sec_xbrl_report_leak_guard.py` — public-report leak flags, text-leak, raw-value-key, report-leak rejection
- `backend/app/services/layer3_sec_xbrl_canonical_concepts.py` — canonical report redaction scan payloads
- `diagnostics/assessment/sec_xbrl_report_redaction.py` — diagnostic residual magnitude stripping
- Report-envelope, matrix-label, stratified-identity, nonlocal-hit-class, and sector redaction helpers (batches 1–3)
- Package-family policy registry and mixed-source package contract

**Test state (last verified):** `477 passed, 3 warnings` on the full SEC XBRL suite.

---

## Next Posture (per planning doc 1349)

From the progress board "Next posture":
> Continue only byte-stable diagnostic text/hit-class extraction or
> service-family-specific runtime guard migrations after exact semantics are
> proven; do not bulk-migrate custom wrappers.

**Remaining custom surfaces (do NOT bulk-migrate):**
- `layer3_sec_xbrl_projection_persistence._reject_raw_or_local_authority` (already delegates to shared guard; no migration needed)
- `layer3_sec_xbrl_statement_packet_persistence._reject_raw_or_local_authority` (same)
- `layer3_sec_xbrl_operator_review_workflow._reject_raw_or_local_authority` (same)
- CIK/contact scan variants, auth-binding helpers, residual-magnitude policy surfaces

These are NOT exact duplicates of the shared guard — they preserve service-specific error contracts.
**Do not touch them** until a focused planning doc defines the exact semantics.

---

## Prioritized Work Queue

### 1. Progress board sync (IMMEDIATE, ~30 min)

**Goal:** Correct the stale board before any further SEC XBRL work.

```
Task: Merge the two stale board entries (PR #2172, #2173)
Files: next_milestone_plans/layer3_progress_board.md
       next_milestone_plans/layer3_progress_manifest.json (snapshot_base_main_commit, notes)
       next_milestone_plans/layer3_workbench_proof_manifest.json (if affected)
Verification:
  - python tools/l3-progress-check.py passes
  - git diff --check clean
  - No code or behavior change
PR title: "Sync SEC XBRL progress board to merged PR #2172-#2173"
```

### 2. SEC XBRL activation lane — write planning doc 1350 (AFTER board sync)

**Goal:** Write `next_milestone_plans/Layer3_planning_docs/1350-sec-xbrl-activation-lane-selection.md`.

This is the **activation planning doc** that authorizes (or explicitly defers) the parked
activation lane. The consolidation work (#2128–#2173) was the prerequisite. Now the question
is whether and how to enable the default-on runtime.

**Template to follow:** `199_AUTH_SECURITY_ENTRY_FREEZE.md` (same structure with capability
isolation matrix, evidence ledger, stop conditions, and entry_decision field).

**The activation lane covers:**
- `layer3_sec_xbrl_default_on_admission_restatement.py` — default-on runtime posture
- `backend/app/services/layer3_sec_xbrl_value_reveal_authority.py` — value-reveal authorization
- `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py` — controlled reveal submit
- E2E integration path (`layer3_sec_xbrl_e2e_integration.py`, `layer3_sec_xbrl_e2e_offline_orchestrator.py`)
- Multi-filing evidence authority gate (`layer3_sec_xbrl_multi_filing_evidence_authority_gate.py`)
- In-app auth policy (`layer3_sec_xbrl_in_app_auth_policy.py`)

**Entry decision choices:**
- `deferred_pending_auth_security_framework` (RECOMMENDED if auth is not yet implemented)
- `deferred_pending_operator_acceptance_criteria`
- `proceed_with_bounded_default_on_validation_only`

**Stop conditions for this planning doc:**
- Do NOT change any runtime default in this PR
- Do NOT enable value-reveal or controlled-submit behavior
- Do NOT modify E2E integration routes
- Doc only: capability isolation matrix + evidence ledger + entry decision

**Verification for this PR:**
- `python tools/l3-progress-check.py` passes
- Full SEC XBRL suite: `python -m pytest backend/tests/test_sec_xbrl*.py -q` — no regression
- `git diff --check` clean

### 3. After planning doc 1350 is merged

Only then: implement whatever entry_decision 1350 selects. If `deferred`, stop and coordinate
with the Layer 3 / Auth track. If `proceed_with_bounded_default_on_validation_only`, write
the corresponding contract doc (1351) before any code.

---

## What Is EXPLICITLY OUT OF SCOPE for this session

- Auth/security implementation (zero auth infrastructure exists; see `200_AUTH_SECURITY_ENTRY_CONTRACT.md`)
- Frontend/UI changes
- Alembic migrations
- Source acquisition (no live Arelle invocation, no live SEC network calls)
- Value-reveal behavior changes
- `layer3_sec_xbrl_operator_review_workflow.py` beyond the already-merged `_reject_unadmitted_keys` migration
- Any new `_reject_raw_or_local_authority` wrapper consolidation (these are NOT exact duplicates)

---

## File Ownership — Avoid Collisions with Layer 3 Session

This session owns:
- `backend/app/services/layer3_sec_xbrl_*.py` files
- `backend/tests/test_sec_xbrl*.py` files
- `diagnostics/assessment/sec_xbrl_*.py`
- `next_milestone_plans/Layer3_planning_docs/1349-*.md`, `1350-*.md`
- `next_milestone_plans/layer3_progress_board.md` (for SEC XBRL entries only)

**Do NOT touch:**
- `backend/app/services/layer3_workbench.py` or other Layer 3 workbench services
- `backend/app/review_ui/static/layer3.js` or `.html`
- `backend/app/api/layer3.py`
- `next_milestone_plans/Layer3_planning_docs/199_*.md`, `200_*.md`
- `next_milestone_plans/layer3_progress_manifest.json` (owned by Layer 3 session for APS/workbench entries)

---

## Verification Commands (run after each PR)

```powershell
# Full SEC XBRL suite
python -m pytest backend/tests/test_sec_xbrl*.py -q

# Progress check
python tools/l3-progress-check.py

# JSON validity
python -m json.tool next_milestone_plans/layer3_progress_manifest.json > $null
python -m json.tool next_milestone_plans/layer3_workbench_proof_manifest.json > $null

# Clean diff
git diff --check
```
