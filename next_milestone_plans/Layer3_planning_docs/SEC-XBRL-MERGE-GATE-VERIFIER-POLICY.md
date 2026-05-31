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

- Executor (Codex): authors slices, self-verifies, opens and lands PRs.
- Independent verifier (Claude, verifier/architect lane): provides review independent of the executor. This is the
  dependable review lane. The bot is best-effort defense-in-depth, never the sole gate.

## Tier classification

Quick test: if reverting the PR would require a down-migration, a data backfill, or it touches stored/revealed values
runtime defaults, or redaction posture, it is **Tier 2**. Otherwise it is **Tier 1**.

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
4. An INDEPENDENT (Claude/verifier) pre-merge review is RECORDED before merge.
   - The executor PAUSES after CI-green and self-verification, hands the PR (diff and verification evidence) to the
     operator, who relays it to the independent verifier; the verifier's review is relayed back and recorded on the
     PR before merge.
   - The executor MUST NOT self-certify and merge a Tier-2 PR.

## Enforcement

Soft (in effect): this policy is referenced from `AGENTS.md` (Git And PR Workflow) and recorded as a durable executor
memory note, so the executor consults it and pauses on Tier-2 PRs.

Hard (mechanical): the `SEC XBRL Tier-2 review gate` workflow (`.github/workflows/sec-xbrl-tier2-gate.yml`) fails a PR
that changes a path-detectable Tier-2 surface (Alembic migrations, `backend/app/models/models.py`, or
`backend/app/services/*` persistence/durable/archive services) unless the PR carries the
`tier2-independent-review-recorded` label, applied only
after an independent pre-merge review is recorded. The gate becomes blocking once branch protection on `main` is
configured to REQUIRE the `tier2-review-gate` check (an operator/GitHub-admin action). Value-reveal, default-on, and
redaction-posture changes are not reliably path-detectable and remain soft-governed by this policy and AGENTS.md.

## Disposition recording

When the bot is silent at merge time, record a tracking issue following the #2004 / #2008 / #2009 pattern: the opening
body states the bot did not post; the closing comment records the verifier disposition (independent review for
Tier 2; executor self-verification for Tier 1) and explicitly does NOT claim a bot review.

## Non-goals

Process governance only. No code, runtime, schema, persistence, value-reveal, default-on, or redaction-posture
changes. Default-off and validate-only postures are unaffected by this document.
