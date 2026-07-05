from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SCHEMA_ID = "diagnostics.sec_xbrl_storage_preflight.v1"
DEFAULT_MIN_FREE_BYTES = 25_000_000


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL storage scaling preflight. This reads existing "
            "storage state and free-space metadata only; it does not seed, prune, "
            "or write report artifacts."
        )
    )
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--min-free-bytes", type=int, default=DEFAULT_MIN_FREE_BYTES)
    args = parser.parse_args()

    report = build_report(storage_root=Path(args.storage_root), min_free_bytes=args.min_free_bytes)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["storage_root_exists"] and report["free_space_threshold_met"] else 1


def build_report(*, storage_root: Path, min_free_bytes: int = DEFAULT_MIN_FREE_BYTES) -> dict[str, Any]:
    root = Path(storage_root)
    artifact_count = 0
    total_bytes = 0
    namespace_count = 0
    if root.is_dir():
        namespace_count = sum(1 for child in root.iterdir() if child.is_dir())
        for path in root.rglob("*"):
            if path.is_file():
                artifact_count += 1
                total_bytes += path.stat().st_size

    usage = shutil.disk_usage(_usage_probe_path(root))
    free_space_bytes = int(usage.free)
    threshold = max(0, int(min_free_bytes or 0))
    return {
        "schema_id": SCHEMA_ID,
        "storage_root_exists": root.is_dir(),
        "artifact_count": artifact_count,
        "total_bytes": total_bytes,
        "namespace_count": namespace_count,
        "free_space_bytes": free_space_bytes,
        "min_free_bytes": threshold,
        "free_space_threshold_met": free_space_bytes >= threshold,
        "mutation_performed": False,
        "pruning_performed": False,
        "seed_performed": False,
        "report_artifact_written": False,
        "validate_only": True,
    }


def _usage_probe_path(path: Path) -> Path:
    probe = path
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return probe


if __name__ == "__main__":
    raise SystemExit(main())
