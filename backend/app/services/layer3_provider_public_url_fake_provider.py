from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.layer3_provider_public_url_state import PROVIDER_PUBLIC_URL_REDACTED_MARKER


PROVIDER_PUBLIC_URL_FAKE_PROVIDER_SCHEMA_ID = "layer3.provider_public_url.fake_provider.v1"
PROVIDER_PUBLIC_URL_RESPONSE_FORBIDDEN_FIELDS = frozenset(
    {
        "raw_public_url",
        "provider_credentials",
        "provider_secret",
        "provider_token",
        "public_proxy_url",
        "download_url",
    }
)


@dataclass(frozen=True)
class ProviderPublicUrlFakeReceipt:
    provider_public_url_receipt_id: str
    provider_public_url_state: str
    provider_public_url_prefix: str
    provider_public_url_expires_at_epoch: int

    def to_prepare_response(self) -> dict[str, Any]:
        return {
            "schema_id": PROVIDER_PUBLIC_URL_FAKE_PROVIDER_SCHEMA_ID,
            "provider_public_url_receipt_id": self.provider_public_url_receipt_id,
            "provider_public_url": PROVIDER_PUBLIC_URL_REDACTED_MARKER,
            "provider_public_url_prefix": self.provider_public_url_prefix,
            "provider_public_url_state": self.provider_public_url_state,
            "provider_public_url_expires_at_epoch": self.provider_public_url_expires_at_epoch,
            "public_url_enabled": False,
            "raw_public_url_exposed": False,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
        }
