from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-default-on-runtime.py"


def _runtime_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_default_on_runtime", RUNTIME_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_default_on_runtime_advances_to_selected_nonlocal_readiness_gate() -> None:
    report = _runtime_module().build_report()

    assert report["decision"] == "default_on_runtime_enabled"
    assert report["blocking_reasons"] == []
    assert report["next_slice"] == "sec_xbrl_default_on_nonlocal_production_readiness_design_v1"
