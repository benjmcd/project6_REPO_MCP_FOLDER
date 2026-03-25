from __future__ import annotations

from app.services.sciencebase_connector.contracts import RECONCILIATION_STATUSES


def is_reconciliation_terminal(status: str) -> bool:
    return str(status or "") in RECONCILIATION_STATUSES
