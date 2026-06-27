# A8 SEC XBRL Readiness Gate

Milestone: `M-A8-LIFECYCLE-DESIGN`

Status: checklist-only owner gate for any future A8 value-reveal implementation.
This document changes no runtime behavior and authorizes no reveal.

## Gate Decision

A8 value reveal remains not owner-authorized until every item below is true.
If any item is false or unverified, the only allowed outcome is blocked/no-op.

## Required Before Implementation

1. Live authority is refreshed and pinned.
   - `project6-origin/main` must be fetched by an operator-authorized network
     step, and the implementation branch must start from that live ref.
   - Any parallel A7 proof branch must be merged or explicitly excluded by the
     owner before A8 code touches value-reveal authority.

2. Current default-off posture is still source-confirmed.
   - `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED=false`,
     `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED=false`, and
     `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED=false` remain the
     shipped defaults (`backend/app/core/config.py:152-175`).
   - The support matrix still pins those flags false and classifies value
     reveal/internal value store/controlled submit as `experimental_default_off`
     (`config/support_matrix.yaml:8-18`, `config/support_matrix.yaml:52-64`).

3. Design approval exists for the raw-at-rest lifecycle.
   - The approved design must include states from redacted authority through raw
     creation, quarantine, secure erasure, and blocked-erasure remediation.
   - It must explicitly resolve historical planning drift such as the
     non-authoritative default-on language reconciled by `1360-posture-reconcile.md`
     (`next_milestone_plans/Layer3_planning_docs/1360-posture-reconcile.md:37-64`).

4. Storage isolation is implemented before raw values can be created.
   - Raw values must live outside the repo, outside OneDrive/cloud-sync roots,
     outside `settings.storage_dir` static exposure, and outside any committed or
     generated artifact tree.
   - Each reveal gets an isolated namespace with no shared mutable raw-value
     files across datasets.
   - Status/audit artifacts store only hashes, counts, state, policy ids, actor
     hashes, and tombstones.

5. A supported secure-erasure backend is implemented and preflighted.
   - `crypto_erase` is the preferred backend for Windows/SSD/cloud-sync
     uncertainty.
   - `overwrite_unlink` is allowed only for a local backend that can verify direct
     overwrite semantics and path absence.
   - Quarantine-only movement never satisfies this gate. Current H6 moves files
     and writes a manifest (`tools/sec-h6-quarantine.py:348-357`), so it is
     containment evidence only.

6. Erasure audit and replay are implemented.
   - Erasure receipts include schema id, transition state, policy id, authority
     hashes, value inventory hash, byte count, backend id, verification result,
     actor hash, and timestamp.
   - Repeating a completed erasure is idempotent.
   - Conflicting replay, partial erase, unverifiable erase, missing backend, or
     stale authority produces `erasure_blocked` and does not return values.

7. Reveal remains explicit and owner-bound.
   - Requests require authenticated operator identity, explicit
     `operator_reveal_confirmation=True`, current authority hash, and server
     resolution of sidecar/dataset/value-store lineage.
   - Browser/client requests do not supply raw sidecar ids, paths, URLs,
     accessions, CIKs, local storage, source acquisition, Arelle, delivery, or
     default-on fields.

8. Redaction and audit boundaries are preserved.
   - Audit/status receipts do not persist raw values or raw identity. The legacy
     Arelle receipt already has this posture (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:595-597`,
     `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:652-668`).
   - Identity-like values remain suppressed even on the explicit reveal path.
   - No raw SEC URLs, local paths, storage roots, accessions, tickers, contacts,
     proxy headers, credentials, or operator text enter committed artifacts.

9. H6 quarantine tooling is either upgraded or explicitly scoped.
   - If H6 remains quarantine-only, A8 must not call it a secure-erasure tool.
   - If H6 becomes part of A8, it needs new implementation and tests for
     erasure backend selection, overwrite/crypto-erasure verification, tombstone
     receipts, idempotent replay, and blocked partial failure.
   - Current additive tests should continue proving dry-run/no-mutation,
     confirmation refusal, storage-root isolation refusal, target collision
     refusal, and move-only/non-erasure behavior.

10. Verification is complete before owner authorization.
    - Focused unit tests cover lifecycle transitions, raw-store isolation,
      erasure backend preflight, erasure success, erasure failure, replay, stale
      authority, redaction, and status projection.
    - Integration tests use isolated runtime state and retained/offline evidence.
    - No live SEC egress, taxonomy download, Arelle run, or value reveal occurs
      unless the owner explicitly authorizes that separate proof.
    - `git diff --check`, focused pytest, SEC XBRL redaction scans, and the
      support-matrix/runtime posture checks pass.

11. Tier-2 governance is satisfied.
    - Any implementation touching value reveal, revealed-value handling,
      persistence, defaults, schema, or redaction posture is Tier 2 under the
      active policy (`next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:34-37`,
      `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:55-68`).
    - The PR must record exact Tier-2 surfaces, rollback/containment notes,
      focused verification, and independent review or an explicit owner-approved
      self-verification rationale.

## Owner Authorization Rule

The owner may authorize A8 implementation only after the checklist is complete
and the selected implementation packet says exactly which gate items are being
implemented. Authorization to design does not authorize value reveal, raw storage,
secure erasure, flag changes, live SEC egress, Arelle execution, or PR merge.
