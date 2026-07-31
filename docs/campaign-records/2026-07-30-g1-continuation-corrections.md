# G1 continuation — corrections + adversarial-check disposition (2026-07-30)

Fable adversarial check (session 91b270df): **BUILD-HONEST-AND-CORRECT**. Every falsifiable headline
reproduced exactly (V1 193, S4 154/0-skip self-enforcing, capture+evaluator 90, gate 71, V3 30,
test_layer3_api 327, pilot 22, V8 exit 0). Both STOPs GENUINE — no regression hidden, no evasion.
Scope clean: frozen docs untouched ec506fe7..75460571; the c7b47543..75460571 spec delta is exactly
the one documented S3 amendment 4130d44b (not drift); state/agent-inbox untouched; no push; gate
inert/fail-closed (every exit path returns 2, network syscalls denied, no DB/settings dependency).

## CORRECTION — B1a final source blob (report Finding 1, MAJOR)
The continuation report says the B1a-sealed source's "final source blob is now
3e46ccf88a0cf0329cf1be075d8fa073ac2d33cf". THAT IS WRONG — 3e46ccf8 is the blob of a DIFFERENT file
(backend/app/services/layer3_origin_continuity.py at 75460571). The B1a seal binds
backend/tests/test_layer3_connector_source_intake_pilot.py. Independently verified (read-only git):
- old seal blob b8a89df2… = pilot at c7b47543 AND at build base ec506fe7 (unchanged).
- TRUE final pilot blob at build HEAD 75460571 = **8ec90984fc01d1290f72a56109b26564505056d4**.
Any B1a reseal must bind 8ec90984, NEVER 3e46ccf8. (Self-revealing error — a wrong reseal fails the
next B1a run — but corrected here before any owner ballot.)

## Report-accuracy notes (minor, non-blocking)
- Header "Tasks 1-8 built+tested" overstates Task 8B: dual_live_evaluator.py is a ~70-line
  static-INDETERMINATE SCAFFOLD (honestly described in the body + authorized as "Tasks 7-8
  scaffolding" in the S3 decision record). The FULL Task-8 evaluator (frozen 2247-2445) remains
  open work, much offline-executable. Do NOT count Task 8 spec-complete.
- The 48 broad-suite failures were BUILD-INTRODUCED by authorized Tasks 6-7 (over-broad reserved-
  marker detection rejecting legacy shapes) then fixed in 75460571 — a normal stabilization loop,
  disclosed in the body; not churn concealment, nothing weakened (legacy surface verified green:
  327 + 164 + 22 pilot).
- "Independent" reviews = same-session Codex subagents (self-review, not external); test evidence
  was reproduced independently by the Fable check, so it stands regardless.
- Open records-convention question: the `source-sha256` self-hash lines in the G1 records do not
  reproduce from committed bytes (likely hashing an out-of-repo artifact) — cosmetic, flagged.

## Disposition
Clause-5 wiring: STOP was CORRECT (unconditional 409 raise at connector_egress_arming.py:900-904;
clauses 1-4 fully built; clearance postdated the build). NOW AUTHORIZED (f7393131). B1a STOP: CORRECT
governance (seal binds an externally-attested object; authorized Tasks 1-7 legitimately changed the
pilot bytes; Codex refused to self-update the external seal). Owner decides the B1a proof-object.
