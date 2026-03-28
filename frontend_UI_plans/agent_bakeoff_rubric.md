# Agent Bake-Off Rubric

## 1. Purpose

This rubric is used to score Jules and Antigravity against the same bounded slice.

The goal is to compare implementation quality, not presentation style alone.

## 2. Scoring Model

Recommended scale per category:

- `0` = failed or materially incorrect
- `1` = weak
- `2` = adequate
- `3` = strong
- `4` = excellent

Recommended weighting:

| Category | Weight |
| --- | --- |
| Spec fidelity | 20 |
| Scope discipline | 15 |
| Architecture and modularity | 15 |
| Read-only safety and boundary handling | 10 |
| Test quality | 10 |
| UI interaction quality | 10 |
| Repo-fit simplicity | 10 |
| Mismatch and failure-state handling | 10 |

## 3. Category Definitions

### 3.1 Spec Fidelity

Score how closely the output follows the frozen planning docs.

High score requires:

- correct route family
- correct node model
- correct tree behavior
- correct details drawer behavior

### 3.2 Scope Discipline

Score whether the output stayed within Slice 01.

Low score triggers:

- unauthorized preview work
- unauthorized polling
- new framework/build-system additions
- unrelated refactors

### 3.3 Architecture And Modularity

Score whether the implementation is cleanly layered and extensible.

High score requires:

- clear separation of route, schema, service, UI, and asset concerns
- minimal cross-coupling
- no ad hoc monolithic handler logic

### 3.4 Read-Only Safety And Boundary Handling

Score whether the implementation respects:

- GET-only review endpoints
- allowlisted review roots
- no mutation/generation side effects

### 3.5 Test Quality

Score whether tests are:

- present
- meaningful
- aligned to the validation plan
- grounded in the golden runtime

### 3.6 UI Interaction Quality

Score whether the slice delivers:

- usable run selector
- usable overview switching
- usable tree behavior
- usable node/file-to-details interactions
- usable diagram zoom/pan if included in the slice

### 3.7 Repo-Fit Simplicity

Score whether the implementation fits the repo without unnecessary platform changes.

High score requires:

- additive backend-served shape
- no needless infrastructure expansion
- minimal touched-file surface consistent with the blueprint

### 3.8 Mismatch And Failure-State Handling

Score whether the implementation correctly handles:

- disabled non-reviewable runs
- missing advertised report refs
- empty reviewable state
- not-exercised nodes

## 4. Disqualifying Mistakes

Any of these should heavily penalize or disqualify an entry:

- writes or mutates runtime state
- adds run execution controls
- introduces an unplanned frontend framework or build toolchain
- ignores the canonical graph registry
- hides missing artifacts instead of surfacing them

## 5. Recommended Review Output

For each agent, produce:

- per-category score
- weighted total
- short strengths summary
- short weaknesses summary
- merge recommendation:
  - accept
  - reject
  - accept only as partial basis

