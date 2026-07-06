# SEC XBRL Corpus Run Gate Spec

Status: canonical pre-registered run-level gate registry for future SEC XBRL
corpus runs.

This document governs future corpus runs. It does not re-grade or expand the
completed 2026-07-05 owner-authorized corpus-go run. The historical
[`corpus-run-plan.md`](corpus-run-plan.md) remains the superseded record for
that completed run, and `docs/program-context/04-evidence-registry.md` remains
the current evidence authority for the #2433/#2434 corpus-go record.

This spec authorizes no network egress, no runtime/default/config change, no
backend/tool/test change, no value reveal, no production-readiness claim, and no
raw artifact publication. It defines what a future run must prove before anyone
may say that run's gates passed.

## Authority Anchors

- Historical corpus plan and supersession boundary:
  [`corpus-run-plan.md`](corpus-run-plan.md).
- Program-context forward sequencing:
  [`../../docs/program-context/03-forward-plan.md`](../../docs/program-context/03-forward-plan.md).
- Program-context evidence registry and #2427 through #2434 PR/SHA anchors:
  [`../../docs/program-context/04-evidence-registry.md`](../../docs/program-context/04-evidence-registry.md).
- Current live-source rate and request-budget policy:
  `backend/app/core/config.py` and
  `backend/app/services/layer3_sec_edgar_live_source_artifact.py`
  (`RATE_POLICY_ID`,
  `sec_edgar_text_table_live_source_artifact_default_1rps_max_10rps_v1`,
  default one request per second, admitted 1-10 requests per second, default ten
  live requests per process, 25 MB configured artifact limit, 200 MB hard source
  artifact ceiling).
- Current storage preflight tool:
  `diagnostics/assessment/sec-xbrl-storage-preflight.py`
  (`diagnostics.sec_xbrl_storage_preflight.v1`, validate-only, no report write).
- Current corpus disposition and reason-code emission surfaces:
  `backend/app/services/layer3_sec_xbrl_sidecar.py` and
  `backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py`.
  The code locations are the reason-code registry authority; this spec must not
  freeze a complete enumerated reason-code list. Current examples include the
  #2427-era hardening codes for unprovisioned taxonomy years, pre-inline-era
  filings, and standalone XML/XBRL source-family blocks.
- Current redaction guard surfaces:
  `diagnostics/assessment/sec_xbrl_diagnostic_framework.py`,
  `backend/app/services/layer3_sec_xbrl_public_authority_guard.py`,
  `backend/app/services/layer3_sec_xbrl_report_leak_guard.py`, and the corpus
  runner's offline-product report scan in
  `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`.
- Current H7-style multi-filing evidence/admission containment:
  `backend/app/services/layer3_sec_xbrl_multi_filing_evidence_authority_gate.py`
  and the #2427 hardening record in the program-context evidence registry.

## Evidence Bundle Contract

Every future run must export one hash-anchored evidence bundle before any
gate-passed announcement. The bundle may point at operator-local durable
artifacts by hash and by accepted public root marker only. The intentional
public root marker is `C:/p6store`; all other local paths must be redacted or
represented by hashes.

At minimum, the bundle records:

- `spec_id`: `sec_xbrl_corpus_run_gate_spec.v1`.
- `spec_file`: `next_milestone_plans/Layer3_planning_docs/corpus-run-gate-spec.md`.
- `run_namespace` and `client_request_id` namespace. New acquisition runs use a
  fresh namespace. Exact replay or resume bundles may reuse request ids only
  when the bundle carries a fresh regrade/export namespace plus a request-id
  ledger proving that each reused id binds to the same basis hash.
- `repo_main_sha` and PR/SHA anchors used for code authority.
- `gate_results`: one object per gate below, including `id`, `status_tag`,
  `timing`, `artifact_ref`, `artifact_sha256`, `grader`, `pass`, and
  `blocked_reasons`.
- Amendment records for any changed rate, size cap, scope, form set, or source
  family.

No gate passes from prose alone. A gate either has a machine-readable artifact
where this spec requires one, or it fails closed.

## Status Tags

- `ACTIVE-NOW`: binds zero-egress replay, record-truth, and future planning or
  report-only work immediately.
- `LIVE-RUN-ONLY`: specified now but dormant until an owner-authorized live-egress
  corpus run is scheduled.

## Gate Registry

### G1 - Disposition Taxonomy

- Status tag: `ACTIVE-NOW`.
- Timing: pre-run schema declaration, then post-run evidence verification.
- Statement: every input and selected filing slot must carry one named final
  disposition. `unresolved` means no authoritative ticker/issuer/filing basis was
  obtained. `named block` means the basis was obtained or attempted and a
  specific admitted guard, source-family limit, taxonomy limit, storage limit,
  rate limit, or policy condition stopped support.
- Required artifact: machine-readable per-input and per-filing disposition
  receipt table, plus the code-authority refs for reason-code emitters.
- Pass condition: every row has exactly one final disposition from the run schema
  and, where not `supported`, at least one non-empty reason code emitted from the
  current code registry authority. The artifact cites the registry locations
  rather than copying a complete reason-code list.
- Grader: independent regrader for the exported bundle; operator may attest
  operator-local fields, but may not self-grade final pass.
- Repo anchors: `backend/app/services/layer3_sec_xbrl_sidecar.py`,
  `backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py`,
  #2427 in `docs/program-context/04-evidence-registry.md`, and
  `corpus-run-plan.md` "Named Disposition Taxonomy".

### G2 - Zero Unnamed Or Silent Failures

- Status tag: `ACTIVE-NOW`.
- Timing: post-run.
- Statement: no input, chunk, receipt, filing slot, or replay record may end in a
  null, missing, silent, or only-exceptional state.
- Required artifact: per-record receipt fields for input id, selected filing slot
  id, disposition, reason codes, receipt hash, and blocked/supported/degraded
  state.
- Pass condition: every planned input and every attempted slot appears in the
  receipt table; no row lacks disposition, reason, or receipt hash; exception
  text without a mapped reason code is a failure.
- Grader: independent regrader over exported receipts and receipt hashes.
- Repo anchors: `corpus-run-plan.md` historical gates 1-2 and allowed receipt
  fields; #2433/#2434 evidence-registry correction that the completed run's
  `zero_unnamed_failures` gate was one of the four completion gates.

### G3 - Volume Thresholds

- Status tag: `LIVE-RUN-ONLY`.
- Timing: pre-run threshold registration and post-run grading.
- Statement: a live corpus run must pre-register supported-filing and
  supported-issuer minimums, plus the named owner shortfall adjudicator. This
  gate is dormant for pure planning or record-only lanes that make no corpus-run
  gate-pass claim; it applies to any zero-egress regrade or report-only bundle
  that evaluates a previously acquired live corpus run.
- Required artifact: machine-readable aggregate counts for supported filings,
  supported issuers, input count, attempted filing count, named block count, and
  shortfall adjudicator identity/decision reference when thresholds are not met.
- Pass condition: supported filings and supported issuers meet the registered
  minimums. A shortfall can be recorded only by the named owner adjudicator and
  is not self-adjudicated by the run operator or implementation agent.
- Grader: independent regrader verifies counts; owner adjudicates any named
  shortfall separately.
- Repo anchors: `corpus-run-plan.md` current 30 filing / 15 issuer historical
  minimums and #2433/#2434 evidence-registry count records.

### G4 - Storage Preflight

- Status tag: `ACTIVE-NOW`.
- Timing: pre-run, with mid-run rechecks for runs exceeding about 30 minutes.
- Statement: the run must prove storage root availability and free-space adequacy
  before writing, and must recheck during longer runs. Total free space observed
  today is not enough; the threshold must be tied to projected writes for this
  run.
- Required artifact: JSON stdout from
  `python diagnostics/assessment/sec-xbrl-storage-preflight.py --storage-root <operator-root> --min-free-bytes <threshold>`
  captured into the evidence bundle, plus a projection object containing
  `projected_write_bytes`, `safety_factor`, `min_free_bytes`, and recheck
  timestamps for long runs.
- Pass condition: `storage_root_exists=true`, `validate_only=true`,
  `mutation_performed=false`, `pruning_performed=false`, `seed_performed=false`,
  `report_artifact_written=false`, and `free_space_bytes >= min_free_bytes`.
  `min_free_bytes` must be at least `max(10 GB, projected_write_bytes *
  safety_factor)`, with safety factor at least 2.0 unless a pre-registered owner
  amendment raises it. The projection object must attest that the storage root
  is outside the repo and outside OneDrive. For runs over about 30 minutes, each
  chunk boundary or 30-minute interval recheck must also pass.
- Grader: independent regrader checks the preflight JSON, projection math, and
  recheck cadence; operator attests only storage-root access that is not fully
  visible in the exported bundle.
- Repo anchors: `diagnostics/assessment/sec-xbrl-storage-preflight.py`,
  `corpus-run-plan.md` "Storage Budget", and the #2434 storage/integrity
  supplement record. This gate exists because a documented 0-byte-disk incident
  killed a worker lane mid-arc.

### G5 - Rate Compliance

- Status tag: `LIVE-RUN-ONLY`.
- Timing: pre-run budget registration, mid-run logging, post-run grading.
- Statement: live egress must prove request pacing and total request budget
  compliance from per-request data. An asserted wall-clock cadence is not
  compliance.
- Required artifact: machine-readable per-request timestamp log with host,
  request class, run namespace, request id hash, configured maximum rate, total
  request budget, observed request count, deferral/block records, and
  `RATE_POLICY_ID`.
- Pass condition: every request stays within the pre-registered max rate and
  total request budget for each host class; no missing timestamp intervals; no
  unamended rate or request-budget change.
- Grader: independent regrader over timestamp log and policy fields.
- Repo anchors: `backend/app/core/config.py`,
  `backend/app/services/layer3_sec_edgar_live_source_artifact.py`, and
  `corpus-run-plan.md` rate decision/checklist.

### G6 - Redaction Scan

- Status tag: `ACTIVE-NOW`.
- Timing: post-run before any committed/report publication.
- Statement: committed text, public report surfaces, receipts, and regrade
  artifacts must be scanned for forbidden classes, not only checked for a single
  substring.
- Required artifact: machine-readable redaction scan report produced by a named
  scan wrapper or grader script that uses the repo guard surfaces:
  `diagnostics/assessment/sec_xbrl_diagnostic_framework.py`,
  `backend/app/services/layer3_sec_xbrl_public_authority_guard.py`, and
  `backend/app/services/layer3_sec_xbrl_report_leak_guard.py`. The report must
  include scanned surface list, guard version/hash, forbidden-class booleans,
  allowlist entries, and final `passed`.
- Named command: for redacted product-runner reports, the current anchored
  command is
  `python diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py --redacted-product-runner-report <report> --storage-dir <operator-root> --matrix-plan <matrix-plan> --output <scan-report>`.
  That command proves only the runner's offline redacted-product report import
  scan. It is not, by itself, a complete G6 artifact. A G6 pass also requires a
  supplemental scan for committed docs, receipts, and regrade reports; that scan
  must name its script/module and include its source hash in the artifact.
- Forbidden classes: operator identity/contact, local paths other than the
  intentional `C:/p6store` root marker, User-Agent contents, raw fact values,
  raw CIK/accession/SEC URL authority, source artifact bytes, raw SEC payloads,
  raw CompanyFacts payloads, and raw Arelle output.
- Pass condition: zero forbidden-class hits outside the explicit allowlist. The
  only path allowlist in this spec is the literal canonical root marker
  `C:/p6store`; child paths must be durable-root-relative or hashed.
- Grader: independent regrader reruns or verifies the scan artifact before
  publication.
- Repo anchors: redaction guard modules listed above,
  `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py` offline report
  redaction scan, `corpus-run-plan.md` forbidden fields, and the program-context
  maintenance redaction rule.

### G7 - Egress Arming Record

- Status tag: `LIVE-RUN-ONLY`.
- Timing: pre-run before the first request.
- Statement: live egress requires a durable arming record that names the hosts,
  request budget, and authorizing grant reference before network use begins.
  SEC EDGAR and taxonomy-host egress are distinct entries.
- Required artifact: pre-run arming record with run namespace, grant reference,
  host allowlist, SEC EDGAR request budget, taxonomy-host request budget,
  User-Agent presence marker, live-network flags, arming timestamp hash, and a
  redacted orderable timestamp or monotonic sequence marker.
- Pass condition: arming record exists before the first request timestamp; every
  request host appears in the arming record; taxonomy-package egress is not
  smuggled under the SEC EDGAR budget; the exported order marker proves the
  arming record predates the first request without exposing operator-local raw
  details.
- Grader: independent regrader over arming record and timestamp log; owner grant
  reference is operator-attested when the full grant cannot be public.
- Repo anchors: live-source config/service anchors and
  `diagnostics/assessment/sec-live-preflight.py` as the live preflight posture.

### G8 - Idempotency And Rerun Rules

- Status tag: `LIVE-RUN-ONLY`.
- Timing: pre-run namespace registration, mid-run receipt capture, post-run
  rerun/replay grading.
- Statement: every rerun must use a fresh `client_request_id` namespace unless
  it is intentionally replaying the exact same basis. Reusing ids for changed
  bases can return replay-blocked receipts and must not be treated as fresh
  evidence.
- Required artifact: namespace ledger with run namespace, chunk namespace,
  per-slot request-id hashes, basis hash for each id, replay/resume markers, and
  clipped/crashed chunk resume decision.
- Pass condition: no request id is reused for a changed basis; replayed ids bind
  to the same basis hash; clipped/crashed chunks have an explicit resume or
  abandon disposition.
- Grader: independent regrader compares namespace ledger, receipts, and
  aggregate dispositions.
- Repo anchors: `corpus-run-plan.md` client request id namespace and per-filing
  isolation sections.

### G9 - Independent Regrade

- Status tag: `ACTIVE-NOW`.
- Timing: post-run, after export and before "gates passed" claims.
- Statement: no run-level gates-passed announcement is valid until a second
  grader regrades the exported hash-anchored evidence bundle against this spec.
- Required artifact: independent regrade report with spec hash, evidence-bundle
  hash, gate-by-gate verdicts, unresolved questions, operator-attested fields,
  and final pass/fail.
- Pass condition: independent regrade says every applicable gate passed. Fields
  requiring operator-only access, including p6store-local state and arming
  details, are labeled `operator_attested` and regraded only from exported
  evidence. The report must not claim full independence for facts the grader
  could not independently observe.
- Grader: independent lane, workflow agent, or reviewer distinct from the run
  operator.
- Repo anchors: #2434 evidence-registry framing of operator-local durable root
  evidence and unanchored probe context.

### G10 - Deviation Protocol

- Status tag: `ACTIVE-NOW`.
- Timing: pre-run and before any deviating action.
- Statement: any deviation from a pre-registered knob must be amended before the
  deviating action. Retroactive reconciliation does not pass this gate.
- Required artifact: amendment ledger with affected knob, previous value, new
  value, reason, authorizing actor, timestamp, and downstream gates requiring
  regrade. Knobs include rate, request budget, size cap, storage threshold,
  ticker/input scope, form set, source family, taxonomy egress, and redaction
  allowlist.
- Pass condition: every observed deviation has a prior amendment entry; no
  unamended 10 rps versus 2 rps, 150 MB versus 25 MB, form-set, or scope
  deviation is present.
- Grader: independent regrader compares planned values, amendments, runtime
  artifacts, and final reports.
- Repo anchors: `corpus-run-plan.md` rate and storage decisions, live-source
  config/service constants, and #2433/#2434 supersession notes documenting why
  pre-registration is required.

## Claim Language

A future closeout may say "gates passed" only when:

1. every `ACTIVE-NOW` gate applies and passes;
2. every `LIVE-RUN-ONLY` gate either applies and passes for live egress or is
   explicitly marked dormant for a zero-egress/replay/record-only lane;
3. the independent regrade report is complete; and
4. the redaction scan is clean.

If any applicable gate artifact is missing, empty, operator-only without
exported evidence, or retroactively amended after the action it controls, the
correct claim is `gate_failed_closed`, not `passed_with_context`. A
`LIVE-RUN-ONLY` gate marked dormant for a zero-egress planning, replay, or
record-only lane is exempt from its live-egress artifact requirement only when
the bundle records the dormant reason and makes no claim that the dormant live
control passed.
