from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

LAYER3_API_RELATIVE = "backend/app/api/layer3.py"
LAYER3_API_PACKAGE_RELATIVE = "backend/app/api/layer3"


def resolve_layer3_api_source(source_root=None) -> str:
    """Return the layer3 API source, package-aware.

    While backend/app/api/layer3.py is a single file, returns that file's text
    verbatim (byte-identical to Path.read_text(encoding='utf-8')). After it is
    decomposed into the backend/app/api/layer3/ package, returns the
    deterministic concatenation (sorted by POSIX relative path) of every *.py
    file under the package, so all substring/token checks still match. Returns
    "" if neither exists (fail-closed: substring checks then evaluate False).
    """
    root = Path(source_root) if source_root is not None else ROOT
    file_path = root / LAYER3_API_RELATIVE
    if file_path.is_file():
        return file_path.read_text(encoding="utf-8")
    pkg = root / LAYER3_API_PACKAGE_RELATIVE
    if pkg.is_dir():
        parts = sorted(pkg.rglob("*.py"), key=lambda p: p.relative_to(pkg).as_posix())
        return "\n".join(p.read_text(encoding="utf-8") for p in parts)
    return ""


LIVE_NETWORK_FIELD = "layer3_sec_edgar_live_network_enabled"
ARELLE_CUTOVER_FIELD = "layer3_sec_edgar_arelle_fact_authority_cutover_enabled"
VALUE_REVEAL_FIELD = "layer3_sec_edgar_arelle_value_reveal_enabled"
CONTROLLED_SUBMIT_FIELD = "layer3_sec_xbrl_controlled_value_reveal_submit_enabled"
POSTURE_FIELDS = (
    LIVE_NETWORK_FIELD,
    ARELLE_CUTOVER_FIELD,
    VALUE_REVEAL_FIELD,
    CONTROLLED_SUBMIT_FIELD,
)


def committed_runtime_posture(*, source_root: Path | None = None) -> dict[str, bool]:
    """Return the committed SEC XBRL default posture used by validate-only diagnostics."""
    root = Path(source_root) if source_root is not None else ROOT
    defaults = _settings_field_defaults(root)
    live_network_default_off = defaults.get(LIVE_NETWORK_FIELD) is False
    arelle_cutover_default_on = defaults.get(ARELLE_CUTOVER_FIELD) is True
    arelle_cutover_default_off = defaults.get(ARELLE_CUTOVER_FIELD) is False
    value_reveal_default_off = defaults.get(VALUE_REVEAL_FIELD) is False
    controlled_submit_default_off = defaults.get(CONTROLLED_SUBMIT_FIELD) is False
    return {
        "config_defaults_off": bool(
            live_network_default_off and arelle_cutover_default_off and value_reveal_default_off
        ),
        "config_safety_defaults_off": bool(live_network_default_off and value_reveal_default_off),
        "arelle_cutover_default_on_admitted": bool(arelle_cutover_default_on),
        "superseded_by_default_on_runtime": bool(arelle_cutover_default_on),
        "live_network_default_off": bool(live_network_default_off),
        "value_reveal_default_off": bool(value_reveal_default_off),
        "controlled_value_reveal_submit_default_off": bool(controlled_submit_default_off),
    }


def runtime_posture_criterion_passed(posture: Mapping[str, Any]) -> bool:
    return bool(posture.get("config_safety_defaults_off"))


def runtime_posture_criterion_evidence(posture: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "config_defaults_off": bool(posture.get("config_defaults_off")),
        "config_safety_defaults_off": bool(posture.get("config_safety_defaults_off")),
        "arelle_cutover_default_on_admitted": bool(posture.get("arelle_cutover_default_on_admitted")),
        "superseded_by_default_on_runtime": bool(posture.get("superseded_by_default_on_runtime")),
        "live_network_default_off": bool(posture.get("live_network_default_off")),
        "value_reveal_default_off": bool(posture.get("value_reveal_default_off")),
        "controlled_value_reveal_submit_default_off": bool(
            posture.get("controlled_value_reveal_submit_default_off")
        ),
    }


def _settings_field_defaults(source_root: Path) -> dict[str, Any]:
    config_path = source_root / "backend" / "app" / "core" / "config.py"
    if _same_file(source_root, ROOT):
        try:
            from app.core.config import Settings  # noqa: PLC0415

            return {
                name: field.default
                for name, field in Settings.model_fields.items()
                if name in POSTURE_FIELDS
            }
        except Exception:
            pass
    if not config_path.exists():
        return {}
    return _settings_field_defaults_from_text(config_path.read_text(encoding="utf-8"))


def _settings_field_defaults_from_text(config_text: str) -> dict[str, bool]:
    defaults: dict[str, bool] = {}
    for field in POSTURE_FIELDS:
        match = re.search(
            rf"{re.escape(field)}:\s*bool\s*=\s*Field\(\s*default=(True|False)",
            config_text,
        )
        if match:
            defaults[field] = match.group(1) == "True"
    return defaults


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False
