# Layer3 Progress Artifact Rebuild Prompt

Use this prompt when rebuilding the Claude Cowork artifact or its scheduled refresh.

```text
Rebuild the Layer3 APS progress artifact so it reflects current repo truth and renders reliably.

Use the clean repo checkout that contains the current artifact files and matches the artifact state you want to refresh.
For this packet, the current seed checkout is:
`C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3-progress-main`

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
- current `main` now includes the bounded package-derived context handoff implementation slice from PR `#115`, rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- current `main` now also includes the merged PR `#119` malformed-scoped candidate-discovery closeout across the export, export-package, and context-packet gates
- current `main` also includes the post-PR116 docs/progress sync from PR `#117`
- current `main` now also includes the landed read-only `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze from PR `#118`, selecting `context_dossier` as the next later shared APS family after the landed package-context milestone
- current `main` also includes the post-PR118 docs/progress closeout from PR `#120`
- current `main` now includes the bounded `aps_context_dossier_handoff` implementation slice from PR `#121`, rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`, plus narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`
- current `main` also includes the post-PR121 docs/progress closeout from PR `#122`
- current `main` also includes the post-PR122 artifact-state fix from PR `#123`
- paired export-derived context packets remain the live dossier input branch; the landed package-derived context handoff must not be presented as dossier input proof
- current `main` now also includes the landed read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze from PR `#124`, selecting `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary
- current `main` now also includes the bounded deterministic insight handoff implementation slice from PR `#126`, rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, plus narrow deterministic gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- current `main` now also includes the post-PR126 docs/progress sync from PR `#127`
- current `main` now also includes the landed read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze from PR `#128`, selecting `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary
- current `main` now also includes the post-PR128 docs/progress sync from PR `#129`
- current `main` now also includes the bounded deterministic challenge handoff implementation slice from PR `#130`, rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`, and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`
- current `main` now also includes the post-PR130 docs/progress sync from PR `#131`
- current `main` now also includes the landed read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze from PR `#132`, selecting `deterministic_challenge_review_packet` as the next deterministic continuation beyond the now-landed deterministic challenge handoff
- current `main` now also includes the post-PR132 docs/progress sync from PR `#133`
- current `main` now also includes the bounded deterministic challenge review-packet handoff slice from PR `#134`, rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, plus the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`
- current `main` now also includes the post-PR134 docs/progress sync from PR `#135`
- current `main` now also includes the landed read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze from PR `#136`, selecting `validate_only_gates` as the exact next verification continuation beyond the landed review-packet handoff
- the immediate required move is now to represent that validate-only-gates freeze as `merged` and the bounded validate-only execution or report-refresh lane as `planned`, not to restate the already-landed review-packet handoff or widen beyond that boundary
- `validate_only_gates` is now the landed current-main family choice; later validate-only execution or report refresh remains planned and must not be collapsed into the same state

When rebuilding from a checkout that matches current `main` after PR `#136` is merged and before any validate-only execution or report-refresh PR exists:
- show the bounded `context_dossier` handoff slice from PR `#121` as completed on `main`
- show the exact-run gate-hardening follow-up as already landed on `main`
- show the landed package-derived-context freeze as completed on `main`
- show the package-derived context handoff slice as `merged`
- show the landed `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze as `merged`
- show the bounded `context_dossier` handoff lane from PR `#121` as `merged`
- show the post-PR121 docs/progress closeout from PR `#122` and the post-PR122 artifact-state fix from PR `#123` as already landed on `main`
- do not present package-derived context as dossier input proof
- show the read-only deterministic continuation freeze, rooted in `deterministic_insight_artifact`, as `merged`
- show the read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze as `merged`
- show the bounded deterministic challenge handoff as `merged`
- show the read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze as `merged`
- show the post-PR132 docs/progress closeout from PR `#133` as already landed on `main`
- show the bounded deterministic challenge review-packet handoff as `merged`
- show `validate_only_gates` as `merged` from PR `#136`
- show the bounded validate-only execution or report-refresh lane as `planned`

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
