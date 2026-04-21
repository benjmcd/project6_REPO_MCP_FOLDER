# Layer3 Progress UI Spec

## Purpose

This file defines how an external render surface, including a Claude Cowork artifact,
should present the bounded Layer3 APS progress chain.

The manifest and board already define truth and prose. This file exists so a renderer
does not have to guess how to turn that truth into a stable interface.

## Proven Failure Modes To Avoid

Do not repeat these patterns:
- embedding a hardcoded manifest snapshot inside artifact HTML and then calling it live
- refreshing only the repo files while leaving the artifact itself stale
- requiring JavaScript to populate the milestone table or other primary content
- requiring Mermaid to understand what is done, what is current, and what is still deferred
- flattening done, current focus, candidate next work, and deferred scope into one undifferentiated view

## Canonical Inputs

Render from these in order:
1. `next_milestone_plans/layer3_progress_manifest.json`
2. `next_milestone_plans/layer3_progress_board.md`
3. `next_milestone_plans/layer3_progress_refresh_spec.md`

GitHub PR state remains authority for merged versus open.
The UI must not override authority.

## Hard Render Rules

- The artifact must remain understandable with HTML and CSS alone.
- JavaScript may enhance interaction, but it must not be required for:
  - summary counts
  - milestone rows
  - current focus
  - candidate next consumers
  - deferred scope
- Mermaid is optional enhancement only.
- If Mermaid fails, there must be no loss of meaning.
- If the artifact cannot read refreshed files at render time, the scheduled refresh must rewrite the artifact itself from current manifest data.
- Do not present candidate next consumers as though they are already the current implementation lane.

## Required Visual Sections

Render these sections in this order:

1. `Program State Summary`
   - show summary cards for:
     - done now on `main`
     - current focus
     - candidate next consumers
     - deferred scope
   - use manifest `summary_counts` and `next_required_decision`

2. `Current Focus`
   - render the `next_required_decision` block as the most visually prominent active or closure section
   - if `next_required_decision.state` is not `settled`, treat it as the most visually prominent non-complete section
   - if `next_required_decision.state` is `settled`, render a closure card instead of a next-lane card
   - include:
     - title
     - why now
     - must-not-skip rules or reopen conditions

3. `Completed Chain`
   - render the merged milestone chain as a visual rail or grouped sequence
   - each item should remain readable without JS
   - keep milestone order aligned with the manifest

4. `Milestone Table`
   - render a stable table in markup
   - do not rely on JS to create rows
   - include:
     - milestone title
     - state
     - governing doc
     - key PRs
     - short note

5. `Candidate Next Consumers`
   - render `next_required_decision.candidate_families`
   - if the list is empty under a `settled` packet, render an explicit `None active` message instead of inventing candidates
   - visually distinguish these from the current focus

6. `Deferred Scope`
   - render deferred items as a muted grouped grid or list
   - make it visually obvious these are not in the active lane

## Visual State Mapping

Use these colors consistently:
- `merged`: green
- `merged_with_open_docs_closeout`: green-olive or other clearly separate done-plus-followup state
- `open`: orange
- `planned`: amber
- `settled`: green-gray or other clearly closed-but-not-deferred state
- `deferred`: gray
- `branch_only`: blue or other clearly non-main state

State labels should remain visible in text, not color alone.

## Layout Guidance

### Desktop

- center the artifact in a readable max-width frame
- use a distinct top summary band
- keep the current focus card above the completed chain
- use flat, information-dense layout rather than decorative dashboard chrome

### Mobile

- stack summary cards vertically
- let the completed chain wrap into rows
- keep milestone rows readable without horizontal overflow where possible

## Content Priority

The user should understand this in under ten seconds:
1. what is already done on `main`
2. what the current focus is
3. what the next bounded consumer candidates are
4. what is still explicitly deferred

If a renderer has to choose between visual flourish and certainty, prefer certainty.

## Implementation Guidance For Cowork

Preferred approach:
- generate primary sections as static HTML from the refreshed manifest
- use CSS for layout and state styling
- use JS only for non-essential polish such as expand-collapse or filters

Acceptable optional enhancement:
- add Mermaid only as a duplicate visualization of an already-readable static section

Unacceptable approach:
- store a stale `const manifest = ...` snapshot in artifact HTML without rewriting that artifact during refresh
- hide the milestone table behind DOM-building JS
- make the only progress diagram depend on Mermaid
