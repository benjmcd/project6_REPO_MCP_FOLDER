from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from zipfile import ZIP_STORED, ZipFile, ZipInfo


SCHEMA_ID = "tools.sec_xbrl_arelle_provision.v1"
ARELLE_PACKAGE = "arelle-release"
ARELLE_VERSION = "2.41.3"
READ_TIMEOUT_SECONDS = 120
DEFAULT_TAXONOMY_YEARS = ("2025",)
ADMITTED_TAXONOMY_YEARS = tuple(str(year) for year in range(2019, 2027))
_CYD_2024_FLAT_ARCHIVE_MEMBERS = frozenset(
    {
        "cyd-2024.xsd",
        "cyd-6k-sub-2024.xsd",
        "cyd-8k-sub-2024.xsd",
        "cyd-af-2024.xsd",
        "cyd-af-sub-2024.xsd",
        "cyd-cr-2024.xsd",
        "cyd-entire-2024.xsd",
    }
)
_CYD_2025_FLAT_ARCHIVE_MEMBERS = frozenset(
    {
        "cyd-2025.xsd",
        "cyd-6k-sub-2025.xsd",
        "cyd-8k-sub-2025.xsd",
        "cyd-af-2025.xsd",
        "cyd-af-sub-2025.xsd",
        "cyd-cr-2025.xsd",
        "cyd-entire-2025.xsd",
    }
)
_CYD_2025_OPERATOR_BUILT_MEMBERS: tuple[dict[str, Any], ...] = (
    {
        "name": "cyd-2025.xsd",
        "sha256": "da7e6f4447191c4e62f07ffef156348bf7683fb717743b29316ef2f09688e57e",
        "bytes": 52_366,
    },
    {
        "name": "cyd-6k-sub-2025.xsd",
        "sha256": "6ae880e18f03b8a4d6048fa445ba7da219d8eeac6d6ed72479b5f50bbc77a3bc",
        "bytes": 26_130,
    },
    {
        "name": "cyd-8k-sub-2025.xsd",
        "sha256": "6cd008fa9bdab4e0eed8ebcc4dcfd3c52580a1cff806dd24d42d990dab15e5af",
        "bytes": 26_130,
    },
    {
        "name": "cyd-af-2025.xsd",
        "sha256": "456e41cd3e86fb8a9f497f9175945c2260a52c5bc2829d8c4eeda95673c85ff4",
        "bytes": 11_802,
    },
    {
        "name": "cyd-af-sub-2025.xsd",
        "sha256": "b8255b4f6224dc9c523908ca014c4839b5c633a5478132cb7d81474d7113a0db",
        "bytes": 31_457,
    },
    {
        "name": "cyd-cr-2025.xsd",
        "sha256": "8a05e855611bfbe57486f086e78aaebd00567ff50dcfa5a40b6a0defed435651",
        "bytes": 7_666,
    },
    {
        "name": "cyd-entire-2025.xsd",
        "sha256": "49d2dd9dad441ee137fbad06c17f225c94755134234b1d7db1b409b9d544a40f",
        "bytes": 52_326,
    },
)
_SEC_FLAT_ARCHIVE_MEMBERS_BY_YEAR = {
    "2024": _CYD_2024_FLAT_ARCHIVE_MEMBERS,
    "2025": _CYD_2025_FLAT_ARCHIVE_MEMBERS,
}


def _taxonomy_spec(
    *,
    id: str,
    kind: str,
    name: str,
    version: str,
    url: str,
    sha256: str | None,
    bytes: int | None,
    source: str,
    pinned: bool = True,
    download_ready: bool = True,
    unavailable_reason: str | None = None,
    operator_built_archive: bool = False,
    operator_built_members: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "id": id,
        "kind": kind,
        "name": name,
        "version": version,
        "url": url,
        "sha256": sha256,
        "bytes": bytes,
        "source": source,
        "pinned": pinned,
        "download_ready": download_ready,
    }
    if unavailable_reason:
        spec["unavailable_reason"] = unavailable_reason
    if operator_built_archive:
        spec["operator_built_archive"] = True
        spec["operator_built_members"] = list(operator_built_members or ())
    return spec


_TAXONOMY_SPECS: tuple[dict[str, Any], ...] = (
    _taxonomy_spec(
        id="fasb-us-gaap-2019",
        kind="arelle_taxonomy_package",
        name="us-gaap-2019.zip",
        version="2019",
        url="https://xbrl.fasb.org/us-gaap/2019/us-gaap-2019-01-31.zip",
        sha256="16ea8c9f25e61a3d2e824ab917067f787683c9eeff2147cbe3b0463508d1d667",
        bytes=5_728_252,
        source="FASB 2019 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2019",
        kind="arelle_taxonomy_package",
        name="srt-2019.zip",
        version="2019",
        url="https://xbrl.fasb.org/srt/2019/srt-2019-01-31.zip",
        sha256="947af75fd03cd08915430b7b4200e9c037d0d14e4f86a12632adb16eedbf73f7",
        bytes=161_358,
        source="FASB 2019 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2019-unavailable",
        kind="offline_cache_archive",
        name="sec-2019.zip",
        version="2019",
        url="https://xbrl.sec.gov/2019.zip",
        sha256=None,
        bytes=None,
        source="SEC 2019 taxonomy package archive unavailable; DEI-only archive is not equivalent to the full SEC suite",
        pinned=False,
        download_ready=False,
        unavailable_reason="sec_suite_archive_unavailable",
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2020",
        kind="arelle_taxonomy_package",
        name="us-gaap-2020.zip",
        version="2020",
        url="https://xbrl.fasb.org/us-gaap/2020/us-gaap-2020-01-31.zip",
        sha256="043d45481d7baacb2f04ebd97dbcfecdc6706b74e38fe002c4b4703ef7a0a4d2",
        bytes=6_345_468,
        source="FASB 2020 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2020",
        kind="arelle_taxonomy_package",
        name="srt-2020.zip",
        version="2020",
        url="https://xbrl.fasb.org/srt/2020/srt-2020-01-31.zip",
        sha256="57168b52f9e8da5bc9aa593f6a6aacc581c83877b59fe8d43291730da1bc840c",
        bytes=158_794,
        source="FASB 2020 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2020-unavailable",
        kind="offline_cache_archive",
        name="sec-2020.zip",
        version="2020",
        url="https://xbrl.sec.gov/2020.zip",
        sha256=None,
        bytes=None,
        source="SEC 2020 taxonomy package archive unavailable; DEI-only archive is not equivalent to the full SEC suite",
        pinned=False,
        download_ready=False,
        unavailable_reason="sec_suite_archive_unavailable",
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2021",
        kind="arelle_taxonomy_package",
        name="us-gaap-2021.zip",
        version="2021",
        url="https://xbrl.fasb.org/us-gaap/2021/us-gaap-2021-01-31.zip",
        sha256="2e4309134cf62ff7ad61a371333fe52c6002279706bba244b63b4e64b8274843",
        bytes=6_526_936,
        source="FASB 2021 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2021",
        kind="arelle_taxonomy_package",
        name="srt-2021.zip",
        version="2021",
        url="https://xbrl.fasb.org/srt/2021/srt-2021-01-31.zip",
        sha256="096cc522a9b7424d07459df76ffd4462dd74b910e702901a4f587960009c4327",
        bytes=186_168,
        source="FASB 2021 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2021",
        kind="offline_cache_archive",
        name="sec-2021.zip",
        version="2021",
        url="https://xbrl.sec.gov/2021.zip",
        sha256="0b834bdf26f5880a2ccfe7fe973940ee41ad746d8f8a782d3649f0dfdad5b53b",
        bytes=598_328,
        source="SEC 2021 taxonomy package archive",
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2022",
        kind="arelle_taxonomy_package",
        name="us-gaap-2022.zip",
        version="2022",
        url="https://xbrl.fasb.org/us-gaap/2022/us-gaap-2022.zip",
        sha256="8af6fbbcec3818cd372f391cece9e62018e115b7b65ea75a6a38b9709af3ab37",
        bytes=6_485_888,
        source="FASB 2022 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2022",
        kind="arelle_taxonomy_package",
        name="srt-2022.zip",
        version="2022",
        url="https://xbrl.fasb.org/srt/2022/srt-2022.zip",
        sha256="37d0156ccc5ee77594a84109eb475ca3fe75a56ff25069e261e943d451451c9f",
        bytes=182_036,
        source="FASB 2022 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2022",
        kind="offline_cache_archive",
        name="sec-2022.zip",
        version="2022",
        url="https://xbrl.sec.gov/2022.zip",
        sha256="b9f01a19df2e286f016e89239f616c0dd1012c3477947a7374d02c84ebd06568",
        bytes=576_613,
        source="SEC 2022 taxonomy package archive",
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2023",
        kind="arelle_taxonomy_package",
        name="us-gaap-2023.zip",
        version="2023",
        url="https://xbrl.fasb.org/us-gaap/2023/us-gaap-2023.zip",
        sha256="b48fbb7be5cbaef5532ebff51394176ca6e7241ffce5fc88812485b8e6f9d6fd",
        bytes=6_607_657,
        source="FASB 2023 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2023",
        kind="arelle_taxonomy_package",
        name="srt-2023.zip",
        version="2023",
        url="https://xbrl.fasb.org/srt/2023/srt-2023.zip",
        sha256="e1a667a56cde32af35fcf5a1936691bd4d22e52a29ce2af7218c5ef4c23810de",
        bytes=188_585,
        source="FASB 2023 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2023",
        kind="offline_cache_archive",
        name="sec-2023.zip",
        version="2023",
        url="https://xbrl.sec.gov/2023.zip",
        sha256="0b5cd8689d9b2fdda525b15603b459171c624e175079d90a917ca1e518c592e4",
        bytes=954_681,
        source="SEC 2023 taxonomy package archive",
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2024",
        kind="arelle_taxonomy_package",
        name="us-gaap-2024.zip",
        version="2024",
        url="https://xbrl.fasb.org/us-gaap/2024/us-gaap-2024.zip",
        sha256="decdd417d86ff7bfb5ca166c0ca1001017aea873673544a8d7f91c34bf5d82df",
        bytes=7_115_653,
        source="FASB 2024 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2024",
        kind="arelle_taxonomy_package",
        name="srt-2024.zip",
        version="2024",
        url="https://xbrl.fasb.org/srt/2024/srt-2024.zip",
        sha256="136d16f1bf62ca1966300231b2b399f90631ba703381aeec467e9bec4f3867eb",
        bytes=188_150,
        source="FASB 2024 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2024",
        kind="offline_cache_archive",
        name="sec-2024.zip",
        version="2024",
        url="https://xbrl.sec.gov/2024.zip",
        sha256="418477e806d5a2d6b21376a26c01fc373d549dae8d18f223a6ebddf80680bdf0",
        bytes=1_084_829,
        source="SEC 2024 taxonomy package archive",
    ),
    _taxonomy_spec(
        id="sec-cyd-2024",
        kind="offline_cache_archive",
        name="cyd-2024.zip",
        version="2024",
        url="https://xbrl.sec.gov/cyd/2024/cyd-2024.zip",
        sha256="a52a1ab486257a5497a8ca4573a5d81a558c1fabcc1e858fabb769de658c3719",
        bytes=16_356,
        source="SEC 2024 Cybersecurity Disclosure taxonomy archive, operator-fetched 2026-07-05",
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2025",
        kind="arelle_taxonomy_package",
        name="us-gaap-2025.zip",
        version="2025",
        url="https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.zip",
        sha256="a3b835925ad74030eb5be865a26d7dfe44013081c4ab7204b6122316a685fff4",
        bytes=7_101_405,
        source="FASB 2025 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2025",
        kind="arelle_taxonomy_package",
        name="srt-2025.zip",
        version="2025",
        url="https://xbrl.fasb.org/srt/2025/srt-2025.zip",
        sha256="aad1daeb4bdfe3057f4ed81482c06130f873a59fa7fce5193c5731f93b1fef88",
        bytes=191_908,
        source="FASB 2025 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2025",
        kind="offline_cache_archive",
        name="sec-2025.zip",
        version="2025",
        url="https://xbrl.sec.gov/2025.zip",
        sha256="6a963051af02ff458e02669549bd55f9d547281724f3b4e053cb0157be8121e4",
        bytes=1_201_089,
        source="SEC 2025 taxonomy package archive",
    ),
    _taxonomy_spec(
        id="sec-cyd-2025",
        kind="offline_cache_archive",
        name="cyd-2025.zip",
        version="2025",
        url="https://xbrl.sec.gov/cyd/2025/",
        sha256="ad7b166a3913778a4fabb15f3a4431d80eb1930d9cc1e271c318f7b4cffdfc33",
        bytes=208_667,
        source=(
            "SEC 2025 Cybersecurity Disclosure taxonomy loose files; "
            "operator-built deterministic archive 2026-07-06; SEC does not publish cyd-2025.zip"
        ),
        operator_built_archive=True,
        operator_built_members=_CYD_2025_OPERATOR_BUILT_MEMBERS,
    ),
    _taxonomy_spec(
        id="fasb-us-gaap-2026",
        kind="arelle_taxonomy_package",
        name="us-gaap-2026.zip",
        version="2026",
        url="https://xbrl.fasb.org/us-gaap/2026/us-gaap-2026.zip",
        sha256="f4c8b8b5697ba7d825a8614b159611cd25a46640e98a9737cda1e4a672bd4c81",
        bytes=7_387_980,
        source="FASB 2026 GAAP Financial Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="fasb-srt-2026",
        kind="arelle_taxonomy_package",
        name="srt-2026.zip",
        version="2026",
        url="https://xbrl.fasb.org/srt/2026/srt-2026.zip",
        sha256="34dab1ee7a10b9991fee1e17437c278908599ff2258ea3270ef718cab265be05",
        bytes=195_234,
        source="FASB 2026 SEC Reporting Taxonomy package",
    ),
    _taxonomy_spec(
        id="sec-2026",
        kind="offline_cache_archive",
        name="sec-2026.zip",
        version="2026",
        url="https://xbrl.sec.gov/2026.zip",
        sha256="16243a0713f10fb7bebd020cb0da505e2bf4ef180af3e19b8e4cd4ad2a75a6a0",
        bytes=1_175_887,
        source="SEC 2026 taxonomy package archive",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Provision and verify the optional SEC XBRL Arelle dependency lane. "
            "Downloads versioned FASB taxonomy packages only to the provided runtime directory."
        )
    )
    parser.add_argument("--taxonomy-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--years", default=",".join(DEFAULT_TAXONOMY_YEARS))
    args = parser.parse_args()

    report = build_report(
        taxonomy_dir=Path(args.taxonomy_dir),
        cache_dir=Path(args.cache_dir),
        download=not args.no_download,
        years=_parse_years(args.years),
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(_summary(report), sort_keys=True))
    return 0 if report["ready"] else 2


def taxonomy_specs(*, years: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for year in _normalise_years(years):
        pinned_specs = [spec for spec in _TAXONOMY_SPECS if spec["version"] == year]
        if pinned_specs:
            specs.extend(dict(spec) for spec in pinned_specs)
        else:
            specs.extend(_planned_taxonomy_specs(year))
    return specs


def _parse_years(value: str) -> tuple[str, ...]:
    return _normalise_years([item.strip() for item in str(value or "").split(",") if item.strip()])


def _normalise_years(years: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    raw_years = years or DEFAULT_TAXONOMY_YEARS
    requested = tuple(dict.fromkeys(str(year).strip() for year in raw_years if str(year).strip()))
    if not requested:
        return DEFAULT_TAXONOMY_YEARS
    unsupported = [year for year in requested if year not in ADMITTED_TAXONOMY_YEARS]
    if unsupported:
        raise ValueError(f"Unsupported taxonomy year(s): {', '.join(unsupported)}")
    return requested


def _planned_taxonomy_specs(year: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"fasb-us-gaap-{year}",
            "kind": "arelle_taxonomy_package",
            "name": f"us-gaap-{year}.zip",
            "version": year,
            "url": f"https://xbrl.fasb.org/us-gaap/{year}/us-gaap-{year}.zip",
            "sha256": None,
            "bytes": None,
            "source": f"FASB {year} GAAP Financial Reporting Taxonomy package",
            "pinned": False,
            "download_ready": False,
        },
        {
            "id": f"fasb-srt-{year}",
            "kind": "arelle_taxonomy_package",
            "name": f"srt-{year}.zip",
            "version": year,
            "url": f"https://xbrl.fasb.org/srt/{year}/srt-{year}.zip",
            "sha256": None,
            "bytes": None,
            "source": f"FASB {year} SEC Reporting Taxonomy package",
            "pinned": False,
            "download_ready": False,
        },
        {
            "id": f"sec-{year}",
            "kind": "offline_cache_archive",
            "name": f"sec-{year}.zip",
            "version": year,
            "url": f"https://xbrl.sec.gov/{year}.zip",
            "sha256": None,
            "bytes": None,
            "source": f"SEC {year} taxonomy package archive",
            "pinned": False,
            "download_ready": False,
        },
    ]


def build_report(
    *,
    taxonomy_dir: Path,
    cache_dir: Path,
    download: bool,
    load_with_arelle: bool = True,
    years: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    requested_years = _normalise_years(years)
    taxonomy_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    arelle = _arelle_status()
    packages = [_ensure_taxonomy_package(taxonomy_dir, spec, download=download) for spec in taxonomy_specs(years=requested_years)]
    blocked = _blocked_reasons(arelle=arelle, packages=packages)
    arelle_packages = [pkg for pkg in packages if pkg["kind"] == "arelle_taxonomy_package"]
    cache_archives = [pkg for pkg in packages if pkg["kind"] == "offline_cache_archive"]
    arelle_load = {
        "attempted": False,
        "loaded_hashes": [],
        "invalid_hashes": [],
        "error": None,
    }
    sec_cache = {
        "attempted": False,
        "archive_ids": [],
        "extracted_file_count": 0,
        "offline_entrypoints": [],
        "error": None,
    }
    if not blocked and load_with_arelle:
        arelle_load = _load_taxonomy_packages_with_arelle([Path(pkg["path"]) for pkg in arelle_packages])
        if arelle_load["error"]:
            blocked.append("arelle_taxonomy_package_load_failed")
        elif len(arelle_load["loaded_hashes"]) != len(arelle_packages):
            blocked.append("arelle_taxonomy_package_load_incomplete")
        elif arelle_load["invalid_hashes"]:
            blocked.append("arelle_taxonomy_package_invalid")
        sec_cache = _seed_and_verify_sec_taxonomy_cache(cache_dir, cache_archives)
        if sec_cache["error"]:
            blocked.append("sec_taxonomy_cache_unavailable")
        elif any(not item["loaded"] for item in sec_cache["offline_entrypoints"]):
            blocked.append("sec_taxonomy_cache_entrypoint_load_failed")

    return {
        "schema_id": SCHEMA_ID,
        "ready": not blocked,
        "blocked_reasons": blocked,
        "arelle": arelle,
        "requested_taxonomy_years": list(requested_years),
        "taxonomy_year_coverage": _taxonomy_year_coverage(packages),
        "taxonomy_packages": packages,
        "taxonomy_artifact_count": len(packages),
        "taxonomy_package_count": len(arelle_packages),
        "taxonomy_cache_archive_count": len(cache_archives),
        "taxonomy_package_loaded_count": len(arelle_load["loaded_hashes"]),
        "taxonomy_cache_dir_created": cache_dir.is_dir(),
        "arelle_load": arelle_load,
        "sec_taxonomy_cache": sec_cache,
        "non_goals_preserved": {
            "sec_network_fetch_performed": False,
            "sidecar_invoked": False,
            "value_reveal_performed": False,
            "runtime_defaults_changed": False,
            "raw_values_returned": False,
        },
    }


def _arelle_status() -> dict[str, Any]:
    try:
        version = importlib.metadata.version(ARELLE_PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        return {
            "package": ARELLE_PACKAGE,
            "expected_version": ARELLE_VERSION,
            "installed": False,
            "version": None,
            "version_matches": False,
            "importable": False,
            "import_error": "package_not_found",
        }
    import_error = None
    importable = False
    try:
        from arelle import Cntlr  # noqa: F401
        from arelle import PackageManager  # noqa: F401

        importable = True
    except Exception as exc:
        import_error = exc.__class__.__name__
    return {
        "package": ARELLE_PACKAGE,
        "expected_version": ARELLE_VERSION,
        "installed": True,
        "version": version,
        "version_matches": version == ARELLE_VERSION,
        "importable": importable,
        "import_error": import_error,
    }


def _ensure_taxonomy_package(taxonomy_dir: Path, spec: dict[str, Any], *, download: bool) -> dict[str, Any]:
    path = taxonomy_dir / spec["name"]
    downloaded = False
    pinned = bool(spec.get("pinned"))
    download_ready = bool(spec.get("download_ready"))
    download_blocked = bool(download and not path.exists() and not (pinned and download_ready))
    if not path.exists() and download and pinned and download_ready:
        if spec.get("operator_built_archive"):
            path.write_bytes(_download_operator_built_archive(spec))
        else:
            path.write_bytes(_download(spec["url"]))
        downloaded = True
    exists = path.is_file()
    observed_hash = _sha256(path) if exists else None
    observed_bytes = path.stat().st_size if exists else None
    expected_hash = spec.get("sha256")
    expected_bytes = spec.get("bytes")
    return {
        **spec,
        "path": str(path),
        "downloaded": downloaded,
        "download_blocked": download_blocked,
        "exists": exists,
        "observed_sha256": observed_hash,
        "sha256_matches": observed_hash == expected_hash if expected_hash else False,
        "observed_bytes": observed_bytes,
        "bytes_match": observed_bytes == expected_bytes if expected_bytes else False,
    }


def _load_taxonomy_packages_with_arelle(paths: list[Path]) -> dict[str, Any]:
    try:
        from arelle import Cntlr
        from arelle import PackageManager
    except Exception as exc:
        return {"attempted": False, "loaded_hashes": [], "invalid_hashes": [], "error": exc.__class__.__name__}
    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    try:
        PackageManager.init(cntlr, loadPackagesConfig=False)
        loaded_hashes: list[str] = []
        invalid_hashes: list[str] = []
        for path in paths:
            package_hash = _sha256(path)
            try:
                info = PackageManager.addPackage(cntlr, str(path.resolve()))
            except Exception:
                info = None
            if info is None:
                invalid_hashes.append(package_hash)
            else:
                loaded_hashes.append(package_hash)
        if loaded_hashes:
            PackageManager.rebuildRemappings(cntlr)
        return {"attempted": True, "loaded_hashes": loaded_hashes, "invalid_hashes": invalid_hashes, "error": None}
    except Exception as exc:
        return {"attempted": True, "loaded_hashes": [], "invalid_hashes": [], "error": exc.__class__.__name__}
    finally:
        cntlr.close()


def _seed_and_verify_sec_taxonomy_cache(cache_dir: Path, archives: list[dict[str, Any]]) -> dict[str, Any]:
    status = {
        "attempted": True,
        "archive_ids": [item["id"] for item in archives],
        "extracted_file_count": 0,
        "offline_entrypoints": [],
        "error": None,
    }
    try:
        extracted_years: set[str] = set()
        for archive in archives:
            year = str(archive["version"])
            status["extracted_file_count"] += _extract_sec_archive_to_cache(
                Path(archive["path"]),
                cache_dir,
                year=year,
            )
            extracted_years.add(year)
        for year in sorted(extracted_years):
            status["offline_entrypoints"].extend(_load_sec_entrypoints_offline(cache_dir, year=year))
    except Exception as exc:
        status["error"] = exc.__class__.__name__
    return status


def _extract_sec_archive_to_cache(archive_path: Path, cache_dir: Path, *, year: str) -> int:
    year = str(year)
    extracted = 0
    with ZipFile(archive_path) as zip_file:
        for name in zip_file.namelist():
            relative_path = _sec_archive_cache_relative_path(name, year=year)
            if relative_path is None:
                continue
            target = cache_dir / "https" / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zip_file.read(name))
            extracted += 1
    return extracted


def _sec_archive_cache_relative_path(name: str, *, year: str) -> Path | None:
    name = name.replace("\\", "/")
    bare_prefix = "xbrl.sec.gov/"
    prefixed_prefix = f"{year}/{bare_prefix}"
    if name.endswith("/"):
        return None
    flat_members = _SEC_FLAT_ARCHIVE_MEMBERS_BY_YEAR.get(year, frozenset())
    if "/" not in name and name in flat_members:
        relative = f"xbrl.sec.gov/cyd/{year}/{name}"
    elif name.startswith(prefixed_prefix):
        relative = name.removeprefix(f"{year}/")
    elif name.startswith(bare_prefix):
        relative = name
    else:
        return None
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    return Path(*parts)


def _sec_entrypoint_urls(year: str) -> list[str]:
    year = str(year)
    urls = [
        f"https://xbrl.sec.gov/dei/{year}/dei-{year}.xsd",
        f"https://xbrl.sec.gov/country/{year}/country-{year}.xsd",
        f"https://xbrl.sec.gov/currency/{year}/currency-{year}.xsd",
        f"https://xbrl.sec.gov/exch/{year}/exch-{year}.xsd",
    ]
    if year in _SEC_FLAT_ARCHIVE_MEMBERS_BY_YEAR:
        urls.append(f"https://xbrl.sec.gov/cyd/{year}/cyd-{year}.xsd")
    return urls


def _load_sec_entrypoints_offline(cache_dir: Path, *, year: str) -> list[dict[str, Any]]:
    year = str(year)
    try:
        from arelle import Cntlr
    except Exception as exc:
        return [
            {
                "year": year,
                "url": "arelle_import",
                "loaded": False,
                "error": exc.__class__.__name__,
                "model_errors": [],
            }
        ]
    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    cntlr.webCache.cacheDir = str(cache_dir)
    cntlr.webCache.workOffline = True
    results: list[dict[str, Any]] = []
    try:
        for url in _sec_entrypoint_urls(year):
            model = None
            try:
                model = cntlr.modelManager.load(url)
                model_errors = list(getattr(model, "errors", []) or []) if model is not None else []
                results.append(
                    {
                        "year": year,
                        "url": url,
                        "loaded": model is not None and not model_errors,
                        "error": None,
                        "model_errors": [str(item) for item in model_errors],
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "year": year,
                        "url": url,
                        "loaded": False,
                        "error": exc.__class__.__name__,
                        "model_errors": [],
                    }
                )
            finally:
                if model is not None:
                    model.close()
    finally:
        cntlr.close()
    return results


def _blocked_reasons(*, arelle: dict[str, Any], packages: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if not arelle["installed"]:
        reasons.append("arelle_package_missing")
    elif not arelle["version_matches"]:
        reasons.append("arelle_version_mismatch")
    if not arelle["importable"]:
        reasons.append("arelle_import_failed")
    if any(not pkg["exists"] for pkg in packages):
        reasons.append("taxonomy_package_missing")
    if any(pkg.get("unavailable_reason") for pkg in packages):
        reasons.append("taxonomy_year_partial_coverage")
    if any(pkg.get("download_blocked") for pkg in packages) or any(pkg["exists"] and not pkg.get("pinned") for pkg in packages):
        reasons.append("taxonomy_package_unpinned")
    if any(pkg["exists"] and pkg.get("pinned") and not pkg["sha256_matches"] for pkg in packages):
        reasons.append("taxonomy_package_hash_mismatch")
    if any(pkg["exists"] and pkg.get("pinned") and not pkg["bytes_match"] for pkg in packages):
        reasons.append("taxonomy_package_size_mismatch")
    return reasons


def _taxonomy_year_coverage(packages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    for package in packages:
        year = str(package.get("version") or "")
        if year not in coverage:
            coverage[year] = {
                "planned_artifact_count": 0,
                "pinned_artifact_count": 0,
                "present_artifact_count": 0,
                "missing_artifact_count": 0,
                "download_ready_artifact_count": 0,
                "unavailable_artifact_count": 0,
                "partial_coverage": False,
            }
        coverage[year]["planned_artifact_count"] += 1
        coverage[year]["pinned_artifact_count"] += 1 if package.get("pinned") else 0
        coverage[year]["present_artifact_count"] += 1 if package.get("exists") else 0
        coverage[year]["missing_artifact_count"] += 0 if package.get("exists") else 1
        coverage[year]["download_ready_artifact_count"] += 1 if package.get("download_ready") else 0
        coverage[year]["unavailable_artifact_count"] += 1 if package.get("unavailable_reason") else 0
        coverage[year]["partial_coverage"] = coverage[year]["unavailable_artifact_count"] > 0
    return coverage


def _download(url: str) -> bytes:
    with urlopen(url, timeout=READ_TIMEOUT_SECONDS) as response:
        return response.read()


def _download_operator_built_archive(spec: dict[str, Any]) -> bytes:
    base_url = str(spec["url"]).rstrip("/") + "/"
    member_payloads: dict[str, bytes] = {}
    for member in sorted(spec.get("operator_built_members") or [], key=lambda item: str(item["name"])):
        name = str(member["name"])
        _validate_flat_member_name(name)
        payload = _download(base_url + name)
        expected_hash = str(member.get("sha256") or "")
        expected_bytes = int(member.get("bytes") or -1)
        if _sha256_bytes(payload) != expected_hash:
            raise RuntimeError("operator_built_member_hash_mismatch")
        if len(payload) != expected_bytes:
            raise RuntimeError("operator_built_member_size_mismatch")
        member_payloads[name] = payload
    archive_payload = _build_flat_zip_archive(member_payloads)
    expected_archive_hash = spec.get("sha256")
    expected_archive_bytes = spec.get("bytes")
    if expected_archive_hash and _sha256_bytes(archive_payload) != expected_archive_hash:
        raise RuntimeError("operator_built_archive_hash_mismatch")
    if expected_archive_bytes and len(archive_payload) != int(expected_archive_bytes):
        raise RuntimeError("operator_built_archive_size_mismatch")
    return archive_payload


def _build_flat_zip_archive(members: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name in sorted(members):
            _validate_flat_member_name(name)
            info = ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 0
            info.compress_type = ZIP_STORED
            info.external_attr = 0o644 << 16
            archive.writestr(info, members[name])
    return buffer.getvalue()


def _validate_flat_member_name(name: str) -> None:
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise ValueError("invalid_flat_archive_member")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": report["schema_id"],
        "ready": report["ready"],
        "blocked_reasons": report["blocked_reasons"],
        "arelle_version": report["arelle"]["version"],
        "requested_taxonomy_years": report["requested_taxonomy_years"],
        "taxonomy_package_loaded_count": report["taxonomy_package_loaded_count"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
