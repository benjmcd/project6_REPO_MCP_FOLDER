# Reconciliation: issue #2010 (stricter gate) vs SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md (canonical)

Status: reconciliation record (process only; no code, runtime, schema, or redaction-posture impact).
Scope: resolves the standing contradiction between GitHub issue #2010's go-forward gate language and the canonical SEC XBRL merge-gate policy. Records the recommended resolution and the single owner action required to enact it.

## The contradiction
Two artifacts give conflicting merge-gate rules for SEC XBRL Layer 3 PRs:

1. **Issue #2010 (stricter).** Its body's "go-forward gate reminder" requires *independent verifier review recorded plus CI green before merge* for **all** SEC XBRL PRs, with no tier distinction. Its first comment adds that any PR touching schema, durable persistence, `models.py`, Alembic, runtime defaults, value reveal, redaction posture, or API/UI/operator workflow is Tier 2 and **"must stop for independent pre-merge review"** — i.e. a hard blocker with no executor self-certification path. Issue state: OPEN.

2. **`SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md` (canonical, softer).** Established 2026-05-31 as a deliberate "right-sized governance" response to the same connector-outage root cause that prompted #2010. It defines an explicit Tier 1 / Tier 2 distinction: bot silence is not a blocker; executor self-verification satisfies the Tier 1 record; for Tier 2, independent review is *sought when practical* or when a concrete risk trigger is present, and if not obtained the executor records why self-verification is adequate and what would force a follow-up. Merge is blocked only by failed required checks, unresolved critical/blocking findings, missing rollback/containment notes for schema/persistence changes, unclear authority, or an explicit operator instruction requiring review.

The contradiction is mirrored wherever the canonical policy is cited as authoritative: `AGENTS.md` (the SEC XBRL merge-gate paragraph) and the Layer 3 planning docs `1286-*`, `1288-*`, `1290-*`, `1329-*` all restate the softer "sought when practical" Tier-2 rule. None of these restate #2010's blanket "must stop." So the divergence is entirely between issue #2010 and the canonical policy (plus its faithful citations); **no product/code/config file encodes the merge gate**, so reconciliation is doc/process-only.

## Recommended resolution — Option A: #2010's go-forward language is superseded by the canonical policy
Rationale (Talmudic, converged):
- **Authority by form, scope, and date.** The policy doc is a purpose-built, dated (2026-05-31) governance artifact that post-dates #2010's informal inline note and governs exactly this subject matter with explicit tier logic. #2010 frames itself as an "Admin follow-up" to an outage, not a policy amendment.
- **Coherence.** Adopting #2010's blanket "independent review for all SEC XBRL PRs" would erase the Tier 1/Tier 2 distinction the policy was specifically designed to provide, and would retroactively reclassify prior Tier-1-only merges (e.g. #2003/#2005/#2006, dispositioned under #2004/#2008/#2009 consistent with the softer policy) as having merged without a now-required review — reopening settled dispositions for no safety gain.
- **No drift.** `AGENTS.md` and the `1286/1288/1290/1329` planning docs already state the canonical softer policy correctly, so **no edits to any policy/agent/planning doc are required** to enact Option A. The only live inconsistency is the OPEN issue #2010 carrying contradictory go-forward language with no expiry.

Rejected — Option B (adopt #2010's stricter gate as canonical): contradicts the policy doc's explicit intent, imposes a blanket gate the policy already rejected as disproportionate, forces edits to the policy + `AGENTS.md` + four planning docs, and reopens retroactive exposure on prior dispositions. Less coherent; not recommended.

## Owner action required (single step — reserved to the owner)
Enacting Option A is one outward GitHub action, queued here rather than performed unilaterally because it resolves a governance-posture question:

1. Post this closing comment on issue #2010, then close it:

   > Superseded. The SEC XBRL merge gate is governed by `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md` (established 2026-05-31), a purpose-built policy that post-dates this issue and defines explicit Tier 1 / Tier 2 handling: executor self-verification satisfies the Tier 1 record; Tier 2 seeks independent review when practical or on a concrete risk trigger, recording rationale otherwise. The go-forward "independent review for all SEC XBRL PRs / Tier-2 must stop" language in this issue's body and first comment is superseded by that policy. Prior Tier-1 PRs (#2003/#2005/#2006) were dispositioned consistently with the canonical policy. Closing as superseded; reopen if the canonical policy itself should be made stricter.

No code, policy-doc, `AGENTS.md`, or planning-doc change is needed. If the owner instead prefers Option B, that is a separate decision that would amend the canonical policy and is out of scope for this reconciliation record.
