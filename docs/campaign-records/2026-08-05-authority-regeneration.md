# Authority regeneration bound to the landed fix (2026-08-05)

> Regeneration record. The prior authority set bound `code_revision e10bffc5…`; the live-run code was
> patched at `e53955d29c9ff3efcf17316d499f1aa6a64b58ae`. Both the campaign definition and both grants
> declare `continuation_after_code_change_not_authorized`, so the prior set carries no authority over
> the patched code. This record does not authorize a run: **G2-P8 remains a separate owner act.**
> Redaction posture: operator-identifying absolute paths given as neutral placeholders.

## 1. Method — validated before use

No generator existed. Rather than hand-author and hope, the regeneration script's **first phase
recomputed every derived value of the existing (to-be-retired) set from its own artifacts and asserted
a match against the landed index**. It reproduced **9 of 9**: the campaign raw digest and canonical
fingerprint, both grants' raw digests and canonical fingerprints, **both consumption-marker digests**,
and the rebuilt index bytes hashing to their own filename. Only then was the new set emitted. An
independent reviewer reproduced the same 9/9 result separately.

Mechanism recorded so it need not be re-derived: `raw_*_sha256` is the digest of the **pretty-printed
file bytes**, while `canonical_*_fingerprint` is the digest of `canonical_json_bytes(model)` — these
differ on disk. `connector_run_id` is **deterministic** (`compute_parent_arming_id` over connector
key, campaign id, grant digest, arming nonce), which is why consumption-marker digests are computable
before the run. The index file's own bytes are compact sorted JSON and its filename **is** its digest.

## 2. What was regenerated

A fresh evidence root at **revision 1** with `predecessor_index_relative_path` and
`predecessor_index_sha256` both `null` (owner ruling **D5=a**), leaving the prior tree intact as inert
history. New campaign identifier is a fresh UUID4 (**D4=a**), distinct from the retired one; both
arming nonces are fresh. Every `code_revision` field — campaign, both grants, and all index elements —
binds the landed commit. The window runs seven days from generation. The database was initialized to
the single alembic head.

Grants are identified **by raw digest**, never by `grant_id`: the `grant_id` strings were carried
verbatim from the retired grants and are informational only.

Archive copies under `evidence/campaigns/` and `evidence/grants/` are byte-identical to the top-level
artifacts. `consumed/`, `logs/`, and `log-seals/` are empty — correct pre-run staging, matching how
the retired set was staged (consumption markers are index-declared but written only at consumption).

## 3. Verification

Verified **key-free, offline, with no arming**, using the repository's own resolvers against the new
set and a freshly provisioned run checkout at the landed commit:

- independent fingerprint re-derivation matches the declared value;
- `resolve_current_dual_live_campaign_definition` — pass;
- `resolve_current_connector_egress_grant` for both connectors — pass;
- `connector_campaign_log_capture._current_authority` — pass;
- reviewed source identity derives the **landed** revision.

An independent reviewer re-derived every digest and re-ran the resolvers separately, reaching the same
result (73 substantive checks).

## 4. Run checkout, and a trap recorded for future re-provisioning

The run checkout must be a **standalone clone**, not a linked worktree: a linked worktree inherits
`extensions.worktreeConfig` from the shared configuration, which the source-identity verifier rejects.

**Recorded trap:** if the clone's checkout runs under an inherited `core.autocrlf=true`, the working
tree is smudged to CRLF, so the wrapper's raw blob object id no longer equals the blob in `HEAD` and
the source-identity gate refuses. `checkout --force` and `reset --hard` are **no-ops** in that state
because the index already matches. The working recipe: clone with `--no-checkout`, set
`core.longpaths=true` and `core.autocrlf=false`, check out the target commit, then leave
`core.autocrlf=false` locally so a later checkout cannot re-smudge it. After the fix the wrapper's raw
blob object id equals the `HEAD` blob and the frozen plan blob resolves correctly.

## 5. Disposition of the retired set — stated honestly

Retirement is **declarative, not mechanical**. Paired with its *own* original checkout, the retired
set still resolves and its window remains open until its stated expiry. Launching that pairing would
run the **known-defective** code; it refuses at the first workload import, **before any network
egress**, but would still consume an operator cycle and pollute the evidence tree. Mixed pairings
(new set with old checkout, or the reverse) fail closed in both directions.

Mitigation applied: the retired directory's one-command launcher — which armed egress itself, gated
only on the presence of the credential — was renamed out of invocability, and a README recording all
of the above was placed alongside it. No evidence file was modified. **The refused-run exhibits are
preserved untouched**, and the retired grants were never consumed.

No launcher exists for the current set, by design, because P8 has not been granted.

## 6. Durability election

No preservation re-rotation is elected for this tranche. The durability act for this work is the
branch push of the landed commit; the authority artifacts live outside the repository by design and
are reproducible from the recorded method above.

## 7. Non-claims

Does not authorize the live run. Does not close G2-P3 or the G2-P5 live half. Does not alter the
frozen plan blob, the B1a seal, the dependency digest, or the timeout contract. Does not re-adjudicate
any C4 residual.
