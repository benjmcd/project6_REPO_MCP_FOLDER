from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from collections import defaultdict
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import L3SecXbrlProjectionFact, L3SecXbrlProjectionSet
from app.models.models import (
    L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
    L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
)
from app.services.layer3_utils import json_clone, stable_hash


PROJECTION_SET_SCHEMA_ID = "layer3.sec_xbrl_projection_set.v1"
ALLOWED_STATEMENTS = {"income", "balance", "cashflow"}
RAW_VALUE_KEYS = {"_value", "value", "effective_value", "amount"}
RAW_AUTHORITY_KEYS = {
    "resolved_fact_id",
    "resolved_fact_ids",
    "derived_from_resolved_fact_ids",
    "raw_resolved_fact_authority",
    "raw_resolved_fact_authorities",
    "cik",
    "cik_or_filer_ref",
    "filer_or_cik",
    "accession",
    "accession_number",
    "company_name",
    "issuer_name",
    "registrant",
    "registrant_name",
    "ticker",
    "contact",
    "user_agent",
    "local_path",
    "raw_path",
    "storage_dir",
    "storage_root",
    "sec_url",
}
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
RAW_PERIOD_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class SecXbrlProjectionPersistenceError(ValueError):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "blocked",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": dict(self.details),
            },
        }


def materialize_redacted_projection_set(
    db: Session,
    *,
    client_request_id: str,
    projection: Mapping[str, Any],
    source_report_schema_id: str,
    source_report_hash: str,
) -> dict[str, Any]:
    request_id = _required_text(client_request_id, "client_request_id")
    report_schema_id = _required_text(source_report_schema_id, "source_report_schema_id")
    report_hash = _required_hash(source_report_hash, "source_report_hash")
    periods = _normalise_periods(projection)
    facts = _redacted_facts_from_periods(periods)
    if not facts:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_empty_projection",
            "SEC XBRL projection persistence requires at least one redacted fact row.",
        )

    sidecar_hash = _single_required_hash(facts, "sidecar_receipt_hash")
    value_hash = _single_required_hash(facts, "value_store_hash")
    dataset_version_id = _single_optional_text(facts, "dataset_version_id")
    envelope = {
        "schema_id": PROJECTION_SET_SCHEMA_ID,
        "source_report_schema_id": report_schema_id,
        "source_report_hash": report_hash,
        "dataset_version_id": dataset_version_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_store_hash": value_hash,
        "redaction_policy": L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
        "sector_family_presence": _sector_family_presence(projection=projection, periods=periods),
        "period_refs": _period_refs(periods),
        "facts": facts,
    }
    _reject_raw_or_local_authority(envelope)
    projection_basis_hash = stable_hash(envelope)

    existing_by_request = (
        db.query(L3SecXbrlProjectionSet)
        .filter(L3SecXbrlProjectionSet.client_request_id == request_id)
        .one_or_none()
    )
    existing_by_basis = (
        db.query(L3SecXbrlProjectionSet)
        .filter(L3SecXbrlProjectionSet.projection_basis_hash == projection_basis_hash)
        .one_or_none()
    )
    if existing_by_request is not None:
        if existing_by_request.projection_basis_hash != projection_basis_hash:
            raise SecXbrlProjectionPersistenceError(
                "sec_xbrl_projection_persistence_client_request_conflict",
                "client_request_id already materialized a different SEC XBRL projection basis.",
                details={"client_request_id": request_id},
            )
        return _response(existing_by_request, idempotent_replay=True)
    if existing_by_basis is not None:
        return _response(existing_by_basis, idempotent_replay=True)

    set_row = L3SecXbrlProjectionSet(
        client_request_id=request_id,
        projection_basis_hash=projection_basis_hash,
        projection_schema_id=PROJECTION_SET_SCHEMA_ID,
        source_report_schema_id=report_schema_id,
        source_report_hash=report_hash,
        dataset_version_id=dataset_version_id,
        sidecar_receipt_hash=sidecar_hash,
        value_store_hash=value_hash,
        sector_family_presence_json=json_clone(envelope["sector_family_presence"]),
        period_refs_json=json_clone(envelope["period_refs"]),
        projection_summary_json=_projection_summary(periods=periods, facts=facts),
        redaction_policy=L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
        status=L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
    )
    try:
        db.add(set_row)
        db.flush()
        for fact in facts:
            db.add(
                L3SecXbrlProjectionFact(
                    sec_xbrl_projection_set_id=set_row.sec_xbrl_projection_set_id,
                    period_ref=fact["period_ref"],
                    period_index=fact["period_index"],
                    statement=fact["statement"],
                    statement_row_index=fact["statement_row_index"],
                    canonical_id=fact["canonical_id"],
                    basis=fact["basis"],
                    requested_basis=fact["requested_basis"],
                    family=fact["family"],
                    source_qname=fact.get("source_qname"),
                    status=fact["status"],
                    oracle_confirmed=fact["oracle_confirmed"],
                    mapping_method=fact.get("mapping_method"),
                    mapping_confidence=fact.get("mapping_confidence"),
                    unit_class=fact.get("unit_class"),
                    provenance_complete=fact["provenance_complete"],
                    value_redacted=True,
                    resolved_fact_provenance_present=fact["resolved_fact_provenance_present"],
                    sidecar_receipt_hash=fact["sidecar_receipt_hash"],
                    value_store_hash=fact["value_store_hash"],
                    derived_from_concepts_json=json_clone(fact["derived_from_concepts"]),
                )
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_integrity_error",
            "SEC XBRL projection persistence failed without admitting partial projection rows.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(set_row)
    return _response(set_row, idempotent_replay=False)


def _normalise_periods(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    status = str(projection.get("status") or "")
    if status == "canonical_multi_period_projection_ready":
        periods = projection.get("periods")
        if not isinstance(periods, Sequence) or isinstance(periods, (str, bytes)):
            raise SecXbrlProjectionPersistenceError(
                "sec_xbrl_projection_persistence_periods_missing",
                "Multi-period projection persistence requires a period list.",
            )
        return [_normalise_period(item, fallback_index=index) for index, item in enumerate(periods, start=1)]
    if status == "canonical_projection_ready":
        return [
            {
                "period_ref": _required_text(projection.get("period_ref") or "fy-period-1", "period_ref"),
                "period_index": 1,
                "projection": dict(projection),
            }
        ]
    raise SecXbrlProjectionPersistenceError(
        "sec_xbrl_projection_persistence_projection_not_ready",
        "Only ready redacted canonical projection output can be persisted.",
        details={"status": status},
    )


def _normalise_period(item: Any, *, fallback_index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_period_invalid",
            "Each projection period must be an object.",
        )
    projection = item.get("projection")
    if not isinstance(projection, Mapping):
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_period_projection_missing",
            "Each projection period must carry a projection object.",
        )
    if projection.get("status") != "canonical_projection_ready":
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_period_projection_not_ready",
            "Each projection period must carry ready canonical projection output.",
            details={"status": projection.get("status")},
        )
    return {
        "period_ref": _required_text(item.get("period_ref") or f"fy-period-{fallback_index}", "period_ref"),
        "period_index": _positive_int(item.get("period_index") or fallback_index, "period_index"),
        "projection": dict(projection),
    }


def _redacted_facts_from_periods(periods: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    statement_counts_by_period: dict[tuple[str, str], int] = defaultdict(int)
    for period in periods:
        period_ref = _safe_public_ref(period["period_ref"], "period_ref")
        period_index = _positive_int(period["period_index"], "period_index")
        projection = period["projection"]
        items = projection.get("concepts") or projection.get("projection_items") or []
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise SecXbrlProjectionPersistenceError(
                "sec_xbrl_projection_persistence_concepts_invalid",
                "Projection concepts must be a list.",
            )
        for item in items:
            if not isinstance(item, Mapping) or item.get("status") == "legitimately_absent":
                continue
            _reject_raw_or_local_authority(item)
            statement = _statement(item.get("statement"))
            key = (period_ref, statement)
            statement_counts_by_period[key] += 1
            facts.append(
                {
                    "period_ref": period_ref,
                    "period_index": period_index,
                    "statement": statement,
                    "statement_row_index": statement_counts_by_period[key],
                    "canonical_id": _required_text(item.get("canonical_id"), "canonical_id"),
                    "basis": _required_text(item.get("basis"), "basis"),
                    "requested_basis": _required_text(
                        item.get("requested_basis") or item.get("basis"),
                        "requested_basis",
                    ),
                    "family": _required_text(item.get("family") or "universal", "family"),
                    "source_qname": _optional_text(item.get("source_qname")),
                    "status": _required_text(item.get("status"), "status"),
                    "oracle_confirmed": _oracle_value(item.get("oracle_confirmed")),
                    "mapping_method": _optional_text(item.get("mapping_method")),
                    "mapping_confidence": _optional_text(item.get("mapping_confidence")),
                    "unit_class": _optional_text(item.get("unit_class")),
                    "provenance_complete": item.get("provenance_complete") is True,
                    "value_redacted": _required_true(item.get("value_redacted"), "value_redacted"),
                    "resolved_fact_provenance_present": _required_bool(
                        item.get("resolved_fact_provenance_present"),
                        "resolved_fact_provenance_present",
                    ),
                    "sidecar_receipt_hash": _required_hash(
                        item.get("sidecar_receipt_hash")
                        or projection.get("sidecar_receipt_hash"),
                        "sidecar_receipt_hash",
                    ),
                    "value_store_hash": _required_hash(
                        item.get("value_store_hash")
                        or projection.get("value_store_hash"),
                        "value_store_hash",
                    ),
                    "dataset_version_id": _optional_text(
                        item.get("dataset_version_id") or projection.get("dataset_version_id")
                    ),
                    "derived_from_concepts": _public_concept_list(item.get("derived_from_concepts")),
                }
            )
    return facts


def _projection_summary(*, periods: Sequence[Mapping[str, Any]], facts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    statements = defaultdict(int)
    families = defaultdict(int)
    for fact in facts:
        statements[str(fact["statement"])] += 1
        families[str(fact["family"])] += 1
    return {
        "period_count": len(periods),
        "fact_count": len(facts),
        "statement_counts": dict(sorted(statements.items())),
        "family_counts": dict(sorted(families.items())),
        "redaction_policy": L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
        "value_redacted_count": sum(1 for item in facts if item.get("value_redacted") is True),
    }


def _response(row: L3SecXbrlProjectionSet, *, idempotent_replay: bool) -> dict[str, Any]:
    fact_count = len(row.facts)
    return {
        "status": L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
        "schema_id": PROJECTION_SET_SCHEMA_ID,
        "sec_xbrl_projection_set_id": row.sec_xbrl_projection_set_id,
        "client_request_id": row.client_request_id,
        "projection_basis_hash": row.projection_basis_hash,
        "fact_count": fact_count,
        "redaction_policy": row.redaction_policy,
        "idempotent_replay": idempotent_replay,
        "runtime_default_enabled": False,
        "value_reveal_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
    }


def _period_refs(periods: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "period_ref": str(period["period_ref"]),
            "period_index": int(period["period_index"]),
        }
        for period in periods
    ]


def _sector_family_presence(*, projection: Mapping[str, Any], periods: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    presence = projection.get("sector_family_presence")
    if isinstance(presence, Mapping):
        return json_clone(dict(presence))
    for period in periods:
        period_projection = period.get("projection")
        if isinstance(period_projection, Mapping) and isinstance(period_projection.get("sector_family_presence"), Mapping):
            return json_clone(dict(period_projection["sector_family_presence"]))
    return {}


def _single_required_hash(facts: Sequence[Mapping[str, Any]], field: str) -> str:
    values = sorted({str(item.get(field) or "") for item in facts if str(item.get(field) or "")})
    if len(values) != 1:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_provenance_hash_ambiguous",
            f"Projection persistence requires exactly one {field}.",
            details={field: values},
        )
    return _required_hash(values[0], field)


def _single_optional_text(facts: Sequence[Mapping[str, Any]], field: str) -> str | None:
    values = sorted({str(item.get(field) or "") for item in facts if str(item.get(field) or "")})
    if len(values) > 1:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_dataset_version_ambiguous",
            "Projection persistence requires one dataset_version_id when supplied.",
            details={field: values},
        )
    return values[0] if values else None


def _statement(value: Any) -> str:
    statement = _required_text(value, "statement")
    if statement not in ALLOWED_STATEMENTS:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_statement_not_admitted",
            "Projection fact statement is not admitted for SEC XBRL persistence.",
            details={"statement": statement},
        )
    return statement


def _oracle_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = _required_text(value, "oracle_confirmed")
    if text != "oracle_absent":
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_oracle_state_invalid",
            "Projection fact oracle state is not admitted.",
            details={"oracle_confirmed": text},
        )
    return text


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_required_field_missing",
            f"SEC XBRL projection persistence requires {field}.",
            details={"field": field},
        )
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_hash(value: Any, field: str) -> str:
    text = _required_text(value, field).lower()
    if not HASH_RE.fullmatch(text):
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_hash_invalid",
            f"SEC XBRL projection persistence requires a 64-character lowercase hex hash for {field}.",
            details={"field": field},
        )
    return text


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_integer_invalid",
            f"SEC XBRL projection persistence requires an integer {field}.",
            details={"field": field},
        ) from exc
    if number <= 0:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_integer_invalid",
            f"SEC XBRL projection persistence requires a positive {field}.",
            details={"field": field},
        )
    return number


def _required_true(value: Any, field: str) -> bool:
    if value is not True:
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_redaction_required",
            f"SEC XBRL projection persistence requires {field}=true.",
            details={"field": field},
        )
    return True


def _required_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_boolean_required",
            f"SEC XBRL projection persistence requires boolean {field}.",
            details={"field": field},
        )
    return value


def _safe_public_ref(value: Any, field: str) -> str:
    text = _required_text(value, field)
    _reject_raw_or_local_authority(text)
    return text


def _public_concept_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SecXbrlProjectionPersistenceError(
            "sec_xbrl_projection_persistence_concept_list_invalid",
            "Derived concept references must be a list of public concept ids.",
        )
    concepts = []
    for item in value:
        concept = _required_text(item, "derived_from_concepts")
        _reject_raw_or_local_authority(concept)
        concepts.append(concept)
    return concepts


def _reject_raw_or_local_authority(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_match = key_text.strip().lower()
            if key_match in RAW_VALUE_KEYS or key_match in RAW_AUTHORITY_KEYS:
                if item is not None:
                    raise SecXbrlProjectionPersistenceError(
                        "sec_xbrl_projection_persistence_raw_authority_not_admitted",
                        "SEC XBRL projection persistence cannot store raw values or raw authority identifiers.",
                        details={"field": key_text},
                    )
            _reject_raw_or_local_authority(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_raw_or_local_authority(item)
        return
    if isinstance(value, str):
        if (
            ACCESSION_RE.search(value)
            or SEC_URL_RE.search(value)
            or WINDOWS_ABS_PATH_RE.search(value)
            or RAW_PERIOD_DATE_RE.search(value)
        ):
            raise SecXbrlProjectionPersistenceError(
                "sec_xbrl_projection_persistence_raw_reference_not_admitted",
                "SEC XBRL projection persistence cannot store raw accession, SEC URL, period date, or local path strings.",
            )
