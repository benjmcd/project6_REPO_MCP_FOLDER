"""Run strict-parser cases normally and verify them in a fresh guarded child."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import nrc_strict_cases as cases


_GUARDED_CHILD_ENV = "PROJECT6_NRC_STRICT_GUARDED_CHILD"
_SUPPORT_FILE = Path(cases.__file__).resolve()
_PARENT_CASES: dict[str, Any] = {
    name: value
    for name, value in vars(cases).items()
    if name.startswith("test_") and bool(getattr(value, "__test__", True))
}
globals().update(_PARENT_CASES)


def test_full_strict_subset_passes_in_fresh_guarded_child() -> None:
    backend = Path(__file__).resolve().parents[1]
    child_env = os.environ.copy()
    child_env[_GUARDED_CHILD_ENV] = "1"
    existing_pythonpath = child_env.get("PYTHONPATH")
    child_env["PYTHONPATH"] = (
        str(backend)
        if not existing_pythonpath
        else f"{backend}{os.pathsep}{existing_pythonpath}"
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(_SUPPORT_FILE),
            "-q",
            "-rA",
        ],
        check=False,
        cwd=backend,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, (
        f"guarded child failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    passed = re.search(r"(\d+) passed", completed.stdout)
    skipped = re.search(r"(\d+) skipped", completed.stdout)
    assert passed is not None, completed.stdout
    assert skipped is None, completed.stdout
    assert int(passed.group(1)) == 29
    assert (
        "PASSED tests/nrc_strict_cases.py::test_frozen_profile_constants_are_exact"
        in completed.stdout
    )
    assert (
        "PASSED tests/nrc_strict_cases.py::test_guarded_child_network_denial_self_probe"
        in completed.stdout
    )
