from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.nrc_aps_deterministic_insight_artifact_gate import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
