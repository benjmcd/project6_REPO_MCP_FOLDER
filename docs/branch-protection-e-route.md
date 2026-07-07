# E-route: branch protection for `main` (owner-executable)

Status: preparation artifact. The enabling step is a GitHub repository-settings/admin action reserved to the owner; this doc supplies the exact, verified command and rationale. Nothing here changes repository behavior until the owner runs the command.

## 2026-07-07 supersession note (M-RELEASE-GATE-F5)

Live branch protection for `main` is now active. The verified rule requires
the exact contexts `release-gate`, `test`, and `root-tests`, with
`strict=false` and `enforce_admins=true`. The historical "no branch
protection" and fail-open premise below is therefore retained only as prior
context.

The F5 lane also promotes release-gate from a five-family aggregate to an
eight-family aggregate: `release-lock-install`, `backend-layer3-api`,
`backend-coverage`, `backend-migrations-postgres`,
`sec-xbrl-arelle-provisioning`, `root-tests`, `nrc-aps-ocr`, and `test`.
Because `test` and `root-tests` are already branch-protection contexts, their
release-gate membership is coverage-coherence rather than new platform
enforcement. `nrc-aps-ocr` is the net-new release-gate-blocking CI family.

## Current state (the fail-open)
`main` has **no branch protection**: `gh api repos/benjmcd/project6_REPO_MCP_FOLDER/branches/main/protection` returns `404 Branch not protected`. CI runs on every PR and push to `main`, but green CI is **author-enforced** — nothing at the platform level blocks a merge while checks are failing or pending. Closing this gap is the "E-route" referenced in prior governance discussion.

## CI topology (verified at `main` = f64faacd, `.github/workflows/playwright.yml`)
Triggers: `push` and `pull_request` to `main`/`master`. Terminal/aggregator jobs and their roles:

| Job (`name:`) | Role | `if: always()` | Covers (via `needs:` + result-check) |
|---|---|---|---|
| `release-gate` | release identity + RC acceptance + manifest gate | yes | `release-lock-install`, `backend-layer3-api` (→ its 4 shards), `backend-coverage`, `backend-migrations-postgres`; also runs `release_readiness_check.py` and the current RC acceptance capstone |
| `test` | Playwright aggregate | yes | `playwright-shard` (4 shards) |
| `backend-layer3-api` | backend Layer 3 API aggregate | (verify) | `backend-layer3-api-shard` (4) |
| `root-tests` | repo-root test aggregate | (verify) | `root-tests-shard` (4) |
| `sec-xbrl-arelle-provisioning` | optional Arelle provisioning + fail-closed | (verify trigger) | standalone |
| `nrc-aps-ocr` | NRC APS OCR proof | (verify trigger) | standalone |

`release-gate`'s "Check manifest-backed CI jobs" step exits non-zero if any of its four needed jobs is not `success`, and it has `if: always()`, so **`release-gate == success` transitively implies the whole backend/release pipeline passed**. `test == success` implies all Playwright shards passed.

## Recommended required status checks
Core (verified to run unconditionally with `if: always()`, and together they gate the backend/release pipeline and the e2e suite):

```
["release-gate", "test"]
```

Optional additions for defense-in-depth — add ONLY after confirming each runs on every PR with `if: always()` (a required check that is ever skipped/never-runs blocks merges indefinitely): `root-tests` (root suite is not in `release-gate`'s needs), `sec-xbrl-arelle-provisioning`, `nrc-aps-ocr`.

Context strings must exactly equal the job `name:` field. Matrix/shard jobs (`backend-layer3-api-shard-N/4`, etc.) are NOT listed directly — they are covered by their aggregators.

## Owner command (run with repo admin permissions)
```bash
gh api -X PUT repos/benjmcd/project6_REPO_MCP_FOLDER/branches/main/protection --input - <<'EOF'
{
  "required_status_checks": { "strict": true, "contexts": ["release-gate", "test"] },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF
```
- `strict: true` — branch must be up to date with `main` before merge (re-runs checks on stale branches; expect occasional "out of date" rebases).
- `enforce_admins: true` — admins are also gated (drop to `false` if you need an admin override hatch).
- `required_pull_request_reviews: null` — no human-review requirement added here; this is a *CI* gate only. (The SEC XBRL review policy is governed separately by `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`; see the #2010 reconciliation record.)

## Verify after enabling
1. `gh api repos/benjmcd/project6_REPO_MCP_FOLDER/branches/main/protection` returns the rule (no 404).
2. GitHub UI: Settings > Branches > Branch protection rules shows `release-gate` and `test` as required.
3. Open a throwaway draft PR; confirm the two checks are requested and that "Merge" is blocked until they report success.

## Caveats
- Admin/owner-only action; non-admin agents/users cannot enable it.
- If a listed context's job name changes in `playwright.yml`, the required check will hang as "expected" forever — keep this list in sync with the workflow `name:` fields.
- This is a CI fail-closed gate, not a review mandate; it is orthogonal to and compatible with the canonical SEC XBRL merge-gate policy.
