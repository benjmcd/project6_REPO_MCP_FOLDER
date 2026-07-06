# 02 — Decision Record

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
