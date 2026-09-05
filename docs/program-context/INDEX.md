# Program Context — Index and Conventions

> **2026-09-04 current pointer:** This exhaustive set contains exactly six
> tracked files: this index plus the five numbered records below. The current
> cross-record summary is
> [docs/MASTER_CONTEXT.md](../MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).
> No seventh program-context file is required. Historical entries remain dated
> evidence; current runtime claims must still be revalidated against source.

Destination: `docs/program-context/`. This six-file set is the exhaustive program record for the
SEC-XBRL Layer 3 value-retention/reveal campaign and its successors: what was accomplished,
why each decision was made, what comes next, and under what acceptance criteria.
`docs/MASTER_CONTEXT.md` remains the executive summary; where the two disagree, the more
recently dated entry governs and the older one must receive a supersession note.

## Files

| File | Contents |
|---|---|
| `00-posture-and-invariants.md` | The governing posture: every standing rail, with the reasoning that justifies it and the code/doc that enforces it |
| `01-arc-ledger.md` | Chronological accomplishment ledger: every tranche, PR, SHA, operator proof — what it did and why it was the right move at that point |
| `02-decision-record.md` | ADR-style record of every significant decision: context, alternatives weighed, choice, justification, evidence, revisit-conditions |
| `03-forward-plan.md` | Every open pursuit with status, residual delta, acceptance criteria, pass/fail requirements, SHOULD-NOTs, owner gates, and sequencing |
| `04-evidence-registry.md` | Every load-bearing hash, count, receipt id, PR/SHA, and where it lives — the verification anchor table |

## Authority order (inherits repo convention)

1. Live `project6-origin/main` + actual source/tests/CI.
2. This set and `docs/MASTER_CONTEXT.md` (dated entries; newest governs).
3. `next_milestone_plans/` planning docs and the progress board (mixed historical ledger —
   read per its own supersession rules).
4. Session exports / operator sandbox artifacts: evidence of what happened, never current
   implementation truth without revalidation.

## Maintenance protocol

- Update trigger: any merged tranche, any operator proof, any owner decision, any posture
  change. The updating lane appends/supersedes — it never rewrites history entries.
- Supersession convention: prepend a dated status block; do not delete prior text
  (lesson: the progress board's mixed-ledger ambiguity cost multiple audit cycles).
- Redaction rule (absolute): no raw retained values, no operator identity/contact, no
  local paths other than the intentionally-public canonical root `C:/p6store`, no SEC URLs
  or issuer/accession payloads. Evidence enters as SHA-256 hashes, counts, policy ids,
  receipt-id hashes, and reason codes only.
- Tier: updates to this set are Tier-1 docs lanes (self-merge on green CI with bot review
  threads resolved) unless a change re-states runtime/admission semantics, in which case the
  lane must stop and classify.
- Verification duty: every factual claim added must carry a committed or re-derivable anchor
  (PR number, merge SHA, file:line, report/store hash, or committed docs/manifests) that a
  later agent can re-derive without this set's author being present.

## Reading order for a new agent/session

`00` (what must never be violated) -> `01` (what exists) -> `02` (why it is shaped this way)
-> `03` (what to do next) -> `04` (how to verify any of it). Then
`docs/OPERATOR_UTILIZATION_INDEX.md` for how to actually run things.
