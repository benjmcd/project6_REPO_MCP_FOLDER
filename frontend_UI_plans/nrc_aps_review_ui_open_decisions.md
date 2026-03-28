# NRC APS Review UI Open Decisions

This document records the decisions already recommended and user-confirmed for v1, plus the small set of non-critical implementation details that remain discretionary.

## 1. Recommended Defaults To Freeze

These are the recommended defaults based on the verified repo shape and the current user direction.

### Product Scope

- NRC APS only
- read-only review surface
- latest completed reviewable run as default landing target
- historical run selector enabled
- general and run-specific views both present in v1

### Technical Shape

- backend-served additive UI
- additive read-only review API
- Mermaid as the first renderer
- renderer-independent review model underneath Mermaid
- hybrid source-of-truth model:
  - DB/API for run identity and selector metadata
  - persisted artifacts for review rendering and file tree

### Interaction Shape

- node click highlights files and opens details
- file click highlights mapped node and opens details
- diagram zoom/pan is a first-class requirement
- file preview is deferred
- live polling is deferred

## 2. Resolved User Decisions

These decisions are now user-confirmed and should be treated as the default implementation target.

1. **Disabled runs in selector**
   - Preferred: show non-reviewable NRC APS runs as disabled entries with reasons.
   - Fallback: if disabled-row handling becomes a material blocker, temporarily show reviewable runs only.

2. **Tree presentation**
   - Default v1: strict filesystem tree.
   - Possible later enhancement: alternate curated review-tree view grouped by meaning first and filesystem second.

3. **General view density**
   - `Pipeline Overview` should remain cleaner, more conceptual, and materially less dense than the run-specific view.
   - This should follow the attached reference direction as closely as practical.

4. **Details panel content**
   - Default v1: metadata plus a small structured summary extracted from the selected node/file when available.
   - Not v1: full raw file preview in the details panel.

5. **No-reviewable-run empty state**
   - Default v1: show the normal UI shell with disabled panes if no reviewable run exists.

6. **Strict tree reveal behavior**
   - Default v1: within the strict filesystem tree, auto-reveal the selected node's mapped files.

7. **Detail panel placement**
   - Default v1: right-side drawer or right-side column.

8. **Preview follow-on**
   - When preview is added later, start with JSON/text only.
   - Defer safe image preview for PNG visual pages until after the first preview slice works cleanly.

## 3. Remaining Non-Critical Notes

There are no remaining critical open questions for the v1 review UI scope.

Outstanding implementation discretion may still exist around:

- exact drawer sizing and responsive collapse behavior
- exact tree expansion animation and reveal behavior
- exact visual treatment of disabled runs and disabled panes

These are implementation details, not scope-definition blockers.

## 4. Decisions That Should Not Be Reopened Without A Clear Reason

- the surface should remain read-only in v1
- the initial scope should remain NRC APS only
- the implementation should favor the existing backend as the serving home
- the UI should not depend on a hardcoded single runtime root
- the general and run-specific views should share one canonical node model
- the default tree mode for v1 should be a strict filesystem tree
- the general pipeline view should remain cleaner and more conceptual than the run-specific view
- the details panel should live on the right
- future preview should start with JSON/text only
