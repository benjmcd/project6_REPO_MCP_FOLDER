# SEC/XBRL Layer 3 Operator Runbook (CLI + UI)

Status: operator-facing runbook for driving the SEC/XBRL Layer 3 operator-review lifecycle
end-to-end. Validate-only posture: `production_readiness_claimed` is `False` on every step.

## What this covers

The full operator-review lifecycle for a SEC filing:

```
open  →  status  →  decide  →  prepare-authority  →  reveal  →  reveal-status
(live fetch +     (review     (approve/      (mechanical)   (controlled    (hash-only
 Arelle + oracle   ready)      reject/...)                   disclosure)     replay)
 + open review)
```

Two interfaces drive it:

- **CLI** (`backend/app/cli/sec_xbrl_operator_cli.py`): a thin HTTP client over the existing
  Layer 3 routes. It is the **intended entry point for the `open` step**, because the browser
  UI deliberately omits the live-acquisition "open" control (see Safety posture below).
- **Browser UI** (`/review/layer3`): the `sec-xbrl-*` panels drive `status`, `decision/submit`,
  `value-reveal/authority/prepare`, and `value-reveal/submit` once a `workflow_id` exists.

Either interface can drive the post-open steps. The recommended flow is **CLI `open` →
(CLI or UI) for the rest**.

## Safety posture (do not "fix" by exposing more in the UI)

The operator UI **intentionally excludes** controls that trigger live SEC acquisition or raw
disclosure from a click surface. The e2e suite asserts the open / source-acquisition /
arelle-invoke controls are absent (`e2e/layer3-workbench.spec.js`, the `blockedControlId`
groups). This is a deliberate defense-in-depth posture: live acquisition is a deliberate,
explicit operator action, not an accidental browser click. The CLI is that deliberate action —
it requires an explicit `--confirm` flag for both `open` (live fetch) and `reveal` (disclosure),
and never supplies any confirmation or decision value on the operator's behalf.

Do not wire the open/acquisition/reveal-trigger controls into the browser UI without an explicit
posture decision and updating those e2e invariants visibly.

## Prerequisites

- The API server running and reachable (set `--base-url` or `LAYER3_API_BASE_URL`, default
  `http://127.0.0.1:8000`).
- For the **live** `open` path: `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=true`, a SEC
  fair-access `LAYER3_SEC_EDGAR_USER_AGENT`, and the Arelle env
  (`SEC_XBRL_ARELLE_TAXONOMY_PACKAGES`, `SEC_XBRL_ARELLE_CACHE_DIR`,
  `SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY=online`, the Arelle corpus-validation flags). Without
  the live flag the `open` route returns a governed "live network disabled" error — the CLI
  prints it and exits nonzero.
- For `reveal`: the controlled-value-reveal feature flag must be enabled server-side
  (`layer3_sec_xbrl_controlled_value_reveal_submit_enabled`).
- For `AUTH_OWNER=proxy` deployments: pass `--identity <user>` and `--groups <csv>` so the CLI
  sends the proxy identity headers (`X-Forwarded-User` / `X-Forwarded-Groups` by default;
  override the header NAMES via `PROXY_IDENTITY_HEADER_NAME` / `PROXY_GROUPS_HEADER_NAME`). In
  `AUTH_OWNER=none` mode these are not needed.

Company coverage is the fixed allow-list of tickers in the acquisition connector
(`REAL_COMPANY_CIK_REFS`): AAPL, MSFT, NVDA, AMZN, TSLA, JPM, XOM, PFE, T, UAL, MET, PLD, FIZZ,
STLD, SONY, CCJ. The CLI derives the CIK from the ticker; use `--cik` to override.

## CLI lifecycle (full, scriptable)

```bash
# 1) Open a review (LIVE: fetches + Arelle + classification + optional CompanyFacts oracle).
#    --confirm is REQUIRED (it triggers a live SEC acquisition).
python -m app.cli.sec_xbrl_operator_cli open --ticker AAPL --require-oracle --confirm
#    -> prints redacted corpus/companyfacts summaries + the workflow_id + workflow_basis_hash.

# 2) Inspect status (optional).
python -m app.cli.sec_xbrl_operator_cli status --workflow-id <WF_ID> --workflow-basis-hash <WF_HASH>

# 3) Submit the operator decision. review_decision + reason_code are explicit human choices —
#    the CLI never defaults them. --notes is required for any non-approved decision.
python -m app.cli.sec_xbrl_operator_cli decide \
    --workflow-id <WF_ID> --workflow-basis-hash <WF_HASH> \
    --review-decision approved --reason-code ready_for_next_freeze
#    -> prints decision_id + decision_basis_hash.

# 4) Prepare the value-reveal authority (mechanical; only valid for approved+ready decisions).
python -m app.cli.sec_xbrl_operator_cli prepare-authority \
    --decision-id <DECISION_ID> --decision-basis-hash <DECISION_HASH>
#    -> prints authority_receipt_id + authority_basis_hash.

# 5) Reveal controlled values. --confirm is REQUIRED (it discloses raw financial values to
#    the authorized operator). Values print to stdout only and are NOT persisted by the CLI.
python -m app.cli.sec_xbrl_operator_cli reveal \
    --authority-receipt-id <AUTH_ID> --authority-basis-hash <AUTH_HASH> --confirm

# 6) Replay reveal status (hash-only; no raw values).
python -m app.cli.sec_xbrl_operator_cli reveal-status --receipt-id <SUBMIT_RECEIPT_ID>
```

`review_decision` ∈ {approved, changes_requested, rejected, blocked};
`reason_code` ∈ {ready_for_next_freeze, needs_packet_revision, authority_gap, redaction_gap,
operator_blocked}. The value-reveal authority requires `approved` + `ready_for_next_freeze`.

## Hybrid flow (CLI open → browser UI for the rest)

1. Run CLI `open` (above); copy the printed `workflow_id` (and `workflow_basis_hash`).
2. Open `/review/layer3` in the browser.
3. Paste the `workflow_id` into the **SEC-XBRL operator-review workflow status** panel; the
   decision and value-reveal panels auto-populate their ids as you proceed.
4. Submit the decision; prepare authority; tick the explicit reveal-confirmation checkbox to
   disclose values. (These UI panels are already wired to the same routes the CLI uses.)

## Honesty / safety invariants

- `--confirm` is mandatory and never defaulted for both `open` (live acquisition) and `reveal`
  (disclosure); `review_decision` / `reason_code` are always explicit operator inputs.
- Non-`reveal` output is hash/id/count only — the raw CIK is never echoed (the operator-typed
  ticker is). `reveal` prints raw values to stdout for the authorized operator, with a
  transient/sensitive warning, and the CLI does not write them to disk.
- `production_readiness_claimed` is `False` on every response; the tool is validate-only and
  does not self-certify production admission.
