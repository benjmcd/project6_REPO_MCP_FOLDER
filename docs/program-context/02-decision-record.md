# 02 — Decision Record

## 2026-09-04 reconciliation — no new owner decision

This docs pass records source and PR state; it makes no new owner decision. See
[MASTER_CONTEXT](../MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation)
for the current bounded summary.

The July explicit-second-key `NOT-GRANTED` disposition remains the historical
authority for that exact proposed key. Later landed connector handoff,
adopted-external intake, and public ScienceBase source paths mean it must not be
read as a blanket assertion that all B1b-related source remains unimplemented.
Conversely, later source presence does not retroactively approve the old key,
close its ballot, or grant connector-to-intake auto-trigger, acquisition,
credential, signing, flag-arming, nonlocal, or merge authority. I12 and ledger
custody remain separately governed.

ADR-style. Each: context → alternatives → decision → why optimal given the circumstances →
evidence → revisit-when. Dates 2026.

## D1. Retention over erasure (06-28, reaffirmed throughout)

- Context: original A8 design was a secure-erasure lifecycle for "raw-at-rest" SEC values.
- Alternatives: (a) erasure lifecycle; (b) avoidance (never store); (c) durable retention.
- Decision: (c), with redaction re-aimed at identity/paths/secrets.
- Why optimal: the data is public-domain; erasure destroyed evidence while defending
  nothing; avoidance made the product (value analysis) impossible. Independently verified
  against source before adoption (no documented erasure rationale existed).
- Evidence: PR #2406 rewrite; posture recorded repo-wide; I1/I2.
- Revisit when: a non-public/licensed/contractual source class is ever ingested — that class
  needs its own disposition policy (explicitly out of scope for SEC EDGAR).

## D2. Controlled-submit surface over legacy Arelle reveal (07-02)

- Context: two reveal surfaces existed; owner had to pick one for GO.
- Alternatives: (a) current controlled-submit path; (b) legacy Arelle reveal service;
  (c) both.
- Decision: (a). Legacy stays default-off governed sibling; (c) rejected outright.
- Why optimal: (a) is newer, fail-closed by construction, bound to server-owned lineage
  (decision → workflow → packet → projection → authority), and is the surface the A7 proof
  chain feeds. (b) predates the lineage model and would need independent hardening. (c)
  doubles the audit surface for zero product gain.
- Evidence: a8-owner-decision-brief.md; owner GO text; CK3 executed through (a).
- Revisit when: a distinct product use for legacy reveal appears — requires its own
  authorization + acceptance criteria (P4 handles labeling meanwhile).

## D3. Hygiene override-ack design (07-02)

- Context: owner's chosen proof root was Downloads-like/temp-named — classes the owner's own
  authorization contract rejected.
- Alternatives: (a) reject owner root, force a compliant one; (b) silently weaken the rail;
  (c) strict contract + narrow recorded override for NAME classes only.
- Decision: (c).
- Why optimal: (a) blocks the owner on their own machine for a heuristic, not a structural
  risk; (b) silently destroys the rail; (c) preserves the full contract, honors owner intent,
  and converts the exception into recorded evidence (override flag + reason code + namespace
  hash in every receipt). Structural classes stay non-overridable because no owner intent
  makes cloud-sync corruption or git churn safe.
- Evidence: #2415 implementation + tests; both operator proofs carry the recorded override.
- Revisit when: never silently; only via explicit Tier-2 posture change.

## D4. Op-time hygiene enforcement, not boot gate (07-02)

- Context: `settings.storage_dir` defaults repo-relative and feeds non-A8 subsystems.
- Alternatives: (a) validate root at app startup; (b) validate at A8 value-store operations.
- Decision: (b).
- Why optimal: (a) breaks every ordinary dev run for subsystems that never touch retained
  values (fragility for zero safety). (b) puts the check exactly where the protected asset
  is touched. The separate boot-time containment validator still guards the genuinely global
  condition (raw-bearing flags armed with unsafe storage/db).
- Evidence: config.py:113 default; sidecar op-time checks; containment validator; the
  first CK2 run failing closed at boot until containment env was correct.

## D5. Asymmetric merge gates (07-02)

- Context: velocity mandate vs a value-reveal runtime change.
- Alternatives: (a) review everything; (b) review nothing (velocity); (c) Tier-triggered
  asymmetry.
- Decision: (c) — Tier-1 self-merge on green + resolved threads; Tier-2 risk documentation,
  targeted verification, and independent review when the live merge-gate policy's concrete
  review triggers or blockers apply.
- Why optimal: (a) would have added ~12 review round-trips to docs lanes for zero findings;
  (b) would have merged #2415 with a real OneDrive-variant hygiene bypass (caught in review
  round 1). The asymmetry provably paid for itself exactly once — on the one lane that
  needed it.
- Evidence: #2415 two-round review record; every other lane's clean self-merge.

## D6. Fused operator lane D1→O2→O3 (07-02)

- Context: three ranked pursuits (replay-proof, Arelle binding proof, real-data reveal) each
  needed the previous one's artifacts.
- Alternatives: (a) three serialized lanes with separate closeouts; (b) one checkpointed
  lane.
- Decision: (b), each checkpoint individually fail-closed and banked.
- Why optimal: identical safety semantics (abort at any checkpoint = the serialized version),
  one-third the ceremony, and CK3 structurally requires CK2's store anyway. The
  investigating agent recommended (a) for provenance cleanliness; the fusion preserved that
  cleanliness via per-checkpoint evidence records — a case where the orchestrator's
  adversarial review improved on the investigator's ranking.
- Evidence: ck1/ck2/ck3 outputs; a8_real_reveal_report.json; #2422 record.

## D7. Zero-egress replay over fresh live smoke (07-02→03)

- Context: board language said "live smoke next"; June artifacts existed on disk.
- Alternatives: (a) fresh SEC egress smoke; (b) replay retained artifacts by receipt+hash.
- Decision: (b), with (a) demoted to fallback-if-artifacts-stale.
- Why optimal: retained public artifacts carry full hash lineage; a new fetch adds network
  risk, rate-limit cost, and fair-access footprint to prove something the receipts already
  prove. The board's "next" language was verified HISTORICAL per its own supersession rules
  before deciding.
- Evidence: M-FWD-OPTIONS-2 analysis + orchestrator sandbox inventory verification; CK1's
  `network_request_made=false` chain.

## D8. Canonical machine-root over in-repo root (07-04)

- Context: owner requested an in-repo durable root that "exists in every new worktree."
- Alternatives: (a) in-repo tracked folder; (b) rail change to permit (a); (c) canonical
  machine-level root auto-provisioned by repo tooling; (d) repo-adjacent sibling.
- Decision: (c) `C:/p6store`, owner-approved after the conflict was surfaced.
- Why optimal: (a) is triple-rejected by I4 (repo_relative + OneDrive-synced repo +
  git_tracked) AND cannot deliver durability — worktrees share only tracked files, so the
  folder arrives empty or the values enter git history. (b) removes a rail that guards a
  real corruption mechanism (OneDrive sync mid-write) to simulate a property (per-worktree
  store) that still wouldn't exist. (d) fails because the repo's parent (Desktop) is also
  OneDrive-synced on this machine. (c) delivers the actual intent — always-present,
  zero-setup, rebase-proof — more strongly than the literal request: one shared store
  pre-exists every worktree by construction.
- Evidence: #2423; MIGRATION_MANIFEST.json (sha 845974f7…); live `provision-a8-root` proof
  from a fresh worktree.
- Revisit when: multi-machine operation begins (then the canonical-root concept needs a
  per-machine provisioning story, same design).

## D9. Migration = copy-verify-repoint, never move/delete (07-04)

- Context: existing store lived in the sandbox (recorded-override root).
- Alternatives: (a) move; (b) copy + delete source; (c) copy + verify + repoint, source
  retained.
- Decision: (c).
- Why optimal: I1 forbids destroying retained values under any pretext including migration;
  the source doubles as an independent backup; namespace hashes inside copied artifacts
  describe the ORIGIN root and are preserved as historical evidence rather than falsified —
  new writes under the new root mint new namespace hashes.
- Evidence: robocopy 43/43 zero-fail; p3_verify.py PASS (hygiene accepted no-override,
  chain + store re-verified); both manifests.

## D10. Program-context set as a structured file family (07-04, this set)

- Context: owner requested an exhaustive all-encompassing context artifact.
- Alternatives: (a) grow MASTER_CONTEXT into a monolith; (b) new competing master doc;
  (c) structured set under docs/program-context/ with MASTER_CONTEXT as executive summary.
- Decision: (c).
- Why optimal: (a) makes the executive summary unreadable and churn-heavy; (b) creates dual
  sources of truth (the exact drift failure mode three audits flagged); (c) separates
  concerns (invariants / history / reasoning / plan / evidence) with explicit authority
  ordering and a maintenance protocol. Authored by the session holding the decision
  reasoning; independently anchor-verified before landing (I8).
- Revisit when: the set itself drifts — the INDEX maintenance protocol is the guard.

## D11. Delegation architecture (standing)

- Context: two repo-lane desktop threads + one orchestrator session; owner directive to delegate
  most execution.
- Decision: repo-lane threads own repo/git lanes (fenced, one PR at a time); the orchestrator
  session owns operator-private lanes (proofs, migrations — where the authorization chain
  lives), independent Tier-2 review, cross-lane adjudication, and record dispatch.
- Why optimal: subagents cannot verify in-band owner authorization (demonstrated by an
  executor's correct refusal of the proof task); git surfaces stay single-writer per lane;
  and every repo-lane product gets adversarially reviewed by a party that didn't write it.
- Evidence: 15 PRs landed collision-free; the refusal incident; two-round #2415 review.

## 2026-07-05 Corpus-Go Decision Addendum (M-PROGRAM-CONTEXT-2)

This section appends D12-D18 for the corpus-go arc. M-PROGRAM-CONTEXT-2
verified PR/SHA pairs, code anchors, durable-root files under `C:/p6store`,
report hashes, and the #2433 count surface before appending.

Corrections applied to the source addendum:

- The aggregate report currently hashes to
  `52385f07a1a4dc29871708602bacadb159da44499bb950fd887665abd3879e91`,
  not the earlier payload hash `113ce73679547f5d202cb273ebca9d2373f90fab9ae688e9159cc7894c3cee10`.
- The storage/integrity supplement currently hashes to
  `bce4d7800db4742577fcfe1214618ab7730057e46a4e6bd374b7d8848f6eb1e3`,
  not the earlier payload hash `22cda8340cef3ae68cd08d1a09748e384feefc8a82700ddfb4b8304294be0141`.
- The verified supported distribution is 18 full domestic 10-K/10-Q pairs,
  MSFT with a supported 10-Q and a named 10-K `arelle_model_errors_present`
  block, plus CURLF/CRLBF supported 40-F filings. The 39 supported filings /
  21 supported issuers totals still match the completed #2433 count surface.
- The source payload named `provision_report_2021_2026.json`; this lane did
  not locate that report under `C:/p6store`, so runtime-provisioning report
  details below are carried as operator-authored context unless separately
  anchored. The committed PR/code/test provisioning anchors were verified.

## D12. Per-ticker isolation over connector-ceiling chunking (07-05)

- Context: the run plan batched by connector ceilings (4 or fewer CIK
  references per request). Live pilot chunks 03-09 all failed as whole chunks:
  one issuer lacking a requested form (`required_form_missing`) or one
  unresolvable ticker (`company_matrix_unknown`) rejected the entire connector
  request. That connector behavior is correct for invalid requests, but
  chunk-level blast radius violated the run's per-filing-isolation intent.
- Alternatives: (a) keep four-ticker chunks and pre-sort tickers into
  domestic/foreign/unknown groups; (b) per-ticker calls.
- Decision: (b) - one corpus call per ticker, fresh process each.
- Why optimal: (a) requires knowing each ticker's filer class in advance, which
  is exactly what the run discovers; misclassification recreates the failure.
  (b) makes every failure class a named per-ticker disposition by construction,
  at negligible request-count cost because submissions metadata is per-issuer
  either way. The wall cost was about 8 seconds pacing per ticker, irrelevant
  next to Arelle time.
- Evidence: chunks 03-09 chunk-level failures vs 22 subsequent per-ticker runs,
  every one dispositioned; run gates 4/4 PASS.
- Revisit when: the connector grows per-row partial-result semantics for
  multi-ticker requests.

## D13. Two-pass form strategy: explicit 10-K/10-Q, then discovery fallback (07-05)

- Context: the owner mandate names 10-Ks and 10-Qs; the corpus service
  originally hardcoded a discovery policy whose interim slot often selects
  8-Ks. After #2431 added explicit form passthrough, pure-explicit requests
  fail closed for foreign private issuers that have no 10-K to find.
- Alternatives: (a) discovery-only, which loses the 10-Q guarantee; (b)
  explicit-only, which blocks foreign issuers; (c) per-ticker two-pass -
  explicit `10-K`/`10-Q` first, discovery fallback on named failure.
- Decision: (c).
- Why optimal: maximizes the mandated form pair where it exists, degrades to
  other applicable forms exactly where domestic forms cannot exist, and records
  which pass served each ticker for provenance.
- Evidence, verified/corrected by M-PROGRAM-CONTEXT-2: the current aggregate
  report records 39 supported filings / 21 supported issuers: 18 full domestic
  10-K/10-Q pairs, MSFT with a supported 10-Q and named 10-K block, and
  CURLF/CRLBF supported 40-F filings. SONY/CCJ/DNN/NXE/MT/TSM annuals remain
  retained but blocked as the IFRS follow-up group.
- Revisit when: an owner mandate wants per-form-family targeting, such as all
  10-Qs of a fiscal year. Explicit passthrough supports form-family selection;
  fiscal-year filters and all-matches selection remain future selection work.

## D14. Vendored SEC inline-transforms plugin over Arelle upgrade or reimplementation (07-05)

- Context: payload-authored operator context reported a uniform 8-model-error
  pilot block, a refuted 2026-taxonomy hypothesis, and isolation of the errors
  to `ix11.11.1.2:invalidTransformation` on the SEC transformation registry
  namespace for cover-page dei facts. The committed fix lane then vendored the
  SEC transform plugin and loaded it through the helper.
- Alternatives: (a) upgrade Arelle; (b) whitelist that error class in the H3
  blocker; (c) reimplement the transforms from spec; (d) vendor the canonical
  Arelle/EDGAR implementation as an in-repo plugin loaded by the helper.
- Decision: (d).
- Why optimal: (a) was verified as a dead end; (b) silently drops typed values
  and reintroduces the degradation class H3 exists to kill; (c) adds fidelity
  and maintenance risk; (d) keeps the offline/pinned posture with no new runtime
  network dependency and fails closed if the plugin cannot load.
- Evidence: #2432; plugin and pinning under `tools/arelle_sec_transforms/`;
  helper load and model-error-code diagnostics in `tools/sec-xbrl-arelle.py`;
  tests in `backend/tests/test_sec_xbrl_arelle_helper.py`. The #2433 record
  carries the operator re-probe claim that the previously blocked filing reached
  `model_error_count=0`.
- Retro-explanation locked in: June's STLD 523-fact success was never
  contradictory; financial facts use standard ixt transforms, while cover-page
  facts use ixt-sec.
- Revisit when: SEC publishes a new transformation registry version, or
  arelle-release absorbs the registry into core.

## D15. Size-cap: ceiling-only raise, default untouched (07-04, owner-authorized)

- Context: the owner authorized raising the filing size cap with justification.
  Large-cap 10-K complete-submission texts routinely run 50-150 MB; the prior
  25 MB ceiling would have blocked much of the authorized matrix.
- Alternatives: (a) raise the default limit; (b) raise only the ceiling from
  25 MB to 200 MB and keep the default at 25 MB, arming larger limits per-run
  through env.
- Decision: (b).
- Why optimal: preserves the default fail-closed posture for every non-corpus
  consumer; the corpus run arms 150 MB per-run under the new ceiling, while
  200 MB covers realistic large filings and bounds single-artifact memory/disk.
- Evidence: #2427 H5 and tests proving default-limit behavior unchanged.

## D16. Taxonomy provisioning: operator-fetch-then-pin, fail-closed on unpinned (07-04 to 07-05)

- Context: multi-year provisioning needed pins that did not exist; archives live
  across two hosting eras, with FASB dated names pre-2022 and SEC suite zips
  using different internal layouts across years.
- Decision: the operator fetches official archives, computes sha256 and bytes,
  and a repo lane commits pinned specs. The tool refuses unpinned/partial years
  fail-closed. 2019/2020 SEC suites are recorded as explicitly partial rather
  than masqueraded as complete.
- Why optimal: pins make provisioning reproducible and tamper-evident without
  granting agent lanes network access; explicit-partial beats silent-partial.
- Evidence: #2428 historical pins, #2429 dual-layout extraction, #2430 2026
  pins; `tools/sec-xbrl-arelle-provision.py`; and
  `backend/tests/test_sec_xbrl_arelle_provisioning.py`. The source payload also
  reported a runtime provisioning state of 12/12 packages and 24/24 entrypoints,
  but M-PROGRAM-CONTEXT-2 did not locate the named runtime report under
  `C:/p6store`.

## D17. Owner inputs run as-given; corrections run as supplements (07-05)

- Context: the owner ticker list contained TSMC, while Taiwan Semi's SEC ticker
  is TSM, and three non-SEC listings: KAP, PDN, YCA.
- Decision: run every row exactly as written as named `company_matrix_unknown`
  dispositions, and run the obvious correction TSM as a clearly labeled
  supplemental row.
- Why optimal: silently rewriting owner input corrupts the authorization trail;
  dropping the correction wastes an obviously intended issuer. Both facts belong
  in the record.
- Evidence: the aggregate report has per-ticker entries for TSMC as written and
  `TSM(supplemental)`.

## D18. IFRS taxonomy family: deferred as a named follow-up, not silently absorbed (07-05)

- Context: six foreign issuers' annuals (SONY/CCJ/DNN/NXE/MT/TSM) were acquired
  and retained but blocked with `arelle_model_errors_present`; the IFRS taxonomy
  family was not provisioned.
- Alternatives: (a) block corpus close on IFRS provisioning; (b) whitelist the
  error class for foreign filings; (c) close the corpus with named dispositions
  and queue an IFRS-pins lane with concrete acceptance criteria.
- Decision: (c).
- Why optimal: the owner mandate centers 10-K/10-Q with foreign forms as
  applicable/feasible; the filings are banked and replayable at zero egress cost
  once pins land.
- Acceptance criteria for the follow-up: operator-fetched and hashed
  `ifrs-YYYY` packages pinned; year/family admission extended to the IFRS
  family; previously blocked annuals rerun to supported-or-named-block with
  zero new SEC egress.

## Operational Lessons Register (07-05)

- Request bindings replay blocked results for a reused `client_request_id`;
  every rerun mints fresh ids.
- `Base.metadata.create_all` requires model modules imported first; import
  services/models, then run `create_all`.
- Shell backgrounding dies with the tool session; long operator runs use
  harness-managed background execution, and per-ticker isolation makes batch
  splits cheap.
- The helper now exports model error codes, never values, so diagnosis no longer
  requires an operator API probe (#2432 observability fix).

## D19. CYD family-vintage admission by reason-code registry, not history rewrite (07-05)

- Context: the 2026-07-05 corpus-go record left MSFT with a supported 10-Q and
  a named 10-K block. PR #2436 then pinned the SEC CYD 2024 family and added
  `taxonomy_family_vintage_unprovisioned` for family-specific taxonomy gaps.
  The Phase-2 operator replay used retained receipts and zero egress to rerun
  the MSFT FY2025 10-K against the governed helper path.
- Alternatives: (a) rewrite the original #2433/#2434 39-filing record; (b)
  leave MSFT as an open named block until another live corpus run; (c) append a
  hash-only supersession addendum for the governed replay.
- Decision: (c). The prior 39-filing record remains the historical record; the
  current addendum records the later MSFT 10-K supported-equivalent outcome and
  updates the current corpus distribution to 40 supported filings and 19 full
  domestic 10-K/10-Q pairs.
- Why optimal: the replay was receipt-bound, zero-egress, hash-anchored, and
  independently regraded. Rewriting the old record would blur provenance, while
  waiting for a fresh live run would add egress to prove a retained-evidence
  delta. A supersession addendum keeps both states true in time.
- Evidence: PR #2436 (`fc141039`) for the CYD family pin and reason code; PR
  #2435 (`fab89ced`) for the gate registry; provisioning report hash
  `04b3e9354cf92ffd6221d2859b64d2e60c698df323938e5e4614cf9b861ff159`;
  governed replay parser receipt
  `4bf632ece7dc4a0c23661d954b8f4475c7f4e0e26303eb6a20b68469ad8ba911`;
  evidence bundle hash
  `e1b15bd206ee271fbd4131f7cb083f71f04573a4bbc318bb51b4f531dbd00199`;
  independent regrade hash
  `214f2f1014d3ecc06f7e49fd6ce1fc2d17a1811ce53452966d5381329aadff6d`;
  verdict `PASS_WITH_ATTESTED_FIELDS`.
- Operator lesson: filed-year and taxonomy-year are not equivalent. MSFT FY2025
  filed in 2025 can import `us-gaap-2024` and `cyd-2024`; family-vintage
  detection must follow schema references and the pinned package registry, not
  the filing fiscal year label.
- Registry lesson: `cyd-2025` exists upstream as loose files only; the XSDs are
  reachable while a zip archive is not available. The IFRS phase will need an
  operator-built deterministic zip with per-file provenance before admitting
  `cyd-2025` for the three affected IFRS annuals. The local enumeration artifact
  is `ifrs-cyd-vintage-enumeration.md`, sha256
  `72391c5da90bb3e3439979fcf23106f0b664617e6a091b5a153bf3978ca896e4`;
  it is cited by name and hash only, not committed.
- Revisit when: the IFRS follow-up pins `ifrs-2025-03-27` and a governed
  deterministic `cyd-2025` package, then reruns the remaining annuals to
  supported-equivalent or named-block outcomes.

## 2026-07-06 Program-Context Decision Addendum (M-PROGRAM-CONTEXT-3)

This section appends D20-D26 from the 2026-07-05/06 program arc. The
landing lane re-verified PR states and merge SHAs for #2435, #2436, #2437,
and #2438; re-hashed the durable files named below; and re-checked the
source/default and workflow anchors before admitting these decisions. Where
evidence is operator-local, this record admits only hashes, counts, policy ids,
and operator-attested framing.

## D20. cyd-2025 provisioning uses a deterministic operator-built zip (07-06)

- Context: the remaining IFRS annual follow-up references two taxonomy-family
  gaps: IFRS 2025-03-27 and, for three retained annuals, SEC `cyd-2025`.
  The earlier CYD closeout proved `cyd-2024` is available as a zip and can be
  pinned through the existing archive machinery, but the local enumeration
  artifact shows `cyd-2025` exists upstream as loose files rather than a zip.
- Alternatives: (a) extend the provisioner to support loose-file pin specs;
  (b) skip `cyd-2025` and leave the annuals blocked; (c) have the operator
  fetch the enumerated loose files, record per-file provenance, build a
  deterministic zip, and pin that zip through the existing archive path.
- Decision: (c). The operator builds a deterministic local `cyd-2025` zip with
  sorted entries and fixed metadata after recording per-file source URL, fetch
  date, and sha256 evidence.
- Why optimal: it reuses the already proven archive/extraction machinery from
  #2436, avoids a schema and verification-loop code change for a single known
  vintage, remains reversible, and makes the resulting zip hash re-derivable
  from the recorded per-file hashes.
- Evidence: #2436 `fc141039` for CYD family pinning and flat archive handling;
  `ifrs-cyd-vintage-enumeration.md` hash
  `72391c5da90bb3e3439979fcf23106f0b664617e6a091b5a153bf3978ca896e4`;
  current source has `sec-cyd-2024` pin/test coverage and no admitted
  `cyd-2025` zip.
- Revisit when: a second loose-file taxonomy family appears. At that point,
  general loose-file pin support may be justified.

## D21. Enumeration-before-fetch governs IFRS/CYD taxonomy egress (07-06)

- Context: receipt-level enumeration showed all six blocked foreign annuals
  reference exactly IFRS 2025-03-27, while the CYD lesson showed family
  vintages can be required without matching a filing fiscal-year label.
- Alternatives: (a) fetch a broad multi-year IFRS span; (b) defer all IFRS
  work; (c) enumerate retained artifacts first, then request only the exact
  taxonomy vintages needed.
- Decision: (c). Before any taxonomy egress, enumerate required families and
  vintages from retained artifacts, record that enumeration as the grant input,
  and fetch only the named set under owner authorization.
- Why optimal: it minimizes egress, keeps the authorization surface concrete,
  and prevents replay cycles from discovering new taxonomy gaps only after
  fetch approval has already been spent.
- Evidence: `ifrs-cyd-vintage-enumeration.md` hash
  `72391c5da90bb3e3439979fcf23106f0b664617e6a091b5a153bf3978ca896e4`; #2437
  D19 lesson that filed-year and taxonomy-year are not equivalent.
- Revisit when: retained artifacts are insufficient and a live acquisition
  grant is separately authorized.

## D22. Orchestrated delegation uses ack-gated dispatch and scoped independent verification (07-06)

- Context: the 2026-07-05/06 arc used an orchestrator, repo-lane workers, and
  independent reviewer/regrader agents. The failing classes were not
  implementation failures alone; they were lost mandates, stale hashes, wrong
  distribution summaries, and self-graded operator claims.
- Alternatives: (a) trust worker self-verification; (b) review only after
  merge; (c) require mandate-specific dispatch acknowledgment, blocking
  independent verification, and pre-merge review threads while CI runs.
- Decision: (c). In orchestrated multi-lane programs, a lane is dispatched only
  after the worker rollout acknowledges the specific source mandate. A lane is
  marked program-PASS only after the orchestrator re-verifies fence, source
  defaults, review-thread state, and decisive operational evidence where those
  checks are relevant to the lane. This is a program-pass discipline, not a
  universal GitHub merge blocker: Tier-1 docs/report lanes still follow the
  canonical merge policy of self-verification plus CI and resolved threads,
  with independent pre-merge review required only for the policy's concrete
  risk triggers or when ambiguity remains. Operator-only evidence is exported
  as hash-anchored bundles and regraded separately, with non-re-derivable fields
  labeled operator-attested.
- Why optimal: it binds assurance to the exact failure points observed in this
  program and makes review blocking before merge instead of advisory after the
  fact.
- Evidence: #2437 review caught the stale-hash current-pointer trap before
  merge; `CYD_PHASE2_REGRADE.md` hash
  `214f2f1014d3ecc06f7e49fd6ce1fc2d17a1811ce53452966d5381329aadff6d`
  records `PASS_WITH_ATTESTED_FIELDS` with zero hash mismatches and named
  attested-only fields.
- Revisit when: an automated dispatcher can prove source-mandate delivery and
  review-thread state without relying on transcript inspection.

## D23. Heavy local Python/Arelle work serializes per machine (07-06)

- Context: one Windows machine can host the orchestrator and multiple worker
  lanes. Repeated local pytest, xdist, and Arelle runs compete for CPU, memory,
  and filesystem handles.
- Alternatives: (a) let each agent choose concurrency independently; (b) ban
  local heavy checks; (c) serialize heavy local processes per machine, cap
  worker counts locally, and shift soak/repeat iterations to isolated CI when
  possible.
- Decision: (c). Local heavy runs serialize by machine, not by agent; repeated
  local xdist runs must state an explicit cap such as `-n 4`; soak loops should
  move to CI or run strictly one process at a time under contention.
- Why optimal: it preserves validation quality without turning local hardware
  contention into flaky evidence or locked worktrees.
- Evidence: #2438 recorded local proof under `-n 4`, ten strictly serial soak
  runs, and CI `-n auto` only on isolated GitHub-hosted runners.
- Revisit when: local agents run on isolated machines or a machine-level
  scheduler exists.

## D24. Coverage speedup roadmap is A-first, B-gated, and semantics-aware (07-06)

- Context: investigation found `backend-coverage` was the release-gate critical
  path, with a serial pytest step rerunning the Layer 3 API suite already run
  in shards. The correctness risk was not speed; it was preserving the
  coverage threshold over the same covered line set.
- Alternatives: (a) in-job pytest-xdist while preserving job id, targets, glob,
  and `--cov-fail-under=90`; (b) shard-combine redesign that removes the
  duplicate job; (c) hotspot pruning; (d) broaden release-gate needs.
- Decision: land (a) first. Consider (b) only if the post-A residual matters;
  do (c) only after A's real numbers; surface (d) as an owner governance
  decision, not an engineering default.
- Why optimal: pytest-cov's native xdist combine preserves one threshold
  evaluation over complete coverage data, while shard-combine redesign is the
  place incomplete coverage can silently pass due to path aliasing or missing
  data.
- Evidence: #2438 `be8efadb` changed only `.github/workflows/playwright.yml`
  and `backend/tests/requirements-layer3-api.txt`; PR proof records exact
  covered-line-set parity, 2659/2659 collect parity, floor-trip failure at
  88.86%, and 10/10 capped soak runs; post-merge main run `28776807974`
  recorded `backend-coverage` success in 494 seconds.
- Revisit when: `backend-coverage` remains the dominant release-gate delay
  after #2438, or the owner wants a release-gate dependency change.

## D25. Lane completion is detected by bounded polling, not persistent watchers (07-06)

- Context: long-lived watcher processes died with parent sessions during the
  arc and masked state transitions. Completion evidence ultimately lived in
  explicit inbox reports, PR state, CI checks, and post-merge proof.
- Alternatives: (a) trust persistent watcher processes; (b) require manual
  status checks only; (c) use short-lived polling plus explicit source-of-truth
  rechecks.
- Decision: (c). Use restart-safe polling for handoff/report discovery, then
  re-check PR state, review threads, CI, main SHA, and local proof surfaces from
  authority before declaring a lane passed.
- Why optimal: each observation is cheap, stateless, and re-grounded in current
  authority; no resident process becomes an implicit source of truth.
- Evidence: this program's closeout lanes already require PR/CI/thread
  re-query and inbox report verification before done.
- Revisit when: a durable monitor writes signed, replayable state transitions.

## D26. Current-pointer fields must carry supersession pointers (07-06)

- Context: #2437 review found that `latest_*`/current summary fields could
  still quote superseded aggregate hashes while the historical record was
  otherwise correctly preserved.
- Alternatives: (a) rewrite historical entries; (b) leave current-pointer
  fields stale; (c) preserve history and add one-line corrected-value pointers
  wherever a current pointer would otherwise resolve to a known-superseded
  fact.
- Decision: (c). Historical entries remain intact, but current-pointer
  surfaces such as `MASTER_CONTEXT`, `latest_*` status fields, and forward-plan
  summaries get dated supersession notes when they quote a superseded hash,
  distribution, or status.
- Why optimal: it preserves provenance while removing the reader trap that a
  "current" field can point to a known-wrong value.
- Evidence: #2437 `c6bb87f8` corrected the corpus-40 current-pointer class;
  this lane refreshes `docs/MASTER_CONTEXT.md` under explicit authorization.
- Revisit when: current-pointer fields are replaced by generated pointers from
  the evidence registry.

## 2026-07-06 Program-Context Decision Addendum (M-PROGRAM-CONTEXT-4)

This section appends D27 after the #2440 `cyd-2025` pin lane. PR #2441
re-verified #2440 state, code/test anchors, operator-local artifact
hashes, archive member hashes, and the post-#2440 provisioning report before
admitting this addendum. Machine-local evidence remains hash-only, and this
addendum admits no production-readiness, default-on, value-reveal, raw-value,
or new live-egress claim.

## D27. Generic owner directives authorize only established egress classes (07-06)

- Context: after the owner's 2026-07-06 generic "proceed as you see fit"
  directive, two taxonomy actions were queued: `cyd-2025` under the established
  `xbrl.sec.gov` taxonomy host class, and IFRS 2025-03-27 under a new host
  class involving `ifrs.org` / `xbrl.ifrs.org`. D21 and the G7 live-egress
  rule were created to prevent generic prompts from becoming blanket authority
  for new irreversible egress classes.
- Alternatives: (a) treat generic proceed as blanket egress authorization; (b)
  require a named grant for every egress action including established classes;
  (c) apply generic directives only inside host/request classes already
  established by prior named grants and sustained operator precedent, while
  freezing at any new host class until a named grant states host and budget.
- Decision: (c). Generic owner directives flow through established egress
  classes, currently including bounded `xbrl.sec.gov` taxonomy-host fetches
  and SEC EDGAR filing fetches only under an active corpus grant. A new host
  class requires a named owner grant that identifies the host class and request
  budget before the first request.
- Why optimal: it preserves velocity where the owner has already accepted the
  egress class while keeping the first use of a new host class objective,
  auditable, and explicitly owner-controlled. The boundary is simple: a host
  class with no prior named grant or sustained accepted precedent is new.
- Evidence: `CYD2025_FETCH_ARMING.json` hash
  `af704db4bf1b171bd1a8bea7a6b03fcf7bbd57e8f1a92cdadc02256ef5f490f6`
  records `xbrl.sec.gov` only, budget 10, written-before-first-request, and
  explicitly does not authorize `xbrl.ifrs.org`; #2440
  `6d962b24` merged the `cyd-2025` pin lane under the established class.
- Subsequent frontier: #2442 `e7e9e867` pins the retained local IFRS 2025
  package and verifies package-set/sidecar admission. That narrows F3, but
  it does not convert generic owner directives into blanket authorization for
  future first-use host classes or new live vintages, and it does not publish
  foreign-annual replay/result outcomes.
- Revisit when: an owner grant explicitly names a new host class and request
  budget, or when the project adds a durable authorization registry that can
  classify egress classes mechanically.

## 2026-07-06 Corpus 46 Decision Addendum (M-CORPUS-46-RECORD)

This section appends D28 after the owner-named IFRS grant, PR #2442, and the
retained foreign-annual replay closeout. This lane re-verified the owner grant
record, request ledger, retained IFRS package hash, r3 provisioning report,
six replay result rows, evidence bundle, independent regrade, and PR states for
#2437, #2440, #2441, and #2442 before admitting this decision. Machine-local
evidence remains hash-only. This addendum admits no production-readiness,
default-on, value-reveal, raw-value, live SEC EDGAR egress, new unbounded
taxonomy egress, or local path claim beyond the established `C:/p6store` root.

## D28. Budget-constrained fetch strategy for named new-host grants (07-06)

- Context: D27 required a named host-and-budget grant before first-use IFRS
  taxonomy egress. The owner then granted an IFRS Accounting Taxonomy fetch
  from the IFRS host class with a request budget of 5 or fewer requests. The
  grant was enough to acquire the needed retained package, but only if the
  lane avoided speculative browsing and recorded budget use before the first
  request.
- Alternatives: (a) use the grant as broad host-class permission; (b) refuse
  until every candidate URL is known; (c) write an arming record before any
  request, order attempts by expected information per request, interleave
  zero-cost research, use metadata-only checks before content fetches where
  uncertain, keep a per-request ledger, and stop at the budget ceiling.
- Decision: (c). A named new-host grant must be translated into a concrete
  arming record before egress, then executed as a finite request ledger. The
  ledger, not intent, is the admissible authority for later pinning and replay
  records.
- Why optimal: it preserves D27's explicit-owner boundary while letting a
  narrow taxonomy fetch complete without pretending the host class is now open
  ended. It also makes failure clean: if the budget is exhausted, the exact
  unresolved candidate set is reported rather than silently expanding the
  authority.
- Evidence: `IFRS2025_FETCH_ARMING.json` hash
  `cb275a03cbbadfcdb55a8eedc3d585f8dd5eb6cb4c9a8b45bac986ceb080b8f6`
  records `written_before_first_request=true`, the owner grant text, allowed
  IFRS host class, and request budget 5. The PINNING note hash
  `20dfec68cccba35eb9969763ec056ac568824dd0df5f5b9c43151ac854945c07`
  records the 5/5 request ledger. `IFRSAT-2025.zip` hashes to
  `302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19`
  at 2,103,003 bytes; PR #2442 pins/adopts it. The r3 provisioning report
  hash `6ff72308060a5769ff708b556bc3e9a6269ac867b1f06eaa6d0291f4a8a9708c`
  reports `ready=true`, 13/13 packages loaded, 26/26 SEC entrypoints intact,
  and IFRS 2025 offline entrypoints loaded.
- Revisit when: the project adds a durable authorization registry, or when a
  future taxonomy family requires repeated host-class fetches rather than one
  bounded package acquisition.

## D29. Coordination-record provenance is archived by hash, not raw-log commits (07-06)

- Context: D5 uses PR #2415 as the campaign's Tier-2 merge-gate evidence, but
  the mutable dual-agent inbox substrate that carried the implementer narrative
  and closeout record was not itself durably anchored.
- Alternatives: (a) commit raw inbox logs; (b) summarize without an integrity
  anchor; (c) copy the inbox coordination set to
  `C:/p6store/inbox-archive/2026-07-06/`, then commit only hash and section
  pointers.
- Decision: (c). The primary PR #2415 narrative lives in archived primary
  inbox-log sections `M-A8-RUNTIME-GO REPORT 1`,
  `M-A8-RUNTIME-GO REPORT 2`, and `M-A8-RUNTIME-GO REPORT 3`; this record
  cites those markers by name and does not quote or commit the log.
- Why optimal: the archive preserves point-in-time review provenance while I2
  still keeps raw logs, local coordination chatter, and machine-specific
  details out of git history. Hash-only admission makes the snapshot
  re-checkable without converting agent inbox files into durable source files.
- Evidence: archived primary inbox-log sha256
  `861b55ec3ceb1a9bffd4faaf3e985f6d9d14ad800daafc63ec48f18a5597c1b7`
  under `C:/p6store/inbox-archive/2026-07-06/`; archive manifest aggregate
  sha256 `42cd507ba527597fa5ab4128889ac5cf7caef3d213debd6cab65a19b4fb3a337`
  for 50 copied files / 2,140,077 bytes. The archived inbox shows
  `M-A8-RUNTIME-GO REPORT 2` records the implementer's paraphrase of the
  independent round-1 `NEEDS-CHANGES` findings (F1-F6); it contains no
  independent bracketed-reviewer `APPROVED` verdict block for PR #2415. The
  archived dispatch inbox log contains this durability-lane dispatch reference
  to PR #2415 but no A8 report narrative or independent verdict block. Live
  GitHub state for PR #2415 is `MERGED`, with one `COMMENTED` bot review, zero
  PR comments, and four resolved review threads. PR #2415 closure is therefore
  anchored by the merge action plus `M-A8-RUNTIME-GO REPORT 3`, not by a
  separate inbox approval verdict.
- Revisit when: the repo gains a signed coordination-log export, or when
  inbox/source-payload archival becomes automated at lane closeout.

## D30. Content-uniqueness verdicts must grep the current refactored layout, not pre-refactor paths (07-06)

- Context: the 2026-07-06 dirty-worktree adjudication and its later
  deep-dive verification corrected two path-sensitive verdicts.
  `worktrees/l3-package-life` was a false `UNIQUE-CONTENT` result because
  the check grepped stale pre-refactor `backend/app/api/layer3.py` paths after
  current main had moved the live surface into a `layer3/` package.
  `worktrees/sec-family-res` also showed that landed SEC XBRL feature concepts
  can move under renamed files while a divergent `.v1` variant remains an
  owner-review item.
- Alternatives: (a) adjudicate preserved content by original worktree paths or
  branch ancestry alone; (b) require manual file-by-file proof for every
  dirty worktree without reusable mechanical checks; (c) require repo-wide
  symbol greps against current main, tree-identity checks where an old commit
  can be compared to its merge (`git diff <sha> <merge> --numstat` empty means
  fully landed), enumeration with `git status --porcelain --ignored
  --untracked-files=all --ignore-submodules=none` or an equivalent recursive
  ignored-directory hash inventory, and a directory inventory outside
  `git worktree list`.
- Decision: (c). Any future content-uniqueness verdict against rebuilt main
  must search the current layout, not just the path shape that existed when
  the old worktree was authored. A clean status or clean worktree list is not
  sufficient evidence when ignored `archive/` payloads or unregistered plain
  directories may exist.
- Why optimal: this preserves the owner-gated cleanup posture without turning
  stale paths into false retention or false discard decisions. It also makes
  the proof portable across refactors: symbols, tree identity, ignored-content
  enumeration, and plain-directory discovery each check a different failure
  mode.
- Evidence: `state/agent-inbox/worktree-unlanded-deepdive-2026-07-06.json`
  hashes to
  `03f50a85e452121ddc65af4cecf3ba8f7cf98fb6e84f1dd1c9c3398a5c46c5fd`
  at 132,716 bytes and records the corrected dispositions plus the
  path-refactor and enumeration failures. `state/agent-inbox/worktree-disposition-plan-v2.md`
  hashes to
  `ca5b06307ac2a6c3fdcdea932fae97ad49264677c82b361eb84555b9e7984afa`
  at 8,169 bytes and translates the corrections into the cleanup execution
  discipline. The I12 archive aggregate
  `9291ee34af6c510329818488b2bfe834559308def95bd3cfdb58b537a1a392ea`
  anchors the same-day adjudication record set without committing raw local
  logs.
- Revisit when: the worktree cleanup tool mechanically enforces ignored
  enumeration, unregistered-directory inventory, and refactor-aware
  symbol/tree checks before proposing any discard or uniqueness verdict.

## D31. IMF envelope-grant execution stops on policy signals, not workarounds (07-08)

- Context: the IMF DataMapper build lane remained blocked after the official
  help page failed to publish a response-envelope example. The owner then
  granted a narrow D27 envelope-pin authorization: `www.imf.org` only,
  `/external/datamapper/api/v2` only, four counted GETs total, envelope pin
  only, and no pilot, sweep, bulk download, production ingest, SDMX/portal
  probing, or workaround behavior.
- Alternatives: (a) leave IMF deferred-final; (b) treat the grant as license
  for retries, browser/WAF evasion, or broader DataMapper probing; (c) arm a
  D27 record before egress, make only the minimal planned request, and stop on
  any grant hard-STOP signal.
- Decision: (c), executed. The arming record was written before live egress.
  `GET 1/4` to the v2 indicators family returned HTTP 403, which the grant
  defined as a hard STOP. No contingency request was used, no envelope was
  pinned, and no connector build started. IMF remains owner-gated/deferred.
- Why optimal: a 403 is source behavior, not an engineering puzzle to bypass.
  Stopping preserved the anti-bulk and no-workaround posture, converted the
  failed pin into durable evidence, and avoided spending contingency requests
  on a condition the owner explicitly classified as terminal.
- Evidence: PR #2466 `d8f7b6df` records the addendum; the D27/D28 arming
  record `state/agent-inbox/imf-envelope-arming-record.md` records request
  `1/4`, HTTP 403, 418 bytes, no redirect, no retry, and zero contingency
  spent.
- Revisit when: the owner either accepts IMF as deferred-final, or supplies a
  manual browser-captured envelope sufficient for a zero-egress rebuild. Future
  automated WAF, account-gated, SDMX/portal, or retry-workaround paths remain
  refused unless a separate owner decision changes the source class.

## 2026-07-08 Admission-Spine Decision Addendum (M-ADMISSION-MAP)

Verification preamble: this addendum was written against live
`project6-origin/main` tip `ee87e5765427c9cbd9d3f4609fd8379afd47b0a7`,
with line anchors re-derived in the execution worktree and no D-numbering
renumbered or backfilled.

## D32. Source-artifact admission map becomes the local-depth program spine (07-08)

- Context: the owner admission-spine brief at
  `state/agent-inbox/decision-brief-2026-07-08.txt` and the owner "proceed"
  authorization select the next program as a shared source-artifact admission
  spine for connector-produced material that claims downstream Layer 3 use.
  The connector-breadth wave expanded the anonymous/public acquisition surface;
  the next gap is not more connector breadth, but a common proof contract for
  source artifacts, processor profiles, material preview, Gate B/C, 3C, and
  package/handoff state.
- Alternatives: (a) continue outward connector acquisition before fixing the
  local admission proof axis; (b) treat connector `supported` status as
  sufficient Layer 3 material admission; (c) publish a docs-only admission map
  first, park OD-6 and the outward arm without foreclosing them, and declare
  the first migration-forcing pilot as Tier-2 in advance.
- Decision: (c). Publish planning doc 1366 as the Phase 0+1
  source-artifact admission-map contract, record the posture ladder as a
  documentation/proof axis rather than support-matrix statuses, and use it as
  the current local-depth admission-spine program pointer. OD-6 and the
  outward connector arm remain parked, not rejected. Phase 3, the ScienceBase
  direct-envelope pilot, is declared Tier-2 in advance because
  `L3SourceIntakeRecord` CheckConstraints in `backend/app/models/models.py`
  force a migration.
- Why optimal: the map separates acquisition/provenance adapters from the
  downstream authority surfaces they must not own. It preserves current
  behavior as evidence, documents seams before refactor, avoids smuggling new
  support-matrix states into the selected profile, and makes the first
  migration-bearing pilot explicit before implementation pressure appears.
- Evidence: owner brief
  `state/agent-inbox/decision-brief-2026-07-08.txt` hashes to
  `ec81e1ca25edb4621fe62146a0de1662f79452be457b08fee8356e5cdbf590b9`;
  planning doc 1366 records the live anchor map and the Phase 0-7 sequence;
  this D32 addendum records the owner "proceed" authorization and the
  Tier-2 declaration for the ScienceBase direct-envelope pilot.
- Revisit when: a Phase 2 neutral NRC APS facade, a Phase 3 ScienceBase
  direct-envelope pilot, or the first Phase 4 shape pilot is ready to move
  from documentation/proof posture into code. Any support-matrix, schema,
  migration, live-pilot, nonlocal-admission, connector-source-default, or
  production-readiness expansion requires its own explicit lane and proof.

## 2026-07-13 Admission-Spine B1 Owner-Ratification Addendum

Provenance qualification: the decisions below were supplied in direct current-
owner chat and relayed into the records lane. The precise owner decision
timestamp was not provided, the message identifier was not exposed, and no
independent owner artifact was provided. Those facts are not inferred. The
operator-held ratification receipt is identified below by basename, byte count,
full SHA-256, and canonical self-hash; it is not a repository-carried file.

## D33. Ratify the complete v1 identity-metadata enumeration exactly as proposed (07-13)

- Context: B1b promotion identity needs one owner-settled v1 field contract
  before any later build packet can be evaluated. A partial field-name summary
  would omit the proposal's null, normalization, canonical-JSON, versioning,
  equivalence, and persistence-design semantics.
- Alternatives: (a) leave the enumeration unresolved; (b) ratify only the three
  inner hash fields; (c) ratify the complete 58-disposition proposal with no
  overrides.
- Decision: (c). `ENUMERATION_DISPOSITION=RATIFIED-EXACTLY-AS-PROPOSED`;
  disposition count `58`; overrides `NONE`. Identity version is
  `layer3.connector_source_intake.identity_metadata.v1`. The outer tuple axes
  are `source_family` and `content_sha256`. The inner metadata-hash fields are
  `connector_key`, `sciencebase_item_id`, and `media_type`.

| # | Field | Ratified v1 disposition |
|---:|---|---|
| 01 | `source_family` | INCLUDE — outer tuple axis only |
| 02 | `content_sha256` | INCLUDE — outer tuple axis only |
| 03 | `connector_key` | INCLUDE — inner hash |
| 04 | `sciencebase_item_id` | INCLUDE — inner hash |
| 05 | `media_type`, including canonical charset/parameters | INCLUDE — inner hash |
| 06 | `client_request_id` | EXCLUDE |
| 07 | `connector_run_id` | EXCLUDE |
| 08 | `connector_run_target_id` | EXCLUDE |
| 09 | `freshness_timestamp` | EXCLUDE |
| 10 | `sciencebase_download_uri` | EXCLUDE |
| 11 | `sciencebase_file_name` / `original_filename` | EXCLUDE |
| 12 | `content_size_bytes` | EXCLUDE |
| 13 | `source_label` | EXCLUDE |
| 14 | `source_description` | EXCLUDE |
| 15 | `connector_source_intake_record_id` | EXCLUDE |
| 16 | `operator_decision` | EXCLUDE |
| 17 | `metadata_hash` | EXCLUDE; retained unchanged as lineage fingerprint |
| 18 | `authority_basis_hash` | EXCLUDE |
| 19 | `storage_ref` | EXCLUDE |
| 20 | `provenance_json` | EXCLUDE |
| 21 | `downstream_eligibility_json` | EXCLUDE |
| 22 | `summary_json` | EXCLUDE |
| 23 | `status` | EXCLUDE |
| 24 | `created_at` | EXCLUDE |
| 25 | `updated_at` | EXCLUDE |
| 26 | `schema_id` | EXCLUDE |
| 27 | `mode` | EXCLUDE |
| 28 | `server_authority` | EXCLUDE |
| 29 | `source_gate` | EXCLUDE |
| 30 | `preview_encoding` | EXCLUDE |
| 31 | `gate_b_material_admission_enabled` | EXCLUDE |
| 32 | `gate_b_mode` | EXCLUDE |
| 33 | `csv_only_pilot` | EXCLUDE |
| 34 | `media_type_widening_deferred` | EXCLUDE |
| 35 | `support_matrix_capability_added` | EXCLUDE |
| 36 | `new_http_route_added` | EXCLUDE |
| 37 | `operator_source_intake_table_modified` | EXCLUDE |
| 38 | `generic_source_classes_widened` | EXCLUDE |
| 39 | `support_matrix_changed` | EXCLUDE |
| 40 | `media_type_gate_widened` | EXCLUDE |
| 41 | `absolute_path_exposed` | EXCLUDE |
| 42 | `sciencebase_item_url` | EXCLUDE FROM v1; future consideration DEFERRED |
| 43 | `ConnectorRun.source_system` | DEFERRED; not part of v1 |
| 44 | `ConnectorRun.source_mode` | EXCLUDE FROM v1; future consideration DEFERRED |
| 45 | `stable_release_key` | DEFERRED; not part of v1 |
| 46 | `stable_release_identifier` | DEFERRED; not part of v1 |
| 47 | `identifiers_json` | DEFERRED; not part of v1 |
| 48 | `source_artifact_key` | EXCLUDE FROM v1; future consideration DEFERRED |
| 49 | `canonical_artifact_key` | EXCLUDE FROM v1; future consideration DEFERRED |
| 50 | `remote_checksum_type` | EXCLUDE |
| 51 | `remote_checksum_value` | EXCLUDE |
| 52 | `downloaded_sha256` | EXCLUDE |
| 53 | `etag` | EXCLUDE |
| 54 | `last_modified` | EXCLUDE |
| 55 | `source_reference_json` | EXCLUDE |
| 56 | `permission_snapshot_json` | EXCLUDE |
| 57 | `access_level_summary` | EXCLUDE |
| 58 | `public_read_confirmed` | EXCLUDE |

- Exact semantics: fields 03-05 are non-null. `connector_key` and
  `sciencebase_item_id` are strings, Unicode-whitespace-trimmed,
  NFC-normalized, and case-preserved; empty, missing, or null is invalid and
  unhashable. `media_type` uses full-value parsing, lowercased essence and
  parameter names, duplicate-name rejection, unquote/trim/NFC parameter
  values, an explicit nullable charset, a lowercased charset token without
  alias guessing, and order-independent parameters.
- Canonicalization/version semantics: the preimage is the version `schema_id`
  plus its three-field `fields` object. Serialize with sorted keys,
  ASCII-escaped compact JSON, `allow_nan=False`, UTF-8, no `default=str`, then
  emit lowercase 64-hex SHA-256. Persist the version separately and include it
  in the preimage. Any field, normalization, null, JSON, or version change
  requires a newly owner-ratified version; v1 is never reinterpreted. Missing
  required fields leave version and hash null and make the record P1-ineligible.
- Persistence-design boundary: the nullable version/hash pair, paired-null
  constraint, and non-unique lookup index are ratified as design only. This
  decision authorizes no persistence implementation, schema/ORM edit,
  migration, backfill, or runtime activation.
- Why optimal: the complete contract makes semantic equivalence replayable and
  reviewable without turning request, storage, operator, or mutable runtime
  metadata into identity.
- Evidence: operator-held `b1b-ratification-2026-07-13.md`, 10,942 bytes, full
  SHA-256 `CC56D146D2574CE66E80E0B4BF3DC509B5213BDFD8B9310EC06EF99EE4D5298A`,
  canonical self-hash
  `6B21BC536C49708E72F4B8C15CCE1AE2BEC483C4C659D426F62A8F46CE7AFA9B`.
- Revisit gate: only a new explicit owner-ratified version may change these
  semantics. A separate build authorization is required before implementation.

## D34. Ratify first-committed approved-receipt precedence (07-13)

- Context: repeated Gate-B decisions for one final I1 promotion identity need a
  deterministic collision rule that distinguishes equivalent replay from a
  divergent decision and from a non-approved outcome.
- Alternatives: (a) latest decision wins; (b) every approval mints another
  receipt; (c) first successfully committed approved receipt wins, equivalent
  replay reuses it, and divergence fails closed pending explicit supersession.
- Decision: (c), `PRECEDENCE_DISPOSITION=RATIFIED-AS-PROPOSED`:
  1. For one final I1 identity, the first successfully committed approved
     receipt wins.
  2. A later semantically equivalent approval reuses that receipt and mints no
     new receipt.
  3. A divergent Gate-B decision returns dedicated HTTP `409`
     `promotion_identity_decision_conflict`, mutates zero rows, and requires
     explicit owner authority for supersession.
  4. A non-approved decision mints no receipt and occupies no promotion
     identity.
- Why optimal: this rule makes approval replay idempotent, keeps conflict
  visible, prevents last-writer-wins mutation, and reserves semantic
  supersession for an explicit owner act.
- Evidence: the same operator-held ratification receipt and hashes recorded in
  D33. This rule is distinct from the earlier CT3-08=M1/dual-retention decision
  and does not infer implementation or an intake-uniqueness migration.
- Revisit gate: only explicit owner supersession may replace a committed
  divergent decision. Implementation still requires separate authority.

### Non-decisional second-key status note

This note records current gate state; it is deliberately unnumbered because a
non-grant is not a constructive decision.

```text
SECOND_KEY_STATUS=NOT-GRANTED
SECOND_KEY_FUTURE_INTENT=INTENDED-NON-AUTHORIZING
SECOND_KEY_WITHHELD=NOT-CLAIMED
NEXT_POSTURE=EXPLICIT-SECOND-KEY-OWNER-GATE
```

The records-only alignment lane grants no implementation, schema, ORM,
migration, runtime, build dispatch, B1b build PR, or B1b build merge authority.

`B1A-PASS; B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN; LOOP-NOT-RUN-superseded-by-run; SCHEMA-NOT-CHANGED.`
