# S3 delta decision record — owner-delegated ruling (2026-07-30)

Owner message (session 91b270df): "Proceed as you see fit (whatever you determine to be most
adequate/optimal). Delegate/orchestrate as I have been instructing up to this point." — an explicit
delegation of the g1-owner-delta-packet decisions to the session. Provenance is disclosed here
honestly: the selections below were made BY THE SESSION under that delegation, not by direct owner
per-item ballot.

## Decision 1 (S3, the sole true frozen-contract defect): OPTION B ADOPTED
Clause 5's third equality leg re-worded from "raw SHA-256 recorded on the canonical connector-target
receipt" (a Phase-B artifact that cannot exist at the Phase-A gate) to the raw SHA-256 REHASHED from
the content-addressed NRC target blob at evaluation time (never a stored-column read). Consequential
edits: the falsification bullet (~line 845) and NrcAcquisitionSuccessEvidence field naming (~1013).
Basis: the adjudication packet's recommendation — smallest frozen-text blast radius, invariant 12
untouched (one canonical receipt, minted in Phase B), not-weaker (a fresh rehash triangulated against
two independent rederivations is stronger than reading a recorded value), and the owner's standing
anti-churn + remove-unnecessary-complexity rules. Noted: 2 of 3 Opus adjudicators leaned Option A
(split-receipt); the Fable synthesis ranked B first on the owner's own standing rules; delegation
resolves the judgment call to B. Option C stood rejected unanimously.

## Decisions 2-4: reading-confirmations RATIFIED by delegation (no frozen-text change)
- S1: "exact active lease token" = token-VALUE identity; unexpiry binds only the send/reservation
  path (plan 1284-1289); finalize-`failed` reachable post-expiry. Implementations must remove any
  stranded-running path built on the disfavored reading.
- S2-NRC: plan 1925-1927 governs linkage timing — ApsContentLinkage.blob_sha256 binds in Phase B
  against admitted bytes; acceptance bullet 1741-1742 states targets, not timing.
- S4: plan 2639 is COMMAND-level — every prescribed command must run and be recorded;
  pre-existing environment-conditional in-test skips inside a command that runs do not void the
  green claim; net-new G1 tests must not introduce skips. No text change; micro-clarification
  declined under anti-churn.

## Process
This delta commit goes to external focused review (Codex 019faa86) before any implementation builds
against the amended clause; the agent-executable substrate (ScienceBase Phase-A persistence, NRC
Phase-B linkage binding, predicate de-coupling, S4 test restructure, Tasks 7-8 scaffolding) proceeds
in parallel as it does not depend on the amended referent.

## Consequential-edit list — UPDATE (2026-07-30, per external review condition)
External delta review (Codex 019faa86, dispatch dc412968) cleared the plan amendment
CLEARED-WITH-CONDITIONS: Y1/Y2/Y3/Y5 PASS, Y4 flagged ONE surviving stale normative referent in the
frozen COMPANION doc. Additional consequential edit applied: campaign-record governance restatement
`docs/campaign-records/2026-07-29-dual-live-proof.md` (the "whose raw SHA-256 ... connector-target
receipt" leg, ~line 971) synced to the blob-rehash referent. Full amended plan+campaign pair is now
internally coherent. All other old-referent hits are historical/labeled (prior reviews, packet,
this record, the plan's [S3 delta] annotation) and remain as history.
