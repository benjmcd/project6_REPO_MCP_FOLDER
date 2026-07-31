from __future__ import annotations

import json
import os
import re
import socket
import sys
import warnings
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import UUID


_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
_BACKEND = _ROOT / "backend"
_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_FALSE_VALUES = frozenset(("", "0", "false", "no", "off"))
_TRUE_VALUES = frozenset(("1", "true", "yes", "on"))
_AUTHORITY_VARIABLES = (
    "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
    "CONNECTOR_SCIENCEBASE_GRANT_PATH",
    "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    "CONNECTOR_NRC_APS_GRANT_PATH",
    "CONNECTOR_NRC_APS_GRANT_SHA256",
)
_OPTIONS = {
    "--campaign-id": "campaign_id",
    "--campaign-fingerprint": "campaign_fingerprint",
}
_BLOCKING_DEPENDENCIES = [
    "tracked_external_s3_clause_5_clearance",
    "privileged_dual_live_runner",
]
_NONCLAIMS = [
    "no campaign evidence evaluated",
    "no connector run executed",
    "no live acquisition performed",
    "no Layer 3 continuity verdict",
    "no package or handoff verdict",
    "no production readiness claim",
]
_LOW_LEVEL_INSTALLED = False
_REQUESTS_INSTALLED = False


class DualLiveNetworkDenied(OSError):
    def __init__(self) -> None:
        self.code = "dual_live_network_denied"
        super().__init__(self.code)


def _deny_network(*_args: object, **_kwargs: object) -> None:
    raise DualLiveNetworkDenied


_LOW_LEVEL_HOOKS = (
    (socket.socket, "connect"),
    (socket.socket, "connect_ex"),
    (socket.socket, "bind"),
    (socket.socket, "sendto"),
    (socket, "create_connection"),
    (socket, "getaddrinfo"),
    (socket, "gethostbyname"),
    (socket, "gethostbyname_ex"),
    (socket, "gethostbyaddr"),
    (socket, "getnameinfo"),
    (socket, "getfqdn"),
)


def _install_low_level_guard() -> None:
    global _LOW_LEVEL_INSTALLED

    if _LOW_LEVEL_INSTALLED:
        if not all(getattr(owner, name) is _deny_network for owner, name in _LOW_LEVEL_HOOKS):
            raise RuntimeError("network guard changed")
        return

    for owner, name in _LOW_LEVEL_HOOKS:
        setattr(owner, name, _deny_network)
    if not all(getattr(owner, name) is _deny_network for owner, name in _LOW_LEVEL_HOOKS):
        raise RuntimeError("network guard incomplete")
    _LOW_LEVEL_INSTALLED = True


def _install_network_guard() -> None:
    global _REQUESTS_INSTALLED

    sys.dont_write_bytecode = True
    _install_low_level_guard()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import requests

    request_hooks = (
        (requests.api, "request"),
        (requests, "request"),
        (requests.sessions.Session, "request"),
        (requests.sessions.Session, "send"),
        (requests.adapters.HTTPAdapter, "send"),
    )
    if _REQUESTS_INSTALLED:
        if not all(getattr(owner, name) is _deny_network for owner, name in request_hooks):
            raise RuntimeError("requests guard changed")
        return

    for owner, name in request_hooks:
        setattr(owner, name, _deny_network)
    if not all(getattr(owner, name) is _deny_network for owner, name in request_hooks):
        raise RuntimeError("requests guard incomplete")
    if requests.Session.request is not _deny_network or requests.Session.send is not _deny_network:
        raise RuntimeError("requests aliases unguarded")
    _REQUESTS_INSTALLED = True


def _forbidden_module_loaded() -> bool:
    for name in sys.modules:
        if name in {"app.core.config", "app.db.session", "sqlalchemy"}:
            return True
        if name.startswith("sqlalchemy."):
            return True
        if name.startswith("app.") and "connector" in name:
            return True
    return False


def _emit(payload: Mapping[str, Any]) -> None:
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write(line + "\n")


def _emit_refusal(code: str) -> int:
    _emit(
        {
            "code": code,
            "fresh_live": False,
            "schema_id": "project6.dual_live_gate_refusal.v1",
            "status": "REFUSED",
        }
    )
    return 2


def _environment_refusal(environ: Mapping[str, str]) -> str | None:
    raw_flag = environ.get("CONNECTOR_LIVE_EGRESS_ENABLED", "")
    if not isinstance(raw_flag, str):
        return "dual_live_egress_flag_invalid"
    normalized = raw_flag.casefold()
    if normalized not in _FALSE_VALUES | _TRUE_VALUES:
        return "dual_live_egress_flag_invalid"
    if normalized in _TRUE_VALUES:
        return "dual_live_egress_enabled"
    if any(environ.get(name, "") != "" for name in _AUTHORITY_VARIABLES):
        return "dual_live_send_authority_environment_present"
    return None


def _valid_campaign_id(value: str) -> bool:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _parse_arguments(argv: Sequence[str]) -> tuple[str | None, str | None, str | None]:
    values: dict[str, str | None] = {
        "campaign_id": None,
        "campaign_fingerprint": None,
    }
    seen: set[str] = set()
    structural_error = False
    index = 0

    while index < len(argv):
        token = argv[index]
        field = _OPTIONS.get(token)
        if field is None or field in seen:
            structural_error = True
            index += 1
            continue
        seen.add(field)
        if index + 1 >= len(argv):
            index += 1
            continue
        candidate = argv[index + 1]
        if candidate in _OPTIONS:
            index += 1
            continue
        if candidate.startswith("--"):
            structural_error = True
            index += 2
            continue
        values[field] = candidate
        index += 2

    if structural_error:
        return None, None, "dual_live_arguments_invalid"
    campaign_id = values["campaign_id"]
    campaign_fingerprint = values["campaign_fingerprint"]
    if campaign_id is None:
        return None, None, "dual_live_campaign_id_missing"
    if not _valid_campaign_id(campaign_id):
        return None, None, "dual_live_campaign_id_invalid"
    if campaign_fingerprint is None:
        return None, None, "dual_live_campaign_fingerprint_missing"
    if not _LOWERCASE_SHA256.fullmatch(campaign_fingerprint):
        return None, None, "dual_live_campaign_fingerprint_invalid"
    return campaign_id, campaign_fingerprint, None


class _NoAccess:
    def __getattribute__(self, name: str) -> object:
        raise RuntimeError(f"reserved dependency accessed: {name}")


def _evaluate(*, campaign_id: str, campaign_fingerprint: str) -> dict[str, Any]:
    backend = str(_BACKEND)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.services.dual_live_evaluator import evaluate_dual_live_proof

    return evaluate_dual_live_proof(
        _NoAccess(),
        campaign_id=campaign_id,
        expected_campaign_fingerprint=campaign_fingerprint,
        settings=_NoAccess(),
    )


def _expected_report(campaign_id: str, campaign_fingerprint: str) -> dict[str, Any]:
    return {
        "schema_id": "project6.dual_live_evaluation.v1",
        "campaign_id": campaign_id,
        "expected_campaign_fingerprint": campaign_fingerprint,
        "status": "INDETERMINATE",
        "fresh_live": False,
        "evaluation_complete": False,
        "code": "tracked_s3_clearance_and_privileged_runner_required",
        "blocking_dependencies": list(_BLOCKING_DEPENDENCIES),
        "validated_surfaces": [],
        "nonclaims": list(_NONCLAIMS),
    }


def _report_is_exact(
    report: object,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> bool:
    expected = _expected_report(campaign_id, campaign_fingerprint)
    if type(report) is not dict:
        return False
    if list(report) != list(expected) or report != expected:
        return False
    return (
        report["fresh_live"] is False
        and report["evaluation_complete"] is False
        and type(report["blocking_dependencies"]) is list
        and type(report["validated_surfaces"]) is list
        and type(report["nonclaims"]) is list
    )


def main(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    sys.dont_write_bytecode = True
    arguments = list(sys.argv[1:] if argv is None else argv)
    environment = os.environ if environ is None else environ

    try:
        _install_low_level_guard()
    except Exception:
        return _emit_refusal("dual_live_gate_internal_error")

    environment_error = _environment_refusal(environment)
    if environment_error is not None:
        return _emit_refusal(environment_error)

    campaign_id, campaign_fingerprint, argument_error = _parse_arguments(arguments)
    if argument_error is not None:
        return _emit_refusal(argument_error)
    if campaign_id is None or campaign_fingerprint is None:
        return _emit_refusal("dual_live_gate_internal_error")

    try:
        if _forbidden_module_loaded():
            raise RuntimeError("dirty process")
        _install_network_guard()
        report = _evaluate(
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        )
        if _forbidden_module_loaded():
            raise RuntimeError("forbidden import")
        if not _report_is_exact(
            report,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        ):
            raise RuntimeError("evaluation contract drift")
        _emit(report)
    except Exception:
        return _emit_refusal("dual_live_gate_internal_error")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
