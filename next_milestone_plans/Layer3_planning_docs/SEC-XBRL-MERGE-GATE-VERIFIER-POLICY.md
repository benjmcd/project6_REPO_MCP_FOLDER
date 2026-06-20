# SEC XBRL Merge-Gate & Verifier-Tier Policy

Status: active process policy (right-sized governance; no code, runtime, schema, or redaction-posture impact).
Established: 2026-05-31.
Scope: all SEC XBRL Layer 3 pull requests — canonical normalization, sector families, statement
organization/assembly, projection, multi-period, persistence, value-reveal, validation gates, and their
diagnostics/services/tests/docs.

## Why this exists

The automated review bot (`chatgpt-codex-connector`) has proven intermittently unavailable:

- Reviewed PRs #1999 / #2001 / #2002.
- Went silent before merge on #2003 / #2005 / #2006.
- Recovered on #2011.
- Silent again on #2014.

Review-coverage gaps were dispositioned in issues #2004 / #2008 / #2009; the connector outage root cause requires
GitHub-App admin authority and remains an open operator action (#2010). Because the bot cannot be relied upon as the
sole independent review, this policy defines a risk-tiered merge gate that treats the bot as best-effort
defense-in-depth and uses independent review as an escalation tool rather than a blanket progress blocker.

## Roles

- Executor: whichever agent authors the PR — Codex by default for product slices; Claude when directed (e.g.
  governance/hygiene). The executor classifies risk, self-verifies, records evidence, opens, and lands PRs.
- Independent verifier: a reviewer independent of the PR's author — the agent that did NOT author the PR, and/or the
  operator. Independent review is recommended for higher-risk changes and required only when an explicit blocker,
  failed verification, ambiguous authority boundary, or operator instruction calls for it. The automated bot is
  best-effort defense-in-depth, never the sole gate.

## Tier classification

Quick test: if the PR is validate-only/additive/reversible and does not touch stored or revealed values, runtime
defaults, redaction posture, durable schema, or persistence, it is **Tier 1**. If it touches any of those surfaces, it
is **Tier 2** and needs explicit risk documentation plus targeted verification. Tier 2 does not automatically require a
separate pre-merge reviewer.

### Tier 1 — low-risk (validate-only, additive, reversible)

Applies when the PR changes ONLY: diagnostics, validate-only committed reports, tests, planning/process docs, or
additive service logic with NO schema, persistence, value-reveal, runtime-default, or redaction-posture change.

Merge gate:
1. Verifier record documented in the PR body (verification commands and results).
2. CI green (all shards and aggregate checks).
3. `@codex review` or another independent review request may be posted when useful, but bot silence is not a blocker.
   Record bot silence only when it affects the PR's risk/disposition narrative.

Executor self-verification satisfies the Tier 1 verifier record. Independent review is optional defense-in-depth unless
a concrete blocker is present.

### Tier 2 — high-risk / irreversible

Applies when the PR touches any of: Alembic migrations; `models.py` / ORM schema; durable persistence; value-reveal
enablement or revealed-value handling; runtime default-on changes; redaction-posture changes.

Merge gate (Tier 1 requirements PLUS):
4. PR body or closing comment records the exact Tier 2 surfaces touched and why they are necessary.
5. Verification includes the narrowest meaningful tests plus migration/rollback or containment notes when schema or
   persistence changes are present.
6. Independent review is sought when practical for redaction-posture changes, value reveal, default-on behavior,
   destructive/irreversible migrations, broad operator workflow changes, or any change whose authority boundary remains
   ambiguous after audit. If independent review is not obtained, the executor records why self-verification is adequate
   and what would force a follow-up.
7. Merge is blocked only by failing CI checks (author-enforced; `main` has no branch-protection required-status-check
   gate), unresolved critical/blocking review findings, missing rollback or
   containment notes for schema/persistence changes, unclear authority, or an operator instruction requiring review.

## Disposition recording

When the bot is silent at merge time, do not open a tracking issue by default. Record a PR comment or issue only when
the silence materially affects risk assessment, leaves a requested review unresolved, or is needed for operator-facing
handoff. Any such record must explicitly avoid claiming a bot review.

## Non-goals

Process governance only. No code, runtime, schema, persistence, value-reveal, default-on, or redaction-posture
changes. Default-off and validate-only postures are unaffected by this document.
