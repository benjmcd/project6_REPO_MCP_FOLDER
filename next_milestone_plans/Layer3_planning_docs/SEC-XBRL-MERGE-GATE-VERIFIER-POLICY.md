# SEC XBRL Merge-Gate & Verifier-Tier Policy

Status: active process policy (validate-only governance; no code, runtime, schema, or redaction-posture impact).
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
sole independent review, this policy defines a risk-tiered merge gate with a dependable independent-verifier lane and
relegates the bot to best-effort defense-in-depth.

## Roles

- Executor: whichever agent authors the PR — Codex by default for product slices; Claude when directed (e.g.
  governance/hygiene). The executor self-verifies, opens, and lands PRs.
- Independent verifier: a reviewer independent of the PR's author — the agent that did NOT author the PR (Codex
  reviews Claude-authored Tier-2 PRs; Claude reviews Codex-authored Tier-2 PRs), and/or the operator. This is the
  dependable review lane. The automated bot is best-effort defense-in-depth, never the sole gate.

## Tier classification

Quick test: if reverting the PR would require a down-migration, a data backfill, or it touches stored/revealed values, runtime defaults, or redaction posture, it is **Tier 2**. Otherwise it
is **Tier 1**.

### Tier 1 — low-risk (validate-only, additive, reversible)

Applies when the PR changes ONLY: diagnostics, validate-only committed reports, tests, planning/process docs, or
additive service logic with NO schema, persistence, value-reveal, runtime-default, or redaction-posture change.

Merge gate:
1. Verifier record documented in the PR body (verification commands and results).
2. CI green (all shards and aggregate checks).
3. `@codex review` posted as best-effort; if the bot is silent within the watch window, record a silent-bot
   disposition and proceed.

Executor self-verification satisfies the Tier 1 verifier record; independence is the Tier 2 escalation, not a
Tier 1 requirement (the bot remains best-effort defense-in-depth, never the sole gate).

### Tier 2 — high-risk / irreversible

Applies when the PR touches ANY of: Alembic migrations; `models.py` / ORM schema; durable persistence; value-reveal
enablement or revealed-value handling; runtime default-on changes; redaction-posture changes.

Merge gate (Tier 1 requirements PLUS):
4. An INDEPENDENT pre-merge review — by a reviewer who is NOT the PR's author — is RECORDED before merge.
   - The executor PAUSES after CI-green and self-verification, hands the PR (diff and verification evidence) to the
     operator, who relays it to the independent verifier; the verifier's review is relayed back and recorded on the
     PR before merge.
   - The executor MUST NOT self-certify and merge a Tier-2 PR.

## Disposition recording

When the bot is silent at merge time, record a tracking issue following the #2004 / #2008 / #2009 pattern: the opening
body states the bot did not post; the closing comment records the verifier disposition (independent review for
Tier 2; executor self-verification for Tier 1) and explicitly does NOT claim a bot review.

## Non-goals

Process governance only. No code, runtime, schema, persistence, value-reveal, default-on, or redaction-posture
changes. Default-off and validate-only postures are unaffected by this document.
