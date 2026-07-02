# A8 Owner Decision Brief

Milestone: `M-A8-OWNER-DECISION-BRIEF`

Status: Tier-1 owner decision packet. This document does not implement runtime
behavior, flip flags, change defaults, add schema/model/migration work, change
redaction posture, enable value reveal, fetch SEC data, run Arelle, touch A7
proof-surface source, or generate runtime artifacts.

## Decision To Make

The owner decision is whether to authorize a bounded Tier-2 implementation of
A8 durable public-value retention and operator value reveal for SEC EDGAR XBRL
financial facts.

The decision is not whether public SEC financial values are secret. Current A8
design treats them as public government disclosures and retained product data.
The risk boundary is operator identity, local paths, storage roots, raw URLs,
tokens, proxy headers, tenant/workspace values, provider/connector secrets,
artifact bytes, and client-supplied authority.

The irreversible operational step is enabling operator-visible reveal. Values
are retained durably once the owner enables the internal value store and the
implementation passes storage, lineage, and redaction gates. Rollback is
flags-off containment, fail-closed readers, and commit revert. Rollback is never
deletion of retained public SEC financial values.

## Surface Choice

Recommended surface: current SEC XBRL authority plus controlled-submit path.

Flags:

- `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED`
- `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED`

Why this path is recommended:

- It is the newer path and is already aligned with server-owned authority
  receipts.
- It requires sidecar/value-store lineage, current authority, and explicit
  submit confirmation.
- It is fail-closed when required receipts or lineage are missing.
- It builds on the A7 persisted chain now proven in CI by PR `#2412`.

Alternative surface: legacy Arelle value-reveal service.

Flag:

- `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED`

Why this path is not recommended for first A8 authorization:

- It is an older reveal service rather than the current SEC XBRL
  authority/controlled-submit path.
- Choosing it would require separate owner acceptance criteria and proof that it
  remains default-off, redacted, lineage-bound, and not broader than the
  selected legacy route.

Choosing both surfaces is explicitly not recommended. A8 should authorize one
reveal surface at a time so request binding, receipt lineage, rollback, and
operator-facing consequences stay checkable.

## Options

| Option | Owner authorization | Consequence |
|---|---|---|
| `GO` | Authorize bounded Tier-2 implementation of durable internal value-store retention and the recommended current controlled-submit reveal path. | Implementation may add storage hygiene, policy-label updates, server-owned request binding, redaction tests, and controlled-submit reveal behavior. Defaults must remain off in source until owner runtime configuration arms them after verification. |
| `GO-PARTIAL` | Authorize durable internal value-store retention only; defer operator-visible reveal. | Implementation may retain public SEC values in the governed store behind `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED`, but `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED` and `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED` stay false. A later owner decision is required for reveal. |
| `HOLD` | Authorize no A8 runtime implementation. | All A8 flags remain false, no durable value store is armed, no reveal path is enabled, and current A7/A8 artifacts remain planning and proof surfaces only. |

## Authorization Acceptance Criteria

These criteria import and tighten the `M-ADVERSARIAL-REVIEW-AUDIT` acceptance
list. Every item is pass/fail checkable at implementation-verification time.

| Criterion | Pass condition | Fails closed when |
|---|---|---|
| Selected reveal surface | Owner selects exactly one surface: recommended current SEC XBRL authority/controlled-submit path or the legacy Arelle reveal service. Exact flags are named in the PR body. | Both surfaces are authorized, no surface is selected, or a route is implied without exact flags. |
| Live authority | Implementation PR records fetched `project6-origin/main` SHA, branch `HEAD`, branch ancestry, touched files, and current default-off proof for all A8 flags. | Main was not freshly fetched, ancestry is unclear, touched surfaces are omitted, or any A8 flag defaults on in source. |
| Durable storage root | Runtime storage root is durable, isolated, off repo, off OneDrive/cloud sync, non-static, non-git, not shared across authorities, not operator Downloads-like, and not projected as a raw path/root. Temp roots are test fixtures only. | Storage is repo-relative, cloud-synced, static-served, committed/generated, shared across authorities, missing/unreadable, Downloads-like, or exposed in audit/status. |
| Server-owned lineage | Store and reveal bind to current authority hash, sidecar id/hash, dataset hash where applicable, value-store hash/count, auth binding, and explicit operator confirmation for display/submit. | Client-supplied authority replaces server resolution, lineage is stale or missing, confirmation is missing, or replay conflicts are accepted. |
| Request binding | Browser/client cannot supply raw paths, raw URLs, storage roots, source identity, Arelle fields, connector dispatch fields, credentials, proxy headers, operator contact fields, or unknown extras. Unknown extras are rejected at the request model or proven blocked before service calls. | Any forbidden or unknown client field can influence source, storage, lineage, Arelle execution, reveal, or operator authority. |
| Audit/status redaction | Audit/status surfaces expose only hashes, counts, policy ids, state, safe reason codes, timestamps, and lineage. Public values are retained in the governed store and returned only through the authorized controlled response. | Audit/status duplicate public values unnecessarily, expose operator identity, paths, roots, URLs, tokens, proxy headers, contact strings, provider/connector secrets, artifact bytes, or weaken durable retention into hash-only records. |
| Rollback and containment | Rollback posture is flags off, fail-closed readers, and commit revert. Existing retained value stores remain intact as durable product data. | Rollback deletes retained SEC values, adds secure-erasure requirements, mutates stores destructively, or depends on H6/archive movement. |
| Verification | Focused tests cover store hygiene, hash/count/lineage, request binding, redaction, idempotency, failure states, `git diff --check`, and CI links. Validate-only commands use isolated/offline runtime state and do not fetch SEC data, download taxonomy, run Arelle network resolution, reveal values, mutate shared operator stores, or generate artifacts. | Tests rely on shared seeded state, live SEC/taxonomy/Arelle/runtime network, generated artifacts, omitted changed surfaces, red CI, or unproven redaction/request boundaries. |
| Tier-2 posture | PR body names exact Tier-2 surfaces, rollback/containment notes, owner authorization, and review posture before runtime merge. | Tier-2 surfaces are ambiguous, owner authorization is missing, rollback/containment is absent, review posture is unstated, or implementation silently grants schema/default-on/live-egress authority. |

## Should Not Contain

The owner authorization packet should not contain:

- Any implicit authorization for live SEC egress, taxonomy download, Arelle
  network execution, schema/model/migration work, flag default-on changes, or
  legacy Arelle reveal route activation unless separately and explicitly
  selected.
- Temp directories as acceptable production or durable runtime roots.
- Secure-erasure, retained-value deletion, or value-store wiping as rollback.
- H6/archive movement as part of A8 durable store behavior.
- Broad implementation freedom beyond the selected reveal, storage, lineage,
  request-binding, redaction, and rollback surfaces.
- A request-model hardening shortcut that changes value-reveal route behavior
  without Tier-2 owner authorization and rollback/containment notes.

## Open Owner Inputs

The owner must provide these inputs before implementation starts:

1. Selected surface: recommended current SEC XBRL controlled-submit path, legacy
   Arelle reveal service, or no reveal.
2. Durable storage root location for retained public SEC values.
3. Decision posture: `GO`, `GO-PARTIAL`, or `HOLD`.

## Prerequisites Satisfied

- A8 durable retention design authority is merged: PR `#2406`, merge commit
  `80370c3fe4917df054f041851ee1aade1a838497`.
- A7 real-Arelle synthetic CI proof is merged: PR `#2407`, merge commit
  `c96ea5154dd13a0724d74f8979bb28651d667cb8`.
- A7/A8 board reconciliation is merged: PR `#2408`, merge commit
  `fd0cb72fdf7716113fcf61b5e5137acd3d304f91`.
- Corrected A8 implementation specification is merged and the progress board,
  progress manifest, and proof manifest were reconciled there: PR `#2409`,
  merge commit `54d616b365d658adb933482b2a867cb9bc2d8c39`.
- Master context and proof-provenance docs are merged: PR `#2410`, merge commit
  `abd8c3f8ac2b2545fda8b88d46aa916a22b626e8`; PR `#2411`, merge commit
  `0290ff5bbbd5a4d6c52aa3a09eb994985c0ca39f`.
- A7 full-chain CI durability is merged and proves the synthetic offline
  connector -> parser -> regex-fact -> Arelle sidecar -> material bridge ->
  `DatasetVersion` chain plus fail-closed missing-sidecar behavior: PR `#2412`,
  merge commit `67bab0b010edeeecf8a91cca78bb463a6fb0f5ba`.

## Owner Reply Shape

An adequate owner reply can be short but must contain all required inputs:

```text
Decision: GO | GO-PARTIAL | HOLD
Surface: current SEC XBRL controlled-submit | legacy Arelle reveal | no reveal
Durable storage root: <absolute off-repo, off-cloud-sync, non-static, non-git root>
```

If the owner chooses `GO` or `GO-PARTIAL`, the implementation PR must still pass
the acceptance criteria above before merge. This brief authorizes no runtime
change by itself.
