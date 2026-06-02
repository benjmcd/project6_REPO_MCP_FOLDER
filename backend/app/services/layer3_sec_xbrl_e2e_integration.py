from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_sec_xbrl_canonical_statement_organization import (
    organize_canonical_projection_by_statement,
)
from app.services.layer3_sec_xbrl_statement_assembly import (
    assemble_reviewable_statement_packet,
)
from app.services.layer3_utils import json_clone


HASH_RE = re.compile(r"^[0-9a-f]{64}$")
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
RAW_REFERENCE_KEYS = {
    "accession",
    "accession_number",
    "cik",
    "cik_or_filer_ref",
    "company_name",
    "contact",
    "filer_or_cik",
    "issuer_name",
    "local_path",
    "raw_path",
    "registrant",
    "registrant_name",
    "sec_url",
    "storage_dir",
    "storage_root",
    "ticker",
    "user_agent",
}
PROJECTION_PRIVATE_KEYS = {
    "_decimals",
    "_period_key",
    "_resolution_key",
    "_unit",
    "_value",
    "amount",
    "derived_from_resolved_fact_ids",
    "effective_value",
    "lexical_value",
    "resolved_fact_id",
    "sidecar_receipt_id",
    "value",
}


class SecXbrlE2EIntegrationError(ValueError):
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


def redacted_projection_persistence_payload(canonical_projection: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt a private canonical projection into the redacted persistence contract."""

    periods = _projection_periods(canonical_projection)
    redacted_periods = []
    examined_absent: list[str] = []
    for period in periods:
        projection = period["projection"]
        concepts = [_redacted_projection_item(item, projection=projection) for item in _projected_items(projection)]
        if not concepts:
            examined_absent.append(period["period_ref"])
            continue
        redacted_periods.append(
            {
                "period_ref": period["period_ref"],
                "period_index": period["period_index"],
                "projection": {
                    "status": "canonical_projection_ready",
                    "dataset_version_id": _optional_text(projection.get("dataset_version_id")),
                    "sidecar_receipt_hash": _required_hash(
                        projection.get("sidecar_receipt_hash"),
                        "sidecar_receipt_hash",
                    ),
                    "value_store_hash": _required_hash(
                        projection.get("value_store_hash"),
                        "value_store_hash",
                    ),
                    "concepts": concepts,
                },
            }
        )
    if not redacted_periods:
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_no_projected_facts",
            "SEC XBRL end-to-end integration requires at least one period with projected facts.",
            details={"examined_absent_period_refs": examined_absent},
        )
    payload = {
        "status": "canonical_multi_period_projection_ready",
        "periods": redacted_periods,
    }
    presence = canonical_projection.get("sector_family_presence")
    if isinstance(presence, Mapping):
        payload["sector_family_presence"] = json_clone(presence)
    _reject_output_raw_or_local_authority(payload)
    return payload


def projection_items_for_statement_assembly(canonical_projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return private in-memory projection items with period refs for statement assembly only."""

    items: list[dict[str, Any]] = []
    for period in _projection_periods(canonical_projection):
        for item in _projected_items(period["projection"]):
            _reject_input_raw_reference_fields(item)
            row = dict(item)
            row["period_ref"] = period["period_ref"]
            row["period_index"] = period["period_index"]
            items.append(row)
    if not items:
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_no_projected_facts",
            "SEC XBRL end-to-end integration requires projected facts for statement assembly.",
        )
    return items


def build_reviewable_statement_packet_from_projection(
    *,
    canonical_projection: Mapping[str, Any],
    statement_role_view_records: Sequence[Mapping[str, Any]],
    identity_residuals: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the redacted statement packet from private projection and A-role authority."""

    if not isinstance(statement_role_view_records, Sequence) or isinstance(statement_role_view_records, (str, bytes)):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_statement_role_authority_invalid",
            "SEC XBRL end-to-end integration requires statement-role view authority records.",
        )
    projection_items = projection_items_for_statement_assembly(canonical_projection)
    organization_result = organize_canonical_projection_by_statement(
        projection_items=projection_items,
        statement_role_view_records=list(statement_role_view_records),
    )
    return assemble_reviewable_statement_packet(
        projection_items=projection_items,
        organization_result=organization_result,
        identity_residuals=list(identity_residuals or []),
    )


def _projection_periods(canonical_projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(canonical_projection, Mapping):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_projection_invalid",
            "SEC XBRL end-to-end integration requires a canonical projection object.",
        )
    status = str(canonical_projection.get("status") or "")
    if status == "canonical_multi_period_projection_ready":
        periods = canonical_projection.get("periods")
        if not isinstance(periods, Sequence) or isinstance(periods, (str, bytes)):
            raise SecXbrlE2EIntegrationError(
                "sec_xbrl_e2e_integration_periods_missing",
                "SEC XBRL end-to-end integration requires a period list.",
            )
        return [_normalise_period(item, fallback_index=index) for index, item in enumerate(periods, start=1)]
    if status == "canonical_projection_ready":
        return [
            {
                "period_ref": "fy-period-1",
                "period_index": 1,
                "projection": canonical_projection,
            }
        ]
    raise SecXbrlE2EIntegrationError(
        "sec_xbrl_e2e_integration_projection_not_ready",
        "SEC XBRL end-to-end integration only accepts ready canonical projection output.",
        details={"status": status},
    )


def _normalise_period(item: Any, *, fallback_index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_period_invalid",
            "Each SEC XBRL projection period must be an object.",
        )
    projection = item.get("projection")
    if not isinstance(projection, Mapping) or projection.get("status") != "canonical_projection_ready":
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_period_projection_not_ready",
            "Each SEC XBRL projection period must carry ready canonical projection output.",
            details={"status": projection.get("status") if isinstance(projection, Mapping) else None},
        )
    return {
        "period_ref": _required_public_text(item.get("period_ref") or f"fy-period-{fallback_index}", "period_ref"),
        "period_index": _positive_int(item.get("period_index") or fallback_index, "period_index"),
        "projection": projection,
    }


def _projected_items(projection: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    concepts = projection.get("concepts") or projection.get("projection_items") or []
    if not isinstance(concepts, Sequence) or isinstance(concepts, (str, bytes)):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_projection_items_invalid",
            "SEC XBRL canonical projection concepts must be a list.",
        )
    return [
        item
        for item in concepts
        if isinstance(item, Mapping) and item.get("status") != "legitimately_absent"
    ]


def _redacted_projection_item(item: Mapping[str, Any], *, projection: Mapping[str, Any]) -> dict[str, Any]:
    _reject_input_raw_reference_fields(item)
    sidecar_hash = _required_hash(
        item.get("sidecar_receipt_hash") or projection.get("sidecar_receipt_hash"),
        "sidecar_receipt_hash",
    )
    value_hash = _required_hash(
        item.get("value_store_hash") or projection.get("value_store_hash"),
        "value_store_hash",
    )
    resolved_fact_present = _resolved_fact_provenance_present(item)
    if not resolved_fact_present:
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_resolved_fact_authority_missing",
            "Projected SEC XBRL facts require resolved-fact provenance before persistence adaptation.",
            details={
                "canonical_id": str(item.get("canonical_id") or ""),
                "status": str(item.get("status") or ""),
            },
        )
    row = {
        "canonical_id": _required_public_text(item.get("canonical_id"), "canonical_id"),
        "basis": _required_public_text(item.get("basis"), "basis"),
        "requested_basis": _required_public_text(
            item.get("requested_basis") or item.get("basis"),
            "requested_basis",
        ),
        "statement": _required_public_text(item.get("statement"), "statement"),
        "family": _required_public_text(item.get("family") or "universal", "family"),
        "status": _required_public_text(item.get("status"), "status"),
        "source_qname": _optional_public_text(item.get("source_qname")),
        "oracle_confirmed": item.get("oracle_confirmed"),
        "mapping_method": _optional_public_text(item.get("mapping_method")),
        "mapping_confidence": _optional_public_text(item.get("mapping_confidence")),
        "unit_class": _optional_public_text(item.get("unit_class")),
        "provenance_complete": item.get("provenance_complete") is True,
        "value_redacted": True,
        "resolved_fact_provenance_present": True,
        "sidecar_receipt_hash": sidecar_hash,
        "value_store_hash": value_hash,
        "dataset_version_id": _optional_public_text(
            item.get("dataset_version_id") or projection.get("dataset_version_id")
        ),
        "derived_from_concepts": _public_text_list(item.get("derived_from_concepts")),
    }
    return {key: value for key, value in row.items() if value is not None}


def _resolved_fact_provenance_present(item: Mapping[str, Any]) -> bool:
    if bool(str(item.get("resolved_fact_id") or "").strip()):
        return True
    source_ids = item.get("derived_from_resolved_fact_ids")
    return (
        item.get("status") == "derived"
        and isinstance(source_ids, Sequence)
        and not isinstance(source_ids, (str, bytes))
        and len(source_ids) == 2
        and all(bool(str(source_id or "").strip()) for source_id in source_ids)
    )


def _reject_input_raw_reference_fields(item: Mapping[str, Any]) -> None:
    for key, value in item.items():
        key_text = str(key)
        key_match = key_text.strip().lower()
        if key_match in PROJECTION_PRIVATE_KEYS:
            continue
        if key_match in RAW_REFERENCE_KEYS and value is not None:
            raise SecXbrlE2EIntegrationError(
                "sec_xbrl_e2e_integration_raw_reference_not_admitted",
                "SEC XBRL end-to-end integration does not admit raw identity, path, or source references.",
                details={"field": key_text},
            )
        _reject_public_text_patterns(value, field=key_text)


def _reject_output_raw_or_local_authority(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_match = key_text.strip().lower()
            if key_match in PROJECTION_PRIVATE_KEYS or key_match in RAW_REFERENCE_KEYS:
                if item is not None:
                    raise SecXbrlE2EIntegrationError(
                        "sec_xbrl_e2e_integration_raw_output_not_admitted",
                        "SEC XBRL end-to-end integration output cannot carry raw values or raw authority.",
                        details={"field": key_text},
                    )
            _reject_output_raw_or_local_authority(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_output_raw_or_local_authority(item)
        return
    _reject_public_text_patterns(value, field="value")


def _reject_public_text_patterns(value: Any, *, field: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_public_text_patterns(item, field=str(key))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_public_text_patterns(item, field=field)
        return
    if not isinstance(value, str):
        return
    if (
        ACCESSION_RE.search(value)
        or SEC_URL_RE.search(value)
        or WINDOWS_ABS_PATH_RE.search(value)
        or LOCAL_REF_RE.search(value)
        or RAW_PERIOD_DATE_RE.search(value)
    ):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_raw_reference_not_admitted",
            "SEC XBRL end-to-end integration does not admit raw accession, SEC URL, period date, or local path strings.",
            details={"field": field},
        )


def _required_public_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_required_field_missing",
            f"SEC XBRL end-to-end integration requires {field}.",
            details={"field": field},
        )
    _reject_public_text_patterns(text, field=field)
    return text


def _optional_public_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    _reject_public_text_patterns(text, field="public_text")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_hash(value: Any, field: str) -> str:
    text = _required_public_text(value, field).lower()
    if not HASH_RE.fullmatch(text):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_hash_invalid",
            f"SEC XBRL end-to-end integration requires a 64-character lowercase hex hash for {field}.",
            details={"field": field},
        )
    return text


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_integer_invalid",
            f"SEC XBRL end-to-end integration requires an integer {field}.",
            details={"field": field},
        ) from exc
    if number <= 0:
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_integer_invalid",
            f"SEC XBRL end-to-end integration requires a positive {field}.",
            details={"field": field},
        )
    return number


def _public_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SecXbrlE2EIntegrationError(
            "sec_xbrl_e2e_integration_public_text_list_invalid",
            "SEC XBRL end-to-end integration requires public text lists.",
        )
    return [_required_public_text(item, "public_text") for item in value]
