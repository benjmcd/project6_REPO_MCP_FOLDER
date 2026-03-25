from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


APS_TOTAL_KEYS = ("count", "total", "Total", "totalHits", "total_hits", "TotalHits")
APS_RESULTS_KEYS = ("results", "Results", "documents", "Documents")
APS_TEXT_PATH_CANDIDATES = (
    ("document", "content"),
    ("content",),
    ("IndexedContent",),
    ("indexedContent",),
    ("DocumentText",),
    ("documentText",),
    ("DocumentContent",),
    ("documentContent",),
    ("Text",),
    ("text",),
)
APS_OPERATOR_MAP = {"eq": "equals", "gt": "ge", "lt": "le"}
APS_ALLOWED_WIRE_SHAPE_MODES = {"auto_probe", "guide_native", "shape_a", "shape_b", "draft_shape_a"}
APS_SHAPE_A_EXPRESSION_OPERATORS = {"ge", "gt", "le", "lt", "eq", "ne"}
APS_DEFAULT_DIALECT_PROBE_ORDER = ("shape_a", "guide_native", "shape_b")


@dataclass(frozen=True)
class ApsLogicalQuery:
    text_query: str
    properties: list[dict[str, Any]]
    main_lib_filter: bool
    legacy_lib_filter: bool
    sort_field: str
    sort_direction: int
    include_content: bool | None
    requested_take: int | None
    identity_fingerprint: str


def stable_json_hash(payload: Any) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def strip_internal_fields(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if str(key).startswith("_"):
                continue
            out[str(key)] = strip_internal_fields(value)
        return out
    if isinstance(obj, list):
        return [strip_internal_fields(item) for item in obj]
    return obj


def coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_sort(raw_sort: Any, explicit_sort_direction: Any) -> tuple[str, int]:
    sort_raw = str(raw_sort or "DateAddedTimestamp").strip() or "DateAddedTimestamp"
    if sort_raw.startswith("-"):
        return sort_raw[1:] or "DateAddedTimestamp", 1
    if sort_raw.startswith("+"):
        return sort_raw[1:] or "DateAddedTimestamp", 0
    direction = coerce_int(explicit_sort_direction, 1)
    if direction not in {0, 1}:
        direction = 1
    return sort_raw, direction


def map_aps_filter(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or raw.get("field") or "").strip()
    if not name:
        return None
    operator_raw = str(raw.get("operator") or "equals").strip()
    operator = APS_OPERATOR_MAP.get(operator_raw, operator_raw or "equals")
    value = raw.get("value")
    return {"name": name, "operator": operator, "value": value}


def normalize_aps_query_payload(query_payload: dict[str, Any], mode: str) -> tuple[dict[str, Any], list[str]]:
    inbound = dict(query_payload or {})
    warnings: list[str] = []

    if isinstance(inbound.get("searchCriteria"), dict):
        outbound = dict(inbound)
        criteria = dict(inbound.get("searchCriteria") or {})
        if "q" not in criteria:
            criteria["q"] = ""
        if "mainLibFilter" not in criteria:
            criteria["mainLibFilter"] = True
            warnings.append("default mainLibFilter=true applied")
        if "legacyLibFilter" not in criteria:
            criteria["legacyLibFilter"] = False
            warnings.append("default legacyLibFilter=false applied")
        if "properties" not in criteria or not isinstance(criteria.get("properties"), list):
            criteria["properties"] = []
        outbound["searchCriteria"] = criteria
        outbound["skip"] = coerce_int(outbound.get("skip", 0), 0)
        sort, sort_direction = parse_sort(outbound.get("sort"), outbound.get("sortDirection"))
        outbound["sort"] = sort
        outbound["sortDirection"] = sort_direction
        return strip_internal_fields(outbound), warnings

    q_value = str(inbound.get("q") or inbound.get("queryString") or "").strip()
    sort_value, sort_direction = parse_sort(inbound.get("sort"), inbound.get("sortDirection"))
    skip = max(0, coerce_int(inbound.get("skip", 0), 0))

    properties: list[dict[str, Any]] = []
    for raw in inbound.get("filters", []) if isinstance(inbound.get("filters"), list) else []:
        mapped = map_aps_filter(raw)
        if mapped:
            properties.append(mapped)
    for raw in inbound.get("anyFilters", []) if isinstance(inbound.get("anyFilters"), list) else []:
        mapped = map_aps_filter(raw)
        if mapped:
            warnings.append("anyFilters OR semantics approximated into properties list")
            mapped["_logic"] = "OR"
            properties.append(mapped)

    docket_raw = inbound.get("docketNumber")
    if docket_raw is not None:
        for docket in str(docket_raw).split(","):
            value = docket.strip()
            if not value:
                continue
            properties.append({"name": "DocketNumber", "operator": "equals", "value": value})

    outbound: dict[str, Any] = {
        "skip": skip,
        "sort": sort_value,
        "sortDirection": sort_direction,
        "searchCriteria": {
            "q": q_value,
            "mainLibFilter": bool(inbound.get("mainLibFilter", True)),
            "legacyLibFilter": bool(inbound.get("legacyLibFilter", False)),
            "properties": properties,
        },
    }
    if "content" in inbound:
        outbound["content"] = bool(inbound.get("content"))
    if "take" in inbound:
        outbound["take"] = max(1, coerce_int(inbound.get("take"), 100))

    if mode == "lenient_pass_through":
        known_fields = {
            "q",
            "queryString",
            "filters",
            "anyFilters",
            "mainLibFilter",
            "legacyLibFilter",
            "sort",
            "sortDirection",
            "skip",
            "searchCriteria",
            "content",
            "take",
            "docketNumber",
        }
        for key, value in inbound.items():
            if key in known_fields or key in outbound:
                continue
            outbound[key] = value
            warnings.append(f"lenient pass-through preserved top-level field: {key}")

    return strip_internal_fields(outbound), warnings


def normalize_wire_dialect(value: Any, *, default: str = "auto_probe") -> str:
    normalized = str(value or default).strip().lower()
    if normalized == "draft_shape_a":
        return "shape_a"
    if normalized in APS_ALLOWED_WIRE_SHAPE_MODES:
        return normalized
    return default


def shape_a_expression_value(field: str, operator: str, value: Any) -> str:
    if isinstance(value, bool):
        literal = "true" if value else "false"
    elif isinstance(value, (int, float)):
        literal = str(value)
    else:
        escaped = str(value).replace("'", "''")
        literal = f"'{escaped}'"
    return f"({field} {operator} {literal})"


def guide_property_to_shape_a_filter(prop: dict[str, Any]) -> dict[str, Any] | None:
    field = str(prop.get("name") or "").strip()
    if not field:
        return None
    operator = str(prop.get("operator") or "equals").strip() or "equals"
    value = prop.get("value")
    if value is None:
        return None
    if operator in APS_SHAPE_A_EXPRESSION_OPERATORS:
        return {"field": field, "value": shape_a_expression_value(field, operator, value)}
    return {"field": field, "value": value, "operator": operator}


def guide_to_shape_a_payload(guide_payload: dict[str, Any]) -> dict[str, Any]:
    base = dict(guide_payload or {})
    criteria = dict(base.get("searchCriteria") or {})
    filters: list[dict[str, Any]] = []
    any_filters: list[dict[str, Any]] = []
    for raw_prop in criteria.get("properties", []) if isinstance(criteria.get("properties"), list) else []:
        if not isinstance(raw_prop, dict):
            continue
        mapped = guide_property_to_shape_a_filter(raw_prop)
        if not mapped:
            continue
        if str(raw_prop.get("_logic") or "").strip().upper() == "OR":
            any_filters.append(mapped)
        else:
            filters.append(mapped)

    shape_a: dict[str, Any] = {
        "q": str(criteria.get("q") or ""),
        "filters": filters,
        "anyFilters": any_filters,
        "mainLibFilter": bool(criteria.get("mainLibFilter", True)),
        "legacyLibFilter": bool(criteria.get("legacyLibFilter", False)),
        "sort": str(base.get("sort") or "DateAddedTimestamp"),
        "sortDirection": coerce_int(base.get("sortDirection", 1), 1),
        "skip": max(0, coerce_int(base.get("skip", 0), 0)),
    }
    if "content" in base:
        shape_a["content"] = bool(base.get("content"))
    if "take" in base:
        shape_a["take"] = max(1, coerce_int(base.get("take"), 100))
    return shape_a


def build_logical_query(normalized_query_payload: dict[str, Any]) -> ApsLogicalQuery:
    criteria = dict(normalized_query_payload.get("searchCriteria") or {})
    properties = [strip_internal_fields(dict(item or {})) for item in criteria.get("properties", []) if isinstance(item, dict)]
    include_content: bool | None = None
    if "content" in normalized_query_payload:
        include_content = bool(normalized_query_payload.get("content"))
    requested_take: int | None = None
    if "take" in normalized_query_payload:
        requested_take = max(1, coerce_int(normalized_query_payload.get("take"), 100))
    sort_field, sort_direction = parse_sort(normalized_query_payload.get("sort"), normalized_query_payload.get("sortDirection"))
    identity = {
        "q": str(criteria.get("q") or ""),
        "mainLibFilter": bool(criteria.get("mainLibFilter", True)),
        "legacyLibFilter": bool(criteria.get("legacyLibFilter", False)),
        "properties": properties,
        "sort": sort_field,
        "sortDirection": sort_direction,
        "content": include_content,
        "take": requested_take,
    }
    return ApsLogicalQuery(
        text_query=str(criteria.get("q") or ""),
        properties=properties,
        main_lib_filter=bool(criteria.get("mainLibFilter", True)),
        legacy_lib_filter=bool(criteria.get("legacyLibFilter", False)),
        sort_field=sort_field,
        sort_direction=sort_direction,
        include_content=include_content,
        requested_take=requested_take,
        identity_fingerprint=stable_json_hash(identity),
    )


def logical_query_dict(logical_query: ApsLogicalQuery) -> dict[str, Any]:
    return {
        "q": logical_query.text_query,
        "mainLibFilter": bool(logical_query.main_lib_filter),
        "legacyLibFilter": bool(logical_query.legacy_lib_filter),
        "properties": [strip_internal_fields(dict(item or {})) for item in logical_query.properties],
        "sort": logical_query.sort_field,
        "sortDirection": int(logical_query.sort_direction),
        "content": logical_query.include_content,
        "take": logical_query.requested_take,
    }


def compile_guide_native_payload(logical_query: ApsLogicalQuery, *, skip: int, take: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "skip": max(0, int(skip)),
        "sort": logical_query.sort_field,
        "sortDirection": int(logical_query.sort_direction),
        "searchCriteria": {
            "q": logical_query.text_query,
            "mainLibFilter": bool(logical_query.main_lib_filter),
            "legacyLibFilter": bool(logical_query.legacy_lib_filter),
            "properties": [strip_internal_fields(dict(item or {})) for item in logical_query.properties],
        },
        "take": max(1, int(take)),
    }
    if logical_query.include_content is not None:
        payload["content"] = bool(logical_query.include_content)
    return payload


def compile_shape_a_payload(logical_query: ApsLogicalQuery, *, skip: int, take: int) -> dict[str, Any]:
    guide_payload = compile_guide_native_payload(logical_query, skip=skip, take=take)
    return guide_to_shape_a_payload(guide_payload)


def compile_shape_b_payload(logical_query: ApsLogicalQuery, *, skip: int, take: int) -> dict[str, Any]:
    filters: list[dict[str, Any]] = []
    docket_values: list[str] = []
    for prop in logical_query.properties:
        field = str(prop.get("name") or "").strip()
        if not field:
            continue
        operator = str(prop.get("operator") or "equals").strip() or "equals"
        value = prop.get("value")
        if field == "DocketNumber" and value is not None:
            docket_values.append(str(value).strip())
        filters.append({"name": field, "operator": operator, "value": value})
    prefix = "+" if int(logical_query.sort_direction) == 0 else "-"
    payload: dict[str, Any] = {
        "queryString": logical_query.text_query,
        "docketNumber": ",".join([item for item in docket_values if item]),
        "filters": filters,
        "sort": f"{prefix}{logical_query.sort_field}",
        "skip": max(0, int(skip)),
        "take": max(1, int(take)),
    }
    if logical_query.include_content is not None:
        payload["content"] = bool(logical_query.include_content)
    return payload


def compile_dialect_payload(logical_query: ApsLogicalQuery, *, dialect: str, skip: int, take: int) -> dict[str, Any]:
    normalized = normalize_wire_dialect(dialect, default="shape_a")
    if normalized == "guide_native":
        return compile_guide_native_payload(logical_query, skip=skip, take=take)
    if normalized == "shape_b":
        return compile_shape_b_payload(logical_query, skip=skip, take=take)
    return compile_shape_a_payload(logical_query, skip=skip, take=take)


def build_wire_payload_candidates(
    logical_query: ApsLogicalQuery,
    *,
    dialect_order: list[str],
    skip: int,
    take: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for raw_dialect in dialect_order:
        dialect = normalize_wire_dialect(raw_dialect, default="shape_a")
        payload = strip_internal_fields(
            compile_dialect_payload(logical_query, dialect=dialect, skip=skip, take=take)
        )
        payload_hash = stable_json_hash(payload)
        if payload_hash in seen_hashes:
            continue
        seen_hashes.add(payload_hash)
        out.append({"wire_shape": dialect, "payload": payload})
    return out


def parse_json_response_text(text: str | None) -> tuple[dict[str, Any] | None, str]:
    body = text or ""
    if not body.strip():
        return None, "empty_body"
    try:
        payload = json.loads(body)
    except ValueError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "non_dict_json"
    return payload, "ok"


def extract_content_and_path(raw_payload: dict[str, Any]) -> tuple[str | None, str | None]:
    for candidate in APS_TEXT_PATH_CANDIDATES:
        current: Any = raw_payload
        ok = True
        for key in candidate:
            if not isinstance(current, dict) or key not in current:
                ok = False
                break
            current = current[key]
        if not ok or current is None:
            continue
        if isinstance(current, str):
            value = current.strip()
            if value:
                return value, ".".join(candidate)
    return None, None


def first_total_value(payload: dict[str, Any]) -> tuple[int | None, str | None]:
    for key in APS_TOTAL_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        try:
            return int(value), key
        except (TypeError, ValueError):
            return None, key
    return None, None


def normalize_document_projection(raw_doc: dict[str, Any], *, known_document_types: set[str] | None = None) -> dict[str, Any]:
    content, content_source_path = extract_content_and_path(raw_doc)
    accession = str(
        raw_doc.get("AccessionNumber")
        or raw_doc.get("accessionNumber")
        or raw_doc.get("accession_number")
        or ""
    ).strip()
    document_type_value = raw_doc.get("DocumentType") or raw_doc.get("type")
    document_type_known = None
    if known_document_types is not None:
        if isinstance(document_type_value, list):
            document_type_known = any(str(item).strip() in known_document_types for item in document_type_value)
        else:
            document_type_known = str(document_type_value or "").strip() in known_document_types
    return {
        "accession_number": accession or None,
        "document_title": raw_doc.get("DocumentTitle") or raw_doc.get("title"),
        "document_type": document_type_value,
        "document_type_known": document_type_known,
        "document_date": raw_doc.get("DocumentDate") or raw_doc.get("documentDate"),
        "date_added_timestamp": raw_doc.get("DateAddedTimestamp") or raw_doc.get("dateAddedTimestamp"),
        "url": raw_doc.get("Url") or raw_doc.get("url"),
        "docket_number": raw_doc.get("DocketNumber") or raw_doc.get("docketNumber"),
        "content_source_path": content_source_path,
        "content_present": bool(content),
    }


def normalize_search_response(payload: dict[str, Any], *, known_document_types: set[str] | None = None) -> dict[str, Any]:
    results_key = next((key for key in APS_RESULTS_KEYS if isinstance(payload.get(key), list)), None)
    raw_items = payload.get(results_key, []) if results_key else []

    hits: list[dict[str, Any]] = []
    schema_variant = "unknown"
    for raw_hit in raw_items:
        if not isinstance(raw_hit, dict):
            continue
        if isinstance(raw_hit.get("document"), dict):
            vendor_document = dict(raw_hit.get("document") or {})
            schema_variant = "results_with_document"
        else:
            vendor_document = dict(raw_hit)
            if results_key and results_key.lower().startswith("document"):
                schema_variant = "documents_flat"
            elif results_key:
                schema_variant = "results_flat"
        projection = normalize_document_projection(vendor_document, known_document_types=known_document_types)
        hits.append(
            {
                "vendor_hit": raw_hit,
                "vendor_document": vendor_document,
                "projection": projection,
            }
        )

    total_hits, raw_total_key = first_total_value(payload)
    return {
        "schema_variant": schema_variant,
        "results_key": results_key,
        "raw_total_key": raw_total_key,
        "total_hits": total_hits,
        "count_returned": len(hits),
        "hits": hits,
    }


def normalize_document_response(payload: dict[str, Any], *, known_document_types: set[str] | None = None) -> dict[str, Any]:
    if isinstance(payload.get("document"), dict):
        vendor_document = dict(payload.get("document") or {})
        wrapper = "document"
    else:
        vendor_document = dict(payload)
        wrapper = "root"
    projection = normalize_document_projection(vendor_document, known_document_types=known_document_types)
    return {
        "wrapper_variant": wrapper,
        "vendor_document": vendor_document,
        "projection": projection,
    }


def infer_wire_dialect_from_request(request_body: dict[str, Any]) -> str:
    if not isinstance(request_body, dict):
        return "shape_a"
    if isinstance(request_body.get("searchCriteria"), dict):
        return "guide_native"
    if "queryString" in request_body or "docketNumber" in request_body:
        return "shape_b"
    return "shape_a"


def request_to_logical_query(request_body: dict[str, Any]) -> ApsLogicalQuery:
    mode = "lenient_pass_through"
    normalized, _warnings = normalize_aps_query_payload(dict(request_body or {}), mode=mode)
    return build_logical_query(normalized)


def status_class(status_code: int) -> str:
    code = int(status_code or 0)
    if code < 400:
        return "success"
    if 400 <= code <= 499:
        return "client_error"
    if 500 <= code <= 599:
        return "server_error"
    return "unknown"


def payload_shape_hash(payload: dict[str, Any]) -> str:
    return stable_json_hash(strip_internal_fields(payload or {}))


def parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def choose_dialect_order(
    *,
    forced_mode: str,
    capabilities: list[dict[str, Any]],
    now: datetime | None = None,
) -> list[str]:
    normalized_mode = normalize_wire_dialect(forced_mode, default="auto_probe")
    if normalized_mode != "auto_probe":
        return [normalized_mode]

    now_utc = now or datetime.now(timezone.utc).replace(tzinfo=None)
    preferred: list[str] = []
    ranked = sorted(
        capabilities or [],
        key=lambda row: (
            1 if (parse_iso_datetime(row.get("cooldown_until")) and parse_iso_datetime(row.get("cooldown_until")) > now_utc) else 0,
            -(coerce_int(row.get("success_count"), 0) - coerce_int(row.get("failure_count"), 0)),
            -coerce_int(row.get("success_count"), 0),
            coerce_int(row.get("failure_count"), 0),
            0 if coerce_int(row.get("last_status"), 999) < 400 else 1,
        ),
    )
    for row in ranked:
        dialect = normalize_wire_dialect(row.get("dialect"), default="shape_a")
        cooldown_until = parse_iso_datetime(row.get("cooldown_until"))
        if cooldown_until and cooldown_until > now_utc:
            continue
        if dialect in APS_DEFAULT_DIALECT_PROBE_ORDER and dialect not in preferred and coerce_int(row.get("success_count"), 0) > 0:
            preferred.append(dialect)

    for default in APS_DEFAULT_DIALECT_PROBE_ORDER:
        if default not in preferred:
            preferred.append(default)
    return preferred
