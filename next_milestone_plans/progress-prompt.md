# Layer3 Progress Artifact Rebuild Prompt

Use this prompt when rebuilding the Claude Cowork artifact or its scheduled refresh.

```text
Rebuild the Layer3 APS progress artifact so it reflects current repo truth and renders reliably.

Use the clean repo checkout that contains the current artifact files and matches the artifact state you want to refresh.
For this packet, the current seed checkout is:
`C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3-pkgctx-handoff`

Read these files in this order:
1. `next_milestone_plans/layer3_progress_refresh_spec.md`
2. `next_milestone_plans/layer3_progress_manifest.json`
3. `next_milestone_plans/layer3_progress_board.md`
4. `next_milestone_plans/progress-ui-spec.md`

Goal:
- rebuild the `layer3-aps-progress` Cowork artifact so it clearly shows:
  - what is done on `main`
  - what the current focus is
  - what the candidate next consumers are
  - what is explicitly deferred

Hard rules:
- GitHub PR state is authority for merged versus open.
- Do not infer merge state from planning-doc wording alone.
- The artifact must remain readable with HTML and CSS alone.
- JavaScript may enhance interaction, but it must not be required for milestone rows, current focus, candidate next consumers, or deferred scope.
- Mermaid is optional enhancement only. If it does not render, there must be no loss of meaning.
- Do not call the artifact live if it only embeds a stale snapshot and never updates from refreshed inputs.

Required sections in order:
1. Program State Summary
2. Current Focus
3. Completed Chain
4. Milestone Table
5. Candidate Next Consumers
6. Deferred Scope

Visual rules:
- `merged`: green
- `merged_with_open_docs_closeout`: distinct green-plus-followup state
- `open`: orange
- `planned`: amber
- `deferred`: gray
- `branch_only`: blue
- keep labels visible in text, not color alone

Critical architectural rule:
- If the artifact can read refreshed files at render time, use that.
- If it cannot, then the scheduled refresh must rewrite the artifact itself from the refreshed manifest and board during every successful refresh.

Current repo-side facts to preserve:
- current `main` includes the bounded APS multisource implementation from PR `#101`
- current `main` includes the docs-only multisource closeout from PR `#102`
- current `main` also includes the export-package first shared-consumer freeze and its docs-only closeout from PR `#106` and PR `#107`
- the immediate required move is no longer to choose the first shared consumer; that choice is already settled on current `main` in favor of `evidence_report_export_package`
- current `main` also includes the bounded export-package handoff implementation slice from PR `#109` and its docs-only closeout from PR `#110`, rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- current `main` also includes the exact-run export/export-package gate-hardening follow-up from PR `#111` and `#112`
- current `main` now includes the landed `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` freeze from PR `#113`, selecting package-derived context packet as the next later shared APS family beyond the landed export-package boundary
- the current branch/workspace now carries the bounded package-derived context handoff implementation slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- the current branch/workspace also includes the narrow context-packet gate hardening in `backend/app/services/nrc_aps_context_packet_gate.py` and `backend/tests/test_layer3_aps_context_packet_handoff.py`
- that branch-local slice is not yet landed on current `main` and should remain `branch_only` until GitHub confirms a PR exists
- `context_dossier` remains later and must not be presented as a co-equal current-focus choice with the next package-derived-context freeze

When rebuilding from a checkout that matches current `main` after the export-package handoff slice lands:
- show that slice as completed on `main`
- show the exact-run gate-hardening follow-up as already landed on `main`
- show the landed package-derived-context freeze as completed on `main`

When rebuilding from the current branch/workspace checkout before a PR exists:
- show the bounded package-derived context handoff slice as `branch_only`
- use landing that branch-local slice as the current focus that follows the landed freeze
- do not describe that branch-local slice as landed on `main` or as an open PR before GitHub confirms one exists

Also update the scheduled refresh task so it no longer:
- writes or references `current_main_commit`
- treats Mermaid as primary
- refreshes only the repo files while leaving the artifact itself stale

Success criteria:
- the artifact renders correctly without relying on Mermaid
- the milestone table is present without JS-created critical rows
- done, current focus, candidate next consumers, and deferred scope are visually distinct
- the scheduled refresh and the artifact are wired so the visible artifact actually updates after refresh
```
