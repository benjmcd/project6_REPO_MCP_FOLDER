from __future__ import annotations

import importlib.util
from pathlib import Path
from zipfile import ZipFile


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


def test_sec_xbrl_arelle_provisioning_declares_operator_verified_2026_pins_without_default_bump() -> None:
    module = _helper_module()

    assert module.DEFAULT_TAXONOMY_YEARS == ("2025",)
    specs = module.taxonomy_specs(years=["2026"])
    by_name = {spec["name"]: spec for spec in specs}

    assert [spec["id"] for spec in specs] == [
        "fasb-us-gaap-2026",
        "fasb-srt-2026",
        "sec-2026",
    ]
    assert by_name["us-gaap-2026.zip"]["url"] == "https://xbrl.fasb.org/us-gaap/2026/us-gaap-2026.zip"
    assert by_name["us-gaap-2026.zip"]["sha256"] == "f4c8b8b5697ba7d825a8614b159611cd25a46640e98a9737cda1e4a672bd4c81"
    assert by_name["us-gaap-2026.zip"]["bytes"] == 7_387_980
    assert by_name["srt-2026.zip"]["url"] == "https://xbrl.fasb.org/srt/2026/srt-2026.zip"
    assert by_name["srt-2026.zip"]["sha256"] == "34dab1ee7a10b9991fee1e17437c278908599ff2258ea3270ef718cab265be05"
    assert by_name["srt-2026.zip"]["bytes"] == 195_234
    assert by_name["sec-2026.zip"]["url"] == "https://xbrl.sec.gov/2026.zip"
    assert by_name["sec-2026.zip"]["sha256"] == "16243a0713f10fb7bebd020cb0da505e2bf4ef180af3e19b8e4cd4ad2a75a6a0"
    assert by_name["sec-2026.zip"]["bytes"] == 1_175_887
    assert all(spec["pinned"] and spec["download_ready"] for spec in specs)
    assert module._sec_entrypoint_urls("2026") == [
        "https://xbrl.sec.gov/dei/2026/dei-2026.xsd",
        "https://xbrl.sec.gov/country/2026/country-2026.xsd",
        "https://xbrl.sec.gov/currency/2026/currency-2026.xsd",
        "https://xbrl.sec.gov/exch/2026/exch-2026.xsd",
    ]


def test_sec_xbrl_arelle_provisioning_declares_operator_verified_cyd_2024_pin_only() -> None:
    module = _helper_module()

    specs = module.taxonomy_specs(years=["2024"])
    by_name = {spec["name"]: spec for spec in specs}
    absent_vintage_names = {spec["name"] for spec in module.taxonomy_specs(years=["2023", "2025", "2026"])}

    assert "cyd-2024.zip" in by_name
    assert by_name["cyd-2024.zip"]["id"] == "sec-cyd-2024"
    assert by_name["cyd-2024.zip"]["kind"] == "offline_cache_archive"
    assert by_name["cyd-2024.zip"]["version"] == "2024"
    assert by_name["cyd-2024.zip"]["url"] == "https://xbrl.sec.gov/cyd/2024/cyd-2024.zip"
    assert by_name["cyd-2024.zip"]["sha256"] == "a52a1ab486257a5497a8ca4573a5d81a558c1fabcc1e858fabb769de658c3719"
    assert by_name["cyd-2024.zip"]["bytes"] == 16_356
    assert by_name["cyd-2024.zip"]["pinned"] is True
    assert by_name["cyd-2024.zip"]["download_ready"] is True
    assert "https://xbrl.sec.gov/cyd/2024/cyd-2024.xsd" in module._sec_entrypoint_urls("2024")
    assert not any(name.startswith("cyd-") for name in absent_vintage_names)


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


def test_sec_xbrl_arelle_provisioning_extracts_supported_sec_cache_layouts(tmp_path: Path) -> None:
    module = _helper_module()
    bare_archive_path = tmp_path / "sec-2022.zip"
    prefixed_archive_path = tmp_path / "sec-2025.zip"
    flat_cyd_archive_path = tmp_path / "cyd-2024.zip"
    cache_dir = tmp_path / "cache"
    cyd_members = [
        "cyd-2024.xsd",
        "cyd-6k-sub-2024.xsd",
        "cyd-8k-sub-2024.xsd",
        "cyd-af-2024.xsd",
        "cyd-af-sub-2024.xsd",
        "cyd-cr-2024.xsd",
        "cyd-entire-2024.xsd",
    ]

    with ZipFile(bare_archive_path, "w") as archive:
        archive.writestr("xbrl.sec.gov/dei/2022/dei-2022.xsd", "<schema/>")
        archive.writestr("not-sec/dei/2022/dei-2022.txt", "ignore")

    with ZipFile(prefixed_archive_path, "w") as archive:
        archive.writestr("2025/xbrl.sec.gov/dei/2025/dei-2025.xsd", "<schema/>")
        archive.writestr("2024/xbrl.sec.gov/dei/2025/dei-2025-wrong-prefix.xsd", "<schema/>")

    with ZipFile(flat_cyd_archive_path, "w") as archive:
        for member in cyd_members:
            archive.writestr(member, "<schema/>")
        archive.writestr("../cyd-2024.xsd", "ignore")
        archive.writestr("nested/cyd-2024.xsd", "ignore")
        archive.writestr("cyd-2025.xsd", "ignore")

    assert module._extract_sec_archive_to_cache(bare_archive_path, cache_dir, year="2022") == 1
    assert module._extract_sec_archive_to_cache(prefixed_archive_path, cache_dir, year="2025") == 1
    assert module._extract_sec_archive_to_cache(flat_cyd_archive_path, cache_dir, year="2024") == len(cyd_members)

    assert (cache_dir / "https" / "xbrl.sec.gov" / "dei" / "2022" / "dei-2022.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "dei" / "2025" / "dei-2025.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2024" / "cyd-2024.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2024" / "cyd-entire-2024.xsd").is_file()
    assert not (cache_dir / "https" / "2022" / "xbrl.sec.gov").exists()
    assert not (cache_dir / "https" / "2025" / "xbrl.sec.gov").exists()
    assert not (cache_dir / "https" / "xbrl.sec.gov" / "dei" / "2025" / "dei-2025-wrong-prefix.xsd").exists()
    assert not (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2024" / "cyd-2025.xsd").exists()
    assert module._sec_entrypoint_urls("2022") == [
        "https://xbrl.sec.gov/dei/2022/dei-2022.xsd",
        "https://xbrl.sec.gov/country/2022/country-2022.xsd",
        "https://xbrl.sec.gov/currency/2022/currency-2022.xsd",
        "https://xbrl.sec.gov/exch/2022/exch-2022.xsd",
    ]
    assert module._sec_entrypoint_urls("2025") == [
        "https://xbrl.sec.gov/dei/2025/dei-2025.xsd",
        "https://xbrl.sec.gov/country/2025/country-2025.xsd",
        "https://xbrl.sec.gov/currency/2025/currency-2025.xsd",
        "https://xbrl.sec.gov/exch/2025/exch-2025.xsd",
    ]


def test_sec_xbrl_arelle_provisioning_verifies_sec_entrypoints_after_all_archives(monkeypatch, tmp_path: Path) -> None:
    module = _helper_module()
    extracted: list[str] = []

    def fake_extract(archive_path: Path, _cache_dir: Path, *, year: str) -> int:
        assert year == "2024"
        extracted.append(Path(archive_path).name)
        return 1

    def fake_load(_cache_dir: Path, *, year: str) -> list[dict[str, object]]:
        assert year == "2024"
        assert extracted == ["sec-2024.zip", "cyd-2024.zip"]
        return [{"year": year, "url": "https://xbrl.sec.gov/cyd/2024/cyd-2024.xsd", "loaded": True}]

    monkeypatch.setattr(module, "_extract_sec_archive_to_cache", fake_extract)
    monkeypatch.setattr(module, "_load_sec_entrypoints_offline", fake_load)

    status = module._seed_and_verify_sec_taxonomy_cache(
        tmp_path / "cache",
        [
            {"id": "sec-2024", "version": "2024", "path": str(tmp_path / "sec-2024.zip")},
            {"id": "sec-cyd-2024", "version": "2024", "path": str(tmp_path / "cyd-2024.zip")},
        ],
    )

    assert status["error"] is None
    assert status["archive_ids"] == ["sec-2024", "sec-cyd-2024"]
    assert status["extracted_file_count"] == 2
    assert status["offline_entrypoints"] == [
        {"year": "2024", "url": "https://xbrl.sec.gov/cyd/2024/cyd-2024.xsd", "loaded": True}
    ]


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
