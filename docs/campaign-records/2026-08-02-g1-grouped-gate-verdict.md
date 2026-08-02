# G1->G2 grouped architecture/security gate — verdict (2026-08-02)

The frozen G-structure's integrated G1->G2 gate over the WHOLE offline substrate (Tasks 1-8 + controls),
assessed as one architecture + one attack surface (8-agent workflow: 3 Sonnet scouts -> 3 Opus assessors
-> Opus synthesis -> Fable gate). Builds ON the already-ACCEPTED per-tranche results (clause-5, B1a,
Task-8), value-add = integration + system-level lens. Binds to HEAD ~cf57de58, frozen plan 68f740af +
B1a seal b8a89df2 byte-untouched.

## VERDICT: G1-PASS-WITH-CONDITIONS — advance to G2 PREPARATION (NOT a live-run authorization)
G1 is sound as an integrated system, ZERO blockers: tranches compose correctly end-to-end
(Phase-A -> quiescence/authority-clear -> secret-free Phase-B -> seal -> evaluator/gate), invariants
enforced redundantly at 3+ layers; security-sound at the acceptance boundary (exact-registry,
INDETERMINATE>FAIL>PASS fail-closed evaluator; no cross-tranche false-PASS / privilege-escalation /
evidence-forgery path found within the disclosed threat model). The 13.5k-line runtime/windows pair is
adjudicated LOAD-BEARING (Win32 job-object/TCP-census/ACL/reparse/mutex primitives, no stdlib equivalent)
— per ceiling-removal + anti-churn, NO proportionality-trim gate created; the over-engineering concern
resolves as legitimate.

## PROCESS-HONESTY NOTE (surfaced, being closed)
The dedicated consolidated-security lane FAILED (StructuredOutput retry cap, no output). The adjudicator
compensated with two converging lanes + disk re-verification of 4 security linchpins (fail-closed
aggregation dual_live_evaluator.py:6659-6673/6690; Python-only spawn denial nrc_aps_strict_parse.py:3-5/
70-82; HTTP execute route router.py:580; Phase-A-failure-cannot-spawn-Phase-B dual_live_runtime.py:
3509-3528). Condition C1 required the owner to disposition this OR commission a clean sweep. DISPOSITION
TAKEN: a dedicated consolidated-security adversarial sweep is being run to close the gap directly (results
appended). This removes the need for an owner coverage decision.

## 4 CONDITIONS (binding)
- C1 SECURITY-COVERAGE DISPOSITION: close the failed-lane gap (being closed via the commissioned sweep).
- C2 VERDICT BINDING: PASS binds to cf57de58 + frozen 68f740af + seal b8a89df2; any substrate change
  beyond G2-prereq work or the 3 enumerated rewrite cases triggers a targeted delta review of the seam
  (targeted, not full rerun, per the main-movement rule).
- C3 PREP-ONLY SCOPE: authorizes G2 PREPARATION only (host/dependency provisioning, offline fault-injection
  drills, runbook, CVE attestation, docs). NO live/credentialed acquisition, NO subscription key or
  grant/campaign files into any long-lived process, NO egress arming outside the offline harness.
- C4 NAMED-RESIDUAL CARRIAGE: 3 live-manifesting MAJOR residuals carried by name, each discharged or
  owner-accepted, never silently dropped: (i) Phase-B non-atomic durability + deterministic campaign_id
  poisoning forcing real re-acquisition on retry; (ii) hostile-native-PDF in-process parse under
  Python-only spawn denial (not an OS sandbox); (iii) shared-executor HTTP credential-containment seam
  defended at acceptance but not at physical send.

## G2 PREREQUISITE GATE (ordered; all BLOCKING except P9)
- G2-P1 Provision the live host: py3.12 (dont_write_bytecode, pycache_prefix=NUL), the exact 6-package
  requests egress stack matching pinned RECORD hashes, file-interference-quiet; fix the py3.11 doc drift.
- G2-P2 Reproduce the offline bar ON that host: test_dual_eval.py 401/401 + 3 tamper campaigns green,
  BEFORE any credential exists (converts the certified bar past its host-ineligibility nonclaim).
- G2-P3 Supply chain: one-time CVE/freshness attestation of the egress stack + the in-process PDF parser
  (PyMuPDF/MuPDF locked ver); confirm no unpinned optional requests extras in the child env.
- G2-P4 Durability demo + recovery: process-kill fault injection at each Phase-B commit boundary (offline)
  proving a Phase-B defect cannot silently force repeated REAL re-fetch; tested operator recovery runbook
  (poisoned-campaign_id cleanup, orphaned-row reconciliation, unsealed-dir archival). No atomicity-model
  change required — demonstrated behavior + recovery.
- G2-P5 Credential containment: subscription key + grant/campaign files present ONLY in the CLI
  acquisition child, never a long-lived FastAPI process; restrict/disable the strict egress-execute HTTP
  route for the live window; WRITTEN statement that the evaluator's fail-closed refusal of
  HTTP-driven/partial/duplicate runs is the INTENDED safety net for the shared-executor seam.
- G2-P6 Explicit owner acceptance of (a) the hostile-native-PDF residual (with the G2-P3 CVE result) and
  (b) the single-fsync buffered-evidence forensic-replay residual (no false-PASS impact).
- G2-P7 C1 security-coverage disposition closed (the sweep).
- G2-P8 THE G2 GATE PROPER: separate explicit owner authorization of the live run + drift check vs
  cf57de58 + byte-verify frozen 68f740af/seal b8a89df2 + confirm P1-P7 closed. Only then may a live
  credentialed acquisition execute.
- G2-P9 NON-BLOCKING hygiene (explicitly NOT a gate): reconcile impl-plan/file-map (P2 #2); clear/waive
  ~15 dual_live_windows.py ctypes mypy diagnostics (P2 #3); optional runtime-block consolidation. None
  may be promoted to a blocker.

## C1 CLOSED — dedicated consolidated security sweep (security-reviewer/opus, 2026-08-02)
VERDICT: SECURITY-SOUND-FOR-G1-GATE, risk LOW. 0 critical, 0 high, 1 medium (design-inherent), 6 low/info.
Independently re-verified all 4 adjudicator linchpins + extended across the whole surface; found nothing
the compensating lanes missed, nothing new at critical/high. The adjudicator's compensated-coverage
acceptance is JUSTIFIED. This DISCHARGES condition C1 / prerequisite G2-P7. No new binding condition.

Negative results (couldn't break it — load-bearing for a security gate):
- NO reachable egress offline/default-off: the single real socket (connector_egress_transport.py:1671-1687,
  allow_redirects=False, verify=True) is reachable only after both flags true + full grant/definition/index
  revalidation + exact host/path/query/method preflight + public-address SSRF assertion (_assert_all_addresses_public
  :1517). All 3 HTTP entries + the CLI fail closed; generic routes blocked in exclusive-proof mode.
- NO Phase-A/Phase-B credential coexistence window: authority-clear (dual_live_runtime.py:4321-4398) refuses
  unless the Phase-A child is quiesced+closed, then clears os.environ + settings authority, asserts
  all_required_absent; Phase-B env secret-free by construction (CONNECTOR_LIVE_EGRESS_ENABLED="false").
- NO false-PASS/verdict-downgrade: INDETERMINATE>FAIL>PASS exact-registry (dual_live_evaluator.py:6659-6673),
  status a constrained Literal, exceptions→INDETERMINATE, DB mode=ro + query_only + deny-authorizer; gate
  re-derives the aggregate, exit 0 only on structurally-exact all-PASS.
- NO cross-tranche forgery within the disclosed model: re-derivation at every seam, no-overwrite seals,
  cross-domain DB↔file parity. A fully coordinated cross-domain rewrite is the disclosed non-claim.
- NO hardcoded secrets; dependency provenance hard-gated (RECORD-hash verifier fail-closed).

Residual upgrade: C4-iii (shared-executor HTTP credential seam) found MORE contained than "acceptance-only"
— the subscription key is cryptographically pinned to adams-api.nrc.gov:443 at PHYSICAL send via a header
allow-list (connector_egress_evidence.py:466-503, rejects the key under credential_audience="none") + audience
equality (connector_egress_transport.py:421); the strict builder attaches the key only to ordinal-1/adams-api
and sends empty headers to www.nrc.gov. G2-P5's route-disable stays as belt-and-suspenders. C4-i (Phase-B
durability) reconfirmed an AVAILABILITY concern only (partial commit → evaluator FAIL/INDETERMINATE, never
PASS). C4-ii (hostile-PDF) + buffered-evidence residuals honest, correctly bounded.

M1 (MEDIUM, non-blocking): the gate trusts env-supplied evidence locations (tools/dual_live_gate.py:341-354);
integrity rests on the 69-check evaluator + read-only DB custody + backend content-hash chain — forging a PASS
requires a fully self-consistent bundle hashing to the configured INDEX_SHA256 = the intended proof burden.
Document in the threat model; optional owner-signed pinned manifest if the threat model expands. G1-non-blocking.
Two hardening suggestions → G2-P9 hygiene: structural phase_b_sources fail-closed wiring (dual_live_evaluator.py:3161);
document the env-driven evidence trust boundary. CVE audit (pip-audit) = G2-P3 as already planned.

**G1 IS NOW FULLY CERTIFIED — the security pillar is independent (not compensated). G1-PASS stands with C1
discharged; C2/C3/C4 remain governing; the G2 prerequisite gate (P1-P8) is unchanged.**
