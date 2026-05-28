from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from typing import Any


SCHEMA_ID = "tools.sec_xbrl_arelle_extract.v1"
ARELLE_PACKAGE = "arelle-release"
ARELLE_VERSION = "2.41.3"
MIN_MAX_FACTS = 100_000


def main() -> int:
    parser = argparse.ArgumentParser(description="Contained Arelle iXBRL resolved-fact extractor.")
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--max-facts", type=int, default=MIN_MAX_FACTS)
    parser.add_argument("--taxonomy-package", action="append", default=[])
    parser.add_argument("--cache-dir", default="")
    parser.add_argument("--internet-connectivity", choices=("online", "offline"), default="offline")
    args = parser.parse_args()
    if args.max_facts < MIN_MAX_FACTS:
        _emit_error("max_facts_too_low", max_facts=args.max_facts)
        return 2
    try:
        version = importlib.metadata.version(ARELLE_PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        _emit_error("arelle_package_missing")
        return 2
    if version != ARELLE_VERSION:
        _emit_error("arelle_version_mismatch", observed_version=version)
        return 2
    try:
        from arelle import Cntlr  # type: ignore
        from arelle import PackageManager  # type: ignore
    except Exception as exc:
        _emit_error("arelle_import_failed", error_class=exc.__class__.__name__)
        return 2

    entries = [Path(item) for item in args.input]
    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    if args.cache_dir:
        cntlr.webCache.cacheDir = str(Path(args.cache_dir).resolve())
    cntlr.webCache.workOffline = args.internet_connectivity == "offline"
    try:
        package_status = _load_packages(cntlr, PackageManager, args.taxonomy_package)
    except Exception as exc:
        _emit_error("taxonomy_package_load_failed", error_class=exc.__class__.__name__)
        cntlr.close()
        return 2
    package_hashes = package_status["loaded_hashes"]
    facts: list[dict[str, Any]] = []
    loaded_document_counts: list[int] = []
    model_error_count = 0
    try:
        for entry_index, entry in enumerate(entries, start=1):
            try:
                model = cntlr.modelManager.load(str(entry))
            except Exception as exc:
                _emit_error("arelle_model_load_failed", error_class=exc.__class__.__name__, entry_document_index=entry_index)
                return 2
            try:
                raw_facts = list(getattr(model, "facts", []) or []) if model is not None else []
                if len(facts) + len(raw_facts) > args.max_facts:
                    _emit_error("fact_count_exceeds_limit", fact_count=len(facts) + len(raw_facts), max_facts=args.max_facts)
                    return 2
                concept_index = _concept_index(model)
                source_order_base = len(facts)
                facts.extend(
                    _fact_payload(model, concept_index, fact, source_order_base + index, entry_index=entry_index)
                    for index, fact in enumerate(raw_facts, start=1)
                )
                loaded_document_counts.append(len(getattr(model, "urlDocs", {}) or {}) if model is not None else 0)
                model_error_count += len(list(getattr(model, "errors", []) or [])) if model is not None else 0
            finally:
                if model is not None:
                    model.close()
        diagnostics = _diagnostics(model_error_count=model_error_count, facts=facts)
        print(
            json.dumps(
                {
                    "schema_id": SCHEMA_ID,
                    "arelle_package": ARELLE_PACKAGE,
                    "arelle_version": version,
                    "fact_count": len(facts),
                    "facts": facts,
                    "diagnostics": diagnostics,
                    "taxonomy_package_loaded": bool(package_hashes),
                    "taxonomy_package_count": len(package_hashes),
                    "taxonomy_package_hashes": package_hashes,
                    "taxonomy_package_invalid_count": len(package_status["invalid_hashes"]),
                    "taxonomy_package_invalid_hashes": package_status["invalid_hashes"],
                    "taxonomy_network_resolution_enabled": args.internet_connectivity == "online",
                    "document_set": {
                        "entry_document_count": len(entries),
                        "loaded_document_count": sum(loaded_document_counts),
                        "max_loaded_document_count": max(loaded_document_counts or [0]),
                        "entry_documents_loaded": len(loaded_document_counts),
                        "entry_document_loaded": len(loaded_document_counts) == len(entries),
                    },
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    finally:
        cntlr.close()


def _load_packages(cntlr: Any, package_manager: Any, package_paths: list[str]) -> dict[str, list[str]]:
    package_hashes: list[str] = []
    invalid_hashes: list[str] = []
    if not package_paths:
        return {"loaded_hashes": package_hashes, "invalid_hashes": invalid_hashes}
    package_manager.init(cntlr, loadPackagesConfig=False)
    for raw_path in package_paths:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            invalid_hashes.append(hashlib.sha256(str(raw_path).encode("utf-8")).hexdigest())
            continue
        package_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            info = package_manager.addPackage(cntlr, str(path.resolve()))
        except Exception:
            invalid_hashes.append(package_hash)
            continue
        if info is None:
            invalid_hashes.append(package_hash)
            continue
        package_hashes.append(package_hash)
    if not package_hashes:
        raise RuntimeError("taxonomy_package_valid_package_missing")
    package_manager.rebuildRemappings(cntlr)
    return {"loaded_hashes": package_hashes, "invalid_hashes": invalid_hashes}


def _fact_payload(
    model: Any,
    concept_index: dict[tuple[str, str], Any],
    fact: Any,
    source_order: int,
    *,
    entry_index: int,
) -> dict[str, Any]:
    context = getattr(fact, "context", None)
    unit = getattr(fact, "unit", None)
    effective_value = str(getattr(fact, "value", "") or "")
    lexical_value = _lexical_value(fact)
    return {
        "source_order": source_order,
        "entry_document_index": entry_index,
        "concept": _concept_payload(model, concept_index, fact),
        "context_id": str(getattr(context, "id", "") or _attr(fact, "contextRef") or ""),
        "unit_id": str(getattr(unit, "id", "") or _attr(fact, "unitRef") or ""),
        "period": _period_payload(context),
        "unit": _unit_payload(unit),
        "dimensions": _dimensions_payload(context),
        "decimals": _attr(fact, "decimals"),
        "precision": _attr(fact, "precision"),
        "scale": _attr(fact, "scale"),
        "format": _attr(fact, "format"),
        "sign": _attr(fact, "sign"),
        "hidden": _hidden(fact),
        "continued": bool(_attr(fact, "continuedAt")),
        "continued_at": _attr(fact, "continuedAt"),
        "footnote_count": len(list(getattr(fact, "footnotes", []) or [])),
        "value": effective_value,
        "effective_value": effective_value,
        "lexical_value": lexical_value,
    }


def _concept_payload(model: Any, concept_index: dict[tuple[str, str], Any], fact: Any) -> dict[str, Any]:
    concept = getattr(fact, "concept", None)
    qname = getattr(concept, "qname", None) or getattr(fact, "qname", None)
    dts_concept = concept or _lookup_concept(model, concept_index, qname)
    payload = _qname_payload(qname)
    namespace = payload["namespace"]
    standard = _is_standard_namespace(namespace)
    return {
        **payload,
        "standard": standard,
        "extension": bool(namespace and not standard),
        "abstract": bool(getattr(dts_concept, "isAbstract", False)) if dts_concept is not None else False,
        "resolved_from_dts": dts_concept is not None,
    }


def _concept_index(model: Any) -> dict[tuple[str, str], Any]:
    qname_concepts = getattr(model, "qnameConcepts", {}) or {}
    output: dict[tuple[str, str], Any] = {}
    for candidate_qname, concept in qname_concepts.items():
        namespace = str(getattr(candidate_qname, "namespaceURI", "") or "")
        local_name = str(getattr(candidate_qname, "localName", "") or "")
        if namespace and local_name:
            output[(namespace, local_name)] = concept
    return output


def _lookup_concept(model: Any, concept_index: dict[tuple[str, str], Any], qname: Any) -> Any:
    qname_concepts = getattr(model, "qnameConcepts", {}) or {}
    found = qname_concepts.get(qname)
    if found is not None:
        return found
    namespace = str(getattr(qname, "namespaceURI", "") or "")
    local_name = str(getattr(qname, "localName", "") or "")
    if not namespace or not local_name:
        return None
    return concept_index.get((namespace, local_name))


def _period_payload(context: Any) -> dict[str, Any]:
    if context is None:
        return {"type": "missing", "start": None, "end": None, "instant": None, "forever": False, "resolved": False}
    if bool(getattr(context, "isForeverPeriod", False)):
        return {"type": "forever", "start": None, "end": None, "instant": None, "forever": True, "resolved": True}
    if bool(getattr(context, "isInstantPeriod", False)):
        return {
            "type": "instant",
            "start": None,
            "end": None,
            "instant": _context_date(context, "instantDate", "instantDatetime", adjusted_end=True),
            "forever": False,
            "resolved": True,
        }
    if bool(getattr(context, "isStartEndPeriod", False)):
        return {
            "type": "duration",
            "start": _context_date(context, "startDate", "startDatetime"),
            "end": _context_date(context, "endDate", "endDatetime", adjusted_end=True),
            "instant": None,
            "forever": False,
            "resolved": True,
        }
    return {"type": "unknown", "start": None, "end": None, "instant": None, "forever": False, "resolved": False}


def _unit_payload(unit: Any) -> dict[str, Any]:
    if unit is None:
        return {"resolved": False, "measures": [], "currency": None, "numerator": [], "denominator": []}
    measures = getattr(unit, "measures", ([], [])) or ([], [])
    numerator = [_qname_text(qname) for qname in (measures[0] if len(measures) > 0 else [])]
    denominator = [_qname_text(qname) for qname in (measures[1] if len(measures) > 1 else [])]
    currency = next((item for item in numerator if item.startswith("iso4217:")), None)
    return {"resolved": True, "measures": numerator, "currency": currency, "numerator": numerator, "denominator": denominator}


def _dimensions_payload(context: Any) -> dict[str, Any]:
    explicit: list[dict[str, Any]] = []
    typed: list[dict[str, Any]] = []
    qname_dims = getattr(context, "qnameDims", {}) or {} if context is not None else {}
    for axis, dim in sorted(qname_dims.items(), key=lambda item: _qname_text(item[0])):
        axis_payload = _qname_payload(axis)
        if bool(getattr(dim, "isExplicit", False)):
            explicit.append({"axis": axis_payload, "member": _qname_payload(getattr(dim, "memberQname", None))})
        else:
            typed_member = getattr(dim, "typedMember", None)
            typed.append({"axis": axis_payload, "member_qname": _qname_payload(getattr(typed_member, "qname", None)), "value": _typed_value(typed_member)})
    return {"explicit": explicit, "typed": typed, "resolved": context is not None}


def _diagnostics(*, model_error_count: int, facts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model_error_count": model_error_count,
        "concept_resolved_from_dts_count": sum(1 for fact in facts if fact["concept"]["resolved_from_dts"]),
        "concept_dts_unresolved_count": sum(1 for fact in facts if not fact["concept"]["resolved_from_dts"]),
        "period_unresolved_count": sum(1 for fact in facts if not fact["period"]["resolved"]),
        "unit_unresolved_count": sum(1 for fact in facts if not fact["unit"]["resolved"]),
        "typed_dimension_fact_count": sum(1 for fact in facts if fact["dimensions"]["typed"]),
        "explicit_dimension_fact_count": sum(1 for fact in facts if fact["dimensions"]["explicit"]),
        "hidden_fact_count": sum(1 for fact in facts if fact["hidden"]),
        "continued_fact_count": sum(1 for fact in facts if fact["continued"]),
    }


def _qname_payload(qname: Any) -> dict[str, str]:
    return {"qname": _qname_text(qname), "namespace": str(getattr(qname, "namespaceURI", "") or ""), "local_name": str(getattr(qname, "localName", "") or "")}


def _qname_text(qname: Any) -> str:
    if qname is None:
        return ""
    prefix = str(getattr(qname, "prefix", "") or "")
    local = str(getattr(qname, "localName", "") or "")
    if prefix and local:
        return f"{prefix}:{local}"
    return local or str(qname)


def _is_standard_namespace(namespace: str) -> bool:
    known = ("fasb.org/us-gaap", "xbrl.sec.gov/dei", "xbrl.sec.gov/srt", "xbrl.ifrs.org", "xbrl.org/")
    return any(marker in namespace for marker in known)


def _attr(fact: Any, name: str) -> str | None:
    getter = getattr(fact, "get", None)
    if callable(getter):
        value = getter(name)
        if value is not None:
            return str(value)
    return None


def _hidden(fact: Any) -> bool:
    if bool(getattr(fact, "isHidden", False)):
        return True
    node = fact
    for _ in range(20):
        tag = str(getattr(node, "tag", "") or "").lower()
        if tag.endswith("hidden") or tag.endswith("}hidden"):
            return True
        parent = getattr(node, "getparent", None)
        node = parent() if callable(parent) else None
        if node is None:
            return False
    return False


def _typed_value(node: Any) -> str:
    if node is None:
        return ""
    itertext = getattr(node, "itertext", None)
    if callable(itertext):
        return " ".join(part.strip() for part in itertext() if str(part).strip())
    return str(getattr(node, "text", "") or "")


def _lexical_value(fact: Any) -> str:
    itertext = getattr(fact, "itertext", None)
    if callable(itertext):
        return " ".join(part.strip() for part in itertext() if str(part).strip())
    text = getattr(fact, "text", None)
    if text is not None:
        return str(text)
    return ""


def _date(value: Any) -> str | None:
    if value is None:
        return None
    date_method = getattr(value, "date", None)
    if callable(date_method):
        return date_method().isoformat()
    return str(value)


def _context_date(context: Any, date_attr: str, datetime_attr: str, *, adjusted_end: bool = False) -> str | None:
    direct = getattr(context, date_attr, None)
    if direct is not None:
        return _date(direct)
    value = getattr(context, datetime_attr, None)
    if adjusted_end and isinstance(value, datetime):
        return (value - timedelta(days=1)).date().isoformat()
    return _date(value)


def _emit_error(reason: str, **details: Any) -> None:
    print(json.dumps({"schema_id": SCHEMA_ID, "status": "blocked", "reason": reason, **details}, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
