> Tracked forward-frontier record, frozen at PR #2456 (frontier state = main 444d2773 / #2455; the direction fork local-depth vs outward remains OPEN at landing). Source: the untracked living dossier at state/agent-inbox/forward-frontier-dossier.md, sha256 48c6cdd1261bc3fb585982243cc451b5bde77b994132a293766c7b4b9899f06c at landing; this tracked copy publication-normalizes role labels while preserving the dossier claims. This is a dated PLANNING/FRONTIER record subordinate to docs/MASTER_CONTEXT.md and docs/program-context/ (D10: it is not a second master context). Future campaign/frontier records land as siblings in this folder.

# Forward Frontier Dossier — "What comes next?" (started 2026-07-07)

Standalone living document dedicated to ONE question: beyond the immediate next pass, what is
left for this project as a whole — what are we building toward, which lanes/pursuits/decisions
should be prioritized, and which are most critical/valuable to the repo's functionality and
utility. Every entry must be evidence-backed (file/PR/SHA anchors) or carry explicit reasoning.
Maintained incrementally: findings appended as they arrive; corrections dated, never silently
rewritten. Authority order: live project6-origin/main > merged-PR evidence > this dossier.

Baseline at start: main tip `a356f74c` (#2454); the 2026-07-06/07 repo-ops campaign fully
closed (see docs/campaign-records/2026-07-06-repo-ops-campaign.md); zero open PRs.

---

## §0. Orchestrator priors (seed — to be verified/extended by investigation, not trusted)

Known standing gates and pursuit surfaces going in (anchors to be re-verified):
- Program pursuits P2–P7 + F1–F8 frames in docs/program-context/03-forward-plan.md
  (corpus broadening; legacy-reveal disposition P4; nonlocal/production admission P5;
  worktree/branch cleanup P6 [now largely executed]; standing small items P7; horizon
  sequence ending at a default-on consideration that is explicitly a separate owner decision).
- "Deliberately NOT planned" list (03-forward-plan tail): no SEC-value erasure (I1), no
  default-on flips by agents (I3), no second master-context (D10), no new SEC egress while
  retained artifacts suffice (D7).
- Unsupported feature tracks named as SEPARATE architecture/security programs: HA, keyed
  connectors, model egress, real provider delivery, signed-reference export (support matrix).
- Owner-personal queue from the closed campaign: onlook upstream contribution; mass
  remote-branch deletion; /tmp/audit-wt/p6main unlock; held-dirs optional pass.
- A8 arc: value-retention runtime PROVEN with real data (fused D1→O2→O3 operator proof);
  corpus at 46 supported filings / 27 issuers; runtime posture deliberately report_only /
  not_implemented / defaults-false (arming owner-local per run).
- 17B (admitted-issuer production value-reveal) previously adjudicated NOT_READY with 12
  sign-off questions; erasure premise since overturned (retention posture).

Open orchestrator questions for the investigation (do not assume answers):
Q1 What does the repo functionally DO today end-to-end for a user/operator, and where are the
   real capability gaps vs its own documented target state?
Q2 Which pursuits raise FUNCTIONALITY/UTILITY (vs record-keeping/hygiene, which is now done)?
Q3 What is the actual dependency graph between P2/P4/P5/17B/default-on and the unsupported
   feature tracks — what unlocks what?
Q4 What is production/deployment reality (compose stack, admission, auth, observability) vs
   claimed production-grade status — any drift since #2305-#2308?
Q5 What test/CI truth gaps remain (coverage exclusions, skipped suites, OCR/e2e/PG paths)?
Q6 NRC APS product surface: state, users, gaps? Review UI / workbench maturity?
Q7 Anything in backend TODOs/models/routes that reveals unfinished intended features?

---

## §1. Investigation findings (investigation lane — per-pursuit entries)

### Investigation basis

- Live authority checked 2026-07-07: `project6-origin/main` is `a356f74c2ca3ff9b3f14d1f0bbbd6054934f7d44`; `gh pr list --state open` returned `[]`. The matching merged closeout PR is #2454, and the latest inspected main push run was GitHub Actions run `28850989356`, conclusion `success` across the listed jobs.
- Source-read rule used here: tracked-file evidence was read from `project6-origin/main:<path>`, not from the dirty root checkout. The Master Context itself warns that it is narrative/state, not runtime truth, and must be verified against current `project6-origin/main` before action (`project6-origin/main:docs/MASTER_CONTEXT.md:L1-L5`).
- Priority scale for this section: P0 = next agent-executable or owner-decision item with high utility and low ambiguity; P1 = high utility but owner-gated, security-gated, or broad; P2 = useful but secondary or dependent on a concrete operator need; P3 = parked, hygiene-only, or explicitly not planned.

### Capability map

| Area | Current live-main capability | Gap / boundary |
|---|---|---|
| Local operator foundation | The selected profile is `local_expert` with `public_connectors` and `sec_xbrl_offline`, local deployment, no auth boundary, and default-off SEC live/value/agent/nonlocal flags (`project6-origin/main:config/support_matrix.yaml:L1-L18`). Health/readiness/OpenAPI are selected supported capabilities (`project6-origin/main:config/support_matrix.yaml:L47-L50`), and `/health` plus DB-backed `/ready` are live routes (`project6-origin/main:backend/main.py:L510-L523`). | This is not a nonlocal/multi-trust/product-hosted posture; support matrix says no nonlocal capability and no production-ready SEC value reveal/provider/HA/durable queue/multi-executor claim is selected (`project6-origin/main:config/support_matrix.yaml:L8-L18`). |
| Public connectors / analytics | Method-aware analytics, ScienceBase public connector, Senate LDA anonymous connector, connector observability, Layer 3 UI, and health/readiness are `supported` entries (`project6-origin/main:config/support_matrix.yaml:L20-L50`). | Keyed connectors are `unsupported` (`project6-origin/main:config/support_matrix.yaml:L152-L155`), so third-party identity/keyed operation is a separate security/product program, not a small config flip. |
| NRC APS review product | The shipped UI pages are `/review/nrc-aps`, `/document-trace`, `/workbench-compare`, and `/candidate-b-trace` (`project6-origin/main:backend/main.py:L474-L495`; `project6-origin/main:frontend_UI_plans/README.md:L88-L110`). Clean deploy serves 15 core review routes against completed DB pipeline runs (`project6-origin/main:docs/layer3-production-activation.md:L503-L513`). | Eight workbench/Candidate-B routes depend on local corpus fixtures absent from a clean deploy and return errors/empty results until fixtures are staged (`project6-origin/main:docs/layer3-production-activation.md:L515-L521`). Current docs say runtime Candidate B Trace parity, document-trace parity expansion, DB schema/model/migration work, persistence redesign, and new run-submission UI remain out (`project6-origin/main:docs/nrc_adams/nrc_aps_status_handoff.md:L4-L15`). |
| Layer 3 workbench / package flow | `/review/layer3` is live (`project6-origin/main:backend/main.py:L498-L501`) and the status handoff records many bounded slices through planning, approval, execution start, package review, handoff/export prep, APS dispatch, and same-origin delivery (`project6-origin/main:docs/nrc_adams/nrc_aps_status_handoff.md:L254-L263`). | General analysis execution beyond the bounded one-pass start, public/signed URLs, generic downstream dispatch, connector dispatch, destination selection, package mutation/reconstruction, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, LLM planning, and full mockup activation remain out (`project6-origin/main:docs/nrc_adams/nrc_aps_status_handoff.md:L254-L263`). |
| SEC XBRL offline / value authority | Corpus is current at 46 supported filings / 27 issuers, with 6/6 retained IFRS annual zero-egress replays READY and evidence/regrade hashes recorded (`project6-origin/main:docs/program-context/03-forward-plan.md:L257-L285`; `project6-origin/main:docs/MASTER_CONTEXT.md:L58-L76`). A8 value-retention proof is complete with 523 revealed facts / 497 non-empty values, production-readiness false, and source defaults unchanged (`project6-origin/main:docs/MASTER_CONTEXT.md:L173-L199`). | Value reveal, controlled submit, internal store, corpus validation, production admission evaluator, live SEC egress, model egress, and package inventory are pinned false/default-off (`project6-origin/main:config/support_matrix.yaml:L10-L19`; `project6-origin/main:backend/app/core/config.py:L133-L192`). No new SEC egress while retained artifacts suffice and no default-on flips by agents are planned (`project6-origin/main:docs/program-context/03-forward-plan.md:L655-L661`). |
| Deployment / production | The reference compose stack is app + Postgres + nginx auth proxy, with durable DB/storage/export volumes and smoke switches for auth, product-flow probe, and durability (`project6-origin/main:docs/layer3-production-activation.md:L266-L343`). | The same doc says this is a starting point, not a production-hardened blueprint; TLS, secrets, and log aggregation are deployment-owned (`project6-origin/main:docs/layer3-production-activation.md:L266-L270`, `L492-L501`). Compose deliberately omits SEC value-reveal flags and the production-admission evaluator (`project6-origin/main:docs/layer3-production-activation.md:L529-L543`). |
| CI / release proof | Current main run `28850989356` was green by GitHub inspection. Workflow contains required OCR proof with Tesseract (`project6-origin/main:.github/workflows/playwright.yml:L352-L458`), Layer 3 coverage with `--cov-fail-under=90` (`project6-origin/main:.github/workflows/playwright.yml:L542-L569`), Postgres migration/golden-path jobs (`project6-origin/main:.github/workflows/playwright.yml:L571-L622`), Playwright aggregator (`project6-origin/main:.github/workflows/playwright.yml:L679-L692`), and release gate (`project6-origin/main:.github/workflows/playwright.yml:L624-L677`). | Release gate depends on `release-lock-install`, `backend-layer3-api`, `backend-coverage`, `backend-migrations-postgres`, and `sec-xbrl-arelle-provisioning`, but not `root-tests`, `nrc-aps-ocr`, or Playwright `test`; program context marks that as owner-decision because it changes merge semantics (`project6-origin/main:docs/program-context/03-forward-plan.md:L481-L494`). |
| Unfinished route/service signals | Command result / inference: a live-main search over `backend`/`tools` found no broad TODO/FIXME frontier. Meaningful markers are deliberate fail-closed product states: delivery/outbox/webhook `*_not_ready`, signed/private-provider `closed_not_implemented`, and agent model invocation not implemented (`project6-origin/main:backend/app/review_ui/static/layer3.js:L25295-L27338`; `project6-origin/main:backend/app/services/layer3_agent_product_runtime.py:L173-L191`). | Inference: the unfinished frontier is not a generic cleanup backlog; it clusters around explicitly gated delivery/export/provider/model/production surfaces. |

### P2 corpus and future SEC acquisition

- What it is: broaden/record SEC XBRL corpus authority and retained-evidence replay.
- Current state: executed for current retained scope; P2/F3 residual is closed at 46 supported filings, with no remaining resolvable retained foreign-annual replay/result-recording delta (`project6-origin/main:docs/program-context/03-forward-plan.md:L524-L578`).
- Value: inference from the corpus records: more corpus breadth only increases utility when retained artifacts are insufficient for a new functional question.
- Prereqs / gate holder: owner for any additional live acquisition, new vintages, or host classes; agents may run report-only/record-only lanes over already authorized retained evidence (`project6-origin/main:docs/program-context/03-forward-plan.md:L557-L570`).
- Dependency edges: P2 strengthens P5 but does not formally gate it (`project6-origin/main:docs/program-context/03-forward-plan.md:L529-L531`).
- Effort / risk: small-medium for future record-only addenda; Tier-2 only if runtime/persistence behavior changes (`project6-origin/main:docs/program-context/03-forward-plan.md:L571-L578`).
- Recommended priority: P3 until an operator question needs new evidence. Do not spend next cycles re-proving retained corpus.

### P4 legacy Arelle reveal disposition

- What it is: owner labels the legacy Arelle reveal surface as a dormant/superseded sibling to controlled submit.
- Current state: unblocked and independent, but only a one-word owner posture choice plus small Tier-1 label lane remains (`project6-origin/main:docs/program-context/03-forward-plan.md:L528-L531`, `L580-L592`).
- Value: inference from audit cost: low functional lift, modest token/audit savings because future agents stop re-adjudicating the dormant surface.
- Prereqs / gate holder: owner one-liner; no behavior activation allowed (`project6-origin/main:docs/program-context/03-forward-plan.md:L584-L592`).
- Dependency edges: independent; should not bundle with P5, egress, corpus, or controlled-submit work (`project6-origin/main:docs/program-context/03-forward-plan.md:L567-L568`, `L611-L612`).
- Effort / risk: small, low risk if label-only.
- Recommended priority: P2/P3. Worth batching with support-matrix posture work, not worth interrupting functional lanes.

### A8 / 17B controlled value reveal and default-on boundary

- What it is: owner-local controlled SEC value reveal and the later question of admitted/default posture.
- Current state: A8 is closed for the current value-retention arc; the real-data D1 -> O2 -> O3 proof recorded 523 revealed facts, 497 non-empty values, `value_reveal_performed=true`, `production_readiness_claimed=false`, and source defaults unchanged (`project6-origin/main:docs/MASTER_CONTEXT.md:L173-L199`). The old secure-erasure premise is superseded as a category error for public SEC values (`project6-origin/main:docs/MASTER_CONTEXT.md:L348-L356`).
- Current correction to §0 prior: I did not verify the exact "17B ... 12 sign-off questions" wording in the tracked live-main files inspected here; treat that phrase as carried-forward until a specific current-main anchor is supplied. Live-main anchored truth is that reveal proof is A8 evidence, not production/nonlocal admission evidence (`project6-origin/main:docs/MASTER_CONTEXT.md:L193-L199`; `project6-origin/main:docs/program-context/03-forward-plan.md:L596-L600`).
- Value (inference): high for owner-local SEC utility when the owner wants inspected values; not production admission by itself.
- Prereqs / gate holder: owner-local arming per run only; source defaults remain false (`project6-origin/main:docs/MASTER_CONTEXT.md:L197-L199`; `project6-origin/main:config/support_matrix.yaml:L10-L19`).
- Dependency edges: controlled value reveal is separate from P5 admission because P5 admission evidence must have `value_reveal_performed=false` (`project6-origin/main:docs/program-context/03-forward-plan.md:L596-L600`). Default-on is after P5 and is a separate owner decision, not authorized by the horizon (`project6-origin/main:docs/program-context/03-forward-plan.md:L646-L653`).
- Effort / risk: medium/high if expanded; high blast radius for any default/source-posture change.
- Recommended priority: P1 only if the owner wants another controlled local value exercise; default-on remains P3/blocked until after explicit P5 success and owner authorization.

### P5 nonlocal / production admission

- What it is: admit the SEC XBRL value/production posture for nonlocal deployment.
- Current state: 6 of 7 gate criteria pass; sole blocker is the human/operator final-admission packet, evaluator default-off, and reveal proofs are not admission evidence (`project6-origin/main:docs/program-context/03-forward-plan.md:L594-L616`). The admission evaluator fails closed when the flag is disabled and requires all criteria (`project6-origin/main:backend/app/services/layer3_sec_xbrl_production_admission.py:L1-L17`, `L176-L257`).
- Value: inference from product direction: this is the largest single unlock if the owner wants project6 to move from local/offline proof to nonlocal production use.
- Prereqs / gate holder: owner/operator supplies final admission and backfill-disposition packets plus nonlocal deployment evidence; evaluator is enabled only for evaluation (`project6-origin/main:docs/program-context/03-forward-plan.md:L601-L608`).
- Dependency edges: depends on final-admission packet, settled semantics, durable posture, and record truth; P2 strengthens but does not gate (`project6-origin/main:docs/program-context/03-forward-plan.md:L529-L531`). It must not be bundled with egress, corpus, exports, or legacy reveal (`project6-origin/main:docs/program-context/03-forward-plan.md:L611-L612`).
- Effort / risk: large/high; production-readiness false positives are called out as the worst failure class (`project6-origin/main:docs/program-context/03-forward-plan.md:L613-L616`).
- Recommended priority: P1 owner-gated. If the owner wants production soon, this becomes the highest-value decision lane; otherwise it should remain parked.

### Delivery, export, signed-reference, and provider delivery

- What it is: turn Layer 3/NRC/SEC package outputs into externally usable delivery artifacts and references.
- Current state: same-origin delivery/readiness UI/API exists in bounded form, but support matrix classifies real provider delivery and signed-reference export as unsupported (`project6-origin/main:config/support_matrix.yaml:L132-L160`). Deployment docs show signed-reference generation requires `LAYER3_SIGNED_REFERENCE_SECRET`; without it the route returns a 409 missing-secret error (`project6-origin/main:docs/layer3-production-activation.md:L311-L326`).
- Value: inference from operator utility: after review/package creation, delivery/export is the next practical usefulness boundary because it lets outputs leave the workbench in governed form.
- Prereqs / gate holder: owner/product security decision for signed references, provider identity, private URL model, and auditability; deployment must supply secrets/TLS if nonlocal (`project6-origin/main:docs/layer3-production-activation.md:L492-L501`, `L311-L326`).
- Dependency edges: forward-plan horizon places delivery/export surfaces before multi-filing gate enforcement, nonlocal auth hardening, admission, and default-on consideration (`project6-origin/main:docs/program-context/03-forward-plan.md:L646-L653`).
- Effort / risk: medium/large; security, identity, and artifact lifetime semantics matter.
- Recommended priority: P1 for functionality/utility, but only after a concrete delivery mode is chosen. Do not mix with P5 admission.

### Model/agent egress and qualitative execution

- What it is: allow model-backed or agent-generated analysis products and qualitative/hybrid/RAG/vector execution.
- Current state: model/agent egress is unsupported in the support matrix (`project6-origin/main:config/support_matrix.yaml:L137-L139`), source flag is deny-all by default (`project6-origin/main:backend/app/core/config.py:L180-L192`), and the runtime explicitly has no provider/model call and raises `NotImplementedError` (`project6-origin/main:backend/app/services/layer3_agent_product_runtime.py:L173-L191`). The NRC/Layer 3 handoff keeps qualitative/hybrid/RAG/vector execution and LLM planning out (`project6-origin/main:docs/nrc_adams/nrc_aps_status_handoff.md:L254-L263`).
- Value: potentially high for product intelligence, but inference: it is not the next safe utility step because the security/policy/adapter contract is not implemented.
- Prereqs / gate holder: owner/security policy lane, egress posture change, adapter implementation, provenance/review/draft-only semantics (`project6-origin/main:backend/app/services/layer3_agent_product_runtime.py:L173-L181`).
- Dependency edges: separate architecture/security program, not an A8 follow-on (`project6-origin/main:docs/program-context/03-forward-plan.md:L646-L653`).
- Effort / risk: large/high.
- Recommended priority: P2/P3 until explicit owner demand for model-generated products exists.

### NRC APS review/workbench product surface

- What it is: operator-facing review, document-trace, workbench-compare, and Candidate B inspection.
- Current state: shipped baseline is explicit and browser-covered (`project6-origin/main:frontend_UI_plans/README.md:L88-L110`); core clean-deploy review routes need no extra env vars for already-ingested runs (`project6-origin/main:docs/layer3-production-activation.md:L503-L513`).
- Value: inference from current support status: this is one of the most immediately usable product surfaces because it is operator-facing today, not blocked on SEC production admission.
- Prereqs / gate holder: concrete operator/product requirement for any expansion; docs say future browser work should be explicit expansion/refinement and only reopen wider Candidate B runtime admission if the shipped bundle-scoped model proves insufficient (`project6-origin/main:frontend_UI_plans/README.md:L111-L121`).
- Dependency edges: independent from SEC P5/A8; fixture-staging depends on operator runtime state for workbench/Candidate-B routes (`project6-origin/main:docs/layer3-production-activation.md:L515-L521`).
- Effort / risk: small-medium for targeted UI/browser refinement; medium if runtime admission or persistence/schema scope reopens.
- Recommended priority: P0/P1 when backed by a concrete operator workflow gap; otherwise keep as P2 and avoid speculative widening.

### CI / release-gate hardening

- What it is: decide whether all meaningful CI families should gate release readiness.
- Current state: latest inspected main run is green, and the workflow includes backend coverage, OCR, Postgres migrations, Playwright, and release-gate jobs (`project6-origin/main:.github/workflows/playwright.yml:L352-L692`). Program context identifies a release-gate dependency gap because `root-tests`, `nrc-aps-ocr`, and Playwright `test` are not release-gate blockers (`project6-origin/main:docs/program-context/03-forward-plan.md:L481-L494`).
- Value: inference: high repo-utility because it protects every future functional lane from accidental non-blocking regressions.
- Prereqs / gate holder: owner decision, because changing release-gate dependencies changes merge semantics (`project6-origin/main:docs/program-context/03-forward-plan.md:L488-L494`).
- Dependency edges: supports all future implementation work; independent of P2/P4/P5.
- Effort / risk: small-medium code/config, medium process risk.
- Recommended priority: P0 for owner decision; P1 for implementation after decision.

### Worktree, branch, held-dir, and owner-personal queue

- What it is: operational cleanup after the repo-ops campaign.
- Current state: campaign record says actionable frontier was quiescent except storage, zip determinism, and governance durability; other candidate work was owner-gated or cosmetic (`project6-origin/main:docs/campaign-records/2026-07-06-repo-ops-campaign.md:L22-L40`). Post-campaign state reduced registered repo-local worktrees to zero and left 12 held dirs plus owner-only items (`project6-origin/main:docs/campaign-records/2026-07-06-repo-ops-campaign.md:L257-L308`). `/tmp/audit-wt/p6main` remains a locked external placement violation needing owner decision (`project6-origin/main:docs/program-context/03-forward-plan.md:L228-L232`).
- Value (inference): mostly operational hygiene, not product functionality.
- Prereqs / gate holder: owner authorization for held dirs, external locked worktree, remote branch deletion, or identity-bearing Onlook upstream contribution (`project6-origin/main:docs/campaign-records/2026-07-06-repo-ops-campaign.md:L287-L297`).
- Dependency edges: independent from functional pursuits except reducing collision/disk risk.
- Effort / risk: small-medium, but deletion/removal class requires owner authorization.
- Recommended priority: P3 unless disk/collision risk recurs.

### P7 proof-import schema and support-matrix cadence

- What it is: low-risk record-truth tooling: sanitized proof-import schema plus periodic support-matrix posture audit.
- Current state: forward plan names P7a as a small Tier-1 hash/count/policy-only proof schema and P7c as a small support-matrix audit cadence (`project6-origin/main:docs/program-context/03-forward-plan.md:L636-L644`).
- Value: inference: moderate-to-high leverage because it reduces future audit cost and prevents docs from implying unsupported production posture while functional lanes continue.
- Prereqs / gate holder: agent-executable if kept Tier-1, no runtime/persistence expansion.
- Dependency edges: supports P5, A8, delivery/export, and future corpus records by making evidence intake safer and less bespoke.
- Effort / risk: small/low.
- Recommended priority: P1, especially as a parallelizable maintenance lane after immediate owner-decision items are clarified.

### Dependency graph

```text
Current local/offline supported profile
  -> NRC APS review UI / document trace / workbench compare / Candidate B Trace
  -> Layer 3 bounded workbench/package/handoff/readiness surfaces
  -> SEC XBRL offline/corpus/replay proofs

P2 corpus authority (executed for retained scope)
  -> strengthens P5 confidence
  -> future live acquisition only with owner grant

A7/A8 fact authority + controlled value reveal proof (closed/default-off)
  -> owner-local value utility
  -/> P5 admission evidence, because P5 requires value_reveal_performed=false
  -/> default-on, because default-on is a later separate owner decision

P4 legacy reveal label
  -> audit clarity only
  -> independent of P5 / delivery / corpus

Delivery/export/signed-reference/provider program
  -> practical output utility
  -> multi-filing gate enforcement
  -> nonlocal auth hardening
  -> P5 production admission
  -> default-on consideration, owner-only and separately authorized

Model/agent egress, HA, keyed connectors, provider delivery, signed-reference export
  -> separate architecture/security programs
  -> not A8 follow-on slices

CI release-gate dependency decision
  -> cross-cuts every future lane
  -> owner decision before implementation
```

#### Investigator's top-5 recommendation

1. P0/P1: decide and implement the release-gate dependency policy for `root-tests`, `nrc-aps-ocr`, and Playwright `test`. This is the smallest high-leverage repo-utility decision because it changes future regression protection (`project6-origin/main:docs/program-context/03-forward-plan.md:L481-L494`).
2. P0/P1: advance NRC APS only from a concrete operator workflow gap, because it is already shipped/browser-covered and immediately user-facing; avoid speculative Candidate B/runtime widening without a product requirement (`project6-origin/main:frontend_UI_plans/README.md:L88-L121`).
3. P1: choose a delivery/export/signed-reference/provider-delivery architecture if external consumption is the next product goal; this is a real utility unlock, but support matrix currently marks provider/signed-reference tracks unsupported and deployment docs require explicit secret/TLS posture (`project6-origin/main:config/support_matrix.yaml:L132-L160`; `project6-origin/main:docs/layer3-production-activation.md:L311-L326`, `L492-L501`).
4. P1 owner-gated: run P5 only when the owner actually wants nonlocal/production admission and can supply the final-admission packet. The code is not the blocker; the human/operator packet and deployment evidence are (`project6-origin/main:docs/program-context/03-forward-plan.md:L594-L616`).
5. P1: do P7a/P7c as a cheap audit-safety lane after the owner-decision queue is clear. It does not itself add product features, but it lowers the cost and risk of every future proof/admission/support-matrix claim (`project6-origin/main:docs/program-context/03-forward-plan.md:L636-L644`).

Recommendation / inference: do not prioritize P2 retained-corpus replay (closed), P4 legacy label alone (small audit cleanup), P6/held-dir cleanup (operational), default-on (explicitly not authorized), or model/agent egress (not implemented and unsupported without a security/product policy lane) as next functional work.

---

## §2. Verification/conceptualization (three-reviewer verification pass, 2026-07-07)

Verdicts: anchors SOUND; completeness SOUND_WITH_CORRECTIONS; ranking SOUND_WITH_CORRECTIONS.

### 2.1 Anchor verification (SOUND)
All load-bearing §1 anchors independently re-verified against project6-origin/main: support-
matrix profile/pins/unsupported statuses; release-gate `needs:` block (the five deps, excluding
root-tests/nrc-aps-ocr/Playwright test — confirmed straight from playwright.yml L628-633);
OCR/coverage(-90 floor)/PG jobs; the five review routes + health/ready; the eight default-off
flags in config.py L130-195; the fail-closed delivery/agent-runtime markers; A8 523/497
figures; corpus 46/27 + 6/6 replays; P5 6-of-7 + evaluator 7-criteria fail-closed code. Two
non-material impressions (job naming; the CI-run-green claim is a point-in-time GitHub
observation, not git-anchored — the ranking never rested on it).

### 2.2 Completeness corrections (accepted)
- MISSED PURSUIT (material): public-connector/analytics vertical breadth — the one
  operator-facing, agent-executable, non-owner-gated functional frontier (supported statuses
  support_matrix L22-50; full sciencebase_connector/ package + senate_lda connector live).
  §1's top-5 skewed toward owner-gated lanes by omitting it.
- MISSED ITEM: F5's second half — an ACTIVE GitHub workflow registration "SEC XBRL Tier-2
  review gate" whose file `.github/workflows/sec-xbrl-tier2-gate.yml` is ABSENT on main
  (verified: ls-tree shows only playwright.yml). Cheap, near-agent-executable hygiene fix.
- MISSED LANE CLASS: standing maintenance (I12 archive cadence, P7c support-matrix audit
  cadence, coverage-floor upkeep, corpus-regrade cadence, storage watch) — recurring, not
  one-shot.
- 17B delta under-stated: tracked main DOES anchor the substance (MASTER_CONTEXT L346-356:
  erasure premise superseded; system already built for retention). Retention posture REMOVED
  the erasure blocker; residual = the structural reveal/admission separation (I10) +
  single-GET enforcement. (Corrects §1's carried-forward hedge at dossier L94.)
- Minor: F4 coverage Option B (optional, only if the gate slows) and the v2→v3 adjudication
  schema item (batchable with P7a) belong on the map.

### 2.3 Ranking/dependency corrections (accepted)
- DEPENDENCY ERROR fixed: P5 is decoupled from performing a reveal (criterion 6:
  value_reveal_performed must be False in admission evidence) but COUPLED to a prior
  value-reveal-AUTHORITY decision (criterion 4: value_reveal_authority_receipt_valid requires
  eligibility + non-empty receipt id — production_admission.py L176-184). Edge redrawn:
  reveal-AUTHORITY --required--> P5; reveal-ACT --forbidden-during--> P5.
- Horizon arrows are "sequenced, not scheduled" (forward-plan L646) — suggested owner ordering,
  NOT dependencies. Delivery/export ∥ P5 (and delivery_export_enabled must be FALSE during
  admission runs — a negative constraint, not a feed).
- HUB INSIGHT: one "nonlocal deployment hardening" program (TLS + secret store + auth boundary
  + provider identity/private-URL model) is the shared upstream unlock for signed-reference
  export + real provider delivery + part of P5's nonlocal-deployment evidence (+ partial
  keyed-connectors). Only HA and model-egress are orthogonal.
- P7a/P7c demoted P1→P2 under the strict functionality criterion (maintenance multiplier, not
  functional unlock) — background lane, not headline.

---

## §3. Synthesized ranking + recommendations (orchestrator, post-§1+§2)

WHAT THE PROJECT IS BUILDING TOWARD (evidence-grounded): a locally-proven, fail-closed
analysis/review platform (NRC APS review + Layer-3 workbench + SEC-XBRL offline value
authority) whose growth axes are (a) more public data/analysis capability locally, and
(b) a governed path outward — delivery/export of outputs, then nonlocal production admission,
with default-on posture as a distinct, never-implied final owner decision.

### Ranked frontier (functionality/utility-first)

TIER 1 — decisions that unlock or protect everything (owner, cheap):
1. F5 release-gate dependency policy (root-tests / nrc-aps-ocr / Playwright test as blockers?)
   — one decision; protects every future lane from non-blocking regressions. Plus the
   agent-executable orphaned-workflow-registration cleanup (file absent on main).
2. THE DIRECTION CHOICE: local-depth vs outward. Everything in Tier 2 forks on it. If outward:
   fund the nonlocal-deployment-hardening HUB first (unlocks 3 tracks + P5 evidence). If
   local-depth: fund connector/analytics breadth + NRC APS refinement.

TIER 2 — functional build lanes:
3. Public-connector/analytics vertical breadth (agent-executable; needs only a named operator
   data/analysis target) — highest utility-per-gate-cost on the map.
4. NRC APS / workbench refinement from CONCRETE operator workflow gaps (shipped baseline is
   browser-covered; speculative widening explicitly discouraged by its own docs).
5. Nonlocal deployment hardening HUB → then signed-reference export and/or provider delivery
   (pick one concrete delivery mode first); P5 final-admission packet when the owner wants
   production (sole blocker is the human packet + nonlocal evidence; criterion-4
   reveal-authority receipt must exist/valid).

TIER 3 — background/maintenance (agent-executable, batch):
6. Standing-maintenance lane: I12 cadence, P7c support-matrix audit cadence, coverage-floor
   upkeep, corpus-regrade cadence, storage watch. Plus P7a proof-import schema + v2→v3
   adjudication schema + P4 legacy-reveal label (batch), F4 only if the gate slows.

PARKED (with reasons): P2 corpus (closed at 46/27 until a new evidentiary need — D7 forbids
speculative egress); model/agent egress (unsupported; needs a security/policy program + real
demand); HA (orthogonal infra program); default-on (explicitly not authorized by anything);
owner-personal queue (onlook upstream, mass branch deletion, /tmp unlock, held dirs).

### Single highest-leverage next concrete pass
The F5 decision + its two mechanical fixes (gate-deps edit if approved; orphaned-registration
cleanup regardless): smallest input (one owner call), broadest protection (merge semantics for
every future lane), and it clears the last named CI-truth wart before any Tier-2 build starts.

### CORRECTION (2026-07-07) — F5 executed
F5 is no longer an open owner decision. Executed via PR #2455, merged 444d2773
(current main tip at time of writing): release-gate required needs expanded 5 -> 8
(adds root-tests, nrc-aps-ocr, test; exact-set needs assertion added to the guard
test); the only net-new BLOCKING family is nrc-aps-ocr — live branch protection
already required test and root-tests independently, so their addition is
coverage-coherence, not new enforcement. Orphan workflow registration 286330393
("SEC XBRL Tier-2 review gate") disabled, not deleted. Tier-1 item 1 above and this
"Single highest-leverage next concrete pass" block are superseded. Higher-authority
tracked record: docs/program-context/03-forward-plan.md (M-RELEASE-GATE-F5 block),
per this dossier's authority order (line 8). §2's "MISSED ITEM: F5's second half"
(line 239) is resolved by the same PR; noted here rather than edited in place.

---

## §4. Local-depth fork anatomy (three-reviewer dissection, 2026-07-07; anchors verified vs main 444d2773)

### 4.1 What exists (the machinery the fork builds on)
- CONNECTOR FRAMEWORK: shared package backend/app/services/sciencebase_connector/ (contracts/
  executor/planner/reconciliation/serialization/reporting, ~350 LOC: 23 target statuses, 20
  error classes, 9 phases, per-run semaphore + per-host locks, atomic target transitions) +
  lifecycle helpers hosted in connectors_sciencebase.py (3,169 LOC: submit/lease/checkpoint/
  cancel/resume/finalize + the heavy download->ingest->profile->recommend pipeline + the
  observability projection serialize_connector_run). THREE connectors prove the pattern:
  ScienceBase (heavy, file-downloading), Senate LDA (975 LOC metadata-only template: bespoke
  client + token-bucket rate limiter ~2rps + backoff honoring Retry-After + terminal-or-
  retryable per-target isolation; ZERO new tables — aliases its domain onto the shared
  ConnectorRun* columns), NRC ADAMS (the counter-example: needed bespoke tables, migrations
  0007/0008/0011, and a full nrc_aps_* sub-subsystem). Egress safety is IN-CODE per connector:
  https-only + host allowlist + SSRF private-IP rejection; base URLs in config.py:210-214.
  Public connectors have NO bespoke UI — observability = GET /connectors/runs/{id} projections
  + on-disk reports (12 files per run via reporting.report_refs). Golden-path proof convention
  = live pilot validator via project6.ps1 (first_import/recurring_sync/budget_cap/cancel_resume
  scenarios). Framework is deliberately serial: max_concurrent_runs=1, per_host_fetch_limit=2.
- ANALYTICS VERTICAL: analysis.py IS the framework (support-matrix evidence anchor :44-100) —
  ANALYSIS_METHOD_REGISTRY is an IN-CODE dict (no HTTP catalog route exists; §0-era "catalog
  GET" prior CORRECTED); methods = dataclass spec + _run_* fn + dispatch branch, persisting to
  existing AnalysisRun/AnalysisArtifact/AssumptionCheck/CaveatNote tables (descriptive_summary,
  113 lines, is the template). Sibling deterministic surfaces: NRC APS insight rules
  (APS_RULE_SPECS; sha256-canonical-JSON checksummed artifacts — rules are append-only with
  fixed versions) and market-insight heuristic categories (trend/correlation/emerging_risk;
  explicitly 'heuristic', never a live LLM). Heavy deps: statsmodels/ruptures/matplotlib.
- CORRECTED PRIOR: "member-state frame" (memory descriptor from the 3C era) has ZERO hits in
  tracked backend code — treat as never-landed concept, not an existing surface.

### 4.2 The hard boundary inside the analytics half
Numeric/payload methods are INFEASIBLE today by construction, not by omission: the insight
layer's rule_evaluation_view exposes ONLY aggregate counts (total facts/caveats/constraints/
unresolved, per-packet) — fact VALUES are never projected into the context-packet->dossier
layer (contract.py:209-261). Unlocking value-level analytics = new linkage = new schema +
migration + dossier contract v2 + gate/contract tests = Tier-2 program (the single gate that
converts the whole numeric-analysis class from infeasible to feasible).

### 4.3 What adding ONE unit requires (derived checklists)
- NEW ANONYMOUS METADATA CONNECTOR (the cheapest connector unit; Senate template): 1 service
  module (submit_/execute_ pair, ~300-600 LOC incl. rate-limiter/backoff/error-classification)
  + 1 config base-URL field + dispatch-map entry + typed request schema + POST route + support-
  matrix entry (exact-asserted: support_matrix.yaml + support_matrix_constants.py + the
  mirrored test dict + docs/support-matrix-local-expert.md + README front door, with
  PR-1..PR-5 evidence markers) + ~7-12 tests in the PR-1..PR-5 lane pattern (correctness, L17
  negatives, lease/conflict/cancel/resume, source fidelity, operator journey) — all inside
  existing backend shards, no new CI job (no live-network CI per D7). Tier-1 iff zero new
  tables. THE DOMINANT COST IS NOT CODE: live egress to a NEW host class requires a NAMED
  owner grant (host + request budget, D27) executed as a written arming record + per-request
  ledger (D28) BEFORE the first live request. Building/testing offline against fixtures needs
  no grant.
- NEW ANALYSIS METHOD (the cheapest unit overall): registry entry + runner + dispatch branch +
  happy-path/caveat tests + eval-tool wiring + changelog/README/matrix-anchor touch-ups;
  Tier-1, zero migration, zero egress. Insight RULES and market categories similar but with
  paired _contract+_gate tests and checksum append-only discipline.
- ESCALATION TRIGGERS to Tier-2/programs: any new table/migration; raw-content persistence
  (adds I4/I5 off-repo storage + default-off arming flag obligations); any KEYED source
  (collides with keyed_connectors=unsupported + the anonymous-only overlay boundary_note —
  a policy program, not a config flip); any model-backed method (model egress unsupported).

### 4.4 Candidate menu (from the dissection; owner picks targets)
Tier-1 immediate: 5th analysis method (seasonality/outlier/trend-slope/missingness classes);
6th insight rule over dossier counts; 4th market-insight category; a method-catalog GET route
IF an operator needs UI method discovery (currently doesn't exist; build-on-demand only).
Tier-1 + one owner egress grant: a third anonymous .gov/open-data metadata connector; or
widening ScienceBase external_fetch_policy to specific new allowlisted hosts (seam exists).
Tier-2 programs (owner-scoped): the fact-value linkage unlock (4.2); raw-persisting connector;
keyed-connector policy program.
