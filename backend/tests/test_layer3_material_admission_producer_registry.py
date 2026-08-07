from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from types import ModuleType


PRODUCERS = frozenset(
    {
        "app.services.layer3_workbench:material_preview",
        "app.services.layer3_source_intake:source_intake_material_preview",
        "app.services.layer3_source_directory_material_admission:source_directory_material_preview",
        "app.services.layer3_connector_source_intake:connector_source_intake_material_preview",
    }
)

KNOWN_WRAPPERS = frozenset(
    {
        "app.services.layer3_connector_promotion:_verify_receipt_gate_b_spine",
        "app.services.layer3_sec_edgar_material_bridge:prepare_sec_edgar_text_table_material_authority_bridge",
        "app.services.layer3_sec_edgar_html_inline_xbrl_material_bridge:prepare_sec_edgar_html_inline_xbrl_material_bridge",
        "app.services.layer3_sec_edgar_html_inline_xbrl_fact_material_bridge:prepare_sec_edgar_html_inline_xbrl_fact_material_bridge",
        "app.services.layer3_sec_edgar_live_material_bridge:prepare_sec_edgar_text_table_live_source_artifact_material_authority_bridge",
    }
)

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef
FUNCTION_NODE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _guard_modules(extra_modules: tuple[ModuleType, ...] = ()) -> list[ModuleType]:
    import app.api.layer3
    import app.services

    modules = []
    for module_info in pkgutil.iter_modules(app.services.__path__, prefix="app.services."):
        if not module_info.name.rsplit(".", 1)[-1].startswith("layer3_"):
            continue
        modules.append(importlib.import_module(module_info.name))
    modules.append(app.api.layer3)
    for module_info in pkgutil.iter_modules(app.api.layer3.__path__, prefix="app.api.layer3."):
        modules.append(importlib.import_module(module_info.name))
    modules.extend(extra_modules)
    return modules


def _import_aliases(function_node: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(function_node):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name.rsplit(".", 1)[-1]
    return aliases


def _top_level_import_aliases(module_node: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in module_node.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name.rsplit(".", 1)[-1]
    return aliases


def _called_names(function_node: FunctionNode, aliases: dict[str, str] | None = None) -> set[str]:
    resolved_aliases = dict(aliases or {})
    resolved_aliases.update(_import_aliases(function_node))
    names: set[str] = set()
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(resolved_aliases.get(func.id, func.id))
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _keyword_names(function_node: FunctionNode) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            names.update(keyword.arg for keyword in node.keywords if keyword.arg)
    return names


def _string_literals(function_node: FunctionNode) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(function_node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(node.value)
    return values


def _module_source_has_call(source: str, name: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == name:
            return True
    return False


def _module_source_has_keyworded_call(source: str, name: str, keyword: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = (
            func.id
            if isinstance(func, ast.Name)
            else func.attr
            if isinstance(func, ast.Attribute)
            else ""
        )
        if called == name and any(item.arg == keyword for item in node.keywords):
            return True
    return False


def _is_preview_or_bridge_site(function_node: FunctionNode, aliases: dict[str, str] | None = None) -> bool:
    called = _called_names(function_node, aliases)
    strings = _string_literals(function_node)
    computes_hash = {
        "material_preview_hash",
        "compute_material_preview_hash",
        "_gate_b_material_preview_hash",
    } & called
    forwards_hash = "material_preview_hash" in strings
    preview_name = function_node.name == "material_preview" or function_node.name.endswith(
        "_material_preview"
    )
    bridge_name = function_node.name.startswith("prepare_") and "material" in function_node.name
    has_material_candidate = "material_candidate" in strings or "material_candidates" in strings
    return bool((computes_hash and (preview_name or bridge_name or has_material_candidate)) or (bridge_name and forwards_hash))


def _is_hash_persisting_site(
    module_name: str,
    function_node: FunctionNode,
    aliases: dict[str, str] | None = None,
) -> bool:
    if module_name in {"app.services.layer3_gate_b_state", "app.services.layer3_workbench"}:
        return False
    called = _called_names(function_node, aliases)
    keywords = _keyword_names(function_node)
    persists_hash = {
        "claim_gate_b_idempotency",
        "gate_b_idempotency_claim_matches",
        "gate_b_idempotency_request_hash",
    } & called
    return bool(persists_hash and "material_preview_hash" in keywords)


def _production_gate_b_hash_persistence_chain_is_intact() -> bool:
    from app.services import layer3_gate_b_state, layer3_workbench

    entry_source = inspect.getsource(layer3_workbench.gate_b_decision)
    workbench_source = inspect.getsource(layer3_workbench._gate_b_decision_impl)
    claim_source = inspect.getsource(layer3_gate_b_state.claim_gate_b_idempotency)
    return (
        _module_source_has_call(entry_source, "_gate_b_decision_impl")
        and _module_source_has_call(workbench_source, "compute_material_preview_hash")
        and _module_source_has_keyworded_call(
            workbench_source,
            "gate_b_idempotency_claim_matches",
            "material_preview_hash",
        )
        and _module_source_has_keyworded_call(
            workbench_source,
            "claim_gate_b_idempotency",
            "material_preview_hash",
        )
        and _module_source_has_keyworded_call(
            claim_source,
            "gate_b_idempotency_request_hash",
            "material_preview_hash",
        )
        and "db.add(claim)" in claim_source
    )


def _discover_material_preview_sites(
    extra_modules: tuple[ModuleType, ...] = (),
) -> set[str]:
    sites: set[str] = set()
    for module in _guard_modules(extra_modules):
        module_aliases: dict[str, str] = {}
        try:
            module_aliases = _top_level_import_aliases(ast.parse(inspect.getsource(module)))
        except (OSError, TypeError):
            module_aliases = {}
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if obj.__module__ != module.__name__:
                continue
            try:
                source = inspect.getsource(obj)
            except (OSError, TypeError):
                continue
            parsed = ast.parse(source)
            function_node = next(
                (
                    node
                    for node in ast.walk(parsed)
                    if isinstance(node, FUNCTION_NODE_TYPES) and node.name == obj.__name__
                ),
                None,
            )
            if function_node is None:
                continue
            if _is_preview_or_bridge_site(function_node, module_aliases) or _is_hash_persisting_site(
                module.__name__,
                function_node,
                module_aliases,
            ):
                sites.add(f"{module.__name__}:{name}")
    return sites


def _classify_producers(sites: set[str]) -> set[str]:
    assert _production_gate_b_hash_persistence_chain_is_intact()
    return sites & PRODUCERS


def _rogue_material_preview(db, payload):
    from app.services.layer3_gate_b_state import material_preview_hash

    candidate = {
        "candidate_id": "mat-rogue-1",
        "source_class": "rogue_connector",
        "source_ref": "rogue:1",
        "query_basis": "rogue",
        "provenance_ref": "rogue:1",
        "source_identity": {},
        "source_provenance": {},
        "payload": {},
        "load_summary": {},
    }
    return {
        "material_candidate": candidate,
        "material_preview_hash": material_preview_hash([candidate]),
    }


def _rogue_hash_persisting_producer(db):
    from app.services.layer3_gate_b_state import claim_gate_b_idempotency

    return claim_gate_b_idempotency(
        db,
        client_request_id="rogue-client-request",
        preflight_id="rogue-preflight",
        source_set_id="rogue-source-set",
        material_preview_id="rogue-preview",
        material_preview_hash="f" * 64,
        gate_b_decision_manifest_id="rogue-decision-manifest",
    )


def _rogue_split_api_material_preview(db, payload):
    from app.services.layer3_gate_b_state import material_preview_hash

    candidate = {
        "candidate_id": "mat-rogue-split-api-1",
        "source_class": "rogue_split_api_connector",
        "source_ref": "rogue-split-api:1",
        "query_basis": "rogue_split_api",
        "provenance_ref": "rogue-split-api:1",
        "source_identity": {},
        "source_provenance": {},
        "payload": {},
        "load_summary": {},
    }
    return {
        "material_candidate": candidate,
        "material_preview_hash": material_preview_hash([candidate]),
    }


def _rogue_alias_api_material_preview(db, payload):
    from app.services.layer3_gate_b_state import material_preview_hash as preview_hash_alias

    candidate = {
        "candidate_id": "mat-rogue-alias-api-1",
        "source_class": "rogue_alias_api_connector",
        "source_ref": "rogue-alias-api:1",
        "query_basis": "rogue_alias_api",
        "provenance_ref": "rogue-alias-api:1",
        "source_identity": {},
        "source_provenance": {},
        "payload": {},
        "load_summary": {},
    }
    return {
        "material_candidate": candidate,
        "material_preview_hash": preview_hash_alias([candidate]),
    }


async def post_async_material_preview(db, payload):
    from app.services.layer3_gate_b_state import material_preview_hash

    candidate = {
        "candidate_id": "mat-rogue-async-api-1",
        "source_class": "rogue_async_api_connector",
        "source_ref": "rogue-async-api:1",
        "query_basis": "rogue_async_api",
        "provenance_ref": "rogue-async-api:1",
        "source_identity": {},
        "source_provenance": {},
        "payload": {},
        "load_summary": {},
    }
    return {
        "material_candidate": candidate,
        "material_preview_hash": material_preview_hash([candidate]),
    }


def test_material_preview_producer_registry_is_exact() -> None:
    discovered = _discover_material_preview_sites()

    assert _classify_producers(discovered) == PRODUCERS
    assert discovered == PRODUCERS | KNOWN_WRAPPERS


def test_material_preview_guard_scans_split_layer3_api_modules() -> None:
    scanned = {module.__name__ for module in _guard_modules()}

    assert "app.api.layer3" in scanned
    assert "app.api.layer3.source_ingestion" in scanned


def test_gate_b_decision_reads_production_boundary_not_test_helper() -> None:
    from app.services import layer3_source_boundary, layer3_workbench

    entry_source = inspect.getsource(layer3_workbench.gate_b_decision)
    source = inspect.getsource(layer3_workbench._gate_b_decision_impl)
    assert _module_source_has_call(entry_source, "_gate_b_decision_impl")
    assert "test_layer3_bounded_e2e" not in entry_source
    assert "test_layer3_bounded_e2e" not in source
    assert "CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY" in source

    assert tuple(layer3_source_boundary.SUPPORTED_SOURCE_CLASSES) == (
        "dataset_version",
        "aps_content_document",
    )
    assert (
        layer3_source_boundary.CONNECTOR_SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_MODE
        == "connector_source_intake_gate_b_material_admission"
    )
    assert (
        layer3_source_boundary.CONNECTOR_SOURCE_INTAKE_GATE_B_SOURCE_CLASS
        == "connector_produced_single_source"
    )
    assert (
        layer3_source_boundary.CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX
        == "mat-connector_source_intake_record-"
    )


def test_guard_detects_rogue_material_preview_producer() -> None:
    module = ModuleType("app.services.layer3_rogue_material_preview")
    _rogue_material_preview.__module__ = module.__name__
    module.rogue_material_preview = _rogue_material_preview

    discovered = _discover_material_preview_sites((module,))

    assert "app.services.layer3_rogue_material_preview:rogue_material_preview" in discovered
    assert discovered != PRODUCERS | KNOWN_WRAPPERS


def test_guard_detects_rogue_hash_persisting_producer() -> None:
    module = ModuleType("app.services.layer3_rogue_hash_persisting_producer")
    _rogue_hash_persisting_producer.__module__ = module.__name__
    module.rogue_hash_persisting_producer = _rogue_hash_persisting_producer

    discovered = _discover_material_preview_sites((module,))

    assert (
        "app.services.layer3_rogue_hash_persisting_producer:rogue_hash_persisting_producer"
        in discovered
    )
    assert discovered != PRODUCERS | KNOWN_WRAPPERS


def test_guard_detects_rogue_split_api_material_preview_producer() -> None:
    module = ModuleType("app.api.layer3.source_ingestion_rogue")
    _rogue_split_api_material_preview.__module__ = module.__name__
    module.post_source_ingestion_rogue_material_preview = _rogue_split_api_material_preview

    discovered = _discover_material_preview_sites((module,))

    assert (
        "app.api.layer3.source_ingestion_rogue:post_source_ingestion_rogue_material_preview"
        in discovered
    )
    assert discovered != PRODUCERS | KNOWN_WRAPPERS


def test_guard_detects_rogue_async_split_api_material_preview_producer() -> None:
    module = ModuleType("app.api.layer3.async_rogue")
    post_async_material_preview.__module__ = module.__name__
    module.post_async_material_preview = post_async_material_preview

    discovered = _discover_material_preview_sites((module,))

    assert "app.api.layer3.async_rogue:post_async_material_preview" in discovered
    assert discovered != PRODUCERS | KNOWN_WRAPPERS


def test_guard_detects_alias_import_material_preview_hash() -> None:
    module = ModuleType("app.api.layer3.alias_route")
    _rogue_alias_api_material_preview.__module__ = module.__name__
    module.post_alias_rogue_material_preview = _rogue_alias_api_material_preview

    discovered = _discover_material_preview_sites((module,))

    assert "app.api.layer3.alias_route:post_alias_rogue_material_preview" in discovered
    assert discovered != PRODUCERS | KNOWN_WRAPPERS
