from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen


SCHEMA_ID = "tools.sec_xbrl_arelle_provision.v1"
ARELLE_PACKAGE = "arelle-release"
ARELLE_VERSION = "2.41.3"
READ_TIMEOUT_SECONDS = 120

_TAXONOMY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "fasb-us-gaap-2025",
        "name": "us-gaap-2025.zip",
        "version": "2025",
        "url": "https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.zip",
        "sha256": "a3b835925ad74030eb5be865a26d7dfe44013081c4ab7204b6122316a685fff4",
        "bytes": 7_101_405,
        "source": "FASB 2025 GAAP Financial Reporting Taxonomy package",
    },
    {
        "id": "fasb-srt-2025",
        "name": "srt-2025.zip",
        "version": "2025",
        "url": "https://xbrl.fasb.org/srt/2025/srt-2025.zip",
        "sha256": "aad1daeb4bdfe3057f4ed81482c06130f873a59fa7fce5193c5731f93b1fef88",
        "bytes": 191_908,
        "source": "FASB 2025 SEC Reporting Taxonomy package",
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
    arelle_load = {
        "attempted": False,
        "loaded_hashes": [],
        "invalid_hashes": [],
        "error": None,
    }
    if not blocked and load_with_arelle:
        arelle_load = _load_taxonomy_packages_with_arelle([Path(pkg["path"]) for pkg in packages])
        if arelle_load["error"]:
            blocked.append("arelle_taxonomy_package_load_failed")
        elif len(arelle_load["loaded_hashes"]) != len(packages):
            blocked.append("arelle_taxonomy_package_load_incomplete")
        elif arelle_load["invalid_hashes"]:
            blocked.append("arelle_taxonomy_package_invalid")

    return {
        "schema_id": SCHEMA_ID,
        "ready": not blocked,
        "blocked_reasons": blocked,
        "arelle": arelle,
        "taxonomy_packages": packages,
        "taxonomy_package_count": len(packages),
        "taxonomy_package_loaded_count": len(arelle_load["loaded_hashes"]),
        "taxonomy_cache_dir_created": cache_dir.is_dir(),
        "arelle_load": arelle_load,
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
