from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from app.services.layer3_sec_xbrl_offline_companyfacts_oracle_packet import (  # noqa: E402
    inspect_sec_xbrl_offline_companyfacts_oracle_packet,
)


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-offline-companyfacts-oracle-packet-report.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL offline CompanyFacts oracle packet diagnostic. It reads already-acquired "
            "offline evidence and an optional operator-supplied CompanyFacts JSON. It does not download sources, "
            "invoke Arelle, touch DB persistence, expose API/UI, reveal values, or claim production readiness."
        )
    )
    parser.add_argument("--storage-dir", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--companyfacts-json", default="")
    parser.add_argument("--expected-sidecar-receipt-hash", default="")
    parser.add_argument("--expected-statement-classification-receipt-hash", default="")
    parser.add_argument("--period-limit", type=int, default=2)
    args = parser.parse_args()

    report = inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        Path(args.storage_dir),
        companyfacts_path=Path(args.companyfacts_json) if args.companyfacts_json else None,
        expected_sidecar_receipt_hash=args.expected_sidecar_receipt_hash or None,
        expected_statement_classification_receipt_hash=args.expected_statement_classification_receipt_hash or None,
        period_limit=args.period_limit,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output.as_posix()}")
    print(f"status={report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
