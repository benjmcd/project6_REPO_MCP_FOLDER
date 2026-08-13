"""Non-certified regression check for the owned-child logger-topology freeze.

NOT part of the certified `tests/test_dual_gate.py` count (356) - deliberately a separate
file so the certified figure cited in landed G2 records is unaffected.

Guards the defect fixed by `dual_live_runtime._preload_owned_workload_modules()`: the owned
child freezes its logger topology (tools/dual_live_run.py:432, invoked :883) before dispatching
the phase workloads, which lazily import `app.db.session`. SQLAlchemy creates loggers at import
(sqlalchemy/log.py:53) AND per Engine/Pool instance (:248), and app/db/session.py builds the
engine at module scope, so any workload import after the freeze raised
`dual_live_logger_topology_frozen` - flattened to the opaque `dual_live_run_refused`.

Each check runs in a FRESH interpreter: this test process already has `app.*` and `sqlalchemy`
resident, which is exactly what masks the defect in-process.

The POSITIVE CONTROL is the load-bearing assertion: with the preload disabled the replay MUST
deny. Without it, a future preload gap would pass silently.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

# Full statically-visible post-freeze import surface of BOTH phase workloads
# (dual_live_runtime.py :5373-5381, :5541-5544, :5737-5743, :6556-6557, :6261-6266).
REPLAY_MODULES = (
    "app.db.session",
    "app.models.models",
    "app.schemas.api",
    "app.services.connector_egress_arming",
    "app.services.connector_egress_authorization",
    "app.services.connector_egress_evidence",
    "app.services.connector_egress_transport",
    "app.services.connectors_nrc_adams",
    "app.services.connectors_sciencebase",
    "app.services.connector_campaign_log_capture",
    "app.services.layer3_connector_source_intake",
    "app.services.layer3_origin_continuity",
    "app.services.layer3_workbench",
    "app.services.nrc_aps_phase_b_linkage",
)

_CHILD = r'''
import importlib, json, logging, os, sys
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[1])
preload = sys.argv[2] == "preload"
modules = json.loads(sys.argv[3])

from app.services import dual_live_runtime

if preload:
    dual_live_runtime._preload_owned_workload_modules()

# Apply the freeze's own denial to the same getLogger entry points it patches
# (dual_live_runtime.py:7274-7275, :7326-7352). The full freeze_logger_topology()
# additionally requires the child's pristine pipe-handler topology, which does not
# exist here; the denial semantics are what this regression guards.
deny = dual_live_runtime._deny_logger_topology_mutation
logging.getLogger = deny
logging.Manager.getLogger = deny
logging.Logger.manager.getLogger = deny

denied = []
for name in modules:
    try:
        importlib.import_module(name)
    except BaseException as exc:
        denied.append(name if getattr(exc, "code", None) == "dual_live_logger_topology_frozen"
                      else "%s:%s" % (name, type(exc).__name__))

# Instance-level construction: Engine/Pool loggers are created per instance, not only at import.
try:
    from sqlalchemy import text
    from app.db.session import SessionLocal
    s = SessionLocal()
    s.execute(text("select 1"))
    s.rollback()
    s.close()
except BaseException as exc:
    denied.append("SessionLocal:%s" % (getattr(exc, "code", None) or type(exc).__name__))

print(json.dumps({
    "denied": denied,
    # D1 tripwire: the named residual must NOT be dragged into the credentialed child.
    "analysis_loaded": "app.services.analysis" in sys.modules,
}))
'''


def _run(mode: str, tmp_path: Path) -> dict:
    db = (tmp_path / "regression.db").as_posix()
    env = {
        **{k: v for k, v in __import__("os").environ.items()},
        "DATABASE_URL": f"sqlite:///{db}",
        "STORAGE_DIR": str(tmp_path / "storage"),
        "DEPLOYMENT_MODE": "local",
        "AUTH_OWNER": "none",
        "TRUSTED_PROXY_MODE": "false",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.pop("NRC_ADAMS_APS_SUBSCRIPTION_KEY", None)
    env.pop("CONNECTOR_LIVE_EGRESS_ENABLED", None)
    completed = subprocess.run(
        [sys.executable, "-B", "-c", _CHILD, str(BACKEND), mode, json.dumps(list(REPLAY_MODULES))],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_preload_admits_the_whole_post_freeze_workload_surface(tmp_path: Path) -> None:
    result = _run("preload", tmp_path)
    assert result["denied"] == [], (
        "post-freeze workload imports were denied despite the preload; "
        f"_preload_owned_workload_modules is incomplete: {result['denied']}"
    )


def test_positive_control_without_preload_denies(tmp_path: Path) -> None:
    result = _run("control", tmp_path)
    assert result["denied"], (
        "control run produced no denials - the freeze semantics are not being exercised, "
        "so the preload check above proves nothing"
    )
    assert "app.db.session" in result["denied"]


def test_named_residual_is_not_pulled_into_the_owned_child(tmp_path: Path) -> None:
    # D1 = (a): app.services.analysis (matplotlib/PIL, +29 loggers) is a NAMED residual,
    # deliberately not preloaded. This tripwire fails if it is ever dragged in implicitly.
    assert _run("preload", tmp_path)["analysis_loaded"] is False
