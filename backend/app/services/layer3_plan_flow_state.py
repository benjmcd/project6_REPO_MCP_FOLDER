from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisPlan, L3Session
from app.services.layer3_plan_revision_state import plan_revision_control_from_session


def latest_analysis_plan(db: Session, *, session_id: str) -> L3AnalysisPlan | None:
    return (
        db.query(L3AnalysisPlan)
        .filter(L3AnalysisPlan.session_id == session_id)
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .first()
    )


def plan_revision_control_for_session(db: Session, *, session_id: str) -> dict[str, Any] | None:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    return plan_revision_control_from_session(session)
