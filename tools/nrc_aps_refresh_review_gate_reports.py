from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.review_nrc_aps_gate_reports import refresh_review_gate_reports  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh review-runtime gate_reports and summary.gate_results for one NRC APS run.")
    parser.add_argument("--run-id", required=True, help="Run id whose review runtime should be refreshed.")
    parser.add_argument("--review-root", default="", help="Optional explicit review runtime root. Defaults to runtime discovery by run id.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow zero matching gate runs instead of failing closed.")
    args = parser.parse_args(argv)

    try:
        result = refresh_review_gate_reports(
            run_id=str(args.run_id),
            review_root=str(args.review_root or "").strip() or None,
            python_executable=sys.executable,
            require_runs=not bool(args.allow_empty),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0 if bool(result.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
