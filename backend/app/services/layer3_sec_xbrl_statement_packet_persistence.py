from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    L3SecXbrlProjectionFact,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketRow,
    L3SecXbrlStatementPacketSet,
    L3SecXbrlStatementPacketStatement,
)
from app.models.models import (
    L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
    L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
)
from app.services.layer3_sec_xbrl_statement_assembly import STATEMENT_ASSEMBLY_SCHEMA_ID
from app.services.layer3_utils import json_clone, stable_hash


PACKET_SET_SCHEMA_ID = STATEMENT_ASSEMBLY_SCHEMA_ID
ALLOWED_STATEMENTS = ("income", "balance", "cashflow")
RAW_VALUE_KEYS = {"_value", "value", "effective_value", "amount", "lexical_value"}
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
RESIDUAL_MAGNITUDE_KEYS = {"relative_magnitude", "residual_abs", "residual", "magnitude"}
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
LOCAL_REF_RE = re.compile(
    r"(?i)(?:"
    r"file://"
    r"|\\\\[^\\/]+[\\/]"
    r"|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$)"
    r")"
)
RAW_PERIOD_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
ORGANIZATION_CONTRACT_BOOL_FIELDS = {
    "contract_passed",
    "contract_b_authoritative_organization",
    "contract_every_fact_id_bound",
    "contract_derived_inputs_bound_and_corroborated",
}
ORGANIZATION_CONTRACT_COUNT_FIELDS = {
    "normalized_fact_count",
    "organized_count",
    "unjoined_count",
    "a_divergent_count",
    "a_role_unknown_count",
}
ORGANIZATION_CONTRACT_KEYS = ORGANIZATION_CONTRACT_BOOL_FIELDS | ORGANIZATION_CONTRACT_COUNT_FIELDS


class SecXbrlStatementPacketPersistenceError(ValueError):
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


def materialize_redacted_statement_packet(
    db: Session,
    *,
    client_request_id: str,
    sec_xbrl_projection_set_id: str,
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    request_id = _required_text(client_request_id, "client_request_id")
    _reject_raw_or_local_authority(request_id)
    projection_set_id = _required_text(sec_xbrl_projection_set_id, "sec_xbrl_projection_set_id")
    projection_set = (
        db.query(L3SecXbrlProjectionSet)
        .filter(L3SecXbrlProjectionSet.sec_xbrl_projection_set_id == projection_set_id)
        .one_or_none()
    )
    if projection_set is None:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_projection_set_missing",
            "Statement packet persistence requires an existing persisted SEC XBRL projection set.",
            details={"sec_xbrl_projection_set_id": projection_set_id},
        )
    if not isinstance(packet, Mapping):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_packet_invalid",
            "Statement packet persistence requires a redacted statement packet object.",
        )
    _reject_raw_or_local_authority(packet)
    _validate_packet_header(packet)

    facts = list(projection_set.facts)
    if not facts:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_projection_facts_empty",
            "Statement packet persistence requires persisted projection facts.",
        )
    single_period = _single_projection_period(facts)
    statements = _normalise_statements(packet, facts=facts, single_period=single_period)
    rows = [row for statement in statements for row in statement["rows"]]
    if not rows:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_empty_packet",
            "Statement packet persistence requires at least one redacted review row.",
        )

    identity_rollup = _public_identity_rollup(packet.get("identity_rollup") or {})
    organization_contract = _public_organization_contract(packet.get("organization_contract") or {})
    packet_summary = _packet_summary(statements=statements, rows=rows)
    provenance_complete_count = sum(1 for row in rows if row["provenance_complete"] is True)
    review_ready = (
        packet.get("status") == "statement_assembly_ready"
        and len(rows) > 0
        and provenance_complete_count == len(rows)
        and identity_rollup["identity_residuals_within_tolerance"] is not False
    )
    _validate_packet_derived_contract(
        packet,
        packet_summary=packet_summary,
        provenance_complete_count=provenance_complete_count,
        review_ready=review_ready,
    )
    envelope = {
        "schema_id": PACKET_SET_SCHEMA_ID,
        "sec_xbrl_projection_set_id": projection_set.sec_xbrl_projection_set_id,
        "source_projection_basis_hash": projection_set.projection_basis_hash,
        "source_projection_schema_id": projection_set.projection_schema_id,
        "statement_organization_authority": _required_text(
            packet.get("statement_organization_authority"),
            "statement_organization_authority",
        ),
        "value_policy": L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
        "statement_count": packet_summary["statement_count"],
        "total_review_rows": packet_summary["total_review_rows"],
        "provenance_complete_count": provenance_complete_count,
        "review_exception_count": packet_summary["review_exception_count"],
        "review_ready": review_ready,
        "identity_rollup": identity_rollup,
        "organization_contract": organization_contract,
        "statements": statements,
    }
    _reject_raw_or_local_authority(envelope)
    packet_basis_hash = stable_hash(envelope)

    existing_by_request = (
        db.query(L3SecXbrlStatementPacketSet)
        .filter(L3SecXbrlStatementPacketSet.client_request_id == request_id)
        .one_or_none()
    )
    existing_by_basis = (
        db.query(L3SecXbrlStatementPacketSet)
        .filter(L3SecXbrlStatementPacketSet.packet_basis_hash == packet_basis_hash)
        .one_or_none()
    )
    if existing_by_request is not None:
        if existing_by_request.packet_basis_hash != packet_basis_hash:
            raise SecXbrlStatementPacketPersistenceError(
                "sec_xbrl_statement_packet_persistence_client_request_conflict",
                "client_request_id already materialized a different SEC XBRL statement packet basis.",
                details={"client_request_id": request_id},
            )
        return _response(existing_by_request, idempotent_replay=True)
    if existing_by_basis is not None:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_basis_replay_request_mismatch",
            "packet_basis_hash already belongs to a different client_request_id; replay the original request id.",
            details={
                "client_request_id": request_id,
                "original_client_request_id": existing_by_basis.client_request_id,
            },
        )

    packet_set = L3SecXbrlStatementPacketSet(
        sec_xbrl_projection_set_id=projection_set.sec_xbrl_projection_set_id,
        client_request_id=request_id,
        packet_basis_hash=packet_basis_hash,
        packet_schema_id=PACKET_SET_SCHEMA_ID,
        source_projection_basis_hash=projection_set.projection_basis_hash,
        source_projection_schema_id=projection_set.projection_schema_id,
        statement_organization_authority=envelope["statement_organization_authority"],
        value_policy=L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
        statement_count=envelope["statement_count"],
        total_review_rows=envelope["total_review_rows"],
        provenance_complete_count=envelope["provenance_complete_count"],
        review_exception_count=envelope["review_exception_count"],
        review_ready=envelope["review_ready"],
        identity_rollup_json=json_clone(identity_rollup),
        organization_contract_json=json_clone(organization_contract),
        packet_summary_json=json_clone(packet_summary),
        status=L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
    )
    try:
        db.add(packet_set)
        db.flush()
        for statement in statements:
            statement_row = L3SecXbrlStatementPacketStatement(
                sec_xbrl_statement_packet_set_id=packet_set.sec_xbrl_statement_packet_set_id,
                statement=statement["statement"],
                statement_index=statement["statement_index"],
                line_count=statement["line_count"],
                projected_count=statement["projected_count"],
                derived_count=statement["derived_count"],
                provenance_complete_count=statement["provenance_complete_count"],
                review_exception_count=statement["review_exception_count"],
                status_counts_json=json_clone(statement["status_counts"]),
                family_counts_json=json_clone(statement["family_counts"]),
            )
            db.add(statement_row)
            db.flush()
            for row in statement["rows"]:
                db.add(
                    L3SecXbrlStatementPacketRow(
                        sec_xbrl_statement_packet_statement_id=statement_row.sec_xbrl_statement_packet_statement_id,
                        sec_xbrl_projection_fact_id=row["sec_xbrl_projection_fact_id"],
                        statement=row["statement"],
                        statement_row_index=row["statement_row_index"],
                        source_index=row["source_index"],
                        period_ref=row["period_ref"],
                        period_index=row["period_index"],
                        canonical_id=row["canonical_id"],
                        basis=row["basis"],
                        requested_basis=row["requested_basis"],
                        family=row["family"],
                        source_qname=row.get("source_qname"),
                        status=row["status"],
                        oracle_confirmed=row["oracle_confirmed"],
                        mapping_method=row.get("mapping_method"),
                        mapping_confidence=row.get("mapping_confidence"),
                        unit_class=row.get("unit_class"),
                        provenance_complete=row["provenance_complete"],
                        value_redacted=True,
                        review_exception=row["review_exception"],
                        derived_from_concepts_json=json_clone(row["derived_from_concepts"]),
                    )
                )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_integrity_error",
            "SEC XBRL statement packet persistence failed without admitting partial packet rows.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(packet_set)
    return _response(packet_set, idempotent_replay=False)


def _validate_packet_header(packet: Mapping[str, Any]) -> None:
    if packet.get("schema_id") != PACKET_SET_SCHEMA_ID:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_schema_invalid",
            "Statement packet persistence requires the reviewable statement packet schema.",
            details={"schema_id": packet.get("schema_id")},
        )
    if packet.get("value_policy") != L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_value_policy_invalid",
            "Statement packet persistence requires redacted_no_values.",
            details={"value_policy": packet.get("value_policy")},
        )
    if packet.get("status") != "statement_assembly_ready":
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_packet_not_ready",
            "Only ready redacted statement packets can be persisted.",
            details={"status": packet.get("status")},
        )


def _normalise_statements(
    packet: Mapping[str, Any],
    *,
    facts: Sequence[L3SecXbrlProjectionFact],
    single_period: tuple[str, int] | None,
) -> list[dict[str, Any]]:
    raw_statements = packet.get("statements")
    if not isinstance(raw_statements, Sequence) or isinstance(raw_statements, (str, bytes)):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_statements_invalid",
            "Statement packet persistence requires a statement list.",
        )
    statements: list[dict[str, Any]] = []
    for index, item in enumerate(raw_statements, start=1):
        if not isinstance(item, Mapping):
            raise SecXbrlStatementPacketPersistenceError(
                "sec_xbrl_statement_packet_persistence_statement_invalid",
                "Each statement packet section must be an object.",
            )
        statement = _statement(item.get("statement"))
        rows = _normalise_rows(item.get("rows") or [], statement=statement, facts=facts, single_period=single_period)
        status_counts = _row_count_map(rows, "status")
        family_counts = _row_count_map(rows, "family")
        line_count = len(rows)
        projected_count = sum(1 for row in rows if str(row.get("status") or "").startswith("projected"))
        derived_count = sum(1 for row in rows if row.get("status") == "derived")
        provenance_complete_count = sum(1 for row in rows if row["provenance_complete"] is True)
        review_exception_count = sum(1 for row in rows if row["review_exception"])
        _require_public_count(item.get("line_count"), line_count, "line_count")
        _require_public_count(item.get("projected_count"), projected_count, "projected_count")
        _require_public_count(item.get("derived_count"), derived_count, "derived_count")
        _require_public_count(
            item.get("provenance_complete_count"),
            provenance_complete_count,
            "provenance_complete_count",
        )
        _require_public_count(item.get("review_exception_count"), review_exception_count, "review_exception_count")
        _require_public_count_map(item.get("status_counts") or {}, status_counts, "status_counts")
        _require_public_count_map(item.get("family_counts") or {}, family_counts, "family_counts")
        statements.append(
            {
                "statement": statement,
                "statement_index": index,
                "line_count": line_count,
                "projected_count": projected_count,
                "derived_count": derived_count,
                "provenance_complete_count": provenance_complete_count,
                "review_exception_count": review_exception_count,
                "status_counts": status_counts,
                "family_counts": family_counts,
                "rows": rows,
            }
        )
    return statements


def _normalise_rows(
    value: Any,
    *,
    statement: str,
    facts: Sequence[L3SecXbrlProjectionFact],
    single_period: tuple[str, int] | None,
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_rows_invalid",
            "Statement packet rows must be a list.",
        )
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise SecXbrlStatementPacketPersistenceError(
                "sec_xbrl_statement_packet_persistence_row_invalid",
                "Each statement packet row must be an object.",
            )
        _reject_raw_or_local_authority(item)
        row_statement = _statement(item.get("statement") or statement)
        if row_statement != statement:
            raise SecXbrlStatementPacketPersistenceError(
                "sec_xbrl_statement_packet_persistence_row_statement_mismatch",
                "Statement packet row statement must match its parent statement section.",
            )
        period_ref, period_index = _row_period(item, single_period=single_period)
        normalised = {
            "statement": row_statement,
            "statement_row_index": _positive_int(item.get("statement_row_index") or index, "statement_row_index"),
            "source_index": _positive_int(item.get("source_index") or index, "source_index"),
            "period_ref": period_ref,
            "period_index": period_index,
            "canonical_id": _required_text(item.get("canonical_id"), "canonical_id"),
            "basis": _required_text(item.get("basis"), "basis"),
            "requested_basis": _required_text(item.get("requested_basis") or item.get("basis"), "requested_basis"),
            "family": _required_text(item.get("family") or "universal", "family"),
            "source_qname": _optional_text(item.get("source_qname")),
            "status": _required_text(item.get("status"), "status"),
            "oracle_confirmed": _oracle_value(item.get("oracle_confirmed")),
            "mapping_method": _optional_text(item.get("mapping_method")),
            "mapping_confidence": _optional_text(item.get("mapping_confidence")),
            "unit_class": _optional_text(item.get("unit_class")),
            "provenance_complete": item.get("provenance_complete") is True,
            "value_redacted": _required_true(item.get("value_redacted"), "value_redacted"),
            "derived_from_concepts": _public_concept_list(item.get("derived_from_concepts")),
        }
        normalised["review_exception"] = (
            normalised["provenance_complete"] is not True
            or normalised["oracle_confirmed"] in {"false", "oracle_absent"}
        )
        fact = _matching_fact(normalised, facts)
        normalised["sec_xbrl_projection_fact_id"] = fact.sec_xbrl_projection_fact_id
        rows.append(normalised)
    return rows


def _matching_fact(row: Mapping[str, Any], facts: Sequence[L3SecXbrlProjectionFact]) -> L3SecXbrlProjectionFact:
    matches = [
        fact
        for fact in facts
        if fact.period_ref == row["period_ref"]
        and fact.period_index == row["period_index"]
        and fact.statement == row["statement"]
        and fact.statement_row_index == row["statement_row_index"]
        and fact.canonical_id == row["canonical_id"]
        and fact.basis == row["basis"]
        and fact.requested_basis == row["requested_basis"]
        and fact.family == row["family"]
        and (fact.source_qname or None) == (row.get("source_qname") or None)
    ]
    if len(matches) != 1:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_projection_fact_binding_failed",
            "Statement packet row must bind to exactly one persisted projection fact.",
            details={
                "canonical_id": row["canonical_id"],
                "statement": row["statement"],
                "statement_row_index": row["statement_row_index"],
                "match_count": len(matches),
            },
        )
    return matches[0]


def _single_projection_period(facts: Sequence[L3SecXbrlProjectionFact]) -> tuple[str, int] | None:
    values = {(fact.period_ref, fact.period_index) for fact in facts}
    if len(values) == 1:
        return next(iter(values))
    return None


def _row_period(item: Mapping[str, Any], *, single_period: tuple[str, int] | None) -> tuple[str, int]:
    period_ref = _optional_text(item.get("period_ref"))
    period_index_value = item.get("period_index")
    if period_ref is None and period_index_value is None and single_period is not None:
        return single_period
    if period_ref is None or period_index_value is None:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_period_binding_required",
            "Statement packet rows require explicit period refs unless the projection set has one period.",
        )
    return _safe_public_ref(period_ref, "period_ref"), _positive_int(period_index_value, "period_index")


def _public_identity_rollup(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_identity_rollup_invalid",
            "Statement packet identity rollup must be an object.",
        )
    _reject_raw_or_local_authority(value)
    if value.get("identity_residuals"):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_residual_magnitudes_not_admitted",
            "Persisted statement packets do not admit residual magnitude rows in the first slice.",
        )
    return {
        "identity_residual_count": _non_negative_int(value.get("identity_residual_count") or 0, "identity_residual_count"),
        "identity_residual_evaluated_count": _non_negative_int(
            value.get("identity_residual_evaluated_count") or 0,
            "identity_residual_evaluated_count",
        ),
        "identity_residual_within_tolerance_count": _non_negative_int(
            value.get("identity_residual_within_tolerance_count") or 0,
            "identity_residual_within_tolerance_count",
        ),
        "identity_residual_failed_count": _non_negative_int(
            value.get("identity_residual_failed_count") or 0,
            "identity_residual_failed_count",
        ),
        "identity_residuals_within_tolerance": _optional_bool_or_none(
            value.get("identity_residuals_within_tolerance"),
            "identity_residuals_within_tolerance",
        ),
    }


def _public_organization_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_organization_contract_invalid",
            "Statement packet organization contract must be an object.",
        )
    _reject_raw_or_local_authority(value)
    _reject_unadmitted_keys(
        value,
        admitted=ORGANIZATION_CONTRACT_KEYS,
        error_code="sec_xbrl_statement_packet_persistence_organization_contract_invalid",
        message="Statement packet organization contract only admits public contract fields.",
    )
    public = {
        key: _required_bool(value[key], key)
        for key in ORGANIZATION_CONTRACT_BOOL_FIELDS
        if key in value
    }
    public.update(
        {
            key: _non_negative_int(value[key], key)
            for key in ORGANIZATION_CONTRACT_COUNT_FIELDS
            if key in value
        }
    )
    return public


def _packet_summary(*, statements: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "statement_count": len(statements),
        "total_review_rows": len(rows),
        "statements_with_rows": sum(1 for statement in statements if statement["rows"]),
        "review_exception_count": sum(1 for row in rows if row["review_exception"]),
        "value_policy": L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
    }


def _validate_packet_derived_contract(
    packet: Mapping[str, Any],
    *,
    packet_summary: Mapping[str, Any],
    provenance_complete_count: int,
    review_ready: bool,
) -> None:
    _require_public_count(packet.get("statement_count"), packet_summary["statement_count"], "statement_count")
    _require_public_count(packet.get("total_review_rows"), packet_summary["total_review_rows"], "total_review_rows")
    _require_public_count(
        packet.get("provenance_complete_count"),
        provenance_complete_count,
        "provenance_complete_count",
    )
    _require_public_count(
        packet.get("review_exception_count"),
        packet_summary["review_exception_count"],
        "review_exception_count",
    )
    if _required_bool(packet.get("review_ready"), "review_ready") is not review_ready:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_packet_summary_invalid",
            "Statement packet public header fields must match normalized persisted packet rows.",
            details={"field": "review_ready"},
        )


def _response(row: L3SecXbrlStatementPacketSet, *, idempotent_replay: bool) -> dict[str, Any]:
    statement_count = len(row.statements)
    row_count = sum(len(statement.rows) for statement in row.statements)
    return {
        "status": L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
        "schema_id": PACKET_SET_SCHEMA_ID,
        "sec_xbrl_statement_packet_set_id": row.sec_xbrl_statement_packet_set_id,
        "sec_xbrl_projection_set_id": row.sec_xbrl_projection_set_id,
        "client_request_id": row.client_request_id,
        "packet_basis_hash": row.packet_basis_hash,
        "statement_count": statement_count,
        "row_count": row_count,
        "value_policy": row.value_policy,
        "idempotent_replay": idempotent_replay,
        "runtime_default_enabled": False,
        "value_reveal_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "operator_workflow_enabled": False,
    }


def _statement(value: Any) -> str:
    statement = _required_text(value, "statement")
    if statement not in ALLOWED_STATEMENTS:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_statement_not_admitted",
            "Statement packet statement is not admitted for SEC XBRL persistence.",
            details={"statement": statement},
        )
    return statement


def _oracle_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = _required_text(value, "oracle_confirmed")
    if text not in {"true", "false", "oracle_absent"}:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_oracle_state_invalid",
            "Statement packet row oracle state is not admitted.",
            details={"oracle_confirmed": text},
        )
    return text


def _public_count_map(value: Any, field: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_count_map_invalid",
            "Statement packet count maps must be objects.",
            details={"field": field},
        )
    counts: dict[str, int] = {}
    for key, item in value.items():
        label = _safe_public_ref(str(key), field)
        counts[label] = _non_negative_int(item, field)
    return counts


def _row_count_map(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field) or "") for row in rows).items()))


def _require_public_count(value: Any, expected: int, field: str) -> None:
    actual = _non_negative_int(value, field)
    if actual != expected:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_packet_summary_invalid",
            "Statement packet public header fields must match normalized persisted packet rows.",
            details={"field": field, "expected": expected, "actual": actual},
        )


def _require_public_count_map(value: Any, expected: Mapping[str, int], field: str) -> None:
    actual = _public_count_map(value, field)
    if actual != dict(expected):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_packet_summary_invalid",
            "Statement packet public statement counts must match normalized persisted packet rows.",
            details={"field": field, "expected": dict(expected), "actual": actual},
        )


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_required_field_missing",
            f"SEC XBRL statement packet persistence requires {field}.",
            details={"field": field},
        )
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_int(value: Any, field: str) -> int:
    number = _non_negative_int(value, field)
    if number <= 0:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_integer_invalid",
            f"SEC XBRL statement packet persistence requires a positive {field}.",
            details={"field": field},
        )
    return number


def _non_negative_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_integer_invalid",
            f"SEC XBRL statement packet persistence requires an integer {field}.",
            details={"field": field},
        ) from exc
    if number < 0:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_integer_invalid",
            f"SEC XBRL statement packet persistence requires a non-negative {field}.",
            details={"field": field},
        )
    return number


def _required_true(value: Any, field: str) -> bool:
    if value is not True:
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_redaction_required",
            f"SEC XBRL statement packet persistence requires {field}=true.",
            details={"field": field},
        )
    return True


def _required_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_boolean_required",
            f"SEC XBRL statement packet persistence requires boolean {field}.",
            details={"field": field},
        )
    return value


def _optional_bool_or_none(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    return _required_bool(value, field)


def _safe_public_ref(value: Any, field: str) -> str:
    text = _required_text(value, field)
    _reject_raw_or_local_authority(text)
    return text


def _public_concept_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SecXbrlStatementPacketPersistenceError(
            "sec_xbrl_statement_packet_persistence_concept_list_invalid",
            "Derived concept references must be a list of public concept ids.",
        )
    concepts = []
    for item in value:
        concept = _required_text(item, "derived_from_concepts")
        _reject_raw_or_local_authority(concept)
        concepts.append(concept)
    return concepts


def _reject_unadmitted_keys(
    value: Mapping[str, Any],
    *,
    admitted: set[str],
    error_code: str,
    message: str,
) -> None:
    unknown = sorted(str(key) for key in value if str(key) not in admitted)
    if unknown:
        raise SecXbrlStatementPacketPersistenceError(
            error_code,
            message,
            details={"fields": unknown},
        )


def _reject_raw_or_local_authority(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_match = key_text.strip().lower()
            if key_match in RAW_VALUE_KEYS or key_match in RAW_AUTHORITY_KEYS:
                if item is not None:
                    raise SecXbrlStatementPacketPersistenceError(
                        "sec_xbrl_statement_packet_persistence_raw_authority_not_admitted",
                        "SEC XBRL statement packet persistence cannot store raw values or raw authority identifiers.",
                        details={"field": key_text},
                    )
            if key_match in RESIDUAL_MAGNITUDE_KEYS and item is not None:
                raise SecXbrlStatementPacketPersistenceError(
                    "sec_xbrl_statement_packet_persistence_residual_magnitudes_not_admitted",
                    "SEC XBRL statement packet persistence cannot store residual magnitude fields.",
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
            or LOCAL_REF_RE.search(value)
            or RAW_PERIOD_DATE_RE.search(value)
        ):
            raise SecXbrlStatementPacketPersistenceError(
                "sec_xbrl_statement_packet_persistence_raw_reference_not_admitted",
                "SEC XBRL statement packet persistence cannot store raw accession, SEC URL, period date, or local path strings.",
            )
