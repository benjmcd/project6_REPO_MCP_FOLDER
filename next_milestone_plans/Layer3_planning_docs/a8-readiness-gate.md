# A8 SEC XBRL Retention Readiness Gate

Milestone: `M-A8-RETENTION-REDESIGN`

Status: readiness-completeness owner gate for future A8 durable value retention.
This document changes no runtime behavior and authorizes no reveal.

Authority note: this redesign pass refreshed `project6-origin/main` to
`c96ea5154dd13a0724d74f8979bb28651d667cb8` and rebased the A8 branch onto that
authority. Any future implementation pass must refresh live authority again
before runtime edits.

## Gate Decision

A8 implementation remains not owner-authorized until every item below is true.
If any item is false or unverified, the only allowed outcome is blocked/no-op.
The gate is retention-first: public SEC EDGAR financial values are retained
as product data, while operator identity and operational secrets remain redacted
from audit/status and request authority.

## Required Before Implementation

1. Live authority and posture are refreshed and pinned.
   - `project6-origin/main` must be fetched by an operator-authorized Git step,
     and the implementation branch must start from that live ref.
   - Current posture must state that SEC EDGAR financial values are retained and
     operator identity, paths, URLs, tokens, proxy headers, tenant/workspace
     values, provider/connector secrets, and artifact bytes are redacted from
     audit/status/request authority.
   - Feature flags for value reveal, internal value store, and controlled submit
     remain default-off until a separate owner-approved Tier-2 implementation.
   - Acceptance criterion: the packet records fetched main SHA, branch `HEAD`,
     branch ancestry, current flag defaults, support-matrix posture, and the
     value-retained/identity-redacted boundary.
   - Evidence required: `git fetch project6-origin main --prune`,
     `git rev-parse project6-origin/main`, `git rev-list --left-right --count
     project6-origin/main...HEAD`, source reads of `backend/app/core/config.py`,
     `config/support_matrix.yaml`, and the cited redaction/public-value docs.
   - Fails closed when: main cannot be refreshed, branch ancestry is unclear,
     flags default on without owner authorization, or the packet treats public
     financial values as the redaction target instead of operator/operational
     authority material.

2. Durable value-store design is owner-approved.
   - The approved design must name the internal value store as the durable
     endpoint for public SEC financial values.
   - The design must identify value-store hash, value count, value semantics,
     sidecar lineage, dataset hash where applicable, and receipt/state metadata.
   - Acceptance criterion: the implementation packet points to an approved A8
     design that retains public financial values durably and keeps audit/status
     projections identity/secret/path/token redacted.
   - Evidence required: owner-approved `a8-lifecycle-design.md`, source reads of
     sidecar internal value-store write/read paths, and focused tests for store
     hash/count/lineage invariants.
   - Fails closed when: the store is framed as a liability instead of product
     data, values are excluded from the retained store, lineage/hash/count semantics are missing,
     or a runtime implementation starts without owner approval.

3. Storage hygiene is implemented before retained values can be written.
   - Retained value storage must use an isolated namespace outside the repo,
     outside OneDrive/cloud-sync roots, outside static delivery, outside git-
     committed/generated artifact trees, and outside operator Downloads stores.
   - Hygiene protects durability, reproducibility, and operational boundaries; it
     is not a claim that public financial values are confidential.
   - Acceptance criterion: store preflight proves the namespace is isolated,
     durable, not static-served, not git-committed, and not cloud-sync/shared in a
     way that breaks authority or reproducibility.
   - Evidence required: focused tests for accepted/rejected storage roots,
     namespace isolation, missing/unreadable store failure, and status/audit
     absence of local paths/storage roots.
   - Fails closed when: storage is repo-relative, OneDrive/cloud-synced,
     static-served, committed, shared across authorities, permission-broad, or
     projected into audit/status as a raw path/root.

4. Reveal request binding is explicit and server-owned.
   - Operator-visible display/submit requires authenticated operator identity,
     explicit confirmation, current authority hash, and server-resolved
     sidecar/dataset/value-store lineage.
   - Client requests must not supply raw paths, URLs, source-acquisition fields,
     CIK/accession/source identity, local storage roots, Arelle execution fields,
     connector dispatch fields, proxy headers, credentials, or operator contact
     fields.
   - Acceptance criterion: display/submit is impossible unless server-side
     authority resolution and explicit operator confirmation both pass.
   - Evidence required: request validation tests for missing confirmation,
     stale authority, forbidden fields, unknown fields, missing value store,
     lineage mismatch, and idempotent replay.
   - Fails closed when: browser/client payloads can select source/storage
     authority, bypass confirmation, reuse stale authority, or inject raw/local
     operational fields.

5. Audit/status redaction preserves identity and operational secrecy while values
   remain retained in the store.
   - Audit/status receipts may expose hashes, counts, policy ids, state,
     authority lineage, timestamps, and blocked reason codes.
   - Audit/status receipts must not expose raw operator identity, raw actor text
     unless explicitly hashed, tenant/workspace values, proxy headers, tokens,
     local paths, raw URLs, storage roots, credentials, provider/connector
     secrets, artifact bytes, or operational contact strings.
   - Acceptance criterion: tests prove public values are retained in the durable
     store, while audit/status/request authority surfaces stay identity/secret/
     path/token redacted.
   - Evidence required: receipt/status/projection tests, redaction scans over
     committed fixtures, and value-store assertions that values remain present in
     the governed store.
   - Fails closed when: audit/status duplicate public values unnecessarily,
     operational identity or secrets leak, or value-store retention is weakened
     into audit-only hash/count records.

6. Verification is complete before owner authorization.
   - Focused unit tests cover retention states, store hygiene, hash/count/lineage
     integrity, request binding, idempotency, redaction boundary, failure states,
     and status projection.
   - Validation uses isolated/offline runtime state and does not fetch SEC data,
     run Arelle, download taxonomies, reveal values, mutate shared operator
     stores, or generate artifacts during validate-only steps unless separately
     authorized.
   - Acceptance criterion: the implementation PR records exact commands and CI
     links, all focused tests pass, `git diff --check` is clean, and GitHub CI is
     green.
   - Evidence required: exact pytest commands, `git diff --check`, redaction/
     posture checks, and PR check results.
   - Fails closed when: tests rely on shared seeded state, operator Downloads,
     live SEC/taxonomy/Arelle/runtime network, generated artifacts, omitted
     changed surfaces, or red CI.

7. Tier-2 governance is satisfied for any runtime implementation.
   - Any future implementation touching value reveal, retained value handling,
     persistence, defaults, schema/model/migration, route behavior, or redaction
     posture is Tier 2 under the active policy.
   - The PR must record exact Tier-2 surfaces, rollback/containment notes,
     focused verification, review posture, and owner authorization before merge.
   - Acceptance criterion: the implementation PR clearly identifies whether it
     touches Tier-2 surfaces and records rollback, containment, verification,
     review, and owner posture.
   - Evidence required: PR body and closeout report listing exact files,
     governance surfaces, risk triggers, rollback/containment notes, independent
     review status or owner-approved self-verification rationale, and CI status.
    - Fails closed when: Tier-2 surfaces are ambiguous, owner/review posture is
      missing, rollback/containment notes are absent, CI fails, or a planning PR
      accidentally changes runtime value reveal, flags, persistence, redaction
      posture, A7 proof surfaces, or workflows.

## Tier-2 Implementation Guard Addendum

1. Durable value-store retention policy cannot imply value-store deletion.
   - Any future A8 implementation must replace the sidecar internal value-store
     `tied_to_sidecar_receipt_lifecycle` label in diagnostics and persisted
     store metadata with `sec_xbrl_public_financial_value_retention_v1`.
   - The implementation must include a source/test guard that no value-store
     deletion path is added to honor the old lifecycle-tied label.
   - The allowed rollback posture is containment by default-off flags,
     fail-closed readers, and commit revert; rollback must not remove retained
     public SEC financial values from the durable store.

## Conditional Future Source-Class Caveat

A future non-public, licensed, paid-vendor, contractual, or no-retention source
class would need a separate source-class policy and owner-approved governance
before runtime work. That future source class is out of scope for SEC EDGAR A8.
SEC EDGAR financial values are public government disclosures and belong in the
retained product value store.

## Owner Authorization Rule

The owner may authorize A8 implementation only after this gate is complete and
the selected implementation packet states exactly which gate items are being
implemented. Authorization to design does not authorize runtime value reveal,
internal value-store flag flips, controlled-submit flag flips, schema/model/
migration work, route changes, rendered UI changes, live SEC egress, taxonomy
download, Arelle execution, A7 proof-surface changes, workflow changes, operator
Downloads-store access, or PR merge.
