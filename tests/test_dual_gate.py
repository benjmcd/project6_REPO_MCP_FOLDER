from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "dual_live_gate.py"
PROJECT6 = ROOT / "project6.ps1"
FROZEN_PLAN = ROOT / "docs" / "superpowers" / "plans" / "2026-07-29-dual-live-proof.md"
PILOT_TEST = ROOT / "backend" / "tests" / "test_layer3_connector_vertical_loop.py"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
CAMPAIGN_ID = "123e4567-e89b-42d3-a456-426614174000"
CAMPAIGN_FINGERPRINT = "a" * 64
EXPECTED_FROZEN_PLAN_BLOB = "68f740af86dc7d1ac2227f81a6ea28e7e2c7458f"
TASK8_IMPLEMENTATION_BASE = "49cc7e20d1a4dcd6f84df076aafc18d0cd03b876"
FORBIDDEN_REQUIRED_ALIASES = (
    "DUAL_LIVE_POSTRUN",
    "DUAL_LIVE_ATTESTATION",
    "DUAL_LIVE_ISSUER",
)
FORBIDDEN_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_postrun_evidence.py",
    "tools/dual_live_issue.py",
)
ALLOWED_NEW_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
    "backend/app/services/dual_live_windows.py",
    "tools/dual_live_run.py",
)
FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
)
ALLOWED_CHANGED_PRODUCTION_PATHS = frozenset(
    (
        *ALLOWED_NEW_PRODUCTION_PATHS,
        "backend/app/services/connector_egress_authorization.py",
        "backend/app/services/connector_egress_transport.py",
        "backend/app/services/connector_egress_arming.py",
        "backend/app/services/connector_campaign_log_capture.py",
        "backend/app/services/dual_live_evaluator.py",
        "tools/dual_live_gate.py",
        "project6.ps1",
    )
)
AUTHORITY_VARIABLES = (
    "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
    "CONNECTOR_SCIENCEBASE_GRANT_PATH",
    "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    "CONNECTOR_NRC_APS_GRANT_PATH",
    "CONNECTOR_NRC_APS_GRANT_SHA256",
)
EXPECTED_REPORT = {
    "schema_id": "project6.dual_live_evaluation.v1",
    "campaign_id": CAMPAIGN_ID,
    "expected_campaign_fingerprint": CAMPAIGN_FINGERPRINT,
    "status": "INDETERMINATE",
    "fresh_live": False,
    "evaluation_complete": False,
    "code": "tracked_s3_clearance_and_privileged_runner_required",
    "blocking_dependencies": [
        "tracked_external_s3_clause_5_clearance",
        "privileged_dual_live_runner",
    ],
    "validated_surfaces": [],
    "nonclaims": [
        "no campaign evidence evaluated",
        "no connector run executed",
        "no live acquisition performed",
        "no Layer 3 continuity verdict",
        "no package or handoff verdict",
        "no production readiness claim",
    ],
}


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _is_production_path(path: str) -> bool:
    return (
        path == "project6.ps1"
        or path.startswith("backend/app/")
        or path.startswith("tools/")
    )


def _changed_production_surface() -> tuple[frozenset[str], frozenset[str]]:
    diff_lines = _git_output(
        "diff",
        "--name-status",
        "--diff-filter=ACMRD",
        TASK8_IMPLEMENTATION_BASE,
    ).splitlines()
    untracked = _git_output(
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        "backend/app",
        "tools",
        "project6.ps1",
    ).splitlines()
    changed: set[str] = set()
    deleted: set[str] = set()
    for line in diff_lines:
        fields = line.split("\t")
        status = fields[0]
        if status.startswith("R"):
            old_path, new_path = fields[1:]
            if _is_production_path(old_path):
                changed.add(old_path)
                deleted.add(old_path)
            if _is_production_path(new_path):
                changed.add(new_path)
        elif status.startswith("C"):
            new_path = fields[-1]
            if _is_production_path(new_path):
                changed.add(new_path)
        else:
            path = fields[-1]
            if _is_production_path(path):
                changed.add(path)
                if status == "D":
                    deleted.add(path)
    changed.update(path for path in untracked if _is_production_path(path))
    return frozenset(changed), frozenset(deleted)


def _changed_production_paths() -> frozenset[str]:
    changed, _ = _changed_production_surface()
    return changed


def _deleted_production_paths() -> frozenset[str]:
    _, deleted = _changed_production_surface()
    return deleted


def _a_scoped_production_surface_is_allowed() -> bool:
    changed, deleted = _changed_production_surface()
    return not deleted and changed <= ALLOWED_CHANGED_PRODUCTION_PATHS


def _tracked_source_text() -> str:
    paths = ALLOWED_CHANGED_PRODUCTION_PATHS | _changed_production_paths()
    return "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in sorted(paths)
        if (ROOT / path).is_file()
    )


def _git_blob_sha(path: Path) -> str:
    return _git_output("hash-object", str(path.relative_to(ROOT)))


def _pilot_seal() -> str:
    tree = ast.parse(PILOT_TEST.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "FIXTURE_SOURCE_FILE_GIT_BLOB":
            value = ast.literal_eval(node.value)
            assert isinstance(value, str)
            return value
    raise AssertionError("pilot seal constant is missing")


def test_a_scoped_build_adds_no_attestation_index_or_env_contract() -> None:
    tracked = _tracked_source_text()
    assert all(alias not in tracked for alias in FORBIDDEN_REQUIRED_ALIASES)
    assert all(not (ROOT / path).exists() for path in FORBIDDEN_PRODUCTION_PATHS)


def test_a_scoped_changed_production_surface_is_allowlisted() -> None:
    assert _a_scoped_production_surface_is_allowed()


def test_deleted_production_path_is_detected_and_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deleted = "backend/app/services/dual_live_runtime.py"

    def fake_git_output(*args: str) -> str:
        if args and args[0] == "diff":
            return f"D\t{deleted}"
        return ""

    monkeypatch.setattr(sys.modules[__name__], "_git_output", fake_git_output)

    assert deleted in _changed_production_paths()
    assert deleted in _deleted_production_paths()
    assert not _a_scoped_production_surface_is_allowed()


def test_frozen_and_sealed_authority_files_are_unchanged() -> None:
    assert _git_blob_sha(FROZEN_PLAN) == EXPECTED_FROZEN_PLAN_BLOB
    assert _pilot_seal() == "b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2"


def test_a_scoped_build_has_required_runtime_units() -> None:
    assert all(
        (ROOT / path).is_file() for path in FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS
    )


def _compact(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
        + os.linesep.encode()
    )


def _refusal(code: str) -> bytes:
    return _compact(
        {
            "code": code,
            "fresh_live": False,
            "schema_id": "project6.dual_live_gate_refusal.v1",
            "status": "REFUSED",
        }
    )


def _captured(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True) + "\n"


def _captured_refusal(code: str) -> str:
    return _refusal(code).decode().removesuffix(os.linesep) + "\n"


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("CONNECTOR_LIVE_EGRESS_ENABLED", None)
    env.pop("DUAL_LIVE_CAMPAIGN_ID", None)
    env.pop("DUAL_LIVE_CAMPAIGN_FINGERPRINT", None)
    env.pop("PYTHONPATH", None)
    for name in AUTHORITY_VARIABLES:
        env.pop(name, None)
    return env


def _valid_args() -> list[str]:
    return [
        "--campaign-id",
        CAMPAIGN_ID,
        "--campaign-fingerprint",
        CAMPAIGN_FINGERPRINT,
    ]


def _run_gate(
    tmp_path: Path,
    *,
    args: list[str] | None = None,
    env_updates: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = _clean_env()
    if env_updates:
        env.update(env_updates)
    return subprocess.run(
        [sys.executable, "-B", str(GATE), *(args if args is not None else _valid_args())],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
    )


def _run_powershell(
    tmp_path: Path,
    *,
    action: str,
    env_updates: dict[str, str] | None = None,
    empty_path: bool = False,
    action_args: list[str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    if POWERSHELL is None:
        raise AssertionError("PowerShell is required for the dual-live gate contract")
    env = _clean_env()
    if env_updates:
        env.update(env_updates)
    if empty_path:
        env["PATH"] = ""
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT6),
            "-Action",
            action,
            "-PythonVersion",
            "3.11",
            *(action_args or []),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
    )


def test_valid_gate_is_exact_inert_and_cwd_independent(tmp_path: Path) -> None:
    completed = _run_gate(
        tmp_path,
        env_updates={"CONNECTOR_LIVE_EGRESS_ENABLED": "OFF", "PYTHONPATH": ""},
    )

    assert completed.returncode == 2
    assert completed.stdout == _compact(EXPECTED_REPORT)
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("false_value", ["", "0", "false", "FALSE", "no", "NO", "off", "OFF"])
def test_false_egress_values_are_accepted_without_stripping(
    tmp_path: Path, false_value: str
) -> None:
    completed = _run_gate(
        tmp_path,
        env_updates={"CONNECTOR_LIVE_EGRESS_ENABLED": false_value},
    )

    assert completed.returncode == 2
    assert completed.stdout == _compact(EXPECTED_REPORT)
    assert completed.stderr == b""


@pytest.mark.parametrize("true_value", ["1", "true", "TRUE", "yes", "YES", "on", "ON"])
def test_true_egress_values_refuse_before_authority_or_arguments(
    tmp_path: Path, true_value: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=["--unknown"],
        env_updates={
            "CONNECTOR_LIVE_EGRESS_ENABLED": true_value,
            AUTHORITY_VARIABLES[0]: "secret-authority",
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_egress_enabled")
    assert completed.stderr == b""
    assert b"secret-authority" not in completed.stdout


@pytest.mark.parametrize("invalid_value", [" false ", " true ", "2", "enabled", "\t"])
def test_invalid_egress_value_has_total_precedence(
    tmp_path: Path, invalid_value: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=["--unknown"],
        env_updates={
            "CONNECTOR_LIVE_EGRESS_ENABLED": invalid_value,
            AUTHORITY_VARIABLES[0]: "secret-authority",
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_egress_flag_invalid")
    assert completed.stderr == b""
    assert invalid_value.encode() not in completed.stdout


@pytest.mark.parametrize("authority_name", AUTHORITY_VARIABLES)
def test_each_nonempty_authority_variable_refuses_without_disclosure(
    tmp_path: Path, authority_name: str
) -> None:
    secret = f"secret-{authority_name}"
    completed = _run_gate(
        tmp_path,
        args=["--unknown"],
        env_updates={authority_name: secret},
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_send_authority_environment_present")
    assert completed.stderr == b""
    assert authority_name.encode() not in completed.stdout
    assert secret.encode() not in completed.stdout


def test_whitespace_authority_is_present_and_empty_authority_is_absent(
    tmp_path: Path,
) -> None:
    present = _run_gate(tmp_path, env_updates={AUTHORITY_VARIABLES[0]: " "})
    absent = _run_gate(tmp_path, env_updates={AUTHORITY_VARIABLES[0]: ""})

    assert present.stdout == _refusal("dual_live_send_authority_environment_present")
    assert absent.stdout == _compact(EXPECTED_REPORT)


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (["--help"], "dual_live_arguments_invalid"),
        (["--"], "dual_live_arguments_invalid"),
        (["positional"], "dual_live_arguments_invalid"),
        ([f"--campaign-id={CAMPAIGN_ID}"], "dual_live_arguments_invalid"),
        (["--campaign-i", CAMPAIGN_ID], "dual_live_arguments_invalid"),
        (["--unknown", "value"], "dual_live_arguments_invalid"),
        (
            [
                "--campaign-id",
                CAMPAIGN_ID,
                "--campaign-id",
                CAMPAIGN_ID,
                "--campaign-fingerprint",
                CAMPAIGN_FINGERPRINT,
            ],
            "dual_live_arguments_invalid",
        ),
        ([], "dual_live_campaign_id_missing"),
        (["--campaign-fingerprint", CAMPAIGN_FINGERPRINT], "dual_live_campaign_id_missing"),
        (["--campaign-id"], "dual_live_campaign_id_missing"),
        (
            ["--campaign-id", "--campaign-fingerprint", CAMPAIGN_FINGERPRINT],
            "dual_live_campaign_id_missing",
        ),
        (
            ["--campaign-id", "", "--campaign-fingerprint", CAMPAIGN_FINGERPRINT],
            "dual_live_campaign_id_invalid",
        ),
        (["--campaign-id", CAMPAIGN_ID], "dual_live_campaign_fingerprint_missing"),
        (
            ["--campaign-id", CAMPAIGN_ID, "--campaign-fingerprint"],
            "dual_live_campaign_fingerprint_missing",
        ),
        (
            ["--campaign-id", CAMPAIGN_ID, "--campaign-fingerprint", ""],
            "dual_live_campaign_fingerprint_invalid",
        ),
    ],
)
def test_strict_argument_grammar_and_field_refusals(
    tmp_path: Path, args: list[str], code: str
) -> None:
    completed = _run_gate(tmp_path, args=args)

    assert completed.returncode == 2
    assert completed.stdout == _refusal(code)
    assert completed.stderr == b""


@pytest.mark.parametrize(
    "campaign_id",
    [
        CAMPAIGN_ID.upper(),
        "123e4567-e89b-12d3-a456-426614174000",
        "{123e4567-e89b-42d3-a456-426614174000}",
        "123e4567e89b42d3a456426614174000",
    ],
)
def test_cli_rejects_noncanonical_or_non_v4_uuid_forms(
    tmp_path: Path, campaign_id: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=[
            "--campaign-id",
            campaign_id,
            "--campaign-fingerprint",
            CAMPAIGN_FINGERPRINT,
        ],
    )

    assert completed.stdout == _refusal("dual_live_campaign_id_invalid")


def test_invalid_id_precedes_missing_fingerprint(tmp_path: Path) -> None:
    completed = _run_gate(tmp_path, args=["--campaign-id", "not-a-uuid"])

    assert completed.stdout == _refusal("dual_live_campaign_id_invalid")


@pytest.mark.parametrize(
    "campaign_fingerprint",
    ["A" * 64, "a" * 63, "a" * 65, ("a" * 63) + "g"],
)
def test_cli_rejects_noncanonical_fingerprint(
    tmp_path: Path, campaign_fingerprint: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=[
            "--campaign-id",
            CAMPAIGN_ID,
            "--campaign-fingerprint",
            campaign_fingerprint,
        ],
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_campaign_fingerprint_invalid")
    assert completed.stderr == b""


def test_import_is_side_effect_free() -> None:
    probe = f"""
import importlib.util
import io
import json
import socket
import sys
from contextlib import redirect_stderr, redirect_stdout
before = (socket.socket.connect, socket.getaddrinfo, sys.dont_write_bytecode)
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
stdout = io.StringIO()
stderr = io.StringIO()
with redirect_stdout(stdout), redirect_stderr(stderr):
    spec.loader.exec_module(module)
after = (socket.socket.connect, socket.getaddrinfo, sys.dont_write_bytecode)
print(json.dumps({{
    "guard_unchanged": before == after,
    "stdout": stdout.getvalue(),
    "stderr": stderr.getvalue(),
    "requests_loaded": "requests" in sys.modules,
    "app_loaded": any(name == "app" or name.startswith("app.") for name in sys.modules),
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "guard_unchanged": True,
        "stdout": "",
        "stderr": "",
        "requests_loaded": False,
        "app_loaded": False,
    }
    assert completed.stderr == ""


def test_early_refusal_installs_only_low_level_guard() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import socket
import sys
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main(["--unknown"], {{}})
try:
    socket.getaddrinfo("example.invalid", 443)
except OSError as exc:
    denial = [type(exc).__name__, getattr(exc, "code", None), str(exc)]
else:
    denial = None
print(json.dumps({{
    "result": result,
    "output": output.getvalue(),
    "denial": denial,
    "requests_loaded": "requests" in sys.modules,
    "evaluator_loaded": "app.services.dual_live_evaluator" in sys.modules,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_arguments_invalid")
    assert payload["denial"] == [
        "DualLiveNetworkDenied",
        "dual_live_network_denied",
        "dual_live_network_denied",
    ]
    assert payload["requests_loaded"] is False
    assert payload["evaluator_loaded"] is False
    assert completed.stderr == ""


def test_full_guard_is_idempotent_and_denies_all_required_entrypoints() -> None:
    probe = f"""
import importlib.util
import json
import socket
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._install_network_guard()
import requests
identities = (socket.socket.connect, socket.getaddrinfo, requests.Session.send)
module._install_network_guard()
idempotent = identities == (socket.socket.connect, socket.getaddrinfo, requests.Session.send)
sock = socket.socket()
session = requests.Session()
adapter = requests.adapters.HTTPAdapter()
probes = [
    lambda: sock.connect(("127.0.0.1", 1)),
    lambda: sock.connect_ex(("127.0.0.1", 1)),
    lambda: sock.bind(("127.0.0.1", 0)),
    lambda: sock.sendto(b"x", ("127.0.0.1", 1)),
    lambda: socket.create_connection(("127.0.0.1", 1)),
    lambda: socket.getaddrinfo("example.invalid", 443),
    lambda: socket.gethostbyname("example.invalid"),
    lambda: socket.gethostbyname_ex("example.invalid"),
    lambda: socket.gethostbyaddr("127.0.0.1"),
    lambda: socket.getnameinfo(("127.0.0.1", 1), 0),
    lambda: socket.getfqdn("example.invalid"),
    lambda: requests.api.request("GET", "https://example.invalid"),
    lambda: requests.request("GET", "https://example.invalid"),
    lambda: session.request("GET", "https://example.invalid"),
    lambda: session.send(requests.Request("GET", "https://example.invalid").prepare()),
    lambda: adapter.send(requests.Request("GET", "https://example.invalid").prepare()),
]
denials = []
for invoke in probes:
    try:
        invoke()
    except OSError as exc:
        denials.append([type(exc).__name__, getattr(exc, "code", None), str(exc)])
    else:
        denials.append(None)
sock.close()
session.close()
adapter.close()
print(json.dumps({{"idempotent": idempotent, "denials": denials}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["idempotent"] is True
    assert payload["denials"] == [
        ["DualLiveNetworkDenied", "dual_live_network_denied", "dual_live_network_denied"]
    ] * 16
    assert completed.stderr == ""


def test_valid_main_imports_only_inert_app_surface() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import sys
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
forbidden = [
    name for name in sys.modules
    if name in ("app.core.config", "app.db.session")
    or name == "sqlalchemy"
    or name.startswith("sqlalchemy.")
    or (name.startswith("app.") and "connector" in name)
]
print(json.dumps({{"result": result, "output": output.getvalue(), "forbidden": forbidden}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured(EXPECTED_REPORT)
    assert payload["forbidden"] == []
    assert completed.stderr == ""


@pytest.mark.parametrize(
    "forbidden_module",
    [
        "app.core.config",
        "app.db.session",
        "app.services.some_connector",
        "sqlalchemy",
    ],
)
def test_valid_main_rejects_preloaded_forbidden_modules(
    forbidden_module: str,
) -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import sys
import types
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules[{forbidden_module!r}] = types.ModuleType({forbidden_module!r})
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert forbidden_module not in payload["output"]
    assert completed.stderr == ""


def test_guard_reverification_detects_replacement() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import socket
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._install_low_level_guard()
socket.getaddrinfo = lambda *args, **kwargs: []
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert completed.stderr == ""


def test_report_drift_is_internal_refusal() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._evaluate = lambda **kwargs: {{"status": "PASS"}}
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert completed.stderr == ""


def test_unexpected_valid_path_failure_is_secret_safe() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
secret = "must-not-escape"
def fail_guard():
    raise RuntimeError(secret)
module._install_network_guard = fail_guard
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert "must-not-escape" not in payload["output"]
    assert completed.stderr == ""


def test_run_action_is_exact_refusal_without_child_or_side_effect(
    tmp_path: Path,
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="run-dual-live-proof",
        env_updates={
            "DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID,
            "DUAL_LIVE_CAMPAIGN_FINGERPRINT": CAMPAIGN_FINGERPRINT,
        },
        empty_path=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == _compact(
        {
            "action": "run-dual-live-proof",
            "code": "tracked_s3_clearance_and_privileged_runner_required",
            "fresh_live": False,
            "schema_id": "project6.dual_live_run_refusal.v1",
            "status": "REFUSED",
        }
    )
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("env_updates", "code"),
    [
        ({}, "dual_live_campaign_id_missing"),
        ({"DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID}, "dual_live_campaign_fingerprint_missing"),
    ],
)
def test_validate_action_prechecks_missing_environment_without_child(
    tmp_path: Path, env_updates: dict[str, str], code: str
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="validate-dual-live-proof",
        env_updates=env_updates,
        empty_path=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal(code)
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("action", ["run-dual-live-proof", "validate-dual-live-proof"])
def test_powershell_actions_reject_remaining_arguments(
    tmp_path: Path, action: str
) -> None:
    completed = _run_powershell(
        tmp_path,
        action=action,
        env_updates={
            "DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID,
            "DUAL_LIVE_CAMPAIGN_FINGERPRINT": CAMPAIGN_FINGERPRINT,
        },
        empty_path=True,
        action_args=["unexpected"],
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_arguments_invalid")
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


def test_validate_action_directly_preserves_gate_output_exit_and_cwd(
    tmp_path: Path,
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="validate-dual-live-proof",
        env_updates={
            "DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID,
            "DUAL_LIVE_CAMPAIGN_FINGERPRINT": CAMPAIGN_FINGERPRINT,
            "CONNECTOR_LIVE_EGRESS_ENABLED": "off",
            "PYTHONPATH": "",
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == _compact(EXPECTED_REPORT)
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


def test_validate_action_contains_mandated_direct_launcher_shape() -> None:
    source = PROJECT6.read_text(encoding="utf-8")
    required = """Push-Location $RepoRoot
        try {
            & py "-$PythonVersion" -B .\\tools\\dual_live_gate.py --campaign-id $env:DUAL_LIVE_CAMPAIGN_ID --campaign-fingerprint $env:DUAL_LIVE_CAMPAIGN_FINGERPRINT
            $DualLiveGateExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        exit $DualLiveGateExitCode"""

    assert required in source


def test_powershell_declares_each_dual_live_action_once() -> None:
    source = PROJECT6.read_text(encoding="utf-8")
    validate_set = source.split("[ValidateSet(", 1)[1].split(")]", 1)[0]

    assert validate_set.count('"run-dual-live-proof"') == 1
    assert validate_set.count('"validate-dual-live-proof"') == 1
    assert source.count('\n    "run-dual-live-proof" {') == 1
    assert source.count('\n    "validate-dual-live-proof" {') == 1
