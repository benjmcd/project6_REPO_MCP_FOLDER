# Agent Bake-Off Submission Checklist

## 1. Purpose

Each agent submission should satisfy this checklist so the two outputs can be compared on equal terms.

## 2. Required Submission Items

Each submission should provide all of the following.

Submission artifacts should be written into the agent's owned bake-off directory:

- Jules:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\jules\`
- Antigravity:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\`

The owned bake-off directory is the canonical place for:

- written deliverables
- logs
- screenshots
- exported patches/diffs

Actual code edits for the implementation slice should still occur in the tool's isolated repo lane.

Recommended exact editable lanes:

- Jules:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-jules-slice01`
- Antigravity:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-slice01`

If rerun lanes are used instead, keep the same `jules`/`antigravity` owned output directories and only change the editable lane path.

### 2.1 Change Summary

- concise implementation summary
- explicit statement of what was in scope
- explicit statement of what was intentionally not implemented

### 2.2 Changed File List

- list of existing files modified
- list of new files added
- short reason for each touched file

### 2.3 Architecture Notes

- description of route layer
- description of service/module boundaries
- description of UI asset structure

### 2.4 Assumptions

- any assumptions made that were not directly specified
- any points where the agent had to choose between multiple reasonable implementations

### 2.5 Risks And Tradeoffs

- known weaknesses
- deferred concerns
- anything that may need revision in Slice 02

### 2.6 Validation Evidence

- tests added
- tests run
- commands used
- results summary
- any tests not run and why

### 2.7 UI Evidence

When possible, include:

- screenshot(s)
- short walkthrough of the implemented interactions

### 2.8 Scope-Conformance Statement

Explicitly confirm whether the submission:

- remained read-only
- remained NRC APS only
- avoided preview/polling/execution controls
- avoided new build tools/frameworks

## 3. Required Comparison Questions

Each submission should make it easy to answer:

- Did the agent follow the planning docs?
- Did the agent stay in Slice 01?
- Did the agent keep the implementation modular?
- Did the agent preserve repo-fit simplicity?
- Did the agent handle the known mismatch cases safely?

## 4. Completion Standard

A submission is not comparison-ready unless it includes:

- changed file inventory
- validation evidence
- assumptions
- risks
- scope-conformance statement
