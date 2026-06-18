from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "tools" / "sec-xbrl-arelle-provision.py"


def _helper_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_arelle_provision", HELPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_arelle_provisioning_declares_pinned_packages_with_provenance() -> None:
    module = _helper_module()

    assert module.ARELLE_PACKAGE == "arelle-release"
    assert module.ARELLE_VERSION == "2.41.3"
    specs = module.taxonomy_specs()

    assert [spec["id"] for spec in specs] == [
        "fasb-us-gaap-2025",
        "fasb-srt-2025",
    ]
    assert all(spec["version"] == "2025" for spec in specs)
    assert {spec["sha256"] for spec in specs} == {
        "a3b835925ad74030eb5be865a26d7dfe44013081c4ab7204b6122316a685fff4",
        "aad1daeb4bdfe3057f4ed81482c06130f873a59fa7fce5193c5731f93b1fef88",
    }
    assert all(spec["url"].startswith("https://xbrl.fasb.org/") for spec in specs)
    assert all(spec["source"] for spec in specs)


def test_sec_xbrl_arelle_provisioning_fails_closed_without_downloaded_taxonomies(tmp_path: Path) -> None:
    module = _helper_module()

    report = module.build_report(
        taxonomy_dir=tmp_path / "taxonomy",
        cache_dir=tmp_path / "cache",
        download=False,
        load_with_arelle=False,
    )

    assert report["schema_id"] == "tools.sec_xbrl_arelle_provision.v1"
    assert report["ready"] is False
    assert "taxonomy_package_missing" in report["blocked_reasons"]
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
    assert report["non_goals_preserved"]["sidecar_invoked"] is False
    assert report["non_goals_preserved"]["runtime_defaults_changed"] is False
