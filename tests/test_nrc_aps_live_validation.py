import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(BACKEND / "app" / "storage_test_runtime"))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from tools import run_nrc_aps_live_validation as live_validation  # noqa: E402


class _FakeClient:
    def __init__(self) -> None:
        self.scopes: list[str] = []
        self.base_url = "https://adams-api.nrc.gov"
        self.subscription_key = "test-nrc-key"

    def request(
        self,
        *,
        method: str,
        url: str,
        call_class: str,
        headers: dict[str, str],
        json_payload: dict[str, object] | None = None,
        stream: bool = False,
        explicit_scope: str | None = None,
    ):
        self.scopes.append(str(explicit_scope or ""))

        class _Response:
            status_code = 200
            text = '{"count":1,"results":[{"document":{"AccessionNumber":"ML1"}}]}'
            content = text.encode("utf-8")

            def json(self):
                return {"count": 1, "results": [{"document": {"AccessionNumber": "ML1"}}]}

        return _Response()


def test_v1_qps_ramp_uses_distinct_safeguard_scopes_per_attempt(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(live_validation.time, "sleep", lambda _seconds: None)

    result = live_validation.run_v1_qps_ramp(fake, mode="observe")

    assert result["status"] == live_validation.V1_STATUS_OBSERVED
    assert result["levels"]
    assert len(fake.scopes) == sum(level["rps"] for level in result["levels"])
    assert len(fake.scopes) == len(set(fake.scopes))
    assert fake.scopes[0] == "live_validation_v1_rps:1:attempt:1"
    assert "live_validation_v1_rps:3:attempt:3" in fake.scopes
