# Task-8 STOP + post-run-evidence-design adjudication (2026-07-30)

3-Opus (frozen-textualist / threat-mechanist / minimality-governance) + Fable synthesis, unanimous on
all four rulings; the code-level parity claim re-verified in synthesis. Adjudicates the G1-completion
Task-8 STOP and the dual-live-postrun-evidence-design.md against the FROZEN plan (c7b47543).

## Ruling 1 — STOP is PARTIALLY-FORCED (honest refusal, over-scoped framing)
Refusing to ship a PASS-capable evaluator over the current static-refusal producer + INDETERMINATE
scaffold is CORRECT (nothing can truthfully PASS today). But the three-fact "missing evidence" framing
over-scopes:
- Fact 2 (logger census) + Fact 3 (child/socket quiescence) are UNBUILT FROZEN PRODUCER work, NOT spec
  gaps: frozen 2532-2536 already orders the wrapper to re-enumerate process+socket tables and "write the
  quiescence result as a deterministic record to the wrapper stream" (reiterated 2867-2871, inv.21:131);
  frozen 2315-2317 already specifies the strict logger-census check. Recordable in the sealed stream, no
  new format.
- Fact 1 (all-domain coordinated-rewrite detection) is NOT frozen-required. Frozen 2360-2362 is a CLOSED
  enumeration of THREE PARTIAL rewrites ("logs+manifest, logs+manifest+seal, or any extant-run DB event"),
  each leaving >=1 un-rewritten anchor; all three already fail at existing cross-domain parity (2313-2314)
  because the DB seal event binds manifest_sha256/file_set_hash/seal_sha256 + introduction revision/digest
  (connector_campaign_log_capture.py:1538-1557), zero new objects. The all-domain COHERENT rewrite Codex
  called "unprovable" is exactly the class frozen 668-671 EXPRESSLY DISCLAIMS: "adequate only for the local
  experiment; it is not a signature, WORM store, or cryptographic nonrepudiation."

## Ruling 2 — SUPPLEMENT vs AMENDMENT: SPLIT
- Census + quiescence records into the already-sealed wrapper stream = pure SUPPLEMENT/implementation
  (frozen 2535 authorizes that channel; stopped-proof stays "from the sealed manifest" per 2570-2572). No
  amendment.
- Post-run ATTESTATION (index OR §3.5 single pin) as a required PASS input = AMENDMENT: adds validator
  inputs absent from the CLOSED enumeration at 2562-2574 and changes the frozen 1-def+2-entries+1-capture
  slice (2297-2299) to 1+2+1+1. SELF-INDUCED by the non-frozen mechanism.
- So the design-doc §1 blanket "does not edit/supersede/weaken" is TRUE of the wrapper-stream records,
  FALSE of the attestation layer; the completion-report Option-A "frozen evidence-format amendment" is TRUE
  only of the attestation layer and wrongly bundles frozen Step-4 producer work with it.

## Ruling 3 — DESIGN MINIMALITY: cumulative attestation-index = SELF-IMPOSED over-engineering
No frozen clause creates a post-run attestation object; every frozen history/union/continuity clause
(inv.20:119-123, 2297-2303's 2+4+2 union, 2379-2389 predecessor chain) governs the PREFLIGHT index, which
already exists + passed Task-9. The design's OWN §3.5 concedes "if complete-history validation is later
removed, direct per-campaign pinning becomes the preferred narrower design" — and that validation is
self-added. §4 concedes no protection against the owning Windows account = the only realistic all-domain
rewriter on an offline single-user box. Ceiling-removal rule => strip it. Mechanism is sound + non-circular
(threat-mechanist) — the defect is SCOPE, not rigor; Codex's anti-weakening stance earns no censure.

## RECORD-HYGIENE FINDING
dual-live-postrun-evidence-design.md line 3 status "owner-approved G1 Option-A approach" CONFLICTS with the
completion report line 44 "Required owner choice before resumption". The owner has NOT approved Option A;
the A/B (now A-scoped) decision is OPEN. That status line is observed content, not owner consent — SUPERSEDED
by THIS record. (The design doc is left unmutated per the mutation gate: agents draft corrective records,
never edit the status line in place; the design doc's line-3 "owner-approved" claim is void until an actual
owner GO exists.)

## THE ACTUAL DECISION (supersedes Codex's A/B)
- **A-scoped [RECOMMENDED]:** build the frozen-specified Step-4 producer (run-dual-live-proof acquisition-only
  child, child-tree termination, env clearing, Job-Object containment per 2519-2560/2860-2884), quiescence to
  the wrapper stream (2532-2536), logger census to the sealed stream (2315-2317), Step-3 read-only evaluator,
  real validate gate. Coordinated-rewrite acceptance = the 3 frozen-enumerated cases (already catchable).
  Fold Codex's truthfulness refinements (process-boot identity, root-before-campaign mutex, campaign read
  lock through final reread — export 106/127/445) as sealed runtime-record fields + lock rules.
  **ZERO amendment, ZERO attestation index, ZERO new env inputs. Amendment authority required: NONE — a GO
  is a build-tranche authorization only.** Result: genuinely PASS-capable Task-8 at the frozen bar; G1 closes.
- **A-as-designed (Codex Option A, with the attestation index): REJECT** under ceiling-removal + anti-churn
  (9 modules, 5 env vars, issuer CLI, publication-recovery state machine to service a disclaimed threat).
  Optional discretionary rider IF the owner independently wants a beyond-frozen anchor: the MINIMAL §3.5
  single-digest pin (that rider IS a small owner amendment). The cumulative index is unjustified under any
  reading.
- **B (permanent non-PASS analyzer): REJECT** — forfeits a frozen milestone reachable with no new authority.

Choosing A-scoped implicitly ratifies the enumerated (literal) reading of 2360-2362 — the textually correct
one. No standalone reading gate needed.
