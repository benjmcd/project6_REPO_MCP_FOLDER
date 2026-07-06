from __future__ import annotations

import importlib.util
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "tools" / "sec-xbrl-arelle-provision.py"


def _helper_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_arelle_provision", HELPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_error_payload(excinfo) -> dict[str, object]:
    return json.loads(str(excinfo.value))


def _metadata_drifted_zip_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        info = ZipInfo(filename="a.xsd", date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.compress_type = ZIP_STORED
        info.external_attr = 0o644 << 16
        archive.writestr(info, b"a")
    return buffer.getvalue()


def test_sec_xbrl_arelle_provisioning_declares_pinned_packages_with_provenance() -> None:
    module = _helper_module()

    assert module.ARELLE_PACKAGE == "arelle-release"
    assert module.ARELLE_VERSION == "2.41.3"
    specs = module.taxonomy_specs()

    assert [spec["id"] for spec in specs] == [
        "fasb-us-gaap-2025",
        "fasb-srt-2025",
        "ifrs-2025",
        "sec-2025",
        "sec-cyd-2025",
    ]
    assert [spec["kind"] for spec in specs] == [
        "arelle_taxonomy_package",
        "arelle_taxonomy_package",
        "arelle_taxonomy_package",
        "offline_cache_archive",
        "offline_cache_archive",
    ]
    by_name = {spec["name"]: spec for spec in specs}
    assert all(spec["version"] == "2025" for spec in specs)
    assert {spec["sha256"] for spec in specs} == {
        "a3b835925ad74030eb5be865a26d7dfe44013081c4ab7204b6122316a685fff4",
        "aad1daeb4bdfe3057f4ed81482c06130f873a59fa7fce5193c5731f93b1fef88",
        "302afc7f69c5f92697ab8d87a6f584406f4addaf7f905468052c280c2fe16d19",
        "6a963051af02ff458e02669549bd55f9d547281724f3b4e053cb0157be8121e4",
        "ad7b166a3913778a4fabb15f3a4431d80eb1930d9cc1e271c318f7b4cffdfc33",
    }
    assert {Path(spec["url"]).name for spec in specs} == {
        "us-gaap-2025.zip",
        "srt-2025.zip",
        "IFRSAT-2025.zip",
        "2025.zip",
        "2025",
    }
    assert by_name["IFRSAT-2025.zip"]["id"] == "ifrs-2025"
    assert by_name["IFRSAT-2025.zip"]["kind"] == "arelle_taxonomy_package"
    assert by_name["IFRSAT-2025.zip"]["url"] == (
        "https://www.ifrs.org/content/dam/ifrs/standards/taxonomy/ifrs-taxonomies/IFRSAT-2025.zip"
    )
    assert by_name["IFRSAT-2025.zip"]["bytes"] == 2_103_003
    assert by_name["IFRSAT-2025.zip"]["offline_entrypoints"] == [
        "https://xbrl.ifrs.org/taxonomy/2025-03-27/full_ifrs/full_ifrs-cor_2025-03-27.xsd"
    ]
    assert "IFRS Foundation 2025 IFRS Accounting Taxonomy package" in by_name["IFRSAT-2025.zip"]["source"]
    assert by_name["cyd-2025.zip"]["url"] == "https://xbrl.sec.gov/cyd/2025/"
    assert by_name["cyd-2025.zip"]["bytes"] == 208_667
    assert by_name["cyd-2025.zip"]["operator_built_archive"] is True
    assert "operator-built deterministic archive" in by_name["cyd-2025.zip"]["source"]
    assert "loose files" in by_name["cyd-2025.zip"]["source"]
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


def test_sec_xbrl_arelle_provisioning_declares_operator_verified_cyd_pins_only() -> None:
    module = _helper_module()

    specs = module.taxonomy_specs(years=["2024"])
    cyd_2025_specs = module.taxonomy_specs(years=["2025"])
    by_name = {spec["name"]: spec for spec in specs}
    cyd_2025_by_name = {spec["name"]: spec for spec in cyd_2025_specs}
    absent_vintage_names = {spec["name"] for spec in module.taxonomy_specs(years=["2023", "2026"])}

    assert "cyd-2024.zip" in by_name
    assert by_name["cyd-2024.zip"]["id"] == "sec-cyd-2024"
    assert by_name["cyd-2024.zip"]["kind"] == "offline_cache_archive"
    assert by_name["cyd-2024.zip"]["version"] == "2024"
    assert by_name["cyd-2024.zip"]["url"] == "https://xbrl.sec.gov/cyd/2024/cyd-2024.zip"
    assert by_name["cyd-2024.zip"]["sha256"] == "a52a1ab486257a5497a8ca4573a5d81a558c1fabcc1e858fabb769de658c3719"
    assert by_name["cyd-2024.zip"]["bytes"] == 16_356
    assert by_name["cyd-2024.zip"]["pinned"] is True
    assert by_name["cyd-2024.zip"]["download_ready"] is True
    assert cyd_2025_by_name["cyd-2025.zip"]["id"] == "sec-cyd-2025"
    assert cyd_2025_by_name["cyd-2025.zip"]["kind"] == "offline_cache_archive"
    assert cyd_2025_by_name["cyd-2025.zip"]["version"] == "2025"
    assert cyd_2025_by_name["cyd-2025.zip"]["url"] == "https://xbrl.sec.gov/cyd/2025/"
    assert (
        cyd_2025_by_name["cyd-2025.zip"]["sha256"]
        == "ad7b166a3913778a4fabb15f3a4431d80eb1930d9cc1e271c318f7b4cffdfc33"
    )
    assert cyd_2025_by_name["cyd-2025.zip"]["bytes"] == 208_667
    assert cyd_2025_by_name["cyd-2025.zip"]["pinned"] is True
    assert cyd_2025_by_name["cyd-2025.zip"]["download_ready"] is True
    assert cyd_2025_by_name["cyd-2025.zip"]["operator_built_archive"] is True
    assert "https://xbrl.sec.gov/cyd/2024/cyd-2024.xsd" in module._sec_entrypoint_urls("2024")
    assert "https://xbrl.sec.gov/cyd/2025/cyd-2025.xsd" in module._sec_entrypoint_urls("2025")
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
    flat_cyd_2025_archive_path = tmp_path / "cyd-2025.zip"
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
    cyd_2025_members = [member.replace("2024", "2025") for member in cyd_members]

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

    with ZipFile(flat_cyd_2025_archive_path, "w") as archive:
        for member in cyd_2025_members:
            archive.writestr(member, "<schema/>")
        archive.writestr("../cyd-2025.xsd", "ignore")
        archive.writestr("nested/cyd-2025.xsd", "ignore")
        archive.writestr("cyd-2024.xsd", "ignore")

    assert module._extract_sec_archive_to_cache(bare_archive_path, cache_dir, year="2022") == 1
    assert module._extract_sec_archive_to_cache(prefixed_archive_path, cache_dir, year="2025") == 1
    assert module._extract_sec_archive_to_cache(flat_cyd_archive_path, cache_dir, year="2024") == len(cyd_members)
    assert module._extract_sec_archive_to_cache(flat_cyd_2025_archive_path, cache_dir, year="2025") == len(
        cyd_2025_members
    )

    assert (cache_dir / "https" / "xbrl.sec.gov" / "dei" / "2022" / "dei-2022.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "dei" / "2025" / "dei-2025.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2024" / "cyd-2024.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2024" / "cyd-entire-2024.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2025" / "cyd-2025.xsd").is_file()
    assert (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2025" / "cyd-entire-2025.xsd").is_file()
    assert not (cache_dir / "https" / "2022" / "xbrl.sec.gov").exists()
    assert not (cache_dir / "https" / "2025" / "xbrl.sec.gov").exists()
    assert not (cache_dir / "https" / "xbrl.sec.gov" / "dei" / "2025" / "dei-2025-wrong-prefix.xsd").exists()
    assert not (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2024" / "cyd-2025.xsd").exists()
    assert not (cache_dir / "https" / "xbrl.sec.gov" / "cyd" / "2025" / "cyd-2024.xsd").exists()
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
        "https://xbrl.sec.gov/cyd/2025/cyd-2025.xsd",
    ]


def test_sec_xbrl_arelle_provisioning_builds_deterministic_operator_archive() -> None:
    module = _helper_module()

    first = module._build_flat_zip_archive({"b.xsd": b"b", "a.xsd": b"a"})
    second = module._build_flat_zip_archive({"a.xsd": b"a", "b.xsd": b"b"})

    assert first == second
    with ZipFile(BytesIO(first)) as archive:
        assert archive.namelist() == ["a.xsd", "b.xsd"]
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.create_system == 0
            assert info.compress_type == ZIP_STORED
            assert info.external_attr == 0o644 << 16


def test_sec_xbrl_arelle_provisioning_rejects_default_zip_metadata(tmp_path: Path) -> None:
    module = _helper_module()
    archive_path = tmp_path / "default.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("a.xsd", b"a")

    with pytest.raises(RuntimeError) as excinfo:
        module.verify_zip_determinism(archive_path)

    payload = _runtime_error_payload(excinfo)
    assert payload["reason"] == "zip_determinism_date_time_mismatch"
    assert payload["entry"] == "a.xsd"
    assert payload["field"] == "date_time"
    assert payload["expected"] == [1980, 1, 1, 0, 0, 0]


def test_sec_xbrl_arelle_provisioning_accepts_normalized_operator_archive(tmp_path: Path) -> None:
    module = _helper_module()
    archive_path = tmp_path / "normalized.zip"
    archive_path.write_bytes(module._build_flat_zip_archive({"b.xsd": b"b", "a.xsd": b"a"}))

    assert module.verify_zip_determinism(archive_path) is None


def test_sec_xbrl_arelle_provisioning_fails_closed_on_operator_archive_metadata_drift(
    monkeypatch, tmp_path: Path
) -> None:
    module = _helper_module()
    drifted_archive = _metadata_drifted_zip_bytes()
    requested_urls: list[str] = []

    def fake_download(url: str) -> bytes:
        requested_urls.append(url)
        return b"a"

    monkeypatch.setattr(module, "_download", fake_download)
    monkeypatch.setattr(module, "_build_flat_zip_archive", lambda _members: drifted_archive)
    spec = {
        "id": "sec-cyd-test",
        "kind": "offline_cache_archive",
        "name": "cyd-test.zip",
        "version": "2099",
        "url": "https://xbrl.sec.gov/cyd/2099/",
        "sha256": module._sha256_bytes(drifted_archive),
        "bytes": len(drifted_archive),
        "source": "operator-built archive with drifted metadata",
        "pinned": True,
        "download_ready": True,
        "operator_built_archive": True,
        "operator_built_members": [{"name": "a.xsd", "sha256": module._sha256_bytes(b"a"), "bytes": 1}],
    }

    with pytest.raises(RuntimeError) as excinfo:
        module._ensure_taxonomy_package(tmp_path, spec, download=True)

    payload = _runtime_error_payload(excinfo)
    assert requested_urls == ["https://xbrl.sec.gov/cyd/2099/a.xsd"]
    assert payload == {
        "reason": "zip_determinism_create_system_mismatch",
        "entry": "a.xsd",
        "field": "create_system",
        "expected": 0,
        "actual": 3,
    }


def test_sec_xbrl_arelle_provisioning_downloads_operator_archive_from_loose_files(monkeypatch, tmp_path: Path) -> None:
    module = _helper_module()
    member_bytes = {"b.xsd": b"b", "a.xsd": b"a"}
    archive_bytes = module._build_flat_zip_archive(member_bytes)
    requested_urls: list[str] = []

    def fake_download(url: str) -> bytes:
        requested_urls.append(url)
        return member_bytes[Path(url).name]

    monkeypatch.setattr(module, "_download", fake_download)
    spec = {
        "id": "sec-cyd-test",
        "kind": "offline_cache_archive",
        "name": "cyd-test.zip",
        "version": "2099",
        "url": "https://xbrl.sec.gov/cyd/2099/",
        "sha256": module._sha256_bytes(archive_bytes),
        "bytes": len(archive_bytes),
        "source": "operator-built deterministic archive from SEC loose files",
        "pinned": True,
        "download_ready": True,
        "operator_built_archive": True,
        "operator_built_members": [
            {"name": "a.xsd", "sha256": module._sha256_bytes(b"a"), "bytes": 1},
            {"name": "b.xsd", "sha256": module._sha256_bytes(b"b"), "bytes": 1},
        ],
    }

    package = module._ensure_taxonomy_package(tmp_path, spec, download=True)

    assert requested_urls == ["https://xbrl.sec.gov/cyd/2099/a.xsd", "https://xbrl.sec.gov/cyd/2099/b.xsd"]
    assert package["exists"] is True
    assert package["downloaded"] is True
    assert package["sha256_matches"] is True
    assert package["bytes_match"] is True
    assert (tmp_path / "cyd-test.zip").read_bytes() == archive_bytes


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


def test_sec_xbrl_arelle_provisioning_verifies_ifrs_entrypoint_after_package_load(
    monkeypatch, tmp_path: Path
) -> None:
    module = _helper_module()
    captured: dict[str, object] = {}
    expected_url = "https://xbrl.ifrs.org/taxonomy/2025-03-27/full_ifrs/full_ifrs-cor_2025-03-27.xsd"

    def fake_arelle_status() -> dict[str, object]:
        return {
            "package": module.ARELLE_PACKAGE,
            "expected_version": module.ARELLE_VERSION,
            "installed": True,
            "version": module.ARELLE_VERSION,
            "version_matches": True,
            "importable": True,
            "import_error": None,
        }

    def fake_ensure(taxonomy_dir: Path, spec: dict[str, object], *, download: bool) -> dict[str, object]:
        return {
            **spec,
            "path": str(taxonomy_dir / str(spec["name"])),
            "downloaded": False,
            "download_blocked": False,
            "exists": True,
            "observed_sha256": spec["sha256"],
            "sha256_matches": True,
            "observed_bytes": spec["bytes"],
            "bytes_match": True,
        }

    def fake_load(paths: list[Path], *, entrypoints=()) -> dict[str, object]:
        captured["package_names"] = [path.name for path in paths]
        captured["entrypoints"] = list(entrypoints)
        return {
            "attempted": True,
            "loaded_hashes": [f"hash-{index}" for index, _path in enumerate(paths)],
            "invalid_hashes": [],
            "offline_entrypoints": [
                {**entrypoint, "loaded": True, "error": None, "model_errors": []} for entrypoint in entrypoints
            ],
            "error": None,
        }

    monkeypatch.setattr(module, "_arelle_status", fake_arelle_status)
    monkeypatch.setattr(module, "_ensure_taxonomy_package", fake_ensure)
    monkeypatch.setattr(module, "_load_taxonomy_packages_with_arelle", fake_load)
    monkeypatch.setattr(
        module,
        "_seed_and_verify_sec_taxonomy_cache",
        lambda _cache_dir, _archives: {"attempted": True, "archive_ids": [], "extracted_file_count": 0, "offline_entrypoints": [], "error": None},
    )

    report = module.build_report(taxonomy_dir=tmp_path / "taxonomy", cache_dir=tmp_path / "cache", download=False)

    assert report["ready"] is True
    assert captured["package_names"] == ["us-gaap-2025.zip", "srt-2025.zip", "IFRSAT-2025.zip"]
    assert captured["entrypoints"] == [{"package_id": "ifrs-2025", "year": "2025", "url": expected_url}]
    assert report["arelle_load"]["offline_entrypoints"] == [
        {"package_id": "ifrs-2025", "year": "2025", "url": expected_url, "loaded": True, "error": None, "model_errors": []}
    ]


def test_sec_xbrl_arelle_provisioning_blocks_ifrs_entrypoint_load_failure(monkeypatch, tmp_path: Path) -> None:
    module = _helper_module()

    def fake_arelle_status() -> dict[str, object]:
        return {
            "package": module.ARELLE_PACKAGE,
            "expected_version": module.ARELLE_VERSION,
            "installed": True,
            "version": module.ARELLE_VERSION,
            "version_matches": True,
            "importable": True,
            "import_error": None,
        }

    def fake_ensure(taxonomy_dir: Path, spec: dict[str, object], *, download: bool) -> dict[str, object]:
        return {
            **spec,
            "path": str(taxonomy_dir / str(spec["name"])),
            "downloaded": False,
            "download_blocked": False,
            "exists": True,
            "observed_sha256": spec["sha256"],
            "sha256_matches": True,
            "observed_bytes": spec["bytes"],
            "bytes_match": True,
        }

    def fake_load(paths: list[Path], *, entrypoints=()) -> dict[str, object]:
        return {
            "attempted": True,
            "loaded_hashes": [f"hash-{index}" for index, _path in enumerate(paths)],
            "invalid_hashes": [],
            "offline_entrypoints": [
                {**entrypoint, "loaded": False, "error": "OSError", "model_errors": []} for entrypoint in entrypoints
            ],
            "error": None,
        }

    monkeypatch.setattr(module, "_arelle_status", fake_arelle_status)
    monkeypatch.setattr(module, "_ensure_taxonomy_package", fake_ensure)
    monkeypatch.setattr(module, "_load_taxonomy_packages_with_arelle", fake_load)
    monkeypatch.setattr(
        module,
        "_seed_and_verify_sec_taxonomy_cache",
        lambda _cache_dir, _archives: {"attempted": True, "archive_ids": [], "extracted_file_count": 0, "offline_entrypoints": [], "error": None},
    )

    report = module.build_report(taxonomy_dir=tmp_path / "taxonomy", cache_dir=tmp_path / "cache", download=False)

    assert report["ready"] is False
    assert "arelle_taxonomy_package_entrypoint_load_failed" in report["blocked_reasons"]


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
    assert report["taxonomy_year_coverage"]["2025"]["planned_artifact_count"] == 5
    assert report["taxonomy_year_coverage"]["2025"]["pinned_artifact_count"] == 5
    assert report["taxonomy_year_coverage"]["2019"]["partial_coverage"] is True
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
