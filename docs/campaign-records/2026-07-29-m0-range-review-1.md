# M0 range review 1 — external Codex 019faa86 (C6-compliant), range 356eff2e..3ed5589a

Date: 2026-07-29. VERDICT: DO-NOT-FREEZE — defect classes 2/3/4 not mechanically resolved (arming-service
predecessor predicate weaker than execution order; wire accounting exceeds Requests-adapter mechanism;
parser lane lacks complete edit surface + exact fail-closed bounds). Class 1 conditionally resolved.
Source reply: 16,940 B, sha256 below. Transcribed verbatim (BOM stripped if present). Non-authorizing.

source-sha256: 1e8876ff457a36fa7446aa497f75f14e489072f435e65036fc7a642de711ca91

---

# External review: dual-live M0 correction range

## Verdict

**DO-NOT-FREEZE**

The range materially improves the plan and preserves its default-off and owner-gated posture, but three of the four named defect classes are still not mechanically resolved:

1. the ScienceBase arming service enforces a weaker NRC predecessor predicate than the execution order requires;
2. the promised raw-wire accounting and hard aggregate byte ceiling exceed the selected Requests-adapter mechanism;
3. the secret-free parser lane has neither a complete edit surface nor exact fail-closed resource controls against the current parser code.

These are authority/mechanism defects, not editorial polish. The first changes when a second owner grant can be consumed; the second changes the meaning and enforceability of the owner byte budget; the third changes whether privileged parser behavior is actually excluded. They require another correction round and full-range re-review.

## Scope and identity

- **REPO-CONFIRMED:** `project6-origin/main` resolves to `c1fcd840b421ceafb560266858a75808207f4540`.
- **REPO-CONFIRMED:** final reviewed HEAD is `3ed5589a1a88911684e4a9165e3757a4115bfd79`.
- **REPO-CONFIRMED:** the requested range contains exactly:
  - `78eb3146618cd425ad0070c19250031bec0e16c7`, parent `356eff2e03e68ff4d776df130e566eac265634e1`;
  - `3ed5589a1a88911684e4a9165e3757a4115bfd79`, parent `78eb3146618cd425ad0070c19250031bec0e16c7`.
- **REPO-CONFIRMED:** range size is exactly `489 insertions, 83 deletions`:
  - campaign record: `+103/-28`;
  - implementation plan: `+386/-55`.
- **REPO-CONFIRMED:** only the two authorized documents changed.
- **REPO-CONFIRMED:** `git diff --check 356eff2e..3ed5589a` is clean and the worktree is clean.
- **REPO-CONFIRMED:** final file SHA-256 values:
  - plan: `790147a79ffd86502d55be392f15425942ebf69d9c0f539822ab27e072e865a2`;
  - campaign: `e9b6441168798350cbb74c70be155fb201be9e05806c68a1a294f9cf7e59d018`.
- **UNVERIFIED:** runtime behavior and proposed tests. The review boundary prohibited Python, pytest, Alembic, Node, and npm execution.

## R1 — Four defect classes against actual code paths

### 1. Strict runtime state machine — conditionally resolved, not independently blocking

**REPO-CONFIRMED:** the corrected documents consistently specify:

`armed -> pending -> running -> completed|failed|cancelled`

with one `armed -> pending` CAS, lease acquisition as the only `pending -> running` transition, one strict finalizer, deterministic terminal-event uniqueness, and generic cancel/resume/finalize rejection. See:

- `docs/superpowers/plans/2026-07-29-dual-live-proof.md:79-83`;
- `docs/superpowers/plans/2026-07-29-dual-live-proof.md:818-830`;
- `docs/superpowers/plans/2026-07-29-dual-live-proof.md:973-1010`;
- `docs/campaign-records/2026-07-29-dual-live-proof.md:349-366`.

**REPO-CONFIRMED:** the existing connector executors do not yet have that property:

- `connectors_sciencebase.py:957-975` and `connectors_nrc_adams.py:2541-2555` set `running` without a `pending` status constraint;
- both executors call that lease helper before loading `request_config_json` and identifying the strict envelope (`connectors_sciencebase.py:2799-2833`; `connectors_nrc_adams.py:3531-3566`).

**Assessment:** the plan assigns both connector files and demands tests proving that no strict path enters `running` from another state. That is adequate as an implementation requirement only if the strict-envelope/status check occurs before the current lease mutation. Add that ordering explicitly; otherwise an implementation can satisfy the prose dispatch while retaining the unsafe current pre-dispatch lease call.

### 2. Network privilege window — not resolved

**REPO-CONFIRMED:** the target design correctly separates an acquisition-only child from a secret-free, network-denied downstream parser (`plan:13-20`, `123-134`, `2192-2210`; `campaign:401-410`, `480-500`).

**REPO-CONFIRMED:** the implementation surface is incomplete:

- Task 5 names only `connectors_nrc_adams.py`, API schemas, and tests (`plan:1523-1530`);
- Task 8 names capture/evaluator/gate files and `project6.ps1`, but not the parser modules (`plan:1930-1940`);
- current NRC import flow is `connectors_nrc_adams.py:32,77-88` -> `nrc_aps_artifact_ingestion.py:13` -> `nrc_aps_document_processing.py:23-27`;
- the current parser imports OCR, advanced table, and advanced OCR modules at module load;
- `ocr_enabled=false` does not close all OCR paths: the hybrid branch at `nrc_aps_document_processing.py:1282-1295` can call Tesseract based on availability without checking `ocr_enabled`;
- advanced table execution is selected by document type at `nrc_aps_document_processing.py:1781-1786`;
- Tesseract uses `subprocess.run` at `nrc_aps_ocr.py:80-86`;
- the hybrid OCR exception is converted to degradation at `nrc_aps_document_processing.py:1314-1315`, contradicting the campaign requirement that a prohibited path or breached bound fail the campaign;
- the current PDF page check allows `content_parse_max_pages * 30` (`nrc_aps_document_processing.py:1164-1169`), not the stated strict page bound.

**REPO-CONFIRMED:** the plan lists bound categories but gives no numeric values, immutable config fields, units, measurement points, or enforcement owner for pages, rendered pixels, text, tables, temp disk, memory, CPU/wall time, and output (`plan:1621-1629`; `campaign:487-491`).

**Conclusion:** “force baseline plus `ocr_enabled=false`” is not a mechanism that refuses every current OCR/Camelot/subprocess path. The plan must include the affected processing modules, define exact limits, make prohibited branches unreachable or explicitly fatal, and test those actual branches in a network-denied, secret-free process.

### 3. Authority accounting — not resolved

**REPO-CONFIRMED:** the documents now define a manifest-bound counter and reconcile it against the DB ledger. They also claim that a Requests HTTP adapter at the “lowest application-visible” boundary counts the raw status line, raw headers, and body bytes as received, and that the aggregate can never exceed `max_run_bytes` (`plan:1245-1342`; `campaign:610-638`).

**REPO-CONFIRMED:** the project permits `requests>=2.31` (`backend/requirements.txt:16`) and the current connectors use Requests.

**INFERENCE, corroborated by the installed Requests/urllib3 source:** the named adapter seam does not expose the original raw status-line/header octets. Requests receives an urllib3 response and constructs status and headers from parsed fields (`requests/adapters.py:349-356`); urllib3 obtains those after `http.client` has parsed the response and rebuilds an `HTTPHeaderDict` from `httplib_response.msg.items()` (`urllib3/connection.py:570-594`). Original casing, whitespace, line endings, and exact status/header octets are therefore not available to a counter mounted only at the Requests adapter seam.

**INFERENCE:** aborting at a streamed chunk boundary also cannot guarantee that network wire receipt “never exceeded” the remaining aggregate. Headers are already received before the adapter returns a response, and socket/TLS/urllib3 buffering may receive more bytes than the application yields before the next check. The design can enforce an application-delivered raw-body ceiling, or detect that an application-visible count crossed a ceiling, but those are not the stated exact raw-wire hard cap.

**Conclusion:** choose and bind one honest metric before freeze:

- either redefine the experimental owner budget as an exact canonical application-visible metric, with explicit status/header serialization and buffering non-claims; or
- move measurement/enforcement below Requests to a transport/proxy/OS boundary that actually observes the claimed bytes.

The evaluator, reservation arithmetic, grant schema, and acceptance language must use the same currency. A post-crossing abort cannot support “never exceeded.”

### 4. Grant isolation — not resolved

**REPO-CONFIRMED:** execution step 5 defines NRC acquisition success as all of:

- strict terminal `completed`, exactly one terminal event, no lease, and no later failure/cancellation;
- canonical ledger reservation/completion parity within ceiling;
- no `spent_unknown`;
- DB-ledger/transport-counter agreement;
- complete admitted PDF `200` within limits;
- raw SHA-256 on the canonical connector-target receipt.

See `plan:2495-2506`.

**REPO-CONFIRMED:** the arming service and its tests enforce only the narrower predecessor check:

- deterministic NRC run exists;
- strict terminal `completed`;
- exactly one valid terminal event;
- no unexpired lease;
- bind the run ID and `ledger_terminal_hash`.

See `plan:801-809` and `924-929`.

**INFERENCE:** because `POST /api/v1/connectors/egress-armings` is an exposed control surface, a direct service/API call can reach ScienceBase marker creation after the narrow terminal check without proving counter parity, absence of unknown sends, or the canonical PDF receipt. Wrapper ordering is procedural; it does not make the isolation mechanical. Binding a stored `ledger_terminal_hash` is not equivalent to rederiving and validating the full predicate.

**Required correction:** the ScienceBase arming service itself must rederive the complete NRC acquisition-success predicate, using authoritative DB events, sealed counter evidence, and the canonical target receipt, in the same call before marker creation. Add adversarial tests for every omitted clause and prove zero marker/DB/event mutation on each failure.

## R2 — Guarantee hunt

| Guarantee | Result | Evidence |
|---|---|---|
| Wall-clock scope and UTC exception | **Resolved** | Monotonic duration/rate/deadline rules and the explicit injected-UTC authority-window exception now agree (`campaign:624-630`; `plan:1269-1281`, `1303-1317`). |
| Admission-shape carveout versus Tasks 4/5 | **Not fully resolved** | The architecture still says the downstream process performs “all parsing” only after child stop (`plan:13-19`), while invariant 21 and Task 4 explicitly perform bounded CSV header/data-row parsing in the acquisition child (`plan:123-127`, `1394-1396`). Replace “all parsing” with “all substantive/document parsing except the enumerated bounded admission checks.” |
| Eight-component request fingerprint | **Partially resolved** | Reservation and send-side prose now enumerate the same eight conceptual components (`plan:1191-1194`, `1282-1290`). However, “arming/grant digest” is not an exact field definition, and key names, header canonicalization, duplicate handling, URL normalization, and the body-absence representation are not specified as one executable canonical payload. Require one shared canonical helper/schema and mutation tests for every component. |
| Execution step 8 versus connector finalization in steps 5/7 | **Resolved** | Step 8 now says both connectors were already finalized inside their executors and explicitly forbids a second finalize (`plan:2518-2525`). |
| `http.jsonl` counter-only routing versus evaluator strict parse | **Resolved in prose** | Wrapper routing reserves `http.jsonl` for counter records only and makes any other line indeterminate (`plan:2465-2470`); evaluator requires strict parse and exact one-to-one reconciliation (`plan:2119-2131`). Runtime remains **UNVERIFIED**. |

## R3 — Plan/campaign internal consistency

- **States:** mostly consistent, subject to the pre-lease strict-envelope ordering condition above.
- **Ordinals and ceilings:** consistent: ScienceBase `1/2/3`; NRC `1/2`; redirects/retries/fallbacks are separately reserved or denied.
- **Ledger/counter:** field-level reconciliation is consistent, but the selected counter cannot support the promised raw-wire semantics. Failure records also need an exact nullable/error schema so “one record per physical send” is deterministic when no HTTP status exists.
- **Processes:** the two-phase acquisition/downstream model is consistent. The phrase “at most one campaign process alive” is imprecise because a wrapper and one child coexist; say “at most one application/runtime child, plus the network-inert wrapper” if that is the intended single-writer boundary.
- **Parser stops:** inconsistent with current code because prohibited OCR/subprocess failures can degrade rather than fail, and the plan omits the modules that own those paths.
- **Budgets:** request counts and stage body caps are coherent; the aggregate raw-wire hard ceiling is not.
- **Campaign close:** `campaign:276-280`, `903-904` and `plan:2595-2596` say an unused grant is retired by campaign-close head advancement, but no execution/closeout step creates such a successor. The index model permits a successor only by adding a new complete campaign slice. Either define the actual close/head-advance operation and authority or remove the claim. Until then, NRC failure is the active predecessor fence; “retired by head advancement” is unsupported.

## R4 — Default-off, authority, egress, governance, and owner gates

- **REPO-CONFIRMED:** M0 candidate status grants no implementation/network authority (`plan:5-6`; `campaign:1-7`).
- **REPO-CONFIRMED:** live egress defaults false (`plan:485-488`).
- **REPO-CONFIRMED:** Tasks 1-9 are offline; Task 10 sends nothing; Task 11 is explicitly owner-gated and cannot start from the plan (`plan:47-65`).
- **REPO-CONFIRMED:** validation is validate-only, fails closed on empty state, and may not seed/generate evidence (`plan:59-60`, `2088-2105`, `2221-2247`).
- **REPO-CONFIRMED:** the campaign retains M0-M4 grouped governance, M5-M8 live/repeatability gates, and a separate M9 promotion decision (`campaign:881-892`).
- **UNVERIFIED:** literal gates named `G0` through `G4` do not appear in either reviewed document. If the handoff intended M0-M4, those gates are present. If `G0-G4` are distinct canonical gates, their mapping is absent and cannot be confirmed from this range.

The default-off/no-authority/no-egress/owner-decision posture is intact. The verdict does not grant implementation, egress, owner approval, PR, merge, or promotion authority.

## R5 — Fresh-eyes findings

1. **Blocking:** full NRC acquisition success is checked by the wrapper but not by the ScienceBase arming service.
2. **Blocking:** “raw wire bytes” and “never exceed” are stronger than a Requests-adapter counter can enforce.
3. **Blocking:** the strict parser contract omits the modules and exact bounds needed to make current OCR/table/subprocess behavior unreachable or fatal.
4. **Correction required:** “all parsing after stop” conflicts with the explicit acquisition-time CSV shape check.
5. **Correction required:** campaign-close head advancement is promised but not specified.
6. **Hardening condition:** make the fingerprint preimage one named canonical schema/helper rather than matching prose lists.
7. **Hardening condition:** distinguish the orchestration wrapper from the one permitted application/runtime child.

## Decision debate and consensus

**Freeze case:** the two commits repair substantial earlier ambiguity: they add a strict state machine, two-process privilege separation, counter/ledger reconciliation, NRC-first arming order, monotonic timing, counter-only log routing, and explicit finalization ownership. The governance posture remains conservative.

**Do-not-freeze case:** M0 is a design freeze for an executable authority-sensitive plan. A weaker service-side grant gate can spend the second grant outside the declared predicate; the selected transport boundary cannot measure/enforce the promised budget currency; and the parser lane cannot satisfy its own refusal/fail-closed contract through the named code surface. Freezing would convert unresolved architecture into implementation obligations and invite either silent guarantee weakening or out-of-plan changes.

**Consensus:** **DO-NOT-FREEZE.** The defects are core and coherent, not speculative edge polish.

## Minimum acceptance criteria for the next review

1. Put the entire NRC acquisition-success predicate inside ScienceBase arming creation before marker creation; rederive, do not trust a stored projection.
2. Choose an enforceable byte-accounting currency/layer and make grant, reservation, counter, evaluator, and non-claims identical.
3. Add the real parser modules to the task surface; define exact numeric limits/units; make OCR/Camelot/Paddle/subprocess paths refuse and fail closed; test the current hybrid and advanced-table branches.
4. Reconcile the admission-parse wording and define one executable eight-component fingerprint schema.
5. Specify or retract campaign-close head advancement.
6. Retain every current default-off, validate-only, no-authority, owner-gated, M0-M9, and production-non-claim boundary.
7. Re-run an independent full-range review; a delta-only review is insufficient.

No correction blob or implementation is authorized or supplied.
