# A8 SEC XBRL Readiness Gate

Milestone: `M-A8-DESIGN-COMPLETE`

Status: readiness-completeness owner gate for any future A8 value-reveal
implementation. This document changes no runtime behavior and authorizes no
reveal.

Authority note: this design-completion pass refreshed `project6-origin/main` to
`525993c721cad0e1349105f7502271c2be4ae996` and rebased the A8 design branch on
that authority. Any future implementation pass must refresh live authority again
before it edits runtime code.

## Gate Decision

A8 value reveal remains not owner-authorized until every item below is true.
If any item is false or unverified, the only allowed outcome is blocked/no-op.
Each item is independently checkable: the future implementation packet must
record the acceptance criterion, evidence, and fail-closed outcome for every item
before owner authorization.

## Required Before Implementation

1. Live authority is refreshed and pinned.
   - `project6-origin/main` must be fetched by an operator-authorized network
     step, and the implementation branch must start from that live ref.
   - Any parallel A7 proof branch must be merged or explicitly excluded by the
     owner before A8 code touches value-reveal authority.
   - Acceptance criterion: the implementation packet records the fetched
     `project6-origin/main` SHA, implementation branch `HEAD`, branch ancestry
     relative to main, and the decision on every parallel A7 proof lane.
   - Evidence required: `git fetch project6-origin main --prune`,
     `git rev-parse project6-origin/main`, `git rev-parse HEAD`, and
     `git rev-list --left-right --count project6-origin/main...HEAD`.
   - Fails closed when: live main cannot be fetched, branch ancestry is unclear,
     a parallel owner lane may collide, or an A7 proof claim is carried forward
     without live merge/exclusion evidence.

2. Current default-off posture is still source-confirmed.
   - `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED=false`,
     `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED=false`, and
     `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED=false` remain the
     shipped defaults (`backend/app/core/config.py:152-175`).
   - The support matrix still pins those flags false and classifies value
     reveal/internal value store/controlled submit as `experimental_default_off`
     (`config/support_matrix.yaml:8-18`, `config/support_matrix.yaml:52-64`).
   - Acceptance criterion: source defaults and support-matrix posture both prove
     value reveal, internal value store, and controlled submit remain
     default-off unless an owner-approved Tier-2 implementation explicitly
     changes them.
   - Evidence required: line-cited reads of `backend/app/core/config.py` and
     `config/support_matrix.yaml`, plus a focused test or script that asserts the
     default-off posture when runtime settings are constructed.
   - Fails closed when: any flag defaults on, support-matrix posture drifts, or
     runtime setting construction contradicts the source reads.

3. Design approval exists for the raw-at-rest lifecycle.
   - The approved design must include states from redacted authority through raw
     creation, quarantine, secure erasure, and blocked-erasure remediation.
   - It must explicitly resolve historical planning drift such as the
     non-authoritative default-on language reconciled by `1360-posture-reconcile.md`
     (`next_milestone_plans/Layer3_planning_docs/1360-posture-reconcile.md:37-64`).
   - Acceptance criterion: the approved design names every lifecycle state,
     transition authority, invariant, redaction posture, audit/replay rule,
     failure transition, and non-admission before runtime code is modified.
   - Evidence required: owner-approved `a8-lifecycle-design.md` revision with
     B1-B8 coverage and a PR body that states the change is design-only or
     separately identifies Tier-2 implementation surfaces.
   - Fails closed when: the state machine omits raw creation, erasure, blocked
     remediation, replay/idempotency, redaction posture, or historical posture
     reconciliation.

4. Storage isolation is implemented before raw values can be created.
   - Raw values must live outside the repo, outside OneDrive/cloud-sync roots,
     outside `settings.storage_dir` static exposure, and outside any committed or
     generated artifact tree.
   - Each reveal gets an isolated namespace with no shared mutable raw-value
     files across datasets.
   - Status/audit artifacts store only hashes, counts, state, policy ids, actor
     hashes, and tombstones.
   - Acceptance criterion: raw-value creation is impossible until storage
     preflight proves an isolated namespace outside repo, OneDrive/cloud sync,
     static delivery, committed artifacts, and operator Downloads stores.
   - Evidence required: unit tests for accepted and rejected storage roots,
     namespace isolation, status/audit redaction, and absence of raw paths/values
     from receipts.
   - Fails closed when: storage root is repo-relative, cloud-synced,
     static-served, shared across datasets, permission-broad, or projected into
     status/audit.

5. A supported secure-erasure backend is implemented and preflighted.
   - `crypto_erase` is the preferred backend for Windows/SSD/cloud-sync
     uncertainty.
   - `overwrite_unlink` is allowed only for a local backend that can verify direct
     overwrite semantics and path absence.
   - Quarantine-only movement never satisfies this gate. Current H6 moves files
     and writes a manifest (`tools/sec-h6-quarantine.py:348-357`), so it is
     containment evidence only.
   - Acceptance criterion: reveal is blocked unless configured storage reports a
     supported erasure backend, backend health, and a verification method before
     any A8 raw-at-rest material is created.
   - Evidence required: backend-interface tests for `crypto_erase`,
     `overwrite_unlink` eligibility, unsupported backend refusal, missing backend
     refusal, and quarantine-only non-qualification.
   - Fails closed when: erasure support is absent, unverifiable, cloud-sync
     unsafe, permission-denied, overwrite-ineligible, or represented only by H6
     quarantine movement.

6. Erasure audit and replay are implemented.
   - Erasure receipts include schema id, transition state, policy id, authority
     hashes, value inventory hash, byte count, backend id, verification result,
     actor hash, and timestamp.
   - Repeating a completed erasure is idempotent.
   - Conflicting replay, partial erase, unverifiable erase, missing backend, or
     stale authority produces `erasure_blocked` and does not return values.
   - Acceptance criterion: every erasure transition writes an immutable receipt
     that can be replayed without re-revealing values, and any conflicting replay
     enters or remains in a fail-closed blocked state.
   - Evidence required: tests for successful erasure replay, duplicate replay,
     conflicting replay, stale authority, partial erase, missing backend, and
     unverifiable erase, plus receipt-shape assertions that raw values and raw
     identity are absent.
   - Fails closed when: replay can mutate receipt history, erase twice with a
     different basis, infer erasure from missing files, or return raw values.

7. Reveal remains explicit and owner-bound.
   - Requests require authenticated operator identity, explicit
     `operator_reveal_confirmation=True`, current authority hash, and server
     resolution of sidecar/dataset/value-store lineage.
   - Browser/client requests do not supply raw sidecar ids, paths, URLs,
     accessions, CIKs, local storage, source acquisition, Arelle, delivery, or
     default-on fields.
   - Acceptance criterion: no reveal response is possible without authenticated
     owner/operator identity, explicit confirmation, current authority, and
     server-resolved lineage; client-supplied raw storage/source fields are
     rejected before authority is read.
   - Evidence required: request-validation tests for missing confirmation,
     missing actor, stale authority, unknown fields, forbidden raw/source fields,
     and lineage mismatch.
   - Fails closed when: browser payloads can select storage/source artifacts,
     bypass confirmation, reuse stale authority, or provide raw path/URL/CIK/
     accession/source-acquisition fields.

8. Redaction and audit boundaries are preserved.
   - Audit/status receipts do not persist raw values or raw identity. The legacy
     Arelle receipt already has this posture (`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:595-597`,
     `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:652-668`).
   - Identity-like values remain suppressed even on the explicit reveal path.
   - No raw SEC URLs, local paths, storage roots, accessions, tickers, contacts,
     proxy headers, credentials, or operator text enter committed artifacts.
   - Acceptance criterion: every state projection has an explicit redaction
     posture and tests prove audit/status/log/receipt paths remain hash/count/
     tombstone-only outside the approved reveal response.
   - Evidence required: redaction tests over status, audit receipt, erasure
     receipt, failure receipt, replay response, logs if captured, and committed
     fixture artifacts.
   - Fails closed when: raw value, raw identity, path, storage root, SEC URL,
     accession, CIK, credential, contact, proxy header, or free-form operator
     text reaches durable audit/status/artifact surfaces.

9. H6 quarantine tooling is either upgraded or explicitly scoped.
   - If H6 remains quarantine-only, A8 must not call it a secure-erasure tool.
   - If H6 becomes part of A8, it needs new implementation and tests for
     erasure backend selection, overwrite/crypto-erasure verification, tombstone
     receipts, idempotent replay, and blocked partial failure.
   - Current additive tests should continue proving dry-run/no-mutation,
     confirmation refusal, storage-root isolation refusal, target collision
     refusal, and move-only/non-erasure behavior.
   - Acceptance criterion: A8 implementation either excludes H6 from secure
     erasure or upgrades it under Tier-2 governance with backend-specific erasure
     receipts and blocked-failure tests.
   - Evidence required: continued H6 tests for dry-run zero mutation,
     confirmation refusals, storage-root refusal, archive-collision refusal, and
     move-only/non-erasure posture; if upgraded, additional secure-erasure tests
     and policy notes are required.
   - Fails closed when: H6 movement is described as secure erasure, H6 archive
     bytes remain readable while the lifecycle claims erased, or A8 depends on H6
     without backend verification.

10. Verification is complete before owner authorization.
    - Focused unit tests cover lifecycle transitions, raw-store isolation,
      erasure backend preflight, erasure success, erasure failure, replay, stale
      authority, redaction, and status projection.
    - Integration tests use isolated runtime state and retained/offline evidence.
    - No live SEC egress, taxonomy download, Arelle run, or value reveal occurs
      unless the owner explicitly authorizes that separate proof.
    - `git diff --check`, focused pytest, SEC XBRL redaction scans, and the
      support-matrix/runtime posture checks pass.
    - Acceptance criterion: the implementation PR includes focused tests for
      every changed runtime surface, proves isolated/offline state, records
      commands and outputs, and keeps validate actions validate-only.
    - Evidence required: exact pytest commands, redaction/support-matrix checks,
      `git diff --check`, CI links, and a note that no live SEC/taxonomy/Arelle/
      value-reveal/operator-store access occurred unless separately authorized.
    - Fails closed when: tests seed shared state, rely on operator Downloads,
      require live SEC/Arelle network, generate artifacts during validate-only
      steps, omit a changed surface, or leave CI red.

11. Tier-2 governance is satisfied.
    - Any implementation touching value reveal, revealed-value handling,
      persistence, defaults, schema, or redaction posture is Tier 2 under the
      active policy (`next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:34-37`,
      `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md:55-68`).
    - The PR must record exact Tier-2 surfaces, rollback/containment notes,
      focused verification, and independent review or an explicit owner-approved
      self-verification rationale.
    - Acceptance criterion: any runtime implementation PR identifies whether it
      touches Tier-2 surfaces and records rollback/containment, verification,
      review posture, and owner authorization before merge.
    - Evidence required: PR body and closeout report listing exact files,
      affected governance surfaces, risk triggers, rollback/containment notes,
      independent review status or explicit self-verification rationale, and CI
      status.
    - Fails closed when: Tier-2 surfaces are ambiguous, review/owner posture is
      missing, rollback/containment notes are absent, CI fails, or a design-only
      PR accidentally changes runtime value reveal, erasure, flags, schema,
      persistence, redaction posture, A7 proof surfaces, or workflows.

## Owner Authorization Rule

The owner may authorize A8 implementation only after the checklist is complete
and the selected implementation packet says exactly which gate items are being
implemented. Authorization to design does not authorize value reveal, raw storage,
secure erasure, flag changes, live SEC egress, Arelle execution, A7 proof-surface
changes, operator Downloads-store access, or PR merge.
