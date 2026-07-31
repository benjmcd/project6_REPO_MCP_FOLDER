from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.core.config import Settings


_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class DualLiveEvaluationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _require_campaign_id(campaign_id: str) -> None:
    if not isinstance(campaign_id, str):
        raise DualLiveEvaluationError("dual_live_campaign_id_invalid")
    try:
        parsed = UUID(campaign_id)
    except (ValueError, AttributeError):
        raise DualLiveEvaluationError("dual_live_campaign_id_invalid") from None
    if parsed.version != 4 or str(parsed) != campaign_id:
        raise DualLiveEvaluationError("dual_live_campaign_id_invalid")


def _require_campaign_fingerprint(expected_campaign_fingerprint: str) -> None:
    if not isinstance(expected_campaign_fingerprint, str) or not _LOWERCASE_SHA256.fullmatch(
        expected_campaign_fingerprint
    ):
        raise DualLiveEvaluationError("dual_live_campaign_fingerprint_invalid")


def evaluate_dual_live_proof(
    db: Session,
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    settings: Settings,
) -> dict[str, Any]:
    _require_campaign_id(campaign_id)
    _require_campaign_fingerprint(expected_campaign_fingerprint)
    return {
        "schema_id": "project6.dual_live_evaluation.v1",
        "campaign_id": campaign_id,
        "expected_campaign_fingerprint": expected_campaign_fingerprint,
        "status": "INDETERMINATE",
        "fresh_live": False,
        "evaluation_complete": False,
        "code": "tracked_s3_clearance_and_privileged_runner_required",
        "blocking_dependencies": [
            "tracked_external_s3_clause_5_clearance",
            "privileged_dual_live_runner",
        ],
        "validated_surfaces": [],
        "nonclaims": [
            "no campaign evidence evaluated",
            "no connector run executed",
            "no live acquisition performed",
            "no Layer 3 continuity verdict",
            "no package or handoff verdict",
            "no production readiness claim",
        ],
    }
