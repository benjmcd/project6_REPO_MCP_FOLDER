from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"
SCRIPTS_DIR = REPO_ROOT / "scripts"
CONFIG_PATH = REPO_ROOT / "backend" / "app" / "core" / "config.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _matrix() -> dict[str, Any]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _matrix_status_by_id() -> dict[str, str]:
    return {
        str(item["id"]): str(item["status"])
        for item in _matrix()["capabilities"]
    }


def _ids_with_status(status_by_id: Mapping[str, str], status: str) -> set[str]:
    return {capability_id for capability_id, value in status_by_id.items() if value == status}


def _evidence_file_pointers(evidence: str) -> list[Path]:
    refs: list[Path] = []
    for raw_token in evidence.split(";"):
        token = raw_token.strip()
        if not token or token.startswith("PR-"):
            continue
        token = token.split("::", 1)[0].split(":", 1)[0].strip()
        path = Path(token[2:] if token.startswith("./") else token)
        if path.parts and path.parts[0] in {"backend", "config", "docs", "tests"}:
            refs.append(path)
        elif path.name == "README.md":
            refs.append(path)
    return refs


def _status_agreement_errors(source_maps: Mapping[str, Mapping[str, str]]) -> list[str]:
    matrix_status = _matrix_status_by_id()
    errors: list[str] = []
    for source_name, source_status in source_maps.items():
        missing = sorted(set(matrix_status) - set(source_status))
        extra = sorted(set(source_status) - set(matrix_status))
        disagreements = sorted(
            capability_id
            for capability_id in set(matrix_status) & set(source_status)
            if source_status[capability_id] != matrix_status[capability_id]
        )
        if missing:
            errors.append(f"{source_name} missing capabilities: {missing}")
        if extra:
            errors.append(f"{source_name} extra capabilities: {extra}")
        for capability_id in disagreements:
            errors.append(
                f"{source_name} status disagreement for {capability_id}: "
                f"matrix={matrix_status[capability_id]} source={source_status[capability_id]}"
            )
    return errors


def _support_matrix_check_status_by_id(module: Any) -> dict[str, str]:
    return dict(module.EXPECTED_STATUS_BY_ID)


def _rc3_status_by_id(module: Any) -> dict[str, str]:
    status: dict[str, str] = {}
    for capability_id in module.UNSUPPORTED_CAPABILITIES:
        status[capability_id] = "unsupported"
    for capability_id in module.EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES:
        status[capability_id] = "experimental_default_off"
    for capability_id in module.OFFLINE_SIMULATION_CAPABILITIES:
        status[capability_id] = "simulation"
    for capability_id in module.SUPPORTED_CAPABILITIES:
        status[capability_id] = "supported"
    return status


def test_honesty_machinery_status_sources_agree_with_matrix() -> None:
    runtime_audit = _load_module(
        "support_matrix_runtime_contract_audit",
        SCRIPTS_DIR / "support_matrix_runtime_contract_audit.py",
    )
    support_check = _load_module("support_matrix_check", SCRIPTS_DIR / "support_matrix_check.py")
    rc3 = _load_module("rc3_sec_xbrl_offline_acceptance", SCRIPTS_DIR / "rc3_sec_xbrl_offline_acceptance.py")
    exhaustive = _load_module(
        "test_layer3_support_matrix_runtime_contract_exhaustive",
        REPO_ROOT / "backend" / "tests" / "test_layer3_support_matrix_runtime_contract_exhaustive.py",
    )

    matrix_status = _matrix_status_by_id()
    errors = _status_agreement_errors(
        {
            "runtime_contract_audit.EXPECTED_STATUS_BY_ID": runtime_audit.EXPECTED_STATUS_BY_ID,
            "support_matrix_check.EXPECTED_STATUS_BY_ID": _support_matrix_check_status_by_id(support_check),
            "rc3_acceptance tier sets": _rc3_status_by_id(rc3),
            "exhaustive_runtime_contract_test parametrization": {
                capability_id: matrix_status[capability_id]
                for capability_id in exhaustive._matrix_capability_ids()
            },
        }
    )

    assert errors == []
    assert set(runtime_audit.PROBES) == set(matrix_status)


def test_honesty_machinery_red_proof_catches_synthetic_status_disagreement() -> None:
    matrix_status = _matrix_status_by_id()
    mutated = dict(matrix_status)
    mutated["sec_live_network_egress"] = "unsupported"

    errors = _status_agreement_errors({"synthetic_checker": mutated})

    assert any("sec_live_network_egress" in error for error in errors)


def test_honesty_machinery_rc3_forbidden_union_matches_matrix() -> None:
    rc3 = _load_module("rc3_sec_xbrl_offline_acceptance", SCRIPTS_DIR / "rc3_sec_xbrl_offline_acceptance.py")
    matrix_status = _matrix_status_by_id()
    forbidden = (
        _ids_with_status(matrix_status, "unsupported")
        | _ids_with_status(matrix_status, "experimental_default_off")
    )

    assert rc3.UNSUPPORTED_CAPABILITIES == _ids_with_status(matrix_status, "unsupported")
    assert rc3.EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES == _ids_with_status(matrix_status, "experimental_default_off")
    assert rc3.FORBIDDEN_SUPPORTED_CAPABILITIES == forbidden


def test_honesty_machinery_pinned_false_flags_are_identical_and_default_false() -> None:
    runtime_audit = _load_module(
        "support_matrix_runtime_contract_audit",
        SCRIPTS_DIR / "support_matrix_runtime_contract_audit.py",
    )
    support_check = _load_module("support_matrix_check", SCRIPTS_DIR / "support_matrix_check.py")
    rc3 = _load_module("rc3_sec_xbrl_offline_acceptance", SCRIPTS_DIR / "rc3_sec_xbrl_offline_acceptance.py")
    sec_audit = _load_module("sec_xbrl_offline_honesty_audit", SCRIPTS_DIR / "sec_xbrl_offline_honesty_audit.py")

    matrix_flags = tuple(_matrix()["pinned_false_flags"])
    assert tuple(runtime_audit.PINNED_FALSE_FLAGS) == matrix_flags
    assert tuple(support_check.PINNED_FALSE_FLAGS) == matrix_flags
    assert tuple(rc3.PINNED_FALSE_FLAGS) == matrix_flags
    assert tuple(sec_audit.PINNED_FALSE_FLAGS) == matrix_flags

    defaults = support_check._settings_defaults(REPO_ROOT)
    assert {flag: defaults.get(flag) for flag in matrix_flags} == {
        flag: False
        for flag in matrix_flags
    }


def test_honesty_machinery_supported_evidence_pointers_resolve() -> None:
    missing: list[str] = []
    for capability in _matrix()["capabilities"]:
        if capability["status"] != "supported":
            continue
        pointers = _evidence_file_pointers(str(capability.get("evidence") or ""))
        if not pointers:
            missing.append(f"{capability['id']}: <no file evidence refs>")
            continue
        for pointer in pointers:
            if not (REPO_ROOT / pointer).exists():
                missing.append(f"{capability['id']}: {pointer.as_posix()}")

    assert missing == []
