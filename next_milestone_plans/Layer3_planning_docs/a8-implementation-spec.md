# A8 Durable Value Retention Implementation Spec

Milestone: `M-A8-IMPLEMENTATION-SPEC`

Status supersession (2026-07-02): owner GO is complete for the current SEC XBRL
authority/controlled-submit surface, and PR #2415 merged the default-off A8
runtime guard packet; the implementation-spec status below remains historical
for PR #2409 lineage and future-surface guidance.

Status: owner-authorizable Tier-2 implementation specification only. This PR
does not implement runtime behavior, flip flags, change defaults, add schema or
migrations, change value reveal behavior, change redaction posture, touch A7
proof surfaces, or generate runtime artifacts.

## 2026-07-02 Status Supersession

Owner GO was given on 2026-07-02 for the current SEC XBRL
authority/controlled-submit surface. The default-off A8 runtime guard packet
merged as PR `#2415` at
`6a28d0a481e046e613ce1d7ef7932eb633ef2002`, and the redacted operator proof is
recorded via PR `#2419` at
`7fa72e745c7a2d6b72be37971e0e8768780dc5d5`.

Later 2026-07-02 record-truth refresh: the current controlled-submit path was
operator-proven on real data with sanitized evidence only: report SHA-256
`790fbb8eaa7de4be447f6c401089cb3b6435ff86614f4f0f57e656fc287a39d8`,
523 revealed facts, 497 non-empty values, value-store SHA-256
`3bc81d84fc75bde17d074eee610130efa2659e2b2d281e756402007243eef5a0`,
`value_store_hash=eb702c84d42e16200f9f07bbb5888b277b987bca028a51304e922ef2377ce285`,
persisted receipt hash
`7fe4c3da194396dbe11261eb6ec42942b4c23ce534c37e982f2c872cc4a50546`,
prior flag-off receipt hash
`d5c3585e91397f778f7d0f0297ac05d168dd7410fdaea1e2db7d18cbd3d5036d`, and
`production_readiness_claimed=false`. PR `#2421` then landed O6
guard-doc/support-matrix hardening at
`f566ddb14f62cd717f697f1d13b533ff434785ed` without changing A8 source defaults
or runtime posture.

Admission note: `layer3_sec_xbrl_production_admission.py` lines 141-156 require
`value_reveal_performed=false` in the evaluated production-admission evidence
run. The real-data reveal proof is A8 evidence, not admission evidence.

Flags remain default-false in source. Any arming remains owner-local per-run
runtime configuration. The implementation-spec language below is retained as
historical authority for the merged default-off A8 arc and as live guidance for
future surfaces: live SEC smoke, Arelle live binding, nonlocal admission, and
legacy Arelle reveal disposition.

Base authority for this planning packet: `project6-origin/main` fetched at
`80370c3fe4917df054f041851ee1aade1a838497`.

Review-thread remediation refresh: `project6-origin/main` was fetched at
`fd0cb72fdf7716113fcf61b5e5137acd3d304f91` before this Tier-1 ledger
reconciliation. The pre-remediation branch ancestry was one commit ahead and
one commit behind live main because PR `#2408` landed the A7/A8 board
reconciliation after this PR was opened.

## Owner Decision Summary

This packet uses `a8-lifecycle-design.md`, merged in PR `#2406` at
`80370c3fe4917df054f041851ee1aade1a838497`, as the owner-approved A8 durable
value-retention design authority.

The future A8 implementation should enable the existing filesystem-backed
internal value store as the first durable store for public SEC EDGAR financial
values, after owner authorization. It should keep audit/status CSV and receipt
surfaces hash/count/redaction-only, then expose values only through the existing
server-bound reveal authority and controlled-submit route path.

The implementation packet remains Tier 2 because it would touch durable
persistence, retained values, value reveal, route behavior, and redaction
boundary enforcement. All flags remain default-off until the owner authorizes
that runtime packet.

## Current Source Truth

- Feature defaults are off in `backend/app/core/config.py:152-174` for
  `layer3_sec_edgar_arelle_internal_value_store_enabled`,
  `layer3_sec_edgar_arelle_value_reveal_enabled`, and
  `layer3_sec_xbrl_controlled_value_reveal_submit_enabled`; the support matrix
  also pins the corresponding environment flags false in
  `config/support_matrix.yaml:10-18` and marks each capability
  `experimental_default_off` in `config/support_matrix.yaml:52-64`.
- The sidecar already computes and persists value records behind the internal
  value-store flag: `_local_facts` feeds `value_records` at
  `backend/app/services/layer3_sec_xbrl_sidecar.py:206-215`,
  `_write_internal_value_store` runs at `:321-322`, the writer is
  `:1129-1161`, the metadata helper is `:1164-1189`, the reader is
  `:355-413`, and the file path helper is
  `backend/app/services/layer3_sec_xbrl_sidecar.py:1341-1353`.
- The sidecar still labels the retained store
  `tied_to_sidecar_receipt_lifecycle` in diagnostics and store metadata at
  `backend/app/services/layer3_sec_xbrl_sidecar.py:825-829`, `:1140`, and
  `:1188`. Current source search found no value-store deletion path; the future
  implementation must keep that true.
- The legacy Arelle reveal service exists at
  `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py`. It rejects
  forbidden request fields at `:40-101` and `:286-303`, requires the
  `layer3_sec_edgar_arelle_value_reveal_enabled` flag plus explicit operator
  confirmation at `:150-175`, writes hash/count/lineage receipts at `:520-597`,
  and does not persist raw values in audit receipts.
- The current SEC XBRL route path is authority prepare plus controlled submit:
  `backend/app/api/layer3/sec_xbrl.py:778-953` and status at `:957-1007`.
  The request models are `backend/app/api/layer3/__init__.py:1309-1330`; they
  currently allow extra fields, so the future implementation must harden or
  explicitly reject extras at the service boundary and route boundary.
- The source-SEC legacy value reveal route remains under
  `backend/app/api/layer3/source_sec_edgar.py:531-566`; A8 should not make that
  route default-on.
- The value-reveal authority service binds approved operator decisions,
  projection/packet lineage, dataset version hash, sidecar hash, and value-store
  hash in `backend/app/services/layer3_sec_xbrl_value_reveal_authority.py:70-258`
  and validates approved decisions, redacted packet/projection state, and store
  authority at `:261-343` and `:381-420`.
- Controlled submit validates the submit flag, explicit confirmation, existing
  authority receipt, sidecar/value-store lineage, idempotent receipts, hash/count
  status projection, and raw authority rejection in
  `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py:98-204`,
  `:306-351`, `:900-970`, and `:1033-1043`.
- The sidecar-mode material bridge intentionally keeps CSV values redacted while
  retaining hashes and lengths; the sidecar projection sets `value_text` and
  effective/lexical text to empty strings and `value_redacted` true at
  `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py:710-812`.

## Gate Item Implementation Map

### Gate 1 - Live authority and posture are refreshed and pinned

Future code changes:
- `backend/app/core/config.py:152-174`: keep all three A8 flags default `False`;
  add no default-on behavior.
- `config/support_matrix.yaml:10-18` and `:52-64`: keep false pins and
  `experimental_default_off` until the owner-authorized Tier-2 PR lands.
- PR workflow: fetch `project6-origin/main`, record base SHA, branch `HEAD`, and
  `git rev-list --left-right --count project6-origin/main...HEAD`.

Tests:
- Add/extend `backend/tests/test_sec_xbrl_a8_*` to assert default-off flags in
  `settings` and the support matrix remain false.
- Keep running `backend/tests/test_sec_xbrl_a8_implementation_spec.py` and
  `backend/tests/test_ci_coverage_completeness.py`.

Rollback:
- Revert only the Tier-2 implementation commit. Because defaults remain off, a
  rollback returns to no-op behavior without data migration.

### Gate 2 - Durable value-store design is owner-approved

Future code changes:
- `backend/app/services/layer3_sec_xbrl_sidecar.py:206-215`: preserve value
  record creation as the source of retained public financial values.
- `backend/app/services/layer3_sec_xbrl_sidecar.py:321-322`: keep the writer
  invoked only when `internal_value_store_enabled` is true.
- `backend/app/services/layer3_sec_xbrl_sidecar.py:1129-1161`: change the
  persisted store policy to `sec_xbrl_public_financial_value_retention_v1`,
  keep `operator_surface_exposure` and `committed_artifact_exposure` false, and
  keep writes create-only/idempotent.
- `backend/app/services/layer3_sec_xbrl_sidecar.py:1164-1189`: change the
  metadata policy to the same durable policy value when persisted.

Tests:
- Extend `backend/tests/test_sec_xbrl_sidecar.py` to assert persisted store
  records retain `effective_value` and `lexical_value`, report the durable
  policy id, hash/count semantics, and idempotent replay.
- Add a guard that the old `tied_to_sidecar_receipt_lifecycle` label is absent
  from emitted persisted store metadata.

Rollback:
- Flip no runtime defaults. If the Tier-2 implementation must be backed out,
  revert the sidecar policy/idempotency changes and leave existing store files
  unread but not removed.
- The no-deletion source guard is a regression canary for accidental direct
  deletion APIs in the sidecar source (`unlink`, `rmdir`, `remove`, and
  `rmtree`, including `os`/`shutil` aliases through string and AST checks). It
  is not an adversarial sandbox and does not claim to catch `getattr` dispatch,
  subprocess deletion, file truncation, or equivalent evasions.

### Gate 3 - Storage hygiene is implemented before retained values can be written

Future code changes:
- `backend/app/services/layer3_sec_xbrl_sidecar.py:1349-1353`: add a
  preflight helper around `_root()` that rejects repo-relative, OneDrive/cloud
  sync, static-served, committed, operator Downloads, missing, unreadable, or
  shared authority roots before `_write_internal_value_store` can write.
- `backend/app/services/layer3_sec_xbrl_sidecar.py:1341-1342`: keep
  `_value_store_path()` under an isolated `internal-value-stores` namespace and
  expose only a namespace hash in receipts/status, never the local path.

Tests:
- Add sidecar tests for accepted durable off-repo roots and rejected repo,
  OneDrive, static, committed, missing, unreadable, and Downloads-like roots.
- Temp roots are test fixtures only. Durable runtime roots must remain off-repo,
  off-OneDrive/cloud-sync, non-static, non-git, and not Downloads-like.
- Add response/status scans that fail if a raw storage root or local path is
  projected.

Rollback:
- Revert the preflight helper and associated tests. Existing store files remain
  untouched; default-off flags continue to block writes.

### Gate 4 - Reveal request binding is explicit and server-owned

Future code changes:
- `backend/app/api/layer3/__init__.py:1309-1330`: change the value-reveal
  authority and controlled-submit request models to `extra="forbid"` or prove
  every extra field is rejected before service calls.
- `backend/app/api/layer3/sec_xbrl.py:778-953`: keep route families server
  constants, require auth binding via `_sec_xbrl_policy_decision`,
  `_sec_xbrl_require_binding`, and `_sec_xbrl_record_binding`, and reject any
  browser attempt to send raw paths, SEC URLs, source identity, storage roots,
  Arelle fields, connector dispatch fields, proxy headers, credentials, or
  operator contact fields.
- `backend/app/services/layer3_sec_xbrl_value_reveal_authority.py:70-258` and
  `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py:98-204`:
  keep the two-step authority receipt plus explicit submit confirmation; never
  allow client-supplied sidecar/value-store raw authority to replace server
  resolution.

Tests:
- Extend `backend/tests/test_sec_xbrl_value_reveal_guard_contracts.py` and the
  route-level tests to cover missing confirmation, stale authority, unknown
  fields, forbidden fields, lineage mismatch, missing store, and replay
  conflict.

Rollback:
- Revert the request-model hardening and route/service checks. Since flags stay
  off by default, rollback removes newly admitted runtime path without turning
  reveal on.

### Gate 5 - Audit/status redaction preserves identity and operational secrecy

Future code changes:
- `backend/app/services/layer3_sec_xbrl_sidecar.py:812-829` and `:955`: keep
  sidecar diagnostics/status value-free except hashes/counts/policy/state and
  update the policy label to durable retention.
- `backend/app/services/layer3_sec_edgar_arelle_value_reveal.py:520-597` and
  `backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py:900-970`:
  keep audit/status receipts hash/count/lineage only, with raw values returned
  only in the controlled response body when the owner-authorized route passes.
- `backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py:710-812`:
  keep sidecar-mode CSV `value_text`, `effective_value_text`, and
  `lexical_value_text` empty and keep values in the durable store.

Tests:
- Extend redaction tests over sidecar status, reveal authority, controlled
  submit status, and material-bridge CSV to assert identity/secret/path/token
  redaction while retained store records still contain public values.

Rollback:
- Revert only the redaction/status changes. Do not remove retained value stores;
  disable flags to stop new writes and reveals.

### Gate 6 - Verification is complete before owner authorization

Future code changes:
- No runtime code is needed for the gate itself. The implementation PR must add
  the focused tests described above and list exact commands and CI links.
- Validation commands must be validate-only, offline/isolated, and must not
  fetch SEC data, run Arelle network resolution, mutate shared operator stores,
  or generate artifacts unless the owner separately authorizes that action.

Tests:
- Required minimum: focused sidecar tests, storage-hygiene tests, route binding
  tests, value-reveal authority tests, controlled-submit tests, material-bridge
  redaction tests, `python -m pytest backend/tests/test_ci_coverage_completeness.py -q`,
  and `git diff --check`.

Rollback:
- Revert the implementation PR. The test-only portion can remain if it describes
  still-required behavior; otherwise revert it with the implementation commit.

### Gate 7 - Tier-2 governance is satisfied for runtime implementation

Future code changes:
- PR body and closeout must identify Tier-2 surfaces: retained value handling,
  durable persistence, value reveal, route behavior, request binding, and
  redaction posture.
- `next_milestone_plans/Layer3_planning_docs/a8-readiness-gate.md`: keep the
  retention-policy back-door guard added by this planning PR.
- `backend/app/services/layer3_sec_xbrl_sidecar.py:825-829`, `:1140`, and
  `:1188`: replace the old lifecycle-tied label with
  `sec_xbrl_public_financial_value_retention_v1` and add a source/test guard
  that no value-store deletion path is introduced to honor the old label.

Tests:
- Add a source/static test that scans the sidecar module for the durable policy
  id, absence of the old label in persisted-path emissions, and absence of
  value-store deletion operations.
- Keep CI green before merge and record owner authorization or the explicit
  self-verification rationale required by the active Tier-2 policy.

Rollback:
- Revert the Tier-2 implementation commit. For already-created durable stores,
  rollback is containment-by-disabled-flags and reader fail-closed behavior, not
  value deletion.

## Durable Store Enable Path

Recommended path: keep the filesystem-backed internal value store for the first
implementation, not an ORM migration. The existing store already has the needed
lineage/hash/count/read-verify shape, and the immediate A8 risk is governance and
hygiene, not relational queryability. Moving values into ORM would broaden the
first authorization into migrations, model changes, backup/restore semantics,
and database retention policy. That can be a later packet after the filesystem
contract is owner-authorized and tested.

Implementation sequence after owner authorization:
1. Add storage-root preflight and namespace-hash reporting around `_root()` and
   `_value_store_path()`.
2. Rename the persisted and status policy label to
   `sec_xbrl_public_financial_value_retention_v1`.
3. Keep `_write_internal_value_store()` create-only and idempotent.
4. Keep `read_sec_edgar_arelle_resolved_fact_authority_internal_value_store()`
   verifying sidecar id/hash, value-store hash, and count on every read.
5. Enable only by owner-set
   `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED=true`; default remains
   false in code and support matrix until a later owner posture change.

## Reveal Enable Path

Recommended path: owner-authorize the current SEC XBRL authority/submit route
path, and keep the legacy source-SEC Arelle reveal route default-off.

Implementation sequence after owner authorization:
1. Require existing approved operator decision, redacted packet/projection,
   dataset version hash, sidecar hash, and value-store hash through
   `layer3_sec_xbrl_value_reveal_authority.prepare_value_reveal_authority_receipt`.
2. Require explicit submit confirmation through
   `layer3_sec_xbrl_controlled_value_reveal_submit.submit_controlled_value_reveal`.
3. Keep route families server-owned in `backend/app/api/layer3/sec_xbrl.py`.
4. Reject client raw fields at request-model and service boundaries.
5. Return public values only in the controlled response body; keep audit/status
   receipts hash/count/lineage-only.

## Material-Bridge Decision

Recommendation: keep sidecar-mode material-bridge CSV redacted and read values
from the durable store only through the reveal path.

Reason: CSV and material-bridge artifacts are review/audit surfaces that are
easier to commit, export, or compare. The retained store is the durable product
data location. Keeping CSV redacted preserves the current audit/store
decoupling while still retaining values durably and reproducibly.

Rejected alternative: populating sidecar-mode CSV values from the store during
A8. That would duplicate retained values across artifact classes and broaden
review/export implications without improving durability.

## Flag Matrix

| Flag | Current default | Tier-2 implementation action | Dependency | Owner posture |
|---|---:|---|---|---|
| `LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED` / `layer3_sec_edgar_arelle_internal_value_store_enabled` | `False` | May be set true only by owner runtime config after storage hygiene and durable policy tests pass. | Required before value-reveal authority or controlled submit can resolve a value store. | Default-off in this PR and until owner authorizes runtime. |
| `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED` / `layer3_sec_edgar_arelle_value_reveal_enabled` | `False` | Keep legacy source-SEC Arelle reveal default-off unless owner explicitly authorizes that route. | Independent legacy reveal route; not the preferred A8 route. | Default-off in this PR and until owner authorizes runtime. |
| `LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED` / `layer3_sec_xbrl_controlled_value_reveal_submit_enabled` | `False` | May be set true only after value-store exists, authority receipt exists, auth binding passes, and explicit confirmation is supplied. | Depends on store flag and server-resolved authority/lineage. | Default-off in this PR and until owner authorizes runtime. |

No flag is flipped in this PR.

## Tier-2 Rollback And Containment

- Primary rollback is reverting the implementation commit and returning flags to
  false.
- Existing value-store files are retained as durable product data; rollback does
  not remove them.
- If a store fails integrity after rollback, readers fail closed on missing,
  unreadable, invalid, lineage-mismatched, hash-mismatched, or count-mismatched
  data.
- If a reveal path must be disabled, turn off controlled-submit and legacy
  reveal flags; do not alter stored values.

## Out Of Scope

- No live SEC egress changes.
- No Arelle execution or Arelle network behavior changes.
- No A7 proof-surface changes.
- No nonlocal delivery, export, or provider delivery behavior.
- No workflow or GitHub Actions changes.
- No progress board, progress manifest, or proof manifest changes beyond Tier-1
  ledger reconciliation for PR `#2409`.
- No runtime, schema, migration, persistence, redaction-posture, route, or flag
  change in this planning PR.

## Authorization Checklist

The owner can authorize a future Tier-2 implementation only when the packet
states:

- exact base SHA and branch ancestry;
- exact flags to arm and proof they remain default-off in source;
- exact sidecar/value-store/reveal route files touched;
- storage-hygiene proof;
- retention-policy label fix and no value-store deletion-path guard;
- material-bridge CSV decision;
- migration decision and rollback/containment posture;
- focused tests and CI links;
- review posture under the active SEC XBRL Tier-2 policy.
