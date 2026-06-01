# 1285 - Multi-Period Projection

Milestone:

`sec_xbrl_multi_period_projection_design_v1`

## Scope

This implementation slice adds validate-only multi-period canonical projection over the governed SEC XBRL sidecar/value-store authority. It keeps the existing single-FY projection behavior intact and adds an explicit comparative-period wrapper.

Files in this slice:

- `backend/app/services/layer3_sec_xbrl_canonical_concepts.py`
- `backend/tests/test_sec_xbrl_canonical_projection.py`
- `backend/tests/test_sec_xbrl_multi_period_projection.py`
- `diagnostics/assessment/sec-xbrl-multi-period-projection.py`
- `diagnostics/assessment/sec-xbrl-multi-period-projection-report.json`
- `next_milestone_plans/Layer3_planning_docs/1285-multi-period.md`

## Runtime Contract

`fy_periods_from_records(...)` enumerates FY period candidates from non-dimensional standard sidecar records. The filing document-period end is ordered first when it matches a candidate period, followed by comparative FY periods.

`project_issuer_canonical_facts_by_periods(...)` runs the existing canonical projection for each selected FY period. Each period keeps the same value-store, sidecar receipt, dataset-version, oracle-confirmation, sector-family, and identity-residual behavior as the single-period projection.

The default `project_issuer_canonical_facts(...)` path remains unchanged for existing callers.

## Guardrails

The multi-period wrapper fails closed when no FY periods can be selected. It does not seed data, fetch SEC data, invoke Arelle, reveal values, persist projection rows, emit linkbase relationships, change statement assembly, or enable runtime defaults.

The committed diagnostic report is redacted. It reports only period references, counts, statement-level count rollups, document-period-match booleans, and validation criteria. It excludes raw values, raw resolved fact authorities, issuer identities, accessions, period dates, URLs, and local paths.

## Proof

Focused tests:

`python -m pytest ./backend/tests/test_sec_xbrl_multi_period_projection.py ./backend/tests/test_sec_xbrl_canonical_projection.py -q`

Result: `18 passed`.

Committed report:

`diagnostics/assessment/sec-xbrl-multi-period-projection-report.json`

Report decision:

`sec_xbrl_multi_period_projection_validate_only_ready`

## Next Posture

`sec_xbrl_projection_persistence_design_v1_tier2_risk_assessed_entry`

Real-filer sector-family validation is satisfied by the validate-only real-corpus runner gate `sec_xbrl_sector_family_real_filer_validation_v1`, using redacted operator-acquired offline receipts for US-GAAP bank and insurer annual filings. Persistence remains deferred to a Tier 2 risk-assessed design entry step. The deferred persistence work is preserved on branch `codex/sec-family-res`; it is reference-only and not a merge base for this no-schema landing branch.

The validation gate extends the existing real-corpus product runner with sector-family activation as a validated dimension. It does not introduce a standalone greenfield diagnostic.

The committed runner report records separate redacted storage markers for the broader live matrix run and the operator-supplied offline sector-family evidence. That provenance split is intentional and is not a same-root claim; no raw local paths are committed.

Non-blocking backlog note: keyed or salted HMAC issuer pseudonyms may be useful as operator-side defense in depth for offline artifacts that hash real CIKs before redaction. The committed surface is already safe for this landing because synthetic issuer-hash preimages and count-only real-corpus summaries are used; HMAC pseudonyms are not part of this landing and are not a gate.
