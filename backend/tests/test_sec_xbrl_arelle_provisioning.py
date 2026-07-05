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
        "sec-2025",
    ]
    assert [spec["kind"] for spec in specs] == [
        "arelle_taxonomy_package",
        "arelle_taxonomy_package",
        "offline_cache_archive",
    ]
    assert all(spec["version"] == "2025" for spec in specs)
    assert {spec["sha256"] for spec in specs} == {
        "a3b835925ad74030eb5be865a26d7dfe44013081c4ab7204b6122316a685fff4",
        "aad1daeb4bdfe3057f4ed81482c06130f873a59fa7fce5193c5731f93b1fef88",
        "6a963051af02ff458e02669549bd55f9d547281724f3b4e053cb0157be8121e4",
    }
    assert {Path(spec["url"]).name for spec in specs} == {
        "us-gaap-2025.zip",
        "srt-2025.zip",
        "2025.zip",
    }
    assert all(spec["source"] for spec in specs)


def test_sec_xbrl_arelle_provisioning_declares_operator_verified_historical_pins() -> None:
    module = _helper_module()

    specs = module.taxonomy_specs(years=["2019", "2020", "2021", "2022", "2023", "2024"])
    by_name = {spec["name"]: spec for spec in specs}

    assert by_name["us-gaap-2019.zip"]["url"].endswith("/us-gaap/2019/us-gaap-2019-01-31.zip")
    assert by_name["srt-2021.zip"]["url"].endswith("/srt/2021/srt-2021-01-31.zip")
    assert by_name["us-gaap-2019.zip"]["sha256"] == "16ea8c9f25e61a3d2e824ab917067f787683c9eeff2147cbe3b0463508d1d667"
    assert by_name["us-gaap-2024.zip"]["bytes"] == 7_115_653
    assert by_name["srt-2024.zip"]["sha256"] == "136d16f1bf62ca1966300231b2b399f90631ba703381aeec467e9bec4f3867eb"
    assert by_name["sec-2021.zip"]["url"] == "https://xbrl.sec.gov/2021.zip"
    assert by_name["sec-2024.zip"]["sha256"] == "418477e806d5a2d6b21376a26c01fc373d549dae8d18f223a6ebddf80680bdf0"
    assert all(spec["pinned"] and spec["download_ready"] for spec in specs if not spec.get("unavailable_reason"))


def test_sec_xbrl_arelle_provisioning_reports_2019_2020_sec_cache_as_partial(tmp_path: Path) -> None:
    module = _helper_module()

    specs = module.taxonomy_specs(years=["2019", "2020"])
    report = module.build_report(
        taxonomy_dir=tmp_path / "taxonomy",
        cache_dir=tmp_path / "cache",
        download=False,
        load_with_arelle=False,
        years=["2019", "2020"],
    )

    assert [spec["id"] for spec in specs if spec["kind"] == "offline_cache_archive"] == [
        "sec-2019-unavailable",
        "sec-2020-unavailable",
    ]
    assert all(spec["download_ready"] is False for spec in specs if spec["kind"] == "offline_cache_archive")
    assert report["taxonomy_year_coverage"]["2019"]["partial_coverage"] is True
    assert report["taxonomy_year_coverage"]["2019"]["unavailable_artifact_count"] == 1
    assert report["taxonomy_year_coverage"]["2019"]["pinned_artifact_count"] == 2
    assert report["taxonomy_year_coverage"]["2020"]["partial_coverage"] is True
    assert "taxonomy_year_partial_coverage" in report["blocked_reasons"]


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


def test_sec_xbrl_arelle_provisioning_dry_lists_requested_years_without_downloads(tmp_path: Path) -> None:
    module = _helper_module()

    specs = module.taxonomy_specs(years=["2019", "2025"])
    report = module.build_report(
        taxonomy_dir=tmp_path / "taxonomy",
        cache_dir=tmp_path / "cache",
        download=False,
        load_with_arelle=False,
        years=["2019", "2025"],
    )

    assert sorted({spec["version"] for spec in specs}) == ["2019", "2025"]
    assert report["requested_taxonomy_years"] == ["2019", "2025"]
    assert report["taxonomy_year_coverage"]["2019"]["planned_artifact_count"] == 3
    assert report["taxonomy_year_coverage"]["2025"]["planned_artifact_count"] == 3
    assert report["taxonomy_year_coverage"]["2025"]["pinned_artifact_count"] == 3
    assert report["taxonomy_year_coverage"]["2019"]["partial_coverage"] is True
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
