"""A7 durable proof: REAL Arelle resolves inline-XBRL facts from a committed
synthetic fixture, offline, against the provisioned SEC DEI taxonomy.

This closes a real CI gap: the existing Arelle tests exercise only the helper's
pure functions (package-load logic, URI building, diagnostics) with fakes, and
the sidecar tests mock the Arelle subprocess runner entirely. Nothing else runs
the real Arelle subprocess end-to-end and asserts DTS-resolved facts. That
capability — the heart of the SEC-XBRL fact-authority path that A7 proved on a
real 10-Q — was previously only demonstrated by an operator run, never guarded
in CI.

The test runs only where Arelle 2.41.3 + the provisioned taxonomy/cache are
present (the `sec-xbrl-arelle-provisioning` CI job, which sets
SEC_XBRL_ARELLE_TAXONOMY_PACKAGES / SEC_XBRL_ARELLE_CACHE_DIR). It skips in the
plain backend shards (no Arelle), so it is offline and side-effect-free there.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "tools" / "sec-xbrl-arelle.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sec_xbrl_a7" / "minimal_dei_ixbrl.htm"
ARELLE_VERSION = "2.41.3"
EXPECTED_CONCEPTS = {"dei:DocumentType", "dei:EntityRegistrantName", "dei:AmendmentFlag"}


def _arelle_pinned() -> bool:
    try:
        import importlib.metadata as metadata

        return metadata.version("arelle-release") == ARELLE_VERSION
    except Exception:
        return False


def _taxonomy_packages() -> list[str]:
    raw = os.environ.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", "")
    return [item for item in raw.split(os.pathsep) if item and Path(item).is_file()]


def _cache_dir() -> str:
    candidate = os.environ.get("SEC_XBRL_ARELLE_CACHE_DIR", "")
    return candidate if candidate and Path(candidate).is_dir() else ""


_SKIP_REASON = "requires Arelle 2.41.3 + provisioned SEC taxonomy/cache (runs in the sec-xbrl-arelle-provisioning CI job)"
_RUNNABLE = bool(_arelle_pinned() and _taxonomy_packages() and _cache_dir() and FIXTURE.is_file() and HELPER.is_file())


@pytest.mark.skipif(not _RUNNABLE, reason=_SKIP_REASON)
def test_real_arelle_resolves_dei_facts_offline_from_committed_fixture() -> None:
    cmd = [sys.executable, str(HELPER), "--input", str(FIXTURE)]
    for package in _taxonomy_packages():
        cmd += ["--taxonomy-package", package]
    cmd += ["--cache-dir", _cache_dir(), "--internet-connectivity", "offline", "--max-facts", "100000"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, f"helper failed: {result.stderr or result.stdout}"

    report = json.loads(result.stdout.strip().splitlines()[-1])
    diagnostics = report["diagnostics"]

    # Real Arelle ran as an offline subprocess and resolved every concept from the DTS.
    assert report["arelle_version"] == ARELLE_VERSION
    assert report["taxonomy_network_resolution_enabled"] is False
    assert report["fact_count"] == 3
    assert diagnostics["concept_resolved_from_dts_count"] == 3
    assert diagnostics["concept_dts_unresolved_count"] == 0
    assert diagnostics["model_error_count"] == 0

    facts = report["facts"]
    assert {fact["concept"]["qname"] for fact in facts} >= EXPECTED_CONCEPTS
    assert all(fact["concept"]["resolved_from_dts"] for fact in facts)
