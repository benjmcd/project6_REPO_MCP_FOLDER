# 00 — Governing Posture and Invariants

Every rail below is stated with (a) what it requires, (b) WHY it is the optimal posture given
the circumstances, and (c) WHERE it is enforced. These are the constraints every future lane
inherits. None is ceremony; each earns its place. (Owner standing directive: velocity ceremony
may be disregarded; safety/honesty rails may not. This file is the authoritative list of which
is which.)

## I1. Retain, never erase (SEC public financial values)

- Requires: retained SEC EDGAR financial values are durable product data. No deletion,
  wiping, secure-erasure, or archival-移动 of value stores as rollback or cleanup. Rollback is
  always containment (flags off, fail-closed readers), never data destruction.
- Why optimal: SEC EDGAR values are public-domain facts. Treating them as toxic-to-hold was a
  category error (the original A8 secure-erasure design was overturned on exactly this
  reasoning, 2026-06-28; PR #2406 rewrote the design). Erasure machinery would add risk
  (destroying evidence) while protecting nothing.
- Enforced: `sec_xbrl_public_financial_value_retention_v1` policy id emitted by the sidecar
  (`backend/app/services/layer3_sec_xbrl_sidecar.py`, VALUE_RETENTION_POLICY_ID); no-deletion
  source guard test (AST + string, incl. os/shutil aliases) in
  `backend/tests/test_sec_xbrl_sidecar.py`; guard's threat model documented (accidental
  regression canary, not adversarial sandbox — O6/#2421).

## I2. Redaction targets identity, never values

- Requires: operator identity, contact strings, credentials, raw local paths, storage roots,
  SEC URLs, issuer/accession payloads never appear in receipts, status surfaces, committed
  docs, PR text, or reports. Values themselves are retained (I1) and revealed only through
  the governed controlled-submit response.
- Why optimal: the sensitive material in this system is who/where/how the operator runs, not
  the public financial data. Inverting this (redacting values, leaking paths) was the failure
  mode of the pre-retention design.
- Enforced: hash/count/policy-only receipt surfaces; namespace-hash instead of raw root
  (sidecar hygiene metadata); `_reject_raw_or_local_authority` on reveal services;
  response-scan tests; every record-truth lane re-audits its diff for leaks before merge.

## I3. Default-off, owner-armed

- Requires: all raw-bearing/reveal flags default False in source. The selected support
  matrix pins live SEC network, internal value store, controlled-submit reveal, legacy
  Arelle reveal, corpus validation, and production admission evaluator false; the separate
  nonlocal authorization gate is default-false in source and must be explicitly authorized.
  Arming is per-run owner-local env configuration only. Merging code never arms anything.
- Why optimal: separates capability from activation. Every capability can be reviewed,
  merged, and CI-proven while the dangerous transitions (egress, reveal) remain individually
  owner-controlled and per-run reversible. This is what allowed the entire A8 arc to merge on
  green CI without a single production-risk moment.
- Enforced: `backend/app/core/config.py` (~152-178) defaults; support-matrix pins; boot-time
  containment validator `_validate_raw_bearing_sec_storage_containment` (config.py ~303-414;
  function starts ~346)
  refuses to start with raw-bearing flags armed unless STORAGE_EXPOSURE=disabled and
  STORAGE_DIR/DATABASE_URL are off-repo/off-OneDrive (demonstrated live, 2026-07-02).

## I4. Storage-root hygiene (structural vs name classes)

- Requires: A8 value-store operations classify the storage root. STRUCTURAL classes hard-fail
  with no override ever: repo_relative, git_tracked, onedrive_cloud_sync, static_public_served,
  generated_artifact, shared_authority, missing_unreadable, permission_broad. NAME classes
  (downloads_like, temp_like) fail by default but may be accepted with the explicit
  `LAYER3_SEC_XBRL_STORAGE_ROOT_HYGIENE_OVERRIDE_ACK` (default False), and every override is
  recorded in receipts with reason code + namespace hash.
- Why optimal: structural classes represent real corruption/exposure mechanisms (git churn,
  cloud-sync mid-write corruption, static serving, shared authority collisions) — no owner
  intent can make those safe, so no override exists. Name classes are heuristics about
  operator habits (Downloads cleanup, temp semantics) — the owner may knowingly accept them
  for replay/proof work, and honesty is preserved by recording the override rather than
  silently weakening the rail. Enforcement is at VALUE-STORE OPERATION time, not app boot,
  because `settings.storage_dir` defaults repo-relative and feeds non-A8 subsystems — a boot
  gate would break every ordinary dev run (non-fragility).
- Enforced: `_classify_value_store_storage_root` + `StorageRootHygieneResult`
  (sidecar ~1427-1533); per-class tests incl. OneDrive-variant regression and
  symlink/case/separator variants (#2415 review round + O6/#2421).

## I5. Canonical durable root: C:/p6store

- Requires: durable A8 value stores live at the machine-level canonical root `C:/p6store`
  (hygiene class: accepted, no override). Auto-provisioned by `project6.ps1`
  (`provision-a8-root` strict action; `setup` warning-only hook). The operator sandbox root
  remains valid only as a recorded-override replay surface.
- Why optimal (and why NOT in-repo, which was the owner's first instinct): an in-repo root is
  triple-rejected by I4 (repo_relative + this repo is OneDrive-synced + would need git
  tracking to "exist in worktrees") and cannot deliver durability anyway — worktrees share
  only tracked files, so per-worktree presence means either an always-empty store or
  committing retained values into git history (violating I2 and bloating every clone). One
  machine-level root is strictly stronger: it pre-exists every worktree/rebase by
  construction and all worktrees share the SAME store. Owner approved this substitution
  explicitly (2026-07-04).
- Enforced: #2423 tooling + docs; migration manifest `C:/p6store/MIGRATION_MANIFEST.json`
  (sha256 845974f7…); migration was copy-verify-repoint with the source sandbox retained (I1).

## I6. Tiered merge gates, asymmetric by risk

- Requires: Tier-1 (validate-only/docs/additive tests) lanes self-merge on green CI with all
  bot review threads resolved. Tier-2 triggers (value reveal, durable persistence, schema/
  migrations, default-on, redaction posture) require exact risk/surface documentation and
  targeted verification; independent review is sought or required under the live merge-gate
  policy's concrete risk/blocker triggers. Bot findings are never ignorable; "bot silence is
  not a blocker" does not cover bot findings that exist.
- Why optimal: matches review cost to irreversibility. The one Tier-2 lane of the campaign
  (#2415) went through a two-round independent review that caught a real hygiene bypass
  (OneDrive-variant) before merge — evidence the asymmetry is calibrated correctly, not
  theater. Meanwhile ~a dozen Tier-1 lanes merged same-day without quality loss.
- Enforced: `next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`;
  operational habit: always check GraphQL reviewThreads, never just CI + mergeable
  (lesson from the 2026-07-01 adversarial audit that refuted a premature MERGE-READY verdict).

## I7. Record truth (the repo must say what is true)

- Requires: every merged tranche and every operator proof is recorded in the repo record
  (progress board + both JSON manifests + MASTER_CONTEXT + affected planning docs) promptly,
  in sanitized form (I2), with supersession notes instead of rewrites. Operator-local
  evidence is recorded by hash/count so it is verifiable without being committed.
- Why optimal: three separate audit cycles (2026-07-01, -02, -03) each found the record
  lagging reality as the top-ranked risk — stale records cause future agents to re-litigate
  closed decisions or trust dead anchors. The cost of a record-truth lane is one small
  Tier-1 PR; the cost of drift is repeated multi-agent audit cycles.
- Enforced: convention + the RT/RT-2/RT-3 lane precedent (#2419, #2420, #2422); manifest
  validity checks (`json.tool`, `tools/l3-progress-check.py`) in every record lane.

## I8. Evidence taxonomy and zero-trust verification

- Requires: every report separates repo-confirmed fact / GitHub-state fact / operator-record
  fact / inference. Cross-agent claims are re-derived, not trusted: independent dual-lens
  audits for state claims, adversarial verify rounds for review findings, hash-anchored
  artifacts for operator proofs.
- Why optimal: this discipline caught, among others: a premature merge-ready verdict, a
  misdiagnosed "347 vs ~15 worktrees" undercount (the auditor's own orchestrator was wrong),
  a stale ledger citation of an undiffed file, and the admission-semantics subtlety. Each
  catch happened precisely at a taxonomy boundary where trust would have propagated an error.
- Enforced: convention in every lane handoff; dual blind-lens audit pattern; the requirement
  that reports quote commands + decisive output.

## I9. Dual-agent lane fencing

- Requires: parallel agent lanes carry explicit file-surface fences, one open PR per lane,
  fetch+rebase before merge, stop-and-report on any fence conflict. Handoff artifacts stay
  repo-local, never global temp/Downloads. Dispatch to a second thread waits for pickup, and
  pickup is verified from session metadata where available.
- Why optimal: every landing across 15+ PRs by two parallel agents merged without a single
  cross-lane conflict — the fences plus rebase rule made "avoid parallel git" (the old
  blanket rule) unnecessary while preserving its intent.
- Enforced: per-lane handoff text; operational lessons recorded in the arc ledger.

## I10. Admission evidence semantics

- Requires: production-admission evidence packets must have `value_reveal_performed` exactly
  False in the EVALUATED evidence run (fail-closed on missing key). Reveal proofs are A8
  value-retention evidence, never admission evidence; prior owner-local reveal history does
  not taint future admission runs.
- Why optimal: this keeps "we proved reveal works" and "this production runtime does not
  reveal" as independent, simultaneously-provable claims — which is exactly the honest
  production posture.
- Enforced: `backend/app/services/layer3_sec_xbrl_production_admission.py:141-156`
  (`_check_containment_invariants_held`); clarification recorded in the repo record via
  #2422.

## I11. Worktree no-remove rail

- Requires: no agent removes worktrees/branches without explicit per-class owner
  authorization. Lane-created ephemeral worktrees are the one recorded deviation class
  (record-truth-3 removed its own post-merge; logged, not repeated without note).
- Why optimal: 347 worktrees exist; only 11 are mechanically-provable safe removals; the
  rest may hold preserved or in-flight work. Reversibility beats tidiness until the owner
  authorizes a cleanup lane with an inventory (which exists, hash-anchored, in the
  M-FWD3-EVIDENCE report).

  (Superseded 2026-07-06: owner-authorized cleanup executed - registry
  353 -> 163, 190 removed, about 85 GB reclaimed; the 139 protected
  worktrees were then individually adjudicated read-only. Rail intent
  unchanged for everything still protected. See 03-forward-plan.md F6 plus
  M-DIRTY-ADJUDICATION refreshes.)

## I12. Record-lane inbox archive refresh

- Requires: at each record-lane closeout, refresh the off-repo inbox archive in
  a new lane-unique folder under `C:/p6store/inbox-archive/` (for example, a
  date folder plus lane slug or timestamp), write an `ARCHIVE_MANIFEST.json`
  with copied-file hashes and an aggregate sha256, and cite that aggregate hash
  in the lane's durable record entry.
- Why optimal: agent-inbox logs and lane-source payloads are mutable
  coordination state. A dated off-repo hash archive preserves provenance
  without committing raw logs or treating single-copy OneDrive state as the
  durable record.
- Enforced: record-lane closeout convention, beginning with the 2026-07-06 seed
  archive recorded in D29 and the evidence registry.

## I13. Semantic ratification does not authorize a B1b build

- Requires: an owner ratification of target semantics is recorded as a durable
  decision without being upgraded into implementation authority. The complete
  58-disposition identity-metadata enumeration is
  `RATIFIED-EXACTLY-AS-PROPOSED`; the promotion-identity precedence rule is
  `RATIFIED-AS-PROPOSED`. The explicit second key remains not granted. Its
  future intent is `INTENDED-NON-AUTHORIZING`, and `WITHHELD` is not claimed.
- Why optimal: target-state agreement and authority to mutate runtime are
  independent controls. Keeping them separate makes the next owner gate exact,
  prevents a future-intent statement from becoming an accidental grant, and
  permits records to converge without implying that schema, persistence, or
  dispatch work has begun.
- Enforced: D33 and D34 contain the self-contained ratified semantics; the
  unnumbered status note after them carries the remaining explicit-second-key
  gate. No implementation, schema, ORM, migration, runtime, build dispatch,
  B1b build PR, or B1b build merge is authorized by those records.
- Current standing:
  `B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`

> **Candidate invariant:** I14 becomes standing only when co-committed with the
> exact dual-live campaign record, implementation plan, and D35-D43 after M0
> review. Until then it is a proposal and grants no authority.

## I14. Connector caller posture is not egress-grant authority

- Requires: identity, role, local mode, feature flags, and caller-supplied
  references never substitute for the named connector grant required by
  D27/D28. A live arming and every physical-request reservation must first
  load/rederive the protected strict campaign definition as a deny-only
  correlation predicate, then load the connector-specific owner grant from a
  protected server path, match separately configured SHA-256 values, strictly
  validate the definition/grant intersection and both half-open windows, and
  traverse the protected evidence-index chain. Its configured revision must be
  the unique maximal head and the selected campaign's earliest complete-slice
  introduction before marker creation; a preserved ancestor cannot arm even if
  its grant is unused. After arming, that revision/digest must remain equal to
  the immutable arming binding at reservation and immediately before send. Bind
  the definition, grant, and index digests to the arming. Only the grant
  supplies egress authority.
- Also requires: `fresh_live` is derived from a canonical terminal request
  ledger plus admitted raw bytes; it is never a caller field. One canonical
  connector-origin receipt lives on the connector target and downstream
  surfaces carry only its ID/hash.
- Historical boundary: expired or rotated definition/grant bytes may be
  rehashed only through a protected server-configured content-addressed
  evidence-index chain to validate recorded send times inside both original
  half-open windows. The configured index must be the unique maximal head;
  successors preserve every predecessor reference and add exactly one complete
  disjoint slice. Campaign armings, log seals, and both seal events bind the
  earliest complete-slice introduction revision/digest. Those evidence types
  are distinct/read-only and cannot arm, execute, reserve, send, or revive
  budget.
- Ceiling and custody boundary: each grant has one nonce, one deterministic
  parent arming, and one no-overwrite consumption marker. Any replacement needs
  a new strict definition/campaign and explicitly superseding grant;
  same-campaign recovery is not admissible. Exact derived URLs remain in
  memory; strict URL scalar columns are null and raw metadata responses are not
  persisted. ScienceBase duplicate-member/sole-`downloadUri` and raw-path/query
  authority are checked before permissive parsing. The four-stream runtime-log
  manifest, separate no-overwrite seal, and both connector-run seal events are
  part of the custody scan; machine-global logs and cryptographic
  nonrepudiation are not claimed.
- Why optimal: authentication answers who called, while the grant answers what
  exact egress was approved. Separating them prevents a local flag or owner
  role from silently widening target, credential audience, or request budget,
  and prevents fixture/live relabeling.
- Experimental boundary: protected local definition/grant files,
  no-overwrite seals, and service-enforced JSON/event immutability are adequate
  only for the exclusive single-process proof.
  Supported multi-user/production operation requires a signed grant/control
  plane and normalized immutable grant/ledger/receipt schema.
- Prospective enforcement:
  `docs/campaign-records/2026-07-29-dual-live-proof.md`,
  `docs/superpowers/plans/2026-07-29-dual-live-proof.md`, D39-D43. No
  implementation, grant file, egress, or proof is claimed by this candidate.
