from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_canonical_concepts.v1"
REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_canonical_comparability.v1"
PROJECTION_REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_canonical_projection.v1"
COVERAGE_BREADTH_REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_canonical_coverage_breadth.v1"
MAPPING_CONFIDENCE = "reviewed_high_value_headline_statement_crosswalk"
IDENTITY_TOLERANCE = Decimal("0.005")
PERIOD_CLASS = "FY"


@dataclass(frozen=True)
class SourceConcept:
    taxonomy: str
    local_name: str

    @property
    def qname(self) -> str:
        return f"{self.taxonomy}:{self.local_name}"


@dataclass(frozen=True)
class CanonicalConcept:
    canonical_id: str
    basis: str
    statement: str
    sources: tuple[SourceConcept, ...]

    @property
    def key(self) -> str:
        return f"{self.canonical_id}[{self.basis}]"


CANONICAL_CONCEPTS: tuple[CanonicalConcept, ...] = (
    CanonicalConcept(
        "Revenue",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
            SourceConcept("us-gaap", "Revenues"),
            SourceConcept("ifrs-full", "Revenue"),
        ),
    ),
    CanonicalConcept(
        "CostOfSales",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "CostOfGoodsAndServicesSold"),
            SourceConcept("us-gaap", "CostOfRevenue"),
            SourceConcept("ifrs-full", "CostOfSales"),
        ),
    ),
    CanonicalConcept(
        "GrossProfit",
        "total",
        "income",
        (SourceConcept("us-gaap", "GrossProfit"), SourceConcept("ifrs-full", "GrossProfit")),
    ),
    CanonicalConcept(
        "OperatingIncome",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "OperatingIncomeLoss"),
            SourceConcept("ifrs-full", "ProfitLossFromOperatingActivities"),
        ),
    ),
    CanonicalConcept(
        "ProfitBeforeTax",
        "total",
        "income",
        (
            SourceConcept(
                "us-gaap",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            ),
            SourceConcept(
                "us-gaap",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            ),
            SourceConcept("ifrs-full", "ProfitLossBeforeTax"),
        ),
    ),
    CanonicalConcept(
        "IncomeTaxExpense",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "IncomeTaxExpenseBenefit"),
            SourceConcept("ifrs-full", "IncomeTaxExpenseContinuingOperations"),
        ),
    ),
    CanonicalConcept(
        "ProfitLoss",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "ProfitLoss"),
            SourceConcept("ifrs-full", "ProfitLoss"),
            SourceConcept("us-gaap", "NetIncomeLoss"),
        ),
    ),
    CanonicalConcept(
        "ProfitLoss",
        "parent",
        "income",
        (
            SourceConcept("us-gaap", "NetIncomeLoss"),
            SourceConcept("ifrs-full", "ProfitLossAttributableToOwnersOfParent"),
        ),
    ),
    CanonicalConcept(
        "EpsBasic",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "EarningsPerShareBasic"),
            SourceConcept("ifrs-full", "BasicEarningsLossPerShare"),
        ),
    ),
    CanonicalConcept(
        "EpsDiluted",
        "total",
        "income",
        (
            SourceConcept("us-gaap", "EarningsPerShareDiluted"),
            SourceConcept("ifrs-full", "DilutedEarningsLossPerShare"),
        ),
    ),
    CanonicalConcept(
        "CashAndEquivalents",
        "total",
        "balance",
        (
            SourceConcept("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
            SourceConcept("ifrs-full", "CashAndCashEquivalents"),
        ),
    ),
    CanonicalConcept(
        "CurrentAssets",
        "total",
        "balance",
        (SourceConcept("us-gaap", "AssetsCurrent"), SourceConcept("ifrs-full", "CurrentAssets")),
    ),
    CanonicalConcept(
        "NoncurrentAssets",
        "total",
        "balance",
        (SourceConcept("us-gaap", "AssetsNoncurrent"), SourceConcept("ifrs-full", "NoncurrentAssets")),
    ),
    CanonicalConcept(
        "TotalAssets",
        "total",
        "balance",
        (SourceConcept("us-gaap", "Assets"), SourceConcept("ifrs-full", "Assets")),
    ),
    CanonicalConcept(
        "CurrentLiabilities",
        "total",
        "balance",
        (SourceConcept("us-gaap", "LiabilitiesCurrent"), SourceConcept("ifrs-full", "CurrentLiabilities")),
    ),
    CanonicalConcept(
        "NoncurrentLiabilities",
        "total",
        "balance",
        (
            SourceConcept("us-gaap", "LiabilitiesNoncurrent"),
            SourceConcept("ifrs-full", "NoncurrentLiabilities"),
        ),
    ),
    CanonicalConcept(
        "TotalLiabilities",
        "total",
        "balance",
        (SourceConcept("us-gaap", "Liabilities"), SourceConcept("ifrs-full", "Liabilities")),
    ),
    CanonicalConcept(
        "Equity",
        "total",
        "balance",
        (
            SourceConcept("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
            SourceConcept("ifrs-full", "Equity"),
        ),
    ),
    CanonicalConcept(
        "Equity",
        "parent",
        "balance",
        (
            SourceConcept("us-gaap", "StockholdersEquity"),
            SourceConcept("ifrs-full", "EquityAttributableToOwnersOfParent"),
        ),
    ),
    CanonicalConcept(
        "OperatingCashFlow",
        "total",
        "cashflow",
        (
            SourceConcept("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
            SourceConcept("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
        ),
    ),
    CanonicalConcept(
        "InvestingCashFlow",
        "total",
        "cashflow",
        (
            SourceConcept("us-gaap", "NetCashProvidedByUsedInInvestingActivities"),
            SourceConcept("ifrs-full", "CashFlowsFromUsedInInvestingActivities"),
        ),
    ),
    CanonicalConcept(
        "FinancingCashFlow",
        "total",
        "cashflow",
        (
            SourceConcept("us-gaap", "NetCashProvidedByUsedInFinancingActivities"),
            SourceConcept("ifrs-full", "CashFlowsFromUsedInFinancingActivities"),
        ),
    ),
)

_CONCEPT_BY_KEY = {concept.key: concept for concept in CANONICAL_CONCEPTS}
_NONCURRENT_DERIVATIONS = (
    ("NoncurrentAssets[total]", "TotalAssets[total]", "CurrentAssets[total]"),
    ("NoncurrentLiabilities[total]", "TotalLiabilities[total]", "CurrentLiabilities[total]"),
)
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*:" + "/" + "/")
_LOCAL_PATH_RE = re.compile(r"[A-Za-z]:[\\/]")
_CONTACT_RE = re.compile("contact" + r"@nexonpvp\.net", re.IGNORECASE)


def canonical_concept_inventory() -> list[dict[str, Any]]:
    return [
        {
            "canonical_id": concept.canonical_id,
            "basis": concept.basis,
            "statement": concept.statement,
            "source_qnames": [source.qname for source in concept.sources],
            "mapping_method": "reviewed_statement_crosswalk",
            "mapping_confidence": MAPPING_CONFIDENCE,
        }
        for concept in CANONICAL_CONCEPTS
    ]


def primary_taxonomy_from_records(records: Sequence[Mapping[str, Any]]) -> str:
    counts: Counter[str] = Counter()
    for record in records:
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        namespace = str(concept.get("namespace") or "")
        taxonomy = taxonomy_from_namespace(namespace)
        if taxonomy in {"us-gaap", "ifrs-full"}:
            counts[taxonomy] += 1
    if not counts:
        return "unknown"
    return "ifrs-full" if counts["ifrs-full"] >= counts["us-gaap"] else "us-gaap"


def taxonomy_from_namespace(namespace: str) -> str:
    if "fasb.org/us-gaap" in namespace:
        return "us-gaap"
    if "xbrl.ifrs.org" in namespace:
        return "ifrs-full"
    return "unknown"


def resolve_issuer_canonical_concepts(
    *,
    companyfacts: Mapping[str, Any],
    sidecar_records: Sequence[Mapping[str, Any]],
    value_records: Sequence[Mapping[str, Any]],
    fiscal_year: int | str | None = None,
) -> dict[str, Any]:
    primary_taxonomy = primary_taxonomy_from_records(sidecar_records)
    value_by_fact_id = {
        str(item.get("resolved_fact_id") or ""): item
        for item in value_records
        if isinstance(item, Mapping)
    }
    resolutions: list[dict[str, Any]] = []
    for concept in CANONICAL_CONCEPTS:
        resolution = _resolve_concept(
            concept=concept,
            companyfacts=companyfacts,
            sidecar_records=sidecar_records,
            value_by_fact_id=value_by_fact_id,
            primary_taxonomy=primary_taxonomy,
            fiscal_year=fiscal_year,
        )
        if resolution["status"] == "legitimately_absent" and concept.basis == "total":
            fallback = _parent_fallback(concept)
            if fallback is not None:
                fallback_resolution = _resolve_concept(
                    concept=fallback,
                    companyfacts=companyfacts,
                    sidecar_records=sidecar_records,
                    value_by_fact_id=value_by_fact_id,
                    primary_taxonomy=primary_taxonomy,
                    fiscal_year=fiscal_year,
                    requested_basis=concept.basis,
                    mapping_method="basis_fallback_total_to_parent",
                )
                if fallback_resolution["status"] != "legitimately_absent":
                    resolution = fallback_resolution
        resolutions.append(resolution)
    _apply_noncurrent_derivations(resolutions, projection=False)
    identities = statement_identity_residuals(resolutions)
    return {
        "primary_taxonomy": primary_taxonomy,
        "defined_count": len(CANONICAL_CONCEPTS),
        "resolved_count": sum(1 for item in resolutions if item["status"] != "legitimately_absent"),
        "inline_confirmed_count": sum(1 for item in resolutions if item.get("inline_confirmed") is True),
        "legitimately_absent_count": sum(1 for item in resolutions if item["status"] == "legitimately_absent"),
        "concepts": resolutions,
        "statement_identity_residuals": identities,
    }


def primary_fy_period_from_records(
    records: Sequence[Mapping[str, Any]],
    value_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    value_by_fact_id = {
        str(item.get("resolved_fact_id") or ""): item
        for item in (value_records or [])
        if isinstance(item, Mapping)
    }
    instant_ends: list[str] = []
    duration_starts_by_end: dict[str, list[str]] = {}
    document_period_end_values: list[str] = []
    for record in records:
        if not _is_standard_non_dimensional_record(record):
            continue
        period = record.get("period") if isinstance(record.get("period"), Mapping) else {}
        period_type = str(period.get("type") or "")
        if period_type == "instant" and str(period.get("instant") or ""):
            instant_ends.append(str(period.get("instant") or ""))
        elif period_type == "duration" and str(period.get("start") or "") and str(period.get("end") or ""):
            duration_starts_by_end.setdefault(str(period.get("end") or ""), []).append(str(period.get("start") or ""))
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        if str(concept.get("local_name") or "") == "DocumentPeriodEndDate":
            value_record = value_by_fact_id.get(str(record.get("resolved_fact_id") or ""))
            if isinstance(value_record, Mapping) and str(value_record.get("effective_value") or ""):
                document_period_end_values.append(str(value_record.get("effective_value") or ""))

    candidate_ends = sorted(set(instant_ends) | set(duration_starts_by_end))
    if not candidate_ends:
        return {
            "status": "missing_fy_period",
            "period_class": PERIOD_CLASS,
            "instant_period_key": None,
            "duration_period_key": None,
            "document_period_end_date_cross_checked": False,
        }

    end = next((item for item in sorted(document_period_end_values, reverse=True) if item in candidate_ends), candidate_ends[-1])
    duration_starts = sorted(set(duration_starts_by_end.get(end) or []))
    duration_key = ("d", duration_starts[0], end) if duration_starts else None
    return {
        "status": "ready",
        "period_class": PERIOD_CLASS,
        "instant_period_key": ("i", end),
        "duration_period_key": duration_key,
        "document_period_end_date_cross_checked": (
            not document_period_end_values or any(item == end for item in document_period_end_values)
        ),
    }


def project_issuer_canonical_facts(
    *,
    companyfacts: Mapping[str, Any],
    sidecar_records: Sequence[Mapping[str, Any]],
    value_records: Sequence[Mapping[str, Any]],
    sidecar_receipt_id: str | None,
    sidecar_receipt_hash: str | None,
    value_store_hash: str | None,
    dataset_version_id: str | None,
    fiscal_year: int | str | None = None,
) -> dict[str, Any]:
    primary_taxonomy = primary_taxonomy_from_records(sidecar_records)
    fy_period = primary_fy_period_from_records(sidecar_records, value_records)
    if fy_period["status"] != "ready":
        return _blocked_projection(
            primary_taxonomy=primary_taxonomy,
            reason="canonical_projection_fy_period_missing",
            evidence={"period_class": PERIOD_CLASS},
        )
    if fy_period.get("document_period_end_date_cross_checked") is not True:
        return _blocked_projection(
            primary_taxonomy=primary_taxonomy,
            reason="canonical_projection_document_period_end_mismatch",
            evidence={"period_class": PERIOD_CLASS},
        )

    value_by_fact_id = {
        str(item.get("resolved_fact_id") or ""): item
        for item in value_records
        if isinstance(item, Mapping)
    }
    expected_value_store_hash = str(value_store_hash or "")
    if expected_value_store_hash and stable_hash(list(value_records)) != expected_value_store_hash:
        return _blocked_projection(
            primary_taxonomy=primary_taxonomy,
            reason="canonical_projection_value_store_hash_mismatch",
            evidence={"value_record_count": len(value_records)},
        )

    shared_provenance = {
        "sidecar_receipt_id": str(sidecar_receipt_id or ""),
        "sidecar_receipt_hash": str(sidecar_receipt_hash or ""),
        "value_store_hash": expected_value_store_hash,
        "dataset_version_id": str(dataset_version_id or ""),
    }
    projections: list[dict[str, Any]] = []
    blocking_reasons: list[dict[str, Any]] = []
    for concept in CANONICAL_CONCEPTS:
        projection = _project_concept(
            concept=concept,
            companyfacts=companyfacts,
            sidecar_records=sidecar_records,
            value_by_fact_id=value_by_fact_id,
            primary_taxonomy=primary_taxonomy,
            fy_period=fy_period,
            fiscal_year=fiscal_year,
            shared_provenance=shared_provenance,
        )
        if projection.get("_blocked_reason") is not None:
            blocking_reasons.append(dict(projection["_blocked_reason"]))
            continue
        if projection["status"] == "legitimately_absent" and concept.basis == "total":
            fallback = _parent_fallback(concept)
            if fallback is not None:
                fallback_projection = _project_concept(
                    concept=fallback,
                    companyfacts=companyfacts,
                    sidecar_records=sidecar_records,
                    value_by_fact_id=value_by_fact_id,
                    primary_taxonomy=primary_taxonomy,
                    fy_period=fy_period,
                    fiscal_year=fiscal_year,
                    requested_basis=concept.basis,
                    mapping_method="basis_fallback_total_to_parent",
                    shared_provenance=shared_provenance,
                )
                if fallback_projection.get("_blocked_reason") is not None:
                    blocking_reasons.append(dict(fallback_projection["_blocked_reason"]))
                    continue
                if fallback_projection["status"] != "legitimately_absent":
                    projection = fallback_projection
        projections.append(projection)

    if blocking_reasons:
        return _blocked_projection(
            primary_taxonomy=primary_taxonomy,
            reason="canonical_projection_provenance_or_value_blocked",
            evidence={"blocking_reason_count": len(blocking_reasons)},
            blocking_reasons=blocking_reasons,
        )

    _apply_noncurrent_derivations(projections, projection=True)
    identities = statement_identity_residuals(projections)
    projected = [item for item in projections if item["status"] != "legitimately_absent"]
    confirmed_or_unconfirmed = [
        item for item in projected if item.get("oracle_confirmed") in {True, False}
    ]
    confirmed = [item for item in projected if item.get("oracle_confirmed") is True]
    return {
        "status": "canonical_projection_ready",
        "primary_taxonomy": primary_taxonomy,
        "period_class": PERIOD_CLASS,
        "defined_count": len(CANONICAL_CONCEPTS),
        "projected_count": len(projected),
        "oracle_confirmed_count": len(confirmed),
        "oracle_absent_count": sum(1 for item in projected if item.get("oracle_confirmed") == "oracle_absent"),
        "projected_unconfirmed_count": sum(1 for item in projected if item.get("oracle_confirmed") is False),
        "legitimately_absent_count": sum(1 for item in projections if item["status"] == "legitimately_absent"),
        "provenance_complete_count": sum(1 for item in projected if item.get("provenance_complete") is True),
        "oracle_confirmed_rate_excluding_absent": (
            round(len(confirmed) / len(confirmed_or_unconfirmed), 4) if confirmed_or_unconfirmed else None
        ),
        "fy_period": fy_period,
        "concepts": projections,
        "statement_identity_residuals": identities,
        "blocking_reasons": [],
    }


def build_redacted_projection_report(
    *,
    issuer_bundles: Sequence[Mapping[str, Any]],
    fiscal_year: int | str | None = None,
) -> dict[str, Any]:
    per_issuer = []
    total_projected = 0
    total_confirmed = 0
    total_oracle_absent = 0
    total_absent = 0
    total_provenance_complete = 0
    identity_count = 0
    identity_ok_count = 0
    blocking_reasons: list[dict[str, Any]] = []
    for index, bundle in enumerate(issuer_bundles):
        issuer_ref = str(bundle.get("issuer_ref") or f"issuer-{index}")
        projection = project_issuer_canonical_facts(
            companyfacts=dict(bundle.get("companyfacts") or {}),
            sidecar_records=list(bundle.get("sidecar_records") or []),
            value_records=list(bundle.get("value_records") or []),
            sidecar_receipt_id=str(bundle.get("sidecar_receipt_id") or ""),
            sidecar_receipt_hash=str(bundle.get("sidecar_receipt_hash") or ""),
            value_store_hash=str(bundle.get("value_store_hash") or ""),
            dataset_version_id=str(bundle.get("dataset_version_id") or ""),
            fiscal_year=fiscal_year,
        )
        if projection["status"] != "canonical_projection_ready":
            blocking_reasons.extend(list(projection.get("blocking_reasons") or []))
        identities = [
            _public_identity(item)
            for item in projection.get("statement_identity_residuals") or []
            if item["status"] == "evaluated"
        ]
        total_projected += int(projection.get("projected_count") or 0)
        total_confirmed += int(projection.get("oracle_confirmed_count") or 0)
        total_oracle_absent += int(projection.get("oracle_absent_count") or 0)
        total_absent += int(projection.get("legitimately_absent_count") or 0)
        total_provenance_complete += int(projection.get("provenance_complete_count") or 0)
        identity_count += len(identities)
        identity_ok_count += sum(1 for item in identities if item["within_tolerance"] is True)
        per_issuer.append(
            {
                "issuer_hash": stable_hash({"issuer_ref": issuer_ref})[:24],
                "primary_taxonomy": projection["primary_taxonomy"],
                "period_class": PERIOD_CLASS,
                "headline_canonical_defined": projection.get("defined_count", len(CANONICAL_CONCEPTS)),
                "projected_count": projection.get("projected_count", 0),
                "oracle_confirmed_count": projection.get("oracle_confirmed_count", 0),
                "oracle_absent_count": projection.get("oracle_absent_count", 0),
                "legitimately_absent_count": projection.get("legitimately_absent_count", 0),
                "provenance_complete_count": projection.get("provenance_complete_count", 0),
                "provenance_fields_present": _public_provenance_presence(
                    list(projection.get("concepts") or [])
                ),
                "concepts": [_public_projection(item) for item in projection.get("concepts") or []],
                "statement_identity_residuals": identities,
            }
        )
    report: dict[str, Any] = {
        "schema_id": PROJECTION_REPORT_SCHEMA_ID,
        "target": "sec_xbrl_canonical_projection_artifact_validate_only_v1",
        "decision": "canonical_projection_validate_only_ready" if not blocking_reasons else "canonical_projection_validate_only_blocked",
        "source_mode": "supplied_governed_source_bundles",
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "value_authority": "governed_arelle_sidecar_value_store",
        "oracle_authority": "companyfacts_period_aware_validation_only",
        "coverage_framing": "headline_canonical_projected_over_defined_not_filing_wide",
        "canonical_concept_defined_count": len(CANONICAL_CONCEPTS),
        "issuer_hash_count": len(per_issuer),
        "summary": {
            "headline_canonical_cell_count": len(CANONICAL_CONCEPTS) * len(per_issuer),
            "projected_count": total_projected,
            "oracle_confirmed_count": total_confirmed,
            "oracle_absent_count": total_oracle_absent,
            "legitimately_absent_count": total_absent,
            "provenance_complete_count": total_provenance_complete,
            "statement_identity_evaluated_count": identity_count,
            "statement_identity_within_tolerance_count": identity_ok_count,
        },
        "canonical_concepts": canonical_concept_inventory(),
        "per_issuer": per_issuer,
        "blocking_reasons": blocking_reasons,
        "redaction": {},
        "non_goals_preserved": _projection_non_goals(),
    }
    report["redaction"] = report_redaction_scan_payload(report)
    return report


def build_redacted_comparability_report(
    *,
    issuer_bundles: Sequence[Mapping[str, Any]],
    fiscal_year: int | str | None = None,
) -> dict[str, Any]:
    per_issuer = []
    total_resolved = 0
    total_inline = 0
    total_absent = 0
    identity_count = 0
    identity_ok_count = 0
    for index, bundle in enumerate(issuer_bundles):
        issuer_ref = str(bundle.get("issuer_ref") or f"issuer-{index}")
        resolution = resolve_issuer_canonical_concepts(
            companyfacts=dict(bundle.get("companyfacts") or {}),
            sidecar_records=list(bundle.get("sidecar_records") or []),
            value_records=list(bundle.get("value_records") or []),
            fiscal_year=fiscal_year,
        )
        identities = [
            _public_identity(item)
            for item in resolution["statement_identity_residuals"]
            if item["status"] == "evaluated"
        ]
        total_resolved += int(resolution["resolved_count"])
        total_inline += int(resolution["inline_confirmed_count"])
        total_absent += int(resolution["legitimately_absent_count"])
        identity_count += len(identities)
        identity_ok_count += sum(1 for item in identities if item["within_tolerance"] is True)
        per_issuer.append(
            {
                "issuer_hash": stable_hash({"issuer_ref": issuer_ref})[:24],
                "primary_taxonomy": resolution["primary_taxonomy"],
                "period_class": PERIOD_CLASS,
                "headline_canonical_defined": resolution["defined_count"],
                "headline_canonical_resolved": resolution["resolved_count"],
                "headline_canonical_inline_confirmed": resolution["inline_confirmed_count"],
                "headline_canonical_legitimately_absent": resolution["legitimately_absent_count"],
                "concepts": [_public_resolution(item) for item in resolution["concepts"]],
                "statement_identity_residuals": identities,
            }
        )
    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "target": "sec_xbrl_canonical_cross_company_comparability_validate_only_v1",
        "decision": "canonical_comparability_validate_only_ready",
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "coverage_framing": "headline_canonical_resolved_over_defined_only_not_filing_wide",
        "canonical_concept_defined_count": len(CANONICAL_CONCEPTS),
        "issuer_hash_count": len(per_issuer),
        "summary": {
            "headline_canonical_cell_count": len(CANONICAL_CONCEPTS) * len(per_issuer),
            "headline_canonical_resolved_count": total_resolved,
            "headline_canonical_inline_confirmed_count": total_inline,
            "headline_canonical_legitimately_absent_count": total_absent,
            "headline_canonical_unexplained_gap_count": (
                len(CANONICAL_CONCEPTS) * len(per_issuer) - total_resolved - total_absent
            ),
            "statement_identity_evaluated_count": identity_count,
            "statement_identity_within_tolerance_count": identity_ok_count,
        },
        "canonical_concepts": canonical_concept_inventory(),
        "per_issuer": per_issuer,
        "redaction": report_redaction_scan_payload(per_issuer),
        "non_goals_preserved": {
            "default_on_readiness_claimed": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_currency_conversion_claimed": False,
            "statement_assembly_claimed": False,
            "linkbase_relationships_required_or_consumed": False,
        },
    }
    report["redaction"] = report_redaction_scan_payload(report)
    return report


def report_redaction_scan_payload(payload: Any) -> dict[str, bool]:
    text = str(payload)
    return {
        "raw_accession_found": bool(_ACCESSION_RE.search(text)),
        "raw_contact_found": bool(_CONTACT_RE.search(text)),
        "raw_local_path_found": bool(_LOCAL_PATH_RE.search(text)),
        "raw_period_date_found": bool(_DATE_RE.search(text)),
        "raw_url_found": bool(_URL_RE.search(text)),
        "raw_values_in_report": False,
        "passed": not any(
            (
                _ACCESSION_RE.search(text),
                _CONTACT_RE.search(text),
                _LOCAL_PATH_RE.search(text),
                _DATE_RE.search(text),
                _URL_RE.search(text),
            )
        ),
    }


def statement_identity_residuals(resolutions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    resolved = {
        str(item.get("_resolution_key") or ""): item
        for item in resolutions
        if item.get("status") != "legitimately_absent" and isinstance(item.get("_value"), Decimal)
    }
    return [
        _identity(
            "current_assets_plus_noncurrent_assets_equals_total_assets",
            resolved,
            ("CurrentAssets[total]", "NoncurrentAssets[total]", "TotalAssets[total]"),
            lambda values: values[0] + values[1] - values[2],
            "TotalAssets[total]",
        ),
        _identity(
            "total_liabilities_plus_equity_equals_total_assets",
            resolved,
            ("TotalLiabilities[total]", "Equity[total]", "TotalAssets[total]"),
            lambda values: values[0] + values[1] - values[2],
            "TotalAssets[total]",
        ),
        _derived_liabilities_identity(resolved),
        _identity(
            "revenue_minus_cost_of_sales_equals_gross_profit",
            resolved,
            ("Revenue[total]", "CostOfSales[total]", "GrossProfit[total]"),
            lambda values: values[0] - values[1] - values[2],
            "Revenue[total]",
        ),
        _identity(
            "current_liabilities_plus_noncurrent_liabilities_equals_total_liabilities",
            resolved,
            ("CurrentLiabilities[total]", "NoncurrentLiabilities[total]", "TotalLiabilities[total]"),
            lambda values: values[0] + values[1] - values[2],
            "TotalLiabilities[total]",
        ),
    ]


def _resolve_concept(
    *,
    concept: CanonicalConcept,
    companyfacts: Mapping[str, Any],
    sidecar_records: Sequence[Mapping[str, Any]],
    value_by_fact_id: Mapping[str, Mapping[str, Any]],
    primary_taxonomy: str,
    fiscal_year: int | str | None,
    requested_basis: str | None = None,
    mapping_method: str = "primary_taxonomy_curated_crosswalk",
) -> dict[str, Any]:
    for source in _ordered_sources(concept, primary_taxonomy):
        fact = _companyfacts_fy_fact(companyfacts, source, fiscal_year=fiscal_year)
        if fact is None:
            continue
        inline = _inline_confirmation(
            sidecar_records=sidecar_records,
            value_by_fact_id=value_by_fact_id,
            source=source,
            unit=str(fact["unit"]),
            period_key=tuple(fact["period_key"]),
            value=fact["value"],
        )
        status = "resolved_inline_confirmed" if inline["confirmed"] else "resolved_without_inline_confirmation"
        return {
            "canonical_id": concept.canonical_id,
            "basis": concept.basis,
            "requested_basis": requested_basis or concept.basis,
            "statement": concept.statement,
            "status": status,
            "source_qname": source.qname,
            "period_class": PERIOD_CLASS,
            "inline_confirmed": inline["confirmed"],
            "mapping_method": mapping_method,
            "mapping_confidence": MAPPING_CONFIDENCE,
            "unit_class": _unit_class(str(fact["unit"])),
            "resolved_fact_id": inline.get("resolved_fact_id"),
            "_resolution_key": concept.key if requested_basis is None else f"{concept.canonical_id}[{requested_basis}]",
            "_value": fact["value"],
            "_unit": str(fact["unit"]),
        }
    return {
        "canonical_id": concept.canonical_id,
        "basis": concept.basis,
        "requested_basis": requested_basis or concept.basis,
        "statement": concept.statement,
        "status": "legitimately_absent",
        "source_qname": None,
        "period_class": PERIOD_CLASS,
        "inline_confirmed": False,
        "mapping_method": mapping_method,
        "mapping_confidence": MAPPING_CONFIDENCE,
        "absence_reason": "no_reviewed_fy_source_fact",
        "_resolution_key": concept.key if requested_basis is None else f"{concept.canonical_id}[{requested_basis}]",
    }


def _project_concept(
    *,
    concept: CanonicalConcept,
    companyfacts: Mapping[str, Any],
    sidecar_records: Sequence[Mapping[str, Any]],
    value_by_fact_id: Mapping[str, Mapping[str, Any]],
    primary_taxonomy: str,
    fy_period: Mapping[str, Any],
    fiscal_year: int | str | None,
    shared_provenance: Mapping[str, str],
    requested_basis: str | None = None,
    mapping_method: str = "primary_taxonomy_sidecar_value_store_projection",
) -> dict[str, Any]:
    for source in _ordered_sources(concept, primary_taxonomy):
        record = _sidecar_fy_record(
            sidecar_records=sidecar_records,
            source=source,
            fy_period=fy_period,
            statement=concept.statement,
        )
        if record is None:
            continue
        resolved_fact_id = str(record.get("resolved_fact_id") or "")
        if not resolved_fact_id:
            return _blocked_concept_projection(
                concept=concept,
                requested_basis=requested_basis,
                reason="canonical_projection_resolved_fact_id_missing",
                source_qname=source.qname,
            )
        value_record = value_by_fact_id.get(resolved_fact_id)
        if not isinstance(value_record, Mapping):
            return _blocked_concept_projection(
                concept=concept,
                requested_basis=requested_basis,
                reason="canonical_projection_value_store_record_missing",
                source_qname=source.qname,
            )
        effective_value = _decimal(value_record.get("effective_value"))
        if effective_value is None:
            return _blocked_concept_projection(
                concept=concept,
                requested_basis=requested_basis,
                reason="canonical_projection_effective_value_invalid",
                source_qname=source.qname,
            )
        missing_provenance = [
            field for field, value in shared_provenance.items() if not str(value or "").strip()
        ]
        if missing_provenance:
            return _blocked_concept_projection(
                concept=concept,
                requested_basis=requested_basis,
                reason="canonical_projection_provenance_incomplete",
                source_qname=source.qname,
                evidence={"missing_provenance_fields": missing_provenance},
            )
        unit = _unit_name(record.get("unit") if isinstance(record.get("unit"), Mapping) else {})
        period_key = _resolved_fact_period_key(record.get("period") if isinstance(record.get("period"), Mapping) else {})
        oracle = _companyfacts_oracle_confirmation(
            companyfacts=companyfacts,
            source=source,
            unit=unit,
            period_key=period_key,
            value=effective_value,
            decimals=record.get("decimals"),
            fiscal_year=fiscal_year,
        )
        if oracle is True:
            status = "projected_oracle_confirmed"
        elif oracle == "oracle_absent":
            status = "projected_oracle_absent"
        else:
            status = "projected_unconfirmed"
        return {
            "canonical_id": concept.canonical_id,
            "basis": concept.basis,
            "requested_basis": requested_basis or concept.basis,
            "statement": concept.statement,
            "status": status,
            "source_qname": source.qname,
            "period_class": PERIOD_CLASS,
            "oracle_confirmed": oracle,
            "mapping_method": mapping_method,
            "mapping_confidence": MAPPING_CONFIDENCE,
            "unit_class": _unit_class(unit),
            "resolved_fact_id": resolved_fact_id,
            "sidecar_receipt_id": shared_provenance["sidecar_receipt_id"],
            "sidecar_receipt_hash": shared_provenance["sidecar_receipt_hash"],
            "value_store_hash": shared_provenance["value_store_hash"],
            "dataset_version_id": shared_provenance["dataset_version_id"],
            "provenance_complete": True,
            "_resolution_key": concept.key if requested_basis is None else f"{concept.canonical_id}[{requested_basis}]",
            "_value": effective_value,
            "_unit": unit,
        }
    return {
        "canonical_id": concept.canonical_id,
        "basis": concept.basis,
        "requested_basis": requested_basis or concept.basis,
        "statement": concept.statement,
        "status": "legitimately_absent",
        "source_qname": None,
        "period_class": PERIOD_CLASS,
        "oracle_confirmed": "oracle_absent",
        "mapping_method": mapping_method,
        "mapping_confidence": MAPPING_CONFIDENCE,
        "absence_reason": "no_reviewed_sidecar_fy_source_fact",
        "provenance_complete": False,
        "_resolution_key": concept.key if requested_basis is None else f"{concept.canonical_id}[{requested_basis}]",
    }


def _apply_noncurrent_derivations(items: list[dict[str, Any]], *, projection: bool) -> None:
    by_key = {
        str(item.get("_resolution_key") or ""): item
        for item in items
        if isinstance(item, Mapping)
    }
    for target_key, total_key, current_key in _NONCURRENT_DERIVATIONS:
        target = by_key.get(target_key)
        total = by_key.get(total_key)
        current = by_key.get(current_key)
        if target is None or target.get("status") != "legitimately_absent":
            continue
        if not _derivation_source_ready(total) or not _derivation_source_ready(current):
            continue
        if str(total.get("_unit") or "") != str(current.get("_unit") or ""):
            continue
        derived = _derived_noncurrent_item(
            target=target,
            total=total,
            current=current,
            projection=projection,
        )
        index = items.index(target)
        items[index] = derived
        by_key[target_key] = derived


def _derivation_source_ready(item: Mapping[str, Any] | None) -> bool:
    if not isinstance(item, Mapping) or item.get("status") == "legitimately_absent":
        return False
    return (
        isinstance(item.get("_value"), Decimal)
        and bool(str(item.get("_unit") or ""))
        and bool(str(item.get("resolved_fact_id") or ""))
    )


def _derived_noncurrent_item(
    *,
    target: Mapping[str, Any],
    total: Mapping[str, Any],
    current: Mapping[str, Any],
    projection: bool,
) -> dict[str, Any]:
    total_value = total["_value"]
    current_value = current["_value"]
    derived_value = total_value - current_value
    source_fact_ids = [
        str(total.get("resolved_fact_id") or ""),
        str(current.get("resolved_fact_id") or ""),
    ]
    item: dict[str, Any] = {
        "canonical_id": target.get("canonical_id"),
        "basis": target.get("basis"),
        "requested_basis": target.get("requested_basis"),
        "statement": target.get("statement"),
        "status": "derived",
        "source_qname": None,
        "period_class": PERIOD_CLASS,
        "mapping_method": "derived_total_minus_current",
        "mapping_confidence": MAPPING_CONFIDENCE,
        "unit_class": _unit_class(str(total.get("_unit") or "")),
        "derived_from_concepts": [
            str(total.get("_resolution_key") or ""),
            str(current.get("_resolution_key") or ""),
        ],
        "derived_from_resolved_fact_ids": source_fact_ids,
        "_resolution_key": target.get("_resolution_key"),
        "_value": derived_value,
        "_unit": str(total.get("_unit") or ""),
    }
    if projection:
        item.update(
            {
                "oracle_confirmed": _derived_oracle_confirmation(total, current),
                "sidecar_receipt_id": total.get("sidecar_receipt_id"),
                "sidecar_receipt_hash": total.get("sidecar_receipt_hash"),
                "value_store_hash": total.get("value_store_hash"),
                "dataset_version_id": total.get("dataset_version_id"),
                "provenance_complete": _derived_projection_provenance_complete(total, current),
            }
        )
    else:
        item["inline_confirmed"] = total.get("inline_confirmed") is True and current.get("inline_confirmed") is True
    return item


def _derived_oracle_confirmation(total: Mapping[str, Any], current: Mapping[str, Any]) -> bool | str:
    states = {total.get("oracle_confirmed"), current.get("oracle_confirmed")}
    if states == {True}:
        return True
    if False in states:
        return False
    return "oracle_absent"


def _derived_projection_provenance_complete(total: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    fields = ("sidecar_receipt_id", "sidecar_receipt_hash", "value_store_hash", "dataset_version_id")
    return (
        bool(total.get("resolved_fact_id"))
        and bool(current.get("resolved_fact_id"))
        and all(str(total.get(field) or "").strip() for field in fields)
        and all(str(current.get(field) or "").strip() for field in fields)
        and all(str(total.get(field) or "") == str(current.get(field) or "") for field in fields)
    )


def _sidecar_fy_record(
    *,
    sidecar_records: Sequence[Mapping[str, Any]],
    source: SourceConcept,
    fy_period: Mapping[str, Any],
    statement: str,
) -> Mapping[str, Any] | None:
    instant_key = fy_period.get("instant_period_key")
    duration_key = fy_period.get("duration_period_key")
    preferred = duration_key if statement != "balance" else instant_key
    fallback = instant_key if statement != "balance" else duration_key
    for period_key in (preferred, fallback):
        if not isinstance(period_key, tuple):
            continue
        matches = [
            record
            for record in sidecar_records
            if _is_standard_non_dimensional_record(record)
            and _record_matches_source(record, source)
            and _resolved_fact_period_key(record.get("period") if isinstance(record.get("period"), Mapping) else {}) == period_key
        ]
        if matches:
            return sorted(matches, key=lambda item: int(item.get("source_order") or 0))[0]
    return None


def _companyfacts_oracle_confirmation(
    *,
    companyfacts: Mapping[str, Any],
    source: SourceConcept,
    unit: str,
    period_key: tuple[str, ...],
    value: Decimal,
    decimals: Any,
    fiscal_year: int | str | None,
) -> bool | str:
    concept = ((companyfacts.get(source.taxonomy) or {}).get(source.local_name) or {})
    units = concept.get("units") if isinstance(concept, Mapping) else {}
    facts = (units or {}).get(unit)
    if not isinstance(facts, Sequence) or isinstance(facts, (str, bytes)):
        return "oracle_absent"
    period_seen = False
    tolerance = _decimals_tolerance(decimals)
    for fact in facts:
        if not isinstance(fact, Mapping) or fact.get("fp") != PERIOD_CLASS:
            continue
        if fiscal_year is not None and str(fact.get("fy") or "") != str(fiscal_year):
            continue
        if _companyfacts_period_key(fact) != period_key:
            continue
        period_seen = True
        candidate = _decimal(fact.get("val"))
        if candidate is not None and abs(candidate - value) <= tolerance:
            return True
    return False if period_seen else "oracle_absent"


def _is_standard_non_dimensional_record(record: Mapping[str, Any]) -> bool:
    concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
    if concept.get("standard") is not True:
        return False
    dimensions = record.get("dimensions") if isinstance(record.get("dimensions"), Mapping) else {}
    return not list(dimensions.get("explicit") or []) and not list(dimensions.get("typed") or [])


def _record_matches_source(record: Mapping[str, Any], source: SourceConcept) -> bool:
    concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
    return (
        str(concept.get("local_name") or "") == source.local_name
        and taxonomy_from_namespace(str(concept.get("namespace") or "")) == source.taxonomy
    )


def _blocked_projection(
    *,
    primary_taxonomy: str,
    reason: str,
    evidence: Mapping[str, Any],
    blocking_reasons: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    reasons = list(blocking_reasons or [{"reason": reason, "evidence": dict(evidence)}])
    return {
        "status": "canonical_projection_blocked",
        "primary_taxonomy": primary_taxonomy,
        "period_class": PERIOD_CLASS,
        "defined_count": len(CANONICAL_CONCEPTS),
        "projected_count": 0,
        "oracle_confirmed_count": 0,
        "oracle_absent_count": 0,
        "projected_unconfirmed_count": 0,
        "legitimately_absent_count": 0,
        "provenance_complete_count": 0,
        "concepts": [],
        "statement_identity_residuals": [],
        "blocking_reasons": reasons,
    }


def _blocked_concept_projection(
    *,
    concept: CanonicalConcept,
    requested_basis: str | None,
    reason: str,
    source_qname: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "canonical_id": concept.canonical_id,
        "basis": concept.basis,
        "requested_basis": requested_basis or concept.basis,
        "_blocked_reason": {
            "reason": reason,
            "canonical_id": concept.canonical_id,
            "basis": concept.basis,
            "requested_basis": requested_basis or concept.basis,
            "source_qname": source_qname,
            "evidence": dict(evidence or {}),
        },
    }


def _companyfacts_fy_fact(
    companyfacts: Mapping[str, Any],
    source: SourceConcept,
    *,
    fiscal_year: int | str | None,
) -> dict[str, Any] | None:
    concept = ((companyfacts.get(source.taxonomy) or {}).get(source.local_name) or {})
    units = concept.get("units") if isinstance(concept, Mapping) else {}
    best: dict[str, Any] | None = None
    for unit_name, facts in (units or {}).items():
        if not isinstance(facts, Sequence) or isinstance(facts, (str, bytes)):
            continue
        for fact in facts:
            if not isinstance(fact, Mapping) or fact.get("fp") != PERIOD_CLASS:
                continue
            if fiscal_year is not None and str(fact.get("fy") or "") != str(fiscal_year):
                continue
            value = _decimal(fact.get("val"))
            if value is None:
                continue
            period_key = _companyfacts_period_key(fact)
            if period_key is None:
                continue
            candidate = {
                "value": value,
                "unit": str(unit_name or ""),
                "period_key": period_key,
                "fy": str(fact.get("fy") or ""),
            }
            if best is None or (candidate["fy"], candidate["period_key"]) > (best["fy"], best["period_key"]):
                best = candidate
    return best


def _inline_confirmation(
    *,
    sidecar_records: Sequence[Mapping[str, Any]],
    value_by_fact_id: Mapping[str, Mapping[str, Any]],
    source: SourceConcept,
    unit: str,
    period_key: tuple[str, ...],
    value: Decimal,
) -> dict[str, Any]:
    for record in sidecar_records:
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        if str(concept.get("local_name") or "") != source.local_name:
            continue
        if taxonomy_from_namespace(str(concept.get("namespace") or "")) != source.taxonomy:
            continue
        dimensions = record.get("dimensions") if isinstance(record.get("dimensions"), Mapping) else {}
        if list(dimensions.get("explicit") or []) or list(dimensions.get("typed") or []):
            continue
        if _unit_name(record.get("unit") if isinstance(record.get("unit"), Mapping) else {}) != unit:
            continue
        if _resolved_fact_period_key(record.get("period") if isinstance(record.get("period"), Mapping) else {}) != period_key:
            continue
        value_record = value_by_fact_id.get(str(record.get("resolved_fact_id") or ""))
        if value_record is None:
            continue
        effective = _decimal(value_record.get("effective_value"))
        if effective is not None and effective == value:
            return {
                "confirmed": True,
                "resolved_fact_id": str(record.get("resolved_fact_id") or ""),
                "effective_value": effective,
            }
    return {"confirmed": False, "resolved_fact_id": None, "effective_value": None}


def _ordered_sources(concept: CanonicalConcept, primary_taxonomy: str) -> tuple[SourceConcept, ...]:
    return tuple(sorted(concept.sources, key=lambda source: 0 if source.taxonomy == primary_taxonomy else 1))


def _parent_fallback(concept: CanonicalConcept) -> CanonicalConcept | None:
    return _CONCEPT_BY_KEY.get(f"{concept.canonical_id}[parent]")


def _companyfacts_period_key(fact: Mapping[str, Any]) -> tuple[str, ...] | None:
    end = str(fact.get("end") or "")
    start = str(fact.get("start") or "")
    if not end:
        return None
    if start:
        return ("d", start, end)
    return ("i", end)


def _resolved_fact_period_key(period: Mapping[str, Any]) -> tuple[str, ...]:
    period_type = str(period.get("type") or "")
    if period_type == "instant":
        return ("i", str(period.get("instant") or ""))
    if period_type == "duration":
        return ("d", str(period.get("start") or ""), str(period.get("end") or ""))
    return ("?",)


def _unit_name(unit: Mapping[str, Any]) -> str:
    denominator = list(unit.get("denominator") or [])
    numerator = list(unit.get("numerator") or [])
    if denominator and numerator:
        return "/".join((_unit_measure_name(numerator[0]), _unit_measure_name(denominator[0])))
    currency = str(unit.get("currency") or "")
    if currency:
        return currency.split(":")[-1]
    measures = list(unit.get("measures") or [])
    return _unit_measure_name(measures[0]) if measures else "unitless"


def _unit_measure_name(value: Any) -> str:
    return str(value or "").split(":")[-1]


def _unit_class(unit_name: str) -> str:
    if "/" in unit_name:
        return "divided_unit"
    if unit_name and unit_name != "unitless":
        return "single_unit"
    return "unitless"


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _decimals_tolerance(decimals: Any) -> Decimal:
    if decimals is None or decimals == "":
        return Decimal("0")
    text = str(decimals).strip()
    if text.upper() in {"INF", "INFINITY"}:
        return Decimal("0")
    try:
        return Decimal(1).scaleb(-int(text))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _identity(
    identity_id: str,
    resolved: Mapping[str, Mapping[str, Any]],
    keys: tuple[str, ...],
    residual_fn: Any,
    scale_key: str,
) -> dict[str, Any]:
    missing = [key for key in keys if key not in resolved]
    if missing:
        return {"identity_id": identity_id, "status": "not_evaluated", "missing_concepts": missing}
    if len({resolved[key].get("_unit") for key in keys}) != 1:
        return {"identity_id": identity_id, "status": "not_evaluated", "reason": "unit_classes_not_aligned"}
    values = [resolved[key]["_value"] for key in keys]
    residual = residual_fn(values)
    scale = resolved[scale_key]["_value"]
    relative = _relative_magnitude(residual, scale)
    return {
        "identity_id": identity_id,
        "status": "evaluated",
        "concepts": list(keys),
        "residual_abs": str(abs(residual)),
        "relative_magnitude": f"{relative:.2E}",
        "within_tolerance": relative <= IDENTITY_TOLERANCE,
    }


def _derived_liabilities_identity(resolved: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    keys = ("TotalAssets[total]", "Equity[total]", "CurrentLiabilities[total]", "NoncurrentLiabilities[total]")
    missing = [key for key in keys if key not in resolved]
    if missing or "TotalLiabilities[total]" in resolved:
        return {
            "identity_id": "derived_total_liabilities_equals_assets_minus_equity_and_split",
            "status": "not_evaluated",
            "missing_concepts": missing,
            "direct_total_liabilities_present": "TotalLiabilities[total]" in resolved,
        }
    if len({resolved[key].get("_unit") for key in keys}) != 1:
        return {
            "identity_id": "derived_total_liabilities_equals_assets_minus_equity_and_split",
            "status": "not_evaluated",
            "reason": "unit_classes_not_aligned",
        }
    derived = resolved["TotalAssets[total]"]["_value"] - resolved["Equity[total]"]["_value"]
    residual = (
        resolved["CurrentLiabilities[total]"]["_value"]
        + resolved["NoncurrentLiabilities[total]"]["_value"]
        - derived
    )
    relative = _relative_magnitude(residual, derived)
    return {
        "identity_id": "derived_total_liabilities_equals_assets_minus_equity_and_split",
        "status": "evaluated",
        "concepts": list(keys),
        "residual_abs": str(abs(residual)),
        "relative_magnitude": f"{relative:.2E}",
        "within_tolerance": relative <= IDENTITY_TOLERANCE,
    }


def _relative_magnitude(residual: Decimal, scale: Decimal) -> Decimal:
    if scale == 0:
        return Decimal("0") if residual == 0 else Decimal("1")
    return abs(residual / scale)


def _public_resolution(item: Mapping[str, Any]) -> dict[str, Any]:
    public = {
        "canonical_id": item.get("canonical_id"),
        "basis": item.get("basis"),
        "requested_basis": item.get("requested_basis"),
        "statement": item.get("statement"),
        "status": item.get("status"),
        "source_qname": item.get("source_qname"),
        "period_class": item.get("period_class"),
        "inline_confirmed": item.get("inline_confirmed"),
        "mapping_method": item.get("mapping_method"),
        "mapping_confidence": item.get("mapping_confidence"),
    }
    if item.get("unit_class") is not None:
        public["unit_class"] = item.get("unit_class")
    if item.get("derived_from_concepts") is not None:
        public["derived_from_concepts"] = item.get("derived_from_concepts")
    if item.get("absence_reason") is not None:
        public["absence_reason"] = item.get("absence_reason")
    return public


def _public_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    public = {
        "canonical_id": item.get("canonical_id"),
        "basis": item.get("basis"),
        "requested_basis": item.get("requested_basis"),
        "statement": item.get("statement"),
        "status": item.get("status"),
        "source_qname": item.get("source_qname"),
        "period_class": item.get("period_class"),
        "oracle_confirmed": item.get("oracle_confirmed"),
        "mapping_method": item.get("mapping_method"),
        "mapping_confidence": item.get("mapping_confidence"),
        "provenance_complete": item.get("provenance_complete") is True,
    }
    if item.get("unit_class") is not None:
        public["unit_class"] = item.get("unit_class")
    if item.get("derived_from_concepts") is not None:
        public["derived_from_concepts"] = item.get("derived_from_concepts")
    if item.get("absence_reason") is not None:
        public["absence_reason"] = item.get("absence_reason")
    return public


def _public_provenance_presence(items: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    projected = [item for item in items if item.get("status") != "legitimately_absent"]
    return {
        "resolved_fact_id_present_for_all_projected": all(
            _projected_resolved_fact_provenance_present(item) for item in projected
        ),
        "sidecar_receipt_present_for_all_projected": all(
            bool(item.get("sidecar_receipt_id")) and bool(item.get("sidecar_receipt_hash"))
            for item in projected
        ),
        "value_store_hash_present_for_all_projected": all(bool(item.get("value_store_hash")) for item in projected),
        "dataset_version_present_for_all_projected": all(bool(item.get("dataset_version_id")) for item in projected),
    }


def _projected_resolved_fact_provenance_present(item: Mapping[str, Any]) -> bool:
    if bool(item.get("resolved_fact_id")):
        return True
    source_ids = item.get("derived_from_resolved_fact_ids")
    return (
        item.get("status") == "derived"
        and isinstance(source_ids, Sequence)
        and not isinstance(source_ids, (str, bytes))
        and len(source_ids) == 2
        and all(bool(str(source_id or "").strip()) for source_id in source_ids)
    )


def _projection_non_goals() -> dict[str, bool]:
    return {
        "default_on_readiness_claimed": False,
        "production_readiness_claimed": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_currency_conversion_claimed": False,
        "statement_assembly_claimed": False,
        "linkbase_relationships_required_or_consumed": False,
        "live_network_or_arelle_required": False,
        "value_reveal_performed": False,
    }


def _public_identity(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity_id": item.get("identity_id"),
        "status": item.get("status"),
        "concepts": item.get("concepts"),
        "residual_abs": item.get("residual_abs"),
        "relative_magnitude": item.get("relative_magnitude"),
        "within_tolerance": item.get("within_tolerance"),
    }
