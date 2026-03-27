# Agent Bake-Off Submission Checklist: APS Tier1 Retrieval Plane Phase1B

Each submission must provide all of the following in its owned workspace folder.

## Required deliverables

- concise implementation summary
- exact changed-file list with a short reason for each file
- architecture/module boundary notes
- assumptions made
- blockers encountered or explicitly avoided
- risks, tradeoffs, and tech-debt accounting
- exact validation commands run
- test results with pass or fail counts
- explicit statement on whether the review UI regression suite was run
- scope-conformance statement

## Required technical disclosures

Each submission must explicitly state:

- the exact operator-only external HTTP routes implemented
- whether existing public APS routes remained unchanged
- whether schema reuse succeeded without modifying `backend\app\schemas\api.py`
- how empty retrieval scope fails closed
- whether the empty retrieval scope route returns the frozen HTTP `409`
- how retrieval search ordering matches current canonical behavior

## Required owned-output locations

Antigravity:

- `frontend_UI_plans\agent_workspaces\antigravity\deliverables\`
- `frontend_UI_plans\agent_workspaces\antigravity\logs\`
- `frontend_UI_plans\agent_workspaces\antigravity\patches\`
- `frontend_UI_plans\agent_workspaces\antigravity\screenshots\`

Jules:

- `frontend_UI_plans/agent_workspaces/jules/deliverables/`
- `frontend_UI_plans/agent_workspaces/jules/logs/`
- `frontend_UI_plans/agent_workspaces/jules/patches/`
- `frontend_UI_plans/agent_workspaces/jules/screenshots/`
