from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.nrc_aps_validate_only_gates import refresh_validate_only_gates  # noqa: E402
from app.services.nrc_aps_validate_only_gates import ValidateOnlyGatesError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persist the dedicated NRC APS validate-only runtime/report-ref artifact for one run.")
    parser.add_argument("--run-id", required=True, help="Run id whose review runtime should be materialized into the dedicated validate-only artifact.")
    parser.add_argument("--review-root", default="", help="Optional explicit review runtime root. Defaults to runtime discovery by run id.")
    args = parser.parse_args(argv)

    try:
        refresh_validate_only_gates(
            run_id=str(args.run_id),
            review_root=str(args.review_root or "").strip() or None,
        )
    except ValidateOnlyGatesError as exc:
        print(exc.message or str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
