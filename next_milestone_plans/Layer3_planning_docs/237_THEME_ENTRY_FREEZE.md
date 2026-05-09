# Layer 3 Theme Entry Freeze

Status: implementation-entry checklist for future theme-complete Layer 3 work.

This document is the stop/go checklist for any pass that touches Layer 3 pages, themes, or end-to-end UI proof. It does not authorize implementation by itself.

## Required Preflight

Before any implementation pass:

1. fetch `project6-origin/main`;
2. confirm current branch, local HEAD, remote main, and `git status --short --branch`;
3. confirm no open PRs or unresolved review threads relevant to Layer 3 UI/theme work;
4. run `python .\tools\l3-progress-check.py`;
5. run the focused backend/API and Playwright tests relevant to the touched surface;
6. run `git diff --check`;
7. classify the target as docs-only, test-only, UI-only, backend/API-only, or separately frozen runtime behavior.

If any validation is infeasible, report the exact reason and continue only within the admitted scope.

## Grill-Me Gate

Use these questions before editing. If the answer cannot be proven from current source/tests/docs, stay in audit mode.

1. Is the target surface live, prototype, or deferred?
   - recommended answer now: `/review/layer3` is live; `/review/layer3/static/claude.html` is prototype.
2. Does the change alter product behavior or only proof/planning?
   - recommended answer for the next pass: test-only over existing live themes.
3. Could the change accidentally make Claude live?
   - recommended answer: no; any Claude live work needs its own freeze.
4. Does the change create or imply arbitrary corpus ingestion?
   - recommended answer: no; current source authority is server-owned materialization and admitted source rows.
5. Does theme selection change API payloads or server authority?
   - recommended answer: no; theme is presentation only.
6. Are manual/spec/custom fields backed by corpus/session authority?
   - recommended answer: empty or absent unless server-linked; sample text belongs only on prototype surfaces.
7. Are headed and headless browser checks both required?
   - recommended answer: yes for visible UI/theme changes; test-only planning can name the requirement.
8. Is any broader deferred category being touched?
   - recommended answer: stop unless a separate freeze admits it.

## Allowed First Implementation After This Pack

The narrowest next implementation pass is:

```text
Implement one test-only Layer 3 live-theme parity proof for /review/layer3 across system, light, dark, and workbench. Do not include Claude. Do not add UI controls or backend behavior. Use existing admitted source setup/materialization, drive the maximum currently supported rendered path, assert request-shape parity, visual/focus coherence, and forbidden-control absence in headed and headless Chromium. Stop and report if existing controls cannot support the proof.
```

## Claude Implementation Entry

Claude can enter implementation only after a separate freeze states:

- selected live route strategy;
- exact prototype sections retained, mapped, or removed;
- stable selectors and accessibility roles;
- how corpus-linked manual/spec content is sourced;
- failure behavior for absent live state;
- visual parity requirements;
- exact tests and screenshots;
- negative invariants and stop conditions.

Until then, Claude remains a static prototype route and theme selector redirect.

## PR Scope Rules

- docs-only pass: planning docs and optional proof metadata only if needed.
- test-only pass: tests/helpers only; no runtime behavior.
- UI-only pass: static UI files and UI tests only; no backend/API/model/migration behavior.
- backend/API pass: routes/DTO/services/tests only after a freeze; no rendered controls unless separately admitted.
- broad runtime pass: one category at a time, with its own freeze and proof plan.

## Re-Audit Requirements

After any pass:

1. re-run the focused validations;
2. inspect `git diff --check`;
3. inspect changed files for accidental scope widening;
4. confirm Claude classification was not changed unless explicitly intended;
5. confirm no unsupported controls or payload fields were introduced;
6. if a PR is opened, wait for checks and inspect review comments/threads before merge.

## Stop Condition

Stop immediately and report instead of patching if the work requires local upload, local-directory ingestion, broad parser/OCR behavior, source adapter registry, source-class expansion, web connector retrieval, RAG/vector retrieval, package mutation/reconstruction, connector/destination dispatch, provider network writes, provider-public URLs, rendered provider-private controls, full mockup activation, hidden LLM planning, model/migration changes, or auth/security changes.
