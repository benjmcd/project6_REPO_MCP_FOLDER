from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from zipfile import ZipFile


SCHEMA_ID = "tools.sec_xbrl_arelle_provision.v1"
ARELLE_PACKAGE = "arelle-release"
ARELLE_VERSION = "2.41.3"
READ_TIMEOUT_SECONDS = 120

_TAXONOMY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "fasb-us-gaap-2025",
        "kind": "arelle_taxonomy_package",
        "name": "us-gaap-2025.zip",
        "version": "2025",
        "url": "https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.zip",
        "sha256": "a3b835925ad74030eb5be865a26d7dfe44013081c4ab7204b6122316a685fff4",
        "bytes": 7_101_405,
        "source": "FASB 2025 GAAP Financial Reporting Taxonomy package",
    },
    {
        "id": "fasb-srt-2025",
        "kind": "arelle_taxonomy_package",
        "name": "srt-2025.zip",
        "version": "2025",
        "url": "https://xbrl.fasb.org/srt/2025/srt-2025.zip",
        "sha256": "aad1daeb4bdfe3057f4ed81482c06130f873a59fa7fce5193c5731f93b1fef88",
        "bytes": 191_908,
        "source": "FASB 2025 SEC Reporting Taxonomy package",
    },
    {
        "id": "sec-2025",
        "kind": "offline_cache_archive",
        "name": "sec-2025.zip",
        "version": "2025",
        "url": "https://xbrl.sec.gov/2025.zip",
        "sha256": "6a963051af02ff458e02669549bd55f9d547281724f3b4e053cb0157be8121e4",
        "bytes": 1_201_089,
        "source": "SEC 2025 taxonomy package archive",
    },
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
    args = parser.parse_args()

    report = build_report(
        taxonomy_dir=Path(args.taxonomy_dir),
        cache_dir=Path(args.cache_dir),
        download=not args.no_download,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(_summary(report), sort_keys=True))
    return 0 if report["ready"] else 2


def taxonomy_specs() -> list[dict[str, Any]]:
    return [dict(spec) for spec in _TAXONOMY_SPECS]


def build_report(
    *,
    taxonomy_dir: Path,
    cache_dir: Path,
    download: bool,
    load_with_arelle: bool = True,
) -> dict[str, Any]:
    taxonomy_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    arelle = _arelle_status()
    packages = [_ensure_taxonomy_package(taxonomy_dir, spec, download=download) for spec in taxonomy_specs()]
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
    if not path.exists() and download:
        path.write_bytes(_download(spec["url"]))
        downloaded = True
    exists = path.is_file()
    observed_hash = _sha256(path) if exists else None
    observed_bytes = path.stat().st_size if exists else None
    return {
        **spec,
        "path": str(path),
        "downloaded": downloaded,
        "exists": exists,
        "observed_sha256": observed_hash,
        "sha256_matches": observed_hash == spec["sha256"],
        "observed_bytes": observed_bytes,
        "bytes_match": observed_bytes == spec["bytes"],
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
        for archive in archives:
            status["extracted_file_count"] += _extract_sec_archive_to_cache(Path(archive["path"]), cache_dir)
        status["offline_entrypoints"] = _load_sec_entrypoints_offline(cache_dir)
    except Exception as exc:
        status["error"] = exc.__class__.__name__
    return status


def _extract_sec_archive_to_cache(archive_path: Path, cache_dir: Path) -> int:
    extracted = 0
    with ZipFile(archive_path) as zip_file:
        for name in zip_file.namelist():
            if name.endswith("/") or not name.startswith("2025/xbrl.sec.gov/"):
                continue
            relative = name.removeprefix("2025/")
            target = cache_dir / "https" / Path(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zip_file.read(name))
            extracted += 1
    return extracted


def _load_sec_entrypoints_offline(cache_dir: Path) -> list[dict[str, Any]]:
    try:
        from arelle import Cntlr
    except Exception as exc:
        return [{"url": "arelle_import", "loaded": False, "error": exc.__class__.__name__, "model_errors": []}]
    urls = [
        "https://xbrl.sec.gov/dei/2025/dei-2025.xsd",
        "https://xbrl.sec.gov/country/2025/country-2025.xsd",
        "https://xbrl.sec.gov/currency/2025/currency-2025.xsd",
        "https://xbrl.sec.gov/exch/2025/exch-2025.xsd",
    ]
    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    cntlr.webCache.cacheDir = str(cache_dir)
    cntlr.webCache.workOffline = True
    results: list[dict[str, Any]] = []
    try:
        for url in urls:
            model = None
            try:
                model = cntlr.modelManager.load(url)
                model_errors = list(getattr(model, "errors", []) or []) if model is not None else []
                results.append(
                    {
                        "url": url,
                        "loaded": model is not None and not model_errors,
                        "error": None,
                        "model_errors": [str(item) for item in model_errors],
                    }
                )
            except Exception as exc:
                results.append({"url": url, "loaded": False, "error": exc.__class__.__name__, "model_errors": []})
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
    if any(pkg["exists"] and not pkg["sha256_matches"] for pkg in packages):
        reasons.append("taxonomy_package_hash_mismatch")
    if any(pkg["exists"] and not pkg["bytes_match"] for pkg in packages):
        reasons.append("taxonomy_package_size_mismatch")
    return reasons


def _download(url: str) -> bytes:
    with urlopen(url, timeout=READ_TIMEOUT_SECONDS) as response:
        return response.read()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": report["schema_id"],
        "ready": report["ready"],
        "blocked_reasons": report["blocked_reasons"],
        "arelle_version": report["arelle"]["version"],
        "taxonomy_package_loaded_count": report["taxonomy_package_loaded_count"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
