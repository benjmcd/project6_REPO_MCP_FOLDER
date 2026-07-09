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
        "app.services.layer3_sec_edgar_material_bridge:prepare_sec_edgar_text_table_material_authority_bridge",
        "app.services.layer3_sec_edgar_html_inline_xbrl_material_bridge:prepare_sec_edgar_html_inline_xbrl_material_bridge",
        "app.services.layer3_sec_edgar_html_inline_xbrl_fact_material_bridge:prepare_sec_edgar_html_inline_xbrl_fact_material_bridge",
        "app.services.layer3_sec_edgar_live_material_bridge:prepare_sec_edgar_text_table_live_source_artifact_material_authority_bridge",
    }
)


def _service_modules(extra_modules: tuple[ModuleType, ...] = ()) -> list[ModuleType]:
    import app.services

    modules = []
    for module_info in pkgutil.iter_modules(app.services.__path__, prefix="app.services."):
        if not module_info.name.rsplit(".", 1)[-1].startswith("layer3_"):
            continue
        modules.append(importlib.import_module(module_info.name))
    modules.extend(extra_modules)
    return modules


def _called_names(function_node: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _string_literals(function_node: ast.FunctionDef) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(function_node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(node.value)
    return values


def _is_preview_or_bridge_site(function_node: ast.FunctionDef) -> bool:
    called = _called_names(function_node)
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


def _discover_material_preview_sites(
    extra_modules: tuple[ModuleType, ...] = (),
) -> set[str]:
    sites: set[str] = set()
    for module in _service_modules(extra_modules):
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if obj.__module__ != module.__name__:
                continue
            try:
                source = inspect.getsource(obj)
            except (OSError, TypeError):
                continue
            parsed = ast.parse(source)
            function_node = next(
                node for node in parsed.body if isinstance(node, ast.FunctionDef)
            )
            if _is_preview_or_bridge_site(function_node):
                sites.add(f"{module.__name__}:{name}")
    return sites


def _classify_producers(sites: set[str]) -> set[str]:
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


def test_material_preview_producer_registry_is_exact() -> None:
    discovered = _discover_material_preview_sites()

    assert _classify_producers(discovered) == PRODUCERS
    assert discovered == PRODUCERS | KNOWN_WRAPPERS


def test_gate_b_decision_reads_production_boundary_not_test_helper() -> None:
    from app.services import layer3_source_boundary, layer3_workbench

    source = inspect.getsource(layer3_workbench.gate_b_decision)
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
