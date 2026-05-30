# 1282 - SEC XBRL Sector-Conditioned Canonical Families

Milestone:

`sec_xbrl_sector_conditioned_canonical_families_deferred_design_v1`

## Scope

This design slice records the sector-conditioned canonical family decision and adds a validate-only, redacted coverage diagnostic. It does not change `CanonicalConcept`, add sector-family resolution, alter statement assembly, fetch SEC data, invoke Arelle, reveal values, persist runtime artifacts, or change runtime defaults.

Files in this slice:

- `next_milestone_plans/Layer3_planning_docs/1282-sec-xbrl-sector-conditioned-canonical-families.md`
- `diagnostics/assessment/sec-xbrl-sector-family-coverage.py`
- `diagnostics/assessment/sec-xbrl-sector-family-coverage-report.json`
- `backend/tests/test_sec_xbrl_sector_family_coverage.py`

Doc number 1282 follows statement-organization doc 1281.

## Sector Determination

Sector class is a reporting label only. The future runtime should read `dei:EntityPrimarySicNumber` from the filing data already carried by the SEC XBRL sidecar/value-store path, map it through the versioned table `sic_range_to_sector_class_v1`, and record only the sector-class label:

| SIC range | Sector class |
| --- | --- |
| 1000-1499 | `extractive` |
| 6000-6199 | `banking` |
| 6300-6411 | `insurance` |
| 6500-6599 | `real_estate_reit` |
| otherwise absent or unknown | `diversified_or_other` |

If `dei:EntityPrimarySicNumber` is absent, the documented fallback is SEC submissions metadata. That fallback is design-only here; this slice does not implement new SEC metadata retrieval.

## Core Decision

Sector conditioning is concept-presence driven, not SIC-gated.

The reference grounding includes a diversified filing whose primary SIC class maps outside banking and insurance while the filing reports insurance and banking concepts. A primary-SIC gate would discard those reported headline families. Therefore SIC remains a primary-sector label and cannot decide whether a family resolves. A family becomes eligible only when the filing reports one of the family's governed source qnames.

The follow-on implementation posture is:

`sec_xbrl_sector_conditioned_canonical_families_v1_resolution_presence_conditioned`

## Family Registry Shape

The follow-on resolution slice should extend the canonical registry design with a family qualifier such as `universal`, `extractive`, `banking`, `insurance`, or `real_estate_reit`. This design does not make that model change.

Each sector family is limited to headline, non-dimensional FY concepts for v1. Dimensional roll-forwards, detailed insurance movement tables, per-period projection, persisted store semantics, and final statement assembly stay out of scope.

## Grounded Headline Families

The first grounded family definitions are:

| Family | Canonical concept id | Source concept |
| --- | --- | --- |
| `extractive` | `ExtractiveExplorationEvaluationExpense` | `ifrs-full:ExpenseArisingFromExplorationForAndEvaluationOfMineralResources` |
| `extractive` | `ExtractiveCurrentOreStockpiles` | `ifrs-full:CurrentOreStockpiles` |
| `extractive` | `ExtractiveExplorationExpense` | `us-gaap:ExplorationExpense` |
| `banking` | `BankingInterestIncome` | `ifrs-full:InterestIncomeForFinancialAssetsMeasuredAtAmortisedCost` |
| `banking` | `BankingGrossLoanCommitments` | `ifrs-full:GrossLoanCommitments` |
| `banking` | `BankingCustomerDepositsCurrent` | `ifrs-full:CurrentDepositsFromCustomers` |
| `banking` | `BankingInterestAndDividendIncome` | `us-gaap:InterestAndDividendIncomeOperating` |
| `banking` | `BankingInterestExpense` | `us-gaap:InterestExpense` |
| `banking` | `BankingDeposits` | `us-gaap:Deposits` |
| `insurance` | `InsuranceRevenue` | `ifrs-full:InsuranceRevenue` |
| `insurance` | `InsuranceContractsLiabilityAsset` | `ifrs-full:InsuranceContractsLiabilityAsset` |
| `insurance` | `InsurancePremiumsEarnedNet` | `us-gaap:PremiumsEarnedNet` |
| `insurance` | `InsuranceClaimsAdjustmentExpenseLiability` | `us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense` |

## Coverage Diagnostic

The validate-only diagnostic records a redacted static reference summary from the operator survey. `None` input means "use the static reference evidence"; an explicit empty list means "no evidence" and fails closed with `no_sector_family_coverage_evidence`.

The committed report is restricted to sector class, family id, canonical concept id, public standard taxonomy concept id, taxonomy token, counts, coverage rates, and booleans. It excludes issuer names, raw SIC numbers, accessions, periods, URLs, local paths, raw values, and resolved fact authorities.

Reference evidence is intentionally count-only:

- Extractive family presence is recorded through two IFRS headline concepts.
- Banking family presence is recorded through three IFRS headline concepts.
- Insurance family presence is recorded through two IFRS headline concepts.
- One redacted reference filer remains universal-only for these families.

## Status

- `sector_conditioned_families_design_complete`: `true`
- `sector_conditioned_families_implemented`: `false`
- `sector_conditioning`: `concept_presence_not_sic_gated`
- `runtime_defaults_changed`: `false`
- `next_posture`: `sec_xbrl_sector_conditioned_canonical_families_v1_resolution_presence_conditioned`
