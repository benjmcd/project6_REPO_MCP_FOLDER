from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_internal_webhook_connector, layer3_workbench


def test_internal_webhook_rejects_credential_bearing_configured_url(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://user:pass@127.0.0.1/hook")

    with pytest.raises(layer3_workbench.Layer3WorkbenchError) as exc:
        layer3_internal_webhook_connector._configured_destination_url()  # noqa: SLF001

    assert exc.value.error_code == "internal_webhook_destination_credentials_not_admitted"
    assert "LAYER3_INTERNAL_WEBHOOK_URL" in exc.value.blocked_fields
